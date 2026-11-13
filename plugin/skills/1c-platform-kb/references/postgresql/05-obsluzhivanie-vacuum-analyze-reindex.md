# Регламентное обслуживание PostgreSQL под 1С: VACUUM, ANALYZE, autovacuum, REINDEX, раздувание

> **Официальные тексты по теме** (конспекты документации ИТС 8.3.27 и методических статей ИТС, составлены по полным текстам): `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`. Статья писалась до получения доступа к закрытой документации: там, где ниже сказано «документация закрыта», «не прочитано» или стоит ⚠, сверяйтесь с этими конспектами — при расхождении правы они.

> Статус: проверено независимой сверкой 19.10.2026: синтаксис и опции `VACUUM`/`ANALYZE`/`REINDEX`/`CLUSTER`, ключи `vacuumdb`/`reindexdb`/`pg_amcheck`/`pg_checksums`, умолчания и контекст параметров автоочистки, заморозки, WAL и bgwriter, блокировки, фазы и колонки представлений `pg_stat_progress_*` и `pg_stat_*`, тексты сообщений о wraparound и журнала автоочистки, утверждения «с версии N» — сверены с документацией PostgreSQL 18, исходными текстами документации и кода веток 14–18 и примечаниями к выпускам 16–19; рекомендации для 1С — с приложением K и описаниями модулей документации «PostgreSQL для 1С» 16 (совпадает с 18) и с конспектами ИТС в `../its-metod/` и `../its-docs/`; pg_repack — с его документацией и исходным кодом 1.5.3, пакеты — с packages.ubuntu.com и индексами `repo.postgrespro.ru` (ветка `1c-16` — на 19.10.2026). Исправлено 16 ошибок, закрыто 2 пометки «⚠» (ещё 2 оговорки «по памяти рецензента» подтверждены исходным кодом; одна потерянная пометка «⚠» восстановлена в разделе 8.4); на сервере не проверялось. Ранее, 10.10.2026, выполнена программная сверка имён, умолчаний и колонок — расхождений не было. Для «PostgreSQL для 1С» 16 пути, служба и журнал сервера оговорены в условных обозначениях ниже.

> Область: регулярное обслуживание баз «1С:Предприятие 8» в PostgreSQL на Ubuntu Server — MVCC и «мёртвые» строки, `VACUUM`/`ANALYZE`/autovacuum, `REINDEX`, `vacuumdb`/`reindexdb`, `pg_repack`, `CLUSTER`, оценка раздувания (bloat), заморозка и переполнение счётчика транзакций, специфика 1С (временные таблицы и системный каталог, длинные транзакции, реструктуризация, «Тестирование и исправление», итоги регистров), рост WAL и места на диске, контрольные точки, целостность данных, готовые скрипты и расписание | Версии: PostgreSQL 14–18 (документация сверена по 18.6; 19 — на 19.10.2026 только RC 1 от 15.10.2026), сборки «PostgreSQL с патчем от 1С» 14–18, Postgres Pro Standard / «Postgres Pro 1С» 17–18 (документация 18.6.2), Ubuntu Server 22.04 / 24.04 / 26.04 LTS, платформа 1С 8.3.27 и 8.5.x | Актуальность: 2026-10-10

Условные обозначения (те же, что в остальных статьях раздела `kb/postgresql`):

- `NN` — старший номер версии PostgreSQL (14…18). В примерах чаще всего `18` — подставляйте свой.
- «Debian-раскладка» — пакеты на `postgresql-common` (архив Ubuntu, PGDG, deb-пакеты «PostgreSQL с патчем от 1С»): бинарники `/usr/lib/postgresql/NN/bin`, данные `/var/lib/postgresql/NN/main`, конфигурация `/etc/postgresql/NN/main/`, журнал `/var/log/postgresql/postgresql-NN-main.log`, служба `postgresql@NN-main`.
- «Раскладка Postgres Pro» — `/opt/pgpro/<редакция>-NN/bin`, данные `/var/lib/pgpro/<редакция>-NN/data`, служба `postgrespro-<редакция>-NN` (редакция `1c` или `std`).
- Бесплатная сборка «PostgreSQL для 1С» от Postgres Professional, ветка 16 (пакеты `postgrespro-1c-16*`), устроена по раскладке Postgres Pro: программы `/opt/pgpro/1c-16/bin` (при быстрой установке `pg-wrapper` добавляет ссылки на них в `PATH`), данные `/var/lib/pgpro/1c-16/data`, служба `postgrespro-1c-16`. Журнал сервера у неё не в `/var/log/postgresql/`, а в `/var/lib/pgpro/1c-16/data/log/postgresql-<дата>_<время>.log` (`pg-setup initdb` включает `logging_collector`) — в командах `grep` по журналу подставляйте этот путь. Контрольные суммы страниц `pg-setup initdb` включает по умолчанию. Раздел K.3 приложения K (настройки для 1С) в документации ветки 16 совпадает с текстом ветки 18 [PGPro]. Подробности — `kb/guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`.
- **[PG]** — документация PostgreSQL (postgresql.org/docs/18), **[1С]** — материалы ИТС и документация платформы, **[PGPro]** — документация Postgres Pro, **[практика]** — приёмы сообщества, не закреплённые официально.
- «⚠ не подтверждено» — первоисточник прочитать не удалось; утверждение основано на памяти автора или практике сообщества. Проверяйте на стенде.
- Все SQL-команды выполняются от суперпользователя: `sudo -u postgres psql -d имя_базы`. Имена таблиц 1С в PostgreSQL — в нижнем регистре (`_document123`, `_accumrgt4567`).

Связанные статьи: `kb/postgresql/02-postgresql-conf-tyuning-dlya-1c.md` (параметры `postgresql.conf`), `kb/postgresql/03-administrirovanie-psql-i-utility.md` (psql, службы, пути), `kb/linux/05-systemd-sluzhby-zhurnaly-cron.md` (cron и таймеры systemd), `kb/linux/07-diski-fs-lvm.md` (место на диске), `kb/its-docs/adm-gl06-administrirovanie-ib-p3.md` (тестирование и исправление ИБ).

## Кратко — 20 главных фактов и команд

1. PostgreSQL хранит несколько версий строки (MVCC). `UPDATE` и `DELETE` не стирают старую версию, а помечают её «мёртвой». Место освобождает только `VACUUM` (ручной или автоматический). Если он не успевает, таблицы и индексы «раздуваются» [PG].
2. **Autovacuum нельзя выключать.** Это прямая рекомендация и [1С], и [PGPro]: `autovacuum = on`, `autovacuum_max_workers` = от «ядра/4» до «ядра/2», но не меньше 4, `autovacuum_naptime = 20s`.
3. Обычный `VACUUM` не блокирует работу пользователей (блокировка `SHARE UPDATE EXCLUSIVE`) и не возвращает место операционной системе — он делает его пригодным для повторного использования. `VACUUM FULL` возвращает место, но берёт `ACCESS EXCLUSIVE` и требует свободного места примерно на размер таблицы [PG].
4. Пороги автоочистки по умолчанию: очистка при `50 + 0.2 × число_строк` мёртвых строк, анализ при `50 + 0.1 × число_строк` изменений. Для таблицы на 10 млн строк это 2 млн мёртвых строк — для 1С слишком поздно; коэффициенты обычно снижают [практика].
5. Ночной регламент одной командой: `sudo -u postgres vacuumdb --all --analyze --jobs=4 --skip-locked`.
6. Только статистика: `vacuumdb --all --analyze-only --jobs=4`. После `pg_restore` — `vacuumdb --analyze-in-stages имя_базы`.
7. Перестроить индексы без остановки работы: `REINDEX (VERBOSE) TABLE CONCURRENTLY public._document123;` или `reindexdb --concurrently --jobs=2 имя_базы`. После сбоя остаются недействительные индексы `…_ccnew` — их нужно удалить.
8. Кто мешает очистке: длинные транзакции и сеансы `idle in transaction`, забытые подготовленные транзакции, неактивные слоты репликации. Ищутся по `pg_stat_activity` (`backend_xmin`), `pg_prepared_xacts`, `pg_replication_slots` [PG].
9. Самые «грязные» таблицы: `SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;`.
10. Ход очистки: представление `pg_stat_progress_vacuum`; `VACUUM FULL` и `CLUSTER` — `pg_stat_progress_cluster`; `REINDEX` — `pg_stat_progress_create_index` [PG].
11. Счётчик транзакций 32-битный. Контроль: `SELECT datname, age(datfrozenxid) FROM pg_database;`. Норма — до ~200 млн (`autovacuum_freeze_max_age`). При остатке менее 40 млн сервер пишет предупреждения, при остатке менее 3 млн перестаёт выдавать новые XID — доступно только чтение [PG].
12. 1С массово создаёт временные таблицы. Каждая оставляет записи в `pg_class`, `pg_attribute`, `pg_type`, `pg_depend`, `pg_statistic`. Если автоочистку держит длинная транзакция, системный каталог раздувается до гигабайтов и тормозит всё [практика]. Модуль `fasttrun` (функция `fasttruncate`) как раз нужен, чтобы `pg_class` не рос [PGPro].
13. Autovacuum не обрабатывает временные таблицы [PG]. Долгоживущий сеанс со старой временной таблицей может удерживать `datfrozenxid` базы [практика].
14. Оценка раздувания: точно — расширение `pgstattuple` (`pgstattuple_approx`, `pgstatindex`), приблизительно — запросы по статистике (раздел 9).
15. `pg_repack` — «онлайн `VACUUM FULL`»: пакет `postgresql-NN-repack`, расширение `pg_repack` в базе, таблице нужен первичный ключ или уникальный индекс по `NOT NULL`-колонкам, свободное место — около двух размеров таблицы с индексами.
16. Реструктуризация при обновлении конфигурации 1С создаёт новые таблицы и переносит в них данные. Нужно свободное место примерно на размер изменяемых таблиц, а после неё — `ANALYZE` (у новых таблиц нет статистики) [практика].
17. «Тестирование и исправление» в конфигураторе — это средство исправления логики базы 1С (ссылочная целостность, итоги, структура). Оно требует монопольного режима и не заменяет `VACUUM`/`ANALYZE`; «Сжатие таблиц» в клиент-серверном варианте недоступно [1С].
18. `pg_wal` растёт по трём основным причинам: неактивный слот репликации, сломанная архивация (`archive_command`), слишком большой `wal_keep_size`. Удалять файлы из `pg_wal` вручную нельзя. Диагностика: `pg_replication_slots`, `pg_stat_archiver` [PG].
19. Контрольные точки: с PostgreSQL 17 счётчики в `pg_stat_checkpointer` (`num_timed`, `num_requested`), в 14–16 — в `pg_stat_bgwriter`. Если запрошенных точек больше, чем плановых, увеличивайте `max_wal_size` [PG].
20. Контрольные суммы страниц в PostgreSQL 18 включены по умолчанию (`initdb`), раньше их включали явно; в «PostgreSQL для 1С» 16 их включает `pg-setup initdb` (раздел 14.1). Проверка: `SHOW data_checksums;`, офлайн — `pg_checksums --check`, логическая проверка — `pg_amcheck`, проверка читаемости — `pg_dump … > /dev/null` [PG].

## 1. MVCC, «мёртвые» строки и раздувание

### 1.1. Как это устроено

- У каждой версии строки есть служебные поля `xmin` (транзакция, создавшая версию) и `xmax` (транзакция, удалившая её).
- `INSERT` создаёт версию. `DELETE` только проставляет `xmax`. `UPDATE` = «удалить старую версию + вставить новую».
- Версия становится «мёртвой», когда её не видит ни один действующий снимок данных. До этого момента удалить её нельзя.
- Читатели не блокируют писателей и наоборот [PG], но плата за это — мусор, который кто-то должен убирать.
- В индексах на каждую версию строки есть своя запись. Исключение — HOT-обновление (heap-only tuple): если не менялась ни одна индексированная колонка и на той же странице есть свободное место, новая версия не получает записей в индексах, а промежуточные версии вычищаются при обычном обращении к странице, без `VACUUM` [PG]. Доля HOT видна в `pg_stat_user_tables` (`n_tup_hot_upd` против `n_tup_upd`).

Вспомогательные структуры, которые ведёт `VACUUM`:

| Структура | Файл | Назначение |
|---|---|---|
| Карта свободного места (FSM) | `<relfilenode>_fsm` | где в таблице есть место для новых версий строк |
| Карта видимости (VM) | `<relfilenode>_vm` | какие страницы целиком видимы всем (`all-visible`) и целиком заморожены (`all-frozen`); нужна для index-only scan и чтобы `VACUUM` пропускал чистые страницы |

### 1.2. Что такое раздувание (bloat)

Раздувание — это место в файлах таблицы или индекса, занятое мёртвыми версиями и пустотами.

- Обычный `VACUUM` помечает место свободным, но файл не уменьшает. Исключение: если полностью пустые страницы оказались в конце файла и удалось быстро взять исключительную блокировку, «хвост» отрезается [PG].
- Таблица, выросшая из-за массового `UPDATE`/`DELETE`, остаётся большой: свободное место внутри неё будет заполняться новыми строками, но диску оно не вернётся.
- В B-дереве полностью пустые страницы используются повторно, а полупустые остаются полупустыми. При характере нагрузки «вставили диапазон ключей — потом почти весь удалили» индекс разрастается; документация прямо рекомендует периодически перестраивать такие индексы [PG].

Чем плохо раздувание для 1С:

- последовательные чтения и сканирования индексов читают больше страниц;
- в кеше (`shared_buffers`, страничный кеш ОС) лежит мусор вместо данных;
- дольше идут резервное копирование на уровне файлов и восстановление;
- раздутый системный каталог замедляет планирование каждого запроса и создание временных таблиц (раздел 11.1).

### 1.3. Что не даёт VACUUM убрать мусор

`VACUUM` удаляет только те версии, которые не нужны самому старому снимку в кластере («горизонт xmin»). Горизонт удерживают:

| Причина | Где смотреть | Что делать |
|---|---|---|
| Длинная транзакция или сеанс `idle in transaction` | `pg_stat_activity`: `xact_start`, `state`, `age(backend_xid)`, `age(backend_xmin)` | завершить транзакцию; `pg_terminate_backend(pid)` |
| Подготовленная (двухфазная) транзакция | `pg_prepared_xacts`: `age(transaction)` | `COMMIT PREPARED` / `ROLLBACK PREPARED` |
| Слот репликации | `pg_replication_slots`: `age(xmin)`, `age(catalog_xmin)` | починить потребителя или удалить слот |
| Реплика с `hot_standby_feedback = on` | на реплике — длинные запросы | завершить запрос на реплике; параметр может вызывать раздувание на основном сервере [PG] |
| Длинный `pg_dump` | в `pg_stat_activity` — `application_name = 'pg_dump'` | запускать очистку после окончания дампа |

Все держатели горизонта одним запросом (добавлен рецензентом по колонкам из документации [PG]; на стенде не выполнялся — проверьте перед включением в мониторинг):

```sql
SELECT 'сеанс' AS kind, pid::text AS id, age(backend_xmin) AS xmin_age,
       coalesce(state, '') || ': ' || left(query, 60) AS info
  FROM pg_stat_activity
 WHERE backend_xmin IS NOT NULL
UNION ALL
SELECT 'подготовленная транзакция', gid, age(transaction), owner || '@' || database
  FROM pg_prepared_xacts
UNION ALL
SELECT 'слот репликации', slot_name::text, greatest(age(xmin), age(catalog_xmin)),
       slot_type || ', active=' || active::text
  FROM pg_replication_slots
 WHERE xmin IS NOT NULL OR catalog_xmin IS NOT NULL
UNION ALL
SELECT 'реплика (hot_standby_feedback)', application_name, age(backend_xmin), client_addr::text
  FROM pg_stat_replication
 WHERE backend_xmin IS NOT NULL
ORDER BY xmin_age DESC NULLS LAST
LIMIT 10;
```

Первая строка результата — тот, кто сейчас мешает `VACUUM` сильнее всех. Запрос показывает держателей во всём кластере, а не только в текущей базе, и это намеренно:

- слот репликации держит горизонт сразу во всех базах;
- сеанс и подготовленная транзакция держат горизонт прежде всего в своей базе и в общих (shared) таблицах каталога;
- Уточнено 19.10.2026 по исходному коду PostgreSQL 18 (`src/backend/storage/ipc/procarray.c`, функция `GetSnapshotData()`: `xmin` снимка считается по XID всех выполняющихся транзакций кластера без отбора по базе и записывается как `xmin` сеанса): **пишущая** транзакция, получившая XID в соседней базе того же сервера, косвенно сдерживает очистку и в вашей базе — новые снимки в ней не могут иметь `xmin` новее этого XID, а горизонт базы считается по `xmin` её сеансов. На стенде не проверялось. Поэтому «забытую» транзакцию ищите по всему серверу, а не только в базе, где растёт мусор.

В отчёте `VACUUM (VERBOSE)` это видно так (PostgreSQL 15+):

```
tuples: 0 removed, 100000 remain, 50000 are dead but not yet removable
removable cutoff: 754, which was 1200345 XIDs old when operation ended
```

Строка `are dead but not yet removable` с большим числом и «старый» `removable cutoff` означают, что горизонт кто-то держит. В версии 14 вывод ручного `VACUUM (VERBOSE)` был другим — `N dead row versions cannot be removed yet, oldest xmin: …`, а в журнале автоочистки — `tuples: … are dead but not yet removable, oldest xmin: …` (строки `removable cutoff` ещё не было; сверено по `vacuumlazy.c` веток 14 и 15).

## 2. VACUUM

### 2.1. Синтаксис (PostgreSQL 18) [PG]

```sql
VACUUM [ ( option [, ...] ) ] [ table_and_columns [, ...] ]

-- option:
--   FULL [ boolean ]
--   FREEZE [ boolean ]
--   VERBOSE [ boolean ]
--   ANALYZE [ boolean ]
--   DISABLE_PAGE_SKIPPING [ boolean ]
--   SKIP_LOCKED [ boolean ]
--   INDEX_CLEANUP { AUTO | ON | OFF }
--   PROCESS_MAIN [ boolean ]
--   PROCESS_TOAST [ boolean ]
--   TRUNCATE [ boolean ]
--   PARALLEL integer
--   SKIP_DATABASE_STATS [ boolean ]
--   ONLY_DATABASE_STATS [ boolean ]
--   BUFFER_USAGE_LIMIT size
-- table_and_columns:
--   [ ONLY ] table_name [ * ] [ ( column_name [, ...] ) ]
```

Общие правила:

- `VACUUM` нельзя выполнять внутри блока транзакции (`BEGIN … COMMIT`).
- Без списка таблиц обрабатывается вся текущая база (все таблицы, на которые есть право).
- Нужна привилегия `MAINTAIN` на таблицу (PostgreSQL 17+; есть роль `pg_maintain`) либо права владельца таблицы, владельца базы или суперпользователя. Чужие таблицы молча пропускаются.
- Список колонок допустим только вместе с `ANALYZE`.
- Булеву опцию можно писать без значения: `VACUUM (VERBOSE, ANALYZE)` равно `VACUUM (VERBOSE true, ANALYZE true)`.

### 2.2. Опции

| Опция | Что делает | Умолчание | С какой версии |
|---|---|---|---|
| `FULL` | переписывает таблицу в новый файл, возвращает место ОС; `ACCESS EXCLUSIVE`, нужно место под копию | off | — |
| `FREEZE` | агрессивная заморозка: как `vacuum_freeze_min_age = 0` и `vacuum_freeze_table_age = 0`; с `FULL` избыточна | off | — |
| `VERBOSE` | подробный отчёт по каждой таблице на уровне `INFO` | off | — |
| `ANALYZE` | после очистки собрать статистику планировщика | off | — |
| `DISABLE_PAGE_SKIPPING` | не пропускать страницы по карте видимости; только при подозрении на повреждение VM | off | 9.6 |
| `SKIP_LOCKED` | не ждать блокировку, а пропустить занятую таблицу | off | 12 |
| `INDEX_CLEANUP` | `AUTO` — пропускать очистку индексов, если мёртвых строк очень мало; `ON` — чистить всегда; `OFF` — не чистить индексы (быстрее, для аварийной заморозки) | `AUTO` | 12 (`AUTO` — 14) |
| `PROCESS_MAIN` | обрабатывать основную таблицу; `false` — только TOAST | true | 16 |
| `PROCESS_TOAST` | обрабатывать TOAST-таблицу; с `FULL` обязателен | true | 14 |
| `TRUNCATE` | отрезать пустые страницы в конце файла и вернуть их ОС; `false` — избежать кратковременной `ACCESS EXCLUSIVE` | true (если не выключен параметр хранения таблицы `vacuum_truncate`, а в 18 — и одноимённый параметр сервера, появившийся в 18) | 12 |
| `PARALLEL n` | чистить индексы в `n` фоновых процессах; `0` — запретить | выбирается автоматически | 13 |
| `SKIP_DATABASE_STATS` | не обновлять `datfrozenxid` базы в конце команды (ускоряет серию вызовов) | off | 16 |
| `ONLY_DATABASE_STATS` | только обновить `datfrozenxid`; список таблиц пуст | off | 16 |
| `BUFFER_USAGE_LIMIT` | размер кольца буферов (128 kB…16 GB, `0` — без кольца) | `vacuum_buffer_usage_limit` (2MB в 17+, 256kB в 16) | 16 |

Пояснения:

- **`INDEX_CLEANUP AUTO`.** Очистка индексов — самая дорогая часть. Если мёртвых строк совсем мало, PostgreSQL её пропускает. В документации число не названо; порог проверен по исходному коду (`src/backend/access/heap/vacuumlazy.c`, ветка `REL_18_STABLE`): `#define BYPASS_THRESHOLD_PAGES 0.02` — очистка индексов пропускается, если страниц с мёртвыми указателями меньше 2 % страниц таблицы **и** список мёртвых указателей занимает меньше 32 МБ. В отчёте `VACUUM (VERBOSE)` и в журнале автоочистки это видно по строке `index scan bypassed: …` (вместо `index scan needed: …`). Пропуск безвреден: мёртвые указатели останутся до следующей очистки.
- **`PARALLEL`.** Параллельно обрабатываются только индексы: один процесс на индекс, только индексы больше `min_parallel_index_scan_size`, нужно минимум два таких индекса. Число процессов = минимум из числа подходящих индексов, значения `PARALLEL` и `max_parallel_maintenance_workers` (по умолчанию 2). С `FULL` не сочетается. На `ANALYZE` не влияет. Autovacuum параллельный режим не использует.
- **Память.** Список мёртвых строк хранится в памяти объёмом `maintenance_work_mem` (для autovacuum — `autovacuum_work_mem`). Если памяти не хватает, индексы сканируются несколько раз (`index_vacuum_count` в `pg_stat_progress_vacuum` больше 1). До PostgreSQL 16 включительно использовалось не больше 1 ГБ; в 17 ограничение снято и структура стала компактнее [PG, release notes 17].
- **`VACUUM` для GIN-индексов** заодно разбирает список отложенных вставок (pending list).

### 2.3. Блокировки [PG]

| Команда | Блокировка таблицы | Что блокирует |
|---|---|---|
| `VACUUM` (без `FULL`) | `SHARE UPDATE EXCLUSIVE` | другой `VACUUM`/`ANALYZE`, `CREATE INDEX`, `REINDEX CONCURRENTLY`, `ALTER TABLE`; чтение и запись не блокирует |
| усечение «хвоста» в конце `VACUUM` | кратковременно `ACCESS EXCLUSIVE` | всё; если блокировку быстро взять не удалось, усечение пропускается |
| `ANALYZE` | `SHARE UPDATE EXCLUSIVE` | то же, что обычный `VACUUM` |
| `VACUUM FULL`, `CLUSTER` | `ACCESS EXCLUSIVE` | всё, включая `SELECT` |
| `REINDEX` (без `CONCURRENTLY`) | запись в таблицу блокируется, на сам индекс — `ACCESS EXCLUSIVE` | `INSERT`/`UPDATE`/`DELETE`; чтения, которым нужен этот индекс (планировщик берёт `ACCESS SHARE` на все индексы таблицы, поэтому на практике ждут почти все запросы) |
| `REINDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` | только DDL и другой `VACUUM`; работа пользователей продолжается |
| `ALTER TABLE … SET (autovacuum_…)`, `SET STATISTICS` | `SHARE UPDATE EXCLUSIVE` | DDL и `VACUUM` |

`SHARE UPDATE EXCLUSIVE` конфликтует сама с собой: на одной таблице одновременно работает только одна операция обслуживания.

### 2.4. Примеры

```sql
-- Очистка и статистика одной таблицы с отчётом
VACUUM (VERBOSE, ANALYZE) public._accumrgt4567;

-- Вся база: очистка + статистика (долго на больших базах — лучше vacuumdb -j)
VACUUM (ANALYZE);

-- Не ждать занятые таблицы, индексы чистить в 4 процесса
VACUUM (SKIP_LOCKED, PARALLEL 4) public._inforg8901;

-- Заморозка перед «заморозкой» базы в архив или при приближении wraparound
VACUUM (FREEZE, VERBOSE) public._document123;

-- Аварийная заморозка: без индексов и без усечения — максимально быстро
VACUUM (FREEZE, INDEX_CLEANUP OFF, TRUNCATE false, VERBOSE) public._document123;

-- Только TOAST-таблица (большие значения: хранилища, двоичные данные)
VACUUM (PROCESS_MAIN false, VERBOSE) public.config;

-- Вернуть место ОС (монопольно! нужно место под копию таблицы)
VACUUM (FULL, VERBOSE, ANALYZE) public._inforg8901;
```

