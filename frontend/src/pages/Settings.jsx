import { useState } from 'react'
import { FileKey2, Send, UserCheck } from 'lucide-react'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Textarea } from '../components/Input.jsx'
import { api } from '../lib/api.js'

export default function SettingsPage() {
  const [to, setTo] = useState('')
  const [subject, setSubject] = useState('Тест FITSIZ Sales Agent')
  const [body, setBody] = useState(
    'Тестовое письмо. Если вы это читаете — SMTP через Mail.ru настроен корректно.',
  )
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  const [mgrBusy, setMgrBusy] = useState(false)
  const [mgrStatus, setMgrStatus] = useState(null)

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

  const sendManagerTest = async () => {
    setMgrBusy(true)
    setMgrStatus(null)
    try {
      const res = await fetch('/api/email/test-manager-email', {
        method: 'POST',
      })
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
    <div className="p-8 space-y-5">
      <div>
        <div className="font-body text-[11px] font-bold uppercase tracking-badge text-fitsiz-muted">
          Конфигурация
        </div>
        <h1 className="mt-1 font-heading text-3xl">Настройки</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileKey2 size={14} className="text-fitsiz-green" />
            Источник истины
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-3 text-sm text-fitsiz-muted-light">
          <p>
            Все ключевые параметры (SMTP/IMAP, Anthropic API-ключ, имя агента,
            лимиты, режим{' '}
            <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-xs text-fitsiz-lime">
              AUTO_SEND
            </code>
            ) берутся из файла{' '}
            <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-xs text-fitsiz-lime">
              .env
            </code>{' '}
            в корне проекта. Редактирование через UI не реализовано — это
            осознанный выбор: секреты лежат в файле, не в БД.
          </p>
          <p>
            Чтобы поменять настройки — отредактируй <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-xs text-fitsiz-lime">.env</code> и перезапусти backend.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send size={14} className="text-fitsiz-green" />
            Тестовая отправка SMTP
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <Input
            type="email"
            placeholder="куда отправить, например you@mail.ru"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
          <Input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Тема"
          />
          <Textarea
            rows={4}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className="flex items-center gap-3">
            <Button variant="primary" onClick={send} disabled={busy}>
              {busy ? 'Отправка…' : 'Отправить тест'}
            </Button>
            {status && (
              <span
                className={
                  'text-xs ' +
                  (status.ok ? 'text-fitsiz-green' : 'text-red-400')
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
          <CardTitle className="flex items-center gap-2">
            <UserCheck size={14} className="text-fitsiz-green" />
            Тест уведомления менеджеру
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-fitsiz-muted-light">
            Отправляет тестовый warm-alert на адрес{' '}
            <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-xs text-fitsiz-lime">
              MANAGER_EMAIL
            </code>{' '}
            из <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-xs text-fitsiz-lime">.env</code> — с фиктивным лидом. Проверяет, что менеджер получает уведомления, когда лид становится тёплым.
          </p>
          <div className="flex items-center gap-3">
            <Button variant="primary" onClick={sendManagerTest} disabled={mgrBusy}>
              {mgrBusy ? 'Отправка…' : 'Отправить тест менеджеру'}
            </Button>
            {mgrStatus && (
              <span
                className={
                  'text-xs ' +
                  (mgrStatus.ok ? 'text-fitsiz-green' : 'text-red-400')
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
