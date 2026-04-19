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
      title="Импорт лидов из CSV / XLSX"
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
          <Button variant="primary" onClick={submit} disabled={busy}>
            {busy ? 'Импорт…' : 'Импортировать'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-fitsiz-muted-light">
          Ожидаемые колонки:{' '}
          <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-[11px] text-fitsiz-lime">
            company_name, contact_name, email, phone, city, region,
            company_type, specialization, website, source, notes
          </code>
          . Дубли по email пропускаются.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="block w-full text-sm text-fitsiz-muted-light"
        />
        {err && (
          <div className="rounded-chip border border-red-500/30 bg-red-900/20 p-3 text-sm text-red-300">
            {err}
          </div>
        )}
        {result && (
          <div className="space-y-1 rounded-card border border-fitsiz-green/30 bg-fitsiz-green/10 p-4 text-sm text-fitsiz-white">
            <div>
              Всего строк:{' '}
              <b className="text-fitsiz-green">{result.total_rows}</b>
            </div>
            <div>
              Создано:{' '}
              <b className="text-fitsiz-green">{result.created}</b>
            </div>
            <div>
              Пропущено дублей:{' '}
              <b className="text-fitsiz-muted-light">
                {result.skipped_duplicates}
              </b>
            </div>
            {result.errors?.length ? (
              <div className="mt-2 text-red-300">
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
