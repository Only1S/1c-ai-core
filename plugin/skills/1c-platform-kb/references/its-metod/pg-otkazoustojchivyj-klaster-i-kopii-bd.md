# ИТС-конспект (методические материалы): Отказоустойчивый кластер PostgreSQL и внешняя синхронизация для механизма копий баз данных
> Источник: статьи раздела «Методическая поддержка» портала 1С:ИТС (ссылки — в разделах). Это конспект своими словами, не дословный текст. Составлен 2026-10-10.

## Кратко: главные официальные рекомендации

1. В самом PostgreSQL нет механизма автоматического переключения на резервный сервер. Аналог «MS SQL Server Always On Availability Groups» для систем на 1С:Предприятии собирается из связки **Patroni + etcd + HAProxy**.
2. Распределение ролей: Patroni управляет экземпляром PostgreSQL и автоматически переводит роль ведущего на резервный узел при сбое; etcd (альтернативы — ZooKeeper, Consul, Kubernetes) хранит общую для узлов информацию (список узлов, кто сейчас ведущий); HAProxy даёт единую точку подключения, не зависящую от текущего распределения ролей.
3. На узлы СУБД ставится PostgreSQL с модификациями фирмы «1С». Кластер PostgreSQL вручную **не инициализируется** — это сделает Patroni при первом запуске.
4. Автозапуск службы PostgreSQL на узлах СУБД **отключается** (`systemctl disable postgresql-11`): запуском и остановкой PostgreSQL управляет Patroni, и автозапуск ему только мешает.
5. etcd: первый узел запускается с `ETCD_INITIAL_CLUSTER_STATE="new"`; каждый следующий узел добавляется в два этапа — сначала кластер оповещается (`etcdctl member add`), потом запускается сам узел с `"existing"`. После сборки на всех узлах выставляется одинаковый `ETCD_INITIAL_CLUSTER` и `ETCD_INITIAL_CLUSTER_STATE="existing"`.
6. `ETCD_HEARTBEAT_INTERVAL` подбирается с учётом сетевой задержки между узлами, `ETCD_ELECTION_TIMEOUT` — в несколько раз больше него (в примере 1000 мс и 5000 мс).
7. Ошибки в `ETCD_INITIAL_CLUSTER` (несуществующие серверы, опечатки) приводят к сбою запуска etcd; если первый запуск не удался — очистить содержимое каталога из `ETCD_DATA_DIR` и повторить.
8. На клиентском интерфейсе etcd включается проверка логина и пароля (`etcdctl user add root`, `etcdctl auth enable`).
9. На скорость и безопасность переключения в Patroni влияют `maximum_lag_on_failover` и `master_start_timeout`. Максимальное время переключения = `loop_wait + master_start_timeout + loop_wait`; при `master_start_timeout: 0` оно равно `loop_wait`, но при асинхронной репликации это **может привести к потере последних транзакций**.
10. В unit-файле службы Patroni особенно важны `TimeoutSec` (сколько systemd ждёт при запуске/остановке до принудительного завершения) и `Restart` (политика перезапуска); в примере — `30` и `no`.
11. Любую службу (etcd, patroni, haproxy, дополнительный PostgreSQL) добавлять в автозапуск (`systemctl enable`) только после проверки, что она успешно стартовала.
12. В параметрах информационной базы 1С в качестве сервера СУБД указывается адрес HAProxy, а не конкретный узел PostgreSQL: HAProxy опрашивает REST API Patroni (порт 8008) и направляет подключения только на текущий ведущий сервер (в его статистике ведущий — «UP», резервные — «DOWN»).
13. Если SELinux не отключён, перед запуском HAProxy нужно разрешить ему обращения на внешние адреса: `setsebool -P haproxy_connect_any=1`.
14. Настройки PostgreSQL в таком кластере задаются **через конфигурационный файл Patroni** (секция `postgresql` → `parameters`), их рекомендуется держать одинаковыми на всех узлах; применяются командами `patronictl reload` и `patronictl restart` по каждому узлу.
15. Значения параметров PostgreSQL в статье — только пример синтаксиса; сами значения подбираются по статьям ИТС «Настройки PostgreSQL для работы с 1С:Предприятием» (части 1 и 2).
16. Проверка отказоустойчивости: `patronictl list` (колонка «Lag in MB» у резервных должна быть 0.0), плановое переключение (`patronictl failover`), имитация сбоя перезагрузкой ведущего. Работающий сеанс 1С:Предприятия не должен заметить изменений в инфраструктуре.
17. Резервную копию штатными средствами (`pg_basebackup`) можно снимать не только с ведущего, но и с резервного сервера.
18. Описанная процедура восстановления — проверка на демонстрационном стенде. В реальной аварии этап «Удаление данных» нужно пересматривать по обстоятельствам сбоя; этап «Восстановление» предполагает, что кластер Patroni уже полностью развёрнут и его нужно только наполнить данными.
19. Резервный сервер PostgreSQL доступен только на чтение, **включая временные таблицы**, поэтому запросы 1С:Предприятия, создающие временные таблицы, на нём завершаются ошибкой. Для механизма копий баз данных (внешний тип репликации) нужен **дополнительный кластер PostgreSQL, доступный на запись**, — отдельный сервер либо второй экземпляр на одном из существующих узлов.
20. Промежуточная база в дополнительном кластере создаётся **созданием информационной базы средствами 1С** (платформа выполняет тонкие настройки базы, зависящие от версии платформы); затем таблицы удаляются, подключается расширение `postgres_fdw` и импортируется схема `public` с резервного сервера.
21. В настройках подключения к копии базы данных указывается промежуточная база (дополнительный кластер), а не сам резервный сервер.
22. Узлу, который используется как источник для копии базы данных, имеет смысл запретить становиться ведущим — тег Patroni `nofailover: true`.
23. После каждой реструктуризации информационной базы (изменения структуры метаданных) импортированные внешние таблицы в промежуточной базе нужно удалить и импортировать схему заново.

---

## Статья: Построение отказоустойчивого кластера PostgreSQL. Настройка внешней синхронизации на PostgreSQL для механизма копий баз данных

- **Дата публикации:** 06.04.2020 (рубрика «PostgreSQL»)
- **Ссылка:** https://its.1c.ru/db/metod8dev/content/5971/hdoc
- **Прямая ссылка:** https://its.1c.ru/db/content/metod8dev/src/developers/scalability/administration/postgresql/i8105971.htm

### Оценка применимости на октябрь 2026: частично устарело

Это оценка составителя конспекта, в самой статье её нет.

