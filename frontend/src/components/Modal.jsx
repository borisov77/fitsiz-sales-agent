import { X } from 'lucide-react'
import { useEffect } from 'react'

export function Modal({ open, onClose, title, children, footer, wide = false }) {
  useEffect(() => {
    if (!open) return
    const handler = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div
        className={
          'relative w-full bg-fitsiz-surface-1 border border-fitsiz-border rounded-card-lg ' +
          (wide ? 'max-w-3xl' : 'max-w-lg')
        }
      >
        <div className="flex items-center justify-between border-b border-fitsiz-border px-6 py-4">
          <h2 className="font-body text-sm font-bold uppercase tracking-cta text-fitsiz-white">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-fitsiz-muted hover:text-fitsiz-white transition-colors"
            aria-label="Закрыть"
          >
            <X size={18} />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-auto px-6 py-5">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-2 border-t border-fitsiz-border px-6 py-4">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
