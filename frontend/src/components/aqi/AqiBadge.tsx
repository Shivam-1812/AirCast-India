import { naqi, onColor, categoryColor } from '@/utils/aqi'

/** Category pill. Pass pm25 (derives category) or a category name. Always shows text, never colour alone. */
export default function AqiBadge({ pm25, category, className = '' }: { pm25?: number; category?: string; className?: string }) {
  const name = category ?? naqi(pm25 ?? 0).name
  return (
    <span
      data-testid="aqi-badge"
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}
      style={{ background: categoryColor(name), color: onColor(name) }}
    >
      {name}
    </span>
  )
}
