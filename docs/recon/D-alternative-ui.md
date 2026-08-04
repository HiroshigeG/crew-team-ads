# Ricognizione D — Alternative UI esistenti per sistemi multi-agente

Due diligence sulle UI multi-agente già esistenti, in vista della web app proprietaria
(React + TypeScript + Tailwind, protocollo WebSocket a contratto già definito) per la
writers' room orientata a campagne ADV. Il prodotto è **destinato alla vendita**: la
verifica delle licenze non è un dettaglio burocratico, è il vincolo che decide cosa si
può toccare e cosa no.

- **Data**: 3 agosto 2026
- **Metodo licenze**: file `LICENSE` letto **dal repo** via API GitHub (`repos/{owner}/{repo}/license`,
  contenuto decodificato) e, dove pertinente, metadati del pacchetto pubblicato su npm.
  Mai la licenza «presunta», mai il badge del README preso per buono.
- **Metodo maturità**: stelle, fork, data dell'ultimo commit sul branch di default,
  letti via API alla data di cui sopra.
- **Nessun codice applicativo** è stato copiato o incollato in questo documento.

**Il nostro bisogno**, come metro di paragone ricorrente nel documento:

1. **timeline di chat unificata** in cui gli agenti si parlano fra loro, visibilmente;
2. **relazioni «chi risponde a chi»** (un campo `to` / reply-to reso graficamente);
3. **Human-in-the-Loop** con un gate di approvazione sulla ricerca;
4. **layout a 3 colonne** (contesto · timeline · proposte).

---

## 0. Il verdetto in una tabella

| # | Progetto | Licenza **verificata** | Stelle | Ultimo commit | Verdetto |
|---|---|---|---|---|---|
| 1 | strnad/CrewAI-Studio | **MIT** (file presente) | 1.333 | 2026-08-03 | Ignorare come prodotto, rubare 2 idee |
| 2 | zinyando/crewai_chat_ui | ⚠️ **Nessun file LICENSE** (README dice «MIT») | 31 | 2025-07-11 | Ignorare |
| 3 | CopilotKit/open-multi-agent-canvas | ⚠️ **Nessun file LICENSE** (README dice MIT) | 517 | 2026-06-05 | Cannibalizzare pattern, con cautela |
| 4 | langchain-ai/agent-chat-ui | **MIT** (file presente) | 3.032 | 2026-08-03 | **Cannibalizzare a fondo** |
| 5 | CopilotKit + AG-UI | **MIT** entrambi (file presenti) | 36.426 / 15.116 | 2026-08-03 | Cannibalizzare il **contratto eventi** |
| 6 | Demo Streamlit varie | MIT / Apache-2.0 / nessuna | — | varie | Ignorare |

**Nessuna delle sei ci fa cambiare idea sulla build custom.** Il motivo è strutturale e
vale la pena dirlo subito: nessuna implementa una timeline agente-agente con relazioni
esplicite «chi risponde a chi». Tutte, senza eccezioni, modellano la conversazione come
**utente ↔ assistente** — anche quelle che si chiamano «multi-agent», dove il
multi-agente sta nel *backend* e il frontend resta un thread lineare a due voci. La
nostra tesi di prodotto (la stanza in cui gli autori si parlano e tu guardi) non ha
un'implementazione pronta là fuori.

Quello che invece esiste, ed è ottimo, è il **vocabolario HITL** (punto 4) e il
**contratto eventi** (punto 5). Quelli si prendono.

---

## 1. CrewAI Studio — strnad/CrewAI-Studio

**Cos'è davvero.** Una GUI Streamlit per *costruire e far girare* crew CrewAI senza
scrivere codice. Non è una UI di conversazione: è un pannello CRUD. Il repo è organizzato
in pagine Streamlit (`app/pg_crews.py`, `pg_agents.py`, `pg_tasks.py`, `pg_tools.py`,
`pg_knowledge.py`, `pg_crew_run.py`, `pg_results.py`, `pg_export_crew.py`) — la struttura
dice tutto: si definiscono agenti, task e tool in form, poi si preme kickoff e si guarda
il log scorrere.

**Stack.** Streamlit + CrewAI. Persistenza su DB locale (`app/db_utils.py`). Usa un fork
di `crewai-tools` con bugfix propri — dettaglio non irrilevante: è un vincolo di
manutenzione ereditato.

**Licenza verificata.** **MIT**, file `LICENSE` presente e leggibile, intestato
«Copyright (c) 2024 Jakub Strnad». Testo MIT standard, nessuna clausola aggiunta.
Nessuna trappola: utilizzabile in un prodotto commerciale mantenendo la nota di
copyright.

**Maturità.** 1.333 stelle, 316 fork, ultimo commit 2026-08-03. Progetto **vivo e
manutenuto**, il più popolare fra le GUI CrewAI dedicate.

**Vicinanza al nostro bisogno: bassa.** Copre l'*authoring* della crew, non la
*conversazione*. Sul HITL: una ricerca nel codice del repo per `human_input` non produce
risultati — non c'è un gate di approvazione, non c'è interruzione né ripresa. E Streamlit
per una timeline viva è la strada che stiamo già abbandonando (ri-render dell'intera
pagina a ogni evento, nessun controllo fine sullo stato).

**Cosa cannibalizzare** (MIT, quindi si può, ma qui parliamo di **idee**, non di codice —
è Python/Streamlit, non ci serve una riga):

- **Il modello a entità separate** Crew / Agent / Task / Tool / Knowledge come oggetti
  CRUD persistiti, non come YAML monolitico. Se un giorno il roster della writers' room
  diventa editabile dall'utente finale, questa è la scomposizione giusta e collaudata.
- **Run in thread con stop.** La crew gira in background e può essere fermata. La nostra
  UI ha bisogno esattamente di questo (un bottone «ferma la stanza» che funzioni davvero),
  ed è un requisito che si dimentica di specificare finché non serve.
- **Export della crew come app a pagina singola.** Idea di packaging interessante per un
  eventuale deliverable-cliente, non per il core.

> **Verdetto: ignorare** come prodotto o base di codice — risolve un problema diverso
> (authoring, non conversazione) su uno stack che stiamo lasciando.

---

## 2. CrewAI Chat UI — zinyando/crewai_chat_ui

**Cos'è davvero.** Un pacchetto Python che scopre automaticamente le crew nella cartella
corrente e le espone dietro una chat web. Si installa, si lancia, si chatta con la crew.
Ambizione volutamente piccola.

