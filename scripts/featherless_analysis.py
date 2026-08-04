#!/usr/bin/env python3
"""Analisi dei modelli Featherless per la stanza ADV.

Cosa fa (serve FEATHERLESS_AI_API_KEY in ../.env):
1. scarica il catalogo modelli via API OpenAI-compatibile;
2. filtra i candidati adatti al lavoro creativo/uncensored (abliterated,
   instruct grossi, famiglie note) entro i limiti del piano Premium;
3. riporta per ognuno: id, taglia, finestra di contesto e — dove esposto —
   il tetto di output (il famoso 32k), così si vede chi lo supera davvero;
4. opzionale (--live): un prompt creativo identico a N candidati per
   confrontare la voce, con temperatura alta. Costa token/tempo: chiede
   conferma implicita col flag.

Uso:
  ../.venv/bin/python3 featherless_analysis.py            # solo catalogo
  ../.venv/bin/python3 featherless_analysis.py --live 4   # + confronto vivo
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://api.featherless.ai/v1"
HERE = Path(__file__).resolve().parent


def load_key() -> str:
    env = HERE.parent / ".env"
    if env.exists():
        for ln in env.read_text().splitlines():
            if ln.startswith("FEATHERLESS_AI_API_KEY="):
                return ln.split("=", 1)[1].strip()
    return os.getenv("FEATHERLESS_AI_API_KEY", "")


_UA = "Mozilla/5.0 (crew-team-ads featherless-analysis)"


def get(path: str, key: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"Authorization": f"Bearer {key}",
                                          "User-Agent": _UA,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def post(payload: dict, key: str) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=data,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json",
                                          "User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


# Famiglie note per copy creativo / senza freni (nel model_class o nell'id).
CREATIVE_FAMILIES = ("abliterated", "heretic", "uncensored", "magnum",
                     "euryale", "behemoth", "cydonia", "anubis", "dolphin",
                     "hermes", "nemo", "wizardlm", "storywriter", "writer",
                     "mytho", "midnight", "rocinante", "lumimaid", "tiefighter")
# Spazzatura da escludere sempre (fine-tune di massa, giocattoli).
JUNK = ("gensyn", "swarm", "grpo", "-0.5b", "0.5b-", "-1b", "1.5b", "-3b")


def _size_from_class(mc: str) -> int:
    """Miliardi di parametri stimati dal model_class (es. 'llama33-70b')."""
    m = re.search(r"(\d+)\s*b\b", mc.lower())
    return int(m.group(1)) if m else 0


def main() -> None:
    key = load_key()
    if not key:
        print("Nessuna FEATHERLESS_AI_API_KEY in ../.env — aggiungila e riprova.")
        sys.exit(1)

    models = get("/models", key).get("data", [])
    plan = [m for m in models if m.get("available_on_current_plan")]
    print(f"Catalogo: {len(models)} modelli · sul tuo piano: {len(plan)}\n")

    # La domanda sui 32k, con i dati: distribuzione del tetto di output.
    caps = {}
    for m in plan:
        c = m.get("max_completion_tokens")
        caps[c] = caps.get(c, 0) + 1
    print("Tetto di output (max_completion_tokens) sui modelli del piano:")
    for c, n in sorted(caps.items(), key=lambda x: -(x[1])):
        print(f"  {str(c):>8} token  →  {n} modelli")
    print()

    cand = []
    for m in plan:
        blob = (m.get("id", "") + " " + m.get("model_class", "")).lower()
        if any(j in blob for j in JUNK):
            continue
        fam = [f for f in CREATIVE_FAMILIES if f in blob]
        size = _size_from_class(m.get("model_class", ""))
        if fam and size >= 24:          # solo pesi massimi creativi
            m["_fam"] = fam
            m["_size"] = size
            cand.append(m)

    cand.sort(key=lambda m: (m["_size"], m.get("id")), reverse=True)
    print(f"Candidati creativi/uncensored (≥24B, sul piano): {len(cand)}\n")
    print(f"{'id':<54}{'classe':<16}{'B':>4}{'ctx':>8}{'out':>7}{'conc':>5}")
    print("-" * 94)
    for m in cand[:30]:
        print(f"{m['id'][:53]:<54}{m.get('model_class','')[:15]:<16}"
              f"{m['_size']:>4}{m.get('context_length','?'):>8}"
              f"{str(m.get('max_completion_tokens','?')):>7}"
              f"{m.get('concurrency_cost','?'):>5}")

    if "--live" in sys.argv:
        n = int(sys.argv[sys.argv.index("--live") + 1])
        top = [m.get("id") for m in cand[:n]]
        prompt = ("Sei un copywriter pubblicitario audace per un brand di denim. "
                  "Dammi UNA sola headline provocatoria e viscerale (max 8 parole) "
                  "per una campagna dark, e in una riga perché funziona. "
                  "Rispondi in italiano.")
        print(f"\n=== Confronto vivo su {len(top)} modelli ===")
        for mid in top:
            try:
                r = post({"model": mid,
                          "messages": [{"role": "user", "content": prompt}],
                          "temperature": 1.0, "max_tokens": 400}, key)
                txt = (r["choices"][0]["message"].get("content") or "").strip()
                print(f"\n--- {mid} ---\n{txt or '(vuoto)'}")
            except Exception as e:
                print(f"\n--- {mid} --- ERRORE: {e}")


if __name__ == "__main__":
    main()
