# Администрирование PostgreSQL для 1С: psql, служебные утилиты, роли и базы, каталоги, журналы

> **Официальные тексты по теме** (конспекты документации ИТС 8.3.27 и методических статей ИТС, составлены по полным текстам): `../its-metod/razmeshchenie-dannyh-i-indeksy.md`, `../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`. Статья писалась до получения доступа к закрытой документации: там, где ниже сказано «документация закрыта», «не прочитано» или стоит ⚠, сверяйтесь с этими конспектами — при расхождении правы они.

> Область: повседневное администрирование сервера PostgreSQL под «1С:Предприятие 8» на Ubuntu Server — клиент `psql`, управление службой, обёртки `postgresql-common`, «родные» утилиты (`pg_ctl`, `initdb`, `pg_controldata` и др.), `pg-setup`/`pg-wrapper` сборок Postgres Pro, роли, базы, права, табличные пространства, настройка «на лету», сеансы, размеры, журналы, перенос каталога данных, расширения, шпаргалка SQL, особенности баз 1С | Версии: PostgreSQL 14–18 (документация сверена по версии 18.6), Ubuntu Server 22.04 / 24.04 / 26.04 LTS, сборки «PostgreSQL с патчем от 1С», «Postgres Pro 1С» (`postgrespro-1c-NN`), Postgres Pro Standard | Актуальность: 2026-10-10 | Фактчек рецензентом: 2026-10-10 (что проверено и что осталось открытым — в разделе «Что не удалось подтвердить»)

Условные обозначения:

- `NN` — старший номер версии PostgreSQL (14, 15, 16, 17, 18). В примерах чаще всего `16` или `17` — подставляйте свой.
- «Debian-раскладка» — пакеты, использующие `postgresql-common`: штатный `postgresql` из архива Ubuntu, пакеты PGDG (apt.postgresql.org) и deb-пакеты «PostgreSQL с патчем от 1С».
- «Раскладка Postgres Pro» — пакеты `postgrespro-1c-NN`, `postgrespro-std-NN` и т.п., всё лежит в `/opt/pgpro/...` и `/var/lib/pgpro/...`.
- «⚠ не подтверждено» — первоисточник прочитать не удалось, утверждение основано на практике сообщества или памяти автора. Перед применением проверьте на стенде указанной рядом командой.
- «Официально» — документация PostgreSQL (postgresql.org/docs), man-страницы Ubuntu, документация Postgres Pro, сайт 1С. «Практика» — приёмы сообщества.
- В таблицах вертикальная черта внутри команд записана как `\|` — этого требует разметка Markdown. В командной строке и в psql вводите просто `|`.

## Кратко — главные факты и команды

1. Локальный вход администратора — через peer-аутентификацию по Unix-сокету: `sudo -u postgres psql`. Пароль не нужен: сервер сверяет имя пользователя ОС с именем роли. `psql -U postgres` от другого пользователя ОС даст `Peer authentication failed`.
2. Вход по сети или по паролю: `psql -h 127.0.0.1 -p 5432 -U postgres -d postgres` или URI `psql "postgresql://postgres@127.0.0.1:5432/postgres"`. Пароль для скриптов — в `~/.pgpass` (строка `хост:порт:база:роль:пароль`, права строго `chmod 0600`, иначе файл игнорируется — libpq выводит лишь предупреждение и спрашивает пароль).
3. Где что лежит, сервер сообщает сам: `SHOW data_directory; SHOW config_file; SHOW hba_file; SHOW ident_file; SHOW unix_socket_directories; SHOW port;`.
4. Debian-раскладка: данные `/var/lib/postgresql/NN/main`, конфигурация `/etc/postgresql/NN/main/` (`postgresql.conf`, `pg_hba.conf`, `pg_ident.conf`, `conf.d/`), журнал `/var/log/postgresql/postgresql-NN-main.log`, сокет `/var/run/postgresql`, бинарники `/usr/lib/postgresql/NN/bin`.
5. Раскладка Postgres Pro: бинарники `/opt/pgpro/1c-NN/bin`, данные и конфигурация вместе в `/var/lib/pgpro/1c-NN/data`, служба `postgrespro-1c-NN` (для Standard — `std-NN`). Для `std-NN` всё документировано; для `1c-NN` официально подтверждён каталог программ `/opt/pgpro/1c-17/bin` (инструкция в `meta.json` репозитория), а каталог данных, имя службы и файл в `/etc/default` следуют тому же шаблону (см. 2.3, там же команды проверки).
6. Служба в Debian-раскладке: один кластер = один юнит `postgresql@NN-main.service`. Юнит `postgresql.service` — только «зонтик», его статус `active (exited)` ничего не говорит о работе сервера. Смотреть нужно `systemctl status postgresql@NN-main` или `pg_lsclusters`.
7. Обёртки Debian: `pg_lsclusters`, `pg_ctlcluster NN main start|stop|restart|reload|status|promote`, `pg_createcluster --locale ru_RU.UTF-8 -p порт -d каталог --start NN имя`, `pg_dropcluster --stop NN имя`, `pg_renamecluster`, `pg_conftool`, `pg_upgradecluster`.
8. «Родной» `pg_ctl`: `pg_ctl -D <каталог> start|stop|restart|reload|status|promote`. Режимы остановки `-m smart|fast|immediate`, по умолчанию `fast`. `immediate` — аварийный, при следующем старте будет восстановление по WAL.
9. Перечитать конфигурацию без перезапуска: `SELECT pg_reload_conf();` или `systemctl reload postgresql@NN-main`. Параметры с `context = postmaster` в `pg_settings` требуют перезапуска; ждущие перезапуска видны запросом `SELECT name FROM pg_settings WHERE pending_restart;`.
10. `ALTER SYSTEM SET параметр = значение;` пишет в `postgresql.auto.conf` в каталоге данных; этот файл перекрывает `postgresql.conf`. Отмена: `ALTER SYSTEM RESET параметр;`.
11. Перед `reload` проверяйте файлы: `SELECT * FROM pg_file_settings WHERE error IS NOT NULL;` и `SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;`. Столбцы `rule_number` и `file_name` в `pg_hba_file_rules` есть только с PostgreSQL 16 — в 14 и 15 запросы с ними завершатся ошибкой.
12. Кто подключён и что делает: `SELECT pid, usename, datname, state, query FROM pg_stat_activity;`. Отменить запрос — `pg_cancel_backend(pid)`, разорвать сеанс — `pg_terminate_backend(pid)`.
13. Удалить базу с активными сеансами: `DROP DATABASE имя WITH (FORCE);` (PostgreSQL 13+) или `dropdb -f имя`. Для базы 1С сначала запретите сеансы в кластере 1С, иначе `rphost` тут же подключится снова.
14. Размеры: `SELECT pg_size_pretty(pg_database_size('имя'));`, `pg_total_relation_size('таблица')` (таблица + индексы + TOAST), `pg_relation_size`, `pg_indexes_size`. В psql — `\l+`, `\dt+`, `\di+`.
15. Журнал сервера: в Debian-раскладке `logging_collector` выключен, stderr пишется в `/var/log/postgresql/postgresql-NN-main.log`, ротация — `logrotate`. При включённом сборщике имя текущего файла даёт `SELECT pg_current_logfile();`.
16. Неинтерактивный запуск: `psql -X -At -v ON_ERROR_STOP=1 -c "SQL"` или `-f файл.sql`. Коды возврата psql: 0 — успех, 1 — фатальная ошибка psql, 2 — нет соединения, 3 — ошибка в скрипте при `ON_ERROR_STOP`.
17. CSV: `psql --csv -c "SELECT ..." > out.csv` или `\copy (SELECT ...) TO 'out.csv' WITH (FORMAT csv, HEADER)`.
18. Актуальные версии на 2026-10-10: PostgreSQL 18.6, 17.11, 16.15, 15.19, 14.24 (выпуск 13 августа 2026). PostgreSQL 14 снимается с поддержки 12 ноября 2026. PostgreSQL 19 — в стадии Beta 4 (24 сентября 2026), финального выпуска нет.
19. 1С работает только со сборками PostgreSQL, содержащими доработки для 1С (типы `mchar`/`mvarchar`, `fulleq`, `fasttrun` и др.). «Ванильный» `postgresql` из архива Ubuntu для баз 1С не подходит.
20. Данные базы 1С напрямую править нельзя: структура таблиц (`_Reference…`, `_Document…`, `_InfoRg…`, `_AccumRg…`, `Config`, `Params`, `v8users`) — внутренняя, целостность обеспечивает только платформа. Официальная позиция 1С (статьи ИТС о размещении данных): сведения о таблицах даются только для понимания, изменять базу допустимо только средствами «1С:Предприятия». Запросы на чтение технически возможны, но аккуратно: в отдельной роли, с тайм-аутами и лучше на копии.
21. Таблицы 1С лежат в схеме `public`; начиная с платформы 8.5.4 схему можно задать другую (поле «Схема БД» в свойствах информационной базы, параметр `--db-schema`) — тогда в запросах и в `\dt` указывайте схему явно: `\dt myschema.*`.

## 1. Версии и сборки на октябрь 2026

### 1.1. PostgreSQL (официально, postgresql.org)

| Ветка | Текущий выпуск | Первый выпуск | Конец поддержки |
|---|---|---|---|
| 18 | 18.6 | 25 сентября 2025 | 14 ноября 2030 |
| 17 | 17.11 | 26 сентября 2024 | 8 ноября 2029 |
| 16 | 16.15 | 14 сентября 2023 | 9 ноября 2028 |
| 15 | 15.19 | 13 октября 2022 | 11 ноября 2027 |
| 14 | 14.24 | 30 сентября 2021 | 12 ноября 2026 |
| 13 | 13.23 | 24 сентября 2020 | не поддерживается с 13 ноября 2025 |

PostgreSQL 19 на 2026-10-10 не выпущен: на главной странице postgresql.org последняя новость о нём — Beta 4 от 24 сентября 2026.

### 1.2. Что стоит в Ubuntu «из коробки» (packages.ubuntu.com)

| Ubuntu | Пакет `postgresql` | Версия PostgreSQL |
|---|---|---|
| 22.04 LTS (jammy) | 14+238 | 14 |
| 24.04 LTS (noble) | 16+257build1.1 | 16 |
| 25.10 (questing) | 17+282ubuntu1 | 17 |
| 26.04 LTS (resolute) | 18+290ubuntu1 | 18 |
| 26.10 (stonking) | 18+293ubuntu1 | 18 |

Версии пакета сверены по packages.ubuntu.com 2026-10-10 (для noble показана версия из `noble-updates`; в основном архиве noble — `16+257build1`).

Штатный пакет Ubuntu — без доработок 1С. Для баз 1С он не годится, но его клиент (`postgresql-client`) и документация по раскладке применимы.

### 1.3. Сборки, поддерживаемые 1С (v8.1c.ru, список на 2026-10-10)

| Сборка | Версии (x86-64) |
|---|---|
| PostgreSQL с патчем от 1С | 18.4-1.1C, 17.10-2.1C, 16.14-1.1C, 15.18-1.1C, 14.23-1.1C |
| Postgres Pro 1С | 18.4, 17.10, 16.14, 15.18, 14.23 |
| Postgres Pro Standard / Enterprise (и сертифицированные) | 18.4.1, 17.10.1, 16.14.1, 15.18.1, 14.23.1 |
| Tantor SE 1C | 18.3.1, 17.10.1, 16.14.0, 15.18.0, 14.23.0 |

- «PostgreSQL с патчем от 1С» поддерживается на Ubuntu 20.04, 22.04, 24.04, 26.04 (таблица ОС на v8.1c.ru).
- Репозиторий «Postgres Pro 1С» (`repo.postgrespro.ru/1c/`) содержит ветки `1c-14` … `1c-18`; для ветки 17 собраны пакеты под Ubuntu 22.04, 24.04, 25.10, 26.04 (версия 17.10).
- Список на v8.1c.ru — это версии, протестированные фирмой «1С»; он отстаёт от апстрима (на 2026-10-10 в списке 18.4 / 17.10, а текущие выпуски PostgreSQL — 18.6 / 17.11). В списке есть и другие СУБД на базе PostgreSQL: Tantor Certified для 1С, Pangolin, Jatoba, Nexign NORD для 1С, Arenadata Prosperity для 1С.
- Минимальная версия платформы (официально: «Список изменений» платформы 8.5.4.1306, раздел о поддержке СУБД; сама страница требований версии СУБД к версиям платформы не привязывает):
  - Postgres Pro 13, 14, 15 (текущие минорные выпуски) — поддержка «начиная с версии 1С:Предприятие 8.3.18»;
  - Postgres Pro 16 и 17 — начиная с 8.3.22;
  - Postgres Pro 18 — начиная с 8.3.27;
  - PostgreSQL 18 (x86-64, сборка с патчем от 1С) — добавлен в 8.3.27 (изменения после публикации версии);
  - в 8.5.1 прекращена поддержка PostgreSQL до версии 9.6 включительно.
- ⚠ не подтверждено: с какой версии платформы поддерживается именно сборка «PostgreSQL с патчем от 1С» версий 16 и 17 — в прочитанных фрагментах «Списка изменений» запись найдена только для Postgres Pro. Подробнее о совместимости — `kb/postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`.

### 1.4. Чем сборки отличаются для администратора

| Признак | Debian-раскладка (Ubuntu, PGDG, «PostgreSQL с патчем от 1С») | Раскладка Postgres Pro (`postgrespro-1c-NN`, `-std-NN`) |
|---|---|---|
| Управление кластерами | `postgresql-common`: `pg_lsclusters`, `pg_ctlcluster`, `pg_createcluster` | `pg-setup`, `systemctl`, «родной» `pg_ctl` |
| Служба | `postgresql@NN-main.service` (+ «зонтик» `postgresql.service`) | `postgrespro-1c-NN.service` |
| Конфигурация | отдельно от данных, в `/etc/postgresql/NN/main` | в каталоге данных |
| Несколько версий рядом | да, штатно | да, каждая в своём `/opt/pgpro/<редакция>-NN` |
| Клиентские программы в `PATH` | `/usr/bin/psql` — ссылка на `pg_wrapper` | после `pg-wrapper links update` |

Раскладка deb-пакетов «PostgreSQL с патчем от 1С» подтверждена частично. Официальный Dockerfile фирмы «1С» (`1C-Company/docker_fresh`, образ `images/db`) ставит пакеты из архива `postgresql_*.tar.bz2` командой `apt-get install -y --allow-downgrades /tmp/pgsql/*.deb` и добавляет в `PATH` каталог `/usr/lib/postgresql/${VERSION}/bin` — то есть программы лежат по дебиановской схеме «каталог на версию». ⚠ не подтверждено чтением самого пакета: зависимость от `postgresql-common` и автоматическое создание кластера `NN/main` в `/etc/postgresql/NN/main` (в том Dockerfile кластер создаётся вручную в `PGDATA=/var/lib/postgresql/data`). Это следует из старой инструкции 1С по сборке (в зависимостях названа `postgresql-common`) и из практики. Проверка на своём сервере: `dpkg -s postgresql-NN | grep -i depends`, `dpkg -L postgresql-NN | head`, `pg_lsclusters`.

## 2. Раскладка каталогов и файлов

### 2.1. Как узнать раскладку на работающем сервере

```sql
SHOW data_directory;            -- каталог данных (PGDATA)
SHOW config_file;               -- путь к postgresql.conf
SHOW hba_file;                  -- путь к pg_hba.conf
SHOW ident_file;                -- путь к pg_ident.conf
SHOW unix_socket_directories;   -- каталог(и) Unix-сокета
SHOW port;                      -- порт
SHOW external_pid_file;         -- дополнительный PID-файл
SHOW log_directory;             -- каталог журналов (при logging_collector = on)
SELECT pg_current_logfile();    -- текущий файл журнала сборщика (NULL, если сборщик выключен)
```

Одним запросом, с указанием, откуда взято значение:

```sql
SELECT name, setting, source, sourcefile, sourceline
FROM pg_settings
WHERE name IN ('data_directory','config_file','hba_file','ident_file',
               'unix_socket_directories','port','log_directory','log_filename',
               'logging_collector','external_pid_file','cluster_name')
ORDER BY name;
```

Если сервер не запущен:

```bash
pg_lsclusters                                        # Debian-раскладка: версия, кластер, порт, статус, каталог данных, журнал
systemctl cat postgresql@16-main                     # что именно запускает systemd
systemctl cat postgrespro-1c-17                      # то же для Postgres Pro
sudo -u postgres /usr/lib/postgresql/16/bin/postgres -D /etc/postgresql/16/main -C data_directory
/usr/lib/postgresql/16/bin/pg_config --bindir --sharedir --pkglibdir --sysconfdir   # каталоги установки; файл входит в postgresql-client-16 (см. 7.4)
dpkg -L postgrespro-1c-17-server | grep -E 'bin/|\.service'   # какие файлы поставил пакет
```

`postgres -C параметр` печатает значение параметра и завершается, сервер при этом не запускается.

### 2.2. Debian-раскладка (официально: man `pg_createcluster`, `pg_ctlcluster`, документация Ubuntu Server)

| Что | Путь |
|---|---|
| Каталог данных | `/var/lib/postgresql/NN/main` |
| Каталог конфигурации | `/etc/postgresql/NN/main/` |
| Основной файл | `/etc/postgresql/NN/main/postgresql.conf` |
| Аутентификация | `/etc/postgresql/NN/main/pg_hba.conf` |
| Сопоставление имён | `/etc/postgresql/NN/main/pg_ident.conf` |
| Дополнительные настройки | `/etc/postgresql/NN/main/conf.d/*.conf` (подключается директивой `include_dir 'conf.d'`) |
| Режим автозапуска | `/etc/postgresql/NN/main/start.conf` (`auto`, `manual`, `disabled`) |
| Опции `pg_ctl` | `/etc/postgresql/NN/main/pg_ctl.conf` |
| Переменные окружения сервера | `/etc/postgresql/NN/main/environment` |
| Настройки `ALTER SYSTEM` | `/var/lib/postgresql/NN/main/postgresql.auto.conf` |
| Журнал сервера | `/var/log/postgresql/postgresql-NN-main.log` — режим `0640`, владелец — владелец кластера (`postgres`), группа `adm`; сам каталог `/var/log/postgresql` — `root:postgres`, режим `1775` (исходный код `pg_createcluster`, `pg_ctlcluster` и `postinst` пакета) |
| Каталог сокета | `/var/run/postgresql/` (файл `.s.PGSQL.5432`) — для кластеров пользователя `postgres`; каталог `postgres:postgres`, режим `2775`. Это умолчание задаёт патч Debian `51-default-sockets-in-var.patch` (в «ванильной» сборке — `/tmp`) |
| Серверные бинарники | `/usr/lib/postgresql/NN/bin/` — пакет `postgresql-NN`: `postgres`, `pg_ctl`, `initdb`, `pg_controldata`, `pg_resetwal`, `pg_checksums`, `pg_waldump`, `pg_upgrade`, `pg_rewind`, `pg_archivecleanup`, `pg_test_fsync`, `pg_test_timing`, `pgbench`, `oid2name`, `vacuumlo` (в 18 ещё `pg_createsubscriber`, `pg_walsummary`) |
| Клиентские бинарники | там же, `/usr/lib/postgresql/NN/bin/` — пакет `postgresql-client-NN`: `psql`, `pg_dump`, `pg_dumpall`, `pg_restore`, `pg_basebackup`, `pg_receivewal`, `pg_recvlogical`, `pg_isready`, `pg_amcheck`, `pg_verifybackup`, `pg_config`, `createdb`, `dropdb`, `createuser`, `dropuser`, `clusterdb`, `reindexdb`, `vacuumdb` |
| Клиентские программы в `PATH` | `/usr/bin/psql`, `/usr/bin/pg_dump`, `/usr/bin/createdb` … — ссылки на `pg_wrapper` |
| Файлы расширений | `/usr/share/postgresql/NN/extension/` (`.control`, `.sql`), библиотеки `/usr/lib/postgresql/NN/lib/` |
| Общие настройки обёрток | `/etc/postgresql-common/` (`createcluster.conf`, `user_clusters`, `pg_upgradecluster.d/`) |
| Домашний каталог `postgres` | `/var/lib/postgresql` (там же `~/.pgpass`, `~/.psqlrc`, `~/.psql_history`) |
| Ротация журнала | `/etc/logrotate.d/postgresql-common` |

Имя кластера по умолчанию — `main`. Шаблон путей: `/etc/postgresql/<версия>/<кластер>/`, `/var/lib/postgresql/<версия>/<кластер>`, `/var/log/postgresql/postgresql-<версия>-<кластер>.log`.

В `createcluster.conf` заданы умолчания для новых кластеров: `create_main_cluster = true` (при установке пакета `postgresql-NN`, если кластеров нет, создаётся `main`), `start_conf = 'auto'`, `data_directory = '/var/lib/postgresql/%v/%c'`, `ssl = on` (с «snakeoil»-сертификатом пакета `ssl-cert`), `cluster_name = '%v/%c'`, `add_include_dir = 'conf.d'`, а также свой `log_line_prefix`. Эталон файла лежит в `/usr/share/postgresql-common/createcluster.conf`, рабочая копия `/etc/postgresql-common/createcluster.conf` создаётся при установке пакета (через `ucf`); дополнительные файлы настроек — в `/etc/postgresql-common/createcluster.d/`. Практическое применение для 1С: до установки серверного пакета можно задать там `initdb_options = '--locale=ru_RU.UTF-8'`, чтобы кластер `main` сразу создался с русской локалью (параметр `initdb_options` есть в исходном коде `pg_createcluster` и в эталонном файле, по умолчанию пуст; сам приём — практика, обычный путь — `pg_dropcluster` + `pg_createcluster --locale`, см. 6.2).

Тот же `postinst` создаёт системного пользователя `postgres` с домашним каталогом `/var/lib/postgresql` и оболочкой `/bin/bash`.

### 2.3. Раскладка Postgres Pro (официально для `std-NN`: документация Postgres Pro; для `1c-NN` — каталог программ подтверждён, остальное по тому же шаблону)

| Что | Postgres Pro Standard 17 (документировано) | Postgres Pro 1С 17 |
|---|---|---|
| Каталог установки | `/opt/pgpro/std-17` | `/opt/pgpro/1c-17` (официально: `meta.json` репозитория) |
| Бинарники | `/opt/pgpro/std-17/bin` | `/opt/pgpro/1c-17/bin` (официально: там лежит `pg-setup`) |
| Каталог данных по умолчанию | `/var/lib/pgpro/std-17/data` | `/var/lib/pgpro/1c-17/data` (по шаблону) |
| Конфигурация | в каталоге данных: `postgresql.conf`, `pg_hba.conf`, `pg_ident.conf`, `postgresql.auto.conf` | то же |
| Служба systemd | `postgrespro-std-17` | `postgrespro-1c-17` (по шаблону) |
| Файл юнита | `/lib/systemd/system/postgrespro-std-17.service`; в Debian, Ubuntu и Альт есть ещё сценарий `/etc/init.d/postgrespro-std-17` | `/lib/systemd/system/postgrespro-1c-17.service` (по шаблону) |
| Файл с путём к данным | `/etc/default/postgrespro-std-17` (на странице `pg-setup` тот же файл назван `/etc/default/postgrespro-standard-17` — по-видимому, неточность документации). В этом же файле, по документации, меняют `PG_OOM_ADJUST_VALUE` для дочерних процессов postmaster — значит, это файл вида «ПЕРЕМЕННАЯ=значение» | `/etc/default/postgrespro-1c-17` (по шаблону) |
| Владелец процессов | `postgres` | `postgres` |
| Пакеты | `postgrespro-std-17`, `-server`, `-client`, `-libs`, `-contrib` | `postgrespro-1c-17`, `-server`, `-client`, `-libs`, `-contrib`, `-dev`, `-docs`, `-docs-ru`, `-jit`, `-plperl`, `-plpython3`, `-pltcl` |
| Файл репозитория apt | — | `/etc/apt/sources.list.d/postgresql-1c-17.list` (создаёт `pgpro-repo-add.sh`) |

- Имена пакетов `postgrespro-1c-17*` и версия 17.10 подтверждены индексом репозитория (`Packages` для noble). Метапакет `postgrespro-1c-17` зависит от `-client`, `-server`, `-contrib`, создаёт базу с параметрами по умолчанию, включает автозапуск и кладёт клиентские утилиты в `PATH`.
- Подтверждено официально (файл `meta.json` в `repo.postgrespro.ru/1c/1c-17/`): для установки рядом с уже имеющимся PostgreSQL ставят `postgrespro-1c-17-contrib` и выполняют `/opt/pgpro/1c-17/bin/pg-setup initdb`, `/opt/pgpro/1c-17/bin/pg-setup service enable`, `/opt/pgpro/1c-17/bin/pg-setup service start`. Там же — список ОС: Ubuntu 22.04, 24.04, 25.10, 26.04 (x86_64).
- Подтверждено 11.10.2026 документацией самой сборки «для 1С» (`https://repo.postgrespro.ru/doc/pg1c/16/ru/html/binary-installation-on-linux.html`, разделы 18.1.4, 18.1.5.2, 18.1.7, и страница `pg-setup`; в версии 18 то же в разделе 17.1): каталог данных `/var/lib/pgpro/1c-NN/data`, имя службы `postgrespro-1c-NN` (файл `/lib/systemd/system/postgrespro-1c-NN.service`, для Debian и Ubuntu есть и скрипт `/etc/init.d/postgrespro-1c-NN`), файл `/etc/default/postgrespro-1c-NN`. То же подтверждено чтением пакета `postgrespro-1c-16-server` 16.14-1.noble (скрипт `pg-setup`, файл службы, `postinst`); написание имени файла с заглавной буквой на странице `pg-setup` (`postgrespro-1C-NN`) — неточность документации, в пакете везде `postgrespro-1c-16`. Проверка: `dpkg -L postgrespro-1c-17-server | grep -E 'pg-setup|\.service'`, `ls /etc/default/postgrespro-*`, `systemctl list-unit-files 'postgrespro*'`, `sudo -u postgres /opt/pgpro/1c-17/bin/psql -Atc "SHOW data_directory"`.
- Подтверждено 11.10.2026 чтением пакета `postgrespro-1c-16-server` 16.14-1.noble: каталог Unix-сокета в сборке «для 1С» — `/tmp` (в `postgresql.conf.sample` — `#unix_socket_directories = '/tmp'`; `pg-setup` ищет свободный порт по отсутствию файла `/tmp/.s.PGSQL.<порт>`). Прежний текст: каталог Unix-сокета в сборках Postgres Pro. Документация Postgres Pro 17 про `unix_socket_directories` говорит: «значение по умолчанию обычно `/tmp`, но оно может быть изменено во время сборки»; в Debian-раскладке — `/var/run/postgresql`. По практике сообщества у Postgres Pro сокет лежит в `/tmp` (отсюда ошибка «No such file or directory … /var/run/postgresql/.s.PGSQL.5432», когда клиент взят из пакетов Ubuntu). Проверка: `SHOW unix_socket_directories;` или `sudo ss -lxp | grep PGSQL`.
- Клиент из состава Postgres Pro (`/opt/pgpro/1c-17/bin/psql`) собран с тем же каталогом сокета, что и сервер, поэтому `sudo -u postgres /opt/pgpro/1c-17/bin/psql` работает без `-h`. Клиенту из пакетов Ubuntu нужно указать каталог явно: `psql -h /tmp` (или `-h 127.0.0.1` с паролем).

### 2.4. Что лежит внутри каталога данных

| Имя | Назначение |
|---|---|
| `base/` | файлы баз данных (подкаталог на каждую базу, имя — OID) |
| `global/` | общие каталоги кластера, файл `pg_control` |
| `pg_wal/` | журнал упреждающей записи (WAL), сегменты по 16 МБ |
| `pg_tblspc/` | символические ссылки на табличные пространства |
| `pg_xact/`, `pg_multixact/` | статусы транзакций |
| `pg_stat/`, `pg_stat_tmp/` | статистика |
| `log/` | журналы сервера, если `logging_collector = on` и `log_directory = 'log'` (умолчание) |
| `PG_VERSION` | номер старшей версии |
| `postgresql.auto.conf` | параметры, заданные `ALTER SYSTEM` |
| `postmaster.pid` | файл блокировки работающего сервера (PID, каталог, время старта, порт, каталог сокета) |
| `postmaster.opts` | параметры командной строки последнего запуска |
| `standby.signal`, `recovery.signal` | признаки режима резервного сервера / восстановления |

Права: каталог данных принадлежит `postgres`, режим `0700` (или `0750`, если кластер создан с `initdb -g`). Сервер откажется стартовать при более широких правах.

## 3. psql: подключение

### 3.1. Параметры подключения

| Ключ | Длинная форма | Что задаёт | Умолчание |
|---|---|---|---|
| `-h` | `--host` | имя хоста, IP или каталог Unix-сокета (если начинается с `/`) | каталог сокета, заданный при сборке |
| `-p` | `--port` | порт TCP или «расширение» файла сокета | 5432 |
| `-U` | `--username` | роль PostgreSQL | имя пользователя ОС |
| `-d` | `--dbname` | база данных или целая строка подключения | совпадает с именем роли |
| `-w` | `--no-password` | никогда не спрашивать пароль (для скриптов) | — |
| `-W` | `--password` | спросить пароль до подключения | — |

Примеры:

```bash
sudo -u postgres psql                              # локально, peer, база postgres
sudo -u postgres psql -d buh                       # сразу в базу buh
psql -h 127.0.0.1 -p 5432 -U postgres -d postgres  # по TCP, спросит пароль
psql -h 192.168.1.10 -U usr1c buh                  # база и роль позиционно: psql [опции] [база [роль]]
psql -h /var/run/postgresql -p 5433 -U postgres    # явный каталог сокета и порт второго кластера
psql "host=192.168.1.10 port=5432 dbname=buh user=usr1c connect_timeout=5"
psql "postgresql://usr1c@192.168.1.10:5432/buh?application_name=admin&connect_timeout=5"
psql -l                                            # список баз и выход
```

Если `sudo -u postgres psql` запускается из каталога, недоступного пользователю `postgres` (например, из `/home/admin`), psql выведет предупреждение `could not change directory to "/home/admin": Permission denied`. Это не ошибка. Чтобы не видеть его, выполняйте `cd /tmp` или `sudo -i -u postgres`.

### 3.2. Peer-аутентификация и `sudo -u postgres`

