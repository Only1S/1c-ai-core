# Apache Kafka: безопасность, кластер, мониторинг, обслуживание и обновление

> **Официальные тексты по теме**: документация Apache Kafka 4.4 (каталог `docs/` ветки `4.4` репозитория `apache/kafka`): `security/security-overview.md`, `security/listener-configuration.md`, `security/encryption-and-authentication-using-ssl.md`, `security/authentication-using-sasl.md`, `security/authorization-and-acls.md`, `operations/kraft.md`, `operations/basic-kafka-operations.md`, `operations/monitoring.md`, `operations/hardware-and-os.md`, `getting-started/upgrade.md`; файлы `config/controller.properties`, `config/broker.properties` и классы конфигурации той же ветки.

> Статус: написано 20.10.2026 по первоисточникам (документация и исходный код ветки `4.4`); на сервере не запускалось. Независимой сверки не было. Непроверенное помечено «⚠».

> Область: как закрыть Kafka паролями и шифрованием, разграничить доступ систем (1С, мост, аналитика) к темам, собрать кластер, за чем следить, как обслуживать и обновлять. Установка и базовая настройка — `01-…`; обмен 1С — `03-…`.

Пометки: **[Kafka-док 4.4]**, **[Kafka-код 4.4]** — как в `01-…`; **[сторонний]** — документация сторонних проектов (Prometheus JMX Exporter, kafka_exporter); **[практика]** — опыт сообщества; **⚠** — не подтверждено.

Условные обозначения: брокеры `kafka01…03.example.local` (10.0.0.21–23), контроллеры `kctl01…03.example.local` (10.0.0.31–33); учётные записи Kafka: `admin` (межброкерный обмен и администрирование), `erp-1c` (база ERP), `bridge` (HTTP-мост), `bi` (аналитика).

## Кратко — главные факты

1. **По умолчанию в Kafka нет ни шифрования, ни паролей, ни разграничения доступа**: слушатель `PLAINTEXT`, любой, кто дошёл до порта 9092, может читать, писать и удалять темы [Kafka-док 4.4 `security-overview`]. На стенде в изолированной сети это терпимо, в рабочей сети — нет.
2. **Протоколы слушателя:** `PLAINTEXT`, `SSL` (TLS, по желанию — проверка сертификата клиента), `SASL_PLAINTEXT`, `SASL_SSL`. Для обмена с 1С разумный выбор — **`SASL_SSL` с `SCRAM-SHA-512`**: шифрование + логин/пароль на каждую систему [Kafka-док 4.4].
3. **Учётные записи SCRAM хранятся в метаданных кластера.** Запись для межброкерного обмена нужно создать **до запуска брокеров** — ключом `--add-scram` при `kafka-storage.sh format`; остальные — `kafka-configs.sh --alter --add-config 'SCRAM-SHA-512=[…]' --entity-type users` [Kafka-док 4.4 `authentication-using-sasl`].
4. **SCRAM — только поверх TLS**: иначе обмен можно перехватить и подобрать пароль [там же].
5. **TLS по умолчанию — 1.2 и 1.3** (`ssl.enabled.protocols=TLSv1.2,TLSv1.3`), ключи и сертификаты можно задавать в формате PEM прямо в настройках или файлами [Kafka-код 4.4 `SslConfigs`; Kafka-док 4.4]. Сертификат брокера должен разрешать и `serverAuth`, и `clientAuth`: брокеры подключаются друг к другу как клиенты [Kafka-док 4.4 «Common Pitfalls»].
6. **ACL включаются** `authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer`. Если на ресурс нет ни одного ACL, доступ есть **только у суперпользователей** (`super.users=User:admin`) [Kafka-док 4.4 `authorization-and-acls`]. `allow.everyone.if.no.acl.found=true` — путь к «всё открыто», не включайте.
7. **Кластер:** контроллеров 3 (выдерживают 1 отказ) или 5 (2 отказа), отдельно от брокеров; брокеров от 3; темы с `replication.factor=3`, `min.insync.replicas=2`, производители с `acks=all` (это умолчание клиента с 3.0) — тогда подтверждённая запись переживает отказ одного брокера [Kafka-док 4.4 `kraft`; Kafka-код 4.4 `ProducerConfig`].
8. **Метрики — через JMX**, удалённый JMX выключен по умолчанию (включается `JMX_PORT`) [Kafka-док 4.4 `monitoring`]. Главные: `UnderReplicatedPartitions` = 0, `UnderMinIsrPartitionCount` = 0, `OfflinePartitionsCount` = 0, `ActiveControllerCount` = 1 ровно на одном узле, `RequestHandlerAvgIdlePercent` и `NetworkProcessorAvgIdlePercent` > 0,3, **отставание групп потребителей** [там же].
9. **Отставание обмена 1С** проверяется одной командой: `kafka-consumer-groups.sh --describe --group <группа>` — столбец `LAG` [Kafka-док 4.4 `basic-kafka-operations`].
10. **Резервной копии «как у СУБД» у Kafka нет.** Надёжность — репликация; копия в другой кластер — MirrorMaker 2. Для обмена 1С источник истины — база 1С (очередь outbox), поэтому важнее уметь переотправить, чем восстановить Kafka.
11. **Обновление — по одному узлу**, затем `kafka-features.sh … upgrade --release-version <X.Y>`. После этого шага откат метаданных невозможен; хранилище, размеченное утилитой 4.4, старый брокер не откроет [Kafka-док 4.4 `upgrade`].
12. **С ZooKeeper на 4.x напрямую не перейти** — сначала 3.9 и миграция на KRaft [Kafka-док 4.4 `kraft`].

