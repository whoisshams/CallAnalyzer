const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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
