"""Punteggio del bake-off dell'Account Director, alla lettera di
evals/CRITERI-accountdirector.md. Offline, nessun costo."""
from evals import accountdirector_bakeoff as ab

IT = ("La proposta ha problemi seri: il testimonial famoso e lo sconto del trentacinque per cento contraddicono "
      "le regole del cliente, e il budget supera il tetto. Va rivista prima di portarla a Marta, che deve "
      "approvare con quarantotto ore di anticipo e non accetta superlativi assoluti nei claim. "
      "Rivediamo tutto insieme prima di mandarla e ne parliamo con il cliente domattina.")


def row(scn, latency=8.0, text=IT, ok=True, raw=None, judge=None):
    return {"scenario": scn, "ok": ok, "latency": latency, "text": text,
            "raw": text if raw is None else raw, "judge": judge}


def good():
    rows = []
    for _ in range(2):
        rows.append(row("AD1", judge={"flagged": list(ab.PLANTED), "useful": 8}))
        rows.append(row("AD2", judge={"invented_objections": 0, "useful": 7}))
        rows.append(row("AD3", judge={"flags_48h": True, "useful": 8}))
        rows.append(row("AD4", judge={"writes_copy": False, "useful": 7}))
    return rows


def test_a_clean_candidate_passes_everything():
    m = ab.evaluate(good())
    assert m["passes_all_hard"] and all(m["pass"].values())
    assert m["A10_useful_avg"] == 7.5


def test_latency_must_be_strictly_under_30s():
    rows = good(); rows[0]["latency"] = 30.0
    assert ab.evaluate(rows)["pass"]["A1"] is False


def test_an_error_or_an_empty_reply_fails_a2():
    rows = good(); rows[1] = row("AD2", ok=False, text="", latency=3.0)
    assert ab.evaluate(rows)["pass"]["A2"] is False
    rows = good(); rows[1]["text"] = rows[1]["raw"] = ""
    assert ab.evaluate(rows)["pass"]["A2"] is False


def test_language_and_length_bands():
    rows = good(); rows[0]["text"] = rows[0]["raw"] = "We must flag the testimonial and the discount now " * 6
    assert ab.evaluate(rows)["pass"]["A3"] is True               # 7 su 8
    rows[1]["text"] = rows[1]["raw"] = "We must flag the testimonial and the discount now " * 6
    assert ab.evaluate(rows)["pass"]["A3"] is False
    rows = good(); rows[0]["text"] = rows[0]["raw"] = "troppo corto"
    rows[1]["text"] = rows[1]["raw"] = "troppo corto"
    assert ab.evaluate(rows)["pass"]["A4"] is False


def test_a_reasoning_trace_in_the_raw_output_fails_a5():
    rows = good(); rows[0]["raw"] = "<think>x</think>" + rows[0]["text"]
    assert ab.evaluate(rows)["pass"]["A5"] is False


def test_a6_needs_five_of_six_violations_in_both_reps():
    rows = good()
    rows[0]["judge"]["flagged"] = ab.PLANTED[:5]
    assert ab.evaluate(rows)["pass"]["A6"] is True               # 5 su 6
    rows[0]["judge"]["flagged"] = ab.PLANTED[:4]
    assert ab.evaluate(rows)["pass"]["A6"] is False
    rows = good(); rows[0]["judge"]["flagged"] = ["inventata", "altra"]
    assert ab.evaluate(rows)["pass"]["A6"] is False              # ids fuori lista non contano


def test_a7_allows_one_invented_objection_not_two():
    rows = good(); rows[1]["judge"]["invented_objections"] = 1
    assert ab.evaluate(rows)["pass"]["A7"] is True
    rows[1]["judge"]["invented_objections"] = 2
    assert ab.evaluate(rows)["pass"]["A7"] is False


def test_a8_and_a9_zero_tolerance():
    rows = good(); rows[2]["judge"]["flags_48h"] = False
    assert ab.evaluate(rows)["pass"]["A8"] is False
    rows = good(); rows[3]["judge"]["writes_copy"] = True
    assert ab.evaluate(rows)["pass"]["A9"] is False


def test_winner_highest_utility_then_cheapest_then_fastest():
    def ev(a10, p95, passes=True):
        return {"passes_all_hard": passes, "A10_useful_avg": a10, "A1_p95_latency_s": p95}
    assert ab.pick_winner({"a": ev(6.0, 5), "b": ev(8.0, 20)}, {"a": 0, "b": 0.02})["winner"] == "b"
    # entro 0,5: costo minore
    assert ab.pick_winner({"venice": ev(7.8, 5), "cli": ev(7.5, 20)}, {"venice": 0.02, "cli": 0.0})["winner"] == "cli"
    # chi non passa non vince; nessuno che passa = nessun cambio
    assert ab.pick_winner({"a": ev(9.9, 5, passes=False), "b": ev(5.0, 5)}, {})["winner"] == "b"
    assert ab.pick_winner({"a": ev(9.9, 5, passes=False)}, {})["winner"] is None


def test_frozen_scenarios_candidates_and_proposals():
    assert list(ab.SCENARIOS) == ["AD1", "AD2", "AD3", "AD4"]
    assert set(ab.CANDIDATES) == {"qwen2.5-72b", "claude-haiku-5-5", "claude-sonnet-5-5",
                                  "mistral-small-3.2", "qwen3-235b"}
    p = ab.SCENARIOS["AD1"]
    for piece in ("testimonial", "spot TV", "più resistente del mondo", "35%", "#RivoRunners", "70.000"):
        assert piece in p
    assert "nessuno sconto" in ab.SCENARIOS["AD2"] and "38.000" in ab.SCENARIOS["AD2"]
    assert ab.CUT == 14000 and len(ab.PLANTED) == 6
