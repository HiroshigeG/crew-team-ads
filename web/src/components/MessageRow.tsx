import { ArrowRight, Lock } from 'lucide-react'
import { DIRECTOR, HEADS } from '../mocks/roster'
import type { TimelineMessage } from '../state/fold'
import { cn } from '../lib/cn'
import { TypingText } from './TypingText'

function clock(ts: string) {
  return new Date(ts).toLocaleTimeString('it-IT', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

const ROLE_BADGE: Record<string, string> = {
  market_researcher: 'ricerca',
  creative_strategist: 'strategia',
  cd: 'direzione creativa',
  copywriter: 'copy',
  social: 'social',
  producer: 'produzione',
}

export function MessageRow({ msg }: { msg: TimelineMessage }) {
  const isDirector = msg.speaker === 'director'
  const head = isDirector ? null : HEADS[msg.speaker]
  const name = isDirector ? DIRECTOR.name : (head?.name ?? msg.speaker)
  const color = isDirector ? DIRECTOR.color : (head?.color ?? '#999')
  const toHead = msg.to && msg.to !== 'director' ? HEADS[msg.to] : null

  return (
    <div
      className={cn(
        'group flex gap-3 px-4 py-2',
        isDirector && 'rounded-lg bg-raised py-3',
      )}
    >
      <div
        className="grid size-8 shrink-0 place-items-center rounded-full text-sm"
        style={{
          border: `1.5px solid ${color}`,
          background: `color-mix(in oklab, ${color} 12%, transparent)`,
        }}
        aria-hidden
      >
        {isDirector ? DIRECTOR.avatar : head?.avatar}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-[13.5px] font-semibold" style={{ color }}>
            {name}
          </span>
          {!isDirector && head && (
            <span className="rounded border border-edge px-1.5 py-px text-[10.5px] tracking-wide text-faint">
              {ROLE_BADGE[head.key]}
            </span>
          )}
          {/* La relazione viene dal campo `to` del contratto, mai dal testo */}
          {toHead && (
            <span className="flex items-center gap-1 text-xs text-dim">
              <ArrowRight className="size-3" aria-hidden />
              <span style={{ color: toHead.color }}>{toHead.name}</span>
            </span>
          )}
          {msg.isPrivate && (
            <span className="flex items-center gap-1 text-[10.5px] text-warn">
              <Lock className="size-3" aria-hidden /> privato
            </span>
          )}
          <span className="tnum ml-auto text-xs text-faint">{clock(msg.ts)}</span>
          {msg.route && (
            <span
              className={cn(
                'rounded px-1 py-px font-mono text-[10px]',
                msg.route === 'subscription'
                  ? 'bg-lifted text-faint'
                  : 'bg-warn/15 text-warn',
              )}
              title={
                msg.route === 'subscription'
                  ? 'Turno in abbonamento'
                  : 'Turno fatturato via API'
              }
            >
              {msg.route === 'subscription' ? 'abbonamento' : 'API'}
            </span>
          )}
        </div>
        <div className="mt-1 max-w-[72ch] text-[15px] leading-relaxed text-ink">
          {msg.streaming ? <TypingText text={msg.text} /> : msg.text}
        </div>
      </div>
    </div>
  )
}