## 1. Модель безопасности

| Уровень | Чем закрывается | Где |
|---|---|---|
| Сеть | Сетевой экран: порт клиентов — только серверам 1С, мосту, системам; порт контроллеров — только узлам Kafka | `ufw`, сетевое оборудование |
| Шифрование | TLS на слушателях `SSL`/`SASL_SSL` | раздел 2 |
| Подлинность | SASL/SCRAM (пароль), TLS-сертификат клиента, Kerberos (GSSAPI), OAUTHBEARER | раздел 3 |
| Права | ACL на темы, группы, кластер | раздел 4 |
| Квоты | Ограничение скорости на пользователя/клиента | `kafka-configs.sh --entity-type users --add-config producer_byte_rate=…` [Kafka-док 4.4 «Setting quotas»] |

Слушатель контроллеров клиентам не нужен, и документация советует изолировать его на уровне сети [Kafka-док 4.4 `listener-configuration`].

## 2. TLS

### 2.1. Сертификаты

Свой УЦ из документации Kafka годится для стенда; в организации обычно есть корпоративный УЦ — тогда проверьте три вещи [Kafka-док 4.4 «Common Pitfalls in Production»]:

1. **Расширенное назначение ключа (EKU):** у брокера должны быть и `serverAuth`, и `clientAuth`. Профиль «веб-сервер» обычно даёт только `serverAuth` — межброкерное соединение тогда не установится.
2. **Цепочка:** при подписи промежуточным УЦ в хранилище нужна вся цепочка до корня.
3. **SAN:** УЦ мог не перенести запрошенные имена; смотрите `openssl x509 -in cert.pem -text -noout`.

Проверка имени хоста включена: клиент сверяет имя брокера с сертификатом (`ssl.endpoint.identification.algorithm=https`); отключать её (пустая строка) — только осознанно [Kafka-док 4.4 `encryption-and-authentication-using-ssl`].

### 2.2. PEM вместо JKS/PKCS12

С 2.7 ключ и сертификаты можно задать в формате PEM; пароли хранилищ (`ssl.keystore.password`, `ssl.truststore.password`) для PEM не используются, пароль зашифрованного ключа — `ssl.key.password` [Kafka-док 4.4]. Файловый вариант:

```properties
# фрагмент /etc/kafka/server.properties — TLS на слушателе клиентов (PEM-файлы)
ssl.keystore.type=PEM
ssl.keystore.location=/etc/kafka/tls/kafka01.pem      # закрытый ключ + сертификат + цепочка
ssl.truststore.type=PEM
ssl.truststore.location=/etc/kafka/tls/ca-chain.pem
ssl.client.auth=none                                   # пароли проверяет SASL
```

Варианты с ключом прямо в значении (`ssl.keystore.key`, `ssl.keystore.certificate.chain`, `ssl.truststore.certificates`) — тоже есть [Kafka-док 4.4]; файлы проще обновлять. Порядок блоков в PEM-файле хранилища ключей (ключ, затем сертификат и цепочка) — ⚠ сверить с разделом «SSL key and certificates in PEM format» документации и проверить запуском.

Права: `chown root:kafka /etc/kafka/tls/*.pem && chmod 640 …`.

`ssl.client.auth`: `none` (умолчание), `requested` (документация называет его ложным чувством безопасности — не используйте), `required` (взаимный TLS) [Kafka-док 4.4].

## 3. SASL/SCRAM: логины и пароли систем

