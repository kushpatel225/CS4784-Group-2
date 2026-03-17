import './App.css'

export default function App({ onNavigate }) {
  return (
    <div className="landing">
      <div className="landing-header">
        <div className="ornament">✦</div>
        <h1 className="landing-title">Arbiter</h1>
        <p className="landing-subtitle">An omniscient mediator for those who cannot agree</p>
        <div className="ornament-line"><span>✦ ✦ ✦</span></div>
      </div>

      <div className="landing-cards">
        <button className="portal-card card-a" onClick={() => onNavigate('a')}>
          <div className="card-sigil">I</div>
          <div className="card-label">Person A</div>
          <div className="card-desc">State your position. Your counsel awaits.</div>
        </button>

        <div className="vs-divider">
          <div className="vs-line" />
          <span className="vs-text">vs</span>
          <div className="vs-line" />
        </div>

        <button className="portal-card card-b" onClick={() => onNavigate('b')}>
          <div className="card-sigil">II</div>
          <div className="card-label">Person B</div>
          <div className="card-desc">Present your case. Be heard completely.</div>
        </button>
      </div>

      <button className="omniscient-btn" onClick={() => onNavigate('omniscient')}>
        <span className="eye-icon">👁</span>
        <span>Enter the Omniscient View</span>
        <span className="eye-icon">👁</span>
      </button>

      <p className="landing-footer">
        Each party speaks privately. The Arbiter sees all.
      </p>
    </div>
  )
}