# IIS: производительность, обратный прокси (ARR и URL Rewrite), сжатие и кеширование, журналы, FREB, мониторинг и типовые ошибки

> **Официальные тексты по теме**: документация Microsoft — справочник конфигурации IIS (`https://learn.microsoft.com/iis/configuration/…`, исходники — репозиторий `MicrosoftDocs/iis-docs`), статьи о ARR и URL Rewrite (`…/iis/extensions/…`), статьи поддержки по IIS (`https://learn.microsoft.com/troubleshoot/developer/webapps/iis/…`, репозиторий `MicrosoftDocs/SupportArticles-docs`), «Tuning IIS 10.0» (`…/windows-server/administration/performance-tuning/role/web-server/tuning-iis-10`), HTTP Server API (`…/windows/win32/http/…`: журнал ошибок http.sys), справка командлетов `WebAdministration` и `IISAdministration`, команд `netsh http`, `typeperf`, `logman`. По 1С — «Руководство администратора» 8.3.27, гл. 8 (разд. 8.2, 8.10.2, 8.10.3) и прил. 7 (`/TComp`), конспекты `../its-docs/adm-gl08-veb-servery-p1.md` и `…-p2.md`; методички ИТС 6034 (рабочие процессы IIS на 8.3.26+) и 5899 (журналы веб-серверов). **Публикация 1С на IIS** (`webinst`, `default.vrd`, `wsisapi.dll`, права NTFS, лимиты `requestFiltering`, HTTPS и аутентификация для публикации) здесь не описывается — она в `../1c-windows/03-veb-publikaciya-iis.md`; при расхождении по фактам о 1С правы конспекты ИТС.

> Статус: проверено независимой сверкой 20.10.2026: с исходными текстами документации Microsoft (`iis-docs` — справочник конфигурации пулов, `webLimits`, `limits`, `logFile`/`customFields`, `log`, `httpLogging`, `serverRuntime`, `httpCompression`/`scheme`, `urlCompression`, `caching`, `clientCache`, `webSocket`, `tracing`/`traceFailedRequests`/`traceProviderDefinitions` и образцы `appcmd` к ним, статьи AppCmd, URL Rewrite 1.x/2.0, ARR, IIS Compression, Enhanced Logging, IIS 10.0 1709/1809, установка IIS 8.5; снимки экрана «Server Proxy Settings» в статье ARR о прямом прокси; `SupportArticles-docs` — KB 943891, 820129, 944884, 817445, 969062, 2634635, 2693489, 832981, 2697604, 502 в ARR, FRT для ARR, 400, 500.19, падения, «медленные страницы», LogParser, «Proxy server rejects requests from ARR»; `windowsserverdocs` — Tuning IIS 10.0, `netsh http`, `typeperf`, `logman`; `win32` — журнал ошибок HTTP Server API; справка командлетов `WebAdministration`/`IISAdministration`; страницы загрузки iis.net; блоги службы поддержки IIS о счётчиках; класс WMI `Win32_PerfRawData_W3SVC_WebService`), с полными текстами ИТС («Руководство администратора» 8.3.27, гл. 8, прил. 3.24 и 7; методички 6034, 5899), с инструкцией Grafana и сторонней копией схемы ARR; исправлено 4 ошибки (главная — таймаут ARR: 30 с по умолчанию у фермы, у серверного прокси 120 с, у фермы свои настройки прокси), закрыто 9 пометок; на сервере не проверялось.

> Область: IIS 10.0 на Windows Server 2016–2025 как веб-сервер публикаций 1С и как обратный прокси перед внутренними сервисами: пулы приложений под нагрузкой (очередь, веб-сад, переработка, проверка работоспособности, ограничение ЦП), соединения и таймауты, параметры http.sys, сжатие, кеширование, URL Rewrite и Application Request Routing (ARR), WebSocket, журналы W3C и HTTPERR, трассировка неудачных запросов (FREB), журналы событий, счётчики производительности, порядок диагностики и коды ошибок с подстатусами. | Версии: IIS 10.0 (Windows Server 2016 — версия 1607, 2019 — 1809, 2022, 2025; номер IIS везде 10.0), URL Rewrite 2.1, ARR 3.0 | Актуальность: 2026-10-20

**Как читать статью**

- **[MS Learn]** — документация Microsoft (learn.microsoft.com и её исходники на GitHub), прочитана 20.10.2026. С уточнением «справочник» — страница справочника конфигурации IIS; «поддержка» — статья из раздела Troubleshoot; «tuning» — «Tuning IIS 10.0»; «HTTP API» — документация HTTP Server API.
- **[MS TechCommunity]** — блог службы поддержки IIS Microsoft (techcommunity.microsoft.com): официальный автор, но не справочник.
- **[ИТС-адм разд. N]** — «Руководство администратора» 1С 8.3.27; **[ИТС-адм прил. N]** — приложения к нему; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС с годом.
- **[сторонний]** — официальные страницы сторонних продуктов (Grafana и др.) и статьи этой базы о сервисах.
- **[практика]** — устоявшаяся практика администрирования; в первоисточнике в таком виде не описана, проверять на стенде.
- **⚠** — утверждение не подтверждено первоисточником или документы расходятся (пояснение рядом). Полный список — «Что не удалось подтвердить».
- Условные обозначения: `web1c.corp.local` — Windows-хост с IIS и публикацией 1С (как в `../1c-windows/03-…`); `rp-iis.corp.local` — IIS с ARR, работающий обратным прокси (например, в DMZ); `srv-1c-app` — сервер 1С пользователя на Ubuntu с Apache и публикацией `demo`; `srv-obs`, `srv-itsm` — серверы наблюдаемости и учёта (как в `../apache/03-…`); `1C-<версия>` — пул приложений публикации; `Default Web Site` — сайт с идентификатором 1 (`W3SVC1`).
- Команды выполняются **в консоли PowerShell или cmd, запущенной от имени администратора**. `appcmd.exe` лежит в `%windir%\system32\inetsrv\` и в `PATH` не входит — пишите полный путь или перейдите в этот каталог. Изменения через `appcmd … /commit:apphost` пишутся в `%windir%\system32\inetsrv\config\applicationHost.config` [MS Learn].
- **Перед любой серией правок** — резервная копия конфигурации: `appcmd add backup before-tuning`; список — `appcmd list backups`; откат — `appcmd restore backup "before-tuning"` (восстановление останавливает сервер и возвращает глобальную конфигурацию) [MS Learn, appcmd]. Командлеты-аналоги — `Backup-WebConfiguration` / `Restore-WebConfiguration` (модуль `WebAdministration`) [MS Learn].

Смежные статьи (их тему здесь не повторяю):

- `iis/01-ustrojstvo-ustanovka-sajty-puly.md` — устройство IIS, установка ролей, сайты, привязки, пулы и удостоверения, `applicationHost.config`, делегирование конфигурации;
- `iis/02-https-autentifikaciya-bezopasnost.md` — TLS и сертификаты, Schannel, HSTS, HTTP/2 по привязкам, аутентификация (Windows, Kerberos, Basic), фильтрация запросов, ограничения по IP, заголовки безопасности;
- `../1c-windows/03-veb-publikaciya-iis.md` — публикация 1С: модуль, `webinst`, `default.vrd`, пул для версии платформы, лимиты `requestLimits`, `UrlSegmentMaxLength`, коды ответа в контексте публикации;
- `../1c-windows/04-domen-kerberos-klienty-terminalnyj-server.md` — SPN и делегирование (важно, если перед публикацией с проверкой подлинности Windows стоит прокси);
- `../1c-windows/05-licenzii-diagnostika-otlichiya-ot-linux.md` — технологический журнал, дампы (`ProcDump`, `LocalDumps`), сборщики `logman` для сервера 1С;
- `../1c-windows/06-windows-server-dlya-administratora-1c.md` — версии и сроки поддержки Windows Server, TCP-стек, электропитание, антивирус, журналы событий;
- `../apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md` — то же для Apache на Ubuntu (сравнение подходов, настройки сервисов за прокси);
- `../guides/04-1c-server-vzaimodejstviya.md` — сервер взаимодействия 1С (WebSocket, публикация через обратный прокси).

## Кратко — главные факты

1. **Путь запроса:** http.sys (ядро) принимает соединение, разбирает запрос, проверяет свои лимиты и ставит запрос в очередь пула; `w3wp.exe` пула прогоняет его через модули до обработчика (у публикации 1С — ISAPI `wsisapi.dll`); готовый ответ может отдать и кеш ядра [MS Learn, tuning]. Отказы http.sys в журнал сайта **не попадают** — только в HTTPERR [MS Learn, HTTP API].
2. **Три разных «503»:** переполнена очередь пула (`queueLength`, `1000`) — HTTPERR `QueueFull`; превышен `appConcurrentRequestLimit` (`5000`) — 503.2; пул остановлен или отключён защитой от сбоев — 503.0, HTTPERR `AppOffline` [MS Learn].
3. **Защита от частых сбоев:** 5 сбоев за 5 минут — пул отключается до ручного запуска [MS Learn]. События WAS в журнале «Система»: **5002** — пул отключён после серии сбоев, **5011** — процесс упал, **5010** — не ответил на проверку связи, **5013** — не уложился в `shutdownTimeLimit` [MS Learn; MS TechCommunity].
4. **Рабочие процессы для 1С:** файловая база — строго 1 [ИТС-адм разд. 8.2, 8.10.2.2]; клиент-серверная на 8.3.26+ — ~1 на 100 сеансов [ИТС-мет 6034, 2025]; каждый `w3wp` держит свой экземпляр расширения 1С [ИТС-адм разд. 8.2].
5. **Переработка по умолчанию** — каждые 29 ч, с перекрытием; старому процессу дают 90 с (`shutdownTimeLimit`), дольше — вызов обрывается; простой — 20 мин [MS Learn]. Для 1С — ночное расписание, `idleTimeout=0`, `AlwaysRunning` [практика; `iis/01-…`, разд. 7].
6. **Таймауты соединений:** `connectionTimeout` 2 мин (простой, ожидание тела, ожидание в очереди), `headerWaitTimeout` `00:00:00`, `minBytesPerSecond` 240 байт/с, keep-alive включён [MS Learn]. Время выполнения ISAPI-запроса IIS не ограничивает — ограничивают прокси и клиенты [практика ⚠].
7. **Реестр http.sys:** `MaxFieldLength`/`MaxRequestBytes` 16 384, `UrlSegmentMaxLength` 260, `UrlSegmentMaxCount` 255; применяются после `net stop http` / `net start http` с зависимыми службами IIS [MS Learn] или перезагрузки [ИТС-адм разд. 8.10.2.4].
8. **Сжатие:** статическое ставится по умолчанию, динамическое — компонент `Web-Dyn-Compression`; атрибуты `<httpCompression>` — только уровень сервера; динамическое отключается при ЦП > 90 % [MS Learn]. Тонкий клиент 1С сжимает трафик сам (`/TComp`, по умолчанию Zstandard) [ИТС-адм прил. 7] — второй раз сжимать незачем [практика].
9. **Кеширование:** кеш ядра не хранит ответы на запросы с аутентификацией, со строкой запроса, с телом, динамически сжатые и больше 256 КБ [MS Learn]. Профилей кеша вывода для публикации 1С не создавать [практика].
10. **ARR — прокси поверх URL Rewrite** (ставить URL Rewrite первым); прокси включается на уровне сервера (`system.webServer/proxy`). Таймаут свой у серверного прокси («Server Proxy Settings», по умолчанию **120 с**) и у каждой фермы (настройки «Proxy» фермы, по умолчанию **30 с**); истёк — **502.3**, `sc-win32-status` **12002** [MS Learn; раздел 7.3]. Для 1С таймаут поднимать.
11. **1С за обратным прокси** требует `X-Forwarded-For/Host/Proto/Port` [ИТС-адм разд. 8.10.3]: `X-Forwarded-For` ARR ставит сам, остальное — серверные переменные URL Rewrite `HTTP_X_FORWARDED_*`, разрешённые в `allowedServerVariables` [MS Learn; схема — практика].
12. **`preserveHostHeader`** — серверный параметр ARR, передаёт бэкенду исходный `Host`; без него Grafana новее 8.3.5 пишет «origin not allowed» [сторонний: Grafana].
13. **WebSocket:** компонент `Web-WebSockets`, секция `<webSocket>` (`receiveBufferLimit` 4 МБ, `pingInterval` 0) [MS Learn]; ARR 3.0 проксирует WebSocket, 502.5 — «WebSocket failure (ARR)» [MS Learn; сторонний].
14. **Журнал сайта:** `%SystemDrive%\inetpub\logs\LogFiles\W3SVC<id>\u_exГГММДД.log`, ежедневно, время UTC; по умолчанию нет `sc-bytes`, `cs-bytes`, `cs-host`, `cs-version` — включить [MS Learn]. `time-taken` — мс от первого байта запроса до последней отправки.
15. **Свои поля журнала** (IIS 8.5+) — заголовки и серверные переменные, например `X-Forwarded-For` на бэкенде; такие файлы получают суффикс `_x` [MS Learn].
16. **HTTPERR:** `%SystemRoot%\System32\LogFiles\HTTPERR\httperr<N>.log`, по 1 МБ; причина — последнее поле (`QueueFull`, `Timer_ConnectionIdle`, `Connection_Dropped`, `FieldLength`…) [MS Learn].
17. **FREB:** компонент `Web-Http-Tracing`; включается на сайте и правилом (коды, `timeTaken`); файлы `fr######.xml` + `freb.xsl`, по умолчанию 50 на сайт [MS Learn].
18. **Счётчики:** `HTTP Service Request Queues` (`CurrentQueueSize`, `RejectedRequests`), `APP_POOL_WAS` (`Current Application Pool State`, `…Uptime`), `Process(w3wp*)` [MS TechCommunity]; ARR — `Application Request Routing Server` [MS Learn].
19. **Что выполняется сейчас:** `appcmd list requests`, `Get-WebRequest`, «Рабочие процессы» в диспетчере (нужен `Web-Request-Monitor`), очереди ядра — `netsh http show servicestate view=requestq` [MS Learn].
20. **Порядок диагностики:** HTTPERR → журнал сайта (статус.подстатус, win32, `time-taken`) → события WAS и Application → FREB → дампы `w3wp` → технологический журнал 1С (раздел 14). Коды с подстатусами — раздел 13.

---

## 1. Как IIS обрабатывает запрос и где что ограничивается

### 1.1. Звенья

| Звено | Что делает | Что ограничивает (главное) | Где видно отказ |
|---|---|---|---|
| TCP и TLS (Schannel) | соединение, рукопожатие | протоколы, шифры — `iis/02-…` | журнал «Система» (Schannel), сетевой трассировщик |
| http.sys: разбор | читает строку запроса и заголовки | `MaxFieldLength`, `MaxRequestBytes`, `UrlSegmentMaxLength`, `UrlSegmentMaxCount` (реестр, раздел 4) | **HTTPERR** (`FieldLength`, `RequestLength`, `URL_Length`, `BadRequest`), клиент видит 400 |
| http.sys: таймеры | следит за простоем и скоростью | `connectionTimeout`, `headerWaitTimeout`, `minBytesPerSecond` (раздел 3) | **HTTPERR** (`Timer_*`), клиент — обрыв |
| http.sys: кеш ядра | отдаёт готовые ответы | `UriEnableCache`, `UriMaxUriBytes`, `<caching enableKernelCache>` (раздел 6) | `netsh http show cachestate` |
| http.sys: очередь пула | ждёт, пока `w3wp` заберёт запрос | `queueLength` пула, `maxConnections` сайта | **HTTPERR** (`QueueFull`, `ConnLimit`, `AppOffline`, `Disabled`), клиент — 503 |
| WAS / W3SVC | запускают и контролируют `w3wp` | `processModel`, `recycling`, `failure`, `cpu` (раздел 2) | журнал «Система», источник WAS |
| `w3wp`: модули | фильтрация, аутентификация, переписывание URL, сжатие, кеш вывода | `requestFiltering`, `serverRuntime`, `rewrite`, `httpCompression`, `caching` | **журнал сайта** (статус.подстатус), FREB |
| `w3wp`: обработчик | ISAPI 1С, статика, ARR | у ISAPI своего таймаута выполнения нет [практика ⚠]; у ARR — таймаут прокси | журнал сайта, FREB, журнал «Приложение» (падения) |

Отсюда правило: **если запроса нет в журнале сайта — смотрите HTTPERR**; если пул «молчит» — журнал «Система» [MS Learn, поддержка; практика].

### 1.2. Где лежат журналы (по умолчанию)

| Журнал | Путь | Источник |
|---|---|---|
| Журнал сайта (W3C) | `%SystemDrive%\inetpub\logs\LogFiles\W3SVC<id сайта>\u_exГГММДД.log` | [MS Learn, справочник `logFile`; поддержка] |
| HTTPERR (http.sys) | `%SystemRoot%\System32\LogFiles\HTTPERR\httperr<N>.log` | [MS Learn, HTTP API] |
| FREB | `%SystemDrive%\inetpub\logs\FailedReqLogFiles\W3SVC<id>\fr######.xml` + `freb.xsl` | [MS Learn] |
| Конфигурация | `%windir%\system32\inetsrv\config\applicationHost.config`, `web.config` приложений | [MS Learn] |
| Резервные копии `appcmd` | `%windir%\system32\inetsrv\backup\<имя>` | [MS Learn, поддержка FREB] |
| События | «Система» (WAS, http.sys, Schannel), «Приложение» (Application Error для `w3wp.exe`), журналы конфигурации IIS ⚠ | раздел 11 |

