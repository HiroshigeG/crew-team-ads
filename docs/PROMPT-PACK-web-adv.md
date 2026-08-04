# Prompt pack — Crew Web (app ADV multi-agente con Human-in-the-Loop)

Serie di prompt da dare a Claude Code, uno per fase, dentro una sessione tmux.
Scritti il 03/08/2026.

---

## Premessa da leggere prima di lanciare qualsiasi cosa

**Assunzione presa** (cambiala qui se sbagliata, tutto il resto ne discende):
la web app **sostituisce Chainlit** (`app.py`) e convive con la TUI
(`room_tui.py`). Il terminale resta per chi lavora in terminale; il browser
diventa la superficie per le sessioni ADV con cliente. Se invece deve
sostituire la TUI, cancella la Fase 6 e aggiungi la dismissione di `room_tui.py`.

**Il backend esiste già.** È `crew_cast.py`, 741 righe, 80 test verdi. Nessun
prompt qui dentro dice «costruisci un backend CrewAI»: dicono «esponi quello
che c'è». Superficie disponibile:

| Funzione / classe | A cosa serve in UI |
|---|---|
| `Roster`, `Head` | lista agenti: nome, avatar, colore, modello, persona, creatività |
| `route_plan(roster, transcript, msg)` | ondate: chi parla, in parallelo, e **`to`** = a chi risponde |
| `head_speak()` · `head_speak_after_search()` | il turno di un agente |
| `parse_search_request()` · `web_search()` | il gate di ricerca (SEARCH_REQUEST) |
| `RoomSession` | transcript persistito → storico sessioni |
| `parse_auto_request()` · `requested_rounds()` | collab mode («discutete fra voi per N giri») |
| `temp_for_level()` · `creativity_block()` | slider creatività 0–10, con meccanismo onesto |
| `ClaudeLLM` · `last_claude_route()` | abbonamento vs API a pagamento, per turno |
| `missing_keys()` | validazione all'avvio |

**Regole trasversali — incollale in fondo a OGNI prompt:**

```
Vincoli non negoziabili:
- Non duplicare la logica di crew_cast.py. Importalo. Se manca qualcosa,
  aggiungi in modo ADDITIVO senza cambiare firme esistenti.
- Non rompere room_tui.py e i suoi 80 test: `.venv/bin/python3 -m pytest tests/ -q`
  deve restare verde. Girala prima di dire che hai finito.
- Niente chiavi API, niente percorsi /Users/, niente nomi di clienti reali nel
  codice o nei dati mock. Questo repo è pubblico (HiroshigeG/crew-team-ads).
- Python: sempre .venv/bin/python3, mai python3 di sistema.
- Se un requisito ti sembra sbagliato, fermati e dillo prima di implementarlo.
```

---

## Fase 0 — Ricognizione (3 agenti in parallelo, nessun codice scritto)

> Prima di scrivere una riga voglio tre ricognizioni indipendenti. Non
> modificare nessun file: produci tre documenti in `docs/recon/`.
>
> **Agente A — Contratto del core.** Leggi `crew_cast.py` per intero e scrivi
> `docs/recon/A-core-contract.md`: ogni funzione e classe pubblica con firma
> esatta, tipo di ritorno e forma reale dei dati (per `route_plan` mostra un
> esempio vero di ondata con il campo `to`; per `parse_search_request` la
> tripla). Segna quali funzioni sono bloccanti (chiamate LLM) e vanno quindi
> fuori dal thread della UI. Segna cosa NON esiste e servirebbe.
>
> **Agente B — Ricognizione componenti.** Vai su https://21st.dev e cerca
> componenti React+Tailwind riusabili per: chat timeline con avatar e
> raggruppamento per autore, blocco di conferma/approvazione, card di stato con
> indicatore live, sidebar collassabile, pannello a tre colonne ridimensionabile,
> effetto typing/streaming. Per ognuno scrivi in `docs/recon/B-componenti.md`:
> nome, URL, **licenza**, dipendenze che tira dentro, e un giudizio secco
> «prendere / adattare / lasciare» con una riga di motivo. Guarda anche
> https://component.gallery ma solo come riferimento di pattern, non come
> sorgente di codice. **Verifica e riporta** se queste sono effettivamente fuori
> dal nostro stack React web, come credo: pub.dev/packages/fluent_ui e
> forui.dev (Flutter), reactnativereusables.com e github.com/nativeui-org/ui
> (React Native). Se mi sbaglio su una, dillo.
>
> **Agente C — Cosa salvare da Chainlit.** Leggi `app.py` e scrivi
> `docs/recon/C-chainlit.md`: quali comportamenti sono giusti e vanno
> replicati (intake delle 4 domande, gate di ricerca, gestione errori), e quali
> sono i tre limiti che BUILD_BRIEF.md §2 gli imputa. Elenca cosa si può
> riusare letteralmente.
>
> Nessuno dei tre scrive codice applicativo.

