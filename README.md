# FITSIZ AI Sales Agent — Архитектура проекта

> v0.2 (апрель 2026): убрали Telegram из проекта. Уведомления о тёплых лидах
> теперь уходят на email менеджеру (`MANAGER_EMAIL` в `.env`).

## 1. Суть проекта

Автономный AI-агент для холодных B2B-продаж сварочных масок FITSIZ. Агент берёт на себя полный цикл: от первого письма до момента, когда клиент говорит "давайте работать". После этого лид передаётся менеджеру.

**Персона агента:** сотрудник отдела продаж FITSIZ (имя настраивается).
**Целевая аудитория:** магазины СИЗ, сварочного оборудования, строительные базы, промышленные дистрибьюторы, оптовые площадки.

---

## 2. Функциональная карта

### 2.1. Что делает агент

| Функция | Описание |
|---------|----------|
| Импорт лидов | Загрузка CSV/XLSX с данными: компания, email, город, специализация, контактное лицо |
| Генерация cold-писем | Персонализированное первое письмо на основе профиля компании |
| Отправка email | SMTP через Mail.ru для бизнеса, с вложениями (прайс, каталог, КП) |
| Чтение входящих | IMAP — проверка ответов каждые 10 минут |
| Ведение диалога | AI анализирует ответ, генерирует релевантный ответ, задаёт вопросы |
| Отправка документов | По запросу или по контексту — прайс-лист, каталог, листовка, КП |
| Follow-up цепочки | Если нет ответа: 3 дня → follow-up 1, 7 дней → follow-up 2, 14 дней → финальное |
| Квалификация | Определение статуса: холодный → заинтересован → обсуждение → тёплый → передан |
| Передача менеджеру | **Уведомление по email на `MANAGER_EMAIL`** со сводкой по лиду и ссылкой на переписку + смена статуса. Менеджер видит всю историю в дашборде. |
| Dashboard | Веб-интерфейс для управления лидами, просмотра переписок, метрик |

### 2.2. Чего агент НЕ делает

- Не отправляет договоры (только менеджер)
- Не обсуждает индивидуальные скидки ниже прайса (только партнёрская программа)
- Не звонит — только email
- Не спамит — максимум 20 новых писем в день, с интервалами
- Не отвечает мгновенно — задержка 15-45 минут (имитация живого человека)
- **Не использует Telegram и другие мессенджеры** — весь сигнал идёт по email

---

## 3. Техстек

### 3.1. Backend

| Компонент | Технология | Почему |
|-----------|-----------|--------|
| Язык | Python 3.11+ | Лучшие библиотеки для email, простой для поддержки |
| Фреймворк | FastAPI | Async, быстрый, API для фронтенда |
| База данных | SQLite (старт) → PostgreSQL (масштаб) | Ноль настройки на старте, миграция через Alembic |
| ORM | SQLAlchemy 2.0 | Стандарт, async-поддержка |
| Очереди задач | APScheduler | Лёгкий планировщик, достаточно для наших объёмов |
| Email (отправка) | smtplib + email.mime | Стандартная библиотека Python — используется и для писем клиентам, и для уведомлений менеджеру |
| Email (чтение) | imapclient | Надёжная IMAP-библиотека |
| AI-мозг | Anthropic API (Claude Sonnet) | Лучшее качество текста для B2B-коммуникаций |
| Уведомления менеджеру | smtplib (reuse email_sender) | Единый канал — email, один путь отправки, одна инфраструктура. Никаких мессенджеров в проекте. |

### 3.2. Frontend (Dashboard)

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | React + Vite |
| UI-библиотека | shadcn/ui + Tailwind CSS |
| HTTP-клиент | fetch / axios |
| Роутинг | React Router |

### 3.3. Инфраструктура

| Компонент | Решение |
|-----------|---------|
| Хостинг | VPS (Timeweb Cloud / Selectel), 1 CPU, 2 GB RAM |
| ОС | Ubuntu 22.04 |
| Процесс-менеджер | systemd (backend как сервис) |
| Reverse proxy | Caddy (автоматический HTTPS) |
| Git | GitHub (приватный репозиторий) |
| CI/CD | GitHub Actions → SSH deploy |

---

## 4. Структура проекта (для GitHub)

