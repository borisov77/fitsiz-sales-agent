import { useCallback, useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Sparkles,
  Send,
  Check,
  Pencil,
  Trash2,
  ArrowLeft,
  RefreshCcw,
  UserRound,
  Clock,
  Brain,
  ArrowDownLeft,
  ArrowUpRight,
} from 'lucide-react'
import { api } from '../lib/api.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Textarea } from '../components/Input.jsx'
import { Badge } from '../components/Badge.jsx'

function MessageBubble({ m, onEdit, onApprove, onSend, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(m.subject || '')
  const [body, setBody] = useState(m.body_text || '')
  const [busy, setBusy] = useState(null)

  const isOut = m.direction === 'outgoing'
  const isDraft = m.status === 'draft'
  const isQueued = m.status === 'queued'

  const save = async () => {
    setBusy('save')
    try {
      await onEdit(m.id, { subject, body_text: body })
      setEditing(false)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div
      className={
        'rounded-card border p-5 ' +
        (isOut
          ? 'border-fitsiz-border bg-fitsiz-surface-1'
          : 'border-fitsiz-lime/30 bg-fitsiz-lime/5')
      }
    >
      <div className="mb-3 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-badge text-fitsiz-muted">
        {isOut ? (
          <>
            <ArrowUpRight size={12} className="text-fitsiz-green" />
            <span className="font-bold text-fitsiz-white">FITSIZ → клиент</span>
          </>
        ) : (
          <>
            <ArrowDownLeft size={12} className="text-fitsiz-lime" />
            <span className="font-bold text-fitsiz-white">Клиент → FITSIZ</span>
          </>
        )}
        <Badge variant={m.status}>{m.status}</Badge>
        <Clock size={11} />
        <span className="normal-case tracking-normal">
          {new Date(m.sent_at || m.created_at).toLocaleString('ru-RU')}
        </span>
        {m.ai_prompt_used && (
          <span className="ml-auto flex items-center gap-1 normal-case tracking-normal">
            <Brain size={11} className="text-fitsiz-green" />
            <span className="font-mono text-[10px] text-fitsiz-muted">
              {m.ai_prompt_used}
            </span>
          </span>
        )}
      </div>
      {editing ? (
        <div className="space-y-3">
          <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
          <Textarea
            rows={10}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing(false)}>
              Отмена
            </Button>
            <Button size="sm" onClick={save} disabled={busy === 'save'}>
              {busy === 'save' ? 'Сохраняю…' : 'Сохранить'}
            </Button>
          </div>
        </div>
      ) : (
        <>
          {m.subject && (
            <div className="mb-2 font-body text-sm font-bold text-fitsiz-white">
              {m.subject}
            </div>
          )}
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-fitsiz-muted-light">
            {m.body_text}
          </div>
          {m.attachments?.length ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {m.attachments.map((a) => (
                <span
                  key={a}
                  className="rounded-pill bg-fitsiz-surface-2 px-3 py-1 font-mono text-[11px] text-fitsiz-muted-light"
                >
                  📎 {a}
                </span>
              ))}
            </div>
          ) : null}
        </>
      )}

      {isOut && (isDraft || isQueued) && !editing && (
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          {isDraft && (
            <Button variant="outline" size="xs" onClick={() => setEditing(true)}>
              <Pencil size={11} /> Править
            </Button>
          )}
          {isDraft && (
            <Button variant="outline" size="xs" onClick={() => onApprove(m.id)}>
              <Check size={11} /> В очередь
            </Button>
          )}
          <Button variant="primary" size="xs" onClick={() => onSend(m.id)}>
            <Send size={11} /> Отправить
          </Button>
          <Button
            variant="outline"
            size="xs"
            onClick={() => {
              if (confirm('Удалить черновик?')) onDelete(m.id)
            }}
            className="!ring-red-500/40 hover:!bg-red-900/20 text-red-400"
          >
            <Trash2 size={11} />
          </Button>
        </div>
      )}
    </div>
  )
}