---

## Fase 1 — Roster dei 5 agenti + contratto degli eventi

> Due deliverable, nessuna UI ancora.
>
> **1. `roster.adv.json`** — un roster alternativo con i cinque ruoli qui sotto,
> nella forma che `Roster.load()` già si aspetta (`key`, `name`, `avatar`,
> `color`, `model_id`, `persona`, `creativity`). La `persona` contiene **solo la
> parte di ruolo**: `ROOM_RULES` viene anteposto dal core, non ripeterlo.
> Modelli solo da questa lista verificata: `anthropic/claude-opus-5`,
> `anthropic/claude-sonnet-5`, `gemini/gemini-3.1-pro-preview`, `xai/grok-4.5`.
> Distribuiscili con criterio e scrivi in un commento perché quel modello per
> quel ruolo.
>
> Le personas, da usare testuali:
>
> - **market_researcher** 🔎 — *You are the Market Researcher: you map the
>   audience and the competitive field — who we are talking to, what they
>   already believe, and what rivals have actually run. You deal in evidence,
>   not vibes: when a claim about a competitor or a market would change the
>   room's direction and you cannot verify it, ask to search rather than guess.
>   You leave concept and copy to others.*
> - **creative_strategist** 🧠 — *You are the Creative Strategist: you turn the
>   research into the angle — the human tension the campaign unlocks and the
>   territory the brand can own. Give the room two or three genuinely different
>   angles, not variations of one. You leave headlines to the Copywriter and
>   channels to the Media Planner.*
> - **copywriter** ✍️ — *You are the Copywriter: you write the actual words —
>   headline, subhead, body — in the brand's voice, tight enough to survive a
>   feed. You write to the angle the Strategist chose; if the angle is unclear,
>   ask for it rather than inventing one. Never pad, and never write a headline
>   you cannot defend in one line.*
> - **media_planner** 📊 — *You are the Media Planner: you decide where the work
>   runs and how the budget splits — channels, formats, flighting — always
>   against the stated budget and KPI. Say what you would cut first if the
>   budget dropped by 30%. You leave the creative to others, and never invent
>   benchmark numbers you cannot verify.*
> - **performance_analyst** 📉 — *You are the Performance Analyst: you are the
>   room's cold eye. State expected KPI ranges, the assumptions behind them, and
>   the two or three ways this plan most plausibly fails. Flag any number in the
>   room that nobody has verified. Never approve your own optimism.*
>
> Valuta se tenere anche `producer` come sesta testa che sintetizza e impacchetta
> il dossier senza mai scegliere l'idea (è il comportamento attuale del core).
> Consiglia tu, motivando in una riga.
>
> **2. `docs/EVENT-CONTRACT.md`** — il protocollo WebSocket fra server e
> browser, definito **sulle funzioni reali** censite dall'Agente A. Un evento per
> ogni cosa che la UI deve poter disegnare, con payload tipizzato:
> ondata pianificata · turno iniziato (con `to`) · token in streaming · turno
> completato · richiesta di ricerca in attesa · esito ricerca · cambio di stato
> di una testa (`idle` `thinking` `speaking` `searching` `waiting_approval`
> **`error`**) · **degrado del router** · rotta del turno (`subscription` |
> `api`) · sessione salvata. Definisci anche i messaggi browser→server:
> messaggio del Director, verdetto sul gate (approva/nega/riscrivi), stop,
> modifica roster, cambio creatività.
>
> Gli stati `error` e il degrado del router **non sono opzionali**: sono la
> lezione della sessione del 03/08, in cui il router è morto in silenzio e per
> un'ora è sembrato che un modello sano fosse rotto.
>
> Scrivi il contratto in TypeScript (tipi) e in Python (dataclass o TypedDict),
> le due metà devono corrispondere una a una.