**Stack.** Backend FastAPI + uvicorn (da `pyproject.toml`), frontend in HTML/CSS/JS
serviti dal pacchetto. Non c'è un framework frontend moderno: niente React, niente build
step. Dipende da `crewai>=0.134.0`.

**Licenza verificata.** ⚠️ **Nessun file `LICENSE` nel repository.** Verificato due volte:
il listato della root contiene solo `.gitignore`, `README.md`, `__init__.py`, `images`,
`pyproject.toml`, `src`; e una ricerca ricorsiva sull'intero albero del branch di default
(`main`) non trova alcun file con «licen[cs]e» nel nome. Il `pyproject.toml` **non ha un
campo `license`**. L'unica affermazione è nel README, sotto forma di due righe:

> `## License`
> `MIT`

Su questa situazione vale la sezione finale: una dichiarazione nel README è
*probabilmente* una concessione valida, ma è priva della nota di copyright e del testo
completo, e non è la stessa cosa di un `LICENSE`. Per un prodotto venduto è un rischio
che non ha senso correre per così poco valore.

**Maturità.** 31 stelle, 4 fork, **ultimo commit 11 luglio 2025** — oltre un anno di
inattività alla data di questa ricognizione. Il README indica ancora la pubblicazione su
PyPI come «when published». Progetto **fermo**.

**Vicinanza al nostro bisogno: molto bassa.** Chat lineare utente↔crew. Nessun HITL,
nessuna visualizzazione agente-agente, nessuna relazione `to`. Ha thread multipli e
indicatori di digitazione, che è quanto.

**Cosa cannibalizzare.** Nulla di sostanziale. L'unico spunto è concettuale e lo
annotiamo per onestà: l'**auto-discovery delle crew** dalla cartella di lavoro è una
comodità di sviluppo carina, ma è ortogonale a un prodotto venduto dove il roster è
definito dal prodotto, non scoperto dal filesystem.

> **Verdetto: ignorare** — fermo da oltre un anno, licenza senza file, e risolve una
> frazione del problema con uno stack che non ci serve.

---

## 3. Open Multi-Agent Canvas — CopilotKit/open-multi-agent-canvas

**Cos'è davvero.** Il progetto della lista **nominalmente** più vicino a noi: si presenta
come «the open-source multi-agent chat interface that lets you manage multiple agents in
one dynamic conversation». Nella pratica è una **canvas** con una chat CopilotKit a
fianco, dove agenti diversi (un Travel Agent, un AI Researcher, un MCP Agent generico)
rendono ciascuno il proprio riquadro di stato dentro l'area di lavoro, mentre l'utente
parla con loro da un'unica composer.

**Stack.** Next.js + TypeScript (`frontend/`), LangGraph + Python con Poetry (`agent/`),
CopilotKit come strato di collegamento, MCP per l'aggancio di server esterni (menziona
`mcp.composio.dev` e `mcp.run` come server pubblici usabili).

**Licenza verificata.** ⚠️ **Nessun file `LICENSE` nel repository**, ed è un caso più
insidioso del precedente perché il README **afferma il contrario**. Testo letterale del
README:

> «Distributed under the MIT License. See LICENSE for more info.»

Il file a cui quella riga rimanda **non esiste**. Verificato con una ricerca ricorsiva
sull'intero albero del branch di default (`main`): zero occorrenze di «licen[cs]e» nei
percorsi. Il listato della root contiene solo `.gitignore`, `README.md`, `agent`,
`frontend`, `renovate.json`.

C'è una sfumatura che peggiora il quadro invece di migliorarlo: `agent/pyproject.toml`
dichiara `license = "MIT"`, ma quel campo copre **solo il sotto-pacchetto Python**
dell'agente. Il `frontend/package.json` — cioè **la parte che ci interesserebbe**, la UI —
**non ha alcun campo `license`**. La parte di valore per noi è quindi la meno coperta.

Va detto per correttezza: l'organizzazione proprietaria (CopilotKit) pubblica il repo
principale sotto MIT, e l'intenzione è palesemente MIT. Ma «l'intenzione è palese» non è
un argomento che si porta in due diligence su un prodotto venduto.

**Maturità.** 517 stelle, 77 fork, ultimo commit 2026-06-05. Il README rimanda issue e PR
al monorepo principale di CopilotKit: il progetto è stato **assorbito**, questo repo è
ormai una vetrina. Vivo come dimostrazione, non come base su cui costruire.

**Vicinanza al nostro bisogno: media, e più bassa di quanto il nome prometta.** «Multiple
agents in one dynamic conversation» descrive il *routing* verso agenti diversi, non
agenti che **si parlano fra loro**. Il thread resta utente↔agente-attivo. Non c'è
relazione `to`, non c'è HITL documentato in questo repo.

**Cosa cannibalizzare** (pattern osservati, nessun codice — e con la cautela della
licenza di cui sopra):

- **La canvas come terza colonna vivente.** È la conferma esterna più forte della nostra
  scelta di layout: la chat non deve contenere gli artefatti, deve accompagnarli. La
  nostra colonna «proposte» è esattamente questo, e vederla funzionare altrove la
  convalida.
- **Un riquadro di stato per agente**, che l'agente stesso popola e aggiorna mentre
  lavora, invece di un unico spinner globale. Traduce bene in «chi sta scrivendo cosa,
  adesso» nella nostra stanza.
- **L'aggancio MCP come porta laterale**: server esterni configurabili dall'utente senza
  toccare il codice. Da tenere a mente per la ricerca, non per la v1.

> **Verdetto: cannibalizzare pattern** (canvas + riquadri di stato per agente) —
> **ma non copiare codice** finché la licenza resta senza file. Il valore è nell'idea di
> layout, che è gratis.

---

## 4. Agent Chat UI — langchain-ai/agent-chat-ui

**È la scoperta più utile della lista.** Non per quello che è nel complesso, ma per una
sua parte specifica.

**Cos'è davvero.** Una web app che parla con un qualsiasi agente LangGraph (Python o
TypeScript) via URL di deployment + ID dell'assistente. Chat, streaming, cronologia
thread, artefatti in pannello laterale, e — la parte che conta — un **Agent Inbox** per
le interruzioni human-in-the-loop.

**Stack.** Next.js + TypeScript + **Tailwind + shadcn/ui** (presente `components.json`),
pnpm. **È esattamente il nostro stack.** Il codice è quindi leggibile e trasferibile
senza traduzione concettuale, che è una differenza enorme rispetto ai progetti Streamlit.

