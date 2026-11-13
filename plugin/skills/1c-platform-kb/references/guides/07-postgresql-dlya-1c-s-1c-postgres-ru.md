# Установка «PostgreSQL для 1С» с сайта 1c.postgres.ru: инструкция пользователя, сверенная с первоисточниками

> Область: установка бесплатной сборки «PostgreSQL для 1С» компании Postgres Professional на Ubuntu Server | Версии: сборки 14–18, Ubuntu 22.04 / 24.04 / 25.10 / 26.04 | Актуальность: 2026-10-11.
> **Источники (прочитаны 11.10.2026):** (1) файл пользователя «Установка PG SQL.docx» — рабочая инструкция его организации; (2) сайт `https://1c.postgres.ru/` (страница, ответы на вопросы, форма); (3) репозиторий `https://repo.postgrespro.ru/1c/` — листинги, `meta.json` веток 14–18, индексы `Packages`, полный текст `pgpro-repo-add.sh`; (4) **официальная документация именно этой сборки** — `https://repo.postgrespro.ru/doc/pg1c/<версия>/ru/html/` (версии 16 и 18: глава «Установка из двоичных пакетов», страницы `pg-setup`, `pg-wrapper`, `initdb`, `pgpro_tune`, приложение K «Настройка PostgreSQL для решений 1С», описания модулей); (5) **сам пакет** `postgrespro-1c-16-server_16.14-1.noble_amd64.deb` (скачан с согласия пользователя, сумма SHA256 совпала с индексом репозитория, ничего не запускалось): файл службы, скрипты `pg-setup` и `check-db-dir`, пресеты `*.tune`, образцы конфигурации, скрипты установки и удаления — и метапакет `postgrespro-1c-16_16.14-1.noble_amd64.deb` (его скрипт установки) — раздел 7.
> **На живом сервере команды не выполнялись.** Подробный разбор той же установки — в `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, раздел 5; здесь — короткий порядок действий, сверка инструкции пользователя и конспект документации сборки.
> Обозначения: **[док.]** — документация сборки; **[пакет]** — содержимое пакета `postgrespro-1c-16-server` 16.14; **[репо]** — файлы репозитория; **[сайт]** — 1c.postgres.ru; **[инстр.]** — инструкция пользователя; **[вывод]** — вывод составителя, первоисточником прямо не подтверждён.

---

## 1. Что такое 1c.postgres.ru

- Сайт Postgres Professional для пользователей 1С. Раздаёт **«PostgreSQL для 1С» — ванильный PostgreSQL с патчами и расширениями для совместимости с 1С** **[сайт]**. Это не Postgres Pro: коммерческие Postgres Pro Standard и Postgres Pro Enterprise для 1С — отдельные продукты.
- **Условия [сайт]:** бесплатно для любых целей, **кроме предоставления СУБД как услуги (DBaaS) и встраивания в свои продукты**. Без гарантий и **без технической поддержки**; обновления могут выходить с задержкой относительно PostgreSQL и Postgres Pro. В реестр российского ПО сборка **не входит**. Поставщик позиционирует её для малого бизнеса, тестовых и непроизводственных сред, некритичных данных, «единиц и десятков пользователей».
- **Совместимость [сайт]:** все сборки технически совместимы с платформой 1С; какие версии прошли тестирование 1С — смотреть на `https://v8.1c.ru/requirements/` (в базе знаний — `../1c/01-arhitektura-versii-trebovaniya.md`, `../postgresql/01-…`, раздел 1).
- **Отличие от сборки с сайта 1С [сайт]:** параметры конфигурации автоматически выставляются под характеристики машины; сборка «готова к использованию и не требует дополнительной установки системных зависимостей».
- **Только 64-разрядные** Windows и Linux.
- Контакты: `1c@postgrespro.ru`.

### Версии и операционные системы

Форма на сайте предлагает PostgreSQL 9.5–18, но списки ОС сайт отдаёт только для 14–18 (для более старых веток запрос завершается ошибкой сервера; их выпуски лежат в `https://repo.postgrespro.ru/1c/archive/`). Поддерживаемые выпуски Ubuntu по `meta.json` **[репо, 11.10.2026]**:

| Ветка | Версия сборки | Ubuntu |
|---|---|---|
| 14 | 14.23 | 22.04, 24.04 |
| 15 | 15.18 | 22.04, 24.04 |
| **16** | **16.14** | **22.04, 24.04** |
| 17 | 17.10 | 22.04, 24.04, 25.10, 26.04 |
| 18 | 18.4 | 22.04, 24.04, 25.10, 26.04 |

**На Ubuntu 26.04 сборки 14–16 не выпускаются** — только 17 и 18. Другие ОС в списке: Альт Сервер, Debian, РЕД ОС, RHEL и производные, ROSA (с 16-й ветки), SLES, Windows.

### Форму заполнять не обязательно

Форма (версия, ОС, ФИО, e-mail, компания, согласие на обработку персональных данных) отправляет письмо с инструкцией. **Те же самые тексты инструкций лежат открыто** в файле `https://repo.postgrespro.ru/1c/1c-<версия>/meta.json` (поле `install` для каждой ОС), а адрес скрипта строится по шаблону — письмо для самой установки не требуется **[репо]**.

---

## 2. Инструкция пользователя и её сверка

Краткое содержание файла «Установка PG SQL.docx» **[инстр.]**: зайти на 1c.postgres.ru → выбрать версию (в инструкции — 16) и ОС (Ubuntu) → указать контакты → получить письмо с командами → **до установки** перевести локаль системы в `en_US.UTF-8` → установить → задать пароль пользователю `postgres`.

| Шаг инструкции | Что говорят первоисточники | Замечание |
|---|---|---|
| Письмо: `wget https://repo.postgrespro.ru/1c-16/keys/pgpro-repo-add.sh`, `sh pgpro-repo-add.sh` | **[репо]** Скрипт доступен по трём адресам с одинаковым содержимым (суммы MD5 совпали 11.10.2026): `repo.postgrespro.ru/1c-16/…`, `repo.postgrespro.ru/1c/1c-16/…`, `repo.postgres.ru/1c/1c-16/…`. В `meta.json` сейчас записан третий | Запускать от `root` (`sudo sh …`); перед запуском скрипт стоит просмотреть — это рекомендует и документация |
| `apt-get install postgrespro-1c-16` — «если наш продукт единственный Postgres на машине» | **[док., 18.1.4]** Быстрая установка: ставит клиент, сервер, модули; создаёт кластер, запускает службу, включает автозапуск, добавляет программы в `PATH` | Пакет конфликтует с `postgresql-common` — **apt удалит другой установленный PostgreSQL**; перед установкой посмотреть список удаляемого (раздел 3, шаг 4) |
| `apt-get install postgrespro-1c-16-contrib` и три команды `pg-setup` — «если уже установлен другой Postgres» | **[док., 18.1.5]** Расширенная установка: кластер и автозапуск настраиваются вручную | Автозапуск в этом варианте по умолчанию выключен — нужна `pg-setup service enable` |
| «Перед установкой локаль системы установить в `en_US.UTF-8`, иначе конфигурация WE не загрузится» | **[док., страницы `pg-setup`, 18.1.5]** Кластер создаётся с локалью из переменной **`LANG` текущего сеанса** (`LC_*` игнорируются) — то есть локаль действительно нужно выставить **до** установки. **[пакет]** Если же локаль сеанса не UTF-8 (`C`, `POSIX`, а также `C.UTF-8` — частое умолчание Ubuntu Server), `pg-setup` подбирает её сам, и **первой в его списке стоит `ru_RU.UTF-8`**, `en_US.UTF-8` — вторая (раздел 7). Это и объясняет требование инструкции: без явной `en_US.UTF-8` кластер на машине, где сгенерирована русская локаль, получится русским. **[док., K.1]** Для решений 1С документация требует **русскую** локаль `ru_RU.UTF-8` (пример дан для неё) | Противоречия нет **[вывод]**: локаль кластера должна соответствовать «Языку (стране)» информационной базы (`../postgresql/01-…`, раздел 4.2). Для русских конфигураций — `ru_RU.UTF-8`, для международных (WE) с английской локалью — `en_US.UTF-8`. Причину «WE не загрузится» по первоисточнику проверить не удалось — это опыт организации пользователя |
| `locale -a`, `locale`, `sudo locale-gen en_US.UTF-8`, `sudo update-locale`, `sudo localectl set-locale LANG=en_US.UTF-8` | Стандартные команды Ubuntu (`../linux/09-tyuning-yadra-lokali-vremya-bezopasnost.md`) | **Важное дополнение:** новая системная локаль действует только в **новых сеансах**. После `localectl set-locale` нужно выйти и войти заново (или передать `LANG=…` прямо в команде установки), иначе кластер создастся в старой локали |
| Перейти в `/opt/pgpro/1c-16/bin`, выполнить `sudo -u postgres ./psql` | **[док.]** Каталог установки — `/opt/pgpro/1c-16`; при быстрой установке `psql` уже есть в `PATH` | Достаточно `sudo -u postgres psql` из любого каталога |
| `ALTER USER postgres WITH PASSWORD 'new_password';` | Команда корректна | Надёжнее команда psql `\password postgres`: пароль не отображается, не попадает в `~postgres/.psql_history` и в журнал сервера |
| Выход командой `exit` | В psql работают `exit`, `quit`, `\q` | — |

