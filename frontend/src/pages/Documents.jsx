import { useCallback, useEffect, useRef, useState } from 'react'
import {
  FileSpreadsheet,
  FileText,
  Upload,
  RefreshCw,
  Trash2,
  CheckCircle2,
} from 'lucide-react'
import { api } from '../lib/api.js'
import { Card, CardBody, CardHeader, CardTitle } from '../components/Card.jsx'
import { Button } from '../components/Button.jsx'
import { PageHeader } from '../components/PageHeader.jsx'

const ICONS = {
  pricelist: FileSpreadsheet,
  presentation: FileText,
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function DocumentSlot({ slot, onUpload, onDelete }) {
  const inputRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const Icon = ICONS[slot.key] || FileText

  const pick = () => {
    setErr(null)
    inputRef.current?.click()
  }

  const onFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setErr(null)
    try {
      await onUpload(slot.key, file)
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const remove = async () => {
    if (!confirm(`Удалить «${slot.title}»?`)) return
    setBusy(true)
    setErr(null)
    try {
      await onDelete(slot.key)
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setBusy(false)
    }
  }

  const uploadLabel =
    slot.key === 'pricelist' ? 'Загрузить прайс-лист' : 'Загрузить презентацию'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Icon size={18} className="text-fitsiz-green" />
          {slot.title}
        </CardTitle>
      </CardHeader>
      <CardBody>
        <input
          ref={inputRef}
          type="file"
          accept={slot.accept.join(',')}
          onChange={onFile}
          className="hidden"
        />

        {slot.uploaded ? (
          <div>
            <div className="flex items-start gap-3 rounded-chip border border-fitsiz-green/30 bg-fitsiz-green/10 p-4">
              <CheckCircle2
                size={20}
                className="mt-0.5 shrink-0 text-fitsiz-green"
              />
              <div className="min-w-0">
                <div className="truncate text-[15px] font-semibold text-fitsiz-white">
                  {slot.filename}
                </div>
                <div className="mt-0.5 text-[13px] text-fitsiz-muted">
                  Загружено: {formatDate(slot.uploaded_at) || '—'}
                </div>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={pick}
                disabled={busy}
              >
                <RefreshCw size={13} /> {busy ? 'Загрузка…' : 'Заменить'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={remove}
                disabled={busy}
              >
                <Trash2 size={13} /> Удалить
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-start gap-4 rounded-chip border border-dashed border-fitsiz-border bg-fitsiz-black/40 p-6">
            <div className="text-[14px] text-fitsiz-muted">
              Слот пуст. Агент не сможет отправлять этот документ, пока он не
              загружен.
            </div>
            <Button variant="primary" size="sm" onClick={pick} disabled={busy}>
              <Upload size={14} /> {busy ? 'Загрузка…' : uploadLabel}
            </Button>
          </div>
        )}

        {err && (
          <div className="mt-3 rounded-chip border border-red-500/30 bg-red-900/20 p-3 text-[13px] text-red-300">
            {err}
          </div>
        )}

        <div className="mt-4 text-[12px] uppercase tracking-badge text-fitsiz-muted">
          {slot.format_label}
        </div>
      </CardBody>
    </Card>
  )
}

export default function Documents() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback(async () => {
    try {
      const d = await api.documents()
      setData(d)
    } catch (e) {
      setErr(e.message)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onUpload = async (slot, file) => {
    await api.documentUpload(slot, file)
    await load()
  }
  const onDelete = async (slot) => {
    await api.documentDelete(slot)
    await load()
  }

  const slots = data?.slots

  return (
    <div className="p-10">
      <PageHeader
        chip="документы"
        title="Документы"
        accent="ты"
        description="Два документа, которыми оперирует агент: прайс-лист и презентация. Загрузите файлы здесь — агент будет прикладывать их к письмам по ситуации."
      />

      {err && (
        <div className="mb-5 rounded-chip border border-red-500/30 bg-red-900/20 p-4 text-[14px] text-red-300">
          Ошибка API: {err}
        </div>
      )}

      {data?.any_empty && (
        <div className="mb-5 rounded-chip border border-amber-500/40 bg-amber-900/20 p-4 text-[14px] text-amber-200">
          Загрузите прайс-лист и презентацию, чтобы агент мог отправлять
          документы клиентам.
        </div>
      )}

      {!slots ? (
        <div className="text-[14px] text-fitsiz-muted">загрузка…</div>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <DocumentSlot
            slot={slots.pricelist}
            onUpload={onUpload}
            onDelete={onDelete}
          />
          <DocumentSlot
            slot={slots.presentation}
            onUpload={onUpload}
            onDelete={onDelete}
          />
        </div>
      )}
    </div>
  )
}
