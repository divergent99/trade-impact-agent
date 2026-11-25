import { useEffect, useRef, useState } from 'react'
import Card from './Card.jsx'
import { fmtDuration, toolLabel } from '../lib/format.js'
import './AgentTimeline.css'

const ICON = { ok: '✓', error: '!', running: '' }

function Step({ step }) {
  if (step.kind === 'status') {
    return (
      <li className={`tl-step tl-status${step.active ? ' active' : ''}`}>
        <span className="tl-icon">{step.active ? <span className="tl-spinner" /> : '•'}</span>
        <span className="tl-text">{step.message}</span>
      </li>
    )
  }
  return (
    <li className={`tl-step tl-tool is-${step.status}`}>
      <span className="tl-icon">{step.status === 'running' ? <span className="tl-spinner" /> : ICON[step.status]}</span>
      <span className="tl-text">
        <span className="tl-label">{toolLabel(step.name, step.input)}</span>
        {step.summary && <span className="tl-summary">{step.summary}</span>}
      </span>
      {step.ms != null && <span className="tl-ms">{fmtDuration(step.ms)}</span>}
    </li>
  )
}

export default function AgentTimeline({ steps, active, elapsedMs }) {
  const bodyRef = useRef(null)
  const [open, setOpen] = useState(true)

  // auto-collapse once a run finishes so the report gets the spotlight
  useEffect(() => {
    setOpen(active)
  }, [active])

  useEffect(() => {
    const el = bodyRef.current
    if (el && active) el.scrollTop = el.scrollHeight
  }, [steps, active])

  if (!steps.length && !active) return null

  const tools = steps.filter((s) => s.kind === 'tool')
  const failed = tools.filter((s) => s.status === 'error').length

  return (
    <div className="tl-wrap">
      <Card contentClassName="tl-card">
        <button type="button" className="tl-header" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          <span className="eyebrow">{active ? 'Agent working' : 'Agent log'}</span>
          <span className="tl-meta">
            {tools.length} lookup{tools.length === 1 ? '' : 's'}
            {failed ? ` · ${failed} failed` : ''}
            {elapsedMs ? ` · ${fmtDuration(elapsedMs)}` : ''}
            <span className={`tl-chevron${open ? ' open' : ''}`}>{'▾'}</span>
          </span>
        </button>
        {open && (
          <ol className="tl-body" ref={bodyRef} aria-live="polite">
            {!steps.length && (
              <li className="tl-step tl-status active">
                <span className="tl-icon">
                  <span className="tl-spinner" />
                </span>
                <span className="tl-text">Connecting to the trade desk</span>
              </li>
            )}
            {steps.map((s) => (
              <Step step={s} key={s.key} />
            ))}
          </ol>
        )}
      </Card>
    </div>
  )
}
