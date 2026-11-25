import Card from './Card.jsx'
import { fmt, fmtPct, seasonLabel } from '../lib/format.js'
import { teamByLabel } from '../lib/teams.js'
import Jersey from './Jersey.jsx'
import TeamLogo from './TeamLogo.jsx'
import './PlayerDashboard.css'

// rough "elite" marks used only to scale the mini bars under each number
const STAT_FIELDS = [
  { key: 'pts', label: 'PTS', max: 35 },
  { key: 'reb', label: 'REB', max: 14 },
  { key: 'ast', label: 'AST', max: 11 },
  { key: 'stl', label: 'STL', max: 2.2 },
  { key: 'blk', label: 'BLK', max: 3 },
]

const PCT_FIELDS = [
  { key: 'fg_pct', label: 'FG%' },
  { key: 'fg3_pct', label: '3P%' },
  { key: 'ft_pct', label: 'FT%' },
]

function inDeal(name, description) {
  if (!name || !description) return false
  const d = description.toLowerCase()
  const parts = name.toLowerCase().split(/\s+/)
  const last = parts[parts.length - 1]
  return d.includes(name.toLowerCase()) || (last.length > 3 && d.includes(last))
}

function Identity({ player, description, sub }) {
  const team = teamByLabel(player.team)
  const featured = inDeal(player.name, description)
  return (
    <div className="pr-id">
      <div className="pr-jersey" style={{ '--team-color': team?.color || 'var(--signal)' }}>
        <Jersey team={team} number={player.jersey} name={player.name} size={62} />
      </div>
      <div className="pr-id-text">
        <div className="player-name">{player.name}</div>
        <div className="player-meta">
          {team && <TeamLogo team={team} size={16} className="pr-team-logo" />}
          <span className="pr-meta-text">{sub}</span>
        </div>
        <div className="pr-tags">
          {featured && <span className="pr-tag deal">In the deal</span>}
          {player.injury?.status && (
            <span className={`pr-tag injury${/out/i.test(player.injury.status) ? ' out' : ''}`} title={player.injury.description || ''}>
              <span className="injury-dot" />
              {player.injury.status}
              {player.injury.return_date ? ` · ${player.injury.return_date}` : ''}
            </span>
          )}
          {!featured && !player.injury?.status && <span className="pr-tag">Healthy</span>}
        </div>
      </div>
    </div>
  )
}

function StatCols({ s }) {
  const extras = [
    s.min != null && s.min !== '' ? `${typeof s.min === 'number' ? fmt(s.min) : s.min} MIN` : null,
    s.games_played ? `${s.games_played} GP` : null,
    typeof s.turnover === 'number' ? `${fmt(s.turnover)} TOV` : null,
  ].filter(Boolean)

  return (
    <>
      <div className="pr-stats">
        {STAT_FIELDS.map(({ key, label, max }) => {
          const v = s[key]
          const pct = typeof v === 'number' ? Math.max(4, Math.min(100, (v / max) * 100)) : 0
          return (
            <div className="pr-stat" key={key}>
              <div className="pr-stat-value">{fmt(v)}</div>
              <div className="pr-stat-bar">
                <span style={{ width: `${pct}%` }} />
              </div>
              <div className="pr-stat-label">{label}</div>
            </div>
          )
        })}
      </div>

      <div className="pr-side">
        <div className="pct-bars">
          {PCT_FIELDS.map(({ key, label }) => {
            const pct = typeof s[key] === 'number' ? Math.max(0, Math.min(s[key] * 100, 100)) : 0
            return (
              <div className="pct-row" key={key}>
                <span className="pct-label">{label}</span>
                <div className="pct-track" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
                  <div className="pct-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="pct-value">{fmtPct(s[key])}</span>
              </div>
            )
          })}
        </div>
        {extras.length > 0 && <div className="stat-extras">{extras.join(' · ')}</div>}
      </div>
    </>
  )
}

function BioCols({ player }) {
  const draft = player.draft_year ? `'${String(player.draft_year).slice(-2)} R${player.draft_round ?? '?'}#${player.draft_number ?? '?'}` : 'Undrafted'
  const blocks = [
    { label: 'HT', value: player.height || '-' },
    { label: 'WT', value: player.weight ? `${player.weight}` : '-' },
    { label: 'DRAFT', value: draft },
  ]
  return (
    <>
      <div className="pr-stats bio">
        {blocks.map((b) => (
          <div className="pr-stat" key={b.label}>
            <div className="pr-stat-value bio">{b.value}</div>
            <div className="pr-stat-label">{b.label}</div>
          </div>
        ))}
      </div>
      <div className="pr-side">
        <div className="pr-empty">
          <span className="pr-empty-icon" aria-hidden="true">
            {'∅'}
          </span>
          <div>
            <div className="pr-empty-title">No season line</div>
            <div className="pr-empty-text">{player.college || player.country || 'Bio data only'}</div>
          </div>
        </div>
      </div>
    </>
  )
}

function PlayerRow({ player, description }) {
  const hasStats = player.stats && typeof player.stats === 'object'
  const sub = [player.team, player.position].filter(Boolean).join(' · ')
  const notes = [hasStats && player.season ? `${seasonLabel(player.season)} season` : null, player.match_note, player.stats_note].filter(Boolean)

  return (
    <Card contentClassName="player-row">
      <div className="pr-grid">
        <Identity player={player} description={description} sub={sub} />
        {hasStats ? <StatCols s={player.stats} /> : <BioCols player={player} />}
      </div>
      {notes.length > 0 && <div className="stats-note">{notes.join(' · ')}</div>}
    </Card>
  )
}

function PlayerSkeleton({ name }) {
  return (
    <Card contentClassName="player-row">
      <div className="pr-grid">
        <div className="pr-id">
          <div className="pr-jersey skel pr-jersey-skel" />
          <div className="pr-id-text">
            <div className="player-name">{name}</div>
            <div className="player-meta">Pulling stats and injury report…</div>
          </div>
        </div>
        <div className="pr-stats">
          {STAT_FIELDS.map((f) => (
            <div className="pr-stat" key={f.key}>
              <div className="skel" style={{ height: 20, width: '70%', margin: '0 auto' }} />
              <div className="pr-stat-label">{f.label}</div>
            </div>
          ))}
        </div>
        <div className="pr-side">
          <div className="skel skel-line" />
          <div className="skel skel-line" />
          <div className="skel skel-line" style={{ width: '70%' }} />
        </div>
      </div>
    </Card>
  )
}

export default function PlayerDashboard({ players, pending = [], description }) {
  const loadedNames = new Set(players.map((p) => (p.name || '').toLowerCase()))
  const waiting = pending.filter((n) => !loadedNames.has(n.toLowerCase()))
  if (!players.length && !waiting.length) return null

  // players named in the move first, then everyone else
  const sorted = [...players].sort((a, b) => inDeal(b.name, description) - inDeal(a.name, description))

  return (
    <div className="players-wrap">
      <div className="section-head">
        <span className="eyebrow">Player stat sheet</span>
        <span className="section-meta">Raw API numbers, never retyped by the model</span>
      </div>
      <div className="players-list">
        {sorted.map((p) => (
          <PlayerRow player={p} key={p.name} description={description} />
        ))}
        {waiting.map((n) => (
          <PlayerSkeleton name={n} key={`pending-${n}`} />
        ))}
      </div>
    </div>
  )
}
