# Развёртывание с нуля: виртуальная машина → Ubuntu Server → PostgreSQL для 1С → сервер 1С → база → веб → бэкапы

> Область: одна ВМ на Windows-хосте, на ней и PostgreSQL, и сервер 1С | Стек: Ubuntu Server 24.04 LTS, «1С:Предприятие» 8.3.27, «PostgreSQL для 1С» 17 от Postgres Professional | Актуальность: 2026-10-10
>
> **Статус:** руководство собрано из конспектов официальной документации ИТС и проверенных статей базы знаний. На живом сервере последовательность целиком **не прогонялась** — проверяйте результат после каждого этапа (команды проверки приведены).

## Почему такой стек

- **Ubuntu 24.04 LTS** — входит в перечень ОС для 64-разрядного сервера 1С 8.3.27 (20.04, 22.04, 24.04). Ubuntu 26.04 в документации 8.3.27 не значится. Источник: `../its-docs/cs-gl01-trebovaniya.md`, разд. 1.2.1.
- **PostgreSQL 17** — документация 8.3.27 называет поддерживаемыми версии 10–18 в вариантах «с патчем от 1С» и «от Postgres Pro» (там же, разд. 1.5.8). Здесь основной вариант — бесплатная сборка «PostgreSQL для 1С» от Postgres Professional: ставится из открытого репозитория. Вариант со сборкой от фирмы «1С» — в `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`.
- **Для платформы 8.5** шаги те же; отличия документации — в `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`. С версии 8.5.4 изменён механизм лицензирования (см. этап 7).

## Переменные, которые используются ниже

Задайте их в каждой новой сессии терминала (значения — пример, подставьте свои).

```bash
V=8.3.27.2074            # точный номер сборки платформы — как в имени дистрибутива
HOST=srv1c               # короткое имя сервера
DOMAIN=example.local
IP=192.168.1.50          # статический адрес сервера
NET=192.168.1.0/24       # сеть, из которой подключаются клиенты
PG=/opt/pgpro/1c-17/bin  # каталог программ PostgreSQL
RAC=/opt/1cv8/x86_64/$V/rac
```

## Этап 0. Что подготовить заранее

1. **Дистрибутив сервера 1С для Linux** с releases.1c.ru: архив с файлом `setup-full-<версия>-x86_64.run`. Версия клиентов на Windows должна совпадать с версией сервера.
2. **Лицензии:** серверная и клиентские (пин-коды программных лицензий либо ключи HASP). Для сервера в ВМ документация рекомендует программные лицензии: USB over IP для HASP не поддерживается.
3. **Ресурсы ВМ** (ориентир для небольшой базы, до пары десятков пользователей): 4–8 vCPU, 16 ГБ ОЗУ фиксированного объёма, диск под систему 40–60 ГБ, отдельный диск под данные PostgreSQL и отдельный — под резервные копии. Расчёт под нагрузку — `../its-metod/raschet-oborudovaniya-i-nagruzochnoe-testirovanie.md`.
4. **Имя и адрес сервера.** Клиенты 1С подключаются к кластеру по имени хоста, поэтому имя должно разрешаться в реальный адрес и на сервере, и на каждом клиенте.

## Этап 1. Виртуальная машина и установка Ubuntu Server

Параметры ВМ важны из-за привязки программной лицензии (см. этап 7) — задайте их **до** активации и потом не меняйте.

- **Hyper-V:** поколение 2; шаблон безопасной загрузки «Центр сертификации Microsoft UEFI»; **статическая** память (динамическую не включать); внешний виртуальный коммутатор; **статический MAC-адрес** сетевого адаптера.
- **VMware / VirtualBox:** сетевой адаптер в режиме моста (bridged), фиксированный MAC.
- При установке Ubuntu Server отметьте установку OpenSSH. Установщик по умолчанию отдаёт логическому тому не весь диск — расширение описано в `../linux/07-diski-fs-lvm.md`.

Подробнее: `../linux/11-ustanovka-ubuntu-server-i-vm.md`.

## Этап 2. Базовая настройка ОС

Выполняется обычным пользователем с `sudo`.

