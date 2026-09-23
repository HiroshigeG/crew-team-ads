# EVENT-CONTRACT — protocollo WebSocket fra server e browser

**Versione protocollo: 1** · Fase 1 della web app ADV (vedi `docs/DECISIONS.md` D1).
Definito sulle funzioni reali di `crew_cast.py` censite in
`docs/recon/A-core-contract.md` (citata sotto come «recon A»). Il core non si
duplica: il server orchestra le chiamate e traduce in eventi; il browser
disegna e basta.

## 1. Trasporto e convenzioni

- **WebSocket, un oggetto JSON per frame.** Il campo `type` è il discriminante,
  su entrambe le direzioni.
- **Una connessione = una sessione di stanza** (una `RoomSession`). Riconnessione
  e ripresa di sessioni salvate sono fuori contratto in v1 (il core non sa
  elencarle né ricaricarle — recon A §4.5).
- **Ogni evento server→browser porta `ts`** (ISO 8601, orologio del server: il
  core non ha timestamp — recon A §4.4) **e `seq`** (intero monotono per
  connessione: è `seq`, non l'ordine di arrivo, a fare fede).
- **Gli id (`plan_id`, `turn_id`, `request_id`) sono stringhe opache** generate
  dal server, uniche nella sessione. Il browser non ne interpreta la forma.
- **Mai percorsi assoluti sul filo**: i nomi file sono relativi a `transcripts/`.
- Chiavi delle teste: quelle del roster (`Roster.keys()`); il destinatario
  speciale è la stringa `"director"`.

## 2. Eventi server → browser

| # | `type` | Quando | Fonte nel core |
|---|---|---|---|
| 1 | `wave_planned` | il router ha prodotto il piano a ondate | `route_plan()` |
| 2 | `turn_started` | una testa prende la parola | prima di `head_speak*()` |
| 3 | `turn_token` | testo in streaming del turno | vedi §6.1 |
| 4 | `turn_completed` | il turno è nel transcript | dopo `head_speak*()` + `parse_search_request()` |
| 5 | `search_pending` | una testa chiede di cercare, gate in attesa | tripla di `parse_search_request()` **o** `parse_social_request()`; campo `kind` |
| 6 | `search_result` | esito del gate (in ogni direzione) | `web_search()` / `social_intel()` o verdetto `deny`; campo `kind` |
| 7 | `head_state` | cambio di stato di una testa | orchestrazione server |
| 8 | `router_degraded` | il router a ondate è caduto sul fallback | vedi §6.2 — lezione del 03/08 |
| 9 | `turn_route` | rotta di fatturazione di un turno Claude | `last_claude_route()` — vedi §6.3 |
| 10 | `session_saved` | il transcript è stato persistito | `RoomSession.append_*()` |

Dettagli non ovvi:

- **`wave_planned.waves`** è la forma esatta di `route_plan()`: lista di ondate,
  ogni ondata lista di step `{speaker, instruction, to}`. **Garanzia di
  contratto**: `instruction` è SEMPRE una stringa (eventualmente vuota). Il
  server la normalizza prima di emettere, perché sul percorso di fallback la
  chiave può mancare del tutto (trappola documentata in recon A §2.9).
- **`turn_completed.text`** è la `clean_reply` di `parse_search_request()` (e
  poi `parse_social_request()`): né la riga `SEARCH_REQUEST` né `SOCIAL_INTEL`
  arrivano al browser dentro il testo di un turno.
- **`search_pending.kind` / `search_result.kind`** (v1.2, D23): `"search"` =
  ricerca web (DuckDuckGo, `web_search()`); `"social"` = tool social configurato
  (`social_intel()` → comando `CREW_SOCIAL_TOOL_CMD`, es. il TikTok analyzer).
  Stesso gate HITL, stessi verdetti, backend diverso. Assente = `"search"`
  (retro-compatibile). Una richiesta per turno: se una testa scrive entrambe le
  righe, vince `SEARCH_REQUEST`. Il gate resta **fail-closed**; le sentinelle
  del core fra parentesi quadre (`[social tool not configured]`, `[… failed]`,
  `[no results]`) diventano `status` `failed`/`empty`, mai un digest inventato.
- **`turn_started.after_search`** lega il secondo turno di una testa (quello
  post-gate, via `head_speak_after_search()`) alla `request_id` che l'ha
  causato: la UI può disegnarli come un'unica sequenza.
- **`head_state` è autoritativo per le card** (idle / thinking / speaking /
  searching / waiting_approval / error); gli eventi di turno sono autoritativi
  per la timeline. La UI non deve inferire gli stati dagli eventi di turno.
- **`head_state.state = "error"`**: `detail` porta il messaggio dell'eccezione.
  L'errore NON entra mai nel transcript (regola ereditata da Chainlit, recon C
  §1.5): le altre teste non devono leggere un errore come contributo creativo.
