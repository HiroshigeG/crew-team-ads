import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { applyRoster, setModels } from './mocks/roster'

const DEMO = new URLSearchParams(location.search).has('demo')

async function boot() {
  let missingKeys: string[] = []
  if (!DEMO) {
    // missing_keys() all'avvio: se manca una chiave la UI lo dice in chiaro
    // invece di far fallire il primo turno (spec Fase 3).
    try {
      const res = await fetch('/api/status')
      const status = await res.json()
      missingKeys = status.missing_keys ?? []
      applyRoster(status.roster ?? [])
      setModels(status.models ?? [])
    } catch {
      missingKeys = ['server non raggiungibile']
    }
  }
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App demo={DEMO} missingKeys={missingKeys} />
    </StrictMode>,
  )
}

void boot()
