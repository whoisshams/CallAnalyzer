import { useState } from 'react'
import './App.css'
import InputWindow from './InputWindow.jsx'
import OutputWindow from './OutputWindow.jsx'

const STEPS = [
  'Starting analysis...',
  'Checking agent tone...',
  'Checking patient tone...',
  'Checking call outcome...',
  'Building final summary...',
]

function App() {
  const [messages, setMessages] = useState([])

  async function handleAnalyze() {
    setMessages([])
    for (const step of STEPS) {
      await new Promise((r) => setTimeout(r, 700))
      setMessages((prev) => [...prev, step])
    }
  }

  return (
    <>
      <InputWindow onAnalyze={handleAnalyze} />
      <OutputWindow messages={messages} />
    </>
  )
}

export default App
