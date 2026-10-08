import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Card({ title, subtitle, right, children, className }: {
  title?: string; subtitle?: string; right?: ReactNode; children: ReactNode; className?: string
}) {
  return (
    <section className={cn('glass p-5', className)}>
      {(title || right) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="font-display text-base font-semibold">{title}</h2>}
            {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-xl bg-slate-400/20', className)} aria-hidden />
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="glass flex flex-col items-center gap-3 p-8 text-center">
      <AlertTriangle className="text-amber-500" />
      <p className="font-medium">Couldn't load data</p>
      <p className="max-w-md text-sm text-muted">{error instanceof Error ? error.message : 'Unknown error'}. Is the API running on port 8000?</p>
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-1.5 text-sm text-white">
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 p-8 text-center text-muted">
      <Inbox /> <p className="text-sm">{text}</p>
    </div>
  )
}
