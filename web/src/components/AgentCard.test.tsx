/** Stati sulla card agente (Fase 6), `error` incluso: motivo leggibile. */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentCard } from './AgentCard'
import type { Head } from '../mocks/roster'

const HEAD: Head = {
  key: 'cd', name: 'Creative Director', avatar: '🎨', color: '#ff8700',
  model_id: 'anthropic/claude-opus-5', persona: 'x', creativity: 7,
  tagline: 'Dalle verità alla direzione esecutiva.',
}

describe('AgentCard', () => {
  it.each([
    ['thinking', 'sta pensando'],
    ['speaking', 'sta scrivendo'],
    ['searching', 'sta cercando'],
    ['waiting_approval', 'aspetta il tuo ok'],
  ] as const)('stato %s → «%s»', (state, label) => {
    render(<AgentCard head={HEAD} live={{ state, detail: null }} />)
    expect(screen.getByText(label)).toBeTruthy()
  })

  it('a riposo la card è compatta: nessuna riga di stato (05/08)', () => {
    // Con 9 teste la colonna deve stare a video: "in ascolto" non si
    // stampa più — lo stato compare solo quando la testa fa qualcosa.
    render(<AgentCard head={HEAD} live={{ state: 'idle', detail: null }} />)
    expect(screen.queryByText('in ascolto')).toBeNull()
  })

  it('error mostra «non disponibile» E il motivo leggibile', () => {
    render(
      <AgentCard
        head={HEAD}
        live={{ state: 'error', detail: 'claude CLI oltre il tempo massimo' }}
      />,
    )
    expect(screen.getByText('non disponibile')).toBeTruthy()
    expect(screen.getByText(/oltre il tempo massimo/)).toBeTruthy()
  })

  it('la barra creatività dichiara il livello', () => {
    render(<AgentCard head={HEAD} />)
    expect(screen.getByLabelText('Creatività 7 su 10')).toBeTruthy()
  })

  it('la tagline è visibile sulla card (scelta UX 07/10)', () => {
    render(<AgentCard head={HEAD} live={{ state: 'idle', detail: null }} />)
    expect(screen.getByText('Dalle verità alla direzione esecutiva.')).toBeTruthy()
  })

  it('senza tagline la card resta com’era: nessuna riga vuota', () => {
    const { container } = render(
      <AgentCard head={{ ...HEAD, tagline: undefined }} live={{ state: 'idle', detail: null }} />,
    )
    expect(container.textContent).not.toContain('undefined')
    expect(screen.queryByText('Dalle verità alla direzione esecutiva.')).toBeNull()
  })
})