```
fitsiz-sales-agent/
├── README.md                    # Этот документ
├── .env.example                 # Шаблон переменных окружения
├── .gitignore
│
├── backend/
│   ├── main.py                  # FastAPI app, точка входа
│   ├── config.py                # Настройки из .env
│   ├── database.py              # SQLAlchemy engine + session
│   │
│   ├── models/                  # SQLAlchemy модели
│   │   ├── lead.py              # Лид (компания, контакт, статус)
│   │   ├── message.py           # Отдельное сообщение (переписка строится по lead_id + email-threading)
│   │   ├── document.py          # Загруженные документы (прайсы, каталоги)
│   │   └── campaign.py          # Кампания (группа лидов + шаблон)
│   │
│   ├── services/
│   │   ├── email_sender.py      # SMTP отправка через Mail.ru — один модуль для писем клиентам И уведомлений менеджеру
│   │   ├── email_reader.py      # IMAP чтение входящих
│   │   ├── email_parser.py      # Парсинг входящих, очистка цитат и подписей
│   │   ├── ai_engine.py         # Anthropic API — генерация писем и ответов
│   │   ├── manager_notifier.py  # Уведомления менеджеру на email при warm-лидах
│   │   ├── antispam.py          # Лимиты отправки, рандомные задержки
│   │   ├── lead_importer.py     # Импорт CSV/XLSX (переиспользуется HTTP и CLI)
│   │   └── scheduler.py         # APScheduler — cron-задачи
│   │
│   ├── api/
│   │   ├── leads.py             # CRUD лидов + импорт CSV
│   │   ├── conversations.py     # Просмотр переписок + AI-черновики + модерация
│   │   ├── email.py             # Тестовая отправка / проверка входящих / квота
│   │   ├── campaigns.py         # Управление кампаниями
│   │   ├── documents.py         # Загрузка документов
│   │   ├── dashboard.py         # Метрики и статистика
│   │   └── settings.py          # Настройки агента
│   │
│   ├── prompts/
│   │   ├── system_prompt.md     # Главный system prompt агента
│   │   ├── cold_email.md        # Шаблон генерации cold-письма
│   │   ├── follow_up.md         # Шаблоны follow-up
│   │   ├── reply_handler.md     # Обработка входящих ответов
│   │   ├── qualifier.md         # Промпт квалификации
│   │   └── manager_notification.md  # Шаблон письма менеджеру о тёплом лиде
│   │
│   ├── knowledge/               # Знания агента о продукте
│   │   ├── product_catalog.md   # Каталог масок (из xlsx)
│   │   ├── pricing.md           # Прайс-лист + партнёрская программа
│   │   ├── competitors.md       # Конкурентный анализ (WELDER, FUBAG)
│   │   ├── faq.md               # Частые вопросы и ответы
│   │   └── objections.md        # Работа с возражениями
│   │
│   └── migrations/              # Alembic миграции
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Главная: метрики, активные лиды
│   │   │   ├── Leads.jsx        # Таблица лидов + импорт
│   │   │   ├── Conversations.jsx  # Список переписок
│   │   │   ├── ConversationDetail.jsx  # Переписка + AI-черновики + модерация
│   │   │   ├── Campaigns.jsx    # Управление кампаниями
│   │   │   └── Settings.jsx     # Настройки агента
│   │   ├── components/
│   │   │   ├── LeadTable.jsx
│   │   │   ├── ConversationView.jsx
│   │   │   ├── EmailPreview.jsx
│   │   │   ├── StatsCard.jsx
│   │   │   └── ImportModal.jsx
│   │   └── lib/
│   │       └── api.js           # API-клиент
│   ├── package.json
│   └── vite.config.js
│
├── documents/                   # Вложения для отправки
│   ├── pricelist_2026.pdf
│   ├── catalog_fitsiz_2026.pdf
│   ├── leaflet_element_classic.pdf
│   ├── leaflet_hd_ultra.pdf
│   └── commercial_offer_template.pdf
│
├── scripts/
│   ├── import_leads.py          # CLI-импорт лидов из CSV
│   ├── setup_db.py              # Инициализация БД
│   ├── test_email_parser.py     # Sanity-тесты парсера цитат
│   └── deploy.sh                # Скрипт деплоя на VPS
│
├── docker-compose.yml           # (опционально, для деплоя)
├── requirements.txt             # Python-зависимости
└── Makefile                     # Команды: make run, make deploy, make test
```

