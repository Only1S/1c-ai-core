# RabbitMQ: безопасность, кластер, мониторинг, обслуживание и обновление

> **Официальные тексты по теме**: документация RabbitMQ 4.4 (`versioned_docs/version-4.4/` репозитория `rabbitmq/rabbitmq-website`): `access-control.md`, `ssl/index.md`, `production-checklist.md`, `clustering.md`, `cluster-formation.md`, `quorum-queues/index.md`, `metadata-store/index.md`, `networking.md`, `prometheus/index.md`, `management/index.md`, `memory.md`, `disk-alarms.md`, `definitions.md`, `backup.md`, `upgrade.md`, `rolling-upgrade.md`, `feature-flags/index.md`; схема настроек `deps/rabbit/priv/schema/rabbit.schema` (метка `v4.4.0` репозитория `rabbitmq/rabbitmq-server`); примечания к выпуску 4.4.0.

> Статус: написано 20.10.2026 по первоисточникам; на сервере не запускалось. Независимой сверки не было. Непроверенное помечено «⚠».

> Область: пароли и права, TLS, кластер из трёх узлов, за чем следить, как резервировать описание брокера, как обновлять. Установка и понятия — `01-…`; обмен 1С — `03-…`.

Пометки: **[RMQ-док 4.4]**, **[RMQ-код 4.4.0]**, **[RMQ-RN 4.4.0]**, **[RMQ-сайт]** — как в `01-…`; **[практика]**; **⚠**.

Условные обозначения: узлы `rmq01…03.example.local`, имена узлов `rabbit@rmq01…03`; vhost `erp`; пользователи `admin`, `erp-1c`, `site`, `bi`, `monitor`.

## Кратко — главные факты

1. **Права в RabbitMQ — на vhost, тремя регулярными выражениями:** `configure` (создавать/удалять обменники и очереди), `write` (публиковать, привязывать к очереди), `read` (получать, привязывать от обменника, очищать очередь) [RMQ-док 4.4 `access-control`].
2. **Теги пользователя управляют доступом к веб-интерфейсу и HTTP API:** `administrator`, `monitoring`, `policymaker`, `management`; без тега пользователь может работать по AMQP, но не войти в веб-интерфейс [RMQ-док 4.4 `management`].
3. **`guest` — только с `localhost`**; анонимный вход (`ANONYMOUS`) в работе отключают [RMQ-док 4.4 `install-debian`, `production-checklist`].
4. **TLS:** слушатель `listeners.ssl.default = 5671` и `ssl_options.cacertfile/certfile/keyfile`; проверка сертификата клиента — `ssl_options.verify = verify_peer` + `ssl_options.fail_if_no_peer_cert = true` [RMQ-док 4.4 `ssl`]. Отключить порт без TLS — `listeners.tcp = none` [RMQ-код 4.4.0 схемы настроек].
5. **Erlang-cookie** — общий секрет узлов кластера и утилит: кто знает cookie и дотянулся до порта 25672, тот управляет узлом. Права `400`, владелец `rabbitmq` [RMQ-док 4.4 `clustering`, `production-checklist`].
6. **Кластер — 3 или 5 узлов**, кворумные очереди реплицируются на большинство; Khepri (Raft) — хранилище метаданных по умолчанию с 4.2 [RMQ-док 4.4 `production-checklist`, `metadata-store`].
7. **С 4.1 `join_cluster` не требует `stop_app`/`reset`**, но присоединение узла к кластеру **уничтожает его данные** [RMQ-док 4.4 `clustering`]. Для работы документация советует автоматическое формирование (`cluster_formation.peer_discovery_backend = classic_config` со списком узлов), а не ручное [там же; `cluster-formation`].
8. **Мониторинг — модуль `rabbitmq_prometheus`** (порт 15692), готовые панели Grafana (например, 10991 «RabbitMQ-Overview») [RMQ-док 4.4 `prometheus`]. Для обмена 1С главное: **глубина очередей**, **неподтверждённые**, **очереди без получателей**, **сторожа памяти и диска**.
9. **Резервирование:** описание брокера (vhost, пользователи, права, обменники, очереди, привязки, политики) — `rabbitmqctl export_definitions` [RMQ-док 4.4 `definitions`]. Сами сообщения — копией каталога данных **остановленного** узла [RMQ-док 4.4 `backup`]; для обмена 1С источник истины — база 1С.
10. **Обновление:** перед ним включить **все стабильные флаги** (`rabbitmqctl enable_feature_flag all`), иначе обновление может не пройти; ветки не перепрыгивать: 3.13 → 4.2 → 4.3 → 4.4 [RMQ-док 4.4 `upgrade`; переход 4.3 → 4.4 — RMQ-RN 4.4.0].
11. **Перед остановкой узла кластера** — `rabbitmq-diagnostics check_if_node_is_quorum_critical` и/или режим обслуживания `rabbitmq-upgrade drain` [RMQ-док 4.4 `upgrade`].

