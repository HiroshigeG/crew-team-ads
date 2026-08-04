/**
 * foldEvents: piega un flusso di eventi del contratto (EVENT-CONTRACT.md)
 * nello stato che la UI disegna. È l'unico punto che interpreta gli eventi:
 * in Fase 3 il WebSocket alimenta questa stessa funzione, i mock spariscono
 * e nient'altro cambia.
 *
 * I messaggi del Director non arrivano dal server (sono client→server):
 * nella timeline entrano come eco locale (DirectorEcho), esattamente come
 * farà l'app reale al momento dell'invio.
 */
import type {
  HeadStateName,
  SearchPending,
  SearchResult,
  ServerEvent,
  TurnRoute,
  WaveStep,
} from '../contract/types'
// In Fase 3 il roster arriverà dal server insieme agli eventi; per ora i
// nomi leggibili vengono dal mock (serve solo alla riga "chi parla").
import { HEADS } from '../mocks/roster'

function planLabel(waves: WaveStep[][]): string {
  const name = (k: string) => HEADS[k]?.name ?? k
  return waves
    .map((wave) =>
      wave
        .map((s) =>
          s.to !== 'director' ? `${name(s.speaker)} → ${name(s.to)}` : name(s.speaker),
        )
        .join(' + '),
    )
    .join(', poi ')
}

export interface DirectorEcho {
  type: 'director_echo'
  seq: number
  ts: string
  text: string
}

/** Eco locale di un messaggio privato del Director (v1.1). */
export interface PrivateEcho {
  type: 'private_echo'
  seq: number
  ts: string
  head: string
  text: string
}

export type FeedEntry = ServerEvent | DirectorEcho | PrivateEcho

export interface TimelineMessage {
  id: string
  speaker: string // chiave testa oppure "director"
  to: string | null // "director" | chiave testa | null (messaggi del Director)
  text: string
  ts: string
  isPrivate: boolean
  streaming: boolean
  route: TurnRoute | null
}

export type TimelineItem =
  | { kind: 'message'; id: string; ts: string; msg: TimelineMessage }
  | {
      kind: 'gate'
      id: string
      ts: string
      gate: SearchPending
      result: SearchResult | null
    }
  | {
      kind: 'system'
      id: string
      ts: string
      text: string
      tone: 'info' | 'warn' | 'danger'
    }

export interface HeadLive {
  state: HeadStateName
  detail: string | null
}

export interface RoomState {
  items: TimelineItem[]
  heads: Record<string, HeadLive>
  /** Gate aperti in ordine di arrivo: la UI ne propone UNO alla volta
   *  (Fase 4) — il primo è l'attivo, gli altri sono in coda. */
  pendingGates: SearchPending[]
  pendingGate: SearchPending | null
  degraded: { planId: string; reason: string } | null
  lastSaved: { stamp: string; file: string } | null
  lastPlan: WaveStep[][] | null
  /** v1.1: thread privati per testa — STAGNI, mai negli items di stanza. */
  privateThreads: Record<string, TimelineMessage[]>
  /** v1.1: collab in corso (null = nessuna). v1.2: `mode` "organic" = libera. */
  collab: { round: number; total: number; mode?: 'fixed' | 'organic' } | null
  /** Costo e rotta della sessione: turni per canale di fatturazione. */
  routes: { subscription: number; api: number }
}