---

## 5. Модель данных

### 5.1. Lead (Лид)

```
id              UUID, PK
company_name    VARCHAR(255)        # "СварМонтаж-Уфа"
contact_name    VARCHAR(255)        # "Иванов Сергей Петрович"
email           VARCHAR(255)        # "zakup@svarmontazh-ufa.ru"
phone           VARCHAR(50)         # опционально
city            VARCHAR(100)        # "Уфа"
region          VARCHAR(100)        # "Республика Башкортостан"
company_type    ENUM                # retailer, distributor, manufacturer, other
specialization  TEXT                # "сварочное оборудование, СИЗ, электроды"
website         VARCHAR(255)        # опционально
source          VARCHAR(100)        # "2gis", "manual", "exhibition"
notes           TEXT                # заметки из research
status          ENUM                # new, contacted, replied, interested, negotiating, warm, transferred, rejected, unsubscribed
campaign_id     FK → Campaign
assigned_to     VARCHAR(100)        # "agent" или "manager_name"
created_at      DATETIME
updated_at      DATETIME
last_contact_at DATETIME
next_action_at  DATETIME            # когда следующий follow-up
```

### 5.2. Статусы лида (воронка)

```
new          → Загружен, ещё не контактировали
contacted    → Отправлено первое письмо
follow_up_1  → Первый follow-up (3 дня)
follow_up_2  → Второй follow-up (7 дней)
follow_up_3  → Финальный follow-up (14 дней)
replied      → Ответил (любой ответ)
interested   → Проявил интерес (запросил прайс, задал вопросы)
negotiating  → Обсуждает условия (объёмы, доставку, сроки)
warm         → Готов к работе ("давайте договор", "готовы заказать") → триггер email-уведомления менеджеру
transferred → Передан менеджеру
rejected     → Отказ ("не интересно", "работаем с другими")
unsubscribed → Попросил не писать
```

### 5.3. Message (Сообщение)

```
id              UUID, PK
lead_id         FK → Lead
direction       ENUM            # outgoing, incoming
subject         VARCHAR(500)
body_text       TEXT            # текст письма
body_html       TEXT            # HTML-версия (опционально)
attachments     JSON            # ["pricelist_2026.pdf", "catalog.pdf"]
email_message_id VARCHAR(255)   # Message-ID заголовок
in_reply_to     VARCHAR(255)    # In-Reply-To заголовок (для цепочек)
status          ENUM            # draft, queued, sent, delivered, read, bounced, received, failed
ai_prompt_used  TEXT            # какой промпт использовался (для отладки)
created_at      DATETIME
sent_at         DATETIME
```

> Отдельной таблицы `Conversation` нет. «Переписка» — это Message, сгруппированные по `lead_id`, порядок восстанавливается по email-заголовкам `in_reply_to` / `references`.

### 5.4. Campaign (Кампания)

```
id              UUID, PK
name            VARCHAR(255)    # "Магазины СИЗ Урал — май 2026"
description     TEXT
template_type   VARCHAR(50)     # "cold_retail", "cold_distributor"
target_products JSON            # ["FSC-С777", "FSC-U810"]
status          ENUM            # draft, active, paused, completed
daily_limit     INT             # максимум писем в день
created_at      DATETIME
```

### 5.5. Document (Документ для отправки)

```
id              UUID, PK
name            VARCHAR(255)    # "Прайс-лист FITSIZ 2026"
file_path       VARCHAR(500)    # "documents/pricelist_2026.pdf"
doc_type        ENUM            # pricelist, catalog, leaflet, commercial_offer, certificate
description     TEXT
file_size       INT
created_at      DATETIME
```

---

## 6. Email-движок

### 6.1. Mail.ru для бизнеса — настройки

```
SMTP: smtp.mail.ru:465 (SSL)
IMAP: imap.mail.ru:993 (SSL)
```

Требования:
- Доменная почта (например, sales@fitsiz.ru)
- Пароль приложения (не основной пароль аккаунта)
- SPF, DKIM, DMARC записи в DNS домена — без них письма пойдут в спам

### 6.2. Антиспам-защита (критично)

