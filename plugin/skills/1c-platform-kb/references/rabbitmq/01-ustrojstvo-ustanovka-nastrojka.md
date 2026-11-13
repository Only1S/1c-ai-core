# RabbitMQ: устройство, версии, установка на Ubuntu и в Docker, базовая настройка

> **Официальные тексты по теме**: документация RabbitMQ 4.4 — исходники сайта в репозитории `rabbitmq/rabbitmq-website`, каталог `versioned_docs/version-4.4/` (`install-debian.md`, `which-erlang.md`, `configure.md`, `networking.md`, `production-checklist.md`, `vhosts.md`, `quorum-queues/index.md`, `amqp.md`, `management/index.md`, `metadata-store/index.md`, `memory.md`, `disk-alarms.md`); сроки поддержки — `docusaurus.config.js` того же репозитория (данные таблицы `rabbitmq.com/release-information`); примечания к выпуску 4.4.0 (GitHub, `rabbitmq/rabbitmq-server`); образ Docker — `docker-library/docs/rabbitmq/content.md`.

> Статус: написано 20.10.2026 по первоисточникам; на сервере не запускалось. Независимой сверки не было. Непроверенное помечено «⚠».

> Область: RabbitMQ как отдельный сервис для обмена 1С с другими системами и между базами — что это, какую версию брать, как поставить на Ubuntu Server из репозиториев команды RabbitMQ или в Docker, основные понятия и настройки. Безопасность, кластер, мониторинг, обновление — `02-…`; как 1С работает с RabbitMQ — `03-…`.

Пометки: **[RMQ-док 4.4]** — документация RabbitMQ 4.4; **[RMQ-код 4.4.0]** — исходный код `rabbitmq/rabbitmq-server`, метка `v4.4.0`; **[RMQ-RN 4.4.0]** — примечания к выпуску 4.4.0; **[RMQ-сайт]** — данные страницы Release Information (`docusaurus.config.js`); **[Docker Hub]** — описание официального образа; **[Ubuntu]** — packages.ubuntu.com; **[практика]**; **⚠**.

Условные обозначения: узел `rmq01.example.local` (10.0.0.41); виртуальный хост обмена 1С — `erp`; пользователи — `admin`, `erp-1c`, `site`.

## Кратко — главные факты

1. **Версии на 20.10.2026** [RMQ-сайт]: **4.4.0** (20.10.2026; бесплатная поддержка сообщества до 31.07.2027), **4.3.6** (16.09.2026; сообщество — до 31.01.2027). Ветка 4.2 у сообщества уже не поддерживается (до 31.07.2026), коммерческая поддержка Broadcom — до 30.06.2030. Более старые ветки не поддерживаются.
2. **Пакет `rabbitmq-server` из Ubuntu устарел:** в 24.04 — 3.12.1, в 22.04 — 3.9.27 [Ubuntu]. Документация прямо запрещает его для работы: версии отстают на годы, вне поддержки и не обновляются напрямую на современные [RMQ-док 4.4 `install-debian`]. Ставьте из **репозиториев команды RabbitMQ** (`deb1/deb2.rabbitmq.com`) вместе с их сборкой Erlang — для Ubuntu 22.04, 24.04 и 26.04 (26.04 пользуется репозиторием `noble`).
3. **Erlang:** 4.4.0 поддерживает Erlang 27, 28 и 29; Erlang 26 больше не поддерживается [RMQ-док 4.4 `which-erlang`; RMQ-RN 4.4.0].
4. **Протоколы из коробки:** AMQP 0-9-1 и **AMQP 1.0** (с 4.0 — встроенно, без модуля) на одном порту **5672** (TLS — 5671); MQTT, STOMP и их WebSocket-варианты — модулями; веб-интерфейс и HTTP API — модуль `rabbitmq_management`, порт **15672** [RMQ-док 4.4 `amqp`, `networking`].
5. **Пользователь `guest`/`guest` создаётся по умолчанию, но входит только с `localhost`** [RMQ-док 4.4 `install-debian`]. Создайте своих пользователей, `guest` удалите.
6. **Очереди для обмена — кворумные (`quorum`)**: реплицируемые, долговечные; зеркалирование классических очередей удалено в 4.0 [RMQ-док 4.4 `quorum-queues`]. У кворумной очереди с 4.0 **предел повторных доставок — 20**: сообщение, которое получатель 20 раз вернул, отбрасывается или уходит в «отстойник» (DLX) [там же].
7. **Метаданные кластера хранятся в Khepri** (Raft): с 4.2.0 — по умолчанию для новых установок; старые установки переходят включением флага `khepri_db` [RMQ-док 4.4 `metadata-store`].
8. **Сторожа ресурсов:** при занятости памяти выше 60% (`vm_memory_high_watermark.relative = 0.6`) и при свободном месте на диске меньше `disk_free_limit` (по умолчанию всего **50 МБ**) RabbitMQ **перестаёт принимать сообщения** от всех отправителей [RMQ-док 4.4 `production-checklist`]. Предел по диску в работе поднимайте до размера памяти и выше.
9. **Минимум для рабочего узла:** 4 ядра, 4 ГиБ ОЗУ, отдельно от других СУБД и дисково-нагруженных служб [RMQ-док 4.4 `production-checklist`]. Ни на ВМ с «PostgreSQL для 1С», ни на сервер 1С.
10. **Имя узла = `rabbit@<короткое имя хоста>`**, каталог данных называется по нему. Смена имени хоста «теряет» данные узла; в Docker имя хоста задавайте явно (`hostname:`) [RMQ-док 4.4 `configure`; Docker Hub].
11. **Дескрипторы файлов:** не меньше 50 000, в работе — до 500 000 [RMQ-док 4.4 `production-checklist`]; через дополнительный файл юнита `LimitNOFILE`.
12. **Кластер — нечётное число узлов (3, 5)**; один узел допустим для стенда и тестов [там же].

