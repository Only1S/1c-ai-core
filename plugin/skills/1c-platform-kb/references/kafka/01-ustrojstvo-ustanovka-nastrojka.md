# Apache Kafka: устройство, версии, установка на Ubuntu и в Docker, базовая настройка

> **Официальные тексты по теме**: документация Apache Kafka 4.4 — исходники в репозитории `apache/kafka`, ветка `4.4`, каталог `docs/` (`getting-started/quickstart.md`, `getting-started/docker.md`, `getting-started/upgrade.md`, `getting-started/compatibility.md`, `operations/kraft.md`, `operations/java-version.md`, `operations/hardware-and-os.md`, `design/design.md`); образ Docker — `docker/examples/README.md`, `docker/jvm/Dockerfile`, `docker/resources/common-scripts/*`; файл `config/server.properties` и сценарии `bin/kafka-server-start.sh`, `bin/kafka-run-class.sh` той же ветки; страница загрузок `kafka.apache.org/community/downloads/` и каталог `downloads.apache.org/kafka/`.

> Статус: написано 20.10.2026 по первоисточникам (документация и исходный код ветки `4.4`, страница загрузок, пакеты Ubuntu 24.04); на сервере не запускалось. Независимой сверки не было. Непроверенное помечено «⚠».

> Область: Kafka как отдельный сервис для обмена данными между 1С и другими системами — что это, какую версию брать, как поставить на Ubuntu Server (из архива под systemd) или в Docker, как правильно настроить слушателей и каталоги. Безопасность, кластер, мониторинг и обновление — `02-…`; как 1С отправляет и получает сообщения — `03-…`.

Пометки в тексте:

- **[Kafka-док 4.4]** — документация Kafka 4.4 (каталог `docs/` ветки `4.4`, опубликована на kafka.apache.org);
- **[Kafka-код 4.4]** — исходный код и файлы ветки `4.4` (`config/`, `bin/`, `docker/`, классы `*Configs.java`);
- **[Kafka-сайт]** — страница загрузок kafka.apache.org и каталог downloads.apache.org (проверено 20.10.2026);
- **[Ubuntu]** — packages.ubuntu.com;
- **[практика]** — опыт сообщества, первоисточником не подтверждён;
- **⚠** — не подтверждено, с пояснением что именно.

Связанные статьи:

- `02-bezopasnost-klaster-monitoring-obsluzhivanie.md` — TLS, SASL/SCRAM, ACL, кластер из нескольких узлов, метрики, обслуживание, обновление;
- `03-obmen-1c-s-kafka.md` — обмен 1С с Kafka: HTTP-мост, внешние компоненты, «1С:Шина», шаблон outbox;
- `../observability/01-…` — WSL2 и Docker Engine на ПК (стенд);
- `../linux/05-…` (systemd), `../linux/07-…` (диски), `../linux/09-…` (параметры ядра), `../linux/01-shell-osnovy.md` (почему `/tmp` — не место для данных).

Условные обозначения: узел Kafka — `kafka01.example.local` (`10.0.0.21`); пользователь ОС — `kafka`; программа — `/opt/kafka`, настройки — `/etc/kafka`, данные — `/var/lib/kafka`, журналы — `/var/log/kafka`. Команды выполняет администратор через `sudo`, если не сказано иное.

## Кратко — главные факты

