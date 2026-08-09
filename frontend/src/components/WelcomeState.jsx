const SUGGESTIONS = [
  "What motivates Jo March to refuse Laurie's proposal?",
  "How does economic status shape the Bennet daughters' choices?",
  "Compare the opening lines of both novels.",
]

export default function WelcomeState({ onSubmit }) {
  return (
    <div className="welcome-state">
      <p className="welcome-state__greeting">
        <em>Ready to answer questions about</em>{' '}
        <strong>Little Women</strong>{' '}
        <em>and</em>{' '}
        <strong>Pride &amp; Prejudice.</strong>
      </p>

      <span className="welcome-state__divider">Or try asking</span>

      <div className="welcome-state__suggestions">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            className="welcome-state__suggestion-btn"
            onClick={() => onSubmit(q)}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
