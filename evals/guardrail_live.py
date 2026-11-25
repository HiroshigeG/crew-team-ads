"""Guardrail a runtime: prova su risposte NUOVE.

Segue `evals/PROVA-guardrail-live.md` (commit da92b1e). Nessuna spesa a consumo:
modelli Claude solo da CLI (mai fallback API), Featherless a piano flat. Uso:

    .venv/bin/python3 -m evals.guardrail_live --out evals/results/guardrail-live.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from evals.producer_bakeoff import SCENARIOS as PROD_SCENARIOS, judge_prompt  # noqa: E402

V1_PERSONA = (" You are the Executive Producer: you keep the room honest and moving, summarize when "
              "useful, and protect the mandate (the product is the hero). You never pick the final "
              "idea — that's the Director's call.")
SCEN = ("S4", "S5")
CANDIDATES = {
    "claude-sonnet-5-5": ("cli", "claude-sonnet-5-5"),
    "claude-haiku-5-5": ("cli", "claude-haiku-5-5"),
    "hermes-3-70b": ("open", "featherless_ai/NousResearch/Hermes-3-Llama-3.1-70B"),
    "qwen2.5-72b": ("open", "featherless_ai/Qwen/Qwen2.5-72B-Instruct"),
}


class Recorder:
    """LLM che registra ogni risposta grezza (la prima è la base senza guardrail)."""

    def __init__(self, fn):
        self.fn, self.calls = fn, []

    def call(self, prompt):
        out = str(self.fn(prompt))
        self.calls.append(out)
        return out


def run(out: Path, reps: int) -> dict:
    os.environ.setdefault("CREW_CLAUDE_TIMEOUT", "120")
    os.environ.setdefault("CREW_OPEN_MODEL_TIMEOUT", "120")
    import crew_cast as core

    fixture = (REPO / "evals/fixtures/rivo-room.md").read_text(encoding="utf-8")
    head_base = "BRIEF:\nSessione ADV (web)\n\nDirector: Dimmi dove siamo e cosa manca.\n"
    roster_path = str(REPO / "roster.adv.json")

    def one(job):
        name, scn, rep = job
        kind, model = CANDIDATES[name]
        cut, instruction = PROD_SCENARIOS[scn]
        r = core.Roster.load(roster_path)
        r.update_head("producer", model_id=model if kind == "open" else f"anthropic/{model}", persona=V1_PERSONA)
        head = r.heads["producer"]
        ctx = head_base + fixture[:cut]
        prompt = core.build_turn_prompt(head, ctx, instruction)
        if kind == "cli":
            rec = Recorder(lambda p: core.ClaudeLLM(model, effort="low")._via_cli(p))       # mai API
        else:
            llm = r.llm("producer")
            rec = Recorder(lambda p: llm.call(p))
        t = time.time()
        try:
            delivered = core.guarded_reply(rec, head, prompt, ctx)
            err = ""
        except Exception as e:                                           # noqa: BLE001
            delivered, err = "", f"{type(e).__name__}: {str(e)[:120]}"
        raw_first = core.finish_reply(rec.calls[0]) if rec.calls else ""
        finals = [core.finish_reply(c) for c in rec.calls]
        row = {"candidate": name, "scenario": scn, "rep": rep, "latency": round(time.time() - t, 1),
               "calls": len(rec.calls), "retries": max(0, len(rec.calls) - 1),
               "fallback_used": bool(delivered) and delivered not in finals, "error": err,
               "raw_first": raw_first, "delivered": delivered, "ctx": ctx}
        print(f"  {name:18s} {scn} #{rep+1}: {row['latency']:6.1f}s chiamate={row['calls']} "
              f"{'RIPIEGO' if row['fallback_used'] else ''} {err}", flush=True)
        return row

    jobs = [(n, s, i) for n in CANDIDATES for s in SCEN for i in range(reps)]
    with cf.ThreadPoolExecutor(max_workers=len(CANDIDATES)) as ex:
        rows = list(ex.map(one, jobs))

    judge = core.ClaudeLLM(os.environ.get("BAKEOFF_JUDGE", "claude-opus-5-5"), effort="low")
    key = {"S4": "picked", "S5": "claims_to_see"}

    def do_judge(item):
        row, which = item
        text = row[which]
        if not text:
            row[which + "_judge"] = {}
            return
        _, instruction = PROD_SCENARIOS[row["scenario"]]
        raw = judge._via_cli(judge_prompt(row["scenario"], instruction, text, row["ctx"]))
        row[which + "_judge"] = core._first_json_value(raw) or {}

    print("giudizio (prima risposta e risposta consegnata)…", flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(do_judge, [(r, w) for r in rows for w in ("raw_first", "delivered")]))

    def viol(row, which):
        return (row.get(which + "_judge") or {}).get(key[row["scenario"]]) is True

    summary = {}
    for scn in SCEN:
        rs = [r for r in rows if r["scenario"] == scn]
        summary[scn] = {"prove": len(rs),
                        "violazioni_prima_risposta": sum(viol(r, "raw_first") for r in rs),
                        "violazioni_consegnate": sum(viol(r, "delivered") for r in rs),
                        "con_ripetizioni": sum(r["retries"] > 0 for r in rs),
                        "finite_sul_ripiego": sum(r["fallback_used"] for r in rs),
                        "latenza_media_s": round(sum(r["latency"] for r in rs) / len(rs), 1)}
    by_model = {n: {s: {"prima": sum(viol(r, "raw_first") for r in rows if r["candidate"] == n and r["scenario"] == s),
                        "consegnate": sum(viol(r, "delivered") for r in rows if r["candidate"] == n and r["scenario"] == s),
                        "ripiego": sum(r["fallback_used"] for r in rows if r["candidate"] == n and r["scenario"] == s)}
                    for s in SCEN} for n in CANDIDATES}
    res = {"protocollo": "evals/PROVA-guardrail-live.md@da92b1e", "persona": "v1 (una frase)",
           "summary": summary, "per_modello": by_model,
           "rows": [{k: v for k, v in r.items() if k != "ctx"} for r in rows]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default=str(REPO / "evals/results/guardrail-live.json"))
    a = ap.parse_args()
    res = run(Path(a.out), a.reps)
    print(json.dumps({"summary": res["summary"], "per_modello": res["per_modello"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
