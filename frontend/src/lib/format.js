export const GRADE_COLORS = {
  A: '#4ade80',
  B: '#a3e635',
  C: '#facc15',
  D: '#ff9a4d',
  F: '#fb4b4b',
}

export const gradeColor = (g) => GRADE_COLORS[(g || '').charAt(0)] || 'var(--signal)'

export function fmt(n, digits = 1) {
  return typeof n === 'number' && Number.isFinite(n) ? n.toFixed(digits) : '-'
}

export function fmtPct(n) {
  return typeof n === 'number' && Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : '-'
}

export function seasonLabel(season) {
  return season ? `${season}-${String(season + 1).slice(-2)}` : ''
}

export function fmtDuration(ms) {
  if (!ms && ms !== 0) return ''
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export function timeAgo(ts) {
  const s = Math.round((Date.now() - ts) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

const TOOL_LABELS = {
  get_team_roster: (i) => `Roster: ${i?.team_name ?? '?'}`,
  get_player_stats: (i) => `Stats: ${i?.player_name ?? '?'}${i?.season ? ` (${seasonLabel(i.season)})` : ''}`,
  search_trade_news: (i) => `News: "${i?.query ?? ''}"`,
}

export const toolLabel = (name, input) => (TOOL_LABELS[name] ? TOOL_LABELS[name](input) : name)

export function reportToText({ team, description, report, sources = [] }) {
  const sign = report.win_prob_delta >= 0 ? '+' : ''
  const lines = [
    `TRADE DESK: ${description}`,
    `Evaluated for: ${team}`,
    '',
    `Grade: ${report.trade_grade}  |  Win outlook: ${sign}${report.win_prob_delta} pts  |  Confidence: ${report.confidence}`,
    report.headline,
    '',
  ]
  if (report.counterpart) lines.push(`${report.counterpart.team}: ${report.counterpart.grade}. ${report.counterpart.take}`, '')
  if (report.roster_fit_summary) lines.push(report.roster_fit_summary, '')
  if (report.pros?.length) lines.push('Upside:', ...report.pros.map((p) => `+ ${p}`), '')
  if (report.cons?.length) lines.push('Risks:', ...report.cons.map((c) => `- ${c}`), '')
  if (report.key_stat_comparisons?.length) {
    lines.push('Breakdown:', ...report.key_stat_comparisons.map((r) => `  ${r.stat}: ${r.before} -> ${r.after}`), '')
  }
  if (report.verdict) lines.push(report.verdict, '')
  if (report.historical_parallel) lines.push(`Parallel: ${report.historical_parallel}`, '')
  if (sources.length) lines.push('Sources:', ...sources.map((s) => `  ${s.title} (${s.url})`))
  return lines.join('\n').trim()
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // clipboard API blocked (http, iframe): fall back to a hidden textarea
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    let ok = false
    try {
      ok = document.execCommand('copy')
    } catch {
      ok = false
    }
    document.body.removeChild(ta)
    return ok
  }
}
