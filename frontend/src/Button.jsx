// Author: Shams Anjum, 2026

// A simple reusable button.
// className lets callers add extra styles (e.g. btn-analyze).
function Button({ onClick, disabled, className, children }) {
  return (
    <button
      type="button"
      className={`btn ${className ?? ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

export default Button
