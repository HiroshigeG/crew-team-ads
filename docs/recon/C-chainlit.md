# Ricognizione C — La UI Chainlit: cosa salvare, cosa buttare

**Oggetto**: `app.py` (187 righe), front-end Chainlit attuale della writers' room.
**Contesto**: si valuta una web app che **sostituirà** questa UI, convivendo con la TUI
(`room_tui.py`). Questo documento serve a non perdere per strada i comportamenti buoni.
**Metodo**: sola lettura di `app.py`, `BUILD_BRIEF.md`, `crew_cast.py`, `chainlit.md`.

---

## 0. Premessa che cambia la lettura di tutto il resto

`app.py` **usa l'API vecchia di `crew_cast.py`**: `core.CAST`, `core.route()`,
`core.speak()`, `core.speak_after_search()` — cioè le funzioni definite in
`crew_cast.py:148-298`. Non tocca nulla di quello che è stato aggiunto dopo per la TUI
(`crew_cast.py:301-741`): `Roster`, `Head`, `RoomSession`, `route_plan()`,
`head_speak()`, `creativity_block()`, `parse_auto_request()`.

Conseguenza pratica: **buona parte di ciò che manca a Chainlit esiste già nel core**,
non va inventata. La web app non deve riscrivere la logica, deve *renderizzarla*. In
particolare `route_plan()` (`crew_cast.py:680`) restituisce già **ondate** di passi
paralleli con un campo `to` che dice a chi ciascuna testa si rivolge — cioè
esattamente i due limiti 1 e 2 del §2 del brief, già risolti a livello di dato.

---

## 1. Comportamenti giusti, da replicare

### 1.1 Intake delle quattro domande — `app.py:17-33`, `app.py:75-100`

La lista `INTAKE` (`app.py:17-33`) è **dato puro**: quattro tuple
`(campo, domanda_markdown, placeholder)` per brand / theme / mandate / medium. Ogni
domanda porta con sé un esempio concreto ("es. …") che è metà del suo valore: senza
placeholder il Director scrive brief vaghi e la stanza tira a indovinare — lo dice il
testo stesso della prima domanda.

Il ciclo (`app.py:76-83`) fa tre cose che vanno conservate:

- **una domanda alla volta**, non un form unico: il Director legge l'esempio e risponde;
- **abort pulito** (`app.py:80-82`): se l'utente chiude senza rispondere, messaggio
  esplicito ("Brief interrotto") e uscita, niente stato mezzo scritto;
- **`.strip()` su ogni risposta** (`app.py:83`) prima di comporre.

Il brief viene poi assemblato **solo** da `core.build_brief()` (`app.py:85`) — nessuna
formattazione lato UI. E viene **rimostrato al Director** dentro un blocco di codice
(`app.py:92-93`): il Director vede letteralmente il testo che i modelli riceveranno.
Questo va replicato: è il punto in cui ci si accorge di aver scritto male il mandato.

Subito dopo, `app.py:94-99` insegna **come si parla alla stanza** — sintassi di
indirizzamento (`cd: …`, `strategist, …`), il cross-talk (`cd, chiedi a social…`) e
l'avviso che la ricerca web richiede permesso. È onboarding nel momento giusto: dopo il
brief, prima del primo turno.

### 1.2 Il gate di ricerca — `app.py:103-139` (+ `app.py:170-180`)

È il pezzo meglio progettato del file, e va replicato **comportamento per comportamento**:

