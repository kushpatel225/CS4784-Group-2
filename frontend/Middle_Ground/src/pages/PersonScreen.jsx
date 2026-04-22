import { useState, useRef, useEffect } from 'react'
import ConsentScreen from './ConsentScreen.jsx'
import PreSurveyScreen from './PreSurveyScreen.jsx'
import SurveyScreen from './SurveyScreen.jsx'
import './PersonScreen.css'

const CONFIG = {
  a: { label: 'Person A', sigil: 'I', color: 'crimson', placeholder: 'State your position...', endpoint: '/api/chat/a' },
  b: { label: 'Person B', sigil: 'II', color: 'cobalt', placeholder: 'Present your argument...', endpoint: '/api/chat/b' },
}

const MAX_MESSAGES = 10
const MIN_MESSAGES = 4

export default function PersonScreen({ person, onBack }) {
  const cfg = CONFIG[person]
  const otherCfg = CONFIG[person === 'a' ? 'b' : 'a']

  const [consented, setConsented] = useState(null)
  const [preSurveyDone, setPreSurveyDone] = useState(false)
  const [participantName, setParticipantName] = useState('')
  const [thread, setThread] = useState([])
  const [mode, setMode] = useState('coach')
  const [input, setInput] = useState('')
  const [sideInput, setSideInput] = useState('')
  const [sideMessages, setSideMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sideLoading, setSideLoading] = useState(false)
  const [messageCount, setMessageCount] = useState(0)
  const [allMessageCounts, setAllMessageCounts] = useState({ a: 0, b: 0 })
  const [debateEnded, setDebateEnded] = useState(false)
  const [showSurvey, setShowSurvey] = useState(false)
  const [endingDebate, setEndingDebate] = useState(false)
  const [otherName, setOtherName] = useState('')
  const bottomRef = useRef(null)
  const sideBottomRef = useRef(null)
  const prevThreadLen = useRef(0)

  useEffect(() => {
    async function checkRegistration() {
      try {
        const res = await fetch('/api/state')
        const data = await res.json()
        const defaultName = person === 'a' ? 'Person A' : 'Person B'
        const storedName = data.names?.[person]
        if (storedName && storedName !== defaultName) {
          setParticipantName(storedName)
          setConsented(true)
          setPreSurveyDone(data.pre_survey_done?.[person] || false)
        } else {
          setConsented(false)
        }
        if (data.debate_ended) {
          setDebateEnded(true)
          setShowSurvey(true)
        }
      } catch (e) {
        setConsented(false)
      }
    }
    checkRegistration()
  }, [])

  useEffect(() => {
    if (thread.length > prevThreadLen.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      prevThreadLen.current = thread.length
    }
  }, [thread])

  useEffect(() => {
    sideBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sideMessages])

  useEffect(() => {
    if (!consented || !preSurveyDone) return
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [consented, preSurveyDone])

  const seenAutoIds = useRef(new Set())

  async function fetchAll() {
    try {
      const [threadRes, stateRes] = await Promise.all([
        fetch('/api/thread'),
        fetch('/api/state'),
      ])
      const threadData = await threadRes.json()
      const stateData = await stateRes.json()
      const thread = threadData.thread || []
      setThread(thread)
      setMode(threadData.mode || 'coach')
      setMessageCount(stateData.message_counts?.[person] || 0)
      setAllMessageCounts(stateData.message_counts || { a: 0, b: 0 })
      setOtherName(stateData.names?.[person === 'a' ? 'b' : 'a'] || otherCfg.label)
      if (threadData.debate_ended && !debateEnded) {
        setDebateEnded(true)
        setShowSurvey(true)
      }
      thread.forEach((msg, idx) => {
        if (msg.role === 'auto_side' && msg.target === person && !seenAutoIds.current.has(idx)) {
          seenAutoIds.current.add(idx)
          setSideMessages(prev => [...prev, { role: 'assistant', content: msg.content, auto: true }])
        }
      })
    } catch (e) {}
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading || messageCount >= MAX_MESSAGES || debateEnded) return
    setInput('')
    setLoading(true)
    try {
      const res = await fetch(cfg.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      if (data.error) { alert(data.error); return }
      setMessageCount(data.count || messageCount + 1)

      if (data.auto_reply) {
        setSideMessages(prev => [...prev, {
          role: 'assistant',
          content: data.auto_reply,
          auto: true
        }])
      }
      await fetchAll()
    } catch (e) {
      console.error('Send error:', e)
    } finally {
      setLoading(false)
    }
  }

  async function sendSideMessage() {
    const text = sideInput.trim()
    if (!text || sideLoading) return
    setSideMessages(prev => [...prev, { role: 'user', content: text }])
    setSideInput('')
    setSideLoading(true)
    try {
      const res = await fetch(`/api/sidepanel/${person}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      setSideMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch (e) {
      setSideMessages(prev => [...prev, { role: 'assistant', content: 'Connection error.' }])
    } finally {
      setSideLoading(false)
    }
  }

  async function endDebate() {
    if (!confirm('End the debate for both participants? This cannot be undone.')) return
    setEndingDebate(true)
    try {
      await fetch('/api/end', { method: 'POST' })
      setDebateEnded(true)
      setShowSurvey(true)
    } catch (e) {
      console.error('End debate error:', e)
    } finally {
      setEndingDebate(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  function handleSideKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendSideMessage() }
  }

  const limitReached = messageCount >= MAX_MESSAGES
  const minTurnsMet = allMessageCounts.a >= MIN_MESSAGES && allMessageCounts.b >= MIN_MESSAGES

  if (consented === null) return null

  if (!consented) {
    return (
      <ConsentScreen
        person={person}
        onBack={onBack}
        onConsented={name => {
          setParticipantName(name)
          setConsented(true)
        }}
      />
    )
  }

  if (!preSurveyDone) {
    return (
      <PreSurveyScreen
        person={person}
        participantName={participantName}
        onCompleted={() => setPreSurveyDone(true)}
      />
    )
  }

  if (showSurvey) {
    return (
      <SurveyScreen
        person={person}
        participantName={participantName}
        mode={mode}
        onSubmitted={onBack}
      />
    )
  }

  return (
    <div className={`person-screen accent-${cfg.color}`}>
      <header className="person-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div className="person-identity">
          <span className="person-sigil">{cfg.sigil}</span>
          <span className="person-name">{participantName}</span>
        </div>
        <div className="header-right">
          <div className="privacy-badge">{mode === 'none' ? 'No AI' : 'AI Assisted'}</div>
          <div className={`msg-counter ${limitReached ? 'limit' : ''}`}>{messageCount}/{MAX_MESSAGES}</div>
          <button className="end-btn" onClick={endDebate} disabled={endingDebate || debateEnded || !minTurnsMet} title={!minTurnsMet ? `Both participants must send at least ${MIN_MESSAGES} messages before ending` : ''}>
            {endingDebate ? 'Ending...' : !minTurnsMet ? `Min ${MIN_MESSAGES} turns required` : 'End Debate'}
          </button>
        </div>
      </header>

      <div className="screen-body">
        <div className="main-panel">
          <main className="messages-area">
            {thread.filter(m => m.role === 'user').length === 0 && !loading && (
              <div className="empty-state">
                <div className="empty-sigil">{cfg.sigil}</div>
                <p className="empty-title">Welcome, {participantName}</p>
                <p className="empty-sub">Start the debate. Both sides will appear here.</p>
              </div>
            )}

            {thread.map((msg, i) => {
              if (msg.role !== 'user') return null
              const isMe = msg.person === person
              return (
                <div key={i} className={`message ${isMe ? 'message-me' : 'message-other'}`}>
                  <div className="message-label">{isMe ? participantName : otherName}</div>
                  <div className="message-bubble">{msg.content}</div>
                </div>
              )
            })}

            {loading && (
              <div className="message message-me">
                <div className="message-label">{participantName}</div>
                <div className="message-bubble typing"><span /><span /><span /></div>
              </div>
            )}

            <div ref={bottomRef} />
          </main>

          <footer className="input-area">
            {debateEnded ? (
              <div className="limit-banner">The debate has ended.</div>
            ) : limitReached ? (
              <div className="limit-banner">You have reached the maximum of {MAX_MESSAGES} messages.</div>
            ) : (
              <>
                <div className="input-wrapper">
                  <textarea
                    className="chat-input"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder={cfg.placeholder}
                    rows={1}
                  />
                  <button className="send-btn" onClick={sendMessage} disabled={!input.trim() || loading}>↑</button>
                </div>
                <p className="input-hint">Press Enter to send · Shift+Enter for new line</p>
              </>
            )}
          </footer>
        </div>

        {mode !== 'none' && (
          <div className="side-panel">
            <div className="side-panel-header">
              Your Assistant
            </div>
            <div className="side-messages">
              {sideMessages.length === 0 && (
                <p className="side-empty">Ask your assistant anything, or wait for automatic responses.</p>
              )}
              {sideMessages.map((msg, i) => (
                <div key={i} className={`side-msg side-msg-${msg.role}`}>
                  <div className="side-msg-label">
                    {msg.role === 'user' ? participantName : msg.auto ? '⚡ Auto' : 'Assistant'}
                  </div>
                  <div className="side-msg-bubble">{msg.content}</div>
                </div>
              ))}
              {sideLoading && (
                <div className="side-msg side-msg-assistant">
                  <div className="side-msg-label">Assistant</div>
                  <div className="side-msg-bubble typing"><span /><span /><span /></div>
                </div>
              )}
              <div ref={sideBottomRef} />
            </div>
            <div className="side-input-area">
              <textarea
                className="side-input"
                value={sideInput}
                onChange={e => setSideInput(e.target.value)}
                onKeyDown={handleSideKey}
                placeholder="Ask a question..."
                rows={1}
              />
              <button className="side-send-btn" onClick={sendSideMessage} disabled={!sideInput.trim() || sideLoading}>↑</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}