# Crew Team Ads

**A multi-model AI writers' room for ad & film creative briefs — with the human Director in the loop.**

One brief goes in upstream (brand + theme, no execution). A crew of specialists — each running on a **different model** (Claude, Gemini, Grok) — confronts it from different angles and hands the Director three distinct, ownable executional directions to choose from. The crew never picks the idea. The Director does.

Two ways to run the same cast:

- **`brainstorm_crew.py`** — a **structured** CrewAI run: a hierarchical crew with a Producer that delegates, three specialists, and a **Director checkpoint after every task** (approve, or type a note and the agent revises). Ends in a debrief chat.
- **`room.py`** — a **live** writers' room: you talk in plain language, a router-LLM decides who takes the floor, specialists answer in their own panes, share one room memory, and **talk to each other** when you tell them to.

```
                          ┌───────────────────────────┐
                          │   🎬  THE DIRECTOR (human) │
                          │   owns the brief · decides │
                          └────────────┬──────────────┘
                          brief ▼      ▲ dossier
                          ┌───────────────────────────┐
                          │  🧭 EXECUTIVE PRODUCER      │
                          │     Claude · orchestrates   │
                          │     (never picks the idea)  │
                          └───┬─────────┬─────────┬─────┘
                     ┌────────┘         │         └────────┐
              ┌──────▼──────┐   ┌───────▼──────┐   ┌───────▼───────┐
              │ 🧠 STRATEGIST│   │ 🎨 CREATIVE   │   │ 📡 SOCIAL &    │
              │  Brand truth │   │   DIRECTOR    │   │  PRECEDENTS   │
              │   Gemini     │   │   Claude      │   │   Grok        │
              └──────────────┘   └──────────────┘   └───────────────┘
        one brief upstream · three different minds · one dossier · the Director decides
```

## The cast

| Role | Model | Job |
|---|---|---|
| Executive Producer | Claude | Delegates, makes the specialists confront each other, packages the dossier. Never picks the winner. |
| Strategist | Gemini | The brand truth + the single human tension the theme unlocks. |
| Creative Director | Claude | Three genuinely different executional directions. |
| Social & Precedent Analyst | Grok | Genre grammar: the clichés to avoid, what stays ownable and social-first. |

No research tools are attached: agents reason from knowledge, they do **not** browse — so no invented statistics, campaign names, dates or numbers.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
```

Keys (see `.env.example`): `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY` (Grok goes through litellm, bundled with CrewAI).

## Run

```bash
python step1.py            # smallest possible CrewAI — learn the 5 pieces
python brainstorm_crew.py  # the full 3-model structured crew (Director checkpoints)
python room.py             # the live writers' room
```

For the **tmux mission-control view** (Director's console on top, one pane per agent, live):

```bash
./demo.sh                  # structured crew, mission-control view
./room.sh                  # live writers' room, mission-control view
```

The default brief is a **fictional example** (an invented maison, "AURELIA") so the repo runs out of the box — paste your own brief at launch to replace it.

## License

MIT — see [LICENSE](LICENSE).
