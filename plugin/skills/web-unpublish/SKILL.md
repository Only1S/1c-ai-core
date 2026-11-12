---
name: web-unpublish
description: Удаление веб-публикации 1С из Apache. Используй когда пользователь просит убрать публикацию, удалить веб-доступ к базе
argument-hint: "<appname | --all>"
allowed-tools:
  - Bash
  - Read
  - Glob
  - AskUserQuestion
---

# /web-unpublish — Удаление веб-публикации 1С из Apache

Удаляет блок публикации из `httpd.conf` и каталог `publish/{appname}` внутри Apache. Если других публикаций не осталось — удаляет глобальный блок 1C и останавливает Apache. С флагом `--all` удаляет все публикации разом.

> **Внимание:** этот навык управляет только веб-публикациями в Apache (блоки в `httpd.conf` + каталог `publish/`). Он **НЕ** удаляет каталоги проекта, `upload/`, базы данных или исходники.

Имя публикации проверяется **до** удаления: без `..`, разделителей пути и двоеточия, и блок `# --- 1C Publication: <имя> ---` должен быть в `httpd.conf` с тем же регистром (`/web-publish` пишет имя строчными). Иначе — отказ с кодом 1 и подсказкой, `httpd.conf` и каталоги не тронуты; с `--all` так же проверяется каждое имя из `httpd.conf` (правка ядра).

## Usage

```
/web-unpublish <appname>
/web-unpublish bpdemo
/web-unpublish --all
```

## Параметры подключения

Прочитай `.v8-project.json` из корня проекта. Если задан `webPath` — используй как `-ApachePath`.
По умолчанию `tools/apache24` от корня проекта.

Если пользователь не указал `appname` и не указал `--all`, выполни `/web-info` чтобы показать список публикаций и спроси какую удалить.

Если пользователь просит удалить **все** публикации — используй `-All`.

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/web-unpublish.py" <параметры>
```

Нужен модуль Python `psutil`: без него скрипт сразу завершится с кодом 1 и подсказкой `python -m pip install --user psutil` (правка ядра).

### Параметры скрипта

| Параметр | Обязательный | Описание |
|----------|:------------:|----------|
| `-AppName <имя>` | * | Имя публикации |
| `-All` | * | Удалить все публикации |
| `-ApachePath <путь>` | нет | Корень Apache (по умолчанию `tools/apache24`) |

> `*` — нужен либо `-AppName`, либо `-All`

## Примеры

```powershell
# Удалить одну публикацию
python "${CLAUDE_SKILL_DIR}/scripts/web-unpublish.py" -AppName "bpdemo"

# Удалить все публикации
python "${CLAUDE_SKILL_DIR}/scripts/web-unpublish.py" -All

# С указанием пути
python "${CLAUDE_SKILL_DIR}/scripts/web-unpublish.py" -AppName "mydb" -ApachePath "C:\tools\apache24"
```
