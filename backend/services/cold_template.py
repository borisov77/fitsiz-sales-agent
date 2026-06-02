"""Шаблон ПЕРВОГО письма (cold). Не генерируется AI — задаётся в Settings.

Первое касание — жёсткий шаблон с подстановкой переменных лида. AI отвечает
на входящие, делает follow-up и квалификацию, но первое письмо не трогает.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from backend.models.lead import Lead
from backend.services.app_settings import _get, _set

KEY_SUBJECT = "cold_tpl_subject"
KEY_BODY = "cold_tpl_body"
KEY_SIGNATURE = "cold_tpl_signature"

# Разумный дефолт — без номера сертификата, прицел на ЛПР, упоминание вложений.
DEFAULT_SUBJECT = "Сварочные маски FITSIZ — для вашего ассортимента"

DEFAULT_BODY = (
    "Здравствуйте, {contact_name}!\n\n"
    "Меня зовут Владимир, компания FITSIZ — российский производитель сварочных "
    "масок (Казань). Вижу, что {company_name} работает в нашей нише, поэтому "
    "коротко и по делу.\n\n"
    "Наши маски дают партнёру 35–45% маржи при продаже по РРЦ, а каждая идёт с "
    "бесплатным приложением FITSIZ.APP для сварщиков — такого нет ни у одного "
    "другого бренда в РФ. Для покупателя это повод выбрать вашу полку, для вас — "
    "отстройка от соседних магазинов.\n\n"
    "Прайс-лист и презентацию приложил к письму. Если интересно — ответьте, и я "
    "подберу ассортимент под вашу аудиторию."
)

DEFAULT_SIGNATURE = (
    "С уважением,\n"
    "Владимир\n"
    "Менеджер по работе с партнёрами, FITSIZ\n"
    "fitsiz.ru | fitsiz.app"
)

# Маркер источника письма — по нему email-движок не добавляет свою подпись
COLD_TEMPLATE_MARKER = "cold_template"

# --- Шаблон НАПОМИНАНИЯ (Зона 1: одно письмо через 1 день тишины) ---
KEY_REMINDER_SUBJECT = "reminder_tpl_subject"
KEY_REMINDER_BODY = "reminder_tpl_body"

# Дефолт напоминания. Закрытие «С уважением, Владимир» НЕ включаем —
# его даёт общая подпись cold_tpl_signature (иначе задвоится). Тон: мягкое
# «поднимаю наверх» + сразу просьба о контакте ЛПР по закупкам.
DEFAULT_REMINDER_SUBJECT = "Re: Сварочные маски напрямую с производства - ищем партнёров"

DEFAULT_REMINDER_BODY = (
    "Добрый день!\n\n"
    "Ранее отправлял информацию о сварочных масках FITSIZ и условиях "
    "партнёрства — на случай, если письмо затерялось, поднимаю его наверх.\n\n"
    "Если вопрос поставок сейчас неактуален — подскажите, пожалуйста, к кому в "
    "компании можно обратиться по закупкам. Буду признателен за короткий ответ."
)

# Маркер источника напоминания — email-движок не добавляет свою авто-подпись
COLD_REMINDER_MARKER = "cold_reminder"


class ColdTemplateError(RuntimeError):
    """Шаблон первого письма не заполнен."""


# ==========================
# Чтение / запись шаблона
# ==========================
def get_template(db: Session) -> dict[str, str]:
    subj = _get(db, KEY_SUBJECT)
    body = _get(db, KEY_BODY)
    sign = _get(db, KEY_SIGNATURE)
    return {
        "subject": DEFAULT_SUBJECT if subj is None else subj,
        "body": DEFAULT_BODY if body is None else body,
        "signature": DEFAULT_SIGNATURE if sign is None else sign,
    }


def set_template(db: Session, subject: str, body: str, signature: str) -> dict[str, str]:
    _set(db, KEY_SUBJECT, subject)
    _set(db, KEY_BODY, body)
    _set(db, KEY_SIGNATURE, signature)
    return get_template(db)


def is_filled(db: Session) -> bool:
    tpl = get_template(db)
    return bool(tpl["subject"].strip() and tpl["body"].strip())


# ==========================
# Шаблон напоминания (Зона 1)
# ==========================
def get_reminder_template(db: Session) -> dict[str, str]:
    """Шаблон напоминания. Подпись — общая с первым письмом (cold_tpl_signature)."""
    subj = _get(db, KEY_REMINDER_SUBJECT)
    body = _get(db, KEY_REMINDER_BODY)
    sign = _get(db, KEY_SIGNATURE)
    return {
        "subject": DEFAULT_REMINDER_SUBJECT if subj is None else subj,
        "body": DEFAULT_REMINDER_BODY if body is None else body,
        "signature": DEFAULT_SIGNATURE if sign is None else sign,
    }


def set_reminder_template(db: Session, subject: str, body: str) -> dict[str, str]:
    _set(db, KEY_REMINDER_SUBJECT, subject)
    _set(db, KEY_REMINDER_BODY, body)
    return get_reminder_template(db)


def is_reminder_filled(db: Session) -> bool:
    tpl = get_reminder_template(db)
    return bool(tpl["subject"].strip() and tpl["body"].strip())


# ==========================
# Подстановка переменных
# ==========================
def fill_placeholders(text: str, lead: Lead) -> str:
    company = (lead.company_name or "").strip()
    contact = (lead.contact_name or "").strip()
    text = text.replace("{company_name}", company)
    if contact:
        text = text.replace("{contact_name}", contact)
    else:
        # Имя неизвестно — убираем обращение вместе с предшествующей запятой/пробелом
        text = re.sub(r"\s*,?\s*\{contact_name\}", "", text)
    return text


# ==========================
# Сборка письма для лида
# ==========================
def build_first_email(db: Session, lead: Lead) -> tuple[str, str, list[str]]:
    """Возвращает (subject, body+подпись, attachments). Бросает, если шаблон пуст."""
    if not is_filled(db):
        raise ColdTemplateError(
            "Заполните шаблон первого письма в Настройках"
        )
    tpl = get_template(db)
    subject = fill_placeholders(tpl["subject"], lead).strip()
    body = fill_placeholders(tpl["body"], lead).rstrip()
    signature = fill_placeholders(tpl["signature"], lead).strip()
    if signature:
        body = f"{body}\n\n{signature}"

    from backend.services.document_store import available_attachments

    attachments = sorted(available_attachments())  # прайс + презентация, что есть
    return subject, body, attachments


def build_reminder_email(db: Session, lead: Lead) -> tuple[str, str]:
    """Возвращает (subject, body+подпись) для письма-напоминания.

    Без вложений — это лёгкий «поднимаю наверх» nudge, файлы уже уходили
    с первым письмом. Бросает ColdTemplateError, если шаблон не заполнен.
    """
    if not is_reminder_filled(db):
        raise ColdTemplateError("Заполните шаблон напоминания в Настройках")
    tpl = get_reminder_template(db)
    subject = fill_placeholders(tpl["subject"], lead).strip()
    body = fill_placeholders(tpl["body"], lead).rstrip()
    signature = fill_placeholders(tpl["signature"], lead).strip()
    if signature:
        body = f"{body}\n\n{signature}"
    return subject, body
