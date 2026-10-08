import type { ReactNode } from 'react'
import { CloudRain, Droplets, Gauge as GaugeIcon, Thermometer, Wind } from 'lucide-react'
import { fmtNum } from '@/utils/format'
import { motion } from 'motion/react'

export function Tile({ icon, label, value, unit, sub }: { icon: ReactNode; label: string; value: string; unit?: string; sub?: string }) {
  return (
    <motion.div whileHover={{ y: -3 }} className="glass flex items-center gap-3 p-3.5">
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-accent/15 text-accent">{icon}</div>
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
        <div className="font-display text-lg font-semibold tnum leading-tight">
          {value}<span className="ml-1 text-xs font-normal text-muted">{unit}</span>
        </div>
        {sub && <div className="text-[11px] text-muted">{sub}</div>}
      </div>
    </motion.div>
  )
}

export function WeatherTiles({ w }: { w: Record<string, number | null> }) {
  const windDur = Math.max(0.6, 6 - (w.wind_speed ?? 0) / 4)
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Tile icon={<Thermometer size={20} />} label="Temperature" value={fmtNum(w.temperature, 1)} unit="°C" />
      <Tile icon={<Droplets size={20} />} label="Humidity" value={fmtNum(w.humidity)} unit="%" />
      <Tile
        icon={<Wind size={20} style={{ animation: `spin ${windDur}s linear infinite` }} />}
        label="Wind" value={fmtNum(w.wind_speed, 1)} unit="km/h" sub={(w.wind_speed ?? 0) < 6 ? 'Calm: pollution lingers' : 'Helps disperse pollution'}
      />
      <Tile icon={<CloudRain size={20} />} label="Rain" value={fmtNum(w.rain, 1)} unit="mm/h" sub={(w.rain ?? 0) > 0 ? 'Washing out particles' : 'No rain'} />
    </div>
  )
}

const POLL: { k: string; label: string; unit: string; d: number }[] = [
  { k: 'pm10', label: 'PM10', unit: 'µg/m³', d: 0 }, { k: 'no2', label: 'NO₂', unit: 'µg/m³', d: 0 },
  { k: 'so2', label: 'SO₂', unit: 'µg/m³', d: 0 }, { k: 'o3', label: 'O₃', unit: 'µg/m³', d: 0 }, { k: 'co', label: 'CO', unit: 'µg/m³', d: 0 },
]
export function PollutantTiles({ p }: { p: Record<string, number | null> }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {POLL.map((x) => (
        <Tile key={x.k} icon={<GaugeIcon size={20} />} label={x.label} value={fmtNum(p[x.k], x.d)} unit={x.unit} />
      ))}
    </div>
  )
}