## 1. Понятия

| Понятие | Что это | Для обмена 1С |
|---|---|---|
| Виртуальный хост (vhost) | Изолированное пространство: свои обменники, очереди, права | Отдельный vhost на контур обмена (`erp`) |
| Обменник (exchange) | Точка, куда отправитель публикует; маршрутизирует по правилам | Отправитель знает только обменник и ключ маршрутизации |
| Тип обменника | `direct` (точное совпадение ключа), `fanout` (всем), `topic` (шаблоны `*`, `#`), `headers` | `topic`: ключи вида `erp.nomenclature.changed` |
| Очередь (queue) | Хранит сообщения до подтверждения получателем | По очереди на каждого получателя |
| Привязка (binding) | Связь «обменник → очередь» с ключом/шаблоном | Подписка получателя на нужные события |
| Тип очереди | `classic` (один узел), `quorum` (реплицируется, Raft), `stream` (журнал с повторным чтением) | `quorum` |
| Подтверждение получателя (ack) | Получатель сообщает «обработал» — сообщение удаляется | Подтверждать **после** записи в 1С |
| Подтверждение издателя (publisher confirm) | Брокер сообщает отправителю «принял и сохранил» | Удалять из очереди отправки 1С только после него |
| DLX (dead letter exchange) | Куда уходят отвергнутые, просроченные, превысившие предел доставок | «Отстойник» для разбора ошибок |
| Политика (policy) | Параметры очередей/обменников по шаблону имени | Предел доставок, DLX, длина очереди |

Главное отличие от Kafka: сообщение после подтверждения **удаляется** из очереди; перечитать прошлое нельзя (кроме потоков — streams). Зато есть гибкая маршрутизация, приоритеты, отложенная доставка (модулем), «отстойник». Сравнение — `../kafka/01-…`, раздел 1.2.

## 2. Версии и выбор

| Ветка | Последний выпуск | Поддержка сообщества до | Коммерческая поддержка до |
|---|---|---|---|
| 4.4 | 4.4.0 (20.10.2026) | 31.07.2027 | 31.10.2028 |
| 4.3 | 4.3.6 (16.09.2026) | 31.01.2027 | 30.04.2028 |
| 4.2 | 4.2.11 (16.09.2026) | 31.07.2026 (закончилась) | 30.06.2030 |
| 4.1 | 4.1.8 (22.01.2026) | 31.01.2026 (закончилась) | 30.04.2027 |

