import { useState, useRef, useEffect } from 'react'
import './OmniscientScreen.css'

export default function OmniscientScreen({ onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [target, setTarget] = useState('b')
  const [stats, setStats] = useState({ a_message_count: 0, b_message_count: 0 })
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  async function fetchStats() {
    try {
      const res = await fetch('/api/state')
      const data = await res.json()
      setStats(data)
    } catch (e) {}
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/omniscient/persuade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, target }),
      })
      const data = await res.json()
      const meta = `Persuading Person ${data.target.toUpperCase()} · Context from A: ${data.has_context_a ? '✓' : '—'} · Context from B: ${data.has_context_b ? '✓' : '—'}`
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, meta }])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Please try again.' }])
    } finally {
      setLoading(false)
      fetchStats()
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  async function handleReset() {
    if (!confirm('Reset all debate data?')) return
    await fetch('/api/reset', { method: 'POST' })
    setMessages([])
    setStats({ a_message_count: 0, b_message_count: 0 })
  }

  return (
    <div className="omni-screen">
      <header className="omni-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div className="omni-identity">
          <span className="omni-eye">👁</span>
          <span className="omni-title">Omniscient</span>
        </div>
        <button className="reset-btn" onClick={handleReset}>Reset</button>
      </header>

      <div className="stats-bar">
        <div className="stat">
          <span className="stat-label">Person A</span>
          <span className="stat-count">{stats.a_message_count} msg{stats.a_message_count !== 1 ? 's' : ''}</span>
        </div>
        <div className="stat-divider">|</div>
        <div className="stat">
          <span className="stat-label">Person B</span>
          <span className="stat-count">{stats.b_message_count} msg{stats.b_message_count !== 1 ? 's' : ''}</span>
        </div>
        <div className="stat-divider">·</div>
        <div className="stat">
          <span className="stat-label">All data visible</span>
        </div>
      </div>

      <div className="target-selector">
        <span className="target-label">Persuade toward:</span>
        <div className="target-options">
          <button className={`target-btn ${target === 'a' ? 'active' : ''}`} onClick={() => setTarget('a')}>
            Person A's view
          </button>
          <button className={`target-btn ${target === 'b' ? 'active' : ''}`} onClick={() => setTarget('b')}>
            Person B's view
          </button>
        </div>
      </div>

      <main className="omni-messages">
        {messages.length === 0 && (
          <div className="omni-empty">
            <div className="omni-empty-glyph">👁</div>
            <p className="omni-empty-title">All truths are known here</p>
            <p className="omni-empty-sub">
              Ask the Arbiter to craft a persuasive argument.<br />
              It has seen everything from both sides.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`omni-msg omni-msg-${msg.role}`}>
            <div className="omni-msg-label">{msg.role === 'user' ? 'Operator' : 'The Arbiter'}</div>
            <div className="omni-msg-bubble">{msg.content}</div>
            {msg.meta && <div className="omni-msg-meta">{msg.meta}</div>}
          </div>
        ))}

        {loading && (
          <div className="omni-msg omni-msg-assistant">
            <div className="omni-msg-label">The Arbiter</div>
            <div className="omni-msg-bubble typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="omni-input-area">
        <div className="omni-input-wrapper">
          <textarea
            className="omni-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask the Arbiter to formulate a persuasion strategy..."
            rows={1}
          />
          <button className="omni-send-btn" onClick={sendMessage} disabled={!input.trim() || loading}>
            ↑
          </button>
        </div>
        <p className="input-hint">The Arbiter reads all conversations before responding.</p>
      </footer>
    </div>
  )
}