| Comportamento | Riga | Perché conta |
|---|---|---|
| Si mostra **query *e* motivo** | `app.py:108-112` | Il Director non approva un URL alla cieca: giudica se la ricerca cambia davvero la risposta. Il motivo arriva dal modello via `SEARCH_REQUEST: <query> \|\| <why>` (`crew_cast.py:118`). |
| Tre opzioni: **approva / nega / riscrivi** | `app.py:114-116` | "Riscrivi" è la terza via che evita il binario secco: la query del modello spesso è quasi giusta. |
| **Default = deny** (fail-closed) | `app.py:121` | Se il widget torna vuoto/nullo, non si cerca. Nessuna ricerca parte per omissione. |
| Query riscritta ⇒ **approvazione implicita** | `app.py:123-129` | Chi si prende la briga di riscrivere sta approvando. Se però riscrive vuoto, resta la query originale e si approva comunque (`app.py:127-129`) — comportamento voluto, da preservare così. |
| Il **rifiuto non è un vicolo cieco** | `app.py:131-133` | Si avvisa ("🚫 Ricerca negata") e **la testa parla lo stesso**, obbligata a dichiarare cosa non può verificare (`crew_cast.py:271-273`). Il turno non si perde. |
| Ricerca **ispezionabile** | `app.py:135-137` | La ricerca gira dentro uno step espandibile che espone i risultati grezzi. Il Director può controllare su cosa il modello sta basando la risposta. |
| Il **detto-prima-di-chiedere non si butta** | `app.py:174-177` | Se la testa ha scritto qualcosa *prima* della riga `SEARCH_REQUEST`, quel testo resta a schermo; se non ha scritto nulla, la bolla vuota viene **rimossa** invece di restare lì spenta. |
| Timeout lunghi (3600s) | `app.py:118`, `app.py:78`, `app.py:126` | Il Director può alzarsi dalla scrivania senza far scadere la stanza. Nella web app l'equivalente è uno **stato "decisione pendente" persistito**, non un timer. |

### 1.3 Trasparenza del routing — `app.py:152-154`

Prima che qualcuno parli, la UI mostra il piano: `"chi prende la parola"` con i **nomi
leggibili** delle teste (`core.CAST[...]["name"]`), non le chiavi interne. Il Director sa
in anticipo chi risponderà e in che ordine. Da replicare, e da estendere: con
`route_plan()` il piano è a ondate e ha il `to`, quindi si può mostrare anche *a chi*
ciascuno risponde (limite 2 del brief).

### 1.4 Bolla-segnaposto poi riempita — `app.py:159-160`, `app.py:182-183`

La bolla della testa viene **creata vuota e inviata subito**, poi aggiornata quando la
risposta arriva. È il segnale "questa testa ha preso la parola, sta pensando" — cioè un
abbozzo di R2 già presente. Nella web app diventa naturale: stato per testa
(idle / thinking / speaking / searching) su un canale di eventi.

### 1.5 Errori contenuti per testa — `app.py:162-168`

Se `core.speak()` solleva, la bolla diventa `*non disponibile: {e}*` e **il giro
continua con le altre teste** (`continue`). Un modello giù non fa cadere il round.
Da replicare pari pari — e nella web app conta di più, perché in parallelo si moltiplicano
le occasioni di fallire.

Attenzione: l'errore finisce **fuori** dal transcript (`app.py:184` non viene raggiunto per
quella testa). Corretto: le altre teste non devono leggere un messaggio d'errore come se
fosse un contributo creativo.

### 1.6 Chiavi controllate all'avvio — `app.py:56-62`