Источник — [RMQ-сайт]; даты коммерческой поддержки ориентировочные, официальные — на портале Broadcom. Выпуски, исправления которых выходят только для коммерческих клиентов, сообществу недоступны [практика ⚠].

**Что выбрать.** Новая установка — 4.4.0 или последний 4.3.x. Тег 4.3.7, упомянутый в примечаниях к 4.4.0, на 20.10.2026 в таблице выпусков ещё не значится ⚠.

Заметное в 4.4.0 [RMQ-RN 4.4.0]:

- полная поддержка Erlang 28 и 29, в том числе при поэтапном обновлении; если одновременно обновляются и RabbitMQ до 4.4.0, и Erlang до 28+, сначала советуют перейти на 4.3.7 или новее;
- заголовки AMQP 0-9-1 `x-amqp-1.0-*` и аннотации `x-basic-*`, которые писали узлы 3.13 и старше, больше не разбираются — касается только очень старых непрочитанных сообщений;
- строже проверка ответов OpenID Connect (для входа в веб-интерфейс через OAuth 2);
- `GET /api/auth/hash_password/{пароль}` заменён на `POST /api/auth/hash_password`.

## 3. Установка на Ubuntu из репозиториев команды RabbitMQ

### 3.1. Подготовка

- Отдельная ВМ: 4 ядра, 4–8 ГиБ ОЗУ, отдельный диск/том под `/var/lib/rabbitmq` [RMQ-док 4.4 `production-checklist`; размер тома — практика].
- Надёжное хранилище, не сетевая файловая система: документация предостерегает от NAS и советует изолировать хранилище [там же, разделы Storage].
- Имя хоста задать до установки и не менять: `hostnamectl set-hostname rmq01`; имя должно разрешаться (DNS или `/etc/hosts`).
- Время синхронизировать (chrony) — веб-интерфейс считает статистику по местному времени узлов [RMQ-док 4.4 `production-checklist`].

### 3.2. Репозитории и пакеты (Ubuntu 24.04 и 26.04)

Сценарий из документации [RMQ-док 4.4 `install-debian`, «Quick Start Script»]:

```bash
sudo apt-get install curl gnupg apt-transport-https -y
## ключ подписи команды RabbitMQ
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" \
  | sudo gpg --dearmor | sudo tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null
## репозитории Erlang и RabbitMQ
sudo tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-erlang/ubuntu/noble noble main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-erlang/ubuntu/noble noble main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-server/ubuntu/noble noble main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-server/ubuntu/noble noble main
EOF
sudo apt-get update -y
sudo apt-get install -y erlang-base \
  erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
  erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
  erlang-runtime-tools erlang-snmp erlang-ssl \
  erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl
sudo apt-get install rabbitmq-server -y --fix-missing
```

- Для 22.04 — те же строки с `jammy`; для 26.04 отдельного репозитория пока нет, используется `noble` [RMQ-док 4.4].
- Репозиторий Erlang команды RabbitMQ — только `amd64`; на `arm64` Erlang берут с Launchpad [там же].
- Отпечаток ключа сверьте с текущей страницей документации — ключи иногда меняют [практика].
- **Закрепите версию**, чтобы `apt upgrade` не обновил брокер через ветку без подготовки (обновление требует включения флагов, раздел `02-…`, 8):

```bash
apt-cache policy rabbitmq-server
sudo apt-mark hold rabbitmq-server erlang-base     # снимать перед плановым обновлением
```

Как работают `apt-mark hold` и `unattended-upgrades` — `../linux/04-…`.

### 3.3. Что установилось

