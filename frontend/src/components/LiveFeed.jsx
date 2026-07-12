import { useEffect, useRef } from 'react'
import Card from './Card.jsx'
import './LiveFeed.css'

export default function LiveFeed({ lines, active }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [lines])

  // Show nothing before the first run, but as soon as loading starts,
  // render immediately with a placeholder instead of waiting for the
  // first SSE event to arrive (that gap used to look like nothing was happening).
  if (lines.length === 0 && !active) return null

  return (
    <div className="feed-wrap">
      <Card contentClassName="feed">
        <div className="feed-header">
          <span className="eyebrow">{active ? 'Agent working' : 'Agent log'}</span>
        </div>
        <div className="feed-body">
          {lines.length === 0 && active && (
            <div className="feed-line">
              <span className="feed-prompt">&gt;</span> Connecting to trade desk
              <span className="dots dots-inline">
                <span />
                <span />
                <span />
              </span>
            </div>
          )}
          {lines.map((line, i) => (
            <div className="feed-line" key={i} style={{ animationDelay: `${Math.min(i * 40, 200)}ms` }}>
              <span className="feed-prompt">&gt;</span> {line}
            </div>
          ))}
          {active && <span className="feed-cursor" />}
          <div ref={endRef} />
        </div>
      </Card>
    </div>
  )
}
