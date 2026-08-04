# Ricognizione B — Componenti React + Tailwind

Ricognizione per la futura web app (chat multi-agente per sessioni pubblicitarie con
cliente, in sostituzione della UI Chainlit). Solo ricognizione: nessun codice scritto,
nessuna dipendenza aggiunta.

- **Data**: 3 agosto 2026
- **Fonte primaria**: [21st.dev](https://21st.dev)
- **Fonte di soli pattern** (non di codice): [component.gallery](https://component.gallery)
- **Stack di riferimento**: React 19 + Tailwind, registry in stile shadcn/ui (copia-incolla,
  non dipendenza npm)

---

## 0. Avvertenza sulle licenze — leggere prima di copiare qualsiasi cosa

Questa è la scoperta più importante della ricognizione, e cambia il modo in cui va usato
21st.dev.

**Le schede componente di 21st.dev non riportano alcun campo licenza.** Verificato
ispezionando il DOM di due schede diverse (`@shadcn/sidebar` e `@21st/plan-tool`): la
parola «license» non compare da nessuna parte nella pagina. Le schede mostrano nome,
autore, descrizione, codice, un elenco `Dependencies` e un campo `Source` — mai una licenza.

I Termini di servizio di 21st.dev **non concedono** una licenza generalizzata. Testo
letterale:

> «All code, content, and materials published on the Marketplace, including but not limited
> to components, documentation, metadata (such as names and descriptions), and all
> associated media assets (such as images, videos, and thumbnails), are the sole and
> exclusive property of their respective authors and 21st Labs Inc.»

Esiste un `LICENSE` MIT nel repo della piattaforma (`serafimcloud/21st`, «Copyright (c) 2024
21st.dev»), ma copre **il codice del sito**, non le submission della community. Diverse fonti
di terze parti affermano che «tutti i file di 21st.dev sono MIT»: è una semplificazione che
non trova riscontro né nei ToS né nelle schede. Non ci si può appoggiare.

**Regola operativa** che ne deriva, e che ho seguito in tutto il documento: la licenza va
verificata **a monte**, sul progetto indicato nel campo `Source` della scheda. 21st.dev è un
ottimo motore di scoperta, una pessima fonte di verità legale.

Un esempio concreto di perché conta — e di perché non bastava presumere: il componente
`button-approve-n-reject` viene da **shadcn/studio**, il cui `LICENSE.md` è **MIT + Commons
Clause**, non MIT puro. Clausole letterali:

> «**No Sale or Redistribution of Components:** You may not sell, sublicense, or redistribute
> the components of shadcn/studio — whether alone, in a bundle, or as a ported version —
> without modification.»
> «**Competing Products:** The Software shall not be used to create any product or service
> that directly competes with shadcn/studio.»

Su 21st.dev nulla di tutto questo è visibile. GitHub stesso classifica il repo come
`NOASSERTION / Other`.

### Legenda dei giudizi

| Giudizio | Significato |
|---|---|
| **Prendere** | Licenza verificata e permissiva, dipendenze accettabili, risolve l'esigenza così com'è |
| **Adattare** | Base valida ma va rilavorata (manca una feature, dipendenza pesante, o è solo uno scheletro) |
| **Lasciare** | Licenza non verificabile/restrittiva, oppure non pertinente |

---

## 1. La scoperta principale: "Agent Elements"

Prima di entrare nelle 6 esigenze, va segnalata la cosa più utile emersa: **21st ha una
libreria dedicata proprio a interfacce agentiche**, che da sola copre 5 esigenze su 6.

- **Nome**: Agent Elements
- **Vetrina**: <https://agent-elements.21st.dev>
- **Profilo su 21st.dev**: <https://21st.dev/@21st>
- **Upstream**: <https://github.com/21st-dev/agent-elements>
- **Licenza**: **MIT** — verificata via API GitHub (`repos/21st-dev/agent-elements/license`
  → `spdx_id: MIT`), repo pubblico, ultimo push 24/04/2026. **Non** è desumibile dalle schede
  su 21st.dev: solo l'upstream la dichiara.
- **Dipendenze tipiche per componente**: `clsx` + `tailwind-merge` (entrambi MIT), più
  `@tabler/icons-react` (MIT) dove servono icone. Estremamente leggere.
- **Nota su Base UI**: il `package.json` del sito di documentazione usa `@base-ui/react`
  (MIT) e `motion` (MIT) — **non** Radix, **non** framer-motion. Ma sono dipendenze del
  sito-vetrina, non dei singoli componenti portati su 21st.dev, che restano su clsx +
  tailwind-merge.

Componenti disponibili (dal profilo `@21st`): `agent-chat`, `user-message`, `input-bar`,
`send-button`, `markdown`, `plan-tool`, `todo-tool`, `bash-tool`, `edit-tool`, `search-tool`,
`mcp-tool`, `subagent-tool`, `generic-tool`, `thinking-tool`, `error-message`,
`file-attachment`, `attachment-button`, `model-picker`, `mode-selector`, `suggestions`,
`filter-bar`, `text-shimmer`, `spiral-loader`.

La seconda famiglia rilevante è **Vercel AI Elements** (`vercel/ai-elements`), su cui torno
sotto: licenza **Apache-2.0**, non MIT — differenza reale (obbligo di NOTICE, clausola
brevetti), da tenere presente in un repo pubblico.

---

## 2. Le 6 esigenze

### (a) Chat timeline con avatar e raggruppamento messaggi per autore

**Esito onesto: nessun componente trovato fa il raggruppamento per autore nativamente.**
Tutti i candidati rendono una lista di bolle; il raggrupamento consecutivo per autore
(collassare avatar e nome quando lo stesso autore parla più volte di fila) resta logica
applicativa da scrivere a mano. Vale per tutte e quattro le opzioni sotto.

| Componente | URL | Licenza (verificata a monte) | Dipendenze | Giudizio |
|---|---|---|---|---|
| **Message + ChatContainer** (prompt-kit) | <https://21st.dev/@ibelick/components/response-stream> · upstream <https://prompt-kit.com> | **MIT** (`ibelick/prompt-kit`, via API GitHub) | `use-stick-to-bottom` (MIT); `message.tsx` importa Avatar/Tooltip da shadcn/ui | **Prendere** — è l'unico con avatar veri già cablati (`AvatarImage`/`AvatarFallback`) e autoscroll sticky |
| **Chat Bubble / ChatMessageList** (shadcn-chat) | <https://21st.dev/@jakobhoeg/components/chat-bubble> | **MIT** (`jakobhoeg/shadcn-chat`, via API GitHub) | `lucide-react` (ISC) + shadcn/ui | **Adattare** — ha `ChatBubbleAvatar` e `ChatMessageList`, ma il manutentore dichiara nel README di **non mantenerlo più**: copiare il codice, non il CLI |
| **Conversation** (Vercel AI Elements) | <https://21st.dev/@vercel-crawled/components/conversation> · doc <https://elements.ai-sdk.dev/components/conversation> | **Apache-2.0** (testo `LICENSE`: «Copyright 2023 Vercel, Inc.») | `use-stick-to-bottom`, `streamdown` (Apache-2.0), `lucide-react`, `ai`, shadcn/ui | **Adattare** — ottimo l'autoscroll «stick to bottom» + scroll button, ma **`message.tsx` non contiene alcun avatar** (verificato con grep sul sorgente) e tira dentro l'AI SDK |
| **Agent Chat** (Agent Elements) | <https://21st.dev/@21st/components/agent-chat> | **MIT** (`21st-dev/agent-elements`) | `clsx`, `tailwind-merge` | **Adattare** — «drop-in chat shell» con lista scrollabile + composer, stati di errore, empty state centrato; ma senza avatar e senza raggruppamento |

**Raccomandazione**: scheletro da prompt-kit (avatar + sticky scroll con la licenza più
semplice), raggruppamento per autore scritto a mano.

---

### (b) Blocco di conferma/approvazione (approve/reject inline)

L'esigenza meglio coperta di tutte, e con due candidati fatti *esattamente* per il
human-in-the-loop agentico.

| Componente | URL | Licenza (verificata a monte) | Dipendenze | Giudizio |
|---|---|---|---|---|
| **Confirmation** (Vercel AI Elements) | <https://elements.ai-sdk.dev/components/confirmation> | **Apache-2.0** | shadcn Alert + Button, `cn`, tipo `ToolUIPart` da `ai` | **Prendere** — è letteralmente una macchina a stati di approvazione: `input-streaming`, `input-available`, `approval-requested`, `approval-responded`, `output-denied`, `output-available`, con `ConfirmationRequest` / `ConfirmationActions` / `ConfirmationAccepted` / `ConfirmationRejected` |
| **Bash Tool — approval footer** (Agent Elements) | <https://21st.dev/@21st/components/bash-tool/approval-footer> | **MIT** | `clsx`, `tailwind-merge` | **Prendere** — footer inline con due azioni («Skip» / «Run»), il pattern esatto richiesto, con dipendenze quasi nulle |
| **Plan Tool** (Agent Elements) | <https://21st.dev/@21st/components/plan-tool> · varianti `/approved`, `/pending-update` | **MIT** | `clsx`, `tailwind-merge`, `@tabler/icons-react` | **Prendere** — titolo + sommario espandibile con azione Approve, stati `idle`/`pending`; calza sul «piano di campagna da approvare» |
| **Edit Tool — approval footer** (Agent Elements) | <https://21st.dev/@21st/components/edit-tool/approval-footer> | **MIT** | `clsx`, `tailwind-merge` | **Adattare** — stesso pattern applicato a una diff; utile se il cliente approva modifiche testuali |
| **Approve & Reject buttons** (shadcn/studio) | <https://21st.dev/@ShadcnStudio/components/buttons/button-approve-n-reject> | ⚠️ **MIT + Commons Clause** (`LICENSE.md` di `shadcnstudio/shadcn-studio`; GitHub: `NOASSERTION`) | shadcn Button | **Lasciare** — vieta la ridistribuzione dei componenti «anche come versione portata, senza modifiche»: attrito inutile in un repo pubblico, per due bottoni riscrivibili in 10 righe |
| **Alert Dialog** (shadcn/ui) | <https://21st.dev/@shadcn/components/alert-dialog> | **MIT** (`shadcn-ui/ui`) | `@radix-ui/react-alert-dialog` | **Adattare** — è una modale, non un blocco inline: buona solo per conferme distruttive |

**Raccomandazione**: `Confirmation` di AI Elements se la app userà l'AI SDK; altrimenti
l'approval footer di Agent Elements, che è MIT e non tira dentro niente.

---

### (c) Card di stato con indicatore live («agente sta scrivendo/cercando»)

| Componente | URL | Licenza (verificata a monte) | Dipendenze | Giudizio |
|---|---|---|---|---|
| **Text Shimmer** (Agent Elements) | <https://21st.dev/@21st/components/text-shimmer/fast> | **MIT** | `clsx`, `tailwind-merge` | **Prendere** — descritto dall'autore come «shimmering status text for streaming agents», con `duration`/`spread`/`delay` e prop `as`. È esattamente l'indicatore live richiesto |
| **Thinking Tool** (Agent Elements) | <https://21st.dev/@21st/components/thinking-tool/collapsed> | **MIT** | `clsx`, `tailwind-merge`, `@tabler/icons-react` | **Prendere** — riga collassabile con due stati, `thinking` (shimmer animato) e `thought` (statico): è la «card di stato» completa |
| **Search Tool / MCP Tool / Subagent Tool** (Agent Elements) | <https://21st.dev/@21st/components/search-tool/alt-source-set> · `/mcp-tool/interrupted` · `/subagent-tool/interrupted` | **MIT** | non verificate singolarmente (la famiglia usa `clsx` + `tailwind-merge` + icone) | **Adattare** — card di stato per singolo tool con stato `interrupted`: preziose per una writers' room multi-agente |
| **Loader** (prompt-kit) | <https://prompt-kit.com> | **MIT** | **nessuna** (solo React + `cn`) | **Prendere** — verificato sul sorgente: zero dipendenze esterne |
| **Shimmer** (Vercel AI Elements) | <https://elements.ai-sdk.dev> | **Apache-2.0** | `motion/react` (MIT) | **Adattare** — equivalente al Text Shimmer ma introduce `motion` |
| **Spiral Loader** (Agent Elements) | <https://21st.dev/@21st/components/spiral-loader/sizes> | **MIT** | `clsx`, `tailwind-merge`, **`lottie-react`** (MIT) | **Lasciare** — bello, ma `lottie-react` per uno spinner è sproporzionato |
| **Typing Indicator** | <https://21st.dev/@ddoemonn/components/typing-indicator> | **licenza non verificata** | non verificate | **Lasciare** — nessun upstream tracciabile |
| **Message loading** (shadcn-chat) | <https://21st.dev/@jakobhoeg/components/message-loading> | **MIT** (`jakobhoeg/shadcn-chat`) | `lucide-react` | **Adattare** — tre puntini classici; repo non più mantenuto |

---

### (d) Sidebar collassabile

| Componente | URL | Licenza (verificata a monte) | Dipendenze | Giudizio |
|---|---|---|---|---|
| **Sidebar** (shadcn/ui) | <https://21st.dev/@shadcn/components/sidebar> | **MIT** (`shadcn-ui/ui`) | `lucide-react` (ISC), `@radix-ui/react-slot` (MIT), `class-variance-authority` (**Apache-2.0**) | **Prendere** — lo standard di fatto: collapsible integrato, persistenza via cookie, mobile drawer, scorciatoia tastiera. Nessuna ragione di cercare altro |
| **Dashboard with Collapsible Sidebar** | <https://21st.dev/@uniquesonu/components/dashboard-with-collapsible-sidebar> | **licenza non verificata** | non verificate | **Lasciare** — composizione già fatta, ma senza upstream verificabile |
| **Sidebar** (Manu Arora / Aceternity) | <https://21st.dev/@manuarora700/components/sidebar> | **licenza non verificata** — Aceternity UI ha componenti a pagamento, va controllata caso per caso | tipicamente `framer-motion` | **Lasciare** — rischio licenza in un repo pubblico, a fronte di zero vantaggi sulla shadcn |
| Altre (Animated Sidebar, Workbench Sidebar, Sidebar Light, …) | `/@unlumen/components/sidebar-001`, `/@nexus-ui/components/workbench-sidebar`, `/@inference-sh/components/sidebar-light` | **licenza non verificata** | non verificate | **Lasciare** |

*Nota*: su 21st.dev la ricerca «sidebar» restituisce ~21 risultati, ma solo quello di shadcn
ha una licenza verificabile a monte. Le altre sono variazioni estetiche.

---

### (e) Pannello a tre colonne ridimensionabile

| Componente | URL | Licenza (verificata a monte) | Dipendenze | Giudizio |
|---|---|---|---|---|
| **Resizable** (shadcn/ui) | <https://21st.dev/@shadcn/components/resizable> | **MIT** (`shadcn-ui/ui`); motore `react-resizable-panels` **MIT** (verificato su npm) | `lucide-react` (ISC), `react-resizable-panels` (MIT) | **Prendere** — la demo mostra già tre pannelli annidati, `direction="horizontal"`, supporto tastiera. È l'esigenza (e) risolta |
| **Splitter — Three Panels** (Ark UI) | <https://21st.dev/@anubra266/components/splitter/three-panels-splitter> | motore `@ark-ui/react` **MIT** (verificato su npm e su `chakra-ui/ark`); il wrapper su 21st punta a `tarkui.com` → **licenza del wrapper non verificata** | `@ark-ui/react` | **Adattare** — tre pannelli con min-size 20/40/20% pronti, ma introdurrebbe un secondo design system headless accanto a Radix |
| **Resizable** (varie) | `/@sean0205/components/resizable`, `/@preetsuthar17/components/resizable` | **licenza non verificata** | non verificate | **Lasciare** |

**Attenzione**: cercando «resizable» su 21st.dev la maggior parte dei risultati riguarda
*textarea* auto-ridimensionanti, *tabelle* con colonne trascinabili e la «Resizable Navbar»
di Aceternity — non pannelli. I candidati veri sono i due sopra.

---

### (f) Effetto typing / streaming del testo

| Componente | URL | Licenza (verificata a monte) | Dipendenze | Giudizio |
|---|---|---|---|---|
| **Response Stream** (prompt-kit) | <https://21st.dev/@ibelick/components/response-stream> · doc <https://prompt-kit.com/docs/response-stream> | **MIT** (`ibelick/prompt-kit`) | **nessuna** — verificato sul sorgente: importa solo `React` e `cn` | **Prendere** — il migliore del lotto: modalità typewriter e fade parola-per-parola, `fadeDuration`/`segmentDelay`, zero dipendenze |
| **Markdown (streaming)** (Agent Elements) | <https://21st.dev/@21st/components/markdown/streaming> | **MIT** | `clsx`, `tailwind-merge`, `react-markdown` (MIT), `remark-gfm` (MIT) | **Prendere** — serve quando il testo in streaming è markdown (heading, liste, tabelle, code fence): la demo aggiorna lo stato ogni 18 ms senza rompere il parsing |
| **Typewriter** (cult/ui) | <https://21st.dev/@cult-ui/components/typewriter> | **MIT** (`nolly-studio/cult-ui`) | non verificate singolarmente | **Adattare** — effetto decorativo, non pensato per token in arrivo da un modello |
| **Streamdown** (usato da Vercel AI Elements) | <https://github.com/vercel/streamdown> | **Apache-2.0** (verificato su npm) | pacchetto npm autonomo | **Adattare** — markdown pensato per lo streaming, ma è una dipendenza vera, non un copia-incolla |
| **Typing** (loading-ui) | <https://21st.dev/@loading-ui/components/typing> | **licenza non verificata** | non verificate | **Lasciare** |

---

## 3. Verifiche di stack sulle 4 fonti sospette

Tutte e quattro le fonti indicate sono state controllate. **Il sospetto è confermato in tutti
e quattro i casi: nessuna è utilizzabile in una web app React.**

| Fonte | Stack reale | Evidenza | Utilizzabile in React web? |
|---|---|---|---|
| **pub.dev/packages/fluent_ui** | **Flutter / Dart** | Descrizione letterale: «Implements Microsoft's Windows User Interface in Flutter». Tag SDK: `Flutter`. Licenza BSD-3-Clause | **No.** Fra le piattaforme è elencata «Web», ma è Flutter Web (compila in canvas/WASM), che non produce componenti React né classi Tailwind |
| **forui.dev** | **Flutter / Dart** | Claim in home page: «A platform-agnostic **Flutter** UI library for developers seeking consistent and elegant UIs across all devices». Licenze (repo `forus-labs/forui`): codice MIT, font OFL, icone ISC | **No.** «Platform-agnostic» si riferisce alle piattaforme Flutter (iOS/Android/desktop), non al framework |
| **reactnativereusables.com** (`founded-labs/react-native-reusables`) | **React Native** | README: «Bringing shadcn/ui to **React Native**. Beautifully crafted components with Nativewind/Uniwind». Licenza MIT | **No** — con un asterisco onesto: fra i *topic* del repo compare `react-native-web`, quindi in teoria è eseguibile sul web tramite quell'adapter. Ma significherebbe portarsi dietro react-native-web + Nativewind in una app React+Tailwind: costo sproporzionato, e i componenti restano scritti con primitive RN (`View`, `Text`, `Pressable`), non con elementi DOM |
| **github.com/nativeui-org/ui** | **React Native** | README: «Beautifully designed **React Native** components», «Optimized for iOS and Android with React Native», «Works with **Expo** and your favorite tools». Licenza MIT | **No.** Nessuna menzione di react-native-web o di supporto browser |

**Conclusione**: le quattro fonti vanno scartate dalla shortlist. Restano utili al massimo
come riferimento visivo/di naming, mai come sorgente di codice.

---

## 4. Nota su component.gallery

**Consultata esclusivamente come riferimento di pattern — nomenclatura e varianti — e non
come sorgente di codice**, come da mandato. The Component Gallery non ospita codice: indicizza
come **60 componenti** vengono chiamati e strutturati in oltre cento design system reali,
con un conteggio di esempi per ciascuno (es. Accordion 101 esempi, Alert 108, Badge 123).

Il suo valore per questo progetto è la colonna dei **sinonimi**, che aiuta a scegliere un
nome e a non moltiplicare astrazioni. Esempio letterale dalla scheda Accordion:

> «Arrow toggle, Collapse, Collapsible sections, Collapsible, Details, Disclosure, Expandable,
> Expander, ShowyHideyThing»

Voci pertinenti al progetto: **Accordion** (per il blocco di approvazione collassabile),
**Avatar**, **Spinner** e **Progress indicator** (indicatore live), **Empty state** (chat
vuota), **Drawer** e **Navigation** (sidebar), **Stepper** (avanzamento della sessione),
**Toast**, **Tooltip**, **Skeleton**.

**Limite da mettere a verbale**: il catalogo **non contiene** voci per «chat», «message
thread», «split pane / resizable panel» né «sidebar» come entità autonoma. Sono pattern troppo
recenti o troppo di prodotto per un indice di design system generalisti. Per le esigenze (a),
(e) ed (f) component.gallery non offre nemmeno un riferimento di nomenclatura.

---

## 5. Sintesi operativa

Se si dovesse partire domani, la combinazione con il minor debito tecnico e legale è:

| Esigenza | Scelta | Licenza |
|---|---|---|
| (a) Chat timeline | prompt-kit `Message` + `ChatContainer` (raggruppamento per autore da scrivere) | MIT |
| (b) Approvazione inline | Agent Elements `bash-tool/approval-footer` + `plan-tool` | MIT |
| (c) Stato live | Agent Elements `text-shimmer` + `thinking-tool` | MIT |
| (d) Sidebar | shadcn/ui `sidebar` | MIT |
| (e) Tre colonne | shadcn/ui `resizable` (`react-resizable-panels`) | MIT |
| (f) Typing/streaming | prompt-kit `response-stream` (+ Agent Elements `markdown` se serve MD) | MIT |

Tutto MIT, con due sole eccezioni da valutare consapevolmente: `class-variance-authority` è
**Apache-2.0** (arriva comunque con shadcn/ui) e `lucide-react` è **ISC**. Entrambe permissive.

La famiglia **Vercel AI Elements** è tecnicamente la più completa — è l'unica con un
componente `Confirmation` che modella per intero il ciclo di approvazione, e ha anche `plan`,
`agent`, `persona`, `queue`, `checkpoint` — ma è **Apache-2.0** e presuppone l'AI SDK. Va
adottata come blocco unico se si sceglie quello stack, non pescandone un pezzo singolo.

### Cose da non fare

1. Non presumere MIT da 21st.dev: le schede non dichiarano licenza e i ToS non ne concedono una.
2. Non copiare da **shadcn/studio** senza modifiche sostanziali (Commons Clause).
3. Non mescolare Radix (shadcn/ui), Base UI (Agent Elements upstream) e Ark UI (Splitter) nella
   stessa app: scegliere una base headless e restarci.
4. Non aspettarsi il raggruppamento messaggi per autore da un componente pronto: non esiste.
