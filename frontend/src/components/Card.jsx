import { cn } from '../lib/cn.js'

export function Card({ className, children, ...props }) {
  return (
    <div
      className={cn('rounded-lg border border-border bg-white shadow-sm', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children }) {
  return (
    <div className={cn('border-b border-border p-4', className)}>{children}</div>
  )
}

export function CardTitle({ className, children }) {
  return (
    <h3 className={cn('text-sm font-semibold tracking-tight', className)}>
      {children}
    </h3>
  )
}

export function CardBody({ className, children }) {
  return <div className={cn('p-4', className)}>{children}</div>
}
