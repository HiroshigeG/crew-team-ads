import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronDown,
  CircleAlert,
  MessagesSquare,
  Paperclip,
  Route,
  Search,
  Send,
  Square,
  TriangleAlert,
  X,
} from 'lucide-react'
import type { RoomState, TimelineItem } from '../state/fold'
import { HEADS, ROSTER } from '../mocks/roster'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'
import { MessageRow } from './MessageRow'
import { GateBlock } from './GateBlock'

/** Raggruppa messaggi consecutivi di soli agenti (≥3) in blocchi collassabili. */
type Rendered =
  | { kind: 'item'; item: TimelineItem }
  | { kind: 'agent-run'; id: string; items: Extract<TimelineItem, { kind: 'message' }>[] }

function groupItems(items: TimelineItem[]): Rendered[] {
  const out: Rendered[] = []
  let run: Extract<TimelineItem, { kind: 'message' }>[] = []

  const flush = () => {
    if (run.length >= 3) {
      out.push({ kind: 'agent-run', id: run[0].id, items: run })
    } else {
      run.forEach((i) => out.push({ kind: 'item', item: i }))
    }
    run = []
  }

  for (const item of items) {
    if (item.kind === 'message' && item.msg.speaker !== 'director') {
      run.push(item)
    } else {
      flush()
      out.push({ kind: 'item', item })
    }
  }
  flush()
  return out
}

