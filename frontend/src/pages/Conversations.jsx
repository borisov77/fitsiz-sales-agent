import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { Card, CardBody } from '../components/Card.jsx'
import { Badge } from '../components/Badge.jsx'
import { Button } from '../components/Button.jsx'
import { RefreshCcw, Inbox } from 'lucide-react'

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
    <div className="p-6">
      <div className="mb-4 flex items-center gap-2">
        <h1 className="mr-auto text-lg font-semibold">Переписки</h1>
        <Button variant="outline" onClick={load}>
          <RefreshCcw size={14} /> Обновить
        </Button>
        <Button variant="outline" onClick={checkInbox} disabled={busy}>
          <Inbox size={14} /> {busy ? 'IMAP…' : 'Проверить входящие'}
        </Button>
      </div>
      {err && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {err}
        </div>
      )}
      <Card>
        <CardBody className="p-0">
          {rows.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              Переписок пока нет.
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {rows.map((r) => (
                <li key={r.lead_id}>
                  <Link
                    to={`/conversations/${r.lead_id}`}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-muted/40"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <div className="truncate text-sm font-medium">
                          {r.lead_company}
                        </div>
                        <Badge variant={r.lead_status}>{r.lead_status}</Badge>
                        {r.has_draft && (
                          <Badge variant="draft">черновик</Badge>
                        )}
                      </div>
                      <div className="mt-0.5 truncate text-xs text-muted-foreground">
                        {r.lead_email}
                      </div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div>{r.total_messages} сообщ.</div>
                      <div>
                        {r.last_message_at
                          ? new Date(r.last_message_at).toLocaleString('ru-RU')
                          : '—'}
                      </div>
                    </div>
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