## 1. Пользователи и права

### 1.1. Модель для обмена 1С

| Пользователь | Тег | Права в vhost `erp` (`configure` / `write` / `read`) | Смысл |
|---|---|---|---|
| `admin` | `administrator` | `.*` / `.*` / `.*` | Администрирование |
| `erp-1c` | — (или `management`, если 1С ходит через HTTP API) | `^$` / `^erp\.events$` / `^erp\.from-` | Публикует в свой обменник, читает свои очереди, ничего не создаёт |
| `site` | — | `^$` / `^site\.events$` / `^site\.from-` | То же для сайта |
| `bi` | — | `^$` / `^$` / `^bi\.from-` | Только чтение своей очереди |
| `monitor` | `monitoring` | `^$` / `^$` / `^$` | Метрики и веб-интерфейс только на просмотр |

`^$` — «ничего» (пустая строка совпадает только с пустым именем, а пустое имя — это обменник по умолчанию ⚠: публикация в обменник по умолчанию требует `write` на `amq.default` — сверить в таблице прав документации). Топологию (обменники, очереди, привязки) создаёт администратор или файл определений; прикладным учётным записям `configure` не дают [практика].

```bash
sudo rabbitmqctl add_user erp-1c                       # пароль спросит
sudo rabbitmqctl set_permissions -p erp erp-1c '^$' '^erp\.events$' '^erp\.from-'
sudo rabbitmqctl add_user monitor && sudo rabbitmqctl set_user_tags monitor monitoring
sudo rabbitmqctl list_user_permissions erp-1c
sudo rabbitmqctl list_permissions -p erp
```

Какое действие какого права требует (по таблице документации) [RMQ-док 4.4 `access-control`]:

| Действие | Право | На что |
|---|---|---|
| Публикация | `write` | обменник |
| Привязка очереди к обменнику | `write` на очередь, `read` на обменник | |
| Получение (`basic.get`/`basic.consume`), очистка очереди | `read` | очередь |
| Объявление/удаление очереди или обменника | `configure` | очередь/обменник |
| Объявление очереди с DLX | `configure` на очередь, `write` на обменник DLX, `read` на очередь | |
| Пассивное объявление (проверка существования) | с **4.3.1** — хотя бы одно право на ресурс | |

Последний пункт важен для клиентов, которые при подключении «проверяют» очередь: с 4.3.1 пользователю без прав на очередь откажут даже в пассивной проверке [RMQ-док 4.4 `access-control`].

### 1.2. Другие способы входа

| Способ | Модуль | Когда |
|---|---|---|
| Внутренняя база (логин/пароль) | встроенный | По умолчанию |
| LDAP / Active Directory | `rabbitmq_auth_backend_ldap` | Единые учётные записи; кэш — `rabbitmq_auth_backend_cache` |
| OAuth 2 / OpenID Connect (JWT) | `rabbitmq_auth_backend_oauth2` | Есть Keycloak и т. п.; с 4.4 строже проверка обнаружения OIDC [RMQ-RN 4.4.0] |
| Сертификат клиента (x.509, `EXTERNAL`) | `rabbitmq_auth_mechanism_ssl` | Системы, умеющие mTLS |

Источник — [RMQ-док 4.4 `access-control`, `amqp`]. Для 1С практичен логин/пароль поверх TLS: и внешние компоненты, и HTTP API, и сервисы интеграции работают с ним.

## 2. TLS

