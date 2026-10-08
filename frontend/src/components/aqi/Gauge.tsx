import { AnimatedCircularProgressBar } from '@/components/ui/animated-circular-progress-bar'
import { naqi, onColor } from '@/utils/aqi'
import AqiBadge from './AqiBadge'

/** Big circular PM2.5 gauge (scale 0–300 µg/m³). */
export default function Gauge({ pm25 }: { pm25: number }) {
  const c = naqi(pm25)
  return (
    <div className="flex flex-col items-center gap-3" role="img" aria-label={`PM2.5 ${Math.round(pm25)} micrograms per cubic metre, ${c.name}`}>
      <div className="relative">
        <AnimatedCircularProgressBar
          value={Math.min(pm25, 300)} max={300} min={0}
          gaugePrimaryColor={c.color} gaugeSecondaryColor="rgba(120,140,170,0.25)"
          className="size-52 text-transparent"
        />
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <div className="font-display text-5xl font-bold tnum">{Math.round(pm25)}</div>
            <div className="text-xs text-muted">µg/m³ PM2.5</div>
          </div>
        </div>
      </div>
      <AqiBadge category={c.name} className="text-sm" />
      <span className="sr-only" style={{ color: onColor(c.name) }}>{c.name}</span>
    </div>
  )
}
