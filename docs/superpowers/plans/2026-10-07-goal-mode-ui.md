# Goal mode UI (D27) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agganciare il goal mode (D27, già funzionante lato server) all'interfaccia web della ADV Room: fold degli eventi, stato visibile in regia, aiuto comandi e lanciatore.

**Architecture:** Tutto in `web/`: il reducer `foldEvents` impara `goal_verdict` e il `mode: "goal"` di `collab_round` (TDD); un nuovo componente `GoalPanel` nella colonna di regia (RoomPanel) mostra obiettivo/giro/punteggio e fa da lanciatore `/goal`; Timeline aggiorna banner e aiuto comandi. Il server non si tocca.

**Tech Stack:** React 18 + TypeScript, Vitest, Tailwind (token della stanza), lucide-react, vite.

**Spec:** docs/DECISIONS.md voce D27 · docs/EVENT-CONTRACT.md §9 · brief del Director nel `/goal` di sessione (07/10/2026).

## Global Constraints

- Lavorare SOLO in `web/` (più la riga finale in `docs/DECISIONS.md`); `server/` intoccato.
- Score `null` = «giudice non disponibile in questo giro» — fail-closed, MAI un numero inventato.
- Testi UI in italiano, stile della stanza (niente redesign; token/classi esistenti: `label-caps`, `bg-raised`, `text-faint`, `tnum`, …).
- Repo pubblico: prima del commit `git config user.name` deve essere `HiroshigeG`; commit in italiano col perché; NIENTE push.
- Mai `git clean -fdx`/`-fdX`; non toccare `room_tui.py`, demo CLI, `BUILD_BRIEF.md`, `test_tui.py`, branch `tui-local`.
- Commit solo DOPO la demo dal browser (ordine voluto dal Director): prima verifica completa, poi commit codice, poi commit docs che cita lo sha.

## Review Focus

1. `goal_verdict` con `score: null` → la riga di sistema non deve mostrare numeri né `null`/`NaN`; `met` resta false (fail-closed).
2. Chiusura `collab_round {round:0, mode:"goal", reason:"stopped"}` (Stop del Director a metà corsa) → testo sensato, pannello goal che sparisce, nessun crash.
3. `goal_verdict` che arriva senza che la UI abbia mai visto l'eco `/goal` (es. riconnessione concettuale / obiettivo scritto a mano con spazi strani) → `objective` è `null`, il pannello mostra comunque giro e punteggio senza riga vuota.
4. `/goal` senza argomento o con soli spazi → il lanciatore non manda niente (il server lo ignorerebbe: `_goal_mode` ritorna None, ma la UI non deve sprecare un messaggio).
5. Due goal consecutivi nella stessa sessione → il secondo `/goal` sovrascrive l'obiettivo; il verdetto del vecchio goal non resta appeso nel pannello nuovo.

---

### Task 1: fold.ts — eventi goal (TDD)

**Files:**
- Modify: `web/src/state/fold.ts` (RoomState ~riga 100, switch ~righe 256-288)
- Test: `web/src/state/fold.test.ts`

**Interfaces:**
- Consumes: `GoalVerdict`, `CollabRound` da `../contract/types` (già nel contratto).
- Produces: `RoomState.goal: { objective: string | null; lastVerdict: { round: number; score: number | null; met: boolean; reason: string } | null } | null`; `RoomState.collab.mode` allargato a `'goal'`. GoalPanel e Timeline leggono questi.

- [ ] **Step 1: Scrivere i test che falliscono** — nuovo `describe('foldEvents: goal mode (D27)')` in fold.test.ts:

