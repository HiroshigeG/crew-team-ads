import { useState } from 'react'
import { Check, ChevronDown, Globe, Pencil, Radar, X } from 'lucide-react'
import type { SearchPending, SearchResult } from '../contract/types'
import { HEADS } from '../mocks/roster'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'

/**
 * Il gate di ricerca: il momento HITL protagonista. Aperto: query + motivo +
 * tre verdetti (il payload che parte è un GateVerdict del contratto).
 * Risolto: chip di esito + digest ispezionabile.
 */
export function GateBlock({
  gate,
  result,
  queued = false,
}: {
  gate: SearchPending
  result: SearchResult | null
  /** Fase 4: le richieste si propongono UNA alla volta — se queued,
   *  niente pulsanti finché la precedente non è decisa. */
  queued?: boolean
}) {
  const head = HEADS[gate.speaker]
  const isSocial = gate.kind === 'social'
  const { send } = useRoomActions()
  const [editing, setEditing] = useState(false)
  const [query, setQuery] = useState(gate.query)
  const [verdict, setVerdict] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const resolved = result !== null || verdict !== null

  const decide = (v: 'approve' | 'deny' | 'rewrite') => {
    setVerdict(v)
    send({
      type: 'gate_verdict',
      request_id: gate.request_id,
      verdict: v,
      query: v === 'rewrite' ? query : null,
    })
  }

  return (
    <div
      className={cn(
        'mx-4 my-2 rounded-lg border',
        resolved ? 'border-edge' : 'border-warn/60 bg-warn/5',
      )}
    >
      <div className="flex items-start gap-3 px-3 py-2.5">
        {isSocial ? (
          <Radar
            className={cn('mt-0.5 size-4 shrink-0', resolved ? 'text-faint' : 'text-warn')}
            aria-hidden
          />
        ) : (
          <Globe
            className={cn('mt-0.5 size-4 shrink-0', resolved ? 'text-faint' : 'text-warn')}
            aria-hidden
          />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-[13px] text-dim">
            <span style={{ color: head?.color }}>{head?.name}</span>{' '}
            {isSocial
              ? 'chiede di interrogare il tool social:'
              : 'chiede di cercare sul web:'}
          </p>
          {editing ? (
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="mt-1 w-full rounded border border-accent bg-raised px-2 py-1 font-mono text-[13px] outline-none"
              autoFocus
            />
          ) : (
            <p className="mt-0.5 font-mono text-[13px] text-ink">{query}</p>
          )}
          <p className="mt-1 text-[13px] italic text-faint">
            Perché: {gate.why}
          </p>

          {!resolved && queued && (
            <p className="mt-2 text-[13px] text-faint">
              In coda: la stanza te la proporrà appena decidi la richiesta
              precedente.
            </p>
          )}
          {!resolved && !queued && (
            <div className="mt-2.5 flex flex-wrap gap-2">
              <button
                onClick={() => decide(editing ? 'rewrite' : 'approve')}
                className="flex items-center gap-1.5 rounded-md bg-ok/15 px-3 py-1.5 text-[13px] font-medium text-ok hover:bg-ok/25"
              >
                <Check className="size-3.5" aria-hidden />
                {editing ? 'Approva riscritta' : 'Approva'}
              </button>
              <button
                onClick={() => setEditing((e) => !e)}
                className="flex items-center gap-1.5 rounded-md bg-lifted px-3 py-1.5 text-[13px] font-medium text-dim hover:bg-hover hover:text-ink"
              >
                <Pencil className="size-3.5" aria-hidden />
                Riscrivi
              </button>
              <button
                onClick={() => decide('deny')}
                className="flex items-center gap-1.5 rounded-md bg-danger/10 px-3 py-1.5 text-[13px] font-medium text-danger hover:bg-danger/20"
              >
                <X className="size-3.5" aria-hidden />
                Nega
              </button>
            </div>
          )}

          {verdict && !result && (
            <p className="mt-2 text-[13px] text-dim">
              {verdict === 'deny'
                ? 'Ricerca negata. La testa risponderà dichiarando cosa non può verificare.'
                : 'Approvata. La ricerca parte…'}
            </p>
          )}

          {result && (
            <div className="mt-2">
              <button
                onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-1.5 text-[13px] text-dim hover:text-ink"
              >
                <span
                  className={cn(
                    'rounded px-1.5 py-px text-[10.5px] font-medium tracking-wide',
                    result.status === 'approved' && 'bg-ok/15 text-ok',
                    result.status === 'denied' && 'bg-danger/15 text-danger',
                    (result.status === 'failed' || result.status === 'empty') &&
                      'bg-warn/15 text-warn',
                  )}
                >
                  {result.status === 'approved' && 'completata'}
                  {result.status === 'denied' && 'negata'}
                  {result.status === 'failed' && 'fallita'}
                  {result.status === 'empty' && 'nessun risultato'}
                </span>
                {result.digest && (
                  <>
                    risultati
                    <ChevronDown
                      className={cn('size-3.5 transition-transform', open && 'rotate-180')}
                      aria-hidden
                    />
                  </>
                )}
              </button>
              {open && result.digest && (
                <pre className="mt-2 whitespace-pre-wrap rounded-md bg-bg px-3 py-2 font-mono text-xs leading-relaxed text-dim">
                  {result.digest}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
