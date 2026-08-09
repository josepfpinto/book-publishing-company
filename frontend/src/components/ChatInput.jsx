import { useState, useRef, useEffect } from 'react'

export default function ChatInput({ onSubmit, isLoading }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const trimmed = value.trim()
  const isEmpty = trimmed.length === 0
  const sendDisabled = isEmpty || isLoading

  // Auto-expand: reset to auto first so scrollHeight can shrink
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  function handleSubmit() {
    if (sendDisabled) return
    onSubmit(trimmed)
    setValue('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const textareaClass = [
    'chat-input__textarea',
    isLoading ? 'chat-input__textarea--loading' : '',
  ].filter(Boolean).join(' ')

  const buttonClass = [
    'chat-input__send',
    isLoading
      ? 'chat-input__send--loading'
      : isEmpty
        ? 'chat-input__send--disabled'
        : 'chat-input__send--enabled',
  ].filter(Boolean).join(' ')

  return (
    <div className="chat-input">
      <textarea
        ref={textareaRef}
        className={textareaClass}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask something about the book…"
        rows={1}
        disabled={isLoading}
        aria-label="Message"
      />
      <button
        className={buttonClass}
        onClick={handleSubmit}
        disabled={sendDisabled}
        aria-label="Send"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M2 8L14 2L8 14L7 9L2 8Z"
            fill="currentColor"
            stroke="currentColor"
            strokeWidth="0.5"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  )
}