---

## 3. Порядок установки (Ubuntu 22.04 / 24.04, ветка 16, один PostgreSQL на машине)

Для другой ветки заменить `16` на её номер (на Ubuntu 26.04 — только `17` или `18`). В командах `en_US.UTF-8` — локаль из инструкции пользователя; для русскоязычных баз подставить `ru_RU.UTF-8`.

**Шаг 1. Исходное состояние** (обычный пользователь с `sudo`):

```bash
lsb_release -ds; dpkg --print-architecture          # ожидается Ubuntu 22.04/24.04 и amd64
dpkg -l | grep -Ei 'postgres|pgpro' || echo "другого PostgreSQL нет"
```

**Шаг 2. Локаль — до установки:**

```bash
locale -a | grep -Ei 'en_US|ru_RU'                   # что уже сгенерировано
locale                                               # текущая локаль сеанса; C.UTF-8 или POSIX — не годится
sudo locale-gen en_US.UTF-8                          # сгенерировать нужную локаль
sudo localectl set-locale LANG=en_US.UTF-8           # системная локаль (то же делает update-locale LANG=…)
```

Выйти из сеанса и войти заново. Проверка: `locale | grep '^LANG='` → `LANG=en_US.UTF-8`, и в выводе `locale` нет `LC_ALL=C`.

Почему это важно **[пакет]**: если локаль сеанса — `C`, `POSIX` или `C.UTF-8` (её скрипт приравнивает к `C`), `pg-setup` перебирает запасной список `ru_RU.UTF-8`, `en_US.UTF-8`, `kk_KZ.UTF-8`, `tr_TR.UTF-8` и берёт первую сгенерированную (точный порядок действий — раздел 7). На машине, где есть и русская, и английская локали, без явного `LANG=en_US.UTF-8` кластер получится **русским**. Для русскоязычных баз, наоборот, достаточно сгенерировать `ru_RU.UTF-8`.

**Шаг 3. Репозиторий:**

```bash
cd /tmp
wget https://repo.postgrespro.ru/1c/1c-16/keys/pgpro-repo-add.sh
less pgpro-repo-add.sh                               # просмотреть
sudo sh pgpro-repo-add.sh
```

Проверка: `cat /etc/apt/sources.list.d/postgresql-1c-16.list` (строка `deb https://repo.postgres.ru/1c/1c-16/ubuntu <кодовое имя> main`) и `apt-cache policy postgrespro-1c-16` (кандидат `16.14-1.<кодовое имя>`).

**Шаг 4. Установка:**

```bash
apt-get -s install postgrespro-1c-16 | grep -E '^(Inst|Remv)'   # пробный прогон: нет ли строк Remv с чужими пакетами
sudo LANG=en_US.UTF-8 apt-get install -y postgrespro-1c-16      # LANG передан явно — от него зависит локаль кластера
```

Если в пробном прогоне есть строки `Remv` с `postgresql-*` — на машине стоит другой PostgreSQL, и быстрая установка его удалит. Тогда остановиться: нужна расширенная установка (`../postgresql/01-…`, раздел 5.2) и резервная копия существующих баз.

**Шаг 5. Проверка:**

```bash
systemctl status postgrespro-1c-16 --no-pager        # active (running), enabled
sudo -u postgres psql -c "select version()"
sudo -u postgres psql -c "\l"                        # столбцы Collate и Ctype — en_US.UTF-8, Encoding — UTF8
sudo -u postgres psql -Atc "show data_directory" -c "show port" -c "show listen_addresses" -c "show data_checksums"
```

Ожидается: каталог данных `/var/lib/pgpro/1c-16/data`, порт 5432, контрольные суммы `on` **[док.]**.

**Шаг 6. Пароль пользователя `postgres`** (нужен серверу 1С для подключения по TCP):

```bash
sudo -u postgres psql
```

В psql: `\password postgres` (ввести пароль дважды), затем `\q`. Проверка входа по паролю: `psql -h 127.0.0.1 -U postgres -c "select 1"`.

**Шаг 7. Параметры, специфичные для 1С.** Быстрая установка их **не выставляет**: метапакет вызывает `pg-setup initdb` без параметров, и применяется только общий пресет `default.tune` (раздел 7; вывод сделан по коду пакетов, запуском не проверен). Сначала убедиться:

```bash
sudo tail -n 60 /var/lib/pgpro/1c-16/data/postgresql.conf       # в блоке pgpro_tune перечислены использованные пресеты
sudo -u postgres psql -Atc "show max_locks_per_transaction" -c "show standard_conforming_strings" -c "show shared_preload_libraries"
```

Если там `64`, `on` и пусто — параметры 1С не заданы. Применить пресет `1c.tune` и сразу поправить два его значения, лишних для сервера, где 1С и PostgreSQL стоят на одной машине (перезапуск обрывает сеансы — выполнять до ввода в работу или в согласованное окно):

```bash
sudo cp -a /var/lib/pgpro/1c-16/data/postgresql.conf /var/lib/pgpro/1c-16/data/postgresql.conf.bak
sudo -u postgres /opt/pgpro/1c-16/bin/pgpro_tune -D /var/lib/pgpro/1c-16/data --no-default -P /opt/pgpro/1c-16/share/1c.tune
sudo /opt/pgpro/1c-16/bin/pg-setup set listen_addresses "'localhost'"   # 1c.tune ставит '*'; для отдельного сервера 1С — см. guides/03
sudo /opt/pgpro/1c-16/bin/pg-setup set work_mem 64MB                    # 1c.tune ставит 512MB; значение подобрать по postgresql/02
sudo systemctl restart postgrespro-1c-16
sudo -u postgres psql -Atc "show max_locks_per_transaction" -c "show standard_conforming_strings" -c "show shared_preload_libraries" -c "show listen_addresses" -c "show work_mem"
```

Ожидается: `256`, `off`, `plantuner`, `localhost`, `64MB`. Ключ `--no-default` нужен, чтобы утилита не дописала общий пресет второй раз; путь к пресету задан полностью, как в примере документации. Если служба не запустилась — `journalctl -u postgrespro-1c-16 -n 50` и вернуть копию `postgresql.conf.bak`. Те же параметры можно задать и вручную, без пресета — список в `../postgresql/01-…`, раздел «Кратко», пункт 15, и в разделе 5 ниже.