- **`search_result.status`**: `web_search()` non alza mai eccezioni, comunica il
  fallimento nella stringa (recon A §2.7). Il server la annusa e traduce:
  `"[search failed: …]"` → `failed`, `"[no results]"` → `empty`, altrimenti
  `approved`. Verdetto negato → `denied` con `final_query` e `digest` a `null`.
- **`session_saved`** viene emesso a ogni persistenza (il core riscrive l'intero
  file a ogni append — recon A §2.8): `channel` dice se è la stanza o un canale
  privato.

## 3. Messaggi browser → server

| `type` | Cosa fa | Note di contratto |
|---|---|---|
| `director_message` | battuta del Director | il server la appende al transcript PRIMA del routing (ordine ereditato da `app.py`, recon C §1.8) |
| `gate_verdict` | verdetto sul gate di ricerca | `rewrite` implica approvazione; `rewrite` con `query` vuota/bianca = `approve` con la query originale (comportamento voluto, recon C §1.2). **Default fail-closed**: nessun verdetto = nessuna ricerca. |
| `stop` | ferma la stanza | cancella ondate pendenti e giri collab; **i turni in volo si completano** — il core non sa cancellare una chiamata in corso (recon A §4.3). La UI deve mostrare "sto fermando…", non "fermo". |
| `roster_update` | aggiunge/modifica/rimuove una testa | il server DEVE validare `key` con `^[a-z][a-z0-9_]{0,31}$`: il core non lo fa e una chiave illegale sparirebbe in silenzio al load successivo (recon A §4.7). `save()` è esplicita, mai implicita. |
| `creativity_set` | slider creatività 0–10 | il server clampa a [0,10] e riemette lo stato; l'etichetta onesta del meccanismo viene da `Head.mechanism_label()` |
| `head_active` | `{ key, active }` — panchina (D22) | testa disattivata = **non instradata né in collab** (e nemmeno via @menzione), ma **ancora raggiungibile in privato**. Il server rifiuta la disattivazione che lascerebbe la stanza **senza teste attive** (guardia gemella di `remove_head`). La UI è la fonte dello stato (il flusso non ha replay) e lo rispecchia al server. |

## 4. Macchina a stati di una testa

```
idle ─(turn_started)→ thinking ─(primo turn_token)→ speaking ─(turn_completed)→ idle
                                                        │
                        (turn_completed + search_pending)┴→ waiting_approval
waiting_approval ─(gate approve)→ searching ─(search_result)→ thinking → …
waiting_approval ─(gate deny)───────────────(search_result)→ thinking → …
qualunque stato ─(eccezione)→ error ─(prossimo turn_started)→ thinking
```

Regole d'ordine garantite dal server:

1. Per turno: `turn_started` < `turn_token`* < `turn_completed` (oppure
   `head_state:error` al posto di `turn_completed`).
2. Turno con ricerca: `turn_completed` < `search_pending` < *(gate_verdict)* <
   `search_result` < `turn_started` (con `after_search` valorizzato).
