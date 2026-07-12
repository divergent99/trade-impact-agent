import { useRef, useState } from 'react'
import TradeForm from './components/TradeForm.jsx'
import LiveFeed from './components/LiveFeed.jsx'
import PlayerDashboard from './components/PlayerDashboard.jsx'
import ReportCard from './components/ReportCard.jsx'
import Prism from './components/Prism.jsx'
import { streamAnalysis } from './lib/api.js'

export default function App() {
  const [team, setTeam] = useState('Lakers')
  const [tradeDescription, setTradeDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [lines, setLines] = useState([])
  const [players, setPlayers] = useState([])
  const [sources, setSources] = useState([])
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const controllerRef = useRef(null)

  function runAnalysis(teamArg, descArg) {
    const t = teamArg ?? team
    const d = descArg ?? tradeDescription

    controllerRef.current?.abort()
    setLoading(true)
    setLines([])
    setPlayers([])
    setSources([])
    setReport(null)
    setError(null)

    controllerRef.current = streamAnalysis(t, d, {
      onProgress: (msg) => setLines((prev) => [...prev, msg]),
      onPlayers: (p) => setPlayers(p),
      onSources: (s) => setSources(s),
      onReport: (r) => setReport(r),
      onDone: () => setLoading(false),
      onError: (err) => {
        setError(err.message || 'Something went wrong reaching the trade desk.')
        setLoading(false)
      },
    })
  }

  function handleExampleClick(exampleTeam, exampleDescription) {
    if (loading) return
    setTeam(exampleTeam)
    setTradeDescription(exampleDescription)
    runAnalysis(exampleTeam, exampleDescription)
  }

  return (
    <>
      <div className="bg-layer" aria-hidden="true">
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
        />
      </div>

      <div className="page-content">
        <header className="hero">
          <span className="eyebrow">Trade Desk — Live Agent Analysis</span>
          <h1>Run the trade before it happens.</h1>
          <p>
            Describe a move. An agent pulls real rosters, live stats, and breaking news,
            then grades it like a front-office analyst on deadline.
          </p>
        </header>

        <TradeForm
          team={team}
          setTeam={setTeam}
          tradeDescription={tradeDescription}
          setTradeDescription={setTradeDescription}
          onSubmit={() => runAnalysis()}
          onExampleClick={handleExampleClick}
          loading={loading}
        />

        {error && <div className="error-banner">{error}</div>}

        <LiveFeed lines={lines} active={loading} />

        <PlayerDashboard players={players} />

        <ReportCard report={report} sources={sources} />
      </div>
    </>
  )
}