```bash
# имя хоста и /etc/hosts: имя должно указывать на реальный адрес, а не на 127.0.1.1
sudo hostnamectl set-hostname $HOST
sudo cp /etc/hosts /etc/hosts.bak
sudo sed -i "/^127\.0\.1\.1/s/^/#/" /etc/hosts
echo "$IP $HOST.$DOMAIN $HOST" | sudo tee -a /etc/hosts

# обновления, локаль, время
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y locales unzip curl wget mc htop sysstat
sudo locale-gen en_US.UTF-8 ru_RU.UTF-8
sudo update-locale LANG=ru_RU.UTF-8
sudo timedatectl set-timezone Asia/Tashkent
sudo timedatectl set-ntp true
```

**Проверка:**

```bash
hostname -f                 # srv1c.example.local
getent hosts $HOST          # должен вернуть $IP, а не 127.0.1.1
locale -a | grep -i ru_RU   # ru_RU.utf8
timedatectl                 # System clock synchronized: yes
```

После `update-locale` перезайдите в систему, чтобы `LANG` применился.

Статический адрес задаётся в netplan — `../linux/08-set-ssh-firewall.md`. Локаль `ru_RU.UTF-8` обязана существовать **до** создания кластера PostgreSQL: локаль кластера потом не меняется.

## Этап 3. Диски под данные и копии

Если под PostgreSQL и копии выделены отдельные диски, смонтируйте их до установки СУБД (пример для второго диска `/dev/sdb`, файловая система ext4):

```bash
lsblk -f                                   # убедиться, что /dev/sdb пуст
sudo mkfs.ext4 -L pgdata /dev/sdb
sudo mkdir -p /var/lib/pgpro
echo 'LABEL=pgdata /var/lib/pgpro ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
sudo mount -a && findmnt /var/lib/pgpro
```

⚠ `mkfs` уничтожает данные на диске — проверьте имя устройства по `lsblk`. Каталог под копии (`/backup`) монтируется так же, на другой диск. Подробнее: `../linux/07-diski-fs-lvm.md`.

## Этап 4. PostgreSQL для 1С

### 4.1. Установка

```bash
locale -a | grep -i ru_RU                  # локаль обязана быть

cd /tmp
wget https://repo.postgrespro.ru/1c/1c-17/keys/pgpro-repo-add.sh
less pgpro-repo-add.sh                     # просмотреть скрипт перед запуском от root
sudo sh pgpro-repo-add.sh

apt-get -s install postgrespro-1c-17 | grep -E '^(Inst|Remv)'   # что поставит и что удалит
sudo LANG=ru_RU.UTF-8 apt-get install -y postgrespro-1c-17
```

Метапакет сам создаёт кластер в `/var/lib/pgpro/1c-17/data` с локалью из `LANG`, включает автозапуск и запускает службу `postgrespro-1c-17`.

