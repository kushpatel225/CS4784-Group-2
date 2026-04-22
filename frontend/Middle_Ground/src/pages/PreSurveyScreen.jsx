import { useState } from 'react'
import './SurveyScreen.css'

const CONFIG = {
  a: { color: 'crimson' },
  b: { color: 'cobalt' },
}

const SCALE_QUESTIONS = [
  {
    key: 'position_strength',
    label: 'How strongly do you hold your position on this topic?',
    help: '1 = Not strongly at all, 5 = Extremely strongly',
  },
  {
    key: 'openness_to_change',
    label: 'How open are you to changing your mind on this topic?',
    help: '1 = Not open at all, 5 = Very open',
  },
  {
    key: 'argument_confidence',
    label: 'How confident are you in your ability to argue your position?',
    help: '1 = Not confident, 5 = Very confident',
  },
  {
    key: 'opposing_familiarity',
    label: 'How familiar are you with the opposing viewpoint?',
    help: '1 = Not familiar at all, 5 = Very familiar',
  },
]

export default function PreSurveyScreen({ person, participantName, onCompleted }) {
  const cfg = CONFIG[person]

  const [scaleAnswers, setScaleAnswers] = useState(
    Object.fromEntries(SCALE_QUESTIONS.map(q => [q.key, null]))
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function setScale(key, value) {
    setScaleAnswers(prev => ({ ...prev, [key]: value }))
  }

  async function handleSubmit() {
    const unanswered = SCALE_QUESTIONS.filter(q => scaleAnswers[q.key] === null)
    if (unanswered.length > 0) {
      setError('Please answer all questions before continuing.')
      return
    }

    setLoading(true)
    setError('')
    
    const payload = { ...scaleAnswers }

    try {
      const res = await fetch(`/api/pre_survey/${person}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      onCompleted()
    } catch (e) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`survey-screen accent-${cfg.color}`}>
      <div className="survey-card">
        <div className="survey-header">
          <h1 className="survey-title">Pre-Debate Survey</h1>
          <p className="survey-subtitle">
            Before we begin, tell us about your current stance, {participantName}.
          </p>
        </div>

        <div className="survey-questions">
          {SCALE_QUESTIONS.map(q => (
            <div key={q.key} className="survey-question">
              <div className="survey-q-label">{q.label}</div>
              <div className="survey-q-help">{q.help}</div>
              <div className="survey-scale">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    className={`scale-btn ${scaleAnswers[q.key] === n ? 'selected' : ''}`}
                    onClick={() => setScale(q.key, n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {error && <p className="survey-error">{error}</p>}

        <button
          className="survey-submit-btn"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Begin Debate →'}
        </button>
      </div>
    </div>
  )
}