export function foldEvents(entries: FeedEntry[]): RoomState {
  const items: TimelineItem[] = []
  const byTurn = new Map<string, TimelineMessage>()
  const gates = new Map<
    string,
    Extract<TimelineItem, { kind: 'gate' }>
  >()
  const heads: Record<string, HeadLive> = {}
  const pendingGates: SearchPending[] = []
  const privateThreads: Record<string, TimelineMessage[]> = {}
  const routes = { subscription: 0, api: 0 }
  let collab: RoomState['collab'] = null
  let degraded: RoomState['degraded'] = null
  let lastSaved: RoomState['lastSaved'] = null
  let lastPlan: WaveStep[][] | null = null

  const privateThread = (key: string) => (privateThreads[key] ??= [])

  const sorted = [...entries].sort((a, b) => a.seq - b.seq)

  for (const e of sorted) {
    switch (e.type) {
      case 'director_echo': {
        items.push({
          kind: 'message',
          id: `dir-${e.seq}`,
          ts: e.ts,
          msg: {
            id: `dir-${e.seq}`,
            speaker: 'director',
            to: null,
            text: e.text,
            ts: e.ts,
            isPrivate: false,
            streaming: false,
            route: null,
          },
        })
        break
      }
      case 'wave_planned': {
        lastPlan = e.waves
        // Trasparenza del routing (recon C §1.3): il Director vede in
        // anticipo chi prenderà la parola, con nomi leggibili.
        items.push({
          kind: 'system',
          id: `plan-${e.seq}`,
          ts: e.ts,
          text: `Prende la parola: ${planLabel(e.waves)}`,
          tone: 'info',
        })
        break
      }
      case 'private_echo': {
        privateThread(e.head).push({
          id: `pe-${e.seq}`,
          speaker: 'director',
          to: e.head,
          text: e.text,
          ts: e.ts,
          isPrivate: true,
          streaming: false,
          route: null,
        })
        break
      }
      case 'turn_started': {
        const msg: TimelineMessage = {
          id: e.turn_id,
          speaker: e.speaker,
          to: e.to,
          text: '',
          ts: e.ts,
          isPrivate: e.private,
          streaming: true,
          route: null,
        }
        byTurn.set(e.turn_id, msg)
        if (e.private) {
          // Stagno: il privato vive nel suo thread, mai in stanza.
          privateThread(e.speaker).push(msg)
        } else {
          items.push({ kind: 'message', id: e.turn_id, ts: e.ts, msg })
        }
        break
      }
      case 'turn_token': {
        const msg = byTurn.get(e.turn_id)
        if (msg) msg.text += e.text
        break
      }
      case 'turn_completed': {
        const msg = byTurn.get(e.turn_id)
        if (msg) {
          msg.text = e.text // il testo completo è autoritativo
          msg.streaming = false
        }
        break
      }
      case 'search_pending': {
        pendingGates.push(e)
        const item = {
          kind: 'gate' as const,
          id: e.request_id,
          ts: e.ts,
          gate: e,
          result: null,
        }
        gates.set(e.request_id, item)
        items.push(item)
        break
      }
      case 'search_result': {
        const item = gates.get(e.request_id)
        if (item) item.result = e
        const i = pendingGates.findIndex((g) => g.request_id === e.request_id)
        if (i >= 0) pendingGates.splice(i, 1)
        break
      }
      case 'head_state': {
        heads[e.speaker] = { state: e.state, detail: e.detail }
        if (e.state === 'error') {
          // Il dettaglio tecnico non entra mai nel transcript (D5): qui è
          // una nota di servizio per il Director, non una battuta.
          items.push({
            kind: 'system',
            id: `err-${e.seq}`,
            ts: e.ts,
            text: `${e.speaker}: non disponibile. Dettaglio nel canale privato.`,
            tone: 'danger',
          })
        }
        break
      }
      case 'router_degraded': {
        degraded = { planId: e.plan_id, reason: e.reason }
        items.push({
          kind: 'system',
          id: `deg-${e.seq}`,
          ts: e.ts,
          text: `Instradamento ridotto (${e.reason}): usa @menzione per scegliere chi parla.`,
          tone: 'warn',
        })
        break
      }
      case 'turn_route': {
        const msg = byTurn.get(e.turn_id)
        if (msg) msg.route = e.route
        routes[e.route] += 1
        break
      }
      case 'collab_round': {
        if (e.round === 0) {
          collab = null
          const text =
            e.reason === 'exhausted'
              ? 'Collab conclusa: la stanza ha esaurito, la parola torna al Director.'
              : e.reason === 'cap'
                ? 'Collab conclusa al tetto di sicurezza: la parola torna al Director.'
                : e.reason === 'stopped'
                  ? 'Collab fermata dal Director.'
                  : 'Collab conclusa: la parola torna al Director.'
          items.push({
            kind: 'system',
            id: `collab-${e.seq}`,
            ts: e.ts,
            text,
            tone: 'info',
          })
        } else {
          collab = { round: e.round, total: e.total, ...(e.mode ? { mode: e.mode } : {}) }
          items.push({
            kind: 'system',
            id: `collab-${e.seq}`,
            ts: e.ts,
            text:
              e.mode === 'organic'
                ? `Collab libera: giro ${e.round}.`
                : `Collab: giro ${e.round}/${e.total}.`,
            tone: 'info',
          })
        }
        break
      }
      case 'session_saved': {
        lastSaved = { stamp: e.stamp, file: e.file }
        break
      }
    }
  }

  return {
    items,
    heads,
    pendingGates,
    pendingGate: pendingGates[0] ?? null,
    degraded,
    lastSaved,
    lastPlan,
    privateThreads,
    collab,
    routes,
  }
}