function AgentRun({
  items,
}: {
  items: Extract<TimelineItem, { kind: 'message' }>[]
}) {
  const [open, setOpen] = useState(true)
  const names = [...new Set(items.map((i) => HEADS[i.msg.speaker]?.name ?? i.msg.speaker))]

  return (
    <div className="my-1">
      <button
        onClick={() => setOpen((o) => !o)}
        className="mx-4 flex items-center gap-2 rounded px-2 py-1 text-xs text-faint hover:bg-lifted hover:text-dim"
        aria-expanded={open}
      >
        <MessagesSquare className="size-3.5" aria-hidden />
        <span>
          Scambio fra {names.join(', ')} · {items.length} messaggi
        </span>
        <ChevronDown
          className={cn('size-3.5 transition-transform', !open && '-rotate-90')}
          aria-hidden
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            {items.map((i) => (
              <MessageRow key={i.id} msg={i.msg} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/** Empty state (P1 della critica): la stanza vuota al primo avvio insegna
 *  invece di lasciare il Director davanti a un vuoto. */
function EmptyRoom({
  filtering,
  onClear,
}: {
  filtering: boolean
  onClear: () => void
}) {
  if (filtering) {
    return (
      <div className="mx-auto max-w-md px-6 pt-16 text-center">
        <p className="text-[14px] text-dim">Nessun messaggio col filtro attivo.</p>
        <button
          onClick={onClear}
          className="mt-3 rounded-md bg-lifted px-3 py-1.5 text-[13px] text-dim hover:bg-hover hover:text-ink"
        >
          Azzera filtri
        </button>
      </div>
    )
  }
  return (
    <div className="mx-auto max-w-lg px-6 pt-14 text-center">
      <div className="text-4xl" aria-hidden>🎬</div>
      <h2 className="mt-3 text-[17px] font-semibold">La stanza è pronta.</h2>
      <p className="mt-2 text-[14px] leading-relaxed text-dim">
        Apri con il brief: marca, tema, budget, target e KPI. Poi lascia che la
        stanza reagisca, oppure rivolgiti a una testa per nome.
      </p>
      <div className="mx-auto mt-5 max-w-sm space-y-2 text-left">
        {[
          ['📎', 'Carica il brief', 'Trascina un PDF nell’input: lo smistatore lo assegna a chi deve studiarlo.'],
          ['@', 'Chiama una testa', '«@strategist dammi tre angoli» — la @menzione la sceglie tu.'],
          ['⚙', 'Discutete fra voi', '«discutete fra voi per 3 giri» = N giri; «…finché avete qualcosa da dire» o «/auto libero» = collab libera.'],
        ].map(([icon, title, body]) => (
          <div key={title} className="flex gap-3 rounded-lg bg-raised px-3 py-2.5">
            <span className="mt-0.5 w-5 shrink-0 text-center text-dim">{icon}</span>
            <div>
              <p className="text-[13.5px] font-medium">{title}</p>
              <p className="text-[12.5px] text-faint">{body}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function SystemLine({ item }: { item: Extract<TimelineItem, { kind: 'system' }> }) {
  const Icon =
    item.tone === 'danger' ? CircleAlert : item.tone === 'warn' ? TriangleAlert : Route
  return (
    <div
      className={cn(
        'mx-4 my-1.5 flex items-center gap-2 rounded-md px-3 py-1.5 text-xs',
        item.tone === 'danger' && 'bg-danger/10 text-danger',
        item.tone === 'warn' && 'bg-warn/10 text-warn',
        item.tone === 'info' && 'bg-lifted text-dim',
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden />
      <span>{item.text}</span>
    </div>
  )
}

export function Timeline({ state }: { state: RoomState }) {
  const [draft, setDraft] = useState('')
  const [degradedSeen, setDegradedSeen] = useState(false)
  const [stopSent, setStopSent] = useState(false)
  const [attached, setAttached] = useState<{ name: string; text: string; isImage: boolean; imageId: string } | null>(null)
  const [uploadErr, setUploadErr] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  // Fase 5.6: filtro per agente + ricerca testuale nel transcript.
  const [speakerFilter, setSpeakerFilter] = useState<Set<string>>(new Set())
  const [query, setQuery] = useState('')

  const filtering = speakerFilter.size > 0 || query.trim().length > 0
  const visible = useMemo(() => {
    if (!filtering) return state.items
    const q = query.trim().toLowerCase()
    return state.items.filter((it) => {
      if (it.kind === 'message') {
        const m = it.msg
        if (
          speakerFilter.size &&
          m.speaker !== 'director' &&
          !speakerFilter.has(m.speaker)
        )
          return false
        if (q && !m.text.toLowerCase().includes(q)) return false
        return true
      }
      if (it.kind === 'gate') {
        if (speakerFilter.size && !speakerFilter.has(it.gate.speaker)) return false
        if (q) {
          const hay = `${it.gate.query} ${it.gate.why} ${it.result?.digest ?? ''}`
          return hay.toLowerCase().includes(q)
        }
        return true
      }
      // Righe di sistema: via quando si filtra per agente; testuale sì.
      if (speakerFilter.size) return false
      return q ? it.text.toLowerCase().includes(q) : true
    })
  }, [state.items, speakerFilter, query, filtering])

  const rendered = useMemo(() => groupItems(visible), [visible])
  const scrollRef = useRef<HTMLDivElement>(null)
  const { sendDirector, send } = useRoomActions()

  // Una chat atterra sull'ultimo messaggio: lì vivono il gate aperto e il
  // turno in streaming. Segue anche gli eventi nuovi in arrivo.
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [rendered.length])

  const submit = () => {
    const note = draft.trim()
    // Immagine: percorso di visione dedicato (D15) — va alla testa Gemini,
    // che è l'unica che la legge. Eco locale così resta a schermo.
    if (attached?.isImage) {
      sendDirector(`📎 ${attached.name} → alla testa con visione. ${note}`.trim())
      send({ type: 'study_image', image_id: attached.imageId, text: note })
      setDraft('')
      setAttached(null)
      return
    }
    // Documento di testo: entra come UN messaggio del Director e passa dal
    // solito router (nessuna @menzione = lo smistatore decide chi studia)
    // o da una @menzione se il Director ha già scelto la testa.
    let text = note
    if (attached) {
      const doc = `Documento allegato «${attached.name}»:\n"""\n${attached.text}\n"""`
      text = note ? `${note}\n\n${doc}` : doc
    }
    if (!text) return
    sendDirector(text)
    setDraft('')
    setAttached(null)
  }

  const onPick = async (f: File | undefined) => {
    if (!f) return
    setUploadErr('')
    try {
      const body = new FormData()
      body.append('file', f)
      const res = await fetch('/api/upload', { method: 'POST', body })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || `upload fallito (${res.status})`)
      }
      const d = await res.json()
      setAttached({ name: d.filename, text: d.text, isImage: d.is_image, imageId: d.image_id })
    } catch (e) {
      setUploadErr(
        e instanceof Error ? e.message : 'upload non disponibile (modalità demo?)',
      )
    }
  }

  return (
    <div className="flex h-full min-w-0 flex-col">
      {state.degraded && !degradedSeen && (
        <div className="flex items-center gap-2 border-b border-warn/30 bg-warn/10 px-4 py-2 text-[13px] text-warn">
          <TriangleAlert className="size-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1">
            Instradamento ridotto ({state.degraded.reason}): usa una @menzione
            (es. <span className="font-mono">@cd</span>) per scegliere chi parla.
          </span>
          <button
            onClick={() => setDegradedSeen(true)}
            className="rounded p-1 hover:bg-warn/15"
            aria-label="Chiudi avviso"
          >
            <X className="size-3.5" aria-hidden />
          </button>
        </div>
      )}

      {state.collab && (
        <div className="flex items-center gap-2 border-b border-accent/30 bg-accent/10 px-4 py-2 text-[13px] text-accent">
          <MessagesSquare className="size-4 shrink-0" aria-hidden />
          <span className="tnum">
            {state.collab.mode === 'organic'
              ? `Collab libera: giro ${state.collab.round}. La stanza va avanti finché ha qualcosa da dire; lo Stop resta sempre disponibile.`
              : `Collab in corso: giro ${state.collab.round}/${state.collab.total}. Lo Stop qui sotto resta sempre disponibile.`}
          </span>
        </div>
      )}

      {/* Barra filtri: sotto i 640px va a capo invece di accavallarsi. */}
      <div className="flex flex-wrap items-center gap-2 border-b border-edge px-4 py-1.5">
        <div className="flex flex-wrap items-center gap-1">
          {ROSTER.map((h) => {
            const active = speakerFilter.has(h.key)
            return (
              <button
                key={h.key}
                onClick={() =>
                  setSpeakerFilter((f) => {
                    const next = new Set(f)
                    if (next.has(h.key)) next.delete(h.key)
                    else next.add(h.key)
                    return next
                  })
                }
                className={cn(
                  'grid size-7 place-items-center rounded-full text-[13px] transition-opacity',
                  active ? 'opacity-100' : 'opacity-45 hover:opacity-80',
                )}
                style={{
                  border: `1.5px solid ${active ? h.color : 'var(--color-edge)'}`,
                  background: active
                    ? `color-mix(in oklab, ${h.color} 15%, transparent)`
                    : 'transparent',
                }}
                title={`Filtra: ${h.name}`}
                aria-pressed={active}
              >
                {h.avatar}
              </button>
            )
          })}
        </div>
        <div className="relative ml-auto w-56 max-[640px]:w-full">
          <Search
            className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-faint"
            aria-hidden
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Cerca nel transcript…"
            className="w-full rounded-md border border-edge bg-raised py-1 pl-7 pr-6 text-[12.5px] outline-none placeholder:text-faint focus:border-accent"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-faint hover:text-ink"
              aria-label="Pulisci ricerca"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          )}
        </div>
        {filtering && (
          <span className="tnum shrink-0 text-[11.5px] text-faint">
            {visible.length}/{state.items.length}
          </span>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 space-y-0.5 overflow-y-auto py-3">
        {rendered.length === 0 && (
          <EmptyRoom filtering={filtering} onClear={() => {
            setSpeakerFilter(new Set())
            setQuery('')
          }} />
        )}
        {rendered.map((r) =>
          r.kind === 'agent-run' ? (
            <AgentRun key={r.id} items={r.items} />
          ) : r.item.kind === 'message' ? (
            <motion.div
              key={r.item.id}
              initial={{ opacity: 0, y: 2 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              <MessageRow msg={r.item.msg} />
            </motion.div>
          ) : r.item.kind === 'gate' ? (
            <GateBlock
              key={r.item.id}
              gate={r.item.gate}
              result={r.item.result}
              queued={
                r.item.result === null &&
                state.pendingGates[0]?.request_id !== r.item.gate.request_id
              }
            />
          ) : (
            <SystemLine key={r.item.id} item={r.item} />
          ),
        )}
      </div>

      <div className="border-t border-edge px-4 pb-4 pt-3">
        {state.pendingGate && (
          <p className="mb-2 text-xs text-warn">
            La stanza aspetta il tuo verdetto sulla richiesta di ricerca qui sopra
            {state.pendingGates.length > 1 &&
              ` (altre ${state.pendingGates.length - 1} in coda)`}
            .
          </p>
        )}
        {stopSent && (
          <p className="mb-2 text-xs text-dim">
            Stop inviato: i turni in volo si completano, le ondate in coda non
            partono. La parola torna a te.
          </p>
        )}
        {uploadErr && (
          <p className="mb-2 text-xs text-danger">{uploadErr}</p>
        )}
        {attached && (
          <div className="mb-2 flex items-center gap-2 rounded-md border border-edge bg-raised px-2.5 py-1.5 text-[12.5px]">
            <Paperclip className="size-3.5 shrink-0 text-accent" aria-hidden />
            <span className="min-w-0 flex-1 truncate">
              <span className="font-medium">{attached.name}</span>
              <span className="text-faint">
                {attached.isImage
                  ? ' — immagine, la studia la testa con visione (Gemini)'
                  : ` — ${(attached.text.length / 1000).toFixed(1)}k caratteri, pronto per lo smistatore`}
              </span>
            </span>
            <button
              onClick={() => setAttached(null)}
              className="shrink-0 rounded p-0.5 text-faint hover:text-ink"
              aria-label="Togli l'allegato"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </div>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md,.markdown,.csv,image/*"
          className="hidden"
          onChange={(e) => {
            void onPick(e.target.files?.[0])
            e.target.value = ''
          }}
        />
        <div className="flex items-end gap-2">
          <button
            onClick={() => fileRef.current?.click()}
            className="grid size-10 shrink-0 place-items-center rounded-lg bg-lifted text-dim hover:bg-hover hover:text-ink"
            title="Carica un documento (PDF, testo) — lo smistatore decide chi lo studia"
            aria-label="Carica un documento"
          >
            <Paperclip className="size-4" aria-hidden />
          </button>
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
            placeholder="Parla alla stanza… («@cd sviluppa il frame due», «discutete fra voi per 3 giri»)"
            className="max-h-40 flex-1 resize-none rounded-lg border border-edge bg-raised px-3 py-2.5 text-[14px] leading-snug outline-none placeholder:text-faint focus:border-accent"
          />
          <button
            className="grid size-10 shrink-0 place-items-center rounded-lg bg-lifted text-dim hover:bg-hover hover:text-danger"
            title="Ferma la stanza (i turni in volo si completano)"
            aria-label="Ferma la stanza"
            onClick={() => {
              send({ type: 'stop' })
              setStopSent(true)
              setTimeout(() => setStopSent(false), 8000)
            }}
          >
            <Square className="size-4" aria-hidden />
          </button>
          <button
            className={cn(
              'grid size-10 shrink-0 place-items-center rounded-lg',
              draft.trim() || attached
                ? 'bg-accent text-bg'
                : 'bg-lifted text-faint',
            )}
            disabled={!draft.trim() && !attached}
            onClick={submit}
            aria-label="Invia alla stanza"
          >
            <Send className="size-4" aria-hidden />
          </button>
        </div>
      </div>
    </div>
  )
}