ИТС требует, чтобы на веб-серверах продукционного контура собирались журналы доступа и ошибок IIS [ИТС-мет 5899, 2016] — на IIS это журнал сайта и HTTPERR.

### 1.3. Версии IIS 10.0

Номер IIS во всех Windows Server с 2016 по 2025 — 10.0; что менялось внутри IIS 10.0 по выпускам — `iis/01-…`, разд. 1.1. Для этой статьи важно [MS Learn]: HTTP/2 в http.sys (с Windows Server 2016, только поверх TLS) и модуль `IISAdministration`; атрибут FREB `traceAllAfterTimeout` (IIS 10.0); серверные переменные с протоколом и шифром TLS для журнала (версия 1709); приоритет схем сжатия по порядку `<scheme>` (1803); новый API сжатия для потоковых данных (1809, Windows Server 2019). «Tuning IIS 10.0» отмечает, что в Windows Server 2022 http.sys сам управляет соединениями и часть параметров реестра больше не используется (раздел 4.1). Страницы «что нового в IIS» для Windows Server 2025 нет ⚠. Сроки поддержки Windows Server и выбор ОС под 1С — `../1c-windows/06-…`, разд. 1.1.

---

## 2. Пул приложений под нагрузкой

Все атрибуты пулов с умолчаниями, удостоверение, предзагрузка и готовый профиль пула для публикации 1С (тремя способами — `appcmd`, `WebAdministration`, `IISAdministration`) — в `iis/01-…`, разд. 7.3–7.9. Здесь — только то, что определяет отказы и задержки под нагрузкой.

### 2.1. Очередь пула и ограничение одновременных запросов

| Атрибут | Элемент | Умолчание | Что происходит при превышении |
|---|---|---|---|
| `queueLength` | `applicationPools/add` | `1000` | http.sys отвечает 503 на новые запросы; HTTPERR `QueueFull` [MS Learn] |
| `loadBalancerCapabilities` | `add/failure` | `HttpLevel` | `HttpLevel` — ответ 503; `TcpLevel` — разрыв TCP вместо 503 (балансировщик уровня TCP увидит «узел недоступен» и уведёт трафик) [MS Learn] |
| `appConcurrentRequestLimit` | `system.webServer/serverRuntime` | `5000` | 503.2 «Concurrent request limit exceeded» [MS Learn] |
| `maxConnections` | `sites/site/limits` | `4294967295` | 503, HTTPERR `ConnLimit` [MS Learn] |

- Очередь растёт, когда `w3wp` не успевает забирать запросы: потоки IIS заняты долгими вызовами (у публикации 1С — ожиданием кластера 1С), процесс перезапускается или завис. Microsoft советует увеличивать `queueLength` для приложений с медленным бэкендом, если видны 503 [MS Learn, tuning]; но это отсрочка — сначала ищите, почему запросы долго выполняются [практика].
- `TcpLevel` нужен за L4-балансировщиком: 503 от «живого» узла он считает нормальным ответом [MS Learn].
- Очереди http.sys по пулам видны в `netsh http show servicestate view=requestq` [MS Learn, netsh; состав вывода ⚠ — смотреть на своём сервере] и в счётчике `HTTP Service Request Queues\CurrentQueueSize` (раздел 12).

```bat
cd /d %windir%\system32\inetsrv
appcmd set apppool "1C-<версия>" /queueLength:2000
appcmd set apppool "1C-<версия>" /failure.loadBalancerCapabilities:TcpLevel
appcmd list apppool "1C-<версия>" /text:*
```

Форма `appcmd set apppool "<пул>" /<атрибут>:<значение>` и точечная нотация дочерних элементов — по образцам Microsoft (`/processModel.shutdownTimeLimit:00:00:30`) [MS Learn, справочник `processModel`]. `TcpLevel` включайте, только если перед IIS действительно стоит L4-балансировщик [практика].

### 2.2. Сколько рабочих процессов

`processModel.maxProcesses`: `1` (умолчание) — один процесс; `2` и больше — **веб-сад**; `0` — по числу узлов NUMA (IIS 8.0+) [MS Learn].

| Публикация 1С | Процессов в пуле | Источник |
|---|---|---|
| Файловая база | строго **1**: файл базы обслуживает само расширение, каждый процесс — свой экземпляр; при фоновых заданиях иначе нельзя | [ИТС-адм разд. 8.2, 8.10.2.2] |
| Клиент-серверная, 8.3.26 и новее | **~1 на 100 одновременных сеансов** через публикацию (1000 сеансов — 10) — против кратковременных зависаний | [ИТС-мет 6034, 2025] |
| Клиент-серверная, до 8.3.26 | официальной рекомендации нет; обычно 1–2 | [практика ⚠] |

- Каждый `w3wp` держит свой экземпляр расширения 1С и свои соединения с кластером [ИТС-адм разд. 8.2]: память хоста ≈ число процессов × `Private Bytes` одного `w3wp` под нагрузкой (раздел 12) [практика].
- Как http.sys распределяет запросы между процессами веб-сада, документация не описывает ⚠; веб-сад или несколько пулов для групп пользователей — сравнение способов в `iis/01-…`, разд. 7.7.
- Привязка процессов к узлам NUMA — атрибуты `cpu` (`numaNodeAssignment`, `numaNodeAffinityMode`); распределение потоков пула по ЦП (`ThreadPoolUseIdealCpu`) — раздел 4.3 [MS Learn].

```bat
:: клиент-серверная база 8.3.26+, ~400 одновременных сеансов через IIS
appcmd set apppool "1C-<версия>" /processModel.maxProcesses:4
:: сколько w3wp сейчас у пула (процессы появляются по мере нагрузки)
appcmd list wps /apppool.name:"1C-<версия>"
```

### 2.3. Переработка, простой и длинные операции

Умолчания [MS Learn, справочник]: переработка каждые 29 ч (`periodicRestart time="29:00:00"`), остановка простаивающего процесса через 20 мин (`idleTimeout`), запуск по первому запросу (`startMode="OnDemand"`). Переработка идёт **с перекрытием** (`disallowOverlappingRotation=false`): новые запросы — в новый `w3wp`, старый дорабатывает текущие не дольше `shutdownTimeLimit` (90 с) и убивается — событие WAS **5013** [MS Learn, поддержка KB 2634635]. Процесс, не стартовавший за `startupTimeLimit` (90 с), убивается, и это **засчитывается как сбой** для защиты от частых сбоев [MS Learn].

Следствия для 1С [практика, если не сказано иное]:

- сеанс клиент-серверной базы живёт в кластере и переработкой не теряется, но **вызов дольше 90 с** в старом процессе оборвётся; 29 ч не кратны суткам, и переработка «уплывает» на рабочий день — отсюда `time=00:00:00` + ночное `schedule`, `idleTimeout=00:00:00`, `AlwaysRunning` (команды — `iis/01-…`, разд. 7.5, 7.8);
- **пул файловой базы** — ещё и `disallowOverlappingRotation=true`: при перекрытии на короткое время работают два процесса, а ИТС требует один процесс на файловую публикацию [ИТС-адм разд. 8.2, 8.10.2.2]. Уточнено 20.10.2026 по справочнику `recycling` [MS Learn]: Microsoft сама советует `true`, если код в рабочем процессе не поддерживает несколько рабочих процессов;
- лимиты памяти (`memory`, `privateMemory`) — только при наблюдаемом росте `Private Bytes`, а не «на всякий случай»;
- в IIS 10.0 `logEventOnRecycle` по умолчанию пишет **все** причины переработки (`Time, Requests, Schedule, Memory, IsapiUnhealthy, OnDemand, ConfigChange, PrivateMemory`; до IIS 10 — только `Time, Memory, PrivateMemory`) [MS Learn]: по событиям видно, почему оборвалась длинная операция.

```bat
appcmd set apppool "1C-file-<версия>" /recycling.disallowOverlappingRotation:true
:: ручная переработка (или Restart-WebAppPool -Name "1C-<версия>")
appcmd recycle apppool "1C-<версия>"
```

### 2.4. Проверка работоспособности, защита от сбоев, восстановление

| Механизм | Атрибуты и умолчания [MS Learn] | Что видно |
|---|---|---|
| Проверка связи | `pingingEnabled=true`, `pingInterval=00:00:30`, `pingResponseTime=00:01:30` | не ответил — процесс завершается, событие WAS **5010** [MS TechCommunity] |
| Защита от частых сбоев | `rapidFailProtection=true`, `rapidFailProtectionMaxCrashes=5`, `rapidFailProtectionInterval=00:05:00` | пул отключён — событие **5002**, ответы **503.0**, HTTPERR `AppOffline` |
| Отладка упавшего процесса | `orphanWorkerProcess=false`, `orphanActionExe`/`orphanActionParams` (`%1%` — PID) | `true` — «больной» процесс не убивается, а остаётся для отладчика |
| Действие при остановке пула | `autoShutdownExe`, `autoShutdownParams` | запуск своей программы (оповещение) |

- **Снятие дампа зависшего `w3wp`** может закончиться тем, что WAS убьёт процесс по таймауту проверки связи — пока отладчик держит процесс, тот не отвечает [MS TechCommunity, IIS Support Blog]. На время дампа — `pingingEnabled=false` у этого пула, потом вернуть [практика по тому же блогу ⚠].
- **Пул, отключённый защитой, сам не поднимется**: устранить причину (у 1С обычно разрядность модуля или две версии модуля в одном пуле — `../1c-windows/03-…`, разд. 3.2–3.3 [ИТС-адм разд. 8.10.2.1, 8.10.2.2]) и запустить вручную.
- Отключать `rapidFailProtection`, «чтобы не останавливалось», не нужно: модуль продолжит падать, а сигнал пропадёт; за балансировщиком лучше `TcpLevel` (раздел 2.1) [практика].

```powershell
Get-IISAppPool                                  # таблица: Name, Status, CLR Ver, Pipeline Mode, Start Mode (образец MS)
Get-WebAppPoolState -Name "1C-8.3.27.2074"      # Started / Stopped
Start-WebAppPool -Name "1C-8.3.27.2074"
```

```bat
:: только на время снятия дампа, затем вернуть true
appcmd set apppool "1C-<версия>" /processModel.pingingEnabled:false
```

### 2.5. Ограничение ЦП

Элемент `cpu` [MS Learn]: `limit` в **тысячных долях процента** (`0` — выключено; в диспетчере IIS 8.5+ — в процентах), `action` — `NoAction` (только событие, по умолчанию), `KillW3wp`, `Throttle`, `ThrottleUnderLoad` (два последних — IIS 8.0+), `resetInterval` — `00:05:00`. Полезно, когда на одном IIS публикации 1С и «тяжёлый» внутренний сервис: его пулу — `ThrottleUnderLoad` [практика]. Пулам 1С ограничение обычно не ставят: при `KillW3wp` пострадают все сеансы процесса [практика].

```bat
:: 30 % ЦП, ограничивать только под нагрузкой
appcmd set apppool "svc-pool" /cpu.limit:30000 /cpu.action:ThrottleUnderLoad
appcmd list apppool "svc-pool" /text:* | findstr /i cpu
```

Несколько атрибутов в одной команде `set` допустимы [MS Learn, appcmd]. Уточнено 20.10.2026 по справочнику `cpu` [MS Learn]: образец Microsoft для `cpu.*` записан через `set config` — `appcmd set config -section:system.applicationHost/applicationPools /[name='DefaultAppPool'].cpu.action:"KillW3wp" /commit:apphost`; форма `set apppool … /cpu.limit:` — та же точечная нотация, что в образце `processModel.*`.

---

## 3. Соединения, keep-alive и таймауты

### 3.1. Параметры

| Атрибут | Элемент | Умолчание | Смысл [MS Learn, справочник] |
|---|---|---|---|
| `connectionTimeout` | `webLimits` (сервер), `sites/site/limits` и `siteDefaults/limits` (сайт) | `00:02:00` | разрыв «неактивного» соединения: сработал таймер http.sys `Timer_ConnectionIdle` (простой), `Timer_EntityBody` (тело не приходит; перезапускается на каждой порции данных) или `Timer_AppPool` (запрос слишком долго в очереди пула) |
| `headerWaitTimeout` | `webLimits` | `00:00:00` | сколько ждать все заголовки; защита от атак «медленными заголовками» |
| `minBytesPerSecond` | `webLimits` | `240` | минимальная скорость **отправки ответа**; рвёт, если ответ не ушёл за «размер / 240 байт/с» |
| `maxGlobalBandWidth` / `maxBandwidth` | `webLimits` / `sites/site/limits` | `4294967295` | предел полосы сервера / сайта |
| `maxConnections` | `sites/site/limits` | `4294967295` | предел соединений сайта |
| `maxUrlSegments` | `sites/site/limits` (IIS 8.0+) | `32` | сегментов URL; превышение — вероятно, 404.20 «Too Many URL Segments» ⚠ (связь в документации не указана) |
| `allowKeepAlive` | `system.webServer/httpProtocol` | `true` | постоянные соединения |
| `enableNagling` | `system.webServer/serverRuntime` | `false` | алгоритм Нейгла |
| `uploadReadAheadSize` | `serverRuntime` | `49152` | сколько байт тела IIS буферизует и передаёт ISAPI-расширению или модулю; остальное расширение читает само |
| `maxRequestEntityAllowed` | `serverRuntime` | `4294967295` | предел тела по `Content-Length`; превышение — 403 по справочнику |
| `demandStartThreshold`, `dynamicRegistrationThreshold` | `webLimits` | `2147483647`, `100` (IIS 8.5+) | предел числа рабочих процессов на сервере; сайтов больше порога — активация по первому запросу |

**Расхождение** ⚠: документация HTTP Server API описывает `Timer_MinBytesPerSecond` как «по умолчанию 150 байт/с», `Timer_HeaderWait` — «по умолчанию 2 минуты» [MS Learn, HTTP API], справочник IIS — `minBytesPerSecond=240`, `headerWaitTimeout=00:00:00`. Вероятно, первое — умолчания самого http.sys, второе — значения IIS для своих сайтов; действует ли при `00:00:00` умолчание http.sys, не сказано. Фактические значения — `netsh http show timeout` и `netsh http show servicestate view=session verbose=yes` [MS Learn, netsh; состав вывода ⚠].

### 3.2. Что это значит для 1С и сервисов

- **Длинные операции 1С** (отчёт в веб-клиенте, синхронный вызов HTTP-сервиса) `connectionTimeout` не обрывает: пока `w3wp` обрабатывает запрос, соединение не «простаивает» [практика ⚠]. Обрывают их прокси (таймаут ARR: у серверного прокси по умолчанию 120 с, у фермы — 30 с, раздел 7.3), балансировщики, клиенты и переработка пула (раздел 2.3).
- **Медленная загрузка** (`ПоместитьФайл`, POST в HTTP-сервис через медленный канал): пауза в передаче тела дольше `connectionTimeout` — разрыв, `Timer_EntityBody` в HTTPERR [MS Learn]. При реальных паузах (VPN, мобильные клиенты) — `connectionTimeout` сайта 5–10 мин [практика].
- **Медленное скачивание** ниже 240 байт/с оборвёт `minBytesPerSecond` (`Timer_MinBytesPerSecond`) [MS Learn]; в интернете ставить `0` не рекомендую — защита от «медленных клиентов» [практика].
- **Публикация в интернет:** `headerWaitTimeout` 30 с — так в образце Microsoft [MS Learn]; остальная защита — `iis/02-…`.
- **Keep-alive не выключать:** иначе каждый запрос — новое соединение и, при HTTPS, новое рукопожатие TLS; Microsoft отдельно советует keep-alive для TLS [MS Learn, tuning].

```bat
cd /d %windir%\system32\inetsrv
appcmd set config -section:system.applicationHost/webLimits /headerWaitTimeout:"00:00:30" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].limits.connectionTimeout:00:05:00" /commit:apphost
:: проверка, включая умолчания
appcmd list config -section:system.applicationHost/webLimits /config:*
appcmd list config -section:system.applicationHost/sites /config:* | findstr /i "connectionTimeout maxConnections maxUrlSegments"
```

Синтаксис — по образцам справочника (`webLimits`, `sites/site/limits`) и `appcmd list config … /config:*` [MS Learn].

### 3.3. Глобальные таймауты http.sys (`netsh http`)

`netsh http add timeout timeouttype=idleconnectiontimeout|headerwaittimeout value=<секунды>` — **глобальные** таймауты службы HTTP; `netsh http show timeout` — показать; `netsh http delete timeout timeouttype=…` — вернуть умолчание [MS Learn, `netsh http`]. Для сайтов IIS действуют значения из конфигурации IIS (3.1); как они сочетаются с глобальными, документация не описывает ⚠ — меняйте таймауты в IIS, а `netsh http show timeout` используйте для проверки.

---

## 4. http.sys: параметры реестра

### 4.1. Таблица

Раздел `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\HTTP\Parameters`, значения типа DWORD [MS Learn, поддержка «Http.sys registry settings for Windows»]. «Риск» — код предупреждения Microsoft: 0 — без риска; 1 — опасно (больше памяти, уязвимее к атакам); 2 — малое значение чаще сбрасывает кеш; 3 — малое значение замедляет статику.

