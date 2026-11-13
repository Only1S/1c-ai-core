# Шпаргалка на каждый день и аварийные инструкции: сервер 1С + PostgreSQL на Ubuntu

> Область: одна ВМ с сервером 1С 8.3.27 и «PostgreSQL для 1С» 17 (Postgres Professional), развёрнутая по `01-razvertyvanie-s-nulya.md` | Актуальность: 2026-10-10
>
> **Статус:** собрано из конспектов документации ИТС и статей базы знаний; на живом сервере инструкции целиком не прогонялись. Параметры `rac` в документации ИТС не перечислены — при сомнении сверяйтесь со встроенной справкой `rac help <режим>`. Для сборки PostgreSQL от фирмы «1С» имя службы — `postgresql@17-main`, каталог данных — `/var/lib/postgresql/17/main`.

## Переменные

```bash
V=8.3.27.2074                                  # версия платформы на сервере
RAC=/opt/1cv8/x86_64/$V/rac
SRV=srv1cv8-$V@default                         # служба сервера 1С
PGSVC=postgrespro-1c-17                        # служба PostgreSQL
DATA=/home/usr1cv8/.1cv8/1C/1cv8               # каталог данных кластера 1С
PGDATA=/var/lib/pgpro/1c-17/data
CL=$($RAC cluster list | awk '/^cluster/{print $3}')     # UUID кластера
```

UUID базы: `$RAC infobase summary list --cluster=$CL` (поле `infobase`). Если в кластере заданы администраторы — ко всем командам добавляются `--cluster-user=… --cluster-pwd=…`.

## A. Шпаргалка «задача → команда»

### Службы и процессы

| Задача | Команда |
|---|---|
| Состояние сервера 1С | `systemctl status $SRV --no-pager` |
| Состояние PostgreSQL | `systemctl status $PGSVC --no-pager` |
| Процессы кластера | `ps aux \| grep -E '[r]agent\|[r]mngr\|[r]phost'` |
| Слушающие порты 1С | `sudo ss -tlnp \| grep -E 'ragent\|rmngr\|rphost\|ras'` |
| Слушает ли PostgreSQL | `sudo ss -tlnp \| grep 5432`; `sudo -u postgres pg_isready` |
| Журнал сервера 1С | `journalctl -u $SRV -e --no-pager` |
| Журнал PostgreSQL | `journalctl -u $PGSVC -e --no-pager`; файлы в `$PGDATA/log/` |
| Что не запустилось | `systemctl --failed` |
| Автозапуск включён? | `systemctl is-enabled $SRV $PGSVC ras-$V` |

### Кластер 1С (rac)

| Задача | Команда |
|---|---|
| Кластеры | `$RAC cluster list` |
| Базы | `$RAC infobase summary list --cluster=$CL` |
| Сеансы | `$RAC session list --cluster=$CL` |
| Сеансы одной базы | `$RAC session list --cluster=$CL --infobase=$IB` |
| Завершить сеанс | `$RAC session terminate --cluster=$CL --session=<UUID сеанса>` |
| Соединения | `$RAC connection list --cluster=$CL` |
| Рабочие процессы и их память | `$RAC process list --cluster=$CL` |
| Рабочие серверы | `$RAC server list --cluster=$CL` |
| Управляемые блокировки | `$RAC lock list --cluster=$CL` |
| Выданные лицензии | `$RAC session list --cluster=$CL --licenses` |
| Справка по режиму | `$RAC help infobase` |

### Ресурсы

| Задача | Команда |
|---|---|
| Память | `free -h` |
| Нагрузка, первые 60 секунд | `uptime; vmstat 1 5; iostat -xz 1 3` |
| Кто ест память | `ps aux --sort=-rss \| head -15` |
| Кто ест CPU | `top -b -n 1 \| head -20` |
| Кто пишет на диск | `sudo iotop -o -b -n 3` |
| Место на дисках | `df -h; df -i` |
| Что заняло место | `sudo du -xh --max-depth=1 /var \| sort -h \| tail` |
| Убивал ли OOM killer | `journalctl -k --since "2 days ago" \| grep -i -E 'out of memory\|killed process'` |

