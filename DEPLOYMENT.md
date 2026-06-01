# Деплой FITSIZ Sales Agent

## Сервер
- Провайдер: Beget VPS
- IP: 155.212.147.151
- ОС: Ubuntu 24.04
- Конфигурация: 1 vCPU, 2 ГБ RAM, 15 ГБ NVMe
- Домен: https://sales.fitsiz.ru
- Доступ по SSH: root@155.212.147.151 (по SSH-ключу)

## Что развёрнуто и работает
- Backend (uvicorn) — systemd-сервис fitsiz-agent на 127.0.0.1:8000
- Frontend — собран в frontend/dist, раздаётся через Caddy
- Caddy — reverse proxy + автоматический HTTPS (Let's Encrypt) на sales.fitsiz.ru
- Basic Auth на уровне Caddy (логин admin) — браузерное окно перед входом
- Вход в приложение — JWT, таблица users в SQLite
- APScheduler — 3 задачи: проверка почты (600с), отправка очереди (300с), follow-up (1800с)

## Расположение
- Код проекта: /opt/fitsiz-sales-agent
- Виртуальное окружение: /opt/fitsiz-sales-agent/venv
- Конфиг Caddy: /etc/caddy/Caddyfile
- Systemd-юнит: /etc/systemd/system/fitsiz-agent.service
- .env: /opt/fitsiz-sales-agent/.env (НЕ в git)

## Команды управления сервером
- Перезапуск backend: systemctl restart fitsiz-agent
- Логи backend: journalctl -u fitsiz-agent -n 50
- Перезапуск Caddy: systemctl restart caddy
- Статус: systemctl status fitsiz-agent

## Цикл обновления кода
1. Локально (Mac): дорабатываю через Claude Code → git push
2. На сервере: cd /opt/fitsiz-sales-agent && git pull
3. Если менялся backend: systemctl restart fitsiz-agent
4. Если менялся frontend: cd frontend && npm run build (Caddy подхватит автоматически)
5. Создать пользователя для входа: python scripts/create_user.py

## Две защиты на входе
1. Basic Auth (Caddy) — логин admin + пароль (хеш в Caddyfile)
2. Вход в приложение (JWT) — логин/пароль из таблицы users
