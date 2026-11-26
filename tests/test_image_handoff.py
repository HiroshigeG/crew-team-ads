"""D39: la testa senza visione che parla di un'immagine passa la mano a Claude.

Prova del 26/11 (D38): i modelli open mentono sulle immagini in 24 prime risposte
su 27 e insistono anche dopo due rifiuti. Il Copywriter resta su magnum per i
testi; quando la sua risposta parla di un'immagine la riscrive Sonnet, solo da
CLI in abbonamento. Offline: tutti i modelli sono finti.
"""
import json
import logging
from pathlib import Path

import pytest

import crew_cast as core

REPO = Path(__file__).resolve().parent.parent
CTX = "BRIEF:\nSessione ADV\n\nDirector: Descrivimi l'inserzione del 2023.\n"
OPEN_LIE = ("L'inserzione si apre su un cassetto pieno di borracce ammaccate; nell'ultima "
            "inquadratura la Rivo verde è intatta, con il logo in basso a destra.")
CLAUDE_HONEST = ("Non vedo l'inserzione: secondo la descrizione del Market Researcher c'è un "
                 "cassetto con borracce rotte e la Rivo intatta. Il tono mi sembra giusto.")
NO_IMAGE = ("Tre territori di voce: asciutto, ironico, feroce. Il terzo è quello che "
            "nessuno osa dire, e io lo porterei fino in fondo per il target.")


class Seq:
    def __init__(self, *replies, fail=False):
        self.replies, self.prompts, self.fail = list(replies), [], fail

    def call(self, prompt):
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("claude CLI exited 1: giù")
        return self.replies[min(len(self.prompts), len(self.replies)) - 1]


def head(key="copywriter", model="featherless_ai/anthracite-org/magnum-v4-72b",
         image_model="claude-sonnet-5-5"):
    r = core.Roster.load(str(REPO / "roster.adv.json"))
    r.update_head(key, model_id=model, image_model=image_model)
    return r.heads[key]


@pytest.fixture
def claude(monkeypatch):
    """Il modello del passaggio, finto; registra con quale modello è stato chiesto."""
    monkeypatch.setenv("CREW_IMAGE_HANDOFF", "1")
    fake = Seq(CLAUDE_HONEST)
    fake.models = []

    def make(model):
        fake.models.append(model)
        return fake

    monkeypatch.setattr(core, "_image_llm", make)
    return fake


# ── il passaggio ───────────────────────────────────────────────────────────

def test_a_reply_about_an_image_is_rewritten_by_claude(claude):
    own = Seq(OPEN_LIE)
    out = core.guarded_reply(own, head(), "PROMPT", CTX)
    assert out == CLAUDE_HONEST
    assert len(own.prompts) == 1 and claude.prompts == ["PROMPT"]   # stesso prompt
    assert claude.models == ["claude-sonnet-5-5"]


def test_a_reply_that_does_not_talk_about_images_stays_with_the_head(claude):
    assert core.guarded_reply(Seq(NO_IMAGE), head(), "P", CTX) == NO_IMAGE
    assert claude.prompts == []


def test_a_head_without_image_model_keeps_its_reply(claude):
    assert core.guarded_reply(Seq(OPEN_LIE), head(image_model=""), "P", CTX) == OPEN_LIE
    assert claude.prompts == []


def test_a_head_that_can_see_does_not_hand_off(claude):
    h = head("market_researcher", "gemini/gemini-3.1-pro-preview")
    assert core.guarded_reply(Seq(OPEN_LIE), h, "P", CTX) == OPEN_LIE
    assert claude.prompts == []


def test_the_handoff_can_be_switched_off(claude, monkeypatch):
    monkeypatch.setenv("CREW_IMAGE_HANDOFF", "0")
    assert core.guarded_reply(Seq(OPEN_LIE), head(), "P", CTX) == OPEN_LIE
    assert claude.prompts == []


