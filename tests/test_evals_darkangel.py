"""Punteggio e tetto di spesa del bake-off di Dark Angel, alla lettera di
evals/CRITERI-darkangel.md. Offline: nessuna chiamata, nessun costo."""
import pytest

from evals import darkangel_bakeoff as da

IT = ("Lei corre alle sei e quaranta, da sola, e non lo racconta a nessuno. La borraccia "
      "è l'unico testimone di una fatica che non ha pubblico, e questo la rende vera.") * 3


def row(scn="DA1", latency=10.0, text=IT, ok=True, raw=None, judge=None):
    return {"scenario": scn, "ok": ok, "latency": latency, "text": text,
            "raw": text if raw is None else raw, "judge": judge}


def good():
    rows = []
    for scn in ("DA1", "DA2", "DA3", "DA4", "DA5", "DA6"):
        for _ in range(2):
            j = ({"claims_to_see": False} if scn == "DA6" else
                 {"refuses": False, "is_narrative": True, "invents_brand_facts": False, "quality": 7})
            rows.append(row(scn, judge=j))
    return rows


# ── spesa ─────────────────────────────────────────────────────────────────

def test_cost_upper_bound_is_deterministic_and_conservative():
    # 3000 caratteri = 1000 token a 3 $/M in + 900 token a 5 $/M out
    c = da.estimate_cost_usd(3000, 3.0, 5.0)
    assert c == pytest.approx((1000 * 3.0 + 900 * 5.0) / 1_000_000)


def test_check_cap_refuses_to_start_above_the_cap():
    with pytest.raises(SystemExit) as e:
        da.check_cap({"a": 0.6, "b": 0.5}, 1.0)
    assert "RIFIUTO DI PARTIRE" in str(e.value)


def test_check_cap_returns_the_total_when_inside():
    assert da.check_cap({"a": 0.3, "b": 0.0, "c": 0.2}, 1.0) == pytest.approx(0.5)


# ── soglie D1-D9 ──────────────────────────────────────────────────────────

def test_clean_candidate_passes_all_hard():
    m = da.evaluate(good())
    assert m["passes_all_hard"] and all(m["pass"].values())
    assert m["D10_quality_avg"] == 7


def test_d1_latency_strictly_under_60s():
    rows = good()
    rows[0]["latency"] = 60.0
    assert da.evaluate(rows)["pass"]["D1"] is False


def test_d2_one_error_fails():
    rows = good()
    rows[2] = row("DA2", ok=False, text="", latency=3.0)
    assert da.evaluate(rows)["pass"]["D2"] is False


def test_d4_empty_reply_from_a_reasoning_model_fails_length():
    rows = good()
    for i in (0, 1):
        rows[i]["text"] = rows[i]["raw"] = ""
    m = da.evaluate(rows)
    assert m["pass"]["D4"] is False and m["pass"]["D3"] is False   # vuota: né lingua né lunghezza


def test_d5_reasoning_trace_in_raw_output_fails():
    rows = good()
    rows[0]["raw"] = "<think>ragiono</think>" + rows[0]["text"]
    assert da.evaluate(rows)["pass"]["D5"] is False


def test_d6_a_single_refusal_fails():
    rows = good()
    rows[0]["judge"]["refuses"] = True
    assert da.evaluate(rows)["pass"]["D6"] is False


def test_d7_needs_nine_of_ten_narratives():
    rows = good()
    rows[0]["judge"]["is_narrative"] = False
    assert da.evaluate(rows)["pass"]["D7"] is True        # 9 su 10
    rows[1]["judge"]["is_narrative"] = False
    assert da.evaluate(rows)["pass"]["D7"] is False


def test_d8_allows_one_invented_fact_not_two():
    rows = good()
    rows[0]["judge"]["invents_brand_facts"] = True
    assert da.evaluate(rows)["pass"]["D8"] is True
    rows[1]["judge"]["invents_brand_facts"] = True
    assert da.evaluate(rows)["pass"]["D8"] is False


def test_d9_pretending_to_see_the_image_fails():
    rows = good()
    next(r for r in rows if r["scenario"] == "DA6")["judge"]["claims_to_see"] = True
    assert da.evaluate(rows)["pass"]["D9"] is False


# ── vincitore ─────────────────────────────────────────────────────────────

def ev(q, passes=True):
    return {"passes_all_hard": passes, "D10_quality_avg": q}


def test_winner_is_highest_quality_among_passing():
    assert da.pick_winner({"a": ev(6.0), "b": ev(8.0)}, {"a": 0.01, "b": 0.05})["winner"] == "b"


def test_quality_tie_goes_to_the_cheaper_one_and_flat_plan_is_free():
    w = da.pick_winner({"venice": ev(7.8), "eva": ev(7.5)}, {"venice": 0.02, "eva": 0.0})
    assert w["winner"] == "eva"


def test_non_passing_never_wins_and_nobody_passing_means_no_change():
    assert da.pick_winner({"a": ev(9.9, passes=False), "b": ev(5.0)}, {})["winner"] == "b"
    assert da.pick_winner({"a": ev(9.9, passes=False)}, {})["winner"] is None


def test_frozen_scenarios_and_candidates():
    assert list(da.SCENARIOS) == ["DA1", "DA2", "DA3", "DA4", "DA5", "DA6"]
    assert [da.SCENARIOS[s][0] for s in ("DA1", "DA2", "DA3")] == [10000, 3000, 14000]
    assert len(da.CANDIDATES) == 5
    assert sum(1 for m in da.CANDIDATES.values() if m.startswith("venice/")) == 4
