# Репликация, отказоустойчивость PostgreSQL для 1С и обновление версий

> **Официальные тексты по теме** (конспекты документации ИТС 8.3.27 и методических статей ИТС, составлены по полным текстам): `../its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md`, `../its-metod/pg-sborka-arhivirovanie-rezervnoe-kopirovanie.md`. Статья писалась до получения доступа к закрытой документации: там, где ниже сказано «документация закрыта», «не прочитано» или стоит ⚠, сверяйтесь с этими конспектами — при расхождении правы они.

> Проверено независимой сверкой 19.10.2026: статья прочитана целиком; ключи `pg_basebackup`, `pg_rewind`, `pg_upgrade`, `pg_createsubscriber`, параметры репликации и их умолчания, колонки `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_replication_slots`, функции управления восстановлением и слотами, тексты сообщений сверены с документацией PostgreSQL 18, замечаниями к выпускам 13–18 и 14.24/16.15/17.11/18.6, исходным кодом (`pg_rewind`, `pg_upgrade`, `postinit.c`, libpq 14); Patroni — с документацией и журналом выпусков 4.1.5; PgBouncer, repmgr, pg_auto_failover, vip-manager — с официальной документацией и README; BiHA, proxima, multimaster, встроенный пул — с документацией Postgres Pro Enterprise 16/17; пути, служба, `pg-setup`, контрольные суммы, `dbcopies_decoding` — с документацией «PostgreSQL для 1С» 16, индексами репозитория и сценариями пакета `postgrespro-1c-16-server` 16.14; версии пакетов — с packages.ubuntu.com; утверждения о платформе 1С — с конспектами ИТС (`../its-docs/`, `../its-metod/`) и списком СУБД на v8.1c.ru. Исправлено 13 ошибок, закрыто 3 пометки (одна сужена, одна добавлена — о применимости «Версии 2» копий БД к «PostgreSQL для 1С»); на сервере не проверялось. Ранее, 10.10.2026, выполнена программная сверка имён, умолчаний и утверждений «появилось в версии N» — расхождений не найдено.

> Область: потоковая репликация, переключение ролей, автоматический failover (Patroni и аналоги), подключение 1С к отказоустойчивой СУБД, пулеры соединений, механизм «Копии базы данных», обновление минорных и мажорных версий PostgreSQL, обновление ОС (правила сортировки), перенос сервера БД | Версии: Ubuntu Server 22.04 / 24.04 / 26.04 LTS; платформа «1С:Предприятие» 8.3.22–8.3.27 и 8.5.x; PostgreSQL 14–18 в сборках для 1С (сборка от 1С, «PostgreSQL для 1С» и Postgres Pro Standard/Enterprise от Postgres Professional); Patroni 2.1–4.1 | Актуальность: 2026-10-10, сверка 2026-10-19

Условные обозначения:

- **[офиц.]** — взято из первоисточника (документация PostgreSQL, Patroni, PgBouncer, Postgres Pro, сайт и документация 1С, man-страницы Ubuntu); адреса — в разделе «Источники».
- **[офиц., ИТС 5971]** — статья ИТС «Построение отказоустойчивого кластера PostgreSQL…» (по конспекту `kb/its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md`).
- **[практика]** — сложившаяся практика сообщества, не официальная рекомендация.
- **⚠ не подтверждено** — первоисточник прочитать не удалось или утверждение является выводом составителя; перед применением проверить.

Ограничение этой версии статьи: веб-поиск при подготовке был недоступен, читались только страницы с известными адресами (документация PostgreSQL 18, Patroni, PgBouncer, Postgres Pro, v8.1c.ru, packages.ubuntu.com). Разделы its.1c.ru закрыты подпиской. Практика сообщества (Инфостарт, Хабр, форумы) приведена по памяти составителя и помечена.

В примерах используются два варианта раскладки каталогов (подробно — статья 01 этого раздела):

| | Сборка от 1С (раскладка Debian/Ubuntu) | «PostgreSQL для 1С» / Postgres Pro |
|---|---|---|
| Программы | `/usr/lib/postgresql/17/bin` | `/opt/pgpro/1c-17/bin` (Standard: `/opt/pgpro/std-17/bin`) |
| Каталог данных (PGDATA) | `/var/lib/postgresql/17/main` | `/var/lib/pgpro/1c-17/data` |
| Конфигурация | `/etc/postgresql/17/main/` (вне PGDATA) | внутри PGDATA |
| Служба systemd | `postgresql@17-main` | `postgrespro-1c-17` |
| Обёртки | `pg_lsclusters`, `pg_ctlcluster`, `pg_upgradecluster` | `pg-setup`, `pg-wrapper` |

Адреса в примерах: `pg1` 192.168.1.11 (ведущий), `pg2` 192.168.1.12 (резервный), `pg3` 192.168.1.13, виртуальный адрес 192.168.1.10, сервер 1С 192.168.1.20, кластер PostgreSQL версии 17.

Для ветки 16 «PostgreSQL для 1С» (её использует администратор этой базы знаний) в командах подставляйте `16` вместо `17`: программы — `/opt/pgpro/1c-16/bin`, каталог данных — `/var/lib/pgpro/1c-16/data`, служба — `postgrespro-1c-16`, путь к каталогу данных записан в `/etc/default/postgrespro-1c-16` (сверено 19.10.2026 по странице `pg-setup` документации сборки 16 и сценарию `postinst` пакета `postgrespro-1c-16-server` 16.14-1.noble). Локаль в примерах — `ru_RU.UTF-8`; кластер для международных конфигураций (WE) создают в `en_US.UTF-8` — везде, где ниже указана локаль, берите ту, в которой создан ваш кластер (`SELECT datname, datcollate FROM pg_database;`).

---

## Кратко — главные факты и команды

1. **В самом PostgreSQL нет автоматического переключения на резервный сервер** — он лишь умеет реплицировать WAL и по команде повышать реплику. Обнаружение сбоя, выбор нового ведущего и перенос адреса делает внешнее ПО [офиц.]. Для 1С фирма «1С» описывает связку **Patroni + etcd + HAProxy** [офиц., ИТС 5971].
2. **Физическая потоковая репликация** копирует кластер целиком (все базы, побайтно). Требует одинаковой мажорной версии, одинаковой архитектуры и — на практике — одинаковой сборки (с расширениями `mchar`, `fulleq`, `fasttrun`) и одинакового выпуска ОС на всех узлах.
3. **Минимальная настройка реплики:** на ведущем — роль с `REPLICATION`, строка `host replication …` в `pg_hba.conf`, `wal_level = replica` (значение по умолчанию); на резервном —
   ```bash
   sudo -u postgres pg_basebackup -h 192.168.1.11 -U replicator -D /var/lib/postgresql/17/main \
        -X stream -C -S pg2 -R -c fast -P
   ```
   Ключ `-R` создаёт `standby.signal` и дописывает `primary_conninfo` (и `primary_slot_name`) в `postgresql.auto.conf` [офиц.].
4. **Слот репликации не даёт ведущему удалить WAL, который реплика ещё не получила.** Если реплика выключена — `pg_wal` растёт до заполнения диска. Обязательно ограничить: `max_slot_wal_keep_size = 20GB` (по умолчанию `-1`, без предела) и следить за `pg_replication_slots.wal_status` [офиц.].
5. **Резервный сервер доступен только на чтение, включая временные таблицы.** 1С создаёт временные таблицы почти в каждом запросе, поэтому **подключить 1С (даже отчёты) напрямую к реплике нельзя** [офиц., PostgreSQL и ИТС 5971].
6. **Рекомендованный для 1С `synchronous_commit = off` несовместим с синхронной репликацией:** при `off` фиксация не ждёт ни локального диска, ни реплики [офиц.]. Хотите «ноль потерь» — нужен `synchronous_commit = on` (или `remote_write`) и `synchronous_standby_names`; платой будет задержка каждой фиксации.
7. **Отставание:** на ведущем — `SELECT application_name, state, sync_state, replay_lag, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) FROM pg_stat_replication;`, на реплике — `SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(), pg_last_xact_replay_timestamp();` и `pg_stat_wal_receiver`.
8. **Повышение реплики:** `sudo pg_ctlcluster 17 main promote` (Debian-раскладка), `pg_ctl promote -D PGDATA` или `SELECT pg_promote();` [офиц.]. Перед этим старый ведущий должен быть гарантированно остановлен или изолирован — иначе **split-brain** (два сервера принимают запись).
9. **Вернуть старый ведущий в строй репликой:** `pg_rewind` (нужны контрольные суммы данных или `wal_log_hints = on`, целевой сервер остановлен) либо полное пересоздание через `pg_basebackup` [офиц.].
10. **Patroni:** `patronictl list`, `patronictl switchover` (плановое, кластер здоров), `patronictl failover` (аварийное, возможна потеря данных), `patronictl edit-config` (параметры PostgreSQL задаются через Patroni), `patronictl pause/resume` (режим обслуживания) [офиц.]. Актуальная версия — 4.1.5 от 12.08.2026; в Ubuntu: 22.04 — 2.1.3, 24.04 — 3.2.2, 26.04 — 4.1.0 (пакет `patroni`, universe) [офиц.].
11. **В свойствах инфобазы 1С указывается одно имя сервера СУБД** (формат `имя port=5433;`). Перечислить несколько серверов PostgreSQL, по утверждению фирмы «1С», нельзя, поэтому нужна единая точка входа: HAProxy, виртуальный IP (keepalived, vip-manager) или DNS-имя [офиц., ИТС 5971]. Сменить адрес: `rac infobase update --cluster=… --infobase=… --db-server=новый_адрес`.
12. **При переключении СУБД все соединения 1С с PostgreSQL рвутся:** выполняющиеся операции и фоновые задания завершаются ошибкой, открытые транзакции откатываются; сеансы пользователей в кластере 1С сохраняются, следующие обращения идут уже на новый ведущий [практика; ИТС 5971 — «сеанс не должен заметить изменений»].
13. **PgBouncer в режиме `transaction` для 1С не годится:** в этом режиме не поддерживаются `SET` на уровне сеанса и временные таблицы, живущие дольше транзакции [офиц., pgbouncer.org], а 1С использует и то и другое. Режим `session` работает, но числа соединений не сокращает.
14. **`multimaster` (Postgres Pro Enterprise) с 1С не работает:** в документации прямо сказано «Решения 1С не поддерживаются» [офиц.]. BiHA (встроенная отказоустойчивость на физической репликации) архитектурно совместима; явного упоминания 1С в её документации не найдено ⚠.
15. **Механизм «Копии базы данных»** — функция платформы уровня КОРП: копия части или всех таблиц в другой базе/СУБД или в Дата акселераторе, на которую платформа направляет запросы отчётов. Для PostgreSQL с платформы 8.3.25 обновление копии (версия 2) идёт через логическое декодирование: `wal_level = logical` и модуль `dbcopies_decoding` из сборки для 1С [офиц.].
16. **Минорное обновление** (17.10 → 17.11): обновить пакеты, перезапустить службу, прочитать замечания к выпуску. В кластере с репликами сначала обновляют резервные серверы, затем ведущий [офиц.].
17. **Внимание — минорные выпуски от 13.08.2026 (18.6, 17.11, 16.15, 15.19, 14.24):** добавлен параметр `output_plugin_libraries` — белый список модулей логического декодирования, по умолчанию `'pgoutput, test_decoding'` [офиц., замечания к выпускам]. Если используется механизм копий базы данных 1С, после обновления в список нужно добавить модуль 1С (`dbcopies_decoding`) ⚠. На 19.10.2026 сборок для 1С с этим параметром ещё нет: в репозитории «PostgreSQL для 1С» (Ubuntu 24.04) последние выпуски — 14.23, 15.18, 16.14, 17.10, 18.4, в списке протестированных фирмой «1С» — те же номера.
18. **Мажорное обновление** (17 → 18): `pg_upgrade --check`, затем `pg_upgrade` (при желании `--link`); в Debian-раскладке — `sudo pg_upgradecluster -m upgrade -v 18 17 main`. Новая версия должна быть сборкой для 1С с теми же расширениями и поддерживаться вашей версией платформы. После — сбор статистики (`vacuumdb --all --analyze-in-stages`) [офиц.].
19. **Обновление выпуска Ubuntu меняет glibc (22.04 — 2.35, 24.04 — 2.39, 26.04 — 2.43) и ICU**, от которых зависит порядок сортировки строк в индексах. PostgreSQL предупреждает `collation version mismatch`; лечение — `REINDEX` и `ALTER DATABASE … REFRESH COLLATION VERSION` [офиц.]. Реплика на другом выпуске ОС, чем ведущий, может получить «битые» индексы.
20. **Репликация — не резервная копия:** ошибочный `DELETE`, порча данных прикладной ошибкой или удаление базы мгновенно попадают на реплики. Резервное копирование (статья 04) обязательно при любой схеме.

---

## 1. Понятия и выбор схемы

### 1.1. Термины

| Термин | Смысл |
|---|---|
| Ведущий (primary, leader, «мастер») | единственный сервер кластера, принимающий запись |
| Резервный (standby, replica, follower) | сервер, непрерывно применяющий WAL ведущего; при `hot_standby = on` принимает запросы только на чтение |
| Потоковая репликация | передача WAL по сети от процесса `walsender` (ведущий) к `walreceiver` (резервный) |
| Слот репликации | объект на ведущем, удерживающий WAL для конкретного потребителя |
| Линия времени (timeline, TL) | номер «ветки истории» кластера; увеличивается при каждом повышении реплики |
| Switchover | плановая смена ролей без потери данных |
| Failover | аварийное повышение реплики после отказа ведущего |
| Split-brain | два сервера одновременно считают себя ведущими и принимают запись |
| STONITH / fencing | принудительная изоляция («выстрел в голову») старого ведущего |
| DCS | распределённое хранилище состояния кластера (etcd, Consul, ZooKeeper, Kubernetes) |
| RPO / RTO | допустимая потеря данных / допустимое время восстановления |

### 1.2. Что даёт каждая схема

| Схема | RPO | RTO | Сложность | Комментарий |
|---|---|---|---|---|
| Один сервер + резервные копии и архив WAL | минуты (архив WAL) — сутки (только дампы) | десятки минут — часы | низкая | базовый вариант; для одной ВМ на рабочем месте обычно достаточно |
| Ведущий + асинхронная реплика, ручное переключение | секунды | 5–30 минут (нужен человек) | средняя | самый частый «бюджетный» вариант [практика] |
| Ведущий + синхронная реплика | 0 для подтверждённых транзакций | как выше | средняя | каждая фиксация ждёт реплику; отказ единственной синхронной реплики останавливает запись |
| Patroni + etcd (3 узла) + HAProxy/VIP | секунды (асинхронно) или 0 (синхронный режим Patroni) | 30–60 секунд, автоматически | высокая | официально описанная фирмой «1С» схема [офиц., ИТС 5971] |
| Postgres Pro Enterprise BiHA | то же | автоматически | средняя (нужна лицензия) | без внешнего DCS; узел-рефери вместо третьего сервера данных |

Отказоустойчивость СУБД не отменяет отказоустойчивости остальных слоёв: кластера серверов 1С, сети, хранилища, питания, а главное — резервного копирования.

### 1.3. Чего репликация для 1С НЕ даёт

- **Масштабирования чтения.** Реплика PostgreSQL отвергает `CREATE TEMP TABLE`, `INSERT`, DDL: «temporary table creation is not allowed during read-only transactions» [офиц.]. Платформа 1С работает через временные таблицы, поэтому напрямую читать с реплики не может. Обходной путь для отчётов — механизм копий базы данных (раздел 10).
- **Защиты от логических ошибок.** Всё, что выполнено на ведущем, воспроизводится на репликах.
- **Независимости от версии.** Физическая репликация между разными мажорными версиями невозможна [офиц.].

---

## 2. Потоковая физическая репликация: настройка пошагово

### 2.1. Предварительные условия

| Условие | Основание |
|---|---|
| Одинаковая мажорная версия PostgreSQL на всех узлах | [офиц.] «log shipping between servers running different major PostgreSQL release levels is not possible» |
| Минорные версии желательно одинаковые; при обновлении сначала реплики, потом ведущий | [офиц.] |
| Одинаковая аппаратная архитектура (нельзя с 32 на 64 бита, с x86-64 на ARM) | [офиц.] |
| Одинаковая сборка: на реплике должны быть те же библиотеки (`mchar`, `fulleq`, `fasttrun`, `plantuner`, …) | иначе после повышения 1С не сможет работать; [практика] |
| Одинаковый выпуск ОС (версии glibc и ICU) | иначе возможна порча индексов на реплике (раздел 15) [офиц., wiki.postgresql.org] |
| Одинаковые пути табличных пространств | [офиц.] пути передаются без изменений |
| На реплике `max_connections`, `max_prepared_transactions`, `max_locks_per_transaction`, `max_wal_senders`, `max_worker_processes` не меньше, чем на ведущем | [офиц.] иначе восстановление встанет на паузу |
| Сеть между узлами: открыт порт PostgreSQL (5432), задержка минимальна | — |
| Время синхронизировано (chrony / systemd-timesyncd) | для корректных оценок отставания |

### 2.2. Ведущий сервер (pg1)

**Шаг 1. Параметры `postgresql.conf`.** Значения по умолчанию в PostgreSQL 14–18 уже достаточны для репликации; проверьте, что их не меняли:

```ini
# /etc/postgresql/17/main/postgresql.conf   (Postgres Pro: /var/lib/pgpro/1c-17/data/postgresql.conf)
listen_addresses = '*'            # или перечень адресов; по умолчанию 'localhost' - реплика не подключится
wal_level = replica               # по умолчанию replica; minimal репликацию отключает; logical - для копий БД 1С
max_wal_senders = 10              # по умолчанию 10; по одному на реплику + по два на каждый pg_basebackup -X stream
max_replication_slots = 10        # по умолчанию 10
wal_keep_size = 1GB               # по умолчанию 0; запас WAL на случай работы без слота
max_slot_wal_keep_size = 20GB     # по умолчанию -1 (без предела!) - защита диска от "мёртвого" слота
hot_standby = on                  # по умолчанию on; действует на сервере в роли реплики
wal_log_hints = on                # нужно для pg_rewind, если кластер создан без контрольных сумм данных
```

Изменение `wal_level`, `max_wal_senders`, `max_replication_slots`, `wal_log_hints`, `listen_addresses` требует перезапуска; `wal_keep_size`, `max_slot_wal_keep_size` — перечитывания конфигурации.

**Шаг 2. Роль для репликации.**

```sql
-- sudo -u postgres psql
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'СложныйПароль';
```

Атрибут `REPLICATION` даёт право на репликационное подключение и работу со слотами; права на чтение таблиц через SQL он не даёт.

**Шаг 3. `pg_hba.conf`.** Псевдобаза `replication` не входит в `all`, строка нужна отдельная [офиц.]. Сразу разрешите подключение в обе стороны — после переключения роли поменяются:

```text
# /etc/postgresql/17/main/pg_hba.conf
# TYPE  DATABASE     USER        ADDRESS            METHOD
host    replication  replicator  192.168.1.11/32    scram-sha-256
host    replication  replicator  192.168.1.12/32    scram-sha-256
host    replication  replicator  192.168.1.13/32    scram-sha-256
```

**Шаг 4. Применить.**

```bash
sudo systemctl restart postgresql@17-main        # если меняли параметры, требующие перезапуска
sudo systemctl reload  postgresql@17-main        # если меняли только pg_hba.conf и reload-параметры
sudo -u postgres psql -Atc "SELECT name, setting FROM pg_settings
     WHERE name IN ('wal_level','max_wal_senders','max_replication_slots','wal_log_hints','data_checksums');"
```

### 2.3. Резервный сервер (pg2), раскладка Debian/Ubuntu (сборка от 1С)

```bash
# 1. Установить ту же сборку PostgreSQL той же версии, что на ведущем (см. статью 01).
#    Пакет сам создаёт пустой кластер 17/main - его данные надо заменить копией ведущего.
pg_lsclusters
sudo systemctl stop postgresql@17-main

# 2. Убрать пустой каталог данных (каталог /etc/postgresql/17/main с конфигурацией остаётся).
sudo -u postgres mv /var/lib/postgresql/17/main /var/lib/postgresql/17/main.empty

# 3. Пароль роли репликации - в ~/.pgpass пользователя postgres (поле "база" = replication).
sudo -u postgres sh -c 'umask 077; echo "192.168.1.11:5432:replication:replicator:СложныйПароль" >> ~/.pgpass'

# 4. Снять базовую копию с ведущего, создать слот pg2 и записать настройки реплики.
sudo -u postgres /usr/lib/postgresql/17/bin/pg_basebackup \
     -h 192.168.1.11 -p 5432 -U replicator -w \
     -D /var/lib/postgresql/17/main \
     -X stream -C -S pg2 -R -c fast -P -v

# 5. Привести конфигурацию реплики в соответствие с ведущим (в этой раскладке она НЕ копируется):
#    перенести с pg1 файлы postgresql.conf, conf.d/*.conf и pg_hba.conf любым удобным способом
#    (scp, rsync, система управления конфигурацией), поправить listen_addresses, проверить владельца.
ls -l /etc/postgresql/17/main/ /etc/postgresql/17/main/conf.d/
sudo chown -R postgres:postgres /etc/postgresql/17/main

# 6. Запустить и проверить.
sudo systemctl start postgresql@17-main
sudo -u postgres psql -Atc "SELECT pg_is_in_recovery();"        # t - сервер в роли реплики
sudo tail -n 30 /var/log/postgresql/postgresql-17-main.log
```

В журнале реплики должны появиться строки `database system is ready to accept read-only connections` и `started streaming WAL from primary at … on timeline 1`.

Ключи `pg_basebackup`, важные для создания реплики [офиц.]:

| Ключ | Действие |
|---|---|
| `-D каталог` | куда писать копию; каталог должен быть пуст или отсутствовать |
| `-X stream` (по умолчанию) | передавать WAL параллельно копированию вторым соединением |
| `-C -S имя` | создать на ведущем постоянный слот и использовать его; без `-C` слот должен уже существовать; без `-S` используется временный слот |
| `-R` | создать `standby.signal` и дописать параметры подключения (и имя слота) в `postgresql.auto.conf` |
| `-c fast` | не растягивать начальную контрольную точку (по умолчанию `spread` — ждать придётся дольше) |
| `-P`, `-v` | индикатор хода и подробный вывод |
| `-r 50M` | ограничить скорость передачи, чтобы не «положить» ведущий |
| `-T старый=новый` | переназначить каталог табличного пространства |
| `-w` / `-W` | не спрашивать пароль / спросить сразу |

Копию можно снимать и с другого резервного сервера (нужны `max_wal_senders`, `hot_standby`, строка в `pg_hba.conf` на нём) [офиц.].

### 2.4. Резервный сервер, раскладка Postgres Pro («PostgreSQL для 1С»)

```bash
sudo systemctl stop postgrespro-1c-17
sudo -u postgres mv /var/lib/pgpro/1c-17/data /var/lib/pgpro/1c-17/data.empty
sudo -u postgres sh -c 'umask 077; echo "192.168.1.11:5432:replication:replicator:СложныйПароль" >> ~/.pgpass'

sudo -u postgres /opt/pgpro/1c-17/bin/pg_basebackup \
     -h 192.168.1.11 -p 5432 -U replicator -w \
     -D /var/lib/pgpro/1c-17/data \
     -X stream -C -S pg2 -R -c fast -P -v

sudo systemctl start postgrespro-1c-17
sudo -u postgres /opt/pgpro/1c-17/bin/psql -Atc "SELECT pg_is_in_recovery();"
```

