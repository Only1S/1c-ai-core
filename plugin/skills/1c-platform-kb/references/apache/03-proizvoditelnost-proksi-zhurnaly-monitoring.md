# Apache: производительность и настройка MPM, обратный прокси и балансировка, журналы, mod_status, мониторинг

> **Официальные тексты по теме** (конспекты полных текстов ИТС): `../its-docs/adm-gl08-veb-servery-p1.md` (разд. 8.2 — для Linux рекомендуется MPM `worker`; каждый рабочий процесс веб-сервера обслуживает свой экземпляр расширения 1С), `../its-docs/adm-gl08-veb-servery-p2.md` (разд. 8.10.1.1 — `ServerLimit 1` для файловой базы; разд. 8.10.3 — какие заголовки должен передавать обратный прокси), `../its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md` (ИТС-мет 5980 — заголовки прокси перед публикацией; ИТС-мет 5899 — на веб-серверах должны собираться access- и error-журналы). По самому Apache первоисточник — документация httpd 2.4 (https://httpd.apache.org/docs/2.4/) и журнал изменений `CHANGES_2.4`. Публикация 1С (`webinst`, `default.vrd`, модуль `wsap24`) здесь не описывается — она в `../1c/05-veb-publikaciya-apache-nginx.md`.

> Статус: проверено независимой сверкой 20.10.2026: исходники документации Apache (ветка `2.4.x`), `CHANGES_2.4`, исходный код httpd 2.4.52, 2.4.58, 2.4.59–2.4.66 и 2.4.69 (MPM, `mod_status`, `mod_proxy`/`mod_proxy_http`/`proxy_util`, `mod_filter`, `mod_deflate`, `mod_brotli`, `core`), пакет `apache2` Ubuntu 22.04/24.04/26.04 на git.launchpad.net (конфигурация, `apache2.service`, `apache2ctl`, `envvars`, `a2enmod`, `README.Debian`, патчи jammy и noble), packages.ubuntu.com, документация systemd v255 и ядра (cgroup v2), пакет Grafana Alloy 1.20.1, README шаблонов Zabbix 7.4, `apache_exporter` и `wrk`, учебник Grafana, полный текст гл. 8 «Руководства администратора» 1С 8.3.27; исправлено 15 ошибок, закрыта 21 пометка «⚠»; на сервере не проверялось. Автор статьи сверял значения с документацией `2.4.x`, кодом 2.4.69 и пакетом Ubuntu; версии — на 20.10.2026.

> Область: Apache HTTP Server 2.4 на Ubuntu Server: выбор и расчёт MPM, соединения и таймауты, сжатие и кеширование, обратный прокси перед сервисами (Redmine, NetBox, GlitchTip, Grafana, Loki) и перед публикацией 1С на другом сервере, WebSocket, балансировка, журналы, `mod_status`, мониторинг (Zabbix, Prometheus, Loki/Grafana), нагрузочная проверка. | Версии: Apache httpd **2.4.69** (01.10.2026, текущий выпуск); пакет `apache2` в Ubuntu 22.04 — **2.4.52**-1ubuntu4.25, 24.04 — **2.4.58**-1ubuntu8.17, 26.04 — **2.4.66**-2ubuntu2.6. | Актуальность: 2026-10-20.

Пометки в тексте:

- **[Apache-док]** — документация Apache HTTP Server 2.4 и журнал изменений `CHANGES_2.4`; с уточнением «код» — исходный код выпуска 2.4.69;
- **[Ubuntu]** — файлы пакета `apache2` Ubuntu (конфигурация, `postinst`, `debian/rules`, `logrotate`), списки файлов и версии с packages.ubuntu.com, документация Ubuntu Server;
- **[Debian]** — `README.Debian` из того же пакета;
- **[ИТС-адм разд. N]** — «Руководство администратора» 1С:Предприятие 8.3.27;
- **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС с годом;
- **[сторонний]** — официальные страницы сторонних продуктов (Zabbix, prometheus apache_exporter, wrk, Grafana, Loki, Alloy) и статьи базы о сервисах;
- **[практика]** — вывод или опыт, первоисточника нет;
- **⚠** — не подтверждено первоисточником: проверьте на своём сервере.

Связанные статьи (их тема здесь не расписывается):

- `apache/01-ustanovka-i-ustrojstvo.md` — установка, раскладка `/etc/apache2`, `a2enmod`/`a2ensite`, `apache2ctl`, виртуальные хосты, порядок слияния секций;
- `apache/02-https-bezopasnost-autentifikaciya.md` — TLS и сертификаты (certbot), заголовки безопасности, Basic/LDAP/Kerberos (`mod_auth_gssapi`), ограничение доступа;
- `apache/04-tipovye-problemy-i-apache-na-windows.md` — разбор типовых отказов и Apache под Windows (`mpm_winnt`, Apache Lounge);
- `../1c/05-veb-publikaciya-apache-nginx.md` — публикация 1С: `webinst`, `default.vrd`, `wsap24`, пример MPM для 1С (разд. 12), nginx перед Apache (разд. 9);
- `../1c/10-proizvoditelnost-otkazoustojchivost-ekspluataciya.md` — производительность сервера 1С;
- `../linux/06-processy-i-proizvoditelnost.md` — `ps`, `top`, память процессов; `../linux/08-set-ssh-firewall.md` — `ss`, `ufw`; `../linux/05-systemd-sluzhby-zhurnaly-cron.md` — systemd, `journalctl`, `logrotate`;
- `../observability/03-loki-i-grafana.md` — Loki, LogQL, Grafana, Alloy; `../observability/02-glitchtip.md` — GlitchTip;
- `../redmine/02-ustanovka-ubuntu-postgresql.md` (разд. 13 — Apache перед Redmine), `../netbox/02-ustanovka-ubuntu.md` и `../netbox/05-netbox-v-stende-nablyudaemosti.md`, `../guides/09-sovmestimost-instrumentov.md` — порты сервисов и прокси с TLS.

Условные обозначения в примерах:

| Хост | Роль | Apache |
|---|---|---|
| `srv-1c-app` | сервер 1С и публикация 1С (`wsap24`) | MPM `worker` (рекомендация 1С), публикации в `apache2.conf` или `conf-available/` |
| `srv-itsm` | Redmine, NetBox | MPM `event`, только обратный прокси с TLS |
| `srv-obs` | GlitchTip, Loki, Grafana | MPM `event`, только обратный прокси с TLS |
| `rp-1c` (условно) | внешний обратный прокси перед публикацией 1С на `srv-1c-app` | MPM `event` |

Домены `*.example.local`, адреса `10.10.0.0/24` и сервер мониторинга `10.10.0.50` условные — подставьте свои. Команды выполняются через `sudo` от администратора; рабочие процессы Apache работают от `www-data` [Ubuntu]. Порты сервисов — как в стенде (`../guides/09-…`): Redmine `8080`, NetBox `8090`, GlitchTip `8000`, Grafana `3000`, Loki `3100`; на рабочей ВМ публикуйте их только на `127.0.0.1`, а наружу выпускайте через Apache [сторонний: `../guides/09-…`].

---

## Кратко — главные факты

1. **MPM.** `prefork` — процесс на соединение; `worker` — потоки, поток занят соединением всё время, включая простой keep-alive; `event` — простаивающий keep-alive держит слушающий поток [Apache-док]. Ubuntu включает `mpm_event` [Ubuntu], 1С для Linux рекомендует `worker` [ИТС-адм разд. 8.2]. Итог: `srv-1c-app` — `worker`, прокси-серверы — `event`.
2. **`MaxRequestWorkers`** — предел одновременных запросов; для `worker`/`event` ≤ `ServerLimit × ThreadsPerChild` и кратен `ThreadsPerChild`, иначе Apache поправит его с предупреждением [Apache-док]. Умолчание Apache — 16 × 25 = 400, в файлах Ubuntu — 150 [Ubuntu].
3. **`ServerLimit` и `ThreadLimit` при `reload` не меняются** — только `restart` [Apache-док].
4. **Исчерпание в `error.log`:** «server reached MaxRequestWorkers setting» — `AH00484` (event), `AH00286` (worker), `AH00161` (prefork); заранее — «within MinSpareThreads» `AH10159`/`AH00287`; «scoreboard is full» `AH03490` → увеличить `ServerLimit` [Apache-док, код 2.4.69].
5. **Память** считают по RSS: размер процесса × число процессов + запас, своп недопустим [Apache-док]. Огромный VSZ потоковых MPM — стеки потоков (`ulimit -s`, 8 МБ) [Apache-док].
6. **`Timeout` в Ubuntu 300 с** (у Apache 60) — ожидание ввода-вывода, а не предел длительности запроса; он же умолчание `ProxyTimeout` и `timeout=` прокси [Ubuntu, Apache-док].
7. **`KeepAlive On`, `KeepAliveTimeout 5`, `MaxKeepAliveRequests 100`** — у Apache и в Ubuntu; в `worker` простой keep-alive держит поток, выше ~60 с поднимать не советуют [Apache-док].
8. **`LimitRequestBody` с 2.4.54 — 1 ГиБ** (раньше 0): больше — `413`; Ubuntu не задаёт; действует и на прокси [Apache-док, Ubuntu].
9. **`LimitRequestFieldSize 8190`**, а заголовок SPNEGO бывает до 12392 байт; `LimitRequestFieldSize`, `LimitRequestLine` и `LimitRequestFields` берутся из первого виртуального хоста на IP:порт — задавать глобально (к `LimitRequestBody` это не относится: он действует по каталогам и `<Location>`) [Apache-док].
10. **`mod_reqtimeout` в Ubuntu:** `header=20-40,minrate=500`, `body=10,minrate=500` (у Apache `body=20`) — медленнее 500 байт/с → `408` [Ubuntu, Apache-док].
11. **Сжатие:** `mod_deflate` включён для текстовых типов, без `application/json`; `mod_brotli` (2.4.26+) есть, но выключен [Ubuntu, Apache-док]. Сжимать в одном звене; помнить о BREACH [Apache-док].
12. **`mod_cache` с `CacheQuickHandler on`** (умолчание) отдаёт кеш в обход проверок доступа [Apache-док] — не под 1С и не под сервисами с авторизацией.
13. **Обратный прокси:** `ProxyPass` + `ProxyPassReverse`, `ProxyRequests Off` [Apache-док]. `mod_proxy_http` сам ставит `X-Forwarded-For/Host/Server`, но не `Proto` и `Port` [Apache-док]; 1С требует `X-Forwarded-Port/Host/Proto/For` [ИТС-адм разд. 8.10.3] — недостающие через `RequestHeader set`.
14. **Пул соединений** — только у явного worker; `ProxyPass` проверяются по порядку (длинные пути раньше); URL-префикс → worker sharing, параметры позднего правила игнорируются [Apache-док].
15. **Реальный IP на бэкенде** — `mod_remoteip` (`RemoteIPHeader X-Forwarded-For`, для частных адресов — `RemoteIPInternalProxy`), а не `%{X-Forwarded-For}i` в журнале [Apache-док, Ubuntu].
16. **WebSocket** с 2.4.47 — `ProxyPass … upgrade=websocket`; `mod_proxy_wstunnel` устарел; простаивающий туннель живёт `max(Timeout, timeout=)` с 2.4.53, а в 2.4.52 (Ubuntu 22.04) — `min(Timeout, timeout=)` [Apache-док, CHANGES 2.4.53, код 2.4.52/2.4.58/2.4.69].
17. **Балансировка:** `mod_proxy_balancer` + `lbmethod_*` (`byrequests` по умолчанию, `bybusyness` — по активным запросам), привязка `stickysession` (cookie `ROUTEID`), проверки `mod_proxy_hcheck` (2.4.21+); `balancer-manager` — только `Require local`/`ip` [Apache-док, Ubuntu].
18. **Журналы Ubuntu:** `/var/log/apache2/{error,access,other_vhosts_access}.log`, формат `combined` с `%O` (`mod_logio` статический); logrotate ежедневно, 14 копий, `640 root:adm`, затем `reload` [Ubuntu].
19. **Время ответа:** `%D` (мкс), `%{ms}T` (2.4.13+), `%^FB` — до первого байта при `LogIOTrackTTFB On` [Apache-док].
20. **`mod_status` в Ubuntu включён:** `/server-status` с localhost, `ExtendedStatus On`, `ProxyStatus On`; машинный формат `?auto`, с 2.4.58 — ключ `GracefulWorkers` [Ubuntu, Apache-док, код].
21. **Мониторинг:** Zabbix 7.4 «Apache by HTTP»/«Apache by Zabbix agent», `apache_exporter` (порт 9117) — по `?auto` [сторонний]; журналы — Alloy → Loki (`../observability/03-…`).
22. **Нагрузка** (`ab`, `wrk`) — только тестовая база или статика: вызов HTTP-сервиса 1С без повторного использования сеансов создаёт сеанс и занимает лицензию [практика].

---

## 1. Версии и что от них зависит

### 1.1. Что стоит в Ubuntu

| Выпуск Ubuntu | Пакет `apache2` (20.10.2026) | Основа | Что важно для этой статьи |
|---|---|---|---|
| 22.04 (jammy) | 2.4.52-1ubuntu4.25 | 2.4.52 | нет `GracefulWorkers` в `?auto`, нет `hcmethod=GET11` и др., `LimitRequestBody` по умолчанию 0 (уточнено 20.10.2026: в коде 2.4.52 `AP_DEFAULT_LIMIT_REQ_BODY` = 0, а патч пакета `CVE-2022-29404.patch` правит только `mod_lua`; ни один из 92 патчей ветки `ubuntu/jammy-updates` умолчание не меняет); простаивающий туннель WebSocket закрывается по `min(Timeout, timeout=)` (разд. 10) |
| 24.04 (noble) | 2.4.58-1ubuntu8.17 | 2.4.58 | `GracefulWorkers`, `%{cuz}t`, `DeflateAlterETag`, `H2WebSockets`; нет `addressttl` и `ConnsAsyncWaitIO` |
| 26.04 (resolute) | 2.4.66-2ubuntu2.6 | 2.4.66 | всё перечисленное, `addressttl`, ключ `ConnsAsyncWaitIO`; юнит systemd с ограничениями (см. `../1c/05-…`, разд. 3.1) |
| сайт Apache | 2.4.69 от 01.10.2026 | — | текущий выпуск ветки 2.4 [Apache-док] |

Ubuntu переносит в свои сборки исправления безопасности, но не новые возможности. Поэтому функциональность определяется номером основы, а не датой пакета [практика]. Проверка на сервере:

```bash
apache2 -v                                   # Server version: Apache/2.4.58 (Ubuntu)
apache2ctl -V | grep -Ei 'version|mpm'       # Server MPM: event / worker
apache2ctl -M | sort                         # загруженные модули (shared и static)
apache2ctl -l                                # модули, вкомпилированные статически
a2query -M                                   # выбранный MPM (утилита Ubuntu)
dpkg -l apache2 apache2-bin apache2-utils | tail -n +6
```

`a2query` — служебная утилита Ubuntu/Debian для запроса включённых модулей и выбранного MPM; ключ `-M` есть в её исходнике [Debian, Ubuntu]. В `apache2-bin` Ubuntu статически вкомпилированы `unixd`, `logio`, `watchdog`, `version` и `log_config` (ключи `--enable-mods-static="unixd logio watchdog version"` и `--enable-log-config=static` в `debian/rules`). Поэтому `a2enmod logio` не нужен: формат `%O` работает сразу, а `mod_proxy_hcheck` получает обязательный для него `mod_watchdog` без отдельного включения [Ubuntu].

### 1.2. Возможности по версиям (всё — [Apache-док], `CHANGES_2.4` и страницы модулей)

| Возможность | С версии | 22.04 | 24.04 | 26.04 |
|---|---|---|---|---|
| `mod_brotli` | 2.4.26 | да | да | да |
| `RemoteIPProxyProtocol` (PROXY protocol в `mod_remoteip`) | 2.4.31 | да | да | да |
| параметр `responsefieldsize`; статус балансировщика `R` (hot spare) | 2.4.34 | да | да | да |
| `RequestReadTimeout handshake=` | 2.4.39 | да | да | да |
| `%h` с учётом `mod_remoteip`, `%{c}h` — адрес TCP-соединения | 2.4.39 | да | да | да |
| `ProxyPass … upgrade=websocket` средствами `mod_proxy_http`; список кодов в `ProxyErrorOverride` | 2.4.47 | да | да | да |
| `ProxyWebsocketFallbackToProxyHttp` | 2.4.48 | да | да | да |
| `LimitRequestBody` по умолчанию 1 ГиБ вместо 0 | 2.4.54 | нет (уточнено 20.10.2026 по коду 2.4.52 и патчам пакета) | да | да |
| туннель (WebSocket, CONNECT) живёт по большему из таймаутов клиента и бэкенда, а не по меньшему | 2.4.53 | нет | да | да |
| `hcmethod=OPTIONS11/HEAD11/GET11` (HTTP/1.1 в проверках) | 2.4.55 | нет | да | да |
| `rotatelogs -T` | 2.4.56 | нет | да | да |
| ключ `GracefulWorkers` в `?auto`, удаление дублей `BusyWorkers`/`IdleWorkers` | 2.4.58 | нет | да | да |
| `%{cuz}t` и `%{%-format}t` в `ErrorLogFormat`; `DeflateAlterETag`; `H2WebSockets` | 2.4.58 | нет | да | да |
| параметр `addressttl` (срок кеша DNS адреса бэкенда) | 2.4.59 | нет | нет (уточнено 20.10.2026: среди 68 патчей ветки `ubuntu/noble-updates` переноса нет) | да |
| ключ `ConnsAsyncWaitIO` в `?auto` | 2.4.63 (уточнено 20.10.2026 по `mod_status.c`: нет в 2.4.62, есть в 2.4.63) | нет | нет | да |
| `ListenTCPDeferAccept` | 2.4.66 по `CHANGES_2.4`; страница `mpm_common` пишет «2.5.1 and later» — ошибка документации | нет | нет | да (уточнено 20.10.2026: директива есть в коде 2.4.66 `server/listen.c`, в 2.4.65 нет) |

---

## 2. MPM: как устроены и какой выбрать

### 2.1. Три модели

| MPM | Как обслуживает соединения | Плюсы | Минусы |
|---|---|---|---|
| `prefork` | Управляющий процесс держит пул дочерних процессов без потоков; одно соединение — один процесс [Apache-док] | Изоляция запросов, годится для непотокобезопасных библиотек [Apache-док] | Больше всего памяти; у `mod_proxy` нет пула соединений к бэкенду, параметры `acquire`, `ttl`, `min`, `smax`, `hmax` игнорируются [Apache-док] |
| `worker` | Несколько процессов, в каждом `ThreadsPerChild` потоков и слушающий поток; поток занят соединением до его закрытия [Apache-док] | Меньше памяти, чем у `prefork` [Apache-док]; рекомендован 1С для публикации на Linux [ИТС-адм разд. 8.2] | Простаивающий keep-alive держит поток |
| `event` | Как `worker`, но слушающий поток берёт на себя keep-alive-сокеты, закрытие и дописывание ответа медленным клиентам; рабочие потоки освобождаются [Apache-док] | Тысячи простаивающих соединений не держат потоков; включён в Ubuntu по умолчанию [Ubuntu] | Для ответов от прокси/CGI/FastCGI поток всё равно занят до конца ответа: MPM не знает, где конец содержимого [Apache-док] |

Подробности `event` [Apache-док]:

- Все модули из поставки Apache совместимы с `event`. Если фильтр соединения объявил себя несовместимым, MPM для такого соединения откатывается к поведению `worker`.
- Ограничение «поток занят до конца ответа» касается и обратного прокси. Поэтому на прокси-сервере `event` экономит потоки на keep-alive, но не на долгих ответах бэкенда: долгий запрос к 1С или GlitchTip занимает поток так же, как в `worker`.
- Начиная с 2.4.24 процессы, которые завершаются мягко (graceful), используют слоты scoreboard до `ServerLimit`. Значит, `ServerLimit` должен покрывать и рабочие процессы, и процессы, доживающие после `reload`. В `mod_status` это колонки `Slot` и `Stopping`, состояние «Yes (old gen)».

### 2.2. Что выбрать на каждом сервере

| Сервер | MPM | Почему |
|---|---|---|
| `srv-1c-app` (публикация 1С, `wsap24`) | **`worker`** | Официальная рекомендация 1С для Linux [ИТС-адм разд. 8.2, 8.10.1.1]. В каждом процессе Apache свой экземпляр расширения 1С [ИТС-адм разд. 8.2], а значит, и свой пул соединений с кластером [практика], поэтому лучше мало процессов и много потоков (`../1c/05-…`, разд. 12.1). На `event` публикация на практике работает, но поддержка 1С вправе сослаться на документацию [`../1c/05-…`, разд. 3.3] |
| `srv-1c-app`, файловая база | `worker` с `ServerLimit 1` | Иначе фоновые задания файловой базы работают некорректно [ИТС-адм разд. 8.10.1.1] |
| `srv-itsm`, `srv-obs` (только прокси) | **`event`** | Много простаивающих соединений браузеров и API-клиентов; модулей сторонних производителей нет [практика] |
| внешний прокси `rp-1c` | `event` | То же; долгие запросы 1С займут потоки — считайте их как в `worker` (разд. 4) [Apache-док, практика] |
| сервер с `mod_php` | `prefork` | `libapache2-mod-php` переключает MPM на `prefork` [`../1c/05-…`, разд. 3.3, практика]; на серверах этой базы PHP нет |

### 2.3. Как переключить MPM

```bash
apache2ctl -V | grep -i 'server mpm'       # что сейчас
sudo a2dismod mpm_event                    # выключить текущий (в Ubuntu mpm_event.load помечен «Conflicts: mpm_worker mpm_prefork»)
sudo a2enmod  mpm_worker
sudo apache2ctl configtest                 # Syntax OK
sudo systemctl restart apache2             # смена MPM — только полный перезапуск
apache2ctl -V | grep -i 'server mpm'       # Server MPM:     worker
systemctl status apache2 --no-pager | head -n 12
```

⚠ **Предупреждение:** `restart` обрывает текущие запросы. Пользователи веб-клиента 1С переподключатся, а долгие вызовы HTTP-сервисов прервутся. Делайте это в окно обслуживания. Конфликт MPM записан в первой строке `.load`-файла (`# Conflicts: mpm_worker mpm_prefork`) [Ubuntu]. Если не выключить старый MPM, `a2enmod` откажет — подтверждено 20.10.2026 по исходнику `a2enmod` пакета (функция `check_conflicts`: «Module … is enabled - cannot proceed due to conflicts. It needs to be disabled first!») [Ubuntu].

---

## 3. Директивы MPM: умолчания, связи, сообщения

### 3.1. Сводная таблица

| Директива | Где действует | Умолчание Apache [Apache-док] | Файлы Ubuntu [Ubuntu] | Меняется при `reload`? |
|---|---|---|---|---|
| `StartServers` | все | event/worker 3, prefork 5 | event/worker 2, prefork 5 | да |
| `MinSpareThreads` | event, worker | 75 (на весь сервер) | 25 | да |
| `MaxSpareThreads` | event, worker | 250 (на весь сервер) | 75 | да |
| `ThreadLimit` | event, worker | 64 | 64 | **нет** |
| `ThreadsPerChild` | event, worker | 25 | 25 | да, не выше `ThreadLimit` |
| `ServerLimit` | все | 16 (prefork — 256) | не задан → 16 | **нет** |
| `MaxRequestWorkers` (старое имя `MaxClients`) | все | event/worker 16 × 25 = 400; prefork 256 | 150 | да |
| `MaxConnectionsPerChild` (старое `MaxRequestsPerChild`) | все | 0 (процесс не перезапускается) | 0 | да |
| `MinSpareServers` / `MaxSpareServers` | prefork | 5 / 10 | 5 / 10 | да |
| `AsyncRequestWorkerFactor` | event | 2 (допускаются дробные, например `1.5`; меньше 1 — поднимается до 1) | не задан | да, для новых процессов; если директиву удалить, до `restart` останется прежнее значение (уточнено 20.10.2026 по коду `event.c` 2.4.69: переменная при перечитывании не сбрасывается) |
| `ListenBackLog` | все | 511 (ограничивается ядром) | не задан | — |
| `MaxMemFree` | все | 2048 КБ на аллокатор (в потоковых MPM — у каждого потока свой) | не задан | — |
| `ThreadStackSize` | потоковые | по ОС; на Linux можно только увеличить | не задан | — |
| `GracefulShutdownTimeout` | все | 0 — ждать завершения запросов бесконечно | не задан | — |

Где лежат значения Ubuntu: `/etc/apache2/mods-available/mpm_event.conf`, `mpm_worker.conf`, `mpm_prefork.conf`. В 24.04 и 26.04 эти файлы содержат директивы без обёртки `<IfModule>`, в 22.04 — внутри `<IfModule mpm_event_module>` и т. п.; значения во всех трёх выпусках одинаковы [Ubuntu]. Файл подключается только вместе с включённым MPM (`IncludeOptional mods-enabled/*.conf` в `apache2.conf`) [Ubuntu].

### 3.2. Правила согласования (нарушение Apache исправит сам и запишет предупреждение) [Apache-док, код 2.4.69]

| Правило | Что произойдёт при нарушении | Сообщение (event / worker / prefork) |
|---|---|---|
| `MaxRequestWorkers` ≥ `ThreadsPerChild` | поднимется до `ThreadsPerChild` | `AH00511` / `AH00314` / — |
| `MaxRequestWorkers` кратно `ThreadsPerChild` | округлится вниз до кратного | `AH00513` / `AH00316` / — |
| `MaxRequestWorkers` ≤ `ServerLimit × ThreadsPerChild` (prefork: ≤ `ServerLimit`) | уменьшится до предела | `AH00515` / `AH00318` / `AH00180` |
| `ThreadsPerChild` ≤ `ThreadLimit` | уменьшится до `ThreadLimit` | предупреждение при запуске |
| `MaxSpareThreads` ≥ `MinSpareThreads` + `ThreadsPerChild` | будет исправлен автоматически | — |
| `MinSpareThreads`, `ServerLimit`, `ThreadLimit`, `StartServers` ≥ 1 | поднимется до 1 | `AH00519` (MinSpareThreads, event) |
| `ServerLimit` при `reload` | изменение игнорируется | `AH00501` / `AH00304` / `AH00179` |
| жёсткие пределы | `ServerLimit` ≤ 20000 (prefork 200000), `ThreadLimit` ≤ 20000 (event 100000, `mpm_winnt` 15000) | `AH00497`/`AH00498` и аналоги |

Пример расчёта из документации [Apache-док]: при `MaxRequestWorkers 90` и `ThreadsPerChild 25` Apache оставит 75 (3 процесса) и напишет «decreasing to nearest multiple 75». Проверка после правки:

```bash
sudo apache2ctl configtest
sudo systemctl reload apache2       # или restart, если менялись ServerLimit/ThreadLimit
sudo journalctl -u apache2 --since "-5 min" --no-pager
sudo grep -E 'AH0051[1-6]|AH0031[4-9]|AH0018[0-3]|AH0050[01]|AH0030[34]' /var/log/apache2/error.log | tail
```

### 3.3. Сообщения о нехватке потоков и процессов [Apache-док, код 2.4.69]

| Ситуация | event | worker | prefork | Что делать |
|---|---|---|---|---|
| Заняты все `MaxRequestWorkers`, новые соединения ждут в очереди `ListenBackLog` | `AH00484 server reached MaxRequestWorkers setting, consider raising the MaxRequestWorkers setting` | `AH00286` (тот же текст) | `AH00161` | увеличить `MaxRequestWorkers` (и `ServerLimit`), найти долгие запросы через `server-status` |
| Свободных потоков меньше `MinSpareThreads`, а до `MaxRequestWorkers` не добраться | `AH10159 server is within MinSpareThreads of MaxRequestWorkers…` | `AH00287` | — | ранний сигнал: запас мал |
| Scoreboard заполнен, хотя до `MaxRequestWorkers` не дошли (процессы доживают после `reload` или спада нагрузки) | `AH03490 scoreboard is full, not at MaxRequestWorkers.Increase ServerLimit.` | `AH00288` | — | увеличить `ServerLimit` (запас под мягко завершающиеся процессы) |
| Процессы порождаются пачками | `AH00486 server seems busy, (you may need to increase StartServers, ThreadsPerChild or Min/MaxSpareThreads)…` | `AH00289` | `AH00162` | поднять `MinSpareThreads`/`StartServers` |

С 2.4.36 `event` пишет `AH00484` только тогда, когда свободных потоков действительно нет; раньше появляется одноразовое `AH10159` [Apache-док, CHANGES 2.4.36]. `AH00484`/`AH00286` и `AH10159`/`AH00287` пишутся с уровнем `error` **один раз** за жизнь управляющего процесса: флаг хранится в данных, которые переживают `reload`, и сбрасывается только полным перезапуском [Apache-док, код 2.4.69]. Отсутствие сообщения в свежем хвосте журнала ничего не доказывает — смотрите `server-status` (разд. 13) [см. также `../1c/05-…`, разд. 12.1].

```bash
sudo grep -cE 'reached MaxRequestWorkers|within MinSpareThreads|scoreboard is full' /var/log/apache2/error.log
sudo zgrep -hE 'reached MaxRequestWorkers' /var/log/apache2/error.log.*.gz | tail   # в сжатых копиях
```

### 3.4. `event`: сколько соединений выдержит

Процесс `event` принимает новые соединения, только пока число его соединений (без закрывающихся) меньше `ThreadsPerChild + AsyncRequestWorkerFactor × свободные_потоки`. Если заняты все потоки, он закрывает keep-alive-соединения досрочно, не дожидаясь `KeepAliveTimeout` [Apache-док]. Оценка по документации:

```
макс. соединений ≈ (ThreadsPerChild + AsyncRequestWorkerFactor × свободные_потоки) × ServerLimit
при полностью свободных потоках:  (AsyncRequestWorkerFactor + 1) × MaxRequestWorkers
```

Для файлов Ubuntu (`MaxRequestWorkers 150`, фактор 2) это до 3 × 150 = 450 соединений при простое. Менять `AsyncRequestWorkerFactor` документация советует только по данным `mod_status` и после тщательных проверок [Apache-док].

### 3.5. Куда писать свои значения

- **Проще всего** править сам `/etc/apache2/mods-available/mpm_worker.conf` (или `mpm_event.conf`). Это конфигурационный файл пакета: при обновлении `apt` покажет запрос о слиянии изменений — сохраняйте свою версию [практика].
- **Альтернатива** — отдельный файл `/etc/apache2/conf-available/zz-mpm-tuning.conf` с теми же директивами и `sudo a2enconf zz-mpm-tuning`. `conf-enabled/*.conf` подключаются после `mods-enabled/*.conf` [Ubuntu, `apache2.conf`], а для директив MPM действует значение, прочитанное последним — уточнено 20.10.2026 по коду `worker.c`/`event.c` 2.4.69: обработчики `ThreadsPerChild`, `MaxRequestWorkers`, `ServerLimit` и др. просто присваивают глобальную переменную [Apache-док, код]. После правки всё равно сверяйте `server-status` и сообщения при запуске.
- Обёртку `<IfModule mpm_worker_module>` / `<IfModule worker.c>` ставьте, если файл может пережить смену MPM. В документации 1С пример дан как `<IfModule worker.c>` [ИТС-адм разд. 8.10.1.1]; оба имени допустимы [практика].

---

## 4. Расчёт под память и процессор

### 4.1. Метод из документации

Документация Apache сводит расчёт к простому правилу: сервер **никогда** не должен свопиться. Нужно определить средний размер процесса Apache (через `top` или список процессов), разделить на доступную память, оставив место другим процессам, и ограничить `MaxRequestWorkers` [Apache-док, perf-tuning]. Для потоковых MPM единица расчёта — процесс с `ThreadsPerChild` потоками [практика].

```bash
# процессы Apache: PID, число потоков (nlwp), RSS и VSZ в КБ
ps -o pid,ppid,user,nlwp,rss,vsz,cmd -C apache2 --sort=-rss
# суммарно по процессам www-data (RSS, МБ)
ps -o rss= -u www-data | awk '{s+=$1} END {printf "%.0f MB\n", s/1024}'
# память всей службы (cgroup) — строка Memory:
systemctl status apache2 --no-pager | grep -E 'Memory|Tasks'
# пик памяти службы (cgroup v2, файл memory.peak — с ядра 5.19; на ядре 5.15 из 22.04 его нет —
# уточнено 20.10.2026 по Documentation/admin-guide/cgroup-v2.rst ядер 5.15 и 5.19)
cat /sys/fs/cgroup/system.slice/apache2.service/memory.peak 2>/dev/null
free -m
```

Почему не смотреть на VSZ: у каждого потока резервируется стек, на Linux по умолчанию размера `ulimit -s` (8 МБ, если он `unlimited`) [Apache-док, `ThreadStackSize`]. Процесс со 128 потоками показывает около 1 ГБ виртуальной памяти, которая не занята физически [практика]. Уменьшать `ThreadStackSize` документация не советует: на Linux уже 128000 байт приводит к падениям с распространёнными модулями [Apache-док].

### 4.2. Порядок расчёта

1. Дать серверу поработать под обычной нагрузкой. Для 1С — после того как пользователи открыли веб-клиент и прошли типовые операции: модуль 1С и пул соединений инициализированы [практика].
2. Снять RSS процессов `apache2` (кроме управляющего от `root`) в пике: `ps … --sort=-rss`. Взять максимум, а не среднее, с запасом 20–30 % [практика].
3. Посчитать бюджет памяти Apache: `RAM − (ОС + сервер 1С + СУБД, если она на этом хосте + кэш файлов)`. На `srv-1c-app` львиная доля памяти принадлежит `rphost`/`rmngr` 1С (`../1c/10-…`), Apache получает остаток [практика].
4. `процессов = бюджет / RSS_процесса` → `ServerLimit` (с запасом на мягко завершающиеся процессы у `event`).
5. `MaxRequestWorkers = процессов × ThreadsPerChild`, проверить правила разд. 3.2.
6. Проверить под нагрузкой: `BusyWorkers` в `server-status` и отсутствие `AH00484`/`AH00286` (разд. 13).

Условный пример для `srv-1c-app` (числа **выдуманы для иллюстрации** — измерьте свои):

| Величина | Значение |
|---|---|
| RAM ВМ | 32 ГБ |
| ОС, 1С (`ragent`, `rmngr`, `rphost`), запас | 26 ГБ |
| бюджет Apache | 6 ГБ |
| RSS процесса `apache2` с модулем 1С и 128 потоками (замер) | 900 МБ → с запасом 1,2 ГБ |
| процессов | 6 / 1,2 = 5 → `ServerLimit 4` + 1 в запас |
| `ThreadsPerChild` / `ThreadLimit` | 128 / 128 |
| `MaxRequestWorkers` | 4 × 128 = 512 |

Готовая отправная точка для 1С на 100–150 пользователей и рассуждение «почему мало процессов и много потоков» — `../1c/05-…`, разд. 12.1. Для файловой базы — `ServerLimit 1` [ИТС-адм разд. 8.10.1.1; `../1c/05-…`, разд. 12.2].

Для прокси-серверов (`srv-itsm`, `srv-obs`) Apache лёгкий: модулей приложений нет, процесс `event` занимает десятки мегабайт ⚠ (оценка — измерьте). Значений Ubuntu (`MaxRequestWorkers 150`) хватает, пока одновременных **активных** запросов меньше 150. Простаивающие соединения при `event` потоков не занимают [Apache-док]. Поднимать стоит, если `BusyWorkers` регулярно подходит к 150.

### 4.3. Процессор

- Основные потребители процессора на прокси — рукопожатия TLS и сжатие. Keep-alive снижает число рукопожатий, а `DeflateCompressionLevel`/`BrotliCompressionQuality` (разд. 6) регулируют цену сжатия [Apache-док, практика].
- `HostnameLookups Off` — умолчание Apache и явно задано в `apache2.conf` Ubuntu. С `On` каждый запрос порождает как минимум одно обращение к DNS; имена в журналах восстанавливают потом утилитой `logresolve` [Apache-док, Ubuntu].
- `AllowOverride None` избавляет от поиска `.htaccess` в каждом каталоге [Apache-док]. В Ubuntu так настроены `/`, `/usr/share`, `/var/www` [Ubuntu].
- `ListenCoresBucketsRatio` (2.4.17+, `SO_REUSEPORT`) имеет смысл от 16 ядер (рекомендуемое отношение 8) [Apache-док]. На ВМ этой базы не нужен.

### 4.4. Пределы ОС

- **Очередь приёма:** `ListenBackLog 511` [Apache-док], фактически не больше `net.core.somaxconn` ядра [Apache-док: «often limited to a smaller number by the operating system»]. Посмотреть очередь слушающего сокета можно командой `ss -ltn 'sport = :443'`: в колонке `Recv-Q` — текущая очередь, в `Send-Q` — её предел [практика].
- **epoll:** при ошибке «AH00156: Couldn't create pollset in child; check system or user limits (prefork; у worker — AH03285 …in thread…, у event — AH00495 Couldn't create a Thread Safe Pollset…; уточнено 20.10.2026 по коду 2.4.x)» `README.Debian` советует поднять `fs.epoll.max_user_instances` выше `MaxClients + MaxClients/ThreadsPerChild` (для worker/event), например `fs.epoll.max_user_instances=1024` в `/etc/sysctl.conf` [Debian].
- **Файловые дескрипторы:** каждое соединение с клиентом и с бэкендом — дескриптор. Юнит Apache `LimitNOFILE` не задаёт (уточнено 20.10.2026 по `debian/apache2.service` веток jammy/noble/resolute), но предел ставит сам `apache2ctl` при запуске от `root`: `ulimit -n 8192` по умолчанию, значение берётся из переменной `APACHE_ULIMIT_MAX_FILES` в `/etc/apache2/envvars` (там есть закомментированный образец `ulimit -n 65536`) [Ubuntu: `debian/apache2ctl`, `README.Debian`]. Поэтому одного drop-in `LimitNOFILE=` мало — `apache2ctl` всё равно выставит 8192. Проверка для работающего процесса: `cat /proc/$(pgrep -o apache2)/limits | grep 'open files'`. При сотнях соединений на процесс и ошибках `Too many open files` — раскомментировать и поднять `APACHE_ULIMIT_MAX_FILES` в `envvars`, затем `restart`; значение не должно превышать жёсткий предел службы systemd (если превышает — дополнительно drop-in `LimitNOFILE=`, `../linux/05-…`) [Ubuntu, практика].

