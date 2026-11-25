import { useState } from 'react'
import Card from './Card.jsx'
import { copyText, gradeColor, reportToText } from '../lib/format.js'
import { teamByValue } from '../lib/teams.js'
import './ReportCard.css'

function GradeShield({ grade, size = 'lg' }) {
  return (
    <div className={`grade-badge grade-${size}`} style={{ '--grade-color': gradeColor(grade) }}>
      <svg viewBox="0 0 100 112" className="grade-shield" aria-hidden="true">
        <path
          d="M50 2 L96 18 V56 C96 84 76 102 50 110 C24 102 4 84 4 56 V18 Z"
          fill="var(--navy-3)"
          stroke="var(--grade-color)"
          strokeWidth="3"
        />
      </svg>
      <span className="grade-letter" aria-label={`Grade ${grade}`}>
        {grade}
      </span>
    </div>
  )
}

function Confidence({ level }) {
  const n = { low: 1, medium: 2, high: 3 }[level] || 2
  return (
    <span className={`pill confidence conf-${level}`} title="How well the pulled data supports this grade">
      <span className="conf-bars" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <span key={i} className={i <= n ? 'on' : ''} />
        ))}
      </span>
      {level} confidence
    </span>
  )
}

function WinMeter({ delta }) {
  // -20..+20 maps onto the bar; bigger swings pin to the end
  const span = (Math.min(Math.abs(delta), 20) / 20) * 50
  return (
    <div className="win-meter" aria-hidden="true">
      <div className="win-meter-track">
        <span className="win-meter-mid" />
        <span
          className={`win-meter-fill ${delta >= 0 ? 'up' : 'down'}`}
          style={delta >= 0 ? { left: '50%', width: `${span}%` } : { right: '50%', width: `${span}%` }}
        />
      </div>
      <div className="win-meter-labels">
        <span>-20</span>
        <span>0</span>
        <span>+20</span>
      </div>
    </div>
  )
}

function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

export function ReportSkeleton({ caption = 'Writing the report' }) {
  return (
    <div className="report-wrap">
      <Card contentClassName="report">
        <div className="report-top">
          <div className="skel skel-shield" />
          <div className="report-headline-block">
            <div className="skel skel-line" style={{ width: '30%' }} />
            <div className="skel skel-line lg" style={{ width: '85%' }} />
            <div className="skel skel-line" style={{ width: '45%' }} />
          </div>
        </div>
        <div className="skel-para">
          <div className="skel skel-line" />
          <div className="skel skel-line" />
          <div className="skel skel-line" style={{ width: '70%' }} />
        </div>
        <div className="skel-split">
          <div className="skel skel-block" />
          <div className="skel skel-block" />
        </div>
        <p className="skel-caption">
          <span className="tl-spinner" /> {caption}
        </p>
      </Card>
    </div>
  )
}

export default function ReportCard({ report, sources = [], team, description, onRerun, shareUrl }) {
  const [copied, setCopied] = useState(null)
  if (!report) return null

  const delta = Number(report.win_prob_delta) || 0
  const teamInfo = teamByValue(team)

  async function copy(kind) {
    const ok = await copyText(kind === 'link' ? shareUrl : reportToText({ team: teamInfo?.label || team, description, report, sources }))
    setCopied(ok ? kind : 'fail')
    setTimeout(() => setCopied(null), 1800)
  }

  return (
    <div className="report-wrap" style={{ '--grade-color': gradeColor(report.trade_grade) }}>
      <Card contentClassName="report">
        <div className="report-move">
          <span className="report-team-tag" style={{ '--team-color': teamInfo?.color || 'var(--signal)' }}>
            {teamInfo?.abbr || team}
          </span>
          <span className="report-move-text">{description}</span>
        </div>

        <div className="report-top">
          <GradeShield grade={report.trade_grade} />
          <div className="report-headline-block">
            <span className="eyebrow">Grade for the {teamInfo?.label || team}</span>
            <h2 className="report-headline">{report.headline}</h2>
            <div className="report-pills">
              <span className={`pill win-delta ${delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'}`}>
                <span aria-hidden="true">{delta > 0 ? '▲' : delta < 0 ? '▼' : '◆'}</span>
                {delta > 0 ? '+' : ''}
                {delta} pts win outlook
              </span>
              <Confidence level={report.confidence} />
            </div>
            <WinMeter delta={delta} />
          </div>
        </div>

        {report.counterpart && (
          <div className="counterpart">
            <GradeShield grade={report.counterpart.grade} size="sm" />
            <div>
              <div className="counterpart-team">Other side: {report.counterpart.team}</div>
              <p>{report.counterpart.take}</p>
            </div>
          </div>
        )}

        {report.roster_fit_summary && <p className="report-fit">{report.roster_fit_summary}</p>}

        {(report.pros?.length > 0 || report.cons?.length > 0) && (
          <div className="pros-cons">
            <div className="pc-col pros">
              <span className="pc-title">Upside</span>
              <ul>
                {report.pros?.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
            <div className="pc-col cons">
              <span className="pc-title">Risks</span>
              <ul>
                {report.cons?.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {report.key_stat_comparisons?.length > 0 && (
          <div className="section">
            <span className="eyebrow section-title">The breakdown</span>
            <div className="stat-table" role="table">
              <div className="stat-row stat-head" role="row">
                <span role="columnheader">Metric</span>
                <span role="columnheader">Before</span>
                <span aria-hidden="true" />
                <span role="columnheader">After</span>
              </div>
              {report.key_stat_comparisons.map((row, i) => (
                <div className="stat-row" role="row" key={i}>
                  <span className="stat-label" role="cell">
                    {row.stat}
                  </span>
                  <span className="stat-before" role="cell">
                    {row.before}
                  </span>
                  <span className="stat-arrow" aria-hidden="true">
                    &rarr;
                  </span>
                  <span className="stat-after" role="cell">
                    {row.after}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {report.verdict && (
          <div className="section verdict">
            <span className="eyebrow section-title">Analyst take</span>
            <p>{report.verdict}</p>
          </div>
        )}

        {report.historical_parallel && (
          <div className="historical-parallel">
            <span className="historical-parallel-icon" aria-hidden="true">
              &#8635;
            </span>
            <p>{report.historical_parallel}</p>
          </div>
        )}

        {sources.length > 0 && (
          <div className="section sources">
            <span className="eyebrow section-title">Sources</span>
            <ul className="sources-list">
              {sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-link">
                    <span className="source-title">{s.title}</span>
                    <span className="source-domain">
                      {domainOf(s.url)}
                      {s.published ? ` · ${String(s.published).slice(0, 16)}` : ''}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="report-actions">
          <button type="button" className="btn-ghost" onClick={() => copy('text')}>
            {copied === 'text' ? 'Copied' : 'Copy summary'}
          </button>
          {shareUrl && (
            <button type="button" className="btn-ghost" onClick={() => copy('link')}>
              {copied === 'link' ? 'Link copied' : 'Copy link'}
            </button>
          )}
          {onRerun && (
            <button type="button" className="btn-ghost" onClick={onRerun}>
              Re-run
            </button>
          )}
          {copied === 'fail' && <span className="copy-fail">Couldn't access the clipboard</span>}
        </div>
      </Card>
    </div>
  )
}
