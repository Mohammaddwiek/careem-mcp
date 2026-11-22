import { useEffect, useState, type ReactNode } from 'react'

/**
 * Shows the app inside a phone on desktop screens (on a real phone it fills the screen instead).
 * The screen is its own scroll area and the containing block for fixed layers, so sheets, drawers
 * and overlays stay inside the phone.
 */
export function PhoneFrame({ tone, children, aside, below }: {
  tone: 'careem' | 'app'; children: ReactNode; aside?: ReactNode; below?: ReactNode
}) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 15000)
    return () => clearInterval(t)
  }, [])
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }).replace(/\s?[AP]M$/i, '')
  return (
    <div className="stage">
      <div className="phone-col">
      <div className="phone">
        <div className="phone-inner" id="phone-inner">
          <div className={`status-bar status-${tone}`} aria-hidden="true">
            <span className="status-time">{time}</span>
            <span className="island" />
            <span className="status-icons">
              <svg width="18" height="12" viewBox="0 0 18 12"><rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5.5" width="3" height="6.5" rx="1" /><rect x="10" y="3" width="3" height="9" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" /></svg>
              <span className="status-net">4G</span>
              <span className="battery"><span className="battery-fill" /></span>
            </span>
          </div>
          <div className="phone-screen" id="phone-screen">{children}</div>
          <span className="home-indicator" aria-hidden="true" />
        </div>
      </div>
      {below}
      </div>
      {aside}
    </div>
  )
}
