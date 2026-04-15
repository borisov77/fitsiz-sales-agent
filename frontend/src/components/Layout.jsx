import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, MessagesSquare, Settings } from 'lucide-react'
import { cn } from '../lib/cn.js'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/leads', label: 'Лиды', icon: Users },
  { to: '/conversations', label: 'Переписки', icon: MessagesSquare },
  { to: '/settings', label: 'Настройки', icon: Settings },
]

export default function Layout() {
  return (
    <div className="flex h-full">
      <aside className="flex w-60 flex-col border-r border-border bg-muted/40">
        <div className="border-b border-border px-5 py-4">
          <div className="text-sm font-semibold">FITSIZ</div>
          <div className="text-xs text-muted-foreground">AI Sales Agent</div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {links.map((l) => {
            const Icon = l.icon
            return (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )
                }
              >
                <Icon size={16} />
                {l.label}
              </NavLink>
            )
          })}
        </nav>
        <div className="border-t border-border p-3 text-[11px] text-muted-foreground">
          v0.1 · dev
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