1. **Kafka — не очередь, а журнал.** Сообщения пишутся в разделы (partitions) тем (topics) и хранятся заданный срок (по умолчанию `log.retention.hours=168`, 7 суток) независимо от того, прочитаны они или нет. Каждый получатель (группа потребителей) сам помнит, докуда дочитал (смещение, offset). Порядок гарантирован только внутри одного раздела [Kafka-док 4.4 `design`, `introduction`].
2. **Версии на 20.10.2026.** Поддерживаемые выпуски по странице загрузок: **4.3.1** (25.06.2026), **4.2.2** (29.09.2026), **4.1.2** (17.03.2026). Файлы выпуска **4.4.0** лежат на `downloads.apache.org` с 15.10.2026, и документация ветки `4.4` уже ссылается на него, но страница загрузок его ещё не показывает. План проекта — три выпуска в год, исправления выпускаются только для поддерживаемых веток [Kafka-сайт].
3. **С 4.0 (18.03.2025) ZooKeeper удалён — только KRaft.** Метаданные кластера хранят сами узлы Kafka в роли контроллера. Перейти с ZooKeeper можно только через выпуск-«мост» 3.9 [Kafka-док 4.4 `upgrade`, `kraft`].
4. **Java:** брокеру, Connect и утилитам нужна Java 17+; полностью поддерживаются 17, 21 и 25, рекомендуется последняя LTS — **25**. Клиентам и Streams достаточно Java 11 [Kafka-док 4.4 `java-version`, `upgrade` 4.0.0]. В Ubuntu 24.04 есть `openjdk-25-jre-headless` (25.0.4.1), `openjdk-21-…`, `openjdk-17-…` [Ubuntu].
5. **Пакета `kafka` в Ubuntu нет** (есть только клиентские `librdkafka1` и `kcat`) [Ubuntu]. Ставят из архива `kafka_2.13-<версия>.tgz` под свой юнит systemd или из образа Docker `apache/kafka:<версия>`.
6. **Хранилище нужно разметить до первого запуска:** `kafka-storage.sh random-uuid` → `kafka-storage.sh format …`. Kafka больше не размечает пустые каталоги сама [Kafka-док 4.4 `kraft`].
7. **В поставляемом `config/server.properties` данные лежат в `/tmp/kraft-combined-logs`.** Это пример, а не рабочая настройка: `/tmp` в Ubuntu очищается при загрузке (в 26.04 — вообще в ОЗУ). Сразу задайте `log.dirs` на отдельном диске [Kafka-код 4.4 `config/server.properties`; `../linux/01-shell-osnovy.md`].
8. **Главная ошибка настройки — `advertised.listeners`.** Клиент подключается по адресу из `bootstrap.servers`, получает в ответ адреса из `advertised.listeners` и дальше ходит уже по ним. Если там `localhost` или имя контейнера, внешний клиент (сервер 1С, мост) соединится и тут же «потеряет» брокер.
9. **Смешанный режим (`process.roles=broker,controller`) — только для стенда.** В работе контроллеры отдельно от брокеров, их 3 или 5 (выдерживают 1 или 2 отказа) [Kafka-док 4.4 `kraft`].
10. **Умолчания, которые стоит поменять сразу:** `auto.create.topics.enable=true` (тема создаётся при первой записи — опечатка в имени темы молча создаст новую), `default.replication.factor=1`, `min.insync.replicas=1` [Kafka-код 4.4 `ServerLogConfigs`, `ReplicationConfigs`]. Для стенда из одного узла это допустимо, для работы — см. `02-…`, раздел 4.
11. **Предел сообщения по умолчанию — около 1 МБ** (`message.max.bytes` = 1 048 588 байт) [Kafka-код 4.4]. Выгрузку 1С в десятки мегабайт в одно сообщение не кладите — режьте на части или передавайте ссылку на файл.
12. **Отдельный сервер или контейнер.** Kafka (JVM, страничный кэш, интенсивная запись) не ставится на ВМ с «PostgreSQL для 1С» и на рабочий сервер 1С — то же правило, что для GlitchTip, Redmine и NetBox.
13. **Образ `apache/kafka-native` (GraalVM) — экспериментальный**, для разработки и проверок, не для работы [Kafka-док 4.4 `docker`].

## 1. Что такое Kafka и когда она нужна для 1С

### 1.1. Понятия

| Понятие | Что это | Что важно администратору |
|---|---|---|
| Брокер (broker) | Процесс Kafka, хранящий разделы тем и обслуживающий клиентов | Порт клиентов (обычно 9092), каталоги `log.dirs` |
| Контроллер (controller) | Процесс Kafka, хранящий метаданные кластера (темы, разделы, ACL, учётные записи SCRAM) в журнале `__cluster_metadata` | Кворум 3 или 5; порт контроллеров (обычно 9093) |
| Тема (topic) | Именованный поток сообщений | Число разделов, коэффициент репликации, срок хранения |
| Раздел (partition) | Упорядоченный журнал внутри темы; единица параллелизма | Порядок сообщений есть только внутри раздела |
| Ключ сообщения (key) | Строка или байты; по нему клиент выбирает раздел (хеш ключа) | Все сообщения с одним ключом попадают в один раздел и читаются по порядку |
| Смещение (offset) | Номер сообщения в разделе | Группа потребителей сохраняет смещения в служебной теме `__consumer_offsets` |
| Группа потребителей (consumer group) | Несколько потребителей делят разделы темы между собой | Отставание группы (lag) — главный показатель «обмен встал» |
| Реплика, ISR | Копии раздела на разных брокерах; ISR — реплики, не отставшие от ведущей | `min.insync.replicas` + `acks=all` = подтверждение записи только после копирования |

Kafka не удаляет сообщение после чтения: получатель может перечитать тему с нужного места (`kafka-consumer-groups.sh --reset-offsets`, см. `02-…`, раздел 7). Это главное отличие от RabbitMQ, где сообщение после подтверждения из очереди уходит.

