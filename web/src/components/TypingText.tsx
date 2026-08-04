import { useEffect, useState } from 'react'

/**
 * Rivelazione per parola del testo in streaming, con caret. In Fase 3 il
 * testo cresce da solo coi turn_token: qui simuliamo la stessa resa.
 */
export function TypingText({ text }: { text: string }) {
  const words = text.split(' ')
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (count >= words.length) return
    const id = setTimeout(() => setCount((c) => c + 1), 90)
    return () => clearTimeout(id)
  }, [count, words.length])

  return (
    <span>
      {words.slice(0, count).join(' ')}
      <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[3px] animate-pulse rounded-sm bg-accent" />
    </span>
  )
}
