import { useState } from 'react'
import './App.css'
import InputWindow from './InputWindow.jsx'
import OutputWindow from './OutputWindow.jsx'

function App() {
  // Transcript text lives here so both panels can access it
  const [transcript, setTranscript] = useState('')
  // Increments each time the user clicks Analyze; OutputWindow watches this
  const [analyzeCount, setAnalyzeCount] = useState(0)

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">CallAnalyser</span>
          <span className="brand-version">v0.4 · demo</span>
        </div>
        <div className="server-status">
          <span className="status-dot" aria-hidden="true" />
          <span>api.callanalyser.local</span>
          <span className="server-meta">FastAPI · 4 agents</span>
        </div>
      </header>

      <InputWindow
        transcript={transcript}
        onChange={setTranscript}
        onAnalyze={() => setAnalyzeCount((n) => n + 1)}
      />

      <OutputWindow transcript={transcript} analyzeCount={analyzeCount} />
    </div>
  )
}

export default App
