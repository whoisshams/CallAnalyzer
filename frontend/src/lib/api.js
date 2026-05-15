const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
// Default to a relative path so the Vite dev proxy can forward to the
// Whisper server at http://localhost:9000 (configured in vite.config.js).
// This avoids CORS issues with the container which doesn't allow cross-origin.
const TRANSCRIBE_URL = import.meta.env.VITE_TRANSCRIBE_URL ?? '/whisper'

/**
 * @template T
 * @param {string} path
 * @param {RequestInit} [options]
 * @returns {Promise<T>}
 */
async function requestJson(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`

    try {
      const body = await response.json()
      if (body && typeof body.detail === 'string') {
        message = body.detail
      }
    } catch {
      // Fall back to the status message when the API does not return JSON.
    }

    throw new Error(message)
  }

  return response.json()
}

/** @returns {Promise<{ status: string }>} */
export function checkHealth() {
  return requestJson('/health')
}

/**
 * @param {{ transcript_id: string, transcript: string }} payload
 * @returns {Promise<Record<string, unknown>>}
 */
export function analyzeTranscript(payload) {
  return requestJson('/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Stream backend progress events from POST /analyze/stream.
 * Calls onEvent(type, data) for each Server-Sent Event as it arrives.
 * Event types: 'progress' (string), 'result' (full JSON), 'error' ({detail}).
 *
 * @param {{ transcript_id: string, transcript: string }} payload
 * @param {(event: string, data: any) => void} onEvent
 * @param {AbortSignal} [signal]
 */
export async function streamAnalysis(payload, onEvent, signal) {
  const response = await fetch(`${API_BASE_URL}/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  // Read the response body as a stream and parse SSE events as they arrive.
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE events are separated by a blank line ("\n\n").
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() // keep the trailing incomplete chunk for next read

    for (const chunk of chunks) {
      let event = 'message'
      let data = ''
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data += line.slice(5).trim()
      }
      if (data) onEvent(event, JSON.parse(data))
    }
  }
}

/**
 * Send an audio file to the Whisper-compatible transcription endpoint
 * and return the transcribed text.
 *
 * @param {File} file
 * @returns {Promise<string>}
 */
export async function transcribeAudio(file) {
  // Build a multipart/form-data body — same shape as the curl example.
  const form = new FormData()
  form.append('file', file)
  form.append('model', 'whisper-1')
  form.append('language', 'auto')
  form.append('response_format', 'json')
  form.append('temperature', '0')

  const url = `${TRANSCRIBE_URL}/v1/audio/transcriptions`

  let response
  try {
    response = await fetch(url, {
      method: 'POST',
      body: form, // Do NOT set Content-Type — the browser adds the boundary.
    })
  } catch (err) {
    // fetch() throws (with a vague message like "Load failed") when the
    // request never reached the server — usually a wrong URL, the server is
    // not running, or CORS blocked the request before a response could be read.
    throw new Error(
      `Could not reach transcription server at ${url}. ` +
      `Check that it is running and CORS allows http://localhost:5173. ` +
      `(${err.message})`,
      { cause: err },
    )
  }

  if (!response.ok) {
    throw new Error(`Transcription failed with status ${response.status}`)
  }

  const data = await response.json()
  return data.text ?? ''
}
