import { useState, useRef, useEffect } from 'react'
import './PersonScreen.css'

const CONFIG = {
  a: {
    label: 'Person A',
    sigil: 'I',
    color: 'crimson',
    placeholder: 'State your position...',
    endpoint: '/api/chat/a',
  },
  b: {
    label: 'Person B',
    sigil: 'II',
    color: 'cobalt',
    placeholder: 'Present your argument...',
    endpoint: '/api/chat/b',
  },
}

export default function PersonScreen({ person, onBack }) {
  const cfg = CONFIG[person]
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(cfg.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Please try again.' }])
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

  return (
    <div className={`person-screen accent-${cfg.color}`}>
      <header className="person-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div className="person-identity">
          <span className="person-sigil">{cfg.sigil}</span>
          <span className="person-name">{cfg.label}</span>
        </div>
        <div className="privacy-badge">🔒 Private</div>
      </header>

      <main className="messages-area">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-sigil">{cfg.sigil}</div>
            <p className="empty-title">Your counsel is ready</p>
            <p className="empty-sub">Speak freely. Your words are heard only here.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <div className="message-label">
              {msg.role === 'user' ? cfg.label : 'Counsel'}
            </div>
            <div className="message-bubble">{msg.content}</div>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant">
            <div className="message-label">Counsel</div>
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