⚠ Метапакет конфликтует с `postgresql-common`: если на машине уже стоит другой PostgreSQL, apt его удалит. На чистом сервере это не проблема; иначе — «расширенная установка» из `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, разд. 5.2.

**Проверка:**

```bash
systemctl status postgrespro-1c-17 --no-pager
sudo -u postgres psql -At -c "select version()" -c "show data_directory" -c "show port"
sudo -u postgres psql -c "select datname, pg_encoding_to_char(encoding) enc, datcollate from pg_database"
# ожидается UTF8 и ru_RU.UTF-8
```

Если `psql` не находится — `sudo $PG/pg-wrapper links update` или вызывайте `$PG/psql` по полному пути.

### 4.2. Пароль и доступ

```bash
sudo -u postgres psql -c "\password postgres"     # задать пароль — он понадобится серверу 1С
sudo -u postgres psql -At -c "show hba_file" -c "show listen_addresses"
```

Сервер 1С и PostgreSQL стоят на одной машине и общаются по TCP через `localhost`, поэтому `listen_addresses = 'localhost'` менять не нужно, а порт 5432 наружу не открывается. Метапакет настраивает в `pg_hba.conf` метод `md5` для TCP. Метод `scram-sha-256` работает с платформой 8.3.20 и новее.

### 4.3. Настройки под 1С

Сборка «для 1С» при установке сама подбирает конфигурацию под объём памяти и число ядер. Сначала посмотрите, что уже выставлено, затем приведите ключевые параметры к официальным рекомендациям ИТС («Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2», редакция 19.06.2025 — `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`).

```bash
sudo -u postgres psql -c "select name, setting, unit, source from pg_settings where source not in ('default','override') order by name"
```

В формулах ИТС «RAM» — память, доступная именно PostgreSQL. Пример для ВМ на 16 ГБ, где PostgreSQL отдаётся 8 ГБ, остальное — серверу 1С и ОС:

| Параметр | Формула ИТС | Значение для 8 ГБ под PostgreSQL |
|---|---|---|
| `shared_buffers` | RAM/4 | `2GB` |
| `effective_cache_size` | RAM − shared_buffers | `6GB` |
| `work_mem` | RAM/32..64 или 32MB..256MB | `128MB` |
| `maintenance_work_mem` | RAM/16..32 или 256MB..4GB | `512MB` |
| `temp_buffers` | 32..256MB | `64MB` |
| `max_connections` | 500..8000 | `500` |
| `max_locks_per_transaction` | 512..2000 | `512` |
| `min_wal_size` / `max_wal_size` | 512MB..4G / вдвое больше | `1GB` / `2GB` |
| `random_page_cost` | 1.1–1.3 для SSD | `1.1` |

```bash
sudo -u postgres psql <<'SQL'
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET work_mem = '128MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET temp_buffers = '64MB';
ALTER SYSTEM SET max_connections = 500;
ALTER SYSTEM SET max_locks_per_transaction = 512;
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET from_collapse_limit = 20;
ALTER SYSTEM SET join_collapse_limit = 20;
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_naptime = '20s';
ALTER SYSTEM SET bgwriter_delay = '20ms';
ALTER SYSTEM SET bgwriter_lru_multiplier = 4.0;
ALTER SYSTEM SET bgwriter_lru_maxpages = 400;
ALTER SYSTEM SET standard_conforming_strings = off;
ALTER SYSTEM SET escape_string_warning = off;
ALTER SYSTEM SET jit = off;
ALTER SYSTEM SET row_security = off;
SQL
sudo systemctl restart postgrespro-1c-17
sudo -u postgres psql -c "select name, setting, pending_restart from pg_settings where name in ('shared_buffers','max_connections','max_locks_per_transaction','standard_conforming_strings')"
```

Замечания:

- **`fsync` не трогать** (`on`). ИТС рекомендует ещё `synchronous_commit = off` — это заметно ускоряет запись, но при сбое можно потерять транзакции последних 0,5–1 секунды (целостность базы сохраняется). Решение за вами: `ALTER SYSTEM SET synchronous_commit = off;` и `SELECT pg_reload_conf();`.
- **Автовакуум не выключать никогда.**
- Суммарный расход `work_mem` может достигать `work_mem × число операций × число соединений` — при нехватке памяти уменьшайте его первым.
- Отменить правку: `ALTER SYSTEM RESET имя;`. Все правки `ALTER SYSTEM` лежат в `postgresql.auto.conf` каталога данных.

Полный разбор параметров и расхождений с рекомендациями Postgres Professional — `../postgresql/02-postgresql-conf-tyuning-dlya-1c.md`. Тюнинг ОС (huge pages, THP, `vm.*`) — `../linux/09-tyuning-yadra-lokali-vremya-bezopasnost.md`.

## Этап 5. Сервер 1С

### 5.1. Зависимости и шрифты

```bash
sudo add-apt-repository -y multiverse
sudo apt update
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | sudo debconf-set-selections
sudo apt install -y ttf-mscorefonts-installer fontconfig \
    libfreetype6 libgsf-1-114 unixodbc libkrb5-3 libgssapi-krb5-2 imagemagick
sudo fc-cache -fv
```

Шрифты Microsoft Core Fonts нужны серверу для печатных форм и PDF. Список библиотек по документации — `../its-docs/cs-gl01-trebovaniya.md`, разд. 1.3.3.

### 5.2. Установка платформы

```bash
mkdir -p ~/distr/1c && cd ~/distr/1c
unzip ~/server64_*.zip -d .                # имя архива — как у скачанного дистрибутива
chmod +x setup-full-$V-x86_64.run
sudo ./setup-full-$V-x86_64.run --mode unattended \
    --enable-components server,ws,server_admin,liberica_jre,ru
