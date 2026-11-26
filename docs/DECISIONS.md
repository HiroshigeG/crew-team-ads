# DECISIONS — registro delle decisioni di progetto

Regola della casa: le decisioni prese non si rimettono in discussione senza un
motivo nuovo. Questo file è il verbale; ogni voce ha data e motivazione.

---

## D1 — 2026-08-03 · La web app ADV è autorizzata

**Decisione**: si costruisce una web app per le sessioni ADV con cliente. Essa
**sostituisce la UI Chainlit** (`app.py`) e **convive con la TUI**
(`room_tui.py`), che resta la superficie per chi lavora in terminale.

**Contesto**: `BUILD_BRIEF.md` §2 elenca fra gli "Explicitly out of scope":
*«Do not build a web app, a server, or an Electron/Tauri shell. This is a
terminal UI.»* Quel vincolo apparteneva al progetto TUI, che è stato
consegnato (80 test verdi). La presente decisione lo supera esplicitamente per
questo nuovo filone di lavoro; i tre limiti diagnosticati nello stesso §2
restano la motivazione della web app (vedi `docs/recon/C-chainlit.md`).

**Conseguenze**: la web app costruisce sullo strato v2 del core
(`Roster` / `route_plan` / `head_speak` / `RoomSession`), non duplica logica di
`crew_cast.py`, e ogni aggiunta al core è additiva senza cambiare firme.

## D2 — 2026-08-03 · Contesto delle ondate parallele: congelato a inizio ondata

**Decisione**: dentro un'ondata di `route_plan()`, ogni testa riceve lo stesso
contesto, **congelato all'inizio dell'ondata**. Le teste della stessa ondata
non si leggono a vicenda. A fine ondata le battute vengono fuse nel transcript
**nell'ordine degli step dell'ondata**, e l'ondata successiva parte dal
transcript aggiornato.

**Motivo**: è l'unica semantica coerente con l'esecuzione parallela — oggi la
sequenzialità di `app.py` fa sì che chi parla dopo legga chi ha parlato prima
nello stesso giro (recon C §1.8); in parallelo quella garanzia non può esistere
e va sostituita da una regola esplicita e deterministica.

## D3 — 2026-08-03 · Roster ADV ridotto a 6 teste

**Decisione**: eliminati `media_planner` e `performance_analyst` dal roster ADV;
rientra `social` (Social & Precedent Analyst, voce testuale del roster base).
Composizione finale: market_researcher, creative_strategist, cd, copywriter,
social, producer.

**Motivo**: stanza più piccola = giri più leggeri e meno costosi; il ruolo di
filtro critico torna al social (anti-cliché, precedenti di genere, famiglia
modello diversa da chi genera le idee) invece che a un analista KPI.

## D4 — 2026-08-03 · Effort per testa (teste Claude; cablaggio in Fase 2)

**Decisione** (Director + assistente, 03/08): quando l'effort sarà cablato
(`--effort` sulla CLI in `ClaudeLLM._via_cli`, campo opzionale su `Head`):

| Testa | Effort |
|---|---|
| creative_strategist | `high` |
| cd | `high` |
| copywriter | `high` |
| producer | `low` |
| router (sonnet) | `low` |

- Il Director propendeva per `max` sullo strategist: **rimandato**, non
  bocciato. Motivo: il ramo CLI ha `CLAUDE_TIMEOUT = 240s` e un turno che
  sfora ricade in silenzio sull'API a pagamento (senza timeout) — `max` è
  l'effort più esposto a questo. Si riapre quando `CLAUDE_TIMEOUT` diventa
  configurabile via env (modifica additiva prevista nello stesso cablaggio).
- Le teste Gemini/Grok (market_researcher, social) non hanno effort: restano
  governate dalla creativity (temperatura).
- Vincolo di sequenza: la chiave `effort` NON va aggiunta ai roster JSON prima
  del campo (con default) sulla dataclass `Head` — `from_dict` è `cls(**d)` e
  una chiave sconosciuta manda l'intero file in `.bad`.
- Verificato il 03/08 sulla CLI 2.1.220: flag `--effort` con valori
  `low|medium|high|xhigh|max`; valore invalido → warning e default (non fatale).

## D5 — 2026-08-03 · Timeout CLI: rete di sicurezza, non guinzaglio (FATTO)

**Decisione e implementazione** (stesso giorno): `CLAUDE_TIMEOUT` passa da 240s
a **1800s di default**, sovrascrivibile con la variabile d'ambiente
`CREW_CLAUDE_TIMEOUT`; allo scadere **niente fallback silenzioso sull'API** —
`ClaudeLLM.call()` alza un errore esplicito («nessun fallback automatico») e
decide il front-end. Gli altri errori CLI continuano a ricadere sull'API come
prima. Motivo: nei processi reali da campagna (ricerca, script, effort alto) i
turni lunghi sono normali; un timeout stretto che rifà in silenzio lo stesso
lavoro su un canale a pagamento era il peggio dei due mondi. Coperto da test
(`test_cli_timeout_env_override`, `test_cli_timeout_does_not_fall_back_to_api`).
**Nota**: questo riapre la valutazione `max` sullo strategist (vedi D4).

**Integrazione (stesso giorno, FATTO nel core)**: allo scadere il lavoro già
prodotto **non si butta** — `ClaudeTimeoutError.partial` porta l'output che la
CLI aveva già scritto, da mostrare come bozza.

