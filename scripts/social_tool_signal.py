#!/usr/bin/env python3
"""Esempio di tool "social intel" (D23) — legge un signal.json GIA' prodotto dal
TikTok Viral Analyzer e ne stampa un digest compatto su stdout.

È il backend leggero (gratis, niente scrape): la stanza consulta l'analisi già
fatta. Si aggancia con, nel .env di crew-team-ads:

    CREW_SOCIAL_TOOL_CMD=".venv/bin/python3 scripts/social_tool_signal.py"
    TIKTOK_ANALYZER_DIR="/percorso/al/tuo/tiktok-viral-analyzer"

Il motore passa la query come ULTIMO argomento. Qui il file è uno solo, quindi
la query serve da contesto (e da filtro se combacia col brand del signal).

Nessun percorso è cablato: l'analyzer si indica con TIKTOK_ANALYZER_DIR — così
il repo pubblico resta pulito e portabile.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _signal_path() -> Path:
    base = os.getenv("TIKTOK_ANALYZER_DIR")
    if not base:
        raise SystemExit("[social tool: set TIKTOK_ANALYZER_DIR al tuo analyzer]")
    # SIGNAL_FILE opzionale se il file non si chiama signal.json.
    return Path(base) / (os.getenv("TIKTOK_SIGNAL_FILE") or "signal.json")


def build_digest(query: str) -> str:
    p = _signal_path()
    if not p.is_file():
        return f"[social tool: {p.name} non trovato in TIKTOK_ANALYZER_DIR]"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[social tool: {p.name} illeggibile: {e}]"

    meta = d.get("meta", {}) or {}
    seg = d.get("segnale", {}) or {}
    ins = d.get("insight", {}) or {}
    dire = d.get("direzione", {}) or {}
    out: list[str] = []

    subj = meta.get("subject") or ", ".join(meta.get("brands", []) or []) or "?"
    out.append(f"TIKTOK SIGNAL — soggetto: {subj} "
               f"({meta.get('n_videos', '?')} video, {meta.get('generated_at', '?')})")
    if query:
        out.append(f"(richiesta della stanza: {query})")
    if meta.get("sample_note"):
        out.append(f"Nota campione: {meta['sample_note']}")

    pats = seg.get("winning_patterns") or []
    if pats:
        out.append("\nPATTERN VINCENTI:")
        for pt in pats[:5]:
            out.append(f"- {pt.get('pattern', pt) if isinstance(pt, dict) else pt}")

    deltas = seg.get("baseline_delta") or []
    if deltas:
        out.append("\nDELTA TOP vs BOTTOM:")
        for de in deltas[:6]:
            if isinstance(de, dict):
                out.append(f"- {de.get('dimension','?')}: vincono «{de.get('winners','?')}» "
                           f"su «{de.get('losers','?')}» — {de.get('delta_note','')}")

    ovb = ins.get("owners_vs_brand") or {}
    if ovb:
        out.append(f"\nOWNER vs BRAND: owner {ovb.get('owner_share_pct','?')}% · "
                   f"brand {ovb.get('brand_share_pct','?')}%")

    voice = ins.get("audience_voice") or []
    if voice:
        out.append("\nVOCE DEL PUBBLICO (cluster):")
        for v in voice[:6]:
            if isinstance(v, dict):
                out.append(f"- {v.get('cluster','?')} [{v.get('sentiment','?')}, "
                           f"vol {v.get('volume','?')}]")

    brief = dire.get("brief") or {}
    if brief:
        out.append("\nDIREZIONE PROPOSTA:")
        for k in ("title", "thesis", "concept", "hook_formula"):
            if brief.get(k):
                out.append(f"- {k}: {brief[k]}")
    moves = dire.get("next_moves") or []
    if moves:
        out.append("\nPROSSIME MOSSE:")
        for m in moves[:5]:
            out.append(f"- {m}")

    return "\n".join(out).strip() or "[social tool: signal vuoto]"


def main() -> None:
    query = sys.argv[-1] if len(sys.argv) > 1 else ""
    print(build_digest(query))


if __name__ == "__main__":
    main()
