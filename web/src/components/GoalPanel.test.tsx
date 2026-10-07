/** GoalPanel (D27): lanciatore `/goal` + stato del goal in corso in regia. */
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { GoalPanel } from './GoalPanel'
import { RoomContext } from '../lib/socket'
import { foldEvents, type RoomState } from '../state/fold'

const idle = (): RoomState => foldEvents([])

const active = (over: Partial<NonNullable<RoomState['goal']>> = {}): RoomState => ({
  ...foldEvents([]),
  collab: { round: 3, total: 8, mode: 'goal' },
  goal: {
    objective: 'un claim per il target giovane',
    lastVerdict: { round: 2, score: 6, met: false, reason: 'manca il tono' },
    ...over,
  },
})

function mount(state: RoomState) {
  const sendDirector = vi.fn()
  render(
    <RoomContext.Provider
      value={{ send: () => {}, sendDirector, sendPrivate: () => {} }}
    >
      <GoalPanel state={state} />
    </RoomContext.Provider>,
  )
  return sendDirector
}

describe('GoalPanel: goal in corso', () => {
  it('mostra obiettivo, giro k/N e ultimo punteggio', () => {
    mount(active())
    expect(screen.getByText('un claim per il target giovane')).toBeTruthy()
    expect(screen.getByText(/giro 3\/8/)).toBeTruthy()
    expect(screen.getByText(/6\/10/)).toBeTruthy()
    expect(screen.getByText(/manca il tono/)).toBeTruthy()
  })

  it('score null → «giudice non disponibile», mai un numero', () => {
    mount(active({
      lastVerdict: { round: 2, score: null, met: false, reason: 'judge giù' },
    }))
    expect(screen.getByText(/giudice non disponibile/i)).toBeTruthy()
    expect(screen.queryByText(/\d\/10/)).toBeNull()
  })

  it('senza verdetti ancora: in attesa del primo verdetto', () => {
    mount(active({ lastVerdict: null }))
    expect(screen.getByText(/primo verdetto/i)).toBeTruthy()
  })
})

describe('GoalPanel: lanciatore', () => {
  it('da fermo mostra il lanciatore, disabilitato con obiettivo vuoto', () => {
    mount(idle())
    const btn = screen.getByRole('button', { name: /avvia il goal/i })
    expect((btn as HTMLButtonElement).disabled).toBe(true)
  })

  it('con un obiettivo scritto manda «/goal <testo>» alla stanza', () => {
    const sendDirector = mount(idle())
    fireEvent.change(screen.getByPlaceholderText(/obiettivo/i), {
      target: { value: '  tre frame per la e-bike  ' },
    })
    fireEvent.click(screen.getByRole('button', { name: /avvia il goal/i }))
    expect(sendDirector).toHaveBeenCalledWith('/goal tre frame per la e-bike')
  })

  it('con soli spazi non manda niente', () => {
    const sendDirector = mount(idle())
    fireEvent.change(screen.getByPlaceholderText(/obiettivo/i), {
      target: { value: '   ' },
    })
    const btn = screen.getByRole('button', { name: /avvia il goal/i })
    expect((btn as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(btn)
    expect(sendDirector).not.toHaveBeenCalled()
  })

  it('durante una collab il lanciatore è disabilitato (una corsa alla volta)', () => {
    const state: RoomState = {
      ...foldEvents([]),
      collab: { round: 1, total: 3, mode: 'fixed' },
    }
    mount(state)
    const btn = screen.getByRole('button', { name: /avvia il goal/i })
    expect((btn as HTMLButtonElement).disabled).toBe(true)
  })
})
