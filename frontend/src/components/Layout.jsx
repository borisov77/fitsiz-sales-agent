import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, MessagesSquare, Settings } from 'lucide-react'
import { cn } from '../lib/cn.js'

const links = [
  { to: '/', label: 'Обзор', icon: LayoutDashboard },
  { to: '/leads', label: 'Лиды', icon: Users },
  { to: '/conversations', label: 'Переписки', icon: MessagesSquare },
  { to: '/settings', label: 'Настройки', icon: Settings },
]

export default function Layout() {
  return (
    <div className="flex h-full bg-fitsiz-black">
      <aside className="flex w-64 shrink-0 flex-col border-r border-fitsiz-border bg-fitsiz-black">
        {/* Шапка с логотипом */}
        <div className="px-6 py-6">
          <img
            src="/brand/fitsiz-logo-white.png"
            alt="FITSIZ"
            className="h-7 w-auto"
          />
          <div className="mt-2 font-body text-[10px] font-bold uppercase tracking-badge text-fitsiz-muted">
            Sales Agent
          </div>
        </div>

        {/* Навигация */}
        <nav className="flex-1 space-y-1 px-3 py-2">
          {links.map((l) => {
            const Icon = l.icon
            return (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 rounded-pill px-4 py-2.5 font-body text-sm transition-colors',
                    isActive
                      ? 'bg-fitsiz-surface-1 text-fitsiz-white'
                      : 'text-fitsiz-muted hover:text-fitsiz-white hover:bg-fitsiz-surface-1/60',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-pill bg-fitsiz-green"
                      />
                    )}
                    <Icon
                      size={16}
                      className={cn(
                        isActive ? 'text-fitsiz-green' : 'text-fitsiz-muted group-hover:text-fitsiz-white',
                      )}
                    />
                    <span className={cn(isActive && 'font-semibold')}>
                      {l.label}
                    </span>
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Футер сайдбара */}
        <div className="border-t border-fitsiz-border px-6 py-4 text-[10px] uppercase tracking-badge text-fitsiz-muted">
          v0.2 · dev
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
