"""Dark Angel, menù di tre idee: tutti i modelli rigenerati da zero.

Segue `evals/PROVA-CIECA-darkangel-menu.md` (commit 826729e). Venice a crediti con
limite superiore di spesa imposto (rifiuta di partire sopra il tetto); i modelli
Claude solo da CLI in abbonamento, mai il fallback API. Uso:

    .venv/bin/python3 -m evals.darkangel_menu --cap-usd 0.25 --out evals/results/darkangel-menu.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from evals.darkangel_bakeoff import (  # noqa: E402
    check_cap, estimate_cost_usd, has_reasoning_leak, venice_prices,
)
from evals.producer_bakeoff import italian_ratio, word_count  # noqa: E402

FORMAT = ("Dammi TRE idee diverse, numerate 1, 2, 3, ciascuna di al massimo 50 parole, "
          "su tre angoli diversi tra loro e da quello che la stanza sta già battendo. "
          "Niente premesse né commenti: solo le tre idee.")

SCENARIOS = {
    "DN1": (10000, "Qual è l'idea più scomoda per vendere questa borraccia, quella che nessun brand di running oserebbe firmare?"),
    "DN2": (3000, "Che cosa direbbe di Rivo il cliente più cinico, e come ne facciamo un annuncio?"),
    "DN3": (14000, "Prendi la direzione attuale e rovesciala: la stessa verità, vista da chi non corre."),
}
CANDIDATES = {
    "glm": ("venice", "venice/glm-5-3-flash-uncensored"),
    "aion": ("venice", "venice/aion-labs-aion-3-5-mini"),
    "opus": ("cli", "claude-opus-5-5"),
    "sonnet": ("cli", "claude-sonnet-5-5"),
}

from guardrails import parse_ideas  # noqa: E402  (un solo parser: lo stesso del guardrail)


def check_format(raw: str, text: str) -> dict:
    ideas = parse_ideas(text)
    return {
        "n_ideas": len(ideas),
        "three_ideas": len(ideas) == 3,
        "max_words": max((word_count(i) for i in ideas), default=0),
        "short_enough": bool(ideas) and all(word_count(i) <= 60 for i in ideas),
        "italian": italian_ratio(text) >= 0.70 if text else False,
        "leak": has_reasoning_leak(raw),
    }


def run(out: Path, cap_usd: float, temperature: float = 0.9, effort: str = "medium") -> dict:
    os.environ.setdefault("CREW_OPEN_MODEL_TIMEOUT", "120")
    os.environ.setdefault("CREW_CLAUDE_TIMEOUT", "180")
    import crew_cast as core
    import providers as pv

    fixture = (REPO / "evals/fixtures/rivo-room.md").read_text(encoding="utf-8")
    head_base = "BRIEF:\nSessione ADV (web)\n\n"
    roster_path = str(REPO / "roster.adv.json")

    def build(name: str, scn: str):
        cut, ask = SCENARIOS[scn]
        kind, model = CANDIDATES[name]
        r = core.Roster.load(roster_path)
        r.update_head("dark_angel", model_id=model if kind == "venice" else f"anthropic/{model}")
        ctx = head_base + fixture[:cut]
        return r, core.build_turn_prompt(r.heads["dark_angel"], ctx, f"{ask} {FORMAT}")

    # tetto: limite superiore PRIMA di qualunque chiamata a pagamento
    base = os.getenv("VENICE_API_BASE") or pv.PROVIDERS["venice"].openai_base
    key = os.getenv("VENICE_API_KEY", "")
    prices = venice_prices(base, key) if key else {}
    upper: dict[str, float] = {}
    for name, (kind, model) in CANDIDATES.items():
        if kind != "venice":
            upper[name] = 0.0
            continue
        vid = model.split("/", 1)[1]
        if vid not in prices:
            raise SystemExit(f"prezzo Venice non trovato per {vid}: non parto")
        inp, outp = prices[vid]
        upper[name] = sum(estimate_cost_usd(len(build(name, s)[1]), inp, outp) for s in SCENARIOS)
    total = check_cap(upper, cap_usd)
    print(f"limite superiore di spesa: {total:.3f} $ (tetto {cap_usd:.2f} $) "
          f"{ {k: round(v, 3) for k, v in upper.items()} }", flush=True)

    def one(name: str) -> list[dict]:
        rows = []
        for scn in SCENARIOS:
            r, prompt = build(name, scn)
            kind, model = CANDIDATES[name]
            t = time.time()
            try:
                if kind == "cli":
                    raw = core.ClaudeLLM(model, effort=effort)._via_cli(prompt)       # mai API
                else:
                    llm = r.llm("dark_angel")
                    llm.temperature = temperature
                    raw = str(llm.call(prompt))
                ok, err = True, ""
            except Exception as e:                                 # noqa: BLE001
                raw, ok, err = "", False, f"{type(e).__name__}: {str(e)[:140]}"
            text = core.finish_reply(raw) if ok else ""
            rows.append({"candidate": name, "scenario": scn, "ok": ok,
                         "latency": round(time.time() - t, 1), "raw": raw, "text": text,
                         "ideas": parse_ideas(text), "format": check_format(raw, text), "error": err})
            print(f"  {name:7s} {scn}: {rows[-1]['latency']:6.1f}s idee={len(rows[-1]['ideas'])} "
                  f"{'ok' if ok else 'ERR ' + err}", flush=True)
        return rows

    with cf.ThreadPoolExecutor(max_workers=len(CANDIDATES)) as ex:
        rows = [r for part in ex.map(one, list(CANDIDATES)) for r in part]
    res = {"protocollo": "evals/PROVA-CIECA-darkangel-menu.md@826729e", "temperature": temperature,
           "effort": effort, "upper_bound_usd": round(total, 4), "cap_usd": cap_usd, "rows": rows}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--out", default=str(REPO / "evals/results/darkangel-menu.json"))
    a = ap.parse_args()
    run(Path(a.out), a.cap_usd)


if __name__ == "__main__":
    main()