Здесь `postgresql.conf` и `pg_hba.conf` лежат внутри каталога данных и приезжают вместе с копией — править нужно только то, что относится к конкретному узлу (`listen_addresses`, если задан адресом, а не `*`).

### 2.5. Что именно записывает ключ `-R`

```bash
sudo -u postgres ls -l /var/lib/postgresql/17/main/standby.signal
sudo -u postgres cat /var/lib/postgresql/17/main/postgresql.auto.conf
```

```ini
# postgresql.auto.conf на реплике (пример, сокращённо: реальная строка содержит и другие параметры libpq)
primary_conninfo = 'user=replicator passfile=''/var/lib/postgresql/.pgpass'' host=192.168.1.11 port=5432 sslmode=prefer'
primary_slot_name = 'pg2'
```

- `standby.signal` — пустой файл в каталоге данных. Его наличие при запуске переводит сервер в режим резервного: он не завершает восстановление, а бесконечно ждёт новый WAL [офиц.]. При повышении файл удаляется сервером.
- `primary_conninfo` — строка подключения libpq к ведущему. Пароль можно указать прямо в ней (`password=…`) или держать в `~/.pgpass`. Если пароль был передан через переменную `PGPASSWORD` или запрос, он попадёт в файл открытым текстом [практика].
- Рекомендуется сразу добавить в строку явное имя: `application_name=pg2` — по нему реплика видна в `pg_stat_replication` и в `synchronous_standby_names`. Без него используется значение `cluster_name` реплики, а если оно пусто — `walreceiver` [офиц.]. В Debian-раскладке `pg_createcluster` задаёт `cluster_name = '17/main'`, поэтому все реплики по умолчанию называются одинаково — `17/main` [практика].
- `recovery_target_timeline` по умолчанию `latest` — реплика сама переходит на новую линию времени после смены ведущего [офиц.].
- Параметры восстановления с PostgreSQL 12 задаются в `postgresql.conf` / `postgresql.auto.conf`; файла `recovery.conf` больше нет (его наличие не даст серверу запуститься).

Изменить источник репликации на работающей реплике:

```sql
ALTER SYSTEM SET primary_conninfo = 'host=192.168.1.12 port=5432 user=replicator application_name=pg1';
SELECT pg_reload_conf();      -- walreceiver переподключится без перезапуска сервера
```

### 2.6. Параметры репликации: справочник

Значения по умолчанию — PostgreSQL 18 [офиц.].

| Параметр | Где действует | По умолчанию | Смысл |
|---|---|---|---|
| `wal_level` | ведущий | `replica` | `minimal` / `replica` / `logical`; только при запуске |
| `max_wal_senders` | отправитель | `10` | максимум процессов `walsender`; `0` выключает репликацию; только при запуске |
| `max_replication_slots` | отправитель | `10` | максимум слотов; только при запуске |
| `wal_keep_size` | отправитель | `0` | сколько МБ прошлого WAL держать в `pg_wal` для отстающих реплик |
| `max_slot_wal_keep_size` | отправитель | `-1` | предел WAL, удерживаемого слотами; `-1` — без предела |
| `idle_replication_slot_timeout` | отправитель | `0` | (PostgreSQL 18) аннулировать слот, простаивающий дольше заданного времени |
| `wal_sender_timeout` | отправитель | `60s` | разрывать репликационное соединение без активности |
| `synchronous_standby_names` | ведущий | пусто | список синхронных реплик (раздел 4) |
| `synchronous_commit` | ведущий, сеанс | `on` | чего ждёт `COMMIT` (раздел 4) |
| `primary_conninfo` | реплика | пусто | строка подключения к источнику WAL |
| `primary_slot_name` | реплика | пусто | имя слота на источнике |
| `hot_standby` | реплика | `on` | разрешить запросы на чтение при восстановлении; только при запуске |
| `max_standby_streaming_delay` | реплика | `30s` | сколько применение WAL ждёт конфликтующий запрос, прежде чем отменить его; `-1` — ждать вечно |
| `max_standby_archive_delay` | реплика | `30s` | то же для WAL из архива |
| `hot_standby_feedback` | реплика | `off` | сообщать ведущему о запросах реплики (меньше отмен запросов, но раздувание таблиц на ведущем) |
| `wal_receiver_status_interval` | реплика | `10s` | как часто реплика сообщает о своём прогрессе |
| `wal_receiver_timeout` | реплика | `60s` | разрывать соединение без активности со стороны реплики |
| `wal_retrieve_retry_interval` | реплика | `5s` | пауза перед повторной попыткой получить WAL |
| `recovery_min_apply_delay` | реплика | `0` | намеренная задержка применения («отложенная реплика» — защита от ошибочных действий) |
| `sync_replication_slots` | реплика | `off` | (PostgreSQL 17+) синхронизировать логические слоты с признаком `failover` с ведущего |
| `synchronized_standby_slots` | ведущий | пусто | (PostgreSQL 17+) физические слоты, которых ждут отправители логической репликации |
| `output_plugin_libraries` | отправитель | `'pgoutput, test_decoding'` | (с выпусков 08.2026) разрешённые модули логического декодирования |

Точный контекст изменения каждого параметра на вашем сервере: `SELECT name, setting, unit, context FROM pg_settings WHERE name LIKE '%standby%' OR name LIKE '%wal_%';`

---

## 3. Слоты репликации

### 3.1. Зачем и как

Без слота ведущий удаляет сегменты WAL по своим правилам (`max_wal_size`, `wal_keep_size`). Если реплика отстала сильнее — в её журнале появится `requested WAL segment … has already been removed`, и её придётся пересоздавать. Слот гарантирует, что нужный реплике WAL останется на диске ведущего [офиц.].

```sql
-- создать физический слот (если не создавали ключом -C у pg_basebackup)
SELECT * FROM pg_create_physical_replication_slot('pg2');
-- вторым аргументом true можно сразу зарезервировать WAL:
SELECT * FROM pg_create_physical_replication_slot('pg3', true);

-- список слотов
SELECT slot_name, slot_type, active, active_pid, restart_lsn, wal_status, safe_wal_size
FROM pg_replication_slots;

-- удалить слот (только неактивный)
SELECT pg_drop_replication_slot('pg2');
```

На реплике имя слота задаётся параметром `primary_slot_name = 'pg2'`. Один слот — один потребитель.

### 3.2. Главная опасность: переполнение диска

Слот неактивной реплики (выключена, сломана, забыта после `pg_basebackup -C`, `pg_receivewal`, удалённой копии базы 1С) удерживает WAL без ограничения. На нагруженной базе 1С (перепроведение, закрытие месяца, реструктуризация) это десятки гигабайт в час. Когда раздел с `pg_wal` заполняется, PostgreSQL аварийно останавливается (`PANIC: could not write to file "pg_wal/…": No space left on device`).

Защита:

```ini
max_slot_wal_keep_size = 20GB     # подобрать: меньше свободного места на разделе pg_wal с запасом
```

Когда слот упирается в предел, он аннулируется (реплику придётся пересоздать), зато ведущий продолжает работать. Состояние видно в `pg_replication_slots` [офиц.]:

| `wal_status` | Смысл |
|---|---|
| `reserved` | удерживаемый WAL в пределах `max_wal_size` |
| `extended` | `max_wal_size` превышен, но файлы удерживаются слотом или `wal_keep_size` |
| `unreserved` | слот больше не гарантирует наличие WAL; часть файлов удалится на следующей контрольной точке (ещё может вернуться в `reserved`/`extended`) |
| `lost` | нужный WAL удалён, слот непригоден |

`safe_wal_size` — сколько байт WAL ещё можно записать, прежде чем слот окажется под угрозой (`NULL` при `max_slot_wal_keep_size = -1`). `invalidation_reason` (PostgreSQL 17+): `wal_removed`, `rows_removed`, `wal_level_insufficient`, а с PostgreSQL 18 ещё `idle_timeout` (вместе с параметром `idle_replication_slot_timeout`). `inactive_since` (PostgreSQL 17+) — с какого момента слот неактивен.

### 3.3. Мониторинг слотов

```sql
-- на ведущем: сколько WAL удерживает каждый слот
SELECT slot_name, slot_type, active,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal,
       wal_status,
       pg_size_pretty(safe_wal_size) AS safe_left
FROM pg_replication_slots
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC NULLS LAST;
```

```bash
# размер каталога WAL и свободное место
sudo du -sh /var/lib/postgresql/17/main/pg_wal
df -h /var/lib/postgresql/17/main
```

Правила эксплуатации [практика]:

- оповещение при `active = false` дольше N минут и при `retained_wal` больше порога;
- реплику выводите из эксплуатации вместе со слотом (`pg_drop_replication_slot`);
- **никогда не удаляйте файлы из `pg_wal` вручную** — устраняйте причину (слот, архивация);
- слот удерживает не только WAL: при `hot_standby_feedback = on` он держит и горизонт очистки (`xmin`), мешая `VACUUM` на ведущем (статья 05);
- физические слоты на реплику не копируются; после повышения реплики слоты для остальных узлов создаются заново (Patroni делает это сам).

---

## 4. Асинхронная, синхронная и каскадная репликация

### 4.1. Асинхронная (по умолчанию)

Ведущий подтверждает `COMMIT` клиенту, не дожидаясь реплики. Реплика обычно отстаёт на доли секунды, но при отказе ведущего последние транзакции могут не успеть уйти — после повышения реплики их не будет. Для 1С это означает возможную потерю последних проведённых документов и, что неприятнее, рассогласование с внешними системами (обмены, отправленные сообщения, выданные номера) [практика].

### 4.2. Синхронная

```ini
# на ведущем
synchronous_standby_names = 'FIRST 1 (pg2, pg3)'   # ждать pg2; если он недоступен - pg3
# synchronous_standby_names = 'ANY 1 (pg2, pg3)'   # кворум: достаточно любой одной из перечисленных
synchronous_commit = on                             # обязательно НЕ off и НЕ local
```

Синтаксис `synchronous_standby_names` [офиц.]:

```text
[FIRST] число ( имя [, ...] )     -- по приоритету: первые "число" доступных реплик из списка
ANY число ( имя [, ...] )         -- кворум: любые "число" реплик из списка
имя [, ...]                       -- старая форма, равна FIRST 1
```

- Имена — это `application_name` реплик (см. 2.5), сравниваются без учёта регистра; `*` — любая реплика.
- Параметр перечитывается без перезапуска (`SELECT pg_reload_conf();`).
- Состояние видно в `pg_stat_replication.sync_state`: `sync`, `potential` (кандидат), `quorum`, `async`.

Чего ждёт `COMMIT` при непустом `synchronous_standby_names` [офиц.]:

| `synchronous_commit` | Чего ждёт фиксация | Что переживёт |
|---|---|---|
| `remote_apply` | реплика записала WAL на диск **и применила** (изменения видны запросам на реплике) | всё; самая большая задержка |
| `on` (по умолчанию) | реплика получила запись и сбросила её на диск | потерю ведущего |
| `remote_write` | реплика получила запись и передала её ОС (без `fsync`) | падение процесса PostgreSQL на реплике, но не падение ОС реплики |
| `local` | только локальный сброс на диск ведущего | реплику не ждёт |
| `off` | ничего не ждёт (даже локального диска; задержка до 3 × `wal_writer_delay`) | при сбое теряются последние транзакции, целостность базы сохраняется |

Если `synchronous_standby_names` пуст, значения `remote_apply`, `remote_write`, `local` равносильны `on` [офиц.].

**Конфликт с рекомендациями для 1С.** Документация Postgres Pro для 1С рекомендует `synchronous_commit = off` («при сбое можно потерять только последние транзакции») [офиц., приложение K.3]. С таким значением синхронная репликация фактически выключена, что бы ни стояло в `synchronous_standby_names`. Решение принимается осознанно:

- нужна максимальная скорость записи и допустима потеря секунд данных — `synchronous_commit = off`, репликация асинхронная;
- нужна гарантия «подтверждённая транзакция есть на двух серверах» — `synchronous_commit = on` или `remote_write`, и каждая фиксация 1С (а их очень много и они мелкие) будет ждать сетевого обмена и записи на диск реплики. Обязательно замерьте на копии базы.

Параметр можно задать не для всего кластера, а для базы или роли:

```sql
ALTER DATABASE buh SET synchronous_commit = 'remote_write';   -- только для базы buh
ALTER ROLE usr1cv8 SET synchronous_commit = 'on';             -- только для роли, под которой работает 1С
```

**Ловушка единственной синхронной реплики.** Если указана одна реплика и она недоступна, все фиксации на ведущем зависают в ожидании (для пользователей 1С — «всё встало», в `pg_stat_activity` ожидание `SyncRep`). Транзакции при этом уже зафиксированы локально. Выход:

```sql
ALTER SYSTEM SET synchronous_standby_names = '';
SELECT pg_reload_conf();
```

Поэтому синхронную репликацию строят минимум с двумя репликами (`FIRST 1 (pg2, pg3)` или `ANY 1 (…)`) либо отдают управление списком Patroni (`synchronous_mode`, раздел 7).

### 4.3. Каскадная

Реплика может сама быть источником WAL для других реплик — это разгружает ведущий и сеть до удалённой площадки.

```ini
# на pg3 (реплика второго уровня)
primary_conninfo = 'host=192.168.1.12 port=5432 user=replicator application_name=pg3'
```

На промежуточной реплике (pg2) нужны `max_wal_senders > 0`, `hot_standby = on` и строка `replication` в `pg_hba.conf`. Каскадная репликация всегда асинхронна; настройки синхронной репликации на неё не действуют [офиц.]. При повышении промежуточной реплики нижестоящие продолжают получать WAL с неё (при `recovery_target_timeline = 'latest'`).

---

## 5. Мониторинг репликации и отставания

### 5.1. На ведущем: `pg_stat_replication`

Одна строка на каждый процесс `walsender` (то есть на каждую напрямую подключённую реплику) [офиц.].

```sql
SELECT application_name, client_addr, state, sync_state,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn))   AS not_sent,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), flush_lsn))  AS not_flushed,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) AS not_replayed,
       write_lag, flush_lag, replay_lag, reply_time
FROM pg_stat_replication;
```

| Столбец | Смысл |
|---|---|
| `state` | `startup`, `catchup` (догоняет), `streaming` (норма), `backup` (идёт `pg_basebackup`), `stopping` |
| `sent_lsn` | до какой позиции WAL отправлен |
| `write_lsn` / `flush_lsn` / `replay_lsn` | до какой позиции реплика записала / сбросила на диск / применила |
| `write_lag` / `flush_lag` / `replay_lag` | задержка по времени для соответствующей стадии (то, чего стоили бы `remote_write` / `on` / `remote_apply`) |
| `sync_state` | `async`, `potential`, `sync`, `quorum` |
| `sync_priority` | приоритет в списке `FIRST` |
| `backend_xmin` | горизонт, сообщённый репликой при `hot_standby_feedback` |
| `reply_time` | время последнего ответа реплики |

Пустой результат означает, что ни одна реплика не подключена.

### 5.2. На реплике

```sql
-- роль и позиции
SELECT pg_is_in_recovery()                                   AS is_standby,
       pg_last_wal_receive_lsn()                             AS received,
       pg_last_wal_replay_lsn()                              AS replayed,
       pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()) AS apply_backlog_bytes,
       pg_last_xact_replay_timestamp()                       AS last_replayed_commit;

-- отставание по времени без ложных срабатываний при простое ведущего
SELECT CASE WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN interval '0'
            ELSE now() - pg_last_xact_replay_timestamp() END AS replay_delay;

-- состояние приёмника WAL (ровно одна строка, пока walreceiver работает)
SELECT status, sender_host, sender_port, slot_name,
       flushed_lsn, received_tli, latest_end_lsn, last_msg_receipt_time
FROM pg_stat_wal_receiver;

-- отменённые из-за конфликтов с восстановлением запросы
SELECT datname, confl_snapshot, confl_lock, confl_bufferpin, confl_tablespace, confl_deadlock
FROM pg_stat_database_conflicts;
```

Замечания:

- `pg_current_wal_lsn()` на реплике не работает (ошибка «recovery is in progress») — там используют `pg_last_wal_receive_lsn()` / `pg_last_wal_replay_lsn()`.
- `now() - pg_last_xact_replay_timestamp()` без условия растёт всё время, пока на ведущем нет транзакций, — это не отставание.
- Пустой `pg_stat_wal_receiver` на реплике — приёмник не запущен: смотрите журнал (неверный пароль, нет строки в `pg_hba.conf`, удалён нужный WAL, недоступна сеть).
- Приостановить и возобновить применение WAL: `SELECT pg_wal_replay_pause();`, `SELECT pg_wal_replay_resume();`, состояние — `SELECT pg_get_wal_replay_pause_state();` (`not paused`, `pause requested`, `paused`) [офиц.].

### 5.3. Что ставить на оповещение

| Проверка | Запрос / команда | Порог [практика] |
|---|---|---|
| Реплика подключена | `SELECT count(*) FROM pg_stat_replication WHERE state = 'streaming';` | меньше ожидаемого числа |
| Отставание в байтах | `pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)` | больше 100 МБ–1 ГБ дольше 5 минут |
| Отставание по времени | `replay_lag` | больше 1–5 минут |
| Неактивный слот | `SELECT slot_name FROM pg_replication_slots WHERE NOT active;` | любой, кроме заведомо известных |
| Слот под угрозой | `wal_status IN ('unreserved','lost')` | сразу |
| Место под `pg_wal` | `df` | меньше 20 % свободного |
| Роль узла изменилась | `SELECT pg_is_in_recovery();` | неожиданное значение |
| Patroni | `patronictl list` — колонки `State`, `TL` и отставание (`Lag in MB` до Patroni 4.1; с 4.1.0 — `Receive LSN`/`Lag` и `Replay LSN`/`Lag`) | не `running` / `streaming`, лаг не 0 |

---

## 6. Переключение ролей вручную

### 6.1. Команды повышения реплики

Три равноценных способа [офиц.]:

```bash
# Debian-раскладка (обёртка над pg_ctl)
sudo pg_ctlcluster 17 main promote

# любой вариант установки: pg_ctl от имени postgres
sudo -u postgres /usr/lib/postgresql/17/bin/pg_ctl promote -D /var/lib/postgresql/17/main
sudo -u postgres /opt/pgpro/1c-17/bin/pg_ctl       promote -D /var/lib/pgpro/1c-17/data
```

```sql
-- из SQL (суперпользователь либо роль, которой выдано право EXECUTE на функцию)
SELECT pg_promote();                 -- ждать завершения до 60 секунд; возвращает true при успехе
SELECT pg_promote(true, 120);        -- ждать до 120 секунд
SELECT pg_promote(false);            -- не ждать
```

При повышении сервер дочитывает имеющийся WAL, переходит на новую линию времени, удаляет `standby.signal` и начинает принимать запись. Параметр `promote_trigger_file` удалён в PostgreSQL 16 — файл-триггер больше не используется.

Проверка: `SELECT pg_is_in_recovery();` должно вернуть `f`; в журнале — `selected new timeline ID: 2`, `database system is ready to accept connections`.

### 6.2. Плановое переключение (switchover) без потери данных

Исходно: pg1 — ведущий, pg2 — реплика со слотом `pg2`.

```bash
# 0. Заблокировать работу в 1С: запретить новые сеансы и регламентные задания, завершить сеансы
#    (rac infobase update ... --sessions-deny=on --scheduled-jobs-deny=on; rac session terminate ...)
#    либо остановить службу сервера 1С.

# 1. На pg1: убедиться, что реплика догнала, и сделать контрольную точку.
sudo -u postgres psql -c "SELECT application_name, state, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag
                          FROM pg_stat_replication;"
sudo -u postgres psql -c "CHECKPOINT;"

# 2. На pg1: штатно остановить ведущий. При обычной остановке walsender досылает реплике весь WAL.
sudo systemctl stop postgresql@17-main
sudo -u postgres env LANG=C /usr/lib/postgresql/17/bin/pg_controldata /var/lib/postgresql/17/main \
     | grep -E 'cluster state|Latest checkpoint location|TimeLineID'
#    ожидается: Database cluster state: shut down

# 3. На pg2: проверить, что получено всё (позиция не меньше "Latest checkpoint location" с pg1), и повысить.
sudo -u postgres psql -Atc "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"
sudo pg_ctlcluster 17 main promote
sudo -u postgres psql -Atc "SELECT pg_is_in_recovery();"                 # f

# 4. На pg2 (новый ведущий): создать слот для будущей реплики pg1.
sudo -u postgres psql -c "SELECT pg_create_physical_replication_slot('pg1');"

# 5. На pg1: превратить его в реплику нового ведущего.
sudo -u postgres touch /var/lib/postgresql/17/main/standby.signal
sudo -u postgres tee /etc/postgresql/17/main/conf.d/replication.conf >/dev/null <<'EOF'
primary_conninfo = 'host=192.168.1.12 port=5432 user=replicator application_name=pg1'
primary_slot_name = 'pg1'
EOF
sudo systemctl start postgresql@17-main
sudo -u postgres psql -Atc "SELECT pg_is_in_recovery();"                 # t

# 6. На pg1 (теперь реплика): удалить старый слот pg2 - слот на реплике тоже удерживает WAL.
sudo -u postgres psql -c "SELECT pg_drop_replication_slot('pg2');"

# 7. Переключить 1С на новый адрес (раздел 8) и снять блокировки.
```

Пояснения:

- В Debian-раскладке файл `conf.d/replication.conf` читается, если в `postgresql.conf` есть `include_dir = 'conf.d'` (так по умолчанию). В раскладке Postgres Pro допишите те же строки в `postgresql.conf` в каталоге данных. Параметр `primary_conninfo` без `standby.signal` игнорируется, поэтому его можно заранее прописать на обоих узлах.
- При таком порядке `pg_rewind` не нужен: старый ведущий остановлен чисто, и реплика получила всё до последней записи. Если же в шаге 3 позиции не совпали (реплика не успела получить хвост WAL) — старый ведущий «ушёл вперёд», и его придётся перематывать (6.4).
- Обратное переключение выполняется так же, с переменой ролей. Документация PostgreSQL называет регулярные переключения полезными: они дают окно для обслуживания каждого сервера и заодно проверяют, что механизм переключения действительно сработает, когда понадобится; там же советуют письменные процедуры [офиц.].

### 6.3. Аварийное переключение (failover)

```bash
# 1. Убедиться, что старый ведущий действительно мёртв или изолирован (см. 6.5).
#    Если он "полуживой" - выключить ВМ/питание или закрыть порт 5432 межсетевым экраном.

# 2. На реплике: оценить, что получено, и повысить.
sudo -u postgres psql -Atc "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(), pg_last_xact_replay_timestamp();"
sudo pg_ctlcluster 17 main promote

# 3. Переключить 1С на новый ведущий (виртуальный адрес, DNS или rac infobase update --db-server).

# 4. Старый ведущий не должен вернуться в сеть ведущим: отключить автозапуск службы.
sudo systemctl disable postgresql@17-main      # на старом ведущем, когда до него удастся добраться
```

