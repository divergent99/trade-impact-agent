// value = what the agent sees, label = what the user sees
export const TEAMS = [
  { value: 'Hawks', label: 'Atlanta Hawks', abbr: 'ATL', conf: 'East', color: '#e03a3e', nbaId: 1610612737, espn: 'atl', jersey: ['#e03a3e', '#c1d32f'] },
  { value: 'Celtics', label: 'Boston Celtics', abbr: 'BOS', conf: 'East', color: '#007a33', nbaId: 1610612738, espn: 'bos', jersey: ['#007a33', '#ffffff'] },
  { value: 'Nets', label: 'Brooklyn Nets', abbr: 'BKN', conf: 'East', color: '#a1a1a4', nbaId: 1610612751, espn: 'bkn', jersey: ['#1a1a1a', '#ffffff'] },
  { value: 'Hornets', label: 'Charlotte Hornets', abbr: 'CHA', conf: 'East', color: '#00788c', nbaId: 1610612766, espn: 'cha', jersey: ['#1d1160', '#00a3b4'] },
  { value: 'Bulls', label: 'Chicago Bulls', abbr: 'CHI', conf: 'East', color: '#ce1141', nbaId: 1610612741, espn: 'chi', jersey: ['#ce1141', '#ffffff'] },
  { value: 'Cavaliers', label: 'Cleveland Cavaliers', abbr: 'CLE', conf: 'East', color: '#860038', nbaId: 1610612739, espn: 'cle', jersey: ['#860038', '#fdbb30'] },
  { value: 'Pistons', label: 'Detroit Pistons', abbr: 'DET', conf: 'East', color: '#c8102e', nbaId: 1610612765, espn: 'det', jersey: ['#c8102e', '#ffffff'] },
  { value: 'Pacers', label: 'Indiana Pacers', abbr: 'IND', conf: 'East', color: '#fdbb30', nbaId: 1610612754, espn: 'ind', jersey: ['#002d62', '#fdbb30'] },
  { value: 'Heat', label: 'Miami Heat', abbr: 'MIA', conf: 'East', color: '#98002e', nbaId: 1610612748, espn: 'mia', jersey: ['#98002e', '#f9a01b'] },
  { value: 'Bucks', label: 'Milwaukee Bucks', abbr: 'MIL', conf: 'East', color: '#00471b', nbaId: 1610612749, espn: 'mil', jersey: ['#00471b', '#eee1c6'] },
  { value: 'Knicks', label: 'New York Knicks', abbr: 'NYK', conf: 'East', color: '#f58426', nbaId: 1610612752, espn: 'ny', jersey: ['#006bb6', '#f58426'] },
  { value: 'Magic', label: 'Orlando Magic', abbr: 'ORL', conf: 'East', color: '#0077c0', nbaId: 1610612753, espn: 'orl', jersey: ['#0077c0', '#ffffff'] },
  { value: '76ers', label: 'Philadelphia 76ers', abbr: 'PHI', conf: 'East', color: '#006bb6', nbaId: 1610612755, espn: 'phi', jersey: ['#006bb6', '#ffffff'] },
  { value: 'Raptors', label: 'Toronto Raptors', abbr: 'TOR', conf: 'East', color: '#ce1141', nbaId: 1610612761, espn: 'tor', jersey: ['#ce1141', '#ffffff'] },
  { value: 'Wizards', label: 'Washington Wizards', abbr: 'WAS', conf: 'East', color: '#e31837', nbaId: 1610612764, espn: 'wsh', jersey: ['#002b5c', '#e31837'] },
  { value: 'Mavericks', label: 'Dallas Mavericks', abbr: 'DAL', conf: 'West', color: '#00538c', nbaId: 1610612742, espn: 'dal', jersey: ['#00538c', '#ffffff'] },
  { value: 'Nuggets', label: 'Denver Nuggets', abbr: 'DEN', conf: 'West', color: '#fec524', nbaId: 1610612743, espn: 'den', jersey: ['#0e2240', '#fec524'] },
  { value: 'Warriors', label: 'Golden State Warriors', abbr: 'GSW', conf: 'West', color: '#ffc72c', nbaId: 1610612744, espn: 'gs', jersey: ['#1d428a', '#ffc72c'] },
  { value: 'Rockets', label: 'Houston Rockets', abbr: 'HOU', conf: 'West', color: '#ce1141', nbaId: 1610612745, espn: 'hou', jersey: ['#ce1141', '#ffffff'] },
  { value: 'Clippers', label: 'LA Clippers', abbr: 'LAC', conf: 'West', color: '#c8102e', nbaId: 1610612746, espn: 'lac', jersey: ['#c8102e', '#ffffff'] },
  { value: 'Lakers', label: 'Los Angeles Lakers', abbr: 'LAL', conf: 'West', color: '#fdb927', nbaId: 1610612747, espn: 'lal', jersey: ['#552583', '#fdb927'] },
  { value: 'Grizzlies', label: 'Memphis Grizzlies', abbr: 'MEM', conf: 'West', color: '#5d76a9', nbaId: 1610612763, espn: 'mem', jersey: ['#5d76a9', '#ffffff'] },
  { value: 'Timberwolves', label: 'Minnesota Timberwolves', abbr: 'MIN', conf: 'West', color: '#78be20', nbaId: 1610612750, espn: 'min', jersey: ['#0c2340', '#78be20'] },
  { value: 'Pelicans', label: 'New Orleans Pelicans', abbr: 'NOP', conf: 'West', color: '#b4975a', nbaId: 1610612740, espn: 'no', jersey: ['#0c2340', '#c8a96b'] },
  { value: 'Thunder', label: 'Oklahoma City Thunder', abbr: 'OKC', conf: 'West', color: '#007ac1', nbaId: 1610612760, espn: 'okc', jersey: ['#007ac1', '#ffffff'] },
  { value: 'Suns', label: 'Phoenix Suns', abbr: 'PHX', conf: 'West', color: '#e56020', nbaId: 1610612756, espn: 'phx', jersey: ['#1d1160', '#e56020'] },
  { value: 'Trail Blazers', label: 'Portland Trail Blazers', abbr: 'POR', conf: 'West', color: '#e03a3e', nbaId: 1610612757, espn: 'por', jersey: ['#e03a3e', '#ffffff'] },
  { value: 'Kings', label: 'Sacramento Kings', abbr: 'SAC', conf: 'West', color: '#5a2d81', nbaId: 1610612758, espn: 'sac', jersey: ['#5a2d81', '#ffffff'] },
  { value: 'Spurs', label: 'San Antonio Spurs', abbr: 'SAS', conf: 'West', color: '#c4ced4', nbaId: 1610612759, espn: 'sa', jersey: ['#c4ced4', '#111111'] },
  { value: 'Jazz', label: 'Utah Jazz', abbr: 'UTA', conf: 'West', color: '#f9a01b', nbaId: 1610612762, espn: 'utah', jersey: ['#002b5c', '#f9a01b'] },
]

