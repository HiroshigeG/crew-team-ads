#!/usr/bin/env python3
"""Esempio di tool "social intel" (D23) — variante PESANTE: lancia la pipeline
del TikTok Viral Analyzer per una nuova analisi e poi ne stampa il digest.

⚠️  Costa (Apify + Gemini) e richiede minuti: l'analyzer NON è una search box, è
una pipeline brand-config (ingest → analyze → build_signal). Questo wrapper la
esegue e poi riusa il digest di social_tool_signal.py.

Si aggancia con, nel .env di crew-team-ads:

    CREW_SOCIAL_TOOL_CMD=".venv/bin/python3 scripts/social_tool_scrape.py"
    TIKTOK_ANALYZER_DIR="/percorso/al/tuo/tiktok-viral-analyzer"
    # I passi ESATTI della TUA pipeline, separati da ';'. {q} = la query della
    # stanza (di solito la chiave del brand nel config dell'analyzer).
    TIKTOK_PIPELINE_CMDS="python ingest.py --brand {q}; python analyze.py; python build_signal.py"
    CREW_SOCIAL_TOOL_TIMEOUT=600   # lo scrape è lento: alza il tetto

La query arriva come ULTIMO argomento. Nessun percorso è cablato nel repo.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

# Riusa il lettore del signal: stesso digest, così la stanza vede lo stesso
# formato che leggerebbe dal file già pronto.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from social_tool_signal import build_digest  # noqa: E402


def main() -> None:
    query = sys.argv[-1] if len(sys.argv) > 1 else ""
    base = os.getenv("TIKTOK_ANALYZER_DIR")
    if not base:
        print("[social tool: set TIKTOK_ANALYZER_DIR al tuo analyzer]")
        return
    steps = os.getenv("TIKTOK_PIPELINE_CMDS")
    if not steps:
        print("[social tool: set TIKTOK_PIPELINE_CMDS coi passi della tua "
              "pipeline, es. 'python ingest.py --brand {q}; python analyze.py; "
              "python build_signal.py']")
        return
    timeout = int(os.getenv("CREW_SOCIAL_TOOL_TIMEOUT") or 600)
    for raw in steps.split(";"):
        cmd = raw.strip().replace("{q}", query)
        if not cmd:
            continue
        try:
            r = subprocess.run(shlex.split(cmd), cwd=base, capture_output=True,
                               text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"[social tool: passo «{cmd}» oltre {timeout}s, interrotto]")
            return
        except Exception as e:
            print(f"[social tool: passo «{cmd}» non eseguibile: {e}]")
            return
        if r.returncode != 0:
            print(f"[social tool: passo «{cmd}» rc={r.returncode}: "
                  f"{(r.stderr or '').strip()[:300]}]")
            return
    # Pipeline finita: emetti il digest del signal appena prodotto.
    print(build_digest(query))


if __name__ == "__main__":
    main()
