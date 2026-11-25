"""Account Director in produzione = il vincitore del bake-off
(evals/CRITERI-accountdirector.md, risultati in evals/results/accountdirector.json)."""
import json
from pathlib import Path

import crew_cast as core
import providers as pv

REPO = Path(__file__).resolve().parent.parent


def _ad():
    r = json.loads((REPO / "roster.adv.json").read_text(encoding="utf-8"))
    heads = r["heads"] if isinstance(r, dict) and "heads" in r else r
    heads = heads if isinstance(heads, list) else list(heads.values())
    return next(h for h in heads if h["key"] == "account_director")


def test_the_account_director_runs_on_the_measured_winner():
    h = _ad()
    assert h["model_id"] == "anthropic/claude-sonnet-5-5"
    # misurato con effort medium: l'`high` precedente non è mai stato provato
    assert h["effort"] == "medium"


def test_the_persona_is_unchanged():
    assert _ad()["persona"].lstrip().startswith("You are the Account Director: you carry the client")
    assert "never write copy" in _ad()["persona"]


def test_the_roster_still_loads_with_every_model_allowed():
    r = core.Roster.load(str(REPO / "roster.adv.json"))
    assert r.heads["account_director"].model_id == "anthropic/claude-sonnet-5-5"
    assert all(core.model_allowed(h.model_id) for h in r.heads.values())


def test_autocast_prefers_the_measured_account_director_models():
    assert pv.ROLE_PREFERENCES["account_director"][:2] == (
        "anthropic/claude-sonnet-5-5", "anthropic/claude-haiku-5-5")
    # con Claude e basta, producer e Account Director non finiscono sullo stesso modello se si può evitare
    a = pv.autocast(["producer", "account_director"], {"anthropic"})
    assert a["producer"] != a["account_director"]