- **Что остаётся верным:** архитектура (Patroni + хранилище состояния + HAProxy как единая точка входа), принцип «PostgreSQL управляется только Patroni», порядок сборки кластера etcd, логика проверки состояния через REST API Patroni, принцип задания настроек PostgreSQL через Patroni, идея промежуточной базы с `postgres_fdw` для механизма копий баз данных и необходимость переимпорта схемы после реструктуризации.
- **Что устарело:**
  - Статье больше шести лет (апрель 2020). Стенд — CentOS 7 (снята с поддержки), установка через `yum`, пути и имена служб RPM-сборки (`/usr/pgsql-11/bin`, `/var/lib/pgsql/11/data`, `postgresql-11.service`). На Ubuntu пакеты, пути и имена служб другие; в статье они не описаны.
  - PostgreSQL 11.5_12.1C (ветка 11 снята с поддержки), платформа 8.3.16.1224, Patroni 1.6.4, Python 3.6.8 — старые версии.
  - Привязанные к PostgreSQL 11 детали: параметр `wal_keep_segments` и файлы `recovery.conf` / `recovery.done` в новых версиях PostgreSQL отсутствуют, поэтому блок `parameters` и шаги восстановления нельзя переносить на современную версию без сверки с документацией.
  - Команды `etcdctl cluster-health`, `etcdctl member add <имя> <url>`, `etcdctl user add`, `etcdctl --username` — синтаксис старого API etcd (v2); в актуальных версиях etcd и Patroni синтаксис команд и секция подключения к etcd в `patroni.yml` иные — сверять с их документацией.
  - Имена параметров Patroni (`master_start_timeout`, секция `bootstrap.users`) относятся к версии 1.6.4; для актуальной версии Patroni проверять по её документации.
- **Чего в статье нет (и нельзя из неё вывести):** TLS для etcd и REST API Patroni (в примере всё по http, а сам etcd в приведённом выводе статуса предупреждает, что незащищённые клиентские подключения крайне не рекомендуются), резервирование самого HAProxy, синхронная репликация (только ссылка на документацию), вариант для Ubuntu.
- В тексте источника есть опечатки и потери вёрстки — они собраны в разделе «Замеченные неточности источника» в конце конспекта.

### 1. Введение и состав решения

Цель статьи — показать, как для систем на 1С:Предприятии построить отказоустойчивый кластер PostgreSQL, сходный по назначению с «MS SQL Server Always On Availability Groups». Сложность в том, что сам PostgreSQL не умеет автоматически переключаться на резервный сервер; статья показывает, как добиться автоматического переключения при сбое ведущего.

| Компонент | Назначение |
|---|---|
| **Patroni** | Шаблон для построения отказоустойчивых кластеров на PostgreSQL. Управляет экземпляром PostgreSQL, автоматически переключает роль ведущего на резервный сервер при сбое. Общую информацию кластера (список узлов, положение ведущего) хранит во внешней системе: ZooKeeper, etcd, Consul или Kubernetes |
| **etcd** | Согласованное распределённое хранилище «ключ — значение», надёжное место для данных, к которым обращается распределённая система или кластер машин |
| **HAProxy** | Прокси-сервер TCP- и HTTP-трафика. Создаёт единую точку подключения к PostgreSQL, не зависящую от распределения ролей между серверами |

### 2. Стенд

Четыре машины под управлением CentOS 7:

| Имя | IP-адрес | Описание |
|---|---|---|
| Core.example | 10.0.0.11 | симуляция инфраструктуры (сервер 1С:Предприятия, HAProxy, узел etcd) |
| DBOne.example | 10.0.0.21 | первый сервер PostgreSQL |
| DBTwo.example | 10.0.0.22 | второй сервер PostgreSQL |
| DBThree.example | 10.0.0.23 | третий сервер PostgreSQL |

Исходные предположения:

- машины созданы, ОС установлена и обновлена;
- все машины в одной сети;
- машины находят друг друга по DNS-именам `core.example`, `dbone.example`, `dbtwo.example`, `dbthree.example`.

#### 2.1. Имя машины = имя в DNS

На каждой машине имя хоста приводится к DNS-имени и проверяется (вторая команда должна вывести заданное имя):

```bash
# на core.example
sudo hostnamectl set-hostname core.example --static
hostname

# на dbone.example
sudo hostnamectl set-hostname dbone.example --static
hostname

# на dbtwo.example
sudo hostnamectl set-hostname dbtwo.example --static
hostname

# на dbthree.example
sudo hostnamectl set-hostname dbthree.example --static
hostname
```

#### 2.2. Дистрибутивы

- Сервер 1С:Предприятия для RPM-based Linux-систем — https://releases.1c.ru/project/Platform83, использована версия 8.3.16.1224.
- СУБД PostgreSQL для Linux x86 (64-bit) одним архивом (RPM) — https://releases.1c.ru/project/AddCompPostgre, использована версия 11.5_12.1C.

#### 2.3. Установка

**Core.example** — установить и запустить сервер 1С:Предприятия. Подробная инструкция по установке: https://its.1c.ru/db/metod8dev#content:5953:hdoc

**DBOne.example, DBTwo.example, DBThree.example** — на этом этапе настройка одинакова: ставится PostgreSQL с модификациями фирмы «1С».

1. В каталоге с распакованным дистрибутивом PostgreSQL 11.5_12.1C:

   ```bash
   sudo yum install -y postgresql11-1c-*.rpm
   ```

   Кластер **не инициализировать** — это будет сделано при установке Patroni.

2. Запретить автозапуск PostgreSQL при старте ОС:

   ```bash
   sudo systemctl disable postgresql-11
   ```

   Причина: остановкой и запуском PostgreSQL будет управлять Patroni, автозапуск ему только помешает.

### 3. etcd

Общий план раздела развёртывания: сначала создаётся кластер etcd и в него добавляются узлы; затем строится кластер Patroni, хранящий свою конфигурацию в etcd; затем настраивается HAProxy, который отслеживает смену ведущего сервера и скрывает её от 1С:Предприятия.

Кластер etcd разворачивается **на всех машинах стенда** (core и три сервера СУБД).

#### 3.1. Первый узел кластера etcd (на core.example)

1. Установка из пакета:

   ```bash
   sudo yum install -y etcd
   ```

2. Отложить настройки по умолчанию:

   ```bash
   sudo mv /etc/etcd/etcd.conf /etc/etcd/etcd.conf.def
   ```

