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
        <h1>Call Recording Analyzer</h1>
        <p>Paste or load a transcript, then click Analyze.</p>
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
