# A — Contratto del core (`crew_cast.py`)

Ricognizione in sola lettura del backend condiviso, in vista di una web app che
sostituisca Chainlit (`app.py`) e conviva con la TUI (`room_tui.py`).
Fonti: `crew_cast.py` (741 righe, letto per intero), `tests/test_core_ext.py`,
`tests/test_tui.py`, `roster.json`. Nessun file è stato modificato, nessuna
chiamata LLM è stata eseguita.

Il modulo dichiara la propria regola d'oro nel docstring: **«Nothing in this
module prints or draws — the front-end owns all I/O»**. È vero: il core non ha
dipendenze dalla UI. Ma non ha nemmeno hook di progresso, streaming o
cancellazione — vedi §7.

---

## 1. Due generazioni di API nello stesso file

`crew_cast.py` contiene **due strati sovrapposti** che fanno la stessa cosa in
modi diversi. Chi disegna la web app deve scegliere consapevolmente:

| | Strato v1 (legacy, `CAST`) | Strato v2 (roster, `Roster`) |
|---|---|---|
| Cast | costante `CAST` (4 teste fisse) | `Roster` caricato da `roster.json`, editabile a runtime |
| Turno | `speak()` / `speak_after_search()` | `head_speak()` / `head_speak_after_search()` |
| Routing | `route()` → lista piatta di step | `route_plan()` → lista di **ondate** |
| Prompt | costruito inline dentro `speak()` | `build_turn_prompt()` (puro, testabile) |
| Creatività | assente | slider 0-10 (`temp_for_level` / `creativity_block`) |
| Privato | assente | `RoomSession` con canali stagni |
| Chi lo usa | `app.py` (Chainlit) e `room.py` | `room_tui.py` |

**La web app deve usare lo strato v2.** Lo strato v1 sopravvive solo perché
Chainlit non è mai stato migrato; se la web app sostituisce `app.py`, `route()`,
`speak()` e `speak_after_search()` restano vivi solo come *fallback interno* di
`route_plan()` (che chiama `route()` quando il router a ondate fallisce).

---

## 2. Funzioni e classi pubbliche — firma, ritorno, forma reale del dato

### 2.1 Chiavi e routing di fatturazione

```python
missing_keys() -> list
```
Ritorna la lista delle chiavi assenti fra `REQUIRED_KEYS = ("ANTHROPIC_API_KEY",
"GEMINI_API_KEY", "XAI_API_KEY")`. Forma reale: `[]` quando tutto è a posto,
altrimenti p.es. `["XAI_API_KEY"]`. Legge `os.getenv` al momento della chiamata.

```python
last_claude_route() -> str
```
Ritorna **`"subscription"`**, **`"api"`** o **`"?"`** (se nessuna chiamata Claude
è ancora avvenuta). È l'ultimo elemento di `_route_log`, una **lista globale di
modulo**: non è per-sessione né per-turno. `room_tui.py` la usa solo per il
banner «stai fatturando» (`_check_billing`). Vedi §7 per il problema in
multi-utente.

```python
class ClaudeLLM:
    def __init__(self, model: str)          # model SENZA prefisso, es. "claude-opus-5"
    self.model: str
    def call(self, prompt: str) -> str
```
Drop-in di `crewai.LLM`. `call()` prova prima la CLI `claude` locale
(abbonamento) e in caso di eccezione ricade sull'API a consumo; appende
`"subscription"` o `"api"` a `_route_log`. La CLI gira con
`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` **rimossi
dall'env** (verificato in `tests/test_core_ext.py::test_claude_cli_env_scrubs_billing_and_endpoint_vars`)
e con timeout `CLAUDE_TIMEOUT = 240` secondi. Se la CLI non è installata
(`CLAUDE_CLI = shutil.which("claude")` è `None`) si va diretti in API.
`call()` **può alzare eccezione** se anche l'API fallisce.

Istanze di modulo già pronte: `llm_claude_voice` (opus-5), `llm_claude_router`
(sonnet-5), `llm_gemini`, `llm_grok`.

### 2.2 Slider di creatività (puri)