3. Создать новый `/etc/etcd/etcd.conf`:

   ```ini
   #[Member]
   ETCD_DATA_DIR="/var/lib/etcd"
   ETCD_LISTEN_PEER_URLS="http://0.0.0.0:2380"
   ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"
   ETCD_NAME="core"
   ETCD_HEARTBEAT_INTERVAL="1000"
   ETCD_ELECTION_TIMEOUT="5000"
   #[Clustering]
   ETCD_INITIAL_ADVERTISE_PEER_URLS="http://core.example:2380"
   ETCD_ADVERTISE_CLIENT_URLS="http://core.example:2379"
   ETCD_INITIAL_CLUSTER="core=http://core.example:2380"
   ETCD_INITIAL_CLUSTER_TOKEN="etcd-example"
   ETCD_INITIAL_CLUSTER_STATE="new"
   ```

   (исправлено по смыслу: в источнике параметры `ETCD_INITIAL_ADVERTISE_PEER_URLS` и `ETCD_ADVERTISE_CLIENT_URLS` слиплись в одну строку.)

   Смысл параметров:

   | Параметр | Что задаёт |
   |---|---|
   | `ETCD_DATA_DIR` | Каталог данных кластера etcd |
   | `ETCD_LISTEN_PEER_URLS` | Схема и точка подключения для остальных узлов кластера в виде `scheme://IP:port`. Схема — `http` или `https`; для unix-сокетов — `unix://` или `unixs://`. Адрес `0.0.0.0` означает, что порт слушается на всех интерфейсах |
   | `ETCD_LISTEN_CLIENT_URLS` | То же, но для клиентов кластера |
   | `ETCD_NAME` | Человекочитаемое имя узла, уникальное в кластере. Для первого узла — любое; для последующих должно совпадать с именем, указанным при добавлении узла |
   | `ETCD_HEARTBEAT_INTERVAL` | Интервал в миллисекундах между рассылками лидером оповещений «я всё ещё лидер». Задавать с учётом сетевой задержки между узлами |
   | `ETCD_ELECTION_TIMEOUT` | Время в миллисекундах от последнего полученного оповещения лидера до попытки ведомого узла захватить роль лидера. Рекомендуется в несколько раз больше `ETCD_HEARTBEAT_INTERVAL` (подробности — в документации etcd) |
   | `ETCD_INITIAL_ADVERTISE_PEER_URLS` | Список URL, по которым узел доступен остальным узлам кластера; по ним идёт обмен данными внутри кластера. Хотя бы один адрес должен быть маршрутизируемым для всех членов кластера. Допустимы доменные имена. Используется только при первом запуске нового узла |
   | `ETCD_ADVERTISE_CLIENT_URLS` | ⚠ в источнике неясно: описание дословно повторяет описание предыдущего параметра (адреса, по которым узел находят остальные узлы), без оговорки про первый запуск; по названию и по значению в примере (порт 2379) это адреса клиентского интерфейса узла |
   | `ETCD_INITIAL_CLUSTER` | Список узлов кластера на момент запуска. Используется только при первом запуске нового узла |
   | `ETCD_INITIAL_CLUSTER_TOKEN` | Токен кластера, одинаковый на всех узлах. Используется только при первом запуске нового узла |
   | `ETCD_INITIAL_CLUSTER_STATE` | `"new"` — первый запуск первого узла кластера; `"existing"` — узел при старте пытается связаться с остальными узлами кластера |

4. Запуск демона:

   ```bash
   sudo systemctl start etcd.service
   ```

5. Проверки:

   - служба запущена и в состоянии `active`:

     ```bash
     sudo systemctl status etcd.service
     ```

     (в примере вывода: `Active: active (running)`, в журнале — выбор лидера и строка о готовности обслуживать клиентские запросы; там же предупреждение etcd о том, что незащищённые клиентские подключения по 2379 крайне не рекомендуются);

   - при ошибке запуска смотреть системный журнал:

     ```bash
     journalctl -xel
     ```

   - кластер должен состоять из одного узла и быть здоровым:

     ```bash
     etcdctl cluster-health
     ```

     Ожидаемый вывод: один `member ... is healthy` и строка `cluster is healthy`.

6. Если всё в порядке — добавить в автозапуск:

   ```bash
   sudo systemctl enable etcd.service
   ```

Предупреждение авторов: при запуске etcd пытается найти все узлы из `ETCD_INITIAL_CLUSTER`; если хотя бы один не найден — запуск завершается сбоем. Если что-то пошло не так — удалить содержимое каталога, заданного в `ETCD_DATA_DIR`.

#### 3.2. Добавление нового узла etcd

Добавление идёт в два этапа: (1) кластер предупреждается о новом узле; (2) запускается сам новый узел. Действия выполняются **последовательно** для каждого из оставшихся серверов стенда; пример — `dbtwo.example`.

1. На `core.example` — оповестить кластер:

   ```bash
   etcdctl member add dbtwo http://dbtwo.example:2380
   ```

   Команда сообщает ID нового участника и выводит значения, которые нужно задать на новом узле:

   ```text
   ETCD_NAME="dbtwo"
   ETCD_INITIAL_CLUSTER="dbtwo=http://dbtwo.example:2380,core=http://core.example:2380"
   ETCD_INITIAL_CLUSTER_STATE="existing"
   ```

2. На новом узле — установить etcd и отложить настройки по умолчанию:

   ```bash
   sudo yum install -y etcd
   sudo mv /etc/etcd/etcd.conf /etc/etcd/etcd.conf.def
   ```

3. Создать `/etc/etcd/etcd.conf`:

   ```ini
   #[Member]
   ETCD_DATA_DIR="/var/lib/etcd"
   ETCD_LISTEN_PEER_URLS="http://0.0.0.0:2380"
   ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"
   ETCD_NAME="dbtwo"
   ETCD_HEARTBEAT_INTERVAL="1000"
   ETCD_ELECTION_TIMEOUT="5000"
   #[Clustering]
   ETCD_INITIAL_ADVERTISE_PEER_URLS="http://dbtwo.example:2380"
   ETCD_ADVERTISE_CLIENT_URLS="http://dbtwo.example:2379"
   ETCD_INITIAL_CLUSTER="core=http://core.example:2380,dbtwo=http://dbtwo.example:2380"
   ETCD_INITIAL_CLUSTER_TOKEN="etcd-example"
   ETCD_INITIAL_CLUSTER_STATE="existing"
   ```

   Предупреждения авторов: не забывать менять `ETCD_NAME` на каждом узле; `ETCD_INITIAL_CLUSTER` критичен для первого запуска — несуществующие серверы или иные ошибки в нём приводят к сбою запуска.

4. Запустить демон на новом узле:

   ```bash
   sudo systemctl start etcd.service
   ```

5. Проверки:

   ```bash
   sudo systemctl status etcd.service   # служба должна быть active
   etcdctl cluster-health               # новый узел должен быть healthy, итог - cluster is healthy
   etcdctl member list                  # список узлов: name, peerURLs, clientURLs, isLeader
   ```

6. Если всё в порядке — автозапуск:

   ```bash
   sudo systemctl enable etcd.service
   ```

#### 3.3. Завершение установки etcd

