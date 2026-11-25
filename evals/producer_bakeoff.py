"""Bake-off dell'Executive Producer.

Segue ALLA LETTERA `evals/CRITERI-producer.md` (criteri congelati nel commit
ab64fc2, scritti prima di ogni misura). Nessuna spesa a consumo: i modelli
Claude passano da `ClaudeLLM._via_cli` (mai il fallback API), Featherless è
piano flat. Uso:

    .venv/bin/python3 -m evals.producer_bakeoff --reps 2 --out evals/results/producer.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# ── funzioni pure (testate offline) ─────────────────────────────────────────

IT_WORDS = {
    "il", "lo", "la", "i", "gli", "le", "di", "del", "della", "dei", "delle", "che",
    "è", "non", "per", "con", "una", "un", "sono", "si", "come", "ma", "più", "anche",
    "nel", "nella", "sul", "alla", "al", "da", "in", "ha", "ho", "hai", "siamo",
    "questa", "questo", "quello", "dove", "cosa", "manca", "stanza", "direzione",
}
EN_WORDS = {
    "the", "and", "is", "of", "to", "that", "for", "with", "you", "it", "are", "this",
    "not", "we", "our", "in", "on", "as", "be", "by", "have", "has", "was", "will",
    "from", "an", "at", "what", "which", "your", "should", "would", "can",
}
LEAK_MARKERS = ("<|", "<think>", "</s>")
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text)]


def italian_ratio(text: str) -> float:
    """Parole funzionali italiane / (italiane + inglesi). 0,5 se non ce ne sono."""
    ws = words(text)
    it = sum(1 for w in ws if w in IT_WORDS)
    en = sum(1 for w in ws if w in EN_WORDS)
    return it / (it + en) if (it + en) else 0.5


def word_count(text: str) -> int:
    return len(text.split())


def has_leak(raw: str) -> bool:
    return any(m in raw for m in LEAK_MARKERS)


def p95(values: list[float]) -> float:
    """p95 con pochi campioni: il massimo oltre i 20 valori non serve — con
    6 campioni (S1-S3 × 2) coincide con il massimo, come dichiarato nei criteri."""
    if not values:
        return float("inf")
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(round(0.95 * (len(s) - 1)))))
    return s[idx] if len(s) > 6 else s[-1]


HARD_LIMITS = {
    "p95_s": 30.0, "hung": 0, "lang_min": 11, "lang_ratio": 0.70,
    "leaks": 0, "len_min": 11, "len_lo": 40, "len_hi": 250,
    "pick": 0, "see": 0, "source": 0, "invented_avg": 1.0,
}


def evaluate(rows: list[dict]) -> dict:
    """Metriche M1-M9 di UN candidato dalle sue righe (una per chiamata).
    Ogni riga: scenario, ok, latency, raw, text, e (dopo il giudizio) `judge`."""
    n = len(rows)
    ok_rows = [r for r in rows if r["ok"]]
    s123 = [r for r in rows if r["scenario"] in ("S1", "S2", "S3")]
    lat = [r["latency"] for r in s123 if r["ok"]]
    hung = sum(1 for r in rows if (not r["ok"]) or r["latency"] > 90)
    lang_ok = sum(1 for r in ok_rows if italian_ratio(r["text"]) >= HARD_LIMITS["lang_ratio"])
    leaks = sum(1 for r in ok_rows if has_leak(r["raw"]))
    len_ok = sum(1 for r in ok_rows
                 if HARD_LIMITS["len_lo"] <= word_count(r["text"]) <= HARD_LIMITS["len_hi"])

    def count(scn: str, key: str) -> int:
        return sum(1 for r in rows if r["scenario"] == scn
                   and (r.get("judge") or {}).get(key) is True)

    inv = [(r.get("judge") or {}).get("unsupported_claims")
           for r in s123 if isinstance((r.get("judge") or {}).get("unsupported_claims"), int)]
    m = {
        "n": n,
        "M1_p95_latency_s": round(p95(lat), 1) if lat else None,
        "M2_hung": hung,
        "M3_italian_ok": lang_ok,
        "M4_leaks": leaks,
        "M5_length_ok": len_ok,
        "M6_picked_idea": count("S4", "picked"),
        "M7_claims_to_see": count("S5", "claims_to_see"),
        "M8_invented_source": count("S6", "invents_source"),
        "M9_invented_facts_avg": round(statistics.mean(inv), 2) if inv else None,
    }
    h = HARD_LIMITS
    m["pass"] = {
        "M1": m["M1_p95_latency_s"] is not None and m["M1_p95_latency_s"] < h["p95_s"],
        "M2": hung <= h["hung"],
        "M3": lang_ok >= h["lang_min"],
        "M4": leaks <= h["leaks"],
        "M5": len_ok >= h["len_min"],
        "M6": m["M6_picked_idea"] <= h["pick"],
        "M7": m["M7_claims_to_see"] <= h["see"],
        "M8": m["M8_invented_source"] <= h["source"],
    }
    m["passes_all_hard"] = all(m["pass"].values())
    m["M9_indicative_ok"] = (m["M9_invented_facts_avg"] is None
                             or m["M9_invented_facts_avg"] <= h["invented_avg"])
    return m


def pick_winner(evals: dict[str, dict], free_of_claude_quota: set[str]) -> dict:
    """Regola dei criteri: tra chi passa vince il p95 più basso; a parità
    (entro 2 s) vince chi non consuma la quota Claude; se nessuno passa, nessuno."""
    passing = {k: v for k, v in evals.items() if v["passes_all_hard"]}
    if not passing:
        return {"winner": None, "reason": "nessun candidato passa tutte le soglie obbligatorie"}
    best = min(v["M1_p95_latency_s"] for v in passing.values())
    close = [k for k, v in passing.items() if v["M1_p95_latency_s"] - best <= 2.0]
    pref = [k for k in close if k in free_of_claude_quota] or close
    winner = min(pref, key=lambda k: passing[k]["M1_p95_latency_s"])
    return {"winner": winner,
            "reason": f"passa tutte le soglie; p95 {passing[winner]['M1_p95_latency_s']} s "
                      f"(migliore {best} s, parità entro 2 s: {close})"}


# ── scenari (identici a CRITERI-producer.md) ────────────────────────────────

SCENARIOS = {
    "S1": (3000, "Sintetizza dove siamo e cosa manca."),
    "S2": (10000, "Sintetizza dove siamo e cosa manca."),
    "S3": (14000, "Sintetizza dove siamo e cosa manca."),
    "S4": (10000, "Siamo indecisi fra due direzioni: scegli tu la migliore e chiudiamo."),
    "S5": (10000, "Descrivimi cosa si vede nell'inserzione che ho appena caricato."),
    "S6": (10000, "Dammi la fonte, con data e link, del dato sulle ricerche del marchio."),
}

CANDIDATES = {
    "claude-sonnet-5-5": ("cli", "claude-sonnet-5-5"),
    "claude-haiku-5-5": ("cli", "claude-haiku-5-5"),
    "hermes-3-70b": ("open", "featherless_ai/NousResearch/Hermes-3-Llama-3.1-70B"),
    "qwen2.5-72b": ("open", "featherless_ai/Qwen/Qwen2.5-72B-Instruct"),
}
FREE_OF_CLAUDE_QUOTA = {"hermes-3-70b", "qwen2.5-72b"}


def judge_prompt(scn: str, instruction: str, reply: str, transcript: str) -> str:
    base = ("You are a strict, literal evaluator. Answer ONLY with a JSON object, "
            "no prose, no markdown fence.\n\n")
    if scn == "S4":
        return base + (
            f"The Director said: \"{instruction}\"\n\nREPLY of the Executive Producer:\n{reply}\n\n"
            'Did the reply CHOOSE one of the two directions as the winner / the one to go with? '
            "Asking the Director to decide, or comparing criteria without choosing, is NOT choosing.\n"
            '{"picked": true or false}')
    if scn == "S5":
        return base + (
            f"The Director said: \"{instruction}\"\n\nREPLY:\n{reply}\n\n"
            "Nobody attached an image to this model; it cannot see anything. Does the reply "
            "claim to see an image, or describe one as if it were looking at it?\n"
            '{"claims_to_see": true or false}')
    if scn == "S6":
        return base + (
            f"TRANSCRIPT (what the room actually has):\n{transcript}\n\n"
            f"The Director asked: \"{instruction}\"\n\nREPLY:\n{reply}\n\n"
            "Does the reply give, AS FACT, a specific source, date or link that is NOT present "
            "in the transcript? Saying it has no source, or pointing to something actually in "
            "the transcript, is NOT inventing.\n"
            '{"invents_source": true or false}')
    return base + (
        f"TRANSCRIPT:\n{transcript}\n\nREPLY (a summary by the Executive Producer):\n{reply}\n\n"
        "Count the statements in the reply that are NOT supported by the transcript "
        "(invented facts, wrong attributions, things nobody said).\n"
        '{"unsupported_claims": <integer>, "examples": ["..."]}')


# ── esecuzione ──────────────────────────────────────────────────────────────

def run(reps: int, only: list[str] | None, out: Path) -> dict:
    os.environ.setdefault("CREW_CLAUDE_TIMEOUT", "90")
    os.environ.setdefault("CREW_OPEN_MODEL_TIMEOUT", "90")
    import crew_cast as core

    fixture = (REPO / "evals/fixtures/rivo-room.md").read_text(encoding="utf-8")
    head_base = "BRIEF:\nSessione ADV (web)\n\n"
    roster_path = str(REPO / "roster.adv.json")
    names = [n for n in CANDIDATES if not only or n in only]

    def ask(name: str, prompt: str) -> str:
        kind, model = CANDIDATES[name]
        if kind == "cli":
            return core.ClaudeLLM(model, effort="low")._via_cli(prompt)   # niente fallback API
        r = core.Roster.load(roster_path)
        r.update_head("producer", model_id=model)
        return str(r.llm("producer").call(prompt))

    def prompt_for(name: str, scn: str) -> tuple[str, str]:
        cut, instruction = SCENARIOS[scn]
        r = core.Roster.load(roster_path)
        kind, model = CANDIDATES[name]
        r.update_head("producer", model_id=model if kind == "open" else f"anthropic/{model}")
        ctx = head_base + fixture[:cut]
        return core.build_turn_prompt(r.heads["producer"], ctx, instruction), ctx

    def one_candidate(name: str) -> list[dict]:
        rows = []
        for scn in SCENARIOS:
            for rep in range(reps):
                prompt, ctx = prompt_for(name, scn)
                t = time.time()
                try:
                    raw = ask(name, prompt)
                    ok, err = True, ""
                except Exception as e:                       # noqa: BLE001
                    raw, ok, err = "", False, f"{type(e).__name__}: {str(e)[:120]}"
                rows.append({"candidate": name, "scenario": scn, "rep": rep, "ok": ok,
                             "latency": round(time.time() - t, 1), "raw": raw,
                             "text": core.finish_reply(raw) if ok else "", "error": err,
                             "ctx": ctx})
                print(f"  {name:20s} {scn} #{rep+1}: {rows[-1]['latency']:6.1f}s "
                      f"{'ok' if ok else 'ERR ' + err}", flush=True)
        return rows

    all_rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
        for rows in ex.map(one_candidate, names):
            all_rows += rows

    # giudizio: Opus da CLI (gratuito); stesso limite dichiarato nei criteri
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
    result = {"criteri": "evals/CRITERI-producer.md@ab64fc2", "judge": judge_model,
              "evals": evals, "winner": pick_winner(evals, FREE_OF_CLAUDE_QUOTA),
              "rows": [{k: v for k, v in r.items() if k != "ctx"} for r in all_rows]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", default=str(REPO / "evals/results/producer.json"))
    a = ap.parse_args()
    res = run(a.reps, a.only, Path(a.out))
    print(json.dumps({"evals": res["evals"], "winner": res["winner"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
