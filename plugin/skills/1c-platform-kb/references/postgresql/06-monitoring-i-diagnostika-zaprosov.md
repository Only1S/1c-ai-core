# Мониторинг и диагностика PostgreSQL под 1С: статистика, блокировки, медленные запросы, EXPLAIN

> **Официальные тексты по теме** (конспекты документации ИТС 8.3.27 и методических статей ИТС, составлены по полным текстам): `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`, `../its-metod/razmeshchenie-dannyh-i-indeksy.md`. Статья писалась до получения доступа к закрытой документации: там, где ниже сказано «документация закрыта», «не прочитано» или стоит ⚠, сверяйтесь с этими конспектами — при расхождении правы они.

> Статус: проверено независимой сверкой 19.10.2026: утверждения о PostgreSQL (параметры журналирования и статистики, их умолчания и способ применения, представления `pg_stat_*`, `pg_locks`, имена событий ожидания, `pg_stat_statements`, `auto_explain`, `EXPLAIN`, сообщения журнала, размер таблицы блокировок) сверены с документацией PostgreSQL 18, замечаниями к выпускам 15–18 и исходным кодом веток REL_16/17/18_STABLE; сведения о сборке «PostgreSQL для 1С» 16 — с её документацией (приложения F и K, `auto_dump`) и индексом пакетов 16.14; Postgres Pro Standard 17 (`pg_wait_sampling`, `pgpro_stats`, `pgpro_pwr`, `pg_hint_plan` для 1С) — с документацией postgrespro.ru; сторонние инструменты (pgBadger 13.2, pg_activity, pgcenter, pg_profile 4.16, шаблоны Zabbix 7.4 и плагин агента 2, mamonsu 3.5.18, postgres_exporter 0.20.1) — с README, журналами изменений и исходным кодом на GitHub и git.zabbix.com; версии пакетов — с packages.ubuntu.com и индексом apt.postgresql.org; утверждения о 1С — с конспектами `../its-docs/` и `../its-metod/`. Исправлено 12 ошибок, закрыто 4 пометки «⚠»; на сервере не проверялось. Ранее (10.10.2026) выполнялась программная сверка имён, умолчаний и колонок с документацией PostgreSQL 18; официальные рекомендации 1С — в `../its-metod/`.

> Область: наблюдение за работающим сервером PostgreSQL, обслуживающим «1С:Предприятие 8» (клиент-серверный вариант, Ubuntu Server): кто что делает, кто кого блокирует, какие запросы самые дорогие, как читать план и как пройти путь «жалоба пользователя → причина → исправление». | Версии: PostgreSQL 14–18 (текущая на 2026-10-10 — **18.6** от 2026-08-13; поддерживаются 14.24, 15.19, 16.15, 17.11, 18.6; PostgreSQL 14 снимается с поддержки 2026-11-12; PostgreSQL 19 — Beta 4 от 2026-09-24, не выпущен; на 19.10.2026 — RC 1 от 2026-10-15, по-прежнему не выпущен); сборки для 1С — «PostgreSQL с патчем от 1С» и Postgres Pro 1С/Standard 14–18; платформа 1С 8.3.2x / 8.5.x; Ubuntu 22.04 / 24.04 / 26.04. | Актуальность: 2026-10-10

Пометки в тексте: **[офиц.]** — документация PostgreSQL / Postgres Pro / ИТС; **[практика]** — опыт сообщества; **⚠ не подтверждено** — не удалось сверить с первоисточником, проверяйте на своём стенде.

Связанные статьи базы знаний (не дублируются здесь):

- `kb/postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md` — сборки, пакеты, пути (`/etc/postgresql/NN/main`, `/opt/pgpro/1c-NN`);
- `kb/postgresql/02-postgresql-conf-tyuning-dlya-1c.md` — настройка `postgresql.conf` под 1С;
- `kb/postgresql/03-administrirovanie-psql-i-utility.md` — `psql`, роли, `ALTER SYSTEM`;
- `kb/postgresql/05-obsluzhivanie-vacuum-analyze-reindex.md` — VACUUM / ANALYZE / REINDEX, раздувание;
- `kb/1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md` — технологический журнал (ТЖ), `logcfg.xml`;
- `kb/1c/03-administrirovanie-klastera-ras-rac.md` — `rac`, поля сеансов и соединений;
- `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md` — конспект статей ИТС 6011 / 6031 / 6032 / 6039 (методика расследования, `auto_dump`, `pg_wait_sampling`);
- `kb/its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md` — конспект статьи ИТС 6006 (методика расследования ошибок блокировок, в том числе запросы к `pg_locks`);
- `kb/1c/10-proizvoditelnost-otkazoustojchivost-ekspluataciya.md` — производительность и эксплуатация сервера 1С;
- `kb/its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`, `kb/its-metod/razmeshchenie-dannyh-i-indeksy.md` — таблицы, поля и индексы 1С;
- `kb/linux/02-tekst-i-logi.md` — разбор ТЖ и журналов утилитами `grep` / `awk` / `perl`.

Условные обозначения в командах: кластер PostgreSQL в раскладке Debian/Ubuntu — версия `18`, имя `main` (служба `postgresql@18-main`, конфигурация `/etc/postgresql/18/main/`, журнал `/var/log/postgresql/postgresql-18-main.log`); для Postgres Pro 1С подставляйте службу `postgrespro-1c-17` и каталог данных `/var/lib/pgpro/1c-17/data`. **У пользователя этой базы знаний — бесплатная сборка «PostgreSQL для 1С» ветки 16:** служба `postgrespro-1c-16`, программы `/opt/pgpro/1c-16/bin`, каталог данных `/var/lib/pgpro/1c-16/data`, журнал сервера `/var/lib/pgpro/1c-16/data/log` (сборщик журнала включает `pg-setup`), каталог Unix-сокета — `/tmp` (сверено 19.10.2026 с `../guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`, раздел 7). Запросы к представлениям ниже писались под 17–18: на 16 действуют оговорки «до 17» (`pg_stat_bgwriter` вместо `pg_stat_checkpointer`, `blk_read_time` вместо `shared_blk_read_time`, старые имена событий ожидания). Кластер пользователя создаётся в локали `en_US.UTF-8`, а `initdb` записывает её же в `lc_messages`, поэтому сообщения журнала, скорее всего, уже английские и для pgBadger менять ничего не нужно — проверьте `SHOW lc_messages;`. База 1С в примерах — `erp`.

## Кратко — 20 главных фактов и команд

1. **Первый взгляд на сервер** — `pg_stat_activity`: `SELECT pid, state, wait_event_type, wait_event, now()-xact_start AS xact, now()-query_start AS q, left(query,100) FROM pg_stat_activity WHERE state <> 'idle' ORDER BY xact_start;` **[офиц.]**
2. **Все соединения 1С выглядят одинаково**: `usename` — роль из свойств информационной базы, `client_addr` — адрес сервера 1С (а не рабочего места пользователя), `application_name` — `1CV8` (**⚠ не подтверждено** по документации; проверьте: `SELECT DISTINCT application_name FROM pg_stat_activity;`). Пользователя 1С по `pg_stat_activity` определить нельзя.
3. **Связь «бэкенд PostgreSQL ↔ сеанс 1С»** — через PID серверного процесса: свойство `Dbpid` (`dbpid=…`) событий `DBPOSTGRS` технологического журнала **[офиц., ИТС]** и поле `db-proc-info` в `rac session list` / «Соединение с СУБД» в консоли кластера **[офиц., ИТС]** равны `pg_stat_activity.pid`. Соединения берутся из пула, поэтому связь действует только пока соединение «захвачено» сеансом (идёт вызов СУБД, открыта транзакция или удерживаются временные таблицы).
4. **Кто кого блокирует** — функция `pg_blocking_pids(pid)` **[офиц.]**; самосоединение `pg_locks` документация прямо называет ненадёжным. Готовое «дерево блокировок» — запрос Q-09 в библиотеке ниже.
5. **Два уровня блокировок.** Управляемые блокировки 1С (события ТЖ `TLOCK`, `TTIMEOUT`, `TDEADLOCK`) живут в менеджере блокировок сервера 1С и в PostgreSQL **не видны**. Блокировки СУБД видны в `pg_locks` и журнале PostgreSQL. В управляемом режиме 1С работает с PostgreSQL на уровне изоляции Read Committed с блокировками строк; в автоматическом — Serializable с блокировками таблиц (документация платформы; подтверждено 11.10.2026 таблицей из главы 9 «Руководства разработчика» 8.3.27: автоматические блокировки на PostgreSQL — блокировки таблиц, Serializable; управляемые — блокировки записей, Read Committed; ранее: в этой сессии не перечитывалась).
6. **Время ожидания блокировки** платформа задаёт сеансу сама: `SET lock_timeout = 20000` (20 с, параметр информационной базы «Время ожидания блокировки данных») **[офиц., ИТС 6011]**. Истечение → `ERROR: canceling statement due to lock timeout` (SQLSTATE `55P03`), в 1С — «Конфликт блокировок при выполнении транзакции».
7. **Журнал ожиданий блокировок**: `log_lock_waits = on` — сообщение пишется, когда ожидание превысило `deadlock_timeout` (по умолчанию `1s`) **[офиц.]**.
8. **`pg_stat_statements`** — обязательное расширение: `shared_preload_libraries = 'pg_stat_statements'` (перезапуск), `CREATE EXTENSION pg_stat_statements;`, топ: `SELECT calls, total_exec_time, mean_exec_time, rows, query FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;` **[офиц.]**
9. **Особенность 1С**: запросы обращаются к временным таблицам `tt<N>` (`pg_temp.tt7`), номер и OID которых разные в разных соединениях, поэтому один и тот же запрос 1С даёт много записей в `pg_stat_statements`. Лечится увеличением `pg_stat_statements.max` (10000 — рекомендация ИТС 6011) и группировкой с заменой `tt\d+` (запрос Q-27). В PostgreSQL 18 идентификатор запроса считается по имени таблицы, а не по OID **[офиц., release notes 18]**.
10. **План запроса 1С вне платформы**: перед `EXPLAIN` выставить параметры сеанса, которые ставит платформа: `SET enable_mergejoin = off; SET cpu_operator_cost = 0.001; SET lock_timeout = 20000; SET escape_string_warning = off;` **[офиц., ИТС 6011]** — иначе план будет другим.
11. **`EXPLAIN (ANALYZE, BUFFERS)` выполняет запрос на самом деле**; изменяющие запросы оборачивать в `BEGIN; … ROLLBACK;` **[офиц.]**. В PostgreSQL 18 `BUFFERS` включается вместе с `ANALYZE` автоматически.
12. **Главное при чтении плана** — сравнить оценку `rows=` с фактом `actual … rows=` и не забыть умножить `actual time` и `rows` на `loops` **[офиц.]**. Расхождение на порядки (типично: `rows=1` у временной таблицы при факте в десятки тысяч) → Nested Loop вместо Hash Join.
13. **`<plansql/>` в `logcfg.xml` на продуктивном сервере использовать нельзя** — только на тестовом **[офиц., ИТС 6011]**. На продуктиве планы длинных запросов пишет `auto_explain` с обязательным порогом `auto_explain.log_min_duration` (в примере ИТС — `10s`).
14. **`auto_explain.log_analyze = on` замедляет все запросы**, а не только длинные (инструментируется каждый оператор) **[офиц.]**; смягчение — `auto_explain.log_timing = off` и `auto_explain.sample_rate`.
15. **`log_line_prefix` для pgBadger**: `'%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '` (так в ИТС 6006 и в старых README pgBadger; актуальный README: `'%t [%p]: user=%u,db=%d,app=%a,client=%h '`) **[офиц.]**. Обязательны метка времени (`%t`/`%m`/`%n`) и PID (`%p`/`%c`).
16. **pgBadger**: `sudo apt install pgbadger` (Ubuntu 24.04 — 12.4, 26.04 — 13.2; последний релиз 13.2 от 2025-12-29); `pgbadger -j 4 /var/log/postgresql/postgresql-18-main.log -o report.html`.
17. **Изменения представлений по версиям**, ломающие старые запросы: `pg_stat_checkpointer` появился в 17 (столбцы контрольных точек убраны из `pg_stat_bgwriter`, удалены `buffers_backend*`); `pg_stat_io` появился в 16; в 18 из `pg_stat_wal` удалены `wal_write`, `wal_sync`, `wal_write_time`, `wal_sync_time` (перенесены в `pg_stat_io`); в `pg_stat_statements` `blk_read_time` → `shared_blk_read_time` (17), `total_time` → `total_exec_time` (13); в 17 изменилось написание части имён событий ожидания (`AutoVacuumMain` → `AutovacuumMain`, `WALSync` → `WalSync`, `BufFileRead` → `BuffileRead`) **[офиц.]**.
18. **Быстрая оценка «виновата ли СУБД»** (ИТС 6011): сумма длительностей событий `DBPOSTGRS` к сумме `CALL` в ТЖ больше ~50 % → заниматься запросами.
19. **Интерактивные «top» для PostgreSQL**: `sudo apt install pg-activity` → `sudo -u postgres pg_activity -U postgres` (клавиши `1`/`2`/`3` — выполняющиеся / ожидающие / блокирующие запросы).
20. **Минимум алертов**: доступность (`pg_isready`), соединения > 80–90 % от `max_connections`, отставание/обрыв репликации и неактивные слоты, транзакции старше N минут и `idle in transaction`, свободное место (PGDATA, `pg_wal`, архив), возраст XID (`age(datfrozenxid)`), сбои и отставание архивации WAL (`pg_stat_archiver`), взаимоблокировки, давность последней резервной копии.

## 1. Подготовка: что включить заранее

Диагностика «задним числом» возможна только если сбор статистики и журналирование были включены до инцидента. Ниже — минимальный постоянный набор.

### 1.1. Отличия версий PostgreSQL, важные для мониторинга

| Возможность | С какой версии | Комментарий |
|---|---|---|
| `pg_stat_statements.total_exec_time` (вместо `total_time`), `track_planning` | 13 | старые скрипты с `total_time` не работают |
| `pg_stat_activity.query_id`, `compute_query_id` | 14 | единый идентификатор запроса в `pg_stat_activity`, `EXPLAIN VERBOSE`, журнале (`%Q`) |
| `pg_locks.waitstart` | 14 | момент начала ожидания блокировки |
| `pg_stat_wal`, `pg_stat_progress_copy`, `pg_stat_statements_info`, столбцы `session_time` / `active_time` / `sessions_*` в `pg_stat_database` | 14 | |
| `idle_session_timeout` | 14 | |
| Статистика в разделяемой памяти (нет процесса stats collector и параметра `stats_temp_directory`) | 15 | совет «вынести `pg_stat_tmp` в tmpfs» относится к сборщику статистики ≤ 14; в 15+ в `pg_stat_tmp` остаётся, в частности, файл текстов `pg_stat_statements` (`pgss_query_texts.stat`). Приложение K документации «PostgreSQL для 1С» 16 (K.3.12) этот совет повторяет — он унаследован от старых версий (сверено 19.10.2026 с замечаниями к выпуску 15 и исходным кодом `pg_stat_statements` REL_16) |
| `log_destination = jsonlog` | 15 | |
| `log_checkpoints = on` и `log_autovacuum_min_duration = 10min` по умолчанию | 15 | |
| `pg_stat_io`; `last_seq_scan` / `last_idx_scan`; `pg_buffercache_summary()`; `EXPLAIN (GENERIC_PLAN)` | 16 | |
| `pg_stat_checkpointer` (из `pg_stat_bgwriter` убраны столбцы контрольных точек и `buffers_backend`, `buffers_backend_fsync`) | 17 | |
| `pg_wait_events`; `transaction_timeout`; `EXPLAIN (MEMORY, SERIALIZE)`; в `pg_stat_statements` — `shared_blk_read_time` / `shared_blk_write_time` (переименованы), `local_blk_*_time`, `stats_since`, `minmax_stats_since`; в `pg_stat_progress_vacuum` — `indexes_total`, `indexes_processed`, `dead_tuple_bytes` | 17 | в `pg_stat_progress_vacuum` переименованы `max_dead_tuples` → `max_dead_tuple_bytes`, `num_dead_tuples` → `num_dead_item_ids`; имена событий ожидания (кроме классов `LWLock` и `Lock`) теперь строятся из внутренних имён, поэтому часть изменилась: `AutoVacuumMain` → `AutovacuumMain`, `WALSync` / `WALWrite` (класс `IO`) → `WalSync` / `WalWrite`, `BufFileRead` / `BufFileWrite` → `BuffileRead` / `BuffileWrite` (сверено 19.10.2026: замечания к выпуску 17, документация 16 и 18, `wait_event_names.txt` и `generate-wait_event_types.pl` ветки REL_17_STABLE) |
| `EXPLAIN ANALYZE` автоматически включает `BUFFERS`; дробные `rows`; строка `Index Searches`; пометка `Disabled: true` | 18 | |
| `pg_stat_io`: столбцы `read_bytes` / `write_bytes` / `extend_bytes`, строки для WAL (`object = 'wal'`); из `pg_stat_wal` удалены `wal_write`, `wal_sync`, `wal_write_time`, `wal_sync_time` | 18 | `track_wal_io_timing` теперь управляет временем в `pg_stat_io` |
| `pg_stat_get_backend_io(pid)`, `pg_stat_get_backend_wal(pid)`, `pg_stat_reset_backend_stats(pid)` | 18 | статистика ввода-вывода по отдельному бэкенду |
| `pg_stat_checkpointer.num_done`, `slru_written`; в `pg_stat_all_tables` — `total_vacuum_time`, `total_autovacuum_time`, `total_analyze_time`, `total_autoanalyze_time` | 18 | |
| `pg_stat_statements`: идентификатор запроса по имени таблицы (а не OID), свёртка списков констант `IN (…)`, параметризация `SET`, `parallel_workers_to_launch` / `parallel_workers_launched`, `wal_buffers_full` | 18 | важно для 1С, см. 4.6 |
| `log_connections` — список значений (`receipt`, `authentication`, `authorization`, `setup_durations`, `all`); `log_lock_failures`; `%L` в `log_line_prefix`; `track_cost_delay_timing` | 18 | старые `on`/`off` для `log_connections` по-прежнему принимаются |

Источник: документация PostgreSQL 18 и примечания к выпускам 17 и 18 **[офиц.]**.

### 1.2. Права: роль для мониторинга

Суперпользователь для мониторинга не нужен. Встроенная роль `pg_monitor` (включает `pg_read_all_settings`, `pg_read_all_stats`, `pg_stat_scan_tables`) даёт доступ к текстам чужих запросов в `pg_stat_activity` / `pg_stat_statements` и к служебным функциям **[офиц.]**.

```sql
CREATE ROLE monitor LOGIN PASSWORD 'ИзменитеМеня';
GRANT pg_monitor TO monitor;
-- отмена и завершение чужих сеансов без прав суперпользователя (сеансы суперпользователей не затрагивает):
GRANT pg_signal_backend TO monitor;
```

Без `pg_read_all_stats` в чужих строках `pg_stat_activity` вместо текста запроса видно `<insufficient privilege>`.

### 1.3. Параметры сбора статистики

| Параметр | По умолчанию | Рекомендация для сервера 1С | Применение |
|---|---|---|---|
| `track_activities` | `on` | `on` | перечитывание |
| `track_counts` | `on` | `on` (нужно автоочистке) | перечитывание |
| `track_activity_query_size` | `1024` (байт) | `32768`–`1048576`: тексты запросов 1С длинные; ИТС 6011 даёт `1048576` | **перезапуск** |
| `track_io_timing` | `off` | `on` после проверки `pg_test_timing` | перечитывание |
| `track_wal_io_timing` | `off` | `on` (14+; в 18 время пишется в `pg_stat_io`) | перечитывание |
| `track_functions` | `none` | `none` (1С не использует хранимые функции; для отчётов `pg_profile` можно `pl`) | перечитывание |
| `compute_query_id` | `auto` | `auto` (`pg_stat_statements` включает вычисление сам) | перечитывание |
| `stats_fetch_consistency` | `cache` | не менять | сеанс |

Проверка цены измерения времени (важно в виртуальной машине: медленный источник времени делает `track_io_timing` и `EXPLAIN ANALYZE` дорогими) **[офиц.]**:

```bash
/usr/lib/postgresql/18/bin/pg_test_timing            # Postgres Pro: /opt/pgpro/1c-17/bin/pg_test_timing
cat /sys/devices/system/clocksource/clocksource0/current_clocksource   # tsc, kvm-clock, hyperv_clocksource_tsc_page — быстрые; acpi_pm, hpet — медленные
```

Если в выводе `pg_test_timing` среднее «Per loop time including overhead» в пределах десятков наносекунд — включать можно без опасений **[практика]**.

### 1.4. Постоянный профиль настроек (пример)

В раскладке Debian/Ubuntu удобно положить отдельный файл в `conf.d` (каталог подключён пакетом `postgresql-common`); в Postgres Pro — править `postgresql.conf` в каталоге данных или использовать `ALTER SYSTEM`.

```ini
# /etc/postgresql/18/main/conf.d/90-monitoring.conf

# --- библиотеки (перезапуск). Допишите к уже имеющимся: online_analyze, plantuner, pg_wait_sampling ...
shared_preload_libraries = 'pg_stat_statements,auto_explain'

# --- статистика
track_activity_query_size = 32768        # перезапуск
track_io_timing = on
track_wal_io_timing = on

# --- pg_stat_statements
pg_stat_statements.max = 10000           # перезапуск
pg_stat_statements.track = top
pg_stat_statements.track_planning = off
pg_stat_statements.save = on

# --- журнал
lc_messages = 'C'                        # английские сообщения: нужны pgBadger и поиску по журналу
log_line_prefix = '%m [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_duration_statement = '5s'        # подберите под свою систему
log_lock_waits = on
deadlock_timeout = '1s'
log_temp_files = '100MB'
log_checkpoints = on
log_autovacuum_min_duration = '10s'
log_connections = off                    # 1С держит пул соединений; включать на время разбора
log_disconnections = off
log_parameter_max_length = 1024
log_error_verbosity = default

# --- auto_explain: планы длинных запросов без инструментирования остальных
auto_explain.log_min_duration = '30s'
auto_explain.log_analyze = off
auto_explain.log_format = text
```

```bash
sudo pg_ctlcluster 18 main restart          # или: sudo systemctl restart postgresql@18-main
sudo -u postgres psql -d erp -c 'CREATE EXTENSION IF NOT EXISTS pg_stat_statements;'
sudo -u postgres psql -c "SELECT name, setting, pending_restart FROM pg_settings WHERE name IN ('shared_preload_libraries','track_activity_query_size','pg_stat_statements.max','log_line_prefix');"
```

Что требует перезапуска, а что нет: `shared_preload_libraries`, `pg_stat_statements.max`, `track_activity_query_size`, `logging_collector` — только перезапуск; параметры `log_*`, `deadlock_timeout`, `track_io_timing`, `auto_explain.*`, `pg_stat_statements.track` — достаточно `SELECT pg_reload_conf();` **[офиц.]**.

## 2. pg_stat_activity: кто подключён и что делает

Одна строка на серверный процесс, включая служебные (`backend_type` ≠ `client backend`) **[офиц.]**.

### 2.1. Столбцы

| Столбец | Смысл | На что смотреть |
|---|---|---|
| `datid`, `datname` | база | у служебных процессов пусто |
| `pid` | PID серверного процесса (он же в `ps`, `top`, `pg_locks.pid`, `%p` журнала, `dbpid` ТЖ 1С) | ключ для всех связок |
| `leader_pid` | PID лидера параллельной группы | у 1С обычно пусто (параллелизм для 1С отключают) |
| `usesysid`, `usename` | роль | для 1С — роль из параметров информационной базы |
| `application_name` | имя приложения, заданное клиентом | `psql`, `pg_dump`, `pgbadger`…; у 1С — см. 2.5 |
| `client_addr`, `client_hostname`, `client_port` | адрес клиента; `NULL` — Unix-сокет или служебный процесс; порт `-1` — Unix-сокет | для 1С — адрес **сервера 1С** |
| `backend_start` | когда установлено соединение | долго живущие соединения — норма для пула 1С |
| `xact_start` | начало текущей транзакции; `NULL`, если транзакции нет | возраст транзакции = `now() - xact_start` |
| `query_start` | начало текущего запроса; если `state` ≠ `active` — начало **последнего** запроса | |
| `state_change` | когда последний раз менялся `state` | для `idle in transaction`: сколько сеанс «висит» = `now() - state_change` |
| `wait_event_type`, `wait_event` | чего ждёт процесс; оба `NULL` — не ждёт (работает на процессоре) | см. 2.3 |
| `state` | состояние | см. 2.2 |
| `backend_xid` | идентификатор транзакции верхнего уровня (появляется, когда транзакция что-то изменила) | совпадает с `pg_locks.transactionid` |
| `backend_xmin` | горизонт `xmin` бэкенда | самый старый `backend_xmin` не даёт VACUUM убирать мёртвые строки |
| `query_id` | идентификатор запроса (14+) | соединяется с `pg_stat_statements.queryid` |
| `query` | текст текущего или последнего запроса, обрезан до `track_activity_query_size` | |
| `backend_type` | `client backend`, `autovacuum worker`, `walsender`, `checkpointer`, `background writer`, `parallel worker`… | |

### 2.2. Значения state

| `state` | Что это | Комментарий для 1С |
|---|---|---|
| `active` | выполняет запрос | при непустом `wait_event` запрос выполняется, но сейчас чего-то ждёт |
| `idle` | ждёт команду клиента, транзакции нет | десятки и сотни таких соединений — нормальный пул 1С |
| `idle in transaction` | транзакция открыта, запрос не выполняется | сервер 1С «думает» между запросами транзакции (код на встроенном языке, внешний вызов, ожидание управляемой блокировки). Долгое пребывание — проблема: удерживаются блокировки строк и горизонт очистки |
| `idle in transaction (aborted)` | то же, но оператор в транзакции завершился ошибкой | |
| `fastpath function call` | выполняется fast-path-функция | |
| `disabled` | у бэкенда выключен `track_activities` | |
| `starting` | (18) соединение устанавливается, идёт аутентификация | |

`wait_event` и `state` независимы: `active` + `wait_event_type = 'Lock'` — запрос заблокирован; `idle` + `Client: ClientRead` — обычное ожидание команды клиента **[офиц.]**.

### 2.3. Типы ожиданий (wait_event_type)

| Тип | Смысл | Типичные `wait_event` и что они значат |
|---|---|---|
| `Lock` | ожидание «тяжёлой» блокировки | `transactionid` — ждёт завершения другой транзакции (конкуренция за строку); `tuple` — очередь за строкой; `relation` — блокировка таблицы (DDL, реструктуризация, `LOCK TABLE` автоматического режима, `VACUUM FULL`); `extend` — расширение файла таблицы; `virtualxid`; `advisory` |
| `LWLock` | лёгкая блокировка структур в разделяемой памяти | `WALWrite`, `WALInsert` — упор в запись WAL; `BufferMapping`, `BufferContent` — конкуренция за буферы; `LockManager` — слишком много блокировок/секций; `ProcArray`, `XidGen`, `SubtransSLRU`, `MultiXact*` |
| `IO` | ожидание ввода-вывода | `DataFileRead` — чтение данных (мало памяти под кеш / медленный диск); `DataFileWrite`, `DataFileExtend`; `WalSync`, `WalWrite` (до 16 включительно — `WALSync`, `WALWrite`); `BuffileRead` / `BuffileWrite` (до 16 — `BufFileRead` / `BufFileWrite`) — временные файлы (мало `work_mem`) |
| `IPC` | ожидание другого процесса | `SyncRep` — синхронная репликация; `ParallelFinish`, `MessageQueue*` — параллельные запросы; `CheckpointDone` |
| `Client` | ожидание клиента | `ClientRead` — сервер ждёт команду от клиента (у `idle in transaction` — «мяч на стороне 1С»); `ClientWrite` — клиент медленно забирает результат |
| `Activity` | простой служебного процесса в основном цикле | `AutovacuumMain` (до 16 — `AutoVacuumMain`), `CheckpointerMain`, `WalWriterMain` — норма |
| `BufferPin` | ожидание закрепления буфера | редкость |
| `Timeout` | ожидание истечения времени | `VacuumDelay` — пауза автоочистки (ограничение стоимости), `PgSleep` |
| `Extension` | ожидание, заданное расширением | |