def test_retries_after_the_handoff_go_to_claude_not_back_to_the_head(claude, monkeypatch):
    # il controllo con modello dice «bugia» alla prima riscrittura di Claude
    monkeypatch.setenv("CREW_LLM_GUARDRAIL", "1")
    claude.replies = [OPEN_LIE, CLAUDE_HONEST]

    class Guard:
        def _via_cli(self, prompt):
            lied = OPEN_LIE in prompt
            return f'{{"violation": {"true" if lied else "false"}, "why": "x"}}'

    monkeypatch.setattr(core, "llm_claude_guard", Guard())
    own = Seq(OPEN_LIE)
    out = core.guarded_reply(own, head(), "P", CTX)
    assert out == CLAUDE_HONEST
    assert len(own.prompts) == 1 and len(claude.prompts) == 2
    assert "REJECTED" in claude.prompts[1]


def test_cli_down_keeps_the_head_reply_under_the_checks(monkeypatch, caplog):
    reply = NO_IMAGE + " Nell'inserzione si vede un cassetto."
    monkeypatch.setenv("CREW_IMAGE_HANDOFF", "0")
    without = core.guarded_reply(Seq(reply), head(), "P", CTX)
    monkeypatch.setenv("CREW_IMAGE_HANDOFF", "1")
    down = Seq(fail=True)
    monkeypatch.setattr(core, "_image_llm", lambda model: down)
    own = Seq(reply)
    with caplog.at_level(logging.WARNING, logger="crew_cast"):
        out = core.guarded_reply(own, head(), "P", CTX)
    assert out == without                          # i controlli restano quelli di prima
    assert len(down.prompts) == 1                  # un tentativo, poi le ripetizioni tornano alla testa
    assert any("non disponibile da CLI" in m.getMessage() for m in caplog.records)


# ── mai l'API a pagamento ──────────────────────────────────────────────────

def test_the_handoff_model_only_uses_the_cli(monkeypatch):
    seen = []
    monkeypatch.setattr(core.ClaudeLLM, "_via_cli", lambda self, p: seen.append((self.model, p)) or "ok")

    def no_api(self, prompt):
        raise AssertionError("il passaggio non deve passare da ClaudeLLM.call (API a pagamento)")

    monkeypatch.setattr(core.ClaudeLLM, "call", no_api)
    llm = core._image_llm("claude-sonnet-5-5")
    assert llm.call("P") == "ok" and seen == [("claude-sonnet-5-5", "P")]


def test_a_cli_failure_propagates_instead_of_falling_back_to_the_api(monkeypatch):
    def down(self, p):
        raise RuntimeError("claude CLI exited 1")

    monkeypatch.setattr(core.ClaudeLLM, "_via_cli", down)
    monkeypatch.setattr(core.ClaudeLLM, "call",
                        lambda self, p: (_ for _ in ()).throw(AssertionError("API")))
    with pytest.raises(RuntimeError, match="exited 1"):
        core._image_llm("claude-sonnet-5-5").call("P")


# ── il roster ──────────────────────────────────────────────────────────────

def test_the_production_copywriter_hands_off_images_to_sonnet():
    r = core.Roster.load(str(REPO / "roster.adv.json"))
    cw = r.heads["copywriter"]
    assert cw.model_id == "featherless_ai/anthracite-org/magnum-v4-72b"   # i testi restano a magnum
    assert cw.image_model == "claude-sonnet-5-5"


def test_rosters_written_before_the_field_still_load(tmp_path):
    p = tmp_path / "old.json"
    d = json.loads((REPO / "roster.adv.json").read_text(encoding="utf-8"))
    for h in d["heads"]:
        h.pop("image_model", None)
    p.write_text(json.dumps(d), encoding="utf-8")
    r = core.Roster.load(str(p))
    assert all(h.image_model == "" for h in r.heads.values())


def test_the_suite_default_keeps_the_handoff_off():
    import os
    assert os.environ.get("CREW_IMAGE_HANDOFF") == "0"    # conftest: nessuna CLI vera nei test
