import { useRef, useState } from 'react'
import Button from './Button.jsx'
import { transcribeAudio } from './lib/api.js'

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
  const fileInputRef = useRef(null)
  const [transcribing, setTranscribing] = useState(false)

  // Triggered when the user picks an MP3 file. Sends it to the transcription
  // API, then puts the resulting text into the transcript textarea.
  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    e.target.value = '' // reset so the same file can be re-uploaded later
    if (!file) return

    setTranscribing(true)
    try {
      const text = await transcribeAudio(file)
      onChange(text)
    } catch (err) {
      alert(`Transcription failed: ${err.message}`)
    } finally {
      setTranscribing(false)
    }
  }

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

        {/* Upload MP3 button: opens the hidden file picker */}
        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={transcribing}
        >
          {transcribing ? 'Transcribing...' : 'Upload MP3'}
        </Button>

        {/* Hidden file input — accepts only audio files */}
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/mpeg,audio/mp3,.mp3"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
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
            ? `${transcript.length.toLocaleString()} characters`
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
