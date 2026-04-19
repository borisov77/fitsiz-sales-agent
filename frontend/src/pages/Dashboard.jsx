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
} from 'lucide-react'
import { api } from '../lib/api.js'
import { StatsCard } from '../components/StatsCard.jsx'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'
import { Button } from '../components/Button.jsx'
import { Input } from '../components/Input.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
import { LEAD_STATUS_RU } from '../lib/labels.js'

const FUNNEL_ORDER = [
  'new',
  'contacted',
  'follow_up_1',
  'follow_up_2',
  'follow_up_3',
  'replied',
  'interested',
  'negotiating',
  'warm',
  'transferred',
  'rejected',
  'unsubscribed',
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

export default function Dashboard() {
  const [leads, setLeads] = useState([])
  const [quota, setQuota] = useState(null)
  const [conv, setConv] = useState([])
  const [err, setErr] = useState(null)

  const loadAll = useCallback(async () => {
    try {
      const [l, q, c] = await Promise.all([
        api.leadsList({ limit: 1000 }),
        api.emailQuota(),
        api.conversationsList({ limit: 500 }),
      ])
      setLeads(l || [])
      setQuota(q)
      setConv(c || [])
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
  const activeCount =
    counts.contacted +
    counts.follow_up_1 +
    counts.follow_up_2 +
    counts.follow_up_3 +
    counts.replied +
    counts.interested +
    counts.negotiating
  const warmCount = counts.warm || 0
  const transferred = counts.transferred || 0
  const withDrafts = conv.filter((c) => c.has_draft)

  return (
    <div className="p-10">
      <PageHeader
        chip="обзор"
        title="Обзор"
        accent="зор"
        description="Состояние воронки, квота отправки сегодня и переписки, где агент ждёт твоего одобрения."
      />

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
          hint="письма ушли, ждём реакции"
          icon={Activity}
        />
        <StatsCard
          label="Тёплые"
          value={warmCount}
          tone={warmCount ? 'accent' : 'default'}
          icon={Flame}
        />
        <StatsCard
          label="Передано менеджеру"
          value={transferred}
          tone={transferred ? 'lime' : 'default'}
          icon={ClipboardCheck}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Воронка по статусам</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="flex flex-wrap gap-2.5">
              {FUNNEL_ORDER.map((s) => (
                <div
                  key={s}
                  className="flex items-center gap-3 rounded-chip bg-fitsiz-black/40 border border-fitsiz-border px-4 py-2.5"
                >
                  <Badge variant={s}>{LEAD_STATUS_RU[s]}</Badge>
                  <span className="font-heading text-[20px] leading-none text-fitsiz-white">
                    {counts[s] || 0}
                  </span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        <QuotaCard
          quota={quota}
          onEdit={onEditLimit}
          onReset={onResetLimit}
        />
      </div>

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
