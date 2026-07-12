import Card from './Card.jsx'
import './ReportCard.css'

const GRADE_COLORS = {
  A: '#4ade80',
  B: '#9be38b',
  C: '#ff7a1a',
  D: '#ff9a4d',
  F: '#fb4b4b',
}

export default function ReportCard({ report, sources = [] }) {
  if (!report) return null

  const gradeColor = GRADE_COLORS[report.trade_grade] || 'var(--signal)'
  const deltaPositive = report.win_prob_delta >= 0

  return (
    <div className="report-wrap" style={{ '--grade-color': gradeColor }}>
      <Card contentClassName="report">
        <div className="report-top">
          <div className="grade-badge">
            <svg viewBox="0 0 100 112" className="grade-shield" aria-hidden="true">
              <path
                d="M50 2 L96 18 V56 C96 84 76 102 50 110 C24 102 4 84 4 56 V18 Z"
                fill="var(--navy-3)"
                stroke="var(--grade-color)"
                strokeWidth="3"
              />
            </svg>
            <span className="grade-letter">{report.trade_grade}</span>
          </div>

          <div className="report-headline-block">
            <span className="eyebrow">Trade grade</span>
            <h2 className="report-headline">{report.headline}</h2>
            <div className={`win-delta ${deltaPositive ? 'up' : 'down'}`}>
              <span className="win-delta-arrow">{deltaPositive ? '\u25B2' : '\u25BC'}</span>
              {Math.abs(report.win_prob_delta)}% win outlook
            </div>
          </div>
        </div>

        {report.roster_fit_summary && (
          <p className="report-fit">{report.roster_fit_summary}</p>
        )}

        {report.key_stat_comparisons?.length > 0 && (
          <div className="stat-table">
            <span className="eyebrow" style={{ marginBottom: 10, display: 'inline-flex' }}>
              The breakdown
            </span>
            {report.key_stat_comparisons.map((row, i) => (
              <div className="stat-row" key={i}>
                <div className="stat-label">{row.stat}</div>
                <div className="stat-values">
                  <span className="stat-before">{row.before}</span>
                  <span className="stat-arrow">&rarr;</span>
                  <span className="stat-after">{row.after}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {report.verdict && (
          <div className="verdict">
            <span className="eyebrow" style={{ marginBottom: 8, display: 'inline-flex' }}>
              Analyst take
            </span>
            <p>{report.verdict}</p>
          </div>
        )}

        {report.historical_parallel && (
          <div className="historical-parallel">
            <span className="historical-parallel-icon">&#8635;</span>
            <p>{report.historical_parallel}</p>
          </div>
        )}

        {sources.length > 0 && (
          <div className="sources">
            <span className="eyebrow" style={{ marginBottom: 8, display: 'inline-flex' }}>
              Sources
            </span>
            <div className="sources-list">
              {sources.map((s) => (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-link" key={s.url}>
                  {s.title}
                </a>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}