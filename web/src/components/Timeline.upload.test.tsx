/** Upload: più documenti e immagini in un solo invio (prima: un file alla volta,
 *  l'<input> non era `multiple` e `attached` era un oggetto singolo). */
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Timeline } from './Timeline'
import { RoomContext } from '../lib/socket'
import { foldEvents } from '../state/fold'

const sendDirector = vi.fn()
const send = vi.fn()

function mount() {
  return render(
    <RoomContext.Provider value={{ send, sendDirector, sendPrivate: () => {} }}>
      <Timeline state={foldEvents([])} />
    </RoomContext.Provider>,
  )
}

function mockUpload() {
  globalThis.fetch = vi.fn(async (_url: string, init: RequestInit) => {
    const f = (init.body as FormData).get('file') as File
    const isImage = f.type.startsWith('image/')
    return {
      ok: true,
      json: async () => ({
        filename: f.name,
        text: isImage ? '' : `TESTO(${f.name})`,
        is_image: isImage,
        image_id: isImage ? `img-${f.name}` : '',
      }),
    } as Response
  }) as unknown as typeof fetch
}

const file = (name: string, type = 'text/plain') => new File(['x'], name, { type })

beforeAll(() => {
  Element.prototype.scrollTo ??= () => {}
})
beforeEach(() => {
  vi.clearAllMocks()
  mockUpload()
})
afterEach(() => cleanup())

describe('Timeline: allegati multipli', () => {
  it("l'input accetta più file", () => {
    const { container } = mount()
    const input = container.querySelector('input[type=file]') as HTMLInputElement
    expect(input.multiple).toBe(true)
  })

  it('mostra un chip per ogni file caricato e se ne può togliere uno', async () => {
    const { container } = mount()
    const input = container.querySelector('input[type=file]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [file('guideline.pdf'), file('bene.md'), file('male.md')] },
    })
    await waitFor(() => expect(screen.getAllByLabelText(/Togli l'allegato/i)).toHaveLength(3))
    fireEvent.click(screen.getAllByLabelText(/Togli l'allegato/i)[1])
    expect(screen.getAllByLabelText(/Togli l'allegato/i)).toHaveLength(2)
    expect(screen.queryByText('bene.md')).toBeNull()
  })

  it('i documenti partono in UN messaggio con la nota; le immagini a parte', async () => {
    const { container } = mount()
    const input = container.querySelector('input[type=file]') as HTMLInputElement
    fireEvent.change(input, {
      target: {
        files: [file('guideline.pdf', 'application/pdf'), file('bene.md'), file('ad.png', 'image/png')],
      },
    })
    await waitFor(() => expect(screen.getAllByLabelText(/Togli l'allegato/i)).toHaveLength(3))
    fireEvent.change(screen.getByPlaceholderText(/Parla alla stanza/i), {
      target: { value: 'Ecco i nostri materiali.' },
    })
    fireEvent.keyDown(screen.getByPlaceholderText(/Parla alla stanza/i), { key: 'Enter' })

    const docMsgs = sendDirector.mock.calls.map((c) => String(c[0])).filter((t) => t.includes('Documento allegato'))
    expect(docMsgs).toHaveLength(1)                          // un solo messaggio per i documenti
    expect(docMsgs[0]).toContain('Ecco i nostri materiali.')
    expect(docMsgs[0]).toContain('TESTO(guideline.pdf)')
    expect(docMsgs[0]).toContain('TESTO(bene.md)')
    expect(send).toHaveBeenCalledWith({ type: 'study_image', image_id: 'img-ad.png', text: '' })
    // dopo l'invio gli allegati si svuotano
    expect(screen.queryAllByLabelText(/Togli l'allegato/i)).toHaveLength(0)
  })

  it('senza documenti la nota accompagna la prima immagine', async () => {
    const { container } = mount()
    const input = container.querySelector('input[type=file]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [file('a.png', 'image/png'), file('b.png', 'image/png')] },
    })
    await waitFor(() => expect(screen.getAllByLabelText(/Togli l'allegato/i)).toHaveLength(2))
    fireEvent.change(screen.getByPlaceholderText(/Parla alla stanza/i), {
      target: { value: 'Descrivete.' },
    })
    fireEvent.keyDown(screen.getByPlaceholderText(/Parla alla stanza/i), { key: 'Enter' })
    expect(send).toHaveBeenCalledWith({ type: 'study_image', image_id: 'img-a.png', text: 'Descrivete.' })
    expect(send).toHaveBeenCalledWith({ type: 'study_image', image_id: 'img-b.png', text: '' })
  })

  it('oltre 8 allegati si ferma con un messaggio chiaro', async () => {
    const { container } = mount()
    const input = container.querySelector('input[type=file]') as HTMLInputElement
    const many = Array.from({ length: 10 }, (_, i) => file(`d${i}.md`))
    fireEvent.change(input, { target: { files: many } })
    await waitFor(() => expect(screen.getAllByLabelText(/Togli l'allegato/i)).toHaveLength(8))
    expect(screen.getByText(/massimo 8 allegati/i)).toBeTruthy()
  })
})