---

## 5. Соединения и таймауты

### 5.1. Таблица директив

| Директива | Умолчание Apache [Apache-док] | Ubuntu [Ubuntu] | Смысл и замечания |
|---|---|---|---|
| `Timeout` | 60 | **300** (`apache2.conf`) | Ожидание ввода-вывода: пакет от клиента при пустом буфере чтения, подтверждение при полном буфере записи, вывод CGI, умолчание `ProxyTimeout`. Это не общий предел длительности запроса |
| `KeepAlive` | On | On | Постоянные соединения HTTP/1.1 |
| `KeepAliveTimeout` | 5 (допускается суффикс `ms`) | 5 | Ожидание следующего запроса в том же соединении; после прихода запроса действует `Timeout`. Для имённого виртуального хоста без своего значения берётся значение первого хоста на IP:порт |
| `MaxKeepAliveRequests` | 100 (0 — без ограничения) | 100 | Документация советует держать высоким |
| `RequestReadTimeout` | `handshake=0 header=20-40,MinRate=500 body=20,MinRate=500` | `header=20-40,minrate=500`, `body=10,minrate=500` (`reqtimeout.conf`) | При нарушении — `408`, запись на уровне `info` (`LogLevel reqtimeout:info`). Этап `handshake` — с 2.4.39 |
| `LimitRequestBody` | 1073741824 (1 ГиБ); до 2.4.54 — 0 | не задан | 0 — без ограничения; действует для сервера, хоста, каталога, `<Location>` |
| `LimitRequestFieldSize` | 8190 | не задан | Размер одного заголовка; SPNEGO — до 12392 байт |
| `LimitRequestLine` | 8190 | не задан | Строка запроса (метод + URI + протокол), включая query string |
| `LimitRequestFields` | 100 | не задан | Число заголовков |
| `LimitXMLRequestBody` | 1000000 | не задан | Для модулей, разбирающих XML средствами Apache (например, WebDAV); влияет ли на SOAP-сервисы 1С — ⚠ (модуль 1С разбирает тело сам, вероятно, не влияет) |
| `ProxyTimeout` | значение `Timeout` | не задан → 300 | Ожидание данных от бэкенда (разд. 7) |
| `GracefulShutdownTimeout` | 0 | не задан | Сколько секунд после «graceful-stop» обслуживать текущие соединения; 0 — ждать до конца |

