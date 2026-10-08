import { BlurFade } from '@/components/ui/blur-fade'
import SkyBackground from '@/components/layout/SkyBackground'
import { Card, ErrorState, Skeleton } from '@/components/common/ui'
import { ErrorByHorizon, ImportanceBar, ModelVsBaseline } from '@/components/charts/Bars'
import { useImportance, usePerformance } from '@/hooks/useApi'

const f = (v: number | undefined, d = 1) => (v == null ? '–' : v.toFixed(d))

export default function ModelInsights() {
  const perf = usePerformance()
  const imp = useImportance()
  if (perf.error) return <div className="mx-auto max-w-3xl px-4 pt-10"><ErrorState error={perf.error} onRetry={() => perf.refetch()} /></div>

  const rows = perf.data?.table ?? []
  const chosen: Record<number, string> = {}
  Object.entries(perf.data?.metadata.horizons ?? {}).forEach(([h, v]: [string, any]) => (chosen[+h] = v.model))
  const headline = [6, 24, 48, 72]

  return (
    <>
      <SkyBackground pm25={40} />
      <div className="mx-auto max-w-6xl space-y-6 px-4 pt-8">
        <BlurFade>
          <h1 className="font-display text-3xl font-bold">Model insights</h1>
          <p className="text-sm text-muted">How well does AirCast forecast, and against what? All numbers are measured on data the models never saw during training.</p>
        </BlurFade>

        <Card title="Accuracy by horizon" subtitle="Best model per horizon vs. persistence ('tomorrow = today'). Lower RMSE is better.">
          {perf.isLoading ? <Skeleton className="h-64" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm tnum">
                <thead className="text-left text-xs text-muted">
                  <tr><th className="py-2">Horizon</th><th>Model</th><th>Test</th><th>MAE</th><th>RMSE</th><th>R²</th><th>Persistence RMSE</th><th>Skill vs persistence</th></tr>
                </thead>
                <tbody>
                  {headline.flatMap((h) => ['A_recent90d', 'B_winter'].map((t) => {
                    const m = rows.find((r) => r.horizon === h && r.test === t && r.model === chosen[h])
                    const b = rows.find((r) => r.horizon === h && r.test === t && r.model === 'Persistence')
                    if (!m) return null
                    return (
                      <tr key={`${h}${t}`} className="border-t border-card-border">
                        <td className="py-2 font-medium">{h} h</td><td>{m.model}</td><td>{t === 'A_recent90d' ? 'A · last 90 d' : 'B · winter'}</td>
                        <td>{f(m.MAE)}</td><td>{f(m.RMSE)}</td><td>{f(m.R2, 2)}</td><td>{f(b?.RMSE)}</td>
                        <td className={m.skill_vs_persistence > 0 ? 'font-semibold text-emerald-600' : 'font-semibold text-red-500'}>{(m.skill_vs_persistence * 100).toFixed(0)}%</td>
                      </tr>
                    )
                  }))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Model vs baseline" subtitle="RMSE on Test A (most recent 90 days), µg/m³">
            {perf.isLoading ? <Skeleton className="h-64" /> : <ModelVsBaseline rows={rows.filter((r) => r.test === 'A_recent90d')} model={chosen} />}
          </Card>
          <Card title="Error grows with horizon" subtitle="Mean absolute error of the chosen model, µg/m³">
            {perf.isLoading ? <Skeleton className="h-64" /> : <ErrorByHorizon rows={rows} model={chosen} />}
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="What drives the forecast" subtitle="Mean |SHAP| for the 24 h model, grouped by feature meaning">
            {imp.isLoading ? <Skeleton className="h-64" /> : imp.data && <ImportanceBar data={imp.data} />}
          </Card>
          <Card title="24-hour alert classifier" subtitle="Will tomorrow's average PM2.5 exceed 90 µg/m³?">
            <table className="w-full text-sm tnum">
              <thead className="text-left text-xs text-muted"><tr><th className="py-2">Test</th><th>Precision</th><th>Recall</th><th>F1</th><th>PR-AUC</th></tr></thead>
              <tbody>
                {(perf.data?.alert ?? []).map((a) => (
                  <tr key={a.test} className="border-t border-card-border">
                    <td className="py-2">{a.test === 'A_recent90d' ? 'A · last 90 d' : 'B · winter'}</td>
                    <td>{f(a.precision, 2)}</td><td>{f(a.recall, 2)}</td><td>{f(a.f1, 2)}</td><td>{f(a.pr_auc, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-muted">The decision threshold was tuned on a validation block for ≥ 80% recall, so missing a Poor-air day is less likely than a false alarm.</p>
          </Card>
        </div>

        <Card title="Method and limitations">
          <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
            <li>Targets are PM2.5 at +6, 12, 24, 36, 48, 60 and 72 h per city; the hourly curve is interpolated between those horizons.</li>
            <li>Features use only past data: PM2.5 lags and rolling windows, weather, calendar and Diwali flags, city location. A unit test proves no future leakage.</li>
            <li>Splits are chronological with a 72 h gap. Test A is the latest 90 days; Test B is the Nov 2025–Feb 2026 winter.</li>
            <li>The data is <b>modelled</b> (Copernicus CAMS) rather than from ground sensors, so it approximates station readings.</li>
            <li>Forecasts do not use future weather, so errors are larger at longer horizons and for sudden spikes.</li>
          </ul>
        </Card>
      </div>
    </>
  )
}
