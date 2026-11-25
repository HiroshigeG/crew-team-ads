"""Dark Angel in produzione = il candidato scelto dopo il bake-off v2
(evals/CRITERI-darkangel-v2.md, scelta del Director il 25/11/2026)."""
import json
from pathlib import Path

import crew_cast as core
import providers as pv

REPO = Path(__file__).resolve().parent.parent
GLM = "venice/glm-5-3-flash-uncensored"


def _adv_dark_angel():
    r = json.loads((REPO / "roster.adv.json").read_text(encoding="utf-8"))
    heads = r["heads"] if isinstance(r, dict) and "heads" in r else r
    heads = heads if isinstance(heads, list) else list(heads.values())
    return next(h for h in heads if h["key"] == "dark_angel")


def test_dark_angel_runs_on_the_abliterated_venice_model():
    assert _adv_dark_angel()["model_id"] == GLM


def test_temperature_is_the_measured_neighbourhood_not_the_broken_one(monkeypatch):
    # misurato: a 0,9 il testo è pulito, a 1,09 (creatività 9) esce con parole rovinate
    monkeypatch.setenv("VENICE_API_KEY", "chiave-finta")
    r = core.Roster.load(str(REPO / "roster.adv.json"))
    t = core.make_llm(r.heads["dark_angel"]).temperature
    assert 0.8 <= t <= 0.95, t


def test_the_roster_still_loads_with_every_model_allowed():
    r = core.Roster.load(str(REPO / "roster.adv.json"))
    assert all(core.model_allowed(h.model_id) for h in r.heads.values())


def test_autocast_prefers_the_measured_dark_angel():
    assert pv.ROLE_PREFERENCES["dark_angel"][0] == GLM
    assert pv.autocast(["dark_angel"], {"venice"})["dark_angel"] == GLM


def test_suggested_venice_models_are_only_the_ones_that_worked():
    s = pv.PROVIDERS["venice"].suggested
    assert s[0] == GLM
    # misurati e scartati: risposte vuote col tetto di produzione / finge di vedere
    assert "venice/abliteration-abliterated-model-large-v2" not in s
    assert "venice/venice-uncensored-1-2" not in s
