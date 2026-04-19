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
import { Card, CardBody } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Textarea } from '../components/Input.jsx'
import { Badge } from '../components/Badge.jsx'
import { FOLLOW_UP_STAGE_RU, volumeLabel } from '../lib/labels.js'

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
        'rounded-card-lg border p-7 ' +
        (isOut
          ? 'border-fitsiz-border bg-fitsiz-surface-1'
          : 'border-fitsiz-lime/30 bg-fitsiz-lime/5')
      }
    >
      <div className="mb-4 flex flex-wrap items-center gap-3 text-[11px] uppercase tracking-badge text-fitsiz-muted">
        {isOut ? (
          <>
            <ArrowUpRight size={14} className="text-fitsiz-green" />
            <span className="font-bold text-fitsiz-white">FITSIZ → клиент</span>
          </>
        ) : (
          <>
            <ArrowDownLeft size={14} className="text-fitsiz-lime" />
            <span className="font-bold text-fitsiz-white">Клиент → FITSIZ</span>
          </>
        )}
        <Badge variant={m.status} />
        <Clock size={12} />
        <span className="normal-case tracking-normal">
          {new Date(m.sent_at || m.created_at).toLocaleString('ru-RU')}
        </span>
        {m.ai_prompt_used && (
          <span className="ml-auto flex items-center gap-1 normal-case tracking-normal">
            <Brain size={12} className="text-fitsiz-green" />
            <span className="font-mono text-[11px] text-fitsiz-muted">
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
            <div className="mb-3 font-body text-[16px] font-bold text-fitsiz-white">
              {m.subject}
            </div>
          )}
          <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-fitsiz-muted-light">
            {m.body_text}
          </div>
          {m.attachments?.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {m.attachments.map((a) => (
                <span
                  key={a}
                  className="rounded-pill bg-fitsiz-surface-2 px-3 py-1.5 font-mono text-[12px] text-fitsiz-muted-light"
                >
                  📎 {a}
                </span>
              ))}
            </div>
          ) : null}
        </>
      )}

      {isOut && (isDraft || isQueued) && !editing && (
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          {isDraft && (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              <Pencil size={13} /> Править
            </Button>
          )}
          {isDraft && (
            <Button variant="outline" size="sm" onClick={() => onApprove(m.id)}>
              <Check size={13} /> В очередь
            </Button>
          )}
          <Button variant="primary" size="sm" onClick={() => onSend(m.id)}>
            <Send size={13} /> Отправить
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (confirm('Удалить черновик?')) onDelete(m.id)
            }}
            className="!ring-red-500/40 hover:!bg-red-900/20 text-red-400"
          >
            <Trash2 size={13} />
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
    return (
      <div className="p-10 text-[15px] text-fitsiz-muted">загрузка…</div>
    )
  if (err)
    return <div className="p-10 text-[15px] text-red-400">Ошибка: {err}</div>

  const hasIncoming = data.messages.some((m) => m.direction === 'incoming')

  return (
    <div className="p-10">
      {/* Шапка: breadcrumb, название компании, действия */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link
            to="/conversations"
            className="mb-3 inline-flex items-center gap-2 text-[12px] uppercase tracking-badge text-fitsiz-muted hover:text-fitsiz-white transition-colors"
          >
            <ArrowLeft size={14} /> К перепискам
          </Link>
          <h1 className="page-title">{data.lead_company}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Badge variant={data.lead_status}>{data.lead_status}</Badge>
            <span className="text-[14px] text-fitsiz-muted">
              {data.lead_email}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="md" onClick={load}>
            <RefreshCcw size={14} /> Обновить
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={transfer}
            disabled={busy === 'transfer'}
          >
            <UserRound size={14} /> Менеджеру
          </Button>
        </div>
      </div>

      {/* AI-тулбар */}
      <div className="mb-6 flex flex-wrap gap-2">
        <Button variant="primary" size="sm" onClick={draftCold} disabled={busy === 'cold'}>
          <Sparkles size={13} /> {busy === 'cold' ? 'Создаю…' : 'Cold-письмо'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={draftReply}
          disabled={!hasIncoming || busy === 'reply'}
          title={hasIncoming ? '' : 'Нет входящих от клиента'}
        >
          <Sparkles size={13} /> {busy === 'reply' ? 'Ответ…' : 'Ответить AI'}
        </Button>
        {['follow_up_1', 'follow_up_2', 'follow_up_3'].map((s) => (
          <Button
            key={s}
            variant="outline"
            size="sm"
            onClick={() => draftFollowUp(s)}
            disabled={busy === `fu:${s}`}
          >
            <Sparkles size={13} />{' '}
            {busy === `fu:${s}` ? '…' : FOLLOW_UP_STAGE_RU[s]}
          </Button>
        ))}
        <Button variant="outline" size="sm" onClick={qualify} disabled={busy === 'qualify'}>
          <Brain size={13} /> {busy === 'qualify' ? 'Оценка…' : 'Квалифицировать'}
        </Button>
      </div>

      {qualifier && (
        <Card variant="accent" className="mb-6">
          <CardBody>
            <div className="font-body text-[12px] font-bold uppercase tracking-badge text-fitsiz-black/70">
              Оценка AI
            </div>
            <div className="mt-4 flex flex-wrap gap-8">
              <div>
                <div className="font-heading text-[48px] leading-none">
                  {qualifier.interest_score}
                  <span className="font-body text-[22px] text-fitsiz-black/60">
                    /10
                  </span>
                </div>
                <div className="mt-2 text-[11px] uppercase tracking-badge text-fitsiz-black/70">
                  Интерес
                </div>
              </div>
              <div>
                <div className="font-heading text-[48px] leading-none">
                  {qualifier.buying_readiness}
                  <span className="font-body text-[22px] text-fitsiz-black/60">
                    /10
                  </span>
                </div>
                <div className="mt-2 text-[11px] uppercase tracking-badge text-fitsiz-black/70">
                  Готовность
                </div>
              </div>
              <div>
                <div className="font-heading text-[32px] leading-none">
                  {volumeLabel(qualifier.estimated_volume)}
                </div>
                <div className="mt-2 text-[11px] uppercase tracking-badge text-fitsiz-black/70">
                  Объём
                </div>
              </div>
            </div>
            <div className="mt-5 text-[15px]">
              <span className="font-bold">Следующий шаг:</span>{' '}
              {qualifier.next_action}
            </div>
            <div className="mt-2 text-[13px] text-fitsiz-black/70">
              {qualifier.reasoning}
            </div>
            {qualifier.transfer_to_manager && (
              <div className="mt-4 rounded-chip bg-fitsiz-black/20 px-4 py-3 text-[14px] font-bold">
                ⚠ Рекомендация AI: передать лида менеджеру.
              </div>
            )}
          </CardBody>
        </Card>
      )}

      <div className="space-y-4">
        {data.messages.length === 0 ? (
          <Card>
            <CardBody className="text-[15px] text-fitsiz-muted">
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