**Licenza verificata.** **MIT**, file `LICENSE` presente, intestato «Copyright (c) 2025
Brace Sproul». Testo MIT standard, nessuna clausola aggiunta. **Pulita**: si può leggere,
adattare e ridistribuire in un prodotto commerciale mantenendo la nota di copyright.

**Maturità.** 3.032 stelle, 666 fork, ultimo commit 2026-08-03. Manutenuto **da
LangChain** (organizzazione, non individuo). Il più solido della lista dopo CopilotKit.

**Vicinanza al nostro bisogno: alta sul HITL, nulla sul multi-agente.** Il README non
menziona HITL, ma il README mente per omissione: nel sorgente c'è un apparato HITL
completo. I percorsi rilevanti:

```
src/components/thread/agent-inbox/index.tsx
src/components/thread/agent-inbox/types.ts
src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx
src/components/thread/agent-inbox/components/thread-actions-view.tsx
src/components/thread/agent-inbox/components/inbox-item-input.tsx
src/components/thread/agent-inbox/components/state-view.tsx
src/components/thread/agent-inbox/components/tool-call-table.tsx
src/components/thread/messages/generic-interrupt.tsx
src/components/thread/artifact.tsx
```

**Il vocabolario HITL**, letto da `agent-inbox/types.ts`, è la cosa più preziosa
dell'intera ricognizione. In forma di contratto:

- `DecisionType` = `"approve" | "edit" | "reject"` — tre decisioni, non due. La terza via
  («approvo ma modificando») è quella che nella pratica serve sempre e che si tende a
  dimenticare in fase di design.
- `ActionRequest` = `{ name, args, description? }` — l'azione che l'agente *propone*,
  descritta in modo leggibile.
- `ReviewConfig` = `{ action_name, allowed_decisions[], args_schema? }` — **per ogni
  azione si dichiara quali decisioni sono ammesse**. Il gate non è uniforme: una ricerca
  può essere approvabile-o-modificabile ma non rifiutabile, un'altra sì. E `args_schema`
  permette di generare il form di modifica invece di scriverlo a mano.
- `HITLRequest` = `{ action_requests[], review_configs[] }` — **più azioni in un solo
  gate**, approvabili in blocco o singolarmente.
- `Decision` come unione discriminata: `{type:"approve"}` | `{type:"reject", message?}` |
  `{type:"edit", edited_action}` — il rifiuto porta con sé una motivazione, la modifica
  porta con sé l'azione corretta.

Sui **limiti**, per onestà: è **legato a LangGraph**, non a CrewAI. `types.ts` importa da
`@langchain/langgraph-sdk` e da `@langchain/core/messages`. Non è adottabile
così com'è. Ed è, di nuovo, una chat **utente↔agente**: nessuna nozione di agenti che si
parlano, nessuna relazione `to`.

**Cosa cannibalizzare** (MIT, quindi **anche il codice**, mantenendo la nota di copyright):

- **Il contratto di decisione HITL per intero.** È la spina dorsale del nostro gate di
  approvazione ricerca. Da riscrivere sui nostri tipi (via LangGraph), ma la *forma* —
  `allowed_decisions` per azione, `args_schema` per il form, decisioni come unione
  discriminata — è già progettata bene e ci risparmia un giro di errori.
- **La metafora «inbox» per le approvazioni pendenti.** Il gate non è un modale che
  blocca la stanza: è una coda di cose che ti aspettano, che puoi evadere quando vuoi.
  Per una writers' room dove il Director può accumulare più richieste è la metafora
  giusta.
- **`tool-call-table.tsx`**: rendere gli argomenti di una chiamata come **tabella
  ispezionabile** invece che come blob JSON. Applicabile direttamente alle nostre query
  di ricerca da approvare.
- **`state-view.tsx`**: mostrare lo stato dell'agente prima e dopo, così il Director
  approva sapendo *cosa cambia*.
- **`artifact.tsx` + pannello laterale**: ancora una conferma indipendente della terza
  colonna.

> **Verdetto: cannibalizzare a fondo** — stesso stack, licenza MIT pulita, e possiede il
> pezzo di design che ci manca (il contratto HITL). È la fonte migliore della lista.

---

## 5. CopilotKit + CrewAI (integrazione ufficiale, protocollo AG-UI)

Qui vanno separate due cose che la lista tiene insieme, perché hanno profili di rischio
diversi: **CopilotKit** (il framework frontend, prodotto di un'azienda) e **AG-UI** (il
protocollo).

### 5a. AG-UI — il protocollo

**Cos'è davvero.** Un protocollo a eventi, leggero, per lo streaming fra backend agentico
e frontend. Nato dalla collaborazione di CopilotKit con LangGraph e CrewAI, oggi con SDK
in TypeScript, Python, Go, Java, Kotlin, .NET, Ruby, Dart.

**Licenza verificata.** **MIT**, file `LICENSE` presente nel repo `ag-ui-protocol/ag-ui`,
intestato «Copyright (c) 2025». Testo MIT standard.

⚠️ **Un'annotazione precisa, verificata su npm**: i pacchetti pubblicati `@ag-ui/core` e
`@ag-ui/client` (versione 0.0.57 alla data odierna) **non hanno il campo `license` nel
loro `package.json`**. La licenza del repo (MIT) governa comunque il codice, ma i
metadati del pacchetto la omettono: se in futuro girerete uno scanner di licenze
automatico in CI, questi due pacchetti risulteranno «UNKNOWN» e andranno annotati a mano.
Non è un problema legale, è un problema di processo — ma è meglio saperlo prima.

**Maturità.** 15.116 stelle, 1.374 fork, ultimo commit 2026-08-03. Molto vivo. Ma
attenzione al numero di versione: **0.0.57 è pre-1.0**, e nel sorgente ci sono già eventi
marcati `@deprecated ... Will be removed in 1.0.0` (tutta la famiglia `THINKING_*`,
sostituita da `REASONING_*`). Il protocollo **si sta ancora muovendo**.

**Vicinanza al nostro bisogno: alta come riferimento, nulla come adozione.** Non ci dà
una UI. Ci dà un **vocabolario di eventi** già pensato per il problema che il nostro
contratto WebSocket sta risolvendo. Ecco l'enumerazione reale, letta dal sorgente
(`sdks/typescript/packages/core/src/events.ts`):

