# Каталог типовых проблем связки 1С + PostgreSQL на Linux: симптом → причина → решение

> **Официальные тексты по теме** (конспекты документации ИТС 8.3.27 и методических статей ИТС, составлены по полным текстам): `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, `../its-metod/ekspluataciya-krupnoj-sistemy-blokirovki-tranzakcii.md`, `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`. Статья писалась до получения доступа к закрытой документации: там, где ниже сказано «документация закрыта», «не прочитано» или стоит ⚠, сверяйтесь с этими конспектами — при расхождении правы они.

> Проверено независимой сверкой 19.10.2026: статья прочитана целиком; около 200 утверждений (тексты сообщений PostgreSQL и libpq, умолчания и описания параметров, версии появления и удаления, режимы блокировок, ключи утилит, имена представлений и колонок, рекомендации для 1С, пути и имена служб сборки «PostgreSQL для 1С» 16) сверены с документацией PostgreSQL 18 (и 15, 16, 19 RC — где различаются), исходным кодом PostgreSQL веток 11–18 (`auth.c`, `fe-connect.c`, `dbcommands.c`, `varsup.c`), документацией «PostgreSQL для 1С» 16 (приложение K, модули F, `pg-setup`), юнитом из пакета 16.14, документацией Postgres Pro 17 и Enterprise 17, packages.ubuntu.com, Microsoft Learn и конспектами ИТС `../its-docs/`, `../its-metod/`. Исправлено 14 ошибок (тексты сообщений о `pg_hba.conf`, локали и wraparound по версиям, формулировка ошибки взаимоблокировки, семафоры в Linux, порог GEQO, параметры `auto_dump` и наличие `pg_hint_plan` в сборке Postgres Pro, переход на Postgres Pro Enterprise, версии появления `hash_mem_multiplier = 2.0`, `datlocprovider`, `shared_memory_size_in_huge_pages`, предел таблиц в запросе MS SQL, статус PostgreSQL 19), закрыто 5 пометок «⚠», добавлена 1 (каталог ТЖ по умолчанию — документация называет два пути); добавлены сведения для сборки «PostgreSQL для 1С» 16 (абзац «Соглашения в командах», юнит службы в 5.3). Ранее, 10.10.2026, выполнена программная сверка имён, умолчаний и колонок с документацией PostgreSQL 18. На сервере команды не выполнялись; официальные рекомендации 1С — в `../its-metod/`.

> Область: диагностика и устранение ошибок клиент-серверной «1С:Предприятие 8» с СУБД PostgreSQL на Ubuntu Server (подключение, создание баз, расширения, память, производительность, блокировки, повреждения данных, WAL и диск, обновления) | Версии: Ubuntu 22.04 / 24.04 / 26.04 LTS; платформа 1С 8.3.22–8.3.27 и 8.5.1–8.5.4; PostgreSQL 14–18 в сборках для 1С («PostgreSQL с патчем от 1С», Postgres Pro 1С / Standard / Enterprise), справочно — PostgreSQL 19 (на 19.10.2026 — RC 1 от 15.10.2026, финальный выпуск ещё не вышел) | Актуальность: 2026-10-10, независимая сверка 2026-10-19

Условные обозначения:

- **[PG]** — документация PostgreSQL (postgresql.org), проверено по первоисточнику при подготовке статьи.
- **[PGPro]** — документация Postgres Professional (приложение «Настройка Postgres Pro для решений 1С», описания модулей).
- **[1С]** — документация платформы и методические статьи ИТС (в том числе по конспектам `kb/its-docs/`, `kb/its-metod/`).
- **[практика]** — сложившаяся практика сообщества (Infostart, Habr, форумы, блоги интеграторов), не официальная рекомендация.
- **⚠ не подтверждено** — утверждение по памяти автора; первоисточник при подготовке прочитать не удалось. Перед применением проверить на тестовом стенде.

Ограничение этой версии статьи: поиск по интернету при подготовке был недоступен (исчерпан лимит поисковых запросов сессии), читались только страницы с известными адресами — документация PostgreSQL, Postgres Pro, v8.1c.ru. Страницы ИТС отдаются автоматическому загрузчику с искажённой кириллицей; материалы Infostart/Habr/форумов напрямую не сверялись. Поэтому точные тексты сообщений **платформы 1С** (в отличие от текстов PostgreSQL) местами помечены ⚠.

Соглашения в командах: кластер PostgreSQL в раскладке Debian/Ubuntu — версия `17`, имя `main` (служба `postgresql@17-main`, конфигурация `/etc/postgresql/17/main/`, данные `/var/lib/postgresql/17/main`, журнал `/var/log/postgresql/postgresql-17-main.log`). Для сборки Postgres Pro 1С подставляйте службу `postgrespro-1c-17`, каталог данных `/var/lib/pgpro/1c-17/data`, программы `/opt/pgpro/1c-17/bin`. **У пользователя этой базы знаний — ветка 16:** служба `postgrespro-1c-16`, данные `/var/lib/pgpro/1c-16/data`, программы и библиотеки `/opt/pgpro/1c-16/bin` и `/opt/pgpro/1c-16/lib`, журнал сервера `/var/lib/pgpro/1c-16/data/log/`, кластер в локали `en_US.UTF-8` (подставляйте её вместо `ru_RU.UTF-8`). Утилит `postgresql-common` (`pg_lsclusters`, `pg_createcluster`, `pg_dropcluster`, служба `postgresql@…`) в этой сборке нет — её пакет конфликтует с `postgresql-common`; состояние экземпляра — `systemctl status postgrespro-1c-16` или `sudo /opt/pgpro/1c-16/bin/pg-setup service status` (`kb/guides/07-…`). Сервер 1С — служба `srv1cv8-<версия>@default`, пользователь ОС `usr1cv8`. База 1С в примерах — `buh`, адрес сервера 1С — `192.168.10.20`.

Смежные статьи базы знаний (там подробности, здесь — каталог): `01-sborki-postgresql-dlya-1c-ustanovka.md` (сборки, локаль, зависимости), `02-postgresql-conf-tyuning-dlya-1c.md` (параметры, `pg_hba.conf`, тюнинг ОС), `03-administrirovanie-psql-i-utility.md`, `04-rezervnoe-kopirovanie-i-vosstanovlenie.md`, `05-obsluzhivanie-vacuum-analyze-reindex.md` (VACUUM, REINDEX, WAL, повреждения), `06-monitoring-i-diagnostika-zaprosov.md` (pg_stat_*, блокировки, планы), `kb/1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md` (технологический журнал).

---

## Кратко — главные факты и команды

1. **Текст ошибки в 1С состоит из «обёртки» платформы и сообщения СУБД.** «Сервер баз данных не обнаружен» + текст libpq/`FATAL` — проблема подключения или аутентификации (раздел 2). «Ошибка СУБД: ERROR: …» — сервер ответил ошибкой на запрос (разделы 3–9). «Конфликт блокировок при выполнении транзакции» — таймаут блокировки (раздел 7). Искать причину нужно по **английской части** сообщения.
2. **Первые три команды при любой проблеме:**
   ```bash
   pg_lsclusters                                                   # кластер online? порт? каталог данных?
   sudo tail -n 100 /var/log/postgresql/postgresql-17-main.log     # что сказал сервер
   df -h /var/lib/postgresql && free -h                            # место и память
   ```
   Подводный камень Ubuntu: `systemctl status postgresql` показывает `active (exited)` всегда — это служба-«зонтик». Реальное состояние — `systemctl status postgresql@17-main` и `pg_lsclusters`.
3. **Сервер 1С подключается к PostgreSQL только по TCP** (даже на одной машине), поэтому нужны `listen_addresses`, строка `host` в `pg_hba.conf` и пароль роли. Строки `local … peer` на 1С не влияют [PG][практика].
4. **«Сервер баз данных не обнаружен» ≠ «сервер выключен».** Под этой шапкой приходят и `Connection refused`, и `no pg_hba.conf entry`, и `password authentication failed`, и ошибки разрешения имён. `Connection refused` означает, что по адресу никто не слушает; отказ самого PostgreSQL выглядит иначе (`FATAL: …`) [PG].
5. **Обычный PostgreSQL из репозитория Ubuntu/PGDG для 1С не годится:** нет типов `mchar`/`mvarchar`, оператора `==` (`fulleq`), функции `fasttruncate()` (`fasttrun`) [PGPro][1С]. Признак — `ERROR: type "mvarchar" does not exist`.
6. **Локаль `ru_RU.UTF-8` должна существовать в ОС до создания кластера**, а кластер — быть создан с ней. Иначе при создании базы: `new collation (ru_RU.UTF-8) is incompatible with the collation of the template database`, `invalid locale name` (в 16+ — `invalid LC_COLLATE locale name`) [PG][1С][PGPro].
7. **Пользователю PostgreSQL, от имени которого 1С создаёт базу, нужна привилегия `SUPERUSER` — только на момент создания** [1С]. После создания её можно снять: `ALTER USER dbuser WITH NOSUPERUSER;`.
8. **`ERROR: out of shared memory` — это не нехватка ОЗУ**, а переполнение таблицы блокировок: поднимите `max_locks_per_transaction` (умолчание 64; для 1С 256 [PGPro], 512–2000 [1С]) и перезапустите PostgreSQL.
9. **Режим блокировок конфигурации определяет поведение на PostgreSQL:** автоматический — уровень изоляции Serializable и блокировки **таблиц целиком**, управляемый — Read Committed и блокировки строк [1С]. Конфигурация в автоматическом режиме на PostgreSQL почти не масштабируется по параллельной записи.
10. **Платформа сама выставляет параметры сеанса:** `enable_mergejoin = off`, `cpu_operator_cost = 0.001`, `lock_timeout = 20000`, `escape_string_warning = off`, `client_min_messages = error`, `lc_messages = 'en_US.UTF-8'`, `client_encoding = 'utf8'` [1С, ИТС 6011]. Чтобы получить в `psql` тот же план, что у 1С, задайте их перед `EXPLAIN` — и добавьте `SET standard_conforming_strings = off;`, если сервер настроен иначе.
11. **Медленные запросы 1С на PostgreSQL чаще всего — следствие неверной оценки числа строк** (временные таблицы, сложные условия): планировщик выбирает Nested Loop там, где нужен Hash Join. Лечится статистикой (`plantuner.fix_empty_table = on`, явный `ANALYZE`, при необходимости `online_analyze`), переписыванием запроса и параметрами `join_collapse_limit`/`from_collapse_limit = 20`, `jit = off`, `max_parallel_workers_per_gather = 0` [1С][PGPro].
12. **`autovacuum` не выключать никогда** [1С][PGPro]. Раздувание таблиц, `pg_class`/`pg_attribute` в гигабайтах и предупреждения о wraparound — следствие выключенной или не успевающей автоочистки и «висящих» транзакций (`idle in transaction`).
13. **Файлы в `pg_wal` руками не удалять никогда.** Разросшийся `pg_wal` — это неактивный слот репликации или сломанная архивация; смотрите `pg_replication_slots` и `pg_stat_archiver`. При заполнении диска PostgreSQL делает PANIC-остановку, зафиксированные транзакции не теряются, но сервер не поднимется, пока не освободится место [PG].
14. **После обновления выпуска Ubuntu (22.04 → 24.04 → 26.04) меняются glibc и ICU** — индексы по строкам могут стать некорректными. Нужны сборка PostgreSQL под новую ОС, `REINDEX` и `ALTER DATABASE … REFRESH COLLATION VERSION` [PG]. Безопаснее переносить базы дампом на новую ВМ.
15. **Версионные ловушки:** PostgreSQL 14 — `password_encryption = scram-sha-256` по умолчанию; 15 — у `PUBLIC` отобрано право `CREATE` в схеме `public`, удалён `stats_temp_directory`; 18 — MD5 объявлен устаревшим, контрольные суммы включены в `initdb` по умолчанию; **19 (на 19.10.2026 — кандидат в выпуск RC 1)** — `standard_conforming_strings` принудительно `on`, `escape_string_warning` удалён, `jit` выключен по умолчанию, `max_locks_per_transaction` по умолчанию 128 [PG] (сверено 19.10.2026 с примечаниями к выпуску 19, редакция на 09.10.2026; на 19.10.2026 вышел RC 1). Для 1С используйте только версии из списка поддерживаемых (на июль 2026 — 14–18).
16. **«Тормозит» — сначала выяснить, где время:** СУБД, сервер 1С или ожидание блокировок. Быстрая оценка — доля длительности событий `DBPOSTGRS` в `CALL` по технологическому журналу; больше ~50 % — заниматься запросами [1С, ИТС 6011].
17. **Виртуальная машина:** энергосбережение и переподписка vCPU настраиваются на хосте; динамическая память/ballooning для сервера СУБД и сервера 1С противопоказаны (ломают huge pages, провоцируют OOM, сбивают привязку программных лицензий 1С) [1С][PGPro][практика].
18. **Универсальные запросы диагностики:**
    ```sql
    -- кто что делает и чего ждёт
    SELECT pid, state, wait_event_type, wait_event, now() - xact_start AS xact_age,
           now() - query_start AS query_age, left(query, 80) AS query
    FROM pg_stat_activity WHERE backend_type = 'client backend' ORDER BY xact_start NULLS LAST;
    -- кто кого блокирует
    SELECT pid, pg_blocking_pids(pid) AS blocked_by, left(query, 80) AS query
    FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;
    ```

---

## 1. С чего начинать: как читать ошибку и где искать подробности

### 1.1. Анатомия сообщения об ошибке в 1С

| Что видит пользователь или администратор 1С | Что это значит | Куда идти |
|---|---|---|
| «Ошибка при выполнении операции с информационной базой. **Сервер баз данных не обнаружен**» + текст вида `could not connect to server…`, `connection to server at … failed…`, `FATAL: …` | Рабочий процесс 1С не смог установить соединение с PostgreSQL: сеть, имя, порт, `pg_hba.conf`, пароль, лимит соединений | Раздел 2 |
| «**Ошибка СУБД:** `ERROR: …`» (часто с `DETAIL`, `HINT`, `CONTEXT`) | Соединение есть, PostgreSQL отклонил конкретный запрос | Разделы 3–6, 8, 9 |
| «**Конфликт блокировок при выполнении транзакции:** Превышено максимальное время ожидания предоставления блокировки» | Таймаут **управляемой** блокировки 1С (менеджер блокировок кластера). PostgreSQL ни при чём | Раздел 7 |
| «Конфликт блокировок при выполнении транзакции: `ERROR: canceling statement due to lock timeout`» | Таймаут блокировки **СУБД** (`lock_timeout`, который платформа ставит сеансу) | Раздел 7 |
| «Конфликт блокировок при выполнении транзакции:» + `ERROR: deadlock detected` | Взаимоблокировка **СУБД**, PostgreSQL отменил транзакцию-жертву. Взаимоблокировка **управляемых** блокировок 1С выглядит иначе — «Неустранимый конфликт блокировок» (событие ТЖ `TDEADLOCK`). Уточнено 19.10.2026 по конспектам ИТС `../its-metod/monitoring-i-audit.md` (тексты управляемых блокировок в `Descr`) и `../1c/07-…` (ИТС 5809, 6006: ошибки блокировок СУБД 1С выводит с префиксом «Конфликт блокировок при выполнении транзакции:» и текстом СУБД); прежняя формулировка «Неразрешимый конфликт…» была неверной | Раздел 7 |
| «Ошибка соединения с сервером 1С:Предприятия», «Сервер 1С:Предприятия не обнаружен» | Проблема между клиентом и кластером 1С, до СУБД дело не дошло | `kb/1c/02`, `kb/1c/03` |

Правило [1С, ИТС 2313]: после ошибки базы данных внутри транзакции эту транзакцию нельзя ни продолжить, ни зафиксировать — только отменить. В журнале PostgreSQL это выглядит как серия `ERROR: current transaction is aborted, commands ignored until end of transaction block`. Это всегда **следствие**: причина — первая ошибка выше по журналу в том же процессе (`pid`).

### 1.2. Где лежат подробности

```bash
# --- PostgreSQL ---
pg_lsclusters                                                     # версия, имя, порт, статус, каталог, журнал
sudo systemctl status postgresql@17-main --no-pager               # состояние экземпляра (не «postgresql»!)
sudo journalctl -u postgresql@17-main -n 100 --no-pager           # ошибки запуска
sudo tail -n 200 /var/log/postgresql/postgresql-17-main.log       # журнал сервера (Debian-раскладка)
sudo -u postgres psql -At -c "SHOW logging_collector" -c "SHOW log_directory" -c "SELECT pg_current_logfile()"   # где журнал в других сборках
# Postgres Pro 1С
sudo journalctl -u postgrespro-1c-17 -n 100 --no-pager
sudo ls -lt /var/lib/pgpro/1c-17/data/log/ | head

# --- только ошибки и фатальные сообщения за сегодня ---
sudo grep -E 'ERROR|FATAL|PANIC' /var/log/postgresql/postgresql-17-main.log | tail -n 50

# --- сервер 1С ---
V=$(ls /opt/1cv8/x86_64/ | sort -V | tail -1)                     # установленная версия платформы
sudo systemctl status "srv1cv8-$V@default" --no-pager
sudo journalctl -u "srv1cv8-$V@default" -n 100 --no-pager
sudo ls -lt /home/usr1cv8/.1cv8/1C/1cv8/logs/ /home/usr1cv8/.1cv8/logs/ 2>/dev/null | head   # «ТЖ по умолчанию» (SYSTEM/ERROR, 24 часа)
# документация 8.3.27 называет оба каталога: 6.14.3 — ~/.1cv8/1C/1cv8/logs, приложение 3.24.1 — ~/.1cv8/logs (⚠ какой действует в вашей сборке — смотреть на сервере; см. kb/1c/07)
```

Журнал PostgreSQL полезно настроить заранее (подробно — `06-monitoring-i-diagnostika-zaprosov.md`):

```ini
# /etc/postgresql/17/main/conf.d/95-diag.conf   → sudo systemctl reload postgresql@17-main
log_line_prefix = '%m [%p] %q%u@%d %h '         # время, pid, роль@база, адрес клиента
log_lock_waits = on                             # ожидания дольше deadlock_timeout (1 с)
log_temp_files = 100MB                          # крупные временные файлы
log_checkpoints = on                            # умолчание on с 15-й версии
log_autovacuum_min_duration = '10s'
log_min_duration_statement = '5s'               # 0 = все запросы: только кратковременно, на нагрузке замедляет
lc_messages = 'C'                               # сообщения на английском — их проще искать
```

Минимальный технологический журнал 1С для ловли ошибок СУБД (`/opt/1cv8/conf/logcfg.xml`, применяется без перезапуска в течение 60 секунд; каталог должен быть доступен на запись `usr1cv8`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="/var/log/1c/tj" history="24">
    <event><eq property="name" value="EXCP"/></event>
    <event><eq property="name" value="DBPOSTGRS"/><ge property="durationus" value="5000000"/></event>
    <event><eq property="name" value="TTIMEOUT"/></event>
    <event><eq property="name" value="TDEADLOCK"/></event>
    <property name="all"/>
  </log>
</config>
```

```bash
sudo install -d -o usr1cv8 -g grp1cv8 /var/log/1c/tj
grep -rh --include='*.log' 'EXCP' /var/log/1c/tj | grep -i -E 'ERROR:|FATAL:' | tail -n 20
```

### 1.3. Коды SQLSTATE, которые встречаются чаще всего [PG]

| SQLSTATE | Сообщение PostgreSQL | Смысл |
|---|---|---|
| `28P01` | `password authentication failed for user "…"` | неверный пароль или несовместимый метод |
| `28000` | `no pg_hba.conf entry for host …` | нет подходящего правила доступа |
| `3D000` | `database "…" does not exist` | базы нет (опечатка, другой экземпляр, другой порт) |
| `53300` | `sorry, too many clients already` | исчерпан `max_connections` |
| `53100` | `could not extend file …: No space left on device` | диск заполнен |
| `53200` | `out of memory`, `out of shared memory` | нехватка памяти процесса либо таблицы блокировок |
| `55P03` | `canceling statement due to lock timeout` | блокировку ждали дольше `lock_timeout` |
| `40P01` | `deadlock detected` | взаимоблокировка |
| `40001` | `could not serialize access …` | конфликт сериализации (уровни Repeatable Read / Serializable) |
| `23505` | `duplicate key value violates unique constraint "…"` | нарушение уникальности индекса |
| `25P02` | `current transaction is aborted, commands ignored until end of transaction block` | следствие предыдущей ошибки в транзакции |
| `42704` | `type "mvarchar" does not exist` | нет расширения `mchar` (ванильная сборка) |
| `42501` | `permission denied for …` | нет прав (схема `public`, таблица, язык) |
| `55006` | `database "…" is being accessed by other users` | к базе есть подключения |
| `54001` | `stack depth limit exceeded` | слишком глубокая рекурсия разбора запроса |
| `57014` | `canceling statement due to statement timeout` / `… due to user request` | сработал таймаут или запрос отменён |
| `57P01` | `terminating connection due to administrator command` | соединение завершено (`pg_terminate_backend`, остановка сервера) |
| `57P03` | `the database system is starting up` / `… is in recovery mode` | сервер ещё не готов принимать соединения |
| `XX001`, `XX002` | `invalid page in block …`, повреждение индекса | повреждение данных (раздел 8) |

Код SQLSTATE в журнал добавляет `%e` в `log_line_prefix`.

---

## 2. Подключение и аутентификация

### 2.1. Каталог ошибок

Тексты libpq зависят от версии клиентской библиотеки, встроенной в платформу 1С: старый формат — `could not connect to server: …`, новый (libpq 14+) — `connection to server at "…" (…), port 5432 failed: …` [PG]. Смысл одинаков.