3. Fra ondate: tutti i `turn_completed`/`error` dell'ondata N precedono ogni
   `turn_started` dell'ondata N+1. Dentro un'ondata il contesto è congelato
   all'inizio e il merge nel transcript segue l'ordine degli step (decisione D2).
4. `turn_route` arriva dopo il `turn_completed` dello stesso turno.

## 5. Tipi — TypeScript

```typescript
export const PROTOCOL_VERSION = 1;

export type HeadStateName =
  | "idle" | "thinking" | "speaking" | "searching"
  | "waiting_approval" | "error";
export type TurnRoute = "subscription" | "api";
export type SearchStatus = "approved" | "denied" | "failed" | "empty";
export type SavedChannel = "room" | "private";
export type GateVerdictName = "approve" | "deny" | "rewrite";
export type RosterAction = "add" | "update" | "remove";

/** Uno step del piano, forma esatta di route_plan(). */
export interface WaveStep {
  speaker: string;      // chiave della testa
  instruction: string;  // sempre presente, eventualmente "" (mai assente)
  to: string;           // chiave di una testa oppure "director"
}

interface ServerEventBase {
  ts: string;   // ISO 8601, orologio del server
  seq: number;  // monotono per connessione
}

export interface WavePlanned extends ServerEventBase {
  type: "wave_planned";
  plan_id: string;
  waves: WaveStep[][];
}

export interface TurnStarted extends ServerEventBase {
  type: "turn_started";
  turn_id: string;
  plan_id: string;
  wave_index: number;           // 0-based dentro il piano
  speaker: string;
  to: string;                   // testa o "director"
  private: boolean;             // canale privato (RoomSession.append_private)
  after_search: string | null;  // request_id se è il turno post-gate
}

export interface TurnToken extends ServerEventBase {
  type: "turn_token";
  turn_id: string;
  text: string;                 // frammento; v. §6.1 per la granularità in v1
}

export interface TurnCompleted extends ServerEventBase {
  type: "turn_completed";
  turn_id: string;
  speaker: string;
  to: string;
  text: string;                 // clean_reply: senza riga SEARCH_REQUEST
  private: boolean;
}

export interface SearchPending extends ServerEventBase {
  type: "search_pending";
  request_id: string;
  turn_id: string;              // il turno che ha chiesto di cercare
  speaker: string;
  query: string;                // dalla tripla di parse_search_request()
  why: string;
}

export interface SearchResult extends ServerEventBase {
  type: "search_result";
  request_id: string;
  status: SearchStatus;
  final_query: string | null;   // query effettiva (riscritta se rewrite); null se denied
  digest: string | null;        // righe "- titolo — snippet (url)"; null se denied
}

export interface HeadState extends ServerEventBase {
  type: "head_state";
  speaker: string;
  state: HeadStateName;
  detail: string | null;        // per "error": messaggio; MAI nel transcript
}

export interface RouterDegraded extends ServerEventBase {
  type: "router_degraded";
  plan_id: string;
  reason: string;               // perché il router a ondate è caduto
}

export interface TurnRouteEvent extends ServerEventBase {
  type: "turn_route";
  turn_id: string;
  route: TurnRoute;             // "subscription" | "api" — solo teste anthropic/*
}

export interface SessionSaved extends ServerEventBase {
  type: "session_saved";
  stamp: string;                // es. "20260803-101500"
  file: string;                 // relativo a transcripts/, mai assoluto
  channel: SavedChannel;
}

export type ServerEvent =
  | WavePlanned | TurnStarted | TurnToken | TurnCompleted
  | SearchPending | SearchResult | HeadState | RouterDegraded
  | TurnRouteEvent | SessionSaved;

// ---- browser → server ----

export interface DirectorMessage {
  type: "director_message";
  text: string;
}

export interface GateVerdict {
  type: "gate_verdict";
  request_id: string;
  verdict: GateVerdictName;
  query: string | null;         // obbligatoria per "rewrite"; vuota ⇒ approve con l'originale
}

export interface Stop {
  type: "stop";
}

export interface RosterFields {
  name?: string;
  avatar?: string;
  color?: string;               // hex, riusabile in CSS
  model_id?: string;            // solo da VERIFIED_MODELS
  persona?: string;
  creativity?: number;          // 0–10
}

export interface RosterUpdate {
  type: "roster_update";
  action: RosterAction;
  key: string;                  // il server valida ^[a-z][a-z0-9_]{0,31}$
  fields: RosterFields | null;  // null solo per "remove"
}

export interface CreativitySet {
  type: "creativity_set";
  key: string;
  level: number;                // 0–10, il server clampa
}

export type ClientMessage =
  | DirectorMessage | GateVerdict | Stop | RosterUpdate | CreativitySet;
```