| Famiglia | Eventi |
|---|---|
| Ciclo di vita run | `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR` |
| Passi | `STEP_STARTED`, `STEP_FINISHED` |
| Testo | `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `TEXT_MESSAGE_CHUNK` |
| Tool | `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, `TOOL_CALL_CHUNK`, `TOOL_CALL_RESULT` |
| Ragionamento | `REASONING_START`, `REASONING_MESSAGE_START/CONTENT/END/CHUNK`, `REASONING_END`, `REASONING_ENCRYPTED_VALUE` |
| Stato | `STATE_SNAPSHOT`, `STATE_DELTA`, `MESSAGES_SNAPSHOT` |
| Attività | `ACTIVITY_SNAPSHOT`, `ACTIVITY_DELTA` |
| Estensione | `RAW`, `CUSTOM` |

Il modulo importa inoltre un `InterruptSchema` dai propri tipi, e il repo contiene una
feature `interrupt` dimostrativa con test end-to-end **specifici per CrewAI**
(`apps/dojo/e2e/tests/crewAITests/interruptPage.spec.ts`,
`apps/dojo/e2e/interrupt-crewai-fixtures.ts`): l'HITL su CrewAI è supportato ed è
testato, non solo dichiarato.

**Cosa cannibalizzare** — e qui sta il valore vero:

- **Le tre distinzioni strutturali** che il nostro contratto farebbe bene ad avere se
  già non le ha: (a) `START`/`CONTENT`/`END` separati da `CHUNK`, cioè il ciclo di vita
  distinto dallo streaming incrementale; (b) `SNAPSHOT` **e** `DELTA` per lo stato, così
  un client che si riconnette a metà sessione può risincronizzarsi senza rigiocare tutto
  — problema che in una writers' room lunga si presenta di sicuro; (c) `REASONING_*`
  come **famiglia separata** dal testo, che è esattamente ciò che serve per mostrare «sta
  pensando» senza mescolarlo alle battute della stanza.
- **`ACTIVITY_SNAPSHOT` / `ACTIVITY_DELTA`**: un canale di «cosa sta succedendo» distinto
  dai messaggi. La nostra riga di stato («il Director sta valutando…») è questo.
- **`RAW` e `CUSTOM` come valvole di sfogo**: due eventi di estensione previsti *dal
  principio*, per non dover rompere il contratto al primo caso non previsto. Se il nostro
  contratto non li ha, aggiungerli adesso costa nulla e più avanti salva.
- **La lezione sulla deprecazione**: `THINKING_*` → `REASONING_*` mostra che anche un
  protocollo curato sbaglia i nomi al primo giro. Vale la pena versionare il nostro
  contratto fin da subito.

### 5b. CopilotKit — il framework

**Cos'è davvero.** Uno strato React per costruire UI agentiche: componenti di chat,
generative UI, azioni frontend richiamabili dall'agente. Le integrazioni CrewAI sono
**ufficiali e presenti nel monorepo**: `examples/integrations/crewai-crews` e
`examples/integrations/crewai-flows`.

Sul HITL, il meccanismo documentato è `renderAndWaitForResponse`: la render function di
un'azione può **restituire un valore in modo asincrono**, cioè l'agente disegna una scelta
dentro la chat e resta in attesa che l'utente prema un bottone. È un pattern elegante e
molto vicino al nostro gate.

**Licenza verificata — e qui serve precisione, perché il quadro è a due livelli.**

**Livello 1 — il core, MIT.** Il file `LICENSE` alla root di `CopilotKit/CopilotKit` è
«The MIT License», intestato «Copyright (c) Atai Barkai». E, cosa che conta di più
perché è ciò che si installa davvero, i **pacchetti pubblicati su npm** riportano tutti
`license: MIT` (verificato su `@copilotkit/react-core`, `@copilotkit/react-ui` e
`@copilotkit/runtime`, versione 1.65.0). Per l'uso normale — installo il pacchetto,
costruisco la mia UI, vendo il prodotto — **è MIT e si può**.

**Livello 2 — esiste una parte a pagamento, ed è bene sapere dove.** Nel repo ci sono
script `mint-dev-license.mjs`. Non sono un dettaglio: rivelano un modello di licensing
commerciale su una parte dello stack. Dal commento in testa allo script, testualmente:

> «Self-hosted Intelligence gates memory behind a signed offline license.»

e ancora:

> «The signer lives in the private Intelligence source (it depends on the
> `@cpki/license-catalog` workspace package)»

In chiaro: esiste uno stack **«Intelligence»** il cui sorgente è **privato**, in cui la
funzionalità `memory` è **a pagamento** e sbloccata da un `COPILOTKIT_LICENSE_TOKEN`
firmato. Nella modalità gestita (o con le immagini pubbliche ufficiali) la chiave
pubblica master di CopilotKit è immutabile e il token **deve essere emesso da CopilotKit**.
Lo script serve solo a fabbricare una licenza di sviluppo su build locali non «baked».

**Cosa significa per noi, concretamente**: usare i componenti React MIT è libero; appoggiarsi
a *Intelligence* / memory o alla piattaforma gestita significa **entrare in un rapporto
commerciale con un fornitore**, con un token che può essere revocato e un prezzo che può
cambiare. Per un prodotto che vendiamo, è una dipendenza da mettere a bilancio
consapevolmente, non da scoprire in produzione.

**Maturità.** CopilotKit: 36.426 stelle, 4.499 fork, ultimo commit 2026-08-03. Il
monorepo è ampio (`packages/`: `react-core`, `react-ui`, `runtime`, `angular`, `vue`,
`react-native`, `voice`, `web-components`, più una famiglia `channels-*` per Slack,
Teams, Discord, WhatsApp, Telegram). È il progetto più maturo della ricognizione.

**Vicinanza al nostro bisogno: media.** Ottimo per «utente parla con un agente», con
generative UI e HITL già risolti. Ma resta un modello **a copilota**: un assistente
affiancato all'utente. La writers' room non è un copilota, è una **stanza che l'utente
guarda e in cui interviene**. Adottare CopilotKit ci farebbe combattere contro
l'astrazione invece che appoggiarci a essa.

> **Verdetto: cannibalizzare il contratto eventi di AG-UI** (allineare il nostro
> WebSocket a un vocabolario di fatto standard, gratis e MIT), **cannibalizzare il pattern
> `renderAndWaitForResponse`** per il gate, **non adottare CopilotKit come framework** —
> il modello copilota non è il nostro, e il livello *Intelligence* introduce una
> dipendenza commerciale da un fornitore in un prodotto che vendiamo.

---

## 6. Demo Streamlit varie