Разовое изменение параметров на время сеанса:

```sql
SET maintenance_work_mem = '2GB';       -- больше памяти под список мёртвых строк
SET vacuum_cost_delay = 0;              -- ручной VACUUM и так не тормозится (умолчание 0)
VACUUM (VERBOSE, ANALYZE) public._accumrg4560;
```

Чтобы, наоборот, притормозить ручную очистку днём:

```bash
sudo -u postgres env PGOPTIONS='-c vacuum_cost_delay=2ms -c vacuum_cost_limit=1000' \
  vacuumdb --analyze --table=public._accumrg4560 buh
```

`PGOPTIONS` — переменная libpq: её содержимое передаётся серверу как параметры сеанса, поэтому приём работает с `psql`, `vacuumdb`, `reindexdb`.

### 2.5. Наблюдение за ходом

```sql
SELECT p.pid, p.datname, p.relid::regclass AS tbl, p.phase,
       round(100.0 * p.heap_blks_scanned  / nullif(p.heap_blks_total, 0), 1) AS scanned_pct,
       round(100.0 * p.heap_blks_vacuumed / nullif(p.heap_blks_total, 0), 1) AS vacuumed_pct,
       p.index_vacuum_count,
       a.backend_type, now() - a.query_start AS runtime, left(a.query, 60) AS query
FROM pg_stat_progress_vacuum p
JOIN pg_stat_activity a USING (pid);
```

`relid::regclass` даёт имя только для таблиц текущей базы; для чужой базы будет число.

Фазы [PG]: `initializing` → `scanning heap` → `vacuuming indexes` → `vacuuming heap` → (повтор, если не хватило памяти) → `cleaning up indexes` → `truncating heap` → `performing final cleanup`.

Колонки `pg_stat_progress_vacuum` в PostgreSQL 18: `pid`, `datid`, `datname`, `relid`, `phase`, `heap_blks_total`, `heap_blks_scanned`, `heap_blks_vacuumed`, `index_vacuum_count`, `max_dead_tuple_bytes`, `dead_tuple_bytes`, `num_dead_item_ids`, `indexes_total`, `indexes_processed`, `delay_time`. В 14–16 вместо `max_dead_tuple_bytes`/`num_dead_item_ids` были `max_dead_tuples`/`num_dead_tuples`, а колонок `indexes_*` и `dead_tuple_bytes` не было. `delay_time` заполняется только при `track_cost_delay_timing = on` (PostgreSQL 18).

## 3. ANALYZE и статистика планировщика

### 3.1. Что делает ANALYZE [PG]

```sql
ANALYZE [ ( option [, ...] ) ] [ table_and_columns [, ...] ]
-- option: VERBOSE [ boolean ] | SKIP_LOCKED [ boolean ] | BUFFER_USAGE_LIMIT size
```

- Читает случайную выборку строк и записывает в `pg_statistic` (читать удобнее через представление `pg_stats`): долю `NULL`, среднюю ширину, число различных значений (`n_distinct`), список самых частых значений (MCV), гистограмму, корреляцию физического и логического порядка.
- Обновляет `pg_class.reltuples` и `relpages`. Эти же поля обновляют `VACUUM` и `CREATE INDEX`.
- Блокировка — `SHARE UPDATE EXCLUSIVE`: работе пользователей не мешает.
- Размер выборки определяется наибольшей «целью статистики» среди колонок. Это `300 × цель` строк, то есть 30 000 строк при цели 100 и 300 000 строк при цели 1000. В документации множитель не назван; проверено по исходному коду (`src/backend/commands/analyze.c`, функция `std_typanalyze`: `stats->minrows = 300 * stats->attstattarget;`). Поэтому `ANALYZE` даже огромной таблицы идёт секунды-минуты, а не часы — и поэтому же на таблицах в сотни миллионов строк оценка `n_distinct` бывает грубой.
- Пустая таблица статистику не обновляет: остаётся прежняя.
- Привилегия — `MAINTAIN` (17+) или владелец.

```sql
ANALYZE;                                         -- вся база
ANALYZE (VERBOSE) public._document123;           -- одна таблица с отчётом
ANALYZE public._inforg8901 (_fld8902rref);       -- одна колонка
ANALYZE (SKIP_LOCKED);                           -- не ждать занятые таблицы
```

Когда статистика устаревает, планировщик ошибается в оценке числа строк и выбирает плохой план: вложенные циклы по миллионам строк, последовательное чтение вместо индекса. Для 1С это типичная причина «вчера отчёт работал 5 секунд, сегодня 20 минут» после массовой загрузки или перепроведения.

### 3.2. Цель статистики: default_statistics_target

- `default_statistics_target` — число элементов в списке MCV и корзин гистограммы. Умолчание 100, диапазон 1–10000 [PG].
- Больше цель — точнее оценки для неравномерных распределений, но дольше `ANALYZE` и планирование.
- Для отдельной колонки:

```sql
ALTER TABLE public._accumrg4560 ALTER COLUMN _fld4561rref SET STATISTICS 1000;
ANALYZE public._accumrg4560;
-- вернуть умолчание:
ALTER TABLE public._accumrg4560 ALTER COLUMN _fld4561rref SET STATISTICS -1;
-- задать число различных значений вручную, если ANALYZE ошибается:
ALTER TABLE public._accumrg4560 ALTER COLUMN _fld4561rref SET (n_distinct = 50000);
```

- [практика] Для баз 1С в сотни гигабайт значение поднимают глобально до 500–1000. Официальных рекомендаций [1С] и [PGPro] на этот счёт нет. Менять стоит после замера конкретных проблемных запросов, а не «на всякий случай».
- Настройки колонок пропадают, когда платформа пересоздаёт таблицу при реструктуризации (раздел 11.5).

### 3.3. Расширенная статистика [PG]

По умолчанию планировщик считает условия по разным колонкам независимыми. Для связанных колонок это даёт заниженные оценки. Объект расширенной статистики описывает связь:

```sql
CREATE STATISTICS [ [ IF NOT EXISTS ] имя ]
    [ ( вид [, ...] ) ]                -- ndistinct | dependencies | mcv
    ON колонка_или_(выражение), колонка_или_(выражение) [, ...]
    FROM таблица;

CREATE STATISTICS st_doc123_org_date (dependencies, ndistinct, mcv)
    ON _fld124rref, _date_time FROM public._document123;
ANALYZE public._document123;           -- без ANALYZE объект пуст
```

- `dependencies` — функциональные зависимости (одна колонка определяет другую); работает для условий равенства с константой и `IN`.
- `ndistinct` — число различных комбинаций; улучшает оценки `GROUP BY` по нескольким колонкам.
- `mcv` — частые комбинации значений.
- Описания лежат в `pg_statistic_ext`, данные — в `pg_statistic_ext_data`. Для оценок соединений таблиц расширенная статистика не используется.
- [практика] В базах 1С применяется редко: объект удаляется вместе с таблицей при реструктуризации, а имена колонок (`_fldNNN`) меняются между базами. Имеет смысл как точечное лекарство для конкретного тяжёлого запроса.

### 3.4. Статистика и временные таблицы 1С

- Autovacuum не видит временные таблицы, значит, и не анализирует их [PG].
- Современные версии платформы 1С сами выполняют `ANALYZE` для временных таблиц после заполнения. Поэтому модуль `online_analyze` «с современными версиями 1С использовать не рекомендуется» [PGPro]; статья [1С] в общем случае тоже рекомендует `online_analyze.enable = off`. Учтите: у самого модуля умолчание — `on` (документация модуля в «PostgreSQL для 1С» 16): если библиотека загружена (`shared_preload_libraries`), а `online_analyze.enable` не задан явно, модуль работает.
- `plantuner.fix_empty_table = on` (модуль `plantuner` в `shared_preload_libraries`) обнуляет оценку размера для только что созданной пустой таблицы: без него планировщик считает новую таблицу намного больше, чем она есть [PGPro].
- Подробности параметров — в `02-postgresql-conf-tyuning-dlya-1c.md`.

### 3.5. Когда запускать ANALYZE вручную

| Ситуация | Команда |
|---|---|
| После `pg_restore`, загрузки `.dt`, `ibcmd infobase restore` | `vacuumdb --analyze-in-stages база` или `vacuumdb --analyze-only -j 4 база` |
| После реструктуризации (обновление конфигурации) | `vacuumdb --analyze-only -j 4 база` |
| После массового перепроведения, свёртки, загрузки данных | `vacuumdb --analyze -j 4 база` |
| После сбоя сервера (счётчики статистики обнулены, раздел 4.7) | `vacuumdb --all --analyze -j 4` |
| После `pg_upgrade` до версий 17 и ниже | `vacuumdb --all --analyze-in-stages` |
| После `pg_upgrade` на 18 | обычная статистика переносится (кроме расширенной и счётчиков накопительной статистики). Документация `pg_upgrade` 18 предписывает две команды подряд: `vacuumdb --all --analyze-in-stages --missing-stats-only` (быстро собрать то, чего нет), затем `vacuumdb --all --analyze-only` (обновить счётчики, по которым autovacuum решает, когда чистить и анализировать). Обе можно ускорить ключом `--jobs` |

`pg_dump` версии 18 умеет выгружать статистику (`--statistics`), но по умолчанию этого не делает (`--no-statistics` — умолчание); документация всё равно советует `ANALYZE` после восстановления [PG].

Прикладные планы в PostgreSQL отдельно чистить не нужно: подготовленные запросы перепланируются автоматически, когда меняется структура объектов или обновляется их статистика [PG]. Аналога `DBCC FREEPROCCACHE` из регламента для MS SQL здесь нет.

## 4. Autovacuum

### 4.1. Как работает [PG]

- Требует `autovacuum = on` и `track_counts = on` (оба включены по умолчанию).
- **Launcher** (один процесс `autovacuum launcher`) раз в `autovacuum_naptime` запускает по одному рабочему процессу в каждой базе. Если баз N, запуски распределяются: в среднем один запуск каждые `naptime / N`.
- **Worker** (`autovacuum worker`) подключается к базе, просматривает счётчики изменений каждой таблицы и выполняет `VACUUM` и/или `ANALYZE` там, где превышен порог. Одновременно работает не больше `autovacuum_max_workers` процессов на весь кластер.
- Временные таблицы не обрабатываются. Секционированные таблицы как целое не обрабатываются (только секции).
- Если другой сеанс запрашивает блокировку, конфликтующую с `SHARE UPDATE EXCLUSIVE` (например, `ALTER TABLE` при реструктуризации 1С), autovacuum **уступает и прерывается**. Исключение — очистка для защиты от переполнения счётчика: в `pg_stat_activity` её запрос оканчивается на `(to prevent wraparound)`, и она не прерывается.
- Регулярный запуск команд, берущих `SHARE UPDATE EXCLUSIVE` на ту же таблицу (например, частый ручной `ANALYZE`), может не дать автоочистке завершиться никогда [PG].

### 4.2. Пороги запуска [PG]

```
порог очистки  = min( autovacuum_vacuum_max_threshold,
                      autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor × reltuples )
порог вставок  = autovacuum_vacuum_insert_threshold
                 + autovacuum_vacuum_insert_scale_factor × reltuples × доля_незамороженных_страниц
порог анализа  = autovacuum_analyze_threshold + autovacuum_analyze_scale_factor × reltuples
```

- С порогом очистки сравнивается число мёртвых строк (`n_dead_tup`).
- С порогом вставок — число вставленных с прошлой очистки строк (`n_ins_since_vacuum`); такая очистка нужна таблицам «только вставка» ради карты видимости и заморозки (PostgreSQL 13+). Множитель «доля незамороженных» появился в 18.
- С порогом анализа — число изменённых строк с прошлого анализа (`n_mod_since_analyze`).
- `autovacuum_vacuum_max_threshold` (PostgreSQL 18) ограничивает порог сверху для гигантских таблиц.
- Независимо от порогов таблица очищается принудительно, если возраст её `relfrozenxid` превысил `autovacuum_freeze_max_age` — даже при `autovacuum = off`.

Пример для таблицы на 10 млн строк:

| Настройка | Порог очистки | Порог анализа |
|---|---|---|
| По умолчанию (0.2 / 0.1) | 2 000 050 мёртвых строк | 1 000 050 изменений |
| 0.05 / 0.02 | 500 050 | 200 050 |
| 0.01 / 0.005 | 100 050 | 50 050 |

### 4.3. Параметры (PostgreSQL 18) [PG]

| Параметр | Умолчание | Применение | Смысл |
|---|---|---|---|
| `autovacuum` | `on` | reload | включить launcher |
| `autovacuum_worker_slots` | `16` | restart | (18+) сколько слотов зарезервировано под рабочие процессы |
| `autovacuum_max_workers` | `3` | reload в 18 (в пределах `autovacuum_worker_slots`); restart в 14–17 | максимум одновременных рабочих процессов |
| `autovacuum_naptime` | `1min` | reload | пауза между обходами одной базы |
| `autovacuum_vacuum_threshold` | `50` | reload | база порога очистки, строк |
| `autovacuum_vacuum_scale_factor` | `0.2` | reload | доля таблицы в пороге очистки |
| `autovacuum_vacuum_max_threshold` | `100000000` | reload | (18+) верхняя граница порога; `-1` — без границы |
| `autovacuum_vacuum_insert_threshold` | `1000` | reload | база порога по вставкам; `-1` — отключить |
| `autovacuum_vacuum_insert_scale_factor` | `0.2` | reload | доля таблицы в пороге по вставкам |
| `autovacuum_analyze_threshold` | `50` | reload | база порога анализа |
| `autovacuum_analyze_scale_factor` | `0.1` | reload | доля таблицы в пороге анализа |
| `autovacuum_vacuum_cost_delay` | `2ms` | reload | пауза при исчерпании лимита стоимости; `-1` — брать `vacuum_cost_delay` |
| `autovacuum_vacuum_cost_limit` | `-1` | reload | лимит стоимости; `-1` — брать `vacuum_cost_limit` (200) |
| `autovacuum_freeze_max_age` | `200000000` | restart | возраст XID, при котором очистка принудительна |
| `autovacuum_multixact_freeze_max_age` | `400000000` | restart | то же для мультитранзакций |
| `autovacuum_work_mem` | `-1` | reload | память на процесс; `-1` — брать `maintenance_work_mem` (64MB по умолчанию) |
| `log_autovacuum_min_duration` | `10min` | reload | журналировать действия автоочистки дольше указанного; `0` — все, `-1` — ничего |
| `vacuum_cost_page_hit` / `_miss` / `_dirty` | `1` / `2` / `20` | сессия | «цена» страницы из кеша / с диска / испачканной |
| `vacuum_cost_limit` | `200` | сессия | накопленная стоимость, после которой процесс засыпает |
| `vacuum_cost_delay` | `0` | сессия | пауза для ручного `VACUUM` (0 — не тормозить) |
| `track_cost_delay_timing` | `off` | — | (18+) учитывать время сна в отчётах и `pg_stat_progress_vacuum.delay_time` |

Точные значения, границы и контекст на своём сервере:

```sql
SELECT name, setting, unit, context, boot_val
FROM pg_settings
WHERE name LIKE 'autovacuum%' OR name LIKE 'vacuum%' OR name = 'log_autovacuum_min_duration'
ORDER BY name;
```

### 4.4. Ограничение скорости (cost-based delay)

Рабочий процесс копит «стоимость» прочитанных и изменённых страниц. Накопив `cost_limit`, он засыпает на `cost_delay`. Лимит **делится между всеми работающими процессами**: общий ввод-вывод не зависит от их числа. Процессы, обслуживающие таблицы с собственными `autovacuum_vacuum_cost_delay`/`_cost_limit`, в балансировке не участвуют [PG].

Оценка «потолка» при умолчаниях (лимит 200, пауза 2 мс → до 500 циклов в секунду, 100 000 единиц в секунду на всех):

| Случай | Страниц в секунду | Примерно |
|---|---|---|
| все страницы читаются с диска (цена 2) | 50 000 | ~390 МБ/с чтения |
| все страницы изменяются (цена 20) | 5 000 | ~39 МБ/с записи |

Вывод: добавление рабочих процессов без увеличения `autovacuum_vacuum_cost_limit` очистку **не ускоряет** — тот же лимит делится на большее число процессов. Растёт только число одновременно обслуживаемых таблиц.

### 4.5. Тюнинг под нагрузку 1С

Официальный минимум [1С][PGPro] (совпадает в статье ИТС «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2», ред. 19.06.2025, и в приложении K документации Postgres Pro):

```ini
autovacuum = on                       # не выключать: база растёт, производительность падает
autovacuum_max_workers = 4            # от «ядра/4» до «ядра/2», но не меньше 4
autovacuum_naptime = 20s              # слишком большая пауза — таблицы не успевают очищаться
```

Чего в официальных текстах нет — порогов (`scale_factor`), лимита стоимости, памяти. Ниже [практика] — отправная точка для OLTP-базы 1С на SSD, которую нужно проверять наблюдением (раздел 4.7):

```ini
# /etc/postgresql/18/main/conf.d/50-autovacuum.conf   (Postgres Pro: postgresql.conf в каталоге данных)
autovacuum_vacuum_scale_factor = 0.02         # очистка при ~2 % мёртвых строк вместо 20 %
autovacuum_analyze_scale_factor = 0.01        # анализ при ~1 % изменений вместо 10 %
autovacuum_vacuum_insert_scale_factor = 0.05  # таблицы «только вставка»
autovacuum_vacuum_cost_limit = 2000           # SSD: в 10 раз больше умолчания; для HDD 400–800
autovacuum_vacuum_cost_delay = 2ms            # умолчание с версии 12
autovacuum_work_mem = 512MB                   # × autovacuum_max_workers — учитывать в бюджете памяти
log_autovacuum_min_duration = 0               # на время настройки — журналировать всё; потом, например, 30s
```

Применение и проверка:

```bash
sudo systemctl reload postgresql@18-main          # Postgres Pro: sudo systemctl reload postgrespro-1c-NN (ветка 16 — postgrespro-1c-16)
sudo -u postgres psql -c "SELECT name, setting, pending_restart FROM pg_settings WHERE name LIKE 'autovacuum%';"
```

Замечания:

- `autovacuum_max_workers` в 14–17 меняется только перезапуском. В 18 достаточно `reload`, но значение не может превышать `autovacuum_worker_slots` (тот меняется перезапуском).
- Память: каждый рабочий процесс может занять `autovacuum_work_mem` (или `maintenance_work_mem`, если `-1`). В 17–18 при `maintenance_work_mem = 4GB` и 8 процессах это до 32 ГБ — поэтому `autovacuum_work_mem` лучше задать явно. В 14–16 список мёртвых строк автоочистки ограничен 1 ГБ на процесс (документация 16, `autovacuum_work_mem`; ограничение снято в 17 — release notes 17), то есть в том же примере до 8 ГБ.
- Много баз на сервере (десятки): launcher обходит их по очереди, и при малом числе рабочих процессов до «своей» базы очередь доходит редко. Здесь важнее число процессов и маленький `autovacuum_naptime`.
- Слишком агрессивные пороги на слабом диске дают постоянный фоновый ввод-вывод. Критерий — не «чтобы autovacuum работал реже», а «чтобы `n_dead_tup` у горячих таблиц не рос от запуска к запуску».

### 4.6. Настройки на уровне таблицы

```sql
-- Горячая таблица итогов: чистить по фиксированному числу строк, а не по доле
ALTER TABLE public._accumrgt4567 SET (
    autovacuum_vacuum_scale_factor  = 0,
    autovacuum_vacuum_threshold     = 20000,
    autovacuum_analyze_scale_factor = 0,
    autovacuum_analyze_threshold    = 20000
);

-- Своя (более высокая) скорость очистки для одной таблицы; такая таблица не участвует в балансировке
ALTER TABLE public._inforg8901 SET (autovacuum_vacuum_cost_limit = 4000, autovacuum_vacuum_cost_delay = 1);

-- TOAST-часть таблицы настраивается отдельно, с префиксом toast.
ALTER TABLE public.config SET (toast.autovacuum_vacuum_scale_factor = 0.05);

-- Посмотреть и сбросить
SELECT c.oid::regclass, c.reloptions FROM pg_class c WHERE c.reloptions IS NOT NULL AND c.relkind = 'r';
ALTER TABLE public._accumrgt4567 RESET (autovacuum_vacuum_scale_factor, autovacuum_vacuum_threshold,
                                        autovacuum_analyze_scale_factor, autovacuum_analyze_threshold);
```

Доступные параметры хранения: `autovacuum_enabled`, `autovacuum_vacuum_threshold`, `autovacuum_vacuum_scale_factor`, `autovacuum_vacuum_max_threshold` (18), `autovacuum_vacuum_insert_threshold`, `autovacuum_vacuum_insert_scale_factor`, `autovacuum_analyze_threshold`, `autovacuum_analyze_scale_factor`, `autovacuum_vacuum_cost_delay`, `autovacuum_vacuum_cost_limit`, `autovacuum_freeze_min_age`, `autovacuum_freeze_max_age`, `autovacuum_freeze_table_age`, `autovacuum_multixact_freeze_*`, `log_autovacuum_min_duration`, `vacuum_index_cleanup`, `vacuum_truncate`, `vacuum_max_eager_freeze_failure_rate` (18), а также `fillfactor` (список сверен 19.10.2026 с описанием параметров хранения `CREATE TABLE` в документации 18). Команда берёт `SHARE UPDATE EXCLUSIVE` — пользователям не мешает [PG].

Ограничения именно для 1С [практика]:

- Настройки хранятся в `pg_class.reloptions` конкретной таблицы. Когда платформа пересоздаёт таблицу (реструктуризация, «Реструктуризация таблиц» в тестировании и исправлении, загрузка `.dt`), настройки **теряются**. Держите их в скрипте и применяйте заново после каждого обновления конфигурации.
- Номера таблиц (`_accumrgt4567`) в разных базах разные. Соответствие «объект метаданных → таблица» даёт функция встроенного языка `ПолучитьСтруктуруХраненияБазыДанных()`.
- На таблицы системного каталога (`pg_class`, `pg_attribute`…) эти настройки поставить нельзя без `allow_system_table_mods` — для каталога работают только глобальные пороги.
- `ALTER TABLE … SET (autovacuum_enabled = off)` для таблиц 1С не применяйте: принудительная очистка «от wraparound» всё равно придёт, но уже по раздутой таблице.

### 4.7. Мониторинг

Состояние таблиц (колонки `pg_stat_user_tables` [PG]: `n_live_tup`, `n_dead_tup`, `n_mod_since_analyze`, `n_ins_since_vacuum`, `last_vacuum`, `last_autovacuum`, `last_analyze`, `last_autoanalyze`, `vacuum_count`, `autovacuum_count`, `analyze_count`, `autoanalyze_count`; в 18 добавлены `total_vacuum_time`, `total_autovacuum_time`, `total_analyze_time`, `total_autoanalyze_time`):

```sql
-- Топ по мёртвым строкам и расстояние до порога автоочистки (без учёта настроек отдельных таблиц)
SELECT s.relname,
       s.n_live_tup, s.n_dead_tup,
       round(100.0 * s.n_dead_tup / nullif(s.n_live_tup + s.n_dead_tup, 0), 1) AS dead_pct,
       round(current_setting('autovacuum_vacuum_threshold')::numeric
             + current_setting('autovacuum_vacuum_scale_factor')::numeric * greatest(c.reltuples, 0)) AS av_threshold,
       s.n_mod_since_analyze,
       s.last_autovacuum, s.last_autoanalyze, s.autovacuum_count,
       pg_size_pretty(pg_total_relation_size(s.relid)) AS total_size
FROM pg_stat_user_tables s
JOIN pg_class c ON c.oid = s.relid
ORDER BY s.n_dead_tup DESC
LIMIT 30;

-- Большие таблицы, которые автоочистка давно не трогала
SELECT relname, n_live_tup, n_dead_tup,
       greatest(last_vacuum, last_autovacuum)   AS last_vac,
       greatest(last_analyze, last_autoanalyze) AS last_an
FROM pg_stat_user_tables
WHERE n_live_tup > 100000
ORDER BY greatest(last_vacuum, last_autovacuum) NULLS FIRST
LIMIT 30;

-- Что делает автоочистка сейчас
SELECT pid, datname, now() - xact_start AS runtime, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE backend_type = 'autovacuum worker'
ORDER BY xact_start;
```

Признаки проблем:

