import { BlurFade } from '@/components/ui/blur-fade'
import SkyBackground from '@/components/layout/SkyBackground'
import { Card } from '@/components/common/ui'
import { NAQI } from '@/utils/aqi'

const SOURCES = [
  ['Open-Meteo Air Quality API', 'https://open-meteo.com/en/docs/air-quality-api', 'Hourly PM2.5, PM10, NO₂, SO₂, O₃, CO from Copernicus CAMS: the forecast target and pollutant history.'],
  ['Open-Meteo Historical Weather API', 'https://open-meteo.com/en/docs/historical-weather-api', 'ERA5 reanalysis weather: temperature, humidity, pressure, wind, rain.'],
  ['Open-Meteo Forecast API', 'https://open-meteo.com/en/docs', 'Fills the most recent days so data is current.'],
  ['CPCB National AQI', 'https://cpcb.nic.in', 'Category cut-offs for PM2.5 used for labels and colours.'],
]

export default function About() {
  return (
    <>
      <SkyBackground pm25={25} />
      <div className="mx-auto max-w-4xl space-y-6 px-4 pt-8">
        <BlurFade>
          <h1 className="font-display text-3xl font-bold">About AirCast India</h1>
          <p className="mt-1 text-muted">An open, educational forecasting project: how bad will the air be over the next three days?</p>
        </BlurFade>
        <Card title="Data sources">
          <ul className="space-y-3 text-sm">
            {SOURCES.map(([t, u, d]) => (
              <li key={t}><a href={u} target="_blank" rel="noreferrer" className="font-medium text-accent underline">{t}</a><p className="text-muted">{d}</p></li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-muted">Open-Meteo data is licensed CC BY 4.0. Data: Open-Meteo, Copernicus CAMS, ERA5.</p>
        </Card>
        <Card title="How we forecast">
          <p className="text-sm leading-relaxed">
            Hourly pollution and weather for ten cities feed a feature pipeline (lags, rolling statistics, weather, calendar). Gradient boosting, random forest, ridge and a stacking
            ensemble are compared with persistence baselines on chronological hold-out sets. The best model per horizon serves the forecast; SHAP explains it.
          </p>
        </Card>
        <Card title="PM2.5 categories (24 h average)">
          <div className="grid gap-2 sm:grid-cols-2">
            {NAQI.map((c, i) => (
              <div key={c.name} className="flex items-center gap-3 text-sm">
                <span className="size-4 rounded" style={{ background: c.color }} />
                <b className="w-28">{c.name}</b>
                <span className="tnum text-muted">{i === 0 ? '0–30' : i === NAQI.length - 1 ? '250+' : `${NAQI[i - 1].max + 1}–${c.max}`} µg/m³</span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Limitations and disclaimer">
          <ul className="list-disc space-y-1.5 pl-5 text-sm">
            <li>Values come from a global atmospheric model, not ground monitors, and can differ from station readings.</li>
            <li>Sudden spikes (fires, Diwali, dust storms) are the hardest to predict and error grows with horizon.</li>
            <li>This is an educational project. It is not an official AQI source and not medical advice.</li>
          </ul>
        </Card>
      </div>
    </>
  )
}