echo "код возврата установщика: $?"
```

Состав компонентов — как в примере документации: `server` — кластер серверов, `ws` — модуль расширения веб-сервера, `server_admin` — сервер и утилита администрирования (`ras`, `rac`), `liberica_jre` — Java, `ru` — русский интерфейс (указывается явно). Источник: `../its-docs/cs-gl03-ustanovka-komponentov-p1.md`.

**Проверка:**

```bash
ls /opt/1cv8/x86_64/$V/ | grep -E 'ragent|rmngr|rphost|^ras$|^rac$|service'
for b in ragent rmngr rphost ras rac; do ldd /opt/1cv8/x86_64/$V/$b | grep "not found"; done   # пусто — хорошо
getent passwd usr1cv8 && getent group grp1cv8      # пользователь создаётся установщиком
```

### 5.3. Служба сервера

Автозапуск установщик не настраивает — это отдельный шаг. Юнит поставляется шаблоном, экземпляр с параметрами по умолчанию называется `default`.

```bash
sudo systemctl link /opt/1cv8/x86_64/$V/srv1cv8-$V@.service
sudo systemctl enable --now srv1cv8-$V@default
sleep 5
systemctl status srv1cv8-$V@default --no-pager
ps aux | grep -E '[r]agent|[r]mngr|[r]phost'
sudo ss -tlnp | grep -E 'ragent|rmngr|rphost'      # порты 1540, 1541 и из диапазона 1560–1591
```

Параметры экземпляра (каталог данных, порты, отладка) задаются через `sudo systemctl edit srv1cv8-$V@default` строками `Environment=SRV1CV8_…` в секции `[Service]`; допустимые имена — `SRV1CV8_DATA`, `SRV1CV8_PORT`, `SRV1CV8_REGPORT`, `SRV1CV8_RANGE`, `SRV1CV8_DEBUG`, `SRV1CV8_SECLEV`, `SRV1CV8_KEYTAB`, `SRV1CV8_PINGPERIOD`, `SRV1CV8_PINGTIMEOUT`. ⚠ Имена двух последних в документации и в поставляемом юните могут различаться (`SRV1CV8_PING_PERIOD` / `SRV1CV8_PING_TIMEOUT`) — фактические имена смотрите в `systemctl cat srv1cv8-$V@default`. Каталог данных кластера по умолчанию — `/home/usr1cv8/.1cv8/1C/1cv8`. Источник: `../its-docs/cs-gl04-zapusk-komponentov.md`.

### 5.4. Сервер администрирования и сетевой экран

```bash
sudo systemctl link /opt/1cv8/x86_64/$V/ras-$V.service
sudo systemctl enable --now ras-$V.service
sleep 3
$RAC cluster list                          # UUID кластера, host, port : 1541

sudo ufw allow OpenSSH
sudo ufw allow from $NET to any port 1540:1541 proto tcp
sudo ufw allow from $NET to any port 1560:1591 proto tcp
sudo ufw --force enable
sudo ufw status verbose
```

Порт `ras` (1545) наружу открывать не нужно, если `rac` запускается на самом сервере. Версия `ras` должна совпадать с версией кластера.

Чтобы сервер 1С стартовал после СУБД, добавьте зависимость:

```bash
sudo systemctl edit srv1cv8-$V@default
# в открывшемся редакторе:
# [Unit]
# After=postgrespro-1c-17.service network-online.target
# Wants=postgrespro-1c-17.service network-online.target
sudo systemctl daemon-reload
```

Подробнее: `../1c/02-ustanovka-servera-ubuntu.md`, `../1c/03-administrirovanie-klastera-ras-rac.md`.

## Этап 6. Информационная база

```bash
CL=$($RAC cluster list | awk '/^cluster/{print $3}')
read -rsp "Пароль пользователя postgres в СУБД: " PGPWD; echo

