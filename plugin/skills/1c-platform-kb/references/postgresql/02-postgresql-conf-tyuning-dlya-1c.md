# Настройка postgresql.conf, pg_hba.conf и ОС под нагрузку 1С

> **Официальные тексты по теме** (конспекты документации ИТС 8.3.27 и методических статей ИТС, составлены по полным текстам): `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`, `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`. Статья писалась до получения доступа к закрытой документации: там, где ниже сказано «документация закрыта», «не прочитано» или стоит ⚠, сверяйтесь с этими конспектами — при расхождении правы они.

> Область: параметры `postgresql.conf` (память, WAL, контрольные точки, планировщик, autovacuum, блокировки, расширения), `pg_hba.conf` и тюнинг Ubuntu Server под PostgreSQL, обслуживающий «1С:Предприятие 8» в клиент-серверном варианте; готовые стартовые конфигурации для ВМ 8–128 ГБ | Версии: PostgreSQL 14–18 (сборки с патчем 1С `18.4-1.1C`, `17.10-2.1C`, `16.14-1.1C`, `15.18-1.1C`, `14.23-1.1C`; Postgres Pro Standard/1C 14–18), взгляд вперёд на PostgreSQL 19 (на 10.10.2026 — Beta 4); Ubuntu 22.04 / 24.04 / 26.04; платформа 1С 8.3.2x / 8.5.x | Актуальность: 2026-10-10

Метки источников в тексте:

- **[1С]** — методические статьи ИТС, прежде всего «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2» (ред. 19.06.2025). Подробный конспект — в `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md`.
- **[1С-6011]** — статья ИТС «Методика расследования проблем производительности на уровне работы СУБД PostgreSQL» (21.02.2023, https://its.1c.ru/db/metod8dev/content/6011/hdoc): из неё известно, какие параметры сеанса платформа задаёт сама. Конспект — в `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`.
- **[PGPro]** — документация Postgres Pro Standard 17/18, приложение K «Настройка Postgres Pro для решений 1С».
- **[PG]** — документация PostgreSQL 18 (postgresql.org), примечания к выпускам 15–19.
- **[Canonical]** — документация и примечания к выпуску Ubuntu.
- **[Tantor]** — документация Tantor SE 1C 17.
- **[практика]** — практика сообщества и расчёты автора статьи; не официальная рекомендация.
- **⚠ не подтверждено** — утверждение не удалось проверить по первоисточнику; перед применением проверить на стенде.

Статус проверки (рецензия 10.10.2026): значения [PGPro] сверены напрямую со страницами K.2–K.4 документации Postgres Pro Standard 17 и 18; умолчания, контексты и формулировки [PG] — со страницами документации PostgreSQL 18 и 19 (бета); версии — с postgresql.org и v8.1c.ru; известная проблема Ubuntu 26.04 — с примечаниями к выпуску; формулы PGTune — с исходным кодом. Значения [1С] сверены **только с конспектами этой базы знаний**: страницы its.1c.ru без подписки не читаются.

## Кратко

1. **Официальных источников два, и они почти совпадают:** [1С] «Часть 2» (2025) и [PGPro] приложение K. Оба называют свои числа «отправной точкой», а не готовым ответом. Формулы считаются от памяти, **доступной именно PostgreSQL**: если на той же ВМ работает сервер 1С, его память сначала вычитают [1С].
2. **Память:** `shared_buffers = RAM/4`, `effective_cache_size = RAM − shared_buffers`, `work_mem = RAM/32..64` или `32MB..256MB`, `maintenance_work_mem = RAM/16..32` или `256MB..4GB`, `temp_buffers = 32..256MB` [1С][PGPro].
3. **Обязательное для платформы 1С (PostgreSQL ≤ 18):** `standard_conforming_strings = off`, `escape_string_warning = off`; `max_locks_per_transaction` — 256 [PGPro] или 512…2000 [1С]; `max_connections` — не меньше 500 [PGPro], 500..8000 [1С].
4. **WAL:** `fsync = on` всегда; `synchronous_commit = off` официально рекомендован для 1С — при сбое теряются транзакции последних 0,5–1 с, целостность базы сохраняется [1С][PGPro][PG]. `full_page_writes` не трогать.
5. **Контрольные точки и фоновая запись:** `checkpoint_timeout = 15min` [PGPro], `min_wal_size = 512MB..4GB`, `max_wal_size = 2 × min_wal_size`, `bgwriter_delay = 20ms`, `bgwriter_lru_multiplier = 4.0`, `bgwriter_lru_maxpages = 400` [1С][PGPro].
6. **Планировщик:** `random_page_cost = 1.1–1.3` для SSD, `from_collapse_limit = 20`, `join_collapse_limit = 20`, `geqo = on`, `geqo_threshold = 12`, `jit = off` [1С][PGPro]; `max_parallel_workers_per_gather = 0` [PGPro]. Параметры `enable_mergejoin = off` и `cpu_operator_cost = 0.001` в конфигурацию сервера вносить **не нужно**: платформа 1С сама задаёт их командой `SET` в каждом своём сеансе [1С-6011] (раздел 3.5).
7. **Autovacuum не выключать никогда.** `autovacuum_max_workers` = от ядер/4 до ядер/2, но не меньше 4; `autovacuum_naptime = 20s` [1С][PGPro].
8. **Расширения:** `plantuner` (`plantuner.fix_empty_table = on`) [PGPro]; `online_analyze` для современных версий 1С **не рекомендуется** и включается только при доказанной необходимости [1С][PGPro]. Сообщество по старой памяти включает оба — это расхождение с актуальной официальной позицией.
9. **PostgreSQL 19 ломает привычный конфиг 1С:** `standard_conforming_strings` всегда `on` (выставить `off` нельзя), `escape_string_warning` удалён [PG]. Сборок 1С для 19-й ветки на 10.10.2026 нет; при будущем переходе эти строки из конфига нужно убрать.
10. **Куда писать:** в Debian-раскладке — отдельный файл `/etc/postgresql/NN/main/conf.d/90-1c.conf`. `ALTER SYSTEM` пишет в `postgresql.auto.conf`, и он **сильнее** `postgresql.conf` и `conf.d` [PG].
11. **Применить:** `sudo systemctl reload postgresql@NN-main` или `SELECT pg_reload_conf();`. Параметрам с `context = postmaster` нужен перезапуск: `shared_buffers`, `max_connections`, `max_locks_per_transaction`, `huge_pages`, `shared_preload_libraries`, `wal_level`, `max_files_per_process`, `listen_addresses`, `io_method`.
12. **Проверить:** `SHOW имя;`, `SELECT name, setting, source, sourcefile, pending_restart FROM pg_settings WHERE source <> 'default';`, ошибки в файлах до перезагрузки — `SELECT * FROM pg_file_settings WHERE NOT applied;`.
13. **Huge pages:** `sudo -u postgres postgres -D … -C shared_memory_size_in_huge_pages` (сервер остановлен) → `vm.nr_hugepages` → `huge_pages = on`. На **Ubuntu 26.04 (ядро 7.0)** это не оптимизация, а обход известной регрессии PostgreSQL [Canonical].
14. **THP для PostgreSQL «discouraged»** [PG]. В Ubuntu режим по умолчанию, по практике, `madvise` (происхождение умолчания подтверждено рассылкой kernel-team Ubuntu — правка 2017 года для 17.10, см. раздел 6; для ядер 22.04–26.04 отдельно не подтверждено документацией Canonical — проверяйте командой `cat /sys/kernel/mm/transparent_hugepage/enabled`) — этого обычно достаточно; строгий вариант — `transparent_hugepage=never`.
15. **ОС:** `vm.swappiness = 1..10`, `vm.dirty_background_bytes = 67108864`, `vm.dirty_bytes = 536870912`, `vm.overcommit_memory = 2` только на выделенном сервере СУБД, `noatime`, отключить энергосбережение CPU [1С][PGPro][практика].
16. **pg_hba.conf:** правила читаются сверху вниз, срабатывает первое совпавшее, «проваливания» дальше нет. Сервер 1С подключается по TCP — нужна строка `host` (даже для `127.0.0.1`). Метод — `scram-sha-256`; `md5` объявлен устаревшим в PostgreSQL 18 [PG].
17. **Калькуляторы (PGTune и т. п.) не знают про 1С:** не выставляют параметры совместимости, `max_locks_per_transaction`, `synchronous_commit`, включают параллельные запросы, дают маленький `work_mem`. Их результат — только заготовка для блока памяти.
18. **Главные ошибки:** большой `work_mem`/`temp_buffers` при сотнях соединений, выключенный autovacuum, `fsync = off` в продуктиве, гигантский `shared_buffers` без huge pages, правка `postgresql.conf` при наличии того же параметра в `postgresql.auto.conf`.
19. **Платформа 1С сама настраивает свой сеанс** [1С-6011]: `SET client_min_messages = error`, `lc_messages = 'en_US.UTF-8'`, `enable_mergejoin = off`, `escape_string_warning = off`, `cpu_operator_cost = 0.001`, `client_encoding = 'utf8'`, `lock_timeout = 20000`. Отсюда три следствия: эти параметры из `postgresql.conf` на сеансы 1С не действуют (сеансовый `SET` сильнее файла); план запроса в `psql` совпадёт с платформенным, только если задать те же `SET`; на сервере СУБД должна быть сгенерирована локаль `en_US.UTF-8` (последнее — вывод из механики PostgreSQL и практика сообщества, ⚠ в статьях ИТС прямо не сказано; раздел 3.5).
20. **Роль 1С:** для создания информационной базы из 1С роли нужна привилегия `SUPERUSER` (одного `CREATEDB` недостаточно); после создания базы её можно снять — `ALTER USER … WITH NOSUPERUSER` (документация платформы, раздел 8.2).

---

## 1. Версии, сборки, расположение файлов

### 1.1. Что актуально на 10.10.2026

| Что | Версия | Источник |
|---|---|---|
| PostgreSQL (сообщество) | 18.6, 17.11, 16.15, 15.19, 14.24 | [PG] страница выпусков |
| PostgreSQL 19 | **Beta 4 от 24.09.2026**, финального выпуска нет | [PG] |
| PostgreSQL с патчем 1С | 18.4-1.1C, 17.10-2.1C, 16.14-1.1C, 15.18-1.1C, 14.23-1.1C; ОС: Ubuntu 20.04/22.04/24.04/26.04 и др. | v8.1c.ru |
| Postgres Pro 1C | 18.4, 17.10, 16.14, 15.18, 14.23 | v8.1c.ru |
| Postgres Pro Standard / Enterprise | 18.4.1, 17.10.1, … (в списке 1С); документация вендора — 17.11.2 и 18.6.2 | v8.1c.ru, postgrespro.ru |
| Tantor SE 1C | 18.3.1, 17.10.0, 16.14.0, 15.18.0, 14.23.0 | v8.1c.ru |
| Ubuntu 26.04 LTS | ядро 7.0, PostgreSQL 18 в репозитории | [Canonical] |

«Ванильный» PostgreSQL из репозитория Ubuntu или PGDG для 1С не подходит: нужны патчи (типы `mchar`/`mvarchar`, `fulleq`, `fasttrun` и др.). Рекомендации этой статьи рассчитаны на сборку с патчем 1С или Postgres Pro.

### 1.2. Где лежит конфигурация

| | Debian-раскладка (PostgreSQL с патчем 1С, пакеты Ubuntu/PGDG) | Раскладка Postgres Pro |
|---|---|---|
| `postgresql.conf` | `/etc/postgresql/NN/main/postgresql.conf` | `/var/lib/pgpro/1c-NN/data/postgresql.conf` (Standard: `/var/lib/pgpro/std-NN/data/`) |
| Доп. файлы | `/etc/postgresql/NN/main/conf.d/*.conf` | по умолчанию нет; можно добавить `include_dir` |
| `pg_hba.conf` | `/etc/postgresql/NN/main/pg_hba.conf` | в каталоге данных |
| `postgresql.auto.conf` | `/var/lib/postgresql/NN/main/postgresql.auto.conf` | в каталоге данных |
| Бинарники | `/usr/lib/postgresql/NN/bin/` | `/opt/pgpro/1c-NN/bin/` (Standard: `/opt/pgpro/std-NN/bin/`) |
| Служба | `postgresql@NN-main.service` | `postgrespro-1c-NN.service` (`postgrespro-std-NN`) |
| Журнал | `/var/log/postgresql/postgresql-NN-main.log` | `log/` в каталоге данных либо journald |

Узнать точно на живом сервере:

```sql
SHOW config_file;      -- основной файл
SHOW hba_file;         -- pg_hba.conf
SHOW data_directory;   -- каталог данных (там же postgresql.auto.conf)
SELECT version();
```

Во всех примерах ниже используется Debian-раскладка и версия 17 (`NN = 17`); для другой версии замените число.

---

## 2. Куда писать настройки и как их применять

### 2.1. Источники значений и их приоритет

От слабого к сильному [PG]:

1. Встроенное умолчание (`boot_val`).
2. `postgresql.conf` и всё, что он подключает директивами `include`, `include_if_exists`, `include_dir`. Файлы читаются по порядку; если параметр встречается несколько раз — **действует последнее вхождение**. В `include_dir` берутся только файлы `*.conf`, не начинающиеся с точки, в порядке имён по правилам локали C (цифры раньше букв, заглавные раньше строчных).
3. `postgresql.auto.conf` — файл, который пишет `ALTER SYSTEM`. Читается после `postgresql.conf` и **переопределяет его**.
4. Параметры командной строки сервера (`postgres -c имя=значение`) — сильнее файлов и `ALTER SYSTEM`.
5. `ALTER DATABASE … SET` и `ALTER ROLE … SET` (в том числе `ALTER ROLE … IN DATABASE … SET`) — применяются при открытии новой сессии и переопределяют файлы.
6. `SET` / `SET LOCAL` в сессии, `PGOPTIONS` у клиента.

Синтаксис `postgresql.conf` [PG]: один параметр на строку, знак `=` необязателен, имена нечувствительны к регистру, `#` — комментарий. Значения, не являющиеся простым числом или идентификатором, берутся в одинарные кавычки. Единицы памяти: `B`, `kB`, `MB`, `GB`, `TB` (множитель 1024); времени: `us`, `ms`, `s`, `min`, `h`, `d`. Разделители тысяч не допускаются.

### 2.2. Рекомендуемый способ для Debian-раскладки: отдельный файл в `conf.d`

Пакет `postgresql-common` при создании кластера добавляет в `postgresql.conf` строку `include_dir = 'conf.d'` и создаёт сам каталог (проверено по исходникам пакета: в `/etc/postgresql-common/createcluster.conf` по умолчанию активны `add_include_dir = 'conf.d'`, `ssl = on`, `cluster_name = '%v/%c'`, `log_line_prefix = '%m [%p] %q%u@%d '`; для версий до 14 включительно — ещё и `stats_temp_directory`). Свои настройки удобно держать отдельным файлом: основной `postgresql.conf` остаётся в исходном виде, а все отличия от него собраны в одном месте — их легко сравнить, перенести на другой сервер и откатить.

```bash
grep -n '^include' /etc/postgresql/17/main/postgresql.conf        # убедиться, что include_dir = 'conf.d' есть
sudo -u postgres nano /etc/postgresql/17/main/conf.d/90-1c.conf   # свои настройки
ls -l /etc/postgresql/17/main/conf.d/                             # владелец postgres, расширение .conf
```

Правила:

- Файл с большим номером (`90-…`) читается позже и побеждает файлы с меньшим номером и сам `postgresql.conf`. Но если строка `include_dir` стоит в середине `postgresql.conf`, параметры, заданные **ниже неё** в основном файле, окажутся сильнее `conf.d`. Проверяйте фактический источник по `pg_settings.sourcefile`.
- Перед правкой — копия: `sudo cp -a /etc/postgresql/17/main/postgresql.conf{,.bak-$(date +%F)}`.
- Точечно читать и менять параметр в основном файле можно утилитой `pg_conftool`: `pg_conftool 17 main show shared_buffers`, `sudo pg_conftool 17 main set max_connections 500`.

### 2.3. ALTER SYSTEM и postgresql.auto.conf

```sql
ALTER SYSTEM SET work_mem = '64MB';      -- записать в postgresql.auto.conf
ALTER SYSTEM RESET work_mem;             -- убрать одну запись
ALTER SYSTEM RESET ALL;                  -- очистить файл целиком
SELECT pg_reload_conf();                 -- применить (для параметров, не требующих перезапуска)
```

- Команда только пишет в файл; чтобы значение начало действовать, нужен reload или restart.
- `postgresql.auto.conf` руками не редактируют, пока сервер работает: параллельный `ALTER SYSTEM` может затереть правку [PG].
- В PostgreSQL 17+ команду можно запретить параметром `allow_alter_system = off` (задаётся только в файле или командной строке; это защита от случайностей, а не средство безопасности) [PG].
- Типичная ловушка: параметр когда-то задали через `ALTER SYSTEM`, потом правят `postgresql.conf` — и «ничего не меняется». Диагностика — колонка `sourcefile` в `pg_settings`.

Выбор способа: постоянные настройки сервера — в `conf.d/90-1c.conf` (видны в файле, удобно сравнивать и переносить); `ALTER SYSTEM` — когда нет доступа к файловой системе или для временных экспериментов, после которых делается `RESET`.

### 2.4. Настройки на уровне базы и роли

Полезно, когда на одном сервере несколько баз 1С с разным характером нагрузки, или нужно ограничить отдельную учётную запись, не трогая сервер целиком:

```sql
ALTER DATABASE buh SET work_mem = '128MB';
ALTER ROLE report_user SET statement_timeout = '10min';
ALTER ROLE usr1cv8 IN DATABASE zup SET enable_nestloop = off;   -- только как временная мера при разборе плохого плана
SELECT d.datname, r.rolname, s.setconfig                        -- посмотреть, что задано
FROM pg_db_role_setting s
LEFT JOIN pg_database d ON d.oid = s.setdatabase
LEFT JOIN pg_roles r ON r.oid = s.setrole;
```

Значения применяются только к **новым** сессиям. Сервер 1С держит пул соединений, поэтому, чтобы настройка подействовала наверняка, перезапустите рабочие процессы `rphost` или дождитесь пересоздания соединений.

### 2.5. reload и restart

```bash
# Перечитать конфигурацию без разрыва сессий (любой из вариантов)
sudo systemctl reload postgresql@17-main
sudo pg_ctlcluster 17 main reload
sudo -u postgres psql -c "SELECT pg_reload_conf();"

# Перезапуск (разрывает все соединения 1С; делать в окно обслуживания)
sudo systemctl restart postgresql@17-main
sudo pg_ctlcluster 17 main restart

# Postgres Pro
sudo systemctl reload postgrespro-1c-17
sudo systemctl restart postgrespro-1c-17
```

При reload главный процесс перечитывает файлы и передаёт сигнал всем серверным процессам; работающие сессии подхватывают новые значения после завершения текущей команды [PG]. Неверные значения при reload **игнорируются с записью в журнал** — сервер продолжает работать на старых. При старте же неверное значение или неизвестный параметр приводят к отказу запуска. Поэтому после правки сначала проверяйте файл (раздел 2.6), потом делайте reload, и только затем — restart, если он нужен.

Перед перезапуском PostgreSQL корректно остановить сервер 1С (`sudo systemctl stop srv1cv8-…@default`) или хотя бы убедиться, что пользователей нет: иначе рабочие процессы получат разрыв соединений с СУБД.

### 2.6. Как проверить, что применилось

```sql
-- 1. Текущее значение
SHOW shared_buffers;
SELECT current_setting('work_mem');

-- 2. Всё, что отличается от умолчаний, и откуда взято
SELECT name, setting, unit, source, sourcefile, sourceline, pending_restart
FROM pg_settings
WHERE source NOT IN ('default', 'override')
ORDER BY sourcefile, sourceline;

-- 3. Что изменено в файлах, но ждёт перезапуска
SELECT name, setting, context FROM pg_settings WHERE pending_restart;

-- 4. Проверка файлов ДО reload: ошибки и «проигравшие» строки
SELECT sourcefile, sourceline, name, setting, applied, error
FROM pg_file_settings
WHERE NOT applied OR error IS NOT NULL;

-- 5. Нужен ли параметру перезапуск
SELECT name, context, vartype, min_val, max_val, enumvals, boot_val, reset_val
FROM pg_settings
WHERE name IN ('shared_buffers', 'work_mem', 'synchronous_commit', 'max_locks_per_transaction');
```

Колонки `pg_settings` [PG]: `setting` — действующее значение (в единицах `unit`), `source` — откуда оно (`default`, `configuration file`, `database`, `user`, `session` и т. д.), `sourcefile`/`sourceline` — файл и строка, `pending_restart` — в файле уже другое значение, но нужен перезапуск, `boot_val` — встроенное умолчание, `reset_val` — к чему вернёт `RESET`.

`pg_file_settings` показывает **текущее содержимое файлов**, а не то, что применено [PG]: `applied = false` при пустом `error` означает, что строку переопределила более поздняя; синтаксическая ошибка или неизвестное имя параметра в любом из файлов приводит к тому, что сервер не применяет из файлов ничего, и `applied = false` показывается у **всех** строк. По умолчанию читать представление может только суперпользователь.

Значения колонки `context` [PG]:

| context | Как менять |
|---|---|
| `internal` | нельзя (задаётся при сборке или `initdb`) |
| `postmaster` | только при старте сервера → **restart** |
| `sighup` | в файле + **reload** |
| `superuser-backend`, `backend` | в файле + reload, действует на новые сессии; можно задать при подключении |
| `superuser` | файл + reload либо `SET` суперпользователем (или ролью с правом `SET` на параметр) |
| `user` | файл + reload либо `SET` в любой сессии |

Быстрый просмотр из shell:

```bash
sudo -u postgres psql -Atc "SELECT name||' = '||setting||coalesce(unit,'')||'  ['||source||']' FROM pg_settings WHERE source <> 'default' ORDER BY 1"
grep -Ev '^\s*(#|$)' /etc/postgresql/17/main/postgresql.conf /etc/postgresql/17/main/conf.d/*.conf
sudo cat /var/lib/postgresql/17/main/postgresql.auto.conf
```

---

## 3. Официальные рекомендации: сводка и расхождения

### 3.1. [1С] «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2» (ред. 19.06.2025)

Адрес: https://its.1c.ru/db/metod8dev/content/5866/hdoc. Статья рассчитана на PostgreSQL 9.6+ и сервер класса 8–512 ГБ RAM, 4–256 ядер, RAID или SSD; все значения названы приблизительной отправной точкой.

| Группа | Рекомендация [1С] |
|---|---|
| Сервер | отключить HyperThreading и Energy Saving; запретить своппинг разделяемой памяти (пример дан только для FreeBSD) |
| Память | `shared_buffers = RAM/4`; `temp_buffers = 32..256MB`; `work_mem = RAM/32..64` или `32MB..256MB`; `maintenance_work_mem = RAM/16..32` или `work_mem * 4` или `256MB..4GB`; `effective_cache_size = RAM - shared_buffers` |
| glibc | при заметной фрагментации памяти — `Environment=MALLOC_MMAP_THRESHOLD_=8192` в unit-файле |
| WAL | `fsync = on`; `synchronous_commit = off`; `checkpoint_completion_target = 0.5..0.9`; `min_wal_size = 512MB..4G`; `max_wal_size = 2 * min_wal_size`; `commit_delay = 1000`, `commit_siblings = 5` — только при нагрузке выше 1000 TPS |
| Фоновая запись | `bgwriter_delay = 20ms`; `bgwriter_lru_multiplier = 4.0`; `bgwriter_lru_maxpages = 400` |
| Autovacuum | `autovacuum = on` (не выключать); `autovacuum_max_workers = CPU cores/4..2`, но не меньше 4; `autovacuum_naptime = 20s` |
| Ядро | `max_files_per_process = 8000` |
| Планировщик | `random_page_cost = 1.5–2.0` (RAID) / `1.1–1.3` (SSD); `from_collapse_limit = 20`; `join_collapse_limit = 20`; `geqo = on`; `geqo_threshold = 12` |
| Ввод-вывод | `effective_io_concurrency = 2` (одиночный диск — 1, RAID — 2 и больше) |
| Платформа 1С | `standard_conforming_strings = off`; `escape_string_warning = off`; `max_locks_per_transaction = 512…2000`; `max_connections = 500..8000` (ориентир: от «число сеансов кластера 1С / 8» до «число сеансов / 4»); `jit = off` |
| Сеансы и соединения | `row_security = off`; `ssl = off`; `temp_tablespaces` — на отдельные быстрые диски; каталог `pg_stat_tmp` — в tmpfs |
| Временные таблицы | `enable_temp_memory_catalog` (сборки с 16.4, по умолчанию `off`) — включать только при перегруженных дисках и свободных CPU |
| online_analyze | `online_analyze.enable = off` (в общем случае не рекомендуется); если включать — `table_type = 'temporary'`, `verbose = 'off'`, `threshold = 50`, `scale_factor = 0.1`, `local_tracking = on`, `min_interval = 10000` |

Чего в статье **нет**: `huge_pages`, `shared_preload_libraries`, `plantuner`, `checkpoint_timeout`, `wal_buffers`, параметров параллельных запросов, `enable_*`, `cpu_*`, `default_statistics_target`, порогов autovacuum, таймаутов, настроек Linux (sysctl, THP). Часть «отсутствующего» (`enable_mergejoin`, `cpu_operator_cost`, `lock_timeout`) платформа задаёт сама на уровне сеанса — см. раздел 3.5.

Замечания к самой статье (по конспекту): значение `max_files_per_process = 8000` названо в ней «умолчанием», хотя умолчание PostgreSQL — 1000 [PG] (к какой сборке относится 8000, не сказано); совет про `effective_io_concurrency = 2` и каталог `pg_stat_tmp` отражает PostgreSQL до 14-й версии; `checkpoint_segments` относится только к версиям до 9.5 и в современных версиях отсутствует (строка с ним не даст серверу стартовать).

Отдельная статья [1С] (25.09.2025, https://its.1c.ru/db/metod8dev/content/6035/hdoc) описывает параметр `enable_temp_rd_buffers` сборок `17.5-11.1C` и `16.9-34.1C` — см. раздел 4.12.

### 3.2. [PGPro] Приложение K документации Postgres Pro Standard 17 и 18

Адрес: https://postgrespro.ru/docs/postgrespro/17/config-one-c (для 18 — тот же путь с `18`). Текст для версий 17 и 18 совпадает; набор параметров почти тот же, что у [1С]. Отличия и дополнения:

| Параметр | [PGPro] | Отличие от [1С] |
|---|---|---|
| `max_connections` | `500..10000`, не менее 500 | [1С]: 500..8000 |
| `max_locks_per_transaction` | `256` | [1С]: 512…2000 |
| `max_files_per_process` | `10000` | [1С]: 8000 |
| `effective_io_concurrency` | пример `2`; для HDD — по числу дисков в RAID 0/1, для SSD — «несколько сотен». Текст и для 18-й версии утверждает, что параметр влияет только на сканирование по битовой карте, — для PostgreSQL/Postgres Pro 18 это уже не так (раздел 4.6) | [1С]: 2 |
| `max_parallel_workers_per_gather` | `0` (параллельные запросы отключить) | у [1С] нет |
| `checkpoint_timeout` | `15min` | у [1С] нет |
| `commit_delay` | `1000`, если средний TPS больше 1000 | совпадает |
| `enable_sorted_merge_join` | `off` — параметр **только Postgres Pro** (умолчание `on`): отключает соединения слиянием в планах с сортировкой. Обоснование [PGPro]: решения 1С с соединениями слиянием не работают, планировщик зря тратит время на их рассмотрение — отключение сокращает время планирования | в «Части 2» нет; но платформа сама ставит в сеансе `enable_mergejoin = off` [1С-6011] |
| `MALLOC_MMAP_THRESHOLD_` | `8192`, переменная окружения в unit-файле systemd (в тексте — `/etc/systemd/system/postgresql.service`) при существенной фрагментации памяти | совпадает |
| `plantuner` | добавить в `shared_preload_libraries`, `plantuner.fix_empty_table = on` | у [1С] нет |
| `online_analyze` | для современных версий 1С использовать не рекомендуется; при необходимости — `shared_preload_libraries = 'online_analyze'`, `enable = on`, `threshold = 50`, `scale_factor = 0.1`, `verbose = off`, `table_type = 'temporary'`, `min_interval = 10000` | совпадает по смыслу |
| Сервер | отключить гиперпоточность и энергосбережение; отключить подкачку для разделяемой памяти | совпадает |
| Локаль | `ru_RU.UTF-8` должна быть активна у пользователя, создающего кластер | — |
| Прочие модули | `fasttrun`, `fulleq`, `mchar` — встроены; `dbcopies_decoding` (для копий БД нужен `wal_level = logical`); `auto_dump`; `pg_hint_plan` с `pg_hint_plan.hints_anywhere = on` — **только Postgres Pro Standard/Enterprise** (K.4.6); в бесплатной «PostgreSQL для 1С» 16.14 модуля нет (нет в приложении F и в индексе пакетов; уточнено 19.10.2026) | — |

### 3.3. [PGPro] pgpro_tune и пресет 1c.tune

В Postgres Pro `initdb` по умолчанию запускает утилиту `pgpro_tune`, которая считывает объём памяти и число CPU (переменные `MEMMB`, `NCPU`) и дописывает параметры в `postgresql.conf`. Пресеты: `default.tune` (применяется всегда, если не указан `--no-default`), `1c.tune` (параметры для 1С, часть требует `plantuner`), `extensions.tune`, `regress.tune`.

```bash
# Postgres Pro: создать кластер (локаль должна быть ru_RU.UTF-8; pg-setup берёт её из LANG, переменные LC_* игнорирует)
sudo dpkg-reconfigure locales                 # включить ru_RU.UTF-8 (и en_US.UTF-8 — см. раздел 3.5)
export LANG="ru_RU.UTF-8"
sudo /opt/pgpro/1c-17/bin/pg-setup initdb     # документированная форма: pg-setup initdb [параметры_initdb]
# initdb при этом сам запускает pgpro_tune с пресетом default.tune (подбирает значения под редакцию и версию сервера)

# Посмотреть доступные пресеты и применить пресет 1С к существующему кластеру
/opt/pgpro/1c-17/bin/pgpro_tune --show
sudo -u postgres /opt/pgpro/1c-17/bin/pgpro_tune -D /var/lib/pgpro/1c-17/data -P 1c.tune   # в документации пресет называется 1c.tune; имя брать из вывода --show
sudo systemctl restart postgrespro-1c-17

# Отключить автонастройку при initdb
initdb --no-tune …            # или переменная окружения PGPRO_TUNE=disable
```

Что подтверждено документацией [PGPro] (проверено 10.10.2026 по страницам `app-pgpro-tune`, `app-initdb`, `binary-installation-on-linux` для версий 15, 17 и 18):

- Синтаксис: `pgpro_tune [параметр...] [-D | --pgdata] каталог имя_пресета`. Опции: `-P имя` / `--preset=имя` (можно несколько — выполняются по очереди), `-O параметры` / `--options=параметры` (параметры для пресета), `--default-options=параметры`, `--preset-dir=каталог` (по умолчанию пресеты лежат в каталоге `share` установки), `--config-file=файл`, `--no-default` (не применять `default.tune`), `--set имя=значение` (переменная окружения для пресетов), `--show`, `-V`, `-?`. Имя пресета задаётся **либо** через `-P`, **либо** последним аргументом; оба способа сразу — ошибка.
- Пресет — исполняемый файл (обычно shell-скрипт), который печатает строки для `postgresql.conf`; ему доступны переменные `MEMMB`, `NCPU`, `EDITION`, `MVER`, флаги сборки `USE_LZ4`, `USE_ICU`, `USE_LLVM` и т. п. Результат записывается отдельным блоком в `postgresql.conf` (или в файл, заданный `--config-file`).
- Во всех примерах документации имена пресетов пишутся с расширением: `default.tune`, `1c.tune`, `extensions.tune`, `regress.tune`, собственный — полным путём (`-P/path/to/test.tune`). Можно ли опускать `.tune` (`-P 1c`) — в документации не сказано.
- `initdb`: `--no-tune` отключает утилиту, `--tune=параметры` «устанавливает параметры для pgpro_tune»; переменная `PGPRO_TUNE=disable` равносильна `--no-tune`, любое другое её значение равносильно `--tune=значение`. `pg-setup initdb` принимает обычные параметры `initdb`; про аргумент `tune` сказано только, что он «выбирает вариант конфигурации базы данных», допустимые значения не перечислены.
- Уточнено 11.10.2026: документация самой сборки «для 1С» (`https://repo.postgrespro.ru/doc/pg1c/16/ru/html/` и `/18/`, страницы `app-initdb`, `app-pgpro-tune`) описывает `pgpro_tune` и пресет `1c.tune`, но примера с `--tune=1c` тоже не содержит. Не подтверждена форма `pg-setup initdb --tune=1c`, которая кочует по инструкциям сообщества для сборок `postgrespro-1c-NN`. Ни в одной из проверенных версий документации (15, 17, 18 Postgres Pro Standard; 16 и 18 сборки «для 1С») такого примера нет. Если нужна — сначала проверьте на стенде; надёжный документированный путь — `pg-setup initdb`, затем `pgpro_tune … -P 1c.tune` и перезапуск.
- Для продукта «Postgres Pro для 1С» (`postgrespro-1c-NN`, репозиторий `repo.postgrespro.ru/1c/1c-14 … 1c-18`) страница загрузки сообщает, что конфигурация выставляется автоматически под машину; документация говорит, что конфигурация по умолчанию подбирается под устанавливаемый продукт. Есть ли в бесплатной сборке сама утилита `pgpro_tune` и что именно применяется по умолчанию — проверьте: `ls /opt/pgpro/1c-17/bin/ | grep -i tune`, затем сравните `pg_settings` с разделом 3.2.
- Точного перечня параметров, которые ставит `1c.tune`, в документации нет (сказано лишь: «параметры, специфичные для 1С», часть требует модуля `plantuner`, подробности — в приложении K). Содержимое можно прочитать прямо в файле пресета (`find /opt/pgpro -name '1c.tune'`) либо сравнить `pg_settings` до и после.

Для сборки «PostgreSQL с патчем 1С» в Debian-раскладке аналога `pgpro_tune` нет: настройки вносятся вручную.

### 3.4. Чем официальные рекомендации отличаются от документации PostgreSQL и практики сообщества

| Вопрос | [1С] / [PGPro] | [PG] и общая практика PostgreSQL | Практика сообщества 1С |
|---|---|---|---|
| `shared_buffers` | RAM/4 | 25 % RAM как старт, больше 40 % обычно бессмысленно | то же; на общей с 1С машине — от «своей» доли памяти |
| `work_mem` | RAM/32..64 или 32–256MB | 4MB по умолчанию; считать от числа активных сеансов | 32–128MB; официальная формула на малых ВМ даёт слишком много |
| `synchronous_commit` | `off` | `on` по умолчанию; `off` допустим, если потеря последних транзакций приемлема | почти всегда `off`; `on` — там, где нельзя терять проведённые документы |
| `join_collapse_limit`/`geqo_threshold` | 20 / 12 | значения ≥ `geqo_threshold` включают GEQO и дают «неоптимальные планы» | часто так же; иногда поднимают `geqo_threshold` до 16–20 (⚠ не подтверждено: статьи сообщества при рецензии не читались — поиск был недоступен) |
| Соединение слиянием | платформа сама выполняет `SET enable_mergejoin = off` в каждом сеансе [1С-6011]; [PGPro] дополнительно: `enable_sorted_merge_join = off` | не отключать методы глобально | `enable_mergejoin = off` в `postgresql.conf` встречается, но для сеансов 1С избыточен и зря действует на все остальные сеансы (psql, отчётные инструменты) |
| Параллельные запросы | [PGPro]: `max_parallel_workers_per_gather = 0` | 2 по умолчанию | 0; иногда 2–4 под тяжёлые отчёты |
| `online_analyze` | не рекомендуется, по умолчанию выключен | — (не входит в PostgreSQL) | по старым инструкциям включают вместе с `plantuner` |
| `effective_io_concurrency` | 2 (старый текст); [PGPro] — сотни для SSD | 16 по умолчанию в 18-й версии | 100–200 для SSD |
| `huge_pages` | не упоминается | рекомендуется для больших `shared_buffers`; `try` по умолчанию | включают от 8–16 ГБ `shared_buffers` |
| Гиперпоточность | отключить | — | спорно: часто оставляют включённой, проверяя тестом |
| Каталог `pg_stat_tmp` в tmpfs | рекомендуется | с PostgreSQL 15 статистика в разделяемой памяти, `stats_temp_directory` удалён | для 15+ неактуально |
| `jit` | `off` | `on` по умолчанию до 18; **`off` по умолчанию с 19** | `off` |

Колонка «Практика сообщества 1С» изложена по общеизвестной практике: статьи Infostart, Habr и Mista ни при подготовке, ни при рецензии прочитать не удалось (поиск был недоступен). ⚠ Конкретные числа из этой колонки (`geqo_threshold` 16–20, параллелизм 2–4 под отчёты, порог включения huge pages, отношение к гиперпоточности) ссылками не подтверждены — воспринимайте их как гипотезы для проверки на стенде, а не как рекомендации.

### 3.5. Параметры сеанса, которые платформа 1С задаёт сама [1С-6011]

По статье ИТС «Методика расследования проблем производительности на уровне работы СУБД PostgreSQL» (21.02.2023) платформа «1С:Предприятие» при соединении с PostgreSQL устанавливает собственные параметры сеанса. Чтобы получить в `psql` тот же план, что и у платформы, статья предписывает выполнить перед запросом:

```sql
/* Параметры соединения платформы */
SET client_min_messages = error;
SET lc_messages TO 'en_US.UTF-8';
SET enable_mergejoin = off;
SET escape_string_warning = off;
SET cpu_operator_cost = 0.001;
SET client_encoding = 'utf8';
SET lock_timeout = 20000;
```

Что из этого следует для настройки сервера:

| Параметр сеанса платформы | Следствие |
|---|---|
| `enable_mergejoin = off` | Соединение слиянием в запросах 1С отключено самой платформой. Вносить `enable_mergejoin = off` в `postgresql.conf` не требуется; рекомендация [PGPro] `enable_sorted_merge_join = off` лишь экономит время планирования. Строка `Settings: enable_mergejoin = 'off', cpu_operator_cost = '0.001'` в планах из статей ИТС про `auto_dump` — это именно сеансовые установки платформы, а не настройка стенда |
| `cpu_operator_cost = 0.001` | Умолчание PostgreSQL — 0.0025; платформа снижает стоимость вычисления операторов в своих сеансах. В конфигурации сервера менять не нужно |
| `lock_timeout = 20000` | 20 с — ожидание блокировки на уровне СУБД в сеансах 1С. Глобальный `lock_timeout` на сеансы 1С не влияет (раздел 4.11) |
| `escape_string_warning = off` | Дублирует «обязательную» строку конфигурации. В PostgreSQL 19 параметр удалён, поэтому такая команда `SET` завершится ошибкой `unrecognized configuration parameter` — см. раздел 4.10 |
| `lc_messages = 'en_US.UTF-8'` | Сообщения об ошибках в сеансах 1С — английские независимо от `lc_messages` сервера. PostgreSQL проверяет, что названная локаль существует в ОС; если `en_US.UTF-8` не сгенерирована, команда завершается ошибкой `invalid value for parameter "lc_messages"`. Поэтому на сервере СУБД держите обе локали: `ru_RU.UTF-8` и `en_US.UTF-8` (команды — под таблицей). ⚠ Требование про `en_US.UTF-8` — вывод из механики PostgreSQL и практика сообщества; в статьях ИТС оно прямо не сформулировано |
| `client_min_messages = error` | Предупреждения и замечания клиенту (платформе) не передаются |
| `client_encoding = 'utf8'` | Кодировка обмена с клиентом — UTF-8 независимо от настроек сервера |

Проверить и добавить локали на сервере СУБД:

```bash
locale -a | grep -Ei 'en_US|ru_RU'                 # должны быть en_US.utf8 и ru_RU.utf8
sudo locale-gen en_US.UTF-8 ru_RU.UTF-8            # сгенерировать недостающие
sudo systemctl restart postgresql@17-main          # чтобы процессы сервера увидели новую локаль (в окно обслуживания)
```

Оговорки: список взят из примера статьи 2023 года (по конспекту базы знаний); набор и значения могут зависеть от версии платформы. Фактический набор на своём сервере видно так: на время включить `log_statement = 'all'` для роли 1С на тестовой базе и посмотреть первые команды нового соединения либо снять план через `auto_explain`/`EXPLAIN (SETTINGS)` — строка `Settings:` перечисляет параметры планировщика, отличающиеся от умолчаний.

В том же примере статьи в цепочке запросов платформы после заполнения временной таблицы идёт явная команда `ANALYZE pg_temp.tt7;` — платформа сама собирает статистику по временным таблицам (по-видимому, именно поэтому официальные источники больше не считают `online_analyze` обязательным; раздел 4.14).

---

## 4. Параметры по группам

В таблицах: «Умолч.» — умолчание PostgreSQL 18 [PG]; «Применение» — `restart` (context `postmaster`), `reload` (`sighup`), `сессия` (`user`/`superuser` — достаточно reload, действует на новые команды).

### 4.1. Соединения

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `listen_addresses` | `localhost` | `localhost`, если 1С на том же хосте; IP интерфейса или `*`, если на другом | restart |
| `port` | `5432` | 5432 | restart |
| `max_connections` | 100 | ≥ 500 [PGPro]; 500..8000 [1С] | restart |
| `superuser_reserved_connections` | 3 | 3–5 | restart |
| `tcp_keepalives_idle` / `_interval` / `_count` | 0 (значения ОС) | см. ниже | сессия |
| `client_connection_check_interval` | 0 (выкл.) | 0 или 10–30 с | сессия |

**`max_connections`.** Сервер 1С держит пул соединений в каждом рабочем процессе `rphost`; число соединений примерно соответствует числу одновременно выполняющихся серверных вызовов и фоновых заданий, а не числу пользователей. Отсюда ориентир [1С]: от «сеансы / 8» до «сеансы / 4», но не меньше 500. Сам параметр память почти не расходует (растут таблица блокировок и служебные структуры в разделяемой памяти), её расходуют реально работающие сеансы. Занижать нельзя: при исчерпании пользователи 1С получат `FATAL: sorry, too many clients already`. На малых ВМ (до 20–30 пользователей) допустимо 200–300 [практика]. После изменения пересчитайте huge pages.

Контроль:

```sql
SELECT count(*) AS total,
       count(*) FILTER (WHERE state = 'active') AS active,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx,
       current_setting('max_connections') AS max_conn
FROM pg_stat_activity WHERE backend_type = 'client backend';
```

**`tcp_keepalives_*`.** При нуле действуют значения ядра Linux (`net.ipv4.tcp_keepalive_time = 7200`, `tcp_keepalive_intvl = 75`, `tcp_keepalive_probes = 9`), то есть «мёртвое» соединение обнаруживается через 2 часа с лишним. Если сервер 1С и СУБД на разных хостах и между ними есть межсетевой экран или NAT, обрывающий простаивающие соединения, задайте [практика]: `tcp_keepalives_idle = 60`, `tcp_keepalives_interval = 10`, `tcp_keepalives_count = 6`. На одном хосте (через `127.0.0.1`) менять не нужно.

### 4.2. Память

| Параметр | Умолч. | Формула для 1С | Применение |
|---|---|---|---|
| `shared_buffers` | 128MB | RAM/4 [1С][PGPro] | restart |
| `huge_pages` | `try` | `try`; `on` при `shared_buffers` ≥ 8 ГБ и на Ubuntu 26.04 | restart |
| `effective_cache_size` | 4GB | RAM − `shared_buffers` [1С][PGPro] | сессия |
| `work_mem` | 4MB | RAM/32..64 или 32–256MB [1С][PGPro] | сессия |
| `hash_mem_multiplier` | 2.0 | 2.0 | сессия |
| `maintenance_work_mem` | 64MB | RAM/16..32, или `work_mem × 4`, или 256MB–4GB | сессия |
| `autovacuum_work_mem` | −1 (= `maintenance_work_mem`) | 256MB–2GB [практика] | reload |
| `temp_buffers` | 8MB | 32–256MB [1С][PGPro] | сессия (до первого обращения к временным таблицам) |
| `max_stack_depth` | 2MB | 2MB; до 6–7MB при ошибке `stack depth limit exceeded` | сессия (superuser) |

Здесь и далее **RAM** — память, доступная PostgreSQL [1С]. Если сервер 1С работает на той же ВМ, из общего объёма вычитают его долю. Практический ориентир для совмещённого хоста: PostgreSQL — около половины памяти, остальное — процессам `rphost`/`rmngr`/`ragent` и ОС [практика].

**`shared_buffers`** — общий кэш страниц в разделяемой памяти. [PG]: разумный старт — 25 % памяти на выделенном сервере, более 40 % обычно не даёт выигрыша, а большое значение требует увеличить `max_wal_size`. Двойное кэширование (свой кэш + страничный кэш ОС) — причина, по которой не отдают всё. Риски: слишком большой кэш без huge pages раздувает таблицы страниц каждого серверного процесса; на совмещённом хосте — отнимает память у 1С.

**`effective_cache_size`** — не выделяет память, это подсказка планировщику, сколько данных реально лежит в кэшах (свой + ОС). Занижение склоняет к последовательным сканам, завышение — к индексным. На совмещённом хосте считайте от «своей» половины.

**`work_mem`** — лимит памяти на **одну операцию** сортировки или хеширования в одном запросе; операций в запросе может быть несколько, а хеш-операциям разрешено `work_mem × hash_mem_multiplier`. [1С] прямо оговаривает: это не жёсткий лимит и теоретический максимум — `max_connections × work_mem` (на практике достигается редко). Запросы 1С с десятками соединений и временных таблиц чувствительны к этому параметру: при нехватке сортировки и хеши уходят во временные файлы. Грубая проверка на безопасность [практика]:

```
активные_сеансы × work_mem × 2 (hash_mem_multiplier) × 2..3 (узла плана)  ≤  RAM_pg − shared_buffers − запас
```

Пример: 16 ГБ под PostgreSQL, `shared_buffers = 4GB`, 40 одновременно активных запросов, `work_mem = 64MB` → 40 × 64 × 2 × 2 ≈ 10 ГБ — на грани; 128MB уже опасно. Нужен ли больший `work_mem`, показывают временные файлы [1С]:

```sql
SELECT datname, temp_files, pg_size_pretty(temp_bytes) AS temp_size
FROM pg_stat_database WHERE datname IS NOT NULL ORDER BY temp_bytes DESC;
```

Точечно поднять значение для тяжёлой базы можно через `ALTER DATABASE … SET work_mem`, не увеличивая его для всех.

**`maintenance_work_mem`** — память для `VACUUM`, `CREATE INDEX`, `ALTER TABLE ADD FOREIGN KEY`. Это важно для 1С: реструктуризация при обновлении конфигурации пересоздаёт таблицы и индексы. С PostgreSQL 17 `VACUUM` больше не ограничен молча одним гигабайтом [PG]. Автоочистка может занять до `autovacuum_max_workers × maintenance_work_mem`, поэтому для неё задайте отдельный `autovacuum_work_mem`.

**`temp_buffers`** — буферы **каждой сессии** для временных таблиц. 1С использует временные таблицы очень интенсивно, поэтому умолчание 8MB мало. Память выделяется по мере надобности (около 64 байт на буфер заранее, 8 КБ при использовании [PG]), но **не возвращается до конца сессии**, а соединения 1С долгоживущие. [1С]: чем больше соединений и меньше памяти, тем меньше значение; стремиться к большим значениям не следует. Проверка: `реальные_соединения × temp_buffers` не должно превышать 15–25 % памяти PostgreSQL [практика]. Значение можно сменить в сессии только до первого обращения к временным таблицам.

**Фрагментация памяти glibc.** Если у долгоживущих серверных процессов растёт RSS при невысокой реальной нагрузке, [1С] и [PGPro] рекомендуют переменную окружения `MALLOC_MMAP_THRESHOLD_=8192`: выделения от 8 КБ идут через `mmap` и возвращаются ОС при освобождении.

```bash
sudo systemctl edit postgresql@17-main
```

```ini
[Service]
Environment=MALLOC_MMAP_THRESHOLD_=8192
```

```bash
sudo systemctl restart postgresql@17-main
sudo cat /proc/$(sudo head -1 /var/lib/postgresql/17/main/postmaster.pid)/environ | tr '\0' '\n' | grep MALLOC
```

В Debian-раскладке то же можно задать в `/etc/postgresql/17/main/environment` строкой `MALLOC_MMAP_THRESHOLD_ = 8192`. Включать только при подтверждённой проблеме: больше системных вызовов `mmap`/`munmap` — небольшая плата по CPU.

### 4.3. Блокировки и файлы

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `max_locks_per_transaction` | 64 (в 19-й версии — 128) | 256 [PGPro]; 512…2000 [1С] | restart |
| `max_files_per_process` | 1000 | 8000 [1С]; 10000 [PGPro] | restart |
| `deadlock_timeout` | 1s | 1s | сессия (superuser) |
| `max_prepared_transactions` | 0 | 0 | restart |

**`max_locks_per_transaction`.** Общая таблица блокировок рассчитана на `max_locks_per_transaction × (число серверных процессов + max_prepared_transactions)` объектов. Серверные процессы — это `max_connections` + процессы автоочистки (14–17: `autovacuum_max_workers` + 1 или + 2; 18: `autovacuum_worker_slots` + 2) + `max_worker_processes` + `max_wal_senders` (уточнено 19.10.2026 по документации 16–18 и коду `postinit.c`; формула только с `max_connections` устарела); это ограничение на **среднее**, отдельная транзакция может занять больше, пока есть место в таблице [PG]. Считаются объекты (таблицы, индексы), а не строки. 1С за одну транзакцию трогает сотни таблиц и создаёт множество временных таблиц; [PGPro] отдельно объясняет своё значение 256: 1С использует много временных таблиц, при закрытии соединения сервер пытается удалить их все **одной транзакцией**; если блокировок не хватит, транзакция прервётся и останутся «потерянные» временные таблицы. Симптом нехватки — `ERROR: out of shared memory` с подсказкой `You might need to increase max_locks_per_transaction`. Для больших конфигураций (ERP, много таблиц) [1С] советует значения ближе к 2000. Память: порядка сотен байт на слот, то есть десятки–сотни мегабайт разделяемой памяти при больших значениях; после изменения пересчитайте huge pages. В PostgreSQL 19 умолчание 128, причём размер слота изменён так, что для прежней ёмкости значение нужно **удвоить** [PG].

**`max_files_per_process`.** Каждая таблица и индекс — минимум один файл; в базе 1С десятки тысяч объектов. Когда процесс упирается в лимит, PostgreSQL начинает закрывать и открывать файлы заново, что стоит времени [1С]. Диагностика — `lsof -p <pid> | wc -l`. Значение должно обеспечиваться лимитом ОС: у службы systemd мягкий `LimitNOFILE` по умолчанию 1024, жёсткий 524288. Серверный процесс при старте сам проверяет, сколько дескрипторов ему реально доступно, и ограничивает себя этим числом, поэтому при `max_files_per_process = 8000` нужен `LimitNOFILE` не меньше этого значения (раздел 7.6). В PostgreSQL 18 лимит считает только файлы самого процесса (открытые главным процессом не учитываются) [PG].

**`deadlock_timeout`** — сколько ждать блокировку перед проверкой на взаимоблокировку; тот же порог использует `log_lock_waits`. Умолчание 1 с подходит. Увеличивать имеет смысл только если проверки заметно нагружают сервер; уменьшать — для отладки ожиданий.

### 4.4. WAL и надёжность

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `wal_level` | `replica` | `replica`; `logical` — только для механизма копий БД (`dbcopies_decoding`) | restart |
| `fsync` | `on` | **`on`** | reload |
| `synchronous_commit` | `on` | `off` [1С][PGPro] | сессия |
| `full_page_writes` | `on` | `on` | reload |
| `wal_sync_method` | `fdatasync` (Linux) | не менять; сравнить методы — `pg_test_fsync` | reload |
| `wal_buffers` | −1 (1/32 `shared_buffers`, максимум 16MB) | −1 | restart |
| `wal_compression` | `off` | `lz4` (15+, если сборка поддерживает) [практика] | сессия (superuser) |
| `wal_writer_delay` | 200ms | 200ms | reload |
| `commit_delay` / `commit_siblings` | 0 / 5 | 0; `1000` / `5` только при > 1000 TPS и `synchronous_commit = on` | сессия (`commit_delay` — только superuser) |

**`fsync`.** Выключение грозит неустранимым повреждением базы при сбое питания или ОС [PG]. Старые статьи ИТС (2007–2015) допускали `fsync = off` при RAID-контроллере с батареей и ИБП; актуальная редакция 2025 года однозначна: `fsync = on` [1С]. Если у RAID-контроллера кэш в режиме write-back — проверить наличие и исправность батареи. В ВМ на Windows-хосте то же относится к кэшу записи хоста и виртуального диска: «ускорение» за счёт игнорирования сброса на диск равносильно `fsync = off`.

**`synchronous_commit = off` — допустимо ли для 1С.** Да, это официальная рекомендация [1С][PGPro]. Механика [PG]: клиенту сообщают об успешной фиксации, не дожидаясь сброса WAL на диск; запись делает процесс WAL writer. При падении сервера или ОС теряются транзакции, подтверждённые за последние до `3 × wal_writer_delay` (по умолчанию до 0,6 с; [1С] называет 0,5–1 с). База остаётся целостной — потерянные транзакции выглядят как отменённые. Это принципиально отличается от `fsync = off`, где возможна порча данных. Что это значит для учёта: документ, проведённый за полсекунды до аварийного отключения питания, может оказаться непроведённым, хотя пользователь видел успех. Где это неприемлемо (кассы, обмен с внешними системами, где «подтверждённое» уже ушло наружу), оставляют `on` и компенсируют быстрым диском с защищённым кэшем записи. Параметр меняется без перезапуска и может задаваться на уровне базы: `ALTER DATABASE kassa SET synchronous_commit = on;`.

**`full_page_writes`** — после каждой контрольной точки первая модификация страницы пишет в WAL страницу целиком; это защита от частично записанных страниц. Отключение ускоряет запись, но при сбое может незаметно повредить базу [PG][1С]. Не отключать.

**`wal_compression`** сжимает полные образы страниц в WAL: меньше объём журнала и записи на диск ценой CPU. Значения: `off`, `pglz` (`on` — исторический синоним), `lz4` и `zstd` — если сборка собрана с соответствующими библиотеками (PostgreSQL 15+) [PG]. В 19-й версии `on` означает «лучший доступный метод» [PG]. Проверить, что поддерживает сборка:

```sql
SELECT enumvals FROM pg_settings WHERE name = 'wal_compression';
```

**`commit_delay` / `commit_siblings`** — пауза перед сбросом WAL, чтобы объединить фиксации нескольких транзакций. Срабатывает, только если активно не менее `commit_siblings` транзакций; игнорируется при `fsync = off` [PG]. Стартовое значение по [PG] — половина времени одного сброса 8 КБ по `pg_test_fsync`. Важно: [PG] (глава «Asynchronous Commit») прямо говорит, что `commit_delay` — метод **синхронной** фиксации и при асинхронной фиксации игнорируется («commit_delay is ignored during an asynchronous commit»). То есть при рекомендованном для 1С `synchronous_commit = off` пара `commit_delay`/`commit_siblings` ничего не даёт; оба официальных источника для 1С тем не менее приводят её рядом с `synchronous_commit = off`, оговаривая порог 1000 TPS. Практический вывод: задавать `commit_delay` имеет смысл только там, где оставлен `synchronous_commit = on` и нагрузка действительно выше 1000 TPS. Для справки [PG]: некоторые служебные команды (например, `DROP TABLE`) и двухфазная фиксация фиксируются синхронно при любом значении `synchronous_commit`.

**Вынос WAL на отдельный диск** даёт 10–12 % на нагруженных OLTP-системах [1С, статья 2012 г.]. В Linux каталог `pg_wal` переносят при остановленном сервере и заменяют символической ссылкой либо задают при создании кластера (`initdb --waldir`, `pg_createcluster … -- --waldir=/путь`). В ВМ с одним виртуальным диском на одном физическом носителе выигрыша нет.

### 4.5. Контрольные точки и фоновая запись

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `checkpoint_timeout` | 5min | 15min [PGPro] | reload |
| `max_wal_size` | 1GB | `2 × min_wal_size` (1–8GB) [1С][PGPro]; на нагруженных базах больше | reload |
| `min_wal_size` | 80MB | 512MB–4GB [1С][PGPro] | reload |
| `checkpoint_completion_target` | 0.9 | 0.9 ([1С]: 0.5..0.9) | reload |
| `checkpoint_warning` | 30s | 30s | reload |
| `bgwriter_delay` | 200ms | 20ms [1С][PGPro] | reload |
| `bgwriter_lru_maxpages` | 100 | 400 [1С][PGPro] | reload |
| `bgwriter_lru_multiplier` | 2.0 | 4.0 [1С][PGPro] | reload |

Контрольная точка начинается по истечении `checkpoint_timeout` либо при приближении объёма WAL к `max_wal_size` — что наступит раньше [PG]. Редкие контрольные точки — меньше записи (в том числе полных образов страниц), но дольше восстановление после сбоя и больше места под WAL. `max_wal_size` — мягкий предел, не гарантия. `checkpoint_completion_target = 0.9` растягивает запись на 90 % интервала; уменьшать не рекомендуется, а ставить выше 0.9 (вплоть до допустимого 1.0) [PG] не советует: контрольная точка перестанет успевать завершаться вовремя.

Критерий правильной настройки [1С][PG]: в журнале нет сообщений `checkpoints are occurring too frequently` и контрольные точки по требованию редки по сравнению с плановыми:

```sql
-- PostgreSQL 17+
SELECT num_timed, num_requested, buffers_written,
       round(write_time/1000) AS write_s, round(sync_time/1000) AS sync_s, stats_reset
FROM pg_stat_checkpointer;
-- PostgreSQL ≤ 16
SELECT checkpoints_timed, checkpoints_req, buffers_checkpoint, buffers_backend, stats_reset
FROM pg_stat_bgwriter;
```

Если `num_requested` (`checkpoints_req`) растёт сопоставимо с `num_timed` — увеличивайте `max_wal_size`.

**Фоновая запись.** Процесс background writer заранее сбрасывает «грязные» буферы, чтобы серверным процессам не приходилось делать это самим. Официальные значения (пауза 20 мс, до 400 страниц за проход, множитель 4.0) делают его заметно активнее умолчаний. Слишком большая пауза перекладывает запись на контрольную точку и серверные процессы; слишком малая — загружает ядро CPU вхолостую [1С]. Контроль: `SELECT buffers_clean, maxwritten_clean, buffers_alloc FROM pg_stat_bgwriter;` — быстрый рост `maxwritten_clean` означает, что процесс упирается в `bgwriter_lru_maxpages`.

### 4.6. Ввод-вывод

| Параметр | Умолч. (18) | Для 1С на SSD | Применение |
|---|---|---|---|
| `effective_io_concurrency` | 16 (в версиях ≤ 17 — 1) | 100–200 [PGPro: «несколько сотен»] | сессия; можно задать на табличное пространство |
| `maintenance_io_concurrency` | 16 (в версиях ≤ 17 — 10) | 16–200 | сессия |
| `io_method` (18+) | `worker` | `worker` | restart |
| `io_workers` (18) | 3 | 3; при ≥ 16 vCPU — vCPU/4 [практика] | reload |
| `io_combine_limit` (17+) | 128kB | не менять | сессия |
| `bgwriter_flush_after` / `checkpoint_flush_after` | 512kB / 256kB (Linux) | не менять | reload |

`effective_io_concurrency` — сколько одновременных операций ввода-вывода сессия пытается инициировать (диапазон 0–1000). Значение `2` из [1С] — наследие эпохи HDD, когда параметр влиял только на bitmap heap scan. В PostgreSQL 18 параметр управляет и дистанцией упреждающего чтения в подсистеме асинхронного ввода-вывода; завышенное значение увеличивает задержки всех запросов [PG]. Для SSD/NVMe и виртуальных дисков на них разумно 100–200.

Асинхронный ввод-вывод PostgreSQL 18 описан в разделе 5.

### 4.7. Планировщик

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `random_page_cost` | 4.0 | 1.1–1.3 (SSD); 1.5–2.0 (RAID из HDD) [1С][PGPro] | сессия |
| `seq_page_cost` | 1.0 | 1.0 | сессия |
| `cpu_tuple_cost` / `cpu_index_tuple_cost` / `cpu_operator_cost` | 0.01 / 0.005 / 0.0025 | умолчания; см. ниже | сессия |
| `default_statistics_target` | 100 | 100 | сессия |
| `from_collapse_limit` | 8 | 20 [1С][PGPro] | сессия |
| `join_collapse_limit` | 8 | 20 [1С][PGPro] | сессия |
| `geqo` / `geqo_threshold` | `on` / 12 | `on` / 12 [1С][PGPro] | сессия |
| `jit` | `on` (с 19-й версии `off`) | `off` [1С][PGPro] | сессия |
| `cursor_tuple_fraction` | 0.1 | 0.1 | сессия |
| `plan_cache_mode` | `auto` | `auto` | сессия |
| `enable_nestloop`, `enable_hashjoin`, `enable_mergejoin` и др. | `on` | см. ниже | сессия |

**`random_page_cost`** — относительная стоимость случайного чтения страницы; завышенное значение толкает планировщик к полным сканам таблиц [1С]. Ниже `seq_page_cost` ставить нельзя; при отдельном табличном пространстве на других дисках значение задают для него: `ALTER TABLESPACE fast SET (random_page_cost = 1.1);`.

**`from_collapse_limit` / `join_collapse_limit` и GEQO.** Первый определяет, до какого числа элементов `FROM` подзапросы «поднимаются» во внешний запрос, второй — до какого числа явные `JOIN` переставляются планировщиком. Запросы 1С (виртуальные таблицы регистров, ограничения доступа RLS, динамические списки) часто соединяют больше 8 таблиц, поэтому умолчание 8 мешает найти хороший порядок соединений. При этом [PG] предупреждает: значения, равные или превышающие `geqo_threshold`, передают такие запросы генетическому оптимизатору (GEQO), который ищет план эвристически и может дать не лучший. Официальная комбинация 20/12 это и означает: запросы с 12 и более элементами `FROM` планирует GEQO — планирование быстрое, план приемлемый. Полный перебор для 15–20 таблиц занял бы больше времени, чем само выполнение. GEQO отключать не рекомендуется [1С].

**`jit = off`.** JIT-компиляция окупается на долгих аналитических запросах; у коротких транзакционных запросов 1С накладные расходы больше выигрыша [1С]. В PostgreSQL 19 JIT выключен по умолчанию: разработчики признали стоимостную модель его включения ненадёжной [PG].

**Параметры `enable_*`.** Это переключатели методов, а не «настройки»: значение `off` не запрещает метод, а делает его очень дорогим.

- `enable_sorted_merge_join = off` — рекомендация [PGPro]; параметр есть **только в Postgres Pro** и отключает соединение слиянием в планах, где для него нужна сортировка.
- `enable_mergejoin = off` — **задаётся самой платформой 1С** командой `SET` в каждом сеансе [1С-6011] (раздел 3.5); он отключает соединение слиянием целиком, а не только с сортировкой. Именно поэтому в статье ИТС про `auto_dump` (июнь 2025, сборка 16.x-1C) строка `Settings:` плана содержит `enable_mergejoin = 'off', cpu_operator_cost = '0.001'`: это сеансовые установки платформы, а не конфигурация сборки и не ручная настройка стенда. Вносить `enable_mergejoin = off` в `postgresql.conf` для сборки с патчем 1С не нужно: на сеансы 1С это ничего не добавит, а остальным сеансам (psql, выгрузки, внешняя аналитика) без причины ухудшит планы. Как официальная рекомендация для конфигурации сервера этот параметр нигде не значится.
- `enable_nestloop = off` глобально ставить нельзя: короткие запросы по индексу — основа работы 1С. Допустимо как временная мера на уровне базы или роли при разборе конкретного плохого плана.
- `enable_hashjoin`, `enable_seqscan`, `enable_indexscan`, `enable_bitmapscan`, `enable_material`, `enable_memoize`, `enable_hashagg`, `enable_sort`, `enable_incremental_sort`, `enable_partitionwise_*` — оставлять по умолчанию.

**`cpu_*`-стоимости.** В рекомендациях по конфигурации сервера ([1С] «Часть 2», [PGPro] приложение K) их нет. При этом `cpu_operator_cost = 0.001` (умолчание 0.0025) платформа 1С задаёт сама в каждом сеансе [1С-6011] — в `postgresql.conf` его дублировать не нужно. `cpu_tuple_cost` и `cpu_index_tuple_cost` оставлять по умолчанию; менять без измерений не нужно. Следствие для диагностики: `EXPLAIN` из `psql` без `SET enable_mergejoin = off; SET cpu_operator_cost = 0.001;` покажет **другой** план, чем получает платформа (раздел 10.6).

**`default_statistics_target`.** Умолчание 100 официальные источники не меняют. Значения 300–1000 улучшают оценки на неравномерных данных, но удорожают `ANALYZE` и планирование каждого запроса; повышать лучше точечно: `ALTER TABLE … ALTER COLUMN … SET STATISTICS 500;`. В Tantor SE 1C есть отдельный параметр `default_statistics_target_temp_tables` для временных таблиц [Tantor].

**`cursor_tuple_fraction`** — доля строк курсора, которую планировщик рассчитывает вернуть; официальных рекомендаций для 1С нет, оставлять 0.1.

### 4.8. Параллельное выполнение

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `max_worker_processes` | 8 | не меньше числа vCPU | restart |
| `max_parallel_workers` | 8 | до числа vCPU | сессия |
| `max_parallel_workers_per_gather` | 2 | **0** [PGPro] | сессия |
| `max_parallel_maintenance_workers` | 2 | 2–4 [практика] | сессия |

Почему параллельные запросы для 1С отключают: типичный тяжёлый запрос 1С наполняет временную таблицу (`INSERT INTO … SELECT`) и читает другие временные таблицы. В ванильном PostgreSQL запрос, изменяющий данные, параллельно не планируется, а чтение временных таблиц выполняет только ведущий процесс (операция «parallel restricted») [PG]. Для множества коротких запросов запуск рабочих процессов — чистые накладные расходы, к тому же каждый рабочий процесс получает собственный `work_mem`. В Postgres Pro есть параметр `enable_parallel_temptables` (по умолчанию `off`), в Tantor SE 1C заявлен параллелизм при работе с временными таблицами [PGPro][Tantor] — на этих СУБД вопрос можно пересмотреть под тяжёлые отчёты, проверив на стенде.

`max_parallel_maintenance_workers` на запросы не влияет: это параллельное построение индексов (`CREATE INDEX` для B-дерева, GIN, BRIN) и параллельный `VACUUM`. При `max_parallel_workers_per_gather = 0` они продолжают работать и ускоряют реструктуризацию и загрузку `dt`. Память `maintenance_work_mem` делится на всю команду, а не выдаётся каждому рабочему процессу [PG].

### 4.9. Autovacuum

| Параметр | Умолч. (18) | Для 1С | Применение |
|---|---|---|---|
| `autovacuum` | `on` | **`on`** [1С][PGPro] | reload |
| `autovacuum_max_workers` | 3 | от vCPU/4 до vCPU/2, не меньше 4 [1С][PGPro] | restart (≤ 17); reload в пределах `autovacuum_worker_slots` (18+) |
| `autovacuum_worker_slots` (18+) | 16 | 16 | restart |
| `autovacuum_naptime` | 1min | 20s [1С][PGPro] | reload |
| `autovacuum_vacuum_threshold` / `_scale_factor` | 50 / 0.2 | 50 / 0.01–0.05 [практика] | reload; можно на таблицу |
| `autovacuum_analyze_threshold` / `_scale_factor` | 50 / 0.1 | 50 / 0.005–0.02 [практика] | reload; можно на таблицу |
| `autovacuum_vacuum_insert_threshold` / `_scale_factor` | 1000 / 0.2 | умолчания | reload |
| `autovacuum_vacuum_max_threshold` (18+) | 100000000 | умолчание | reload |
| `autovacuum_vacuum_cost_delay` | 2ms | 2ms | reload |
| `autovacuum_vacuum_cost_limit` | −1 (= `vacuum_cost_limit` = 200) | 800–2000 на SSD [практика] | reload |
| `autovacuum_work_mem` | −1 | 256MB–2GB [практика] | reload |
| `autovacuum_freeze_max_age` | 200000000 | умолчание | restart |
| `log_autovacuum_min_duration` | 10min | 10s–1min на время настройки | reload |

Как это работает [PG]: раз в `autovacuum_naptime` на каждую базу запускается рабочий процесс; таблица очищается, когда число «мёртвых» строк превышает `threshold + scale_factor × число_строк` (в 18-й версии — не больше `autovacuum_vacuum_max_threshold`), и анализируется по аналогичной формуле для изменённых строк. Очистка тормозит сама себя: набрав `cost_limit` условных единиц, процесс спит `cost_delay`; лимит **делится между всеми работающими процессами**, поэтому, добавляя процессы, поднимайте и лимит — иначе каждый станет медленнее.

Особенности 1С:

- Официально заданы только три параметра (`on`, число процессов, `naptime = 20s`); пороги — область практики сообщества.
- Умолчание `scale_factor = 0.2` для таблицы регистра на 100 млн строк означает очистку после 20 млн мёртвых строк — слишком поздно. Снижайте глобально до 0.01–0.05 либо точечно: `ALTER TABLE _accumrg12345 SET (autovacuum_vacuum_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.005);`.
- 1С непрерывно создаёт и удаляет временные таблицы; каждая такая операция меняет системный каталог (`pg_class`, `pg_attribute`, `pg_type`, `pg_depend`, `pg_statistic`). Каталог распухает, если автоочистка не успевает, — отсюда короткий `naptime` и не менее четырёх процессов. Сами временные таблицы автоочистка не обрабатывает (они видны только своей сессии).
- Выключение автоочистки ведёт к росту базы и деградации; кроме того, очистка для защиты от зацикливания счётчика транзакций запускается даже при `autovacuum = off` [PG].
- Долгие открытые транзакции и сеансы `idle in transaction` не дают удалять мёртвые строки, как бы ни был настроен autovacuum.

```sql
-- где копятся мёртвые строки и когда таблицу чистили
SELECT relname, n_live_tup, n_dead_tup, n_mod_since_analyze, last_autovacuum, last_autoanalyze
FROM pg_stat_all_tables ORDER BY n_dead_tup DESC LIMIT 20;

-- размер системного каталога (распухание из-за временных таблиц)
SELECT c.relname, pg_size_pretty(pg_total_relation_size(c.oid)) AS size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'pg_catalog' AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 10;

-- что автоочистка делает прямо сейчас
SELECT pid, datname, relid::regclass, phase, heap_blks_scanned, heap_blks_total FROM pg_stat_progress_vacuum;
```

### 4.10. Параметры совместимости с 1С, локаль, время

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `standard_conforming_strings` | `on` | **`off`** [1С][PGPro] (PostgreSQL ≤ 18) | сессия |
| `escape_string_warning` | `on` | **`off`** [1С][PGPro] (PostgreSQL ≤ 18) | сессия |
| `row_security` | `on` | `off` [1С][PGPro] | сессия |
| `ssl` | `off` (в Debian-раскладке `pg_createcluster` создаёт кластер с `ssl = on` — см. ниже) | `off` [1С] | reload |
| `lc_messages` | из окружения | `en_US.UTF-8` или `C` [практика]; в сеансах 1С платформа сама ставит `en_US.UTF-8` [1С-6011] | сессия (superuser) |
| `datestyle` | `ISO, MDY`; `initdb` ставит по локали (`iso, dmy` для `ru_RU`) | не менять | сессия |
| `timezone`, `log_timezone` | из системы при `initdb` | часовой пояс сервера | сессия / reload |

**`standard_conforming_strings = off`** разрешает обратную косую черту как символ экранирования в обычных строковых литералах — так формирует запросы платформа 1С. **`escape_string_warning = off`** убирает предупреждения об этом, иначе журнал заполняется сообщениями `nonstandard use of \\ in a string literal`.

**Важно про PostgreSQL 19** [PG, документация и примечания к выпуску 19 Beta 4]: «Beginning in PostgreSQL 19, this parameter is always `on`… it cannot be set to `off`» — параметр `standard_conforming_strings` оставлен только для чтения приложениями; `escape_string_warning` удалён («removed as unnecessary»). Что из этого следует:

- Строка `escape_string_warning = off` в конфигурации — это неизвестный параметр, строка `standard_conforming_strings = off` — недопустимое значение. При **старте** сервера и то и другое считается ошибкой конфигурации, сервер 19-й версии с такими строками не запустится; при reload такие строки игнорируются с записью в журнал. Это следует из общих правил обработки конфигурации [PG] и текста документации; на бета-версии не проверялось — ⚠ не подтверждено опытом.
- Платформа 1С в каждом сеансе сама выполняет `SET escape_string_warning = off` [1С-6011] а официальное требование `standard_conforming_strings = off` означает, что она формирует строковые литералы в расчёте на обратную косую черту как символ экранирования. На сервере 19-й версии такая команда `SET` завершится ошибкой (`unrecognized configuration parameter`), а литералы с обратной косой чертой будут разобраны иначе. Вывод рецензента: **существующие версии платформы с PostgreSQL 19 несовместимы**, потребуются и новая сборка СУБД, и версия платформы, рассчитанная на это изменение (⚠ вывод из двух источников, официального заявления 1С на 10.10.2026 нет).
- Дампы, снятые `pg_dump` старше 19-й версии при `standard_conforming_strings = off`, в сервер 19 корректно не загрузятся [PG] — при будущей миграции снимать дамп утилитами новой версии.
- Сборок с патчем 1С, Postgres Pro и Tantor для 19-й ветки в списке поддерживаемых СУБД на v8.1c.ru на 10.10.2026 нет (PostgreSQL 19 там не упоминается). Не планируйте переход на 19, пока 1С не объявит поддержку.

**`row_security = off`**: запрос, к которому применилась бы политика защиты строк, завершается ошибкой вместо молчаливой фильтрации. Платформа 1С механизм RLS СУБД не использует (её «RLS» реализован в тексте запросов), так что параметр — страховка, а не ускорение.

**`ssl = off`**: шифрование соединения расходует CPU [1С]. Оправдано, когда сервер 1С и СУБД на одном хосте или в доверенном сегменте. Если трафик между ними идёт по общей сети — оставьте `on` и используйте `hostssl` в `pg_hba.conf`. В Debian-раскладке кластер создаётся уже с `ssl = on`: `pg_createcluster` берёт `ssl = on` из `/etc/postgresql-common/createcluster.conf` и, если существует `/etc/ssl/certs/ssl-cert-snakeoil.pem`, а ключ `/etc/ssl/private/ssl-cert-snakeoil.key` читается владельцем кластера, прописывает их в `ssl_cert_file`/`ssl_key_file` (проверено по исходному коду `postgresql-common`; документация Ubuntu Server подтверждает: SSL включён по умолчанию, сертификат — из пакета `ssl-cert`, для продуктива его следует заменить). Проверка: `SHOW ssl; SHOW ssl_cert_file;`. При `ssl = on` клиент на библиотеке libpq с настройкой по умолчанию (`sslmode=prefer`) сам выбирает шифрованное соединение, если сервер его предлагает, — запись `host` в `pg_hba.conf` допускает оба варианта. Шифруются ли фактически соединения сервера 1С, видно так (⚠ поведение клиентской библиотеки платформы по документации не проверено — смотрите по факту):

```sql
SELECT a.usename, a.client_addr, s.ssl, s.version, count(*)
FROM pg_stat_ssl s JOIN pg_stat_activity a USING (pid)
WHERE a.backend_type = 'client backend'
GROUP BY 1, 2, 3, 4;
```

**`lc_messages`**: английские сообщения сервера проще искать в документации и интернете; на данные и сортировку параметр не влияет (сортировку задаёт локаль базы, для 1С — `ru_RU.UTF-8`, выбранная при `initdb`). Значение из конфигурации определяет язык сообщений главного процесса и фоновых процессов; сеансы 1С получают `en_US.UTF-8` от самой платформы (раздел 3.5), поэтому локаль `en_US.UTF-8` на сервере СУБД должна быть сгенерирована.

### 4.11. Таймауты

| Параметр | Умолч. | Для 1С | Примечание |
|---|---|---|---|
| `statement_timeout` | 0 | **0 глобально** | [PG] не рекомендует задавать в `postgresql.conf` |
| `lock_timeout` | 0 | **0 глобально** | то же; ожиданием блокировок управляет платформа |
| `transaction_timeout` (17+) | 0 | 0 глобально | то же |
| `idle_in_transaction_session_timeout` | 0 | 0 либо «страховка» в несколько часов | см. ниже; оговорки «не задавать глобально» в [PG] для него нет — осторожность здесь из практики 1С |
| `idle_session_timeout` | 0 | 0 | 1С держит пул простаивающих соединений |
| `deadlock_timeout` | 1s | 1s | раздел 4.3 |
| `authentication_timeout` | 1min | 1min | — |

- `statement_timeout` в глобальной конфигурации оборвёт долгие регламентные операции 1С (закрытие месяца, реструктуризация, загрузка `dt`, `VACUUM FULL`). Если нужен — только на отдельную роль: `ALTER ROLE report_user SET statement_timeout = '15min';`.
- Время ожидания блокировок данных задаётся в параметрах информационной базы 1С (по умолчанию 20 с) и применяется платформой: в сеансе она выполняет `SET lock_timeout = 20000` [1С-6011]. Сеансовый `SET` сильнее файла конфигурации, поэтому глобальный `lock_timeout` на сеансы 1С не действует — зато он подействует на все остальные сеансы (`psql`, `pg_dump`, скрипты обслуживания с `VACUUM FULL`/`REINDEX`, репликация) и приведёт к их неожиданным отказам. [PG] для `statement_timeout`, `lock_timeout` и `transaction_timeout` прямо пишет, что задавать их в `postgresql.conf` не рекомендуется, так как это затронет все сеансы.
- `idle_in_transaction_session_timeout`: сеанс 1С внутри транзакции часто простаивает «с точки зрения СУБД», пока прикладной код на сервере 1С обрабатывает результаты между запросами; при проведении больших документов и закрытии периода такие паузы длятся минутами. Короткий таймаут будет обрывать рабочие транзакции (в 1С это выглядит как ошибка соединения с СУБД). Допустима только «страховка» от зависших сессий — например, `'4h'` [практика].
- Найти зависшие в транзакции сеансы:

```sql
SELECT pid, usename, datname, client_addr, state, now() - xact_start AS xact_age, left(query, 80) AS last_query
FROM pg_stat_activity
WHERE state LIKE 'idle in transaction%' ORDER BY xact_start;
```

### 4.12. Временные файлы и временные таблицы

| Параметр | Умолч. | Для 1С | Применение |
|---|---|---|---|
| `temp_file_limit` | −1 | −1 либо защитный предел (20–50 % свободного места) [практика] | сессия (superuser) |
| `temp_tablespaces` | пусто | табличное пространство на быстром диске [1С][PGPro] | сессия |
| `log_temp_files` | −1 | порог 50–100 МБ на время настройки | сессия (superuser) |
| `enable_temp_memory_catalog` (сборки 1С с 16.4; Tantor SE 1C) | `off` | `off`; `on` — при перегруженных дисках и свободных CPU [1С] | [1С]: при перезапуске |
| `enable_temp_rd_buffers` (сборки 1С с 17.5-11.1C и 16.9-34.1C) | `off` | по результатам теста | ⚠ в источнике не указано |

**`temp_file_limit`** ограничивает суммарный объём временных файлов одного процесса (сортировки, хеши, материализация); при превышении запрос отменяется. Данные явных временных таблиц в лимит **не входят** [PG]. Полезен как защита от запроса, который способен занять весь диск.

**`temp_tablespaces`** — где создаются временные таблицы, их индексы и временные файлы сортировок. Вынос на отдельный быстрый диск разгружает основной том [1С][PGPro].

```bash
sudo mkdir -p /mnt/pgtemp/ts_temp
sudo chown postgres:postgres /mnt/pgtemp/ts_temp && sudo chmod 700 /mnt/pgtemp/ts_temp
sudo -u postgres psql <<'SQL'
CREATE TABLESPACE ts_temp LOCATION '/mnt/pgtemp/ts_temp';
ALTER TABLESPACE ts_temp SET (random_page_cost = 1.1);
GRANT CREATE ON TABLESPACE ts_temp TO usr1cv8;   -- если роль 1С не суперпользователь
SQL
# conf.d/90-1c.conf:  temp_tablespaces = 'ts_temp'   → reload
```

Подводные камни: табличное пространство, указанное в конфигурации, но недоступное роли или не существующее, **молча пропускается** [PG]; табличное пространство — неотъемлемая часть кластера, поэтому размещать его на tmpfs или RAM-диске нельзя (после перезагрузки каталог исчезнет, а записи о нём в кластере останутся) [PG]; каталог попадает в физические резервные копии (`pg_basebackup`), это надо учитывать при восстановлении.

**Каталог `pg_stat_tmp` в tmpfs** [1С][PGPro] — рекомендация для PostgreSQL до 14-й версии включительно (параметр `stats_temp_directory`). С PostgreSQL 15 накопительная статистика хранится в разделяемой памяти, отдельного процесса-сборщика нет, параметр `stats_temp_directory` удалён [PG]. Для версий 15–18 делать ничего не нужно.

**`enable_temp_memory_catalog`** [1С] (в статье сказано «начиная с PostgreSQL 16.4» без уточнения сборки; в ванильном PostgreSQL такого параметра нет): строки системных каталогов, описывающие временные таблицы, хранятся в памяти серверного процесса, а не в общих таблицах каталога. Это снимает распухание каталога и дисковую нагрузку от него ценой CPU. [1С]: по умолчанию выключено; включать на высоконагруженных системах, где дисковая подсистема перегружена, а процессоры свободны; на быстрых SSD и при прогретом кэше операции с временными таблицами с включённой опцией могут стать **медленнее**. По [1С] изменение применяется при перезапуске PostgreSQL; в Tantor SE 1C одноимённый параметр меняется без перезапуска, а после выключения рекомендуется переподключиться [Tantor].

**`enable_temp_rd_buffers`** [1С, статья от 25.09.2025]: файл временной таблицы не создаётся, пока её данные не превысят 32 КБ; маленькие временные таблицы живут только в памяти. Ожидать роста потребления памяти. Требуется ли перезапуск и когда включать — в статье не сказано; проверять на стенде.

Проверить, есть ли параметры в вашей сборке:

```sql
SELECT name, setting, context, short_desc FROM pg_settings WHERE name LIKE 'enable_temp%';
```

### 4.13. Журналирование: необходимый минимум

| Параметр | Умолч. | Рекомендуемо [практика] | Зачем |
|---|---|---|---|
| `log_line_prefix` | `'%m [%p] '` (в Debian-раскладке `pg_createcluster` сразу ставит `'%m [%p] %q%u@%d '`) | `'%m [%p] %q%u@%d/%a '` | время, PID, пользователь, база, приложение |
| `log_checkpoints` | `on` (с 15-й версии) | `on` | частота и длительность контрольных точек |
| `log_lock_waits` | `off` (с 19-й — `on`) | `on` | ожидания блокировок дольше `deadlock_timeout` |
| `log_temp_files` | −1 | `'100MB'` (или 0 на время разбора) | запросы, которым не хватает `work_mem` |
| `log_autovacuum_min_duration` | 10min | `'30s'` | долгие автоочистки |
| `log_min_duration_statement` | −1 | `'5s'`–`'10s'` | медленные запросы целиком |
| `log_statement` | `none` | `none` или `ddl` | `all`/`mod` при нагрузке 1С раздувают журнал |
| `log_connections` / `log_disconnections` | выкл. | выкл. | у 1С много соединений |
| `log_min_messages` | `warning` | `warning` | — |
| `log_min_error_statement` | `error` | `error` | текст запроса, вызвавшего ошибку |
| `track_io_timing` | `off` | `on` после проверки `pg_test_timing` | время ввода-вывода в `EXPLAIN (ANALYZE, BUFFERS)` и `pg_stat_io` |
| `track_activity_query_size` | 1024 | 4096–16384 (restart) | запросы 1С длинные и обрезаются в `pg_stat_activity` |

Замечания:

- Запросы 1С бывают в десятки килобайт; низкий порог `log_min_duration_statement` быстро забивает диск. Следите за ротацией: в Debian-раскладке журнал `/var/log/postgresql/postgresql-NN-main.log` ротирует `logrotate` (сборщик `logging_collector` выключен).
- `track_io_timing` постоянно запрашивает системные часы; на большинстве современных систем это дёшево, но в ВМ с медленным источником времени — заметно. Проверка: `/usr/lib/postgresql/17/bin/pg_test_timing` [PG].
- Для разбора проблем производительности вместо сплошного журналирования используйте `pg_stat_statements` и `auto_explain` (ниже) и технологический журнал 1С (событие `DBPOSTGRS`).

### 4.14. shared_preload_libraries и параметры расширений

```ini
shared_preload_libraries = 'plantuner, pg_stat_statements'    # restart; список через запятую
```

Если хоть одна библиотека из списка не найдена, **сервер не запустится** [PG]. Проверить наличие файлов до перезапуска:

```bash
ls /usr/lib/postgresql/17/lib/ | grep -E 'plantuner|online_analyze|pg_stat_statements|auto_explain|auto_dump|pg_wait_sampling|fasttrun|mchar|fulleq'
sudo -u postgres psql -c "SHOW shared_preload_libraries;"
```

| Библиотека | Назначение | Как подключается | Статус для 1С |
|---|---|---|---|
| `mchar`, `fulleq`, `fasttrun` | типы и операторы совместимости с MS SQL, быстрое нетранзакционное усечение временных таблиц | расширения в базе; в предзагрузке не нуждаются | обязательны, входят в сборки для 1С |
| `plantuner` | управление видимостью индексов для планировщика; `fix_empty_table` | `shared_preload_libraries` или `LOAD` | рекомендован [PGPro] |
| `online_analyze` | немедленный `ANALYZE` после изменения таблицы | `shared_preload_libraries` или `LOAD` | в общем случае не рекомендуется [1С][PGPro] |
| `pg_stat_statements` | статистика по запросам | `shared_preload_libraries` + `CREATE EXTENSION` | рекомендуется для диагностики [практика] |
| `auto_explain` | планы медленных запросов в журнал | `session_preload_libraries` или `shared_preload_libraries` | по необходимости |
| `auto_dump` | сохранение контекста проблемного запроса (DDL и данные временных таблиц) | `shared_preload_libraries` + `CREATE EXTENSION auto_dump` | диагностика; сборки 1С 16/17 (статья ИТС от 25.06.2025), Postgres Pro, Tantor |
| `pg_wait_sampling` | выборочная статистика ожиданий | `shared_preload_libraries` + `CREATE EXTENSION pg_wait_sampling` | диагностика; там же |
| `pg_hint_plan` | подсказки планировщику | [PGPro]: `pg_hint_plan.hints_anywhere = on` | Postgres Pro Standard/Enterprise (K.4.6); в бесплатной «PostgreSQL для 1С» 16.14 нет |
| `dbcopies_decoding` | модуль 1С для механизма копий баз данных | включён в сборки; нужен `wal_level = logical` | только при использовании копий БД |

**plantuner**

| Параметр | Значение для 1С | Что делает |
|---|---|---|
| `plantuner.fix_empty_table` | `on` [PGPro] | для таблицы, в файле которой нет ни одного блока, считает число страниц и строк нулевым. Без этого планировщик приписывает только что созданной (в том числе временной) таблице условный ненулевой размер и ошибается в оценках |
| `plantuner.disable_index` | — | список индексов, скрытых от планировщика (диагностика: «что будет без этого индекса») |
| `plantuner.enable_index` | — | индексы, видимые даже если перечислены в `disable_index` |
| `plantuner.only_index` | — | разрешить только перечисленные индексы (описан в [Tantor]) |

**online_analyze** (умолчания — по документации модуля [PGPro])

| Параметр | Умолч. модуля | Значение, если включать [1С][PGPro] | Что делает |
|---|---|---|---|
| `online_analyze.enable` | `on` | [1С]: `off` в общем случае; `on` — при необходимости | включает немедленный анализ |
| `online_analyze.table_type` | `all` (в Tantor — `temporary`) | `'temporary'` | какие таблицы: `all`, `persistent`, `temporary`, `none` |
| `online_analyze.verbose` | `on` | `off` | выполнять `ANALYZE VERBOSE` (шум в журнале и у клиента) |
| `online_analyze.threshold` | 50 | 50 | минимум изменённых строк (аналог `autovacuum_analyze_threshold`) |
| `online_analyze.scale_factor` | 0.1 | 0.1 | доля размера таблицы (аналог `autovacuum_analyze_scale_factor`) |
| `online_analyze.min_interval` | 10000 | 10000 | минимальный интервал между анализами одной таблицы, мс |
| `online_analyze.local_tracking` | `off` | `on` [1С] | отслеживать изменения временных таблиц внутри процесса сессии |
| `online_analyze.lower_limit` | 0 | — | минимальное число строк в таблице для срабатывания |
| `online_analyze.capacity_threshold` | 100000 | — | максимум временных таблиц в локальном кэше |
| `online_analyze.exclude_tables` / `include_tables` | пусто | — | списки исключений и включений |

Ключевой момент: библиотека, просто добавленная в `shared_preload_libraries` без параметров, работает с умолчаниями модуля — `enable = on`, все типы таблиц, `VERBOSE`. Это немедленный `ANALYZE` после каждого изменения **любой** таблицы и резкое замедление. Поэтому либо не загружайте модуль вовсе (актуальная официальная позиция), либо задавайте параметры явно:

```ini
# Вариант «по старым инструкциям» [практика]; официально — только при доказанной необходимости
shared_preload_libraries = 'online_analyze, plantuner'
online_analyze.enable = on
online_analyze.table_type = 'temporary'
online_analyze.verbose = off
online_analyze.threshold = 50
online_analyze.scale_factor = 0.1
online_analyze.local_tracking = on
online_analyze.min_interval = 10000
plantuner.fix_empty_table = on
```

Когда включать `online_analyze` [1С][PGPro]: фоновое обновление статистики не справляется, и оптимизатор систематически ошибается в оценке числа строк временных таблиц (видно по планам: оценка `rows=` на порядки расходится с фактом). Почему раньше включали всегда: статистику временных таблиц autovacuum не собирает, и без неё планы запросов 1С были плохими. Современные версии платформы решают это сами: в примере из [1С-6011] (статья 2023 года) в цепочке запросов платформы сразу после `INSERT INTO pg_temp.tt7 …` идёт явная команда `ANALYZE pg_temp.tt7;`. С какой именно версии платформы это появилось, официальные источники не называют; в сообществе обычно называют 8.3.13 (⚠ не подтверждено первоисточником). Проверить на своей системе просто: в технологическом журнале (событие `DBPOSTGRS`) или в журнале PostgreSQL при `log_statement = 'all'` на тестовой базе после заполнения временной таблицы должна быть видна команда `ANALYZE pg_temp.tt…`. Если она есть — `online_analyze` для временных таблиц дублирует работу платформы.

**pg_stat_statements**

```ini
shared_preload_libraries = 'plantuner, pg_stat_statements'
pg_stat_statements.max = 10000        # умолч. 5000; restart
pg_stat_statements.track = top        # умолч. top; all — вместе с вложенными
pg_stat_statements.track_utility = on # умолч. on
pg_stat_statements.track_planning = off  # умолч. off; on заметно нагружает при конкуренции
pg_stat_statements.save = on
```

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;      -- в базе, из которой будете смотреть
SELECT round(total_exec_time::numeric/1000, 1) AS total_s, calls,
       round(mean_exec_time::numeric, 1) AS mean_ms, rows, left(query, 100) AS query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;
SELECT pg_stat_statements_reset();                       -- обнулить перед замером
```

Модуль активен только при вычислении идентификатора запроса: `compute_query_id = auto` (умолчание) достаточно [PG].

**auto_explain** (план медленного запроса в журнал)

```ini
session_preload_libraries = 'auto_explain'   # reload, действует на новые сессии
auto_explain.log_min_duration = '10s'        # умолч. -1 (выключено)
auto_explain.log_analyze = off               # on — фактические строки и время, но с накладными расходами на ВСЕ запросы
auto_explain.log_buffers = off               # требует log_analyze
auto_explain.log_timing = on                 # при log_analyze = on отключение снижает накладные расходы
auto_explain.log_nested_statements = off
auto_explain.log_format = text
```

[PG] предупреждает: при `log_analyze = on` замер времени по узлам выполняется для всех запросов, попадающих или нет в журнал, и может «крайне негативно» сказаться на производительности. В продуктиве — только без `log_analyze` либо кратковременно.

---

## 5. Что изменилось в версиях 15–19 и что есть только в сборках для 1С

### 5.1. PostgreSQL 15–18: параметры, значимые для сервера 1С [PG]

| Версия | Изменение | Что это значит на практике |
|---|---|---|
| 15 | `wal_compression` принимает `lz4` и `zstd` | сжатие полных образов страниц в WAL почти без затрат CPU (`lz4`) |
| 15 | `recovery_prefetch` (умолч. `try`), `wal_decode_buffer_size` | быстрее восстановление после сбоя и накат WAL; настраивать не нужно |
| 15 | статистика — в разделяемой памяти; `stats_temp_directory` удалён | совет «`pg_stat_tmp` в tmpfs» больше не нужен |
| 15 | `log_checkpoints = on`, `log_autovacuum_min_duration = 10min` по умолчанию | журнал пишет и на простаивающем сервере — нужна ротация |
| 15 | вычисляемые параметры `shared_memory_size`, `shared_memory_size_in_huge_pages` | точный расчёт huge pages одной командой |
| 15 | `hash_mem_multiplier` по умолчанию 2.0 | хеш-операции берут до `2 × work_mem` — учитывать в расчёте памяти |
| 15 | у роли `PUBLIC` отозвано право `CREATE` в схеме `public` (для новых баз) | роль, под которой работает 1С, должна быть владельцем базы (или суперпользователем на момент создания) |
| 16 | `vacuum_buffer_usage_limit` (в 17-й умолчание поднято до 2MB) | размер кольцевого буфера `VACUUM`/`ANALYZE`; 0 — без ограничения, максимум 1/8 `shared_buffers` |
| 16 | `reserved_connections`, роль `pg_use_reserved_connections` | резерв соединений для мониторинга без прав суперпользователя |
| 16 | представление `pg_stat_io` | ввод-вывод по типам процессов и контекстам |
| 16 | `pg_hba.conf`: регулярные выражения, `include`, `include_if_exists`, `include_dir` | можно держать правила в отдельных файлах |
| 16 | удалены `vacuum_defer_cleanup_age`, `promote_trigger_file`; `force_parallel_mode` → `debug_parallel_query` | при обновлении убрать из конфигурации, иначе сервер не стартует |
| 17 | `transaction_timeout` | не задавать глобально |
| 17 | `allow_alter_system`, `huge_pages_status`, `io_combine_limit` | запрет `ALTER SYSTEM`; проверка, что huge pages реально используются |
| 17 | `VACUUM` не ограничен 1 ГБ памяти, новая структура хранения идентификаторов строк | `maintenance_work_mem`/`autovacuum_work_mem` больше 1GB теперь имеют смысл |
| 17 | `summarize_wal`, `wal_summary_keep_time` | основа инкрементных копий `pg_basebackup --incremental` |
| 17 | `pg_stat_checkpointer`; из `pg_stat_bgwriter` убраны `buffers_backend*` | запросы мониторинга контрольных точек зависят от версии |
| 17 | удалены `old_snapshot_threshold`, `db_user_namespace`, `trace_recovery_messages` | убрать из конфигурации |
| 18 | асинхронный ввод-вывод: `io_method`, `io_workers`, `io_max_concurrency`, `io_max_combine_limit` | см. 5.2 |
| 18 | `effective_io_concurrency` и `maintenance_io_concurrency` по умолчанию 16 | старое значение `2` из инструкций для 1С стало ниже умолчания |
| 18 | `autovacuum_worker_slots` (restart), `autovacuum_max_workers` меняется через reload | число процессов автоочистки можно менять без перезапуска |
| 18 | `autovacuum_vacuum_max_threshold = 100000000`, `vacuum_truncate`, `vacuum_max_eager_freeze_failure_rate`, `track_cost_delay_timing` | очень большие таблицы очищаются раньше, чем по одному только проценту |
| 18 | `initdb` включает контрольные суммы данных по умолчанию | немного больше WAL; `pg_upgrade` требует совпадения настройки в старом и новом кластере (`initdb --no-data-checksums`) |
| 18 | MD5-пароли объявлены устаревшими, `md5_password_warnings` | переходить на `scram-sha-256` |
| 18 | `max_files_per_process` считает только файлы самого процесса | — |
| 18 | `log_connections` принимает список стадий; `log_lock_failures`; `file_copy_method` | — |

### 5.2. Асинхронный ввод-вывод PostgreSQL 18

| Параметр | Умолч. | Значения и смысл [PG] | Применение |
|---|---|---|---|
| `io_method` | `worker` | `worker` — ввод-вывод выполняют отдельные процессы; `io_uring` — через интерфейс ядра (сборка должна быть с `liburing`); `sync` — синхронно, как в 17-й версии | restart |
| `io_workers` | 3 | число процессов ввода-вывода; действует только при `io_method = worker` | reload |
| `io_max_concurrency` | −1 (авто, не более 64) | максимум одновременных операций одного процесса | restart |
| `io_combine_limit` / `io_max_combine_limit` | 128kB / 128kB | объединение соседних чтений в одну операцию | сессия / restart |

Что нужно знать администратору 1С:

- В 18-й версии асинхронно выполняются **чтения** (последовательные сканы, bitmap heap scan, `VACUUM`); запись и WAL — по-прежнему. Выигрыш виден на «холодных» чтениях больших таблиц, а на базе, целиком помещающейся в память, почти незаметен.
- Официальных рекомендаций 1С и Postgres Pro для этих параметров нет (в приложении K для 18-й версии они не упомянуты). Безопасный выбор — умолчание `io_method = worker`.
- `io_workers`: на ВМ с 16 и более vCPU и интенсивным чтением с диска можно поднять до vCPU/4 [практика; так считает PGTune]. Признак нехватки — все процессы `io worker` постоянно заняты (`SELECT pid, state, wait_event FROM pg_stat_activity WHERE backend_type = 'io worker';`).
- `io_method = io_uring` доступен, только если сборка собрана с `liburing`. Проверка: `SELECT enumvals FROM pg_settings WHERE name = 'io_method';`. Если значения нет в списке, строка `io_method = io_uring` не даст серверу запуститься. Для сборок с патчем 1С наличие поддержки ⚠ не подтверждено. Ставить `io_uring` только после теста: PGTune предлагает его для Linux безусловно, не проверяя сборку.
- В PostgreSQL 19 `io_workers` заменён автоматическим пулом: `io_min_workers = 2`, `io_max_workers = 8`, `io_worker_idle_timeout = 1min`, `io_worker_launch_interval = 100ms` [PG, бета-документация].

### 5.3. PostgreSQL 19 (Beta 4 на 24.09.2026): что ждёт конфигурацию 1С [PG]

| Изменение | Последствие |
|---|---|
| `standard_conforming_strings` всегда `on`; `escape_string_warning` удалён | две «обязательные для 1С» строки придётся убрать; нужна версия платформы и сборка, рассчитанные на это: нынешняя платформа сама выполняет `SET escape_string_warning = off` и использует экранирование обратной косой чертой [1С-6011] (раздел 4.10) |
| новый параметр `password_expiration_warning_threshold` (7 дней) | предупреждение о скором истечении срока действия пароля роли |
| умолчание `max_locks_per_transaction` 64 → 128; для прежней ёмкости значение нужно удвоить | при переносе конфигурации `256` → `512`, `512` → `1024` |
| `jit` по умолчанию `off` | строка `jit = off` становится избыточной |
| `io_workers` → `io_min_workers`, `io_max_workers`, `io_worker_idle_timeout`, `io_worker_launch_interval` | убрать `io_workers` из конфигурации |
| `wal_compression = on` выбирает лучший доступный метод | — |
| `default_toast_compression` по умолчанию `lz4` | — |
| `log_lock_waits` по умолчанию `on` | — |
| параллельная автоочистка (`autovacuum_max_parallel_workers`), веса порядка обработки таблиц (`autovacuum_*_score_weight`), `log_autoanalyze_min_duration` | новые возможности настройки autovacuum |
| команда `REPACK` (замена `VACUUM FULL` и `CLUSTER`, есть `CONCURRENTLY`; параметр `max_repack_replication_slots`); старые команды сохранены для совместимости | перестройка таблиц без монопольной блокировки |
| предупреждение после успешной MD5-аутентификации; удалена поддержка RADIUS | переход на SCRAM становится насущным |

Это состояние бета-версии; до выпуска детали могут измениться.

### 5.4. Параметры, которых нет в ванильном PostgreSQL

| СУБД | Параметр | Умолч. | Назначение |
|---|---|---|---|
| Сборка с патчем 1С (16.4+) | `enable_temp_memory_catalog` | `off` | каталог временных таблиц в памяти процесса (раздел 4.12) |
| Сборка с патчем 1С (17.5-11.1C, 16.9-34.1C и новее) | `enable_temp_rd_buffers` | `off` | отложенное создание файлов временных таблиц (раздел 4.12) |
| Postgres Pro | `enable_sorted_merge_join` | `on` | [PGPro] рекомендует `off` для 1С |
| Postgres Pro | `enable_parallel_temptables` | `off` | параллельные планы с временными таблицами |
| Postgres Pro | `enable_self_join_removal`, `enable_any_to_lateral_transformation`, `enable_extra_transformations`, `enable_compound_index_stats` | `on` | преобразования запросов и оценки |
| Postgres Pro | пресеты `pgpro_tune` (`1c.tune`) | — | автонастройка (раздел 3.3) |
| Tantor SE 1C | `enable_temp_memory_catalog` | `off` | то же, что в сборке 1С; по [Tantor] меняется в сеансе без перезапуска («изменения вступают в силу сразу»), после выключения рекомендуется переподключиться |
| Tantor SE 1C | `enable_delayed_temp_file` | `false` | отложенное создание временных файлов сортировок и хешей |
| Tantor SE 1C | `default_statistics_target_temp_tables` | 100 | точность статистики временных таблиц отдельно от постоянных |
| Tantor SE 1C | `enable_large_allocations` | `off` | выделения до 2 ГБ (выгрузка больших значений `bytea`/`text`) |
| Tantor SE 1C | `enable_convert_exists_as_lateral_join` (`true`), `enable_join_pushdown` (`true`), `enable_or_expansion` (`false`), `enable_filter_predicates_reordering` (`false`), а также `enable_convert_in_values_to_any`, `enable_semijoin_relocation`, `enable_sort_pushdown`, `enable_index_path_selectivity` (`true`) и др. | в скобках | преобразования планов под запросы 1С (RLS через `EXISTS`, виртуальные таблицы регистров, `OR`) |

Имена и умолчания в таблице взяты из документации соответствующей СУБД; на своём сервере проверяйте через `pg_settings`.

---

## 6. Готовые примеры конфигурации (диски SSD)

Схема: один файл `conf.d/90-1c.conf` = **общая часть** (6.1) + **блок по объёму памяти** (6.2 или 6.3). Числа — стартовые: формулы [1С]/[PGPro], а там, где официальная формула даёт диапазон, выбрана осторожная граница [практика]. Предположения по vCPU: 8 ГБ — 4, 16 ГБ — 8, 32 ГБ — 8, 64 ГБ — 16, 128 ГБ — 32.

⚠ Статус чисел в блоках ниже. Напрямую из официальных источников взяты только формулы и значения с метками [1С]/[PGPro]. Всё остальное — расчёт автора статьи, **на стенде не проверявшийся**: доля памяти под PostgreSQL на совмещённой ВМ (около половины), выбор `work_mem` и `temp_buffers` внутри официального диапазона, `max_wal_size = 16GB`, `autovacuum_*_scale_factor`, `autovacuum_vacuum_cost_limit`, `autovacuum_work_mem`, `max_parallel_maintenance_workers`, пониженные `max_connections` для малых ВМ и все оценки `vm.nr_hugepages`. Рецензия проверила арифметику и соответствие формулам, но не поведение под нагрузкой. Применяйте как отправную точку и проверяйте по разделу 10; точное число huge pages даёт только команда из раздела 7.1.

### 6.1. Общая часть (не зависит от объёма памяти)

```ini
# /etc/postgresql/17/main/conf.d/90-1c.conf — общая часть
# PostgreSQL 14–18, сборка с патчем 1С или Postgres Pro, диски SSD

# --- Соединения ---
listen_addresses = 'localhost'        # 1С на другом хосте: '192.168.10.30,localhost' или '*' (restart)
port = 5432
superuser_reserved_connections = 5
ssl = off                             # [1С]; через недоверенную сеть — on и hostssl в pg_hba.conf
password_encryption = scram-sha-256   # умолчание с 14-й версии

# --- Совместимость с платформой 1С (PostgreSQL <= 18; для 19 обе строки удалить) ---
standard_conforming_strings = off     # [1С][PGPro]
escape_string_warning = off           # [1С][PGPro]
row_security = off                    # [1С][PGPro]

# --- WAL и надёжность ---
fsync = on                            # никогда не выключать
full_page_writes = on
synchronous_commit = off              # [1С][PGPro]; при сбое теряется до ~1 с подтверждённых транзакций
wal_level = replica
#wal_compression = lz4                # [практика], не официальная рекомендация. Раскомментировать ТОЛЬКО для 15+ и только если
                                      # lz4 есть в enumvals (раздел 4.4): в 14-й версии и в сборке без lz4 такое значение
                                      # недопустимо, и сервер с ним не стартует. Универсальный вариант — wal_compression = on (pglz)
checkpoint_timeout = 15min            # [PGPro]
checkpoint_completion_target = 0.9

# --- Фоновая запись [1С][PGPro] ---
bgwriter_delay = 20ms
bgwriter_lru_maxpages = 400
bgwriter_lru_multiplier = 4.0

# --- SSD ---
random_page_cost = 1.1                # [1С][PGPro]: 1.1–1.3
effective_io_concurrency = 200        # [PGPro]: «несколько сотен» для SSD. В PostgreSQL 18 параметр управляет ещё и глубиной
                                      # упреждающего чтения AIO, а завышение, по [PG], может увеличить задержки всех запросов:
                                      # на 18-й начните с умолчания (16) или 32–64 и поднимайте по замеру
#io_method = worker                   # 18+: умолчание, не менять без теста

# --- Планировщик [1С][PGPro] ---
from_collapse_limit = 20
join_collapse_limit = 20
geqo = on
geqo_threshold = 12
jit = off
max_parallel_workers_per_gather = 0   # [PGPro]
# enable_mergejoin и cpu_operator_cost здесь НЕ задаются: платформа 1С сама ставит в каждом сеансе
# enable_mergejoin = off и cpu_operator_cost = 0.001 [1С-6011]
#enable_sorted_merge_join = off       # [PGPro] только Postgres Pro (в сборке с патчем 1С такого параметра нет —
                                      # незнакомая строка не даст серверу стартовать)

# --- Autovacuum ---
autovacuum = on                       # не выключать
autovacuum_naptime = 20s              # [1С][PGPro]
autovacuum_vacuum_scale_factor = 0.05     # [практика]
autovacuum_analyze_scale_factor = 0.02    # [практика]
autovacuum_vacuum_cost_limit = 1000       # [практика], SSD

# --- Ресурсы ядра ---
max_files_per_process = 8000          # [1С]; у службы нужен LimitNOFILE не меньше (раздел 7.6)

# --- Расширения ---
shared_preload_libraries = 'plantuner, pg_stat_statements'   # библиотеки должны существовать, иначе сервер не стартует
plantuner.fix_empty_table = on        # [PGPro]
pg_stat_statements.max = 10000
# online_analyze намеренно не загружается (раздел 4.14)

# --- Журнал и статистика ---
log_line_prefix = '%m [%p] %q%u@%d/%a '
log_checkpoints = on
log_lock_waits = on
log_temp_files = 100MB
log_autovacuum_min_duration = 30s
log_min_duration_statement = 10s
lc_messages = 'C'                     # английские сообщения; 'en_US.UTF-8', если локаль есть в `locale -a`
track_io_timing = on                  # после проверки pg_test_timing
track_activity_query_size = 8192      # restart
```

### 6.2. PostgreSQL на отдельной ВМ (сервер 1С — на другом хосте)

Память ВМ целиком считается памятью PostgreSQL; в общей части замените `listen_addresses`.

```ini
# ===== 8 ГБ RAM, 4 vCPU, отдельный сервер СУБД =====
max_connections = 300                 # малая ВМ; [PGPro] советует >= 500 — поднять, если хватает памяти
shared_buffers = 2GB                  # RAM/4
effective_cache_size = 6GB            # RAM − shared_buffers
work_mem = 32MB                       # нижняя граница [1С]
maintenance_work_mem = 512MB          # RAM/16
autovacuum_work_mem = 256MB
temp_buffers = 32MB
max_locks_per_transaction = 256       # [PGPro]
min_wal_size = 1GB
max_wal_size = 2GB                    # 2 × min_wal_size
autovacuum_max_workers = 4            # не меньше 4
max_worker_processes = 8
max_parallel_workers = 4
max_parallel_maintenance_workers = 2
huge_pages = try                      # на Ubuntu 26.04: on + vm.nr_hugepages ≈ 1100 (считать командой)
```

```ini
# ===== 16 ГБ RAM, 8 vCPU, отдельный сервер СУБД =====
max_connections = 500
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 1GB
autovacuum_work_mem = 512MB
temp_buffers = 64MB
max_locks_per_transaction = 512       # [1С]: 512…2000
min_wal_size = 2GB
max_wal_size = 4GB
autovacuum_max_workers = 4
max_worker_processes = 8
max_parallel_workers = 8
max_parallel_maintenance_workers = 2
huge_pages = try                      # рекомендуется on + vm.nr_hugepages ≈ 2200
```

```ini
# ===== 32 ГБ RAM, 8 vCPU, отдельный сервер СУБД =====
max_connections = 500
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 128MB
maintenance_work_mem = 2GB
autovacuum_work_mem = 1GB
temp_buffers = 128MB                  # при > 150 реальных соединений снизить до 64MB
max_locks_per_transaction = 512
min_wal_size = 4GB
max_wal_size = 8GB
autovacuum_max_workers = 4
max_worker_processes = 8
max_parallel_workers = 8
max_parallel_maintenance_workers = 4
huge_pages = on                       # vm.nr_hugepages ≈ 4300
```

```ini
# ===== 64 ГБ RAM, 16 vCPU, отдельный сервер СУБД =====
max_connections = 1000
shared_buffers = 16GB
effective_cache_size = 48GB
work_mem = 128MB
maintenance_work_mem = 4GB            # верхняя граница [1С]
autovacuum_work_mem = 1GB
temp_buffers = 128MB
max_locks_per_transaction = 512
min_wal_size = 4GB
max_wal_size = 16GB                   # [практика]: выше формулы 2 × min — под 16 ГБ shared_buffers
autovacuum_max_workers = 6            # vCPU/4..vCPU/2
max_worker_processes = 16
max_parallel_workers = 16
max_parallel_maintenance_workers = 4
#io_workers = 4                       # только PostgreSQL 18
huge_pages = on                       # vm.nr_hugepages ≈ 8500
```

```ini
# ===== 128 ГБ RAM, 32 vCPU, отдельный сервер СУБД =====
max_connections = 1000                # [1С]: сеансы/8 … сеансы/4, не меньше 500
shared_buffers = 32GB
effective_cache_size = 96GB
work_mem = 256MB                      # верхняя граница [1С]; при > 80 одновременно тяжёлых запросов — 128MB
maintenance_work_mem = 4GB
autovacuum_work_mem = 2GB
temp_buffers = 128MB                  # не 256MB: при сотнях соединений это десятки гигабайт
max_locks_per_transaction = 1024      # большие конфигурации (ERP): до 2000 [1С]
min_wal_size = 4GB
max_wal_size = 16GB                   # [практика]
autovacuum_max_workers = 8
max_worker_processes = 32
max_parallel_workers = 32
max_parallel_maintenance_workers = 8
#io_workers = 8                       # только PostgreSQL 18
huge_pages = on                       # vm.nr_hugepages ≈ 17000
```

### 6.3. PostgreSQL и сервер 1С на одной ВМ

Под PostgreSQL отводится примерно половина памяти, вторая половина — рабочим процессам 1С и ОС [практика; принцип «вычесть память других приложений» — [1С]]. `listen_addresses = 'localhost'`, в свойствах базы 1С сервер СУБД — `localhost` (или `127.0.0.1`).

```ini
# ===== 8 ГБ RAM, 4 vCPU, 1С + PostgreSQL (минимальная конфигурация, до ~10 пользователей) =====
max_connections = 200
shared_buffers = 1GB                  # четверть от ~4 ГБ, отведённых СУБД
effective_cache_size = 3GB
work_mem = 32MB                       # при > 15 одновременно активных запросов — 16MB
maintenance_work_mem = 256MB
autovacuum_work_mem = 128MB
temp_buffers = 32MB
max_locks_per_transaction = 256
min_wal_size = 1GB
max_wal_size = 2GB
autovacuum_max_workers = 4
max_worker_processes = 8
max_parallel_workers = 4
max_parallel_maintenance_workers = 2
huge_pages = try                      # на Ubuntu 26.04: on + vm.nr_hugepages ≈ 560
```

```ini
# ===== 16 ГБ RAM, 8 vCPU, 1С + PostgreSQL =====
max_connections = 300
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 32MB
maintenance_work_mem = 512MB
autovacuum_work_mem = 256MB
temp_buffers = 32MB
max_locks_per_transaction = 256
min_wal_size = 1GB
max_wal_size = 2GB
autovacuum_max_workers = 4
max_worker_processes = 8
max_parallel_workers = 4
max_parallel_maintenance_workers = 2
huge_pages = try                      # на Ubuntu 26.04: on + vm.nr_hugepages ≈ 1100
```

```ini
# ===== 32 ГБ RAM, 8 vCPU, 1С + PostgreSQL =====
max_connections = 500
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 1GB
autovacuum_work_mem = 512MB
temp_buffers = 64MB
max_locks_per_transaction = 512
min_wal_size = 2GB
max_wal_size = 4GB
autovacuum_max_workers = 4
max_worker_processes = 8
max_parallel_workers = 8
max_parallel_maintenance_workers = 2
huge_pages = try                      # рекомендуется on + vm.nr_hugepages ≈ 2200
```

```ini
# ===== 64 ГБ RAM, 16 vCPU, 1С + PostgreSQL =====
max_connections = 500
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 128MB
maintenance_work_mem = 2GB
autovacuum_work_mem = 1GB
temp_buffers = 64MB
max_locks_per_transaction = 512
min_wal_size = 4GB
max_wal_size = 8GB
autovacuum_max_workers = 4            # ядра делятся с процессами 1С
max_worker_processes = 16
max_parallel_workers = 8
max_parallel_maintenance_workers = 4
huge_pages = on                       # vm.nr_hugepages ≈ 4300
```

```ini
# ===== 128 ГБ RAM, 32 vCPU, 1С + PostgreSQL =====
max_connections = 1000
shared_buffers = 16GB
effective_cache_size = 48GB
work_mem = 128MB
maintenance_work_mem = 4GB
autovacuum_work_mem = 1GB
temp_buffers = 128MB
max_locks_per_transaction = 512       # большие конфигурации: 1024–2000 [1С]
min_wal_size = 4GB
max_wal_size = 16GB                   # [практика]
autovacuum_max_workers = 8
max_worker_processes = 16
max_parallel_workers = 16
max_parallel_maintenance_workers = 4
#io_workers = 4                       # только PostgreSQL 18
huge_pages = on                       # vm.nr_hugepages ≈ 8500
```

Числа `vm.nr_hugepages` — оценка «`shared_buffers` плюс несколько процентов служебной памяти» для страниц 2 МБ; точное значение даёт только команда из раздела 7.1, причём после каждого изменения `shared_buffers`, `max_connections`, `max_locks_per_transaction`.

На совмещённой ВМ дополнительно ограничьте аппетит сервера 1С в свойствах рабочего сервера кластера (например, «Критический объём памяти процессов», «Временно допустимый объём памяти процессов»), иначе рабочие процессы `rphost` вытеснят страничный кэш, на который рассчитан `effective_cache_size`.

### 6.4. Порядок внедрения конфигурации

```bash
# 1. Копия текущего состояния
sudo cp -a /etc/postgresql/17/main /root/pg17-conf.bak-$(date +%F)
sudo -u postgres psql -Atc "SELECT name||'='||setting FROM pg_settings WHERE source <> 'default'" \
  | sudo tee /root/pg_settings.before >/dev/null     # именно через tee: перенаправление «> /root/…» выполнил бы ваш shell без прав root

# 2. Записать общую часть + свой блок
sudo -u postgres nano /etc/postgresql/17/main/conf.d/90-1c.conf

# 3. Проверить файлы, не применяя (сервер ещё работает на старых значениях).
#    Текст «setting could not be applied» у параметра — не ошибка, а признак «нужен перезапуск»
sudo -u postgres psql -c "SELECT sourcefile, sourceline, name, setting, error FROM pg_file_settings WHERE error IS NOT NULL;"
ls /usr/lib/postgresql/17/lib/ | grep -E 'plantuner|pg_stat_statements'

# 4. Остановить сервер 1С, затем PostgreSQL; рассчитать huge pages (раздел 7.1)
sudo systemctl stop 'srv1cv8-*'            # имя юнита — см. systemctl list-units 'srv1cv8*'
sudo systemctl stop postgresql@17-main
sudo -u postgres /usr/lib/postgresql/17/bin/postgres -D /var/lib/postgresql/17/main \
     -c config_file=/etc/postgresql/17/main/postgresql.conf -C shared_memory_size_in_huge_pages

# 5. Запустить и убедиться, что значения применились
sudo systemctl start postgresql@17-main
pg_lsclusters
sudo -u postgres psql -c "SELECT name, setting, unit, sourcefile FROM pg_settings WHERE source = 'configuration file' ORDER BY name;"
sudo -u postgres psql -c "SELECT name FROM pg_settings WHERE pending_restart;"     # должно быть пусто
sudo tail -n 50 /var/log/postgresql/postgresql-17-main.log

# 6. Если сервер не стартовал — причина в журнале; вернуть прежний файл и запустить снова
sudo journalctl -u postgresql@17-main -n 50 --no-pager
```

---

## 7. Тюнинг ОС под PostgreSQL для 1С

Подробный разбор sysctl, лимитов, THP и huge pages — в `kb/linux/09-tyuning-yadra-lokali-vremya-bezopasnost.md`; здесь — сводка значений именно для сервера СУБД 1С. Официальные требования 1С и Postgres Pro к ОС ограничиваются тремя пунктами: отключить гиперпоточность, отключить энергосбережение, не допускать своппинга разделяемой памяти [1С][PGPro]. Всё остальное — рекомендации PostgreSQL и практика.

### 7.1. Huge pages: расчёт и включение

Зачем: при `shared_buffers` в гигабайты таблицы страниц каждого серверного процесса (а их сотни) занимают заметную память и нагружают TLB; страницы 2 МБ уменьшают таблицы в 512 раз и никогда не уходят в swap — это заодно выполняет требование «не свопить разделяемую память». Действует только на основную область разделяемой памяти [PG].

```bash
# 1. Размер страницы и текущее состояние
grep -i huge /proc/meminfo

# 2. Сколько страниц нужно (PostgreSQL 15+). Сервер должен быть ОСТАНОВЛЕН
sudo systemctl stop postgresql@17-main
sudo -u postgres /usr/lib/postgresql/17/bin/postgres -D /var/lib/postgresql/17/main \
     -c config_file=/etc/postgresql/17/main/postgresql.conf -C shared_memory_size_in_huge_pages
# пример вывода: 4300

# 3. Зарезервировать сейчас и навсегда
sudo sysctl -w vm.nr_hugepages=4300
echo 'vm.nr_hugepages = 4300' | sudo tee /etc/sysctl.d/91-hugepages.conf
grep -E 'HugePages_(Total|Free|Rsvd)' /proc/meminfo      # Total должен стать 4300

# 4. Включить в PostgreSQL и запустить
#    conf.d/90-1c.conf:  huge_pages = on
sudo systemctl start postgresql@17-main
sudo -u postgres psql -c "SHOW huge_pages_status;"        # PostgreSQL 17+: on
grep -E 'HugePages_(Total|Free|Rsvd)' /proc/meminfo      # Free уменьшился или Rsvd > 0
```

На работающем сервере то же число показывает `SHOW shared_memory_size_in_huge_pages;` — удобно, если `shared_buffers` менять не собираетесь. Команда `postgres -C` для вычисляемых параметров (`shared_memory_size`, `shared_memory_size_in_huge_pages`) требует остановленного сервера [PG]; она учитывает `postgresql.conf` и `conf.d`, но показывает значения из файлов, а не из работающего экземпляра.

**PostgreSQL 14** (сборка `14.x-1.1C`): параметра `shared_memory_size_in_huge_pages` ещё нет. Способ из документации 14-й версии — запустить сервер **без** huge pages и посмотреть размер анонимного разделяемого сегмента главного процесса:

```bash
sudo head -1 /var/lib/postgresql/14/main/postmaster.pid                 # PID главного процесса, например 4170
sudo pmap 4170 | awk '/rw-s/ && /zero/ {print $2}'                      # например 6490428K
grep ^Hugepagesize /proc/meminfo                                        # Hugepagesize: 2048 kB
# 6490428 / 2048 ≈ 3169,2 → нужно не меньше 3170 страниц
```

Если после резервирования сервер с `huge_pages = on` всё равно не стартует, [PG] советует проверить ещё два условия: право пользователя ОС `postgres` на huge pages (`vm.hugetlb_shm_group` — нужно для разделяемой памяти System V; при умолчании `shared_memory_type = mmap` обычно не требуется) и лимит блокируемой памяти (`ulimit -l`, для службы systemd — `LimitMEMLOCK=infinity`). Размер страницы, отличный от умолчания ОС (например, 1 ГБ вместо обычных 2 МБ), задаётся параметром `huge_page_size` (restart), а страницы такого размера резервируются через `/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages`; для ВМ с 1С в этом обычно нет нужды.

Правила:

- `huge_pages = try` (умолчание) — при нехватке страниц сервер молча работает на обычных; `on` — не запустится, пока страниц не хватит [PG]. В продуктиве с настроенным резервом ставьте `on`: так проблема видна сразу.
- Если `HugePages_Total` меньше запрошенного — память фрагментирована; надёжнее резервировать при загрузке (sysctl-файл применяется рано) и проверить после перезагрузки.
- Зарезервированная память недоступна остальным процессам. На совмещённой ВМ не резервируйте больше, чем посчитано: лишние страницы просто отнимут память у 1С.
- После изменения `shared_buffers`, `max_connections`, `max_locks_per_transaction`, `max_prepared_transactions`, списка `shared_preload_libraries` число нужно пересчитать.
- **Ubuntu 26.04 (ядро 7.0):** в примечаниях к выпуску (страница «Changes since 25.10», проверено 10.10.2026) описана известная проблема — изменение в Linux 7.0 «may cause a significant throughput and latency regression on PostgreSQL»; по тому же обсуждению в списке рассылки ядра системы с huge pages не затронуты, и Canonical пишет: «ensure your PostgreSQL deployments have huge pages on» и чтобы параметр `huge_pages` был установлен в `on` [Canonical]. На странице изменений точечного выпуска 26.04.1 исправление этой проблемы не упомянуто, поэтому считайте рекомендацию действующей и для 26.04.1. Проблема привязана к ядру, а не к выпуску: на Ubuntu 22.04/24.04 со штатными ядрами (5.15/6.8) её нет, но если на 24.04 установлено HWE-ядро 7.0 (`uname -r`), поступайте так же, как на 26.04 (вывод рецензента из описания проблемы).

### 7.2. Transparent Huge Pages (THP)

[PG] (описание параметра `huge_pages`): прозрачные огромные страницы у части пользователей на некоторых версиях Linux вызывали падение производительности PostgreSQL, поэтому их использование «is currently discouraged (unlike explicit use of `huge_pages`)».

```bash
cat /sys/kernel/mm/transparent_hugepage/enabled     # always [madvise] never — текущее в скобках
cat /sys/kernel/mm/transparent_hugepage/defrag
grep AnonHugePages /proc/meminfo
```

- В Ubuntu режим по умолчанию, по практике, — `madvise`: THP получают только процессы, явно их запросившие. PostgreSQL их не запрашивает, так что для него это равносильно выключению. **Уточнено 11.10.2026**: найден первоисточник происхождения умолчания — рассылка kernel-team Ubuntu, правка «UBUNTU: SAUCE: use CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y as default», принятая в июле 2017 года для 17.10 (lists.ubuntu.com/archives/kernel-team/2017-July/085576.html). Конфигурацию ядра нынешних выпусков прочитать по-прежнему не удалось. Ранее было не подтверждено: документ Canonical с умолчанием THP для 22.04/24.04/26.04 при рецензии найти не удалось (файл конфигурации ядра Ubuntu не открылся), а в облачных и нестандартных образах умолчание может отличаться — **всегда смотрите фактическое значение** командой выше, а не полагайтесь на это утверждение.
- Если показано `always` или нужна гарантия — выключить: временно `echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag`; постоянно — параметр ядра `transparent_hugepage=never` в `GRUB_CMDLINE_LINUX_DEFAULT` файла `/etc/default/grub`, затем `sudo update-grub` и перезагрузка.
- На совмещённой ВМ `never` действует и на процессы 1С; официальной позиции 1С о THP для `rphost` в открытых материалах нет ⚠.

### 7.3. Память: swap, overcommit, «грязные» страницы

| Параметр | Умолч. | Значение | Основание |
|---|---|---|---|
| `vm.swappiness` | 60 | 10 на совмещённой ВМ; 1 на выделенном сервере СУБД | [практика] |
| `vm.overcommit_memory` | 0 | 2 — **только** на выделенном сервере СУБД; на совмещённом оставить 0 | [PG] |
| `vm.overcommit_ratio` | 50 | при `overcommit_memory = 2` — подбирать (обычно 80–95) | [PG]: «при необходимости» |
| `vm.dirty_background_bytes` | 0 | 67108864 (64 МБ) | [практика] |
| `vm.dirty_bytes` | 0 | 536870912 (512 МБ) | [практика] |
| `vm.nr_hugepages` | 0 | по расчёту (7.1) | [PG] |

- **swap**: полностью отключать не обязательно; небольшой swap (2–8 ГБ) при низком `swappiness` — подушка от OOM killer. Активный своппинг процессов PostgreSQL недопустим: проверка — `vmstat 1` (колонки `si`/`so` должны быть нулевыми).
- **overcommit**: при `vm.overcommit_memory = 2` ядро отказывает в выделении сверх `CommitLimit = (RAM − huge pages) × overcommit_ratio / 100 + swap`, и PostgreSQL получает обычную ошибку нехватки памяти в одном запросе вместо убийства главного процесса OOM killer'ом [PG]. На ВМ с сервером 1С так делать нельзя: процессы `rphost` резервируют много виртуальной памяти и начнут получать отказы. Обратите внимание, что память под huge pages из лимита исключается — при `ratio = 50` на сервере с большими `shared_buffers` ошибки начнутся при свободной памяти.
- **dirty_***: при умолчаниях в процентах (10 % / 20 % памяти) на ВМ с десятками гигабайт ядро копит гигабайты несброшенных данных, а потом сбрасывает их залпом — в этот момент контрольная точка и `fsync` WAL «замирают». Абсолютные значения делают запись ровной. Задание `*_bytes` автоматически обнуляет парные `*_ratio` и наоборот.
- ⚠ Числа `vm.swappiness` и `vm.dirty_*` — распространённая практика (те же 64 МБ / 512 МБ встречаются в готовых профилях настройки для PostgreSQL, см. `kb/linux/09-tyuning-yadra-lokali-vremya-bezopasnost.md`), а не официальная рекомендация: ни [1С], ни [PGPro], ни [PG] конкретных значений не дают. Статьи сообщества при рецензии не читались.

```bash
sudo tee /etc/sysctl.d/90-postgresql-1c.conf >/dev/null <<'EOF'
vm.swappiness = 10
vm.dirty_background_bytes = 67108864
vm.dirty_bytes = 536870912
# Только выделенный сервер СУБД (без сервера 1С на этой же ВМ):
#vm.overcommit_memory = 2
#vm.overcommit_ratio = 90
# Только многосокетное «железо» (NUMA):
#kernel.numa_balancing = 0
#vm.zone_reclaim_mode = 0
EOF
sudo sysctl --system                                   # применить все файлы
sysctl vm.swappiness vm.dirty_bytes vm.dirty_background_bytes vm.overcommit_memory
```

Защита главного процесса от OOM killer: в Debian-раскладке посмотрите, что уже задано в юните, — `systemctl show postgresql@17-main -p OOMScoreAdjust`; механизм `PG_OOM_ADJUST_FILE`/`PG_OOM_ADJUST_VALUE` описан в [PG].

### 7.4. Диски: планировщик ввода-вывода, файловая система, noatime

```bash
lsblk -d -o NAME,ROTA,SCHED,MODEL                      # ROTA=0 — SSD/виртуальный диск; SCHED — планировщик
cat /sys/block/sda/queue/scheduler                     # текущий — в квадратных скобках
echo none | sudo tee /sys/block/sda/queue/scheduler    # до перезагрузки
echo 'ACTION=="add|change", KERNEL=="sd[a-z]|vd[a-z]|nvme[0-9]n[0-9]", ATTR{queue/scheduler}="none"' \
  | sudo tee /etc/udev/rules.d/60-io-scheduler.rules   # постоянно
sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=block   # применить правило без перезагрузки
findmnt -no TARGET,SOURCE,FSTYPE,OPTIONS -T /var/lib/postgresql   # том, на котором лежат данные, и параметры его монтирования
```

Ключ `-T` (`--target`) обязателен: без него `findmnt /var/lib/postgresql` ищет точку монтирования **именно с таким путём** и ничего не выводит, если каталог данных лежит на корневом или другом вышестоящем томе.

- Планировщик: для NVMe и виртуальных дисков в ВМ — `none` (очередь всё равно упорядочивает гипервизор); для SATA SSD — `none` или `mq-deadline`. `bfq` для СУБД не использовать [практика].
- Файловая система: ext4 или XFS; опция `noatime` в `/etc/fstab` убирает запись времени доступа при каждом чтении файла данных: `UUID=…  /var/lib/postgresql  ext4  defaults,noatime  0  2`. Применить без перезагрузки: `sudo mount -o remount,noatime <точка_монтирования>` — точку монтирования берите из колонки `TARGET` вывода `findmnt -T` (если данные лежат на корневом томе, это `/`, а не `/var/lib/postgresql`). В Ubuntu по умолчанию действует `relatime`, при котором время доступа обновляется редко, так что выигрыш от `noatime` небольшой.
- TRIM — штатным `fstrim.timer`, а не опцией `discard`.
- Данные PostgreSQL, WAL и временное табличное пространство по возможности на разных томах — но только если под ними разные физические накопители.
- ВМ на Windows-хосте: виртуальный диск фиксированного размера на SSD; не включайте на хосте режимы, игнорирующие сброс кэша записи, — они обнуляют гарантию `fsync`. Реальную скорость синхронной записи покажет `/usr/lib/postgresql/17/bin/pg_test_fsync -f /var/lib/postgresql/17/main/pg_test_fsync.tmp` (неправдоподобно большие значения — десятки тысяч операций в секунду на обычном SSD — признак того, что сброс не доходит до диска).

### 7.5. Процессор: энергосбережение и гиперпоточность

- Энергосбережение отключать обязательно [1С][PGPro]: с ним задержки ответов СУБД растут непредсказуемо. 1С выполняет множество коротких последовательных запросов, поэтому чувствительна к частоте одного ядра сильнее, чем к числу ядер.
- Физический сервер: в BIOS/UEFI профиль «Maximum Performance», отключить C-состояния глубже C1; в ОС — `cpupower frequency-info`, `sudo cpupower frequency-set -g performance`.
- Виртуальная машина: управления частотой внутри гостя обычно нет (каталог `/sys/devices/system/cpu/cpu0/cpufreq` отсутствует) — настраивается **хост**: на Windows-хосте схема электропитания «Высокая производительность» (`powercfg /setactive SCHEME_MIN`), в BIOS хоста — отключить энергосбережение. Не выделяйте ВМ больше vCPU, чем физических ядер хоста.
- Гиперпоточность официально рекомендуют отключать [1С][PGPro] (дословно: «Отключить технологию гиперпоточности»; способ и обоснование в источниках не приведены). В сообществе это спорно (⚠ ссылками не подтверждено — статьи при рецензии не читались). В виртуальной машине гиперпоточность управляется на **хосте** (BIOS/UEFI), из гостевой ОС её не отключить; гость видит vCPU, которые гипервизор раскладывает по логическим ядрам. Решение принимайте по замеру (раздел 10) до и после.
- Утилита `cpupower` в Ubuntu входит в пакеты `linux-tools-common` и `linux-tools-$(uname -r)`; на ВМ она обычно сообщает, что драйвер управления частотой недоступен, — это нормально.

### 7.6. Лимиты службы: открытые файлы

`/etc/security/limits.conf` на службы systemd не действует. Лимиты PostgreSQL задаются в юните:

```bash
systemctl show postgresql@17-main -p LimitNOFILE -p LimitNOFILESoft -p TasksMax
sudo systemctl edit postgresql@17-main
```

```ini
[Service]
LimitNOFILE=65536
```

```bash
sudo systemctl restart postgresql@17-main
sudo cat /proc/$(sudo head -1 /var/lib/postgresql/17/main/postmaster.pid)/limits | grep -i 'open files'
```

Значение должно быть не меньше `max_files_per_process` (8000–10000). Общесистемный предел `fs.file-max` в современных Ubuntu заведомо достаточен. Ошибка `Too many open files` в журнале PostgreSQL — признак того, что лимит процесса ниже потребности.

### 7.7. NUMA

Актуально только для многосокетных физических серверов и ВМ, которым проброшена NUMA-топология: `lscpu | grep -i numa`, `numactl --hardware`. Значения [практика]: `kernel.numa_balancing = 0`, `vm.zone_reclaim_mode = 0` (последнее и так умолчание). В ВМ с одним виртуальным узлом NUMA делать ничего не нужно; размер ВМ желательно держать в пределах одного физического узла хоста. В PostgreSQL 18 появились средства наблюдения за размещением разделяемой памяти по узлам (сборка с `libnuma`), параметров настройки NUMA в `postgresql.conf` нет.

### 7.8. Контрольный список ОС

| Что | Проверка | Целевое состояние |
|---|---|---|
| Huge pages | `grep -i hugepages /proc/meminfo`; `SHOW huge_pages_status;` | `Total` = расчётному, статус `on` |
| THP | `cat /sys/kernel/mm/transparent_hugepage/enabled` | `[madvise]` или `[never]` |
| Swap | `vmstat 1 5`, `swapon --show` | `si`/`so` = 0 |
| `vm.dirty_*` | `sysctl vm.dirty_bytes vm.dirty_background_bytes` | 536870912 / 67108864 |
| Планировщик | `cat /sys/block/*/queue/scheduler` | `[none]` или `[mq-deadline]` |
| `noatime` | `findmnt -no OPTIONS -T /var/lib/postgresql` | есть `noatime` (допустим и `relatime`) |
| Лимит файлов | `/proc/<pid>/limits` | ≥ `max_files_per_process` |
| Частота CPU | `lscpu` (строки с `MHz`); на хосте — схема электропитания | максимальная производительность |
| Время | `timedatectl` | синхронизация включена, часовой пояс верный |

---

## 8. pg_hba.conf: доступ и аутентификация

### 8.1. Формат и порядок обработки

Файл: `/etc/postgresql/NN/main/pg_hba.conf` (Postgres Pro — в каталоге данных; точный путь — `SHOW hba_file;`). Читается при старте и при reload [PG].

```
local      БАЗА  ПОЛЬЗОВАТЕЛЬ              МЕТОД  [параметры]
host       БАЗА  ПОЛЬЗОВАТЕЛЬ  АДРЕС       МЕТОД  [параметры]
hostssl    БАЗА  ПОЛЬЗОВАТЕЛЬ  АДРЕС       МЕТОД  [параметры]
hostnossl  БАЗА  ПОЛЬЗОВАТЕЛЬ  АДРЕС       МЕТОД  [параметры]
include / include_if_exists / include_dir  ФАЙЛ-ИЛИ-КАТАЛОГ        # PostgreSQL 16+
```

| Поле | Значения |
|---|---|
| Тип | `local` — Unix-сокет; `host` — TCP/IP (с SSL или без); `hostssl` — только TCP с SSL; `hostnossl` — только без SSL; `hostgssenc`/`hostnogssenc` — GSSAPI |
| База | `all`; имя; список через запятую; `sameuser`; `samerole`; `replication` (только физическая репликация, под `all` не попадает); `@файл`; с 16-й версии — регулярное выражение с `/` в начале |
| Пользователь | `all`; имя; `+роль` (члены роли); список; `@файл`; регулярное выражение с `/` |
| Адрес | CIDR (`192.168.10.20/32`, `192.168.10.0/24`, `::1/128`); `0.0.0.0/0` и `::0/0` — все; `samehost`; `samenet`; имя хоста |
| Метод | см. таблицу ниже |

Правила обработки [PG]:

1. Записи просматриваются **сверху вниз**; используется **первая**, совпавшая по типу соединения, адресу, базе и пользователю.
2. «Проваливания» нет: если по найденной записи аутентификация не прошла, следующие не пробуются.
3. Если не совпала ни одна запись — отказ.
4. Отсюда порядок: сначала узкие и строгие правила (включая `reject`), потом широкие.
5. Кроме записи в `pg_hba.conf` нужны `listen_addresses` (для TCP), право `CONNECT` на базу и открытый порт в межсетевом экране.

| Метод | Что делает | Где применять |
|---|---|---|
| `peer` | имя пользователя ОС должно совпасть с именем роли; только для `local` | администрирование: `sudo -u postgres psql` |
| `scram-sha-256` | пароль по протоколу SCRAM; хеш в `pg_authid` | все TCP-подключения, включая сервер 1С |
| `md5` | MD5 либо SCRAM (если пароль роли сохранён как SCRAM — автоматически используется SCRAM); **устарел с 18-й версии** | только для совместимости со старыми клиентами |
| `password` | пароль открытым текстом | не использовать |
| `trust` | без проверки | только временно при восстановлении доступа; в продуктиве недопустим |
| `reject` | безусловный отказ | явный запрет для адреса или роли выше разрешающих правил |
| `cert`, `gss`, `ldap`, `pam`, `ident`, `oauth` (18+) | сертификаты, Kerberos, каталог и т. д. | для 1С обычно не нужны |

### 8.2. Типовой набор для сервера 1С

Сервер 1С (процессы `rphost`, `rmngr`) подключается к PostgreSQL **по TCP** под ролью, указанной в свойствах информационной базы, — даже когда СУБД на той же машине (`localhost`). Пользователям 1С доступ к порту 5432 не нужен.

Вариант А — 1С и PostgreSQL на одной ВМ (по сути, умолчание Debian-раскладки):

```
# TYPE  DATABASE  USER      ADDRESS         METHOD
local   all       postgres                  peer             # sudo -u postgres psql
local   all       all                       peer
host    all       all       127.0.0.1/32    scram-sha-256    # сервер 1С через localhost
host    all       all       ::1/128         scram-sha-256
```

`listen_addresses = 'localhost'`; порт 5432 наружу не открывается.

Вариант Б — сервер 1С на отдельном хосте `192.168.10.20`, администратор с `192.168.10.5`:

```
# TYPE  DATABASE  USER      ADDRESS             METHOD
local   all       postgres                      peer
local   all       all                           peer
host    all       all       127.0.0.1/32        scram-sha-256
host    all       all       ::1/128             scram-sha-256
host    all       usr1cv8   192.168.10.20/32    scram-sha-256    # сервер 1С: все базы, включая служебную postgres
host    all       postgres  192.168.10.5/32     scram-sha-256    # рабочее место администратора (psql, pgAdmin)
host    all       all       0.0.0.0/0           reject           # всё остальное — явный отказ (необязательно: отказ и так по умолчанию)
```

`listen_addresses = '192.168.10.30,localhost'` (адрес интерфейса СУБД) и правило межсетевого экрана, разрешающее 5432/tcp только с `192.168.10.20` и `192.168.10.5`.

Замечания:

- В поле базы для роли 1С ставьте `all`: создаваемой базы в момент создания ещё нет, поэтому платформа сначала подключается к уже существующей служебной базе. ⚠ не подтверждено документацией платформы, к какой именно: в сообщениях об ошибках, которые приводят в сообществе, фигурирует база `postgres` (`no pg_hba.conf entry for host …, user …, database "postgres"`), но первоисточником это не проверено. Запись на `all` заведомо достаточна; если нужно сузить — перечислите базы 1С и `postgres` через запятую и проверьте создание тестовой базы.
- Роль 1С: по документации платформы привилегия `SUPERUSER` нужна **в момент создания информационной базы** (одного `CREATEDB` недостаточно), после успешного создания её можно отозвать — `ALTER USER usr1cv8 WITH NOSUPERUSER;` (см. `kb/its-docs/adm-gl05-spisok-infobaz.md`). Для каждой следующей создаваемой из 1С базы привилегию придётся выдавать снова. На практике многие оставляют `postgres`; отдельная роль безопаснее.
- Не пишите `host all all 0.0.0.0/0 md5` «чтобы работало»: это открывает подбор пароля суперпользователя со всей сети.
- Если между серверами недоверенная сеть — `ssl = on`, тип записи `hostssl`.

### 8.3. Команды

```bash
sudo -u postgres nano /etc/postgresql/17/main/pg_hba.conf
sudo -u postgres psql -c "SELECT rule_number, line_number, type, database, user_name, address, auth_method, error FROM pg_hba_file_rules;"   # проверка ДО reload: error должен быть пуст
sudo systemctl reload postgresql@17-main                       # изменения pg_hba.conf перезапуска не требуют
sudo -u postgres psql -c "CREATE ROLE usr1cv8 LOGIN SUPERUSER PASSWORD 'СЛОЖНЫЙ_ПАРОЛЬ';"   # SUPERUSER — на время создания базы из 1С
#   … создать информационную базу средствами 1С …
sudo -u postgres psql -c "ALTER USER usr1cv8 WITH NOSUPERUSER;"                              # после успешного создания базы
sudo -u postgres psql -c "\password postgres"                  # задать пароль интерактивно (не попадает в историю и журнал)
psql -h 192.168.10.30 -U usr1cv8 -d postgres -c "SELECT current_user, inet_client_addr();"    # проверка с хоста сервера 1С
```

Колонка `rule_number` в `pg_hba_file_rules` есть с 16-й версии; в более ранних используйте `line_number`. По умолчанию представление доступно только суперпользователю.

Пароль, написанный прямо в `CREATE ROLE … PASSWORD '…'`, попадает в историю shell и — при `log_statement = 'ddl'`/`'all'` или ошибке в команде — в журнал сервера. Безопаснее создать роль без пароля (`CREATE ROLE usr1cv8 LOGIN SUPERUSER;`) и задать его интерактивно: `sudo -u postgres psql -c "\password usr1cv8"` (psql сам хеширует пароль по `password_encryption` и отправляет на сервер уже хеш).

Какой хеш у паролей и переход с MD5 на SCRAM [PG]:

```sql
SELECT rolname,
       CASE WHEN rolpassword IS NULL THEN 'нет пароля'
            WHEN rolpassword LIKE 'md5%' THEN 'md5'
            WHEN rolpassword LIKE 'SCRAM-SHA-256$%' THEN 'scram-sha-256' END AS hash
FROM pg_authid WHERE rolcanlogin;
-- переход: password_encryption = scram-sha-256 (умолчание с 14-й версии) → задать пароли заново → заменить md5 на scram-sha-256 в pg_hba.conf → reload
ALTER ROLE usr1cv8 PASSWORD 'СЛОЖНЫЙ_ПАРОЛЬ';
```

### 8.4. Типовые сообщения об ошибках

| Сообщение | Причина | Что делать |
|---|---|---|
| `FATAL: no pg_hba.conf entry for host "192.168.10.20", user "usr1cv8", database "buh", no encryption` | нет подходящей строки | добавить строку `host`, reload |
| `FATAL: password authentication failed for user "usr1cv8"` | неверный пароль, либо у роли нет пароля, либо пароль хранится в MD5, а метод — `scram-sha-256` | задать пароль заново при `password_encryption = scram-sha-256` |
| `FATAL: Peer authentication failed for user "postgres"` | подключение через сокет не от пользователя ОС `postgres` | `sudo -u postgres psql` либо подключаться по TCP: `psql -h localhost -U postgres` |
| `authentication method 10 not supported` (в 1С или старом клиенте) | клиентская библиотека не умеет SCRAM | обновить платформу/сборку; обход — `password_encryption = md5`, задать пароль заново, метод `md5` (устарел) |
| `Connection refused` | сервер не слушает адрес или закрыт порт | `listen_addresses` (restart), `ss -tlnp \| grep 5432`, межсетевой экран |
| `FATAL: sorry, too many clients already` | исчерпан `max_connections` | раздел 4.1 |
| `WARNING: … MD5 password …` при `CREATE/ALTER ROLE` (18+) | MD5 объявлен устаревшим | перейти на SCRAM; заглушить можно `md5_password_warnings = off` |

---

## 9. Калькуляторы конфигурации и чем их результат отличается от рекомендаций для 1С

### 9.1. PGTune (pgtune.leopard.in.ua)

Формулы взяты из исходного кода проекта (github.com/le0pard/pgtune). Входные данные: версия PostgreSQL, ОС, тип нагрузки (`web`, `oltp`, `dw`, `desktop`, `mixed`), память, число CPU, число соединений, тип накопителя.

| Параметр | Что выдаёт PGTune | Рекомендация для 1С |
|---|---|---|
| `max_connections` | web 200, oltp 300, dw 40, desktop 20, mixed 100 (или введённое вручную) | ≥ 500 |
| `shared_buffers` | RAM/4 (desktop — RAM/16) | RAM/4 — совпадает |
| `effective_cache_size` | 3/4 RAM | RAM − `shared_buffers` — совпадает |
| `maintenance_work_mem` | RAM/16 (dw — RAM/8), верхний предел 8GB | RAM/16..32, до 4GB — близко |
| `autovacuum_work_mem` | 2GB, если `maintenance_work_mem` ≥ 2GB; иначе не выдаётся | 256MB–2GB [практика] |
| `work_mem` | `(RAM − shared_buffers) / ((max_connections + max_worker_processes) × 3)`; для web/oltp — как есть, для dw/mixed — пополам, для desktop — делится на 6; минимум 4MB | 32–256MB — **в разы больше** |
| `min_wal_size` / `max_wal_size` | oltp 2GB / 8GB; web и mixed 1GB / 4GB; dw 4GB / 16GB | 512MB–4GB / вдвое больше — сопоставимо |
| `checkpoint_completion_target` | 0.9 | 0.9 |
| `wal_buffers` | 3 % от `shared_buffers`, не более 16MB | авто — то же |
| `random_page_cost` | 1.1 для SSD/NVMe/SAN, 4 для HDD | 1.1–1.3 — совпадает |
| `effective_io_concurrency` | HDD 2, SSD 200, SAN 300, NVMe 1000 (выдаётся только для Linux) | 100–200 |
| `default_statistics_target` | 100 (dw — 500) | 100 |
| `huge_pages` | `try` при `shared_buffers` ≥ 2GB, иначе `off` | `try`/`on` |
| `max_parallel_workers_per_gather` | CPU/2 (не более 4, кроме dw) | **0** |
| `max_worker_processes`, `max_parallel_workers` | число CPU | так же |
| `jit` | `off` для web/oltp/mixed (12+) | `off` — совпадает |
| `wal_compression` | `lz4` (15+) | `lz4` — совпадает |
| `autovacuum_max_workers` | 4 при ≥ 16 CPU, 5 при ≥ 32 | не меньше 4 всегда |
| `io_method` (18+) | `io_uring` на Linux, `worker` на остальных ОС | `worker`, пока не проверена сборка |
| `io_workers` (18+) | только при `io_method = worker`: `min(32, max(3, CPU/4))`, выдаётся, если больше 3 | 3; по замеру |

Пример: 32 ГБ, 8 CPU, тип `oltp`, 500 соединений → `work_mem = (32 − 8) ГБ / ((500 + 8) × 3) ≈ 16MB`. Для запросов 1С с большими соединениями и временными таблицами это означает сортировки и хеши на диске.

Чего PGTune **не выдаёт вовсе**: `standard_conforming_strings`, `escape_string_warning`, `max_locks_per_transaction`, `synchronous_commit`, `temp_buffers`, `bgwriter_*`, `checkpoint_timeout`, `from_collapse_limit`/`join_collapse_limit`, `autovacuum_naptime` и пороги, `max_files_per_process`, `shared_preload_libraries`. Без первых трёх 1С либо не работает, либо получает ошибки `out of shared memory`.

Вывод: PGTune годится как быстрая проверка блока памяти и WAL; взять его результат целиком для сервера 1С нельзя.

### 9.2. Другие инструменты

| Инструмент | Что это | Применимость к 1С |
|---|---|---|
| `pgpro_tune` с пресетом `1c.tune` | штатная автонастройка Postgres Pro (раздел 3.3) | единственный «калькулятор» от вендора, поддерживаемого 1С; только для Postgres Pro |
| Tantor `pg_configurator` (веб-сервис `tantorlabs.ru/pgconfigurator`, пакет в составе Tantor и открытый проект `github.com/TantorLabs/pg_configurator`) | генератор конфигурации по параметрам системы [Tantor]. По README проекта: `pg_configurator --db-cpu=40 --db-ram=128Gi --db-disk-type=SSD --db-duty=mixed --pg-version=…`; есть также `--replication-enabled`, `--min-conns`, `--max-conns`, `--shared-buffers-part`, `--client-mem-part`, `--maintenance-mem-part`; полный список — `pg_configurator -h` | наличие профиля именно для 1С ⚠ не подтверждено: ни страница документации Tantor SE 1C, ни README его не описывают. Результат сверяйте с разделом 3 так же, как вывод PGTune |
| CYBERTEC PGConfigurator (pgconfigurator.cybertec.at) | веб-калькулятор общего назначения | про 1С не знает; те же оговорки, что и для PGTune (детали формул ⚠ не проверялись) |

---

## 10. Как проверять эффект настроек

### 10.1. Методика

1. Зафиксировать исходное состояние: конфигурацию (`pg_settings`), время контрольных операций в 1С, статистику `pg_stat_*`.
2. Менять **одну группу параметров за раз** (память → WAL → планировщик → ОС).
3. Перед замером обнулить счётчики: `SELECT pg_stat_reset();` (текущая база), `SELECT pg_stat_reset_shared('bgwriter');` (для 17+ также `'checkpointer'`, для 14+ `'wal'`, для 16+ `'io'`), `SELECT pg_stat_statements_reset();`.
4. Нагружать одинаково: одни и те же операции 1С (проведение пачки документов, отчёт за период, закрытие месяца на копии базы) или сценарий нагрузочного теста.
5. Сравнивать не только время, но и побочные показатели: временные файлы, частоту контрольных точек, ожидания блокировок, загрузку CPU и диска (`vmstat 1`, `iostat -x 1`, `pidstat`).

### 10.2. Тест Гилева (TPC-1C)

Популярный в сообществе бесплатный синтетический тест: конфигурация 1С, которая выполняет типовые операции (создание и проведение документов, запись регистров) и выдаёт условный индекс производительности; есть однопоточный и многопоточный режимы. Особенности:

- Результат сильнее всего зависит от скорости одного ядра CPU, энергосбережения, накладных расходов связки «сервер 1С ↔ СУБД» (один хост или сеть) и от `synchronous_commit`. К `shared_buffers`, `work_mem` и настройкам планировщика тест почти нечувствителен.
- Поэтому он хорош для проверки «железа», виртуализации и раздела 7 (энергосбережение, диски) и плох как доказательство правильности `postgresql.conf` для реальной базы.
- Низкий индекс при мощном сервере — почти всегда энергосбережение, медленная синхронная запись или перегруженный хост виртуализации.
- Шкала оценок и ссылка на загрузку — на сайте автора (gilev.ru, раздел про TPC-1C, адрес вида `http://www.gilev.ru/tpc1cgilv/`). ⚠ не подтверждено: страницу не удалось открыть ни при подготовке статьи, ни при рецензии (сайт отдаёт только http и перенаправляет https обратно на http, инструмент чтения этого не допускает), поэтому всё описание теста в этом разделе дано по памяти, а не по первоисточнику.
- ⚠ Шкала по памяти рецензента (так её обычно пересказывают в сообществе; с сайтом автора **не сверено**): индекс меньше 10 — «плохо», 10–15 — «удовлетворительно», 15–35 — «хорошо», 35–60 — «отлично», выше — «превосходно». Используйте только как грубый ориентир; настоящие пороги показывает сама обработка теста в окне результата.
- Тест — это конфигурация (или `dt`-файл) 1С: загружается в отдельную пустую информационную базу, созданную на проверяемой связке «сервер 1С + PostgreSQL». В рабочую базу его не загружают.

Для промышленной оценки используются инструменты 1С: показатель APDEX по ключевым операциям, «1С:Тест-центр» и «Центр управления производительностью» из «1С:Корпоративного инструментального пакета», технологический журнал (событие `DBPOSTGRS`).

### 10.3. pgbench — применим ограниченно

`pgbench` моделирует банковские микротранзакции (TPC-B-подобный сценарий) и ничего не знает о временных таблицах, типе `mchar` и многотабличных соединениях 1С. Им разумно сравнивать только **подсистему фиксации и диски**: влияние `synchronous_commit`, `wal_compression`, параметров ОС, типа виртуального диска.

```bash
sudo -u postgres createdb bench
sudo -u postgres pgbench -i -s 100 bench                       # ~10 млн строк в pgbench_accounts (~1,5 ГБ)
sudo -u postgres pgbench -c 16 -j 4 -T 300 -P 30 bench         # 16 клиентов, 4 потока, 5 минут, отчёт каждые 30 с
sudo -u postgres pgbench -c 16 -j 4 -T 300 -N bench            # без обновления маленьких таблиц (меньше конкуренции за блокировки)
sudo -u postgres pgbench -c 16 -j 4 -T 120 -S bench            # только чтение
sudo -u postgres dropdb bench
```

Правила [PG]: масштаб `-s` не меньше числа клиентов `-c`; длительность — минуты, а не секунды; прогон повторять несколько раз; не запускать `pgbench -i` в базе, где есть таблицы с именами `pgbench_*`. Запускайте на тестовом сервере или в окно обслуживания — тест создаёт реальную нагрузку.

### 10.4. Быстрые тесты диска и таймера

```bash
/usr/lib/postgresql/17/bin/pg_test_fsync -s 5 -f /var/lib/postgresql/17/main/pg_test_fsync.tmp   # операций синхронной записи в секунду
/usr/lib/postgresql/17/bin/pg_test_timing                                                       # стоимость запроса времени (для track_io_timing)
```

Запускать от пользователя `postgres`, файл — на том же томе, где лежит WAL. По результату `pg_test_fsync` также подбирают `commit_delay` (половина времени одного сброса 8 КБ) [PG].

### 10.5. Наблюдение через pg_stat_*

```sql
-- 1. Попадание в кэш, фиксации, взаимоблокировки, временные файлы по базам
SELECT datname,
       round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS hit_pct,
       xact_commit, xact_rollback, deadlocks, temp_files, pg_size_pretty(temp_bytes) AS temp_size
FROM pg_stat_database WHERE datname NOT LIKE 'template%';
-- hit_pct устойчиво ниже 95–99 % на рабочей базе → мало shared_buffers/памяти; рост temp_* → мал work_mem
-- TPS = разность xact_commit за интервал / длину интервала (нужно для решения о commit_delay)

-- 2. Контрольные точки (17+; для ≤ 16 — pg_stat_bgwriter.checkpoints_timed / checkpoints_req)
SELECT num_timed, num_requested, buffers_written FROM pg_stat_checkpointer;
-- num_requested сопоставим с num_timed → увеличить max_wal_size

-- 3. Фоновая запись
SELECT buffers_clean, maxwritten_clean, buffers_alloc FROM pg_stat_bgwriter;
-- быстрый рост maxwritten_clean → поднять bgwriter_lru_maxpages

-- 4. WAL (14+)
SELECT wal_records, wal_fpi, pg_size_pretty(wal_bytes) AS wal_size, wal_buffers_full FROM pg_stat_wal;
-- рост wal_buffers_full → увеличить wal_buffers; большая доля wal_fpi → реже контрольные точки, wal_compression

-- 5. Кто реально пишет и читает (16+)
SELECT backend_type, object, context, reads, writes, extends, fsyncs
FROM pg_stat_io WHERE coalesce(reads, 0) + coalesce(writes, 0) > 0
ORDER BY writes DESC NULLS LAST LIMIT 15;
-- много writes у 'client backend' в контексте normal → серверные процессы сами вытесняют «грязные» буферы

-- 6. Сеансы: активные, ждущие блокировок, зависшие в транзакции
SELECT state, wait_event_type, count(*) FROM pg_stat_activity
WHERE backend_type = 'client backend' GROUP BY 1, 2 ORDER BY 3 DESC;

-- 7. Самые дорогие запросы (pg_stat_statements)
SELECT round(total_exec_time::numeric / 1000, 1) AS total_s, calls, round(mean_exec_time::numeric, 1) AS mean_ms,
       temp_blks_written, left(query, 120) AS query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 15;

-- 8. Autovacuum успевает?
SELECT relname, n_dead_tup, n_live_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables WHERE n_dead_tup > 10000 ORDER BY n_dead_tup DESC LIMIT 15;

-- 9. Память и huge pages
SHOW shared_memory_size; SHOW shared_memory_size_in_huge_pages; SHOW huge_pages_status;   -- последнее — 17+
```

Что смотреть в журнале PostgreSQL: `checkpoints are occurring too frequently` (мал `max_wal_size`), `temporary file: path … size …` (мал `work_mem`), `process … still waiting for … after …` (ожидания блокировок при `log_lock_waits = on`), `out of shared memory` (мал `max_locks_per_transaction`), `automatic vacuum of table …` с большим временем.

```bash
sudo grep -cE 'checkpoints are occurring too frequently' /var/log/postgresql/postgresql-17-main.log
sudo grep -E 'temporary file' /var/log/postgresql/postgresql-17-main.log | tail -n 20
sudo grep -E 'out of shared memory|too many clients|Too many open files' /var/log/postgresql/postgresql-17-main.log | tail
```

### 10.6. Как получить в psql тот же план, что у платформы [1С-6011]

Сравнивать влияние настроек планировщика (`random_page_cost`, `*_collapse_limit`, `work_mem`) на конкретный запрос 1С имеет смысл только в тех же условиях, в каких его выполняет платформа. Текст запроса берут из технологического журнала (событие `DBPOSTGRS`, поле `Sql`), складывают в файл вместе с параметрами сеанса платформы и выполняют из командной строки:

```sql
-- query.sql
SET client_min_messages = error;
SET lc_messages TO 'en_US.UTF-8';
SET enable_mergejoin = off;
SET escape_string_warning = off;       -- для PostgreSQL 19 эту строку убрать
SET cpu_operator_cost = 0.001;
SET client_encoding = 'utf8';
SET lock_timeout = 20000;

EXPLAIN (ANALYZE, VERBOSE, BUFFERS, SETTINGS)
SELECT …;                              -- текст из поля Sql события DBPOSTGRS
```

```bash
# В статье ИТС: psql -U postgres --dbname=DATABASE --file=query.sql > query.sqlplan
# В Debian-раскладке локальный вход под postgres идёт методом peer, поэтому так:
sudo -u postgres psql --dbname=ИМЯ_БАЗЫ --file=/tmp/query.sql > /tmp/query.sqlplan    # файл — там, где его прочтёт пользователь postgres
# либо по TCP с паролем:
psql -h localhost -U postgres --dbname=ИМЯ_БАЗЫ --file=query.sql > query.sqlplan
```

- В статье ИТС используется `EXPLAIN ANALYZE VERBOSE`; опции `BUFFERS` и `SETTINGS` добавлены здесь для удобства (обе есть в PostgreSQL 12+; `SETTINGS` печатает строку `Settings:` с параметрами планировщика, отличными от умолчаний, — по ней видно, что условия совпали с платформенными).
- `EXPLAIN ANALYZE` **реально выполняет** запрос. Для изменяющих запросов оборачивайте в `BEGIN; … ROLLBACK;` и не запускайте на рабочей базе в часы нагрузки.
- Если запрос использует временные таблицы (`tt1`, `tt2`, …), их нужно создать и заполнить в том же файле теми же командами, что и платформа (включая `ANALYZE pg_temp.ttN`), собрав цепочку запросов выше по технологическому журналу; в сборках с патчем 1С эту работу автоматизирует расширение `auto_dump` (см. `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`).
- Данные, вставленные во временную таблицу через `COPY … FROM STDIN`, в журналы не попадают — для таких запросов план снимают через `auto_explain` (раздел 4.14).

---

## Типичные ошибки и подводные камни

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | Сервер БД «съедает» всю память, OOM killer убивает процессы `postgres` или `rphost` | `work_mem` и/или `temp_buffers` взяты по верхней границе при сотнях соединений; на совмещённой ВМ формулы посчитаны от всей памяти | считать от памяти, доступной PostgreSQL; `work_mem` 32–128MB, `temp_buffers` 32–128MB; тяжёлым базам — `ALTER DATABASE … SET work_mem` |
| 2 | Запросы 1С медленные, в журнале масса `temporary file` | `work_mem` оставлен 4MB или взят из PGTune | поднять `work_mem` по разделу 4.2 |
| 3 | `ERROR: out of shared memory`, HINT про `max_locks_per_transaction` | умолчание 64 при сотнях таблиц в транзакции | 256–512 и выше; restart; пересчитать huge pages |
| 4 | База растёт, запросы деградируют, `pg_class`/`pg_attribute` в гигабайтах | autovacuum выключен «чтобы не мешал» или не успевает; долгие транзакции | `autovacuum = on`, `naptime = 20s`, ≥ 4 процессов, снизить `scale_factor`; найти сеансы `idle in transaction` |
| 5 | После сбоя питания база не открывается или в ней «битые» страницы | `fsync = off` или `full_page_writes = off` в продуктиве; кэш записи хоста без защиты | оба параметра `on`; для скорости — `synchronous_commit = off`; восстановление из резервной копии |
| 6 | После аварии «пропал» только что проведённый документ | `synchronous_commit = off` — ожидаемое поведение | принять риск либо включить `on` для конкретной базы |
| 7 | Большой `shared_buffers` (16+ ГБ), высокая системная загрузка CPU, растёт `PageTables` в `/proc/meminfo` | нет huge pages; на Ubuntu 26.04 — ещё и регрессия ядра 7.0 | раздел 7.1, `huge_pages = on` |
| 8 | Сервер не стартует после включения `huge_pages = on`: `could not map anonymous shared memory: Cannot allocate memory` | `vm.nr_hugepages` меньше потребности (изменили `shared_buffers`/`max_connections`) | пересчитать, увеличить резерв; временно `huge_pages = try` |
| 9 | Изменили `postgresql.conf`, сделали reload — значение прежнее | параметр требует перезапуска; или переопределён в `postgresql.auto.conf`, в `conf.d`, на уровне базы/роли | `pg_settings`: `pending_restart`, `source`, `sourcefile`; `ALTER SYSTEM RESET …` |
| 10 | Сервер не запускается после правки конфигурации | опечатка, неизвестный параметр (удалён в новой версии), библиотека из `shared_preload_libraries` отсутствует, `io_method = io_uring` без поддержки в сборке | `journalctl -u postgresql@17-main -n 50`; вернуть копию файла; до перезапуска проверять `pg_file_settings` |
| 11 | После добавления `online_analyze` в `shared_preload_libraries` всё замедлилось, журнал забит сообщениями `ANALYZE` | модуль работает с умолчаниями: `enable = on`, все таблицы, `VERBOSE` | убрать модуль либо явно задать `table_type = 'temporary'`, `verbose = off` и остальные параметры |
| 12 | 1С: ошибки создания базы или запросов с типом `mchar`, обратной косой чертой в строках | ванильный PostgreSQL без патчей; не задано `standard_conforming_strings = off` | сборка с патчем 1С / Postgres Pro; параметры совместимости |
| 13 | Регламентные операции 1С обрываются: `canceling statement due to statement timeout` или соединение закрыто сервером | глобальные `statement_timeout`, `idle_in_transaction_session_timeout`, `idle_session_timeout` | убрать из глобальной конфигурации; таймауты — только на отдельные роли |
| 14 | Раз в несколько минут система «замирает» на секунды | залповый сброс «грязных» страниц ОС или частые контрольные точки по объёму WAL | `vm.dirty_*_bytes`; увеличить `max_wal_size`, `checkpoint_timeout = 15min` |
| 15 | Простые запросы стали медленнее после «включения параллелизма» | `max_parallel_workers_per_gather > 0`: накладные расходы на запуск рабочих процессов и умножение `work_mem` | вернуть 0 |
| 16 | Планы с полным сканированием больших таблиц при наличии индексов | `random_page_cost = 4` на SSD; занижен `effective_cache_size` | 1.1 и RAM − `shared_buffers` |
| 17 | `FATAL: sorry, too many clients already` | `max_connections` мал для пула соединений 1С | ≥ 500; искать причину роста числа соединений |
| 18 | `Too many open files` или постоянное открытие/закрытие файлов | `LimitNOFILE` службы ниже `max_files_per_process` | drop-in с `LimitNOFILE=65536` |
| 19 | Тест Гилева показывает низкий индекс на мощной ВМ | энергосбережение на хосте, переподписка vCPU, медленная синхронная запись | раздел 7.5; `pg_test_fsync`; `synchronous_commit = off` |
| 20 | `temp_tablespaces` задан, а временные файлы всё равно в основном каталоге | табличное пространство не существует или у роли нет права `CREATE` — значение молча игнорируется | `\db+`, `GRANT CREATE ON TABLESPACE … TO …` |
| 21 | После обновления до новой основной версии сервер не стартует | в конфигурации остались удалённые параметры (`stats_temp_directory`, `vacuum_defer_cleanup_age`, `old_snapshot_threshold`, в 19-й — `escape_string_warning`, `io_workers`) | сверить конфигурацию с примечаниями к выпуску перед обновлением |
| 22 | `effective_io_concurrency = 2` «как в инструкции» на NVMe | значение из эпохи HDD ниже умолчания 18-й версии (16) | 100–200 для SSD |
| 23 | На совмещённой ВМ после `vm.overcommit_memory = 2` процессы 1С падают с ошибками выделения памяти | строгий учёт памяти не рассчитан на `rphost` | вернуть 0; параметр — только для выделенного сервера СУБД |
| 24 | В `psql` запрос 1С выполняется быстро (или с другим планом), а в 1С — медленно | платформа задаёт в сеансе `enable_mergejoin = off`, `cpu_operator_cost = 0.001` и др. [1С-6011]; в `psql` действуют умолчания сервера | воспроизводить с параметрами сеанса платформы (раздел 10.6) |
| 25 | В `postgresql.conf` выставлены `enable_mergejoin = off`, `cpu_operator_cost`, `lock_timeout` «для 1С» | эти параметры платформа и так задаёт в своих сеансах; глобальные значения лишь меняют поведение остальных клиентов (`pg_dump`, скрипты обслуживания) | убрать из конфигурации сервера |
| 26 | Создание информационной базы из 1С завершается ошибкой прав, хотя у роли есть `CREATEDB` | по документации платформы на момент создания базы нужна привилегия `SUPERUSER` | `ALTER USER usr1cv8 WITH SUPERUSER;` → создать базу → `ALTER USER usr1cv8 WITH NOSUPERUSER;` |
| 27 | В журнале PostgreSQL повторяется `invalid value for parameter "lc_messages": "en_US.UTF-8"` | на сервере СУБД не сгенерирована локаль `en_US.UTF-8`, которую платформа запрашивает в каждом сеансе | `sudo locale-gen en_US.UTF-8 && sudo systemctl restart postgresql@17-main` (⚠ практика сообщества; проверьте `locale -a`) |
| 28 | `findmnt /var/lib/postgresql` ничего не выводит, параметры монтирования «не видны» | каталог данных не является отдельной точкой монтирования | `findmnt -T /var/lib/postgresql` |
| 29 | В конфигурацию добавлен `commit_delay = 1000` «по инструкции», эффекта нет | при `synchronous_commit = off` параметр игнорируется [PG] | убрать либо использовать только вместе с `synchronous_commit = on` |
| 30 | После копирования конфигурации Postgres Pro на сборку с патчем 1С (или наоборот) сервер не стартует | параметры, которых нет в другой СУБД: `enable_sorted_merge_join`, `enable_parallel_temptables` (Postgres Pro), `enable_temp_memory_catalog`, `enable_temp_rd_buffers` (сборка 1С), `enable_delayed_temp_file` (Tantor) | перед переносом проверить каждое имя: `SELECT name FROM pg_settings WHERE name = '…';` |

---

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Где конфигурация | `sudo -u postgres psql -c "SHOW config_file;" -c "SHOW hba_file;" -c "SHOW data_directory;"` |
| Свой файл настроек | `sudo -u postgres nano /etc/postgresql/17/main/conf.d/90-1c.conf` |
| Что отличается от умолчаний | `SELECT name, setting, unit, source, sourcefile FROM pg_settings WHERE source <> 'default';` |
| Проверить файлы до применения | `SELECT * FROM pg_file_settings WHERE NOT applied OR error IS NOT NULL;` |
| Перечитать конфигурацию | `sudo systemctl reload postgresql@17-main` или `SELECT pg_reload_conf();` |
| Что ждёт перезапуска | `SELECT name FROM pg_settings WHERE pending_restart;` |
| Перезапуск | `sudo systemctl restart postgresql@17-main` |
| Нужен ли параметру перезапуск | `SELECT name, context FROM pg_settings WHERE name = 'shared_buffers';` |
| Изменить параметр из SQL | `ALTER SYSTEM SET work_mem = '64MB'; SELECT pg_reload_conf();` |
| Отменить `ALTER SYSTEM` | `ALTER SYSTEM RESET work_mem;` / `ALTER SYSTEM RESET ALL;` |
| Параметр для одной базы / роли | `ALTER DATABASE buh SET work_mem = '128MB';` / `ALTER ROLE r SET statement_timeout = '10min';` |
| Точечно изменить основной файл | `sudo pg_conftool 17 main set max_connections 500` |
| Расчёт huge pages (сервер остановлен) | `sudo -u postgres /usr/lib/postgresql/17/bin/postgres -D /var/lib/postgresql/17/main -c config_file=/etc/postgresql/17/main/postgresql.conf -C shared_memory_size_in_huge_pages` |
| Зарезервировать huge pages | `echo 'vm.nr_hugepages = N' \| sudo tee /etc/sysctl.d/91-hugepages.conf && sudo sysctl --system` |
| Используются ли huge pages | `SHOW huge_pages_status;` (17+); `grep -i hugepages /proc/meminfo` |
| Состояние THP | `cat /sys/kernel/mm/transparent_hugepage/enabled` |
| Применить sysctl | `sudo sysctl --system` |
| Лимиты процесса PostgreSQL | `sudo cat /proc/$(sudo head -1 /var/lib/postgresql/17/main/postmaster.pid)/limits` |
| Поднять лимит файлов | `sudo systemctl edit postgresql@17-main` → `[Service]` `LimitNOFILE=65536` → restart |
| Проверить `pg_hba.conf` | `SELECT line_number, type, database, user_name, address, auth_method, error FROM pg_hba_file_rules;` |
| Применить `pg_hba.conf` | `sudo systemctl reload postgresql@17-main` |
| Какие методы сжатия WAL / ввода-вывода умеет сборка | `SELECT name, enumvals FROM pg_settings WHERE name IN ('wal_compression', 'io_method');` |
| Есть ли параметры сборки 1С | `SELECT name, setting FROM pg_settings WHERE name LIKE 'enable_temp%';` |
| Есть ли библиотеки расширений | `ls /usr/lib/postgresql/17/lib/ \| grep -E 'plantuner\|online_analyze\|pg_stat_statements'` |
| Временные файлы по базам | `SELECT datname, temp_files, pg_size_pretty(temp_bytes) FROM pg_stat_database;` |
| Частота контрольных точек | `SELECT num_timed, num_requested FROM pg_stat_checkpointer;` (17+) |
| Соединения: всего / активных | `SELECT state, count(*) FROM pg_stat_activity WHERE backend_type = 'client backend' GROUP BY 1;` |
| Сеансы, зависшие в транзакции | `SELECT pid, now() - xact_start, query FROM pg_stat_activity WHERE state LIKE 'idle in transaction%';` |
| Мёртвые строки и автоочистка | `SELECT relname, n_dead_tup, last_autovacuum FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;` |
| Тяжёлые запросы | `SELECT calls, total_exec_time, left(query, 100) FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;` |
| Скорость синхронной записи | `/usr/lib/postgresql/17/bin/pg_test_fsync -f /var/lib/postgresql/17/main/t.tmp` |
| План запроса как у платформы 1С | перед `EXPLAIN`: `SET enable_mergejoin = off; SET cpu_operator_cost = 0.001; SET lock_timeout = 20000;` (полный список — раздел 3.5) |
| Есть ли локали для 1С | `locale -a \| grep -Ei 'en_US\|ru_RU'` |
| Шифруются ли соединения | `SELECT ssl, count(*) FROM pg_stat_ssl GROUP BY 1;` |
| Роль 1С на время создания базы | `ALTER USER usr1cv8 WITH SUPERUSER;` … создать базу … `ALTER USER usr1cv8 WITH NOSUPERUSER;` |
| На каком томе лежат данные | `findmnt -no TARGET,SOURCE,FSTYPE,OPTIONS -T /var/lib/postgresql` |
| Huge pages для PostgreSQL 14 | `sudo pmap $(sudo head -1 /var/lib/postgresql/14/main/postmaster.pid) \| awk '/rw-s/ && /zero/ {print $2}'` → делить на `Hugepagesize` |
| Postgres Pro: пресет для 1С | `/opt/pgpro/1c-17/bin/pgpro_tune --show`; `pgpro_tune -D <каталог_данных> -P 1c.tune` (имя — из вывода `--show`) |
| Почему сервер не стартует | `sudo journalctl -u postgresql@17-main -n 50 --no-pager`; `sudo tail -n 50 /var/log/postgresql/postgresql-17-main.log` |

---

## Источники

Официальные материалы 1С:

- https://its.1c.ru/db/metod8dev/content/5866/hdoc — «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2» (ред. 19.06.2025): все значения с пометкой [1С]. Использован конспект `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md`; при прямом чтении страницы инструментом кириллица не декодировалась, сверены только строки параметров.
- https://its.1c.ru/db/metod8dev/content/5825/hdoc, https://its.1c.ru/db/metod8dev/content/3788/hdoc, https://its.1c.ru/db/metod8dev/content/4650/hdoc, https://its.1c.ru/db/metod8dev/content/1576/hdoc — старые статьи ИТС (2007–2015) о `fsync`, WAL и памяти: исторический контекст, вынос WAL на отдельный диск (по конспекту).
- https://its.1c.ru/db/metod8dev/content/6035/hdoc — `enable_temp_rd_buffers` (25.09.2025; по конспекту).
- https://its.1c.ru/db/metod8dev/content/6031/hdoc, https://its.1c.ru/db/metod8dev/content/6032/hdoc — `auto_dump` и `pg_wait_sampling` в сборках 1С (25.06.2025): строки `shared_preload_libraries`, пример плана с `enable_mergejoin = 'off', cpu_operator_cost = '0.001'`, имя службы `postgresql@16-main`.
- https://its.1c.ru/db/metod8dev/content/6011/hdoc — «Методика расследования проблем производительности на уровне работы СУБД PostgreSQL» (21.02.2023): параметры сеанса, которые задаёт платформа (`enable_mergejoin = off`, `cpu_operator_cost = 0.001`, `lock_timeout = 20000`, `escape_string_warning = off`, `lc_messages`, `client_min_messages`, `client_encoding`), явный `ANALYZE` временных таблиц в цепочке запросов платформы. Использован конспект `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md` (раздел 4); при рецензии страница напрямую не читалась (нужна подписка).
- Документация платформы «Руководство администратора», создание информационной базы на PostgreSQL — привилегия `SUPERUSER` на момент создания базы (по конспекту `kb/its-docs/adm-gl05-spisok-infobaz.md`).
- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/subd-postgresql/ — поддерживаемые сборки и версии, список ОС.

Postgres Professional:

- https://postgrespro.ru/docs/postgrespro/17/config-one-c и подстраницы `one-c-configuring-locale`, `one-c-basic-server-requirements`, `one-c-configuring-server`, `one-c-additional-modules` (то же для версии 18) — все значения с пометкой [PGPro].
- https://postgrespro.ru/docs/postgrespro/17/app-pgpro-tune, https://postgrespro.ru/docs/postgrespro/17/app-initdb — `pgpro_tune`, пресеты, опции `--tune`/`--no-tune`.
- https://postgrespro.ru/docs/postgrespro/17/online-analyze, https://postgrespro.ru/docs/postgrespro/17/plantuner, https://postgrespro.ru/docs/postgrespro/17/fasttrun — параметры модулей и их умолчания.
- https://postgrespro.ru/docs/postgrespro/17/runtime-config-query — параметры `enable_*`, специфичные для Postgres Pro.
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux (сверены также версии 15 и 18) — пути, пакеты, служба; синтаксис `pg-setup initdb [параметры_initdb]`, формы `--tune=1c` в документации нет.
- https://repo.postgrespro.ru/1c/ — каталоги репозитория сборок для 1С: `1c-14` … `1c-18`; https://1c.postgres.ru/ — страница загрузки (команд установки не содержит).
- При рецензии 10.10.2026 напрямую прочитаны и сверены страницы `one-c-configuring-server` (17 и 18), `one-c-additional-modules`, `one-c-basic-server-requirements`, `one-c-configuring-locale`, `app-pgpro-tune` (17 и 18), `app-initdb`, `online-analyze`, `plantuner`, `runtime-config-query`: все значения [PGPro] в статье совпали с документацией.

PostgreSQL (postgresql.org):

- https://www.postgresql.org/docs/release/ — актуальные минорные версии; статус PostgreSQL 19 (Beta 4).
- https://www.postgresql.org/docs/18/runtime-config-resource.html, `runtime-config-wal.html`, `runtime-config-vacuum.html`, `runtime-config-query.html`, `runtime-config-connection.html`, `runtime-config-client.html`, `runtime-config-locks.html`, `runtime-config-logging.html`, `runtime-config-statistics.html`, `runtime-config-compatible.html`, `runtime-config-preset.html` — умолчания, контексты и описания параметров.
- https://www.postgresql.org/docs/18/config-setting.html, `view-pg-settings.html`, `view-pg-file-settings.html` — файлы конфигурации, приоритеты, представления.
- https://www.postgresql.org/docs/18/kernel-resources.html — huge pages, overcommit, OOM, лимиты.
- https://www.postgresql.org/docs/18/wal-configuration.html — контрольные точки, `commit_delay`, `pg_test_fsync`.
- https://www.postgresql.org/docs/18/wal-async-commit.html — асинхронная фиксация: окно потерь `3 × wal_writer_delay`, «потеря данных, но не повреждение», `commit_delay` игнорируется при асинхронной фиксации, принудительно синхронные команды.
- https://www.postgresql.org/docs/18/app-postgres.html — ключи `-C` (вычисляемые параметры требуют остановленного сервера) и `-c`.
- https://www.postgresql.org/docs/14/kernel-resources.html — расчёт huge pages для версии 14 (через `pmap`).
- https://www.postgresql.org/docs/18/auth-pg-hba-conf.html, `auth-password.html` — формат `pg_hba.conf`, методы, переход на SCRAM.
- https://www.postgresql.org/docs/18/pgstatstatements.html, `auto-explain.html`, `pgbench.html`, `monitoring-stats.html` — модули и представления статистики.
- https://www.postgresql.org/docs/15/release-15.html, `16/release-16.html`, `17/release-17.html`, `18/release-18.html`, `19/release-19.html`, `19/runtime-config-compatible.html`, `19/runtime-config-resource.html` — изменения по версиям, включая `standard_conforming_strings` в 19-й.
- https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server — общие принципы (страница 2021 года).

Ubuntu и прочее:

- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ и `changes-since-previous-interim/` — ядро 7.0, PostgreSQL 18; известная проблема с производительностью PostgreSQL на Linux 7.0 и рекомендация huge pages описаны на странице `changes-since-previous-interim/` (там же ссылки на обсуждение в lore.kernel.org); страница `26.04/1/` (изменения 26.04.1) исправления не упоминает.
- https://ubuntu.com/server/docs/how-to/databases/install-postgresql/ — расположение файлов, методы аутентификации по умолчанию (`peer` для `local`, `scram-sha-256` для `host`), SSL включён по умолчанию с сертификатом из пакета `ssl-cert`.
- https://salsa.debian.org/postgresql/postgresql-common (файлы `pg_createcluster`, `createcluster.conf`) — что `pg_createcluster` записывает в конфигурацию нового кластера: `ssl = on` и сертификат snakeoil, `add_include_dir = 'conf.d'`, `cluster_name`, `log_line_prefix`, `stats_temp_directory` только до 14-й версии.
- https://docs.tantorlabs.ru/tdb/ru/17_5/se1c/ (`runtime-config-resource.html`, `runtime-config-query.html`, `improvements-1c.html`, `online_analyze.html`, `plantuner.html`, `pg_configurator.html`) — параметры Tantor SE 1C.
- https://github.com/le0pard/pgtune (файл `src/features/configuration/configurationSlice.js`) — формулы PGTune (при рецензии 10.10.2026 сверены с исходным кодом заново: `work_mem`, `io_method`, `io_workers`, `autovacuum_*`, `wal_compression`, `jit`).
- https://github.com/TantorLabs/pg_configurator — README открытой версии `pg_configurator` (примеры опций командной строки).
- `kb/linux/09-tyuning-yadra-lokali-vremya-bezopasnost.md`, `kb/postgresql/03-administrirovanie-psql-i-utility.md`, `kb/its-docs/adm-gl05-spisok-infobaz.md` — смежные статьи этой базы знаний (sysctl и THP, раскладки и утилиты, права роли 1С).

Не удалось открыть ни при подготовке, ни при рецензии (10.10.2026):

- сайт gilev.ru (тест TPC-1C) — перенаправление https → http, которое инструмент чтения не проходит;
- страницы its.1c.ru (5866, 6011, 6035 и др.) — без подписки отдаётся только оболочка страницы; все значения [1С] и [1С-6011] опираются на конспекты этой базы знаний;
- описание сборок на releases.1c.ru (с чем собран PostgreSQL 18.x-1.1C: `liburing`, `lz4`, `zstd`) — требуется авторизация;
- файл конфигурации ядра Ubuntu (умолчание THP) и unit-файл `postgresql@.service` в репозитории `postgresql-common`;
- документация Postgres Pro не содержит отдельной страницы утилиты `pg-setup`; точные значения её аргумента `tune` не документированы.

Поиск по интернету при подготовке и при рецензии был недоступен (исчерпан лимит запросов), поэтому статьи сообщества (Infostart, Habr, Mista) напрямую не сверялись — пункты с пометкой [практика] основаны на общеизвестной практике и расчётах автора, а числовые значения из них помечены в тексте «⚠».

### Что осталось неподтверждённым (сводка пометок «⚠»)

| Утверждение | Где в статье | Как проверить на месте |
|---|---|---|
| Форма `pg-setup initdb --tune=1c`; можно ли писать `-P 1c` без `.tune`; что именно ставит `1c.tune` | 3.3 | `pgpro_tune --show`; прочитать файл `1c.tune`; сравнить `pg_settings` до и после |
| Сборка 18.x-1.1C: поддержка `io_uring`, `lz4`, `zstd` | 4.4, 5.2 | `SELECT name, enumvals FROM pg_settings WHERE name IN ('io_method','wal_compression');` |
| Сервер 19-й версии не стартует со строками совместимости 1С; несовместимость нынешней платформы с PostgreSQL 19 | 4.10, 5.3 | только на стенде с бета-версией; ждать объявления 1С |
| С какой версии платформа сама выполняет `ANALYZE` временных таблиц (в сообществе называют 8.3.13) | 4.14 | технологический журнал: команды `ANALYZE pg_temp.tt…` |
| Нужен ли перезапуск для `enable_temp_rd_buffers`; относится ли «с 16.4» у `enable_temp_memory_catalog` только к сборке 1С | 4.12 | `SELECT name, context FROM pg_settings WHERE name LIKE 'enable_temp%';` |
| К какой служебной базе подключается платформа при создании информационной базы | 8.2 | журнал PostgreSQL при `log_connections = on` в момент создания тестовой базы |
| Обязательность локали `en_US.UTF-8` на сервере СУБД | 3.5 | `locale -a`; журнал PostgreSQL на ошибки `lc_messages` |
| Умолчание THP в Ubuntu (`madvise`) | 7.2 | `cat /sys/kernel/mm/transparent_hugepage/enabled` |
| Шкала теста Гилева | 10.2 | окно результата самой обработки теста |
| Профиль 1С в Tantor `pg_configurator`; формулы CYBERTEC PGConfigurator | 9.2 | `pg_configurator -h`; сайт сервиса |
| Числа практики сообщества: `geqo_threshold` 16–20, `default_statistics_target` 300–1000, параллелизм под отчёты, `swappiness`, `vm.dirty_*`, отношение к гиперпоточности | 3.4, 4.7, 7.3, 7.5 | замер на стенде (раздел 10) |
| Все числа готовых блоков 8–128 ГБ, кроме формул [1С]/[PGPro] | 6 | замер на стенде; huge pages — командой из 7.1 |
