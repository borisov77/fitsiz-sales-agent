import { useRef, useState } from 'react'
import { Download } from 'lucide-react'
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
          Единый формат — 4 колонки:{' '}
          <code className="rounded-chip bg-fitsiz-surface-2 px-2 py-0.5 font-mono text-[11px] text-fitsiz-lime">
            company_name, email, description, contact_name
          </code>
          . Обязательны <b className="text-fitsiz-white">company_name</b>,{' '}
          <b className="text-fitsiz-white">email</b>,{' '}
          <b className="text-fitsiz-white">description</b>;{' '}
          <code className="font-mono text-[11px] text-fitsiz-lime">contact_name</code>{' '}
          можно оставить пустым. Дубли по email пропускаются.
        </p>

        <div className="rounded-chip border border-fitsiz-border bg-fitsiz-black/40 p-3">
          <div className="mb-2 text-[12px] uppercase tracking-badge text-fitsiz-muted">
            Пример строки
          </div>
          <code className="block whitespace-pre-wrap break-all font-mono text-[11px] text-fitsiz-muted-light">
            ООО Сварка-Опт,zakaz@svarka-opt.ru,"Оптовый магазин сварки и СИЗ в
            Казани, интересует расширение ассортимента масок",Иванов Сергей
          </code>
          <a
            href={api.leadCsvTemplateUrl}
            download
            className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-semibold text-fitsiz-green hover:underline"
          >
            <Download size={13} /> Скачать шаблон CSV
          </a>
        </div>

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
