import { useState, useEffect } from 'react'
import { streamAnalysis } from './lib/api.js'

// Progress messages now stream from the backend in real time.
// No fake timers — each line appears when the matching backend event fires.

function OutputWindow({ transcript, analyzeCount }) {
  const [messages, setMessages] = useState([])
  const [result, setResult]     = useState(null)

  useEffect(() => {
    if (analyzeCount === 0) return // skip first render

    async function run() {
      setMessages([])
      setResult(null)

      try {
        await streamAnalysis(
          { transcript_id: 'ui_submission', transcript },
          (event, data) => {
            // 'progress' = a status line; 'result' = final JSON; 'error' = failure
            if (event === 'progress') {
              setMessages((prev) => [...prev, data])
            } else if (event === 'result') {
              setResult(data)
            } else if (event === 'error') {
              setMessages((prev) => [...prev, `Error: ${data.detail}`])
            }
          },
        )
      } catch (err) {
        setMessages((prev) => [...prev, `Error: ${err.message}`])
      }
    }

    run()
  }, [analyzeCount, transcript])

  const hasContent = messages.length > 0 || result !== null

  return (
    <div className="panel">
      <p className="panel-title">Output</p>

      {!hasContent && (
        <p className="output-empty">Results will appear here after you click Analyze.</p>
      )}

      {messages.length > 0 && (
        <div className="console">
          {messages.map((msg, i) => (
            <div key={i} className="console-line">
              <span className="console-prefix">›</span>
              {msg}
            </div>
          ))}
        </div>
      )}

      {result && (
        <>
          <p className="result-summary">{result.coordinator_summary}</p>
          <pre className="result-json">{JSON.stringify(result, null, 2)}</pre>
        </>
      )}
    </div>
  )
}

export default OutputWindow
