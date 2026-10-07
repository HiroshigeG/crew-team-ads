import { useState } from 'react'
import { Target } from 'lucide-react'
import type { RoomState } from '../state/fold'
import { useRoomActions } from '../lib/socket'

/**
 * Il goal mode in regia (D27): da fermo è il lanciatore di `/goal <obiettivo>`
 * (stesso pattern del lanciatore collab qui sopra); a goal attivo mostra
 * obiettivo, giro k/N e l'ultimo verdetto del giudice. Score null = giudice
 * non disponibile quel giro: si dice, non si inventa un numero (fail-closed).
 */
export function GoalPanel({ state }: { state: RoomState }) {
  const { sendDirector } = useRoomActions()
  const [objective, setObjective] = useState('')
  const goalRunning = state.collab?.mode === 'goal'
  const busy = state.collab !== null // una corsa alla volta, collab inclusa
  const verdict = state.goal?.lastVerdict ?? null

  const launch = () => {
    const text = objective.trim()
    if (!text || busy) return
    sendDirector(`/goal ${text}`)
    setObjective('')
  }

  if (goalRunning && state.collab) {
    return (
      <section className="space-y-2 border-t border-edge px-4 py-3">
        <div className="flex items-baseline justify-between">
          <p className="label-caps">Obiettivo in corso</p>
          <span className="tnum text-xs text-faint">
            giro {state.collab.round}/{state.collab.total}
          </span>
        </div>
        <p className="text-[13px] leading-snug text-ink">
          {state.goal?.objective ??
            'Obiettivo dato dal Director (non visibile da questa sessione).'}
        </p>
        {verdict === null ? (
          <p className="text-[12px] text-faint">
            Il giudice parla a fine giro: in attesa del primo verdetto.
          </p>
        ) : verdict.score === null ? (
          <p className="text-[12px] leading-snug text-warn">
            Giudice non disponibile nell’ultimo giro: nessun punteggio, il giro
            conta comunque nel tetto.
          </p>
        ) : (
          <p className="text-[12px] leading-snug text-dim">
            <span className="tnum font-medium text-accent">
              {verdict.score}/10
            </span>{' '}
            al giro {verdict.round} — {verdict.reason}
          </p>
        )}
      </section>
    )
  }

  return (
    <section className="space-y-2 border-t border-edge px-4 py-3">
      <p className="label-caps">Dai un obiettivo</p>
      <input
        value={objective}
        onChange={(e) => setObjective(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') launch()
        }}
        placeholder="Obiettivo… («un claim per il target giovane»)"
        aria-label="Obiettivo del goal"
        className="w-full rounded-md border border-edge bg-raised px-2.5 py-1.5 text-[12.5px] text-ink outline-none placeholder:text-faint focus:border-accent"
      />
      <p className="text-[12px] leading-snug text-faint">
        La stanza gira da sola; un giudice esterno la ferma a obiettivo
        raggiunto (tetto 8 giri, Stop sempre disponibile).
      </p>
      <button
        onClick={launch}
        disabled={!objective.trim() || busy}
        className="flex w-full items-center justify-center gap-2 rounded-md border border-edge bg-raised px-3 py-2 text-[13px] font-medium text-ink hover:border-accent hover:bg-lifted disabled:pointer-events-none disabled:text-faint"
      >
        <Target className="size-3.5" aria-hidden />
        Avvia il goal
      </button>
    </section>
  )
}
