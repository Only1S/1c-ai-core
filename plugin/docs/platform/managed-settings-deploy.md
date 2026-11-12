---
name: managed-settings-deploy
description: Управляемые настройки организации Claude Code (managed-settings.json) — высший уровень, который пользователь не снимает; как собрать из project-deny.json генератором gen-managed-settings.py и куда положить по ОС, чтобы запреты ядра не отключались в проектах и нельзя было подгрузить чужие плагины и моды
metadata:
  type: reference
---

# Управляемые настройки организации (managed-settings.json)

Второй рубеж к запретам ядра (Т-1 волны 3, #3). Обычные запреты ядра живут в `.claude/settings.json` проекта — их владелец проекта может снять. **Управляемые настройки** Claude Code — высший уровень: ни пользовательские, ни проектные, ни локальные настройки, ни `--settings` их не перебивают (code.claude.com/docs/en/settings, «Settings precedence»). Туда кладутся запреты ядра и замок каталога плагинов, чтобы:

- запреты опасных команд (`permissions.deny`) **нельзя было снять** в проекте;
- нельзя было добавить чужой каталог плагинов или подгрузить чужой плагин/мод (они могут переписать решения наших барьеров).

Закрывает две находки замера: «запреты не доходят до проектов» и «чужие моды и плагины не видны».

## Собрать

```
python plugin/tools/setup/gen-managed-settings.py --out managed-settings.json
```

Генератор берёт **единый** список запретов `plugin/tools/setup/project-deny.json` (тот же, что `connect-project` ставит в проект — дубля нет) и добавляет замок каталога плагинов. Состав результата:

| Ключ | Что делает |
|---|---|
| `permissions.deny` | 54 запрета ядра (список `plugin/tools/setup/project-deny.json`), неперебиваемые |
| `strictKnownMarketplaces` | белый список источников каталогов: официальный, канал ядра `Only1S/1c-ai-core`, и `{source:skills-dir}` (без него перестают грузиться skills-directory плагины) |
| `disableSideloadFlags` | запрещает `--plugin-dir`, `--plugin-url`, `--agents`, SDK-плагины, `--mcp-config` (кроме in-process `type:sdk`) и `CLAUDE_CODE_PLUGIN_DIRS` |
| `disableCommandPluginSources` | запрещает плагины с источником `command` (их код исполняется на машине) |

На машине мастера ядра `disableSideloadFlags` не ставится: живые пробы сборки плагина перед выпуском запускают кандидата через `--plugin-dir`, и замок их остановит. Его место — рабочие места проектов.

`allowManagedPermissionRulesOnly` намеренно **не** ставится: он отбросил бы `allow`-правила проекта на читающие инструменты серверов ядра (v8std, bsl-platform, bsl-context, code-index). Если нужен максимальный замок — добавить его и перенести нужные `allow` в управляемые настройки (решение владельца).

## Куда положить (система; ставит владелец, не агент)

| ОС | Путь |
|---|---|
| Windows | `C:\Program Files\ClaudeCode\managed-settings.json` |
| macOS | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| Linux и WSL | `/etc/claude-code/managed-settings.json` |

Для команды (планы Team/Enterprise) настройки можно раздать из консоли claude.ai (server-managed settings) или через MDM — подробности на code.claude.com/docs/en/managed-settings. Раскладка по группам пользователей — отдельными endpoint-настройками.

## Проверить

В Claude Code: `/status` → строка «Setting sources» содержит **«Enterprise managed settings»**. Если нет — файл не подхватился (путь, права, валидность JSON). Отклонённые записи — `claude doctor`.

Регресс генератора — `contour-tests` §53 (JSON валиден; `deny` совпадает с `project-deny.json`; в белом списке канал ядра и `skills-dir`; оба замка-флага стоят).
