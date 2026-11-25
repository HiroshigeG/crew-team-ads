"""Il produttore in produzione è ESATTAMENTE quello misurato nel bake-off v2
(evals/CRITERI-producer-v2.md): stessa persona, modello vincitore."""
import json
from pathlib import Path

import crew_cast as core
import providers as pv

REPO = Path(__file__).resolve().parent.parent
V2 = (REPO / "evals/personas/producer-v2.txt").read_text(encoding="utf-8")


def _adv_producer():
    r = json.loads((REPO / "roster.adv.json").read_text(encoding="utf-8"))
    heads = r["heads"] if isinstance(r, dict) and "heads" in r else r
    heads = heads if isinstance(heads, list) else list(heads.values())
    return next(h for h in heads if h["key"] == "producer")


def test_persona_in_code_is_the_measured_one():
    assert core.ROLE_PERSONAS["producer"] == V2


def test_persona_in_the_web_roster_is_the_measured_one():
    assert _adv_producer()["persona"] == V2


def test_the_producer_never_picks_even_softly():
    p = core.ROLE_PERSONAS["producer"]
    assert "NEVER choose, rank or recommend" in p
    assert "not even softly" in p


def test_the_winner_model_runs_the_producer():
    assert _adv_producer()["model_id"] == "anthropic/claude-sonnet-5-5"


def test_the_web_roster_loads_and_every_model_is_allowed():
    r = core.Roster.load(str(REPO / "roster.adv.json"))
    assert r.heads["producer"].model_id == "anthropic/claude-sonnet-5-5"
    assert all(core.model_allowed(h.model_id) for h in r.heads.values())


def test_autocast_prefers_the_measured_producer_models():
    a = pv.autocast(["producer"], {"anthropic"})
    assert a["producer"] == "anthropic/claude-sonnet-5-5"
    # senza Sonnet disponibile ma con Claude: ripiego misurato (Haiku passa il v2)
    assert pv.ROLE_PREFERENCES["producer"][:2] == (
        "anthropic/claude-sonnet-5-5", "anthropic/claude-haiku-5-5")
