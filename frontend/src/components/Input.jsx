import { cn } from '../lib/cn.js'

// FITSIZ inputs — крупнее, зелёный фокус-кольцо, радиус chip 16px.

const baseField =
  'w-full bg-fitsiz-surface-1 text-fitsiz-white placeholder:text-fitsiz-muted ' +
  'border border-fitsiz-border rounded-chip transition-colors ' +
  'focus-visible:outline-none focus-visible:border-fitsiz-green ' +
  'focus-visible:ring-1 focus-visible:ring-fitsiz-green ' +
  'disabled:opacity-50 disabled:cursor-not-allowed'

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(baseField, 'h-12 px-5 py-1 text-[15px]', className)}
      {...props}
    />
  )
}

export function Textarea({ className, ...props }) {
  return (
    <textarea
      className={cn(
        baseField,
        'px-5 py-4 text-[15px] leading-relaxed',
        className,
      )}
      {...props}
    />
  )
}

export function Select({ className, children, ...props }) {
  return (
    <select
      className={cn(baseField, 'h-12 px-5 py-1 text-[15px]', className)}
      {...props}
    >
      {children}
    </select>
  )
}