### 3.1. Порядок включения на новом кластере

1. При разметке хранилища создать межброкерную учётную запись [Kafka-док 4.4 «Creating SCRAM Credentials»]:

```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format -t "$(cat /etc/kafka/cluster-id)" \
  -c /etc/kafka/server.properties --standalone \
  --add-scram 'SCRAM-SHA-512=[name="admin",password="СЛОЖНЫЙ_ПАРОЛЬ"]'
```

Пароль окажется в истории оболочки — выполните с пробелом в начале строки (при `HISTCONTROL=ignorespace`) или очистите историю.

2. Настройки брокера (одиночный узел стенда, слушатель клиентов `SASL_SSL`):

```properties
listeners=SASL_SSL://0.0.0.0:9094,CONTROLLER://kafka01.example.local:9093
advertised.listeners=SASL_SSL://kafka01.example.local:9094
listener.security.protocol.map=CONTROLLER:PLAINTEXT,SASL_SSL:SASL_SSL
inter.broker.listener.name=SASL_SSL
controller.listener.names=CONTROLLER
sasl.enabled.mechanisms=SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
listener.name.sasl_ssl.scram-sha-512.sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
    username="admin" password="СЛОЖНЫЙ_ПАРОЛЬ";
# + блок ssl.* из раздела 2.2
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
super.users=User:admin
```

Настройка JAAS свойством `listener.name.<слушатель>.<механизм>.sasl.jaas.config` (имена в нижнем регистре) заменяет отдельный файл JAAS и ключ JVM `-Djava.security.auth.login.config` [Kafka-док 4.4 `authentication-using-sasl`]. Файл `/etc/kafka/server.properties` теперь содержит пароль — права `640`, группа `kafka`.

Слушатель контроллеров здесь `PLAINTEXT` — допустимо, только если порт 9093 доступен лишь узлам Kafka (отдельная сеть или правила экрана). Для слушателя контроллеров документация показывает и `SASL_SSL` [Kafka-док 4.4 `listener-configuration`]; какой механизм SASL на нём применять в KRaft (учётные записи SCRAM лежат в тех же метаданных, которые контроллеры только ещё синхронизируют) — ⚠, в документации 4.4 прямо не сказано; надёжный вариант — `SSL` с взаимной проверкой сертификатов.

3. Учётные записи систем (после запуска):

```bash
cat > /root/kafka-admin.properties <<'EOF'
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username="admin" password="СЛОЖНЫЙ_ПАРОЛЬ";
ssl.truststore.type=PEM
ssl.truststore.location=/etc/kafka/tls/ca-chain.pem
EOF
chmod 600 /root/kafka-admin.properties
B=kafka01.example.local:9094
/opt/kafka/bin/kafka-configs.sh --bootstrap-server $B --command-config /root/kafka-admin.properties \
  --alter --add-config 'SCRAM-SHA-512=[iterations=8192,password=ПАРОЛЬ_ERP]' --entity-type users --entity-name erp-1c
/opt/kafka/bin/kafka-configs.sh --bootstrap-server $B --command-config /root/kafka-admin.properties \
  --describe --entity-type users --entity-name erp-1c        # проверка: SCRAM-SHA-512 iterations=8192
```

Число итераций по умолчанию — 4096, это и минимум; соль генерируется случайно [Kafka-док 4.4]. Удалить учётную запись — `--alter --delete-config 'SCRAM-SHA-512' --entity-type users --entity-name erp-1c`.

### 3.2. Включение на работающем кластере

Порядок из документации («Incorporating Security Features in a Running Cluster»): добавить новый защищённый слушатель рядом со старым (перезапуск узлов по одному), перевести клиентов, переключить межброкерный обмен, затем убрать `PLAINTEXT` (ещё один проход перезапусков) [Kafka-док 4.4 `incorporating-security-features-in-a-running-cluster`]. Слушателя без пароля для клиентов на время переезда оставляйте только во внутренней сети.

### 3.3. Другие механизмы

| Механизм | Когда | Замечание |
|---|---|---|
| `PLAIN` | Пароли в файле/настройках брокера (или внешняя проверка через свой обработчик) | Пароль передаётся как есть — только с TLS [Kafka-док 4.4] |
| `GSSAPI` (Kerberos) | В домене AD, единые учётные записи служб | Нужны принципалы и keytab для брокеров и клиентов; подробно о Kerberos в стенде — `../1c/08-…` |
| `OAUTHBEARER` | Есть сервер OIDC (Keycloak и т. п.) | С 4.4 при проверке по JWKS обязательны `expected.audience`/`expected.issuer`; адреса JWKS — в системном свойстве `org.apache.kafka.sasl.oauthbearer.allowed.urls` (с 4.0, по умолчанию пусто) [Kafka-док 4.4 `upgrade`] |
| `SSL` с сертификатом клиента | Системы, которые умеют mTLS | Имя пользователя — DN сертификата, сокращается правилами `ssl.principal.mapping.rules` [Kafka-док 4.4 `authorization-and-acls`] |