| Параметр | Умолчание | Диапазон | Смысл | Риск |
|---|---|---|---|---|
| `MaxFieldLength` | 16384 | 64–65534 | предел одного заголовка (≈32 тыс. символов URL) | 1 |
| `MaxRequestBytes` | 16384 | 256–16777216 | предел строки запроса + всех заголовков; если меньше `MaxFieldLength`, тот уменьшается | 1 |
| `UrlSegmentMaxLength` | 260 | 0–32766 | символов в **одном сегменте** пути (между `/`); 0 — до максимума `ULONG` | 1 |
| `UrlSegmentMaxCount` | 255 | 0–16383 | число сегментов пути | 1 |
| `MaxConnections` | MAX_ULONG | 1024–2031616 | переопределяет расчёт числа соединений | 1 |
| `MaxEndpoints` | 0 | 0–1024 | предел объектов конечных точек (0 — по памяти) | 1 |
| `EnableAggressiveMemoryUsage` | 0 | 0/1 | служба HTTP перестаёт принимать соединения при свободном невыгружаемом пуле меньше 20 МБ; с `1` — меньше 8 МБ; может уменьшить `Connections_refused` и 503 в HTTPERR | 0 |
| `MaxBytesPerSend` | 65536 | 1–0xFFFFF | переопределяет окно TCP, которым пользуется http.sys; больше — быстрее скачивание на «длинных толстых» каналах | 0 |
| `UriEnableCache` | 1 | 0/1 | кеш ответов и фрагментов в ядре | 0 |
| `UriMaxUriBytes` | 262144 | 4096–16777216 | ответы больше — не кешируются в ядре | 1, 3 |
| `UriScavengerPeriod` | 120 с | 10–0xFFFFFFFF | период очистки кеша от неиспользуемых записей | 1, 2 |
| `DisableServerHeader` | 0 | 0–2 | заголовок `Server`: 1 — не добавлять в ответы самого http.sys (400, 503…); 2 — не добавлять вообще (`iis/02-…`) | 0 |
| `AllowRestrictedChars`, `EnableNonUTF8`, `FavorUTF8`, `PercentUAllowed` | 0, 1, 1, 1 | логич. | разбор экранированных символов и кодировок URL | 0 |

Дополнительно [MS Learn]:

- `UriMaxCacheMegabyteCount` (по умолчанию 0 — размер кеша ядра подбирается автоматически) [MS Learn, tuning];
- в разделе `…\Services\HTTPFilter\Parameters` — `CertChainCacheOnlyUrlRetrieval` (1): при клиентских сертификатах подсказки AIA при построении цепочки не используются; `0` — использовать [MS Learn, поддержка];
- параметры журнала ошибок `EnableErrorLogging`, `ErrorLogFileTruncateSize`, `ErrorLoggingDir` — раздел 9 [MS Learn, HTTP API];
- для ISAPI- и CGI-приложений с медленной отправкой ответа статья упоминает `MaxBufferedSendBytes` без умолчаний и диапазона ⚠ [MS Learn, поддержка].

**Расхождение** ⚠: статья «Http.sys registry settings» (2020) приводит `MaxConnections`, а «Tuning IIS 10.0» говорит, что в Windows Server 2022 http.sys управляет соединениями сам и `MaxConnections`, `IdleConnectionsHighMark`, `IdleConnectionsLowMark`, `IdleListTrimmerPeriod`, `RequestBufferLookasideDepth`, `InternalRequestLookasideDepth` **больше не используются** [MS Learn, tuning]. На Windows Server 2016–2025 `MaxConnections` не трогать.

### 4.2. Как менять

```powershell
# 1. Копия ветки
reg export "HKLM\SYSTEM\CurrentControlSet\Services\HTTP\Parameters" C:\Backup\http-params.reg
# 2. Значение (пример: сегмент URL для OData — подробно ../1c-windows/03-…, разд. 8.2)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\HTTP\Parameters" -Name UrlSegmentMaxLength -PropertyType DWord -Value 4096 -Force
# 3. Проверка записи
Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\HTTP\Parameters" | Select-Object UrlSegmentMaxLength, MaxFieldLength, MaxRequestBytes
```

Применение [MS Learn, поддержка]: изменения действуют после перезапуска службы HTTP — `net stop http`, `net start http`; при этом останавливаются зависимые службы (W3SVC, WAS и др.), их потом нужно запустить (`net start w3svc`). Статья предлагает также `net stop iisadmin /y` — служба IIS Admin есть только при установленной совместимости с IIS 6 ⚠. ИТС для `UrlSegmentMaxLength` пишет «перезагрузить компьютер» [ИТС-адм разд. 8.10.2.4] — самый надёжный вариант в окно обслуживания. Перезапуск службы HTTP рвёт все HTTP-соединения хоста, включая WinRM и другие службы на http.sys [практика].

```bat
:: в окно обслуживания, от администратора
net stop http /y
net start w3svc
:: проверка
sc query http | findstr STATE
sc query w3svc | findstr STATE
```

Ключ `/y` у `net stop` (подтвердить остановку зависимых служб) — [практика ⚠].

### 4.3. Для каких задач какой параметр

| Симптом | Параметр | Где подробно |
|---|---|---|
| 400 у части пользователей с проверкой подлинности Windows (много групп в AD) — «Request Header Too Long» | `MaxFieldLength`, `MaxRequestBytes` | `iis/02-…`; `../1c-windows/03-…`, разд. 10.6 |
| 400 на длинных ключах OData (`Catalog_…(guid'…')` — один длинный сегмент) | `UrlSegmentMaxLength` | `../1c-windows/03-…`, разд. 8.2 [ИТС-адм разд. 8.10.2.4] |
| Медленная отдача больших ответов на каналах с большой задержкой | `MaxBytesPerSend` | [MS Learn] |
| 503 и отказы соединений при нехватке невыгружаемого пула | `EnableAggressiveMemoryUsage` | [MS Learn] |

Распределение потоков пула IIS по ЦП на NUMA: `HKLM\System\CurrentControlSet\Services\InetInfo\Parameters\ThreadPoolUseIdealCpu` — включено по умолчанию с Windows Server 2016, Microsoft советует не менять [MS Learn, tuning].

---

## 5. Сжатие

### 5.1. Компоненты и как устроено

| Компонент | `Install-WindowsFeature` | DISM | По умолчанию с ролью |
|---|---|---|---|
| Сжатие статического содержимого | `Web-Stat-Compression` | `IIS-HttpCompressionStatic` | да |
| Сжатие динамического содержимого | `Web-Dyn-Compression` | `IIS-HttpCompressionDynamic` | нет |

Имена — из таблицы компонентов IIS 8.5 [MS Learn]; в IIS 10.0 те же ⚠ (сверьте `Get-WindowsFeature Web-*Compression`).

- Модули `StaticCompressionModule` и `DynamicCompressionModule` вызывают **схему сжатия** — библиотеку, зарегистрированную в `<httpCompression><scheme>`. Встроенная схема `gzip` — `%Windir%\system32\inetsrv\gzip.dll` (умеет gzip и deflate) [MS Learn].
- Какие ответы сжимаются, решают **MIME-типы** в `<staticTypes>` и `<dynamicTypes>`; в образце конфигурации Microsoft это `text/*`, `message/*`, `application/javascript` и запрещающая запись `*/*` [MS Learn, справочник]. Редактировать списки в диспетчере IIS нельзя — только `appcmd`, редактор конфигурации или файл [MS Learn, поддержка].
- Включение для URL — `<urlCompression>`: `doStaticCompression=true`, `doDynamicCompression=true` (в IIS 7.5+), `dynamicCompressionBeforeCache=false` [MS Learn].
- Сжатые статические файлы кешируются на диске и в кеше ядра; динамические сжимаются на каждый ответ [MS Learn, tuning; справочник `scheme`].

### 5.2. Параметры `<httpCompression>` (только уровень сервера)

Атрибуты элемента действуют только в `applicationHost.config`; на уровне сайта и ниже игнорируются. `<dynamicTypes>` и `<staticTypes>` в IIS 10.0 можно задавать и на уровне сайта [MS Learn, справочник].

| Атрибут | Умолчание | Смысл |
|---|---|---|
| `directory` | `%SystemDrive%\inetpub\temp\IIS Temporary Compressed Files` | кеш сжатых статических файлов; при интенсивном доступе — вынести с системного диска [MS Learn, tuning]; каталог должен быть на NTFS, иначе статическое сжатие отключается [MS Learn] |
| `doDiskSpaceLimiting` / `maxDiskSpaceUsage` | `true` / `100` (МБ, на каждый пул) | при заполнении на 90 % удаляются давно не использованные файлы |
| `minFileSizeForComp` | `2700` (IIS 7.5+) | файлы меньше не сжимаются |
| `staticCompressionEnableCpuUsage` / `…DisableCpuUsage` | `50` / `100` | включить / выключить статическое сжатие по средней загрузке ЦП (считается раз в 30 с) |
| `dynamicCompressionEnableCpuUsage` / `…DisableCpuUsage` | `50` / `90` | то же для динамического |
| `dynamicCompressionBufferLimit` | `65536` | сколько сжатых данных копить перед отправкой клиенту (IIS 7.5+) |
| `noCompressionForHttp10` | `true` | не сжимать для HTTP/1.0 |
| `noCompressionForProxies` | `true` | не сжимать ответы HTTP/1.1 на запросы, пришедшие через прокси-серверы |
| `noCompressionForRange` | `true` | не сжимать ответы на запросы с `Range` |
| `staticCompressionIgnoreHitFrequency` | `false` | `true` — сжимать статику сразу, без порога «2 обращения за 10 с» (IIS 8.5+) |

Атрибуты `<scheme>`: `name`, `dll`, `doStaticCompression` (`true`), `doDynamicCompression` (`true`), `staticCompressionLevel` (`7`), `dynamicCompressionLevel` (`0`; шкала 0–10). Изменения `dll` и уровней требуют перезапуска службы WWW [MS Learn, справочник].

Порог «частоты обращений» для статики задают `serverRuntime` `frequentHitThreshold` (`2`) и `frequentHitTimePeriod` (`00:00:10`) [MS Learn]: первый запрос к файлу уходит несжатым — это нормально.

### 5.3. IIS Compression (Brotli и обновлённый gzip)

**IIS Compression** — две библиотеки-схемы от Microsoft: `iisbrotli.dll` (Brotli, кодировка `br`) и `iiszlib.dll` (gzip и deflate на zlib) [MS Learn]:

- устанавливается MSI (`iiscompression_amd64.msi`) при **остановленных** службах WAS и W3SVC; кладёт файлы в `%ProgramFiles%\IIS\IIS Compression`, регистрирует схему `br` и **заменяет** встроенную `gzip.dll` на `iiszlib.dll` [MS Learn];
- уровни у схем разные: `gzip.dll` — 0–10, `iiszlib.dll` — **0 = без сжатия**, 1–9, `iisbrotli.dll` — 0–11. Поскольку умолчание `dynamicCompressionLevel` = 0, **после установки IIS Compression динамическое сжатие gzip фактически выключено**, пока уровень не поднят [MS Learn];
- приоритет схем по порядку в коллекции `<scheme>` — с IIS 10.0 версии 1803; раньше выбор шёл по порядку в `Accept-Encoding` клиента [MS Learn];
- браузеры обычно предлагают `br` только по HTTPS [MS Learn].

### 5.4. Сжатие и 1С

| Трафик | Что делать | Почему |
|---|---|---|
| Тонкий клиент через веб-сервер | не сжимать в IIS | клиент и сервер 1С сжимают трафик сами: параметр запуска `/TComp` (`-None`, `-Deflate`, `-SDC`, `-lz4`, `-zstd`; по умолчанию Zstandard) [ИТС-адм прил. 7]; двойное сжатие тратит ЦП впустую [практика] |
| Веб-клиент: статика (JS, CSS, картинки модуля) | статическое сжатие оставить | ставится по умолчанию, ответы кешируются [MS Learn] |
| Веб-клиент и HTTP-сервисы: динамические ответы (HTML, JSON, XML) | включать только при свободном ЦП и медленных каналах; проверить на нагрузке | Microsoft: динамическое сжатие — для серверов с низкой средней загрузкой ЦП и больших ответов, сначала на тесте [MS Learn, tuning] |
| OData и выгрузки в BI | кандидат на динамическое сжатие (большие текстовые ответы) — отдельным пулом/публикацией | [практика] |
| За обратным прокси | сжимать **в одном звене** (обычно на внешнем прокси) | `noCompressionForProxies=true`; сжатое содержимое не переписывается outbound-правилами (раздел 7.2) [MS Learn; вывод — практика] |

Какие `Content-Type` у ответов тонкого клиента и веб-клиента, документация 1С не описывает ⚠ — посмотрите в FREB или в журнале браузера, прежде чем добавлять типы.

```bat
:: 1. Компонент (PowerShell): Install-WindowsFeature -Name Web-Dyn-Compression
cd /d %windir%\system32\inetsrv
:: 2. Текущие списки и параметры (с умолчаниями)
appcmd list config -section:system.webServer/httpCompression /config:*
:: 3. Добавить JSON в динамическое сжатие (уровень сервера)
appcmd set config -section:system.webServer/httpCompression /+"dynamicTypes.[mimeType='application/json',enabled='True']" /commit:apphost
:: 4. Выключить динамическое сжатие только у публикации тонкого клиента
appcmd set config "Default Web Site/demo" -section:system.webServer/urlCompression /doDynamicCompression:"False"
appcmd list config "Default Web Site/demo" -section:system.webServer/urlCompression
```

Синтаксис — по образцам Microsoft [MS Learn]; блокировка секции на уровне приложения — `iis/01-…` (делегирование). Проверка (Windows Server 2019+, где есть `curl.exe` [практика]): `curl.exe -s -o NUL -D - -H "Accept-Encoding: gzip, br" https://web1c.corp.local/demo/ru_RU/` — ищите `Content-Encoding`. Если сжатия нет: тип не в списке, ответ меньше `minFileSizeForComp`, статика не набрала «частоту», ЦП выше порога, запрос через прокси-сервер или с `Range`; причину покажет FREB с областью `Compression` (раздел 10) [MS Learn; практика].

---

## 6. Кеширование

### 6.1. Три кеша IIS

| Кеш | Где | Что кладётся | Управление |
|---|---|---|---|
| Кеш ядра http.sys | ядро | готовые ответы целиком (статика, а также помеченные кешируемыми динамические) | реестр `UriEnableCache`, `UriMaxUriBytes`, `UriScavengerPeriod`, `UriMaxCacheMegabyteCount`; `<caching enableKernelCache>`; профили `kernelCachePolicy` [MS Learn] |
| Кеш вывода (user mode) | `w3wp` | ответы по профилям `<caching><profiles>` | `<caching enabled maxCacheSize maxResponseSize>` [MS Learn] |
| Файловый кеш статики | `w3wp` (модуль `FileCacheModule`, `cachfile.dll`) | содержимое статических файлов | удалить модуль, чтобы выключить полностью [MS Learn, tuning] |

### 6.2. Когда http.sys **не** кеширует ответ

