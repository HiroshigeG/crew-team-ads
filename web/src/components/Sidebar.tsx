import { useState } from 'react'
import {
  Check,
  ChevronDown,
  HardDriveDownload,
  History,
  MessagesSquare,
  Send,
  Settings2,
} from 'lucide-react'
import { BLANK_CAMPAIGN, CAMPAIGN, DECISIONS_LOG } from '../mocks/session'
import { ROSTER } from '../mocks/roster'
import type { RoomState } from '../state/fold'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'
import { AgentCard } from './AgentCard'

function BriefField({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  onChange: (v: string) => void
}) {
  return (
    <label className="block">
      <span className="label-caps">{label}</span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={value.length > 36 ? 2 : 1}
        placeholder={placeholder}
        className="mt-1 w-full resize-none rounded-md border border-edge bg-raised px-2 py-1.5 text-[13.5px] leading-snug text-ink outline-none placeholder:text-faint focus:border-accent"
      />
    </label>
  )
}

export function Sidebar({
  state,
  demo = false,
  onOpenPrivate,
  onEditRoster,
  onOpenHistory,
  disabled,
  onToggleActive,
}: {
  state: RoomState
  /** 05/08: i dati MERIDIA vivono solo in demo — la stanza vera parte vuota. */
  demo?: boolean
  onOpenPrivate?: (key: string) => void
  onEditRoster?: () => void
  onOpenHistory?: () => void
  /** D22: chiavi delle teste in panchina. */
  disabled?: Set<string>
  /** D22: mette in panchina / fa rientrare una testa. */
  onToggleActive?: (key: string) => void
}) {
  const { sendDirector } = useRoomActions()
  const campaign = demo ? CAMPAIGN : BLANK_CAMPAIGN
  const decisions = demo ? DECISIONS_LOG : []
  const bench = disabled ?? new Set<string>()
  const activeCount = ROSTER.length - ROSTER.filter((h) => bench.has(h.key)).length
  const [brief, setBrief] = useState({
    obiettivo: campaign.objective,
    budget: campaign.budget,
    target: campaign.target,
    kpi: campaign.kpi,
  })
  // Il brief serve all'inizio: dopo l'invio si richiude da solo, così le 9
  // teste della stanza restano a video senza scroll (UX 05/08). Il chevron
  // lo riapre quando serve ritoccarlo.
  const [briefOpen, setBriefOpen] = useState(true)
  const briefFilled = Object.values(brief).some((v) => v.trim())
  // Lanciatore collab (D21/D22): il toggle dice al router N giri o "libera".
  const [collabFree, setCollabFree] = useState(false)
  const [rounds, setRounds] = useState(3)

  return (
    <aside className="flex h-full flex-col overflow-y-auto bg-raised">
      <div className="border-b border-edge px-4 py-4">
        <p className="label-caps">Campagna</p>
        <h1 className="mt-1 text-lg font-semibold leading-tight">
          {campaign.name}
        </h1>
        {campaign.brand && (
          <p className="mt-0.5 text-xs text-faint">{campaign.brand}</p>
        )}
      </div>

      <section className="border-b border-edge px-4 py-3">
        <button
          onClick={() => setBriefOpen((o) => !o)}
          aria-expanded={briefOpen}
          className="flex w-full items-center justify-between text-left"
        >
          <span className="label-caps">Brief</span>
          <span className="flex items-center gap-2">
            {!briefOpen && (
              <span className="max-w-[150px] truncate text-xs text-faint">
                {briefFilled ? brief.obiettivo || 'compilato' : 'da compilare'}
              </span>
            )}
            <ChevronDown
              className={cn(
                'size-3.5 text-faint transition-transform',
                briefOpen && 'rotate-180',
              )}
              aria-hidden
            />
          </span>
        </button>
        {briefOpen && (
          <div className="mt-3 space-y-3">
            <BriefField
              label="Obiettivo"
              value={brief.obiettivo}
              placeholder="Cosa deve ottenere la campagna"
              onChange={(v) => setBrief({ ...brief, obiettivo: v })}
            />
            <BriefField
              label="Budget"
              value={brief.budget}
              placeholder="es. 80.000 €"
              onChange={(v) => setBrief({ ...brief, budget: v })}
            />
            <BriefField
              label="Target"
              value={brief.target}
              placeholder="Chi vogliamo muovere"
              onChange={(v) => setBrief({ ...brief, target: v })}
            />
            <BriefField
              label="KPI"
              value={brief.kpi}
              placeholder="Come misuriamo il successo"
              onChange={(v) => setBrief({ ...brief, kpi: v })}
            />
            {/* Brief scritto a mano: apre la stanza senza bisogno di allegati. */}
            <button
              onClick={() => {
                const b = [
                  `PROJECT: ${brief.obiettivo}`,
                  `BUDGET: ${brief.budget}`,
                  `TARGET: ${brief.target}`,
                  `KPI: ${brief.kpi}`,
                ].join('\n')
                sendDirector(
                  `Ecco il brief della campagna. Stanza, reagite.\n\n${b}`,
                )
                setBriefOpen(false)   // il brief è partito: spazio alla stanza
              }}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-accent px-3 py-2 text-[13px] font-medium text-bg hover:opacity-90"
            >
              <Send className="size-3.5" aria-hidden />
              Manda il brief alla stanza
            </button>
          </div>
        )}
      </section>

      <section className="border-b border-edge px-2 py-3">
        <div className="flex items-center justify-between px-2 pb-1">
          <p className="label-caps">La stanza</p>
          {onEditRoster && (
            <button
              onClick={onEditRoster}
              className="rounded p-1 text-faint hover:bg-lifted hover:text-ink"
              title="Modifica il roster (rinomina, modelli, aggiungi o togli teste)"
              aria-label="Modifica il roster"
            >
              <Settings2 className="size-3.5" aria-hidden />
            </button>
          )}
        </div>
        <div className="space-y-0.5">
          {ROSTER.map((h) => (
            <AgentCard
              key={h.key}
              head={h}
              live={state.heads[h.key]}
              onOpen={onOpenPrivate ? () => onOpenPrivate(h.key) : undefined}
              onRetry={() => sendDirector(`@${h.key} riprova il tuo ultimo turno`)}
              active={!bench.has(h.key)}
              onToggleActive={
                onToggleActive ? () => onToggleActive(h.key) : undefined
              }
              canDisable={activeCount > 1}
            />
          ))}
        </div>
      </section>

      {/* Lanciatore collab (D21/D22): il toggle dice al router se dare N giri
          o lasciare la stanza libera. Instrada solo le teste attive. */}
      <section className="space-y-2 border-b border-edge px-4 py-3">
        <p className="label-caps">Discutete fra voi</p>
        <div className="flex items-center gap-1 rounded-md bg-bg p-0.5 text-[12px]">
          <button
            onClick={() => setCollabFree(false)}
            aria-pressed={!collabFree}
            className={cn(
              'flex-1 rounded px-2 py-1 transition-colors',
              !collabFree ? 'bg-lifted text-ink' : 'text-faint hover:text-dim',
            )}
          >
            N giri
          </button>
          <button
            onClick={() => setCollabFree(true)}
            aria-pressed={collabFree}
            className={cn(
              'flex-1 rounded px-2 py-1 transition-colors',
              collabFree ? 'bg-lifted text-ink' : 'text-faint hover:text-dim',
            )}
          >
            Libera
          </button>
        </div>
        {collabFree ? (
          <p className="text-[12px] leading-snug text-faint">
            Vanno avanti finché hanno qualcosa da dire (tetto 30 giri, Stop
            sempre disponibile).
          </p>
        ) : (
          <label className="flex items-center justify-between text-[12.5px] text-dim">
            Giri
            <input
              type="number"
              min={1}
              max={20}
              value={rounds}
              onChange={(e) =>
                setRounds(Math.max(1, Math.min(20, Number(e.target.value) || 1)))
              }
              className="tnum w-16 rounded-md border border-edge bg-raised px-2 py-1 text-right text-ink outline-none focus:border-accent"
            />
          </label>
        )}
        <button
          onClick={() =>
            sendDirector(collabFree ? '/auto libero' : `/auto ${rounds}`)
          }
          className="flex w-full items-center justify-center gap-2 rounded-md border border-edge bg-raised px-3 py-2 text-[13px] font-medium text-ink hover:border-accent hover:bg-lifted"
        >
          <MessagesSquare className="size-3.5" aria-hidden />
          Avvia la discussione
        </button>
      </section>

      <section className="px-4 py-4">
        <p className="label-caps pb-2">Decisioni prese</p>
        {decisions.length > 0 ? (
          <ul className="space-y-2">
            {decisions.map((d) => (
              <li key={d} className="flex gap-2 text-[13px] leading-snug text-dim">
                <Check className="mt-0.5 size-3.5 shrink-0 text-ok" aria-hidden />
                <span>{d}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] leading-snug text-faint">
            Ancora nessuna: arrivano man mano che la stanza decide.
          </p>
        )}
      </section>

      <div className="mt-auto border-t border-edge">
        {(state.routes.subscription > 0 || state.routes.api > 0) && (
          <p className="tnum px-4 pt-2.5 text-xs text-faint">
            Turni Claude: {state.routes.subscription} in abbonamento ·{' '}
            <span className={state.routes.api > 0 ? 'text-warn' : undefined}>
              {state.routes.api} via API
            </span>
          </p>
        )}
        <div className="flex items-center gap-2 px-4 py-2.5 text-xs text-faint">
          {state.lastSaved ? (
            <>
              <HardDriveDownload className="size-3.5 shrink-0" aria-hidden />
              <span className="min-w-0 truncate">
                Salvata · <span className="font-mono">{state.lastSaved.file}</span>
              </span>
            </>
          ) : (
            <span className="min-w-0 flex-1" />
          )}
          {onOpenHistory && (
            <button
              onClick={onOpenHistory}
              className="ml-auto flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 hover:bg-lifted hover:text-ink"
              title="Storico sessioni (sola lettura)"
            >
              <History className="size-3.5" aria-hidden />
              Storico
            </button>
          )}
        </div>
      </div>
    </aside>
  )
}