| Правило | Значение |
|---------|----------|
| Максимум писем в день | 20 новых cold-писем |
| Интервал между письмами | 3-7 минут (рандом) |
| Задержка ответа на входящие | 15-45 минут (рандом) |
| Разогрев нового ящика | Первая неделя: 5 писем/день, потом +5 каждую неделю |
| Обязательная подпись | Имя, должность, телефон, сайт |
| Обязательный отказ | Ссылка "Отписаться" в каждом письме + List-Unsubscribe заголовок |
| Threading | In-Reply-To + References заголовки — ответы в одной цепочке |
| Персонализация | Каждое письмо уникально (AI генерирует), не шаблон |

### 6.3. Логика обработки входящих

```
1. IMAP проверка каждые 10 минут
2. Новое письмо → парсинг:
   a. Определить лида по email отправителя
   b. Извлечь текст (plain text, очистить от цитат)
   c. Сохранить в БД как incoming message
3. AI-анализ ответа:
   a. Классификация: интерес / вопрос / возражение / отказ / отписка / автоответ
   b. Если автоответ (отпуск, уведомление) → игнор, поставить next_action через 7 дней
   c. Если отписка → статус unsubscribed, больше не писать
   d. Если отказ → статус rejected, больше не писать
   e. Если интерес/вопрос → сгенерировать ответ, приложить нужные документы
   f. Если "давайте работать" / "готовы заказать" → статус warm,
      **отправить email менеджеру на `MANAGER_EMAIL`** со сводкой по лиду,
      последним сообщением клиента и ссылкой на переписку в дашборде
4. Задержка 15-45 минут → отправка ответа клиенту
```

### 6.4. Уведомления менеджеру (email)

Триггер — переход лида в статус `warm` (классификация AI `intent=ready` или
эвристика по переписке).

**Что входит в письмо менеджеру:**
- Компания, контактное лицо, email, телефон, город
- Краткая сводка, что интересовало (по результату `qualifier`: оценка
  интереса, готовность к покупке, прогноз объёма)
- Последнее сообщение клиента (plain text, без цитат)
- Deep-link в дашборд на `https://<host>/conversations/<lead_id>` для
  просмотра всей переписки
- Рекомендация AI по следующему шагу

**Куда уходит:**
- `MANAGER_EMAIL` в `.env` — основной получатель
- `MANAGER_EMAIL_CC` (опционально) — список через запятую для копии
  (например, руководителю отдела продаж)

**Как отправляется:**
- Переиспользуется `services/email_sender.py` — тот же SMTP-канал, что и для
  писем клиентам, но отдельный шаблон (`prompts/manager_notification.md`).
- Никаких мессенджеров, ботов, webhook'ов, внешних интеграций. Один канал —
  SMTP. Одна инфраструктура.

---

## 7. AI-движок (ядро агента)

### 7.1. System Prompt агента (основа)

Агент получает system prompt с такой структурой:

```
РОЛЬ: Ты — [имя], менеджер по работе с партнёрами компании FITSIZ.

КОМПАНИЯ: FITSIZ — российский производитель сварочных масок (г. Казань).
Производство в России, сертификат ТР ТС 019/2011. Офис в Домодедово.

КЛЮЧЕВОЕ ПРЕИМУЩЕСТВО: FITSIZ — единственный бренд сварочных масок в РФ
с собственной цифровой экосистемой. Каждая маска = физический продукт +
бесплатный доступ к FITSIZ.APP (мобильное приложение для сварщиков).

ПРОДУКТОВАЯ ЛИНЕЙКА:
[Полный каталог из xlsx — 21 маска, характеристики, цены]

ПАРТНЁРСКАЯ ПРОГРАММА:
- Партнёр: скидка 30%, вход от 30 000₽
- Дилер: скидка 35%, 3 заказа / 150 000₽ за 6 мес
- Эксклюзив: скидка 40%, 500 000₽ за 6 мес

ФЛАГМАНСКИЕ МОДЕЛИ (продвигай в первую очередь):
1. ELEMENT CLASSIC (FSC-С777) — РРЦ 1 600₽, хамелеон, DIN 9-13,
   окно 93x43 мм. Закрывает нижний ценовой сегмент. Конкурент WELDER Ф6.
2. EXPAN HD ULTRA (FSC-U810) — РРЦ 3 550₽, 4 сенсора, DIN 5-8/9-13,
   окно 110x60 мм, HD COLOR. Конкурент FUBAG IR 9-13N S, но при цене ниже
   характеристики лучше (окно 110x60 vs 95x36, 4 датчика vs 2).

КОНКУРЕНТНОЕ ПОЗИЦИОНИРОВАНИЕ:
- FITSIZ заполняет пустой ценовой сегмент между WELDER (дёшево) и FUBAG (дорого)
- HD ULTRA объективно превосходит FUBAG по размеру окна и количеству сенсоров при меньшей цене
- CLASSIC даёт ценовое давление на WELDER при сопоставимых характеристиках
- Ни один конкурент не предлагает цифровую экосистему (FITSIZ.APP)

ТОНАЛЬНОСТЬ:
- Пиши как живой человек, не как робот
- Короткие предложения лучше длинных
- Без пафоса, без "уникальное предложение", без "рады предложить"
- Конкретные факты и цифры
- Уважительный, деловой, но не формальный тон
- Обращайся по имени, если известно
- Не хвали компанию собеседника без конкретики
- Если не знаешь ответа — скажи "уточню и вернусь с ответом"

ЗАПРЕЩЕНО:
- Обсуждать скидки ниже партнёрской программы
- Обещать сроки доставки без уточнения у менеджера
- Отправлять юнит-экономику или себестоимость
- Называть конкретные объёмы складских остатков
- Давать ложную информацию о характеристиках
- Писать больше 3 абзацев в одном письме
- Использовать эмодзи
```

