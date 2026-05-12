function Button({ onClick, children }) {
  return (
    <button type="button" className="btn" onClick={onClick}>
      {children}
    </button>
  )
}

export default Button