Когда etcd установлен и успешно запущен на всех серверах, файл `/etc/etcd/etcd.conf` на **каждом** сервере приводится к окончательному виду:

- `ETCD_INITIAL_CLUSTER` — одинаковый на всех узлах:

  ```ini
  ETCD_INITIAL_CLUSTER="core=http://core.example:2380,dbone=http://dbone.example:2380,dbtwo=http://dbtwo.example:2380,dbthree=http://dbthree.example:2380"
  ```

  (исправлено по смыслу: в источнике опечатка `dbonew.example`.)

- состояние кластера — `existing`:

  ```ini
  ETCD_INITIAL_CLUSTER_STATE="existing"
  ```

#### 3.4. Пользователь и авторизация в etcd

Для обращений на клиентский интерфейс etcd включается авторизация по логину и паролю.

1. Создать пользователя `root` (команда запросит пароль):

   ```bash
   etcdctl user add root
   ```

   Это первый пользователь, поэтому роль `root` назначается ему автоматически; проверка:

   ```bash
   etcdctl user get root
   ```

   Ожидаемый вывод: `User: root`, `Roles: root`.

2. Включить проверку логина и пароля:

   ```bash
   etcdctl auth enable
   ```

   Ожидаемый вывод: `Authentication Enabled`.

3. Убедиться, что изменения вступили в силу:

   ```bash
   etcdctl user get root                    # теперь должно вернуть: Insufficient credentials
   etcdctl --username root user get root    # после ввода пароля: User: root / Roles: root
   ```

### 4. Patroni

#### 4.1. Установка Patroni

Выполняется на всех серверах PostgreSQL (`dbone.example`, `dbtwo.example`, `dbthree.example`).

1. Python:

   ```bash
   sudo yum install -y python3
   sudo python3 -m pip install --upgrade pip
   python3 --version
   ```

   В статье получена версия Python 3.6.8.

2. Зависимости:

   ```bash
   sudo yum install -y gcc python3-devel
   sudo python3 -m pip install psycopg2-binary
   ```

3. Сам Patroni (с поддержкой etcd):

   ```bash
   sudo python3 -m pip install patroni[etcd]
   ```

4. Проверка установки:

   ```bash
   patroni --version
   ```

   В статье получена версия patroni 1.6.4.

#### 4.2. Первый узел Patroni (на dbone.example)

1. Каталог настроек Patroni:

   ```bash
   sudo mkdir /etc/patroni
   sudo chown postgres:postgres /etc/patroni
   sudo chmod 700 /etc/patroni
   ```

2. Файл настроек `/etc/patroni/patroni.yml`.

   В текстовой копии источника вложенность YAML потеряна (все строки с отступом в один пробел); ниже отступы восстановлены по смыслу, состав и значения параметров — как в источнике. Пароли — значения из примера статьи.

   ```yaml
   name: dbone
   namespace: /db/
   scope: postgres
   restapi:
     listen: 0.0.0.0:8008
     connect_address: dbone.example:8008
     authentication:
       username: patroni
       password: patroni
   etcd:
     hosts:
       localhost:2379
     username: root
     password: rootpassword
   bootstrap:
     dcs:
       ttl: 30
       loop_wait: 10
       retry_timeout: 10
       maximum_lag_on_failover: 1048576
       master_start_timeout: 300
       postgresql:
         use_pg_rewind: true
         use_slots: true
         parameters:
           wal_level: replica
           hot_standby: "on"
           wal_keep_segments: 8
           max_wal_senders: 5
           max_replication_slots: 5
           checkpoint_timeout: 30
     initdb:
       - auth-host: md5
       - auth-local: peer
       - encoding: UTF8
       - data-checksums
       - locale: ru_RU.UTF-8
     pg_hba:
       - host replication replicator samenet md5
       - host replication all 127.0.0.1/32 md5
       - host replication all ::1/128 md5
     users:
       usr1cv8:
         password: usr1cv8
         options:
           - superuser
   postgresql:
     listen: 0.0.0.0:5432
     connect_address: dbone.example:5432
     config_dir: /var/lib/pgsql/11/data
     bin_dir: /usr/pgsql-11/bin/
     data_dir: /var/lib/pgsql/11/data
     pgpass: /tmp/pgpass
     authentication:
       superuser:
         username: postgres
         password: V6OxPStvMPh0V7Q982DG
       replication:
         username: replicator
         password: PdR2lIAdwNdcSP4erAXc
       rewind:
         username: rewind_user
         password: WfcuDtEzEbLCHBaYQXX3
     parameters:
       unix_socket_directories: '/var/run/postgresql/'
   tags:
     nofailover: false
     noloadbalance: false
     clonefrom: false
     nosync: false
   ```

   Что видно из примера (чтение самого файла составителем конспекта; в статье эти пункты отдельно не разбираются):

   - Patroni подключается к локальному узлу etcd (`localhost:2379`) под пользователем `root`; ⚠ в источнике неясно: прямо не сказано, что `rootpassword` — это пароль, введённый на шаге `etcdctl user add root`;
   - REST API Patroni слушает порт 8008 (его потом опрашивает HAProxy);
   - при инициализации создаётся кластер с контрольными суммами страниц (`data-checksums`), кодировкой UTF8, локалью `ru_RU.UTF-8`, аутентификацией `peer` для локальных и `md5` для сетевых подключений;
   - создаётся пользователь `usr1cv8` с правами суперпользователя — под ним подключается 1С:Предприятие;
   - отдельные учётные записи для суперпользователя (`postgres`), репликации (`replicator`) и `pg_rewind` (`rewind_user`);
   - включены `use_pg_rewind` и слоты репликации (`use_slots`).

   Параметры, влияющие на переключение на резервный сервер (пояснения авторов):

   | Параметр | Смысл |
   |---|---|
   | `maximum_lag_on_failover` | Максимальное отставание (в байтах) резервного сервера от ведущего, при котором он ещё может участвовать в выборах нового лидера. В примере 1048576 |
   | `master_start_timeout` | Задержка в секундах между обнаружением аварии и началом переключения на резервный сервер. По умолчанию 300. При значении 0 переключение начинается немедленно |

   - **Риск потери данных:** при асинхронной репликации (а в примере она именно асинхронная) `master_start_timeout: 0` может привести к потере последних транзакций.
   - **Формула:** максимальное время переключения на реплику = `loop_wait + master_start_timeout + loop_wait`. Если `master_start_timeout` = 0, это время равно значению `loop_wait`.
   - О возможных вариантах репликации авторы отсылают к документации (ссылка в текстовой копии не сохранилась).