| Что | Где | Источник |
|---|---|---|
| Служба | `rabbitmq-server.service` (`/usr/lib/systemd/system/`) | [RMQ-док 4.4 `install-debian`] |
| Настройки | `/etc/rabbitmq/rabbitmq.conf` (основной, формат `ключ = значение`), `/etc/rabbitmq/advanced.config` (Erlang-термы, редко), `/etc/rabbitmq/rabbitmq-env.conf` (переменные среды) | [RMQ-док 4.4 `configure`] |
| Данные | `/var/lib/rabbitmq/mnesia/rabbit@<хост>` (имя каталога историческое, и при Khepri) | [RMQ-док 4.4 `configure`, таблица переменных]; про Khepri — ⚠ |
| Журналы | `/var/log/rabbitmq/rabbit@<хост>.log` | [RMQ-док 4.4 `install-debian`] |
| Erlang-cookie | `/var/lib/rabbitmq/.erlang.cookie` (сервер), `~/.erlang.cookie` (утилиты) | [RMQ-док 4.4 `clustering`] |
| Пользователь ОС | `rabbitmq` | [RMQ-док 4.4] |

Файл `rabbitmq.conf` после установки может отсутствовать — создайте его сами ⚠ (наличие поставляемого примера — проверить `ls /etc/rabbitmq`).

### 3.4. Ограничение дескрипторов

```bash
sudo mkdir -p /etc/systemd/system/rabbitmq-server.service.d
sudo tee /etc/systemd/system/rabbitmq-server.service.d/limits.conf <<'EOF'
[Service]
LimitNOFILE=131072
EOF
sudo systemctl daemon-reload && sudo systemctl restart rabbitmq-server
sudo rabbitmq-diagnostics status | grep -A3 -i "file descriptors"
```

Способ — [RMQ-док 4.4 `install-debian`] (в примере документации 64000); ориентир «не меньше 50 000, до 500 000» — [RMQ-док 4.4 `production-checklist`]; формула: 95-й процентиль числа соединений × 2 + число очередей [там же].

### 3.5. Базовый `rabbitmq.conf`

```ini
# /etc/rabbitmq/rabbitmq.conf — одиночный узел обмена 1С
listeners.tcp.default = 5672
# веб-интерфейс и HTTP API (после rabbitmq-plugins enable rabbitmq_management)
management.tcp.port = 15672

# сторожа ресурсов
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 4GB

# очереди нового vhost по умолчанию — кворумные (можно задать и при создании vhost)
default_queue_type = quorum

# запрет анонимного входа (механизм ANONYMOUS)
auth_mechanisms.1 = PLAIN
auth_mechanisms.2 = AMQPLAIN
anonymous_login_user = none

# журнал
log.file.level = info
```

- `vm_memory_high_watermark.relative` — рекомендуемый диапазон 0,4–0,7; ОС должно оставаться не меньше 30% памяти [RMQ-док 4.4 `production-checklist`].
- `disk_free_limit.absolute` — рекомендуется не меньше порога памяти (для 4 ГиБ памяти — 4 ГБ) [там же; `disk-alarms`].
- `default_queue_type` (`classic` по умолчанию, `quorum`, `stream`) есть в схеме настроек 4.4.0 [RMQ-код 4.4.0 `deps/rabbit/priv/schema/rabbit.schema`]; задаётся и на уровне vhost: `rabbitmqctl add_vhost … --default-queue-type quorum` [RMQ-док 4.4 `vhosts`]. Все ключи примера (`listeners.tcp.*`, `management.tcp.port`, `vm_memory_high_watermark.relative`, `disk_free_limit.absolute`, `auth_mechanisms.*`, `anonymous_login_user`, `log.file.level`) сверены с той же схемой 20.10.2026: неизвестный ключ RabbitMQ не пропустит и не запустится ⚠ (поведение при ошибке — по опыту).
- Отключение анонимного входа — [RMQ-док 4.4 `production-checklist`, «Anonymous Login»]; если подключаются клиенты AMQP 1.0, оставьте `PLAIN` (им нужен SASL) [RMQ-док 4.4 `amqp`].
- TLS, пароли, права — `02-…`.

### 3.6. Веб-интерфейс и первые шаги

