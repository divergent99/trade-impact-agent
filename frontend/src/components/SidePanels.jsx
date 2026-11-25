import { GRADE_COLORS, gradeColor, timeAgo } from '../lib/format.js'
import { teamByValue } from '../lib/teams.js'

const SCALE = [
  { g: 'A', text: 'Franchise-altering win' },
  { g: 'B', text: 'Clear upgrade, some cost' },
  { g: 'C', text: 'Lateral or unclear' },
  { g: 'D', text: 'Overpaid or poor fit' },
  { g: 'F', text: 'Sets the team back' },
]

export function HistoryPanel({ history, activeId, onSelect, onClear, disabled }) {
  return (
    <section className="side-card" aria-label="Recent analyses">
      <div className="side-head">
        <span className="eyebrow">Recent</span>
        {history.length > 0 && (
          <button type="button" className="link-btn" onClick={onClear} disabled={disabled}>
            Clear
          </button>
        )}
      </div>
      {history.length === 0 ? (
        <div className="side-empty">
          <div className="side-empty-shields" aria-hidden="true">
            {['A', 'C', 'F'].map((g) => (
              <span key={g} style={{ color: GRADE_COLORS[g], borderColor: `${GRADE_COLORS[g]}55` }}>
                {g}
              </span>
            ))}
          </div>
          <p>Graded trades land here so you can flip back without re-running them.</p>
        </div>
      ) : (
        <ul className="history-list">
          {history.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                className={`history-item${h.id === activeId ? ' active' : ''}`}
                onClick={() => onSelect(h)}
                disabled={disabled}
                title={h.description}
              >
                <span className="history-grade" style={{ color: gradeColor(h.report.trade_grade) }}>
                  {h.report.trade_grade}
                </span>
                <span className="history-body">
                  <span className="history-desc">{h.description}</span>
                  <span className="history-meta">
                    {teamByValue(h.team)?.abbr || h.team} &middot; {timeAgo(h.at)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function GradeGuide() {
  return (
    <section className="side-card guide" aria-label="How to read a grade">
      <div className="side-head">
        <span className="eyebrow">Reading the grade</span>
      </div>
      <ul className="scale">
        {SCALE.map((s) => (
          <li key={s.g}>
            <span className="scale-grade" style={{ color: GRADE_COLORS[s.g], background: `${GRADE_COLORS[s.g]}14`, borderColor: `${GRADE_COLORS[s.g]}44` }}>
              {s.g}
            </span>
            <span>{s.text}</span>
          </li>
        ))}
      </ul>
      <dl className="guide-defs">
        <div>
          <dt>Win outlook</dt>
          <dd>Estimated swing in season win odds, in percentage points.</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>How much real data backed the grade. Missing stats or failed lookups lower it.</dd>
        </div>
        <div>
          <dt>Other side</dt>
          <dd>Same deal, graded for the team across the table.</dd>
        </div>
      </dl>
    </section>
  )
}

const STEPS = [
  {
    title: 'Pull rosters',
    text: 'Both teams, current depth chart from balldontlie.',
    icon: (
      <path d="M4 6h16M4 12h16M4 18h10" strokeLinecap="round" />
    ),
  },
  {
    title: 'Check the players',
    text: 'Season averages and injury status for the mover and the incumbents affected.',
    icon: (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M5 20c1.2-3.6 3.8-5.5 7-5.5s5.8 1.9 7 5.5" strokeLinecap="round" />
      </>
    ),
  },
  {
    title: 'Read the room',
    text: 'Recent news and reactions, cited as sources.',
    icon: (
      <>
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <path d="M8 9h8M8 13h8M8 17h5" strokeLinecap="round" />
      </>
    ),
  },
  {
    title: 'Grade it',
    text: 'Letter grade, win swing, pros, risks and the other side of the deal.',
    icon: <path d="M12 3l8 3v6c0 4.5-3.4 7.7-8 9-4.6-1.3-8-4.5-8-9V6l8-3z" strokeLinejoin="round" />,
  },
]

export function HowItWorks() {
  return (
    <section className="how" aria-label="How it works">
      <div className="section-head">
        <span className="eyebrow">What the agent does</span>
        <span className="section-meta">~20-40s per trade</span>
      </div>
      <ol className="how-grid">
        {STEPS.map((s, i) => (
          <li className="how-step" key={s.title}>
            <div className="how-top">
              <svg viewBox="0 0 24 24" className="how-icon" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
                {s.icon}
              </svg>
              <span className="how-num">0{i + 1}</span>
            </div>
            <div className="how-title">{s.title}</div>
            <p>{s.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
