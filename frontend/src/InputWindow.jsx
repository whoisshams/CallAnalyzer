import { useState } from 'react'

import Button from './Button.jsx'
import smoothCall from '../../backend/mock_transcripts/smooth_call.txt?raw'
import badAgent from '../../backend/mock_transcripts/bad_agent.txt?raw'
import badPatient from '../../backend/mock_transcripts/bad_patient.txt?raw'

const SAMPLES = [
  { label: 'Smooth Call', text: smoothCall },
  { label: 'Bad Agent',   text: badAgent },
  { label: 'Bad Patient', text: badPatient },
]

function InputWindow() {
  const [transcript, setTranscript] = useState('')

  function handleChange(event) {
    setTranscript(event.target.value)
  }

  function handleClear() {
    setTranscript('')
  }

  const charCount = transcript.length

  return (
    <div className="input-window">
      <div className="input-window__header">
        <label className="input-window__label" htmlFor="transcript-input">
          Call Transcript
        </label>
        {charCount > 0 && (
          <button
            type="button"
            className="input-window__clear"
            onClick={handleClear}
          >
            Clear
          </button>
        )}
      </div>

      <div className="input-window__samples">
        {SAMPLES.map((s) => (
          <Button key={s.label} onClick={() => setTranscript(s.text)}>
            {s.label}
          </Button>
        ))}
      </div>

      <textarea
        id="transcript-input"
        className="input-window__textarea"
        value={transcript}
        onChange={handleChange}
        placeholder={`Paste or type the call transcript here.\n\nExample:\nAgent: Thank you for calling, how can I help?\nPatient: I need to reschedule my appointment.`}
        spellCheck={false}
        aria-label="Call transcript"
      />

      <div className="input-window__footer">
        <span className="input-window__char-count">
          {charCount > 0 ? `${charCount.toLocaleString()} characters` : 'No transcript entered'}
        </span>
      </div>
    </div>
  )
}

export default InputWindow