### 1.2. Kafka или RabbitMQ для обмена с 1С

| Задача | Kafka | RabbitMQ |
|---|---|---|
| Поток событий, который читают несколько независимых систем (аналитика, сайт, склад) | Подходит: каждая система — своя группа, у каждой своё смещение | Нужна отдельная очередь на каждого получателя (обменник fanout/topic) |
| Перечитать события за прошлую неделю | Да, в пределах срока хранения | Нет (кроме потоков — streams) |
| Маршрутизация по сложным правилам, приоритеты, отложенная доставка | Нет, только темы и разделы | Да: обменники, привязки, заголовки |
| Подключение 1С «из коробки» | Нет ни встроенного средства, ни узла в «1С:Шине» версии 3 (см. `03-…`) | «1С:Шина» имеет узлы RabbitMQ; есть открытые внешние компоненты |
| Эксплуатация | JVM, кворум контроллеров, разметка хранилища | Проще для одного узла; кластер — от 3 узлов |

**Вывод для обмена 1С с 1С и с парой внешних систем:** RabbitMQ проще. Kafka берут, когда в организации она уже есть как шина событий или нужна потоковая обработка и повторное чтение. Подробности о RabbitMQ — `../rabbitmq/`.

## 2. Версии и выбор выпуска

### 2.1. Что есть на 20.10.2026

| Выпуск | Дата | Состояние |
|---|---|---|
| 4.4.0 | файлы на `downloads.apache.org` от 15.10.2026 | Новый, страница загрузок пока не обновлена ⚠ (официальное объявление не найдено) |
| 4.3.1 | 25.06.2026 | Поддерживается (последний на странице загрузок) |
| 4.2.2 | 29.09.2026 | Поддерживается |
| 4.1.2 | 17.03.2026 | Поддерживается |
| 4.0.x | 4.0.0 — 18.03.2025, 4.0.2 — 16.03.2026 | В архиве |
| 3.9.x | последний 3.9.2 | В архиве; последний выпуск с ZooKeeper, «мост» для перехода на KRaft |

Источник — [Kafka-сайт]. Сроков поддержки в годах у Kafka нет: поддерживаются несколько последних веток, исправления выходят по мере надобности.

**Что выбрать.** Для нового стенда — 4.4.0 (документация уже под неё). Для рабочего кластера — последний выпуск поддерживаемой ветки, обычно на одну ветку старше новейшей (сейчас 4.3.1), и обновляться после выхода исправлений (x.y.1). Это рекомендация [практика], не требование проекта.

### 2.2. Что изменилось с 4.0 и важно администратору

- Удалён ZooKeeper; брокеры 4.x требуют KRaft и версию метаданных не ниже 3.3 [Kafka-док 4.4 `upgrade`].
- Брокер, Connect и утилиты — Java 17+, клиенты и Streams — Java 11+ [там же].
- Журналы — Log4j2: файл `config/log4j2.yaml` вместо `log4j.properties`; старые настройки переводятся утилитой `log4j-transform-cli` [там же].
- Каталог `config/kraft/` упразднён, все примеры — в `config/` [там же].
- `--bootstrap-server` принимает только список через запятую (`host1:9092,host2:9092`) [там же].
- Удалены старые версии протокола: клиенты и брокеры должны быть не старше 2.1 [там же]. Для внешних компонент 1С на `librdkafka` это не проблема, но старые самописные клиенты проверьте ⚠.
- Новый протокол перебалансировки групп (KIP-848) включается сам после завершения обновления до 4.0 [там же].

Изменения 4.4.0, заметные администратору [Kafka-док 4.4 `upgrade`]:

- хранилище, размеченное `kafka-storage` версии 4.4, не запускается более старым брокером (KIP-1170) — откат после разметки невозможен;
- `broker.id` объявлен устаревшим, использовать `node.id`;
- утилита `kafka-broker-api-versions.sh` устарела, замена — `kafka-cluster.sh api-versions`;
- контроллер можно снять с учёта (`kafka-cluster.sh unregister-controller`, `kafka-metadata-quorum.sh remove-controller --unregister`);
- брокер с проверкой токенов OAUTHBEARER по JWKS теперь не запускается без `sasl.oauthbearer.expected.audience`/`expected.issuer`.

## 3. Подготовка сервера Ubuntu

### 3.1. Ресурсы