После аварийного переключения система работает на одном сервере («вырожденное состояние», по документации). Реплику нужно создать заново — на старом ведущем (`pg_rewind` или `pg_basebackup`) либо на третьем сервере [офиц.].

При асинхронной репликации транзакции, не успевшие дойти до реплики, потеряны. Оценить потерю можно позже, сравнив на старом ведущем `pg_controldata` (поле «Latest checkpoint location») и журнал с позицией, на которой была повышена реплика (`SELECT * FROM pg_control_checkpoint();`, файл `pg_wal/0000000N.history` на новом ведущем).

### 6.4. Возврат старого ведущего: `pg_rewind`

`pg_rewind` синхронизирует каталог данных старого ведущего с новым, копируя только блоки, изменившиеся после расхождения линий времени; остальное (конфигурация в каталоге данных, новые файлы, WAL) копируется целиком. Это намного быстрее полной копии на больших базах [офиц.].

Требования [офиц.]:

- на целевом (перематываемом) сервере включены контрольные суммы данных (`SHOW data_checksums;` → `on`) **или** `wal_log_hints = on` — и это должно было быть включено ещё до аварии;
- `full_page_writes = on` (по умолчанию);
- целевой сервер остановлен. Если он не был остановлен чисто, `pg_rewind` сам запустит его в однопользовательском режиме для завершения восстановления (отключается ключом `--no-ensure-shutdown`);
- в `pg_wal` целевого сервера есть WAL до точки расхождения (либо ключ `-c` и настроенный `restore_command`);
- источник (`--source-server`) — работающий новый ведущий; подключение обычное (не репликационное) суперпользователем или ролью с правами:

```sql
-- на новом ведущем
CREATE USER rewind_user LOGIN PASSWORD 'СложныйПароль';
GRANT EXECUTE ON function pg_catalog.pg_ls_dir(text, boolean, boolean) TO rewind_user;
GRANT EXECUTE ON function pg_catalog.pg_stat_file(text, boolean) TO rewind_user;
GRANT EXECUTE ON function pg_catalog.pg_read_binary_file(text) TO rewind_user;
GRANT EXECUTE ON function pg_catalog.pg_read_binary_file(text, bigint, bigint, boolean) TO rewind_user;
```

Порядок (старый ведущий pg1, новый ведущий pg2):

```bash
# на pg1
sudo systemctl stop postgresql@17-main

# пробный прогон - ничего не меняет
sudo -u postgres /usr/lib/postgresql/17/bin/pg_rewind \
     --target-pgdata=/var/lib/postgresql/17/main \
     --source-server='host=192.168.1.12 port=5432 user=rewind_user dbname=postgres' \
     --config-file=/etc/postgresql/17/main/postgresql.conf \
     --dry-run -P

# настоящий прогон; -R создаст standby.signal и допишет primary_conninfo в postgresql.auto.conf
sudo -u postgres /usr/lib/postgresql/17/bin/pg_rewind \
     --target-pgdata=/var/lib/postgresql/17/main \
     --source-server='host=192.168.1.12 port=5432 user=rewind_user dbname=postgres' \
     --config-file=/etc/postgresql/17/main/postgresql.conf \
     -R -P

# поправить primary_conninfo: пользователь репликации, application_name, слот; затем запуск
sudo systemctl start postgresql@17-main
```

Ключи [офиц.]: `-D` / `--target-pgdata` — перематываемый каталог; `--source-server` — строка подключения к источнику (или `--source-pgdata` — каталог остановленного источника); `-R` — записать настройки реплики (только с `--source-server`); `-n` / `--dry-run` — пробный прогон; `-P` — ход выполнения; `-c` / `--restore-target-wal` — брать недостающий WAL через `restore_command`; `--config-file` — путь к `postgresql.conf`, если он лежит вне каталога данных (Debian-раскладка; ключ есть с PostgreSQL 15).

Предупреждения:

- **Если `pg_rewind` прервался посередине, каталог данных, скорее всего, испорчен безвозвратно** — документация советует в этом случае снять новую копию [офиц.]. На небольших базах (десятки гигабайт) проще и надёжнее сразу пересоздать реплику через `pg_basebackup` (раздел 2.3).
- Файлы конфигурации, лежащие в каталоге данных (`postgresql.auto.conf`, а в раскладке Postgres Pro — ещё `postgresql.conf` и `pg_hba.conf`), **заменяются копиями с источника**. После перемотки проверьте `listen_addresses`, `primary_conninfo`, `primary_slot_name`.
- `-R` записывает в `primary_conninfo` ту учётную запись, под которой работал `pg_rewind` (`rewind_user`); у неё нет атрибута `REPLICATION` — замените на роль репликации.
- Слоты (`pg_replslot/`) не копируются. Создайте на новом ведущем слот для возвращаемого узла и удалите на нём самом слоты, оставшиеся от прежней роли.
- Сообщение `source and target cluster are on the same timeline` / `no rewind required` означает, что расхождения нет: достаточно создать `standby.signal` и задать `primary_conninfo` (с ключом `-R` `pg_rewind` запишет их и в этом случае) [офиц., исходный код `pg_rewind` 18].

### 6.5. Split-brain и как его избежать

**Что это.** После сбоя связи или перезагрузки старый ведущий продолжает (или снова начинает) принимать запись, хотя реплика уже повышена. Часть серверов 1С пишет в один сервер, часть — в другой; данные расходятся, и автоматически их не объединить: одну из веток придётся выбросить (`pg_rewind` уничтожает изменения перематываемого узла).

Документация PostgreSQL: нужен механизм, сообщающий старому ведущему, что он больше не ведущий (STONITH), иначе возможна ситуация, когда обе системы считают себя ведущими, что приведёт к путанице и в итоге к потере данных [офиц.].

Меры:

| Мера | Суть |
|---|---|
| Единая точка входа для 1С | 1С знает только виртуальный адрес / адрес HAProxy; адрес выдаётся строго одному узлу |
| Изоляция старого ведущего перед повышением реплики | выключить ВМ или питание (IPMI, гипервизор), закрыть порт; не полагаться на «он, наверное, упал» |
| Запрет автозапуска PostgreSQL как ведущего | при ручной схеме — `systemctl disable` на вышедшем из строя узле до разбора; при Patroni служба PostgreSQL отключена, запуском управляет Patroni |
| Кворум | решение о смене ведущего принимает большинство (3 узла DCS; рефери в BiHA; монитор в pg_auto_failover). Двух узлов без третьего «голоса» недостаточно |
| Сторожевой таймер (watchdog) | Patroni + `/dev/watchdog`: узел, потерявший связь с DCS и не сумевший понизить PostgreSQL, перезагружается |
| Синхронная репликация | не предотвращает split-brain, но гарантирует, что повышаемая реплика содержит все подтверждённые транзакции |
| Письменный регламент | кто, по каким признакам и какими командами переключает; регулярные учебные переключения |

Как понять, что split-brain уже случился: на обоих серверах `SELECT pg_is_in_recovery();` возвращает `f`, а `SELECT timeline_id FROM pg_control_checkpoint();` показывает разные линии времени; в `pg_stat_activity` обоих есть сеансы 1С с записью.

---

## 7. Автоматизация отказоустойчивости

### 7.1. Patroni + etcd + HAProxy: архитектура

Схема, описанная фирмой «1С» как аналог «MS SQL Server Always On Availability Groups» [офиц., ИТС 5971]:

```text
           серверы 1С (rphost)
                  |
     единая точка входа: HAProxy :5432  (или виртуальный IP)
                  |  проверка HTTP GET http://узел:8008/primary -> 200 только у ведущего
      +-----------+-----------+
      |           |           |
   pg1:5432    pg2:5432    pg3:5432      PostgreSQL (сборка для 1С)
   patroni     patroni     patroni       агент Patroni, REST API :8008
      |           |           |
      +-----------+-----------+
          etcd (3 узла, порты 2379 клиентский / 2380 межузловой)
```

| Компонент | Роль | Порты |
|---|---|---|
| **Patroni** | агент на каждом узле СУБД: запускает и останавливает PostgreSQL, создаёт реплики, держит «ключ лидера» в DCS, при его потере организует выборы и повышает реплику, возвращает старый ведущий репликой (`pg_rewind`) | REST API 8008 |
| **etcd** (либо Consul, ZooKeeper, Kubernetes) | согласованное хранилище: кто лидер, список узлов, общая конфигурация. Нужен кворум — 3 узла (или 5) | 2379, 2380 |
| **HAProxy** | TCP-прокси: опрашивает REST API Patroni и пускает подключения только на текущий ведущий | 5432 (или иной), статистика 7000 |
| **keepalived / vip-manager** | альтернатива или дополнение HAProxy: переносят виртуальный IP на ведущий узел | VRRP (протокол 112) |

Принципы [офиц., ИТС 5971 и документация Patroni]:

- PostgreSQL на узлах запускает **только Patroni**. Собственную службу PostgreSQL отключают: `sudo systemctl disable --now postgresql@17-main` (сборка от 1С) или `sudo systemctl disable --now postgrespro-1c-17`.
- Параметры PostgreSQL задаются **через Patroni**, а не правкой `postgresql.conf`: Patroni переименовывает исходный файл в `postgresql.base.conf` и пишет свой `postgresql.conf`, подключающий базовый [офиц.].
- В свойствах информационной базы 1С указывается адрес HAProxy (или виртуальный адрес), а не узел PostgreSQL.
- В примере ИТС HAProxy стоит на той же машине, что и сервер 1С, поэтому сервер баз данных в инфобазе — `localhost`. Это заодно убирает HAProxy как отдельную точку отказа: у каждого сервера 1С свой локальный прокси.

Статья ИТС написана в 2020 году для CentOS 7, PostgreSQL 11 и Patroni 1.6.4: параметры `wal_keep_segments`, `master_start_timeout`, секция `bootstrap.users`, файл `recovery.conf`, команды `etcdctl cluster-health` относятся к тем версиям. Для актуальных версий используйте синтаксис ниже.

### 7.2. Версии и пакеты в Ubuntu

Данные packages.ubuntu.com на 10.10.2026 [офиц.]; все пакеты — в компоненте `universe`.

| Пакет | 22.04 (jammy) | 24.04 (noble) | 26.04 (resolute) | Последняя версия разработчика |
|---|---|---|---|---|
| `patroni` | 2.1.3 | 3.2.2 | 4.1.0 | 4.1.5 от 12.08.2026 (совместимость с PostgreSQL 14.24, 15.19, 16.15, 17.11, 18.6) |
| `etcd-server` (+ `etcd-client`) | 3.3.25 | 3.4.30 | 3.5.16 | — |
| `vip-manager` / `vip-manager2` | 1.0.1 / — | 1.0.2 / 2.3.0 | 1.0.2 / 4.0.0 | — |
| `pgbouncer` | 1.16.1 | 1.22.0 | 1.25.1 | — |
| `haproxy`, `keepalived` | в компоненте `main`: haproxy 2.4.30 / 2.8.16 / 3.2.9 и keepalived 2.2.4 / 2.2.8 / 2.3.4 в 22.04 / 24.04 / 26.04 (сверено 19.10.2026 по packages.ubuntu.com) | то же | то же | — |

Замечания:

- Для PostgreSQL 17 и 18 версия Patroni из Ubuntu 22.04 (2.1.3) и из 24.04 (3.2.2) слишком стара: по журналу выпусков Patroni совместимость с PostgreSQL 16 появилась в 3.0.3, с 17 — в 4.0.0, с 18 — в 4.0.7 (сверено 19.10.2026); для ветки 16 подходит Patroni 3.2.2 из 24.04, но не 2.1.3 из 22.04 (версии в архиве Ubuntu подтверждены по packages.ubuntu.com 10.10.2026: 2.1.3 в 22.04, 3.2.2 в 24.04, 4.1.0 в 26.04). Берите свежий Patroni из репозитория PGDG (`apt.postgresql.org`) или ставьте через `pipx` / виртуальное окружение Python (`pip install 'patroni[etcd3]'`). Системный `pip install` в Ubuntu 24.04 и новее запрещён (ошибка `externally-managed-environment`) [практика].
- В etcd 3.3 утилита `etcdctl` по умолчанию говорит по API v2 — добавляйте `ETCDCTL_API=3`; начиная с 3.4 по умолчанию v3.
- Пакет `patroni` для Debian/Ubuntu содержит шаблон конфигурации и вспомогательный сценарий `pg_createconfig_patroni` для интеграции с `postgresql-common` (подтверждено 11.10.2026 списком файлов пакета `patroni` для 24.04 на packages.ubuntu.com: `/usr/bin/pg_createconfig_patroni`, `/etc/patroni/config.yml.in`, `/etc/patroni/dcs.yml`, юниты `patroni.service` и `patroni@.service`) — проверьте `dpkg -L patroni` и `/usr/share/doc/patroni/`.

```bash
sudo apt install etcd-server etcd-client haproxy
sudo apt install patroni            # или более новая версия из PGDG / pipx
patroni --version
etcd --version
```

### 7.3. Кластер etcd (3 узла)

Пакет Ubuntu читает переменные из `/etc/default/etcd`. Пример для узла `pg1` (на остальных меняются имя и адреса):

```ini
ETCD_NAME="pg1"
ETCD_DATA_DIR="/var/lib/etcd/default"
ETCD_LISTEN_PEER_URLS="http://192.168.1.11:2380"
ETCD_LISTEN_CLIENT_URLS="http://192.168.1.11:2379,http://127.0.0.1:2379"
ETCD_INITIAL_ADVERTISE_PEER_URLS="http://192.168.1.11:2380"
ETCD_ADVERTISE_CLIENT_URLS="http://192.168.1.11:2379"
ETCD_INITIAL_CLUSTER="pg1=http://192.168.1.11:2380,pg2=http://192.168.1.12:2380,pg3=http://192.168.1.13:2380"
ETCD_INITIAL_CLUSTER_TOKEN="etcd-pg1c"
ETCD_INITIAL_CLUSTER_STATE="new"
ETCD_HEARTBEAT_INTERVAL="1000"
ETCD_ELECTION_TIMEOUT="5000"
```

```bash
sudo systemctl enable --now etcd          # на всех трёх узлах (при одновременном первом запуске)
etcdctl --endpoints=192.168.1.11:2379,192.168.1.12:2379,192.168.1.13:2379 endpoint health
etcdctl --endpoints=192.168.1.11:2379,192.168.1.12:2379,192.168.1.13:2379 endpoint status -w table
etcdctl member list -w table
```

- `ETCD_HEARTBEAT_INTERVAL` подбирают по сетевой задержке, `ETCD_ELECTION_TIMEOUT` — в несколько раз больше (в примере ИТС 1000 и 5000 мс) [офиц., ИТС 5971].
- После первого успешного запуска значение `ETCD_INITIAL_CLUSTER_STATE` на всех узлах меняют на `"existing"`. Если первый запуск не удался — очистить каталог из `ETCD_DATA_DIR` и повторить [офиц., ИТС 5971].
- Двух узлов etcd недостаточно: при потере одного кворума нет, и Patroni понизит ведущий (см. `failsafe_mode`). Третий узел etcd может стоять на сервере 1С или на маленькой отдельной ВМ.
- В промышленной среде включают аутентификацию и TLS; в примере ИТС всё по HTTP — сам etcd об этом предупреждает.

### 7.4. Конфигурация Patroni

Файл `/etc/patroni/config.yml` на узле `pg1` (синтаксис Patroni 3.x–4.x). Вариант, при котором кластер PostgreSQL создаёт сам Patroni; автоматически созданный пакетом кластер предварительно удаляют (`sudo pg_dropcluster --stop 17 main` — **только на новой пустой установке**) [практика].

```yaml
scope: pg1c                      # имя кластера Patroni
namespace: /service/             # путь в DCS (по умолчанию /service)
name: pg1                        # уникальное имя узла

restapi:
  listen: 0.0.0.0:8008
  connect_address: 192.168.1.11:8008

etcd3:                           # API v3; секция etcd: - для устаревшего API v2
  hosts: 192.168.1.11:2379,192.168.1.12:2379,192.168.1.13:2379

bootstrap:
  dcs:                           # записывается в DCS один раз, при создании кластера
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    primary_start_timeout: 300
    synchronous_mode: false
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        max_connections: 500
        max_locks_per_transaction: 256
        max_worker_processes: 8
        wal_level: replica
        max_wal_senders: 10
        max_replication_slots: 10
        wal_keep_size: 1GB
        wal_log_hints: "on"
        max_slot_wal_keep_size: 20GB
        standard_conforming_strings: "off"
        escape_string_warning: "off"
        shared_preload_libraries: plantuner
        plantuner.fix_empty_table: "on"
  initdb:
    - encoding: UTF8
    - locale: ru_RU.UTF-8          # для конфигураций WE - en_US.UTF-8
    - data-checksums

postgresql:
  listen: 0.0.0.0:5432
  connect_address: 192.168.1.11:5432
  data_dir: /var/lib/postgresql/17/main         # Postgres Pro: /var/lib/pgpro/1c-17/data
  bin_dir: /usr/lib/postgresql/17/bin           # Postgres Pro: /opt/pgpro/1c-17/bin
  pgpass: /var/lib/postgresql/.pgpass_patroni
  authentication:
    superuser:
      username: postgres
      password: ПарольСуперпользователя
    replication:
      username: replicator
      password: ПарольРепликации
    rewind:
      username: rewind_user
      password: ПарольRewind
  pg_hba:
    - local   all          all                           peer
    - host    all          all          127.0.0.1/32     scram-sha-256
    - host    replication  replicator   192.168.1.0/24   scram-sha-256
    - host    all          all          192.168.1.0/24   scram-sha-256
  parameters:
    unix_socket_directories: /var/run/postgresql

watchdog:
  mode: automatic                # off | automatic | required
  device: /dev/watchdog
  safety_margin: 5

tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
```

На остальных узлах отличаются только `name`, `restapi.connect_address` и `postgresql.connect_address`. Локаль `ru_RU.UTF-8` должна существовать в ОС до запуска (`locale -a`).

Важные правила конфигурации Patroni [офиц.]:

- Конфигурация трёх видов: **динамическая** (хранится в DCS, общая для всех узлов, меняется `patronictl edit-config`), **локальная** (файл YAML, имеет приоритет над динамической), **переменные окружения**.
- Секция `bootstrap.dcs` применяется только при первом создании кластера; дальнейшие правки в ней ничего не меняют.
- **Параметры, которые обязаны совпадать на всех узлах, принимаются только из динамической конфигурации** — в локальном файле они игнорируются: `max_connections` (по умолчанию 100), `max_locks_per_transaction` (64), `max_worker_processes` (8), `max_prepared_transactions` (0), `wal_level`, `track_commit_timestamp`. То же для `max_wal_senders` (10), `max_replication_slots` (10), `wal_keep_size` (128MB), `wal_log_hints` (on). Для 1С это критично: `max_connections` и `max_locks_per_transaction = 256` нужно задавать именно через `bootstrap.dcs` / `patronictl edit-config`, иначе кластер поднимется со 100 соединениями и 64 блокировками на транзакцию.
- `listen_addresses`, `port` берутся из `postgresql.listen`, `cluster_name` — из `scope`, `hot_standby` всегда `on`.
- Правило времён: `loop_wait + 2 × retry_timeout ≤ ttl`. По умолчанию `ttl` 30 с (минимум 20), `loop_wait` 10 с, `retry_timeout` 10 с.

Параметры, влияющие на переключение:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `ttl` | 30 | время жизни ключа лидера; столько ждут до начала автоматического переключения |
| `loop_wait` | 10 | пауза между циклами агента |
| `retry_timeout` | 10 | сколько повторять операции с DCS и PostgreSQL; более короткие сбои сети не приводят к понижению ведущего |
| `maximum_lag_on_failover` | — (в примерах 1048576) | максимальное отставание реплики в байтах, при котором она ещё может стать ведущей |
| `primary_start_timeout` | 300 | сколько секунд ведущему даётся на восстановление после сбоя, прежде чем начнётся переключение; `0` — переключаться сразу (при асинхронной репликации возможна потеря последних транзакций) |
| `synchronous_mode` | выкл. | `on` / `quorum`: Patroni сам ведёт `synchronous_standby_names`; ведущим может стать только синхронная реплика |
| `synchronous_mode_strict` | выкл. | не отключать синхронность, даже если синхронных реплик нет (запись на ведущем блокируется) |
| `synchronous_node_count` | 1 | сколько синхронных реплик поддерживать |
| `failsafe_mode` | false | не понижать ведущий при недоступности DCS, если видны все узлы кластера |
| `member_slots_ttl` | 30min | сколько хранить слот выключенной реплики |
| `postgresql.use_pg_rewind` | false | возвращать бывший ведущий через `pg_rewind` |
| `postgresql.use_slots` | true | использовать слоты репликации |

Оценка из статьи ИТС: максимальное время переключения = `loop_wait + master_start_timeout + loop_wait`; при нулевом таймауте — `loop_wait` [офиц., ИТС 5971]. В актуальной документации параметр называется `primary_start_timeout`.

Теги узла: `nofailover: true` — узел никогда не станет ведущим (например, удалённая реплика или узел для копий базы данных); `failover_priority` — приоритет на выборах; `nosync: true` — не выбирать синхронной репликой; `clonefrom: true` — предпочтительный источник для создания новых реплик; `noloadbalance: true` — `GET /replica` возвращает 503; `replicatefrom: имя` — каскадная репликация [офиц.].

Синхронный режим Patroni [офиц.]: при `synchronous_mode: on` Patroni не повышает реплику, пока не убедится, что в ней есть все транзакции, которым клиент получил подтверждение. Если подходящей синхронной реплики нет, ведущий продолжает принимать запись без гарантии репликации (и при его отказе автоматического переключения не будет); `synchronous_mode_strict: true` вместо этого блокирует запись. Напоминание: всё это имеет смысл только при `synchronous_commit` не `off` (раздел 4.2).

### 7.5. Служба и первый запуск

Если Patroni установлен из пакета, служба уже есть (`patroni.service`). Для установки через pip unit-файл создают вручную:

```ini
# /etc/systemd/system/patroni.service
[Unit]
Description=Patroni - HA PostgreSQL
After=network-online.target etcd.service
Wants=network-online.target

[Service]
Type=simple
User=postgres
Group=postgres
ExecStart=/usr/local/bin/patroni /etc/patroni/config.yml
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=process
TimeoutSec=30
Restart=no

[Install]
WantedBy=multi-user.target
```

```bash
sudo install -d -o postgres -g postgres -m 700 /etc/patroni
sudo chown postgres:postgres /etc/patroni/config.yml && sudo chmod 600 /etc/patroni/config.yml
sudo systemctl daemon-reload
sudo systemctl start patroni          # сначала на первом узле: он создаст кластер и станет лидером
sudo journalctl -u patroni -f
patronictl -c /etc/patroni/config.yml list
sudo systemctl enable patroni         # включать автозапуск только после успешной проверки
```

На втором и третьем узле при запуске Patroni сам снимает копию с лидера (`pg_basebackup`) и запускает PostgreSQL репликой. В примере ИТС в unit-файле `Restart=no` и `TimeoutSec=30`; `KillMode=process` нужен, чтобы остановка службы Patroni не убивала PostgreSQL [офиц., ИТС 5971].