По статье поддержки [MS Learn, «Instances in which HTTP.sys doesn't cache content»]: запрос не анонимный или с заголовком `Authorization`; ответ динамически сжат (статическое сжатие совместимо); в запросе есть строка запроса или тело; есть `Range`/`If-Range`; версия HTTP не 1.0/1.1; ответ больше `UriMaxUriBytes` (256 КБ) или его заголовки больше 1024 байт; ответ пришёл несколькими вызовами отправки; кеш полон; ответ нулевой длины; включено сопоставление клиентских сертификатов или собственный модуль журнала; установлен ISAPI-**фильтр**, не поддерживающий кеш; статика открыта как документ по умолчанию (запрос `/`, а не `/default.htm`); файл на UNC-ресурсе без `DoDirMonitoringForUnc=1` (`HKLM\System\CurrentControlSet\Services\Inetinfo\Parameters`).

Вывод для 1С: ответы публикации с аутентификацией и строкой запроса в кеш ядра не попадают [вывод — практика]. Кешируется в основном статика сайта.

### 6.3. Кеш вывода и профили

`<system.webServer><caching>` [MS Learn, справочник]:

| Атрибут | Умолчание | Смысл |
|---|---|---|
| `enabled` | `true` | кеш вывода в `w3wp` |
| `enableKernelCache` | `true` | кеш ядра |
| `maxCacheSize` | `0` (подбирается) | размер кеша вывода, МБ — действует только в `applicationHost.config` |
| `maxResponseSize` | `262144` | максимальный кешируемый ответ, байт — только в `applicationHost.config` |

Профиль `<profiles><add>`: `extension` (обязательный), `policy` и `kernelCachePolicy` (`DontCache` по умолчанию, `CacheUntilChange`, `CacheForTimePeriod`, `DisableCache`), `duration` (`00:00:30`), `location` (`Server` по умолчанию; `Any`, `Client`, `Downstream`, `None`, `ServerAndClient`), `varyByHeaders`, `varyByQueryString` [MS Learn]. Кеш ядра не работает при включённой проверке подлинности Basic или Windows и не поддерживает `varyByQueryString` [MS Learn, walkthrough].

**Для публикаций 1С профилей не создавать** [практика]: ответы модуля 1С зависят от сеанса и пользователя, профиль по расширению (например, `.json`, `.xml`, `.html`) может отдать чужие данные другому пользователю. По умолчанию профилей нет — так и оставить. Если есть подозрение, что ответ 1С берётся из кеша, — FREB покажет событие `HTTPSYS_CACHEABLE` с причиной [MS Learn], а для публикации можно явно выключить оба кеша:

```bat
appcmd set config "Default Web Site/demo" -section:system.webServer/caching /enabled:"False" /enableKernelCache:"False"
appcmd list config "Default Web Site/demo" -section:system.webServer/caching
```

Необходимость этой меры для 1С не доказана ⚠ — это страховка, а не рекомендация 1С.

### 6.4. Кеширование в браузере (`clientCache`)

`<system.webServer><staticContent><clientCache>`: `cacheControlMode` (`NoControl` по умолчанию; `DisableCache` — `Cache-Control: no-cache`; `UseMaxAge` — `max-age` из `cacheControlMaxAge`, по умолчанию `1.00:00:00`; `UseExpires` — `Expires` из `httpExpires`), `cacheControlCustom`, `setEtag` (`true`, IIS 8.0+) [MS Learn]. Действует на **статическое** содержимое — статические сайты на том же IIS можно ускорить `UseMaxAge` (образец команды — `appcmd set config "<сайт>" -section:system.webServer/staticContent /clientCache.cacheControlMode:"UseMaxAge"` [MS Learn]); ответов модуля 1С это не касается [практика ⚠].

### 6.5. Посмотреть содержимое кеша ядра

```bat
netsh http show cachestate
netsh http show cachestate url=https://web1c.corp.local/docs/index.html
```

[MS Learn, `netsh http`; walkthrough output caching].

---

## 7. URL Rewrite и ARR: обратный прокси

### 7.1. Компоненты и установка

| Компонент | Версия (iis.net, 2026) | Зачем | Источник |
|---|---|---|---|
| URL Rewrite | 2.1 | правила переписывания и перенаправления, серверные переменные, outbound-правила | [MS, iis.net downloads] |
| Application Request Routing (ARR) | 3.0 | прокси, фермы серверов, балансировка, проверки работоспособности, привязка клиента, дисковый кеш, WebSocket | [MS, iis.net downloads; WebSocket — сторонний] |

- ARR **зависит от URL Rewrite**: сначала URL Rewrite, потом ARR [MS, страница загрузки ARR]. Оба — отдельные установщики x64 со страниц `https://www.iis.net/downloads/microsoft/url-rewrite` и `…/application-request-routing`; в этой сессии двоичные файлы не скачивались и не проверялись.
- Инструкции для ARR 1.0/2.0 требуют остановить WAS и WMSVC на время установки (ставится исправление IIS) [MS Learn]; для ARR 3.0 отдельной инструкции на learn.microsoft.com нет ⚠ — ставьте в окно обслуживания.
- Если в `web.config` есть секция `<rewrite>`, а модуль URL Rewrite не установлен (новый сервер, восстановление из копии) — **500.19 с HRESULT 0x8007000d** («нераспознанная секция») [MS Learn, поддержка].
- Проверка установки: в `appcmd list config -section:system.webServer/globalModules` должны быть модули URL Rewrite и ARR (имена `RewriteModule`, `ApplicationRequestRouting` — ⚠ по практике) [секция — MS Learn].

### 7.2. URL Rewrite: что нужно знать для прокси

[MS Learn, справочники URL Rewrite 1.x и 2.0]:

- **Распределённые правила** (`<rules>`) — в `web.config` сайта/приложения или в `<location>`; на вход получают путь **относительно** места определения, без ведущего `/`. **Глобальные** (`<globalRules>`) — только в `applicationHost.config`, получают полный путь, выполняются раньше (`PreBeginRequest`) и не отключаются ниже.
- Правила выполняются по порядку; `stopProcessing="true"` останавливает обработку после сработавшего правила. Синтаксис шаблонов по умолчанию — `ECMAScript` (регулярные выражения), сравнение без учёта регистра; есть `Wildcard` и `ExactMatch`.
- Действия: `Rewrite` (внутренняя подмена; если URL абсолютный `http(s)://…` и включён прокси ARR — запрос уходит на другой сервер), `Redirect` (`redirectType`: `Permanent` — 301, `Found` — 302, 303 «See other», `Temporary` — 307; 308 не поддерживается), `CustomResponse`, `AbortRequest`, `None`. `appendQueryString` по умолчанию `true`.
- Серверные переменные: `{HTTP_HOST}`, `{HTTPS}` (`ON`/`OFF`), `{SERVER_PORT_SECURE}`, `{REQUEST_URI}`, `{URL}` и др. Обратные ссылки — `{R:n}` (шаблон правила), `{C:n}` (условия).
- **Установка заголовков запроса** — `<serverVariables><set name="HTTP_…" value="…"/>`: имя `HTTP_X_FORWARDED_PROTO` превращается в заголовок `x-forwarded-proto` (`HTTP_` убирается, `_` → `-`, нижний регистр); `replace` по умолчанию включён. Распределённое правило может менять только переменные из списка **`<allowedServerVariables>`** (он в `applicationHost.config`, меняет его администратор сервера); иначе — ошибка выполнения. Глобальным правилам список не нужен.
- **Outbound-правила** (`<outboundRules>`) правят ответ: заголовки (`serverVariable="RESPONSE_…"`) и тело (`filterByTags`, `preCondition` по `{RESPONSE_CONTENT_TYPE}`). Это дорого по ЦП; **не работают со статическим сжатием** (известная проблема URL Rewrite 2.0); при вставке недоверенных данных — функция `HtmlEncode` [MS Learn].
- `logRewrittenUrl="true"` у действия распределённого правила — писать в журнал IIS переписанный URL вместо исходного [MS Learn].
- Отладка правил — FREB с областью `Rewrite` поставщика `WWW Server` (раздел 10) [MS Learn].

### 7.3. ARR как прокси: серверные параметры

Прокси выключен по умолчанию; включается в диспетчере IIS: узел сервера → «Application Request Routing» → «Server Proxy Settings» → «Enable proxy» [MS Learn, walkthrough reverse proxy; сторонний: Grafana]. В конфигурации это секция `system.webServer/proxy` уровня сервера.

| Параметр | Что известно | Источник |
|---|---|---|
| `enabled` | `true` — ARR обрабатывает правила `Rewrite` с абсолютным URL | [MS Learn: `<proxy enabled="true" …/>` в статье Hotmail/SkyDrive] |
| `preserveHostHeader` | `true` — бэкенд получает исходный `Host` вместо имени из правила | [MS Learn: та же статья; сторонний: Grafana] |
| `reverseRewriteHostInResponseHeaders` | переписывать имя бэкенда в заголовках ответа (`Location`) на имя прокси; Microsoft в своём сценарии ставила `false`, чтобы отдавать `Location` как есть. Уточнено 20.10.2026: на странице «Server Proxy Settings» флажок «Reverse rewrite host in response headers» по умолчанию **включён** | [MS Learn; снимок экрана в «Creating a Forward Proxy Using ARR», шаг 5] |
| `proxy` (атрибут) | цепочка прокси: отправлять запросы ARR через другой прокси | [MS Learn] |
| `minResponseBuffer` | упомянут: слишком малое значение вызывало зависания ASP.NET 4.0. В диспетчере — «Response buffer threshold (KB)», по умолчанию 256; рядом «Response buffer (KB)», 4096 | [MS Learn; снимок экрана там же] |
| таймаут прокси | серверный прокси: «Time-out (seconds)», по умолчанию **120**; у фермы — свои настройки «Proxy», таймаут по умолчанию **30 с** («proxy timeout in the server farm's proxy settings», раздел 7.7) | [MS Learn: снимок экрана «Server Proxy Settings»; поддержка 502] |
| `X-Forwarded-For` | ARR добавляет сам; в трассировке Microsoft — значение `IP:порт` клиента; в «Server Proxy Settings» — имя заголовка («Preserve client IP in the following header», `X-Forwarded-For`) и флажок «Include TCP port from client IP», по умолчанию включён | [MS Learn, поддержка 502; снимок экрана «Server Proxy Settings»] |
| `X-ARR-SSL`, `X-ARR-ClientCert`, `X-ARR-LOG-ID`, `Max-Forwards: 10` | ARR добавляет к запросу на бэкенд; `X-ARR-LOG-ID` — сквозной идентификатор для поиска запроса на бэкенде | [MS Learn, поддержка 502] |

Имена атрибутов конфигурации для таймаута, включения порта в `X-Forwarded-For`, буфера ответа в статьях Microsoft **не приведены** — есть только подписи полей и умолчания в диспетчере (таблица выше). По копии файла схемы ARR `arr_schema.xml` в стороннем репозитории `lextm/iis_schema` [сторонний ⚠ — не страница Microsoft] это `timeout` (`00:02:00`), `includePortInXForwardedFor` (`true`), `xForwardedForHeaderName` (`X-Forwarded-For`), `minResponseBuffer` (256), `responseBufferLimit` (4096), `preserveHostHeader` (`false`), `reverseRewriteHostInResponseHeaders` (`true`); умолчания совпадают со снимком экрана Microsoft. Сверьте на своём сервере после установки ARR — команда выводит все атрибуты секции с текущими значениями:

```bat
cd /d %windir%\system32\inetsrv
appcmd list config -section:system.webServer/proxy /config:*
```

Включение прокси и сохранение `Host` (образцы Microsoft и Grafana):

```bat
appcmd set config -section:system.webServer/proxy /enabled:"True" /commit:apphost
appcmd set config -section:system.webServer/proxy /preserveHostHeader:"True" /commit:apphost
appcmd list config -section:system.webServer/proxy
```

Grafana записывает `-preserveHostHeader:true` [сторонний: Grafana, «Use IIS with URL Rewrite as a reverse proxy»]; в образцах Microsoft параметры `appcmd` пишутся и через `-`, и через `/` (`-section:… /commit:…`); `/enabled:` — по аналогии ⚠.

Таймаут серверного прокси: в диспетчере IIS — «Application Request Routing» → «Server Proxy Settings» → «Time-out (seconds)», по умолчанию 120 (уточнено 20.10.2026 по снимку экрана в статье Microsoft «Creating a Forward Proxy Using ARR»); в конфигурации — атрибут `timeout` формата `чч:мм:сс` (по копии схемы ARR ⚠). Он действует для правил `Rewrite` с абсолютным URL без фермы (сценарии А и Б); у фермы таймаут свой (раздел 7.7). Пример (проверьте имя атрибута до применения):

```bat
appcmd set config -section:system.webServer/proxy /timeout:"00:30:00" /commit:apphost
```

### 7.4. Безопасность прокси

- **Не делать открытый прокси.** Правило вида «всё → `http://{HTTP_HOST}/{R:0}`» превращает сервер в прокси для любого адреса. Целевой хост в правилах — только константы (имена внутренних серверов) [практика]. Прямой прокси ARR — отдельный сценарий и настраивается правилами явно [MS Learn, «Creating a Forward Proxy Using ARR»].
- **TLS к бэкенду.** По умолчанию ARR **не проверяет совпадение имени** в сертификате бэкенда (`SECURITY_FLAG_IGNORE_CERT_CN_INVALID`); управлять проверкой можно параметром `SecureConnectionIgnoreFlags` (DWORD) в `HKLM\SOFTWARE\Microsoft\IIS Extensions\Application Request Routing\Parameters` (флаги `0x00001000` CN, `0x00002000` срок, `0x00000100` неизвестный ЦС, `0x00000200` назначение) [MS Learn]. Статья Microsoft сама себе противоречит: «чтобы изменить поведение — задайте 0» и тут же «0 — то же, что флаг игнорирования CN» ⚠ — проверяйте на стенде с заведомо неверным сертификатом.
- **Разгрузка TLS** у ферм ARR включена по умолчанию: от ARR к серверам фермы трафик идёт по HTTP. Допустимо только внутри доверенной сети [MS Learn, HTTP load balancing].
- **Защита бэкенда от обхода:** бэкенд принимает запросы только с адреса прокси (брандмауэр; `iis/02-…` — ограничения по IP) [практика].
- **Обход путей у Tomcat** (`/..;a=b/`): Microsoft советует блокирующие правила URL Rewrite **до** правил ARR [MS Learn, Reverse Proxy rule template]. Для 1С и Apache-бэкендов прямо не описано ⚠, но блокирующее правило перед прокси-правилом — хорошая общая практика.

### 7.5. Сценарий А: IIS с ARR перед публикацией 1С на другом сервере

Схема: клиенты → `rp-iis.corp.local` (IIS + URL Rewrite + ARR, TLS) → `srv-1c-app` (Apache + `wsap24`, HTTP во внутренней сети) или `web1c.corp.local` (IIS + `wsisapi.dll`). Публикация на бэкенде — `../1c/05-…` (Apache) или `../1c-windows/03-…` (IIS).

**Что требует 1С** [ИТС-адм разд. 8.10.3]: прокси должен формировать `X-Forwarded-Port`, `X-Forwarded-Host`, `X-Forwarded-Proto` («восстановление» исходного запроса) и `X-Forwarded-For` (IP внешнего клиента). Перевод на IIS [MS Learn — механизмы; схема для 1С — практика]:

| Заголовок | Кто ставит | Как |
|---|---|---|
| `X-Forwarded-For` | ARR сам | по умолчанию `IP:порт`; нужен чистый IP — снять флажок «Include TCP port from client IP» в «Server Proxy Settings» (уточнено 20.10.2026 по снимку экрана Microsoft, раздел 7.3); в конфигурации — `includePortInXForwardedFor` (по копии схемы ARR ⚠, сверить `appcmd list config -section:system.webServer/proxy /config:*`) |
| `X-Forwarded-Proto` / `-Host` / `-Port` | правило URL Rewrite | `HTTP_X_FORWARDED_PROTO` = `https`; `HTTP_X_FORWARDED_HOST` = `{HTTP_HOST}`; `HTTP_X_FORWARDED_PORT` = `{SERVER_PORT}` |
| `Host` | ARR | по умолчанию — имя бэкенда из правила; с `preserveHostHeader=true` — внешнее имя |

**Шаг 1. Разрешить серверные переменные** (один раз на сервер; форма — по образцу Microsoft для коллекций ⚠; в диспетчере — «URL Rewrite» → «View Server Variables…» → «Add…» [MS Learn]):

```bat
cd /d %windir%\system32\inetsrv
appcmd set config -section:system.webServer/rewrite/allowedServerVariables /+"[name='HTTP_X_FORWARDED_PROTO']" /commit:apphost
appcmd set config -section:system.webServer/rewrite/allowedServerVariables /+"[name='HTTP_X_FORWARDED_HOST']" /commit:apphost
appcmd set config -section:system.webServer/rewrite/allowedServerVariables /+"[name='HTTP_X_FORWARDED_PORT']" /commit:apphost
appcmd list config -section:system.webServer/rewrite/allowedServerVariables
```

**Шаг 2. Включить прокси и таймаут** (раздел 7.3): таймаут не меньше самого долгого синхронного вызова 1С — например, 30 минут; у Apache-прокси в этой базе для 1С взят час (`../apache/03-…`, разд. 9.2) [практика].

**Шаг 3. Правила сайта прокси** — `web.config` в корне сайта `rp-iis`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <!-- HTTP -> HTTPS (HSTS и привязки — iis/02-…) -->
        <rule name="http-to-https" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="^OFF$" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>
        <!-- Публикация demo: путь на прокси = путь на бэкенде -->
        <rule name="1c-demo" stopProcessing="true">
          <match url="^demo(/.*)?$" />
          <serverVariables>
            <set name="HTTP_X_FORWARDED_PROTO" value="https" />
            <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
            <set name="HTTP_X_FORWARDED_PORT" value="{SERVER_PORT}" />
          </serverVariables>
          <action type="Rewrite" url="http://srv-1c-app.corp.local/demo{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <security>
      <requestFiltering>
        <!-- загрузки в 1С больше 28,6 МБ: 1 ГиБ; то же нужно и на бэкенде -->
        <requestLimits maxAllowedContentLength="1073741824" maxQueryString="32768" />
      </requestFiltering>
    </security>
  </system.webServer>
</configuration>
```

- Структура правила — из примера Microsoft «Reverse Proxy with URL Rewrite v2 and ARR», `<serverVariables><set/>` — из справочника URL Rewrite 2.0, перенаправление — по справочнику (`{HTTPS}` = `OFF`, `redirectType`) [MS Learn; сборка — практика]. `X-Forwarded-Proto` — константа, потому что сайт работает только по HTTPS.
- **Путь не переименовывать** (`/buh` на прокси → `/demo` на бэкенде): ссылки веб-клиента останутся с путём бэкенда, а править их outbound-правилами в ответах 1С ненадёжно [практика ⚠; ср. `../apache/03-…`, разд. 9.2].
- `requestFiltering` действует **и на прокси**: без увеличения лимита большие загрузки получат 404.13 на `rp-iis` (`../1c-windows/03-…`, разд. 8.1). Если секция заблокирована на уровне сервера — 500.19 `0x80070021` (раздел 13).
- **Проверку подлинности Windows через ARR** для публикаций с `-osauth` не рекомендую: NTLM привязан к TCP-соединению, а ARR переиспользует соединения к бэкенду; Kerberos потребует SPN и делегирования на имя прокси [практика ⚠]. Такие публикации — напрямую или через L4-балансировщик (`../1c-windows/04-…`).

**Шаг 4. Проверка:**

```bat
:: с прокси — бэкенд отвечает напрямую
curl.exe -s -o NUL -w "%{http_code}\n" http://srv-1c-app.corp.local/demo/
:: с рабочего места — через прокси; смотреть код, Location и схему
curl.exe -s -o NUL -D - https://rp-iis.corp.local/demo/
```

Какие заголовки дошли до бэкенда: на Apache — временный журнал с `%{X-Forwarded-For}i` и др. (`../apache/03-…`, разд. 9.3); на IIS — свои поля журнала (раздел 8.5) или FREB (`GENERAL_REQUEST_HEADERS`). `Location` с `http://` или с внутренним именем — не дошли `X-Forwarded-Proto`/`Port` или `Host` [практика].

### 7.6. Сценарий Б: IIS перед внутренними сервисами и WebSocket

Шаблон правила такой же, как в 7.5, бэкенд — `http://127.0.0.1:<порт>/` (сервис на том же Windows-хосте) или `http://srv-obs.corp.local:<порт>/`. Что сервису нужно со стороны приложения (`root_url`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `GLITCHTIP_DOMAIN`, «Имя компьютера» и «Протокол» Redmine), — в `../apache/03-…`, разд. 8, и статьях сервисов; на IIS меняется только способ передать заголовки.

**Grafana** — официальная инструкция для IIS [сторонний: Grafana, обновлено 06.03.2025]:

- установить URL Rewrite и ARR, включить прокси («Server Proxy Settings» → «Enable proxy»; без этого — 404);
- правило: шаблон `grafana(/)?(.*)`, без учёта регистра, перезапись на `http://localhost:3000/{R:2}`, с добавлением строки запроса и остановкой обработки;
- в `custom.ini` Grafana: `[server]` `domain = …`, `root_url = %(protocol)s://%(domain)s/grafana/`;
- для Grafana новее 8.3.5 — `appcmd … -section:system.webServer/proxy -preserveHostHeader:true /commit:apphost`, иначе «origin not allowed».

**WebSocket** (Grafana Live — `/api/live/` [сторонний: `../apache/03-…`, разд. 8.4]; сервер взаимодействия 1С — порт WebSocket экземпляра, в примере `../guides/04-…` — 8086):

1. На сервере с ARR — компонент «Протокол WebSocket»: `Install-WindowsFeature -Name Web-WebSockets` (DISM: `IIS-WebSockets`) [MS Learn; имя для `Install-WindowsFeature` — из таблицы IIS 8.5]. Без него приложения IIS получают «The WebSocketModule is not loaded» [MS Learn, поддержка]; проксирование WebSocket через ARR 3.0 без этого компонента не работает [сторонний ⚠].
2. Секция `<system.webServer><webSocket>` [MS Learn, справочник; IIS 8.0+]:

   | Атрибут | Умолчание | Смысл |
   |---|---|---|
   | `enabled` | `true` | разрешить WebSocket |
   | `receiveBufferLimit` | `4194304` | предел буфера приёма соединения, байт |
   | `pingInterval` | `00:00:00` | интервал служебных ping по соединению; `0` — не слать |

3. Простаивающее WebSocket-соединение могут рвать таймауты прокси и межсетевых экранов; ping раз в минуту — по образцу Microsoft (`pingInterval="00:01:00"`) [MS Learn; применимость к ARR ⚠].
4. Ошибка WebSocket в ARR — **502.5** [MS Learn, коды состояния]; в WebSocket-запросе, разобранном IIS как неверный, — **400.11** [MS Learn].

```bat
appcmd set config "rp-iis" -section:system.webServer/webSocket /enabled:"True" /pingInterval:"00:01:00" /commit:apphost
appcmd list config "rp-iis" -section:system.webServer/webSocket /config:*
```

Форма — по образцу справочника `<webSocket>` [MS Learn].

**Loki и GlitchTip за IIS:** приём событий — POST с телом; `maxAllowedContentLength` на прокси должен быть больше предела самого сервиса, иначе 404.13 на IIS вместо понятного 413 сервиса [практика]. Базовая аутентификация на IIS для `push` Loki — `iis/02-…`.

### 7.7. Сценарий В: ARR как балансировщик нескольких IIS с публикациями 1С

Ферма серверов (`webFarms`) [MS Learn, ARR walkthroughs]:

```bat
cd /d %windir%\system32\inetsrv
appcmd.exe set config -section:webFarms /+"[name='farm-1c']" /commit:apphost
appcmd.exe set config -section:webFarms /+"[name='farm-1c'].[address='web1c-01.corp.local']" /commit:apphost
appcmd.exe set config -section:webFarms /+"[name='farm-1c'].[address='web1c-02.corp.local']" /commit:apphost
:: проверка работоспособности: статический файл на каждом узле
appcmd.exe set config -section:webFarms /[name='farm-1c'].applicationRequestRouting.healthCheck.url:"http://rp-iis.corp.local/health.txt" /[name='farm-1c'].applicationRequestRouting.healthCheck.responseMatch:"healthy" /commit:apphost
:: привязка клиента к узлу cookie
appcmd.exe set config -section:webFarms /[name='farm-1c'].applicationRequestRouting.affinity.useCookie:"True" /commit:apphost
:: глобальное правило ARR_farm-1c_loadbalance: шаблон «*» (Wildcard) → http://farm-1c/{R:0}
appcmd.exe list config -section:system.webServer/rewrite/globalRules
```

Все команды — по образцам Microsoft (`myServerFarm`, `healthCheck.url`, `healthCheck.responseMatch`, `affinity.useCookie`) [MS Learn]. Глобальное правило «всё на ферму» диспетчер IIS предлагает создать сам при создании фермы; его же Microsoft показывает тремя командами `appcmd … -section:system.webServer/rewrite/globalRules` [MS Learn]. Хост в URL проверки в образце Microsoft — имя самого сервера ARR («server name or FQDN of ARR server»), файл `health.txt` с текстом `healthy` кладётся на каждый узел фермы [MS Learn]; что ARR подставляет адрес каждого узла, по образцу не очевидно ⚠ (в копии схемы ARR у каждого сервера фермы есть `healthCheckAlternateHostName`/`healthCheckAlternatePort`, что с подстановкой согласуется [сторонний]) — проверьте, остановив сайт на одном узле.

Что важно для 1С:

- **Таймаут и прочие параметры прокси у фермы — свои**: настройки прокси задаются либо на уровне сервера (ARR как серверный прокси, раздел 7.3), либо у фермы, если она используется; у фермы — диспетчер IIS → ферма → «Proxy»; в конфигурации — узел `webFarms/webFarm/applicationRequestRouting/protocol` [MS Learn, поддержка «Proxy server rejects requests from ARR»; ARR request consolidation]. Таймаут фермы по умолчанию **30 с** [MS Learn, поддержка 502] — для 1С поднять так же, как в сценарии А. Имя атрибута `timeout` и умолчания фермы `preserveHostHeader=true`, `reverseRewriteHostInResponseHeaders=false` — по копии схемы ARR [сторонний ⚠]: `appcmd.exe set config -section:webFarms /[name='farm-1c'].applicationRequestRouting.protocol.timeout:"00:30:00" /commit:apphost`, проверка — `appcmd list config -section:webFarms /config:*`.
- **Привязка клиента (`affinity.useCookie`)** — cookie ARR; клиенты должны принимать cookie [MS Learn]. Нужна ли «липкость» веб-клиенту 1С, документация 1С не говорит — по умолчанию включайте (`../1c-windows/03-…`, разд. 12.4) [практика ⚠]. В старых сборках ARR cookie не работала, если сайт на нестандартном порту или адрес не FQDN; исправлено обновлением ARR (KB 2693489) [MS Learn, поддержка].
- **Вывод узла на обслуживание** — «Disallow New Connections»: клиенты с cookie остаются на узле, новые не приходят [MS Learn]. Так обновляют модуль 1С на узлах по одному; версии модуля на всех узлах должны совпадать с кластером [ИТС-адм разд. 8.3.1].
- **Разгрузка TLS** включена по умолчанию (раздел 7.4). Отключение — отдельные правила для `{HTTPS}` = `On` с `https://farm-1c/{R:0}` [MS Learn].
- **Шесть алгоритмов балансировки** и проверки «по живому трафику» + «по URL» [MS Learn]. Для 1С достаточно «по умолчанию» + проверки по статическому файлу; проверять модуль 1С запросом к публикации не стоит — каждый запрос может создать сеанс ⚠.
- **502.4** «No server» — все узлы фермы недоступны или выведены [MS Learn, поддержка].

### 7.8. Счётчики и журналы ARR

- Объекты производительности **«Application Request Routing Server»** (на сервер фермы: `Average Response Time / Request`, `Bytes Received`, `Bytes Sent`, `Current Requests`, `Failed Requests`, `Failed Requests / Sec`, `Health`, `Requests / Sec`, `State`, `Total Requests`; экземпляры — `<ферма>\<сервер>`) и **«Application Request Routing Cache»** (попадания и промахи кеша) [MS Learn].
- Ошибки прокси видны в журнале **сайта прокси** (502 с подстатусом, `sc-win32-status` — код WinHTTP) и в FREB с областями `Rewrite` и `RequestRouting` (события `ARR_SERVER_ROUTED` и т. д.) [MS Learn]. На бэкенде тот же запрос находится по `X-ARR-LOG-ID` [MS Learn].
- Низкоуровневая трассировка WinHTTP со стороны ARR: `netsh trace start scenario=internetclient capture=yes persistent=no level=verbose tracefile=c:\temp\net.etl`, воспроизвести, `netsh trace stop`; рядом появится `net.cab` с журналами [MS Learn, поддержка 502].

---

## 8. Журнал сайта (W3C)

### 8.1. Где и как пишется

Элемент `sites/site/logFile` (умолчания для новых сайтов — `siteDefaults/logFile`) [MS Learn, справочник]:

| Атрибут | Умолчание | Смысл |
|---|---|---|
| `enabled` | `true` | журнал сайта включён |
| `directory` | `%SystemDrive%\inetpub\logs\LogFiles` | корень; внутри — `W3SVC<id сайта>` |
| `logFormat` | `W3C` | ещё `IIS`, `NCSA` (фиксированные поля, локальное время), `Custom` |
| `period` | `Daily` | `Hourly`, `Weekly`, `Monthly`, `MaxSize` |
| `truncateSize` | `20971520` | размер файла для `MaxSize`; меньше 1 048 576 не бывает |
| `localTimeRollover` | `false` | имя файла и момент ротации по местному времени; **время внутри записей W3C всегда UTC** |
| `logExtFileFlags` | см. 8.2 | какие поля писать |
| `logTargetW3C` (IIS 8.5+) | `File` | `ETW` — в трассировку событий (поставщик `Microsoft-Windows-IIS-Logging`), можно оба |
| `flushByEntryCountW3CLog` (IIS 8.5+) | `0` (сброс по 64 КБ) | меньше — быстрее появляются записи, больше дисковых операций |
| `maxLogLineLength` (IIS 8.5+) | `65536` | предел строки |
| `logSiteId` (IIS 8.0+) | `true` | в `s-sitename` — номер, а не имя сайта |

- Имя файла по умолчанию — `u_exГГММДД.log` (ежедневно) [MS Learn, поддержка]; префикс `u_` — признак записи в UTF-8 [практика], по умолчанию `logInUTF8=true` в `system.applicationHost/log` [MS Learn, справочник `log`]. При почасовой ротации и других периодах имя другое [MS Learn].
- С пользовательскими полями (8.5) IIS создаёт **новые** файлы с суффиксом `_x` [MS Learn].
- Записи ASP- и ODBC-ошибок в журнал сайта не попадают [MS Learn].
- Режим журнала сервера `system.applicationHost/log` `centralLogFileMode`: `Site` (по умолчанию: файл на сайт), `CentralW3C` (один текстовый файл на сервер), `CentralBinary` (один двоичный, нужен инструмент для разбора; экономит ЦП и память при сотнях сайтов) [MS Learn, справочник; tuning].
- Выборочная запись — `system.webServer/httpLogging`: `dontLog` (`false`; `true` — не писать успешные, код < 400), `selectiveLogging` (`LogAll` по умолчанию, `LogSuccessful` 100–399, `LogError` 400–999); задаётся до уровня URL [MS Learn]. Пример: для пути приёма событий мониторинга писать только ошибки.
- Каталог журналов — не в `%SystemRoot%` и, при большом трафике, на отдельном диске [MS Learn, configure logging; tuning].

### 8.2. Поля

| `logExtFileFlags` | Поле W3C | По умолчанию | Зачем |
|---|---|---|---|
| `Date`, `Time` | `date`, `time` | да | UTC |
| `ClientIP` | `c-ip` | да | за прокси — адрес прокси (см. 8.5) |
| `UserName` | `cs-username` | да | `-` у анонимных; при Windows-аутентификации — `ДОМЕН\имя` |
| `ServerIP`, `ServerPort` | `s-ip`, `s-port` | да | |
| `Method` | `cs-method` | да | |
| `UriStem`, `UriQuery` | `cs-uri-stem`, `cs-uri-query` | да | |
| `HttpStatus`, `HttpSubStatus` | `sc-status`, `sc-substatus` | да | **подстатус** — главное для диагностики (раздел 13) |
| `Win32Status` | `sc-win32-status` | да | код Windows: `64` — клиент (или ARR) разорвал соединение; `12002` у ARR — таймаут WinHTTP [MS Learn, поддержка 502] |
| `TimeTaken` | `time-taken` | да | мс (8.3) |
| `UserAgent` | `cs(User-Agent)` | да | |
| `Referer` | `cs(Referer)` | да (IIS 8.0+) | |
| `BytesSent`, `BytesRecv` | `sc-bytes`, `cs-bytes` | **нет** | размеры — включить: без них не отличить «медленно, потому что большой ответ» от «медленно, потому что ждали 1С» [MS Learn, поддержка: совет включить] |
| `Host` | `cs-host` | **нет** | несколько имён на одном сайте, прокси |
| `ProtocolVersion` | `cs-version` | **нет** | HTTP/1.1 или HTTP/2 |
| `SiteName`, `ComputerName` | `s-sitename`, `s-computername` | нет | центральный журнал, сбор с нескольких серверов |
| `Cookie` | `cs(Cookie)` | нет | **не включать**: в cookie — идентификаторы сеансов |

Включить недостающие поля для сайта (значения флагов через запятую; форма `"/[name='…'].logFile.<атрибут>:…"` — по образцу Microsoft; запись набора флагов одной строкой ⚠ образца нет):

```bat
cd /d %windir%\system32\inetsrv
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].logFile.logExtFileFlags:Date,Time,ClientIP,UserName,ServerIP,Method,UriStem,UriQuery,HttpStatus,Win32Status,ServerPort,UserAgent,HttpSubStatus,Referer,TimeTaken,BytesSent,BytesRecv,Host,ProtocolVersion" /commit:apphost
appcmd list config -section:system.applicationHost/sites /config:* | findstr /i "logExtFileFlags directory period"
```

После изменения полей новый набор пишется с новой строкой `#Fields:` — разборщики должны читать заголовок, а не полагаться на порядок столбцов [практика].

### 8.3. Что такое `time-taken`

- Отсчёт начинается, когда http.sys получил **первый байт** запроса (до разбора), и заканчивается на **последней отправке** IIS; значение в миллисекундах; первый запрос после открытия файла журнала немного дольше [MS Learn, справочник `logFile`].
- **Сеть:** справочник `logFile` утверждает, что сетевое время не учитывается, а статья поддержки KB 944884 — что с IIS 7.0 `time-taken` **включает** сетевое время (http.sys ждёт подтверждения последнего пакета или сброса соединения), кроме ответов до 2 КБ из памяти и буферизованной отправки ⚠. На практике большие ответы медленным клиентам дают большой `time-taken` при быстром сервере — смотрите вместе с `sc-bytes` [MS Learn, поддержка; практика].
- Для 1С: большой `time-taken` у POST к `/demo/e1cib/…` (веб-клиент) или `/demo/hs/…` (HTTP-сервисы) при малом `sc-bytes` — серверный вызов долго выполнялся в кластере; дальше — технологический журнал (события `VRSREQUEST`/`VRSRESPONSE` на хосте IIS, `CALL` на сервере 1С; `../1c-windows/03-…`, разд. 14.5; `../1c/07-…`) [практика; события — ИТС-адм прил. 3.24].

### 8.4. Ротация, хранение, очистка

- IIS сам старые файлы **не удаляет** [MS Learn, «Managing IIS Log File Storage»]. Варианты Microsoft: сжатие каталога NTFS (журналы сжимаются примерно до 2 % размера; первичное сжатие нагружает сервер), каталог на другом сервере (UNC), удаление старых файлов по расписанию [MS Learn].
- Удаление — разрушающее действие; сначала архивируйте журналы, которые могут понадобиться для разбора инцидентов (ИТС требует собирать журналы веб-серверов [ИТС-мет 5899, 2016]) [практика].

Сценарий очистки (Microsoft приводит VBScript; ниже — то же на PowerShell [практика]); сначала запуск с `-WhatIf`:

```powershell
# C:\Scripts\iis-logs-cleanup.ps1 — удалить журналы IIS старше 90 дней
$root = 'C:\inetpub\logs\LogFiles'
$days = 90
Get-ChildItem -Path $root -Recurse -File -Include *.log |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$days) } |
  Remove-Item -WhatIf          # убрать -WhatIf после проверки списка
```

```bat
:: ежедневный запуск от SYSTEM в 04:00
schtasks /create /tn "IIS-logs-cleanup" /sc daily /st 04:00 /ru SYSTEM /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\iis-logs-cleanup.ps1"
schtasks /query /tn "IIS-logs-cleanup"
```

Каталог FREB чистится сам (`maxLogFiles`, раздел 10); HTTPERR — нет: файлы `httperrN.log` по 1 МБ копятся, их тоже включите в очистку (`%SystemRoot%\System32\LogFiles\HTTPERR`) [MS Learn, HTTP API; практика ⚠ — ограничения числа файлов HTTPERR документация не описывает].

**Расширенное ведение журналов (Advanced Logging)** снято Microsoft с поддержки, загрузка недоступна [MS, iis.net]. Его задачи закрывают пользовательские поля (8.5) и ETW (`logTargetW3C`).

**Отправка в Loki:** читать файлы журнала агентом (Grafana Alloy; Promtail снят с поддержки) — `../observability/03-…`, разд. 7 [сторонний]. Время в записях — UTC, поле `date`+`time`.

### 8.5. Пользовательские поля (IIS 8.5+)

`logFile/customFields` [MS Learn, справочник; «Enhanced Logging for IIS 8.5»]:

- `maxCustomFieldLength` — `4096` байт на поле (2–65 536); суммарно все пользовательские поля строки — до 65 536 байт, дальше обрезка;
- `<add logFieldName="…" sourceName="…" sourceType="…"/>`: `sourceType` — `RequestHeader`, `ResponseHeader` или `ServerVariable`; имя поля без пробелов; серверная переменная — только в **верхнем регистре**;
- настраивается **только для сайта** (на уровне сервера в диспетчере кнопка недоступна).

Главный случай — **бэкенд за прокси**: `c-ip` показывает адрес прокси, реальный клиент — в `X-Forwarded-For`:

```bat
appcmd.exe set config -section:system.applicationHost/sites /+"[name='Default Web Site'].logFile.customFields.[logFieldName='X-Forwarded-For',sourceName='X-Forwarded-For',sourceType='RequestHeader']" /commit:apphost
appcmd.exe list config -section:system.applicationHost/sites | findstr /i customFields
```

Форма команды — образец Microsoft (`ContosoField`); имя источника для заголовка ⚠: в образце XML Microsoft записано `sourceName="X_FORWARDED_FOR"` при `sourceType="RequestHeader"`, а в пошаговой инструкции — «введите `X-FORWARDED-FOR`». Проверьте, что поле заполняется, на тестовом запросе с заголовком.

Полезные для прокси и 1С поля: `X-ARR-LOG-ID` (запрос, пришедший через ARR) [MS Learn, поддержка 502], `X-Forwarded-Proto`, ответный `Content-Encoding` (проверка сжатия), серверные переменные TLS (протокол и шифр — IIS 10.0 1709+, `iis/02-…`) [MS Learn].

### 8.6. Разбор журналов

**PowerShell** — функция, читающая заголовок `#Fields:` (подходит и для HTTPERR, если в нём есть строка `#Fields:`, раздел 9.2) [практика]:

```powershell
function Import-W3CLog {
  param([Parameter(Mandatory)][string[]]$Path)
  foreach ($p in $Path) {
    $fields = $null
    foreach ($line in [System.IO.File]::ReadLines($p)) {
      if ($line.StartsWith('#Fields:')) { $fields = $line.Substring(8).Trim() -split ' '; continue }
      if ($line.StartsWith('#') -or -not $fields) { continue }
      $v = $line -split ' '
      $o = [ordered]@{}
      for ($i = 0; $i -lt $fields.Count; $i++) { $o[$fields[$i]] = $v[$i] }
      [pscustomobject]$o
    }
  }
}
$f = Get-ChildItem C:\inetpub\logs\LogFiles\W3SVC1\u_ex*.log | Sort-Object LastWriteTime | Select-Object -Last 1
# 1. Распределение кодов: статус.подстатус.win32
Import-W3CLog $f.FullName | Group-Object sc-status, sc-substatus, sc-win32-status |
  Sort-Object Count -Descending | Select-Object -First 20 Count, Name
# 2. Запросы дольше 30 с
Import-W3CLog $f.FullName | Where-Object { [int]$_.'time-taken' -gt 30000 } |
  Sort-Object { [int]$_.'time-taken' } -Descending |
  Select-Object -First 20 date, time, cs-method, cs-uri-stem, sc-status, sc-substatus, time-taken
```

**Log Parser 2.2** (Microsoft, загрузка с Download Center; в этой сессии не скачивался) — SQL-подобные запросы к журналам; образцы из статьи поддержки Microsoft [MS Learn, поддержка]:

```bat
logparser.exe "SELECT sc-status, sc-substatus, COUNT(*) FROM *.log GROUP BY sc-status, sc-substatus ORDER BY sc-status" -i:w3c
logparser.exe "SELECT cs-uri-stem, time-taken, sc-bytes FROM *.log WHERE time-taken > 250000 ORDER BY time-taken DESC" -i:w3c
```

Время в журнале — UTC; у Log Parser для перевода есть `TO_LOCALTIME()`. Журналы рабочего сервера лучше разбирать на другой машине — запросы к большим файлам грузят сервер [MS Learn, поддержка].

---

## 9. HTTPERR — журнал ошибок http.sys

### 9.1. Где и как настраивается

- Каталог по умолчанию — `%SystemRoot%\System32\LogFiles\HTTPERR`, файлы `httperr<номер>.log`; ротация по размеру [MS Learn, HTTP API].
- Параметры (раздел `HKLM\System\CurrentControlSet\Services\HTTP\Parameters`) [MS Learn, HTTP API]:

| Параметр | Тип | Умолчание | Смысл |
|---|---|---|---|
| `EnableErrorLogging` | DWORD | `1` | журнал включён |
| `ErrorLogFileTruncateSize` | DWORD | `0x100000` (1 МБ) | размер файла; меньше умолчания нельзя |
| `ErrorLoggingDir` | String | `%SystemRoot%\System32\LogFiles` | корень; http.sys создаёт в нём `HTTPERR`; путь полный, `%SystemRoot%` допустим |

- Изменения читаются при старте драйвера: `net stop http`, `net start http` (раздел 4.2). Права на каталог: администраторы и SYSTEM — полный доступ, остальные — нет [MS Learn].
- Ошибка записи журнала сама отражается в журнале событий [MS Learn].

### 9.2. Формат

Поля через пробел (пробелы внутри поля заменяются на `+`), время UTC [MS Learn, HTTP API]: дата, время, IP и порт клиента, IP и порт сервера, версия протокола, метод, URL со строкой запроса (до 4096 байт), статус, `SiteId` (не используется — `-`), **причина** (никогда не пустая).

Расхождение ⚠: документация HTTP API пишет, что заголовков столбцов в файле нет, а пример в статье поддержки по ошибкам 400 показывает строки `#Software: Microsoft HTTP API 1.0`, `#Fields: date time cs-version cs-method cs-uri sc-status s-reason`; в статье об ошибках ARR в строке HTTPERR после причины стоит имя пула (`… 1 Connection_Dropped DefaultAppPool`) [MS Learn, поддержка]. Состав полей современной Windows смотрите по строке `#Fields:` своего файла.

### 9.3. Причины (`s-reason`) и что делать

[MS Learn, HTTP API «Types of Errors Logged»; выводы для 1С — практика]

| Причина | Значение | Что делать |
|---|---|---|
| `QueueFull` | 503: очередь пула переполнена | `w3wp` не успевает (долгие вызовы 1С, мало процессов): разделы 2.1–2.2 |
| `AppOffline` | 503: приложение выведено из-за ошибок | пул отключён rapid-fail: событие 5002, раздел 2.4 |
| `Disabled` / `AppShutdown` / `AppPoolTimer` | 503: выведено администратором / остановлено по политике / процесс слишком занят | состояние пула; `AppShutdown` на практике ⚠ |
| `ConnLimit` | 503: предел соединений сайта | `maxConnections` |
| `N/A` | 503: внутренняя ошибка (нехватка памяти) | невыгружаемый пул, `EnableAggressiveMemoryUsage` |
| `Connection_Abandoned_By_AppPool` | процесс пула упал или «осиротил» запрос | событие 5011, Application Error 1000 (раздел 11) |
| `Connection_Dropped` | клиент закрыл соединение раньше записи в журнал (1 мин) | клиент или ARR ушёл по таймауту; у ARR — 502.3 [MS Learn, поддержка 502] |
| `Timer_ConnectionIdle` / `Timer_EntityBody` / `Timer_AppPool` / `Timer_HeaderWait` / `Timer_MinBytesPerSecond` | простой / не пришло тело / долго в очереди пула / не пришли заголовки / клиент принимает слишком медленно | раздел 3; первое — норма для keep-alive |
| `FieldLength` / `RequestLength` / `URL_Length` / `URL` | превышен предел поля / запроса / длины URL; `URL` — ошибка разбора URL | раздел 4: `MaxFieldLength`, `MaxRequestBytes`, `UrlSegmentMaxLength` |
| `BadRequest`, `Header`, `Hostname`, `Verb`, `Invalid_CR/LF`, `Number`, `Forbidden` | ошибки разбора | кривой клиент или сканер |
| `EntityTooLarge`, `Version_N/S`, `Internal` | тело больше допустимого ⚠ (какой предел — не указано) / 505 / 500 в http.sys | |

`Connection_Abandoned_By_ReqQueue` часто встречается на практике (запросы очереди, брошенные при остановке или падении процесса), но в перечне HTTP API его нет ⚠.

```powershell
$h = Get-ChildItem "$env:SystemRoot\System32\LogFiles\HTTPERR\httperr*.log" | Sort-Object LastWriteTime | Select-Object -Last 1
Get-Content $h.FullName -Tail 50
# частота причин (последние два поля: причина и, в новых Windows, имя пула)
Get-Content $h.FullName | Where-Object { $_ -notlike '#*' } |
  ForEach-Object { ($_ -split ' ')[-2..-1] -join ' ' } |
  Group-Object | Sort-Object Count -Descending | Select-Object -First 15 Count, Name
```

---

## 10. Трассировка неудачных запросов (FREB)

### 10.1. Что это и что нужно

FREB буферизует события трассировки каждого запроса и **записывает их на диск только для «неудачных»** — по вашему определению: коды состояния, время выполнения, уровень событий [MS Learn, поддержка]. Подходит для 401/404/500 и для «долгих» запросов.

- Компонент «Трассировка» — `Web-Http-Tracing` (DISM `IIS-HttpTracing`) [MS Learn].
- Поставщики по умолчанию: `WWW Server`, `ASP`, `ISAPI Extension`; с ASP.NET 2.0+ — `ASPNET`; установщик ARR добавляет свои (в т. ч. области `Rewrite` и `RequestRouting` у `WWW Server`) [MS Learn].
- Области `WWW Server`: `Authentication`, `Security`, `Filter`, `StaticFile`, `CGI`, `Compression`, `Cache`, `RequestNotifications`, `All` (+ `Rewrite`, `RequestRouting` после URL Rewrite/ARR) [MS Learn, справочник; поддержка ARR].
- Уровни подробности области (`traceAreas/add verbosity`): `General`, `CriticalError`, `Error`, `Warning`, `Information`, `Verbose` (по умолчанию) [MS Learn].

### 10.2. Включение на сайте

`sites/site/traceFailedRequestsLogging` [MS Learn, справочник]:

| Атрибут | Умолчание | Смысл |
|---|---|---|
| `enabled` | `false` | FREB для сайта |
| `directory` | `%SystemDrive%\inetpub\logs\FailedReqLogFiles` | внутри — `W3SVC<id>` |
| `maxLogFiles` | `50` | сколько файлов хранить (старые удаляются) |
| `maxLogFileSizeKB` | `1024` (с IIS 8.0 увеличено) | дальше обрезка с пометкой `LOG_FILE_MAX_SIZE_TRUNCATE` |
| `customActionsEnabled` | `false` | разрешить «действия» правил (дамп и т. п.) |

```bat
cd /d %windir%\system32\inetsrv
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].traceFailedRequestsLogging.enabled:True" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].traceFailedRequestsLogging.maxLogFiles:200" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].traceFailedRequestsLogging.directory:D:\Logs\FailedReqLogFiles" /commit:apphost
```

Форма — образец Microsoft [MS Learn]. PowerShell: `Enable-WebRequestTracing -Name "Default Web Site"` включает трассировку и сразу создаёт правило; описание командлета говорит о кодах 400–600, пример — о 500; уточнено 20.10.2026 по справке параметра `-StatusCodes`: его умолчание — `500` (проверьте созданное правило); выключение — `Disable-WebRequestTracing` [MS Learn].

### 10.3. Правила

`system.webServer/tracing/traceFailedRequests` → `<add path="…">` [MS Learn, справочник]:

- `path` — шаблон относительно приложения (`*`, `*.aspx`; `/` — документ по умолчанию); вложенные пути нельзя;
- `<traceAreas><add provider="…" areas="…" verbosity="…"/>` — что писать;
- `<failureDefinitions>`: `statusCodes` (например `"401.2,404.2,500-599"`; без подстатуса — все подстатусы), `timeTaken` (`00:00:00` — не используется; иначе запрос дольше — «неудачный»), `verbosity` (`Ignore` по умолчанию; `Error` — сохранять при первом событии уровня `Error`/`CriticalError`), `traceAllAfterTimeout` (IIS 10.0: `true` — после срабатывания `timeTaken` писать запрос до конца, а не обрезать);
- действие: `customActionExe`, `customActionParams` (`%1` и др. — параметры; переменные среды раскрываются), `customActionTriggerLimit` (по умолчанию `1` за время жизни процесса, 0–10000).

**Правило для публикации 1С** (5xx, 503 и запросы дольше 30 с). Запись в `applicationHost.config` через `<location>` (`/commit:apphost`), а не в `web.config` публикации, который перезаписывает `webinst` [практика ⚠]; команды — по образцам Microsoft для `traceFailedRequests` [MS Learn]:

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/demo" -section:system.webServer/tracing/traceFailedRequests /+"[path='*']" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/tracing/traceFailedRequests /+"[path='*'].traceAreas.[provider='WWW Server',areas='Authentication,Security,Filter,StaticFile,Compression,Cache,RequestNotifications',verbosity='Verbose']" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/tracing/traceFailedRequests /+"[path='*'].traceAreas.[provider='ISAPI Extension',verbosity='Verbose']" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/tracing/traceFailedRequests /[path='*'].failureDefinitions.statusCodes:"500-599" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/tracing/traceFailedRequests /[path='*'].failureDefinitions.timeTaken:"00:00:30" /commit:apphost
appcmd list config "Default Web Site/demo" -section:system.webServer/tracing/traceFailedRequests
```

Поставщик `ISAPI Extension` — без `areas`: уточнено 20.10.2026 по справочнику `traceProviderDefinitions` [MS Learn] — в определении по умолчанию у `ISAPI Extension` (как и у `ASP`) коллекция областей пуста. **Для прокси ARR** — области `Rewrite,RequestRouting`, коды по задаче (Microsoft в примере ловит даже `200-399`, чтобы увидеть маршрутизацию) [MS Learn, поддержка ARR]:

```bat
appcmd.exe set config "rp-iis" -section:system.webServer/tracing/traceFailedRequests /+"[path='*']"
appcmd.exe set config "rp-iis" -section:system.webServer/tracing/traceFailedRequests /+"[path='*'].traceAreas.[provider='WWW Server',areas='Rewrite,RequestRouting',verbosity='Verbose']"
appcmd.exe set config "rp-iis" -section:system.webServer/tracing/traceFailedRequests /[path='*'].failureDefinitions.statusCodes:"502"
```

**Дамп при медленном запросе** (FREB + ProcDump) [MS Learn, поддержка «slow page response»]: у сайта `customActionsEnabled=True`; в правиле `customActionExe` = путь к `procdump.exe` (**без пробелов в пути**, например `C:\procDump\procdump.exe`), `customActionParams` = `-accepteula -ma %1% C:\myDumps -n 3` (три полных дампа с интервалом 10 с; `-s` — другой интервал). ProcDump — утилита Sysinternals, ставится отдельно; дампы — на несистемный диск. Анализ дампов и передача в поддержку 1С — `../1c-windows/05-…`, разд. 6.

### 10.4. Чтение

- Файлы: `%SystemDrive%\inetpub\logs\FailedReqLogFiles\W3SVC<id>\fr000001.xml` — по файлу на неудачный запрос, плюс `freb.xsl` в каталоге [MS Learn].
- Инструкция Microsoft открывает файл в Internet Explorer: из-за усиленной безопасности IE нужно добавить `about:internet` в надёжные узлы, тогда XSL покажет сводку, «Errors & Warnings», подробности и полную трассировку [MS Learn]. Современные браузеры могут не применять XSL к локальному файлу ⚠ — тогда читайте XML в редакторе или копируйте каталог на рабочую станцию [практика].
- Что смотреть: событие с ошибкой и модуль (`MODULE_SET_RESPONSE_ERROR_STATUS` — кто выставил код ⚠ имя по практике); у ARR — `ARR_SERVER_ROUTED` (куда ушёл запрос: сервер, причина маршрутизации, время ответа), `GENERAL_SET_REQUEST_HEADER` (что добавлено в запрос), `GENERAL_FLUSH_RESPONSE_END` (ошибка отправки) [MS Learn, поддержка 502]; у кеша — `HTTPSYS_CACHEABLE` (почему не закеширован) [MS Learn].
- **После разбора выключите правило или FREB**: буферизация трассировки на каждый запрос — накладные расходы [практика].

---

## 11. Журналы событий Windows

### 11.1. WAS: пулы и рабочие процессы (журнал «Система»)

| Код | Источник | Текст (суть) | Что делать |
|---|---|---|---|
| **5002** | WAS | пул «is being automatically disabled due to a series of failures» — отключён защитой от частых сбоев | найти причину падений (5011, Application Error 1000), исправить, запустить пул [MS Learn — текст события в документации Azure DevOps; там журнал назван «Application» ⚠] |
| **5010** | Microsoft-Windows-WAS | процесс пула «failed to respond to a ping» | зависание или отладчик: дамп (раздел 10.3), `pingResponseTime` [MS TechCommunity] |
| **5011** | WAS, уровень «Предупреждение» | процесс пула «suffered a fatal communication error» — **процесс упал** | Application Error 1000 в журнале «Приложение» в то же время [MS Learn, поддержка] |
| **5013** | Microsoft-Windows-WAS | процесс «exceeded time limits during shut down» | долгие запросы при переработке, `shutdownTimeLimit` (90 с) [MS Learn, поддержка] |

Остальные коды WAS (переработки по времени, памяти, конфигурации, завершение по простою и др.) в просмотренной документации Microsoft не перечислены ⚠. Какие переработки пишутся, задаёт `logEventOnRecycle` (раздел 2.3). Посмотреть всё, что пишет WAS на вашем сервере:

```powershell
# сводка по кодам за 7 дней
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WAS'; StartTime=(Get-Date).AddDays(-7)} |
  Group-Object Id | Sort-Object Count -Descending | Select-Object Count, Name
# последние сбои пулов
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WAS'; Id=5002,5010,5011,5013} -MaxEvents 30 |
  Format-Table TimeCreated, Id, Message -Wrap
```

Имя поставщика `Microsoft-Windows-WAS` — из образцов событий в статьях Microsoft; в просмотре событий источник может показываться как «WAS» [MS Learn; MS TechCommunity].

### 11.2. Падения `w3wp` (журнал «Приложение»)

- **Application Error, 1000**: «Faulting application» `w3wp.exe`, модуль, код исключения [MS Learn, поддержка «process crash»]. Коды: `0xC0000005` — нарушение доступа; `0xC00000FD` — переполнение стека; `0xe0434352` — необработанное исключение .NET (тогда ищите `.NET Runtime`, 1026) [MS Learn]. Для пула 1С без управляемого кода .NET-события не ожидаются; сбойный модуль `wsisapi.dll` или библиотеки 1С — разрядность, смешение версий, ошибка платформы (`../1c-windows/03-…`, разд. 3, 14) [практика].
- Для дампа падения Microsoft предлагает Windows Error Reporting, Debug Diagnostic Tool (правило «Crash» для конкретного пула) или ProcDump [MS Learn]; настройка `LocalDumps` и передача в 1С — `../1c-windows/05-…`, разд. 6.

```powershell
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'; Id=1000; StartTime=(Get-Date).AddDays(-7)} |
  Where-Object Message -match 'w3wp\.exe' | Format-List TimeCreated, Message
```

### 11.3. Прочее

- **Журнал безопасности переполнен** при `CrashOnAuditFail`: неадминистраторы не могут войти, IIS отвечает 500 или 401.1 («Logon failure: user not allowed to log on to this computer») до очистки журнала безопасности и сброса `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\CrashOnAuditFail` в 1 с перезагрузкой [MS Learn, поддержка KB 832981]. Редкий, но эффектный случай «всё сломалось без изменений».
- Журналы конфигурации IIS («IIS Configuration Administrative / Operational») собирает диагностический пакет Microsoft [MS Learn, поддержка ETW]; точные имена каналов для `wevtutil` не сверены ⚠ — `wevtutil el | findstr /i iis`.
- Ошибки TLS (Schannel) и их включение подробнее — `iis/02-…` [MS Learn, поддержка «enable Schannel event logging»].

---

## 12. Мониторинг: состояние и счётчики

### 12.1. Что происходит прямо сейчас

```bat
cd /d %windir%\system32\inetsrv
appcmd list apppools                               :: состояние пулов (state:Started/Stopped)
appcmd list apppools /state:stopped                :: только остановленные
appcmd list wps                                    :: рабочие процессы и их пулы (PID)
appcmd list wps /apppool.name:"1C-<версия>"
appcmd list requests                               :: выполняющиеся запросы: URL, время (time:… msec), клиент
appcmd list requests /apppool.name:"1C-<версия>"
appcmd list requests /site.id:1
netsh http show servicestate view=requestq verbose=no   :: очереди http.sys по пулам
```

[MS Learn: appcmd — образцы `list apppools /state:started`, `list wps /apppool.name:`, `list requests`, `list request /apppool.name:`, `list requests /wp.name:`, `/site.id:`; `netsh http show servicestate`].

```powershell
Get-IISAppPool
Get-WebAppPoolState -Name "1C-8.3.27.2074"
Get-WebRequest -AppPool "1C-8.3.27.2074"          # выполняющиеся запросы пула
```

[MS Learn: `Get-IISAppPool`, `Get-WebAppPoolState`, `Get-WebRequest` (параметры `-AppPool`, `-Process`)].

- В диспетчере IIS: узел сервера → «Рабочие процессы» → двойной щелчок по пулу → столбец времени выполнения («Time Elapsed» в английском интерфейсе). Нужен компонент **«Монитор запросов»** (`Web-Request-Monitor`), после установки может понадобиться `iisreset` [MS Learn, поддержка «slow page response»]. Что `appcmd list requests` и `Get-WebRequest` без этого компонента показывают пусто — по практике ⚠.
- Для 1С «долгие запросы» к `/demo/e1cib/…` и `/demo/hs/…` — это серверные вызовы; кто их делает, видно в кластере (`rac session list`, техжурнал), а не в IIS [практика].

### 12.2. Счётчики производительности

| Объект | Счётчики | Норма / тревога | Источник |
|---|---|---|---|
| `HTTP Service Request Queues` (экземпляр = пул) | `CurrentQueueSize`, `RejectedRequests` | очередь ≈ 0; рост — `w3wp` не успевает; `RejectedRequests` растёт — клиенты получают 503 | [MS TechCommunity] |
| `APP_POOL_WAS` (экземпляр = пул) | `Current Application Pool State`, `Current Application Pool Uptime` | состояние «запущен»; сброс времени работы = переработка или падение | [MS TechCommunity] |
| `Process` (экземпляры `w3wp`, `w3wp#1`…) | `% Processor Time`, `Private Bytes`, `Virtual Bytes` | рост `Private Bytes` без спада — утечка; сравнивайте с лимитами переработки | [MS TechCommunity] |
| `Processor(_Total)`, `Memory` | `% Processor Time`; `Available MBytes`, `% Committed Bytes In Use` | общий фон | [MS TechCommunity] |
| `Web Service` (экземпляр = сайт) | `Current Connections`, `Total Method Requests/sec` | нагрузка по сайтам | Подтверждено 20.10.2026 (Microsoft, класс WMI `Win32_PerfRawData_W3SVC_WebService`: DisplayName «Current Connections», «Total Method Requests/sec») |
| `W3SVC_W3WP` (экземпляр = процесс_пул) | `Active Requests`, `Requests / Sec`, `Active Threads Count` | занятость процесса | объект упоминается Microsoft [MS TechCommunity, Exchange]; имена счётчиков ⚠ |
| `Application Request Routing Server` | `Current Requests`, `Failed Requests / Sec`, `Average Response Time / Request`, `Health`, `State` | рост ошибок и времени ответа бэкенда | [MS Learn] |

Названия на своём сервере (на русской Windows консоль показывает локализованные имена, `typeperf` и `logman` обычно принимают английские ⚠ — `../1c-windows/05-…`, разд. 8):

```bat
typeperf -qx "HTTP Service Request Queues"
typeperf -qx "APP_POOL_WAS"
typeperf -q "W3SVC_W3WP"
typeperf -q "Web Service"
:: быстрый взгляд: 12 замеров раз в 5 с
typeperf "\HTTP Service Request Queues(*)\CurrentQueueSize" "\HTTP Service Request Queues(*)\RejectedRequests" -si 5 -sc 12
```

Синтаксис `typeperf` (`-q`, `-qx`, `-si`, `-sc`) — [MS Learn]. Постоянный сборщик (параметры `logman create counter` — [MS Learn]; маска экземпляров `w3wp*` ⚠ см. `../1c-windows/05-…`):

```bat
logman create counter IIS_web -f bincirc -max 1024 -si 15 -o D:\PerfLogs\IIS_web -c "\HTTP Service Request Queues(*)\CurrentQueueSize" "\HTTP Service Request Queues(*)\RejectedRequests" "\APP_POOL_WAS(*)\Current Application Pool State" "\APP_POOL_WAS(*)\Current Application Pool Uptime" "\Process(w3wp*)\% Processor Time" "\Process(w3wp*)\Private Bytes" "\Processor(_Total)\% Processor Time" "\Memory\Available MBytes"
logman start IIS_web
logman query IIS_web
```

Автозапуск после перезагрузки — задачей планировщика, как для сборщика сервера 1С (`../1c-windows/05-…`, разд. 8.3) [практика].

### 12.3. На что ставить оповещения

[практика; события и счётчики — разделы 11–12]

| Сигнал | Порог | Почему |
|---|---|---|
| События WAS 5002 | любое | пул отключён — публикация отвечает 503 |
| События WAS 5011, Application Error 1000 по `w3wp.exe` | любое / серия | падения модуля; пять подряд → 5002 |
| `RejectedRequests` растёт | любой рост | клиенты получают 503 |
| `CurrentQueueSize` | > 0 дольше минуты | перегрузка или зависание |
| Доля 5xx в журнале сайта | > 1 % за 5 мин | ошибки приложения или прокси |
| `time-taken` p95 по `/hs/` и `/e1cib/` | выше базовой линии в 2 раза | проблемы в кластере 1С или СУБД |
| HTTPERR `QueueFull`, `AppOffline`, `Connection_Abandoned_By_AppPool` | любое | см. раздел 9.3 |
| Место на диске журналов | < 15 % | IIS не удаляет журналы сам |

---

## 13. Коды ответа и подстатусы: справочник с привязкой к 1С и прокси

Значения — [MS Learn, поддержка «HTTP status codes in IIS», KB 943891]; столбец «У 1С и прокси» — [практика] со ссылками. Коды, специфичные для публикации 1С, подробнее — `../1c-windows/03-…`, разд. 14.6.

| Код | Значение IIS | У 1С и прокси | Что делать |
|---|---|---|---|
| **400** (http.sys) | запрос нарушил правила http.sys («Header Field Too Long», «Request Header Too Long») | большой билет Kerberos; длинный сегмент URL OData | HTTPERR: `FieldLength`/`RequestLength`/`URL` → раздел 4 |
| 400.10 / 400.11 | неверный `X-Forwarded-For` / неверный запрос WebSocket | цепочка прокси / прокси WebSocket | разделы 7.5, 7.6 |
| 400.601–400.606 | ошибки ARR (400.604 — «Client gone») | клиент ушёл, не дождавшись | время ответа бэкенда |
| **401.1** / 401.2 / 401.3 | вход не выполнен / ошибка настройки аутентификации / запрещено ACL | неверные учётные данные, переполненный журнал безопасности (11.3); права NTFS на публикацию | `iis/02-…`; `../1c-windows/03-…`, разд. 6 |
| 401.501–401.504, 403.501–403.504 | динамические ограничения IP / запрет по IP или имени | частые запросы интеграций с одного адреса | `iis/02-…` |
| **403.4** / 403.6 / 403.7 / 403.16 | нужен SSL / IP отклонён / нужен клиентский сертификат / сертификат недоверенный | | `iis/02-…` |
| **403.14** | просмотр каталога запрещён | у публикации нет обработчика модуля 1С | `../1c-windows/03-…`, разд. 4.5–4.6 |
| **404.0** | не найдено | правило ARR не сработало (Grafana: шаблон, `root_url`) | FREB, «Test pattern» в URL Rewrite |
| **404.2** / **404.3** / 404.4 | ограничение ISAPI/CGI / ограничение MIME / нет обработчика | модуль 1С не разрешён; нет «Расширений ISAPI» или сопоставления `*`; нет MIME `.zip` | `../1c-windows/03-…`, разд. 2, 4.6, 11.6 |
| 404.5–404.12, 404.18, 404.19 | фильтрация запросов: последовательность, метод, расширение, скрытый сегмент, скрытый файл, длинные заголовки, двойное экранирование, «высокие» символы, строка запроса, правило | URL HTTP-сервисов и OData | `../1c-windows/03-…`, разд. 8.1 |
| **404.13** | `Content-Length` больше допустимого | загрузка больше `maxAllowedContentLength` — **на прокси тоже** | раздел 7.5 |
| 404.14 / 404.15 / 404.20 | длинный URL / строка запроса / много сегментов | OData; для 404.20 — вероятно `maxUrlSegments` (32) ⚠ | `maxUrl`, `maxQueryString`; раздел 3.1 |
| **405.0** | метод не разрешён | PUT/DELETE к HTTP-сервисам перехватывает WebDAV ⚠ | `../1c-windows/03-…`, разд. 2.1 |
| **500.0** | ошибка модуля или ISAPI | ошибка внутри 1С: нет связи с кластером, версия модуля ≠ кластера, права на `bin` | подробные ошибки локально, FREB, техжурнал |
| 500.11 / 500.12 / 500.13 | приложение останавливается / перезапускается / сервер занят | переработка, перегрузка | события WAS, раздел 2 |
| **500.19** | неверная конфигурация | `0x8007000d` — испорченный XML или секция неустановленного модуля (`<rewrite>`); `0x80070021` — секция заблокирована (`appcmd unlock config /section:<секция>`); `0x80070005` — нет прав `IIS_IUSRS` на `web.config` | [MS Learn, поддержка 500.19]; `iis/01-…` |
| **500.21** | модуль не распознан | `IsapiModule` без «Расширений ISAPI» | `Web-ISAPI-Ext` |
| 500.50–500.53 | ошибка URL Rewrite: входящее / глобальное / outbound-правило | переменная не в `allowedServerVariables`; переписывание сжатого ответа | FREB, область `Rewrite` |
| **502.3** | ARR: ошибка соединения пересылки | таймаут (win32 `12002`, `time-taken` ≈ таймаут), разрыв бэкендом (`0x80072efe`) | разделы 7.3, 7.8 [MS Learn, поддержка 502] |
| **502.4** / 502.5 | ARR: нет сервера / сбой WebSocket | все узлы фермы недоступны; нет компонента WebSocket | разделы 7.7, 7.6 |
| 502.2, 502.6, 502.7 | ARR 3.0.1916: ошибка сопоставления / пересылки / выполнения запроса | | FREB `RequestRouting` |
| **503.0** | пул недоступен | rapid-fail после падений модуля | события 5002/5011, раздел 2.4 |
| 503.2 | превышен `appConcurrentRequestLimit` | массовые долгие запросы | раздел 2.1 |
| **503** без подстатуса | отказ http.sys до IIS | `QueueFull`, `AppOffline`, `ConnLimit`, `Disabled` | раздел 9.3 |

Оговорки ⚠: KB 943891 пишет, что подстатусы 401 «видны в браузере, но не в журнале IIS», — на практике `sc-substatus` у 401 заполнен; 404.13 справочника кодов соответствует описанию 413.1 в справочнике `requestLimits` (`../1c-windows/03-…`, разд. 8.1).

---

## 14. Порядок диагностики

### 14.1. Общий путь

1. **Дошёл ли запрос до IIS?** Нет в журнале сайта — HTTPERR (раздел 9) по времени (UTC) и адресу; нет и там — сеть, брандмауэр, привязки, TLS (`iis/01-…`, `iis/02-…`).
2. **Журнал сайта:** `sc-status`.`sc-substatus`, `sc-win32-status`, `time-taken`, `sc-bytes` (раздел 8) → коды (раздел 13).
3. **Пул и процессы:** `appcmd list apppools`, `appcmd list wps`, события WAS и Application Error 1000 (раздел 11).
4. **Внутри запроса:** FREB по коду или `timeTaken` (раздел 10); у прокси — области `Rewrite`, `RequestRouting`.
5. **Подробная ошибка:** `errorMode` по умолчанию `DetailedLocalOnly` — откройте URL на самом хосте IIS; для публикации 1С ИТС предлагает «Подробные сообщения об ошибках» [MS Learn; ИТС-адм разд. 8.10.2.3] — на интернет-публикации после разбора верните (`../1c-windows/03-…`, разд. 14.4).
6. **Зависание или утечка:** «Рабочие процессы» / `Get-WebRequest`, счётчики `Process(w3wp*)`, серия дампов (FREB + ProcDump, раздел 10.3; `../1c-windows/05-…`, разд. 6).
7. **Сторона 1С:** техжурнал на хосте IIS (`VRSREQUEST`/`VRSRESPONSE`) и на сервере 1С, журнал регистрации (`../1c-windows/03-…`, разд. 14.5; `../1c/07-…`).

### 14.2. По симптомам

| Симптом | Куда смотреть сначала | Частые причины |
|---|---|---|
| Все публикации пула — 503 | `appcmd list apppools`, событие 5002 | падения модуля 1С → rapid-fail |
| 503 под нагрузкой, пул запущен | HTTPERR `QueueFull`, `CurrentQueueSize` | медленный кластер, один `w3wp` на сотни сеансов |
| Через прокси 502.3 ровно через 30 с (ферма) или 120 с (серверный прокси) | журнал прокси: `time-taken` ≈ таймауту, win32 12002 | таймаут ARR по умолчанию (разделы 7.3, 7.7) |
| Через прокси неверные ссылки | `Location`, заголовки на бэкенде | нет `X-Forwarded-*`; переименован путь |
| Большие файлы через прокси — 404.13 | журнал сайта **прокси** | `maxAllowedContentLength` на прокси |
| Медленно, ЦП IIS высокий | `Process(w3wp*)`, сжатие, outbound-правила | динамическое сжатие, переписывание ответов |
| Медленно, ЦП IIS низкий | `time-taken`, `Get-WebRequest`, кластер 1С | ожидание сервера 1С или СУБД |
| WebSocket за IIS не подключается (502.5) | компонент WebSocket на прокси | не установлен `Web-WebSockets` |

---

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| Изменение реестра http.sys не подействовало | служба HTTP не перезапускалась | `net stop http` / `net start http` + запуск W3SVC или перезагрузка; это рвёт и WinRM — в окно обслуживания [MS Learn; ИТС-адм разд. 8.10.2.4] |
| Пул «сам» останавливается после обновления платформы | модуль падает при старте → 5 сбоев за 5 мин | 5002, причина в 5011/1000; пул на версию (`../1c-windows/03-…`, разд. 3–4) [MS Learn; ИТС-адм разд. 8.10.2.2] |
| Дамп `w3wp` битый, процесс перезапустился | WAS убил процесс по таймауту ping (5010) | на время дампа `pingingEnabled=false` [MS TechCommunity; практика] |
| Длинная операция обрывается раз в сутки | переработка 29 ч, `shutdownTimeLimit` 90 с (5013) | переработка ночью по расписанию [MS Learn; практика] |
| Файловая база: теряются результаты фоновых заданий после переработки | при перекрытии два процесса | `maxProcesses=1`, `disallowOverlappingRotation=true` [ИТС-адм разд. 8.2, 8.10.2.2; MS Learn, справочник `recycling`] |
| 8.3.26+: «подвисания» веб-клиента при сотнях сеансов | один рабочий процесс | ~1 процесс на 100 сеансов [ИТС-мет 6034] |
| 503 под нагрузкой, HTTPERR `QueueFull` | очередь пула заполнена | искать медленные вызовы, добавить процессы; `queueLength` — отсрочка [MS Learn; практика] |
| За L4-балансировщиком «больной» узел получает трафик | 503 балансировщик считает ответом | `loadBalancerCapabilities=TcpLevel` [MS Learn] |
| Через ARR 502.3 на долгих отчётах и HTTP-сервисах | таймаут прокси: у фермы 30 с, у серверного прокси 120 с | поднять таймаут серверного прокси или фермы (разделы 7.3, 7.7) [MS Learn] |
| Через ARR ссылки 1С на `http://` или внутреннее имя | нет `X-Forwarded-Proto/Host/Port` | `serverVariables` + `allowedServerVariables` (7.5) [ИТС-адм разд. 8.10.3] |
| Правило с `serverVariables` даёт 500.50 | переменная не разрешена | `allowedServerVariables` [MS Learn] |
| Новый сервер: 500.19 `0x8007000d` | `<rewrite>` в `web.config`, URL Rewrite не установлен | установить URL Rewrite (и ARR) [MS Learn] |
| В журнале бэкенда у всех один IP | `c-ip` — адрес прокси | поле `X-Forwarded-For` (8.5) [MS Learn] |
| Outbound-правило не меняет ответ | ответ сжат | сжимать после прокси или не переписывать тело [MS Learn; практика] |
| После установки IIS Compression пропало динамическое сжатие | у `iiszlib.dll` уровень 0 = без сжатия | `dynamicCompressionLevel` ≥ 1 [MS Learn] |
| Диск заполнен журналами | IIS журналы не удаляет | перенос, сжатие NTFS, очистка (8.4) [MS Learn] |
| FREB включён, файлов нет | нет правила или условие не совпало | `traceFailedRequestsLogging` + правило (раздел 10) [MS Learn] |
| Внезапно у всех 500 / 401.1 «user not allowed to log on» | журнал безопасности переполнен при `CrashOnAuditFail` | очистить журнал, `CrashOnAuditFail=1`, перезагрузка [MS Learn] |

## Быстрая шпаргалка — задача → команда

`appcmd` — из `%windir%\system32\inetsrv`, всё — от имени администратора.

| Задача | Команда |
|---|---|
| Копия / откат конфигурации | `appcmd add backup before-tuning` / `appcmd restore backup "before-tuning"` |
| Параметры пула | `appcmd list apppool "1C-<версия>" /text:*` |
| Очередь пула / разрыв TCP вместо 503 | `appcmd set apppool "1C-<версия>" /queueLength:2000`; `… /failure.loadBalancerCapabilities:TcpLevel` |
| Процессов в пуле (8.3.26+) | `appcmd set apppool "1C-<версия>" /processModel.maxProcesses:4` |
| Без перекрытия (файловая база) | `appcmd set apppool "1C-file-<версия>" /recycling.disallowOverlappingRotation:true` |
| Переработать / запустить пул | `appcmd recycle apppool "1C-<версия>"` / `Start-WebAppPool -Name "1C-<версия>"` |
| Заголовки ≤ 30 с; таймаут сайта 5 мин | `appcmd set config -section:system.applicationHost/webLimits /headerWaitTimeout:"00:00:30" /commit:apphost`; `appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].limits.connectionTimeout:00:05:00" /commit:apphost` |
| Значения с умолчаниями | `appcmd list config -section:<секция> /config:*` |
| http.sys: таймауты, очереди, кеш | `netsh http show timeout`; `netsh http show servicestate view=requestq verbose=no`; `netsh http show cachestate` |
| Реестр http.sys | `Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\HTTP\Parameters"` |
| Динамическое сжатие | `Install-WindowsFeature Web-Dyn-Compression`; `appcmd set config -section:system.webServer/httpCompression /+"dynamicTypes.[mimeType='application/json',enabled='True']" /commit:apphost` |
| Прокси ARR, `Host`, все атрибуты | `appcmd set config -section:system.webServer/proxy /enabled:"True" /commit:apphost`; `… /preserveHostHeader:"True" …`; `appcmd list config -section:system.webServer/proxy /config:*` |
| Разрешить серверную переменную | `appcmd set config -section:system.webServer/rewrite/allowedServerVariables /+"[name='HTTP_X_FORWARDED_PROTO']" /commit:apphost` |
| WebSocket | `Install-WindowsFeature Web-WebSockets` |
| Поле `X-Forwarded-For` в журнале | `appcmd set config -section:system.applicationHost/sites /+"[name='Default Web Site'].logFile.customFields.[logFieldName='X-Forwarded-For',sourceName='X-Forwarded-For',sourceType='RequestHeader']" /commit:apphost` |
| FREB на сайте | `appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].traceFailedRequestsLogging.enabled:True" /commit:apphost`; правило — раздел 10.3 |
| Выполняющиеся запросы / процессы | `appcmd list requests /apppool.name:"1C-<версия>"`; `Get-WebRequest -AppPool "1C-<версия>"`; `appcmd list wps` |
| События WAS за неделю | `Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WAS'; StartTime=(Get-Date).AddDays(-7)} \| Group-Object Id` |
| Падения `w3wp` | `Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'; Id=1000} \| Where-Object Message -match 'w3wp'` |
| Счётчики очереди | `typeperf "\HTTP Service Request Queues(*)\CurrentQueueSize" "\HTTP Service Request Queues(*)\RejectedRequests" -si 5 -sc 12` |
| Трассировка WinHTTP на прокси | `netsh trace start scenario=internetclient capture=yes persistent=no level=verbose tracefile=c:\temp\net.etl` … `netsh trace stop` |

---

## Источники

Документация Microsoft, прочитана 20.10.2026 (страницы `https://learn.microsoft.com/…`; исходники — репозитории GitHub `MicrosoftDocs/…`):

- **Справочник конфигурации IIS** (`iis-docs`, `iis/configuration/…`) с образцами команд: `applicationPools/add` (+ `failure`, `processModel`, `cpu`, `recycling`, `periodicRestart`, `schedule`), `webLimits`, `sites/site/limits`, `siteDefaults/limits`, `sites/site/logFile` (+ `customFields`), `system.applicationHost/log`, `traceFailedRequestsLogging`, `sites/site/application`; `system.webServer/serverRuntime`, `httpProtocol`, `httpCompression` (+ `scheme`, `dynamicTypes`, `staticTypes`), `urlCompression`, `caching` (+ `profiles/add`), `staticContent/clientCache`, `webSocket`, `httpErrors`, `httpLogging`, `applicationInitialization`, `requestLimits`, `tracing` (+ `traceFailedRequests`, `failureDefinitions`, `traceAreas`, `traceProviderDefinitions`).
- **Статьи `iis-docs`:** Getting Started with AppCmd.exe; New Features in IIS 10.0 / 1709 / 1809; HTTP/2 on IIS; IIS Thread Pool Ideal CPU Optimization; Enhanced Logging и Logging to ETW in IIS 8.5; IIS 8.0 WebSocket Protocol Support; Multicore Scaling on NUMA Hardware; Installing IIS 8.5 on Windows Server 2012 R2 (имена компонентов); Configure Logging in IIS; Managing IIS Log File Storage; IIS Output Caching; IIS Compression Overview / Using IIS Compression; URL Rewrite — справочники 1.x и 2.0, Using URL Rewrite Module 2.0, Reverse Proxy with URL Rewrite v2 and ARR, Reverse Proxy Rule Template, Setting HTTP request headers and IIS server variables, Creating Outbound Rules; ARR — Using the ARR Module, Install ARR (v1, v2), Deployment Recommendations, Define and Configure an ARR Server Group, HTTP Load Balancing using ARR, Using Performance Counters, Using Compression in ARR, Configure and Enable Disk Cache, Support Added for WINHTTP_OPTION_SECURITY_FLAGS, ARR as generic proxy in Hotmail and SkyDrive; при независимой сверке 20.10.2026 добавлены Creating a Forward Proxy Using ARR (снимки экрана «Server Proxy Settings» с умолчаниями, шаг 5) и Configure Request Consolidation Feature in ARR (настройки прокси сервера и фермы).
- **Статьи поддержки** (`SupportArticles-docs`, `support/developer/webapps/iis/…`): HTTP status codes in IIS (KB 943891); Http.sys registry settings (KB 820129); time-taken field (KB 944884); Troubleshoot failed requests using tracing; Troubleshoot ARR using FRT rules; Troubleshooting 502 errors in ARR; Proxy server rejects requests from ARR; ARR affinity (KB 2693489); Troubleshooting HTTP 400 errors; HTTP error 500.19; Process crash in an IIS application pool; Application pool exceeds time limits during shutdown (KB 2634635); Slow page response and hangs; IIS performance issues using LogParser; HTTP.sys doesn't cache content (KB 817445); Content types for HTTP compression (KB 969062); WebSocketModule is not loaded (KB 2778043); Security event log is full (KB 832981); IIS ETW logs diagnostic (KB 2697604).
- **Tuning IIS 10.0** (`windowsserverdocs`); команды `netsh http`, `netsh trace`, `typeperf`, `logman create counter`; **HTTP Server API** (`win32`, `desktop-src/Http/…`): Configuring Error Logging, Format of the Error Logs, Types of Errors Logged.
- **Командлеты** (`windows-powershell-docs`, `winserver2025-ps`): модули `WebAdministration` и `IISAdministration` — перечни и страницы использованных командлетов.
- **Прочее Microsoft:** страницы загрузки iis.net (ARR 3.0, URL Rewrite 2.1, Advanced Logging — снят), Log Parser 2.2 (Download Center); Azure DevOps «Antivirus scanning exclusions» (текст события 5002); блог службы поддержки IIS — «Perfmon for IIS and ASP.NET» (2019), «Performance Counters for Monitoring IIS» (2019), «IIS application pool may be terminated when capturing a manual memory dump» (5010); блог Exchange (объект `W3SVC_W3WP`); справочник WMI `Win32_PerfRawData_W3SVC_WebService` (learn.microsoft.com/previous-versions, имена счётчиков `Web Service`).

1С (полные тексты ИТС 8.3.27): «Руководство администратора», разд. 8.2, 8.3.1, 8.10.2.1–8.10.2.4, 8.10.3; прил. 3.24 (`VRSREQUEST`/`VRSRESPONSE`), прил. 7 (`/TComp`); ИТС-мет 6034 (2025), 5899 (2016).

Сторонние: Grafana Labs, «Use IIS with URL Rewrite as a reverse proxy» (https://grafana.com/tutorials/iis/, 06.03.2025; перечитано 20.10.2026); WebSocket в ARR 3.0 — описания выпуска и инструкции Jenkins, Qlik (поиск 20.10.2026); копия файла схемы ARR `arr_schema.xml` в репозитории `lextm/iis_schema` на GitHub (имена атрибутов `system.webServer/proxy` и `webFarms`; не страница Microsoft — умолчания сверены со снимками экрана Microsoft).

Статьи базы: `iis/01-…`, `iis/02-…`, `../1c-windows/03-…`–`06-…`, `../apache/03-…`, `../observability/03-…`, `../guides/04-…`, `../its-docs/adm-gl08-veb-servery-p1.md`, `…-p2.md`.

## Что не удалось подтвердить

1. **Атрибуты ARR в конфигурации** для таймаута прокси, включения порта клиента в `X-Forwarded-For`, буфера ответа (серверный `system.webServer/proxy` и `webFarms/…/applicationRequestRouting/protocol` фермы): справочника схемы на learn.microsoft.com нет; имена (`timeout`, `includePortInXForwardedFor`, `responseBufferLimit`, `minResponseBuffer`) — только по копии `arr_schema.xml` в стороннем репозитории. Подписи полей и умолчания серверного прокси (120 с, «Reverse rewrite host…» и «Include TCP port…» включены, буфер 4096/256 КБ) уточнены 20.10.2026 по снимку экрана Microsoft; таймаут фермы 30 с — по статье поддержки о 502. Проверка — `appcmd list config -section:system.webServer/proxy /config:*` и `-section:webFarms /config:*`.
2. **`X-Forwarded-For` от ARR** — формат `IP:порт` (по трассировке Microsoft; флажок «Include TCP port from client IP» включён по умолчанию) и его восприятие платформой 1С.
3. **ARR 3.0 и WebSocket** — поддержка и требование компонента «Протокол WebSocket» на прокси подтверждены только сторонними источниками; у Microsoft — подстатус 502.5.
4. **Установка ARR 3.0** — остановка WAS/WMSVC (так для 1.0/2.0), состав пакета; имена модулей `RewriteModule`, `ApplicationRequestRouting` в `globalModules`.
5. **Умолчания http.sys и IIS:** `Timer_MinBytesPerSecond` 150 байт/с и `Timer_HeaderWait` 2 мин (HTTP API) против `minBytesPerSecond=240` и `headerWaitTimeout=00:00:00` (IIS); сочетание `netsh http add timeout` с настройками IIS.
6. **`time-taken` и сеть:** справочник `logFile` («не включает») против KB 944884 («включает с IIS 7.0»).
7. **Реестр http.sys:** `MaxConnections` описан в статье 2020 года, но «не используется» по «Tuning IIS 10.0» (Windows Server 2022); `MaxBufferedSendBytes` — без умолчаний; `net stop iisadmin /y` (служба есть только с совместимостью IIS 6) и ключ `/y` у `net stop http`.
8. **HTTPERR:** строка `#Fields:` (HTTP API — «заголовков нет», статья о 400 — они есть), имя пула в конце строки, причина `Connection_Abandoned_By_ReqQueue` (нет в перечне), смысл `AppShutdown` и `EntityTooLarge`, удаляются ли старые файлы `httperr*.log`.
9. **События WAS** кроме 5002/5010/5011/5013 (переработки, простой) — коды не сверены; 5002 в документации Azure DevOps отнесено к журналу «Application».
10. **Счётчики** `W3SVC_W3WP` (`Active Requests`, `Requests / Sec`, `Active Threads Count`) — имена по практике (имена `Web Service` подтверждены 20.10.2026 по классу WMI `Win32_PerfRawData_W3SVC_WebService`); маска экземпляров `Process(w3wp*)` в `logman`/`typeperf`; английские имена счётчиков на русской Windows.
11. **`appcmd list requests` / `Get-WebRequest` без «Монитора запросов»** — что показывают пусто (документирована зависимость только для «Рабочих процессов» в диспетчере); состав вывода `netsh http show servicestate`.
12. **Веб-сад:** распределение запросов между процессами; рекомендация для клиент-серверных баз до 8.3.26. (`disallowOverlappingRotation=true` для файловых баз уточнено 20.10.2026: справочник `recycling` советует `true` для кода, не поддерживающего несколько процессов.)
13. **Кеширование для 1С:** кешируемость ответов `wsisapi.dll` и польза явного выключения `caching`; MIME-типы ответов 1С для `dynamicTypes`.
14. **Длительность ISAPI-запроса:** что IIS сам не ограничивает время обработки запроса к `wsisapi.dll` и что `connectionTimeout` не действует во время обработки — вывод из описания таймеров.
15. **`SecureConnectionIgnoreFlags`** — статья Microsoft противоречит сама себе (что значит `0`).
16. **Журналы конфигурации IIS** — имена каналов для `wevtutil`.
17. **Синтаксис `appcmd` без прямого образца:** добавление в `allowedServerVariables`; набор флагов `logExtFileFlags` одной строкой; `system.webServer/proxy /enabled:` и `/timeout:`, `webFarms … protocol.timeout`; имя источника заголовка в `customFields` (`X-Forwarded-For` или `X_FORWARDED_FOR` — в документации оба). (`cpu.*` и правило FREB для `ISAPI Extension` без `areas` уточнены 20.10.2026 по справочникам `cpu` и `traceProviderDefinitions`.)
18. **Имена компонентов** (`Web-Stat-Compression`, `Web-Dyn-Compression`, `Web-WebSockets`, `Web-Request-Monitor`, `Web-AppInit`, `Web-Http-Tracing`) — из таблицы IIS 8.5; для IIS 10.0 сверить `Get-WindowsFeature Web-*`.
19. **Проверка подлинности Windows через ARR** для публикаций с `-osauth` — «не рекомендуется» по практике (NTLM и переиспользование соединений), прямого документа нет.
20. **FREB:** событие `MODULE_SET_RESPONSE_ERROR_STATUS`; применение `freb.xsl` современными браузерами. (Для `Enable-WebRequestTracing` уточнено 20.10.2026: умолчание параметра `-StatusCodes` — 500, хотя описание командлета говорит о 400–600.)
21. **Подстатусы 401 в журнале:** KB 943891 — «в журнале IIS не отображаются», на практике `sc-substatus` заполнен.
22. **Windows Server 2025** — отдельной страницы об изменениях IIS нет.
23. **Проверка работоспособности фермы ARR:** в образце Microsoft хост в `healthCheck.url` — имя самого сервера ARR; как ARR подставляет адреса узлов, из образца не видно (атрибуты `healthCheckAlternateHostName`/`Port` у сервера фермы — только в сторонней копии схемы).
24. **404.20 и `maxUrlSegments`:** справочник атрибута не называет код ответа; связь — вывод по названию подстатуса «Too Many URL Segments».
