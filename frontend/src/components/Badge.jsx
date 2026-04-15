import { cn } from '../lib/cn.js'

// Цвета по статусам воронки
const statusClasses = {
  new: 'bg-slate-100 text-slate-700',
  contacted: 'bg-blue-100 text-blue-700',
  follow_up_1: 'bg-blue-50 text-blue-600',
  follow_up_2: 'bg-blue-50 text-blue-600',
  follow_up_3: 'bg-amber-50 text-amber-700',
  replied: 'bg-cyan-100 text-cyan-700',
  interested: 'bg-emerald-100 text-emerald-700',
  negotiating: 'bg-emerald-100 text-emerald-700',
  warm: 'bg-orange-100 text-orange-700',
  transferred: 'bg-purple-100 text-purple-700',
  rejected: 'bg-red-100 text-red-700',
  unsubscribed: 'bg-zinc-200 text-zinc-700',
  // message status
  draft: 'bg-yellow-100 text-yellow-700',
  queued: 'bg-blue-50 text-blue-600',
  sent: 'bg-emerald-100 text-emerald-700',
  received: 'bg-cyan-100 text-cyan-700',
  failed: 'bg-red-100 text-red-700',
  bounced: 'bg-red-100 text-red-700',
}

export function Badge({ variant, children, className }) {
  const tone = statusClasses[variant] || 'bg-muted text-foreground'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        tone,
        className,
      )}
    >
      {children || variant}
    </span>
  )
}
