# Сторонние компоненты и лицензии

**Коротко.** Наш код и тексты — под лицензией PolyForm Noncommercial 1.0.0 ([LICENSE](LICENSE)); версии до core-v5.6.0 включительно — под MIT. Программ инструментов в репозитории нет: установщик скачивает их из официальных релизов авторов и сверяет контрольные суммы, у каждой программы — своя лицензия. Одна программа закрытая и наша — движок обфускации `obfuscator.zip`. Часть скиллов и приёмов в правилах взята у других авторов — они перечислены ниже с лицензиями.

Канал ядра — два репозитория: закрытый `Only1S/1c-ai-core` для своих проектов и открытый `Only1S/1c-ai-core`. Чем открытый отличается от закрытого — в последнем разделе.

## Что наше (PolyForm Noncommercial 1.0.0)

Хуки `plugin/hooks/`, скрипты `plugin/tools/` (установщик программ, подключение проекта, проверка секретов, запуск серверов), команды `plugin/commands/`, агенты `plugin/agents/`, сценарии `plugin/workflows/`, правила и справочники `plugin/docs/` (кроме пересказов, отмеченных ниже), скиллы с пометкой «наш» в таблице ниже, `README.md`, `RELEASES.md`.

## Программы, которые ставит установщик

В репозитории их нет. Установщик (`plugin/tools/setup/install-tools.py`) скачивает файл релиза с GitHub автора, сверяет SHA-256 из `plugin/tools/setup/tools-manifest.json` и кладёт его в папку данных плагина.

