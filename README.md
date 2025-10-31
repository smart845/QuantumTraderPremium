
# QuantumTrader Premium v2 — Telegram AI Intraday Bot

- **AI/ML** режим по умолчанию (Binance, ccxt)
- Графики в стиле TradingView (свечи + RSI + MACD + Supertrend)
- Trial **3 дня**, затем 5 TON/мес или 40 TON/год
- Авто-активация подписки через **TON**: бот подставляет `UID:{user_id}` в комментарий платежа и активирует подписку, когда увидит транзакцию

## Установка

```bash
pip install -r requirements.txt
cp .env.example .env
# Вставьте TELEGRAM_TOKEN в .env
python run_bot.py
```

## TON авто-подписки

- В боте формируется ссылка:
  - Месяц: `https://tonhub.com/transfer/<TON_ADDRESS>?text=UID:{user_id} Monthly`
  - Год:   `https://tonhub.com/transfer/<TON_ADDRESS>?text=UID:{user_id} Yearly`
- Модуль `core/subscription_checker.py` каждые 10 минут проверяет входящие транзакции и активирует подписку на 30/365 дней.

Запуск чекера:
```bash
python core/subscription_checker.py
```

ENV-переменные (опционально):
```
TON_ADDRESS=UQC3Pro8kBw5LGpD3uxTwrHn6rKP-MMw8sNgFt5IhhDdYZMG
TONCENTER_API=https://toncenter.com/api/v2/getTransactions
TONCENTER_API_KEY=  # если есть
USERS_FILE=data/users.json
TRIAL_DAYS=3
SUBSCRIPTION_CHECK_INTERVAL=600
```

## Вебхуки (опционально)

Смотри инструкцию в предыдущем сообщении — можно развернуть на VPS или на Render.  
Для вебхуков нужен HTTPS-сервер и указать `WEBHOOK_URL` в `.env`.

## Команды

- `/start` — приветствие, меню, статус (Trial/Подписка)
- `/chart` — запрос тикера и график с Entry/SL/TP
- `/train_ai` — обучение ИИ
- `/stop` — остановка потока сигналов
- Либо просто напиши боту тикер: `BTC`, `ETHUSDT`, `SOL`, и т.д.

## Продакшен

- Запуск двух процессов:
  - `python run_bot.py`
  - `python core/subscription_checker.py`
- Рекомендуется `pm2` или `systemd` для авто-ребута.
- Данные пользователей — `data/users.json`, модели — `data/ai_models/`.

> Важно: торговые решения — на ваш риск.


## Реферальная программа (v3)
- Личная ссылка: `https://t.me/<BOT_USERNAME>?start=ref<user_id>`
- Статусы рефералов: `pending` (ожидает оплаты), `paid` (оплачено, ждёт выплаты бонуса), `expired` (>7 дней без оплаты)
- Бонус: **1 TON** за каждую годовую подписку (39 TON) приглашённого
- Ввод TON-адреса рефералом: `/set_ton_address EQC...`
- Просмотр статистики: `/referrals`
- Пометка бонуса как выплаченного: `/mark_paid <referrer_id> <user_id>`


## Docker
```bash
docker build -t quantumtrader .
docker compose up -d
```

## Вебхуки Telegram
Укажи в `.env`:
```
WEBHOOK_URL=https://yourdomain.com/webhook
WEBHOOK_PATH=/webhook
PORT=8080
```
Запуск вебхук-сервера:
```bash
python run_webhook.py
```

## Админ-панель
В `.env` укажи список админов (через запятую):
```
ADMIN_IDS=123456789,987654321
```
Команды:
- `/admin` — краткое меню
- `/grant_month <user_id>` — выдать 30 дней
- `/grant_year <user_id>` — выдать 365 дней
- `/block <user_id>` — заблокировать пользователя
- `/unblock <user_id>` — вернуть триал


## Веб-дашборд (FastAPI)
- Запуск: `python dashboard/app.py`
- Доступ: basic-auth (логин `ADMIN_USER`, пароль `ADMIN_PASSWORD` из .env)
- По умолчанию порт `8090` (настраивается `DASHBOARD_PORT`)
- Команда в Telegram: `/dashboard` — присылает ссылку `BOT_DASHBOARD_URL`

## Deploy на Render/Railway
- Render: используйте `render.yaml` (3 сервиса: bot, ton_checker, dashboard)
- Railway: используйте `railway.json`

## Автовыплаты TON
- В v5 по умолчанию выключены (ручной режим выплат через дашборд)
- Можно включить позже добавлением модуля и секретов, если потребуется


## v6: Улучшения дашборда и уведомления
- Красивый интерфейс (Bootstrap), таблицы со статус-бейджами
- Фильтры и поиск по пользователям и рефералам
- Уведомления админам в Telegram при каждой активации подписки


## v7: TradingView-стиль панель + экспорт/импорт + графики
- Tailwind/Flowbite тёмная тема, разделы: Signals Feed, PnL Stats, AI Insight (данные из `data/trades.json` и `data/signals.json`)
- Plotly-график PnL, автообновление метрик (/api/metrics)
- Экспорт/импорт резервной копии (backup.json)
- Админ-канал (укажи `ADMIN_CHANNEL_ID`), ежедневные отчёты можно включить в `subscription_checker` (cron/pm2)


## GitHub → Deploy
1) Создай репозиторий на GitHub (пустой).  
2) В корне проекта выполни:
```bash
git init
git add .
git commit -m "QuantumTrader Premium v8"
git branch -M main
git remote add origin https://github.com/<yourname>/QuantumTraderPremium.git
git push -u origin main
```
3) Render: *New +* → *Web Service* → *Connect GitHub* → выбери репозиторий.  
   Render сам прочитает `render.yaml` и создаст 3 сервиса: bot, ton_checker, dashboard.

## AI Insight
- Данные читаются из `data/ai_insight.json`
- Панель: `/ai/insight` (меню в навигации)
- Ты можешь обновлять этот файл из бота после предсказаний ИИ.

## Ежедневный отчёт админам
- Запуск: `python core/admin_report.py`
- CRON через ENV: `ADMIN_REPORT_CRON="0 9 * * *"` (по умолчанию 09:00)
- Получатели: `ADMIN_IDS` и/или `ADMIN_CHANNEL_ID` в `.env`


## Deploy on Render (Blueprint)
1) Push проект на GitHub (ветка `main`).
2) Открой https://render.com → New + → Blueprint → выбери свой репозиторий.
3) Render автоматически прочитает `render.yaml` и создаст 3 сервиса:
   - `quantum-dashboard` (FastAPI панель),
   - `quantum-bot` (Telegram‑бот),
   - `ton-checker` (чекер оплат TON).
4) В каждом сервисе во вкладке **Environment** добавь переменные:
   - `TELEGRAM_TOKEN`, `BOT_USERNAME`, `ADMIN_USER`, `ADMIN_PASSWORD`, `ADMIN_IDS`, `TON_ADDRESS`, (опц.) `TONCENTER_API_KEY`.
5) Нажми **Deploy** — всё запустится автоматически.
