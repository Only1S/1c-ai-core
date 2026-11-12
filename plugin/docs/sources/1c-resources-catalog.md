---
name: 1c-resources-catalog
description: Каталог источников для работы с 1С — официальная документация, стандарты, инструменты, MCP-серверы, open-source, сообщества, обучение
metadata:
  type: reference
---

# Каталог источников для работы с 1С

Максимально полный, регион-нейтральный справочник ресурсов разработчика 1С:Предприятие 8 / 1C:EDT / BSL. Собран веером субагентов с проверкой ссылок (2026-07). Использовать как «точки входа»: официальная документация, стандарты, инструменты, MCP/AI, open-source, сообщества, обучение.

**Легенда доступа:** `web` — сайт; `API` — программный интерфейс; `MCP` — MCP-сервер для ИИ; `CLI` — командная строка; `lib` — библиотека/плагин. **⚠️** — платно / подписка ИТС / регистрация.

> Часть инструментов **уже забандлена в этой базе** (см. [[installed-tools-and-servers]]): `bsl-platform`, `EDT-MCP`, `code-index`, `bsl-analyzer`, `1c-toolkit`, скиллы `bsp` и `cc-1c-skills`. Стандарты — [[v8std-mcp-server]]; плагины EDT — [[edt-plugins-installed]].

---

## 1. Официальные ресурсы фирмы «1С»

### Документация платформы и синтакс-помощник
- **1С:ИТС — портал** — https://its.1c.ru — центральный портал документации и поддержки; RU; web ⚠️
- **Руководство разработчика 8.3 (v838doc)** — https://its.1c.ru/db/v838doc — полная документация платформы (язык, объекты, механизмы); RU; web ⚠️
- **Руководство разработчика 1C:EDT (edtdoc)** — https://its.1c.ru/db/edtdoc — проекты, интерфейс, CLI, групповая разработка; RU; web ⚠️
- **Глоссарий разработчика (v8devgloss)** — https://its.1c.ru/db/v8devgloss — толковый словарь терминов платформы; RU; web ⚠️
- **Синтакс-помощник (описание)** — https://v8.1c.ru/platforma/sintaks-pomoshchnik/ — встроенный справочник по языку; RU; web
- **Встроенный язык (раздел платформы)** — https://v8.1c.ru/platforma/vstroennyy-yazyk/ — обзор языка и механизмов; RU; web

### Стандарты и БСП (официально)
- **Система стандартов и методик разработки (v8std)** — https://its.1c.ru/db/v8std — официальные стандарты разработки конфигураций; RU; web ⚠️
- **Библиотека стандартных подсистем — документация** — https://its.1c.ru/db/bsp (актуальная: https://its.1c.ru/db/bsp3111doc) — руководство по БСП; RU; web ⚠️
- **Методподдержка разработчиков (metod8dev)** — https://its.1c.ru/db/metod8dev — методрекомендации, требования к драйверам оборудования; RU; web ⚠️
- **1С:БСП — обзор технологии** — https://v8.1c.ru/tekhnologii/standartnye-biblioteki/1s-biblioteka-standartnykh-podsistem/ — описание БСП; RU; web

### Платформа, продукты, EDT
- **v8.1c.ru — сайт 1С:Предприятие 8** — https://v8.1c.ru/ — технологии, поддержка, обучение; RU; web
- **Обзор системы 1С:Предприятие 8** — https://v8.1c.ru/tekhnologii/overview/ — архитектура и возможности; RU; web
- **edt.1c.ru — сайт 1C:EDT** — https://edt.1c.ru/ — блог, релизы, FAQ; RU; web
- **Документация и книги 1C:EDT** — https://edt.1c.ru/docs/ — руководство, «EDT & Git», plugin developer guide, JavaDoc; RU/EN; web
- **История версий 1C:EDT** — https://edt.1c.ru/docs/new/ — нововведения по версиям; RU; web
- **solutions.1c.ru — каталог решений** — https://solutions.1c.ru/ — 350+ отраслевых продуктов на платформе; RU; web

### Дистрибутивы и обновления
- **releases.1c.ru — Обновление программ** — https://releases.1c.ru/ — дистрибутивы и обновления платформы/конфигураций; RU; web ⚠️
- **portal.1c.ru — Портал 1С:ИТС** — https://portal.1c.ru/ — управление подпиской и сервисами; RU; web ⚠️
- **users.v8.1c.ru — обновления типовых** — https://users.v8.1c.ru/ — загрузка обновлений конфигураций; RU; web ⚠️
- **downloads.v8.1c.ru — файлы платформы** — https://downloads.v8.1c.ru/ — хранилище обновлений платформы; RU; web ⚠️
- **Учебная версия платформы** — https://v8.1c.ru/podderzhka-i-obuchenie/uchebnye-versii/ — бесплатная версия для обучения программированию; RU; web

### Обучение и сертификация
- **Учебный центр №1 (уц1)** — https://uc1.1c.ru/ — официальные курсы, подготовка к экзаменам; RU; web ⚠️
- **1С:Учебное тестирование** — https://uc1.1c.ru/uchebnoe-testirovanie/ — тренажёр тестов к «1С:Профессионал»; RU; web
- **1С:Профессионал — сертификация** — https://1c.ru/prof/prof.htm — страница сертификации; RU; web
- **Центры сертификации** — https://1c.ru/prof/tests/index.jsp — авторизованные центры приёма экзаменов; RU; web
- **Экзамен «1С:Эксперт по техвопросам»** — https://v8.1c.ru/tekhnologii/tekhnologii-krupnykh-vnedreniy/tsentry-korporativnoy-tekhnologicheskoy-podderzhki-tsktp/obuchenie-i-sertifikatsiya/ekzamen-1s-ekspert-po-tekhnologicheskim-voprosam/ — описание экзамена уровня «Эксперт»; RU; web
- **Книги и методматериалы** — https://v8.1c.ru/metod/books/ — учебно-методическая литература (в т.ч. М. Радченко); RU; web

