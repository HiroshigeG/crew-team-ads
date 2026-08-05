import { useState } from 'react'
import {
  Check,
  Eye,
  EyeOff,
  FileText,
  Lock,
  Pencil,
  Printer,
  RefreshCw,
  Undo2,
  X,
} from 'lucide-react'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'
import { wordDiff } from '../lib/diff'
import { buildMarkdown, downloadMarkdown, openPrintView } from '../lib/export'
import { BLANK_CAMPAIGN, CAMPAIGN, DECISIONS_LOG } from '../mocks/session'
import type { RoomState } from '../state/fold'

const BUDGET_SPLIT = [
  { label: 'Video social (single take)', pct: 45 },
  { label: 'OOH golden hour', pct: 25 },
  { label: 'Creator & bar takeover', pct: 20 },
  { label: 'Eventi lancio', pct: 10 },
]

const RISKS = [
  'Territorio “sober curious” affollato nel H2 2026: serve distintività di forma, non solo di messaggio.',
  'La meccanica “memoria” ha precedenti recenti negli spirits: vietato il formato montage.',
]

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="border-b border-edge px-4 py-4">
      <p className="label-caps pb-2">{title}</p>
      {children}
    </section>
  )
}

/** Il testo che viene bloccato come versione: headline + supporto + body
 *  (le parti vuote si saltano — la stanza vera parte senza proposta). */
function composeVersion(p: { headline: string; support: string; body: string }) {
  return [p.headline, p.support && `Supporto: ${p.support}`, p.body]
    .filter(Boolean)
    .join('\n')
}

