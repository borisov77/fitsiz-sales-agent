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
} from 'lucide-react'
import { api } from '../lib/api.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Textarea } from '../components/Input.jsx'
import { Badge } from '../components/Badge.jsx'

function Message({ m, onEdit, onApprove, onSend, onDelete }) {
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
        'rounded-lg border p-3 ' +
        (isOut
          ? 'border-border bg-white'
          : 'border-cyan-200 bg-cyan-50/40')
      }
    >
      <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium">
          {isOut ? 'FITSIZ → клиент' : 'Клиент → FITSIZ'}
        </span>
        <Badge variant={m.status}>{m.status}</Badge>
        <Clock size={12} />
        <span>
          {new Date(m.sent_at || m.created_at).toLocaleString('ru-RU')}
        </span>
        {m.ai_prompt_used && (
          <span className="ml-auto flex items-center gap-1">
            <Brain size={12} />
            <span className="font-mono">{m.ai_prompt_used}</span>
          </span>
        )}
      </div>
      {editing ? (
        <div className="space-y-2">
          <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
          <Textarea
            rows={8}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing(false)}>
              Отмена
            </Button>
            <Button size="sm" onClick={save} disabled={busy === 'save'}>
              {busy === 'save' ? 'Сохранение…' : 'Сохранить'}
            </Button>
          </div>
        </div>
      ) : (
        <>
          {m.subject && (
            <div className="mb-1 text-sm font-semibold">{m.subject}</div>
          )}
          <div className="whitespace-pre-wrap text-sm">{m.body_text}</div>
          {m.attachments?.length ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {m.attachments.map((a) => (
                <span
                  key={a}
                  className="rounded bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
                >
                  📎 {a}
                </span>
              ))}
            </div>
          ) : null}
        </>
      )}

      {isOut && (isDraft || isQueued) && !editing && (
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          {isDraft && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditing(true)}
            >
              <Pencil size={12} /> Править
            </Button>
          )}
          {isDraft && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onApprove(m.id)}
            >
              <Check size={12} /> Одобрить (в очередь)
            </Button>
          )}
          <Button size="sm" onClick={() => onSend(m.id)}>
            <Send size={12} /> Отправить сейчас
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              if (confirm('Удалить черновик?')) onDelete(m.id)
            }}
            className="text-red-600"
          >
            <Trash2 size={12} />
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

  const draftCold = async () => {
    setBusy('cold')
    try {
      await api.draftCold(leadId)
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  const draftReply = async () => {
    setBusy('reply')
    try {
      await api.draftReply(leadId)
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  const draftFollowUp = async (stage) => {
    setBusy(`fu:${stage}`)
    try {
      await api.draftFollowUp(leadId, stage)
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  const qualify = async () => {
    setBusy('qualify')
    setQualifier(null)
    try {
      const r = await api.qualify(leadId)
      setQualifier(r)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  const transfer = async () => {
    if (!confirm('Передать лида менеджеру?')) return
    setBusy('transfer')
    try {
      await api.conversationTransfer(leadId)
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

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

  if (!data && !err) return <div className="p-6 text-sm text-muted-foreground">загрузка…</div>
  if (err) return <div className="p-6 text-sm text-red-700">Ошибка: {err}</div>

  const hasIncoming = data.messages.some((m) => m.direction === 'incoming')

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center gap-2">
        <Link to="/conversations" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft size={18} />
        </Link>
        <h1 className="mr-auto text-lg font-semibold">{data.lead_company}</h1>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCcw size={14} />
        </Button>
        <Button variant="outline" size="sm" onClick={transfer} disabled={busy === 'transfer'}>
          <UserRound size={14} /> Менеджеру
        </Button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Badge variant={data.lead_status}>{data.lead_status}</Badge>
        <span>{data.lead_email}</span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={draftCold} disabled={busy === 'cold'}>
          <Sparkles size={14} /> {busy === 'cold' ? 'Генерация…' : 'Cold-письмо'}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={draftReply}
          disabled={!hasIncoming || busy === 'reply'}
          title={hasIncoming ? '' : 'Нет входящих от клиента'}
        >
          <Sparkles size={14} /> {busy === 'reply' ? 'Ответ…' : 'Ответить AI'}
        </Button>
        {['follow_up_1', 'follow_up_2', 'follow_up_3'].map((s) => (
          <Button
            key={s}
            size="sm"
            variant="outline"
            onClick={() => draftFollowUp(s)}
            disabled={busy === `fu:${s}`}
          >
            <Sparkles size={14} /> {busy === `fu:${s}` ? '…' : s.replace('_', ' ')}
          </Button>
        ))}
        <Button size="sm" variant="outline" onClick={qualify} disabled={busy === 'qualify'}>
          <Brain size={14} /> {busy === 'qualify' ? 'Оценка…' : 'Квалифицировать'}
        </Button>
      </div>

      {qualifier && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Оценка лида</CardTitle>
          </CardHeader>
          <CardBody className="space-y-1 text-sm">
            <div>
              Интерес: <b>{qualifier.interest_score}/10</b>, готовность к
              покупке: <b>{qualifier.buying_readiness}/10</b>, объём:{' '}
              <b>{qualifier.estimated_volume}</b>
            </div>
            <div>
              Следующий шаг:{' '}
              <span className="text-muted-foreground">{qualifier.next_action}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {qualifier.reasoning}
            </div>
            {qualifier.transfer_to_manager && (
              <div className="mt-2 rounded bg-amber-50 p-2 text-amber-800">
                AI рекомендует передать лида менеджеру.
              </div>
            )}
          </CardBody>
        </Card>
      )}

      <div className="space-y-3">
        {data.messages.length === 0 ? (
          <Card>
            <CardBody className="text-sm text-muted-foreground">
              Сообщений пока нет. Сгенерируй cold-письмо кнопкой выше.
            </CardBody>
          </Card>
        ) : (
          data.messages.map((m) => (
            <Message
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