| № | Текст (после «Сервер баз данных не обнаружен») | Причина | Диагностика | Решение |
|---|---|---|---|---|
| 1 | `could not connect to server: Connection refused. Is the server running on host "X" (IP) and accepting TCP/IP connections on port 5432?` / `connection to server at "X" (IP), port 5432 failed: Connection refused` | По адресу и порту никто не слушает: PostgreSQL остановлен; `listen_addresses = 'localhost'`, а подключение идёт с другого хоста или на другой локальный адрес; другой порт | `pg_lsclusters`; `sudo ss -tlnp \| grep postgres`; `SHOW listen_addresses; SHOW port;` | Запустить службу; задать `listen_addresses = '*'` (или конкретные адреса) и **перезапустить**; в 1С указать порт: `host port=5433` |
| 2 | `could not translate host name "X" to address: Name or service not known` (вариант: `Temporary failure in name resolution`) | Сервер 1С не может разрешить имя сервера СУБД | На сервере 1С: `getent hosts X` | Запись в `/etc/hosts` сервера 1С или DNS; либо указать IP-адрес |
| 3 | `… Connection timed out` / `timeout expired` | Пакеты не доходят: брандмауэр (ufw, брандмауэр хоста виртуализации), неверный IP, маршрутизация | С сервера 1С: `nc -vz X 5432`; на сервере СУБД: `sudo ufw status verbose` | `sudo ufw allow from 192.168.10.20 to any port 5432 proto tcp` |
| 4 | `… No route to host` | Нет маршрута либо брандмауэр отвечает ICMP-отказом | `ip route get IP`; `ping` | Сеть/брандмауэр |
| 5 | `FATAL: no pg_hba.conf entry for host "IP", user "U", database "D", no encryption` (так с 14-й версии; в 13 и ранее — `SSL off`; сверено 19.10.2026 по `src/backend/libpq/auth.c` веток 11–18) | Нет строки `host` для сочетания адрес + роль + база. Адрес в сообщении — тот, с которого сервер СУБД видит клиента | `SELECT * FROM pg_hba_file_rules;` | Добавить строку, `sudo systemctl reload postgresql@17-main` |
| 6 | `FATAL: no pg_hba.conf entry for host "::1", …` | `localhost` разрешился в IPv6-адрес `::1`, а строки `host … ::1/128` нет | `getent ahosts localhost` | Добавить `host all all ::1/128 scram-sha-256` либо в 1С указать `127.0.0.1` |
| 7 | `FATAL: password authentication failed for user "U"` | Неверный пароль; у роли нет пароля; пароль роли хранится как MD5, а метод в `pg_hba.conf` — `scram-sha-256`; срок пароля истёк (`VALID UNTIL`) | Журнал сервера (там есть `DETAIL`); запрос типа хеша — ниже | `\password U`; привести в соответствие метод и хеш |
| 8 | `authentication method 10 not supported` (текст подтверждён исходным кодом libpq (`fe-auth.c`: `authentication method %u not supported`), сверено 11.10.2026; ранее: текст по сообщениям сообщества) | Клиентская библиотека старой платформы 1С не умеет SCRAM (метод 10 = SASL), а сервер требует `scram-sha-256` | Версия платформы; тип хеша пароля | Обновить платформу; временный обход — MD5 (раздел 2.4) |
| 9 | `FATAL: database "D" does not exist` | Опечатка в имени базы, другой экземпляр или порт; база удалена | `psql -l` на нужном порту | Исправить параметры информационной базы |
| 10 | `FATAL: role "U" does not exist` | Нет такой роли в этом экземпляре | `\du` | `CREATE ROLE … LOGIN PASSWORD …` |
| 11 | `FATAL: sorry, too many clients already` | Исчерпан `max_connections` (умолчание 100) | Запрос числа соединений — ниже | `max_connections = 500..1000`, перезапуск; найти причину роста |
| 12 | `FATAL: remaining connection slots are reserved for non-replication superuser connections` (версии по 15-ю включительно); `… reserved for roles with the SUPERUSER attribute` (16+; оба текста подтверждены исходным кодом `postinit.c` веток 15 и 18, сверено 11.10.2026; в 16+ есть и третий вариант — `… reserved for roles with privileges of the "pg_use_reserved_connections" role`; ранее: тексты приведены по памяти) | То же, что 11, но роль не суперпользователь: свободны только зарезервированные слоты (`superuser_reserved_connections`, умолчание 3) | То же | То же. Не «лечить» переводом роли 1С в суперпользователи |
| 13 | `FATAL: the database system is starting up` / `… is in recovery mode` / `… is shutting down` | Сервер запускается, восстанавливается по WAL после сбоя или останавливается | Журнал сервера | Дождаться; если восстановление долгое — не перезапускать, смотреть прогресс в журнале |
| 14 | `server closed the connection unexpectedly. This probably means the server terminated abnormally before or while processing the request.` | Серверный процесс завершился: OOM killer, сбой, `pg_terminate_backend`, перезапуск PostgreSQL | Журнал сервера; `sudo dmesg -T \| grep -i -E 'killed process\|out of memory'` | Разделы 5.3, 8 |
| 15 | `FATAL: Peer authentication failed for user "postgres"` (в `psql`, не в 1С) | Локальное подключение через Unix-сокет с методом `peer` от другого пользователя ОС | — | `sudo -u postgres psql` либо `psql -h 127.0.0.1 -U postgres` |

### 2.2. Команды проверки (по шагам, от сервера СУБД к серверу 1С)

```bash
# 1. PostgreSQL запущен и на каком порту
pg_lsclusters
sudo ss -tlnp | grep -E 'postgres|:5432'
# 0.0.0.0:5432 или *:5432 — слушает все адреса; 127.0.0.1:5432 — только локальные подключения

# 2. Параметры и правила доступа
sudo -u postgres psql -c "SHOW listen_addresses;" -c "SHOW port;" -c "SHOW password_encryption;"
sudo -u postgres psql -c "SELECT line_number, type, database, user_name, address, netmask, auth_method, error
                          FROM pg_hba_file_rules ORDER BY line_number;"
# столбец error не пуст → строка с ошибкой; после неудачного reload сервер продолжает работать по старым правилам

# 3. Есть ли у роли пароль и каким алгоритмом он сохранён
sudo -u postgres psql -c "SELECT rolname, rolcanlogin, rolsuper, rolvaliduntil,
       CASE WHEN rolpassword IS NULL THEN 'нет пароля'
            WHEN rolpassword LIKE 'SCRAM-SHA-256\$%' THEN 'scram-sha-256'
            WHEN rolpassword LIKE 'md5%' THEN 'md5' ELSE '?' END AS hash
FROM pg_authid WHERE rolcanlogin;"

# 4. Проверка с сервера 1С от имени пользователя сервера — именно так, как подключается rphost
getent hosts pg-server                                  # имя разрешается?
nc -vz pg-server 5432                                   # порт достижим?
pg_isready -h pg-server -p 5432                         # сервер принимает соединения?
sudo -u usr1cv8 psql "host=pg-server port=5432 dbname=postgres user=postgres" -c "select version();"

# 5. Что записал сервер СУБД в момент неудачной попытки
sudo grep -E 'FATAL|no pg_hba|authentication' /var/log/postgresql/postgresql-17-main.log | tail -n 20

# 6. Сколько соединений занято
sudo -u postgres psql -c "SELECT count(*) AS used, current_setting('max_connections') AS max FROM pg_stat_activity;"
sudo -u postgres psql -c "SELECT datname, usename, client_addr, state, count(*) FROM pg_stat_activity
                          WHERE backend_type = 'client backend' GROUP BY 1,2,3,4 ORDER BY 5 DESC;"
```

Если шаг 4 проходит, а 1С не подключается — причина в параметрах информационной базы (имя сервера, порт, имя базы, пользователь, пароль) либо в том, что рабочий процесс запущен на **другом** рабочем сервере кластера, с которого СУБД недоступна.

### 2.3. Типовая рабочая конфигурация доступа

```ini
# postgresql.conf (или conf.d/90-1c.conf) — требует ПЕРЕЗАПУСКА
listen_addresses = '*'          # умолчание 'localhost' — только локальные TCP-подключения [PG]
port = 5432
ssl = off                       # рекомендация 1С: шифрование повышает загрузку CPU [1С]
```

```text
# pg_hba.conf — достаточно reload; первое совпавшее правило применяется, «проваливания» дальше нет [PG]
# TYPE  DATABASE  USER      ADDRESS             METHOD
local   all       postgres                      peer
host    all       all       127.0.0.1/32        scram-sha-256
host    all       all       ::1/128             scram-sha-256
host    all       postgres  192.168.10.20/32    scram-sha-256     # сервер 1С (все базы, включая служебную postgres)
```

```bash
sudo systemctl restart postgresql@17-main       # после listen_addresses / port
sudo systemctl reload  postgresql@17-main       # после pg_hba.conf
sudo ufw allow from 192.168.10.20 to any port 5432 proto tcp
```

Пояснения:

- Серверу 1С нужен доступ не только к своей базе, но и к служебной базе `postgres` — через неё проверяется существование базы и выполняется `CREATE DATABASE` [практика]. Правило вида `host buh usr …` без доступа к `postgres` даёт ошибку при создании базы.
- **Ловушка `127.0.1.1` в Ubuntu** [практика]: установщик добавляет в `/etc/hosts` строку `127.0.1.1 <имя_хоста>`. Если в поле «Сервер баз данных» указано имя хоста, а `listen_addresses = 'localhost'`, подключение идёт на `127.0.1.1:5432`, где никто не слушает → `Connection refused`. Указывайте `localhost`/`127.0.0.1` либо задайте `listen_addresses = '*'`.
- **Нестандартный порт** в 1С задаётся в поле «Сервер баз данных»: `pg-server port=5433` (пример из документации: `localhost port=6432;`) [1С].
- Не пишите `host all all 0.0.0.0/0 md5` «чтобы работало»: это открывает подбор пароля суперпользователя со всей сети.

### 2.4. md5 и scram-sha-256

Факты [PG]:

- `password_encryption` определяет, в каком виде пароль сохраняется **в момент** `CREATE/ALTER ROLE … PASSWORD` или `\password`. Умолчание — `scram-sha-256` начиная с PostgreSQL 14 (раньше `md5`).
- Метод `md5` в `pg_hba.conf` при пароле, сохранённом как SCRAM, автоматически превращается в SCRAM-аутентификацию. Обратное неверно: пароль-MD5 при методе `scram-sha-256` даёт `password authentication failed`.
- Пароль в виде SCRAM работает с методами `scram-sha-256` и `password`; пароль-MD5 — с `md5` и `password`.
- PostgreSQL 18: MD5 объявлен устаревшим, `CREATE/ALTER ROLE` с MD5 выдаёт предупреждение (глушится `md5_password_warnings = off`); в 19-й предупреждение выдаётся и после успешной MD5-аутентификации.

Поддержка SCRAM платформой 1С: актуальные версии (8.3.2x, 8.5.x) со SCRAM работают [практика]; с какой именно версии — **⚠ не подтверждено** (в просмотренных списках изменений не найдено). Проблема характерна для старых платформ (8.3.1x) в связке с PostgreSQL 13/14+.

Обход для старой платформы (временный; для PostgreSQL 18+ — тупиковый путь, обновляйте платформу):

```sql
ALTER SYSTEM SET password_encryption = 'md5';
SELECT pg_reload_conf();
ALTER ROLE postgres WITH PASSWORD 'СложныйПароль';   -- пароль нужно задать заново, чтобы он пересохранился
```

и метод `md5` в соответствующей строке `pg_hba.conf` (+ `reload`). Правильный путь перехода на SCRAM [PG]: убедиться, что клиенты умеют SCRAM → `password_encryption = 'scram-sha-256'` → заново задать пароли всем ролям → заменить `md5` на `scram-sha-256` в `pg_hba.conf` → `reload`. Какой метод реально использован, видно в журнале при `log_connections = on`: `connection authenticated: identity="postgres" method=scram-sha-256`.

### 2.5. Исчерпание соединений

- Сервер 1С держит **пул** соединений в каждом рабочем процессе; соединение не привязано к пользователю. Число соединений зависит от числа одновременно выполняемых серверных вызовов, фоновых заданий и удерживаемых менеджеров временных таблиц.
- Официальные ориентиры: `max_connections = 500..10000` [PGPro], `500..8000`, от «число сеансов / 8» до «число сеансов / 4» [1С]. Параметр требует перезапуска; при huge pages после изменения пересчитайте `vm.nr_hugepages`.
- Резкий рост числа соединений — симптом, а не причина: массовое ожидание блокировок, зависшие фоновые задания, «утечка» из-за аварийных завершений `rphost`. Смотрите `state` и `wait_event_type` в `pg_stat_activity`.
- Аварийный вход администратора при `too many clients`: слоты `superuser_reserved_connections` (3) доступны только суперпользователю (по любому способу подключения; проще всего — `sudo -u postgres psql` через Unix-сокет). Поэтому роль, под которой работает 1С, после создания базы лучше лишить `SUPERUSER`: иначе 1С займёт и резерв.

```sql
-- аварийно освободить соединения, простаивающие дольше часа (сеансы 1С возьмут новые из пула)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE backend_type = 'client backend' AND state = 'idle' AND now() - state_change > interval '1 hour';
```

---

## 3. Создание, удаление и загрузка информационной базы

### 3.1. Права

| Симптом | Причина | Решение |
|---|---|---|
| `ERROR: permission denied to create database` | У роли нет `CREATEDB`/`SUPERUSER` | По документации 1С пользователю СУБД на момент создания информационной базы нужна привилегия `SUPERUSER` [1С]: `ALTER ROLE dbuser WITH SUPERUSER;` → создать базу → `ALTER USER dbuser WITH NOSUPERUSER;` |
| `ERROR: permission denied for language c` либо `must be superuser to create …` при создании базы (⚠ точный текст зависит от версии и сборки) | Инициализация базы создаёт объекты расширений (`mchar`, `fulleq`, `fasttrun`), для чего нужен суперпользователь | То же |
| `ERROR: permission denied for schema public` (PostgreSQL 15+) | Базу создал один пользователь (например, `postgres` вручную), а 1С работает под другим, не владельцем. С 15-й версии у `PUBLIC` нет права `CREATE` в схеме `public`; владелец схемы — роль `pg_database_owner`, то есть владелец базы [PG] | Сделать роль 1С владельцем базы: `ALTER DATABASE buh OWNER TO dbuser;` либо `GRANT ALL ON SCHEMA public TO dbuser;` (выполнять, подключившись к `buh`) |
| `ERROR: permission denied for table config` / `… for relation …` после восстановления дампа | Объекты восстановлены с другим владельцем | Восстанавливать `pg_restore --no-owner --role=dbuser` либо после: `REASSIGN OWNED BY старая_роль TO dbuser;` (в этой базе) и `ALTER DATABASE buh OWNER TO dbuser;` |
| `ERROR: role "X" does not exist` при `pg_restore` | В дампе владельцем указана роль, которой нет на новом сервере | Создать роль либо `--no-owner --no-privileges` |
| `ERROR: must be owner of database buh` при удалении базы | Удаляет не владелец и не суперпользователь | Удалять от владельца или `postgres` |

Проверка:

```sql
SELECT d.datname, pg_get_userbyid(d.datdba) AS owner FROM pg_database d;
\du
\dn+ public          -- владелец и права на схему public (выполнять в базе 1С)
```

### 3.2. Локаль и кодировка

Тексты сообщений PostgreSQL (сверено 19.10.2026 с `src/backend/commands/dbcommands.c` веток 14, 15, 16 и 18; правило о совпадении с шаблоном — с документацией `CREATE DATABASE` [PG]):

```text
ERROR:  new encoding (UTF8) is incompatible with the encoding of the template database (SQL_ASCII)
HINT:  Use the same encoding as in the template database, or use template0 as template.

ERROR:  new collation (ru_RU.UTF-8) is incompatible with the collation of the template database (en_US.UTF-8)
HINT:  Use the same collation as in the template database, or use template0 as template.

ERROR:  new LC_CTYPE (ru_RU.UTF-8) is incompatible with the LC_CTYPE of the template database (C.UTF-8)
HINT:  Use the same LC_CTYPE as in the template database, or use template0 as template.

ERROR:  invalid locale name: "ru_RU.UTF-8"                 -- PostgreSQL 14–15
ERROR:  invalid LC_COLLATE locale name: "ru_RU.UTF-8"      -- PostgreSQL 16+ (для LC_CTYPE — invalid LC_CTYPE locale name)
```

Причины:

- **Кластер создан с другой локалью** (`C`, `C.UTF-8`, `en_US.UTF-8`) — типично, когда пакет PostgreSQL ставился на систему с `LANG=C.UTF-8`/`en_US.UTF-8` (облачные образы Ubuntu). Правило PostgreSQL: кодировка и локаль новой базы должны совпадать с шаблоном, кроме случая `TEMPLATE template0` [PG].
- **Локали `ru_RU.UTF-8` нет в ОС** (`invalid locale name`, в 16+ — `invalid LC_COLLATE locale name`) либо она сгенерирована после запуска PostgreSQL.
- Документация платформы требует совпадения национальных установок (locale) кластера и создаваемой информационной базы и кодировку UTF-8 [1С]; Postgres Pro — чтобы русская локаль была установлена и активна у пользователя, создающего кластер [PGPro].
- Кодировка `SQL_ASCII` у шаблона — кластер создан при `LANG=C`/`POSIX` без указания кодировки.

Диагностика:

```bash
locale -a | grep -i -E 'ru_RU|C.utf8'                       # есть ли локаль в ОС (вывод: ru_RU.utf8)
sudo -u postgres psql -c "SELECT datname, pg_encoding_to_char(encoding) AS enc, datcollate, datctype, datlocprovider
                          FROM pg_database ORDER BY 1;"            # datlocprovider — с 15-й версии; в 14-й убрать
```

Решение A — локали нет в ОС:

```bash
sudo locale-gen ru_RU.UTF-8
sudo update-locale LANG=ru_RU.UTF-8
sudo systemctl restart postgresql@17-main                   # чтобы серверные процессы увидели новую локаль [практика]
```

Решение B — кластер **пустой** (только что установлен): пересоздать с нужной локалью. Команды уничтожают все данные кластера.

```bash
# Debian-раскладка (сборка от 1С)
sudo pg_dropcluster --stop 17 main
sudo pg_createcluster --locale=ru_RU.UTF-8 --encoding=UTF8 17 main --start
# Postgres Pro 1С
sudo systemctl stop postgrespro-1c-17
sudo rm -rf /var/lib/pgpro/1c-17/data
sudo LANG=ru_RU.UTF-8 /opt/pgpro/1c-17/bin/pg-setup initdb   # локаль берётся из LANG, переменные LC_* игнорируются [PGPro, pg-setup]
sudo systemctl start postgrespro-1c-17
```

Решение C — в кластере уже есть нужные базы: создать базу вручную из `template0` с явной локалью и зарегистрировать информационную базу в кластере 1С на уже существующую пустую базу (без флажка «Создать базу данных в случае её отсутствия») [практика; подтверждено 19.10.2026 («Руководство администратора» 8.3.27, 5.2.1.3.7, конспект `../its-docs/adm-gl05-spisok-infobaz.md`): если в существующей базе данных нет информационной базы, платформа инициализирует в ней новую. Привилегия `SUPERUSER` на момент создания информационной базы нужна и в этом случае — см. 3.1]:

```sql
CREATE DATABASE buh TEMPLATE template0 ENCODING 'UTF8'
       LC_COLLATE 'ru_RU.UTF-8' LC_CTYPE 'ru_RU.UTF-8' OWNER dbuser;
```

Сопутствующее ограничение [1С]: у существующей базы на PostgreSQL «Язык (Страна)» информационной базы можно менять только на значение с тем же порядком сортировки строк СУБД (русский → белорусский можно, русский → украинский нельзя).

Сообщение «**Ошибка СУБД: DATABASE не пригоден для использования**» при создании или подключении базы (⚠ не подтверждено первоисточником; по сообщениям сообщества) связано с тем же кругом причин: локаль/кодировка кластера не соответствует ожидаемой платформой либо база создана не средствами 1С в неподходящей сборке. Порядок проверки — тот же: сборка (раздел 4.1), локаль кластера, журнал PostgreSQL в момент попытки.

### 3.3. База занята

```text
ERROR:  database "buh" is being accessed by other users
DETAIL:  There are 3 other sessions using the database.
```

Возникает при `DROP DATABASE`, `ALTER DATABASE … RENAME/SET TABLESPACE`, при `CREATE DATABASE … TEMPLATE buh` (шаблон не должен иметь других подключений [PG]), при удалении информационной базы из кластера 1С с удалением базы СУБД. Соединения держат рабочие процессы 1С (пул), фоновые задания, `psql`/pgAdmin, резервное копирование.

```bash
# 1. Закрыть доступ со стороны 1С и завершить сеансы (см. kb/1c/03)
rac infobase update --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd=… \
    --sessions-deny=on --scheduled-jobs-deny=on
rac session list --cluster=$CL --infobase=$IB
rac session terminate --cluster=$CL --session=<uuid>
```

```sql
-- 2. Кто подключён
SELECT pid, usename, application_name, client_addr, state FROM pg_stat_activity WHERE datname = 'buh';
-- 3. Запретить новые подключения и завершить существующие
ALTER DATABASE buh ALLOW_CONNECTIONS false;
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'buh' AND pid <> pg_backend_pid();
-- 4. Удалить. PostgreSQL 13+: одной командой с принудительным отключением
DROP DATABASE buh WITH (FORCE);
```

```bash
sudo -u postgres dropdb --force buh        # то же из оболочки (13+)
```

Если базу не удаляют, а, например, переименовывают — после операции верните `ALTER DATABASE … ALLOW_CONNECTIONS true;`.

### 3.4. Прочие ошибки создания и загрузки

| Симптом | Причина | Решение |
|---|---|---|
| `ERROR: database "buh" already exists` | База с таким именем уже есть | Регистрировать информационную базу на существующую базу либо выбрать другое имя |
| `ERROR: source database "template1" is being accessed by other users` | К `template1` подключён `psql`/pgAdmin/мониторинг | Закрыть подключения к `template1` |
| `could not initialize database directory` при `CREATE DATABASE` | Нет прав на каталог данных, диск заполнен, сбой файловой системы [PG] | `df -h`, `df -i`, владелец каталога — `postgres` |
| Имя базы отвергается | Имя длиннее 63 символов, содержит пробелы или совпадает с зарезервированным словом [1С] | Имя из латинских букв, цифр и `_`, начинается с буквы |
| Загрузка `.dt` идёт часами, растёт `pg_wal` | Загрузка — одна большая операция записи; мало `max_wal_size`, частые контрольные точки, медленный `fsync` | На время загрузки: `max_wal_size = 8GB..16GB`, `synchronous_commit = off`, `maintenance_work_mem` побольше; после загрузки — `vacuumdb --analyze` |
| При загрузке `.dt` или записи больших двоичных данных: `ERROR: invalid memory alloc request size …` либо `out of memory … Failed on request of size …` | Упор в предел 1 ГБ на значение поля и на один кусок памяти (раздел 9) | Не решается настройками; переносить базу средствами СУБД (`pg_dump`/`pg_restore`), большие файлы хранить вне базы |
| Информационная база создалась, но первый запуск очень долгий | Холодный кэш, загрузка конфигурации, построение кэшей сервера 1С | Норма для первого входа; повторный вход должен быть быстрым |

