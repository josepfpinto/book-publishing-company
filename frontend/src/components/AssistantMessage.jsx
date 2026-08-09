export default function AssistantMessage({ content, isStreaming, timestamp }) {
  return (
    <div className="assistant-message">
      <div className="assistant-message__rule" aria-hidden="true" />
      <div className="assistant-message__body">
        <div className="assistant-message__meta">
          <span className="assistant-message__label">AI</span>
          {timestamp && (
            <span className="assistant-message__timestamp">{timestamp}</span>
          )}
        </div>
        {isStreaming ? (
          <div className="assistant-message__dots" aria-label="Thinking…">
            <span className="assistant-message__dot" />
            <span className="assistant-message__dot" />
            <span className="assistant-message__dot" />
          </div>
        ) : (
          <p className="assistant-message__content">{content}</p>
        )}
      </div>
    </div>
  )
}