**Перевод существующего кластера под управление Patroni** [офиц., документация Patroni]: создать роли суперпользователя, репликации и перемотки; на каждом узле начиная с ведущего — отключить службу PostgreSQL в systemd, создать конфигурацию Patroni (существующие слоты описать как постоянные в `slots`, иначе Patroni их удалит), запустить `patroni` (он обнаружит работающий экземпляр и начнёт его отслеживать); затем передать запуск Patroni командой `patronictl restart имя_кластера имя_узла` — реплики сразу, ведущий в окно обслуживания.

### 7.6. Команды `patronictl`

Настройки подключения берутся из файла `~/.config/patroni/patronictl.yaml`, из переменной `PATRONICTL_CONFIG_FILE` или ключа `-c файл`; на узле с Patroni можно указывать его же конфигурацию [офиц.].

| Команда | Действие |
|---|---|
| `patronictl -c /etc/patroni/config.yml list` | состав кластера: роль, состояние, линия времени, отставание в МБ, признак ожидающего перезапуска |
| `patronictl topology` | то же в виде дерева репликации |
| `patronictl history pg1c` | история переключений |
| `patronictl switchover pg1c --leader pg1 --candidate pg2` | плановое переключение в здоровом кластере; `--scheduled время` — отложенное, `--force` — без вопросов |
| `patronictl failover pg1c --candidate pg2` | ручное аварийное переключение (нет лидера или синхронной реплики); может повысить и асинхронную реплику — **возможна потеря данных** |
| `patronictl pause pg1c --wait` / `patronictl resume pg1c --wait` | режим обслуживания: автоматическое переключение выключено / включено |
| `patronictl show-config pg1c` | показать динамическую конфигурацию |
| `patronictl edit-config pg1c` | изменить динамическую конфигурацию в редакторе; без редактора: `-p 'work_mem=64MB'` (параметр PostgreSQL), `-s 'ttl=30'` (параметр Patroni), `--apply файл.yml` |
| `patronictl reload pg1c [узел]` | перечитать локальную конфигурацию и выполнить `pg_ctl reload` |
| `patronictl restart pg1c [узел]` | перезапустить PostgreSQL; `--pending` — только там, где ждёт перезапуск; `--role replica`; `--scheduled время` |
| `patronictl reinit pg1c pg3` | пересоздать реплику с нуля |
| `patronictl query pg1c -c "SELECT 1" -r primary` | выполнить SQL на узле с заданной ролью |
| `patronictl dsn pg1c -r primary` | строка подключения к узлу |
| `patronictl flush pg1c switchover` | отменить запланированное переключение (`restart` — запланированный перезапуск) |
| `patronictl remove pg1c` | удалить сведения о кластере из DCS (разрушительно; только при пересоздании или мажорном обновлении) |
| `patronictl version` | версия утилиты, а с именем кластера — версии Patroni и PostgreSQL на узлах |

Изменение параметров PostgreSQL для 1С в работающем кластере:

```bash
patronictl -c /etc/patroni/config.yml edit-config pg1c -p 'shared_buffers=8GB' -p 'temp_buffers=128MB' --force
patronictl -c /etc/patroni/config.yml list            # столбец Pending restart
patronictl -c /etc/patroni/config.yml restart pg1c --pending --force
```

REST API Patroni (порт 8008) [офиц.]: `GET /primary` (он же `/` и `/read-write`) возвращает 200 только на ведущем; `GET /replica` — 200 на работающей реплике (`?lag=10MB` — с отставанием не больше заданного); `GET /sync`, `/async`, `/health`, `/liveness`, `/readiness`; `GET /patroni` и `/cluster` — состояние в JSON; `GET /metrics` — метрики для Prometheus.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.11:8008/primary
curl -s http://192.168.1.11:8008/cluster | jq .
```

### 7.7. HAProxy

`/etc/haproxy/haproxy.cfg` (основа — пример из репозитория Patroni и статья ИТС):

```text
global
    maxconn 2000

defaults
    log global
    mode tcp
    retries 2
    timeout client 12h
    timeout server 12h
    timeout connect 4s
    timeout check 5s

listen stats
    mode http
    bind *:7000
    stats enable
    stats uri /

listen postgres
    bind *:5432
    option httpchk GET /primary
    http-check expect status 200
    default-server inter 3s fastinter 1s fall 2 rise 2 on-marked-down shutdown-sessions
    server pg1 192.168.1.11:5432 maxconn 1000 check port 8008
    server pg2 192.168.1.12:5432 maxconn 1000 check port 8008
    server pg3 192.168.1.13:5432 maxconn 1000 check port 8008
```

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg     # проверка синтаксиса
sudo systemctl enable --now haproxy
# статистика: http://адрес:7000/  - ведущий отмечен UP, реплики - DOWN (это норма)
```

Пояснения:

- Если HAProxy стоит на одной машине с PostgreSQL, порт 5432 занят — используйте другой (в примере Patroni — 5000) и укажите его в 1С: `адрес port=5000;`.
- `on-marked-down shutdown-sessions` рвёт соединения с узлом, переставшим быть ведущим, — иначе сеансы 1С продолжат слать запросы на сервер, ставший репликой.
- `maxconn` в `global` и у серверов должен быть не меньше числа соединений 1С с СУБД; в примере ИТС стоит 100 — для промышленной базы мало.
- `timeout client` / `timeout server` — это таймауты **простоя** соединения. В примере ИТС 30 минут; рабочие процессы 1С держат соединения с СУБД подолгу, и разрыв простаивающего соединения прокси-сервером проявится ошибкой СУБД у пользователя, вернувшегося к работе после паузы ⚠ [практика]. Ставьте заведомо больше типичного простоя сеанса.

### 7.8. Виртуальный IP: keepalived и vip-manager

Вместо прокси (или для резервирования самого HAProxy) можно переносить адрес 192.168.1.10 на текущий ведущий. Все узлы должны быть в одном сегменте L2.

**keepalived** с проверкой роли через REST API Patroni — `/etc/keepalived/keepalived.conf` на каждом узле СУБД [практика]:

```text
vrrp_script chk_patroni_primary {
    script "/usr/bin/curl -sf -o /dev/null http://127.0.0.1:8008/primary"
    interval 2
    fall 2
    rise 2
}

vrrp_instance VI_PG {
    state BACKUP
    nopreempt
    interface ens33
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass Secret12
    }
    virtual_ipaddress {
        192.168.1.10/24
    }
    track_script {
        chk_patroni_primary
    }
}
```

Узел, на котором проверка не проходит (то есть не ведущий), переходит в состояние FAULT и адрес удерживать не может; адрес получает единственный узел с успешной проверкой. Без Patroni сценарий проверки можно заменить на `psql -Atc "select not pg_is_in_recovery()"`, но тогда keepalived сам ничего не повышает и от split-brain не защищает.

**vip-manager** (CYBERTEC) следит за ключом лидера в DCS и вешает адрес на тот узел, чьё имя там записано [офиц.]. Файл `/etc/default/vip-manager.yml`, служба `vip-manager`:

```yaml
ip: 192.168.1.10
netmask: 24
interface: ens33
trigger-key: /service/pg1c/leader      # <namespace>/<scope>/leader
trigger-value: pg1                     # имя этого узла в Patroni (по умолчанию - имя хоста)
dcs-type: etcd                         # etcd | consul | patroni
dcs-endpoints:                         # в файле - списком; в ключе командной строки и переменной VIP_DCS_ENDPOINTS - через запятую
  - http://192.168.1.11:2379
  - http://192.168.1.12:2379
  - http://192.168.1.13:2379
interval: 1000
retry-num: 3
retry-after: 250
```

Вариант без прямого доступа к DCS: `dcs-type: patroni`, `trigger-key: /leader`, `dcs-endpoints: http://127.0.0.1:8008`, `trigger-value: 200`. PostgreSQL должен слушать `*`/`0.0.0.0` либо нужен `net.ipv4.ip_nonlocal_bind=1` [офиц.].

**DNS-имя** вместо адреса (в 1С — `pg-1c.example.local`) годится для ручных схем: после переключения меняют A-запись. Недостатки: кеширование имён (TTL, кеш ОС на серверах 1С), нет автоматики.

### 7.9. Другие менеджеры: repmgr, pg_auto_failover

| | repmgr | pg_auto_failover |
|---|---|---|
| Разработчик | EDB | изначально Citus Data / Microsoft |
| Версия | 5.5.0 от 24.11.2024; по матрице совместимости в документации — PostgreSQL 13–17, ветки 18 в ней нет (сверено 19.10.2026) [офиц.] | последний выпуск по журналу изменений — v2.2 от 03.04.2025 (добавлена поддержка 17, убрана 11 и 12); README ветки main заявляет PostgreSQL 13–18 (сверено 19.10.2026) |
| Архитектура | утилита `repmgr` + демон `repmgrd` на каждом узле, метаданные в самой БД; для кворума — узел-свидетель (witness) | отдельный узел-монитор (PostgreSQL с расширением) + агент `pg_autoctl` на узлах данных; по умолчанию синхронная реплика |
| Команды | `repmgr primary register`, `repmgr standby clone`, `repmgr standby register`, `repmgr standby promote`, `repmgr standby follow`, `repmgr standby switchover`, `repmgr node rejoin`, `repmgr cluster show`, `repmgr witness register`, `repmgr service status` | `pg_autoctl create monitor`, `pg_autoctl create postgres`, `pg_autoctl show state`, `pg_autoctl perform switchover` — `show state` и `perform switchover` подтверждены справочными страницами проекта (каталог `docs/ref`, 11.10.2026), обе команды `create` — там же (сверено 19.10.2026) |
| Точка входа для клиентов | не предоставляет; нужны VIP/прокси и собственные сценарии | рассчитан на строку подключения libpq с несколькими хостами и `target_session_attrs=read-write` (подтверждено справочной страницей `pg_autoctl show uri`, пример оттуда — `postgres://localhost:5502,localhost:5503,localhost:5501/demo?target_session_attrs=read-write&sslmode=prefer`; сверено 11.10.2026) |
| Применимость к 1С | работает (физическая репликация), но изоляцию старого ведущего и перенос адреса надо делать самому [практика] | упирается в вопрос, принимает ли 1С несколько хостов (раздел 8.2) |

Официальных материалов фирмы «1С» по этим инструментам не найдено; для 1С документирован только вариант с Patroni.

### 7.10. Решения Postgres Pro Enterprise

**BiHA (Built-in High Availability)** — встроенная отказоустойчивость Postgres Pro Enterprise (документация 17.11.1) [офиц.]:

- расширение `biha`, утилита `bihactl`, фоновый процесс `biha-background-worker`; внешнее ПО (DCS, Patroni) не требуется;
- **физическая** репликация: один лидер (чтение и запись), последователи (только чтение), выборы нового лидера по алгоритму Raft; синхронная и асинхронная репликация, каскад, геораспределённые конфигурации;
- варианты состава: три и более узлов; два узла + **рефери** (узел без данных, участвует только в голосовании; режимы `referee` и `referee_with_wal`); два узла без рефери не рекомендуются из-за риска split-brain;
- параметры кворума `nquorum` (минимум голосов для избрания лидера) и `minnodes` задаются при `bihactl cluster init`; для схемы «2 + рефери» — оба по 2;
- ручная смена лидера — функция `biha.set_leader()` (вызывается на узле-кандидате); состояние — `SELECT * FROM biha.status_v;`; автоматическая перемотка — `biha.autorewind`;
- BiHA сама задаёт `wal_level`, `max_wal_senders`, `max_replication_slots`, `max_slot_wal_keep_size` (5GB), `wal_keep_size` (1GB), `hot_standby`; `primary_conninfo`, `primary_slot_name`, `synchronous_standby_names` нельзя менять через `ALTER SYSTEM`;
- единая точка входа — расширение **proxima** (прокси + балансировщик + пул соединений): порт «к лидеру» `proxima.port` (по умолчанию 4545) и порт для чтения с реплик `proxima.p2f_port` (4547).

**multimaster** — синхронный кластер без разделения ресурсов, где запись принимают все узлы (логическая репликация + трёхфазная фиксация, минимум три узла или 2 + рефери). В разделе ограничений документации прямо написано: **«Решения 1С не поддерживаются»** [офиц.].

### 7.11. Что из этого совместимо с 1С

| Решение | Совместимость с 1С | Основание |
|---|---|---|
| Потоковая физическая репликация (ручная) | да | 1С работает только с ведущим; реплика — резерв |
| Patroni + etcd + HAProxy | да, **описано фирмой «1С»** | [офиц., ИТС 5971] |
| Patroni + keepalived / vip-manager | да | та же репликация, иная точка входа [практика] |
| repmgr, pg_auto_failover | да, без официальных материалов | [практика] |
| Postgres Pro Enterprise BiHA | архитектурно да (физическая репликация, один пишущий лидер); Postgres Pro Enterprise входит в список СУБД, поддерживаемых 1С | прямого упоминания 1С в документации BiHA не найдено ⚠ — уточнять у Postgres Professional |
| proxima как пул соединений | пользы для 1С нет: при создании временной таблицы или `SET` сеанс закрепляется за процессом («динамический выделенный сеанс») | [офиц., документация proxima]; использование как точки входа с 1С ⚠ не проверено |
| Postgres Pro multimaster | **нет** | [офиц.] «Решения 1С не поддерживаются» |
| Чтение 1С с реплики (балансировка чтения) | **нет** | [офиц.] временные таблицы на реплике запрещены |
| Встроенная логическая репликация (публикации/подписки) как HA | не рекомендуется | раздел 11 |

Обязательное условие для любого варианта: на **всех** узлах стоит одна и та же сборка PostgreSQL для 1С одной версии.

---

## 8. Как 1С подключается к СУБД и что происходит при переключении

### 8.1. Имя сервера БД в свойствах информационной базы

Рабочие процессы сервера 1С (`rphost`) открывают обычные клиентские соединения PostgreSQL (libpq) к адресу из свойства информационной базы «Сервер баз данных». Формат поля для PostgreSQL по документации платформы [офиц.]:

```text
<имя_экземпляра> port=<номер_порта>;
```

Пример из документации — `localhost port=6432;`. Без указания порта используется 5432.

Изменить адрес сервера СУБД у существующей базы:

```bash
RAC=/opt/1cv8/x86_64/8.3.27.XXXX/rac          # подставьте каталог своей версии платформы (ls /opt/1cv8/x86_64/)
CL=$($RAC cluster list | awk '/^cluster/ {print $3}')
$RAC infobase summary list --cluster=$CL      # найти UUID базы
IB=<uuid_базы>

$RAC infobase info --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd='***' | grep -E 'db-server|db-name|dbms'

$RAC infobase update --cluster=$CL --infobase=$IB \
     --infobase-user=Администратор --infobase-pwd='***' \
     --db-server='192.168.1.10'                # или 'pg-1c.example.local', или 'localhost port=5000;'
```

То же в консоли администрирования кластера: свойства информационной базы → «Сервер баз данных». Параметры `--db-server`, `--db-name`, `--db-user`, `--db-pwd`, `--dbms` принимает и `rac infobase update` [офиц.]. Перед сменой адреса завершите сеансы базы; уже открытые соединения рабочих процессов продолжают смотреть на старый сервер, пока не будут закрыты, поэтому после смены надёжнее перезапустить рабочие процессы или службу сервера 1С ⚠ [практика].

### 8.2. Можно ли указать несколько хостов

- **Официально — нет.** В статье ИТС сказано, что в параметрах базы указывается одно имя сервера СУБД, перечислить все серверы PostgreSQL сразу нельзя, и именно поэтому нужна единая точка подключения (HAProxy) [офиц., ИТС 5971; статья 2020 года].
- Сама библиотека libpq умеет список хостов и выбор пишущего узла: `host=pg1,pg2,pg3 port=5432 target_session_attrs=read-write` (значения `any`, `read-write`, `read-only`, `primary`, `standby`, `prefer-standby`); `connect_timeout` действует отдельно на каждый хост [офиц., PostgreSQL].
- Поскольку платформа принимает после имени сервера ключевое слово `port=…`, в сообществе встречаются сообщения, что в то же поле можно дописать и другие параметры libpq (несколько хостов через запятую, `target_session_attrs=read-write`) ⚠ **не подтверждено**: в документации платформы описан только `port`, поведение зависит от версии libpq в составе платформы и может измениться. Не стройте на этом промышленную схему без собственного тестирования; официальный путь — один адрес (прокси, виртуальный IP, DNS).

### 8.3. Виртуальный IP или DNS-имя

| Способ | Что писать в «Сервер баз данных» | Особенности |
|---|---|---|
| HAProxy на каждом сервере 1С | `localhost` или `localhost port=5000;` | нет отдельной точки отказа; настройку прокси надо держать одинаковой на всех серверах 1С |
| Отдельный HAProxy (пара с keepalived) | виртуальный адрес прокси | лишний сетевой переход; прокси надо резервировать |
| Виртуальный IP на ведущем (keepalived, vip-manager) | `192.168.1.10` | один сегмент L2; при переключении возможна задержка обновления ARP |
| DNS-имя | `pg-1c.example.local` | ручное переключение; учитывать TTL и кеширование имён |
| Прямой адрес узла | `192.168.1.11` | при переключении — `rac infobase update --db-server=…` по каждой базе |

Не забудьте `pg_hba.conf`: при работе через прокси PostgreSQL видит адрес прокси, а не сервера 1С, — строка `host` нужна для адресов прокси.

### 8.4. Что происходит с сеансами 1С при переключении СУБД

Состояние сеанса пользователя хранится в кластере серверов 1С, а не в СУБД; в PostgreSQL у сеанса есть только соединения рабочего процесса, открытые транзакции и временные таблицы.

При переключении (планово или аварийно) [практика, если не указано иное]:

1. Все TCP-соединения рабочих процессов с прежним ведущим разрываются (остановка сервера, `on-marked-down shutdown-sessions`, уход виртуального адреса).
2. Операции, выполнявшиеся в этот момент (проведение, отчёт, фоновое и регламентное задание), завершаются ошибкой СУБД; открытые транзакции откатываются. Пользователь видит сообщение об ошибке СУБД (типичные тексты: `server closed the connection unexpectedly` (libpq), `terminating connection due to administrator command` (сервер), при недоступности сервера — `connection to server at "…" (…), port … failed: …`; так пишет libpq начиная с версии 14, а платформа с 8.3.20 поставляется с libpq 14.2, в старых libpq было `could not connect to server`; сверено 19.10.2026 по исходному коду libpq 14) ⚠ точные формулировки платформы не сверялись.
3. Временные таблицы прежних соединений исчезают вместе с соединениями; платформа создаёт их заново в новых соединениях по мере надобности.
4. Сеансы в кластере 1С остаются. Простаивавший в момент переключения пользователь при следующем действии работает уже с новым ведущим — в статье ИТС проверка сформулирована так: «1С:Предприятие не должно заметить изменений в инфраструктуре» [офиц., ИТС 5971].
5. Пока единая точка входа не указывает на новый ведущий (обычно 30–60 секунд у Patroni: `ttl` + время повышения), обращения к базе завершаются ошибкой подключения.
6. При асинхронной репликации последние подтверждённые транзакции могут отсутствовать на новом ведущем. Проверьте последние документы, обмены, очереди сообщений; длительные операции (закрытие месяца, обмен, обновление конфигурации) перезапустите.
7. Если переключение пришлось на реструктуризацию или обновление конфигурации базы данных — базу проверяют особенно тщательно (при сомнениях — восстановление из резервной копии) ⚠.

Плановое переключение проводите в технологическое окно, предварительно заблокировав начало сеансов и регламентные задания:

```bash
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd='***' \
     --sessions-deny=on --scheduled-jobs-deny=on --denied-message="Обслуживание СУБД" --permission-code=ADM
# ... переключение ...
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd='***' \
     --sessions-deny=off --scheduled-jobs-deny=off
```

---

## 9. Пулеры соединений и 1С

### 9.1. PgBouncer: режимы и что в них ломается

Режимы пула [офиц., pgbouncer.org]:

| Режим (`pool_mode`) | Когда серверное соединение возвращается в пул |
|---|---|
| `session` (по умолчанию) | когда клиент отключился |
| `transaction` | когда закончилась транзакция |
| `statement` | после каждого запроса; многооператорные транзакции запрещены |

Таблица совместимости возможностей SQL с режимами (выдержка) [офиц.]:

| Возможность | `session` | `transaction` |
|---|---|---|
| `SET` / `RESET` на уровне сеанса | да | **никогда** |
| Временные таблицы `ON COMMIT PRESERVE ROWS` / `DELETE ROWS` (живущие дольше транзакции) | да | **никогда** |
| Временные таблицы `ON COMMIT DROP` | да | да |
| `PREPARE` / `DEALLOCATE` (SQL) | да | никогда |
| Подготовленные операторы на уровне протокола | да | да, при `max_prepared_statements > 0` |
| Курсоры `WITH HOLD` | да | никогда |
| `LISTEN` | да | никогда |
| Сеансовые рекомендательные блокировки | да | никогда |
| `LOAD` | да | никогда |

### 9.2. Почему режим `transaction` не подходит для 1С

- Платформа при открытии соединения выставляет параметры сеанса командами `SET` (`lock_timeout`, `enable_mergejoin`, `cpu_operator_cost`, `client_min_messages`, `lc_messages` и др. — перечень из методики 1С приведён в статье `kb/1c/10`) [офиц.]. В режиме `transaction` следующий запрос может уйти в другое серверное соединение, где этих настроек нет.
- Платформа создаёт временные таблицы уровня сеанса и обращается к ним в последующих запросах и транзакциях того же соединения. В режиме `transaction` таблица останется в «чужом» соединении: запросы получат `relation "tt…" does not exist` либо увидят чужие данные.
- Итог: `transaction` и `statement` с 1С несовместимы — это прямо следует из таблицы PgBouncer. Режим `session` корректен, но в нём одно клиентское соединение занимает одно серверное на всё время жизни, поэтому **число процессов PostgreSQL не уменьшается**; добавляется только лишний сетевой переход и точка отказа.

Официальная позиция:

- В документации PgBouncer ограничения режимов описаны однозначно (таблица выше) [офиц.].
- Рекомендации фирмы «1С» использовать PgBouncer найти не удалось — и в полных текстах документации 8.3.27 и 75 методических статей ИТС, просмотренных 10.10.2026, PgBouncer не упоминается; прежняя оговорка (ИТС закрыт). Пример `localhost port=6432;` в документации платформы иллюстрирует только синтаксис нестандартного порта; 6432 — это ещё и порт PgBouncer по умолчанию, но о пулере там речи нет.
- Postgres Professional для 1С рекомендует `max_connections = 500..10000` [офиц., приложение K.3], то есть расчёт на прямые соединения. У сервера 1С есть собственный пул соединений с СУБД внутри рабочих процессов.

Вывод [практика]: для 1С пулер не нужен. Вместо него — достаточный `max_connections`, контроль памяти (`work_mem`, `temp_buffers` умножаются на число соединений) и настройка кластера 1С (число рабочих процессов, ограничения сеансов).

### 9.3. Если PgBouncer всё же ставят (режим `session`)

