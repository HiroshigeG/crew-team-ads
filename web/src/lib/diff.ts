/**
 * Diff a parole (LCS classico) per la Versione Finale (Fase 5.4):
 * abbastanza per testi di proposta, zero dipendenze.
 */
export interface DiffPart {
  text: string
  kind: 'same' | 'ins' | 'del'
}

export function wordDiff(before: string, after: string): DiffPart[] {
  const a = before.split(/\s+/).filter(Boolean)
  const b = after.split(/\s+/).filter(Boolean)
  const n = a.length
  const m = b.length
  // Tabella LCS (testi di proposta: dimensioni piccole, va benissimo O(n·m)).
  const L: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  )
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      L[i][j] = a[i] === b[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1])
    }
  }
  const parts: DiffPart[] = []
  const push = (kind: DiffPart['kind'], word: string) => {
    const last = parts[parts.length - 1]
    if (last && last.kind === kind) last.text += ` ${word}`
    else parts.push({ text: word, kind })
  }
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      push('same', a[i])
      i++
      j++
    } else if (L[i + 1][j] >= L[i][j + 1]) {
      push('del', a[i])
      i++
    } else {
      push('ins', b[j])
      j++
    }
  }
  while (i < n) push('del', a[i++])
  while (j < m) push('ins', b[j++])
  return parts
}