export default function ConversationDetail() {
  const { leadId } = useParams()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(null)
  const [qualifier, setQualifier] = useState(null)

  const load = useCallback(async () => {
    setErr(null)
    try {
      const d = await api.conversationGet(leadId)
      setData(d)
    } catch (e) {
      setErr(e.message)
    }
  }, [leadId])

  useEffect(() => {
    load()
  }, [load])

  const runBusy = async (key, fn) => {
    setBusy(key)
    try {
      await fn()
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  const draftCold = () =>
    runBusy('cold', async () => {
      await api.draftCold(leadId)
      await load()
    })
  const draftReply = () =>
    runBusy('reply', async () => {
      await api.draftReply(leadId)
      await load()
    })
  const draftFollowUp = (stage) =>
    runBusy(`fu:${stage}`, async () => {
      await api.draftFollowUp(leadId, stage)
      await load()
    })
  const qualify = () =>
    runBusy('qualify', async () => {
      setQualifier(null)
      const r = await api.qualify(leadId)
      setQualifier(r)
    })
  const transfer = () =>
    runBusy('transfer', async () => {
      if (!confirm('Передать лида менеджеру?')) return
      await api.conversationTransfer(leadId)
      await load()
    })

  const onEdit = async (id, payload) => {
    await api.messageEdit(id, payload)
    await load()
  }
  const onApprove = async (id) => {
    await api.messageApprove(id)
    await load()
  }
  const onSend = async (id) => {
    if (!confirm('Отправить письмо клиенту прямо сейчас?')) return
    try {
      await api.messageSend(id)
      await load()
    } catch (e) {
      alert(e.message)
    }
  }
  const onDelete = async (id) => {
    await api.messageDelete(id)
    await load()
  }

  if (!data && !err)
    return <div className="p-8 text-sm text-fitsiz-muted">загрузка…</div>
  if (err)
    return (
      <div className="p-8 text-sm text-red-400">Ошибка: {err}</div>
    )

  const hasIncoming = data.messages.some((m) => m.direction === 'incoming')

  return (
    <div className="p-8">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link
          to="/conversations"
          className="text-fitsiz-muted hover:text-fitsiz-white transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <h1 className="mr-auto font-heading text-2xl">{data.lead_company}</h1>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCcw size={12} />
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={transfer}
          disabled={busy === 'transfer'}
        >
          <UserRound size={12} /> Менеджеру
        </Button>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Badge variant={data.lead_status}>{data.lead_status}</Badge>
        <span className="text-sm text-fitsiz-muted">{data.lead_email}</span>
      </div>

      {/* AI-тулбар */}
      <div className="mb-5 flex flex-wrap gap-2">
        <Button variant="primary" size="sm" onClick={draftCold} disabled={busy === 'cold'}>
          <Sparkles size={12} /> {busy === 'cold' ? 'Создаю…' : 'Cold-письмо'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={draftReply}
          disabled={!hasIncoming || busy === 'reply'}
          title={hasIncoming ? '' : 'Нет входящих от клиента'}
        >
          <Sparkles size={12} /> {busy === 'reply' ? 'Ответ…' : 'Ответить AI'}
        </Button>
        {['follow_up_1', 'follow_up_2', 'follow_up_3'].map((s) => (
          <Button
            key={s}
            variant="outline"
            size="sm"
            onClick={() => draftFollowUp(s)}
            disabled={busy === `fu:${s}`}
          >
            <Sparkles size={12} />{' '}
            {busy === `fu:${s}` ? '…' : s.replace('_', ' ')}
          </Button>
        ))}
        <Button variant="outline" size="sm" onClick={qualify} disabled={busy === 'qualify'}>
          <Brain size={12} /> {busy === 'qualify' ? 'Оценка…' : 'Квалифицировать'}
        </Button>
      </div>

      {qualifier && (
        <Card variant="accent" className="mb-6">
          <CardBody>
            <div className="font-body text-[11px] font-bold uppercase tracking-badge text-fitsiz-black/70">
              Оценка AI
            </div>
            <div className="mt-2 flex flex-wrap gap-6">
              <div>
                <div className="font-heading text-3xl leading-none">
                  {qualifier.interest_score}
                  <span className="font-body text-lg text-fitsiz-black/60">
                    /10
                  </span>
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-badge text-fitsiz-black/70">
                  Интерес
                </div>
              </div>
              <div>
                <div className="font-heading text-3xl leading-none">
                  {qualifier.buying_readiness}
                  <span className="font-body text-lg text-fitsiz-black/60">
                    /10
                  </span>
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-badge text-fitsiz-black/70">
                  Готовность
                </div>
              </div>
              <div>
                <div className="font-heading text-2xl leading-none">
                  {qualifier.estimated_volume}
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-badge text-fitsiz-black/70">
                  Объём
                </div>
              </div>
            </div>
            <div className="mt-3 text-sm">
              <span className="font-bold">Следующий шаг:</span>{' '}
              {qualifier.next_action}
            </div>
            <div className="mt-1 text-xs text-fitsiz-black/70">
              {qualifier.reasoning}
            </div>
            {qualifier.transfer_to_manager && (
              <div className="mt-3 rounded-chip bg-fitsiz-black/20 px-3 py-2 text-sm font-bold">
                ⚠ Рекомендация AI: передать лида менеджеру.
              </div>
            )}
          </CardBody>
        </Card>
      )}

      <div className="space-y-3">
        {data.messages.length === 0 ? (
          <Card>
            <CardBody className="text-sm text-fitsiz-muted">
              Сообщений пока нет. Сгенерируй cold-письмо кнопкой выше.
            </CardBody>
          </Card>
        ) : (
          data.messages.map((m) => (
            <MessageBubble
              key={m.id}
              m={m}
              onEdit={onEdit}
              onApprove={onApprove}
              onSend={onSend}
              onDelete={onDelete}
            />
          ))
        )}
      </div>
    </div>
  )
}