| Ресурс | Стенд (1 узел) | Рабочий брокер | Источник |
|---|---|---|---|
| ЦП | 2 ядра | 4–8 ядер | [практика] |
| ОЗУ | 4 ГБ (куча 1–2 ГБ) | 16–32 ГБ: куча 4–6 ГБ, остальное — страничный кэш ОС | [Kafka-док 4.4 `java-version`, `hardware-and-os`]; цифры по ОЗУ — [практика] |
| ОЗУ контроллера | — | около 5 ГБ | [Kafka-док 4.4 `kraft`] |
| Диск данных | 20–50 ГБ | отдельный диск или несколько; XFS или ext4 | [Kafka-док 4.4 `hardware-and-os`] |
| Диск метаданных контроллера | — | около 5 ГБ | [Kafka-док 4.4 `kraft`] |

Документация советует считать память так: объём записи в секунду × 30 секунд должен помещаться в страничный кэш, тогда читатели «живых» данных не ходят на диск [Kafka-док 4.4 `hardware-and-os`]. Пример параметров JVM в документации — `-Xmx6g -Xms6g` с G1 для очень нагруженного кластера; для обмена 1С достаточно 2–4 ГБ [Kafka-док 4.4 `java-version`; размер для 1С — практика].

### 3.2. Диск, файловая система, ограничения

- Отдельный диск (или том LVM) под `log.dirs`, не общий с системой и журналами — так советует документация [Kafka-док 4.4 `hardware-and-os`]. Как разметить — `../linux/07-…`.
- Файловая система: XFS или ext4; по замерам авторов документации XFS быстрее на нагрузке Kafka [там же].
- RAID не обязателен: надёжность обеспечивает репликация между брокерами; несколько каталогов в `log.dirs` распределяются по разделам по кругу [там же].
- Принудительный `fsync` из Kafka по умолчанию выключен, и документация советует так и оставить: долговечность обеспечивает репликация, а не сброс на диск [там же].
- **Дескрипторы файлов: не меньше 100 000** для процесса брокера [там же] — в юните systemd `LimitNOFILE=100000` (ниже).
- **`vm.max_map_count`** ограничивает число разделов на брокер (на каждый сегмент — отображения индексов в память); в Ubuntu по умолчанию 65530 [Kafka-док 4.4 `hardware-and-os`; значение по умолчанию — ⚠ сверить `sysctl vm.max_map_count`]. Для сотен тем можно поднять до 262144 [практика] — как задавать параметры ядра, `../linux/09-…`.

### 3.3. Java

```bash
sudo apt update
sudo apt install openjdk-25-jre-headless    # или openjdk-21-jre-headless
java -version                               # проверка: 25.x или 21.x
```

Пакеты есть в Ubuntu 24.04 [Ubuntu]; в 22.04 набор версий OpenJDK другой ⚠ (сверить `apt-cache policy openjdk-21-jre-headless`).

## 4. Установка из архива под systemd

### 4.1. Получить и проверить архив

```bash
VER=4.4.0
cd /tmp
wget https://downloads.apache.org/kafka/$VER/kafka_2.13-$VER.tgz
wget https://downloads.apache.org/kafka/$VER/kafka_2.13-$VER.tgz.sha512
# сравнить контрольную сумму (файл .sha512 — в формате gpg --print-md, сравниваем глазами)
sha512sum kafka_2.13-$VER.tgz
cat kafka_2.13-$VER.tgz.sha512
```

Строгая проверка — подписью: `wget …/kafka_2.13-$VER.tgz.asc`, `wget https://downloads.apache.org/kafka/KEYS`, `gpg --import KEYS`, `gpg --verify kafka_2.13-$VER.tgz.asc kafka_2.13-$VER.tgz` [Kafka-сайт: «проверяйте каждую загрузку по процедуре и ключам KEYS»]. Формат файла `.sha512` — ⚠ (у разных проектов Apache разный; при расхождении формата сравнивайте само значение).

`2.13` в имени — версия Scala, с которой собран брокер; для 4.x другой нет (Scala 2.12 убрана в 4.0) [Kafka-док 4.4 `upgrade`].

### 4.2. Пользователь, каталоги, файлы

```bash
sudo useradd --system --home-dir /var/lib/kafka --shell /usr/sbin/nologin kafka
sudo tar -xzf /tmp/kafka_2.13-4.4.0.tgz -C /opt
sudo ln -sfn /opt/kafka_2.13-4.4.0 /opt/kafka          # обновление = смена ссылки
sudo mkdir -p /etc/kafka /var/lib/kafka/data /var/log/kafka
sudo cp /opt/kafka/config/server.properties /etc/kafka/server.properties
sudo cp /opt/kafka/config/log4j2.yaml /etc/kafka/log4j2.yaml
sudo chown -R kafka:kafka /var/lib/kafka /var/log/kafka
sudo chown -R root:kafka /etc/kafka && sudo chmod 750 /etc/kafka && sudo chmod 640 /etc/kafka/*
```