```bash
sudo rabbitmq-plugins enable rabbitmq_management rabbitmq_prometheus
sudo systemctl restart rabbitmq-server
sudo rabbitmq-diagnostics ping && sudo rabbitmq-diagnostics status | head -40
sudo rabbitmq-diagnostics listeners          # проверка: 5672, 15672, 15692, 25672

# администратор (пароль спросит интерактивно)
sudo rabbitmqctl add_user admin
sudo rabbitmqctl set_user_tags admin administrator
sudo rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
sudo rabbitmqctl delete_user guest

# vhost обмена 1С с кворумными очередями по умолчанию
sudo rabbitmqctl add_vhost erp --description "Обмен 1С" --default-queue-type quorum
sudo rabbitmqctl set_permissions -p erp admin ".*" ".*" ".*"
sudo rabbitmqctl list_vhosts name default_queue_type
```

Формы команд — [RMQ-док 4.4 `access-control`, `vhosts`]. Если пароль передать в командной строке, он попадёт в историю и список процессов — документация советует ввод с клавиатуры или из стандартного ввода [RMQ-док 4.4 `access-control`]. Веб-интерфейс: `http://rmq01.example.local:15672/` (вне стенда — только через TLS, `02-…`).

### 3.7. Порты и сетевой экран

| Порт | Назначение | Кому открыть |
|---|---|---|
| 5672 / 5671 | AMQP 0-9-1 и AMQP 1.0 без TLS / с TLS | Серверы 1С, системы обмена |
| 15672 / 15671 | Веб-интерфейс, HTTP API | Администраторам; серверам 1С — если обмен через HTTP API |
| 15692 / 15691 | Метрики Prometheus | Серверу мониторинга |
| 25672 | Связь узлов кластера и утилит (Erlang distribution) | Только узлам кластера |
| 4369 | epmd (поиск узлов) | Только узлам кластера |
| 35672–35682 | Утилиты командной строки → узлы | Узлам кластера / администраторам |
| 5552 / 5551, 6000–6500 | Протокол потоков и репликация потоков | Если используются потоки |

Источник — [RMQ-док 4.4 `networking`, «Port Access»]. Порты 4369 и 25672 наружу не открывайте: по cookie-файлу через них можно управлять узлом.

## 4. Установка в Docker

Официальный образ — `rabbitmq` (Docker Official Image); метки `4.4.0`, `4.4.0-management`, `4.4-management`, `4-management` обновлены 19–20.10.2026 [Docker Hub API]. Вариант `-management` — с включённым веб-интерфейсом.

Особенности [Docker Hub, описание образа]:

- данные лежат в `/var/lib/rabbitmq` по имени узла, которое по умолчанию берётся из имени хоста — **задавайте `hostname` явно**, иначе после пересоздания контейнера узел «потеряет» данные;
- `/var/lib/rabbitmq` — том по умолчанию;
- `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS`, `RABBITMQ_DEFAULT_VHOST` — задают пользователя и vhost при первом запуске; остальные «докерные» переменные с 3.9 устарели — настройки через `rabbitmq.conf`;
- общий Erlang-cookie для кластера — файлом `/var/lib/rabbitmq/.erlang.cookie` (секрет Docker).

```yaml
# rabbitmq/docker-compose.yml — стенд
services:
  rabbitmq:
    image: rabbitmq:4.4.0-management
    hostname: rmq-stand              # имя узла rabbit@rmq-stand — не менять
    container_name: rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS_FILE: /run/secrets/rmq_admin_pass   # вариант с файлом-секретом
      RABBITMQ_DEFAULT_VHOST: erp
    secrets:
      - rmq_admin_pass
    ports:
      - "5672:5672"
      - "127.0.0.1:15672:15672"     # веб-интерфейс только локально; наружу — через обратный прокси с TLS
      - "15692:15692"
    volumes:
      - rmq-data:/var/lib/rabbitmq
      - ./conf.d/90-local.conf:/etc/rabbitmq/conf.d/90-local.conf:ro
    ulimits:
      nofile: { soft: 131072, hard: 131072 }
secrets:
  rmq_admin_pass:
    file: ./secrets/rmq_admin_pass
volumes:
  rmq-data:
```

