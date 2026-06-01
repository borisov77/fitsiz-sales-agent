import { useState } from 'react'
import { Modal } from './Modal.jsx'
import { Button } from './Button.jsx'
import { Input, Textarea } from './Input.jsx'
import { api } from '../lib/api.js'

const EMPTY = { company_name: '', email: '', description: '', contact_name: '' }

function isEmail(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())
}

export function ManualLeadModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const close = () => {
    setForm(EMPTY)
    setErr(null)
    setBusy(false)
    onClose?.()
  }

  const submit = async () => {
    setErr(null)
    if (!form.company_name.trim()) return setErr('Укажите название компании')
    if (!isEmail(form.email)) return setErr('Укажите корректный email')
    if (!form.description.trim()) return setErr('Опишите компанию — это контекст для бота')

    setBusy(true)
    try {
      const lead = await api.leadCreateManual({
        company_name: form.company_name.trim(),
        email: form.email.trim(),
        description: form.description.trim(),
        contact_name: form.contact_name.trim() || null,
      })
      onCreated?.(lead)
      close()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const label = 'mb-1.5 block text-[12px] uppercase tracking-badge text-fitsiz-muted'

  return (
    <Modal
      open={open}
      onClose={close}
      title="Добавить лид вручную"
      footer={
        <>
          <Button variant="outline" onClick={close}>
            Отмена
          </Button>
          <Button variant="primary" onClick={submit} disabled={busy}>
            {busy ? 'Добавляю…' : 'Добавить'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className={label}>
            Компания <span className="text-fitsiz-green">*</span>
          </label>
          <Input
            value={form.company_name}
            onChange={set('company_name')}
            placeholder="ООО Сварка-Опт"
            autoFocus
          />
        </div>

        <div>
          <label className={label}>
            Email <span className="text-fitsiz-green">*</span>
          </label>
          <Input
            type="email"
            value={form.email}
            onChange={set('email')}
            placeholder="zakaz@company.ru"
          />
        </div>

        <div>
          <label className={label}>
            Описание компании <span className="text-fitsiz-green">*</span>
          </label>
          <Textarea
            rows={4}
            value={form.description}
            onChange={set('description')}
            placeholder="Чем занимается, что важно знать боту: специализация, размер, что ищут, на что обратить внимание в письме…"
          />
        </div>

        <div>
          <label className={label}>Контактное лицо</label>
          <Input
            value={form.contact_name}
            onChange={set('contact_name')}
            placeholder="Иванов Сергей (необязательно)"
          />
        </div>

        {err && (
          <div className="rounded-chip border border-red-500/30 bg-red-900/20 p-3 text-[13px] text-red-300">
            {err}
          </div>
        )}
      </div>
    </Modal>
  )
}