### 5.2. Keep-alive и MPM

- `worker`: каждое простаивающее keep-alive-соединение держит поток до `KeepAliveTimeout`. При 5 с это незаметно; при 60 с (так в эталонной конфигурации 1С `docker_fresh`, `../1c/05-…`, разд. 12.3) нужен соответствующий запас потоков [Apache-док, практика].
- `event`: простаивающие соединения держит слушающий поток, рабочие потоки свободны. Под нагрузкой keep-alive закрывается досрочно, если все потоки заняты [Apache-док].
- Документация: «в любом случае не поднимать выше примерно 60 секунд — большая часть выгоды теряется» [Apache-док, perf-tuning].
- Keep-alive-соединение считается одним «соединением» для `MaxConnectionsPerChild`, сколько бы запросов по нему ни прошло [Apache-док].

### 5.3. Долгие запросы 1С и веб-сервисов

Как на них влияют настройки Apache:

1. **Публикация на самом `srv-1c-app`.** Модуль 1С работает внутри процесса Apache. Пока он ждёт сервер 1С, Apache не обрывает запрос по `Timeout`: тот касается ввода-вывода с клиентом, а клиент в это время просто ждёт ответа [практика ⚠ — по документации Apache: `Timeout` перечисляет только ожидания ввода-вывода, предела «время выполнения обработчика» в нём нет]. Обрывать долгий запрос будут клиент (браузер, внешний сервис со своим таймаутом) или промежуточный прокси.
2. **Цепочка прокси.** На каждом звене таймаут ожидания ответа бэкенда (`timeout=` у `ProxyPass` или `ProxyTimeout`, по умолчанию — `Timeout`) должен быть **не меньше** самого долгого вызова. Правило для цепочки: `таймаут клиента ≥ таймаут внешнего прокси ≥ таймаут внутреннего прокси ≥ длительность вызова` [`../1c/05-…`, разд. 12.3, практика]. В Ubuntu без явной настройки это 300 с.
3. **Большие тела запросов** (загрузка файлов, пакеты обмена): `LimitRequestBody` (1 ГиБ по умолчанию) — на **каждом** звене цепочки, и `mod_reqtimeout`. Ubuntu требует от клиента не меньше 500 байт/с и первый байт тела за 10 с [Ubuntu]; для медленных каналов это обычно не проблема, но для `body=10` при «тяжёлом» начале обработки на клиенте возможны `408` ⚠.
4. **Перезапуск Apache обрывает вызовы.** `reload` (graceful) даёт текущим запросам завершиться, а старые процессы доживают в состоянии `G` [Apache-док]. `systemctl stop` (и `restart`) ведёт себя по-разному (уточнено 20.10.2026 по `debian/apache2.service` и коду 2.4.58/2.4.69):
   - **22.04/24.04:** юнит выполняет `ExecStop=apachectl graceful-stop`, но эта команда только посылает сигнал и сразу завершается (`server/mpm_unix.c`). Сразу после неё systemd шлёт основному процессу `SIGTERM` (`KillSignal` по умолчанию, `KillMode=mixed`; документация systemd прямо предупреждает, что такой `ExecStop` «may not result in a clean stop»), а получив `SIGTERM`, Apache прерывает мягкую остановку и завершает процессы с текущими запросами (одинаково в `event.c`, `worker.c`, `prefork.c`: «We might be here because we received SIGTERM»). Итог: остановка фактически не мягкая, долгие вызовы обрываются; `GracefulShutdownTimeout` здесь не влияет [Ubuntu, Apache-док, код].
   - **26.04:** в юните `KillSignal=SIGWINCH`, остановка действительно мягкая. При `GracefulShutdownTimeout 0` Apache ждёт окончания всех запросов, пока systemd не пошлёт `SIGKILL` по истечении `TimeoutStopSec` (в юните не задан → `DefaultTimeoutStopSec`, по умолчанию сборки systemd 90 с; фактическое значение — `systemctl show apache2 -p TimeoutStopUSec`). Чтобы остановка была предсказуемой, задайте `GracefulShutdownTimeout 60` (меньше `TimeoutStopSec`) [Ubuntu, Apache-док, systemd].
   - Перед плановой остановкой на любом выпуске дайте долгим вызовам завершиться сами (окно обслуживания, `server-status` без `W` по путям 1С) [практика].

### 5.4. Рекомендуемые значения

| Хост | Что задать | Где |
|---|---|---|
| `srv-1c-app` | `Timeout 300` (уже в Ubuntu); `KeepAliveTimeout 5`–`15`; `LimitRequestBody 0` или явный предел на `<Location>` публикаций, куда загружают файлы больше 1 ГиБ; `LimitRequestFieldSize 16384` глобально, если используется Kerberos (`apache/02-…`); `GracefulShutdownTimeout 60` | `conf-available/zz-1c-limits.conf` + `a2enconf` |
| `srv-itsm`, `srv-obs` | `KeepAliveTimeout 5`; `timeout=` у `ProxyPass` по характеру сервиса (60–120 с для веб-интерфейсов); `LimitRequestBody` согласовать с пределами вложений приложения | в виртуальном хосте сервиса |
| `rp-1c` | `timeout=` у `ProxyPass` ≥ самого долгого вызова 1С (например, 3600); `LimitRequestBody` как на бэкенде | в виртуальном хосте |

```apache
# /etc/apache2/conf-available/zz-1c-limits.conf  (srv-1c-app)
# Лимиты заголовков действуют для первого виртуального хоста на IP:порт — поэтому глобально
LimitRequestFieldSize 16384
LimitRequestLine      16384
GracefulShutdownTimeout 60

# Большие загрузки только в публикации demo (имя — ваше)
<Location "/demo">
    LimitRequestBody 0
</Location>
```

```bash
sudo a2enconf zz-1c-limits
sudo apache2ctl configtest && sudo systemctl reload apache2
# Проверка 413/400 до и после: тело 1,5 ГиБ на HTTP-сервис тестовой базы (не продуктив!)
head -c 1610612736 /dev/zero > /tmp/big.bin
curl -s -o /dev/null -w '%{http_code}\n' -X POST --data-binary @/tmp/big.bin \
     http://127.0.0.1/demo/hs/upload/test      # до правки 413, после — ответ сервиса
rm -f /tmp/big.bin
```

`LimitRequestBody 0` снимает защиту от гигантских тел на этом пути. Если загрузка нужна только аутентифицированным пользователям, лучше задать явный предел, например `LimitRequestBody 4294967296` (4 ГиБ; уточнено 20.10.2026 по коду `core.c` 2.4.52 и 2.4.69: значение разбирается `apr_strtoff` в 64-битный `apr_off_t` без верхней границы, так что больше 2 ГиБ принимается; на сервере не проверялось) [практика, код].

---

## 6. Сжатие и кеширование

### 6.1. `mod_deflate`

- Включён в Ubuntu по умолчанию (список модулей в `postinst`: `filter deflate`) [Ubuntu]. `deflate.conf` сжимает `text/html text/plain text/xml text/css text/javascript`, `application/x-javascript application/javascript application/ecmascript`, `application/rss+xml`, `application/wasm`, `application/xml`. В 22.04 строки обёрнуты в `<IfModule mod_deflate.c>`, во всех выпусках — в `<IfModule mod_filter.c>` [Ubuntu].
- **`application/json` не сжимается.** Это касается OData, HTTP-сервисов 1С, API NetBox, Redmine, GlitchTip. Как добавить для 1С — `../1c/05-…`, разд. 12.4. Для прокси-хостов — та же строка `AddOutputFilterByType DEFLATE application/json` в контексте сервера (файл в `conf-available/` + `a2enconf`): в одном контексте такие строки складываются. **Не пишите её одну внутри `<VirtualHost>`:** определение в более узком контексте заменяет унаследованный список типов, и в этом хосте сжимался бы только JSON [Ubuntu, Apache-док: `mod_filter`, `AddOutputFilterByType`]. Если нужно именно в хосте — перечислите в нём все типы.
- Поддерживается только кодировка `gzip`; `mod_deflate` сам выставляет `Vary: Accept-Encoding` [Apache-док].
- **TLS и BREACH:** документация предупреждает, что сжатие внутри TLS делает часть приложений уязвимыми к атакам семейства BREACH [Apache-док]. Для страниц с секретами в теле (CSRF-токены форм) это осознанный выбор [практика].
- Настройки: `DeflateCompressionLevel` 1–9 (по умолчанию — значение zlib), `DeflateBufferSize 8096`, `DeflateWindowSize 15`, `DeflateMemLevel 9`. Защита при распаковке входящих тел (2.4.10+): `DeflateInflateLimitRequestBody` (по умолчанию действует `LimitRequestBody`), `DeflateInflateRatioLimit 200`, `DeflateInflateRatioBurst 3` [Apache-док].
- `DeflateAlterETag` (2.4.58+): `AddSuffix` (умолчание) делает ETag сжатого ответа отличным от несжатого, но мешает ответам `304 Not Modified` на условные запросы к сжатому содержимому. Альтернативы — `NoChange` или `Remove` [Apache-док].
- **Сжимать в одном звене.** При nginx перед Apache или цепочке Apache → Apache выберите одно место (`../1c/05-…`, разд. 12.4) [практика]. Повторно ответ бэкенда с уже выставленным `Content-Encoding` (кроме `identity`) Apache не сжимает — уточнено 20.10.2026 по коду `mod_deflate.c` и `mod_brotli.c` 2.4.69 («Not compressing (content-encoding already …)») [Apache-код].
- Учёт степени сжатия в журнале: `DeflateFilterNote Ratio ratio` и `%{ratio}n` в `LogFormat` [Apache-док].

```bash
curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip' https://netbox.example.local/api/status/ | grep -iE 'content-encoding|vary'
```

### 6.2. `mod_brotli`

- С 2.4.26; модуль `mod_brotli.so` есть в `apache2-bin` всех трёх выпусков, но не включён [Apache-док, Ubuntu]. Фильтр — `BROTLI_COMPRESS`; запрет для запроса — переменная `no-brotli`; `BrotliCompressionQuality 5` (0–11), `BrotliCompressionWindow 18`, `BrotliAlterETag AddSuffix` [Apache-док].
- В одной `AddOutputFilterByType` можно перечислить несколько фильтров через `;` [Apache-док, mod_filter]. Как работает пара `BROTLI_COMPRESS` + `DEFLATE` (уточнено 20.10.2026 по коду 2.4.69 `mod_filter.c`, `util_filter.c`, `mod_brotli.c`, `mod_deflate.c`) [Apache-код]:
  - каждый фильтр сжимает, только если клиент принимает его кодировку, и пропускает ответ, у которого уже есть `Content-Encoding`. Поэтому сработает тот, кто стоит в цепочке **первым**;
  - место в цепочке определяется **первой** регистрацией фильтра. В Ubuntu `DEFLATE` уже зарегистрирован в `mods-enabled/deflate.conf`, а `conf-enabled/` читается позже. Строка `BROTLI_COMPRESS;DEFLATE` в `conf-available/` поставит brotli **после** gzip: браузеры, которые присылают `Accept-Encoding: gzip, deflate, br`, получат gzip, а brotli достанется только клиентам без gzip;
  - чтобы brotli шёл первым, зарегистрируйте его раньше `deflate.conf` — в собственном `mods-available/brotli.conf`: `a2enmod brotli` включает такой файл вместе с модулем, а в `mods-enabled/` он стоит по алфавиту раньше `deflate.conf` [Ubuntu: `a2enmod`, `apache2.conf`; ⚠ на сервере не проверялось — смотрите проверку ниже].

```bash
sudo tee /etc/apache2/mods-available/brotli.conf >/dev/null <<'EOF'
AddOutputFilterByType BROTLI_COMPRESS;DEFLATE text/html text/plain text/css text/javascript application/javascript application/json application/xml
EOF
sudo a2enmod brotli            # если модуль уже был включён, повторный вызов подключит brotli.conf
sudo apache2ctl configtest && sudo systemctl reload apache2
curl -s -o /dev/null -D - -H 'Accept-Encoding: br'                https://grafana.example.local/ | grep -i content-encoding   # br
curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip'              https://grafana.example.local/ | grep -i content-encoding   # gzip
curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip, deflate, br' https://grafana.example.local/ | grep -i content-encoding   # br (как браузер)
```

### 6.3. `mod_expires` — заголовки срока жизни

- `ExpiresActive` по умолчанию `Off`. Задаёт `Expires` и `max-age` в `Cache-Control` по `ExpiresByType`/`ExpiresDefault`, синтаксис `"access plus 1 month"` или `"modification plus 5 hours"` [Apache-док].
- **Не трогает ответы, в которых `Expires` уже есть** (CGI, ответ бэкенда через прокси). Базовое время `modification` для содержимого не из файла не работает [Apache-док].
- Где пригодно: статика, которую Apache отдаёт сам, — например каталог `/static` NetBox через `Alias` (`../netbox/02-…`) [практика].
- **Публикация 1С:** веб-клиент сам управляет кешированием своих ресурсов. Не задавайте `ExpiresDefault` глобально; если глобальное правило есть, отключите его для путей публикаций (`<Location "/demo"> ExpiresActive Off </Location>`) [практика ⚠ — поведение веб-клиента 1С с внешними заголовками кеширования официально не описано].

### 6.4. `mod_cache` — осторожно

- В режиме по умолчанию (`CacheQuickHandler on`) кеш отвечает до этапов аутентификации и авторизации. Ресурс, закешированный однажды, отдаётся **любому** клиенту, в том числе тому, кого не пустило бы `Require ip`. Документация прямо требует не кешировать содержимое с ограничением доступа по адресу (`CacheDisable` или `mod_expires`) [Apache-док]. При `CacheQuickHandler off` выполняются все этапы обработки и модель безопасности сохраняется [Apache-док].
- Запросы с заголовком `Authorization` в режиме quick handler не кешируются и из кеша не отдаются [Apache-док]. Но приложения на cookie-сеансах (Redmine, NetBox, GlitchTip, Grafana, веб-клиент 1С) этим не защищены [практика].
- Ответы с `Cache-Control: private` и `no-store` по умолчанию не сохраняются (`CacheStorePrivate Off`, `CacheStoreNoStore Off`) [Apache-док].
- В Ubuntu: `cache_disk.conf` задаёт `CacheRoot /var/cache/apache2/mod_cache_disk`, `CacheDirLevels 2`, `CacheDirLength 1`, а `CacheEnable` закомментирован [Ubuntu]. Очистку диска выполняет `htcacheclean` (настройки — `/etc/default/apache-htcacheclean`), который запускается при включённом `mod_cache_disk` [Debian].
- **Вывод:** под публикацией 1С и под сервисами с авторизацией `mod_cache` не включать. Ускорение статики решают `mod_expires` и сжатие [практика].

---

## 7. Обратный прокси: `mod_proxy` и `mod_proxy_http`

### 7.1. Модули и базовые правила

```bash
sudo a2enmod proxy proxy_http headers      # proxy_http.load: «# Depends: proxy» — зависимость включится сама
sudo a2enmod remoteip                      # на бэкенде, где нужен реальный IP клиента
apache2ctl -M | grep -E 'proxy|headers|remoteip'
```

