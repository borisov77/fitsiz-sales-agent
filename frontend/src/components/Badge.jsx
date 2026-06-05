import { cn } from '../lib/cn.js'
import {
  LEAD_STATUS_RU,
  MESSAGE_STATUS_RU,
} from '../lib/labels.js'

// FITSIZ badge — pill, uppercase, чуть крупнее для читабельности.
// Если variant совпадает со статусом лида или сообщения — подставим
// русскую подпись. `children` override'ит всё.

const statusClasses = {
  // --- Бизнес-статусы лида (7) ---
  created: 'bg-fitsiz-surface-2 text-fitsiz-muted-light ring-1 ring-fitsiz-border',
  // `sent` — и статус лида («Отправлено»), и статус сообщения («Отправлено»):
  // один зелёный тон обслуживает оба, смысл совпадает.
  sent: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  in_dialog: 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40',
  handed_to_manager: 'bg-fitsiz-lime text-fitsiz-black',
  won: 'bg-fitsiz-green text-fitsiz-black',
  lost: 'bg-red-900/30 text-red-400 ring-1 ring-red-500/30',
  no_reply: 'bg-fitsiz-surface-2 text-fitsiz-muted ring-1 ring-fitsiz-border',
  // --- Статусы сообщений ---
  draft: 'bg-fitsiz-lime/15 text-fitsiz-lime ring-1 ring-fitsiz-lime/40',
  queued: 'bg-fitsiz-surface-2 text-fitsiz-white ring-1 ring-fitsiz-border',
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
