function ScoreBar({ label, score, invert = false }) {
  const fill = invert ? ((11 - score) / 10) * 100 : (score / 10) * 100
  const isLow = fill < 50
  const isMid = fill >= 50 && fill < 75

  return (
    <div className="score-bar-row">
      <span className="score-bar-label">{label}</span>
      <div className="score-bar-track">
        <div
          className={`score-bar-fill ${isLow ? 'fill-low' : isMid ? 'fill-mid' : 'fill-high'}`}
          style={{ width: `${fill}%` }}
        />
      </div>
      <span className="score-bar-value">{score}<small>/10</small></span>
    </div>
  )
}

function ScoreBreakdown({ result }) {
  const { agent_tone_reviewer: agent, patient_tone_reviewer: patient, call_outcome_reviewer: outcome } = result

  if (!agent || !patient || !outcome) return null

  return (
    <section className="stats-card">
      <div className="stats-card__header">
        <span className="stats-card__title">Score Breakdown</span>
      </div>

      <div className="stats-groups">
        <div className="stats-group">
          <p className="stats-group__label">Agent Tone</p>
          <ScoreBar label="Professionalism"  score={agent.professionalism} />
          <ScoreBar label="Empathy"          score={agent.empathy} />
          <ScoreBar label="Clarity"          score={agent.clarity} />
          <ScoreBar label="Helpfulness"      score={agent.helpfulness} />
          <ScoreBar label="Tension Handling" score={agent.tension_handling} />
          {agent.notes && <p className="stats-group__notes">{agent.notes}</p>}
        </div>

        <div className="stats-group">
          <p className="stats-group__label">Patient Tone</p>
          <ScoreBar label="Respectfulness"      score={patient.respectfulness} />
          <ScoreBar label="Clarity"             score={patient.clarity} />
          <ScoreBar label="Cooperation"         score={patient.cooperation} />
          <ScoreBar label="Emotional Regulation" score={patient.emotional_regulation} />
          {patient.notes && <p className="stats-group__notes">{patient.notes}</p>}
        </div>

        <div className="stats-group">
          <p className="stats-group__label">Call Outcome</p>
          <ScoreBar label="Resolution"        score={outcome.resolution_completeness} />
          <ScoreBar label="Follow-Up Clarity" score={outcome.followup_clarity} />
          <ScoreBar label="Privacy Handling"  score={outcome.privacy_handling} />
          <ScoreBar label="Safety Risk"       score={outcome.safety_risk} invert />
          <ScoreBar label="Escalation Needed" score={outcome.escalation_necessity} invert />
          {outcome.notes && <p className="stats-group__notes">{outcome.notes}</p>}
        </div>
      </div>
    </section>
  )
}

export default ScoreBreakdown