Полный справочник с описаниями (17+): `SELECT * FROM pg_wait_events ORDER BY type, name;` **[офиц.]**. Имена в таблице даны по документации 18; с 17 часть имён классов `Activity`, `IO` и др. изменила написание (см. таблицу в 1.1) — в условиях `WHERE wait_event = '…'` для сервера 16 используйте старые имена (сверено 19.10.2026).

Разовый снимок активности показывает случайный момент. Профиль ожиданий получают многократным опросом (скрипт из ИТС 6011 — раз в 3 секунды, см. Q-06) или расширением `pg_wait_sampling` (раздел 10.4).

### 2.4. Время: xact_start, query_start, state_change, backend_xmin

- Длинная транзакция опасна не только блокировками: пока жив её снимок (`backend_xmin`), автоочистка не может удалить версии строк, ставшие мёртвыми позже. Симптом: в журнале автоочистки растёт «dead tuples … are dead but not yet removable», таблицы и индексы пухнут.
- Горизонт удерживают также: слоты репликации (`pg_replication_slots.xmin`, `catalog_xmin`), подготовленные транзакции (`pg_prepared_xacts`), реплика с `hot_standby_feedback = on` (`pg_stat_replication.backend_xmin`). Запрос Q-05 показывает всех «держателей».
- Для `idle in transaction` информативен `now() - state_change` (сколько простаивает), для `active` — `now() - query_start`.
- Таймауты-предохранители **[офиц.]**: `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`, `idle_session_timeout` (14+), `transaction_timeout` (17+). Для роли 1С задавать их глобально опасно: длинные регламентные операции (закрытие месяца, реструктуризация, обмены) будут прерваны. `lock_timeout` платформа выставляет сама (см. 3.6). `idle_session_timeout` для роли 1С не задавать: он рвёт простаивающие соединения пула **[практика]**.

### 2.5. Как выглядит 1С в pg_stat_activity и как найти сеанс 1С

Особенности подключения сервера 1С к PostgreSQL:

- К СУБД подключаются рабочие процессы `rphost` (и `rmngr` для служебных задач), а не клиентские приложения. Поэтому `client_addr` — адрес сервера 1С; если сервер 1С и PostgreSQL на одной машине — `127.0.0.1` / `::1` или `NULL` (Unix-сокет).
- Соединения живут в пуле рабочего процесса. Сеанс 1С получает соединение на время вызова СУБД, транзакции или пока удерживает `МенеджерВременныхТаблиц` хотя бы с одной временной таблицей; потом соединение возвращается в пул **[офиц., документация консоли кластера]**. Один и тот же `pid` в разные моменты обслуживает разных пользователей.
- `usename` у всех одинаковый — роль, указанная при создании информационной базы.
- `application_name`: по наблюдениям сообщества сервер 1С передаёт значение `1CV8` для всех соединений; идентификатора сеанса или имени пользователя 1С в нём нет (**⚠ не подтверждено** официальной документацией — проверьте запросом Q-02). В примере события `DBPOSTGRS` из ИТС 6011 свойства ТЖ `t:applicationName` и `AppID` равны `1CV8C` (тонкий клиент) — это свойства ТЖ 1С, а не `application_name` PostgreSQL.

Три способа связать бэкенд с сеансом 1С:

**1. Технологический журнал → PostgreSQL.** У событий `DBPOSTGRS` есть свойство `Dbpid` — «идентификатор соединения сервера 1С с сервером баз данных в терминах сервера баз данных», то есть PID бэкенда **[офиц., документация платформы]**. В той же строке — `SessionID` (номер сеанса 1С), `Usr` (пользователь 1С), `t:connectID`, `Context` (строка кода). Пример события из ИТС 6011 (сокращено):

```text
38:31.223006-1,DBPOSTGRS,5,process=rphost,p:processName=DATABASE,...,SessionID=2,...,dbpid=11988,Sql="SELECT
T1._IDRRef, ... FROM _Document1337 T1 WHERE ...",RowsAffected=1,Result=PGRES_TUPLES_OK,Context='Форма.Вызов : ...
```

```bash
# все события ТЖ по конкретному бэкенду PostgreSQL (каталог ТЖ — ваш)
grep -rh --include='*.log' -E ',DBPOSTGRS,.*dbpid=11988,' /var/log/1c/tj/ | cut -c1-300
# тот же PID в журнале PostgreSQL (PID в квадратных скобках — из log_line_prefix)
grep -F '[11988]' /var/log/postgresql/postgresql-18-main.log | tail -50
```

```sql
SELECT pid, state, wait_event_type, wait_event, now() - query_start AS dur, query
FROM pg_stat_activity WHERE pid = 11988;
```

**2. PostgreSQL → кластер 1С (`rac`).** В списке сеансов поле `db-proc-info` («Соединение с СУБД») — идентификатор процесса сервера баз данных; показывается только пока соединение захвачено сеансом **[офиц., ИТС: «Клиент-серверный вариант», гл. 5]**. Сопутствующие поля: `db-proc-took` («Захвачено СУБД» — сколько сеанс удерживает соединение), `db-proc-took-at` (момент захвата), `blocked-by-dbms` («Заблокировано СУБД» — номер сеанса, чья транзакция держит блокировку СУБД), `blocked-by-ls` («Заблокировано упр.» — номер сеанса, держащего управляемую блокировку), `duration-current-dbms` (время вызовов СУБД в текущем вызове).

```bash
V=8.3.27.2074                                    # ваша сборка: ls /opt/1cv8/x86_64/
RAC=/opt/1cv8/x86_64/$V/rac                      # требуется запущенный ras (порт 1545)
CL=$($RAC cluster list | awk '/^cluster/{print $3}')

# сеансы, у которых сейчас захвачено соединение с СУБД: номер сеанса, пользователь, приложение, PID бэкенда
$RAC session list --cluster=$CL | awk -v RS= -F'\n' '{
  delete f
  for (i = 1; i <= NF; i++) { split($i, kv, / *: */); val = $i; sub(/^[^:]*: */, "", val); f[kv[1]] = val }
  if (f["db-proc-info"] != "")
    printf "sess=%-5s user=%-22s app=%-12s host=%-15s pg_pid=%-7s took=%-8s blocked_dbms=%s blocked_ls=%s\n",
           f["session-id"], f["user-name"], f["app-id"], f["host"], f["db-proc-info"], f["db-proc-took"],
           f["blocked-by-dbms"], f["blocked-by-ls"]
}'
```

(⚠ не подтверждено: точный формат вывода `rac` — «ключ : значение», записи разделены пустой строкой — сверьте на своей версии; единица измерения `db-proc-took`.) Подробности по `rac` — в `kb/1c/03-administrirovanie-klastera-ras-rac.md`.

**3. По тексту запроса и времени.** Если `Dbpid` недоступен (ТЖ не был включён), остаётся сопоставление по времени и фрагменту текста запроса из `pg_stat_activity.query` / журнала PostgreSQL с событиями ТЖ и журналом регистрации 1С.

### 2.6. Отмена запроса и завершение соединения

```sql
SELECT pg_cancel_backend(12345);      -- отменить текущий запрос (SIGINT); транзакция получит ошибку
SELECT pg_terminate_backend(12345);   -- завершить соединение (SIGTERM); транзакция откатится
-- завершить всё, что простаивает в транзакции дольше часа, в базе erp:
SELECT pid, pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'erp' AND state LIKE 'idle in transaction%' AND now() - state_change > interval '1 hour';
```

- Команда `rac connection disconnect`, если соединение занято запросом к PostgreSQL, ничего не делает — разрыв длительного запроса из кластера 1С поддержан только для MS SQL Server, IBM Db2 и Oracle Database **[офиц., ИТС]**. Зависший запрос PostgreSQL снимают функциями выше; со стороны 1С есть `rac session interrupt-current-server-call` и `rac session terminate`.
- После `pg_terminate_backend` пользователь 1С получит ошибку СУБД, сеанс 1С обычно остаётся жив и возьмёт новое соединение. Никогда не применяйте `kill -9` к процессам `postgres`: это приводит к аварийному перезапуску всего сервера с восстановлением по WAL **[офиц.]**.

## 3. Блокировки

### 3.1. Два уровня: управляемые блокировки 1С и блокировки СУБД

| | Управляемые блокировки 1С | Блокировки PostgreSQL |
|---|---|---|
| Кто ставит | прикладной код (`БлокировкаДанных`) и платформа при записи объектов в управляемом режиме | сам PostgreSQL при выполнении SQL |
| Где хранятся | менеджер блокировок кластера 1С (`rmngr`) | разделяемая память PostgreSQL; блокировки строк — в самих строках на диске |
| Где видны | ТЖ: `TLOCK`, `TTIMEOUT`, `TDEADLOCK`; `rac`: `blocked-by-ls`; консоль кластера: «Заблокировано упр.» | `pg_locks`, `pg_blocking_pids()`, журнал PostgreSQL (`log_lock_waits`); `rac`: `blocked-by-dbms`; ТЖ: длинные `DBPOSTGRS`, свойства `lka` / `lkp` при `<dbmslocks/>` |
| Как выглядит ожидание в PostgreSQL | бэкенд ожидающего сеанса `idle in transaction` (или `idle`), `wait_event = ClientRead`: PostgreSQL ничего не ждёт | бэкенд `active`, `wait_event_type = 'Lock'` |
| Таймаут | «Время ожидания блокировки данных» информационной базы (20 с по умолчанию) → `TTIMEOUT` | `lock_timeout` сеанса (платформа ставит то же значение, 20000 мс) → `55P03` |
| Взаимоблокировка | `TDEADLOCK` | `ERROR: deadlock detected` (`40P01`), счётчик `pg_stat_database.deadlocks` |

Режимы работы платформы с PostgreSQL (по документации платформы, раздел о блокировках данных; Подтверждено 19.10.2026 (конспект «Руководства разработчика» 8.3.27, гл. 9, п. 9.2.3.2 — `../its-docs/dev-gl09-rabota-s-dannymi.md`: для PostgreSQL автоматический режим — блокировки таблиц, Serializable; управляемый — блокировки записей, Read Committed)):

| Режим блокировок конфигурации | Уровень изоляции | Гранулярность блокировок СУБД |
|---|---|---|
| Автоматический | Serializable | таблицы |
| Управляемый | Read Committed | строки |

Позиция разработчиков платформы (ИТС 6006) **[офиц.]**: при управляемом режиме ожиданий на блокировках в PostgreSQL возникать не должно — только на управляемых блокировках. Каждый сценарий, где ожидание возникло именно на уровне PostgreSQL, предлагается документировать и отправлять в поддержку (v8@1c.ru; корпоративным клиентам — CorpTechSupport@1c.ru), не дожидаясь ответа с устранением причины.

Следствия:

- В автоматическом режиме на PostgreSQL параллельная запись в одну таблицу невозможна — пользователи ждут друг друга на блокировках таблиц (`wait_event = relation`). Все современные типовые конфигурации работают в управляемом режиме.
- В управляемом режиме основная масса ожиданий — управляемые блокировки 1С. Если пользователи «ждут», а в `pg_stat_activity` нет ни одного `wait_event_type = 'Lock'` — смотрите ТЖ (`TLOCK` с `WaitConnections`), а не PostgreSQL.
- Блокировки СУБД в управляемом режиме всё равно возникают: конкуренция за строки таблиц итогов регистров (в том числе при выключенном разделении итогов), служебные таблицы, а также блокировки таблиц при реструктуризации, `VACUUM FULL`, `REINDEX` без `CONCURRENTLY`, `TRUNCATE`.

Поиск виновника управляемой блокировки по ТЖ (ИТС 6006) **[офиц.]**:

```bash
# ожидания на управляемых блокировках (у события есть WaitConnections)
grep -rP 'TLOCK.*WaitConnections=\d+' /var/log/1c/tj/
# только долгие (длительность из 6 и более цифр)
grep -rP '\d{6,},TLOCK.*WaitConnections=\d+' /var/log/1c/tj/
# далее: взять номер из WaitConnections (например 16) и найти TLOCK соединения-виновника
# на то же пространство блокировок (Regions) и те же поля (Locks): t:connectID=16
grep -rP 'TLOCK.*t:connectID=16,.*Regions=InfoRg404' /var/log/1c/tj/
```

По свойству `Context` найденного события определяется код, установивший блокировку. Подробнее — `kb/1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.

### 3.2. Представление pg_locks

Одна строка на пару «объект блокировки — режим — процесс»; охватывает весь кластер баз **[офиц.]**.

| Столбец | Смысл |
|---|---|
| `locktype` | тип объекта: `relation`, `extend`, `frozenid`, `page`, `tuple`, `transactionid`, `virtualxid`, `spectoken`, `object`, `userlock`, `advisory`, `applytransaction` |
| `database` | OID базы (0 — общий объект, `NULL` — идентификатор транзакции) |
| `relation` | OID таблицы или индекса (`relation::regclass` работает только для текущей базы) |
| `page`, `tuple` | страница и строка (для `page` / `tuple`) |
| `virtualxid`, `transactionid` | виртуальный / постоянный идентификатор транзакции, на которую направлена блокировка |
| `classid`, `objid`, `objsubid` | объект каталога; у `advisory` — ключ блокировки |
| `virtualtransaction` | виртуальная транзакция владельца или ожидающего |
| `pid` | процесс (`NULL` — подготовленная транзакция) |
| `mode` | режим: `AccessShareLock`, `RowShareLock`, `RowExclusiveLock`, `ShareUpdateExclusiveLock`, `ShareLock`, `ShareRowExclusiveLock`, `ExclusiveLock`, `AccessExclusiveLock` |
| `granted` | `true` — блокировка получена, `false` — процесс ждёт |
| `fastpath` | получена по быстрому пути (без общей таблицы блокировок) |
| `waitstart` | когда началось ожидание (14+) |

Что нужно знать, чтобы читать `pg_locks`:

- **Блокировки строк в `pg_locks` не видны** — они хранятся в самих строках. Сеанс, ждущий строку, выглядит как ожидающий `ShareLock` на `transactionid` транзакции-владельца (и кратко — `tuple`). Поэтому «какую строку ждём» из `pg_locks` не узнать; таблицу и строку подскажет строка `CONTEXT: while updating tuple (стр,поз) in relation "…"` в журнале при `log_lock_waits = on`.
- Каждая транзакция держит `ExclusiveLock` на свой `virtualxid`, а пишущая — ещё и на свой `transactionid`; это норма, а не «подозрительные эксклюзивные блокировки».
- Любой `SELECT` берёт `AccessShareLock` на таблицу, `INSERT`/`UPDATE`/`DELETE` — `RowExclusiveLock`. Чтение конфликтует только с `AccessExclusiveLock` (`ALTER TABLE`, `DROP`, `TRUNCATE`, `VACUUM FULL`, `CLUSTER`); запись — ещё и с `ShareLock` (`CREATE INDEX` и `REINDEX` без `CONCURRENTLY`; `REINDEX` вдобавок берёт `AccessExclusiveLock` на сам индекс, блокируя запросы, которые хотят им воспользоваться). Реструктуризация 1С и ручное обслуживание под нагрузкой блокируют именно так.
- Очередь: запрос `AccessExclusiveLock`, который сам ждёт длинную транзакцию, блокирует **все последующие** обращения к таблице, включая чтение. Перед DDL ставьте `SET lock_timeout = '5s'`.
- Размер таблицы блокировок — `max_locks_per_transaction` объектов на **каждый серверный процесс** и каждую подготовленную транзакцию, то есть `max_locks_per_transaction × (MaxBackends + max_prepared_transactions)`, где `MaxBackends` = `max_connections` + `autovacuum_max_workers` + 1 (в 18 — `autovacuum_worker_slots` + 2) + `max_worker_processes` + `max_wal_senders` (Уточнено 19.10.2026 по документации PostgreSQL 16 и 18, разд. «Lock Management», и исходному коду `InitializeMaxBackends()` / `NLOCKENTS()` веток REL_16 и REL_18: прежняя формула `× (max_connections + max_prepared_transactions)` занижала ёмкость). 1С создаёт много временных таблиц, отсюда рекомендация 256 (Postgres Pro) или 512–2000 (ИТС 5866) вместо 64 по умолчанию; при нехватке — `ERROR: out of shared memory` с подсказкой увеличить `max_locks_per_transaction`.
- Частый опрос `pg_locks` сам создаёт нагрузку на менеджер блокировок **[офиц.]** — не опрашивайте чаще раза в несколько секунд.

Таблица совместимости режимов (✗ — конфликт) **[офиц., глава 13.3]**:

| Запрошен \ Удерживается | AccessShare | RowShare | RowExcl | ShareUpdExcl | Share | ShareRowExcl | Excl | AccessExcl |
|---|---|---|---|---|---|---|---|---|
| AccessShare (`SELECT`) | | | | | | | | ✗ |
| RowShare (`SELECT … FOR UPDATE/SHARE`) | | | | | | | ✗ | ✗ |
| RowExclusive (`INSERT/UPDATE/DELETE`) | | | | | ✗ | ✗ | ✗ | ✗ |
| ShareUpdateExclusive (`VACUUM`, `ANALYZE`, `CREATE INDEX CONCURRENTLY`, `REINDEX CONCURRENTLY`) | | | | ✗ | ✗ | ✗ | ✗ | ✗ |
| Share (`CREATE INDEX`, `REINDEX` — на таблицу) | | | ✗ | ✗ | | ✗ | ✗ | ✗ |
| ShareRowExclusive (`CREATE TRIGGER`, часть `ALTER TABLE`) | | | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Exclusive (`REFRESH MATERIALIZED VIEW CONCURRENTLY`) | | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| AccessExclusive (`ALTER TABLE`, `DROP`, `TRUNCATE`, `VACUUM FULL`, `CLUSTER`, `LOCK TABLE` по умолчанию; `REINDEX` — на индекс) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

### 3.3. pg_blocking_pids() и дерево блокировок

`pg_blocking_pids(pid)` возвращает массив PID процессов, блокирующих указанный процесс (пустой массив, если он не заблокирован); учитывает очередь ожидания и параллельные процессы **[офиц.]**. Вызов кратко блокирует менеджер блокировок — не вызывайте в плотном цикле.

Пары «ждёт → держит»:

```sql
SELECT w.pid                        AS blocked_pid,
       now() - w.query_start        AS waiting,
       w.wait_event_type || ':' || w.wait_event AS wait,
       left(w.query, 100)           AS blocked_query,
       b.pid                        AS blocking_pid,
       b.state                      AS blocking_state,
       now() - b.xact_start         AS blocking_xact_age,
       now() - b.state_change       AS blocking_state_age,
       left(b.query, 100)           AS blocking_last_query
FROM pg_stat_activity w
JOIN LATERAL unnest(pg_blocking_pids(w.pid)) AS x(pid) ON true
JOIN pg_stat_activity b ON b.pid = x.pid
ORDER BY waiting DESC;
```

Дерево блокировок (корень — сеанс, который держит других и сам никого не ждёт):

```sql
WITH RECURSIVE a AS (
    SELECT pid, pg_blocking_pids(pid) AS blocked_by,
           usename, application_name, client_addr, state,
           wait_event_type, wait_event, xact_start, state_change,
           left(regexp_replace(query, '\s+', ' ', 'g'), 150) AS query
    FROM pg_stat_activity
    WHERE pid <> pg_backend_pid()
),
tree AS (
    SELECT a.pid, 0 AS lvl, ARRAY[a.pid] AS path
    FROM a
    WHERE cardinality(a.blocked_by) = 0
      AND EXISTS (SELECT 1 FROM a w WHERE a.pid = ANY (w.blocked_by))
    UNION ALL
    SELECT w.pid, t.lvl + 1, t.path || w.pid
    FROM a w
    JOIN tree t ON t.pid = ANY (w.blocked_by)
    WHERE w.pid <> ALL (t.path)               -- защита от зацикливания
)
SELECT repeat('    ', t.lvl) || t.pid         AS pid_tree,
       a.state,
       a.wait_event_type || ':' || a.wait_event AS wait,
       now() - a.xact_start                   AS xact_age,
       now() - a.state_change                 AS state_age,
       a.usename, a.application_name, a.client_addr,
       a.query
FROM tree t
JOIN a USING (pid)
ORDER BY t.path;
```

Как читать результат:

- Корень дерева в состоянии `idle in transaction` — классика для 1С: транзакция открыта, сервер 1С занят чем-то своим (код, внешний сервис, ожидание управляемой блокировки, интерактивный диалог в транзакции). PID корня → `rac session list` (`db-proc-info`) → пользователь и действие.
- Корень `active` с длинным запросом — оптимизировать запрос (раздел 7).
- Корень — `autovacuum worker`: обычная автоочистка уступает дорогу сама; не уступает только очистка «to prevent wraparound».
- Сеанс, ждущий нескольких, появится в нескольких ветках.

Что именно удерживает блокирующий процесс:

```sql
SELECT l.locktype, l.mode, l.granted, l.fastpath,
       CASE WHEN l.locktype = 'relation' THEN l.relation::regclass::text END AS relation,
       l.transactionid, l.virtualxid, l.waitstart
FROM pg_locks l
WHERE l.pid = 12345
  AND (l.database IS NULL OR l.database IN (0, (SELECT oid FROM pg_database WHERE datname = current_database())))
ORDER BY l.granted, l.locktype, relation;
```

### 3.4. Журнал ожиданий: log_lock_waits и deadlock_timeout

- `deadlock_timeout` (по умолчанию `1s`) — сколько сеанс ждёт блокировку, прежде чем запускается проверка на взаимоблокировку. Проверка дорогая, поэтому значение не стоит делать слишком малым **[офиц.]**.
- `log_lock_waits = on` — когда ожидание превысило `deadlock_timeout`, в журнал пишется сообщение; ещё одно — когда блокировка наконец получена. Документация: для расследования задержек на блокировках можно временно уменьшить `deadlock_timeout` **[офиц.]**.
- `log_lock_failures = on` (18) — журналирует отказ в блокировке (сейчас только `SELECT … NOWAIT`).

Вид сообщений в журнале (при `lc_messages = 'C'`):

```text
LOG:  process 21456 still waiting for ShareLock on transaction 9876543 after 1000.214 ms
DETAIL:  Process holding the lock: 21011. Wait queue: 21456, 21502.
CONTEXT:  while updating tuple (1042,17) in relation "_accumrgt17539"
STATEMENT:  UPDATE _AccumRgT17539 SET ...
LOG:  process 21456 acquired ShareLock on transaction 9876543 after 5321.870 ms
```

Из этих строк видно: кто ждал (`21456`), кого (`21011`), сколько, на какой таблице и строке, каким оператором. Блокирующий оператор ищется в журнале по PID `21011` (если он попал под `log_min_duration_statement`) либо в ТЖ по `dbpid=21011`. pgBadger строит по этим сообщениям раздел «Locks».

```bash
# сколько ожиданий блокировок и на каких таблицах за сегодня
grep -c 'still waiting for' /var/log/postgresql/postgresql-18-main.log
grep -A2 'still waiting for' /var/log/postgresql/postgresql-18-main.log | grep -o 'in relation "[^"]*"' | sort | uniq -c | sort -rn | head
```

### 3.5. Взаимоблокировки

**В СУБД.** PostgreSQL сам находит цикл ожиданий и прерывает одну из транзакций:

```text
ERROR:  deadlock detected
DETAIL:  Process 21456 waits for ShareLock on transaction 9876543; blocked by process 21011.
        Process 21011 waits for ShareLock on transaction 9876544; blocked by process 21456.
        Process 21456: UPDATE _AccumRgT17539 SET ...
        Process 21011: UPDATE _AccumRgT17539 SET ...
