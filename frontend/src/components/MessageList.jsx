import { useRef, useEffect } from 'react'
import UserMessage from './UserMessage.jsx'
import AssistantMessage from './AssistantMessage.jsx'
import SourceList from './SourceList.jsx'

export default function MessageList({ messages }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'instant' })
  }, [messages])

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <div key={message.id}>
          {index > 0 && message.role === 'user' && (
            <div className="message-list__divider" />
          )}
          {message.role === 'user' ? (
            <UserMessage content={message.content} timestamp={message.timestamp} />
          ) : (
            <>
              <AssistantMessage
                content={message.content}
                isStreaming={message.isStreaming}
                timestamp={message.timestamp}
              />
              {!message.isStreaming && message.sources?.length > 0 && (
                <SourceList sources={message.sources} />
              )}
            </>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
