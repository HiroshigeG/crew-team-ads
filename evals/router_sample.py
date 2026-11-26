"""Campione del router a ondate: quante risposte reali il parser accetta (D36).

Solo CLI di Claude in abbonamento (`ClaudeLLM._via_cli`): nessuna chiamata API,
nessuna spesa a consumo. Il prompt è costruito esattamente come `route_plan`
(PLAN_PROMPT, roster di produzione, transcript con il messaggio del Director già
in coda, come fa `handle_director`). Per ogni risposta: piano valido o scartato,
forma del JSON (ondate annidate o array piatto) e speaker buttati.

Uso:  .venv/bin/python -m evals.router_sample [N] [file di uscita]
      N ripetizioni per scenario (default 15 -> 60 chiamate, 4 in parallelo).
"""
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import crew_cast as cc  # noqa: E402

BRIEF = ("Ecco il brief della campagna. Stanza, reagite.\n\n"
         "PROJECT: Aumentare del 20% le vendite online della borraccia Rivo 600 ml entro Natale\n"
         "BUDGET: 50.000 €\nTARGET: Runner urbani 25-40 anni, corrono da soli\n"
         "KPI: Ricerche del marchio e vendite online")
Q = ("Queste sono le campagne che per noi sono andate male. Dite in due righe cosa NON "
     "dobbiamo ripetere e se la direzione attuale rischia di ripeterlo.")
AUTO = ("AUTO MODE round 1: continue the discussion among yourselves. React to what "
        "Market Researcher just said — agree, attack or build. Do not address the Director.")
GOAL = ("GOAL MODE round 1: work toward this goal set by the Director — \"un claim per la "
        "borraccia Rivo che rispetti le nostre guideline e parli al runner che corre da solo\". "
        "React to what the Director just said; push the work closer to the goal. Do not "
        "address the Director.")


def scenarios() -> dict:
    fixture = open(os.path.join(REPO, "evals", "fixtures", "rivo-room.md"), encoding="utf-8").read()
    cut = ("BRIEF:\nSessione ADV (web)\n\n" + fixture)[:14000]
    return {
        "brief": ("BRIEF:\nSessione ADV (web)\n\nDirector: " + BRIEF + "\n", BRIEF),
        "domanda": (cut + f"Director: {Q}\n", Q),
        "auto": (cut, AUTO),
        "goal": (cut, GOAL),
    }


def shape(data) -> str:
    if isinstance(data, list) and data and all(isinstance(w, list) for w in data):
        return "nested"
    return "flat" if isinstance(data, list) else type(data).__name__


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "evals", "results", "router-sample.json")
    roster = cc.Roster.load(os.path.join(REPO, "roster.adv.json"))
    keys = set(roster.keys())
    cast_lines = "\n".join(f"- {h.key}: {h.name} — {h.persona.strip()[:90]}"
                           for h in roster.heads.values())
    scen = scenarios()

    def one(job):
        name, i = job
        tr, msg = scen[name]
        prompt = cc.PLAN_PROMPT.format(cast_lines=cast_lines,
                                       transcript=tr[-cc.ROUTER_CONTEXT_CHARS:], msg=msg)
        t = time.time()
        try:
            raw, err = cc.llm_claude_router._via_cli(prompt), ""
        except Exception as e:  # noqa: BLE001 - si registra, non si nasconde
            raw, err = "", f"{type(e).__name__}: {e}"
        data = cc._first_json_value(raw) if raw else None
        proposed = []
        if isinstance(data, list):
            for w in data:
                for s in (w if isinstance(w, list) else [w]):
                    proposed.append(s.get("speaker") if isinstance(s, dict) else s)
        return {"scen": name, "i": i, "s": round(time.time() - t, 1),
                "ok": bool(cc.parse_wave_plan(raw, keys)) if raw else False, "err": err,
                "shape": shape(data), "dropped": [p for p in proposed if p not in keys],
                "raw": raw[:600]}

    jobs = [(s, i) for i in range(n) for s in scen]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, jobs))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for s in scen:
        r = [x for x in res if x["scen"] == s]
        print(f"{s:8s} validi {sum(x['ok'] for x in r)}/{len(r)}  forme {dict(Counter(x['shape'] for x in r))}"
              f"  errori {sum(bool(x['err']) for x in r)}  speaker buttati {sum(len(x['dropped']) for x in r)}"
              f"  max {max(x['s'] for x in r)}s")
    print(f"totale validi {sum(x['ok'] for x in res)}/{len(res)} -> {out}")


if __name__ == "__main__":
    main()