3. Служба для запуска демона Patroni — unit-файл `/etc/systemd/system/patroni.service`:

   ```ini
   [Unit]
   Description=Runners to orchestrate a high-availability PostgreSQL
   After=syslog.target network.target

   [Service]
   Type=simple
   User=postgres
   Group=postgres
   ExecStart=/usr/local/bin/patroni /etc/patroni/patroni.yml
   ExecReload=/bin/kill -s HUP $MAINPID
   KillMode=process
   TimeoutSec=30
   Restart=no

   [Install]
   WantedBy=multi-user.target
   ```

   Два особенно важных параметра:

   - `TimeoutSec` — сколько секунд systemd ждёт при запуске и остановке службы, прежде чем попытаться завершить её нештатно;
   - `Restart` — политика перезапуска службы, если она завершилась не по команде systemd. Допустимые значения: `no`, `on-success`, `on-failure`, `on-abnormal`, `on-watchdog`, `on-abort`, `always`.

   Затем перечитать настройки systemd:

   ```bash
   sudo systemctl daemon-reload
   ```

4. Запуск:

   ```bash
   sudo systemctl start patroni.service
   ```

5. Проверки успешного запуска:

   - статус службы — `active` (в примере вывода видно, что Patroni сам запускает `pg_ctl initdb` / `initdb` с ключами `--encoding=UTF8 --data-checksums --locale=ru_RU.UTF-8`, в журнале — «Data page checksums are enabled»):

     ```bash
     sudo systemctl status patroni.service
     ```

   - в каталоге из параметра `data_dir` секции `postgresql` появилась структура кластера PostgreSQL (`base`, `global`, `pg_wal`, `pg_hba.conf`, `postgresql.conf` и т. д.):

     ```bash
     sudo ls -l /var/lib/pgsql/11/data
     ```

   - PostgreSQL запущен и слушает порт 5432:

     ```bash
     ss -ltn | grep 5432
     ```

   - к кластеру можно подключиться пользователем `usr1cv8`:

     ```bash
     psql -U usr1cv8 -d postgres
     ```

6. Если всё в порядке — автозапуск:

   ```bash
   sudo systemctl enable patroni.service
   ```

#### 4.3. Настройка patronictl

Чтобы не указывать параметры подключения при каждом вызове `patronictl`, создаётся файл настроек по умолчанию `~/.config/patroni/patronictl.yaml` (отступы восстановлены по смыслу):

```yaml
dcs_api:
  etcd://localhost:2379
namespace: /db/
scope: postgres
authentication:
  username: patroni
  password: patroni
```

Проверка:

```bash
patronictl list
```

Ожидаемый результат — один узел в роли `Leader` в состоянии `running`:

```text
+----------+--------+---------------+--------+---------+----+-----------+-----------------+
| Cluster  | Member | Host          | Role   | State   | TL | Lag in MB | Pending restart |
+----------+--------+---------------+--------+---------+----+-----------+-----------------+
| postgres | dbone  | dbone.example | Leader | running | 1  | 0.0       |                 |
+----------+--------+---------------+--------+---------+----+-----------+-----------------+
```

#### 4.4. Добавление нового узла Patroni

На каждом следующем сервере СУБД повторяются все действия раздела «Первый узел Patroni». Отличается только `/etc/patroni/patroni.yml`: везде `dbone` заменяется именем текущего сервера. То есть для `dbtwo.example` меняются ровно три строки (остальное содержимое файла идентично приведённому выше; в источнике файл для dbtwo приведён целиком и отличается только ими):

```yaml
name: dbtwo
restapi:
  connect_address: dbtwo.example:8008
postgresql:
  connect_address: dbtwo.example:5432
```

Что происходит после запуска Patroni на резервном сервере:

1. Patroni подключается к кластеру на `dbone.example`.
2. Создаётся новый кластер PostgreSQL и заполняется данными с `dbone.example`.
3. Новый кластер PostgreSQL переводится в режим ведомого («slave mode»).

В итоге `patronictl list` должен показать три узла: `dbone` — `Leader`, `dbtwo` и `dbthree` — без роли лидера, все в состоянии `running`, у резервных «Lag in MB» = 0.0:

```text
+----------+---------+-----------+--------+---------+----+-----------+-----------------+
| Cluster  | Member  | Host      | Role   | State   | TL | Lag in MB | Pending restart |
+----------+---------+-----------+--------+---------+----+-----------+-----------------+
| postgres | dbone   | 10.0.0.21 | Leader | running | 1  |           |                 |
| postgres | dbtwo   | 10.0.0.22 |        | running | 1  | 0.0       |                 |
| postgres | dbthree | 10.0.0.23 |        | running | 1  | 0.0       |                 |
+----------+---------+-----------+--------+---------+----+-----------+-----------------+
```

### 5. HAProxy

Зачем: в параметрах информационной базы в кластере 1С:Предприятия указывается одно имя сервера СУБД. Перечислить все серверы PostgreSQL сразу нельзя, а роли (ведущий / резервный) могут смениться в любой момент. Поэтому создаётся единая точка подключения — HAProxy на `core.example`. Его задача — следить за ролями серверов PostgreSQL и при их изменении оперативно перенаправлять запросы 1С:Предприятия к СУБД на новый ведущий сервер.

Действия на `core.example`:

1. Установить HAProxy из пакета и отложить настройки по умолчанию:

   ```bash
   sudo yum install -y haproxy
   sudo mv /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.conf.def
   ```

2. Создать `/etc/haproxy/haproxy.cfg` (отступы восстановлены по смыслу):

   ```text
   global
       maxconn 100

   defaults
       log global
       mode tcp
       retries 2
       timeout client 30m
       timeout connect 4s
       timeout server 30m
       timeout check 5s

   listen stats
       mode http
       bind *:7000
       stats enable
       stats uri /

   listen postgres
       bind *:5432
       option httpchk
       http-check expect status 200
       default-server inter 3s fastinter 1s fall 2 rise 2 on-marked-down shutdown-sessions
       server dbone dbone.example:5432 maxconn 100 check port 8008
       server dbtwo dbtwo.example:5432 maxconn 100 check port 8008
       server dbthree dbthree.example:5432 maxconn 100 check port 8008
   ```

   Что задаёт пример (расшифровка директив — пояснение составителя конспекта, в статье её нет): TCP-режим; приём подключений к PostgreSQL на `*:5432`; проверка узлов HTTP-запросом на порт 8008 (REST API Patroni) с ожиданием кода 200; интервал проверки 3 с (ускоренный — 1 с), 2 неудачи — узел выводится, 2 успеха — возвращается; при пометке узла недоступным его сессии разрываются (`on-marked-down shutdown-sessions`); страница статистики — на порту 7000; таймауты клиента и сервера — 30 минут, лимит подключений — 100.

3. Запуск. Если SELinux не выключался, сначала разрешить HAProxy обращаться на внешние адреса:

   ```bash
   sudo setsebool -P haproxy_connect_any=1
   sudo systemctl start haproxy.service
   ```