HINT:  See server log for query details.
CONTEXT:  while updating tuple (1042,17) in relation "_accumrgt17539"
```

- SQLSTATE `40P01`; счётчик — `pg_stat_database.deadlocks`; в 1С — ошибка СУБД «Конфликт блокировок при выполнении транзакции:» с текстом PostgreSQL (`ERROR: deadlock detected`) в продолжении (событие `EXCP`, `Exception=DataBaseException`). Уточнено 19.10.2026 по конспектам ИТС 5809 и 6006 (`../its-metod/monitoring-i-audit.md`, `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`, `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`): ошибки блокировок уровня СУБД начинаются с этих слов, а «Неустранимый конфликт блокировок» — текст взаимоблокировки **управляемых** блокировок 1С (`TDEADLOCK`), прежняя формулировка «Неразрешимый конфликт…» была неверна.
- В журнале есть оба оператора и обе стороны, но только последние операторы транзакций — блокировки могли быть взяты раньше. Полную картину даёт ТЖ: события `DBPOSTGRS` и `SDBL` обоих `dbpid` за время жизни транзакций плюс `EXCP`.
- Типовые причины в 1С: разный порядок записи одних и тех же строк в параллельных транзакциях (движения регистров без единого порядка, итоги без разделения), повышение уровня блокировки «прочитал → изменил» без предварительной управляемой блокировки.

**В менеджере блокировок 1С.** Событие ТЖ `TDEADLOCK` (свойство `DeadlockConnectionIntersections` — пары соединений, образующих цикл) и `TTIMEOUT`; PostgreSQL о них ничего не знает. Разбор — в `kb/1c/07-…`.

**Сбор сведений о блокировках СУБД средствами платформы.** Элемент `<dbmslocks/>` в `logcfg.xml` включает периодический (не чаще раза в 2 секунды) запрос платформы к СУБД «кто кого блокирует»; к событиям потоков-участников добавляются свойства `lka` (источник), `lkp` (жертва), `lksrc`, `lkpid`, `lkaid`, `lkpto`, `lkato` **[офиц., документация платформы]** (механизм, периодичность и состав свойств сверены 19.10.2026 с конспектом «Руководства администратора» 8.3.27, п. 3.24.2.13 и 3.24.5 — `../its-docs/adm-pr03-sluzhebnye-fajly-p5.md`; ограничений по СУБД документация не называет). (⚠ не подтверждено: с каких версий платформы это работает именно для PostgreSQL — проверьте по своему ТЖ.)

### 3.6. Что делает платформа: lock_timeout и сообщения об ошибках

- Параметры сеанса, которые платформа ставит при соединении с PostgreSQL (ИТС 6011) **[офиц.]**: `SET client_min_messages = error; SET lc_messages TO 'en_US.UTF-8'; SET enable_mergejoin = off; SET escape_string_warning = off; SET cpu_operator_cost = 0.001; SET client_encoding = 'utf8'; SET lock_timeout = 20000;`.
- `lock_timeout = 20000` соответствует параметру информационной базы «Время ожидания блокировки данных» (20 секунд по умолчанию; меняется в конфигураторе: Администрирование → Параметры информационной базы).
- Сообщения PostgreSQL и их смысл:

| Сообщение в журнале PostgreSQL | SQLSTATE | Причина |
|---|---|---|
| `canceling statement due to lock timeout` | `55P03` | блокировку ждали дольше `lock_timeout` |
| `deadlock detected` | `40P01` | взаимоблокировка, транзакция-жертва отменена |
| `canceling statement due to statement timeout` | `57014` | сработал `statement_timeout` |
| `canceling statement due to user request` | `57014` | `pg_cancel_backend()` или отмена со стороны клиента |
| `terminating connection due to administrator command` | `57P01` | `pg_terminate_backend()` или остановка сервера |
| `terminating connection due to idle-in-transaction timeout` | `25P03` | сработал `idle_in_transaction_session_timeout` |
| `could not serialize access due to concurrent update` | `40001` | конфликт сериализации (автоматический режим блокировок 1С, уровень Serializable) |
| `out of shared memory` + HINT про `max_locks_per_transaction` | `53200` | переполнена таблица блокировок |

## 4. pg_stat_statements: какие запросы съедают сервер

Модуль накапливает статистику планирования и выполнения по каждому нормализованному оператору: одна строка на сочетание (пользователь, база, `queryid`, `toplevel`) **[офиц.]**.

### 4.1. Установка

1. Файлы модуля. Раскладка Debian/Ubuntu (PGDG, пакеты Ubuntu, сборка 1С): модули contrib входят в пакет `postgresql-NN`. Postgres Pro 1С: отдельный пакет `postgrespro-1c-17-contrib` (см. `kb/postgresql/01-…`). Проверка: `SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name = 'pg_stat_statements';`
2. Подключить библиотеку (нужен перезапуск). Сначала посмотреть, что уже подключено, и **дописать**, а не заменить:

```sql
SHOW shared_preload_libraries;                 -- например: online_analyze, plantuner
ALTER SYSTEM SET shared_preload_libraries = 'online_analyze', 'plantuner', 'pg_stat_statements', 'auto_explain';
```

```bash
sudo pg_ctlcluster 18 main restart             # Postgres Pro: sudo systemctl restart postgrespro-1c-17
```

3. Создать расширение. Данные модуля общие на весь кластер, а представление создаётся в конкретной базе — достаточно служебной базы `postgres`; ИТС 6011 создаёт его и в базе 1С:

```sql
\c postgres
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT count(*) FROM pg_stat_statements;       -- проверка, что модуль загружен
```

Если после правки сервер не стартует («could not access file "…": No such file or directory») — опечатка в имени библиотеки или не установлен пакет. Исправление: убрать строку из `postgresql.auto.conf` в каталоге данных (`/var/lib/postgresql/18/main/postgresql.auto.conf`) или из файла в `conf.d` и запустить снова.

### 4.2. Параметры

| Параметр | По умолчанию | Смысл | Применение |
|---|---|---|---|
| `pg_stat_statements.max` | `5000` | максимум отслеживаемых операторов; при переполнении вытесняются реже всего выполнявшиеся (счётчик `dealloc`). Для 1С — `10000` (ИТС 6011) и больше | перезапуск |
| `pg_stat_statements.track` | `top` | `top` — операторы верхнего уровня; `all` — ещё и вложенные (внутри функций); `none` — сбор выключен | суперпользователь, перечитывание |
| `pg_stat_statements.track_utility` | `on` | учитывать служебные команды (всё, кроме `SELECT`/`INSERT`/`UPDATE`/`DELETE`/`MERGE`) | суперпользователь |
| `pg_stat_statements.track_planning` | `off` | учитывать планирование (`plans`, `*_plan_time`); при высокой конкуренции даёт заметные накладные расходы | суперпользователь |
| `pg_stat_statements.save` | `on` | сохранять статистику при остановке сервера | файл конфигурации |

- `track`: ИТС 6011 ставит `all`; документация `pg_profile` рекомендует `top`. Для 1С разница невелика (хранимых функций с вложенным SQL практически нет), `top` экономит записи **[практика]**.
- Разделяемая память расходуется пропорционально `max` всегда, пока модуль загружен, даже при `track = none` **[офиц.]**.
- Тексты запросов хранятся не в памяти, а во внешнем файле (`pg_stat_tmp/pgss_query_texts.stat` в каталоге данных). Запросы 1С длинные (десятки килобайт), файл легко вырастает до сотен мегабайт. Если он становится слишком большим, модуль может отбросить тексты — тогда `query` = `NULL` при сохранённых счётчиках; лечится уменьшением `max` или сбросом **[офиц.]**.

### 4.3. Столбцы (PostgreSQL 18; время — в миллисекундах)

| Группа | Столбцы |
|---|---|
| Идентификация | `userid`, `dbid`, `toplevel` (14+), `queryid`, `query` |
| Планирование (при `track_planning`) | `plans`, `total_plan_time`, `min_plan_time`, `max_plan_time`, `mean_plan_time`, `stddev_plan_time` |
| Выполнение | `calls`, `total_exec_time`, `min_exec_time`, `max_exec_time`, `mean_exec_time`, `stddev_exec_time`, `rows` |
| Буферы | `shared_blks_hit`, `shared_blks_read`, `shared_blks_dirtied`, `shared_blks_written`; `local_blks_*` (временные таблицы); `temp_blks_read`, `temp_blks_written` (временные файлы сортировок и хешей) |
| Время ввода-вывода (при `track_io_timing`) | `shared_blk_read_time`, `shared_blk_write_time` (до 17 — `blk_read_time`, `blk_write_time`), `local_blk_read_time`, `local_blk_write_time` (17+), `temp_blk_read_time`, `temp_blk_write_time` (15+) |
| WAL | `wal_records`, `wal_fpi`, `wal_bytes`, `wal_buffers_full` (18) |
| JIT (15+) | `jit_functions`, `jit_generation_time`, `jit_inlining_*`, `jit_optimization_*`, `jit_emission_*`, `jit_deform_*` (17+) |
| Параллелизм (18) | `parallel_workers_to_launch`, `parallel_workers_launched` |
| Время сбора (17+) | `stats_since`, `minmax_stats_since` |

Вспомогательное представление `pg_stat_statements_info` (14+): `dealloc` — сколько раз вытеснялись записи; `stats_reset` — время последнего полного сброса.

Что означают блоки применительно к 1С: `shared_*` — постоянные таблицы и индексы; `local_*` — **временные таблицы** 1С (`tt<N>`), их буферы у каждого бэкенда свои (`temp_buffers`); `temp_*` — временные **файлы** на диске (сортировки, хеш-соединения, материализация, не поместившиеся в `work_mem`).

### 4.4. Топ запросов

Общий шаблон (сортировку меняйте): по суммарному времени — «что грузит сервер», по среднему — «что медленное», по вызовам — «что вызывается слишком часто».

```sql
-- по суммарному времени выполнения
SELECT round(total_exec_time::numeric / 1000, 1)                                       AS total_s,
       round(100 * total_exec_time::numeric / nullif(sum(total_exec_time::numeric) OVER (), 0), 1) AS pct,
       calls,
       round(mean_exec_time::numeric, 1)                                               AS mean_ms,
       round(max_exec_time::numeric, 1)                                                AS max_ms,
       rows,
       round(100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0), 1) AS hit_pct,
       queryid,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200)                               AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

| Что ищем | `ORDER BY` | Дополнительное условие |
|---|---|---|
| самые тяжёлые в сумме | `total_exec_time DESC` | |
| самые медленные в среднем | `mean_exec_time DESC` | `WHERE calls > 5` |
| самые частые | `calls DESC` | |
| возвращают/меняют больше всего строк | `rows DESC` | |
| больше всего читают с диска | `shared_blks_read DESC` или `shared_blk_read_time DESC` | |
| пишут временные файлы | `temp_blks_written DESC` | `WHERE temp_blks_written > 0` |
| генерируют больше всего WAL | `wal_bytes DESC` | |
| нестабильное время | `stddev_exec_time DESC` | |
| дольше всего планируются | `total_plan_time DESC` | нужен `track_planning = on` |

Полный текст одного запроса и его текущие исполнители:

```sql
SELECT query FROM pg_stat_statements WHERE queryid = -1234567890123456789;      -- \x on для удобства
SELECT pid, state, now() - query_start AS dur FROM pg_stat_activity WHERE query_id = -1234567890123456789;
```

Колонки из ИТС 6011 (`Memory` = `shared_blks_read + shared_blks_written`, `IO` = `local_blks_read + local_blks_written`, `Temp` = `temp_blks_read + temp_blks_written`, сортировка по `total_exec_time`) — см. конспект `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, раздел 4.8.

### 4.5. Сброс и работа с интервалами

```sql
SELECT pg_stat_statements_reset();                 -- сбросить всё (по умолчанию только суперпользователь)
SELECT pg_stat_statements_reset(0, 0, 123456789);  -- только один queryid (12+): (userid, dbid, queryid)
SELECT pg_stat_statements_reset(0, 0, 0, true);    -- только min/max времена (17+: параметр minmax_only)
GRANT EXECUTE ON FUNCTION pg_stat_statements_reset(oid, oid, bigint, boolean) TO monitor;   -- сигнатура для 17+
```

Счётчики накопительные с момента сброса, поэтому «что было с 14:00 до 15:00» получают разностью двух снимков. Таблицу снимков держите в служебной базе, **не в базе 1С**:

```sql
\c postgres
CREATE TABLE IF NOT EXISTS pgss_snap AS SELECT now() AS ts, * FROM pg_stat_statements WITH NO DATA;
INSERT INTO pgss_snap SELECT now(), * FROM pg_stat_statements;      -- выполнить в начале и в конце интервала

WITH t AS (SELECT DISTINCT ts FROM pgss_snap ORDER BY ts DESC LIMIT 2),
     b AS (SELECT * FROM pgss_snap WHERE ts = (SELECT min(ts) FROM t)),
     e AS (SELECT * FROM pgss_snap WHERE ts = (SELECT max(ts) FROM t))
SELECT e.calls - coalesce(b.calls, 0)                                              AS calls,
       round((e.total_exec_time - coalesce(b.total_exec_time, 0))::numeric / 1000, 1) AS exec_s,
       e.rows - coalesce(b.rows, 0)                                                AS rows,
       left(regexp_replace(e.query, '\s+', ' ', 'g'), 150)                         AS query
FROM e LEFT JOIN b USING (userid, dbid, queryid, toplevel)
WHERE e.calls > coalesce(b.calls, 0)
ORDER BY exec_s DESC
LIMIT 20;
```

Готовый инструмент для того же — `pg_profile` / `pgpro_pwr` (раздел 10.6); учтите, что он при каждой выборке сбрасывает `pg_stat_statements`.

### 4.6. Особенности с запросами 1С

- **Нормализация.** Платформа передаёт значения параметров прямо в тексте SQL (литералы вида `'\\200\\310…'::bytea`, `CAST(0 AS NUMERIC)` — как в примерах ИТС 6011). `pg_stat_statements` заменяет константы на `$1`, `$2`… и объединяет запросы с одинаковой структурой **[офиц.]**. Текст в `query` — от первого встреченного экземпляра; при высокой скорости вытеснения в тексте могут остаться константы.
- **Временные таблицы.** Запрос 1С к временной таблице выглядит как `… INNER JOIN pg_temp.tt7 T2 …`. `queryid` вычисляется по дереву разбора после анализа; до версии 17 включительно в него входит OID таблицы, а OID временной таблицы у каждого соединения свой. Плюс номер `tt<N>` выдаётся по счётчику соединения. Итог: один и тот же запрос 1С размножается на десятки–сотни записей, `dealloc` растёт, «топ» размывается. Что делать:
  - увеличить `pg_stat_statements.max` (10000–20000) и следить за `SELECT dealloc FROM pg_stat_statements_info;`;
  - группировать вручную, заменяя номера временных таблиц (запрос Q-27);
  - на PostgreSQL 18 идентификатор считается по **имени** таблицы, поэтому одинаковые `tt7` из разных соединений сливаются в одну запись **[офиц., release notes 18]**; разные номера (`tt7` и `tt12`) всё равно дают разные записи.
- **Списки `IN (…)`.** До 18 каждая длина списка констант давала отдельную запись; в 18 списки констант сворачиваются: `IN ($1 /*, ... */)` **[офиц.]**.
- **Служебные команды.** 1С выполняет много `BEGIN` / `COMMIT`, `SET`, `create temporary table tt…`, `TRUNCATE`, `ANALYZE`. Время `COMMIT` информативно (упор в сброс WAL), но если служебные команды забивают представление — `pg_stat_statements.track_utility = off`. В 18 значения в `SET` параметризуются, шума меньше.
- **Откуда запрос в коде 1С.** `pg_stat_statements` не знает ни сеанса, ни строки кода. Берите характерный фрагмент текста (имена таблиц `_AccumRg17539`, `_Document1337`) и ищите его в ТЖ: событие `DBPOSTGRS` содержит `Context` со стеком встроенного языка. Перевод имён таблиц в метаданные — раздел 8.
- **Неполные тексты в `pg_stat_activity`** — это `track_activity_query_size`, к `pg_stat_statements` не относится: тот хранит полный текст.

## 5. Журнал PostgreSQL, auto_explain, pgBadger

### 5.1. Где лежит журнал

| Сборка | Куда пишется | Как найти |
|---|---|---|
| Раскладка Debian/Ubuntu (PGDG, пакеты Ubuntu, сборка 1С) | `logging_collector = off`, stderr перехватывает `pg_ctlcluster`: `/var/log/postgresql/postgresql-18-main.log`; ротация — `logrotate` (`/etc/logrotate.d/postgresql-common`) | `pg_lsclusters` (колонка Log file) |
| Любая, если `logging_collector = on` | каталог `log_directory` (по умолчанию `log` внутри каталога данных), имя по `log_filename` | `SELECT pg_current_logfile();` |
| Postgres Pro 1С | зависит от настроек кластера: либо сборщик журнала в `…/data/log`, либо journald | `SHOW logging_collector; SHOW log_directory; SELECT pg_current_logfile();` затем `journalctl -u postgrespro-1c-17` (Подтверждено 11.10.2026 чтением пакета `postgrespro-1c-16-server` 16.14: умолчание пакета — сборщик журнала включён скриптом `pg-setup`, файлы лежат в `…/data/log`; в journald попадают только сообщения раннего запуска) |

```bash
pg_lsclusters
sudo tail -f /var/log/postgresql/postgresql-18-main.log
sudo -u postgres psql -Atc "SELECT pg_current_logfile()"          # NULL, если сборщик журнала выключен
sudo -u postgres psql -c "SELECT name, size, modification FROM pg_ls_logdir() ORDER BY modification DESC LIMIT 5"
```

### 5.2. Параметры журналирования

Значения по умолчанию — для PostgreSQL 18 **[офиц.]**.

| Параметр | По умолчанию | Что делает | Совет для 1С |
|---|---|---|---|
| `log_min_duration_statement` | `-1` | писать операторы длительностью не меньше порога; `0` — все, `-1` — выключено | постоянно `1s`–`5s`; `0` — только кратковременно |
| `log_min_duration_sample` + `log_statement_sample_rate` | `-1` / `1.0` | писать **долю** операторов длиннее порога (13+) | например `100ms` и `0.05` — выборка без лавины |
| `log_transaction_sample_rate` | `0` | писать все операторы доли транзакций | для разбора логики транзакций на стенде |
| `log_statement` | `none` | `none` / `ddl` / `mod` / `all` — писать операторы до выполнения | `ddl` полезно (видна реструктуризация); `all` не включать вместе с `log_min_duration_statement` |
| `log_duration` | `off` | писать длительность каждого оператора (без текста) | обычно не нужно |
| `log_lock_waits` | `off` | ожидания блокировок дольше `deadlock_timeout` | **`on`** |
| `log_lock_failures` | `off` (18) | неудачные `SELECT … NOWAIT` | по необходимости |
| `log_temp_files` | `-1` | писать временные файлы не меньше порога (кБ) при удалении; `0` — все | `10MB`–`100MB`; `0` на время разбора |
| `log_checkpoints` | `on` (с 15) | контрольные точки | `on` |
| `log_autovacuum_min_duration` | `10min` (с 15; раньше `-1`) | действия автоочистки длительнее порога | `10s`–`1min`; `0` на время разбора |
| `log_connections` | выключено | подключения; в 18 — список `receipt`, `authentication`, `authorization`, `setup_durations`, `all` | включать на время разбора: у 1С пул, шума немного, но он есть |
| `log_disconnections` | `off` | отключения с длительностью сеанса | вместе с `log_connections` |
| `log_line_prefix` | `'%m [%p] '` | префикс строки | см. 5.3 |
| `log_error_verbosity` | `default` | `terse` / `default` / `verbose` | `default` (требование pgBadger) |
| `log_min_error_statement` | `error` | писать текст оператора, вызвавшего ошибку такого уровня | `error` |
| `log_min_messages` | `warning` | минимальный уровень сообщений | `warning`; `debug1`…`debug5` — только кратко (ИТС 6011: журнал огромный, СУБД замедляется) |
| `log_parameter_max_length` | `-1` | длина значений связанных параметров в журнале | `1024` |
| `log_hostname` | `off` | писать имя хоста клиента (обратный DNS) | `off` |
| `log_recovery_conflict_waits` | `off` | ожидания конфликтов восстановления на реплике | `on` на реплике |
| `log_replication_commands` | `off` | команды репликации | по необходимости |
| `log_timezone` | задаётся `initdb` | часовой пояс меток времени | местный |
| `lc_messages` | локаль `initdb` | язык сообщений | `'C'` или `'en_US.UTF-8'` (ИТС 6011, pgBadger) |
| `log_destination` | `stderr` | `stderr`, `csvlog`, `jsonlog` (15+), `syslog` | `stderr`; для машинного разбора добавить `jsonlog` |
| `logging_collector` | `off` | свой сборщик журнала с ротацией | в Ubuntu не обязателен; нужен для `csvlog` / `jsonlog` и посуточных файлов (перезапуск) |
| `log_directory`, `log_filename` | `log`, `postgresql-%Y-%m-%d_%H%M%S.log` | каталог и шаблон имени | ИТС 6006: `log_filename = 'postgresql-%Y-%m-%d.log'` |
| `log_rotation_age`, `log_rotation_size` | `1d`, `10MB` | ротация по времени и размеру | ИТС 6006: `log_rotation_size = 0` (один файл в сутки) |
| `log_truncate_on_rotation` | `off` | перезаписывать файл с тем же именем | `on` вместе с шаблоном вроде `postgresql-%a.log` (неделя по кругу) |

Вид записей, которые стоит уметь узнавать:

```text
LOG:  duration: 12873.412 ms  statement: SELECT T1._IDRRef, ... FROM _Document1337 T1 ...
LOG:  temporary file: path "base/pgsql_tmp/pgsql_tmp21456.3", size 1073741824
STATEMENT:  SELECT ...
LOG:  checkpoint starting: time
LOG:  checkpoint complete: wrote 53412 buffers (5.1%), wrote 87 SLRU buffers; 0 WAL file(s) added, 3 removed, 30 recycled; write=269.912 s, sync=0.412 s, total=270.502 s; ...
LOG:  checkpoint starting: wal
LOG:  automatic vacuum of table "erp.public._inforg12345": index scans: 1 ...
```

- Формат `checkpoint complete` — как в 18; до 17 включительно части `, wrote N SLRU buffers` нет, после процента сразу `;` (сверено 19.10.2026 с `LogCheckpointEnd()` в `xlog.c` REL_18_STABLE и замечаниями к выпуску 18).
- `checkpoint starting: wal` — контрольная точка вызвана заполнением WAL (мал `max_wal_size`); `time` — по расписанию (`checkpoint_timeout`). Частые `wal` — повод увеличить `max_wal_size`.
- `temporary file … size` — запросу не хватило `work_mem`; строка `STATEMENT` показывает виновника.
- Не включайте одновременно `log_min_duration_statement`, `log_duration` и `log_statement = 'all'` (предупреждение pgBadger): при `log_statement = 'all'` текст оператора не попадёт в строку с длительностью.

### 5.3. log_line_prefix

| Экран | Значение | Экран | Значение |
|---|---|---|---|
| `%m` | время с миллисекундами | `%t` | время без миллисекунд |
| `%n` | время в формате Unix-эпохи с мс | `%p` | PID процесса |
| `%u` | роль | `%d` | база |
| `%a` | `application_name` | `%h` | адрес клиента |
| `%r` | адрес и порт клиента | `%L` | локальный адрес сервера (18) |
| `%b` | тип процесса | `%P` | PID лидера параллельной группы |
| `%c` | идентификатор сеанса | `%l` | номер строки журнала в сеансе |
| `%s` | время старта процесса | `%v` | виртуальный идентификатор транзакции |
| `%x` | идентификатор транзакции (0, если нет) | `%e` | SQLSTATE |
| `%i` | тег команды | `%Q` | идентификатор запроса (`query_id`; 0, если не вычисляется) |
| `%q` | для несеансовых процессов — остановиться здесь | `%%` | символ `%` |

Варианты:

```ini
# как в ИТС 6006 и в классической документации pgBadger
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
# то же с миллисекундами (точнее сопоставление с ТЖ 1С, где время с микросекундами)
log_line_prefix = '%m [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
# умолчание пакетов Debian/Ubuntu (createcluster.conf)
log_line_prefix = '%m [%p] %q%u@%d '
```

pgBadger требует в префиксе время (`%t`, `%m` или `%n`) и процесс (`%p` или `%c`); нестандартный префикс передаётся ему ключом `--prefix` **[офиц., README pgBadger]**. PID в квадратных скобках удобен для `grep -F '[12345]'` по `dbpid` из ТЖ 1С.

### 5.4. Два профиля: постоянный и диагностический

Постоянный профиль — в разделе 1.4. Диагностический (по ИТС 6011) включают на ограниченное время, потому что журнал растёт очень быстро, а сбор всех запросов при высокой нагрузке ухудшает производительность:

```sql
ALTER SYSTEM SET lc_messages = 'C';
ALTER SYSTEM SET log_min_duration_statement = 0;      -- все запросы
ALTER SYSTEM SET log_temp_files = 0;
ALTER SYSTEM SET log_autovacuum_min_duration = 0;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
SELECT pg_reload_conf();
-- ... воспроизвести проблему ...
ALTER SYSTEM RESET log_min_duration_statement;        -- вернуть значение из файлов конфигурации
ALTER SYSTEM RESET log_temp_files;
ALTER SYSTEM RESET log_autovacuum_min_duration;
ALTER SYSTEM RESET log_connections;
ALTER SYSTEM RESET log_disconnections;
SELECT pg_reload_conf();
```

Точечно, без общей лавины — только для одной базы или роли (действует на **новые** соединения; пул 1С подхватит по мере пересоздания соединений):

```sql
ALTER DATABASE erp SET log_min_duration_statement = '500ms';
ALTER ROLE usr1c  SET log_temp_files = 0;
-- отмена:
ALTER DATABASE erp RESET log_min_duration_statement;
```

Записи журнала многострочные. Приведение к одной строке на событие (из ИТС 6011) и подсчёт самых частых длинных запросов:

```bash
awk -vORS= '{ if (match($0, "^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] ")) print "\n"$0; else print "<line>"$0 }' \
    /var/log/postgresql/postgresql-18-main.log > /tmp/pg_oneline.log
grep -c 'duration: ' /tmp/pg_oneline.log
grep -oP 'duration: \K[0-9.]+' /tmp/pg_oneline.log | sort -rn | head        # самые длинные, мс
```

### 5.5. auto_explain: планы длинных запросов в журнале

Модуль пишет в журнал план каждого запроса, выполнявшегося дольше порога, — без ручного `EXPLAIN` **[офиц.]**. Для 1С он незаменим, когда запрос нельзя воспроизвести вручную: временные таблицы, заполняемые через `COPY … FROM STDIN` (вставка таблицы значений), нигде не журналируются, и цепочку запросов по ТЖ не собрать (ИТС 6011).

Способы загрузки:

| Способ | Команда | Когда действует |
|---|---|---|
| Для всех, постоянно | `shared_preload_libraries = '…,auto_explain'` | после перезапуска |
| Для новых сеансов, без перезапуска | `ALTER SYSTEM SET session_preload_libraries = 'auto_explain'; SELECT pg_reload_conf();` (или `ALTER DATABASE erp SET session_preload_libraries = 'auto_explain';`) | для новых соединений |
| В одном сеансе `psql` | `LOAD 'auto_explain'; SET auto_explain.log_min_duration = 0;` | только суперпользователь, только этот сеанс |

Параметры (все — только суперпользователь) **[офиц.]**:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `auto_explain.log_min_duration` | `-1` | порог длительности; `0` — все планы; `-1` — выключено. **Без него модуль ничего не пишет** |
| `auto_explain.log_analyze` | `off` | писать `EXPLAIN ANALYZE` (факт), а не просто план |
| `auto_explain.log_buffers` | `off` | статистика буферов (нужен `log_analyze`) |
| `auto_explain.log_wal` | `off` | статистика WAL (нужен `log_analyze`) |
| `auto_explain.log_timing` | `on` | время по узлам (нужен `log_analyze`); `off` — только число строк, заметно дешевле |
| `auto_explain.log_triggers` | `off` | статистика триггеров (нужен `log_analyze`) |
| `auto_explain.log_verbose` | `off` | как `EXPLAIN VERBOSE` |
| `auto_explain.log_settings` | `off` | изменённые параметры, влияющие на планирование (покажет `enable_mergejoin = off`, `cpu_operator_cost = 0.001` от платформы 1С) |
| `auto_explain.log_format` | `text` | `text` / `xml` / `json` / `yaml` |
| `auto_explain.log_level` | `LOG` | уровень сообщения |
| `auto_explain.log_nested_statements` | `off` | учитывать операторы внутри функций |
| `auto_explain.log_parameter_max_length` | `-1` | длина значений параметров запроса в журнале; `0` — не писать |
| `auto_explain.sample_rate` | `1` | доля операторов сеанса, для которых снимается план |

Цена **[офиц.]**: при `log_analyze = on` замер времени по узлам выполняется для **всех** операторов, даже не дошедших до порога; это может крайне негативно влиять на производительность. `log_timing = off` снимает основную часть накладных расходов ценой потери времён по узлам; `sample_rate < 1` инструментирует только долю запросов.

Профили:

```ini
# постоянно на продуктиве: только план (без факта) у запросов дольше 30 с — накладных расходов почти нет
auto_explain.log_min_duration = '30s'
auto_explain.log_analyze = off

# на время расследования: факт по строкам и буферам, без времён узлов
auto_explain.log_min_duration = '10s'      # значение из ИТС 6011
auto_explain.log_analyze = on
auto_explain.log_buffers = on
auto_explain.log_timing = off
auto_explain.log_settings = on
auto_explain.sample_rate = 1
```

Вид записи:

```text
LOG:  duration: 35215.118 ms  plan:
        Query Text: SELECT T1._Fld12346RRef, ... FROM _AccumRg12345 T1 INNER JOIN pg_temp.tt15 T2 ON ...
        Nested Loop  (cost=0.56..1250.33 rows=1 width=52) (actual rows=118340 loops=1)
          ...
```

Если модуль ещё не загружен, параметры `auto_explain.*` надёжнее вписывать в файл конфигурации, а не через `ALTER SYSTEM` (сервер может не знать таких параметров до загрузки библиотеки) **[практика]**.

В сборках «PostgreSQL с патчем от 1С» есть расширение **`auto_dump`** (версия 1.1 — ИТС 6039; входит и в бесплатную сборку «PostgreSQL для 1С» от Postgres Professional — приложение F.5 её документации 16.14, сверено 19.10.2026): по условию (длительность, отмена запроса, расхождение оценки и факта, фрагмент текста) сохраняет текст запроса, план и дамп участвующих временных таблиц, чтобы воспроизвести проблему без платформы. Описание — `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, разделы 1 и 3.