### Официальные блоги/форумы
- **1С:Зазеркалье** — https://wonderland.v8.1c.ru/ — техноблог разработчиков платформы о новых механизмах; RU; web
- **Партнёрский форум «Конференция 1С:Предприятие 8»** — https://partners.v8.1c.ru/forum/ — общение с разработчиками платформы; RU; web ⚠️

---

## 2. Стандарты разработки и качество кода
- **v8std.ru** — https://v8std.ru/ — практический гид по стандартам со связкой правил и диагностик BSLLS/АПК/EDT; RU; web
- **MCP v8std** — https://ai.v8std.ru/mcp — MCP-сервер без ключа: поиск стандартов/диагностик, объяснение предупреждений; RU; MCP *(в базе — [[v8std-mcp-server]])*
- **v8std.ru/lang** — https://v8std.ru/lang/ — справочник по встроенному языку в контексте стандартов; RU; web

---

## 3. Линтеры и статический анализ
- **BSL Language Server** — https://github.com/1c-syntax/bsl-language-server — эталонный LSP для BSL: 100+ диагностик, форматирование, метрики; Java; RU/EN; CLI/API(LSP)
- **claude-code-bsl-lsp** — https://github.com/1c-syntax/claude-code-bsl-lsp — плагин Claude Code, подключающий BSL LS для файлов BSL/OneScript; MIT
- **SonarQube 1C (BSL) Community Plugin** — https://github.com/1c-syntax/sonar-bsl-plugin-community — плагин SonarQube для 1С/OneScript (30+ правил, CPD, импорт BSL LS); web(SonarQube)
- **bsl-analyzer (itrous)** — https://github.com/itrous/bsl-analyzer — CLI/LSP-анализатор BSL на Rust (архитектура rust-analyzer) со встроенным MCP-режимом; CLI/LSP/MCP *(в базе)*
- **mcp-bsl-ls (phsin)** — https://github.com/phsin/mcp-bsl-ls — Python-обёртка над BSL LS, отдаёт ошибки/предупреждения в JSON; MCP(stdio)
- **1C:АПК (Автоматизированная проверка конфигураций)** — https://v8.1c.ru/tekhnologii/1s-avtomatizirovannaya-proverka-konfiguratsiy/ — коммерческий статанализ качества конфигураций (8.3.22+); RU; web ⚠️
- **acc-check-code** — https://github.com/Bazil1c/acc-check-code — расширение, ускоряющее проверку кода в АПК; web
- **v8-code-style (1С:Code style V8 для EDT)** — https://github.com/1C-Company/v8-code-style — офиц. расширение EDT: 90+ проверок кода/метаданных по стандартам; lib(EDT)
- **dt-project-checks** — https://github.com/1C-Company/dt-project-checks — расширение EDT для проверки целостности проектов; lib(EDT)
- **ssl-support** — https://github.com/1C-Company/ssl-support — офиц. расширение EDT для комфортной разработки на БСП (контент-ассист, навигация); lib(EDT)

---

## 4. Тестирование и CI/CD
### Тестирование
- **YAXUnit** — https://github.com/bia-technologies/yaxunit — модульный тест-фреймворк (расширение + плагин EDT), ассерты, отчёты; RU; lib/CLI *(ставит установщик программ плагина в `bin/yaxunit`, headless-прогон — [[task-recipes]] §12; есть ли программа на машине — сообщает хук `session-start.py` в начале сессии, ставит `install-tools.py`)*
- **Vanessa Automation** — https://github.com/pr-mex/vanessa-automation — BDD/сценарное тестирование и автодокументирование на Gherkin, UI-автоматизация; RU; CLI
- **Vanessa-ADD (add)** — https://github.com/vanessa-opensource/add — инструменты «разработки с управляемым качеством» (TDD/BDD/CI), преемник xUnitFor1C; RU; lib/CLI
- **xUnitFor1C** — https://github.com/xDrivenDevelopment/xUnitFor1C — классический набор юнит/приёмочного/сценарного тестирования; RU; lib
- **Coverage41C** — https://github.com/1c-syntax/Coverage41C — замер покрытия кода тестами → genericCoverage.xml для SonarQube; RU/EN; CLI
- **About-tests-in-1C** — https://stepa86.github.io/About-tests-in-1C/ — сборник практик по юнит-/BDD-тестированию, покрытию, мокам; RU; web

### CI/CD, Docker, SonarQube
- **vanessa-runner (vrunner)** — https://github.com/vanessa-opensource/vanessa-runner — OneScript-утилита автоматизации (сборка, обновление, тесты) для CI; RU; CLI
- **gitsync** — https://github.com/oscript-library/gitsync — синхронизация хранилища конфигурации с Git (с историей); RU; CLI
- **precommit1c** — https://github.com/xDrivenDevelopment/precommit1c — git-хук для разборки/сборки внешних обработок/отчётов при коммите; RU; CLI
- **jenkins-lib** — https://github.com/firstBitMarksistskaya/jenkins-lib — Jenkins shared library: пайплайны для форматов Конфигуратора и EDT; RU; CLI
- **onec-docker** — https://github.com/firstBitMarksistskaya/onec-docker — Docker-образы платформы 1С 8.3 для CI; RU; CLI
- **git2sonar** — https://github.com/silverbulleters/git2sonar — выгрузка истории проекта 1С/OneScript в SonarQube; RU; CLI
- **bsl-actions-template** — https://github.com/silverbulleters/bsl-actions-template — шаблон проекта 1С с GitHub Actions; RU; lib
- **jenkins-pipeline-1C-to-sonar** — https://github.com/Stepa86/jenkins-pipeline-1C-to-sonar — готовый конвейер проверки качества через SonarQube в Jenkins; RU; CLI
- **autodocgen** — https://github.com/bia-technologies/autodocgen — генерация документации из исходников конфигурации; RU; CLI

---