4. Проверка запуска:

   ```bash
   sudo systemctl status haproxy.service
   ```

   Затем в веб-интерфейсе HAProxy `http://core.example:7000/` убедиться, что узлы кластера Patroni найдены и роли определены верно: **ведущий сервер отмечен «UP», резервные — «DOWN»**.

5. Если запуск успешен — автозагрузка:

   ```bash
   sudo systemctl enable haproxy.service
   ```

### 6. Изменение настроек PostgreSQL через Patroni

Раз PostgreSQL управляется Patroni, то и его настройки задаются через конфигурационный файл Patroni. Рекомендация авторов — держать эти настройки одинаковыми на всех узлах. Используется параметр `parameters` секции `postgresql` файла `/etc/patroni/patroni.yml`. Исходное состояние:

```yaml
parameters:
  unix_socket_directories: '/var/run/postgresql/'
```

Действия на серверах PostgreSQL:

1. Привести `parameters` к виду (отступы восстановлены по смыслу):

   ```yaml
   parameters:
     unix_socket_directories: '/var/run/postgresql/'
     shared_buffers: '1024MB'
     temp_buffers: '256MB'
     work_mem: '64MB'
     standard_conforming_strings: off
     escape_string_warning: off
     shared_preload_libraries: 'online_analyze, plantuner'
     plantuner.fix_empty_table: on
     online_analyze.enable: on
     online_analyze.table_type: 'temporary'
     online_analyze.local_tracking: on
     online_analyze.verbose: off
     maintenance_work_mem: '256MB'
     max_locks_per_transaction: 256
     lc_messages: 'en_US.UTF-8'
     log_line_prefix: '%m [%p] %q%u@%d '
   ```

   (исправлено по смыслу: в источнике четыре параметра записаны как `online_analize.enable`, `online_analize.table_type`, `online_analize.local_tracking`, `online_analize.verbose` — через «i», хотя подключаемая в том же блоке библиотека называется `online_analyze`. Перед применением сверить написание со статьями о настройке PostgreSQL для 1С.)

   **Оговорка авторов:** значения приведены только как пример того, как задавать параметры. Сами значения нужно определять по статьям ИТС «Настройки PostgreSQL для работы с 1С:Предприятием» и «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2».

2. Применить настройки — перечитать конфигурацию и перезапустить PostgreSQL по очереди на каждом узле:

   ```bash
   patronictl reload postgres dbone
   patronictl restart postgres dbone
   patronictl reload postgres dbtwo
   patronictl restart postgres dbtwo
   patronictl reload postgres dbthree
   patronictl restart postgres dbthree
   ```

3. Проверить, что настройки изменились:

   ```bash
   psql -U usr1cv8 -d postgres
   ```

   ```sql
   SHOW ALL;
   ```

### 7. Проверка переключения на резервный сервер

#### 7.1. Подготовка

В кластере 1С:Предприятия создаётся информационная база:

```text
Имя: test
Сервер баз данных: localhost
Тип СУБД: PostgreSQL
База данных: test
Пользователь сервера БД: usr1cv8
Пароль пользователя сервера БД: usr1cv8
```

Пояснение составителя: в статье причина не названа, но по описанию стенда сервер 1С и HAProxy (слушает 5432) стоят на одной машине `core.example`, поэтому `localhost` здесь — это адрес HAProxy.

В базу загружается произвольная конфигурация. После окончания загрузки проверяется, что данные дошли до резервных серверов:

```bash
patronictl list
```

В колонке «Lag in MB» у резервных серверов должно быть `0.0`.

Для тестов информационная база «Test» открывается в режиме 1С:Предприятие.

#### 7.2. Тест: плановое переключение ведущего сервера

1. На `dbone.example` выполнить команду смены ведущего сервера:

   ```bash
   patronictl failover
   ```

2. Проверить переключение:

   ```bash
   patronictl list
   ```

   В примере роль `Leader` перешла с `dbone` на `dbtwo`, остальные узлы — `running` с отставанием 0.0.

3. Проверить работу в информационной базе: 1С:Предприятие не должно заметить изменений в инфраструктуре.

#### 7.3. Тест: сбой ведущего сервера

1. На текущем ведущем (`dbtwo.example`) выполнить перезагрузку:

   ```bash
   shutdown -r
   ```

2. На `dbone.example` проверить переключение:

   ```bash
   patronictl list
   ```

   В примере лидером снова становится `dbone`, перезагруженный `dbtwo` возвращается в кластер резервным.

3. Проверить работу в информационной базе: 1С:Предприятие не должно заметить изменений в инфраструктуре.

### 8. Резервное копирование

Пример создания резервной копии кластера PostgreSQL средствами из его поставки. Копию можно снимать **как на ведущем, так и на резервном сервере**.

1. Создать копию:

   ```bash
   pg_basebackup -D ~/postgres.bak -Ft -z -P -U usr1cv8
   ```

2. Убедиться, что копия создана:

   ```bash
   ls ~/postgres.bak
   ```

   Ожидаемое содержимое: `base.tar.gz` и `pg_wal.tar.gz`.

### 9. Восстановление после сбоев

**Оговорки авторов:**

- последовательность ниже — это проверка восстановления резервной копии на демонстрационном стенде;
- в реальной ситуации подраздел «Удаление данных» должен быть пересмотрен с учётом фактических обстоятельств сбоя (на стенде данные уничтожаются намеренно, чтобы имитировать потерю);
- подраздел «Восстановление» предполагает, что описанное решение (кластер Patroni) уже полностью развёрнуто и его нужно лишь наполнить данными.

#### 9.1. Удаление данных (имитация потери на стенде)

1. Проверить текущие роли узлов:

   ```bash
   patronictl list
   ```

2. Остановить Patroni и PostgreSQL на **резервных** серверах:

   ```bash
   sudo systemctl stop patroni
   sudo systemctl stop postgresql-11
   ```

3. Остановить Patroni и PostgreSQL на **ведущем** сервере:

   ```bash
   sudo systemctl stop patroni
   sudo systemctl stop postgresql-11
   ```

4. Удалить кластер Patroni:

   ```bash
   patronictl remove postgres
   ```

5. На всех серверах PostgreSQL удалить каталоги кластера:

   ```bash
   sudo rm -rf /var/lib/pgsql/11/data
   ```

#### 9.2. Восстановление