Настройки держим вне `/opt/kafka_*`, чтобы обновление программы их не затирало. Пароли (SCRAM, ключи TLS) появятся в `/etc/kafka` позже — отсюда права `640` и группа `kafka`.

### 4.3. `server.properties` для одиночного узла (стенд, тест)

Поставляемый файл описывает один узел в смешанном режиме [Kafka-код 4.4 `config/server.properties`]. Рабочая версия для узла `kafka01` (без шифрования — только для изолированного стенда; TLS и пароли — `02-…`):

```properties
# /etc/kafka/server.properties — одиночный узел (broker + controller), стенд
process.roles=broker,controller
node.id=1
controller.quorum.bootstrap.servers=kafka01.example.local:9093

# Слушатели: на чём узел принимает соединения ...
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://kafka01.example.local:9093
# ... и какой адрес сообщает клиентам. Только имя/адрес, по которому до узла дойдут клиенты!
advertised.listeners=PLAINTEXT://kafka01.example.local:9092
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,SSL:SSL,SASL_PLAINTEXT:SASL_PLAINTEXT,SASL_SSL:SASL_SSL

# Данные — НЕ в /tmp
log.dirs=/var/lib/kafka/data

# Темы: создавать явно, хранить 7 суток
auto.create.topics.enable=false
num.partitions=3
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# Один узел — служебные темы без реплик
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
share.coordinator.state.topic.replication.factor=1
share.coordinator.state.topic.min.isr=1

num.network.threads=3
num.io.threads=8
num.recovery.threads.per.data.dir=2
```

Пояснения:

- В поставляемом файле `advertised.listeners` включает и `CONTROLLER://localhost:9093` [Kafka-код 4.4]. Для контроллера адрес берётся из `controller.quorum.bootstrap.servers`; оставлять в `advertised.listeners` слушателя контроллера с `localhost` на машине, к которой подключаются извне, не нужно ⚠ (в документации прямого запрета нет — проверьте, что узел стартует, по журналу `server.log`).
- `0.0.0.0` в `listeners` — слушать на всех адресах; в `advertised.listeners` так писать нельзя.
- Служебные темы `__consumer_offsets` и `__transaction_state` создаются при первом обращении; при коэффициенте репликации 3 по умолчанию на одном узле они не создадутся — отсюда явные `…replication.factor=1` [Kafka-док 4.4 `docker/examples/README.md`: «пришлось задать 1, иначе берётся 3»].
- `num.partitions` действует только на автоматически создаваемые темы и на `kafka-topics.sh --create` без `--partitions` ⚠ (для второго случая — сверить `kafka-topics.sh --help`).

### 4.4. Разметка хранилища

```bash
cd /opt/kafka
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
echo "$KAFKA_CLUSTER_ID" | sudo tee /etc/kafka/cluster-id      # сохранить: понадобится для новых узлов
sudo -u kafka bin/kafka-storage.sh format --standalone -t "$KAFKA_CLUSTER_ID" -c /etc/kafka/server.properties
sudo -u kafka cat /var/lib/kafka/data/meta.properties          # проверка: cluster.id, node.id, directory.id
```

`--standalone` размечает узел как единственного голосующего контроллера; кворум получается динамическим, и контроллеры можно потом добавлять командой `kafka-metadata-quorum.sh add-controller` [Kafka-док 4.4 `kraft`]. Для кластера из трёх контроллеров — `--initial-controllers` или `--no-initial-controllers`, см. `02-…`, раздел 4.

**Повторная разметка уничтожает данные** узла. Если узел «не видит» каталог (`No meta.properties found in …`), сначала проверьте `log.dirs` и права, а не размечайте заново.

### 4.5. Юнит systemd

Поставки юнита у Kafka нет; пишем свой. Сценарий `kafka-server-start.sh` по умолчанию берёт `config/log4j2.yaml` рядом с программой и кучу `-Xmx1G -Xms1G`, а журналы приложения пишет в `LOG_DIR` (по умолчанию `<каталог>/logs`) [Kafka-код 4.4 `bin/kafka-server-start.sh`, `bin/kafka-run-class.sh`].