---

## 4. Расширения, типы данных и перенос дампов между сборками

### 4.1. Каталог ошибок

| № | Текст | Причина | Диагностика | Решение |
|---|---|---|---|---|
| 1 | `ERROR: type "mvarchar" does not exist` (вариант: `type "mchar" does not exist`) при создании базы или восстановлении дампа | Ванильный PostgreSQL (пакеты Ubuntu/PGDG) либо в целевой базе не созданы расширения | `SELECT version();` `\dx`; запрос к `pg_available_extensions` — ниже | Поставить сборку для 1С (`01-sborki-postgresql-dlya-1c-ustanovka.md`). Если сборка верная, а база создана вручную — `CREATE EXTENSION mchar; CREATE EXTENSION fulleq; CREATE EXTENSION fasttrun;` до загрузки данных |
| 2 | `ERROR: could not open extension control file "/usr/share/postgresql/17/extension/mchar.control": No such file or directory` | В установленной сборке нет расширения — это ванильный PostgreSQL | То же | Сборка для 1С |
| 3 | `ERROR: could not access file "$libdir/mchar": No such file or directory` | Восстановление дампа, в котором функции типов ссылаются на библиотеку `mchar`, в сборку без неё | Содержимое каталога библиотек (команды ниже) | Сборка для 1С |
| 4 | `ERROR: could not load library "/usr/lib/postgresql/17/lib/mchar.so": libicuuc.so.70: cannot open shared object file: No such file or directory` (аналогично для `fasttrun.so`, `fulleq.so`, `online_analyze.so`) | Библиотека есть, но не находит свою зависимость: сборка собрана под другой выпуск Ubuntu (другая версия ICU) либо ОС обновлена до нового выпуска | `ldd /usr/lib/postgresql/17/lib/mchar.so \| grep 'not found'` | Поставить сборку под текущий выпуск Ubuntu; временно — доустановить нужный `libicuNN` (22.04 — `libicu70`, 24.04 — `libicu74`, 26.04 — `libicu78`) |
| 5 | PostgreSQL не запускается: `FATAL: could not access file "online_analyze": No such file or directory` (так же для `plantuner`, `auto_dump`, `pg_stat_statements`, `pg_prewarm`) | В `shared_preload_libraries` указана библиотека, которой нет в этой сборке (конфигурация перенесена с другого сервера) | `sudo journalctl -u postgresql@17-main -n 30`; `ls /usr/lib/postgresql/17/lib/` (Postgres Pro: `/opt/pgpro/1c-17/lib/`) | Исправить `shared_preload_libraries` в `postgresql.conf` **и** в `postgresql.auto.conf` (если задавалось через `ALTER SYSTEM`), запустить |
| 6 | PostgreSQL не запускается: `unrecognized configuration parameter "enable_temp_rd_buffers"` (или `enable_temp_memory_catalog`, `stats_temp_directory` и т. п.), затем `FATAL: configuration file "…postgresql.conf" contains errors` | Параметр есть только в другой сборке (патч 1С) либо удалён в новой версии | Журнал запуска | Убрать параметр; до перезапуска проверять `SELECT * FROM pg_file_settings WHERE error IS NOT NULL;` |
| 7 | `ERROR: function fasttruncate(unknown) does not exist` | В базе нет расширения `fasttrun` | `\dx` | `CREATE EXTENSION fasttrun;` в базе |
| 8 | `ERROR: operator does not exist: … == …` | В базе нет расширения `fulleq` | `\dx` | `CREATE EXTENSION fulleq;` |
| 9 | Журнал забит `WARNING: nonstandard use of \\ in a string literal`; запросы из техжурнала, выполненные в `psql`, возвращают 0 строк или `invalid input syntax for type bytea` | Не заданы `standard_conforming_strings = off` и `escape_string_warning = off`: 1С передаёт значения `bytea` в escape-формате с обратной косой чертой | `SHOW standard_conforming_strings;` | Задать оба параметра в конфигурации (умолчание PostgreSQL — `on`) [1С][PGPro]; в `psql` — `SET standard_conforming_strings = off;` перед запросом из техжурнала |
| 10 | `pg_upgrade`: `Your installation references loadable libraries that are missing from the new installation`, файл `loadable_libraries.txt` содержит `$libdir/mchar` и т. п. | Новый кластер создан ванильными бинарниками | Содержимое `loadable_libraries.txt` | Новый кластер — тоже сборкой для 1С |
| 11 | `pg_dump: error: aborting because of server version mismatch` | `pg_dump` старше сервера | `pg_dump --version` | Использовать `pg_dump` той же или более новой основной версии, чем сервер: `/usr/lib/postgresql/17/bin/pg_dump` |
| 12 | После добавления `online_analyze` в `shared_preload_libraries` всё замедлилось, журнал заполнен выводом `ANALYZE` | Умолчания модуля: `enable = on`, `verbose = on`, `table_type = 'all'`, `local_tracking = off` [PGPro] | `SHOW online_analyze.table_type;` | Убрать модуль (официально не рекомендуется с современными версиями 1С) либо задать параметры явно — раздел 6.3 |

Проверка сборки и расширений:

```bash
sudo -u postgres psql -Atc "select version();"
sudo -u postgres psql -c "select name, default_version, installed_version from pg_available_extensions
                          where name in ('mchar','fulleq','fasttrun','plantuner','online_analyze','auto_dump') order by 1;"
sudo -u postgres psql -d buh -c '\dx'                       # что создано в базе 1С: должны быть mchar, fulleq, fasttrun
LIBDIR=$(sudo -u postgres psql -Atc "select setting from pg_config where name = 'PKGLIBDIR'")
ls "$LIBDIR" | grep -E 'mchar|fulleq|fasttrun|online_analyze|plantuner|auto_dump|dbcopies'
for f in mchar fulleq fasttrun; do ldd "$LIBDIR/$f.so" | grep 'not found'; done    # пустой вывод = зависимости на месте
dpkg -l | grep -E 'postgres|pgpro|libpq|libicu'             # какие пакеты реально стоят
apt-mark showhold                                           # зафиксированы ли пакеты сборки 1С от замены ванильными
```

Подводный камень сборки от 1С [практика]: её пакеты называются так же, как в Ubuntu/PGDG (`postgresql-17`, `libpq5`), и `apt upgrade` может заменить их ванильными — после чего появляются ошибки 1–4. Профилактика: `sudo apt-mark hold postgresql-17 postgresql-client-17 libpq5`.

### 4.2. Перенос баз между сборками

| Откуда → куда | Логический дамп (`pg_dump` / `pg_restore`) | Физическая копия (каталог данных, `pg_basebackup`, `pg_upgrade`) |
|---|---|---|
| Сборка 1С → сборка 1С той же основной версии | да | да (тот же выпуск ОС — иначе раздел 8.4) |
| Сборка 1С → сборка 1С более новой основной версии | да | `pg_upgrade`, обе сборки с модулями 1С |
| Сборка 1С ↔ Postgres Pro 1С / Standard | да: модули `mchar`, `fulleq`, `fasttrun` в Postgres Pro встроены [PGPro] | не рассчитывать: разные сборки и патчи ядра (⚠ не подтверждено официальным описанием совместимости) |
| Сборка 1С / Postgres Pro → Postgres Pro Enterprise и обратно | да | в сторону Enterprise — только `pg_upgrade`: Enterprise хранит страницы таблиц в 64-битном формате и преобразует страницы кластера PostgreSQL или Postgres Pro Standard постепенно, при первом обращении после обновления; копия каталога данных, `pg_basebackup`, реплика — нет; из Enterprise обратно — только дамп (вывод из формата хранения). Уточнено 19.10.2026 по документации Postgres Pro Enterprise 17, страница `pg_upgrade`, «Примечания» |
| Сборка для 1С → ванильный PostgreSQL | нет: ошибки 1–3 из таблицы выше. Работать с 1С на ванильной сборке нельзя | нет |
| Ванильный → сборка для 1С | да (обычные базы; для 1С не имеет смысла) | нет |
| Любая СУБД → любая (в том числе MS SQL → PostgreSQL) | — | — ; только выгрузка/загрузка `.dt` средствами 1С либо специализированные инструменты миграции |

Практика восстановления дампа базы 1С на другой сервер:

```bash
# источник
sudo -u postgres /usr/lib/postgresql/17/bin/pg_dump -Fc -Z 3 -f /backup/buh.dump buh
# приёмник: пустая база из template0 с нужной локалью, затем загрузка (дамп сам создаст расширения)
sudo -u postgres createdb -T template0 -E UTF8 -l ru_RU.UTF-8 -O dbuser buh
sudo -u postgres pg_restore --no-owner --role=dbuser -j 4 -d buh /backup/buh.dump
sudo -u postgres vacuumdb --analyze -j 4 -d buh             # статистика после загрузки обязательна
```

- Частичный дамп отдельных таблиц (`pg_dump -t …`) для передачи разработчикам нужно загружать в базу, **созданную средствами 1С**, — иначе при создании таблиц будет ошибка об отсутствии типов [1С, ИТС 6011].
- Загрузку SQL-дампа удобно делать одной транзакцией с остановкой на первой ошибке: `psql -1 -v ON_ERROR_STOP=1 -d buh -f dump.sql` [1С, ИТС 6011].
- `pg_restore` работает с пустым `search_path`; для нестандартных типов Postgres Pro рекомендует полностью квалифицировать операторы в пользовательских объектах (представления, функции) [PGPro]. В базах 1С пользовательских объектов нет, поэтому на практике это касается только самодельных представлений и функций поверх таблиц 1С.
- После восстановления копии рабочей базы на тестовый сервер заблокируйте регламентные задания (`rac infobase update … --scheduled-jobs-deny=on`), иначе копия начнёт обмены и рассылки.

---

## 5. Память и лимиты ОС

### 5.1. `out of shared memory`

```text
ERROR:  out of shared memory
HINT:  You might need to increase max_locks_per_transaction.
```

- **Причина:** переполнена разделяемая таблица блокировок. Её ёмкость — `max_locks_per_transaction` объектов на каждый серверный процесс и каждую подготовленную транзакцию; это лимит на число **объектов** (таблиц, индексов), а не строк. Параметр ограничивает среднее: отдельная транзакция может занять больше, пока всё помещается в общую таблицу [PG]. Умолчание 64 (в PostgreSQL 19 — 128, причём ёмкость на единицу значения там вдвое меньше прежней [PG]).
- **Когда возникает в 1С:** транзакции, затрагивающие сотни и тысячи таблиц — реструктуризация, удаление данных информационной базы, `pg_dump` базы 1С (блокирует каждую таблицу), а также закрытие соединения, при котором в одной транзакции удаляются все его временные таблицы; при нехватке блокировок транзакция прерывается и временные таблицы остаются «потерянными» [PGPro].
- **Решение:** `max_locks_per_transaction = 256` [PGPro] или `512..2000` [1С] (большие конфигурации — ближе к 2000); **перезапуск** PostgreSQL; при `huge_pages = on` пересчитать `vm.nr_hugepages` (разделяемая память вырастет).

```bash
sudo -u postgres psql -c "SHOW max_locks_per_transaction;" -c "SHOW max_connections;" -c "SELECT count(*) AS locks_now FROM pg_locks;"
echo "max_locks_per_transaction = 512" | sudo tee /etc/postgresql/17/main/conf.d/91-locks.conf
sudo systemctl restart postgresql@17-main
```

### 5.2. `could not resize shared memory segment`

```text
ERROR:  could not resize shared memory segment "/PostgreSQL.1647543808" to 8388608 bytes: No space left on device
```

- **Причина:** не хватило динамической разделяемой памяти для параллельного запроса. В Linux это файлы в `/dev/shm` (`dynamic_shared_memory_type = posix`). Типично для контейнеров (у Docker `/dev/shm` по умолчанию 64 МБ) и при общем дефиците памяти [практика].
- **Диагностика:** `df -h /dev/shm`; `SHOW dynamic_shared_memory_type; SHOW max_parallel_workers_per_gather;`.
- **Решение для 1С:** `max_parallel_workers_per_gather = 0` — параллельные запросы для 1С отключают [PGPro]. Если параллелизм нужен: увеличить `/dev/shm` (`sudo mount -o remount,size=4G /dev/shm`; в Docker — `--shm-size=2g`), уменьшить `work_mem`.
- Родственный симптом [PG]: `WARNING: could not remove shared memory segment "/PostgreSQL.1450751626": No such file or directory` — systemd-logind удаляет IPC-объекты при выходе пользователя (`RemoveIPC`). Возникает, если `postgres` — не системный пользователь (создан вручную). Лечение: `RemoveIPC=no` в `/etc/systemd/logind.conf` и `sudo systemctl restart systemd-logind`.

### 5.3. OOM killer убил процесс `postgres`

Признаки:

```text
# журнал PostgreSQL
LOG:  server process (PID 12345) was terminated by signal 9: Killed
DETAIL:  Failed process was running: SELECT ...
LOG:  terminating any other active server processes
WARNING:  terminating connection because of crash of another server process
LOG:  all server processes terminated; reinitializing
LOG:  database system was not properly shut down; automatic recovery in progress
# журнал ядра
Out of memory: Killed process 12345 (postgres) total-vm:... anon-rss:...
```

В 1С в этот момент все сеансы получают ошибку СУБД (`server closed the connection unexpectedly` или `terminating connection because of crash of another server process`): после гибели одного серверного процесса PostgreSQL завершает **все** соединения и восстанавливается по WAL. Если убит главный процесс (postmaster), новые соединения не принимаются до перезапуска [PG].

```bash
sudo dmesg -T | grep -i -E 'out of memory|killed process|oom-kill'
sudo journalctl -k --since "-2h" | grep -i -E 'oom|killed process'
sudo grep -E 'terminated by signal|reinitializing|recovery' /var/log/postgresql/postgresql-17-main.log | tail
free -h; swapon --show
ps -eo pid,user,rss,comm --sort=-rss | head -n 15            # кто реально занимает память (rphost или postgres)
```

Причины и решения:

| Причина | Решение |
|---|---|
| Бюджет памяти посчитан от всей ОЗУ, а на той же ВМ работает сервер 1С (`rphost` занимает гигабайты) | Считать от памяти, доступной PostgreSQL: `shared_buffers` = (RAM − память 1С) / 4 [1С][PGPro]; ограничить память рабочих процессов в настройках кластера 1С |
| Большие `work_mem` × число операций × число соединений; `hash_mem_multiplier` (умолчание 2.0 с 15-й версии, в 14-й — 1.0) удваивает лимит для хеш-операций [PG] | `work_mem` 32–128 МБ, тяжёлым базам — точечно: `ALTER DATABASE … SET work_mem` |
| `temp_buffers` 256 МБ × сотни долгоживущих соединений пула 1С: локальные буферы выделяются по мере надобности до лимита и удерживаются сеансом [PG] | `temp_buffers` 32–128 МБ |
| Фрагментация памяти долгоживущих процессов | `Environment=MALLOC_MMAP_THRESHOLD_=8192` в unit-файле (drop-in) [1С][PGPro] |
| Гипервизор отобрал память (ballooning, динамическая память) | Статическая память у ВМ |
| Нет подкачки вовсе | Небольшой swap (2–4 ГБ) и `vm.swappiness = 1..10` [практика] |
| Запрос с ошибочным планом (хеш на миллиарды строк) | Найти запрос по `DETAIL: Failed process was running` и разбираться с планом (раздел 6) |

Защита главного процесса [PG]: строгий учёт памяти `vm.overcommit_memory = 2` — **только на выделенном сервере СУБД** (на совмещённой с 1С машине `rphost` начнёт получать ошибки выделения памяти [практика]); либо `oom_score_adj = -1000` для postmaster с переменными `PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj`, `PG_OOM_ADJUST_VALUE=0` для дочерних процессов. В Debian/Ubuntu-пакетах защита postmaster уже задана в unit-файле (подтверждено 11.10.2026 исходным текстом юнита `systemd/system/postgresql@.service` в репозитории postgresql-common на salsa.debian.org (строка `OOMScoreAdjust=-900`); ранее: не подтверждено: проверьте `systemctl cat postgresql@17-main | grep -i oom`). В сборке «PostgreSQL для 1С» юнит `postgrespro-1c-16.service` задаёт `OOMScoreAdjust=-1000`, `PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj` и `PG_OOM_ADJUST_VALUE=0` (сверено 19.10.2026 по содержимому пакета `postgrespro-1c-16-server` 16.14, разобранного 11.10.2026; проверка на сервере — `systemctl cat postgrespro-1c-16 | grep -i oom`).

### 5.4. `out of memory` и `invalid memory alloc request size`

| Текст | Смысл | Действия |
|---|---|---|
| `ERROR: out of memory` + `DETAIL: Failed on request of size N in memory context "…"` | ОС отказала процессу в памяти (строгий overcommit, исчерпание ОЗУ и swap, лимиты службы) | Раздел 5.3; `systemctl show postgresql@17-main -p MemoryMax -p LimitAS` |
| `ERROR: invalid memory alloc request size 1073741824` (число около 1 ГБ) при записи или чтении большого значения | Предел одного выделения памяти и одного значения поля — 1 ГБ [PG]; при передаче `bytea` в текстовом виде объём удваивается и более, поэтому практический потолок ниже (сотни мегабайт; ⚠ точный порог не подтверждён) | Не хранить в базе такие объёмы одним значением: файлы — в томах на диске (механизм «хранение файлов в томах» в типовых конфигурациях), крупные макеты и обработки — дробить |
| `ERROR: invalid memory alloc request size 18446744073709551613` (абсурдно большое число) при **чтении** | Повреждён заголовок длины значения в строке таблицы — признак повреждения данных | Раздел 8.3 |

### 5.5. `No space left on device` — пять разных ситуаций

| Текст | Что закончилось | Последствия | Действия |
|---|---|---|---|
| `ERROR: could not extend file "base/16385/24680": No space left on device` + `HINT: Check free disk space.` | Том с данными | Запрос отменён, сервер работает; данные не повреждаются [PG] | Освободить место, раздел 10 |
| `ERROR: could not write to file "base/pgsql_tmp/pgsql_tmp12345.0": No space left on device` | Том с временными файлами запросов | Запрос отменён | Раздел 5.7 |
| `PANIC: could not write to file "pg_wal/xlogtemp.12345": No space left on device` | Том с `pg_wal` | Сервер аварийно останавливается и не запускается, пока нет места; зафиксированные транзакции не теряются [PG] | Раздел 10.2 |
| `FATAL: could not create semaphores: No space left on device` + `DETAIL: Failed system call was semget(…)` | **Не диск**: лимит семафоров System V в ядре [PG]. **В Linux не встречается:** здесь PostgreSQL использует семафоры POSIX, семафоры System V не применяются (сверено 19.10.2026 по документации PostgreSQL 18, 18.4.1 «Shared Memory and Semaphores», раздел Linux) — сообщение относится к другим ОС | Сервер не запускается | На других ОС — увеличить лимит семафоров либо уменьшить `max_connections`; на Ubuntu `kernel.sem` трогать незачем |
| `could not resize shared memory segment … No space left on device` | `/dev/shm` | Запрос отменён | Раздел 5.2 |

Проверка места — всегда и блоки, и индексные дескрипторы: `df -h` и `df -i`. Том может быть «полон» при свободных гигабайтах, если закончились inode (миллионы мелких файлов техжурнала, сеансовых данных).

### 5.6. `Too many open files`

```text
ERROR:  could not open file "base/16385/24680": Too many open files
LOG:  out of file descriptors: Too many open files; release and retry
```

- **Причина:** лимит открытых файлов процесса (`LimitNOFILE` службы) ниже потребности либо исчерпан общесистемный `fs.file-max`. База 1С — это десятки тысяч файлов (таблица + индексы + TOAST), каждый серверный процесс держит открытыми до `max_files_per_process` файлов (умолчание 1000 [PG]; для 1С рекомендуют 8000 [1С] / 10000 [PGPro]). При упоре в лимит PostgreSQL начинает закрывать и переоткрывать файлы — производительность падает ещё до появления ошибок [1С].

```bash
PGPID=$(sudo head -1 /var/lib/postgresql/17/main/postmaster.pid)
sudo grep -i 'open files' /proc/$PGPID/limits               # лимит процесса
sudo ls /proc/$PGPID/fd | wc -l                             # открыто у postmaster
sysctl fs.file-nr fs.file-max                               # занято / максимум по системе
sudo -u postgres psql -c "SHOW max_files_per_process;"
sudo lsof -u postgres 2>/dev/null | wc -l                   # всего открыто процессами postgres (диагностика из статьи 1С)

sudo systemctl edit postgresql@17-main                      # добавить:
#   [Service]
#   LimitNOFILE=65536
sudo systemctl restart postgresql@17-main
```

### 5.7. Временные файлы съели диск

- Временные **файлы** появляются, когда сортировка, хеш или материализация не помещаются в `work_mem`; лежат в `base/pgsql_tmp/` (или в `temp_tablespaces`) и удаляются по окончании операции. Временные **таблицы** 1С — отдельное явление (память `temp_buffers`, файлы `t<N>_<filenode>` в каталоге базы).
- Десятки гигабайт временных файлов от одного запроса — почти всегда ошибочный план (декартово произведение, соединение без условия, сортировка огромного промежуточного результата).

```sql
SELECT name, pg_size_pretty(size) AS size, modification FROM pg_ls_tmpdir() ORDER BY size DESC LIMIT 20;   -- сейчас на диске
SELECT datname, temp_files, pg_size_pretty(temp_bytes) FROM pg_stat_database ORDER BY temp_bytes DESC;    -- накоплено
-- pid из имени файла pgsql_tmp<PID>.<N> → какой запрос
SELECT pid, now() - query_start AS dur, left(query, 200) FROM pg_stat_activity WHERE pid = 12345;
SELECT pg_cancel_backend(12345);                                                                          -- отменить запрос
```

