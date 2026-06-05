import { useEffect, useState } from 'react'
import { FileKey2, Send, UserCheck, Users, Trash2, Plus, ArrowRightLeft, Rocket, Mail, Clock, KeyRound } from 'lucide-react'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Textarea } from '../components/Input.jsx'
import { Switch } from '../components/Switch.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
import { api } from '../lib/api.js'

function isEmail(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())
}

function ManagerTransferCard() {
  const [emails, setEmails] = useState([])
  const [maxEmails, setMaxEmails] = useState(5)
  const [auto, setAuto] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [err, setErr] = useState(null)
  const [savedMsg, setSavedMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try {
      const s = await api.settingsGet()
      setEmails(s.manager_emails || [])
      setMaxEmails(s.max_manager_emails || 5)
      setAuto(!!s.auto_transfer_to_manager)
    } catch (e) {
      setErr(e.message)
    }
  }
  useEffect(() => {
    load()
  }, [])

  const persist = async (list) => {
    setErr(null)
    setSavedMsg(null)
    setBusy(true)
    try {
      const s = await api.settingsSetManagerEmails(list)
      setEmails(s.manager_emails || [])
      setSavedMsg('Сохранено')
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const addEmail = async () => {
    const v = newEmail.trim()
    if (!isEmail(v)) return setErr('Укажите корректный email')
    if (emails.some((e) => e.toLowerCase() === v.toLowerCase()))
      return setErr('Такой email уже добавлен')
    if (emails.length >= maxEmails) return setErr(`Не более ${maxEmails} адресов`)
    setNewEmail('')
    await persist([...emails, v])
  }

  const removeEmail = async (idx) => {
    await persist(emails.filter((_, i) => i !== idx))
  }

  const toggleAuto = async (next) => {
    setErr(null)
    setAuto(next)
    try {
      await api.settingsSetAutoTransfer(next)
    } catch (e) {
      setErr(e.message)
      setAuto(!next)
    }
  }

  const atLimit = emails.length >= maxEmails

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ArrowRightLeft size={16} className="text-fitsiz-green" />
          Передача менеджеру
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-6">
        {/* Авто-передача */}
        <div className="flex items-start justify-between gap-4">
          <div className="max-w-md">
            <div className="text-[15px] font-semibold text-fitsiz-white">
              Авто-передача warm-лидов
            </div>
            <p className="mt-1 text-[14px] text-fitsiz-muted-light leading-relaxed">
              Если включено — как только лид становится тёплым, уведомление
              автоматически уходит на все почты менеджеров. Если выключено —
              лид помечается, а письмо отправляется вручную кнопкой «Отправить
              менеджеру».
            </p>
          </div>
          <Switch checked={auto} onChange={toggleAuto} label="Авто-передача" />
        </div>

        <div className="h-px bg-fitsiz-border" />

        {/* Почты менеджеров */}
        <div>
          <div className="mb-3 flex items-center gap-2 text-[15px] font-semibold text-fitsiz-white">
            <Users size={15} className="text-fitsiz-green" />
            Почты менеджеров
            <span className="text-[12px] font-normal text-fitsiz-muted">
              {emails.length}/{maxEmails}
            </span>
          </div>

          {emails.length === 0 ? (
            <div className="mb-3 rounded-chip border border-amber-500/40 bg-amber-900/20 p-3 text-[13px] text-amber-200">
              Добавьте хотя бы одну почту менеджера — иначе уведомления о тёплых
              лидах отправлять некуда.
            </div>
          ) : (
            <ul className="mb-3 space-y-2">
              {emails.map((e, i) => (
                <li
                  key={e}
                  className="flex items-center justify-between rounded-chip border border-fitsiz-border bg-fitsiz-black/40 px-4 py-2.5"
                >
                  <span className="text-[14px] text-fitsiz-white">{e}</span>
                  <button
                    onClick={() => removeEmail(i)}
                    disabled={busy}
                    className="text-fitsiz-muted hover:text-red-400 transition-colors disabled:opacity-50"
                    aria-label={`Удалить ${e}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex items-center gap-2">
            <Input
              type="email"
              placeholder="manager@fitsiz.ru"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !atLimit && addEmail()}
              disabled={atLimit}
              className="max-w-sm"
            />
            <Button
              variant="primary"
              size="md"
              onClick={addEmail}
              disabled={atLimit || busy}
            >
              <Plus size={14} /> Добавить почту
            </Button>
          </div>
          {atLimit && (
            <div className="mt-2 text-[12px] text-fitsiz-muted">
              Достигнут лимит в {maxEmails} адресов — удалите лишний, чтобы
              добавить другой.
            </div>
          )}
        </div>

        {(err || savedMsg) && (
          <div
            className={
              'text-[14px] ' + (err ? 'text-red-400' : 'text-fitsiz-green')
            }
          >
            {err || savedMsg}
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function ColdTemplateCard() {
  const [tpl, setTpl] = useState({ subject: '', body: '', signature: '' })
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    api
      .coldTemplateGet()
      .then((t) => {
        setTpl(t)
        setLoaded(true)
      })
      .catch((e) => setMsg({ ok: false, text: e.message }))
  }, [])

  const set = (k) => (e) => setTpl((t) => ({ ...t, [k]: e.target.value }))

  const save = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const saved = await api.coldTemplateSave(tpl)
      setTpl(saved)
      setMsg({ ok: true, text: 'Шаблон сохранён' })
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const label = 'mb-1.5 block text-[12px] uppercase tracking-badge text-fitsiz-muted'
  const empty = loaded && (!tpl.subject.trim() || !tpl.body.trim())

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail size={16} className="text-fitsiz-green" />
          Шаблон первого письма
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-[14px] text-fitsiz-muted-light leading-relaxed">
          Первое (холодное) письмо НЕ генерируется AI — берётся отсюда. Доступные
          переменные:{' '}
          <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-[12px] text-fitsiz-lime">
            {'{company_name}'}
          </code>{' '}
          <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-[12px] text-fitsiz-lime">
            {'{contact_name}'}
          </code>{' '}
          — подставятся данными лида (если имя пустое, обращение убирается).
          Прайс и презентация уходят вложением. AI остаётся на ответах,
          follow-up и квалификации.
        </p>

        <div>
          <label className={label}>Тема письма</label>
          <Input value={tpl.subject} onChange={set('subject')} />
        </div>
        <div>
          <label className={label}>Тело письма</label>
          <Textarea rows={9} value={tpl.body} onChange={set('body')} />
        </div>
        <div>
          <label className={label}>Подпись / визитка</label>
          <Textarea rows={4} value={tpl.signature} onChange={set('signature')} />
        </div>

        {empty && (
          <div className="rounded-chip border border-amber-500/40 bg-amber-900/20 p-3 text-[13px] text-amber-200">
            Тема и тело не должны быть пустыми — иначе рассылку не запустить.
          </div>
        )}

        <div className="flex items-center gap-4">
          <Button variant="primary" size="md" onClick={save} disabled={busy}>
            {busy ? 'Сохранение…' : 'Сохранить шаблон'}
          </Button>
          {msg && (
            <span
              className={
                'text-[14px] ' + (msg.ok ? 'text-fitsiz-green' : 'text-red-400')
              }
            >
              {msg.text}
            </span>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

function ColdTimingCard() {
  const [reminder, setReminder] = useState('')
  const [noReply, setNoReply] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    try {
      const s = await api.settingsGet()
      setReminder(String(s.reminder_delay_days))
      setNoReply(String(s.no_reply_days))
      setLoaded(true)
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    }
  }
  useEffect(() => {
    load()
  }, [])

  const save = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const r = parseInt(reminder, 10)
      const n = parseInt(noReply, 10)
      if (!Number.isFinite(r) || !Number.isFinite(n))
        throw new Error('Введите целые числа')
      if (r <= 0 || n <= 0) throw new Error('Сроки должны быть больше 0')
      if (r >= n)
        throw new Error('Срок до напоминания должен быть меньше срока до «без ответа»')
      const s = await api.settingsSetColdTiming(r, n)
      setReminder(String(s.reminder_delay_days))
      setNoReply(String(s.no_reply_days))
      setMsg({ ok: true, text: 'Сроки сохранены' })
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const label = 'mb-1.5 block text-[12px] uppercase tracking-badge text-fitsiz-muted'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock size={16} className="text-fitsiz-green" />
          Сроки холодной зоны
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-[14px] text-fitsiz-muted-light leading-relaxed">
          После отправки холодного письма агент ждёт{' '}
          <b className="text-fitsiz-white">срок до напоминания</b>, затем шлёт одно
          напоминание. Если и после этого тишина в течение{' '}
          <b className="text-fitsiz-white">срока до «без ответа»</b> — лид уходит
          в статус «Осталось без ответа».
        </p>
        <div className="flex flex-wrap gap-5">
          <div>
            <label className={label}>Срок до напоминания (дней)</label>
            <Input
              type="number"
              min={1}
              value={reminder}
              onChange={(e) => setReminder(e.target.value)}
              className="max-w-[160px]"
              disabled={!loaded}
            />
          </div>
          <div>
            <label className={label}>Срок до «без ответа» (дней)</label>
            <Input
              type="number"
              min={1}
              value={noReply}
              onChange={(e) => setNoReply(e.target.value)}
              className="max-w-[160px]"
              disabled={!loaded}
            />
          </div>
        </div>
        <div className="rounded-chip border border-fitsiz-border bg-fitsiz-black/40 p-3 text-[13px] text-fitsiz-muted-light">
          Правило: <b className="text-fitsiz-white">напоминание &lt; без ответа</b>.
          Срок до напоминания должен быть строго меньше срока до «без ответа».
        </div>
        <div className="flex items-center gap-4">
          <Button variant="primary" size="md" onClick={save} disabled={busy || !loaded}>
            {busy ? 'Сохранение…' : 'Сохранить сроки'}
          </Button>
          {msg && (
            <span className={'text-[14px] ' + (msg.ok ? 'text-fitsiz-green' : 'text-red-400')}>
              {msg.text}
            </span>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

function AiTokenCard() {
  const [status, setStatus] = useState(null) // {ai_token_set, ai_token_masked, ai_token_source, ai_token_can_store_in_db}
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    try {
      const s = await api.settingsGet()
      setStatus(s)
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    }
  }
  useEffect(() => {
    load()
  }, [])

  const save = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const s = await api.settingsSetAiToken(token)
      setStatus(s)
      setToken('')
      setMsg({ ok: true, text: 'Токен сохранён (зашифрован)' })
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const clear = async () => {
    if (!confirm('Удалить токен из БД? Будет использоваться ANTHROPIC_API_KEY из .env.'))
      return
    setBusy(true)
    setMsg(null)
    try {
      const s = await api.settingsSetAiToken('')
      setStatus(s)
      setToken('')
      setMsg({ ok: true, text: 'Токен удалён из БД (fallback на .env)' })
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const sourceLabel =
    status?.ai_token_source === 'db'
      ? 'из БД (зашифрован)'
      : status?.ai_token_source === 'env'
        ? 'из .env (ANTHROPIC_API_KEY)'
        : '—'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound size={16} className="text-fitsiz-green" />
          AI-токен (Anthropic)
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        <div className="rounded-chip border border-fitsiz-border bg-fitsiz-black/40 p-4">
          <div className="text-[12px] uppercase tracking-badge text-fitsiz-muted">
            Текущий токен
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            {status?.ai_token_set ? (
              <span className="font-mono text-[15px] text-fitsiz-white">
                {status.ai_token_masked}
              </span>
            ) : (
              <span className="text-[14px] text-amber-300">не задан</span>
            )}
            <span className="text-[12px] text-fitsiz-muted">· источник: {sourceLabel}</span>
          </div>
        </div>

        {status && !status.ai_token_can_store_in_db && (
          <div className="rounded-chip border border-amber-500/40 bg-amber-900/20 p-3 text-[13px] text-amber-200">
            FITSIZ_SECRET_KEY в <code>.env</code> не задан — сохранение токена в БД
            недоступно. Работает только fallback на <code>ANTHROPIC_API_KEY</code>.
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-[12px] uppercase tracking-badge text-fitsiz-muted">
            Новый токен (вставьте, чтобы заменить)
          </label>
          <Input
            type="password"
            placeholder="sk-ant-…"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoComplete="off"
            disabled={!status?.ai_token_can_store_in_db}
          />
          <p className="mt-1.5 text-[12px] text-fitsiz-muted">
            Хранится только в зашифрованном виде. Полное значение нигде не
            показывается и не возвращается обратно.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Button
            variant="primary"
            size="md"
            onClick={save}
            disabled={busy || !token.trim() || !status?.ai_token_can_store_in_db}
          >
            {busy ? 'Сохранение…' : 'Сохранить токен'}
          </Button>
          {status?.ai_token_source === 'db' && (
            <Button variant="outline" size="md" onClick={clear} disabled={busy}>
              <Trash2 size={14} /> Удалить из БД
            </Button>
          )}
          {msg && (
            <span className={'text-[14px] ' + (msg.ok ? 'text-fitsiz-green' : 'text-red-400')}>
              {msg.text}
            </span>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

function SendModeCard() {
  const [auto, setAuto] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api
      .settingsGet()
      .then((s) => setAuto(!!s.auto_send))
      .catch((e) => setErr(e.message))
  }, [])

  const toggle = async (next) => {
    setErr(null)
    setAuto(next)
    try {
      await api.settingsSetAutoSend(next)
    } catch (e) {
      setErr(e.message)
      setAuto(!next)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Rocket size={16} className="text-fitsiz-green" />
          Режим рассылки (AUTO_SEND)
        </CardTitle>
      </CardHeader>
      <CardBody>
        <div className="flex items-start justify-between gap-4">
          <div className="max-w-xl">
            <div className="text-[15px] font-semibold text-fitsiz-white">
              {auto ? 'Авто-режим: письма уходят в очередь сразу' : 'Модерация: письма ждут подтверждения'}
            </div>
            <p className="mt-1 text-[14px] text-fitsiz-muted-light leading-relaxed">
              <b className="text-fitsiz-white">Выключено (модерация)</b> — при
              запуске рассылки письма генерируются как черновики, вы вручную
              отправляете их «В очередь». Для теста.
              <br />
              <b className="text-fitsiz-white">Включено (авто)</b> — письма сразу
              встают в очередь и уходят по расписанию с антиспам-задержками.
              Для боевого режима.
            </p>
          </div>
          <Switch checked={auto} onChange={toggle} label="AUTO_SEND" />
        </div>
        {err && <div className="mt-3 text-[14px] text-red-400">{err}</div>}
      </CardBody>
    </Card>
  )
}

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
        description="Передача менеджеру и почты — здесь, в интерфейсе. Секреты (SMTP, ключи) — в .env."
      />

      <ColdTemplateCard />

      <ColdTimingCard />

      <AiTokenCard />

      <SendModeCard />

      <ManagerTransferCard />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileKey2 size={16} className="text-fitsiz-green" />
            Источник истины
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-4 text-[15px] text-fitsiz-muted-light leading-relaxed">
          <p>
            Секреты и инфраструктура (SMTP/IMAP, Anthropic API-ключ, имя агента,
            лимиты, режим <code className={code}>AUTO_SEND</code>) берутся из{' '}
            <code className={code}>.env</code> в корне проекта.
          </p>
          <p>
            Почты менеджеров и режим авто-передачи хранятся в БД и меняются
            прямо здесь — без перезапуска backend.
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
          <Textarea rows={4} value={body} onChange={(e) => setBody(e.target.value)} />
          <div className="flex items-center gap-4 flex-wrap">
            <Button variant="primary" size="md" onClick={send} disabled={busy}>
              {busy ? 'Отправка…' : 'Отправить тест'}
            </Button>
            {status && (
              <span
                className={
                  'text-[14px] ' + (status.ok ? 'text-fitsiz-green' : 'text-red-400')
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
            Отправляет тестовый warm-alert на{' '}
            <b className="text-fitsiz-white">все почты менеджеров</b> из списка
            выше — с фиктивным лидом. Проверяет, что менеджеры получают
            уведомления.
          </p>
          <div className="flex items-center gap-4 flex-wrap">
            <Button
              variant="primary"
              size="md"
              onClick={sendManagerTest}
              disabled={mgrBusy}
            >
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
