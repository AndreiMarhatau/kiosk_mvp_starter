# Kiosk MVP Starter

## Быстрый старт

### Установка зависимостей
```bash
./scripts/install_requirements.sh
```
Скрипт создаст отдельные виртуальные окружения `.venv` для `backend` и `kiosk_app` и установит все зависимости. Можно переопределить интерпретатор через переменную `PYTHON_BIN` (например, `PYTHON_BIN=python3.11 ./scripts/install_requirements.sh`).

### Запуск сервисов по отдельности
- **Бэкенд (FastAPI)**
  ```bash
  ./scripts/run_backend.sh
  ```
  Параметры:
  - `HOST` (по умолчанию `0.0.0.0`)
  - `PORT` (по умолчанию `8000`)
  - `ENABLE_RELOAD=0` отключит авто‑перезапуск.

- **Клиент киоска (PySide6)**
  ```bash
  ./scripts/run_kiosk.sh
  ```
  Можно переопределить интерпретатор переменной `PYTHON_BIN` или точку входа `APP_ENTRY`.

### Совместный запуск
```bash
./scripts/run_all.sh
```
Скрипт поднимет оба приложения параллельно и корректно завершит их по `Ctrl+C`. Убедитесь, что вы используете Bash‑совместимую оболочку (macOS/Linux или Git Bash/WSL на Windows).

После старта доступны:
- API: http://127.0.0.1:8000/health
- Мини‑админка: http://127.0.0.1:8000/admin

### Сборка автономного `.exe`

Для создания Windows‑исполняемого файла, который поднимает бэкенд и клиент одним процессом, используется `PyInstaller` и точка входа `combined_launcher.py`.

Локально (Linux/macOS/Windows):

```bash
pip install -r backend/requirements.txt -r kiosk_app/requirements.txt pyinstaller
python scripts/build_executable.py
```

Готовый файл появится в каталоге `dist/` (`kiosk_app.exe` на Windows). Быстрый тест бэкенда без запуска UI:

```bash
python combined_launcher.py --check-backend
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
