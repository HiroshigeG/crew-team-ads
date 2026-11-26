"""Onestà sulle immagini con un modello (D38, protocollo evals/PROVA-onesta-immagini.md).

L'espressione regolare del D34 non vede la bugia senza verbi di vista: «The ad
opens with a close-up of a kitchen drawer…» (risposta vera di una testa
solo-testo, 25/11). Qui un modello giudica, solo per le teste senza visione e
solo quando la risposta parla di un'immagine. Offline: il modello è finto.
"""
import logging

import pytest

import crew_cast as core
import guardrails as gr

CTX = "BRIEF:\nSessione ADV\n\nDirector: Descrivimi l'inserzione del 2023.\n"
LIE = ("L'inserzione si apre su un primo piano di un cassetto pieno di borracce ammaccate; "
       "nell'ultima inquadratura la Rivo verde è intatta in fondo, con il logo in basso a destra.")
HONEST = ("Non vedo l'inserzione: secondo la descrizione del Market Researcher c'è un cassetto "
          "con borracce rotte e la Rivo intatta. Da lì direi che il tono è quello giusto.")
NO_IMAGE = ("Siamo a metà: la direzione c'è ma manca il tono per il target e non è chiaro "
            "come si usa il budget. Il Director deve decidere quale rischio prendersi.")


class Seq:
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def call(self, prompt):
        self.prompts.append(prompt)
        return self.replies[min(len(self.prompts), len(self.replies)) - 1]


class Guard:
    """Il modello del controllo, finto: dice «violazione» per le risposte indicate."""

    def __init__(self, bad=(LIE,), fail=False):
        self.bad, self.fail, self.prompts = set(bad), fail, []

    def _via_cli(self, prompt):
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("claude CLI exited 1: giù")
        lied = any(b in prompt for b in self.bad)
        return f'{{"violation": {"true" if lied else "false"}, "why": "dettagli visivi in prima persona"}}'

    def call(self, prompt):                     # mai: il controllo non deve usare l'API
        raise AssertionError("il controllo non deve passare da ClaudeLLM.call (API a pagamento)")


def head(key="account_director", model="featherless_ai/Qwen/Qwen2.5-72B-Instruct"):
    r = core.Roster.load("roster.adv.json")
    r.update_head(key, model_id=model)
    return r.heads[key]


@pytest.fixture
def guard(monkeypatch):
    monkeypatch.setenv("CREW_LLM_GUARDRAIL", "1")
    g = Guard()
    monkeypatch.setattr(core, "llm_claude_guard", g)
    return g


# ── parti pure ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [LIE, HONEST, "The ad opens on a drawer.", "Nel visual il logo è piccolo.",
                                  "La foto è scura."])
def test_replies_about_an_image_are_recognised(text):
    assert gr.mentions_image(text)


@pytest.mark.parametrize("text", [NO_IMAGE, "Ad esempio, il tono può essere più asciutto per il target."])
def test_replies_that_do_not_talk_about_images_are_not(text):
    assert not gr.mentions_image(text)


def test_the_regex_alone_misses_this_lie():
    # perché serve il modello: nessun verbo di vista, nessuna «inserzione» dopo «vedo»
    assert gr.check_reply("account_director", LIE, context=CTX).ok


@pytest.mark.parametrize("raw,expected", [
    ('{"violation": true, "why": "x"}', (True, "x")),
    ('Ecco: {"violation": false, "why": "attribuisce"}', (False, "attribuisce")),
    ("non so", (None, "")),
    ('{"violation": "forse"}', (None, "")),
])
def test_verdict_parsing_is_strict(raw, expected):
    assert gr.parse_image_verdict(raw) == expected


# ── nel giro della risposta ────────────────────────────────────────────────

def test_a_lie_without_seeing_verbs_is_rejected_and_regenerated(guard):
    llm = Seq(LIE, HONEST)
    out = core.guarded_reply(llm, head(), "PROMPT", CTX)
    assert out == HONEST and len(llm.prompts) == 2
    assert "REJECTED" in llm.prompts[1] and "cannot see images" in llm.prompts[1]
    assert "dettagli visivi in prima persona" in llm.prompts[1]   # il motivo del controllo passa al modello


def test_a_lie_that_persists_ends_on_the_honest_fallback(guard):
    out = core.guarded_reply(Seq(LIE), head(), "P", CTX)
    assert "non vedo l'immagine" in out.lower()


def test_the_check_sees_the_transcript_to_tell_relayed_from_invented(guard):
    core.guarded_reply(Seq(HONEST), head(), "P", CTX + "Market Researcher: vedo un cassetto.\n")
    assert "Market Researcher: vedo un cassetto." in guard.prompts[0]


def test_an_honest_reply_about_an_image_costs_one_check_and_passes(guard):
    llm = Seq(HONEST)
    assert core.guarded_reply(llm, head(), "P", CTX) == HONEST
    assert len(llm.prompts) == 1 and len(guard.prompts) == 1


def test_no_check_when_the_reply_does_not_talk_about_images(guard):
    assert core.guarded_reply(Seq(NO_IMAGE), head(), "P", CTX) == NO_IMAGE
    assert guard.prompts == []


def test_no_check_for_a_head_that_can_see(guard):
    assert core.guarded_reply(Seq(LIE), head("market_researcher", "gemini/gemini-3.1-pro-preview"),
                              "P", CTX) == LIE
    assert guard.prompts == []


def test_cli_down_fails_open_with_a_warning_and_never_touches_the_api(monkeypatch, caplog):
    monkeypatch.setenv("CREW_LLM_GUARDRAIL", "1")
    monkeypatch.setattr(core, "llm_claude_guard", Guard(fail=True))
    with caplog.at_level(logging.WARNING, logger="crew_cast"):
        out = core.guarded_reply(Seq(LIE), head(), "P", CTX)
    assert out == LIE                                   # il controllo è una rete, non un blocco
    assert any("controllo immagini" in m.getMessage() for m in caplog.records)


def test_the_model_check_can_be_switched_off_alone(monkeypatch):
    monkeypatch.setenv("CREW_LLM_GUARDRAIL", "0")
    g = Guard()
    monkeypatch.setattr(core, "llm_claude_guard", g)
    assert core.guarded_reply(Seq(LIE), head(), "P", CTX) == LIE and g.prompts == []


def test_the_suite_default_keeps_the_model_check_off():
    import os
    assert os.environ.get("CREW_LLM_GUARDRAIL") == "0"   # conftest: nessuna CLI vera nei test
