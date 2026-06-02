import { cn } from '../lib/cn.js'
import {
  LEAD_STATUS_RU,
  MESSAGE_STATUS_RU,
} from '../lib/labels.js'

// FITSIZ badge — pill, uppercase, чуть крупнее для читабельности.
// Если variant совпадает со статусом лида или сообщения — подставим
// русскую подпись. `children` override'ит всё.

const statusClasses = {
  // Воронка — нейтральные/в работе
  new: 'bg-fitsiz-surface-2 text-fitsiz-muted-light ring-1 ring-fitsiz-border',
  contacted: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  follow_up_1: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  follow_up_2: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
  follow_up_3: 'bg-fitsiz-surface-2 text-fitsiz-muted-light ring-1 ring-fitsiz-border',
  // Диалог — единый акцент бренда (зелёный): это рабочая зона человека
  replied: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  interested: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  negotiating: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  warm: 'bg-fitsiz-green text-fitsiz-black',
  transferred: 'bg-fitsiz-lime text-fitsiz-black',
  // Воронка — стоп
  rejected: 'bg-red-900/30 text-red-400 ring-1 ring-red-500/30',
  unsubscribed: 'bg-fitsiz-surface-2 text-fitsiz-muted ring-1 ring-fitsiz-border',
  dead_email: 'bg-fitsiz-surface-2 text-fitsiz-muted ring-1 ring-fitsiz-border',
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
  const ruLabel =
    LEAD_STATUS_RU[variant] ?? MESSAGE_STATUS_RU[variant] ?? variant
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-pill px-3 py-1',
        'font-body text-[12px] font-bold uppercase tracking-badge',
        tone,
        className,
      )}
    >
      {children || ruLabel}
    </span>
  )
}
