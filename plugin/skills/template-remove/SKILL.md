---
name: template-remove
description: "Удалить макет у объекта 1С вместе с его регистрацией в XML объекта. Только по прямой просьбе пользователя"
argument-hint: <ObjectName> <TemplateName>
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# /template-remove — Удаление макета

Удаляет макет и убирает его регистрацию из корневого XML объекта.

## Usage

```
/template-remove <ObjectName> <TemplateName>
```

| Параметр     | Обязательный | По умолчанию | Описание                            |
|--------------|:------------:|--------------|-------------------------------------|
| ObjectName   | да           | —            | Имя объекта                         |
| TemplateName | да           | —            | Имя макета: идентификатор 1С из `ChildObjects` объекта, иначе отказ кодом 1 и ничего не удаляется (правка ядра) |
| SrcDir       | нет          | `src`        | Каталог исходников                  |

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/remove-template.py" -ObjectName "<ObjectName>" -TemplateName "<TemplateName>" [-SrcDir "<SrcDir>"]
```

## Что удаляется

```
<SrcDir>/<ObjectName>/Templates/<TemplateName>.xml     # Метаданные макета
<SrcDir>/<ObjectName>/Templates/<TemplateName>/         # Каталог макета (рекурсивно)
```

## Что модифицируется

- `<SrcDir>/<ObjectName>.xml` — убирается `<Template>` из `ChildObjects`
- Для ExternalReport/Report: если удалённый макет был указан в `MainDataCompositionSchema` — значение очищается