$RAC infobase create --cluster=$CL --create-database \
    --name=demo --dbms=PostgreSQL --db-server=localhost --db-name=demo \
    --locale=ru_RU --db-user=postgres --db-pwd="$PGPWD" \
    --license-distribution=allow --scheduled-jobs-deny=on

$RAC infobase summary list --cluster=$CL
sudo -u postgres psql -c "\l demo"
```

- `--scheduled-jobs-deny=on` держит регламентные задания выключенными, пока база пустая; включите их после загрузки данных: `$RAC infobase update --cluster=$CL --infobase=<UUID> --scheduled-jobs-deny=off` (понадобятся `--infobase-user` и `--infobase-pwd`, когда в базе появятся пользователи).
- **Права пользователя СУБД.** По документации (глава о списке информационных баз, параметры PostgreSQL) пользователь, от имени которого 1С обращается к СУБД, должен иметь привилегию `SUPERUSER` только в момент создания информационной базы; после создания её можно отозвать: `alter user dbuser with nosuperuser;`. Поэтому для работы базы можно завести отдельную роль, а не использовать `postgres` постоянно.
- ⚠ Параметры `rac` в документации ИТС не перечислены — она отсылает к встроенной справке. Перед выполнением сверьтесь: `$RAC help infobase`.
- **Загрузка данных:** из клиента на Windows (конфигуратор → «Администрирование → Загрузить информационную базу») или с сервера утилитой `ibcmd` — `../1c/06-infobazy-ibcmd-paketnyj-rezhim.md`. Перенос из другой СУБД без dt-файла — `ibcmd infobase replicate`.

## Этап 7. Лицензии

1. **До активации** зафиксируйте параметры ВМ. Программная лицензия привязывается к сетевому имени компьютера, материнской плате, BIOS, процессорам, сетевым адаптерам с MAC-адресами, дискам и объёму ОЗУ. Добавлять память и адаптеры можно; **убирать или заменять** — нельзя, потребуется повторная активация новым пин-кодом (в серверном комплекте их три). Источник: `../its-docs/adm-gl10-zashchita-licenzii-p1.md`, разд. 10.3.1.4.
2. **Активация на сервер без графики** — с компьютера Windows, где стоит клиент той же версии: при запуске или в конфигураторе «Сервис → Получение лицензии» → пин-код → «Дополнительно» → флажок **«Установка на сервер»**, поля «Сервер» и «Порт». Файл лицензии окажется на сервере в `/var/1C/licenses`.
3. **Проверка на сервере:**

```bash
sudo ls -l /var/1C/licenses/               # файлы *.lic; каталог: владелец root, группа grp1cv8
id usr1cv8                                  # должен входить в grp1cv8
```

4. Сохраните копии файлов `*.lic` вне сервера. Не держите один и тот же файл в нескольких каталогах поиска — он может стать непригодным.
5. Альтернатива — утилита `ring license` на самом сервере (нужна Java) — `../1c/04-licenzirovanie.md`.
6. **Платформа 8.5.4 и новее:** новый механизм проверки лицензий; для сетевых ключей HASP нужен «Менеджер лицензий» (`rmlic`, порты 475 и 1544). Источник: `../its-metod/licenzii-hasp-java-api-prochee-administrirovanie.md`.

## Этап 8. Веб-публикация (по необходимости)

```bash
sudo apt install -y apache2
sudo a2dismod mpm_event && sudo a2enmod mpm_worker      # документация рекомендует MPM worker
sudo mkdir -p /var/www/demo                             # каталог публикации должен существовать
sudo /opt/1cv8/x86_64/$V/webinst -publish -apache24 -wsdir demo -dir /var/www/demo \
    -connstr "Srvr=$HOST;Ref=demo;" -confpath /etc/apache2/apache2.conf
sudo apachectl configtest
sudo systemctl restart apache2
sudo ufw allow from $NET to any port 80 proto tcp

