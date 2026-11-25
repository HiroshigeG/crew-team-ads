/** Provider noti al server (`/api/status` → `providers`): servono a mostrare
 *  etichette leggibili per le chiavi, senza elencare i provider a mano qui. Il
 *  server manda i NOMI delle variabili e lo stato, mai i valori. */
export interface ProviderInfo {
  id: string
  label: string
  key_env: string | null
  configured: boolean
  needed: boolean
  suggested: string[]
}

/** Ripiego per la modalità demo / server vecchio: le etichette storiche. */
const FALLBACK: Record<string, string> = {
  ANTHROPIC_API_KEY: 'Anthropic (Claude) — teste anthropic/*',
  GEMINI_API_KEY: 'Google Gemini — ricerca e visione',
  XAI_API_KEY: 'xAI (Grok) — analista social',
  FEATHERLESS_AI_API_KEY: 'Featherless — modelli open',
  OPENROUTER_API_KEY: 'OpenRouter — modelli open',
  VENICE_API_KEY: 'Venice — modelli uncensored/abliterated',
}

const labels = new Map<string, string>()

export function setProviders(list: ProviderInfo[]): void {
  labels.clear()
  for (const p of list) if (p.key_env) labels.set(p.key_env, p.label)
}

export function keyLabel(keyEnv: string): string {
  return labels.get(keyEnv) ?? FALLBACK[keyEnv] ?? keyEnv
}