**Шаг 8. Дальше:**

- сервер 1С на той же машине подключается к `localhost` — правила доступа по умолчанию (`peer` для локального сокета, `md5` для TCP) это уже позволяют **[док., `pg-setup`]**;
- **проверить сетевую открытость:** если `show listen_addresses` вернул `*`, сервер слушает все интерфейсы, а в `pg_hba.conf` может стоять правило для `0.0.0.0/0` (так бывает, когда `1c.tune` применён уже при создании кластера) — что с этим делать, раздел 7, замечание 1;
- сервер 1С на другой машине — `listen_addresses`, строка в `pg_hba.conf`, межсетевой экран: `03-1c-i-postgresql-na-raznyh-hostah.md`;
- журнал сервера лежит в `/var/lib/pgpro/1c-16/data/log` и сам не очищается — настроить очистку (раздел 7, замечание 4);
- настройка параметров под 1С — раздел 5 ниже и `../postgresql/02-postgresql-conf-tyuning-dlya-1c.md`;
- резервное копирование — `../postgresql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md`;
- чтобы минорное обновление СУБД не случилось само при `apt upgrade` — фиксация пакетов (`../postgresql/01-…`, раздел 5.6).

### Если кластер создался не в той локали

Признак: в выводе `\l` не та локаль. **Пересоздание кластера уничтожает все базы в нём** — выполнять, только пока баз 1С в кластере нет (иначе сначала `pg_dump` каждой базы):

```bash
sudo systemctl stop postgrespro-1c-16
sudo mv /var/lib/pgpro/1c-16/data /var/lib/pgpro/1c-16/data.wrong-locale
sudo LANG=en_US.UTF-8 /opt/pgpro/1c-16/bin/pg-setup initdb
sudo /opt/pgpro/1c-16/bin/pg-setup service start
sudo -u postgres psql -c "\l"
```

После пересоздания пароль `postgres` задаётся заново; старый каталог удалить, когда всё проверено.

Журнал создания кластера — `/var/lib/pgpro/1c-16/initdb.data.log`; при неудаче `pg-setup` сам удаляет каталог данных и файл `/etc/default/postgrespro-1c-16` и пишет `failed, see <журнал>` **[пакет]**. Кластера в кодировке `SQL_ASCII` при установке через `pg-setup` не получится: при локали `C` скрипт подбирает UTF-8-локаль сам, а если ни одной нет — завершается с `No suitable locale found. Please install/create some UTF-8 locale` **[пакет]**. Такой кластер возможен только при прямом вызове `initdb` **[док., `initdb`]**.

### Типичные сбои при установке

| Что видно | Причина | Что делать |
|---|---|---|
| `This script should be run as root…` | скрипт запущен без `sudo` | `sudo sh pgpro-repo-add.sh` |
| `Version … of Ubuntu distribution is not supported for architecture amd64` | для этого выпуска Ubuntu ветка не собирается (например, 16 на Ubuntu 26.04) | выбрать ветку 17 или 18 |
| `You have already added repository…`, код возврата 2 | файл `/etc/apt/sources.list.d/postgresql-1c-16.list` уже существует | ничего не делать либо удалить файл и запустить скрипт заново |
| `SSL certificate verification error…` | устаревший набор корневых сертификатов | `sudo apt-get install --reinstall ca-certificates`, проверить дату и время |
| `wget` не может выйти в интернет | нет доступа или нужен прокси | переменная `https_proxy`; **SOCKS5-прокси `wget` не поддерживает** **[док., 18.1.2]** |
| apt предлагает удалить `postgresql-common` и пакеты PostgreSQL | метапакет конфликтует с `postgresql-common`, `postgrespro-common`, `postgresql-common-pro-1c` **[репо, `Packages`]** | расширенная установка вместо быстрой |

---

## 4. Документация сборки: установка в Linux (глава «Установка из двоичных пакетов»)

Адреса: `https://repo.postgrespro.ru/doc/pg1c/16/ru/html/binary-installation-on-linux.html` (в версии 16 — раздел 18.1, в версии 18 — раздел 17.1; текст отличается только списком ОС). Там же лежат PDF и EPUB всей документации. Документация вложена и в пакеты `postgrespro-1c-16-docs` (английская) и `postgrespro-1c-16-docs-ru` (русская).

- **Минимальные требования:** процессор 1 ГГц, 1 ГБ ОЗУ, 1 ГБ диска (это минимум для запуска, а не для работы 1С).
- **Два режима:** быстрая установка (пакет `postgrespro-1c-NN`) и расширенная (отдельные пакеты, ручная настройка). Расширенная обязательна при нескольких версиях или продуктах PostgreSQL на машине, при обновлении с другой версии и миграции, при управлении сервером средствами высокой доступности (например, pacemaker).
- **Быстрая установка:** при установке метапакета «могут быть удалены существующие инсталляции» PostgreSQL; пакет нельзя использовать при обновлении и миграции. Конфигурация кластера настраивается под устанавливаемый продукт; для иной настройки — расширенная установка и аргумент `tune` команды `pg-setup initdb`.
- **Раскладка:** программы — `/opt/pgpro/1c-NN/bin`; кластер по умолчанию — `/var/lib/pgpro/1c-NN/data`; путь к каталогу данных сохраняется в `/etc/default/postgrespro-1c-NN` (на странице `pg-setup` тот же файл записан как `/etc/default/postgrespro-1C-NN` — это неточность документации: в пакете везде строчная буква **[пакет]**). В том же файле задаётся `PG_OOM_ADJUST_VALUE`.
- **Служба:** `postgrespro-1c-NN` — файл `/lib/systemd/system/postgrespro-1c-NN.service`; в Debian и Ubuntu есть и SysV-скрипт `/etc/init.d/postgrespro-1c-NN`. Сервер работает от пользователя `postgres`.
- **Контрольные суммы данных включены по умолчанию** — их включает `pg-setup initdb`, в том числе при быстрой установке. Отключаются ключом `--no-data-checksums` у `pg-setup initdb`; у самого `initdb` 16 такого ключа нет, суммы там включает `-k` (уточнено 19.10.2026 по документации сборки 16).
- **Часовые пояса:** используется системный пакет `tzdata` — его нужно держать обновлённым.

### Пакеты

| Пакет | Содержимое |
|---|---|
| `postgrespro-1c-NN` | метапакет быстрой установки |
| `postgrespro-1c-NN-server` | сервер и PL/pgSQL; содержит `pg-setup` |
| `postgrespro-1c-NN-client` | `psql`, `pg_dump` и другие клиентские программы; содержит `pg-wrapper` |
| `postgrespro-1c-NN-libs` | `libpq` и библиотеки ECPG |
| `postgrespro-1c-NN-contrib` | дополнительные модули; в Debian и Ubuntu сервер зависит от него, ставятся вместе |
| `postgrespro-1c-NN-dev` | заголовочные файлы и библиотеки для разработки (в RHEL — `-devel`) |
| `postgrespro-1c-NN-plperl`, `-plpython3`, `-pltcl` | серверные языки |
| `postgrespro-1c-NN-jit` | JIT-компиляция (для 1С не нужна: приложение K рекомендует `jit = off`) |
| `postgrespro-1c-NN-docs`, `-docs-ru` | документация |
| `*-dbgsym` | отладочные символы **[репо]** (в документации названы `-dbg`) |

Минимум для сервера: `-server`, `-client`, `-libs` (в Ubuntu ещё `-contrib`).

### `pg-setup` (от `root`)

