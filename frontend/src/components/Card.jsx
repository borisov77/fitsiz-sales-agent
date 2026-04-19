import { cn } from '../lib/cn.js'

// FITSIZ card — surface-1 фон, радиус 24px, без теней.
// Большие карточки — 32px, акцентная — зелёная плашка (чёрный текст).

export function Card({ className, variant = 'default', children, ...props }) {
  const tones = {
    default: 'bg-fitsiz-surface-1 text-fitsiz-white',
    lg: 'bg-fitsiz-surface-1 text-fitsiz-white rounded-card-lg',
    accent: 'bg-fitsiz-green text-fitsiz-black',
    lime: 'bg-fitsiz-lime text-fitsiz-black',
    outline:
      'bg-transparent text-fitsiz-white border border-fitsiz-border',
  }
  return (
    <div
      className={cn(
        'rounded-card',
        tones[variant],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children }) {
  return (
    <div
      className={cn(
        'border-b border-fitsiz-border/70 px-6 py-4',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function CardTitle({ className, children }) {
  return (
    <h3
      className={cn(
        'font-body text-[13px] font-bold uppercase tracking-cta text-fitsiz-white',
        className,
      )}
    >
      {children}
    </h3>
  )
}

export function CardBody({ className, children }) {
  return <div className={cn('p-6', className)}>{children}</div>
}