- **Обратный прокси включает `ProxyPass` (или `RewriteRule … [P]`); `ProxyRequests On` для этого не нужен.** `ProxyRequests On` превращает сервер в прямой (forward) прокси, который без ограничения доступа опасен «для вашей сети и Интернета в целом» [Apache-док]. Умолчание — `Off`; в Ubuntu `proxy.conf` состоит только из комментариев [Ubuntu]. Проверка: `grep -Rni 'ProxyRequests' /etc/apache2/` — не должно быть `On`.
- **Синтаксис:** `ProxyPass [путь] !|url [ключ=значение …] [nocanon] [interpolate] [noquery]`. Внутри `<Location>` путь опускается; в `<Directory>`, `<If>`, `<Files>` директива не поддерживается [Apache-док].
- **Слэши:** если путь заканчивается на `/`, URL тоже должен заканчиваться на `/`, и наоборот, иначе в запросах к бэкенду потеряются слэши [Apache-док].
- **Порядок:** правила `ProxyPass`/`ProxyPassMatch` проверяются в порядке записи, первое совпадение выигрывает. Длинные пути пишите раньше, исключения (`ProxyPass "/путь" "!"`) — раньше общих правил. Смешивать правила в контексте сервера и в `<Location>` нельзя: правило из `<Location>` вычисляется первым [Apache-док].
- **`ProxyPassReverse`** переписывает только заголовки `Location`, `Content-Location` и `URI` в ответах-перенаправлениях. Абсолютные ссылки внутри HTML он не трогает (для этого — `mod_proxy_html`) [Apache-док]. Отсюда правило: публикуйте приложение по тому же пути, по которому оно работает на бэкенде [практика].
- **`ProxyPassReverseCookieDomain` / `ProxyPassReverseCookiePath`** переписывают домен и путь в `Set-Cookie`, если внешний путь отличается от внутреннего [Apache-док].

### 7.2. Workers и пул соединений

- Параметры связи с бэкендом хранятся в объекте **worker**. Два встроенных worker (прямой и обратный по умолчанию) не используют keep-alive и открывают TCP-соединение на каждый запрос. Явный worker создаётся `ProxyPass`/`ProxyPassMatch`/`ProxySet` и идентифицируется URL бэкенда [Apache-док].
- **Worker sharing:** если URL одного worker — начальная подстрока URL другого, объявленного позже, второй не создаётся. Используется первый, а параметры второго игнорируются с предупреждением при запуске. Пример из документации: `ProxyPass "/apps" "http://backend/" timeout=60` и `ProxyPass "/examples" "http://backend/examples" timeout=10` — для `/examples` будет 60 [Apache-док].
- **`ProxyPassMatch` с подстановками (`$1`)** создаёт новый URL на каждый запрос и уходит на worker по умолчанию: без пула, без кеша DNS. Лечится отдельным `ProxyPass` на тот же бэкенд (явный worker), а с 2.4.47 — явным `enablereuse=on` [Apache-док].
- **Пул — на процесс:** по умолчанию до `ThreadsPerChild` соединений на каждый дочерний процесс (в `prefork` — 1). Параметр `max` между процессами не согласуется [Apache-док].
- **DNS бэкенда** при переиспользовании соединений разрешается один раз на процесс и кешируется до его перезапуска. С 2.4.59 срок задаёт `addressttl` (−1 — до перезапуска) [Apache-док]. При смене IP бэкенда на 22.04/24.04 нужен `reload` [практика].

### 7.3. Параметры `ProxyPass` (worker) [Apache-док]

| Параметр | Умолчание | Когда менять |
|---|---|---|
| `connectiontimeout` | `timeout` | Короткий (`5`) — быстро понять, что бэкенд недоступен; допускается суффикс `ms` |
| `timeout` | `ProxyTimeout` (→ `Timeout`) | Ожидание данных от бэкенда и отправки к нему; для 1С — не меньше самого долгого вызова |
| `retry` | 60 | Сколько секунд не слать запросы на worker в состоянии ошибки; 0 — пробовать всегда |
| `keepalive` | Off | `On` — TCP keep-alive на простаивающих соединениях, если межсетевой экран между Apache и бэкендом рвёт неактивные соединения (частота проб задаётся ОС, может быть до 2 ч) |
| `disablereuse` / `enablereuse` | Off / On | `disablereuse=On` — без пула, если экран молча рвёт соединения или бэкенд за round-robin DNS |
| `ttl` | — | Закрывать неиспользуемые соединения раньше таймаута keep-alive бэкенда: лечит гонку «бэкенд закрыл, прокси отправил» |
| `max` / `min` / `smax` / `acquire` | число потоков процесса / 0 / `max` / — | Ограничить пул; `acquire` — сколько мс ждать свободного соединения, иначе `SERVER_BUSY` |
| `ping` | 0 | Для HTTP/1.1-бэкенда — проверка через `100-Continue` перед пересылкой; секунды (или `ms`) |
| `flushpackets` / `flushwait` | off / 10 | **Действует только для `mod_proxy_ajp` и `mod_proxy_fcgi`** — на HTTP-бэкенды не влияет |
| `iobuffersize` | 8192 | Почти никогда не нужно |
| `responsefieldsize` (2.4.34+) | 8192 | Бэкенд отдаёт заголовок ответа длиннее 8 КБ (большие cookie, длинный `Location`) |
| `upgrade` | — | `websocket` — туннелировать WebSocket (разд. 10) |
| `mapping` | — | `encoded`/`servlet` — как нормализовать путь перед сравнением с `<Location>` |
| `addressttl` (2.4.59+) | −1 | Срок кеша DNS бэкенда в секундах |
| `status`, `route`, `redirect`, `lbset`, `loadfactor` | — | Для членов балансировщика (разд. 11) |

Ключевые слова после параметров: `nocanon` — передать путь «сырым», без канонизации (документация предупреждает о снижении защиты бэкенда); `noquery`; `interpolate` (вместе с `ProxyPassInterpolateEnv On`) [Apache-док].

### 7.4. Заголовки к бэкенду

| Заголовок | Кто ставит | Замечание |
|---|---|---|
| `X-Forwarded-For` | `mod_proxy_http` автоматически | Дописывается к уже пришедшему значению через запятую; адресов может быть несколько [Apache-док] |
| `X-Forwarded-Host` | автоматически | Исходный `Host` клиента [Apache-док] |
| `X-Forwarded-Server` | автоматически | Имя прокси [Apache-док] |
| `X-Forwarded-Proto` | **вручную**: `RequestHeader set X-Forwarded-Proto "https"` или `expr=%{REQUEST_SCHEME}` | Без него Redmine строит ссылки `http://` за HTTPS-прокси [сторонний: `../redmine/02-…`]; NetBox считает запрос защищённым по `X-Forwarded-Proto: https` [сторонний: `../netbox/01-…`]; 1С требует для «восстановления» исходного запроса [ИТС-адм разд. 8.10.3] |
| `X-Forwarded-Port` | **вручную**: `RequestHeader set X-Forwarded-Port "443"` или `expr=%{SERVER_PORT}` | Требуется 1С [ИТС-адм разд. 8.10.3] |
| `Host` | `ProxyPreserveHost On` — исходный; `Off` (умолчание) — имя из URL `ProxyPass` | Документация называет `On` редким случаем [Apache-док], но Redmine, NetBox, GlitchTip и Grafana в своих примерах для Apache ставят `On` [сторонний] — делайте так же |
| `Via` | `ProxyVia` (`Off` по умолчанию: заголовок пропускается без изменений) | `Full` добавляет версию сервера — не включать [Apache-док, практика] |

- `ProxyAddHeaders Off` отключает `X-Forwarded-*`. Умолчание — `On` (2.3.10+), действует только для `mod_proxy_http` [Apache-док].
- `RequestHeader` срабатывает в фазе fixup, непосредственно перед обработчиком. Режим `early` документация называет средством отладки — «в рабочем сервере всегда используйте поздний режим» [Apache-док].
- Переменные выражений `REQUEST_SCHEME`, `SERVER_PORT`, `HTTPS` («on»/«off»), `REMOTE_ADDR`, `CONN_REMOTE_ADDR` описаны в документации `ap_expr` [Apache-док].
- **Подделка `X-Forwarded-For` клиентом.** Прокси дописывает адрес к значению, пришедшему от клиента. Бэкенд должен доверять только правой части цепочки от известных прокси — это и делает `mod_remoteip` (разд. 7.5) [Apache-док].

### 7.5. `mod_remoteip` на бэкенде

- Заменяет адрес клиента на адрес из заголовка (`RemoteIPHeader`). Новый адрес используют `Require ip`, `mod_status`, `%a`/`%h` в журналах. Исходный адрес соединения остаётся доступен как `%{c}a` и `CONN_REMOTE_ADDR` [Apache-док].
- Список адресов разбирается **справа налево** и останавливается на первом недоверенном [Apache-док].
- **Частные адреса** (10/8, 172.16/12, 192.168/16, 169.254/16, 127/8) учитываются, только если прокси перечислены в `RemoteIPInternalProxy`. `RemoteIPTrustedProxy` частные адреса из заголовка за адрес клиента **не** принимает [Apache-док]. Во внутренней сети нужен именно `RemoteIPInternalProxy`.
- Без `RemoteIPInternalProxy`/`RemoteIPTrustedProxy` модуль доверяет заголовку от **любого** хоста — так оставлять нельзя [Apache-док].
- `RemoteIPProxiesHeader` — записать цепочку доверенных прокси в отдельный заголовок; `%{remoteip-proxy-ip-list}n` — в журнал [Apache-док].
- PROXY protocol (2.4.31+): `RemoteIPProxyProtocol On` для балансировщика уровня TCP (HAProxy и т. п.). Включение действует на всю пару IP:порт [Apache-док].
- Журналы: с 2.4.39 `%h` в формате `combined` Ubuntu тоже показывает адрес из `mod_remoteip`, а `%{c}h` — адрес соединения [Apache-док]. Комментарий в `apache2.conf` Ubuntu: вместо `%{X-Forwarded-For}i` используйте `mod_remoteip` [Ubuntu].

```apache
# /etc/apache2/conf-available/remoteip.conf  (бэкенд: srv-1c-app; rp-1c = 10.10.0.20)
RemoteIPHeader        X-Forwarded-For
RemoteIPInternalProxy 10.10.0.20
```

```bash
sudo a2enmod remoteip && sudo a2enconf remoteip
sudo apache2ctl configtest && sudo systemctl reload apache2
sudo tail -n 3 /var/log/apache2/access.log     # первым полем — адрес клиента, а не 10.10.0.20
```

Для 1С: платформа читает `X-Forwarded-For` сама, чтобы определить IP внешнего клиента [ИТС-адм разд. 8.10.3]. `mod_remoteip` нужен для журналов и `Require ip` самого Apache. Видит ли модуль `wsap24` адрес, подменённый `mod_remoteip`, — ⚠ не подтверждено.

### 7.6. Ошибки прокси и что они значат

| Код ответа клиенту | Строка в `error.log` (2.4.69) | Причина | Что делать |
|---|---|---|---|
| 503 | `AH00957: …: attempt to connect to 127.0.0.1:8080 (…) failed`, `AH00959: ap_proxy_connect_backend disabling worker for (…) for 60s`, `AH01114: HTTP: failed to make connection to backend` | бэкенд не слушает порт (контейнер остановлен, служба упала) | `ss -ltnp \| grep 8080`, `docker ps`, `systemctl status …` |
| 503 сразу, без попытки | `AH00940: …: disabled connection for (…)` (уровень error); на уровне debug перед ним `AH00933: …: too soon to retry worker for (…)` | worker в состоянии ошибки, ждёт `retry` (60 с) | поднять бэкенд; при плановых работах — `retry=5` или флаги балансировщика |
| 502 «Proxy Error» через `timeout` секунд | `AH01102: error reading status line from remote server …`, `AH00898: Error reading from remote server returned by /путь`; на уровне debug `AH01103: read timeout` | бэкенд не ответил за `timeout`/`ProxyTimeout` | увеличить `timeout=` у `ProxyPass`; искать медленный запрос у приложения |
| 502 | `AH01102 …` без таймаута, `Error reading from remote server`, `Corrupt status line returned by remote server` | бэкенд закрыл соединение или ответил не по HTTP | `ttl=` меньше keep-alive-таймаута бэкенда; переменная `proxy-initial-not-pooled`; проверить, что схема `http://`/`https://` совпадает с бэкендом |
| 502, а при таймауте отправки — 504 | `AH01097`/`AH01084: pass request body failed …` | обрыв или таймаут при передаче тела запроса бэкенду | `LimitRequestBody` и таймауты бэкенда, сеть |
| 413 | — | превышен `LimitRequestBody` на прокси | разд. 5 |

Коды строк — [Apache-док, код 2.4.69]. Уточнено 20.10.2026 по коду `mod_proxy_http.c` (2.4.52, 2.4.58, 2.4.69) и `proxy_util.c` 2.4.69: если бэкенд не прислал строку статуса за `timeout`, `mod_proxy_http` отвечает **502** (`ap_proxyerror(r, HTTP_BAD_GATEWAY, "Error reading from remote server")`), а не 504, — в отличие от nginx. Код **504** Apache возвращает при таймауте отправки тела запроса бэкенду (`APR_STATUS_IS_TIMEUP → HTTP_GATEWAY_TIME_OUT` в `proxy_util.c`) [Apache-код]. Детали в журнале включаются точечно: `LogLevel warn proxy:info proxy_http:info`, а при разборе — `proxy:debug` на время [Apache-док].

Переменные окружения `mod_proxy_http` для капризных бэкендов (`SetEnv` в `<Location>`) [Apache-док]:

- `proxy-nokeepalive` — закрывать соединение с бэкендом после каждого запроса;
- `force-proxy-request-1.0` — говорить с бэкендом по HTTP/1.0 (подразумевает `proxy-sendcl`);
- `proxy-sendcl` — всегда отправлять `Content-Length` (тело может буферизоваться целиком — дорого для больших загрузок);
- `proxy-sendchunked` — передавать тело потоком chunked (бэкенд должен поддерживать HTTP/1.1);
- `proxy-initial-not-pooled` — для первого запроса на клиентском соединении не брать соединение из пула. Устраняет «error reading status line» из-за гонки с закрытием соединения бэкендом ценой производительности.

`no-proxy` (2.4.26+, ставить через `SetEnvIf`) исключает запрос из обработки `mod_proxy` — единственный способ исключения для `ProxyPass` внутри `<Location>` [Apache-док].

### 7.7. Своя страница ошибки и защитные мелочи

- `ProxyErrorOverride On [коды…]` показывает собственные страницы ошибок Apache вместо страниц бэкенда (с 2.4.47 — только для перечисленных кодов) [Apache-док]. **Не включайте для API и HTTP-сервисов 1С:** клиент интеграции ждёт тело ошибки от приложения [практика].
- `ProxyBadHeader IsError` (умолчание) — неверная строка заголовка ответа даёт 502 [Apache-док].
- `ProxyVia Off`, `ProxyRequests Off` — оставить умолчания [Apache-док].
- Для TLS к бэкенду (`https://` в `ProxyPass`) нужен `SSLProxyEngine On` и проверка сертификата бэкенда (`SSLProxyVerify` и др.) — `apache/02-…`.
- Unix-сокет бэкенда (2.4.7+): `ProxyPass "/" "unix:/run/app.sock|http://localhost/"` [Apache-док].

---

## 8. Прокси перед сервисами: Redmine, NetBox, GlitchTip, Grafana, Loki

Общий шаблон для `srv-itsm` и `srv-obs`: один виртуальный хост на сервис, TLS на Apache (сертификаты и настройки TLS — `apache/02-…`), бэкенд слушает только `127.0.0.1`. Docker публикует порты в обход `ufw` [сторонний: `../guides/09-…`], поэтому `127.0.0.1:` в `ports:` обязателен.

```apache
# Шаблон: /etc/apache2/sites-available/<сервис>.conf
<VirtualHost *:443>
    ServerName  svc.example.local
    # --- TLS: SSLEngine on, сертификаты — см. apache/02-https-bezopasnost-autentifikaciya.md
    ProxyRequests     Off
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port  "443"
    ProxyPass        "/" "http://127.0.0.1:PORT/" connectiontimeout=5 timeout=120
    ProxyPassReverse "/" "http://127.0.0.1:PORT/"
    ErrorLog  ${APACHE_LOG_DIR}/svc_error.log
    CustomLog ${APACHE_LOG_DIR}/svc_access.log perf
</VirtualHost>
<VirtualHost *:80>
    ServerName svc.example.local
    Redirect permanent / https://svc.example.local/
</VirtualHost>
```

Формат `perf` описан в разд. 12.3. Порядок включения:

```bash
sudo a2enmod proxy proxy_http headers ssl
sudo a2ensite svc
sudo apache2ctl configtest && sudo systemctl reload apache2
sudo apache2ctl -S | grep svc.example.local
curl -sI https://svc.example.local/ | head -n 5
```

### 8.1. Redmine (`srv-itsm`)

| Что | Значение |
|---|---|
| Бэкенд | Docker `redmine:7.0.2-trixie`, `ports: ["127.0.0.1:8080:3000"]` (стенд — `8080:3000`, `../redmine/06-…`); без Docker — Puma `127.0.0.1:3000` (`../redmine/02-…`, разд. 12–13) |
| Обязательно | `ProxyPreserveHost On`, `RequestHeader set X-Forwarded-Proto "https"`, иначе ссылки с `http://` [сторонний: `../redmine/02-…`] |
| В самом Redmine | «Администрирование → Настройки → Общие»: «Имя компьютера» `redmine.example.local`, «Протокол» `https`; `autologin_cookie_secure: true` (`../redmine/02-…`, разд. 13; `../redmine/05-…`) |
| `LimitRequestBody` | не меньше предела вложений Redmine в настройках («Максимальный размер вложения», `../redmine/04-…`) — иначе `413` от Apache раньше, чем Redmine покажет понятную ошибку |
| Таймаут | `timeout=120` хватает для веб-интерфейса; массовые выгрузки и REST-импорт — по факту [практика] |

### 8.2. NetBox (`srv-itsm`)

| Что | Значение |
|---|---|
| Бэкенд | Docker netbox-docker `ports: ["127.0.0.1:8090:8080"]` (`../netbox/05-…`) или gunicorn `127.0.0.1:8001` при установке без Docker (`../netbox/02-…`) |
| Обязательно | `ProxyPreserveHost On`, `RequestHeader set "X-Forwarded-Proto" expr=%{REQUEST_SCHEME}` — так в образце `contrib/apache.conf` NetBox [сторонний: `../netbox/02-…`]; в `ALLOWED_HOSTS` — внешнее имя; при `CSRF verification failed` — `CSRF_TRUSTED_ORIGINS` (`../netbox/02-…`, `../netbox/05-…`) |
| Статика без Docker | `Alias /static /opt/netbox/netbox/static` и исключение `ProxyPass /static !` **раньше** `ProxyPass /` (порядок, разд. 7.1); здесь уместен `mod_expires` (разд. 6.3) |
| Сжатие | ответы API — JSON: добавьте `application/json` в `AddOutputFilterByType` (разд. 6.1) |
| `LimitRequestBody` | у nginx-образца NetBox `client_max_body_size 25m` [сторонний: `../netbox/02-…`]; в Apache аналог — `LimitRequestBody 26214400` [практика] |

### 8.3. GlitchTip (`srv-obs`)

