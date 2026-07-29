# Crew Room TUI — design

**Data:** 2026-07-28 · **Stato:** approvato dal Director (sessione di brainstorming)
**Origine:** `BUILD_BRIEF.md` — TUI custom per la writers' room multi-modello.
Requisiti R1–R7 e trappole T1–T6 sono definiti lì; questo documento fissa il *come*.

## Decisioni del Director

| Tema | Scelta |
|---|---|
| Layout | Colonna transcript threaded + colonna destra con card-stato per testa |
| Creatività | Slider 0–10 per testa + badge onesto sul meccanismo (`via temperature` / `via prompt`) |
| Collab mode | Linguaggio naturale («discutete fra voi per 5 giri») **e** comando `/auto N`; Esc interrompe; contatore visibile |
| Tasti/lingua | Chrome UI in italiano, agenti in inglese; F2 Roster · F3 Creatività · F4 Collab · Esc Interrompi · Ctrl+Q Esci |
| Architettura | **A** — `room_tui.py` nuovo + estensioni additive a `crew_cast.py`; `CAST` intatto |
| Chat private | Canale 1:1 per testa, **stagno** (la stanza non vede il privato, la testa in stanza non lo ricorda); ingresso: click sulla card o `/privato <testa>`, Esc torna in stanza |

## 1. File e responsabilità

- `room_tui.py` — **nuovo**: l'app Textual. Tutta la UI, zero definizioni di cast.
- `crew_cast.py` — estensioni **additive**: `Roster`, `route_plan()` (router a ondate),
  helper di creatività. `CAST`, `route()`, `speak()` ecc. restano intatti:
  `app.py` e `room.py` continuano a importare e girare (R7, §5.3 del brief).
- `roster.json` — persistenza del roster, accanto al progetto (R4).
- `transcripts/room-AAAAMMGG-HHMM.md` — transcript di stanza, salvato a ogni
  turno; `transcripts/private-<testa>-<sessione>.md` — chat private 1:1.
- `launcher.sh` — aggiornato: doppio click su `CrewRoom.app` → finestra Terminal
  con la TUI (via `osascript`; un .app da Finder non ha terminale).

## 2. Roster (R4)

Ogni testa è un dato, non una costante:

```json
{"key": "cd", "name": "Creative Director", "avatar": "🎨", "color": "orange3",
 "model_id": "anthropic/claude-opus-5", "persona": "…solo la parte di ruolo…",
 "creativity": 5}
```

- La persona salvata è **solo la parte di ruolo**; `ROOM_RULES` viene anteposto al
  momento di parlare — le regole di stanza restano centralizzate nel core.
- `Roster.load()`: legge `roster.json` se esiste, altrimenti deriva i 4 default da
  `CAST`. Ogni modifica salva su disco; effetto dal turno successivo, senza restart.
- Operazioni da F2: rinomina, edita persona, cambia modello, aggiungi testa,
  rimuovi testa. I 4 attuali sono il roster di default, non un roster fisso.
- Modelli scelti da lista verificata (T2): `anthropic/claude-opus-5`,
  `anthropic/claude-sonnet-5`, `gemini/gemini-3.1-pro-preview`, `xai/grok-4.5`.
- Le teste `anthropic/*` passano **sempre** da `core.ClaudeLLM`
  (subscription-first, env scrubbata — T4, R7). Gemini/Grok da `crewai.LLM`;
  Grok con `additional_drop_params=["stop"]` (T5).
- `roster.json` corrotto → backup del file rotto (`roster.json.bad`) e ripartenza
  dai default. Mai crashare all'avvio per un JSON malformato.

## 3. Creatività (R5, T1)

Slider 0–10 per testa. Mappatura per famiglia di modello:

- **Gemini / Grok** → `temperature` reale: `0.1 + livello × 0.11` (0→0.1, 10→1.2).
  Badge: `[via temperature 0.9]`. L'oggetto LLM si ricostruisce al cambio.
- **Claude 5** (rifiuta `temperature` — T1) → blocco di istruzioni graduato
  iniettato nella persona al momento di parlare, badge `[via prompt]`. Fasce:
  0–2 «stay with proven territory, flag anything unproven», 3–5 (default, nessuna
  iniezione: il comportamento di oggi), 6–8 «push past the obvious, propose at
  least one risky angle», 9–10 «take real risks; no safe ideas; the Director
  will pull you back if needed».
- Lo slider non mente mai: il badge dice sempre il meccanismo attivo per quella
  testa. Nessuno slider silenziosamente ignorato.

## 4. Router a ondate (R1, R3)

`route_plan(roster, transcript, msg)` estende il router attuale:

- Output: **ondate** — lista di liste. `[[strategist, social], [cd]]` =
  strategist e social in parallelo, poi il CD. Ogni passo:
  `{"speaker", "instruction", "to"}` dove `to` è `"director"` o la key di una
  testa (è ciò che rende il cross-talk disegnabile — R3).
- Il prompt del router elenca le teste **dal roster corrente** (non hardcoded):
  una testa aggiunta a runtime è instradabile subito.
- Il pattern X→Y→X (consulto) resta seriale per costruzione: ondate `[[X],[Y],[X]]`.
- Fallback (router in errore / JSON invalido): tutto seriale nell'ordine di oggi,
  poi keyword-match, poi producer — la catena attuale, mai peggio di oggi.
