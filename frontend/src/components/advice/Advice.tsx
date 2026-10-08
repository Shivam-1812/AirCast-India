import { useState } from 'react'
import { Baby, Dumbbell, HeartPulse, ShieldCheck, Clock } from 'lucide-react'
import { Card, Skeleton } from '@/components/common/ui'
import AqiBadge from '@/components/aqi/AqiBadge'
import { useAdvisory, useBestTime } from '@/hooks/useApi'
import { fmtHour, fmtShortTime } from '@/utils/format'

const TABS = [
  { k: 'general', label: 'General', icon: ShieldCheck }, { k: 'children', label: 'Children', icon: Baby },
  { k: 'asthma_elderly', label: 'Asthma / Elderly', icon: HeartPulse }, { k: 'exercise', label: 'Exercise', icon: Dumbbell },
]

export function HealthAdvisoryCard({ category }: { category: string }) {
  const { data } = useAdvisory(category)
  const [tab, setTab] = useState('general')
  return (
    <Card title="Health advice" subtitle="Based on the expected category for the next 24 h" right={<AqiBadge category={category} />}>
      {!data ? <Skeleton className="h-24" /> : (
        <>
          <div role="tablist" className="mb-3 flex flex-wrap gap-1.5">
            {TABS.map(({ k, label, icon: I }) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition ${tab === k ? 'bg-accent text-white' : 'bg-white/30 hover:bg-white/50 dark:bg-white/5 dark:hover:bg-white/10'}`}>
                <I size={13} /> {label}
              </button>
            ))}
          </div>
          <p className="text-sm leading-relaxed" role="tabpanel">{data.groups[tab]}</p>
          <p className="mt-3 text-xs text-muted">{data.summary}</p>
        </>
      )}
    </Card>
  )
}

export function BestTimeCard({ city }: { city: string }) {
  const { data } = useBestTime(city)
  return (
    <Card title="Best time outdoors" subtitle="Cleanest 3-hour window in the next 48 h" right={<Clock size={18} className="text-accent" />}>
      {!data ? <Skeleton className="h-20" /> : (
        <div>
          <div className="font-display text-2xl font-bold">{fmtHour(data.start)} – {fmtShortTime(data.end)}</div>
          <div className="mt-1 flex items-center gap-2 text-sm"><span className="tnum">≈ {Math.round(data.mean_pm25)} µg/m³</span><AqiBadge category={data.category} /></div>
          <p className="mt-3 text-xs text-muted">Worst window: {fmtHour(data.worst_start)} (≈ {Math.round(data.worst_mean_pm25)} µg/m³).</p>
        </div>
      )}
    </Card>
  )
}
