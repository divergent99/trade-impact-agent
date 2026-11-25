import { useEffect, useState } from 'react'
import { logoSources } from '../lib/teams.js'

/**
 * Official team logo with graceful degradation: tries each source in order
 * (NBA CDN, then ESPN) and ends on a team-colored abbreviation badge, so a
 * blocked CDN never shows a broken image.
 */
export default function TeamLogo({ team, size = 24, className = '', title }) {
  const sources = logoSources(team)
  const [idx, setIdx] = useState(0)

  useEffect(() => setIdx(0), [team?.abbr])

  if (!team || idx >= sources.length) {
    return (
      <span
        className={`team-logo team-logo-fallback ${className}`}
        style={{ width: size, height: size, '--team-color': team?.color || 'var(--signal)', fontSize: Math.max(8, size * 0.32) }}
        title={title || team?.label}
        aria-label={team?.label}
      >
        {team?.abbr || '?'}
      </span>
    )
  }

  return (
    <img
      className={`team-logo ${className}`}
      src={sources[idx]}
      width={size}
      height={size}
      alt={team.label}
      title={title || team.label}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setIdx((i) => i + 1)}
    />
  )
}