| Команда | Действие |
|---|---|
| `pg-setup initdb [параметры_initdb]` | создать кластер от имени `postgres`: каталог `/var/lib/pgpro/1c-NN/data`, контрольные суммы, `auth-local = peer`, `auth-host = md5`, локаль из `LANG` |
| `pg-setup find-free-port` | найти свободный порт |
| `pg-setup set-server-port <порт>` | задать порт (по умолчанию 5432) |
| `pg-setup set <параметр> <значение>` | записать параметр в `postgresql.conf` (значение из `postgresql.auto.conf` при этом удаляется) |
| `pg-setup service enable \| disable \| start \| stop \| condrestart \| status` | управление службой |

`pg-setup` управляет только одним кластером и подбирает параметры в расчёте на то, что машина занята одним сервером БД. Для второго экземпляра документация (18.1.7) предлагает `initdb` в другой каталог, другой порт и копию файла службы с изменённым путём к данным.

### `pg-wrapper` (от `root`, пакет `-client`)

`pg-wrapper links update` — создать ссылки на программы в стандартном пути и подключить man-страницы; `pg-wrapper links remove` — убрать. При быстрой установке вызывается автоматически. Если в системе есть `update-alternatives`, программы регистрируются как альтернативы; без него ссылки создаются только при отсутствии конфликтов.

### `pgpro_tune` и пресеты

- Утилита автонастройки: собирает сведения о машине и дописывает параметры **отдельным блоком в конец `postgresql.conf`** (с комментарием, какие пресеты использованы). **При `initdb` запускается по умолчанию**; `initdb --no-tune` отключает, `initdb --tune=<параметры>` передаёт параметры утилите; есть переменная окружения `PGPRO_TUNE`.
- Пресеты: `default.tune` (основной, зависит от редакции и версии сервера), `regress.tune` (для тестов), **`1c.tune`** («параметры, специфичные для 1С, некоторые из которых требуют установки `plantuner`»), `extensions.tune`.
- Синтаксис: `pgpro_tune [параметры] -D <каталог данных> <имя пресета>`; пресет задаётся `-P <имя>` / `--preset=<имя>` либо последним аргументом; `--show` — список пресетов; `--no-default` — без стандартного пресета; `--config-file=<файл>` — другой файл конфигурации.
- Приложение K говорит о `1c.tune` как о том, что «можно также использовать» для быстрой настройки. Применён ли он при установке, документация не уточняет; по коду пакетов — **не применён**: быстрая установка вызывает `pg-setup initdb` без параметров (раздел 7; что именно записывают пресеты — там же). Убедиться на сервере:

```bash
sudo tail -n 60 /var/lib/pgpro/1c-16/data/postgresql.conf            # блок pgpro_tune: какие пресеты использованы
sudo -u postgres /opt/pgpro/1c-16/bin/pgpro_tune --show              # какие пресеты есть
```

Явное применение пресета (команда составлена по странице `pgpro_tune`, на сервере не выполнялась; перед запуском сохранить копию `postgresql.conf`, после — перезапустить службу в согласованное окно). **Прежде чем применять, прочитать раздел 7:** `1c.tune` ставит `work_mem = 512MB` и `listen_addresses = '*'` — оба значения стоит осознанно пересмотреть (полная последовательность с правкой этих двух значений и проверкой — раздел 3, шаг 7):

```bash
sudo cp -a /var/lib/pgpro/1c-16/data/postgresql.conf /var/lib/pgpro/1c-16/data/postgresql.conf.bak
sudo -u postgres /opt/pgpro/1c-16/bin/pgpro_tune -D /var/lib/pgpro/1c-16/data --no-default -P /opt/pgpro/1c-16/share/1c.tune
sudo systemctl restart postgrespro-1c-16
```

Формы `pg-setup initdb --tune=1c`, которая встречается в старых руководствах, в документации сборки нет.

### Обновление

- **Минорное** (16.13 → 16.14): выгрузка и восстановление не требуются **[док., замечания к выпуску 16.14]**; у некоторых выпусков есть оговорки (для 16.14 — «если обновляетесь с версии старше 16.10, см. замечания к 16.10»), поэтому перед обновлением читать «Замечания к выпускам» (`…/release.html`).
- **Мажорное** (16 → 17): базы разных основных версий и разных продуктов на базе PostgreSQL двоично несовместимы — нужен `pg_dumpall` либо `pg_upgrade` **[док., 18.4]**; новая версия ставится расширенной установкой рядом со старой. Порядок — `../postgresql/07-replikaciya-otkazoustojchivost-obnovlenie-versij.md`.
- После обновления модули должны быть той же сборки: при несовпадении ABI расширение выдаёт ошибку `ABI mismatch` **[док., 18.3]**.

### Антивирус

Документация не рекомендует антивирус на сервере СУБД; если он обязателен — исключить каталог данных, каталоги табличных пространств, каталог WAL и `/opt/pgpro/1c-NN/bin`.

---

## 5. Документация сборки: приложение K «Настройка PostgreSQL для решений 1С»

Адрес: `https://repo.postgrespro.ru/doc/pg1c/16/ru/html/config-one-c.html` (тексты версий 16 и 18 совпадают).

**K.1. Локаль.** Русская локаль должна быть установлена и активна у пользователя, создающего кластер; пример: `sudo dpkg-reconfigure locales`, `export LANG="ru_RU.UTF-8"`, `/opt/pgpro/1c-16/bin/pg-setup initdb`.

**K.2. Оборудование и ОС.** 8–512 ГБ ОЗУ, 4–256 ядер, RAID 0–1 или SSD; отключить гиперпоточность; отключить режим энергосбережения (иначе непредсказуемо растут задержки отклика); отключить подкачку для разделяемой памяти.

**K.3. Параметры сервера** (значения названы приблизительными — «начальная точка»):

| Параметр | Значение по документации |
|---|---|
| `max_connections` | 500–10000 (не менее 500) |
| `shared_buffers` | ОЗУ/4 |
| `temp_buffers` | 32–256MB |
| `work_mem` | ОЗУ/32…64 либо 32–256MB |
| `maintenance_work_mem` | ОЗУ/16…32, либо `work_mem` × 4, либо 256MB–4GB |
| `max_files_per_process` | 10000 |
| `bgwriter_delay` | 20ms |
| `bgwriter_lru_multiplier`, `bgwriter_lru_maxpages` | 4.0, 400 |
| `effective_io_concurrency` | 2 (для SSD — до нескольких сотен) |
| `max_parallel_workers_per_gather` | 0 |
| `fsync` | on (не отключать) |
| `synchronous_commit` | off |
| `checkpoint_timeout` | 15min |
| `min_wal_size`, `max_wal_size` | 512MB–4GB; вдвое больше `min_wal_size` |
| `commit_delay` | 1000 — только если больше 1000 транзакций в секунду |
| `effective_cache_size` | ОЗУ − `shared_buffers` |
| `random_page_cost` | 1.5–2.0 для RAID, 1.1–1.3 для SSD |
| `from_collapse_limit`, `join_collapse_limit` | 20, 20 |
| `enable_sorted_merge_join` | off (значение по умолчанию; параметр сборки) |
| `geqo`, `geqo_threshold` | on, 12 |
| `jit` | off |
| `autovacuum` | on |
| `autovacuum_max_workers` | от четверти до половины числа ядер, не менее 4 |
| `autovacuum_naptime` | 20s |
| `temp_tablespaces` | табличное пространство на отдельных быстрых дисках (сначала `CREATE TABLESPACE`) |
| `row_security` | off |
| `max_locks_per_transaction` | 256 |
| `standard_conforming_strings` | off |
| `escape_string_warning` | off |

Дополнительно: при сильной фрагментации памяти — переменная окружения `MALLOC_MMAP_THRESHOLD_=8192` для службы (в документации назван файл `/etc/systemd/system/postgresql.service`; для этой сборки правильнее дополнение к её собственной службе — `sudo systemctl edit postgrespro-1c-16` **[вывод]**); каталог `pg_stat_tmp` рекомендуют вынести в tmpfs (в PostgreSQL 15 и новее статистика хранится в разделяемой памяти, совет относится к старым версиям **[вывод]**).

