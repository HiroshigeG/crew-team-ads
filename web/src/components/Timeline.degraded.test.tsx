/** Banner «Instradamento ridotto» (D37): chiuderlo vale per QUEL degrado.
 *  Prima un booleano lo nascondeva per sempre, anche per un guasto nuovo. */
import { afterEach, beforeAll, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Timeline } from './Timeline'
import { RoomContext } from '../lib/socket'
import { foldEvents, type FeedEntry } from '../state/fold'

const ts = '2026-11-26T08:00:00+01:00'
const degrade = (seq: number, plan: string): FeedEntry[] => [
  { type: 'router_degraded', seq, ts, plan_id: plan, reason: 'piano non valido' },
  { type: 'wave_planned', seq: seq + 1, ts, plan_id: plan, waves: [] },
]

function ui(feed: FeedEntry[]) {
  return (
    <RoomContext.Provider value={{ send: () => {}, sendDirector: () => {}, sendPrivate: () => {} }}>
      <Timeline state={foldEvents(feed)} />
    </RoomContext.Provider>
  )
}

const banner = () => screen.queryByRole('button', { name: 'Chiudi avviso' })

beforeAll(() => {
  Element.prototype.scrollTo ??= () => {}
})
afterEach(() => cleanup())

describe('Timeline: banner di instradamento ridotto', () => {
  it('chiuso resta chiuso per lo stesso degrado, torna per uno nuovo', () => {
    const first = degrade(1, 'p-01')
    const { rerender } = render(ui(first))
    fireEvent.click(banner()!)
    expect(banner()).toBeNull()

    rerender(ui([...first, { type: 'session_saved', seq: 3, ts, stamp: 's', file: 'f', channel: 'room' }]))
    expect(banner()).toBeNull()

    rerender(ui([...first, ...degrade(4, 'p-02')]))
    expect(banner()).not.toBeNull()
  })

  it('si spegne da solo quando il piano dopo è valido', () => {
    const { rerender } = render(ui(degrade(1, 'p-01')))
    expect(banner()).not.toBeNull()
    rerender(ui([...degrade(1, 'p-01'), { type: 'wave_planned', seq: 3, ts, plan_id: 'p-02', waves: [] }]))
    expect(banner()).toBeNull()
  })
})
