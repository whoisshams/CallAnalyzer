// Author: Shams Anjum, 2026

import { useState, useEffect, useCallback } from 'react'

function JsonModal({ result, onClose }) {
  const json = JSON.stringify(result, null, 2)
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(json)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }, [json])

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="json-modal-backdrop" onClick={onClose}>
      <div className="json-modal" onClick={(e) => e.stopPropagation()}>
        <div className="json-modal__header">
          <div className="json-modal__title">
            <span className="json-modal__label">QA Report</span>
            <em className="json-modal__filename">qa_report.json</em>
          </div>
          <div className="json-modal__actions">
            <button type="button" className="copy-button" onClick={handleCopy}>
              {copied ? '✓ copied' : 'copy'}
            </button>
            <button type="button" className="json-modal__close" onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>
        </div>
        <pre className="result-json">{json}</pre>
      </div>
    </div>
  )
}

export default JsonModal