| Наблюдение | Вероятная причина | Действие |
|---|---|---|
| все `autovacuum_max_workers` процессов заняты постоянно | не хватает скорости | поднять `autovacuum_vacuum_cost_limit`, затем число процессов |
| `n_dead_tup` растёт, `last_autovacuum` свежий | горизонт xmin держит транзакция или слот (раздел 1.3) | найти и устранить держателя |
| `last_autovacuum` пуст у горячей таблицы | порог слишком высок; либо очистку всё время прерывают блокировки | снизить порог для таблицы; искать в журнале `canceling autovacuum task` |
| `last_autoanalyze` старый, планы «плывут» | порог анализа высок для большой таблицы | снизить `autovacuum_analyze_scale_factor` |
| в журнале `autovacuum: dropping orphan temp table "база.pg_temp_N.имя"` | остались временные таблицы сеанса, который завершился, не удалив их (сбой, нехватка `max_locks_per_transaction`); автоочистка сама их удаляет | единично — норма; массово — см. раздел 11.1. Точный текст проверен по `autovacuum.c` (PostgreSQL 18). Формулировка `found orphan temp table`, которая встречается в старых статьях, относится к версиям 9.6 и старше (уточнено 19.10.2026 по `autovacuum.c` веток 9.6, 10 и 11: в 9.6 есть обе формулировки, в 10 и новее — только `dropping`) — в журналах 14–18 искать нужно `dropping orphan temp table` |

Журнал: при `log_autovacuum_min_duration = 0` каждая автоочистка пишет отчёт, совпадающий с выводом `VACUUM (VERBOSE)`:

```bash
sudo grep -E 'automatic (vacuum|analyze)|canceling autovacuum' /var/log/postgresql/postgresql-18-main.log | tail -n 50
```

На что смотреть в записи `automatic vacuum of table "база.схема.таблица"` (формат PostgreSQL 15+; запись многострочная, поэтому для чтения целиком удобнее `grep -A 12 'automatic vacuum of table'`):

| Строка записи | Что означает |
|---|---|
| `index scans: N` | сколько раз пришлось пройти по индексам; больше 1 — не хватило `autovacuum_work_mem`/`maintenance_work_mem` |
| `tuples: X removed, Y remain, Z are dead but not yet removable` | `Z` заметно больше нуля — горизонт xmin кто-то держит (раздел 1.3) |
| `removable cutoff: …, which was N XIDs old when operation ended` | большой `N` — тот же признак: очистка работала по «старому» горизонту |
| `index scan needed: …` / `index scan bypassed: …` / `index scan not needed: …` | чистились ли индексы; `bypassed` — сработал порог `INDEX_CLEANUP AUTO` (раздел 2.2), `bypassed by failsafe` — аварийный режим (раздел 10.1) |
| `avg read rate: … MB/s, avg write rate: … MB/s` | фактическая скорость; если она мала, а очистка идёт часами — упирается в `cost_limit` (раздел 4.4) |
| `system usage: CPU: …, elapsed: … s` | полная длительность |

Если параметр `log_autovacuum_min_duration` отличен от `-1`, в журнал попадают и пропуски автоочистки из-за конфликта блокировок или удалённой таблицы [PG]. В PostgreSQL 19 (на 19.10.2026 — RC 1) журналирование автоанализа вынесено в отдельный параметр `log_autoanalyze_min_duration`, а `log_autovacuum_min_duration` управляет только очисткой (сверено 19.10.2026 по примечаниям к выпуску 19).

Счётчики статистики и сбои [PG]:

- При штатной остановке статистика сохраняется в каталоге `pg_stat`. После нештатной (сбой, `immediate`-остановка, восстановление из базовой копии, PITR) **все счётчики обнуляются**. Autovacuum «забывает», сколько мусора накопилось. После любого аварийного перезапуска выполните `vacuumdb --all --analyze`.
- То же делает `SELECT pg_stat_reset();` — документация после него прямо рекомендует `ANALYZE` всей базы. Не вызывайте его «для чистоты эксперимента» на рабочей базе.

### 4.8. Почему autovacuum нельзя отключать

1. Мёртвые строки перестают убираться — таблицы и индексы растут, запросы замедляются. Вернуть место потом можно только `VACUUM FULL`/`pg_repack`.
2. Статистика перестаёт обновляться — планировщик строит планы по устаревшим данным.
3. Не обновляется карта видимости — index-only scan вырождается в обычное чтение таблицы.
4. Растёт возраст транзакций. Принудительная очистка «от wraparound» всё равно запустится (даже при `autovacuum = off`), но в самый неудобный момент, на всех таблицах сразу, и её не прервёт блокировка.
5. Системный каталог базы 1С (десятки тысяч таблиц плюс поток временных) без автоочистки раздувается за часы.
6. Это прямо написано в рекомендациях [1С] и [PGPro].

«Autovacuum мешает ночной обработке» лечится не отключением, а настройкой скорости (`cost_limit`), окна ручного обслуживания и поиском того, кто держит горизонт.

## 5. Что рекомендуют 1С и Postgres Professional: состав и периодичность

### 5.1. Что есть в официальных источниках

