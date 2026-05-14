import Button from './Button.jsx'

// Import the three sample transcripts as plain text strings (Vite ?raw feature)
import smoothCall from '../../backend/mock_transcripts/smooth_call.txt?raw'
import badAgent   from '../../backend/mock_transcripts/bad_agent.txt?raw'
import badPatient from '../../backend/mock_transcripts/bad_patient.txt?raw'

const SAMPLES = [
  { label: 'Smooth Call', text: smoothCall },
  { label: 'Bad Agent',   text: badAgent },
  { label: 'Bad Patient', text: badPatient },
]

// transcript and onChange come from App (controlled input)
// onAnalyze is called when the user clicks the Analyze button
function InputWindow({ transcript, onChange, onAnalyze }) {
  return (
    <div className="panel">
      <p className="panel-title">Transcript</p>

      {/* Sample buttons — click to fill the textarea */}
      <div className="sample-buttons">
        {SAMPLES.map((s) => (
          <Button key={s.label} onClick={() => onChange(s.text)}> 
            {s.label}
          </Button>
        ))}
      </div>

      {/* The main text input area */}
      <textarea
        value={transcript}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Paste or type a call transcript here..."
        spellCheck={false}
      />

      {/* Footer: character count and Analyze button */}
      <div className="input-footer">
        <span className="char-count">
          {transcript.length > 0
            ? `${transcript.length.toLocaleString()} characters` // Fetches the length of the transcript
            : 'No transcript entered'}
        </span>
        <Button
          className="btn-analyze"
          onClick={onAnalyze}
          disabled={transcript.length === 0}
        >
          Analyze
        </Button>
      </div>
    </div>
  )
}

export default InputWindow