### PostgreSQL

| Задача | Команда (`sudo -u postgres psql -c "…"`) |
|---|---|
| Активные запросы | `select pid, state, wait_event_type, now()-query_start as dur, left(query,80) from pg_stat_activity where state <> 'idle' order by query_start` |
| Долгие транзакции | `select pid, now()-xact_start as age, state, left(query,60) from pg_stat_activity where xact_start is not null order by xact_start limit 10` |
| Кто кого блокирует | `select pid, pg_blocking_pids(pid) as blocked_by, left(query,60) from pg_stat_activity where cardinality(pg_blocking_pids(pid)) > 0` |
| Число соединений | `select count(*), state from pg_stat_activity group by state` |
| Размеры баз | `select datname, pg_size_pretty(pg_database_size(datname)) from pg_database order by pg_database_size(datname) desc` |
| Крупнейшие таблицы | `select relname, pg_size_pretty(pg_total_relation_size(oid)) from pg_class where relkind='r' order by pg_total_relation_size(oid) desc limit 15` |
| Отменить запрос | `select pg_cancel_backend(<pid>)` |
| Завершить соединение | `select pg_terminate_backend(<pid>)` |
| Перечитать конфигурацию | `select pg_reload_conf()` |
| Параметры, ждущие перезапуска | `select name, setting from pg_settings where pending_restart` |
| Размер WAL | `sudo du -sh $PGDATA/pg_wal` |
| Слоты репликации | `select slot_name, active, wal_status from pg_replication_slots` |

### Копии, пакеты, сеть

| Задача | Команда |
|---|---|
| Когда был последний бэкап | `ls -lht /backup/pg \| head -5`; `systemctl list-timers pg-backup.timer` |
| Запустить бэкап сейчас | `sudo systemctl start pg-backup.service` |
| Результат последнего бэкапа | `journalctl -u pg-backup.service -e --no-pager` |
| Доступен ли порт с сервера | `nc -zv <хост> <порт>` |
| Разрешение имени | `getent hosts <имя>` |
| Правила сетевого экрана | `sudo ufw status numbered` |
| Зафиксированные пакеты | `apt-mark showhold` |
| Нужна ли перезагрузка | `ls /var/run/reboot-required 2>/dev/null` |

## B. Аварийные и регламентные инструкции

### 1. Пользователи не могут подключиться («Сервер не обнаружен», тайм-аут)

1. На сервере: `systemctl is-active $SRV $PGSVC`; `sudo ss -tlnp | grep -E ':(1540|1541|156[0-9]|15[7-9][0-9])\b'`.
2. Имя сервера: `hostname -f`; `getent hosts $(hostname)` — должен быть реальный адрес, не `127.0.1.1`. Клиент получает от кластера **имя** рабочего сервера и должен уметь его разрешить.
3. На клиенте Windows: `Test-NetConnection srv1c -Port 1541` и `-Port 1560`. Нет ответа — сетевой экран (`sudo ufw status`) или маршрут.
4. Версия клиента должна совпадать с версией сервера.
5. Подключается, но база не открывается — см. инструкцию 4.

Подробнее: `../linux/08-set-ssh-firewall.md`, `../1c/02-ustanovka-servera-ubuntu.md`.

### 2. Сервер 1С не запускается

1. `systemctl status $SRV --no-pager`; `journalctl -u $SRV -b --no-pager | tail -80`.
2. Типовые причины:
   - **Юнит не найден после обновления платформы** — имя службы содержит версию. Зарегистрируйте юнит новой версии: `sudo systemctl link /opt/1cv8/x86_64/$V/srv1cv8-$V@.service`.
   - **Порты заняты** — `sudo ss -tlnp | grep -E '154[01]|156'`; остались процессы прежнего запуска: `ps aux | grep -E '[r]agent|[r]mngr|[r]phost'`.
   - **Права на каталог данных** — `sudo find $DATA ! -user usr1cv8 -ls | head`; исправление: `sudo chown -R usr1cv8:grp1cv8 /home/usr1cv8/.1cv8`.
   - **Нет места на диске** — `df -h` (инструкция 6).
   - **Не хватает библиотек** — `ldd /opt/1cv8/x86_64/$V/ragent | grep "not found"`.