curl -sI http://localhost/demo/ | head -1               # ожидается ответ веб-сервера, не «connection refused»
```

- Версия `webinst` и модуля `wsap24.so` должна точно совпадать с версией кластера; после обновления платформы публикацию нужно обновить и перезапустить Apache.
- Имя виртуального каталога и путь — только латиницей.
- Для доступа из Интернета нужен HTTPS — `../its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md` и `../1c/05-veb-publikaciya-apache-nginx.md`.

## Этап 9. Резервное копирование

Выгрузка dt-файла резервной копией не является — так прямо сказано в документации. Копии делаются средствами СУБД.

```bash
sudo install -d -o postgres -g postgres -m 750 /backup/pg

sudo tee /usr/local/bin/pg-backup.sh >/dev/null <<'EOF'
#!/usr/bin/env bash
# Логические копии всех пользовательских баз PostgreSQL с ротацией.
set -Eeuo pipefail
export PATH=/opt/pgpro/1c-17/bin:$PATH
DIR=/backup/pg
KEEP_DAYS=14
STAMP=$(date +%F_%H%M)

for DB in $(psql -AtX -c "SELECT datname FROM pg_database WHERE datallowconn AND datname NOT IN ('postgres','template1')"); do
  OUT="$DIR/${DB}_${STAMP}.dump"
  pg_dump -Fc -f "$OUT.tmp" "$DB"
  mv "$OUT.tmp" "$OUT"
done
pg_dumpall --globals-only > "$DIR/globals_${STAMP}.sql"
find "$DIR" -type f \( -name '*.dump' -o -name 'globals_*.sql' \) -mtime +"$KEEP_DAYS" -delete
EOF
sudo chmod 755 /usr/local/bin/pg-backup.sh

sudo tee /etc/systemd/system/pg-backup.service >/dev/null <<'EOF'
[Unit]
Description=PostgreSQL logical backup (pg_dump)
After=postgrespro-1c-17.service

[Service]
Type=oneshot
User=postgres
ExecStart=/usr/local/bin/pg-backup.sh
EOF

sudo tee /etc/systemd/system/pg-backup.timer >/dev/null <<'EOF'
[Unit]
Description=Nightly PostgreSQL backup

