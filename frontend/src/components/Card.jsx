import BorderGlow from './BorderGlow.jsx'

// #FF7A1A (--signal) as HSL, used as the default glow color
const SIGNAL_HSL = '25 100 55'

export default function Card({ children, className = '', style, contentClassName = '', ...borderGlowProps }) {
  return (
    <div className={className} style={style}>
      <BorderGlow
        backgroundColor="#121b2e"
        borderRadius={14}
        glowColor={SIGNAL_HSL}
        glowRadius={24}
        glowIntensity={0.6}
        coneSpread={22}
        edgeSensitivity={35}
        colors={['#ff7a1a', '#4ade80', '#38bdf8']}
        {...borderGlowProps}
      >
        <div className={`card-inner ${contentClassName}`}>{children}</div>
      </BorderGlow>
    </div>
  )
}
