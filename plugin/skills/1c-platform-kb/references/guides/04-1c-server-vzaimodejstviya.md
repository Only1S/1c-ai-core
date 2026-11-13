# «1С:Сервер взаимодействия»: собственный сервер системы взаимодействия на Linux

> Область: установка и подключение собственного сервера системы взаимодействия (обсуждения, сообщения, видеозвонки в приложениях 1С) | Актуальность: 2026-10-10
>
> **Источники:** официальные методические статьи ИТС — «Настройка 1С:Сервера взаимодействия с медиасервером Janus — для 8.5.1» (11.03.2026, [its.1c.ru/db/metod8dev/content/6042/hdoc](https://its.1c.ru/db/metod8dev/content/6042/hdoc)), «Настройка 1С:Сервера взаимодействия и медиасервера» (10.07.2023, `…/content/5988/hdoc`), «Настройка 1С:Сервера взаимодействия» (`…/content/5982/hdoc`). Это конспект своими словами; команды приведены как в статьях.
>
> **Статус:** на сервере не выполнялось. Примеры в статьях ИТС даны для систем с `rpm` и `yum` (CentOS 7); отличия для Ubuntu отмечены отдельно и помечены как непроверенные.

## Кратко

1. Система взаимодействия работает либо через облачный сервис «1С:Диалог», либо через собственный «1С:Сервер взаимодействия». Собственный сервер — отдельный продукт со своим дистрибутивом и своей СУБД; сервер 1С и его лицензии он не заменяет.
2. Состав: Java 11, Hazelcast, Elasticsearch, собственно сервер взаимодействия (CS, управляется утилитой `ring`), PostgreSQL, объектное хранилище S3 (MinIO) для файлов, медиасервер Janus для видеоконференций.
3. Минимум оперативной памяти — 4 ГБ (статья 2023 года). Версию сервера взаимодействия выбирают под версию платформы по таблице на странице дистрибутива.
4. Дистрибутив — на releases.1c.ru, проект `CollaborationSystem`; установка — `./1ce-installer-cli install`.
5. Клиенты подключаются к порту WebSocket (по умолчанию в примере — 8086); административный REST API — порт 8087.
6. Информационная база подключается к собственному серверу не стандартной функцией «Управление системой взаимодействия», а обработкой `CollaborationSystemRegister.epf` из дистрибутива сервера.
7. В статьях используются тестовые логины и пароли (`admin:admin`, `db_user_pwd`, `minio123`) — перед эксплуатацией их обязательно заменить.

## Компоненты и порты

| Компонент | Назначение | Порт | Комментарий |
|---|---|---|---|
| Java 11 (AxiomJDK) | среда выполнения | — | нужна Hazelcast, Elasticsearch и CS |
| Hazelcast | распределённый кэш и координация | 5701 | взаимодействие узлов кластера |
| Elasticsearch | полнотекстовый поиск | 9200, 9300 | REST API и транспорт |
| CS | сервер взаимодействия | 8086 | WebSocket, подключения клиентов |
| CS | административный API | 8087 | REST, только для администратора |
| CS | защищённое подключение | 8443, 8444 | HTTPS |
| PostgreSQL | данные системы взаимодействия | 5432 | отдельная база, не база 1С |
| MinIO | хранилище файлов (S3) | 9000 | адрес должен быть доступен клиентам |
| Janus | медиасервер | 8188, 7188 | HTTP API и внутренний API |

Требования безопасности из статьи 2026 года: заменить все тестовые учётные данные; настроить HTTPS через обратный прокси с сертификатами; вынести СУБД и объектное хранилище на отдельные серверы; закрыть служебные порты сетевым экраном.

## Установка по шагам

Все команды выполняются от `root`.

### 1. Java 11

В статье ставится пакет AxiomJDK (`rpm -i axiomjdk-jre-pro11.0.28+12-linux-amd64.rpm`), затем задаётся `JAVA_HOME` для всех сессий:

```bash
readlink $(readlink $(which java))          # путь к установленной Java

tee /etc/profile.d/java.sh << 'EOF'
export JAVA_HOME=/usr/lib/jvm/axiomjdk-java11-pro-runtime.x86_64
export PATH=$JAVA_HOME/bin:$PATH
EOF
chmod +x /etc/profile.d/java.sh
source /etc/profile.d/java.sh
```

⚠ Для Ubuntu (не проверено): пакет ставится через `apt`/`dpkg`, путь к Java будет другим — подставьте в `JAVA_HOME` результат `readlink -f $(which java)` без хвоста `/bin/java`.

### 2. Компоненты системы взаимодействия

```bash
tar -xzf 1c-cs-30.0.32-linux-x86_64.tar.gz      # имя архива — по скачанной версии
./1ce-installer-cli install --ignore-signature-warnings
```

Ожидается сообщение об успешной установке. Утилита `ring` ставится в каталог вида `/opt/1C/1CE/components/1c-enterprise-ring-<версия>-x86_64/ring` (путь из статьи 2023 года); если `ring` не находится по имени — вызывайте по полному пути.

Установщик не поддерживает SELinux в режиме `enforcing` (в статье его переводят в `permissive`). На Ubuntu SELinux по умолчанию не используется.

### 3. PostgreSQL

В статье ставится PostgreSQL 15 в сборке от фирмы «1С» и создаётся кластер. На Ubuntu используйте установку из `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`; если PostgreSQL уже стоит — сразу переходите к шагу 4.4. Статья 2023 года допускает версии от 9.5.

### 4. Экземпляры и их настройка

**4.1. Hazelcast**

```bash
useradd hc_user
mkdir -p /var/cs/hc_instance
chown hc_user:hc_user /var/cs/hc_instance

ring hazelcast instance create --dir /var/cs/hc_instance --owner hc_user
ring hazelcast --instance hc_instance service create \
  --username hc_user --java-home $JAVA_HOME --stopped
```

В статье 2026 года на шаге создания экземпляра Hazelcast дважды приведена команда `service create`. Команда `instance create` здесь взята из статьи 2023 года и по аналогии с шагами для Elasticsearch и CS.

**4.2. Elasticsearch**

```bash
useradd es_user
mkdir -p /var/cs/es_instance
chown es_user:es_user /var/cs/es_instance

ring elasticsearch instance create --dir /var/cs/es_instance --owner es_user
ring elasticsearch --instance es_instance service create \
  --username es_user --java-home $JAVA_HOME --stopped
```

**4.3. Сервер взаимодействия (CS)**

```bash
useradd cs_user
mkdir -p /var/cs/cs_instance
chown cs_user:cs_user /var/cs/cs_instance

ring cs instance create --dir /var/cs/cs_instance --owner cs_user
ring cs --instance cs_instance service create \
  --username cs_user --java-home $JAVA_HOME --stopped
```

**4.4. База данных**

```bash
su - postgres -c psql <<'SQL'
CREATE USER db_user WITH PASSWORD 'db_user_pwd' CREATEDB;
CREATE DATABASE cs_db OWNER db_user;
\c cs_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SQL
```

Замените `db_user_pwd` своим паролем — он используется в следующих шагах. Расширение `uuid-ossp` входит в пакет `contrib`.

**4.5. Подключение CS к PostgreSQL** — два пула соединений, `common` и `privileged`, с одинаковыми параметрами:

```bash
for POOL in common privileged; do
  ring cs --instance cs_instance jdbc pools --name $POOL set-params \
    --url "jdbc:postgresql://localhost:5432/cs_db?currentSchema=public"
  ring cs --instance cs_instance jdbc pools --name $POOL set-params --username db_user
  ring cs --instance cs_instance jdbc pools --name $POOL set-params --password db_user_pwd
done
```

**4.6. Адрес и порт для клиентов**

```bash
ring cs --instance cs_instance websocket set-params --hostname 0.0.0.0
ring cs --instance cs_instance websocket set-params --port 8086
```

### 5. Запуск и проверка

```bash
ring hazelcast     --instance hc_instance service start
ring elasticsearch --instance es_instance service start
ring cs            --instance cs_instance service start

lsof -iTCP -sTCP:LISTEN -P | grep -E 'hc_user|es_user|cs_user'   # в Ubuntu то же покажет: ss -tlnp
```

Ожидаются порты 5701 (Hazelcast), 9200 и 9300 (Elasticsearch), 8086, 8443 и 8444 (CS).

### 6. Регистрация базы данных в сервере

```bash
curl -Sf -X POST -H "Content-Type: application/json" \
  -d '{"url": "jdbc:postgresql://localhost:5432/cs_db", "username": "db_user", "password": "db_user_pwd", "enabled": true}' \
  -u admin:admin http://localhost:8087/admin/bucket_server
```

В ответ приходит JSON с идентификатором зарегистрированной базы. Учётная запись `admin:admin` — тестовая из статьи.

### 7. Сервер TURN/STUN

Нужен, чтобы медиасоединения проходили через NAT и сетевые экраны. Для эксплуатации статья рекомендует собственный `coturn`; для отладки — тестовый сервер 1С, который регистрируется так же через административный API (`url` вида `turn:<хост>:3478`, имя, пароль).

### 8. Общая проверка

```bash
curl http://localhost:8087/rs/health
```

| Поле ответа | Должно быть | Что означает |
|---|---|---|
| `status` | `UP` | общий статус |
| `mainDbOk` | `true` | основная база доступна |
| `allShardsOk` | `true` | все сегменты базы доступны |
| `hazelcast.available` | `true` | кластер Hazelcast активен |
| `elasticsearchOk` | `true` | Elasticsearch доступен |
| `mediaClusterOk` | `false`, после шага 10 — `true` | медиасервер |

### 9. Хранилище файлов (MinIO)

MinIO ставится отдельным пользователем (`minio_user`), бинарный файл — в `/opt/minio`, данные — в `/var/minio`, параметры — в `/etc/default/minio` (`MINIO_VOLUMES`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`), служба — собственный юнит systemd. Статья подчёркивает строку `LimitNOFILE=65536` в юните: без неё звонки с большим числом участников завершаются аварийно.

Дальше: в веб-интерфейсе MinIO создаётся корзина `cs-bucket`, и хранилище регистрируется в сервере:

```bash
curl -Sf -X POST -H 'Content-Type: application/json' \
  -d '{
   "apiType": "AMAZON", "storageType": "DEFAULT",
   "baseUrl": "http://<внешний адрес MinIO>:9000",
   "containerUrl": "http://<внешний адрес MinIO>:9000/cs-bucket",
   "containerName": "cs-bucket",
   "region": "eu-west-1", "accessKeyId": "<ключ>", "secretKey": "<секрет>", "signatureVersion": "V2",
   "uploadLimit": 1073741824, "downloadLimit": 1073741824, "fileSizeLimit": 1073741824,
   "bytesToKeep": 0, "daysToKeep": 31, "pathStyleAccessEnabled": true
  }' \
  -u admin:admin http://localhost:8087/admin/storage_server
```

В `baseUrl` и `containerUrl` нельзя указывать `localhost`, если клиенты подключаются извне: адрес хранилища получают сами клиенты.

### 10. Подключение информационной базы

1. В составе дистрибутива сервера взаимодействия найти обработку `CollaborationSystemRegister.epf`.
2. Открыть её в клиенте 1С («Файл → Открыть»).
3. Заполнить: адрес сервера взаимодействия — `ws://<внешний адрес>:8086` (или `wss://…` при защищённом подключении), адрес электронной почты абонента, имя информационной базы.
4. Нажать «Зарегистрировать».

При ошибке проверить регистрацию хранилища (шаг 9) и доступность порта 8086 с клиентского компьютера.

Параметры подключения экземпляра показывает `ring cs --instance <экземпляр> websocket list-params`; они же лежат в `websocket.yml` (параметры `wss`, `hostname`, `port`) в каталоге `/var/cs/<экземпляр>/config/`. Если настройки не менялись, файла может не быть.

### 11. Медиасервер Janus (видеоконференции)

1. Распаковать дистрибутив `janus-amd64-<версия>`, прочитать `README.md`, запустить `./install.sh`. Janus и вспомогательные службы работают от пользователя `1c_media`, общий каталог записей — `/var/records`.
2. Проверить порты 8188 и 7188.
3. Зарегистрировать медиасервер:

```bash
curl -Sf -X POST -H 'Content-Type: application/json' \
  -d '{"url": "http://<адрес Janus>:8188/janus/", "name": "Janus 1", "confereeLimit": 1000, "enabled": true}' \
  -u admin:admin http://localhost:8087/admin/media_server
```

4. Параметры видеоконференций — файл `/var/cs/cs_instance/config/video.yml`:

| Параметр | Значение в статье | Смысл |
|---|---|---|
| `enabled` | `true` | включить видеоконференции |
| `conference-server-based-threshold` | 3 | с какого числа участников звонок идёт через медиасервер, а не напрямую |
| `conference-server-based-member-limit` | 34 | предел участников через медиасервер |
| `max-bandwidth` | 2000 | предельный битрейт, кбит/с |
| `max-reference-width` / `max-reference-height` | 1280 / 720 | предельное разрешение |
| `max-reference-fps` | 30 | предельная частота кадров |

5. Перезапустить CS (`service stop`, затем `service start`) и убедиться, что `/rs/health` показывает `"mediaClusterOk": true`.

### 12. Внешние пользователи

Чтобы приглашать в обсуждения внешних участников, ставится отдельный сайт (тем же установщиком сервера взаимодействия). В его `config.json` указывается адрес сервера (`"serverURL": "wss://<адрес>"`), сайт публикуется на веб-сервере, после чего подключается командой `ring cs --instance <экземпляр> site set-params --public-url https://<адрес сайта>`. В клиенте после перезапуска появляется команда приглашения внешнего участника.

## Типичные ошибки и подводные камни

| Симптом | Причина | Решение |
|---|---|---|
| Клиенты не подключаются, сервер «здоров» | закрыт порт 8086 или в настройках остался `localhost` | проверить порт с клиента; `websocket list-params` |
| Файлы в обсуждениях не отправляются | в `baseUrl`/`containerUrl` указан адрес, недоступный клиентам | перерегистрировать хранилище с внешним адресом |
| Звонки с большим числом участников обрываются | у службы MinIO нет `LimitNOFILE=65536` | добавить в юнит, `systemctl daemon-reload`, перезапустить |
| `mediaClusterOk: false` | Janus не зарегистрирован или недоступен по адресу из регистрации | проверить порт 8188 и адрес в `media_server` |
| Административный API доступен из сети | порт 8087 не закрыт, пароль `admin:admin` | закрыть порт сетевым экраном, сменить пароль |
| Версия сервера взаимодействия не подходит платформе | версии подбираются парами | сверить с таблицей соответствия на странице дистрибутива |

## Что не подтверждено

- ⚠ Команды установки Java, PostgreSQL и MinIO на Ubuntu: в статьях ИТС они даны для систем с `rpm`/`yum`.
- ⚠ Актуальная таблица соответствия версий сервера взаимодействия и платформы: в статье 2023 года приведены пары 10.0.47 — 8.3.19 и 9.0.34 — 8.3.18, в статье 2026 года используется дистрибутив 30.0.32 для платформы 8.5.1; для 8.3.27 пару нужно смотреть на странице дистрибутива.
- ⚠ Лицензирование сервера взаимодействия в статьях не описано.