### 5.6. pgBadger: отчёт по журналу

pgBadger — анализатор журналов PostgreSQL на Perl, строит HTML-отчёт: самые долгие и самые частые запросы (с нормализацией), ожидания блокировок, временные файлы, контрольные точки, автоочистка, соединения, ошибки **[офиц., проект pgBadger]**. Последняя версия — 13.2 (2025-12-29); поддерживает форматы stderr, csvlog, jsonlog, syslog, журнал pgbouncer.

Установка:

```bash
sudo apt install pgbadger                 # Ubuntu 24.04: 12.4-1; Ubuntu 26.04: 13.2-1 (universe)
pgbadger --version
# либо свежая версия из исходников:
#   tar xzf pgbadger-13.2.tar.gz && cd pgbadger-13.2 && perl Makefile.PL && make && sudo make install
```

Требования к настройкам сервера (README pgBadger): `log_min_duration_statement` (чем меньше порог, тем полнее отчёт), `log_checkpoints = on`, `log_connections = on`, `log_disconnections = on`, `log_lock_waits = on`, `log_temp_files = 0`, `log_autovacuum_min_duration = 0`, `log_error_verbosity = default`, `lc_messages = 'en_US.UTF-8'` или `'C'`, подходящий `log_line_prefix`.

Запуск:

```bash
# один файл, 4 процесса, отчёт в HTML
pgbadger -j 4 /var/log/postgresql/postgresql-18-main.log -o /tmp/pg_report.html

# явный префикс (если формат не распознан автоматически), только база erp, заданный интервал
pgbadger -j 4 --prefix '%m [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ' -d erp \
         -b "2026-10-09 09:00:00" -e "2026-10-09 18:00:00" \
         /var/log/postgresql/postgresql-18-main.log* -o /tmp/day.html

# несколько файлов, включая сжатые; исключить шум
pgbadger --exclude-query="^(COPY|COMMIT|BEGIN)" /var/log/postgresql/postgresql-18-main.log.2.gz \
         /var/log/postgresql/postgresql-18-main.log.1 /var/log/postgresql/postgresql-18-main.log -o /tmp/week.html

# журнал с удалённого сервера по SSH
pgbadger ssh://admin@db01//var/log/postgresql/postgresql-18-main.log -o /tmp/db01.html

# инкрементальный режим: посуточные и понедельные отчёты в каталоге, хранить 4 недели (cron, 04:00)
0 4 * * * /usr/bin/pgbadger -I -q --retention 4 /var/log/postgresql/postgresql-18-main.log.1 -O /var/www/pg_reports/
```

| Ключ | Назначение |
|---|---|
| `-o файл` / `-O каталог` | выходной файл / каталог (для `-I`) |
| `-f формат` | принудительно задать формат журнала (`stderr`, `csv`, `jsonlog`, `syslog`…) |
| `-p`, `--prefix` | значение `log_line_prefix`, если оно нестандартное |
| `-j N` / `-J N` | параллельный разбор одного файла / нескольких файлов (`-j` не действует на сжатые файлы и CSV; сжатые файлы можно разбирать параллельно по одному на процесс через `-J`) |
| `-b`, `-e` | начало и конец интервала |
| `-d база`, `-u роль` | отбор по базе / роли |
| `-I`, `--retention N` | инкрементальный режим; хранить N недель |
| `-x формат` | формат отчёта: `html` (по умолчанию), `text`, `json`, `bin` |
| `--exclude-query regex` | исключить запросы по регулярному выражению |
| `--noexplain` | не обрабатывать строки `auto_explain` |
| `-q` | без индикатора выполнения (для cron) |

Замечания:

- В раскладке Ubuntu журнал ротируется `logrotate` раз в неделю, файл `.log.1` — прошлая неделя. Для посуточных отчётов удобнее включить `logging_collector` с `log_filename = 'postgresql-%Y-%m-%d.log'` и передавать pgBadger вчерашний файл.
- Запросы 1С с литералами pgBadger нормализует сам; имена временных таблиц `tt<N>` — нет, поэтому один запрос может появляться в «Top» несколько раз.
- Полнота раздела «Top queries» определяется порогом `log_min_duration_statement`: при `5s` отчёт покажет только запросы длиннее 5 секунд, а «тысячи быстрых» — нет; их показывает `pg_stat_statements`.

## 6. Статистические представления и ключевые метрики

Все счётчики накопительные с момента `stats_reset`. Смотреть нужно на **скорость изменения** (разность двух снимков), а не на абсолютные значения. С PostgreSQL 15 статистика хранится в разделяемой памяти и сбрасывается на диск при штатной остановке; после аварийного завершения счётчики обнуляются **[офиц.]**.

### 6.1. pg_stat_database — здоровье базы в целом

| Столбцы | Смысл | Метрика и ориентир |
|---|---|---|
| `numbackends` | текущее число соединений (единственный не накопительный столбец) | сравнивать с `max_connections` |
| `xact_commit`, `xact_rollback` | зафиксировано / отменено транзакций | TPS = Δ`xact_commit`/сек; доля откатов = `xact_rollback / (xact_commit + xact_rollback)` — рост говорит об ошибках и таймаутах блокировок |
| `blks_read`, `blks_hit` | блоки, прочитанные мимо буферного кеша PostgreSQL / найденные в нём | cache hit ratio = `blks_hit / (blks_hit + blks_read)`; для OLTP-нагрузки 1С обычно > 99 %. Не учитывает кеш ОС: `blks_read` — не обязательно чтение с диска |
| `tup_returned`, `tup_fetched` | строк прочитано при сканировании / выбрано по индексу | `tup_returned` ≫ `tup_fetched` — много последовательных сканирований |
| `tup_inserted`, `tup_updated`, `tup_deleted` | объём изменений | профиль нагрузки, оценка работы для автоочистки |
| `temp_files`, `temp_bytes` | число и объём временных файлов | рост — не хватает `work_mem` (сортировки, хеши) |
| `deadlocks` | обнаружено взаимоблокировок | любой рост — разбирать (раздел 3.5) |
| `conflicts` | запросы, отменённые из-за конфликтов восстановления (только на реплике) | подробности — `pg_stat_database_conflicts` |
| `checksum_failures`, `checksum_last_failure` | ошибки контрольных сумм страниц | больше 0 — повреждение данных, срочно |
| `blk_read_time`, `blk_write_time` | время чтения / записи блоков, мс (при `track_io_timing`) | среднее время чтения блока = Δ`blk_read_time` / Δ`blks_read` |
| `session_time`, `active_time`, `idle_in_transaction_time` | суммарное время сеансов / выполнения запросов / простоя в транзакции, мс (14+) | доля `idle_in_transaction_time` — «время, когда СУБД ждала сервер 1С с открытой транзакцией» |
| `sessions`, `sessions_abandoned`, `sessions_fatal`, `sessions_killed` | число сеансов; оборванных клиентом; завершённых фатальной ошибкой; завершённых оператором | рост `sessions_abandoned` — падения `rphost` или сетевые обрывы |
| `parallel_workers_to_launch`, `parallel_workers_launched` | параллельные процессы (18) | для 1С обычно нули |
| `stats_reset` | время сброса | знаменатель для «в секунду» |

```sql
SELECT datname, numbackends,
       round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2)              AS cache_hit_pct,
       round(100.0 * xact_rollback / nullif(xact_commit + xact_rollback, 0), 2)  AS rollback_pct,
       temp_files, pg_size_pretty(temp_bytes) AS temp_size, deadlocks,
       round(blk_read_time::numeric / nullif(blks_read, 0), 3)                   AS ms_per_read,
       stats_reset
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY blks_read DESC;
```

### 6.2. pg_stat_user_tables — как используются таблицы

(`pg_stat_all_tables` — все таблицы, `pg_stat_sys_tables` — системные, `pg_stat_user_tables` — пользовательские.)

| Столбцы | Смысл | На что смотреть |
|---|---|---|
| `seq_scan`, `seq_tup_read` | число последовательных сканирований и прочитанных ими строк | большая таблица + большой `seq_tup_read` — не хватает индекса или условие не использует индекс; `seq_tup_read / seq_scan` ≈ размер таблицы — читается целиком |
| `idx_scan`, `idx_tup_fetch` | число индексных сканирований и выбранных строк | |
| `last_seq_scan`, `last_idx_scan` | время последнего сканирования (16+) | |
| `n_tup_ins`, `n_tup_upd`, `n_tup_del` | вставлено / изменено / удалено строк | |
| `n_tup_hot_upd`, `n_tup_newpage_upd` (16+) | HOT-обновления / обновления с переносом на другую страницу | низкая доля HOT у часто обновляемой таблицы — кандидат на уменьшение `fillfactor` |
| `n_live_tup`, `n_dead_tup` | оценка числа живых и мёртвых строк | высокая доля мёртвых — автоочистка не успевает или её держит длинная транзакция |
| `n_mod_since_analyze`, `n_ins_since_vacuum` | изменений после последнего ANALYZE / вставок после VACUUM | давно не анализировалась — устаревшая статистика планировщика |
| `last_vacuum`, `last_autovacuum`, `last_analyze`, `last_autoanalyze` | время последних операций | |
| `vacuum_count`, `autovacuum_count`, `analyze_count`, `autoanalyze_count` | счётчики операций | |
| `total_vacuum_time`, `total_autovacuum_time`, `total_analyze_time`, `total_autoanalyze_time` | суммарное время, мс (18) | |

Временные таблицы 1С автоочистка **не обрабатывает** (у неё нет доступа к чужим временным таблицам), поэтому статистику по ним собирает только явный `ANALYZE` в том же сеансе **[офиц.]**.

### 6.3. pg_stat_user_indexes и pg_statio_*

| Представление | Столбцы | Назначение |
|---|---|---|
| `pg_stat_user_indexes` | `relname`, `indexrelname`, `idx_scan`, `last_idx_scan` (16+), `idx_tup_read`, `idx_tup_fetch` | используется ли индекс; `idx_scan = 0` за длительный срок — кандидат в неиспользуемые |
| `pg_statio_user_tables` | `heap_blks_read` / `heap_blks_hit`, `idx_blks_read` / `idx_blks_hit`, `toast_blks_*`, `tidx_blks_*` | какие таблицы чаще всего читаются мимо буферного кеша |
| `pg_statio_user_indexes` | `idx_blks_read`, `idx_blks_hit` | то же по индексам |

Про неиспользуемые индексы в базе 1С: состав индексов определяет платформа по метаданным (свойство «Индексировать», измерения регистров и т. п.). Удалённый вручную индекс платформа восстановит при реструктуризации, а до того его отсутствие может замедлить типовой запрос. Убирают лишний индекс изменением конфигурации. Свои индексы, созданные в обход платформы, теряются при реструктуризации таблицы **[практика]**. Статистика использования индексов на реплике своя.

### 6.4. Фоновая запись и контрольные точки

PostgreSQL 17+:

| Представление | Столбцы | Смысл |
|---|---|---|
| `pg_stat_checkpointer` | `num_timed`, `num_requested`, `num_done` (18), `restartpoints_timed`, `restartpoints_req`, `restartpoints_done`, `write_time`, `sync_time`, `buffers_written`, `slru_written` (18), `stats_reset` | контрольные точки по расписанию / по требованию, время записи и синхронизации (мс) |
| `pg_stat_bgwriter` | `buffers_clean`, `maxwritten_clean`, `buffers_alloc`, `stats_reset` | буферы, записанные фоновым процессом; сколько раз он останавливался, упёршись в `bgwriter_lru_maxpages` |

PostgreSQL ≤ 16: всё в `pg_stat_bgwriter` — `checkpoints_timed`, `checkpoints_req`, `checkpoint_write_time`, `checkpoint_sync_time`, `buffers_checkpoint`, `buffers_clean`, `maxwritten_clean`, `buffers_backend`, `buffers_backend_fsync`, `buffers_alloc`.

Ориентиры **[практика]**:

- Доля контрольных точек «по требованию» (`num_requested` / `checkpoints_req`) должна быть малой; если она сравнима с плановыми — увеличить `max_wal_size`.
- `maxwritten_clean` быстро растёт — фоновая запись упирается в лимит; ИТС и Postgres Pro рекомендуют для 1С `bgwriter_lru_maxpages = 400`, `bgwriter_lru_multiplier = 4.0`, `bgwriter_delay = 20ms`.
- «Бэкенды пишут сами» (раньше `buffers_backend`) с версии 17 смотрят в `pg_stat_io`: строки `backend_type = 'client backend'`, `context = 'normal'`, столбец `writes`.

### 6.5. pg_stat_wal

Столбцы в 18: `wal_records`, `wal_fpi` (полные образы страниц), `wal_bytes`, `wal_buffers_full`, `stats_reset`. В 14–17 были ещё `wal_write`, `wal_sync`, `wal_write_time`, `wal_sync_time` (в 18 — в `pg_stat_io`, `object = 'wal'`).

- Скорость генерации WAL = Δ`wal_bytes` / время — нужна для расчёта `max_wal_size`, места под архив и канала до реплики.
- `wal_buffers_full` растёт — мал `wal_buffers`.
- Высокая доля `wal_fpi` сразу после контрольных точек — следствие `full_page_writes`; смягчается более редкими контрольными точками.

### 6.6. pg_stat_io (16+)

Одна строка на сочетание `backend_type` × `object` (`relation`, `temp relation`, с 18 — `wal`) × `context` (`normal`, `init`, `vacuum`, `bulkread`, `bulkwrite`). Столбцы: `reads`, `read_bytes` (18), `read_time`, `writes`, `write_bytes` (18), `write_time`, `writebacks`, `writeback_time`, `extends`, `extend_bytes` (18), `extend_time`, `hits`, `evictions`, `reuses`, `fsyncs`, `fsync_time`, `stats_reset`. Времена заполняются при `track_io_timing` (для WAL — `track_wal_io_timing`).

Что из него видно:

- кто читает и пишет больше всех (клиентские процессы, автоочистка, контрольные точки, фоновая запись);
- `object = 'temp relation'` — ввод-вывод временных таблиц 1С, не уместившихся в `temp_buffers`;
- `evictions` у `client backend` — вытеснение буферов из-за нехватки `shared_buffers`;
- `fsyncs` у `client backend` должны быть около нуля.

### 6.7. Архивация и репликация

| Представление | Столбцы | Назначение |
|---|---|---|
| `pg_stat_archiver` | `archived_count`, `last_archived_wal`, `last_archived_time`, `failed_count`, `last_failed_wal`, `last_failed_time`, `stats_reset` | работает ли `archive_command` / `archive_library`; рост `failed_count` и старый `last_archived_time` — архивация стоит, `pg_wal` переполнится |
| `pg_stat_replication` (на ведущем) | `pid`, `usename`, `application_name`, `client_addr`, `backend_start`, `backend_xmin`, `state` (`startup`, `catchup`, `streaming`, `backup`, `stopping`), `sent_lsn`, `write_lsn`, `flush_lsn`, `replay_lsn`, `write_lag`, `flush_lag`, `replay_lag`, `sync_priority`, `sync_state` (`async`, `potential`, `sync`, `quorum`), `reply_time` | состояние и отставание каждой реплики |
| `pg_stat_wal_receiver` (на реплике) | состояние приёмника WAL | подключена ли реплика к ведущему |
| `pg_replication_slots` | `slot_name`, `slot_type`, `active`, `restart_lsn`, `xmin`, `catalog_xmin`, `wal_status`, `safe_wal_size` | неактивный слот удерживает WAL и горизонт очистки |
| `pg_stat_replication_slots` | `spill_txns`, `spill_bytes`, `stream_txns`, `total_txns`, `total_bytes` | статистика логических слотов (механизм копий базы данных 1С использует логическое декодирование) |
| `pg_stat_database_conflicts` (на реплике) | `confl_tablespace`, `confl_lock`, `confl_snapshot`, `confl_bufferpin`, `confl_deadlock`, `confl_active_logicalslot` | причины отмены запросов на реплике |

Запросы — Q-33…Q-36 в библиотеке.

### 6.8. pg_stat_progress_* — ход длительных операций

| Представление | Команды | Ключевые столбцы и фазы |
|---|---|---|
| `pg_stat_progress_vacuum` | `VACUUM`, автоочистка (не `VACUUM FULL`) | `phase`: `initializing`, `scanning heap`, `vacuuming indexes`, `vacuuming heap`, `cleaning up indexes`, `truncating heap`, `performing final cleanup`; `heap_blks_total`, `heap_blks_scanned`, `heap_blks_vacuumed`, `index_vacuum_count`; 17+: `indexes_total`, `indexes_processed`, `dead_tuple_bytes`; 18: `delay_time` |
| `pg_stat_progress_cluster` | `CLUSTER`, `VACUUM FULL` | `command`, `phase`: `seq scanning heap`, `index scanning heap`, `sorting tuples`, `writing new heap`, `swapping relation files`, `rebuilding index`, `performing final cleanup`; `heap_blks_total`, `heap_blks_scanned`, `heap_tuples_written`, `index_rebuild_count` |
| `pg_stat_progress_create_index` | `CREATE INDEX`, `REINDEX` (в том числе `CONCURRENTLY`) | `command`, `phase`: `building index`, `waiting for writers before build`, `index validation: …`, `waiting for old snapshots`, …; `blocks_total` / `blocks_done`, `tuples_total` / `tuples_done`, `lockers_total` / `lockers_done`, `current_locker_pid` |
| `pg_stat_progress_analyze` | `ANALYZE` | `phase`: `acquiring sample rows`, `computing statistics`, …; `sample_blks_total`, `sample_blks_scanned` |
| `pg_stat_progress_copy` (14+) | `COPY` | `command`, `type`, `bytes_processed`, `bytes_total`, `tuples_processed` |
| `pg_stat_progress_basebackup` | `pg_basebackup` | `phase`: `waiting for checkpoint to finish`, `estimating backup size`, `streaming database files`, `waiting for wal archiving to finish`, `transferring wal files`; `backup_total`, `backup_streamed` |

Реструктуризацию 1С (создание новой таблицы, перенос данных, построение индексов) видно в `pg_stat_progress_create_index` и по активным запросам `INSERT … SELECT` в `pg_stat_activity`. Запросы — Q-37…Q-40.

### 6.9. Сброс статистики

| Функция | Что сбрасывает |
|---|---|
| `pg_stat_reset()` | все счётчики текущей базы. **Внимание:** сбрасывает и счётчики, по которым автоочистка решает, когда чистить и анализировать таблицы; после сброса рекомендуется `ANALYZE` всей базы **[офиц.]** |
| `pg_stat_reset_shared('цель')` | общие для кластера счётчики; цель — одно из значений `bgwriter`, `checkpointer`, `archiver`, `io`, `wal`, `slru`, `recovery_prefetch`; без аргумента (17+) — все сразу. На 16: `checkpointer` и `slru` ещё недоступны (оба — с 17; SLRU на 16 сбрасывает `pg_stat_reset_slru()`), `io` — с 16 (сверено 19.10.2026 с замечаниями к выпуску 17) |
| `pg_stat_reset_single_table_counters(oid)` | счётчики одной таблицы или индекса |
| `pg_stat_reset_replication_slot(имя)` | статистика слота |
| `pg_stat_reset_backend_stats(pid)` | статистика одного бэкенда (18) |
| `pg_stat_statements_reset()` | `pg_stat_statements` |
| `pg_stat_clear_snapshot()` | сбросить кеш статистики в текущей транзакции (чтобы повторный запрос вернул свежие значения) |

## 7. EXPLAIN: как получить и прочитать план

### 7.1. Синтаксис и параметры

```sql
EXPLAIN [ ( параметр [, ...] ) ] оператор
```

Параметры (PostgreSQL 18) **[офиц.]**:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `ANALYZE` | `FALSE` | **выполнить** оператор и показать фактическое время и число строк по узлам |
| `BUFFERS` | `FALSE`; с 18 включается автоматически вместе с `ANALYZE` | обращения к буферам: `shared` / `local` / `temp`, `hit` / `read` / `dirtied` / `written`; при `track_io_timing` — время ввода-вывода |
| `VERBOSE` | `FALSE` | списки выходных столбцов узлов, имена со схемой, идентификатор запроса (`Query Identifier`) |
| `COSTS` | `TRUE` | оценочные стоимость, число строк и ширина строки |
| `SETTINGS` | `FALSE` | параметры, влияющие на планирование и отличающиеся от встроенных умолчаний (12+) |
| `WAL` | `FALSE` | записи WAL, полные образы страниц, байты (13+; нужен `ANALYZE`) |
| `TIMING` | `TRUE` | время по узлам (нужен `ANALYZE`); `OFF` уменьшает накладные расходы, если нужны только строки |
| `SUMMARY` | с `ANALYZE` — да | итоговые `Planning Time` / `Execution Time` |
| `GENERIC_PLAN` | `FALSE` | обобщённый план для запроса с параметрами `$1`… (16+; нельзя с `ANALYZE`) |
| `MEMORY` | `FALSE` | память, потраченная планировщиком (17+) |
| `SERIALIZE` | `NONE` | стоимость преобразования результата для передачи клиенту: `TEXT` / `BINARY` (17+; нужен `ANALYZE`) |
| `FORMAT` | `TEXT` | `TEXT` / `XML` / `JSON` / `YAML` |

Рабочая форма для разбора запросов 1С:

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS) SELECT ...;
-- если нужно только число строк, без дорогих замеров времени по узлам:
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF) SELECT ...;
-- изменяющий оператор — только в откатываемой транзакции:
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) UPDATE ...;
ROLLBACK;
```

`EXPLAIN ANALYZE` действительно выполняет оператор со всеми побочными эффектами (результат `SELECT` отбрасывается) **[офиц.]**. На боевой базе тяжёлый запрос создаст ту же нагрузку и те же блокировки, что и в 1С, — по возможности работайте на копии или реплике.

### 7.2. Как получить план запроса 1С

| Способ | Где работает | Замечания |
|---|---|---|
| `<plansql/>` в `logcfg.xml` → свойство `planSQLText` события `DBPOSTGRS` | только тестовый стенд | получение планов замедляет запросы; ИТС 6011 прямо запрещает на продуктивных серверах. Формат плана для PostgreSQL совпадает с форматом из документации СУБД **[офиц.]** |
| `auto_explain` → журнал PostgreSQL | продуктив | обязателен порог `log_min_duration`; раздел 5.5 |
| Расширение `auto_dump` (сборки с патчем 1С, «PostgreSQL для 1С» от Postgres Professional) | продуктив, по условию | сохраняет запрос, план и дамп временных таблиц |
| Вручную: текст из `DBPOSTGRS` → `psql` с `EXPLAIN` | где угодно | описано ниже |

Ручной способ (ИТС 6011) **[офиц.]**:

1. Взять текст запроса из свойства `Sql` события `DBPOSTGRS` (или из журнала PostgreSQL).
2. Собрать файл `query.sql`: сначала параметры сеанса, которые ставит платформа, затем запрос под `EXPLAIN`:

```sql
/* параметры соединения платформы 1С:Предприятие */
SET client_min_messages = error;
SET lc_messages TO 'en_US.UTF-8';
SET enable_mergejoin = off;
SET escape_string_warning = off;
SET cpu_operator_cost = 0.001;
SET client_encoding = 'utf8';
SET lock_timeout = 20000;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT T1._IDRRef, T1._Number, T1._Date_Time
FROM _Document1337 T1
WHERE (T1._Fld2830 = CAST(0 AS NUMERIC)) AND (T1._IDRRef = '\\200\\310p\\213\\315U\\034~\\021\\347\\025\\340@\\243\\3650'::bytea);
```

3. Выполнить и сохранить план:

```bash
# файл должен быть доступен на чтение пользователю postgres (например, лежать в /tmp)
sudo -u postgres psql -X --dbname=erp --file=/tmp/query.sql > /tmp/query.sqlplan
less /tmp/query.sqlplan
```

Подводные камни ручного способа:

- **`standard_conforming_strings`.** Платформа записывает двоичные значения в escape-формате с удвоенной обратной косой чертой (`'\\200\\310…'::bytea`) и рассчитывает на `standard_conforming_strings = off` (это требование 1С к `postgresql.conf`). Если в вашем сеансе `psql` значение `on`, литерал будет понят как другой набор байтов, условие ничего не найдёт и план покажет `rows=0`. Проверьте `SHOW standard_conforming_strings;` и при необходимости добавьте в файл `SET standard_conforming_strings = off;`. (Уточнено 19.10.2026 по документации PostgreSQL 18 — разд. 8.4.2 «`bytea` Escape Format» и параметр `standard_conforming_strings` (разд. 19.13.1): при `off` разборщик строковых литералов сам превращает `\\` в `\`, и функция ввода `bytea` получает `\200` — один байт 0x80; при `on` она получает `\\200` — байты `\`, `2`, `0`, `0`. Требование `standard_conforming_strings = off` — в ИТС 5866 и в приложении K.3.11 документации «PostgreSQL для 1С». На сервере пользователя это стоит проверить в первую очередь: быстрая установка 16.14 параметры для 1С не задаёт — см. `../guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`.)
- **Временные таблицы.** Если запрос обращается к `pg_temp.tt<N>`, перед ним нужно воспроизвести всю цепочку: `create temporary table tt7 (…)` → `create index tmpind_0 on pg_temp.tt7(…)` → `INSERT INTO pg_temp.tt7 … SELECT …` → `ANALYZE pg_temp.tt7` → исследуемый запрос. Запросы, создающие и заполняющие таблицы, лежат выше по ТЖ в том же соединении (`dbpid`). Автоматизация — скрипт `getPGQueryWithTempTables.sbsl` (1С:Исполнитель) из ИТС 6011 или расширение `auto_dump`.
- **`COPY … FROM STDIN`.** Данные, вставленные во временную таблицу из таблицы значений, в ТЖ не попадают — воспроизвести нельзя, остаётся `auto_explain` / `auto_dump`.
- **Тёплый и холодный кеш.** Первый запуск читает с диска (`Buffers: shared read=…`), второй — из кеша (`hit=…`). Сравнивайте одинаковые условия.
- **Параметры планировщика.** Без `enable_mergejoin = off` и `cpu_operator_cost = 0.001` план в `psql` может отличаться от того, что получает 1С.

### 7.3. Как читать план

План — дерево узлов; читается **изнутри наружу** (самые вложенные узлы выполняются первыми), строки от дочерних узлов поднимаются к родительским. Пример (сконструирован для иллюстрации типичной проблемы 1С):

```text
Nested Loop  (cost=0.56..1250.33 rows=1 width=52) (actual time=0.110..48211.512 rows=118340 loops=1)
  Buffers: shared hit=1432112 read=20311, local hit=812
  ->  Seq Scan on pg_temp_7.tt15 t2  (cost=0.00..1.01 rows=1 width=17) (actual time=0.012..35.120 rows=120000 loops=1)
        Buffers: local hit=812
  ->  Index Scan using _accumrg12345_1 on public._accumrg12345 t1  (cost=0.56..1249.31 rows=1 width=69) (actual time=0.350..0.398 rows=1 loops=120000)
        Index Cond: (t1._fld12346rref = t2._q_000_f_000rref)
        Filter: (t1._period >= '2026-01-01 00:00:00'::timestamp without time zone)
        Rows Removed by Filter: 14
        Buffers: shared hit=1432112 read=20311