3. Проверка: `ps aux | grep -E '[r]agent|[r]mngr|[r]phost'` — три процесса; `$RAC cluster list` отвечает.

### 3. «Не обнаружена лицензия»

1. На клиенте в окне ошибки нажать «Подробно» — журнал поиска покажет, где искали и почему отказ.
2. На сервере: `sudo ls -l /var/1C/licenses/`; `id usr1cv8` — пользователь должен входить в `grp1cv8` и иметь доступ к файлам.
3. Не менялось ли в ВМ: имя хоста, MAC-адрес или сам сетевой адаптер, диски, число процессоров, объём памяти в меньшую сторону. Добавление памяти и адаптеров привязку не ломает, удаление и замена — ломают. Параметры опрашиваются не чаще раза в сутки, поэтому отказ может проявиться не сразу.
4. Нет ли одного файла лицензии в нескольких каталогах поиска (`/opt/1cv8/x86_64/$V/conf`, `/opt/1cv8/conf`, `~usr1cv8/.1cv8/conf`, `/var/1C/licenses`).
5. Привязка нарушена — повторная активация **резервным** пин-кодом. Перед ней уберите старый файл `*.lic` из каталогов поиска: иначе и новая, и старая лицензии попадут в чёрный список.
6. Разрешено ли базе получать лицензии с сервера: свойство `license-distribution` в `$RAC infobase info --cluster=$CL --infobase=$IB`.

Подробнее: `../its-docs/adm-gl10-zashchita-licenzii-p1.md`, `../its-docs/adm-gl10-zashchita-licenzii-p2.md`, `../1c/04-licenzirovanie.md`.

### 4. 1С не подключается к PostgreSQL

1. `systemctl is-active $PGSVC`; `sudo -u postgres pg_isready`.
2. Проверить подключение так, как это делает сервер 1С, — по TCP и с паролем: `psql -h localhost -U postgres -d postgres -c "select 1"`.
3. По тексту ошибки:
   - `password authentication failed` — неверный пароль в свойствах базы; сменить: `$RAC infobase update --cluster=$CL --infobase=$IB --db-pwd=…`.
   - `no pg_hba.conf entry for host` — нет строки для адреса сервера 1С в `pg_hba.conf`; после правки `select pg_reload_conf()`.
   - `too many clients already` — исчерпан `max_connections`; смотреть, кто держит соединения (раздел A).
   - `connection to server at "…" (…), port … failed` (libpq 14+, платформа 8.3.20 и новее) или `could not connect to server` (старые libpq) — PostgreSQL не запущен или слушает другой адрес: `show listen_addresses`.
4. Журнал: `journalctl -u $PGSVC -e`, файлы в `$PGDATA/log/`.

Подробнее: `../postgresql/08-tipovye-problemy-1c-postgresql.md` (не проходила независимую проверку).

### 5. «1С тормозит»: локализация

Идти сверху вниз и не менять настройки, пока не найдено узкое место.