---

## Fase 2 — Guscio UI a tre colonne, dati finti

> Costruisci la UI completa in React + TypeScript + Tailwind + lucide-react +
> Framer Motion, in `web/`. **Solo dati mock**, nessuna chiamata di rete: i mock
> però devono avere **esattamente la forma del contratto della Fase 1**, così il
> collegamento della Fase 3 è una sostituzione, non una riscrittura.
>
> Layout: sidebar contesto ~280px · timeline centrale · workspace proposte ~340px.
>
> - **Sinistra**: nome campagna · brief editabile (obiettivo, budget, target,
>   KPI) · le 5 card agente con avatar colorato, ruolo, stato live e barra
>   creatività · riepilogo decisioni presE.
> - **Centro**: timeline cronologica unica dove agenti e umano parlano insieme.
>   Avatar, nome, badge ruolo, timestamp. Quando un agente risponde a un altro,
>   disegna la relazione (`Creative Strategist → Copywriter`) usando il campo
>   `to`, non euristiche sul testo. Messaggi dell'umano visivamente distinti.
>   Blocchi lunghi fra soli agenti collassabili. Input sempre visibile in basso.
>   Streaming con effetto typing.
> - **Destra**: card proposta (concept · headline+copy · canali e split budget ·
>   stima performance e rischi) con azioni rapide, sezione «Versione finale» e
>   pulsante esporta.
>
> Stile: dark mode di default, ispirazione Linear + Discord + Notion. Tipografia
> con gerarchia vera. Animazioni leggere. Responsive: sotto i 1024px la sidebar
> diventa drawer e il workspace scende sotto.
>
> Usa i componenti approvati dall'Agente B in `docs/recon/B-componenti.md`,
> rispettandone la licenza e citando la fonte in un commento. Non installare
> librerie fuori da quell'elenco senza dirmelo.
>
> I dati mock: una campagna ADV inventata (marca di fantasia, mai un cliente
> reale) con almeno 20 messaggi che mostrino discussione fra agenti, una
> richiesta di ricerca in attesa, un blocco HITL aperto, un agente in `error`.
>
> **Fatto quando**: `npm run build` passa, la pagina gira, e ogni stato del
> contratto è visibile almeno una volta nei mock.

---

## Fase 3 — Ponte verso il core vero

> Sostituisci i mock con il backend reale. Server FastAPI in `server/`, WebSocket
> sul contratto della Fase 1, che **importa `crew_cast.py`** e non reimplementa
> nulla.
>
> - Le chiamate LLM sono bloccanti: `asyncio.to_thread`, mai sull'event loop.
> - Le ondate di `route_plan()` girano in parallelo con `asyncio.gather`:
>   il wall-clock di un'ondata deve essere ≈ la testa più lenta, non la somma.
> - Una sessione = una `RoomSession`, il transcript si salva a ogni turno.
> - All'avvio, `missing_keys()`: se manca una chiave, la UI lo dice in chiaro
>   invece di fallire al primo turno.
>
> **Fatto quando**: un brief reale attraversa tutto il giro, cinque agenti
> rispondono, e il transcript su disco combacia con quello che si legge a schermo.

