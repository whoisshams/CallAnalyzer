import { useState, useEffect, useRef } from 'react'
import { streamAnalysis } from './lib/api.js'

// Progress messages now stream from the backend in real time.
// No fake timers — each line appears when the matching backend event fires.

function average(numbers) {
  const total = numbers.reduce((sum, number) => sum + number, 0)
  return Math.round(total / numbers.length)
}

function buildMetrics(result) {
  const agent = result.agent_tone_reviewer
  const patient = result.patient_tone_reviewer
  const outcome = result.call_outcome_reviewer

  if (!agent || !patient || !outcome) return null

  const allScores = [
    agent.professionalism,
    agent.empathy,
    agent.clarity,
    agent.helpfulness,
    agent.de_escalation,
    patient.respectfulness,
    patient.clarity,
    patient.cooperation,
    patient.emotional_regulation,
    11 - patient.escalation_intensity,
    outcome.resolution_completeness,
    outcome.next_step_clarity,
    outcome.phi_compliance,
    11 - outcome.safety_risk,
    11 - outcome.escalation_necessity,
  ]

  const overall = average(allScores) * 10
  const sentiment = average([
    agent.empathy,
    agent.helpfulness,
    agent.de_escalation,
    patient.respectfulness,
    patient.cooperation,
    patient.emotional_regulation,
  ])
  const compliance = outcome.phi_compliance >= 8 && outcome.safety_risk <= 3
    ? 'pass'
    : 'review'

  return {
    overall,
    sentiment,
    compliance,
    actionItems: outcome.escalation_necessity,
  }
}

function buildSupportReview(result) {
  const agent = result.agent_tone_reviewer
  const patient = result.patient_tone_reviewer
  const outcome = result.call_outcome_reviewer

  // If a reviewer block is missing, we cannot safely calculate the score.
  if (!agent || !patient || !outcome) {
    return {
      support_score: null,
      is_flagged: true,
      reasons: ['required_reviewer_data_missing'],
    }
  }

  // Low patient escalation means de-escalation was not really tested.
  // The backend score is 1-10, so 1-3 is treated as low escalation.
  const supportFields = [
    agent.professionalism,
    agent.empathy,
    agent.clarity,
    agent.helpfulness,
  ]

  if (patient.escalation_intensity > 3) {
    supportFields.push(agent.de_escalation)
  }

  // support_score is the exact average of the chosen agent support fields.
  const rawScore = supportFields.reduce((sum, score) => sum + score, 0) / supportFields.length
  const support_score = Number(rawScore.toFixed(1))

  const reasons = []

  if (support_score < 7) reasons.push('support_score_below_7')
  if (agent.professionalism < 6) reasons.push('professionalism_below_6')
  if (agent.empathy < 6) reasons.push('empathy_below_6')
  if (agent.helpfulness < 6) reasons.push('helpfulness_below_6')
  if (outcome.phi_compliance < 9) reasons.push('phi_compliance_below_9')
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
  const abortRef = useRef(null)
  const metrics = result ? buildMetrics(result) : null
  const supportReview = result ? buildSupportReview(result) : null

  useEffect(() => {
    if (analyzeCount === 0) return // skip first render

    async function run() {
      const controller = new AbortController()
      abortRef.current = controller
      setMessages([])
      setResult(null)
      setIsRunning(true)

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
          controller.signal,
        )
      } catch (err) {
        // AbortError means the user clicked Stop. It is not a failure.
        if (err.name === 'AbortError') return
        setMessages((prev) => [...prev, `Error: ${err.message}`])
      } finally {
        setIsRunning(false)
        abortRef.current = null
      }
    }

    run()
  }, [analyzeCount, transcript])

  function stopAnalysis() {
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
            <button type="button" className="stop-button" onClick={stopAnalysis}>
              Stop
            </button>
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
              <strong>{result.transcript_id}</strong>
            </div>
            <p className="result-summary">{result.coordinator_summary}</p>

            {metrics && (
              <div className="metric-grid">
                <div className="metric-card">
                  <span>Overall</span>
                  <strong>{metrics.overall}<small>/100</small></strong>
                </div>
                <div className="metric-card">
                  <span>Sentiment</span>
                  <strong>{metrics.sentiment}<small>/10</small></strong>
                </div>
                <div className="metric-card">
                  <span>Compliance</span>
                  <strong className={metrics.compliance === 'pass' ? 'good' : 'warn'}>
                    {metrics.compliance}
                  </strong>
                </div>
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

          <section className="json-card">
            <div className="json-card__header">
              <span>QA Report <em>qa_report.json</em></span>
              <button
                type="button"
                className="copy-button"
                onClick={() => navigator.clipboard.writeText(JSON.stringify(result, null, 2))}
              >
                copy
              </button>
            </div>
            <pre className="result-json">{JSON.stringify(result, null, 2)}</pre>
          </section>
        </>
      )}
    </div>
  )
}

export default OutputWindow
