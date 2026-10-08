import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Factor, Importance, PerfRow } from '@/api/endpoints'

const axis = { fontSize: 11, fill: 'var(--muted)' }

export function FactorBars({ factors }: { factors: Factor[] }) {
  const data = factors.map((f) => ({ name: f.label, v: f.shap }))
  return (
    <div style={{ height: 40 + data.length * 38 }} role="img" aria-label="Bar chart of the top factors changing the forecast">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tick={axis} axisLine={false} tickLine={false} unit=" µg" />
          <YAxis type="category" dataKey="name" width={150} tick={axis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v) => `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(1)} µg/m³`} contentStyle={{ borderRadius: 12 }} />
          <Bar dataKey="v" radius={6} animationDuration={900}>
            {data.map((d, i) => <Cell key={i} fill={d.v > 0 ? '#ff6a3d' : '#2f9e6b'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ImportanceBar({ data }: { data: Importance[] }) {
  const d = data.slice(0, 12)
  return (
    <div style={{ height: 40 + d.length * 30 }} role="img" aria-label="Global feature importance (mean absolute SHAP value)">
      <ResponsiveContainer>
        <BarChart data={d} layout="vertical" margin={{ right: 16 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tick={axis} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="feature" width={190} tick={axis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v) => `${Number(v).toFixed(2)} µg/m³`} contentStyle={{ borderRadius: 12 }} />
          <Bar dataKey="importance" fill="#1e7bff" radius={6} animationDuration={900} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ModelVsBaseline({ rows, model }: { rows: PerfRow[]; model: Record<number, string> }) {
  const hs = [...new Set(rows.map((r) => r.horizon))].sort((a, b) => a - b).filter((h) => [6, 24, 48, 72].includes(h))
  const data = hs.map((h) => ({
    h: `${h} h`,
    Persistence: rows.find((r) => r.horizon === h && r.model === 'Persistence')?.RMSE,
    'Best model': rows.find((r) => r.horizon === h && r.model === model[h])?.RMSE,
  }))
  return (
    <div style={{ height: 280 }} role="img" aria-label="RMSE of best model versus persistence baseline by forecast horizon">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: -10 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="h" tick={axis} axisLine={false} tickLine={false} />
          <YAxis tick={axis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v) => `${Number(v).toFixed(1)} µg/m³`} contentStyle={{ borderRadius: 12 }} />
          <Legend />
          <Bar dataKey="Persistence" fill="#94a3b8" radius={[6, 6, 0, 0]} />
          <Bar dataKey="Best model" fill="#1e7bff" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ErrorByHorizon({ rows, model }: { rows: PerfRow[]; model: Record<number, string> }) {
  const hs = [...new Set(rows.map((r) => r.horizon))].sort((a, b) => a - b)
  const data = hs.map((h) => ({
    h,
    'Test A (last 90 d)': rows.find((r) => r.horizon === h && r.model === model[h] && r.test === 'A_recent90d')?.MAE,
    'Test B (winter)': rows.find((r) => r.horizon === h && r.model === model[h] && r.test === 'B_winter')?.MAE,
  }))
  return (
    <div style={{ height: 280 }} role="img" aria-label="Mean absolute error by forecast horizon on two test sets">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: -10 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="h" tickFormatter={(h) => `${h} h`} tick={axis} axisLine={false} tickLine={false} />
          <YAxis tick={axis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v) => `${Number(v).toFixed(1)} µg/m³`} labelFormatter={(h) => `${h} h ahead`} contentStyle={{ borderRadius: 12 }} />
          <Legend />
          <Line dataKey="Test A (last 90 d)" stroke="#1e7bff" strokeWidth={3} dot />
          <Line dataKey="Test B (winter)" stroke="#ff7a1a" strokeWidth={3} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
