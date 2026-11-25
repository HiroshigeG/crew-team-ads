/** KeyGate: le etichette vengono dal server (registro dei provider), così un
 *  provider nuovo (Venice) compare senza toccare l'interfaccia. */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { KeyGate } from './KeyGate'
import { setProviders, keyLabel } from '../lib/providers'

afterEach(() => {
  cleanup()
  setProviders([])
})

describe('KeyGate: etichette dal registro dei provider', () => {
  it('mostra l\'etichetta mandata dal server per un provider nuovo', () => {
    setProviders([
      { id: 'venice', label: 'Venice — modelli uncensored', key_env: 'VENICE_API_KEY',
        configured: false, needed: true, suggested: [] },
    ])
    render(<KeyGate missing={['VENICE_API_KEY']} />)
    expect(screen.getByText('Venice — modelli uncensored')).toBeTruthy()
  })

  it('senza dati dal server ricade sulle etichette note, poi sul nome', () => {
    expect(keyLabel('GEMINI_API_KEY')).toMatch(/Gemini/)
    expect(keyLabel('QUALCOSA_API_KEY')).toBe('QUALCOSA_API_KEY')
  })

  it('un provider senza chiave (Ollama) non produce etichette', () => {
    setProviders([
      { id: 'ollama', label: 'Ollama — modelli locali', key_env: null,
        configured: true, needed: false, suggested: [] },
    ])
    expect(keyLabel('OLLAMA_API_KEY')).toBe('OLLAMA_API_KEY')
  })
})
