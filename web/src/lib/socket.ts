/**
 * Il ponte client: un WebSocket che parla il contratto e alimenta
 * foldEvents. I messaggi del Director entrano come eco locale (con seq
 * frazionario, così si ordinano fra gli eventi server già arrivati).
 * Niente riconnessione automatica: il flusso non ha replay (contratto §1),
 * quindi una connessione persa si dichiara, non si maschera.
 */
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import type { ClientMessage, ServerEvent } from '../contract/types'
import type { FeedEntry } from '../state/fold'
import { FEED } from '../mocks/session'

export type LinkStatus = 'demo' | 'connecting' | 'open' | 'closed'

export interface RoomLink {
  entries: FeedEntry[]
  status: LinkStatus
  send: (msg: ClientMessage) => void
  sendDirector: (text: string) => void
  sendPrivate: (head: string, text: string) => void
}

export function useRoom(demo: boolean): RoomLink {
  const [entries, setEntries] = useState<FeedEntry[]>(demo ? FEED : [])
  const [status, setStatus] = useState<LinkStatus>(demo ? 'demo' : 'connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const lastSeq = useRef(0)

  useEffect(() => {
    if (demo) return
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws`)
    wsRef.current = ws
    ws.onopen = () => setStatus('open')
    ws.onclose = () => setStatus('closed')
    ws.onerror = () => setStatus('closed')
    ws.onmessage = (raw) => {
      const ev = JSON.parse(raw.data) as ServerEvent
      lastSeq.current = Math.max(lastSeq.current, ev.seq)
      setEntries((prev) => [...prev, ev])
    }
    return () => ws.close()
  }, [demo])

  const send = (msg: ClientMessage) => {
    wsRef.current?.send(JSON.stringify(msg))
  }

  const sendDirector = (text: string) => {
    // Eco locale: la UI mostra subito la battuta, il server la processa.
    lastSeq.current += 0.5
    setEntries((prev) => [
      ...prev,
      {
        type: 'director_echo',
        seq: lastSeq.current,
        ts: new Date().toISOString(),
        text,
      },
    ])
    if (!demo) send({ type: 'director_message', text })
  }

  const sendPrivate = (head: string, text: string) => {
    lastSeq.current += 0.5
    setEntries((prev) => [
      ...prev,
      {
        type: 'private_echo',
        seq: lastSeq.current,
        ts: new Date().toISOString(),
        head,
        text,
      },
    ])
    if (!demo) send({ type: 'private_message', head, text })
  }

  return { entries, status, send, sendDirector, sendPrivate }
}

export const RoomContext = createContext<
  Pick<RoomLink, 'send' | 'sendDirector' | 'sendPrivate'>
>({
  send: () => {},
  sendDirector: () => {},
  sendPrivate: () => {},
})

export const useRoomActions = () => useContext(RoomContext)