Иногда его используют как точку входа или для учёта соединений. Минимальная конфигурация (`/etc/pgbouncer/pgbouncer.ini` в пакете Ubuntu — подтверждено 11.10.2026 списком файлов пакета для 24.04 на packages.ubuntu.com (там же `/etc/pgbouncer/userlist.txt` и `pgbouncer.service`); ранее: путь по памяти; пакет `pgbouncer`):

```ini
[databases]
* = host=127.0.0.1 port=5432

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = session
max_client_conn = 2000
default_pool_size = 1000
server_reset_query = DISCARD ALL
server_idle_timeout = 600
```

Значения по умолчанию, которые «душат» 1С [офиц.]: `max_client_conn = 100`, `default_pool_size = 20` (на пару «пользователь + база»), `query_wait_timeout = 120` с — двадцать первое соединение 1С будет ждать и через две минуты получит ошибку. `server_reset_query` (`DISCARD ALL`) выполняется при возврате соединения в пул и удаляет временные таблицы и настройки сеанса. В 1С тогда указывают `адрес port=6432;`.

### 9.4. Встроенный пул соединений Postgres Pro Enterprise и proxima

- **Встроенный пул соединений** (Postgres Pro Enterprise до версии 16): в документации 16.15.1 объявлен устаревшим — «Функциональность встроенного пула соединений считается устаревшей», вместо него рекомендуют расширение pgbouncer или иное внешнее средство; там же замечено, что pgbouncer однопоточный и на нагруженных системах нужны несколько экземпляров [офиц.]. В оглавлении документации версии 17 этой главы уже нет [офиц.]. Заявлялось, что клиенты могут использовать параметры сеанса, подготовленные операторы и временные таблицы как при прямом подключении (за счёт «выделенных обслуживающих процессов») — то есть сеанс 1С и там фактически занимал отдельный процесс.
- **proxima** (Postgres Pro Enterprise 17): прокси, балансировщик и пул. При создании временной таблицы, `SET SESSION`, `set_config()`, подготовленных операторов, курсоров, сеансовых блокировок сеанс автоматически становится «динамическим выделенным сеансом» — закрепляется за обслуживающим процессом до конца подключения [офиц.]. Для 1С это значит, что выигрыша от пула нет. Ограничения: при отказе узла посреди сеанса клиентское соединение разрывается; для расширений с собственным сеансовым состоянием автоматики нет (нужен `proxima.force_dedicated = true`) [офиц.]. Совместная работа proxima и 1С ⚠ не проверялась.

---

## 10. Механизм «Копии базы данных» платформы 1С и Дата акселератор

### 10.1. Что это

Механизм платформы для ускорения работы с большими объёмами данных [офиц., v8.1c.ru]:

- платформа создаёт и обновляет **копию нужных данных в другой физической базе данных**; копий может быть несколько; для каждой настраивается состав — от одной таблицы до всех таблиц базы, существующих на момент настройки;
- данные копии платформа может использовать при выполнении запросов и при работе системы компоновки данных — тяжёлые аналитические отчёты уходят с рабочей базы, не нагружая её и не вызывая блокировок;
- копия может лежать на другом сервере СУБД (в том числе другой СУБД) либо в **Дата акселераторе** — собственной СУБД фирмы «1С» в составе кластера серверов, целиком размещающей данные в оперативной памяти; Дата акселератор «работает только совместно с механизмом копий баз данных».

Это не средство отказоустойчивости и не резервная копия: копия содержит только выбранные таблицы и служит для чтения.

### 10.2. Требования и ограничения

| Требование | Источник |
|---|---|
| Клиент-серверный вариант; механизм копий базы данных относится к функциональности уровня **КОРП** | [офиц., руководство администратора, глава о лицензировании — см. `kb/its-docs/adm-gl01-trebovaniya.md`] |
| Исключение: при серверной лицензии ПРОФ клиентская лицензия «1С:Аналитики» разрешает механизм копий совместно с Дата акселератором (один экземпляр акселератора) | [офиц.] |
| Исключение «до 10 сеансов»: возможности КОРП, кроме Дата акселератора, доступны на ПРОФ, пока к каждой базе кластера подключено не более 10 клиентских сеансов | [офиц.] |
| Дата акселератор: по разделу 1.2.2 «Клиент-серверного варианта» — только КОРП, но по разделу 3.1.5.3 той же книги и главе 26.3 «Руководства разработчика» один экземпляр в кластере допустим и при ПРОФ, более одного — только КОРП (документация в этом месте расходится); только 64-разрядный кластер, процессор поколения Intel Haswell / AMD Piledriver или новее, ОЗУ минимум 64 ГБ (рекомендуется 512 ГБ), в Linux — `transparent_hugepage` в `madvise` или `never`, `vm.overcommit_memory=1` | [офиц., `kb/its-docs/cs-gl01-trebovaniya.md`, `cs-gl03-…`] |
| Сеть не хуже 1 Гбит/с между кластером серверов и компьютером с СУБД копии | [офиц.] |
| Версия 2 механизма обновления копии для PostgreSQL: платформа **8.3.25+**, PostgreSQL **10+**, `wal_level = logical`, СУБД «установленная или обновлённая из дистрибутива 1С» (модуль `dbcopies_decoding`) | [офиц., список изменений платформы — по статье 01 этого раздела] |
| Модуль `dbcopies_decoding` («модуль 1С для обновления копий БД») входит также в сборки Postgres Professional (в «PostgreSQL для 1С» 16 — в пакете `postgrespro-1c-16-contrib`; за подробностями документация отсылает в поддержку 1С). При этом «Руководство разработчика» 8.3.27 (гл. 26.2) требует СУБД из дистрибутива фирмы «1С» и прямо говорит, что с другой сборкой «Версию 2» использовать нельзя; если СУБД её не поддерживает, работает «Версия 1». Применимость «Версии 2» к «PostgreSQL для 1С» ⚠ уточнять у 1С | [офиц., документация Postgres Pro 16 (приложение F.14); конспект `kb/its-docs/dev-gl26-kopii-bazy-dannyh.md`] |

### 10.3. Как это устроено (обзор)

Управление — стандартная функция **«Управление копиями базы данных»** (в веб-клиенте открывается ссылкой `#e1cib/system/DataBaseCopiesManagement`) [офиц.]. Для копии задаются: имя, тип СУБД и параметры подключения к базе копии, состав таблиц, способ обновления (тип репликации).

Работу механизма видно по служебным объектам платформы [офиц.]:

- фоновые задания `BackgroundJob.DBCopiesFilling` (первоначальное заполнение копии) и `BackgroundJob.DBCopiesNotification` (обновление копий), системное `SystemBackgroundJob.DBCopiesNotification`;
- событие технологического журнала `DBCOPIES` с операциями `addCopy`, `removeCopy`, `fillTable`, `continueFillTable`, `reFillTable`, `transferChangesTable` (перенос изменённых объектов), `transferTrLogs` (перенос журналов транзакций), `updateCopyContent`, `updateCopyProperties`, `updateTimeIsOver`;
- свойство `DBCopy` в событиях `DBPOSTGRS`, `SDBL`, `DBDA` — имя копии, к которой обратился запрос.

Два способа поддержания копии:

1. **Стандартная репликация** — данные переносит сама платформа: сначала заполняет таблицы копии, затем передаёт изменения. Для PostgreSQL «версия 2» получает изменения из журнала WAL через логическое декодирование модулем `dbcopies_decoding`.
2. **Внешняя репликация** — копию поддерживает СУБД своими средствами (например, физическая реплика), платформа только читает из неё [офиц., ИТС 5971]. По «Руководству разработчика» 8.3.27 (гл. 26.1–26.2) средства СУБД допустимы, только если копия используется лишь через механизм копий и в неё помещены **все** таблицы основной базы; платформа считает такую копию всегда актуальной, а любое расхождение структуры даёт ошибку запроса.

Названия в языке платформы (уточнено 19.10.2026 по конспекту главы 26 «Руководства разработчика» 8.3.27, `kb/its-docs/dev-gl26-kopii-bazy-dannyh.md`; 10.10.2026 эта глава ещё не была прочитана): тип репликации — свойство `ТипРепликации` объекта `МенеджерКопииБазыДанных` (стандартный / внешний); версия стандартной репликации — `ВерсияСтандартнойРепликацииКопийБазыДанных` (`Версия1` — изменения отслеживает кластер серверов 1С, `Версия2` — СУБД основной базы), методы `ПолучитьВерсиюСтандартнойРепликации()` / `УстановитьВерсиюСтандартнойРепликации()` (смена версии сбрасывает состояние копий — следующее обновление станет начальным заполнением); куда направлять запрос — свойства `ИспользованиеКопийБазыДанных`, `ИспользуемыеКопииБазыДанных`, `ТребуемаяАктуальностьДанных` у объекта `Запрос` и у параметров вывода компоновки данных. Запрос не уходит на копию, если в сеансе открыта транзакция или задан менеджер временных таблиц.

### 10.4. Настройка для PostgreSQL: стандартная репликация (версия 2)

Порядок — уточнено 19.10.2026 по конспекту гл. 26.2 «Руководства разработчика» 8.3.27: задать `wal_level = logical`, перезапустить СУБД, затем в стандартной функции управления копиями базы данных включить «Версия2»; если база настраивалась в прежних версиях платформы, действует «Версия1», даже когда в настройках показана «Версия2», — версию нужно переключить заново. Остальные строки ниже — защита диска и белый список модулей [офиц., PostgreSQL]:

```ini
# postgresql.conf основной СУБД
wal_level = logical                 # требует перезапуска; включает в себя уровень replica
max_replication_slots = 10          # нужен свободный слот для каждой копии
max_wal_senders = 10
max_slot_wal_keep_size = 20GB       # защита диска, см. ниже
# с минорных выпусков от 13.08.2026 - белый список модулей логического декодирования:
# output_plugin_libraries = 'pgoutput, test_decoding, dbcopies_decoding'
```

```bash
sudo systemctl restart postgresql@17-main
sudo -u postgres psql -Atc "SHOW wal_level;"
ls "$(/usr/lib/postgresql/17/bin/pg_config --pkglibdir)" | grep -i dbcopies     # модуль есть в сборке
```

Далее: подготовить сервер и пользователя для базы копии (отдельный экземпляр PostgreSQL сборки для 1С или Дата акселератор), создать копию в «Управлении копиями базы данных», дождаться первоначального заполнения.

Эксплуатационные последствия:

- `wal_level = logical` увеличивает объём WAL (в журнал пишется дополнительная информация для декодирования).
- Логическое декодирование работает через **слот репликации** на основной СУБД. Если копия перестала обновляться (остановлен сервер 1С, копия отключена или сломана, а слот остался) — слот удерживает WAL, и `pg_wal` растёт до заполнения диска. Контролируйте `pg_replication_slots` (раздел 3.3) и задайте `max_slot_wal_keep_size` ⚠ (вывод составителя из общих свойств слотов; поведение платформы при аннулировании слота не проверялось — вероятно, копию придётся заполнять заново).
- **`output_plugin_libraries`.** В выпусках PostgreSQL от 13.08.2026 — 18.6, 17.11, 16.15, 15.19, 14.24 (исправление CVE-2026-6471; сверено 19.10.2026 по замечаниям к каждому из этих выпусков; 18.5 не выпускался) — введён белый список модулей вывода логического декодирования. По умолчанию разрешены только `pgoutput` и `test_decoding`; установки, использующие другие модули, должны добавить их после обновления сервера [офиц.]. Параметр перечитывается без перезапуска (`SELECT pg_reload_conf();`); имя в списке должно точно совпадать с именем модуля, которое клиент указал при создании слота. Отказ виден в журнале как `library "…" may not be used as an output plugin`; имена модулей, уже используемых слотами, показывает запрос из документации `SELECT DISTINCT plugin FROM pg_replication_slots WHERE plugin IS NOT NULL;` — выполните его **до** обновления [офиц., runtime-config-replication 18]. Модуль 1С в список по умолчанию апстрима не входит. Проверьте после обновления: `SHOW output_plugin_libraries;` — и, если используете копии базы данных, добавьте модуль 1С ⚠ (как его включат сборки для 1С — не известно: на 19.10.2026 ни «PostgreSQL для 1С» в репозитории Postgres Professional, ни список протестированных фирмой «1С» версий ещё не содержат выпусков с этим параметром — последние 14.23, 15.18, 16.14, 17.10, 18.4).
- После аварийного переключения основной СУБД на реплику логические слоты на новом ведущем отсутствуют (физическая репликация слоты не переносит; синхронизация слотов PostgreSQL 17+ требует слота, созданного с признаком `failover`) — копию, скорее всего, придётся заполнять заново ⚠.
- После реструктуризации базы (обновление конфигурации) состав таблиц меняется; для стандартной репликации платформа учитывает это сама — уточнено 19.10.2026 по конспекту гл. 26.2 «Руководства разработчика» 8.3.27: начальный перенос таблицы в копию повторяется после любого изменения структуры (добавление или удаление реквизита, объекта); для внешней — см. ниже.

### 10.5. Внешняя репликация на PostgreSQL: реплика + промежуточная база

Проблема: физическая реплика PostgreSQL доступна только на чтение, включая временные таблицы, поэтому запросы 1С на ней завершаются ошибкой. Решение из статьи ИТС [офиц., ИТС 5971]:

1. Развернуть **дополнительный кластер PostgreSQL, доступный на запись** — отдельный сервер или второй экземпляр на одном из узлов (в примере — порт 5433).
2. Создать в нём промежуточную базу **средствами 1С** (создать информационную базу — платформа выполнит тонкие настройки базы данных), затем удалить в ней все таблицы.
3. Подключить к промежуточной базе таблицы реплики как внешние через `postgres_fdw`:

```sql
-- в промежуточной базе (psql -p 5433 -d test)
CREATE EXTENSION postgres_fdw;
CREATE SERVER standby_server FOREIGN DATA WRAPPER postgres_fdw
       OPTIONS (host '192.168.1.13', dbname 'test', port '5432');
CREATE USER MAPPING FOR postgres SERVER standby_server OPTIONS (user 'usr1cv8', password '***');
CREATE USER MAPPING FOR usr1cv8  SERVER standby_server OPTIONS (user 'usr1cv8', password '***');
IMPORT FOREIGN SCHEMA public FROM SERVER standby_server INTO public;
```

4. В настройках копии базы данных указать промежуточную базу: сервер `pg3 port=5433`, база `test`.
5. Узлу-источнику запретить становиться ведущим: тег Patroni `nofailover: true`.
6. **После каждой реструктуризации информационной базы** пересоздавать внешние таблицы:

```sql
SELECT 'DROP FOREIGN TABLE ' || string_agg(table_name, ', ') || ';'
FROM information_schema.tables WHERE table_type = 'FOREIGN' \gexec
IMPORT FOREIGN SCHEMA public FROM SERVER standby_server INTO public;
```

Оценка: схема 2020 года для PostgreSQL 11; с появлением версии 2 механизма (8.3.25) для новых внедрений логичнее стандартная репликация. Запросы через `postgres_fdw` с временными таблицами на промежуточном сервере могут выполняться неэффективно (соединения таблиц с разных серверов) ⚠ [практика].

---

## 11. Логическая репликация (публикации и подписки) и базы 1С

### 11.1. Как она устроена

Встроенная логическая репликация передаёт изменения строк отдельных таблиц; издатель и подписчик — независимые кластеры, допускаются разные мажорные версии [офиц.].

```sql
-- издатель (нужен wal_level = logical)
CREATE PUBLICATION pub_all FOR ALL TABLES;

-- подписчик: схема должна быть создана заранее (pg_dump --schema-only | psql)
CREATE SUBSCRIPTION sub_buh
       CONNECTION 'host=192.168.1.11 port=5432 dbname=buh user=replicator password=***'
       PUBLICATION pub_all;

-- контроль
SELECT * FROM pg_stat_subscription;                    -- на подписчике
SELECT slot_name, plugin, active, confirmed_flush_lsn FROM pg_replication_slots;   -- на издателе
```

Ограничения [офиц., PostgreSQL 18]:

- **схема и команды DDL не реплицируются** — изменения структуры надо повторять вручную, иначе репликация остановится с ошибкой;
- значения последовательностей не реплицируются;
- большие объекты не реплицируются;
- реплицируются только таблицы (не представления и не внешние таблицы);
- для `UPDATE` и `DELETE` у таблицы должен быть «идентификатор реплики» — первичный ключ, подходящий уникальный индекс или `REPLICA IDENTITY FULL`.

### 11.2. Применимость к 1С

| Свойство баз 1С | Следствие |
|---|---|
| Любое обновление конфигурации с изменением метаданных — это реструктуризация: платформа создаёт, переименовывает и удаляет таблицы и индексы | DDL не реплицируется → подписка ломается при каждом обновлении конфигурации |
| Нестандартные типы `mchar`, `mvarchar` и расширения `fulleq`, `fasttrun` | на подписчике нужна та же сборка для 1С |
| Многие таблицы не имеют первичного ключа в терминах PostgreSQL ⚠ (не проверялось по каталогу конкретной базы) | потребуется `REPLICA IDENTITY FULL` или назначение индекса — вмешательство в структуру, которой управляет платформа |
| Тысячи таблиц, большие транзакции (проведение, закрытие месяца) | долгая начальная синхронизация, отставание применения |
| Платформа не знает о подписчике | работать с подписчиком как с базой 1С на запись нельзя; на чтение — только пока структура совпадает |

Выводы:

- Как средство отказоустойчивости или масштабирования для 1С встроенная логическая репликация **не применяется**; официальных рекомендаций фирмы «1С» на этот счёт не найдено ⚠.
- Для отчётной нагрузки у платформы есть собственный механизм на логическом декодировании — копии базы данных (раздел 10).
- Единственный оправданный сценарий — **разовый перенос или мажорное обновление с минимальным простоем** при замороженной конфигурации (без обновлений 1С на время переноса), и только после репетиции на копии (раздел 14.6).

---

## 12. Отказоустойчивый кластер 1С + отказоустойчивый PostgreSQL: типовые схемы

Отказоустойчивость самого кластера серверов 1С (несколько центральных серверов, «уровень отказоустойчивости», резервирование кластеров, список серверов в строке подключения клиента) описана в статье `kb/1c/10`. Здесь — стыковка со слоем СУБД.

### 12.1. Схемы

**А. Одна ВМ: сервер 1С + PostgreSQL** (типично для ВМ на Windows-хосте). Отказоустойчивости нет; вторая копия PostgreSQL на той же ВМ или том же диске ничего не даёт. Правильные меры: резервные копии и архив WAL на другой носитель (статья 04), снимки/копии ВМ средствами гипервизора как дополнение, проверенная процедура восстановления.

**Б. Два узла СУБД, асинхронная реплика, ручное переключение.** Сервер 1С обращается к СУБД по DNS-имени или виртуальному адресу. RPO — секунды, RTO — время реакции администратора. Слабые места: человек в контуре; риск split-brain при неаккуратном возврате старого ведущего; слот выключенной реплики заполняет диск.

**В. Три узла: Patroni + etcd, HAProxy на серверах 1С.** Схема из статьи ИТС. Два-три узла PostgreSQL, три узла etcd (третий может жить на сервере 1С или отдельной малой ВМ), HAProxy на каждом сервере 1С (`localhost`). RTO 30–60 секунд без участия человека.

**Г. То же с виртуальным адресом** (keepalived или vip-manager) вместо HAProxy — меньше компонентов на пути запроса, но все узлы должны быть в одном сегменте сети.

**Д. Postgres Pro Enterprise BiHA** (2 узла + рефери или 3 узла) с proxima или виртуальным адресом — без внешнего DCS, по коммерческой лицензии.

**Е. Синхронная репликация поверх В–Д** — когда потеря подтверждённых транзакций недопустима; не менее двух реплик либо осознанный выбор между «останавливать запись» (`synchronous_mode_strict`) и «временно работать без гарантии».

### 12.2. Слабые места и на что смотреть

| Слабое место | Проявление | Что делать |
|---|---|---|
| Единая точка входа сама не резервирована | отдельный HAProxy упал — 1С не видит здоровую СУБД | HAProxy на каждом сервере 1С либо пара прокси с keepalived |
| Два узла без третьего голоса | при потере связи оба считают себя правыми либо оба отказываются работать | третий узел DCS / рефери / свидетель |
| Потеря кворума DCS | Patroni понижает ведущий, запись останавливается при исправной СУБД | 3 узла etcd на разных хостах; `failsafe_mode: true`; мониторинг etcd |
| Асинхронная репликация | после failover нет последних транзакций | синхронный режим либо принятый и записанный RPO; сверка после аварии |
| `synchronous_commit = off` «по рекомендации для 1С» | синхронный режим Patroni не даёт гарантий | включать `on`/`remote_write`, если нужна гарантия (раздел 4.2) |
| Слоты репликации | выключенная реплика или сломанная копия БД заполняет `pg_wal` | `max_slot_wal_keep_size`, оповещения |
| Разные сборки или версии на узлах | после переключения 1С получает `could not access file "$libdir/mchar"` и подобное | одинаковые пакеты на всех узлах, `apt-mark hold`, обновление по регламенту |
| Разные выпуски ОС на узлах | «битые» индексы на реплике после переключения | одинаковый выпуск ОС; раздел 15 |
| Таймауты простоя на прокси | ошибки СУБД у пользователей после паузы | увеличить `timeout client/server` |
| Параметры 1С заданы мимо Patroni | после переключения другие `max_connections`, `max_locks_per_transaction` | задавать через `patronictl edit-config` |
| Длительное обнаружение сбоя | 30–60 секунд ошибок у пользователей | настраивать `ttl`, `loop_wait`, `retry_timeout` с пониманием риска ложных срабатываний |
| Реплика не используется 1С для чтения | «простаивающее» железо | это плата за надёжность; отчёты — через копии базы данных |
| Лицензирование | в Postgres Pro лицензируются все серверы кластера и реплики (статья 01) | учитывать в бюджете |
| Нет регулярных учений | в аварии выясняется, что реплика давно не работает | плановые switchover по регламенту; мониторинг отставания |
| Репликация вместо резервных копий | логическая ошибка мгновенно на всех узлах | полноценное резервное копирование + проверка восстановления; при желании — отложенная реплика (`recovery_min_apply_delay`) |

Резервные копии в кластере можно снимать с реплики (`pg_basebackup` работает и на резервном сервере) [офиц., ИТС 5971 и PostgreSQL] — это снимает нагрузку с ведущего.

---

## 13. Обновление минорной версии

### 13.1. Правила

