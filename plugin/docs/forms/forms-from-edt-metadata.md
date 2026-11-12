---
name: forms-from-edt-metadata
description: "Формы с данными из EDT делать ГИБРИДНО — метаданные/скриншот/ошибки брать напрямую через edt-mcp, а строить/валидировать/конвертировать форму через 1c-forms; встроенный EDT-режим 1c-forms отключён (несовместимость API)"
metadata:
  type: feedback
---

# Правило: гибридная работа с формами (edt-mcp + 1c-forms)

Когда для формы нужны данные из проекта (реквизиты объекта, скриншот WYSIWYG, ошибки EDT), работать **гибридно**: разные шаги — через разные MCP. НЕ полагаться на встроенную EDT-интеграцию сервера `1c-forms` — она отключена.

**Why:** EDT-клиент сервера `1c-forms` (`edt_client.py`) писан под другой API edt-mcp — шлёт `{fqn}` и ждёт JSON-ответ, а edt-mcp v2.5.1 требует `{projectName, objectFqns:[...]}` / `{projectName, formPath}` и отдаёт **Markdown-ресурс** (`content[].type=resource`, `embedded://…md`). Из-за этого метаданные не парсятся — тихо приходит пусто, при этом статус может врать «зелёным». Поэтому дефолт кода — `EDT_ENABLED=false` (`config.py`; в `.env.example` — активная строка), сервер стартует с честным `available:false`. Оба MCP уже подключены — надёжнее оркестрировать их напрямую, чем чинить хрупкий чужой парсер Markdown.

**How to apply:**
1. **Метаданные объекта** (реквизиты / ТЧ / допустимые DataPath) → `edt-mcp` `get_metadata_details({projectName:"<ИМЯ_ПРОЕКТА_EDT>", objectFqns:["Catalog.X"], full:true})`; список объектов — `get_metadata_objects`.
2. **Спецификацию формы собрать самому** из метаданных: главный реквизит `Object` типа `<Тип>Object.X` (напр. `CatalogObject.X`), поля `Object.<реквизит>`, таблицы по табличным частям `Object.<ТЧ>` с колонками `Object.<ТЧ>.<реквизит>`.
3. **Построить / провалидировать / сконвертировать** (форма проекта EDT; для выгрузки Конфигуратора — скиллы `form-*`, таблица в [[forms-skills-and-visual-check]] п.1) → `1c-forms`: `generate_form(spec)` → `validate_form(xml)`; конвертация форматов Конфигуратор↔Managed↔EDT — `convert_form`; справка по тегам/значениям — `get_form_prompt` / `get_form_schema`. ⚠️ Каркас `generate_form` в формате **EDT** в одном из экземпляров пришёл неполным: без корневого `extInfo`, `<handlers>` и `action` у команд, обработчик назван `OnCreateAtServerAtServer` — форма не рисовалась, а обработчики молча не вызывались, и `validate_form` этого не видит. Перед приёмкой сверять каркас по «Что EDT требует…» и «Обработчики: два места регистрации» в [[managed-forms-guide]] _(на текущей версии `1c-forms` не перепроверено: сервер был недоступен)_.
4. **Скриншот формы / ошибки проекта / валидация запроса** (если нужно) — напрямую `edt-mcp` (`get_form_screenshot`, `get_project_errors`, `validate_query`), НЕ через `1c-forms`. Скриншоту нужен флаг рендера — [[edt-mcp-pitfalls]] → «Скриншот формы: флаг рендера в `1cedt.ini`».
5. НЕ включать `EDT_ENABLED=true` в `1c-forms`, пока не написан адаптер `edt_client.py` под API edt-mcp (сверено на v2.5.1, на поздних версиях не перепроверялось; какая версия стоит сейчас — `bundles.info` установки EDT, [[edt-plugins-installed]]) (params `projectName`/`objectFqns`/`formPath` + парсинг Markdown-ресурсов) — это опция на будущее для самодостаточности сервера.

**Проверено (в проекте-экземпляре):** demo на справочнике с табличной частью — `edt-mcp` дал реквизиты и ТЧ → спека → `generate_form` (logform) → `validate_form` = `valid:true`, 0 ошибок, 0 предупреждений.

Связано: инструменты/порты — [[installed-tools-and-servers]]; формы штатно и «с глазами» — [[forms-skills-and-visual-check]]; практикум по формам — [[managed-forms-guide]]; штатные средства, не выдумывать — [[work-through-tools]].