## 6. Tipi — Python

Corrispondenza 1:1 con i tipi TypeScript: stessi nomi, stessi campi, stessi
letterali. `TypedDict` perché sul filo viaggia JSON: `asdict`/parse diretti.

```python
from typing import Literal, TypedDict

PROTOCOL_VERSION = 1

HeadStateName = Literal["idle", "thinking", "speaking", "searching",
                        "waiting_approval", "error"]
TurnRoute = Literal["subscription", "api"]
SearchStatus = Literal["approved", "denied", "failed", "empty"]
SavedChannel = Literal["room", "private"]
GateVerdictName = Literal["approve", "deny", "rewrite"]
RosterAction = Literal["add", "update", "remove"]


class WaveStep(TypedDict):
    speaker: str
    instruction: str          # sempre presente, eventualmente "" (mai assente)
    to: str                   # chiave di una testa oppure "director"


class _ServerEventBase(TypedDict):
    ts: str                   # ISO 8601, orologio del server
    seq: int                  # monotono per connessione


class WavePlanned(_ServerEventBase):
    type: Literal["wave_planned"]
    plan_id: str
    waves: list[list[WaveStep]]


class TurnStarted(_ServerEventBase):
    type: Literal["turn_started"]
    turn_id: str
    plan_id: str
    wave_index: int
    speaker: str
    to: str
    private: bool
    after_search: str | None


class TurnToken(_ServerEventBase):
    type: Literal["turn_token"]
    turn_id: str
    text: str


class TurnCompleted(_ServerEventBase):
    type: Literal["turn_completed"]
    turn_id: str
    speaker: str
    to: str
    text: str                 # clean_reply: senza riga SEARCH_REQUEST
    private: bool


class SearchPending(_ServerEventBase):
    type: Literal["search_pending"]
    request_id: str
    turn_id: str
    speaker: str
    query: str
    why: str


class SearchResult(_ServerEventBase):
    type: Literal["search_result"]
    request_id: str
    status: SearchStatus
    final_query: str | None
    digest: str | None


class HeadState(_ServerEventBase):
    type: Literal["head_state"]
    speaker: str
    state: HeadStateName
    detail: str | None        # per "error": messaggio; MAI nel transcript


class RouterDegraded(_ServerEventBase):
    type: Literal["router_degraded"]
    plan_id: str
    reason: str


class TurnRouteEvent(_ServerEventBase):
    type: Literal["turn_route"]
    turn_id: str
    route: TurnRoute


class SessionSaved(_ServerEventBase):
    type: Literal["session_saved"]
    stamp: str
    file: str                 # relativo a transcripts/, mai assoluto
    channel: SavedChannel


ServerEvent = (WavePlanned | TurnStarted | TurnToken | TurnCompleted
               | SearchPending | SearchResult | HeadState | RouterDegraded
               | TurnRouteEvent | SessionSaved)


# ---- browser → server ----

class DirectorMessage(TypedDict):
    type: Literal["director_message"]
    text: str


class GateVerdict(TypedDict):
    type: Literal["gate_verdict"]
    request_id: str
    verdict: GateVerdictName
    query: str | None         # obbligatoria per "rewrite"; vuota ⇒ approve con l'originale


class Stop(TypedDict):
    type: Literal["stop"]


class RosterFields(TypedDict, total=False):
    name: str
    avatar: str
    color: str
    model_id: str             # solo da VERIFIED_MODELS
    persona: str
    creativity: int           # 0–10


class RosterUpdate(TypedDict):
    type: Literal["roster_update"]
    action: RosterAction
    key: str                  # il server valida ^[a-z][a-z0-9_]{0,31}$
    fields: RosterFields | None


class CreativitySet(TypedDict):
    type: Literal["creativity_set"]
    key: str
    level: int                # 0–10, il server clampa


ClientMessage = (DirectorMessage | GateVerdict | Stop | RosterUpdate
                 | CreativitySet)
```