- Esecuzione: per ogni ondata, `asyncio.gather` di `asyncio.to_thread(llm.call, …)`
  (T3: mai bloccare l'event loop). Wall-clock ondata ≈ testa più lenta (R1).
  I risultati si appendono al transcript nell'ordine del piano (deterministico);
  le card mostrano il completamento man mano.

## 5. UI (R2, R3)

- **Transcript** (sinistra, scrollabile): voci threaded. Chi parla al Director:
  `🎨 Creative Director:`. Cross-talk: `🎨 CD → 📡 Social: …`. Eventi di sistema
  (ricerche approvate/negate, fallback API) in righe attenuate.
- **Card teste** (destra, una per testa dal roster): nome, modello, stato live
  (`· idle / ⚡ pensa / 🔍 cerca / ✎ parla / ⚠ errore`), mini-barra creatività,
  e `→ risponde a CD` durante il cross-talk.
- **Input** in basso; **footer** Textual con le F-keys.
- **Niente streaming token-per-token**: `crewai.LLM.call` e la CLI `claude` sono
  bloccanti. Gli *stati* sono vivi; il testo appare a turno completato. Onesto
  nella UI e in questo documento.
- Intake all'avvio: le 4 domande del brief (brand, theme, mandate, medium) →
  `core.build_brief()`, come oggi in Chainlit.

## 6. Gate di ricerca (R7)

Comportamento identico a oggi, presentazione nuova:

- `SEARCH_REQUEST` intercettata → **modal** con query e **perché** →
  `Approva / Nega / Riscrivi la query` (Riscrivi apre un campo input).
- Con turni paralleli, più richieste si accodano: **un modal alla volta**; le
  teste senza richiesta continuano a lavorare. La testa in attesa mostra
  `🔍 waiting approval`.
- Denied → `core.speak_after_search(key, transcript, why)` (la testa dichiara
  cosa non ha potuto verificare). Approved → `core.web_search()` →
  `core.speak_after_search(…, query, results)`.
- Il gate resta attivo in collab mode: il giro si ferma sul modal.

## 7. Collab mode (R6)

- Trigger: parsing del messaggio del Director («discutete/parlatene fra voi …
  N giri») **oppure** `/auto N`; `/auto` senza numero = tetto di sicurezza
  **20 giri** (hard stop, non si corre via).
- Banner visibile: `AUTO — giro k/N — Esc per interrompere`.
- Ogni giro: il router sceglie chi risponde all'ultima battuta, con `to` = testa
  precedente; il gate di ricerca resta in mezzo.
- Esc interrompe **sempre** (anche a metà giro: il turno in volo si completa,
  il giro successivo non parte) e restituisce la parola al Director.
- Esc vale anche fuori dalla collab mode: annulla le ondate non ancora partite
  del piano corrente (i turni in volo si completano — le chiamate LLM bloccanti
  non sono cancellabili a metà senza perdere il turno).
- Esc è contestuale: in vista privata torna in stanza; in stanza interrompe
  collab/ondate. La priorità è sempre «un Esc ti riporta al controllo».

## 7-bis. Chat private 1:1

Ogni testa ha un canale privato col Director, invisibile al resto della stanza.

- **Ingresso/uscita:** click sulla card della testa oppure `/privato <testa>`
  (alias delle key: `cd`, `strategist`, …). La colonna transcript diventa la
  chat privata — banner `🔒 PRIVATO — <nome>`, bordo dedicato, prompt `🔒 >`.
  Esc torna in stanza. Il router è bypassato: si parla solo con quella testa.
- **Stagno, in entrambe le direzioni che contano:** il contenuto privato non
  entra mai nel transcript condiviso né nel contesto dei turni in stanza —
  nei turni pubblici la testa **non ricorda** le chat private (garanzia dura:
  il contesto pubblico semplicemente non le contiene). Le altre teste non le
  vedono mai.
- **Contesto in privato:** la testa vede il transcript della stanza (per non
  parlare nel vuoto) + la storia privata col Director, con un preambolo
  esplicito: «This is a private sidebar with the Director. The rest of the
  room cannot see this conversation.»
- **Gate di ricerca attivo anche in privato** (stesso modal); i risultati
  restano nel canale privato.
- **Persistenza:** `transcripts/private-<testa>-<sessione>.md`, salvata a ogni
  turno come la stanza. La chat privata sopravvive dentro la sessione; a nuova
  sessione riparte pulita (come il transcript di stanza).
- Mentre sei in privato, i turni di stanza già in volo continuano e le card
  restano vive; l'input di stanza riprende quando torni con Esc. La creatività
  della testa (slider) vale anche in privato.

## 8. Errori

- Testa che fallisce → riga `[non disponibile: …]` nel transcript, card `⚠ errore`,
  la stanza va avanti (come oggi).
- Claude in fallback API a pagamento (`core.last_claude_route() == "api"`) →
  avviso una-tantum nel transcript + indicatore persistente nella card (💳).
- Transcript salvato a ogni turno, non all'uscita: un crash non perde la sessione.

## 9. Test e verifica (§4 del brief)

- Chiamate **reali** micro («Reply with exactly: OK») per ciascun modello del
  roster e per `route_plan` — mai mock, prompt minuscoli.
- Smoke test UI con il pilot di Textual (`run_test()`).
- Demo finale: sessione reale con brief reale, R1–R7 dimostrati (§5.2).
- `app.py` e `room.py` ancora importabili e funzionanti dopo l'estensione (§5.3).

## 10. Fuori scope

Web app / server / Electron / Tauri; `brainstorm_crew.py`; streaming token-level;
Serper o altre ricerche a chiave (T6: si resta su `ddgs`).