### 7.2. Промпты по этапам

**Cold email (первое письмо):**
```
Контекст лида:
- Компания: {company_name}
- Город: {city}
- Специализация: {specialization}
- Контактное лицо: {contact_name}
- Заметки: {notes}

Задача: напиши первое короткое письмо (3-5 предложений).
Цель — вызвать интерес, предложить отправить прайс-лист.
Упомяни 1-2 факта, релевантных их специализации.
Не грузи характеристиками — только суть.
Subject должен быть конкретный, без кликбейта.
```

**Reply handler (обработка ответа):**
```
Контекст:
- Вся переписка: {conversation_history}
- Последнее сообщение клиента: {incoming_message}
- Статус лида: {lead_status}
- Какие документы уже отправлены: {sent_documents}

Задача: проанализируй ответ и сгенерируй ответное письмо.
1. Определи намерение: вопрос / интерес / возражение / отказ / готовность к сделке
2. Ответь по существу
3. Если уместно — предложи отправить документ (прайс, каталог, КП)
4. Если клиент готов работать — предложи связать с менеджером
5. Верни JSON: { "intent": "...", "reply_text": "...", "reply_subject": "...",
   "attachments": [...], "new_status": "...", "is_warm": true/false }
```

**Qualifier (квалификация):**
```
На основе переписки определи:
1. Уровень интереса (1-10)
2. Готовность к покупке (1-10)
3. Примерный потенциальный объём (малый/средний/крупный)
4. Рекомендуемый следующий шаг
5. Нужно ли передать менеджеру? (да/нет)
```

**Manager notification (письмо менеджеру о тёплом лиде):**
```
Контекст:
- Профиль лида: {lead_profile}
- Оценка qualifier: {qualifier_result}
- Последнее сообщение клиента: {last_incoming}
- Ссылка на переписку: {dashboard_link}

Задача: собери короткое письмо для менеджера (не клиента!).
Формат — деловой, без AI-стилистики, просто сводка:
  Тема: [warm] Компания, Город — готов обсуждать
  Тело: 4-6 строк — кто, что хотел, что важно знать, ссылка.
Без "уважаемый менеджер" и пр. — это внутренняя коммуникация.
```

---

## 8. Dashboard (UI)

### 8.1. Страницы

**Dashboard (главная)**
- Всего лидов / активных / тёплых / переданных
- Писем отправлено сегодня / на этой неделе
- Процент ответов (response rate)
- Конверсия по этапам воронки
- Лента последних событий (ответил, стал тёплым, отказ)

**Leads (лиды)**
- Таблица: компания, город, статус, последний контакт, следующее действие
- Фильтры по статусу, городу, кампании
- Импорт CSV/XLSX
- Ручное добавление лида
- Массовые действия: запустить кампанию, пауза, передать менеджеру

**Conversations (переписки)**
- Список переписок (как email-клиент)
- Просмотр цепочки сообщений
- Пометка: одобрить черновик AI / отредактировать / отправить вручную
- Статус каждого сообщения (отправлено, доставлено, прочитано)