## 7. Dove il contratto promette più di quanto il core dia oggi

Tre eventi sono nel contratto perché la UI ne ha bisogno, ma richiedono un
aggancio **additivo** in `crew_cast.py` (nessuna firma esistente cambia).
Finché l'aggancio non c'è, vale il comportamento v1 dichiarato qui.

### 7.1 `turn_token` — il core non fa streaming (recon A §4.1)

`ClaudeLLM.call()` ritorna il testo tutto insieme (subprocess con
`capture_output`; ramo API sincrono). **Comportamento v1**: il server emette
ESATTAMENTE UN `turn_token` con il testo intero, subito prima di
`turn_completed`. La UI non deve assumere granularità: 1 o N frammenti sono
entrambi legali. Aggancio futuro: lettura incrementale sul ramo CLI
(`Popen`), `stream=True` sul ramo litellm.

### 7.2 `router_degraded` — il fallback oggi è silenzioso (recon A §2.9)

`route_plan()` ricade su `route()` internamente senza dirlo a nessuno: è
esattamente il modo in cui il 03/08 il router è morto in silenzio facendo
sembrare rotto un modello sano. **Aggancio richiesto (Fase 2)**: una funzione
di modulo `last_plan_route() -> Literal["waves", "fallback"]` sul modello di
`last_claude_route()` — additiva, zero firme toccate. Senza aggancio il server
NON può emettere questo evento in modo affidabile (la forma del piano di
fallback è indistinguibile da un piano legittimo di ondate singole).

### 7.3 `turn_route` — attribuzione per turno, non per processo (recon A §4.6)