export function Workspace({
  state,
  demo = false,
}: {
  state: RoomState
  /** 05/08: la vetrina MERIDIA vive solo in demo — la stanza vera parte vuota. */
  demo?: boolean
}) {
  const campaign = demo ? CAMPAIGN : BLANK_CAMPAIGN
  const [proposal, setProposal] = useState(
    demo
      ? {
          headline: '«Ricordati la serata.»',
          support: '«La sera comincia lucida.»',
          body: 'Quattro parole che sono un brindisi e una sfida. Mai spiegare la linea, mai la parola «senza»: il prodotto non si scusa.',
        }
      : { headline: '', support: '', body: '' },
  )
  const hasProposal = Boolean(
    proposal.headline.trim() || proposal.support.trim() || proposal.body.trim(),
  )
  const [versions, setVersions] = useState<string[]>([])
  const [showDiff, setShowDiff] = useState(true)
  const final = versions.length > 0
  const latest = versions[versions.length - 1] ?? null
  const previous = versions.length > 1 ? versions[versions.length - 2] : null

  const exportInput = {
    campaignName: campaign.name,
    brief: {
      Obiettivo: campaign.objective,
      Budget: campaign.budget,
      Target: campaign.target,
      KPI: campaign.kpi,
    },
    decisions: demo ? DECISIONS_LOG : [],
    finalVersion: latest,
    state,
  }
  const exportSlug =
    campaign.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') ||
    'campagna'

  return (
    <aside className="flex h-full flex-col overflow-y-auto bg-raised">
      <div className="border-b border-edge px-4 py-4">
        <p className="label-caps">Proposta in lavorazione</p>
        {demo ? (
          <>
            <h2 className="mt-1 text-lg font-semibold leading-tight">
              La lucidità è il nuovo lusso
            </h2>
            <p className="mt-0.5 text-xs text-faint">Angolo 2 · scelto alle 18:06</p>
          </>
        ) : (
          <>
            <h2
              className={cn(
                'mt-1 text-lg font-semibold leading-tight',
                !hasProposal && 'text-faint',
              )}
            >
              {proposal.headline || 'Ancora niente sul tavolo'}
            </h2>
            <p className="mt-0.5 text-xs text-faint">
              Si costruisce qui sotto («Modifica») quando la stanza converge.
            </p>
          </>
        )}
      </div>

      {demo && (
        <Section title="Concept">
          <p className="text-[13.5px] leading-relaxed text-dim">
            In un mondo che si anestetizza per reggere, restare lucidi è il vero
            status symbol. MERIDIA è il drink di chi vuole ricordarsi la serata:
            golden hour nitida, il bicchiere a fuoco, un solo punto fermo in una
            stanza che si muove.
          </p>
        </Section>
      )}

      {hasProposal && (
        <Section title="Headline e copy">
          {proposal.headline && (
            <p className="text-[17px] font-semibold leading-snug">{proposal.headline}</p>
          )}
          {proposal.support && (
            <p className="mt-1 text-[13px] text-dim">Supporto pack e POS: {proposal.support}</p>
          )}
          {proposal.body && (
            <p className="mt-2 text-[13px] leading-relaxed text-faint">
              Body: {proposal.body}
            </p>
          )}
        </Section>
      )}

      {demo && (
        <Section title="Canali e budget · 180.000 €">
          <ul className="space-y-2.5">
            {BUDGET_SPLIT.map((row) => (
              <li key={row.label}>
                <div className="flex items-baseline justify-between gap-2 text-[13px]">
                  <span className="text-dim">{row.label}</span>
                  <span className="tnum font-medium">{row.pct}%</span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-lifted">
                  <div
                    className="h-full rounded-full bg-accent/70"
                    style={{ width: `${row.pct}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {demo && (
        <Section title="Stima e rischi">
          <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[13px]">
            <div>
              <dt className="text-faint">Reach stimata</dt>
              <dd className="tnum font-medium">4,2 M</dd>
            </div>
            <div>
              <dt className="text-faint">Trial attesi</dt>
              <dd className="tnum font-medium">38-46 mila</dd>
            </div>
          </dl>
          <ul className="mt-3 space-y-2">
            {RISKS.map((r) => (
              <li key={r} className="flex gap-2 text-[12.5px] leading-snug text-dim">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-warn" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <ProposalGate
        canApprove={hasProposal}
        onApprove={() => setVersions((v) => [...v, composeVersion(proposal)])}
        onEdit={(text) => setProposal((p) => ({ ...p, body: text }))}
      />

      <section className="mt-auto px-4 py-4">
        <div className="rounded-lg border border-edge bg-bg px-3 py-3">
          <div className="flex items-center justify-between">
            <p className="label-caps flex items-center gap-1.5">
              <Lock className="size-3" aria-hidden /> Versione finale
              {versions.length > 0 && (
                <span className="tnum normal-case tracking-normal">
                  · v{versions.length}
                </span>
              )}
            </p>
            {previous && (
              <button
                onClick={() => setShowDiff((d) => !d)}
                className="flex items-center gap-1 text-[11.5px] text-dim hover:text-ink"
                title="Evidenzia cosa è cambiato rispetto alla versione precedente"
              >
                {showDiff ? <EyeOff className="size-3" aria-hidden /> : <Eye className="size-3" aria-hidden />}
                differenze
              </button>
            )}
          </div>

          {latest ? (
            <div className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed">
              {previous && showDiff ? (
                wordDiff(previous, latest).map((part, i) =>
                  part.kind === 'same' ? (
                    <span key={i}>{part.text} </span>
                  ) : part.kind === 'ins' ? (
                    <span key={i} className="rounded bg-ok/20 px-0.5 text-ok">
                      {part.text}{' '}
                    </span>
                  ) : (
                    <span key={i} className="rounded bg-danger/10 px-0.5 text-danger/80 line-through">
                      {part.text}{' '}
                    </span>
                  ),
                )
              ) : (
                latest
              )}
            </div>
          ) : (
            <p className="mt-2 text-[13px] text-dim">
              Nessuna versione bloccata: approva la proposta qui sopra per
              firmarla.
            </p>
          )}

          <div className="mt-3 grid grid-cols-2 gap-2">
            <button
              className={cn(
                'flex items-center justify-center gap-1.5 rounded-md px-2 py-2 text-[13px] font-medium',
                final ? 'bg-accent text-bg hover:opacity-90' : 'bg-lifted text-faint',
              )}
              disabled={!final}
              onClick={() =>
                downloadMarkdown(buildMarkdown(exportInput), `${exportSlug}.md`)
              }
              title="Scarica il dossier in Markdown"
            >
              <FileText className="size-3.5" aria-hidden />
              Markdown
            </button>
            <button
              className={cn(
                'flex items-center justify-center gap-1.5 rounded-md px-2 py-2 text-[13px] font-medium',
                final ? 'bg-lifted text-ink hover:bg-hover' : 'bg-lifted text-faint',
              )}
              disabled={!final}
              onClick={() => openPrintView(buildMarkdown(exportInput), campaign.name)}
              title="Vista di stampa: il PDF nasce dal dialogo del browser"
            >
              <Printer className="size-3.5" aria-hidden />
              PDF
            </button>
          </div>
        </div>
      </section>
    </aside>
  )
}

/**
 * HITL sulle proposte (Fase 4): quattro azioni grandi; «Modifica» aggiorna il
 * body della proposta E entra nel transcript come intervento del Director.
 * Riapribile: ogni nuova approvazione crea una versione (e il diff, Fase 5.4).
 */
function ProposalGate({
  canApprove = true,
  onApprove,
  onEdit,
}: {
  /** Senza una proposta sul tavolo non c'è niente da firmare (stanza vuota). */
  canApprove?: boolean
  onApprove: () => void
  onEdit: (text: string) => void
}) {
  const { sendDirector } = useRoomActions()
  const [decision, setDecision] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [edit, setEdit] = useState('')

  const big =
    'flex items-center justify-center gap-2 rounded-md px-3 py-2.5 text-[13.5px] font-medium'

  if (decision)
    return (
      <section className="px-4 py-4">
        <div className="flex items-center justify-between gap-2 rounded-lg border border-edge px-3 py-3 text-[13px] text-dim">
          <span>
            {decision === 'approve' && 'Proposta approvata e bloccata come versione.'}
            {decision === 'edit' && 'Modifica applicata e inviata alla stanza.'}
            {decision === 'alt' && 'Richieste alternative: la stanza ci lavora.'}
            {decision === 'reject' && 'Proposta rifiutata: la stanza è stata informata.'}
          </span>
          <button
            onClick={() => setDecision(null)}
            className="flex shrink-0 items-center gap-1 text-[12px] text-faint hover:text-ink"
            title="Riapri la decisione (una nuova approvazione crea una nuova versione)"
          >
            <Undo2 className="size-3.5" aria-hidden />
            riapri
          </button>
        </div>
      </section>
    )

  return (
    <section className="px-4 py-4">
      <div className="rounded-lg border border-warn/60 bg-warn/5 px-3 py-3">
        <p className="text-[14px] font-medium">
          Approvi questa proposta come direzione della campagna?
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button
            className={cn(
              big,
              canApprove
                ? 'bg-ok/15 text-ok hover:bg-ok/25'
                : 'cursor-not-allowed bg-lifted text-faint',
            )}
            disabled={!canApprove}
            title={
              canApprove
                ? undefined
                : 'Niente da firmare: scrivi la proposta con «Modifica»'
            }
            onClick={() => {
              onApprove()
              setDecision('approve')
            }}
          >
            <Check className="size-4" aria-hidden /> Approva
          </button>
          <button
            className={cn(big, 'bg-lifted text-dim hover:bg-hover hover:text-ink')}
            onClick={() => setEditing((e) => !e)}
          >
            <Pencil className="size-4" aria-hidden /> Modifica
          </button>
          <button
            className={cn(big, 'bg-lifted text-dim hover:bg-hover hover:text-ink')}
            onClick={() => {
              sendDirector(
                'Sulla proposta corrente: voglio due alternative genuinamente diverse, non variazioni. Strategist apre, la stanza segue.',
              )
              setDecision('alt')
            }}
          >
            <RefreshCw className="size-4" aria-hidden /> Alternative
          </button>
          <button
            className={cn(big, 'bg-danger/10 text-danger hover:bg-danger/20')}
            onClick={() => {
              sendDirector(
                'La proposta corrente non mi convince: si riparte. Ditemi in una riga a testa cosa salvereste e cosa buttereste.',
              )
              setDecision('reject')
            }}
          >
            <X className="size-4" aria-hidden /> Rifiuta
          </button>
        </div>
        {editing && (
          <div className="mt-3">
            <textarea
              value={edit}
              onChange={(e) => setEdit(e.target.value)}
              rows={3}
              autoFocus
              placeholder="Il nuovo body della proposta (sostituisce quello in card ed entra nel transcript come tuo intervento)…"
              className="w-full resize-none rounded-md border border-accent bg-raised px-2.5 py-2 text-[13.5px] leading-snug outline-none placeholder:text-faint"
            />
            <button
              className={cn(
                big,
                'mt-2 w-full',
                edit.trim() ? 'bg-accent text-bg hover:opacity-90' : 'bg-lifted text-faint',
              )}
              disabled={!edit.trim()}
              onClick={() => {
                onEdit(edit.trim())
                sendDirector(`Modifica del Director alla proposta: ${edit.trim()}`)
                setDecision('edit')
              }}
            >
              Applica e invia la modifica alla stanza
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