- Минорные выпуски (17.10 → 17.11) **не меняют формат хранения данных** и совместимы с предыдущими и последующими минорными выпусками той же ветки. Обновление — это замена программ при остановленном сервере и запуск; каталог данных не трогается [офиц.].
- Перед обновлением читают замечания к выпуску (раздел «Migration»): иногда нужны действия после обновления. Пример — выпуски от 13.08.2026 (18.6, 17.11, 16.15, 15.19, 14.24): новый параметр `output_plugin_libraries` (раздел 10.4); возможная переиндексация индексов `btree_gist` и `ltree`; для 18.6 — проверка `reltuples` у таблиц с GIN-индексами [офиц.].
- Актуальные минорные версии на 10.10.2026: 18.6, 17.11, 16.15, 15.19, 14.24 (ветка 14 снимается с поддержки 12.11.2026) [офиц.]. Фирма «1С» тестирует конкретные минорные версии сборок (на июль 2026 — 18.4, 17.10, 16.14, 15.18, 14.23); более свежие выпуски той же ветки на практике работают, но формально протестированными считаются перечисленные (статья 01).
- Обновляйте **сборку для 1С из её источника** (архив с releases.1c.ru или репозиторий Postgres Professional). Пакеты сборки от 1С называются так же, как дистрибутивные, поэтому держите их под `apt-mark hold`, иначе `apt upgrade` подменит их «ванильными» (статья 01).
- Установка новой версии серверного пакета сама перезапускает работающий PostgreSQL — поэтому обновление делают в окно обслуживания, а не «заодно» с `apt upgrade`. Для «PostgreSQL для 1С» уточнено 19.10.2026 по сценарию `postinst` пакета `postgrespro-1c-16-server` 16.14-1.noble: он выполняет `pg-setup service condrestart` (то есть `systemctl condrestart postgrespro-1c-16` — перезапуск, только если служба запущена), если в `/etc/default/postgrespro-1c-16` не задано `ENABLE_ONLINE_UPGRADE=1`; под Patroni, где эта служба отключена и остановлена, перезапуска не будет, и новые программы вступят в силу после `patronictl restart`. Для пакетов сборки от 1С (раскладка Debian) ⚠ не проверялось [практика].

### 13.2. Одиночный сервер

```bash
# 0. Резервная копия, окно обслуживания, остановка сервера 1С
systemctl list-units 'srv1cv8*' --no-pager
sudo systemctl stop 'srv1cv8*'

# 1а. Сборка от 1С (новый архив той же ветки распакован в /tmp/pg1c-new)
sudo apt-mark unhold postgresql-17 postgresql-client-17 libpq5
sudo apt-get install -y /tmp/pg1c-new/*.deb
sudo systemctl restart postgresql@17-main
sudo apt-mark hold postgresql-17 postgresql-client-17 libpq5

# 1б. "PostgreSQL для 1С" Postgres Professional
sudo apt-get update
dpkg-query -W -f='${Package}\n' 'postgrespro-1c-17*' | xargs sudo apt-mark unhold
sudo apt-get install --only-upgrade -y $(dpkg-query -W -f='${Package} ' 'postgrespro-1c-17*')
sudo systemctl restart postgrespro-1c-17
dpkg-query -W -f='${Package}\n' 'postgrespro-1c-17*' | xargs sudo apt-mark hold

# 2. Проверка
sudo -u postgres psql -Atc "SELECT version();"
sudo -u postgres psql -Atc "SHOW output_plugin_libraries;"        # есть в выпусках от 08.2026
sudo -u postgres psql -d buh -c "SELECT name, installed_version, default_version FROM pg_available_extensions
                                 WHERE installed_version IS NOT NULL AND installed_version <> default_version;"
#    при необходимости: ALTER EXTENSION имя UPDATE;

# 3. Запуск сервера 1С
sudo systemctl start 'srv1cv8*'
```

### 13.3. Кластер с репликами

Порядок [офиц.]: «самая безопасная политика — сначала обновить резервные серверы: новый минорный выпуск с большей вероятностью прочитает WAL предыдущего, чем наоборот».

Ручная схема:

1. Обновить пакеты и перезапустить PostgreSQL на каждой реплике по очереди; убедиться, что репликация возобновилась (`pg_stat_replication`).
2. Плановое переключение на обновлённую реплику (раздел 6.2) — простой для 1С равен времени переключения.
3. Обновить бывший ведущий (теперь реплику).
4. При желании переключиться обратно.

Под управлением Patroni:

```bash
# на каждой реплике по очереди
sudo apt-get install ...                              # новые пакеты сборки
patronictl -c /etc/patroni/config.yml restart pg1c pg2 --force
patronictl -c /etc/patroni/config.yml list            # дождаться streaming и нулевого отставания

# затем сменить лидера и обновить бывший ведущий
patronictl -c /etc/patroni/config.yml switchover pg1c --leader pg1 --candidate pg2 --force
sudo apt-get install ...                              # на pg1
patronictl -c /etc/patroni/config.yml restart pg1c pg1 --force
patronictl -c /etc/patroni/config.yml version pg1c    # версии PostgreSQL на узлах
```

Если установка пакета сама перезапускает или останавливает PostgreSQL в обход Patroni, предварительно включите режим обслуживания `patronictl pause` и снимите его после (`patronictl resume`) ⚠ [практика]. Для BiHA порядок аналогичен: обновить последователя, повысить его (`biha.set_leader`), обновить остальные узлы и старого лидера, вернуть лидерство старому лидеру (`biha.set_leader`), затем `ALTER EXTENSION biha UPDATE;` на лидере; рефери в режиме `referee` расширение не обновляет — его удаляют (`biha.remove_node`) и создают заново [офиц., документация Postgres Pro Enterprise 17, раздел 27.3.16].

---

## 14. Обновление мажорной версии

### 14.1. Перед началом

- Между мажорными версиями формат данных и системных каталогов меняется: просто заменить пакеты нельзя [офиц.].
- **Совместимость с платформой 1С проверяется до обновления** (подробная таблица — статья 01, раздел 3.3):

| Платформа 1С | Мажорные версии PostgreSQL |
|---|---|
| 8.3.22 – 8.3.26 | 14–17 |
| 8.3.27 | 14–18 |
| 8.5.x | 14–18 |

  Если платформа не поддерживает целевую версию СУБД — сначала обновляют платформу (она продолжит работать со старой версией PostgreSQL), потом СУБД. После обновления СУБД платформа должна оставаться в поддерживаемом сочетании.
- Целевая версия должна быть **сборкой для 1С того же семейства** с расширениями `mchar`, `fulleq`, `fasttrun` и теми библиотеками, что перечислены в `shared_preload_libraries` (`plantuner`, `online_analyze`, `auto_dump` …). На «ванильный» PostgreSQL базу 1С обновить нельзя: `pg_upgrade --check` остановится на проверке библиотек.
- Жизненный цикл: 14 — до 12.11.2026, 15 — до 11.11.2027, 16 — до 09.11.2028, 17 — до 08.11.2029, 18 — до 14.11.2030; PostgreSQL 19 на 19.10.2026 — кандидат в выпуск (RC 1 от 15.10.2026), окончательный выпуск ещё не вышел [офиц., postgresql.org].
- Обязательно: полная резервная копия, репетиция на копии сервера, замер времени, план отката.

### 14.2. Способы

| Способ | Простой | Место на диске | Особенности |
|---|---|---|---|
| `pg_upgrade` (копирование) | минуты–часы (зависит от объёма) | × 2 | старый кластер остаётся нетронутым — простой откат |
| `pg_upgrade --link` | минуты | почти не требуется | жёсткие ссылки; после запуска нового кластера старый использовать нельзя; оба каталога на одной ФС |
| `pg_upgrade --clone` | минуты | почти не требуется | reflink (XFS с reflink, Btrfs); старый кластер остаётся пригодным |
| `pg_upgradecluster` (Debian/Ubuntu) | как у выбранного метода | — | обёртка: `dump` (по умолчанию) или `pg_upgrade` |
| Дамп и восстановление (`pg_dump` / `pg_restore`) | часы | × 1 + дамп | заодно убирает раздувание и снимает вопрос правил сортировки; можно на новый сервер и новую ОС |
| Средства 1С (`.dt`, `ibcmd infobase dump/restore`, `ibcmd infobase replicate`) | часы | — | перенос на уровне платформы; годится и для смены СУБД |
| Логическая репликация | секунды–минуты | × 2 | для 1С — только при «замороженной» конфигурации и после репетиции (раздел 11) |

### 14.3. `pg_upgrade`: ключи и порядок действий

Синтаксис и ключи [офиц., PostgreSQL 18]:

```text
pg_upgrade -b старый_bin [-B новый_bin] -d старый_каталог_конфигурации -D новый_каталог_конфигурации [ключи]
```

| Ключ | Действие |
|---|---|
| `-b`, `--old-bindir` / `-B`, `--new-bindir` | каталоги программ старой / новой версии |
| `-d`, `--old-datadir` / `-D`, `--new-datadir` | каталоги (конфигурации) старого / нового кластера |
| `-c`, `--check` | только проверка, данные не меняются; можно выполнять при работающем старом сервере |
| `-k`, `--link` | жёсткие ссылки вместо копирования |
| `--clone` | клонирование файлов (reflink) |
| `--copy` | копирование (по умолчанию) |
| `--copy-file-range` | копирование системным вызовом `copy_file_range` |
| `--swap` | (PostgreSQL 18) перенос каталогов данных в новый кластер; старый становится непригодным с начала переноса |
| `-j N`, `--jobs` | параллельная обработка баз и табличных пространств |
| `-p`, `-P` | порты старого и нового кластера на время обновления (по умолчанию 50432) |
| `-o`, `-O` | дополнительные параметры для старого / нового `postgres` |
| `-U` | имя суперпользователя кластера |
| `-r`, `--retain` | сохранить журналы и SQL-файлы после успеха |
| `--no-statistics` | (PostgreSQL 18) не переносить статистику планировщика |

Порядок действий по документации, применительно к сборке «PostgreSQL для 1С» Postgres Professional (17 → 18):

```bash
# 1. Установить пакеты новой версии рядом со старой (другой каталог /opt/pgpro/1c-18).
#    Документация Postgres Pro: метапакет верхнего уровня при обновлении и миграции не используют -
#    ставят отдельные пакеты сервера и contrib (см. статью 01).

# 2. Создать пустой кластер новой версии с теми же локалью, кодировкой и режимом контрольных сумм. НЕ запускать.
#    (Совпадение контрольных сумм обязательно; локаль и кодировку pg_upgrade 16+ переносит сам, но лучше совпадение.)
sudo LANG=ru_RU.UTF-8 /opt/pgpro/1c-18/bin/pg-setup initdb      # для конфигураций WE - LANG=en_US.UTF-8
sudo -u postgres env LANG=C /opt/pgpro/1c-17/bin/pg_controldata /var/lib/pgpro/1c-17/data | grep -i checksum
sudo -u postgres env LANG=C /opt/pgpro/1c-18/bin/pg_controldata /var/lib/pgpro/1c-18/data | grep -i checksum
#    значения "Data page checksum version" должны совпасть (0 - выключены, 1 - включены)

# 3. Перенести в новый кластер нужные настройки: pg_hba.conf, shared_preload_libraries и параметры 1С.
#    Старый postgresql.conf целиком не копировать - в новой версии часть параметров удалена или переименована.

# 4. Остановить сервер 1С и оба сервера PostgreSQL. Реплики на момент остановки ведущего должны работать,
#    чтобы получить все изменения.
sudo systemctl stop 'srv1cv8*'
sudo systemctl stop postgrespro-1c-17
sudo systemctl stop postgrespro-1c-18 2>/dev/null

# 5. Проверка (из каталога, куда пользователь postgres может писать).
cd /tmp
sudo -u postgres /opt/pgpro/1c-18/bin/pg_upgrade \
     -b /opt/pgpro/1c-17/bin -B /opt/pgpro/1c-18/bin \
     -d /var/lib/pgpro/1c-17/data -D /var/lib/pgpro/1c-18/data \
     --check

# 6. Обновление (при нехватке места или большой базе - добавить --link; -j 4 ускоряет при нескольких базах).
sudo -u postgres /opt/pgpro/1c-18/bin/pg_upgrade \
     -b /opt/pgpro/1c-17/bin -B /opt/pgpro/1c-18/bin \
     -d /var/lib/pgpro/1c-17/data -D /var/lib/pgpro/1c-18/data -j 4

# 7. Запустить новый сервер, отключить старую службу.
sudo systemctl disable postgrespro-1c-17
sudo systemctl enable --now postgrespro-1c-18

# 8. Выполнить сценарии, которые создал pg_upgrade (если создал), например update_extensions.sql.
sudo -u postgres /opt/pgpro/1c-18/bin/psql -f update_extensions.sql postgres

# 9. Статистика (см. ниже) и проверка.
sudo -u postgres /opt/pgpro/1c-18/bin/vacuumdb --all --analyze-in-stages --missing-stats-only
sudo -u postgres /opt/pgpro/1c-18/bin/vacuumdb --all --analyze-only
sudo -u postgres /opt/pgpro/1c-18/bin/psql -Atc "SELECT version();"

# 10. Запустить сервер 1С, проверить работу; старый кластер удалить после периода наблюдения
#     сценарием, имя которого pg_upgrade выводит по завершении (обычно ./delete_old_cluster.sh).
```

Ключевые положения документации [офиц.]:

- **Расширения.** В новую установку нужно поставить те же разделяемые библиотеки расширений (обычно пакетами); команду `CREATE EXTENSION` выполнять **не нужно** — определения объектов переносятся из старого кластера. Если доступны обновления расширений, `pg_upgrade` сообщит об этом и создаст сценарий. Для 1С это означает: пакет `-contrib` (или его аналог в сборке) новой версии с `mchar`, `fulleq`, `fasttrun`, `plantuner` должен быть установлен до запуска.
- **Аутентификация.** `pg_upgrade` несколько раз подключается к обоим серверам — на время обновления нужен метод `peer` для локальных подключений либо файл `~/.pgpass`.
- **Текущий каталог** должен быть доступен на запись пользователю, запускающему `pg_upgrade`; рабочие файлы и журналы — в `pg_upgrade_output.d` внутри нового кластера (при успехе удаляются).
- **Статистика.** До версии 17 включительно статистика планировщика не переносится — сразу после обновления выполняют `vacuumdb --all --analyze-in-stages`. Начиная с **PostgreSQL 18** `pg_upgrade` переносит основную статистику (кроме расширенной из `CREATE STATISTICS` и накопительной), и документация предписывает: `vacuumdb --all --analyze-in-stages --missing-stats-only`, затем `vacuumdb --all --analyze-only` (чтобы корректно заработали автоочистка и автоанализ). Ускорение — ключ `--jobs`; обход ограничения скорости очистки — `PGOPTIONS='-c vacuum_cost_delay=0' vacuumdb …`.
- **Режим `--link`.** Самый быстрый и не требует места, но после запуска нового кластера старый использовать нельзя. Откат: если новый кластер ещё не запускался — убрать суффикс `.old` у файла `global/pg_control` старого кластера и запустить его; если запускался — только восстановление из резервной копии.
- **Откат без `--link`:** старый кластер не изменён — достаточно снова его запустить.
- **Контрольные суммы.** Режим в старом и новом кластере должен совпадать, иначе `pg_upgrade` откажется работать. Начиная с PostgreSQL 18 `initdb` включает их по умолчанию; для обновления кластера, созданного без контрольных сумм, новый кластер инициализируют с `--no-data-checksums` либо заранее включают суммы в старом утилитой `pg_checksums --enable` при остановленном сервере (статья 01). В сборках Postgres Professional суммы включает `pg-setup initdb` (в том числе при быстрой установке) во всех версиях; отключить — `--no-data-checksums` у `pg-setup` (документация сборки 16, раздел 18.1). Сам `initdb` версий до 18 включает их только ключом `-k`.
- **Слоты и модули декодирования.** Начиная с выпусков 08.2026 `pg_upgrade --check` завершится ошибкой, если `output_plugin_libraries` нового кластера не разрешает модули логических слотов старого (при обновлении с 17 и новее) — актуально при использовании копий базы данных 1С.
- **Типы `reg*`.** Обновление не поддерживается для столбцов типов `regcollation`, `regconfig`, `regdictionary`, `regnamespace`, `regoper`, `regoperator`, `regproc`, `regprocedure`.
- Документация Postgres Pro по модулю `mchar` отсылает к подразделу «Предотвращение ошибок разрешения типов операторов» на случай сбоев при переносе баз с нестандартными типами [офиц.]; при ошибках восстановления схемы смотрите журнал в `pg_upgrade_output.d`.

### 14.4. `pg_upgradecluster` (раскладка Debian/Ubuntu, сборка от 1С)

```text
pg_upgradecluster [-v новая_версия] старая_версия имя [новый_каталог_данных]
```

Ключи [офиц., man-страница postgresql-common 257, Ubuntu 24.04]:

| Ключ | Действие |
|---|---|
| `-v версия` | целевая версия (по умолчанию — самая новая из установленных) |
| `-m`, `--method=dump\|upgrade\|link\|clone` | `dump` — `pg_dump` + `pg_restore` (**по умолчанию**); `upgrade` — `pg_upgrade`; `link` и `clone` — сокращения для `-m upgrade --link` и `-m upgrade --clone` |
| `-k`, `--link`; `--clone` | режимы `pg_upgrade` |
| `-j N`, `--jobs` | число параллельных процессов (для `pg_upgrade` и перехватчика `analyze`) |
| `--locale`, `--lc-collate`, `--lc-ctype` … | локаль нового кластера (по умолчанию наследуется от старого) |
| `--keep-port` | не менять порты местами |
| `--rename=имя` | другое имя нового кластера |
| `--old-bindir=каталог` | передаётся `pg_upgrade` |
| `--maintenance-db=база` | база для служебных запросов (по умолчанию `template1`) |
| `--[no-]start` | запускать ли новый кластер после обновления |
| `--keep-on-error` | не удалять новый кластер при неудаче |
| `--logfile файл` | файл журнала нового кластера |

Поведение по умолчанию [офиц.]: конфигурация старого кластера копируется и адаптируется; **новый кластер получает исходный порт, старый переносится на ранее не использовавшийся порт**; старый кластер не удаляется и переводится в ручной запуск (`manual`); контрольные суммы наследуются от старого кластера. Сценарии-перехватчики — в `/etc/postgresql-common/pg_upgradecluster.d/`; они вызываются с аргументами `<старая версия> <имя кластера> <новая версия> <фаза>`, фазы `init` (создан пустой новый кластер) и `finish` (данные перенесены); сбой сценария прерывает обновление.

```bash
# 1. Установить пакеты сборки от 1С для версии 18 (архив с releases.1c.ru): пакет создаст пустой кластер 18/main
sudo apt-get install -y /tmp/pg1c-18/*.deb
pg_lsclusters
# Ver Cluster Port Status Owner    Data directory              Log file
# 17  main    5432 online postgres /var/lib/postgresql/17/main ...
# 18  main    5433 online postgres /var/lib/postgresql/18/main ...

# 2. Удалить ПУСТОЙ кластер 18/main - иначе pg_upgradecluster откажется (целевой кластер уже существует)
sudo pg_dropcluster --stop 18 main

# 3. Остановить сервер 1С и обновить
sudo systemctl stop 'srv1cv8*'
sudo pg_upgradecluster -m upgrade -v 18 17 main            # копирование через pg_upgrade
# sudo pg_upgradecluster -m link -j 4 -v 18 17 main        # жёсткие ссылки, параллельно

# 4. Проверить
pg_lsclusters                                              # 18/main - порт 5432, online; 17/main - другой порт, down
sudo -u postgres psql -Atc "SELECT version();"
sudo -u postgres vacuumdb --all --analyze-in-stages        # для 18: добавить --missing-stats-only, затем --analyze-only

# 5. Запустить сервер 1С, проверить работу; зафиксировать пакеты
sudo apt-mark hold postgresql-18 postgresql-client-18 libpq5

# 6. После периода наблюдения удалить старый кластер и пакеты
sudo pg_dropcluster 17 main
sudo apt-get purge -y postgresql-17 postgresql-client-17
```

Замечания: без `-m` выполняется выгрузка и загрузка (`dump`) — на больших базах это долго; `-m link` требует, чтобы каталоги обеих версий были на одной файловой системе; параметры в скопированном `postgresql.conf`, отсутствующие в новой версии, обёртка комментирует/адаптирует, но файл стоит просмотреть вручную [практика].

### 14.5. Дамп и восстановление

Используются утилиты **новой** версии — они читают серверы начиная с 9.2 [офиц.].

```bash
# старый сервер - порт 5432, новый (той же сборки для 1С, новой версии) - порт 5433
NEWBIN=/usr/lib/postgresql/18/bin

# роли и табличные пространства
sudo -u postgres $NEWBIN/pg_dumpall -p 5432 --globals-only > /backup/globals.sql
sudo -u postgres $NEWBIN/psql -p 5433 -f /backup/globals.sql postgres

# каждая база: каталоговый формат, параллельно
sudo -u postgres $NEWBIN/pg_dump -p 5432 -Fd -j 4 -f /backup/buh.dir buh
sudo -u postgres $NEWBIN/pg_restore -p 5433 -C -d postgres -j 4 /backup/buh.dir

# статистика
sudo -u postgres $NEWBIN/vacuumdb -p 5433 --all --analyze-in-stages
```

Вариант «всё одним потоком» из документации: `pg_dumpall -p 5432 | psql -d postgres -p 5433` [офиц.]. Средства платформы: выгрузка и загрузка `.dt`, `ibcmd infobase dump` / `restore`, а также `ibcmd infobase replicate` — прямая передача базы из одной СУБД в другую с параметрами `--target-dbms`, `--target-db-server`, `--target-db-name`, параллельность `-j` / `-J` (статья `kb/1c/06`) [офиц.]. При любом варианте на время переноса работа пользователей в базе прекращается.

### 14.6. Логическая репликация и `pg_createsubscriber`

Документация называет логическую репликацию третьим способом мажорного обновления с простоем «несколько секунд» [офиц.]. С PostgreSQL 17 есть утилита `pg_createsubscriber`: она превращает физическую реплику в логического подписчика без повторной заливки данных (на источнике нужны `wal_level = logical`, свободные слоты и `max_slot_wal_keep_size = -1` на время работы; версии источника, цели и утилиты должны совпадать) [офиц.]. Дальше подписчика обновляют `pg_upgrade` и после догоняющей репликации переключают на него приложение.

Для 1С этот путь требует: полного запрета изменений структуры (никаких обновлений конфигурации и реструктуризаций) на всё время, одинаковых сборок, проверки идентификаторов реплики у таблиц и обязательной репетиции (раздел 11). Официальных материалов 1С по нему нет ⚠; при допустимом окне в несколько часов проще `pg_upgrade --link`.

### 14.7. Реплики и Patroni при мажорном обновлении

- `pg_upgrade` на резервных серверах не выполняется. После обновления ведущего реплики **создают заново** (`pg_basebackup`) либо, при режиме `--link`, синхронизируют `rsync` по процедуре из документации (`rsync --archive --delete --hard-links --size-only --no-inc-recursive старый_каталог новый_каталог реплика:родительский_каталог`) — вариант для опытных [офиц.].
- Слоты репликации нужно создать заново: если старый кластер старше 17.0, слоты не переносятся вовсе; если 17.0 и новее — переносятся только логические [офиц.].
- Порядок для Patroni [офиц.]:
  1. остановить Patroni на всех узлах;
  2. обновить программы и выполнить `pg_upgrade` на ведущем;
  3. поправить `patroni.yml` (каталоги `bin_dir`, `data_dir`);
  4. удалить из DCS ключ `initialize` либо всё состояние кластера (`patronictl remove имя_кластера`) — `pg_upgrade` выполняет `initdb`, и у кластера новый системный идентификатор;
  5. при желании скопировать `patroni.dynamic.json` из старого каталога данных в новый;
  6. запустить Patroni на ведущем;
  7. на репликах обновить программы, поправить `patroni.yml`, очистить каталог данных;
  8. запустить Patroni на репликах — они будут созданы заново.

### 14.8. Контрольный список мажорного обновления для 1С

