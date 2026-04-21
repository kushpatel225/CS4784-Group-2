import './App.css'

export default function App({ onNavigate }) {
  return (
    <div className="landing">
      <div className="landing-header">
        <div className="ornament">✦</div>
        <h1 className="landing-title">Arbiter</h1>
        <div className="ornament-line"><span>✦ ✦ ✦</span></div>
      </div>

      <div className="landing-cards">
        <button className="portal-card card-a" onClick={() => onNavigate('a')}>
          <div className="card-sigil">I</div>
          <div className="card-label">Go first.</div>
        </button>

        <div className="vs-divider">
          <div className="vs-line" />
          <span className="vs-text">vs</span>
          <div className="vs-line" />
        </div>

        <button className="portal-card card-b" onClick={() => onNavigate('b')}>
          <div className="card-sigil">II</div>
          <div className="card-label">Go second.</div>
        </button>
      </div>

      <button className="omniscient-btn" onClick={() => onNavigate('omniscient')}>
        <span className="eye-icon">👁</span>
        <span>Admin Page</span>
        <span className="eye-icon">👁</span>
      </button>
    </div>
  )
}