/**
 * Il reducer del contratto sotto test: è la macchina a stati della UI,
 * quindi qui si provano gli STATI (Fase 6), errore incluso.
 */
import { describe, expect, it } from 'vitest'
import { foldEvents, type FeedEntry } from './fold'

let n = 0
const seq = () => ++n
const ts = '2026-08-03T18:00:00+02:00'

function turn(speaker: string, text: string, opts: Partial<{
  to: string
  isPrivate: boolean
  id: string
}> = {}): FeedEntry[] {
  const id = opts.id ?? `t-${seq()}`
  return [
    {
      type: 'turn_started', seq: seq(), ts, turn_id: id, plan_id: 'p-1',
      wave_index: 0, speaker, to: opts.to ?? 'director',
      private: opts.isPrivate ?? false, after_search: null,
    },
    {
      type: 'turn_completed', seq: seq(), ts, turn_id: id, speaker,
      to: opts.to ?? 'director', text, private: opts.isPrivate ?? false,
    },
  ]
}

describe('foldEvents: stati delle teste', () => {
  it('propaga ogni stato, error incluso, con dettaglio leggibile', () => {
    const states = ['idle', 'thinking', 'speaking', 'searching',
      'waiting_approval', 'error'] as const
    const feed: FeedEntry[] = states.map((state) => ({
      type: 'head_state', seq: seq(), ts, speaker: `h_${state}`,
      state, detail: state === 'error' ? 'xai/grok-4.5: 429 rate limit' : null,
    }))
    const room = foldEvents(feed)
    for (const s of states) expect(room.heads[`h_${s}`].state).toBe(s)
    expect(room.heads.h_error.detail).toContain('429')
    // L'errore lascia una nota di servizio, MAI una battuta nel transcript.
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => i.tone === 'danger')).toBe(true)
    expect(room.items.filter((i) => i.kind === 'message')).toHaveLength(0)
  })
})

describe('foldEvents: privato stagno', () => {
  it('i turni privati vivono nel thread, mai nella timeline di stanza', () => {
    const feed: FeedEntry[] = [
      ...turn('cd', 'in stanza'),
      ...turn('cd', 'solo per te', { isPrivate: true }),
      { type: 'private_echo', seq: seq(), ts, head: 'cd', text: 'fra noi' },
    ]
    const room = foldEvents(feed)
    const roomTexts = room.items
      .filter((i) => i.kind === 'message')
      .map((i) => (i as { msg: { text: string } }).msg.text)
    expect(roomTexts).toEqual(['in stanza'])
    const priv = room.privateThreads.cd.map((m) => m.text)
    expect(priv).toEqual(['solo per te', 'fra noi'])
  })
})

describe('foldEvents: gate in coda, uno alla volta', () => {
  it('ordina i pending e li rimuove al risultato', () => {
    const feed: FeedEntry[] = [
      { type: 'search_pending', seq: seq(), ts, request_id: 'r-1',
        turn_id: 't-a', speaker: 'cd', query: 'q1', why: 'w1' },
      { type: 'search_pending', seq: seq(), ts, request_id: 'r-2',
        turn_id: 't-b', speaker: 'producer', query: 'q2', why: 'w2' },
    ]
    let room = foldEvents(feed)
    expect(room.pendingGates.map((g) => g.request_id)).toEqual(['r-1', 'r-2'])
    expect(room.pendingGate?.request_id).toBe('r-1')   // attivo = il primo

    feed.push({ type: 'search_result', seq: seq(), ts, request_id: 'r-1',
      status: 'approved', final_query: 'q1', digest: '- fonte' })
    room = foldEvents(feed)
    expect(room.pendingGate?.request_id).toBe('r-2')   // la coda avanza
  })
})

describe('foldEvents: degrado, collab, rotte', () => {
  it('router_degraded produce banner e riga con la via di uscita', () => {
    const room = foldEvents([{
      type: 'router_degraded', seq: seq(), ts, plan_id: 'p-9',
      reason: 'niente JSON',
    }])
    expect(room.degraded?.reason).toBe('niente JSON')
    const sys = room.items.find((i) => i.kind === 'system')
    expect(sys && 'text' in sys && sys.text).toContain('@menzione')
  })

  it('collab_round tiene il contatore e round 0 chiude la corsa', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 3 },
      { type: 'collab_round', seq: seq(), ts, round: 2, total: 3 },
    ]
    expect(foldEvents(feed).collab).toEqual({ round: 2, total: 3 })
    feed.push({ type: 'collab_round', seq: seq(), ts, round: 0, total: 0 })
    expect(foldEvents(feed).collab).toBeNull()
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

  it('conta le rotte di fatturazione per turno', () => {
    const feed: FeedEntry[] = [
      ...turn('cd', 'a', { id: 't-x' }),
      { type: 'turn_route', seq: seq(), ts, turn_id: 't-x', route: 'subscription' },
      ...turn('producer', 'b', { id: 't-y' }),
      { type: 'turn_route', seq: seq(), ts, turn_id: 't-y', route: 'api' },
    ]
    const room = foldEvents(feed)
    expect(room.routes).toEqual({ subscription: 1, api: 1 })
  })
})

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

  it('chiusura stopped in goal mode: goal fermato dal Director', () => {
    const feed: FeedEntry[] = [
      { type: 'collab_round', seq: seq(), ts, round: 2, total: 8, mode: 'goal' },
      { type: 'collab_round', seq: seq(), ts, round: 0, total: 0, mode: 'goal', reason: 'stopped' },
    ]
    const room = foldEvents(feed)
    expect(room.goal).toBeNull()
    const sys = room.items.filter((i) => i.kind === 'system')
    expect(sys.some((i) => 'text' in i && i.text.includes('Goal fermato'))).toBe(true)
  })

  it('un /goal scritto a metà corsa non cambia l’obiettivo in corso', () => {
    const feed: FeedEntry[] = [
      { type: 'director_echo', seq: seq(), ts, text: '/goal claim A' },
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
      { type: 'goal_verdict', seq: seq(), ts, round: 1, score: 4, met: false, reason: 'manca A' },
      // Il Director scrive un secondo /goal mentre A sta ancora girando:
      // il server lo accoda, il pannello deve restare su A fino alla chiusura.
      { type: 'director_echo', seq: seq(), ts, text: '/goal claim B' },
      { type: 'collab_round', seq: seq(), ts, round: 2, total: 8, mode: 'goal' },
    ]
    const room = foldEvents(feed)
    expect(room.goal?.objective).toBe('claim A')
    expect(room.goal?.lastVerdict?.score).toBe(4)
  })

  it('«/goal: X» (come lo accetta il server) non fa ricomparire l’obiettivo vecchio', () => {
    const feed: FeedEntry[] = [
      { type: 'director_echo', seq: seq(), ts, text: '/goal claim A' },
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
      { type: 'collab_round', seq: seq(), ts, round: 0, total: 0, mode: 'goal', reason: 'met' },
      { type: 'director_echo', seq: seq(), ts, text: '/goal: un claim nuovo' },
      { type: 'collab_round', seq: seq(), ts, round: 1, total: 8, mode: 'goal' },
    ]
    const room = foldEvents(feed)
    expect(room.goal?.objective).toBe(': un claim nuovo')
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
})
