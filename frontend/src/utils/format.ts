import { format, formatDistanceToNow } from 'date-fns'

export const fmtNum = (v: number | null | undefined, d = 0) =>
  v == null || Number.isNaN(v) ? '–' : v.toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d })
export const fmtTime = (iso: string) => format(new Date(iso), 'EEE d MMM, h a')
export const fmtHour = (iso: string) => format(new Date(iso), 'EEE h a')
export const fmtShortTime = (iso: string) => format(new Date(iso), 'h a')
export const fmtAgo = (iso: string) => formatDistanceToNow(new Date(iso), { addSuffix: true })
