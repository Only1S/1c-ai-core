---
name: meta-remove
description: "Удалить объект метаданных из конфигурации 1С с проверкой ссылок на него — необратимо, только по прямой просьбе пользователя; скрипт запускает сам пользователь. Для удаления не использовать cf-edit remove-childObject — он снимает только регистрацию и ссылки не проверяет"
argument-hint: <ConfigDir> -Object <Type.Name>
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Glob
  - AskUserQuestion
---

# /meta-remove — удаление объекта метаданных

Безопасно удаляет объект из XML-выгрузки конфигурации. Перед удалением проверяет ссылки на объект в реквизитах, коде и других метаданных. Если ссылки найдены — удаление блокируется.

## Кто запускает (правка этого ядра)

Удаление необратимо, поэтому защита ядра не даёт модели запускать скрипт — даже с `-DryRun`. Скилл готовит команду: проверяет объект через `meta-info`, подставляет пути и ключи и показывает владельцу сначала команду с `-DryRun`, затем без него. Выполняет владелец сам, в своём терминале; после — `cf-validate` и полный набор проверок.

## Использование

```
/meta-remove <ConfigDir> -Object <Type.Name>
```

## Параметры

| Параметр   | Обязательный | Описание                                        |
|------------|:------------:|-------------------------------------------------|
| ConfigDir  | да           | Корневая директория выгрузки (где Configuration.xml) |
| Object     | да           | Тип и имя объекта: `Catalog.Товары`, `Document.Заказ` и т.д. Таблица внешнего источника — четырьмя частями: `ExternalDataSource.PG.Table.products` |
| DryRun     | нет          | Только показать что будет удалено, без изменений |
| KeepFiles  | нет          | Не удалять файлы, только дерегистрировать       |
| Force      | нет          | Удалить несмотря на найденные ссылки; ссылки на формы объекта при этом очищаются |

## Команда

```powershell
python "${CLAUDE_SKILL_DIR}/scripts/meta-remove.py" -ConfigDir "<путь>" -Object "Catalog.Товары"
```

## Поддерживаемые типы

Catalog, Document, Enum, Constant, InformationRegister, AccumulationRegister, AccountingRegister, CalculationRegister, ChartOfAccounts, ChartOfCharacteristicTypes, ChartOfCalculationTypes, BusinessProcess, Task, ExchangePlan, DocumentJournal, Report, DataProcessor, CommonModule, ScheduledJob, EventSubscription, HTTPService, WebService, DefinedType, Role, Subsystem, CommonForm, CommonTemplate, CommonPicture, CommonAttribute, SessionParameter, FunctionalOption, FunctionalOptionsParameter, Sequence, FilterCriterion, SettingsStorage, XDTOPackage, WSReference, StyleItem, Language

## Примеры

```powershell
# Проверка ссылок + dry run
... -ConfigDir C:\WS\tasks\cfsrc\acc_8.3.24 -Object "Catalog.Устаревший" -DryRun

# Удалить объект без ссылок
... -ConfigDir C:\WS\tasks\cfsrc\acc_8.3.24 -Object "Catalog.Устаревший"

# Принудительно удалить несмотря на ссылки
... -ConfigDir C:\WS\tasks\cfsrc\acc_8.3.24 -Object "Catalog.Устаревший" -Force

# Только дерегистрировать (файлы оставить)
... -ConfigDir C:\WS\tasks\cfsrc\acc_8.3.24 -Object "Report.Старый" -KeepFiles

# Удалить общий модуль
... -ConfigDir src -Object "CommonModule.МойМодуль"
```

