import { useState } from 'react'
import './ConsentScreen.css'

const CONFIG = {
  a: { label: 'Person A', sigil: 'I', color: 'crimson' },
  b: { label: 'Person B', sigil: 'II', color: 'cobalt' },
}

export default function ConsentScreen({ person, onBack, onConsented }) {
  const cfg = CONFIG[person]
  const [name, setName] = useState('')
  const [consented, setConsented] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!name.trim()) { setError('Please enter your name.'); return }
    if (!consented) { setError('Please check the consent box to continue.'); return }

    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person, name: name.trim(), consented }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      onConsented(name.trim())
    } catch (e) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div className={`consent-screen accent-${cfg.color}`}>
      <button className="consent-back-btn" onClick={onBack}>← Back</button>
      <div className="consent-card">
        <div className="consent-sigil">{cfg.sigil}</div>
        <h1 className="consent-title">Welcome</h1>
        <p className="consent-subtitle">Before the debate begins, please provide your name and consent.</p>

        <div className="consent-field">
          <label className="consent-label">Your name</label>
          <input
            className="consent-input"
            type="text"
            placeholder="Enter your name..."
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={handleKey}
            autoFocus
          />
        </div>

        <div className="consent-box">
          <label className="consent-check-label">
            <input
              type="checkbox"
              checked={consented}
              onChange={e => setConsented(e.target.checked)}
              className="consent-checkbox"
            />
            <span>I consent to my responses being recorded for research purposes.</span>
          </label>
        </div>

        {error && <p className="consent-error">{error}</p>}

        <button className="consent-btn" onClick={handleSubmit} disabled={loading}>
          {loading ? 'Registering...' : 'Enter Debate'}
        </button>
      </div>
    </div>
  )
}