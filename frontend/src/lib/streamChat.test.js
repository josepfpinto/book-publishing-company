import { describe, it, expect, vi, beforeEach } from 'vitest'
import { streamChat } from './streamChat.js'

/** Build a ReadableStream from an array of string chunks. */
function makeStream(chunks) {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    },
  })
}

/** Build a minimal fetch-compatible Response from chunks. */
function mockResponse(chunks, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    body: makeStream(chunks).pipeThrough(new TextEncoderStream()),
  }
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('streamChat — partial-frame buffer pattern', () => {
  it('correctly collects tokens when a frame is split across two chunks', async () => {
    // The frame boundary \n\n arrives in the second chunk
    const chunks = [
      'event: token\ndata: {"token":"He', // frame starts — no closing \n\n yet
      'llo"}\n\nevent: done\ndata: {}\n\n',  // frame closes + done frame
    ]
    global.fetch = vi.fn().mockResolvedValue(mockResponse(chunks))

    const tokens = []
    const errors = []
    let doneFired = false

    await streamChat({
      bookId: 'little_women',
      message: 'test',
      history: [],
      onToken: (t) => tokens.push(t),
      onSources: vi.fn(),
      onError: (e) => errors.push(e),
      onDone: () => { doneFired = true },
    })

    expect(errors).toHaveLength(0)
    expect(tokens).toEqual(['Hello'])
    expect(doneFired).toBe(true)
  })

  it('does not throw on a half-received data: line', async () => {
    // Chunk 1 ends mid-data-line (no \n\n yet)
    const chunks = [
      'event: token\ndata: {"to',
      'ken":"World"}\n\n',
    ]
    global.fetch = vi.fn().mockResolvedValue(mockResponse(chunks))

    const tokens = []
    await streamChat({
      bookId: 'both',
      message: 'test',
      history: [],
      onToken: (t) => tokens.push(t),
      onSources: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    })

    expect(tokens).toEqual(['World'])
  })

  it('delivers multiple complete frames in a single chunk', async () => {
    const frame1 = 'event: token\ndata: {"token":"A"}\n\n'
    const frame2 = 'event: token\ndata: {"token":"B"}\n\n'
    const frame3 = 'event: sources\ndata: {"sources":[{"id":1}]}\n\n'

    global.fetch = vi.fn().mockResolvedValue(mockResponse([frame1 + frame2 + frame3]))

    const tokens = []
    let sources = null
    await streamChat({
      bookId: 'pride_prejudice',
      message: 'test',
      history: [],
      onToken: (t) => tokens.push(t),
      onSources: (s) => { sources = s },
      onError: vi.fn(),
      onDone: vi.fn(),
    })

    expect(tokens).toEqual(['A', 'B'])
    expect(sources).toEqual([{ id: 1 }])
  })
})

describe('streamChat — AbortController cancellation', () => {
  it('cancels cleanly without throwing an uncaught rejection', async () => {
    const controller = new AbortController()

    // Provide a stream that never closes so abort must do the work
    const neverEnding = new ReadableStream({
      start() { /* intentionally never closed */ },
    })

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: neverEnding.pipeThrough(new TextEncoderStream()),
    })

    const errorSpy = vi.fn()
    const doneSpy  = vi.fn()

    const promise = streamChat({
      bookId: 'little_women',
      message: 'test',
      history: [],
      onToken: vi.fn(),
      onSources: vi.fn(),
      onError: errorSpy,
      onDone: doneSpy,
      signal: controller.signal,
    })

    // Abort mid-stream
    controller.abort()

    await expect(promise).resolves.toBeUndefined()
    // AbortError must NOT propagate as onError
    expect(errorSpy).not.toHaveBeenCalled()
    expect(doneSpy).not.toHaveBeenCalled()
  })

  it('aborts before fetch resolves without onError being called', async () => {
    const controller = new AbortController()
    controller.abort() // abort before fetch even starts

    const abortErr = new DOMException('The user aborted a request.', 'AbortError')
    global.fetch = vi.fn().mockRejectedValue(abortErr)

    const errorSpy = vi.fn()
    await streamChat({
      bookId: 'both',
      message: 'test',
      history: [],
      onToken: vi.fn(),
      onSources: vi.fn(),
      onError: errorSpy,
      onDone: vi.fn(),
      signal: controller.signal,
    })

    expect(errorSpy).not.toHaveBeenCalled()
  })
})

describe('streamChat — untyped frame default dispatch', () => {
  it('dispatches onToken via field presence when no event: line is present', async () => {
    // Backend omits the "event: token" line; frame has only "data: {...}"
    const frame = 'data: {"token":"Untyped"}\n\n'
    global.fetch = vi.fn().mockResolvedValue(mockResponse([frame]))

    const tokens = []
    await streamChat({
      bookId: 'both',
      message: 'test',
      history: [],
      onToken: (t) => tokens.push(t),
      onSources: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    })

    expect(tokens).toEqual(['Untyped'])
  })
})

describe('streamChat — HTTP error handling', () => {
  it('calls onError on non-2xx response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, body: makeStream([]) })

    const errorSpy = vi.fn()
    await streamChat({
      bookId: 'both',
      message: 'test',
      history: [],
      onToken: vi.fn(),
      onSources: vi.fn(),
      onError: errorSpy,
      onDone: vi.fn(),
    })

    expect(errorSpy).toHaveBeenCalledWith('HTTP 500')
  })
})