- Метод `peer` в `pg_hba.conf` (строки типа `local`) берёт имя пользователя ОС у ядра и сравнивает с запрошенной ролью. Пароль не спрашивается и не нужен.
- `pg_createcluster` и `pg-setup initdb` создают кластер с `peer` для локальных подключений и парольным методом для TCP.
  - `pg-setup` (Postgres Pro 14–17, документация): `auth-local = peer`, `auth-host = md5`.
  - `pg_createcluster` (исходный код `postgresql-common`, ветка master): для строк `host` ставится `scram-sha-256`, если версия кластера 14 и выше, и `md5` для более старых; для `local` — `peer`. Текст man-страницы (noble), где назван `md5`, устарел. Документация Ubuntu Server согласуется с кодом: «`scram-sha-256` — умолчание для `host` (до Ubuntu 21.10 был `md5`)». Если в `createcluster.conf` или после `--` заданы свои опции `initdb` `-A`/`--auth*`, обёртка `pg_hba.conf` не трогает.
  - Фактическое значение всегда смотрите в своём `pg_hba.conf` или запросом к `pg_hba_file_rules`. Запись `md5` в `pg_hba.conf` допускает и SCRAM-пароли (сервер сам выберет SCRAM, если пароль роли хранится в виде SCRAM-SHA-256), обратное неверно: при `scram-sha-256` роль с MD5-хешем войти не сможет.
- Поэтому: `sudo -u postgres psql` работает всегда, `psql -U postgres` от пользователя `admin` — нет (`FATAL: Peer authentication failed for user "postgres"`). Обход без правки `pg_hba.conf`: подключаться по TCP (`-h 127.0.0.1`) с паролем.
- Задать пароль роли `postgres` (он нужен серверу 1С, который подключается по TCP):

```bash
sudo -u postgres psql -c "\password postgres"      # интерактивно, пароль не попадёт в историю и журнал
```

```sql
ALTER ROLE postgres PASSWORD 'S3cret';             -- так пароль виден в истории psql и может попасть в журнал сервера
```

### 3.3. Строка подключения и URI (официально, libpq)

```text
postgresql://[пользователь[:пароль]@][хост][:порт][,...][/база][?параметр=значение[&...]]
```

- Схема `postgresql://` или `postgres://`.
- IPv6-адрес — в квадратных скобках: `postgresql://[2001:db8::1234]/database`.
- Каталог сокета в URI: `postgresql:///buh?host=/var/run/postgresql` или с процентным кодированием `postgresql://%2Fvar%2Frun%2Fpostgresql/buh`.
- Несколько хостов: `postgresql://host1:5432,host2:5432/buh?target_session_attrs=read-write`. Значения `target_session_attrs`: `any` (умолчание), `read-write`, `read-only`, `primary`, `standby`, `prefer-standby`.
- `sslmode`: `disable`, `allow`, `prefer` (умолчание), `require`, `verify-ca`, `verify-full`.
- Форма «ключ=значение»: `host=localhost port=5432 dbname=mydb connect_timeout=10`; значения с пробелами — в одинарных кавычках.

### 3.4. Переменные окружения (официально, libpq)

| Переменная | Соответствует | Примечание |
|---|---|---|
| `PGHOST` | `-h` | имя хоста или каталог сокета |
| `PGHOSTADDR` | `hostaddr` | числовой IP, чтобы не обращаться к DNS |
| `PGPORT` | `-p` | |
| `PGDATABASE` | `-d` | |
| `PGUSER` | `-U` | |
| `PGPASSWORD` | пароль | не рекомендуется: в некоторых ОС переменные процесса видны другим пользователям через `ps`. Используйте `~/.pgpass` |
| `PGPASSFILE` | путь к файлу паролей | умолчание `~/.pgpass` |
| `PGSERVICE`, `PGSERVICEFILE` | имя сервиса и файл `~/.pg_service.conf` | |
| `PGOPTIONS` | параметры сеанса | `PGOPTIONS="-c statement_timeout=5min" psql` |
| `PGAPPNAME` | `application_name` | видно в `pg_stat_activity` и журнале |
| `PGCONNECT_TIMEOUT` | тайм-аут подключения, с | |
| `PGCLIENTENCODING` | кодировка клиента | |
| `PGSSLMODE` | `sslmode` | |
| `PGTZ`, `PGDATESTYLE` | часовой пояс и формат дат сеанса | |
| `PGDATA` | каталог данных для серверных утилит (`pg_ctl`, `pg_controldata`) | это не переменная libpq |
| `PGCLUSTER` | `версия/кластер` для обёртки Debian | только `postgresql-common` |

```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGDATABASE=postgres
psql -c "SELECT version();"
PGPASSWORD='S3cret' psql -h 127.0.0.1 -U postgres -c "SELECT 1"   # только для разовых проверок
```

### 3.5. Файл паролей `~/.pgpass` (официально)

Формат строки:

```text
hostname:port:database:username:password
```

Правила:

- Расположение: `~/.pgpass` (домашний каталог берётся из `HOME`), либо путь из `PGPASSFILE` или параметра подключения `passfile`. В Windows — `%APPDATA%\postgresql\pgpass.conf`.
- Права: доступ группе и остальным запрещён — `chmod 0600 ~/.pgpass`. Если права шире, файл игнорируется: подключение не падает, psql спрашивает пароль (а с `-w` завершается ошибкой). По памяти рецензента libpq при этом печатает в stderr предупреждение вида `WARNING: password file "…/.pgpass" has group or world access; permissions should be u=rw (0600) or less` — в заданиях `cron` ищите его в выводе.
- Каждое из первых четырёх полей — литерал или `*` (любое значение). Используется пароль из первой подошедшей строки, поэтому более конкретные строки ставьте выше.
- Символы `:` и `\` внутри значения экранируются обратной косой чертой.
- Имя хоста сравнивается с параметром `host`; если он не задан — ищется `localhost`. `localhost` подходит и для подключения через Unix-сокет в каталоге по умолчанию.
- Строки, начинающиеся с `#`, — комментарии.
- Поле базы `replication` соответствует подключениям потоковой репликации.

```bash
cat > ~/.pgpass <<'EOF'
# hostname:port:database:username:password
127.0.0.1:5432:*:postgres:S3cret
192.168.1.10:5432:buh:usr1c:An0ther
*:*:*:backup:Backup\:Pass
EOF
chmod 0600 ~/.pgpass
psql -w -h 127.0.0.1 -U postgres -c "SELECT current_user"   # -w: не спрашивать пароль, упасть, если его нет
```

Файл ищется в домашнем каталоге того пользователя ОС, от которого запущен клиент. Для заданий `cron` пользователя `postgres` в Debian-раскладке это `/var/lib/postgresql/.pgpass`. Сервер 1С `~/.pgpass` не использует: пароль СУБД хранится в параметрах информационной базы в кластере 1С.

### 3.6. Файл сервисов `~/.pg_service.conf`

```ini
[buh]
host=192.168.1.10
port=5432
dbname=buh
user=usr1c
```

```bash
psql service=buh
PGSERVICE=buh psql
```

Общесистемный файл — `pg_service.conf` в каталоге из `PGSYSCONFDIR` (в Debian-раскладке `/etc/postgresql-common/`).

### 3.7. Файл `~/.psqlrc`

- Общесистемный файл `psqlrc` лежит в каталоге, который показывает `pg_config --sysconfdir`; пользовательский — `~/.psqlrc` (путь меняется переменной `PSQLRC`).
- Можно делать файлы под версию: `~/.psqlrc-18`, `~/.psqlrc-18.6` — более конкретный имеет приоритет.
- Файлы читаются после подключения. Ключ `-X` (`--no-psqlrc`) отключает их чтение — обязательно ставьте его в скриптах, чтобы настройки из `.psqlrc` не ломали разбор вывода.
- История команд — `~/.psql_history` (переменная psql `HISTFILE`, переменная окружения `PSQL_HISTORY`; размер — переменная psql `HISTSIZE`, по умолчанию 500 строк).
- В Debian-раскладке общесистемный каталог — `/etc/postgresql-common/` (файл `/etc/postgresql-common/psqlrc`), для Postgres Pro — то, что выводит `/opt/pgpro/1c-NN/bin/pg_config --sysconfdir`.
- Отличие пакетов Debian/Ubuntu от апстрима (патч `54-debian-alternatives-for-external-tools.patch`): редактор по умолчанию для `\e` — `sensible-editor` (в апстриме `vi`), постраничный просмотр — `pager` (в апстриме `more`). Порядок переменных окружения тот же: `PSQL_EDITOR`, `EDITOR`, `VISUAL`; `PSQL_PAGER`, `PAGER`.

Пример `~/.psqlrc`:

```text
\set QUIET 1
\pset null '(null)'
\x auto
\timing on
\set HISTSIZE 5000
\set HISTCONTROL ignoredups
\set COMP_KEYWORD_CASE upper
\set ON_ERROR_ROLLBACK interactive
\set PROMPT1 '%n@%m:%>/%/%R%x%# '
\set QUIET 0
```

Подстановки в приглашении: `%n` — роль, `%m` — хост (или `[local]`), `%>` — порт, `%/` — база, `%#` — `#` для суперпользователя и `>` для остальных, `%x` — состояние транзакции (`*` — в транзакции, `!` — транзакция с ошибкой), `%R` — `=` в обычном режиме, `-` при продолжении команды, `%p` — PID серверного процесса.

### 3.8. Обёртка `pg_wrapper` в Debian-раскладке: выбор кластера

В Debian-раскладке `psql`, `pg_dump`, `createdb` и другие клиентские программы запускаются через `pg_wrapper`, который выбирает кластер и версию бинарника. Порядок выбора (по убыванию приоритета):

1. опция `--host`;
2. опция `--cluster версия/кластер` (для удалённого сервера — `--cluster версия/хост:порт`, пустой порт означает 5432);
3. переменная `PGHOST` (дальнейший выбор кластера не выполняется);
4. переменная `PGCLUSTER` вида `версия/кластер`;
5. порт из `-p`, `--port` или `PGPORT` без хоста — берётся локальный кластер на этом порту;
6. запись в `~/.postgresqlrc`;
7. запись в `/etc/postgresql-common/user_clusters`;
8. если локальный кластер один — он;
9. если несколько — тот, что слушает порт 5432.

```bash
psql --cluster 16/main -U postgres
PGCLUSTER=17/test pg_dump buh > buh.sql
sudo -u postgres psql -p 5433            # кластер, слушающий 5433
```

Для `psql`, `pg_archivecleanup` и `pg_isready` обёртка берёт самый новый установленный бинарник (они обратно совместимы). Подводный камень из man-страницы: обёртке нужно прочитать конфигурацию сервера, чтобы узнать порт; если порт задан через `ALTER SYSTEM` (в `postgresql.auto.conf`), а обёртка запущена не от `postgres` и не от `root`, подключение может не состояться.

## 4. psql: метакоманды

Метакоманда начинается с обратной косой черты и обрабатывается самим psql, а не сервером. Общие модификаторы команд семейства `\d`: `S` — показывать и системные объекты, `+` — дополнительные столбцы (размер, описание), `x` — развёрнутый вывод (модификатор `x` есть в psql 18; в более старых версиях используйте `\x` или `\gx`). Шаблон имени поддерживает `*` и `?`: `\dt _reference*`, `\dt public.*`.

### 4.1. Справка, подключение, выход

| Команда | Что делает |
|---|---|
| `\?` | справка по метакомандам; `\? options` — ключи командной строки, `\? variables` — переменные |
| `\h` | список команд SQL; `\h ALTER ROLE` — синтаксис конкретной команды |
| `\q` | выход (в скрипте — завершает только этот скрипт) |
| `\c база [роль] [хост] [порт]` | переподключение; `-` на месте параметра — оставить прежнее значение. Пример: `\c buh`, `\c - usr1c`, `\c buh postgres 192.168.1.10 5432`, `\c "postgresql://usr1c@192.168.1.10/buh"` |
| `\conninfo` | сведения о текущем подключении (база, роль, хост или сокет, порт, SSL); в psql 18 вывод стал таблицей и содержит больше сведений (примечания к выпуску 18: «tabular format and include more information») |
| `\password [роль]` | смена пароля роли: psql спрашивает пароль и отправляет на сервер уже зашифрованным, в историю и журнал он не попадает |
| `\encoding [кодировка]` | показать или сменить кодировку клиента |
| `\! команда` | выполнить команду оболочки; `\!` без аргумента — открыть оболочку |
| `\cd каталог` | сменить рабочий каталог psql |

### 4.2. Просмотр объектов

| Команда | Что показывает |
|---|---|
| `\l`, `\l+` | базы данных: владелец, кодировка, провайдер локали, collate/ctype, права; с `+` — размер, табличное пространство, описание |
| `\d` | все таблицы, представления, последовательности текущей базы |
| `\d имя`, `\d+ имя` | структура таблицы: столбцы, типы, индексы, ограничения, триггеры; с `+` — хранение, статистика, описание |
| `\dt`, `\dt+` | таблицы; с `+` — размер и метод доступа |
| `\di`, `\di+` | индексы; с `+` — размер |
| `\dv`, `\dm`, `\ds` | представления, материализованные представления, последовательности |
| `\dn`, `\dn+` | схемы; с `+` — права и описание |
| `\du`, `\dg` | роли и их атрибуты (обе команды равнозначны). В psql 16+ столбец «Member of» из вывода убран |
| `\drg` | членство в ролях: кто в какую роль включён, с какими опциями (`ADMIN`, `INHERIT`, `SET`) и кем выдано (psql 16+) |
| `\dx`, `\dx+` | установленные расширения; с `+` — объекты расширения |
| `\db`, `\db+` | табличные пространства; с `+` — размер, права |
| `\dp`, `\z` | права доступа на таблицы, представления, последовательности (`\z` — синоним `\dp`); в psql 17+ пустой список прав показывается как `(none)`, а права по умолчанию — пустой ячейкой |
| `\ddp` | права по умолчанию (`ALTER DEFAULT PRIVILEGES`) |
| `\df`, `\df+` | функции; `\dfn` — обычные, `\dfa` — агрегатные, `\dfp` — процедуры, `\dft` — триггерные |
| `\sf имя`, `\sf+ имя` | исходный текст функции (`CREATE OR REPLACE FUNCTION ...`); с `+` — с номерами строк |
| `\sv имя` | определение представления |
| `\dT`, `\dT+` | типы данных (в базе 1С здесь видны `mchar`, `mvarchar`) |
| `\dO` | правила сортировки (collations) |
| `\dconfig`, `\dconfig *`, `\dconfig work*` | параметры сервера: без шаблона — только отличные от умолчаний, `*` — все (psql 15+) |
| `\drds` | настройки, заданные через `ALTER ROLE ... SET` и `ALTER DATABASE ... SET` |
| `\dRp`, `\dRs` | публикации и подписки логической репликации |
| `\dy` | событийные триггеры |
| `\dA` | методы доступа |

Примеры:

```text
\l+
\c buh
\dt+ _document*
\d+ _reference15
\di+ _reference15*
\dx
\du
\dp config
\dconfig shared_buffers
```

### 4.3. Формат вывода

| Команда | Что делает |
|---|---|
| `\x [on\|off\|auto]` | развёрнутый вывод («столбец: значение»); `auto` — включается, когда строка не помещается по ширине |
| `\timing [on\|off]` | показывать время выполнения каждой команды (в мс; дольше секунды — ещё и в формате мин:сек) |
| `\a` | переключить выровненный / невыровненный вывод |
| `\t [on\|off]` | только строки данных, без заголовков и итоговой строки |
| `\f [строка]` | разделитель полей для невыровненного вывода |
| `\H` | HTML-вывод |
| `\C [заголовок]` | заголовок таблицы |
| `\pset параметр [значение]` | любая настройка вывода; `\pset` без аргументов — показать все |

Параметры `\pset`: `border` (0–3), `columns`, `csv_fieldsep` (по умолчанию `,`), `expanded` (`x`), `fieldsep` (по умолчанию `|`), `fieldsep_zero`, `footer`, `format` (`aligned`, `asciidoc`, `csv`, `html`, `latex`, `latex-longtable`, `troff-ms`, `unaligned`, `wrapped`), `linestyle` (`ascii`, `old-ascii`, `unicode`), `null`, `numericlocale`, `pager` (`on`, `off`, `always`), `pager_min_lines`, `recordsep`, `recordsep_zero`, `tableattr`, `title`, `tuples_only` (`t`), `unicode_border_linestyle`, `unicode_column_linestyle`, `unicode_header_linestyle`, `xheader_width`.

```text
\pset null '(null)'
\pset pager off
\pset format csv
\pset border 2
\pset linestyle unicode
```

### 4.4. Буфер запроса, выполнение, файлы

| Команда | Что делает |
|---|---|
| `\g [файл]`, `\g \|команда` | выполнить буфер запроса (как `;`), результат можно направить в файл или в конвейер. `\g (format=csv) out.csv` — с разовыми настройками вывода |
| `\gx` | выполнить буфер с развёрнутым выводом только для этого запроса |
| `\gexec` | выполнить запрос, а затем каждое непустое значение результата — как отдельную команду SQL |
| `\gset [префикс]` | записать столбцы единственной строки результата в переменные psql |
| `\gdesc` | показать имена и типы столбцов результата, не выполняя запрос |
| `\watch [i=сек] [c=число] [m=мин_строк] [сек]` | повторять запрос с интервалом (умолчание 2 с; в psql 18 умолчание меняется переменной `WATCH_INTERVAL`); `c=` — число повторов (psql 16+), `m=` — остановиться, когда запрос вернул меньше строк, чем задано (psql 17+). Полные имена опций: `interval=`, `count=`, `min_rows=`. До psql 16 допустима только форма `\watch [сек]` |
| `\e [файл] [строка]` | открыть буфер или файл в редакторе (`PSQL_EDITOR`, `EDITOR`, `VISUAL` — в таком порядке; по умолчанию `vi`, в пакетах Debian/Ubuntu — `sensible-editor`, см. 3.7) |
| `\ef [функция]`, `\ev [представление]` | редактировать определение функции или представления |
| `\p` | показать буфер запроса |
| `\r` | очистить буфер запроса |
| `\w файл` | записать буфер запроса в файл |
| `\s [файл]` | показать или сохранить историю команд |
| `\i файл` | выполнить команды из файла |
| `\ir файл` | то же, но путь относительно каталога текущего скрипта |
| `\o [файл]`, `\o \|команда` | направить вывод запросов в файл или конвейер; `\o` без аргумента — вернуть на экран |
| `\echo текст`, `\qecho текст`, `\warn текст` | вывести текст в stdout, в канал `\o`, в stderr |
| `\copy ...` | копирование на стороне клиента (см. 5.4) |
| `\set [имя [значение]]`, `\unset имя` | задать или удалить переменную psql; `\set` без аргументов — показать все |
| `\getenv переменная ИМЯ_ОКРУЖЕНИЯ`, `\setenv ИМЯ [значение]` | обмен с переменными окружения |
| `\prompt [текст] имя` | спросить значение у пользователя и записать в переменную |
| `\if`, `\elif`, `\else`, `\endif` | условное выполнение в скриптах |
| `\errverbose` | повторить последнее сообщение об ошибке с максимальной подробностью |
| `\crosstabview` | вывести результат как перекрёстную таблицу |
| `\bind параметр ...` | задать параметры `$1`, `$2` для следующего запроса (psql 16+) |
| `\restrict ключ`, `\unrestrict ключ` | ограниченный режим: после `\restrict` разрешена только `\unrestrict` с тем же ключом. Эти команды `pg_dump`, `pg_dumpall` и `pg_restore` вставляют в текстовые дампы; вручную не используются. Появились в исправлении безопасности CVE-2025-8714: PostgreSQL 17.6 от 14 августа 2025 года (подтверждено примечаниями к выпуску) и одновременные выпуски остальных веток (16.10, 15.14, 14.19, 13.22 — подтверждено примечаниями к каждому из этих четырёх выпусков 11.10.2026; прежняя оговорка: для них примечания не перечитывались), а также 18.0. Следствие: текстовый дамп, снятый новым `pg_dump`, более старый `psql` не загрузит (ошибка вида `invalid command \restrict`) — загружайте дамп тем же или более новым `psql` |
| `\parse имя`, `\bind_named имя параметр ...`, `\close_prepared имя` | именованные подготовленные операторы (psql 18) |
| `\startpipeline`, `\sendpipeline`, `\syncpipeline`, `\flushrequest`, `\flush`, `\getresults`, `\endpipeline` | конвейерный режим протокола (psql 18); администратору практически не нужен |

Примеры:

```sql
-- повторять раз в 5 секунд, 12 раз
SELECT count(*) FROM pg_stat_activity WHERE state = 'active' \watch i=5 c=12

-- разовый развёрнутый вывод
SELECT * FROM pg_stat_activity WHERE pid = pg_backend_pid() \gx

-- сгенерировать команды и сразу выполнить: ANALYZE для 10 самых больших таблиц
SELECT format('ANALYZE %s', c.oid::regclass)
FROM pg_class c
WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 10 \gexec

-- значение в переменную и использование
SELECT pg_database_size(current_database()) AS sz \gset
\echo Размер базы: :sz байт

-- вывод в файл и обратно на экран
\o /tmp/sessions.txt
SELECT * FROM pg_stat_activity;
\o
```

Замечания по версиям (подтверждено примечаниями к выпускам): именованные опции `\watch` и ограничение числа повторов `c=` — psql 16; `m=` (`min_rows`) — psql 17; переменная `WATCH_INTERVAL` — psql 18; `\bind` — psql 16. Версия psql определяется клиентом, а не сервером: в Debian-раскладке `pg_wrapper` запускает самый новый из установленных `psql`, в Postgres Pro — тот, по чьему пути вы его вызвали. Проверка — `psql --version` и `\?`. `\gexec` выполняет сгенерированные команды по одной, в режиме автофиксации каждая — отдельная транзакция.

### 4.5. Переменные psql

| Переменная | Значение по умолчанию | Смысл |
|---|---|---|
| `AUTOCOMMIT` | `on` | каждая команда фиксируется сразу; при `off` psql сам открывает транзакцию, нужен явный `COMMIT` |
| `ON_ERROR_STOP` | выключена | при ошибке прекратить выполнение скрипта; код возврата 3 |
| `ON_ERROR_ROLLBACK` | `off` | `on` / `interactive` — ошибка внутри транзакции не обрывает её (неявные точки сохранения) |
| `ECHO` | `none` | `all` (`-a`), `queries` (`-e`), `errors` (`-b`) |
| `ECHO_HIDDEN` | `off` | показывать запросы, которые выполняют метакоманды (`-E`); удобно, чтобы подсмотреть SQL за `\d` |
| `FETCH_COUNT` | не задана | получать результат порциями по N строк, а не целиком в память |
| `HISTSIZE`, `HISTFILE`, `HISTCONTROL` | 500, `~/.psql_history`, `none` | история команд |
| `QUIET` | выключена | не выводить приветствие и служебные сообщения (`-q`) |
| `VERBOSITY` | `default` | подробность ошибок: `default`, `verbose`, `terse`, `sqlstate` |
| `PROMPT1`, `PROMPT2`, `PROMPT3` | `'%/%R%x%# '`, то же, `'>> '` | приглашения |
| `ROW_COUNT`, `SQLSTATE`, `ERROR` | — | результат последней команды: число строк, код состояния, `true` при ошибке |
| `SERVER_VERSION_NUM`, `SERVER_VERSION_NAME` | — | версия сервера, например `180006` и `18.6` |
| `DBNAME`, `HOST`, `PORT`, `USER` | — | параметры текущего подключения |
| `WATCH_INTERVAL` | 2 | интервал `\watch` по умолчанию, секунд (только psql 18+) |
| `SHELL_ERROR`, `SHELL_EXIT_CODE` | — | признак ошибки и код возврата последней команды оболочки, запущенной из psql (например, через `\!`); psql 16+ |

Подстановка в SQL: `:имя` — как есть, `:'имя'` — как строковый литерал с экранированием, `:"имя"` — как идентификатор, `:{?имя}` — задана ли переменная. Внутри кавычек подстановка не выполняется.

```sql
\set tbl '_reference15'
SELECT count(*) FROM :"tbl";
\set db 'buh'
SELECT pg_size_pretty(pg_database_size(:'db'));
```

## 5. psql: неинтерактивный запуск и выгрузка

### 5.1. Ключи для скриптов

| Ключ | Длинная форма | Что делает |
|---|---|---|
| `-c 'SQL'` | `--command` | выполнить команду и выйти; можно несколько `-c` подряд |
| `-f файл` | `--file` | выполнить команды из файла (`-f -` — из stdin) |
| `-A` | `--no-align` | невыровненный вывод |
| `-t` | `--tuples-only` | только данные, без заголовка и итога |
| `-F 'x'` | `--field-separator` | разделитель полей для `-A` (умолчание — вертикальная черта) |
| `-R 'x'` | `--record-separator` | разделитель записей для `-A` |
| `-z`, `-0` | | разделители — нулевой байт (для `xargs -0`) |
| `--csv` | | вывод в CSV (psql 12+) |
| `-x` | `--expanded` | развёрнутый вывод |
| `-H` | `--html` | HTML |
| `-P настройка` | `--pset` | любая настройка `\pset`, например `-P pager=off`, `-P null=NULL` |
| `-o файл` | `--output` | вывод запросов в файл |
| `-L файл` | `--log-file` | дополнительно писать весь вывод в файл |
| `-v имя=значение` | `--set`, `--variable` | задать переменную psql |
| `-X` | `--no-psqlrc` | не читать `psqlrc` и `~/.psqlrc` |
| `-q` | `--quiet` | без служебных сообщений |
| `-1` | `--single-transaction` | обернуть все команды `-c`/`-f` в одну транзакцию (`BEGIN`…`COMMIT`); при ошибке и `ON_ERROR_STOP` — откат |
| `-a`, `-e`, `-b` | `--echo-all`, `--echo-queries`, `--echo-errors` | печатать входные строки / отправляемые запросы / упавшие запросы |
| `-E` | `--echo-hidden` | показывать запросы метакоманд |
| `-w`, `-W` | `--no-password`, `--password` | не спрашивать / спросить пароль |
| `-l` | `--list` | список баз и выход |
| `-V` | `--version` | версия psql |

Коды возврата psql: `0` — нормальное завершение; `1` — фатальная ошибка самого psql (нет памяти, файл не найден); `2` — подключение не удалось и сеанс не интерактивный; `3` — ошибка в скрипте при установленной `ON_ERROR_STOP`.

### 5.2. Типовые формы

```bash
# одно значение в переменную оболочки
SIZE=$(sudo -u postgres psql -X -At -c "SELECT pg_database_size('buh')")

# список баз, по одной в строке
sudo -u postgres psql -X -At -c "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY 1"

# несколько полей через табуляцию
sudo -u postgres psql -X -At -F $'\t' -c "SELECT datname, pg_database_size(datname) FROM pg_database"

# выполнить файл, остановиться на первой ошибке, всё в одной транзакции
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -1 -d buh -f /tmp/script.sql

# передать переменную в скрипт
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -v dbname=buh -f /tmp/report.sql
#   в report.sql:  SELECT pg_size_pretty(pg_database_size(:'dbname'));

# SQL из heredoc
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -d postgres <<'SQL'
SELECT now();
SELECT count(*) FROM pg_stat_activity;
SQL

# проверка кода возврата
if ! sudo -u postgres psql -X -qAt -v ON_ERROR_STOP=1 -c "SELECT 1" >/dev/null; then
    echo "PostgreSQL недоступен" >&2
    exit 1
fi

# цикл по базам
for db in $(sudo -u postgres psql -X -At -c "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate"); do
    sudo -u postgres psql -X -At -d "$db" -c "SELECT current_database(), count(*) FROM pg_stat_user_tables"
done
```

Подводные камни:

- `psql -c "команда1; команда2"` отправляет строку одним запросом, сервер выполняет её как одну транзакцию. Команды, которые нельзя выполнять в блоке транзакции (`CREATE DATABASE`, `DROP DATABASE`, `VACUUM`, `ALTER SYSTEM`, `CREATE TABLESPACE`), в такой строке вместе с другими не работают. Давайте каждой свой `-c` или используйте `-f`.
- Метакоманды в `-c` должны быть единственным содержимым: `-c "\l"` работает, `-c "\l; SELECT 1"` — нет. Смешивать SQL и метакоманды можно в `-f` или через несколько `-c`.
- Без `ON_ERROR_STOP=1` psql после ошибки продолжит выполнять скрипт и вернёт код 0.
- Без `-X` на вывод влияет чужой `~/.psqlrc` (например, `\x auto` или `\timing on`).

### 5.3. Вывод в CSV

```bash
# заголовок + данные
sudo -u postgres psql -X --csv -d buh -c "SELECT datname, numbackends FROM pg_stat_database" > /tmp/db.csv

# без заголовка
sudo -u postgres psql -X --csv -t -d buh -c "SELECT 1, 'a'" > /tmp/x.csv

# разделитель «точка с запятой» (для Excel с русской локалью)
sudo -u postgres psql -X --csv -P csv_fieldsep=';' -d buh -c "SELECT ..." > /tmp/x.csv
```

В интерактивном сеансе:

```text
\pset format csv
\o /tmp/out.csv
SELECT ...;
\o
\pset format aligned
```

### 5.4. `\copy` и `COPY`

- `COPY ... TO/FROM 'файл'` — файл читает и пишет серверный процесс (пользователь ОС `postgres`), путь — на сервере; нужны права суперпользователя или роли `pg_read_server_files` / `pg_write_server_files`.
- `\copy ... to/from 'файл'` — файл читает и пишет psql на стороне клиента с правами локального пользователя; прав суперпользователя не требуется. Вся остальная строка — аргументы `\copy`, подстановка переменных в ней не выполняется, команда должна быть в одну строку.
- Для больших объёмов `COPY` с файлом на сервере быстрее: при `\copy` данные идут через клиентское соединение.

```text
\copy (SELECT datname, pg_database_size(datname) FROM pg_database) TO '/tmp/sizes.csv' WITH (FORMAT csv, HEADER, DELIMITER ';')
\copy mytable FROM '/tmp/data.csv' WITH (FORMAT csv, HEADER)
\copy mytable TO PROGRAM 'gzip > /tmp/mytable.csv.gz' WITH (FORMAT csv)
```

Многострочный вариант с подстановкой переменных (совет из документации psql):

```sql
COPY (SELECT relname, n_live_tup
      FROM pg_stat_user_tables
      ORDER BY n_live_tup DESC)
TO STDOUT WITH (FORMAT csv, HEADER) \g /tmp/tables.csv
```

## 6. Управление сервером

### 6.1. systemd в Debian-раскладке

Устройство (README.systemd пакета `postgresql-common`):

- каждый кластер — отдельная служба `postgresql@<версия>-<кластер>.service`, например `postgresql@16-main.service`;
- `postgresql.service` — родительская служба: запускает, останавливает, перезапускает и перечитывает все кластеры, у которых в `start.conf` стоит `auto`. Связи создаёт генератор `postgresql-generator`;
- журналы по-прежнему пишутся в `/var/log/postgresql`.

