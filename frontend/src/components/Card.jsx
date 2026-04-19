import { cn } from '../lib/cn.js'

// FITSIZ card — surface-1, радиус 24-32px, без теней, с большим воздухом.

export function Card({ className, variant = 'default', children, ...props }) {
  const tones = {
    default: 'bg-fitsiz-surface-1 text-fitsiz-white rounded-card-lg',
    lg: 'bg-fitsiz-surface-1 text-fitsiz-white rounded-card-lg',
    accent: 'bg-fitsiz-green text-fitsiz-black rounded-card-lg',
    lime: 'bg-fitsiz-lime text-fitsiz-black rounded-card-lg',
    outline:
      'bg-transparent text-fitsiz-white border border-fitsiz-border rounded-card-lg',
  }
  return (
    <div
      className={cn(tones[variant], className)}
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
        'border-b border-fitsiz-border/70 px-8 py-5',
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
        'font-body text-[15px] font-bold uppercase tracking-cta text-fitsiz-white',
        className,
      )}
    >
      {children}
    </h3>
  )
}

export function CardBody({ className, children }) {
  return <div className={cn('p-8', className)}>{children}</div>
}