Planning Time: 1.214 ms
Execution Time: 48230.775 ms
```

| Элемент | Смысл |
|---|---|
| `cost=0.56..1250.33` | оценка стоимости: до выдачи первой строки .. полная. Условные единицы (`seq_page_cost = 1.0`); стоимость родителя включает дочерние узлы |
| `rows=1` (в скобках `cost`) | **оценка** числа строк, которые выдаст узел |
| `width=52` | оценка средней ширины строки, байт |
| `actual time=0.350..0.398` | фактическое время, мс: до первой строки .. до последней, **за один проход** узла |
| `rows=1` (в скобках `actual`) | фактическое число строк **за один проход** (среднее; в 18 печатается дробным — `rows=1.00`) |
| `loops=120000` | сколько раз узел выполнялся. Итог по узлу = значение × `loops`: здесь 0.398 мс × 120000 ≈ 47.8 с — вот где всё время запроса |
| `Index Cond` | условие, применённое при поиске по индексу |
| `Filter` + `Rows Removed by Filter` | условие, проверенное уже после чтения строки, и сколько строк отброшено (за проход): здесь 14 лишних строк на каждую найденную |
| `Buffers: shared hit=… read=…` | страницы постоянных таблиц: найдены в буферном кеше / прочитаны вне его; значения **накопительные** (узел плюс все дочерние) — складывать родителя с детьми нельзя |
| `Buffers: local …` | страницы временных таблиц |
| `Buffers: temp read=… written=…` | временные файлы (сортировка, хеш, материализация на диске) |
| `Planning Time` / `Execution Time` | время планирования / выполнения (без разбора текста и без передачи результата клиенту) |

Разбор примера: во временной таблице `tt15` планировщик ожидал 1 строку (`rows=1`), а их 120000 — статистики по временной таблице нет. Поверив оценке, он выбрал Nested Loop и выполнил внутренний индексный поиск 120000 раз. При верной оценке был бы выбран Hash Join с одним проходом по таблице.

Другие строки, которые встречаются в планах **[офиц.]**:

| Строка | Смысл |
|---|---|
| `Rows Removed by Join Filter` | пары строк, отброшенные условием соединения, которое нельзя было применить через индекс или хеш |
| `Rows Removed by Index Recheck`, `Heap Blocks: exact=… lossy=…` | перепроверка условия в Bitmap Heap Scan; `lossy` — битовая карта не поместилась в `work_mem` и хранит страницы целиком |
| `Heap Fetches: N` | Index Only Scan всё же ходил в таблицу проверять видимость (карта видимости устарела — нужен VACUUM) |
| `Index Searches: N` (18) | число поисков по индексу (например, по одному на элемент `IN (…)`) |
| `Sort Method: quicksort  Memory: 74kB` / `external merge  Disk: 102400kB` / `top-N heapsort` | сортировка в памяти / на диске / частичная для `LIMIT` |
| `Hash … Buckets: 1024  Batches: 1  Memory Usage: 35kB` | `Batches` > 1 — хеш-таблица не поместилась в `work_mem` и разбита на части на диске |
| `Workers Planned / Workers Launched` | параллельные процессы (для 1С параллелизм обычно отключён: `max_parallel_workers_per_gather = 0`) |
| `(never executed)` | узел не выполнялся ни разу |
| `Disabled: true` (18) | узел выбран, несмотря на запрет `enable_… = off` (альтернативы не было) |
| `SubPlan N` / `InitPlan N` | подзапрос, выполняемый на каждую строку внешнего узла / один раз |
| `JIT:` | сработала JIT-компиляция (для 1С рекомендуют `jit = off` — ИТС 5866, приложение K.3 документации Postgres Pro) |
| `Settings: enable_mergejoin = 'off', cpu_operator_cost = '0.001', …` | вывод `SETTINGS` |

Оговорки документации (раздел «Caveats») **[офиц.]**: замер времени сам стоит времени (на системах с медленными часами — значительно; проверка `pg_test_timing`); у узла под `LIMIT` оценка даётся для полного выполнения, а факт меньше — это не ошибка оценки; у Merge Join фактическое число строк внутренней стороны может превышать размер таблицы из-за повторных чтений дубликатов; `BitmapAnd` / `BitmapOr` всегда показывают `rows=0`; план на маленькой таблице нельзя переносить на большую.

### 7.4. Узлы плана

Доступ к данным:

| Узел | Как работает | Хорошо / плохо |
|---|---|---|
| `Seq Scan` | читает таблицу целиком, применяя `Filter` | нормально для маленьких таблиц и когда нужна большая доля строк; плохо — на большой таблице с `Rows Removed by Filter` в миллионы |
| `Index Scan` | идёт по индексу (`Index Cond`), за каждой строкой ходит в таблицу | лучший вариант для выборки малой доли строк; плохо, когда отбор фактически делает `Filter`, а не `Index Cond` |
| `Index Only Scan` | берёт данные только из индекса | быстро при свежей карте видимости (`Heap Fetches: 0`) |
| `Bitmap Index Scan` → `Bitmap Heap Scan` | по индексу строит карту страниц, затем читает страницы по порядку; карты нескольких индексов объединяются `BitmapAnd` / `BitmapOr` | средняя доля строк; условия с `OR` и `IN`; следите за `lossy` |
| `Function Scan`, `Values Scan`, `Result` | результат функции / списка `VALUES` / константы | |
| `CTE Scan`, `Subquery Scan` | чтение результата `WITH` / подзапроса | CTE с 12-й версии встраивается в запрос, если используется один раз и без `MATERIALIZED` |

Соединения:

| Узел | Как работает | Когда выбирается | Типичная беда |
|---|---|---|---|
| `Nested Loop` | для каждой строки внешнего набора выполняет внутренний узел | мало строк во внешнем наборе и есть индекс для внутреннего | оценка «1 строка» при факте в тысячи → внутренний узел выполняется тысячи раз (`loops`) |
| `Hash Join` (+ `Hash`) | строит хеш-таблицу по меньшему набору, затем один раз проходит больший | большие наборы, условие-равенство | хеш не помещается в `work_mem` (`Batches` > 1), временные файлы |
| `Merge Join` | сливает два отсортированных набора | оба входа уже отсортированы или дёшево сортируются | платформа 1С отключает его (`enable_mergejoin = off`), в планах 1С встречаться не должен |
| `… Semi Join`, `… Anti Join` | разновидности для `EXISTS` / `IN (подзапрос)` и `NOT EXISTS` | | |

Прочее:

| Узел | Смысл |
|---|---|
| `Sort`, `Incremental Sort` | сортировка (полная / с использованием уже отсортированного префикса); на диске — `external merge` |
| `HashAggregate` | группировка через хеш-таблицу (не требует сортировки; при нехватке `work_mem` с 13-й версии сбрасывается на диск: `Disk Usage`, `Batches`) |
| `GroupAggregate` | группировка по отсортированному входу |
| `Unique`, `WindowAgg`, `SetOp` | устранение дублей, оконные функции, `INTERSECT` / `EXCEPT` |
| `Materialize` | запоминает результат дочернего узла для повторного чтения (внутренняя сторона Nested Loop) |
| `Memoize` (14+) | кеширует результаты внутреннего узла Nested Loop по значению ключа |
| `Append` / `Merge Append` | объединение (`UNION ALL`, секции) |
| `Limit` | обрезает результат (`ПЕРВЫЕ N`) — дочерний узел может быть остановлен досрочно |
| `Gather`, `Gather Merge` | сбор результатов параллельных процессов |
| `ModifyTable` (`Insert`, `Update`, `Delete`) | изменение данных |

### 7.5. Оценка против факта

Главная причина плохих планов — ошибка оценки числа строк. Порядок действий:

1. Найти самый нижний узел, где оценка и факт расходятся на порядок и более (сравнивать `rows` оценки с `rows × loops` факта — с поправкой на то, что `rows` факта дан за один проход).
2. Понять, откуда оценка:
   - нет или устарела статистика (`pg_stat_user_tables.last_analyze`, `n_mod_since_analyze`; для временных таблиц — её нет вовсе без явного `ANALYZE`);
   - условие по нескольким связанным столбцам — планировщик перемножает селективности как независимые и занижает результат;
   - выражение или функция над столбцом — оценка «по умолчанию»;
   - неравномерное распределение значений, не отражённое в статистике (мало корзин гистограммы: `default_statistics_target = 100`).
3. Исправить источник, а не следствие: `ANALYZE имя_таблицы;`, увеличение точности статистики столбца, изменение текста запроса.

```sql
-- что планировщик знает о таблице и столбце
SELECT relname, reltuples::bigint AS rows_est, relpages FROM pg_class WHERE relname = '_inforg12345';
SELECT attname, null_frac, n_distinct, most_common_vals::text, most_common_freqs
FROM pg_stats WHERE tablename = '_inforg12345' AND attname = '_fld12346rref';

ANALYZE VERBOSE _inforg12345;                                             -- обновить статистику таблицы
ALTER TABLE _inforg12345 ALTER COLUMN _fld12346rref SET STATISTICS 1000;  -- точнее гистограмма столбца, затем ANALYZE
```

Ручные настройки на таблицах 1С (`SET STATISTICS`, `CREATE STATISTICS`, собственные индексы) живут до ближайшей реструктуризации этой таблицы: платформа пересоздаёт таблицу, и настройки пропадают **[практика]**.

### 7.6. Типовые патологии в запросах 1С

| Патология | Как выглядит в плане | Причина | Что делать |
|---|---|---|---|
| Nested Loop по временной таблице без статистики | `Seq Scan on tt… (rows=1 …) (actual … rows=десятки тысяч)`, над ним `Nested Loop`, у внутреннего узла `loops=` десятки тысяч | автоочистка не анализирует временные таблицы; без `ANALYZE` планировщик считает таблицу почти пустой | убедиться, что статистика собирается: современные версии платформы сами выполняют `ANALYZE` временных таблиц (⚠ не подтверждено: с какой именно версии), для старых — модуль `online_analyze` (Postgres Pro для современных версий 1С его **не** рекомендует); `plantuner.fix_empty_table = on`; в запросе 1С — индексировать временную таблицу по полям соединения |
| Неверная оценка кардинальности на постоянных таблицах | оценка `rows=1`–`10`, факт — тысячи; выбран Nested Loop / Index Scan вместо Hash Join / Seq Scan | устаревшая статистика на большой таблице (порог автоанализа — доля от размера), условия по связанным столбцам, поля составного типа (условие на три столбца `_TYPE`, `_RTRef`, `_RRRef` перемножает селективности) | `ANALYZE`; снизить `autovacuum_analyze_scale_factor` для больших таблиц; в запросе 1С — `ВЫРАЗИТЬ(… КАК Тип)`, отказ от составного типа в условиях соединения |
| Условия с `ИЛИ` | `Seq Scan` с `Filter: (… OR …)`; либо `BitmapOr`; при `OR` в условии соединения — `Nested Loop` с `Join Filter` и огромным `Rows Removed by Join Filter` | `OR` по разным столбцам (и тем более по столбцам разных таблиц) не позволяет использовать один индекс | переписать запрос 1С на `ОБЪЕДИНИТЬ ВСЕ` из двух запросов с простыми условиями |
| Соединение с виртуальной таблицей или подзапросом | `Subquery Scan` / `HashAggregate` / `Append` внутри `Nested Loop` с большим `loops`; либо полный расчёт подзапроса по всей таблице, а отбор — после | виртуальная таблица (Остатки, Обороты, СрезПоследних) разворачивается в подзапрос с группировкой и `UNION ALL`; планировщик не умеет протолкнуть в него условие соединения и плохо оценивает число строк | условия передавать **в параметры** виртуальной таблицы; результат подзапроса или виртуальной таблицы сначала поместить во временную таблицу (с индексом), потом соединять — рекомендация ИТС 4208 для СрезПоследних |
| Большие списки `В (…)` | `Index Cond: (… = ANY ('{…}'::bytea[]))` с тысячами элементов; большое `Planning Time`; для `НЕ В` — `Filter` и `Seq Scan` | значения списка передаются литералами в тексте запроса | передавать список через временную таблицу и соединение; `НЕ В (подзапрос)` заменять на левое соединение с проверкой на `NULL` |
| `НЕ В (ВЫБРАТЬ …)` | до 16: `Filter: (NOT (SubPlan 1))` вместо `(NOT (hashed SubPlan 1))`; с 17: `Filter: (NOT (ANY (поле = (SubPlan 1).col1)))` вместо `… (hashed SubPlan 1).col1 …` (сверено 19.10.2026 с замечаниями к выпуску 17 и регрессионными тестами `subselect.out` веток REL_16/17/18); `SubPlan` с `loops` = числу строк | результат подзапроса не поместился в `work_mem`, и он выполняется для каждой строки | переписать на соединение / `NOT EXISTS`; увеличить `work_mem` |
| `ПЕРВЫЕ N` + `УПОРЯДОЧИТЬ ПО` | `Limit` → `Index Scan` по индексу сортировки с `Filter` и `Rows Removed by Filter` в миллионы | планировщик решил, что нужные строки встретятся быстро, а они редкие (типично для динамических списков с отборами) | индекс, покрывающий и отбор, и сортировку (свойство «Индексировать» у реквизита); пересмотреть отборы списка |
| Сортировка или хеш на диске | `Sort Method: external merge  Disk: …kB`; `Batches` > 1; `Buffers: temp read/written` | не хватило `work_mem` | поднять `work_mem` (осторожно: это лимит на **узел плана** в каждом соединении); убрать лишнюю сортировку; сократить выборку |
| Условие не попало в индекс | `Filter` вместо `Index Cond`, большой `Rows Removed by Filter` | функция или выражение над полем (`ПОДСТРОКА`, `НАЧАЛОПЕРИОДА`, арифметика), `ПОДОБНО "%…"`, порядок полей в индексе не соответствует условию, сравнение значений разных типов | сравнивать «чистое» поле с параметром; вынести вычисление на сторону параметра |
| Долгое планирование | `Planning Time` сопоставимо с `Execution Time` или больше | десятки соединений (`join_collapse_limit`, `from_collapse_limit`, GEQO), огромные списки, раздутые системные каталоги (`pg_class`, `pg_attribute`, `pg_statistic` — из-за постоянного создания временных таблиц) | проверить размер и раздувание каталогов (Q-44), обслуживать их; упрощать запрос |
| Обход ограничений RLS | в тексте запроса — многоэтажные подзапросы с `EXISTS` / `OR`, в плане — `SubPlan` с большим `loops` | шаблоны ограничения доступа на уровне записей 1С добавляются к каждому запросу | проверить запрос под пользователем с полными правами; оптимизировать шаблоны RLS, перейти на производительный вариант ограничений в БСП |

Эксперименты в сеансе `psql` (ничего не меняют на сервере, только показывают, какой план был бы лучше):

```sql
SET enable_nestloop = off;        -- запретить Nested Loop: если запрос ускорился на порядки — проблема в оценке строк
SET work_mem = '256MB';           -- исчезнет ли сортировка / хеш на диске
SET random_page_cost = 1.1;       -- как повлияет стоимость случайного чтения (SSD)
EXPLAIN (ANALYZE, BUFFERS) ...;
RESET ALL;                        -- вернуть умолчания сеанса (затем заново выполнить SET-ы платформы)
```

Глобально отключать `enable_nestloop` для сервера 1С нельзя — это ломает быстрые запросы. Точечные подсказки возможны через расширение `pg_hint_plan` (в документации Postgres Pro Standard 17 для 1С, приложение K.4.6: `pg_hint_plan.hints_anywhere = on`, подсказка в комментарии `/*+ … */`). В бесплатную сборку «PostgreSQL для 1С» 16.14 `pg_hint_plan` не входит: его нет ни в перечне модулей приложения F, ни в приложении K.4 её документации (сверено 19.10.2026).

### 7.7. Визуализация планов

- https://explain.depesz.com — раскраска «горячих» узлов, расчёт собственного времени узла;
- https://explain.dalibo.com (PEV2) — дерево; есть вариант в виде одного локального HTML-файла;
- https://explain.tensor.ru — на русском, с подсказками по узлам.

План и текст запроса раскрывают структуру данных (а с литералами — и сами данные). Для чувствительных баз используйте локальный PEV2 или анонимизацию **[практика]**. Для этих сервисов удобен формат `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` или обычный текстовый.

## 8. Таблицы базы данных и объекты метаданных 1С

В SQL-запросах платформы нет имён «Справочник.Номенклатура» — только `_Reference123`, `_Fld4567RRef`. Чтобы понять план, имена нужно перевести.

### 8.1. Имена таблиц

Структура имён описана в статье ИТС «Размещение данных 1С:Предприятия 8. Таблицы и поля» (конспект — `kb/its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`) **[офиц.]**. В PostgreSQL идентификаторы без кавычек приводятся к нижнему регистру, поэтому в планах и системных каталогах видно `_reference123`, `_fld4567rref`.

| Таблица | Объект метаданных |
|---|---|
| `_Const<n>` | константа |
| `_Reference<n>` | справочник |
| `_Document<n>` | документ |
| `<таблица>_VT<k>` | табличная часть объекта (`_Document123_VT456`) |
| `_DocumentJournal<n>` | журнал документов |
| `_Enum<n>` | перечисление |
| `_Chrc<n>` | план видов характеристик |
| `_Acc<n>`, `_Acc<n>_ExtDim<k>` | план счетов и виды субконто |
| `_CKind<n>` | план видов расчёта |
| `_Node<n>` | план обмена |
| `_InfoRg<n>` | регистр сведений; `_InfoRgSL<n>` / `_InfoRgSF<n>` — итоги «срез последних» / «срез первых» |
| `_AccumRg<n>` | движения регистра накопления; `_AccumRgT<n>` — итоги (остатки); `_AccumRgTn<n>` — итоги (обороты); `_AccumRgAgg…` — агрегаты |
| `_AccRg<n>` | движения регистра бухгалтерии; `_AccntRegED<n>` — значения субконто; `_AccRgAT<k><n>` — итоги по счёту; `_AccRgCT<n>` — итоги оборотов между счетами |
| `_CRg<n>` | регистр расчёта; `_CRgActPer<n>`, `_CRgRecalc<n>` |
| `_Seq<n>`, `_SeqB<n>` | последовательность документов и её границы |
| `_BPr<n>`, `_BPrPoints<n>`, `_Task<n>` | бизнес-процесс, точки маршрута, задача |
| `…ChngR<n>`, `_ConstsChngR` | таблицы регистрации изменений (планы обмена) |
| `_ScheduledJobs` | регламентные задания |
| `Config`, `ConfigSave`, `ConfigCAS`, `Params`, `Files`, `DBSchema`, `_YearOffset`, `v8users` и др. | служебные таблицы платформы (конфигурация, параметры, пользователи) |
| `tt<N>` в схеме `pg_temp` (`pg_temp_<M>`) | временные таблицы запросов 1С |

### 8.2. Имена полей

| Поле | Смысл |
|---|---|
| `_IDRRef` | ссылка (первичный идентификатор объекта), 16 байт `bytea` |
| `_Version` | версия записи объекта |
| `_Marked` | пометка удаления |
| `_Code`, `_Description` | код и наименование |
| `_ParentIDRRef`, `_OwnerIDRRef`, `_Folder` | родитель, владелец, признак группы справочника |
| `_Date_Time`, `_Number`, `_Posted` | дата, номер, признак проведения документа |
| `_Period`, `_Recorder…`, `_LineNo`, `_Active`, `_RecordKind` | период, регистратор, номер строки, активность, вид движения записей регистров |
| `_KeyField` | ключ строки табличной части |
| `_Fld<n>` | реквизит, измерение, ресурс; а также общий реквизит-разделитель (условие вида `T1._Fld2830 = CAST(0 AS NUMERIC)` почти в каждом запросе — это разделитель данных) |
| `_Splitter`, `_DimHash` | разделитель итогов и хеш измерений в таблицах итогов |
| `_Q_000_F_000RRef` | поля временных таблиц запросов (номер запроса пакета, номер поля) |

Суффиксы полей (на ИТС — раздел «Особенности хранения составных типов данных»; здесь — по примерам из ИТС 6011 и общеизвестной практике) **[практика]**:

| Суффикс | Что хранит | Пример |
|---|---|---|
| `RRef` | ссылка единственного типа | `_Fld847RRef`, `_IDRRef` |
| `_TYPE` | вид значения в поле составного типа: `\001` — Неопределено, `\002` — Булево, `\003` — Число, `\004` — Дата, `\005` — Строка, `\010` (0x08) — Ссылка | `_Fld30691_TYPE` |
| `_L`, `_N`, `_T`, `_S` | значение составного типа: булево, число, дата, строка | `_Fld30691_N` |
| `_RTRef` | номер таблицы ссылочного типа (4 байта) в поле составного типа | `'\\000\\000\\003\\371'::bytea` = 0x000003F9 = 1017 → таблица `_Document1017` (если это документ) |
| `_RRRef` | сама ссылка в поле составного типа | `_Fld30691_RRRef` |
| `TRef` + `RRef` | номер таблицы и ссылка для полей вроде регистратора | `_RecorderTRef`, `_RecorderRRef` |

Номер таблицы из `_RTRef`: `SELECT ('x' || '000003F9')::bit(32)::int;` → `1017`. Поиск записи по ссылке из запроса 1С: значение в тексте запроса — escape-запись 16 байт; в `psql` при `standard_conforming_strings = off` условие можно скопировать как есть, а человекочитаемый вид даёт `encode(_idrref, 'hex')`.

Типы данных в PostgreSQL: строки — `mchar` / `mvarchar` (типы из патча 1С, регистронезависимое сравнение), ссылки и двоичные данные — `bytea`, числа — `numeric`, даты — `timestamp`, булево — `boolean`.

Имена индексов также генерирует платформа (в примере ИТС 6011 — `_document1337_s_hpk`); их логический состав описан в статье ИТС «Индексы таблиц базы данных» (конспект — `kb/its-metod/razmeshchenie-dannyh-i-indeksy.md`), физический — смотрите в самой базе:

```sql
\d+ _document1337
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '_document1337';
```

### 8.3. Как получить соответствие в своей базе

Номера `<n>` уникальны для каждой информационной базы и меняются при создании объектов — справочников «на все случаи» не бывает. Соответствие даёт метод глобального контекста `ПолучитьСтруктуруХраненияБазыДанных()` (выполняется на сервере 1С) **[офиц., синтакс-помощник]**:

```bsl
// Параметры: (<ОбъектыМетаданных>, <ИменаБазыДанных>)
//   ОбъектыМетаданных — массив имён или объектов метаданных; не задан — вся конфигурация
//   ИменаБазыДанных   — Истина: имена в терминах СУБД (_Reference123); Ложь (по умолчанию): в терминах SDBL (Reference123)
Структура = ПолучитьСтруктуруХраненияБазыДанных(, Истина);
Для Каждого Стр Из Структура Цикл
    Если НРег(Стр.ИмяТаблицыХранения) = "_accumrg12345" Тогда
        Сообщить(Стр.ИмяТаблицыХранения + " = " + Стр.ИмяТаблицы + " (" + Стр.Назначение + ")");
        Для Каждого Поле Из Стр.Поля Цикл
            Сообщить("    " + Поле.ИмяПоляХранения + " = " + Поле.ИмяПоля);
        КонецЦикла;
        Для Каждого Индекс Из Стр.Индексы Цикл
            Сообщить("    индекс " + Индекс.ИмяИндексаХранения);
        КонецЦикла;
    КонецЕсли;
КонецЦикла;
```

Колонки результата (таблица значений): `ИмяТаблицыХранения`, `ИмяТаблицы` (например `РегистрНакопления.ТоварыНаСкладах`), `Метаданные`, `Назначение` (`Основная`, `ТабличнаяЧасть`, `Итоги`, `Обороты`, `РегистрацияИзменений` …), `Поля` (`ИмяПоляХранения`, `ИмяПоля`, `Метаданные`), `Индексы` (`ИмяИндексаХранения`, `Поля`).

Инструменты **[практика]**:

- любая консоль кода или внешняя обработка «Структура хранения базы данных» (распространены на Infostart; в составе подсистемы «Инструменты разработчика»);
- «Центр управления производительностью» (ЦУП) из «Корпоративного инструментального пакета» 1С — показывает запросы в терминах метаданных и умеет разбирать планы (упомянут в ИТС 6011);
- со стороны PostgreSQL: размер и активность таблицы видны и без расшифровки (запросы Q-17, Q-19) — расшифровывать стоит только лидеров.

Прямое изменение данных и структуры базы 1С средствами СУБД запрещено лицензионным соглашением и ломает целостность; чтение для диагностики допустимо. Собственные объекты (таблицы снимков, вспомогательные функции) создавайте в отдельной базе, например `postgres` **[практика]**.

## 9. Рабочий процесс «найти, почему 1С тормозит»

### 9.1. Схема

```text
Жалоба пользователя (кто, когда, какая операция, всегда или иногда)
   │
   ├─ сейчас «всё стоит» ──► 9.2 Срочная диагностика
   │
   └─ «медленно работает операция» ──► 9.3 Плановый разбор
        1. ТЖ: длинные CALL → чем занято время: DBPOSTGRS / TLOCK / код
        2. DBPOSTGRS: текст запроса, dbpid, Context
        3. pg_stat_statements: вклад запроса в общую нагрузку
        4. EXPLAIN (ANALYZE, BUFFERS): где время, оценка против факта
        5. Исправление: запрос 1С / индекс (метаданные) / статистика / настройка сервера
        6. Проверка: тот же замер после исправления
```

### 9.2. Срочная диагностика: «прямо сейчас всё стоит»

```bash
# 1. Жив ли сервер и не упёрся ли в ресурсы
pg_isready -h localhost -p 5432
uptime; free -h; df -h /var/lib/postgresql /var/log
vmstat 1 5; iostat -xz 1 3

# 2. Что делают бэкенды и чего ждут
sudo -u postgres psql -X -c "SELECT state, wait_event_type, wait_event, count(*) FROM pg_stat_activity WHERE backend_type = 'client backend' GROUP BY 1,2,3 ORDER BY 4 DESC;"
```

| Что видно | Диагноз | Действие |
|---|---|---|
| много `active` с `wait_event_type = 'Lock'` | очередь на блокировке СУБД | дерево блокировок (Q-09) → корень → `rac session list` по `db-proc-info` → пользователь; при необходимости `pg_terminate_backend(корень)` |
| много `active` без ожидания (`wait_event` пуст), процессор занят на 100 % | тяжёлые запросы | Q-03 → самые долгие запросы → `EXPLAIN`; срочно — `pg_cancel_backend` |
| много `active` с `IO: DataFileRead` | упор в диск / холодный кеш / последовательные сканирования больших таблиц | `iostat`, Q-03, Q-17 |
| `LWLock: WALWrite`, `IO: WalSync` (до 16 — `IO: WALSync`) | упор в запись WAL (диск журнала, синхронная фиксация) | диск под `pg_wal`, `synchronous_commit` (для 1С рекомендуют `off` — ИТС 5866, приложение K.3 Postgres Pro; цена — потеря последних зафиксированных транзакций при сбое, целостность не страдает), `commit_delay` |
| почти все `idle`, а пользователи ждут | проблема не в PostgreSQL: управляемые блокировки 1С, сервер 1С, лицензии, сеть | ТЖ (`TLOCK`, `TTIMEOUT`), `rac session list` (`blocked-by-ls`), загрузка `rphost` |
| много `idle in transaction` | сервер 1С держит транзакции и чем-то занят | Q-04 → PID → сеансы 1С; смотреть `rphost` (процессор, память) |
| соединений ≈ `max_connections`, ошибки `too many clients already` | исчерпан лимит соединений | Q-01; найти, кто плодит соединения (число рабочих процессов и сеансов 1С); поднять `max_connections` (перезапуск) |
| ошибки `No space left on device` | закончилось место (`pg_wal`, временные файлы, журнал) | `df -h`; причины роста `pg_wal`: архивация стоит (Q-35), неактивный слот (Q-34) |

Интерактивно то же показывает `pg_activity` (раздел 10.1).

### 9.3. Плановый разбор медленной операции

**Шаг 0. Быстрая оценка: виновата ли СУБД (ИТС 6011).** Собрать «тонкий» ТЖ со всеми событиями без свойств и просуммировать длительности по типам событий:

```xml
<log location="/var/log/1c/tj/all_mini" history="8">
  <event>
    <ne property="Name" value=""/>
  </event>