## 4. ACL: кто что может

### 4.1. Включение

```properties
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
super.users=User:admin
# allow.everyone.if.no.acl.found не задавать (по умолчанию false)
```

ACL хранятся в метаданных кластера. Административные запросы (создание и удаление тем) клиент шлёт брокеру, брокер пересылает контроллеру, и права проверяются на контроллере — поэтому `authorizer.class.name` и `super.users` нужны **и на контроллерах** [Kafka-док 4.4 «KRaft Principal Forwarding»; вывод о контроллерах — ⚠ по смыслу раздела, проверить на стенде].

Имена в `super.users` разделяются **точкой с запятой** (в именах из сертификатов бывают запятые); тип `User` чувствителен к регистру [Kafka-док 4.4].

### 4.2. Типовой набор для обмена 1С

Схема: ERP пишет в `erp.*` и читает `site.orders.v1`; мост пишет и читает от своего имени; аналитика только читает `erp.*`.

```bash
A="/opt/kafka/bin/kafka-acls.sh --bootstrap-server kafka01.example.local:9094 --command-config /root/kafka-admin.properties"
# ERP: запись во все темы с префиксом erp.
$A --add --allow-principal User:erp-1c --producer --topic erp. --resource-pattern-type prefixed
# ERP: чтение заказов сайта группой erp-1c-orders
$A --add --allow-principal User:erp-1c --consumer --topic site.orders.v1 --group erp-1c-orders
# Аналитика: только чтение erp.* своей группой
$A --add --allow-principal User:bi --consumer --topic erp. --resource-pattern-type prefixed --group bi- --resource-pattern-type prefixed
# Проверка
$A --list --principal User:erp-1c
```

`--producer` даёт `Write`, `Describe`, `Create` на тему; `--consumer` — `Read`, `Describe` на тему и `Read` на группу [Kafka-док 4.4 `authorization-and-acls`]. Сочетание одного `--resource-pattern-type prefixed` для темы и группы в одной команде — ⚠ (тип шаблона, вероятно, применяется к обоим ресурсам; если нужен разный — две команды). Транзакционным производителям нужны ещё права на `TransactionalId`; идемпотентной записи (умолчание клиентов) отдельное право `IdempotentWrite` на кластер с 2.8 не требуется ⚠ (сверить в таблице операций документации).

Ограничить узлы-источники: `--allow-host 10.0.0.11` (адрес сервера 1С) — проверка по IP-адресу клиента [Kafka-док 4.4].

## 5. Кластер

### 5.1. Схема

| Роль | Узлы | `process.roles` | Порты |
|---|---|---|---|
| Контроллеры | 3 (`kctl01…03`), небольшие ВМ: ~5 ГБ ОЗУ, ~5 ГБ диска под метаданные | `controller` | 9093 |
| Брокеры | 3+ (`kafka01…03`) | `broker` | 9094 (клиенты, `SASL_SSL`) |

Смешанный режим документация в работе не рекомендует: контроллер хуже изолирован, его нельзя перезапускать и наращивать отдельно от брокеров [Kafka-док 4.4 `kraft`]. Для небольшой установки обмена 1С компромисс — три узла в смешанном режиме [практика ⚠ — сознательное отступление от рекомендации].

### 5.2. Настройки

Контроллер (`/etc/kafka/controller.properties`, по образцу `config/controller.properties` [Kafka-код 4.4]):

```properties
process.roles=controller
node.id=1                                     # 1,2,3 — уникально в кластере
controller.quorum.bootstrap.servers=kctl01.example.local:9093,kctl02.example.local:9093,kctl03.example.local:9093
listeners=CONTROLLER://kctl01.example.local:9093
advertised.listeners=CONTROLLER://kctl01.example.local:9093
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,SASL_SSL:SASL_SSL
log.dirs=/var/lib/kafka/metadata
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
super.users=User:admin
```

Брокер (`/etc/kafka/server.properties`):