```bash
systemctl list-units 'postgresql*'            # все юниты PostgreSQL
systemctl status postgresql@16-main           # состояние конкретного кластера
sudo systemctl start postgresql@16-main
sudo systemctl stop postgresql@16-main
sudo systemctl restart postgresql@16-main
sudo systemctl reload postgresql@16-main      # перечитать конфигурацию без разрыва сеансов
sudo systemctl restart postgresql             # перезапустить ВСЕ кластеры с start.conf = auto
sudo systemctl enable postgresql              # автозапуск при загрузке (всех кластеров auto)
sudo systemctl disable postgresql             # отключить автозапуск всех кластеров
journalctl -u postgresql@16-main -n 50        # сообщения systemd о запуске и остановке
```

Автозапуск отдельного кластера управляется файлом `/etc/postgresql/NN/<кластер>/start.conf`:

| Значение | Поведение |
|---|---|
| `auto` | кластер запускается и останавливается вместе с `postgresql.service` (умолчание, в том числе если файла нет) |
| `manual` | автоматически не запускается, но `pg_ctlcluster` и `systemctl start postgresql@NN-имя` работают |
| `disabled` | не запускается ничем из штатных средств; по man-странице — только защита от случайностей на время обслуживания |

После правки `start.conf` выполните `sudo systemctl daemon-reload`, чтобы генератор пересоздал связи.

Что написано в юните `postgresql@.service` (исходный код `postgresql-common` 278; посмотреть у себя — `systemctl cat postgresql@16-main`):

- запуск, остановка и перечитывание идут через `pg_ctlcluster --skip-systemctl-redirect`, остановка — в режиме `fast`; есть `ExecReload`, поэтому `systemctl reload` работает;
- юнит требует смонтированных каталогов конфигурации и данных кластера (`RequiresMountsFor` для `/etc/postgresql/<версия>/<кластер>` и `/var/lib/postgresql/<версия>/<кластер>`), входит в `postgresql.service` (`PartOf`), получает от него `reload` и стартует после `network.target`;
- `TimeoutStartSec=0` — запуск не ограничен по времени (восстановление после сбоя может идти долго), неудача запуска игнорируется; `TimeoutStopSec=1h`;
- `OOMScoreAdjust=-900` — защита postmaster от OOM-killer;
- автоматический перезапуск (`Restart=`) намеренно выключен: он мешал бы `pg_ctlcluster ... stop`.

Сам `postgresql.service` — служба типа `oneshot`, у которой запуск и перечитывание — пустая команда `/bin/true`, а `RemainAfterExit` включён; отсюда его вечное `active (exited)`.

В пакете `postgresql-common` есть и другие шаблоны юнитов (по списку файлов пакета для noble): `pg_basebackup@.service`/`.timer`, `pg_dump@.service`/`.timer`, `pg_receivewal@.service`, `pg_compresswal@.service`/`.timer` — готовое еженедельное резервное копирование в `/var/backups/postgresql/<версия>/<кластер>` с хранением трёх копий (README.systemd; включаются командой `systemctl enable --now pg_basebackup@16-main.timer`; для восстановления на момент времени нужен ещё `pg_receivewal@16-main`). README называет эти средства подходящими для малых и средних баз, для больших советует pgBackRest или Barman. О резервном копировании баз 1С — `kb/postgresql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md`.

### 6.2. Обёртки `postgresql-common`

#### pg_lsclusters

Синтаксис: `pg_lsclusters [опции] [версия [кластер]]`. Показывает все кластеры: версия, имя, порт, статус, владелец, каталог данных, файл журнала.

| Ключ | Смысл |
|---|---|
| `-h`, `--no-header` | без строки заголовка |
| `-j`, `--json` | вывод в JSON (нужен пакет `libjson-perl`) |
| `-s`, `--start-conf` | добавить в статус значение `start.conf` |

Статус: `online` или `down`; у резервного сервера добавляется `,recovery`. Столбцы вывода: `Ver`, `Cluster`, `Port`, `Status`, `Owner`, `Data directory`, `Log file`.

```bash
pg_lsclusters
pg_lsclusters -h | awk '{print $1"/"$2, $3, $4}'
pg_lsclusters 16 main
```

#### pg_ctlcluster

Синтаксис: `pg_ctlcluster [опции] версия кластер действие [-- опции pg_ctl]`, действие — `start|stop|restart|reload|status|promote`.

| Действие / ключ | Смысл |
|---|---|
| `start` | создать при необходимости файл журнала и запустить сервер. Коды возврата: 0 — успех, 2 — уже запущен, 1 — прочая ошибка |
| `stop` | остановить; по умолчанию режим `fast`. Коды возврата: 0 — успех, 2 — сервер не был запущен, 1 — прочая ошибка |
| `restart` | остановить (если работает) и запустить |
| `reload` | перечитать конфигурацию без остановки |
| `status` | работает ли сервер; показывает PID и параметры запуска |
| `promote` | перевести резервный сервер в режим чтения-записи |
| `-m`, `--mode smart\|fast\|immediate` | режим остановки для `stop` и `restart`, умолчание `fast` |
| `-f`, `--force` | для `stop`/`restart`: последовательно `fast`, затем `immediate`, затем уничтожение процесса. По man-странице — только когда машина всё равно выключается |
| `--foreground` | запустить `postgres` на переднем плане |
| `--stdlog` | вместе с `--foreground`: stderr в штатный журнал в `/var/log/postgresql/` |
| `-o параметр` | передать параметр процессу `postgres` (можно несколько раз) |
| `--bindir каталог` | каталог с `pg_ctl`, умолчание `/usr/lib/postgresql/<версия>/bin` |
| `--skip-systemctl-redirect` | не перенаправлять на systemd (используется внутри юнита) |

Запущенный от `root`, `pg_ctlcluster` перенаправляет действия в `systemctl`, чтобы кластером управлял systemd (кроме случаев, когда переданы дополнительные опции `postgres` или `pg_ctl`). По исходному коду перенаправляются только `start`, `stop` и `restart`; `reload`, `status` и `promote` выполняются самой обёрткой. Если файла журнала в `/var/log/postgresql/` нет, `start` создаст его заново (режим `0640`, группа `adm`).

```bash
sudo pg_ctlcluster 16 main status
sudo pg_ctlcluster 16 main reload
sudo pg_ctlcluster 16 main restart
sudo pg_ctlcluster -m smart 16 main stop
sudo -u postgres pg_ctlcluster 16 main promote
```

#### pg_createcluster

Синтаксис: `pg_createcluster [опции] версия имя [-- опции initdb]`.

| Ключ | Смысл |
|---|---|
| `-u`, `--user` | владелец кластера и суперпользователь БД (умолчание `postgres`; владельцем не может быть `root`) |
| `-g`, `--group` | группа файлов данных |
| `-d`, `--datadir` | каталог данных (умолчание `/var/lib/postgresql/<версия>/<имя>`) |
| `-s`, `--socketdir` | каталог сокета (умолчание `/var/run/postgresql` для кластеров `postgres`, иначе `/tmp`) |
| `-l`, `--logfile` | файл журнала (умолчание `/var/log/postgresql/postgresql-<версия>-<имя>.log`) |
| `--locale` | локаль кластера; если не задана — наследуется из окружения |
| `--lc-collate`, `--lc-ctype`, `--lc-messages`, `--lc-monetary`, `--lc-numeric`, `--lc-time` | локаль отдельной категории |
| `-e`, `--encoding` | кодировка шаблонных баз; man-страница не рекомендует задавать напрямую — задавайте локаль |
| `-p`, `--port` | порт (1024–65535); по умолчанию — следующий свободный, начиная с 5432 |
| `--start` | запустить кластер после создания (по умолчанию не запускается) |
| `--start-conf auto\|manual\|disabled` | начальное значение `start.conf`, умолчание `auto` |
| `-o параметр=значение`, `--pgoption` | записать параметр в новый `postgresql.conf` |
| `--createclusterconf файл`, `--environment файл` | альтернативные `createcluster.conf` и `environment` |
| `-q`, `--quiet` | без вывода `initdb` |
| `-- опции` | всё после `--` передаётся в `initdb` |

```bash
# основной кластер с русской локалью (локаль должна быть сгенерирована: sudo locale-gen ru_RU.UTF-8)
sudo pg_createcluster --locale ru_RU.UTF-8 --start 16 main

# второй кластер на другом диске и порту, с контрольными суммами страниц
sudo pg_createcluster -d /mnt/pgdata/16/test -p 5433 --locale ru_RU.UTF-8 --start 16 test -- --data-checksums

# сразу задать параметры
sudo pg_createcluster --locale ru_RU.UTF-8 -o listen_addresses='*' -o max_connections=500 --start 17 main
```

Опции записаны перед версией и именем — так, как в синопсисе man-страницы. На практике часто пишут и `pg_createcluster 16 main --locale ... --start`.

#### pg_dropcluster

Синтаксис: `pg_dropcluster [--stop] версия имя`. Удаляет все файлы кластера: данные, WAL, табличные пространства, журнал и конфигурацию, созданную `pg_createcluster`. Без `--stop` работающий кластер не удаляется. Операция необратима.

```bash
sudo pg_dropcluster --stop 16 test
```

Типовой приём при неверной локали свежеустановленного кластера (пока в нём нет данных):

```bash
sudo pg_dropcluster --stop 16 main
sudo pg_createcluster --locale ru_RU.UTF-8 --start 16 main
```

#### pg_renamecluster

Синтаксис: `pg_renamecluster версия старое_имя новое_имя`. Переименовывает каталог конфигурации в `/etc/postgresql/<версия>/`, каталог данных в `/var/lib/postgresql/<версия>/` и файлы журналов в `/var/log/postgresql/`; в `postgresql.conf` обновляет `data_directory`, `hba_file`, `ident_file`, `external_pid_file`, `stats_temp_directory`, `cluster_name`. Кластер на время операции останавливается и запускается снова.

```bash
sudo pg_renamecluster 16 main prod
```

#### pg_conftool

Синтаксис: `pg_conftool [опции] [версия кластер] [файл] команда`. Если файл не указан — `postgresql.conf`.

| Команда / ключ | Смысл |
|---|---|
| `show параметр\|all` | показать параметр или все параметры, присутствующие в файле |
| `set параметр значение` | задать или изменить параметр |
| `remove параметр` | убрать параметр (закомментировать) |
| `edit` | открыть файл в редакторе (`$EDITOR`, иначе `vi`) |
| `-s`, `--short` | показывать только значение |
| `-b`, `--boolean` | булево значение в виде `on`/`off` |
| `-v`, `--verbose` | подробный вывод |

```bash
pg_conftool 16 main show all
pg_conftool -s 16 main show data_directory
sudo pg_conftool 16 main set listen_addresses '*'
sudo pg_conftool 16 main set shared_buffers 4GB
sudo pg_conftool 16 main remove work_mem
sudo pg_conftool 16 main edit                  # открыть postgresql.conf в редакторе
sudoedit /etc/postgresql/16/main/pg_hba.conf   # pg_hba.conf правится обычным редактором
sudo systemctl reload postgresql@16-main
```

`pg_conftool` правит только файл. Чтобы изменение подействовало, нужен `reload` или `restart` (см. раздел 12).

#### pg_upgradecluster

Синтаксис: `pg_upgradecluster [-v новая_версия] старая_версия имя [новый_каталог_данных]`.

| Ключ | Смысл |
|---|---|
| `-v версия` | целевая версия; по умолчанию — самая новая из установленных |
| `-m`, `--method dump\|upgrade\|link\|clone` | способ: `dump` — `pg_dump` + `pg_restore` (умолчание), `upgrade` — `pg_upgrade`; `link` и `clone` — сокращения для `-m upgrade --link` и `-m upgrade --clone` |
| `-k`, `--link` | жёсткие ссылки вместо копирования (для `pg_upgrade`) |
| `--clone` | клонирование файлов (reflink) |
| `-j`, `--jobs` | число параллельных процессов |
| `--locale`, `--lc-*` | локаль нового кластера; по умолчанию — как у старого |
| `--keep-port` | не менять порты местами |
| `--rename имя` | дать новому кластеру другое имя |
| `--logfile файл` | файл журнала нового кластера |
| `--old-bindir каталог` | передаётся в `pg_upgrade` |
| `--maintenance-db база` | база для служебных запросов, умолчание `template1` |
| `--start`, `--no-start` | запускать ли новый кластер |
| `--keep-on-error` | не удалять новый кластер при неудаче |

Поведение по умолчанию: новый кластер создаётся в `/var/lib/postgresql/<новая_версия>/<имя>`; старый кластер переносится на ранее не использовавшийся порт, новый получает исходный порт; старый кластер не удаляется, ему ставится `start.conf = manual`. Контрольные суммы страниц наследуются от старого кластера. Сценарии-перехватчики — в `/etc/postgresql-common/pg_upgradecluster.d/`.

```bash
# при установке postgresql-17 пакет создал пустой кластер 17/main — его нужно убрать
sudo pg_dropcluster --stop 17 main
sudo pg_upgradecluster -m upgrade -v 17 16 main
pg_lsclusters
# после проверки
sudo pg_dropcluster 16 main
```

Для баз 1С обе версии должны быть сборками с доработками 1С (иначе типы `mchar`/`mvarchar` не найдутся). Обновление старшей версии — отдельная тема; здесь только справка по утилите.

#### Прочие программы пакета postgresql-common

По списку файлов пакета (noble) в `/usr/bin` также лежат:

| Программа | Назначение |
|---|---|
| `pg_backupcluster версия кластер действие` | резервные копии кластера в `/var/backups/postgresql/` (базовая копия, дамп, архив WAL); её и запускают юниты `pg_basebackup@`, `pg_dump@` |
| `pg_restorecluster версия кластер каталог_копии` | восстановление кластера из копии, сделанной `pg_backupcluster` |
| `pg_virtualenv` | временный кластер для тестов: создаётся, выполняется команда, кластер удаляется |
| `pg_buildext` | сборка расширений под несколько версий (для сопровождающих пакетов) |
| `pg_config` | обёртка над `pg_config` конкретных версий (⚠ логика выбора версии не проверялась; для однозначного результата вызывайте `/usr/lib/postgresql/NN/bin/pg_config`) |
| `/usr/sbin/pg_updatedicts` | обновление словарей полнотекстового поиска из системных словарей |

⚠ Синтаксис `pg_backupcluster`/`pg_restorecluster` приведён по памяти и здесь не разбирается; перед применением прочитайте `man pg_backupcluster`.

### 6.3. «Родной» pg_ctl (официально)

```text
pg_ctl init[db] [-D datadir] [-s] [-o initdb-options]
pg_ctl start    [-D datadir] [-l filename] [-W] [-t seconds] [-s] [-o options] [-p path] [-c]
pg_ctl stop     [-D datadir] [-m s[mart] | f[ast] | i[mmediate]] [-W] [-t seconds] [-s]
pg_ctl restart  [-D datadir] [-m s[mart] | f[ast] | i[mmediate]] [-W] [-t seconds] [-s] [-o options] [-c]
pg_ctl reload   [-D datadir] [-s]
pg_ctl status   [-D datadir]
pg_ctl promote  [-D datadir] [-W] [-t seconds] [-s]
pg_ctl logrotate [-D datadir] [-s]
pg_ctl kill signal_name process_id
```

Режимы остановки (`-m`):

| Режим | Поведение |
|---|---|
| `smart` | новые подключения запрещаются, сервер ждёт, пока отключатся все клиенты |
| `fast` (умолчание) | клиентов не ждёт: активные транзакции откатываются, клиенты принудительно отключаются, затем штатная остановка |
| `immediate` | все серверные процессы прерываются немедленно, без штатной остановки; при следующем запуске будет восстановление по WAL |

Ключи: `-D` — каталог данных (иначе берётся `PGDATA`); `-l файл` — дописывать вывод сервера в файл; `-w` — ждать завершения операции (умолчание для `start`, `stop`, `restart`, `promote`), `-W` — не ждать; `-t сек` — сколько ждать (умолчание — `PGCTLTIMEOUT` или 60 с; по истечении операция может продолжиться в фоне); `-o "опции"` — передать опции процессу `postgres`; `-s` — только ошибки; `-c` — разрешить дампы памяти. Код возврата `pg_ctl status`: 3 — сервер не работает, 4 — не указан доступный каталог данных.

Запускать `pg_ctl` нужно от владельца кластера (`postgres`), не от `root`.

```bash
# Postgres Pro: конфигурация лежит в каталоге данных, pg_ctl работает напрямую
sudo -u postgres /opt/pgpro/1c-17/bin/pg_ctl -D /var/lib/pgpro/1c-17/data status
sudo -u postgres /opt/pgpro/1c-17/bin/pg_ctl -D /var/lib/pgpro/1c-17/data reload
sudo -u postgres /opt/pgpro/1c-17/bin/pg_ctl -D /var/lib/pgpro/1c-17/data stop -m fast

# Debian-раскладка: status и reload по каталогу данных работают
sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main status
```

В Debian-раскладке `postgresql.conf` лежит не в каталоге данных, поэтому `pg_ctl -D /var/lib/postgresql/16/main start` завершится ошибкой вида `postgres cannot access the server configuration file`. Используйте `pg_ctlcluster` или `systemctl`. Если служба управляется systemd, не запускайте и не останавливайте сервер через `pg_ctl` в обход: systemd потеряет состояние юнита.

### 6.4. Postgres Pro: служба, pg-setup, pg-wrapper

Служба (на примере сборки для 1С версии 17):

```bash
systemctl status postgrespro-1c-17
sudo systemctl start postgrespro-1c-17
sudo systemctl stop postgrespro-1c-17
sudo systemctl restart postgrespro-1c-17
sudo systemctl reload postgrespro-1c-17      # Подтверждено 11.10.2026 чтением пакета postgrespro-1c-16-server 16.14: в юните есть ExecReload=/bin/kill -HUP $MAINPID; равнозначно SELECT pg_reload_conf();
sudo systemctl enable postgrespro-1c-17
journalctl -u postgrespro-1c-17 -n 100
```

`pg-setup` (официально, документация Postgres Pro 17) — сценарий оболочки в `/opt/pgpro/<редакция>-NN/bin`, входит в серверный пакет. Запускается от `root`; операции с базой выполняет от имени `postgres`.

```text
pg-setup initdb [параметры_initdb]
pg-setup find-free-port
pg-setup set-server-port порт
pg-setup set параметр значение
pg-setup service параметр_service
```

| Подкоманда | Смысл |
|---|---|
| `initdb [параметры initdb]` | создать кластер. По умолчанию каталог `/var/lib/pgpro/<редакция>-NN/data`, контрольные суммы включены (отключение — `--no-data-checksums`), `auth-local = peer`, `auth-host = md5`, локаль берётся из `LANG` (переменные `LC_*` игнорируются). Путь к каталогу данных сохраняется в `/etc/default/postgrespro-<редакция>-NN` |
| `find-free-port` | найти свободный порт |
| `set-server-port порт` | задать порт сервера (умолчание 5432) |
| `set параметр значение` | записать параметр в `postgresql.conf`; если параметр был задан через `ALTER SYSTEM`, старое значение удаляется из `postgresql.auto.conf` |
| `service enable` / `disable` | включить / отключить автозапуск |
| `service start` / `stop` | запустить / остановить службу |
| `service condrestart` | перезапустить, если служба работает |
| `service status` | состояние службы |

```bash
locale -a | grep -i ru_RU                                         # локаль должна существовать ДО initdb (sudo locale-gen ru_RU.UTF-8)
sudo LANG=ru_RU.UTF-8 /opt/pgpro/1c-17/bin/pg-setup initdb        # LANG передаётся прямо в команде: не зависит от настроек sudo
# либо явно параметром initdb: sudo /opt/pgpro/1c-17/bin/pg-setup initdb --locale=ru_RU.UTF-8
sudo /opt/pgpro/1c-17/bin/pg-setup service enable
sudo /opt/pgpro/1c-17/bin/pg-setup service start
sudo -u postgres /opt/pgpro/1c-17/bin/psql -Atc "SELECT datname, datcollate, datctype FROM pg_database"   # проверить локаль (сервер уже запущен)
sudo /opt/pgpro/1c-17/bin/pg-setup set max_connections 500       # пример изменения параметра (нужен перезапуск)
sudo /opt/pgpro/1c-17/bin/pg-setup set-server-port 5433          # только если нужен порт, отличный от 5432
sudo /opt/pgpro/1c-17/bin/pg-setup service condrestart           # перезапуск, чтобы применить оба изменения
```

Подкоманды `reload` у `pg-setup service` в документации нет: перечитывайте конфигурацию через `SELECT pg_reload_conf();` или `pg_ctl reload`.

- В Postgres Pro 17 `initdb` автоматически запускает утилиту `pgpro_tune` (отключается `--no-tune`; `--tune=параметры` «устанавливает параметры для pgpro_tune»). Синтаксис: `pgpro_tune [параметр...] [-D | --pgdata] каталог имя_пресета`; ключи `-P имя`/`--preset=имя` (можно несколько, выполняются по порядку), `--preset-dir=каталог` (умолчание — каталог `share`), `--config-file=файл`, `--no-default`, `--default-options=...`, `-O`/`--options=...`, `--set имя=значение`, `--show`. Пресеты: `default.tune` (применяется первым, если нет `--no-default`), `1c.tune` (параметры для 1С, часть требует модуля `plantuner`), `extensions.tune`, `regress.tune`. Применить пресет к готовому кластеру: `sudo -u postgres /opt/pgpro/std-17/bin/pgpro_tune -D /путь/к/данным -P 1c.tune`, затем `SELECT pg_reload_conf();` или перезапуск; список пресетов — `pgpro_tune --show`. В примерах документации имена пресетов пишутся полностью, с расширением `.tune`.
- Уточнено 11.10.2026: в документации самой сборки «для 1С» версий 16 и 18 (`https://repo.postgrespro.ru/doc/pg1c/…/ru/html/app-pgpro-tune.html`) утилита `pgpro_tune` и пресет `1c.tune` описаны, а примера `--tune=1c` нет. Не подтверждена для версий 17–18 форма `pg-setup initdb --tune=1c --locale=ru_RU.UTF-8`, которая встречается в инструкциях к сборке «Postgres Pro 1С». Что известно точно: в документации Postgres Pro 12 синтаксис записан как `pg-setup initdb [--tune=конфигурация] [параметры_initdb]`; в документации версий 13, 14, 15 и 17 страница `pg-setup` показывает только `pg-setup initdb [параметры_initdb]`, а руководство по установке 17 и 18 по-прежнему говорит «аргумент `tune` команды `pg-setup initdb` выбирает вариант конфигурации базы данных», не приводя ни синтаксиса, ни значений. Безопасный порядок: создать кластер `pg-setup initdb`, затем посмотреть `pgpro_tune --show` и применить пресет явно (`-P 1c.tune`), после чего сравнить `pg_settings` до и после. Есть ли `pgpro_tune` в бесплатной сборке `postgrespro-1c-NN`, проверьте: `ls /opt/pgpro/1c-17/bin/ | grep -i tune`; страница 1c.postgres.ru обещает лишь, что параметры «подбираются автоматически под машину».
- В Postgres Pro провайдер локали по умолчанию выбирается по `lc_collate`: для `C`/`POSIX` — `libc`, для остальных — `icu`. В «ванильном» PostgreSQL умолчание `initdb` — `libc`.
- Метапакет `postgrespro-1c-NN` сам создаёт кластер и включает автозапуск. Документация Postgres Pro предупреждает: не ставьте метапакет при обновлении, миграции или когда на машине несколько инсталляций PostgreSQL — он может удалить существующие установки. В этих случаях ставьте `-server`, `-client`, `-libs`, `-contrib` по отдельности.

Условия использования бесплатной сборки «Postgres Pro 1С» (официально, 1c.postgres.ru): разрешено любое использование, кроме предоставления PostgreSQL как услуги (DBaaS) и встраивания в собственные продукты; поставляется «без гарантий и без технической поддержки», обновления могут отставать от основных веток.

`pg-wrapper` (официально) — делает программы Postgres Pro доступными в `PATH` и подключает man-страницы по SQL. Входит в клиентский пакет (`postgrespro-std-17-client`; для сборки 1С — `postgrespro-1c-17-client` по тому же шаблону). Запуск от `root`.

```bash
sudo /opt/pgpro/1c-17/bin/pg-wrapper links update    # создать или заменить ссылки на клиентские и серверные программы
sudo /opt/pgpro/1c-17/bin/pg-wrapper links remove    # убрать ссылки текущей версии
```

Если система поддерживает `update-alternatives`, ссылки добавляются в систему альтернатив, приоритеты между версиями меняются её средствами. Если не поддерживает и есть конфликт с другой установкой — `pg-wrapper` ссылки не создаёт и не меняет; тогда вызывайте программы по полному пути или правьте `PATH`.

## 7. Служебные утилиты сервера

В Debian-раскладке серверные утилиты не лежат в `PATH`: вызывайте их по полному пути `/usr/lib/postgresql/NN/bin/...`. В Postgres Pro — `/opt/pgpro/<редакция>-NN/bin/...` (или через ссылки после `pg-wrapper links update`). Утилиты, читающие каталог данных, запускаются от владельца кластера: `sudo -u postgres ...`.

### 7.1. initdb — создание кластера

Синтаксис: `initdb [опции] [--pgdata | -D] каталог`. Запускается от пользователя, который будет владельцем сервера; от `root` не работает. В Debian-раскладке вместо него используют `pg_createcluster`, в Postgres Pro — `pg-setup initdb`.

| Ключ | Смысл | Умолчание |
|---|---|---|
| `-D`, `--pgdata` | каталог кластера | `PGDATA` |
| `-E`, `--encoding` | кодировка шаблонных баз | выводится из локали |
| `--locale` | локаль кластера | из окружения |
| `--lc-collate`, `--lc-ctype`, `--lc-messages`, `--lc-monetary`, `--lc-numeric`, `--lc-time` | локаль отдельной категории | из окружения |
| `--no-locale` | то же, что `--locale=C` | |
| `--locale-provider={builtin\|libc\|icu}` | провайдер локали | `libc` (в Postgres Pro — см. 6.4) |
| `--icu-locale`, `--icu-rules`, `--builtin-locale` | локаль ICU, доп. правила, локаль встроенного провайдера | |
| `-k`, `--data-checksums` | контрольные суммы страниц данных | в PostgreSQL 18 включены по умолчанию; в 14–17 выключены |
| `--no-data-checksums` | отключить контрольные суммы (PostgreSQL 18) | |
| `-A`, `--auth` | метод аутентификации для `local` и `host` в `pg_hba.conf` (и для обычных, и для репликационных подключений) | `trust` |
| `--auth-local`, `--auth-host` | метод отдельно для сокета и для TCP | |
| `-U`, `--username` | имя суперпользователя | имя пользователя ОС |
| `-W`, `--pwprompt`; `--pwfile=файл` | задать пароль суперпользователя | |
| `-X`, `--waldir` | отдельный каталог для WAL | внутри каталога данных |
| `--wal-segsize` | размер сегмента WAL, МБ (степень двойки 1–1024) | 16 |
| `-g`, `--allow-group-access` | разрешить группе читать файлы кластера | только владелец |
| `-c имя=значение`, `--set` | применить параметр на время `initdb` и записать его в `postgresql.conf` (PostgreSQL 16+) | |
| `-T`, `--text-search-config` | конфигурация полнотекстового поиска | |
| `-N`, `--no-sync` | не ждать записи на диск (только для тестов) | |
| `--sync-method={fsync\|syncfs}` | способ сброса файлов на диск (есть в документации PostgreSQL 18; версия появления — 17, подтверждено замечаниями к выпуску PostgreSQL 17 (сверено 10.10.2026); ранее: версия появления не проверялась — по памяти, 17) | `fsync` |
| `-n`, `--no-clean` | не удалять файлы при сбое (для отладки) | |
| `--tune=параметры`, `--no-tune` | только Postgres Pro: параметры для `pgpro_tune` / не запускать её (см. 6.4) | автонастройка включена |

Версии, в которых появились ключи локали: `--locale-provider` и `--icu-locale` — PostgreSQL 15; `--icu-rules` — 16; значение `builtin` и `--builtin-locale` — 17.

Метод `trust` по умолчанию позволяет любому локальному пользователю подключиться без пароля — документация прямо предостерегает от него. Обёртки `pg_createcluster` и `pg-setup` ставят `peer` для сокета.

```bash
sudo install -d -o postgres -g postgres -m 700 /mnt/pgdata/manual
sudo -u postgres /usr/lib/postgresql/16/bin/initdb -D /mnt/pgdata/manual \
     --locale=ru_RU.UTF-8 --encoding=UTF8 --data-checksums \
     --auth-local=peer --auth-host=scram-sha-256
```

### 7.2. pg_isready — проверка готовности

Синтаксис: `pg_isready [-h хост] [-p порт] [-d база] [-U роль] [-t сек] [-q]`. Тайм-аут `-t` по умолчанию 3 с (0 — без ограничения). Учётные данные не проверяются: утилита показывает только, принимает ли сервер подключения.

| Код возврата | Смысл |
|---|---|
| 0 | сервер принимает подключения |
| 1 | сервер отвергает подключения (например, идёт запуск или восстановление) |
| 2 | нет ответа |
| 3 | попытка не выполнялась (например, неверные параметры) |

```bash
pg_isready -h 127.0.0.1 -p 5432
pg_isready -q -h 127.0.0.1 -p 5432 || echo "PostgreSQL не отвечает"
until pg_isready -q -h 127.0.0.1 -p 5432; do sleep 1; done   # дождаться запуска
```

### 7.3. pg_controldata — управляющая информация кластера