**Campaigns (кампании)**
- Создание: название, целевые продукты, шаблон, лимит в день
- Привязка лидов к кампании
- Статистика кампании: отправлено, ответили, конверсия

**Settings (настройки)**
- Тестовая отправка SMTP (видимая часть — всё остальное в `.env`)
- Тестовое уведомление менеджеру (кнопка «Отправить тестовый warm-alert на `MANAGER_EMAIL`»)
- Информационный блок: где лежат секреты, зачем не в БД

> Редактирование `.env` через UI не реализовано осознанно: секреты хранятся
> в файле, а не в базе — это снижает риск утечки и упрощает аудит.

### 8.2. Режим модерации (важно на старте)

На первом этапе — агент НЕ отправляет письма автоматически. Вместо этого:

1. AI генерирует черновик
2. Черновик появляется в dashboard со статусом "ожидает одобрения"
3. Ты просматриваешь, правишь если нужно, нажимаешь "Отправить"
4. После того как доверие к агенту выросло — включаешь автоматический режим

Это критично для обучения: ты видишь, как агент пишет, корректируешь, и постепенно понимаешь, когда можно отпустить.

---

## 9. Переменные окружения (.env)

```bash
# Email (почта FITSIZ, от имени которой агент пишет клиентам)
EMAIL_ADDRESS=sales@fitsiz.ru
EMAIL_PASSWORD=app_password_here
SMTP_HOST=smtp.mail.ru
SMTP_PORT=465
IMAP_HOST=imap.mail.ru
IMAP_PORT=993

# AI
ANTHROPIC_API_KEY=sk-ant-xxxxx
AI_MODEL=claude-sonnet-4-20250514

# Уведомления менеджеру (тёплые лиды)
MANAGER_EMAIL=manager@fitsiz.ru
MANAGER_NAME=Имя Менеджера             # опционально — подставляется в system prompt
MANAGER_EMAIL_CC=                       # опционально — CC через запятую

# Персона агента (подставляется в письма и подпись)
AGENT_NAME=Владимир
AGENT_TITLE=Менеджер по работе с партнёрами
AGENT_PHONE=+7 (xxx) xxx-xx-xx
AGENT_SIGNATURE=FITSIZ | fitsiz.ru | fitsiz.app

# Лимиты
MAX_COLD_EMAILS_PER_DAY=20
MIN_DELAY_BETWEEN_EMAILS_SEC=180
MAX_DELAY_BETWEEN_EMAILS_SEC=420
MIN_REPLY_DELAY_SEC=900
MAX_REPLY_DELAY_SEC=2700
INBOX_CHECK_INTERVAL_SEC=600

# Режим
AUTO_SEND=false    # false = модерация, true = автоотправка

# База данных
DATABASE_URL=sqlite:///./data/fitsiz_agent.db

# Публичный host (для ссылок в уведомлениях менеджеру)
PUBLIC_BASE_URL=http://127.0.0.1:5173
```

---

## 10. API эндпоинты

### Leads
```
GET    /api/leads                   # Список лидов (с фильтрами)
POST   /api/leads                   # Создать лида вручную
POST   /api/leads/import            # Импорт CSV/XLSX
GET    /api/leads/{id}              # Детали лида
PATCH  /api/leads/{id}              # Обновить лида
POST   /api/leads/{id}/transfer     # Передать менеджеру (вручную)
DELETE /api/leads/{id}              # Удалить лида
```

### Conversations
```
GET    /api/conversations                          # Список переписок
GET    /api/conversations/{lead_id}                # Переписка с лидом
POST   /api/conversations/{lead_id}/draft-cold     # Сгенерировать cold-письмо
POST   /api/conversations/{lead_id}/draft-reply    # Сгенерировать ответ на последнее входящее
POST   /api/conversations/{lead_id}/draft-followup?stage=follow_up_1  # Follow-up
POST   /api/conversations/{lead_id}/qualify        # Оценка лида
POST   /api/conversations/{lead_id}/transfer       # Передать менеджеру
PATCH  /api/conversations/messages/{id}            # Редактировать черновик
POST   /api/conversations/messages/{id}/approve    # Черновик → queued
POST   /api/conversations/messages/{id}/send       # Отправить сейчас
DELETE /api/conversations/messages/{id}            # Удалить черновик
```

