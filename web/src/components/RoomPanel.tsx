import { useState } from 'react'
import {
  HardDriveDownload,
  History,
  MessagesSquare,
  Settings2,
} from 'lucide-react'
import { ROSTER } from '../mocks/roster'
import type { RoomState } from '../state/fold'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'
import { AgentCard } from './AgentCard'
import { GoalPanel } from './GoalPanel'

/**
 * La colonna della REGIA (destra, 05/08): chi c'è in stanza, chi è in
 * panchina, il lanciatore della collab e i contatori di sessione. Nata
 * dallo split della vecchia Sidebar: a sinistra restano campagna e
 * proposta (il LAVORO), qui vive la gestione dei partecipanti.
 */
export function RoomPanel({
  state,
  onOpenPrivate,
  onEditRoster,
  onOpenHistory,
  disabled,
  onToggleActive,
}: {
  state: RoomState
  onOpenPrivate?: (key: string) => void
  onEditRoster?: () => void
  onOpenHistory?: () => void
  /** D22: chiavi delle teste in panchina. */
  disabled?: Set<string>
  /** D22: mette in panchina / fa rientrare una testa. */
  onToggleActive?: (key: string) => void
}) {
  const { sendDirector } = useRoomActions()
  const bench = disabled ?? new Set<string>()
  const activeCount = ROSTER.length - ROSTER.filter((h) => bench.has(h.key)).length
  // Lanciatore collab (D21/D22): il toggle dice al router N giri o "libera".
  const [collabFree, setCollabFree] = useState(false)
  const [rounds, setRounds] = useState(3)

  return (
    <aside className="flex h-full flex-col overflow-y-auto bg-raised">
      <section className="border-b border-edge px-2 py-3">
        <div className="flex items-center justify-between px-2 pb-1">
          <p className="label-caps">La stanza</p>
          <span className="flex items-center gap-1">
            <span className="tnum text-xs text-faint">
              {activeCount}/{ROSTER.length}
            </span>
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
          </span>
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
      <section className="space-y-2 px-4 py-3">
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

      {/* Goal mode (D27): lanciatore `/goal` e stato del goal in corso. */}
      <GoalPanel state={state} />

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