| Что | Значение |
|---|---|
| Бэкенд | Docker, веб-процесс на `8000` (`../observability/02-glitchtip.md`) |
| Пример Apache из базы | `ProxyPreserveHost On`, `ProxyPass / http://localhost:8000/`, `ProxyPassReverse …`, `RequestHeader set "X-Forwarded-Proto" expr=%{REQUEST_SCHEME}`, `RequestHeader set "X-Forwarded-SSL" expr=%{HTTPS}` [сторонний: `../observability/02-…`] |
| В GlitchTip | `GLITCHTIP_DOMAIN=https://glitchtip.example.local` (со схемой), `CSRF_TRUSTED_ORIGINS=https://glitchtip.example.local` [сторонний: `../observability/02-…`, `../guides/09-…`] |
| Приём событий | SDK и код BSL шлют события на `…/api/<id>/store/` или `envelope`. Это POST с телом; `LimitRequestBody` по умолчанию (1 ГиБ) не мешает. Слишком большие события ограничивает сам GlitchTip ⚠ |
| Журнал | события от 1С идут потоком: исключите их из основного журнала или пишите в отдельный (разд. 12.4), чтобы не раздувать `access.log` [практика] |

### 8.4. Grafana (`srv-obs`)

- Официальный пример для Apache: `a2enmod proxy proxy_http`, затем `ProxyPreserveHost on`, `ProxyPass / http://grafana:3000`, `ProxyPassReverse / http://grafana:3000`. Для подкаталога строки с подкаталогом пишутся раньше строк с `/` [сторонний: Grafana, «Run Grafana behind a reverse proxy»].
- В Grafana — `root_url` (и `domain`) под внешний адрес; при TLS на прокси `protocol = http` [сторонний: там же].
- **Grafana Live использует WebSocket по `/api/live/`** [сторонний: «Set up Grafana Live»]. В Apache — `upgrade=websocket` (разд. 10).

```apache
<VirtualHost *:443>
    ServerName grafana.example.local
    # TLS — apache/02-…
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    ProxyPass        "/api/live/" "http://127.0.0.1:3000/api/live/" upgrade=websocket timeout=3600
    ProxyPassReverse "/api/live/" "http://127.0.0.1:3000/api/live/"
    ProxyPass        "/"          "http://127.0.0.1:3000/" connectiontimeout=5 timeout=300
    ProxyPassReverse "/"          "http://127.0.0.1:3000/"
</VirtualHost>
```

Здесь `/api/live/` и `/` — разные URL бэкенда (`…:3000/api/live/` и `…:3000/`). Второй — префикс первого, но объявлен **позже**, поэтому worker sharing не возникает и у каждого свои параметры (разд. 7.2) [Apache-док]. Если поменять строки местами, `/api/live/` получит параметры `/`. На 22.04 (2.4.52) простаивающий туннель живёт по **меньшему** из `Timeout` и `timeout=`, то есть 300 с при `Timeout` Ubuntu, несмотря на `timeout=3600` (разд. 10).

### 8.5. Loki (`srv-obs`) — приём журналов из 1С

- У Loki нет своей аутентификации; в рабочем контуре рекомендованы прокси с TLS и базовой аутентификацией или правило в `DOCKER-USER` [сторонний: `../guides/09-…`, `../observability/03-…`].
- Push API — `POST /loki/api/v1/push`, ответ `204` [сторонний: `../observability/03-…`].

```apache
<VirtualHost *:443>
    ServerName loki.example.local
    # TLS — apache/02-…
    <Location "/loki/api/v1/push">
        AuthType Basic
        AuthName "loki push"
        AuthUserFile /etc/apache2/loki.htpasswd
        <RequireAll>
            Require valid-user
            Require ip 10.10.0.0/24
        </RequireAll>
        ProxyPass        "http://127.0.0.1:3100/loki/api/v1/push" connectiontimeout=5 timeout=30
        ProxyPassReverse "http://127.0.0.1:3100/loki/api/v1/push"
    </Location>
    # остальные пути Loki наружу не публикуем; Grafana ходит к Loki по сети Docker
</VirtualHost>
```

`htpasswd` и аутентификация подробно описаны в `apache/02-…`. Тело push-запроса ограничивает и сам Loki (`max_recv_msg_size`, ответ `413` [сторонний: `../observability/03-…`]). Пачки из 1С держите заметно меньше этого предела [практика].

---

## 9. Прокси перед публикацией 1С на другом сервере

Схема: клиенты → `rp-1c` (Apache, TLS) → `srv-1c-app` (Apache + `wsap24`, HTTP во внутренней сети). Сама публикация и `default.vrd` — `../1c/05-…`. Схема с nginx вместо Apache — `../1c/05-…`, разд. 9.

### 9.1. Что требует 1С

- Обратный прокси должен формировать заголовки `X-Forwarded-Port`, `X-Forwarded-Host`, `X-Forwarded-Proto` («восстановление» исходного запроса) и `X-Forwarded-For` (IP внешнего клиента). Без них часть механизмов может не работать; подробности настройки 1С отсылает к документации веб-сервера [ИТС-адм разд. 8.10.3].
- Методичка по nginx перед публикациями передаёт `Host`, `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Proto https` [ИТС-мет 5980, 2020]. Эталон `docker_fresh` — `Host`, `X-Forwarded-Proto` и `X-Forwarded-Port` (`../1c/05-…`, разд. 9.1).
- Перевод на Apache: `ProxyPreserveHost On` (исходный `Host`), `X-Forwarded-For` и `X-Forwarded-Host` добавит `mod_proxy_http`, `X-Forwarded-Proto` и `X-Forwarded-Port` — через `RequestHeader` [Apache-док].

### 9.2. Конфигурация `rp-1c`

```apache
# /etc/apache2/sites-available/1c.conf на rp-1c
<VirtualHost *:443>
    ServerName 1c.example.local
    # --- TLS: apache/02-https-bezopasnost-autentifikaciya.md
    ProxyRequests     Off
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port  "443"

    # Публикация demo: путь на прокси = путь на бэкенде (ссылки веб-клиента абсолютные)
    ProxyPass        "/demo" "http://srv-1c-app.example.local/demo" connectiontimeout=5 timeout=3600 keepalive=On
    ProxyPassReverse "/demo" "http://srv-1c-app.example.local/demo"

    # Сверх 1 ГиБ — только если в базе действительно грузят такие файлы
    <Location "/demo">
        LimitRequestBody 0
    </Location>

    ErrorLog  ${APACHE_LOG_DIR}/1c_error.log
    CustomLog ${APACHE_LOG_DIR}/1c_access.log perf
</VirtualHost>
<VirtualHost *:80>
    ServerName 1c.example.local
    Redirect permanent / https://1c.example.local/
</VirtualHost>
```

Пояснения:

- `"/demo"` без завершающих слэшей с обеих сторон — правило слэшей [Apache-док]; перенаправление на языковой путь сформирует модуль 1С [практика]. **Путь не переименовывать** (`/buh` → `/demo`): `ProxyPassReverse` правит только заголовки перенаправлений, адреса в ответах веб-клиента останутся внутренними [Apache-док, практика ⚠].
- `timeout=3600` — под самые долгие синхронные вызовы сервисов. Держит ли веб-клиент HTTP-запрос открытым всё время серверного вызова, официально не описано (`../1c/05-…`, «Что не удалось подтвердить», п. 5), поэтому таймаут — с запасом [практика]. `keepalive=On` — если межсетевой экран между прокси и бэкендом рвёт простаивающие соединения [Apache-док].
- Бэкенду придёт `Host: 1c.example.local`. Публикации из `apache2.conf` (контекст сервера) обслуживаются для любого имени; если они внутри именованного `VirtualHost` — добавьте `ServerAlias` [практика]. На `srv-1c-app` — `mod_remoteip` с `RemoteIPInternalProxy <IP rp-1c>` (разд. 7.5). Сжатие — в одном звене, кеширования нет (разд. 6).

### 9.3. Проверка

```bash
# с rp-1c: бэкенд отвечает напрямую
curl -s -o /dev/null -w '%{http_code}\n' http://srv-1c-app.example.local/demo/
# с рабочего места: через прокси, смотреть перенаправление и схему в Location
curl -s -o /dev/null -D - https://1c.example.local/demo/ | grep -iE '^HTTP|^location'
# заголовки, которые получил бэкенд: временный журнал на srv-1c-app
#   LogFormat "%a %{X-Forwarded-For}i %{X-Forwarded-Host}i %{X-Forwarded-Proto}i %{X-Forwarded-Port}i \"%r\"" xfwd
#   CustomLog ${APACHE_LOG_DIR}/xfwd.log xfwd
sudo tail -n 5 /var/log/apache2/xfwd.log
```

`Location` с `http://` или с внутренним именем означает, что не дошли `X-Forwarded-Proto`/`Port` или `Host` (ср. `../1c/05-…`, типовые ошибки, п. 23). Временный журнал после проверки удалите.

### 9.4. Несколько веб-серверов 1С за одним прокси

Балансировщик описан в разд. 11. Для 1С важно:

- **Привязка сеанса.** Официального требования привязки к веб-серверу не найдено (`../1c/05-…`, «Что не удалось подтвердить», п. 4). Эталон 1С для nginx использует `ip_hash`, в Apache аналог — cookie-привязка `ROUTEID` [Apache-док, практика]. С 8.5.4 закреплением запросов сеанса за рабочим процессом занимается кластер (`../1c/05-…`, раздел о 8.5.4).
- **Метод:** `bybusyness` равномернее раскладывает долгие вызовы, чем `byrequests` [Apache-док: описание методов; выбор — практика].
- **Проверки здоровья.** Не направляйте `hcmethod=GET`/`HEAD` на HTTP-сервис 1С: каждая проверка без повторного использования сеансов создаёт сеанс 1С (`../1c/05-…`, разд. 12.5) [практика]. Безопаснее `hcmethod=TCP` или статический файл, который отдаёт сам Apache бэкенда, например `/healthz.txt` из `DocumentRoot`.

---

## 10. WebSocket

- **С 2.4.47** Upgrade проходит «из конца в конец» через `mod_proxy_http`: `ProxyPass "/путь/" "http://бэкенд/путь/" upgrade=websocket`. Туннель включается, только если бэкенд ответил `101 Switching Protocols`, иначе — обычный HTTP [Apache-док]. Доступно во всех выпусках Ubuntu (≥ 2.4.52) [Ubuntu].
- **`mod_proxy_wstunnel` устарел** — нужен для 2.4.46 и старше или при `ProxyWebsocketFallbackToProxyHttp Off` (2.4.48+, по умолчанию `On`); рецепты с `RewriteCond %{HTTP:Upgrade}` и `[P]` на `ws://` при 2.4.47+ не нужны; `upgrade=NONE`/`ANY` — только для отладки [Apache-док].
- **Таймаут туннеля** (уточнено 20.10.2026 по `CHANGES_2.4` и коду `proxy_util.c` 2.4.52, 2.4.58, 2.4.69): с 2.4.53 Apache берёт **большее** из таймаутов клиентского соединения (`Timeout`) и соединения с бэкендом (`timeout=`), а в 2.4.52 — **меньшее** (запись CHANGES 2.4.53 «Use the maximum of front end and backend timeouts instead of the minimum when tunneling requests»; в пакет 22.04 это изменение не перенесено — среди патчей ветки `ubuntu/jammy-updates` его нет). Фильтр `reqtimeout` для туннеля снимается, а оба соединения после туннеля не переиспользуются [Apache-док, код]. Простаивающий WebSocket дольше этого срока будет закрыт; клиенты Grafana Live переподключаются сами [практика ⚠]. Для длинных простоев на 24.04/26.04 задайте `timeout=3600` на правиле WebSocket (пример — разд. 8.4); на 22.04 этого мало — нужно поднять ещё и `Timeout` в этом виртуальном хосте (директива допустима в `<VirtualHost>`), иначе туннель закроется через 300 с.
- **HTTP/2:** WebSocket поверх HTTP/2 (RFC 8441) — директива `H2WebSockets on|off` с 2.4.58, по умолчанию выключена; конфигурации с `upgrade=websocket` должны работать без изменений [Apache-док, CHANGES 2.4.58].
- **1С:** используются ли входящие WebSocket через публикацию, не подтверждено; эталон 1С заголовки `Upgrade` не проксирует (`../1c/05-…`, «Что не удалось подтвердить», п. 6). Добавлять `upgrade=websocket` на путь публикации без необходимости не нужно [практика].

Проверка туннеля:

```bash
curl -s -o /dev/null -w '%{http_code}\n' --http1.1 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  https://grafana.example.local/api/live/ws        # 101 — туннель поднялся (без сеанса Grafana возможен 401)
```

---

## 11. Балансировка: `mod_proxy_balancer`

### 11.1. Модули

```bash
sudo a2enmod proxy_balancer lbmethod_byrequests lbmethod_bybusyness headers
# proxy_balancer.load: «# Depends: proxy alias slotmem_shm»; lbmethod_*.load: «# Depends: proxy_balancer»
apache2ctl -M | grep -E 'balancer|lbmethod|slotmem'
```

Зависимости из первой строки `.load` включаются автоматически [Ubuntu]. Без хотя бы одного `lbmethod_*` балансировщик работать не будет [Apache-док].

### 11.2. Методы [Apache-док]

| `lbmethod` | Модуль | Как распределяет |
|---|---|---|
| `byrequests` (умолчание) | `mod_lbmethod_byrequests` | по числу запросов с весами `loadfactor` (1.0–100.0) |
| `bybusyness` | `mod_lbmethod_bybusyness` | новый запрос — члену с наименьшим числом активных запросов; при равенстве — как `byrequests` |
| `bytraffic` | `mod_lbmethod_bytraffic` | по объёму переданных байт (вход и выход весят одинаково) |
| `heartbeat` | `mod_lbmethod_heartbeat` (Experimental) | по данным `mod_heartbeat`/`mod_heartmonitor` |

### 11.3. Пример: два веб-сервера 1С с привязкой

```apache
# rp-1c: /etc/apache2/sites-available/1c.conf (фрагмент)
Header add Set-Cookie "ROUTEID=.%{BALANCER_WORKER_ROUTE}e; path=/" env=BALANCER_ROUTE_CHANGED
<Proxy "balancer://web1c">
    BalancerMember "http://srv-1c-app.example.local"  route=app1 connectiontimeout=5 timeout=3600 retry=30
    BalancerMember "http://srv-1c-app2.example.local" route=app2 connectiontimeout=5 timeout=3600 retry=30
    ProxySet lbmethod=bybusyness stickysession=ROUTEID
</Proxy>
ProxyPass        "/demo" "balancer://web1c/demo"
ProxyPassReverse "/demo" "balancer://web1c/demo"
```

Схема с `Header add Set-Cookie … env=BALANCER_ROUTE_CHANGED` и `ProxySet stickysession=ROUTEID` взята из документации `mod_proxy_balancer`. Балансировщик экспортирует переменные `BALANCER_WORKER_ROUTE`, `BALANCER_ROUTE_CHANGED`, `BALANCER_WORKER_NAME`, `BALANCER_SESSION_STICKY`, `BALANCER_SESSION_ROUTE`, `BALANCER_NAME` [Apache-док]. Путь в `<Proxy balancer://…>` игнорируется. Завершающий слэш у `BalancerMember` обычно убирают [Apache-док]. Если cookie маршрута содержит точку, балансировщик берёт часть после точки — отсюда точка перед `%{BALANCER_WORKER_ROUTE}e` [Apache-док].

### 11.4. Параметры балансировщика и членов [Apache-док]

| Параметр | Умолчание | Смысл |
|---|---|---|
| `stickysession` | — | имя cookie или параметра URL с маршрутом; регистр имени cookie важен; форма `COOKIE\|param` |
| `nofailover` | Off | `On` — при недоступности «своего» члена сеанс рвётся, а не уходит на другой (если бэкенды не реплицируют сеансы) |
| `maxattempts` | число членов − 1 | попыток переключения |
| `timeout` (балансировщика) | 0 | сколько ждать свободного члена; у члена `timeout` — другое (сокет) |
| `failonstatus` | — | коды ответа, переводящие члена в ошибку (например, `503`) |
| `failontimeout` (2.4.5+) | Off | таймаут чтения после отправки запроса переводит члена в ошибку |
| `forcerecovery` (2.4.2+) | On | если в ошибке все члены — восстанавливать их немедленно, не дожидаясь `retry` |
| `lbset` | 0 | группа: сначала используются члены с меньшим номером |
| `status` | — | `+D` выключен, `+S` остановлен, `+I` игнорировать ошибки, `+R` горячий резерв (2.4.34+) — подменяет неработающего члена того же `lbset`, `+H` резерв, который включается, только когда никого не осталось, `+N` дренаж — только «свои» привязанные сеансы, `+E` ошибка, `C` — провал проверки `mod_proxy_hcheck` |
| `route`, `redirect` | — | маршрут члена; перенаправление запросов без сеанса на член с указанным `route` (плавный вывод узла) |
| `growth` / `BalancerGrowth` | 0 / 5 | сколько членов/балансировщиков можно добавить на лету |

### 11.5. Проверки здоровья: `mod_proxy_hcheck` (2.4.21+) [Apache-док]

- Требует `mod_watchdog`. В Ubuntu он вкомпилирован статически [Ubuntu, `debian/rules`]; включается `sudo a2enmod proxy_hcheck`.
- Параметры членов: `hcmethod` (`None` по умолчанию, `TCP`, `OPTIONS`, `HEAD`, `GET`, а с 2.4.55 — `OPTIONS11`, `HEAD11`, `GET11` по HTTP/1.1), `hcinterval 30`, `hcpasses 1`, `hcfails 1`, `hcuri`, `hcexpr`, `hctemplate`. Без `hcexpr` успехом считаются коды 2xx–3xx. Потоков проверок — `ProxyHCTPsize 16`.
- Члены, снятые проверкой, получают флаг `C` (виден и меняется в `balancer-manager`).

```apache
ProxyHCExpr ok23 {%{REQUEST_STATUS} =~ /^[23]/}
<Proxy "balancer://web1c">
    BalancerMember "http://srv-1c-app.example.local"  route=app1 hcmethod=GET hcuri=/healthz.txt hcexpr=ok23 hcinterval=10 hcfails=3 hcpasses=2
    BalancerMember "http://srv-1c-app2.example.local" route=app2 hcmethod=GET hcuri=/healthz.txt hcexpr=ok23 hcinterval=10 hcfails=3 hcpasses=2
    ProxySet lbmethod=bybusyness stickysession=ROUTEID
</Proxy>
```

`/healthz.txt` — статический файл в `DocumentRoot` бэкенда (`/var/www/html/healthz.txt`). Его отдаёт сам Apache, без модуля 1С и без сеанса 1С (разд. 9.4) [практика]. На 22.04 есть только `GET`/`HEAD`/`OPTIONS` по HTTP/1.0; варианты `*11` — с 2.4.55 [Apache-док].

### 11.6. `balancer-manager` — включать только закрытым

