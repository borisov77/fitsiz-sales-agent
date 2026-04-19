// Русские подписи для enum-значений, приходящих с backend'а.
// На бэке остаются английские ключи (API стабильный), UI переводит при рендере.

export const LEAD_STATUS_RU = {
  new: 'Новый',
  contacted: 'Первое письмо',
  follow_up_1: 'Напоминание 1',
  follow_up_2: 'Напоминание 2',
  follow_up_3: 'Финальное',
  replied: 'Ответил',
  interested: 'Интерес',
  negotiating: 'Переговоры',
  warm: 'Тёплый',
  transferred: 'Передан',
  rejected: 'Отказ',
  unsubscribed: 'Отписался',
}

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

export const FOLLOW_UP_STAGE_RU = {
  follow_up_1: 'Напоминание 1',
  follow_up_2: 'Напоминание 2',
  follow_up_3: 'Финальное',
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
