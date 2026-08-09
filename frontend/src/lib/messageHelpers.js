export function applyToken(messages, id, token) {
  return messages.map(m => m.id === id ? { ...m, content: m.content + token } : m)
}

export function applySources(messages, id, sources) {
  return messages.map(m => m.id === id ? { ...m, sources } : m)
}

export function applyDone(messages, id) {
  return messages.map(m => m.id === id ? { ...m, isStreaming: false } : m)
}

export function applyError(messages, id, msg) {
  return messages.map(m => m.id === id ? { ...m, content: msg, isStreaming: false } : m)
}

export function buildTimestamp() {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}