`last_claude_route()` legge un log globale di processo: con due turni Claude
in parallelo nella stessa ondata l'attribuzione è ambigua. **Comportamento
v1**: il server emette `turn_route` solo quando l'attribuzione è certa (un
solo turno anthropic/* in volo); altrimenti lo omette — meglio nessun dato che
un dato falso su chi sta fatturando. Aggancio futuro: rotta leggibile
per-istanza (es. `ClaudeLLM.last_route`), additivo.

Fuori contratto in v1, già censiti ma rimandati: elenco/ripresa sessioni
(recon A §4.5), conteggio token/costo (recon A §4.8), cancellazione dura di un
turno in volo (recon A §4.3 — `stop` scarta, non ferma la spesa).

## 8. Estensione v1.1 (Fase 5) — additiva

Due aggiunte, nessun cambiamento a ciò che esisteva.

**Browser → server: `private_message`** — `{ type, head, text }`. Apre il
turno di una chat privata 1:1 con la testa `head`. Il server usa i canali
privati di `RoomSession` (stagni per costruzione, recon A §2.8) e risponde
con i normali eventi di turno con `private: true`. Regole:

- i turni privati NON entrano mai nella timeline di stanza: il client li
  smista nel thread privato della testa (`foldEvents.privateThreads`);
- nel privato il gate di ricerca è disattivo in v1.1: un'eventuale riga
  `SEARCH_REQUEST` viene rimossa dal testo e registrata nel log del server.

**Server → browser: `collab_round`** — `{ type, ts, seq, round, total, mode?,
reason? }`. Contatore della collab mode: emesso all'inizio di ogni giro;
`round: 0, total: 0` segnala la fine della corsa. `mode` (v1.2, D21) vale
`"fixed"` (N giri, contatore `giro k/total`) o `"organic"` (collab **libera**:
`total: 0`, la UI mostra solo `giro k`). `reason` compare solo sull'evento di
chiusura (`round: 0`): `"done"` (giri finiti), `"exhausted"` (la stanza ha
taciuto per due giri di fila → si è chiusa da sé), `"cap"` (raggiunto il tetto
di sicurezza), `"stopped"` (Stop del Director).

La collab **fissa** si attiva col trigger naturale del core («discutete fra
voi per N giri», `parse_auto_request`) o col comando `/auto N` — **tetto duro
lato web: 20 giri** (il core ne consentirebbe 50; il cap è applicato dal
server, il core resta intatto). La collab **libera** si attiva con «…finché
avete qualcosa da dire» (o «liberamente» / «a oltranza») o col comando
`/auto libero`: le teste vanno avanti da sole finché hanno di che parlare;
una testa senza altro da dire risponde `[PASS]`, e quando un intero giro è
tutto-PASS per due volte di fila la corsa si chiude (`reason: "exhausted"`).
Cintura di sicurezza contro i loop (degeneration-of-thought) e il consumo:
`CREW_ORGANIC_CAP` giri, default 30. In entrambe le modalità il gate di
ricerca resta attivo dentro i giri; `stop` chiude la corsa a fine giro
corrente (`reason: "stopped"`).

## 9. Estensione v1.3 (D27) — goal mode

Una aggiunta, nessun cambiamento a ciò che esisteva.

**Browser → server**: nessun messaggio nuovo — `/goal <obiettivo>` è testo
dentro un normale `director_message`, riconosciuto lato server prima del
router (come `/auto`).

**Server → browser: `goal_verdict`** — `{ type, ts, seq, round, score, met,
reason }`. Emesso a fine di ogni giro di goal mode, dopo il `collab_round` di
apertura giro e dopo che l'ondata ha parlato. `score` è `0-10` oppure `null`
quando il judge non era disponibile quel giro (chiamata fallita o output
illeggibile — **fail-closed**, come il gate di ricerca: `met` resta `false`,
mai un verdetto inventato). `reason` è una riga sola: cosa manca se `met` è
falso, perché passa se è vero.

`collab_round` si riusa per il contatore di giro anche in goal mode:
`mode: "goal"`, `total` è il tetto (`WEB_GOAL_CAP`, non un totale aperto come
in organic — un goal ha sempre un tetto). Sull'evento di chiusura,
`reason: "met"` si aggiunge al vocabolario esistente (il judge ha certificato
l'obiettivo raggiunto); `"cap"` coincide col significato che già aveva
(tetto di sicurezza raggiunto senza successo — non c'è un `"done"` separato
per il goal: finire il tetto senza aver raggiunto l'obiettivo *è* l'esito
"cap", non un esito neutro).

**Il giudice non è una testa della stanza.** `core.judge_goal()` è una
chiamata LLM a parte (stesso modello/effort del router, `llm_claude_router`
docet) che vede il transcript e il goal, non la persona di nessuna testa:
chi insegue l'obiettivo non è chi lo certifica — lo stesso motivo per cui il
router (`route_plan`) non è affidato a una testa della stanza.

**Tetto obbligatorio**: `WEB_GOAL_CAP` (env `CREW_GOAL_CAP`, default 8) —
più basso del cap organico perché ogni giro è un'ondata intera (fino a 9
teste) più una chiamata di giudizio: caro per costruzione. Lezione diretta
del pattern Ralph/loop engineering: un obiettivo senza tetto, o un judge
rotto, non deve poter far girare la stanza (e la spesa) all'infinito — un
giro col judge indisponibile conta comunque nel tetto.