```ini
# /etc/rabbitmq/conf.d/20-tls.conf (или в rabbitmq.conf)
listeners.ssl.default = 5671
ssl_options.cacertfile = /etc/rabbitmq/tls/ca-chain.pem
ssl_options.certfile   = /etc/rabbitmq/tls/rmq01.pem
ssl_options.keyfile    = /etc/rabbitmq/tls/rmq01.key
ssl_options.verify     = verify_peer
ssl_options.fail_if_no_peer_cert = false      # true — только клиенты с сертификатом (mTLS)

# веб-интерфейс и HTTP API по TLS
management.ssl.port       = 15671
management.ssl.cacertfile = /etc/rabbitmq/tls/ca-chain.pem
management.ssl.certfile   = /etc/rabbitmq/tls/rmq01.pem
management.ssl.keyfile    = /etc/rabbitmq/tls/rmq01.key
```

Ключи `listeners.ssl.default`, `ssl_options.*` — [RMQ-док 4.4 `ssl`]; `management.ssl.port/cacertfile/certfile/keyfile` — [RMQ-код 4.4.0 схемы настроек] модуля `rabbitmq_management`. Файлы ключей — владелец `rabbitmq`, права `400`/`640`.

- Порт 5672 без TLS после перехода закройте: оставьте только `listeners.ssl.default` и уберите `listeners.tcp.default`; явный запрет — `listeners.tcp = none` [RMQ-код 4.4.0 схемы настроек].
- Версии TLS по умолчанию определяются Erlang/OTP; TLS 1.3 поддерживается [RMQ-док 4.4 `ssl`]. Ограничить — `ssl_options.versions.1 = tlsv1.3`, `ssl_options.versions.2 = tlsv1.2` ⚠ (формат сверить по документации).
- Проверка: `openssl s_client -connect rmq01.example.local:5671 -servername rmq01.example.local </dev/null`; разбор ошибок — раздел `troubleshooting-ssl` документации.
- Связь узлов кластера (Erlang distribution) по умолчанию **не шифруется**; шифрование — отдельная настройка (`clustering-ssl.md`) [RMQ-док 4.4]. Проще держать узлы в отдельной сети.

## 3. Защита узла

По «Production Checklist» [RMQ-док 4.4]:

- удалить `guest`, отключить анонимный вход;
- сетевой экран: 4369, 25672, 35672–35682 — только между узлами кластера; 5671/5672 — серверам 1С и системам; 15671/15672 — администраторам; 15692 — мониторингу;
- cookie-файл: `/var/lib/rabbitmq/.erlang.cookie`, права только владельцу;
- шифрование «на диске» RabbitMQ не делает — при необходимости шифруйте том [RMQ-док 4.4 «Encryption at Rest»];
- веб-интерфейс наружу — только через TLS (лучше — за обратным прокси, как в `../apache/03-…`).

## 4. Кластер

### 4.1. Схема и правила

- **Нечётное число узлов:** 3 выдерживают отказ одного, 5 — двух; кворумные очереди по умолчанию размещают реплики на нескольких узлах, достаточно «больше половины, но не все» [RMQ-док 4.4 `production-checklist`].
- **Метаданные** (vhost, пользователи, очереди, обменники) реплицируются на все узлы синхронно — кластеры из десятков узлов не делают, лучше несколько независимых [там же].
- **Классические очереди не реплицируются** (зеркалирование удалено в 4.0) — при отказе их узла очередь недоступна; для обмена — только кворумные [RMQ-док 4.4 `quorum-queues`].
- **Khepri** — Raft-хранилище метаданных; с 4.2 по умолчанию для новых установок. Узлы, поднятые на 4.1 и старше, остаются на Mnesia до включения флага `khepri_db` [RMQ-док 4.4 `metadata-store`]. Стратегии разделения сети (`pause_minority` и др.) относятся к Mnesia; с Khepri поведение определяет Raft ⚠ (подробности — в `metadata-store/…` документации).
- Клиент может подключаться к любому узлу; удобнее — через список узлов в клиенте или балансировщик TCP [RMQ-док 4.4 `production-checklist`].

### 4.2. Сборка

