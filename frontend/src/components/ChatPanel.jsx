import MessageList from './MessageList.jsx'
import ChatInput from './ChatInput.jsx'

function ConversationDivider() {
  return (
    <div className="conversation-divider">
      <div className="conversation-divider__rule" />
      <span className="conversation-divider__label">Conversation</span>
      <div className="conversation-divider__rule" />
    </div>
  )
}

export default function ChatPanel({ messages, isLoading, onSubmit, children }) {
  return (
    <div className="chat-panel">
      {messages.length > 0 && <ConversationDivider />}
      <div className="chat-panel__body">
        {messages.length === 0
          ? children
          : <MessageList messages={messages} />}
      </div>
      <ChatInput onSubmit={onSubmit} isLoading={isLoading} />
    </div>
  )
}
