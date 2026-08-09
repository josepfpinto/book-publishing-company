import { describe, it, expect } from 'vitest'
import { applyToken, applySources, applyDone, applyError, buildTimestamp } from './messageHelpers.js'

const base = [
  { id: 'a', role: 'user',      content: 'hi',  isStreaming: false, sources: [] },
  { id: 'b', role: 'assistant', content: '',    isStreaming: true,  sources: [] },
]

describe('applyToken', () => {
  it('accumulates tokens into the correct message by id', () => {
    const after = applyToken(base, 'b', 'Hello')
    expect(after.find(m => m.id === 'b').content).toBe('Hello')
    expect(after.find(m => m.id === 'a').content).toBe('hi')
  })

  it('does not affect other messages', () => {
    const after = applyToken(base, 'b', 'x')
    expect(after.find(m => m.id === 'a')).toEqual(base[0])
  })

  it('appends successive tokens', () => {
    const step1 = applyToken(base, 'b', 'Hel')
    const step2 = applyToken(step1, 'b', 'lo')
    expect(step2.find(m => m.id === 'b').content).toBe('Hello')
  })
})

describe('applySources', () => {
  it('sets sources on the correct message', () => {
    const src = [{ book_title: 'Little Women', chapter_number: 1 }]
    const after = applySources(base, 'b', src)
    expect(after.find(m => m.id === 'b').sources).toBe(src)
    expect(after.find(m => m.id === 'a').sources).toEqual([])
  })
})

describe('applyDone', () => {
  it('clears isStreaming on the correct message', () => {
    const after = applyDone(base, 'b')
    expect(after.find(m => m.id === 'b').isStreaming).toBe(false)
    expect(after.find(m => m.id === 'a').isStreaming).toBe(false)
  })
})

describe('applyError', () => {
  it('replaces content and clears isStreaming on error', () => {
    const after = applyError(base, 'b', 'something went wrong')
    const msg = after.find(m => m.id === 'b')
    expect(msg.content).toBe('something went wrong')
    expect(msg.isStreaming).toBe(false)
  })
})

describe('buildTimestamp', () => {
  it('returns HH:MM format with zero-padded hours and minutes', () => {
    const ts = buildTimestamp()
    expect(ts).toMatch(/^\d{2}:\d{2}$/)
  })
})
