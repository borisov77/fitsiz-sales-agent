import { cn } from '../lib/cn.js'

// FITSIZ toggle — pill-переключатель, зелёный во включённом состоянии.
export function Switch({ checked, onChange, disabled = false, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      className={cn(
        'relative inline-flex h-7 w-12 shrink-0 items-center rounded-pill transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fitsiz-lime focus-visible:ring-offset-2 focus-visible:ring-offset-fitsiz-black',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        checked ? 'bg-fitsiz-green' : 'bg-fitsiz-surface-3',
      )}
      aria-label={label}
    >
      <span
        className={cn(
          'inline-block h-5 w-5 transform rounded-full bg-white transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1',
        )}
      />
    </button>
  )
}