## 5. Open-source стек и GitHub-экосистема
### 1c-syntax (ядро анализа BSL)
- **bsl-parser** — https://github.com/1c-syntax/bsl-parser — ANTLR4-парсеры языка BSL; lib
- **bsl-parser-core** — https://github.com/1c-syntax/bsl-parser-core — базовая инфраструктура парсеров; lib
- **mdclasses** — https://github.com/1c-syntax/mdclasses — разбор метаданных конфигураций/расширений (Конфигуратор и EDT); lib
- **supconf** — https://github.com/1c-syntax/supconf — чтение файлов настроек поддержки конфигурации; lib
- **vsc-language-1c-bsl** — https://github.com/1c-syntax/vsc-language-1c-bsl — расширение VS Code для BSL/OneScript; lib
- **intellij-language-1c-bsl** — https://github.com/1c-syntax/intellij-language-1c-bsl — плагин IntelliJ IDEA для BSL; lib

### OneScript / OScript
- **OneScript (EvilBeaver)** — https://github.com/EvilBeaver/OneScript — кроссплатформенный интерпретатор языка 1С (сайт oscript.io); RU; CLI
- **opm** — https://github.com/oscript-library/opm — пакетный менеджер OneScript (hub.oscript.io); CLI
- **oscript-library (org)** — https://github.com/oscript-library — 200+ пакетов для OneScript; lib
- **v8runner** — https://github.com/oscript-library/v8runner — ООП-запуск Конфигуратора из CLI; lib/CLI
- **v8storage** — https://github.com/oscript-library/v8storage — работа с хранилищем конфигурации; lib
- **v8find** — https://github.com/oscript-library/v8find — поиск установленных версий платформы; lib
- **oint (OpenIntegrations)** — https://github.com/oscript-library/oint — интеграции (Telegram, VK, Google, S3, PostgreSQL…); lib/CLI
- **deployka** — https://github.com/oscript-library/deployka — CD для 1С (устарел, → vanessa-runner); CLI

### Фреймворки и утилиты
- **Autumn** — https://github.com/autumn-library/autumn — DI/IoC-фреймворк для OneScript; lib
- **GitConverter** — https://github.com/1C-Company/GitConverter — офиц. инструмент 1С для синхронизации хранилища с Git и перехода в EDT с историей; lib/CLI
- **onec_dtools** — https://github.com/Infactum/onec_dtools — Python-инструменты для файлов данных 1С (1CD, контейнеры); lib/CLI
- **1C-dtools** — https://github.com/pumbaEO/1C-dtools — работа с бинарными файлами данных (1CD, cf, epf); CLI
- **onec-util** — https://github.com/v8platform/onec-util — Go-утилиты для платформы 1С; CLI
- **r2gitsync** — https://github.com/khorevaa/r2gitsync — синхронизация хранилища с Git (Go); CLI
- **1c-form-tools** (Caponid) — https://github.com/Caponid/1c-form-tools — Python-скрипты поверх `v8unpack`: модули обычных форм из бинарных `Form.bin` выгрузки Конфигуратора; MIT *(основа нашего скилла `form-bin-module`)*
- **CfeUpdater** (xnd1124) — https://github.com/xnd1124/CfeUpdater — внешняя обработка: что сломается в расширении после обновления типовой (перехватчики, формы, заимствованная СКД). ⚠️ Лицензии нет — только идея; внутри непроверенный нативный бинарник *(концепт — наш скилл `cfe-update-impact`)*
- **Накидка (md_design)** (crimsongoldteam — автор `nkdk`) — https://github.com/crimsongoldteam/md_design — MIT, прототип управляемой формы из markdown-подобного текста + выгрузка в XML конфигурации или расширения; релиз отдаёт `MDDesign.epf`; у нас взят **концепт** текстового эскиза ([[managed-forms-guide]]), сам инструмент не ставим — разбор в [[external-mcp-servers-review]] (волна 05.10.2026, вторая)
- **Универсальные инструменты 1С (ТУЗ)** (cpr1c) — https://github.com/cpr1c/tools_ui_1c — интерактивный инструментарий разработчика для управляемых форм: консоли, редактор объектов, разбор живой базы; релиз отдаёт готовые `UI.cfe`/`UI.cf`/`UI_Portable.epf` (есть сборки `nossl`); **GPL-3.0 — в дистрибутив ядра не включать**, качать из апстрима; разбор — [[external-mcp-servers-review]] (волна 05.10.2026, вторая)
- **Access-control-1C** (VorozhbitDM) — https://github.com/VorozhbitDM/Access-control-1C — обработка «Анализ и контроль доступа» для БСП 3.1+: цепочка «пользователь → группа доступа → профиль → роль → объект» в живой базе, дополняет статический `role-info`; MIT; инструмент для человека. ⚠️ Только тестовая база: пишет в данные доступа в привилегированном режиме, функция «Запустить под пользователем» временно подменяет чужой пароль, меняет настройку защиты от опасных действий. EPF собирать из `src/` скиллом `epf-build`, а не брать бинарник из релиза *(вердикт — [[external-mcp-servers-review]], волна 19.09.2026)*

- **1c-metadata-icons** (Heart-Machine) — https://github.com/Heart-Machine/1c-metadata-icons — иконки видов метаданных 1С в одном стиле (16–64 px, SVG и PNG, светлая и тёмная тема) для общих картинок EDT и Конфигуратора; готовые `.cf`/`.cfe` в релизах; CC BY 4.0 (нужна атрибуция) *(пригодится для схем доработки и общих картинок конфигурации)*

### Мобильная разработка и HTML-интерфейс (образцы)
- **mp-uchet-rashodov-i-dohodov** (sekasid) — https://github.com/sekasid/mp-uchet-rashodov-i-dohodov — мобильное приложение 1С (учёт расходов и доходов) в формате EDT, `Runtime-Version: 8.3.27`, релиз v1.0.9 (08.2026). ⚠️ **Лицензии нет** — только идеи, код не копировать
- **Пример HTML-интерфейса для мобильного приложения (+JS, +CSS)** — https://infostart.ru/1c/articles/2188399/ — базовые приёмы HTML-интерфейса в мобильном приложении; статья, web

---

