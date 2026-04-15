import { Card, CardBody } from './Card.jsx'
import { cn } from '../lib/cn.js'

export function StatsCard({ label, value, hint, tone }) {
  return (
    <Card>
      <CardBody>
        <div className="text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div
          className={cn(
            'mt-1 text-2xl font-semibold',
            tone === 'warn' && 'text-amber-600',
            tone === 'ok' && 'text-emerald-600',
            tone === 'danger' && 'text-red-600',
          )}
        >
          {value}
        </div>
        {hint ? (
          <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
        ) : null}
      </CardBody>
    </Card>
  )
}
