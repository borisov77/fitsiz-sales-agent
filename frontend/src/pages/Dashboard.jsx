import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Users,
  Flame,
  ClipboardCheck,
  Activity,
  MessageSquareWarning,
} from 'lucide-react'
import { api } from '../lib/api.js'
import { StatsCard } from '../components/StatsCard.jsx'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'

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

export default function Dashboard() {
  const [leads, setLeads] = useState([])
  const [quota, setQuota] = useState(null)
  const [conv, setConv] = useState([])
  const [err, setErr] = useState(null)

  useEffect(() => {
    ;(async () => {
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
    })()
  }, [])

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
    <div className="p-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <div className="font-body text-[11px] font-bold uppercase tracking-badge text-fitsiz-muted">
            FITSIZ · Sales Agent
          </div>
          <h1 className="mt-1 font-heading text-3xl">Обзор</h1>
        </div>
      </div>

      {err && (
        <div className="mb-4 rounded-chip border border-red-500/30 bg-red-900/20 p-3 text-sm text-red-300">
          Ошибка API: {err}
        </div>
      )}

      {/* Метрики */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard label="Всего лидов" value={leads.length} icon={Users} />
        <StatsCard
          label="В работе"
          value={activeCount}
          hint="contacted → negotiating"
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

      {/* Воронка + квота */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Воронка по статусам</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="flex flex-wrap gap-2">
              {FUNNEL_ORDER.map((s) => (
                <div
                  key={s}
                  className="flex items-center gap-2 rounded-chip bg-fitsiz-black/40 border border-fitsiz-border px-3 py-2"
                >
                  <Badge variant={s}>{s.replace('_', ' ')}</Badge>
                  <span className="font-heading text-base text-fitsiz-white">
                    {counts[s] || 0}
                  </span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Квота отправки сегодня</CardTitle>
          </CardHeader>
          <CardBody>
            {quota ? (
              <div>
                <div className="flex items-baseline gap-2">
                  <div className="font-heading text-5xl leading-none text-fitsiz-green">
                    {quota.sent_today}
                  </div>
                  <div className="font-heading text-xl text-fitsiz-muted">
                    / {quota.daily_limit}
                  </div>
                </div>
                <div className="mt-2 text-xs uppercase tracking-badge text-fitsiz-muted">
                  Осталось: <span className="text-fitsiz-white font-bold">{quota.remaining}</span>
                </div>
                <div className="mt-4 h-1.5 w-full overflow-hidden rounded-pill bg-fitsiz-surface-2">
                  <div
                    className="h-full bg-fitsiz-green transition-all duration-300"
                    style={{
                      width: `${
                        quota.daily_limit
                          ? Math.min(100, (quota.sent_today / quota.daily_limit) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            ) : (
              <div className="text-sm text-fitsiz-muted">загрузка…</div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Черновики */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareWarning size={14} className="text-fitsiz-lime" />
            Переписки с черновиками
          </CardTitle>
        </CardHeader>
        <CardBody>
          {withDrafts.length === 0 ? (
            <div className="text-sm text-fitsiz-muted">
              Черновиков сейчас нет. Создайте cold-письмо из{' '}
              <Link to="/leads" className="text-fitsiz-green hover:underline">
                раздела лидов
              </Link>
              .
            </div>
          ) : (
            <ul className="divide-y divide-fitsiz-border">
              {withDrafts.map((c) => (
                <li key={c.lead_id} className="flex items-center justify-between py-3">
                  <div className="min-w-0">
                    <Link
                      to={`/conversations/${c.lead_id}`}
                      className="block truncate text-sm font-semibold text-fitsiz-white hover:text-fitsiz-green transition-colors"
                    >
                      {c.lead_company}
                    </Link>
                    <div className="truncate text-xs text-fitsiz-muted">
                      {c.lead_email}
                    </div>
                  </div>
                  <Badge variant={c.lead_status}>{c.lead_status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
