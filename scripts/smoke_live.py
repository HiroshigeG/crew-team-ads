"""Smoke test LIVE — chiamate reali, prompt micro (costo ~zero).
Va lanciato a mano: .venv/bin/python3 scripts/smoke_live.py
Verifica: ogni modello del roster risponde; il router a ondate produce un
piano sensato; Claude passa dalla subscription (T4/R7)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import crew_cast as core

missing = core.missing_keys()
if missing:
    raise SystemExit(f"Chiavi mancanti: {missing}")

roster = core.Roster.default()

for key in roster.keys():
    head = roster.heads[key]
    out = str(roster.llm(key).call("Reply with exactly: OK")).strip()
    route = (f" [{core.last_claude_route()}]"
             if head.model_id.startswith("anthropic/") else "")
    print(f"{head.avatar} {head.name:28} {head.model_id:32} -> {out[:40]!r}{route}")

waves = core.route_plan(roster, "BRIEF: test.\n",
                        "strategist e social, un pensiero a testa sul tema; "
                        "poi il cd tira le fila")
print("\nroute_plan:")
for i, wave in enumerate(waves, 1):
    for s in wave:
        print(f"  ondata {i}: {s['speaker']:12} -> {s['to']:10} | {s['instruction'][:60]}")
