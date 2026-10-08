import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { ArrowDownRight, ArrowRight, ArrowUpRight, BellRing, RefreshCw, Search } from 'lucide-react'
import { useIsFetching, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import Globe3D from '@/components/aqi/Globe3D'
import { NumberTicker } from '@/components/ui/number-ticker'
import { BlurFade } from '@/components/ui/blur-fade'
import { MagicCard } from '@/components/ui/magic-card'
import { BorderBeam } from '@/components/ui/border-beam'
import { AnimatedShinyText } from '@/components/ui/animated-shiny-text'
import AqiBadge from '@/components/aqi/AqiBadge'
import IndiaMap from '@/components/map/IndiaMap'
import SkyBackground from '@/components/layout/SkyBackground'
import { Card, ErrorState, Skeleton } from '@/components/common/ui'
import { useHealth, useOverview } from '@/hooks/useApi'
import type { OverviewItem } from '@/api/endpoints'
import { fmtAgo } from '@/utils/format'

function Trend({ t }: { t: OverviewItem['trend'] }) {
  if (t === 'worse') return <span className="inline-flex items-center gap-0.5 text-red-500"><ArrowUpRight size={14} />worse</span>
  if (t === 'better') return <span className="inline-flex items-center gap-0.5 text-emerald-600"><ArrowDownRight size={14} />better</span>
  return <span className="inline-flex items-center gap-0.5 text-muted"><ArrowRight size={14} />steady</span>
}

export default function Dashboard() {
  const { data, error, refetch, isLoading } = useOverview()
  const { data: health } = useHealth()
  const qc = useQueryClient()
  const fetching = useIsFetching() > 0
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<'pm25' | 'name'>('pm25')

  const list = useMemo(() => {
    const l = (data ?? []).filter((c) => c.city.toLowerCase().includes(q.toLowerCase()))
    return sort === 'pm25' ? l.sort((a, b) => b.pm25 - a.pm25) : l.sort((a, b) => a.city.localeCompare(b.city))
  }, [data, q, sort])

  const worst = data && [...data].sort((a, b) => b.pm25 - a.pm25)[0]
  const best = data && [...data].sort((a, b) => a.pm25 - b.pm25)[0]
  const alerts = data?.filter((c) => c.alert_24h).length ?? 0

  return (
    <>
      <SkyBackground pm25={worst?.pm25 ?? 25} />
      <section className="mx-auto grid max-w-6xl items-center gap-6 px-4 pt-10 lg:grid-cols-2">
        <div>
          <BlurFade delay={0.05}>
            <div className="glass mb-4 inline-flex items-center gap-2 px-3 py-1 text-xs">
              <span className="relative flex size-2"><span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400" /><span className="relative inline-flex size-2 rounded-full bg-emerald-500" /></span>
              <AnimatedShinyText>Live · {health ? `data from ${fmtAgo(health.latest_data_timestamp)}` : 'connecting…'}</AnimatedShinyText>
            </div>
          </BlurFade>
          <BlurFade delay={0.12}>
            <h1 className="font-display text-4xl font-extrabold leading-[1.05] sm:text-6xl">
              Know the air<br /><span className="bg-gradient-to-r from-sky-500 to-blue-700 bg-clip-text text-transparent">before you breathe it.</span>
            </h1>
          </BlurFade>
          <BlurFade delay={0.2}>
            <p className="mt-4 max-w-md text-base text-muted">
              72-hour PM2.5 forecasts for 10 Indian cities, from an ensemble of gradient-boosted models that learn from pollution history and weather.
            </p>
          </BlurFade>
          <BlurFade delay={0.3}>
            <div className="mt-6 grid max-w-md grid-cols-3 gap-3">
              {[
                { l: 'Most polluted now', v: worst ? Math.round(worst.pm25) : null, s: worst?.city },
                { l: 'Cleanest now', v: best ? Math.round(best.pm25) : null, s: best?.city },
                { l: 'Cities with alerts', v: alerts, s: 'next 24 h' },
              ].map((s) => (
                <div key={s.l} className="glass p-3">
                  <div className="font-display text-2xl font-bold tnum">{s.v == null ? '–' : <NumberTicker value={s.v} />}</div>
                  <div className="text-[11px] leading-tight text-muted">{s.l}</div>
                  <div className="text-[11px] font-semibold">{s.s}</div>
                </div>
              ))}
            </div>
          </BlurFade>
        </div>
        <div className="relative mx-auto aspect-square w-full max-w-md" role="img" aria-label="Interactive 3D globe with coloured markers for the ten tracked cities">
          <div className="absolute inset-8 rounded-full bg-blue-500/20 blur-3xl" />
          {data && <Globe3D cities={data} />}
        </div>
      </section>

      <main className="mx-auto mt-10 max-w-6xl space-y-6 px-4">
        {error ? <ErrorState error={error} onRetry={() => refetch()} /> : (
          <>
            <Card title="Air quality map" subtitle="PM2.5 now · click a city for its forecast">
              {isLoading ? <Skeleton className="h-[420px]" /> : <IndiaMap items={data!} />}
            </Card>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-xl font-semibold">Cities</h2>
              <div className="flex flex-wrap items-center gap-2">
                <label className="glass flex items-center gap-2 px-3 py-1.5 text-sm">
                  <Search size={14} className="text-muted" />
                  <input aria-label="Search cities" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search city" className="w-32 bg-transparent outline-none placeholder:text-muted" />
                </label>
                <select aria-label="Sort cities" value={sort} onChange={(e) => setSort(e.target.value as 'pm25' | 'name')} className="glass px-3 py-1.5 text-sm outline-none">
                  <option value="pm25">Most polluted first</option>
                  <option value="name">Name A–Z</option>
                </select>
                <button
                  onClick={() => qc.invalidateQueries().then(() => toast.success('Updated'), () => toast.error('Refresh failed'))}
                  className="glass inline-flex items-center gap-1.5 px-3 py-1.5 text-sm" aria-label="Refresh data"
                >
                  <RefreshCw size={14} className={fetching ? 'animate-spin' : ''} /> Refresh
                </button>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {isLoading && Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-44" />)}
              {!isLoading && list.length === 0 && <p className="col-span-full py-10 text-center text-muted">No city matches “{q}”.</p>}
              {list.map((c, i) => (
                <BlurFade key={c.city} delay={0.04 * i}>
                  <Link to={`/city/${c.city}`} className="block rounded-[1.25rem] outline-offset-4 focus-visible:outline-2">
                    <motion.div whileHover={{ y: -4 }} className="relative">
                      <MagicCard className="glass !rounded-[1.25rem]" gradientColor="rgba(120,170,255,0.18)">
                        <div className="p-5">
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="font-display text-lg font-semibold">{c.city}</h3>
                              <AqiBadge category={c.category} />
                            </div>
                            {c.alert_24h && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 px-2 py-0.5 text-[11px] font-semibold text-red-600 dark:text-red-400" title="Poor or worse air expected in the next 24 h">
                                <BellRing size={12} /> Alert
                              </span>
                            )}
                          </div>
                          <div className="mt-4 flex items-end justify-between">
                            <div>
                              <div className="font-display text-4xl font-bold tnum" style={{ color: c.color }}>{Math.round(c.pm25)}</div>
                              <div className="text-[11px] text-muted">µg/m³ PM2.5 now</div>
                            </div>
                            <div className="text-right text-xs">
                              <div className="text-muted">In 24 h</div>
                              <div className="font-semibold tnum">{Math.round(c.pred_24h)} · {c.pred_category_24h}</div>
                              <Trend t={c.trend} />
                            </div>
                          </div>
                        </div>
                        {c.alert_24h && <BorderBeam size={90} duration={6} colorFrom="#ff6a3d" colorTo="#ff0000" />}
                      </MagicCard>
                    </motion.div>
                  </Link>
                </BlurFade>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  )
}
