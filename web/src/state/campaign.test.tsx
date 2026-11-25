/** Stato condiviso della campagna: brief, proposta, versioni. Una sola fonte
 *  per Sidebar, Workspace ed export (prima: due copie dentro i due layout). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react'
import { RoomContext } from '../lib/socket'
import { foldEvents } from './fold'
import { CampaignProvider, proposalTitle, useCampaign } from './campaign'
import { exportBrief } from '../lib/export'
import { Sidebar } from '../components/Sidebar'
import { Workspace } from '../components/Workspace'

vi.mock('../lib/export', async (orig) => {
  const real = await orig<typeof import('../lib/export')>()
  return { ...real, downloadMarkdown: vi.fn() }
})
import * as exportLib from '../lib/export'

const room = { send: () => {}, sendDirector: vi.fn(), sendPrivate: () => {} }

afterEach(() => cleanup())
beforeEach(() => vi.clearAllMocks())

describe('proposalTitle', () => {
  it('usa la headline se c\'è', () => {
    expect(proposalTitle({ headline: ' «Non ti incita.» ', support: '', body: 'x' }))
      .toBe('«Non ti incita.»')
  })
  it('senza headline ricade sulla prima riga del body, accorciata', () => {
    const body = 'Claim: «Non ti incita. Non perde.» ' + 'a'.repeat(200)
    const t = proposalTitle({ headline: '', support: '', body })!
    expect(t.startsWith('Claim: «Non ti incita.')).toBe(true)
    expect(t.length).toBeLessThanOrEqual(80)
  })
  it('senza niente → null (il chiamante mostra «Ancora niente sul tavolo»)', () => {
    expect(proposalTitle({ headline: '', support: '  ', body: '' })).toBeNull()
  })
})

describe('exportBrief', () => {
  it('porta i valori scritti dal Director, non quelli di un\'altra copia', () => {
    expect(exportBrief({ obiettivo: 'O', budget: 'B', target: 'T', kpi: 'K' }))
      .toEqual({ Obiettivo: 'O', Budget: 'B', Target: 'T', KPI: 'K' })
  })
})

describe('useCampaign', () => {
  it('setBrief è visibile a tutti i consumatori dello stesso provider', () => {
    const { result } = renderHook(() => useCampaign(), { wrapper: CampaignProvider })
    act(() => result.current.setBrief({ ...result.current.brief, obiettivo: 'vendere' }))
    expect(result.current.brief.obiettivo).toBe('vendere')
  })
})

describe('brief → export (regressione del 25/11: brief vuoto nel Markdown)', () => {
  it('quello che il Director scrive nella Sidebar finisce nell\'export', () => {
    render(
      <RoomContext.Provider value={room}>
        <CampaignProvider
          initial={{
            proposal: { headline: '', support: '', body: 'Claim: «Non perde.»' },
            versions: ['Claim: «Non perde.»'],
          }}
        >
          <Sidebar />
          <Workspace state={foldEvents([])} />
        </CampaignProvider>
      </RoomContext.Provider>,
    )
    fireEvent.change(screen.getByPlaceholderText(/Cosa deve ottenere/i), {
      target: { value: 'Più vendite online' },
    })
    fireEvent.change(screen.getByPlaceholderText(/Chi vogliamo muovere/i), {
      target: { value: 'Runner urbani' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Markdown/i }))
    const md = vi.mocked(exportLib.downloadMarkdown).mock.calls[0][0] as string
    expect(md).toContain('- **Obiettivo**: Più vendite online')
    expect(md).toContain('- **Target**: Runner urbani')
  })
})

describe('Workspace: titolo della proposta', () => {
  it('con una proposta solo-body il titolo non resta «Ancora niente sul tavolo»', () => {
    render(
      <RoomContext.Provider value={room}>
        <CampaignProvider
          initial={{ proposal: { headline: '', support: '', body: 'Claim: «Non perde.»' } }}
        >
          <Workspace state={foldEvents([])} />
        </CampaignProvider>
      </RoomContext.Provider>,
    )
    expect(screen.queryByText('Ancora niente sul tavolo')).toBeNull()
    expect(screen.getAllByText(/Claim: «Non perde\.»/).length).toBeGreaterThan(0)
  })
})