### Campaigns
```
GET    /api/campaigns               # Список кампаний
POST   /api/campaigns               # Создать кампанию
PATCH  /api/campaigns/{id}          # Обновить (пауза, лимиты)
POST   /api/campaigns/{id}/launch   # Запустить кампанию
```

### Dashboard
```
GET    /api/dashboard/stats         # Общая статистика
GET    /api/dashboard/funnel        # Воронка конверсии
GET    /api/dashboard/activity      # Лента событий
```

### Documents
```
GET    /api/documents               # Список документов
POST   /api/documents               # Загрузить документ
DELETE /api/documents/{id}          # Удалить документ
```

### Email / система
```
GET    /api/email/quota             # Сколько писем ушло сегодня / лимит
POST   /api/email/send-test         # Тестовое письмо (ручная проверка SMTP)
POST   /api/email/check-inbox       # Ручной pull IMAP
POST   /api/settings/test-manager-email  # Отправить тестовый warm-alert на MANAGER_EMAIL
```

---

## 11. Стоимость и ресурсы

### Ежемесячные расходы

| Статья | Стоимость |
|--------|-----------|
| VPS (1 CPU, 2 GB RAM) | 500-800 ₽/мес |
| Anthropic API (Claude Sonnet) | ~$5-15/мес (при 50-100 лидах) |
| Mail.ru для бизнеса | бесплатно (с доменом) |
| Домен fitsiz.ru | уже есть |
| GitHub (приватный репо) | бесплатно |
| **Итого** | **~1 500 - 2 500 ₽/мес** |

### Расчёт расхода API

Одно cold-письмо: ~1 000 токенов input (system prompt + контекст) + ~300 output = ~1 300 токенов
Один ответ в диалоге: ~2 000 input (контекст + переписка) + ~500 output = ~2 500 токенов

**Prompt caching** включён — system prompt (~27 KB знаний) кешируется на 5 минут,
что снижает реальный input-cost примерно на 90% при пачках вызовов.

При 100 лидах в месяц, ~3 сообщения на лида в среднем:
- 100 × 1 300 (cold) + 200 × 2 500 (ответы) = 630 000 токенов
- Claude Sonnet: ~$3/M input, ~$15/M output → с учётом кеширования **~$3-5/мес**

---

## 12. Безопасность

| Риск | Решение |
|------|---------|
| Утечка API-ключей | .env файл, .gitignore, никогда не в коде |
| Спам-репутация домена | Лимиты, разогрев, SPF/DKIM/DMARC, List-Unsubscribe |
| AI галлюцинации | Режим модерации, запрет на выдумку характеристик, forced tool_use для JSON |
| Юнит-экономика в письмах | System prompt запрещает, проверка на ключевые слова |
| Персональные данные | 152-ФЗ: кнопка "Отписаться", удаление по запросу |
| Потеря данных | SQLite backup ежедневно, git для кода |
| Перехват уведомлений менеджеру | TLS на SMTP, аккаунт `MANAGER_EMAIL` с 2FA |

---

## 13. Этапы разработки (roadmap)

### Этап 1: Каркас (2-3 дня) — ✅ готово
- [x] GitHub repo + .gitignore + README
- [x] Python-проект: FastAPI + SQLAlchemy + SQLite
- [x] Модели данных (Lead, Message, Campaign, Document)
- [x] Базовые API-эндпоинты (CRUD лидов)
- [x] Импорт CSV

### Этап 2: Email-движок (2-3 дня) — ✅ готово
- [x] SMTP отправка через Mail.ru (с вложениями, threading, List-Unsubscribe)
- [x] IMAP чтение входящих
- [x] Матчинг входящих с лидами
- [x] Парсер цитат (RU/EN), автодетект автоответов
- [x] Антиспам: задержки, лимиты, рандомизация

### Этап 3: AI-мозг (3-4 дня) — ✅ готово
- [x] System prompt агента (полная база знаний FITSIZ — 27 KB)
- [x] Генерация cold-писем
- [x] Обработка входящих ответов (intent + JSON через tool_use)
- [x] Квалификация лидов
- [x] Follow-up цепочки (шаблоны 3/7/14 дней)
- [x] Режим модерации (черновики)
- [x] Prompt caching (ephemeral)

