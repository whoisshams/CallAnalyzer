function OutputWindow({ messages }) {
  if (messages.length === 0) return null

  return (
    <div className="output-window">
      {messages.map((msg, i) => (
        <div key={i} className="output-window__line">
          <span className="output-window__prefix">›</span>
          {msg}
        </div>
      ))}
    </div>
  )
}

export default OutputWindow
