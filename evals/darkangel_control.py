"""Controllo non-abliterated di Dark Angel (Opus 5.5 e Sonnet 5.5 da CLI).

Segue `evals/PROVA-CIECA-darkangel-controllo.md` (commit 701e95e). Nessuna
spesa: solo CLI in abbonamento, mai il fallback API. Uso:

    .venv/bin/python3 -m evals.darkangel_control --out evals/results/darkangel-control.json
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

from evals.darkangel_bakeoff import SCENARIOS, judge_prompt  # noqa: E402

CONTROLS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5"}
USE = ("DA1", "DA3", "DA5")


def run(out: Path, effort: str = "medium") -> dict:
    os.environ.setdefault("CREW_CLAUDE_TIMEOUT", "180")
    import crew_cast as core

    fixture = (REPO / "evals/fixtures/rivo-room.md").read_text(encoding="utf-8")
    head_base = "BRIEF:\nSessione ADV (web)\n\n"
    roster_path = str(REPO / "roster.adv.json")

    def build(name: str, scn: str):
        cut, instruction = SCENARIOS[scn]
        r = core.Roster.load(roster_path)
        r.update_head("dark_angel", model_id=f"anthropic/{CONTROLS[name]}")
        ctx = head_base + fixture[:cut]
        return core.build_turn_prompt(r.heads["dark_angel"], ctx, instruction), ctx

    def one(job):
        name, scn = job
        prompt, ctx = build(name, scn)
        t = time.time()
        try:
            raw = core.ClaudeLLM(CONTROLS[name], effort=effort)._via_cli(prompt)   # mai API
            ok, err = True, ""
        except Exception as e:                                  # noqa: BLE001
            raw, ok, err = "", False, f"{type(e).__name__}: {str(e)[:140]}"
        print(f"  {name:7s} {scn}: {time.time()-t:5.1f}s {'ok' if ok else 'ERR ' + err}", flush=True)
        return {"candidate": name, "scenario": scn, "ok": ok, "latency": round(time.time() - t, 1),
                "raw": raw, "text": core.finish_reply(raw) if ok else "", "error": err, "ctx": ctx}

    jobs = [(n, s) for n in CONTROLS for s in USE]
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        rows = list(ex.map(one, jobs))

    judge = core.ClaudeLLM(os.environ.get("BAKEOFF_JUDGE", "claude-opus-5-5"), effort="low")

    def do_judge(row):
        if not row["ok"] or not row["text"]:
            return
        _, instruction = SCENARIOS[row["scenario"]]
        raw = judge._via_cli(judge_prompt(row["scenario"], instruction, row["text"], row["ctx"]))
        row["judge"] = core._first_json_value(raw) or {}

    print("controllo automatico dei rifiuti…", flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(do_judge, rows))

    res = {"protocollo": "evals/PROVA-CIECA-darkangel-controllo.md@701e95e", "effort": effort,
           "rows": [{k: v for k, v in r.items() if k != "ctx"} for r in rows]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "evals/results/darkangel-control.json"))
    ap.add_argument("--effort", default="medium")
    a = ap.parse_args()
    res = run(Path(a.out), a.effort)
    for r in res["rows"]:
        j = r.get("judge") or {}
        print(r["candidate"], r["scenario"], f"{len(r['text'].split())} parole",
              f"rifiuta={j.get('refuses')} narra={j.get('is_narrative')} inventa={j.get('invents_brand_facts')}")


if __name__ == "__main__":
    main()