```properties
process.roles=broker
node.id=11                                    # 11,12,13 — не пересекаются с контроллерами
controller.quorum.bootstrap.servers=kctl01.example.local:9093,kctl02.example.local:9093,kctl03.example.local:9093
controller.listener.names=CONTROLLER
listeners=SASL_SSL://0.0.0.0:9094
advertised.listeners=SASL_SSL://kafka01.example.local:9094
listener.security.protocol.map=CONTROLLER:PLAINTEXT,SASL_SSL:SASL_SSL
inter.broker.listener.name=SASL_SSL
log.dirs=/var/lib/kafka/data
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
auto.create.topics.enable=false
unclean.leader.election.enable=false
# + SASL (3.1), TLS (2.2), ACL (4.1)
```

Брокер не открывает у себя слушателя контроллеров, но обязан описать его протокол в `listener.security.protocol.map` [Kafka-док 4.4 `listener-configuration`]. `unclean.leader.election.enable=false` — умолчание [Kafka-код 4.4 `LogConfig`]; записано явно, чтобы его не включили «для скорости»: при `true` лидером может стать отставшая реплика, и подтверждённые сообщения потеряются.

### 5.3. Разметка

```bash
# один раз, на любой машине
CLUSTER_ID="$(/opt/kafka/bin/kafka-storage.sh random-uuid)"
# вариант А (рекомендуемый): первый контроллер — один голосующий, остальные добавить
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format --cluster-id $CLUSTER_ID --standalone -c /etc/kafka/controller.properties   # kctl01
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format --cluster-id $CLUSTER_ID --no-initial-controllers -c /etc/kafka/controller.properties  # kctl02, kctl03
# после запуска kctl02/03 и догоняния — на каждом из них:
/opt/kafka/bin/kafka-metadata-quorum.sh --command-config /etc/kafka/controller.properties --bootstrap-controller kctl01.example.local:9093 add-controller
# брокеры — без доп. ключей (+ --add-scram для admin, если SCRAM)
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format --cluster-id $CLUSTER_ID -c /etc/kafka/server.properties
```

Вариант Б — все три контроллера сразу ключом `--initial-controllers "1@kctl01.example.local:9093:<UUID1>,2@…:<UUID2>,3@…:<UUID3>"` с одинаковым значением на всех; UUID каталогов заранее получают через `kafka-storage.sh random-uuid` [Kafka-док 4.4 `kraft`]. Оба способа дают **динамический** кворум (`kraft.version=1`); статический (`controller.quorum.voters`) остался для старых кластеров. Где в варианте А указывать `--add-scram` (на контроллере, размечаемом `--standalone`, — там создаются начальные метаданные) — ⚠ проверить на стенде.

Проверка кворума:

```bash
/opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-controller kctl01.example.local:9093 describe --status
/opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-controller kctl01.example.local:9093 describe --replication
/opt/kafka/bin/kafka-features.sh --bootstrap-controller kctl01.example.local:9093 describe   # kraft.version FinalizedVersionLevel: 1
```

### 5.4. Надёжность записи — сочетание настроек

| Где | Настройка | Значение | Почему |
|---|---|---|---|
| Тема/брокер | `replication.factor` | 3 | Три копии |
| Тема/брокер | `min.insync.replicas` | 2 | Запись с `acks=all` подтверждается, если живы ≥ 2 копии; при одной живой — ошибка `NotEnoughReplicas`, а не тихая потеря |
| Производитель | `acks` | `all` (умолчание с 3.0) | Ждать подтверждения от ISR [Kafka-код 4.4 `ProducerConfig`] |
| Производитель | `enable.idempotence` | `true` (умолчание) | Повтор отправки не создаёт дублей в разделе; выключается сам, если `acks` ≠ `all` [Kafka-код 4.4 `ProducerConfig`] |
| Потребитель | `enable.auto.commit` | `false` для обмена 1С | Фиксировать смещение после того, как 1С записала данные; умолчание клиента — `true` [Kafka-код 4.4 `ConsumerConfig`] |
| Потребитель | `auto.offset.reset` | `earliest` для новой группы обмена | Умолчание `latest`: новая группа пропустит всё, что было до её создания [Kafka-код 4.4 `ConsumerConfig`] |

Важно для HTTP-моста: в его примере `application.properties` стоит `kafka.producer.acks=1` — для обмена поменяйте на `all` (см. `03-…`).

## 6. Мониторинг

### 6.1. Метрики JMX

Удалённый JMX по умолчанию выключен; включить — переменная `JMX_PORT` для процессов, запущенных сценариями `bin/` [Kafka-док 4.4 `monitoring`; Kafka-код 4.4 `kafka-run-class.sh`]. Без аутентификации и TLS удалённый JMX открывать нельзя — документация прямо требует защиту [там же]. Удобнее не открывать JMX наружу, а запускать сборщик агентом внутри JVM (6.2).

