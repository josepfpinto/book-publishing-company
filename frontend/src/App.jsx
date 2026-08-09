import { useState, useRef, useEffect } from 'react'
import AppHeader from './components/AppHeader.jsx'
import BookToggle from './components/BookToggle.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import WelcomeState from './components/WelcomeState.jsx'
import { streamChat } from './lib/streamChat.js'
import {
  applyToken,
  applySources,
  applyDone,
  applyError,
  buildTimestamp,
} from './lib/messageHelpers.js'

export default function App() {
  const [messages, setMessages] = useState([])
  const [currentBookContext, setCurrentBookContext] = useState('both')
  const [isLoading, setIsLoading] = useState(false)

  const abortRef = useRef(null)

  function handleSubmit(text) {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const streamId = crypto.randomUUID()
    const timestamp = buildTimestamp()
    const frozenBookContext = currentBookContext

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      bookContext: frozenBookContext,
      timestamp,
      sources: [],
      isStreaming: false,
    }

    const assistantPlaceholder = {
      id: streamId,
      role: 'assistant',
      content: '',
      bookContext: frozenBookContext,
      timestamp,
      sources: [],
      isStreaming: true,
    }

    const history = messages
      .filter(m => !m.isStreaming && m.content.length > 0)
      .map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => {
      const cleaned = prev.map(m =>
        m.role === 'assistant' && m.isStreaming ? { ...m, isStreaming: false } : m
      )
      return [...cleaned, userMessage, assistantPlaceholder]
    })
    setIsLoading(true)

    streamChat({
      bookId: frozenBookContext,
      message: text,
      history,
      signal: controller.signal,
      onToken(token) {
        setMessages(prev => applyToken(prev, streamId, token))
      },
      onSources(sources) {
        setMessages(prev => applySources(prev, streamId, sources))
      },
      onError(msg) {
        setMessages(prev => applyError(prev, streamId, msg))
        setIsLoading(false)
      },
      onDone() {
        setMessages(prev => applyDone(prev, streamId))
        setIsLoading(false)
      },
    })
  }

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  return (
    <div className="app-shell">
      <AppHeader />
      <BookToggle selected={currentBookContext} onSelect={setCurrentBookContext} />
      <ChatPanel messages={messages} isLoading={isLoading} onSubmit={handleSubmit}>
        <WelcomeState onSubmit={handleSubmit} />
      </ChatPanel>
    </div>
  )
}
