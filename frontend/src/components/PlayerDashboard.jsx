import Card from './Card.jsx'
import './PlayerDashboard.css'

const STAT_FIELDS = [
  { key: 'pts', label: 'PTS' },
  { key: 'reb', label: 'REB' },
  { key: 'ast', label: 'AST' },
  { key: 'stl', label: 'STL' },
  { key: 'blk', label: 'BLK' },
]

const PCT_FIELDS = [
  { key: 'fg_pct', label: 'FG%' },
  { key: 'fg3_pct', label: '3P%' },
  { key: 'ft_pct', label: 'FT%' },
]

function fmt(n, digits = 1) {
  return typeof n === 'number' ? n.toFixed(digits) : '—'
}

function fmtPct(n) {
  return typeof n === 'number' ? `${(n * 100).toFixed(1)}%` : '—'
}

function ordinal(n) {
  if (!n) return null
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

function StatCard({ player }) {
  const s = player.stats

  return (
    <>
      <div className="stat-grid">
        {STAT_FIELDS.map(({ key, label }) => (
          <div className="stat-block" key={key}>
            <div className="stat-block-value">{fmt(s[key])}</div>
            <div className="stat-block-label">{label}</div>
          </div>
        ))}
      </div>

      <div className="pct-bars">
        {PCT_FIELDS.map(({ key, label }) => {
          const pct = typeof s[key] === 'number' ? Math.min(s[key] * 100, 100) : 0
          return (
            <div className="pct-row" key={key}>
              <span className="pct-label">{label}</span>
              <div className="pct-track">
                <div className="pct-fill" style={{ width: `${pct}%` }} />
              </div>
              <span className="pct-value">{fmtPct(s[key])}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}

function BioCard({ player }) {
  const draft = player.draft_year
    ? `${player.draft_year}, Round ${player.draft_round}, Pick ${player.draft_number}`
    : 'Undrafted'

  const rows = [
    { label: 'Height', value: player.height || '—' },
    { label: 'Weight', value: player.weight ? `${player.weight} lbs` : '—' },
    { label: 'College', value: player.college || '—' },
    { label: 'Draft', value: draft },
  ]

  return (
    <>
      <div className="bio-grid">
        {rows.map((r) => (
          <div className="bio-row" key={r.label}>
            <span className="bio-label">{r.label}</span>
            <span className="bio-value">{r.value}</span>
          </div>
        ))}
      </div>
      {player.stats_note && <div className="stats-note">{player.stats_note}</div>}
    </>
  )
}

function InjuryBadge({ injury }) {
  if (!injury || !injury.status) return null
  return (
    <div className="injury-badge" title={injury.description || ''}>
      <span className="injury-dot" />
      {injury.status}
      {injury.return_date ? ` · Return ${injury.return_date}` : ''}
    </div>
  )
}

function PlayerCard({ player }) {
  const hasStats = player.stats && typeof player.stats === 'object'

  return (
    <Card contentClassName="player-card">
      <div className="player-card-header">
        <div>
          <div className="player-name">{player.name}</div>
          <div className="player-meta">
            {player.team}
            {player.position ? ` · ${player.position}` : ''}
            {hasStats && player.season ? ` · ${player.season}-${String(player.season + 1).slice(-2)}` : ''}
          </div>
        </div>
      </div>

      <InjuryBadge injury={player.injury} />

      {hasStats ? <StatCard player={player} /> : <BioCard player={player} />}
    </Card>
  )
}

export default function PlayerDashboard({ players }) {
  if (!players || players.length === 0) return null

  return (
    <div className="players-wrap">
      <span className="eyebrow" style={{ marginBottom: 12, display: 'inline-flex' }}>
        Player stat sheet
      </span>
      <div className="players-grid">
        {players.map((p) => (
          <PlayerCard player={p} key={p.name} />
        ))}
      </div>
    </div>
  )
}