1. Платформа 1С поддерживает целевую версию PostgreSQL (таблица в 14.1); сборка целевой версии для вашей ОС существует (статья 01, раздел 3.4).
2. Свежая проверенная резервная копия; место на диске; расчёт времени по репетиции.
3. Установлены пакеты новой версии со всеми расширениями 1С; `pg_upgrade --check` проходит.
4. Начало сеансов и регламентные задания заблокированы, сервер 1С остановлен.
5. Обновление выполнено; настройки (`pg_hba.conf`, параметры 1С, `shared_preload_libraries`) перенесены; порт прежний (или изменён адрес в свойствах баз).
6. Собрана статистика; выполнены сценарии обновления расширений.
7. Проверки: `SELECT version();`, `\dx` в базе 1С (`mchar`, `fulleq`, `fasttrun`), вход в 1С, проведение документа, отчёт, тест производительности.
8. Реплики и слоты пересозданы, резервное копирование перенастроено на новые пути и сделана новая полная копия (старые физические копии к новой версии неприменимы).
9. Пакеты новой версии поставлены на `hold`; старый кластер удалён после периода наблюдения.

---

## 15. Обновление ОС и изменение правил сортировки (collation version mismatch)

### 15.1. В чём проблема

Порядок сортировки строк PostgreSQL берёт из внешней библиотеки: glibc (провайдер `libc`) или ICU (провайдер `icu`). B-tree-индексы по текстовым столбцам хранят строки в этом порядке. Если после обновления ОС библиотека сортирует иначе, индекс оказывается «неправильно упорядоченным»: запросы не находят существующие строки, уникальные индексы пропускают дубликаты [офиц.].

- Самое крупное изменение — glibc 2.28: затронуты переходы на Ubuntu 18.10 и новее (то есть 18.04 → 20.04 и далее), Debian 10, RHEL 8 [офиц., wiki.postgresql.org].
- Версии glibc в LTS-выпусках Ubuntu [офиц., packages.ubuntu.com]: 22.04 — 2.35, 24.04 — 2.39, 26.04 — 2.43. ICU: `libicu70`, `libicu74`, `libicu78` соответственно (статья 01).
- PostgreSQL не может проверить, изменились ли правила на самом деле: он сравнивает **номер версии** библиотеки, записанный при создании базы или правила сортировки, с текущим — и при несовпадении предупреждает. Для glibc номер версии библиотеки используется как приближение версии правил [офиц.]. Поэтому при любом обновлении выпуска Ubuntu предупреждение будет, даже если реальный порядок для ваших данных не изменился.
- Под угрозой B-tree-индексы по `text`, `varchar`, `char` (включая составные) и ключи секционирования по диапазонам; не затронуты `bytea`, числа, базы и столбцы с локалью `C`/`POSIX`. Логические дампы (`pg_dump`) и логическая репликация проблеме не подвержены; подвержены все «двоичные» способы: обновление ОС на месте, `pg_upgrade`, потоковая репликация на сервер с другими правилами, восстановление физической копии на другой ОС [офиц., wiki].
- **Реплика на другом выпуске ОС, чем ведущий, может иметь повреждённые (с точки зрения её библиотеки) индексы при исправном ведущем** [офиц., wiki] — отсюда требование одинаковой ОС на узлах.

Особенность 1С: строковые данные хранятся в типах `mchar` / `mvarchar`, которые сравниваются средствами библиотеки ICU внутри модуля `mchar`, независимо от правил сортировки базы [офиц., документация Postgres Pro]. Версию ICU для этих типов PostgreSQL не отслеживает (это не объекты `pg_collation`), поэтому при смене версии ICU, с которой собрана сборка, предупреждения про индексы по `mchar`/`mvarchar` не будет ⚠ (вывод составителя). Практическое правило: **после обновления выпуска ОС или переноса физической копии на другой выпуск ОС переиндексируйте базы 1С целиком**, не дожидаясь предупреждений.

### 15.2. Как обнаружить

Предупреждения в журнале сервера и в `psql` при подключении к базе:

```text
WARNING:  database "buh" has a collation version mismatch
DETAIL:  The database was created using collation version 2.35, but the operating system provides version 2.39.
HINT:  Rebuild all objects in this database that use the default collation and run ALTER DATABASE buh REFRESH COLLATION VERSION, or build PostgreSQL with the right library version.
```

```text
WARNING:  collation "xx-x-icu" has version mismatch
DETAIL:  The collation in the database was created using version 1.2.3.4, but the operating system provides version 2.3.4.5.
HINT:  Rebuild all objects affected by this collation and run ALTER COLLATION pg_catalog."xx-x-icu" REFRESH VERSION, or build PostgreSQL with the right library version.
```

Второй текст — дословно из документации [офиц.]; первый (для правила сортировки базы по умолчанию) — подтверждено 19.10.2026 (исходный код PostgreSQL 16 и 18, `src/backend/utils/init/postinit.c`: тексты `WARNING`, `DETAIL`, `HINT` совпадают), номера версий — пример для перехода 22.04 → 24.04.

Запросы (PostgreSQL 15 и новее):

```sql
-- правило сортировки по умолчанию каждой базы: записанная и фактическая версии
SELECT datname, datlocprovider, datcollate, datcollversion,
       pg_database_collation_actual_version(oid) AS actual_version
FROM pg_database
WHERE datallowconn;

-- отдельные правила сортировки с расхождением (выполнять в каждой базе)
SELECT collname, collprovider, collversion, pg_collation_actual_version(oid) AS actual_version
FROM pg_collation
WHERE collversion IS NOT NULL AND collversion <> pg_collation_actual_version(oid);

-- какие объекты зависят от правил сортировки, требующих обновления (запрос из документации)
SELECT pg_describe_object(refclassid, refobjid, refobjsubid) AS "Collation",
       pg_describe_object(classid, objid, objsubid) AS "Object"
  FROM pg_depend d JOIN pg_collation c
       ON refclassid = 'pg_collation'::regclass AND refobjid = c.oid
  WHERE c.collversion <> pg_collation_actual_version(c.oid)
  ORDER BY 1, 2;
```

Проверка на уровне ОС (сравнить вывод на старой и новой системе; совпадение не гарантирует отсутствия других отличий) [офиц., wiki]:

```bash
( echo "1-1"; echo "11" ) | LC_COLLATE=en_US.UTF-8 sort
( echo "1-1"; echo "11" ) | LC_COLLATE=ru_RU.UTF-8 sort
ldd --version | head -n1                     # версия glibc
dpkg -l 'libicu*' | grep ^ii                 # версия ICU
```

Проверка конкретного индекса расширением `amcheck` (если оно есть в сборке): `CREATE EXTENSION amcheck; SELECT bt_index_check('имя_индекса'::regclass, true);`.

### 15.3. Как исправить

```bash
# 1. Окно обслуживания: остановить сервер 1С
sudo systemctl stop 'srv1cv8*'

# 2. Переиндексировать все базы (включая postgres и template1)
sudo -u postgres reindexdb --all --verbose
#    или по одной базе, параллельно:
sudo -u postgres reindexdb --dbname=buh --jobs=4 --verbose
```

```sql
-- 3. Обновить записанную версию - только ПОСЛЕ перестройки индексов
ALTER DATABASE buh       REFRESH COLLATION VERSION;
ALTER DATABASE postgres  REFRESH COLLATION VERSION;
ALTER DATABASE template1 REFRESH COLLATION VERSION;

-- отдельные правила сортировки, если по ним были предупреждения (в каждой базе)
ALTER COLLATION pg_catalog."ru-RU-x-icu" REFRESH VERSION;
```

- `ALTER DATABASE … REFRESH COLLATION VERSION` и `ALTER COLLATION … REFRESH VERSION` **только обновляют запись в каталоге и убирают предупреждение**; они не проверяют, что объекты действительно перестроены [офиц.]. Выполнить их без `REINDEX` — значит спрятать проблему.
- `REINDEX` блокирует запись в таблицу; на рабочей базе без остановки используют `REINDEX … CONCURRENTLY` (`reindexdb --concurrently`), но для баз 1С с тысячами таблиц проще окно обслуживания (статья 05).
- Полная переиндексация порождает WAL объёмом порядка суммарного размера индексов — проверьте место в `pg_wal`, архиве и на репликах; слоты отстающих реплик в это время особенно опасны.
- Таблицы, секционированные по диапазонам текстовых ключей, нужно проверить отдельно (строки могли оказаться «не в своей» секции) [офиц., wiki]; в базах 1С секционирование обычно не используется.

### 15.4. Как обновлять ОС сервера СУБД

| Способ | Правила сортировки | Комментарий |
|---|---|---|
| Новый сервер с новой ОС + `pg_dump` / `pg_restore` (или средства 1С) | проблемы нет — индексы строятся заново | самый чистый путь; заодно мажорное обновление PostgreSQL |
| Новый сервер + физическая копия или реплика со старого | **нужна полная переиндексация** после переключения | быстрый перенос данных, затем `REINDEX` в окно |
| `do-release-upgrade` на месте | **нужна полная переиндексация** | см. ниже |

Особенности `do-release-upgrade` для сервера с PostgreSQL для 1С [практика]:

- сделать резервную копию и снимок ВМ; проверить, что для новой ОС есть сборка PostgreSQL нужной версии и что платформа 1С поддерживает новую ОС (статья 01, раздел 3.4: сервер 1С на 10.10.2026 официально поддерживает 22.04 и 24.04, но не 26.04);
- сторонние репозитории (Postgres Professional, PGDG) при обновлении выпуска отключаются — после обновления их включают заново для нового кодового имени и обновляют пакеты сборки до версии, собранной под новую ОС;
- пакеты сборки от 1С имеют те же имена, что дистрибутивные: `hold` защитит от подмены, но установленные пакеты, собранные под старую ОС, могут оказаться несовместимыми с новыми библиотеками — после обновления ставят сборку для нового выпуска Ubuntu;
- в новом выпуске Ubuntu версия PostgreSQL «по умолчанию» другая (14 → 16 → 18); существующий кластер при этом не обновляется автоматически, `postgresql-common` продолжает им управлять;
- после загрузки: проверить запуск кластера, версии glibc/ICU, выполнить переиндексацию и `REFRESH COLLATION VERSION` (15.3).

---

## 16. Перенос сервера БД на другой хост и переключение 1С

### 16.1. Способы

| Способ | Простой | Требования | Когда выбирать |
|---|---|---|---|
| Реплика на новом хосте + плановое переключение | минуты | та же мажорная версия и сборка, та же архитектура; желательно тот же выпуск ОС (иначе `REINDEX`) | большие базы, минимальный простой |
| `pg_basebackup` при остановленной работе 1С | время копирования | то же | средние базы, простая процедура |
| `rsync` остановленного кластера | время копирования | то же + одинаковые пути | когда нет сетевого доступа по протоколу репликации; быстрый повтор «догоняющим» проходом |
| `pg_dump` / `pg_restore` | часы | на новом хосте сборка для 1С (версия может быть новее) | смена версии, ОС, архитектуры; «чистые» индексы |
| Средства 1С (`.dt`, `ibcmd infobase replicate`) | часы | работающий сервер 1С или `ibcmd` | небольшие базы, смена СУБД |

### 16.2. Перенос через реплику (минимальный простой)

1. На новом хосте установить ту же сборку и создать реплику (раздел 2.3 или 2.4).
2. Дождаться `state = streaming` и нулевого отставания.
3. В окно: заблокировать сеансы 1С, остановить старый ведущий, повысить новый сервер (раздел 6.2, шаги 1–3).
4. Переключить 1С (16.5). Старый сервер не запускать (отключить службу) либо превратить в реплику.
5. Если выпуск ОС отличается — переиндексация (раздел 15.3).

### 16.3. Перенос `pg_basebackup` или `rsync`

```bash
# --- вариант pg_basebackup (на НОВОМ хосте; сервер 1С остановлен, чтобы данные не менялись) ---
sudo systemctl stop postgresql@17-main
sudo -u postgres mv /var/lib/postgresql/17/main /var/lib/postgresql/17/main.empty
sudo -u postgres /usr/lib/postgresql/17/bin/pg_basebackup -h СТАРЫЙ_ХОСТ -U replicator \
     -D /var/lib/postgresql/17/main -X stream -c fast -P
#    без ключа -R: сервер запустится самостоятельным (не репликой)
sudo systemctl start postgresql@17-main
```

```bash
# --- вариант rsync (PostgreSQL на обоих хостах одной версии и сборки) ---
# на новом хосте: кластер остановлен
sudo systemctl stop postgresql@17-main

# на старом хосте: предварительный проход при работающем сервере (сокращает простой), затем остановка и чистовой проход
sudo rsync -a --delete /var/lib/postgresql/17/main/ НОВЫЙ_ХОСТ:/var/lib/postgresql/17/main/
sudo systemctl stop 'srv1cv8*'
sudo systemctl stop postgresql@17-main
sudo rsync -a --delete --checksum /var/lib/postgresql/17/main/ НОВЫЙ_ХОСТ:/var/lib/postgresql/17/main/
sudo rsync -a /etc/postgresql/17/main/ НОВЫЙ_ХОСТ:/etc/postgresql/17/main/

# на новом хосте
sudo chown -R postgres:postgres /var/lib/postgresql/17/main /etc/postgresql/17/main
sudo systemctl start postgresql@17-main
```

Правила для `rsync`:

- чистовой проход — **только при остановленном PostgreSQL**; копия каталога работающего сервера без режима резервного копирования непригодна;
- ключ `--checksum` на чистовом проходе нужен, потому что `rsync` сравнивает время изменения с точностью до секунды (рекомендация из документации `pg_upgrade`) [офиц.];
- `rsync` от имени root по SSH требует входа root или `--rsync-path="sudo rsync"`; идентификаторы пользователя `postgres` на хостах могут различаться — после копирования проверьте владельца;
- табличные пространства лежат вне каталога данных (ссылки в `pg_tblspc/`) — их каталоги копируют отдельно по тем же путям;
- в раскладке Postgres Pro конфигурация находится внутри каталога данных и копируется вместе с ним; каталог — `/var/lib/pgpro/1c-17/data`.

### 16.4. Перенос дампом

```bash
# на старом хосте
sudo -u postgres pg_dumpall --globals-only > /backup/globals.sql
sudo -u postgres pg_dump -Fd -j 4 -f /backup/buh.dir buh

# скопировать /backup на новый хост, затем на новом хосте
sudo -u postgres psql -f /backup/globals.sql postgres
sudo -u postgres pg_restore -C -d postgres -j 4 /backup/buh.dir
sudo -u postgres vacuumdb --all --analyze-in-stages
```

На новом хосте должна стоять сборка для 1С (расширения `mchar`, `fulleq`, `fasttrun`), а в ОС — сгенерирована локаль, в которой созданы базы (`ru_RU.UTF-8`, для конфигураций WE — `en_US.UTF-8`), иначе `pg_restore -C` не создаст базу. Если версия на новом хосте новее — используйте `pg_dump` новой версии (раздел 14.5).

### 16.5. Переключение 1С на новый сервер БД

```bash
# 1. Заблокировать работу (до начала чистового копирования)
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd='***' \
     --sessions-deny=on --scheduled-jobs-deny=on --permission-code=ADM
$RAC session list --cluster=$CL --infobase=$IB            # оставшиеся сеансы завершить: rac session terminate

# 2. На новом сервере СУБД: разрешить подключение сервера 1С
#    pg_hba.conf:  host  all  usr1cv8  192.168.1.20/32  scram-sha-256
sudo systemctl reload postgresql@17-main
psql "host=НОВЫЙ_ХОСТ port=5432 dbname=buh user=usr1cv8" -c "SELECT 1"     # проверка с сервера 1С

# 3. Сменить адрес сервера СУБД в свойствах каждой базы
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd='***' \
     --db-server='НОВЫЙ_ХОСТ'

# 4. Перезапустить службу сервера 1С (чтобы не осталось соединений со старым сервером) и снять блокировки
sudo systemctl restart 'srv1cv8*'
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=Администратор --infobase-pwd='***' \
     --sessions-deny=off --scheduled-jobs-deny=off
```

Если 1С изначально настроена на DNS-имя или виртуальный адрес, шаг 3 заменяется сменой записи DNS или переносом адреса. Пароль пользователя СУБД хранится в свойствах базы 1С; при физическом переносе роли и пароли приезжают вместе с кластером, при переносе дампом — с файлом `globals.sql`. После переноса: перенастроить резервное копирование и мониторинг на новый хост, старый сервер PostgreSQL остановить и отключить (`systemctl disable`), чтобы к нему никто не подключился по ошибке.

---

## Типичные ошибки и подводные камни (симптом → причина → решение)

Тексты сообщений PostgreSQL приведены по памяти составителя, если не отмечено [офиц.]; формулировки в вашей версии могут немного отличаться.

### Настройка репликации

| Симптом | Причина | Решение |
|---|---|---|
| `FATAL: no pg_hba.conf entry for replication connection from host "192.168.1.12", user "replicator"` | нет строки для псевдобазы `replication` (под `all` она не попадает) | добавить `host replication replicator адрес/32 scram-sha-256`, `systemctl reload` |
| `FATAL: password authentication failed for user "replicator"` при `pg_basebackup -w` или в журнале реплики | нет или неверна запись в `~/.pgpass` пользователя `postgres` (поле базы должно быть `replication`), права файла не `0600` | исправить `.pgpass`, `chmod 600` |
| `pg_basebackup: error: directory "…" exists but is not empty` | каталог данных не пуст | остановить сервер, убрать содержимое (переименовать каталог) |
| `FATAL: number of requested standby connections exceeds max_wal_senders` | все процессы `walsender` заняты (реплики + `pg_basebackup -X stream` берёт два) | увеличить `max_wal_senders`, перезапустить ведущий |
| `FATAL: database system identifier differs between the primary and standby` | реплика создана собственным `initdb`, а не копией ведущего | пересоздать реплику через `pg_basebackup` |
| `FATAL: could not start WAL streaming: ERROR: replication slot "pg2" does not exist` | в `primary_slot_name` указан несуществующий слот (например, после переключения на новый ведущий) | создать слот на источнике или убрать `primary_slot_name` |
| `ERROR: replication slot "pg2" is active for PID …` | две реплики используют один слот | каждой реплике — свой слот |
| Журнал реплики: `requested WAL segment … has already been removed` | реплика отстала сильнее, чем хранится WAL; слота нет | пересоздать реплику; использовать слот или `wal_keep_size`, либо архив WAL + `restore_command` |
| `WARNING: hot standby is not possible because of insufficient parameter settings` … `LOG: recovery has paused` [офиц.] | на реплике `max_connections` (или `max_locks_per_transaction`, `max_worker_processes`, `max_wal_senders`, `max_prepared_transactions`) меньше, чем на ведущем — типично для Debian-раскладки, где конфигурация реплики не копируется | выставить значения не меньше, чем на ведущем, перезапустить реплику; при увеличении — сначала реплики, потом ведущий |
| Реплика в `pg_stat_replication` называется `17/main` или `walreceiver`; `synchronous_standby_names` «не видит» её | не задан `application_name` в `primary_conninfo` | добавить `application_name=pg2`, `SELECT pg_reload_conf();` |
| Раздел с `pg_wal` на ведущем заполняется | неактивный слот (выключенная реплика, забытый `pg_basebackup -C`, остановленная копия базы 1С), сломанная архивация | `pg_replication_slots` → починить потребителя или `pg_drop_replication_slot`; задать `max_slot_wal_keep_size`; файлы из `pg_wal` вручную не удалять |
| `pg_wal` растёт на **реплике** | на реплике остался слот от времени, когда она была ведущей | удалить слот на реплике |

### Работа и переключение

| Симптом | Причина | Решение |
|---|---|---|
| 1С: ошибки вида `cannot execute CREATE TABLE in a read-only transaction` | 1С подключена к реплике: неверный адрес, прокси проверяет не `/primary`, виртуальный адрес остался на бывшем ведущем | исправить точку входа; проверить `SELECT pg_is_in_recovery();` по адресу, который указан в 1С |
| Запросы на реплике: `ERROR: canceling statement due to conflict with recovery` | применение WAL конфликтует с долгим запросом на реплике | увеличить `max_standby_streaming_delay` или включить `hot_standby_feedback` (ценой раздувания на ведущем) |
| Все записи в 1С «зависли», в `pg_stat_activity` ожидание `SyncRep` | недоступна единственная синхронная реплика | `ALTER SYSTEM SET synchronous_standby_names = ''; SELECT pg_reload_conf();`; на будущее — две реплики или управление через Patroni |
| После сбоя на обоих серверах `pg_is_in_recovery()` = `f` | split-brain: старый ведущий вернулся в строй ведущим | немедленно изолировать один из серверов; выбрать «правильную» ветку; второй перемотать `pg_rewind` или пересоздать; потерянные изменения переносить вручную |
| `pg_rewind: error: target server needs to use either data checksums or "wal_log_hints = on"` (префикс `error:` — с PostgreSQL 15, в 13–14 — `fatal:`) [офиц., исходный код] | кластер создан без контрольных сумм и без `wal_log_hints` | перемотка невозможна — пересоздать узел `pg_basebackup`; включить `wal_log_hints` на будущее |
| `pg_rewind` не находит WAL (`could not find previous WAL record`, `could not open file "…/pg_wal/…"`) | на целевом сервере нет WAL до точки расхождения | ключ `-c` с рабочим `restore_command` либо пересоздать узел |
| После `pg_rewind` в раскладке Postgres Pro сервер слушает не тот адрес или пускает не тех | `postgresql.conf` и `pg_hba.conf` заменены копиями с источника | проверить и поправить конфигурацию после перемотки |
| После переключения 1С: `could not access file "$libdir/mchar": No such file or directory`, `type "mvarchar" does not exist` | на новом ведущем стоит «ванильный» PostgreSQL или другая сборка (в том числе после `apt upgrade`) | установить ту же сборку для 1С на все узлы, `apt-mark hold` |
| Пользователи 1С после паузы получают ошибку СУБД, повтор проходит | прокси (HAProxy, межсетевой экран) рвёт простаивающие соединения | увеличить `timeout client` / `timeout server`; проверить таймауты межсетевого экрана |
| После аварийного переключения в базе нет последних документов | асинхронная репликация: хвост WAL не успел уйти | сверка и повторный ввод; для исключения — синхронный режим (и `synchronous_commit` не `off`) |

### Patroni, HAProxy, PgBouncer