## 6. MCP-серверы для 1С
### Справка платформы / синтаксис
- **mcp-bsl-platform-context** (alkoleft) — https://github.com/alkoleft/mcp-bsl-platform-context — справка по синтаксису/типам/методам платформы (аналог синтакс-помощника); stdio+SSE *(в базе — `bsl-platform`)*
- **platform-context-exporter** (alkoleft) — https://github.com/alkoleft/platform-context-exporter — выгрузка контекста платформы в файлы для индексации (компаньон, не MCP)
- **onec-help-mcp** (rzateev) — https://github.com/rzateev/onec-help-mcp — гибридный поиск (BM25+семантика) по офиц. документации; MCP(stdio)+REST
- **1c-syntax-helper-mcp** (Antonio1C) — https://github.com/Antonio1C/1c-syntax-helper-mcp — поиск по синтаксису через индексацию .hbk в Elasticsearch; HTTP

### Метаданные и живая база
- **mcp-1c** (feenlace) — https://github.com/feenlace/mcp-1c — Go-бинарник: дерево метаданных, формы, поиск по BSL + линтер; stdio
- **1c_mcp** (vladimir-kharin) — https://github.com/vladimir-kharin/1c_mcp — публикация Tools/Resources из расширения конфигурации + Python-прокси; stdio+HTTP/SSE *(v1.9.1 от 14.10.2026, лицензии по-прежнему нет; пересмотрено 19.10.2026 — прежнее «пропустить» в силе)*
- **1c-mcp-toolkit** (ROCTUP) — https://github.com/ROCTUP/1c-mcp-toolkit — MCP/REST к живой базе (метаданные+данные); HTTP *(в базе — `1c-toolkit`)*
- **1C_MCP_metadata** (artesk) — https://github.com/artesk/1C_MCP_metadata — HTTP-сервис в расширении + PowerShell-мост для метаданных; stdio
- **dajet-mcp-server** (zhichkin) — https://github.com/zhichkin/dajet-mcp-server — метаданные 1С и их SQL-хранилище (DaJet), много баз; stdio
- **MCP-DB-Client** (DitriXNew) — https://github.com/DitriXNew/MCP-DB-Client — нативная компонента для MCP-серверов «изнутри» 1С; C++/BSL
- **1c-rest-mcp** (theYahia) — https://github.com/theYahia/1c-rest-mcp — Node.js-интерфейс к REST/OData API 1С; stdio+HTTP
- **onec-mcp** (ruslan-hut) — https://github.com/ruslan-hut/onec-mcp — Go-шлюз LLM↔1С:ERP (продажи, склад); stdio
- **1c-accounting-mcp** (tarasov46) — https://github.com/tarasov46/1c-accounting-mcp — прототип для 1С:Бухгалтерии; stdio
- **onec-mcp-universal** (AlekseiSeleznev) — https://github.com/AlekseiSeleznev/onec-mcp-universal — универсальный шлюз к нескольким backend 1С
- **mcp-rsv-data** (prepod2003) — https://github.com/prepod2003/mcp-rsv-data — NL-чтение данных живой базы 1С + метаданные; Go-мост `.exe` + `.cfe`; MIT *(разобран в [[external-mcp-servers-review]] — skip, дубль `1c-toolkit`)*

### Поиск по коду и RAG
- **code-index-mcp** (Regsorm) — https://github.com/Regsorm/code-index-mcp — Rust-индексатор с first-class BSL (37 инструментов в сборке `bsl-indexer` и 20 в сборке без BSL-слоя (по README апстрима на v1.14.0; у нас в живом `tools/list` — 20), 11 BSL); stdio+HTTP; MIT *(в базе — `code-index`)*
- **1c-mcp-metacode** (ROCTUP) — https://github.com/ROCTUP/1c-mcp-metacode — метаданные+код в граф Neo4j, поиск через Cypher; stdio
- **mcp-1c-v1** (FSerg) — https://github.com/FSerg/mcp-1c-v1 — RAG-поиск на Qdrant + микросервис эмбеддингов; HTTP
- **bsl-graph** (alkoleft) — https://github.com/alkoleft/bsl-graph — граф связей объектов конфигурации (NebulaGraph); MCP+REST
- **bsl-atlas** (Arman-Kudaibergenov) — https://github.com/Arman-Kudaibergenov/bsl-atlas — структурный (SQLite/FTS5) + семантический (ChromaDB) поиск по выгрузкам; MCP

### Анализ / LSP-мосты / тесты / инфраструктура
- **mcp-bsl-lsp-bridge** (SteelMorgan) — https://github.com/SteelMorgan/mcp-bsl-lsp-bridge — Docker-мост MCP→BSL LS (100+ диагностик); MCP ⚠️ *(страницу репо подтвердить не удалось)*
- **mcp-onec-test-runner (METR)** (alkoleft) — https://github.com/alkoleft/mcp-onec-test-runner — сборка базы и запуск YAXUnit из ассистента; stdio
- **1c-log-checker** (SteelMorgan) — https://github.com/SteelMorgan/1c-log-checker — парсинг журналов через ClickHouse+Grafana; MCP
- **1c-ai-sandbox-client-server** (SteelMorgan) — https://github.com/SteelMorgan/1c-ai-sandbox-client-server — изолированная среда для отделения агента от прод-данных
- **v8-session-manager** (1c-neurofish) — https://github.com/1c-neurofish/v8-session-manager — агрегатор клиентских сессий 1С через WebSocket; HTTP+WS
- **compose4mcp** (pravets) — https://github.com/pravets/compose4mcp — Docker Compose для оркестрации 1С-MCP-серверов

### Формы, шаблоны, обёртки над 1С:Напарник
- **1c-formsserver** (Desko77) — https://github.com/Desko77/1c-formsserver — генерация/валидация/конвертация управляемых форм в 3 форматах (18 инструментов); MCP
- **1c-templates-mcp** (Desko77) — https://github.com/Desko77/1c-templates-mcp — поиск по 2200+ шаблонам BSL (SQLite+ChromaDB); SSE
- **1c-buddy** (ROCTUP) — https://github.com/ROCTUP/1c-buddy — чат/MCP/OpenAI-API поверх 1С:Напарник; MCP+OpenAI API
- **spring-mcp-1c-copilot** (SteelMorgan) — https://github.com/SteelMorgan/spring-mcp-1c-copilot — Spring/Kotlin MCP к API 1С:Напарник; SSE

