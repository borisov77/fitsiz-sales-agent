import { cn } from '../lib/cn.js'

const variants = {
  primary:
    'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50',
  secondary:
    'bg-muted text-foreground hover:bg-muted/70 disabled:opacity-50',
  outline:
    'border border-border bg-background hover:bg-muted disabled:opacity-50',
  danger:
    'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50',
  ghost: 'hover:bg-muted disabled:opacity-50',
}

const sizes = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-4 text-sm',
  lg: 'h-10 px-5 text-sm',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