```python
temp_for_level(level: int) -> float
```
`0.1 + 0.11 * clamp(level, 0, 10)`, arrotondato a 2 decimali. Valori verificati
dai test: `0 → 0.1`, `5 → 0.65`, `10 → 1.2`, `-3 → 0.1`, `99 → 1.2`.

```python
creativity_block(level: int) -> str
```
Ritorna il blocco di prompt per la fascia: `0-2` (LOW), `6-8` (HIGH), `9-10`
(MAX), e **stringa vuota `""` per 3-5** (fascia neutra: nessuna iniezione). Ogni
testo inizia con `"CREATIVE RISK SETTING (…)"`. `level` fuori 0-10 → `""`.

### 2.3 `Head` — la testa come dato

```python
@dataclass
class Head:
    key: str          # ^[a-z][a-z0-9_]{0,31}$ (validato SOLO in Roster.load)
    name: str         # "Creative Director"
    avatar: str       # "🎨"
    color: str        # hex Textual, es. "#ff8700" — riusabile in CSS
    model_id: str     # CON prefisso provider, es. "anthropic/claude-opus-5"
    persona: str      # SOLO la parte di ruolo; ROOM_RULES si antepone al volo
    creativity: int = 5

    def mechanism_label(self) -> str
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, d: dict) -> "Head"
```

`mechanism_label()` ritorna la stringa `"via prompt"` per i modelli
`anthropic/*` (Claude 5 rifiuta `temperature`), altrimenti
`"via temperature 0.76"` — cioè `f"via temperature {temp_for_level(creativity)}"`.

`to_dict()` è `dataclasses.asdict`: **JSON-serializzabile as-is**, ed è
esattamente la forma di una voce di `roster.json`:

```json
{
  "key": "cd",
  "name": "Creative Director",
  "avatar": "🎨",
  "color": "#ff8700",
  "model_id": "anthropic/claude-opus-5",
  "persona": " You are the Creative Director: you turn truths into executional directions — concept, visual world, how the product stays the hero. Tension and craft, not safe beauty.",
  "creativity": 5
}
```

Nota: `persona` **comincia con uno spazio** (concatenazione con `ROOM_RULES`).
`Head.from_dict(h.to_dict()) == h` (roundtrip testato).

### 2.4 `make_llm` e `Roster`

```python
make_llm(head: Head) -> ClaudeLLM | crewai.LLM
```
`anthropic/*` → `ClaudeLLM(<nome nudo>)` (subscription-first). Altrimenti
`LLM(model=head.model_id, temperature=temp_for_level(head.creativity))`, più
`additional_drop_params=["stop"]` per `xai/*`. Istantanea (non chiama nulla).

```python
class Roster:
    def __init__(self, heads: dict[str, Head])
    self.heads: dict[str, Head]      # ordinato per inserimento
    @classmethod def default(cls) -> "Roster"
    @classmethod def load(cls, path: str = None) -> "Roster"     # default: roster.json accanto al modulo
    def save(self, path: str = None)                             # scrittura atomica (tmp + os.replace)
    def keys(self)                                               # dict_keys, NON una lista
    def llm(self, key: str)                                      # cache per chiave
    def update_head(self, key: str, **fields)                    # setattr + invalida la cache LLM
    def add_head(self, head: Head)
    def remove_head(self, key: str)                              # ValueError se è l'ultima
```

Forma reale di `Roster.default()` (test `test_roster_default_matches_cast`):
chiavi `["producer", "strategist", "cd", "social"]`, `model_id` rispettivamente
`anthropic/claude-opus-5`, `gemini/gemini-3.1-pro-preview`,
`anthropic/claude-opus-5`, `xai/grok-4.5`, tutte con `creativity == 5`.

`load()` è **paranoica ma silenziosa**: una testa con chiave fuori formato viene
**scartata da sola** (le altre restano); se non ne resta nessuna, o il file è
JSON rotto, il file viene copiato in `<path>.bad` e si torna al default. Nessun
messaggio, nessuna eccezione, nessun modo per il chiamante di sapere che è
successo — la web app non può mostrare «il tuo roster era corrotto».

`save()` **non è implicita**: `add_head`/`remove_head`/`update_head` non
persistono nulla, lo fa il chiamante (esplicito nei test). Il file di default è
uno solo, `roster.json` nella root del repo → vedi §7 (stato globale).