`core.missing_keys()` prima di ogni altra cosa: se manca una chiave si dice **quale** e
**dove va messa**, e non si parte. Fallire subito e in modo azionabile invece di
schiantarsi a metà del primo turno. Da replicare (adattando il messaggio: in una web app
"il file accanto all'app" non significa niente per l'utente).

### 1.7 Onestà sul portafoglio — `app.py:41-51`

Se Claude ricade sull'API a consumo invece che sull'abbonamento, la UI lo dice
**una volta sola per sessione** (flag `billed_warned`). È il requisito §1.5 del brief
reso visibile. Da replicare — con **una correzione obbligatoria**: `last_claude_route()`
legge un log **globale di processo** (`crew_cast.py:45,48`). In una app desktop
mono-utente va bene; in un server multi-sessione la route di una sessione verrebbe
attribuita a un'altra. Serve tracciamento per-sessione.

### 1.8 Transcript come contesto unico — `app.py:87`, `app.py:148-150`, `app.py:184-187`

Un'unica stringa che accumula `BRIEF` + ogni battuta con l'etichetta di chi parla, e
che è l'unico contesto passato ai modelli. Due dettagli importanti:

- la battuta del Director entra **prima** del routing (`app.py:150`), quindi il router
  vede già il messaggio nel contesto;
- la risposta di ogni testa entra nel transcript **prima** che parli la successiva
  (`app.py:184`), quindi nello stesso giro chi parla dopo legge chi ha parlato prima.

**Questo secondo punto è la ragione tecnica per cui oggi funziona in sequenza**, ed è la
decisione di progetto più delicata da prendere per la web app: se due teste girano in
parallelo (R1), non possono vedersi a vicenda. Va deciso esplicitamente che cosa vede
una testa dentro la propria ondata — la scelta ragionevole è: contesto **congelato
all'inizio dell'ondata**, uguale per tutti i membri dell'ondata, e merge a fine ondata.

**Nota**: `app.py` tiene il transcript solo in memoria di sessione (`cl.user_session`,
`app.py:87`, `187`): chiudi la finestra e sparisce. `RoomSession` (`crew_cast.py:561-614`)
fa già meglio — scrive su disco **a ogni turno**, gestisce lo stamp univoco al secondo e
tiene i canali privati stagni. La web app dovrebbe usare `RoomSession`, non replicare la
stringa in sessione.

### 1.9 Chiamate bloccanti fuori dal thread della UI — `app.py:36-38`

`_call()` avvolge ogni chiamata LLM/ricerca in `asyncio.to_thread`. È il trap T3 del
brief. Il wrapper è **agnostico rispetto a Chainlit**: funziona identico sotto qualsiasi
server asincrono.

---

## 2. I tre limiti che `BUILD_BRIEF.md` §2 imputa alla UI Chainlit

Il brief apre il §2 così: *«The Chainlit UI is a linear chat. Three things it cannot do,
and they are the whole reason for this work»*. I tre limiti, riportati fedelmente
(`BUILD_BRIEF.md:94-102`):

1. **«Everything is sequential.»** — *«When the router picks three heads, they answer one
   after another even when they are independent. It feels like a queue, not a room.»*
   Tutto è sequenziale: quando il router sceglie tre teste, rispondono una dopo l'altra
   anche quando sono indipendenti. Sembra una coda, non una stanza.

2. **«Cross-talk is invisible.»** — *«When CD asks Social and reacts, the Director sees
   three bubbles in a row with no thread between them. They cannot tell the agents talked
   to each other.»* Il brief stesso qualifica il difetto: *«This is a presentation
   failure, not a functional one — the mechanism already works.»* Il cross-talk è
   invisibile: il meccanismo funziona già, è la **presentazione** a fallire.

3. **«No parallel view.»** — *«A chat log cannot show four heads thinking at once.»*
   Nessuna vista parallela: un log di chat non può mostrare quattro teste che pensano
   contemporaneamente.

**Avvertenza sul contesto del brief** (fatto, non opinione): il §2 di `BUILD_BRIEF.md`
descrive i requisiti di una **TUI**, ed elenca fra gli "Explicitly out of scope"
(`BUILD_BRIEF.md:142-143`) proprio: *«Do not build a web app, a server, or an
Electron/Tauri shell. This is a terminal UI.»* I tre limiti restano validissimi come
diagnosi della UI Chainlit — ed è per questo che sono qui — ma il documento da cui
provengono non autorizza, di per sé, la web app che si sta valutando. Serve una decisione
esplicita del Director su questo punto.

---

## 3. Cosa si può riusare letteralmente

### 3.1 Logica pura, migra così com'è (o quasi)

| Porzione | Righe | Nota |
|---|---|---|
| `INTAKE` | `app.py:17-33` | Dato puro: lista di tuple con stringhe markdown. Zero dipendenze. Si copia e basta. Il markdown (`**grassetto**`, `\n\n`) va reso lato web, ma è già markdown, non sintassi Chainlit. |
| `_call()` | `app.py:36-38` | `asyncio.to_thread` — nessuna riga di Chainlit. Vale identico sotto FastAPI/Starlette o dentro un task worker. |
| Sequenza d'avvio | `app.py:56`, `85`, `87` | `missing_keys()` → intake → `build_brief()` → inizializza il contesto. Tre chiamate al core, ordinate. La logica migra; cambiano solo i widget attorno. |
| Macchina a stati del verdetto | `app.py:121-133`, `139` | `deny-by-default` → `edit` normalizzato ad `approve` con query sostituita → `approve` chiama `web_search` + `speak_after_search(…, query, results)`, `deny` chiama `speak_after_search(…, why)` senza risultati. È **una funzione pura** `(verdetto, query_riscritta) -> quale chiamata al core`, estraibile senza toccare il framework. Il widget che raccoglie il verdetto (`app.py:107-119`) invece no. |
| Scheletro del turno | `app.py:148-150`, `162-184` | La catena `append Director → route → speak → parse_search_request → (gate) → append transcript` è orchestrazione pura. Tutte le chiamate sono a `core.*`. Ciò che è Chainlit è solo il disegno delle bolle in mezzo. |
| Politica anti-errore | `app.py:162-168` | "cattura, degrada la singola testa, continua il giro, non scrivere l'errore nel transcript" — è una regola, non codice di framework. |

Da notare: **nessuna di queste porzioni contiene logica di dominio propria**. Tutta la
logica vera (personas, routing, parsing di `SEARCH_REQUEST`, ricerca, composizione dei
prompt) è già in `crew_cast.py`. `app.py` è ~190 righe di cui la parte non-Chainlit è
poche decine. Questo è **una buona notizia**: la superficie da riscrivere è la UI, non il
cervello.

### 3.2 Irrimediabilmente accoppiato a Chainlit (da riprogettare, non da portare)

| Cosa | Righe | Perché non migra |
|---|---|---|
| `cl.AskUserMessage` / `cl.AskActionMessage` | `app.py:77`, `107`, `124` | Widget **bloccanti**: il handler si ferma dentro un `await` finché l'utente non risponde. In una web app il turno non può restare appeso a una richiesta HTTP: serve uno stato esplicito "in attesa di decisione" (id della richiesta, persistito) e una ripresa quando la risposta arriva. **È la riprogettazione più grossa del porting**, e tocca sia l'intake sia il gate di ricerca. |
| `cl.Message` + `holder.update()` / `holder.remove()` | `app.py:46`, `58`, `64`, `89`, `132`, `159-183` | Il "manico" a un messaggio mutabile è un'astrazione di Chainlit. Equivalente web: id del messaggio + eventi di patch su WebSocket/SSE. Concettualmente uguale, implementativamente tutto nuovo. |
| `cl.Step(..., type="tool")` | `app.py:135`, `152` | Traccia collassabile per tool. Da rifare come pannello/accordion. Il *contenuto* (query, risultati grezzi, piano di routing) è invece esattamente ciò che va conservato. |
| `cl.user_session` | `app.py:43`, `45`, `86-87`, `144`, `148`, `187` | KV per sessione. Sostituibile con `RoomSession` (`crew_cast.py:561`) + un registro di sessioni lato server. |
| `@cl.on_chat_start` / `@cl.on_message` | `app.py:54`, `142` | L'intero ciclo di vita. Va rimappato su rotte/eventi. |
| `chainlit.md` | tutto il file | È il **boilerplate di default di Chainlit**, mai personalizzato (parla di Chainlit, non della stanza). **Non c'è niente da salvare qui.** Il vero testo di benvenuto della stanza è dentro `app.py:64-73`, e *quello* va portato. |

### 3.3 Cose da NON riportare dalla web app

- **La stringa-transcript in sessione** (`app.py:87`, `187`): superata da `RoomSession`.
- **L'API vecchia del core** (`core.route`/`core.speak`/`core.CAST`): la web app dovrebbe
  costruire su `Roster` + `route_plan()` + `head_speak()` + `RoomSession`, che danno già
  ondate parallele, `to` per il cross-talk, roster editabile e persistito, controllo di
  creatività onesto per modello e trigger della collab mode.
- **`last_claude_route()` globale** come sorgente per l'avviso di fatturazione: va
  reso per-sessione prima di finire su un server (vedi §1.7).

---

## 4. Sintesi in tre righe

Di Chainlit va salvato **il comportamento, non il codice**: l'intake a quattro domande
con esempi e brief rimostrato, il gate di ricerca con motivo-visibile / tre-opzioni /
default-nega / rifiuto-che-non-uccide-il-turno / risultati ispezionabili, la trasparenza
del piano di routing, la bolla-segnaposto, l'errore contenuto per testa e l'avviso onesto
sul portafoglio. La logica pura riusabile è poca e ben identificata (`INTAKE`, `_call`,
la macchina a stati del verdetto, lo scheletro del turno); tutto il resto è widget. E il
grosso di ciò che il §2 del brief lamenta è **già risolto dentro `crew_cast.py`**: la web
app deve renderizzarlo, non riscriverlo.
