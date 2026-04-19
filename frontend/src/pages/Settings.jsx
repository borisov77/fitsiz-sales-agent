import { useState } from 'react'
import { FileKey2, Send, UserCheck } from 'lucide-react'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Textarea } from '../components/Input.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
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
      const data = await api.emailTestManager()
      setMgrStatus({ ok: true, msg: `Ушло. Message-ID: ${data.message_id}` })
    } catch (e) {
      setMgrStatus({ ok: false, msg: e.message })
    } finally {
      setMgrBusy(false)
    }
  }

  const code = 'rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-[12px] text-fitsiz-lime'

  return (
    <div className="p-10 space-y-6">
      <PageHeader
        chip="конфигурация"
        title="Настройки"
        accent="ройки"
        description="Параметры агента в .env. Здесь — только тестовая отправка, чтобы проверить, что всё работает."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileKey2 size={16} className="text-fitsiz-green" />
            Источник истины
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-4 text-[15px] text-fitsiz-muted-light leading-relaxed">
          <p>
            Все ключевые параметры (SMTP/IMAP, Anthropic API-ключ, имя агента,
            лимиты, режим <code className={code}>AUTO_SEND</code>) берутся из
            файла <code className={code}>.env</code> в корне проекта. Редактирование через UI не реализовано — это осознанный выбор: секреты лежат в файле, не в БД.
          </p>
          <p>
            Чтобы поменять настройки — отредактируй{' '}
            <code className={code}>.env</code> и перезапусти backend.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send size={16} className="text-fitsiz-green" />
            Тестовая отправка SMTP
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
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
          <div className="flex items-center gap-4 flex-wrap">
            <Button variant="primary" size="md" onClick={send} disabled={busy}>
              {busy ? 'Отправка…' : 'Отправить тест'}
            </Button>
            {status && (
              <span
                className={
                  'text-[14px] ' +
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
            <UserCheck size={16} className="text-fitsiz-green" />
            Тест уведомления менеджеру
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <p className="text-[15px] text-fitsiz-muted-light leading-relaxed">
            Отправляет тестовый warm-alert на адрес{' '}
            <code className={code}>MANAGER_EMAIL</code> из{' '}
            <code className={code}>.env</code> — с фиктивным лидом.
            Проверяет, что менеджер получает уведомления, когда лид
            становится тёплым.
          </p>
          <div className="flex items-center gap-4 flex-wrap">
            <Button variant="primary" size="md" onClick={sendManagerTest} disabled={mgrBusy}>
              {mgrBusy ? 'Отправка…' : 'Отправить тест менеджеру'}
            </Button>
            {mgrStatus && (
              <span
                className={
                  'text-[14px] ' +
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
