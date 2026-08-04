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