1. На всех узлах — одинаковые версии RabbitMQ и Erlang, имена хостов разрешаются, время синхронизировано.
2. Одинаковый cookie:

```bash
# на rmq01
sudo cat /var/lib/rabbitmq/.erlang.cookie     # скопировать значение защищённым каналом
# на rmq02, rmq03 — до первого запуска или с остановкой службы
sudo systemctl stop rabbitmq-server
echo -n 'ЗНАЧЕНИЕ_COOKIE' | sudo tee /var/lib/rabbitmq/.erlang.cookie >/dev/null
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie && sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie
sudo systemctl start rabbitmq-server
```

3. Формирование кластера — автоматически при первом запуске всех узлов (рекомендуется):

```ini
# на всех узлах, до первого запуска
cluster_formation.peer_discovery_backend = classic_config
cluster_formation.classic_config.nodes.1 = rabbit@rmq01
cluster_formation.classic_config.nodes.2 = rabbit@rmq02
cluster_formation.classic_config.nodes.3 = rabbit@rmq03
```

Ключи — [RMQ-док 4.4 `cluster-formation`]; узлы указывают в той форме, в какой они называются (короткие или полные имена — как настроено) ⚠.

Или вручную (стенд, восстановление) [RMQ-док 4.4 `clustering`]:

```bash
# на rmq02 и rmq03; с 4.1 stop_app/reset не нужны; данные этого узла будут потеряны!
sudo rabbitmqctl join_cluster rabbit@rmq01
sudo rabbitmqctl cluster_status
```

4. Проверка: `rabbitmqctl cluster_status` — все три узла в `Running Nodes`; `rabbitmq-diagnostics check_running`; в веб-интерфейсе — три узла.

Вывести узел из кластера навсегда — `rabbitmqctl forget_cluster_node rabbit@rmq03` с живого узла ⚠ (порядок для Khepri — сверить в `metadata-store/clustering.md`).

### 4.3. Кворумные очереди: что учесть

- Реплики очереди — на трёх узлах (по умолчанию размер группы ограничен числом узлов ⚠ — значение по умолчанию сверить в `quorum-queues`); запись подтверждается большинством.
- **Предел доставок 20** (с 4.0): после 20 возвратов сообщение отбрасывается или уходит в DLX; вернуть старое «без предела» — `x-delivery-limit = -1` или политикой `delivery-limit` [RMQ-док 4.4 `quorum-queues`]. Для обмена 1С — оставьте предел и настройте DLX, иначе «ядовитое» сообщение молча исчезнет.
- Кворумным очередям нужно больше памяти и диска, чем классическим [RMQ-док 4.4 `production-checklist`].
- Длинные очереди (сотни тысяч сообщений из-за простоя получателя) нагружают память; ограничивайте политикой `max-length`/`max-length-bytes` с `overflow = reject-publish` — отправитель 1С получит отказ и оставит сообщение у себя в очереди отправки [практика ⚠].

## 5. Мониторинг

### 5.1. Prometheus и Grafana

```bash
sudo rabbitmq-plugins enable rabbitmq_prometheus
curl -s http://rmq01.example.local:15692/metrics | head          # совокупные метрики
curl -s http://rmq01.example.local:15692/metrics/per-object | grep -c rabbitmq_queue_messages   # по объектам
```

- `/metrics` — совокупные значения (по умолчанию), `/metrics/per-object` — по каждой очереди и соединению (дороже при тысячах объектов), `/metrics/detailed` — с выбором групп метрик [RMQ-док 4.4 `prometheus`].
- Готовая панель Grafana — «RabbitMQ-Overview» (grafana.com, номер 10991); там же есть панели по Raft и Erlang [RMQ-док 4.4 `prometheus`].
- Сбор метрик для веб-интерфейса можно отключить (`management_agent.disable_metrics_collector = true`), если всё смотрят в Grafana — разгружает узлы [RMQ-док 4.4 `management`].

### 5.2. На что ставить тревоги (обмен 1С)

