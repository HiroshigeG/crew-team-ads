import { motion } from 'framer-motion'
import { Power, PowerOff, RotateCw } from 'lucide-react'
import type { Head } from '../mocks/roster'
import type { HeadLive } from '../state/fold'
import { cn } from '../lib/cn'

const STATE_LABEL: Record<string, string> = {
  idle: 'in ascolto',
  thinking: 'sta pensando',
  speaking: 'sta scrivendo',
  searching: 'sta cercando',
  waiting_approval: 'aspetta il tuo ok',
  error: 'non disponibile',
}

const STATE_COLOR: Record<string, string> = {
  idle: 'bg-faint',
  thinking: 'bg-accent',
  speaking: 'bg-ok',
  searching: 'bg-accent',
  waiting_approval: 'bg-warn',
  error: 'bg-danger',
}

const PULSING = new Set(['thinking', 'speaking', 'searching'])

export function AgentCard({
  head,
  live,
  onOpen,
  onRetry,
  active = true,
  onToggleActive,
  canDisable = true,
}: {
  head: Head
  live?: HeadLive
  /** Fase 5.1: click sulla card = ingresso nel canale privato. */
  onOpen?: () => void
  /** Recupero errori (P2 della critica): riprova il turno della testa. */
  onRetry?: () => void
  /** D22: testa in riunione (true) o in panchina (false). */
  active?: boolean
  /** D22: mette in panchina / fa rientrare la testa. */
  onToggleActive?: () => void
  /** D22: la stanza non può svuotarsi — l'ultima attiva non si disattiva. */
  canDisable?: boolean
}) {
  // In panchina la card non mostra stati live: non sta partecipando.
  const state = active ? (live?.state ?? 'idle') : 'idle'
  // Compatta (05/08): con 9 teste la colonna deve stare a video senza
  // scroll. La persona va nel tooltip; lo stato compare SOLO quando la
  // testa fa qualcosa — a riposo la card è una riga sola.
  const busy = active && state !== 'idle'
  return (
    <div
      role={onOpen ? 'button' : undefined}
      tabIndex={onOpen ? 0 : undefined}
      onClick={onOpen}
      onKeyDown={(e) => e.key === 'Enter' && onOpen?.()}
      title={
        head.persona.trim() +
        (onOpen ? ' — click: canale privato' : '')
      }
      className={cn(
        'flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 hover:bg-lifted',
        !active && 'opacity-45',
      )}>
      <div
        className="grid size-7 shrink-0 place-items-center rounded-full text-[13px]"
        style={{
          border: `1.5px solid ${head.color}`,
          background: `color-mix(in oklab, ${head.color} 12%, transparent)`,
        }}
      >
        {head.avatar}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span
            className="truncate text-[13px] font-medium"
            style={{ color: head.color }}
          >
            {head.name}
          </span>
          {/* Creatività 0-10 a tacche */}
          <span
            className="flex shrink-0 items-center gap-[2px]"
            title={`Creatività ${head.creativity}/10`}
            aria-label={`Creatività ${head.creativity} su 10`}
          >
            {Array.from({ length: 10 }, (_, i) => (
              <span
                key={i}
                className="h-1.5 w-[2.5px] rounded-full"
                style={{
                  background:
                    i < head.creativity
                      ? `color-mix(in oklab, ${head.color} 75%, transparent)`
                      : 'var(--color-edge)',
                }}
              />
            ))}
          </span>
        </div>
        {busy && (
          <div className="mt-0.5 flex items-center gap-1.5">
            {PULSING.has(state) ? (
              <motion.span
                className={cn('size-1.5 rounded-full', STATE_COLOR[state])}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
              />
            ) : (
              <span className={cn('size-1.5 rounded-full', STATE_COLOR[state])} />
            )}
            <span
              className={cn(
                'text-xs',
                state === 'error'
                  ? 'text-danger'
                  : state === 'waiting_approval'
                    ? 'text-warn'
                    : 'text-dim',
              )}
            >
              {STATE_LABEL[state]}
            </span>
          </div>
        )}
        {!active && <p className="mt-0.5 text-xs text-faint">in panchina</p>}
        {busy && live?.detail && (
          <p className="mt-0.5 text-xs text-faint">{live.detail}</p>
        )}
        {state === 'error' && onRetry && (
          <button
            onClick={(e) => {
              e.stopPropagation()   // non aprire il privato: è un retry
              onRetry()
            }}
            className="mt-1 flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-danger hover:bg-danger/15"
          >
            <RotateCw className="size-3" aria-hidden /> riprova
          </button>
        )}
      </div>
      {onToggleActive && (
        <button
          onClick={(e) => {
            e.stopPropagation()      // non aprire il privato: è il toggle panchina
            onToggleActive()
          }}
          disabled={active && !canDisable}
          title={
            active
              ? canDisable
                ? 'In riunione — mettila in panchina'
                : 'È l’unica testa attiva: non si può mettere in panchina'
              : 'In panchina — falla rientrare'
          }
          aria-label={
            active ? `Metti ${head.name} in panchina` : `Fai rientrare ${head.name}`
          }
          aria-pressed={!active}
          className={cn(
            'shrink-0 self-center rounded p-1',
            active ? 'text-ok hover:bg-lifted' : 'text-faint hover:bg-lifted',
            active && !canDisable && 'cursor-not-allowed opacity-40 hover:bg-transparent',
          )}
        >
          {active ? (
            <Power className="size-3.5" aria-hidden />
          ) : (
            <PowerOff className="size-3.5" aria-hidden />
          )}
        </button>
      )}
    </div>
  )
}
