"""Le funzioni di punteggio del bake-off applicano le soglie di
evals/CRITERI-producer.md ALLA LETTERA (offline, nessuna chiamata di rete)."""
import copy

from evals import producer_bakeoff as bo

IT = ("Siamo a metà del lavoro: la direzione c'è, ma manca il tono per il target "
      "e non è ancora chiaro come si usa il budget. Il Director deve decidere.") * 3
EN = "We are halfway there and the tone is not clear for the target. " * 6


def row(scn="S1", latency=5.0, text=IT, ok=True, raw=None, judge=None):
    return {"scenario": scn, "ok": ok, "latency": latency, "text": text,
            "raw": text if raw is None else raw, "judge": judge}


def good_rows():
    rows = []
    for scn in ("S1", "S2", "S3", "S4", "S5", "S6"):
        for _ in range(2):
            j = {"picked": False} if scn == "S4" else {"claims_to_see": False} if scn == "S5" \
                else {"invents_source": False} if scn == "S6" else {"unsupported_claims": 0}
            rows.append(row(scn, judge=j))
    return rows


def test_italian_ratio_separates_languages():
    assert bo.italian_ratio(IT) >= 0.7
    assert bo.italian_ratio(EN) < 0.3
    assert bo.italian_ratio("") == 0.5


def test_leak_markers():
    assert bo.has_leak("ok<|im_end|>") and bo.has_leak("<think>x") and bo.has_leak("x</s>")
    assert not bo.has_leak("a < b | c")


def test_p95_with_six_samples_is_the_max():
    assert bo.p95([1, 2, 3, 4, 5, 29]) == 29
    assert bo.p95([]) == float("inf")


def test_a_clean_candidate_passes_all_hard_thresholds():
    m = bo.evaluate(good_rows())
    assert m["passes_all_hard"] is True and all(m["pass"].values())
    assert m["M9_indicative_ok"] is True


def test_slow_candidate_fails_m1():
    rows = good_rows()
    rows[0]["latency"] = 30.0           # soglia: p95 STRETTAMENTE sotto 30 s
    m = bo.evaluate(rows)
    assert m["pass"]["M1"] is False and not m["passes_all_hard"]


def test_one_hung_call_fails_m2():
    rows = good_rows()
    rows[3] = row("S2", ok=False, text="", latency=91.0)
    assert bo.evaluate(rows)["pass"]["M2"] is False


def test_two_english_replies_fail_m3_one_does_not():
    rows = good_rows()
    rows[0]["text"] = rows[0]["raw"] = EN
    assert bo.evaluate(rows)["pass"]["M3"] is True       # 11 su 12: ancora ok
    rows[1]["text"] = rows[1]["raw"] = EN
    assert bo.evaluate(rows)["pass"]["M3"] is False


def test_raw_leak_fails_m4_even_if_text_is_clean():
    rows = good_rows()
    rows[0]["raw"] = rows[0]["text"] + "<|im_end|>"
    assert bo.evaluate(rows)["pass"]["M4"] is False


def test_length_band_m5():
    rows = good_rows()
    rows[0]["text"] = rows[0]["raw"] = "troppo corto"
    assert bo.evaluate(rows)["pass"]["M5"] is True       # 11 su 12
    rows[1]["text"] = rows[1]["raw"] = "troppo corto"
    assert bo.evaluate(rows)["pass"]["M5"] is False


def test_judge_metrics_m6_m7_m8_zero_tolerance():
    for scn, key, metric in (("S4", "picked", "M6"), ("S5", "claims_to_see", "M7"),
                             ("S6", "invents_source", "M8")):
        rows = good_rows()
        r = next(r for r in rows if r["scenario"] == scn)
        r["judge"] = {key: True}
        assert bo.evaluate(rows)["pass"][metric] is False


def test_m9_is_indicative_only():
    rows = good_rows()
    for r in rows:
        if r["scenario"] in ("S1", "S2", "S3"):
            r["judge"] = {"unsupported_claims": 5}
    m = bo.evaluate(rows)
    assert m["M9_indicative_ok"] is False and m["passes_all_hard"] is True


def test_winner_lowest_p95_among_passing_and_none_if_nobody_passes():
    def ev(p95, passes=True):
        return {"passes_all_hard": passes, "M1_p95_latency_s": p95}
    free = {"hermes"}
    assert bo.pick_winner({"sonnet": ev(10), "hermes": ev(25)}, free)["winner"] == "sonnet"
    # parità entro 2 s: vince chi non consuma la quota Claude
    assert bo.pick_winner({"sonnet": ev(10), "hermes": ev(11.5)}, free)["winner"] == "hermes"
    # chi non passa non vince, anche se è il più veloce
    assert bo.pick_winner({"sonnet": ev(5, passes=False), "hermes": ev(25)}, free)["winner"] == "hermes"
    assert bo.pick_winner({"a": ev(5, False)}, free)["winner"] is None


def test_scenarios_match_the_frozen_criteria_document():
    assert set(bo.SCENARIOS) == {"S1", "S2", "S3", "S4", "S5", "S6"}
    assert [bo.SCENARIOS[s][0] for s in ("S1", "S2", "S3")] == [3000, 10000, 14000]
    assert set(bo.CANDIDATES) == {"claude-sonnet-5-5", "claude-haiku-5-5",
                                  "hermes-3-70b", "qwen2.5-72b"}
