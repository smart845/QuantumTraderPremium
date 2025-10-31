
# QuantumTrader PRO Hardening

## Что нового
- ✅ FastAPI Dashboard с сессионной авторизацией и rate limit
- ✅ Pydantic Settings с проверкой секретов
- ✅ SQLAlchemy (async) + SQLite по умолчанию
- ✅ Healthcheck `/healthz`
- ✅ Tenacity retry helpers для сетевых вызовов
- ✅ Стандартизованное логирование (structlog)
- ✅ Скрипт миграции JSON -> SQL (`scripts/migrate_json_to_sql.py`)

## Быстрый старт
1. Сгенерируйте bcrypt-хэш пароля администратора:
   ```bash
   python -c "from passlib.hash import bcrypt; print(bcrypt.hash('YourStrongPass'))"
   ```
2. Заполните `.env` на основе `.env.example`.
3. Локальный запуск:
   ```bash
   uvicorn dashboard_secure.secure_app:app --reload
   ```
4. Миграция данных (если ранее использовали JSON):
   ```bash
   python scripts/migrate_json_to_sql.py
   ```