### Разобраны в волне 19.09.2026 (вердикты и условия пилота — [[external-mcp-servers-review]])
- **tester** (grumagargler) — https://github.com/grumagargler/tester — тестирование через живой клиент 1С + MCP; BSD-2-Clause; possible (MCP HTTP без аутентификации)
- **onec-client-mcp-devkit** (1c-neurofish) — https://github.com/1c-neurofish/onec-client-mcp-devkit — UI тонкого клиента для агента через расширение; LGPL-3.0, вшитая компонента без лицензии; possible
- **v8std** (zeegin) — https://github.com/zeegin/v8std — локальное зеркало стандартов с MCP; CC0 на свои материалы; possible (нативно на Windows не стартует)
- **gyrfalcon** (aleksandrgradoboev-svg) — https://github.com/aleksandrgradoboev-svg/gyrfalcon — индекс конфигурации с подписками и движениями; MIT; possible, незрелый
- **1c-mcp** (skiddgoddamn) — https://github.com/skiddgoddamn/1c-mcp — метаданные, данные и пробное проведение в откате; лицензии нет; только идея
- **1c-trusted-gateway** (alonehobo) — https://github.com/alonehobo/1c-trusted-gateway — маскирующий прокси к данным 1С; лицензии нет; только идея
- **1c-lsp-mcp-skill** (fserg) — https://github.com/fserg/1c-lsp-mcp-skill — MCP-обёртка над BSL LS; LGPL-3.0; skip (дубль `bsl-ls`, 0.0.0.0 без авторизации)

---

## 7. AI-плагины IDE и skills/rules для агентов
### Плагины EDT / Конфигуратор / VS Code
- **EDT-MCP** (DitriXNew) — https://github.com/DitriXNew/EDT-MCP — MCP-плагин для 1C:EDT (97 инструментов по README апстрима (фактический состав в `tools/list` зависит от включённых toolset-ов; у нас опись снята на 2.17.1 и под 2.20.1 не перепроверялась)): валидация запросов, анализ BSL, скриншоты форм, отладка; SSE+HTTP *(в базе — `edt-mcp`)*
- **codepilot1c-edt (CodePilot1C)** (ondysss) — https://github.com/ondysss/codepilot1c-edt — AI-плагин EDT с агентным режимом, RAG и встроенным MCP-Host; HTTP
- **1C_EDT_MCP_PUBLIC** (fedukhin-sys) — https://github.com/fedukhin-sys/1C_EDT_MCP_PUBLIC — альтернативный MCP-плагин для 1C:EDT (89 инструментов), SSE :3001, нужна EDT 2026.1+; Apache-2.0 *(разобран в [[external-mcp-servers-review]] — skip, дубль `edt-mcp`)*
- **mini-ai-1c** (hawkxtreme) — https://github.com/hawkxtreme/mini-ai-1c — десктоп-ассистент рядом с Конфигуратором (захват модуля, правки, вставка); Windows
- **vscode-1c-platform-tools** (yellow-hammer) — https://github.com/yellow-hammer/vscode-1c-platform-tools — расширение VS Code/Cursor (метаданные, отладка, vanessa-runner) + MCP; stdio
- **vscode-1c-platform-extension-pack** (yellow-hammer) — https://github.com/yellow-hammer/vscode-1c-platform-extension-pack — пакет: Platform Tools + MCP + Language 1C
- **1c-ai-connector (ИИкона)** (andromanpro) — https://github.com/andromanpro/1c-ai-connector — *(v1.8.0 от 17.10.2026: несколько баз в чате, права на инструменты отдельно для каждой модели)* — встраивание 25+ LLM в конфигурации 1С через единый коннектор; HTTP/REST; MIT. **Внутри есть MCP-сервер** (HTTP-сервис JSON-RPC: метаданные, структура объектов, read-only запросы, диаграммы; Basic Auth, whitelist, аудит) + прокси `1c-ai-connector-mcp-proxy` для stdio-клиентов — единственная известная нам **MIT**-альтернатива GPL-тулкиту `1c-toolkit`, но требует БСП 3.1.10+ и не умеет `execute_code`; вердикт и условия пилота — [[external-mcp-servers-review]] (волна 05.10.2026, вторая)
- **edt-plugins** (marmyshev) — https://github.com/marmyshev/edt-plugins — **каталог-агрегатор всех плагинов 1C:EDT** с единым сайтом обновлений `marmyshev.github.io/edt-plugins/repository/`; MIT; lib *(кандидаты поверх нашего пака разобраны в [[edt-plugins-installed]] — v8-code-style, ssl-support, bslls-connector, поддержка префиксов)*
- **nkdk** (crimsongoldteam) — https://github.com/crimsongoldteam/nkdk — MCP-сервер: 1С XML-выгрузка ↔ **YAML для AI-агента** (схемы, валидация, импорт/синк, `rename_item`/`delete_item` с сохранением XML-identity); TypeScript/Node, AGPL-3.0, v0.0.3; *(✅ подключён в базе — требует Node в `D:\tools\node`, см. [[installed-tools-and-servers]], [[external-mcp-servers-review]])*

