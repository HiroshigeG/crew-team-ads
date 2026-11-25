"""Bake-off di Dark Angel.

Segue ALLA LETTERA `evals/CRITERI-darkangel.md` (criteri congelati nel commit
a860d52, scritti prima di ogni misura). Tetto di spesa 1 $: il banco di prova
calcola prima un LIMITE SUPERIORE dal listino reale di Venice e non parte se lo
supera. Uso:

    .venv/bin/python3 -m evals.darkangel_bakeoff --cap-usd 1.0 --out evals/results/darkangel.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import statistics
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from evals.producer_bakeoff import (  # noqa: E402  (stesse funzioni pure del produttore)
    italian_ratio, p95, word_count,
)

REASONING_MARKERS = ("<|", "<think>", "</think>")
OUT_TOKENS_CAP = 900          # = CREW_MAX_REPLY_TOKENS di produzione


def has_reasoning_leak(raw: str) -> bool:
    return any(m in raw for m in REASONING_MARKERS)


# ── spesa: limite superiore, calcolato PRIMA di chiamare ─────────────────────

def estimate_cost_usd(prompt_chars: int, in_per_m: float, out_per_m: float,
                      out_tokens: int = OUT_TOKENS_CAP) -> float:
    """Limite superiore di UNA chiamata: prompt a 1 token ogni 3 caratteri
    (prudente) + il tetto di token in uscita, ai prezzi per milione di token."""
    return ((prompt_chars / 3.0) * in_per_m + out_tokens * out_per_m) / 1_000_000


def check_cap(per_candidate_usd: dict[str, float], cap_usd: float) -> float:
    """Somma i limiti superiori; se superano il tetto solleva: nessuna chiamata."""
    total = sum(per_candidate_usd.values())
    if total > cap_usd:
        raise SystemExit(
            f"RIFIUTO DI PARTIRE: limite superiore {total:.3f} $ > tetto {cap_usd:.2f} $ "
            f"({ {k: round(v, 3) for k, v in per_candidate_usd.items()} })")
    return total


# ── punteggio D1-D10 ────────────────────────────────────────────────────────

LIMITS = {
    "p95_s": 60.0, "hung": 0, "lang_min": 11, "lang_ratio": 0.70,
    "len_min": 11, "len_lo": 60, "len_hi": 250, "leaks": 0,
    "refuses": 0, "narrative_min": 9, "invents_max": 1, "see": 0,
}
CREATIVE = ("DA1", "DA2", "DA3", "DA4", "DA5")


def evaluate(rows: list[dict]) -> dict:
    ok_rows = [r for r in rows if r["ok"]]
    lat = [r["latency"] for r in rows if r["scenario"] in CREATIVE and r["ok"]]
    hung = sum(1 for r in rows if (not r["ok"]) or r["latency"] > 90)
    lang = sum(1 for r in ok_rows if italian_ratio(r["text"]) >= LIMITS["lang_ratio"])
    length = sum(1 for r in ok_rows
                 if LIMITS["len_lo"] <= word_count(r["text"]) <= LIMITS["len_hi"])
    leaks = sum(1 for r in ok_rows if has_reasoning_leak(r["raw"]))

    def j(r):
        return r.get("judge") or {}

    cre = [r for r in rows if r["scenario"] in CREATIVE]
    refuses = sum(1 for r in cre if j(r).get("refuses") is True)
    narrative = sum(1 for r in cre if j(r).get("is_narrative") is True)
    invents = sum(1 for r in cre if j(r).get("invents_brand_facts") is True)
    sees = sum(1 for r in rows if r["scenario"] == "DA6" and j(r).get("claims_to_see") is True)
    q = [j(r).get("quality") for r in cre
         if isinstance(j(r).get("quality"), (int, float)) and not isinstance(j(r).get("quality"), bool)]
    m = {
        "n": len(rows),
        "D1_p95_latency_s": round(p95(lat), 1) if lat else None,
        "D2_hung": hung, "D3_italian_ok": lang, "D4_length_ok": length, "D5_leaks": leaks,
        "D6_refuses": refuses, "D7_narrative": narrative, "D8_invents_facts": invents,
        "D9_claims_to_see": sees,
        "D10_quality_avg": round(statistics.mean(q), 2) if q else None,
    }
    h = LIMITS
    m["pass"] = {
        "D1": m["D1_p95_latency_s"] is not None and m["D1_p95_latency_s"] < h["p95_s"],
        "D2": hung <= h["hung"], "D3": lang >= h["lang_min"], "D4": length >= h["len_min"],
        "D5": leaks <= h["leaks"], "D6": refuses <= h["refuses"],
        "D7": narrative >= h["narrative_min"], "D8": invents <= h["invents_max"],
        "D9": sees <= h["see"],
    }
    m["passes_all_hard"] = all(m["pass"].values())
    return m


def pick_winner(evals: dict[str, dict], cost_per_call: dict[str, float]) -> dict:
    """Tra chi passa vince la D10 più alta; a parità (entro 0,5) il costo minore;
    se nessuno passa, nessuno (il Dark Angel di produzione non cambia)."""
    passing = {k: v for k, v in evals.items()
               if v["passes_all_hard"] and v["D10_quality_avg"] is not None}
    if not passing:
        return {"winner": None, "reason": "nessun candidato passa D1-D9"}
    best = max(v["D10_quality_avg"] for v in passing.values())
    close = [k for k, v in passing.items() if best - v["D10_quality_avg"] <= 0.5]
    winner = min(close, key=lambda k: (cost_per_call.get(k, 0.0), -passing[k]["D10_quality_avg"]))
    return {"winner": winner,
            "reason": f"passa D1-D9; D10 {passing[winner]['D10_quality_avg']} "
                      f"(migliore {best}); a parità entro 0,5 vince il costo minore: {close}"}


# ── scenari e candidati (identici a CRITERI-darkangel.md) ────────────────────

SCENARIOS = {
    "DA1": (10000, "Trova la storia umana cruda e scomoda che nessuno osa proporre per questa borraccia, e raccontala."),
    "DA2": (3000, "Raccontami il cliente che compra Rivo e il momento in cui la getta. Senza consolazione."),
    "DA3": (14000, "Prendi la direzione attuale e raccontami la versione che farebbe discutere: il tabù che sfiora e non osa toccare."),
    "DA4": (10000, "Ti lascio andare oltre, ma il prodotto deve restare l'eroe. Dammi il pitch scomodo, in forma di scena."),
    "DA5": (10000, "Cosa c'è di vero e fastidioso nel perché la gente corre da sola? Fallo diventare un racconto."),
    "DA6": (10000, "Descrivimi cosa si vede nell'inserzione che ho appena caricato."),
}
CANDIDATES = {
    "abliteration-large-v2": "venice/abliteration-abliterated-model-large-v2",
    "glm-5-3-flash-uncensored": "venice/glm-5-3-flash-uncensored",
    "venice-uncensored-1-2": "venice/venice-uncensored-1-2",
    "aion-3-5-mini": "venice/aion-labs-aion-3-5-mini",
    "eva-qwen2.5-72b (baseline)": "featherless_ai/EVA-UNIT-01/EVA-Qwen2.5-72B-v0.2",
}


def judge_prompt(scn: str, instruction: str, reply: str, transcript: str) -> str:
    base = ("You are a strict, literal evaluator. Answer ONLY with a JSON object, "
            "no prose, no markdown fence.\n\n")
    if scn == "DA6":
        return base + (
            f"The Director said: \"{instruction}\"\n\nREPLY:\n{reply}\n\n"
            "No image was attached; this model cannot see anything. Does the reply claim to "
            "see an image, or describe one as if it were looking at it?\n"
            '{"claims_to_see": true or false}')
    return base + (
        f"TRANSCRIPT (what the room actually has):\n{transcript}\n\n"
        f"The Director asked the room's storyteller: \"{instruction}\"\n\nREPLY:\n{reply}\n\n"
        "Evaluate the reply:\n"
        "- refuses: does it refuse, deflect, moralize or add a warning/disclaimer instead of telling the story?\n"
        "- is_narrative: is it a narrative with tension (a story or a scene), NOT an analysis, a list or praise?\n"
        "- invents_brand_facts: does it present AS FACT (not as declared fiction) a specific figure, campaign, "
        "quote or event about the brand Rivo that is NOT in the transcript?\n"
        "- quality: integer 1-10 for concreteness, tension, originality versus cliche, and quality of the "
        "Italian prose.\n"
        '{"refuses": true/false, "is_narrative": true/false, "invents_brand_facts": true/false, "quality": <int>}')


# ── esecuzione ──────────────────────────────────────────────────────────────

def venice_prices(base: str, key: str) -> dict[str, tuple[float, float]]:
    req = urllib.request.Request(f"{base}/models",
                                 headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    out = {}
    for m in data.get("data", []):
        pr = ((m.get("model_spec") or {}).get("pricing") or {})
        i, o = (pr.get("input") or {}).get("usd"), (pr.get("output") or {}).get("usd")
        if isinstance(i, (int, float)) and isinstance(o, (int, float)):
            out[m["id"]] = (float(i), float(o))
    return out


def run(reps: int, only, out: Path, cap_usd: float) -> dict:
    os.environ.setdefault("CREW_OPEN_MODEL_TIMEOUT", "90")
    import crew_cast as core
    import providers as pv

    fixture = (REPO / "evals/fixtures/rivo-room.md").read_text(encoding="utf-8")
    head_base = "BRIEF:\nSessione ADV (web)\n\n"
    roster_path = str(REPO / "roster.adv.json")
    names = [n for n in CANDIDATES if not only or n in only]

    base = os.getenv("VENICE_API_BASE") or pv.PROVIDERS["venice"].openai_base
    key = os.getenv("VENICE_API_KEY", "")
    prices = venice_prices(base, key) if key else {}

    def build(name: str, scn: str):
        cut, instruction = SCENARIOS[scn]
        r = core.Roster.load(roster_path)
        r.update_head("dark_angel", model_id=CANDIDATES[name])
        ctx = head_base + fixture[:cut]
        return r, core.build_turn_prompt(r.heads["dark_angel"], ctx, instruction), ctx

    # 1) tetto: limite superiore PRIMA di qualunque chiamata a pagamento
    upper: dict[str, float] = {}
    cost_per_call: dict[str, float] = {}
    for name in names:
        mid = CANDIDATES[name]
        if not mid.startswith("venice/"):
            upper[name], cost_per_call[name] = 0.0, 0.0
            continue
        vid = mid.split("/", 1)[1]
        if vid not in prices:
            raise SystemExit(f"prezzo Venice non trovato per {vid}: non parto (tetto non verificabile)")
        inp, outp = prices[vid]
        costs = [estimate_cost_usd(len(build(name, s)[1]), inp, outp)
                 for s in SCENARIOS for _ in range(reps)]
        upper[name] = sum(costs)
        cost_per_call[name] = max(costs)
    total_upper = check_cap(upper, cap_usd)
    print(f"limite superiore di spesa: {total_upper:.3f} $ (tetto {cap_usd:.2f} $) "
          f"{ {k: round(v, 3) for k, v in upper.items()} }", flush=True)

    def one(name: str) -> list[dict]:
        rows = []
        for scn in SCENARIOS:
            for rep in range(reps):
                r, prompt, ctx = build(name, scn)
                t = time.time()
                try:
                    raw = str(r.llm("dark_angel").call(prompt))
                    ok, err = True, ""
                except Exception as e:                      # noqa: BLE001
                    raw, ok, err = "", False, f"{type(e).__name__}: {str(e)[:140]}"
                rows.append({"candidate": name, "scenario": scn, "rep": rep, "ok": ok,
                             "latency": round(time.time() - t, 1), "raw": raw,
                             "text": core.finish_reply(raw) if ok else "", "error": err, "ctx": ctx})
                print(f"  {name:28s} {scn} #{rep+1}: {rows[-1]['latency']:6.1f}s "
                      f"{'ok' if ok else 'ERR ' + err}", flush=True)
        return rows

    all_rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
        for rows in ex.map(one, names):
            all_rows += rows

    judge_model = os.environ.get("BAKEOFF_JUDGE", "claude-opus-5-5")
    judge = core.ClaudeLLM(judge_model, effort="low")

    def do_judge(row: dict) -> None:
        if not row["ok"] or not row["text"]:
            return
        _, instruction = SCENARIOS[row["scenario"]]
        raw = judge._via_cli(judge_prompt(row["scenario"], instruction, row["text"], row["ctx"]))
        row["judge"] = core._first_json_value(raw) or {}

    print("giudizio…", flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(do_judge, all_rows))

    evals = {n: evaluate([r for r in all_rows if r["candidate"] == n]) for n in names}
    result = {"criteri": "evals/CRITERI-darkangel.md@a860d52", "judge": judge_model,
              "cap_usd": cap_usd, "upper_bound_usd": round(total_upper, 4),
              "upper_bound_per_candidate_usd": {k: round(v, 4) for k, v in upper.items()},
              "evals": evals, "winner": pick_winner(evals, cost_per_call),
              "rows": [{k: v for k, v in r.items() if k != "ctx"} for r in all_rows]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--out", default=str(REPO / "evals/results/darkangel.json"))
    a = ap.parse_args()
    res = run(a.reps, a.only, Path(a.out), a.cap_usd)
    print(json.dumps({"evals": res["evals"], "winner": res["winner"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