- Позволяет менять веса, выводить членов из работы, менять метод и добавлять членов на лету. Требует `mod_status` [Apache-док].
- В Ubuntu блок в `/etc/apache2/mods-available/proxy_balancer.conf` закомментирован и рассчитан на `Require local` [Ubuntu].
- Защита: доступ только с адреса администратора; nonce (`nonce` балансировщика, по умолчанию автоматический UUID) не отключать (`nonce=None`). С 2.4.41 усилена защита от XSS/XSRF [Apache-док]. Дополнительно — аутентификация (`apache/02-…`).
- Управлять можно только балансировщиками, объявленными вне `<Location>`. При работе через менеджер нужен `ProxyPassInherit Off` (отключает и `BalancerInherit`), иначе возможна несогласованность. Изменения переживают перезапуск только при `BalancerPersist On` [Apache-док].

```apache
<Location "/balancer-manager">
    SetHandler balancer-manager
    Require local
    Require ip 10.10.0.10
</Location>
ProxyPass "/balancer-manager" "!"     # если на хосте есть ProxyPass "/" — исключение раньше него
```

`ProxyStatus On` (в Ubuntu задан в `status.conf`) добавляет состояние членов в `server-status` (разд. 13) [Ubuntu, Apache-док].

---

## 12. Журналы

### 12.1. Что есть в Ubuntu из коробки [Ubuntu]

| Файл | Кто пишет | Формат |
|---|---|---|
| `/var/log/apache2/error.log` | `ErrorLog ${APACHE_LOG_DIR}/error.log` в `apache2.conf` и в `000-default.conf` | `LogLevel warn` |
| `/var/log/apache2/access.log` | `CustomLog ${APACHE_LOG_DIR}/access.log combined` в `000-default.conf` | `combined` |
| `/var/log/apache2/other_vhosts_access.log` | `conf-available/other-vhosts-access-log.conf`: хосты без своего `CustomLog` | `vhost_combined` |

Форматы, объявленные в `apache2.conf` (одинаковы в 22.04/24.04/26.04):

```apache
LogFormat "%v:%p %h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" vhost_combined
LogFormat "%h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" combined
LogFormat "%h %l %u %t \"%r\" %>s %O" common
LogFormat "%{Referer}i -> %U" referer
LogFormat "%{User-agent}i" agent
```

Вместо `%b` (размер тела) Ubuntu пишет `%O` — реально отправленные байты с заголовками. Так видны оборванные ответы [Ubuntu, Apache-док]. Комментарий в `http2.conf` Ubuntu (во всех трёх выпусках) утверждает, что `mod_http2` не поддерживает `mod_logio` и `%O`, и предлагает `%B`. Комментарий устарел — уточнено 20.10.2026 по `CHANGES_2.4`: `mod_http2` передаёт счётчики в `mod_logio` с 2.4.19, а точный учёт отправленных байт в `%O` — с 2.4.58 («Accurately report the bytes sent for a request in the '%O' Log format»). Менять `%O` на `%B` не нужно; на 22.04 значения `%O` для запросов по HTTP/2 могут быть неточными [Apache-док]. Права на файлы — `640 root:adm` (из `logrotate`). Читать их без `sudo` может член группы `adm` [Ubuntu].

Методичка ИТС требует на веб-серверах продуктива собирать и access-, и error-журналы [ИТС-мет 5899, 2016].

### 12.2. Журнал ошибок

- `ErrorLog файл|syslog[:[facility][:tag]]`. Значение `|программа` — передача в программу. Для syslog умолчание — `local7`, а facility фактически действует на весь сервер [Apache-док].
- **Уровни:** `emerg`, `alert`, `crit`, `error`, `warn`, `notice`, `info`, `debug`, `trace1`–`trace8`; умолчание `warn`. При записи в файл сообщения уровня `notice` подавить нельзя [Apache-док].
- **По модулям:** `LogLevel warn proxy:info proxy_balancer:info reqtimeout:info`. Имя модуля можно писать как `ssl`, `mod_ssl.c` или `ssl_module`. Уровень по каталогу (`<Directory>`/`<Location>`) влияет только на сообщения, связанные с запросом [Apache-док].
- С 2.4 сообщения «File does not exist» для `404` пишутся на уровне `info`; вернуть прежнее поведение — `LogLevel warn core:info` [Apache-док].
- **`ErrorLogFormat`:** `%{u}t` — время с микросекундами, `%{cuz}t` — ISO 8601 с зоной (2.4.58+), `%L` — ID записи, `%{c}a` — адрес соединения, `%m` — модуль, `%l` — уровень, `%P`/`%T` — процесс/поток. Модификатор `-` выводит `-` для пустого значения [Apache-док]. Пример по умолчанию для потоковых MPM приведён в документации.
- **Связка error ↔ access:** `%L` в обоих форматах даёт общий ID записи. При загруженном `mod_unique_id` это его уникальный ID запроса, который доступен также как `%{UNIQUE_ID}e` [Apache-док].

```apache
# /etc/apache2/conf-available/zz-errorlog.conf
ErrorLogFormat "[%{cuz}t] [%-m:%l] [pid %P:tid %T] [R:%L] [client\ %a] %M% ,\ referer\ %{Referer}i"
LogLevel warn proxy:info reqtimeout:info
```

На 22.04 `%{cuz}t` нет — используйте `%{u}t`. `% ` (процент и пробел) — разделитель полей без вывода, `\ ` — пробел внутри поля [Apache-док]. После правки — `apache2ctl configtest`.

### 12.3. Журнал доступа: формат для разбора производительности

Полезные поля [Apache-док]:

| Поле | Что пишет |
|---|---|
| `%D` | время обработки запроса, **микросекунды** |
| `%T` / `%{ms}T` / `%{us}T` | то же в секундах / мс / мкс (единицы — с 2.4.13) |
| `%^FB` | мкс от получения запроса до первого байта заголовков ответа; нужен `LogIOTrackTTFB On` (2.4.13+, `mod_logio`) |
| `%I` / `%O` / `%S` | байты получено / отправлено / сумма с заголовками (`mod_logio`; `%S` — 2.4.7+) |
| `%X` | состояние соединения в конце: `X` — оборвано до окончания ответа, `+` — останется keep-alive, `-` — закроется |
| `%k` | номер запроса в keep-alive-соединении |
| `%>s` | итоговый статус (у `%s` — статус исходного запроса при внутренних перенаправлениях) |
| `%a` / `%{c}a` | адрес клиента (с учётом `mod_remoteip`) / адрес TCP-соединения |
| `%v` / `%V` | имя виртуального хоста (каноническое / по `UseCanonicalName`) |
| `%{X}i` / `%{X}o` | заголовок запроса / ответа |
| `%{X}e` / `%{X}n` | переменная окружения / заметка модуля: `%{BALANCER_WORKER_NAME}e`, `%{UNIQUE_ID}e`, `%{remoteip-proxy-ip-list}n`, `%{proxy-status}n` и `%{proxy-source-port}n` (`mod_proxy_http`; есть с 2.4.0 — уточнено 20.10.2026 по `CHANGES_2.4` и коду 2.4.52/2.4.69) |
| `%L` | ID записи журнала ошибок для этого запроса |
| `%{msec_frac}t` и др. | время с миллисекундами: `"%{%d/%b/%Y %T}t.%{msec_frac}t %{%z}t"` |

Модификаторы по статусу: `%400,501{User-agent}i` — только при этих кодах; `%!200,304,302{Referer}i` — кроме них [Apache-док].

Формат `perf` для этой базы (комбинированный плюс время и сведения прокси) [практика]:

```apache
# /etc/apache2/conf-available/zz-logformat.conf
LogIOTrackTTFB On
LogFormat "%v:%p %a %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\" %D %^FB %X %k \"%{BALANCER_WORKER_NAME}e\"" perf
```

```bash
sudo a2enconf zz-logformat
sudo apache2ctl configtest && sudo systemctl reload apache2
# использовать: CustomLog ${APACHE_LOG_DIR}/svc_access.log perf
```

`%a` вместо `%h` выбран, чтобы в журнале был адрес даже при `HostnameLookups On`. С `mod_remoteip` оба показывают адрес клиента [Apache-док]. Строки с неразобранными полями (`-` вместо значения) нормальны: например, `%{BALANCER_WORKER_NAME}e` пуст вне балансировщика.

### 12.4. Условная запись и отдельные журналы

- `CustomLog файл формат env=[!]переменная` или `expr=выражение`. Переменные ставит `mod_setenvif` (`SetEnvIf`), который в Ubuntu включён [Apache-док, Ubuntu].
- Типовое: убрать из журнала опросы мониторинга и проверки здоровья.

```apache
SetEnvIf Request_URI "^/server-status" dontlog
SetEnvIf Request_URI "^/healthz\.txt$" dontlog
CustomLog ${APACHE_LOG_DIR}/access.log perf env=!dontlog
```

- Отдельный журнал для потока событий (например, приём событий GlitchTip):

```apache
SetEnvIf Request_URI "^/api/[0-9]+/(store|envelope)/" gt_ingest
CustomLog ${APACHE_LOG_DIR}/glitchtip_ingest.log perf env=gt_ingest
CustomLog ${APACHE_LOG_DIR}/glitchtip_access.log perf env=!gt_ingest
```

- `GlobalLog` (2.4.19+) — журнал, общий для основного сервера и всех хостов, в том числе тех, у которых есть свой `CustomLog` [Apache-док].
- Сотни отдельных журналов по хостам расходуют файловые дескрипторы. Компромисс — общий журнал с `%v` и последующая разбивка утилитой `split-logfile` (есть в `apache2-utils`) [Apache-док, Ubuntu].
- `BufferedLogs On` копит записи в памяти и пишет пачками; задаётся один раз на сервер; при аварии записи теряются [Apache-док]. На серверах этой базы не нужен.

### 12.5. Ротация

**Ubuntu — logrotate** (`/etc/logrotate.d/apache2`, одинаково в 22.04/24.04/26.04; блоки `prerotate`/`postrotate` сокращены) [Ubuntu]:

```
/var/log/apache2/*.log {
	daily
	missingok
	rotate 14
	compress
	delaycompress
	notifempty
	create 640 root adm
	sharedscripts
	prerotate   … run-parts /etc/logrotate.d/httpd-prerotate (если каталог есть)
	postrotate  … invoke-rc.d apache2 reload (если apache2 запущен)
}
```

Следствия:

- Ротируются все `*.log` в `/var/log/apache2/` (в том числе ваши `svc_access.log`), хранятся 14 дней; скрипты из `/etc/logrotate.d/httpd-prerotate/` выполняются перед ротацией — место для копирования журнала в архив [Ubuntu].
- **Каждую ночь — `reload` (graceful restart):** текущие запросы доживают в старых процессах (`G`) [Apache-док]. Для публикации 1С это ежедневное пересоздание экземпляров модуля и пулов соединений с кластером ⚠ (вывод из [ИТС-адм разд. 8.2]); для `event` нужен запас `ServerLimit` (разд. 3.3).

```bash
sudo logrotate -d /etc/logrotate.d/apache2      # «сухой» прогон: что будет сделано
# ⚠ принудительная ротация выполнит reload Apache — не в рабочее время:
sudo logrotate -f /etc/logrotate.d/apache2
ls -lh /var/log/apache2/
```

**Альтернатива — `rotatelogs` через канал** (`apache2-utils`, `/usr/bin/rotatelogs`) [Apache-док, Ubuntu]:

```apache
# имена без окончания .log, чтобы файлы не попали ещё и под logrotate (маска /var/log/apache2/*.log)
CustomLog "|/usr/bin/rotatelogs -l -n 7 /var/log/apache2/1c_access_log 100M" perf
ErrorLog  "|/usr/bin/rotatelogs -l /var/log/apache2/1c_error_log.%Y-%m-%d 86400"
```

- Ротация без перезапуска Apache; по времени (секунды) или размеру (`B/K/M/G`). Ключи: `-l` — местное время, `-L ссылка` — ссылка на текущий файл, `-n N` — циклический набор из N файлов (2.4.5+), `-t` — усечение вместо ротации, `-T` (2.4.56+), `-c`, `-f`, `-D`, `-e`, `-p программа`, `-v` [Apache-док].
- Процесс канала запускается родительским процессом Apache и **работает от `root`**. Держите программу простой и защищённой [Apache-док]. `|` запускает программу без оболочки, `|$` — через `/bin/sh -c` [Apache-док].
- Если такой файл попадает под маску `*.log` logrotate, ротировать будут оба механизма. Выносите журналы `rotatelogs` в отдельный каталог или называйте иначе, как в примере; маски сборщика журналов (разд. 14.3) поправьте под эти имена [практика].

### 12.6. Прочие журналы

- **`mod_log_forensic`** пишет на каждый запрос две строки: до обработки — ID, строку запроса и все заголовки, после — только ID; в обычный журнал ID выводится как `%{forensic-id}n`. Так находят запрос, во время которого упал процесс; проверка — `check_forensic` (`apache2-utils`) [Apache-док, Ubuntu]. Журнал содержит и заголовки `Authorization` (пароли Basic) — документация требует, чтобы его мог читать только пользователь, запустивший сервер, а logrotate Ubuntu создаёт файлы `640 root:adm` [Apache-док, Ubuntu]. Включать только на время разбора аварий: `sudo a2enmod log_forensic` и `ForensicLog ${APACHE_LOG_DIR}/forensic.log`; после разбора выключить и удалить журнал.
- **`journalctl -u apache2`** показывает сообщения запуска и остановки (до открытия `ErrorLog`) и ошибки `apache2ctl` [практика].
- Журналы модуля 1С (технологический журнал процесса `apache2`) — `../1c/05-…`, разд. 12.6; `../1c/07-…`.

### 12.7. Быстрый разбор

```bash
L=/var/log/apache2/access.log           # combined: $1 — адрес, $7 — URI, $9 — статус
sudo awk '{print $9}' $L | sort | uniq -c | sort -rn          # коды ответов
sudo awk '$9 ~ /^5/' $L | tail -n 20                           # последние 5xx
sudo awk '{print $1}' $L | sort | uniq -c | sort -rn | head    # топ клиентов
# perf: $8 — URI, $10 — статус; от конца: $(NF-4) — %D, $(NF-3) — %^FB, $(NF-2) — %X
P=/var/log/apache2/1c_access.log
sudo awk '{printf "%.1f ms %s %s\n", $(NF-4)/1000, $10, $8}' $P | sort -rn | head -20   # самые долгие
sudo awk '$(NF-4) > 30000000 {print $5, $10, $8, $(NF-4)/1e6 " s"}' $P | tail          # дольше 30 с
sudo awk '$(NF-2) == "X"' $P | tail                                                    # оборванные клиентом
```

Поля считайте по своей строке журнала (`head -1`): `%t` занимает два поля, а `User-Agent` содержит пробелы — поэтому хвостовые поля берутся от конца (`NF`). Приёмы `awk` — `../linux/02-tekst-i-logi.md`.

---

## 13. `mod_status`: состояние сервера

### 13.1. Как настроено в Ubuntu [Ubuntu]

`/etc/apache2/mods-available/status.conf` (модуль `status` включён по умолчанию):

```apache
<Location /server-status>
	SetHandler server-status
	Require local
	#Require ip 192.0.2.0/24
</Location>
ExtendedStatus On
#SeeRequestTail On
<IfModule mod_proxy.c>
	ProxyStatus On
</IfModule>
```

- `ExtendedStatus` у Apache по умолчанию `Off`, но загрузка `mod_status` с 2.3.6 включает его. Без него недоступны число запросов и байт, нагрузка на процессор, текущие клиенты и запросы [Apache-док]. Действует на весь сервер, при graceful restart не меняется, сбор немного замедляет сервер [Apache-док].
- `SeeRequestTail On` показывает последние 63 символа запроса вместо первых 63 — удобно для длинных URL OData [Ubuntu, Apache-док].
- **Безопасность:** если `mod_status` загружен, обработчик `server-status` можно назначить в любом файле конфигурации, включая `.htaccess` [Apache-док]. В Ubuntu `.htaccess` не читаются (`AllowOverride None`) [Ubuntu]. Страница с `ExtendedStatus` показывает адреса клиентов и URL запросов — наружу её не открывать [практика].

### 13.2. Открыть страницу серверу мониторинга

```apache
# /etc/apache2/conf-available/zz-status-monitoring.conf
<Location "/server-status">
    SetHandler server-status
    Require local
    Require ip 10.10.0.50
</Location>
```

```bash
sudo a2enconf zz-status-monitoring
sudo apache2ctl configtest && sudo systemctl reload apache2
curl -s http://127.0.0.1/server-status?auto | head
# с сервера мониторинга 10.10.0.50:
curl -s http://srv-itsm.example.local/server-status?auto | grep -E 'BusyWorkers|IdleWorkers'
```

Подводные камни:

- По умолчанию (`AuthMerging Off`) секция с директивами авторизации **заменяет** их из предыдущих секций для того же пути. Поэтому `Require local` повторён — подтверждено 20.10.2026 по документации `mod_authz_core` (`AuthMerging`: при `Off` директивы авторизации секции «override those of the preceding sections») [Apache-док].
- **Хост с `ProxyPass "/"`** отправит `/server-status` на бэкенд. Нужно исключение `ProxyPass "/server-status" "!"` **до** общего правила [Apache-док].
- **Хост с `Redirect permanent / https://…`** на порту 80 перенаправит и `/server-status`. Опрашивайте `https://…/server-status?auto` (при самоподписанном сертификате — `curl -k`) или вынесите статус на отдельный внутренний `VirtualHost`/порт [практика].
- Если запросы к статусу заполняют журнал, уберите их условием `dontlog` (разд. 12.4).

### 13.3. Машинный формат `?auto` [Apache-док, код 2.4.58/2.4.66/2.4.69]

| Ключ | Что значит | Замечание |
|---|---|---|
| `ServerVersion`, `ServerMPM`, `Server Built` | версия, MPM, дата сборки | |
| `CurrentTime`, `RestartTime`, `ServerUptimeSeconds`, `ServerUptime`, `Uptime` | время и аптайм | `Uptime` — только с `ExtendedStatus` |
| `ParentServerConfigGeneration`, `ParentServerMPMGeneration` | поколение конфигурации (растёт при `reload`) | |
| `Load1`, `Load5`, `Load15` | средняя загрузка ОС | |
| `Total Accesses`, `Total kBytes`, `Total Duration` | счётчики с запуска; длительность в мс (с 2.4.35) | `ExtendedStatus` |
| `CPUUser`, `CPUSystem`, `CPUChildrenUser`, `CPUChildrenSystem`, `CPULoad` | процессор | `ExtendedStatus` |
| `ReqPerSec`, `BytesPerSec`, `BytesPerReq`, `DurationPerReq` | **средние с запуска**, не текущие | для графиков считайте скорость по счётчикам |
| `BusyWorkers`, `IdleWorkers` | занятые и свободные потоки (процессы в `prefork`) | до 2.4.58 при `event` печатались дважды (второй раз — в блоке асинхронного MPM) |
| `GracefulWorkers` | потоки, доживающие после graceful restart | **2.4.58+**; до этого считались в `BusyWorkers` |
| `Processes`, `Stopping` | число процессов, из них останавливающихся | только асинхронный MPM (`event`) |
| `ConnsTotal`, `ConnsAsyncWriting`, `ConnsAsyncKeepAlive`, `ConnsAsyncClosing` | соединения, в том числе удерживаемые слушающим потоком | только `event` |
| `ConnsAsyncWaitIO` | соединения в ожидании ввода-вывода | с 2.4.63 (по коду: нет в 2.4.62, есть в 2.4.63–2.4.69); только `event` |
| `Scoreboard` | строка: по символу на слот | легенда ниже |

