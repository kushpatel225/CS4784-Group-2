import { useState, useRef, useEffect } from 'react'
import './PersonScreen.css'

const API_BASE = 'https://backend-debater.discovery.cs.vt.edu'

const CONFIG = {
  a: {
    label: 'Person A',
    sigil: 'I',
    color: 'crimson',
    placeholder: 'State your position...',
<<<<<<< Updated upstream
    endpoint: '/api/chat/a',
=======
    endpoint: `${API_BASE}/api/chat/a`,
    arbiterEndpoint: `${API_BASE}/api/arbiter/a`,
>>>>>>> Stashed changes
  },
  b: {
    label: 'Person B',
    sigil: 'II',
    color: 'cobalt',
    placeholder: 'Present your argument...',
<<<<<<< Updated upstream
    endpoint: '/api/chat/b',
=======
    endpoint: `${API_BASE}/api/chat/b`,
    arbiterEndpoint: `${API_BASE}/api/arbiter/b`,
>>>>>>> Stashed changes
  },
}

export default function PersonScreen({ person, onBack }) {
  const cfg = CONFIG[person]
  const otherCfg = CONFIG[person === 'a' ? 'b' : 'a']

  const [thread, setThread] = useState([])
  const [coachMessages, setCoachMessages] = useState([])
  const [mode, setMode] = useState('coach')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [thread, coachMessages])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 2000)
    return () => clearInterval(interval)
  }, [])

  async function fetchAll() {
    try {
      const [threadRes, coachRes] = await Promise.all([
        fetch(`${API_BASE}/api/thread`),
        fetch(`${API_BASE}/api/coach/${person}`),
      ])
      const threadData = await threadRes.json()
      const coachData = await coachRes.json()
      setThread(threadData.thread || [])
      setMode(threadData.mode || 'coach')
      setCoachMessages((coachData.history || []).filter(m => m.role === 'assistant'))
    } catch (e) {
      console.error('fetchAll error:', e)
    }
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setLoading(true)

    try {
      const res = await fetch(cfg.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      console.log('Response from server:', data)
      await fetchAll()
    } catch (e) {
      console.error('Send error:', e)
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function buildDisplay() {
    const display = []
    let coachIdx = 0

    for (const msg of thread) {
      if (msg.role === 'user') {
        display.push({ type: 'thread', msg })

        // After my own message in coach mode, insert the next coach reply
        if (msg.person === person && mode === 'coach') {
          if (coachIdx < coachMessages.length) {
            display.push({ type: 'coach', msg: coachMessages[coachIdx] })
            coachIdx++
          }
        }
      }

      // Nudges: show in omniscient mode, targeted at this person
      if (msg.role === 'nudge' && mode === 'omniscient' && msg.target === person) {
        display.push({ type: 'nudge', msg })
      }
    }

    return display
  }

  const display = buildDisplay()

  function renderMessage(item, i) {
    const { type, msg } = item

    if (type === 'coach') {
      return (
        <div key={`coach-${i}`} className="message message-coach">
          <div className="message-label">Your Coach</div>
          <div className="message-bubble">{msg.content}</div>
        </div>
      )
    }

    if (type === 'nudge') {
      return (
        <div key={`nudge-${i}`} className="message message-nudge">
          <div className="message-label">👁 Arbiter</div>
          <div className="message-bubble">{msg.content}</div>
        </div>
      )
    }

    const isMe = msg.person === person
    return (
      <div key={`thread-${i}`} className={`message ${isMe ? 'message-me' : 'message-other'}`}>
        <div className="message-label">{isMe ? cfg.label : otherCfg.label}</div>
        <div className="message-bubble">{msg.content}</div>
      </div>
    )
  }

  return (
    <div className={`person-screen accent-${cfg.color}`}>
      <header className="person-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div className="person-identity">
          <span className="person-sigil">{cfg.sigil}</span>
          <span className="person-name">{cfg.label}</span>
        </div>
        <div className="privacy-badge">
          {mode === 'coach' ? '🎓 Coach Mode' : '👁 Omniscient Mode'}
        </div>
      </header>

      <main className="messages-area">
        {display.length === 0 && !loading && (
          <div className="empty-state">
            <div className="empty-sigil">{cfg.sigil}</div>
            <p className="empty-title">Your counsel is ready</p>
            <p className="empty-sub">Start the debate. Both sides will be visible here.</p>
          </div>
        )}

        {display.map((item, i) => renderMessage(item, i))}

        {loading && (
          <div className={`message ${mode === 'coach' ? 'message-coach' : 'message-nudge'}`}>
            <div className="message-label">{mode === 'coach' ? 'Your Coach' : '👁 Arbiter'}</div>
            <div className="message-bubble typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="input-area">
        <div className="input-wrapper">
          <textarea
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={cfg.placeholder}
            rows={1}
          />
          <button className="send-btn" onClick={sendMessage} disabled={!input.trim() || loading}>
            ↑
          </button>
        </div>
        <p className="input-hint">Press Enter to send · Shift+Enter for new line</p>
      </footer>
    </div>
  )
}