Синтаксис: `pg_controldata [-D] каталог_данных`. Печатает содержимое `pg_control`: состояние кластера (`in production`, `shut down`, `in archive recovery`), версию каталога, последнюю контрольную точку и её REDO-позицию, линию времени, размер блока и сегмента WAL, версию контрольных сумм страниц. Запускать может только пользователь, инициализировавший кластер.

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/pg_controldata /var/lib/postgresql/16/main
sudo -u postgres /usr/lib/postgresql/16/bin/pg_controldata /var/lib/postgresql/16/main | grep -E 'state|checkpoint location|TimeLineID|checksum'
```

То же из SQL: `SELECT * FROM pg_control_system();`, `pg_control_checkpoint()`, `pg_control_init()`, `pg_control_recovery()`.

### 7.4. pg_config — сведения об установке

Печатает каталоги и параметры сборки установленной версии. Где он лежит в Debian-раскладке (проверено по спискам файлов пакетов Ubuntu 24.04 на packages.ubuntu.com):

- `/usr/lib/postgresql/NN/bin/pg_config` — пакет `postgresql-client-NN` (то есть есть на любом сервере с PostgreSQL; пакет разработки для него не нужен);
- `/usr/bin/pg_config` — этот путь значится и в `libpq-dev`, и в `postgresql-common` (обёртка);
- `postgresql-server-dev-NN` самого `pg_config` не содержит — в нём только заголовочные файлы сервера и статические библиотеки.

Проверка на своём сервере: `dpkg -S pg_config`. В Postgres Pro `pg_config` лежит в `/opt/pgpro/<редакция>-NN/bin/`; по документации `pg-wrapper links update` может создать на него ссылку в стандартном каталоге программ (Уточнено 11.10.2026: документация сборки «для 1С», раздел 18.1.6.1, для вызова нужного `pg_config` при сборке своих пакетов велит добавлять зависимость от `postgrespro-1c-NN-dev`; прямой фразы «`pg_config` входит в пакет …» там нет — проверка: `dpkg -S /opt/pgpro/1c-17/bin/pg_config`).

| Ключ | Что печатает |
|---|---|
| `--bindir` | каталог пользовательских программ |
| `--libdir` | каталог библиотек |
| `--pkglibdir` | каталог загружаемых модулей сервера (расширения, `shared_preload_libraries`) |
| `--sharedir` | каталог вспомогательных файлов (в нём `extension/`) |
| `--sysconfdir` | каталог общесистемных настроек (`psqlrc`, `pg_service.conf`) |
| `--includedir`, `--includedir-server`, `--pkgincludedir` | заголовочные файлы |
| `--docdir`, `--htmldir`, `--mandir`, `--localedir` | документация, локализация |
| `--pgxs` | makefile для сборки расширений |
| `--configure` | параметры `configure`, с которыми собран сервер |
| `--cc`, `--cflags`, `--cppflags`, `--ldflags`, `--libs` | параметры компиляции |
| `--version` | версия PostgreSQL |

```bash
/usr/lib/postgresql/16/bin/pg_config --version --bindir --sharedir --pkglibdir
/opt/pgpro/1c-17/bin/pg_config --configure
```

### 7.5. pg_checksums — контрольные суммы страниц

Синтаксис: `pg_checksums [опции] [[-D | --pgdata] каталог]`. Проверяет, включает или отключает контрольные суммы. Сервер должен быть остановлен штатно.

| Ключ | Смысл |
|---|---|
| `-c`, `--check` | проверить (режим по умолчанию); код возврата 0, если ошибок нет |
| `-e`, `--enable` | включить: переписывает каждый блок с изменившейся суммой, на большом кластере долго |
| `-d`, `--disable` | отключить: меняет только `pg_control` |
| `-f`, `--filenode` | проверять только отношение с указанным filenode |
| `-P`, `--progress` | показывать ход выполнения |
| `-v`, `--verbose` | перечислять проверенные файлы |
| `-N`, `--no-sync` | не ждать записи на диск (только тесты) |

```bash
sudo systemctl stop postgresql@16-main
sudo -u postgres /usr/lib/postgresql/16/bin/pg_checksums --check -P -D /var/lib/postgresql/16/main
sudo -u postgres /usr/lib/postgresql/16/bin/pg_checksums --enable -P -D /var/lib/postgresql/16/main
sudo systemctl start postgresql@16-main
sudo -u postgres psql -c "SHOW data_checksums;"
```

Пока идёт включение, кластер запускать нельзя — возможна потеря данных. Если утилиту прервали, конфигурация контрольных сумм остаётся прежней, запуск можно повторить. В конфигурации с репликацией включайте или отключайте суммы согласованно на всех узлах при остановленных кластерах (или пересоздайте реплики).

### 7.6. pg_waldump — просмотр WAL

Синтаксис: `pg_waldump [опции] [начальный_сегмент [конечный_сегмент]]`. Отладочный инструмент; читать лучше архивные сегменты, потому что на работающем сервере вывод может оказаться неполным. Показывается только заданная линия времени.

| Ключ | Смысл |
|---|---|
| `-p`, `--path` | каталог с сегментами WAL или каталог, содержащий `pg_wal` |
| `-s`, `--start`; `-e`, `--end` | начальная и конечная позиции (LSN) |
| `-n`, `--limit` | показать N записей |
| `-r`, `--rmgr` | только записи менеджера ресурсов (`-r list` — список) |
| `-R`, `--relation` | только записи отношения `табл_простр/база/relfilenode` |
| `-B`, `--block`; `-F`, `--fork` | конкретный блок и слой (`main`, `fsm`, `vm`, `init`) |
| `-x`, `--xid` | только записи транзакции |
| `-t`, `--timeline` | линия времени |
| `-f`, `--follow` | дойдя до конца, ждать новые записи |
| `-b`, `--bkp-details`; `-w`, `--fullpage` | подробности образов страниц; только записи с образами |
| `-z`, `--stats[=record]` | сводная статистика вместо записей |
| `-q`, `--quiet` | ничего не печатать, кроме ошибок (проверка читаемости) |
| `--save-fullpage=каталог` | сохранить образы страниц в файлы |

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/pg_waldump -p /var/lib/postgresql/16/main/pg_wal -n 20 000000010000000000000001
sudo -u postgres /usr/lib/postgresql/16/bin/pg_waldump -z -p /var/lib/postgresql/16/main/pg_wal 000000010000000A00000010 000000010000000A00000020
```

Практическое применение: понять, какой менеджер ресурсов (`Heap`, `Btree`, `XLOG` с полными образами страниц) создаёт основной объём WAL.

### 7.7. pg_archivecleanup — очистка архива WAL

Синтаксис: `pg_archivecleanup [опции] каталог_архива самый_старый_нужный_файл`. Удаляет из архива все сегменты, логически предшествующие указанному. Рассчитан на использование в `archive_cleanup_command` резервного сервера и на ручной запуск.

| Ключ | Смысл |
|---|---|
| `-n`, `--dry-run` | только напечатать имена файлов, которые были бы удалены |
| `-d`, `--debug` | отладочный вывод в stderr |
| `-x расширение`, `--strip-extension` | отбросить расширение перед сравнением имён (например, `-x .gz` для сжатого архива) |
| `-b`, `--clean-backup-history` | удалять и файлы истории резервных копий (PostgreSQL 17+) |

Длинные формы `--debug`, `--dry-run`, `--strip-extension` появились в PostgreSQL 17 (примечания к выпуску); в 14–16 работают только короткие `-d`, `-n`, `-x`, а ключа `-b` нет. В Debian-раскладке `/usr/bin/pg_archivecleanup` — обёртка, запускающая программу самой новой установленной версии.

```bash
# postgresql.conf резервного сервера
#   archive_cleanup_command = 'pg_archivecleanup /mnt/standby/archive %r'

# вручную: сначала посмотреть, затем удалить всё старше сегмента из имени .backup-файла
pg_archivecleanup -n /backup/wal 000000010000003700000010.00000020.backup
pg_archivecleanup -d /backup/wal 000000010000003700000010.00000020.backup
```

Не применяйте `%r`-вариант к архиву долговременного хранения и к архиву, из которого восстанавливаются несколько резервных серверов.

### 7.8. pg_resetwal — сброс WAL (только как крайняя мера)

Синтаксис: `pg_resetwal [-f] [-n] [опции] [-D] каталог_данных`. Очищает WAL и при необходимости сбрасывает поля `pg_control`. По документации — применять только в последнюю очередь, когда сервер не запускается из-за повреждения WAL или управляющего файла.

Что нужно знать:

- После запуска на кластере с повреждённым WAL сервер, скорее всего, поднимется, но в базе могут остаться несогласованные данные из-за частично зафиксированных транзакций. Документация требует: немедленно выгрузить данные (`pg_dump`), выполнить `initdb` и восстановить; до выгрузки не выполнять операций, изменяющих данные.
- Сервер должен быть остановлен. Утилита откажется работать при наличии файла блокировки `postmaster.pid`; удалять его можно только убедившись, что ни одного серверного процесса не осталось.
- `-n`, `--dry-run` — показать, что будет изменено, ничего не меняя. Всегда начинайте с него.
- `-f`, `--force` — выполнить даже после нештатной остановки или при нечитаемом `pg_control`.
- Каталог данных задаётся только в командной строке, `PGDATA` не используется. Версия утилиты должна совпадать со старшей версией сервера.
- Остальные ключи (`-l`/`--next-wal-file`, `-x`/`--next-transaction-id`, `-o`/`--next-oid`, `-m`/`--multixact-ids`, `-O`/`--multixact-offset`, `-c`/`--commit-timestamp-ids`, `-e`/`--epoch`, `-u`/`--oldest-transaction-id`, `--wal-segsize`, в PostgreSQL 18 ещё `--char-signedness`) — ручная подстановка значений, нужна только когда их не удалось прочитать из `pg_control`.

Порядок действий при повреждении:

1. Остановить службу, убедиться, что процессов `postgres` нет.
2. Снять копию каталога данных на файловом уровне: `sudo rsync -a /var/lib/postgresql/16/main/ /backup/main.broken/`.
3. Попробовать штатные способы: восстановление из резервной копии, запуск с исправленной конфигурацией.
4. Только если их нет: `sudo -u postgres /usr/lib/postgresql/16/bin/pg_resetwal -n -D /var/lib/postgresql/16/main`, затем с `-f`.
5. Запустить сервер, ничего не изменяя, сделать `pg_dump` всех баз, создать новый кластер, восстановить, проверить данные (для 1С — «Тестирование и исправление» на копии).

## 8. Роли

В PostgreSQL «пользователь» и «группа» — одно понятие: роль. Роль с атрибутом `LOGIN` может подключаться. Роли общие для всего кластера, а не для базы.

### 8.1. CREATE / ALTER / DROP ROLE

```text
CREATE ROLE имя [ [ WITH ] атрибут [ ... ] ]
```

| Атрибут | Смысл | Умолчание |
|---|---|---|
| `LOGIN` / `NOLOGIN` | право подключаться | `NOLOGIN` (у `CREATE USER` — `LOGIN`) |
| `SUPERUSER` / `NOSUPERUSER` | обход всех проверок прав | `NOSUPERUSER` |
| `CREATEDB` / `NOCREATEDB` | право создавать базы | `NOCREATEDB` |
| `CREATEROLE` / `NOCREATEROLE` | право создавать, менять и удалять роли | `NOCREATEROLE` |
| `INHERIT` / `NOINHERIT` | наследование прав ролей, в которые входит | `INHERIT` |
| `REPLICATION` / `NOREPLICATION` | право на репликационное подключение и слоты | `NOREPLICATION` |
| `BYPASSRLS` / `NOBYPASSRLS` | обход политик защиты строк | `NOBYPASSRLS` |
| `CONNECTION LIMIT n` | максимум одновременных подключений (`-1` — без ограничения); к суперпользователям не применяется | `-1` |
| `PASSWORD 'пароль'` / `PASSWORD NULL` | пароль; `NULL` — парольная аутентификация для роли всегда неуспешна | нет пароля |
| `VALID UNTIL 'дата-время'` | срок действия пароля (только пароля, не роли; на peer и другие беспарольные методы не влияет) | бессрочно |
| `IN ROLE роль, ...` | включить новую роль в существующие | |
| `ROLE роль, ...` / `ADMIN роль, ...` | включить существующие роли в новую (с правом администрирования для `ADMIN`) | |

`CREATE USER` — то же, что `CREATE ROLE`, но с `LOGIN` по умолчанию. Пароль хранится в зашифрованном виде по методу из `password_encryption` (`scram-sha-256` по умолчанию с PostgreSQL 14); MD5 объявлен устаревшим. Команда `CREATE ROLE ... PASSWORD '...'` передаёт пароль открытым текстом — он может остаться в истории psql и в журнале сервера; безопаснее `\password` или `createuser -P`.

```sql
-- роль для сервера 1С
CREATE ROLE usr1c WITH LOGIN SUPERUSER PASSWORD 'S3cret';

-- после создания информационной базы привилегию можно отозвать (документация 1С: SUPERUSER нужен только в момент создания ИБ)
ALTER ROLE usr1c NOSUPERUSER;

-- роль с ограниченным сроком пароля и лимитом подключений
CREATE ROLE audit LOGIN PASSWORD 'Aud1t' VALID UNTIL '2027-01-01' CONNECTION LIMIT 3;

-- изменение атрибутов
ALTER ROLE usr1c CREATEDB;
ALTER ROLE usr1c PASSWORD 'N3wPass';
ALTER ROLE usr1c VALID UNTIL 'infinity';
ALTER ROLE audit NOLOGIN;                  -- заблокировать вход, не удаляя роль
ALTER ROLE audit RENAME TO auditor;

-- групповая роль
CREATE ROLE readers NOLOGIN;
GRANT readers TO auditor;

-- удаление
DROP ROLE IF EXISTS auditor;
```

- Официально (документация 1С, «Руководство администратора», создание информационной базы; конспект — `kb/its-docs/adm-gl05-spisok-infobaz.md`): привилегия `SUPERUSER` пользователю PostgreSQL нужна только в момент создания информационной базы, после успешного создания её можно отозвать; пример из документации — `alter user dbuser with nosuperuser;`.
- ⚠ практика (первоисточника нет): после `ALTER ROLE ... NOSUPERUSER` роль должна остаться владельцем базы и всех объектов в ней; создание следующей информационной базы этой же ролью снова потребует `SUPERUSER` (платформа создаёт в новой базе расширения и объекты, для которых нужны расширенные права), а без `CREATEDB` не сработает флажок «Создать базу данных в случае ее отсутствия». Многие оставляют роли сервера 1С `SUPERUSER`, ограничивая доступ средствами `pg_hba.conf`. Проверяйте на своей версии платформы и на копии: обновление конфигурации с реструктуризацией, загрузку из `.dt`, создание новой базы.
- Проверить метод хранения паролей (только суперпользователь):

```sql
SELECT rolname,
       CASE WHEN rolpassword LIKE 'SCRAM-SHA-256%' THEN 'scram-sha-256'
            WHEN rolpassword LIKE 'md5%'           THEN 'md5'
            WHEN rolpassword IS NULL               THEN 'нет пароля'
            ELSE 'другое' END AS password_type,
       rolvaliduntil
FROM pg_authid
WHERE rolcanlogin
ORDER BY rolname;
```

### 8.2. Удаление роли, владеющей объектами

`DROP ROLE` не сработает, пока роль чем-то владеет или имеет права. Порядок:

```sql
-- в КАЖДОЙ базе, где у роли есть объекты:
REASSIGN OWNED BY old_role TO postgres;   -- передать объекты текущей базы и общие объекты (базы, табличные пространства)
DROP OWNED BY old_role;                   -- снять оставшиеся права и права по умолчанию
-- затем один раз:
DROP ROLE old_role;
```

### 8.3. createuser / dropuser

Синтаксис: `createuser [параметры подключения] [опции] [имя]`.

| Ключ | Смысл |
|---|---|
| `-P`, `--pwprompt` | спросить пароль новой роли (на сервер уходит уже зашифрованным) |
| `-s`, `--superuser` / `-S` | суперпользователь / нет (умолчание — нет) |
| `-d`, `--createdb` / `-D` | право создавать базы / нет (умолчание — нет) |
| `-r`, `--createrole` / `-R` | право создавать роли / нет (умолчание — нет) |
| `-l`, `--login` / `-L` | право входа (умолчание — да) / нет |
| `-i`, `--inherit` / `-I` | наследование прав (умолчание — да) / нет |
| `-c n`, `--connection-limit` | лимит подключений |
| `-v дата`, `--valid-until` | срок действия пароля |
| `-g роль`, `--member-of` | включить новую роль в существующую |
| `-m роль`, `--with-member`; `-a роль`, `--with-admin` | включить существующую роль в новую |
| `--replication`, `--bypassrls` | соответствующие атрибуты |
| `--interactive` | спрашивать имя и недостающие атрибуты |
| `-e`, `--echo` | показать отправляемые команды SQL |
| `-h`, `-p`, `-U`, `-w`, `-W` | параметры подключения (здесь `-U` — под кем подключаться, а не кого создавать) |

Версии: ключи `-v`/`--valid-until`, `--bypassrls`/`--no-bypassrls`, `-m`/`--with-member`, `-a`/`--with-admin` и имя `--member-of` появились в PostgreSQL 16 (примечания к выпуску); в 14–15 включение в существующую роль записывается как `-g роль`/`--role=роль` (в 16+ `--role` устарел, но принимается). `--replication` и `--bypassrls` требуют подключения суперпользователем. Версия `createuser` в Debian-раскладке соответствует версии выбранного кластера (`pg_wrapper`).

```bash
sudo -u postgres createuser -P -s -e usr1c         # суперпользователь с запросом пароля, показать SQL
sudo -u postgres createuser -P -d backup           # роль с правом создавать базы
sudo -u postgres createuser --replication -P -e replicator
sudo -u postgres dropuser --if-exists backup
```

## 9. Базы данных

### 9.1. CREATE DATABASE

```text
CREATE DATABASE имя
    [ WITH ] [ OWNER [=] роль ]
           [ TEMPLATE [=] шаблон ]
           [ ENCODING [=] кодировка ]
           [ STRATEGY [=] стратегия ]
           [ LOCALE [=] локаль ]
           [ LC_COLLATE [=] lc_collate ]
           [ LC_CTYPE [=] lc_ctype ]
           [ BUILTIN_LOCALE [=] локаль ]
           [ ICU_LOCALE [=] локаль_icu ]
           [ ICU_RULES [=] правила ]
           [ LOCALE_PROVIDER [=] провайдер ]
           [ COLLATION_VERSION = версия ]
           [ TABLESPACE [=] табл_пространство ]
           [ ALLOW_CONNECTIONS [=] разрешить ]
           [ CONNECTION LIMIT [=] лимит ]
           [ IS_TEMPLATE [=] шаблон ]
           [ OID [=] oid ]
```

| Параметр | Смысл | Умолчание |
|---|---|---|
| `OWNER` | владелец базы | выполняющий команду |
| `TEMPLATE` | база-образец | `template1` |
| `ENCODING` | кодировка | как у шаблона |
| `STRATEGY` | `WAL_LOG` — копировать поблочно через WAL (эффективно для маленького шаблона); `FILE_COPY` — копировать каталоги на уровне файлов (намного меньше WAL, но контрольная точка до и после). PostgreSQL 15+ | `WAL_LOG` |
| `LOCALE` | задаёт сразу `LC_COLLATE` и `LC_CTYPE` | как у шаблона |
| `LC_COLLATE`, `LC_CTYPE` | порядок сортировки и классификация символов | как у шаблона |
| `LOCALE_PROVIDER` | `libc`, `icu`, `builtin` (PostgreSQL 15+; `builtin` — 17+) | как у шаблона |
| `ICU_LOCALE`, `ICU_RULES`, `BUILTIN_LOCALE` | локаль соответствующего провайдера | |
| `TABLESPACE` | табличное пространство по умолчанию | как у шаблона |
| `ALLOW_CONNECTIONS` | `false` — к базе не может подключиться никто | `true` |
| `CONNECTION LIMIT` | максимум одновременных подключений; соблюдается приблизительно, к суперпользователям и фоновым процессам не применяется | `-1` |
| `IS_TEMPLATE` | `true` — клонировать может любой с `CREATEDB`; `false` — только суперпользователь или владелец | `false` |

Ограничения:

- Команду нельзя выполнять внутри блока транзакции.
- Кодировка и локаль должны совпадать с шаблоном, кроме случая `TEMPLATE template0`. Поэтому базу с другой локалью создают от `template0`.
- Кодировка должна соответствовать локали (для `C`/`POSIX` допустима любая).
- К шаблону не должно быть других подключений: `CREATE DATABASE` завершится ошибкой, если они есть; на время копирования новые подключения к шаблону блокируются.
- Настройки уровня базы (`ALTER DATABASE ... SET`) и права (`GRANT ... ON DATABASE`) из шаблона не копируются.

```sql
CREATE DATABASE test OWNER usr1c;

-- явная русская локаль (если кластер создан с другой)
CREATE DATABASE buh_test
    OWNER usr1c
    TEMPLATE template0
    ENCODING 'UTF8'
    LC_COLLATE 'ru_RU.UTF-8'
    LC_CTYPE 'ru_RU.UTF-8';

-- на отдельном табличном пространстве, с лимитом подключений
CREATE DATABASE arch OWNER usr1c TABLESPACE slow_hdd CONNECTION LIMIT 20;
```

Базу для 1С обычно создаёт сама платформа (флажок «Создать базу данных в случае ее отсутствия» при добавлении информационной базы в кластер). Требования 1С к имени базы (документация 1С, конспект `kb/its-docs/adm-gl05-spisok-infobaz.md`): первый символ — буква или `_`, далее буквы, `_`, `$`; длина до 63 символов; без пробелов; не зарезервированное слово. Цифры в этом перечне документации для PostgreSQL не названы, но на практике имена вида `buh30` используются повсеместно (PostgreSQL цифры в идентификаторах, кроме первой позиции, допускает). Нестандартный порт в поле «Сервер баз данных» задаётся так: `localhost port=6432;`.

### 9.2. Копирование базы через TEMPLATE

```sql
-- к исходной базе не должно быть подключений
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = 'buh' AND pid <> pg_backend_pid();

CREATE DATABASE buh_copy TEMPLATE buh OWNER usr1c;                        -- любая версия
CREATE DATABASE buh_copy TEMPLATE buh OWNER usr1c STRATEGY = FILE_COPY;   -- PostgreSQL 15+: быстрее для большой базы
```

- Для базы в десятки гигабайт стратегия `WAL_LOG` (умолчание с версии 15) создаёт очень большой объём WAL; `FILE_COPY` копирует файлы и пишет в WAL только короткие записи, но делает две контрольные точки. В PostgreSQL 14 и старше копирование всегда файловое.
- В PostgreSQL 18 на способ копирования влияет параметр `file_copy_method`.
- Для базы 1С: предварительно запретите сеансы и регламентные задания в кластере 1С, иначе рабочие процессы переподключатся и `CREATE DATABASE` упадёт с ошибкой `source database "buh" is being accessed by other users`. Копию зарегистрируйте в кластере 1С как новую информационную базу и не забудьте про блокировку регламентных заданий в ней.

### 9.3. ALTER DATABASE

```text
ALTER DATABASE имя [ WITH ] ALLOW_CONNECTIONS значение | CONNECTION LIMIT число | IS_TEMPLATE значение
ALTER DATABASE имя RENAME TO новое_имя
ALTER DATABASE имя OWNER TO { новый_владелец | CURRENT_ROLE | CURRENT_USER | SESSION_USER }
ALTER DATABASE имя SET TABLESPACE новое_табл_пространство
ALTER DATABASE имя REFRESH COLLATION VERSION
ALTER DATABASE имя SET параметр { TO | = } { значение | DEFAULT }
ALTER DATABASE имя RESET параметр | RESET ALL
```

```sql
ALTER DATABASE buh OWNER TO usr1c;
ALTER DATABASE buh CONNECTION LIMIT 100;
ALTER DATABASE buh WITH ALLOW_CONNECTIONS false;     -- закрыть базу для всех
ALTER DATABASE buh WITH ALLOW_CONNECTIONS true;
ALTER DATABASE buh SET work_mem = '64MB';            -- умолчание параметра для новых сеансов этой базы
ALTER DATABASE buh RESET work_mem;
```

Переименование:

```sql
-- выполнять, подключившись к ДРУГОЙ базе (например, postgres); в переименовываемой не должно быть сеансов
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'buh_old';
ALTER DATABASE buh_old RENAME TO buh_new;
```

- Текущую базу переименовать нельзя (официально). Переименовывать может владелец с правом `CREATEDB` или суперпользователь.
- Если в базе есть другие сеансы, команда завершится ошибкой `database "..." is being accessed by other users` (поведение сервера; в тексте справки по `ALTER DATABASE` это требование отдельно не оговорено).
- После переименования поменяйте имя базы данных в свойствах информационной базы в кластере 1С, иначе платформа будет искать старое имя.

### 9.4. DROP DATABASE

```text
DROP DATABASE [ IF EXISTS ] имя [ [ WITH ] ( FORCE ) ]
```

- Нельзя выполнять внутри блока транзакции и будучи подключённым к удаляемой базе (подключайтесь к `postgres`).
- `WITH (FORCE)` (PostgreSQL 13+) пытается завершить все подключения к базе. Не сработает, если в базе есть подготовленные транзакции, активные слоты логической репликации или подписки, либо если останутся сеансы, которые текущий пользователь завершить не вправе.
- Удаление необратимо.

```sql
DROP DATABASE IF EXISTS buh_copy;
DROP DATABASE buh_copy WITH (FORCE);
```

### 9.5. createdb / dropdb

`createdb [параметры подключения] [опции] [имя [описание]]`:

| Ключ | Смысл |
|---|---|
| `-O роль`, `--owner` | владелец |
| `-T шаблон`, `--template` | шаблон |
| `-E кодировка`, `--encoding` | кодировка |
| `-l локаль`, `--locale` | локаль (задаёт `--lc-collate`, `--lc-ctype`, `--icu-locale`) |
| `--lc-collate`, `--lc-ctype` | отдельные категории |
| `--locale-provider={builtin\|libc\|icu}`, `--icu-locale`, `--icu-rules`, `--builtin-locale` | провайдер локали и его параметры |
| `-D табл_простр`, `--tablespace` | табличное пространство по умолчанию |
| `-S стратегия`, `--strategy` | стратегия создания (`wal_log`, `file_copy`); PostgreSQL 15+ |
| `--maintenance-db база` | к какой базе подключаться для выполнения команды (умолчание `postgres`, затем `template1`) |
| `-e`, `--echo` | показать отправляемый SQL |

`dropdb [параметры подключения] [опции] имя`: `-f`, `--force` — завершить подключения к базе перед удалением; `-i`, `--interactive` — запросить подтверждение; `--if-exists` — не считать ошибкой отсутствие базы; `-e` — показать SQL; `--maintenance-db`.

```bash
sudo -u postgres createdb -O usr1c -T template0 -E UTF8 -l ru_RU.UTF-8 -e buh_test
sudo -u postgres createdb -O usr1c -T buh -S file_copy buh_copy
sudo -u postgres dropdb --if-exists -f -e buh_copy
```

## 10. Права, схемы, владельцы

### 10.1. Виды прав и их обозначения

| Право | Буква в ACL | К чему применяется |
|---|---|---|
| `SELECT` | `r` | таблицы, столбцы, последовательности, большие объекты |
| `INSERT` | `a` | таблицы, столбцы |
| `UPDATE` | `w` | таблицы, столбцы, последовательности |
| `DELETE` | `d` | таблицы |
| `TRUNCATE` | `D` | таблицы |
| `REFERENCES` | `x` | таблицы, столбцы |
| `TRIGGER` | `t` | таблицы |
| `MAINTAIN` | `m` | таблицы: `VACUUM`, `ANALYZE`, `CLUSTER`, `REINDEX`, `REFRESH MATERIALIZED VIEW`, `LOCK TABLE` (PostgreSQL 17+) |
| `CREATE` | `C` | базы (создание схем, установка доверенных расширений), схемы (создание объектов), табличные пространства |
| `CONNECT` | `c` | базы |
| `TEMPORARY` | `T` | базы (создание временных таблиц) |
| `EXECUTE` | `X` | функции, процедуры |
| `USAGE` | `U` | схемы, последовательности, языки, типы |
| `SET` | `s` | параметры конфигурации |
| `ALTER SYSTEM` | `A` | параметры конфигурации |

Чтение записи ACL (вывод `\dp`, `\l`, `\dn+`): `получатель=права/кто_выдал`. Пример: `miriam=arwdDxtm/miriam` — у `miriam` права INSERT, SELECT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN, выданные `miriam` (владельцем). Пустой получатель — `PUBLIC`: `=r/miriam`. Звёздочка после буквы — право с возможностью передачи (`WITH GRANT OPTION`).

Права, которые есть у `PUBLIC` по умолчанию: на базы — `CONNECT` и `TEMPORARY` (`Tc`); на функции и процедуры — `EXECUTE`; на языки и типы — `USAGE`. На таблицы, последовательности, схемы, табличные пространства и параметры — никаких. С PostgreSQL 15 у `PUBLIC` нет права `CREATE` в схеме `public`; схемой `public` владеет встроенная роль `pg_database_owner`, единственный неявный член которой — владелец текущей базы.

### 10.2. GRANT / REVOKE

```sql
-- база
GRANT CONNECT ON DATABASE buh TO auditor;
REVOKE CONNECT ON DATABASE buh FROM PUBLIC;          -- запретить вход всем, кому право не выдано явно (владельца и суперпользователей не касается)
REVOKE TEMPORARY ON DATABASE buh FROM PUBLIC;

-- схема
GRANT USAGE ON SCHEMA public TO auditor;
GRANT CREATE ON SCHEMA public TO developer;

-- таблицы
GRANT SELECT ON ALL TABLES IN SCHEMA public TO auditor;
GRANT SELECT, INSERT, UPDATE, DELETE ON mytable TO app;
GRANT SELECT (col1), UPDATE (col1) ON mytable TO limited;
REVOKE ALL ON mytable FROM PUBLIC;

-- последовательности и функции
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app;

-- права на будущие объекты, которые создаст роль usr1c
ALTER DEFAULT PRIVILEGES FOR ROLE usr1c IN SCHEMA public GRANT SELECT ON TABLES TO auditor;

-- членство в ролях
GRANT readers TO auditor;
GRANT pg_monitor TO zabbix;
REVOKE readers FROM auditor;

-- параметры (PostgreSQL 15+)
GRANT SET ON PARAMETER log_min_duration_statement TO auditor;
GRANT ALTER SYSTEM ON PARAMETER work_mem TO dba_junior;
```

Чтобы роль могла читать таблицу, нужны три вещи: `CONNECT` на базу, `USAGE` на схему и `SELECT` на таблицу.

### 10.3. Предопределённые роли

