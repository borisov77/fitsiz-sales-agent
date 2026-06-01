import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Upload, Sparkles, ExternalLink, SendHorizonal, Rocket } from 'lucide-react'
import { api } from '../lib/api.js'
import { Card, CardBody } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { Input, Select } from '../components/Input.jsx'
import { Badge } from '../components/Badge.jsx'
import { ImportModal } from '../components/ImportModal.jsx'
import { ManualLeadModal } from '../components/ManualLeadModal.jsx'
import { PageHeader } from '../components/PageHeader.jsx'
import { LEAD_STATUS_RU, COMPANY_TYPE_RU } from '../lib/labels.js'
import { cn } from '../lib/cn.js'

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
  const [manualOpen, setManualOpen] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const [launching, setLaunching] = useState(false)

  const load = async () => {
    setErr(null)
    try {
      const list = await api.leadsList({
        status: status || undefined,
        limit: 500,
      })
      setRows(list || [])
      setSelected(new Set())
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

  const notifyManager = async (leadId) => {
    setBusyId(leadId)
    try {
      const res = await api.leadNotifyManager(leadId)
      alert(`Уведомление отправлено на: ${(res.recipients || []).join(', ')}`)
      await load()
    } catch (e) {
      alert(`Не получилось: ${e.message}`)
    } finally {
      setBusyId(null)
    }
  }

  const toggleOne = (id) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const allVisibleIds = filtered.map((r) => r.id)
  const allChecked =
    allVisibleIds.length > 0 && allVisibleIds.every((id) => selected.has(id))
  const toggleAll = () =>
    setSelected((prev) => {
      if (allChecked) return new Set()
      return new Set(allVisibleIds)
    })

  // Кнопка активна, если выбран хотя бы один new-лид
  const selectedNewCount = filtered.filter(
    (r) => selected.has(r.id) && r.status === 'new',
  ).length

  const launchCampaign = async () => {
    const ids = filtered
      .filter((r) => selected.has(r.id) && r.status === 'new')
      .map((r) => r.id)
    if (ids.length === 0) return
    if (
      !confirm(
        `Запустить рассылку по ${ids.length} лид(ам)? Письма сгенерируются и ` +
          `${'' /* режим решает backend */}встанут в очередь или на модерацию (по настройке AUTO_SEND).`,
      )
    )
      return
    setLaunching(true)
    try {
      const res = await api.launchCampaign(ids)
      const mode = res.auto_send ? 'в очередь на отправку' : 'на модерацию (черновики)'
      alert(
        `Готово. Поставлено ${mode}: ${res.queued + res.drafted}. ` +
          `Пропущено (не new): ${res.skipped}.` +
          (res.errors?.length ? `\nОшибки: ${res.errors.length}` : ''),
      )
      await load()
    } catch (e) {
      alert(`Не получилось: ${e.message}`)
    } finally {
      setLaunching(false)
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
              <Upload size={14} /> Импорт CSV
            </Button>
            <Button variant="outline" size="md" onClick={() => setManualOpen(true)}>
              <Plus size={14} /> Добавить лид вручную
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={launchCampaign}
              disabled={selectedNewCount === 0 || launching}
            >
              <Rocket size={14} />
              {launching
                ? 'Запуск…'
                : `Запустить рассылку${selectedNewCount ? ` (${selectedNewCount})` : ''}`}
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
                  <th className="px-5 py-4 text-left">
                    <input
                      type="checkbox"
                      checked={allChecked}
                      onChange={toggleAll}
                      className="h-4 w-4 accent-fitsiz-green cursor-pointer"
                      aria-label="Выбрать все"
                    />
                  </th>
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
                    className={cn(
                      'border-t border-fitsiz-border hover:bg-fitsiz-black/30 transition-colors',
                      selected.has(r.id) && 'bg-fitsiz-green/5',
                    )}
                  >
                    <td className="px-5 py-4">
                      <input
                        type="checkbox"
                        checked={selected.has(r.id)}
                        onChange={() => toggleOne(r.id)}
                        className="h-4 w-4 accent-fitsiz-green cursor-pointer"
                        aria-label={`Выбрать ${r.company_name}`}
                      />
                    </td>
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
                        {r.status === 'warm' ? (
                          <Button
                            variant="primary"
                            size="xs"
                            onClick={() => notifyManager(r.id)}
                            disabled={busyId === r.id}
                          >
                            <SendHorizonal size={12} />
                            {busyId === r.id ? 'Отправка…' : 'Менеджеру'}
                          </Button>
                        ) : (
                          <Button
                            variant="primary"
                            size="xs"
                            onClick={() => generateCold(r.id)}
                            disabled={busyId === r.id}
                          >
                            <Sparkles size={12} />
                            {busyId === r.id ? 'Создаю…' : 'Cold'}
                          </Button>
                        )}
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
                      colSpan={8}
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
      <ManualLeadModal
        open={manualOpen}
        onClose={() => setManualOpen(false)}
        onCreated={load}
      />
    </div>
  )
}