| Симптом | Причина | Решение |
|---|---|---|
| Кластер Patroni работает с `max_connections = 100`, `max_locks_per_transaction = 64`, хотя в `patroni.yml` заданы другие значения | эти параметры принимаются только из динамической конфигурации (DCS) [офиц.] | `patronictl edit-config`, затем `patronictl restart … --pending` |
| Правки в `bootstrap.dcs` не действуют | секция применяется только при создании кластера [офиц.] | `patronictl edit-config` |
| Правка `postgresql.conf` вручную пропадает | файл генерирует Patroni | менять через Patroni (`edit-config` или `postgresql.parameters`) |
| PostgreSQL запущен дважды или «самопроизвольно» стартует бывший ведущий | не отключена собственная служба PostgreSQL | `systemctl disable --now postgresql@17-main` (или `postgrespro-1c-17`); запуском управляет только Patroni |
| Ведущий понижен при исправной СУБД; в журнале Patroni сообщения о недоступности DCS | потерян кворум etcd (упали 2 из 3 узлов, сеть) | восстановить etcd; `etcdctl endpoint health`; рассмотреть `failsafe_mode: true` |
| В статистике HAProxy все серверы DOWN | недоступен REST API Patroni (порт 8008 закрыт, Patroni остановлен), неверный URL проверки | `curl -i http://узел:8008/primary`; открыть порт; проверить `option httpchk` |
| В статистике HAProxy ведущий UP, реплики DOWN | так и должно быть: `/primary` отвечает 200 только на ведущем [офиц., ИТС 5971] | — |
| С PgBouncer: `relation "tt…" does not exist`, «пропадают» настройки сеанса, странные ошибки запросов | `pool_mode = transaction` (или `statement`) | `pool_mode = session` либо убрать PgBouncer |
| С PgBouncer соединения 1С ждут и отваливаются через 2 минуты | `default_pool_size = 20`, `max_client_conn = 100` по умолчанию | увеличить до числа соединений 1С |

### Обновление версий и ОС

| Симптом | Причина | Решение |
|---|---|---|
| `pg_upgrade --check`: `Your installation references loadable libraries that are missing from the new installation` (в списке `$libdir/mchar`, `fulleq`, `fasttrun`, `plantuner`) | новая версия — не сборка для 1С либо не установлен пакет с расширениями | установить сборку для 1С новой версии целиком |
| `pg_upgrade`: `old cluster does not use data checksums but the new one does` (или наоборот) | разный режим контрольных сумм (особенно при переходе на 18, где они включены по умолчанию) | пересоздать новый кластер с `--no-data-checksums` либо включить суммы в старом `pg_checksums --enable` |
| `pg_upgrade`: несовпадение кодировки или локали баз (`encodings … do not match`, `lc_collate values … do not match`) — только при обновлении **на версию 15 и старше**: с PostgreSQL 16 `pg_upgrade` сам задаёт новому кластеру локаль и кодировку старого, и этой проверки в нём нет [офиц., замечания к выпуску 16, исходный код 18] | новый кластер создан с другой локалью | `initdb` нового кластера с `--locale=ru_RU.UTF-8 --encoding=UTF8` (для WE — `en_US.UTF-8`; локаль должна быть сгенерирована в ОС) |
| `pg_upgrade`: `could not open log file` / нет прав на текущий каталог | запуск из каталога, недоступного пользователю `postgres` | `cd /tmp` (или домашний каталог `postgres`) перед запуском |
| `pg_upgrade --check` падает на слотах после обновлений 08.2026 | `output_plugin_libraries` нового кластера не разрешает модуль слотов старого [офиц.] | добавить модуль в `output_plugin_libraries` нового кластера |
| `pg_upgradecluster`: целевой кластер уже существует | пакет новой версии создал пустой `18/main` | `sudo pg_dropcluster --stop 18 main` (убедившись, что он пустой) и повторить |
| `pg_upgradecluster` работает часами | метод по умолчанию — `dump` | `-m upgrade` или `-m link` |
| После мажорного обновления запросы 1С резко замедлились | нет статистики планировщика | `vacuumdb --all --analyze-in-stages` (для 18 — с `--missing-stats-only`, затем `--analyze-only`) |
| После `pg_upgrade --link` старый кластер не запускается | так задумано: после запуска нового кластера старый использовать нельзя | откат только из резервной копии; если новый ещё не запускался — убрать суффикс `.old` у `global/pg_control` |
| После минорного обновления (выпуски от 08.2026) перестали обновляться копии базы данных 1С | модуль логического декодирования не входит в `output_plugin_libraries` ⚠; в журнале PostgreSQL при этом `library "…" may not be used as an output plugin` [офиц.] | добавить модуль 1С в параметр, перечитать конфигурацию |
| `WARNING: database "…" has a collation version mismatch` после обновления ОС | изменилась версия glibc или ICU | `REINDEX` всех баз, затем `ALTER DATABASE … REFRESH COLLATION VERSION` |
| После обновления ОС поиск по индексу не находит существующие строки, появляются дубликаты в уникальных индексах | индексы построены по старым правилам сортировки | немедленная полная переиндексация; дубликаты разбирать вручную |
| После `apt upgrade` / `do-release-upgrade` PostgreSQL «стал другим» | пакеты сборки от 1С заменены дистрибутивными | вернуть сборку для 1С; `apt-mark hold` |
| После мажорного обновления не восстанавливается старая физическая копия | физические копии привязаны к мажорной версии | сразу после обновления сделать новую полную копию |

### Концептуальные ошибки

- **«У нас реплика, резервные копии не нужны».** Реплика повторяет и ошибочные действия. Нужны копии + архив WAL + проверка восстановления.
- **Реплика на том же диске или в той же ВМ** — защищает только от сбоя процесса, но не от потери ВМ, диска, хоста.
- **Автоматический failover на двух узлах без третьего голоса** — гарантированный split-brain при обрыве связи.
- **Синхронная репликация при `synchronous_commit = off`** — гарантий нет.
- **Реплика «для отчётов 1С»** — 1С не может читать с физической реплики; используйте механизм копий базы данных.
- **Ни разу не проверенное переключение** — в аварии выяснится, что реплика давно отстала, слота нет, пароль в `.pgpass` устарел.
- **Разные версии сборки и ОС на узлах** — проблемы всплывают только после переключения.

---

## Быстрая шпаргалка — «задача → команда»

| Задача | Команда |
|---|---|
| Роль для репликации | `CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '…';` |
| Разрешить репликацию | `pg_hba.conf`: `host replication replicator 192.168.1.12/32 scram-sha-256` → `systemctl reload` |
| Создать реплику | `sudo -u postgres pg_basebackup -h pg1 -U replicator -D PGDATA -X stream -C -S pg2 -R -c fast -P` |
| Сервер — ведущий или реплика? | `SELECT pg_is_in_recovery();` (`f` — ведущий) |
| Реплики и отставание (на ведущем) | `SELECT application_name, state, sync_state, replay_lag, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) FROM pg_stat_replication;` |
| Состояние приёма (на реплике) | `SELECT status, sender_host, slot_name, flushed_lsn FROM pg_stat_wal_receiver;` |
| Позиции на реплике | `SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(), pg_last_xact_replay_timestamp();` |
| Создать / удалить слот | `SELECT pg_create_physical_replication_slot('pg2');` / `SELECT pg_drop_replication_slot('pg2');` |
| Слоты и удерживаемый WAL | `SELECT slot_name, active, wal_status, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) FROM pg_replication_slots;` |
| Ограничить WAL для слотов | `ALTER SYSTEM SET max_slot_wal_keep_size = '20GB'; SELECT pg_reload_conf();` |
| Включить синхронную репликацию | `ALTER SYSTEM SET synchronous_standby_names = 'FIRST 1 (pg2, pg3)'; SELECT pg_reload_conf();` + `synchronous_commit = on` |
| Срочно отключить синхронность | `ALTER SYSTEM SET synchronous_standby_names = ''; SELECT pg_reload_conf();` |
| Сменить источник репликации | `ALTER SYSTEM SET primary_conninfo = 'host=… user=replicator application_name=pg1'; SELECT pg_reload_conf();` |
| Пауза / продолжение применения WAL | `SELECT pg_wal_replay_pause();` / `SELECT pg_wal_replay_resume();` |
| Повысить реплику | `sudo pg_ctlcluster 17 main promote` · `pg_ctl promote -D PGDATA` · `SELECT pg_promote();` |
| Состояние остановленного кластера | `sudo -u postgres env LANG=C pg_controldata PGDATA \| grep -E 'state\|checkpoint location\|TimeLineID'` |
| Вернуть старый ведущий | `pg_rewind --target-pgdata=PGDATA --source-server='host=новый user=rewind_user dbname=postgres' -R -P` (сначала `--dry-run`) |
| Сделать сервер репликой вручную | `touch PGDATA/standby.signal` + `primary_conninfo` → запуск |
| Patroni: состояние | `patronictl -c /etc/patroni/config.yml list` · `topology` · `history` |
| Patroni: плановое переключение | `patronictl switchover КЛАСТЕР --leader pg1 --candidate pg2` |
| Patroni: аварийное переключение | `patronictl failover КЛАСТЕР --candidate pg2` |
| Patroni: параметры PostgreSQL | `patronictl edit-config КЛАСТЕР -p 'параметр=значение'` → `patronictl restart КЛАСТЕР --pending` |
| Patroni: режим обслуживания | `patronictl pause КЛАСТЕР` / `patronictl resume КЛАСТЕР` |
| Patroni: пересоздать реплику | `patronictl reinit КЛАСТЕР pg3` |
| Patroni: кто ведущий (HTTP) | `curl -s -o /dev/null -w "%{http_code}\n" http://узел:8008/primary` |
| etcd: здоровье | `etcdctl --endpoints=… endpoint health` · `etcdctl endpoint status -w table` · `etcdctl member list -w table` |
| HAProxy: проверка конфигурации | `sudo haproxy -c -f /etc/haproxy/haproxy.cfg` |
| 1С: текущий сервер СУБД базы | `rac infobase info --cluster=$CL --infobase=$IB --infobase-user=… --infobase-pwd=… \| grep db-server` |
| 1С: сменить сервер СУБД | `rac infobase update --cluster=$CL --infobase=$IB --infobase-user=… --infobase-pwd=… --db-server='адрес port=5432;'` |
| 1С: блокировка на время работ | `rac infobase update … --sessions-deny=on --scheduled-jobs-deny=on --permission-code=ADM` |
| Минорное обновление | обновить пакеты сборки → `systemctl restart postgresql@17-main` → `SELECT version();` |
| Проверка перед мажорным обновлением | `pg_upgrade -b старый_bin -B новый_bin -d старый_PGDATA -D новый_PGDATA --check` |
| Мажорное обновление (Debian-раскладка) | `sudo pg_dropcluster --stop 18 main && sudo pg_upgradecluster -m upgrade -v 18 17 main` |
| Статистика после обновления | `vacuumdb --all --analyze-in-stages` (для 18: `--missing-stats-only`, затем `vacuumdb --all --analyze-only`) |
| Версии правил сортировки | `SELECT datname, datcollversion, pg_database_collation_actual_version(oid) FROM pg_database;` |
| Исправить после обновления ОС | `reindexdb --all` → `ALTER DATABASE имя REFRESH COLLATION VERSION;` |
| Белый список модулей декодирования | `SHOW output_plugin_libraries;` |
| Перенос базы дампом | `pg_dumpall --globals-only`; `pg_dump -Fd -j 4 -f каталог база`; `pg_restore -C -d postgres -j 4 каталог` |

---

## Источники

Документация PostgreSQL 18 (актуальная на 10.10.2026 и на 19.10.2026 версия 18.6; PostgreSQL 19 на 10.10.2026 — Beta 4, на 19.10.2026 — RC 1 от 15.10.2026):

- https://www.postgresql.org/support/versioning/ — поддерживаемые версии, текущие минорные выпуски, даты окончания поддержки.
- https://www.postgresql.org/docs/current/warm-standby.html — требования к ведущему и резервному серверам, настройка резервного сервера (`standby.signal`, `primary_conninfo`), слоты, каскадная и синхронная репликация, порядок минорного обновления реплик.
- https://www.postgresql.org/docs/current/warm-standby-failover.html — failover, STONITH, «вырожденное состояние», `pg_ctl promote` / `pg_promote()`, упоминание `pg_rewind`.
- https://www.postgresql.org/docs/current/hot-standby.html — что разрешено на резервном сервере (запрет временных таблиц), конфликты восстановления, параметры, которые должны быть не меньше, чем на ведущем, текст предупреждения.
- https://www.postgresql.org/docs/current/runtime-config-replication.html — параметры репликации и значения по умолчанию, синтаксис `synchronous_standby_names`, `output_plugin_libraries`.
- https://www.postgresql.org/docs/current/runtime-config-wal.html — `wal_level`, `synchronous_commit`, `wal_log_hints`, `full_page_writes`, `recovery_target_timeline`.
- https://www.postgresql.org/docs/current/app-pgbasebackup.html — ключи `pg_basebackup`, копирование с резервного сервера.
- https://www.postgresql.org/docs/current/app-pgrewind.html — требования, ключи, права роли, предупреждения `pg_rewind`.
- https://www.postgresql.org/docs/current/monitoring-stats.html — `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_stat_subscription`, `pg_stat_database_conflicts`.
- https://www.postgresql.org/docs/current/view-pg-replication-slots.html — столбцы `pg_replication_slots`, значения `wal_status` и `invalidation_reason`.
- https://www.postgresql.org/docs/current/functions-admin.html — `pg_promote`, функции управления восстановлением и слотами, `pg_wal_lsn_diff`.
- https://www.postgresql.org/docs/current/libpq-connect.html — несколько хостов в строке подключения, `target_session_attrs`, `connect_timeout`.
- https://www.postgresql.org/docs/current/upgrading.html — политика минорных и мажорных обновлений, три способа мажорного обновления.
- https://www.postgresql.org/docs/current/pgupgrade.html — ключи и порядок действий `pg_upgrade`, расширения, статистика в версии 18, `rsync` для реплик, откат.
- https://www.postgresql.org/docs/current/logical-replication-restrictions.html — ограничения логической репликации.
- https://www.postgresql.org/docs/current/logical-replication-upgrade.html — обновление кластеров логической репликации, перенос слотов с версии 17.
- https://www.postgresql.org/docs/current/app-pgcreatesubscriber.html — `pg_createsubscriber`.
- https://www.postgresql.org/docs/current/sql-altercollation.html, https://www.postgresql.org/docs/current/sql-alterdatabase.html — `REFRESH VERSION`, `REFRESH COLLATION VERSION`, текст предупреждения, запрос зависимых объектов.
- https://www.postgresql.org/docs/release/18.6/, https://www.postgresql.org/docs/release/17.11/, https://www.postgresql.org/docs/release/14.24/ — выпуски от 13.08.2026: параметр `output_plugin_libraries` (CVE-2026-6471), действия после обновления, окончание поддержки ветки 14.
- https://wiki.postgresql.org/wiki/Locale_data_changes — изменение правил сортировки glibc 2.28, затронутые дистрибутивы, проверка `sort`, что подвержено и что нет.

Ubuntu:

- https://manpages.ubuntu.com/manpages/noble/en/man1/pg_upgradecluster.1.html — ключи, поведение по умолчанию, сценарии-перехватчики (postgresql-common 257).
- https://manpages.ubuntu.com/manpages/noble/en/man1/pg_ctlcluster.1.html — действие `promote`, ключи, интеграция с systemd.
- https://packages.ubuntu.com/ (поиск пакетов `libc6`, `patroni`, `etcd-server`, `pgbouncer`, `vip-manager`) — версии пакетов в 22.04 / 24.04 / 26.04.

Patroni и окружение:

- https://patroni.readthedocs.io/en/latest/patronictl.html — команды `patronictl`, отличие `switchover` от `failover`, файл настроек.
- https://patroni.readthedocs.io/en/latest/dynamic_configuration.html — динамические параметры и значения по умолчанию.
- https://patroni.readthedocs.io/en/latest/patroni_configuration.html — виды конфигурации, параметры, принимаемые только из DCS, работа с `postgresql.base.conf`.
- https://patroni.readthedocs.io/en/latest/yaml_configuration.html — структура YAML-файла, теги, watchdog.
- https://patroni.readthedocs.io/en/latest/replication_modes.html — асинхронный и синхронный режимы, `synchronous_mode_strict`, кворум.
- https://patroni.readthedocs.io/en/latest/rest_api.html — проверки состояния и управляющие запросы REST API.
- https://patroni.readthedocs.io/en/latest/existing_data.html — перевод существующего кластера под Patroni, мажорное обновление.
- https://patroni.readthedocs.io/en/latest/releases.html — версия 4.1.5 от 12.08.2026 и предыдущие.
- https://raw.githubusercontent.com/patroni/patroni/master/haproxy.cfg — образец конфигурации HAProxy.
- https://github.com/cybertec-postgresql/vip-manager — параметры vip-manager.
- https://www.repmgr.org/docs/current/index.html — repmgr 5.5.0, команды.
- https://pg-auto-failover.readthedocs.io/en/main/intro.html — архитектура pg_auto_failover.
- https://www.pgbouncer.org/features.html, https://www.pgbouncer.org/config.html — режимы пула, таблица совместимости, параметры и значения по умолчанию.

Postgres Professional:

- https://postgrespro.ru/docs/enterprise/17/biha-solution, https://postgrespro.ru/docs/enterprise/17/biha-architecture, https://postgrespro.ru/docs/enterprise/17/biha-administration — BiHA: состав, рефери, кворум, переключение, обновление.
- https://postgrespro.ru/docs/enterprise/17/multimaster — multimaster, ограничение «Решения 1С не поддерживаются».
- https://postgrespro.ru/docs/enterprise/17/proxima — proxima: порты, динамический выделенный сеанс, ограничения.
- https://postgrespro.ru/docs/enterprise/16/connection-pooling — встроенный пул соединений объявлен устаревшим.
- https://postgrespro.ru/docs/postgrespro/17/one-c-configuring-server (и соседние разделы приложения K) — рекомендуемые параметры для 1С, в том числе `synchronous_commit = off`, `max_connections`.
- https://postgrespro.ru/docs/postgrespro/17/upgrading, https://postgrespro.ru/docs/postgrespro/17/mchar, https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux — обновление Postgres Pro, модуль `mchar` (ICU), установка без метапакета при обновлении.

Фирма «1С»:

- https://its.1c.ru/db/metod8dev/content/5971/hdoc — «Построение отказоустойчивого кластера PostgreSQL. Настройка внешней синхронизации на PostgreSQL для механизма копий баз данных» (06.04.2020); использован конспект `kb/its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md` (сама страница закрыта подпиской).
- https://v8.1c.ru/platforma/kopii-baz-dannykh/, https://v8.1c.ru/platforma/data-akselerator/, https://v8.1c.ru/platforma/masshtabiruemost-i-proizvoditelnost/ — назначение механизма копий базы данных и Дата акселератора.
- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/spisok-podderzhivaemykh-subd/ — список поддерживаемых СУБД и протестированных версий.
- Документация платформы (руководство администратора, клиент-серверный вариант) — по конспектам `kb/its-docs/`: формат поля «Сервер баз данных», лицензионные требования КОРП, фоновые задания и события технологического журнала механизма копий, параметры `rac infobase update`.

Дополнительно при независимой сверке 19.10.2026:

- Локальные текстовые копии документации PostgreSQL 18 (сняты 10–11.10.2026): `app-pgbasebackup`, `app-pgrewind`, `app-pgcreatesubscriber`, `pgupgrade`, `warm-standby`, `hot-standby`, `runtime-config-replication`, `runtime-config-wal`, `monitoring-stats`, `view-pg-replication-slots`, `functions-admin`, `libpq-connect`, `auth-pg-hba-conf`, `sql-altercollation`, `sql-alterdatabase`, замечания к выпускам 13–18, образец `postgresql.conf` версии 18.
- https://www.postgresql.org/docs/release/18.6/, …/17.11/, …/16.15/, …/14.24/ — `output_plugin_libraries` во всех ветках, `pg_upgrade --check`, 18.5 не выпускался; https://www.postgresql.org/support/versioning/ (на 19.10.2026); https://www.postgresql.org/ (PostgreSQL 19 RC 1 от 15.10.2026); https://www.postgresql.org/docs/18/warm-standby-failover.html, https://www.postgresql.org/docs/18/server-shutdown.html, https://www.postgresql.org/docs/18/logical-replication-restrictions.html.
- Исходный код PostgreSQL (`raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/…`): `src/bin/pg_rewind/pg_rewind.c` и `parsexlog.c` (тексты сообщений), `src/bin/pg_upgrade/check.c` и `controldata.c` (проверки, нет проверки локали), `src/backend/utils/init/postinit.c` (предупреждение о версии правил сортировки; также REL_16_STABLE), `src/include/common/logging.h` (REL_14/15/18 — префикс `fatal:`/`error:`), `REL_14_STABLE/src/interfaces/libpq/fe-connect.c` и `fe-misc.c` (тексты ошибок соединения).
- Patroni: `raw.githubusercontent.com/patroni/patroni/master/docs/*.rst` (`releases`, `patroni_configuration`, `dynamic_configuration`, `yaml_configuration`, `rest_api`, `replication_modes`, `existing_data`, `patronictl`), `haproxy.cfg`; https://pypi.org/pypi/patroni/json — 4.1.5 от 12.08.2026 последняя на 19.10.2026.
- https://www.repmgr.org/docs/current/install-requirements.html — матрица совместимости repmgr; `raw.githubusercontent.com/hapostgres/pg_auto_failover/main/` — `README.md`, `CHANGELOG.md`, `docs/ref/pg_autoctl_create_monitor.rst`, `pg_autoctl_create_postgres.rst`; `raw.githubusercontent.com/cybertec-postgresql/vip-manager/master/README.md`; https://www.pgbouncer.org/features.html, https://www.pgbouncer.org/config.html.
- https://packages.ubuntu.com/ — `patroni`, `etcd-server`, `etcd-client`, `vip-manager`, `vip-manager2`, `pgbouncer`, `haproxy`, `keepalived`, `libc6`, `libicu70/74/78` (на 19.10.2026); список файлов `etcd-server` (noble).
- Postgres Professional: https://postgrespro.ru/docs/enterprise/17/biha-architecture, …/biha-administration, …/proxima, …/multimaster, https://postgrespro.ru/docs/enterprise/16/connection-pooling; документация «PostgreSQL для 1С» 16 (`repo.postgrespro.ru/doc/pg1c/16/ru/html/`: `release.html`, `pg-setup`, `binary-installation-on-linux`, приложение K.3, F.14 `dbcopies_decoding`, F.29 `mchar`); индексы `Packages` репозиториев `repo.postgrespro.ru/1c/1c-14…18/ubuntu/dists/noble/` (на 19.10.2026); сценарии `postinst` и `pg-setup` из пакета `postgrespro-1c-16-server` 16.14-1.noble (разобран 11.10.2026 с согласия пользователя, см. `kb/guides/07-…`).
- Фирма «1С»: список поддерживаемых СУБД на v8.1c.ru (на 19.10.2026); конспекты `kb/its-docs/dev-gl26-kopii-bazy-dannyh.md` (гл. 26 «Руководства разработчика» 8.3.27), `adm-gl01-trebovaniya.md`, `cs-gl01-trebovaniya.md`, `cs-gl03-ustanovka-komponentov-p1.md`, `cs-gl02-klient-servernyj-variant-p2.md`, `adm-pr03-sluzhebnye-fajly-p3/p4.md`, `adm-pr07-parametry-zapuska-1cv8-p3.md`, `adm-gl05-spisok-infobaz.md`, `adm-pr04-komandnye-stroki-utilit-p3.md`; `kb/its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md`, `pg-rasshireniya-1c-i-metodika-rassledovaniya.md`.

Статьи этой базы знаний, на которые есть ссылки: `kb/postgresql/01` (сборки, совместимость версий, установка), `02` (параметры), `04` (резервное копирование), `05` (обслуживание, `REINDEX`), `kb/1c/03` (rac), `kb/1c/06` (ibcmd), `kb/1c/10` (отказоустойчивость кластера 1С).