</log>
```

```bash
cat rphost_*/*.log | awk -F\- '{print $2}' | awk -F\, '{sum[$2]+=$1;} END {for (event in sum) print event" - "sum[event];}'
```

Если сумма по `DBPOSTGRS` больше примерно половины суммы по `CALL` — заниматься запросами; если велика доля `TLOCK` — блокировками 1С; если ни то ни другое — кодом на встроенном языке и сервером 1С.

**Шаг 1. Технологический журнал.** Включить сбор длинных событий (полное описание `logcfg.xml` — в `kb/1c/07-…`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="/var/log/1c/tj/slow" history="24">
    <event>
      <eq property="name" value="DBPOSTGRS"/>
      <ge property="durationus" value="1000000"/>
    </event>
    <event>
      <eq property="name" value="CALL"/>
      <ge property="durationus" value="3000000"/>
    </event>
    <event>
      <eq property="name" value="TLOCK"/>
      <ge property="durationus" value="200000"/>
    </event>
    <event><eq property="name" value="TTIMEOUT"/></event>
    <event><eq property="name" value="TDEADLOCK"/></event>
    <event><eq property="name" value="EXCP"/></event>
    <property name="all"/>
  </log>
</config>
```

`durationus` — микросекунды (`1000000` = 1 с); каталог журнала должен быть доступен на запись пользователю `usr1cv8`; файл кладётся в `/opt/1cv8/conf/logcfg.xml` и подхватывается без перезапуска сервера. Элемент `<plansql/>` на продуктиве не добавлять.

```bash
# топ самых долгих запросов к СУБД (длительность в микросекундах, далее сеанс, пользователь, PID бэкенда)
grep -rh --include='*.log' ',DBPOSTGRS,' /var/log/1c/tj/slow \
  | awk -F'[-,]' '{print $2}' | sort -rn | head
grep -rhoP '^\d+:\d+\.\d+-\d{7,},DBPOSTGRS,.*?SessionID=\d+.*?Usr=[^,]*.*?dbpid=\d+' /var/log/1c/tj/slow | cut -c1-200 | head
```

Из события берём: `Sql` (текст запроса), `dbpid` (PID бэкенда), `Context` (модуль и строка кода 1С), `Usr`, `SessionID`, `Rows` / `RowsAffected`. Готовые конвейеры для группировки по контексту и по тексту запроса — в `kb/linux/02-tekst-i-logi.md`.

**Шаг 2. pg_stat_statements.** Оценить, насколько запрос значим в масштабе сервера: место в топе по `total_exec_time` (раздел 4.4, Q-25…Q-27), число вызовов, чтения с диска, временные файлы. Запрос «10 секунд раз в день» и запрос «50 мс × 2 миллиона раз» требуют разных решений.

**Шаг 3. EXPLAIN.** Получить фактический план (раздел 7.2) и найти:

1. узел с наибольшим собственным временем (`actual time × loops` минус дочерние);
2. узел с наибольшим расхождением оценки и факта;
3. узлы с дисковыми операциями (`temp`, `external merge`, `Batches`);
4. большие `Rows Removed by Filter` / `Rows Removed by Join Filter`.

**Шаг 4. Исправление — по убыванию предпочтительности:**

| Что нашли | Исправление | Кто делает |
|---|---|---|
| плохой текст запроса (виртуальная таблица без параметров, подзапрос в соединении, `ИЛИ`, обращение через точку от поля составного типа, запрос в цикле) | переписать запрос в конфигурации по стандартам разработки 1С | разработчик 1С |
| нет подходящего индекса | свойство «Индексировать» у реквизита, порядок измерений регистра, индексирование временной таблицы в запросе | разработчик 1С |
| устаревшая или отсутствующая статистика | `ANALYZE`; настройка автоанализа для больших таблиц; регламентный пересчёт статистики | администратор СУБД |
| раздувание таблицы или индекса | `VACUUM`, `REINDEX CONCURRENTLY` (см. `kb/postgresql/05-…`) | администратор СУБД |
| не хватает памяти на сортировки и хеши, медленный диск, частые контрольные точки | `work_mem`, `temp_buffers`, `shared_buffers`, `max_wal_size`, `random_page_cost` (см. `kb/postgresql/02-…`) | администратор СУБД |
| длинная транзакция блокирует других | сократить транзакцию, изменить порядок блокировок, включить разделение итогов | разработчик 1С |
| ошибка планировщика, которую не обойти | `pg_hint_plan`, параметры уровня базы (`ALTER DATABASE … SET`), обновление версии PostgreSQL | администратор СУБД |

**Шаг 5. Проверка.** Повторить тот же замер (ТЖ, `pg_stat_statements` после сброса, `EXPLAIN`) и сравнить числа. Отчёты `pg_profile` / `pgpro_pwr` «до» и «после» (`get_diffreport`) дают объективное сравнение по всему серверу.

Если конкретного запроса-виновника нет, а «всё медленно» — собирать профиль ожиданий (Q-06, `pg_wait_sampling`) и смотреть на оборудование (`atop`, `nmon`, `iostat` — ИТС 6011; `kb/linux/06-processy-i-proizvoditelnost.md`). PID самого нагруженного процесса `postgres` из `top` / `atop` сопоставляется с `pg_stat_activity.pid` и `dbpid` ТЖ.

## 10. Инструменты мониторинга

### 10.1. pg_activity — «top» для PostgreSQL

Интерактивная утилита (Python, проект Dalibo): список выполняющихся, ожидающих и блокирующих запросов плюс загрузка процессора, памяти и диска по процессам **[офиц., README проекта]**.

```bash
sudo apt install pg-activity                 # Ubuntu 24.04: 3.4.2; Ubuntu 26.04: 3.6.1 (universe)
sudo -u postgres pg_activity -U postgres     # локально, от пользователя ОС postgres — тогда видны CPU / память / ввод-вывод процессов
pg_activity -h db01 -p 5432 -U monitor -d postgres --no-db-size      # удалённо (системных метрик не будет)
pg_activity -U postgres --min-duration 5 --duration-mode 2           # только запросы дольше 5 с; длительность — по транзакции
```

| Ключ / клавиша | Действие |
|---|---|
| `--duration-mode N` | что считать длительностью: `1` — запрос, `2` — транзакция, `3` — соединение |
| `--min-duration N` | скрыть запросы короче N секунд |
| `--no-db-size` | не считать размер баз (быстрее на больших базах) |
| `--filter dbname:REGEX` | отбор по базе |
| `--refresh N` | период обновления, 0.5–5 с (по умолчанию 2) |
| `F1` / `1`, `F2` / `2`, `F3` / `3` | выполняющиеся / ожидающие / блокирующие запросы |
| `c`, `m`, `r`, `w`, `t` | сортировка по CPU / памяти / чтению / записи / времени |
| `T` | сменить режим длительности |
| `Пробел` | пауза |
| `v` | режим отображения текста запроса |
| стрелки, затем `C` / `K` | выбрать процесс и отменить запрос / завершить соединение |
| `q` | выход |

Для полного набора данных нужен суперпользователь (README проекта; роль с `pg_monitor` даст тексты запросов, но не всё — **[практика]**); без него часть сведений (системные метрики, временные файлы) скрыта. Для «PostgreSQL для 1С» от Postgres Professional сокет лежит в `/tmp`, а `pg_activity` из пакетов Ubuntu ищет его в `/var/run/postgresql` — добавляйте `-h /tmp` (или `-h 127.0.0.1` с паролем).

### 10.2. pgcenter

Консольный инструмент (Go, автор — А. Лесовский) для просмотра статистики PostgreSQL в стиле `top`; только Linux **[офиц., README проекта]**. Подкоманды: `top` (интерактивный просмотр `pg_stat_activity`, `pg_stat_database`, таблиц, индексов, `pg_stat_statements`, репликации, WAL, прогресса операций, плюс системная статистика), `record` и `report` (запись статистики в файл и отчёты по ней — «мониторинг для бедных»), `profile` (профилирование событий ожидания одного бэкенда), `config`. Устанавливается deb-пакетом со страницы релизов проекта (в репозиториях Ubuntu его нет).

```bash
pgcenter top -h 127.0.0.1 -U postgres -d postgres
pgcenter profile -U postgres -d erp -P 12345        # профиль ожиданий бэкенда с PID 12345 (ключи -U и -P подтверждены описанием doc/pgcenter-profile-readme.md проекта, пример оттуда: pgcenter profile -U postgres -P 12345; ключ -d и остальное не подтверждено: точные ключи — pgcenter profile --help)
```

### 10.3. pg_top

Классический «top» для PostgreSQL: `sudo apt install pgtop` (пакет `pgtop` 4.1.3 в Ubuntu 26.04, universe; исполняемый файл — `pg_top`, проект gitlab.com/pg_top/pg_top). Запуск: `sudo -u postgres pg_top` или `pg_top -h хост -p 5432 -U роль -d база`. Показывает процессы PostgreSQL с текущим запросом; из интерфейса можно посмотреть план и блокировки выбранного процесса (список клавиш — `h`). Возможностей меньше, чем у `pg_activity` **[практика]**.

### 10.4. pg_wait_sampling — профиль ожиданий

Расширение Postgres Professional: фоновый процесс с заданным периодом опрашивает состояние всех бэкендов и накапливает историю и профиль событий ожидания — то, что вручную делает скрипт с `pg_stat_activity` раз в 3 секунды, только с периодом 10 мс **[офиц., документация Postgres Pro]**.

Где взять:

| Сборка | Как установить |
|---|---|
| Postgres Pro Standard / Enterprise | входит в состав |
| «PostgreSQL с патчем от 1С» | включено начиная с 17.5-3.1C, 17.4-10.1C, 16.9-16.1C, 16.8-40.1C (ИТС 6032) |
| «PostgreSQL для 1С» от Postgres Professional (бесплатная) | в 16.14 не входит: нет в перечне модулей приложения F документации и в индексе пакетов репозитория (сверено 19.10.2026); пакеты PGDG и Ubuntu собраны под другую сборку и ставятся с `postgresql-NN` / `postgresql-common` — на сервер с `postgrespro-1c-16` их не ставить |
| PGDG (ванильный PostgreSQL) | пакет `postgresql-18-pg-wait-sampling` (в архиве самой Ubuntu по packages.ubuntu.com есть `postgresql-14-pg-wait-sampling` 1.1.3 (22.04), `postgresql-16-pg-wait-sampling` 1.1.5 (24.04) и `postgresql-18-pg-wait-sampling` 1.1.9 (26.04); в репозитории PGDG `noble-pgdg` на 19.10.2026 есть `postgresql-14…18-pg-wait-sampling` 1.1.11 — сверено с индексом `Packages` apt.postgresql.org) |

```ini
# pg_stat_statements должен стоять раньше pg_wait_sampling
shared_preload_libraries = 'pg_stat_statements,pg_wait_sampling'
```

```sql
CREATE EXTENSION pg_wait_sampling;      -- после перезапуска сервера
```

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `pg_wait_sampling.history_size` | `5000` | размер кольцевого буфера истории |
| `pg_wait_sampling.history_period` | `10` (мс) | период опроса для истории |
| `pg_wait_sampling.profile_period` | `10` (мс) | период опроса для профиля |
| `pg_wait_sampling.profile_pid` | `true` | вести профиль по каждому процессу |
| `pg_wait_sampling.profile_queries` | `top` | учитывать идентификатор запроса (`none` / `top` / `all`) |
| `pg_wait_sampling.sample_cpu` | `true` | учитывать процессы, которые ничего не ждут (событие `NULL` — «работает на процессоре») |

Представления: `pg_wait_sampling_current` (текущие ожидания), `pg_wait_sampling_history` (история с меткой времени `ts`), `pg_wait_sampling_profile` (профиль: `pid`, `event_type`, `event`, `queryid`, `count`); функции `pg_wait_sampling_get_current(pid)`, `pg_wait_sampling_reset_profile()`. В свежих версиях Postgres Pro состав столбцов шире (`planid`, `dbid`, `client_addr`, `app_name` и др.).

```sql
-- на что сервер тратит время (число наблюдений × 10 мс ≈ время)
SELECT coalesce(event_type, 'CPU') AS event_type, coalesce(event, '(выполняется)') AS event, sum(count) AS samples
FROM pg_wait_sampling_profile
GROUP BY 1, 2 ORDER BY samples DESC LIMIT 20;

-- какие запросы чего ждут
SELECT p.event_type, p.event, sum(p.count) AS samples, left(s.query, 100) AS query
FROM pg_wait_sampling_profile p
LEFT JOIN (SELECT DISTINCT ON (queryid) queryid, query FROM pg_stat_statements) s USING (queryid)
WHERE p.event IS NOT NULL
GROUP BY 1, 2, 4 ORDER BY samples DESC LIMIT 20;

SELECT pg_wait_sampling_reset_profile();     -- профиль хранится в памяти: периодически сбрасывать (ИТС 6032)
```

### 10.5. pgpro_stats (только Postgres Pro)

Расширение Postgres Pro Standard / Enterprise (в Standard 17 — пакет `pgpro-stats-std-17`), развитие `pg_stat_statements` **[офиц., документация Postgres Pro]**:

- хранит **планы** запросов (`planid`, `plan`) и статистику событий ожидания по каждому запросу (`wait_stats`);
- умеет выборочный сбор (`pgpro_stats.query_sample_rate`), агрегаты по базам, пользователям, приложениям, адресам клиентов (`pgpro_stats_totals`), трассировку сеансов;
- основные представления: `pgpro_stats_statements`, `pgpro_stats_totals`, `pgpro_stats_info`; параметры: `pgpro_stats.max` (5000), `pgpro_stats.track` (`top`), `pgpro_stats.track_planning` (`off`), `pgpro_stats.plan_format` (`text`), `pgpro_stats.profile_period` (10 мс);
- **несовместимо с `pg_stat_statements`**: если указать оба в `shared_preload_libraries`, сервер не запустится. Вместо этого `pgpro_stats` умеет создать совместимые представления `pg_stat_statements` и `pg_stat_kcache`.

Входит ли `pgpro_stats` в бесплатную сборку «Postgres Pro 1С» — Уточнено 11.10.2026: в перечне модулей приложения F документации сборки «для 1С» версий 16.14 и 18.4 (`https://repo.postgrespro.ru/doc/pg1c/…/ru/html/contrib.html`) `pgpro_stats` нет; из средств диагностики там есть `pg_stat_statements`, `auto_explain`, `auto_dump`, `plantuner`, `online_analyze` (на сервере проверьте `SELECT * FROM pg_available_extensions WHERE name = 'pgpro_stats';`).

### 10.6. pg_profile и pgpro_pwr — отчёты о нагрузке за период

Обе разработки (автор — А. Зубков; `pgpro_pwr` — вариант в составе Postgres Pro) делают одно и то же: периодически сохраняют «выборки» статистики (`pg_stat_statements`, `pg_stat_database`, таблицы, индексы, ввод-вывод, ожидания) и строят HTML-отчёт о нагрузке между двумя выборками — аналог AWR в Oracle **[офиц.]**.

| | pg_profile | pgpro_pwr |
|---|---|---|
| Где | открытый проект github.com/zubkov-andrei/pg_profile; последняя версия на 19.10.2026 — 4.16 (2026-09-15); поддерживает PostgreSQL 12–19 (19 — с версии 4.14, 18 — с 4.10) | Postgres Pro Standard / Enterprise, пакет `pgpro-pwr-std-17`; в бесплатную сборку «PostgreSQL для 1С» 16.14 не входит (нет в приложении F) |
| Зависимости | `plpgsql`, `dblink`; `pg_stat_statements` (для статистики операторов); по желанию `pg_stat_kcache` | `dblink`; `pgpro_stats` (предпочтительно) или `pg_stat_statements`; по желанию `pg_wait_sampling`, `pg_stat_kcache` |
| Параметры | те же по смыслу с префиксом `pg_profile.`: `max_sample_age` (7), `max_query_length` (20000), `track_sample_timings` (`off`), `statements_reset` (`on`) — по документации 4.16 | `pgpro_pwr.max` (20 строк в таблицах отчёта), `pgpro_pwr.max_sample_age` (7 дней), `pgpro_pwr.max_query_length` (20000), `pgpro_pwr.track_sample_timings` (`off`), `pgpro_pwr.statements_reset` (`on`) |

Требования к серверу: `track_activities = on`, `track_counts = on`, `track_io_timing = on`, `track_wal_io_timing = on` (14+), `track_functions = all` или `pl`.

Установка `pg_profile` (написан на PL/pgSQL, компиляция не нужна):

```bash
# архив со страницы релизов проекта; каталог расширений: Debian/Ubuntu — /usr/share/postgresql/18/extension
sudo tar xzf pg_profile--4.16.tar.gz --directory /usr/share/postgresql/18/extension
# универсально (README проекта): --directory $(pg_config --sharedir)/extension — pg_config той сборки, в которую ставится расширение
```

```sql
\c postgres
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE SCHEMA profile;
CREATE EXTENSION pg_profile SCHEMA profile;          -- для Postgres Pro: CREATE EXTENSION pgpro_pwr SCHEMA profile;

SELECT * FROM profile.take_sample();                 -- снять выборку вручную
SELECT * FROM profile.show_samples();                -- список выборок с номерами и временем
```

Расписание (crontab пользователя `postgres`, каждые 30 минут — пример из документации):

```bash
*/30 * * * *   psql -c 'SELECT profile.take_sample()' > /dev/null 2>&1
```

(В документации `pgpro_pwr` пример записан как `&> /dev/null`, но cron в Ubuntu выполняет строку через `/bin/sh` (dash), где `&>` не перенаправление: команда уйдёт в фон, а вывод попадёт в письмо cron. Форма `> /dev/null 2>&1` — как в документации `pg_profile` 4.16 — работает в любой оболочке; исправлено 19.10.2026.)

Отчёты:

```bash
# между выборками 480 и 482
psql -Aqtc "SELECT profile.get_report(480,482)" -o report_480_482.html
# за последние сутки
psql -Aqtc "SELECT profile.get_report(tstzrange(now() - interval '1 day', now()))" -o report_last_day.html
# сравнение двух интервалов («до» и «после» изменения)
psql -Aqtc "SELECT profile.get_diffreport(480,482,528,530)" -o diff.html
```

В отчёте: статистика баз (фиксации, откаты, взаимоблокировки, попадания в кеш, временные файлы), ввод-вывод, контрольные точки и WAL, топы операторов по времени, чтениям, временным файлам, WAL; топы таблиц и индексов по сканированиям, изменениям, росту; работа автоочистки; изменения настроек.

Важно: по умолчанию при каждой выборке `pg_stat_statements` **сбрасывается** (параметр `pg_profile.statements_reset` / `pgpro_pwr.statements_reset`, умолчание `on`), поэтому ручные запросы к `pg_stat_statements` показывают данные только с последней выборки. При `statements_reset = off` сброса нет, вытеснение записей отслеживается по `calls`, но потери статистики не исключены (документация pg_profile 4.16 и pgpro_pwr для Postgres Pro 17, сверено 19.10.2026). Значение `pg_stat_statements.max` должно быть таким, чтобы статистика не вытеснялась между выборками.

### 10.7. Zabbix

**Официальные шаблоны Zabbix** **[офиц., zabbix.com/integrations/postgresql]**: «PostgreSQL by Zabbix agent 2» (через загружаемый плагин агента 2), «PostgreSQL by Zabbix agent» (пользовательские параметры с `psql`), «PostgreSQL by ODBC». В документации шаблонов (Zabbix 7.4) указаны проверенные версии PostgreSQL 10–17 (⚠ не подтверждено: работа с PostgreSQL 18 без доработок).

Настройка варианта с агентом 2:

```bash
# пакеты из репозитория Zabbix; плагин PostgreSQL вынесен в отдельный пакет начиная с Zabbix 6.0.10 / 6.2.4 / 6.4
sudo apt install zabbix-agent2 zabbix-agent2-plugin-postgresql
```

```sql
CREATE USER zbx_monitor WITH PASSWORD '<PASSWORD>' INHERIT;
GRANT pg_monitor TO zbx_monitor;
```

```text
# pg_hba.conf (затем: SELECT pg_reload_conf();)
host    all    zbx_monitor    127.0.0.1/32    scram-sha-256
```

В интерфейсе Zabbix: привязать к узлу шаблон «PostgreSQL by Zabbix agent 2» и задать макросы `{$PG.CONNSTRING.AGENT2}` (по умолчанию `tcp://localhost:5432`), `{$PG.USER}` (`zbx_monitor`), `{$PG.PASSWORD}`, `{$PG.DATABASE}` (`postgres`). Для TLS — именованная сессия в файле `/etc/zabbix/zabbix_agent2.d/…conf` (`Plugins.PostgreSQL.Sessions.<имя>.Uri`, `…TLSConnect`).

Что собирает шаблон: соединения по состояниям (`active`, `idle`, `idle in transaction`, `waiting`, всего и в процентах), фоновая запись и контрольные точки, по каждой базе — фиксации, откаты, блоки, строки, временные файлы, взаимоблокировки, конфликты; число и время медленных запросов; репликация (число реплик, отставание); WAL; блокировки; возраст самого старого XID; доступность, время работы, версия.

Триггеры шаблона и пороги по умолчанию (Уточнено 19.10.2026 по README шаблонов Zabbix 7.4 `templates/db/postgresql_agent2` и `templates/db/postgresql_agent`: часть триггеров есть только в шаблоне для агента 1 — это отмечено в таблице):

| Триггер | Порог (макрос) |
|---|---|
| соединений слишком много | > 90 % от `max_connections` в течение 5 минут (`{$PG.CONN_TOTAL_PCT.MAX.WARN}`) |
| медленные запросы | больше 5 запросов (`{$PG.SLOW_QUERIES.MAX.WARN}`) длительностью свыше 30 с (`{$PG.QUERY_ETIME.MAX.WARN}`) |
| взаимоблокировки | > 0 (`{$PG.DEADLOCKS.MAX.WARN}`) |
| конфликты восстановления | > 0 (`{$PG.CONFLICTS.MAX.WARN}`) |
| ошибки контрольных сумм страниц | > 0 |
| возраст самого старого XID | > 18 000 000 (порог жёстко задан в шаблоне агента 2) |
| сервис недоступен / перезапущен / сменилась версия | ping = 0 / время работы < 10 минут / изменилась версия |
| отставание репликации | > 10 минут (`{$PG.REPL_LAG.MAX.WARN}`) — **только шаблон «PostgreSQL by Zabbix agent»**; в шаблоне агента 2 отставание собирается, но триггера нет |
| слишком частые контрольные точки по требованию | > 5 (`{$PG.CHECKPOINTS_REQ.MAX.WARN}`) — **только шаблон агента 1** |
| низкая доля попаданий в кеш | < 90 % (`{$PG.CACHE_HITRATIO.MIN.WARN}`) — **только шаблон агента 1** |

Триггера на длинные транзакции и `idle in transaction` в шаблоне нет — добавляйте свой элемент данных на основе Q-04: пользовательские запросы плагина лежат в каталоге из параметра `Plugins.PostgreSQL.CustomQueriesPath` (Подтверждено 19.10.2026 (README и `postgresql.conf` плагина PostgreSQL, ветка `release/7.4` на git.zabbix.com): верное имя — `Plugins.PostgreSQL.CustomQueriesPath`, умолчания нет; написание `Plugins.Postgres.…` в описании элемента шаблона — опечатка шаблона).

**mamonsu** (Postgres Professional) — активный агент мониторинга PostgreSQL и ОС для Zabbix на Python 3: сам отправляет метрики на сервер Zabbix, использует одно соединение с базой **[офиц., README проекта]**. Заявлена поддержка PostgreSQL 12–18 и Zabbix 4.0–6.4 (⚠ не подтверждено: работа с Zabbix 7.x).

```bash
# репозиторий Postgres Pro для mamonsu: скрипт pgpro-repo-add.sh с repo.postgrespro.ru/mamonsu, затем
sudo apt-get update && sudo apt-get install mamonsu

sudoedit /etc/mamonsu/agent.conf            # секции [zabbix] (client, address), [postgres] (user, password, database, host, port), [system]
mamonsu bootstrap -M mamonsu                # от суперпользователя: создать в базе схему mamonsu со служебными функциями — после этого агенту суперпользователь не нужен
mamonsu export template template.xml        # сформировать шаблон для импорта в Zabbix
sudo systemctl enable --now mamonsu
```

Метрики mamonsu: соединения по состояниям (`pgsql.connections[…]`), контрольные точки и фоновая запись, WAL, архивация (`pgsql.archive_command[count_files_to_archive]`, `[failed_trying_to_archive]`), автоочистка, блокировки по режимам (`pgsql.pg_locks[…]`), события баз (`pgsql.events[deadlocks]`, `[conflicts]`, `[checksum_failures]`), размеры баз и возраст XID по базам (`pgsql.database.max_age[…]`), невалидные индексы, раздутые таблицы, подготовленные транзакции, репликация (`pgsql.replication_lag[sec]`, неактивные слоты), статистика операторов из `pg_stat_statements`, попадания в кеш, аптайм; в Postgres Pro — ещё `pg_wait_sampling`. Встроенные триггеры: больше 2 файлов в очереди архивации; контрольные точки по требованию чаще 12 в час; соединений > 90 % от `max_connections`; невалидные индексы; **самая старая транзакция дольше 18000 с (5 ч)**; возраст самого старого XID среди сеансов > 18 000 000; подготовленная транзакция старше 18000 с; отставание репликации > 300 с; неактивный слот удерживает > 1 ГБ; доля попаданий в кеш < 80 %; перезапуск сервера (аптайм < 600 с); нет ответа 3 минуты (пороги — макросы `plugin_macros` в исходном коде плагинов mamonsu 3.5.18 и `documentation/metrics.md`, сверено 19.10.2026; там же: длинные транзакции mamonsu отслеживает, в отличие от шаблона Zabbix).

Полезные подкоманды: `mamonsu report` (отчёт об оборудовании, ОС и PostgreSQL), `mamonsu tune` (автонастройка `postgresql.conf` — для 1С применять с осторожностью, сверяясь с `kb/postgresql/02-…`).

### 10.8. Prometheus: postgres_exporter и Grafana

`postgres_exporter` (prometheus-community) — экспортёр метрик PostgreSQL; последняя версия 0.20.1 (2026-07-07), порт по умолчанию `9187`, метрики на `/metrics` **[офиц., README и релизы проекта]**.

Уточнено 29.10.2026 (Launchpad): в Ubuntu 24.04 пакет `prometheus-postgres-exporter` — 0.15.0 (выпуск 2023 года, раньше PostgreSQL 17 и 18), пакет `prometheus-node-exporter` — 1.7.0; для PostgreSQL 17–18 брать 0.20.1 с GitHub. Сбор долгих транзакций (`--collector.long_running_transactions`) по умолчанию выключен (`defaultDisabled` в `collector/pg_long_running_transactions.go` v0.20.1); метрики — `pg_long_running_transactions` и `pg_long_running_transactions_oldest_timestamp_seconds`. Если Prometheus стоит на другой ВМ, экспортёр слушает адрес сервера, а не `127.0.0.1`, как в примере ниже; порт закрыть в `ufw` для всех, кроме Prometheus.