| Роль | Что даёт |
|---|---|
| `pg_read_all_data` | чтение всех таблиц, представлений, последовательностей, как при `SELECT` на них и `USAGE` на все схемы; политики RLS не обходит (PostgreSQL 14+) |
| `pg_write_all_data` | запись во все таблицы (`INSERT`, `UPDATE`, `DELETE`) и `USAGE` на все схемы |
| `pg_read_all_settings` | чтение всех параметров, в том числе видимых только суперпользователю |
| `pg_read_all_stats` | чтение всех представлений `pg_stat_*` |
| `pg_stat_scan_tables` | функции мониторинга, берущие блокировки `ACCESS SHARE` на таблицах |
| `pg_monitor` | объединяет три предыдущие; для систем мониторинга |
| `pg_signal_backend` | отмена запросов и завершение чужих сеансов (кроме сеансов суперпользователя) |
| `pg_signal_autovacuum_worker` | отмена текущей очистки таблицы или завершение процесса автоочистки (PostgreSQL 18+) |
| `pg_read_server_files`, `pg_write_server_files`, `pg_execute_server_program` | доступ к файлам и программам на сервере через `COPY` и файловые функции; фактически путь к правам суперпользователя, выдавать крайне осторожно |
| `pg_checkpoint` | выполнение `CHECKPOINT` |
| `pg_maintain` | `VACUUM`, `ANALYZE`, `CLUSTER`, `REINDEX` и т.д. на всех отношениях |
| `pg_use_reserved_connections` | использование слотов из `reserved_connections` |
| `pg_create_subscription` | создание подписок при наличии `CREATE` на базу |
| `pg_database_owner` | неявно — владелец текущей базы |

```sql
GRANT pg_signal_backend TO admin_user;
GRANT pg_read_all_data TO auditor;
```

### 10.4. Схемы

```sql
CREATE SCHEMA audit AUTHORIZATION auditor;
ALTER SCHEMA audit OWNER TO postgres;
ALTER SCHEMA audit RENAME TO audit_old;
DROP SCHEMA audit_old CASCADE;            -- вместе со всеми объектами
SHOW search_path;                         -- по умолчанию "$user", public
SET search_path TO audit, public;
ALTER ROLE auditor SET search_path = audit, public;
```

Платформа 1С создаёт все свои таблицы в схеме `public`. Свои вспомогательные объекты (таблицы отчётов, представления для мониторинга) держите в отдельной схеме или в отдельной базе, чтобы они не мешали реструктуризации и не попадали под «Тестирование и исправление».

### 10.5. Смена владельца

```sql
ALTER DATABASE buh OWNER TO usr1c;
ALTER SCHEMA public OWNER TO usr1c;
ALTER TABLE mytable OWNER TO usr1c;
ALTER TABLESPACE fast_ssd OWNER TO usr1c;

-- все объекты одной роли в текущей базе — другой роли
REASSIGN OWNED BY old_owner TO usr1c;
```

Смена владельца базы не меняет владельцев объектов внутри неё. Если базу 1С восстановили под другой ролью, выполните в этой базе `REASSIGN OWNED BY старая_роль TO новая_роль;` — иначе при реструктуризации появятся ошибки `must be owner of table`.

Массовая смена владельца всех таблиц схемы через `\gexec`:

```sql
SELECT format('ALTER TABLE %I.%I OWNER TO usr1c', schemaname, tablename)
FROM pg_tables WHERE schemaname = 'public' \gexec
```

## 11. Табличные пространства

Табличное пространство — именованный каталог файловой системы, в котором сервер хранит файлы объектов. Применение: вынести базу или тяжёлые таблицы на другой диск, вынести временные файлы на быстрый диск.

Главное предупреждение документации: табличные пространства — неотъемлемая часть кластера, их нельзя рассматривать как самостоятельный набор файлов. Их нельзя подключить к другому кластеру или резервировать по отдельности; потеря табличного пространства (удаление файлов, отказ диска) может сделать кластер нечитаемым или незапускаемым. Размещать их на временных файловых системах (RAM-диск) нельзя.

### 11.1. Создание

```bash
sudo install -d -o postgres -g postgres -m 700 /mnt/ssd1/pg_tblspc
```

```sql
CREATE TABLESPACE fast_ssd OWNER usr1c LOCATION '/mnt/ssd1/pg_tblspc';
GRANT CREATE ON TABLESPACE fast_ssd TO usr1c;
```

Требования: каталог существует, пуст и принадлежит пользователю ОС `postgres`; создавать может только суперпользователь; команду нельзя выполнять в блоке транзакции. В каталоге данных появится символическая ссылка `pg_tblspc/<oid>`. Встроенные пространства: `pg_default` (умолчание для `template0`/`template1` и, значит, для новых баз) и `pg_global` (общие системные каталоги).

### 11.2. Использование и перенос

```sql
-- новая база сразу в пространстве
CREATE DATABASE arch TABLESPACE slow_hdd;

-- перенос всей базы: к базе не должно быть подключений, выполнять из другой базы
ALTER DATABASE buh SET TABLESPACE fast_ssd;

-- перенос одной таблицы (блокировка ACCESS EXCLUSIVE на время копирования; индексы НЕ переносятся)
ALTER TABLE _accumrg1234 SET TABLESPACE fast_ssd;
ALTER INDEX имя_индекса SET TABLESPACE fast_ssd;      -- имена индексов таблицы: \di+ _accumrg1234*

-- перенос всех таблиц и индексов текущей базы из одного пространства в другое
ALTER TABLE ALL IN TABLESPACE pg_default SET TABLESPACE fast_ssd;
ALTER INDEX ALL IN TABLESPACE pg_default SET TABLESPACE fast_ssd;

-- умолчание для новых объектов сеанса и для временных объектов
SET default_tablespace = fast_ssd;
ALTER SYSTEM SET temp_tablespaces = 'fast_tmp';
SELECT pg_reload_conf();
```

- `ALTER DATABASE ... SET TABLESPACE` физически переносит таблицы и индексы из старого пространства по умолчанию в новое. Новое пространство должно быть пустым для этой базы. Объекты в других пространствах не затрагиваются. Нельзя выполнять в блоке транзакции.
- `ALTER TABLE ALL IN TABLESPACE` системные каталоги не переносит — для них `ALTER DATABASE`.
- Для 1С (по документации 8.3.27 («Клиент-серверный вариант», гл. 3; сверено 11.10.2026) платформа сама размещает данные в табличном пространстве `v81c_data`, а индексы — в `v81c_index`, если пространства с такими именами существуют, иначе использует `pg_default`; дальнейшее — практика, не подтверждено документацией): при реструктуризации платформа создаёт таблицы заново, и они оказываются в пространстве по умолчанию базы — ручной перенос отдельных таблиц «слетает». Надёжнее переносить базу целиком.
- У платформы 1С есть собственный механизм размещения таблиц и индексов по табличным пространствам: в статье ИТС 1798 (редакция для 8.3.27) описаны служебные таблицы `_DbSegments` (имя и путь к каталогу на сервере СУБД) и `_DbSegmentsItems` (что куда размещено, отдельно данные и индексы). Если он используется, распределением управляет платформа — не переносите такие таблицы вручную. **Уточнено 11.10.2026** (документация 8.3.27, «Руководство администратора», разд. 1.6.3.3): «использование пользовательских табличных пространств» входит в перечень возможностей, недоступных с серверной лицензией ПРОФ, то есть механизм требует лицензии КОРП. Порядок настройки описан в «Клиент-серверном варианте», разд. 5.5.5.2 (конспект — `../its-docs/cs-gl05-administrirovanie-klastera-p3.md`): свойство конфигурации «Режим использования табличных пространств», стандартная функция «Управление табличными пространствами базы данных» и механизм тестирования и исправления; чтобы создавать пространства, пользователь СУБД в PostgreSQL должен иметь атрибут `SUPERUSER`. Версия появления не уточнялась. Ранее было: Как именно механизм настраивается и с какой версии и лицензии доступен, в прочитанных материалах не описано.
- Вынос временных объектов через `temp_tablespaces` на быстрый диск рекомендует документация Postgres Pro для 1С (приложение K.3, подтверждено): сначала `CREATE TABLESPACE`, затем `temp_tablespaces = 'имя'`; если характеристики дисков отличаются от основных — задайте для пространства свой `random_page_cost`: `ALTER TABLESPACE fast_tmp SET (random_page_cost = 1.1);`. Пространство для временных объектов — такая же часть кластера: если каталог пропадёт (например, это был RAM-диск), запросы с временными таблицами начнут падать. Роли, от имени которой работает сервер 1С, нужно право `CREATE` на это пространство (`GRANT CREATE ON TABLESPACE fast_tmp TO usr1c;`), если она не суперпользователь: по документации PostgreSQL пространства из заранее заданного `temp_tablespaces`, на которые у роли нет права `CREATE`, молча пропускаются — временные таблицы останутся в пространстве по умолчанию.

### 11.3. Просмотр и удаление

```sql
SELECT spcname, spcowner::regrole AS owner, pg_tablespace_location(oid) AS location,
       pg_size_pretty(pg_tablespace_size(oid)) AS size
FROM pg_tablespace;

-- какие базы хранят объекты в пространстве
SELECT d.datname FROM pg_database d
WHERE d.oid IN (SELECT pg_tablespace_databases(t.oid) FROM pg_tablespace t WHERE t.spcname = 'fast_ssd');

DROP TABLESPACE fast_ssd;     -- только когда в нём нет объектов ни одной базы
```

В psql: `\db+`.

## 12. Конфигурация «на лету»

### 12.1. Откуда берётся значение параметра (в порядке возрастания приоритета)

1. Встроенное умолчание.
2. `postgresql.conf` и подключённые из него файлы (`include`, `include_if_exists`, `include_dir`). В `include_dir` читаются только файлы `*.conf`, не начинающиеся с точки, в порядке имён по правилам локали C (цифры раньше букв, заглавные раньше строчных). Если параметр встречается несколько раз — действует последнее вхождение.
3. `postgresql.auto.conf` (пишет `ALTER SYSTEM`) — перекрывает `postgresql.conf`.
4. Параметры командной строки `postgres -c имя=значение` — перекрывают файлы и `ALTER SYSTEM`.
5. `ALTER DATABASE ... SET`, `ALTER ROLE ... SET`, `ALTER ROLE ... IN DATABASE ... SET` — применяются при открытии нового сеанса; настройка роли сильнее настройки базы.
6. `SET` в сеансе, `SET LOCAL` в транзакции, `PGOPTIONS` на стороне клиента.

Правила записи в файле: один параметр в строке, `=` необязателен, `#` — комментарий, строки в одинарных кавычках, единицы памяти `B`, `kB`, `MB`, `GB`, `TB` (множитель 1024), времени `us`, `ms`, `s`, `min`, `h`, `d`. Имена единиц чувствительны к регистру.

### 12.2. SHOW / SET / RESET

```sql
SHOW work_mem;
SHOW ALL;
SELECT current_setting('work_mem');
SELECT current_setting('нет.такого', true);          -- второй аргумент true: вернуть NULL вместо ошибки

SET work_mem = '128MB';                               -- до конца сеанса
SET LOCAL statement_timeout = '30s';                  -- до конца транзакции
SELECT set_config('work_mem', '128MB', false);        -- функция-аналог SET (true — как SET LOCAL)
RESET work_mem;
RESET ALL;
```

### 12.3. ALTER SYSTEM

```text
ALTER SYSTEM SET параметр { TO | = } { значение [, ...] | DEFAULT }
ALTER SYSTEM RESET параметр
ALTER SYSTEM RESET ALL
```

- Пишет в `postgresql.auto.conf` в каталоге данных. `RESET` или `SET ... DEFAULT` удаляет запись, и снова действует значение из `postgresql.conf`.
- Вступает в силу после перечитывания конфигурации (`pg_reload_conf()`, `pg_ctl reload`, SIGHUP), а для параметров, задаваемых только при старте, — после перезапуска.
- Нельзя выполнять в блоке транзакции и в функции. Нельзя задать `data_directory` и `allow_alter_system`.
- Права: суперпользователь или роль с `GRANT ALTER SYSTEM ON PARAMETER`.
- Параметр `allow_alter_system = off` (PostgreSQL 17+) отключает команду; по документации это не механизм безопасности, а защита от случайных правок там, где конфигурацией управляет внешняя система.

```sql
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET log_min_duration_statement = '5s';
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';   -- требует перезапуска
SELECT pg_reload_conf();
ALTER SYSTEM RESET work_mem;
```

Если после `ALTER SYSTEM` сервер не запускается (неверное значение параметра уровня `postmaster`): остановите службу, откройте `postgresql.auto.conf` в каталоге данных, удалите или исправьте строку, запустите сервер. Это обычный текстовый файл.

В Debian-раскладке есть два места для постоянных настроек — `/etc/postgresql/NN/main/conf.d/*.conf` и `postgresql.auto.conf`. Выберите одно. Типичная путаница: значение правят в `postgresql.conf`, а действует старое из `postgresql.auto.conf`. Диагностика — столбцы `source`, `sourcefile`, `sourceline` в `pg_settings`.

### 12.4. Настройки на уровне базы и роли

```sql
ALTER DATABASE buh SET maintenance_work_mem = '1GB';
ALTER ROLE auditor SET statement_timeout = '60s';
ALTER ROLE auditor SET default_transaction_read_only = on;
ALTER ROLE usr1c IN DATABASE buh SET work_mem = '128MB';
ALTER ROLE auditor RESET ALL;
```

Действуют только для новых сеансов. Посмотреть: `\drds` или

```sql
SELECT coalesce(d.datname, '(все базы)') AS database,
       coalesce(r.rolname, '(все роли)') AS role,
       unnest(s.setconfig) AS setting
FROM pg_db_role_setting s
LEFT JOIN pg_database d ON d.oid = s.setdatabase
LEFT JOIN pg_roles r ON r.oid = s.setrole;
```

### 12.5. Перечитывание конфигурации

```sql
SELECT pg_reload_conf();          -- true, если сигнал отправлен
SELECT pg_conf_load_time();       -- когда конфигурация последний раз перечитана
```

```bash
sudo systemctl reload postgresql@16-main
sudo pg_ctlcluster 16 main reload
sudo -u postgres /opt/pgpro/1c-17/bin/pg_ctl -D /var/lib/pgpro/1c-17/data reload
```

При перечитывании неверные значения игнорируются (с записью в журнал), сервер продолжает работать со старыми. Параметры уровня `postmaster` при `reload` не меняются.

### 12.6. Представление pg_settings

Столбцы: `name`, `setting`, `unit`, `category`, `short_desc`, `extra_desc`, `context`, `vartype`, `source`, `min_val`, `max_val`, `enumvals`, `boot_val`, `reset_val`, `sourcefile`, `sourceline`, `pending_restart`.

| `context` | Когда можно изменить |
|---|---|
| `internal` | нельзя: значение определено при сборке или `initdb` |
| `postmaster` | только при запуске сервера — нужен перезапуск |
| `sighup` | в файле конфигурации + `reload` |
| `superuser-backend` | в файле + `reload` либо при подключении (суперпользователь); в уже открытом сеансе не меняется |
| `backend` | в файле + `reload` либо при подключении (любой пользователь); в открытом сеансе не меняется |
| `superuser` | в файле либо `SET` в сеансе (суперпользователь или роль с правом `SET` на параметр) |
| `user` | в файле либо `SET` в сеансе (любой пользователь) |

```sql
-- что требует перезапуска и что уже ждёт его
SELECT name, setting, context FROM pg_settings WHERE context = 'postmaster' ORDER BY name;
SELECT name, setting FROM pg_settings WHERE pending_restart;

-- параметры, отличные от умолчаний, с указанием источника
SELECT name, setting, unit, source, sourcefile, sourceline
FROM pg_settings
WHERE source NOT IN ('default', 'override')
ORDER BY source, name;

-- узнать единицу измерения и допустимые границы
SELECT name, setting, unit, min_val, max_val, boot_val FROM pg_settings WHERE name = 'shared_buffers';
```

### 12.7. Проверка файлов до перечитывания: pg_file_settings и pg_hba_file_rules

Оба представления показывают текущее содержимое файлов на диске, а не то, что загружено в сервер, поэтому ими проверяют правки до `reload`. По умолчанию доступны только суперпользователю.

`pg_file_settings`: `sourcefile`, `sourceline`, `seqno`, `name`, `setting`, `applied`, `error`.

```sql
SELECT sourcefile, sourceline, name, setting, applied, error
FROM pg_file_settings
WHERE error IS NOT NULL OR NOT applied;
```

- `error` не пусто — реальная проблема (неверное значение, или параметр нельзя менять без перезапуска).
- `applied = false` при пустом `error` — запись перекрыта более поздней записью того же параметра, это не ошибка.
- Если в файле синтаксическая ошибка или неизвестное имя параметра, сервер не применит из него ничего: у всех строк `applied = false`.

`pg_hba_file_rules` (PostgreSQL 16+): `rule_number`, `file_name`, `line_number`, `type`, `database`, `user_name`, `address`, `netmask`, `auth_method`, `options`, `error`. В PostgreSQL 14 и 15 столбцов `rule_number` и `file_name` нет (подтверждено документацией 15 и примечаниями к выпуску 16) — порядок правил там задаёт `line_number`.

```sql
-- PostgreSQL 16+
SELECT rule_number, line_number, type, database, user_name, address, netmask, auth_method, error
FROM pg_hba_file_rules
ORDER BY rule_number NULLS FIRST;

-- PostgreSQL 14–15 (работает и в более новых)
SELECT line_number, type, database, user_name, address, netmask, auth_method, error
FROM pg_hba_file_rules
ORDER BY line_number;

-- любая версия
SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;
```

С PostgreSQL 16 в `pg_hba.conf` и `pg_ident.conf` можно подключать другие файлы (`include`, `include_if_exists`, `include_dir`); столбец `file_name` показывает, из какого файла взято правило.

Для `pg_ident.conf` есть аналог — `pg_ident_file_mappings` (PostgreSQL 15+).

## 13. Сеансы

### 13.1. Представление pg_stat_activity

Одна строка на каждый серверный процесс.

| Столбец | Смысл |
|---|---|
| `datid`, `datname` | OID и имя базы |
| `pid` | идентификатор серверного процесса (он же — PID процесса ОС) |
| `leader_pid` | PID ведущего процесса для параллельных исполнителей |
| `usesysid`, `usename` | OID и имя роли |
| `application_name` | имя приложения, которое сообщил клиент |
| `client_addr`, `client_hostname`, `client_port` | адрес клиента; `client_addr` пуст для Unix-сокета и внутренних процессов; `client_port = -1` для сокета |
| `backend_start` | когда процесс запущен (для клиента — момент подключения) |
| `xact_start` | начало текущей транзакции или `NULL` |
| `query_start` | начало текущего запроса, а если сеанс не активен — последнего |
| `state_change` | момент последней смены состояния |
| `wait_event_type`, `wait_event` | чего ждёт процесс (`Lock`, `LWLock`, `IO`, `Client`, `Activity` и т.д.) или `NULL` |
| `state` | состояние (см. ниже) |
| `backend_xid` | идентификатор транзакции верхнего уровня, если назначен |
| `backend_xmin` | горизонт `xmin` процесса — удерживает очистку более новых «мёртвых» строк |
| `query_id` | идентификатор запроса (нужен `compute_query_id` или `pg_stat_statements`) |
| `query` | текст запроса: при `active` — выполняемого, иначе — последнего. Обрезается по `track_activity_query_size` (умолчание 1024 байта) |
| `backend_type` | тип процесса: `client backend`, `autovacuum launcher`, `autovacuum worker`, `background writer`, `checkpointer`, `walwriter`, `walsender`, `walreceiver`, `archiver`, `startup`, `parallel worker`, `logical replication launcher`, `logical replication worker`, `walsummarizer`, `standalone backend` |

Значения `state`:

| Значение | Смысл |
|---|---|
| `active` | выполняет запрос |
| `idle` | ждёт команду клиента |
| `idle in transaction` | транзакция открыта, запрос не выполняется |
| `idle in transaction (aborted)` | то же, но в транзакции была ошибка |
| `fastpath function call` | выполняет функцию по быстрому пути |
| `disabled` | у процесса выключен `track_activities` |
| `starting` | процесс на начальной стадии запуска, идёт аутентификация (есть в документации PostgreSQL 18) |

Чужие запросы видны только суперпользователю и членам `pg_read_all_stats` / `pg_monitor`; остальным в `query` показывается `<insufficient privilege>`.

Сеансы сервера 1С выглядят так: `usename` — роль из свойств информационной базы, `client_addr` — адрес сервера 1С, много сеансов в состоянии `idle` (пул соединений рабочих процессов `rphost`). ⚠ не подтверждено: значение `application_name` у соединений платформы. По памяти автора и рецензента в `pg_stat_activity` и в префиксе журнала (`%a`) встречается `1CV8Server`; в соседнем файле `kb/postgresql/06-monitoring-i-diagnostika-zaprosov.md` названо `1CV8` — первоисточника нет ни у одного варианта (в «Списке изменений» платформы 8.3.27–8.5.4 упоминаний `application_name` не найдено). Не стройте на этом значении фильтры и правила, пока не посмотрите его у себя: `SELECT application_name, count(*) FROM pg_stat_activity WHERE backend_type = 'client backend' GROUP BY 1;`. Имени пользователя 1С и номера сеанса 1С в `pg_stat_activity` нет: сопоставить соединение СУБД с сеансом 1С можно по PID серверного процесса: он равен свойству `dbpid` событий `DBPOSTGRS` технологического журнала и полю `db-proc-info` в `rac session list` («Соединение с СУБД» в консоли кластера). Связь действует, только пока сеанс удерживает соединение из пула (идёт вызов СУБД, открыта транзакция или есть временные таблицы); подробности — в `kb/postgresql/06-monitoring-i-diagnostika-zaprosov.md`.

### 13.2. Отмена запроса и завершение сеанса

| Функция | Действие |
|---|---|
| `pg_cancel_backend(pid)` | отменить текущий запрос сеанса (сигнал SIGINT); сеанс и транзакция остаются, транзакция переходит в состояние ошибки |
| `pg_terminate_backend(pid [, timeout])` | завершить сеанс (SIGTERM). `timeout` в миллисекундах (PostgreSQL 14+): при значении больше 0 функция ждёт завершения и возвращает `false` с предупреждением, если не дождалась |

Права: суперпользователь; роль — член роли-владельца сеанса; член `pg_signal_backend` (кроме сеансов суперпользователей).

```sql
SELECT pg_cancel_backend(12345);
SELECT pg_terminate_backend(12345);
SELECT pg_terminate_backend(12345, 5000);     -- ждать завершения до 5 секунд

-- отменить все запросы, работающие дольше 30 минут
SELECT pid, pg_cancel_backend(pid)
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '30 minutes'
  AND backend_type = 'client backend' AND pid <> pg_backend_pid();

-- завершить «зависшие в транзакции» дольше часа
SELECT pid, pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state LIKE 'idle in transaction%' AND now() - state_change > interval '1 hour';
```

Не используйте `kill -9` для серверных процессов: postmaster воспримет это как аварию, прервёт все сеансы и запустит восстановление. Допустимы только `pg_cancel_backend` / `pg_terminate_backend` (или `kill -INT` / `kill -TERM` для отдельного процесса-сеанса).

Автоматические ограничители (параметры сеанса, можно задать для роли или базы): `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`, `idle_session_timeout` (PostgreSQL 14+), `transaction_timeout` (PostgreSQL 17+). Для роли сервера 1С их не ставьте: платформа держит простаивающие соединения в пуле и выполняет длительные операции.

### 13.3. Отключить всех от базы перед DROP, RENAME, RESTORE, копированием

```sql
-- 1. подключиться к другой базе
\c postgres

-- 2. запретить новые подключения (выберите один способ)
ALTER DATABASE buh WITH ALLOW_CONNECTIONS false;    -- не сможет подключиться никто, включая суперпользователя
-- ALTER DATABASE buh CONNECTION LIMIT 0;            -- не действует на суперпользователей
-- REVOKE CONNECT ON DATABASE buh FROM PUBLIC;       -- не действует на владельца и суперпользователей

-- 3. завершить существующие сеансы
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'buh' AND pid <> pg_backend_pid();

-- 4. выполнить операцию
-- DROP DATABASE buh;   /  ALTER DATABASE buh RENAME TO buh_old;  /  CREATE DATABASE buh_copy TEMPLATE buh;

-- 5. вернуть доступ
ALTER DATABASE buh WITH ALLOW_CONNECTIONS true;
```

- При `ALLOW_CONNECTIONS false` к базе не подключится и `pg_dump`, и `pg_restore`. Для восстановления поверх базы удобнее `CONNECTION LIMIT 0` + работа от суперпользователя либо удаление и создание базы заново.
- Для базы 1С начните с кластера 1С: установите блокировку начала сеансов и блокировку регламентных заданий для информационной базы (консоль администрирования или `rac infobase update ... --sessions-deny=on --scheduled-jobs-deny=on`), завершите сеансы 1С. Иначе рабочие процессы тут же откроют новые соединения, и шаг 3 придётся повторять.
- Короткий путь для удаления: `DROP DATABASE buh WITH (FORCE);` или `dropdb -f buh`.

### 13.4. Сколько подключений и чьи

```sql
SELECT datname, usename, application_name, client_addr, state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1, 2, 3, 4, 5
ORDER BY count(*) DESC;

SELECT count(*) AS used,
       current_setting('max_connections')::int AS max_connections,
       current_setting('superuser_reserved_connections')::int AS reserved
FROM pg_stat_activity
WHERE backend_type = 'client backend';
```

## 14. Размеры и инвентаризация

### 14.1. Функции размеров

| Функция | Что возвращает |
|---|---|
| `pg_database_size(имя или oid)` | полный размер базы, байт |
| `pg_tablespace_size(имя или oid)` | размер табличного пространства |
| `pg_relation_size(отношение [, слой])` | размер одного слоя отношения; слой по умолчанию `main` (ещё `fsm`, `vm`, `init`). Для таблицы — только «куча», без индексов и TOAST |
| `pg_table_size(таблица)` | таблица с TOAST, картами свободного места и видимости, без индексов |
| `pg_indexes_size(таблица)` | все индексы таблицы |
| `pg_total_relation_size(таблица)` | таблица + индексы + TOAST; равно `pg_table_size + pg_indexes_size` |
| `pg_column_size(значение)` | байт на хранение значения (с учётом сжатия) |
| `pg_size_pretty(число)` | человекочитаемый вид: `bytes`, `kB`, `MB`, `GB`, `TB`, `PB` (степени 1024) |
| `pg_size_bytes('1 GB')` | обратное преобразование |
| `pg_relation_filepath(отношение)` | путь к файлу отношения относительно каталога данных |

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT pg_size_pretty(pg_total_relation_size('_inforg12345'));
SELECT pg_relation_filepath('config');
```

### 14.2. Базы по размеру

```sql
SELECT d.datname,
       pg_get_userbyid(d.datdba) AS owner,
       pg_encoding_to_char(d.encoding) AS encoding,
       d.datcollate, d.datctype,
       pg_size_pretty(pg_database_size(d.oid)) AS size
FROM pg_database d
ORDER BY pg_database_size(d.oid) DESC;
```

### 14.3. Топ таблиц и индексов текущей базы

```sql
-- 20 самых больших таблиц: всего, куча, индексы, TOAST и служебные слои, оценка числа строк
SELECT c.oid::regclass AS table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       pg_size_pretty(pg_relation_size(c.oid)) AS heap,
       pg_size_pretty(pg_indexes_size(c.oid)) AS indexes,
       pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid) - pg_indexes_size(c.oid)) AS toast_and_maps,
       c.reltuples::bigint AS est_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'm')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname !~ '^pg_toast'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;

-- 20 самых больших индексов и сколько раз их использовали
SELECT s.schemaname, s.relname AS table_name, s.indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size,
       s.idx_scan
FROM pg_stat_user_indexes s
ORDER BY pg_relation_size(s.indexrelid) DESC
LIMIT 20;
```

### 14.4. Оценка числа строк

`SELECT count(*)` на большой таблице читает её целиком. Быстрая оценка — из статистики:

```sql
SELECT c.reltuples::bigint AS est_rows, c.relpages
FROM pg_class c WHERE c.oid = '_document123'::regclass;

SELECT relname, n_live_tup, n_dead_tup, last_analyze, last_autoanalyze
FROM pg_stat_user_tables WHERE relname = '_document123';
```

`reltuples` обновляют `VACUUM`, `ANALYZE` и некоторые DDL; значение `-1` означает, что таблицу ещё ни разу не анализировали (PostgreSQL 14+).

### 14.5. Версии, расширения, общая инвентаризация

```sql
SELECT version();
SHOW server_version;
SHOW server_version_num;
SELECT pg_postmaster_start_time(), now() - pg_postmaster_start_time() AS uptime;
SELECT current_database(), current_user, session_user, inet_server_addr(), inet_server_port();

-- установленные расширения текущей базы
SELECT e.extname, e.extversion, n.nspname AS schema
FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
ORDER BY e.extname;

-- расширения, доступные для установки, и что уже установлено
SELECT name, default_version, installed_version, comment
FROM pg_available_extensions
ORDER BY name;

-- роли
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolreplication, rolconnlimit, rolvaliduntil
FROM pg_roles WHERE rolname !~ '^pg_' ORDER BY rolname;

-- число объектов по типам
SELECT CASE c.relkind WHEN 'r' THEN 'таблица' WHEN 'i' THEN 'индекс' WHEN 'S' THEN 'последовательность'
                      WHEN 'v' THEN 'представление' WHEN 't' THEN 'TOAST' ELSE c.relkind::text END AS kind,
       count(*)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
