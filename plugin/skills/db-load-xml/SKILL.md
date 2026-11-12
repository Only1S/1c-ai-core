---
name: db-load-xml
description: Загрузка конфигурации 1С из XML-файлов. Используй когда нужно загрузить конфигурацию из файлов, XML, исходников, LoadConfigFromFiles
argument-hint: <configDir> [database]
allowed-tools:
  - Bash
  - Read
  - Glob
  - AskUserQuestion
---

# /db-load-xml — Загрузка конфигурации из XML

Загружает конфигурацию в информационную базу из XML-файлов (исходников). Поддерживает полную и частичную загрузку.

## Usage

```
/db-load-xml <configDir> [database]
/db-load-xml src/config dev
/db-load-xml src/config dev -Mode Partial -Files "Catalogs/Номенклатура.xml,Catalogs/Номенклатура/Ext/ObjectModule.bsl"
```

> **Внимание**: полная загрузка **заменяет всю конфигурацию** в базе. Перед выполнением запроси подтверждение у пользователя.

## ⚠️ Когда загрузка необратима

Цикл обязателен, если загрузка **полная** (`-Mode Full` — заменяет всю конфигурацию, как `/db-load-cf`) или идёт с **`-UpdateDB`** (реструктуризация базы — тот же необратимый шаг, что `/db-update`). Частичная загрузка без `-UpdateDB` меняет только основную конфигурацию и откатывается повторной загрузкой — для неё обязателен лишь шаг 2. **Исключение — `Configuration.xml` в списке файлов:** платформа тогда грузит конфигурацию полностью, и цикл обязателен целиком, с бэкапом (правка ядра).

1. **Бэкап — точка отката.** `/db-dump-cf` (конфигурация), а при `-UpdateDB` — `/db-dump-dt` (данные тоже). Бэкапа нет → операция не начинается.
2. **Проверка целевой базы.** База разрешается по `.v8-project.json` и **называется пользователю явно**. **Целевая база обязана быть зарегистрирована в `.v8-project.json`; незарегистрированная считается боевой (`docs/safety/secrets-and-production-database.md`) — не трогать**, даже если параметры подключения переданы явно.
3. **Сухой прогон.** Показать: база, каталог, режим (`Full`/`Partial` и список файлов), будет ли `-UpdateDB` и что сносится в структуре, где лежит бэкап.
4. **Явное подтверждение** окном вариантов (AskUserQuestion), «применить / отменить». Общее «продолжай» подтверждением не считается (`docs/process/ask-before-changing.md`, `docs/process/questions-as-options.md`).
5. **Применение** — только после подтверждения.
6. **Проверка** — полный сет чекеров (`docs/tools/full-checker-set-before-done.md`).
7. **Откат** — `/db-load-cf <бэкап.cf>` + `/db-update`, при потере данных — `/db-load-dt <бэкап.dt>`.

## Параметры подключения