Предохранитель [PG]: `temp_file_limit = 20GB` (умолчание `-1` — без предела). При превышении транзакция отменяется: `ERROR: temporary file size exceeds temp_file_limit (20971520kB)`. На временные таблицы лимит не распространяется. Значение в `temp_tablespaces`, указывающее на несуществующее пространство или пространство без права `CREATE`, молча игнорируется [PG].

### 5.8. `stack depth limit exceeded`

```text
ERROR:  stack depth limit exceeded
HINT:  Increase the configuration parameter "max_stack_depth" (currently 2048kB), after ensuring the platform's stack depth limit is adequate.
```

- **Причина:** слишком глубокая вложенность выражений в запросе: тысячи условий, соединённых `ИЛИ`/`И`, огромные сгенерированные запросы (ограничения доступа RLS, отборы, собранные в цикле, глубоко вложенные подзапросы).
- **Решение:** `max_stack_depth` должен быть меньше лимита стека ОС примерно на мегабайт; умолчание 2 МБ «консервативно мало» [PG]. Стандартный `ulimit -s` — 8 МБ, значит безопасно `max_stack_depth = 6MB` (достаточно `reload`). Больше — только вместе с лимитом службы: `LimitSTACK=32M` в drop-in и `max_stack_depth = 30MB`. Параллельно — исправлять запрос (список значений → временная таблица и соединение).

```bash
sudo grep -i 'stack' /proc/$(sudo head -1 /var/lib/postgresql/17/main/postmaster.pid)/limits
sudo -u postgres psql -c "ALTER SYSTEM SET max_stack_depth = '6MB';" -c "SELECT pg_reload_conf();"
```

### 5.9. Прочие лимиты

| Текст | Причина | Решение |
|---|---|---|
| `LOG: could not fork new process for connection: Cannot allocate memory` / `Resource temporarily unavailable` | Нет памяти для нового процесса (строгий overcommit) либо лимит числа процессов (`TasksMax`, `LimitNPROC`) | `systemctl show postgresql@17-main -p TasksMax -p LimitNPROC`; память — раздел 5.3 |
| Не стартует после `huge_pages = on`: `FATAL: could not map anonymous shared memory: Cannot allocate memory` | `vm.nr_hugepages` меньше потребности (выросли `shared_buffers`, `max_connections`, `max_locks_per_transaction`) | Пересчитать: `postgres -D … -C shared_memory_size_in_huge_pages` (сервер остановлен; параметр есть с 15-й версии), увеличить резерв; временно `huge_pages = try` |
| `FATAL: could not create shared memory segment: Invalid argument` + `shmget(…)` | Лимиты SysV-памяти; актуально только при `shared_memory_type = sysv` [PG] | Вернуть `mmap` (умолчание) |
| `LOG: could not bind IPv4 address "0.0.0.0": Address already in use` + `FATAL: could not create any TCP/IP sockets` | Порт занят другим экземпляром PostgreSQL [PG] | `sudo ss -tlnp \| grep 5432`; `pg_lsclusters`; развести порты |

---

## 6. Производительность

### 6.1. Сначала — где теряется время

| Наблюдение | Вывод | Дальше |
|---|---|---|
| Процессы `postgres` грузят CPU, в `pg_stat_activity` — `active` без ожиданий | Тяжёлые запросы, плохие планы | 6.2–6.4 |
| `wait_event_type = 'Lock'` у многих сеансов | Блокировки СУБД | Раздел 7 |
| `wait_event_type = 'IO'` (`DataFileRead`, `WALSync`, `WALWrite`), высокий `iowait` | Диск: чтение не из кэша либо медленная синхронная запись | 6.7, 6.9 |
| Сеансы `idle in transaction`, `wait_event = ClientRead` | PostgreSQL ждёт сервер 1С: код 1С работает внутри транзакции либо ждёт управляемую блокировку | Раздел 7, техжурнал |
| `postgres` простаивает, CPU занят `rphost` | Время уходит в код конфигурации на сервере 1С | Замер производительности в 1С, техжурнал `CALL` |
| Всё простаивает, а пользователи ждут | Управляемые блокировки 1С, сеть, лицензии, клиентская часть | Техжурнал `TLOCK`, раздел 7 |

```bash
top -b -n 1 -o %CPU | head -n 20                 # кто грузит процессор: postgres или rphost
vmstat 5 3                                       # wa — ожидание диска, si/so — подкачка, st — время, «украденное» гипервизором
iostat -x 5 3                                    # await, %util по дискам (пакет sysstat)
```

```sql
-- срез ожиданий: что сейчас делают клиентские соединения
SELECT state, wait_event_type, wait_event, count(*)
FROM pg_stat_activity WHERE backend_type = 'client backend' GROUP BY 1,2,3 ORDER BY 4 DESC;
-- самые затратные запросы (нужен pg_stat_statements в shared_preload_libraries)
SELECT calls, round(total_exec_time::numeric/1000, 1) AS total_s, round(mean_exec_time::numeric, 1) AS mean_ms,
       rows, left(query, 120) AS query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 15;
```

Оценка доли СУБД по технологическому журналу (метод [1С, ИТС 6011]: собрать полный ТЖ и сложить длительности по типам событий; если сумма `DBPOSTGRS` больше примерно половины суммы `CALL` — заниматься запросами). Длительность в ТЖ 8.3 — в микросекундах после дефиса в начале строки:

```bash
cat /var/log/1c/tj/rphost_*/*.log | awk -F'[-,]' '/^[0-9][0-9]:[0-9][0-9]\.[0-9]+-[0-9]+,/ {d[$3] += $2}
  END {for (e in d) printf "%-12s %12.1f sec\n", e, d[e]/1e6}' | sort -k2 -nr | head
```

### 6.2. Каталог проблем производительности

| № | Симптом | Причина | Как убедиться | Решение |
|---|---|---|---|---|
| 1 | Запрос с временными таблицами выполняется минуты, в плане `Nested Loop` с оценкой `rows=1` при фактических тысячах и миллионах | По временной таблице нет статистики: автоочистка временные таблицы не обрабатывает [PG] | `EXPLAIN (ANALYZE, BUFFERS)`: сравнить `rows=` в оценке и в `actual` | 6.3 |
| 2 | `Nested Loop` там, где нужен `Hash Join`; время растёт квадратично с объёмом | Ошибка оценки числа строк (устаревшая статистика, коррелированные условия, сложные выражения) | То же; `last_analyze`, `n_mod_since_analyze` в `pg_stat_user_tables` | 6.4 |
| 3 | Один и тот же запрос то быстрый, то медленный | 12 и больше элементов во `FROM` → генетический оптимизатор (`geqo_threshold = 12`: GEQO включается при «не менее» этого числа [PG]) выбирает разные планы; либо «плавает» статистика | Число соединений в запросе; `SHOW geqo_threshold` | 6.4 |
| 4 | Полное сканирование большой таблицы при наличии индекса | `random_page_cost = 4` на SSD, занижен `effective_cache_size`; условие с `ИЛИ`; функция или приведение типа над индексируемым полем | План: `Seq Scan` + `Filter` | `random_page_cost = 1.1..1.3` для SSD, `effective_cache_size = RAM − shared_buffers` [1С][PGPro]; переписать условие |
| 5 | Медленные запросы с `ИЛИ` в условиях соединения или отбора | Планировщик не может использовать один индекс, уходит в `BitmapOr` или полное сканирование | План | В запросе 1С разбить на части через `ОБЪЕДИНИТЬ ВСЕ` [1С] |
| 6 | Медленные соединения с вложенным запросом или виртуальной таблицей (`СрезПоследних`, `Остатки`, `Обороты`) | Подзапрос не имеет статистики и индексов, оценка числа строк произвольна | План: `Subquery Scan`, вложенные циклы по подзапросу | Вынести подзапрос / виртуальную таблицу во временную таблицу с индексом и соединяться с ней [1С, ИТС 4208]; отборы задавать параметрами виртуальной таблицы, а не в `ГДЕ` |
| 7 | Запрос с `В (&Список)` на тысячи значений долго планируется и выполняется | Огромный литеральный список в тексте запроса | Длина текста запроса в ТЖ | Поместить список во временную таблицу и соединиться |
| 8 | Запросы с `ПОЛНОЕ ВНЕШНЕЕ СОЕДИНЕНИЕ` медленные | PostgreSQL поддерживает `FULL JOIN` не для любых условий, платформа преобразует такой запрос в эквивалентную, но менее эффективную форму; конструкция при работе с PostgreSQL не рекомендуется [1С, ИТС 1556 — статья 2010 года] | Текст запроса | Переписать без полного соединения (обычно — левые соединения и `ОБЪЕДИНИТЬ ВСЕ`) |
| 9 | Быстрые запросы стали заметно медленнее, в `EXPLAIN ANALYZE` есть раздел `JIT:` с сотнями миллисекунд | JIT-компиляция включена (умолчание `on` в 12–18) | `SHOW jit;` | `jit = off` [1С][PGPro] |
| 10 | Простые запросы медленнее, чем раньше; ошибки `/dev/shm` | Параллельное выполнение (`max_parallel_workers_per_gather = 2` по умолчанию) | План: `Gather`, `Parallel Seq Scan` | `max_parallel_workers_per_gather = 0` [PGPro] |
| 11 | Проведение документов медленное у всех | Медленная фиксация транзакций (`fsync`), блокировки, раздувание таблиц итогов | `pg_test_fsync`; `wait_event = WALSync`; ТЖ `TLOCK` | 6.5 |
| 12 | Обновление конфигурации (реструктуризация) идёт часами | Стандартный механизм копирует таблицы целиком; мало `maintenance_work_mem`, частые контрольные точки | `pg_stat_progress_create_index`, журнал контрольных точек | 6.6 |
| 13 | После перезапуска PostgreSQL или ВМ первые часы всё медленно | Холодный кэш: `shared_buffers` пуст, страничный кэш ОС пуст | `pg_stat_database`: низкая доля `blks_hit` | 6.7 |
| 14 | База растёт без роста данных; запросы к «маленьким» таблицам медленные | Раздувание: автоочистка выключена или не успевает; горизонт очистки удерживает длинная транзакция, слот, подготовленная транзакция | `n_dead_tup`, `last_autovacuum`; возраст `backend_xmin` | 6.8 |
| 15 | Любые запросы с временными таблицами замедлились, `pg_class`, `pg_attribute`, `pg_type`, `pg_depend`, `pg_statistic` — сотни мегабайт и гигабайты | Раздувание системного каталога от постоянного создания и удаления временных таблиц | Запрос размеров каталога — 6.8 | 6.8 |
| 16 | Раз в несколько минут система «замирает» на секунды | Залповый сброс «грязных» страниц ОС или частые контрольные точки по объёму WAL | `LOG: checkpoints are occurring too frequently`; `pg_stat_checkpointer` (17+) | `max_wal_size` ↑, `checkpoint_timeout = 15min` [PGPro], `vm.dirty_background_bytes`/`vm.dirty_bytes` |
| 17 | Низкая скорость одного потока, тест Гилева показывает низкий индекс на мощном сервере | Энергосбережение CPU, переподписка vCPU, медленная синхронная запись | 6.9 | 6.9 |
| 18 | Память «утекает», подкачка, периодические OOM | Раздел 5.3 | `free -h`, `vmstat` (`si/so`) | Раздел 5.3 |
| 19 | Под нагрузкой высокая системная загрузка CPU при большом `shared_buffers` | Нет huge pages; включены Transparent Huge Pages | `grep -i huge /proc/meminfo`; `cat /sys/kernel/mm/transparent_hugepage/enabled` | `huge_pages = on` с расчётом резерва, THP — `never`/`madvise` (`02-postgresql-conf-tyuning-dlya-1c.md`, раздел 7) |
| 20 | Всё медленно после включения диагностики | `log_min_duration_statement = 0`, `auto_explain.log_analyze`, `<plansql/>` в техжурнале | `SHOW log_min_duration_statement;` `logcfg.xml` | Вернуть пороги; `<plansql/>` на продуктиве запрещён [1С, ИТС 6011] |
| 21 | Медленно сразу после восстановления дампа, `pg_upgrade` (до 18-й версии) или массовой загрузки | Нет статистики оптимизатора | `last_analyze IS NULL` | `vacuumdb --analyze-in-stages -j 4 -d buh`; с 18-й версии `pg_upgrade` переносит статистику (кроме расширенной) [PG] |
| 22 | После переноса с MS SQL «всё стало медленнее» | Автоматический режим блокировок (раздел 7.1); конфигурация PostgreSQL по умолчанию; запросы, написанные под оптимизатор MS SQL (пункты 5–8) | — | Настроить PostgreSQL по рекомендациям [1С][PGPro], перевести конфигурацию в управляемый режим, оптимизировать проблемные запросы |
| 23 | Медленное соединение 1С ↔ СУБД при малой загрузке обоих | Включён SSL; разрешение имён; сервер 1С и СУБД в разных сетях | `SHOW ssl;` `ping`, `mtr` | `ssl = off` [1С]; сервер 1С и СУБД — рядом |

### 6.3. Временные таблицы и статистика

Как платформа работает с временными таблицами (видно в технологическом журнале, событие `DBPOSTGRS`) [1С, ИТС 6011]:

```sql
create temporary table tt7 (_Q_000_F_000RRef bytea) without oids;
create index tmpind_0 on pg_temp.tt7(_Q_000_F_000RRef);
INSERT INTO pg_temp.tt7 ... SELECT ...;
ANALYZE pg_temp.tt7;
```

- Современные версии платформы сами выполняют `ANALYZE` временной таблицы после заполнения — поэтому модуль `online_analyze` с современными версиями 1С не рекомендуется [PGPro]; в рекомендациях 1С он по умолчанию выключен (`online_analyze.enable = off`) и включается, только если фоновое обновление статистики не справляется и оптимизатор часто ошибается [1С].
- `plantuner.fix_empty_table = on` заставляет планировщик считать только что созданную пустую таблицу пустой, а не «таблицей неизвестного размера» — рекомендуется [PGPro].
- Очистка временных таблиц идёт через `fasttruncate()` (модуль `fasttrun`) — без роста `pg_class` [PGPro].

```ini
# рекомендуемый минимум [PGPro]
shared_preload_libraries = 'plantuner'
plantuner.fix_empty_table = on

# online_analyze — только при доказанной необходимости; умолчания модуля вредны, задавать явно [1С][PGPro]
# shared_preload_libraries = 'online_analyze, plantuner'
# online_analyze.enable = on
# online_analyze.table_type = 'temporary'
# online_analyze.verbose = off
# online_analyze.local_tracking = on
# online_analyze.threshold = 50
# online_analyze.scale_factor = 0.1
# online_analyze.min_interval = 10000
```

В сборке «PostgreSQL с патчем от 1С» есть два параметра для нагруженных систем (оба по умолчанию `off`) [1С]: `enable_temp_memory_catalog` (с 16.4; строки системного каталога для временных таблиц — в памяти; нужен перезапуск; выгоден, когда диск перегружен, а процессор свободен) и `enable_temp_rd_buffers` (с 17.5-11.1C и 16.9-34.1C; файл временной таблицы не создаётся, пока данные не превысят 32 Кб; растёт потребление памяти).

### 6.4. Неверные оценки планировщика: порядок действий

1. **Получить план «как у платформы».** Взять текст запроса из события `DBPOSTGRS`, в `psql` задать параметры сеанса платформы и выполнить под `EXPLAIN` [1С, ИТС 6011]:

   ```sql
   SET client_min_messages = error;
   SET lc_messages TO 'en_US.UTF-8';
   SET enable_mergejoin = off;
   SET escape_string_warning = off;
   SET cpu_operator_cost = 0.001;
   SET client_encoding = 'utf8';
   SET lock_timeout = 20000;
   SET standard_conforming_strings = off;      -- если не задан на сервере: иначе литералы bytea из ТЖ прочитаются неверно
   EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
   SELECT ...;                                 -- запрос из техжурнала; временные таблицы предварительно создать, заполнить и ANALYZE
   ```

   Для пакетных запросов с временными таблицами в сборках 1С есть расширение `auto_dump` — оно само выгружает таблицы, текст запроса и план [1С, ИТС 6031/6039]. Условия срабатывания различаются по сборкам: в «PostgreSQL с патчем от 1С» (`auto_dump` 1.1) — `dump_on_query_string`, `dump_on_cancel`, `dump_on_bad_plan`, `dump_on_duration`; в «PostgreSQL для 1С» от Postgres Professional 16 параметра `dump_on_duration` нет, вместо него `dump_on_time` + `timeout` (мс), а нулевые пороги `bad_plan_*` означают «срабатывать всегда» (сверено 19.10.2026 по документации сборки 16, F.5, и конспекту `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`). На сервере сверить: `SELECT name, setting FROM pg_settings WHERE name LIKE 'auto_dump.%';` (после загрузки библиотеки).
2. **Найти узел с расхождением** между оценкой (`rows=`) и фактом (`actual … rows=`) в десятки раз и более — ошибка начинается с самого нижнего такого узла.
3. **Статистика.** `ANALYZE` проблемных таблиц; проверить автоанализ (`autovacuum_analyze_scale_factor`: умолчание 0.1 — для таблиц в десятки миллионов строк это редко, уменьшайте до 0.01–0.02 [практика]). Точность: `default_statistics_target` (умолчание 100) до 300–1000 [практика]. Учтите: 1С при реструктуризации пересоздаёт таблицы, поэтому настройки уровня колонки (`ALTER TABLE … SET STATISTICS`) и объекты `CREATE STATISTICS` теряются.
4. **Параметры планировщика** [1С][PGPro]: `from_collapse_limit = 20`, `join_collapse_limit = 20`, `geqo = on`, `geqo_threshold = 12`, `random_page_cost` под диски, `effective_cache_size`. Postgres Pro дополнительно рекомендует `enable_sorted_merge_join = off` (параметр есть только в Postgres Pro).
5. **Переписать запрос в конфигурации** (пункты 5–8 таблицы 6.2) — самый надёжный способ.
6. **Диагностические переключатели** — только в сеансе, чтобы доказать причину: `SET enable_nestloop = off;` и сравнить время. Глобально выключать вложенные циклы нельзя: это ломает быстрые точечные запросы.
7. **Обновить минорную версию сборки**: сборки 1С и Postgres Pro содержат патчи планировщика под запросы 1С, состав которых меняется от выпуска к выпуску.
8. Крайняя мера в Postgres Pro Standard/Enterprise — `pg_hint_plan` с `pg_hint_plan.hints_anywhere = on` [PGPro, Postgres Pro 17, K.4.6]. В бесплатной сборке «PostgreSQL для 1С» (в том числе 16) модуля `pg_hint_plan` нет — его нет ни в перечне модулей её документации (приложение F), ни в индексе пакетов репозитория 1c-16 для Ubuntu 22.04 и 24.04 (сверено 19.10.2026).

### 6.5. Медленное проведение документов

```bash
# скорость синхронной записи журнала — главный ограничитель коротких транзакций
sudo -u postgres /usr/lib/postgresql/17/bin/pg_test_fsync -f /var/lib/postgresql/17/main/pg_test_fsync.tmp
# сотни операций в секунду у fdatasync — диск без кэша записи или «честный» fsync в ВМ; тысячи и десятки тысяч — норма для SSD
```

- `synchronous_commit = off` — официальная рекомендация для 1С: возможна потеря транзакций за последние 0.5–1 с при сбое, целостность базы сохраняется [1С][PGPro]. `fsync = on` оставлять всегда.
- Ожидания на блокировках: сначала управляемые (ТЖ `TLOCK` с `WaitConnections`), затем СУБД (раздел 7).
- Таблицы итогов регистров раздуваются и конкурируют за строки: проверить автоочистку по ним, включить разделение итогов в конфигурации, периодически пересчитывать итоги средствами 1С.
- Длинная транзакция проведения держит блокировки и горизонт очистки: искать `xact_age` в `pg_stat_activity`.
- Раздувшиеся индексы таблиц движений — `REINDEX (CONCURRENTLY)` в окно обслуживания (`05-obsluzhivanie-vacuum-analyze-reindex.md`).

### 6.6. Медленная реструктуризация

- Стандартный механизм (`v1`) создаёт новую таблицу и переносит в неё данные; оптимизированный (`v2`) переносит основную работу на сторону СУБД (⚠ описание механизма — по материалам сообщества) и доступен для клиент-серверных баз на MS SQL Server и PostgreSQL. Выбор: ключ `-v2` у `/UpdateDBCfg` либо `UpdateDBCfg=v2` в `conf.cfg` на компьютере, где запущен конфигуратор; на серверах кластера нужна Java 1.8+ [1С].
- Места на диске нужно не меньше размера самой большой изменяемой таблицы с индексами плюс WAL за время операции.
- На время обновления [практика]: `maintenance_work_mem = 1GB..4GB` (построение индексов), `max_wal_size = 8GB..16GB`, `synchronous_commit = off`; не запускать одновременно `pg_dump` и тяжёлые отчёты — DDL реструктуризации требует блокировок `ACCESS EXCLUSIVE` и упрётся в `lock_timeout` (раздел 7.3).
- После обновления — `vacuumdb --analyze -d buh`: новые таблицы без статистики.

```sql
SELECT pid, phase, blocks_done, blocks_total, tuples_done, tuples_total FROM pg_stat_progress_create_index;
SELECT pid, now() - xact_start AS xact_age, wait_event_type, wait_event, left(query, 100)
FROM pg_stat_activity WHERE state <> 'idle' ORDER BY xact_start;
```

### 6.7. Холодный кэш после перезапуска

- После перезапуска PostgreSQL `shared_buffers` пуст; после перезагрузки ВМ пуст и страничный кэш ОС — первые обращения читают с диска.
- Автопрогрев [PG]: добавить `pg_prewarm` в `shared_preload_libraries` — фоновый процесс каждые `pg_prewarm.autoprewarm_interval` (300 с) сохраняет список буферов в файл `autoprewarm.blocks` и после перезапуска загружает их обратно.
- Ручной прогрев таблицы: `CREATE EXTENSION pg_prewarm; SELECT pg_prewarm('_accumrgt12345');`.
- Отдельно прогревается сервер 1С: первый вход после перезапуска кластера строит кэши конфигурации — для крупных конфигураций это минуты, и это не проблема СУБД.

