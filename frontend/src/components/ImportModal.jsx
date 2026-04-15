import { useRef, useState } from 'react'
import { Modal } from './Modal.jsx'
import { Button } from './Button.jsx'
import { api } from '../lib/api.js'

export function ImportModal({ open, onClose, onImported }) {
  const inputRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)

  const reset = () => {
    setBusy(false)
    setResult(null)
    setErr(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const submit = async () => {
    const f = inputRef.current?.files?.[0]
    if (!f) {
      setErr('Выберите CSV или XLSX файл')
      return
    }
    setBusy(true)
    setErr(null)
    try {
      const res = await api.leadsImport(f)
      setResult(res)
      onImported?.(res)
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset()
        onClose?.()
      }}
      title="Импорт лидов из CSV/XLSX"
      footer={
        <>
          <Button
            variant="outline"
            onClick={() => {
              reset()
              onClose?.()
            }}
          >
            Закрыть
          </Button>
          <Button onClick={submit} disabled={busy}>
            {busy ? 'Импорт…' : 'Импортировать'}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Ожидаемые колонки: <code>company_name, contact_name, email, phone, city,
          region, company_type, specialization, website, source, notes</code>.
          Дубли по email пропускаются.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="block w-full text-sm"
        />
        {err && (
          <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
            {err}
          </div>
        )}
        {result && (
          <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm">
            <div>Всего строк: <b>{result.total_rows}</b></div>
            <div>Создано: <b>{result.created}</b></div>
            <div>Пропущено дублей: <b>{result.skipped_duplicates}</b></div>
            {result.errors?.length ? (
              <div className="mt-1 text-red-700">
                Ошибок: {result.errors.length}
                <ul className="mt-1 list-inside list-disc">
                  {result.errors.slice(0, 5).map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </Modal>
  )
}