| Метрика / проверка | Тревога | Что означает |
|---|---|---|
| Число сообщений в очереди `erp.from-*` | растёт > 15 мин | 1С не забирает (регламентное задание, ошибки, блокировки) |
| Сообщения без подтверждения (`messages_unacknowledged`) | долго > 0 | Получатель взял и «завис» |
| Получателей у очереди = 0 | для очередей с постоянным получателем | Отвалилась компонента/служба |
| Очередь DLX не пуста | > 0 | Есть «ядовитые» сообщения — разбирать |
| Сторож памяти / диска | сработал | Публикация остановлена для всех |
| Свободные дескрипторы | < 20% | Скоро отказ новых соединений |
| Частота открытия/закрытия соединений | высокая | Клиент подключается на каждое сообщение (типично для кода 1С без долгого соединения) |
| Узлы кластера | не все `running` | Отказ узла |

Пороги — [практика]; про частые переподключения документация предупреждает отдельно («Connection Churn») [RMQ-док 4.4 `production-checklist`].

### 5.3. Команды диагностики

```bash
sudo rabbitmq-diagnostics status                 # версии, память, дескрипторы, сторожа
sudo rabbitmq-diagnostics check_local_alarms     # 0 = норма
sudo rabbitmq-diagnostics alarms
sudo rabbitmq-diagnostics listeners
sudo rabbitmq-diagnostics memory_breakdown       # кто занял память
sudo rabbitmqctl list_queues -p erp name type messages messages_unacknowledged consumers
sudo rabbitmqctl list_connections user peer_host state
sudo tail -n 100 /var/log/rabbitmq/rabbit@$(hostname -s).log
```

Наличие команды `memory_breakdown` и столбцов `list_queues` — ⚠ (сверить `rabbitmq-diagnostics help`, `rabbitmqctl list_queues --help`). Журналы можно отправлять в Loki тем же агентом, что и журналы 1С (`../observability/03-…`).

## 6. Сторожа ресурсов

- **Память:** выше `vm_memory_high_watermark.relative` (0,6) узел блокирует публикацию **во всех соединениях** до снижения; рекомендуемый диапазон 0,4–0,7 [RMQ-док 4.4 `production-checklist`, `memory`].
- **Диск:** ниже `disk_free_limit` — то же. Умолчание 50 МБ годится только для разработки; в работе — не меньше порога памяти. Нехватка диска — «очень серьёзная проблема», возможна потеря данных узла [RMQ-док 4.4 `production-checklist`, `disk-alarms`].
- Для отправителя 1С сработавший сторож выглядит как «зависание» публикации или таймаут — поэтому очередь отправки в 1С (outbox) обязательна, см. `03-…`.

## 7. Резервирование и восстановление

| Что | Как | Источник |
|---|---|---|
| Описание (vhost, пользователи с хешами паролей, права, обменники, очереди, привязки, политики) | `rabbitmqctl export_definitions /backup/rmq-defs-$(date +%F).json`; восстановление — `rabbitmqctl import_definitions <файл>` | [RMQ-док 4.4 `definitions`] |
| Загрузка описания при запуске (развёртывание «как код») | ключ `definitions.import_backend = local_filesystem` + `definitions.local.path = …` | [RMQ-док 4.4 `definitions`; ключи есть в RMQ-код 4.4.0 схемы настроек] |
| Сообщения | Копия каталога данных **остановленного** узла; на работающем узле копия не согласована | [RMQ-док 4.4 `backup`] |
| Переезд на новый кластер | Сине-зелёное развёртывание: новый кластер, перенос описания, переключение клиентов, перекачка остатков (Shovel) | [RMQ-док 4.4 `blue-green-upgrade`] |

`export_definitions` — единственный способ без модуля управления; файл содержит хеши паролей — храните как секрет [RMQ-док 4.4 `definitions`; про секрет — практика]. Выгрузку — по расписанию (cron/systemd timer, `../linux/05-…`) и в Git без паролей.

## 8. Обновление

### 8.1. Пути

| Откуда | Куда |
|---|---|
| 4.3.x | 4.4.x (поэтапно; при одновременном обновлении Erlang до 28+ — сначала 4.3.7+) |
| 4.2.x | 4.3.x |
| 4.1.x | 4.2.x |
| 4.0.x | 4.1.x или 4.2.x |
| 3.13.x | сначала 4.2.x, затем 4.3.x |
| 3.12 и старше (пакет Ubuntu) | только поэтапно по веткам или новый кластер + перенос (сине-зелёное) |

