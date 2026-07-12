import Card from './Card.jsx'

const TEAMS = [
  'Hawks', 'Celtics', 'Nets', 'Hornets', 'Bulls', 'Cavaliers', 'Mavericks',
  'Nuggets', 'Pistons', 'Warriors', 'Rockets', 'Pacers', 'Clippers', 'Lakers',
  'Grizzlies', 'Heat', 'Bucks', 'Timberwolves', 'Pelicans', 'Knicks',
  'Thunder', 'Magic', '76ers', 'Suns', 'Trail Blazers', 'Kings', 'Spurs',
  'Raptors', 'Jazz', 'Wizards',
]

const EXAMPLES = [
  { label: 'Lakers lose LeBron', team: 'Lakers', description: 'LeBron James signs with the Mavericks' },
  { label: 'Nuggets lose Jokic', team: 'Nuggets', description: 'Nikola Jokic is traded to the Knicks' },
  { label: '76ers trade Embiid', team: '76ers', description: 'Joel Embiid is traded to the Warriors' },
  { label: 'Celtics trade Tatum', team: 'Celtics', description: 'Jayson Tatum is traded to the Knicks' },
]

export default function TradeForm({ team, setTeam, tradeDescription, setTradeDescription, onSubmit, onExampleClick, loading }) {
  return (
    <Card animated={loading}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit()
        }}
      >
        <div className="form-row">
          <label htmlFor="team">Team you're evaluating for</label>
          <select id="team" value={team} onChange={(e) => setTeam(e.target.value)} disabled={loading}>
            {TEAMS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <label htmlFor="trade">The move</label>
          <textarea
            id="trade"
            rows={3}
            placeholder="e.g. LeBron James signs with the Mavericks"
            value={tradeDescription}
            onChange={(e) => setTradeDescription(e.target.value)}
            disabled={loading}
            required
          />
        </div>

        <div className="example-chips">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              className="example-chip"
              disabled={loading}
              onClick={() => onExampleClick(ex.team, ex.description)}
            >
              {ex.label}
            </button>
          ))}
        </div>

        <button className={`btn-primary${loading ? ' is-loading' : ''}`} type="submit" disabled={loading || !tradeDescription.trim()}>
          {loading ? (
            <span className="btn-loading">
              Analyzing
              <span className="dots">
                <span />
                <span />
                <span />
              </span>
            </span>
          ) : (
            'Run the trade'
          )}
        </button>
      </form>
    </Card>
  )
}