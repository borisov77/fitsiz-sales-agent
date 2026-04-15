import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import { StatsCard } from '../components/StatsCard.jsx'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'
import { Link } from 'react-router-dom'

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
    async function load() {
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
    }
    load()
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
    <div className="p-6">
      <h1 className="mb-4 text-lg font-semibold">Dashboard</h1>
      {err && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Ошибка API: {err}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard label="Всего лидов" value={leads.length} />
        <StatsCard label="В работе" value={activeCount} hint="contacted → negotiating" />
        <StatsCard label="Тёплые" value={warmCount} tone={warmCount ? 'warn' : undefined} />
        <StatsCard
          label="Передано менеджеру"
          value={transferred}
          tone={transferred ? 'ok' : undefined}
        />
      </div>

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
                  className="flex items-center gap-2 rounded-md border border-border px-3 py-2"
                >
                  <Badge variant={s}>{s}</Badge>
                  <span className="text-sm font-medium">{counts[s] || 0}</span>
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
                <div className="text-3xl font-semibold">
                  {quota.sent_today}{' '}
                  <span className="text-base font-normal text-muted-foreground">
                    / {quota.daily_limit}
                  </span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Осталось: {quota.remaining}
                </div>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-primary"
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
              <div className="text-sm text-muted-foreground">загрузка…</div>
            )}
          </CardBody>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Переписки с черновиками</CardTitle>
        </CardHeader>
        <CardBody>
          {withDrafts.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              Черновиков сейчас нет. Создайте cold-письмо через{' '}
              <Link to="/leads" className="text-primary underline">
                раздел лидов
              </Link>
              .
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {withDrafts.map((c) => (
                <li key={c.lead_id} className="flex items-center justify-between py-2">
                  <div className="min-w-0">
                    <Link
                      to={`/conversations/${c.lead_id}`}
                      className="block truncate text-sm font-medium hover:underline"
                    >
                      {c.lead_company}
                    </Link>
                    <div className="truncate text-xs text-muted-foreground">
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
