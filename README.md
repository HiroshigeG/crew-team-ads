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

## Le due facce dello stesso motore

`crew_cast.py` è il cervello unico — router a ondate, gate di ricerca,
roster editabile, sessioni persistite. Nessuna faccia lo reimplementa:
tutte lo renderizzano.

| Faccia | Per chi | Avvio |
|---|---|---|
| **TUI** (`room_tui.py`) | chi lavora in terminale | `.venv/bin/python3 room_tui.py` |
| **Web / ADV Room** (`server/` + `web/`) | le sessioni ADV col cliente | `.venv/bin/uvicorn server.main:app --port 8000` → `http://localhost:8000` |

**Quando usare quale.** Non sono due porte sulla stessa stanza: sono due
stanze. La **TUI è il laboratorio** — da soli, a mani sporche: brainstorm
veloci, prove di personas e creatività, lavoro sul motore; carica
`roster.json` (il cast base a 4 teste) e vive di tastiera. La **web è la
sala riunioni** — quando qualcuno guarda o il risultato va consegnato:
carica `roster.adv.json` (il cast da campagna a 9 teste), rende cliccabile
ogni decisione davanti a testimoni (gate, proposte, versioni col diff) e ha
le cose da riunione: export del dossier, storico, filtri, chat private.
Regola in una riga: *da soli → Terminale; con un cliente accanto o un
dossier da consegnare → browser.*

## La stanza in terminale (room_tui.py)

Avvio: `.venv/bin/python3 room_tui.py` (un launcher cliccabile, se lo vuoi,
è un `.app` locale di poche righe: non viaggia col repo).

- **Brief**: 4 domande all'avvio, poi la stanza è tua. Parla a tutti o a
  qualcuno (`cd: …`, `cd, chiedi a social …`).
- **Ondate**: le teste indipendenti rispondono in parallelo; i consulti
  (X→Y→X) restano in sequenza, con la freccia `→` nel transcript.
- **F2 Roster**: rinomina, cambia persona/modello, aggiungi o togli teste.
  Persistito in `roster.json` — riapri e ritrovi la tua stanza.
- **F3 Creatività**: 0–10 per testa. Gemini/Grok: `temperature` reale;
  Claude 5 la rifiuta, quindi la manopola inietta istruzioni nel prompt —
  il badge dice sempre quale meccanismo è attivo.
- **F4 / «discutete fra voi per N giri» / `/auto N`**: collab mode — le
  teste discutono da sole, contatore a video, Esc ferma, tetto 20 giri.
- **Click su una card / `/privato cd`**: chat privata 1:1, stagna — la
  stanza non la vede e la testa non la ricorda nei turni pubblici.
- **🔍**: ogni ricerca web resta dietro il tuo permesso (query + perché).
- Transcript in `transcripts/`, salvato a ogni turno.

## La stanza nel browser (server/ + web/)

La faccia per le sessioni ADV con il cliente accanto: tre colonne
(contesto · timeline · proposte), dark, nove teste di default
(`roster.adv.json`). Un solo processo serve tutto:

```bash
cd web && npm install && npm run build && cd ..   # solo la prima volta
.venv/bin/uvicorn server.main:app --port 8000     # poi http://localhost:8000
```

Al **primo accesso** la stanza ti chiede le chiavi API che mancano e le
scrive nel `.env` locale accanto al server (gitignorato: non entrano mai nel
repo). In alternativa: copia `.env.example` in `.env` e compilalo a mano.

- **Contratto eventi**: server e browser parlano il protocollo di
  `docs/EVENT-CONTRACT.md` (WebSocket, eventi tipizzati TS+Python 1:1).
- **Timeline agente-agente**: chi risponde a chi viene dal campo `to` del
  router, mai da euristiche sul testo; scambi lunghi fra soli agenti
  collassabili; filtro per testa e ricerca testuale.
- **HITL ovunque**: gate di ricerca (approva · riscrivi · nega, uno alla
  volta), decisione sulle proposte con diff fra versioni, stop che lascia
  finire i turni in volo e ferma le ondate in coda.
- **Stati onesti**: card con lo stato vivo di ogni testa (errore col motivo
  leggibile), banner «instradamento ridotto» con le **@menzioni** come via
  d'uscita (`@cd`, `@copy`, …), badge `abbonamento`/`API` per turno.
- **In più della TUI**: chat private 1:1 stagne, collab mode con contatore
  (tetto 20 giri), storico sessioni in sola lettura, export campagna in
  Markdown/PDF con le fonti delle ricerche approvate.
- Sviluppo UI: `cd web && npm run dev` (proxy su `:8000`); demo senza motore:
  `http://localhost:5173/?demo=1`. Test: `npm test` (vitest) e
  `tests/test_server.py` (contratto, offline).

## Che fine ha fatto Chainlit (app.py)

È stata la prima faccia web ed è stata **rimossa**: la ADV Room la sostituisce
in tutto (era una chat lineare — niente ondate parallele a video, niente
cross-talk visibile, nessuna vista di stanza — e usava ancora l'API v1 del
core). I suoi comportamenti buoni (intake, gate di ricerca fail-closed, errori
contenuti per testa) vivono nella web app; la diagnosi che ne ha decretato la
fine resta in `docs/recon/C-chainlit.md`, e il codice nella storia git.