| Метрика (MBean) | Норма | Что значит отклонение |
|---|---|---|
| `kafka.controller:type=KafkaController,name=ActiveControllerCount` | 1 ровно на одном узле | 0 везде — нет активного контроллера |
| `kafka.controller:type=KafkaController,name=OfflinePartitionsCount` | 0 | Есть разделы без лидера — запись/чтение их невозможны |
| `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions` | 0 | Реплики отстают или брокер недоступен |
| `kafka.server:type=ReplicaManager,name=UnderMinIsrPartitionCount` | 0 | Запись с `acks=all` в эти разделы отклоняется |
| `kafka.server:type=ReplicaManager,name=IsrShrinksPerSec` / `IsrExpandsPerSec` | 0 вне перезапусков | Частые колебания — сеть, диск, GC |
| `kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent` | > 0,3 | Не хватает потоков `num.io.threads` или диска |
| `kafka.network:type=SocketServer,name=NetworkProcessorAvgIdlePercent` | > 0,3 | Не хватает `num.network.threads` |
| `kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce` | стабильно | Рост — медленный диск, репликация |
| `kafka.controller:type=KafkaController,name=MetadataErrorCount` | 0 | Ошибки применения метаданных |
| Потребитель: `kafka.consumer:type=consumer-fetch-manager-metrics,client-id=…` атрибут `records-lag-max` | мало | Публикует **клиент**, не брокер |

Источник таблицы — [Kafka-док 4.4 `monitoring`]. В 4.4 часть метрик координатора групп в формате Yammer объявлена устаревшей (удаление в 5.0), замена — `kafka.server:type=group-coordinator-metrics,…` [Kafka-док 4.4 `upgrade`].

### 6.2. Prometheus и Grafana

В поставке Kafka экспорта в Prometheus нет. Обычные варианты [сторонний]:

- **Prometheus JMX Exporter** (`prometheus/jmx_exporter`, выпуск 1.7.0 от 06.10.2026) — Java-агент: в юните добавить `Environment="KAFKA_OPTS=-javaagent:/opt/jmx_exporter/jmx_prometheus_javaagent.jar=7071:/etc/kafka/jmx-exporter.yml"`, правила выборки MBean — в YAML. Точное имя файла агента в выпуске 1.7.0 и готовые правила для Kafka — ⚠ сверить в репозитории проекта.
- **kafka_exporter** (`danielqsj/kafka_exporter`, v1.10.0 от 08.09.2026) — отдельный процесс, ходит в Kafka как клиент и отдаёт отставание групп и смещения разделов. Удобен для главного вопроса «обмен 1С отстаёт?».

Хранить метрики можно в том же Prometheus/Grafana, что и для остального стенда; Loki для метрик не подходит (он для журналов, см. `../observability/03-…`).

### 6.3. Журналы

| Файл (`LOG_DIR`, у нас `/var/log/kafka`) | Что там |
|---|---|
| `server.log` | Основной журнал брокера/контроллера |
| `controller.log` | События контроллера |
| `state-change.log` | Смены лидеров и ISR (имя ротации исправлено в 4.0.1: было `stage-change.log.*`) |
| `kafka-authorizer.log` | Отказы и решения ACL (уровень задаётся в `log4j2.yaml`) |
| `kafkaServer-gc.log` | Журнал сборщика мусора (ключ `-loggc` в `kafka-server-start.sh`) |

Список файлов — по `config/log4j2.yaml` ⚠ (сверить в своей установке); `-loggc` — [Kafka-код 4.4 `kafka-server-start.sh`]; переименование `state-change.log` — [Kafka-док 4.4 `upgrade` 4.0.1]. Отправить `server.log` в Loki — тем же агентом, что и журналы 1С (`../observability/03-…`).

### 6.4. Проверки «одной командой»

```bash
K=/opt/kafka/bin; C="--bootstrap-server kafka01.example.local:9094 --command-config /root/kafka-admin.properties"
$K/kafka-topics.sh $C --describe --under-replicated-partitions      # пусто = норма
$K/kafka-topics.sh $C --describe --unavailable-partitions           # пусто = норма
$K/kafka-topics.sh $C --describe --under-min-isr-partitions         # пусто = норма
$K/kafka-consumer-groups.sh $C --describe --group erp-1c-orders     # LAG по разделам
$K/kafka-consumer-groups.sh $C --list
$K/kafka-cluster.sh api-versions $C                                 # 4.4: замена kafka-broker-api-versions.sh
```

