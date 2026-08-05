import { useMemo, useState } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import { AnimatePresence, motion } from 'framer-motion'
import { KeyRound, PanelLeft, Unplug, X } from 'lucide-react'
import { foldEvents } from './state/fold'
import { CAMPAIGN } from './mocks/session'
import { RoomContext, useRoom } from './lib/socket'
import { Sidebar } from './components/Sidebar'
import { RoomPanel } from './components/RoomPanel'
import { Timeline } from './components/Timeline'
import { Workspace } from './components/Workspace'
import { PrivateChat } from './components/PrivateChat'
import { RosterEditor } from './components/RosterEditor'
import { SessionHistory } from './components/SessionHistory'
import { KeyGate } from './components/KeyGate'

/* Pannelli ridimensionabili: react-resizable-panels (MIT), la stessa base
   del componente `resizable` di shadcn/ui approvato in docs/recon/B-componenti.md. */

function ResizeBar() {
  return (
    <Separator className="w-px bg-edge transition-colors hover:bg-accent data-[separator=active]:bg-accent" />
  )
}

export default function App({
  demo,
  missingKeys,
}: {
  demo: boolean
  missingKeys: string[]
}) {
  const room = useRoom(demo)
  const [drawer, setDrawer] = useState(false)
  const [privateHead, setPrivateHead] = useState<string | null>(null)
  const [editingRoster, setEditingRoster] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [rosterRev, setRosterRev] = useState(0)
  // D22: teste in panchina. La UI ne è la fonte (niente replay del flusso) e
  // rispecchia al server con head_active; il server rifiuta di svuotare la stanza.
  const [disabled, setDisabled] = useState<Set<string>>(new Set())
  const toggleActive = (key: string) => {
    const active = disabled.has(key) // se ora è in panchina, il toggle la riattiva
    setDisabled((prev) => {
      const next = new Set(prev)
      if (active) next.delete(key)
      else next.add(key)
      return next
    })
    room.send({ type: 'head_active', key, active })
  }
  const state = useMemo(
    () => foldEvents(room.entries),
    // rosterRev: il roster è mutato in place — si ripiega per ridisegnare.
    [room.entries, rosterRev],
  )

  // D25: chiavi mancanti al primo accesso -> onboarding a schermo intero,
  // non un banner che rimanda all'editor di testo. Il caso "server non
  // raggiungibile" resta un banner: lì non c'è nessuno a cui POSTare.
  const realMissing = missingKeys.filter((k) => k.endsWith('_API_KEY'))
  if (!demo && realMissing.length > 0) {
    return <KeyGate missing={realMissing} />
  }

  const banner =
    missingKeys.length > 0 ? (
      <div className="flex items-center gap-2 border-b border-danger/40 bg-danger/10 px-4 py-2 text-[13px] text-danger">
        <KeyRound className="size-4 shrink-0" aria-hidden />
        <span>
          Server non raggiungibile: avvialo con{' '}
          <span className="font-mono">.venv/bin/uvicorn server.main:app --port 8000</span>{' '}
          e ricarica la pagina.
        </span>
      </div>
    ) : room.status === 'closed' ? (
      <div className="flex items-center gap-2 border-b border-danger/40 bg-danger/10 px-4 py-2 text-[13px] text-danger">
        <Unplug className="size-4 shrink-0" aria-hidden />
        <span>
          Connessione alla stanza persa. Il flusso eventi non ha replay: ricarica
          la pagina per aprire una nuova sessione.
        </span>
      </div>
    ) : null

  return (
    <RoomContext.Provider value={room}>
      <div className="flex h-full flex-col">
        {banner}

        {/* ─── Desktop: tre colonne ridimensionabili ─── */}
        <div className="hidden min-h-0 flex-1 lg:block">
          {/* Taglie numeriche = pixel (API v4): 280 e 340 come da specifica */}
          {/* 05/08: a sinistra il LAVORO (campagna+brief+proposta), al centro
              la conversazione, a destra la REGIA (stanza, panchina, collab). */}
          <Group orientation="horizontal" className="h-full">
            <Panel defaultSize={330} minSize={280} maxSize={460}>
              <div className="flex h-full flex-col overflow-y-auto bg-raised">
                <Sidebar demo={demo} />
                <Workspace state={state} demo={demo} />
              </div>
            </Panel>
            <ResizeBar />
            <Panel minSize={420}>
              <Timeline state={state} />
            </Panel>
            <ResizeBar />
            <Panel defaultSize={290} minSize={250} maxSize={400}>
              <RoomPanel
                state={state}
                onOpenPrivate={setPrivateHead}
                onEditRoster={() => setEditingRoster(true)}
                onOpenHistory={() => setHistoryOpen(true)}
                disabled={disabled}
                onToggleActive={toggleActive}
              />
            </Panel>
          </Group>
        </div>

        {/* ─── Mobile: sidebar a drawer, workspace in coda ─── */}
        <div className="flex min-h-0 flex-1 flex-col lg:hidden">
          <header className="flex shrink-0 items-center gap-3 border-b border-edge bg-raised px-3 py-2.5">
            <button
              onClick={() => setDrawer(true)}
              className="rounded-md p-1.5 text-dim hover:bg-lifted hover:text-ink"
              aria-label="Apri il pannello contesto"
            >
              <PanelLeft className="size-5" aria-hidden />
            </button>
            <h1 className="truncate text-[15px] font-semibold">
              {demo ? CAMPAIGN.name : 'ADV Room'}
            </h1>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="flex h-[78dvh] flex-col border-b border-edge">
              <Timeline state={state} />
            </div>
            <Sidebar demo={demo} />
            <Workspace state={state} demo={demo} />
          </div>

          <AnimatePresence>
            {drawer && (
              <>
                <motion.button
                  className="fixed inset-0 z-40 bg-bg/70"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setDrawer(false)}
                  aria-label="Chiudi il pannello"
                />
                <motion.div
                  className="fixed inset-y-0 left-0 z-50 w-[300px] max-w-[85vw] border-r border-edge"
                  initial={{ x: -320 }}
                  animate={{ x: 0 }}
                  exit={{ x: -320 }}
                  transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                >
                  <button
                    onClick={() => setDrawer(false)}
                    className="absolute right-2 top-3 z-10 rounded-md p-1.5 text-dim hover:bg-lifted"
                    aria-label="Chiudi"
                  >
                    <X className="size-4" aria-hidden />
                  </button>
                  <RoomPanel
                    state={state}
                    onOpenPrivate={(k) => {
                      setDrawer(false)
                      setPrivateHead(k)
                    }}
                    onEditRoster={() => {
                      setDrawer(false)
                      setEditingRoster(true)
                    }}
                    onOpenHistory={() => {
                      setDrawer(false)
                      setHistoryOpen(true)
                    }}
                    disabled={disabled}
                    onToggleActive={toggleActive}
                  />
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>

        {privateHead && (
          <PrivateChat
            headKey={privateHead}
            state={state}
            onClose={() => setPrivateHead(null)}
          />
        )}
        {editingRoster && (
          <RosterEditor
            onClose={() => setEditingRoster(false)}
            onApplied={() => setRosterRev((r) => r + 1)}
          />
        )}
        {historyOpen && <SessionHistory onClose={() => setHistoryOpen(false)} />}
      </div>
    </RoomContext.Provider>
  )
}
