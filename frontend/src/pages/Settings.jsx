import { useState } from 'react'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input } from '../components/Input.jsx'
import { api } from '../lib/api.js'

export default function SettingsPage() {
  const [to, setTo] = useState('')
  const [subject, setSubject] = useState('Тест FITSIZ Sales Agent')
  const [body, setBody] = useState(
    'Тестовое письмо. Если вы это читаете — SMTP через Mail.ru настроен корректно.',
  )
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  const send = async () => {
    if (!to) {
      setStatus({ ok: false, msg: 'Укажите адрес получателя' })
      return
    }
    setBusy(true)
    setStatus(null)
    try {
      const res = await api.emailSendTest({ to, subject, body_text: body })
      setStatus({ ok: true, msg: `Ушло. Message-ID: ${res.message_id}` })
    } catch (e) {
      setStatus({ ok: false, msg: e.message })
    } finally {
      setBusy(false)
    }
  }

  const [mgrBusy, setMgrBusy] = useState(false)
  const [mgrStatus, setMgrStatus] = useState(null)

  const sendManagerTest = async () => {
    setMgrBusy(true)
    setMgrStatus(null)
    try {
      const res = await fetch('/api/email/test-manager-email', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || res.statusText)
      setMgrStatus({ ok: true, msg: `Ушло. Message-ID: ${data.message_id}` })
    } catch (e) {
      setMgrStatus({ ok: false, msg: e.message })
    } finally {
      setMgrBusy(false)
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-lg font-semibold">Настройки</h1>

      <Card>
        <CardHeader>
          <CardTitle>Источник истины</CardTitle>
        </CardHeader>
        <CardBody className="space-y-2 text-sm">
          <p className="text-muted-foreground">
            Все ключевые параметры (SMTP/IMAP, Anthropic API-ключ, имя агента,
            лимиты, режим <code>AUTO_SEND</code>) берутся из файла{' '}
            <code>.env</code> в корне проекта. Редактирование через UI
            пока не реализовано — это осознанный выбор: секреты лежат не в БД.
          </p>
          <p className="text-muted-foreground">
            Чтобы поменять агента — отредактируй <code>.env</code> и
            перезапусти backend.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Тестовая отправка через SMTP</CardTitle>
        </CardHeader>
        <CardBody className="space-y-2">
          <Input
            type="email"
            placeholder="куда отправить, например you@mail.ru"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
          <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
          <textarea
            rows={4}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          />
          <div className="flex items-center gap-2">
            <Button onClick={send} disabled={busy}>
              {busy ? 'Отправка…' : 'Отправить тест'}
            </Button>
            {status && (
              <span
                className={
                  'text-sm ' + (status.ok ? 'text-emerald-700' : 'text-red-700')
                }
              >
                {status.msg}
              </span>
            )}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Тест уведомления менеджеру</CardTitle>
        </CardHeader>
        <CardBody className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Отправляет тестовый warm-alert на адрес <code>MANAGER_EMAIL</code> из
            <code>.env</code> — с фиктивным лидом. Проверяет, что менеджер
            получает уведомления когда лид становится тёплым.
          </p>
          <div className="flex items-center gap-2">
            <Button onClick={sendManagerTest} disabled={mgrBusy}>
              {mgrBusy ? 'Отправка…' : 'Отправить тест менеджеру'}
            </Button>
            {mgrStatus && (
              <span
                className={
                  'text-sm ' +
                  (mgrStatus.ok ? 'text-emerald-700' : 'text-red-700')
                }
              >
                {mgrStatus.msg}
              </span>
            )}
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