Эти значения в основном совпадают с рекомендациями ИТС; сравнение и расчёт под свою машину — `../postgresql/02-postgresql-conf-tyuning-dlya-1c.md` и `../its-metod/pg-nastrojki-postgresql-dlya-1c.md`. При расхождении с ИТС для платформы 1С приоритет у ИТС.

**K.4. Модули.**

- Встроены и включены по умолчанию, настройки не требуют: **`mchar`** (типы `mchar`, `mvarchar` — сравнение без учёта регистра, обработка концевых пробелов как в MS SQL, на библиотеке ICU), **`fulleq`** (оператор `==`, для которого `NULL == NULL` истинно), **`fasttrun`** (функция `fasttruncate()` — нетранзакционное усечение временных таблиц без разрастания `pg_class`).
- **`dbcopies_decoding`** — модуль 1С для обновления копий базы данных (механизм из `../its-docs/dev-gl26-kopii-bazy-dannyh.md`); нужен `wal_level = logical`.
- **`plantuner`** — `shared_preload_libraries = 'plantuner'` и `plantuner.fix_empty_table = on` (улучшает планы для только что созданных пустых таблиц).
- **`online_analyze`** — «не рекомендуется использовать с современными версиями 1С»; включать только если статистика временных таблиц систематически неверна (параметры: `online_analyze.enable = on`, `threshold = 50`, `scale_factor = 0.1`, `verbose = off`, `table_type = 'temporary'`, `min_interval = 10000`).

Прочие модули сборки (приложение F): `pg_stat_statements`, `auto_explain`, `auto_dump`, `pg_buffercache`, `pg_prewarm`, `pgstattuple`, `amcheck`, `pg_trgm`, `postgres_fdw` и другие стандартные. В 16-й ветке есть также `aqo`, `adminpack`, `old_snapshot`; в 18-й их нет, зато есть `pg_logicalinspect` и `pg_overexplain`. **`pgpro_stats` в перечне нет.** Список на сервере: `SELECT name, default_version FROM pg_available_extensions ORDER BY 1;`.

---

## 6. Что проверить на своём сервере

Команды только читают состояние (кроме помеченных в тексте выше):

```bash
cat /etc/default/postgrespro-1c-16                    # ожидается PGDATA=/var/lib/pgpro/1c-16/data
systemctl is-enabled postgrespro-1c-16                # включён ли автозапуск
sudo -u postgres psql -Atc "show listen_addresses"    # ожидается localhost; '*' — применён 1c.tune, сервер слушает все интерфейсы
sudo grep -v '^\s*#' /var/lib/pgpro/1c-16/data/pg_hba.conf | grep -v '^\s*$'   # нет ли строки host all all 0.0.0.0/0
sudo du -sh /var/lib/pgpro/1c-16/data/log             # сколько занял журнал сервера
sudo -u postgres psql -Atc "show unix_socket_directories" -c "show log_destination" -c "show logging_collector" -c "show shared_preload_libraries"
sudo tail -n 60 /var/lib/pgpro/1c-16/data/postgresql.conf
sudo -u postgres psql -c "select datname, pg_encoding_to_char(encoding) enc, datlocprovider, datcollate, datctype from pg_database"
dpkg -l 'postgrespro-1c-16*' | grep '^ii'
```

По документации провайдер локали при `initdb` по умолчанию — `libc` (ICU включается ключом `--locale-provider=icu`); фактическое значение покажет столбец `datlocprovider`.

Главное, что стоит подтвердить на сервере: **какие пресеты `pgpro_tune` применились при установке** (блок в конце `postgresql.conf`). По коду пакетов — только `default.tune`, то есть параметры для 1С после быстрой установки не заданы (раздел 3, шаг 7). Остальные открытые вопросы — `06-otkrytye-voprosy.md`, сценарий сбора — `05-sbor-dannyh-s-servera.md`.

---

## 7. Что показал разбор пакетов `postgrespro-1c-16-server` и `postgrespro-1c-16` (16.14-1.noble)

Серверный пакет (7 222 670 байт) скачан 11.10.2026 из `repo.postgrespro.ru/1c/1c-16/ubuntu/pool/main/p/postgrespro-1c-16/`; SHA256 `821bfd5b…645db9` совпал с индексом `Packages`. Читались только текстовые файлы; в двоичных `initdb` и `pgpro_tune` искались строки. Для других веток и выпусков Ubuntu содержимое может отличаться — сверять на сервере (`dpkg -L`, `systemctl cat`).

### Служба `/lib/systemd/system/postgrespro-1c-16.service`

| Параметр | Значение | Что это значит |
|---|---|---|
| `Type` | `notify` | systemd ждёт сигнала готовности от сервера |
| `User`, `Group` | `postgres` | — |
| `OOMScoreAdjust` | `-1000` | postmaster защищён от OOM killer; для дочерних процессов — `PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj`, `PG_OOM_ADJUST_VALUE=0` |
| `EnvironmentFile` | `/etc/default/postgrespro-1c-16` | файл обязателен: без него служба не запустится |
| `ExecStartPre` | `check-db-dir ${PGDATA}` | проверка, что каталог данных инициализирован и его версия — 16 |
| `ExecStart` | `/opt/pgpro/1c-16/bin/postgres -D ${PGDATA}` | — |
| `ExecReload` | `/bin/kill -HUP $MAINPID` | `systemctl reload postgrespro-1c-16` перечитывает конфигурацию |
| `KillMode`, `KillSignal` | `mixed`, `SIGINT` | остановка службы — «быстрое» завершение (fast shutdown): сеансы обрываются, транзакции откатываются |
| `TimeoutStartSec`, `TimeoutStopSec` | `0` (без предела), `1h` | долгий запуск после сбоя systemd не прервёт |

Чего в службе **нет**: `Restart=` (после аварийного завершения сервер сам не поднимется), `LimitNOFILE=`, директив изоляции. Менять службу — только дополнением: `sudo systemctl edit postgrespro-1c-16` (сам файл перезаписывается при обновлении пакета).

Сообщения `check-db-dir` при неудачном запуске: `"<каталог>" is missing or empty. Use "…/pg-setup initdb" to initialize the database cluster.`; `An old version of the database format was found. You need to dump and reload before using Postgres Pro 1c-16.`

### Скрипт `pg-setup`: как на самом деле выбирается локаль

1. Если локаль сеанса 7-битная (`locale charmap` = `ANSI_X3.4-1968`, то есть `C` или `POSIX`) — берётся локаль входа пользователя, вызвавшего `sudo` (переменная `SUDO_USER`), а если её нет — пользователя `postgres`.
2. Если `LANG` пуста, а `LC_CTYPE` задана — `LANG` приравнивается к `LC_CTYPE`.
3. Локаль `C` с кодировкой (`C.UTF-8`) сбрасывается в `C`.
4. Если локаль всё ещё 7-битная — по очереди пробуются **`ru_RU.UTF-8`, `en_US.UTF-8`, `kk_KZ.UTF-8`, `tr_TR.UTF-8`**; берётся первая, которая сгенерирована в системе.
5. Если не подошла ни одна — любая UTF-8-локаль из `locale -a`, кроме `C.UTF-8`.
6. Если UTF-8-локалей нет вовсе — ошибка `No suitable locale found. Please install/create some UTF-8 locale`, каталог данных и файл `/etc/default/postgrespro-1c-16` удаляются.
7. `initdb` запускается от `postgres` с `LANG=<выбранная локаль>`; `LC_CTYPE` и `LC_COLLATE` приравнены к ней.

Вывод: при явной UTF-8-локали в `LANG` (`en_US.UTF-8`, `ru_RU.UTF-8`) используется именно она; подбор включается только при `C`, `POSIX`, `C.UTF-8`.

### Скрипт `pg-setup`: остальное