GROUP BY 1 ORDER BY 2 DESC;
```

```bash
psql --version
sudo -u postgres psql -X -At -c "SHOW server_version"
dpkg -l | grep -E 'postgres|pgpro'        # установленные пакеты и их версии
pg_lsclusters                             # Debian-раскладка
```

## 15. Журналы сервера

### 15.1. Параметры (официально, значения по умолчанию PostgreSQL 18)

| Параметр | Умолчание | Смысл |
|---|---|---|
| `log_destination` | `stderr` | куда писать: список из `stderr`, `csvlog`, `jsonlog`, `syslog` |
| `logging_collector` | `off` | фоновый сборщик: перехватывает stderr и пишет в файлы. Меняется только при запуске сервера. Для `csvlog` и `jsonlog` обязателен |
| `log_directory` | `log` | каталог файлов сборщика; относительный путь — от каталога данных |
| `log_filename` | `postgresql-%Y-%m-%d_%H%M%S.log` | шаблон имени (формат `strftime`) |
| `log_file_mode` | `0600` | права на файлы журнала |
| `log_rotation_age` | `24h` | новый файл через указанное время; `0` — отключить |
| `log_rotation_size` | `10MB` | новый файл по достижении размера; `0` — отключить |
| `log_truncate_on_rotation` | `off` | при ротации по времени перезаписывать существующий файл с тем же именем, а не дописывать |
| `log_line_prefix` | `'%m [%p] '` | префикс каждой строки |
| `log_timezone` | задаёт `initdb` | часовой пояс меток времени в журнале |
| `log_min_messages` | `WARNING` | минимальный уровень сообщений в журнале |
| `log_min_error_statement` | `ERROR` | с какого уровня записывать текст оператора, вызвавшего ошибку |
| `log_min_duration_statement` | `-1` | записывать операторы длительнее N мс; `0` — все; `-1` — отключено |
| `log_statement` | `none` | `none`, `ddl`, `mod`, `all` |
| `log_duration` | `off` | длительность каждого оператора |
| `log_checkpoints` | `on` | контрольные точки (умолчание `on` — с PostgreSQL 15; в 14 — `off`) |
| `log_connections` | выключено | подключения; в PostgreSQL 18 — список стадий (`receipt`, `authentication`, `authorization`, `setup_durations`, `all`), значения `on`/`off` тоже принимаются |
| `log_disconnections` | `off` | отключения с длительностью сеанса |
| `log_lock_waits` | `off` | ожидания блокировки дольше `deadlock_timeout` |
| `log_lock_failures` | `off` | неудачные попытки взять блокировку (`SELECT ... NOWAIT`); PostgreSQL 18+ |
| `log_temp_files` | `-1` | временные файлы размером от N кБ; `0` — все |
| `log_autovacuum_min_duration` | `10min` | действия автоочистки длительнее заданного; `0` — все (умолчание `10min` — с PostgreSQL 15; в 14 — `-1`, то есть отключено) |
| `log_error_verbosity` | `DEFAULT` | `TERSE`, `DEFAULT`, `VERBOSE` |
| `log_hostname` | `off` | писать имя хоста клиента (обратный DNS-запрос на каждое подключение) |

Подстановки `log_line_prefix`: `%m` — время с миллисекундами, `%t` — время без миллисекунд, `%n` — время в формате Unix, `%p` — PID, `%u` — роль, `%d` — база, `%a` — имя приложения, `%h` — адрес клиента, `%r` — адрес и порт клиента, `%L` — локальный адрес сервера, на который пришло подключение (есть в документации 18), `%b` — тип процесса, `%P` — PID ведущего процесса параллельной группы, `%i` — тег команды, `%e` — код SQLSTATE, `%c` — идентификатор сеанса, `%l` — номер строки журнала в сеансе, `%s` — время старта процесса, `%v` — виртуальный идентификатор транзакции, `%x` — идентификатор транзакции, `%Q` — идентификатор запроса, `%q` — для внесеансовых процессов остановить вывод префикса здесь, `%%` — знак процента.

### 15.2. Где смотреть в Ubuntu

| Сборка | Где журнал | Ротация |
|---|---|---|
| Debian-раскладка (умолчание) | `/var/log/postgresql/postgresql-NN-main.log` — stderr сервера, перенаправленный обёрткой; `logging_collector = off` | `logrotate`: `/etc/logrotate.d/postgresql-common` — для `/var/log/postgresql/*.log`: `weekly`, `rotate 10`, `copytruncate`, `delaycompress`, `compress`, `notifempty`, `missingok`, `su root root` (подтверждено исходным файлом пакета) |
| Debian-раскладка, `logging_collector = on` | `<каталог данных>/log/` либо каталог из `log_directory` | средствами PostgreSQL (`log_rotation_*`); `logrotate` эти файлы не трогает |
| Postgres Pro | `<каталог данных>/log/postgresql-<дата>_<время>.log` — Подтверждено 11.10.2026 чтением пакета `postgrespro-1c-16-server` 16.14-1.noble: `pg-setup initdb` создаёт каталог `log` в каталоге данных и записывает в `postgresql.conf` `logging_collector = on`; остальные параметры — умолчания (`log_directory = 'log'`, `log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'`). Сообщения до запуска сборщика уходят в журнал systemd | `log_rotation_age = 1d`, `log_rotation_size = 10MB`; **старые файлы сами не удаляются** — нужна своя очистка |
| Любая | сообщения systemd о запуске и остановке: `journalctl -u <служба>` | journald |

Как узнать точно:

```sql
SHOW logging_collector;
SHOW log_destination;
SHOW log_directory;
SHOW log_filename;
SELECT pg_current_logfile();               -- NULL, если сборщик выключен
SELECT * FROM pg_ls_logdir() ORDER BY modification DESC LIMIT 5;   -- файлы в log_directory
```

```bash
sudo tail -f /var/log/postgresql/postgresql-16-main.log
sudo grep -E 'ERROR|FATAL|PANIC' /var/log/postgresql/postgresql-16-main.log | tail -50
sudo zgrep -h 'FATAL' /var/log/postgresql/postgresql-16-main.log.*.gz | tail
sudo ls -lt /var/lib/pgpro/1c-17/data/log/ | head
journalctl -u postgresql@16-main --since "1 hour ago"
journalctl -u postgrespro-1c-17 -n 100 --no-pager
pg_lsclusters            # последний столбец — файл журнала кластера
```

В Debian-раскладке умолчание `log_line_prefix` задаётся в `createcluster.conf` и включает метку времени, PID и «роль@база» (состав подтверждён исходным файлом пакета; точная строка — по памяти рецензента `'%m [%p] %q%u@%d '`, сверьте: `grep log_line_prefix /etc/postgresql/NN/main/postgresql.conf`). Файл журнала создаётся с режимом `0640`, владелец — владелец кластера (`postgres`), группа — `adm` (подтверждено исходным кодом `pg_createcluster` и `pg_ctlcluster`: группа `adm` ставится для кластеров системных пользователей). Чтобы читать журнал без `sudo`, пользователя добавляют в группу `adm`: `sudo usermod -aG adm admin` (в Ubuntu первый пользователь, созданный установщиком, обычно уже в ней). Проверка — `ls -l /var/log/postgresql/`.

Следствие ротации с `copytruncate`: `logrotate` копирует файл и обрезает исходный, не трогая сервер, поэтому PostgreSQL перезапускать или уведомлять не нужно; несколько строк, записанных между копированием и обрезкой, могут потеряться. Ротация раз в неделю с хранением 10 файлов — около 10 недель истории. При включённом подробном журналировании (`log_min_duration_statement`, `log_statement`) недельный файл может вырасти на гигабайты — следите за `/var/log` или смените в `/etc/logrotate.d/postgresql-common` `weekly` на `daily` (и добавьте, например, `maxsize 1G`).

### 15.3. Типовые настройки журналирования

```sql
ALTER SYSTEM SET log_min_duration_statement = '5s';   -- запросы дольше 5 секунд
ALTER SYSTEM SET log_lock_waits = on;                 -- ожидания блокировок дольше deadlock_timeout (1 с)
ALTER SYSTEM SET log_temp_files = '100MB';            -- крупные временные файлы
ALTER SYSTEM SET log_autovacuum_min_duration = '1s';
ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d %a %h ';
SELECT pg_reload_conf();
```

Все перечисленные параметры применяются перечитыванием конфигурации. `log_min_duration_statement = 0` и `log_statement = 'all'` на рабочей базе 1С за считаные часы дают гигабайты журнала — включайте кратковременно и следите за местом на диске.

Собственная ротация PostgreSQL с недельным циклом (семь файлов, перезапись по кругу; приём из документации):

```text
logging_collector = on                 # требует перезапуска
log_directory = 'log'
log_filename = 'postgresql-%a.log'     # Mon, Tue, ...
log_truncate_on_rotation = on
log_rotation_age = 1d
log_rotation_size = 0
```

Принудительно начать новый файл: `SELECT pg_rotate_logfile();` (только при включённом сборщике).

## 16. Перенос каталога данных, смена порта, второй кластер

### 16.1. Перенос каталога данных на другой диск

Самый надёжный способ — смонтировать новый диск в прежнюю точку (`/var/lib/postgresql` или `/var/lib/pgpro`): пути в конфигурации и юнитах не меняются. Если нужен именно новый путь, порядок такой.

Debian-раскладка (кластер 16/main, новый путь `/mnt/pgdata/16/main`):

```bash
# 1. убедиться, что путь тот, и остановить кластер
sudo -u postgres psql -X -At -c "SHOW data_directory"
sudo systemctl stop postgresql@16-main
pg_lsclusters                                   # статус down

# 2. скопировать с сохранением владельцев, прав, жёстких ссылок, ACL и расширенных атрибутов
sudo install -d -o postgres -g postgres -m 700 /mnt/pgdata/16/main
sudo rsync -aHAX --info=progress2 /var/lib/postgresql/16/main/ /mnt/pgdata/16/main/

# 3. проверить владельца и права (каталог данных: postgres, 0700 или 0750)
sudo chown -R postgres:postgres /mnt/pgdata
sudo chmod 700 /mnt/pgdata/16/main
sudo -u postgres ls /mnt/pgdata/16/main/PG_VERSION

# 4. указать новый путь
sudo pg_conftool 16 main set data_directory /mnt/pgdata/16/main

# 5. старый каталог не удалять, а переименовать до проверки
sudo mv /var/lib/postgresql/16/main /var/lib/postgresql/16/main.old

# 6. запустить и проверить
sudo systemctl start postgresql@16-main
pg_lsclusters
sudo -u postgres psql -X -At -c "SHOW data_directory"

# 7. после проверки баз
sudo rm -rf /var/lib/postgresql/16/main.old
```

Пояснения:

- Косые черты в конце путей `rsync` обязательны: копируется содержимое каталога, а не сам каталог внутрь нового.
- `rsync -a` сохраняет права, владельцев, время и символические ссылки; `-H` — жёсткие ссылки, `-A` — ACL, `-X` — расширенные атрибуты. Копировать нужно при остановленном сервере.
- Родительские каталоги нового пути должны быть доступны пользователю `postgres` хотя бы на проход (`x`): `namei -l /mnt/pgdata/16/main` покажет права по всей цепочке.
- Табличные пространства — отдельные каталоги; ссылки на них лежат в `pg_tblspc/` и после копирования продолжают указывать на прежние места. Если переносите и их, при остановленном сервере скопируйте каталог и пересоздайте ссылку, либо до переноса выполните `ALTER DATABASE ... SET TABLESPACE`.
- Если WAL вынесен (`initdb -X`), `pg_wal` — символическая ссылка; `rsync -a` скопирует ссылку, а не содержимое.
- Юнит `postgresql@.service` ждёт монтирования только своих штатных каталогов — `/etc/postgresql/<версия>/<кластер>` и `/var/lib/postgresql/<версия>/<кластер>` (директива `RequiresMountsFor`, подтверждено исходным файлом юнита `postgresql-common` 278). О новом пути systemd не знает. Чтобы сервер не стартовал раньше, чем смонтирован новый диск, добавьте зависимость: `sudo systemctl edit postgresql@16-main` и в открывшемся файле

```ini
[Unit]
RequiresMountsFor=/mnt/pgdata
```

- AppArmor: в штатных пакетах PostgreSQL для Ubuntu профиля AppArmor для `postgres` нет (в отличие, например, от MySQL), поэтому правка профиля при переносе не требуется. Подтверждено списками файлов пакетов на packages.ubuntu.com: в `postgresql-16` и `postgresql-common` (24.04) и в `postgresql-18` (26.04) нет ни одного файла в `/etc/apparmor.d`; для 22.04 и для сборок 1С / Postgres Pro список не читался, но оснований ждать иного нет. Проверка на своём сервере: `sudo aa-status | grep -i postgres` (пустой вывод — профиля нет). Если профиль есть (сторонняя сборка, собственная политика), добавьте в него новый путь и выполните `sudo systemctl reload apparmor`; отказы видны в `sudo journalctl -k | grep -i 'apparmor.*DENIED'`.
- Проверка, что каталог после копирования цел, до запуска сервера: `sudo -u postgres /usr/lib/postgresql/16/bin/pg_controldata /mnt/pgdata/16/main | grep -E 'state|checkpoint location'` — состояние должно быть `shut down`.
- После правки `data_directory` систему обёрток перечитывать не нужно: `pg_lsclusters` и `pg_ctlcluster` каждый раз читают путь из `postgresql.conf`. Если добавляли `RequiresMountsFor` — файл drop-in применяется после `sudo systemctl daemon-reload` (`systemctl edit` делает это сам).
- Альтернатива правке `data_directory` — новый кластер в нужном месте (`pg_createcluster -d /mnt/pgdata/16/main ...`) и перенос баз через `pg_dump`/`pg_restore`. Дольше, зато заодно убирает раздувание таблиц.

Postgres Pro (каталог `/var/lib/pgpro/1c-17/data`):

```bash
sudo systemctl stop postgrespro-1c-17
sudo install -d -o postgres -g postgres -m 700 /mnt/pgdata/1c-17/data
sudo rsync -aHAX --info=progress2 /var/lib/pgpro/1c-17/data/ /mnt/pgdata/1c-17/data/
systemctl cat postgrespro-1c-17 | grep -iE 'PGDATA|EnvironmentFile|ExecStart'   # как юнит узнаёт каталог данных
cat /etc/default/postgrespro-1c-17
# поправить путь к каталогу данных в /etc/default/postgrespro-1c-17 (его используют pg-setup и служба)
sudo mv /var/lib/pgpro/1c-17/data /var/lib/pgpro/1c-17/data.old
sudo systemctl start postgrespro-1c-17
sudo -u postgres psql -X -At -c "SHOW data_directory"
```

Подтверждено 11.10.2026 чтением пакета `postgrespro-1c-16-server` 16.14-1.noble: файл `/etc/default/postgrespro-1c-NN` — файл окружения из одной строки `PGDATA=<каталог>` (путь с пробелами `pg-setup` берёт в кавычки, но юнит предупреждает, что пробелы в пути ломают `pg-setup`); юнит подключает его как `EnvironmentFile` и запускает `postgres -D ${PGDATA}`. Туда же можно дописать `PG_OOM_ADJUST_VALUE=<число>` и `ENABLE_ONLINE_UPGRADE=1` (тогда установка обновления пакета не перезапускает сервер автоматически). Прежний текст: точный формат файла `/etc/default/postgrespro-1c-NN` и имя переменной в нём. Документация (руководство по установке Postgres Pro 17 и 18) говорит, что `pg-setup initdb` сохраняет в этом файле путь к каталогу данных, что «любые команды, управляющие службой, будут нацелены именно на эту базу данных» и что в том же файле можно изменить `PG_OOM_ADJUST_VALUE`. Отсюда следует, что это файл окружения вида `ИМЯ=значение`; по памяти рецензента путь записан как `PGDATA=/var/lib/pgpro/1c-17/data` — проверьте `cat /etc/default/postgrespro-1c-17` и `systemctl cat postgrespro-1c-17`. Запасной вариант, не зависящий от формата: оставить пути как есть и смонтировать новый диск в `/var/lib/pgpro`.

Ещё один документированный путь для Postgres Pro — создать кластер сразу в нужном месте: `pg-setup initdb` принимает параметры `initdb`, в том числе `-D` / `--pgdata` (Подтверждено 11.10.2026 по тексту скрипта `pg-setup` из пакета `postgrespro-1c-16-server` 16.14: путь из `-D` / `--pgdata` записывается в `/etc/default/postgrespro-1c-NN` как `PGDATA=<путь>`, но **только если этого файла ещё нет**; если файл уже есть и указывает на другой каталог, скрипт отказывается работать и советует вызывать `initdb` напрямую и настраивать службу вручную. Каталог должен быть пустым. На сервере не выполнялось — после выполнения проверьте содержимое файла), затем перенести базы через `pg_dump`/`pg_restore`.

### 16.2. Смена порта

```bash
# Debian-раскладка
sudo pg_conftool 16 main set port 5433
sudo systemctl restart postgresql@16-main
pg_lsclusters

# Postgres Pro
sudo /opt/pgpro/1c-17/bin/pg-setup set-server-port 5433
sudo systemctl restart postgrespro-1c-17

# проверка
sudo ss -tlnp | grep postgres
sudo -u postgres psql -p 5433 -X -At -c "SHOW port"
```

- `port` — параметр уровня `postmaster`, нужен перезапуск.
- От порта зависит имя файла сокета: `/var/run/postgresql/.s.PGSQL.5433`. Локальные клиенты должны указывать `-p 5433` или `PGPORT`.
- Не задавайте порт через `ALTER SYSTEM` в Debian-раскладке: обёртка `pg_wrapper` может не прочитать `postgresql.auto.conf` и подключаться не туда.
- В свойствах информационной базы 1С поле «Сервер баз данных» принимает вид `имя_или_адрес port=5433;`.
- Откройте новый порт в брандмауэре (`sudo ufw allow from <адрес сервера 1С> to any port 5433 proto tcp`) и поправьте скрипты резервного копирования и мониторинга.

### 16.3. Второй кластер на том же сервере

Зачем: тестовая копия на другой версии, изоляция баз с разными настройками памяти, отдельный диск.

Debian-раскладка:

```bash
sudo pg_createcluster -p 5433 --locale ru_RU.UTF-8 --start 16 test
pg_lsclusters
systemctl status postgresql@16-test
sudo -u postgres psql -p 5433
sudo -u postgres psql --cluster 16/test
sudoedit /etc/postgresql/16/test/postgresql.conf      # своя конфигурация
sudo systemctl restart postgresql@16-test
sudo pg_dropcluster --stop 16 test                    # удалить со всеми данными
```

Postgres Pro: второй экземпляр создаётся вручную. Порядок из документации (руководство по установке, раздел о нескольких экземплярах): 1) установить Postgres Pro; 2) запустить `initdb` с другим каталогом данных; 3) задать разные порты в `postgresql.conf` экземпляров; 4) для автозапуска создать копию `/lib/systemd/system/postgrespro-std-17.service` (или `/etc/init.d/postgrespro-std-17`) под другим именем, поменять в ней путь к каталогу данных и включить автозапуск штатными средствами (`systemctl enable <имя копии>`), а не через `pg-setup`. Готового юнита-шаблона, как в Debian-раскладке, нет. Копию кладите в `/etc/systemd/system/` — файлы в `/lib/systemd/system` перезаписываются при обновлении пакета.

```bash
sudo install -d -o postgres -g postgres -m 700 /var/lib/pgpro/1c-17/data2
sudo -u postgres /opt/pgpro/1c-17/bin/initdb -D /var/lib/pgpro/1c-17/data2 \
     --locale=ru_RU.UTF-8 --auth-local=peer --auth-host=scram-sha-256
echo "port = 5433" | sudo -u postgres tee -a /var/lib/pgpro/1c-17/data2/postgresql.conf
systemctl cat postgrespro-1c-17        # взять за образец для /etc/systemd/system/postgrespro-1c-17-second.service
```

Каждому кластеру нужны: свой каталог данных, свой порт, своя доля памяти (`shared_buffers` суммируются), свои задания резервного копирования. Общих ролей и баз у кластеров нет.

## 17. Расширения

### 17.1. Основное

- Расширение ставится в конкретную базу командой `CREATE EXTENSION`. Файлы расширения (`имя.control`, `имя--версия.sql`, библиотека `.so`) должны быть на сервере: `SHAREDIR/extension` и `PKGLIBDIR` (их показывает `pg_config --sharedir --pkglibdir`). В PostgreSQL 18 путь поиска управляющих файлов задаётся параметром `extension_control_path`.
- Debian-раскладка: `/usr/share/postgresql/NN/extension/`, `/usr/lib/postgresql/NN/lib/`. Модули contrib входят в серверный пакет `postgresql-NN` (подтверждено списками файлов `postgresql-16` для 24.04 и `postgresql-18` для 26.04: в них есть `pg_stat_statements.so` и `pg_stat_statements.control`); пакет `postgresql-contrib` — метапакет-зависимость. ⚠ не подтверждено для пакетов «PostgreSQL с патчем от 1С»; проверка — `ls /usr/share/postgresql/NN/extension/*.control`.
- Postgres Pro: `/opt/pgpro/1c-NN/share/extension/`, `/opt/pgpro/1c-NN/lib/`; contrib — пакет `postgrespro-1c-NN-contrib`, серверный пакет от него зависит.
- Права: обычно нужен суперпользователь. Расширение, помеченное в управляющем файле как доверенное (trusted), может установить любой пользователь с правом `CREATE` на базу.
- Часть модулей должна быть загружена при старте сервера через `shared_preload_libraries` (список через запятую; изменение требует перезапуска). Одного `CREATE EXTENSION` для них недостаточно.

```text
CREATE EXTENSION [ IF NOT EXISTS ] имя [ WITH ] [ SCHEMA схема ] [ VERSION версия ] [ CASCADE ]
```

```sql
SELECT name, default_version, installed_version FROM pg_available_extensions ORDER BY name;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION pgstattuple SCHEMA public;
ALTER EXTENSION pg_stat_statements UPDATE;            -- до версии по умолчанию
ALTER EXTENSION pg_stat_statements UPDATE TO '1.11';  -- до конкретной версии
DROP EXTENSION pgstattuple;
\dx
\dx+ mchar
```

### 17.2. Пример: pg_stat_statements

```sql
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
```

```bash
sudo systemctl restart postgresql@16-main
```

```sql
SHOW shared_preload_libraries;
\c buh
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT calls, round(total_exec_time::numeric) AS total_ms, round(mean_exec_time::numeric, 2) AS mean_ms,
       rows, left(query, 100) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

`ALTER SYSTEM SET shared_preload_libraries` заменяет весь список. Если там уже есть модули, перечислите все: `'plantuner, pg_stat_statements'`. Опечатка в имени библиотеки не даст серверу запуститься — правьте `postgresql.auto.conf` вручную (см. 12.3).

### 17.3. Модули для 1С (официально: документация Postgres Pro, приложение «Настройка Postgres Pro для решений 1С»)

| Модуль | Назначение | Подключение |
|---|---|---|
| `mchar` | типы `MCHAR` и `MVARCHAR` для совместимости с Microsoft SQL Server | встроен, включён по умолчанию |
| `fulleq` | дополнительный оператор равенства для совместимости с MS SQL Server | встроен, включён по умолчанию |
| `fasttrun` | транзакционно-небезопасная функция усечения временных таблиц, не дающая расти `pg_class` | встроен, включён по умолчанию |
| `dbcopies_decoding` | обновление копий баз данных 1С; для логической репликации нужен `wal_level = logical` | включён по умолчанию |
| `plantuner` | улучшает планы для недавно созданных пустых таблиц | `shared_preload_libraries = 'plantuner'`, `plantuner.fix_empty_table = on` |
| `online_analyze` | немедленное обновление статистики после изменения данных | с современными версиями 1С использовать не рекомендуется; при необходимости — `shared_preload_libraries = 'online_analyze'`, `online_analyze.enable = on`, `online_analyze.table_type = 'temporary'` и др. |
| `pg_hint_plan` | указания планировщику | `pg_hint_plan.hints_anywhere = on` — читать указания `/*+ ... */` из любой части запроса. Есть только в Postgres Pro Standard/Enterprise, в бесплатной «PostgreSQL для 1С» 16.14 его нет (уточнено 19.10.2026) |
| `auto_dump` | сбор сведений о длительных и проблемных запросах для последующего воспроизведения | `shared_preload_libraries = 'auto_dump'`, `auto_dump.enable = on` и обязательные параметры модуля; нужен перезапуск |

Полный набор параметров `online_analyze` из приложения K.4: `online_analyze.enable = on`, `online_analyze.threshold = 50`, `online_analyze.scale_factor = 0.1`, `online_analyze.verbose = off`, `online_analyze.table_type = 'temporary'`, `online_analyze.min_interval = 10000`.

Эти сведения относятся к Postgres Pro Standard 17; состав модулей в сборке «Postgres Pro 1С» и в «PostgreSQL с патчем от 1С» проверьте командами `\dx` в базе 1С и `SELECT name FROM pg_available_extensions;`. Базу 1С нельзя восстановить на сервере без этих модулей: восстановление остановится на ошибке `type "mchar" does not exist` или подобной.

## 18. Шпаргалка SQL администратора

Запросы рассчитаны на PostgreSQL 14–18; отличия по версиям оговорены. Выполнять от суперпользователя или роли с `pg_monitor`. Запросы со столбцами вида `relid::regclass` показывают имена только для объектов текущей базы. Запрос 8 показывает содержимое файла на диске, а не то, что загружено в сервер: если после правки `pg_hba.conf` ещё не было `reload`, действуют прежние правила. Представления `pg_file_settings` и `pg_hba_file_rules` по умолчанию читает только суперпользователь (роли `pg_monitor` недостаточно).

### 18.1. Сервер и конфигурация

```sql
-- 1. Версия сервера
SELECT version();

-- 2. Время старта и время работы
SELECT pg_postmaster_start_time() AS started, now() - pg_postmaster_start_time() AS uptime;

-- 3. Когда последний раз перечитана конфигурация
SELECT pg_conf_load_time();

-- 4. Основные пути и порт
SELECT name, setting FROM pg_settings
WHERE name IN ('data_directory','config_file','hba_file','ident_file','unix_socket_directories','port','log_directory');

-- 5. Параметры, отличные от умолчаний, и откуда они взяты
SELECT name, setting, unit, source, sourcefile, sourceline
FROM pg_settings
WHERE source NOT IN ('default', 'override')
ORDER BY source, name;

-- 6. Параметры, ждущие перезапуска
SELECT name, setting FROM pg_settings WHERE pending_restart;

-- 7. Ошибки в файлах конфигурации (до reload)
SELECT sourcefile, sourceline, name, setting, error FROM pg_file_settings WHERE error IS NOT NULL;
SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;               -- любая версия
-- SELECT file_name, line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;  -- PostgreSQL 16+: с именем файла

-- 8. Правила pg_hba.conf в том виде, в каком они записаны в файле (порядок = порядок проверки)
SELECT line_number, type, database, user_name, address, netmask, auth_method
FROM pg_hba_file_rules WHERE error IS NULL ORDER BY line_number;                        -- PostgreSQL 14–15 и новее (один файл)
-- SELECT rule_number, file_name, line_number, type, database, user_name, address, netmask, auth_method
-- FROM pg_hba_file_rules WHERE error IS NULL ORDER BY rule_number;                     -- PostgreSQL 16+ (учитывает include)

-- 9. Основной сервер или резервный; включены ли контрольные суммы
SELECT pg_is_in_recovery() AS is_standby, current_setting('data_checksums') AS checksums;
```

### 18.2. Сеансы и запросы

```sql
-- 10. Активные запросы, самые долгие сверху
SELECT pid, usename, datname, application_name, client_addr,
       now() - query_start AS runtime,
       wait_event_type, wait_event,
       left(query, 120) AS query
FROM pg_stat_activity
WHERE state = 'active' AND backend_type = 'client backend' AND pid <> pg_backend_pid()
ORDER BY query_start;

-- 11. Сеансы по базам и состояниям
SELECT datname, state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY datname, state
ORDER BY datname, count(*) DESC;

-- 12. Долгие транзакции (старше 5 минут)
SELECT pid, usename, datname, state,
       now() - xact_start AS xact_age,
       now() - state_change AS in_state,
       left(query, 100) AS last_query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND now() - xact_start > interval '5 minutes'
ORDER BY xact_start;

-- 13. Сеансы «idle in transaction»
SELECT pid, usename, datname, client_addr, now() - state_change AS idle_for, left(query, 100) AS last_query
FROM pg_stat_activity
WHERE state LIKE 'idle in transaction%'
ORDER BY state_change;

-- 14. Кто удерживает самый старый снимок (мешает очистке)
SELECT pid, usename, datname, state, backend_xmin, age(backend_xmin) AS xmin_age, now() - xact_start AS xact_age
FROM pg_stat_activity
WHERE backend_xmin IS NOT NULL
ORDER BY age(backend_xmin) DESC
LIMIT 10;

-- 15. Использование лимита подключений
SELECT count(*) AS used, current_setting('max_connections')::int AS max_connections
FROM pg_stat_activity WHERE backend_type = 'client backend';

-- 16. Отменить запрос / завершить сеанс
SELECT pg_cancel_backend(12345);
SELECT pg_terminate_backend(12345);

-- 17. Завершить все сеансы базы, кроме своего
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = 'buh' AND pid <> pg_backend_pid();
```

### 18.3. Блокировки

```sql
-- 18. Кто кого блокирует
SELECT w.pid AS waiting_pid, w.usename AS waiting_user,
       now() - w.query_start AS waiting_for,
       left(w.query, 80) AS waiting_query,
       b.pid AS blocking_pid, b.usename AS blocking_user, b.state AS blocking_state,
       now() - b.xact_start AS blocking_xact_age,
       left(b.query, 80) AS blocking_query
FROM pg_stat_activity w
JOIN LATERAL unnest(pg_blocking_pids(w.pid)) AS blk(pid) ON true
JOIN pg_stat_activity b ON b.pid = blk.pid
ORDER BY waiting_for DESC;

-- 19. Невыданные блокировки (столбец waitstart — PostgreSQL 14+)
SELECT l.pid, l.locktype, l.mode, l.relation::regclass AS relation, l.waitstart,
       left(a.query, 80) AS query
FROM pg_locks l JOIN pg_stat_activity a ON a.pid = l.pid
WHERE NOT l.granted
ORDER BY l.waitstart;

-- 20. Кто держит блокировки на конкретной таблице
SELECT l.pid, l.mode, l.granted, a.usename, a.state, now() - a.xact_start AS xact_age, left(a.query, 80) AS query
FROM pg_locks l JOIN pg_stat_activity a ON a.pid = l.pid
WHERE l.relation = '_document123'::regclass
ORDER BY l.granted DESC, a.xact_start;

-- 21. Число взаимоблокировок по базам с момента сброса статистики
SELECT datname, deadlocks, stats_reset FROM pg_stat_database WHERE datname IS NOT NULL ORDER BY deadlocks DESC;
```

Документация рекомендует определять блокирующие процессы функцией `pg_blocking_pids()`, а не самосоединением `pg_locks`: представление не показывает, какие режимы конфликтуют и кто стоит в очереди раньше.

### 18.4. Размеры

```sql
-- 22. Базы по размеру
SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database ORDER BY pg_database_size(datname) DESC;

-- 23. Топ-20 таблиц текущей базы (см. также 14.3)
SELECT c.oid::regclass AS table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       pg_size_pretty(pg_relation_size(c.oid)) AS heap,
       pg_size_pretty(pg_indexes_size(c.oid)) AS indexes,
       c.reltuples::bigint AS est_rows
FROM pg_class c
WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;

-- 24. Топ-20 индексов
SELECT relname AS table_name, indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size, idx_scan
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;

-- 25. Неиспользуемые индексы (ни одного сканирования с момента сброса статистики; уникальные исключены)
SELECT s.schemaname, s.relname AS table_name, s.indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0 AND NOT i.indisunique AND NOT i.indisprimary
ORDER BY pg_relation_size(s.indexrelid) DESC;

-- 26. Табличные пространства
SELECT spcname, pg_tablespace_location(oid) AS location, pg_size_pretty(pg_tablespace_size(oid)) AS size
FROM pg_tablespace;

-- 27. Объём каталога WAL
SELECT count(*) AS files, pg_size_pretty(sum(size)) AS total FROM pg_ls_waldir();

