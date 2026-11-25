import { useEffect, useMemo, useRef, useState } from 'react'
import TradeForm from './components/TradeForm.jsx'
import AgentTimeline from './components/AgentTimeline.jsx'
import PlayerDashboard from './components/PlayerDashboard.jsx'
import ReportCard, { ReportSkeleton } from './components/ReportCard.jsx'
import { GradeGuide, HistoryPanel, HowItWorks } from './components/SidePanels.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import Prism from './components/Prism.jsx'
import { API_URL, fetchHealth, streamAnalysis } from './lib/api.js'
import { addToHistory, loadHistory, saveHistory } from './lib/history.js'
import { isValidTeam } from './lib/teams.js'

function canRenderBackground() {
  if (typeof window === 'undefined') return false
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return false
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

function readUrlParams() {
  const p = new URLSearchParams(window.location.search)
  const team = p.get('team')
  const move = p.get('move')
  return { team: isValidTeam(team) ? team : null, move: move ? move.slice(0, 500) : null }
}

function upsertPlayer(list, player) {
  const key = (player.name || '').toLowerCase()
  const i = list.findIndex((p) => (p.name || '').toLowerCase() === key)
  if (i === -1) return [...list, player]
  const next = list.slice()
  next[i] = player
  return next
}

let stepSeq = 0

export default function App() {
  const initial = useMemo(readUrlParams, [])
  const [team, setTeam] = useState(initial.team || 'Lakers')
  const [tradeDescription, setTradeDescription] = useState(initial.move || '')

  const [phase, setPhase] = useState('idle') // idle | running | done | error
  const [steps, setSteps] = useState([])
  const [players, setPlayers] = useState([])
  const [sources, setSources] = useState([])
  const [report, setReport] = useState(null)
  const [writing, setWriting] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [serverMs, setServerMs] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const [ran, setRan] = useState(null) // {team, description} of the run on screen

  const [history, setHistory] = useState(loadHistory)
  const [activeId, setActiveId] = useState(null)
  const [health, setHealth] = useState(null)
  const showBg = useMemo(canRenderBackground, [])

  const controllerRef = useRef(null)
  const runRef = useRef(null)
  const startedRef = useRef(0)

  const loading = phase === 'running'

  useEffect(() => {
    let alive = true
    fetchHealth()
      .then((h) => alive && setHealth({ ok: true, ...h }))
      .catch(() => alive && setHealth({ ok: false }))
    return () => {
      alive = false
      controllerRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (!loading) return
    const id = setInterval(() => setElapsed(Date.now() - startedRef.current), 250)
    return () => clearInterval(id)
  }, [loading])

  useEffect(() => {
    saveHistory(history)
  }, [history])

  function resetRun() {
    setSteps([])
    setPlayers([])
    setSources([])
    setReport(null)
    setWriting(false)
    setError(null)
    setNotice(null)
    setServerMs(null)
    setActiveId(null)
  }

  function runAnalysis(teamArg, descArg) {
    const t = teamArg ?? team
    const d = (descArg ?? tradeDescription).trim()
    if (!d) return

    controllerRef.current?.abort()
    resetRun()
    setPhase('running')
    setRan({ team: t, description: d })
    setElapsed(0)
    startedRef.current = Date.now()

    const run = { team: t, description: d, report: null, players: [], sources: [], cancelled: false, error: null }
    runRef.current = run
    const isCurrent = () => runRef.current === run

    controllerRef.current = streamAnalysis(t, d, {
      status: ({ message }) => {
        if (!isCurrent()) return
        setWriting(/report/i.test(message))
        setSteps((prev) => [
          ...prev.map((s) => (s.kind === 'status' ? { ...s, active: false } : s)),
          { kind: 'status', message, active: true, key: `s${++stepSeq}` },
        ])
      },
      tool: (ev) => {
        if (!isCurrent()) return
        setSteps((prev) => {
          const i = prev.findIndex((s) => s.kind === 'tool' && s.id === ev.id)
          if (i === -1) {
            const cleared = prev.map((s) => (s.kind === 'status' ? { ...s, active: false } : s))
            return [...cleared, { kind: 'tool', key: `t${ev.id}`, ...ev }]
          }
          const next = prev.slice()
          next[i] = { ...next[i], ...ev }
          return next
        })
      },
      player: (p) => {
        if (!isCurrent()) return
        run.players = upsertPlayer(run.players, p)
        setPlayers(run.players)
      },
      players: (list) => {
        if (!isCurrent() || !Array.isArray(list)) return
        run.players = list
        setPlayers(list)
      },
      sources: (list) => {
        if (!isCurrent() || !Array.isArray(list)) return
        run.sources = list
        setSources(list)
      },
      report: (r) => {
        if (!isCurrent()) return
        run.report = r
        setReport(r)
        setWriting(false)
      },
      error: ({ message }) => {
        if (!isCurrent()) return
        run.error = message
        setError(message)
      },
      done: ({ elapsed_ms }) => isCurrent() && setServerMs(elapsed_ms),
      finish: () => {
        if (!isCurrent()) return
        setWriting(false)
        setSteps((prev) => prev.map((s) => (s.kind === 'status' ? { ...s, active: false } : s)))
        if (run.report) {
          const entry = {
            id: `${Date.now()}`,
            at: Date.now(),
            team: run.team,
            description: run.description,
            report: run.report,
            players: run.players,
            sources: run.sources,
          }
          setHistory((h) => addToHistory(h, entry))
          setActiveId(entry.id)
          setPhase('done')
        } else if (run.cancelled) {
          setNotice('Analysis stopped.')
          setPhase('idle')
        } else {
          if (!run.error) setError('The analysis ended unexpectedly.')
          setPhase('error')
        }
      },
    })
  }

  function cancel() {
    if (runRef.current) runRef.current.cancelled = true
    controllerRef.current?.abort()
  }

  function handleExampleClick(exampleTeam, exampleDescription) {
    if (loading) return
    setTeam(exampleTeam)
    setTradeDescription(exampleDescription)
    runAnalysis(exampleTeam, exampleDescription)
  }

  function restore(entry) {
    if (loading) return
    resetRun()
    setTeam(entry.team)
    setTradeDescription(entry.description)
    setRan({ team: entry.team, description: entry.description })
    setPlayers(entry.players || [])
    setSources(entry.sources || [])
    setReport(entry.report)
    setActiveId(entry.id)
    setPhase('done')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const shareUrl = useMemo(() => {
    if (!ran) return null
    const u = new URL(window.location.href)
    u.search = new URLSearchParams({ team: ran.team, move: ran.description }).toString()
    u.hash = ''
    return u.toString()
  }, [ran])

  const pendingPlayers = steps
    .filter((s) => s.kind === 'tool' && s.name === 'get_player_stats' && s.status === 'running')
    .map((s) => s.input?.player_name)
    .filter(Boolean)

  const hasResults = loading || report || steps.length > 0
  const missingKeys = health?.ok
    ? Object.entries(health.configured || {})
        .filter(([, v]) => !v)
        .map(([k]) => k)
    : []

  return (
    <>
      {showBg && (
        <div className="bg-layer" aria-hidden="true">
          <ErrorBoundary>
            <Prism
              animationType="rotate"
              timeScale={0.35}
              height={3.5}
              baseWidth={5.5}
              scale={3.6}
              hueShift={0.15}
              colorFrequency={1}
              noise={0.12}
              glow={0.55}
              bloom={0.7}
              suspendWhenOffscreen
            />
          </ErrorBoundary>
        </div>
      )}

      <div className="page-content">
        <header className={`hero${hasResults ? ' compact' : ''}`}>
          <div className="hero-top">
            <span className="eyebrow">Trade Desk / Live Agent Analysis</span>
            <span className={`health health-${health == null ? 'pending' : health.ok ? (missingKeys.length ? 'warn' : 'ok') : 'down'}`}>
              <span className="health-dot" />
              {health == null
                ? 'Checking desk'
                : health.ok
                  ? `${health.season} season`
                  : 'Desk offline'}
            </span>
          </div>
          <h1>Run the trade before it happens.</h1>
          {!hasResults && (
            <p>
              Describe a move. An agent pulls real rosters, live stats, injury reports and breaking news, then grades it
              like a front-office analyst on deadline.
            </p>
          )}
        </header>

        {health && !health.ok && (
          <div className="banner banner-warn">
            Can't reach the backend at <code>{API_URL}</code>. Start it or set <code>VITE_API_URL</code>.
          </div>
        )}
        {missingKeys.length > 0 && (
          <div className="banner banner-warn">
            Server is missing keys for: {missingKeys.join(', ')}. Results will be degraded.
          </div>
        )}

        <div className="layout">
          <main className="main-col">
            <TradeForm
              team={team}
              setTeam={setTeam}
              tradeDescription={tradeDescription}
              setTradeDescription={setTradeDescription}
              onSubmit={() => runAnalysis()}
              onCancel={cancel}
              onExampleClick={handleExampleClick}
              loading={loading}
              elapsed={elapsed}
            />

            {error && (
              <div className="banner banner-error" role="alert">
                <span>{error}</span>
                {ran && (
                  <button type="button" className="btn-ghost sm" onClick={() => runAnalysis(ran.team, ran.description)}>
                    Try again
                  </button>
                )}
              </div>
            )}
            {notice && <div className="banner banner-info">{notice}</div>}

            <ErrorBoundary resetKey={ran?.description} fallback={<div className="banner banner-error">Couldn't render the results.</div>}>
              {report ? (
                <ReportCard
                  report={report}
                  sources={sources}
                  team={ran?.team}
                  description={ran?.description}
                  shareUrl={shareUrl}
                  onRerun={() => ran && runAnalysis(ran.team, ran.description)}
                />
              ) : (
                loading && (
                  <ReportSkeleton
                    caption={
                      writing
                        ? 'Writing the report'
                        : `Researching: ${steps.filter((x) => x.kind === 'tool' && x.status !== 'running').length} lookups done`
                    }
                  />
                )
              )}

              <AgentTimeline steps={steps} active={loading} elapsedMs={loading ? null : serverMs} />

              <PlayerDashboard players={players} pending={pendingPlayers} description={ran?.description} />
            </ErrorBoundary>

            {!hasResults && <HowItWorks />}
          </main>

          <aside className="side-col">
            <HistoryPanel
              history={history}
              activeId={activeId}
              onSelect={restore}
              onClear={() => setHistory([])}
              disabled={loading}
            />
            <GradeGuide />
          </aside>
        </div>

        <footer className="footer">
          Stats: balldontlie &middot; News: Tavily &middot; Analysis: Claude. Grades are opinions, not predictions.
        </footer>
      </div>
    </>
  )
}