- Файл `/etc/default/postgrespro-1c-16` содержит одну строку `PGDATA=<каталог>`. Каталог из `-D` / `--pgdata` записывается туда, только если файла ещё нет; если файл есть и указывает на другой каталог — отказ с советом вызывать `initdb` напрямую и настраивать службу вручную. Непустой каталог — ошибка `Data directory … is not empty!`.
- `initdb` вызывается с `--auth-local=peer --auth-host=md5` (оба можно переопределить ключами `--auth-local=…`, `--auth-host=…`); дополнительные ключи можно передать и через переменную окружения `PGSETUP_INITDB_OPTIONS`.
- Журнал создания кластера — `/var/lib/pgpro/1c-16/initdb.data.log`.
- После `initdb` скрипт создаёт каталог `data/log` и **включает `logging_collector = on`**. Журнал сервера пишется в `/var/lib/pgpro/1c-16/data/log/postgresql-<дата>_<время>.log`; новый файл — раз в сутки или по достижении 10 МБ; **старые файлы не удаляются** (см. замечание ниже).
- Порт: скрипт ищет свободный, начиная с 5432, проверяя файл сокета `/tmp/.s.PGSQL.<порт>` — то есть **каталог Unix-сокета этой сборки — `/tmp`** (то же в образце конфигурации: `unix_socket_directories = '/tmp'`). Клиенты из пакетов Ubuntu ищут сокет в `/var/run/postgresql` и без `-h /tmp` или `-h 127.0.0.1` не подключатся; `psql` самой сборки подключается сразу.
- **Если после `initdb` в `postgresql.conf` стоит `listen_addresses = '*'`, скрипт дописывает в `pg_hba.conf` строку `host all all 0.0.0.0/0 md5`** — доступ по паролю с любого адреса.
- Недокументированная команда: `pg-setup psql [ключи]` — запускает `psql` от пользователя `postgres` с портом из конфигурации.
- `pg-setup service …` требует наличия `/etc/default/postgrespro-1c-16`, иначе сообщает `Default database not found. Use … initdb to create it`.

### Пресеты `pgpro_tune`

`default.tune` — выполняется при `initdb` всегда (если не указан `--no-tune`):

| Что | Значение |
|---|---|
| `max_connections` | 250 |
| `shared_buffers` | ОЗУ/4 |
| `effective_cache_size` | ОЗУ − `shared_buffers` |
| `work_mem`, `temp_buffers` | 32MB, 16MB |
| `maintenance_work_mem` | ОЗУ/16, не более 12 ГБ |
| `autovacuum_work_mem` | половина `maintenance_work_mem`, не более 1 ГБ |
| `autovacuum_max_workers` | половина числа ядер, от 4 до 100; `vacuum_cost_limit` = число процессов × 100 |
| `autovacuum_naptime` | 20s |
| `autovacuum_vacuum_scale_factor`, `autovacuum_vacuum_insert_scale_factor`, `autovacuum_analyze_scale_factor` | 0.01, 0.01, 0.005 |
| `bgwriter_delay`, `bgwriter_lru_multiplier`, `bgwriter_lru_maxpages` | 20ms, 4.0, 4000 |
| `default_statistics_target` | 800 |
| `track_activity_query_size` | 10kB |
| `wal_compression`, `default_toast_compression` | lz4, lz4 |
| `min_wal_size`, `max_wal_size` | 2GB, 4GB |
| `effective_io_concurrency`, `random_page_cost` | **500 и 1.1 — в расчёте на NVMe SSD**; в файле рядом закомментированы варианты для SATA SSD (200 и 1.3) и HDD (1 и 4.0) |
| `jit` | off |
| `log_lock_waits`, `log_connections`, `log_disconnections` | on, on, on |

Объём памяти берётся из `/proc/meminfo` с учётом ограничений cgroup (`memory.high`, `memory.max`).

`1c.tune` — параметры для 1С:

| Что | Значение |
|---|---|
| `work_mem`, `temp_buffers` | **512MB**, 256MB |
| `listen_addresses` | **`'*'`** |
| `shared_preload_libraries` | добавляется `plantuner`; `plantuner.fix_empty_table = on` |
| `max_locks_per_transaction` | 256 |
| `max_files_per_process` | 10000 |
| `max_parallel_workers_per_gather` | 0 |
| `checkpoint_timeout` | 15min |
| `commit_delay` | 1000 |
| `standard_conforming_strings`, `escape_string_warning` | off, off |
| `enable_sorted_merge_join` | off |
| `from_collapse_limit`, `join_collapse_limit` | 20, 20 |
| `hash_mem_multiplier` | 4 |
| `row_security` | off |

Параметры `skip_temp_rel_lock`, `enable_temp_memory_catalog`, `planner_upper_limit_estimation` в `1c.tune` записываются только для редакции Enterprise — в бесплатной сборке их не будет. `extensions.tune` для этой сборки подключает `pg_stat_statements` (`pg_stat_statements.max` — от числа соединений, `track = all`); `pgpro_stats` — только для Enterprise.

### Метапакет `postgrespro-1c-16` и вопрос «применяется ли `1c.tune` сам»

Метапакет (3 144 байта, SHA256 совпал с индексом) содержит только скрипты. Его `postinst` **при первой установке** делает ровно следующее:

1. `pg-wrapper links update` — ссылки на программы в `PATH`;
2. если в `/var/lib/pgpro/1c-16/data` ещё нет кластера: `pg-setup find-free-port`, затем **`pg-setup initdb` без единого параметра**; если свободный порт оказался не 5432 — `pg-setup set-server-port <порт>` с сообщением `Set 1c-16 PGPORT to <порт>`;
3. `pg-setup service enable` и `pg-setup service start`.

При обновлении метапакета скрипт не делает ничего; если кластер в каталоге уже есть, `initdb` пропускается — существующие данные не затрагиваются. `prerm` при удалении вызывает `pg-wrapper links remove`.

Как `initdb` вызывает автонастройку (строка в двоичном файле): `"<путь>/pgpro_tune" <содержимое ключа --tune> -D <каталог данных>`. При пустом `--tune` утилита получает только каталог данных и выполняет один стандартный пресет `default.tune`.

**Вывод: при быстрой установке `1c.tune` не применяется** — в `postgresql.conf` попадает только `default.tune`, а параметры для 1С (`max_locks_per_transaction = 256`, `standard_conforming_strings = off`, `plantuner` и остальные из таблицы выше) нужно применить отдельно (раздел 3, шаг 7). Вывод сделан по тексту скриптов и строкам двоичных файлов, запуском не проверен; на сервере он проверяется однозначно — по блоку `# The following presets were used:` в конце `postgresql.conf`.

Попутно: в `pgpro_tune` есть шаблон имени `%s.tune`, а параметры из `--tune` подставляются перед `-D` как есть. Поэтому старая форма `pg-setup initdb --tune=1c`, вероятнее всего, по-прежнему работает (слово `1c` становится именем пресета и дополняется до `1c.tune`) — это правдоподобное объяснение, но не проверенный факт. Именно на такой случай рассчитана ветка `pg-setup`, дописывающая правило в `pg_hba.conf` при `listen_addresses = '*'`.

Как опознать сборку на работающем сервере: `select version()` возвращает строку вида `PostgreSQL 16.14 on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit`; дополнительно есть параметры `show pgpro_version;` и `show pgpro_edition;`.

Мелкое расхождение: приложение K называет `enable_sorted_merge_join = off` значением по умолчанию, а в образце конфигурации пакета указано `#enable_sorted_merge_join = on`; `1c.tune` в любом случае ставит `off` явно.

### Замечания для эксплуатации **[вывод по содержимому пакета]**

