import { useEffect } from 'react'
import { naqi } from '@/utils/aqi'

/** Full-page sky whose colour and haze follow the current PM2.5 level. */
export default function SkyBackground({ pm25 = 25 }: { pm25?: number }) {
  useEffect(() => {
    const c = naqi(pm25)
    const dark = document.documentElement.classList.contains('dark')
    const root = document.documentElement.style
    if (dark) {
      root.removeProperty('--sky-top'); root.removeProperty('--sky-bottom')
    } else {
      root.setProperty('--sky-top', c.sky[0]); root.setProperty('--sky-bottom', c.sky[1])
    }
    root.setProperty('--haze', String(c.haze))
    const obs = new MutationObserver(() => {
      const d = document.documentElement.classList.contains('dark')
      if (d) { root.removeProperty('--sky-top'); root.removeProperty('--sky-bottom') }
      else { root.setProperty('--sky-top', c.sky[0]); root.setProperty('--sky-bottom', c.sky[1]) }
    })
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => obs.disconnect()
  }, [pm25])

  return (
    <div className="sky" aria-hidden>
      <div className="stars" />
      <div className="cloud animate-drift" style={{ width: 520, height: 120, top: '12%', left: '8%' }} />
      <div className="cloud animate-drift-slow" style={{ width: 700, height: 150, top: '34%', left: '45%' }} />
      <div className="cloud animate-drift" style={{ width: 420, height: 100, top: '58%', left: '-4%' }} />
      <div className="cloud animate-drift-slow" style={{ width: 600, height: 130, top: '75%', left: '55%' }} />
    </div>
  )
}