1. Восстановить каталог кластера PostgreSQL на новом ведущем сервере (на `dbone.example`):

   ```bash
   sudo mkdir /var/lib/pgsql/11/data
   sudo chown postgres:postgres /var/lib/pgsql/11/data
   sudo chmod 700 /var/lib/pgsql/11/data
   sudo tar xzf base.tar.gz -C /var/lib/pgsql/11/data
   sudo tar xzf pg_wal.tar.gz -C /var/lib/pgsql/11/data/pg_wal
   sudo rm /var/lib/pgsql/11/data/recovery.conf
   sudo rm /var/lib/pgsql/11/data/recovery.done
   sudo systemctl start patroni
   ```

   ⚠ в источнике неясно: архивы `base.tar.gz` и `pg_wal.tar.gz` указаны без пути, хотя созданы они были в `~/postgres.bak`; текущий каталог для команд `tar` не оговорён.

2. Перенести резервную копию на будущие резервные серверы (с `dbone.example`):

   ```bash
   scp -r ~/postgres.bak dbtwo.example:postgres.bak
   scp -r ~/postgres.bak dbthree.example:postgres.bak
   ```

3. На `dbtwo.example` и `dbthree.example` повторить те же действия, что были выполнены на `dbone.example` (шаг 1).

4. Проверить результат:

   ```bash
   patronictl list
   ```

   Ожидается: `dbone` — `Leader`, `dbtwo` и `dbthree` — `running` с «Lag in MB» = 0.0.

### 10. Использование резервного сервера PostgreSQL для механизма копий базы данных

#### 10.1. В чём проблема

У механизма копий баз данных при размещении данных в PostgreSQL есть особенность в использовании **внешнего** типа репликации. Резервный сервер PostgreSQL доступен только на чтение — **включая временные таблицы**. Поэтому запросы к СУБД с созданием временных таблиц, которые выполняет 1С:Предприятие, на резервном сервере завершаются ошибкой.

Решение: развернуть **дополнительный кластер PostgreSQL, доступный для записи**, и обращаться к данным резервного сервера через него (как к внешним таблицам).

#### 10.2. Создание дополнительного кластера PostgreSQL

Два варианта:

- добавить новый сервер и установить на него PostgreSQL — порядок действий не отличается от обычной установки PostgreSQL;
- если новый сервер нежелателен — разместить дополнительный кластер на одном из существующих серверов PostgreSQL (этот вариант и показан).

Пример: на `dbthree.example`, данные кластера — в `/var/lib/pgsql/11/proxy`.

1. Инициализировать кластер:

   ```bash
   export LANG="ru_RU.UTF-8"
   sudo -u postgres /usr/pgsql-11/bin/initdb -D /var/lib/pgsql/11/proxy --auth-local=peer --auth-host=md5
   ```

   В примере вывода: локали `COLLATE`, `CTYPE`, `MESSAGES` — `ru_RU.UTF-8`; кодировка по умолчанию — `UTF8`; конфигурация текстового поиска — `russian`; контрольные суммы страниц данных **отключены** («Data page checksums are disabled» — в отличие от основного кластера, созданного Patroni с `data-checksums`).

2. Создать unit-файл `/etc/systemd/system/postgresql-11-proxy.service`:

   ```ini
   [Unit]
   Description=PostgreSQL 11 database proxy server
   After=syslog.target
   After=network.target

   [Service]
   Type=notify
   User=postgres
   Group=postgres
   Environment=PGDATA=/var/lib/pgsql/11/proxy/
   OOMScoreAdjust=-1000
   ExecStartPre=/usr/pgsql-11/bin/postgresql-11-check-db-dir ${PGDATA}
   ExecStart=/usr/pgsql-11/bin/postmaster -D ${PGDATA}
   ExecReload=/bin/kill -HUP $MAINPID
   KillMode=mixed
   KillSignal=SIGINT
   TimeoutSec=300

   [Install]
   WantedBy=multi-user.target
   ```

3. Задать порт, на котором дополнительный кластер принимает подключения клиентов. ⚠ в источнике неясно: файл назван `/var/lib/pgsql/11/proxy/postgre.sql`; по содержимому (секция «CONNECTIONS AND AUTHENTICATION») это `postgresql.conf` в каталоге дополнительного кластера.

   ```ini
   #------------------------------------------------------------------------------
   # CONNECTIONS AND AUTHENTICATION
   #------------------------------------------------------------------------------
   # - Connection Settings -
   listen_addresses = '*'          # what IP address(es) to listen on;
                                   # comma-separated list of addresses;
                                   # defaults to 'localhost'; use '*' for all
                                   # (change requires restart)
   port = 5433
   ```

   Пояснение составителя: основной экземпляр PostgreSQL на этом же сервере слушает 5432, дополнительный — 5433.

