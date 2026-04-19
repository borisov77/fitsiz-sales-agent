import { Card, CardBody } from './Card.jsx'
import { cn } from '../lib/cn.js'

// FITSIZ stats card — огромная цифра в Russo One, подпись в Inter uppercase.
// Акцентный вариант — зелёный фон с чёрным текстом.

export function StatsCard({ label, value, hint, tone = 'default', icon: Icon }) {
  const variant =
    tone === 'accent' ? 'accent' : tone === 'lime' ? 'lime' : 'default'

  const labelColor =
    variant === 'default' ? 'text-fitsiz-muted' : 'text-fitsiz-black/70'
  const hintColor =
    variant === 'default' ? 'text-fitsiz-muted' : 'text-fitsiz-black/70'

  const valueTone =
    variant !== 'default'
      ? '' // акцентные — чёрный текст из карточки
      : tone === 'warn'
      ? 'text-fitsiz-lime'
      : tone === 'ok'
      ? 'text-fitsiz-green'
      : tone === 'danger'
      ? 'text-red-400'
      : 'text-fitsiz-white'

  return (
    <Card variant={variant}>
      <CardBody>
        <div className="flex items-start justify-between gap-3">
          <div
            className={cn(
              'text-[11px] font-bold uppercase tracking-badge',
              labelColor,
            )}
          >
            {label}
          </div>
          {Icon ? (
            <Icon
              size={18}
              className={
                variant === 'default' ? 'text-fitsiz-muted' : 'text-fitsiz-black/70'
              }
            />
          ) : null}
        </div>
        <div
          className={cn(
            'mt-3 font-heading text-5xl leading-none tracking-heading',
            valueTone,
          )}
        >
          {value}
        </div>
        {hint ? (
          <div className={cn('mt-2 text-xs', hintColor)}>{hint}</div>
        ) : null}
      </CardBody>
    </Card>
  )
}
