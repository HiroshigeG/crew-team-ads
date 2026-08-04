import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Lock, Send, X } from 'lucide-react'
import { HEADS } from '../mocks/roster'
import type { RoomState } from '../state/fold'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'
import { TypingText } from './TypingText'

/**
 * Chat privata 1:1 (Fase 5.1): stagna per costruzione — usa i canali privati
 * di RoomSession. La stanza non la vede e la testa, in stanza, non se ne
 * ricorda: qui la UI lo dice esplicitamente al Director.
 */
export function PrivateChat({
  headKey,
  state,
  onClose,
}: {
  headKey: string
  state: RoomState
  onClose: () => void
}) {
  const head = HEADS[headKey]
  const { sendPrivate } = useRoomActions()
  const [draft, setDraft] = useState('')
  const thread = state.privateThreads[headKey] ?? []
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [thread.length, thread[thread.length - 1]?.streaming])

  if (!head) return null

  const submit = () => {
    const text = draft.trim()
    if (!text) return
    sendPrivate(headKey, text)
    setDraft('')
  }

  return (
    <>
      <button
        className="fixed inset-0 z-40 bg-bg/60"
        onClick={onClose}
        aria-label="Chiudi il canale privato"
      />
      <motion.aside
        className="fixed inset-y-0 right-0 z-50 flex w-[400px] max-w-[92vw] flex-col border-l bg-raised"
        style={{ borderColor: `color-mix(in oklab, ${head.color} 45%, transparent)` }}
        initial={{ x: 420 }}
        animate={{ x: 0 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      >
        <header className="flex items-center gap-3 border-b border-edge px-4 py-3">
          <div
            className="grid size-9 place-items-center rounded-full text-base"
            style={{
              border: `1.5px solid ${head.color}`,
              background: `color-mix(in oklab, ${head.color} 12%, transparent)`,
            }}
            aria-hidden
          >
            {head.avatar}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[14px] font-semibold" style={{ color: head.color }}>
              {head.name}
            </p>
            <p className="flex items-center gap-1 text-[11.5px] text-warn">
              <Lock className="size-3" aria-hidden />
              Canale privato: la stanza non lo vede
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-dim hover:bg-lifted hover:text-ink"
            aria-label="Chiudi"
          >
            <X className="size-4" aria-hidden />
          </button>
        </header>

        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
          {thread.length === 0 && (
            <p className="pt-6 text-center text-[13px] leading-relaxed text-faint">
              Nessuno scambio privato ancora. Quello che vi dite qui resta qui:
              in stanza, la testa non se ne ricorda.
            </p>
          )}
          {thread.map((m) => (
            <div key={m.id} className="text-[14px] leading-relaxed">
              <span
                className="mr-2 font-semibold"
                style={{ color: m.speaker === 'director' ? 'var(--color-ink)' : head.color }}
              >
                {m.speaker === 'director' ? 'Tu' : head.name}
              </span>
              <span className="text-ink/90">
                {m.streaming ? <TypingText text={m.text} /> : m.text}
              </span>
            </div>
          ))}
        </div>

        <div className="border-t border-edge px-3 pb-3 pt-2.5">
          <div className="flex items-end gap-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  submit()
                }
              }}
              rows={2}
              placeholder={`In privato a ${head.name}…`}
              className="flex-1 resize-none rounded-lg border border-edge bg-bg px-3 py-2 text-[14px] leading-snug outline-none placeholder:text-faint focus:border-accent"
            />
            <button
              className={cn(
                'grid size-9 shrink-0 place-items-center rounded-lg',
                draft.trim() ? 'bg-accent text-bg' : 'bg-lifted text-faint',
              )}
              disabled={!draft.trim()}
              onClick={submit}
              aria-label="Invia in privato"
            >
              <Send className="size-4" aria-hidden />
            </button>
          </div>
        </div>
      </motion.aside>
    </>
  )
}
