/**
 * streamChat — POST /api/chat and consume the SSE response body.
 *
 * SSE frames are delimited by \n\n.  Network chunks may arrive mid-frame,
 * so we accumulate a buffer and split on \n\n, keeping the incomplete tail
 * in the buffer (the pop() partial-frame pattern).
 *
 * @param {object} opts
 * @param {string}   opts.bookId    — "little_women" | "pride_prejudice" | "both"
 * @param {string}   opts.message   — user's question
 * @param {Array}    opts.history   — prior conversation turns [{ role, content }, ...]
 * @param {Function} opts.onToken   — called with each text token string
 * @param {Function} opts.onSources — called once with the sources array
 * @param {Function} opts.onError   — called with an error message string
 * @param {Function} opts.onDone    — called when the stream closes cleanly
 * @param {AbortSignal} [opts.signal] — optional AbortController signal
 */
export async function streamChat({
  bookId,
  message,
  history = [],
  onToken,
  onSources,
  onError,
  onDone,
  signal,
}) {
  let response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: bookId, message, history }),
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') return
    onError(err.message ?? 'Network error')
    return
  }

  if (!response.ok) {
    onError(`HTTP ${response.status}`)
    return
  }

  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader()

  // Wrap the abort signal so we can race it against reader.read()
  // when the underlying fetch stream doesn't self-abort (e.g. in tests).
  const abortPromise = signal
    ? new Promise((_, reject) => {
        if (signal.aborted) {
          reject(new DOMException('Aborted', 'AbortError'))
        } else {
          signal.addEventListener(
            'abort',
            () => reject(new DOMException('Aborted', 'AbortError')),
            { once: true },
          )
        }
      })
    : null

  let buffer = ''

  try {
    while (true) {
      const { done, value } = await (abortPromise
        ? Promise.race([reader.read(), abortPromise])
        : reader.read())
      if (done) break

      buffer += value

      // Split on SSE frame delimiter; last element may be partial — keep it.
      const frames = buffer.split('\n\n')
      buffer = frames.pop() // incomplete tail stays in buffer

      for (const frame of frames) {
        if (!frame.trim()) continue
        parseFrame(frame, { onToken, onSources, onError })
      }
    }

    // Flush any remaining complete frame at stream end
    if (buffer.trim()) {
      parseFrame(buffer, { onToken, onSources, onError })
    }

    onDone()
  } catch (err) {
    if (err.name === 'AbortError') return
    onError(err.message ?? 'Stream read error')
  } finally {
    reader.releaseLock()
  }
}

/**
 * Parse a single SSE frame (text between two \n\n delimiters).
 * A frame may contain multiple "data: ..." lines; we join them.
 */
function parseFrame(frame, { onToken, onSources, onError }) {
  let eventType = null
  const dataLines = []

  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) {
      eventType = line.slice('event: '.length).trim()
    } else if (line.startsWith('data: ')) {
      dataLines.push(line.slice('data: '.length))
    }
  }

  if (!dataLines.length) return

  const rawData = dataLines.join('\n')

  let parsed
  try {
    parsed = JSON.parse(rawData)
  } catch {
    // Bare string tokens (no JSON wrapping) — treat as token
    onToken(rawData)
    return
  }

  switch (eventType) {
    case 'token':
      onToken(parsed.token ?? parsed)
      break
    case 'sources':
      onSources(parsed.sources ?? parsed)
      break
    case 'error':
      onError(parsed.message ?? String(parsed))
      break
    case 'done':
      // onDone is called by the outer loop after stream closes
      break
    default:
      // Untyped frame — fall back by field presence
      if (parsed.token !== undefined) onToken(parsed.token)
      else if (parsed.sources !== undefined) onSources(parsed.sources)
      else if (parsed.message !== undefined) onError(parsed.message)
  }
}
