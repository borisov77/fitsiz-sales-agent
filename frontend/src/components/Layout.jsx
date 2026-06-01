import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  MessagesSquare,
  FileText,
  Settings,
  LogOut,
} from 'lucide-react'
import { cn } from '../lib/cn.js'

const links = [
  { to: '/', label: 'Обзор', icon: LayoutDashboard },
  { to: '/leads', label: 'Лиды', icon: Users },
  { to: '/conversations', label: 'Переписки', icon: MessagesSquare },
  { to: '/documents', label: 'Документы', icon: FileText },
  { to: '/settings', label: 'Настройки', icon: Settings },
]

export default function Layout({ user, onLogout }) {
  return (
    <div className="flex h-full bg-fitsiz-black">
      <aside className="flex w-72 shrink-0 flex-col border-r border-fitsiz-border bg-fitsiz-black">
        {/* Шапка с логотипом */}
        <div className="px-7 py-7">
          <img
            src="/brand/fitsiz-logo-white.png"
            alt="FITSIZ"
            className="h-9 w-auto"
          />
          <div className="mt-3 font-body text-[11px] font-bold uppercase tracking-badge text-fitsiz-muted">
            Sales Agent
          </div>
        </div>

        {/* Навигация */}
        <nav className="flex-1 space-y-1 px-4 py-2">
          {links.map((l) => {
            const Icon = l.icon
            return (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 rounded-pill px-5 py-3 font-body text-[15px] transition-colors',
                    isActive
                      ? 'bg-fitsiz-surface-1 text-fitsiz-white font-semibold'
                      : 'text-fitsiz-muted hover:text-fitsiz-white hover:bg-fitsiz-surface-1/60',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-pill bg-fitsiz-green"
                      />
                    )}
                    <Icon
                      size={18}
                      className={cn(
                        isActive
                          ? 'text-fitsiz-green'
                          : 'text-fitsiz-muted group-hover:text-fitsiz-white',
                      )}
                    />
                    <span>{l.label}</span>
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Футер сайдбара: пользователь + выход */}
        <div className="border-t border-fitsiz-border px-4 py-4">
          <button
            onClick={onLogout}
            className="group flex w-full items-center gap-3 rounded-pill px-5 py-3 font-body text-[15px] text-fitsiz-muted transition-colors hover:bg-fitsiz-surface-1/60 hover:text-fitsiz-white"
          >
            <LogOut size={18} className="text-fitsiz-muted group-hover:text-fitsiz-white" />
            <span>Выйти</span>
            {user?.username && (
              <span className="ml-auto truncate text-[12px] text-fitsiz-muted">
                {user.username}
              </span>
            )}
          </button>
          <div className="px-5 pt-3 text-[11px] uppercase tracking-badge text-fitsiz-muted">
            v0.2 · dev
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