---

## Fase 4 — Gate di ricerca, HITL e stati di degrado

> Il pezzo che la specifica originale non aveva, ed è il più prezioso.
>
> **Gate di ricerca.** Quando un turno finisce con `SEARCH_REQUEST`, la UI mostra
> un blocco evidenziato con la **query** e il **perché**, e tre azioni: approva ·
> nega · riscrivi la query. Approva → `web_search()` → `head_speak_after_search()`.
> Nega → la testa parla comunque e deve dichiarare cosa non ha potuto verificare.
> Con turni paralleli le richieste si accodano: **una alla volta**, le altre
> teste continuano a lavorare e chi aspetta mostra `waiting_approval`.
>
> **HITL sulle proposte.** Blocco giallo/arancione con domanda chiara e quattro
> pulsanti grandi: Approva · Modifica · Chiedi alternative · Rifiuta. «Modifica»
> apre un campo e la modifica rientra nel transcript come intervento del Director.
>
> **Stati di degrado** — priorità massima:
> - una testa che fallisce va in `error` sulla card, **con il motivo leggibile**;
> - se il router non risponde, banner di sistema: «instradamento ridotto — usa
>   @menzione per scegliere chi parla», e le @menzioni devono funzionare davvero;
> - ogni turno mostra un badge `abbonamento` o `API` da `last_claude_route()`;
> - **niente `except: pass`**. Ogni eccezione ingoiata va almeno loggata: è
>   esattamente il difetto che ha reso non diagnosticabile il guasto del 03/08.
>
> **Stop.** Un pulsante ferma tutto: i turni in volo si completano, le ondate non
> ancora partite non partono, la parola torna al Director.

---

## Fase 5 — Il sorpasso

> Le cose che la specifica non chiedeva e che rendono l'app migliore della
> richiesta. Implementale in quest'ordine, fermandoti quando dico basta.
>
> 1. **Chat private 1:1** con una testa, stagne: la stanza non le vede e la
>    testa in stanza non se ne ricorda. Ingresso col click sulla card.
> 2. **Collab mode**: «discutete fra voi per N giri» o `/auto N`, con contatore
>    visibile, tetto duro a 20 giri e stop sempre disponibile. Il gate di ricerca
>    resta attivo dentro il giro.
> 3. **Roster editabile a runtime**: rinomina, cambia persona, cambia modello,
>    aggiungi o togli una testa. Effetto dal turno successivo, senza restart.
>    Cinque agenti sono il default, non un vincolo.
> 4. **Diff della Versione Finale**: a ogni decisione approvata, evidenzia cosa
>    è cambiato rispetto alla versione precedente.
> 5. **Storico sessioni** dai transcript di `RoomSession`, riapribili in lettura.
> 6. **Filtro della timeline per agente** e ricerca testuale nel transcript.
> 7. **Costo e rotta della sessione**: quanti turni da abbonamento, quanti da API.
> 8. **Esporta campagna**: Markdown e PDF, con brief, decisioni, versione finale
>    e la lista delle ricerche approvate con le fonti.

---

## Fase 6 — Verifica e consegna

> Nessuna funzione nuova. Solo:
>
> - test del server sul contratto degli eventi (ondate parallele, coda del gate,
>   degrado del router, stop a metà ondata);
> - test dei componenti UI sugli stati, incluso `error`;
> - `.venv/bin/python3 -m pytest tests/ -q` verde: gli 80 test della TUI non
>   devono aver perso un colpo;
> - `README.md` aggiornato: tre facciate sullo stesso motore (TUI, web, e cosa
>   è successo a Chainlit), con l'avvio di ognuna;
> - sweep di sanificazione prima di qualunque push: nessun `/Users/`, nessuna
>   chiave, nessun nome di cliente, autore `HiroshigeG`.
>
> Riporta l'output vero dei comandi, non un riassunto.