```ini
# /etc/systemd/system/kafka.service
[Unit]
Description=Apache Kafka (KRaft)
Documentation=https://kafka.apache.org/documentation/
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=kafka
Group=kafka
Environment="KAFKA_HEAP_OPTS=-Xms2g -Xmx2g"
Environment="KAFKA_LOG4J_OPTS=-Dlog4j2.configurationFile=/etc/kafka/log4j2.yaml"
Environment="LOG_DIR=/var/log/kafka"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /etc/kafka/server.properties
# SIGTERM -> штатная остановка: сброс журналов, передача лидерства; JVM выходит с кодом 143
SuccessExitStatus=143
TimeoutStopSec=180
Restart=on-failure
RestartSec=10
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kafka
systemctl status kafka --no-pager
sudo journalctl -u kafka -n 50 --no-pager
sudo tail -n 50 /var/log/kafka/server.log
ss -tlnp | grep -E ':(9092|9093)\b'           # проверка: слушает оба порта
```

Почему не `ExecStop=…/kafka-server-stop.sh`: этот сценарий ищет и останавливает **все** процессы `kafka.Kafka` на машине по выводу `ps` [Kafka-код 4.4 `bin/kafka-server-stop.sh`]. systemd и так посылает основному процессу SIGTERM, а Kafka на него выполняет штатную остановку [Kafka-док 4.4 `basic-kafka-operations` «Graceful shutdown»]. Код выхода 143 (128 + 15) после SIGTERM — норма JVM [практика]; `TimeoutStopSec` — запас на сброс журналов и передачу лидерства большого числа разделов.

### 4.6. Проверка: тема, запись, чтение

```bash
cd /opt/kafka
B=kafka01.example.local:9092
bin/kafka-topics.sh --bootstrap-server $B --create --topic test-1c --partitions 3 --replication-factor 1
bin/kafka-topics.sh --bootstrap-server $B --describe --topic test-1c
echo 'привет из 1С' | bin/kafka-console-producer.sh --bootstrap-server $B --topic test-1c
bin/kafka-console-consumer.sh --bootstrap-server $B --topic test-1c --from-beginning --max-messages 1
bin/kafka-metadata-quorum.sh --bootstrap-server $B describe --status    # LeaderId, CurrentVoters
```

Проверку стоит повторить **с другой машины** (например, с сервера 1С: `kcat -b kafka01.example.local:9092 -L` из пакета `kcat`) — так ловится ошибка в `advertised.listeners`.

### 4.7. Сетевой экран

| Порт | Кто подключается | Открыть для |
|---|---|---|
| 9092 (клиенты; позже 9094/SASL_SSL) | серверы 1С с внешней компонентой, HTTP-мост, другие системы | конкретных адресов |
| 9093 (контроллеры) | только узлы Kafka | только узлов кластера |
| 8080 (HTTP-мост, если есть) | серверы 1С | серверов 1С |

```bash
sudo ufw allow from 10.0.0.0/24 to any port 9092 proto tcp
sudo ufw status numbered
```

Подробнее о `ufw` — `../linux/08-…`.

## 5. Установка в Docker

Удобно для стенда (на ПК в WSL2 рядом с GlitchTip и Loki, см. `../observability/01-…`) и для небольших установок.

### 5.1. Что важно знать об образе `apache/kafka`

- Образ на основе `eclipse-temurin:25-jre-alpine`, процесс работает от пользователя `appuser` (uid 1000); каталоги `/var/lib/kafka/data`, `/etc/kafka/secrets`, `/mnt/shared/config` созданы в образе [Kafka-код 4.4 `docker/jvm/Dockerfile`].
- Нужен Docker **20.10.4 или новее**, иначе ошибка `/opt/kafka/config/ file not writable` [Kafka-код 4.4 `docker/examples/README.md`].
- Без своих настроек запускается одиночный узел со стандартным `server.properties`, то есть с данными в `/tmp/kraft-combined-logs` внутри контейнера — **после пересоздания контейнера данные пропадут** [там же; Kafka-код 4.4 `config/server.properties`].
- Если `CLUSTER_ID` не задан, сценарий запуска подставляет зашитый в образ идентификатор и сам размечает хранилище [Kafka-код 4.4 `docker/resources/common-scripts/configureDefaults`]. Задавайте свой (`kafka-storage.sh random-uuid` или любой 22-символьный base64url).
- Настройки передаются тремя способами: умолчание; свои файлы в томе `/mnt/shared/config`; переменные окружения. Переменные перекрывают файлы [Kafka-код 4.4 `docker/examples/README.md`].
- Правило имени переменной: `.` → `_`, `_` → `__`, `-` → `___`, приставка `KAFKA_`. Пример: `log.dirs` → `KAFKA_LOG_DIRS`, `offsets.topic.replication.factor` → `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` [там же].
- Уровень журнала — `KAFKA_LOG4J_ROOT_LOGLEVEL`; дополнительные логгеры — `KAFKA_LOG4J_LOGGERS='логгер=уровень,…'` [там же].