Источники — [RMQ-док 4.4 `upgrade`] (таблица в документации 4.4 доведена до 4.3) и [RMQ-RN 4.4.0] для 4.3 → 4.4. Пакет Ubuntu 3.12.1 обновлять «на месте» до 4.4 бессмысленно: новый узел из репозитория RabbitMQ и перенос описания проще [практика].

### 8.2. Порядок поэтапного обновления кластера

1. Прочитать примечания к целевому выпуску и проверить совместимость Erlang (`which-erlang`).
2. **Включить все стабильные флаги** на текущей версии:

```bash
sudo rabbitmqctl list_feature_flags
sudo rabbitmqctl enable_feature_flag all
```

[RMQ-док 4.4 `upgrade`, `feature-flags`].
3. Выгрузить описание (`export_definitions`).
4. По одному узлу:

```bash
sudo rabbitmq-diagnostics check_if_node_is_quorum_critical   # не останавливать, если узел критичен для кворума
sudo rabbitmq-upgrade drain                                   # режим обслуживания: клиенты уходят, лидеры переезжают
sudo apt-mark unhold rabbitmq-server erlang-base
sudo apt-get install rabbitmq-server=<версия>-1 …             # и Erlang, если нужно
sudo apt-mark hold rabbitmq-server erlang-base
sudo systemctl restart rabbitmq-server
sudo rabbitmq-upgrade revive                                  # если узел остался в режиме обслуживания ⚠
sudo rabbitmq-upgrade await_online_quorum_plus_one            # дождаться, пока кворумные очереди снова в безопасности
```

Команды `check_if_node_is_quorum_critical`, `drain`, `revive`, `await_online_quorum_plus_one` — [RMQ-док 4.4 `upgrade`]. Сохраняется ли режим обслуживания после перезапуска узла — ⚠ (см. раздел «Maintenance Mode» документации). Точное имя версии пакета — `apt-cache madison rabbitmq-server`.

5. После всех узлов — снова `enable_feature_flag all` (новые флаги новой версии) и проверка обмена 1С.

**Откат:** понижение версии документация не поддерживает в общем случае (раздел «Downgrades») ⚠ — откат = новый кластер на старой версии + описание + перекачка.

### 8.3. Одиночный узел и Docker

Одиночный узел — те же шаги без `drain`: остановка, обновление пакета, запуск; обмен 1С на это время копит сообщения в очередях отправки. В Docker — сменить метку образа (`rabbitmq:4.4.0-management`), `docker compose up -d`; том данных и `hostname` те же; флаги — `docker exec rabbitmq rabbitmqctl enable_feature_flag all` **до** смены метки.

## 9. Контрольный список «RabbitMQ готов к обмену с 1С»

1. Версия из поддерживаемой ветки (4.4 или 4.3), Erlang 27–29, пакет закреплён.
2. `guest` удалён, анонимный вход выключен, у каждой системы своя учётная запись с минимальными правами в своём vhost.
3. TLS на 5671 и 15671; 5672 закрыт или только во внутренней сети.
4. Очереди обмена — кворумные; политика с DLX и пределом доставок; «отстойник» мониторится.
5. `disk_free_limit` поднят, сторожа под наблюдением; дескрипторы ≥ 50 000.
6. Метрики Prometheus собираются, тревоги на рост очередей, DLX, сторожа, узлы.
7. `export_definitions` — по расписанию; описание топологии — в Git.
8. Порядок обновления (флаги → поэтапно) опробован на стенде.

## Источники

- Документация RabbitMQ 4.4: `raw.githubusercontent.com/rabbitmq/rabbitmq-website/main/versioned_docs/version-4.4/<страница>.md`.
- Схема настроек: `raw.githubusercontent.com/rabbitmq/rabbitmq-server/v4.4.0/deps/rabbit/priv/schema/rabbit.schema`.
- Примечания к выпуску 4.4.0: `api.github.com/repos/rabbitmq/rabbitmq-server/releases/tags/v4.4.0`.
- Сроки поддержки: `rabbitmq-website/main/docusaurus.config.js` (`releaseBranches`).