`VERIFIED_MODELS` è la whitelist dei 4 model id validati sul registry
(`anthropic/claude-opus-5`, `anthropic/claude-sonnet-5`,
`gemini/gemini-3.1-pro-preview`, `xai/grok-4.5`) — la TUI la usa per popolare
la select del modello.

### 2.5 Costruttori di prompt (puri, nessuna rete)

```python
build_turn_prompt(head: Head, context: str, instruction: str,
                  private: bool = False) -> str
build_after_search_prompt(head: Head, context: str, why: str,
                          query: str = None, results: str = None,
                          private: bool = False) -> str
build_brief(brand: str, theme: str, mandate: str, medium: str) -> str
```

`build_turn_prompt` compone, separati da `\n\n`: `ROOM_RULES + head.persona`, poi
(se non neutra) `creativity_block(head.creativity)`, poi (se `private`)
`PRIVATE_PREAMBLE`, poi `"ROOM TRANSCRIPT (latest last):\n" + context[-8000:]`,
poi `"The floor is yours now. Your brief for this turn: … Speak as {name}:"`.
**Il contesto è troncato agli ultimi 8000 caratteri**, sempre.

`build_after_search_prompt` con `results=None` → blocco `DENIED`; con
`query`/`results` → blocco `APPROVED` + `RESULTS:`.