1. **Весь сервер или одна операция?** Одна операция у одного пользователя — это запрос или блокировка (шаги 5–6). Всё и у всех — ресурсы (шаги 2–4).
2. **CPU:** `uptime` (нагрузка против числа ядер), `top` — кто занят: `rphost` или `postgres`.
3. **Память:** `free -h` — колонка `available`, используется ли swap; `ps aux --sort=-rss | head`.
4. **Диск:** `iostat -xz 1 5` — `%util` около 100 и большой `await` указывают на диск; `sudo iotop -o`.
5. **PostgreSQL:** долгие запросы и транзакции, ожидания блокировок (раздел A). Состояние `idle in transaction` на минуты — зависшая транзакция, она же мешает очистке.
6. **1С:** `$RAC session list --cluster=$CL` — поля `blocked-by-dbms`, `blocked-by-ls`, `duration-current`, `memory-current`; `$RAC lock list --cluster=$CL`.
7. **Статистика устарела после массовой загрузки** — `sudo -u postgres vacuumdb -d <база> --analyze-only -j 4`.
8. Для разбора конкретной операции — технологический журнал с событиями `CALL` и `DBPOSTGRS`: `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`, методика ИТС — `../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`.

### 6. Закончилось место на диске

1. Что заполнено: `df -h; df -i`. Чем: `sudo du -xh --max-depth=2 /var /home /backup 2>/dev/null | sort -h | tail -20`.
2. Обычные виновники и безопасные действия:
   - **Технологический журнал 1С** — уменьшить `history` в `logcfg.xml` или убрать лишние события; старые каталоги журнала можно удалить.
   - **Системный журнал** — `sudo journalctl --vacuum-size=500M`.
   - **Кэш пакетов** — `sudo apt clean`.
   - **Старые копии** в `/backup` — удалять осознанно, оставив последнюю проверенную.
   - **Каталог `pg_wal`** — см. ниже.
3. ⚠ **Файлы в `pg_wal` вручную не удалять** — это разрушит базу. Найти причину роста: неактивный слот репликации (`select slot_name, active from pg_replication_slots`), неработающая архивация (`select * from pg_stat_archiver`), долгая транзакция.
4. **PostgreSQL уже не стартует из-за нехватки места:** освободить место чем угодно другим (журналы, копии, кэш пакетов) либо расширить диск ВМ (`../linux/07-diski-fs-lvm.md`), затем `sudo systemctl start $PGSVC`. Не использовать `pg_resetwal` — он ведёт к потере данных.
5. Проверка: `df -h` — свободно не меньше 15–20 %; службы активны.

### 7. Зависшие сеансы; блокировка входа на время работ

```bash
IB=<UUID базы>
# запретить вход и регламентные задания
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=<админ ИБ> --infobase-pwd=<пароль> \
    --sessions-deny=on --denied-message="Регламентные работы" --permission-code=svc2026 --scheduled-jobs-deny=on

# завершить сеансы базы
for S in $($RAC session list --cluster=$CL --infobase=$IB | awk '/^session /{print $3}'); do
  $RAC session terminate --cluster=$CL --session=$S
done
$RAC session list --cluster=$CL --infobase=$IB        # должно быть пусто

# ...работы... затем снять запрет
$RAC infobase update --cluster=$CL --infobase=$IB --infobase-user=<админ ИБ> --infobase-pwd=<пароль> \
    --sessions-deny=off --scheduled-jobs-deny=off
```

- При установленном запрете войти можно с кодом разрешения: параметр запуска `/UC svc2026`.
- Сеанс, занятый запросом к PostgreSQL, из кластера не разрывается — запрос снимают на стороне СУБД: `select pg_cancel_backend(<pid>)`.
- Не забудьте снять запрет: иначе пользователи не войдут и после окончания работ.

### 8. `rphost` съел память или падает; OOM killer убил `postgres`