### 5.2. `docker-compose.yml` для стенда

```yaml
# kafka/docker-compose.yml — одиночный узел, данные в именованном томе
services:
  kafka:
    image: apache/kafka:4.4.0
    hostname: kafka
    container_name: kafka
    restart: unless-stopped
    ports:
      - "9092:9092"            # для клиентов снаружи Docker
    environment:
      CLUSTER_ID: "ЗАМЕНИТЬ_на_вывод_kafka-storage_random-uuid"
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: "broker,controller"
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:29093"
      KAFKA_LISTENERS: "CONTROLLER://:29093,INTERNAL://:19092,EXTERNAL://:9092"
      # INTERNAL — для контейнеров той же сети (мост, Kafka UI); EXTERNAL — адрес, по которому придут с серверов 1С
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka:19092,EXTERNAL://stand-pc.example.local:9092"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: "INTERNAL"
      KAFKA_CONTROLLER_LISTENER_NAMES: "CONTROLLER"
      KAFKA_LOG_DIRS: "/var/lib/kafka/data"
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_SHARE_COORDINATOR_STATE_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_SHARE_COORDINATOR_STATE_TOPIC_MIN_ISR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_HEAP_OPTS: "-Xms1g -Xmx1g"
    volumes:
      - kafka-data:/var/lib/kafka/data
volumes:
  kafka-data:
```

Основа — пример `docker-compose-files/single-node/plaintext` из репозитория Kafka [Kafka-код 4.4]: в нём слушатели `CONTROLLER`, `PLAINTEXT` (внутренний) и `PLAINTEXT_HOST` (`localhost:9092`) и `KAFKA_CONTROLLER_QUORUM_VOTERS` (статический кворум — для одиночного контейнера это нормально). Отличия здесь — том для данных, `KAFKA_LOG_DIRS`, запрет автосоздания тем и внешний адрес вместо `localhost`.

Проверка:

```bash
docker compose up -d
docker compose logs kafka | grep -i -E "error|started"     # ждём "Kafka Server started"
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 --create --topic test-1c --partitions 3 --replication-factor 1
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 --list
```

Фраза `Kafka Server started` в журнале — ⚠ (точный текст сверить в своём журнале). Утилиты лежат в образе в `/opt/kafka/bin` [Kafka-код 4.4 `docker/jvm/Dockerfile`].

**Права на том.** Процесс в контейнере — uid 1000. Если вместо именованного тома монтировать каталог хоста (`./data:/var/lib/kafka/data`), каталог должен принадлежать uid 1000, иначе `AccessDeniedException` при разметке ⚠ (сообщение — по опыту; сверить в журнале).

**WSL2.** Порт 9092, опубликованный из Docker внутри WSL2, доступен с Windows как `localhost:9092`, а с других машин — только если включён зеркальный сетевой режим или проброс порта; в `advertised.listeners` должен стоять адрес, по которому придёт клиент (подробно — `../observability/01-…`, разделы о сети WSL2).

### 5.3. Веб-интерфейс

В поставке Kafka веб-интерфейса нет. Для стенда используют сторонние (Kafka UI от Provectus, Redpanda Console, AKHQ) [практика]. Любой из них — отдельный контейнер в той же сети, подключение к `kafka:19092`; закрывайте его паролем или держите только на `127.0.0.1` — он умеет удалять темы и сдвигать смещения.

## 6. Настройки тем, которые понадобятся для обмена 1С

| Параметр (тема / брокер) | Умолчание | Что ставить для обмена 1С | Зачем |
|---|---|---|---|
| `partitions` при создании | `num.partitions=1` | 3–6 на тему | Параллельное чтение несколькими потребителями; порядок — по ключу |
| `replication.factor` | `default.replication.factor=1` | 3 в кластере, 1 на стенде | Переживает отказ брокера |
| `min.insync.replicas` | 1 | 2 при факторе 3 | С `acks=all` запись подтверждается только после копии |
| `retention.ms` (`log.retention.hours`) | 168 ч | 7–14 суток | Запас на простой получателя на праздники |
| `retention.bytes` | −1 (без предела) | предел по диску | Не забить диск |
| `cleanup.policy` | `delete` | `compact` для тем «последнее состояние объекта» (ключ = УИД) | Хранить последнюю версию каждого ключа |
| `max.message.bytes` (`message.max.bytes`) | 1 048 588 байт | оставить; крупное — по частям | Предел и у клиентов (`max.request.size`), и у потребителей |

Умолчания — [Kafka-код 4.4 `ServerLogConfigs`, `ReplicationConfigs`, `TopicConfig`]; значения для 1С — [практика].

