import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { Card, CardBody } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'
import { Button } from '../components/Button.jsx'
import { RefreshCcw, Inbox, ArrowUpRight } from 'lucide-react'

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

  return (
    <div className="p-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="font-body text-[11px] font-bold uppercase tracking-badge text-fitsiz-muted">
            Диалоги
          </div>
          <h1 className="mt-1 font-heading text-3xl">Переписки</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load}>
            <RefreshCcw size={14} /> Обновить
          </Button>
          <Button variant="primary" onClick={checkInbox} disabled={busy}>
            <Inbox size={14} /> {busy ? 'IMAP…' : 'Проверить входящие'}
          </Button>
        </div>
      </div>

      {err && (
        <div className="mb-4 rounded-chip border border-red-500/30 bg-red-900/20 p-3 text-sm text-red-300">
          {err}
        </div>
      )}

      <Card>
        <CardBody className="p-0">
          {rows.length === 0 ? (
            <div className="p-10 text-center text-sm text-fitsiz-muted">
              Переписок пока нет.
            </div>
          ) : (
            <ul className="divide-y divide-fitsiz-border">
              {rows.map((r) => (
                <li key={r.lead_id}>
                  <Link
                    to={`/conversations/${r.lead_id}`}
                    className="group flex items-center gap-4 px-6 py-4 hover:bg-fitsiz-black/30 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="truncate text-sm font-semibold text-fitsiz-white group-hover:text-fitsiz-green transition-colors">
                          {r.lead_company}
                        </div>
                        <Badge variant={r.lead_status}>{r.lead_status}</Badge>
                        {r.has_draft && <Badge variant="draft">черновик</Badge>}
                      </div>
                      <div className="mt-1 truncate text-xs text-fitsiz-muted">
                        {r.lead_email}
                      </div>
                    </div>
                    <div className="text-right text-[10px] uppercase tracking-badge text-fitsiz-muted">
                      <div className="text-fitsiz-white">
                        {r.total_messages} <span className="text-fitsiz-muted">сообщ.</span>
                      </div>
                      <div className="mt-0.5 normal-case tracking-normal text-[11px]">
                        {r.last_message_at
                          ? new Date(r.last_message_at).toLocaleString('ru-RU')
                          : '—'}
                      </div>
                    </div>
                    <ArrowUpRight
                      size={16}
                      className="text-fitsiz-muted group-hover:text-fitsiz-green transition-colors"
                    />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