Прочитай `.v8-project.json` из корня проекта. Возьми `v8path` (путь к платформе) и разреши базу:
1. Если пользователь указал параметры подключения (путь, сервер) — используй их, **только если такая база есть в `.v8-project.json`** (правка ядра: незарегистрированная база считается боевой, `docs/safety/secrets-and-production-database.md`; барьер `guard-destructive` такой вызов отклонит)
2. Если указал базу по имени — ищи по id / alias / name в `.v8-project.json`
3. Если не указал — сопоставь текущую ветку Git с `databases[].branches`
4. Если ветка не совпала — используй `default`
Если `v8path` не задан — спроси пользователя, какую платформу брать, и впиши её в `v8path` в `.v8-project.json` (правка ядра: без `-V8Path` скрипт взял бы новейшую установленную платформу — она может быть другой линейки, например 8.5, и сконвертировать базу; барьер `guard-destructive` такой запуск отклоняет).
Если файла нет — предложи `/db-list add`.
Если база не зарегистрирована — операция **не выполняется**: сперва пользователь решает, регистрировать ли её как тестовую (`/db-list add`) (правка ядра).
Если в записи базы указан `configSrc` — используй как каталог загрузки по умолчанию.
Для `-Extension` каталог берётся из `extensions[].src` записи базы, если он там указан.

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/db-load-xml.py" <параметры>
```

### Параметры скрипта

| Параметр | Обязательный | Описание |
|----------|:------------:|----------|
| `-V8Path <путь>` | нет | Каталог bin платформы, или полный путь к `1cv8.exe` / `ibcmd.exe` |
| `-InfoBasePath <путь>` | * | Файловая база |
| `-InfoBaseServer <сервер>` | * | Сервер 1С (для серверной базы) |
| `-InfoBaseRef <имя>` | * | Имя базы на сервере |
| `-UserName <имя>` | нет | Имя пользователя |
| `-Password <пароль>` | нет | Пароль |
| `-ConfigDir <путь>` | да | Каталог XML-исходников |
| `-Mode <режим>` | нет | `Full` (по умолч.) / `Partial` |
| `-Files <список>` | для Partial | Относительные пути файлов через запятую |
| `-ListFile <путь>` | для Partial | Путь к файлу со списком (альтернатива `-Files`) |
| `-Extension <имя>` | нет | Загрузить в расширение |
| `-AllExtensions` | нет | Загрузить все расширения (только полностью; частями — по одному через `-Extension`) |
| `-NoApplyCheck` | нет | Не проверять применимость расширения после загрузки |
| `-Format <формат>` | нет | `Hierarchical` (по умолч.) / `Plain` |
| `-UpdateDB` | нет | После загрузки сразу обновить конфигурацию БД (`/UpdateDBCfg`) |
| `-AdditionalV8Arguments <список>` | нет | Доп. аргументы запуска `1cv8.exe` через запятую, напр. `/UseHwLicenses+` |
| `-AdditionalIbcmdArguments <список>` | нет | Доп. аргументы `ibcmd` через запятую, в форме `--ключ=значение` |

> `*` — нужен либо `-InfoBasePath`, либо пара `-InfoBaseServer` + `-InfoBaseRef`

### Режимы загрузки

| Режим | Описание |
|-------|----------|
| `Full` | Полная загрузка — замена всей конфигурации из каталога XML |
| `Partial` | Частичная — загрузка выбранных файлов (с `-partial -updateConfigDumpInfo`) |

> Если в список файлов включить `Configuration.xml`, платформа выполнит **полную загрузку конфигурации**, а не только перечисленных объектов.

### Формат файла списка (listFile)

Файл содержит **относительные пути к файлам** в каталоге выгрузки (один на строку), кодировка **UTF-8 с BOM**:

```
Catalogs/Номенклатура.xml
Catalogs/Номенклатура/Ext/ObjectModule.bsl
Documents/Заказ.xml
Documents/Заказ/Forms/ФормаДокумента.xml
```

## После выполнения

Если `-UpdateDB` не был указан — **предложи выполнить `/db-update`** для применения изменений к БД

## Примеры

```powershell
# Полная загрузка
python "${CLAUDE_SKILL_DIR}/scripts/db-load-xml.py" -V8Path "C:\Program Files\1cv8\8.3.25.1257\bin" -InfoBasePath "C:\Bases\MyDB" -UserName "Admin" -ConfigDir "C:\WS\cfsrc" -Mode Full

# Частичная загрузка конкретных файлов
python "${CLAUDE_SKILL_DIR}/scripts/db-load-xml.py" -InfoBasePath "C:\Bases\MyDB" -UserName "Admin" -ConfigDir "C:\WS\cfsrc" -Mode Partial -Files "Catalogs/Номенклатура.xml,Catalogs/Номенклатура/Ext/ObjectModule.bsl"

# Загрузка расширения
python "${CLAUDE_SKILL_DIR}/scripts/db-load-xml.py" -InfoBasePath "C:\Bases\MyDB" -UserName "Admin" -ConfigDir "C:\WS\ext_src" -Mode Full -Extension "МоёРасширение"

# Загрузка + обновление БД в одном запуске
python "${CLAUDE_SKILL_DIR}/scripts/db-load-xml.py" -InfoBasePath "C:\Bases\MyDB" -UserName "Admin" -ConfigDir "C:\WS\cfsrc" -Mode Full -UpdateDB
```