```bash
B=kafka01.example.local:9092
bin/kafka-topics.sh --bootstrap-server $B --create --topic erp.nomenclature.v1 \
  --partitions 6 --replication-factor 3 \
  --config min.insync.replicas=2 --config retention.ms=1209600000
bin/kafka-configs.sh --bootstrap-server $B --entity-type topics --entity-name erp.nomenclature.v1 --describe
```

Имена тем удобно строить как `<система>.<сущность>.<версия формата>`; точки и подчёркивания в одном имени не смешивайте — Kafka предупреждает о конфликте имён метрик ⚠ (поведение известно по прежним выпускам; сверить вывод `--create`).

**Разделы можно только добавить, но не убавить**, и добавление меняет раздел для ключей (`hash(key) % число_разделов`) — порядок сообщений по ключу на стыке нарушится [Kafka-док 4.4 `basic-kafka-operations`]. Закладывайте число разделов сразу.

## 7. Типовые ошибки установки

| Симптом | Причина | Что сделать |
|---|---|---|
| `No meta.properties found in /var/lib/kafka/data` при запуске | Хранилище не размечено или `log.dirs` указывает не туда | `kafka-storage.sh format …` (раздел 4.4); проверить `log.dirs` |
| Клиент с другой машины подключается, но запись/чтение висят, в журнале клиента — попытки соединиться с `localhost:9092` или `kafka:19092` | `advertised.listeners` сообщает адрес, недоступный клиенту | Указать имя/адрес, по которому клиент дойдёт до брокера |
| Тема не создаётся на одном узле, в журнале — нехватка реплик для `__consumer_offsets` | Умолчание фактора репликации служебных тем — 3 | `offsets.topic.replication.factor=1` и др. (раздел 4.3) |
| После перезагрузки ОС «пропали» все темы | Данные лежали в `/tmp/kraft-combined-logs` | Перенести `log.dirs`; данные восстановить не из чего |
| Контейнер не стартует: `/opt/kafka/config/ file not writable` | Docker старше 20.10.4 | Обновить Docker |
| `UnsupportedClassVersionError` при запуске | Java старше 17 | Поставить 21 или 25 |
| `Too many open files` | Мало дескрипторов | `LimitNOFILE=100000` в юните; для Docker — `ulimits` в compose |
| Запись с клиента 1С падает с `RecordTooLargeException` / `MESSAGE_TOO_LARGE` | Сообщение больше 1 МБ | Делить сообщение; поднимать предел — согласованно на брокере, теме, производителе и потребителе |

Тексты ошибок клиентов — по опыту ⚠; точные сообщения брокера ищите в `/var/log/kafka/server.log`.

## 8. Что проверить после установки

1. `systemctl is-active kafka` — `active`; `ss -tlnp` — заняты 9092 и 9093.
2. `kafka-metadata-quorum.sh … describe --status` — есть `LeaderId`, в `CurrentVoters` — ожидаемые контроллеры.
3. `kafka-topics.sh --list` с **другой** машины — список возвращается.
4. `log.dirs` — на отдельном диске, не в `/tmp`; `df -h /var/lib/kafka`.
5. `auto.create.topics.enable=false` — запись в несуществующую тему даёт ошибку, а не создаёт тему.
6. Порт 9092 открыт только нужным адресам; на стенде без шифрования — Kafka не видна из интернета.
7. Сохранён идентификатор кластера (`/etc/kafka/cluster-id`) и копия `/etc/kafka`.

## Источники

- Документация Kafka 4.4: `raw.githubusercontent.com/apache/kafka/4.4/docs/<раздел>/<страница>.md` (опубликована на `kafka.apache.org/44/…`); список страниц — `api.github.com/repos/apache/kafka/git/trees/4.4?recursive=1`.
- Исходный код и файлы ветки `4.4`: `config/server.properties`, `bin/kafka-server-start.sh`, `bin/kafka-run-class.sh`, `bin/kafka-server-stop.sh`, `docker/jvm/Dockerfile`, `docker/resources/common-scripts/configureDefaults`, `docker/examples/README.md`, `docker/examples/docker-compose-files/single-node/plaintext/docker-compose.yml`, `server-common/…/ServerLogConfigs.java`, `server/…/ReplicationConfigs.java`, `clients/…/TopicConfig.java`.
- Страница загрузок `kafka.apache.org/community/downloads/` и каталог `downloads.apache.org/kafka/` (20.10.2026).
- Пакеты Ubuntu 24.04: `packages.ubuntu.com/noble/openjdk-25-jre-headless`, `…/kcat`, `…/librdkafka1`.
