export default function UserMessage({ content, timestamp }) {
  return (
    <div className="user-message">
      <div className="user-message__card">
        <p className="user-message__content">{content}</p>
        {timestamp && (
          <p className="user-message__timestamp">{timestamp}</p>
        )}
      </div>
    </div>
  )
}