```sql
CREATE USER postgres_exporter WITH PASSWORD 'ИзменитеМеня';
GRANT CONNECT ON DATABASE postgres TO postgres_exporter;
GRANT pg_monitor TO postgres_exporter;
```

```ini
# /etc/systemd/system/postgres_exporter.service  (двоичный файл — из релиза на GitHub, положен в /usr/local/bin)
[Unit]
Description=Prometheus exporter for PostgreSQL
After=network-online.target

[Service]
User=postgres_exporter
Environment="DATA_SOURCE_URI=localhost:5432/postgres?sslmode=disable"
Environment="DATA_SOURCE_USER=postgres_exporter"
Environment="DATA_SOURCE_PASS_FILE=/etc/postgres_exporter/password"
ExecStart=/usr/local/bin/postgres_exporter --web.listen-address=127.0.0.1:9187 \
  --collector.stat_statements --collector.long_running_transactions \
  --collector.database_wraparound --collector.stat_checkpointer --collector.postmaster
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin postgres_exporter
sudo install -d -m 750 -o root -g postgres_exporter /etc/postgres_exporter
sudoedit /etc/postgres_exporter/password            # одна строка — пароль роли postgres_exporter
sudo chown root:postgres_exporter /etc/postgres_exporter/password && sudo chmod 640 /etc/postgres_exporter/password
sudo systemctl daemon-reload && sudo systemctl enable --now postgres_exporter
curl -s http://127.0.0.1:9187/metrics | grep -E '^pg_up|^pg_stat_database_deadlocks'
```

Коллекторы:

| Включены по умолчанию | Выключены по умолчанию (включаются ключом `--collector.имя`) |
|---|---|
| `database`, `locks`, `replication`, `replication_slots`, `settings`, `stat_activity`, `stat_archiver`, `stat_bgwriter`, `stat_database`, `stat_progress_vacuum`, `stat_replication`, `stat_user_tables`, `statio_user_tables`, `wal` | `database_wraparound`, `long_running_transactions`, `postmaster`, `process_idle`, `stat_activity_autovacuum`, `stat_checkpointer`, `stat_statements` (с текстом запроса — `--collector.stat_statements.include_query`), `stat_wal_receiver`, `statio_user_indexes`, `xlog_location` |

Замечания: пользовательские запросы через `--extend.query-path` (`queries.yaml`) объявлены устаревшими — для произвольных SQL-метрик проект рекомендует `sql_exporter`; в 0.20.0 коллектор `replication_slot` переименован в `replication_slots`, удалён ключ `--disable-settings-metrics`. Один экспортёр может опрашивать несколько серверов через `/probe?target=хост:5432`.

Примеры правил оповещения (имена метрик сверяйте по `/metrics` своей версии — **[практика]**):

```yaml
groups:
  - name: postgresql
    rules:
      - alert: PostgresDown
        expr: pg_up == 0
        for: 1m
      - alert: PostgresTooManyConnections
        expr: sum(pg_stat_activity_count) / max(pg_settings_max_connections) > 0.85
        for: 5m
      - alert: PostgresDeadlocks
        expr: increase(pg_stat_database_deadlocks{datname="erp"}[10m]) > 0
      - alert: PostgresLongTransaction
        expr: max(pg_stat_activity_max_tx_duration{datname="erp"}) > 3600
        for: 5m
      - alert: PostgresArchiveFailing
        expr: increase(pg_stat_archiver_failed_count[15m]) > 0
      - alert: PostgresReplicationLag
        expr: pg_replication_lag_seconds > 300
        for: 5m
```

Grafana: источник данных Prometheus и готовая панель из каталога grafana.com/grafana/dashboards (для `postgres_exporter` распространена панель «PostgreSQL Database», ID 9628) **[практика]**. Системные метрики (диск, процессор, память) даёт `node_exporter`.

### 10.9. Что обязательно ставить на оповещения

| Что контролировать | Как измерить | Ориентир порога **[практика]** |
|---|---|---|
| Доступность | `pg_isready -h хост -p 5432`; `SELECT 1`; `pg_up` | нет ответа 1–3 минуты |
| Перезапуск сервера | `pg_postmaster_start_time()` | аптайм < 10 минут |
| Число соединений | Q-01 | > 80 % (предупреждение), > 90 % (авария) от `max_connections` |
| Длинные транзакции | Q-04: `max(now() - xact_start)` | > 30–60 минут (исключая известные регламентные операции) |
| `idle in transaction` | Q-04: `now() - state_change` при `state LIKE 'idle in transaction%'` | > 10–15 минут |
| Ожидания блокировок | число бэкендов с `wait_event_type = 'Lock'`; сообщения `still waiting for` в журнале | > 5–10 ожидающих дольше минуты |
| Взаимоблокировки | Δ`pg_stat_database.deadlocks` | любой рост |
| Репликация | Q-33: реплика отсутствует в `pg_stat_replication`; отставание | реплика пропала; отставание > 5–10 минут или > 1 ГБ |
| Слоты репликации | Q-34: `active = false`, объём удерживаемого WAL | неактивен дольше часа; удерживает > 1–10 ГБ |
| Архивация WAL | Q-35: рост `failed_count`, давность `last_archived_time`, число файлов `.ready` | любая ошибка; очередь > 10–50 сегментов; нет архивации > 15–30 минут при активной записи |
| Свободное место | `df` для каталога данных, `pg_wal`, табличных пространств, каталога архива и журналов | < 20 % (предупреждение), < 10 % (авария); отдельно — скорость убывания |
| Возраст XID | Q-41: `age(datfrozenxid)` | > 500 млн (предупреждение), > 1 млрд (авария); сервер перестаёт принимать пишущие транзакции, когда до 2^31 остаётся около 3 млн |
| Резервные копии | давность последней успешной копии (по журналу средства резервного копирования) | старше суток |
| Контрольные точки | доля «по требованию» (Q-29) | > 10–20 % от всех |
| Временные файлы | Δ`temp_bytes` | резкий рост относительно обычного уровня |
| Ошибки в журнале | строки `FATAL`, `PANIC`, `ERROR:  could not …` | любое `PANIC` / `FATAL` (кроме ошибок аутентификации) |
| Ошибки контрольных сумм | `pg_stat_database.checksum_failures` | > 0 |
| Мёртвые строки, автоочистка | Q-20, Q-42 | автоочистка таблицы длится часами; доля мёртвых строк > 20–30 % в крупных таблицах |
| Операционная система | загрузка CPU, iowait, время отклика дисков, подкачка, OOM-killer в `dmesg` / `journalctl -k` | по базовой линии сервера |

## 11. Библиотека диагностических SQL-запросов

Запускать в `psql` от роли с `pg_monitor`; запросы к таблицам и индексам — в базе 1С (`\c erp`), остальные — в любой. Для широких результатов — `\x auto`; повтор каждые N секунд — `\watch N`. Имена столбцов даны для PostgreSQL 16–18, отличия отмечены.

### А. Активность

**Q-01. Соединения: всего, по состояниям, доля от лимита**

```sql
SELECT count(*)                                                             AS total,
       count(*) FILTER (WHERE state = 'active')                             AS active,
       count(*) FILTER (WHERE state = 'idle')                               AS idle,
       count(*) FILTER (WHERE state LIKE 'idle in transaction%')            AS idle_in_xact,
       count(*) FILTER (WHERE wait_event_type = 'Lock')                     AS waiting_lock,
       current_setting('max_connections')::int                              AS max_conn,
       round(100.0 * count(*) / current_setting('max_connections')::int, 1) AS pct
FROM pg_stat_activity
WHERE backend_type = 'client backend';
```

**Q-02. Кто подключён: база, роль, приложение, адрес** (заодно показывает, что 1С пишет в `application_name`)

```sql
SELECT datname, usename, application_name, client_addr,
       count(*)                                 AS conns,
       count(*) FILTER (WHERE state <> 'idle')  AS busy,
       min(backend_start)                       AS oldest_conn
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1, 2, 3, 4
ORDER BY conns DESC;
```

**Q-03. Активные запросы, самые долгие сверху**

```sql
SELECT pid, datname, usename, client_addr,
       now() - query_start AS query_age,
       now() - xact_start  AS xact_age,
       wait_event_type, wait_event, query_id,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200) AS query
FROM pg_stat_activity
WHERE state = 'active' AND pid <> pg_backend_pid() AND backend_type = 'client backend'
ORDER BY query_start
LIMIT 20;
```

**Q-04. Долгие транзакции и `idle in transaction`**

```sql
SELECT pid, datname, usename, state,
       now() - xact_start   AS xact_age,
       now() - state_change AS in_state,
       backend_xid, backend_xmin,
       left(regexp_replace(query, '\s+', ' ', 'g'), 150) AS last_query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND pid <> pg_backend_pid()
  AND now() - xact_start > interval '5 minutes'
ORDER BY xact_start;
```

**Q-05. Кто удерживает горизонт очистки (xmin)**

```sql
SELECT 'backend' AS kind, pid::text AS id, datname AS db, state AS info,
       age(backend_xmin) AS xmin_age, now() - xact_start AS since
FROM pg_stat_activity WHERE backend_xmin IS NOT NULL
UNION ALL
SELECT 'slot', slot_name, database, CASE WHEN active THEN 'active' ELSE 'INACTIVE' END,
       age(coalesce(xmin, catalog_xmin)), NULL
FROM pg_replication_slots WHERE coalesce(xmin, catalog_xmin) IS NOT NULL
UNION ALL
SELECT 'prepared xact', gid, database, owner, age(transaction), now() - prepared
FROM pg_prepared_xacts
UNION ALL
SELECT 'standby feedback', application_name, NULL, state, age(backend_xmin), NULL
FROM pg_stat_replication WHERE backend_xmin IS NOT NULL
ORDER BY xmin_age DESC NULLS LAST
LIMIT 15;
```

**Q-06. Снимок ожиданий** (запускать многократно: `\watch 1`; накопление в файл — скрипты `wait_monitor.sh` из ИТС 6011, см. конспект, раздел 4.11)

```sql
SELECT coalesce(wait_event_type, 'CPU')        AS wait_type,
       coalesce(wait_event, '(выполняется)')   AS wait_event,
       count(*)
FROM pg_stat_activity
WHERE state = 'active' AND pid <> pg_backend_pid() AND backend_type = 'client backend'
GROUP BY 1, 2
ORDER BY 3 DESC;
```

**Q-07. Всё об одном бэкенде**

```sql
SELECT pid, backend_type, datname, usename, application_name, client_addr, client_port,
       backend_start, xact_start, query_start, state_change, state,
       wait_event_type, wait_event, backend_xid, backend_xmin, query_id,
       pg_blocking_pids(pid) AS blocked_by, query
FROM pg_stat_activity
WHERE pid = 12345 \gx
```

### Б. Блокировки

**Q-08. Пары «ждёт → держит»** — первый запрос раздела 3.3.

**Q-09. Дерево блокировок** — второй запрос раздела 3.3.

**Q-10. Неполученные блокировки с длительностью ожидания** (`waitstart` — 14+)

```sql
SELECT l.pid, a.usename, l.locktype, l.mode,
       CASE WHEN l.locktype = 'relation'      THEN l.relation::regclass::text
            WHEN l.locktype = 'transactionid' THEN 'xid ' || l.transactionid::text
            ELSE l.locktype END               AS object,
       now() - l.waitstart                    AS waiting,
       pg_blocking_pids(l.pid)                AS blocked_by,
       left(a.query, 120)                     AS query
FROM pg_locks l
JOIN pg_stat_activity a USING (pid)
WHERE NOT l.granted
ORDER BY l.waitstart NULLS LAST;
```

**Q-11. «Тяжёлые» блокировки таблиц (мешают записи или чтению)**

```sql
SELECT l.pid, l.mode, l.granted, l.relation::regclass AS relation,
       a.state, now() - a.xact_start AS xact_age, left(a.query, 120) AS query
FROM pg_locks l
JOIN pg_stat_activity a USING (pid)
WHERE l.locktype = 'relation'
  AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND l.mode IN ('ShareLock', 'ShareRowExclusiveLock', 'ExclusiveLock', 'AccessExclusiveLock')
ORDER BY l.granted, a.xact_start;
```

**Q-12. Сколько блокировок держит каждый сеанс и заполненность таблицы блокировок**

```sql
SELECT l.pid, count(*) AS locks, count(*) FILTER (WHERE NOT l.fastpath) AS in_shared_table,
       a.state, now() - a.xact_start AS xact_age, left(a.query, 100) AS query
FROM pg_locks l
JOIN pg_stat_activity a USING (pid)
GROUP BY l.pid, a.state, a.xact_start, a.query
ORDER BY locks DESC
LIMIT 10;

-- ёмкость: max_locks_per_transaction × (MaxBackends + max_prepared_transactions), см. 3.2
-- MaxBackends: до 17 — max_connections + autovacuum_max_workers + 1 + max_worker_processes + max_wal_senders;
--              в 18  — max_connections + autovacuum_worker_slots + 2 + max_worker_processes + max_wal_senders
SELECT current_setting('max_locks_per_transaction')::int
       * ( current_setting('max_connections')::int
         + coalesce(current_setting('autovacuum_worker_slots', true)::int + 2,
                    current_setting('autovacuum_max_workers')::int + 1)
         + current_setting('max_worker_processes')::int
         + current_setting('max_wal_senders')::int
         + current_setting('max_prepared_transactions')::int ) AS capacity,
       (SELECT count(*) FROM pg_locks WHERE NOT fastpath) AS used;   -- блокировки в общей таблице (без fast-path)
```

### В. Базы, таблицы, индексы

**Q-13. Время сеансов по базам: сколько работали, сколько простаивали в транзакции** (14+)

```sql
SELECT datname, sessions, sessions_abandoned, sessions_fatal, sessions_killed,
       round(session_time::numeric / 3600000, 1)             AS session_h,
       round(active_time::numeric / 3600000, 1)              AS active_h,
       round(idle_in_transaction_time::numeric / 3600000, 1) AS idle_in_xact_h
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY active_time DESC;
```

Сводка по базе (кеш, откаты, временные файлы, взаимоблокировки) — запрос раздела 6.1.

**Q-14. Размеры баз**

```sql
SELECT datname, pg_size_pretty(pg_database_size(oid)) AS size
FROM pg_database
ORDER BY pg_database_size(oid) DESC;
```

**Q-15. Крупнейшие таблицы: данные, индексы, TOAST**

```sql
SELECT c.oid::regclass                               AS table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       pg_size_pretty(pg_relation_size(c.oid))       AS heap,
       pg_size_pretty(pg_indexes_size(c.oid))        AS indexes,
       pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid) - pg_indexes_size(c.oid)) AS toast_and_maps,
       c.reltuples::bigint                           AS rows_est
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = 'public'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;
```

**Q-16. Крупнейшие индексы и их использование**

```sql
SELECT relname AS table_name, indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size,
       idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

**Q-17. Топ таблиц по последовательным сканированиям**

```sql
SELECT relname, seq_scan, seq_tup_read,
       seq_tup_read / nullif(seq_scan, 0)      AS rows_per_seq_scan,
       idx_scan, n_live_tup,
       pg_size_pretty(pg_relation_size(relid)) AS size
FROM pg_stat_user_tables
WHERE seq_scan > 0 AND pg_relation_size(relid) > 50 * 1024 * 1024
ORDER BY seq_tup_read DESC
LIMIT 20;
```

**Q-18. «Нет индекса?»: последовательных сканирований больше, чем индексных** (вариант запроса из ИТС 6011)

```sql
SELECT relname,
       seq_scan - coalesce(idx_scan, 0) AS too_much_seq,
       CASE WHEN seq_scan - coalesce(idx_scan, 0) > 0 THEN 'Нет индекса?' ELSE 'OK' END AS message,
       pg_size_pretty(pg_relation_size(relid)) AS size,
       seq_scan, coalesce(idx_scan, 0) AS idx_scan
FROM pg_stat_user_tables
WHERE pg_relation_size(relid) > 10 * 1024 * 1024
ORDER BY too_much_seq DESC
LIMIT 20;
```

**Q-19. Самые изменяемые таблицы и доля HOT-обновлений**

```sql
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del,
       round(100.0 * n_tup_hot_upd / nullif(n_tup_upd, 0), 1) AS hot_pct,
       n_live_tup,
       pg_size_pretty(pg_total_relation_size(relid))          AS total_size
FROM pg_stat_user_tables
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
LIMIT 20;
```

**Q-20. Мёртвые строки и давность очистки и анализа**

```sql
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       n_mod_since_analyze,
       greatest(last_vacuum, last_autovacuum)   AS last_vac,
       greatest(last_analyze, last_autoanalyze) AS last_an,
       autovacuum_count, autoanalyze_count
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC
LIMIT 20;
```

**Q-21. Неиспользуемые индексы** (с момента сброса статистики; уникальные исключены)

```sql
SELECT s.relname AS table_name, s.indexrelname AS index_name, s.idx_scan,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0 AND NOT i.indisunique AND NOT i.indisprimary
ORDER BY pg_relation_size(s.indexrelid) DESC
LIMIT 30;
```

**Q-22. Дублирующиеся индексы** (одинаковые таблица, столбцы, классы операторов, выражения и предикат)

```sql
SELECT pg_size_pretty(sum(pg_relation_size(idx))::bigint) AS size,
       (array_agg(idx))[1] AS idx1, (array_agg(idx))[2] AS idx2,
       (array_agg(idx))[3] AS idx3, (array_agg(idx))[4] AS idx4
FROM (SELECT indexrelid::regclass AS idx,
             (indrelid::text || E'\n' || indclass::text || E'\n' || indkey::text || E'\n' ||
              coalesce(indexprs::text, '') || E'\n' || coalesce(indpred::text, '')) AS key
      FROM pg_index) sub
GROUP BY key
HAVING count(*) > 1
ORDER BY sum(pg_relation_size(idx)) DESC;
```

**Q-23. Невалидные индексы** (остаются после прерванного `CREATE INDEX CONCURRENTLY` / `REINDEX CONCURRENTLY`)

```sql
SELECT indexrelid::regclass AS index_name, indrelid::regclass AS table_name
FROM pg_index
WHERE NOT indisvalid;
```

**Q-24. Раздувание таблицы и индекса** (расширение `pgstattuple`; подробно — `kb/postgresql/05-…`)

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT * FROM pgstattuple_approx('_accumrg12345'::regclass);   -- dead_tuple_percent, approx_free_percent
SELECT * FROM pgstatindex('_accumrg12345_1'::regclass);        -- avg_leaf_density (у B-дерева норма около 90), leaf_fragmentation
```

### Г. Запросы (pg_stat_statements)

Основной топ по суммарному времени — раздел 4.4.

**Q-25. Топ по времени ввода-вывода** (нужен `track_io_timing`; до 17-й версии столбцы называются `blk_read_time`, `blk_write_time`)

```sql
SELECT round((shared_blk_read_time + shared_blk_write_time)::numeric / 1000, 1) AS io_s,
       round(total_exec_time::numeric / 1000, 1)                                AS total_s,
       calls, shared_blks_read, shared_blks_written,
       left(regexp_replace(query, '\s+', ' ', 'g'), 150)                        AS query
FROM pg_stat_statements
ORDER BY shared_blk_read_time + shared_blk_write_time DESC
LIMIT 20;
```

**Q-26. Топ по временным файлам и по объёму WAL**

```sql
SELECT calls,
       pg_size_pretty(temp_blks_written * current_setting('block_size')::bigint)                    AS temp_written,
       pg_size_pretty(temp_blks_written * current_setting('block_size')::bigint / nullif(calls, 0)) AS temp_per_call,
       round(mean_exec_time::numeric, 1)                                                            AS mean_ms,
       left(regexp_replace(query, '\s+', ' ', 'g'), 150)                                            AS query
FROM pg_stat_statements
WHERE temp_blks_written > 0
ORDER BY temp_blks_written DESC
LIMIT 20;

SELECT calls, pg_size_pretty(wal_bytes) AS wal, wal_records, wal_fpi,
       left(regexp_replace(query, '\s+', ' ', 'g'), 150) AS query
FROM pg_stat_statements
ORDER BY wal_bytes DESC
LIMIT 20;
```

**Q-27. Топ с объединением дублей 1С** (одинаковые запросы к разным временным таблицам `tt<N>` считаются вместе)

```sql
SELECT round(sum(total_exec_time)::numeric / 1000, 1)                  AS total_s,
       sum(calls)                                                      AS calls,
       count(*)                                                        AS entries,
       round((sum(total_exec_time) / nullif(sum(calls), 0))::numeric, 2) AS mean_ms,
       sum(rows)                                                       AS rows,
       left(regexp_replace(regexp_replace(query, '\mtt\d+\M', 'ttN', 'g'), '\s+', ' ', 'g'), 250) AS query_norm
FROM pg_stat_statements
GROUP BY regexp_replace(regexp_replace(query, '\mtt\d+\M', 'ttN', 'g'), '\s+', ' ', 'g')
ORDER BY sum(total_exec_time) DESC
LIMIT 20;
```

**Q-28. Состояние самого pg_stat_statements** (заполненность и вытеснение)

```sql
SELECT (SELECT count(*) FROM pg_stat_statements)       AS entries,
       current_setting('pg_stat_statements.max')::int  AS max_entries,
       dealloc, stats_reset
FROM pg_stat_statements_info;
```

### Д. Ввод-вывод, WAL, контрольные точки, временные файлы

**Q-29. Контрольные точки и фоновая запись**

```sql
-- PostgreSQL 17+
SELECT num_timed, num_requested,
       round(100.0 * num_requested / nullif(num_timed + num_requested, 0), 1) AS requested_pct,
       round(write_time::numeric / 1000) AS write_s, round(sync_time::numeric / 1000) AS sync_s,
       buffers_written, stats_reset
FROM pg_stat_checkpointer;
SELECT buffers_clean, maxwritten_clean, buffers_alloc, stats_reset FROM pg_stat_bgwriter;

-- PostgreSQL 16 и более ранние (в том числе «PostgreSQL для 1С» 16)
SELECT checkpoints_timed, checkpoints_req,
       round(100.0 * checkpoints_req / nullif(checkpoints_timed + checkpoints_req, 0), 1) AS requested_pct,
       buffers_checkpoint, buffers_clean, maxwritten_clean, buffers_backend, buffers_backend_fsync, buffers_alloc, stats_reset
FROM pg_stat_bgwriter;
```

**Q-30. Объём и скорость генерации WAL; размер каталога pg_wal** (на ведущем сервере)

```sql
SELECT wal_records, wal_fpi, pg_size_pretty(wal_bytes) AS wal_total, wal_buffers_full,
       pg_size_pretty(round(wal_bytes / greatest(extract(epoch FROM now() - stats_reset)::numeric, 1) * 3600)) AS wal_per_hour,
       stats_reset
FROM pg_stat_wal;

SELECT count(*) AS files, pg_size_pretty(sum(size)) AS size FROM pg_ls_waldir();
```

**Q-31. Кто читает и пишет: pg_stat_io** (16+)

```sql
SELECT backend_type, object, context, reads, writes, extends, hits, evictions, fsyncs,
       round(read_time::numeric)  AS read_ms,
       round(write_time::numeric) AS write_ms
FROM pg_stat_io
WHERE coalesce(reads, 0) + coalesce(writes, 0) + coalesce(extends, 0) > 0
ORDER BY coalesce(reads, 0) + coalesce(writes, 0) DESC;
```

**Q-32. Временные файлы на диске прямо сейчас и временные таблицы сеансов**

```sql
-- временные файлы (сортировки, хеши): по процессам
SELECT substring(t.name FROM 'pgsql_tmp(\d+)')::int AS pid,
       count(*) AS files, pg_size_pretty(sum(t.size)) AS size,
       left(max(a.query), 120) AS query
FROM pg_ls_tmpdir() t
LEFT JOIN pg_stat_activity a ON a.pid = substring(t.name FROM 'pgsql_tmp(\d+)')::int
GROUP BY 1
ORDER BY sum(t.size) DESC;

-- временные таблицы (tt<N> запросов 1С) по временным схемам сеансов; выполнять в базе 1С
SELECT n.nspname AS temp_schema, count(*) AS tables,
       pg_size_pretty(sum(pg_total_relation_size(c.oid))) AS size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relpersistence = 't' AND c.relkind = 'r'
GROUP BY 1
ORDER BY sum(pg_total_relation_size(c.oid)) DESC
LIMIT 20;
```

Размер чужих временных таблиц считается по файлам на диске — данные, ещё лежащие в локальных буферах сеанса (`temp_buffers`), не учитываются. Если в сборке включено хранение метаданных временных таблиц в памяти (параметр `enable_temp_memory_catalog` из ИТС 5866), в `pg_class` их может не быть (⚠ не подтверждено).

### Е. Архивация и репликация

**Q-33. Отставание реплик** (на ведущем)

```sql
SELECT application_name, client_addr, state, sync_state,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn))   AS not_sent,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) AS not_replayed,
       write_lag, flush_lag, replay_lag, reply_time
FROM pg_stat_replication;
```

**Q-34. Слоты репликации и удерживаемый ими WAL** (на ведущем)

```sql
SELECT slot_name, slot_type, database, active, wal_status,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal,
       age(xmin) AS xmin_age, age(catalog_xmin) AS catalog_xmin_age
FROM pg_replication_slots
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC NULLS LAST;
```

**Q-35. Архивация WAL: ошибки, давность, очередь**

```sql
SELECT archived_count, failed_count, last_archived_wal, last_archived_time,
       now() - last_archived_time AS since_last_archived,
       last_failed_wal, last_failed_time
FROM pg_stat_archiver;

SELECT count(*) AS ready_to_archive FROM pg_ls_archive_statusdir() WHERE name LIKE '%.ready';
```

**Q-36. Состояние реплики** (выполнять на реплике)

```sql
SELECT pg_is_in_recovery()         AS is_replica,
       pg_last_wal_receive_lsn()   AS received,
       pg_last_wal_replay_lsn()    AS replayed,
       pg_size_pretty(pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn())) AS replay_backlog,
       now() - pg_last_xact_replay_timestamp() AS replay_delay;

SELECT status, sender_host, sender_port, slot_name, latest_end_lsn, last_msg_receipt_time
FROM pg_stat_wal_receiver;
```

`replay_delay` растёт и тогда, когда на ведущем просто нет транзакций, — оценивайте его вместе с `replay_backlog`.

### Ж. Ход длительных операций

**Q-37. VACUUM и автоочистка**

```sql
SELECT p.pid, p.datname, p.relid::regclass AS table_name, p.phase,
       round(100.0 * p.heap_blks_scanned  / nullif(p.heap_blks_total, 0), 1) AS scanned_pct,
       round(100.0 * p.heap_blks_vacuumed / nullif(p.heap_blks_total, 0), 1) AS vacuumed_pct,
       p.index_vacuum_count,
       now() - a.xact_start AS running,
       a.backend_type, left(a.query, 80) AS query
FROM pg_stat_progress_vacuum p
JOIN pg_stat_activity a USING (pid);
```

**Q-38. CREATE INDEX и REINDEX** (в том числе при реструктуризации 1С)

```sql
SELECT p.pid, p.datname, p.relid::regclass AS table_name, p.index_relid::regclass AS index_name,
       p.command, p.phase,
       round(100.0 * p.blocks_done / nullif(p.blocks_total, 0), 1) AS blocks_pct,
       round(100.0 * p.tuples_done / nullif(p.tuples_total, 0), 1) AS tuples_pct,
       p.lockers_done || '/' || p.lockers_total AS lockers, p.current_locker_pid,
       now() - a.query_start AS running
FROM pg_stat_progress_create_index p
JOIN pg_stat_activity a USING (pid);
```

