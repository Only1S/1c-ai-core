---
name: template-add
description: "Завести у объекта 1С новый пустой макет и зарегистрировать его в XML объекта — первый шаг для печатной формы или схемы компоновки. Содержимое потом собирают mxl-compile (табличный документ) или skd-compile (СКД)"
argument-hint: <ObjectName> <TemplateName> <TemplateType>
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# /template-add — Добавление макета

Создаёт макет указанного типа и регистрирует его в корневом XML объекта.

## Usage

```
/template-add <ObjectName> <TemplateName> <TemplateType>
```

| Параметр      | Обязательный | По умолчанию    | Описание                                         |
|---------------|:------------:|-----------------|--------------------------------------------------|
| ObjectName    | да           | —               | Имя объекта                                      |
| TemplateName  | да           | —               | Имя макета: идентификатор 1С, иначе отказ кодом 1 (правка ядра) |
| TemplateType  | да           | —               | Тип: HTML, Text, SpreadsheetDocument, BinaryData, DataCompositionSchema |
| Synonym       | нет          | = TemplateName  | Синоним макета                                   |
| Lang          | нет          | `ru`            | Код языка страницы — только для типа HTML. Повторный вызов с другим языком добавляет страницу в существующий макет |
| SrcDir        | нет          | `src`           | Путь к папке типа объектов (`Reports`, `DataProcessors`, `Catalogs`, `Documents`...), внутри которой лежит `<ObjectName>.xml`. Дефолт `src` подходит для каталогов с внешними обработками/отчётами, лежащими рядом |
| -SetMainSKD   | нет          | —               | Принудительно установить MainDataCompositionSchema |

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/add-template.py" -ObjectName "<ObjectName>" -TemplateName "<TemplateName>" -TemplateType "<TemplateType>" [-Synonym "<Synonym>"] [-Lang "<Lang>"] [-SrcDir "<SrcDir>"] [-SetMainSKD]
```

## Пример

Добавить основную СКД к отчёту в расширении:

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/add-template.py" -ObjectName "ОтчётПродажи" -TemplateName "ОсновнаяСхемаКомпоновкиДанных" -TemplateType "DataCompositionSchema" -SrcDir "src/cfe/МоёРасширение/Reports"
```

## Маппинг типов

Пользователь может указать тип в свободной форме. Определи нужный по контексту:

| Пользователь пишет                          | TemplateType        | Расширение | Содержимое              |
|---------------------------------------------|---------------------|------------|-------------------------|
| HTML                                        | HTML                | `Template/<lang>.html` | Пустой HTML-документ <!-- dev_core checkup-1017 --> |
| Text, текстовый документ, текст             | Text                | `.txt`     | Пустой файл <!-- dev_core checkup-1017 --> |
| SpreadsheetDocument, табличный документ, MXL | SpreadsheetDocument | `.xml`     | Минимальный spreadsheet |
| BinaryData, двоичные данные                 | BinaryData          | `.bin`     | Пустой файл             |
| DataCompositionSchema, СКД, схема компоновки | DataCompositionSchema | `.xml`   | Минимальная DCS-схема   |

## Конвенция именования

Для макетов **печатных форм** (тип SpreadsheetDocument) применяй префикс `ПФ_MXL_`:

| Контекст                                                         | Формат имени               | Пример                  |
|------------------------------------------------------------------|----------------------------|-------------------------|
| Печатная форма (дополнительная обработка вида ПечатнаяФорма, или пользователь явно говорит «печатная форма») | `ПФ_MXL_<КраткоеИмя>`     | `ПФ_MXL_М11`, `ПФ_MXL_СчётФактура`, `ПФ_MXL_КонвертDL` |
| Прочие макеты (загрузка данных, служебные, настройки)            | Без префикса               | `МакетЗагрузки`, `НастройкиПечати` |

Если пользователь указал имя макета без префикса, но контекст — печатная форма, **добавь префикс `ПФ_MXL_` автоматически** и сообщи об этом.

## MainDataCompositionSchema (авто)

При добавлении макета типа `DataCompositionSchema` к `ExternalReport` или `Report`:
- Если `MainDataCompositionSchema` пуст — автоматически заполняется ссылкой на макет
- Используй `-SetMainSKD` чтобы перезаписать существующее значение <!-- dev_core checkup-1017 -->

## Что создаётся

```
<SrcDir>/<ObjectName>/Templates/
├── <TemplateName>.xml              # Метаданные макета (1 UUID)
└── <TemplateName>/
    └── Ext/
        ├── Template.<ext>          # Содержимое макета
        └── Template/<lang>.html    # HTML: содержимое (Template.xml — дескриптор)
```

## Что модифицируется

- `<SrcDir>/<ObjectName>.xml` — добавляется `<Template>` в `ChildObjects`
- Для ExternalReport/Report: может обновляться `MainDataCompositionSchema`