**[1С], ИТС.** В разделе «Методическая поддержка → Администрирование → СУБД → PostgreSQL» (https://its.1c.ru/db/metod8dev/browse/13/-1/3199/3258/3259/3263) на 10.10.2026 девять статей: настройки PostgreSQL (часть 1 — 5825, часть 2 — 5866), установка на Debian (5822), две статьи по PostgreSQL 9.6 — «Методика сборки дистрибутива СУБД PostgreSQL 9.6 c патчами для работы с 1С:Предприятие» (5942, от 31.05.2018) и «Настройка непрерывного архивирования и восстановления на момент времени в PostgreSQL 9.6» (5947, от 15.05.2018), отказоустойчивый кластер Patroni + etcd + HAProxy (5971), «Расширение auto_dump» (6031, от 25.06.2025) и «Расширение pg_wait_sampling» (6032, от 25.06.2025) сборки 1С, «Отложенное создание файлов временных таблиц в PostgreSQL с патчем от 1С» — параметр `enable_temp_rd_buffers` (6035, от 25.09.2025). Названия и даты сверены рецензентом 10.10.2026 по тексту страниц (страницы открыты без подписки; кодировка windows-1251). **Отдельной статьи «Регламентные операции на уровне СУБД» для PostgreSQL там нет.** Такая статья есть только для MS SQL Server (https://its.1c.ru/db/metod8dev/content/5837/hdoc, ред. 18.11.2022). Её состав — фактический эталон того, что 1С считает обязательным регламентом СУБД:

| Регламент для MS SQL Server [1С] | Команда в статье | Периодичность по статье [1С] | Аналог в PostgreSQL |
|---|---|---|---|
| Обновление статистик | `exec sp_msforeachtable N'UPDATE STATISTICS ? WITH FULLSCAN'` | **не реже одного раза в день**; таблицы не блокирует; оптимальную частоту подбирают опытным путём, для часто меняющихся таблиц — отдельная, более частая процедура | `ANALYZE` / `vacuumdb --analyze-only`; постоянно — автоанализ |
| Очистка процедурного кеша | `DBCC FREEPROCCACHE` | сразу после каждого обновления статистики, с той же частотой | не требуется: планы перестраиваются сами при обновлении статистики (раздел 3.5) |
| Дефрагментация индексов | `sp_msforeachtable N'DBCC INDEXDEFRAG (<имя базы данных>, ''?'')'` | **не реже одного раза в неделю**, при высокой изменчивости данных — до одного раза в день; таблицы не блокирует | прямого аналога нет; мёртвые записи индексов убирает `VACUUM` |
| Реиндексация таблиц | `sp_msforeachtable N'DBCC DBREINDEX (''?'')'` | **не реже одного раза в неделю**, во время минимальной нагрузки (блокирует таблицы на всё время работы); после реиндексации дефрагментация не нужна | `REINDEX` / `REINDEX CONCURRENTLY` / `reindexdb` |
| Контроль выполнения регламентных процедур | журнал плана обслуживания (View History) | регулярно | журнал скриптов, `pg_stat_user_tables.last_*`, журнал сервера |

Периодичность подтверждена: текст статьи прочитан рецензентом 10.10.2026 (страница публичная, кодировка windows-1251). Статья прямо называет все три срока: статистика — не реже раза в день, дефрагментация индексов — не реже раза в неделю, реиндексация — не реже раза в неделю и в период минимальной нагрузки. Там же общий принцип, который переносится на PostgreSQL без изменений: выполнение регламентных процедур должно быть автоматизировано, а их своевременность и правильность нужно регулярно контролировать. Оговорка статьи про страничные блокировки (`ALLOW_PAGE_LOCKS`) при дефрагментации начиная с платформы 8.3.22 относится только к MS SQL Server.

Второй официальный источник [1С] — документация платформы, «Клиент-серверный вариант. Руководство администратора», раздел 5.5.8 «Выполнение различных административных задач» (конспект — `kb/its-docs/cs-gl05-administrirovanie-klastera-p3.md`). Там перечислены действия на стороне СУБД, которые не меняют структуру базы данных, но нужны «для работоспособности и приемлемой производительности» и допустимы для всех поддерживаемых СУБД, **включая PostgreSQL**: проверка целостности, реиндексация, дефрагментация, реорганизация, создание резервной копии, очистка процедурного кеша, сбор статистики. Команд и периодичности для PostgreSQL документация не даёт — только сам перечень. Практический вывод: `VACUUM`, `ANALYZE`, `REINDEX`, `pg_amcheck` и резервное копирование средствами СУБД относятся к действиям, которые 1С прямо называет допустимыми. Изменение структуры данных (таблиц, колонок и индексов, созданных платформой) в этот перечень не входит. `pg_repack` в документации 1С не упоминается: по смыслу это «реорганизация», но он временно создаёт в базе свои таблицы и триггеры — применяйте его только вне обновления конфигурации (раздел 8.4).

Для PostgreSQL прямые числовые требования [1С] по обслуживанию есть только в статье 5866: `autovacuum = on` с предупреждением, что выключение ведёт к росту базы и серьёзной деградации производительности, `autovacuum_max_workers = CPU cores/4..2 но не меньше 4`, `autovacuum_naptime = 20s` (сверено по тексту статьи 10.10.2026).

**[PGPro].** Приложение K «Настройка Postgres Pro для решений 1С» (версии 17 и 18; в документации «PostgreSQL для 1С» ветки 16 — «Настройка PostgreSQL для решений 1С», раздел K.3 тот же) повторяет те же три параметра автоочистки и больше про регламент не говорит. Общая глава «Регламентные задачи обслуживания» даёт принципы:

- частый обычный `VACUUM` лучше редкого `VACUUM FULL`; `VACUUM FULL` по возможности избегать;
- если автоочистка отключена, типовая схема — `VACUUM` всей базы раз в сутки в период низкой нагрузки, а интенсивно меняющихся таблиц — чаще;
- отключать автоочистку имеет смысл только при крайне предсказуемой нагрузке;
- `ANALYZE` всей базы дёшев (читается выборка); колонкам с быстро «уезжающими» значениями (даты) статистику нужно обновлять чаще;
- B-деревья с характером «вставили — почти всё удалили» стоит периодически перестраивать; `REINDEX CONCURRENTLY` обычно предпочтительнее;
- если таблицу регулярно очищают целиком — использовать `TRUNCATE`, а не `DELETE` + `VACUUM`.

### 5.2. Сводный регламент для базы 1С

| Операция | Периодичность | Как | Основание |
|---|---|---|---|
| Автоочистка и автоанализ | постоянно | `autovacuum = on`, пороги по разделу 4.5 | [1С][PGPro] |
| `VACUUM ANALYZE` всех баз | ежедневно ночью, после резервного копирования | `vacuumdb --all --analyze --jobs=N --skip-locked` | [PG] «типовая схема»; [1С] для MS SQL: статистика — не реже раза в день (статья 5837); сбор статистики назван допустимой задачей и для PostgreSQL (документация платформы, 5.5.8) |
| `ANALYZE` после массовых изменений | по событию | `vacuumdb --analyze-only -j N база` | [PG] |
| Контроль возраста XID | ежедневно (мониторинг) | `age(datfrozenxid)` | [PG] |
| Контроль длинных транзакций, слотов, архивации | ежедневно (мониторинг) | запросы разделов 1.3 и 12 | [PG] |
| Отчёт о раздувании таблиц и индексов | еженедельно | запросы раздела 9 | [практика] |
| `REINDEX CONCURRENTLY` раздутых индексов | еженедельно (небольшие базы — целиком; большие — выборочно по отчёту) | `reindexdb --concurrently` / точечный `REINDEX` | [PG]: периодически; [1С] для MS SQL: реиндексация — не реже раза в неделю (статья 5837). Для PostgreSQL срок от 1С не установлен — перенос «раз в неделю» остаётся [практика] |
| Контроль размера системного каталога | еженедельно | запрос раздела 11.1 | [практика] |
| `VACUUM FULL` / `pg_repack` | только по необходимости | раздел 8 | [PG]: не для регулярного использования |
| Проверка целостности (`pg_amcheck`, пробный `pg_dump`, пробное восстановление копии) | ежемесячно | раздел 14 | [практика] |
| Пересчёт итогов, сдвиг границы итогов (уровень 1С) | ежемесячно после закрытия периода | средствами конфигурации | [1С], раздел 11.6 |
| «Тестирование и исправление» | не регламент, а ремонт: при ошибках | конфигуратор, монопольно | [1С], раздел 11.7 |

## 6. REINDEX и reindexdb

### 6.1. Синтаксис и формы [PG]

```sql
REINDEX [ ( option [, ...] ) ] { INDEX | TABLE | SCHEMA } [ CONCURRENTLY ] name
REINDEX [ ( option [, ...] ) ] { DATABASE | SYSTEM } [ CONCURRENTLY ] [ name ]
-- option: CONCURRENTLY [ boolean ] | TABLESPACE new_tablespace | VERBOSE [ boolean ]
```

| Форма | Что перестраивает |
|---|---|
| `INDEX имя` | один индекс |
| `TABLE имя` | все индексы таблицы и её TOAST-таблицы |
| `SCHEMA имя` | все индексы схемы |
| `DATABASE [имя]` | все индексы текущей базы, **кроме системного каталога** (так с версии 16; в 14–15 — включая каталог) |
| `SYSTEM [имя]` | только индексы системного каталога текущей базы |

- `DATABASE` и `SYSTEM` работают только с текущей базой; имя необязательно с версии 16 (в 14–15 обязательно — release notes 16), но если указано — должно совпадать с текущей.
- `SCHEMA`, `DATABASE`, `SYSTEM` нельзя выполнять в блоке транзакции. `CONCURRENTLY` — тоже нельзя.
- Права: `MAINTAIN` на таблицу (17+), владелец; для `SCHEMA`/`DATABASE` — владелец или роль `pg_maintain`.

Когда нужен `REINDEX`:

1. Индекс раздут (раздел 9).
2. Индекс повреждён (ошибки чтения, результат `amcheck`).
3. Остался недействительный индекс после неудачного `CREATE INDEX CONCURRENTLY`/`REINDEX CONCURRENTLY`.
4. Изменён параметр хранения индекса (`fillfactor`).
5. После смены версии библиотеки сортировки (glibc/ICU) при обновлении ОС — порядок строк мог измениться, текстовые индексы нужно перестроить.

### 6.2. Обычный режим и CONCURRENTLY

| | `REINDEX` | `REINDEX … CONCURRENTLY` |
|---|---|---|
| Блокировки | запись в таблицу запрещена; индекс под `ACCESS EXCLUSIVE` | `SHARE UPDATE EXCLUSIVE`: чтение и запись идут |
| Скорость | быстрее | медленнее: два прохода по таблице и ожидание чужих транзакций |
| Место на диске | новый индекс рядом со старым до конца операции | то же (старый и новый существуют одновременно) |
| В транзакции | `INDEX`/`TABLE` — можно | нельзя |
| Системный каталог | можно | нельзя (`REINDEX SYSTEM CONCURRENTLY` не поддерживается; при `DATABASE CONCURRENTLY` каталог пропускается) |
| Индексы ограничений-исключений | можно | пропускаются |
| При сбое | откат без следов | остаётся недействительный индекс |

Особенности `CONCURRENTLY`:

- На одной таблице одновременно идёт только одно конкурентное построение.
- Операция ждёт завершения всех транзакций, начавшихся до неё и способных видеть таблицу. Длинная транзакция 1С (закрытие месяца) заставит `REINDEX` ждать часами. Фазы ожидания видны в `pg_stat_progress_create_index.phase` (`waiting for writers before build`, `waiting for old snapshots` и т.д.).
- Сам длинный `REINDEX`, как любая долгая транзакция, мешает `VACUUM` убирать мусор в других таблицах [PG].

Недействительные индексы после сбоя:

```sql
SELECT n.nspname, c.relname AS index_name, t.relname AS table_name,
       pg_size_pretty(pg_relation_size(c.oid)) AS size
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT i.indisvalid;
```

- Суффикс `_ccnew` — недостроенный новый индекс: `DROP INDEX CONCURRENTLY public."имя_ccnew";` и повторить `REINDEX`.
- Суффикс `_ccold` — старый индекс, который не успели удалить (новый уже работает): просто удалить.
- К суффиксу может добавляться номер (`_ccnew1`). Недействительный индекс не используется запросами, но обновляется при каждой записи — оставлять его нельзя.

### 6.3. Примеры

```sql
REINDEX (VERBOSE) INDEX CONCURRENTLY public._accumrgt4567_1;
REINDEX (VERBOSE) TABLE CONCURRENTLY public._document123;
REINDEX (VERBOSE) DATABASE CONCURRENTLY buh;          -- подключившись к базе buh
REINDEX (VERBOSE) SYSTEM buh;                          -- каталог; только в окне обслуживания
REINDEX (TABLESPACE fast_ssd) TABLE CONCURRENTLY public._inforg8901;   -- перестроить с переносом
```

Ход выполнения:

```sql
SELECT pid, datname, relid::regclass AS tbl, index_relid::regclass AS idx, command, phase,
       blocks_done, blocks_total, tuples_done, tuples_total
FROM pg_stat_progress_create_index;
```

Аварийный случай — повреждены индексы системного каталога и к базе не подключиться обычным образом [PG]:

```bash
sudo -u postgres env PGOPTIONS='-P' psql buh        # -P: не использовать системные индексы
# в psql:  REINDEX DATABASE buh;   (в 16+ для каталога — REINDEX SYSTEM buh;)
```

### 6.4. reindexdb [PG]

```
reindexdb [connection-option...] [option...]
          [ -S | --schema схема ] ... [ -t | --table таблица ] ... [ -i | --index индекс ] ...
          [ -s | --system ] [ dbname | -a | --all ]
```

| Ключ | Назначение |
|---|---|
| `-a`, `--all` | все базы кластера |
| `-d база`, `--dbname=база` | одна база (можно строку подключения) |
| `--concurrently` | использовать `REINDEX … CONCURRENTLY` |
| `-i индекс`, `--index=…` | только указанный индекс (ключ можно повторять) |
| `-t таблица`, `--table=…` | только индексы указанной таблицы |
| `-S схема`, `--schema=…` | только указанная схема |
| `-s`, `--system` | только системный каталог; несовместим с `-j` |
| `-j N`, `--jobs=N` | N параллельных соединений; нужен запас `max_connections` |
| `--tablespace=имя` | перестроить в другом табличном пространстве |
| `-e`, `--echo` | показывать отправляемые команды |
| `-v`, `--verbose` | подробный вывод |
| `-q`, `--quiet` | без сообщений о ходе |
| `--maintenance-db=база` | к какой базе подключаться за списком баз при `-a` (по умолчанию `postgres`, затем `template1`) |
| `-h`, `-p`, `-U`, `-w`, `-W` | хост (или каталог сокета), порт, роль, не спрашивать/спросить пароль |

```bash
# Все индексы одной базы, без блокировки работы, в 2 потока
sudo -u postgres reindexdb --concurrently --jobs=2 --dbname=buh

# Индексы одной таблицы, с показом команд
sudo -u postgres reindexdb --concurrently -e -t public._document123 buh

# Конкретные индексы
sudo -u postgres reindexdb --concurrently -i public._accumrgt4567_1 -i public._accumrgt4567_2 buh

# Системный каталог (блокирует работу; в окне обслуживания)
sudo -u postgres reindexdb --system buh

# Все базы кластера
sudo -u postgres reindexdb --all --concurrently --jobs=2
```

- С версии 17 `reindexdb -j` умеет параллельно обрабатывать и список `--index`, если индексы относятся к разным таблицам [PG, release notes 17].
- Для Postgres Pro путь к утилите — `/opt/pgpro/1c-NN/bin/reindexdb` (если пакет не добавил её в `PATH`).
- Полная переиндексация большой базы порождает WAL объёмом порядка суммарного размера индексов. Проверьте место в `pg_wal`, архиве WAL и на репликах.

## 7. vacuumdb [PG]

```
vacuumdb [connection-option...] [option...] [ -t | --table таблица [ (колонка [,...]) ] ] ... [ dbname | -a | --all ]
vacuumdb [connection-option...] [option...] [ -n | --schema схема ] ... [ dbname | -a | --all ]
vacuumdb [connection-option...] [option...] [ -N | --exclude-schema схема ] ... [ dbname | -a | --all ]
```

Обёртка над SQL-командой `VACUUM`; разницы с запуском из psql нет, но есть параллельность по таблицам и обход всех баз.

| Ключ | Назначение |
|---|---|
| `-a`, `--all` | все базы кластера |
| `-d база` | одна база |
| `-z`, `--analyze` | `VACUUM` + `ANALYZE` |
| `-Z`, `--analyze-only` | только `ANALYZE` |
| `--analyze-in-stages` | только `ANALYZE` в три прохода с растущей целью статистики (1 → 10 → умолчание): быстро получить хоть какую-то статистику |
| `--missing-stats-only` | (18+) анализировать только объекты без статистики; только вместе с `-Z` или `--analyze-in-stages`; нужен суперпользователь |
| `-j N`, `--jobs=N` | N параллельных соединений (по таблицам) |
| `-P N`, `--parallel=N` | `VACUUM (PARALLEL N)` — параллельная обработка индексов одной таблицы |
| `-f`, `--full` | `VACUUM FULL` (монопольные блокировки!) |
| `-F`, `--freeze` | агрессивная заморозка |
| `-t таблица[(колонки)]` | только указанная таблица; колонки — только с `-z`/`-Z` |
| `-n схема` / `-N схема` | только схема / кроме схемы |
| `--skip-locked` | пропускать занятые таблицы |
| `--min-xid-age=N` | только таблицы с возрастом XID не меньше N |
| `--min-mxid-age=N` | только таблицы с возрастом мультитранзакций не меньше N |
| `--no-index-cleanup` / `--force-index-cleanup` | `INDEX_CLEANUP OFF` / `ON` |
| `--no-truncate` | не отрезать пустой «хвост» |
| `--no-process-main` / `--no-process-toast` | пропустить основную таблицу / TOAST |
| `--disable-page-skipping` | не доверять карте видимости |
| `--buffer-usage-limit=размер` | размер кольца буферов |
| `-e`, `-v`, `-q` | показать команды / подробно / тихо |
| `--maintenance-db=база` | база для получения списка баз при `-a` |

```bash
# Ночной регламент: все базы, очистка + статистика, 4 потока, занятые таблицы пропустить
sudo -u postgres vacuumdb --all --analyze --jobs=4 --skip-locked

# Только статистика одной базы (после реструктуризации или загрузки)
sudo -u postgres vacuumdb --analyze-only --jobs=4 buh

# После pg_restore: сначала грубая статистика, затем полная
sudo -u postgres vacuumdb --analyze-in-stages buh

# Одна таблица и одна колонка (скобки экранируются кавычками)
sudo -u postgres vacuumdb --analyze --verbose --table='public._document123(_date_time)' buh

# Таблицы, которым пора замораживаться: возраст больше 150 млн транзакций
sudo -u postgres vacuumdb --all --freeze --min-xid-age=150000000 --jobs=4

# Очень большая таблица: индексы в 4 процесса
sudo -u postgres vacuumdb --analyze --parallel=4 --table=public._accumrg4560 buh
```

Подводные камни:

- Таблица ключей соответствует версии 18. На старых версиях части ключей нет: `--no-process-main` и `--buffer-usage-limit` появились в 16, `--missing-stats-only` — в 18. Точный список для своей версии — `vacuumdb --help`.
- `-j N` открывает N соединений в каждой базе; `-j` вместе с `-f` может привести к взаимоблокировкам на системном каталоге [PG].
- `--analyze-in-stages` на базе с **уже существующей** нормальной статистикой временно ухудшает планы (первые проходы заменяют её грубой). Применять только после восстановления или `pg_upgrade` [PG].
- `vacuumdb -f` на рабочей базе 1С — это остановка работы: каждая таблица по очереди берётся под `ACCESS EXCLUSIVE`.
- Родственная утилита `clusterdb` — обёртка над `CLUSTER`; для баз 1С практического применения почти не имеет.

## 8. Возврат места: VACUUM FULL, CLUSTER, pg_repack

### 8.1. Когда это вообще нужно

Обычный `VACUUM` достаточен, пока таблица живёт в стабильном режиме: освобождённое место тут же занимается новыми строками. Полная перезапись оправдана, когда:

- удалили или переписали большую часть таблицы разово (свёртка базы, удаление помеченных, очистка регистра сведений, истории данных) и это место больше не понадобится;
- таблица раздулась из-за аварии (сутки с зависшей транзакцией) и теперь в разы больше нормы;
- раздут системный каталог (раздел 11.1);
- место на диске заканчивается.

Документация: `FULL` «не рекомендуется для регулярного использования» [PG].

### 8.2. VACUUM FULL

- Переписывает таблицу в новый файл и перестраивает все её индексы. Старые файлы удаляются по завершении.
- Блокировка `ACCESS EXCLUSIVE` на всё время: не работают даже `SELECT`.
- Нужно свободное место: размер «живых» данных таблицы плюс её индексов.
- Ход — в `pg_stat_progress_cluster` (фазы `initializing`, `seq scanning heap`, `swapping relation files`, `rebuilding index`, `performing final cleanup`; фазы `index scanning heap`, `sorting tuples` и `writing new heap` бывают только у `CLUSTER` — сверено по документации 18 и `heapam_handler.c`).
- Порождает WAL объёмом с новую таблицу и индексы.

```sql
SET maintenance_work_mem = '2GB';
VACUUM (FULL, VERBOSE, ANALYZE) public._inforg8901;
```

Для базы 1С выполнять при заблокированных сеансах (раздел 15.5): иначе рабочие процессы 1С повиснут на блокировке, а пользователи получат ошибки тайм-аута.

### 8.3. CLUSTER [PG]

```sql
CLUSTER [ ( VERBOSE [ boolean ] ) ] [ table_name [ USING index_name ] ]
```

- Физически упорядочивает строки таблицы по индексу. Побочный эффект тот же, что у `VACUUM FULL`: таблица и индексы переписаны без мусора.
- Блокировка `ACCESS EXCLUSIVE`. Место: копия таблицы плюс индексы; при сортировке — до двух размеров таблицы.
- Операция разовая: новые строки порядок не соблюдают. Индекс запоминается (`CLUSTER таблица;` повторит по нему; `ALTER TABLE … SET WITHOUT CLUSTER` — забыть).
- После `CLUSTER` нужен `ANALYZE`.

```sql
CLUSTER (VERBOSE) public._inforg8901 USING _inforg8901_1;
ANALYZE public._inforg8901;
```

[практика] Для 1С `CLUSTER` даёт выигрыш на таблицах, которые читаются диапазонами по ведущим полям «кластерного» индекса платформы (обычно индекс с суффиксом `_1`), но эффект временный, а простой — полный. Используется редко.

### 8.4. pg_repack

Расширение и одноимённая утилита: переписывает таблицу, как `VACUUM FULL`/`CLUSTER`, но **без длительной монопольной блокировки**. Источник — https://reorg.github.io/pg_repack/ (версия 1.5.3 поддерживает PostgreSQL 9.5–18).

Как работает полная перепаковка таблицы:

1. Создаёт служебную таблицу-журнал и триггер, записывающий в неё все `INSERT`/`UPDATE`/`DELETE` исходной таблицы.
2. Копирует строки в новую таблицу, строит на ней индексы, накатывает накопленные изменения из журнала.
3. Меняет файлы таблиц местами в системном каталоге и удаляет старую.

`ACCESS EXCLUSIVE` берётся только кратко — в начале (установка триггера) и в конце (подмена). Остальное время таблица доступна на чтение и запись; с версии 1.5.3 на неё держится `SHARE UPDATE EXCLUSIVE`, чтобы никто не выполнил DDL (подтверждено примечаниями к выпуску 1.5.3: блокировка заменена с `ACCESS SHARE` на `SHARE UPDATE EXCLUSIVE`).

Следствия для разных версий Ubuntu:

- **1.5.3 (Ubuntu 26.04, PGDG).** `SHARE UPDATE EXCLUSIVE` конфликтует сама с собой: пока идёт перепаковка, на этой таблице не работают autovacuum, ручной `VACUUM`/`ANALYZE`, `REINDEX CONCURRENTLY`, а `ALTER TABLE` платформы 1С (реструктуризация) встаёт в очередь и ждёт — и за ним в ту же очередь встают все остальные запросы к таблице.
- **1.4.7 (Ubuntu 22.04) и 1.5.0 (Ubuntu 24.04).** Держится только `ACCESS SHARE`, которая DDL не останавливает. Если во время перепаковки платформа выполнит реструктуризацию этой таблицы, результат непредсказуем — документация pg_repack запрещает DDL над целевой таблицей во время работы. На этих версиях запрет нужно обеспечивать организационно: блокировать обновление конфигурации на время работы pg_repack.
- На время между установкой триггера и подменой в базе существуют служебные объекты схемы `repack`: таблица-журнал и новая таблица (имена вида `repack.log_<oid>` и `repack.table_<oid>` — в документации pg_repack не приведены; подтверждено 19.10.2026 по исходному коду 1.5.3, `lib/pg_repack.sql.in`). Не запускайте в это время выгрузку `.dt`, «Тестирование и исправление» и `pg_dump` для переноса базы — ⚠ не подтверждено: поведение платформы 1С при наличии посторонней схемы `repack` рецензентом не проверялось. В схеме `public` на время работы появляется только триггер `repack_trigger` на исходной таблице.

Требования и ограничения:

- У таблицы должен быть `PRIMARY KEY` или уникальный индекс по `NOT NULL`-колонкам. Иначе: `WARNING: relation … must have a primary key or not-null unique keys` — таблица пропускается.
- Запускать может суперпользователь или владелец (владельцу нужен ключ `--no-superuser-check`).
- Свободное место: примерно **два размера** таблицы с индексами.
- Не работает с временными таблицами; нельзя упорядочивать по GiST-индексу.
- Нельзя выполнять DDL над таблицей во время работы. Для 1С это значит: **не запускать во время обновления конфигурации и реструктуризации**.
- Версии утилиты, библиотеки и SQL-расширения должны совпадать.
- Системный каталог (`pg_class` и т.п.) перепаковать нельзя (представление `repack.tables` в исходном коде 1.5.3 исключает схемы `pg_catalog` и `information_schema`).

Для баз 1С первое требование существенно: платформа создаёт не ограничения `PRIMARY KEY`, а обычные уникальные индексы, причём не у каждой таблицы. Заранее узнать, какие таблицы pg_repack пропустит, можно запросом (условие повторяет требование из документации pg_repack и сверено 19.10.2026 с представлением `repack.primary_keys` исходного кода 1.5.3 — отличие одно: pg_repack проверяет `NOT NULL` только у ключевых колонок индекса, без колонок `INCLUDE`, которых у индексов 1С нет; запрос добавлен рецензентом и на стенде не выполнялся):

```sql
-- Таблицы схемы public без первичного ключа и без уникального индекса по NOT NULL-колонкам
SELECT c.oid::regclass AS tbl,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total
FROM pg_class c
WHERE c.relkind = 'r'
  AND c.relnamespace = 'public'::regnamespace
  AND NOT EXISTS (
        SELECT 1
          FROM pg_index i
         WHERE i.indrelid = c.oid
           AND i.indisunique AND i.indisvalid
           AND i.indpred IS NULL                         -- индекс не частичный
           AND NOT (0 = ANY (i.indkey::int2[]))          -- без выражений
           AND NOT EXISTS (SELECT 1
                             FROM unnest(i.indkey::int2[]) AS k(attnum)
                             JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
                            WHERE NOT a.attnotnull))
ORDER BY pg_total_relation_size(c.oid) DESC;
```

Для таблиц из этого списка остаётся `VACUUM FULL` в окне обслуживания. Создавать в таблицах 1С собственный первичный ключ «ради pg_repack» не нужно: это изменение структуры, которое 1С не относит к допустимым действиям (раздел 5.1), и оно пропадёт при реструктуризации.

Установка на Ubuntu:

| Ubuntu | Пакет в архиве Ubuntu (universe) | Версия pg_repack |
|---|---|---|
| 22.04 jammy | `postgresql-14-repack` | 1.4.7 |
| 24.04 noble | `postgresql-16-repack` | 1.5.0 |
| 26.04 resolute | `postgresql-18-repack` | 1.5.3 |

Для других сочетаний версий — репозиторий PGDG (apt.postgresql.org), где есть `postgresql-NN-repack` для всех поддерживаемых веток.

```bash
sudo apt install postgresql-18-repack
sudo -u postgres psql -d buh -c "CREATE EXTENSION pg_repack;"
/usr/lib/postgresql/18/bin/pg_repack --version
```

Состав пакета Ubuntu 26.04 (проверено по списку файлов `postgresql-18-repack` 1.5.3-1): утилита `/usr/lib/postgresql/18/bin/pg_repack`, библиотека `/usr/lib/postgresql/18/lib/pg_repack.so`, файлы расширения `/usr/share/postgresql/18/extension/pg_repack.control` и `pg_repack--1.5.3.sql`. Зависимости: `postgresql-18`, `libpq5`, `libc6`. Обёртки в `/usr/bin` нет — утилиту вызывают по полному пути.

Postgres Pro:

- **Postgres Pro Standard** — пакет `pg-repack-std-NN` (для 18 — `pg-repack-std-18`); он указан в перечне пакетов документации Postgres Pro Standard 18 («pg_repack — расширение Postgres Pro и утилита для реорганизации таблиц»). Ставится в `/opt/pgpro/std-NN`.
- **Бесплатная сборка «Postgres Pro для 1С»** (репозиторий `repo.postgrespro.ru/1c/1c-NN`) — на 10.10.2026 в каталоге пакетов Ubuntu для `1c-18` лежат только пакеты `postgrespro-1c-18*` (сервер, клиент, библиотеки, contrib, dev, jit, plperl, plpython3, pltcl, документация). Пакета `pg-repack-1c-18` там **нет**; упоминавшееся в сообществе имя `pg-repack-1c-NN` не подтвердилось. Для ветки `1c-16` то же самое: в индексах пакетов для jammy и noble только `postgrespro-1c-16*` (сверено 19.10.2026); в документации этой ветки pg_repack не упоминается. Варианты: перейти на Postgres Pro Standard либо собрать pg_repack из исходных текстов с `pg_config` этой сборки (пакет `postgrespro-1c-NN-dev`) — ⚠ не подтверждено: сборка из исходных текстов под `postgrespro-1c` рецензентом не проверялась.

Уточнено 19.10.2026 по packages.ubuntu.com: в LTS-выпусках Ubuntu пакета `postgresql-17-repack` нет (он был только в промежуточном выпуске 25.10 questing, версия 1.5.2-1) — для ветки 17 на LTS его берут из PGDG. ⚠ Не подтверждено: совместимость пакета `postgresql-NN-repack` из PGDG/Ubuntu со сборкой «PostgreSQL с патчем от 1С». Формально зависимость выполняется (пакет требует `postgresql-NN`, сборка 1С предоставляет пакет с таким именем), но патчи 1С меняют код сервера, и бинарная совместимость библиотеки `pg_repack.so` никем не гарантирована. Ни 1С, ни авторы pg_repack такое сочетание не описывают. Сначала проверьте на копии базы: `CREATE EXTENSION pg_repack;`, пробная перепаковка одной таблицы, затем сверка числа строк и «Тестирование и исправление» в режиме проверки. Проверка наличия: `apt-cache search repack`, `SELECT * FROM pg_available_extensions WHERE name = 'pg_repack';`.

Основные ключи:

| Ключ | Назначение |
|---|---|
| `-d база` / `-a` | база / все базы (где установлено расширение) |
| `-t таблица` | только таблица (ключ повторяется) |
| `-c схема` | только схема |
| `-n`, `--no-order` | режим «онлайн `VACUUM FULL`» без упорядочивания (умолчание для некластеризованных таблиц) |
| `-o колонки`, `--order-by=…` | упорядочить по колонкам («онлайн `CLUSTER`») |
| `-x`, `--only-indexes` | перестроить только индексы указанной таблицы |
| `-i индекс`, `--index=…` | перестроить один индекс |
| `-s пространство`, `-S` | перенести таблицу (и индексы) в другое табличное пространство |
| `-j N`, `--jobs=N` | параллельное построение индексов (только для полной перепаковки) |
| `-N`, `--dry-run` | показать, что будет сделано, ничего не меняя |
| `-T секунд`, `--wait-timeout=…` | сколько ждать блокировку, прежде чем отменять мешающие запросы (умолчание 60) |
| `-D`, `--no-kill-backend` | не отменять чужие запросы по тайм-ауту, а пропустить таблицу |
| `-Z`, `--no-analyze` | не делать `ANALYZE` в конце |
| `-k`, `--no-superuser-check` | не проверять, что роль — суперпользователь (запуск владельцем таблиц поддержан с версии 1.5.2) |
| `-I таблица`, `--parent-table=…` | перепаковать родительскую таблицу вместе с наследниками |
| `-C расширение`, `--exclude-extension=…` | пропустить таблицы, принадлежащие указанному расширению |
| `--apply-count=N` | сколько записей журнала изменений применять за одну транзакцию (с 1.5.1) |
| `--switch-threshold=N` | переключать таблицы, когда в журнале изменений осталось не больше N записей (с 1.5.0) |
| `--no-error-on-invalid-index` | не останавливаться, встретив недействительный индекс; с 1.5.2 остановка с ошибкой — поведение по умолчанию |
| `-e`, `-E уровень` | показывать запросы / уровень сообщений |

```bash
PGR=/usr/lib/postgresql/18/bin/pg_repack

# Пробный прогон по одной таблице
sudo -u postgres $PGR -d buh -t public._inforg8901 --dry-run

# Перепаковать таблицу, индексы строить в 2 потока, чужие запросы не убивать
sudo -u postgres $PGR -d buh -t public._inforg8901 --no-order --jobs=2 --no-kill-backend

# Только индексы таблицы
sudo -u postgres $PGR -d buh -t public._document123 --only-indexes

# Вся база (долго; каждая таблица по очереди)
sudo -u postgres $PGR -d buh --no-order --jobs=2
```

Ошибки и их лечение:

| Сообщение | Причина | Решение |
|---|---|---|
| `must have a primary key or not-null unique keys` | нет подходящего ключа | такую таблицу — только `VACUUM FULL` |
| `already has a trigger called repack_trigger` / `Cannot create index … already exists` | прошлый запуск прерван | `DROP EXTENSION pg_repack CASCADE; CREATE EXTENSION pg_repack;`, удалить оставшиеся недействительные индексы, повторить |
| `Another pg_repack command may be running on the table` | параллельный запуск | дождаться и повторить |
| `program 'pg_repack X' does not match database library 'pg_repack Y'` | разные версии утилиты и расширения | обновить пакет, `ALTER EXTENSION pg_repack UPDATE` либо пересоздать расширение |
| `pg_repack … is not installed in the database` | нет расширения в базе | `CREATE EXTENSION pg_repack;` |

[практика] Альтернатива того же класса — расширение `pg_squeeze` (работает фоновым процессом через логическое декодирование). ⚠ не подтверждено: с базами 1С не проверялось, в этой базе знаний не описано.

### 8.5. Что выбрать

| Задача | Инструмент | Простой для пользователей |
|---|---|---|
| Убрать мусор, место вернуть в оборот | `VACUUM` / autovacuum | нет |
| Сжать раздутые индексы | `REINDEX CONCURRENTLY` | нет |
| Сжать раздутую таблицу, пользователи работают | `pg_repack` | секунды в начале и конце |
| Сжать таблицу, есть окно обслуживания | `VACUUM FULL` | на всё время |
| Сжать таблицы системного каталога | `VACUUM FULL pg_catalog.…` | на всё время, для всей базы |
| Сжать всю базу и заодно обновить версию/кодировку | `pg_dump` → `pg_restore` в новую базу | на всё время |
| Упорядочить строки физически | `CLUSTER` / `pg_repack -o` | да / нет |

## 9. Оценка раздувания

### 9.1. Быстрые признаки

```sql
-- Размеры: таблица, индексы, всего
SELECT c.oid::regclass AS tbl,
       pg_size_pretty(pg_relation_size(c.oid))       AS heap,
       pg_size_pretty(pg_indexes_size(c.oid))        AS indexes,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       c.reltuples::bigint AS rows_est
FROM pg_class c
WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 30;
```

Тревожные признаки: индексы в разы больше таблицы; таблица быстро растёт при стабильном числе строк; `n_dead_tup` сопоставим с `n_live_tup`.

### 9.2. Приблизительная оценка по статистике (без чтения данных)

Запросы ниже — упрощённая авторская оценка: ожидаемый размер считается из `reltuples` и средней ширины колонок (`pg_stats`). Они не читают таблицу и выполняются секунды. Точность ±10–20 %; для таблиц без свежей статистики результат бессмыслен — сначала `ANALYZE`. Более точные и общепринятые скрипты того же типа — https://github.com/ioguix/pgsql-bloat-estimation (`table/table_bloat.sql`, `btree/btree_bloat.sql`) и запрос из https://wiki.postgresql.org/wiki/Show_database_bloat.

Таблицы:

```sql
WITH t AS (
    SELECT c.oid, n.nspname, c.relname, c.reltuples, c.relpages,
           current_setting('block_size')::int AS bs,
           COALESCE((regexp_match(array_to_string(c.reloptions, ','), 'fillfactor=([0-9]+)'))[1]::int, 100) AS ff,
           (SELECT sum((1 - s.null_frac) * s.avg_width)
              FROM pg_stats s
             WHERE s.schemaname = n.nspname AND s.tablename = c.relname) AS data_width
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND c.relpages > 1280                 -- только таблицы больше 10 МБ
      AND c.reltuples > 0
), e AS (
    SELECT *,
           -- строка: указатель 4 + заголовок 24 + данные, выровненные до 8 байт
           ceil(reltuples * (4 + 24 + ceil(data_width / 8.0) * 8) / ((bs - 24) * ff / 100.0)) AS est_pages
    FROM t
    WHERE data_width IS NOT NULL
)
SELECT nspname, relname,
       pg_size_pretty(relpages::bigint * bs)                           AS real_size,
       pg_size_pretty(est_pages::bigint * bs)                          AS expected_size,
       pg_size_pretty(greatest(relpages - est_pages, 0)::bigint * bs)  AS bloat_size,
       round((100 * greatest(relpages - est_pages, 0) / relpages)::numeric, 1) AS bloat_pct
FROM e
ORDER BY greatest(relpages - est_pages, 0) DESC
LIMIT 30;
```

Индексы (только B-деревья по обычным колонкам; индексы по выражениям пропускаются):

```sql
WITH i AS (
    SELECT n.nspname, ct.relname AS tblname, ci.relname AS idxname,
           ci.reltuples, ci.relpages,
           current_setting('block_size')::int AS bs,
           COALESCE((regexp_match(array_to_string(ci.reloptions, ','), 'fillfactor=([0-9]+)'))[1]::int, 90) AS ff,
           (SELECT sum((1 - s.null_frac) * s.avg_width)
              FROM unnest(x.indkey::int2[]) AS k(attnum)
              JOIN pg_attribute a ON a.attrelid = x.indrelid AND a.attnum = k.attnum
              JOIN pg_stats s ON s.schemaname = n.nspname
                             AND s.tablename = ct.relname
                             AND s.attname = a.attname) AS key_width,
           (0 = ANY (x.indkey::int2[])) AS has_expr
    FROM pg_index x
    JOIN pg_class ci ON ci.oid = x.indexrelid
    JOIN pg_class ct ON ct.oid = x.indrelid
    JOIN pg_namespace n ON n.oid = ct.relnamespace
    JOIN pg_am am ON am.oid = ci.relam
    WHERE am.amname = 'btree'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND ci.relpages > 1280                -- только индексы больше 10 МБ
      AND ci.reltuples > 0
), e AS (
    SELECT *,
           -- запись: указатель 4 + заголовок 8 + ключ, выровненный до 8; страница: минус заголовок 24 и служебные 16
           1 + ceil(reltuples * (4 + 8 + ceil(key_width / 8.0) * 8) / ((bs - 40) * ff / 100.0)) AS est_pages
    FROM i
    WHERE NOT has_expr AND key_width IS NOT NULL
)
SELECT nspname, tblname, idxname,
       pg_size_pretty(relpages::bigint * bs)                           AS real_size,
       pg_size_pretty(est_pages::bigint * bs)                          AS expected_size,
       pg_size_pretty(greatest(relpages - est_pages, 0)::bigint * bs)  AS bloat_size,
       round((100 * greatest(relpages - est_pages, 0) / relpages)::numeric, 1) AS bloat_pct
FROM e
ORDER BY greatest(relpages - est_pages, 0) DESC
LIMIT 30;
```

Ограничения оценки:

- не учитывается дедупликация B-деревьев (PostgreSQL 13+): индекс с повторяющимися ключами реально **меньше** расчётного, значит, раздувание занижается;
- не учитываются `NULL`-битовая карта и точное выравнивание каждой колонки;
- типы `mchar`/`mvarchar` сборок для 1С учитываются по `avg_width` из статистики — как обычные строковые;
- TOAST-часть в оценку таблиц не входит;
- в регулярных выражениях намеренно стоит `[0-9]`, а не `\d`: на серверах 1С обычно `standard_conforming_strings = off`, и обратная косая черта в строке была бы «съедена».

Ориентиры [практика]: раздувание индекса больше 30–40 % при размере от сотен мегабайт — кандидат на `REINDEX CONCURRENTLY`; раздувание таблицы больше 40–50 % и больше нескольких гигабайт — кандидат на `pg_repack`/`VACUUM FULL`, если место действительно нужно.

### 9.3. Точная оценка: pgstattuple [PG]

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;      -- входит в contrib; функции вызывают суперпользователь или роль pg_stat_scan_tables
```

| Функция | Что возвращает | Цена |
|---|---|---|
| `pgstattuple(regclass)` | `table_len`, `tuple_count`, `tuple_len`, `tuple_percent`, `dead_tuple_count`, `dead_tuple_len`, `dead_tuple_percent`, `free_space`, `free_percent` | полное чтение таблицы |
| `pgstattuple_approx(regclass)` | `table_len`, `scanned_percent`, `approx_tuple_count`, `approx_tuple_len`, `approx_tuple_percent`, `dead_tuple_count`, `dead_tuple_len`, `dead_tuple_percent`, `approx_free_space`, `approx_free_percent` | читает только страницы, не отмеченные в карте видимости; остальное берёт из FSM |
| `pgstatindex(regclass)` | `version`, `tree_level`, `index_size`, `root_block_no`, `internal_pages`, `leaf_pages`, `empty_pages`, `deleted_pages`, `avg_leaf_density`, `leaf_fragmentation` | полное чтение индекса (B-дерево) |
| `pgstatginindex(regclass)` | `version`, `pending_pages`, `pending_tuples` | — |
| `pgstathashindex(regclass)` | страницы и записи хеш-индекса, `free_percent` | — |
| `pg_relpages(regclass)` | число страниц | — |

```sql
-- Одна таблица, быстро
SELECT * FROM pgstattuple_approx('public._accumrgt4567'::regclass);

-- Один индекс
SELECT index_size, leaf_pages, empty_pages, deleted_pages, avg_leaf_density, leaf_fragmentation
FROM pgstatindex('public._accumrgt4567_1'::regclass);

-- 20 самых больших таблиц схемы public
SELECT c.oid::regclass AS tbl,
       pg_size_pretty(s.table_len)               AS heap_size,
       round(s.dead_tuple_percent::numeric, 1)   AS dead_pct,
       round(s.approx_free_percent::numeric, 1)  AS free_pct
FROM (SELECT oid FROM pg_class
       WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace
       ORDER BY relpages DESC LIMIT 20) c,
     LATERAL pgstattuple_approx(c.oid::regclass) s
ORDER BY s.table_len DESC;

-- 20 самых больших B-деревьев
SELECT c.oid::regclass AS idx,
       pg_size_pretty(s.index_size) AS index_size,
       s.avg_leaf_density, s.leaf_fragmentation, s.empty_pages, s.deleted_pages
FROM (SELECT ci.oid FROM pg_class ci JOIN pg_am am ON am.oid = ci.relam
       WHERE ci.relkind = 'i' AND am.amname = 'btree'
         AND ci.relnamespace = 'public'::regnamespace
       ORDER BY ci.relpages DESC LIMIT 20) c,
     LATERAL pgstatindex(c.oid::regclass) s
ORDER BY s.index_size DESC;
```

Как читать:

- `avg_leaf_density` — средняя заполненность листовых страниц. У свежего индекса около 90 % (`fillfactor` B-дерева по умолчанию 90). Ниже 50–60 % — раздут.
- `leaf_fragmentation` — доля листовых страниц «не по порядку»; на SSD значения не имеет.
- `dead_tuple_percent` большой — `VACUUM` не успевает или не может убрать мусор; `free_percent` большой — мусор убран, но место не возвращено.
- `pgstattuple` и `pgstatindex` читают объект целиком и нагружают диск. На рабочей базе днём пользуйтесь `pgstattuple_approx` и запускайте по списку, а не по всей базе.

### 9.4. pg_freespacemap [PG]

```sql
CREATE EXTENSION IF NOT EXISTS pg_freespacemap;

-- свободное место по каждой странице (по данным FSM)
SELECT * FROM pg_freespace('public._document123'::regclass) LIMIT 20;

-- итог по таблице
SELECT count(*)                                   AS pages,
       pg_size_pretty(sum(avail)::bigint)         AS free_total,
       round(100.0 * sum(avail) / (count(*) * current_setting('block_size')::int), 1) AS free_pct
FROM pg_freespace('public._document123'::regclass);
```

- Функции: `pg_freespace(rel regclass, blkno bigint) → int2` и `pg_freespace(rel regclass) → setof (blkno bigint, avail int2)`.
- Значения округлены до 1/256 страницы (32 байта) и не обновляются при каждой вставке — карта свежая только после `VACUUM`.
- Для индексов FSM хранит только признак «страница полностью свободна», поэтому для оценки индексов расширение непригодно.

## 10. Заморозка и переполнение счётчика транзакций (wraparound)

### 10.1. Суть [PG]

- Идентификатор транзакции (XID) — 32 бита. Сравнение циклическое: для любой транзакции около 2 млрд XID считаются «прошлым» и около 2 млрд — «будущим».
- Если строка проживёт без обслуживания больше ~2 млрд транзакций, она «уедет в будущее» и станет невидимой. Чтобы этого не случилось, `VACUUM` **замораживает** старые версии: помечает их как видимые всем навсегда.
- У каждой таблицы есть `pg_class.relfrozenxid` — граница, старше которой незамороженных строк нет. У базы — `pg_database.datfrozenxid`, минимум по её таблицам. Возраст считается функцией `age()`.
- Для мультитранзакций (несколько сеансов блокируют одну строку) действует аналогичный счётчик: `relminmxid`, `datminmxid`, функция `mxid_age()`.

| Параметр | Умолчание | Смысл |
|---|---|---|
| `vacuum_freeze_min_age` | 50 млн | версии старше этого возраста `VACUUM` замораживает попутно |
| `vacuum_freeze_table_age` | 150 млн | при таком возрасте `relfrozenxid` обычный `VACUUM` становится «агрессивным» — читает все незамороженные страницы; не больше 0.95 × `autovacuum_freeze_max_age` |
| `autovacuum_freeze_max_age` | 200 млн (макс. 2 млрд; restart) | при таком возрасте автоочистка таблицы запускается принудительно, даже при `autovacuum = off`, и не прерывается блокировками |
| `vacuum_failsafe_age` | 1.6 млрд | (14+) «аварийный режим»: `VACUUM` отключает паузы, пропускает очистку индексов и усечение, лишь бы успеть заморозить |
| `vacuum_multixact_freeze_min_age` / `_table_age` | 5 млн / 150 млн | то же для мультитранзакций |
| `autovacuum_multixact_freeze_max_age` | 400 млн | принудительная очистка по мультитранзакциям |
| `vacuum_multixact_failsafe_age` | 1.6 млрд | аварийный режим по мультитранзакциям |
| `vacuum_max_eager_freeze_failure_rate` | 0.03 | (18+) обычный `VACUUM` заранее замораживает часть полностью видимых страниц; 0 — отключить |

Увеличение `autovacuum_freeze_max_age` растит каталог `pg_xact`: при 200 млн это около 50 МБ, при 2 млрд — около 0.5 ГБ (и около 2 ГБ / 20 ГБ в `pg_commit_ts`, если включён `track_commit_timestamp`) [PG].

### 10.2. Контроль

```sql
-- По базам
SELECT datname,
       age(datfrozenxid)                                    AS xid_age,
       round(100.0 * age(datfrozenxid) / 2147483647, 1)     AS pct_of_limit,
       mxid_age(datminmxid)                                 AS mxid_age
FROM pg_database
ORDER BY age(datfrozenxid) DESC;

-- По таблицам текущей базы (с учётом TOAST) — запрос из документации
SELECT c.oid::regclass AS table_name,
       greatest(age(c.relfrozenxid), age(t.relfrozenxid)) AS age
FROM pg_class c
LEFT JOIN pg_class t ON c.reltoastrelid = t.oid
WHERE c.relkind IN ('r', 'm')
ORDER BY 2 DESC
LIMIT 20;

-- Идёт ли сейчас «противозацикливающая» очистка
SELECT pid, datname, now() - xact_start AS runtime, query
FROM pg_stat_activity
WHERE backend_type = 'autovacuum worker' AND query LIKE '%to prevent wraparound%';
```

Ориентиры для мониторинга [практика]:

| `age(datfrozenxid)` | Оценка |
|---|---|
| до 200–250 млн | норма: автоочистка справляется |
| 300–500 млн | автоочистка отстаёт — искать причину (раздел 10.4) |
| больше 1 млрд | срочные действия, пока не дошло до 1.6 млрд (failsafe) |
| около 2,107 млрд (до предела ~2,147 млрд осталось 40 млн) | предупреждения в журнале и клиентам (раздел 10.3) |
| около 2,144 млрд (осталось 3 млн) | сервер отказывает в выдаче новых XID — запись невозможна |

### 10.3. Сообщения сервера (PostgreSQL 17–18) [PG]

Когда до предела остаётся меньше 40 млн транзакций:

```
WARNING:  database "buh" must be vacuumed within 39985967 transactions
HINT:  To avoid XID assignment failures, execute a database-wide VACUUM in that database.
```

Когда остаётся меньше 3 млн — новые XID не выдаются, работают только читающие транзакции:

```
ERROR:  database is not accepting commands that assign new transaction IDs to avoid wraparound data loss in database "buh"
HINT:  Execute a database-wide VACUUM in that database.
```

Уточнено 19.10.2026 по исходному коду `src/backend/access/transam/varsup.c` веток 14–18: у всех этих подсказок есть вторая строка `You might also need to commit or roll back old prepared transactions, or drop stale replication slots.`; в 17–18 предупреждение, которое выдаётся при самой выдаче нового XID, имеет подсказку `To avoid transaction ID assignment failures, …` (без сокращения «XID»), а вариант `To avoid XID assignment failures, …` выводится при пересчёте пределов (после `VACUUM` и при запуске сервера) — для поиска по журналу используйте `must be vacuumed within`.

В версиях 14–16 тексты другие (сверено по документации 15, 16, 17 и 18 и по `varsup.c`; формулировки сменились именно в 17):

```
WARNING:  database "buh" must be vacuumed within 39985967 transactions
HINT:  To avoid a database shutdown, execute a database-wide VACUUM in that database.

ERROR:  database is not accepting commands to avoid wraparound data loss in database "buh"
HINT:  Stop the postmaster and vacuum that database in single-user mode.
```

Подсказке про однопользовательский режим следовать **не нужно** и в 14–16: документация этих версий прямо говорит, что останавливать сервер и входить в однопользовательский режим «не требуется и нежелательно» — `VACUUM` выполняется на работающем сервере, а в однопользовательском режиме отключены защитные механизмы от потери данных. Единственный повод для однопользовательского режима — выполнить `TRUNCATE` или `DROP` ненужных таблиц, чтобы их не чистить; запас в 3 млн транзакций оставлен именно для этого.

В PostgreSQL 19 (на 19.10.2026 — RC 1) порог предупреждений поднят с 40 млн до 100 млн оставшихся транзакций — и для XID, и для мультитранзакций (сверено 19.10.2026 по примечаниям к выпуску 19).

### 10.4. Действия при приближении к пределу [PG]

1. Найти и завершить (зафиксировать/откатить) старые подготовленные транзакции:

```sql
SELECT gid, prepared, owner, database, age(transaction) AS xid_age FROM pg_prepared_xacts ORDER BY 5 DESC;
-- ROLLBACK PREPARED 'gid';
```

2. Найти и завершить длинные транзакции:

```sql
SELECT pid, datname, usename, state, xact_start,
       age(backend_xid) AS xid_age, age(backend_xmin) AS xmin_age, left(query, 80) AS query
FROM pg_stat_activity
WHERE backend_xid IS NOT NULL OR backend_xmin IS NOT NULL
ORDER BY greatest(age(backend_xid), age(backend_xmin)) DESC
LIMIT 10;
-- SELECT pg_terminate_backend(pid);
```

3. Проверить слоты репликации и удалить ненужные (реплику потом, возможно, придётся пересоздать):

```sql
SELECT slot_name, slot_type, active, age(xmin) AS xmin_age, age(catalog_xmin) AS catalog_xmin_age
FROM pg_replication_slots ORDER BY greatest(age(xmin), age(catalog_xmin)) DESC NULLS LAST;
-- SELECT pg_drop_replication_slot('имя');
```

4. Выполнить `VACUUM` проблемной базы от суперпользователя. **Не** `VACUUM FULL` и **не** `VACUUM FREEZE`: первый требует XID и места, второй делает больше работы, чем нужно, чтобы выйти из аварии.

```bash
# самые старые таблицы — первыми, в несколько потоков
sudo -u postgres vacuumdb --min-xid-age=1000000000 --jobs=4 --verbose buh
sudo -u postgres vacuumdb --jobs=4 buh
```

```sql
-- если время критично: одна огромная таблица без индексов и усечения
VACUUM (INDEX_CLEANUP OFF, TRUNCATE false, VERBOSE) public._accumrg4560;
```

5. Убедиться, что возраст упал (`age(datfrozenxid)`), и разобраться, почему автоочистка не справилась: мало рабочих процессов, низкий `cost_limit`, держатель горизонта, автоочистка отключена на таблице.

Особенность 1С [практика]:

- Autovacuum не обрабатывает временные таблицы [PG]. У временной таблицы тоже есть `relfrozenxid`, и он участвует в расчёте `datfrozenxid`. Механизм подтверждён исходным кодом PostgreSQL 18: функция `vac_update_datfrozenxid()` (`src/backend/commands/vacuum.c`) берёт минимум `relfrozenxid` по **всем** таблицам `pg_class` без исключения для временных, а чужие временные таблицы пропускают и `VACUUM`, и autovacuum («We cannot safely process other backends' temp tables» в `autovacuum.c`). Заморозить такую таблицу может только сам сеанс-владелец.
- Рабочие процессы 1С держат соединения с СУБД долго, а временные таблицы в них не удаляются, а очищаются и переиспользуются. Старая временная таблица в «вечном» соединении не даёт `datfrozenxid` двигаться, хотя все постоянные таблицы заморожены.
- Диагностика:

```sql
SELECT n.nspname, c.relname, age(c.relfrozenxid) AS xid_age
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relpersistence = 't' AND c.relkind = 'r'
ORDER BY age(c.relfrozenxid) DESC
LIMIT 20;
```

- Лечение: завершить соответствующие сеансы СУБД или перезапустить рабочие процессы 1С (`rphost`) — при закрытии соединения временные таблицы удаляются. Плановый перезапуск рабочих процессов кластера 1С решает проблему профилактически.
- Как по схеме `pg_temp_N` найти сеанс-владельца. В PostgreSQL 16–18 число `N` — это идентификатор серверного процесса (backend ID), и PID по нему даёт `pg_stat_get_backend_pid(N)`. Документация 16, 17 и 18 прямо говорит, что backend ID используется, в частности, для обозначения временной схемы сеанса (в 16 это «небольшое положительное целое», в 17–18 — «целое >= 0»); в примечаниях к выпуску 16 сказано, что `pg_stat_get_backend_idset()` и родственные функции стали возвращать неизменный backend ID. В исходном коде 18 схема называется `pg_temp_<MyProcNumber>` (`src/backend/catalog/namespace.c`). Запрос (добавлен рецензентом, на стенде не выполнялся):

```sql
-- PostgreSQL 16+: самые «старые» временные схемы и их сеансы
SELECT t.nspname, t.tables, t.xid_age,
       a.pid, a.usename, a.application_name, a.client_addr, a.backend_start, a.state
FROM (SELECT n.nspname, count(*) AS tables, max(age(c.relfrozenxid)) AS xid_age
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE c.relpersistence = 't' AND c.relkind = 'r'
         AND left(n.nspname, 8) = 'pg_temp_'
       GROUP BY n.nspname) t
LEFT JOIN pg_stat_activity a
       ON a.pid = pg_stat_get_backend_pid(substring(t.nspname from 9)::int)
ORDER BY t.xid_age DESC
LIMIT 20;
```

  Пустой `pid` означает, что владельца уже нет: это «потерянная» схема, её таблицы удалит autovacuum (раздел 11.1). Найденный `pid` сопоставляется с сеансом 1С по колонке `db-proc-info` вывода `rac session list` и по свойству `dbpid` технологического журнала.
- Подтверждено примечаниями к выпуску PostgreSQL 16 (сверено 11.10.2026): начиная с 16-й версии `pg_stat_get_backend_idset()` и связанные функции используют постоянный идентификатор серверного процесса, а раньше значения-индексы могли меняться в течение жизни сеанса. В PostgreSQL 14 и 15 этот приём **не работает**: там `pg_stat_get_backend_idset()` возвращала порядковые номера от 1 до числа активных процессов (так написано в документации 15), не связанные с номером временной схемы. Прямого способа получить PID по `pg_temp_N` из SQL в этих версиях рецензент не нашёл; косвенный — первое число в колонке `pg_locks.virtualtransaction` (формат `N/номер`): `SELECT DISTINCT pid FROM pg_locks WHERE split_part(virtualtransaction, '/', 1) = 'N';`. Уточнено 19.10.2026 по исходному коду веток 14 и 15: и номер в имени схемы (`pg_temp_%d` в `namespace.c`), и первая часть виртуального идентификатора транзакции (`vxid.backendId` в `xact.c`) берутся из одного значения `MyBackendId`, а `pg_locks` выводит его в формате `%d/%u` (`lockfuncs.c`); блокировку своего `virtualxid` сеанс берёт в начале каждой транзакции и снимает в её конце, поэтому строка есть только пока сеанс находится в транзакции. На стенде запрос не проверялся. Практический выход для 14–15 — плановый перезапуск рабочих процессов 1С.

## 11. Специфика 1С

### 11.1. Временные таблицы и раздувание системного каталога

Механизм:

- Запросы 1С с `ПОМЕСТИТЬ`, соединения с виртуальными таблицами, RLS и т.п. порождают временные таблицы (`tt1`, `tt2`, …) в сеансе СУБД. В нагруженной базе это тысячи созданий в минуту.
- Создание любой таблицы — это вставка строк в системный каталог: `pg_class` (сама таблица, её индексы, TOAST), `pg_attribute` (по строке на каждую колонку плюс системные колонки), `pg_type` (тип строки и тип массива), `pg_depend`, `pg_index`; после `ANALYZE` — `pg_statistic`. Удаление таблицы превращает все эти строки в мёртвые.
- Платформа снижает поток: временные таблицы не удаляются, а очищаются функцией `fasttruncate()` модуля `fasttrun` и используются повторно. Назначение модуля по документации — «не допустить роста `pg_class`»; операция нетранзакционная [PGPro].
- Каталог чистит обычный autovacuum. Если горизонт xmin держит длинная транзакция, мёртвые строки каталога копятся — `pg_attribute` и `pg_class` вырастают до гигабайтов [практика].
- [PGPro] Большое число временных таблиц при закрытии соединения может исчерпать таблицу блокировок (`max_locks_per_transaction`): транзакция прерывается, остаются «потерянные» временные таблицы (при закрытии соединения все временные таблицы сеанса удаляются одной транзакцией). Их позже удаляет autovacuum; в журнале это запись `autovacuum: dropping orphan temp table "база.pg_temp_N.имя"` (текст проверен по исходному коду 18). Autovacuum удаляет такие таблицы, только убедившись, что сеанса-владельца схемы уже нет; пока владелец жив, его временные таблицы никто, кроме него самого, тронуть не может.

Симптомы:

- растёт время планирования всех запросов, даже простых;
- медленно создаются временные таблицы; в `pg_stat_activity` много сеансов на `CREATE TEMP TABLE`/`fasttruncate`;
- высокая нагрузка CPU при малом вводе-выводе;
- `\d` в psql «задумывается».

Обнаружение:

```sql
-- 10 самых больших таблиц системного каталога
SELECT c.oid::regclass AS catalog_table,
       pg_size_pretty(pg_relation_size(c.oid))        AS heap,
       pg_size_pretty(pg_indexes_size(c.oid))         AS indexes,
       pg_size_pretty(pg_total_relation_size(c.oid))  AS total,
       s.n_live_tup, s.n_dead_tup, s.last_autovacuum, s.autovacuum_count
FROM pg_class c
JOIN pg_stat_sys_tables s ON s.relid = c.oid
WHERE c.relnamespace = 'pg_catalog'::regnamespace AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 10;

-- Сколько объектов реально описано в каталоге
SELECT relkind, relpersistence, count(*) FROM pg_class GROUP BY 1, 2 ORDER BY 3 DESC;

-- Точная доля мусора (расширение pgstattuple)
SELECT * FROM pgstattuple('pg_catalog.pg_attribute'::regclass);
SELECT * FROM pgstattuple('pg_catalog.pg_class'::regclass);
```

Оценка [практика]: для базы 1С с 10–30 тыс. таблиц нормальный размер `pg_attribute` — десятки-сотни мегабайт, `pg_class` — единицы-десятки мегабайт. Гигабайты или `free_percent`/`dead_tuple_percent` в десятки процентов — раздувание. Надёжный эталон — те же таблицы в свежевосстановленной копии базы.

Лечение:

1. Устранить причину: найти держателя горизонта (раздел 1.3, 11.2). Пока он жив, чистить бесполезно.
2. Обычная очистка (работу не блокирует, место не возвращает, но останавливает рост):

```sql
VACUUM (VERBOSE, ANALYZE) pg_catalog.pg_class;
VACUUM (VERBOSE, ANALYZE) pg_catalog.pg_attribute;
VACUUM (VERBOSE, ANALYZE) pg_catalog.pg_type;
VACUUM (VERBOSE, ANALYZE) pg_catalog.pg_depend;
VACUUM (VERBOSE, ANALYZE) pg_catalog.pg_index;
VACUUM (VERBOSE, ANALYZE) pg_catalog.pg_statistic;
```

3. Если каталог уже раздут — сжатие в окне обслуживания, при заблокированных сеансах 1С. Каждая команда берёт `ACCESS EXCLUSIVE` на таблицу каталога, то есть на это время в базе останавливается всё:

```sql
VACUUM (FULL, VERBOSE, ANALYZE) pg_catalog.pg_attribute;
VACUUM (FULL, VERBOSE, ANALYZE) pg_catalog.pg_class;
VACUUM (FULL, VERBOSE, ANALYZE) pg_catalog.pg_type;
VACUUM (FULL, VERBOSE, ANALYZE) pg_catalog.pg_depend;
VACUUM (FULL, VERBOSE, ANALYZE) pg_catalog.pg_index;
VACUUM (FULL, VERBOSE, ANALYZE) pg_catalog.pg_statistic;
```

4. Профилактика: `autovacuum_naptime = 20s` и достаточное число рабочих процессов [1С][PGPro]; низкие глобальные `scale_factor` (на каталог нельзя поставить индивидуальные); контроль длинных транзакций; `max_locks_per_transaction` по рекомендациям (256 у [PGPro], 512…2000 у [1С]).

Параметры сборок 1С, связанные с временными таблицами [1С]:

- `enable_temp_memory_catalog` (статья ИТС 5866: «начиная с PostgreSQL 16.4», по умолчанию `off`; применяется при перезапуске PostgreSQL). Смысл по тексту статьи (сверено 10.10.2026): строки системных каталогов, относящиеся к временным таблицам, хранятся в отдельном хранилище в оперативной памяти, а не в `pg_class`/`pg_attribute` на диске. Для темы этого раздела это главное: по смыслу (в статье прямо не сказано — вывод рецензента, ⚠ на стенде не проверялось) при `on` поток временных таблиц перестаёт порождать мёртвые строки в дисковом каталоге, то есть уходит сама причина его раздувания. Плата — вычислительные накладные расходы: статья советует включать параметр только там, где дисковая подсистема перегружена, а процессоры свободны; на быстрых SSD или при «прогретом» кеше файловой системы создание, изменение и удаление временных таблиц с включённой опцией может идти дольше. Подробности — в `02-postgresql-conf-tyuning-dlya-1c.md`, разделы 3.1 и 4.12.
- `enable_temp_rd_buffers` (сборки «PostgreSQL с патчем от 1С» начиная с `17.5-11.1C` и `16.9-34.1C`; булев, по умолчанию `off`) — статья ИТС 6035 «Отложенное создание файлов временных таблиц в PostgreSQL с патчем от 1С» от 25.09.2025, сверено 10.10.2026. При `on` файл временной таблицы на диске не создаётся, пока её данные не превысят 32 Кб: до этого момента они лежат в оперативной памяти; после очистки временной таблицы файл удаляется, и накопление снова идёт в памяти. При `off` сохраняется поведение обычного PostgreSQL — файлы создаются сразу. Статья предупреждает о росте общего потребления памяти при включении; со стороны платформы 1С поведение СУБД не меняется. На раздувание системного каталога параметр **не влияет** (строки в `pg_class` создаются как прежде) — он снижает нагрузку на файловую систему. Нужен ли перезапуск для применения, в статье не сказано (⚠ не подтверждено: проверьте `SELECT context FROM pg_settings WHERE name = 'enable_temp_rd_buffers';`).
- В ванильном PostgreSQL (пакеты PGDG и архива Ubuntu) этих двух параметров нет: строка с ними в `postgresql.conf` не даст серверу запуститься (`unrecognized configuration parameter`). В приложении K документации Postgres Pro они не упоминаются; 19.10.2026 проверено, что их нет и в прочитанных страницах документации «PostgreSQL для 1С» ветки 16 (приложение K, описания модулей для 1С, `pg-setup`, `pgpro_tune`, примечания к выпускам 16 и 16.14) (⚠ не подтверждено: есть ли они в самой сборке — проверяется только на сервере запросом ниже). Перед переносом конфигурации между сборками проверьте: `SELECT name FROM pg_settings WHERE name LIKE 'enable_temp%';`.

### 11.2. Длинные транзакции и idle in transaction

Как это выглядит со стороны СУБД: транзакция 1С (`НачатьТранзакцию()` … `ЗафиксироватьТранзакцию()`, проведение документа, запись набора) открывает транзакцию PostgreSQL. Между запросами, пока код выполняется на сервере 1С, сеанс СУБД находится в состоянии `idle in transaction`. Секунды — норма. Часы — проблема.

Типичные источники в 1С [практика]:

- закрытие месяца, расчёт себестоимости, массовое перепроведение в одной транзакции;
- реструктуризация обычным механизмом (одна транзакция на всё, раздел 11.5);
- обмены и загрузки, пишущие весь пакет одной транзакцией;
- отладка на рабочей базе: остановка на точке останова внутри транзакции;
- зависший рабочий процесс или клиент, не закрывший транзакцию;
- внешние инструменты: долгий `pg_dump`, BI-выгрузки, забытый `BEGIN` в psql.

Поиск:

```sql
SELECT pid, datname, usename, application_name, client_addr, state,
       now() - xact_start    AS xact_age,
       now() - state_change  AS in_state,
       age(backend_xid)      AS xid_age,
       age(backend_xmin)     AS xmin_age,
       wait_event_type, wait_event,
       left(query, 100)      AS last_query
FROM pg_stat_activity
WHERE backend_type = 'client backend'
  AND xact_start IS NOT NULL
ORDER BY xact_start
LIMIT 20;
```

Значения `state` [PG]: `active`, `idle`, `idle in transaction`, `idle in transaction (aborted)`, `fastpath function call`, `disabled`; в документации 18 добавлено `starting` (начальный запуск сеанса, проверка подлинности клиента) — в документации 16 и 17 его нет.

Завершение:

```sql
SELECT pg_cancel_backend(12345);       -- отменить текущий запрос (сеанс остаётся)
SELECT pg_terminate_backend(12345);    -- разорвать сеанс; транзакция откатится
```

Для сеансов 1С правильнее сначала завершить сеанс средствами кластера 1С (консоль администрирования, `rac session terminate`), и только если не помогло — `pg_terminate_backend`. Платформа получит ошибку соединения и откатит свою транзакцию.

Тайм-ауты [PG]:

| Параметр | Умолчание | Действие |
|---|---|---|
| `idle_in_transaction_session_timeout` | `0` (выкл.) | разрывает сеанс, простаивающий внутри транзакции дольше указанного |
| `idle_session_timeout` | `0` | разрывает сеанс, простаивающий вне транзакции; для 1С не использовать — платформа держит пул соединений |
| `transaction_timeout` | `0` | (17+) разрывает сеанс, если транзакция длится дольше указанного |
| `statement_timeout` | `0` | отменяет запрос, работающий дольше указанного |
| `lock_timeout` | `0` | отменяет запрос, ждущий блокировку дольше указанного |

[практика] Для баз 1С допустим только `idle_in_transaction_session_timeout`, и с большим запасом: значение должно превышать самую долгую легальную паузу между запросами внутри транзакции (тяжёлые расчёты на стороне сервера 1С). Задавать на базу или роль, а не глобально:

```sql
ALTER DATABASE buh SET idle_in_transaction_session_timeout = '2h';
-- отменить:
ALTER DATABASE buh RESET idle_in_transaction_session_timeout;
```

Официальных рекомендаций [1С] по этому параметру нет; `transaction_timeout` и `statement_timeout` для рабочей роли 1С не задавайте — оборвёте закрытие месяца и реструктуризацию.

### 11.3. Массовые перепроведения, загрузки, свёртка

Что происходит в СУБД:

- каждое перепроведение документа — удаление и вставка его движений плюс обновление итогов: поток мёртвых строк в таблицах движений (`_accumrg…`, `_accrg…`, `_inforg…`) и итогов;
- объём WAL — десятки и сотни гигабайт; при включённой архивации и репликации это всё уходит в архив и на реплики;
- автоочистка отстаёт: пороги (доля таблицы) достигаются на больших таблицах медленно, а статистика устаревает;
- загрузка `.dt` и перенос `ibcmd infobase replicate` создают все таблицы заново: статистики у них нет вообще.

Порядок действий:

1. До: проверить свободное место (данные, `pg_wal`, архив WAL), сделать резервную копию, убедиться, что нет «старых» транзакций и неактивных слотов.
2. Во время: выполнять порциями (по периодам, по организациям) с отдельной транзакцией на документ; следить за `pg_stat_user_tables.n_dead_tup`, размером `pg_wal`, занятостью рабочих процессов автоочистки.
3. После:

```bash
sudo -u postgres vacuumdb --analyze --jobs=4 buh          # очистка + статистика
sudo -u postgres psql -d buh -f /usr/local/share/pg-maint/health-report.sql   # отчёт (раздел 15.3)
```

4. Если после удаления большого объёма данных место нужно вернуть — `pg_repack` или `VACUUM FULL` по конкретным таблицам; индексы — `REINDEX CONCURRENTLY`.

Отключать autovacuum «на время загрузки» не нужно: на новых таблицах он почти ничего не стоит, зато соберёт статистику.

### 11.4. Таблицы итогов регистров

Какие таблицы обновляются чаще всего (имена платформы; в PostgreSQL — в нижнем регистре):

| Таблица | Содержимое |
|---|---|
| `_AccumRgT<N>` | итоги регистра накопления (остатки); есть, только если регистр поддерживает остатки |
| `_AccumRgTn<N>` | обороты регистра накопления; есть, только если регистр поддерживает обороты |
| `_AccRgAT0<N>`, `_AccRgAT1<N>`, … `_AccRgAT<k><N>` | итоги регистра бухгалтерии по счёту: `_AccRgAT0` — итоги по счёту, `_AccRgAT<i>` — с `i` видами субконто, `i` от 1 до максимального числа субконто в плане счетов (по конспекту `razmeshchenie-dannyh-i-indeksy.md`) |
| `_AccRgCT<N>` | итоги оборотов между счетами; только у регистра с поддержкой корреспонденции |
| `_InfoRgSL<N>`, `_InfoRgSF<N>` | итоги «срез последних» / «срез первых» периодического регистра сведений; есть, только если у регистра включены свойства «Разрешить итоги: срез последних» / «срез первых» |
| `_AccumRg<N>`, `_AccRg<N>`, `_InfoRg<N>` | движения (в основном вставки и удаления) |
| `_AccumRgOpt`, `_AccRgOpt` | настройки хранения итогов (по одной таблице на все регистры накопления / бухгалтерии); маленькие, но обновляются при пересчёте и сдвиге периода итогов |
| `_AccumRgAgg<N>` и родственные (`_AccumRgSt`, `_AccumRgBf`, `_AccumRgDl`) | агрегаты оборотных регистров накопления, если они включены |

Имена сверены рецензентом по конспектам статей ИТС «Размещение данных 1С:Предприятия 8» в этой базе знаний (`kb/its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`, `kb/its-metod/razmeshchenie-dannyh-i-indeksy.md`); там же — состав полей и индексов каждой таблицы.

Почему раздуваются: каждая запись движений изменяет строку итогов (`UPDATE`) — «горячие» строки (ходовая номенклатура, основные счета) получают тысячи версий в день. Если изменённые колонки не входят в индексы и на странице есть место, обновление идёт как HOT и мусор убирается «на лету»; иначе растут и таблица, и индексы.

Что делать:

- индивидуальные пороги автоочистки для самых горячих таблиц итогов (раздел 4.6);
- контроль раздувания их индексов и `REINDEX CONCURRENTLY` по отчёту;
- на уровне 1С — пересчёт итогов и сдвиг периода рассчитанных итогов (раздел 11.6): таблица итогов физически уменьшается, потому что платформа удаляет «нулевые» и лишние записи;
- [практика] `fillfactor` ниже 100 (например, 80–90) на таблице итогов повышает долю HOT-обновлений, но настройка пропадает при реструктуризации и требует перезаписи таблицы, чтобы подействовать на существующие страницы. Применять только при доказанной пользе.

Соответствие «регистр → таблица» — `ПолучитьСтруктуруХраненияБазыДанных()` либо обработки просмотра структуры хранения.

### 11.5. Реструктуризация при обновлении конфигурации

Реструктуризация — приведение таблиц базы к новой структуре метаданных при «Обновить конфигурацию базы данных».

Официально [1С] (документация платформы, см. `kb/its-docs/adm-pr03-sluzhebnye-fajly-p2.md`, `adm-pr07-parametry-zapuska-1cv8-p1.md`):

- Механизмов два. `v1` — обычный (единственный в 8.3.10 и младше). `v2` — оптимизированный: только клиент-серверный вариант и только MS SQL Server или PostgreSQL.
- Выбор: ключ `-v1|-v2` команды конфигуратора `/UpdateDBCfg`; если ключа нет — параметр `UpdateDBCfg=v1|v2` в файле `conf.cfg` **на компьютере, где запущен конфигуратор**. Умолчание — `v1`.
- Оптимизированному механизму нужна Java (JRE 1.8+) на сервере 1С; параметры JVM — `RestructJavaOpts` в `conf.cfg` на сервере кластера (например, `RestructJavaOpts=-Xmx2048m`).
- Если `-v2` конфликтует с другими параметрами, молча используется обычный механизм. При фоновом обновлении (`-BackgroundStart`) оптимизированный механизм не применяется.

```
# conf.cfg на рабочем месте администратора (Windows: C:\Program Files\1cv8\conf\conf.cfg)
UpdateDBCfg=v2
```

```
"C:\Program Files\1cv8\8.3.27.1688\bin\1cv8.exe" DESIGNER /S "srv1c\buh" /N "Администратор" /P "***" ^
    /UpdateDBCfg -Server -v2 -SessionTerminate force /Out "C:\log\updatedbcfg.log"
```

Что происходит в базе данных [практика; официального описания внутренней механики нет — ⚠ не подтверждено первоисточником, особенно в части транзакций и параллельности `v2`]:

| | Обычный механизм (`v1`) | Оптимизированный (`v2`) |
|---|---|---|
| Новая структура | для каждой изменяемой таблицы создаётся новая таблица (в имени добавка `NG`), затем старая удаляется, новая переименовывается | то же: новая таблица, перенос, подмена |
| Перенос данных | строки читает и пишет сервер 1С (или конфигуратор), построчно, в один поток | запросами на стороне СУБД (`INSERT … SELECT`), таблицы обрабатываются параллельно |
| Транзакция | одна длинная на всю реструктуризацию | короче, по таблицам |
| Скорость на больших таблицах | часы | в разы быстрее |

Последствия для администратора PostgreSQL:

- **Место на диске.** До подмены существуют и старая, и новая таблица с индексами. Нужен запас не меньше суммарного размера изменяемых таблиц с индексами плюс WAL того же порядка. Размер заранее: `SELECT pg_size_pretty(pg_total_relation_size('public._document123'));`.
- **WAL.** Объём — порядка размера новых таблиц и индексов. Он уйдёт в архив и на реплики.
- **Горизонт очистки.** Длинная транзакция `v1` держит xmin: во всей базе на это время не убирается мусор.
- **Статистика.** У новых таблиц её нет до первого автоанализа. Сразу после обновления: `vacuumdb --analyze-only -j 4 база`.
- **Настройки таблиц.** `ALTER TABLE … SET (…)`, `SET STATISTICS`, расширенная статистика, `fillfactor`, вручную созданные индексы — пропадают вместе со старой таблицей.
- **Блокировки.** `ALTER TABLE`/`DROP TABLE` требуют `ACCESS EXCLUSIVE`; autovacuum на этих таблицах прерывается (`canceling autovacuum task` в журнале — это нормально). Ручные `REINDEX CONCURRENTLY`, `pg_repack`, `pg_dump` на время обновления нужно остановить — они либо помешают, либо сломаются.
- **Побочный плюс.** Пересозданные таблицы и их индексы получаются без раздувания.
- **Прерывание.** Если реструктуризация оборвалась (сбой, нехватка места), в базе могут остаться таблицы с добавкой `ng`. Платформа обычно доводит дело до конца при следующем запуске; вручную их не удаляйте, не имея резервной копии. Поиск: `SELECT relname FROM pg_class WHERE relkind = 'r' AND relname LIKE '%ng' ORDER BY 1;` ⚠ не подтверждено: точный вид суффикса зависит от версии платформы.

### 11.6. Пересчёт итогов (уровень 1С)

Итоги регистров — данные приложения, а не СУБД: PostgreSQL о них ничего не знает. Средств «пересчитать итоги» на уровне СУБД нет.

- **Где запускается:** конфигуратор → «Администрирование» → «Тестирование и исправление» → «Пересчет итогов» (монопольно); в режиме предприятия — стандартная обработка «Управление итогами и агрегатами» (типовые конфигурации на БСП); из кода — методы менеджера регистра `ПересчитатьИтоги()`, `ПересчитатьТекущиеИтоги()`, `ПересчитатьИтогиЗаПериод()`, `УстановитьМаксимальныйПериодРассчитанныхИтогов()`; пакетно — `/IBCheckAndRepair -RecalcTotals`.
- **Параллельность:** свойство информационной базы «Количество заданий пересчета итогов» (по умолчанию 4, клиент-серверный вариант) и ключ `-JobsCount` [1С].
- **Что это значит для СУБД:** таблицы итогов массово переписываются (`DELETE` + `INSERT`). Сразу после пересчёта нужна очистка и статистика:

```bash
sudo -u postgres vacuumdb --analyze --jobs=4 buh
```

- **Зачем регулярно:** сдвиг периода рассчитанных итогов на закрытый период уменьшает число записей итогов и ускоряет проведение текущих документов; пересчёт исправляет расхождения итогов с движениями.

### 11.7. «Тестирование и исправление» против обслуживания на уровне СУБД

Запуск: конфигуратор → «Администрирование» → «Тестирование и исправление ИБ»; пакетно — `/IBCheckAndRepair` [1С]. Почти всегда требует монопольного режима.

| Режим тестирования и исправления | Что делает | Ближайший аналог на уровне PostgreSQL | В чём разница |
|---|---|---|---|
| Реиндексация таблиц (`-ReIndex`) | перестраивает все индексы таблиц, включая дополнительные | `REINDEX` / `reindexdb --concurrently` | СУБД делает то же без монопольного режима и без остановки пользователей |
| Реструктуризация таблиц (`-Rebuild`) | пересоздаёт каждую таблицу и переносит данные | `VACUUM FULL` / `pg_repack` всей базы | платформа ещё и приводит структуру к метаданным; очень долго, нужно место под копию |
| Сжатие таблиц (`-IBCompression`) | **только файловый вариант** | `VACUUM FULL` / `pg_repack` | в клиент-серверном варианте режима нет |
| Пересчёт итогов (`-RecalcTotals`) | пересчитывает таблицы итогов по движениям | нет | логика приложения |
| Проверка логической целостности (`-LogIntegrity`) | проверяет внутренние связи данных 1С | нет | логика приложения; `amcheck` проверяет физическую структуру, а не смысл |
| Проверка ссылочной целостности (`-LogAndRefsIntegrity`) | ищет «битые» ссылки | нет | внешних ключей в базах 1С нет |
| Проверка целостности хранения двоичных данных (`-BinaryDataStorageIntegrity`) | только клиент-серверный вариант | нет | логика приложения |

Пример пакетного запуска (с рабочего места администратора; на сервере без графики конфигуратору нужен виртуальный X-сервер):

```
"C:\Program Files\1cv8\8.3.27.1688\bin\1cv8.exe" DESIGNER /S "srv1c\buh" /N "Администратор" /P "***" ^
    /IBCheckAndRepair -ReIndex -RecalcTotals -JobsCount 4 /Out "C:\log\check.log"
```

Чего тестирование и исправление **не делает**: не убирает мёртвые строки там, где не пересоздаёт таблицы; не собирает статистику планировщика как самостоятельную операцию; не замораживает транзакции; не чистит системный каталог; не проверяет контрольные суммы страниц.

Чего обслуживание СУБД **не делает**: не проверяет смысл данных 1С, не пересчитывает итоги, не исправляет ссылки.

Вывод: это разные инструменты. Ежедневный регламент — уровень СУБД (разделы 4–7, 15). Тестирование и исправление — ремонт при ошибках или после сбоев, по документации оно предназначено для «диагностики и устранения ошибочных состояний» базы [1С]. После него всегда выполняйте `vacuumdb --analyze`.

## 12. Рост WAL и места на диске; временные файлы

### 12.1. Как формируется размер pg_wal [PG]

- WAL пишется сегментами по 16 МБ в каталог `pg_wal` (Debian-раскладка: `/var/lib/postgresql/NN/main/pg_wal`).
- Контрольная точка запускается каждые `checkpoint_timeout` (умолчание 5 мин) или когда объём WAL приближается к `max_wal_size` (умолчание 1 ГБ) — что наступит раньше. После неё ненужные сегменты удаляются или переименовываются под будущее использование.
- `max_wal_size` — **мягкий** предел: под тяжёлой нагрузкой, при сбое архивации или большом `wal_keep_size` он превышается.
- `min_wal_size` (умолчание 80 МБ) — объём, который всегда оставляется для повторного использования.
- Рекомендации для 1С: `min_wal_size = 512MB..4G`, `max_wal_size = 2 × min_wal_size` [1С][PGPro]; `checkpoint_timeout = 15min` [PGPro].

Нормальный размер `pg_wal` — до `max_wal_size` плюс `wal_keep_size`. Всё, что заметно больше, чем-то удерживается:

| Что удерживает WAL | Признак | Устранение |
|---|---|---|
| Слот репликации, потребитель которого отстал или исчез | `pg_replication_slots`: `active = f`, большой `retained_wal`, `wal_status = extended` | починить реплику/потребителя либо удалить слот |
| Архивация не работает (`archive_command` возвращает ошибку) или не успевает | `pg_stat_archiver.failed_count` растёт, в `pg_wal/archive_status` копятся файлы `*.ready`, в журнале `archive command failed with exit code …` | исправить команду, права, место в архиве |
| Большой `wal_keep_size` | `SHOW wal_keep_size;` | уменьшить |
| Сводка WAL для инкрементальных копий (`summarize_wal = on`, 17+) отстаёт | `pg_get_wal_summarizer_state()` | разобраться с процессом `walsummarizer` |
| Логический слот + длинная транзакция | логическому декодированию нужен WAL с начала самой старой транзакции | завершить транзакцию |
| Массовая операция (реструктуризация, перепроведение, загрузка) | всплеск объёма, контрольные точки идут «по требованию» | это нормально; дождаться, проверить `max_wal_size` |

Сама по себе длинная транзакция **без** логических слотов WAL не удерживает — она вредит очистке (раздел 1.3), но не размеру `pg_wal`.

Особенность 1С: механизм «копии базы данных» в PostgreSQL использует логическую репликацию — модуль `dbcopies_decoding`, нужен `wal_level = logical` [PGPro]. Если обновление копии остановилось, её слот копит WAL на основном сервере.

### 12.2. Диагностика

```bash
df -h /var/lib/postgresql
sudo du -sh /var/lib/postgresql/18/main/pg_wal
sudo ls /var/lib/postgresql/18/main/pg_wal/archive_status | grep -c '\.ready$'
```

```sql
-- Сколько WAL лежит на диске
SELECT count(*) AS segments, pg_size_pretty(sum(size)) AS total FROM pg_ls_waldir();

-- Слоты: кто сколько удерживает (на реплике вместо pg_current_wal_lsn() — pg_last_wal_replay_lsn())
SELECT slot_name, slot_type, database, active, active_pid, wal_status, safe_wal_size,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC NULLS LAST;

-- Архивация
SELECT archived_count, last_archived_wal, last_archived_time,
       failed_count, last_failed_wal, last_failed_time
FROM pg_stat_archiver;

-- Настройки, влияющие на размер
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('max_wal_size', 'min_wal_size', 'wal_keep_size', 'max_slot_wal_keep_size',
               'idle_replication_slot_timeout', 'archive_mode', 'archive_command',
               'checkpoint_timeout', 'wal_level', 'summarize_wal');

-- Темп генерации WAL (с момента stats_reset)
SELECT pg_size_pretty(wal_bytes) AS wal_total, wal_records, wal_fpi, wal_buffers_full, stats_reset FROM pg_stat_wal;
```

Колонки `pg_replication_slots`, полезные при разборе [PG]: `wal_status` (`reserved` — в пределах `max_wal_size`; `extended` — предел превышен, но файлы держатся; `unreserved` — файлы будут удалены на следующей контрольной точке; `lost` — слот непригоден), `safe_wal_size`, `inactive_since` (17+), `invalidation_reason` (17+: `wal_removed`, `rows_removed`, `wal_level_insufficient`; значение `idle_timeout` — с 18, вместе с параметром `idle_replication_slot_timeout`).

### 12.3. Устранение

```sql
-- Удалить ненужный слот (активный удалить нельзя: сначала остановить потребителя)
SELECT pg_drop_replication_slot('имя_слота');

-- После устранения причины — ускорить очистку pg_wal
CHECKPOINT;
```

Страховка от повторения [PG]:

```ini
max_slot_wal_keep_size = 50GB          # умолчание -1: слот может удерживать WAL без ограничения
idle_replication_slot_timeout = 2d     # PostgreSQL 18+: неактивный слот объявляется недействительным; 0 — выключено
```

Слот, вышедший за `max_slot_wal_keep_size`, становится `lost`: WAL удаляется, но реплику или копию базы придётся создавать заново. Это осознанный выбор «лучше потерять реплику, чем остановить основной сервер».

Сломанная архивация:

1. Причина — в журнале сервера: `sudo grep -i 'archive command failed' /var/log/postgresql/postgresql-18-main.log | tail`.
2. Исправить (место в хранилище архива, права, сеть). Накопившиеся сегменты архиватор отправит сам, после чего они удалятся.
3. Крайняя мера, если диск заполнится раньше: временно `archive_command = '/bin/true'` и `reload`. Цепочка WAL в архиве при этом **рвётся** — после восстановления архивации обязательно сделать новую базовую копию.

Категорически нельзя:

- удалять файлы из `pg_wal` вручную (`rm`) — сервер может не запуститься или потерять данные;
- «чистить» `pg_wal` утилитой `pg_archivecleanup` — она предназначена для каталога архива;
- запускать `pg_resetwal` «чтобы освободить место» — это средство последней надежды при повреждении (раздел 14.5).

### 12.4. Диск заполнился

Симптом: сервер остановился с `PANIC: could not write to file "pg_wal/…": No space left on device`.

1. Ничего не удалять в каталоге данных.
2. Освободить место вне его: старые журналы (`/var/log`), старые резервные копии, кеш пакетов (`sudo apt clean`) — либо расширить том (LVM: `sudo lvextend -r -L +20G /dev/vg/lv`, см. `kb/linux/07-diski-fs-lvm.md`).
3. Запустить сервер: `sudo systemctl start postgresql@18-main`; дождаться восстановления по WAL.
4. Найти причину по разделам 12.1–12.3 и запросу ниже.

```sql
SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database ORDER BY pg_database_size(datname) DESC;
```

```bash
sudo du -xsh /var/lib/postgresql/18/main/* | sort -h | tail -n 8
```

Профилактика: мониторинг свободного места с порогами 20 % и 10 %; запас под реструктуризацию и `VACUUM FULL` (копия самой большой таблицы с индексами); [практика] «балластный» файл на 1–2 ГБ на том же томе, который можно удалить в аварии.

### 12.5. Временные файлы

Не путать два разных явления:

| | Временные файлы запросов | Временные таблицы 1С |
|---|---|---|
| Откуда | сортировка, хеш-соединение, материализация не поместились в `work_mem` | `CREATE TEMP TABLE` платформой |
| Где лежат | `base/pgsql_tmp/pgsql_tmp<PID>.<N>` (или в `temp_tablespaces`) | `base/<oid базы>/t<N>_<filenode>` (или в `temp_tablespaces`) |
| Память | `work_mem` | `temp_buffers` |
| Когда удаляются | по окончании операции | при завершении сеанса (или `DROP`) |
| Учёт | `pg_stat_database.temp_files`, `temp_bytes`; `log_temp_files` | обычные функции размера |

```sql
-- Накопленная статистика временных файлов (запрос из статьи ИТС 5866 — для подбора work_mem)
SELECT sum(temp_files) AS temp_files, pg_size_pretty(sum(temp_bytes)) AS temp_size FROM pg_stat_database;

-- По базам
SELECT datname, temp_files, pg_size_pretty(temp_bytes) AS temp_size, stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL ORDER BY temp_bytes DESC;

-- Временные файлы на диске прямо сейчас
SELECT name, pg_size_pretty(size) AS size, modification FROM pg_ls_tmpdir() ORDER BY size DESC LIMIT 20;

-- Временные таблицы на диске сейчас, по сеансам (без учёта данных, ещё не сброшенных из локальных буферов)
SELECT n.nspname, count(*) AS tables,
       pg_size_pretty(sum(pg_total_relation_size(c.oid))) AS size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relpersistence = 't' AND c.relkind = 'r'
GROUP BY n.nspname
ORDER BY sum(pg_total_relation_size(c.oid)) DESC
LIMIT 20;
```

Параметры [PG]:

- `log_temp_files` (умолчание `-1`): `0` — журналировать каждый временный файл, положительное значение — только файлы не меньше указанного размера (в килобайтах, можно `100MB`). Сообщение пишется при удалении файла.
- `temp_file_limit` (умолчание `-1`, без предела): максимум дискового места под временные файлы одного процесса. При превышении запрос отменяется с ошибкой `temporary file size exceeds temp_file_limit`. [практика] Для 1С предел в десятки гигабайт защищает диск от «убежавшего» запроса.
- `temp_tablespaces`: вынести временные объекты на отдельный быстрый диск [1С][PGPro].
- После аварии оставшиеся файлы `pgsql_tmp*` сервер удаляет при запуске сам.

## 13. Контрольные точки и фоновая запись: что наблюдать

### 13.1. Параметры [PG]

| Параметр | Умолчание | Рекомендация для 1С |
|---|---|---|
| `checkpoint_timeout` | `5min` | `15min` [PGPro] |
| `max_wal_size` | `1GB` | `2 × min_wal_size`, то есть 1–8 ГБ [1С][PGPro] |
| `min_wal_size` | `80MB` | `512MB..4G` [1С][PGPro] |
| `checkpoint_completion_target` | `0.9` | `0.5..0.9` [1С]; документация PostgreSQL снижать не советует |
| `checkpoint_warning` | `30s` | не менять |
| `log_checkpoints` | `on` (с версии 15) | оставить включённым |
| `bgwriter_delay` | `200ms` | `20ms` [1С][PGPro] |
| `bgwriter_lru_maxpages` | `100` | `400` [1С][PGPro] |
| `bgwriter_lru_multiplier` | `2.0` | `4.0` [1С][PGPro] |

### 13.2. Представления

PostgreSQL 17 и 18 — `pg_stat_checkpointer` и «похудевший» `pg_stat_bgwriter`:

```sql
SELECT num_timed, num_requested,
       round(100.0 * num_requested / nullif(num_timed + num_requested, 0), 1) AS requested_pct,
       buffers_written,
       round(write_time / 1000) AS write_s,
       round(sync_time / 1000)  AS sync_s,
       stats_reset
FROM pg_stat_checkpointer;

SELECT buffers_clean, maxwritten_clean, buffers_alloc, stats_reset FROM pg_stat_bgwriter;

-- Кто пишет страницы данных на диск (16+)
SELECT backend_type, sum(writes) AS writes, sum(fsyncs) AS fsyncs, sum(evictions) AS evictions
FROM pg_stat_io
WHERE object = 'relation'
GROUP BY backend_type
ORDER BY 2 DESC NULLS LAST;
```

Колонки `pg_stat_checkpointer` [PG]: `num_timed` (плановые по тайм-ауту), `num_requested` (по требованию), `num_done` (реально выполненные; 18+), `restartpoints_timed`/`_req`/`_done` (для реплик), `write_time`, `sync_time` (мс), `buffers_written`, `slru_written` (18+), `stats_reset`.

PostgreSQL 14–16 — всё в `pg_stat_bgwriter`:

```sql
SELECT checkpoints_timed, checkpoints_req,
       round(100.0 * checkpoints_req / nullif(checkpoints_timed + checkpoints_req, 0), 1) AS requested_pct,
       buffers_checkpoint, buffers_clean, maxwritten_clean,
       buffers_backend, buffers_backend_fsync, buffers_alloc, stats_reset
FROM pg_stat_bgwriter;
```

В 17 колонки контрольных точек перенесены в `pg_stat_checkpointer`, а `buffers_backend` и `buffers_backend_fsync` удалены — их заменяет `pg_stat_io` [PG, release notes 17].

Сброс счётчиков перед замером: `SELECT pg_stat_reset_shared('checkpointer');`, `SELECT pg_stat_reset_shared('bgwriter');` (в 14–16 только `'bgwriter'`).

### 13.3. Как читать

| Наблюдение | Что значит | Действие |
|---|---|---|
| доля точек «по требованию» велика (ориентир [практика] — больше 10–20 %) | WAL заполняет `max_wal_size` быстрее, чем наступает тайм-аут | увеличить `max_wal_size` |
| в журнале `checkpoints are occurring too frequently (N seconds apart)` с подсказкой увеличить `max_wal_size` | точки по заполнению WAL идут чаще `checkpoint_warning` | увеличить `max_wal_size`; единичные сообщения во время массовых операций безвредны |
| `maxwritten_clean` быстро растёт | фоновая запись упирается в `bgwriter_lru_maxpages` и останавливает проход | увеличить `bgwriter_lru_maxpages` |
| много записей страниц обслуживающими процессами (`client backend` в `pg_stat_io`; `buffers_backend` в 14–16) | фоновая запись и контрольные точки не успевают освобождать буферы | агрессивнее bgwriter, проверить размер `shared_buffers` |
| `buffers_backend_fsync > 0` (14–16) или `fsyncs` у `client backend` | обслуживающие процессы сами вызывают `fsync` — очередь запросов синхронизации переполнена | проблема дисковой подсистемы или экстремальная нагрузка записи |
| большое `sync_time` | диски медленно выполняют `fsync` | проверить хранилище, кеш контроллера, настройки диска ВМ |

Строка журнала при `log_checkpoints = on` содержит всё нужное: сколько буферов записано, сколько сегментов WAL добавлено/удалено/переиспользовано, время записи и синхронизации, «расстояние» между точками в килобайтах:

```bash
sudo grep 'checkpoint complete' /var/log/postgresql/postgresql-18-main.log | tail -n 20
```

## 14. Целостность данных

### 14.1. Контрольные суммы страниц [PG]

- В PostgreSQL 18 `initdb` включает контрольные суммы **по умолчанию**; отключить — `initdb --no-data-checksums`. В 14–17 их нужно было включать явно: `initdb --data-checksums` (`-k`). Исключение — сборки Postgres Pro: в «PostgreSQL для 1С» 16 кластер, созданный `pg-setup initdb` (в том числе при быстрой установке), получает контрольные суммы по умолчанию (документация `pg-setup` ветки 16) — проверьте `SHOW data_checksums;`.
- В Debian-раскладке параметры `initdb` передаются после `--`: `sudo pg_createcluster 16 main --locale ru_RU.UTF-8 -- --data-checksums`.
- Защищаются только страницы данных (таблицы, индексы). Временные файлы и внутренние структуры — нет.
- Включаются и выключаются для кластера целиком.
- `pg_upgrade` требует одинаковой настройки в старом и новом кластере: при переходе на 18 со старого кластера без сумм новый создают с `--no-data-checksums` (либо сначала включают суммы на старом).

```sql
SHOW data_checksums;                                   -- on / off
SELECT datname, checksum_failures, checksum_last_failure
FROM pg_stat_database WHERE checksum_failures > 0;     -- NULL, если суммы выключены
```

При чтении повреждённой страницы запрос завершается ошибкой вида `invalid page in block N of relation base/…` с предупреждением `page verification failed, calculated checksum … but expected …`, а счётчик `checksum_failures` растёт.

### 14.2. pg_checksums [PG]

```
pg_checksums [option...] [[-D | --pgdata] datadir]
```

Работает **только на штатно остановленном** кластере. Утилита серверная: в Debian-раскладке лежит в `/usr/lib/postgresql/NN/bin/` и в `PATH` не попадает.

| Ключ | Назначение |
|---|---|
| `-c`, `--check` | проверить суммы (режим по умолчанию) |
| `-e`, `--enable` | включить суммы: переписывает все блоки |
| `-d`, `--disable` | выключить: меняет только `pg_control` |
| `-f N`, `--filenode=N` | проверить только отношение с данным filenode |
| `-P`, `--progress` | показывать ход |
| `-v`, `--verbose` | перечислять проверенные файлы |
| `-N`, `--no-sync` | не ждать сброса на диск (только для тестов) |
| `--sync-method=fsync\|syncfs` | способ сброса (с 17) |

```bash
sudo systemctl stop postgresql@18-main
sudo -u postgres /usr/lib/postgresql/18/bin/pg_checksums --check --progress -D /var/lib/postgresql/18/main
echo "код возврата: $?"            # 0 — ошибок нет
# включить суммы на старом кластере (долго: читает и переписывает всю базу)
sudo -u postgres /usr/lib/postgresql/18/bin/pg_checksums --enable --progress -D /var/lib/postgresql/18/main
sudo systemctl start postgresql@18-main
```

- Во время работы утилиты кластер запускать нельзя. Если её прервать, настройка сумм остаётся прежней — команду можно повторить.
- При репликации включать/выключать суммы нужно согласованно на всех узлах (остановить все либо пересоздать реплики).
- Проверка «на ходу»: `pg_basebackup` при снятии базовой копии проверяет суммы по умолчанию и сообщает об ошибках.

### 14.3. amcheck и pg_amcheck [PG]

Расширение `amcheck` проверяет логическую структуру индексов и таблиц:

| Функция | Что проверяет | Блокировка |
|---|---|---|
| `bt_index_check(index regclass, heapallindexed boolean, checkunique boolean)` | инварианты B-дерева; с `heapallindexed` — что каждая строка таблицы есть в индексе; `checkunique` (проверка уникальности) — с 17, в 14–16 его нет | `ACCESS SHARE` — как у `SELECT`, можно на рабочей базе |
| `bt_index_parent_check(index, heapallindexed, rootdescend, checkunique)` | то же плюс связи «родитель — потомок» | `SHARE` — блокирует запись; на реплике не работает |
| `gin_index_check(index regclass)` | структуру GIN-индекса (18+) | — |
| `verify_heapam(relation regclass, on_error_stop, check_toast, skip, startblock, endblock)` | структуру страниц таблицы, по строке на каждое нарушение | — |

```sql
CREATE EXTENSION IF NOT EXISTS amcheck;
SELECT bt_index_check(index => 'public._document123_1'::regclass, heapallindexed => true);
SELECT * FROM verify_heapam('public._document123'::regclass, check_toast => true);
```

Утилита `pg_amcheck` (14+) обходит базу целиком. В Debian-раскладке она лежит в `/usr/lib/postgresql/NN/bin/` (пакет `postgresql-client-NN`), и обёртки в `/usr/bin` для неё **нет**: пакет `postgresql-client-common` в Ubuntu 24.04 и 26.04 создаёт ссылки только для `psql`, `pg_dump`, `pg_dumpall`, `pg_restore`, `pg_basebackup`, `pg_isready`, `pg_receivewal`, `pg_recvlogical`, `vacuumdb`, `reindexdb`, `clusterdb`, `createdb`, `dropdb`, `createuser`, `dropuser`, `pgbench`, `vacuumlo` и устаревших `createlang`, `droplang`, `pg_receivexlog` (проверено по спискам файлов пакета; повторно 19.10.2026 для noble и resolute). Команда `pg_amcheck` без пути даст `command not found` — вызывайте по полному пути. Для Postgres Pro — `/opt/pgpro/1c-NN/bin/pg_amcheck`.

```bash
PGA=/usr/lib/postgresql/18/bin/pg_amcheck

# Все таблицы и B-деревья базы, 4 соединения, с индикатором хода
sudo -u postgres $PGA --install-missing --jobs=4 --progress -d buh

# С проверкой «каждая строка есть в индексе» (в разы дольше)
sudo -u postgres $PGA --heapallindexed --jobs=2 --progress -d buh

# Одна таблица (её индексы и TOAST проверяются автоматически)
sudo -u postgres $PGA -d buh --table='public._document123'

# Все базы кластера, не проверяя уже замороженные страницы
sudo -u postgres $PGA --all --skip=all-frozen --jobs=4

echo "код возврата: $?"      # 0 — всё проверено без замечаний; ненулевой — разбирайте вывод
```

Коды возврата `pg_amcheck` в документации не описаны (уточнено 11.10.2026 по исходному коду `pg_amcheck.c` ветки 18: при найденных повреждениях утилита завершается с кодом 2 (`if (!all_checks_pass) exit(2);`); ранее было не подтверждено: ненулевой код при найденных повреждениях — по памяти рецензента об исходном коде). В скриптах опирайтесь не только на код, но и на вывод: при повреждении утилита печатает строки с именем отношения, номером блока и текстом нарушения.

`pg_amcheck` проверяет обычные таблицы, TOAST-таблицы, материализованные представления, последовательности и индексы B-дерева; отношения других типов (в том числе GIN-индексы — функция `gin_index_check` есть только в самом расширении `amcheck` 18) он молча пропускает [PG]. Ключ `--install-missing` сам создаёт расширение `amcheck` в базе (в схеме `pg_catalog`, если не указана другая) — то есть оставляет в базе 1С новый объект; это безвредно, но при сравнении баз о нём стоит помнить.

Основные ключи: `-a`/`-d шаблон`/`-D шаблон` (базы), `-t`/`-T` (таблицы), `-i`/`-I` (индексы), `-s`/`-S` (схемы), `-r`/`-R` (любые отношения), `--heapallindexed`, `--parent-check`, `--rootdescend`, `--checkunique` (с 17), `--no-dependent-indexes`, `--no-dependent-toast`, `--exclude-toast-pointers`, `--on-error-stop`, `--skip=none|all-visible|all-frozen`, `--startblock`, `--endblock`, `--install-missing[=схема]`, `-j N`, `-P`, `-v`, `-e`. Ключи `--parent-check` и `--rootdescend` берут блокировки, мешающие записи, — не для рабочего времени.

Важно [PG]: `amcheck` доказывает только наличие повреждения, но не его отсутствие; общего способа починки найденного нет; `REINDEX` помогает не всегда — сначала ищите первопричину.

### 14.4. pg_dump как проверка читаемости

```bash
sudo -u postgres pg_dump -Fc -d buh -f /dev/null && echo "все таблицы прочитаны"
```

- `pg_dump` читает каждую строку каждой таблицы, включая TOAST: нечитаемая страница или ошибка контрольной суммы прервёт дамп с ошибкой.
- Индексы `pg_dump` не читает — их проверяет `amcheck`.
- На время работы дамп держит снимок данных (горизонт очистки, раздел 1.3): запускайте ночью и до `vacuumdb`.
- Лучшая проверка — регулярное пробное восстановление резервной копии на стенд с открытием базы в 1С.

### 14.5. Действия при повреждении

1. Остановить запись: запретить сеансы в кластере 1С. Не запускать «на удачу» `VACUUM FULL`, `REINDEX DATABASE`, «Тестирование и исправление».
2. Остановить PostgreSQL и сделать файловую копию всего каталога данных (включая `pg_wal` и табличные пространства) — чтобы было куда вернуться после неудачных попыток.
3. Проверить оборудование и ОС: `dmesg -T | grep -iE 'error|i/o|ata|nvme'`, SMART, память, файловую систему, хранилище гипервизора.
4. Если есть резервная копия и архив WAL — восстановление на момент до повреждения (PITR). Это основной и единственный надёжный путь.
5. Повреждён только индекс (ошибки при чтении по индексу, `bt_index_check`): `REINDEX INDEX CONCURRENTLY имя;`.
6. Повреждены индексы системного каталога: `PGOPTIONS='-P' psql база`, затем `REINDEX SYSTEM база;` [PG].
7. Повреждены страницы таблицы, копии нет — спасение того, что читается, в новую базу. Параметры опасные и только на время выгрузки [PG]:

```sql
SET ignore_checksum_failure = on;   -- читать страницы с неверной суммой; может вызвать сбой или скрыть порчу
SET zero_damaged_pages = on;        -- страницы с испорченным заголовком считать пустыми: строки на них УНИЧТОЖАЮТСЯ
```

```bash
sudo -u postgres env PGOPTIONS='-c ignore_checksum_failure=on' pg_dump -Fc -d buh -f /backup/buh-rescue.dump
```

8. Сервер не запускается из-за повреждения WAL или `pg_control` — `pg_resetwal` как последнее средство [PG]: `pg_resetwal --dry-run -D каталог`, затем `pg_resetwal -f -D каталог`. После него данные могут быть несогласованными: сразу `pg_dump`, новый `initdb`, восстановление. Ничего не изменять в базе до выгрузки.
9. После любого восстановления с потерями — «Тестирование и исправление» в 1С (логическая и ссылочная целостность, пересчёт итогов): на уровне СУБД смысл данных не проверить.
10. Найти первопричину (диск, память, контроллер без защиты кеша при `fsync`, сбой питания ВМ), иначе повторится.

## 15. Готовые скрипты и расписание

Общие принципы:

- Скрипты выполняются от пользователя ОС `postgres`: локальное подключение по сокету с peer-аутентификацией, пароли не нужны.
- Один файл блокировки на все скрипты обслуживания — чтобы очистка, переиндексация и отчёт не накладывались.
- Путь к утилитам — в переменной `PGBIN` (Debian-раскладка: `/usr/lib/postgresql/18/bin`; Postgres Pro: `/opt/pgpro/1c-NN/bin`, для «PostgreSQL для 1С» ветки 16 — `/opt/pgpro/1c-16/bin`).

Подготовка:

```bash
sudo install -d -o postgres -g postgres -m 750 /var/log/postgresql/maintenance
sudo install -d -o root -g root -m 755 /usr/local/share/pg-maint
```

### 15.1. Ночной VACUUM ANALYZE

`/usr/local/sbin/pg-nightly-vacuum.sh`:

```bash
#!/usr/bin/env bash
# Ночная очистка и сбор статистики по всем базам кластера PostgreSQL.
# Запускать от пользователя postgres (cron или systemd timer).
set -Eeuo pipefail

PGBIN="${PGBIN:-/usr/lib/postgresql/18/bin}"
export PGPORT="${PGPORT:-5432}"
JOBS="${JOBS:-4}"
LOGDIR="${LOGDIR:-/var/log/postgresql/maintenance}"
LOCK=/var/lock/pg-maintenance.lock

mkdir -p "$LOGDIR"
LOG="$LOGDIR/vacuum-$(date +%F).log"

exec 9>"$LOCK"
if ! flock -n 9; then
    echo "$(date -Is) пропуск: другое обслуживание ещё выполняется" >>"$LOG"
    exit 0
fi

echo "$(date -Is) начало: vacuumdb --all --analyze --jobs=$JOBS --skip-locked" >>"$LOG"
rc=0
"$PGBIN/vacuumdb" --all --analyze --jobs="$JOBS" --skip-locked >>"$LOG" 2>&1 || rc=$?
echo "$(date -Is) конец, код возврата $rc" >>"$LOG"

find "$LOGDIR" -name 'vacuum-*.log' -mtime +30 -delete
exit "$rc"
```

### 15.2. Еженедельная переиндексация без остановки работы

`/usr/local/sbin/pg-weekly-reindex.sh`:

```bash
#!/usr/bin/env bash
# Еженедельный REINDEX CONCURRENTLY. Аргументы — имена баз; без аргументов — все пользовательские базы.
# Запускать от пользователя postgres.
set -Eeuo pipefail

PGBIN="${PGBIN:-/usr/lib/postgresql/18/bin}"
export PGPORT="${PGPORT:-5432}"
JOBS="${JOBS:-2}"
LOGDIR="${LOGDIR:-/var/log/postgresql/maintenance}"
LOCK=/var/lock/pg-maintenance.lock

mkdir -p "$LOGDIR"
LOG="$LOGDIR/reindex-$(date +%F).log"

exec 9>"$LOCK"
if ! flock -n 9; then
    echo "$(date -Is) пропуск: другое обслуживание ещё выполняется" >>"$LOG"
    exit 0
fi

if [ "$#" -gt 0 ]; then
    DBS=("$@")
else
    mapfile -t DBS < <("$PGBIN/psql" -XAt -d postgres -c \
        "SELECT datname FROM pg_database
          WHERE datallowconn AND NOT datistemplate AND datname <> 'postgres' ORDER BY 1")
fi

rc=0
for db in "${DBS[@]}"; do
    echo "$(date -Is) [$db] reindexdb --concurrently --jobs=$JOBS" >>"$LOG"
    "$PGBIN/reindexdb" --concurrently --jobs="$JOBS" --dbname="$db" >>"$LOG" 2>&1 || rc=$?

    # Недействительные индексы (_ccnew/_ccold), оставшиеся после сбоев
    invalid=$("$PGBIN/psql" -XAt -d "$db" -c \
        "SELECT format('%I.%I', n.nspname, c.relname)
           FROM pg_index i
           JOIN pg_class c ON c.oid = i.indexrelid
           JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE NOT i.indisvalid")
    if [ -n "$invalid" ]; then
        echo "$(date -Is) [$db] ВНИМАНИЕ: недействительные индексы, удалить вручную:" >>"$LOG"
        echo "$invalid" >>"$LOG"
        rc=1
    fi
done

echo "$(date -Is) конец, код возврата $rc" >>"$LOG"
find "$LOGDIR" -name 'reindex-*.log' -mtime +90 -delete
exit "$rc"
```

Для больших баз (сотни гигабайт) полная еженедельная переиндексация избыточна: она идёт часами и порождает WAL размером со все индексы. Тогда перестраивают только раздутые индексы — выборочно, по `pgstatindex`:

```bash
sudo -u postgres psql -X -d buh <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT format('REINDEX INDEX CONCURRENTLY %I.%I', n.nspname, c.relname)
FROM (SELECT ci.oid, ci.relname, ci.relpages, ci.relnamespace
        FROM pg_class ci
        JOIN pg_index x ON x.indexrelid = ci.oid AND x.indisvalid
       WHERE ci.relkind = 'i'
         AND ci.relam = (SELECT oid FROM pg_am WHERE amname = 'btree')
         AND ci.relnamespace = 'public'::regnamespace
         AND ci.relpages > 12800      -- индексы больше 100 МБ
       OFFSET 0) c                    -- OFFSET 0: сначала отобрать индексы, потом вызывать pgstatindex
JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL pgstatindex(c.oid::regclass) s
WHERE s.avg_leaf_density < 60         -- заполненность листьев ниже 60 %
ORDER BY c.relpages DESC
\gexec
SQL
```

`\gexec` выполняет каждую строку результата как отдельную команду. Учтите: `pgstatindex` читает каждый проверяемый индекс целиком.

Замечание рецензента к этому запросу. В исходном варианте автора условие «только B-дерево» задавалось соединением с `pg_am`, а `pgstatindex` вызывалась через `LATERAL` в том же списке `FROM`. Планировщик вправе вызвать функцию раньше, чем отфильтрует тип индекса, и тогда на первом же индексе другого типа запрос упал бы с ошибкой «is not a btree index». Подзапрос с `OFFSET 0` не «разворачивается» планировщиком, поэтому отбор гарантированно выполняется первым. Запрос по-прежнему не выполнялся на стенде. Команды `REINDEX … CONCURRENTLY` из результата выполняются последовательно; если одна завершится ошибкой, psql продолжит со следующей, а недействительный индекс `_ccnew` придётся удалить вручную (раздел 6.2).

### 15.3. Отчёт о состоянии и раздувании

`/usr/local/share/pg-maint/health-report.sql`:

```sql
\pset pager off
\echo '=== База, размер, возраст XID'
SELECT current_database() AS db,
       pg_size_pretty(pg_database_size(current_database())) AS size,
       (SELECT age(datfrozenxid) FROM pg_database WHERE datname = current_database()) AS xid_age;

\echo '=== Топ-15 таблиц по мёртвым строкам'
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 15;

\echo '=== Топ-15 таблиц по размеру'
SELECT c.oid::regclass AS tbl,
       pg_size_pretty(pg_relation_size(c.oid))       AS heap,
       pg_size_pretty(pg_indexes_size(c.oid))        AS indexes,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total
FROM pg_class c
WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace
ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 15;

\echo '=== Системный каталог: 8 самых больших таблиц'
SELECT c.oid::regclass AS catalog_table,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       s.n_live_tup, s.n_dead_tup, s.last_autovacuum
FROM pg_class c JOIN pg_stat_sys_tables s ON s.relid = c.oid
WHERE c.relnamespace = 'pg_catalog'::regnamespace AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 8;

\echo '=== Самые старые открытые транзакции'
SELECT pid, usename, state, now() - xact_start AS xact_age, age(backend_xmin) AS xmin_age, left(query, 60) AS query
FROM pg_stat_activity
WHERE backend_type = 'client backend' AND xact_start IS NOT NULL AND datname = current_database()
ORDER BY xact_start LIMIT 5;

\echo '=== Слоты репликации'
SELECT slot_name, slot_type, active, wal_status,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots;

\echo '=== Недействительные индексы'
SELECT n.nspname, c.relname
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT i.indisvalid;
```

В этот же файл добавьте запросы оценки раздувания из раздела 9.2.

`/usr/local/sbin/pg-health-report.sh`:

```bash
#!/usr/bin/env bash
# Еженедельный отчёт по каждой базе. Запускать от пользователя postgres.
set -Eeuo pipefail

PGBIN="${PGBIN:-/usr/lib/postgresql/18/bin}"
export PGPORT="${PGPORT:-5432}"
LOGDIR="${LOGDIR:-/var/log/postgresql/maintenance}"
SQL=/usr/local/share/pg-maint/health-report.sql

mkdir -p "$LOGDIR"
OUT="$LOGDIR/health-$(date +%F).txt"

mapfile -t DBS < <("$PGBIN/psql" -XAt -d postgres -c \
    "SELECT datname FROM pg_database
      WHERE datallowconn AND NOT datistemplate AND datname <> 'postgres' ORDER BY 1")

for db in "${DBS[@]}"; do
    echo "################ $db ################" >>"$OUT"
    "$PGBIN/psql" -X -d "$db" -f "$SQL" >>"$OUT" 2>&1 || true
done

find "$LOGDIR" -name 'health-*.txt' -mtime +180 -delete
```

Установка прав:

```bash
sudo chown root:root /usr/local/sbin/pg-*.sh /usr/local/share/pg-maint/health-report.sql
sudo chmod 755 /usr/local/sbin/pg-*.sh
sudo chmod 644 /usr/local/share/pg-maint/health-report.sql
sudo -u postgres /usr/local/sbin/pg-nightly-vacuum.sh     # пробный запуск
```

### 15.4. Расписание

Вариант 1 — cron, файл `/etc/cron.d/pg-maintenance` (владелец `root`, права `644`, в имени файла нет точек, в конце — перевод строки):

```
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""
# мин час день месяц день_недели пользователь команда
30 1 * * *  postgres  /usr/local/sbin/pg-nightly-vacuum.sh
0  3 * * 0  postgres  /usr/local/sbin/pg-weekly-reindex.sh
0  7 * * 1  postgres  /usr/local/sbin/pg-health-report.sh
```

Вариант 2 — таймеры systemd (пропущенный запуск будет выполнен после включения сервера благодаря `Persistent=true`).

`/etc/systemd/system/pg-nightly-vacuum.service`:

```ini
[Unit]
Description=PostgreSQL: nightly VACUUM ANALYZE
After=postgresql.service

[Service]
Type=oneshot
User=postgres
Group=postgres
Environment=PGBIN=/usr/lib/postgresql/18/bin
Environment=JOBS=4
ExecStart=/usr/local/sbin/pg-nightly-vacuum.sh
```

`/etc/systemd/system/pg-nightly-vacuum.timer`:

```ini
[Unit]
Description=PostgreSQL: nightly VACUUM ANALYZE (timer)

[Timer]
OnCalendar=*-*-* 01:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Для переиндексации — такая же пара `pg-weekly-reindex.service`/`.timer` с `OnCalendar=Sun *-*-* 03:00:00`; для отчёта — `OnCalendar=Mon *-*-* 07:00:00`. Для Postgres Pro в `After=` укажите `postgrespro-1c-NN.service`, а в `PGBIN` — `/opt/pgpro/1c-NN/bin` (для ветки 16 — `postgrespro-1c-16.service` и `/opt/pgpro/1c-16/bin`).

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pg-nightly-vacuum.timer
systemctl list-timers 'pg-*'
sudo systemctl start pg-nightly-vacuum.service        # пробный запуск вручную
journalctl -u pg-nightly-vacuum.service -n 50 --no-pager
systemd-analyze calendar 'Sun *-*-* 03:00:00'         # проверить выражение расписания
```

Используйте что-то одно — cron или таймеры, не оба сразу.

### 15.5. Обслуживание и окно работы пользователей

| Операция | Пользователи 1С работают? | Замечание |
|---|---|---|
| autovacuum, `VACUUM`, `ANALYZE`, `vacuumdb -z` | да | создаёт ввод-вывод; ручной запуск — ночью |
| `REINDEX CONCURRENTLY`, `reindexdb --concurrently` | да | ждёт завершения длинных транзакций; не совмещать с обновлением конфигурации |
| `pg_repack` | да | секунды `ACCESS EXCLUSIVE` в начале и конце; не совмещать с обновлением конфигурации |
| `pg_amcheck` (без `--parent-check`), `pg_dump` | да | `pg_dump` держит горизонт очистки |
| `REINDEX` без `CONCURRENTLY`, `REINDEX SYSTEM` | нет | запись (а фактически и чтение) блокируется |
| `VACUUM FULL`, `CLUSTER`, `VACUUM FULL` каталога | нет | `ACCESS EXCLUSIVE` |
| «Тестирование и исправление», реструктуризация | нет | монопольный режим 1С |
| `pg_checksums` | нет | сервер остановлен |

Порядок ночью: резервное копирование → `vacuumdb --analyze` → (по воскресеньям) переиндексация → отчёт. Очистка после дампа эффективнее: дамп больше не держит горизонт.

Что учесть в расписании 1С:

- тяжёлые регламентные задания (закрытие месяца, расчёт себестоимости, обмены, обновление полнотекстового индекса) держат длинные транзакции — разведите их по времени с очисткой и переиндексацией;
- для монопольных операций СУБД сначала заблокируйте начало сеансов и регламентные задания информационной базы (консоль администрирования кластера или `rac infobase update … --sessions-deny=on --scheduled-jobs-deny=on --denied-message="…" --permission-code=…`) и завершите активные сеансы; после работ снимите блокировку (`--sessions-deny=off --scheduled-jobs-deny=off`);
- перезапуск рабочих процессов 1С по расписанию закрывает старые соединения с СУБД вместе с их временными таблицами (раздел 10.4).

## Типичные ошибки и подводные камни (симптом → причина → решение)

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | База растёт, запросы замедляются, `n_dead_tup` огромный | autovacuum выключен или не успевает | включить; поднять `autovacuum_vacuum_cost_limit`, число процессов, снизить `scale_factor` (раздел 4.5) |
| 2 | `VACUUM` отработал, а `n_dead_tup` не уменьшился; в отчёте `dead but not yet removable` | горизонт xmin держит длинная транзакция, подготовленная транзакция, слот или реплика | найти держателя (раздел 1.3), завершить, повторить `VACUUM` |
| 3 | После `VACUUM` файл таблицы не уменьшился | так и должно быть: обычный `VACUUM` место ОС не возвращает | если место нужно — `pg_repack` или `VACUUM FULL` (раздел 8) |
| 4 | Пользователи 1С «зависли», в `pg_stat_activity` очередь на блокировку | днём запущен `VACUUM FULL`, `CLUSTER`, `REINDEX` без `CONCURRENTLY` или `vacuumdb -f` | отменить (`pg_cancel_backend`); такие операции — только в окне обслуживания |
| 5 | После обновления конфигурации отчёты и проведение резко замедлились | у пересозданных таблиц нет статистики | `vacuumdb --analyze-only -j 4 база` |
| 6 | После восстановления из дампа или загрузки `.dt` всё медленно | статистика не восстанавливается (в 18 — только с `pg_dump --statistics`) | `vacuumdb --analyze-in-stages база` |
| 7 | После сбоя сервера таблицы начали раздуваться | счётчики статистики обнулились, autovacuum «не знает» о мусоре | `vacuumdb --all --analyze` после каждого аварийного старта |
| 8 | Настройки `ALTER TABLE … SET (autovacuum_…)` «пропали» | таблица пересоздана реструктуризацией | хранить настройки в скрипте, применять после каждого обновления |
| 9 | Планирование любого запроса занимает сотни миллисекунд, CPU загружен | раздут системный каталог (`pg_attribute`, `pg_class`) из-за потока временных таблиц | раздел 11.1: устранить держателя горизонта, `VACUUM`, при необходимости `VACUUM FULL` каталога в окне |
| 10 | В журнале `WARNING: database "…" must be vacuumed within N transactions` | возраст XID приближается к пределу | раздел 10.4, не откладывая |
| 11 | `age(datfrozenxid)` растёт, хотя все таблицы очищены | старые временные таблицы в долгоживущих соединениях либо слот/подготовленная транзакция | запрос по временным таблицам (раздел 10.4); перезапуск `rphost` |
| 12 | `REINDEX CONCURRENTLY` «висит» часами | ждёт завершения длинной транзакции | найти её (`pg_stat_progress_create_index.phase`, `current_locker_pid`), дождаться или завершить |
| 13 | В таблице появились индексы `…_ccnew` со статусом `INVALID` | `REINDEX CONCURRENTLY` прерван | `DROP INDEX CONCURRENTLY`, повторить |
| 14 | `pg_wal` занимает десятки гигабайт | неактивный слот, сломанная архивация, большой `wal_keep_size` | раздел 12; файлы вручную не удалять |
| 15 | Сервер остановился: `No space left on device` | диск заполнен (WAL, реструктуризация, временные файлы) | раздел 12.4: освободить место вне каталога данных, запустить, найти причину |
| 16 | В журнале `checkpoints are occurring too frequently` | мал `max_wal_size` для текущей нагрузки | увеличить `max_wal_size` (раздел 13) |
| 17 | В журнале `canceling autovacuum task` | автоочистка уступила блокировке (DDL платформы, ручной `ANALYZE`, `REINDEX`) | единично — норма; постоянно на одной таблице — найти конкурента |
| 18 | `pg_repack` падает с `must have a primary key or not-null unique keys` | у таблицы нет подходящего ключа | для неё — `VACUUM FULL` в окне |
| 19 | `pg_repack`: `already has a trigger called repack_trigger` | прошлый запуск прерван | `DROP EXTENSION pg_repack CASCADE; CREATE EXTENSION pg_repack;` и повторить |
| 20 | `vacuumdb --analyze-in-stages` на рабочей базе ухудшил планы | первые проходы заменили хорошую статистику грубой | дождаться конца; впредь использовать `--analyze-only` |
| 21 | Оценочный запрос раздувания показывает бессмыслицу | нет свежей статистики; либо в чужом скрипте есть `\d` в регулярном выражении, а на сервере `standard_conforming_strings = off` (обратная косая черта теряется) | `ANALYZE`; использовать запросы раздела 9.2 (там `[0-9]`) или `pgstattuple` |
| 22 | `ERROR: VACUUM cannot run inside a transaction block` | команда выполнена внутри `BEGIN` или в инструменте, оборачивающем всё в транзакцию | запускать отдельной командой в режиме автофиксации (`psql -c`) |
| 23 | Ошибка `invalid page in block …` / `page verification failed` | повреждение страницы (диск, память, сбой питания без защиты кеша) | раздел 14.5; не «чинить» наугад |
| 24 | Автоочистка идёт постоянно и грузит диск | слишком низкие пороги при слабом диске либо она не может догнать поток мусора | смотреть `pg_stat_progress_vacuum`; поднять `cost_limit` (быстрее закончит), а не отключать |
| 25 | Отключили autovacuum «на время загрузки» и забыли | человеческий фактор | не отключать вовсе; проверка: `SHOW autovacuum;` и `reloptions` с `autovacuum_enabled=false` |
| 26 | «Тестирование и исправление» запускают еженедельно «для профилактики» | перенос привычек файловых баз | для клиент-серверной базы регламент — на уровне СУБД; тестирование — по необходимости |
| 27 | `idle_in_transaction_session_timeout` оборвал закрытие месяца | значение меньше легальной паузы внутри транзакции 1С | увеличить или снять; задавать на базу, не глобально |
| 28 | Ручной `ANALYZE` по расписанию каждые несколько минут, а автоочистка таблицы не завершается | конфликт `SHARE UPDATE EXCLUSIVE`: `ANALYZE` прерывает autovacuum | убрать частый ручной `ANALYZE`, настроить пороги автоанализа |

## Быстрая шпаргалка — «задача → команда»

| Задача | Команда |
|---|---|
| Очистить и проанализировать все базы | `sudo -u postgres vacuumdb --all --analyze --jobs=4 --skip-locked` |
| Только статистика одной базы | `sudo -u postgres vacuumdb --analyze-only --jobs=4 buh` |
| Статистика после восстановления | `sudo -u postgres vacuumdb --analyze-in-stages buh` |
| Очистить одну таблицу с отчётом | `VACUUM (VERBOSE, ANALYZE) public._accumrgt4567;` |
| Вернуть место ОС (монопольно) | `VACUUM (FULL, VERBOSE, ANALYZE) public._inforg8901;` |
| Вернуть место без остановки | `sudo -u postgres /usr/lib/postgresql/18/bin/pg_repack -d buh -t public._inforg8901 --no-order` |
| Перестроить индексы таблицы без остановки | `REINDEX (VERBOSE) TABLE CONCURRENTLY public._document123;` |
| Перестроить все индексы базы без остановки | `sudo -u postgres reindexdb --concurrently --jobs=2 buh` |
| Перестроить индексы системного каталога | `sudo -u postgres reindexdb --system buh` |
| Найти недействительные индексы | `SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;` |
| Топ таблиц по мёртвым строкам | `SELECT relname, n_dead_tup, last_autovacuum FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;` |
| Что делает автоочистка сейчас | `SELECT pid, query FROM pg_stat_activity WHERE backend_type = 'autovacuum worker';` |
| Ход `VACUUM` | `SELECT * FROM pg_stat_progress_vacuum;` |
| Ход `VACUUM FULL` / `CLUSTER` | `SELECT * FROM pg_stat_progress_cluster;` |
| Ход `REINDEX` | `SELECT * FROM pg_stat_progress_create_index;` |
| Ход `ANALYZE` | `SELECT * FROM pg_stat_progress_analyze;` |
| Параметры автоочистки | `SELECT name, setting FROM pg_settings WHERE name LIKE 'autovacuum%';` |
| Порог автоочистки для одной таблицы | `ALTER TABLE t SET (autovacuum_vacuum_scale_factor = 0, autovacuum_vacuum_threshold = 20000);` |
| Таблицы с индивидуальными настройками | `SELECT oid::regclass, reloptions FROM pg_class WHERE reloptions IS NOT NULL;` |
| Самые старые транзакции | `SELECT pid, state, now() - xact_start, query FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 10;` |
| Отменить запрос / разорвать сеанс | `SELECT pg_cancel_backend(pid);` / `SELECT pg_terminate_backend(pid);` |
| Подготовленные транзакции | `SELECT * FROM pg_prepared_xacts;` |
| Возраст XID по базам | `SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;` |
| Заморозить самые старые таблицы | `sudo -u postgres vacuumdb --all --min-xid-age=150000000 --jobs=4` |
| Размер таблиц каталога | `SELECT oid::regclass, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class WHERE relnamespace = 'pg_catalog'::regnamespace AND relkind = 'r' ORDER BY pg_total_relation_size(oid) DESC LIMIT 10;` |
| Точное раздувание таблицы | `SELECT * FROM pgstattuple_approx('public.t'::regclass);` |
| Точное раздувание индекса | `SELECT avg_leaf_density FROM pgstatindex('public.i'::regclass);` |
| Размер `pg_wal` | `SELECT count(*), pg_size_pretty(sum(size)) FROM pg_ls_waldir();` |
| Слоты репликации | `SELECT slot_name, active, wal_status, restart_lsn FROM pg_replication_slots;` |
| Удалить слот | `SELECT pg_drop_replication_slot('имя');` |
| Состояние архивации | `SELECT * FROM pg_stat_archiver;` |
| Контрольные точки (17+) | `SELECT num_timed, num_requested, write_time, sync_time FROM pg_stat_checkpointer;` |
| Контрольные точки (14–16) | `SELECT checkpoints_timed, checkpoints_req FROM pg_stat_bgwriter;` |
| Временные файлы по базам | `SELECT datname, temp_files, pg_size_pretty(temp_bytes) FROM pg_stat_database;` |
| Включены ли контрольные суммы | `SHOW data_checksums;` |
| Ошибки контрольных сумм | `SELECT datname, checksum_failures FROM pg_stat_database WHERE checksum_failures > 0;` |
| Проверить суммы офлайн | `sudo -u postgres /usr/lib/postgresql/18/bin/pg_checksums --check -P -D /var/lib/postgresql/18/main` |
| Проверить таблицы и индексы | `sudo -u postgres /usr/lib/postgresql/18/bin/pg_amcheck --install-missing --jobs=4 -P -d buh` (обёртки в `/usr/bin` нет) |
| Проверить читаемость данных | `sudo -u postgres pg_dump -Fc -d buh -f /dev/null` |
| Журнал автоочистки | `sudo grep 'automatic vacuum' /var/log/postgresql/postgresql-18-main.log \| tail` |
| Применить изменения `postgresql.conf` | `sudo systemctl reload postgresql@18-main` или `SELECT pg_reload_conf();` |

## Источники

Замечание о методе: веб-поиск в этой сессии был недоступен (исчерпан лимит запросов), поэтому использовались только прямые обращения к известным адресам первоисточников. Материалы сообщества (Инфостарт, Хабр, форумы) найти и прочитать не удалось — утверждения с пометкой [практика] основаны на знаниях автора и не подкреплены ссылкой.

Документация PostgreSQL 18 (страницы «current», сборка 18.6):

- https://www.postgresql.org/docs/current/sql-vacuum.html — синтаксис и опции `VACUUM`, параллельный режим, права, блокировки.
- https://www.postgresql.org/docs/current/routine-vacuuming.html — принципы очистки, формулы порогов автоочистки, заморозка, сообщения и порядок действий при wraparound, мультитранзакции, поведение autovacuum при конфликте блокировок, временные таблицы.
- https://www.postgresql.org/docs/current/runtime-config-vacuum.html — все параметры `autovacuum_*`, `vacuum_*` и их умолчания.
- https://www.postgresql.org/docs/current/sql-analyze.html, https://www.postgresql.org/docs/current/planner-stats.html, https://www.postgresql.org/docs/current/sql-createstatistics.html, https://www.postgresql.org/docs/current/runtime-config-query.html — `ANALYZE`, `default_statistics_target`, расширенная статистика.
- https://www.postgresql.org/docs/current/sql-reindex.html, https://www.postgresql.org/docs/current/app-reindexdb.html — `REINDEX`, `CONCURRENTLY`, недействительные индексы, ключи `reindexdb`.
- https://www.postgresql.org/docs/current/app-vacuumdb.html — ключи `vacuumdb`.
- https://www.postgresql.org/docs/current/sql-cluster.html — `CLUSTER`.
- https://www.postgresql.org/docs/current/progress-reporting.html — `pg_stat_progress_vacuum`, `_analyze`, `_cluster`, `_create_index`, фазы.
- https://www.postgresql.org/docs/current/monitoring-stats.html — `pg_stat_all_tables`, `pg_stat_database`, `pg_stat_bgwriter`, `pg_stat_checkpointer`, `pg_stat_archiver`, `pg_stat_wal`, `pg_stat_io`; сброс счётчиков при нештатной остановке; предупреждение о `pg_stat_reset()`.
- https://www.postgresql.org/docs/current/explicit-locking.html, https://www.postgresql.org/docs/current/sql-altertable.html — режимы блокировок, блокировка при изменении параметров хранения.
- https://www.postgresql.org/docs/current/storage-hot.html — HOT-обновления.
- https://www.postgresql.org/docs/current/pgstattuple.html, https://www.postgresql.org/docs/current/pgfreespacemap.html — оценка раздувания.
- https://www.postgresql.org/docs/current/amcheck.html, https://www.postgresql.org/docs/current/app-pgamcheck.html — проверка индексов и таблиц.
- https://www.postgresql.org/docs/current/checksums.html, https://www.postgresql.org/docs/current/app-pgchecksums.html — контрольные суммы.
- https://www.postgresql.org/docs/current/runtime-config-developer.html, https://www.postgresql.org/docs/current/app-pgresetwal.html — `zero_damaged_pages`, `ignore_checksum_failure`, `pg_resetwal`.
- https://www.postgresql.org/docs/current/wal-configuration.html, https://www.postgresql.org/docs/current/runtime-config-wal.html, https://www.postgresql.org/docs/current/runtime-config-replication.html, https://www.postgresql.org/docs/current/view-pg-replication-slots.html — контрольные точки, размер WAL, слоты, `max_slot_wal_keep_size`, `idle_replication_slot_timeout`.
- https://www.postgresql.org/docs/current/runtime-config-client.html, https://www.postgresql.org/docs/current/runtime-config-resource.html, https://www.postgresql.org/docs/current/runtime-config-logging.html — тайм-ауты сеансов, память обслуживания, `temp_file_limit`, параметры bgwriter, `log_autovacuum_min_duration`, `log_temp_files`, `log_checkpoints`.
- https://www.postgresql.org/docs/current/functions-admin.html — функции размеров, WAL, управления сеансами.
- https://www.postgresql.org/docs/current/app-pgdump.html, https://www.postgresql.org/docs/current/sql-prepare.html — выгрузка статистики в 18, перепланирование подготовленных запросов.
- https://www.postgresql.org/docs/current/release-18.html, https://www.postgresql.org/docs/17/release-17.html — что изменилось в 17 и 18 (память `VACUUM`, `pg_stat_checkpointer`, `MAINTAIN`, `autovacuum_worker_slots`, `autovacuum_vacuum_max_threshold`, суммы по умолчанию, перенос статистики `pg_upgrade`, `idle_replication_slot_timeout`).
- https://www.postgresql.org/ — актуальные выпуски на 10.10.2026: 18.6, 17.11, 16.15, 15.19, 14.24 (13.08.2026); 19 Beta 4 (24.09.2026); окончание поддержки 14 — 12.11.2026. На 19.10.2026 (https://www.postgresql.org/support/versioning/) младшие версии те же; вышел 19 RC 1 (15.10.2026).
- https://www.postgresql.org/download/linux/ubuntu/ — репозиторий PGDG для Ubuntu.

Postgres Professional (документация Postgres Pro Standard 18.6.2):

- https://postgrespro.ru/docs/postgrespro/18/routine-vacuuming, https://postgrespro.ru/docs/postgrespro/current/routine-reindex — общие рекомендации по очистке и переиндексации.
- https://postgrespro.ru/docs/postgrespro/current/config-one-c, https://postgrespro.ru/docs/postgrespro/18/one-c-configuring-server, https://postgrespro.ru/docs/postgrespro/18/one-c-additional-modules — приложение K «Настройка Postgres Pro для решений 1С»: автоочистка, контрольные точки, bgwriter, `max_locks_per_transaction` и «потерянные» временные таблицы, модули.
- https://postgrespro.ru/docs/postgrespro/18/fasttrun, https://postgrespro.ru/docs/postgrespro/current/online-analyze, https://postgrespro.ru/docs/postgrespro/18/plantuner — модули для 1С.

1С:

- https://its.1c.ru/db/metod8dev/content/5866/hdoc — «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2» (ред. 19.06.2025): параметры автоочистки, WAL, bgwriter, запрос по временным файлам. При первой записи страница была получена с искажённой кодировкой; 19.10.2026 значения сверены с конспектом `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md`, составленным по полному тексту.
- https://its.1c.ru/db/metod8dev/content/5837/hdoc — «Регламентные операции на уровне СУБД для MS SQL Server» (ред. 18.11.2022): состав регламента и периодичность. Текст прочитан 10.10.2026 (раздел 5.1); периодичность повторно сверена 19.10.2026 по тексту во фрейме `…/scenarios/i8105837.htm` (кодировка windows-1251).
- https://its.1c.ru/db/metod8dev/content/6035/hdoc — статья от 25.09.2025 о параметре `enable_temp_rd_buffers` сборок 1С; текст сверен 10.10.2026 (раздел 11.1), конспект — `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md`, раздел 6.
- https://its.1c.ru/db/metod8dev/browse/13/-1/3199/3258/3259/3263 — перечень статей ИТС по PostgreSQL (19.10.2026 повторно: те же девять статей — 5825, 5822, 5866, 5942, 5947, 5971, 6031, 6032, 6035).
- Документация платформы 8.3.27 (по конспектам `kb/its-docs/`): `adm-gl06-administrirovanie-ib-p3.md` (тестирование и исправление), `adm-pr07-parametry-zapuska-1cv8-p1.md` и `-p2.md` (`/UpdateDBCfg`, `/IBCheckAndRepair`), `adm-pr03-sluzhebnye-fajly-p2.md` (`UpdateDBCfg`, `RestructJavaOpts` в `conf.cfg`), `adm-gl06-administrirovanie-ib-p2.md` (количество заданий пересчёта итогов).

Прочее:

- https://reorg.github.io/pg_repack/ — pg_repack 1.5.3: принцип работы, требования, ключи, сообщения об ошибках.
- https://packages.ubuntu.com/search?keywords=repack&searchon=names&suite=all&section=all — пакеты `postgresql-NN-repack` в выпусках Ubuntu.
- https://wiki.postgresql.org/wiki/Show_database_bloat, https://github.com/ioguix/pgsql-bloat-estimation — общепринятые запросы оценки раздувания (в статье даны собственные упрощённые запросы).

Независимая сверка 19.10.2026 (что использовано дополнительно):

- Текстовые копии документации PostgreSQL 18 (сняты 10–11.10.2026): `routine-vacuuming`, `sql-vacuum`, `sql-analyze`, `sql-reindex`, `sql-cluster`, `app-vacuumdb`, `app-reindexdb`, `app-pgdump`, `pgupgrade`, `runtime-config-vacuum`, `-resource`, `-wal`, `-replication`, `-logging`, `-query`, `progress-reporting`, `monitoring-stats`, `view-pg-replication-slots`, `pgstattuple`, `pgfreespacemap`, `amcheck`, `app-pgamcheck`, `app-pgchecksums`, `app-pgbasebackup`, `conf-sample-18`, `release-16`/`-17`/`-18`; страницы https://www.postgresql.org/docs/18/routine-reindex.html, `planner-stats.html`, `sql-createstatistics.html`, https://www.postgresql.org/docs/19/release-19.html.
- Исходный код PostgreSQL (`raw.githubusercontent.com/postgres/postgres/<ветка>/…`): `src/backend/access/transam/varsup.c` (ветки 14–18, тексты сообщений о wraparound), `src/backend/access/heap/vacuumlazy.c` (14, 15, 16, 18), `src/backend/access/heap/heapam_handler.c` (18, фазы `VACUUM FULL`), `src/backend/storage/ipc/procarray.c` (18, `GetSnapshotData`), `src/backend/postmaster/autovacuum.c` (9.6, 10, 11), `src/backend/catalog/namespace.c`, `src/backend/access/transam/xact.c`, `src/backend/utils/adt/lockfuncs.c`, `src/backend/storage/lmgr/lock.c` (14, 15), `src/backend/utils/misc/guc_tables.c` (18), `contrib/amcheck/verify_nbtree.c` (18); документация в исходниках `doc/src/sgml/maintenance.sgml` (14–17), `config.sgml` (16), `monitoring.sgml` (16, 17), `amcheck.sgml` и `ref/pg_checksums.sgml` (16, 17).
- Документация «PostgreSQL для 1С» 16 (Postgres Professional, `repo.postgrespro.ru/doc/pg1c/16/ru/html/`): приложение K (K.3 и K.4; текст K.3 побайтно совпадает с веткой 18), `online-analyze`, `plantuner`, `fasttrun`, `dbcopies_decoding`, `pg-setup`, `pg-wrapper`, перечень `contrib`, примечания к выпускам 16 и 16.14; индексы пакетов `repo.postgrespro.ru/1c/1c-16/ubuntu/dists/{jammy,noble}/main/binary-amd64/Packages` (19.10.2026: только `postgrespro-1c-16*`, версия 16.14); https://postgrespro.ru/docs/postgrespro/18/binary-installation-on-linux (пакет `pg-repack-std-18`).
- pg_repack: `raw.githubusercontent.com/reorg/pg_repack/{master,ver_1.5.3}/doc/pg_repack.rst` (поддерживаемые версии, ключи, сообщения, журнал выпусков 1.5.0–1.5.3), `…/ver_1.5.3/lib/pg_repack.sql.in` (имена служебных таблиц, `repack.primary_keys`, исключение системных схем).
- Ubuntu: https://packages.ubuntu.com/search?keywords=repack&searchon=names&suite=all&section=all, `…/resolute/amd64/postgresql-18-repack/filelist`, `…/{noble,resolute}/all/postgresql-client-common/filelist`.
- 1С: перечень статей раздела ИТС по PostgreSQL и текст статьи 5837 (19.10.2026); конспекты базы `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md`, `razmeshchenie-dannyh-i-indeksy.md`, `razmeshchenie-dannyh-tablicy-i-polya.md`, `kb/its-docs/adm-pr03-sluzhebnye-fajly-p2.md`, `adm-pr07-parametry-zapuska-1cv8-p1.md`/`-p2.md`, `adm-gl06-administrirovanie-ib-p2.md`/`-p3.md`, `cs-gl01-trebovaniya.md`, `cs-gl05-administrirovanie-klastera-p3.md`; `kb/guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md` (раскладка и журнал сборки 16).

