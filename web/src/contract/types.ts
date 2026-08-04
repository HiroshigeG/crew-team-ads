/**
 * Tipi del protocollo — COPIA TESTUALE di docs/EVENT-CONTRACT.md §5.
 * Non modificare qui: la fonte di verità è il contratto. La Fase 3
 * sostituirà i mock con un WebSocket che parla ESATTAMENTE questa forma.
 */

export const PROTOCOL_VERSION = 1

export type HeadStateName =
  | 'idle' | 'thinking' | 'speaking' | 'searching'
  | 'waiting_approval' | 'error'
export type TurnRoute = 'subscription' | 'api'
export type SearchStatus = 'approved' | 'denied' | 'failed' | 'empty'
export type SavedChannel = 'room' | 'private'
export type GateVerdictName = 'approve' | 'deny' | 'rewrite'
export type RosterAction = 'add' | 'update' | 'remove'

/** Uno step del piano, forma esatta di route_plan(). */
export interface WaveStep {
  speaker: string      // chiave della testa
  instruction: string  // sempre presente, eventualmente "" (mai assente)
  to: string           // chiave di una testa oppure "director"
}

interface ServerEventBase {
  ts: string   // ISO 8601, orologio del server
  seq: number  // monotono per connessione
}

export interface WavePlanned extends ServerEventBase {
  type: 'wave_planned'
  plan_id: string
  waves: WaveStep[][]
}

export interface TurnStarted extends ServerEventBase {
  type: 'turn_started'
  turn_id: string
  plan_id: string
  wave_index: number
  speaker: string
  to: string
  private: boolean
  after_search: string | null
}

export interface TurnToken extends ServerEventBase {
  type: 'turn_token'
  turn_id: string
  text: string
}

export interface TurnCompleted extends ServerEventBase {
  type: 'turn_completed'
  turn_id: string
  speaker: string
  to: string
  text: string
  private: boolean
}

export interface SearchPending extends ServerEventBase {
  type: 'search_pending'
  request_id: string
  turn_id: string
  speaker: string
  query: string
  why: string
  /** v1.2 (D23): 'search' = web (DuckDuckGo), 'social' = tool social configurato. */
  kind?: 'search' | 'social'
}

export interface SearchResult extends ServerEventBase {
  type: 'search_result'
  request_id: string
  status: SearchStatus
  final_query: string | null
  digest: string | null
  kind?: 'search' | 'social'
}

export interface HeadState extends ServerEventBase {
  type: 'head_state'
  speaker: string
  state: HeadStateName
  detail: string | null
}

export interface RouterDegraded extends ServerEventBase {
  type: 'router_degraded'
  plan_id: string
  reason: string
}

export interface TurnRouteEvent extends ServerEventBase {
  type: 'turn_route'
  turn_id: string
  route: TurnRoute
}

export interface SessionSaved extends ServerEventBase {
  type: 'session_saved'
  stamp: string
  file: string
  channel: SavedChannel
}

/** v1.1 (Fase 5): contatore collab; round=0,total=0 = corsa finita. */
export interface CollabRound extends ServerEventBase {
  type: 'collab_round'
  round: number
  total: number
  /** v1.2 (D21): "organic" = collab libera (total aperto, "giro k" senza
   *  denominatore); "fixed" = N giri col contatore classico. */
  mode?: 'fixed' | 'organic'
  /** v1.2 (D21): solo sull'evento di chiusura (round 0) — perché si è fermata. */
  reason?: 'done' | 'exhausted' | 'cap' | 'stopped'
}

export type ServerEvent =
  | WavePlanned | TurnStarted | TurnToken | TurnCompleted
  | SearchPending | SearchResult | HeadState | RouterDegraded
  | TurnRouteEvent | SessionSaved | CollabRound

// ---- browser → server ----

export interface DirectorMessage {
  type: 'director_message'
  text: string
}

export interface GateVerdict {
  type: 'gate_verdict'
  request_id: string
  verdict: GateVerdictName
  query: string | null
}

export interface Stop {
  type: 'stop'
}

export interface RosterFields {
  name?: string
  avatar?: string
  color?: string
  model_id?: string
  persona?: string
  creativity?: number
}

export interface RosterUpdate {
  type: 'roster_update'
  action: RosterAction
  key: string
  fields: RosterFields | null
}

export interface CreativitySet {
  type: 'creativity_set'
  key: string
  level: number
}

/** v1.1 (Fase 5): chat privata 1:1 — il server risponde con turni private:true. */
export interface PrivateMessage {
  type: 'private_message'
  head: string
  text: string
}

/** v1.1 (D15): studia un'immagine caricata; lo smista alla testa Gemini. */
export interface StudyImage {
  type: 'study_image'
  image_id: string
  text: string
}

/** v1.2 (D22): panchina — una testa disattivata non viene instradata né entra
 *  in collab (resta però raggiungibile in privato). */
export interface HeadActive {
  type: 'head_active'
  key: string
  active: boolean
}

export type ClientMessage =
  | DirectorMessage | GateVerdict | Stop | RosterUpdate | CreativitySet
  | PrivateMessage | StudyImage | HeadActive