**tonykipkemboi/crewai-streamlit-demo** — **MIT** (file `LICENSE` presente e verificato).
73 stelle, 42 fork, ultimo commit **16 febbraio 2025**: fermo da oltre un anno. È
esattamente ciò che dichiara, una demo di come far uscire l'output dei task CrewAI su
Streamlit. Nessun HITL, nessuna relazione fra agenti.

**camel-ai/camel** — **Apache-2.0** (verificato). 17.534 stelle, ultimo commit
2026-07-31, molto vivo. Ma va chiarito un equivoco della lista: **non è una UI**, è un
framework multi-agente. Il suo interesse per noi è teorico (il paradigma di
role-playing fra agenti è affine alla nostra stanza), non pratico.

**crewAIInc/crewAI-examples** — ⚠️ **nessuna licenza rilevata** (campo licenza vuoto via
API). 6.128 stelle, ultimo commit 2026-04-20. Repo ufficiale di esempi CrewAI, ma senza
file di licenza: da leggere, non da copiare.

**Cosa cannibalizzare.** Nulla. Sono dimostrazioni didattiche; il nostro problema è
un altro ordine di grandezza.

> **Verdetto: ignorare** tutte e tre — demo didattiche, in gran parte ferme, e una senza
> licenza.

---

## 7. Oltre la lista — 5 scoperte degne di nota

Ricerche svolte su GitHub con query del tipo «multi-agent chat UI», «agent canvas»,
«human in the loop agent UI», «crewai frontend», «langgraph chat ui», «AG-UI protocol»,
più i topic `agent-chat` e `human-in-the-loop`. Le cinque che meritano di essere
riportate, con gli stessi criteri delle precedenti.

### 7.1 langchain-ai/agent-inbox — **la migliore scoperta per il nostro gate**

- **Licenza verificata**: **MIT**. **1.042 stelle**, ultimo commit **2026-08-03**.
- **Cos'è**: una UI **dedicata** alle interruzioni HITL, in stile casella di posta. Gli
  agenti propongono azioni, l'operatore le trova in inbox e le approva, modifica o
  rifiuta. È il pattern dell'`agent-inbox` di Agent Chat UI (§4) **estratto in prodotto
  autonomo e portato più a fondo**.
- **Perché conta**: è la dimostrazione che il HITL merita una superficie propria e non un
  modale. Per noi, che abbiamo un gate di approvazione ricerca come **funzione di
  prodotto** e non come dettaglio tecnico, è il riferimento di design più diretto che
  esista, ed è MIT.
- **Verdetto: cannibalizzare** — insieme a §4, è la fonte primaria per il gate.

### 7.2 assistant-ui/assistant-ui — **la migliore scoperta per la timeline**

