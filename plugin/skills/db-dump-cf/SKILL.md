---
name: db-dump-cf
description: "Выгрузить конфигурацию базы 1С в файл CF — копия только конфигурации, без данных. Используй, когда просят выгрузить конфигурацию в CF или сохранить копию конфигурации перед загрузкой. Копия всей базы с данными — db-dump-dt, выгрузка в XML-исходники — db-dump-xml"
argument-hint: "[database] [output.cf]"
allowed-tools:
  - Bash
  - Read
  - Glob
  - AskUserQuestion
---

# /db-dump-cf — Выгрузка конфигурации в CF-файл

Выгружает конфигурацию информационной базы в бинарный CF-файл.

## Usage

```
/db-dump-cf [database] [output.cf]
/db-dump-cf dev config.cf
/db-dump-cf                          — база по умолчанию, файл config.cf
```

## Параметры подключения

Прочитай `.v8-project.json` из корня проекта и разреши базу:
1. Если пользователь указал параметры подключения (путь, сервер) — используй их, **только если такая база есть в `.v8-project.json`** (правка ядра: незарегистрированная база считается боевой, `docs/safety/secrets-and-production-database.md`; барьер `guard-destructive` такой вызов отклонит)
2. Если указал базу по имени — ищи по id / alias / name в `.v8-project.json`
3. Если не указал — сопоставь текущую ветку Git с `databases[].branches`
4. Если ветка не совпала — используй `default`
Платформа — `v8path` найденной записи базы, иначе корневой `v8path`. Не задан ни там, ни там — спроси пользователя, какую платформу брать, и впиши её в `v8path` в `.v8-project.json` (правка ядра: без `-V8Path` скрипт взял бы новейшую установленную платформу — она может быть другой линейки, например 8.5, и сконвертировать базу; барьер `guard-destructive` такой запуск отклоняет).
Если файла нет — предложи `/db-list add`.
Если база не зарегистрирована — операция **не выполняется**: сперва пользователь решает, регистрировать ли её как тестовую (`/db-list add`) (правка ядра).

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/db-dump-cf.py" <параметры>
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
| `-OutputFile <путь>` | да | Путь к выходному CF-файлу |
| `-Extension <имя>` | нет | Выгрузить расширение |
| `-AllExtensions` | нет | Выгрузить все расширения |
| `-AdditionalV8Arguments <список>` | нет | Доп. аргументы запуска `1cv8.exe` через запятую, напр. `/UseHwLicenses+` |
| `-AdditionalIbcmdArguments <список>` | нет | Доп. аргументы `ibcmd` через запятую, в форме `--ключ=значение` |

> `*` — нужен либо `-InfoBasePath`, либо пара `-InfoBaseServer` + `-InfoBaseRef`

## Примеры

```powershell
# Выгрузка конфигурации (файловая база)
python "${CLAUDE_SKILL_DIR}/scripts/db-dump-cf.py" -InfoBasePath "C:\Bases\MyDB" -UserName "Admin" -OutputFile "C:\backup\config.cf"

# Серверная база
python "${CLAUDE_SKILL_DIR}/scripts/db-dump-cf.py" -InfoBaseServer "srv01" -InfoBaseRef "MyApp_Dev" -UserName "Admin" -Password "secret" -OutputFile "config.cf"

# Выгрузка расширения
python "${CLAUDE_SKILL_DIR}/scripts/db-dump-cf.py" -InfoBasePath "C:\Bases\MyDB" -UserName "Admin" -OutputFile "ext.cfe" -Extension "МоёРасширение"
```
