import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Upload, Sparkles, ExternalLink } from 'lucide-react'
import { api } from '../lib/api.js'
import { Card, CardBody } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Select } from '../components/Input.jsx'
import { Badge } from '../components/Badge.jsx'
import { ImportModal } from '../components/ImportModal.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
import { LEAD_STATUS_RU, COMPANY_TYPE_RU } from '../lib/labels.js'

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
      const list = await api.leadsList({
        status: status || undefined,
        limit: 500,
      })
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
      alert('Черновик создан — откройте «Переписки».')
    } catch (e) {
      alert(`Не получилось: ${e.message}`)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="p-10">
      <PageHeader
        chip="база"
        title="Лиды"
        accent="ды"
        description="Потенциальные партнёры FITSIZ. Импортируй CSV или XLSX, запусти cold-письмо по одному клику."
        actions={
          <>
            <Button variant="outline" size="md" onClick={() => setImportOpen(true)}>
              <Upload size={14} /> Импорт
            </Button>
            <Button variant="primary" size="md" disabled>
              <Plus size={14} /> Добавить
            </Button>
          </>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Input
          placeholder="Поиск: компания, email, город, контакт"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-56"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? LEAD_STATUS_RU[s] : 'все статусы'}
            </option>
          ))}
        </Select>
        <div className="ml-auto text-[12px] uppercase tracking-badge text-fitsiz-muted">
          Показано:{' '}
          <span className="text-fitsiz-white font-bold">{filtered.length}</span>{' '}
          / {rows.length}
        </div>
      </div>

      {err && (
        <div className="mb-5 rounded-chip border border-red-500/30 bg-red-900/20 p-4 text-[14px] text-red-300">
          {err}
        </div>
      )}

      <Card>
        <CardBody className="p-0">
          <div className="overflow-auto">
            <table className="w-full text-[14px]">
              <thead className="bg-fitsiz-black/40 text-[11px] uppercase tracking-badge text-fitsiz-muted">
                <tr>
                  <th className="px-6 py-4 text-left font-bold">Компания</th>
                  <th className="px-6 py-4 text-left font-bold">Контакт</th>
                  <th className="px-6 py-4 text-left font-bold">Email</th>
                  <th className="px-6 py-4 text-left font-bold">Город</th>
                  <th className="px-6 py-4 text-left font-bold">Статус</th>
                  <th className="px-6 py-4 text-left font-bold">Тип</th>
                  <th className="px-6 py-4 text-right font-bold">Действия</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={r.id}
                    className="border-t border-fitsiz-border hover:bg-fitsiz-black/30 transition-colors"
                  >
                    <td className="px-6 py-4 font-semibold text-fitsiz-white">
                      <Link
                        to={`/conversations/${r.id}`}
                        className="hover:text-fitsiz-green transition-colors"
                      >
                        {r.company_name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-fitsiz-muted-light">
                      {r.contact_name || '—'}
                    </td>
                    <td className="px-6 py-4 text-fitsiz-muted-light">
                      {r.email}
                    </td>
                    <td className="px-6 py-4 text-fitsiz-muted-light">
                      {r.city || '—'}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={r.status} />
                    </td>
                    <td className="px-6 py-4 text-fitsiz-muted">
                      {COMPANY_TYPE_RU[r.company_type] || r.company_type}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="inline-flex gap-2">
                        <Button
                          variant="primary"
                          size="xs"
                          onClick={() => generateCold(r.id)}
                          disabled={busyId === r.id}
                        >
                          <Sparkles size={12} />
                          {busyId === r.id ? 'Создаю…' : 'Cold'}
                        </Button>
                        <Link to={`/conversations/${r.id}`}>
                          <Button variant="outline" size="xs">
                            <ExternalLink size={12} /> Открыть
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-6 py-16 text-center text-[15px] text-fitsiz-muted"
                    >
                      Ничего не найдено. Импортируйте CSV с лидами.
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