-- 28. Временные таблицы сеансов (в базах 1С их много)
SELECT n.nspname AS temp_schema, count(*) AS tables, pg_size_pretty(sum(pg_total_relation_size(c.oid))) AS size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname ~ '^pg_temp_' AND c.relkind = 'r'
GROUP BY n.nspname
ORDER BY sum(pg_total_relation_size(c.oid)) DESC
LIMIT 20;
```

Запрос 25 в базе 1С — только диагностика. Индексы таблиц 1С создаёт и пересоздаёт платформа; удалять их вручную нельзя. Статистика использования копится с момента `stats_reset`, а индекс, не нужный ежедневно, может понадобиться при закрытии месяца.

### 18.5. Очистка, статистика, «раздувание»

```sql
-- 29. Таблицы с наибольшим числом «мёртвых» строк и когда их чистили
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;

-- 30. Возраст идентификаторов транзакций по базам (контроль зацикливания счётчика)
SELECT datname, age(datfrozenxid) AS xid_age,
       round(100.0 * age(datfrozenxid) / 2147483647, 1) AS pct_to_wraparound
FROM pg_database
ORDER BY age(datfrozenxid) DESC;

-- 31. Таблицы, которые чаще всего читаются последовательно (кандидаты на анализ запросов)
SELECT relname, seq_scan, seq_tup_read, idx_scan, n_live_tup
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;

-- 32. Сводка по базам: фиксации, откаты, временные файлы, попадания в кеш
SELECT datname, numbackends, xact_commit, xact_rollback, deadlocks,
       temp_files, pg_size_pretty(temp_bytes) AS temp_size,
       round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS cache_hit_pct,
       stats_reset
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY xact_commit DESC;

-- 33. Работающая автоочистка
SELECT pid, datname, now() - xact_start AS runtime, left(query, 100) AS query
FROM pg_stat_activity
WHERE backend_type = 'autovacuum worker';
```

### 18.6. Ход длительных операций (pg_stat_progress_*)

| Представление | Какие команды |
|---|---|
| `pg_stat_progress_vacuum` | `VACUUM`, в том числе автоочистка (кроме `VACUUM FULL`) |
| `pg_stat_progress_cluster` | `CLUSTER` и `VACUUM FULL` |
| `pg_stat_progress_analyze` | `ANALYZE` |
| `pg_stat_progress_create_index` | `CREATE INDEX`, `REINDEX`, в том числе `CONCURRENTLY` |
| `pg_stat_progress_copy` | `COPY FROM` и `COPY TO` |
| `pg_stat_progress_basebackup` | `pg_basebackup` |

```sql
-- 34. VACUUM: фаза и доля просмотренных блоков
SELECT p.pid, p.datname, p.relid::regclass AS table_name, p.phase,
       round(100.0 * p.heap_blks_scanned / nullif(p.heap_blks_total, 0), 1) AS scanned_pct,
       p.index_vacuum_count
FROM pg_stat_progress_vacuum p;

-- 35. CREATE INDEX / REINDEX
SELECT p.pid, p.relid::regclass AS table_name, p.index_relid::regclass AS index_name, p.command, p.phase,
       round(100.0 * p.blocks_done / nullif(p.blocks_total, 0), 1) AS blocks_pct,
       round(100.0 * p.tuples_done / nullif(p.tuples_total, 0), 1) AS tuples_pct
FROM pg_stat_progress_create_index p;

-- 36. VACUUM FULL / CLUSTER
SELECT p.pid, p.relid::regclass AS table_name, p.command, p.phase,
       p.heap_blks_scanned, p.heap_blks_total, p.heap_tuples_written, p.index_rebuild_count
FROM pg_stat_progress_cluster p;

-- 37. ANALYZE
SELECT p.pid, p.relid::regclass AS table_name, p.phase, p.sample_blks_scanned, p.sample_blks_total
FROM pg_stat_progress_analyze p;

-- 38. COPY (в том числе загрузка pg_restore)
SELECT p.pid, p.relid::regclass AS table_name, p.command, p.type,
       pg_size_pretty(p.bytes_processed) AS processed, pg_size_pretty(p.bytes_total) AS total, p.tuples_processed
FROM pg_stat_progress_copy p;

-- 39. Базовая резервная копия (pg_basebackup)
SELECT pid, phase,
       pg_size_pretty(backup_streamed) AS streamed, pg_size_pretty(backup_total) AS total,
       round(100.0 * backup_streamed / nullif(backup_total, 0), 1) AS pct,
       tablespaces_streamed, tablespaces_total
FROM pg_stat_progress_basebackup;
```

Фазы `VACUUM`: `initializing`, `scanning heap`, `vacuuming indexes`, `vacuuming heap`, `cleaning up indexes`, `truncating heap`, `performing final cleanup`. Фазы `CREATE INDEX`: `initializing`, `building index`, а для `CONCURRENTLY` ещё `waiting for writers before build`, `waiting for writers before validation`, `index validation: scanning index`, `index validation: sorting tuples`, `index validation: scanning table`, `waiting for old snapshots`.

### 18.7. WAL, контрольные точки, репликация

```sql
-- 40. Текущая позиция WAL и имя сегмента (на основном сервере)
SELECT pg_current_wal_lsn() AS lsn, pg_walfile_name(pg_current_wal_lsn()) AS wal_file;

-- 41. Сколько WAL записано между двумя моментами: запомнить LSN, подождать, вычесть
SELECT pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/5A000000'::pg_lsn));

-- 42. Отставание реплик (на основном сервере)
SELECT application_name, client_addr, state, sync_state,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn))   AS not_sent,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) AS not_replayed,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- 43. Состояние резервного сервера (на реплике)
SELECT pg_is_in_recovery() AS in_recovery,
       pg_last_wal_receive_lsn() AS received,
       pg_last_wal_replay_lsn()  AS replayed,
       now() - pg_last_xact_replay_timestamp() AS replay_delay;

-- 44. Слоты репликации и сколько WAL они удерживают
SELECT slot_name, slot_type, active,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal,
       wal_status
FROM pg_replication_slots;

-- 45. Контрольные точки: PostgreSQL 17+
SELECT num_timed, num_requested, write_time, sync_time, buffers_written, stats_reset FROM pg_stat_checkpointer;
--     PostgreSQL 16 и более ранние (в том числе «PostgreSQL для 1С» 16)
SELECT checkpoints_timed, checkpoints_req, buffers_checkpoint, stats_reset FROM pg_stat_bgwriter;

-- 46. Архивирование WAL
SELECT archived_count, last_archived_wal, last_archived_time, failed_count, last_failed_wal, last_failed_time
FROM pg_stat_archiver;

-- 47. Подготовленные (двухфазные) транзакции — в норме пусто
SELECT gid, prepared, owner, database FROM pg_prepared_xacts;
```

- Запрос 43: `replay_delay` растёт и при простое основного сервера (нет новых транзакций — нечего воспроизводить), поэтому сравнивайте ещё и позиции `received`/`replayed`.
- Запрос 44: неактивный слот с большим `retained_wal` — причина переполнения диска каталогом `pg_wal`. Удаление слота: `SELECT pg_drop_replication_slot('имя');`.
- Запрос 45: много `num_requested` (`checkpoints_req`) по сравнению с `num_timed` — признак малого `max_wal_size`.

### 18.8. Роли, базы, расширения

```sql
-- 48. Роли и их атрибуты
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolreplication, rolconnlimit, rolvaliduntil
FROM pg_roles WHERE rolname !~ '^pg_' ORDER BY rolname;

-- 49. Членство в ролях
SELECT r.rolname AS role, m.rolname AS member
FROM pg_auth_members am
JOIN pg_roles r ON r.oid = am.roleid
JOIN pg_roles m ON m.oid = am.member
ORDER BY 1, 2;

-- 50. Базы: владелец, кодировка, локаль, доступность, лимит, табличное пространство
SELECT d.datname, pg_get_userbyid(d.datdba) AS owner, pg_encoding_to_char(d.encoding) AS encoding,
       d.datcollate, d.datctype, d.datallowconn, d.datconnlimit, d.datistemplate, t.spcname AS tablespace
FROM pg_database d JOIN pg_tablespace t ON t.oid = d.dattablespace
ORDER BY d.datname;

-- 51. Настройки, заданные на уровне баз и ролей
SELECT coalesce(d.datname, '*') AS database, coalesce(r.rolname, '*') AS role, unnest(s.setconfig) AS setting
FROM pg_db_role_setting s
LEFT JOIN pg_database d ON d.oid = s.setdatabase
LEFT JOIN pg_roles r ON r.oid = s.setrole;

-- 52. Расширения текущей базы
SELECT extname, extversion, extnamespace::regnamespace AS schema FROM pg_extension ORDER BY extname;

-- 53. Самые затратные запросы (нужен pg_stat_statements; имена столбцов — PostgreSQL 13+)
SELECT calls, round(total_exec_time::numeric) AS total_ms, round(mean_exec_time::numeric, 2) AS mean_ms,
       rows, left(query, 100) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

В запросе 50 для PostgreSQL 15+ можно добавить столбец `d.datlocprovider` (`c` — libc, `i` — icu, `b` — builtin).

## 19. Особенности баз 1С

### 19.1. Как выглядит база 1С изнутри

- Платформа создаёт все объекты в схеме `public`. Начиная с 8.5.4 (официально, «Список изменений» платформы 8.5.4) таблицы можно разместить в произвольной схеме PostgreSQL: поле «Схема БД» в свойствах информационной базы, параметр `--db-schema` у `rac`, `ibsrv`, `ibcmd`, параметр `DBSchema` команды `CREATEINFOBASE`. Если схема задана, во всех примерах ниже заменяйте `public` на неё (или выполните `SET search_path TO имя_схемы;`). Узнать схему: `SELECT schemaname, count(*) FROM pg_tables WHERE tablename IN ('config','params') GROUP BY 1;`.
- PostgreSQL приводит имена без кавычек к нижнему регистру, поэтому в `psql` таблицы видны как `config`, `params`, `_reference15`, `_document123`, `_inforg456`, хотя в документации 1С они пишутся `Config`, `_Reference15` и т.д.
- Номер в имени таблицы (`_Reference15`) присваивается платформой и в разных базах одной и той же конфигурации может отличаться. Соответствие «объект метаданных — таблица» хранится в самой базе в сериализованном виде (по ИТС 1591 — в таблице `Params`) и в читаемом виде доступно только через платформу: метод встроенного языка `ПолучитьСтруктуруХраненияБазыДанных()` (в англоязычном синтаксисе `GetDBStorageStructureInfo()`) или обработки на его основе.
- Строковые поля имеют типы `mchar` и `mvarchar` (расширение `mchar`), ссылки — `bytea` длиной 16 байт, двоичные данные и хранилища значений — `bytea`. Внешних ключей в базе нет: ссылочную целостность обеспечивает платформа.
- Во время работы платформа создаёт множество временных таблиц с именами вида `tt<число>` в схемах `pg_temp_N` (⚠ практика; проверка — запрос 28 из раздела 18).

Служебные таблицы. Имена и назначение сверены по двум статьям ИТС, конспекты которых лежат в этой базе знаний: «Размещение данных 1С:Предприятия 8» (its.1c.ru/db/metod8dev/content/1591, далее «ИТС 1591»; `kb/its-metod/razmeshchenie-dannyh-i-indeksy.md`) и «Размещение данных 1С:Предприятия 8. Таблицы и поля» (content/1798, редакция для 8.3.27, далее «ИТС 1798»; `kb/its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`).

| Таблица (как в документации 1С) | Назначение |
|---|---|
| `Config` | основная конфигурация информационной базы: соответствует реальной структуре данных и используется в режиме Предприятия |
| `ConfigSave` | конфигурация, редактируемая конфигуратором; переписывается в `Config` при «Обновлении конфигурации базы данных» |
| `ConfigCAS`, `ConfigCASSave` | системное хранилище конфигураций расширений и его сохранённая копия |
| `Params` | параметры информационной базы: национальные настройки, таблица соответствия объектов метаданных объектам базы данных (таблицам, полям, индексам) и другие служебные «файлы»; здесь же запись `users.usr` |
| `Files` | служебная информация; по ИТС 1798 — работа с хранилищем конфигурации на платформе 8.3.9 и ниже, профайлы и т.п. |
| `DepotFiles` | работа с хранилищем конфигурации |
| `DBSchema` | сведения о структуре базы данных «1С:Предприятия» (одна запись, поле `SerializedData`) |
| `DBChanges` | изменения схемы в процессе обновления конфигурации базы данных (одна запись, поле `SerializedData`) |
| `IBVersion`, `SchemaStorage` | служебные таблицы платформы; названы в официальной команде `pg_dump` из методики ИТС («лёгкая» копия базы), назначение в прочитанных статьях не описано |
| `v8users` | список пользователей информационной базы (написание — см. ниже) |
| `_YearOffset` | смещение дат. По обеим статьям ИТС создаётся только при работе с Microsoft SQL Server; при этом в официальной команде `pg_dump` из методики ИТС для PostgreSQL («лёгкая» копия) таблица названа (`-t _YearOffset`). ⚠ Есть ли она в вашей базе, покажет `\dt _yearoffset`; для PostgreSQL смещение дат не используется |
| `_UsersWorkHistory` | история работы пользователей |
| `_SystemSettings`, `_CommonSettings`, `_RepSettings`, `_RepVarSettings`, `_FrmDtSettings`, `_DynListSettings`, `_ErrorProcessingSettings`, `_URLExternalData`, `_InternalSettings` | хранилища настроек: системных, общих, отчётов, вариантов отчётов, данных форм, динамических списков, обработки ошибок, внешних данных навигационных ссылок, внутренних |
| `_DataHistoryQueue`, `_DataHistoryVersions`, `_DataHistoryLatestVersions<n>`, `_DataHistoryMetadata`, `_DataHistorySettings`, `_DataHistoryAfterWriteQueue` | история данных |
| `_DbCopies`, `_DbCopiesSettings`, `_DbCopiesTablesStates`, `_DbCopiesTrChanges`, `_DbCopiesUpdates` и др. | копии базы данных и Дата акселератор |
| `_DbSegments`, `_DbSegmentsItems` | табличные пространства, назначенные средствами платформы (имя, путь к каталогу на сервере СУБД, что куда размещено) |
| `_ScheduledJobs` | регламентные задания: расписание, состояние, время последнего запуска (одна таблица) |
| `_ConfigChangeRec`, `_ConfigChangeRec_ExtProps` | регистрация изменений конфигурации; создаются, если есть план обмена с признаком «Распределенная информационная база» |
| `ODataSettings`, `WebSocketClients`, `_MobileClientDataExchange`, `_IntegServiceSettings<n>`, `_IntegChannelOutQueue<n>`, `_IntegChannelInQueue<n>` | настройки OData, WebSocket-клиенты, обмен с мобильным клиентом, сервисы интеграции |
| `_ExtensionsInfo…` | расширения конфигурации (⚠ по практике; в прочитанных статьях ИТС таблица не названа) |

У таблиц `Config`, `ConfigSave`, `ConfigCAS`, `ConfigCASSave`, `DepotFiles`, `Files`, `Params` одинаковый набор полей (ИТС 1798): `FileName`, `Creation`, `Modified`, `Attributes`, `DataSize`, `BinaryData`.

Написание имени таблицы пользователей в двух статьях ИТС разное: в ИТС 1591 — `v8users`, в ИТС 1798 — `_v8users`. По практике сообщества (все известные инструкции и запросы к реальным базам) таблица в базе называется `v8users`, в PostgreSQL — в нижнем регистре; вариант с подчёркиванием, по-видимому, особенность оформления новой статьи. ⚠ Проверьте в своей базе до любых действий: `\dt *v8users*`. Поля таблицы по ИТС 1798: `ID` (идентификатор пользователя), `Name` (имя), `Descr` (полное имя), `OSName` (пользователь ОС; NULL, если аутентификация ОС не задана), `Changed`, `RolesID`, `Show` (показывать в списке выбора), `Data` (все данные о пользователе), `AdmRole` (есть право «Администратор»), `UsSprH`, `EAuth` (разрешена аутентификация паролем).

При старте платформа проверяет наличие обязательных служебных таблиц (ИТС 1591: `Config`, `ConfigSave`, `Files`, `Params`, `DBSchema`, `v8users`, хранилища настроек и др.): если нет какой-то одной — сообщение «информационная база разрушена», если нет ни одной — база считается пустой и таблицы создаются заново. Наличие и целостность прикладных таблиц в штатном режиме не проверяются — для этого есть «Тестирование и исправление».

Таблицы прикладных объектов (префиксы подтверждены ИТС 1591 и ИТС 1798; `<n>`, `<k>` — номера). Таблицы регистрации изменений (`…ChngR…`) создаются, только если объект участвует хотя бы в одном плане обмена:

| Объект метаданных | Таблицы |
|---|---|
| Константы | `_Const<n>` (ИТС 1798; в старой статье ИТС 1591 — одна общая таблица `_Consts`); регистрация изменений — по обеим статьям ИТС одна общая таблица `_ConstsChngR`, на практике в базах встречается и `_ConstChngR<n>` (⚠ практика; смотрите `\dt _const*`) |
| Справочники | `_Reference<n>`; табличные части `_Reference<n>_VT<k>`; регистрация изменений `_ReferenceChngR<n>` |
| Документы | `_Document<n>`; табличные части `_Document<n>_VT<k>`; `_DocumentChngR<n>`; журналы документов `_DocumentJournal<n>` |
| Последовательности | `_Seq<n>`, `_SeqB<n>`, `_SeqChngR<n>` |
| Перечисления | `_Enum<n>` |
| Планы видов характеристик | `_Chrc<n>`, `_ChrcChngR<n>` |
| Планы счетов | `_Acc<n>`, `_Acc<n>_ExtDim<k>`, `_AccChngR<n>` |
| Планы видов расчёта | `_CKind<n>`, `_CKind<n>_BaseCK`, `_CKind<n>_LeadingCK`, `_CKind<n>_DisplacedCK` |
| Регистры сведений | `_InfoRg<n>`; срезы последних и первых `_InfoRgSL<n>`, `_InfoRgSF<n>`; `_InfoRgChngR<n>` |
| Регистры накопления | движения `_AccumRg<n>`; итоги `_AccumRgT<n>` (остатки), `_AccumRgTn<n>` (обороты); агрегаты `_AccumRgAgg…<n>`, `_AccumRgSt<n>`, `_AccumRgBf<n>`, `_AccumRgDl<n>`; настройки `_AccumRgOpt` |
| Регистры бухгалтерии | движения `_AccRg<n>`; итоги `_AccRgAT<k><n>`, `_AccRgCT<n>`; значения субконто `_AccRgED<n>` (так в ИТС 1591 и на практике; в ИТС 1798 та же таблица записана как `_AccntRegED<n>` — сверьте по `\dt _acc*`); настройки `_AccRgOpt`. Итогов по счёту столько таблиц, каково максимальное число субконто плана счетов (`_AccRgAT0<n>`, `_AccRgAT1<n>` …); `_AccRgCT<n>` есть только у регистров с корреспонденцией |
| Регистры расчёта | `_CRg<n>`, `_CRgActPer<n>`, `_CRgRecalc<n>` |
| Бизнес-процессы и задачи | `_BPr<n>`, `_BPrPoints<n>`, `_Task<n>` |
| Планы обмена | `_Node<n>` |

Типовые поля: `_IDRRef` (ссылка), `_Version`, `_Marked` (пометка удаления), `_PredefinedID`, `_ParentIDRRef`, `_OwnerIDRRef`, `_Folder`, `_Code`, `_Description`, `_Date_Time`, `_Number`, `_Posted`, `_Period`, `_Recorder…`, `_LineNo`, `_Active`, `_RecordKind`, `_Fld<n>` (реквизиты, измерения, ресурсы). У полей составного типа — суффиксы (`_TYPE`, `_L`, `_N`, `_T`, `_S`, `_RTRef`, `_RRRef`); у ссылочных — `RRef`. Суффиксы `_TYPE`, `_RTRef`, `_RRRef` и `RRef` видны в официальных примерах запросов из методики ИТС (например, `_Fld30691_TYPE`, `_Fld30691_RTRef`, `_Fld30691_RRRef`); `_L` (булево), `_N` (число), `_T` (дата), `_S` (строка) приведены по практике — ИТС 1798 обозначает суффиксы обобщённо (`_ID<suff>`, `_Fld<n><suff>`) и отсылает к разделу «Особенности хранения составных типов данных» (⚠ этот раздел не прочитан). `_RTRef` — номер таблицы ссылочного типа (4 байта), по нему определяется, на какую таблицу указывает ссылка `_RRRef`. Поле `_Version` в таблицах ссылочных объектов меняется при каждом обновлении записи (ИТС 1798).

Быстрый обзор базы 1С:

```sql
\c buh
\dx
\dt+ config
SELECT count(*) FROM pg_tables WHERE schemaname = 'public';

-- сколько таблиц каждого вида
SELECT regexp_replace(tablename, '[0-9].*$', '') AS prefix, count(*),
       pg_size_pretty(sum(pg_total_relation_size(format('%I.%I', schemaname, tablename)::regclass))) AS size
FROM pg_tables
WHERE schemaname = 'public'
GROUP BY 1
ORDER BY sum(pg_total_relation_size(format('%I.%I', schemaname, tablename)::regclass)) DESC;
```

### 19.2. Почему нельзя править данные напрямую

1. Структура хранения — внутреннее дело платформы. Она меняется при обновлении конфигурации (реструктуризация пересоздаёт таблицы) и между версиями платформы; номера таблиц и полей не постоянны.
2. Целостность поддерживает только платформа: ссылки между объектами, версии объектов (`_Version`), таблицы итогов регистров, таблицы регистрации изменений планов обмена, последовательности документов, история данных, индексы полнотекстового поиска. Изменив строку в `_AccumRg…`, вы не измените итоги в `_AccumRgT…` — остатки в отчётах разойдутся с движениями.
3. Сервер 1С кеширует объекты и метаданные. Прямое изменение базы он не увидит и может перезаписать его старым значением либо работать с противоречивыми данными.
4. Прикладная логика (обработчики записи, проведения, проверки заполнения, права доступа на уровне записей) при прямом изменении не выполняется.
5. Официальная позиция фирмы «1С» (подтверждено конспектами статей ИТС 1591 и ИТС 1798 в этой базе знаний; изложение близко к тексту, не дословная цитата): сведения о таблицах и полях предназначены исключительно для понимания расположения и состава данных и не должны использоваться для работы с данными способами, не предусмотренными штатными механизмами «1С:Предприятия 8»; база данных должна быть защищена от несанкционированного доступа, а её модификация должна выполняться только средствами «1С:Предприятия»; в следующих версиях платформы состав таблиц и полей может измениться. ⚠ не подтверждено: что прямой доступ к данным является именно нарушением лицензионного соглашения — такая формулировка распространена в сообществе, но в прочитанных статьях ИТС её нет (там запрет сформулирован как «не должны использоваться»); текст лицензионного соглашения не проверялся.
6. Резервное копирование и восстановление базы с информационной базой — только целиком (ИТС 1591): выгрузка или подмена отдельных таблиц 1С средствами СУБД нарушает согласованность.

Что администратору СУБД делать можно и нужно: `VACUUM`, `ANALYZE`, `REINDEX`, резервное копирование и восстановление, перенос базы и табличных пространств, настройка параметров, мониторинг, запросы на чтение. Чего делать нельзя: `INSERT`/`UPDATE`/`DELETE`/`TRUNCATE` в таблицах 1С, `ALTER TABLE`, создание и удаление индексов и триггеров на таблицах 1С, изменение типов.

### 19.3. Как безопасно выполнять запросы на чтение

- Лучше всего — на копии базы или на реплике, а не на рабочей базе.
- Отдельная роль только для чтения с тайм-аутами:

```sql
CREATE ROLE ro_audit LOGIN PASSWORD 'R3adOnly';
GRANT CONNECT ON DATABASE buh TO ro_audit;
GRANT pg_read_all_data TO ro_audit;                               -- PostgreSQL 14+
ALTER ROLE ro_audit SET default_transaction_read_only = on;
ALTER ROLE ro_audit SET statement_timeout = '60s';
ALTER ROLE ro_audit SET lock_timeout = '2s';
ALTER ROLE ro_audit SET idle_in_transaction_session_timeout = '60s';
```

- Работая от суперпользователя, включайте защиту в сеансе:

```sql
SET default_transaction_read_only = on;
SET statement_timeout = '60s';
SET lock_timeout = '2s';
BEGIN TRANSACTION READ ONLY;
SELECT count(*) FROM _document123;
ROLLBACK;
```

- Не держите транзакцию открытой. Сеанс в состоянии `idle in transaction` удерживает снимок, и автоочистка не может убрать «мёртвые» строки во всей базе — таблицы раздуваются.
- Даже `SELECT` берёт на таблицу блокировку `ACCESS SHARE`. Она конфликтует с `ACCESS EXCLUSIVE`, которую запрашивают реструктуризация (обновление конфигурации), `TRUNCATE`, `VACUUM FULL` (а `REINDEX` берёт её на сам индекс). Долгий запрос на чтение способен остановить обновление конфигурации, а за ожидающей `ACCESS EXCLUSIVE` выстроится очередь из всех остальных сеансов.
- Не запускайте тяжёлые запросы без `LIMIT` и без оценки плана: сначала `EXPLAIN` (без `ANALYZE`), затем сам запрос.
- Удобные приёмы чтения:

```sql
SELECT encode(_idrref, 'hex') AS ref, _code, _description FROM _reference15 LIMIT 10;   -- ссылка в шестнадцатеричном виде
SELECT filename, creation, modified, datasize FROM params ORDER BY filename;            -- что лежит в Params
SELECT filename, datasize FROM config ORDER BY datasize DESC LIMIT 10;                  -- самые большие части конфигурации
```

Имена столбцов `filename`, `creation`, `modified`, `attributes`, `datasize`, `binarydata` подтверждены статьёй ИТС 1798 (`FileName`, `Creation`, `Modified`, `Attributes`, `DataSize`, `BinaryData`); в PostgreSQL они в нижнем регистре. Типы столбцов статья не приводит — посмотрите `\d params` и `\d config` в своей базе. Не выбирайте `binarydata` без нужды: в `config` это десятки и сотни мегабайт.

Строковые столбцы 1С имеют типы `mchar`/`mvarchar` (официально, документация Postgres Pro, модуль `mchar`): операторы `=`, `<`, `<=`, `>=`, `>` сравнивают без учёта регистра средствами ICU, пробелы в конце строки обрабатываются по правилам Microsoft SQL Server; для сравнения с учётом регистра есть отдельные операторы `&=`, `&<`, `&<=`, `&>=`, `&>`. Поэтому условие `WHERE filename = 'USERS.USR'` найдёт ту же строку, что и `'users.usr'`.

### 19.4. Сброс пароля пользователя 1С через СУБД (известный приём сообщества и его риски)

Ситуация: утрачен пароль единственного пользователя с административными правами, войти в конфигуратор нельзя.

Сначала — поддерживаемые способы: войти другим пользователем с административными правами; восстановить базу из резервной копии, сделанной до смены пароля; обратиться к автору изменения.

Приём сообщества (⚠ практика, официально не документирован; это прямое изменение служебных таблиц со всеми рисками из 19.2): платформа, не найдя списка пользователей, пускает в конфигуратор без аутентификации. Список временно «прячут», входят в конфигуратор, затем возвращают список на место и меняют пароль штатным способом.

```sql
-- 0. Обязательно: резервная копия базы (pg_dump); сеансы пользователей 1С завершены, регламентные задания заблокированы.
--    Блокировка начала сеансов в кластере 1С без кода разрешения не даст запуститься и Конфигуратору:
--    либо не ставьте её, либо ставьте с кодом разрешения и запускайте Конфигуратор с параметром /UC <код>.

--    Перед шагом 1 убедитесь, что объекты называются именно так (схема public, таблица v8users, строка users.usr):
--      \dt public.v8users*
--      SELECT filename, datasize FROM public.params WHERE filename = 'users.usr';
--    Если таблицы лежат в другой схеме (платформа 8.5.4+) — замените public на неё.

-- 1. Спрятать список пользователей
BEGIN;
ALTER TABLE public.v8users RENAME TO v8users_saved;
UPDATE public.params SET filename = 'users.usr_saved' WHERE filename = 'users.usr';   -- должно быть UPDATE 1
COMMIT;

-- 2. Запустить Конфигуратор для этой базы: вход произойдёт без запроса имени и пароля.
--    Платформа создаст новую пустую таблицу v8users. Конфигуратор НЕ закрывать.

--    Перед шагом 3 проверьте, что есть ОБЕ таблицы — новая пустая v8users и сохранённая v8users_saved:
--      \dt public.v8users*
--      SELECT count(*) FROM public.v8users;          -- ожидается 0
--      SELECT count(*) FROM public.v8users_saved;    -- ожидается число прежних пользователей
--    Если новой v8users нет или в ней есть строки — НЕ выполняйте DROP, разберитесь, что произошло.

-- 3. Вернуть список пользователей на место (в одной транзакции: DDL в PostgreSQL транзакционен,
--    при ошибке любой из команд COMMIT превратится в ROLLBACK и ничего не изменится)
BEGIN;
DROP TABLE public.v8users;
ALTER TABLE public.v8users_saved RENAME TO v8users;
UPDATE public.params SET filename = 'users.usr' WHERE filename = 'users.usr_saved';   -- должно быть UPDATE 1
COMMIT;

-- 4. В открытом Конфигураторе: Администрирование → Пользователи → задать новый пароль нужному пользователю.
```

Риски и оговорки:

