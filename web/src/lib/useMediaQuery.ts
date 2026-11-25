import { useCallback, useSyncExternalStore } from 'react'

/** `true` se la media query combacia ora, e si aggiorna da sola. Serve a montare
 *  UN layout solo (desktop o mobile): montarli entrambi e nasconderne uno col
 *  CSS duplicava ogni componente con il suo stato, i suoi effetti e i suoi
 *  pulsanti (bug del 25/11: brief doppio, «Approva» nascosto cliccabile). */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mql = window.matchMedia(query)
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    },
    [query],
  )
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => false,
  )
}
