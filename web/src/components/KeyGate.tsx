import { useState } from 'react'
import { KeyRound, LoaderCircle } from 'lucide-react'

/**
 * Onboarding chiavi (D25): al primo accesso, se mancano chiavi, la stanza le
 * chiede qui invece di rimandare all'editor di testo. Le chiavi viaggiano solo
 * verso il server locale (localhost), che le scrive nel `.env` gitignorato:
 * mai nel repo, mai rimandate indietro, mai loggate in valore.
 */
const KEY_LABEL: Record<string, string> = {
  ANTHROPIC_API_KEY: 'Anthropic (Claude) — teste anthropic/*',
  GEMINI_API_KEY: 'Google Gemini — ricerca e visione',
  XAI_API_KEY: 'xAI (Grok) — analista social',
  FEATHERLESS_AI_API_KEY: 'Featherless — modelli open (facoltativa)',
  OPENROUTER_API_KEY: 'OpenRouter — modelli open (facoltativa)',
}

export function KeyGate({ missing }: { missing: string[] }) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const filled = missing.filter((k) => (values[k] ?? '').trim())

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const payload = Object.fromEntries(
        filled.map((k) => [k, values[k].trim()]),
      )
      const res = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      // Ricarica: main.tsx rilegge /api/status e la stanza parte pulita.
      location.reload()
    } catch (e) {
      setBusy(false)
      setError(
        `Salvataggio fallito (${String(e)}). Alternativa manuale: copia ` +
          '.env.example in .env accanto al server e incolla lì le chiavi.',
      )
    }
  }

  return (
    <div className="grid min-h-full place-items-center px-4 py-10">
      <div className="w-full max-w-md rounded-xl border border-edge bg-raised p-6">
        <div className="flex items-center gap-2.5">
          <KeyRound className="size-5 text-accent" aria-hidden />
          <h1 className="text-[17px] font-semibold">Colleghiamo la stanza</h1>
        </div>
        <p className="mt-2 text-[13.5px] leading-relaxed text-dim">
          Prima sessione: servono le chiavi API delle famiglie di modelli.
          Restano <strong>solo sul tuo computer</strong> (file{' '}
          <span className="font-mono text-[12.5px]">.env</span> locale,
          escluso da git) — non entrano mai nel codice né in un repo.
        </p>
        <div className="mt-5 space-y-3.5">
          {missing.map((k) => (
            <label key={k} className="block">
              <span className="label-caps">{KEY_LABEL[k] ?? k}</span>
              <input
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={values[k] ?? ''}
                onChange={(e) =>
                  setValues((v) => ({ ...v, [k]: e.target.value }))
                }
                placeholder={k}
                className="mt-1 w-full rounded-md border border-edge bg-bg px-3 py-2 font-mono text-[13px] text-ink outline-none placeholder:text-faint focus:border-accent"
              />
            </label>
          ))}
        </div>
        {error && (
          <p className="mt-3 text-[13px] leading-snug text-danger">{error}</p>
        )}
        <button
          onClick={submit}
          disabled={busy || filled.length === 0}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-md bg-accent px-3 py-2.5 text-[13.5px] font-medium text-bg hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <KeyRound className="size-4" aria-hidden />
          )}
          {busy
            ? 'Collego…'
            : filled.length === missing.length
              ? 'Collega e apri la stanza'
              : `Collega ${filled.length}/${missing.length} chiavi`}
        </button>
        <p className="mt-3 text-[12px] leading-snug text-faint">
          Puoi salvarne anche solo una parte: le teste senza chiave restano
          segnalate finché non completi.
        </p>
      </div>
    </div>
  )
}