### Skills / rules для Claude Code / Cursor / Codex
- **cc-1c-skills** (Nikolay-Shirokov) — https://github.com/Nikolay-Shirokov/cc-1c-skills — скиллы полного цикла разработки 1С (плагин Claude Code); *(в базе — `.claude/skills`)*
- **claude-code-skills-1c** (Desko77) — https://github.com/Desko77/claude-code-skills-1c — Claude Code Skills для 1С-артефактов из XML/JSON; MIT, фактически **88 скиллов** (`1c-*`) + 29 правил + 5 команд *(дельта против нашего набора и риск смешивания имён — [[external-skills-review]]; из набора взяты запросы → скиллы `query-compose`/`query-optimize`)*
- **cursor-1c-skills** (Desko77) — https://github.com/Desko77/cursor-1c-skills — адаптация скиллов/правил под Cursor
- **ai_rules_1c** (comol) — https://github.com/comol/ai_rules_1c — rules/skills/subagents для BSL (Cursor, Claude Code, Codex, OpenCode) *(формальной лицензии нет; взяты только концепты; README отправляет агента к установочному протоколу — не исполнять; вердикт — [[external-mcp-servers-review]], волна 19.09.2026)*
- **1c-ai-skills** (blessed2k) — https://github.com/blessed2k/1c-ai-skills — плагин Claude Code «1c-dev»: 9 markdown-скиллов цикла «опрос → спека → шаги → выполнение»; MIT *(плагин не ставить — дубль нашего цикла; взяты 5 дельт текстом)*
- **1c-ai-feature-dev-workflow** (AndreevED) — https://github.com/AndreevED/1c-ai-feature-dev-workflow — адаптация `feature-dev` из `anthropics/claude-plugins-official` под 1С; MIT *(possible: только лестница размера консилиума)*
- **tiny1C** (bigsofter) — https://github.com/bigsofter/tiny1C — правила разработки 1С для агентов, у каждого правила свой источник и своя проверка; код MIT, тексты правил CC BY 4.0 *(берём знание, MCP-сервер не ставим)*
- **v8std-standards-harness** (axelboman277) — https://github.com/axelboman277/v8std-standards-harness — скилл «не пропускать сверку со стандартами»: карта «действие в коде → номера стандартов»; MIT
- **1c-ai-development-kit** (Arman-Kudaibergenov) — https://github.com/Arman-Kudaibergenov/1c-ai-development-kit — агенты/скиллы/правила для 1С в Cursor
- **unica** (IngvarConsulting) — https://github.com/IngvarConsulting/unica — плагин Codex со скиллами, MCP и скриптами для 1С
- **form-ordinary** (dreamadv81) — https://github.com/dreamadv81/form-ordinary — скилл для ОБЫЧНЫХ форм: `form.frm` ⇄ JSON байт в байт, правка операциями, проверка, отрисовка в SVG/PNG, распаковка и сборка `Form.bin`; Python 3.12+ без сторонних пакетов; MIT, но 300 картинок платформы внутри — права фирмы «1С» *(разбор и проба на копиях форм — [[external-skills-review]] §J)*
- **1c-cf-vendor-merge** (alonehobo) — https://github.com/alonehobo/1c-cf-vendor-merge — скилл обновления доработанной типовой на новый релиз трёхсторонним git-слиянием XML-выгрузок (ветки старого и нового релиза и текущей конфигурации, авторазбор конфликтов, импорт в пустую базу, `/CheckModules` с расширениями); **лицензии нет** — только идеи *(свой скилл по ним — решение владельца 19.10.2026, [[external-skills-review]] §J)*

### Скиллы общего назначения (вне 1С-контура)
- **i-have-adhd** (ayghri) — https://github.com/ayghri/i-have-adhd — форма ответа агента: действие первым, шаги нумеровать, в конце один следующий шаг, без вступлений и концовок; MIT *(не ставим — приёмы своими словами в [[human-texts-start-with-action]] п.8)*
- **no-ai-slop** (petergyang) — https://github.com/petergyang/no-ai-slop — 20+ «машинных» оборотов текста и как их убрать; MIT *(не ставим — русский список в [[human-texts-start-with-action]] п.9, явно пустые обороты ловит `health-check`)*
- **obsidian-skills** (kepano) — https://github.com/kepano/obsidian-skills — MIT, скиллы по спеке Agent Skills (на 30.10.2026 их 6): `obsidian-markdown`, `obsidian-bases`, `obsidian-cli`, `json-canvas`, **`defuddle`** (чистое web→markdown вместо WebFetch), `knap`; *релевантно потому, что наша база знаний — Obsidian-vault; вердикт по каждому — [[external-skills-review]]. В ядро взяты 4 скилла набора: `obsidian-markdown`, `obsidian-bases`, `obsidian-cli`, `json-canvas` (наши правки — [[vendor-patches]]). `defuddle` не копировался: идея оформлена своим скиллом `page-fetch`, CLI ставится отдельно (`THIRD-PARTY.md`). `knap` не разбирался*
- **claude-code-mods** (hamzafer) — https://github.com/hamzafer/claude-code-mods — 25 модов Claude Code (плагины с функциями-хуками, 2.1.287+): строки контекста и кэша, стражи опасных команд, игры; MIT *(не ставим — чужой мод может переписать вердикты наших барьеров; три образца для своих модов — [[claude-code-mods-review]])*
- **awesome-claude-code-mods** (karanb192) — https://github.com/karanb192/awesome-claude-code-mods — каталог 6000+ модов с доступом каждого по статическому разбору (сайт mods.aidojo.si); CC0 *(для первичного отсева, не для допуска — [[claude-code-mods-review]])*
- **better-claude** (midudev) — https://github.com/midudev/better-claude — 8 плагинов и модов: context-meter, time-machine (снимки рабочей папки в git), `/commit`, очередь запросов, озвучка; MIT *(не ставим; context-meter — образец для своего мода, time-machine и commit — против наших правил git, [[claude-code-mods-review]])*

> Разобрано и **отклонено** (чтобы не разбирать повторно): `pixel-agents-hq/pixel-agents` — визуализация агентов, ценности для 1С нет; `alishahryar1/free-claude-code` — прокси к сторонним LLM-провайдерам, уводит рабочий трафик наружу против [[secrets-and-production-database]]; `OBLADAET-ru/1Cbase` — учебник 1С одной HTML-страницей, в разработке, без лицензии (19.10.2026). Причины — [[external-skills-review]] §C, §J.

---

