import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, BellRing, ShieldCheck } from 'lucide-react'
import { BlurFade } from '@/components/ui/blur-fade'
import { BorderBeam } from '@/components/ui/border-beam'
import SkyBackground from '@/components/layout/SkyBackground'
import Gauge from '@/components/aqi/Gauge'
import SmogScene from '@/components/aqi/SmogScene'
import { PollutantTiles, WeatherTiles } from '@/components/aqi/Tiles'
import ForecastChart from '@/components/charts/ForecastChart'
import { FactorBars } from '@/components/charts/Bars'
import { BestTimeCard, HealthAdvisoryCard } from '@/components/advice/Advice'
import AqiBadge from '@/components/aqi/AqiBadge'
import { Card, ErrorState, Skeleton } from '@/components/common/ui'
import { useCurrent, useExplain, useForecast, useHistory } from '@/hooks/useApi'
import { CITIES } from '@/utils/cities'
import { fmtTime } from '@/utils/format'

export default function CityDetail() {
  const { name = '' } = useParams()
  const city = CITIES.find((c) => c.toLowerCase() === name.toLowerCase())
  if (!city) return <div className="mx-auto max-w-3xl px-4 pt-10"><ErrorState error={new Error(`Unknown city "${name}"`)} /></div>
  return <CityView city={city} />
}

function CityView({ city }: { city: string }) {
  const cur = useCurrent(city)
  const fc = useForecast(city)
  const hist = useHistory(city, 168)
  const ex = useExplain(city)
  const pm = cur.data?.pollutants.pm25 ?? undefined

  if (cur.error || fc.error) return <div className="mx-auto max-w-3xl px-4 pt-10"><ErrorState error={cur.error ?? fc.error} onRetry={() => { cur.refetch(); fc.refetch() }} /></div>
  const pct = fc.data ? Math.round(fc.data.alert_score * 100) : 0

  return (
    <>
      <SkyBackground pm25={pm ?? 25} />
      <div className="mx-auto max-w-6xl space-y-6 px-4 pt-8">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground"><ArrowLeft size={14} /> All cities</Link>

        <BlurFade>
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <div className="glass relative flex flex-col items-center gap-4 p-6">
              <h1 className="font-display text-3xl font-bold">{city}</h1>
              {pm == null ? <Skeleton className="size-52 !rounded-full" /> : <Gauge pm25={pm} />}
              {cur.data && <p className="text-xs text-muted">Observed {fmtTime(cur.data.observed_at)}</p>}
              {cur.data?.us_aqi != null && <p className="text-xs text-muted">US AQI (model) {Math.round(cur.data.us_aqi)}</p>}
            </div>
            <div className="glass relative overflow-hidden p-0">
              <div className="absolute left-4 top-4 z-10 rounded-lg bg-black/40 px-2.5 py-1 text-xs text-white backdrop-blur">Live particle view · drag to rotate</div>
              {pm == null ? <Skeleton className="h-full min-h-72" /> : (
                <SmogScene pm25={pm} windSpeed={cur.data?.weather.wind_speed ?? 8} windDeg={180} className="h-72 lg:h-full lg:min-h-80" />
              )}
              <BorderBeam size={120} duration={10} />
            </div>
          </div>
        </BlurFade>

        <BlurFade delay={0.1}>
          <div className="space-y-3">
            {cur.data ? <WeatherTiles w={cur.data.weather} /> : <Skeleton className="h-20" />}
            {cur.data ? <PollutantTiles p={cur.data.pollutants} /> : <Skeleton className="h-20" />}
          </div>
        </BlurFade>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2" title="Next 72 hours" subtitle="PM2.5 forecast with 80% range · bands show NAQI categories"
            right={fc.data && <AqiBadge category={fc.data.category_24h} />}>
            {fc.data ? <ForecastChart points={fc.data.points} /> : <Skeleton className="h-80" />}
          </Card>
          <Card title="Next-24 h alert" subtitle="Poor or worse air (daily PM2.5 > 90 µg/m³)">
            {fc.data ? (
              <div>
                <div className="flex items-center gap-2">
                  {fc.data.alert_24h ? <BellRing className="text-red-500" /> : <ShieldCheck className="text-emerald-500" />}
                  <span className="font-display text-3xl font-bold tnum">{pct}%</span>
                  <span className="text-xs text-muted">alert score</span>
                </div>
                <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-400/25" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                  <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${pct}%`, background: fc.data.alert_24h ? '#ef4444' : '#22c55e' }} />
                </div>
                <p className="mt-3 text-sm">{fc.data.alert_24h ? 'Poor or worse air is likely. Plan to limit outdoor exposure.' : 'Air is not expected to reach the Poor category tomorrow.'}</p>
                <p className="mt-2 text-xs text-muted">Expected 24 h average: <b className="tnum">{Math.round(fc.data.mean_24h)}</b> µg/m³. The score is an uncalibrated model output, not a literal probability.</p>
              </div>
            ) : <Skeleton className="h-40" />}
          </Card>
        </div>

        <Card title="Last 7 days → next 3 days" subtitle="Observed (dark line) joined to forecast (blue)">
          {fc.data && hist.data ? <ForecastChart points={fc.data.points} history={hist.data} height={300} /> : <Skeleton className="h-72" />}
        </Card>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2" title="Why this forecast?" subtitle="Top factors moving the 24 h forecast, via SHAP">
            {ex.isLoading ? <Skeleton className="h-52" /> : ex.error ? <p className="text-sm text-muted">Explanations unavailable.</p> : ex.data && (
              <div className="grid gap-4 md:grid-cols-2">
                <FactorBars factors={ex.data.factors} />
                <ul className="space-y-2 text-sm">
                  {ex.data.factors.map((f) => (
                    <li key={f.label} className="flex gap-2"><span className={f.direction === 'up' ? 'text-orange-500' : 'text-emerald-600'}>{f.direction === 'up' ? '▲' : '▼'}</span>{f.text}</li>
                  ))}
                  <li className="pt-1 text-xs text-muted">Baseline average prediction: {Math.round(ex.data.base_value)} µg/m³.</li>
                </ul>
              </div>
            )}
          </Card>
          <div className="space-y-6">
            <BestTimeCard city={city} />
            {fc.data && <HealthAdvisoryCard category={fc.data.category_24h} />}
          </div>
        </div>
      </div>
    </>
  )
}
