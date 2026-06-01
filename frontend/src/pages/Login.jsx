import { useState } from 'react'
import { LogIn } from 'lucide-react'
import { Button } from '../components/Button.jsx'
import { Input } from '../components/Input.jsx'
import { api } from '../lib/api.js'

export default function Login({ onLoggedIn }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e?.preventDefault()
    setErr(null)
    if (!username || !password) return setErr('Введите логин и пароль')
    setBusy(true)
    try {
      const user = await api.authLogin(username, password)
      onLoggedIn?.(user)
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
    }
  }

  const label = 'mb-1.5 block text-[12px] uppercase tracking-badge text-fitsiz-muted'

  return (
    <div className="flex min-h-full items-center justify-center bg-fitsiz-black p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-card-lg border border-fitsiz-border bg-fitsiz-surface-1 p-8"
      >
        <img
          src="/brand/fitsiz-logo-white.png"
          alt="FITSIZ"
          className="mx-auto h-9 w-auto"
        />
        <div className="mt-2 mb-7 text-center text-[11px] font-bold uppercase tracking-badge text-fitsiz-muted">
          Sales Agent — вход
        </div>

        <div className="space-y-4">
          <div>
            <label className={label}>Логин</label>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
          </div>
          <div>
            <label className={label}>Пароль</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {err && (
            <div className="rounded-chip border border-red-500/30 bg-red-900/20 p-3 text-[13px] text-red-300">
              {err}
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={busy}
          >
            <LogIn size={15} /> {busy ? 'Вход…' : 'Войти'}
          </Button>
        </div>
      </form>
    </div>
  )
}