```ini
shared_preload_libraries = 'plantuner, pg_prewarm, pg_stat_statements'
```

### 6.8. Автоочистка и раздувание

```sql
-- где больше всего мёртвых строк и когда их чистили
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
-- кто удерживает горизонт очистки
SELECT pid, state, now() - xact_start AS xact_age, age(backend_xmin) AS xmin_age, left(query, 80)
FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER BY age(backend_xmin) DESC LIMIT 10;
SELECT slot_name, active, age(xmin) AS xmin_age, age(catalog_xmin) AS catalog_xmin_age FROM pg_replication_slots;
SELECT gid, prepared, age(transaction) FROM pg_prepared_xacts;
-- размер системного каталога (раздувается от временных таблиц)
SELECT c.relname, pg_size_pretty(pg_total_relation_size(c.oid)) AS size
FROM pg_class c WHERE c.relnamespace = 'pg_catalog'::regnamespace AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 8;
```

- `autovacuum = on` всегда; `autovacuum_max_workers` — от ядер/4 до ядер/2, но не меньше 4; `autovacuum_naptime = 20s` [1С][PGPro]. Умолчания PostgreSQL (3 процесса, 1 минута, 20 % таблицы [PG]) для 1С слабы.
- Автоочистка «мешает» днём — не выключать, а ускорять: `autovacuum_vacuum_cost_limit = 1000..2000` на SSD, меньший `autovacuum_vacuum_scale_factor` (0.01–0.05) для больших таблиц [практика]. Даже при `autovacuum = off` система запускает автоочистку для защиты от зацикливания счётчика транзакций [PG].
- Каталог в гигабайтах: в окно обслуживания при остановленном сервере 1С — `VACUUM FULL pg_class; VACUUM FULL pg_attribute; VACUUM FULL pg_type; VACUUM FULL pg_depend; VACUUM FULL pg_statistic;` в базе 1С, затем разобраться, почему автоочистка каталога не справлялась (длинные транзакции).

### 6.9. Процессор, диск и виртуальная машина

- Официально: отключить HyperThreading и энергосбережение (иначе задержки ответов растут непредсказуемо), не допускать вытеснения разделяемой памяти в подкачку [1С][PGPro].
- В ВМ частотой процессора управляет **хост**: на Windows-хосте — схема «Высокая производительность» (`powercfg /setactive SCHEME_MIN`, проверка `powercfg /getactivescheme`), в BIOS/UEFI — профиль максимальной производительности. Внутри гостя каталог `/sys/devices/system/cpu/cpu0/cpufreq` обычно отсутствует.
- Не выдавать ВМ больше vCPU, чем есть физических ядер; столбец `st` в `vmstat` больше нескольких процентов — хост перегружен.
- Память ВМ — статическая. Динамическая память и ballooning: гость внезапно теряет память (OOM, подкачка), ломаются huge pages, а у программных лицензий 1С меняются ключевые параметры компьютера [1С][практика].
- Диск ВМ: фиксированный (не динамически расширяемый) виртуальный диск на SSD хоста, исключения антивируса для файлов виртуальных дисков, кэш записи хоста — только при защите питания [практика].
- Быстрая проверка «железа»: `pg_test_fsync` (диск), `pg_test_timing` (таймер), однопоточный тест (например, тест Гилева) — он чувствителен именно к частоте ядра, энергосбережению и накладным расходам виртуализации, а не к `postgresql.conf` [практика].

---

## 7. Блокировки

### 7.1. Как устроены блокировки 1С на PostgreSQL

Режим задаётся свойством конфигурации «Режим управления блокировкой данных» (и свойствами отдельных объектов); администратор СУБД изменить его не может — это доработка конфигурации.

| Режим конфигурации | Уровень изоляции транзакций | Блокировки СУБД | Кто обеспечивает согласованность |
|---|---|---|---|
| Автоматический | Serializable | **таблицы целиком** | СУБД |
| Управляемый | Read Committed | строки | менеджер управляемых блокировок кластера 1С (`rmngr`) |
| Автоматический и управляемый | по режиму конкретного объекта | смешанно | — |

Источник таблицы — документация платформы, раздел о блокировках данных [1С] (в базе знаний приведена в `06-monitoring-i-diagnostika-zaprosov.md`, раздел 3.1; сверено 19.10.2026 с «Руководством разработчика» 8.3.27, 9.2.3.2 — конспект `../its-docs/dev-gl09-rabota-s-dannymi.md`: для PostgreSQL автоматический режим — блокировки таблиц и Serializable, управляемый — блокировки записей и Read Committed). Что из этого следует:

- **Автоматический режим на PostgreSQL** — транзакция, работающая с таблицей, блокирует её для других пишущих транзакций до своего завершения. Два пользователя не могут одновременно проводить документы, пишущие в один регистр. На MS SQL Server в том же режиме блокируются записи и диапазоны, поэтому при переносе базы «как есть» с MS SQL параллельность резко падает. Это не дефект настройки PostgreSQL и параметрами не лечится.
- В терминах PostgreSQL такая блокировка — сильная блокировка отношения, совместимая только с чтением (режим `EXCLUSIVE` «допускает параллельно только блокировки `ACCESS SHARE`, то есть только чтение» [PG]); читающие вне транзакции запросы не ждут — PostgreSQL версионная СУБД. Точный текст команды, которой платформа ставит блокировку (ожидаемо `LOCK TABLE … IN EXCLUSIVE MODE`), — **⚠ не подтверждено**; проверить на своей системе можно так:

```bash
grep -rhi --include='*.log' 'lock table' /var/log/1c/tj | head          # нужен ТЖ с событиями DBPOSTGRS
```

```sql
-- сильные блокировки таблиц и возраст транзакций, которые их держат
SELECT l.pid, l.mode, l.granted, c.relname, now() - a.xact_start AS xact_age, left(a.query, 80) AS query
FROM pg_locks l
JOIN pg_class c ON c.oid = l.relation
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE l.locktype = 'relation' AND c.relname !~ '^pg_'
  AND l.mode IN ('ShareLock', 'ShareRowExclusiveLock', 'ExclusiveLock', 'AccessExclusiveLock')
ORDER BY a.xact_start;
```

- **Управляемый режим** — блокировки ставит прикладной код (`БлокировкаДанных`) и платформа при записи объектов; СУБД работает на Read Committed с короткими блокировками строк. Позиция разработчиков платформы: при управляемом режиме ожиданий на уровне PostgreSQL быть не должно — только на управляемых блокировках; каждый воспроизводимый случай ожидания именно в PostgreSQL следует документировать и отправлять в поддержку (v8@1c.ru, корпоративным клиентам — CorpTechSupport@1c.ru), не прекращая собственного расследования [1С].
- **Таймаут.** Параметр информационной базы «Время ожидания блокировки данных» (по умолчанию 20 секунд) действует на оба уровня: для управляемых блокировок — в менеджере блокировок, для СУБД — платформа выполняет `SET lock_timeout = 20000` [1С, ИТС 6011]. Изменение параметра требует административных прав и монопольного доступа, для PostgreSQL применяется сразу [1С].
- Все современные типовые конфигурации работают в управляемом режиме. Автоматический режим встречается в старых и самописных конфигурациях; перевод в управляемый — задача разработчика (нужна расстановка управляемых блокировок в коде).

### 7.2. Каталог ошибок и состояний

| № | Симптом | Причина | Диагностика | Решение |
|---|---|---|---|---|
| 1 | «Конфликт блокировок при выполнении транзакции: Превышено максимальное время ожидания предоставления блокировки» | Таймаут **управляемой** блокировки 1С. В PostgreSQL ожидающий сеанс выглядит как `idle in transaction` / `ClientRead` | ТЖ: `TTIMEOUT`, `TLOCK` с `WaitConnections`; `rac session list` — поле `blocked-by-ls` | Сократить транзакции, сузить области блокировок (разработчик); не запускать тяжёлые групповые операции в рабочее время |
| 2 | «Конфликт блокировок при выполнении транзакции: `ERROR: canceling statement due to lock timeout`», часто с `CONTEXT: while updating tuple (…) in relation "…"` | Таймаут блокировки **СУБД**: автоматический режим (таблицы); конкуренция за одни строки (итоги регистров); DDL реструктуризации ждёт `pg_dump` или длинный отчёт; обслуживание с `ACCESS EXCLUSIVE` | Журнал PostgreSQL при `log_lock_waits = on`; `pg_blocking_pids()`; `rac` — поле `blocked-by-dbms`; ТЖ с `<dbmslocks/>` | 7.3–7.5 |
| 3 | «Конфликт блокировок при выполнении транзакции:» + `ERROR: deadlock detected` (уточнено 19.10.2026 по ИТС, см. 1.1; «Неустранимый конфликт блокировок» — это взаимоблокировка управляемых блокировок, событие `TDEADLOCK`) | Взаимоблокировка: транзакции захватывают одни и те же ресурсы в разном порядке. PostgreSQL обнаруживает её через `deadlock_timeout` (1 с) и прерывает одну из транзакций [PG] | В журнале PostgreSQL — оба процесса и их запросы; ТЖ: `EXCP` с текстом ошибки (событие `TDEADLOCK` формируется только для управляемых блокировок) | Единый порядок захвата ресурсов, исключительная управляемая блокировка до чтения (разработчик); повтор операции пользователем |
| 4 | Сеансы в состоянии `idle in transaction` минутами и часами | Транзакция открыта, сервер 1С не шлёт запросов: длительный код внутри транзакции, ожидание управляемой блокировки, зависший `rphost` или фоновое задание, остановка в отладчике внутри транзакции | Запрос ниже; сопоставить `pid` с `dbpid` в ТЖ и с `db-proc-info` в `rac session list` | Завершить сеанс 1С (`rac session terminate`) или `pg_terminate_backend(pid)`; найти код по ТЖ |
| 5 | `VACUUM FULL`, `REINDEX`, `ALTER TABLE`, запущенные администратором, «висят», а за ними встают все запросы к таблице | Команда ждёт `ACCESS EXCLUSIVE` за длинной транзакцией; новые запросы встают в очередь за ней. У сеанса администратора нет `lock_timeout` | `pg_blocking_pids()` | Отменить команду; перед обслуживанием в своём сеансе: `SET lock_timeout = '5s';` |
| 6 | В журнале: `ERROR: canceling autovacuum task` + `CONTEXT: automatic vacuum of table "…"` | Автоочистка уступила конфликтующему запросу блокировки (DDL) — штатное поведение | Частота сообщений по одной таблице | Если постоянно по одной таблице — она не чистится: найти, кто ей мешает |
| 7 | `ERROR: could not serialize access due to concurrent update` (⚠ применительно к 1С не подтверждено) | Конфликт сериализации на уровнях Repeatable Read / Serializable — возможен в автоматическом режиме | Журнал PostgreSQL | Повтор операции; перевод в управляемый режим |
| 8 | Обновление конфигурации падает с `lock timeout` во время резервного копирования | `pg_dump` держит `ACCESS SHARE` на всех таблицах до конца выгрузки, реструктуризации нужен `ACCESS EXCLUSIVE` [PG] | `SELECT pid, application_name FROM pg_stat_activity WHERE application_name = 'pg_dump';` | Не обновлять конфигурацию во время `pg_dump`; развести по времени |

Пример записи о взаимоблокировке в журнале PostgreSQL:

```text
ERROR:  deadlock detected
DETAIL:  Process 12345 waits for ShareLock on transaction 67890; blocked by process 23456.
        Process 23456 waits for ShareLock on transaction 67891; blocked by process 12345.
HINT:  See server log for query details.
CONTEXT:  while updating tuple (0,5) in relation "_accumrgt123"
```

Пример записи об ожидании (`log_lock_waits = on`):

```text
LOG:  process 12345 still waiting for ShareLock on transaction 67890 after 1000.123 ms
DETAIL:  Process holding the lock: 23456. Wait queue: 12345.
```

### 7.3. Какие операции что блокируют [PG]

| Операция | Режим блокировки таблицы | Что останавливает |
|---|---|---|
| `SELECT`; `pg_dump` (на всё время выгрузки) | `ACCESS SHARE` | только операции с `ACCESS EXCLUSIVE` |
| `INSERT`, `UPDATE`, `DELETE` | `ROW EXCLUSIVE` | `CREATE INDEX` без `CONCURRENTLY`, сильные блокировки |
| `VACUUM` (без `FULL`), `ANALYZE`, `CREATE INDEX CONCURRENTLY`, `REINDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` | друг друга и DDL; чтение и запись идут |
| `CREATE INDEX` (без `CONCURRENTLY`) | `SHARE` | запись в таблицу |
| `VACUUM FULL`, `CLUSTER`, `REINDEX` (без `CONCURRENTLY`), `TRUNCATE`, `DROP TABLE`, большинство форм `ALTER TABLE` | `ACCESS EXCLUSIVE` | всё, включая чтение. Уточнение для `REINDEX` (документация команды): на таблицу берётся `SHARE` (запись остановлена, чтение разрешено), на перестраиваемый индекс — `ACCESS EXCLUSIVE`; планировщик обращается ко всем индексам таблицы, поэтому на деле встают почти все запросы к ней |

Реструктуризация 1С — это DDL; «Тестирование и исправление» и обновление конфигурации базы данных со стороны 1С дополнительно требуют монопольного режима.

### 7.4. Диагностика

```sql
-- 1. Кто кого блокирует прямо сейчас
SELECT a.pid AS waiting_pid, now() - a.query_start AS waiting, pg_blocking_pids(a.pid) AS blocked_by,
       a.wait_event_type, a.wait_event, left(a.query, 100) AS waiting_query
FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0
ORDER BY a.query_start;

-- 2. Что делает блокирующий (подставить pid из blocked_by)
SELECT pid, state, now() - xact_start AS xact_age, now() - state_change AS in_state, left(query, 200) AS last_query
FROM pg_stat_activity WHERE pid = 23456;

-- 3. Самые старые открытые транзакции и «зависшие в транзакции»
SELECT pid, usename, client_addr, state, now() - xact_start AS xact_age, now() - state_change AS idle_for, left(query, 100)
FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND backend_type = 'client backend'
ORDER BY xact_start LIMIT 15;

-- 4. Счётчик взаимоблокировок по базам
SELECT datname, deadlocks, conflicts FROM pg_stat_database WHERE datname IS NOT NULL;
```

```bash
# журнал PostgreSQL: ожидания, таймауты, взаимоблокировки
sudo grep -E 'still waiting for|deadlock detected|canceling statement due to lock timeout' -A3 \
     /var/log/postgresql/postgresql-17-main.log | tail -n 60
# сторона 1С: какой сеанс держит соединение с pid PostgreSQL и кем он заблокирован
rac session list --cluster=$CL | grep -E 'session-id|user-name|db-proc-info|blocked-by-dbms|blocked-by-ls'
```

Технологический журнал для блокировок СУБД: события `DBPOSTGRS`, `SDBL`, `EXCP`, `TLOCK`, `TTIMEOUT`, `TDEADLOCK` плюс элемент `<dbmslocks/>` (добавляет свойства `lka`, `lkp`, `lkpid`, `lkaid`, `lksrc` — «жертва» и «источник» блокировки СУБД) [1С]; подробности — `kb/1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.

### 7.5. Что может администратор и что — только разработчик

| Действие | Кто |
|---|---|
| Включить `log_lock_waits`, собрать ТЖ, найти блокирующий сеанс и его код (`Context`) | администратор |
| Завершить зависший сеанс: `rac session terminate`, `pg_terminate_backend(pid)` | администратор |
| Развести по времени резервное копирование, обслуживание, обновление конфигурации, тяжёлые регламентные задания | администратор |
| Ускорить транзакции: `synchronous_commit = off`, быстрые диски, актуальная статистика, отсутствие раздувания | администратор |
| Таймауты-предохранители: `idle_in_transaction_session_timeout` для роли 1С — с большой осторожностью и большим значением (час и более): он оборвёт и легитимные длинные операции, у которых между запросами долго работает код 1С; `statement_timeout`, `idle_session_timeout`, `transaction_timeout` (17+) для роли 1С не задавать [практика] | администратор |
| Перевод конфигурации в управляемый режим, сужение областей блокировок, порядок захвата ресурсов, разделение итогов, сокращение транзакций | разработчик |

---

## 8. Ошибки данных и обслуживания

### 8.1. «Ошибка СУБД: ERROR: …» — типовые варианты

| № | Текст | Причина | Действия |
|---|---|---|---|
| 1 | `ERROR: duplicate key value violates unique constraint "_reference123_1"` + `DETAIL: Key (…)=(…) already exists.` — при записи, обмене, обновлении конфигурации | В данных есть дубли по ключу уникального индекса (логическая ошибка данных, незавершённая прошлая реструктуризация); строки, равные по правилам `mchar` (без учёта регистра и хвостовых пробелов); индекс ранее был повреждён и пропустил дубль | 8.2 |
| 2 | `ERROR: could not create unique index "…"` + `DETAIL: Key (…)=(…) is duplicated.` — при реструктуризации или `REINDEX` | То же: дубли уже лежат в таблице | 8.2 |
| 3 | `ERROR: current transaction is aborted, commands ignored until end of transaction block` | Следствие более ранней ошибки в той же транзакции | Искать первую ошибку выше по журналу для того же `pid` |
| 4 | `ERROR: invalid page in block 1234 of relation base/16385/24680`; при включённых контрольных суммах перед ней `WARNING: page verification failed, calculated checksum … but expected …` | Повреждена страница данных | 8.3 |
| 5 | `ERROR: could not read block 1234 in file "base/16385/24680": read only 0 of 8192 bytes` / `… Input/output error` | Файл короче ожидаемого либо ошибка чтения с диска | `dmesg -T`; 8.3 |
| 6 | `ERROR: missing chunk number 0 for toast value 123456 in pg_toast_24680`; `unexpected chunk number …` | Повреждена TOAST-таблица (хранилище длинных значений) или её индекс | 8.3 |
| 7 | `ERROR: could not open file "base/16385/24680": No such file or directory` | Файл таблицы или индекса отсутствует (сбой файловой системы, удаление файлов вручную, неконсистентная копия каталога данных) | 8.3 |
| 8 | `ERROR: index "…" contains unexpected zero page at block N` + `HINT: Please REINDEX it.` | Повреждён индекс | `REINDEX INDEX CONCURRENTLY "…";` |
| 9 | `ERROR: could not access status of transaction 123456` + `DETAIL: Could not open file "pg_xact/0012": No such file or directory.` | Потерян журнал статусов транзакций — тяжёлое повреждение | 8.3, восстановление из копии |
| 10 | `ERROR: cache lookup failed for relation 12345` / `could not open relation with OID 12345` | Объект удалён параллельным DDL (временная таблица, реструктуризация); если повторяется постоянно — повреждён системный каталог | Разово — повторить операцию; постоянно — 8.3 |
| 11 | `ERROR: invalid byte sequence for encoding "UTF8": 0x00` | В строке есть нулевой символ, PostgreSQL его в текстовых значениях не допускает [практика] | Убрать символ в данных/коде (например, после чтения из внешнего источника) |
| 12 | `ERROR: index row size 2912 exceeds btree version 4 maximum 2704 for index "…"` + `HINT: Values larger than 1/3 of a buffer page cannot be indexed.` | Слишком длинное значение индексируемых полей | Раздел 9.2 |
| 13 | `ERROR: target lists can have at most 1664 entries`; `tables can have at most 1600 columns` | Слишком много колонок в запросе или временной таблице | Раздел 9.2 |
| 14 | `ERROR: canceling statement due to statement timeout` | Задан глобальный `statement_timeout` | Убрать из глобальной конфигурации; для роли 1С не задавать |
| 15 | `ERROR: canceling statement due to user request` | Запрос отменён: `pg_cancel_backend`, прерывание серверного вызова в 1С, завершение сеанса | Выяснить, кто отменил |
| 16 | `FATAL: terminating connection due to administrator command` | `pg_terminate_backend`, остановка или перезапуск PostgreSQL | Проверить, не было ли перезапуска (`pg_postmaster_start_time()`) |
| 17 | `FATAL: terminating connection due to idle-in-transaction timeout` / `… idle-session timeout` | Заданы `idle_in_transaction_session_timeout` / `idle_session_timeout` | Для роли 1С убрать (`ALTER ROLE … RESET …`) |
| 18 | `ERROR: cannot execute INSERT in a read-only transaction` | Информационная база указывает на реплику (hot standby) либо задан `default_transaction_read_only = on` | `SELECT pg_is_in_recovery();` — исправить адрес сервера СУБД |
| 19 | `WARNING: database "buh" must be vacuumed within N transactions` | Приближается зацикливание счётчика транзакций | 8.5 |
| 20 | `WARNING: database "buh" has a collation version mismatch` | Сменилась версия библиотеки сортировки | 8.4 |

### 8.2. Нарушение уникальности индекса

```sql
-- 1. Какие колонки входят в индекс
SELECT indexdef FROM pg_indexes WHERE indexname = '_reference123_1';
-- 2. Найти дубли по этим колонкам (подставить колонки из определения индекса)
SELECT _fld456, _fld457, count(*) FROM _reference123 GROUP BY 1, 2 HAVING count(*) > 1 LIMIT 50;
-- 3. Проверить сам индекс (расширение amcheck)
CREATE EXTENSION IF NOT EXISTS amcheck;
SELECT bt_index_check('_reference123_1'::regclass, true);
```

- Какой объект метаданных стоит за таблицей `_Reference123` — функция встроенного языка `ПолучитьСтруктуруХраненияБазыДанных()` [1С].
- Если индекс повреждён (ошибка `bt_index_check`, недавняя смена ОС/glibc/ICU — раздел 8.4) — `REINDEX`; если после перестроения `could not create unique index … is duplicated` — дубли реальные.
- Реальные дубли устраняют средствами 1С: «Тестирование и исправление информационной базы» (проверка логической и ссылочной целостности, реиндексация, пересчёт итогов) — сначала на копии; затем поиск и объединение дублей в прикладном решении. Прямая правка данных SQL-запросами в обход платформы приводит к рассогласованию данных и ограничена лицензионным соглашением платформы (⚠ формулировку уточняйте в лицензионном соглашении) — используйте её только как крайнюю меру на копии и с пониманием структуры хранения.
- После «Тестирования и исправления» выполните `vacuumdb --analyze -d buh`.

### 8.3. Повреждение данных: порядок действий

1. **Прекратить запись и сделать копию.** Остановить сервер 1С, остановить PostgreSQL и скопировать **весь** каталог данных (и табличные пространства) на другой носитель — до любых попыток ремонта; чинить только копию [практика, wiki.postgresql.org/wiki/Corruption].

   ```bash
   V=$(ls /opt/1cv8/x86_64/ | sort -V | tail -1)             # установленная версия платформы
   sudo systemctl stop "srv1cv8-$V@default"
   sudo systemctl stop postgresql@17-main
   sudo rsync -a /var/lib/postgresql/17/main/ /mnt/rescue/pgdata-$(date +%F)/
   ```

2. **Найти причину** — иначе повреждение повторится: ошибки диска (`sudo dmesg -T | grep -i -E 'i/o error|nvme|ata[0-9]|ext4|xfs'`, `sudo smartctl -a /dev/sda`), сбой питания при кэше записи без защиты, `fsync = off` или `full_page_writes = off`, неисправная память, откат снимка ВМ, копирование каталога данных работающего сервера без `pg_basebackup`, перенос каталога данных на другую версию ОС (раздел 8.4), ручное удаление файлов в каталоге данных.
3. **Лучший путь — восстановление из резервной копии** с докатом WAL до момента перед повреждением (`04-rezervnoe-kopirovanie-i-vosstanovlenie.md`).
4. **Оценить масштаб**, если копии нет:

   ```bash
   sudo -u postgres pg_amcheck -d buh --install-missing --heapallindexed -j 4 -P     # таблицы и B-tree индексы (14+)
   sudo -u postgres pg_dump -Fc -f /dev/null buh                                     # читаются ли все таблицы
   # при остановленном сервере и включённых контрольных суммах:
   sudo -u postgres /usr/lib/postgresql/17/bin/pg_checksums --check -D /var/lib/postgresql/17/main
   ```

   Проверки `--parent-check` и `--rootdescend` требуют более сильных блокировок и останавливают запись [PG].
5. **Повреждены только индексы** — `REINDEX INDEX/TABLE`. Повреждены системные индексы — запуск с игнорированием системных индексов (`ignore_system_indexes`) и `REINDEX SYSTEM` [PG].
6. **Повреждены страницы таблиц** — спасение уцелевших строк [PG]:

   ```sql
   SET zero_damaged_pages = on;        -- повреждённые страницы обнуляются в памяти: строки на них ТЕРЯЮТСЯ
   SET ignore_checksum_failure = on;   -- читать страницы с неверной контрольной суммой (если заголовок цел)
   ```

   затем `pg_dump` повреждённых таблиц или всей базы → новый кластер (`initdb`) → восстановление → «Тестирование и исправление» в 1С (ссылочная целостность, итоги). Оба параметра предназначены для разработчиков и «никогда не должны использоваться в рабочей базе» [PG] — только на копии, для выгрузки.
7. **TOAST (`missing chunk number`)** — сначала `REINDEX TABLE pg_toast.pg_toast_24680;`. Если не помогло — найти строки, которые не читаются:

   ```sql
   DO $$
   DECLARE r record; v text;
   BEGIN
     FOR r IN SELECT ctid FROM _reference123 LOOP
       BEGIN
         SELECT t::text INTO v FROM _reference123 t WHERE t.ctid = r.ctid;
       EXCEPTION WHEN OTHERS THEN
         RAISE NOTICE 'повреждена строка %: %', r.ctid, SQLERRM;
       END;
     END LOOP;
   END $$;
   ```

   Какая таблица стоит за `pg_toast_24680`: `SELECT 24680::regclass;`. Повреждённые строки восстанавливают из резервной копии (таблица целиком — `pg_restore -t`) [практика].
8. **`pg_resetwal`** — только если сервер не запускается из-за повреждения WAL или `pg_control`, и только как последнее средство. После него данные могут быть несогласованными: сразу выгрузить дамп, создать новый кластер, восстановить; ничего не изменять в базе до выгрузки [PG].
9. После любого спасения: новый кластер через выгрузку/загрузку, «Тестирование и исправление» в 1С, полная резервная копия, устранение первопричины.

Профилактика: `fsync = on`, `full_page_writes = on`; контрольные суммы данных (`SHOW data_checksums;` — включены по умолчанию при `initdb` с PostgreSQL 18 [PG] и в кластерах, созданных `pg-setup` Postgres Pro; включить на существующем кластере — `pg_checksums --enable -D …` при остановленном сервере); регулярная проверка восстановления из копии; счётчик `checksum_failures` в `pg_stat_database`.

### 8.4. Версия правил сортировки: `collation version mismatch`, glibc и ICU

```text
WARNING:  database "buh" has a collation version mismatch
DETAIL:  The database was created using collation version 2.35, but the operating system provides version 2.39.
HINT:  Rebuild all objects in this database that use the default collation and run ALTER DATABASE buh REFRESH COLLATION VERSION, or build PostgreSQL with the right library version.
```

- **Причина:** PostgreSQL запоминает версию правил сортировки (для `libc` — версию glibc) и сверяет её при подключении к базе (15+). Версия меняется при обновлении выпуска Ubuntu (22.04 — glibc 2.35, 24.04 — 2.39, 26.04 — 2.43; для 26.04 и `libicu78` сверено 19.10.2026 по packages.ubuntu.com) и при физическом переносе каталога данных на другую версию ОС (`pg_basebackup`, реплика, копия диска) [PG].
- **Чем опасно:** индексы хранят порядок строк по старым правилам; при изменении правил поиск по индексу может не находить существующие строки, а уникальные индексы — пропускать дубли [PG, wiki Locale_data_changes]. Логические способы переноса (`pg_dump`, логическая репликация) этой проблеме не подвержены.
- **Особенность 1С:** платформа ставит `client_min_messages = error`, поэтому предупреждение в 1С не видно — только в журнале PostgreSQL и в `psql`. Строковые поля 1С имеют типы `mchar`/`mvarchar`, которые сравниваются через библиотеку ICU [PGPro]: на их индексы влияет смена версии **ICU** (22.04 — `libicu70`, 24.04 — `libicu74`, 26.04 — `libicu78`), и об этом PostgreSQL не предупреждает (⚠ вывод из описания модуля `mchar`; официального описания поведения при смене версии ICU не найдено). Поэтому после смены выпуска ОС перестраивать индексы баз 1С нужно всегда, независимо от наличия предупреждения.

```bash
# что записано и что предоставляет ОС (PostgreSQL 15+)
sudo -u postgres psql -c "SELECT datname, datcollversion, pg_database_collation_actual_version(oid) AS actual FROM pg_database;"
# окно обслуживания, сервер 1С остановлен: перестроить индексы и обновить отметку версии
sudo -u postgres reindexdb -d buh -j 4
sudo -u postgres psql -c "ALTER DATABASE buh REFRESH COLLATION VERSION;"
for db in postgres template1; do
  sudo -u postgres reindexdb -d "$db"
  sudo -u postgres psql -c "ALTER DATABASE $db REFRESH COLLATION VERSION;"
