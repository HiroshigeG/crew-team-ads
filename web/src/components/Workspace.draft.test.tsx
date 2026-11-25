/** A goal raggiunto il server manda `proposal_drafted`: la card si riempie,
 *  ma senza mai calpestare il lavoro del Director. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Workspace } from './Workspace'
import { RoomContext } from '../lib/socket'
import { foldEvents, type FeedEntry, type RoomState } from '../state/fold'
import { CampaignProvider, useCampaign, type Proposal } from '../state/campaign'

const room = { send: () => {}, sendDirector: vi.fn(), sendPrivate: () => {} }
const ts = '2026-11-25T12:00:00+01:00'

const drafted = (seq: number, headline: string, body: string): FeedEntry => ({
  type: 'proposal_drafted', seq, ts, source: 'goal', headline, support: '', body,
})

function Probe() {
  const { proposal, setProposal } = useCampaign()
  return (
    <>
      <output data-testid="body">{proposal.body}</output>
      <button onClick={() => setProposal({ ...proposal, body: 'SCRITTO DAL DIRECTOR' })}>edit</button>
    </>
  )
}

function mount(state: RoomState, initial?: Proposal) {
  const tree = (s: RoomState) => (
    <RoomContext.Provider value={room}>
      <CampaignProvider initial={initial ? { proposal: initial } : undefined}>
        <Workspace state={s} />
        <Probe />
      </CampaignProvider>
    </RoomContext.Provider>
  )
  const r = render(tree(state))
  return { ...r, again: (s: RoomState) => r.rerender(tree(s)) }
}

afterEach(() => cleanup())

describe('Workspace: bozza di proposta dal goal', () => {
  it('riempie la card quando è vuota', () => {
    mount(foldEvents([drafted(5, 'Non ti incita. Non perde.', 'Film da 20 secondi.')]))
    expect(screen.getByTestId('body').textContent).toBe('Film da 20 secondi.')
    expect(screen.queryByText('Ancora niente sul tavolo')).toBeNull()
    expect(screen.getAllByText('Non ti incita. Non perde.').length).toBeGreaterThan(0)
  })

  it('non calpesta una proposta già scritta dal Director', () => {
    mount(
      foldEvents([drafted(5, 'Bozza', 'bozza automatica')]),
      { headline: '', support: '', body: 'LA MIA PROPOSTA' },
    )
    expect(screen.getByTestId('body').textContent).toBe('LA MIA PROPOSTA')
  })

  it('applica la stessa bozza una volta sola: una modifica successiva resta', () => {
    const state = foldEvents([drafted(5, 'Bozza', 'bozza automatica')])
    const { again } = mount(state)
    expect(screen.getByTestId('body').textContent).toBe('bozza automatica')
    fireEvent.click(screen.getByText('edit'))
    again(foldEvents([drafted(5, 'Bozza', 'bozza automatica')]))   // stessa bozza (seq 5)
    expect(screen.getByTestId('body').textContent).toBe('SCRITTO DAL DIRECTOR')
  })
})