1. **Сетевой доступ.** После быстрой установки сервер слушает только `localhost` (умолчание; `1c.tune` не применён). Если же `1c.tune` применён **при создании кластера** (ключом `--tune`), сервер слушает все интерфейсы, а `pg_hba.conf` пускает по паролю с любого адреса. Когда сервер 1С стоит на той же машине, это лишнее: вернуть `listen_addresses = 'localhost'` и убрать строку `0.0.0.0/0` либо закрыть порт 5432 межсетевым экраном (`../linux/08-set-ssh-firewall.md`). Если `1c.tune` применяется позже вручную, `listen_addresses` станет `'*'`, но `pg_hba.conf` не изменится — подключения извне отклоняются, пока правило не добавлено; `listen_addresses` всё равно лучше вернуть (раздел 3, шаг 7).
2. **`work_mem = 512MB`** из `1c.tune` — значение на одну операцию сортировки или хеширования в каждом сеансе; при сотне сеансов 1С на машине с небольшой памятью это риск исчерпания ОЗУ. Приложение K той же документации называет диапазон 32–256MB. Подбирать по `../postgresql/02-postgresql-conf-tyuning-dlya-1c.md`.
3. **Диски.** `random_page_cost = 1.1` и `effective_io_concurrency = 500` рассчитаны на NVMe; для виртуальной машины на обычных дисках значения нужно поднять и опустить соответственно (подсказки есть в самом `postgresql.conf`).
4. **Журнал сервера растёт без ограничения:** файлы в `data/log` не удаляются, а `log_connections` и `log_disconnections` включены — при работе 1С записей много. Нужна регулярная очистка (например, `find /var/lib/pgpro/1c-16/data/log -name 'postgresql-*.log' -mtime +14 -delete` от `postgres` по расписанию) либо схема с перезаписью (`log_filename = 'postgresql-%a.log'`, `log_truncate_on_rotation = on`). Каталог журнала лежит внутри каталога данных и попадает в файловые резервные копии.
5. **Обновление пакета перезапускает сервер.** Скрипт `postinst` при настройке пакета выполняет `pg-setup service condrestart` — работающий сервер будет перезапущен сразу при `apt upgrade`, сеансы 1С оборвутся. Чтобы этого не происходило, либо держать пакеты зафиксированными (`apt-mark hold`), либо добавить в `/etc/default/postgrespro-1c-16` строку `ENABLE_ONLINE_UPGRADE=1` — тогда перезапуск после обновления выполняется вручную в согласованное окно.
6. **Автозапуск.** `postinst` серверного пакета при первой установке включает службу (`deb-systemd-helper enable`), хотя документация говорит, что при расширенной установке автозапуск выключен. Проверять `systemctl is-enabled postgrespro-1c-16`.
7. **Пользователь `postgres`** создаётся скриптом `preinst` как системный, с домашним каталогом `/var/lib/postgresql` и оболочкой `/bin/bash`; если пользователь уже есть, но оболочка у него нерабочая, она заменяется на `/bin/bash`.
8. **Удаление пакета не трогает данные:** `prerm` останавливает и отключает службу, `postrm` удаляет скрипт `/etc/init.d/postgrespro-1c-16`; каталог `/var/lib/pgpro/1c-16` и файл `/etc/default/postgrespro-1c-16` остаются.
9. **Модули 1С лежат в другом пакете.** В серверном пакете из расширений только `plpgsql`; `mchar`, `fulleq`, `fasttrun`, `plantuner` и прочие — в `postgrespro-1c-16-contrib`, от которого серверный пакет зависит. Зависит он также от `locales` и `ssl-cert`; в образце конфигурации `ssl = off`.
10. В каталоге `share` лежат образцы `small.conf.sample`, `medium.conf.sample`, `big.conf.sample` — они помечены версией 9.6 и для настройки не годятся.


## 8. Расширения для 1С в сборке: страницы приложения F документации (прочитаны 19.10.2026)

> Источник: документация «PostgreSQL для 1С» 16 (`https://repo.postgrespro.ru/doc/pg1c/16/ru/html/`): `mchar.html` (F.29), `fulleq.html` (F.21), `fasttrun.html` (F.19), `online-analyze.html` (F.30), `plantuner.html` (F.45), `dbcopies_decoding.html` (F.14), `auto-dump.html` (F.5), `one-c-additional-modules.html` (K.4), `typeconv-oper.html` (подраздел 10.2.1). Пересказ своими словами; имена и значения — как в документации.

### 8.1. Что включено само и что нужно включать

| Модуль | Что делает | Включение (K.4) |
|---|---|---|
| `mchar` | Типы `mchar` и `mvarchar` — аналоги `char`/`varchar` MS SQL. Подробности ниже | встроен, включён по умолчанию, настройки не требует |
| `fulleq` | Оператор `==`, который, как в MS SQL, даёт TRUE при двух NULL | встроен, включён по умолчанию |
| `fasttrun` | Функция `fasttruncate('таблица')` — быстрое усечение временных таблиц без разрастания `pg_class` | встроен, включён по умолчанию |
| `dbcopies_decoding` | Модуль 1С для обновления копий баз данных (`../its-docs/dev-gl26-kopii-bazy-dannyh.md`) на логической репликации | включён по умолчанию; нужен `wal_level = logical`; подробности документация отсылает в поддержку 1С. Поставляется в пакете `postgrespro-1c-16-contrib`. **С PostgreSQL 16.15 (13.08.2026, CVE-2026-6471)** модули вывода логического декодирования ограничены параметром `output_plugin_libraries` (по умолчанию только `pgoutput`, `test_decoding`). После выхода сборки на основе 16.15 модуль 1С нужно будет вписать туда [PG, примечания к 16.15]. «Руководство разработчика», гл. 26.2, со сборками не из дистрибутива 1С допускает только «Версию 1» механизма копий (`../its-docs/dev-gl26-kopii-bazy-dannyh.md`) |
| `plantuner` | Указания планировщику: скрыть или принудительно показать индексы; исправление оценки для пустых таблиц | `shared_preload_libraries = 'plantuner'`, `plantuner.fix_empty_table = on` |
| `online_analyze` | Немедленный `ANALYZE` после `INSERT`/`UPDATE`/`DELETE`/`SELECT INTO`/`COPY` | **с современными версиями 1С не рекомендуется**; включать, только если оптимизатор систематически ошибается в числе строк |
| `auto_dump` | Выгрузка проблемных запросов с таблицами и планом для воспроизведения | `shared_preload_libraries = 'auto_dump'`, `auto_dump.enable = on`, `auto_dump.output_directory`, перезапуск |

### 8.2. `mchar` и `mvarchar`

- Совместимы с `CHAR`/`VARCHAR` MS SQL. Для сравнения и смены регистра используют ICU, поэтому ведут себя одинаково в разных ОС.
- Отличия от стандартных `char`/`varchar`:
  - сравнение без учёта регистра;
  - MS SQL-обработка концевых пробелов;
  - хранятся всегда как двухбайтовый Unicode — независимо от кодировки базы.
- Возможности:
  - функции `length()` и `substr()`, конкатенация `||`;
  - операторы `<`, `<=`, `=`, `>=`, `>` без учёта регистра и `&<`, `&<=`, `&=`, `&>=`, `&>` с учётом регистра;
  - неявное приведение между `mchar` и `mvarchar`;
  - индексы B-дерево и хеш;
  - `LIKE` (с индексной поддержкой), `SIMILAR TO`, `~`.