## 8. Каталоги и агрегаторы
- **OpenYellow** — https://openyellow.org (github.com/OpenBSL/OpenYellow) — агрегатор OSS-проектов 1С с рейтингом по звёздам; web
- **YellowPM** — https://github.com/OpenBSL/YellowPM — пакетный менеджер обработок/отчётов/расширений из GitHub в 1С по индексам OpenYellow; lib
- **awesome-1c** — https://github.com/artbear/awesome-1c — курируемый список инструментов и библиотек экосистемы 1С; web
- **StackTechnologies1C** — https://github.com/Oxotka/StackTechnologies1C — MIT, курируемый обзор стека разработчика 1С (разработка, СУБД, git и хранилище, прототипирование, качество, CI/CD, интеграции); предшественник `Landscape1C` того же автора — для регулярной сверки брать живой `Landscape1C`, здесь полезны разделы-обзоры; web
- **Untru/1c-mcp (Awesome 1C MCP)** — https://github.com/Untru/1c-mcp — каталог MCP-серверов 1С с матрицами совместимости; web
- **yellowmcp.dev** — https://yellowmcp.dev/catalog — каталог ~49 MCP-серверов и AI-инструментов для 1С; web
- **Landscape1C (Ландшафт технологий 1С)** (Oxotka) — https://landscape1c.ru (github.com/Oxotka/Landscape1C) — MIT, наследник StackTechnologies1C (тот тоже жив): 229 карточек инструментов с разметкой по роли, контексту, зрелости, лицензии и доступности в РФ. Машиночитаемо: https://landscape1c.ru/llms.txt (список с описаниями) и `data.js` (поле `repo` у 83 карточек). Годится для дельты по **не-MCP** инструментам (CI, тесты, конвертация форматов, администрирование); по MCP/AI слабо — одна карточка. Данные на 26.08.2026; web
- **skills.sh** (Vercel, github.com/vercel-labs/skills, MIT) — https://skills.sh — каталог Agent Skills с машинным поиском `https://skills.sh/api/search?q=…&limit=…` (до 100). **1С-срез отдаётся только на кириллические запросы** («1С», «1с», «БСП»), латиница даёт шум. CLI `npx skills` и скилл `find-skills` не ставить: телеметрия включена по умолчанию, установка глобальная и без подтверждения. Рецепт сверки — [[external-mcp-servers-review]] (волна 19.09.2026); API
- **awesome-claude-code** (hesreallyhim) — https://github.com/hesreallyhim/awesome-claude-code — курируемый каталог слоя «общий Claude Code»: хуки, линтеры конфигов, безопасность, скиллы. ⚠️ Лицензия **CC BY-NC-ND 4.0** — в ядре только ссылка и наши вердикты, без копий списка, CSV и описаний. Есть фермы клонов `r01-…` — читать только оригинал; web

**Эталоны слоя Claude Code** (вне 1С — для сверки хуков, скиллов и MCP):
- **anthropics/claude-code** — https://github.com/anthropics/claude-code — CHANGELOG и документация хуков; ⚠️ проприетарная лицензия — только чтение и пересказ со ссылкой
- **Piebald-AI/claude-code-system-prompts** — https://github.com/Piebald-AI/claude-code-system-prompts — веса системных промптов и инструментов по версиям Claude Code, тег на каждую версию; MIT на оформление, сами тексты промптов принадлежат Anthropic — в ядро не копировать. Упомянутый в их README `tweakcc` не ставить: он патчит установленный Claude Code. Замер — [[claude-code-context-engineering]]
- **agentskills/agentskills** — https://github.com/agentskills/agentskills — спецификация формата Agent Skills (`SKILL.md`, frontmatter, имена); код Apache-2.0, доки CC-BY-4.0
- **modelcontextprotocol/modelcontextprotocol** — https://github.com/modelcontextprotocol/modelcontextprotocol — спецификация MCP; лицензия в переходе MIT → Apache-2.0, доки CC-BY-4.0

---

## 9. Сообщества, форумы, базы знаний
- **Инфостарт (Infostart)** — https://infostart.ru — крупнейшее RU-сообщество: статьи, маркетплейс, курсы, биржа; web
- **Форум Инфостарт** — https://forum.infostart.ru — форум по конфигурациям и разработке; форум
- **Хаб «1С» на Habr** — https://habr.com/ru/hubs/1C/ — тематический хаб разработки/администрирования; блог
- **Волшебный форум (Mista)** — https://forum.mista.ru — старейший активный форум 1С-специалистов; форум
- **Книга знаний Mista** — https://kb.mista.ru — база знаний по программированию 1С (С. Митичкин); база знаний
- **CyberForum — раздел 1С** — https://www.cyberforum.ru/1c/ — раздел 1С на форуме программистов; форум
- **Форум База 1С** — https://forum-baza.ru — вопросы-ответы для программистов/бухгалтеров/админов; форум
- **1C:Developer Network (1C:DN)** — https://1c-dn.com — офиц. англоязычная площадка: документация, туториалы, форум; EN; база знаний

---

## 10. Блоги, производительность, обучение
### Блоги и справочники
- **Программист 1С** — https://programmist1c.ru — блог по решениям на 1С/Битрикс; блог
- **Hello, 1С (howknow1c)** — http://howknow1c.ru — бесплатные уроки по программированию/конфигурированию; блог/курс
- **Блог 1С программиста** — https://1c-programmer-blog.ru — разборы по разработке 8.2/8.3; блог
- **myblog-1c.ru** — https://www.myblog-1c.ru — шпаргалки и методичка по типовым; блог
- **bp1s.ru** — https://bp1s.ru — авторские заметки по разработке; блог
- **helpf.pro** — https://helpf.pro — рецепты кода и решения типовых задач; база знаний

