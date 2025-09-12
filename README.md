# Kiosk MVP Starter

## Быстрый старт

### 1) Бэкенд (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
bash run.sh  # или: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Откройте:  
- API: http://127.0.0.1:8000/health  
- Мини‑админка (UI‑скелет): http://127.0.0.1:8000/admin

### 2) Клиент киоска (PySide6)
В отдельном терминале:
```bash
cd kiosk_app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Что входит
- Публичные эндпойнты: `/config`, `/home/buttons`, `/pages/{slug}`, `/upload`
- Мок‑данные (в памяти) для кнопок/страниц/темы
- JWT‑логин `/auth/login` (логин: `admin`, пароль: `admin`)
- Мини‑админка на Jinja2 (пока только чтение списка кнопок)

## Дальше по шагам
1. Подключить SQLite + SQLAlchemy + Alembic (модели: users, themes, settings, pages, buttons, assets, blocks).
2. CRUD API для страниц/кнопок/темы + валидация.
3. Полноценная админка: авторизация, формы/drag‑n‑drop, загрузка медиа.
4. WebSocket: пуш обновлений киоску.
5. Кеш/офлайн‑режим клиента и автозапуск в киоск‑режиме.
