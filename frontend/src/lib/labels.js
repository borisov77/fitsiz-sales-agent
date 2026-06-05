// Русские подписи для enum-значений, приходящих с backend'а.
// На бэке остаются английские ключи (API стабильный), UI переводит при рендере.

export const LEAD_STATUS_RU = {
  created: 'Создано',
  sent: 'Отправлено',
  in_dialog: 'Ведётся переписка',
  handed_to_manager: 'Отправлено менеджеру',
  won: 'Заключён договор',
  lost: 'Сделка не состоялась',
  no_reply: 'Осталось без ответа',
}

// Бакет «диалога» — рабочая зона человека (лид ответил, ведём переписку).
export const DIALOG_STATUSES = ['in_dialog']

// Разделы списка переписок. Порядок = порядок вывода: рабочая зона сверху.
export const CONVERSATION_SECTIONS = [
  {
    key: 'dialog',
    title: 'Ведётся переписка',
    statuses: ['in_dialog'],
    main: true,
  },
  { key: 'cold', title: 'Холодные', statuses: ['created', 'sent'] },
  { key: 'no_reply', title: 'Осталось без ответа', statuses: ['no_reply'] },
  { key: 'manager', title: 'У менеджера', statuses: ['handed_to_manager'] },
  { key: 'closed', title: 'Закрытые', statuses: ['won', 'lost'] },
]

export const MESSAGE_STATUS_RU = {
  draft: 'Черновик',
  queued: 'В очереди',
  sent: 'Отправлено',
  delivered: 'Доставлено',
  read: 'Прочитано',
  received: 'Входящее',
  bounced: 'Отскочило',
  failed: 'Ошибка',
}

export const COMPANY_TYPE_RU = {
  retailer: 'Розница',
  distributor: 'Дистрибьютор',
  manufacturer: 'Производитель',
  other: 'Другое',
}

export const INTENT_RU = {
  interest: 'Интерес',
  question: 'Вопрос',
  objection: 'Возражение',
  ready: 'Готов к сделке',
  reject: 'Отказ',
  unsubscribe: 'Отписка',
  autoreply: 'Автоответ',
  out_of_scope: 'Вне зоны',
}

export const ESTIMATED_VOLUME_RU = {
  small: 'Малый',
  medium: 'Средний',
  large: 'Крупный',
  strategic: 'Стратегический',
  unknown: 'Неизвестно',
}

// Универсальный helper: вернёт русскую подпись из словаря либо сам ключ (для незнакомых значений).
export function label(dict, key, fallback) {
  if (key == null) return fallback ?? '—'
  return dict[key] ?? (fallback ?? key)
}

export function leadStatusLabel(key) {
  return label(LEAD_STATUS_RU, key)
}
export function messageStatusLabel(key) {
  return label(MESSAGE_STATUS_RU, key)
}
export function companyTypeLabel(key) {
  return label(COMPANY_TYPE_RU, key)
}
export function intentLabel(key) {
  return label(INTENT_RU, key)
}
export function volumeLabel(key) {
  return label(ESTIMATED_VOLUME_RU, key)
}