### Производительность и эксплуатация
- **1c-optimyzer** (anymasoft) — https://github.com/anymasoft/1c-optimyzer — анализ архивов **технологического журнала (ТЖ)** 1С: загрузка в DuckDB, read-only SQL-консоль, библиотека SQL-шаблонов, опц. подключение PostgreSQL/MS SQL для разбора планов запросов. Desktop-GUI (Tauri 2 + Python-sidecar), готовый `.msi` (Node/Docker не нужны). ⚠️ **Не MCP** — автоматизации из Claude нет. ⚠️ Лицензия **source-available: коммерческое использование запрещено без разрешения автора**. v0.1.0 (09.07.2026), 20★; инструмент
- **OneSTools.PS.TechLog** (akpaevj) — https://github.com/akpaevj/OneSTools.PS.TechLog — PowerShell-модуль разбора и агрегации ТЖ (`Get-TechLog`/`Sort-TechLog`/`Group-TechLog`), работает в Windows PowerShell 5.1. **MIT**. ✅ Забандлен в ядро (`tools/OneSTools.PS.TechLog`); инструмент
- **rdv-team/loga** (RDV SOFT) — https://github.com/rdv-team/loga — потоковый парсинг ТЖ, фильтры, агрегации, экспорт в Excel; чанкинг файлов 10–50 ГБ (Parquet), многопоточность. Python 3.10+, **BSD-3-Clause**, v1.1.0 (12.2025); инструмент *(только в мастере: клон `tools\loga` + враппер `tools\run-loga.cmd`, в плагин не входит; статус — [[installed-tools-and-servers]], секция «Статус установки»)*
- **medigor/tech-log-parser** — https://github.com/medigor/tech-log-parser — CLI-конвертер ТЖ→JSON на Rust, готовый `converter.exe`; корректно разбирает «битый» JSON ТЖ 8.3.25+. **MIT**, только парсинг (агрегации нет), v0.1.0 (2024); инструмент
- **free-archer/read-tj-pl** — https://github.com/free-archer/read-tj-pl — загрузка полного ТЖ (с планами запросов) в локальный **SQLite** → SQL-агрегация. Python, **MIT**; ⚠️ репозиторий архивирован (04.2026); инструмент
- **rdv-team/logt** (RDV SOFT) — https://github.com/rdv-team/logt — реконструкция длительных операций (`VRSREQUEST`→`VRSRESPONSE`), метрики dbms-time/lock-waits. **BSD-3-Clause**, активен; ⚠️ **обязателен ClickHouse 25.6+**, анализ — через GUI-обработку 1С; инструмент
- **Gilev.ru (Ускоряем 1С)** — http://www.gilev.ru — центр экспертизы по производительности (методики, KIP, 1С:ЦКТП); портал
- **Курс Гилёва по производительности** — http://www.gilev.ru/kurs/ — подготовка к «1С:Эксперт»; курс
- **spec8.ru** — https://www.spec8.ru — «Профессиональное программирование в 1С:Предприятии 8», подготовка к экзаменам; курс

### Курсы и YouTube
- **Курсы-по-1С.рф** — https://xn----1-bedvffifm4g.xn--p1ai — дистанционное обучение (Е. Гилёв): программирование, EDT, Git, DevOps; курс
- **1С:Учебный центр (YouTube)** — https://www.youtube.com/@uc1c — видеоинструкции, вебинары, материалы к экзаменам; канал
- **Илья Леонтьев про 1С (YouTube)** — https://www.youtube.com/@leontyev_ilya — разработка, стримы; канал
- **NIZAMOV.SCHOOL (YouTube)** — https://www.youtube.com/@nizamovschool — мобильная разработка, интеграция; канал
- **Желтый клуб (YouTube)** — https://www.youtube.com/@yellowclub — программирование, автотесты, управление командой; канал

---

## 11. Telegram-каналы и чаты
### Каналы
- **1С:Предприятие 8** — https://t.me/onecv8 — крупный новостной канал по 1С
- **Желтый клуб** — https://t.me/yellowclub_official — сообщество 1С-программистов
- **INFOSTART Enterprise** — https://t.me/infostart_enterprise — официальный канал Инфостарта
- **OpenYellow** — https://t.me/OpenYellowProject — open-source-инструменты и практики
- **1С СППР** — https://t.me/SPPR1c — проектирование прикладных решений, инженерные практики
- **Никита Федькин (nixel2007)** — https://t.me/nixel2007_thoughts — заметки мейнтейнера BSL LS / 1c-syntax
- **1С:Лекторий** — https://t.me/lector_1c — анонсы и записи лекций фирмы 1С

### Чаты
- **BSL Language Server** — https://t.me/bsl_language_server — чат по BSL LS и контролю качества кода
- **Сообщество 1С-разработчиков** — https://t.me/e1c_community — общий чат вопросов по разработке
- **1С:EDT** — https://t.me/e1c_edt — чат по среде разработки EDT
- **1С, БСП, DevOps и Архитектура** — https://t.me/ssl1c — БСП, DevOps, архитектура
- **Администрирование 1С** — https://t.me/adm_1c — настройка/администрирование/оптимизация
- **PostgreSQL + 1C + Linux** — https://t.me/PostgreSQL_1C_Linux — эксплуатация 1С на PostgreSQL/Linux
- **1C Middle** — https://t.me/middle1c — чат для разработчиков middle+

---

## 12. Коммерческие / SaaS MCP-решения
- **ARQA MCP Server** — https://arqa.cc/ru/mcp-server — on-premise MCP для документов/отчётов через AI (Бухгалтерия/УТ/ERP/ЗУП); ⚠️ платный, триал
- **OneMCP** — https://onemcp.ru — облачная платформа семантического поиска по метаданным/коду/докам; freemium
- **VibeCoding1C** — https://vibecoding1c.ru — no-code конструктор MCP-серверов для 1С + курсы; ⚠️ платный
- **Infostart MCP** — https://infostart.ru — поиск по метаданным с гибридной индексацией + синтакс-помощник; ⚠️ платный
- **OneRPA / comol MCP** — https://docs.onerpa.ru/mcp-servery-1c — ~9 Docker-контейнеров (справка, метаданные, валидация); ⚠️ платный
- **INFATON MCP35** — расширение на 35 инструментов под ERP-сценарии; ⚠️ коммерческое
- **@rcs-kz/mcp-1c** — npm/Python-рантайм с тарифами Solo/Pro/Team; ⚠️ коммерческий

---

## Примечания по достоверности (2026-07)
- Все ссылки собраны и проверены веб-поиском/фетчем субагентами. Лицензии у части OSS-проектов в каталогах явно не указаны.
- **Требует проверки:** `SteelMorgan/mcp-bsl-lsp-bridge` — значится в каталогах, отдельную страницу репозитория подтвердить не удалось.
- Быстрая переиндексация экосистемы MCP/AI — через каталоги §8 (OpenYellow, Untru/1c-mcp, yellowmcp.dev): они обновляются чаще этого справочника.
- **Записи волны 19.09.2026** (§5 — утилиты и мобильные образцы, §6 — «Разобраны в волне», §7, §8) проверены через `gh api` (метаданные, лицензия, дерево) и HTTP-запросом (`landscape1c.ru/llms.txt`, API skills.sh, статья Инфостарта — ответ 200). Лицензии — по файлу LICENSE, а не по полю GitHub.
