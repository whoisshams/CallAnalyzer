import { useState, useEffect, useRef } from 'react'
import { streamAnalysis } from './lib/api.js'
import Button from './Button.jsx'
import ScoreBreakdown from './ScoreBreakdown.jsx'
import JsonModal from './JsonModal.jsx'

// Progress messages now stream from the backend in real time.
// No fake timers — each line appears when the matching backend event fires.

function buildSupportReview(result) {
  const agent = result.agent_tone_reviewer
  const patient = result.patient_tone_reviewer
  const outcome = result.call_outcome_reviewer

  if (!agent || !patient || !outcome) {
    return {
      support_score: null,
      is_flagged: true,
      reasons: ['required_reviewer_data_missing'],
    }
  }

  const supportFields = [
    agent.professionalism,
    agent.empathy,
    agent.clarity,
    agent.helpfulness,
    agent.tension_handling,
  ]

  const rawScore = supportFields.reduce((sum, score) => sum + score, 0) / supportFields.length
  const support_score = Number(rawScore.toFixed(1))

  const reasons = []
  if (support_score < 7) reasons.push('support_score_below_7')
  if (agent.professionalism < 6) reasons.push('professionalism_below_6')
  if (agent.empathy < 6) reasons.push('empathy_below_6')
  if (agent.helpfulness < 6) reasons.push('helpfulness_below_6')
  if (outcome.privacy_handling < 9) reasons.push('privacy_handling_below_9')
  if (outcome.safety_risk >= 7) reasons.push('safety_risk_at_or_above_7')

  return {
    support_score,
    is_flagged: reasons.length > 0,
    reasons,
  }
}

function OutputWindow({ transcript, analyzeCount }) {
  const [messages, setMessages] = useState([])
  const [result, setResult]     = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [showJson, setShowJson] = useState(false)
  const abortRef = useRef(null)
  const supportReview = result ? buildSupportReview(result) : null

  useEffect(() => {
    if (analyzeCount === 0) return

    const controller = new AbortController()
    abortRef.current = controller

    async function run() {
      setMessages([])
      setResult(null)
      setIsRunning(true)

      try {
        await streamAnalysis(
          { transcript_id: 'ui_submission', transcript },
          (event, data) => {
            if (event === 'progress') {
              setMessages((prev) => [...prev, data])
            } else if (event === 'result') {
              setResult(data)
            } else if (event === 'error') {
              setMessages((prev) => [...prev, `Error: ${data.detail}`])
            }
          },
          controller.signal,
        )
      } catch (err) {
        if (err.name === 'AbortError') return
        setMessages((prev) => [...prev, `Error: ${err.message}`])
      } finally {
        setIsRunning(false)
        if (abortRef.current === controller) abortRef.current = null
      }
    }

    run()
    return () => controller.abort()
  }, [analyzeCount, transcript])

  function stopAnalysis() {
    if (!isRunning) return
    abortRef.current?.abort()
    setIsRunning(false)
    setMessages((prev) => [...prev, 'Analysis stopped by user.'])
  }

  const hasContent = messages.length > 0 || result !== null

  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-title">Analysis</p>
        <div className="analysis-actions">
          {isRunning && (
            <Button className="stop-button" onClick={stopAnalysis}>
              Stop
            </Button>
          )}
          <span className="panel-meta">report · live</span>
        </div>
      </div>

      {!hasContent && (
        <div className="output-empty">
          <p className="output-empty__title">Ready to analyze</p>
          <p className="output-empty__hint">
            Load or paste a transcript, then click Analyze. Four agents will review the call:
          </p>
          <ul className="agent-list">
            <li><span className="agent-dot" />Coordinator</li>
            <li><span className="agent-dot" />Agent tone reviewer</li>
            <li><span className="agent-dot" />Patient tone reviewer</li>
            <li><span className="agent-dot" />Call outcome reviewer</li>
          </ul>
        </div>
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
          <section className="summary-card">
            <div className="summary-heading">
              <span className="summary-label">Coordinator Summary</span>
            </div>
            <p className="result-summary">{result.coordinator_summary}</p>

            {supportReview && (
              <div className="metric-grid">
                <div className="metric-card">
                  <span>Support Score</span>
                  <strong>{supportReview.support_score ?? 'n/a'}<small>/10</small></strong>
                </div>
                <div className="metric-card">
                  <span>Flag Status</span>
                  <strong className={supportReview.is_flagged ? 'warn' : 'good'}>
                    {supportReview.is_flagged ? 'flagged' : 'clear'}
                  </strong>
                </div>
              </div>
            )}

            {supportReview?.is_flagged && (
              <div className="flag-box">
                <span>Flag reasons</span>
                <ul>
                  {supportReview.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <ScoreBreakdown result={result} />

          <div className="json-view-row">
            <button
              type="button"
              className="btn-view-json"
              onClick={() => setShowJson(true)}
            >
              <span className="btn-view-json__icon">{'{}'}</span>
              View as JSON
            </button>
          </div>

          {showJson && (
            <JsonModal result={result} onClose={() => setShowJson(false)} />
          )}
        </>
      )}
    </div>
  )
}

export default OutputWindow
