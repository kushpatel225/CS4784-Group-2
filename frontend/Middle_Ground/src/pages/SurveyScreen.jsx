import { useState } from 'react'
import './SurveyScreen.css'

const CONFIG = {
  a: { color: 'crimson' },
  b: { color: 'cobalt' },
}

const BASE_QUESTIONS = [
  { key: 'position_strength_now', label: 'How strongly do you now hold your position on this topic?', help: '1 = Not strongly at all, 5 = Extremely strongly', type: 'scale' },
  { key: 'position_shift', label: 'How much did your position shift during the conversation?', help: '1 = Not at all, 5 = Completely changed', type: 'scale' },
  { key: 'shift_reason', label: 'If your position shifted, what was the primary reason?', type: 'open', condition: (a) => a.position_shift > 1 },
  { key: 'conversation_productive', label: 'How productive did the conversation feel overall?', help: '1 = Not productive, 5 = Very productive', type: 'scale' },
  { key: 'felt_heard', label: 'Did you feel heard by the other participant?', help: '1 = Not at all, 5 = Completely', type: 'scale' },
  { key: 'new_information', label: "Did any new information or arguments come up that you hadn't considered before?", options: ['Yes', 'No'], type: 'choice' },
  { key: 'new_info_influence', label: 'Did that information influence your thinking?', help: '1 = Not at all, 5 = Significantly', type: 'scale', condition: (a) => a.new_information === 'Yes' },
  { key: 'comfort_expressing', label: 'How comfortable were you expressing your views?', help: '1 = Very uncomfortable, 5 = Very comfortable', type: 'scale' },
  { key: 'opposing_persuasive', label: 'How persuasive did you find the opposing argument?', help: '1 = Not persuasive at all, 5 = Very persuasive', type: 'scale' },
]

// Q13 — coach + omniscient (scale)
const AI_SCALE_QUESTIONS = [
  {
    key: 'assistance_forward',
    label: 'How helpful was the outside assistance in moving the conversation forward?',
    help: '1 = Not helpful at all, 5 = Extremely helpful',
    type: 'scale',
  },
]

// Q14 — coach + omniscient (Yes / No / Somewhat)
const AI_YNS_QUESTIONS = [
  {
    key: 'assistance_new_perspectives',
    label: 'Did the assistance introduce any information or perspectives you hadn\'t considered?',
    options: ['Yes', 'No', 'Somewhat'],
    type: 'choice',
  },
]

// Q15 — coach + omniscient (More / Less / No difference)
const AI_ENGAGEMENT_QUESTIONS = [
  {
    key: 'assistance_engagement',
    label: 'Did the assistance make you more or less willing to engage with the opposing viewpoint?',
    options: ['More', 'Less', 'No difference'],
    type: 'choice',
  },
]

// Q16 — coach + omniscient (Yes / No / Unsure)
const AI_REACHED_DEPTH = [
  {
    key: 'reached_depth',
    label: 'Did the conversation reach a depth you don\'t think it would have on its own?',
    options: ['Yes', 'No', 'Unsure'],
    type: 'choice',
  },
]

// Q17 — omniscient only (scale 1–5 with custom labels)
const OMNISCIENT_BIAS_QUESTION = {
  key: 'ai_bias',
  label: 'Did the assistance seem to favor one side over the other?',
  help: '1 = Strongly favored my opponent, 3 = Neutral, 5 = Strongly favored me',
  type: 'scale',
}

export default function SurveyScreen({ person, participantName, mode, onSubmitted }) {
  const cfg = CONFIG[person]
  const isAI = mode === 'coach' || mode === 'omniscient'
  const isOmniscient = mode === 'omniscient'

  // Build the full question list based on mode
  const allQuestions = [
    ...BASE_QUESTIONS,
    ...(isAI ? AI_SCALE_QUESTIONS : []),
    ...(isAI ? AI_YNS_QUESTIONS : []),
    ...(isAI ? AI_ENGAGEMENT_QUESTIONS : []),
    ...(isAI ? AI_REACHED_DEPTH : []),
    ...(isOmniscient ? [OMNISCIENT_BIAS_QUESTION] : []),
  ]

  const [answers, setAnswers] = useState(
    Object.fromEntries(allQuestions.map(q => [q.key, q.type === 'open' ? '' : null]))
  )
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function setAnswer(key, value) {
    setAnswers(prev => ({ ...prev, [key]: value }))
  }

  async function handleSubmit() {
    const unanswered = allQuestions
      .filter(q => !q.condition || q.condition(answers))
      .filter(q => q.type === 'open' ? !answers[q.key]?.trim() : answers[q.key] === null)
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
          {allQuestions.filter(q => !q.condition || q.condition(answers)).map(q => (
          <div key={q.key} className="survey-question">
            <div className="survey-q-label">{q.label}</div>
            {q.type === 'scale' && (
              <>
                <div className="survey-q-help">{q.help}</div>
                <div className="survey-scale">
                  {[1,2,3,4,5].map(n => (
                    <button key={n} className={`scale-btn ${answers[q.key] === n ? 'selected' : ''}`} onClick={() => setAnswer(q.key, n)}>{n}</button>
                  ))}
                </div>
              </>
            )}
            {q.type === 'choice' && (
              <div className="survey-scale">
                {q.options.map(opt => (
                  <button key={opt} className={`scale-btn scale-btn--text ${answers[q.key] === opt ? 'selected' : ''}`} onClick={() => setAnswer(q.key, opt)}>{opt}</button>
                ))}
              </div>
            )}
            {q.type === 'open' && (
              <textarea className="survey-textarea" value={answers[q.key]} onChange={e => setAnswer(q.key, e.target.value)} placeholder="Describe in your own words..." rows={3} />
            )}
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