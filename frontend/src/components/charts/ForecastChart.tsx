import { Area, ComposedChart, CartesianGrid, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ForecastPoint, HistoryPoint } from '@/api/endpoints'
import { NAQI, naqi } from '@/utils/aqi'
import { fmtHour, fmtShortTime } from '@/utils/format'

const BANDS = [
  { y1: 0, y2: 30, c: NAQI[0].color }, { y1: 30, y2: 60, c: NAQI[1].color }, { y1: 60, y2: 90, c: NAQI[2].color },
  { y1: 90, y2: 120, c: NAQI[3].color }, { y1: 120, y2: 250, c: NAQI[4].color }, { y1: 250, y2: 1000, c: NAQI[5].color },
]

type Row = { t: string; actual?: number; pm25?: number; band?: [number, number] }

function Tip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const r: Row = payload[0].payload
  const v = r.pm25 ?? r.actual
  if (v == null) return null
  return (
    <div className="glass px-3 py-2 text-xs shadow-lg" style={{ backdropFilter: 'blur(20px)' }}>
      <div className="font-semibold">{fmtHour(r.t)}</div>
      <div className="tnum">{r.actual != null ? 'Observed' : 'Forecast'}: <b>{Math.round(v)}</b> µg/m³ · {naqi(v).name}</div>
      {r.band && <div className="tnum text-muted">80% range: {Math.round(r.band[0])}–{Math.round(r.band[1])}</div>}
    </div>
  )
}

/** Forecast (with 10–90% ribbon) optionally joined to recent history. */
export default function ForecastChart({ points, history, height = 320 }: { points: ForecastPoint[]; history?: HistoryPoint[]; height?: number }) {
  const rows: Row[] = []
  history?.forEach((h) => h.pm25 != null && rows.push({ t: h.timestamp, actual: h.pm25 }))
  points.forEach((p, i) => rows.push({ t: p.timestamp, pm25: p.pm25, band: [p.lower, p.upper], ...(i === 0 && history ? { actual: p.pm25 } : {}) }))
  const max = Math.max(60, ...rows.map((r) => Math.max(r.pm25 ?? 0, r.actual ?? 0, r.band?.[1] ?? 0))) * 1.1
  const now = points[0]?.timestamp

  return (
    <div style={{ height }} role="img" aria-label="Line chart of observed and forecast PM2.5 with uncertainty range">
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          {BANDS.filter((b) => b.y1 < max).map((b) => (
            <ReferenceArea key={b.y1} y1={b.y1} y2={Math.min(b.y2, max)} fill={b.c} fillOpacity={0.1} ifOverflow="hidden" />
          ))}
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" tickFormatter={fmtShortTime} minTickGap={36} tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, Math.ceil(max)]} tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} unit="" />
          <Tooltip content={<Tip />} />
          <Area dataKey="band" stroke="none" fill="#1e7bff" fillOpacity={0.18} isAnimationActive animationDuration={900} />
          {history && <Line dataKey="actual" stroke="var(--foreground)" strokeWidth={2} dot={false} connectNulls />}
          <Line dataKey="pm25" stroke="#1e7bff" strokeWidth={3} dot={false} strokeDasharray={history ? '0' : undefined} animationDuration={1100} />
          {now && history && <ReferenceLine x={now} stroke="var(--muted)" strokeDasharray="4 4" label={{ value: 'now', position: 'top', fontSize: 11, fill: 'var(--muted)' }} />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
