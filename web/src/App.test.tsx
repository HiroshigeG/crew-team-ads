/** Regressione del 25/11: App montava il layout desktop E quello mobile insieme
 *  (nascosto uno col CSS) → ogni pulsante e ogni stato esistevano due volte. */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import App from './App'

function setViewport(desktop: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: desktop,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
}

beforeAll(() => {
  // react-resizable-panels osserva le dimensioni: jsdom non ha ResizeObserver
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
  Element.prototype.scrollTo ??= () => {}
  Element.prototype.scrollIntoView ??= () => {}
})
afterEach(() => cleanup())

describe('App: un layout solo', () => {
  it('su desktop il brief esiste una volta sola', () => {
    setViewport(true)
    render(<App demo missingKeys={[]} />)
    expect(screen.getAllByRole('button', { name: /Manda il brief alla stanza/i })).toHaveLength(1)
  })

  it('su mobile il brief esiste una volta sola', () => {
    setViewport(false)
    render(<App demo missingKeys={[]} />)
    expect(screen.getAllByRole('button', { name: /Manda il brief alla stanza/i })).toHaveLength(1)
  })
})