**Q-39. VACUUM FULL и CLUSTER**

```sql
SELECT p.pid, p.datname, p.relid::regclass AS table_name, p.command, p.phase,
       round(100.0 * p.heap_blks_scanned / nullif(p.heap_blks_total, 0), 1) AS scanned_pct,
       p.heap_tuples_scanned, p.heap_tuples_written, p.index_rebuild_count,
       now() - a.query_start AS running
FROM pg_stat_progress_cluster p
JOIN pg_stat_activity a USING (pid);
```

**Q-40. ANALYZE, COPY, базовая резервная копия**

```sql
SELECT pid, datname, relid::regclass AS table_name, phase, sample_blks_scanned, sample_blks_total
FROM pg_stat_progress_analyze;

SELECT pid, datname, relid::regclass AS table_name, command, type,
       pg_size_pretty(bytes_processed) AS done, pg_size_pretty(bytes_total) AS total, tuples_processed
FROM pg_stat_progress_copy;

SELECT pid, phase, pg_size_pretty(backup_streamed) AS streamed, pg_size_pretty(backup_total) AS total,
       round(100.0 * backup_streamed / nullif(backup_total, 0), 1) AS pct
FROM pg_stat_progress_basebackup;
```

Значения `relid::regclass` осмысленны только при подключении к той базе, где идёт операция (столбец `datname`); в другой базе будет показан числовой OID.

### З. Обслуживание и конфигурация

**Q-41. Возраст XID по базам и по таблицам**

```sql
SELECT datname, age(datfrozenxid) AS xid_age, mxid_age(datminmxid) AS mxid_age,
       current_setting('autovacuum_freeze_max_age')::int AS freeze_max_age,
       round(100.0 * age(datfrozenxid) / 2000000000, 1)  AS pct_of_2bn
FROM pg_database
ORDER BY xid_age DESC;

SELECT c.oid::regclass AS table_name, age(c.relfrozenxid) AS xid_age,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS size
FROM pg_class c
WHERE c.relkind IN ('r', 'm', 't')
ORDER BY age(c.relfrozenxid) DESC
LIMIT 15;
```

**Q-42. Что сейчас делает автоочистка**

```sql
SELECT pid, datname, now() - xact_start AS running, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE backend_type = 'autovacuum worker'
ORDER BY xact_start;
```

**Q-43. Изменённые настройки, ожидающие перезапуска, ошибки в файлах, настройки баз и ролей**

```sql
SELECT name, setting, unit, source, sourcefile, sourceline
FROM pg_settings
WHERE source NOT IN ('default', 'override')
ORDER BY name;

SELECT name, setting FROM pg_settings WHERE pending_restart;

SELECT sourcefile, sourceline, name, setting, error FROM pg_file_settings WHERE error IS NOT NULL;

SELECT coalesce(d.datname, '(все базы)') AS db, coalesce(r.rolname, '(все роли)') AS role, s.setconfig
FROM pg_db_role_setting s
LEFT JOIN pg_database d ON d.oid = s.setdatabase
LEFT JOIN pg_roles r    ON r.oid = s.setrole;
```

**Q-44. Системные каталоги: размер и мёртвые строки** (пухнут из-за постоянного создания временных таблиц)

```sql
SELECT c.relname, pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       s.n_live_tup, s.n_dead_tup, s.last_autovacuum
FROM pg_class c
JOIN pg_stat_sys_tables s ON s.relid = c.oid
WHERE c.relnamespace = 'pg_catalog'::regnamespace
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 10;
```

**Q-45. Что лежит в буферном кеше** (расширение `pg_buffercache`; на больших `shared_buffers` запрос сам заметно нагружает сервер)

```sql
CREATE EXTENSION IF NOT EXISTS pg_buffercache;
SELECT * FROM pg_buffercache_summary();          -- 16+: buffers_used, buffers_unused, buffers_dirty, buffers_pinned, usagecount_avg

SELECT c.relname, count(*) AS buffers,
       pg_size_pretty(count(*) * current_setting('block_size')::bigint)       AS cached,
       round(100.0 * count(*) / (SELECT count(*) FROM pg_buffercache), 1)     AS pct_of_cache
FROM pg_buffercache b
JOIN pg_class c ON b.relfilenode = pg_relation_filenode(c.oid)
               AND b.reldatabase IN (0, (SELECT oid FROM pg_database WHERE datname = current_database()))
GROUP BY c.relname
ORDER BY buffers DESC
LIMIT 15;
```

**Q-46. Версия, время работы, время загрузки конфигурации**

```sql
SELECT version();
SELECT pg_postmaster_start_time()         AS started,
       now() - pg_postmaster_start_time() AS uptime,
       pg_conf_load_time()                AS conf_loaded,
       pg_is_in_recovery()                AS is_replica,
       current_setting('data_directory')  AS pgdata;
```

## 12. Типичные ошибки и подводные камни

| Симптом | Причина | Решение |
|---|---|---|
| Пользователи 1С «висят», а в `pg_stat_activity` все соединения `idle` или `idle in transaction`, ожиданий `Lock` нет | ждут не PostgreSQL: управляемая блокировка 1С, загруженный `rphost`, внешний сервис, нехватка лицензий | ТЖ: `TLOCK` с `WaitConnections`, `TTIMEOUT`; `rac session list` — поле `blocked-by-ls`; загрузка процессов сервера 1С |
| Очередь из `active` с `wait_event_type = 'Lock'`, в корне дерева — `idle in transaction` | транзакция 1С открыта и чем-то занята вне СУБД (долгий код, диалог, HTTP-вызов внутри транзакции) | PID корня → `db-proc-info` в `rac` → сеанс и пользователь; срочно — `pg_terminate_backend`; по существу — сократить транзакцию в коде |
| После обновления конфигурации или реструктуризации «встала вся база», ожидания `Lock: relation` | оператор с `AccessExclusiveLock` ждёт длинную транзакцию, а за ним в очереди стоят все остальные | реструктуризацию выполнять без пользователей; найти и завершить мешающую транзакцию (Q-11, дерево блокировок) |
| Запрос в `psql` выполняется быстро, тот же запрос из 1С — медленно (или наоборот) | другие параметры сеанса (платформа ставит `enable_mergejoin = off`, `cpu_operator_cost = 0.001`), другая статистика временных таблиц, тёплый кеш | воспроизводить с параметрами платформы и полной цепочкой временных таблиц (раздел 7.2); брать план из `auto_explain` |
| `EXPLAIN ANALYZE` запроса из ТЖ возвращает `rows=0`, хотя в 1С строки есть | литерал `bytea` разобран при `standard_conforming_strings = on` | `SET standard_conforming_strings = off;` перед запросом (раздел 7.2) |
| В `pg_stat_statements` тысячи почти одинаковых записей, `dealloc` быстро растёт, топ «размазан» | временные таблицы 1С (`tt<N>`, разные OID), списки `IN` разной длины, служебные команды | `pg_stat_statements.max` = 10000–20000, группировка Q-27, `track_utility = off`; PostgreSQL 18 заметно сокращает дубли |
| `ERROR: pg_stat_statements must be loaded via "shared_preload_libraries"` | расширение создано, но библиотека не загружена (или сервер не перезапущен) | добавить в `shared_preload_libraries`, перезапустить |
| Сервер не стартует после правки `shared_preload_libraries` | опечатка в имени, не установлен пакет с модулем, одновременно указаны `pgpro_stats` и `pg_stat_statements` | исправить `postgresql.auto.conf` / файл в `conf.d` вручную; причина — в журнале (`journalctl -u postgresql@18-main`, `/var/log/postgresql/…`) |
| Текст запроса в `pg_stat_activity` обрезан | `track_activity_query_size = 1024` по умолчанию | увеличить до 32768–1048576 (перезапуск) |
| Вместо текста запроса `<insufficient privilege>` | у роли нет `pg_read_all_stats` | `GRANT pg_monitor TO роль;` |
| После включения `auto_explain.log_analyze` сервер заметно замедлился | при `log_analyze` инструментируются все операторы, а не только длинные; дорогой источник времени в виртуальной машине | `auto_explain.log_timing = off`, `sample_rate < 1`, либо `log_analyze = off`; проверить `pg_test_timing` |
| `EXPLAIN ANALYZE` показывает время в разы больше обычного выполнения | накладные расходы замера времени по узлам | `EXPLAIN (ANALYZE, TIMING OFF)`; сменить источник времени ВМ |
| Журнал PostgreSQL занял весь диск | оставлен `log_min_duration_statement = 0`, `log_min_messages = debug*`, `log_statement = 'all'` | вернуть пороги (`ALTER SYSTEM RESET …; SELECT pg_reload_conf();`); вынести журнал на отдельный раздел; настроить ротацию |
| Журнала нет там, где ожидали | включён `logging_collector` (журнал в `…/log` каталога данных) либо, наоборот, выключен (журнал в `/var/log/postgresql/` или journald) | `SHOW logging_collector; SELECT pg_current_logfile(); pg_lsclusters` |
| pgBadger выдаёт пустой или неполный отчёт | `log_line_prefix` без времени и PID или нестандартный; сообщения на русском (`lc_messages = 'ru_RU.UTF-8'`); порог `log_min_duration_statement` слишком высок | ключ `--prefix`; `lc_messages = 'C'`; снизить порог на время сбора |
| Скрипты мониторинга после обновления PostgreSQL падают с `column … does not exist` | переименования и переносы столбцов между версиями (таблица в 1.1) | поправить запросы: `pg_stat_checkpointer` (17+), `shared_blk_read_time` (17+), `pg_stat_io` вместо `buffers_backend` и `wal_write*` |
| Доля попаданий в кеш 99,9 %, а диски загружены | метрика не видит временные файлы, WAL, автоочистку, чтения через кеш ОС | `pg_stat_io`, `temp_bytes`, `pg_stat_wal`, `iostat -xz 1` |
| Счётчики статистики внезапно обнулились | аварийный перезапуск сервера, `pg_stat_reset()`, выборка `pg_profile` (сбрасывает `pg_stat_statements`) | смотреть `stats_reset`; строить метрики на разностях; не вызывать `pg_stat_reset()` без нужды |
| Таблицы растут, автоочистка работает, в её журнале «dead but not yet removable» | горизонт очистки держит длинная транзакция, неактивный слот репликации, подготовленная транзакция, реплика с `hot_standby_feedback` | Q-05; завершить транзакцию, удалить ненужный слот (`pg_drop_replication_slot`), `ROLLBACK PREPARED` |
| Каталог `pg_wal` растёт без остановки | не работает архивация, неактивный слот, реплика отстала | Q-34, Q-35; починить `archive_command`; удалить брошенный слот |
| Удалили «неиспользуемый» индекс в базе 1С — запросы замедлились или индекс вернулся | индексы таблиц 1С создаёт платформа по метаданным | не менять структуру базы 1С вручную; лишние индексы убирать через конфигурацию |
| `ERROR: out of shared memory`, HINT про `max_locks_per_transaction` | переполнена таблица блокировок (много временных таблиц и объектов в одной транзакции) | увеличить `max_locks_per_transaction` (256 и больше; перезапуск), Q-12 |
| После `kill -9` процесса `postgres` отвалились все пользователи | аварийное завершение бэкенда вызывает перезапуск всех процессов и восстановление по WAL | только `pg_cancel_backend()` / `pg_terminate_backend()` |
| `pg_cancel_backend()` вернул `true`, но запрос продолжается | бэкенд ждёт клиента (`ClientWrite`) или находится в непрерываемом участке | подождать; затем `pg_terminate_backend()`; проверить сеть и `rphost` |
| В `rac session list` поле `db-proc-info` пустое у «подозреваемого» сеанса | в момент опроса сеанс не удерживал соединение с СУБД | опрашивать несколько раз; использовать ТЖ (`dbpid`) |
| Мониторинг сам создаёт нагрузку | частый опрос `pg_locks` и `pg_blocking_pids()`, `pg_stat_statements` с текстами, `pg_buffercache`, функций размера | интервал опроса 30–60 с; тексты запросов не тянуть (`pg_stat_statements(false)`); тяжёлые запросы — раз в час |
| Ровно через 20 секунд ожидания пользователь получает «Конфликт блокировок…» | сработал `lock_timeout = 20000`, выставленный платформой (или таймаут управляемой блокировки) | искать, кто держал блокировку (`log_lock_waits`, ТЖ), а не увеличивать таймаут |

## 13. Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Жив ли сервер | `pg_isready -h localhost -p 5432` |
| Кластеры, порты, журналы (Ubuntu) | `pg_lsclusters` |
| Что происходит сейчас | `sudo -u postgres pg_activity -U postgres` |
| Соединения по состояниям | `SELECT state, count(*) FROM pg_stat_activity WHERE backend_type='client backend' GROUP BY 1;` |
| Самые долгие активные запросы | Q-03 |
| Долгие транзакции, `idle in transaction` | Q-04 |
| Чего ждут бэкенды | Q-06, затем `\watch 1` |
| Кто блокирует процесс 12345 | `SELECT pg_blocking_pids(12345);` |
| Дерево блокировок | раздел 3.3 (Q-09) |
| Отменить запрос / завершить соединение | `SELECT pg_cancel_backend(12345);` / `SELECT pg_terminate_backend(12345);` |
| Найти сеанс 1С по PID бэкенда | `rac session list --cluster=$CL` → поле `db-proc-info` (раздел 2.5) |
| Найти бэкенд по событию ТЖ | свойство `dbpid=` события `DBPOSTGRS` → `WHERE pid = …`; `grep -F '[PID]'` по журналу PostgreSQL |
| Включить журнал ожиданий блокировок | `ALTER SYSTEM SET log_lock_waits = on; SELECT pg_reload_conf();` |
| Журналировать запросы дольше 5 с | `ALTER SYSTEM SET log_min_duration_statement = '5s'; SELECT pg_reload_conf();` |
| Где журнал | `SELECT pg_current_logfile();` или `/var/log/postgresql/postgresql-18-main.log` |
| Подключить `pg_stat_statements` | `shared_preload_libraries` += `pg_stat_statements` → перезапуск → `CREATE EXTENSION pg_stat_statements;` |
| Топ запросов по суммарному времени | раздел 4.4; с учётом временных таблиц 1С — Q-27 |
| Сбросить статистику запросов | `SELECT pg_stat_statements_reset();` |
| Планы длинных запросов в журнал | `auto_explain.log_min_duration = '10s'` (раздел 5.5) |
| План конкретного запроса | `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS) …` с параметрами платформы (раздел 7.2) |
| План изменяющего запроса без изменений | `BEGIN; EXPLAIN (ANALYZE, BUFFERS) …; ROLLBACK;` |
| Отчёт по журналу | `pgbadger -j 4 /var/log/postgresql/postgresql-18-main.log -o report.html` |
| Сводка по базе (кеш, откаты, временные файлы, взаимоблокировки) | запрос раздела 6.1 |
| Таблицы с последовательными сканированиями | Q-17, Q-18 |
| Крупнейшие таблицы и индексы | Q-15, Q-16 |
| Неиспользуемые / дублирующиеся / невалидные индексы | Q-21 / Q-22 / Q-23 |
| Мёртвые строки, давность очистки | Q-20 |
| Кто держит горизонт очистки | Q-05 |
| Ход VACUUM / CREATE INDEX / VACUUM FULL | Q-37 / Q-38 / Q-39 |
| Контрольные точки | Q-29 |
| Скорость генерации WAL, размер `pg_wal` | Q-30 |
| Архивация WAL | Q-35 |
| Репликация: отставание, слоты | Q-33, Q-34 (на реплике — Q-36) |
| Возраст XID | Q-41 |
| Временные файлы и временные таблицы | Q-32 |
| Изменённые настройки, ожидающие перезапуска | Q-43 |
| Что за таблица `_AccumRg12345` | `ПолучитьСтруктуруХраненияБазыДанных(, Истина)` (раздел 8.3) |
| Отчёт о нагрузке за период | `psql -Aqtc "SELECT profile.get_report(480,482)" -o report.html` (pg_profile / pgpro_pwr) |
| Профиль ожиданий | `SELECT event_type, event, sum(count) FROM pg_wait_sampling_profile GROUP BY 1,2 ORDER BY 3 DESC;` |
| Доля времени СУБД в работе 1С | сумма длительностей `DBPOSTGRS` / сумма `CALL` в ТЖ (раздел 9.3, шаг 0) |
| Справочник событий ожидания (17+) | `SELECT * FROM pg_wait_events WHERE type = 'Lock';` |
| Проверка цены замера времени | `/usr/lib/postgresql/18/bin/pg_test_timing` |

## 14. Источники

Веб-поиск в сессии подготовки статьи был недоступен (исчерпан лимит); источники читались напрямую по известным адресам 2026-10-10. Сведения, которые не удалось сверить, помечены в тексте «⚠ не подтверждено».

PostgreSQL (официальная документация, версия 18.6):

- https://www.postgresql.org/ — актуальные версии (18.6, 17.11, 16.15, 15.19, 14.24 от 2026-08-13; 19 Beta 4 от 2026-09-24; окончание поддержки 14 — 2026-11-12).
- https://www.postgresql.org/docs/current/monitoring-stats.html — `pg_stat_activity`, типы и события ожидания, `pg_stat_database`, `pg_stat_all_tables`, `pg_stat_all_indexes`, `pg_statio_*`, `pg_stat_bgwriter`, `pg_stat_checkpointer`, `pg_stat_wal`, `pg_stat_io`, `pg_stat_archiver`, `pg_stat_replication`, функции сброса статистики.
- https://www.postgresql.org/docs/current/progress-reporting.html — представления `pg_stat_progress_*`, фазы операций.
- https://www.postgresql.org/docs/current/view-pg-locks.html — `pg_locks`, рекомендация использовать `pg_blocking_pids()`.
- https://www.postgresql.org/docs/current/explicit-locking.html — режимы блокировок и таблица их совместимости.
- https://www.postgresql.org/docs/current/runtime-config-locks.html — `deadlock_timeout`, `max_locks_per_transaction`.
- https://www.postgresql.org/docs/current/runtime-config-logging.html — параметры журналирования, `log_line_prefix`, `log_connections` в 18.
- https://www.postgresql.org/docs/current/runtime-config-statistics.html — `track_*`, `compute_query_id`.
- https://www.postgresql.org/docs/current/pgstatstatements.html — столбцы, параметры, функции, нормализация, свёртка списков `IN`.
- https://www.postgresql.org/docs/current/auto-explain.html — параметры `auto_explain`, предупреждения о накладных расходах.
- https://www.postgresql.org/docs/current/sql-explain.html и https://www.postgresql.org/docs/current/using-explain.html — параметры `EXPLAIN`, чтение плана, оговорки.
- https://www.postgresql.org/docs/18/release-18.html и https://www.postgresql.org/docs/17/release-17.html — изменения представлений статистики, `pg_stat_statements`, `EXPLAIN`, журналирования.
- https://wiki.postgresql.org/wiki/Lock_Monitoring — запросы по блокировкам, совет про `log_lock_waits`.

1С (ИТС, методические материалы и документация платформы):

- https://its.1c.ru/db/metod8dev/content/6011/hdoc — «Методика расследования проблем производительности на уровне работы СУБД PostgreSQL» (21.02.2023): оценка `DBPOSTGRS` / `CALL`, параметры сеанса платформы, воспроизведение запросов с временными таблицами, `auto_explain`, `pg_stat_statements`, опрос ожиданий, `dbpid`. Конспект: `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`.
- https://its.1c.ru/db/metod8dev/content/6006/hdoc — «Методика расследования ошибок блокировок» (16.11.2022): поиск по `TLOCK` и `WaitConnections`, запросы к `pg_locks`, настройки журнала PostgreSQL и `log_line_prefix`, pgBadger, позиция разработчиков о блокировках PostgreSQL в управляемом режиме. Конспект: `kb/its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`.
- https://its.1c.ru/db/metod8dev/content/6032/hdoc и https://its.1c.ru/db/metod8dev/content/6039/hdoc — `pg_wait_sampling` и `auto_dump` 1.1 в сборках PostgreSQL с патчем 1С (по конспекту базы знаний).
- https://its.1c.ru/db/metod8dev/content/5866/hdoc — «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2» (19.06.2025): `max_locks_per_transaction`, `standard_conforming_strings`, `online_analyze`, параметры фоновой записи.
- https://its.1c.ru/db/metod8dev/content/1798/hdoc — «Размещение данных 1С:Предприятия 8. Таблицы и поля» (27.05.2025): имена таблиц и полей. https://its.1c.ru/db/metod8dev/content/1590/hdoc — «Индексы таблиц базы данных».
- Документация платформы (ИТС, раздел закрыт подпиской; использованы конспекты `kb/its-docs/…`): технологический журнал — события `DBPOSTGRS`, `TLOCK`, `TTIMEOUT`, `TDEADLOCK`, свойства `Dbpid`, `planSQLText`, элементы `<plansql>`, `<dbmslocks>`; консоль кластера — свойства сеанса «Соединение с СУБД», «Захвачено СУБД», «Заблокировано СУБД», «Заблокировано упр.».

Postgres Professional:

- https://postgrespro.ru/docs/postgrespro/17/config-one-c (приложение «Настройка Postgres Pro для решений 1С»), https://postgrespro.ru/docs/postgrespro/17/one-c-configuring-server, https://postgrespro.ru/docs/postgrespro/17/one-c-additional-modules — рекомендуемые параметры, `plantuner`, `online_analyze` (не рекомендуется для современных версий 1С), `pg_hint_plan`.
- https://postgrespro.ru/docs/postgrespro/17/pg-wait-sampling — установка, представления, параметры `pg_wait_sampling`.
- https://postgrespro.ru/docs/postgrespro/17/pgpro-stats — `pgpro_stats`, несовместимость с `pg_stat_statements`.
- https://postgrespro.ru/docs/postgrespro/17/pgpro-pwr — `pgpro_pwr`: выборки, отчёты, параметры, расписание.
- https://github.com/postgrespro/mamonsu и https://raw.githubusercontent.com/postgrespro/mamonsu/master/documentation/metrics.md — установка, команды, метрики и триггеры mamonsu.

Инструменты:

- https://github.com/darold/pgbadger, https://raw.githubusercontent.com/darold/pgbadger/master/README, https://github.com/darold/pgbadger/releases — настройки сервера, ключи, примеры, версия 13.2.
- https://github.com/zubkov-andrei/pg_profile — установка, зависимости, поддерживаемые версии (в первой редакции статьи была указана 4.14, хотя уже вышла 4.16 от 2026-09-15).
- https://github.com/dalibo/pg_activity — установка, ключи, клавиши.
- https://github.com/lesovsky/pgcenter — подкоманды pgcenter.
- https://www.zabbix.com/integrations/postgresql — шаблоны Zabbix, пользователь `zbx_monitor`, макросы, триггеры.
- https://github.com/prometheus-community/postgres_exporter и https://github.com/prometheus-community/postgres_exporter/releases — коллекторы, переменные окружения, версия 0.20.1.
- https://packages.ubuntu.com/noble/pgbadger, https://packages.ubuntu.com/resolute/pgbadger, https://packages.ubuntu.com/noble/pg-activity, https://packages.ubuntu.com/resolute/pg-activity, https://packages.ubuntu.com/resolute/pgtop, https://packages.ubuntu.com/resolute/postgresql — версии пакетов в Ubuntu 24.04 и 26.04 (в 26.04 метапакет `postgresql` зависит от `postgresql-18`).

Первоисточники независимой сверки 19.10.2026:

- Документация PostgreSQL 18 (текстовые копии от 10–11.10.2026): `runtime-config-logging`, `runtime-config-statistics`, `runtime-config-locks`, `runtime-config-compatible`, `monitoring-stats`, `view-pg-locks`, `view-pg-wait-events`, `functions-info`, `functions-admin`, `progress-reporting`, `pgstatstatements`, `auto-explain`, `sql-explain`, `routine-vacuuming`, `pgbuffercache`, `pgstattuple`, образец `postgresql.conf` 18; замечания к выпускам 15, 16, 17, 18.
- Исходный код PostgreSQL (https://raw.githubusercontent.com/postgres/postgres/REL_16_STABLE/…, REL_17_STABLE, REL_18_STABLE): `src/backend/utils/init/postinit.c` (`InitializeMaxBackends`), `src/backend/storage/lmgr/lock.c` (`NLOCKENTS`), `src/backend/storage/lmgr/proc.c` (сообщения `still waiting for` / `acquired`), `src/backend/access/transam/xlog.c` (`checkpoint complete`), `src/backend/utils/activity/wait_event_names.txt` и `generate-wait_event_types.pl`, `src/backend/utils/adt/pgstatfuncs.c` (состояние `starting`), `doc/src/sgml/config.sgml` (REL_16), `doc/src/sgml/datatype.sgml` (формат `bytea`), `src/test/regress/expected/subselect.out`, `contrib/pg_stat_statements/pg_stat_statements.c`; https://www.postgresql.org/ и https://www.postgresql.org/support/versioning/ — 19 RC 1 от 2026-10-15, окончание поддержки 14.
- Документация «PostgreSQL для 1С» 16 (https://repo.postgrespro.ru/doc/pg1c/16/ru/html/): приложение F (перечень модулей, F.5 `auto_dump`), приложение K (K.3 параметры, K.4 модули), установка; индекс пакетов 16.14 для noble; разбор пакета — `../guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`.
- Postgres Pro Standard 17: https://postgrespro.ru/docs/postgrespro/17/one-c-additional-modules (K.4.6 `pg_hint_plan`), `one-c-configuring-server`, `pg-wait-sampling`, `pgpro-stats`, `pgpro-pwr`.
- pgBadger: https://raw.githubusercontent.com/darold/pgbadger/v13.2/README; pg_activity: https://raw.githubusercontent.com/dalibo/pg_activity/v3.6.2/README.md; pgcenter: https://raw.githubusercontent.com/lesovsky/pgcenter/v0.11.0/README.md и `doc/pgcenter-profile-readme.md`; pg_profile: https://raw.githubusercontent.com/zubkov-andrei/pg_profile/4.16/README.md и `doc/pg_profile.md`, страница выпуска 4.16 (2026-09-15).
- Zabbix 7.4: https://raw.githubusercontent.com/zabbix/zabbix/release/7.4/templates/db/postgresql_agent2/README.md и `…/postgresql_agent/README.md`; плагин агента 2 — https://git.zabbix.com/projects/AP/repos/postgresql (README.md, postgresql.conf, ветка `release/7.4`).
- mamonsu 3.5.18: README.md, `documentation/metrics.md`, `mamonsu/plugins/pgsql/*.py` (пороги триггеров); postgres_exporter 0.20.1: README.md и CHANGELOG.md.
- https://apt.postgresql.org/pub/repos/apt/dists/noble-pgdg/main/binary-amd64/Packages.gz — пакеты `postgresql-NN-pg-wait-sampling` в PGDG; https://packages.ubuntu.com/ — `postgresql-NN-pg-wait-sampling` в 22.04, 24.04, 26.04.
- Конспекты ИТС: `../its-docs/dev-gl09-rabota-s-dannymi.md` (уровни изоляции), `../its-docs/adm-pr03-sluzhebnye-fajly-p3.md`, `…-p5.md` (`Dbpid`, `<dbmslocks>`), `../its-docs/cs-gl05-administrirovanie-klastera-p2.md` (поля сеанса, разрыв соединения), `../its-metod/monitoring-i-audit.md` и `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md` (тексты ошибок блокировок), `../its-metod/pg-nastrojki-postgresql-dlya-1c.md` (ИТС 5866), `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md` (ИТС 6011, 6032, 6039).
