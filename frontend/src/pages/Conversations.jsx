import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { Card, CardBody } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'
import { Button } from '../components/Button.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
import { CONVERSATION_SECTIONS } from '../lib/labels.js'
import { RefreshCcw, Inbox, ArrowUpRight } from 'lucide-react'

function ConversationRow({ r }) {
  return (
    <li>
      <Link
        to={`/conversations/${r.lead_id}`}
        className="group flex items-center gap-5 px-7 py-5 hover:bg-fitsiz-black/30 transition-colors"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="truncate text-[16px] font-semibold text-fitsiz-white group-hover:text-fitsiz-green transition-colors">
              {r.lead_company}
            </div>
            <Badge variant={r.lead_status} />
            {r.has_draft && <Badge variant="draft" />}
          </div>
          <div className="mt-1 truncate text-[13px] text-fitsiz-muted">
            {r.lead_email}
          </div>
        </div>
        <div className="text-right text-[11px] uppercase tracking-badge text-fitsiz-muted">
          <div className="text-[14px] normal-case tracking-normal text-fitsiz-white font-semibold">
            {r.total_messages}{' '}
            <span className="text-fitsiz-muted font-normal">сообщ.</span>
          </div>
          <div className="mt-1 normal-case tracking-normal text-[12px]">
            {r.last_message_at
              ? new Date(r.last_message_at).toLocaleString('ru-RU')
              : '—'}
          </div>
        </div>
        <ArrowUpRight
          size={18}
          className="text-fitsiz-muted group-hover:text-fitsiz-green transition-colors"
        />
      </Link>
    </li>
  )
}

function Section({ section, rows }) {
  const { title, main } = section
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-center gap-3">
        <h2
          className={
            'font-body text-[13px] font-bold uppercase tracking-badge ' +
            (main ? 'text-fitsiz-green' : 'text-fitsiz-muted-light')
          }
        >
          {title}
        </h2>
        <span
          className={
            'rounded-pill px-2.5 py-0.5 text-[12px] font-bold ' +
            (main
              ? 'bg-fitsiz-green/15 text-fitsiz-green ring-1 ring-fitsiz-green/40'
              : 'bg-fitsiz-surface-2 text-fitsiz-muted-light ring-1 ring-fitsiz-border')
          }
        >
          {rows.length}
        </span>
      </div>
      <Card
        className={main ? 'ring-1 ring-fitsiz-green/30 transition-shadow' : ''}
      >
        <CardBody className="p-0">
          {rows.length === 0 ? (
            <div className="p-8 text-center text-[14px] text-fitsiz-muted">
              Нет лидов в этом разделе
            </div>
          ) : (
            <ul className="divide-y divide-fitsiz-border">
              {rows.map((r) => (
                <ConversationRow key={r.lead_id} r={r} />
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </section>
  )
}

export default function Conversations() {
  const [rows, setRows] = useState([])
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    setErr(null)
    try {
      const l = await api.conversationsList({ limit: 300 })
      setRows(l || [])
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const checkInbox = async () => {
    setBusy(true)
    try {
      const res = await api.emailCheckInbox()
      alert(`Проверено: ${res.checked}, связано с лидами: ${res.matched}`)
      await load()
    } catch (e) {
      alert(`IMAP: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  // Группируем по разделам на фронте (API уже отдаёт статусы).
  const grouped = CONVERSATION_SECTIONS.map((section) => ({
    section,
    rows: rows.filter((r) => section.statuses.includes(r.lead_status)),
  }))

  return (
    <div className="p-10">
      <PageHeader
        chip="диалоги"
        title="Переписки"
        accent="писки"
        description="Все цепочки с клиентами. Черновики AI, одобрение, отправка — здесь."
        actions={
          <>
            <Button variant="outline" size="md" onClick={load}>
              <RefreshCcw size={14} /> Обновить
            </Button>
            <Button variant="primary" size="md" onClick={checkInbox} disabled={busy}>
              <Inbox size={14} /> {busy ? 'IMAP…' : 'Проверить входящие'}
            </Button>
          </>
        }
      />

      {err && (
        <div className="mb-5 rounded-chip border border-red-500/30 bg-red-900/20 p-4 text-[14px] text-red-300">
          {err}
        </div>
      )}

      {rows.length === 0 && !err ? (
        <Card>
          <CardBody className="p-12 text-center text-[15px] text-fitsiz-muted">
            Переписок пока нет.
          </CardBody>
        </Card>
      ) : (
        grouped.map(({ section, rows: secRows }) => (
          <Section key={section.key} section={section} rows={secRows} />
        ))
      )}
    </div>
  )
}