```ts
describe('foldEvents: goal mode (D27)', () => {
  it('collab_round mode goal apre il contatore e la riga «Goal: giro k/N»', () => {
    const feed: FeedEntry[] = [
      { type: 'director_echo', seq: seq(), ts, text: '/goal un claim per la e-bike' },
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
    ]
    const room = foldEvents(feed)
    expect(room.collab).toEqual({ round: 1, total: 8, mode: 'goal' })
    expect(room.goal?.objective).toBe('un claim per la e-bike')
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => 'text' in i && i.text === 'Goal: giro 1/8.')).toBe(true)
  })

  it('goal_verdict entra in timeline con punteggio e motivo, e aggiorna lastVerdict', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
      { type: 'goal_verdict', seq: seq(), ts, round: 1, score: 6, met: false,
        reason: 'manca il target giovane' },
    ]
    const room = foldEvents(feed)
    expect(room.goal?.lastVerdict).toEqual(
      { round: 1, score: 6, met: false, reason: 'manca il target giovane' })
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => 'text' in i &&
      i.text.includes('6/10') && i.text.includes('manca il target giovane'))).toBe(true)
  })

  it('score null = giudice non disponibile: mai un numero inventato (fail-closed)', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 2, total: 8, mode: 'goal' },
      { type: 'goal_verdict', seq: seq(), ts, round: 2, score: null, met: false,
        reason: 'giudice non disponibile questo giro' },
    ]
    const room = foldEvents(feed)
    expect(room.goal?.lastVerdict?.score).toBeNull()
    const line = room.items.find((i) => i.kind === 'system' && 'text' in i &&
      i.text.includes('iudice non disponibile'))
    expect(line).toBeDefined()
    expect(line && 'text' in line && /\d\/10|null|NaN/.test(line.text)).toBe(false)
  })

  it('chiusura reason met: obiettivo raggiunto, goal e collab si azzerano', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
      { type: 'goal_verdict', seq: seq(), ts, round: 1, score: 9, met: true, reason: 'ok' },
      { type: 'collab_round', seq: seq(), ts, round: 0, total: 0, mode: 'goal', reason: 'met' },
    ]
    const room = foldEvents(feed)
    expect(room.collab).toBeNull()
    expect(room.goal).toBeNull()
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => 'text' in i && i.text.includes('Obiettivo raggiunto'))).toBe(true)
  })

  it('chiusura cap in goal mode: tetto raggiunto senza obiettivo', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 8, total: 8, mode: 'goal' },
      { type: 'collab_round', seq: seq(), ts, round: 0, total: 0, mode: 'goal', reason: 'cap' },
    ]
    const room = foldEvents(feed)
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => 'text' in i &&
      i.text.includes('Tetto raggiunto senza obiettivo'))).toBe(true)
  })

  it('un secondo /goal sovrascrive obiettivo e verdetto precedenti', () => {
    const feed: FeedEntry[] = [
      { type: 'director_echo', seq: seq(), ts, text: '/goal vecchio obiettivo' },
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
      { type: 'goal_verdict', seq: seq(), ts, round: 1, score: 9, met: true, reason: 'ok' },
      { type: 'collab_round', seq: seq(), ts, round: 0, total: 0, mode: 'goal', reason: 'met' },
      { type: 'director_echo', seq: seq(), ts, text: '/goal nuovo obiettivo' },
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
    ]
    const room = foldEvents(feed)
    expect(room.goal?.objective).toBe('nuovo obiettivo')
    expect(room.goal?.lastVerdict).toBeNull()
  })

  it('cap fuori dal goal mode tiene il testo collab di sempre', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 0, mode: 'organic' },
      { type: 'collab_round', seq: seq(), ts, round: 0, total: 0, reason: 'cap' },
    ]
    const room = foldEvents(feed)
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => 'text' in i &&
      i.text.includes('tetto di sicurezza'))).toBe(true)
  })
})
```

- [ ] **Step 2: Vederli fallire** — `cd web && npm test -- --run src/state/fold.test.ts` → FAIL (type error su `goal` / testi mancanti).
- [ ] **Step 3: Implementazione minima** in fold.ts:
  - `RoomState.collab` → `mode?: 'fixed' | 'organic' | 'goal'`.
  - Nuovo campo documentato: `/** v1.3 (D27): goal in corso — obiettivo (dall'eco /goal), ultimo verdetto. */ goal: { objective: string | null; lastVerdict: { round: number; score: number | null; met: boolean; reason: string } | null } | null`.
  - Nel loop: `let goal = null`, `let lastGoalObjective: string | null = null`.
  - In `director_echo`: `const m = /^\/goal\s+(.+)/i.exec(e.text.trim()); if (m) lastGoalObjective = m[1].trim()`.
  - Nuovo `case 'goal_verdict'`: aggiorna `goal = { objective: goal?.objective ?? lastGoalObjective, lastVerdict: {round, score, met, reason} }`; riga di sistema: score null → `'Giudice non disponibile in questo giro: il giro conta comunque nel tetto.'` (tone `warn`); altrimenti `` `Giudice, giro ${e.round}: ${e.score}/10 — ${e.reason}` `` (tone `info`).
  - `case 'collab_round'` round>0 con `mode === 'goal'`: testo `` `Goal: giro ${e.round}/${e.total}.` ``; `goal = { objective: lastGoalObjective, lastVerdict: goal?.lastVerdict ?? null }` SOLO se goal era null (apertura) — a giri successivi conserva lastVerdict. Attenzione al caso "secondo /goal": alla chiusura goal torna null, quindi alla riapertura lastVerdict riparte pulito.
  - round 0: se `e.reason === 'met'` → `'Obiettivo raggiunto: la parola torna al Director.'`; se `mode === 'goal'` e reason `'cap'` → `'Tetto raggiunto senza obiettivo: la parola torna al Director.'`; se `mode === 'goal'` e `'stopped'` → `'Goal fermato dal Director.'`; altrimenti testi esistenti invariati. In ogni chiusura goal: `goal = null`.
  - `return { …, goal }`.
