// Author: Shams Anjum, 2026

import { useEffect, useState } from 'react'
import './App.css'
import InputWindow from './InputWindow.jsx'
import OutputWindow from './OutputWindow.jsx'
import { checkStatus } from './lib/api.js'

const API_HOST = new URL(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').host

function App() {
  const [transcript, setTranscript] = useState('')
  const [transcriptId, setTranscriptId] = useState('')
  const [analyzeCount, setAnalyzeCount] = useState(0)
  const [apiState, setApiState] = useState('checking')
  const [apiMessage, setApiMessage] = useState('Checking API…')

  useEffect(() => {
    checkStatus()
      .then((s) => {
        const state =
          s.anthropic === 'available' ? 'ok'
          : s.anthropic === 'demo' ? 'demo'
          : s.anthropic === 'limited' ? 'warn'
          : 'error'
        setApiState(state)
        setApiMessage(s.message)
      })
      .catch(() => {
        setApiState('error')
        setApiMessage('Cannot reach API.')
      })
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div className="brand-copy">
            <div>
              <span className="brand-name">CallAnalyser</span>
              <span className="brand-version">v0.4 · demo</span>
            </div>
            <p className="brand-description">
              A configurable call center QA analyzer, currently demoed with healthcare calls.
            </p>
          </div>
        </div>
        <div className="server-status">
          <span className={`status-dot status-dot--${apiState}`} aria-hidden="true" />
          <span>{API_HOST}</span>
          <span className="server-meta">{apiMessage}</span>
        </div>
      </header>

      <InputWindow
        transcript={transcript}
        demoMode={apiState === 'demo'}
        onChange={setTranscript}
        onSampleSelect={setTranscriptId}
        onAnalyze={() => setAnalyzeCount((n) => n + 1)}
      />

      <OutputWindow
        transcript={transcript}
        transcriptId={transcriptId}
        analyzeCount={analyzeCount}
      />
    </div>
  )
}

export default App