**D5-bis (03/08, FATTO)**: per gli errori CLI *diversi* dal timeout il
fallback sull'API resta, ma diventa **trasparente**: `ClaudeLLM.last_cli_error`
conserva il motivo (prima un `pass` lo inghiottiva — è l'errore di credito
rimasto invisibile per un'ora nella notte del 03/08), e se cadono entrambi i
canali l'eccezione riporta TUTTE e due le metà («CLI: … · API: …»). Coperto da
`test_cli_failure_falls_back_to_api_transparently` e
`test_both_channels_down_raises_the_whole_truth`. **Design per i front-end
(Fase 2, confermato dal Director)**: allo scadere è **il canale privato della
testa a contattare il Director** — proattivo, come un messaggio in arrivo:
«sto superando il tempo: mi dai altri N minuti o riparto dalla bozza?» — mai
nella stanza comune: il timeout è un fatto tecnico, non un contributo
creativo, e le altre teste non devono leggerlo.

## D6 — 2026-08-03 · Blocco creatività solo dove non c'è temperatura (FATTO)

**Decisione e implementazione**: `build_turn_prompt()` inietta il blocco
«CREATIVE RISK SETTING» **solo alle teste `anthropic/*`**. Prima lo ricevevano
tutte: Gemini/Grok a creativity alta avevano doppio effetto (temperatura E
blocco), non dichiarato dal badge «via temperature». Ora il badge dice la
verità intera. Coperto da `test_build_turn_prompt_block_only_for_anthropic`.

## D7 — 2026-08-03 · Gemini: API, punto (CLI disinstallata)

**Decisione del Director**: «o CLI o API, non ha senso tenerle entrambe —
andiamo con la API». Le teste Gemini restano su `GEMINI_API_KEY`; la Gemini
CLI, installata e ispezionata in giornata (0.53.1), è stata **disinstallata**.
**Motivo verificato prima di decidere**: la CLI non espone la temperatura —
l'abbonamento avrebbe tolto l'unica manopola continua di creatività di Gemini.
La deep research resta possibile in API (grounding Google Search di Gemini,
oltre al gate DuckDuckGo della stanza).

## D8 — 2026-08-03 · Scala creatività ancorata 0-10 (FATTO)

**Decisione del Director** («va bene la scala che hai fatto») e
implementazione stesso giorno: `_CREATIVITY_BLOCKS` passa da 4 fasce a
**11 gradini interi**, ognuno con una regola contabile che dichiara il proprio
numero («dial N/10»). Il 5 resta neutro (nessuna iniezione). Da 0 a 4 la
scala stringe (prudenza crescente verso 0), da 6 a 10 allarga (rischio
obbligatorio crescente: da «almeno una idea rischiosa» a «niente che un
cliente approverebbe al primo sguardo»). Vale solo per le teste `anthropic/*`
(D6); Gemini/Grok restano su temperatura pura. Coperto da
`test_creativity_block_bands` (unicità di tutti gli 11 gradini inclusa).

## D9 — 2026-08-03 · Deep research: gate + comando Director, niente toggle

**Decisione del Director** (approvata la proposta): la ricerca profonda entra
nella grammatica della stanza per due vie, entrambe sotto il controllo del
Director e caso per caso:

1. **Gate**: `RESEARCH_REQUEST: <tema> || <perché>`, parallelo a
   `SEARCH_REQUEST` — la testa la chiede, il Director approva/nega/riscrive
   (fail-closed, motivo visibile), all'approvazione parte il loop.
2. **Comando diretto**: il Director la ordina a una testa senza aspettare che
   venga chiesta.

**Niente toggle/modalità persistente**: un modo che resta acceso produce
ricerche non richieste — contrario alla filosofia del permesso per caso.

**Forma del loop**: 3-5 query dal tema → ricerca per ognuna → un giro mirato
sui buchi (max 2-3 giri totali) → sintesi con fonti in un blocco
`RESEARCH DIGEST` che entra nel transcript, ispezionabile. I tempi lunghi
sono coperti da D5 (timeout largo, bozza salvata, richiesta nel privato).

## D10 — 2026-08-03 · Un solo campo `effort` per testa, tradotto per famiglia

**Decisione del Director** («extended thinking per tutte»): il roster avrà un
solo campo opzionale `effort` per testa; il core lo traduce nella manopola
giusta di ogni famiglia:

- `anthropic/*` → flag `--effort` sulla CLI (valori verificati D4);
- `gemini/*` → parametro di profondità di thinking via API (i 3.x sono
  modelli thinking nativi) — da smoke-testare al cablaggio;
- `xai/*` → i grok-4.x ragionano di default; manopola esplicita da verificare
  al cablaggio, altrimenti il campo per loro è no-op dichiarato.

Vincolo di sequenza invariato (D4): prima il campo con default sulla
dataclass `Head`, poi la chiave nei JSON. Da implementare in Fase 2 insieme a
D9 e al resto del cablaggio.

**FATTO (Fase 3, 03/08)**: campo `Head.effort` + flag `--effort` in
`ClaudeLLM._via_cli`, router a `low`, livelli D4 nel `roster.adv.json`.
Nello stesso giro cablati anche gli agganci del contratto §7:
`last_plan_route()` (il `router_degraded` è stato emesso DAL VIVO al primo
fallback reale durante l'accettazione) e `ClaudeLLM.last_route` per-istanza
(badge `sub`/`api` per turno). Restano per la Fase 4: D9 (RESEARCH_REQUEST)
e il contatto proattivo dal canale privato al timeout (D5).

## D11 — 2026-08-03 · Disciplina licenze (rettificata: uso personale, repo pubblico)

**Rettifica del Director (12:48)**: il prodotto NON è destinato alla vendita —
è per uso personale; il «fai come se fosse in vendita» era uno sprone alla
qualità. La due diligence (`docs/recon/D-alternative-ui.md`) resta valida ma
la premessa commerciale di quel documento va letta come finzione dichiarata.

**Cosa resta vero comunque, e perché**: questo repo è **pubblico** su GitHub,
e pubblicare È distribuire. Quindi:

- **Nel codice del repo entra solo MIT o Apache-2.0**, con attribution nei
  commenti (prassi già in uso in `web/`): incorporare GPL/AGPL in un repo
  pubblicato con altra licenza sarebbe una violazione a prescindere dalla
  vendita.
- **La licenza si verifica sul file `LICENSE`, mai sul badge o sul README**
  (due dei sei progetti valutati dichiaravano MIT senza avere il file;
  «nessuna licenza» = tutti i diritti riservati).

**Cosa si rilassa con l'uso personale**: strumenti e app di terzi USATI
accanto al progetto (non incorporati nel codice) vanno bene con qualunque
licenza; Commons Clause e CC-NC mordono solo la vendita, che non c'è. Se un
giorno la destinazione cambiasse davvero, la sezione licenze della recon D
torna normativa così com'è.

**Riaperto su decisione del Director (12:50)**: **lobe-chat** come
riferimento UX (studio + esecuzione locale, mai copia di codice nel repo
pubblico) — in agenda per la fase di rifinitura visiva, insieme al canvas
CopilotKit dal vivo.

**Esito della ricognizione**: nessuna alternativa pronta fa quello che
costruiamo (nessuna ha una timeline agente-agente con relazioni `to`
strutturate); la strada custom è confermata.

## D13 — 2026-08-03 · Contratto v1.1: privato, collab, tetto 20 (FATTO)

**Fase 5.1-5.3** (estensione additiva, documentata in EVENT-CONTRACT §8):

- **`private_message`** browser→server: chat 1:1 coi canali privati di
  `RoomSession` (stagni per costruzione); i turni privati non toccano mai la
  timeline di stanza. **Gate disattivo nel privato in v1.1** (una
  `SEARCH_REQUEST` nel privato viene rimossa e loggata).
- **`collab_round`** server→browser: contatore della collab; `/auto N` o
  trigger naturale del core; **tetto duro web a 20 giri** (il core ne
  consentirebbe 50: la specifica web vince, applicata dal server, core
  intatto); stop chiude a fine giro corrente; gate attivi nei giri.
- **Roster a runtime**: `add` completato lato server (chiave validata,
  modello solo da whitelist), editor nella UI; effetto dal turno successivo.
- Contatore di sessione «turni in abbonamento / via API» dagli eventi
  `turn_route`.

**Fase 5.4-5.8 (stesso giorno, FATTO)**: diff a parole della Versione Finale
(ogni approvazione crea una versione; inserzioni/cancellazioni evidenziate,
attivabile/disattivabile); storico sessioni da `GET /api/sessions[/{stamp}]`
in sola lettura (guardia anti-traversal sulla forma dello stamp, testata);
filtro timeline per agente + ricerca testuale nel transcript; esporta
campagna in Markdown scaricabile e PDF **via dialogo di stampa del browser**
(scelta dichiarata: zero dipendenze), con brief, decisioni, versione finale
e ricerche approvate con fonti.

## D19 — 2026-08-03 · Twist dei due copywriter (ricerca) (FATTO)

Ricerca approfondita (`docs/recon/E-copy-pair.md`) su magnum vs Opus 4.8.
Personas riscritte perché siano complementari e si sfidino, sul modello della
coppia copywriter/art-director di Bernbach:
- **Copywriter (magnum) = «il liquido»**: apre, butta territori già in voce,
  osa la riga indicibile, NON giudica.
- **Copywriter 2 (Opus 4.8) = «il recipiente»**: giudica con 3 prove
  (brief/claim/originalità), uccide, sceglie, chiede una cosa in più, chiude
  l'esecuzione; i propri tic («It's not X, it's Y») messi al bando nella persona.
Base teorica: l'auto-correzione intrinseca peggiora (Huang et al.), serve un
critico terzo (Liang et al.). **Da fare**: test cieco 30 min (10 headline a
testa sullo stesso brief) per confermare che magnum porta idee, non solo tono.

## D18 — 2026-08-03 · Contesto di stanza condiviso e ampio (FATTO)

Il core passava solo **8000 caratteri** di transcript a ogni testa (~2000
token): le teste erano quasi cieche sulla storia. Ora un budget UNICO e
condiviso: `CONTEXT_CHARS = 60000` (~16k token), sovrascrivibile con
`CREW_CONTEXT_CHARS`; il router usa `ROUTER_CONTEXT_CHARS = 12000`.

**Vincolo dichiarato al Director**: le teste Featherless (magnum, EVA) hanno
finestra **32.768 token totali** (contesto+risposta) — è un muro fisico, non
possono andare «oltre i 32k». Il budget condiviso è tenuto sotto quel tetto
per lasciare spazio a persona, istruzione e a un turno lungo. Se un giorno
servisse contesto davvero >32k, quelle teste andrebbero su modelli a finestra
grande (Claude/Gemini 1M), non sui 72B Featherless. Coperto da test
(`test_build_turn_prompt_truncates_context`, `test_context_chars_env_override`).

## D17 — 2026-08-03 · Assegnazione modelli alle teste + Copywriter 2 (FATTO)

Roster ADV portato a **8 teste** su scelta del Director (AskUserQuestion):
- **Copywriter → magnum-v4-72b** (Featherless): la voce creativa dark.
- **Dark Angel** (nuova, EVA-Qwen2.5-72B): storyteller senza freni, `@dark_angel`.
- **Copywriter 2 → claude-opus-4-8 a effort MAX** (nuova): seconda voce di
  copy, precisa e affilata, in contrasto con magnum — due opzioni di headline
  da motori diversi. `claude-opus-4-8` aggiunto a VERIFIED_MODELS; la CLI in
  abbonamento lo serve anche a effort max (smoke test PONG, 03/08).

Nota magnum/OpenRouter: magnum sta su ENTRAMBI (Featherless e OpenRouter).
Scelto Featherless perché il Premium del Director rende le richieste illimitate
a costo marginale zero, mentre OpenRouter fattura a token. Cambiabile in
`openrouter/anthracite-org/magnum-v4-72b` se si preferisce.

## D16 — 2026-08-03 · Scelta modelli creativi open (FATTO)

Prefisso `openrouter/` aggiunto agli OPEN_MODEL_PREFIXES; chiave
`OPENROUTER_API_KEY` in `.env` (fornita dal Director, da rigenerare dopo i
test come la Featherless). Modelli proposti nell'editor, **provati dal vivo**
sullo stesso brief dark di prova (un brand denim, campagna volutamente cruda):

- **`featherless_ai/anthracite-org/magnum-v4-72b`** → la testa CREATIVA. È
  Qwen2.5-72B ri-addestrato per la prosa tipo Claude 3; voce migliore, dark
  e coerente, formato rispettato. Confermato anche online (modello narrativo
  open molto popolare).
- **`featherless_ai/zetasepic/Qwen2.5-72B-Instruct-abliterated`** e
  **`.../huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2`** → abliterated puri
  (tolgono i rifiuti, non aggiungono talento): per la testa che deve solo
  non-rifiutare il gore. Il 14B è il «poche parole» veloce.
- **`openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition`** →
  creativo+uncensored, ma **italiano traballante** (24B Mistral): meglio in
  inglese.

Esclusi (tornavano `content` vuoto — reasoning-model che non consegnano in un
turno): Huihui-Qwen3.5-27B-abliterated e MiniMax-M2.1.

## D14 — 2026-08-03 · Modelli open (Featherless / Ollama) e upload documenti (FATTO)

**Modelli open** (richiesta Director: MiniMax e Huihui-Qwen3.5-27B-abliterated):
il core ammette i prefissi `featherless_ai/` e `ollama/` oltre alla whitelist
Claude/Gemini/Grok (`core.model_allowed`), serviti dal percorso litellm già
in uso per Grok. Chiave `FEATHERLESS_AI_API_KEY` in `.env`. MiniMax-M2.1
(229B) richiede Featherless Premium senza limite di taglia; l'abliterated 27B
sta su Premium o in locale via Ollama. Motivazione d'uso: un modello con i
rifiuti rimossi serve dove un Claude/Gemini bocciano (es. campagna gore).
**Non smoke-testato dal vivo** (nessuna chiave in sessione): prima chiamata
vera a carico del Director.

**Upload documenti** (Fase 7): `POST /api/upload` estrae il testo da PDF
(pdfplumber) e testo/markdown; l'immagine è accettata ma senza estrazione
(serve un modello vision, non nel core v1). La UI (graffetta nell'input)
manda il documento come UN messaggio del Director, così passa dal solito
router — **nessuna @menzione = lo smistatore decide chi studia**, una
@menzione = la testa la scegli tu. Verificato dal vivo: brief PDF caricato,
router → Market Researcher + Creative Strategist, entrambi hanno studiato
il brief e risposto.

**Correzioni UX** (dalla critica impeccable, 31/40): empty state che insegna
la stanza al primo avvio (era vuota, P1); pulsante «riprova» sulla card in
errore (P2); barra filtri che va a capo sotto i 640px (P2).

## D15 — 2026-08-03 · Visione immagini (solo Gemini) e brief scritto (FATTO)

**Visione** (scelta del Director fra tre opzioni): in v1.1 le immagini le
legge SOLO una testa Gemini (`vision_capable` = `gemini/*`), via il percorso
multimodale di litellm (`head_study_image`, additivo, non tocca la CLI di
Claude text-only). L'upload di un'immagine viene smistato in automatico alla
prima testa Gemini del roster (`vision_head`); se non ce n'è, lo si dice, non
si finge. Il server tiene i byte in una cache RAM piccola fra upload e
`study_image`. Coperto da test (routing alla testa Gemini, id scaduto).

**Brief scritto a mano**: bottone «Manda il brief alla stanza» nella sidebar
che compone i 4 campi (obiettivo/budget/target/KPI) in un messaggio del
Director — si apre la stanza senza allegare nulla.

**Chiave Featherless**: fornita dal Director, va in `.env`
(`FEATHERLESS_AI_API_KEY`, già ignorato da git). ⚠️ La scrittura via strumenti
è stata BLOCCATA dai permessi (protezione giusta): la mette il Director con
`!`. Consigliata la rigenerazione dopo i test (chiave vista in transcript).
Script di analisi catalogo/confronto: `scripts/featherless_analysis.py`.

**Analisi Featherless eseguita dal vivo (03/08, chiave attiva)**:
- Catalogo: 21.632 modelli, tutti sul piano Premium. **Il tetto di output NON
  è 32k universale**: `max_completion_tokens` = None su 15.879, 4096 su 4.524,
  2048 su 910, e **32768 solo su 319 modelli** — il 32k è il massimo, non la
  regola. La tua osservazione era invertita.
- **Trappola dei modelli reasoning**: il tuo `Huihui-Qwen3.5-27B-abliterated`
  e `MiniMax-M2.1` in una singola chiamata **restituiscono `content` vuoto**:
  spendono tutto il budget nel campo `reasoning`/thinking (`finish_reason:
  length`). Per generare copy in un turno sono la scelta sbagliata: pensano e
  non consegnano.
- **Migliori per copy creativo/dark** (72B non-reasoning, rispondono diretti e
  on-brand, provati sul prompt dark di prova): `anthracite-org/magnum-v4-72b`
  (il più forte sulla scrittura), `llmfan46/Tower-Plus-72B-ultra-uncensored-heretic`,
  `zetasepic/Qwen2.5-72B-Instruct-abliterated`. Contesto 32k, concorrenza 4.
- Raccomandazione: nel roster, per la testa "senza freni" usare un 72B
  abliterated/magnum, non un reasoning-model.

## D12 — 2026-08-03 · @menzioni deterministiche e gate uno-alla-volta (FATTO)

**Fase 4**: una @menzione del Director (`@cd`, `@copy`, `@researcher`, …)
**scavalca il router** — un'ondata parallela con le teste nominate, zero
chiamate LLM di instradamento: è la via d'uscita promessa dal banner
«instradamento ridotto» e funziona anche col router morto. I gate di ricerca
si propongono **uno alla volta** (gli altri mostrano «in coda»); il fallback
API di Claude e ogni eccezione prima ingoiata ora lasciano log (D5-bis, e
`log = logging.getLogger("crew_cast")` sui punti che facevano `pass`). Da cannibalizzare in Fase 3:
l'apparato HITL di Agent Chat UI (MIT, stesso stack), i pattern eventi di
AG-UI (SNAPSHOT accanto a DELTA per la riconnessione — candidato per il
contratto v2), e AgentTeams come riferimento di tesi.

## D20 — 2026-08-04 · Account Director al posto del media planner (FATTO)

**Decisione**: la stanza ADV guadagna un'ottava… nona testa, **Account
Director** (`account_director`, Claude Opus 5, effort high, creativity 3), e
sparisce l'ultimo riferimento al **media planner** (era già stato eliminato
come testa in D3; restava solo citato nella persona dello Strategist, ora
reindirizzata all'Account Director).

**Contesto**: alla domanda «cosa manca alla dream team da Mad Men?» il buco
vero non erano i canali (media planner) ma **la voce del cliente e della
realtà commerciale** nella stanza — la tensione account/creativi che rende
viva un'agenzia. L'Account Director non genera idee (perciò creativity bassa):
fa da avvocato dell'idea davanti al cliente e da freno quando la stanza si
innamora di qualcosa di invendibile o indifendibile (brand safety, legale, il
gore che fa perdere l'account). Su Claude per lucidità e diplomazia, non gore;
subscription-first come le altre teste `anthropic/*`.

**Conseguenze**: nessuna modifica al server/frontend — il roster è caricato a
runtime e il router lo instrada da sé. Aggiornato il mock `web/src/mocks/
roster.ts` ai 9 head per la coerenza della demo.

## D21 — 2026-08-04 · Collab «libera»: le teste parlano finché hanno di che dire (FATTO)

**Decisione**: accanto alla collab a **N giri fissi** (D-Fase5) arriva la
collab **libera/organica**: la stanza va avanti da sola finché ha qualcosa da
dire, non per un numero prefissato. Trigger: «…finché avete qualcosa da dire»
(o «liberamente», «a oltranza») e il comando `/auto libero`.

**Meccanica**: ogni giro il router sceglie chi parla (già emergente, non
round-robin — è il `to` che fa parlare le teste tra loro). La novità è lo
**stop dinamico**: a una testa senza altro da dire si chiede di rispondere
`[PASS]`; quando un intero giro è tutto-PASS per **due volte di fila**
(`_DRY_ROUNDS_TO_STOP`) la corsa si chiude da sé (`collab_round` finale con
`reason: "exhausted"`). Resta una **cintura di sicurezza** dura,
`CREW_ORGANIC_CAP` giri (default 30): «senza struttura» completo è la trappola
da evitare — due modelli lasciati soli convergono e si ripetono
(degeneration-of-thought, Liang et al., citato in `docs/recon/E-copy-pair.md`)
e ogni giro costa token. Lo stop del Director resta sempre disponibile
(`reason: "stopped"`).

**Conseguenze**: additive. Core intatto (la logica libera vive nel server,
`crew_cast.py` non cambia firme); contratto esteso con `mode`/`reason` su
`collab_round` (v1.2); `_run_plan` accetta un `collector` opzionale per contare
i PASS senza toccare gli altri chiamanti. Test: `_collab_mode` (fixed vs
organic) e un e2e che prova la chiusura per esaurimento ben prima del tetto.
Il **toggle** lato UI (Sidebar «Discutete fra voi»: N giri ↔ Libera + Avvia)
manda `/auto N` o `/auto libero`, così il router capisce la modalità senza che
il Director debba ricordare la frase.

## D22 — 2026-08-04 · Panchina: attivare/disattivare le teste (FATTO)

**Decisione**: il Director può mettere una testa **in panchina** e farla
rientrare, decidendo chi partecipa alla riunione. Una testa in panchina **non
viene instradata** dal router, **non entra in collab** e **non risponde nemmeno
a una @menzione** — ma resta **raggiungibile in privato** (la panchina è
"non partecipa alla riunione", non "sparita"). Toggle sulla card di ogni testa
nella Sidebar (⏻); la card in panchina è sbiadita e segna «in panchina».

**Meccanica**: il server tiene `Room.disabled: set[str]`; il router riceve una
**vista filtrata** del roster (`_routing_roster()`) con le sole teste attive —
i turni veri girano comunque sul roster reale e sulla sua cache di LLM. Guardia
gemella di `remove_head`: **la stanza non può restare senza teste attive**
(l'ultima non si disattiva, lato UI e lato server). La UI è la fonte dello
stato (il flusso eventi non ha replay) e lo rispecchia col messaggio
`head_active`.

**Conseguenze**: additive. `crew_cast.py` intatto (firme invariate: il filtro
è una `Roster` costruita al volo che condivide `_llms`); contratto esteso con
`head_active`; nuovo stato UI in `App.tsx` passato alle due Sidebar (desktop e
drawer). Test: una testa benchata è fuori dal router; la stanza non si svuota.

## D23 — 2026-08-04 · Grok fa ricerche social (gate social + Live Search) (FATTO)

**Decisione**: Grok (Social & Precedent Analyst) diventa il **ricercatore
social** della stanza, su tre livelli, tutti additivi e opt-in dove costano:

1. **Persona** (già attiva): la persona lo spinge a usare il gate di ricerca
   (`SEARCH_REQUEST`, già disponibile a tutte le teste via ROOM_RULES) per
   trend/precedenti reali invece di andare a memoria. Backend: DuckDuckGo.
2. **Tool "social intel" agganciabile** (es. il TikTok analyzer): nuova riga
   `SOCIAL_INTEL: <query> || <perché>` che passa dallo **stesso gate HITL** del
   SEARCH_REQUEST ma chiama `social_intel()` — un **comando esterno
   configurabile** (`CREW_SOCIAL_TOOL_CMD`), spento di default. Il repo pubblico
   **non cabla nessun percorso**: il comando decide cosa fa (leggere un
   `signal.json` già prodotto = gratis, o lanciare uno scrape live = pesante).
   Due script d'esempio in `scripts/` (`social_tool_signal.py`,
   `social_tool_scrape.py`) leggono l'analyzer da `TIKTOK_ANALYZER_DIR`.
3. **Grok Live Search nativo** (X + web in tempo reale): opt-in via
   `CREW_GROK_LIVE_SEARCH` (ha un costo per fonte). Passa come `extra_body`
   → litellm → corpo della richiesta xAI (`search_parameters`, `mode: auto`).

**Contesto**: richiesta del Director — «voglio che grok faccia ricerche social»
e «potrebbe usare il mio tiktok analyzer?». L'analyzer NON è una search box: è
una pipeline brand-config (ingest → analyze → build_signal → `signal.json`).
Perciò il livello leggero (leggere il signal) è quello consigliato d'uso
quotidiano; lo scrape live resta possibile ma caro/lento.

**Conseguenze**: additive. Core: `SOCIAL_RE`, `parse_social_request()`,
`social_intel()` (subprocess con timeout e sentinelle), flag Live Search in
`make_llm` — nessuna firma esistente cambiata. Server: `run_turn` rileva anche
il SOCIAL_INTEL, il gate porta `kind`, `settle_gate` sceglie il backend per
tipo. Contratto: `kind` su `search_pending`/`search_result` (retro-compatibile).
UI: GateBlock rietichetta («tool social» + icona radar). `.env.example`
aggiornato. Test: parser, `social_intel` (off + comando), flag Live Search, e un
e2e che prova che il gate social usa il backend giusto e non tocca `web_search`.

## D24 — 2026-08-04 · Chainlit rimossa (FATTO)

**Decisione**: `app.py`, `chainlit.md` e `.chainlit/` escono dal repo. D1
diceva «la web app sostituisce Chainlit»: la sostituzione è compiuta, la
faccia storica non ha più motivo di esistere nel working tree.

**Contesto**: era una chat lineare sull'API v1 del core — niente ondate a
video, niente cross-talk, nessuna vista di stanza. I suoi comportamenti buoni
(intake, gate fail-closed, errori per testa) vivono nella ADV Room dal
porting di Fase 3-4. La diagnosi resta in `docs/recon/C-chainlit.md`; il
codice resta nella storia git (recuperabile con un checkout).

**Conseguenze**: README aggiornato (due facce, non tre); `chainlit` non era
nei requirements, quindi nessun cambio di dipendenze.

## D25 — 2026-08-04 · Onboarding chiavi al primo accesso (FATTO)

**Decisione**: chi apre la ADV Room senza chiavi non viene più rimandato
all'editor di testo: la UI mostra un **modulo di primo accesso** (KeyGate) che
chiede le chiavi mancanti e le invia a `POST /api/keys`, che le scrive nel
`.env` locale (gitignorato) e in `os.environ` del processo. È il prerequisito
per pubblicare la ADV Room: **il repo non contiene mai chiavi**, ognuno
collega le proprie al primo avvio.

**Guardrail**: whitelist chiusa dei nomi (le 3 obbligatorie + Featherless/
OpenRouter facoltative) — niente scrittura arbitraria di variabili; valori mai
loggati e mai rimandati indietro (la risposta porta solo i NOMI salvati);
scrittura atomica con permessi 600; il resto del `.env` (commenti, altre
variabili) sopravvive. Il caso «server non raggiungibile» resta un banner:
non c'è nessuno a cui POSTare. `CREW_ENV_FILE` permette ai test di puntare
un file temporaneo.

**Conseguenze**: additive. Nuovo endpoint REST + componente `KeyGate.tsx`;
il banner chiavi in `App.tsx` è sostituito dal gate a schermo intero (il
banner resta solo per il server irraggiungibile). Test: whitelist, update
in place del `.env`, valori mai in risposta, 400 su payload invalido.

## D26 — 2026-08-04 · La faccia terminale diventa privata: il repo pubblico è la ADV Room (FATTO)

**Decisione**: il repo pubblico contiene **solo la ADV Room** (motore +
server + web + docs). Tutta la faccia terminale — `room_tui.py`, i demo CLI
storici (`room.py`, `room.sh`, `demo.sh`, `demo_listener.py`,
`brainstorm_crew.py`, `step1.py`), `launcher.sh`, `BUILD_BRIEF.md`,
`tests/test_tui.py` — esce dal tracking e resta **privata, solo in locale**
(«quella la uso io»). README riscritto da zero come ADV Room.

**Meccanica**: `git rm --cached` (i file restano su disco: `crew-tui`
continua a funzionare identico) + `.gitignore` perché non rientrino;
snapshot completo nel branch **locale** `tui-local` (mai pushato) come rete
di sicurezza. `textual` esce dai requirements pubblici (serve solo alla TUI:
in locale è già nel venv; se si ricrea il venv, `pip install textual`).

**Avvertenze**: (1) la storia è stata **riscritta il 04/08 sera** con
git-filter-repo (`--refs refs/heads/main`: TUI purgata da TUTTA la storia,
26 commit; albero del tip verificato identico al pre-rewrite; `tui-local` e
il remote intatti). Il force push del ramo riscritto lo lancia il Director a
mano — la deny rule di sicurezza impedisce a Claude i `push --force`, ed è
giusto così. Gli SHA vecchi restano raggiungibili su GitHub per link diretto
finché la cache non li scarta. (2) ⚠️ precisazione onesta sul primo verbale:
`git clean -fd` NON tocca i file ignorati — la TUI è al sicuro dal `-fd`
semplice; il pericolo reale è `git clean -fdx`/`-fdX`. Guardrail installati
(04/08): deny `Bash(git clean*)` nelle impostazioni Claude + wrapper `git()`
in `~/.zshrc` che blocca ogni `git clean` interattivo (scappatoia esplicita:
`command git clean …`); recupero estremo: branch `tui-local`. (3) I test
locali restano 116 (pytest raccoglie `test_tui.py` dal disco); un clone
pubblico ne vede ~46 (core + server), ed è giusto così.

## D27 — 2026-08-12 · Goal mode: la stanza persegue un obiettivo da sola (FATTO)

**Decisione**: nuovo trigger `/goal <obiettivo>` nel messaggio del Director.
La stanza gira a ondate come in collab mode, ma invece di fermarsi per numero
di giri o per silenzio, un **giudice separato dalla stanza** (`core.judge_goal`,
stesso motore del router — non una testa, non chi sta inseguendo l'obiettivo)
valuta il transcript contro l'obiettivo dopo ogni giro e assegna uno score
0-10 + un verdetto `met`. La corsa si ferma quando `met` è vero, quando il
Director manda `stop`, o al tetto `WEB_GOAL_CAP` (env `CREW_GOAL_CAP`,
default 8) — mai altrimenti.

**Contesto**: pattern preso da fuori (Ralph loop / "loop engineering" —
Claude Code `/goal`, Codex CLI `/goal`, entrambi derivati dallo stesso pattern
di Geoffrey Huntley): un ciclo pianifica-agisci-verifica con condizione di
stop esplicita, tetto obbligatorio, criteri di successo dichiarati prima di
partire. La ADV Room aveva già i due terzi del meccanismo (route_plan a
ondate + `_run_collab` per il ciclo, session persistita su disco a ogni
giro — lo stato non vive nel contesto di un singolo processo, sopravvive a
un crash); mancava solo il terzo pezzo: una condizione di stop legata a un
obiettivo del Director invece che a un numero di giri o al silenzio della
stanza.

**Perché un giudice a parte e non una testa**: le teste della stanza sono
scritte per generare, non per certificare — lasciare che una di loro
giudichi il proprio lavoro (o quello dei colleghi) è la stessa fiducia mal
riposta che porterebbe a fidarsi della memoria di un modello per un fatto
verificabile. Stesso principio già applicato al router (`route_plan` non è
una testa) e al gate di ricerca (fail-closed, mai un dato inventato).

**Guardrail**: (1) tetto obbligatorio — un giudice rotto o un obiettivo
irraggiungibile costano al massimo `WEB_GOAL_CAP` ondate, mai un loop
infinito; (2) fail-closed sul judge — output illeggibile o chiamata fallita
→ `met: false`, mai un verdetto inventato, il giro comunque consuma il
tetto; (3) `stop` del Director resta valido a ogni giro, come in collab.

**Conseguenze**: additive, nessuna firma esistente cambiata. Core
(`crew_cast.py`): `llm_claude_judge`, `JUDGE_PROMPT`, `parse_goal_verdict`,
`judge_goal` — stesso stile paranoico di `parse_wave_plan`/`route_plan`.
Server (`server/main.py`): `Room._goal_mode` (controllato PRIMA di
`_collab_mode`, che resta intatto) e `Room._run_goal`, tetto
`WEB_GOAL_CAP`. Contratto: nuovo evento `goal_verdict`; `collab_round.mode`
si allarga a `"goal"`, `collab_round.reason` a `"met"` (vedi
`docs/EVENT-CONTRACT.md` §9). UI agganciata (commit `093ba56`, 07/10/2026):
fold degli eventi goal, GoalPanel in regia (lanciatore + obiettivo/giro/
punteggio), banner e aiuto comandi — verificata dal browser con un
obiettivo vero. Test: 9 nuovi (`tests/test_core_ext.py`: judge + parser;
`tests/test_server.py`: trigger, obiettivo raggiunto, tetto senza successo,
judge indisponibile) — 130 verdi in locale, nessuna regressione.

## D28 — 2026-11-25 · Dopo la prova «da cliente»: guardrail, onestà, lingua, proposta (FATTO)

Una prova completa con un brand fittizio (documenti, immagini, ricerca, goal
mode, export) ha trovato otto difetti. Cause radice **misurate**, non ipotizzate.

**Executive Producer lento (2-5 min) + token `<|im_end|>` nel testo**: stessa
causa. Hermes-3-70B su Featherless non si ferma dopo la fine-turno: risponde
«Azzurro<|im_end|>» e **continua inventando un turno dell'utente**, fino al
limite del contesto. Non era concorrenza (due 70B in parallelo: 4 s). Fix: ogni
LLM open (`featherless_ai/`, `openrouter/`, `ollama/`) nasce con stop-token,
tetto di token (`CREW_MAX_REPLY_TOKENS`, 900) e timeout duro
(`CREW_OPEN_MODEL_TIMEOUT`, 120 s); `strip_special_tokens` taglia alla prima
fine-turno. Misura prima/dopo: 4 teste Featherless in parallelo 24,6 s → 5,1 s;
turno vero del produttore con transcript da 14k caratteri 12,2 s.

**«Instradamento ridotto» (router a ondate in fallback)**: il router è
`ClaudeLLM("claude-sonnet-5", effort="low")`, NON la testa Producer (la prima
ipotesi era sbagliata). In 20 prove offline con dati reali: 20 piani validi,
quindi la causa dal vivo **non è ancora nota**. Fatto solo ciò che serve a
trovarla: ogni piano scartato logga l'output del modello, e il passaggio dalla
CLI all'API a pagamento non è più silenzioso. Il contratto del parser NON
cambia (un array piatto resta non valido, come da test esistente).

**Onestà (il modello non mente mai)**: blocco HONESTY in `ROOM_RULES` per tutte
le teste (niente «ho visto/cercato/verificato» se non è vero; le immagini si
conoscono solo dalla descrizione di un collega) + riga CAPABILITIES per testa
(testo solo vs visione).

**Lingua**: le teste rispondono nella lingua del Director (prima: «Speak in
English» fisso). Il giudice scrive il motivo nella lingua del goal.

**Interfaccia**: `App` montava layout desktop e mobile insieme, nascondendone
uno col CSS → ogni componente esisteva due volte (brief doppio, «Approva»
nascosto cliccabile, brief vuoto nell'export). Ora un layout solo
(`useMediaQuery`) e stato condiviso di campagna (`state/campaign.tsx`).
Upload: più file per messaggio (max 8), documenti in un solo messaggio,
immagini a parte. Titolo della proposta derivato anche dal body.

**Proposta a goal raggiunto**: nuovo evento `proposal_drafted` (vedi
`docs/EVENT-CONTRACT.md` §10), estratto e mai inventato, fail-closed.

**Test**: pytest 131 → 184, vitest 35 → 56, tutto verde.

## D29 — 2026-11-25 · Modelli scelti con misure: produttore e Dark Angel (FATTO)

Metodo: criteri e soglie **scritti e committati prima di misurare**, giudice
`claude-opus-5-5` da CLI, tetto di spesa imposto dal banco di prova (limite
superiore dal listino reale, rifiuta di partire se lo supera). Dettaglio in
`evals/` (criteri, risultati, note).

**Executive Producer → `anthropic/claude-sonnet-5-5` (CLI, nessuna spesa).**
v1 (persona di una frase): nessuno passa, tutti scelgono l'idea quando il
Director lo ordina. v2 (persona riscritta, una sola variabile cambiata,
dichiarato come secondo tentativo): passano Sonnet 5.5 (p95 20,1 s) e Haiku 5.5
(25,4 s); Hermes-3 e Qwen2.5-72B no. La persona ha pesato più del modello.

**Dark Angel → `venice/glm-5-3-flash-uncensored`, creatività 7 (0,87).**
v1: nessuno passa; `abliteration-large-v2` ha ricevuto 12 HTTP 400 (nostra
temperatura 1,09 > 1, corretto con un massimo per provider) e il testo degli
altri era rovinato. v2 (temperatura 0,9, una variabile): una pausa di ~33 min
della macchina ha viziato una chiamata per candidato; rifatti solo i due che
fallivano solo per quello, dichiarato prima. Esito: `aion-3-5-mini` passa tutte
le soglie (D10 6,8, p95 54,9 s) ma Venice non lo dichiara abliterated e la
privacy è «anonymized»; `glm-5-3-flash-uncensored` (abliterated, privacy
«private», p95 7,8 s) sbaglia D7 di uno (8/10; 10/10 nella prima corsa).
**Scelta del Director: glm**, quindi adottato **sapendo che non supera
formalmente il v2**. `abliteration-large-v2` resta non valutato: ragiona sempre
e col tetto di 900 token restituisce testo vuoto; servirebbe un tetto per modello
e costerebbe di più.

**Riserve**: 12 chiamate per candidato e 2 ripetizioni sono poche (D7 di glm è
passato da 10/10 a 8/10 fra due corse: il risultato è rumoroso); giudice della
stessa famiglia dei candidati Claude; un solo brand fittizio, in italiano; la
spesa reale non è misurata (c'è solo il limite superiore, 0,296 $ + 0,296 $ +
0,076 $ su 1 $).

**Conseguenze di prodotto**: massimo di temperatura per provider
(`Provider.max_temperature`); proposte Venice nell'editor ridotte ai modelli
misurati; l'auto-cast preferisce questi due modelli; `VENICE_API_KEY` ora è
richiesta da chi usa il roster ADV così com'è.

## D30 — 2026-11-25 · Dark Angel: giudizio umano alla cieca (FATTO)

**Perché**: il punteggio automatico (giudice Opus) non misura «provocatorio e
intelligente». Creativity Benchmark (arXiv 2509.09702: 678 creativi, 11.012
confronti umani) trova che i giudici LLM correlano poco con gli umani e che i
modelli stanno tutti vicini (il migliore batte il peggiore il 61% delle volte);
«Galton's Law of Mediocrity» (arXiv 2509.25767) che sulle idee pubblicitarie i
modelli tornano alla media. **Non esiste un modello aperto adatto addestrato
sulla pubblicità**: su Hugging Face solo adattatori amatoriali su frasi brevi di
prodotto (TinyLlama, GPT-2, Falcon-7B, Llama-2-7B, Phi-2; 6-40 download), Meta
AdLlama è proprietario e ottimizza i clic. Quindi la leva è la richiesta, e il
giudice è il Director, alla cieca.

**Round 1, aion contro glm (4 scenari)**: aion 2, glm 1, nessuno 1: pareggio
entro il rumore. **Round 2, persona nuova contro vecchia (3 scenari, protocollo
e regola congelati prima, `evals/PROVA-CIECA-darkangel-persona.md`)**: voti
persona nuova 2, vecchia 1; modello glm 2, aion 1. **Esito per la regola: la
persona nuova NON si adotta** (una chiamata nuova di aion ha risposto con una
parola e i controlli dovevano reggere in tutte; letto solo per glm, glm-nuova
vince 1 scenario su 3). Dark Angel resta `venice/glm-5-3-flash-uncensored` con la
persona attuale. Dati in `evals/results/darkangel-blind.json`.

**Riserve**: 1 votante, 3-4 scenari, 1 ripetizione per cella; il «nessuno» su
DA1 nel round 1 e le stonature d'italiano a temperatura 0,9 in entrambi i modelli
dicono che la qualità del testo, non solo l'idea, è un problema aperto. La
persona nuova faceva trapelare il proprio metodo in un testo («Butto via subito
le tre idee ovvie…») e aion sul DA1 non ha consegnato niente.

**Da provare (non fatto)**: più proposte brevi invece di una rifinita, scelte dal
Director (flusso orientato alla diversità, come suggerisce la ricerca); una
temperatura più bassa; un controllo non-abliterated gratuito da CLI.

## D31 — 2026-11-25 · Dark Angel: il controllo non-abliterated (FATTO)

Protocollo e regola congelati prima (`evals/PROVA-CIECA-darkangel-controllo.md`):
Opus 5.5 e Sonnet 5.5 da CLI (nessuna spesa) contro glm e aion, alla cieca,
persona attuale, scenari DA1/DA3/DA5. **Nessun controllo ha rifiutato o
ammorbidito** (giudice automatico, 0 su 6). Voti del Director: aion 1, glm 1,
Sonnet 1, Opus 0. Per la regola: i modelli abliterated vincono 2 scenari su 3,
quindi «l'abliterazione si guadagna il posto». **Lettura onesta: debole.** Un
solo votante, 3 scenari; Sonnet 5.5, gratis da CLI, ha comunque preso un voto.
Soprattutto: su questo brief (una borraccia) i modelli normali **non rifiutano**,
quindi la prova non misura il caso in cui l'abliterazione servirebbe davvero
(temi più duri). Il requisito «Dark Angel abliterated» del Director resta e non
cambia nulla nel roster. Dati: `evals/results/darkangel-control*.json`.

**Dark Angel nel complesso (D30+D31)**: tre prove alla cieca non separano
chiaramente glm, aion e Sonnet. Il guadagno atteso non viene dal modello ma da
come si chiede: da provare più proposte brevi scelte dal Director.

## D32 — 2026-11-25 · Dark Angel: menù di tre idee, tutto rigenerato (FATTO)

Protocollo congelato prima (`evals/PROVA-CIECA-darkangel-menu.md`): quattro modelli
(glm, aion, Opus 5.5, Sonnet 5.5) rigenerati da zero su scenari nuovi (DN1-DN3),
formato «tre idee brevi», elenco unico mescolato, giudice il Director alla cieca.
Punti (3/2/1): **Opus 5, glm 4, Sonnet 3, aion 2**: pareggio per la regola
(distacco 1). Copertura (scenari con un'idea nelle prime tre): glm 2, Opus 2,
Sonnet 1, aion 1. Voti: DN1 Opus + aion; DN2 glm; DN3 Sonnet + Opus + glm.

**Letture, con le riserve**: (1) nessun modello domina, coerente con la ricerca
(i modelli stanno vicini). (2) **Il menù funziona**: in ogni scenario il Director ha
trovato almeno un'idea da tenere, da ognuno dei quattro modelli. (3) **Le scelte
sono poche** (2, 1 e 3 su 10-12 idee): la maggior parte non raggiunge «provocatoria
e intelligente», e una idea è stata scartata come «ok ma non provocatoria».
(4) **Una delle due idee di aion è stata un'infrazione del formato** (4 parole,
«Seppelliamo la vecchia borraccia.») rimasta nel menù come da protocollo: un
indizio che la brevità secca possa funzionare meglio di 50 parole, da verificare,
non una conclusione. Un votante, 3 scenari, 1 generazione per cella.

Dati: `evals/results/darkangel-menu.json` e `darkangel-menu-blind.json`. Il roster
non è stato toccato.

## D33 — 2026-11-25 · Dark Angel risponde con tre idee brevi (FATTO)

Scelta del Director dopo il menù di D32: modello invariato (`venice/glm-5-3-flash-uncensored`),
persona = quella attuale **più** una regola: tre idee numerate, al massimo 50 parole
ciascuna, su angoli diversi tra loro e da quello che la stanza sta già battendo,
senza premesse. Tagline della card: «Three uncomfortable pitches, no brakes.».
Le altre teste non cambiano (test).

**Verifica dal vivo** (3 chiamate vere a glm, senza la richiesta del formato nel
messaggio, circa 0,004 $ di limite superiore): il formato regge **3 volte su 3**
(tre idee numerate, in italiano, nessun token trapelato); il limite di 50 parole
regge **2 volte su 3** (una idea di 85 parole). Restano piccole stonature
d'italiano di glm (es. «si ammacciava»). Il formato non è stato confrontato con la
risposta lunga di prima: l'evidenza è che dal menù il Director ha trovato almeno
un'idea da tenere per scenario, non che il menù batta il testo lungo.

## D34 — 2026-11-25 · Guardrail a runtime (CrewAI fase 2): fatto, soglia NON raggiunta (FATTO)

**Cosa**: `guardrails.py` + `crew_cast.guarded_reply`. Ciò che i bake-off misuravano ora
si impone: il produttore non sceglie/raccomanda l'idea, nessuna testa solo-testo
finge di vedere un'immagine, niente link inventati, Dark Angel dà tre idee brevi,
risposta nella lingua del Director, lunghezza del produttore. Una risposta che viola
una regola viene **rifiutata con il motivo e rigenerata** (default 2 ripetizioni,
`CREW_GUARDRAIL_RETRIES`); per bugie e violazioni del ruolo, a ripetizioni esaurite
si consegna una frase veritiera di ripiego, per i difetti di stile l'ultima risposta
con un warning. Si spegne con `CREW_GUARDRAILS=0`. Le **stesse funzioni girano dentro
un `Task` di CrewAI vero** (`Task.guardrail`, test con un LLM finto): è il primo uso
reale di `Task`/`Agent`, senza cambiare le firme del motore.

**Misura in campione** (96 risposte dei bake-off del produttore, verdetti del giudice;
espressioni corrette guardando quegli stessi dati, quindi **non provano la
generalizzazione**): sceglie l'idea 9/9, finge di vedere 2/3, 0 falsi allarmi su 48
sintesi. La prima versione dava 4 falsi allarmi sulle risposte oneste «Non vedo
l'inserzione» (negazione ignorata): corretti.

**Prova su risposte NUOVE** (`evals/PROVA-guardrail-live.md`, protocollo congelato prima,
persona debole del v1, 24 prove, solo CLI e Featherless): sceglie l'idea **9/12 → 2/12**
consegnate; finge di vedere **2/12 → 1/12**; ripiego usato **0** volte. **La soglia
(0/12 su entrambe) non è raggiunta: il guardrail NON si dichiara «a posto».** Sono
sfuggite a mano: Qwen che scrive «credo che la direzione migliore sia…» (espressione
aggiunta dopo: ora in campione anche quella) e Hermes che descrive l'inserzione senza
verbi di vista (non coperto). Costo: 1,71 chiamate per prova in media, latenza media
~54 s su modelli lenti; una chiamata Hermes è fallita con un errore di Featherless.

**Letture**: (1) il guardrail riduce molto il difetto ma le espressioni regolari hanno un
tetto; (2) con la persona v2 in produzione i modelli Claude non sceglievano già più:
l'effetto reale dei guardrail lì non è misurato; (3) prossimo passo sensato: un
controllo con un modello (CrewAI `LLMGuardrail`) solo per il produttore, una chiamata
in più su CLI gratuita.

## D35 — 2026-11-25 · Account Director → Sonnet 5.5, da misure (FATTO)

Criteri congelati prima (`evals/CRITERI-accountdirector.md`, fe66bce): cinque
candidati, 4 scenari con verità nascosta (6 violazioni piantate in una proposta,
una proposta in regola, le 48 ore di approvazione, il divieto di scrivere copy) × 2
ripetizioni, giudice Opus da CLI, tetto 0,10 $ (limite superiore usato 0,017 $).

**Vince `claude-sonnet-5-5` (CLI, nessuna spesa a consumo)**: passa A1-A9, p95 13,8 s,
trova 6 violazioni su 6, 1 obiezione inventata su una proposta in regola, ricorda le
48 ore, non scrive copy, utilità 8,38. **Haiku 5.5** manca solo A7 (2 obiezioni
inventate in entrambe le ripetizioni). **Qwen2.5-72B, l'Account Director di prima,
fallisce 6 soglie su 9**: p95 35,7 s, italiano 0/8 (risponde in inglese), 4/8 nella
banda di lunghezza, non ricorda le 48 ore, scrive copy 2/2 nonostante la persona lo
vieti, utilità 3,5. I due modelli Venice (Mistral Small 3.2, Qwen3-235B) non scrivono
mai le 48 ore e scrivono slogan in tutte le prove.

**Adottato** con `effort medium` (quello misurato; l'`high` del roster non è mai stato
provato). L'auto-cast lo preferisce, poi Haiku.

**Riserva**: il produttore e l'Account Director ora girano **sullo stesso modello**
(Sonnet 5.5): il roster ha 8 modelli diversi invece di 9, e la quota Claude è
condivisa con router e Strategist. È la conseguenza di scegliere ruolo per ruolo il
vincitore misurato. Se si vuole tornare a 9 modelli distinti, il candidato è Haiku 5.5
per uno dei due (passa il produttore v2, manca solo A7 come Account Director). Limiti:
8 chiamate per candidato, un votante-giudice automatico della stessa famiglia di due
candidati, un solo brand fittizio; le violazioni sono inventate da noi.

## D36 — 2026-11-25 · «Instradamento ridotto»: causa trovata e corretta (FATTO)

Il D28 lasciava aperta la causa del router a ondate in fallback dal vivo: 20
prove offline davano 20 piani validi. Misurata ora con un campione più largo.

**Esclusi con prove**: guasto della CLI (alle 10:40 il router v1, che usa la stessa
CLI, ha funzionato: ha scelto `cd`, che il ripiego senza CLI non sceglie; e il log
del server non ha il warning del ramo d'eccezione); differenze fra la `Room` vera e
la riproduzione (stesso esito con `Room.handle_director`, roster e parser di allora:
0 banner su 5).

**Causa**: il modello del router risponde spesso con un **array piatto** di passi
(`[{…},{…}]`) invece che con le ondate (`[[{…}]]`). Su 60 chiamate reali (4
situazioni della stanza × 15, solo CLI): 28 scartate, 27 piatte con speaker tutti
validi, 1 con ondate di chiavi nude. Il tasso cambia molto per situazione: brief 1/15,
domanda del Director 11/15, goal 9/15, auto 6/15. Per questo le prove offline (solo
brief e auto) lo avevano mancato.

**Fix** (`parse_wave_plan`): un array piatto si legge come passi **in sequenza**, una
ondata per passo (la lettura prudente: un consulto non diventa parallelo); un passo
scritto come chiave nuda prende l'istruzione vuota, che `_run_plan` riempie col
messaggio del Director. Il contratto del D28 («un array piatto resta non valido») era
condizionato alla mancanza di una causa misurata: la causa c'è, e i due test che lo
fissavano sono stati riscritti sul comportamento nuovo, con le risposte vere del
campione come casi.

**Verifica su risposte nuove** (`evals/router_sample.py`, `evals/results/router-sample-dopo.json`):
**60/60 piani validi**, 0 errori, 5 risposte piatte accettate. Prima:
`evals/results/router-sample-prima.json`.

**Trovato strada facendo, non corretto qui**:
- **La CLI che si aggiorna da sola** (npm) sparisce per qualche minuto da
  `/opt/homebrew/bin/claude`: in una corsa 22 chiamate su 60 sono fallite con
  `FileNotFoundError`. Dal vivo questo manda il router (e ogni testa Claude) sull'API
  a consumo, o in fallback se l'API non risponde. È ambientale; ora è almeno nel log.
- **`last_plan_route()` è globale di processo**: con due stanze aperte insieme, una
  può mostrare il banner per il fallback dell'altra. Non spiega il 25/11 (un solo
  WebSocket).
- Nell'interfaccia il banner, una volta acceso, non si spegne più (`degraded` non
  torna a `null` dopo un piano valido).

## D37 — 2026-11-26 · I tre difetti trovati col D36, corretti (FATTO)

**CLI che si aggiorna da sola.** Quando il percorso della CLI sparisce
(`FileNotFoundError`), `ClaudeLLM._via_cli` aspetta che torni, controllando ogni 2 s
fino a `CREW_CLI_MISSING_WAIT` (90 s), e riprova **una** volta. Prima quel buco mandava
la chiamata sull'API a pagamento. Se la CLI non torna entro il tetto, vale il
fallback di prima (D5-bis, ora con un warning nel log). Gli altri errori della CLI non
si riprovano. Test: `tests/test_cli_update_window.py`.

**Esito del router per stanza.** `last_plan_route()` legge prima l'esito registrato
nel thread corrente (`threading.local`), poi il globale; il server lo legge **nello
stesso thread** che ha instradato (`Room._route_plan`), non dopo dal ciclo eventi. Due
stanze in parallelo non si scambiano più il banner. Test che cade col server di
prima: `test_no_banner_for_another_rooms_fallback`.

**Banner nell'interfaccia.** Il banner descrive il piano corrente: un `wave_planned`
con un altro `plan_id` lo spegne (la riga nella timeline resta: è storia). Chiuderlo
vale per quel degrado (il suo `seq`), non per tutti i futuri.

## D38 — 2026-11-26 · Onestà sulle immagini con un modello: molto meglio, soglia NON raggiunta (FATTO)

**Cosa**: per le teste **senza visione** (tutte tranne il Market Researcher), quando una
risposta parla di un'immagine, un modello (`claude-sonnet-5-5`, effort low, **solo CLI**:
mai l'API a pagamento) giudica se presenta dettagli visivi come visti, o dettagli
assenti dal transcript come fatti. Se sì: rifiuto con il motivo, rigenerazione, poi
ripiego veritiero. Guasto della CLI o verdetto illeggibile: la risposta passa con un
warning. Il controllo gira anche sulle risposte respinte solo per stile (l'onestà
viene prima della lingua). `CREW_LLM_GUARDRAIL=0` lo spegne, `CREW_GUARD_MODEL` lo
cambia. Il `LLMGuardrail` di CrewAI non si usa: vuole un `BaseLLM` e con Claude
passerebbe dall'API a consumo.

**Prova a criteri congelati** (`evals/PROVA-onesta-immagini.md`, 45 prove su risposte
nuove: 5 modelli × 3 scenari × 3, giudice Opus):

| | 1ª corsa | 2ª corsa (dopo il fix) | soglia |
|---|---|---|---|
| bugie nelle prime risposte | 26/45 | 25/45 | base |
| bugie consegnate | 3/45 | **1/45** | 0 per scenario: **no** |
| ripiego | 6/45 | **9/45** | ≤ 5: **no** |
| falsi allarmi | 0/19 | 1/20 (5%) | ≤ 10%: sì |

L'espressione regolare del D34 da sola avrebbe preso 9 bugie su 25 (solo quelle con
«Looking at…»). La 1ª corsa ha trovato un difetto vero (una bugia in inglese cadeva
sulla regola della lingua e veniva consegnata): corretto, poi 2ª corsa con soglie
invariate. La bugia rimasta (Hermes, I2) attribuisce al collega ma aggiunge una luce
«che si posa delicatamente» che il collega non ha descritto: controllo e giudice non
concordano su un abbellimento.

**Il dato più importante è per modello**: Sonnet 5.5 e Haiku 5.5 mentono 1 volta su
18 prime risposte; **Hermes, Qwen e magnum mentono in 24 prime risposte su 27, in entrambe le corse**, e
sono loro a finire sul ripiego (9 su 9). La soglia 3 manca perché quei modelli
insistono anche dopo due rifiuti motivati: il ripiego è la frase veritiera, quindi
corretto, ma la stanza perde il loro contributo. In produzione questo tocca il
**Copywriter (magnum-v4-72b)**; Dark Angel (glm, Venice) non è stato misurato.

**Costo**: in media 6-13 s di controllo per risposta che parla di immagini, solo su
quelle; zero sulle altre.

**Non si dichiara «a posto»**: soglie 1 e 3 mancate. Lettura: il controllo porta le
bugie consegnate da 25 a 1 su 45 senza falsi allarmi rilevanti; il limite residuo è
la scelta dei modelli open sulle teste che discutono immagini.

## D39 — 2026-11-26 · Le immagini le riscrive Claude: soglie raggiunte (FATTO)

**Cosa**: scelta del Director dopo il D38 (riferita da un'altra sessione). Il
Copywriter resta su magnum-v4-72b per i testi. Quando una sua risposta parla di
un'immagine, la riscrive `claude-sonnet-5-5` (effort low) partendo dallo stesso prompt,
e se servono ripetizioni le fa sempre Sonnet. Sonnet gira **solo dalla CLI in
abbonamento** (`CliOnlyLLM`, mai l'API a pagamento). Se la CLI sparisce perché si sta
aggiornando, il sistema aspetta e riprova come nel D37. Se la CLI è giù per qualunque
altro motivo, resta la risposta della testa, sotto i controlli del D38. Il passaggio si
decide nel campo `image_model` della testa nel roster (oggi c'è solo sul Copywriter) e
si spegne con `CREW_IMAGE_HANDOFF=0`. Vale solo per le teste senza visione.

**Prova** (`evals/PROVA-onesta-immagini.md` v3, scritta e committata prima in 7505470;
stessa prova del D38, soglie invariate, le tre teste open con `--handoff
claude-sonnet-5-5`; risultato in `evals/results/onesta-immagini-v3.json`):

| | v2 (D38) | v3 (D39) | soglia |
|---|---|---|---|
| bugie nelle prime risposte | 25/45 | 22/45 | base |
| bugie consegnate | 1/45 | **0/45** (0 in ogni scenario) | 0: **sì** |
| ripiego | 9/45 | **0/45** | ≤ 5: **sì** |
| falsi allarmi del controllo | 1/20 | 0/23 | ≤ 10%: **sì** |

- Tutte le 27 prove dei modelli open sono passate a Sonnet. Sonnet e Haiku hanno
  scritto da soli, con 0 bugie nelle prime risposte.
- **Il prezzo della scelta**: 5 prime risposte open erano oneste e sono state riscritte
  comunque. Sui turni che parlano di immagini, la voce di magnum si perde anche quando
  non mentiva.
- **Latenza** delle prove open: in media 35,5 s, contro i 51,3 s della v2. Il ripiego
  dopo due rifiuti costava più del passaggio.
- **Nessuna chiamata all'API a consumo** nella corsa.

**Limiti**: 45 prove, un solo brand fittizio, controllo e giudice sono entrambi Claude.
Nella stanza la riscrittura compare sotto il nome del Copywriter, e il modello che l'ha
scritta si vede solo nel log. Dark Angel (glm su Venice) e Social (Grok) non hanno
`image_model`: non sono stati misurati.
