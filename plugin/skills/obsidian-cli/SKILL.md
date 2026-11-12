---
name: obsidian-cli
description: "Работать с хранилищем Obsidian через его командную строку (нужен запущенный Obsidian) — поиск, бэклинки, задачи, свойства, отладка плагинов Obsidian. Используй, только когда нужно действие самого Obsidian; прочитать или найти заметку достаточно обычным чтением файлов"
---

# Obsidian CLI

Use the `obsidian` CLI to interact with a running Obsidian instance. Requires Obsidian to be open.

## Command reference

Run `obsidian help` to see all available commands. This is always up to date. Full docs: https://help.obsidian.md/cli

## Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian create name="My Note" silent overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

## File targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension needed)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

## Vault targeting

Commands target the most recently focused vault by default. Use `vault=<name>` as the first parameter to target a specific vault:

```bash
obsidian vault="My Vault" search query="test"
```

## Common patterns

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
```

Use `--copy` on any command to copy output to clipboard. Use `silent` to prevent files from opening. Use `total` on list commands to get a count.

## Plugin development

### Develop/test cycle

After making code changes to a plugin or theme, follow this workflow:

1. **Reload** the plugin to pick up changes:
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **Check for errors** — if errors appear, fix and repeat from step 1:
   ```bash
   obsidian dev:errors
   ```
3. **Verify visually** with a screenshot or DOM inspection:
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **Check console output** for warnings or unexpected logs:
   ```bash
   obsidian dev:console level=error
   ```

### Additional developer commands

Run JavaScript in the app context:

```bash
obsidian eval code="app.vault.getFiles().length"
```

Inspect CSS values:

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

Toggle mobile emulation:

```bash
obsidian dev:mobile on
```

Run `obsidian help` to see additional developer commands including CDP and debugger controls.

---

## Запуск в этой среде (наша правка)

Команды `obsidian …` в PATH нет — **CLI поставляется вместе с приложением**. Проверено зондом 03.08.2026:

```bash
"C:/Program Files/Obsidian/Obsidian.com" help
```

`Obsidian.com` — консольная обёртка приложения, она и есть CLI. Полезно завести короткий алиас в сессии:

```bash
alias obsidian='"C:/Program Files/Obsidian/Obsidian.com"'
```

**Требуется запущенный Obsidian.** При закрытом приложении CLI отвечает `The CLI is unable to find Obsidian. Please make sure Obsidian is running and try again.` (и при этом код возврата `0` — по нему успех не определять, смотреть на текст ответа). Приложение **я не запускаю сам** — это `docs/safety/no-screen-control.md`; прошу пользователя открыть Obsidian и продолжаю.

Хранилище проекта — корень его репозитория (`.obsidian/` лежит рядом с `docs/`); имя хранилища в Obsidian — имя этой папки. Если в приложении открыто несколько хранилищ, целиться явно: `vault="<имя папки проекта>"` первым параметром. Команды работают, только пока приложение Obsidian запущено.

**Границы в этом хранилище:** команды на запись (`create`, `append`, `property:set`) не применять к `docs/`, `CLAUDE.md`, `README.md` и `docs/MEMORY.md` — там формат держат гейты мастера ядра (`tools/indexes/gen-doc-index.py`, `health-check`), правки идут обычным путём через Edit/Write; в проекте с плагином `docs/` приходит плагином и не правится, этих гейтов там нет (правка ядра). CLI здесь — для чтения, поиска, бэклинков и работы с личными заметками пользователя.
