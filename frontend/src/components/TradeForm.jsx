import Card from './Card.jsx'
import { EXAMPLES, TEAMS, teamByValue } from '../lib/teams.js'
import TeamLogo from './TeamLogo.jsx'

const MAX_LEN = 500
const MIN_LEN = 5

export default function TradeForm({
  team,
  setTeam,
  tradeDescription,
  setTradeDescription,
  onSubmit,
  onCancel,
  onExampleClick,
  loading,
  elapsed,
}) {
  const len = tradeDescription.trim().length
  const valid = len >= MIN_LEN && len <= MAX_LEN

  const submit = () => {
    if (!loading && valid) onSubmit()
  }

  return (
    <Card animated={loading}>
      <form
        className="trade-form"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <div className="form-grid">
          <div className="form-row">
            <label htmlFor="team">Evaluating for</label>
            <div className="select-wrap">
              <TeamLogo team={teamByValue(team)} size={22} className="select-logo" />
              <select id="team" value={team} onChange={(e) => setTeam(e.target.value)} disabled={loading}>
              {['East', 'West'].map((conf) => (
                <optgroup label={`${conf}ern Conference`} key={conf}>
                  {TEAMS.filter((t) => t.conf === conf).map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </optgroup>
              ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <label htmlFor="trade">
              The move
              <span className={`char-count${len > MAX_LEN ? ' over' : ''}`}>
                {len}/{MAX_LEN}
              </span>
            </label>
            <textarea
              id="trade"
              rows={3}
              maxLength={MAX_LEN + 50}
              placeholder="e.g. Nikola Jokic is traded to the Knicks for two first-round picks"
              value={tradeDescription}
              onChange={(e) => setTradeDescription(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  submit()
                }
              }}
              disabled={loading}
              required
            />
          </div>
        </div>

        <div className="example-chips" role="group" aria-label="Example trades">
          <span className="chips-label">Try</span>
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

        <div className="form-actions">
          <button
            className={`btn-primary${loading ? ' is-loading' : ''}`}
            type="submit"
            disabled={loading || !valid}
          >
            {loading ? (
              <span className="btn-loading">
                Analyzing
                <span className="dots">
                  <span />
                  <span />
                  <span />
                </span>
                <span className="btn-timer">{(elapsed / 1000).toFixed(0)}s</span>
              </span>
            ) : (
              'Run the trade'
            )}
          </button>
          {loading && (
            <button type="button" className="btn-ghost" onClick={onCancel}>
              Stop
            </button>
          )}
        </div>
        {!loading && <div className="form-hint">Ctrl / Cmd + Enter to run</div>}
      </form>
    </Card>
  )
}
