/**
 * Esporta campagna (Fase 5.8): Markdown scaricabile e vista di stampa per
 * il PDF (il PDF nasce dal dialogo di stampa del browser: zero dipendenze,
 * scelta dichiarata).
 */
import type { RoomState } from '../state/fold'
import { HEADS } from '../mocks/roster'

export interface ExportInput {
  campaignName: string
  brief: Record<string, string>
  decisions: string[]
  finalVersion: string | null
  state: RoomState
}

export function approvedSearches(state: RoomState) {
  return state.items.flatMap((it) =>
    it.kind === 'gate' && it.result?.status === 'approved'
      ? [{
          speaker: HEADS[it.gate.speaker]?.name ?? it.gate.speaker,
          query: it.result.final_query ?? it.gate.query,
          why: it.gate.why,
          digest: it.result.digest ?? '',
        }]
      : [],
  )
}

export function buildMarkdown(input: ExportInput): string {
  const lines: string[] = [`# ${input.campaignName}`, '']
  lines.push('## Brief', '')
  for (const [k, v] of Object.entries(input.brief)) {
    lines.push(`- **${k}**: ${v}`)
  }
  lines.push('', '## Decisioni prese', '')
  for (const d of input.decisions) lines.push(`- ${d}`)
  lines.push('', '## Versione finale', '')
  lines.push(input.finalVersion ?? '_Nessuna versione bloccata._')
  const searches = approvedSearches(input.state)
  lines.push('', '## Ricerche approvate e fonti', '')
  if (!searches.length) lines.push('_Nessuna ricerca approvata in sessione._')
  for (const s of searches) {
    lines.push(`### ${s.speaker}: \`${s.query}\``, '', `Perché: ${s.why}`, '')
    for (const row of s.digest.split('\n').filter(Boolean)) lines.push(row)
    lines.push('')
  }
  const routes = input.state.routes
  lines.push('---',
    `Turni Claude: ${routes.subscription} in abbonamento · ${routes.api} via API.`)
  return lines.join('\n')
}

export function downloadMarkdown(md: string, filename: string): void {
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** PDF via dialogo di stampa: vista pulita, poi il browser fa il resto. */
export function openPrintView(md: string, title: string): void {
  const w = window.open('', '_blank', 'width=820,height=900')
  if (!w) return
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const html = esc(md)
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/^- (.*)$/gm, '<li>$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/^---$/gm, '<hr>')
    .replace(/\n{2,}/g, '</p><p>')
  w.document.write(`<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>${esc(title)}</title>
<style>
  body { font: 14px/1.5 Georgia, 'Times New Roman', serif; color: #1a1a1a;
         max-width: 44rem; margin: 2.5rem auto; padding: 0 1.5rem; }
  h1 { font-size: 24px; } h2 { font-size: 18px; margin-top: 1.6em; }
  h3 { font-size: 15px; margin-top: 1.2em; }
  code { font: 12px ui-monospace, monospace; background: #f2f0ea;
         padding: 1px 4px; border-radius: 3px; }
  li { margin: 0.25em 0; } hr { border: 0; border-top: 1px solid #ccc; }
  @media print { body { margin: 0.5cm auto; } }
</style></head><body><p>${html}</p>
<script>window.onload = () => window.print()</script></body></html>`)
  w.document.close()
}
