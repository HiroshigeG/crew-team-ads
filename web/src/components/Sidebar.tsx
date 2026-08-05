import { useState } from 'react'
import { ChevronDown, Send } from 'lucide-react'
import { BLANK_CAMPAIGN, CAMPAIGN } from '../mocks/session'
import { useRoomActions } from '../lib/socket'
import { cn } from '../lib/cn'

/**
 * Testata della colonna del LAVORO (sinistra, 05/08): campagna + brief,
 * compatti — sotto ci vive la proposta (Workspace). La regia dei
 * partecipanti (roster, panchina, collab) è passata a destra (RoomPanel).
 */
function BriefField({
  label,
  value,
  placeholder,
  span2 = false,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  /** Campo largo (obiettivo, target): occupa tutta la riga della griglia. */
  span2?: boolean
  onChange: (v: string) => void
}) {
  return (
    <label className={cn('block', span2 && 'col-span-2')}>
      <span className="label-caps">{label}</span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={span2 && value.length > 40 ? 2 : 1}
        placeholder={placeholder}
        className="mt-1 w-full resize-none rounded-md border border-edge bg-raised px-2 py-1.5 text-[13.5px] leading-snug text-ink outline-none placeholder:text-faint focus:border-accent"
      />
    </label>
  )
}

export function Sidebar({
  demo = false,
}: {
  /** 05/08: i dati MERIDIA vivono solo in demo — la stanza vera parte vuota. */
  demo?: boolean
}) {
  const { sendDirector } = useRoomActions()
  const campaign = demo ? CAMPAIGN : BLANK_CAMPAIGN
  const [brief, setBrief] = useState({
    obiettivo: campaign.objective,
    budget: campaign.budget,
    target: campaign.target,
    kpi: campaign.kpi,
  })
  // Il brief serve all'inizio: dopo l'invio si richiude da solo — sotto c'è
  // la proposta, che è il vero lavoro della colonna (UX 05/08).
  const [briefOpen, setBriefOpen] = useState(true)
  const briefFilled = Object.values(brief).some((v) => v.trim())

  return (
    <div className="shrink-0">
      <div className="border-b border-edge px-4 py-3">
        <div className="flex items-baseline justify-between gap-2">
          <h1 className="min-w-0 truncate text-[16px] font-semibold leading-tight">
            {campaign.name}
          </h1>
          <span className="label-caps shrink-0">Campagna</span>
        </div>
        {campaign.brand && (
          <p className="mt-0.5 text-xs text-faint">{campaign.brand}</p>
        )}
      </div>

      <section className="border-b border-edge px-4 py-3">
        <button
          onClick={() => setBriefOpen((o) => !o)}
          aria-expanded={briefOpen}
          className="flex w-full items-center justify-between text-left"
        >
          <span className="label-caps">Brief</span>
          <span className="flex items-center gap-2">
            {!briefOpen && (
              <span className="max-w-[150px] truncate text-xs text-faint">
                {briefFilled ? brief.obiettivo || 'compilato' : 'da compilare'}
              </span>
            )}
            <ChevronDown
              className={cn(
                'size-3.5 text-faint transition-transform',
                briefOpen && 'rotate-180',
              )}
              aria-hidden
            />
          </span>
        </button>
        {briefOpen && (
          <div className="mt-3">
            {/* Griglia compatta (05/08): i campi corti dividono la riga. */}
            <div className="grid grid-cols-2 gap-x-2 gap-y-2.5">
              <BriefField
                label="Obiettivo"
                value={brief.obiettivo}
                placeholder="Cosa deve ottenere la campagna"
                span2
                onChange={(v) => setBrief({ ...brief, obiettivo: v })}
              />
              <BriefField
                label="Target"
                value={brief.target}
                placeholder="Chi vogliamo muovere"
                span2
                onChange={(v) => setBrief({ ...brief, target: v })}
              />
              <BriefField
                label="Budget"
                value={brief.budget}
                placeholder="es. 80.000 €"
                onChange={(v) => setBrief({ ...brief, budget: v })}
              />
              <BriefField
                label="KPI"
                value={brief.kpi}
                placeholder="Misura del successo"
                onChange={(v) => setBrief({ ...brief, kpi: v })}
              />
            </div>
            {/* Brief scritto a mano: apre la stanza senza bisogno di allegati. */}
            <button
              onClick={() => {
                const b = [
                  `PROJECT: ${brief.obiettivo}`,
                  `BUDGET: ${brief.budget}`,
                  `TARGET: ${brief.target}`,
                  `KPI: ${brief.kpi}`,
                ].join('\n')
                sendDirector(
                  `Ecco il brief della campagna. Stanza, reagite.\n\n${b}`,
                )
                setBriefOpen(false)   // il brief è partito: spazio alla proposta
              }}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-md bg-accent px-3 py-2 text-[13px] font-medium text-bg hover:opacity-90"
            >
              <Send className="size-3.5" aria-hidden />
              Manda il brief alla stanza
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
