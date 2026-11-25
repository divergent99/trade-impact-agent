// value = what the agent sees, label = what the user sees
export const TEAMS = [
  { value: 'Hawks', label: 'Atlanta Hawks', abbr: 'ATL', conf: 'East', color: '#e03a3e' },
  { value: 'Celtics', label: 'Boston Celtics', abbr: 'BOS', conf: 'East', color: '#007a33' },
  { value: 'Nets', label: 'Brooklyn Nets', abbr: 'BKN', conf: 'East', color: '#a1a1a4' },
  { value: 'Hornets', label: 'Charlotte Hornets', abbr: 'CHA', conf: 'East', color: '#00788c' },
  { value: 'Bulls', label: 'Chicago Bulls', abbr: 'CHI', conf: 'East', color: '#ce1141' },
  { value: 'Cavaliers', label: 'Cleveland Cavaliers', abbr: 'CLE', conf: 'East', color: '#860038' },
  { value: 'Pistons', label: 'Detroit Pistons', abbr: 'DET', conf: 'East', color: '#c8102e' },
  { value: 'Pacers', label: 'Indiana Pacers', abbr: 'IND', conf: 'East', color: '#fdbb30' },
  { value: 'Heat', label: 'Miami Heat', abbr: 'MIA', conf: 'East', color: '#98002e' },
  { value: 'Bucks', label: 'Milwaukee Bucks', abbr: 'MIL', conf: 'East', color: '#00471b' },
  { value: 'Knicks', label: 'New York Knicks', abbr: 'NYK', conf: 'East', color: '#f58426' },
  { value: 'Magic', label: 'Orlando Magic', abbr: 'ORL', conf: 'East', color: '#0077c0' },
  { value: '76ers', label: 'Philadelphia 76ers', abbr: 'PHI', conf: 'East', color: '#006bb6' },
  { value: 'Raptors', label: 'Toronto Raptors', abbr: 'TOR', conf: 'East', color: '#ce1141' },
  { value: 'Wizards', label: 'Washington Wizards', abbr: 'WAS', conf: 'East', color: '#e31837' },
  { value: 'Mavericks', label: 'Dallas Mavericks', abbr: 'DAL', conf: 'West', color: '#00538c' },
  { value: 'Nuggets', label: 'Denver Nuggets', abbr: 'DEN', conf: 'West', color: '#fec524' },
  { value: 'Warriors', label: 'Golden State Warriors', abbr: 'GSW', conf: 'West', color: '#ffc72c' },
  { value: 'Rockets', label: 'Houston Rockets', abbr: 'HOU', conf: 'West', color: '#ce1141' },
  { value: 'Clippers', label: 'LA Clippers', abbr: 'LAC', conf: 'West', color: '#c8102e' },
  { value: 'Lakers', label: 'Los Angeles Lakers', abbr: 'LAL', conf: 'West', color: '#fdb927' },
  { value: 'Grizzlies', label: 'Memphis Grizzlies', abbr: 'MEM', conf: 'West', color: '#5d76a9' },
  { value: 'Timberwolves', label: 'Minnesota Timberwolves', abbr: 'MIN', conf: 'West', color: '#78be20' },
  { value: 'Pelicans', label: 'New Orleans Pelicans', abbr: 'NOP', conf: 'West', color: '#b4975a' },
  { value: 'Thunder', label: 'Oklahoma City Thunder', abbr: 'OKC', conf: 'West', color: '#007ac1' },
  { value: 'Suns', label: 'Phoenix Suns', abbr: 'PHX', conf: 'West', color: '#e56020' },
  { value: 'Trail Blazers', label: 'Portland Trail Blazers', abbr: 'POR', conf: 'West', color: '#e03a3e' },
  { value: 'Kings', label: 'Sacramento Kings', abbr: 'SAC', conf: 'West', color: '#5a2d81' },
  { value: 'Spurs', label: 'San Antonio Spurs', abbr: 'SAS', conf: 'West', color: '#c4ced4' },
  { value: 'Jazz', label: 'Utah Jazz', abbr: 'UTA', conf: 'West', color: '#f9a01b' },
]

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
  const l = label.toLowerCase()
  return TEAMS.find((t) => t.label.toLowerCase() === l) || TEAMS.find((t) => l.endsWith(t.value.toLowerCase()))
}
