export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')

// Server pings every 15s, so 45s of silence means the connection is dead.
const IDLE_TIMEOUT_MS = 45_000

async function readErrorMessage(res) {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      const first = body.detail[0]
      const field = first?.loc?.[first.loc.length - 1]
      if (field === 'trade_description') return 'Describe the move in 5 to 500 characters.'
      return first?.msg || 'Invalid request.'
    }
  } catch {
    /* not JSON */
  }
  if (res.status === 429) return 'Rate limit reached. Give it a few minutes.'
  if (res.status >= 500) return `The trade desk server errored (${res.status}).`
  return `Request failed (${res.status}).`
}

/**
 * Streams POST /analyze/stream with fetch + manual SSE parsing (EventSource
 * can't send a POST body).
 *
 * handlers: { status, tool, player, players, sources, report, error, done }
 * Each handler gets the parsed JSON payload. Exactly one of error/done-with-
 * report fires at the end, and `finish` is always called once.
 * Returns an AbortController.
 */
export function streamAnalysis(team, tradeDescription, handlers) {
  const controller = new AbortController()
  let finished = false
  let sawReport = false
  let sawError = false
  let idleTimer = null

  const finish = (err) => {
    if (finished) return
    finished = true
    clearTimeout(idleTimer)
    if (err) handlers.error?.({ message: err })
    handlers.finish?.()
  }

  const resetIdle = () => {
    clearTimeout(idleTimer)
    idleTimer = setTimeout(() => {
      controller.abort()
      finish('Lost connection to the trade desk (no response for 45s).')
    }, IDLE_TIMEOUT_MS)
  }

  function dispatch(block) {
    let event = 'message'
    const dataLines = []
    for (const line of block.split('\n')) {
      if (!line || line.startsWith(':')) continue
      const idx = line.indexOf(':')
      const field = idx === -1 ? line : line.slice(0, idx)
      let value = idx === -1 ? '' : line.slice(idx + 1)
      if (value.startsWith(' ')) value = value.slice(1)
      if (field === 'event') event = value
      else if (field === 'data') dataLines.push(value)
    }
    if (!dataLines.length) return

    let payload
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch {
      return // ignore a malformed event rather than killing the whole run
    }

    if (event === 'report') sawReport = true
    if (event === 'error') {
      sawError = true
      handlers.error?.(payload)
      return
    }
    if (event === 'done') {
      handlers.done?.(payload)
      finish(sawReport || sawError ? null : 'The analysis ended without a report.')
      return
    }
    handlers[event]?.(payload)
  }

  ;(async () => {
    try {
      resetIdle()
      const res = await fetch(`${API_URL}/analyze/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify({ team, trade_description: tradeDescription }),
        signal: controller.signal,
      })
      if (!res.ok || !res.body) {
        finish(await readErrorMessage(res))
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        resetIdle()
        // SSE allows \r\n, \r or \n line endings; normalize before splitting
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n?/g, '\n')
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop()
        for (const b of blocks) dispatch(b)
      }
      buffer += decoder.decode()
      if (buffer.trim()) dispatch(buffer)
      finish(sawReport || sawError ? null : 'Connection closed before the analysis finished.')
    } catch (err) {
      if (err.name === 'AbortError') {
        finish(null)
        return
      }
      finish(
        err instanceof TypeError
          ? `Can't reach the trade desk at ${API_URL}. Is the backend running?`
          : err.message || 'Something went wrong.',
      )
    }
  })()

  return controller
}

export async function fetchHealth() {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 6000)
  try {
    const res = await fetch(`${API_URL}/health`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(String(res.status))
    return await res.json()
  } finally {
    clearTimeout(t)
  }
}