Легенда scoreboard: `_` — ждёт соединения, `S` — запускается, `R` — читает запрос, `W` — отправляет ответ, `K` — keep-alive (чтение), `D` — DNS, `C` — закрывает соединение, `L` — пишет журнал, `G` — завершается мягко, `I` — очистка простаивающего потока, `.` — свободный слот без процесса [Apache-док, код `mod_status.c`]. Длина строки обычно равна `MaxRequestWorkers`: пустые слоты процессов сверх `MaxRequestWorkers / ThreadsPerChild` и потоков сверх `ThreadsPerChild` (до `ServerLimit × ThreadLimit`) не выводятся; строка длиннее, только пока в «лишних» слотах доживают процессы после `reload` (уточнено 20.10.2026 по коду `mod_status.c` 2.4.69) [Apache-код].

### 13.4. Как читать

| Картина | Что значит | Действие |
|---|---|---|
| `BusyWorkers` ≈ `MaxRequestWorkers`, мало `_` | потоки исчерпаны, новые соединения ждут в очереди | разд. 3.3–4; искать долгие запросы (`W`) |
| много `W` с большим временем в HTML-странице (колонка `SS` — секунды с начала запроса) | долгие ответы: вызовы 1С или медленный бэкенд | `ExtendedStatus` показывает URL и клиента; сверить с журналом `%D` |
| много `K` при `worker` | потоки заняты простоем keep-alive | уменьшить `KeepAliveTimeout` или перейти на `event` (кроме сервера 1С) |
| много `G` после ночного `reload` | доживают долгие запросы | норма; при `AH03490` увеличить `ServerLimit` |
| много `R` | медленные клиенты или атака «медленными заголовками» | `mod_reqtimeout` (разд. 5) |
| `ConnsAsyncKeepAlive` велик, `BusyWorkers` мал (`event`) | всё в порядке: простаивающие соединения не держат потоков | — |

Порядок разбора из документации: убедиться, что `ExtendedStatus On`; найти в `top` процессы `apache2`, которые больше всех едят процессор или память; найти их PID на `server-status` и посмотреть запрос и клиента. Запросы короткие, поэтому может понадобиться несколько попыток [Apache-док].

```bash
watch -n 2 "curl -s http://127.0.0.1/server-status?auto | grep -E 'Busy|Idle|Graceful|Processes|Conns'"
curl -s 'http://127.0.0.1/server-status?refresh=5' >/dev/null      # для браузера: автообновление каждые 5 с
curl -s http://127.0.0.1/server-status | sed 's/<[^>]*>//g' | grep -E ' W ' | head   # грубо: строки в состоянии W
```

---

## 14. Мониторинг

### 14.1. Zabbix

Шаблоны из поставки Zabbix 7.4 (требуют Zabbix 7.4+, проверены на Apache 2.4.41) [сторонний]:

| Шаблон | Как собирает | Макросы и особенности |
|---|---|---|
| «Apache by HTTP» | HTTP-агент Zabbix опрашивает `server-status?auto` удалённо | `{$APACHE.STATUS.HOST}`, `{$APACHE.STATUS.PORT}` (80), `{$APACHE.STATUS.PATH}` (`server-status?auto`), `{$APACHE.STATUS.SCHEME}` (`http`), `{$APACHE.RESPONSE_TIME.MAX.WARN}` (10 с) |
| «Apache by Zabbix agent» | агент опрашивает статус локально и дополнительно собирает статистику процессов `apache` (CPU, память, запущен ли) | для серверов, где агент уже стоит |

- Элементы: всего запросов и байт, скорость (как изменение счётчиков — шаблон сознательно **не** использует `ReqPerSec`/`BytesPerSec`, это средние с запуска), `BusyWorkers`/`IdleWorkers`, разбивка scoreboard по состояниям. Обнаружение `event` добавляет `ConnsTotal`, `ConnsAsync*`, `Processes` [сторонний].
- Триггеры: страница статуса недоступна 30 мин, служба недоступна, время ответа выше макроса, перезапуск (аптайм < 10 мин), смена версии [сторонний].
- **Чего в шаблоне нет и что стоит добавить** [практика]:
  - триггер на заполнение потоков: `last(…workers_total.busy) / <MaxRequestWorkers вашего сервера> > 0.8` в течение 5 минут (`MaxRequestWorkers` в `?auto` не выводится — задайте макросом);
  - элемент журнала `log[/var/log/apache2/error.log,"reached MaxRequestWorkers|within MinSpareThreads|scoreboard is full"]` (агенту нужно право чтения: группа `adm`) ⚠ синтаксис элемента сверяйте с документацией вашей версии Zabbix;
  - веб-сценарий на публикацию 1С и сервисы (код ответа, время);
  - срок сертификата — `apache/02-…`.
- Ключ `GracefulWorkers` (2.4.58+) шаблон не собирает — уточнено 20.10.2026: в списке элементов README шаблонов 7.4 его нет; потоки в состоянии `G` видны элементом «Workers finishing» (разбор строки scoreboard) [сторонний]. После ночного `reload` на 22.04 доживающие потоки попадают в `BusyWorkers` — возможны ложные всплески [Apache-док, практика].

### 14.2. Prometheus: `apache_exporter` [сторонний]

- Проект `Lusitaniae/apache_exporter`, последний выпуск — **v1.1.1 от 22.06.2026**. В Ubuntu есть пакет `prometheus-apache-exporter`: 22.04 — 0.11.0, 24.04 — 1.0.6, 26.04 — 1.0.11 [сторонний, Ubuntu].
- Ключи: `--scrape_uri` (по умолчанию `http://localhost/server-status?auto`; **`?auto` обязателен**, иначе будут только `apache_up` и `apache_cpuload`), `--web.listen-address` (по умолчанию `:9117`), `--host_override`, `--insecure`, `--web.config.file` (TLS и базовая аутентификация самого экспортёра) [сторонний].
- Метрики: `apache_up`, `apache_accesses_total`, `apache_sent_kilobytes_total`, `apache_workers`, `apache_scoreboard`, `apache_cpu_load`, `apache_uptime_seconds_total`, `apache_duration_ms_total`, `apache_version`. Помеченные «(*)» требуют `ExtendedStatus On` [сторонний].
- Скорости считаются на стороне Prometheus: `rate(apache_accesses_total[5m])`; по экспортёру на каждый экземпляр Apache [сторонний].
- Порт 9117 закройте `ufw` для всех, кроме Prometheus (`../linux/08-…`). Параметры экспортёра в пакете Ubuntu — в `/etc/default/prometheus-apache-exporter` (уточнено 20.10.2026 по спискам файлов пакета на packages.ubuntu.com для 22.04, 24.04 и 26.04; там же юнит `prometheus-apache-exporter.service`) [Ubuntu].
- В стенде этой базы Prometheus нет (Loki + Grafana + GlitchTip). Экспортёр нужен, если метрики Apache захотят видеть в Grafana рядом с журналами [практика].

### 14.3. Журналы Apache в Loki и Grafana

- Сбор файлов журналов — **Grafana Alloy**; Promtail снят с поддержки 02.03.2026 [сторонний: `../observability/03-…`, разд. 7].
- Компоненты Alloy для чтения файлов — `local.file_match` → `loki.source.file` → `loki.write` [сторонний: документация Alloy]:

```alloy
// /etc/alloy/config.alloy на srv-1c-app (фрагмент) ⚠ на сервере не проверялся
local.file_match "apache" {
  path_targets = [
    {"__path__" = "/var/log/apache2/*access.log", "job" = "apache", "host" = "srv-1c-app", "kind" = "access"},
    {"__path__" = "/var/log/apache2/*error.log",  "job" = "apache", "host" = "srv-1c-app", "kind" = "error"},
  ]
}
loki.source.file "apache" {
  targets    = local.file_match.apache.targets
  forward_to = [loki.write.obs.receiver]
}
loki.write "obs" {
  endpoint {
    url = "https://loki.example.local/loki/api/v1/push"
    basic_auth {
      username = "alloy"
      password = sys.env("LOKI_PUSH_PASSWORD")
    }
  }
}
```

- **Метки** — только статичные: `job`, `host`, `kind` (иногда `vhost`). Статус, IP, URL и пользователь в метки не выносятся — для них фильтры и разбор при запросе [сторонний: `../observability/03-…`, разд. 3].
- Права: журналы `640 root:adm`. Пользователь службы Alloy должен входить в группу `adm`. Пакет Alloy для Debian/Ubuntu делает это сам: создаёт пользователя `alloy` и добавляет его в группы `adm` и `systemd-journal` (уточнено 20.10.2026 по `packaging/deb/control/postinst` выпуска 1.20.1); проверка — `id alloy` [сторонний]. Переменные окружения вроде `LOKI_PUSH_PASSWORD` служба берёт из `/etc/default/alloy` (`EnvironmentFile` в юните пакета) [сторонний].
- Ротация logrotate (переименование + `create`) штатная для чтения файлов; сжатые `.gz` Alloy читать не должен — маска `*.log` их не захватывает [практика].
- Запросы LogQL с парсером `pattern` (формат `combined`) [сторонний: Loki 3.7.8, log_queries]:

```logql
# число ответов 5xx за 5 минут по хостам (шаблон для формата combined; строки формата perf начинаются с %v:%p — для них второй шаблон)
sum by (host) (count_over_time({job="apache", kind="access"} | pattern `<ip> <_> <_> [<_>] "<method> <uri> <_>" <status> <_>` | status =~ "5.." [5m]))

# 95-й процентиль времени ответа публикации 1С (формат perf: поле %D после User-Agent)
quantile_over_time(0.95,
  {job="apache", kind="access", host="srv-1c-app"}
  | pattern `<_> <ip> <_> <_> [<_>] "<method> <uri> <_>" <status> <_> "<_>" "<_>" <dur_us> <ttfb> <_> <_> <_>`
  | unwrap dur_us [5m]) by (host)

# ошибки исчерпания потоков
{job="apache", kind="error"} |~ "reached MaxRequestWorkers|scoreboard is full"
```

Эти запросы — заготовки: проверьте шаблоны `pattern` на своих строках в Grafana Explore ⚠.

### 14.4. Что контролировать и с какими порогами

| Что | Источник | Порог для начала [практика] |
|---|---|---|
| Служба запущена, порт отвечает | Zabbix `net.tcp.service`, `systemctl is-active apache2` | недоступна 1–2 мин |
| Заполнение потоков | `BusyWorkers` / `MaxRequestWorkers` | > 80 % дольше 5 мин |
| Исчерпание | `AH00484`/`AH00286`/`AH00161`, `AH03490` в `error.log` | любое появление |
| Ошибки прокси | `AH01102`, `AH00898`, `AH00957`, `AH01114`, `AH00940`; доля 5xx в access | > 1 % запросов за 5 мин, или любые 502/504 на API интеграций |
| Время ответа | `%D` (95-й процентиль) по публикации 1С и сервисам | рост в 2 раза к недельной норме |
| Оборванные ответы | `%X = X` | всплеск |
| Перезапуски | `ServerUptimeSeconds`, `ParentServerConfigGeneration` | неожиданный перезапуск |
| Место под журналы | `/var/log` | < 15 % свободного |
| Сертификаты | `apache/02-…` | < 21 дня |

### 14.5. Синтетические проверки `curl`

```bash
# время по фазам: DNS, TCP, TLS, первый байт, всего
curl -s -o /dev/null -w 'dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total} code=%{http_code}\n' \
     https://1c.example.local/demo/
# только заголовки ответа
curl -sI https://redmine.example.local/ | head -n 5
```

Проверка самой публикации 1С (веб-клиент, WSDL, HTTP-сервис, OData) — `../1c/05-…`, разд. 7.

---

## 15. Нагрузочная проверка

⚠ **Предупреждение.** Нагрузка на публикацию 1С создаёт сеансы, занимает лицензии и рабочие процессы кластера, а на продуктиве мешает пользователям. Нагружайте тестовую базу и тестовый стенд или статический ресурс. Вызовы HTTP-сервисов без `reuseSessions` создают сеанс на каждый запрос (`../1c/05-…`, разд. 12.5) [практика]. Предупредите владельцев сервисов (Redmine, NetBox, GlitchTip) до теста.

### 15.1. `ab` (ApacheBench) [Apache-док, Ubuntu]

Ставится пакетом `apache2-utils` (`/usr/bin/ab`; там же `htcacheclean`, `logresolve`, `rotatelogs`, `check_forensic`, `split-logfile`) [Ubuntu].

| Ключ | Смысл |
|---|---|
| `-n` | число запросов (по умолчанию 1 — нерепрезентативно) |
| `-c` | одновременность (по умолчанию 1) |
| `-t` | ограничение по времени, секунды (подразумевает `-n 50000`) |
| `-k` | включить keep-alive (по умолчанию выключен) |
| `-s` | таймаут сокета, с (по умолчанию 30; 2.4.4+) |
| `-H` | дополнительный заголовок (например, `Accept-Encoding: gzip`) |
| `-A` | Basic-аутентификация `логин:пароль` |
| `-p` / `-u` + `-T` | файл для POST / PUT и его `Content-Type` |
| `-m` | произвольный метод (2.4.10+) |
| `-l` | не считать ошибкой разную длину ответов (динамические страницы; 2.4.7+) |
| `-e` | CSV-распределение по процентилям |

Ограничения из документации: статические буферы фиксированной длины, неполная реализация HTTP/1.x; `ab` может измерить сам себя, а не сервер [Apache-док].

```bash
sudo apt install -y apache2-utils
# статический файл через прокси: 2000 запросов, 50 одновременно, с keep-alive
ab -n 2000 -c 50 -k https://netbox.example.local/static/netbox.css
# лёгкий HTTP-сервис тестовой базы (не продуктив!), длительность 60 с
ab -t 60 -c 20 -k -l -H 'Accept: application/json' https://1c-test.example.local/test/hs/ping/
```

Смотрите `Requests per second`, `Time per request`, `Failed requests`, `Non-2xx responses` и таблицу процентилей. Параллельно — `server-status` и `error.log`:

```bash
watch -n 1 "curl -s http://127.0.0.1/server-status?auto | grep -E 'Busy|Idle|Conns'"
sudo tail -f /var/log/apache2/error.log
```

### 15.2. `wrk` [сторонний]

- Пакет `wrk` 4.1.0 есть в Ubuntu 22.04, 24.04 и 26.04 (`universe`) [Ubuntu]. Многопоточный, на epoll; сценарии на LuaJIT (`-s`) [сторонний].
- Ключи: `-t` — потоки, `-c` — открытых соединений всего, `-d` — длительность (`30s`, `2m`), `-H` — заголовок, `--latency` — подробное распределение задержек, `--timeout` — сколько ждать ответа [сторонний].
- Совет авторов: на машине с `wrk` нужно достаточно эфемерных портов, а `listen` backlog сервера должен быть больше числа одновременных соединений теста [сторонний] — сравните с `ListenBackLog` (разд. 4.4).

```bash
sudo apt install -y wrk
wrk -t4 -c200 -d60s --latency https://grafana.example.local/public/build/   # статика Grafana; путь — ваш
```

### 15.3. Порядок теста [практика]

1. Зафиксировать исходное состояние: `server-status?auto`, `free -m`, `ps … --sort=-rss`, журналы.
2. Запустить нагрузку с генератора на **другой** машине: генератор на том же хосте искажает результат.
3. Ступенчато поднимать одновременность (10 → 50 → 100 → 200) и на каждой ступени смотреть `BusyWorkers`, RSS, загрузку процессора, `AH00484`, долю ошибок, `%D`.
4. Найти точку, где растёт время ответа или появляются ошибки. Сравнить с расчётом разд. 4 и поправить MPM.
5. Повторить тест после правки и записать результаты в эксплуатационную документацию.

---

## 16. Готовые наборы настроек

### 16.1. `srv-1c-app` — публикация 1С (серверная база)

| Что | Значение | Где |
|---|---|---|
| MPM | `worker` (разд. 2.3) | `a2dismod mpm_event && a2enmod mpm_worker` |
| Потоки | по замеру (разд. 4); отправная точка — `../1c/05-…`, разд. 12.1 | `mods-available/mpm_worker.conf` |
| Таймауты | `Timeout 300` (Ubuntu), `KeepAliveTimeout 5`, `GracefulShutdownTimeout 60` | `conf-available/zz-1c-limits.conf` |
| Размер запросов | `LimitRequestBody` на `<Location>` публикаций; `LimitRequestFieldSize 16384` глобально (Kerberos) | там же |
| Сжатие | `deflate` (Ubuntu) + `application/json` при больших ответах OData (`../1c/05-…`, разд. 12.4) | `conf-available/` |
| Кеш | `mod_cache` и глобальный `ExpiresDefault` — нет | — |
| Реальный IP | `mod_remoteip` + `RemoteIPInternalProxy <IP прокси>` (если есть прокси) | `conf-available/remoteip.conf` |
| Журнал | формат `perf` с `%D` и `%^FB` | `conf-available/zz-logformat.conf` |
| Статус | `/server-status` для `127.0.0.1` и сервера мониторинга | `conf-available/zz-status-monitoring.conf` |

### 16.2. `srv-itsm` / `srv-obs` и `rp-1c`

- **Прокси сервисов:** `event` с `MaxRequestWorkers 150` из Ubuntu (поднимать по `BusyWorkers`); модули `proxy proxy_http headers ssl` (+ `brotli`, `expires` по необходимости); хост на сервис с `ProxyPreserveHost On`, `X-Forwarded-Proto`/`Port`, `timeout=` по сервису; Grafana `/api/live/` — `upgrade=websocket`; журнал на сервис в формате `perf`, поток событий GlitchTip — отдельно; мониторинг — «Apache by HTTP» или `apache_exporter`, журналы — Alloy → Loki (разд. 8, 10, 12, 14).
- **`rp-1c`:** `event`, но потоки считать по одновременным **долгим** вызовам 1С (разд. 2.1); `ProxyPreserveHost On`, `X-Forwarded-Proto https`, `X-Forwarded-Port 443` [ИТС-адм разд. 8.10.3]; `connectiontimeout=5`, `timeout=` ≥ самого долгого вызова; пути как на бэкенде; при нескольких бэкендах — `bybusyness` + `ROUTEID`, проверки — `TCP` или статический файл (разд. 9, 11).