`build_brief` produce il testo del brief nella forma attesa a monte
(`PROJECT:` / `LAUNCH THEME:` / `MANDATE:` / `MEDIUM:` + il paragrafo
«WHAT WE DON'T HAVE YET»). I 4 campi sono esattamente quelli dell'intake di
`app.py` e `room_tui.py`: `brand`, `theme`, `mandate`, `medium`.

### 2.6 Turni (bloccanti)

```python
head_speak(roster: Roster, key: str, context: str, instruction: str,
           private: bool = False) -> str
head_speak_after_search(roster: Roster, key: str, context: str, why: str,
                        query: str = None, results: str = None,
                        private: bool = False) -> str
```
Ritornano il testo della battuta, `str(...).strip()`. Il testo **può contenere
una riga `SEARCH_REQUEST:`** (solo `head_speak`; il prompt del secondo turno la
vieta esplicitamente). Nessun metadato: niente token usati, niente durata,
niente id del turno, niente indicazione di quale provider ha risposto.
`KeyError` se `key` non è nel roster (il roster può cambiare mentre il turno è
in volo — la TUI si difende con un `if key not in self.roster.heads`).

Equivalenti legacy su `CAST`: `speak(key, transcript, instruction) -> str` e
`speak_after_search(key, transcript, why, query=None, results=None) -> str`.

### 2.7 Gate di ricerca web

```python
parse_search_request(reply: str) -> tuple
```
**La tripla che restituisce** è `(clean_reply, query, why)`:

- nessuna richiesta → `(reply, None, None)` — la reply è restituita **identica**,
  non ripulita;
- richiesta trovata → `(reply_senza_la_riga_SEARCH_REQUEST_strippata, query, why)`.

Esempio reale, con l'input nella forma imposta da `ROOM_RULES`:

```python
reply = (
    "Il territorio 'silenzio' è forte, ma va verificato.\n"
    "SEARCH_REQUEST: competitor hero film silence territory 2026 || "
    "devo sapere se un competitor l'ha già occupato"
)
parse_search_request(reply)
# -> ("Il territorio 'silenzio' è forte, ma va verificato.",
#     "competitor hero film silence territory 2026",
#     "devo sapere se un competitor l'ha già occupato")
```

Il regex è `^\s*SEARCH_REQUEST:\s*(.+?)\s*\|\|\s*(.+?)\s*$` con `re.MULTILINE`:
serve il separatore `||`, e una richiesta senza `||` **non viene riconosciuta e
resta nel testo della battuta**. `SEARCH_RE.sub("", reply)` rimuove **tutte** le
occorrenze, ma `m` è solo la prima: con due richieste nello stesso turno si
perde la seconda. Funzione **pura**.

```python
web_search(query: str, n: int = 5) -> str
```
DuckDuckGo via `ddgs`, senza chiave. Ritorna un digest a righe:

```
- <title> — <primi 220 char del body> (<href>)
- …
```

**Non alza mai eccezione**: in errore ritorna la stringa `"[search failed: <e>]"`,
senza risultati `"[no results]"`. Il chiamante deve quindi *annusare la stringa*
per capire se è andata male — non c'è un flag di esito.

### 2.8 `RoomSession` — transcript e canali privati

```python
class RoomSession:
    def __init__(self, brief: str, base_dir: str = None, stamp: str = None)
    self.brief: str
    self.base_dir: str        # default: transcripts/ accanto al modulo
    self.stamp: str           # "%Y%m%d-%H%M%S", uniquificato con "-2", "-3", …
    self.room_text: str
    self.room_path: str       # <base_dir>/room-<stamp>.md
    def room_context(self) -> str
    def append_room(self, label: str, text: str)
    def private_path(self, key: str) -> str        # <base_dir>/private-<key>-<stamp>.md
    def private_context(self, key: str) -> str
    def append_private(self, key: str, label: str, text: str)
```

`room_text` è **una stringa piatta**, non una lista di messaggi:
`append_room("Creative Director", "…")` fa `room_text += f"{label}: {text}\n"`.
`room_context()` ritorna `f"BRIEF:\n{brief}\n\n{room_text}"`.

`private_context(key)` ritorna brief + testo di stanza + `\n--- PRIVATE SIDEBAR
(only you and the Director) ---\n` + il privato **di quella sola testa**.
Garanzia dura testata (`test_session_private_is_watertight`): il privato non
entra mai in `room_context()` né nel privato di un'altra testa.

**Ogni append riscrive l'intero file** (`open(..., "w")`), per stanza e per
privato. Il costruttore stesso scrive subito il file (side effect alla nascita)
e uniquifica lo stamp se `room-<stamp>.md` esiste già, così due sessioni aperte
nello stesso secondo non si sovrascrivono.

### 2.9 Router a ondate

```python
parse_wave_plan(raw: str, valid_keys) -> list        # puro
route_plan(roster: Roster, transcript: str, msg: str) -> list   # bloccante
```

Forma reale del ritorno: **lista di ondate; ogni ondata è una lista di step;
ogni step è `{"speaker": str, "instruction": str, "to": str}`**, con `to` ∈
`valid_keys ∪ {"director"}`. Massimo **4 step in totale** su tutte le ondate.

`parse_wave_plan` è paranoica: cerca `[[ … ]]` nel testo, JSON non valido → `[]`,
un elemento non-lista → `[]` (scarta tutto il piano), step con `speaker`
sconosciuto → scartato, `to` mancante/ignoto → `"director"`, `to == speaker` →
normalizzato a `"director"` (bug 12). Le ondate rimaste vuote non vengono
aggiunte. `instruction` è sempre presente, `str(s.get("instruction", ""))`, ma
**può essere la stringa vuota**.

#### Esempio vero di ondata, con il campo `to`

Dall'output del router validato in `tests/test_core_ext.py::test_parse_wave_plan_valid`
(stessa forma usata come piano finto in tutta `tests/test_tui.py`):

```python
[
  # ONDATA 1 — due teste parlano IN PARALLELO, entrambe rispondono al Director
  [
    {"speaker": "strategist", "instruction": "a", "to": "director"},
    {"speaker": "social",     "instruction": "b", "to": "director"},
  ],
  # ONDATA 2 — parte solo quando la 1 è finita; il CD si rivolge al social
  [
    {"speaker": "cd", "instruction": "c", "to": "social"},
  ],
]
```

Letto in chiaro: *«Strategist e Social danno la loro lettura in parallelo (≈ il
tempo della testa più lenta); poi il Creative Director prende la parola e la
sua battuta è indirizzata al Social»*. La UI usa `to` per il titolo della
entry: `🎨 Creative Director → 📡 Social & Precedent Analyst:` quando `to` è una
testa, `🎨 Creative Director:` quando è `"director"` (logica in
`room_tui.py::_entry_header`).

Il consulto — la regola esplicita di `PLAN_PROMPT`, *«consults are NEVER
parallel»* — ha questa forma a tre ondate da uno step:

```python
[
  [{"speaker": "cd",         "instruction": "…", "to": "strategist"}],  # X pone la domanda a Y
  [{"speaker": "strategist", "instruction": "…", "to": "cd"}],          # Y risponde a X
  [{"speaker": "cd",         "instruction": "…", "to": "director"}],    # X reagisce, al Director
]
```

`route_plan` costruisce `cast_lines` dal roster **corrente** (`- {key}: {name} —
{persona[:90]}`), quindi una testa aggiunta a runtime è instradabile subito;
tronca il transcript a `[-6000:]`; se il router fallisce o il piano è vuoto,
**ricade su `route()`** e avvolge ogni step in un'ondata da uno:
`[[{**s, "to": "director"}] for s in steps]`. Verificato in
`test_route_plan_falls_back_to_sequential`:

```python
route_plan(roster, "T", "cd: dammi un'idea")
# -> [[{"speaker": "cd", "instruction": "cd: dammi un'idea", "to": "director"}]]
```

⚠️ **Trappola del fallback**: `route()` filtra gli step solo sul campo
`speaker`, quindi un piano che passa da lì **può arrivare senza la chiave
`instruction`** (il router LLM la ha omessa). La TUI si difende con
`step.get("instruction") or fallback_instruction` (bug 10). Una web app che
faccia `step["instruction"]` alza `KeyError` e perde il turno.

```python
route(transcript: str, msg: str) -> list      # legacy, bloccante
```
Lista piatta di massimo 4 `{"speaker": …, "instruction": …}` (chiave
`instruction` non garantita, v. sopra). Fallback a cascata: router LLM →
prefisso da `ALIASES` (`"cd"`, `"creative"`, `"strat"`, `"ep"`, …) →
`[{"speaker": "producer", "instruction": msg}]`.

### 2.10 Modalità collab (trigger in italiano)

```python
parse_auto_request(msg: str) -> int | None
requested_rounds(msg: str) -> int | None
```

`parse_auto_request` riconosce «discutete/discutetene/parlate/parlatene/parlarne/
confrontatevi … fra|tra (di) voi» e ritorna il numero di giri, **cappato a
`AUTO_MAX_ROUNDS = 50`**; senza numero → `AUTO_DEFAULT_CAP = 20`; se non è una
richiesta di collab, o se c'è una negazione (`non`/`senza`) nei 12 caratteri
subito prima del verbo → `None`. Valori dai test:

| input | ritorno |
|---|---|
| `"discutete fra voi per 5 giri"` | `5` |
| `"parlatene fra di voi"` | `20` |
| `"discutete fra voi per 500 giri"` | `50` |
| `"discutete fra voi per 0 giri"` | `0` (falsy!) |
| `"non parlate fra di voi, aspettate il mio brief"` | `None` |
| `"quando parlate fra di voi restate concreti"` | `20` |
| `"cd: parlami del tema"` | `None` |

`requested_rounds` estrae il numero **grezzo, prima del cap** (`"…500 giri"` →
`500`, `"parlatene fra di voi"` → `None`), e serve solo alla UI per dire «ho
tagliato a 50».

### 2.11 Costanti pubbliche riusabili dalla web app

`REQUIRED_KEYS`, `CLAUDE_CLI`, `CLAUDE_TIMEOUT` (240), `ROOM_RULES`,
`ROLE_PERSONAS` (4 chiavi), `SEARCH_RE`, `CAST` (v1, include `color` ANSI e
`avatar`), `ALIASES`, `ROUTER_PROMPT`, `PLAN_PROMPT`, `VERIFIED_MODELS`,
`ROSTER_PATH`, `PRIVATE_PREAMBLE`, `AUTO_DEFAULT_CAP` (20), `AUTO_MAX_ROUNDS`
(50). Invariante testata: `ROOM_RULES + ROLE_PERSONAS[key] == CAST[key]["persona"]`.

---

## 3. Funzioni bloccanti

### 3.1 Bloccanti — LLM o rete: MAI nel thread/event-loop della UI

| Funzione | Cosa fa | Latenza tipica / limite |
|---|---|---|
| `ClaudeLLM.call()` | subprocess CLI `claude`, fallback API | timeout **240 s**, poi ancora l'API |
| `head_speak()` | 1 chiamata LLM | secondi–minuti |
| `head_speak_after_search()` | 1 chiamata LLM | secondi–minuti |
| `speak()` / `speak_after_search()` (v1) | 1 chiamata LLM | idem |
| `route()` | 1 chiamata LLM (sonnet) | secondi |
| `route_plan()` | 1 chiamata router, **+ una seconda via `route()` se fallisce** | fino a due round-trip |
| `web_search()` | HTTP verso DuckDuckGo | secondi; nessun timeout esplicito |

La TUI le esegue tutte con `asyncio.to_thread(...)`. Una web app deve fare lo
stesso (thread pool, task queue o processo worker) e **non deve dare per
scontato che un turno finisca**: nel caso peggiore, CLI in timeout (240 s) +
retry API, per ogni testa dell'ondata.

`make_llm()` e `Roster.llm()` costruiscono oggetti e basta: istantanei — ma
`Roster.llm()` va chiamato prima del thread solo se si vuole evitare che due
turni paralleli costruiscano lo stesso LLM (la cache non è thread-safe).

### 3.2 I/O su disco — veloci ma sincroni

`Roster.load()`, `Roster.save()`, `RoomSession.__init__()`,
`RoomSession.append_room()`, `RoomSession.append_private()`. Riscrivono l'intero
file a ogni turno: irrilevante per una sessione, ma è I/O bloccante dentro
l'handler.

### 3.3 Pure / istantanee — si possono chiamare ovunque

`missing_keys()` (legge solo l'env), `last_claude_route()`, `temp_for_level()`,
`creativity_block()`, `Head.mechanism_label/to_dict/from_dict`,
`build_turn_prompt()`, `build_after_search_prompt()`, `build_brief()`,
`parse_search_request()`, `parse_wave_plan()`, `parse_auto_request()`,
`requested_rounds()`, `RoomSession.room_context()`, `.private_context()`,
`.private_path()`, `Roster.keys/update_head/add_head/remove_head`, `make_llm()`.

### 3.4 Un costo nascosto: l'import

`import crew_cast` esegue `load_dotenv()`, `shutil.which("claude")` e
**istanzia quattro LLM a livello di modulo** (`llm_claude_voice`,
`llm_claude_router`, `llm_gemini`, `llm_grok`). Non fa chiamate di rete, ma è
lavoro all'import: in un server va fatto una volta all'avvio, non per richiesta.

---

## 4. Cosa NON esiste e servirebbe

Elenco basato su ciò che il codice offre davvero, non su desiderata generici.

### 4.1 Streaming dei token — **assente**
`ClaudeLLM._via_cli` usa `subprocess.run(..., capture_output=True)` con
`--output-format text`: il testo arriva **tutto insieme a fine turno**. Il ramo
API usa `LLM.call(prompt)` (sincrono, non `stream=True`). Non esiste né un
callback per chunk né un generatore. Una web app che voglia il testo che scorre
deve modificare il core (`subprocess.Popen` + lettura incrementale sul ramo CLI,
`stream=True` sul ramo litellm) — non basta wrapparlo.

### 4.2 Eventi di progresso — **assenti**
Fra la chiamata e il ritorno non c'è nessun segnale: né «router partito», né
«turno iniziato», né heartbeat. La TUI se li fabbrica da sola
(`system_line("🎛 scelgo chi parla…")` prima del router, `card.set_status(...)`
prima del turno) perché il core non li offre. La web app dovrà fare lo stesso:
il core non le dirà mai quanto manca.

### 4.3 Cancellazione di un turno in corso — **assente**
Nessun parametro `cancel_token`/`stop_event`, nessuna cooperazione. La TUI
cancella solo *fra* le ondate (`_cancel_pending`, `_collab_stop`): «i turni in
volo si completano». Per la web app significa che «Stop» può solo scartare il
risultato, non fermare la spesa. L'unico limite duro è `CLAUDE_TIMEOUT = 240` e
solo sul ramo CLI: **la chiamata API e `web_search()` non hanno timeout
esplicito**.

### 4.4 Serializzazione JSON — **solo a metà**
- ✅ `Head.to_dict()` è JSON-pronto, e `roster.json` è il suo formato naturale.
- ❌ `Roster` **non ha un `to_dict()`/`from_dict()`**: l'unico modo di
  serializzarlo è `save()` su file. Per un endpoint `GET /roster` bisogna fare
  a mano `{"heads": [h.to_dict() for h in roster.heads.values()]}` (esattamente
  ciò che `save()` fa internamente).
- ❌ `RoomSession` **non ha nessuna serializzazione**: `room_text` è una stringa
  markdown-ish `"label: testa\n"`. Non esiste una lista di messaggi con
  `{id, speaker, to, text, timestamp, private}`. Una battuta multi-riga rompe
  qualsiasi parsing a righe, quindi **il transcript non è ri-strutturabile in
  modo affidabile** a posteriori. Per una UI web (bolle, avatar, «→ risponde
  a»,  scroll, permalink a un turno) questo è il buco più grosso.
- ❌ Nessun timestamp da nessuna parte (solo lo `stamp` del nome file).

### 4.5 Elenco e ripresa delle sessioni — **assenti**
`RoomSession` sa **creare** e **appendere**, non **elencare** né **ricaricare**:
non esistono `RoomSession.list()` né `RoomSession.load(stamp)`. I file stanno in
`transcripts/` con nomi `room-<stamp>.md` e `private-<key>-<stamp>.md`, ma il
brief e il testo non sono separabili in modo pulito dal markdown scritto. Una
web app con «le mie sessioni» deve costruirsi un proprio strato di persistenza.

### 4.6 Stato globale mutabile — problema in multi-sessione/multi-utente
- `_route_log` è **globale di modulo**: `last_claude_route()` dice solo «l'ultima
  chiamata Claude *del processo*». Con ondate in parallelo o due utenti non si
  sa più *quale* turno ha fatturato.
- `roster.json` è **un file unico nella root del repo** (`ROSTER_PATH`): due
  sessioni web che editano il roster si sovrascrivono a vicenda. Serve un path
  per sessione/utente (`Roster.load(path)`/`save(path)` lo permettono già).
- `Roster._llms` è una cache non protetta: due turni paralleli sulla stessa
  testa possono costruire due LLM. Innocuo oggi, non thread-safe per contratto.

### 4.7 Errori silenziosi che una UI dovrebbe poter mostrare
- `Roster.load()` scarta teste con chiave invalida **senza dirlo**, e in caso di
  file rotto fa `.bad` + default **senza dirlo**.
- `add_head()`/`update_head()` **non validano** `key` con `_HEAD_KEY_RE`: la web
  app può creare una testa con chiave illegale che funziona in memoria e poi
  **sparisce silenziosamente al prossimo `load()`**. La validazione va rifatta
  lato web app.
- `web_search()` comunica il fallimento come stringa (`"[search failed: …]"`).
- `head_speak()` propaga l'eccezione se tutti i canali Claude falliscono: la web
  app deve avere un suo `try/except` per turno, o un'ondata muore per intero.

### 4.8 Altre lacune minori ma concrete
- **Nessun conteggio token/costo**: niente usage, quindi nessun contatore di
  spesa possibile oltre al binario `subscription`/`api`.
- **Il gate di ricerca è tutto lato front-end**: il core offre solo
  `parse_search_request` + `web_search` + `head_speak_after_search`. Approvazione,
  modifica della query, negazione, e la nota di sistema nel transcript sono
  logica che la TUI implementa da sé e che la web app dovrà **riscrivere**.
- **Il trigger collab è solo in italiano** (`parse_auto_request`) mentre le
  battute sono in inglese (`ROOM_RULES`): una web app internazionale non ha un
  aggancio in inglese.
- **`parse_auto_request("…0 giri") == 0`**, falsy: `if n:` lo tratta come
  «nessuna collab». Va usato `is not None` se si vuole distinguere.
- **Il brief è immutabile**: `RoomSession.brief` si fissa nel costruttore, non
  c'è API per aggiornarlo a metà sessione.
- **Contesto troncato a 8000 caratteri** (6000 per il router) senza alcun
  riassunto: in una sessione lunga le teste perdono l'inizio della stanza e il
  core non offre nessun meccanismo di compressione.
