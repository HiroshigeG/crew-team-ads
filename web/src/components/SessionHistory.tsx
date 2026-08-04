import { useEffect, useState } from 'react'
import { ArrowLeft, History, X } from 'lucide-react'

/**
 * Storico sessioni (Fase 5.5): i transcript di RoomSession dal server,
 * riapribili in sola lettura. In demo (o server giù) lo dice, senza fingere.
 */

interface SessionMeta {
  stamp: string
  file: string
  chars: number
  excerpt: string
}

function stampLabel(stamp: string): string {
  const m = stamp.match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/)
  if (!m) return stamp
  return `${m[3]}/${m[2]}/${m[1]} · ${m[4]}:${m[5]}`
}

export function SessionHistory({ onClose }: { onClose: () => void }) {
  const [sessions, setSessions] = useState<SessionMeta[] | null>(null)
  const [error, setError] = useState(false)
  const [open, setOpen] = useState<{ stamp: string; content: string } | null>(null)

  useEffect(() => {
    fetch('/api/sessions')
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions ?? []))
      .catch(() => setError(true))
  }, [])

  const read = (stamp: string) => {
    fetch(`/api/sessions/${stamp}`)
      .then((r) => r.json())
      .then((d) => setOpen({ stamp, content: d.content ?? '' }))
      .catch(() => setError(true))
  }

  return (
    <>
      <button className="fixed inset-0 z-40 bg-bg/70" onClick={onClose} aria-label="Chiudi" />
      <div className="fixed inset-y-10 left-1/2 z-50 flex w-[720px] max-w-[94vw] -translate-x-1/2 flex-col rounded-xl border border-edge bg-raised shadow-2xl">
        <header className="flex items-center gap-2.5 border-b border-edge px-5 py-3.5">
          {open ? (
            <button
              onClick={() => setOpen(null)}
              className="rounded-md p-1 text-dim hover:bg-lifted hover:text-ink"
              aria-label="Torna all'elenco"
            >
              <ArrowLeft className="size-4" aria-hidden />
            </button>
          ) : (
            <History className="size-4 text-faint" aria-hidden />
          )}
          <h2 className="flex-1 truncate text-[15px] font-semibold">
            {open ? `Sessione del ${stampLabel(open.stamp)} (sola lettura)` : 'Storico sessioni'}
          </h2>
          <button onClick={onClose} className="rounded-md p-1.5 text-dim hover:bg-lifted" aria-label="Chiudi">
            <X className="size-4" aria-hidden />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {open ? (
            <pre className="whitespace-pre-wrap font-sans text-[13.5px] leading-relaxed text-ink/90">
              {open.content}
            </pre>
          ) : error ? (
            <p className="pt-8 text-center text-[13px] text-faint">
              Storico non raggiungibile (modalità demo o server spento).
            </p>
          ) : sessions === null ? (
            <p className="pt-8 text-center text-[13px] text-faint">Carico lo storico…</p>
          ) : sessions.length === 0 ? (
            <p className="pt-8 text-center text-[13px] text-faint">
              Nessuna sessione salvata ancora: il transcript nasce col primo turno.
            </p>
          ) : (
            <ul className="space-y-1">
              {sessions.map((s) => (
                <li key={s.stamp}>
                  <button
                    onClick={() => read(s.stamp)}
                    className="w-full rounded-md px-3 py-2.5 text-left hover:bg-lifted"
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="tnum text-[13.5px] font-medium">
                        {stampLabel(s.stamp)}
                      </span>
                      <span className="tnum text-[11.5px] text-faint">
                        {(s.chars / 1000).toFixed(1)}k caratteri
                      </span>
                    </div>
                    {s.excerpt && (
                      <p className="mt-0.5 truncate text-[12.5px] text-dim">
                        «{s.excerpt}»
                      </p>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