const NBA_LOGO = (id) => `https://cdn.nba.com/logos/nba/${id}/global/L/logo.svg`
const ESPN_LOGO = (code) => `https://a.espncdn.com/i/teamlogos/nba/500/${code}.png`

/** Candidate logo URLs in preference order; the component falls through on error. */
export const logoSources = (team) => (team ? [NBA_LOGO(team.nbaId), ESPN_LOGO(team.espn)] : [])

export const teamByValue = (v) => TEAMS.find((t) => t.value === v)

export function isValidTeam(v) {
  return TEAMS.some((t) => t.value === v)
}

// Hypotheticals only: real moves that already happened make bad demos.
export const EXAMPLES = [
  { label: 'Lakers lose LeBron', team: 'Lakers', description: 'LeBron James signs with the Mavericks' },
  { label: 'Nuggets lose Jokic', team: 'Nuggets', description: 'Nikola Jokic is traded to the Knicks' },
  { label: '76ers trade Embiid', team: '76ers', description: 'Joel Embiid is traded to the Warriors' },
  { label: 'Celtics trade Tatum', team: 'Celtics', description: 'Jayson Tatum is traded to the Knicks' },
]

// balldontlie full names ("Los Angeles Lakers", "LA Clippers") -> team meta
export const teamByLabel = (label) => {
  if (!label) return undefined
  const l = label.toLowerCase().trim()
  return (
    TEAMS.find((t) => t.label.toLowerCase() === l || t.abbr.toLowerCase() === l || t.value.toLowerCase() === l) ||
    TEAMS.find((t) => l.endsWith(t.value.toLowerCase()) || l.includes(t.value.toLowerCase()))
  )
}
