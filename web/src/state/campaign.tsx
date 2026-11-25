/** Stato condiviso della campagna in lavorazione: brief, proposta, versioni
 *  bloccate. Prima viveva dentro Sidebar e Workspace, montati in DOPPIO (layout
 *  desktop + mobile): l'export leggeva una copia vuota. Ora è una fonte sola. */
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { BLANK_CAMPAIGN, CAMPAIGN } from '../mocks/session'

export interface Brief {
  obiettivo: string
  budget: string
  target: string
  kpi: string
}

export interface Proposal {
  headline: string
  support: string
  body: string
}

interface CampaignValue {
  brief: Brief
  setBrief: (b: Brief) => void
  proposal: Proposal
  setProposal: (p: Proposal | ((prev: Proposal) => Proposal)) => void
  versions: string[]
  addVersion: (v: string) => void
}

const EMPTY_PROPOSAL: Proposal = { headline: '', support: '', body: '' }

const DEMO_PROPOSAL: Proposal = {
  headline: '«Ricordati la serata.»',
  support: '«La sera comincia lucida.»',
  body: 'Quattro parole che sono un brindisi e una sfida. Mai spiegare la linea, mai la parola «senza»: il prodotto non si scusa.',
}

/** I dati MERIDIA vivono solo in demo: la stanza vera parte vuota. */
export function initialCampaign(demo: boolean): Partial<Pick<CampaignValue, 'brief' | 'proposal'>> {
  const c = demo ? CAMPAIGN : BLANK_CAMPAIGN
  return {
    brief: { obiettivo: c.objective, budget: c.budget, target: c.target, kpi: c.kpi },
    proposal: demo ? DEMO_PROPOSAL : EMPTY_PROPOSAL,
  }
}

/** Titolo della card «Proposta in lavorazione»: la headline se c'è; altrimenti
 *  la prima riga del body (la proposta può nascere da «Modifica», che scrive
 *  solo il body), accorciata; altrimenti il supporto; altrimenti null. */
export function proposalTitle(p: Proposal, max = 80): string | null {
  const first = (s: string) => s.trim().split('\n')[0].trim()
  const raw = first(p.headline) || first(p.body) || first(p.support)
  if (!raw) return null
  return raw.length <= max ? raw : raw.slice(0, max - 1).trimEnd() + '…'
}

const Ctx = createContext<CampaignValue | null>(null)

export function CampaignProvider({
  children,
  initial,
}: {
  children?: ReactNode
  initial?: Partial<{ brief: Brief; proposal: Proposal; versions: string[] }>
}) {
  const [brief, setBrief] = useState<Brief>(
    initial?.brief ?? { obiettivo: '', budget: '', target: '', kpi: '' },
  )
  const [proposal, setProposal] = useState<Proposal>(initial?.proposal ?? EMPTY_PROPOSAL)
  const [versions, setVersions] = useState<string[]>(initial?.versions ?? [])
  const value = useMemo<CampaignValue>(
    () => ({
      brief,
      setBrief,
      proposal,
      setProposal,
      versions,
      addVersion: (v) => setVersions((prev) => [...prev, v]),
    }),
    [brief, proposal, versions],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useCampaign(): CampaignValue {
  const v = useContext(Ctx)
  if (!v) throw new Error('useCampaign fuori da <CampaignProvider>')
  return v
}