### Этап 4: Dashboard (3-4 дня) — ✅ готово
- [x] React + Vite + Tailwind
- [x] Страница Dashboard (метрики, воронка, квота)
- [x] Страница Leads (таблица + импорт + фильтры)
- [x] Страницы Conversations (список + детальный просмотр + модерация)
- [x] Страница Settings (тест SMTP)

### Этап 5: Автоматизация + уведомления + деплой (2-3 дня) — текущий
- [ ] APScheduler:
  - [ ] IMAP-проверка каждые 10 минут
  - [ ] Отправка queued-писем с антиспам-задержками
  - [ ] Автогенерация follow-up по `next_action_at`
- [ ] **Email-уведомления менеджеру** на `MANAGER_EMAIL` при warm-лиде
  (сводка + ссылка на переписку в дашборде). Telegram — **убран из проекта**.
- [ ] Тестовая кнопка «Отправить warm-alert менеджеру» в Settings
- [ ] Deep-link из письма менеджеру в `/conversations/<id>`
- [ ] Деплой на VPS (systemd + Caddy)
- [ ] GitHub Actions CI/CD

### Этап 6: Обкатка + доработка (ongoing)
- [ ] Тестовая кампания на 10-20 лидов (режим модерации)
- [ ] Корректировка промптов по результатам
- [ ] Переход на автоматический режим
- [ ] Масштабирование

---

## 14. Формат базы лидов (CSV для импорта)

```csv
company_name,contact_name,email,city,region,company_type,specialization,website,source,notes
"СварМонтаж-Уфа","Иванов Сергей","zakup@svarmontazh.ru","Уфа","Башкортостан","retailer","сварочное оборудование, СИЗ","svarmontazh.ru","2gis","3 точки, торгуют FUBAG и ESAB"
"ПромИнструмент","Кузнецова Ольга","info@prominstrument.com","Екатеринбург","Свердловская обл.","distributor","электроинструмент, СИЗ, расходники","prominstrument.com","yandex","крупный дистрибьютор Урал"
```

---

## 15. Как запускать через Claude Code

### Первый запуск

```bash
# 1. Клонировать репозиторий
git clone git@github.com:your-username/fitsiz-sales-agent.git
cd fitsiz-sales-agent

# 2. Backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить EMAIL_*, ANTHROPIC_API_KEY, MANAGER_EMAIL
python -m scripts.setup_db
python -m scripts.import_leads --file scripts/sample_leads.csv   # опционально

# 3. Frontend
cd frontend && npm install && cd ..

# 4. Запуск (в двух терминалах)
./venv/bin/uvicorn backend.main:app --reload --port 8000
npm run dev --prefix frontend
# → http://localhost:5173
```

### Работа с Claude Code по этапам

Для каждого этапа даёшь Claude Code конкретную задачу. Примеры:

```
"Этап 5: реализуй scheduler.py на APScheduler.
 Три джобы:
 1) каждые 10 минут — fetch_new_messages() из email_reader.
 2) каждые 30 минут — процессим queued-письма через email_sender,
    соблюдая задержки 3-7 мин между cold-отправками.
 3) каждые 6 часов — ищем лидов без ответа с next_action_at <= now,
    генерим follow-up через ai_engine, ставим status=draft или queued
    в зависимости от AUTO_SEND.
 Все джобы читают AUTO_SEND из .env: в модерации scheduler создаёт
 только черновики, не отправляет."
```

```
"Этап 5: реализуй services/manager_notifier.py.
 Функция notify_warm_lead(lead, qualifier_result, last_incoming).
 Собирает email по шаблону prompts/manager_notification.md.
 Отправляет через email_sender.send_email на MANAGER_EMAIL с
 опциональным CC из MANAGER_EMAIL_CC.
 Deep-link = {PUBLIC_BASE_URL}/conversations/{lead.id}.
 Вызывается автоматически из reply_handler, когда intent=ready
 или is_warm=true. Дубли предотвращаем: если у лида уже был warm-alert
 в последние 24 часа — не шлём повторный."
```

```
"Этап 5: добавь в API /api/settings/test-manager-email POST-эндпоинт,
 отправляет тестовое warm-alert письмо на MANAGER_EMAIL с фиктивными
 данными лида. В Settings.jsx добавь кнопку 'Отправить тест менеджеру'."
```

---

*Документ подготовлен для использования как ТЗ при разработке через Claude Code.*
*FITSIZ | fitsiz.ru | fitsiz.app*