[Timer]
OnCalendar=*-*-* 01:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now pg-backup.timer
sudo systemctl start pg-backup.service          # первый запуск вручную
systemctl status pg-backup.service --no-pager; ls -lh /backup/pg
```

**Проверка восстановлением — обязательна**, иначе копии нет:

```bash
F=$(ls -t /backup/pg/demo_*.dump | head -1)
sudo -u postgres $PG/createdb demo_restore_test
sudo -u postgres $PG/pg_restore -d demo_restore_test -j 4 "$F"
sudo -u postgres $PG/psql -d demo_restore_test -c "select count(*) from pg_class where relkind='r'"
sudo -u postgres $PG/dropdb demo_restore_test
```

Кроме баз, копируйте:

| Что | Где | Зачем |
|---|---|---|
| Данные кластера 1С | `/home/usr1cv8/.1cv8/1C/1cv8` | реестр кластера и список баз, журнал регистрации |
| Лицензии | `/var/1C/licenses` | файлы `*.lic` |
| Настройки платформы | `/opt/1cv8/conf`, `/opt/1cv8/x86_64/$V/conf` | `conf.cfg`, `logcfg.xml`, `nethasp.ini` |
| Публикации | `/var/www/<имя>`, `/etc/apache2` | `default.vrd`, конфигурация Apache |
| Настройки PostgreSQL | `/var/lib/pgpro/1c-17/data/*.conf` | `postgresql.conf`, `postgresql.auto.conf`, `pg_hba.conf` |

Копии должны уезжать с сервера (другой хост, NAS, шара Windows). Физические копии, архив WAL и восстановление на момент времени — `../postgresql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` (статья не проходила независимую проверку).

## Этап 10. Журналы и минимальный контроль

```bash
journalctl -u srv1cv8-$V@default --since today --no-pager | tail -50
journalctl -u postgrespro-1c-17 --since today --no-pager | tail -50
sudo -u postgres psql -c "select pid, state, now()-xact_start as xact_age, left(query,60) from pg_stat_activity where state <> 'idle' order by xact_start nulls last limit 10"
df -h; free -h
```

Технологический журнал на ошибки включается файлом `logcfg.xml` в `/opt/1cv8/conf` (каталог журнала должен быть доступен на запись пользователю `usr1cv8`):

```bash
sudo install -d -o usr1cv8 -g grp1cv8 -m 750 /var/log/1c/techlog
sudo mkdir -p /opt/1cv8/conf
sudo tee /opt/1cv8/conf/logcfg.xml >/dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="/var/log/1c/techlog" history="48">
    <event><eq property="name" value="EXCP"/></event>
    <property name="all"/>
  </log>
</config>
EOF
```

Журнал подхватывается без перезапуска сервера. Полный журнал (все события) на рабочем сервере постоянно держать нельзя. Подробнее: `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`, `../its-metod/tehzhurnal-bash-i-potreblenie-resursov.md`.

## Этап 11. Клиенты на Windows

1. Установить платформу **той же версии**, что и сервер.
2. Обеспечить разрешение имени сервера: запись в DNS либо строка в `C:\Windows\System32\drivers\etc\hosts`:

```text
192.168.1.50 srv1c.example.local srv1c
```

3. Проверить порты из PowerShell: `Test-NetConnection srv1c -Port 1541`.
4. Добавить базу: «на сервере 1С:Предприятия», кластер `srv1c`, имя базы `demo`.

⚠ Ограничение из документации: клиент в виртуальной машине с сетью типа NAT не поддерживается, если кластер серверов расположен на хост-компьютере этой же ВМ.

## Итоговый чек-лист

- [ ] `getent hosts $HOST` возвращает реальный адрес; имя сервера разрешается на клиентах.
- [ ] `locale -a` содержит `ru_RU.utf8`; базы PostgreSQL — UTF8 / ru_RU.UTF-8.
- [ ] `postgrespro-1c-17`, `srv1cv8-$V@default`, `ras-$V` — `enabled` и `active`.
- [ ] После перезагрузки сервера всё поднимается само; `$RAC cluster list` отвечает.
- [ ] База создана, клиент с Windows входит.
- [ ] Лицензии получены, копии `*.lic` сохранены вне сервера, параметры ВМ зафиксированы.
- [ ] Таймер `pg-backup.timer` активен, копия создаётся, **пробное восстановление выполнено**.
- [ ] Копии уезжают с сервера.
- [ ] `ufw` включён; наружу открыты только 22, 1540–1541, 1560–1591 (и 80/443 при веб-публикации).

## Что сделать в первую неделю эксплуатации

1. Перезагрузить сервер и убедиться, что всё стартует в правильном порядке.
2. Запретить автоматическое обновление пакетов СУБД: `sudo apt-mark hold postgrespro-1c-17 postgrespro-1c-17-server postgrespro-1c-17-client postgrespro-1c-17-libs postgrespro-1c-17-contrib` — обновляйте их осознанно, в окно работ.
3. Проследить за ростом диска, памятью `rphost` и временем ночной копии.
4. Настроить регламент обслуживания — `../postgresql/05-obsluzhivanie-vacuum-analyze-reindex.md`.
5. Прочитать аварийные инструкции — `02-runbooki-i-shpargalki.md`.

## Источники

- Конспекты документации 8.3.27: `../its-docs/cs-gl01-trebovaniya.md`, `../its-docs/adm-gl02-ustanovka-p1.md`, `../its-docs/cs-gl03-ustanovka-komponentov-p1.md`, `../its-docs/cs-gl03-ustanovka-komponentov-p2.md`, `../its-docs/cs-gl04-zapusk-komponentov.md`, `../its-docs/cs-gl05-administrirovanie-klastera-p3.md`, `../its-docs/adm-gl08-veb-servery-p1.md`, `../its-docs/adm-gl10-zashchita-licenzii-p1.md`, `../its-docs/adm-gl10-zashchita-licenzii-p2.md`, `../its-docs/adm-pr04-komandnye-stroki-utilit-p3.md`.
- Конспекты методических статей ИТС: `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`, `../its-metod/licenzii-hasp-java-api-prochee-administrirovanie.md`.
- Проверенные статьи базы знаний: `../1c/02-ustanovka-servera-ubuntu.md`, `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, `../1c/05-veb-publikaciya-apache-nginx.md`, `../1c/04-licenzirovanie.md`.
