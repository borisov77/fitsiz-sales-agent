import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Users,
  Flame,
  ClipboardCheck,
  Activity,
  MessageSquareWarning,
  Pencil,
  RotateCcw,
  FileWarning,
  SendHorizonal,
  Rocket,
} from 'lucide-react'
import { api } from '../lib/api.js'
import { cn } from '../lib/cn.js'
import { StatsCard } from '../components/StatsCard.jsx'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'
import { Button } from '../components/Button.jsx'
import { Input } from '../components/Input.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
import { LEAD_STATUS_RU } from '../lib/labels.js'

const FUNNEL_ORDER = [
  'created',
  'sent',
  'in_dialog',
  'handed_to_manager',
  'won',
  'lost',
  'no_reply',
]

function QuotaCard({ quota, onEdit, onReset }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState('')
  const [busy, setBusy] = useState(false)

  const startEdit = () => {
    setVal(String(quota?.daily_limit ?? ''))
    setEditing(true)
  }

  const save = async () => {
    const n = parseInt(val, 10)
    if (!Number.isFinite(n) || n < 0) {
      alert('Введи целое число ≥ 0')
      return
    }
    setBusy(true)
    try {
      await onEdit(n)
      setEditing(false)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    if (!confirm('Сбросить лимит к значению из .env?')) return
    setBusy(true)
    try {
      await onReset()
      setEditing(false)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Квота отправки сегодня</CardTitle>
      </CardHeader>
      <CardBody>
        {!quota ? (
          <div className="text-[14px] text-fitsiz-muted">загрузка…</div>
        ) : editing ? (
          <div className="space-y-3">
            <div className="text-[13px] text-fitsiz-muted">
              Новый дневной лимит писем
            </div>
            <Input
              type="number"
              min={0}
              max={10000}
              value={val}
              onChange={(e) => setVal(e.target.value)}
              autoFocus
            />
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={save}
                disabled={busy}
              >
                {busy ? 'Сохраняю…' : 'Сохранить'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditing(false)}
              >
                Отмена
              </Button>
              {quota.has_override && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={reset}
                  disabled={busy}
                >
                  <RotateCcw size={12} /> Сброс (.env)
                </Button>
              )}
            </div>
            <div className="text-[12px] text-fitsiz-muted">
              В <code className="text-fitsiz-lime">.env</code>:{' '}
              <b className="text-fitsiz-white">{quota.env_default}</b>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-baseline gap-3">
              <div className="font-heading text-[64px] leading-none text-fitsiz-green">
                {quota.sent_today}
              </div>
              <div className="font-heading text-[26px] text-fitsiz-muted">
                / {quota.daily_limit}
              </div>
            </div>
            <div className="mt-3 text-[12px] uppercase tracking-badge text-fitsiz-muted">
              Осталось:{' '}
              <span className="text-fitsiz-white font-bold">
                {quota.remaining}
              </span>
            </div>
            <div className="mt-5 h-2 w-full overflow-hidden rounded-pill bg-fitsiz-surface-2">
              <div
                className="h-full bg-fitsiz-green transition-all duration-300"
                style={{
                  width: `${
                    quota.daily_limit
                      ? Math.min(
                          100,
                          (quota.sent_today / quota.daily_limit) * 100,
                        )
                      : 0
                  }%`,
                }}
              />
            </div>
            <div className="mt-5 flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={startEdit}
              >
                <Pencil size={12} /> Изменить лимит
              </Button>
              {quota.has_override && (
                <span className="text-[11px] uppercase tracking-badge text-fitsiz-lime">
                  override (.env: {quota.env_default})
                </span>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

const STEP_LABEL = {
  created: 'Создано (всего)',
  sent: 'Отправлено',
  in_dialog: 'Ответили',
  handed_to_manager: 'У менеджера',
  won: 'Договор',
}

function FunnelView({ funnel, counts }) {
  if (!funnel) {
    return <div className="text-[14px] text-fitsiz-muted">загрузка воронки…</div>
  }
  const top = funnel.steps?.[0]?.reached || 0
  const conv = funnel.conversions || {}
  const convItems = [
    { label: 'Ответили / Отправлено', value: conv.reply_rate },
    { label: 'Передано / Ответили', value: conv.qualify_rate },
    { label: 'Договор / Передано', value: conv.deal_rate },
  ]
  const shareItems = [
    { label: 'Осталось без ответа', value: conv.no_reply_share, n: funnel.terminals?.no_reply },
    { label: 'Отказ', value: conv.lost_share, n: funnel.terminals?.lost },
  ]

  return (
    <div className="space-y-6">
      {/* Убывающие ступени воронки */}
      <div className="space-y-2">
        {funnel.steps.map((s) => {
          const pct = top ? Math.round((s.reached / top) * 100) : 0
          return (
            <div key={s.key} className="flex items-center gap-3">
              <div className="w-40 shrink-0 text-[13px] text-fitsiz-muted-light">
                {STEP_LABEL[s.key] || s.key}
              </div>
              <div className="relative h-8 flex-1 overflow-hidden rounded-chip bg-fitsiz-surface-2">
                <div
                  className="h-full rounded-chip bg-fitsiz-green/30 ring-1 ring-fitsiz-green/40 transition-all"
                  style={{ width: `${Math.max(pct, s.reached > 0 ? 6 : 0)}%` }}
                />
                <div className="absolute inset-0 flex items-center gap-2 px-3">
                  <span className="font-heading text-[18px] leading-none text-fitsiz-white">
                    {s.reached}
                  </span>
                  <span className="text-[11px] text-fitsiz-muted">{pct}%</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Ключевые конверсии */}
      <div>
        <div className="mb-2 text-[11px] uppercase tracking-badge text-fitsiz-muted">
          Конверсии
        </div>
        <div className="grid grid-cols-3 gap-3">
          {convItems.map((m) => (
            <div
              key={m.label}
              className="rounded-chip border border-fitsiz-border bg-fitsiz-black/40 px-4 py-3"
            >
              <div className="font-heading text-[26px] leading-none text-fitsiz-green">
                {m.value ?? 0}%
              </div>
              <div className="mt-1.5 text-[11px] text-fitsiz-muted">{m.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Терминалы сбоку */}
      <div>
        <div className="mb-2 text-[11px] uppercase tracking-badge text-fitsiz-muted">
          Потери
        </div>
        <div className="grid grid-cols-2 gap-3">
          {shareItems.map((m) => (
            <div
              key={m.label}
              className="flex items-baseline justify-between rounded-chip border border-fitsiz-border bg-fitsiz-black/40 px-4 py-3"
            >
              <div>
                <div className="font-heading text-[22px] leading-none text-fitsiz-white">
                  {m.n ?? 0}
                </div>
                <div className="mt-1.5 text-[11px] text-fitsiz-muted">{m.label}</div>
              </div>
              <div className="text-[13px] text-fitsiz-muted-light">{m.value ?? 0}%</div>
            </div>
          ))}
        </div>
      </div>

      {/* Сырые счётчики по 7 статусам */}
      <div className="flex flex-wrap gap-2">
        {FUNNEL_ORDER.map((s) => (
          <div
            key={s}
            className="flex items-center gap-2 rounded-chip bg-fitsiz-black/40 border border-fitsiz-border px-3 py-1.5"
          >
            <Badge variant={s}>{LEAD_STATUS_RU[s]}</Badge>
            <span className="font-heading text-[16px] leading-none text-fitsiz-white">
              {(counts[s] ?? funnel.counts?.[s]) || 0}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [leads, setLeads] = useState([])
  const [quota, setQuota] = useState(null)
  const [conv, setConv] = useState([])
  const [docs, setDocs] = useState(null)
  const [campaign, setCampaign] = useState(null)
  const [funnel, setFunnel] = useState(null)
  const [err, setErr] = useState(null)
  const [notifyBusy, setNotifyBusy] = useState(null)

  const loadAll = useCallback(async () => {
    try {
      const [l, q, c, d, cs, fn] = await Promise.all([
        api.leadsList({ limit: 1000 }),
        api.emailQuota(),
        api.conversationsList({ limit: 500 }),
        api.documents(),
        api.campaignStatus(),
        api.campaignFunnel(),
      ])
      setLeads(l || [])
      setQuota(q)
      setConv(c || [])
      setDocs(d)
      setCampaign(cs)
      setFunnel(fn)
    } catch (e) {
      setErr(e.message)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const onEditLimit = async (n) => {
    const q = await api.emailSetLimit(n)
    setQuota(q)
  }
  const onResetLimit = async () => {
    const q = await api.emailResetLimit()
    setQuota(q)
  }

  const counts = FUNNEL_ORDER.reduce((acc, s) => {
    acc[s] = leads.filter((x) => x.status === s).length
    return acc
  }, {})
  const activeCount = (counts.sent || 0) + (counts.in_dialog || 0)
  const handedCount = counts.handed_to_manager || 0
  const wonCount = counts.won || 0
  const withDrafts = conv.filter((c) => c.has_draft)
  const dialogLeads = leads.filter((x) => x.status === 'in_dialog')

  const notifyManager = async (leadId) => {
    setNotifyBusy(leadId)
    try {
      const res = await api.leadNotifyManager(leadId)
      alert(`Уведомление отправлено на: ${(res.recipients || []).join(', ')}`)
      await loadAll()
    } catch (e) {
      alert(`Не получилось: ${e.message}`)
    } finally {
      setNotifyBusy(null)
    }
  }

  return (
    <div className="p-10">
      <PageHeader
        chip="обзор"
        title="Обзор"
        accent="зор"
        description="Состояние воронки, квота отправки сегодня и переписки, где агент ждёт твоего одобрения."
      />

      {docs?.any_empty && (
        <div className="mb-5 flex items-start gap-3 rounded-chip border border-amber-500/40 bg-amber-900/20 p-4 text-amber-200">
          <FileWarning size={20} className="mt-0.5 shrink-0 text-amber-400" />
          <div className="text-[14px]">
            <div className="font-semibold text-amber-100">
              Документы загружены не полностью
            </div>
            <div className="mt-0.5">
              Загрузите прайс-лист и презентацию, чтобы агент мог отправлять
              документы клиентам.{' '}
              <Link
                to="/documents"
                className="font-semibold text-amber-300 hover:underline"
              >
                Перейти к документам
              </Link>
              .
            </div>
          </div>
        </div>
      )}

      {err && (
        <div className="mb-5 rounded-chip border border-red-500/30 bg-red-900/20 p-4 text-[14px] text-red-300">
          Ошибка API: {err}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard label="Всего лидов" value={leads.length} icon={Users} />
        <StatsCard
          label="В работе"
          value={activeCount}
          hint="отправлено + переписка"
          icon={Activity}
        />
        <StatsCard
          label="У менеджера"
          value={handedCount}
          tone={handedCount ? 'accent' : 'default'}
          icon={Flame}
        />
        <StatsCard
          label="Заключено договоров"
          value={wonCount}
          tone={wonCount ? 'lime' : 'default'}
          icon={ClipboardCheck}
        />
      </div>

      {campaign && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Rocket size={16} className="text-fitsiz-green" />
              Статус кампании
            </CardTitle>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {[
                { label: 'В очереди', value: campaign.queued, tone: 'lime' },
                { label: 'Отправлено сегодня', value: campaign.sent_today },
                { label: 'Ждут ответа', value: campaign.awaiting_reply },
                { label: 'В диалоге', value: campaign.in_dialog, tone: 'green' },
                { label: 'У менеджера', value: campaign.handed },
              ].map((m) => (
                <div
                  key={m.label}
                  className="rounded-chip border border-fitsiz-border bg-fitsiz-black/40 px-4 py-4"
                >
                  <div
                    className={cn(
                      'font-heading text-[34px] leading-none',
                      m.tone === 'green'
                        ? 'text-fitsiz-green'
                        : m.tone === 'lime'
                          ? 'text-fitsiz-lime'
                          : 'text-fitsiz-white',
                    )}
                  >
                    {m.value}
                  </div>
                  <div className="mt-2 text-[11px] uppercase tracking-badge text-fitsiz-muted">
                    {m.label}
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Конверсионная воронка</CardTitle>
          </CardHeader>
          <CardBody>
            <FunnelView funnel={funnel} counts={counts} />
          </CardBody>
        </Card>

        <QuotaCard
          quota={quota}
          onEdit={onEditLimit}
          onReset={onResetLimit}
        />
      </div>

      {dialogLeads.length > 0 && (
        <Card className="mt-6 border-fitsiz-green/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flame size={16} className="text-fitsiz-green" />
              Ведётся переписка — можно передать менеджеру
            </CardTitle>
          </CardHeader>
          <CardBody>
            <ul className="divide-y divide-fitsiz-border">
              {dialogLeads.map((l) => (
                <li
                  key={l.id}
                  className="flex items-center justify-between gap-4 py-4"
                >
                  <div className="min-w-0">
                    <Link
                      to={`/conversations/${l.id}`}
                      className="block truncate text-[15px] font-semibold text-fitsiz-white hover:text-fitsiz-green transition-colors"
                    >
                      {l.company_name}
                    </Link>
                    <div className="mt-0.5 truncate text-[13px] text-fitsiz-muted">
                      {l.email}
                    </div>
                  </div>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => notifyManager(l.id)}
                    disabled={notifyBusy === l.id}
                  >
                    <SendHorizonal size={13} />
                    {notifyBusy === l.id ? 'Отправка…' : 'Отправить менеджеру'}
                  </Button>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareWarning size={16} className="text-fitsiz-lime" />
            Переписки с черновиками
          </CardTitle>
        </CardHeader>
        <CardBody>
          {withDrafts.length === 0 ? (
            <div className="text-[14px] text-fitsiz-muted">
              Черновиков сейчас нет. Создайте cold-письмо из{' '}
              <Link
                to="/leads"
                className="text-fitsiz-green hover:underline font-semibold"
              >
                раздела лидов
              </Link>
              .
            </div>
          ) : (
            <ul className="divide-y divide-fitsiz-border">
              {withDrafts.map((c) => (
                <li
                  key={c.lead_id}
                  className="flex items-center justify-between py-4"
                >
                  <div className="min-w-0">
                    <Link
                      to={`/conversations/${c.lead_id}`}
                      className="block truncate text-[15px] font-semibold text-fitsiz-white hover:text-fitsiz-green transition-colors"
                    >
                      {c.lead_company}
                    </Link>
                    <div className="mt-0.5 truncate text-[13px] text-fitsiz-muted">
                      {c.lead_email}
                    </div>
                  </div>
                  <Badge variant={c.lead_status} />
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
