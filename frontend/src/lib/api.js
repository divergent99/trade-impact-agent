const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Streams POST /analyze/stream via fetch + manual SSE parsing, since the
 * native EventSource API can't send a POST body.
 *
 * The SSE spec allows \n, \r, or \r\n as line endings — some stacks (notably
 * uvicorn on Windows) send \r\n. We normalize to \n before splitting on the
 * blank-line event boundary, otherwise events silently never parse.
 *
 * callbacks: { onProgress(msg), onReport(report), onDone(), onError(err) }
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function streamAnalysis(team, tradeDescription, callbacks) {
  const controller = new AbortController()

  function processChunk(chunk) {
    const lines = chunk.split('\n').filter((l) => !l.startsWith(':'))
    let event = 'message'
    let data = ''
    for (const line of lines) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      if (line.startsWith('data:')) data += line.slice(5).trim()
    }
    if (!data) return

    if (event === 'progress') {
      const parsed = JSON.parse(data)
      callbacks.onProgress?.(parsed.message)
    } else if (event === 'players') {
      callbacks.onPlayers?.(JSON.parse(data))
    } else if (event === 'sources') {
      callbacks.onSources?.(JSON.parse(data))
    } else if (event === 'report') {
      callbacks.onReport?.(JSON.parse(data))
    } else if (event === 'done') {
      callbacks.onDone?.()
    }
  }

  ;(async () => {
    try {
      const res = await fetch(`${API_URL}/analyze/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ team, trade_description: tradeDescription }),
        signal: controller.signal,
      })

      if (!res.ok || !res.body) {
        throw new Error(`Request failed (${res.status})`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        // normalize \r\n -> \n so the \n\n split below actually matches,
        // regardless of which line ending the server used
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() // keep the last (possibly incomplete) chunk
        for (const chunk of chunks) processChunk(chunk)
      }

      // flush whatever's left after the stream closes (e.g. a final event
      // with no trailing blank line before the connection ended)
      if (buffer.trim()) processChunk(buffer)
    } catch (err) {
      if (err.name !== 'AbortError') callbacks.onError?.(err)
    }
  })()

  return controller
}