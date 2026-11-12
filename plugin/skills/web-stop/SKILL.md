---
name: web-stop
description: "Остановить веб-сервер Apache целиком — все публикации перестают открываться, но остаются настроенными. Используй, когда просят остановить веб-сервер или Apache. Убрать одну публикацию базы — web-unpublish"
argument-hint: ""
allowed-tools:
  - Bash
  - Read
  - Glob
---

# /web-stop — Остановка Apache

Останавливает Apache HTTP Server. Публикации сохраняются — при следующем `/web-publish` сервер запустится снова.

## Usage

```
/web-stop
```

## Параметры подключения

Прочитай `.v8-project.json` из корня проекта. Если задан `webPath` — используй как `-ApachePath`.
По умолчанию `tools/apache24` от корня проекта.

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/web-stop.py" <параметры>
```

Нужен модуль Python `psutil`: без него скрипт сразу завершится с кодом 1 и подсказкой `python -m pip install --user psutil` (правка ядра).

### Параметры скрипта

| Параметр | Обязательный | Описание |
|----------|:------------:|----------|
| `-ApachePath <путь>` | нет | Корень Apache (по умолчанию `tools/apache24`) |

## После выполнения

Предложи пользователю:
- **Перезапуск** — `/web-publish <база>` (повторный вызов поднимет Apache с существующими публикациями)
- **Удаление публикаций** — `/web-unpublish <имя>` или `/web-unpublish --all`

## Примеры

```powershell
# Остановить Apache
python "${CLAUDE_SKILL_DIR}/scripts/web-stop.py"

# С указанием пути
python "${CLAUDE_SKILL_DIR}/scripts/web-stop.py" -ApachePath "C:\tools\apache24"
```