1. `journalctl -k --since "1 day ago" | grep -i -E 'out of memory|killed process'` — кого убило ядро.
2. `$RAC process list --cluster=$CL` — память рабочих процессов; `ps aux --sort=-rss | head`.
3. Для 1С: пороги памяти задаются в свойствах рабочего сервера («Временно допустимый объём памяти процессов», «Критический объём памяти процессов») — при превышении кластер сам перезапускает процесс. Описание — `../its-docs/cs-gl05-administrirovanie-klastera-p1.md`.
4. Для PostgreSQL: проверить `shared_buffers + work_mem × соединения` против объёма памяти; уменьшить `work_mem`. После гибели процесса `postgres` сервер СУБД перезапускается и выполняет восстановление — дождаться, проверить `pg_isready`.
5. Падения `rphost` с дампом — `../its-metod/linux-ustanovka-platformy-dampy-kriptopro.md`, `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.
6. Если памяти ВМ объективно мало — увеличить её (увеличение привязку лицензии не ломает).

### 9. Восстановление базы из копии

**В отдельную базу (безопасно; так же проверяются копии):**

```bash
F=/backup/pg/demo_2026-10-10_0130.dump
sudo -u postgres createdb demo_copy
sudo -u postgres pg_restore -d demo_copy -j 4 "$F"
read -rsp "Пароль postgres в СУБД: " PGPWD; echo
$RAC infobase create --cluster=$CL --name=demo_copy --dbms=PostgreSQL --db-server=localhost \
    --db-name=demo_copy --locale=ru_RU --db-user=postgres --db-pwd="$PGPWD" \
    --license-distribution=allow --scheduled-jobs-deny=on
```

Регламентные задания в копии оставляйте запрещёнными: иначе копия начнёт рассылать почту и выполнять обмены как рабочая база.

**Поверх рабочей базы (разрушающее действие):**

1. Запретить вход и завершить сеансы (инструкция 7).
2. Сохранить текущее состояние: `sudo -u postgres pg_dump -Fc -f /backup/pg/demo_before_restore.dump demo`.
3. `sudo -u postgres dropdb demo && sudo -u postgres createdb demo && sudo -u postgres pg_restore -d demo -j 4 "$F"`.
4. Снять запрет, проверить вход.

⚠ `dropdb` необратим — шаг 2 обязателен. Если `dropdb` сообщает, что база используется, — остались соединения: завершить сеансы 1С либо `select pg_terminate_backend(pid) from pg_stat_activity where datname='demo'`.

Подробнее: `../postgresql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` (не проходила независимую проверку).

### 10. Обновление платформы 1С на сервере

1. Скачать дистрибутив; новая версия ставится **рядом** со старой, в свой каталог `/opt/1cv8/x86_64/<новая версия>`.
2. Запретить вход, сделать бэкап (инструкции 7 и раздел A).
3. Остановить старое: `sudo systemctl disable --now $SRV ras-$V`.
4. Установить новую версию (`NEW=…`): `sudo ./setup-full-$NEW-x86_64.run --mode unattended --enable-components server,ws,server_admin,liberica_jre,ru`.
5. Зарегистрировать и запустить юниты новой версии:

```bash
sudo systemctl link /opt/1cv8/x86_64/$NEW/srv1cv8-$NEW@.service /opt/1cv8/x86_64/$NEW/ras-$NEW.service
sudo systemctl enable --now srv1cv8-$NEW@default ras-$NEW.service
/opt/1cv8/x86_64/$NEW/rac cluster list
```

6. Перенести настройки экземпляра, если они были: `systemctl cat $SRV` покажет прежние `Environment=`.
7. Обновить веб-публикацию: повторить `webinst` новой версии и перезапустить Apache — версия модуля должна совпадать с версией кластера.
8. Обновить клиентов до той же версии; снять запрет.
9. **Откат:** остановить и отключить юниты новой версии, включить старые. Каталог данных кластера общий — откат возможен, пока новая версия не изменила формат данных; перед обновлением сохраните копию `$DATA`.

Подробнее: `../1c/02-ustanovka-servera-ubuntu.md`, `../its-docs/adm-gl11-gl12-pr02-pr05-obnovlenie-udalenie-zhurnal-oshibki.md`.

### 11. Обновление конфигурации базы

Порядок: запрет входа и регламентных заданий (инструкция 7) → бэкап → загрузка обновления и обновление конфигурации базы данных → снятие запрета → первый вход администратора для обработчиков обновления. Команды `ibcmd` и пакетного режима конфигуратора — `../1c/06-infobazy-ibcmd-paketnyj-rezhim.md` (статья не проходила независимую проверку; ключи сверены с документацией ИТС программно). Официальный справочник — `../its-docs/adm-pr04-komandnye-stroki-utilit-p3.md` и `../its-docs/adm-pr07-parametry-zapuska-1cv8-p1.md`.

### 12. Плановая перезагрузка сервера

```bash
# остановка: сначала 1С, потом СУБД
sudo systemctl stop $SRV
sudo systemctl stop $PGSVC
sudo reboot

