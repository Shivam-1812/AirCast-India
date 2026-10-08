import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import type { OverviewItem } from '@/api/endpoints'
import AqiBadge from '@/components/aqi/AqiBadge'

function useDark() {
  const [d, setD] = useState(document.documentElement.classList.contains('dark'))
  useEffect(() => {
    const o = new MutationObserver(() => setD(document.documentElement.classList.contains('dark')))
    o.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => o.disconnect()
  }, [])
  return d
}

export default function IndiaMap({ items }: { items: OverviewItem[] }) {
  const nav = useNavigate()
  const dark = useDark()
  return (
    <div className="h-[420px] overflow-hidden rounded-2xl" role="application" aria-label="Map of India with PM2.5 per city">
      <MapContainer center={[22.5, 79]} zoom={5} minZoom={4} scrollWheelZoom={false} className="size-full" attributionControl>
        <TileLayer
          key={dark ? 'd' : 'l'}
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors" className={dark ? "map-dark" : ""}
        />
        {items.map((c) => (
          <CircleMarker
            key={c.city}
            center={[c.lat, c.lon]}
            radius={10 + Math.min(c.pm25, 250) / 14}
            pathOptions={{ color: '#fff', weight: 2, fillColor: c.color, fillOpacity: 0.9 }}
            eventHandlers={{ click: () => nav(`/city/${c.city}`) }}
          >
            <Tooltip direction="top" permanent className="!bg-transparent !border-0 !shadow-none !font-semibold !text-[11px]">
              {Math.round(c.pm25)}
            </Tooltip>
            <Popup>
              <div className="min-w-40 text-sm">
                <b>{c.city}</b>
                <div className="mt-1 flex items-center gap-2"><span className="tnum">{Math.round(c.pm25)} µg/m³</span><AqiBadge category={c.category} /></div>
                <div className="mt-1 text-xs">In 24 h: <b>{Math.round(c.pred_24h)}</b> ({c.pred_category_24h})</div>
                <button className="mt-2 text-xs font-medium text-blue-600 underline" onClick={() => nav(`/city/${c.city}`)}>Open forecast</button>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
