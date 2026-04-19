import { cn } from '../lib/cn.js'

// FITSIZ button — pill, uppercase, green primary.
// Размер sm — это базовый pill, md/lg — крупнее для ключевых CTA.

const base =
  'inline-flex items-center justify-center gap-2 font-bold uppercase tracking-cta ' +
  'rounded-pill transition-colors transition-transform duration-100 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fitsiz-lime focus-visible:ring-offset-2 ' +
  'focus-visible:ring-offset-fitsiz-black active:scale-[0.98] ' +
  'disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap'

const variants = {
  primary:
    'bg-fitsiz-green text-fitsiz-black hover:bg-fitsiz-green-hover',
  lime:
    'bg-fitsiz-lime text-fitsiz-black hover:bg-fitsiz-lime-hover',
  ghost:
    'bg-transparent text-fitsiz-white ring-[1.5px] ring-inset ring-fitsiz-white ' +
    'hover:bg-fitsiz-white hover:text-fitsiz-black',
  // secondary — тёмный вариант без обводки, для второстепенных действий
  secondary:
    'bg-fitsiz-surface-2 text-fitsiz-white hover:bg-fitsiz-surface-3',
  outline:
    'bg-transparent text-fitsiz-white ring-[1px] ring-inset ring-fitsiz-border ' +
    'hover:bg-fitsiz-surface-1',
  danger:
    'bg-red-600 text-white hover:bg-red-500',
}

const sizes = {
  xs: 'h-7 px-3 text-[11px]',
  sm: 'h-8 px-4 text-[12px]',
  md: 'h-10 px-5 text-[13px]',
  lg: 'h-12 px-7 text-[14px]',
}

export function Button({
  variant = 'primary',
  size = 'sm',
  className,
  children,
  ...props
}) {
  return (
    <button
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  )
}
