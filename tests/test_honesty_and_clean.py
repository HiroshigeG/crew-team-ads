"""Offline: pulizia dei token trapelati, onestà dei modelli, lingua del Director.

Regressioni del 25/11/2026: una risposta finiva con `<|im_end|>` (token del
template di chat di Hermes-3); l'Account Director (solo testo) scriveva
«Looking at the ad…» come se vedesse l'immagine; le teste rispondevano in
inglese a un cliente che scriveva in italiano.
"""
import pytest

import crew_cast as core


# ── token speciali trapelati ──────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("risposta.<|im_end|>", "risposta."),
    ("risposta.<|im_end|>\n", "risposta."),
    ("<|im_start|>assistant\nciao", "ciao"),
    ("testo<|endoftext|>", "testo"),
    ("testo<|eot_id|><|start_header_id|>user<|end_header_id|>", "testo"),
    ("testo</s>", "testo"),
    ("testo<|end_of_text|>", "testo"),
    # misurato il 25/11 su Featherless: dopo la fine-turno Hermes-3 INVENTA un
    # intero turno dell'utente. Tutto ciò che segue la prima fine-turno è scarto.
    ("Azzurro<|im_end|>\n<|im_start|>user\nQuanto è alto il cielo?", "Azzurro"),
    ("Sì.<|im_end|>\n<|im_start|>assistant\nNo.<|im_end|>", "Sì."),
])
def test_strip_special_tokens_removes_template_leaks(raw, expected):
    assert core.strip_special_tokens(raw).strip() == expected


@pytest.mark.parametrize("text", [
    "a < b | c > d",
    "<b>grassetto</b> e <i>corsivo</i>",
    "Il tag |pipe| resta.",
    "SEARCH_REQUEST: borracce 2026 || perché serve",
])
def test_strip_special_tokens_keeps_normal_text(text):
    assert core.strip_special_tokens(text) == text


def test_strip_special_tokens_is_idempotent():
    once = core.strip_special_tokens("x<|im_end|><|im_end|>")
    assert core.strip_special_tokens(once) == once == "x"


class _LeakyLLM:
    def call(self, prompt):
        return "  risposta pulita.<|im_end|>  "


def test_head_speak_strips_leaked_token(monkeypatch):
    r = core.Roster.default()
    monkeypatch.setitem(r._llms, "cd", _LeakyLLM())
    assert core.head_speak(r, "cd", "T", "go") == "risposta pulita."


def test_head_speak_after_search_strips_leaked_token(monkeypatch):
    r = core.Roster.default()
    monkeypatch.setitem(r._llms, "cd", _LeakyLLM())
    out = core.head_speak_after_search(r, "cd", "T", "perché")
    assert out == "risposta pulita."


def test_legacy_speak_paths_strip_leaked_token(monkeypatch):
    monkeypatch.setitem(core.CAST["cd"], "llm", _LeakyLLM())
    assert core.speak("cd", "T", "go") == "risposta pulita."
    assert core.speak_after_search("cd", "T", "perché") == "risposta pulita."


def test_head_study_image_strips_leaked_token(monkeypatch):
    import litellm

    class _Msg:
        content = "descrizione<|im_end|>"

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    monkeypatch.setattr(litellm, "completion", lambda **kw: _Resp())
    r = core.Roster.default()
    r.update_head("cd", model_id="gemini/gemini-3.1-pro-preview")
    assert core.head_study_image(r, "cd", "T", "guarda", "AAAA") == "descrizione"


# ── onestà: il modello non mente mai ──────────────────────────────────────

def test_room_rules_have_an_honesty_block():
    rules = core.ROOM_RULES
    assert "HONESTY" in rules
    assert "never lie" in rules.lower()
    # niente da dichiarare come fatto se non è stato fatto davvero
    assert "did not actually do" in rules
    # le immagini si conoscono solo attraverso la descrizione di un'altra testa
    assert "cannot see images" in rules
    assert "according to" in rules


def test_text_only_head_is_told_it_cannot_see():
    r = core.Roster.default()
    r.update_head("cd", model_id="anthropic/claude-sonnet-5")
    p = core.build_turn_prompt(r.heads["cd"], "T", "go")
    assert "CAPABILITIES" in p
    assert "text only" in p
    assert "you cannot see any image" in p


def test_vision_head_is_not_told_it_is_blind():
    r = core.Roster.default()
    r.update_head("cd", model_id="gemini/gemini-3.1-pro-preview")
    p = core.build_turn_prompt(r.heads["cd"], "T", "go")
    assert "you cannot see any image" not in p
    assert "you can see images" in p


# ── lingua: quella del Director ───────────────────────────────────────────

def test_room_rules_follow_the_directors_language():
    rules = core.ROOM_RULES
    assert "Speak in English" not in rules
    assert "language the Director" in rules
    assert "Italian" in rules          # l'esempio concreto che ha rotto il 25/11


def test_judge_reason_follows_the_goal_language():
    assert "language of the goal" in core.JUDGE_PROMPT
