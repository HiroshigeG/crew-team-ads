/** useMediaQuery: serve a montare UN layout solo (prima: due, nascosti col CSS). */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook } from '@testing-library/react'
import { useMediaQuery } from './useMediaQuery'

type Listener = () => void
function mockMatchMedia(initial: boolean) {
  let matches = initial
  const listeners = new Set<Listener>()
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    get matches() { return matches },
    media: query,
    addEventListener: (_: string, l: Listener) => listeners.add(l),
    removeEventListener: (_: string, l: Listener) => listeners.delete(l),
  })) as unknown as typeof window.matchMedia
  return (v: boolean) => { matches = v; listeners.forEach((l) => l()) }
}

afterEach(() => cleanup())

describe('useMediaQuery', () => {
  it('parte dal valore corrente', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useMediaQuery('(min-width: 1024px)'))
    expect(result.current).toBe(true)
  })
  it('si aggiorna quando la finestra cambia', () => {
    const set = mockMatchMedia(true)
    const { result } = renderHook(() => useMediaQuery('(min-width: 1024px)'))
    act(() => set(false))
    expect(result.current).toBe(false)
  })
})