`RABBITMQ_DEFAULT_PASS_FILE` упомянут в описании образа среди переменных [Docker Hub]; поддерживается ли он в 4.4 наравне с `RABBITMQ_DEFAULT_PASS` — ⚠ (если нет — задать пароль переменной и сменить после первого входа). Каталог `/etc/rabbitmq/conf.d/` с файлами `.conf` — способ раздельной настройки [RMQ-док 4.4 `configure`, «a directory of .conf files»]; что в образе он читается — ⚠. Модуль Prometheus в образе `-management` включён ли — ⚠ (проверить `rabbitmq-plugins list` внутри контейнера, при необходимости `rabbitmq-plugins enable rabbitmq_prometheus`).

```bash
docker compose up -d
docker exec rabbitmq rabbitmq-diagnostics status | head -30
docker exec rabbitmq rabbitmqctl list_vhosts name default_queue_type
```

## 5. Очереди и сообщения для обмена 1С: что настроить

### 5.1. Топология «по умолчанию» для одной ERP и нескольких получателей

```text
                ┌──────────── привязка erp.nomenclature.* ──► очередь site.from-erp   (сайт)
ERP (1С) ─► обменник erp.events (topic)
                └──────────── привязка erp.#           ──► очередь bi.from-erp      (аналитика)

Сайт ─► обменник site.events (topic) ── привязка site.order.* ──► очередь erp.from-site (ERP)

Отвергнутые ─► обменник dlx (fanout) ──► очередь dlx.erp-1c (разбор ошибок)
```

```bash
# через rabbitmqadmin (v2) или веб-интерфейс; ниже — эквивалент через HTTP API (curl)
U=admin:ПАРОЛЬ; H=http://127.0.0.1:15672/api; V=erp
curl -u $U -X PUT $H/exchanges/$V/erp.events  -H 'content-type: application/json' -d '{"type":"topic","durable":true}'
curl -u $U -X PUT $H/exchanges/$V/dlx         -H 'content-type: application/json' -d '{"type":"fanout","durable":true}'
curl -u $U -X PUT $H/queues/$V/site.from-erp  -H 'content-type: application/json' -d '{"durable":true,"arguments":{"x-queue-type":"quorum"}}'
curl -u $U -X POST $H/bindings/$V/e/erp.events/q/site.from-erp -H 'content-type: application/json' -d '{"routing_key":"erp.nomenclature.*"}'
# политика: предел доставок и «отстойник» для всех очередей vhost
curl -u $U -X PUT $H/policies/$V/erp-dlx -H 'content-type: application/json' \
  -d '{"pattern":".*","apply-to":"queues","definition":{"dead-letter-exchange":"dlx","delivery-limit":20}}'
```

Пути HTTP API (`/api/exchanges/<vhost>/<имя>`, `/api/queues/…`, `/api/bindings/<vhost>/e/<обменник>/q/<очередь>`, `/api/policies/…`) — по справочнику API модуля управления (`/api/index.html` на самом узле) ⚠ (формы тел сверить там же). Аргумент очереди `x-queue-type=quorum` и политики `delivery-limit`, `dead-letter-exchange` — [RMQ-док 4.4 `quorum-queues`]. Описание всех объектов (обменники, очереди, привязки, политики, пользователи) удобно хранить в файле определений и загружать при развёртывании (`02-…`, раздел 7).

### 5.2. Свойства для надёжного обмена

| Где | Что | Почему |
|---|---|---|
| Очередь | `durable`, тип `quorum` | Переживает перезапуск и (в кластере) отказ узла |
| Сообщение | постоянное (`delivery_mode = 2` в AMQP 0-9-1; в AMQP 1.0 — `durable` в заголовке) | Пишется на диск; для кворумных очередей сообщения сохраняются в любом случае ⚠ |
| Отправитель | подтверждения издателя (publisher confirms) | Знать, что брокер принял; без них «отправлено» ≠ «сохранено» |
| Получатель | ручное подтверждение (`ack`) после записи в 1С; `prefetch` 10–100 | Сбой до `ack` → сообщение вернётся |
| Очередь | предел доставок (умолчание 20 у кворумной) + DLX | «Ядовитое» сообщение не крутится бесконечно |
| Получатель | идемпотентность | Повторная доставка неизбежна |

