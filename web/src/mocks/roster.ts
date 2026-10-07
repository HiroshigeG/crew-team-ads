/**
 * Roster mock: stessa forma di roster.adv.json (Head.to_dict() del core).
 * Nove teste (D3/D16/D17/D19/D20). Colori e chiavi identici al file reale;
 * in produzione `applyRoster()` lo sostituisce col vero da /api/status, quindi
 * questo serve solo alla demo (?demo=1) e come default prima del mount.
 */

export interface Head {
  key: string
  name: string
  avatar: string
  color: string
  model_id: string
  persona: string
  /** Frase breve in italiano per la UI (card, chat privata); dal roster vero. */
  tagline?: string
  creativity: number
  effort?: string
}

export const ROSTER: Head[] = [
  {
    key: 'market_researcher',
    name: 'Market Researcher',
    avatar: '🔎',
    color: '#00afd7',
    model_id: 'gemini/gemini-3.1-pro-preview',
    persona: 'Mappa pubblico e campo competitivo. Evidenze, non sensazioni.',
    tagline: 'Maps the audience and the competitive field. Evidence first.',
    creativity: 2,
  },
  {
    key: 'creative_strategist',
    name: 'Creative Strategist',
    avatar: '🧠',
    color: '#af87ff',
    model_id: 'anthropic/claude-sonnet-5',
    persona: 'Trasforma la ricerca in due o tre angoli genuinamente diversi.',
    tagline: 'Turns research into two or three genuinely different angles.',
    creativity: 7,
  },
  {
    key: 'cd',
    name: 'Creative Director',
    avatar: '🎨',
    color: '#ff8700',
    model_id: 'anthropic/claude-opus-5',
    persona: 'Dalle verità alla direzione esecutiva: concept, mondo visivo.',
    tagline: 'Turns insight into direction: concept and visual world.',
    creativity: 5,
  },
  {
    key: 'copywriter',
    name: 'Copywriter',
    avatar: '✍️',
    color: '#ff5faf',
    model_id: 'featherless_ai/anthracite-org/magnum-v4-72b',
    persona: 'Il liquido della coppia: apre a caldo, voce, la riga che nessuno osa.',
    tagline: 'Writes the first lines: voice, rhythm, the bold option.',
    creativity: 7,
  },
  {
    key: 'social',
    name: 'Social & Precedent Analyst',
    avatar: '📡',
    color: '#5fff87',
    model_id: 'xai/grok-4.5',
    persona: 'Grammatica del genere e vita social. Bolla i cliché.',
    tagline: 'Knows the genre and the feeds. Flags the clichés.',
    creativity: 5,
  },
  {
    key: 'producer',
    name: 'Executive Producer',
    avatar: '🧭',
    color: '#d7af00',
    model_id: 'featherless_ai/NousResearch/Hermes-3-Llama-3.1-70B',
    persona: 'Tiene la stanza onesta, impacchetta il dossier. Mai sceglie.',
    tagline: 'Keeps the room honest and moving. Never picks the idea.',
    creativity: 7,
  },
  {
    key: 'dark_angel',
    name: 'Dark Angel',
    avatar: '🖤',
    color: '#c0304a',
    model_id: 'featherless_ai/EVA-UNIT-01/EVA-Qwen2.5-72B-v0.2',
    persona: 'Lo storyteller senza freni: la storia scomoda che nessuno pitcha.',
    tagline: 'The unfiltered storyteller: the uncomfortable pitch.',
    creativity: 9,
  },
  {
    key: 'copywriter_2',
    name: 'Copywriter 2',
    avatar: '🖋️',
    color: '#5f8fff',
    model_id: 'anthropic/claude-opus-4-8',
    persona: 'Il recipiente: giudica, verifica i claim, mano finale.',
    tagline: 'Judges the drafts, checks the claims, writes the final copy.',
    creativity: 7,
    effort: 'max',
  },
  {
    key: 'account_director',
    name: 'Account Director',
    avatar: '💼',
    color: '#af875f',
    model_id: 'featherless_ai/Qwen/Qwen2.5-72B-Instruct',
    persona: 'La voce del cliente: vendibile? difendibile? avvocato dell’idea.',
    tagline: 'The client\'s voice: sellable, defensible, on brief?',
    creativity: 3,
    effort: 'high',
  },
]

export const HEADS: Record<string, Head> = Object.fromEntries(
  ROSTER.map((h) => [h.key, h]),
)

/**
 * Sostituisce il roster mock con quello vero arrivato da /api/status.
 * Mutazione in place PRIMA del mount (vedi main.tsx): le import esistenti
 * di ROSTER/HEADS restano valide senza refactor.
 */
export function applyRoster(heads: Head[]): void {
  if (!heads?.length) return
  ROSTER.splice(0, ROSTER.length, ...heads)
  for (const k of Object.keys(HEADS)) delete HEADS[k]
  for (const h of heads) HEADS[h.key] = h
}

/** Whitelist modelli (da /api/status in produzione, default = la stessa
 *  VERIFIED_MODELS del core). */
export const MODELS: string[] = [
  'anthropic/claude-opus-5',
  'anthropic/claude-sonnet-5',
  'gemini/gemini-3.1-pro-preview',
  'xai/grok-4.5',
]

export function setModels(models: string[]): void {
  if (models?.length) MODELS.splice(0, MODELS.length, ...models)
}

export const EFFORTS = ['', 'low', 'medium', 'high', 'xhigh', 'max']

export const DIRECTOR = {
  key: 'director',
  name: 'Director',
  avatar: '🎬',
  color: '#e8e6f0',
}
