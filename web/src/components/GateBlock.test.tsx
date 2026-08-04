/** Il gate HITL (Fase 6): attivo coi tre verdetti, in coda senza pulsanti. */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GateBlock } from './GateBlock'
import type { SearchPending, SearchResult } from '../contract/types'

const GATE: SearchPending = {
  type: 'search_pending', ts: '2026-08-03T18:00:00+02:00', seq: 1,
  request_id: 'r-1', turn_id: 't-1', speaker: 'market_researcher',
  query: 'quota mercato', why: 'non posso saperlo',
}

describe('GateBlock', () => {
  it('attivo: query, perché e i tre verdetti', () => {
    render(<GateBlock gate={GATE} result={null} />)
    expect(screen.getByText('quota mercato')).toBeTruthy()
    expect(screen.getByText(/non posso saperlo/)).toBeTruthy()
    for (const label of ['Approva', 'Riscrivi', 'Nega']) {
      expect(screen.getByRole('button', { name: new RegExp(label) })).toBeTruthy()
    }
  })

  it('in coda: niente pulsanti finché non si decide il precedente', () => {
    render(<GateBlock gate={GATE} result={null} queued />)
    expect(screen.getByText(/In coda/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Approva/ })).toBeNull()
  })

  it('risolto: chip di esito e digest ispezionabile', () => {
    const result: SearchResult = {
      type: 'search_result', ts: GATE.ts, seq: 2, request_id: 'r-1',
      status: 'approved', final_query: 'quota mercato', digest: '- fonte (url)',
    }
    render(<GateBlock gate={GATE} result={result} />)
    expect(screen.getByText('completata')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Nega/ })).toBeNull()
  })
})
