const KEY = 'trade-desk:history:v1'
const MAX = 10

export function loadHistory() {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((h) => h && h.report && h.id) : []
  } catch {
    return []
  }
}

export function saveHistory(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)))
  } catch {
    /* storage full or blocked (private mode): history is a nice-to-have */
  }
}

export function addToHistory(list, entry) {
  const deduped = list.filter(
    (h) => !(h.team === entry.team && h.description.trim().toLowerCase() === entry.description.trim().toLowerCase()),
  )
  return [entry, ...deduped].slice(0, MAX)
}
