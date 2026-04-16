import { useState } from 'react'
import './SurveyScreen.css'

const CONFIG = {
  a: { color: 'crimson' },
  b: { color: 'cobalt' },
}

const QUESTIONS = [
  { key: 'stance_shift', label: 'Did your stance shift during the debate?', help: '1 = Not at all, 5 = Completely changed' },
  { key: 'conversation_depth', label: 'How deep did the conversation feel?', help: '1 = Very shallow, 5 = Very deep' },
  { key: 'ai_helpfulness', label: 'How helpful was the AI assistance?', help: '1 = Not helpful, 5 = Extremely helpful' },
  { key: 'ai_utilization', label: 'How often did you engage with the AI?', help: '1 = Never, 5 = Very frequently' },
]

const OMNISCIENT_QUESTION = {
  key: 'ai_bias', label: 'Did the AI seem biased toward one side?', help: '1 = Not at all, 5 = Extremely biased'
}

export default function SurveyScreen({ person, participantName, mode, onSubmitted }) {
  const cfg = CONFIG[person]
  const questions = mode === 'omniscient' ? [...QUESTIONS, OMNISCIENT_QUESTION] : QUESTIONS

  const [answers, setAnswers] = useState(
    Object.fromEntries(questions.map(q => [q.key, null]))
  )
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function setAnswer(key, value) {
    setAnswers(prev => ({ ...prev, [key]: value }))
  }

  async function handleSubmit() {
    const unanswered = questions.filter(q => answers[q.key] === null)
    if (unanswered.length > 0) {
      setError('Please answer all questions before submitting.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`/api/survey/${person}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(answers),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setSubmitted(true)
      setTimeout(() => onSubmitted(), 2000)
    } catch (e) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className={`survey-screen accent-${cfg.color}`}>
        <div className="survey-card">
          <div className="survey-done-icon">✓</div>
          <h2 className="survey-done-title">Thank you, {participantName}</h2>
          <p className="survey-done-sub">Your responses have been recorded.</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`survey-screen accent-${cfg.color}`}>
      <div className="survey-card">
        <div className="survey-header">
          <h1 className="survey-title">Post-Debate Survey</h1>
          <p className="survey-subtitle">Please rate your experience, {participantName}.</p>
        </div>

        <div className="survey-questions">
          {questions.map(q => (
            <div key={q.key} className="survey-question">
              <div className="survey-q-label">{q.label}</div>
              <div className="survey-q-help">{q.help}</div>
              <div className="survey-scale">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    className={`scale-btn ${answers[q.key] === n ? 'selected' : ''}`}
                    onClick={() => setAnswer(q.key, n)}
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
          {loading ? 'Submitting...' : 'Submit Survey'}
        </button>
      </div>
    </div>
  )
}