Ключи `--under-replicated-partitions`, `--unavailable-partitions`, `--under-min-isr-partitions` (и `--at-min-isr-partitions`) есть в `TopicCommand` ветки 4.4 [Kafka-код 4.4].

## 7. Обслуживание

### 7.1. Перезапуск узла

- `systemctl restart kafka` — штатная остановка: сброс журналов на диск и передача лидерства разделов другим репликам [Kafka-док 4.4 «Graceful shutdown»; там же упомянута настройка `controlled.shutdown.enable=true` — действует ли она в KRaft или брокер всегда просит контроллер о передаче лидерства сам, ⚠ не сверено с кодом]. Передача лидерства удаётся, только если у всех разделов узла фактор репликации > 1 и есть живая реплика.
- Перезапускать узлы **по одному**, дожидаясь пустого `--under-replicated-partitions`.
- После перезапусков лидеры могут скопиться на части узлов; Kafka выравнивает это сама (`auto.leader.rebalance.enable`) или вручную `kafka-leader-election.sh --election-type preferred --all-topic-partitions` [Kafka-док 4.4 «Balancing leadership»; ключи `--election-type`, `--all-topic-partitions` есть в `LeaderElectionCommand` ветки 4.4].

### 7.2. Темы

| Действие | Команда | Оговорка |
|---|---|---|
| Изменить срок хранения | `kafka-configs.sh … --entity-type topics --entity-name T --alter --add-config retention.ms=…` | Действует сразу |
| Вернуть умолчание | `… --alter --delete-config retention.ms` | С 4.3 удаление несуществующего ключа — не ошибка [Kafka-док 4.4 `upgrade`] |
| Добавить разделы | `kafka-topics.sh … --alter --topic T --partitions N` | Уменьшить нельзя; меняется раздел для ключей; новые разделы потребитель с `auto.offset.reset=latest` может частично пропустить — документация советует `by_duration:<срок>` [Kafka-док 4.4 «Modifying topics»] |
| Удалить тему | `kafka-topics.sh … --delete --topic T` | Необратимо |
| Служебные темы | `__consumer_offsets`, `__transaction_state`, `__share_group_state`, `__cluster_metadata` | Разделы в них **никогда** не добавлять вручную [там же] |

### 7.3. Смещения групп (переобработка обмена)

Перечитать заказы сайта за сутки в 1С (группа должна быть остановлена — все потребители отключены):

```bash
$K/kafka-consumer-groups.sh $C --group erp-1c-orders --topic site.orders.v1 --reset-offsets --by-duration P1D --dry-run
$K/kafka-consumer-groups.sh $C --group erp-1c-orders --topic site.orders.v1 --reset-offsets --by-duration P1D --execute
```

Варианты: `--to-earliest`, `--to-latest`, `--to-datetime 2026-10-19T00:00:00.000`, `--shift-by -100`, `--from-file`; без `--execute` команда только показывает, что сделает [Kafka-док 4.4 «Managing consumer groups»]. Переобработка в 1С безопасна, только если обработчик идемпотентен (см. `03-…`, раздел 5).

### 7.4. Перенос разделов, вывод узла

Добавленный брокер не получает старые разделы сам: план переноса строит `kafka-reassign-partitions.sh --generate`, выполняет `--execute`, контролирует `--verify`; скорость ограничивается `--throttle` [Kafka-док 4.4 «Expanding your cluster», «Limiting bandwidth»]. Вывод брокера — сначала перенести с него разделы, затем остановить; каталог данных — с 4.3 можно «оцепить» (cordon, KIP-1066) [Kafka-док 4.4 `upgrade` 4.3.0].

### 7.5. Резервирование и восстановление

| Что | Чем | Замечание |
|---|---|---|
| Сообщения | Репликация внутри кластера; **MirrorMaker 2** — копия в другой кластер | Снимок каталога данных живого брокера целостной копией не является [практика] |
| Настройки | Копия `/etc/kafka`, `/etc/systemd/system/kafka.service` | Включая пароли и ключи — хранить как секреты |
| Метаданные (темы, ACL, SCRAM) | Живут в `__cluster_metadata` на контроллерах; выгрузка для справки: `kafka-topics.sh --describe`, `kafka-acls.sh --list`, `kafka-configs.sh --describe --entity-type users` | Скрипт пересоздания тем и ACL держите в Git |
| Идентификатор кластера | `/etc/kafka/cluster-id`, `meta.properties` | Нужен для разметки новых узлов |

