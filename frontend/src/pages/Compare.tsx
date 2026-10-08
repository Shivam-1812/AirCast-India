import { useState } from 'react'
import { BlurFade } from '@/components/ui/blur-fade'
import SkyBackground from '@/components/layout/SkyBackground'
import CompareChart, { SERIES_COLORS } from '@/components/charts/CompareChart'
import AqiBadge from '@/components/aqi/AqiBadge'
import { Card, ErrorState, Skeleton } from '@/components/common/ui'
import { useCompare } from '@/hooks/useApi'
import { CITIES } from '@/utils/cities'
import { naqi } from '@/utils/aqi'

export default function Compare() {
  const [sel, setSel] = useState<string[]>(['Delhi', 'Pune'])
  const { data, error, isLoading, refetch } = useCompare(sel)
  const toggle = (c: string) => setSel((s) => (s.includes(c) ? s.filter((x) => x !== c) : s.length < 4 ? [...s, c] : s))

  return (
    <>
      <SkyBackground pm25={60} />
      <div className="mx-auto max-w-6xl space-y-6 px-4 pt-8">
        <BlurFade>
          <h1 className="font-display text-3xl font-bold">Compare cities</h1>
          <p className="text-sm text-muted">Pick up to four cities to overlay their 72-hour forecasts.</p>
        </BlurFade>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Select cities">
          {CITIES.map((c) => {
            const on = sel.includes(c)
            return (
              <button key={c} onClick={() => toggle(c)} aria-pressed={on} disabled={!on && sel.length >= 4}
                className={`glass px-3.5 py-1.5 text-sm font-medium transition disabled:opacity-40 ${on ? '!bg-accent !text-white' : ''}`}>
                {c}
              </button>
            )
          })}
        </div>
        {error ? <ErrorState error={error} onRetry={() => refetch()} /> : (
          <>
            <Card title="Forecast overlay" subtitle="PM2.5, µg/m³">
              {isLoading || !data ? <Skeleton className="h-80" /> : sel.length === 0 ? <p className="py-10 text-center text-muted">Select at least one city.</p> : <CompareChart series={data.series} />}
            </Card>
            {data && (
              <Card title="Summary" subtitle="Next 72 h of forecast hours">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs text-muted">
                      <tr><th className="py-2">City</th><th>Min</th><th>Average</th><th>Max</th><th>Hours Poor or worse</th><th>Category (avg)</th></tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.series).map(([c, pts], i) => {
                        const v = pts.map((p) => p.pm25)
                        const avg = v.reduce((a, b) => a + b, 0) / v.length
                        return (
                          <tr key={c} className="border-t border-card-border tnum">
                            <td className="py-2 font-medium"><span className="mr-2 inline-block size-2.5 rounded-full" style={{ background: SERIES_COLORS[i] }} />{c}</td>
                            <td>{Math.round(Math.min(...v))}</td><td>{Math.round(avg)}</td><td>{Math.round(Math.max(...v))}</td>
                            <td>{v.filter((x) => x > 90).length}</td><td><AqiBadge category={naqi(avg).name} /></td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </>
  )
}