- [ ] **Step 4: Test verdi** — `npm test -- --run src/state/fold.test.ts` → PASS, poi l'intera suite `npm test -- --run` senza regressioni.

### Task 2: Timeline — banner goal + aiuto comandi

**Files:**
- Modify: `web/src/components/Timeline.tsx` (banner ~riga 278, EmptyRoom ~riga 126)

**Interfaces:**
- Consumes: `state.collab.mode === 'goal'`, `state.goal` da Task 1.

- [ ] **Step 1: Banner** — nel ramo `state.collab`, caso `mode === 'goal'`: `` `Goal in corso: giro ${round}/${total}. Un giudice esterno valuta ogni giro; lo Stop resta sempre disponibile.` ``
- [ ] **Step 2: Aiuto comandi** — nuova voce in EmptyRoom: `['🎯', 'Dai un obiettivo', '«/goal un claim per il target giovane» — la stanza gira da sola e un giudice la ferma a obiettivo raggiunto (tetto 8 giri).']`
- [ ] **Step 3: Verifica** — `npm test -- --run` ancora verde (nessun test rotto), `npx tsc --noEmit` pulito.

### Task 3: GoalPanel nella colonna di regia

**Files:**
- Create: `web/src/components/GoalPanel.tsx`
- Modify: `web/src/components/RoomPanel.tsx` (nuova `<section>` dopo «Discutete fra voi»)
- Test: `web/src/components/GoalPanel.test.tsx`

**Interfaces:**
- Consumes: `RoomState` (campi `collab`, `goal`), `useRoomActions().sendDirector`.
- Produces: `export function GoalPanel({ state }: { state: RoomState })`.

- [ ] **Step 0: Skill di design** — hallmark → frontend-design → ui-typography (regola CLAUDE.md), restando nello stile della stanza: niente redesign, pattern del lanciatore collab.
- [ ] **Step 1: Test del componente** (stile AgentCard.test.tsx): (a) con goal attivo renderizza obiettivo, «giro k/N» e ultimo punteggio «6/10»; (b) con `lastVerdict.score === null` mostra «giudice non disponibile», nessun numero; (c) da fermo mostra il lanciatore e il bottone è disabilitato con input vuoto; (d) submit con testo chiama `sendDirector('/goal <testo>')`.
- [ ] **Step 2: FAIL** — `npm test -- --run src/components/GoalPanel.test.tsx`.
- [ ] **Step 3: Implementazione** — due stati:
  - *Goal attivo* (`state.collab?.mode === 'goal'`): card con `label-caps` «Obiettivo in corso», testo obiettivo (o «(obiettivo non visibile da questa sessione)» se null), riga `tnum` «giro k/N», ultimo verdetto: «6/10 — motivo» / «giudice non disponibile in questo giro» / «in attesa del primo verdetto».
  - *Da fermo*: input «Obiettivo…» + bottone «Avvia il goal» (icona `Target`) che fa `sendDirector('/goal ' + v.trim())` solo se `v.trim()` non vuoto; disabilitato durante una collab/goal in corso.
- [ ] **Step 4: PASS + suite intera.** Montare in RoomPanel (desktop + drawer mobile ereditano: RoomPanel è lo stesso componente).

### Task 4: Verifica completa, demo dal browser, commit, docs

- [ ] **Step 1:** `cd web && npm test -- --run && npm run build && npm run lint` — tutto pulito.
- [ ] **Step 2: Skill post-build** — make-interfaces-feel-better (dettagli) e web-design-guidelines (accessibilità) sul nuovo componente; applicare i fix minori.
- [ ] **Step 3: Demo reale** — avviare server (`.venv/bin/uvicorn server.main:app --port 8000`) + web; dal browser: panchina per ridurre il costo a 2-3 teste, poi un `/goal` con obiettivo vero e modesto; screenshot/GIF di: lancio, riga «Goal: giro k/N», verdetto del giudice, pannello di regia, chiusura. Consegna al Director via SendUserFile.
- [ ] **Step 4: Commit codice** — verificare `git config user.name` = HiroshigeG; commit in italiano col perché (niente push).
- [ ] **Step 5: DECISIONS.md** — sotto D27, sostituire «resta lavoro aperto» con la riga «UI agganciata» + sha del commit + data (07/10/2026); secondo commit docs.

## Self-review

- Spec coverage: fold (1.a-e del brief) → Task 1; stato visibile in regia (2) → Task 3; aiuto comandi + lanciatore (3) → Task 2-3; verifica/demo/commit/docs → Task 4. ✓
- Nessun placeholder; tipi coerenti (`RoomState.goal` definito in Task 1, consumato in Task 2-3). ✓
- Review Focus: (1)→test score null; (2)→ramo `stopped` in Task 1 Step 3; (3)→objective null gestito in Task 3; (4)→guard sul trim in Task 3; (5)→test «secondo /goal». ✓
