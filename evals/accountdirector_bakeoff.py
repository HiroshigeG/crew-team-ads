"""Bake-off dell'Account Director.

Segue ALLA LETTERA `evals/CRITERI-accountdirector.md` (criteri congelati nel commit
fe66bce, prima di ogni misura). Tetto di spesa 0,10 $: calcola un LIMITE SUPERIORE
dal listino reale di Venice e rifiuta di partire se lo supera. Claude solo da CLI
(mai fallback API). Uso:

    .venv/bin/python3 -m evals.accountdirector_bakeoff --cap-usd 0.10 --out evals/results/accountdirector.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from evals.darkangel_bakeoff import check_cap, estimate_cost_usd, venice_prices  # noqa: E402
from evals.producer_bakeoff import has_leak, italian_ratio, p95, word_count  # noqa: E402

REASONING_MARKERS = ("<|", "<think>", "</think>")
LIMITS = {"p95_s": 30.0, "hung": 0, "lang_min": 7, "len_lo": 50, "len_hi": 250, "len_min": 7,
          "leaks": 0, "flagged_min": 5, "invented_max": 1}

PLANTED = ["testimonial", "tv", "superlativo", "sconto", "hashtag", "budget"]


def has_reasoning_leak(raw: str) -> bool:
    return has_leak(raw) or any(m in raw for m in REASONING_MARKERS)


# ── punteggio A1-A10 ────────────────────────────────────────────────────────

def evaluate(rows: list[dict]) -> dict:
    ok_rows = [r for r in rows if r["ok"] and r["text"].strip()]
    lat = [r["latency"] for r in rows if r["ok"]]
    bad = sum(1 for r in rows if (not r["ok"]) or (not r["text"].strip()) or r["latency"] > 90)
    lang = sum(1 for r in ok_rows if italian_ratio(r["text"]) >= 0.70)
    length = sum(1 for r in ok_rows if LIMITS["len_lo"] <= word_count(r["text"]) <= LIMITS["len_hi"])
    leaks = sum(1 for r in ok_rows if has_reasoning_leak(r["raw"]))

    def j(r):
        return r.get("judge") or {}

    def of(scn):
        return [r for r in rows if r["scenario"] == scn]

    flagged = [len({f for f in (j(r).get("flagged") or []) if f in PLANTED}) for r in of("AD1")]
    invented = [j(r).get("invented_objections") for r in of("AD2")]
    f48 = [j(r).get("flags_48h") is True for r in of("AD3")]
    copy = sum(1 for r in of("AD4") if j(r).get("writes_copy") is True)
    useful = [j(r).get("useful") for r in rows
              if isinstance(j(r).get("useful"), (int, float)) and not isinstance(j(r).get("useful"), bool)]
    m = {
        "n": len(rows),
        "A1_p95_latency_s": round(p95(lat), 1) if lat else None,
        "A2_bad": bad, "A3_italian_ok": lang, "A4_length_ok": length, "A5_leaks": leaks,
        "A6_flagged_per_rep": flagged, "A7_invented_per_rep": invented,
        "A8_flags_48h_per_rep": f48, "A9_writes_copy": copy,
        "A10_useful_avg": round(statistics.mean(useful), 2) if useful else None,
    }
    L = LIMITS
    m["pass"] = {
        "A1": m["A1_p95_latency_s"] is not None and m["A1_p95_latency_s"] < L["p95_s"],
        "A2": bad <= L["hung"], "A3": lang >= L["lang_min"], "A4": length >= L["len_min"],
        "A5": leaks <= L["leaks"],
        "A6": len(flagged) == 2 and all(f >= L["flagged_min"] for f in flagged),
        "A7": len(invented) == 2 and all(isinstance(i, int) and i <= L["invented_max"] for i in invented),
        "A8": len(f48) == 2 and all(f48),
        "A9": copy <= 0 and len(of("AD4")) == 2,
    }
    m["passes_all_hard"] = all(m["pass"].values())
    return m


def pick_winner(evals: dict[str, dict], cost_per_call: dict[str, float]) -> dict:
    """Tra chi passa vince la A10 più alta; a parità (entro 0,5) il costo minore, poi
    il p95 più basso; se nessuno passa, nessuno (l'Account Director non cambia)."""
    passing = {k: v for k, v in evals.items() if v["passes_all_hard"] and v["A10_useful_avg"] is not None}
    if not passing:
        return {"winner": None, "reason": "nessun candidato passa A1-A9"}
    best = max(v["A10_useful_avg"] for v in passing.values())
    close = [k for k, v in passing.items() if best - v["A10_useful_avg"] <= 0.5]
    winner = min(close, key=lambda k: (cost_per_call.get(k, 0.0), passing[k]["A1_p95_latency_s"]))
    return {"winner": winner,
            "reason": f"passa A1-A9; A10 {passing[winner]['A10_useful_avg']} (migliore {best}); "
                      f"entro 0,5 vince il costo minore, poi il p95: {close}"}


# ── scenari e candidati (identici a CRITERI-accountdirector.md) ──────────────

def _proposal(text: str) -> str:
    return f"Il Director sottopone questa proposta: {text} Dai il tuo parere da Account Director."


SCENARIOS = {
    "AD1": _proposal("testimonial un ex velocista famoso, spot TV regionale e affissioni, claim "
                     "\"La borraccia più resistente del mondo\", sconto del 35% per tre giorni a Natale, "
                     "hashtag #RivoRunners, budget 70.000 €."),
    "AD2": _proposal("film da 20 secondi alle 6:40 in un cortile, luce piatta, nessun volto riconoscibile, "
                     "claim \"Non ti incita. Non perde.\" con sotto \"Guarnizione sostituibile. 12 ore al "
                     "freddo, 6 al caldo (test interno).\", solo Instagram e YouTube, budget 38.000 €, "
                     "nessuno sconto."),
    "AD3": "Lanciamo la creatività domani mattina alle 9, è pronta stasera. Ti torna?",
    "AD4": "Scrivimi tu tre slogan alternativi per Rivo, così li portiamo a Marta.",
}
CUT = 14000
CANDIDATES = {
    "qwen2.5-72b": ("open", "featherless_ai/Qwen/Qwen2.5-72B-Instruct"),
    "claude-haiku-5-5": ("cli", "claude-haiku-5-5"),
    "claude-sonnet-5-5": ("cli", "claude-sonnet-5-5"),
    "mistral-small-3.2": ("open", "venice/mistral-small-3-2-24b-instruct"),
    "qwen3-235b": ("open", "venice/qwen3-235b-a22b-instruct-2507"),
}


def judge_prompt(scn: str, instruction: str, reply: str, transcript: str) -> str:
    base = ("You are a strict, literal evaluator. Answer ONLY with a JSON object, no prose, no markdown "
            "fence.\n\n")
    head = (f"CLIENT GUIDELINES AND RULES (in the transcript):\n{transcript}\n\n"
            f"The Director said: \"{instruction}\"\n\nREPLY of the Account Director:\n{reply}\n\n")
    useful = ('"useful": <integer 1-10: how useful the reply is to the Director: a clear verdict and '
              'prioritised objections, not a vague summary>')
    if scn == "AD1":
        return base + head + (
            "The proposal contains exactly SIX violations of the client's rules: testimonial (a famous "
            "testimonial), tv (TV is excluded), superlativo (absolute superlative claim), sconto (35% discount "
            "above the 15% limit), hashtag (hashtag with the brand name), budget (70.000 € above the 50.000 € "
            "cap). List which of these ids the reply CLEARLY flags as a problem.\n"
            '{"flagged": ["testimonial"|"tv"|"superlativo"|"sconto"|"hashtag"|"budget", ...], ' + useful + "}")
    if scn == "AD2":
        return base + head + (
            "This proposal complies with all the client's rules. Count the objections in the reply that are "
            "NOT grounded in the client's rules or the brief (invented problems).\n"
            '{"invented_objections": <integer>, ' + useful + "}")
    if scn == "AD3":
        return base + head + (
            "The client's rules say the founder (Marta) needs 48 hours to approve any creative. Does the reply "
            "flag the 48-hour approval as a problem for launching tomorrow?\n"
            '{"flags_48h": true or false, ' + useful + "}")
    return base + head + (
        "The Account Director never writes copy or invents concepts. Does the reply write slogans, headlines "
        "or claims of its own?\n"
        '{"writes_copy": true or false, ' + useful + "}")


# ── esecuzione ──────────────────────────────────────────────────────────────

def run(out: Path, cap_usd: float, reps: int = 2, only=None) -> dict:
    os.environ.setdefault("CREW_OPEN_MODEL_TIMEOUT", "90")
    os.environ.setdefault("CREW_CLAUDE_TIMEOUT", "120")
    import crew_cast as core
    import providers as pv

    fixture = (REPO / "evals/fixtures/rivo-room.md").read_text(encoding="utf-8")
    head_base = "BRIEF:\nSessione ADV (web)\n\nDirector: Rivo, valutiamo una proposta.\n"
    roster_path = str(REPO / "roster.adv.json")
    names = [n for n in CANDIDATES if not only or n in only]

    def build(name: str, scn: str):
        kind, model = CANDIDATES[name]
        r = core.Roster.load(roster_path)
        r.update_head("account_director", model_id=model if kind == "open" else f"anthropic/{model}")
        ctx = head_base + fixture[:CUT]
        return r, core.build_turn_prompt(r.heads["account_director"], ctx, SCENARIOS[scn]), ctx

    base = os.getenv("VENICE_API_BASE") or pv.PROVIDERS["venice"].openai_base
    key = os.getenv("VENICE_API_KEY", "")
    prices = venice_prices(base, key) if key else {}
    upper: dict[str, float] = {}
    cost_per_call: dict[str, float] = {}
    for name in names:
        kind, model = CANDIDATES[name]
        if not model.startswith("venice/"):
            upper[name], cost_per_call[name] = 0.0, 0.0
            continue
        vid = model.split("/", 1)[1]
        if vid not in prices:
            raise SystemExit(f"prezzo Venice non trovato per {vid}: non parto (tetto non verificabile)")
        inp, outp = prices[vid]
        costs = [estimate_cost_usd(len(build(name, s)[1]), inp, outp) for s in SCENARIOS for _ in range(reps)]
        upper[name], cost_per_call[name] = sum(costs), max(costs)
    total = check_cap(upper, cap_usd)
    print(f"limite superiore di spesa: {total:.3f} $ (tetto {cap_usd:.2f} $) "
          f"{ {k: round(v, 4) for k, v in upper.items()} }", flush=True)

    def one(name: str) -> list[dict]:
        rows = []
        for scn in SCENARIOS:
            for rep in range(reps):
                r, prompt, ctx = build(name, scn)
                kind, model = CANDIDATES[name]
                t = time.time()
                try:
                    if kind == "cli":
                        raw = core.ClaudeLLM(model, effort="medium")._via_cli(prompt)       # mai API
                    else:
                        raw = str(r.llm("account_director").call(prompt))
                    ok, err = True, ""
                except Exception as e:                                  # noqa: BLE001
                    raw, ok, err = "", False, f"{type(e).__name__}: {str(e)[:140]}"
                rows.append({"candidate": name, "scenario": scn, "rep": rep, "ok": ok,
                             "latency": round(time.time() - t, 1), "raw": raw,
                             "text": core.finish_reply(raw) if ok else "", "error": err, "ctx": ctx})
                print(f"  {name:20s} {scn} #{rep+1}: {rows[-1]['latency']:6.1f}s "
                      f"{'ok' if ok else 'ERR ' + err}", flush=True)
        return rows

    with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
        all_rows = [r for part in ex.map(one, names) for r in part]

    judge = core.ClaudeLLM(os.environ.get("BAKEOFF_JUDGE", "claude-opus-5-5"), effort="low")

    def do_judge(row: dict) -> None:
        if not row["ok"] or not row["text"].strip():
            return
        raw = judge._via_cli(judge_prompt(row["scenario"], SCENARIOS[row["scenario"]], row["text"], row["ctx"]))
        row["judge"] = core._first_json_value(raw) or {}

    print("giudizio…", flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(do_judge, all_rows))

    evals = {n: evaluate([r for r in all_rows if r["candidate"] == n]) for n in names}
    res = {"criteri": "evals/CRITERI-accountdirector.md@fe66bce", "judge": judge.model,
           "cap_usd": cap_usd, "upper_bound_usd": round(total, 4), "evals": evals,
           "winner": pick_winner(evals, cost_per_call),
           "rows": [{k: v for k, v in r.items() if k != "ctx"} for r in all_rows]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", default=str(REPO / "evals/results/accountdirector.json"))
    a = ap.parse_args()
    res = run(Path(a.out), a.cap_usd, only=a.only)
    print(json.dumps({"evals": res["evals"], "winner": res["winner"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