done
```

`REFRESH COLLATION VERSION` только обновляет отметку в каталоге и убирает предупреждение — перестроены ли объекты, команда не проверяет [PG]. Безопасная стратегия обновления ОС: новая ВМ с новой Ubuntu и сборкой PostgreSQL под неё, перенос баз через `pg_dump`/`pg_restore`.

### 8.5. Предупреждения о зацикливании счётчика транзакций (wraparound)

```text
WARNING:  database "buh" must be vacuumed within 39985967 transactions
HINT:  To avoid XID assignment failures, execute a database-wide VACUUM in that database.

ERROR:  database is not accepting commands that assign new transaction IDs to avoid wraparound data loss in database "buh"
HINT:  Execute a database-wide VACUUM in that database.
```

Тексты выше — PostgreSQL 17 и 18 (подсказка предупреждения бывает и в варианте `To avoid transaction ID assignment failures, …` — зависит от места проверки в коде). В 14–16 (в том числе в сборке 16 у пользователя) они другие: предупреждение с подсказкой `HINT: To avoid a database shutdown, execute a database-wide VACUUM in that database.`, отказ — `ERROR: database is not accepting commands to avoid wraparound data loss in database "buh"` с подсказкой `HINT: Stop the postmaster and vacuum that database in single-user mode.` Эта подсказка устарела — документация 15 и 16 уже советует обычный `VACUUM` без остановки сервера (порядок ниже). Сверено 19.10.2026 по `src/backend/access/transam/varsup.c` веток 14–18 и разделу «Routine Vacuuming» документации 15, 16, 18.

- Предупреждения начинаются, когда до предела остаётся 40 млн транзакций; при остатке менее 3 млн сервер перестаёт выдавать новые идентификаторы — запись останавливается, чтение работает [PG].
- Причина всегда одна: очистка не может «заморозить» старые строки — автоочистка выключена либо горизонт удерживают старая транзакция, подготовленная транзакция или забытый слот репликации.

```sql
SELECT datname, age(datfrozenxid) AS xid_age FROM pg_database ORDER BY 2 DESC;      -- норма — около 200 млн; устойчивый рост за 500 млн — искать, что мешает очистке
SELECT c.oid::regclass AS table_name, greatest(age(c.relfrozenxid), age(t.relfrozenxid)) AS age
FROM pg_class c LEFT JOIN pg_class t ON c.reltoastrelid = t.oid
WHERE c.relkind IN ('r', 'm') ORDER BY 2 DESC LIMIT 20;
```

Порядок действий [PG]: (1) зафиксировать или откатить старые подготовленные транзакции (`pg_prepared_xacts`); (2) завершить долгие транзакции (`pg_stat_activity`, `pg_terminate_backend`); (3) удалить забытые слоты репликации (`pg_replication_slots`); (4) выполнить в проблемной базе обычный `VACUUM` (не `VACUUM FULL` и не `VACUUM FREEZE`); (5) убедиться, что автоочистка включена. Однопользовательский режим в современных версиях для этого не нужен и «его следует избегать» [PG].

```bash
sudo -u postgres vacuumdb -d buh -j 4 --verbose
```

На нагруженной базе 1С принудительная очистка «to prevent wraparound» (видна в `pg_stat_activity.query`) — регулярное штатное событие: `autovacuum_freeze_max_age` по умолчанию 200 млн транзакций, такая очистка запускается даже при `autovacuum = off` и не уступает блокировкам, как обычная автоочистка [PG].

---

## 9. Ограничения и особенности типов данных

### 9.1. Как типы 1С хранятся в PostgreSQL

Сводка по примерам запросов платформы из статей ИТС и описаниям модулей Postgres Pro; официальной таблицы соответствия типов в открытых источниках при подготовке не найдено (⚠ строки без пометки источника — по наблюдениям в реальных базах).

| Тип 1С | Тип PostgreSQL | Примечание |
|---|---|---|
| Ссылка | `bytea` (16 байт) | в запросах платформы: `_IDRRef = '\\200\\310…'::bytea` [1С, ИТС 6011] |
| Строка фиксированной длины | `mchar(n)` | регистронезависимое сравнение, хвостовые пробелы — как в MS SQL [PGPro] |
| Строка переменной длины | `mvarchar(n)` | то же |
| Строка неограниченной длины | `mvarchar` без длины | длинные значения — в TOAST; не индексируется [1С] |
| Число | `numeric(p, s)` | в запросах платформы: `CAST(0 AS NUMERIC)` [1С, ИТС 6011] |
| Дата | `timestamp` (без часового пояса) | хранится без смещения года |
| Булево | `boolean` | |
| ХранилищеЗначения, двоичные данные | `bytea` | длинные значения — в TOAST; не индексируется [1С] |
| Составной тип | несколько колонок на одно поле (`_TYPE`, `_L`, `_N`, `_T`, `_S`, `_RTRef`, `_RRRef`) | одно поле составного типа даёт до семи колонок в запросе |

Особенности, которые воспринимаются как «странности»:

- `mchar`/`mvarchar` хранят строки в **UTF-16** независимо от кодировки базы и сравнивают их через **ICU**; операторы `=`, `<`, `>` — без учёта регистра, для сравнения с учётом регистра есть отдельные операторы `&=`, `&<`, `&>` [PGPro]. В `psql` запрос `SELECT … WHERE _description = 'иванов'` найдёт и «ИВАНОВ».
- Оператор `==` (модуль `fulleq`) считает два `NULL` равными — так платформа получает семантику MS SQL [PGPro].
- Даты: диапазон `timestamp` в PostgreSQL начинается задолго до нашей эры, поэтому даты 1С хранятся как есть. Смещение дат на 2000 лет и таблица `_YearOffset` существуют только при работе с Microsoft SQL Server [1С]. При прямом чтении базы MS SQL и PostgreSQL одни и те же даты выглядят по-разному.
- Пустая дата 1С хранится как `0001-01-01 00:00:00`, а не `NULL` [практика].
- Числа: `numeric` — точный десятичный тип; его собственный предел (сотни тысяч разрядов) намного больше того, что позволяет задать конфигуратор 1С (по «Руководству разработчика» 8.3.27, глава 4, максимально допустимая разрядность числа во встроенном языке — 32 знака (сверено 11.10.2026); для длины числового реквизита в конфигураторе остаётся прежняя оговорка: предел разрядности числа в платформе — 38, по памяти), поэтому «переполнение числа» (`numeric field overflow`) — это всегда превышение разрядности, заданной в метаданных, а не ограничение СУБД. Арифметика над `numeric` медленнее целочисленной — на тяжёлых агрегатах это заметно по загрузке процессора.
- Сортировка строк: в MS SQL её определяет collation базы (обычно `Cyrillic_General_CI_AS`), в PostgreSQL для строк 1С — правила ICU. Порядок букв совпадает, но может отличаться положение знаков препинания, пробела, дефиса, цифр относительно букв, «ё» [практика; ⚠ конкретные различия зависят от версий]. Код, который полагается на сравнение строк «больше/меньше» (диапазоны кодов и номеров как строк), после переноса с MS SQL может вести себя иначе.

### 9.2. Пределы PostgreSQL и как они проявляются в 1С

| Предел | Значение [PG] | Как проявляется | Что делать |
|---|---|---|---|
| Размер значения одного поля | 1 ГБ | `invalid memory alloc request size`, `out of memory` при записи больших двоичных данных, при загрузке `.dt` с такими данными | Не хранить такие объёмы в базе одним значением (раздел 5.4) |
| Колонок в таблице | 1600 (меньше, если строка не помещается в страницу 8 КБ) | `ERROR: tables can have at most 1600 columns` — временные таблицы запросов с огромным списком полей, регистры с очень большим числом измерений и ресурсов | Сократить список полей, разбить запрос |
| Колонок в результате запроса | 1664 | `ERROR: target lists can have at most 1664 entries` — запросы и отчёты с сотнями полей, особенно составного типа | То же |
| Размер строки B-tree индекса | около 1/3 страницы: 2704 байта | `ERROR: index row size … exceeds btree version 4 maximum 2704 for index "…"` — длинные строки в индексируемых полях (измерения, реквизиты с признаком «Индексировать», длинные коды); `mvarchar` хранится в UTF-16 — 2 байта на символ, строка в 1024 символа уже занимает более 2 КБ | Сократить длину индексируемых строк в конфигурации либо снять индексирование; на MS SQL то же ограничение проявляется иначе (предел ключа 900/1700 байт) |
| Колонок в индексе | 32 | Платформа сама ограничивает индексы (для «дополнительных индексов» — не более 16 физических колонок [1С]) | — |
| Длина идентификатора | 63 байта | Имя базы данных — не длиннее 63 символов [1С] | — |
| Параметров запроса | 65 535 | Актуально для внешних инструментов, обращающихся к базе | — |
| Глубина стека разбора | `max_stack_depth` (2 МБ по умолчанию) | `stack depth limit exceeded` | Раздел 5.8 |
| Число таблиц в запросе | жёсткого предела нет (в современных версиях MS SQL Server — тоже: число таблиц в одном `SELECT` ограничено только ресурсами; сверено 19.10.2026 по Microsoft Learn, «Maximum capacity specifications for SQL Server») | Запрос выполняется, но при числе элементов `FROM` больше `join_collapse_limit` порядок соединений не оптимизируется полностью, а начиная с `geqo_threshold` план выбирает генетический оптимизатор — планы нестабильны | Упрощать запросы; `join_collapse_limit`, `from_collapse_limit = 20` [1С][PGPro] |
| Длина текста запроса | практический предел — 1 ГБ на строку | Гигантские запросы (RLS, списки) долго разбираются и планируются | Временные таблицы вместо списков |
| Текст запроса в `pg_stat_activity` | `track_activity_query_size`, умолчание 1024 байта | Запросы 1С обрезаны | `track_activity_query_size = 1048576` (перезапуск) [1С, ИТС 6011] |
| Число таблиц в базе | практически не ограничено | В крупных конфигурациях десятки тысяч таблиц и индексов: медленные `\d`, `pg_dump`; нужен большой `max_locks_per_transaction` | Раздел 5.1 |
| Размер таблицы | 32 ТБ | — | — |
| Нулевой символ в строке | недопустим | `invalid byte sequence for encoding "UTF8": 0x00` | Очищать данные |

---

## 10. WAL и место на диске

Подробный разбор — `05-obsluzhivanie-vacuum-analyze-reindex.md` (раздел 12) и `04-rezervnoe-kopirovanie-i-vosstanovlenie.md`; здесь — каталог и порядок спасения.

### 10.1. Разросся `pg_wal`

Нормальный размер каталога — до `max_wal_size` (мягкий предел, под нагрузкой превышается) плюс `wal_keep_size`. Если он в разы больше — что-то удерживает сегменты:

| Причина | Признак | Устранение |
|---|---|---|
| Неактивный или отстающий слот репликации (остался от реплики, `pg_basebackup -C`, `pg_receivewal`, механизма копий базы данных 1С) | `pg_replication_slots`: `active = f`, большой объём удержания; `max_slot_wal_keep_size = -1` — слот может удерживать WAL без ограничения [PG] | Починить потребителя либо `SELECT pg_drop_replication_slot('имя');` затем `CHECKPOINT;` |
| Архивация не работает или не успевает | `pg_stat_archiver.failed_count` растёт; в журнале `archive command failed with exit code …`; в `pg_wal/archive_status` копятся `*.ready` | Исправить `archive_command` (место, права, сеть): накопленное отправится само. `pg_wal` будет расти, пока ситуация не разрешится [PG] |
| Большой `wal_keep_size` | `SHOW wal_keep_size;` | Уменьшить |
| Массовая операция (реструктуризация, загрузка `.dt`, перепроведение) | Всплеск объёма, контрольные точки «по требованию» | Штатно; дождаться окончания и контрольной точки |
| Контрольные точки не завершаются (очень медленный диск) | `log_checkpoints`: длительность записи | Диск; `checkpoint_completion_target` |

```bash
df -h /var/lib/postgresql; sudo du -sh /var/lib/postgresql/17/main/pg_wal
sudo ls /var/lib/postgresql/17/main/pg_wal/archive_status 2>/dev/null | grep -c '\.ready$'
```

```sql
SELECT count(*) AS segments, pg_size_pretty(sum(size)) AS total FROM pg_ls_waldir();
SELECT slot_name, slot_type, active, wal_status,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained
FROM pg_replication_slots ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC NULLS LAST;
SELECT archived_count, last_archived_time, failed_count, last_failed_wal, last_failed_time FROM pg_stat_archiver;
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('max_wal_size','wal_keep_size','max_slot_wal_keep_size','archive_mode','archive_command','wal_level');
```

Страховка: `max_slot_wal_keep_size = 20GB..50GB` (слот, вышедший за предел, теряется, зато основной сервер не останавливается), мониторинг `pg_stat_archiver` и свободного места, `pg_wal` и резервные копии — на разных томах.

### 10.2. Место закончилось, сервер не стартует: порядок спасения

Признаки: `PANIC: could not write to file "pg_wal/xlogtemp.NNN": No space left on device`, служба в состоянии `failed`, в 1С — «Сервер баз данных не обнаружен». Зафиксированные транзакции не потеряны, но база останется недоступной, пока не появится место [PG].

1. **Ничего не удалять внутри каталога данных** — ни из `pg_wal`, ни из `pg_xact`, ни «лишние» файлы в `base`.
2. Понять, какой том заполнен и чем:

   ```bash
   df -h; df -i
   sudo du -xsh /var/lib/postgresql/17/main/* | sort -h | tail -n 8
   sudo du -xsh /var/log/* /var/backups /home/usr1cv8/.1cv8 2>/dev/null | sort -h | tail -n 10
   ```

3. Освободить место **вне** каталога данных: журналы systemd (`sudo journalctl --vacuum-size=200M`), кэш пакетов (`sudo apt clean`), старые журналы PostgreSQL (`/var/log/postgresql/*.gz`; у Postgres Pro — старые файлы в `…/data/log/`, это журналы сообщений, а не WAL), технологический журнал 1С, дампы аварийных завершений, старые резервные копии на том же томе.
4. Либо увеличить том. В стандартной установке Ubuntu Server с LVM логический том часто занимает не всю группу томов:

   ```bash
   sudo vgs                                                  # VFree > 0 → есть свободное место в группе
   sudo lvextend -r -L +20G /dev/ubuntu-vg/ubuntu-lv         # -r сразу расширяет файловую систему
   # если увеличен сам виртуальный диск на хосте:
   sudo growpart /dev/sda 3 && sudo pvresize /dev/sda3 && sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
   ```

   Экстренный приём для ext4 [практика]: уменьшить резерв суперпользователя (по умолчанию 5 % тома) — `sudo tune2fs -m 1 /dev/mapper/ubuntu--vg-ubuntu--lv`.
5. Запустить PostgreSQL и дождаться восстановления по WAL; следить по журналу:

   ```bash
   sudo systemctl start postgresql@17-main
   sudo tail -f /var/log/postgresql/postgresql-17-main.log    # ждать «database system is ready to accept connections»
   ```

6. Найти и устранить причину роста (раздел 10.1; раздувание — 6.8; временные файлы — 5.7).
7. Если архивация сломана и быстро не чинится, а место кончается снова: временно `archive_command = '/bin/true'` и `reload`. Цепочка архива при этом рвётся — после починки обязательно новая базовая копия.

Чего делать нельзя: `rm` в `pg_wal`; `pg_resetwal` «чтобы освободить место»; `pg_archivecleanup` по каталогу `pg_wal` (утилита предназначена для каталога архива); `VACUUM FULL` на заполненном диске (ему нужно место под копию таблицы).

---

## 11. После обновления перестало работать

### 11.1. Общие правила

- Смена версии платформы 1С (в любую сторону) без смены версии PostgreSQL дополнительных действий со стороны СУБД не требует [1С].
- Каждая основная версия PostgreSQL поддерживается платформой начиная с определённого релиза (по данным статьи `01-sborki-postgresql-dlya-1c-ustanovka.md`, собранным из списка изменений платформы: 12–15 — с 8.3.18, 16 и 17 — с 8.3.22, 18 — с 8.3.27; в 8.5.1 прекращена поддержка версий до 9.6 включительно). Перед обновлением любой из сторон сверяйтесь со списком на v8.1c.ru; на июль 2026 протестированы сборки 14.23, 15.18, 16.14, 17.10, 18.4 [1С]. Точный текст сообщения платформы при неподдерживаемой версии СУБД — ⚠ не подтверждено.
- Минорное обновление PostgreSQL (17.9 → 17.10) — замена пакетов и перезапуск службы; до перезапуска работает старый код. Мажорное (17 → 18) — `pg_upgrade`/`pg_upgradecluster` или дамп; подробно — `07-replikaciya-otkazoustojchivost-obnovlenie-versij.md`.
- Перед мажорным обновлением: резервная копия, проверка на копии, `pg_upgrade --check`, сверка своей конфигурации с примечаниями к выпуску.

```sql
-- всё, что задано не по умолчанию: это нужно сверить с примечаниями к новой версии
SELECT name, setting, source, sourcefile FROM pg_settings WHERE source NOT IN ('default', 'override') ORDER BY name;
```

### 11.2. Каталог

| После чего | Симптом | Причина | Решение |
|---|---|---|---|
| `apt upgrade` | `type "mvarchar" does not exist`, `could not load library …mchar.so` | Пакеты сборки 1С заменены ванильными из архива Ubuntu/PGDG (одинаковые имена пакетов) | Переустановить сборку 1С; `apt-mark hold postgresql-17 postgresql-client-17 libpq5` |
| Любое обновление PostgreSQL | Сервер не стартует: `unrecognized configuration parameter "…"` | В конфигурации остался удалённый параметр: `stats_temp_directory` (15), `vacuum_defer_cleanup_age` (16), `old_snapshot_threshold` (17), `escape_string_warning` (19) [PG] | Удалить строку из `postgresql.conf`/`conf.d`/`postgresql.auto.conf` |
| Мажорное обновление | Сервер не стартует: `could not access file "…"` | В `shared_preload_libraries` — библиотека, которой нет в новой сборке | Раздел 4.1, строка 5 |
| `pg_upgrade` до 18-й версии | Все запросы медленные | Статистика оптимизатора не переносится | `vacuumdb --all --analyze-in-stages`; с 18-й переносится (кроме расширенной) [PG] |
| `pg_upgrade` на 18 | `pg_upgrade` отказывается работать из-за контрольных сумм | В 18-й `initdb` включает контрольные суммы по умолчанию, а настройки старого и нового кластера должны совпадать [PG] | Новый кластер создать с `--no-data-checksums` либо заранее включить суммы в старом (`pg_checksums --enable`) |
| Обновление до 14+ | Старая платформа 1С не проходит аутентификацию после смены пароля | `password_encryption` по умолчанию стал `scram-sha-256` [PG] | Раздел 2.4 |
| Обновление до 15+ | `permission denied for schema public` в **новых** базах | У `PUBLIC` отобрано право `CREATE` в схеме `public`; владелец схемы — владелец базы. Базы, перенесённые обновлением или дампом, сохраняют прежние права [PG] | Раздел 3.1 |
| Обновление до 15+ | Перестали работать скрипты резервного копирования с `pg_start_backup()`/`pg_stop_backup()` | Монопольный режим копирования удалён, функции переименованы в `pg_backup_start()`/`pg_backup_stop()` [PG] | Переписать скрипты либо перейти на `pg_basebackup` |
| Обновление до 15+ | Рекомендация «вынести `pg_stat_tmp` в tmpfs» не применяется, параметр не распознан | Статистика хранится в разделяемой памяти, `stats_temp_directory` удалён [PG] | Убрать параметр |
| Обновление до 17+ | Скрипты мониторинга падают на `pg_stat_bgwriter` | Часть колонок перенесена в `pg_stat_checkpointer` | Обновить запросы (`06-monitoring-i-diagnostika-zaprosov.md`) |
| Обновление до 18 | Предупреждения при `ALTER ROLE … PASSWORD` с MD5 | MD5 объявлен устаревшим [PG] | Перейти на SCRAM; `md5_password_warnings = off` — только чтобы заглушить |
| Попытка перейти на 19 (на 19.10.2026 — RC 1 от 15.10.2026) | 1С не работает либо сервер не стартует со старой конфигурацией | `standard_conforming_strings` принудительно `on`, `escape_string_warning` удалён; `jit` по умолчанию выключен; `max_locks_per_transaction` по умолчанию 128 с иной ёмкостью [PG] | Не использовать 19-ю версию для 1С до появления её в списке поддерживаемых и выхода сборок с патчами |
| Обновление выпуска Ubuntu (`do-release-upgrade`) | `could not load library …: libicuuc.so.NN`; PostgreSQL не запускается или заменён версией из архива Ubuntu; сторонние репозитории отключены | Сборка привязана к библиотекам конкретного выпуска (`libicu70`/`74`/`78`, `libssl`, `libllvm`) | Поставить сборку под новый выпуск, вернуть репозиторий; затем `REINDEX` и `REFRESH COLLATION VERSION` (раздел 8.4). Надёжнее — новая ВМ и перенос дампом |
| Обновление выпуска Ubuntu | Поиск по строкам «не находит» записи, дубли в справочниках | Сменились glibc и ICU, индексы не перестроены | Раздел 8.4 |
| Обновление платформы 1С | Первый запуск долгий, конфигуратор предлагает обновить конфигурацию базы данных | Смена режима совместимости или структуры служебных таблиц → реструктуризация | Место на диске и время (раздел 6.6) |
| Перенос на новый сервер копированием каталога данных | Не стартует: `database files are incompatible with server` | Другая основная версия или другая сборка | Только та же сборка и основная версия; иначе — дамп |
| Включение пулера соединений (PgBouncer) между 1С и PostgreSQL | Ошибки с временными таблицами, «потерянные» настройки сеанса | Режим пула на уровне транзакций несовместим с временными таблицами и `SET` сеанса, которыми пользуется 1С [практика] | Не ставить пулер в транзакционном режиме (`07-…`, раздел 9) |

---

## 12. Отличия поведения 1С на PostgreSQL от MS SQL, которые принимают за ошибки

| Что наблюдают | Почему так | Что с этим делать |
|---|---|---|
| В автоматическом режиме блокировок пользователи ждут друг друга на любой записи | Блокировки на уровне таблиц (раздел 7.1) | Управляемый режим |
| База не уменьшается после удаления данных, файлы растут | MVCC: старые версии строк остаются до `VACUUM`; обычная очистка возвращает место для повторного использования, но не операционной системе | Автоочистка; `VACUUM FULL`/`pg_repack` — только при реальной необходимости, в окно обслуживания |
| Длинный отчёт никого не блокирует, но таблицы «пухнут» | Читатели не блокируют писателей, зато длинная транзакция удерживает горизонт очистки | Контролировать длинные транзакции (6.8) |
| «Журнал транзакций» не нужно усекать, нет моделей восстановления | WAL перерабатывается автоматически; растёт только из-за слотов и сломанной архивации (раздел 10) | Мониторинг слотов и архиватора |
| Нет кластерных индексов | Таблицы PostgreSQL — «кучи»; индекс, который в MS SQL кластерный, здесь обычный | Учитывать при оценке чтения диапазонами; `CLUSTER` даёт разовый эффект |
| Тяжёлый отчёт использует одно ядро | Параллельное выполнение для 1С отключают (`max_parallel_workers_per_gather = 0` [PGPro]); в MS SQL работает параллелизм (MAXDOP) | Оптимизировать запрос; копия базы для отчётов |
| Запросы с временными таблицами чувствительны к статистике | Статистика временных таблиц собирается только явным `ANALYZE` (раздел 6.3) | `plantuner`, актуальная сборка |
| `ПОЛНОЕ ВНЕШНЕЕ СОЕДИНЕНИЕ` медленное | Платформа преобразует запрос (раздел 6.2, строка 8) | Переписать запрос |
| Строки сортируются иначе; сравнение строк «больше/меньше» даёт другие результаты | Правила ICU вместо collation MS SQL (раздел 9.1) | Не полагаться на порядок знаков препинания и спецсимволов |
| Запрос без `УПОРЯДОЧИТЬ ПО` (в том числе `ПЕРВЫЕ N`) возвращает строки в другом порядке | Порядок без сортировки не гарантирован; на PostgreSQL он определяется физическим расположением строк и планом [практика] | Всегда задавать сортировку явно |
| Даты в таблицах «нормальные», а в MS SQL были сдвинуты на 2000 лет | Смещение дат нужно только MS SQL [1С] | Учитывать при прямом чтении базы и в интеграциях |
| Команда «удалить соединение» в консоли кластера не прерывает длительный запрос | Для PostgreSQL удаление соединения невозможно: команда не выполняет никаких действий [1С] | `pg_cancel_backend(pid)` / `pg_terminate_backend(pid)`; `rac session interrupt-current-server-call` |
| После прерванного обновления конфигурации в базе остались «лишние» таблицы | Реструктуризация многоэтапная; промежуточные таблицы платформа дорабатывает или убирает при следующем запуске обновления (⚠ детали зависят от версии платформы и механизма `v1`/`v2`) | Не удалять вручную без резервной копии; повторить обновление, иметь запас места и времени |
| Тексты ошибок блокировок другие | `canceling statement due to lock timeout`, `deadlock detected` вместо сообщений MS SQL | Раздел 7.2 |
| Нет сжатия и шифрования базы средствами СУБД через настройки 1С | Для PostgreSQL в документации кластера эти возможности не значатся [1С] | Сжатие и шифрование на уровне файловой системы или диска |
| Сотни процессов `postgres` в состоянии `idle` | Каждое соединение пула 1С — отдельный процесс ОС (в MS SQL — потоки) | Норма; учитывать память на соединение и `max_connections` |
| Резервная копия не переносится «файлом `.bak`» на любой сервер | `pg_dump` — логический дамп (нужна сборка с модулями 1С на приёмнике), физическая копия — только на ту же основную версию и сборку | Раздел 4.2 |
| Регистронезависимый поиск и сравнение работают «сами» | Типы `mchar`/`mvarchar`, а не collation базы | Учитывать при ручных SQL-запросах |

---

## 13. Чек-лист «1С не подключается к базе»

Выполнять по порядку; первая непройденная проверка и есть причина.

```bash
# === на сервере СУБД ===
# 1. Экземпляр запущен? Если нет — почему
pg_lsclusters
sudo systemctl status postgresql@17-main --no-pager | head -n 15
sudo journalctl -u postgresql@17-main -n 50 --no-pager
df -h /var/lib/postgresql; df -i /var/lib/postgresql              # не кончилось ли место (раздел 10.2)

# 2. Слушает ли нужный адрес и порт
sudo ss -tlnp | grep -E ':5432\b'
sudo -u postgres psql -Atc "SHOW listen_addresses" -c "SHOW port"

# 3. Локально сервер отвечает?
sudo -u postgres psql -Atc "select version(), pg_is_in_recovery(), now() - pg_postmaster_start_time() as uptime"

# 4. Сборка годится для 1С?
sudo -u postgres psql -Atc "select count(*) from pg_available_extensions where name in ('mchar','fulleq','fasttrun')"   # ожидается 3

# 5. Правила доступа и пароль роли
sudo -u postgres psql -c "SELECT line_number, type, database, user_name, address, auth_method, error FROM pg_hba_file_rules"
sudo -u postgres psql -c "SELECT rolname, rolsuper, rolcanlogin, rolvaliduntil, left(rolpassword, 14) AS hash FROM pg_authid WHERE rolcanlogin"

# 6. Свободны ли соединения
sudo -u postgres psql -Atc "select count(*) || ' из ' || current_setting('max_connections') from pg_stat_activity"

# 7. Брандмауэр
sudo ufw status verbose | grep -E '5432|Status'

# === на сервере 1С (от имени пользователя сервера) ===
# 8. Имя, порт, вход
getent hosts pg-server
nc -vz pg-server 5432
sudo -u usr1cv8 psql "host=pg-server port=5432 dbname=postgres user=postgres" -c "select 1"     # нужен пакет клиента psql

# === снова на сервере СУБД ===
# 9. Что сервер записал о неудачной попытке (адрес клиента, роль, база, причина)
sudo grep -E 'FATAL|authentication|no pg_hba' /var/log/postgresql/postgresql-17-main.log | tail -n 20
```

| Шаг не пройден | Раздел |
|---|---|
| 1 — экземпляр `down`, в журнале `No space left on device` | 10.2 |
| 1 — в журнале `could not access file`, `unrecognized configuration parameter`, `could not map anonymous shared memory` | 4.1, 5.9, 11.2 |
| 2 — слушает только `127.0.0.1`, а сервер 1С на другом хосте | 2.3 |
| 3 — `the database system is starting up` | дождаться восстановления, 2.1 (строка 13) |
| 4 — меньше 3 | 4.1, статья `01-…` |
| 5 — нет подходящей строки, столбец `error` не пуст, у роли нет пароля, хеш `md5` при методе `scram-sha-256` | 2.3, 2.4 |
| 6 — соединения исчерпаны | 2.5 |
| 7, 8 — порт недостижим, имя не разрешается | 2.1 (строки 2–4) |
| 8 проходит, 1С не подключается | Параметры информационной базы: сервер (`имя port=NNNN`), имя базы, пользователь, пароль; проверить `rac infobase info`; другой рабочий сервер кластера; версия платформы и SCRAM (2.4) |
| Подключение есть, ошибка при создании базы | Раздел 3 |

---

## 14. Чек-лист «1С тормозит на PostgreSQL»

```bash
# 1. Ресурсы: кто занят — postgres, rphost или диск
uptime; free -h; df -h
top -b -n 1 -o %CPU | head -n 15
vmstat 5 3                                   # wa — диск, si/so — подкачка, st — перегружен хост виртуализации
iostat -x 5 3                                # await, %util
sudo dmesg -T | grep -i -E 'out of memory|killed process|i/o error' | tail
```

```sql
-- 2. Что делает СУБД прямо сейчас
SELECT state, wait_event_type, wait_event, count(*) FROM pg_stat_activity
WHERE backend_type = 'client backend' GROUP BY 1,2,3 ORDER BY 4 DESC;

-- 3. Блокировки и долгие транзакции
SELECT pid, pg_blocking_pids(pid) AS blocked_by, now() - query_start AS waiting, left(query, 80)
FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;
SELECT pid, state, now() - xact_start AS xact_age, left(query, 80) FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND backend_type = 'client backend' ORDER BY xact_start LIMIT 10;

-- 4. Ключевые настройки: совпадают ли с рекомендациями для 1С
SELECT name, setting, unit, source FROM pg_settings WHERE name IN
 ('shared_buffers','effective_cache_size','work_mem','temp_buffers','maintenance_work_mem','max_connections',
  'random_page_cost','effective_io_concurrency','from_collapse_limit','join_collapse_limit','geqo_threshold',
  'jit','max_parallel_workers_per_gather','synchronous_commit','fsync','max_wal_size','checkpoint_timeout',
  'autovacuum','autovacuum_max_workers','autovacuum_naptime','max_locks_per_transaction',
  'standard_conforming_strings','shared_preload_libraries','huge_pages','ssl','log_min_duration_statement') ORDER BY 1;

-- 5. Автоочистка и раздувание
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class
WHERE relname IN ('pg_class','pg_attribute','pg_type','pg_depend','pg_statistic');

-- 6. Временные файлы и попадания в кэш
SELECT datname, temp_files, pg_size_pretty(temp_bytes) AS temp,
       round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 1) AS cache_hit_pct, deadlocks
FROM pg_stat_database WHERE datname NOT LIKE 'template%' ORDER BY temp_bytes DESC;

-- 7. Самые затратные запросы
SELECT calls, round(total_exec_time::numeric/1000, 1) AS total_s, round(mean_exec_time::numeric, 1) AS mean_ms,
       left(query, 100) FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
```

```bash
# 8. Диск: скорость синхронной записи
sudo -u postgres /usr/lib/postgresql/17/bin/pg_test_fsync -f /var/lib/postgresql/17/main/pg_test_fsync.tmp
# 9. Сторона 1С: управляемые блокировки и доля времени СУБД (нужен технологический журнал)
grep -rhP '\d{6,},TLOCK.*WaitConnections=\d+' /var/log/1c/tj | tail -n 5
```

Разбор результатов:

| Что увидели | Вывод | Раздел |
|---|---|---|
| `st` > 5–10 %, загрузка одного ядра 100 % при простое остальных | Перегружен хост, энергосбережение, однопоточный упор | 6.9 |
| `si/so` ≠ 0, `Killed process` в `dmesg` | Не хватает памяти | 5.3 |
| `wa` высокий, `await` десятки миллисекунд | Медленный диск, холодный кэш, залповая запись | 6.7, 6.2 (строка 16) |
| Много `Lock` в ожиданиях; есть `blocked_by` | Блокировки СУБД | 7 |
| Много `idle in transaction`, транзакции возрастом в минуты | Длинные транзакции 1С, управляемые блокировки | 7.2 (строки 1, 4) |
| `jit = on`, `max_parallel_workers_per_gather > 0`, `random_page_cost = 4` на SSD, `work_mem = 4MB`, `shared_buffers = 128MB`, `standard_conforming_strings = on` | PostgreSQL работает с настройками по умолчанию | `02-postgresql-conf-tyuning-dlya-1c.md` |
| В `shared_preload_libraries` есть `online_analyze` без явных параметров | Синхронный `ANALYZE VERBOSE` всех таблиц | 6.3 |
| `n_dead_tup` сравнимо с `n_live_tup`, `last_autovacuum` давно или пусто; каталог в гигабайтах | Автоочистка не справляется | 6.8 |
| `temp` в десятки гигабайт | Мал `work_mem` либо ошибочные планы | 5.7, 6.4 |
| `cache_hit_pct` заметно ниже 99 % на прогретой системе | Мало памяти под кэш либо запросы читают лишнее | `shared_buffers`, 6.4 |
| Один-два запроса дают основную долю `total_s` | Оптимизировать эти запросы | 6.4 |
| `pg_test_fsync` показывает сотни операций в секунду | Медленная фиксация транзакций | 6.5 |
| В PostgreSQL всё спокойно, есть длинные `TLOCK` | Управляемые блокировки 1С | 7.2 (строка 1) |
| В PostgreSQL всё спокойно, блокировок нет | Время уходит в код 1С, сеть, клиент | Замер производительности в 1С, ТЖ `CALL` |

---

## Типичные ошибки и подводные камни (симптом → причина → решение)

Ошибки самих администраторов, из-за которых простая проблема превращается в аварию. Каталоги сообщений СУБД — в разделах 2–11.

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | `systemctl status postgresql` показывает `active (exited)`, а 1С не подключается | Это служба-«зонтик», её состояние ничего не говорит об экземпляре | `pg_lsclusters`, `systemctl status postgresql@17-main` |
| 2 | Поправили `pg_hba.conf` — ничего не изменилось | Не сделан `reload`; правили не тот файл; в файле синтаксическая ошибка, и сервер остался на старых правилах | `SHOW hba_file;` → правка → `reload` → `SELECT * FROM pg_hba_file_rules WHERE error IS NOT NULL;` |
| 3 | Изменили `listen_addresses`, `max_connections`, `shared_buffers`, сделали `reload` — значение прежнее | Параметры требуют перезапуска | `SELECT name FROM pg_settings WHERE pending_restart;` → `restart` |
| 4 | Значение в `postgresql.conf` не действует | Перекрыто в `conf.d/*.conf`, в `postgresql.auto.conf` (`ALTER SYSTEM`), на уровне базы или роли | `SELECT name, setting, source, sourcefile, sourceline FROM pg_settings WHERE name = '…';` |
| 5 | «В `psql` всё работает», а 1С не подключается | Проверяли `sudo -u postgres psql` — это Unix-сокет и метод `peer`; 1С ходит по TCP с паролем | Проверять `psql -h <адрес> -U <роль>` с сервера 1С от имени `usr1cv8` |
| 6 | При `too many clients` не может войти даже администратор | Роль 1С — суперпользователь и заняла резервные слоты | После создания базы: `ALTER USER dbuser WITH NOSUPERUSER;` [1С] |
| 7 | В `pg_hba.conf` стоит `trust` или `0.0.0.0/0` «чтобы заработало» | Ошибку аутентификации обошли вместо исправления | Конкретные адреса и `scram-sha-256` |
| 8 | После «очистки» `pg_wal` вручную сервер не стартует или потеряны данные | Удалены нужные сегменты WAL | Восстановление из резервной копии; впредь — раздел 10 |
| 9 | База растёт, запросы деградируют, через месяцы — предупреждения о wraparound | `autovacuum = off` «чтобы не мешал» | `autovacuum = on` всегда [1С][PGPro]; раздел 6.8 |
| 10 | После сбоя питания или хоста база повреждена | `fsync = off` / `full_page_writes = off` «для скорости»; кэш записи без защиты | Оба параметра `on`; для скорости — `synchronous_commit = off` [1С] |
| 11 | После копирования `postgresql.conf` с другого сервера PostgreSQL не запускается | В файле библиотеки и параметры другой сборки или версии | До перезапуска: `SELECT * FROM pg_file_settings WHERE error IS NOT NULL;`; после — журнал службы |
| 12 | Настройки взяты из генератора (PGTune и т. п.) без правок, 1С работает медленно | Нет параметров, специфичных для 1С: `jit = off`, `max_parallel_workers_per_gather = 0`, `standard_conforming_strings = off`, `max_locks_per_transaction`, `join_collapse_limit` и др. | Сверить с рекомендациями [1С][PGPro] |
| 13 | `online_analyze` включён «по старой инструкции» | Рекомендации для старых версий платформы | Убрать либо задать параметры явно (6.3) |
| 14 | Резервная копия — копия каталога данных работающего сервера (`cp`, `rsync`, снимок диска без согласования) — не поднимается или даёт повреждённую базу | Несогласованная файловая копия | Только `pg_basebackup`, `pg_dump` или копия при остановленном сервере |
| 15 | После отката снимка ВМ «пропали» данные, не работают лицензии 1С, разошлись обмены | Снимок ВМ — не резервная копия базы | Резервное копирование средствами СУБД; снимки — только кратковременно перед работами |
| 16 | После `kill -9` одного процесса `postgres` отвалились все пользователи | Аварийное завершение серверного процесса вызывает перезапуск всех соединений и восстановление по WAL | `pg_cancel_backend(pid)` / `pg_terminate_backend(pid)` |
| 17 | После `apt upgrade` или `do-release-upgrade` 1С перестала работать с базой | Заменены пакеты сборки, сменились библиотеки ОС | Раздел 11.2; `apt-mark hold`; обновление ОС — через новую ВМ |
| 18 | Запрос из техжурнала в `psql` даёт другой план или 0 строк | Не заданы параметры сеанса платформы и `standard_conforming_strings = off` | Раздел 6.4 |
| 19 | Регламентные операции 1С обрываются по таймауту | Глобальные `statement_timeout`, `idle_session_timeout`, `idle_in_transaction_session_timeout`, `transaction_timeout` | Убрать из глобальной конфигурации и с роли 1С |
| 20 | Ищут блокировки в `pg_locks`, а там пусто | Пользователи ждут управляемые блокировки 1С | Техжурнал `TLOCK`/`TTIMEOUT` (раздел 7) |
| 21 | Днём «всё встало» после запуска обслуживания | `VACUUM FULL`, `REINDEX` без `CONCURRENTLY`, `CLUSTER` берут `ACCESS EXCLUSIVE` | Только в окно обслуживания; `REINDEX … CONCURRENTLY`; `SET lock_timeout` в сеансе администратора |
| 22 | Разбирают последнюю ошибку в журнале | `current transaction is aborted…` — следствие | Искать первую ошибку того же `pid` |
| 23 | Заполнение одного тома остановило и базу, и копирование, и журналы | Данные, `pg_wal`, резервные копии, технологический журнал — на одном томе | Развести по томам; мониторинг порогов 80–90 % |
| 24 | PostgreSQL не стартует после увеличения `shared_buffers` или `max_connections` | `huge_pages = on`, резерв `vm.nr_hugepages` не пересчитан | Раздел 5.9 |
| 25 | «На тестовой базе блокировок нет, а на рабочей есть» | Параллельность на пустой или малой базе непоказательна [1С] | Тестировать на копии рабочей базы под нагрузкой |
| 26 | Гостевая ВМ «то быстрая, то медленная» без причин внутри неё | Энергосбережение и переподписка на хосте, динамическая память | Раздел 6.9 |

---

## Быстрая шпаргалка — «задача → команда»

| Задача | Команда |
|---|---|
| Состояние экземпляров PostgreSQL | `pg_lsclusters` |
| Состояние и журнал службы | `sudo systemctl status postgresql@17-main`; `sudo journalctl -u postgresql@17-main -n 50 --no-pager` |
| Журнал сервера | `sudo tail -n 200 /var/log/postgresql/postgresql-17-main.log` |
| Где журнал в другой сборке | `sudo -u postgres psql -Atc "SELECT pg_current_logfile()"` |
| Только ошибки | `sudo grep -E 'ERROR\|FATAL\|PANIC' /var/log/postgresql/postgresql-17-main.log \| tail -n 50` |
| Кто слушает порт | `sudo ss -tlnp \| grep 5432` |
| Принимает ли сервер соединения | `pg_isready -h pg-server -p 5432` |
| Проверка входа, как у 1С | `sudo -u usr1cv8 psql "host=pg-server port=5432 dbname=postgres user=postgres" -c "select 1"` |
| Правила `pg_hba.conf` и ошибки в них | `SELECT line_number, type, database, user_name, address, auth_method, error FROM pg_hba_file_rules;` |
| Применить `pg_hba.conf` | `sudo systemctl reload postgresql@17-main` |
| Тип хеша пароля | `SELECT rolname, left(rolpassword, 14) FROM pg_authid WHERE rolcanlogin;` |
| Задать пароль заново | `sudo -u postgres psql -c "\password postgres"` |
| Открыть порт для сервера 1С | `sudo ufw allow from 192.168.10.20 to any port 5432 proto tcp` |
| Занятые соединения | `SELECT count(*), current_setting('max_connections') FROM pg_stat_activity;` |
| Сборка и модули 1С | `SELECT version();` `SELECT name FROM pg_available_extensions WHERE name IN ('mchar','fulleq','fasttrun');` |
| Зависимости библиотеки модуля | `ldd /usr/lib/postgresql/17/lib/mchar.so \| grep 'not found'` |
| Защитить сборку 1С от замены | `sudo apt-mark hold postgresql-17 postgresql-client-17 libpq5` |
| Локали ОС и баз | `locale -a \| grep ru_RU`; `SELECT datname, datcollate, datctype FROM pg_database;` |
| Сгенерировать локаль | `sudo locale-gen ru_RU.UTF-8 && sudo systemctl restart postgresql@17-main` |
| Пересоздать пустой кластер с локалью | `sudo pg_dropcluster --stop 17 main && sudo pg_createcluster --locale=ru_RU.UTF-8 17 main --start` |
| Дать и снять права на время создания базы | `ALTER ROLE dbuser WITH SUPERUSER;` … `ALTER USER dbuser WITH NOSUPERUSER;` |
| Права на схему `public` (15+) | `ALTER DATABASE buh OWNER TO dbuser;` или `GRANT ALL ON SCHEMA public TO dbuser;` |
| Удалить базу с подключениями (13+) | `DROP DATABASE buh WITH (FORCE);` / `dropdb --force buh` |
| Отключить всех от базы | `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='buh' AND pid <> pg_backend_pid();` |
| Таблица блокировок переполнена | `max_locks_per_transaction = 512` → `restart` |
| Следы OOM killer | `sudo dmesg -T \| grep -i -E 'out of memory\|killed process'` |
| Лимиты процесса PostgreSQL | `sudo cat /proc/$(sudo head -1 /var/lib/postgresql/17/main/postmaster.pid)/limits` |
| Поднять лимит файлов | `sudo systemctl edit postgresql@17-main` → `[Service]` `LimitNOFILE=65536` → `restart` |
| Временные файлы сейчас | `SELECT name, pg_size_pretty(size) FROM pg_ls_tmpdir() ORDER BY size DESC LIMIT 10;` |
| Срез ожиданий | `SELECT state, wait_event_type, wait_event, count(*) FROM pg_stat_activity GROUP BY 1,2,3 ORDER BY 4 DESC;` |
| Кто кого блокирует | `SELECT pid, pg_blocking_pids(pid), left(query,80) FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;` |
| Долгие и зависшие транзакции | `SELECT pid, state, now()-xact_start, left(query,80) FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start;` |
| Отменить запрос / завершить соединение | `SELECT pg_cancel_backend(pid);` / `SELECT pg_terminate_backend(pid);` |
| Журналировать ожидания блокировок | `ALTER SYSTEM SET log_lock_waits = on; SELECT pg_reload_conf();` |
| План «как у платформы» | `SET enable_mergejoin = off; SET cpu_operator_cost = 0.001; SET standard_conforming_strings = off;` → `EXPLAIN (ANALYZE, BUFFERS) …` |
| Самые затратные запросы | `SELECT calls, total_exec_time, left(query,100) FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;` |
| Мёртвые строки и автоочистка | `SELECT relname, n_dead_tup, last_autovacuum FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;` |
| Обновить статистику всей базы | `sudo -u postgres vacuumdb --analyze -j 4 -d buh` |
| Скорость синхронной записи | `sudo -u postgres /usr/lib/postgresql/17/bin/pg_test_fsync -f /var/lib/postgresql/17/main/t.tmp` |
| Размер `pg_wal` | `SELECT count(*), pg_size_pretty(sum(size)) FROM pg_ls_waldir();` |
| Слоты репликации | `SELECT slot_name, active, wal_status, restart_lsn FROM pg_replication_slots;` |
| Удалить забытый слот | `SELECT pg_drop_replication_slot('имя'); CHECKPOINT;` |
| Состояние архивации | `SELECT archived_count, failed_count, last_failed_wal FROM pg_stat_archiver;` |
| Расширить том LVM | `sudo vgs; sudo lvextend -r -L +20G /dev/ubuntu-vg/ubuntu-lv` |
| Проверить индексы и таблицы | `sudo -u postgres pg_amcheck -d buh --install-missing --heapallindexed -j 4 -P` |
| Перестроить индексы после смены ОС | `sudo -u postgres reindexdb -d buh -j 4` → `ALTER DATABASE buh REFRESH COLLATION VERSION;` |
| Возраст счётчика транзакций | `SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;` |
| Контрольные суммы включены? | `SHOW data_checksums;` |
| Что не по умолчанию в конфигурации | `SELECT name, setting, sourcefile FROM pg_settings WHERE source NOT IN ('default','override');` |
| Ошибки в файлах конфигурации до перезапуска | `SELECT * FROM pg_file_settings WHERE error IS NOT NULL;` |
| Сеансы 1С и их соединения с СУБД | `rac session list --cluster=$CL` (поля `db-proc-info`, `blocked-by-dbms`, `blocked-by-ls`) |
| Заблокировать вход и регламентные задания | `rac infobase update --cluster=$CL --infobase=$IB … --sessions-deny=on --scheduled-jobs-deny=on` |

---

## Источники

PostgreSQL (postgresql.org) — прочитано при подготовке:

- https://www.postgresql.org/docs/17/server-start.html — ошибки запуска сервера и подключения клиентов: `could not bind`, `could not create semaphores: No space left on device`, `Connection refused`, новый формат сообщений libpq.
- https://www.postgresql.org/docs/17/client-authentication-problems.html — `no pg_hba.conf entry`, `password authentication failed`, `database … does not exist`.
- https://www.postgresql.org/docs/17/auth-password.html — методы `scram-sha-256`/`md5`/`password`, автоматический переход `md5` → SCRAM, порядок миграции.
- https://www.postgresql.org/docs/17/runtime-config-connection.html — `listen_addresses`, `max_connections`, `superuser_reserved_connections`, `reserved_connections`, `password_encryption`.
- https://www.postgresql.org/docs/17/sql-createdatabase.html — правила совпадения кодировки и локали с шаблоном, `template0`, `could not initialize database directory`, требования к шаблону.
- https://www.postgresql.org/docs/17/runtime-config-locks.html — `max_locks_per_transaction`, `deadlock_timeout`.
- https://www.postgresql.org/docs/17/explicit-locking.html — режимы блокировок таблиц и строк, какие команды их берут, поведение при взаимоблокировках.
- https://www.postgresql.org/docs/17/kernel-resources.html — OOM killer, `vm.overcommit_memory`, `oom_score_adj`, `RemoveIPC`, лимиты файлов и семафоров.
- https://www.postgresql.org/docs/17/runtime-config-resource.html — `max_stack_depth`, `temp_file_limit`, `dynamic_shared_memory_type`, `max_files_per_process`, `work_mem`, `temp_buffers`, `hash_mem_multiplier`, `huge_pages`.
- https://www.postgresql.org/docs/17/runtime-config-client.html — `lock_timeout`, `statement_timeout`, `idle_in_transaction_session_timeout`, `idle_session_timeout`, `transaction_timeout`, `temp_tablespaces`, `row_security`.
- https://www.postgresql.org/docs/17/runtime-config-autovacuum.html — умолчания автоочистки, запуск при `autovacuum = off` для защиты от wraparound.
- https://www.postgresql.org/docs/17/routine-vacuuming.html — тексты предупреждений о wraparound, пороги 40 млн / 3 млн, порядок действий, запросы возраста.
- https://www.postgresql.org/docs/17/runtime-config-developer.html — `zero_damaged_pages`, `ignore_checksum_failure`, `ignore_system_indexes`.
- https://www.postgresql.org/docs/17/checksums.html, https://www.postgresql.org/docs/17/app-pgamcheck.html, https://www.postgresql.org/docs/17/app-pgresetwal.html — контрольные суммы, проверка `pg_amcheck`, условия применения `pg_resetwal`.
- https://www.postgresql.org/docs/17/sql-altercollation.html, https://www.postgresql.org/docs/17/sql-alterdatabase.html — несовпадение версии правил сортировки, `REFRESH COLLATION VERSION`.
- https://www.postgresql.org/docs/17/continuous-archiving.html, https://www.postgresql.org/docs/17/runtime-config-replication.html, https://www.postgresql.org/docs/17/diskusage.html — рост `pg_wal` при сбое архивации, PANIC при заполнении тома WAL, `max_slot_wal_keep_size`, `wal_keep_size`.
- https://www.postgresql.org/docs/17/limits.html — пределы: поле 1 ГБ, 1600 колонок, 1664 колонки результата, 32 колонки индекса, 63 байта идентификатора.
- https://www.postgresql.org/docs/17/pgprewarm.html — автопрогрев кэша.
- https://www.postgresql.org/docs/14/release-14.html, https://www.postgresql.org/docs/15/release-15.html, https://www.postgresql.org/docs/18/release-18.html, https://www.postgresql.org/docs/19/release-19.html — несовместимые изменения версий 14, 15, 18 и 19 (при подготовке — Beta 4 от 24.09.2026; при сверке 19.10.2026 — RC 1 от 15.10.2026; все упомянутые в статье несовместимости 19-й версии в редакции примечаний на 09.10.2026 на месте).
- https://wiki.postgresql.org/wiki/Locale_data_changes — изменение правил сортировки в glibc 2.28, затронутые дистрибутивы, симптомы, проверка командой `sort`.
- https://wiki.postgresql.org/wiki/Corruption — порядок действий при повреждении, типовые причины, инструменты.

Postgres Professional — прочитано при подготовке:

- https://postgrespro.ru/docs/postgrespro/17/config-one-c и подстраницы `one-c-configuring-locale`, `one-c-configuring-server`, `one-c-additional-modules` — локаль до создания кластера, значения параметров для 1С (включая объяснение `max_locks_per_transaction = 256`), встроенные модули, рекомендация не использовать `online_analyze` с современными версиями 1С, `pg_hint_plan`.
- https://postgrespro.ru/docs/postgrespro/17/mchar — типы `mchar`/`mvarchar`: UTF-16, ICU, регистронезависимые и регистрозависимые операторы.
- https://postgrespro.ru/docs/postgrespro/17/online-analyze — параметры модуля и их умолчания.
- https://postgrespro.ru/docs/postgrespro/17/typeconv-oper — разрешение операторов для нестандартных типов при `pg_restore`/`pg_upgrade`.

Фирма «1С»:

- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/subd-postgresql/ — поддерживаемые сборки и версии (PostgreSQL с патчем от 1С 18.4-1.1C, 17.10-2.1C, 16.14-1.1C, 15.18-1.1C, 14.23-1.1C; Postgres Pro; Tantor), список ОС, включая Ubuntu 20.04–26.04.
- https://v8.1c.ru/platforma/upravlenie-blokirovkami-v-tranzakcii/ — режимы управления блокировками (таблица по СУБД на странице — картинка).
- https://v8.1c.ru/platforma/postgresql/ — общие сведения о сборке PostgreSQL с патчем от 1С.
- Методические статьи ИТС — по конспектам этой базы знаний (`kb/its-metod/`): https://its.1c.ru/db/metod8dev/content/5866/hdoc («Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2»), https://its.1c.ru/db/metod8dev/content/6011/hdoc (методика расследования производительности PostgreSQL, параметры сеанса платформы), https://its.1c.ru/db/metod8dev/content/6031/hdoc и https://its.1c.ru/db/metod8dev/content/6039/hdoc (`auto_dump`), https://its.1c.ru/db/metod8dev/content/6035/hdoc (`enable_temp_rd_buffers`), https://its.1c.ru/db/metod8dev/content/4208/hdoc (СрезПоследних), https://its.1c.ru/db/metod8dev/content/1556/hdoc (полное внешнее соединение), https://its.1c.ru/db/metod8dev/content/2313/hdoc (ошибки базы данных и транзакции), https://its.1c.ru/db/metod8dev/content/2707/hdoc (блокировки регистров, тестирование на пустой базе), https://its.1c.ru/db/metod8dev/content/6006/hdoc и https://its.1c.ru/db/metod8dev/content/4051/hdoc (методика расследования ошибок блокировок и взаимоблокировок, позиция разработчиков по PostgreSQL).
- Документация платформы 8.3.27 / 8.5.1 — по конспектам `kb/its-docs/`: привилегия `SUPERUSER` на момент создания базы, формат поля «Сервер баз данных» с портом, ограничения имени базы, смена «Язык (Страна)», невозможность удаления соединения для PostgreSQL, оптимизированная реструктуризация (`UpdateDBCfg=v2`), требования к локали кластера.

Смежные статьи этой базы знаний: `kb/postgresql/01`–`07`, `kb/1c/03`, `kb/1c/07`, `kb/linux/04`, `kb/linux/07`, `kb/linux/09`.

Использовано при независимой сверке 19.10.2026:

- Документация PostgreSQL 18 (текстовые копии от 10–11.10.2026): `runtime-config-*` (умолчания и описания параметров), `postgresql.conf.sample` 18, `kernel-resources` (18.4.1 — в Linux семафоры POSIX, System V не используются; 18.4.2 `RemoveIPC`; 18.4.4 OOM), `routine-vacuuming`, `sql-createdatabase`, `sql-reindex`, `app-pgamcheck`, `amcheck`, `pgprewarm`, `pgtestfsync`, `app-dropdb`, `app-vacuumdb`, `app-pgrestore`, `app-initdb`, представления `pg_hba_file_rules`, `pg_replication_slots`, `pg_prepared_xacts`; примечания к выпускам 13–18; https://www.postgresql.org/docs/18/explicit-locking.html; https://www.postgresql.org/docs/15/routine-vacuuming.html и …/16/routine-vacuuming.html; https://www.postgresql.org/docs/19/release-19.html (редакция на 09.10.2026; на сайте — объявление о RC 1 от 15.10.2026).
- Исходный код PostgreSQL (`raw.githubusercontent.com/postgres/postgres/REL_NN_STABLE/…`): `src/backend/libpq/auth.c` (ветки 11–18: `no encryption` с 14-й, `connection authenticated: … method=…`), `src/interfaces/libpq/fe-connect.c` (13 и 14: новый формат `connection to server at …`), `src/backend/commands/dbcommands.c` (14, 15, 16, 18: тексты о локали и кодировке), `src/backend/access/transam/varsup.c` (14–18: тексты о wraparound).
- Документация «PostgreSQL для 1С» 16 от Postgres Professional (https://repo.postgrespro.ru/doc/pg1c/16/ru/html/): приложение K (K.1–K.4), F.5 `auto_dump`, F.19 `fasttrun`, F.21 `fulleq`, F.29 `mchar`, F.30 `online_analyze`, F.45 `plantuner`, перечень модулей приложения F, `pg-setup`, 10.2.1 `typeconv-oper`; юнит `postgrespro-1c-16.service` из пакета `postgrespro-1c-16-server` 16.14. Postgres Pro 17: https://postgrespro.ru/docs/postgrespro/17/one-c-additional-modules (K.4.6 `pg_hint_plan`); Postgres Pro Enterprise 17: https://postgrespro.ru/docs/enterprise/17/pgupgrade («Примечания»: 64-битный формат страниц, преобразование после `pg_upgrade`).
- https://packages.ubuntu.com/resolute/libc6 (glibc 2.43 в 26.04) и поиск `libicu` для resolute (`libicu78`).
- https://raw.githubusercontent.com/MicrosoftDocs/sql-docs/live/docs/sql-server/maximum-capacity-specifications-for-sql-server.md — число таблиц в `SELECT`, предел ключа индекса 900/1700 байт.
- Конспекты базы знаний: `../its-docs/adm-gl05-spisok-infobaz.md` (5.2.1.3.7 — инициализация ИБ в существующей базе), `../its-docs/adm-gl06-administrirovanie-ib-p3.md` (6.14 — ТЖ по умолчанию в `~/.1cv8/1C/1cv8/logs`, перечитывание `logcfg.xml` раз в 60 секунд), `../its-docs/adm-pr03-sluzhebnye-fajly-p3.md` и `-p5.md` (3.24.1 — ТЖ по умолчанию в `~/.1cv8/logs`; `TDEADLOCK`, `WaitConnections`, свойства `<dbmslocks>`), `../its-docs/dev-gl09-rabota-s-dannymi.md` (9.2.3.2 — режимы блокировок по СУБД), `../its-docs/cs-gl01-trebovaniya.md` и `cs-gl05-administrirovanie-klastera-p2/p3.md`, `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`, `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, `../its-metod/monitoring-i-audit.md` (тексты ошибок управляемых блокировок), `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`, `../its-metod/ekspluataciya-krupnoj-sistemy-blokirovki-tranzakcii.md`, `../its-metod/razmeshchenie-dannyh-i-indeksy.md`; `../guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`.

Не удалось прочитать или проверить при подготовке:

- Поиск по интернету был недоступен: материалы Infostart, Habr, forum.mista.ru, wiki.astralinux.ru, altlinux.org напрямую не сверялись; пункты с пометкой [практика] основаны на общеизвестной практике.
- Страницы its.1c.ru (документация платформы и metod8dev) автоматическому загрузчику отдаются с искажённой кириллицей либо закрыты подпиской. Не подтверждены первоисточником: точные тексты сообщений платформы 1С (кроме приведённых в конспектах ИТС), версия платформы с поддержкой `scram-sha-256`, точный SQL блокировок автоматического режима, официальные пределы размеров полей при работе с PostgreSQL, сообщение «DATABASE не пригоден для использования».