---

## Типичные ошибки (симптом → причина → решение)

| # | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | Публикация или сервис «подвисают» для всех, потом отпускает; в `error.log` `AH00484`/`AH00286` | исчерпан `MaxRequestWorkers` | разд. 3–4: поднять `MaxRequestWorkers`/`ServerLimit`, найти долгие запросы в `server-status` и по `%D` |
| 2 | После `reload` растёт число процессов, `AH03490 scoreboard is full` | процессы доживают с долгими запросами, `ServerLimit` без запаса | увеличить `ServerLimit` (нужен `restart`), уменьшить частоту `reload` |
| 3 | Значение `MaxRequestWorkers` «не применилось» | не кратно `ThreadsPerChild` или больше `ServerLimit × ThreadsPerChild` | читать `AH00513`/`AH00515` при запуске, согласовать (разд. 3.2) |
| 4 | `ServerLimit`/`ThreadLimit` изменены, но ничего не поменялось | при `reload` игнорируются (`AH00501`) | `sudo systemctl restart apache2` в окно обслуживания |
| 5 | Сервер ушёл в своп, всё медленно | `MaxRequestWorkers` больше, чем помещается в память | расчёт по RSS (разд. 4), не по VSZ |
| 6 | `413 Request Entity Too Large` при загрузке файла больше 1 ГиБ | `LimitRequestBody` по умолчанию 1 ГиБ (2.4.54+) на бэкенде или на прокси | задать на `<Location>` на **всех** звеньях (разд. 5.4) |
| 7 | `400 Bad Request` при входе через Kerberos | токен SPNEGO больше `LimitRequestFieldSize 8190` | `LimitRequestFieldSize 16384` **глобально** (внутри имённого хоста не сработает) |
| 8 | `414 Request-URI Too Long` у OData с длинным `$filter` | `LimitRequestLine 8190` | поднять глобально или переходить на POST/пакетные запросы |
| 9 | `408 Request Timeout` при медленной загрузке | `mod_reqtimeout` Ubuntu: `body=10,minrate=500` | поднять `body=` и/или снизить `minrate` для конкретного хоста; `LogLevel reqtimeout:info` для подтверждения |
| 10 | `502 Proxy Error` («Error reading from remote server») ровно через `timeout` секунд на долгом вызове 1С через прокси; в `error.log` `AH01102` | `timeout=`/`ProxyTimeout` (по умолчанию `Timeout`, 300 с в Ubuntu) меньше длительности | `timeout=` у `ProxyPass` с запасом; согласовать цепочку (разд. 5.3, 7.6) |
| 11 | `503` сразу после короткого сбоя бэкенда, хотя бэкенд уже поднялся | worker в ошибке ждёт `retry` (60 с) | подождать или `retry=10`; балансировщик с несколькими членами |
| 12 | Периодические `502` «error reading status line from remote server» на первых запросах | бэкенд закрыл простаивающее соединение из пула (гонка keep-alive) | `ttl=` меньше keep-alive-таймаута бэкенда, или `SetEnv proxy-initial-not-pooled 1`, или `disablereuse=On` |
| 13 | Таймаут, заданный в `ProxyPass` для подпути, не действует | worker sharing: URL подпути — продолжение URL более раннего правила | упорядочить по длине URL; смотреть предупреждения при запуске (разд. 7.2) |
| 14 | После входа браузер уходит на `http://` или на внутреннее имя | нет `X-Forwarded-Proto`/`Port`, `ProxyPreserveHost Off` | разд. 7.4, 9.2 |
| 15 | `CSRF verification failed` в NetBox/GlitchTip за прокси | приложение не видит внешнюю схему/имя | `ProxyPreserveHost On`, `X-Forwarded-Proto`; `CSRF_TRUSTED_ORIGINS` (разд. 8.2–8.3) |
| 16 | В журналах бэкенда у всех один IP — адрес прокси | нет `mod_remoteip` | `RemoteIPHeader X-Forwarded-For` + `RemoteIPInternalProxy` (разд. 7.5) |
| 17 | `mod_remoteip` включён, а IP всё равно прокси | у клиентов частные адреса, а прокси указан в `RemoteIPTrustedProxy` — частные адреса из заголовка он за адрес клиента не принимает | использовать `RemoteIPInternalProxy` |
| 18 | Grafana пишет об ошибке подключения Live, панели не обновляются сами | WebSocket `/api/live/` не проксируется | `ProxyPass "/api/live/" … upgrade=websocket` раньше `ProxyPass "/"` (разд. 8.4) |
| 19 | WebSocket рвётся через несколько минут простоя | туннель закрывается по `max(Timeout, timeout=)`, а на 22.04 (2.4.52) — по `min(Timeout, timeout=)` | `timeout=3600` на правиле WebSocket; на 22.04 — ещё и `Timeout` в виртуальном хосте (разд. 10) |
| 20 | `/server-status` на прокси-хосте отдаёт страницу приложения или `404` | `ProxyPass "/"` перехватывает путь | `ProxyPass "/server-status" "!"` до общего правила |
| 21 | `curl http://…/server-status` отвечает `301` | хост на 80 перенаправляет всё на HTTPS | опрашивать `https://…` (`-k` при самоподписанном) или отдельный внутренний хост |
| 22 | Мониторинг получает `403` на `server-status` | `Require local` в `status.conf`, своя секция не добавлена или потеряла `Require` | разд. 13.2 |
| 23 | Страница, закрытая `Require ip`, видна посторонним | включён `mod_cache` с quick handler | выключить или `CacheDisable` для пути, `CacheQuickHandler off` (разд. 6.4) |
| 24 | Ответы JSON не сжаты | `application/json` нет в `deflate.conf` Ubuntu | разд. 6.1 |
| 25 | Ночью единичные `502`/обрывы долгих запросов | ежедневный `reload` от logrotate совпал с пиком или долгими операциями | перенести время logrotate (таймер `logrotate.timer`, `../linux/05-…`) или `rotatelogs` для журналов публикации |
| 26 | `AH00156: Couldn't create pollset in child; check system or user limits (prefork; у worker — AH03285 …in thread…, у event — AH00495 Couldn't create a Thread Safe Pollset…; уточнено 20.10.2026 по коду 2.4.x)` | мало `fs.epoll.max_user_instances` | разд. 4.4 [Debian] |
| 27 | После нагрузочного теста HTTP-сервиса кончились лицензии 1С | каждый вызов создал сеанс | тестовая база, `reuseSessions="autouse"` (`../1c/05-…`, разд. 12.5) |
| 28 | 26.04: `systemctl stop apache2` «висит» до 90 с, затем процессы убиты | `KillSignal=SIGWINCH` — мягкая остановка ждёт долгие запросы (`GracefulShutdownTimeout 0`), пока systemd не пошлёт `SIGKILL` по `TimeoutStopSec` | `GracefulShutdownTimeout 60` (разд. 5.3). На 22.04/24.04 наоборот: `stop` обрывает запросы сразу |

---

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Версия и MPM | `apache2 -v`; `apache2ctl -V \| grep -i mpm`; `a2query -M` |
| Модули (в т. ч. статические) | `apache2ctl -M`; `apache2ctl -l` |
| Проверить конфигурацию | `sudo apache2ctl configtest` (ожидается `Syntax OK`) |
| Виртуальные хосты | `sudo apache2ctl -S` |
| Применить без обрыва запросов | `sudo systemctl reload apache2` |
| Применить `ServerLimit`/`ThreadLimit`/смену MPM | `sudo systemctl restart apache2` (обрывает запросы) |
| Переключить на worker | `sudo a2dismod mpm_event && sudo a2enmod mpm_worker && sudo apache2ctl configtest && sudo systemctl restart apache2` |
| Память процессов | `ps -o pid,nlwp,rss,vsz,cmd -C apache2 --sort=-rss` |
| Память службы | `systemctl status apache2 --no-pager \| grep -E 'Memory\|Tasks'` |
| Состояние потоков | `curl -s http://127.0.0.1/server-status?auto \| grep -E 'Busy\|Idle\|Graceful\|Scoreboard'` |
| Следить за потоками | `watch -n 2 "curl -s http://127.0.0.1/server-status?auto \| grep -E 'Busy\|Idle'"` |
| Исчерпание в журнале | `sudo grep -cE 'reached MaxRequestWorkers\|scoreboard is full' /var/log/apache2/error.log` |
| Ошибки прокси | `sudo grep -E 'AH01102\|AH00898\|AH00957\|AH01114\|AH00940' /var/log/apache2/*error.log \| tail` |
| Очередь приёма | `ss -ltn 'sport = :443'` |
| Включить прокси | `sudo a2enmod proxy proxy_http headers` |
| Включить балансировщик | `sudo a2enmod proxy_balancer lbmethod_bybusyness` |
| Реальный IP на бэкенде | `sudo a2enmod remoteip` + `RemoteIPHeader X-Forwarded-For`, `RemoteIPInternalProxy <IP>` |
| Сжатие JSON | `AddOutputFilterByType DEFLATE application/json` в файле `conf-available/` (контекст сервера, не одной строкой в `<VirtualHost>` — разд. 6.1) |
| Включить brotli | `AddOutputFilterByType BROTLI_COMPRESS;DEFLATE …` в `mods-available/brotli.conf` + `sudo a2enmod brotli` (разд. 6.2) |
| Проверить сжатие | `curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip' URL \| grep -i content-encoding` |
| Время по фазам | `curl -s -o /dev/null -w 'ttfb=%{time_starttransfer} total=%{time_total} code=%{http_code}\n' URL` |
| Коды ответов | `sudo awk '{print $9}' /var/log/apache2/access.log \| sort \| uniq -c \| sort -rn` |
| Ротация — проверить | `sudo logrotate -d /etc/logrotate.d/apache2` |
| Нагрузочный тест | `ab -n 2000 -c 50 -k URL`; `wrk -t4 -c200 -d60s --latency URL` (только тест) |
| Журнал службы | `sudo journalctl -u apache2 -e` |

---

## Источники


- **Apache** (прочитано 20.10.2026): https://httpd.apache.org/ (выпуск 2.4.69) и https://downloads.apache.org/httpd/CHANGES_2.4 (версии появления возможностей); исходники документации `raw.githubusercontent.com/apache/httpd/2.4.x/docs/manual/`: `mod/mpm_common.xml`, `mod/event.xml`, `mod/worker.xml`, `mod/prefork.xml`, `mod/core.xml`, `mod/mod_proxy.xml`, `mod/mod_proxy_http.xml`, `mod/mod_proxy_wstunnel.xml`, `mod/mod_proxy_balancer.xml`, `mod/mod_lbmethod_*.xml`, `mod/mod_proxy_hcheck.xml`, `mod/mod_remoteip.xml`, `mod/mod_headers.xml`, `expr.xml`, `mod/mod_deflate.xml`, `mod/mod_brotli.xml`, `mod/mod_filter.xml`, `mod/mod_expires.xml`, `mod/mod_cache.xml`, `mod/mod_cache_disk.xml`, `caching.xml`, `mod/mod_reqtimeout.xml`, `mod/mod_http2.xml`, `mod/mod_log_config.xml`, `mod/mod_logio.xml`, `mod/mod_log_forensic.xml`, `mod/mod_unique_id.xml`, `mod/mod_status.xml`, `logs.xml`, `howto/reverse_proxy.xml`, `misc/perf-tuning.xml`, `programs/ab.xml`, `programs/rotatelogs.xml`.
- **Исходный код Apache 2.4.69** (`raw.githubusercontent.com/apache/httpd/2.4.69/…`): `server/mpm/{event,worker,prefork}/*.c` — коды и тексты сообщений `AHxxxxx`; `modules/generators/mod_status.c` — ключи `?auto`, легенда scoreboard (сравнение с метками 2.4.52, 2.4.58, 2.4.66); `modules/proxy/proxy_util.c`, `mod_proxy_http.c`, `mod_proxy_balancer.c` — сообщения прокси, таймаут туннеля.
- **Ubuntu/Debian:** https://packages.ubuntu.com/{jammy,noble,resolute}/apache2 и списки файлов `apache2-bin`, `apache2-utils`; пакеты `prometheus-apache-exporter`, `wrk`; исходники пакета https://git.launchpad.net/ubuntu/+source/apache2/plain/debian/… (ветки `ubuntu/jammy-updates`, `ubuntu/noble-updates`, `ubuntu/resolute`): `config-dir/apache2.conf.in`, `mods-available/{mpm_event,mpm_worker,mpm_prefork,status,deflate,proxy,proxy_balancer,reqtimeout,cache_disk,http2}.conf` и `*.load`, `other-vhosts-access-log.conf`, `000-default.conf`, `apache2.logrotate`, `apache2.postinst`, `rules`, `a2query.in`, `apache2.README.Debian`; https://documentation.ubuntu.com/server/how-to/web-services/install-apache2/.
- **Независимая сверка 20.10.2026** (рецензент): исходники документации `2.4.x` (те же файлы плюс `mod/mod_authz_core.xml`, `sections.xml`); исходный код меток 2.4.52, 2.4.58, 2.4.59–2.4.66, 2.4.69: `mod_status.c` (появление `ConnsAsyncWaitIO`, длина scoreboard), `proxy_util.c` и `mod_proxy_http.c` (таймаут туннеля по версиям, 502 при таймауте ответа), `mod_filter.c`, `server/util_filter.c`, `mod_deflate.c`, `mod_brotli.c` (порядок фильтров и отказ от повторного сжатия), `server/core.c` 2.4.52/2.4.69 (`LimitRequestBody`), `server/listen.c` 2.4.65/2.4.66, `server/mpm_unix.c`, `event.c`/`worker.c` (`graceful-stop`, обработчики директив MPM); пакет Ubuntu с git.launchpad.net (ветки `ubuntu/jammy-updates`, `ubuntu/noble-updates`, `ubuntu/resolute-updates`): `apache2.service`, `apache2ctl`, `config-dir/envvars`, `a2enmod`, `changelog`, полный набор `debian/patches` веток jammy и noble; packages.ubuntu.com — версии и списки файлов `apache2-bin`, `apache2-utils`, `prometheus-apache-exporter`, `wrk`; systemd v255 (`man/systemd.service.xml`, `systemd.kill.xml`, `systemd-system.conf.xml`, `meson_options.txt`); документация ядра `cgroup-v2.rst` 5.15/5.19; Grafana Alloy 1.20.1 (`packaging/deb/control/postinst`, `packaging/deb/alloy.service`, документация компонентов, выпуски на GitHub); README шаблонов Zabbix 7.4; README и выпуски `apache_exporter`; README `wrk`; учебник Grafana «Run Grafana behind a reverse proxy» и `set-up-grafana-live.md`.
- **1С:** «Руководство администратора» 8.3.27, глава 8 (разд. 8.2, 8.10.1.1, 8.10.3; полный текст главы и конспекты `../its-docs/adm-gl08-veb-servery-p1.md`, `-p2.md`); ИТС-мет 5980 (2020) и 5899 (2016) — `../its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md`.
- **Сторонние:** README шаблонов Zabbix 7.4 `templates/app/apache_http` и `apache_agent` (github.com/zabbix/zabbix, ветка `release/7.4`); https://github.com/Lusitaniae/apache_exporter (README, выпуски); https://github.com/wg/wrk; документация Grafana (`tutorials/run-grafana-behind-a-proxy`, `setup-grafana/set-up-grafana-live.md`, ветка `main`), Loki 3.7.8 (`query/log_queries`), Alloy (`reference/components/loki/loki.source.file.md`, `local.file_match.md`, `loki.write.md`); статьи базы `../redmine/02-…`, `../redmine/06-…`, `../netbox/01-…`, `../netbox/02-…`, `../netbox/05-…`, `../observability/02-…`, `../observability/03-…`, `../guides/09-…`.

---

## Что не удалось подтвердить

1. **`wsap24` под `event`** — официально для Linux рекомендован только `worker` [ИТС-адм разд. 8.2], работа под `event` известна по практике.
2. **Туннель WebSocket:** закрыто 20.10.2026 — по коду 2.4.52 туннель живёт `min(Timeout, timeout=)`, с 2.4.53 (код 2.4.58, 2.4.69) — `max(...)`. Не проверялось только, как переподключаются клиенты Grafana Live.
3. **Коды ответа прокси:** закрыто 20.10.2026 по коду — таймаут ожидания ответа бэкенда даёт 502, 504 — только таймаут отправки тела запроса (разд. 7.6).
4. **`LimitRequestBody`:** закрыто 20.10.2026 по коду и патчам пакета (разд. 1, 5.4); на сервере значения больше 2 ГиБ не проверялись.
5. **Версии:** закрыто 20.10.2026 — `ConnsAsyncWaitIO` с 2.4.63; `addressttl` в пакет 24.04 не перенесён; `ListenTCPDeferAccept` есть в коде 2.4.66 (в документации ошибка).
6. **Сжатие:** порядок `BROTLI_COMPRESS`/`DEFLATE` и отказ от повторного сжатия установлены по коду 2.4.69 (разд. 6.1–6.2), комментарий `http2.conf` устарел (разд. 12.1); рецепт с `mods-available/brotli.conf` на сервере не проверялся.
7. **Порядок подключения:** закрыто 20.10.2026 — директивы MPM: действует прочитанное последним (код); `a2enmod` при конфликте откажет (исходник пакета); `AuthMerging Off` заменяет `Require` (документация).
8. **systemd:** закрыто 20.10.2026 — на 22.04/24.04 `stop` не мягкий, на 26.04 ждёт до `TimeoutStopSec` (умолчание systemd 90 с); дескрипторы задаёт `apache2ctl` (`ulimit -n 8192`); `memory.peak` — с ядра 5.19. На сервере не проверялось, какое `TimeoutStopUSec` реально стоит в Ubuntu.
9. **1С:** пересоздание экземпляров расширения и пулов при ежедневном `reload`; видит ли `wsap24` адрес от `mod_remoteip`; что ломается при переименовании пути публикации на прокси; WebSocket публикации и длительность HTTP-запроса веб-клиента (см. `../1c/05-…`, «Что не удалось подтвердить», пп. 4–6); влияние `LimitXMLRequestBody` на SOAP-сервисы; поведение `ab -k` с `reuseSessions`; кеширование ресурсов веб-клиента при внешних `Expires`.
10. **Мониторинг:** синтаксис элемента `log[]` вашей версии Zabbix (страницы документации Zabbix с этой машины не открылись); работа конфигурации разд. 14.3 на Alloy 1.20.1/1.21.0; шаблоны `pattern` LogQL на реальных строках `perf`. Закрыто 20.10.2026: `GracefulWorkers` шаблоны Zabbix 7.4 не собирают (README); файл параметров экспортёра — `/etc/default/prometheus-apache-exporter`; пользователь пакета Alloy — `alloy`, в группу `adm` его добавляет сам пакет.
