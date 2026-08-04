# ADV Room

**A multi-model AI writers' room for advertising campaigns — with the human
Director in the loop, in the browser.**

One brief goes in. A cast of nine specialist heads — each on its **own model**
(Claude, Gemini, Grok, and open 72B models via Featherless/OpenRouter) —
confronts it from different angles in a live room: they answer in parallel
waves, consult each other, ask permission before touching the web, and hand
the Director distinct, ownable directions. The room never picks the idea.
The Director does.

```
                 ┌────────────────────────────────┐
                 │    🎬  THE DIRECTOR (human)     │
                 │    owns the brief · decides     │
                 └───────────────┬────────────────┘
                          brief ▼  ▲ dossier
   ┌─────────────────────────────────────────────────────────┐
   │                      THE ROOM (web)                     │
   │  🔎 research · 🧠 strategy · 🎨 creative direction        │
   │  ✍️ copy (magnum) · 🖋️ copy 2 (Claude) · 📡 social        │
   │  🧭 producer · 🖤 dark storyteller · 💼 account           │
   │  parallel waves · agent-to-agent turns · HITL gates     │
   └─────────────────────────────────────────────────────────┘
```

## What makes it a room, not a chat

- **Wave routing**: a router-LLM plans who speaks, in which order, and who
  can run **in parallel**; consults (X→Y→X) stay sequential. The timeline
  shows agent-to-agent turns from the router's own `to` field — never from
  text heuristics.
- **Human-in-the-loop everywhere**: web searches wait behind a gate
  (approve · rewrite · deny, one at a time, fail-closed); proposals carry
  versions with word-level diff; stop lets in-flight turns finish and
  cancels the queue.
- **Two copywriters engineered as a pair**: an uncensored 72B ("the liquid":
  first heat, voice, the line nobody dares) against Claude at max effort
  ("the container": judgment, claims, final hand) — see
  `docs/recon/E-copy-pair.md` for the research behind it.
- **Collab modes**: fixed rounds (`/auto N`) or **free-running** — the heads
  keep talking until the room runs dry (a head with nothing new passes;
  two all-pass rounds close the run; a hard cap guards the bill).
- **Bench**: toggle any head in or out of the meeting; benched heads are
  not routed but remain reachable in private 1:1 chat (watertight — the
  room never sees it).
- **Social intelligence**: the social analyst can request a web search, use
  Grok's native live search on X (opt-in), or query an **external social
  tool** through a configurable command — same HITL gate, different backend
  (`scripts/social_tool_*.py` show how to plug a TikTok analysis pipeline).
- **Honest states**: per-head live status (with readable error reasons),
  a "degraded routing" banner with @mentions as the escape hatch,
  per-turn `subscription`/`API` billing badges.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
.venv/bin/uvicorn server.main:app --port 8000    # → http://localhost:8000
```

**No keys in the repo — ever.** On first access the room shows a setup
screen asking for the API keys it needs (Anthropic, Gemini, xAI; Featherless
and OpenRouter optional) and writes them to a local, gitignored `.env` next
to the server. Alternatively, copy `.env.example` to `.env` and fill it in
by hand.

UI development: `cd web && npm run dev` (proxies to `:8000`); engine-less
demo: `http://localhost:5173/?demo=1`.

## Architecture

| Layer | What | Where |
|---|---|---|
| Engine | roster, wave router, search gates, creativity dial, sessions | `crew_cast.py` |
| Contract | typed events, TS+Python 1:1, WebSocket | `docs/EVENT-CONTRACT.md` |
| Bridge | FastAPI + WebSocket, one connection = one room | `server/main.py` |
| UI | React + Tailwind, three resizable columns, dark | `web/` |

The engine is the only brain; the web app renders, it doesn't think. Every
decision (D1–D25) is on the record in `docs/DECISIONS.md`, with the
reconnaissance that led to it in `docs/recon/`.

Claude heads run **subscription-first** (local CLI, metered API only as a
transparent fallback); Gemini and Grok bill per token; open models ride a
flat Featherless plan or OpenRouter credits. The default cast and the
reasoning behind every model choice live in `roster.adv.json`.

## Tests

```bash
.venv/bin/python3 -m pytest tests/   # engine + server contract, offline
cd web && npm test                   # UI event-folding, vitest
```

## License

MIT — see [LICENSE](LICENSE).