Для обмена 1С потеря Kafka не катастрофа, если в 1С есть очередь отправки (outbox) и возможность переотправить период — это и есть «резервная копия» обмена (`03-…`, раздел 5).

## 8. Обновление

### 8.1. Порядок (из любой версии 3.3.x–4.3.x на 4.4.0)

1. Прочитать «Notable changes» целевого выпуска в `upgrade.md` [Kafka-док 4.4].
2. Обновить программу на узлах **по одному** (контроллеры, затем брокеры [практика]): остановить, сменить ссылку `/opt/kafka`, запустить, дождаться пустого `--under-replicated-partitions`.
3. Проверить работу кластера и клиентов (обмен 1С, мост) на новой программе.
4. Завершить обновление метаданных:

```bash
/opt/kafka/bin/kafka-features.sh --bootstrap-server kafka01.example.local:9094 --command-config /root/kafka-admin.properties upgrade --release-version 4.4
/opt/kafka/bin/kafka-features.sh --bootstrap-server kafka01.example.local:9094 --command-config /root/kafka-admin.properties describe
```

После шага 4 **откат метаданных не поддерживается** для версий с изменениями метаданных [Kafka-док 4.4 `upgrade` 4.3.0]. До шага 4 можно вернуть старую программу, но с 4.4 хранилище, размеченное утилитой 4.4 (новые узлы), старый брокер не запустит (KIP-1170) [Kafka-док 4.4 `upgrade` 4.4.0].

### 8.2. Особые случаи

| Откуда | Как |
|---|---|
| ZooKeeper, любая версия | Обновиться до 3.9.x, мигрировать на KRaft по документации 3.9, затем на 4.x [Kafka-док 4.4 `kraft`] |
| KRaft старше 3.3 | Сначала 3.9.x [Kafka-док 4.4 `upgrade`] |
| Статический кворум (`controller.quorum.voters`) | После обновления до 4.1+: `kafka-features.sh … upgrade --feature kraft.version=1`, затем заменить `controller.quorum.voters` на `controller.quorum.bootstrap.servers` на всех узлах [Kafka-док 4.4 `kraft`] |
| Клиенты старше 2.1 | Обновить клиентов до перехода брокеров на 4.x [Kafka-док 4.4 `upgrade` 4.0.0] |
| Свои настройки Log4j 1.x | Перевести в `log4j2.yaml` (`log4j-transform-cli`) [там же] |
| Docker | Сменить метку образа (`apache/kafka:4.4.0`), `docker compose up -d`; том с данными сохраняется. Шаг 4 — так же `kafka-features.sh` внутри контейнера |

## 9. Контрольный список «Kafka готова к работе с 1С»

1. Слушатель клиентов `SASL_SSL`, `PLAINTEXT` для клиентов отключён; порт контроллеров закрыт экраном.
2. У каждой системы своя учётная запись SCRAM; `super.users` — только администратор.
3. ACL выданы по префиксам тем и группам; `allow.everyone.if.no.acl.found` не включён.
4. Темы обмена: `replication.factor=3`, `min.insync.replicas=2`, срок хранения ≥ 7 суток; `auto.create.topics.enable=false`.
5. Сертификаты: `serverAuth`+`clientAuth`, полная цепочка, имена в SAN; напоминание о сроке действия.
6. Метрики собираются; оповещения на `UnderMinIsrPartitionCount > 0`, `OfflinePartitionsCount > 0`, отсутствие активного контроллера, отставание групп обмена.
7. Скрипт пересоздания тем и ACL — в Git; копия `/etc/kafka` — в хранилище секретов.
8. Порядок обновления опробован на стенде.

## Источники

- Документация Kafka 4.4: `raw.githubusercontent.com/apache/kafka/4.4/docs/security/*.md`, `…/operations/{kraft,basic-kafka-operations,monitoring,hardware-and-os}.md`, `…/getting-started/upgrade.md`.
- Код ветки `4.4`: `config/controller.properties`, `config/broker.properties`, `bin/kafka-run-class.sh`, `bin/kafka-server-start.sh`, `clients/…/SslConfigs.java`, `clients/…/producer/ProducerConfig.java`, `clients/…/consumer/ConsumerConfig.java`, `storage/…/LogConfig.java`.
- Prometheus JMX Exporter — `github.com/prometheus/jmx_exporter` (выпуск 1.7.0); kafka_exporter — `github.com/danielqsj/kafka_exporter` (v1.10.0); даты — API выпусков GitHub, 20.10.2026.
