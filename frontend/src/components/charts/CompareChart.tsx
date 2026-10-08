import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ForecastPoint } from '@/api/endpoints'
import { fmtHour, fmtShortTime } from '@/utils/format'

export const SERIES_COLORS = ['#1e7bff', '#ff7a1a', '#16a34a', '#a855f7']

export default function CompareChart({ series }: { series: Record<string, ForecastPoint[]> }) {
  const names = Object.keys(series)
  const n = series[names[0]]?.length ?? 0
  const rows = Array.from({ length: n }, (_, i) => {
    const r: Record<string, any> = { t: series[names[0]][i].timestamp }
    names.forEach((c) => (r[c] = series[c][i].pm25))
    return r
  })
  return (
    <div style={{ height: 340 }} role="img" aria-label={`Forecast comparison for ${names.join(', ')}`}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" tickFormatter={fmtShortTime} minTickGap={36} tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={(l) => fmtHour(String(l))} formatter={(v) => `${Math.round(Number(v))} µg/m³`} contentStyle={{ borderRadius: 12 }} />
          <Legend />
          {names.map((c, i) => (
            <Line key={c} dataKey={c} stroke={SERIES_COLORS[i]} strokeWidth={2.5} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