- **Licenza verificata**: **MIT**. **11.387 stelle**, ultimo commit **2026-08-03**.
- **Cos'è**: una libreria React/TypeScript di **primitive** per chat AI, in stile Radix
  (componenti headless e componibili, non un'app da forkare). Le primitive pubblicate:

  ```
  thread · threadList · threadListItem · message · messagePart · composer
  branchPicker · chainOfThought · reasoning · actionBar · selectionToolbar
  attachment · suggestion · queueItem · error · assistantModal
  ```

- **Perché conta**: tre di queste primitive risolvono problemi che **abbiamo davvero**.
  `messagePart` — un messaggio non è una stringa, è una sequenza di parti eterogenee
  (testo, tool call, ragionamento): è il modello dati corretto per una battuta della
  nostra stanza. `chainOfThought` e `reasoning` — superficie dedicata al pensiero,
  separata dal detto, che è la distinzione che AG-UI fa negli eventi e che qui è resa
  in componenti. `branchPicker` — navigare fra versioni alternative di una risposta,
  che è **esattamente** la forma della nostra colonna «proposte» quando un agente
  propone più varianti di copy.
- **Verdetto: cannibalizzare** — è MIT, è React+TS, ed è l'unica fonte della ricognizione
  che ci dà un modello dati per la **timeline**.

### 7.3 agentscope-ai/AgentTeams (alias `hiclaw`) — **il più vicino alla nostra tesi**

- **Licenza verificata**: **Apache-2.0**. **5.286 stelle**, ultimo commit **2026-08-03**.
  Versione v1.2.0 (luglio 2026).
- **Cos'è**: un «Collaborative Multi-Agent OS» con architettura Manager–Workers in cui
  **tutta la collaborazione avviene dentro stanze Matrix** condivise fra umano, Manager e
  Worker. Client web = Element. Stack pesante e infrastrutturale (gateway AI, server
  Matrix, MinIO, controller Kubernetes con CRD).
- **Perché conta**: è l'unico progetto trovato che **condivide la nostra tesi di
  prodotto**, ed è esplicito al riguardo. Dal README, testualmente:

  > «No hidden agent-to-agent calls. Everything is visible and intervenable.»

  e sul HITL:

  > «Every Matrix Room includes you, the Manager, and relevant Workers»

  con intervento a runtime nella forma `@bob wait, change the password rule to minimum
  8 chars`. Cioè: **gli agenti si parlano in chiaro davanti all'umano, e l'umano può
  interrompere rivolgendosi a uno specifico agente**. È la nostra stanza, costruita su
  Matrix.
- **Cosa cannibalizzare**: (a) il **principio dichiarato** — nessuna chiamata
  agente-agente nascosta — come regola di design del nostro contratto eventi, non solo
  come feature; (b) **`m.mentions` come modello per la relazione `to`**: Matrix ha già
  risolto «chi parla a chi» in una stanza a molte voci, e la sua soluzione (menzioni
  esplicite come dato strutturato, non come testo) è quella che ci serve; (c)
  l'intervento umano come **messaggio nella stanza indirizzato a un agente**, non come
  form fuori banda — più naturale e molto più semplice da modellare.
- **Verdetto: cannibalizzare pattern** — non adottare (Matrix + Kubernetes è un ordine di
  grandezza fuori scala per noi), ma è la conferma più forte che la direzione è giusta e
  la migliore fonte di idee sulla relazione `to`.

### 7.4 saigontechnology/AgentCrew

- **Licenza verificata**: **Apache-2.0**. **212 stelle**, ultimo commit **2026-08-03**.
- **Cos'è**: applicazione di chat con sistema multi-agente, multi-modello e MCP. Più
  vicina a un client desktop/chat generalista che a una writers' room.
- **Perché conta**: poco, ma è attiva e con licenza pulita. Segnalata per completezza
  come alternativa Apache-2.0 nel caso servisse un riferimento di implementazione
  multi-agente + MCP.
- **Verdetto: ignorare** — nulla di specifico che non ci diano meglio §7.1 e §7.2.

### 7.5 sekera-radim/impri

- **Licenza verificata**: **MIT**. **1 stella**, ultimo commit 2026-08-03.
- **Cos'è**: inbox di approvazione HITL — l'agente propone un'azione, un umano approva o
  rifiuta, poi l'azione parte. API REST + server MCP + inbox web in Vue 3 + Vuetify.
- **Perché conta**: conferma indipendente che «approval inbox» sta diventando **il**
  pattern per il HITL. Ma con 1 stella è un progetto personale: da guardare come schizzo
  di architettura (separazione fra *proposta*, *decisione* ed *esecuzione* come tre
  momenti distinti, con watcher), non come dipendenza.
- **Verdetto: ignorare** come codice, **annotare** la tripartizione proposta/decisione/
  esecuzione.

### ⚠️ Due trappole di licenza incontrate strada facendo

Le riporto perché sono progetti popolari che verrebbe naturale valutare, e in entrambi i
casi **il dato che GitHub mostra in cima al repo è fuorviante**.

**lobehub/lobe-chat** (81.180 stelle) — GitHub riporta `NOASSERTION`. Il file è una
**«LobeHub Community License»**, basata su Apache-2.0 **con condizioni aggiuntive**.
Testo letterale:

> «b. a commercial license must be obtained from the producer if you want to develop and
> distribute a derivative work based on LobeChat.»

L'uso commerciale «as-is» come servizio è permesso, ma **sviluppare e distribuire
un'opera derivata richiede una licenza commerciale dal produttore**. Per noi — che
faremmo per definizione un'opera derivata — è **veleno**. Da non toccare.

**microsoft/autogen** (60.193 stelle) — GitHub riporta **CC-BY-4.0**, che per del codice
sarebbe un allarme rosso. In realtà il repo ha **due file**: `LICENSE` è
Creative Commons Attribution 4.0 (copre la documentazione) e **`LICENSE-CODE` è MIT**
(«Copyright (c) Microsoft Corporation») e copre il codice. Il rilevamento automatico di
GitHub legge solo il primo. **Il codice è MIT e sarebbe utilizzabile** — la segnalo
soprattutto come esempio del perché la regola «leggere il file, non il badge» non è
pedanteria: qui il badge sbaglia in senso pessimistico, altrove sbaglia in senso
ottimistico.

---

## 8. Rischio licenze per un prodotto commerciale

Sezione operativa. Il prodotto **si vende**: quello che segue non è teoria, è la lista
delle cose che possono far male.

### 8.1 Le permissive — via libera, con un adempimento

**MIT** — si può usare, modificare, incorporare in software proprietario, vendere, senza
pubblicare il proprio sorgente. **L'unico obbligo**: includere la nota di copyright e il
testo della licenza nelle distribuzioni. Per una web app venduta come servizio, in
pratica: una pagina o un file `THIRD-PARTY-NOTICES` raggiungibile. È l'adempimento che
tutti dimenticano e che costa dieci minuti.

**Apache-2.0** — stesse libertà, più due cose che MIT non ha:
- **concessione esplicita di brevetto** da parte dei contributori (per un prodotto
  commerciale è una *protezione in più*, non un vincolo — Apache-2.0 è, sotto questo
  profilo, **più sicura** di MIT);
- **clausola di ritorsione**: se facciamo causa a qualcuno per brevetto sostenendo che
  quel software lo viola, perdiamo la licenza di brevetto. Irrilevante per noi.
- obblighi pratici: conservare il file `NOTICE` se presente, e **segnalare le modifiche**
  ai file modificati.

**In sintesi**: MIT e Apache-2.0 vanno benissimo. Serve solo tenere l'elenco delle
attribuzioni e non perdere i `NOTICE`.

### 8.2 Le copyleft — da evitare, l'AGPL in modo assoluto

**GPL (v2/v3)** — copyleft forte. Se **distribuiamo** un'opera derivata, va distribuita
sotto GPL, sorgente compreso. Storicamente il SaaS aggirava il problema («non distribuisco,
eseguo su un server mio»), ma è un equilibrio fragile su cui non si costruisce un
prodotto: basta un componente desktop, un container consegnato al cliente o un'installazione
on-premise e la distribuzione c'è.

**AGPL-3.0 — veleno puro per un SaaS proprietario.** La differenza sta nella **sezione 13**,
che chiude proprio quella scappatoia: se gli utenti **interagiscono con il software
attraverso una rete**, va offerto loro il **sorgente completo corrispondente** dell'opera
derivata. Una web app venduta è **esattamente** lo scenario che l'AGPL è stata scritta per
catturare. Incorporare codice AGPL nella nostra app significa **essere obbligati a
pubblicare il nostro sorgente ai clienti**. Regola secca: **zero AGPL nel prodotto**, e va
verificato **in modo ricorsivo** — anche una dipendenza transitiva contagia.

### 8.3 Le non-libere travestite — la categoria più insidiosa

Queste sono pericolose perché **si presentano come open source** e spesso mostrano
«MIT» o «Apache-2.0» nel nome.

**Commons Clause** — non è una licenza, è un *rider* che si appiccica a una licenza
permissiva e ne rimuove il diritto di **vendere**. La definizione di «vendere» include
esplicitamente la fornitura di un servizio a pagamento le cui funzionalità derivano dal
software. Un componente «MIT + Commons Clause» **non è utilizzabile in un prodotto
venduto**. È già stato incontrato in questo progetto (cfr. ricognizione B, il caso
shadcn/studio): non è un rischio teorico.

**CC-BY-NC (e ogni variante NonCommercial)** — vieta l'uso commerciale. Fine. Inutilizzabile.
E va aggiunto che le licenze Creative Commons **non sono pensate per il software** (lo dice
Creative Commons stessa): se un progetto di codice è sotto CC, c'è comunque un problema
di adeguatezza, a prescindere dalla clausola NC.

**Le «Community License» aziendali** — Apache-2.0 (o MIT) **più condizioni aggiuntive**,
tipicamente: niente rimozione del branding, niente multi-tenancy, e — la più letale —
**opera derivata solo con licenza commerciale**. `lobehub/lobe-chat` (§7) è il caso
concreto trovato oggi. GitHub le etichetta `NOASSERTION`: **`NOASSERTION` va sempre
trattato come «rosso finché non dimostrato verde»**, mai come «probabilmente ok».

**Nessuna licenza** — il caso di `zinyando/crewai_chat_ui`, `CopilotKit/open-multi-agent-canvas`
e `crewAIInc/crewAI-examples`. Va detto con chiarezza: **in assenza di una concessione,
il diritto d'autore si applica per intero**. Nessuna licenza ≠ pubblico dominio: significa
**tutti i diritti riservati**, cioè nessun diritto di copiare, modificare o
ridistribuire. Il fatto che il codice sia pubblicamente leggibile su GitHub non concede
nulla oltre a ciò che i Termini di GitHub prevedono (fork e visualizzazione sulla
piattaforma).

Sui due casi in cui **il README dichiara MIT ma manca il file**: una dichiarazione nel
README è, con ogni probabilità, una concessione valida — è una manifestazione scritta
della volontà del titolare. Ma è **debole**: priva della nota di copyright, del testo
completo e dell'individuazione certa del titolare. La posizione ragionevole per un
prodotto venduto:

- **si può leggere e studiare** (nessuno vieta di imparare da un'architettura);
- **non si copia codice** finché la situazione non è sanata;
- se una porzione servisse davvero, **si apre una issue chiedendo di aggiungere il file
  `LICENSE`** — costa un messaggio e nel caso di `open-multi-agent-canvas` (dove il README
  già rimanda a un file inesistente) è quasi certamente una svista che il manutentore
  correggerà volentieri. **La risposta va conservata.**

### 8.4 CopilotKit e AG-UI — risposta puntuale

Il committente ha chiesto esattamente questo, e la risposta è a due livelli.

**AG-UI** — **MIT**, verificato dal file `LICENSE` nel repo `ag-ui-protocol/ag-ui`. Un
protocollo, per di più, è ancora meno problematico di una libreria: **implementare una
specifica non è un'opera derivata del suo SDK**. Se ci limitiamo ad **allineare il nostro
contratto WebSocket ai loro nomi di evento** — che è ciò che raccomando — non stiamo
usando il loro codice affatto, e la questione licenza non si pone nemmeno. Se invece
importassimo `@ag-ui/client`, sarebbe MIT e andrebbe bene, con l'annotazione operativa
del §5a: i `package.json` pubblicati **omettono il campo `license`**, quindi uno scanner
automatico li segnerà come sconosciuti e andranno documentati a mano.

**CopilotKit** — **MIT** per tutto ciò che si installa normalmente: file `LICENSE` alla
root («The MIT License», «Copyright (c) Atai Barkai») e campo `license: MIT` sui pacchetti
npm `@copilotkit/react-core`, `@copilotkit/react-ui`, `@copilotkit/runtime` (v1.65.0,
verificati). **Costruire e vendere un prodotto sopra questi pacchetti è consentito**,
mantenendo l'attribuzione.

**Ma** — ed è la parte da non perdere — CopilotKit è un'**azienda con un modello
commerciale**, e una parte dello stack **non** è MIT: lo stack **«Intelligence»**, il cui
sorgente è **privato**, con la funzionalità `memory` sbloccata da un
`COPILOTKIT_LICENSE_TOKEN` **firmato** ed emesso da CopilotKit (§5b, citazioni testuali
dallo script `mint-dev-license.mjs`). Implicazioni pratiche per un prodotto venduto:

1. **Il confine è netto e va rispettato consapevolmente**: SDK React = MIT, libero.
   *Intelligence* / memory / piattaforma gestita = **contratto commerciale con un
   fornitore terzo**.
2. **Un token può essere revocato e un prezzo può cambiare.** Se una funzione che
   vendiamo al cliente dipende da un token altrui, quella funzione non è nostra. Va
   messo a bilancio, o evitato.
3. **Rischio di scivolamento**: si comincia con i componenti MIT e ci si ritrova con una
   dipendenza gestita senza una decisione esplicita. Se si usa CopilotKit, il confine va
   scritto in `DECISIONS.md` **prima**, non dopo.

Vale anche la considerazione strategica, al di là della licenza: costruire il nostro
prodotto di punta sopra il framework di un'azienda che vende **il proprio** prodotto
nello stesso spazio è una scelta da fare a occhi aperti.

### 8.5 Checklist operativa prima del rilascio

1. **Inventario delle dipendenze** con licenza risolta, transitive incluse.
2. **Zero AGPL**, verificato ricorsivamente. Nessuna GPL se è previsto un artefatto
   consegnato al cliente.
3. **Nessun `NOASSERTION`, nessuna Commons Clause, nessuna `-NC`** non risolta a mano.
4. **File `THIRD-PARTY-NOTICES`** con le note di copyright MIT/BSD e i `NOTICE` Apache.
5. **Modifiche segnalate** sui file Apache-2.0 modificati.
6. Per ogni porzione presa da un repo **senza file `LICENSE`**: o non si prende, o si
   ottiene una concessione scritta e la si archivia.
7. Se entra AG-UI o CopilotKit: **annotare a mano** i pacchetti il cui `package.json`
   omette il campo licenza, e **scrivere in `DECISIONS.md` il confine** fra ciò che è MIT
   e ciò che è a pagamento.

> **Nota di merito e limite.** Le licenze qui riportate sono state lette dai file dei
> repository alla data del 3 agosto 2026. Le licenze **cambiano** (il caso LobeChat, «From
> 1.0, LobeChat is licensed under…», ne è la prova). Prima di un rilascio commerciale la
> verifica va **rifatta** sulle versioni effettivamente incorporate. Questo documento è una
> due diligence tecnica, **non un parere legale**.

---

## 9. Conclusione — i 3 pattern più preziosi da cannibalizzare

Se di tutta questa ricognizione dovessero sopravvivere tre cose, sono queste.

**1. Il contratto di decisione HITL a tre vie, con permessi per azione.**
Da `langchain-ai/agent-chat-ui` (MIT) e `langchain-ai/agent-inbox` (MIT). Non
approva/rifiuta, ma **approva / modifica / rifiuta**, dove ogni azione dichiara le
decisioni ammesse (`allowed_decisions`) e porta uno schema degli argomenti (`args_schema`)
da cui generare il form di modifica. Il rifiuto trasporta una motivazione, la modifica
trasporta l'azione corretta. Più azioni possono stare in un unico gate. È il progetto
già fatto del nostro gate di approvazione ricerca, ed è la cosa che ci risparmia più
errori.

**2. La separazione fra ciclo di vita, contenuto, ragionamento e stato negli eventi.**
Da AG-UI (MIT). Quattro distinzioni da portare nel nostro contratto WebSocket:
`START`/`CONTENT`/`END` distinti dai `CHUNK` di streaming; `SNAPSHOT` **accanto** a
`DELTA` sullo stato, perché un client che si riconnette a metà sessione deve poter
risincronizzarsi senza rigiocare la storia; `REASONING_*` come famiglia **separata** dal
testo, per mostrare il pensiero senza sporcare le battute; un canale `ACTIVITY_*`
distinto dai messaggi per la riga di stato. Più due valvole di sfogo (`RAW`, `CUSTOM`)
previste dal principio. Allinearsi a un vocabolario di fatto standard costa poco adesso e
rende leggibile il nostro contratto a chiunque venga dopo.

**3. La visibilità agente-agente come principio, e `m.mentions` come modello per il `to`.**
Da `agentscope-ai/AgentTeams` (Apache-2.0): «No hidden agent-to-agent calls. Everything
is visible and intervenable.» È la nostra tesi di prodotto, scritta da altri, e conferma
che la stanza vale la pena. Sul piano tecnico, la lezione è che **Matrix ha già risolto
«chi parla a chi» in una stanza a molte voci** modellando le menzioni come **dato
strutturato**, non come testo da riconoscere — che è precisamente la forma che deve avere
il nostro campo `to`. E l'intervento umano come **messaggio nella stanza indirizzato a un
agente** (invece che come form fuori banda) è più naturale per l'utente e più semplice da
modellare per noi.

**Menzione d'onore**, perché è il quarto e riguarda la timeline: da
`assistant-ui/assistant-ui` (MIT), il modello **`messagePart`** — un messaggio non è una
stringa, è una **sequenza di parti eterogenee** (testo, tool call, ragionamento). È il
modello dati corretto per una battuta della nostra stanza, e `branchPicker` è già la
forma della colonna «proposte» quando un agente offre più varianti.

---

## Fonti e riferimenti

Tutte le licenze indicate come «verificate» sono state lette dal file `LICENSE` del
repository via API GitHub alla data del 3 agosto 2026; le licenze npm dai metadati del
pacchetto pubblicato.

**Le sei alternative valutate**
1. [strnad/CrewAI-Studio](https://github.com/strnad/CrewAI-Studio) — GUI Streamlit per CrewAI. MIT verificata.
2. [zinyando/crewai_chat_ui](https://github.com/zinyando/crewai_chat_ui) — chat UI per crew. Nessun file LICENSE.
3. [CopilotKit/open-multi-agent-canvas](https://github.com/CopilotKit/open-multi-agent-canvas) — canvas multi-agente Next.js. Nessun file LICENSE nonostante il README.
4. [langchain-ai/agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui) — chat UI LangGraph con Agent Inbox. MIT verificata.
5. [CopilotKit/CopilotKit](https://github.com/CopilotKit/CopilotKit) — framework frontend per agenti. MIT verificata (core).
6. [ag-ui-protocol/ag-ui](https://github.com/ag-ui-protocol/ag-ui) — protocollo AG-UI. MIT verificata.
7. [tonykipkemboi/crewai-streamlit-demo](https://github.com/tonykipkemboi/crewai-streamlit-demo) — demo Streamlit. MIT verificata, ferma da 02/2025.
8. [camel-ai/camel](https://github.com/camel-ai/camel) — framework multi-agente (non una UI). Apache-2.0 verificata.
9. [crewAIInc/crewAI-examples](https://github.com/crewAIInc/crewAI-examples) — esempi ufficiali CrewAI. Nessuna licenza rilevata.

**Scoperte oltre la lista**
10. [langchain-ai/agent-inbox](https://github.com/langchain-ai/agent-inbox) — UI inbox dedicata al HITL. MIT verificata.
11. [assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui) — primitive React per chat AI. MIT verificata.
12. [agentscope-ai/AgentTeams](https://github.com/agentscope-ai/AgentTeams) (alias [hiclaw](https://github.com/agentscope-ai/hiclaw)) — multi-agent OS su stanze Matrix. Apache-2.0 verificata.
13. [saigontechnology/AgentCrew](https://github.com/saigontechnology/AgentCrew) — chat multi-agente multi-modello. Apache-2.0 verificata.
14. [sekera-radim/impri](https://github.com/sekera-radim/impri) — inbox di approvazione HITL. MIT verificata, progetto personale.

**Trappole di licenza segnalate**
15. [lobehub/lobe-chat](https://github.com/lobehub/lobe-chat) — «LobeHub Community License»: opera derivata solo con licenza commerciale.
16. [microsoft/autogen](https://github.com/microsoft/autogen) — GitHub mostra CC-BY-4.0 (doc), ma `LICENSE-CODE` è MIT (codice).

**Documentazione e contesto**
17. [Documentazione AG-UI](https://docs.ag-ui.com/) — panoramica del protocollo.
18. [AG-UI — concetti sugli eventi](https://github.com/ag-ui-protocol/ag-ui/blob/main/docs/concepts/events.mdx) — vocabolario degli eventi.
19. [CopilotKit — frontend per agenti CrewAI con AG-UI](https://www.copilotkit.ai/blog/how-to-add-a-frontend-to-any-crewai-agent-using-ag-ui-protocol) — guida ufficiale all'integrazione.
20. [CrewAI — integrazione con CopilotKit](https://blog.crewai.com/enhancing-crewai-with-copilotkit-integration/) — annuncio lato CrewAI.
21. [CopilotKit — Human-in-the-Loop](https://docs.showcase.copilotkit.ai/ag2/human-in-the-loop) — pattern `renderAndWaitForResponse`.
22. [Documentazione CopilotKit](https://docs.copilotkit.ai/) — riferimento del framework.

**Ispirazione visiva (dichiarata come tale — solo pattern, nessun asset)**
23. [AI Agent Chat UI — Smart, Context-Aware Conversations, di Raw UX](https://dribbble.com/shots/25686285-AI-Agent-Chat-UI-Smart-Context-Aware-Conversations) — esplicitamente pensata per chat multi-agente: gerarchia visiva fra voci diverse nello stesso thread.
24. [Agent: Chat Interface, di Maciek Balasinski](https://dribbble.com/shots/25687049-Agent-Chat-Interface) — piattaforma multi-canale, utile per il trattamento di stati e transizioni.
25. [Dribbble — tag `agent_chat`](https://dribbble.com/tags/agent_chat) — rassegna continua.

> Le fonti Dribbble sono **ispirazione visiva dichiarata**: si guardano per gerarchia,
> ritmo e trattamento degli stati. **Nessun asset, nessun layout e nessun codice** va
> ripreso da lì — sono opere protette dei rispettivi autori, senza licenza d'uso.
