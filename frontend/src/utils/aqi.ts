export const NAQI = [
  { max: 30, name: 'Good', color: '#00b050', sky: ['#6fc2ff', '#e8f6ff'], haze: 0 },
  { max: 60, name: 'Satisfactory', color: '#92d050', sky: ['#7fb8ff', '#eef4fb'], haze: 0.15 },
  { max: 90, name: 'Moderate', color: '#ffd966', sky: ['#a9bfd6', '#f3ead3'], haze: 0.35 },
  { max: 120, name: 'Poor', color: '#ff9900', sky: ['#c4a77e', '#efd9b4'], haze: 0.6 },
  { max: 250, name: 'Very Poor', color: '#ff0000', sky: ['#b0765d', '#d7a98a'], haze: 0.85 },
  { max: Infinity, name: 'Severe', color: '#7f0000', sky: ['#7a4a40', '#a77b6a'], haze: 1 },
] as const

export type Category = (typeof NAQI)[number]['name']

export function naqi(pm25: number) {
  return NAQI.find((c) => pm25 <= c.max) ?? NAQI[NAQI.length - 1]
}
export const categoryColor = (name: string) => NAQI.find((c) => c.name === name)?.color ?? '#888'
export const categoryOrder = (name: string) => NAQI.findIndex((c) => c.name === name)
/** Readable text colour on top of a category colour. */
export const onColor = (name: string) => (['Good', 'Satisfactory', 'Moderate'].includes(name) ? '#0b1b2e' : '#ffffff')
