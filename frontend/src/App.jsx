import './App.css'

function App() {
  return (
    <main className="app-shell">
      <section className="hero-card" aria-labelledby="page-title">
        <p className="eyebrow">Call Recording Analyzer</p>
        <h1 id="page-title">Frontend scaffold is ready.</h1>
        <p className="intro">
          This Vite React app is set up to talk to the FastAPI backend. The
          transcript analysis UI can now build on the client in{' '}
          <code>src/lib/api.js</code>.
        </p>

        <div className="status-grid" aria-label="Setup status">
          <div>
            <span>Frontend</span>
            <strong>Vite + React + JavaScript</strong>
          </div>
          <div>
            <span>Backend API</span>
            <strong>http://localhost:8000</strong>
          </div>
          <div>
            <span>Analyze endpoint</span>
            <strong>POST /analyze</strong>
          </div>
        </div>
      </section>
    </main>
  )
}

export default App