4. Перечитать настройки systemd и запустить второй демон PostgreSQL:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start postgresql-11-proxy.service
   ```

5. Проверить, что порт слушается:

   ```bash
   ss -ltn | grep 5433
   ```

6. Если запуск успешен — автозапуск:

   ```bash
   sudo systemctl enable postgresql-11-proxy.service
   ```

#### 10.3. Настройка дополнительного кластера

1. Создать пользователя для 1С:Предприятия. Войти пользователем `postgres`:

   ```bash
   sudo -u postgres psql -p 5433
   ```

   и создать пользователя:

   ```sql
   CREATE USER usr1cv8 WITH SUPERUSER LOGIN ENCRYPTED PASSWORD 'usr1cv8';
   ```

2. Создать информационную базу в кластере 1С:Предприятия:

   ```text
   Имя: test
   Сервер баз данных: dbthree.example port=5433
   Тип СУБД: PostgreSQL
   База данных: test
   Пользователь сервера БД: usr1cv8
   Пароль пользователя сервера БД: usr1cv8
   ```

   Зачем создавать именно через 1С: при создании базы данных платформа выполняет в ней тонкие настройки, которые могут зависеть от версии платформы 1С:Предприятия; создание информационной базы гарантирует корректное создание базы данных в кластере PostgreSQL.

#### 10.4. Настройка промежуточной базы данных

1. Войти пользователем `postgres` в созданную базу:

   ```bash
   sudo -u postgres psql -p 5433 -d test
   ```

2. Удалить все таблицы (запрос формирует оператор `DROP TABLE` по всем таблицам схемы `public`, `\gexec` тут же его выполняет):

   ```sql
   select 'DROP TABLE ' || string_agg(tablename, ', ') || ';' from pg_tables where schemaname = 'public' \gexec
   ```

3. Создать в базе расширение `postgres_fdw`:

   ```sql
   CREATE EXTENSION postgres_fdw;
   ```

4. Создать внешний сервер с параметрами подключения к резервному серверу:

   ```sql
   CREATE SERVER standby_server FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host '', dbname 'test', port '5432');
   ```

   ⚠ в источнике неясно: значение `host` в команде пустое (`host ''`). По тексту шага здесь задаются параметры подключения к резервному серверу; конкретный адрес в статье не приведён.

5. Создать отображения пользователей промежуточного сервера на пользователя резервного:

   ```sql
   CREATE USER MAPPING FOR postgres SERVER standby_server OPTIONS (user 'usr1cv8', password 'usr1cv8');
   CREATE USER MAPPING FOR usr1cv8 SERVER standby_server OPTIONS (user 'usr1cv8', password 'usr1cv8');
   ```

6. Импортировать таблицы внешней базы:

   ```sql
   IMPORT FOREIGN SCHEMA public FROM SERVER standby_server INTO public;
   ```

#### 10.5. Что указывать в настройках копии базы данных

В настройках подключения к копии базы данных указывается **промежуточная** база:

```text
Сервер: dbthree.example port=5433
База данных: test
```

#### 10.6. Запрет выбора узла ведущим (секция tags в patroni.yml)

Если резервный сервер используется для копии базы данных, имеет смысл запретить Patroni выбирать его ведущим. Для этого правится секция `tags` файла `patroni.yml`. По умолчанию:

```yaml
tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
```

| Тег | Действие |
|---|---|
| `nofailover` | `true` запрещает выбирать этот узел в качестве ведущего |
| `clonefrom` | `true` рекомендует брать этот узел как источник резервной копии при развёртывании нового узла Patroni; если `true` стоит у нескольких узлов — один выбирается случайно |
| `noloadbalance` | Задаёт HTTP-код возврата 503 для запроса `GET /replica` REST API |
| `nosync` | `true` запрещает выбирать этот узел для синхронной репликации |

То есть на узле, отданном под копию базы данных, выставляется `nofailover: true` (итоговый вид секции в статье не приведён — вывод следует из описания тега).

Итог авторов: после выполнения этих настроек внешняя синхронизация для механизма копий баз данных и выполнение запросов на копии должны работать корректно. ⚠ в источнике неясно: в итоговой фразе названа «СУБД MS SQL Server», хотя весь раздел посвящён PostgreSQL, — по-видимому, оговорка.

### 11. Реструктуризация информационной базы

При изменении структуры метаданных информационной базы меняется и структура базы данных. Эти изменения нужно перенести в промежуточную базу: удалить импортированные таблицы и импортировать схему заново. Действия на `dbthree.example`:

1. Войти пользователем `postgres` в промежуточную базу:

   ```bash
   sudo -u postgres psql -p 5433 -d test
   ```

2. Удалить импортированные (внешние) таблицы:

   ```sql
   select 'DROP FOREIGN TABLE ' || string_agg(table_name, ', ') || ';' from information_schema.tables where table_type = 'FOREIGN' \gexec
   ```

3. Импортировать таблицы внешней базы заново:

   ```sql
   IMPORT FOREIGN SCHEMA public FROM SERVER standby_server INTO public;
   ```

### 12. Сводный чек-лист по статье

Порядок работ в том виде, как он изложен в статье:

1. Привести имена хостов к DNS-именам (`hostnamectl set-hostname ... --static`).
2. На `core` — сервер 1С:Предприятия; на узлах СУБД — PostgreSQL сборки 1С, без `initdb`, с отключённым автозапуском службы.
3. etcd: первый узел (`new`) → проверка `cluster-health` → `enable`; далее для каждого узла: `member add` на действующем узле → конфиг с `existing` на новом → запуск → проверка → `enable`.
4. Выровнять `ETCD_INITIAL_CLUSTER` и выставить `existing` на всех узлах.
5. Создать пользователя `root` в etcd и включить авторизацию.
6. На узлах СУБД: Python 3, `psycopg2-binary`, `patroni[etcd]`.
7. Первый узел Patroni: `/etc/patroni` (владелец `postgres`, права 700), `patroni.yml`, unit-файл, `daemon-reload`, запуск, проверки (служба, каталог данных, порт 5432, вход под `usr1cv8`), `enable`.
8. Настроить `patronictl` (`~/.config/patroni/patronictl.yaml`), проверить `patronictl list`.
9. Остальные узлы Patroni — то же с заменой имени узла; убедиться, что в кластере три узла.
10. HAProxy на `core`: конфиг, при необходимости `setsebool`, запуск, проверка страницы статистики на 7000 (ведущий «UP», резервные «DOWN»), `enable`.
11. Задать рабочие параметры PostgreSQL в `patroni.yml` на всех узлах, `patronictl reload` + `restart` по каждому, проверить `SHOW ALL`.
12. Создать информационную базу через адрес HAProxy, загрузить конфигурацию, проверить отставание 0.0.
13. Тесты: плановое переключение и перезагрузка ведущего; 1С не должна заметить.
14. Резервная копия `pg_basebackup`; проверка восстановления.
15. Для механизма копий баз данных: дополнительный экземпляр PostgreSQL на 5433 → пользователь → информационная база через 1С → удаление таблиц → `postgres_fdw` → внешний сервер → отображения пользователей → импорт схемы → указать промежуточную базу в настройках копии → `nofailover: true` на узле.
16. После каждой реструктуризации — пересоздать внешние таблицы.

### 13. Замеченные неточности источника

Перечень мест, где текстовая копия статьи искажена или содержит опечатки (в конспекте они либо исправлены с пометкой, либо отмечены знаком ⚠):

- В первом `etcd.conf` два параметра (`ETCD_INITIAL_ADVERTISE_PEER_URLS` и `ETCD_ADVERTISE_CLIENT_URLS`) слиты в одну строку — в конспекте разнесены.
- Описание `ETCD_ADVERTISE_CLIENT_URLS` повторяет описание `ETCD_INITIAL_ADVERTISE_PEER_URLS`.
- В итоговом `ETCD_INITIAL_CLUSTER` опечатка в имени хоста: `dbonew.example` — в конспекте исправлено на `dbone.example`.
- В перечне серверов для установки Patroni опечатка: `dbthree.exemple`.
- В YAML-файлах (`patroni.yml`, `patronictl.yaml`, блок `parameters`) и в `haproxy.cfg` потеряна вложенность отступов — в конспекте восстановлена по смыслу.
- Параметры `online_analize.*` (через «i») при библиотеке `online_analyze` — в конспекте исправлено с пометкой.
- Конфигурационный файл дополнительного кластера назван `postgre.sql`.
- В `CREATE SERVER standby_server ...` пустое значение `host`.
- В итоговой фразе раздела про копии баз данных упомянут MS SQL Server вместо PostgreSQL.
- В описании тестов написано, что 1С:Предприятие изменений «заменить» не должно — по смыслу «заметить».
- Про три сервера СУБД сказано «на обоих».
- Команды `tar` при восстановлении используют имена архивов без пути.
- Примеры вывода команд (`etcdctl member list`, `patronictl list`) местами не согласованы между собой (идентификаторы узлов etcd, номера линий времени TL); в конспекте они приведены только как иллюстрация ожидаемого результата.

