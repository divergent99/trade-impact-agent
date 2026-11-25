// Generic basketball tank top drawn in the team's colors with the player's
// number and surname. Not a replica of any real uniform design.

function luminance(hex) {
  const h = hex.replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}

function contrast(a, b) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (l1 + 0.05) / (l2 + 0.05)
}

const BODY = 'M31 4 C36 24 64 24 69 4 L84 7 C82 22 86 33 95 37 L95 108 L5 108 L5 37 C14 33 18 22 16 7 Z'
const NECK = 'M31 4 C36 24 64 24 69 4'
const ARM_L = 'M16 7 C18 22 14 33 5 37'
const ARM_R = 'M84 7 C82 22 86 33 95 37'

let uid = 0

export default function Jersey({ team, number, name, size = 56 }) {
  const [base, trimRaw] = team?.jersey || ['#1a2540', '#ff7a1a']
  // keep the number readable even when the trim is close to the base color
  const trim = contrast(base, trimRaw) >= 2.2 ? trimRaw : luminance(base) > 0.4 ? '#111111' : '#ffffff'
  const num = number != null && String(number).trim() !== '' ? String(number).trim().slice(0, 2) : null
  const surname = (name || '').split(/\s+/).filter(Boolean).slice(-1)[0] || ''
  const shortName = surname.toUpperCase().slice(0, 10)
  const id = `jg${++uid}`

  return (
    <svg
      className="jersey"
      viewBox="0 0 100 112"
      width={size}
      height={size * 1.12}
      role="img"
      aria-label={num ? `${name}, number ${num}` : name}
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.18" />
          <stop offset="0.55" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="1" stopColor="#000000" stopOpacity="0.22" />
        </linearGradient>
      </defs>
      <path d={BODY} fill={base} />
      <path d={BODY} fill={`url(#${id})`} />
      {/* side panel stripes */}
      <path d="M5 50 L5 108 L11 108 L11 46 Z" fill={trim} opacity="0.85" />
      <path d="M95 50 L95 108 L89 108 L89 46 Z" fill={trim} opacity="0.85" />
      {/* trim piping */}
      <path d={NECK} fill="none" stroke={trim} strokeWidth="4" strokeLinecap="round" />
      <path d={ARM_L} fill="none" stroke={trim} strokeWidth="4" strokeLinecap="round" />
      <path d={ARM_R} fill="none" stroke={trim} strokeWidth="4" strokeLinecap="round" />
      <path d={BODY} fill="none" stroke="#000" strokeOpacity="0.35" strokeWidth="1.2" />
      {shortName && (
        <text
          x="50"
          y="41"
          textAnchor="middle"
          fill={trim}
          fontFamily="'Barlow Condensed', sans-serif"
          fontWeight="700"
          fontSize={shortName.length > 7 ? 9 : 11}
          letterSpacing="0.5"
        >
          {shortName}
        </text>
      )}
      <text
        x="50"
        y={num ? 88 : 82}
        textAnchor="middle"
        fill={trim}
        stroke="#000"
        strokeOpacity="0.25"
        strokeWidth="1"
        paintOrder="stroke"
        fontFamily="'Barlow Condensed', sans-serif"
        fontWeight="800"
        fontSize={num ? (num.length > 1 ? 46 : 50) : 30}
      >
        {num ?? (name || '?').split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase()}
      </text>
    </svg>
  )
}