- Стандартное расширение `citext` похоже, но концевые пробелы обрабатывает не как MS SQL.
- **Риск при `pg_restore` и `pg_upgrade` (подраздел 10.2.1).** `pg_restore` работает с пустым `search_path` — фактически только `pg_catalog`. Операторы нестандартных типов, определённые в другой схеме, могут не найтись, и восстановление или `pg_upgrade` завершится ошибкой. Документация советует:
  - в своём коде писать такие операторы полностью: `OPERATOR(схема.оператор)`;
  - помнить, что конструкции без явного оператора сравнения (`IS [NOT] DISTINCT FROM`, `IN`/`NOT IN`, `NULLIF`, `JOIN … USING`, `NATURAL JOIN`, простой `CASE a WHEN b`) так не переписать — проверять их после восстановления или обновления.
  
  Для баз 1С это значит: **пробное восстановление дампа и пробный `pg_upgrade` на копии обязательны** (`../postgresql/04-…`, `../postgresql/07-…`). В какой схеме расширение ставит свои операторы в базах 1С, на сервере не проверялось ⚠ — запрос: `SELECT oprnamespace::regnamespace, oprname, oprleft::regtype, oprright::regtype FROM pg_operator WHERE oprleft = 'mchar'::regtype LIMIT 5;`.

### 8.3. `fulleq`

Оператор `==` определён для типов `bool`, `bytea`, `char`, `name`, `int2`, `int4`, `int8`, `int2vector`, `text`, `oid`, `xid`, `cid`, `oidvector`, `float4`, `float8`, `abstime`, `reltime`, `macaddr`, `inet`, `cidr`, `varchar`, `date`, `time`, `timestamp`, `timestamptz`, `interval`, `timetz`. Типы `abstime` и `reltime` из ванильного PostgreSQL удалены в версии 12; список, видимо, исторический ⚠.

### 8.4. `fasttrun`

`select fasttruncate('ИМЯ_ТАБЛИЦЫ');` — операция **нетранзакционная**: её нельзя откатить, и результат сразу виден во всех сеансах при любом уровне изоляции. Назначение — временные таблицы 1С. Без неё массовые `TRUNCATE` временных таблиц раздувают системный каталог `pg_class`.

### 8.5. `plantuner`

- Параметры:
  - `plantuner.disable_index` — список индексов, невидимых планировщику;
  - `plantuner.enable_index` — индексы, видимые, даже если скрыты первым параметром;
  - `plantuner.fix_empty_table` — для таблицы без блоков в файле обнулять оценку страниц и строк. Иначе планировщик считает только что созданную таблицу большой — это типичный случай для временных таблиц 1С.
- Загрузка — `LOAD 'plantuner'` в сеансе или `shared_preload_libraries`.
- Для 1С приложение K советует только `fix_empty_table = on`. `disable_index`/`enable_index` — средство разового расследования (проверить, станет ли запрос быстрее без индекса), а не постоянная настройка.

### 8.6. `online_analyze`

- Параметры и их значения по умолчанию в самом модуле (F.30):

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `online_analyze.enable` | `on` | включить |
| `online_analyze.verbose` | `on` | `ANALYZE VERBOSE`; в SQL имя писать в кавычках: `ALTER SYSTEM SET "online_analyze.verbose" = 'off';` (`verbose` — зарезервированное слово) |
| `online_analyze.scale_factor` | `0.1` | доля таблицы, после которой анализ (аналог `autovacuum_analyze_scale_factor`) |
| `online_analyze.threshold` | `50` | минимум изменённых строк (аналог `autovacuum_analyze_threshold`) |
| `online_analyze.min_interval` | `10000` | минимум мс между `ANALYZE` одной таблицы |
| `online_analyze.table_type` | `all` | `all` / `persistent` / `temporary` / `none` |
| `online_analyze.exclude_tables`, `include_tables` | пусто | исключить / включить таблицы (`include` важнее) |
| `online_analyze.local_tracking` | `off` | отслеживать временные таблицы внутри обслуживающего процесса |
| `online_analyze.lower_limit` | `0` | минимум строк в таблице для срабатывания |
| `online_analyze.capacity_threshold` | `100000` | сколько временных таблиц держать в локальном кеше |

- **Важно:** умолчание `enable = on` — это значение модуля после загрузки. Пока `online_analyze` нет в `shared_preload_libraries` (и не выполнен `LOAD`), модуль не работает.
- Приложение K (K.4.4) для случая, когда модуль всё же включают, даёт набор: `enable = on`, `threshold = 50`, `scale_factor = 0.1`, `verbose = off`, `table_type = 'temporary'`, `min_interval = 10000`.
- Рекомендации ИТС (`../its-metod/pg-nastrojki-postgresql-dlya-1c.md`) — `online_analyze.enable = off` в общем случае. Это согласуется с документацией сборки.
- В примере ИТС для отказоустойчивого кластера (`../its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md`) модуль включён — это частный пример, а не общая рекомендация.

### 8.7. `auto_dump` в сборке Postgres Pro — не то же, что `auto_dump` 1.1 из методичек ИТС

**Параметры по документации сборки 16 (F.5):**

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `auto_dump.enable` | off | включить |
| `auto_dump.output_directory` | — (обязательный) | каталог выгрузок; служба должна иметь права на чтение и запись |
| `auto_dump.dump_on_query_string` | `''` | выгружать запросы, содержащие фрагмент (без учёта регистра) |
| `auto_dump.dump_on_cancel` | off | выгружать запросы, отменённые СУБД (`pg_cancel_backend`, тайм-аут блокировки); не срабатывает на `idle_in_transaction_session_timeout` и `idle_session_timeout` |
| `auto_dump.dump_on_bad_plan` | off | выгружать при расхождении ожидаемого и фактического числа строк |
| `auto_dump.bad_plan_count_threshold` | 1000000 | порог абсолютной разницы; **0 — условие выполнено всегда** |
| `auto_dump.bad_plan_percent_threshold` | 100 | порог разницы в процентах (0–100); **0 — выполнено всегда**; срабатывает при превышении обоих порогов |
| `auto_dump.dump_on_time` | off | выгружать запросы дольше `auto_dump.timeout` |
| `auto_dump.timeout` | 0 | порог для `dump_on_time`, мс; **0 — выгружаются все запросы** |
| `auto_dump.dump_temporary_tables` / `dump_persistent_tables` / `dump_all_temp_tables` | off | какие таблицы класть в выгрузку |
| `auto_dump.dump_data` | off | выгружать содержимое (нужен ещё `dump_temporary_tables` или `dump_persistent_tables`) |
| `auto_dump.dump_indexes` | off | команды создания индексов |
| `auto_dump.dump_copy_data` | off | данные через `COPY TO` в отдельные TXT-файлы, иначе `INSERT` |
| `auto_dump.dump_query`, `dump_create`, `dump_plan` | off | текст запроса, `CREATE TABLE`, план |

- Порядок проверки условий: `dump_on_cancel` → `dump_on_query_string` → `dump_on_bad_plan` → `dump_on_time`.
- Ограничения:
  - только для отладки, не для постоянного мониторинга;
  - несовместим с `PREPARE TRANSACTION` при временных таблицах;
  - при `dump_all_temp_tables` не видит временные схемы автономных транзакций;
  - при `dump_data` читает таблицы и искажает статистику (лишние последовательные чтения).
- **Расхождение с базой.** Конспект методичек ИТС 6031/6039 (`../its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md`, разд. 3) описывает `auto_dump` 1.1 из сборки PostgreSQL **с патчами 1С** (`16.11-1.1C`, `17.7-1.1C`, `18.1-2.1C`):
  - параметры `auto_dump.dump_on_duration` и `auto_dump.data_format`;
  - функции `auto_dump_immediate`, `auto_dump_current`, `auto_dump_next`;
  - нулевые пороги bad plan там значат «не срабатывать».
  
  В документации сборки Postgres Pro 16 этого нет: вместо них `dump_on_time` + `timeout` и `dump_copy_data`, а нулевые пороги значат «срабатывать всегда».
  
  **У пользователя стоит сборка Postgres Pro.** Поэтому параметры брать из этой таблицы, а на сервере сверить: `SELECT name, setting FROM pg_settings WHERE name LIKE 'auto_dump.%';` — после загрузки библиотеки ⚠.