Источники: подтверждения и предел доставок — [RMQ-док 4.4 `quorum-queues`, `production-checklist`]; остальное — [практика]. Опрос очереди (`basic.get`) документация считает неэффективным [RMQ-док 4.4 `production-checklist`, «Polling Consumers»] — но для регламентного задания 1С без постоянного соединения это часто единственный путь; см. `03-…`.

### 5.3. AMQP 1.0: адреса

С 4.0 адреса AMQP 1.0 имеют формат v2 [RMQ-док 4.4 `amqp`]:

| Адрес | Смысл |
|---|---|
| `/exchanges/<обменник>/<ключ>` | Отправка в обменник с ключом маршрутизации |
| `/exchanges/<обменник>` | Отправка в обменник с пустым ключом |
| `/queues/<очередь>` | Отправка прямо в очередь; как источник — получение из очереди |

Спецсимволы в именах кодируются процентами (`/` → `%2F`). Клиент AMQP 1.0 обязан пройти SASL; vhost выбирается полем `hostname` кадра `open` в виде `vhost:<имя>`, иначе — `default_vhost` из настроек (умолчание `/`) [RMQ-док 4.4 `amqp`]. Это важно для подключения сервисов интеграции 1С без «1С:Шины» (`03-…`, раздел 4).

## 6. Типовые ошибки установки

| Симптом | Причина | Что сделать |
|---|---|---|
| `apt install rabbitmq-server` поставил 3.12 | Не подключены репозитории команды RabbitMQ (взят пакет Ubuntu) | Подключить `deb1/deb2.rabbitmq.com`, `apt-cache policy rabbitmq-server` |
| Узел не стартует после установки Erlang из Ubuntu | Erlang не той версии (в Ubuntu может быть старше 27) | Erlang из репозитория команды RabbitMQ |
| `ACCESS_REFUSED`, пользователь `guest` с другой машины | `guest` разрешён только с `localhost` | Свой пользователь |
| После смены имени хоста «пропали» очереди | Каталог данных привязан к имени узла | Вернуть имя; переносить узел — по процедуре документации |
| Отправители «зависли», в журнале — memory/disk alarm | Сработал сторож памяти или диска | Освободить место/память, разобрать, кто не читает очереди (`02-…`, раздел 6) |
| Веб-интерфейс не открывается | Модуль не включён или порт закрыт | `rabbitmq-plugins enable rabbitmq_management`, `rabbitmq-diagnostics listeners` |
| Контейнер после пересоздания пустой | Не задан `hostname` или нет тома | `hostname:` в compose и именованный том |

Тексты ошибок клиентов — [практика ⚠].

## 7. Что проверить после установки

1. `rabbitmq-diagnostics status` — версия RabbitMQ и Erlang ожидаемые; `file descriptors` — лимит поднят.
2. `rabbitmqctl list_users` — нет `guest`; у администратора тег `administrator`.
3. `rabbitmqctl list_vhosts name default_queue_type` — у `erp` — `quorum`.
4. `rabbitmq-diagnostics listeners` — только нужные порты; 4369/25672 закрыты экраном снаружи.
5. `disk_free_limit` поднят; `/var/lib/rabbitmq` на отдельном томе.
6. Пакет закреплён (`apt-mark showhold`).

## Источники

- Документация RabbitMQ 4.4: `raw.githubusercontent.com/rabbitmq/rabbitmq-website/main/versioned_docs/version-4.4/<страница>.md` (опубликована на `rabbitmq.com/docs/…`).
- Сроки поддержки: `raw.githubusercontent.com/rabbitmq/rabbitmq-website/main/docusaurus.config.js` (раздел `releaseBranches`), страница `rabbitmq.com/release-information`.
- Примечания к выпуску 4.4.0: `api.github.com/repos/rabbitmq/rabbitmq-server/releases/tags/v4.4.0`.
- Образ Docker: `raw.githubusercontent.com/docker-library/docs/master/rabbitmq/content.md`; метки — `hub.docker.com/v2/repositories/library/rabbitmq/tags/<метка>`.
- Пакеты Ubuntu: `packages.ubuntu.com/noble/rabbitmq-server`, `…/jammy/rabbitmq-server`.
