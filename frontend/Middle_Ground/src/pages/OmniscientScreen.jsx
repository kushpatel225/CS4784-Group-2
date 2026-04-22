import { useState, useRef, useEffect } from 'react'
import './OmniscientScreen.css'

export default function OmniscientScreen({ onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [nudgeTarget, setNudgeTarget] = useState('b')
  const [mode, setMode] = useState('coach')
  const [stats, setStats] = useState({ a_message_count: 0, b_message_count: 0 })
  const [context, setContext] = useState({ person_a: [], person_b: [] })
  const [showTranscripts, setShowTranscripts] = useState(true)
  const bottomRef = useRef(null)
  const [names, setNames] = useState({ a: 'Person A', b: 'Person B' })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [])

  async function fetchAll() {
    try {
      const [stateRes, contextRes] = await Promise.all([
        fetch('/api/state'),
        fetch('/api/context'),
      ])
      const stateData = await stateRes.json()
      setStats(stateData)
      setMode(stateData.mode)
      setNudgeTarget(stateData.nudge_target)
      setNames(stateData.names || { a: 'Person A', b: 'Person B' })
      setContext(await contextRes.json())
    } catch (e) {}
  }

  async function updateSettings(updates) {
    try {
      await fetch('/api/omniscient/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
    } catch (e) {}
  }

  async function handleModeToggle(newMode) {
    setMode(newMode)
    await updateSettings({ mode: newMode })
  }

  async function handleNudgeTarget(target) {
    setNudgeTarget(target)
    await updateSettings({ nudge_target: target })
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
        body: JSON.stringify({ message: text, target: nudgeTarget }),
      })
      const data = await res.json()
      const meta = `Nudging toward Person ${data.target.toUpperCase()}'s view · A: ${data.has_context_a ? '✓' : '—'} · B: ${data.has_context_b ? '✓' : '—'}`
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, meta }])
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

  async function handleReset() {
    if (!confirm('Reset all debate data?')) return
    await fetch('/api/reset', { method: 'POST' })
    setMessages([])
    setStats({ a_message_count: 0, b_message_count: 0 })
    setContext({ person_a: [], person_b: [] })
  }

  function renderTranscript(history, label) {
    const userOnly = history.filter(m => m.role === 'user')
    if (userOnly.length === 0) return <p className="transcript-empty">No messages yet.</p>
    return userOnly.map((m, i) => (
      <div key={i} className="transcript-msg">
        <span className="transcript-label">{label}:</span> {m.content}
      </div>
    ))
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

      {/* Mode toggle: Coach vs Omniscient */}
      <div className="mode-toggle-bar">
        <button
          className={`mode-btn ${mode === 'none' ? 'active' : ''}`}
          onClick={() => handleModeToggle('none')}
        >
          🚫 No AI
        </button>
        <button
          className={`mode-btn ${mode === 'coach' ? 'active' : ''}`}
          onClick={() => handleModeToggle('coach')}
        >
          🎓 Personal Coach
        </button>
        <button
          className={`mode-btn ${mode === 'omniscient' ? 'active' : ''}`}
          onClick={() => handleModeToggle('omniscient')}
        >
          👁 Omniscient
        </button>
      </div>

      {/* Nudge direction — only relevant in omniscient mode */}
      {mode === 'omniscient' && (
        <div className="target-selector">
          <span className="target-label">Nudge everyone toward:</span>
          <div className="target-options">
            <button
              className={`target-btn ${nudgeTarget === 'a' ? 'active' : ''}`}
              onClick={() => handleNudgeTarget('a')}
            >
              Person A's view
            </button>
            <button
              className={`target-btn ${nudgeTarget === 'b' ? 'active' : ''}`}
              onClick={() => handleNudgeTarget('b')}
            >
              Person B's view
            </button>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="stats-bar">
        <div className="stat">
          <span className="stat-label">{names.a}</span>
          <span className="stat-count">{stats.a_message_count} msgs</span>
        </div>
        <div className="stat-divider">|</div>
        <div className="stat">
          <span className="stat-label">{names.b}</span>
          <span className="stat-count">{stats.b_message_count} msgs</span>
        </div>
        <div className="stat-divider">·</div>
        <div className="stat">
          <span className="stat-label">Mode</span>
          <span className="stat-count">{mode === 'coach' ? 'Personal Coach' : `Omniscient → ${nudgeTarget.toUpperCase()}`}</span>
        </div>
      </div>

      {/* Live transcripts */}
      <div className="transcripts-toggle" onClick={() => setShowTranscripts(p => !p)}>
        <span>Live Transcripts</span>
        <span className="toggle-counts">A: {stats.a_message_count} · B: {stats.b_message_count}</span>
        <span className="toggle-arrow">{showTranscripts ? '▲' : '▼'}</span>
      </div>

      {showTranscripts && (
        <div className="transcripts-panel">
          <div className="transcript-col transcript-a">
            <div className="transcript-header">Person A</div>
            {renderTranscript(context.person_a, names.a)}
          </div>
          <div className="transcript-divider" />
          <div className="transcript-col transcript-b">
            <div className="transcript-header">Person B</div>
            {renderTranscript(context.person_b, names.b)}
          </div>
        </div>
      )}

      {/* Arbiter manual chat */}
      <main className="omni-messages">
        {messages.length === 0 && (
          <div className="omni-empty">
            <div className="omni-empty-glyph">👁</div>
            <p className="omni-empty-title">All truths are known here</p>
            <p className="omni-empty-sub">
              {mode === 'none'
                ? 'No AI mode — pure debate between the two participants.'
                : mode === 'coach'
                ? 'Personal Coach mode — each person gets private coaching.'
                : `Omniscient mode — nudging both toward Person ${nudgeTarget.toUpperCase()}'s view.`}
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
            <div className="omni-msg-bubble typing"><span /><span /><span /></div>
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
            placeholder="Send a manual instruction to the Arbiter..."
            rows={1}
          />
          <button className="omni-send-btn" onClick={sendMessage} disabled={!input.trim() || loading}>↑</button>
        </div>
        <p className="input-hint">Manual override — the Arbiter will use full context from both sides.</p>
      </footer>
    </div>
  )
}