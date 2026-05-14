import { useState, useEffect } from 'react'

// The progress steps shown in the console during analysis
const STEPS = [
  'Starting analysis...',
  'Checking agent tone...',
  'Checking patient tone...',
  'Checking call outcome...',
  'Building final summary...',
]

// OutputWindow owns all analysis state and logic.
// analyzeCount is a number that goes up by 1 each time the user clicks Analyze.
// When it changes, useEffect runs the analysis.
function OutputWindow({ transcript, analyzeCount }) {
  const [messages, setMessages] = useState([])
  const [result, setResult]     = useState(null)

  // Run analysis every time analyzeCount increases
  useEffect(() => {
    // Skip the very first render (analyzeCount starts at 0)
    if (analyzeCount === 0) return

    async function runAnalysis() {
      setMessages([])
      setResult(null)

      // Show each step one by one with a short delay
      for (const step of STEPS) {
        await new Promise((r) => setTimeout(r, 700))
        setMessages((prev) => [...prev, step])
      }

      // TODO: replace this placeholder with a real API call:
      // const data = await analyzeTranscript({ transcript_id: 'ui_submission', transcript })
      // setResult(data)
      setResult({
        coordinator_summary: 'Placeholder summary. Wire the API to see real results.',
        transcript,
      })
    }

    runAnalysis()
  }, [analyzeCount, transcript]) // re-runs when analyzeCount changes; transcript is read inside the useEffect hook

  const hasContent = messages.length > 0 || result !== null

  return (
    <div className="panel">
      <p className="panel-title">Output</p>

      {/* Placeholder shown before the first analysis */}
      {!hasContent && (
        <p className="output-empty">Results will appear here after you click Analyze.</p>
      )}

      {/* Console log lines shown while analysis is running */}
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

      {/* Summary and full JSON shown after analysis finishes */}
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