- Работоспособность зависит от версии платформы; на новых версиях приём может не сработать или потребовать иных действий. ⚠ Не проверено на 8.3.27 и 8.5; первоисточника (документации 1С) у приёма нет, в этой сессии не удалось перечитать и ни одну публикацию сообщества с его описанием — последовательность приведена по памяти автора и рецензента (она совпадает с широко известным вариантом для Microsoft SQL Server: переименование `v8users` и строки `users.usr` в `Params`).
- Что подтверждено официально, косвенно: список пользователей действительно хранится в таблице `v8users` и в записи `users.usr` таблицы `Params` — в методике ИТС по снятию «лёгкой» копии базы (конспект — `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`) строки `users.usr` вырезаются из дампа таблицы `Params` (`sed '/^users[.]usr/d'`), а таблица `v8users` в перечень выгружаемых данных не входит. Цель в статье не названа; по смыслу — копия без списка пользователей.
- Что официальной документации противоречит: по статье ИТС 1591 `v8users` входит в число обязательных служебных таблиц, и отсутствие одной из них должно приводить к сообщению «информационная база разрушена». На практике, по сообщениям сообщества, платформа при запуске создаёт пустую `v8users` заново, но это поведение не документировано и не гарантировано. Если Конфигуратор сообщил, что база разрушена, — закройте его и выполните шаг 3 без `DROP TABLE` (только `ALTER TABLE ... RENAME` и `UPDATE`).
- Ошибка на шаге 3 (например, конфигуратор закрыли раньше или таблица не пересоздалась) оставит базу без пользователей или с двумя наборами данных. Поэтому — только после резервной копии и сначала на копии базы.
- Пока список спрятан, в базу без пароля войдёт любой, кто до неё дотянется, с полными правами. Блокировка начала сеансов в кластере 1С мешает и Конфигуратору, поэтому на время операции закройте доступ иначе: отключите публикации на веб-сервере и ограничьте сеть, либо используйте код разрешения (`--permission-code` при блокировке сеансов и параметр запуска `/UC код` у Конфигуратора).
- Если в базе включена аутентификация ОС, стандартные роли привязаны к пользователям или используются разделители данных, последствия шире, чем «сброс пароля».
- С точки зрения безопасности это означает: любой, у кого есть права суперпользователя PostgreSQL или доступ к файлам кластера, получает полный доступ к данным 1С. Защищайте роль `postgres`, `pg_hba.conf` и резервные копии.

## Типичные ошибки и подводные камни

| Симптом | Причина | Решение |
|---|---|---|
| `psql: error: ... FATAL: Peer authentication failed for user "postgres"` | подключение через сокет от пользователя ОС, имя которого не совпадает с ролью | `sudo -u postgres psql` либо подключение по TCP с паролем: `psql -h 127.0.0.1 -U postgres` |
| `FATAL: password authentication failed for user ...` | неверный пароль, пароль не задан или несовместим метод (`md5`-хеш при `scram-sha-256` в `pg_hba.conf`) | `sudo -u postgres psql -c "\password роль"`; проверить тип хеша запросом из 8.1 и строку в `pg_hba_file_rules` |
| `FATAL: no pg_hba.conf entry for host "192.168.1.20", user "usr1c", database "buh"` | в `pg_hba.conf` нет подходящей строки | добавить строку `host ...`, проверить `pg_hba_file_rules`, выполнить `reload` |
| `connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: No such file or directory` | сервер не запущен; либо другой порт; либо сокет в другом каталоге (клиент из пакета Ubuntu, сервер Postgres Pro) | `pg_lsclusters` / `systemctl status`; `ss -lx \| grep PGSQL`; указать `-h /tmp` или `-h 127.0.0.1`, `-p порт` |
| `connection to server at "192.168.1.10", port 5432 failed: Connection refused` | сервер слушает только `localhost`, закрыт брандмауэром или остановлен | `SHOW listen_addresses;`, `sudo ss -tlnp \| grep 5432`, `sudo ufw status` |
| `systemctl status postgresql` показывает `active (exited)`, а подключиться нельзя | это «зонтичный» юнит, он ничего не говорит о кластере | `systemctl status postgresql@NN-main`, `pg_lsclusters`, журнал в `/var/log/postgresql/` |
| Правка `postgresql.conf` не действует | не выполнен `reload`; параметр требует перезапуска; значение перекрыто `postgresql.auto.conf`, файлом из `conf.d` или настройкой роли/базы | `SELECT name, setting, source, sourcefile, pending_restart FROM pg_settings WHERE name = '...'`; `\drds` |
| После `ALTER SYSTEM` или правки конфигурации сервер не запускается | неверное значение параметра уровня `postmaster`, опечатка в `shared_preload_libraries` | прочитать журнал; исправить `postgresql.auto.conf` или `postgresql.conf` вручную; запустить |
| `pg_ctl: ... postgres cannot access the server configuration file` | в Debian-раскладке конфигурация лежит не в каталоге данных | `pg_ctlcluster NN main start` или `systemctl start postgresql@NN-main` |
| `ERROR: database "buh" is being accessed by other users` | к базе есть подключения (для 1С — пул соединений `rphost`) | заблокировать сеансы в кластере 1С, затем приём из 13.3 или `DROP DATABASE ... WITH (FORCE)` |
| `ERROR: source database "buh" is being accessed by other users` | копирование через `TEMPLATE` при активных сеансах в исходной базе | отключить сеансы (13.3) |
| `ERROR: cannot drop the currently open database` / `current database cannot be renamed` | команда выполняется из той же базы | `\c postgres` и повторить |
| `ERROR: CREATE DATABASE cannot run inside a transaction block` | команда внутри `BEGIN` либо в одной строке `-c` с другими командами, либо с ключом `-1` | выполнять отдельной командой |
| `ERROR: new collation (ru_RU.UTF-8) is incompatible with the collation of the template database` | локаль отличается от локали `template1` | добавить `TEMPLATE template0` |
| `ERROR: invalid locale name: "ru_RU.UTF-8"` (14–15); в 16+ — `invalid LC_COLLATE locale name` / `invalid LC_CTYPE locale name` (уточнено 19.10.2026 по `dbcommands.c`) | локаль не сгенерирована в ОС | `sudo locale-gen ru_RU.UTF-8`, перезапустить PostgreSQL |
| `ERROR: type "mchar" does not exist` при восстановлении базы 1С | сервер без доработок 1С | использовать сборку для 1С |
| `ERROR: role "xxx" cannot be dropped because some objects depend on it` | роль владеет объектами или имеет права | `REASSIGN OWNED BY`, `DROP OWNED BY` в каждой базе, затем `DROP ROLE` |
| `ERROR: must be owner of table ...` при обновлении конфигурации 1С | после восстановления объекты принадлежат другой роли | `REASSIGN OWNED BY старая TO новая;` в этой базе |
| `~/.pgpass` не используется, psql спрашивает пароль | права шире `0600`; не совпали хост, порт, база или роль; файл лежит в домашнем каталоге другого пользователя | `chmod 0600 ~/.pgpass`; сверить поля; помнить, что под `sudo -u postgres` домашний каталог — `/var/lib/postgresql` |
| Скрипт на psql «успешно» завершается при ошибках SQL | не задан `ON_ERROR_STOP` | `psql -X -v ON_ERROR_STOP=1 ...` и проверка кода возврата (3) |
| Вывод psql в скрипте внезапно изменил формат | сработал `~/.psqlrc` | ключ `-X` |
| `could not change directory to "/home/admin": Permission denied` | `sudo -u postgres` из каталога, недоступного `postgres` | безвредно; `cd /tmp` перед командой |
| `FATAL: sorry, too many clients already` | исчерпан `max_connections` | войти под суперпользователем (резерв `superuser_reserved_connections`), завершить лишние сеансы, пересмотреть `max_connections` |
| Диск заполнен каталогом `pg_wal` | неактивный слот репликации, сбой `archive_command`, очень долгая транзакция | запросы 44, 46, 12 из раздела 18; устранить причину, не удалять файлы WAL вручную |
| База растёт, хотя данных не прибавляется | раздувание: автоочистке мешает долгая транзакция или `idle in transaction` | запросы 12–14 и 29 |
| Кластер не стартует после переноса каталога данных | неверный владелец или права (`0700`), недоступен родительский каталог, диск не смонтирован к моменту старта | `namei -l путь`, `chown -R postgres:postgres`, `chmod 700`, `RequiresMountsFor` в юните |
| `pg_upgradecluster` отказывается: целевой кластер уже существует | пакет новой версии создал пустой `NN/main` | `sudo pg_dropcluster --stop NN main`, повторить |
| После установки метапакета Postgres Pro пропала прежняя установка | метапакет рассчитан на «чистую» машину | при нескольких инсталляциях ставить отдельные пакеты `-server`, `-client`, `-libs`, `-contrib` |
| Команда `psql` не найдена после установки Postgres Pro | программы лежат в `/opt/pgpro/.../bin` и не в `PATH` | `sudo /opt/pgpro/1c-NN/bin/pg-wrapper links update` или вызов по полному пути |
| `ALLOW_CONNECTIONS false` — и теперь к базе не подключиться даже суперпользователю | так и задумано | из базы `postgres`: `ALTER DATABASE имя WITH ALLOW_CONNECTIONS true;` |
| `FATAL: role "admin" does not exist` или `FATAL: database "admin" does not exist` | `psql` без `-U` и `-d` берёт имя роли и базы из имени пользователя ОС (при `sudo psql` — `root`) | `sudo -u postgres psql` либо явно `-U роль -d база` |
| `ERROR: column "rule_number" does not exist` (или `file_name`) в запросе к `pg_hba_file_rules` | сервер PostgreSQL 14 или 15: эти столбцы появились в 16 | использовать `line_number` (см. 12.7) |
| `\watch i=5 c=12` не останавливается после 12 повторов; `invalid command \bind`, `\drg`, `\dconfig` | старый клиент `psql`: именованные опции `\watch` и `c=` понимает psql 16+, `m=` — 17+, `\bind` и `\drg` — 16+, `\dconfig` — 15+. Подтверждено 11.10.2026 исходным кодом psql 15 (`command.c`: аргумент разбирается функцией `strtod()`, при результате не больше нуля интервал берётся равным 1 с, сообщения об ошибке нет). Ранее было: По памяти рецензента (исходный код psql 15 не перечитывался): psql 15 и старше не сообщает об ошибке, а молча повторяет запрос бесконечно с интервалом 1 с | `psql --version`; вызвать более новый `psql` по полному пути; прервать `\watch` — Ctrl+C |
| `invalid command \restrict` при загрузке текстового дампа | дамп снят `pg_dump` с исправлением CVE-2025-8714 (17.6 и одновременные выпуски других веток, 18), а загружается более старым `psql` | загружать тем же или более новым `psql` |
| `WARNING: psql major version 16, server major version 17. Some psql features might not work.` | клиент старше сервера: часть метакоманд `\d…` может работать неверно | использовать `psql` той же или более новой версии, чем сервер |
| `pg_dump: error: aborting because of server version mismatch` | `pg_dump` старше сервера | запускать `pg_dump` из каталога версии сервера: `/usr/lib/postgresql/NN/bin/pg_dump` или `/opt/pgpro/1c-NN/bin/pg_dump` |
| `FATAL: the database system is starting up` / `is shutting down` / `is in recovery mode` | сервер запускается (идёт восстановление по WAL), останавливается или перезапускается после сбоя процесса | дождаться: `until pg_isready -q; do sleep 1; done`; причину сбоя искать в журнале |
| `FATAL: remaining connection slots are reserved for roles with the SUPERUSER attribute` | обычные слоты `max_connections` заняты, остались только зарезервированные | то же, что при `too many clients`: войти суперпользователем, разобраться с сеансами (13.4) |
| Журнал `/var/log/postgresql/postgresql-NN-main.log` пуст, а сервер работает | включён `logging_collector` — журнал пишется в `log_directory` | `SELECT pg_current_logfile();`, `SHOW log_directory;` |
| После правки `pg_hba.conf` представление `pg_hba_file_rules` показывает новое правило, а подключиться всё равно нельзя | представление читает файл с диска; сервер правило ещё не загрузил | `SELECT pg_reload_conf();` и проверить `SELECT pg_conf_load_time();` |

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Войти локально администратором | `sudo -u postgres psql` |
| Войти по сети | `psql -h хост -p 5432 -U роль -d база` |
| Выполнить один запрос из оболочки | `sudo -u postgres psql -X -At -c "SELECT ..."` |
| Выполнить файл с остановкой на ошибке | `psql -X -v ON_ERROR_STOP=1 -f файл.sql` |
| Выгрузить запрос в CSV | `psql -X --csv -c "SELECT ..." > out.csv` |
| Список кластеров (Debian-раскладка) | `pg_lsclusters` |
| Статус / перезапуск / перечитывание | `systemctl status postgresql@NN-main`, `sudo systemctl restart postgresql@NN-main`, `sudo systemctl reload postgresql@NN-main` |
| То же для Postgres Pro | `systemctl status postgrespro-1c-NN`, `sudo systemctl restart postgrespro-1c-NN` |
| Перечитать конфигурацию из SQL | `SELECT pg_reload_conf();` |
| Где каталог данных и конфигурация | `SHOW data_directory; SHOW config_file; SHOW hba_file;` |
| Изменить параметр | `ALTER SYSTEM SET имя = 'значение';` + `reload` или `pg_conftool NN main set имя значение` |
| Что требует перезапуска | `SELECT name FROM pg_settings WHERE pending_restart;` |
| Проверить конфигурацию до `reload` | `SELECT * FROM pg_file_settings WHERE error IS NOT NULL;` |
| Проверить `pg_hba.conf` | `SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;` |
| Создать роль | `CREATE ROLE имя LOGIN PASSWORD '...';` или `createuser -P имя` |
| Сменить пароль | `\password имя` |
| Создать базу | `CREATE DATABASE имя OWNER роль;` или `createdb -O роль имя` |
| Скопировать базу | `CREATE DATABASE копия TEMPLATE исходная;` |
| Переименовать базу | `ALTER DATABASE старое RENAME TO новое;` |
| Удалить базу с сеансами | `DROP DATABASE имя WITH (FORCE);` или `dropdb -f имя` |
| Список баз с размерами | `\l+` |
| Таблицы с размерами | `\dt+` |
| Размер базы | `SELECT pg_size_pretty(pg_database_size('имя'));` |
| Активные сеансы | `SELECT pid, usename, datname, state, query FROM pg_stat_activity;` |
| Отменить запрос / завершить сеанс | `SELECT pg_cancel_backend(pid);` / `SELECT pg_terminate_backend(pid);` |
| Кто кого блокирует | запрос 18 из раздела 18 (`pg_blocking_pids`) |
| Хвост журнала | `sudo tail -f /var/log/postgresql/postgresql-NN-main.log` |
| Текущий файл журнала сборщика | `SELECT pg_current_logfile();` |
| Готов ли сервер | `pg_isready -h хост -p порт` |
| Состояние кластера с диска | `sudo -u postgres /usr/lib/postgresql/NN/bin/pg_controldata каталог_данных` |
| Создать второй кластер | `sudo pg_createcluster -p 5433 --locale ru_RU.UTF-8 --start NN имя` |
| Удалить кластер | `sudo pg_dropcluster --stop NN имя` |
| Сменить порт | `sudo pg_conftool NN main set port 5433` + перезапуск; Postgres Pro: `pg-setup set-server-port 5433` |
| Установить расширение | `CREATE EXTENSION имя;` |
| Список расширений | `\dx` |
| Время работы сервера | `SELECT now() - pg_postmaster_start_time();` |
| Текущий LSN | `SELECT pg_current_wal_lsn();` |
| Отставание реплик | `SELECT application_name, replay_lag FROM pg_stat_replication;` |

## Что не удалось подтвердить

Состояние на 2026-10-10 после фактчека. Поиск в интернете не работал ни при написании, ни при рецензии (исчерпан лимит запросов); первоисточники читались напрямую по известным адресам, а материалы сообщества (Инфостарт, Хабр, форумы) найти и перечитать было нечем. Поэтому всё, что помечено «практика», опирается на память, а не на перечитанные публикации.

Остаётся не подтверждённым первоисточником:

1. Сборка «Postgres Pro 1С»: каталог данных `/var/lib/pgpro/1c-NN/data`, имя службы `postgrespro-1c-NN`, файл `/etc/default/postgrespro-1c-NN` и его формат (имя переменной с каталогом данных), наличие `ExecReload` в юните. Каталог программ `/opt/pgpro/1c-17/bin` и команды `pg-setup` подтверждены файлом `meta.json` репозитория. Проверка: `dpkg -L postgrespro-1c-17-server`, `systemctl cat postgrespro-1c-17`, `cat /etc/default/postgrespro-1c-17`.
2. Форма `pg-setup initdb --tune=1c` для версий 17–18 и наличие `pgpro_tune` в бесплатной сборке `postgrespro-1c-NN` (для версии 12 синтаксис `pg-setup initdb [--tune=конфигурация]` документирован).
3. Каталог Unix-сокета (ожидается `/tmp`) и расположение журнала сервера в сборках Postgres Pro.
4. Что deb-пакеты «PostgreSQL с патчем от 1С» зависят от `postgresql-common` и создают кластер `NN/main` в `/etc/postgresql/NN/main` (каталог программ `/usr/lib/postgresql/NN/bin` подтверждён официальным Dockerfile 1С).
5. Значение `application_name` у соединений сервера 1С (`1CV8Server` или `1CV8`).
6. Что прямой доступ к данным 1С является именно нарушением лицензионного соглашения (сам запрет на нештатную работу с данными подтверждён статьями ИТС).
7. Приём сброса пароля через `v8users` и `users.usr`: первоисточника нет, на 8.3.27 и 8.5 не проверен, противоречит описанной в ИТС проверке обязательных служебных таблиц.
8. Фактическое имя таблицы пользователей (`v8users` по ИТС 1591 и практике, `_v8users` по ИТС 1798), таблицы регистрации изменений констант (`_ConstsChngR` по ИТС, `_ConstChngR<n>` по практике) и таблицы значений субконто (`_AccRgED<n>` или `_AccntRegED<n>`) — проверяется только в живой базе командой `\dt`.
9. Суффиксы полей составного типа `_L`, `_N`, `_T`, `_S` (раздел ИТС «Особенности хранения составных типов данных» не прочитан); имена временных таблиц `tt<N>`.
10. Минимальная версия платформы для сборки «PostgreSQL с патчем от 1С» версий 16 и 17 (для Postgres Pro — подтверждено, см. 1.3).
11. Поведение платформы 1С после `ALTER ROLE ... NOSUPERUSER` (документация 1С разрешает отзыв после создания информационной базы; какие операции после этого перестают работать — не проверено) и после ручного переноса отдельных таблиц в другое табличное пространство. У платформы есть собственный механизм табличных пространств (в статье ИТС 1798, редакция для 8.3.27, описаны таблицы `_DbSegments`, `_DbSegmentsItems`; с какой версии он появился и какая лицензия нужна — не проверено) — как он сочетается с ручным `ALTER TABLE ... SET TABLESPACE`, тоже не проверено.
12. Мелочи, отмеченные «⚠» по тексту: поведение `\watch` с именованными опциями в psql 15 и старше, версия появления `initdb --sync-method`, логика выбора версии обёрткой `/usr/bin/pg_config`, синтаксис `pg_backupcluster`.

Снято с этого списка при рецензии (подтверждено, источник указан в тексте): версии PostgreSQL и статус 19 Beta 4; версии пакетов Ubuntu; владелец, группа и режим файла журнала (`0640`, `postgres:adm`); содержимое `logrotate`; отсутствие профиля AppArmor в пакетах Ubuntu 24.04 и 26.04; `RequiresMountsFor` в юните; метод `scram-sha-256` для `host` у `pg_createcluster` (PostgreSQL 14+); версии появления опций `\watch`; расположение `pg_config` по пакетам; запрет 1С на нештатную работу с данными; имена и назначение служебных таблиц; минимальные версии платформы для Postgres Pro 16/17/18.

## Источники

Официальная документация PostgreSQL (версия 18, читалась 2026-10-10):

- https://www.postgresql.org/support/versioning/ — таблица версий, текущие выпуски, сроки поддержки.
- https://www.postgresql.org/ — даты выпусков 18.6/17.11/16.15/15.19/14.24, состояние PostgreSQL 19 (Beta 4).
- https://www.postgresql.org/docs/current/app-psql.html — ключи psql, метакоманды, переменные, приглашение, `psqlrc`, `\copy`, `\watch`, коды возврата.
- https://www.postgresql.org/docs/current/libpq-pgpass.html — формат и права `~/.pgpass`.
- https://www.postgresql.org/docs/current/libpq-envars.html — переменные окружения `PG*`, предупреждение о `PGPASSWORD`.
- https://www.postgresql.org/docs/current/libpq-connect.html — URI и строки подключения, `target_session_attrs`, `sslmode`.
- https://www.postgresql.org/docs/current/app-pg-ctl.html — `pg_ctl`, режимы остановки, тайм-ауты, коды возврата.
- https://www.postgresql.org/docs/current/app-initdb.html — ключи `initdb`, контрольные суммы по умолчанию в 18, метод `trust`.
- https://www.postgresql.org/docs/current/app-pg-isready.html, app-pgcontroldata.html, app-pgconfig.html, app-pgchecksums.html, pgwaldump.html, pgarchivecleanup.html, app-pgresetwal.html — служебные утилиты.
- https://www.postgresql.org/docs/current/sql-createrole.html, app-createuser.html — роли.
- https://www.postgresql.org/docs/current/sql-createdatabase.html, sql-alterdatabase.html, sql-dropdatabase.html, app-createdb.html, app-dropdb.html — базы данных.
- https://www.postgresql.org/docs/current/ddl-priv.html, sql-grant.html, predefined-roles.html, sql-reassign-owned.html — права, предопределённые роли, смена владельца.
- https://www.postgresql.org/docs/current/manage-ag-tablespaces.html, sql-altertable.html — табличные пространства и перенос таблиц.
- https://www.postgresql.org/docs/current/config-setting.html, sql-altersystem.html, runtime-config-file-locations.html, view-pg-settings.html, view-pg-file-settings.html, view-pg-hba-file-rules.html — конфигурация.
- https://www.postgresql.org/docs/current/monitoring-stats.html, view-pg-locks.html, progress-reporting.html — `pg_stat_activity`, статистика, блокировки, ход операций.
- https://www.postgresql.org/docs/current/functions-admin.html, functions-info.html — функции администрирования, размеров, WAL, сведения о сеансе и сервере.
- https://www.postgresql.org/docs/current/runtime-config-logging.html — параметры журналирования, `log_line_prefix`.
- https://www.postgresql.org/docs/current/sql-createextension.html — расширения.

Ubuntu и Debian:

- https://manpages.ubuntu.com/manpages/noble/en/man1/pg_createcluster.1.html, pg_ctlcluster.1.html, pg_lsclusters.1.html, pg_dropcluster.1.html, pg_renamecluster.1.html, pg_conftool.1.html, pg_upgradecluster.1.html, pg_wrapper.1.html — обёртки `postgresql-common`, пути по умолчанию, `start.conf`.
- https://ubuntu.com/server/docs/how-to/databases/install-postgresql/ — пути конфигурации в Ubuntu, `listen_addresses`, смена метода `host` на `scram-sha-256`.
- https://packages.ubuntu.com/ (поиск пакета `postgresql`) — версии PostgreSQL в выпусках Ubuntu.
- https://salsa.debian.org/postgresql/postgresql-common/ — `systemd/README.systemd` (юниты `postgresql@версия-кластер`, «зонтичный» `postgresql.service`, генератор), `createcluster.conf`, `debian/postgresql-common.logrotate`.

Postgres Pro:

- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux — пакеты, `/opt/pgpro/std-17`, `/var/lib/pgpro/std-17/data`, служба, предупреждение о метапакете.
- https://postgrespro.ru/docs/postgrespro/17/pg-setup — подкоманды `pg-setup`.
- https://postgrespro.ru/docs/postgrespro/17/pg-wrapper — `pg-wrapper links update|remove`.
- https://postgrespro.ru/docs/postgrespro/17/app-pgpro-tune, app-initdb — `pgpro_tune`, пресет `1c.tune`, `--tune`, провайдер локали по умолчанию.
- https://postgrespro.ru/docs/postgrespro/17/config-one-c и подразделы one-c-configuring-locale, one-c-basic-server-requirements, one-c-configuring-server, one-c-additional-modules — локаль `ru_RU.UTF-8`, модули `mchar`, `fulleq`, `fasttrun`, `plantuner`, `online_analyze`, параметры для 1С.
- https://repo.postgrespro.ru/1c/ — ветки `1c-14` … `1c-18`, `meta.json` (версия 17.10, поддерживаемые ОС, имена пакетов), `keys/pgpro-repo-add.sh` (файл `/etc/apt/sources.list.d/postgresql-1c-17.list`), индекс `Packages` для noble.
- https://1c.postgres.ru/ — условия использования бесплатных сборок для 1С.

1С:

- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/spisok-podderzhivaemykh-subd/ — поддерживаемые версии PostgreSQL и Postgres Pro.
- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/subd-postgresql/ — ОС, на которых поддерживается «PostgreSQL с патчем от 1С» (Ubuntu 20.04–26.04).
- https://its.1c.ru/db/metod8dev/content/1798/hdoc — «Размещение данных 1С:Предприятия 8. Таблицы и поля» (редакция для 8.3.27): имена служебных таблиц, поля, префиксы таблиц объектов. При рецензии использован конспект `kb/its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`.
- https://its.1c.ru/db/metod8dev/content/1591/hdoc — «Размещение данных 1С:Предприятия 8» (публикация 26.03.2019, по содержанию — эпоха 8.0–8.2): обязательные служебные таблицы, их проверка при старте, запрет на нештатную работу с данными, резервное копирование только целиком. Конспект — `kb/its-metod/razmeshchenie-dannyh-i-indeksy.md`.
- https://its.1c.ru/db/metod8dev/content/5942/hdoc — инструкция 1С по сборке PostgreSQL с патчем (упоминание `postgresql-common`). Статья старая (PostgreSQL 9.6), использована только как косвенное подтверждение раскладки.
- Локальные конспекты документации ИТС в этой базе знаний: `kb/its-docs/adm-gl05-spisok-infobaz.md` (требования к имени базы PostgreSQL, формат `сервер port=N;`, `SUPERUSER` только на момент создания ИБ); `kb/its-docs/adm-pr07-parametry-zapuska-1cv8-p1.md` и `kb/its-docs/cs-gl05-administrirovanie-klastera-p1.md` (код разрешения и параметр `/UC`); `kb/its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md` (официальные примеры запросов с суффиксами `_TYPE`, `_RTRef`, `_RRRef`; команда `pg_dump` «лёгкой» копии с вырезанием `users.usr`).

Проверено дополнительно при рецензии 2026-10-10 (фактчек):

- https://www.postgresql.org/docs/release/16.0/ — `\watch` с числом повторов и именованными опциями, `\bind`, `\drg`, новые ключи `createuser`, `initdb -c`, номера правил и имя файла в `pg_hba_file_rules`.
- https://www.postgresql.org/docs/release/17.0/ — `\watch min_rows`, `pg_archivecleanup --clean-backup-history` и длинные ключи, право `MAINTAIN` и роль `pg_maintain`, `allow_alter_system`, `transaction_timeout`, `pg_stat_checkpointer`, встроенный провайдер локали.
- https://www.postgresql.org/docs/release/18.0/ — модификатор `x`, `WATCH_INTERVAL`, конвейерные команды psql, табличный `\conninfo`, контрольные суммы по умолчанию, `log_connections`, `file_copy_method`, `extension_control_path`, `pg_signal_autovacuum_worker`, устаревание MD5.
- https://www.postgresql.org/docs/release/17.6/ — `\restrict` (CVE-2025-8714), дата выпуска 2025-08-14.
- https://www.postgresql.org/docs/18/view-pg-hba-file-rules.html и https://www.postgresql.org/docs/15/view-pg-hba-file-rules.html — состав столбцов представления в 18 и в 15.
- https://www.postgresql.org/docs/18/app-psql.html, app-pg-ctl.html, app-initdb.html, app-pgresetwal.html, app-pgchecksums.html, app-createuser.html, sql-createdatabase.html, sql-alterdatabase.html, sql-altersystem.html, ddl-priv.html, predefined-roles.html, monitoring-stats.html, runtime-config-logging.html, functions-admin.html — сверка синтаксиса, умолчаний и формулировок по разделам 4–15.
- https://salsa.debian.org/postgresql/postgresql-common/-/raw/master/pg_createcluster и .../pg_ctlcluster — исходный код: метод аутентификации по умолчанию (`scram-sha-256` для версий 14+), каталог сокета, создание файла журнала (`0640`, группа `adm`), перенаправление в `systemctl`.
- https://salsa.debian.org/postgresql/postgresql-common/-/raw/master/debian/postgresql-common.logrotate — точное содержимое правила ротации.
- https://sources.debian.org/src/postgresql-common/278/systemd/ — юниты `postgresql.service` и `postgresql@.service` (`RequiresMountsFor`, `TimeoutStopSec=1h`, `OOMScoreAdjust=-900`), `debian/postgresql-common.postinst` (пользователь `postgres`, домашний каталог `/var/lib/postgresql`, права `/var/log/postgresql` и `/var/run/postgresql`), `createcluster.conf`.
- https://salsa.debian.org/postgresql/postgresql/-/raw/18/debian/patches/series и патч `54-debian-alternatives-for-external-tools.patch` — редактор `sensible-editor` и `pager` по умолчанию в psql из пакетов Debian/Ubuntu; патч `51-default-sockets-in-var.patch` (по названию) — сокет в `/var/run/postgresql`.
- https://packages.ubuntu.com/ — версии пакета `postgresql` по выпускам; списки файлов `postgresql-16`, `postgresql-client-16`, `postgresql-server-dev-16`, `libpq-dev`, `postgresql-common` (noble) и `postgresql-18` (resolute): расположение `pg_config`, состав `bin`, модули contrib в серверном пакете, отсутствие профилей AppArmor, шаблоны юнитов.
- https://postgrespro.ru/docs/postgrespro/12/binary-installation-on-linux, https://postgrespro.ru/docs/postgrespro/13/pg-setup, .../14/pg-setup, .../15/pg-setup, https://postgrespro.ru/docs/postgrespro/18/binary-installation-on-linux — история аргумента `tune` у `pg-setup initdb`, файл в `/etc/default`, `PG_OOM_ADJUST_VALUE`, порядок создания второго экземпляра.
- https://postgrespro.ru/docs/postgrespro/17/runtime-config-connection — умолчание `unix_socket_directories`; https://postgrespro.ru/docs/postgrespro/17/mchar — семантика сравнения `mchar`/`mvarchar`.
- https://repo.postgrespro.ru/1c/1c-17/meta.json — официальные команды установки сборки «Postgres Pro 1С» (`/opt/pgpro/1c-17/bin/pg-setup initdb`, `service enable`, `service start`), список ОС.
- https://dl03.1c.ru/content/Platform/8_5_4_1306/1cv8upd_8_5_4_1306.htm — «Список изменений» платформы 8.5.4.1306: схема БД PostgreSQL (`--db-schema`, 8.5.4), с каких версий платформы поддерживаются Postgres Pro 13–18, прекращение поддержки PostgreSQL ≤ 9.6 (8.5.1). Документ прочитан частично (первые 300 тыс. знаков из 685 тыс.).
- https://raw.githubusercontent.com/1C-Company/docker_fresh/master/images/db/Dockerfile — официальный Dockerfile 1С: установка deb-пакетов сборки 1С, каталог `/usr/lib/postgresql/${VERSION}/bin`.

