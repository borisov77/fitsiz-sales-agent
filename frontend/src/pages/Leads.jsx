import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Upload, Sparkles } from 'lucide-react'
import { api } from '../lib/api.js'
import { Card, CardBody } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Select } from '../components/Input.jsx'
import { Badge } from '../components/Badge.jsx'
import { ImportModal } from '../components/ImportModal.jsx'

const STATUSES = [
  '',
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

export default function Leads() {
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [err, setErr] = useState(null)
  const [importOpen, setImportOpen] = useState(false)
  const [busyId, setBusyId] = useState(null)

  const load = async () => {
    setErr(null)
    try {
      const list = await api.leadsList({ status: status || undefined, limit: 500 })
      setRows(list || [])
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const filtered = rows.filter((r) => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return (
      r.company_name?.toLowerCase().includes(q) ||
      r.email?.toLowerCase().includes(q) ||
      r.city?.toLowerCase().includes(q) ||
      r.contact_name?.toLowerCase().includes(q)
    )
  })

  const generateCold = async (leadId) => {
    setBusyId(leadId)
    try {
      await api.draftCold(leadId)
      alert('Черновик создан — открой раздел «Переписки».')
    } catch (e) {
      alert(`Не получилось: ${e.message}`)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h1 className="mr-auto text-lg font-semibold">Лиды</h1>
        <Button variant="outline" onClick={() => setImportOpen(true)}>
          <Upload size={14} /> Импорт CSV/XLSX
        </Button>
        <Button variant="outline" disabled>
          <Plus size={14} /> Добавить вручную
        </Button>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Поиск: компания, email, город, контакт"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-52">
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s || 'все статусы'}
            </option>
          ))}
        </Select>
        <div className="ml-auto text-xs text-muted-foreground">
          показано: {filtered.length} / {rows.length}
        </div>
      </div>

      {err && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Ошибка: {err}
        </div>
      )}

      <Card>
        <CardBody className="p-0">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left">Компания</th>
                  <th className="px-4 py-2 text-left">Контакт</th>
                  <th className="px-4 py-2 text-left">Email</th>
                  <th className="px-4 py-2 text-left">Город</th>
                  <th className="px-4 py-2 text-left">Статус</th>
                  <th className="px-4 py-2 text-left">Тип</th>
                  <th className="px-4 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id} className="border-t border-border hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">
                      <Link
                        to={`/conversations/${r.id}`}
                        className="hover:underline"
                      >
                        {r.company_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {r.contact_name || '—'}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{r.email}</td>
                    <td className="px-4 py-2 text-muted-foreground">{r.city || '—'}</td>
                    <td className="px-4 py-2">
                      <Badge variant={r.status}>{r.status}</Badge>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{r.company_type}</td>
                    <td className="px-4 py-2 text-right">
                      <div className="inline-flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => generateCold(r.id)}
                          disabled={busyId === r.id}
                        >
                          <Sparkles size={14} />
                          {busyId === r.id ? 'Генерация…' : 'Cold-письмо'}
                        </Button>
                        <Link to={`/conversations/${r.id}`}>
                          <Button variant="ghost" size="sm">Открыть</Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                      Ничего не найдено. Попробуйте импортировать CSV.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>

      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={load}
      />
    </div>
  )
}