| Файл и версия | Для чего | Источник | Лицензия |
|---|---|---|---|
| bsl-indexer-windows-x64.zip 1.15.6 | индексатор кода 1С — поиск по коду, вызовы и связи (MCP-сервер code-index) | [Regsorm/code-index-mcp](https://github.com/Regsorm/code-index-mcp) | **MIT** |
| bsl-context-windows-x64.zip 0.23.1 | справка по встроенному языку и платформе 1С (MCP-сервер bsl-context) | [Regsorm/bsl-context](https://github.com/Regsorm/bsl-context) | **MIT (с атрибуцией двух авторов)** |
| bsl-analyzer-windows-amd64.exe 0.4.0 | анализатор кода 1С — автоматическая проверка после каждой правки модуля .bsl | [itrous/bsl-analyzer](https://github.com/itrous/bsl-analyzer) | **LGPL-3.0-or-later (поставляемая сборка)** |
| mcp-bsl-context-0.3.2.jar 0.3.2 | синтаксис и объектная модель платформы 1С (MCP-сервер bsl-platform; нужна Java 17 или новее) | [alkoleft/mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) | **MIT** |
| MCP_Toolkit.epf 1.9.0 | обработка для базы 1С: через неё сервер 1c-toolkit выполняет запросы и код в тестовой базе (открывается в базе вручную) | [ROCTUP/1c-mcp-toolkit](https://github.com/ROCTUP/1c-mcp-toolkit) | **GPL-3.0** |
| 1c-metadata-json-exporter.epf 2.0.0 | обработка для базы 1С: выгружает структуру метаданных в JSON | [Romandredan/1c-metadata-json-exporter](https://github.com/Romandredan/1c-metadata-json-exporter) | **MIT** |
| YAxUnit-25.12.cfe 25.12 | движок юнит-тестов 1С YAXUnit (расширение .cfe): команда /ones-core:tests ставит его в тестовую базу | [bia-technologies/yaxunit](https://github.com/bia-technologies/yaxunit) | **Apache-2.0** |
| OneScript-2.2.0-win-x64.zip 2.2.0 | исполнитель скриптов OneScript для vanessa-runner (необязательная запись, `--only onescript …`) | [EvilBeaver/OneScript](https://github.com/EvilBeaver/OneScript) | **MPL-2.0** |
| vanessa-runner-3.0.2.ospx 3.0.2 | запуск сценариев Vanessa Automation без интерфейса (пакет opm; зависимости — из hub.oscript.io) | [vanessa-opensource/vanessa-runner](https://github.com/vanessa-opensource/vanessa-runner) | **MPL-2.0** |
| add-6.9.5.ospx 6.9.5 | Vanessa Automation Driven Development, `bddRunner.epf` (пакет opm) | [vanessa-opensource/add](https://github.com/vanessa-opensource/add) | **MPL-2.0** |
| vanessa-automation-single.1.2.043.45.zip 1.2.043.45 | движок сценариев Vanessa Automation (`vanessa-automation-single.epf`), харнесс передаёт его vrunner | [Pr-Mex/vanessa-automation](https://github.com/Pr-Mex/vanessa-automation) | **BSD-3-Clause** |
| obfuscator.zip, версия выпуска ядра | закрытый движок обфускации кода 1С для `/ones-core:protect` (необязательная запись, `--only obfuscator`) | страница Release этого канала, ассет выпуска; сумма сверяется по `sha256.txt` внутри архива | **закрытая лицензия Only1S**, не MIT |

Программы под GPL и LGPL не распространяются вместе с плагином — именно поэтому их ставит установщик, а не репозиторий.

Внутри `obfuscator.zip` — сторонние компоненты: tree-sitter 0.25.10, грамматика tree-sitter-bsl и jtreesitter 0.25.6 под **MIT**, рантайм native-image под **GPL-2.0 с Classpath Exception**. Полный список — `THIRD-PARTY.md` в архиве, тексты лицензий — его папка `third-party/`.

## Программы и сервисы, которые плагин вызывает, но не ставит

| Что | Для чего | Источник | Лицензия |
|---|---|---|---|
| BSL Language Server | сервер `bsl-ls` — анализ модулей | [1c-syntax/bsl-language-server](https://github.com/1c-syntax/bsl-language-server) | **LGPL-3.0-or-later** |
| claude-code-bsl-lsp | ставит и обновляет BSL Language Server | [1c-syntax/claude-code-bsl-lsp](https://github.com/1c-syntax/claude-code-bsl-lsp) | **MIT** |
| headroom | сервер `headroom` — сжатие длинного вывода | PyPI `headroom-ai` | **Apache-2.0** |
| v8std | сервер стандартов 1С, сетевой сервис `ai.v8std.ru` | v8std.ru | условия сервиса |
| defuddle | скилл `page-fetch` — текст веб-страницы | [kepano/defuddle](https://github.com/kepano/defuddle) | **MIT** |
| v8unpack | скиллы `cf-unpack`, `form-bin-module` — разбор файлов 1С без платформы | [saby-integration/v8unpack](https://github.com/saby-integration/v8unpack) | **MIT** |
| EDT-MCP | необязательный сервер `edt-mcp` — работа с проектом в 1C:EDT | [DitriXNew/EDT-MCP](https://github.com/DitriXNew/EDT-MCP) | **AGPL-3.0** |
| 1c-formsserver | сервер `1c-forms` — проверка и сборка управляемых форм, ставит установщик | [Desko77/1c-formsserver](https://github.com/Desko77/1c-formsserver) | **MIT** |
| платформа 1С, Java 17+, Python 3.8+, Git | системные программы | ставит пользователь | — |

## Сторонний контент внутри плагина

| Что | Источник | Лицензия | Примечание |
|---|---|---|---|
| инструментальные скиллы 1С в `plugin/skills/` (`cf-*`, `db-*`, `epf-*`, `form-*`, `meta-*`, `mxl-*`, `skd-*` и др.) | [Nikolay-Shirokov/cc-1c-skills](https://github.com/Nikolay-Shirokov/cc-1c-skills) | **MIT** (© 2025-2026 Nick Shirokov) | наши правки — в 16 папках (незарегистрированная база в `db-*`, запрет вызова моделью у `meta-remove` и `support-edit`, путь пользователя в `epf-build` и `web-test`); перечень — `plugin/docs/safety/vendor-patch-registry.md` |
| хук `plugin/hooks/support-guard.py` — защита объектов на поддержке поставщика | перенос на Python хука `hooks/support-guard.mjs` из cc-1c-skills | **MIT** (© 2025-2026 Nick Shirokov) | логика и тексты отказа — поставщика; наши добавки — раскладка EDT и `Configuration.distr` |
| скилл `1c-standards` | [SolovievHub/1c-standards-claude-skill](https://github.com/SolovievHub/1c-standards-claude-skill) | **лицензии нет** | ⚠ входит и в открытый репозиторий — решение и риск владельца (13.11.2026, ADR-0014); наши правки номеров стандартов — в реестре правок |
| скилл `bsp` (БСП 3.1.11) | [brake71/1c-ssl-skills](https://github.com/brake71/1c-ssl-skills) | **MIT** (© 2026 Чекменев Д. А.) | навигатор, справочники и `bsp_api.py` |
| скиллы `obsidian-markdown`, `obsidian-bases`, `obsidian-cli`, `json-canvas` | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | **MIT** | наши правки — русские триггеры в описаниях |
| скиллы `archify` (3.1.0), `simplify-codebase`, `test-value` | [tt-a1i/archify](https://github.com/tt-a1i/archify), коммит `88d1ae4` | **MIT** (© 2026 tt-a1i, © 2025 Cocoon AI; © 2026 simplify-codebase contributors) | `LICENSE` и `THIRD_PARTY_NOTICES.md` — в папке каждого скилла; наши правки — русские описания, проверка обновлений в сети только по `ARCHIFY_UPDATE_CHECK_ENABLED=1`, без самоправки `test-value` (`tools/patches/archify-skills.py`). Встроенные знаки технологий — под своими лицензиями (Simple Icons, CC0 у коллекции); знак Vue.js (**CC BY-NC-SA 4.0**, некоммерческая) из набора **убран**; строка о нём в `THIRD_PARTY_NOTICES.md` вендора оставлена как есть |
| модуль PowerShell `OneSTools.PS.TechLog` 1.1.11 в папке `tools` плагина — разбор технологического журнала 1С (`Get-TechLog`, `Sort-TechLog`, `Group-TechLog`) | [akpaevj/OneSTools.PS.TechLog](https://github.com/akpaevj/OneSTools.PS.TechLog), пакет PowerShell Gallery | **MIT** (© Akpaev E.A.) | код не изменялся; `LICENSE` — в папке модуля; наш только `Import-TechLog.ps1` (самолокующийся импорт) |
| скилл `uuid-validate` — `scripts/check_uuid_duplicates.py` | [Desko77/claude-code-skills-1c](https://github.com/Desko77/claude-code-skills-1c) | **MIT** (© 2026 Desko77) | скрипт как есть; `SKILL.md` — наш |
| скиллы `query-compose`, `query-optimize` — материал в `references/` | Desko77/claude-code-skills-1c | **MIT** (© 2026 Desko77) | `SKILL.md` — наши; источник указан в шапке каждого файла |
| скилл `1c-platform-kb` — база знаний по платформе 1С и окружению (149 статей) | база знаний администратора владельца: конспекты документации ИТС 8.3.27 и методичек ИТС своими словами, статьи по PostgreSQL, MS SQL, Linux, Windows, Apache, IIS, Kafka, RabbitMQ | **конспекты ИТС — пересказ платного материала по подписке владельца** | ⛔ убрать перед открытием репозитория; в закрытом канале и проектах владельца — можно; дословных текстов ИТС нет; снимок — `tools/indexes/sync-platform-kb.py`; с 13.11.2026 входит и в открытый репозиторий — решение владельца (ADR-0014) |
| скилл `form-ordinary` — обычные формы: `form.frm` ⇄ JSON, правка, проверка, отрисовка, `Form.bin` | [dreamadv81/form-ordinary](https://github.com/dreamadv81/form-ordinary), коммит `3c51f01` | **MIT** | `LICENSE` — в папке скилла; **картинки платформы (`frm_codec/data/platform_pictures/`, права фирмы «1С») не включены** — оставлен только `index.json` с их именами и кодами, отрисовка рисует серые квадраты; свои картинки — переменной `FRM_PLATFORM_PICTURES` |
| скилл `cf-vendor-update` — обновление доработанной типовой на новый релиз | **наш** | MIT | по идее `alonehobo/1c-cf-vendor-merge` (лицензии нет): код не брался, грабли в `docs/platform/vendor-release-update.md` — пересказ |
| скилл `form-bin-module` — `scripts/form_bin_module.py` | [Caponid/1c-form-tools](https://github.com/Caponid/1c-form-tools) | **MIT** (© 2025 Caponid) | перенос с изменениями; текст лицензии — в шапке скрипта |
| скиллы `page-fetch`, `cf-unpack`, `cfe-update-impact` | **наши** | MIT | `cfe-update-impact` — по идее xnd1124/CfeUpdater (лицензии нет): код и тесты не брались |
| `plugin/docs/platform/designer-batch-runs.md` — «вердикт по нескольким сигналам» | Desko77/claude-code-skills-1c | **MIT** | пересказ своими словами |
| `plugin/docs/code/code-situation-standards-map.md` — карта «ситуация → стандарты» | [axelboman277/v8std-standards-harness](https://github.com/axelboman277/v8std-standards-harness) | **MIT** (© 2026 axelboman277) | перестроено, номера сверены через v8std |
| `plugin/docs/code/naming-and-module-design.md` — лестница выбора точки врезки | [blessed2k/1c-ai-skills](https://github.com/blessed2k/1c-ai-skills) | **MIT** | пересказ |
| приёмы в `capture-knowledge`, `subagents-on-explicit-consent`, `readiness-matrix-and-process-diagram` | [obra/superpowers](https://github.com/obra/superpowers), [github/spec-kit](https://github.com/github/spec-kit) | **MIT** | только идеи, текст свой |
| `plugin/docs/tools/claude-code-context-engineering.md` — веса фрагментов системного промпта | [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) | **MIT** | только числа и имена фрагментов |
| `plugin/docs/sources/1c-resources-catalog.md` §8 — поиск по skills.sh | [vercel-labs/skills](https://github.com/vercel-labs/skills) | **MIT** | описание своими словами |
| приёмы в `edt-mcp-pitfalls`, `managed-forms-guide` | [bigsofter/tiny1C](https://github.com/bigsofter/tiny1C) | **CC BY 4.0** (тексты) | пересказ с пометкой «по мотивам» |
| приёмы в `config-git-forks-and-merges`, `bug-diagnosis-loop` | [yellow-hammer/dev-rules](https://github.com/yellow-hammer/dev-rules) | **CC BY-SA 4.0** | ✓ только пересказ, сверено 12.11.2026 |
| словарь вердиктов в `two-axis-code-review` | [trailofbits/skills](https://github.com/trailofbits/skills) | **CC BY-SA 4.0** | ✓ только пересказ, сверено 12.11.2026 |
| нотация эскиза формы в `managed-forms-guide`, `forms-skills-and-visual-check` | [crimsongoldteam/md_design](https://github.com/crimsongoldteam/md_design) | **MIT** | идея, нотация своя |
| хук `plugin/hooks/scan-inbound.py` — категории признаков подмены инструкций | [lasso-security/claude-hooks](https://github.com/lasso-security/claude-hooks) | **MIT** | только идея и категории; признаки и код свои |
| идеи в `edt-mcp-pitfalls`, `designer-batch-runs`, `capture-knowledge`, `vertical-task-slicing` | [comol/ai_rules_1c](https://github.com/comol/ai_rules_1c) | формальной лицензии нет | только идеи, дословных заимствований нет |
| идеи в `coding-discipline`, `naming-and-module-design` и ролях `architect-1c`, `programmer-1c`, `tester-1c`, `reviewer-1c` — проверяемое ядро и тонкие переходники, тест первым, фазы ревью архитектуры | [unclebob/swarm-forge](https://github.com/unclebob/swarm-forge) | формальной лицензии нет | только идеи, пересказ своими словами под 1С; сопоставление — `plugin/docs/sources/external-skills-review.md` |

## Открытый репозиторий Only1S/1c-ai-core

Каждый выпуск кладётся в открытый репозиторий снимком того же содержимого, что в закрытом канале, со следующими отличиями (12.11.2026):

1. Скилл `1c-standards` входит в снимок по решению владельца 13.11.2026 (ADR-0014). У источника нет лицензии — риск публикации владелец принял на себя.
2. Скилл `1c-platform-kb` входит в снимок по решению владельца 13.11.2026 (ADR-0014): конспекты ИТС и методичек своими словами, дословных текстов нет.
3. Пересказы под CC BY-SA 4.0 (`config-git-forks-and-merges`, `bug-diagnosis-loop`, `two-axis-code-review`) сверены 12.11.2026: общих цепочек из 8 слов подряд с текстами источников нет (yellow-hammer/dev-rules — 70 файлов, trailofbits/skills — 209 файлов).
4. Указание авторов MIT-компонентов сохранено (эта страница и шапки файлов).
5. Закрытый движок обфускации `obfuscator.zip` к открытому Release не прикладывается.
6. README открытого репозитория — свой, короткий (`README.public.md` мастера).

<details><summary>Для мастера ядра (dev_core)</summary>

В мастере те же файлы лежат в `.claude/skills/` и `docs/`; плагин собирается из них при выпуске (`tools/release/build-plugin.py`). Клоны поставщиков в папке `tools/` (`cc-1c-skills`, `1c-ssl-skills`, `claude-code-bsl-lsp`, `loga`, `1c-formsserver`) и загрузки владельца в `tools/downloads/` в git мастера не входят и в канал не публикуются. Наши правки стороннего кода — `docs/safety/vendor-patch-registry.md`.

</details>