# после загрузки
systemctl is-active $PGSVC $SRV ras-$V
sudo -u postgres pg_isready
$RAC cluster list && $RAC infobase summary list --cluster=$CL
```

Запуск — в обратном порядке: сначала PostgreSQL, потом сервер 1С. Если в юните сервера 1С задано `After=postgrespro-1c-17.service`, при загрузке порядок соблюдается сам.

### 13. Очистка сеансовых данных («кэша») сервера 1С

Не регулярная процедура — только при зависших сеансах, переживающих перезапуск, или ошибках сеансовых данных после аварии. Официальной инструкции 1С для Linux нет, приём общепринятый.

```bash
sudo systemctl stop $SRV
ps aux | grep -E '[r]agent|[r]mngr|[r]phost'           # процессов быть не должно
sudo ls -d $DATA/reg_*/snccntx* 2>/dev/null
sudo rm -rf -- $DATA/reg_*/snccntx*                    # только сеансовые данные
sudo systemctl start $SRV
```

⚠ **Нельзя удалять** `1cv8wsrv.lst`, `reg_1541/1CV8Clst.lst` (реестр кластера — пропадут все базы) и каталоги баз с журналом регистрации `1Cv8Log`. Все сеансы пользователей будут потеряны.

### 14. Веб-публикация перестала работать

1. `systemctl status apache2 --no-pager`; `sudo apachectl configtest`; `sudo tail -50 /var/log/apache2/error.log`.
2. После обновления платформы: в конфигурации Apache осталась строка `LoadModule _1cws_module` со старым путём — `grep -rn _1cws_module /etc/apache2/`. Переопубликовать `webinst` новой версии, перезапустить Apache.
3. Работает ли сам кластер: `$RAC cluster list`. Строка соединения — в `default.vrd` каталога публикации.
4. Права: пользователь `www-data` должен читать каталог публикации и каталог версии платформы.

Подробнее: `../1c/05-veb-publikaciya-apache-nginx.md`, `../its-docs/adm-gl08-veb-servery-p1.md`.

### 15. Копия базы для тестов; перенос на другой сервер

- **Копия на том же сервере:** как первая часть инструкции 9 (дамп → новая база → регистрация в кластере с запрещёнными регламентными заданиями).
- **Перенос на другой сервер:** `pg_dump -Fc` на старом → скопировать файл (`rsync -aP`) → `createdb` и `pg_restore` на новом → `rac infobase create` без `--create-database`. Версии PostgreSQL: восстанавливать в ту же или более новую; сборка должна быть «для 1С» (в дампе используются типы `mchar`/`mvarchar`).
- Лицензии на новый сервер не переносятся копированием файла — привязка к оборудованию.

## C. Скрипт проверки здоровья

Запускается от `root` (через `sudo`). Код возврата: 0 — всё в порядке, 1 — есть замечания.

```bash
#!/usr/bin/env bash
# /usr/local/bin/1c-health.sh — быстрая проверка сервера 1С + PostgreSQL
set -u
V=8.3.27.2074
SRV=srv1cv8-$V@default
PGSVC=postgrespro-1c-17
BACKUP_DIR=/backup/pg
export PATH=/opt/pgpro/1c-17/bin:$PATH
RC=0
ok()   { printf '[ OK ] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; RC=1; }

for S in "$PGSVC" "$SRV" "ras-$V"; do
  systemctl is-active --quiet "$S" && ok "служба $S активна" || warn "служба $S НЕ активна"
done

for P in 1540 1541 5432; do
  ss -tln | grep -q ":$P " && ok "порт $P слушается" || warn "порт $P не слушается"
done

while read -r USE MNT; do
  [ "${USE%\%}" -ge 85 ] && warn "диск $MNT заполнен на $USE" || ok "диск $MNT: $USE"
done < <(df --output=pcent,target -x tmpfs -x devtmpfs -x squashfs -x efivarfs | tail -n +2)

AVAIL=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
[ "$AVAIL" -lt 1024 ] && warn "доступной памяти мало: ${AVAIL} МБ" || ok "доступно памяти: ${AVAIL} МБ"

LAST=$(find "$BACKUP_DIR" -name '*.dump' -mmin -1560 2>/dev/null | head -1)
[ -n "$LAST" ] && ok "свежая копия есть: $LAST" || warn "нет копий моложе 26 часов в $BACKUP_DIR"

LONG=$(sudo -u postgres psql -AtX -c "select count(*) from pg_stat_activity where xact_start < now() - interval '30 minutes'" 2>/dev/null)
[ "${LONG:-x}" = "0" ] && ok "транзакций старше 30 минут нет" || warn "транзакций старше 30 минут: ${LONG:-нет ответа от PostgreSQL}"

CONN=$(sudo -u postgres psql -AtX -c "select count(*)*100/current_setting('max_connections')::int from pg_stat_activity" 2>/dev/null)
[ "${CONN:-100}" -lt 80 ] && ok "соединений PostgreSQL: ${CONN}% от max_connections" || warn "соединений PostgreSQL: ${CONN:-?}% от max_connections"

OOM=$(journalctl -k --since "24 hours ago" 2>/dev/null | grep -c -i 'out of memory')
[ "$OOM" -eq 0 ] && ok "OOM killer за сутки не срабатывал" || warn "OOM killer за сутки: $OOM"

exit $RC
```

Установка: сохранить в `/usr/local/bin/1c-health.sh`, `sudo chmod 755 /usr/local/bin/1c-health.sh`, запуск — `sudo 1c-health.sh`. Скрипт только читает состояние и ничего не меняет.

## D. Регламент

| Когда | Что проверять |
|---|---|
| Ежедневно | `sudo 1c-health.sh`; ночная копия создана; место на дисках; ошибки в журналах служб |
| Еженедельно | Пробное восстановление одной копии в отдельную базу; размер баз и крупнейших таблиц; рост `pg_wal`; память `rphost`; доступные обновления безопасности ОС |
| Ежемесячно | Обновление ОС в окно работ (с перезагрузкой); проверка, что копии уезжают с сервера и читаются там; ревизия пользователей и правил сетевого экрана; срок действия сертификатов HTTPS |
| Перед любыми работами | Бэкап; запрет входа; после работ — снять запрет и проверить вход обычным пользователем |

Официальные материалы по эксплуатации и мониторингу: `../its-metod/ekspluataciya-krupnoj-sistemy-blokirovki-tranzakcii.md`, `../its-metod/monitoring-i-audit.md`, `../its-metod/sbor-dannyh-dlya-rassledovaniya-problem.md`.

## Источники

- Конспекты документации 8.3.27: `../its-docs/cs-gl04-zapusk-komponentov.md`, `../its-docs/cs-gl05-administrirovanie-klastera-p3.md`, `../its-docs/adm-gl10-zashchita-licenzii-p1.md`, `../its-docs/adm-gl10-zashchita-licenzii-p2.md`, `../its-docs/adm-gl08-veb-servery-p1.md`, `../its-docs/adm-pr04-komandnye-stroki-utilit-p3.md`, `../its-docs/cs-gl02-klient-servernyj-variant-p1.md`.
- Статьи базы знаний: `../1c/02-ustanovka-servera-ubuntu.md`, `../1c/03-administrirovanie-klastera-ras-rac.md`, `../1c/05-veb-publikaciya-apache-nginx.md`, `../linux/06-processy-i-proizvoditelnost.md`, `../linux/07-diski-fs-lvm.md`.
