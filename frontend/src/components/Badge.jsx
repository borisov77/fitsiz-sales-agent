import { cn } from '../lib/cn.js'

// FITSIZ badge — pill, uppercase, 6px/12px padding.
// Цвета распределены по смыслу (не только бренд-палитра): статусы воронки
// нужно различать, поэтому для «нейтральных» состояний используем
// оттенки surface, а зелёный — только для ключевых «хороших» событий.

const statusClasses = {
  // Воронка — нейтральные/в работе
  new: 'bg-fitsiz-surface-2 text-fitsiz-muted-light ring-1 ring-fitsiz-border',
  contacted: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  follow_up_1: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  follow_up_2: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  follow_up_3: 'bg-fitsiz-surface-2 text-fitsiz-lime ring-1 ring-fitsiz-lime/40',
  replied: 'bg-fitsiz-lime/15 text-fitsiz-lime ring-1 ring-fitsiz-lime/40',
  // Воронка — прогресс
  interested: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  negotiating: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  warm: 'bg-fitsiz-green text-fitsiz-black',
  transferred: 'bg-fitsiz-lime text-fitsiz-black',
  // Воронка — стоп
  rejected: 'bg-red-900/30 text-red-400 ring-1 ring-red-500/30',
  unsubscribed: 'bg-fitsiz-surface-2 text-fitsiz-muted ring-1 ring-fitsiz-border',
  // Статусы сообщений
  draft: 'bg-fitsiz-lime/15 text-fitsiz-lime ring-1 ring-fitsiz-lime/40',
  queued: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  sent: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  received: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  failed: 'bg-red-900/30 text-red-400 ring-1 ring-red-500/30',
  bounced: 'bg-red-900/30 text-red-400 ring-1 ring-red-500/30',
}

export function Badge({ variant, children, className }) {
  const tone = statusClasses[variant] || 'bg-fitsiz-surface-2 text-fitsiz-white'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-pill px-2.5 py-[3px]',
        'font-body text-[10px] font-bold uppercase tracking-badge',
        tone,
        className,
      )}
    >
      {children || variant}
    </span>
  )
}
