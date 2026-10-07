import { useState } from 'react'
import { Plus, Trash2, X } from 'lucide-react'
import { applyRoster, EFFORTS, MODELS, ROSTER, type Head } from '../mocks/roster'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'

const KEY_RE = /^[a-z][a-z0-9_]{0,31}$/

/**
 * Roster editabile a runtime (Fase 5.3): rinomina, persona, modello, effort,
 * aggiungi/togli. Le modifiche partono come roster_update sul contratto e
 * valgono dal turno successivo — nessun restart. Sei teste sono il default,
 * non un vincolo.
 */
export function RosterEditor({
  onClose,
  onApplied,
}: {
  onClose: () => void
  onApplied: () => void
}) {
  const { send } = useRoomActions()
  const [draft, setDraft] = useState<Head[]>(() =>
    ROSTER.map((h) => ({ ...h })),
  )
  const [added, setAdded] = useState<Head | null>(null)

  const patch = (key: string, fields: Partial<Head>) =>
    setDraft((d) => d.map((h) => (h.key === key ? { ...h, ...fields } : h)))

  const apply = () => {
    const original = new Map(ROSTER.map((h) => [h.key, h]))
    for (const h of draft) {
      const before = original.get(h.key)
      if (!before) {
        send({ type: 'roster_update', action: 'add', key: h.key, fields: h })
        continue
      }
      const changed: Record<string, unknown> = {}
      for (const f of ['name', 'avatar', 'color', 'model_id', 'persona', 'tagline', 'effort'] as const) {
        if (h[f] !== before[f]) changed[f] = h[f]
      }
      if (Object.keys(changed).length) {
        send({ type: 'roster_update', action: 'update', key: h.key, fields: changed })
      }
    }
    for (const h of ROSTER) {
      if (!draft.some((d) => d.key === h.key)) {
        send({ type: 'roster_update', action: 'remove', key: h.key, fields: null })
      }
    }
    applyRoster(draft)
    onApplied()
    onClose()
  }

  const field =
    'w-full rounded-md border border-edge bg-bg px-2 py-1.5 text-[13px] outline-none focus:border-accent'

  return (
    <>
      <button className="fixed inset-0 z-40 bg-bg/70" onClick={onClose} aria-label="Chiudi" />
      <div className="fixed inset-y-6 left-1/2 z-50 flex w-[680px] max-w-[94vw] -translate-x-1/2 flex-col rounded-xl border border-edge bg-raised shadow-2xl">
        <header className="flex items-center justify-between border-b border-edge px-5 py-3.5">
          <div>
            <h2 className="text-[16px] font-semibold">Il roster della stanza</h2>
            <p className="text-[12px] text-faint">
              Le modifiche valgono dal turno successivo, senza riavvii.
            </p>
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 text-dim hover:bg-lifted" aria-label="Chiudi">
            <X className="size-4" aria-hidden />
          </button>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {draft.map((h) => (
            <div key={h.key} className="rounded-lg border border-edge p-3">
              <div className="flex items-center gap-2">
                <span
                  className="grid size-8 shrink-0 place-items-center rounded-full"
                  style={{
                    border: `1.5px solid ${h.color}`,
                    background: `color-mix(in oklab, ${h.color} 12%, transparent)`,
                  }}
                  aria-hidden
                >
                  {h.avatar}
                </span>
                <input
                  className={cn(field, 'font-medium')}
                  value={h.name}
                  onChange={(e) => patch(h.key, { name: e.target.value })}
                  aria-label={`Nome di ${h.key}`}
                />
                <select
                  className={cn(field, 'w-[230px] shrink-0 font-mono text-[12px]')}
                  value={h.model_id}
                  onChange={(e) => patch(h.key, { model_id: e.target.value })}
                  aria-label={`Modello di ${h.key}`}
                >
                  {MODELS.map((m) => (
                    <option key={m} value={m}>{m.slice(m.indexOf('/') + 1)}</option>
                  ))}
                </select>
                <select
                  className={cn(field, 'w-[110px] shrink-0 text-[12px]')}
                  value={h.effort ?? ''}
                  onChange={(e) => patch(h.key, { effort: e.target.value })}
                  aria-label={`Effort di ${h.key}`}
                  disabled={!h.model_id.startsWith('anthropic/')}
                  title={
                    h.model_id.startsWith('anthropic/')
                      ? 'Profondità di ragionamento'
                      : 'Effort disponibile solo sulle teste Claude'
                  }
                >
                  {EFFORTS.map((e) => (
                    <option key={e} value={e}>{e || 'effort: default'}</option>
                  ))}
                </select>
                <button
                  onClick={() => setDraft((d) => d.filter((x) => x.key !== h.key))}
                  disabled={draft.length <= 1}
                  className="rounded-md p-1.5 text-dim hover:bg-danger/15 hover:text-danger disabled:opacity-30"
                  title={draft.length <= 1 ? 'La stanza non può restare vuota' : 'Togli dalla stanza'}
                  aria-label={`Rimuovi ${h.name}`}
                >
                  <Trash2 className="size-4" aria-hidden />
                </button>
              </div>
              <input
                className={cn(field, 'mt-2')}
                value={h.tagline ?? ''}
                onChange={(e) => patch(h.key, { tagline: e.target.value })}
                placeholder="Frase breve mostrata sulla card (in italiano)…"
                aria-label={`Frase breve di ${h.key}`}
              />
              <textarea
                className={cn(field, 'mt-2 resize-none leading-snug')}
                rows={2}
                value={h.persona}
                onChange={(e) => patch(h.key, { persona: e.target.value })}
                aria-label={`Persona di ${h.key}`}
              />
            </div>
          ))}

          {added ? (
            <div className="rounded-lg border border-accent/50 p-3">
              <div className="grid grid-cols-4 gap-2">
                <input className={field} placeholder="chiave (es. media)" value={added.key}
                  onChange={(e) => setAdded({ ...added, key: e.target.value.toLowerCase() })} />
                <input className={field} placeholder="Nome" value={added.name}
                  onChange={(e) => setAdded({ ...added, name: e.target.value })} />
                <input className={field} placeholder="Avatar (emoji)" value={added.avatar}
                  onChange={(e) => setAdded({ ...added, avatar: e.target.value })} />
                <select className={cn(field, 'font-mono text-[12px]')} value={added.model_id}
                  onChange={(e) => setAdded({ ...added, model_id: e.target.value })}>
                  {MODELS.map((m) => (
                    <option key={m} value={m}>{m.slice(m.indexOf('/') + 1)}</option>
                  ))}
                </select>
              </div>
              <textarea className={cn(field, 'mt-2 resize-none')} rows={2}
                placeholder="Persona (in inglese, come le altre)…" value={added.persona}
                onChange={(e) => setAdded({ ...added, persona: e.target.value })} />
              <div className="mt-2 flex gap-2">
                <button
                  className="rounded-md bg-accent px-3 py-1.5 text-[13px] font-medium text-bg disabled:opacity-40"
                  disabled={
                    !KEY_RE.test(added.key) ||
                    draft.some((h) => h.key === added.key) ||
                    !added.name.trim()
                  }
                  onClick={() => {
                    setDraft((d) => [...d, added])
                    setAdded(null)
                  }}
                >
                  Aggiungi alla stanza
                </button>
                <button
                  className="rounded-md bg-lifted px-3 py-1.5 text-[13px] text-dim"
                  onClick={() => setAdded(null)}
                >
                  Annulla
                </button>
              </div>
              {!KEY_RE.test(added.key) && added.key !== '' && (
                <p className="mt-1 text-[12px] text-danger">
                  Chiave non valida: minuscole, numeri e _, inizia con una lettera.
                </p>
              )}
            </div>
          ) : (
            <button
              onClick={() =>
                setAdded({
                  key: '', name: '', avatar: '🤖', color: '#8899aa',
                  model_id: MODELS[1] ?? MODELS[0], persona: ' You are ',
                  tagline: '', creativity: 5, effort: '',
                })
              }
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-edge py-2.5 text-[13px] text-dim hover:border-accent hover:text-ink"
            >
              <Plus className="size-4" aria-hidden />
              Aggiungi una testa
            </button>
          )}
        </div>

        <footer className="flex justify-end gap-2 border-t border-edge px-5 py-3">
          <button onClick={onClose} className="rounded-md bg-lifted px-4 py-2 text-[13.5px] text-dim hover:bg-hover">
            Annulla
          </button>
          <button onClick={apply} className="rounded-md bg-accent px-4 py-2 text-[13.5px] font-medium text-bg hover:opacity-90">
            Applica alla stanza
          </button>
        </footer>
      </div>
    </>
  )
}
