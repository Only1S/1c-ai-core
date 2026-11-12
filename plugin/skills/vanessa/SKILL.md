---
name: vanessa
description: "Сгенерировать и проверить сценарий Vanessa Automation (BDD для 1С, Gherkin/.feature) по библиотеке готовых шагов va-ai (1569 шагов). Используй, когда нужно проверить поведение собранной доработки в КЛИЕНТЕ 1С сценарием (UI-приёмка, не замена YAXUnit), сгенерировать или починить .feature, перед прогоном через vanessa-runner. Правило: шаги — ТОЛЬКО из библиотеки, после генерации обязателен валидатор scripts/validate.py. Сам прогон сценария на тестовой базе — харнесс run-scenario, не этот скилл"
---

# Vanessa Automation: генерация и проверка .feature по библиотеке шагов

Слой генерации и проверки UI-сценариев (BDD) для 1С на базе [va-ai](https://github.com/Nikolay-Shirokov/va-ai) (MIT, автор тот же, что у `cc-1c-skills`). Этот скилл — **знание + валидатор**; сам прогон сценария в клиенте 1С делает харнесс `plugin/tools/vanessa/run-scenario.py` (vanessa-runner + vanessa-automation.epf на тестовой базе).

Роутер ASCII-only — безопасен при устаревшей кодовой странице консоли Windows. Файлы знания — UTF-8.

## Reading UTF-8 files on Windows

Read with explicit UTF-8, не через PowerShell-конвейеры (они перекодируют stdout):

```bash
python -X utf8 -c "import sys; from pathlib import Path; sys.stdout.reconfigure(encoding='utf-8'); print(Path(sys.argv[1]).read_text(encoding='utf-8'))" "PATH"
```

## What is here

- `ai-knowledge/guide.md` — руководство по синтаксису Gherkin/Turbo Gherkin и шагам.
- `ai-knowledge/templates.md` — шаблоны типовых сценариев (справочники, документы, отчёты).
- `ai-knowledge/steps-library.json` — библиотека из 1569 шагов по разделам (`UI`, `Служебные`, `Прочее`, …); у шага поля `шаг` — текст шага, `описание`, `тип` — категория (`UI.Формы.Ввод на основании`).
- `ai-knowledge/semantic-validation-guide.md` — как валидатор сопоставляет шаги семантически.
- `scripts/validate.py` (+ `step_parser.py`, `semantic_matcher.py`, `metrics_logger.py`, наш разбор `gherkin_walk.py`) — валидатор сценария, чистый Python stdlib, без внешних зависимостей и без сети.

## Как генерировать сценарий

1. Разобрать, что проверяем в КЛИЕНТЕ (навигация, открытие формы, ввод, проверка значения/сообщения).
2. Открыть `ai-knowledge/guide.md` и `templates.md`; подобрать шаги **только** из `steps-library.json` (поиск по полю `шаг`, раздел — по полю `тип`).
3. Собрать `.feature` на русском Gherkin: первые строки — `# encoding: utf-8` и `# language: ru` (без них валидатор красный), двойные кавычки `"..."`, параметры в кавычках.
4. **Не придумывать шаги.** Нет подходящего шага — искать близкий в библиотеке (валидатор подскажет), а не писать свой.

## Обязательная проверка (парный валидатор)

Сгенерировал/поменял `.feature` — сразу прогони валидатор (как `*-validate` у остальных скиллов ядра):

```bash
PYTHONIOENCODING=utf-8 python "${CLAUDE_SKILL_DIR}/scripts/validate.py" "<путь к .feature>" \
  --library "${CLAUDE_SKILL_DIR}/ai-knowledge/steps-library.json" --ai-format
```

- Код возврата `0` — все шаги в библиотеке, синтаксис цел; `1` — есть шаг не из библиотеки или ошибка синтаксиса (в отчёте — строка, шаг, подсказки). Пока валидатор красный — в клиент сценарий не гоним: харнесс прогона сам запускает валидатор и на красном отказывает.
- Проверяется шаг на любом ключевом слове русского Gherkin, в том числе в `Контекст:`/`Предыстория:`, `Структура сценария:`/`Шаблон сценария:`. Условие `Если … Тогда` и `ИначеЕсли … Тогда` — тоже шаг библиотеки; `Иначе`, группа `*Заголовок` и строки блока `"""` не разбираются. Ошибка — строка без ключевого слова после первого шага, сценарий без шагов, файл без сценариев, незакрытый блок.
- Параметры — в двойных кавычках; апостроф внутри значения допустим. Значение с двойными кавычками внутри пишем в одинарных: `'ООО "Вектор"'`; другой параметр целиком в одинарных кавычках — ошибка.
- `--compact` — краткий YAML-отчёт; `--verbose` — подробный; `--log-metrics` — флаг, пишет метрики в `data/metrics.jsonl` (по умолчанию не пишет).

## Прогон в клиенте (следующий шаг, не этот скилл)

Прошедший валидатор `.feature` гоняется на **тестовой** базе проекта харнессом прогона (vanessa-runner грузит `vanessa-automation.epf`, гоняет сценарий, отдаёт отчёт pass/fail):

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/vanessa/run-scenario.py" "<путь к .feature>" --project .
```

В мастере ядра (без плагина) — `python plugin/tools/vanessa/run-scenario.py …`. Отчёт — каталог `<сценарий>.report` (junit внутри); засчитывается только отчёт этого прогона. Боевую базу не трогаем ([secrets-and-production-database](../../docs/safety/secrets-and-production-database.md)); данные тестовые ([personal-data-masked-from-1c](../../docs/safety/personal-data-masked-from-1c.md)). Журнал проверки самой доработки — в репозитории проекта, а не ядра ([journal-placement](../../docs/process/journal-placement.md)).

## Границы

- UI-приёмка сценарием, **не** замена YAXUnit (юнит-тесты логики).
- Шаги — только из библиотеки; свой шаг = ошибка валидатора.
- Источник — va-ai (MIT), вендорен в реестр [vendor-patches](../../docs/safety/vendor-patches.md); обновление — пересинхронизацией из апстрима, затем `python tools/patches/vanessa-validator.py`.
