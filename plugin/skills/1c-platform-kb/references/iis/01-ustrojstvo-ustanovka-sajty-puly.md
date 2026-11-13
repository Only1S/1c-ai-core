# IIS 10: устройство, установка, сайты, приложения, пулы приложений, конфигурация и средства управления

> **Официальные тексты по теме:** документация Microsoft по IIS (learn.microsoft.com/iis; исходники — репозиторий `MicrosoftDocs/iis-docs`): «Introduction to IIS Architectures», «IIS Modules Overview», «Introduction to ApplicationHost.config», «Deep Dive into IIS Configuration with IIS 7 and IIS 8», «How to Use Locking in IIS 7.0 Configuration», «Getting Started with AppCmd.exe», «Understanding Sites, Applications, and Virtual Directories», «Application Pool Identities», «Understanding Built-In User and Group Accounts in IIS 7», «Shared Configuration with IIS 7», «Remote Administration for IIS Manager», справочник конфигурации (`system.applicationHost/applicationPools`, `…/sites`, `…/configHistory`, `…/webLimits`, `configurationRedirection`, `system.webServer/handlers`, `…/modules`, `…/globalModules`, `…/security/isapiCgiRestriction`); справка модулей PowerShell `IISAdministration`, `WebAdministration`, `ServerManager` (набор Windows Server 2025); «Roles, Role Services, and Features included in Windows Server — Server Core»; справка `netsh http`; страница жизненного цикла IIS. По 1С: «Руководство администратора» 8.3.27, гл. 8 (`../its-docs/adm-gl08-veb-servery-p1.md`, `../its-docs/adm-gl08-veb-servery-p2.md`), методички ИТС 6034, 5977, 5944. **Публикация 1С на IIS (`webinst`, `default.vrd`, `wsisapi.dll`) — в `../1c-windows/03-veb-publikaciya-iis.md`, здесь не дублируется;** ниже только общие механизмы IIS и пометки, где они важны для 1С.

> Статус: проверено независимой сверкой 20.10.2026: с исходниками `MicrosoftDocs/iis-docs` (справочник конфигурации `applicationPools`, `processModel`, `recycling`, `periodicRestart`, `failure`, `cpu`, `sites`, `binding`, `limits`, `application`, `virtualDirectory`, `configHistory`, `configurationRedirection`, `handlers`, `modules`, `globalModules`, `isapiCgiRestriction`, `anonymousAuthentication` с образцами; статьи об архитектуре, модулях, `applicationHost.config`, блокировке, `appcmd`, удостоверениях пулов, встроенных учётных записях, общей конфигурации, истории конфигурации, удалённом управлении, установке IIS 8.5, новинках IIS 10/1709/1809), справкой PowerShell (`IISAdministration`, `WebAdministration`, `ServerManager`, `Dism`), списком ролей Server Core, справкой `netsh http` и `icacls`, страницей жизненного цикла IIS, статьями поддержки Microsoft, полным текстом гл. 8 «Руководства администратора» 1С 8.3.27 и методичками ИТС 6034, 5977, 5944; исправлено 4 ошибки, закрыто 15 пометок; на сервере не проверялось. Команды на живом IIS не выполнялись; помеченное [практика] и «⚠» проверить на стенде.

> Область: общее администрирование IIS 10.0 на Windows Server 2016–2025 — устройство (HTTP.sys, WAS, W3SVC, `w3wp.exe`, конвейер, модули, обработчики), установка роли и компонентов (в том числе на Server Core), система конфигурации (`applicationHost.config`, `web.config`, наследование, блокировка, `administration.config`, `redirection.config`), сайты и привязки, приложения и виртуальные каталоги, пулы приложений (удостоверение, режимы, запуск, переработка, простой, защита от сбоев, веб-сад), средства управления (Диспетчер IIS, `appcmd.exe`, `IISAdministration`, `WebAdministration`, удалённое управление), резервирование и перенос конфигурации, общая конфигурация, обновления, учётные записи и права NTFS. HTTPS, аутентификация, защита — `02-https-autentifikaciya-bezopasnost.md`; производительность, ARR, URL Rewrite, журналы, FREB, диагностика — `03-proizvoditelnost-arr-zhurnaly-diagnostika.md` | Версии: IIS 10.0 (Windows Server 2016, 2019, 2022, 2025; Windows 10/11 — только стенд) | Актуальность: 2026-10-20

Пометки в тексте: **[MS Learn]** — документация Microsoft (learn.microsoft.com, репозитории `MicrosoftDocs/iis-docs`, `windows-powershell-docs`, `windowsserverdocs`, `SupportArticles-docs`); **[ИТС-адм разд. N]** — «Руководство администратора» 1С:Предприятия 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС с годом; **[сторонний]** — официальные страницы других производителей и авторов; **[практика]** — устоявшаяся практика, в первоисточниках в таком виде не описана; **⚠** — не подтверждено первоисточником (пояснение рядом), полный список — в разделе «Что не удалось подтвердить».

**Как читать статью**

- Многие страницы Microsoft по IIS написаны для IIS 7.0–8.5 (2007–2013 годы). В справочнике конфигурации у каждого элемента есть строка совместимости «IIS 10.0 — не изменялся» или описание изменения; где написано именно так, утверждение действует и для IIS 10.0. Где страница старая и строки совместимости нет, это оговорено.
- Условные обозначения: `web1c.corp.local` — Windows-хост с IIS; `CORP` — домен; `srv-1c-app` — сервер 1С пользователя на Ubuntu (кластер, к которому ходит модуль 1С); `Portal` — условный сайт «не 1С» с содержимым в `D:\Sites\portal`; `1C-8.3.27.2074` — пул под конкретную сборку платформы (номер условный, как в `../1c-windows/03-…`); `demo` — публикация 1С.
- Команды PowerShell выполняются в Windows PowerShell 5.1, **запущенном от имени администратора** («Запуск от имени администратора»). Команды `appcmd` даны для `cmd.exe`: `appcmd.exe` лежит в `%windir%\system32\inetsrv\` и в `PATH` не входит [MS Learn]. В PowerShell сложные аргументы `appcmd` с кавычками и скобками лучше передавать через `cmd /c "…"` или маркер `--%` [практика].
- Смежные статьи раздела (пишутся параллельно): `02-https-autentifikaciya-bezopasnost.md` — сертификаты, привязки HTTPS, TLS и Schannel, HSTS, аутентификация (анонимная, Basic, Windows, Kerberos, делегирование), фильтрация запросов, защита сервера; `03-proizvoditelnost-arr-zhurnaly-diagnostika.md` — производительность и лимиты, сжатие, кэш, очереди и HTTP.sys, ARR и URL Rewrite (обратный прокси, балансировка), журналы W3C, FREB, коды ошибок, сбор дампов. По 1С на Windows: `../1c-windows/03-veb-publikaciya-iis.md` (публикация на IIS), `../1c-windows/04-domen-kerberos-klienty-terminalnyj-server.md` (AD, SPN, делегирование), `../1c-windows/06-windows-server-dlya-administratora-1c.md` (сама ОС, сроки поддержки). Для сравнения подходов на Linux — `../apache/01-ustanovka-i-ustrojstvo.md`.

## Кратко — главные факты

1. **IIS 10.0 — компонент Windows**: версия «10.0» на Windows Server 2016–2025 и Windows 10/11, возможности различаются выпуском ОС (1709, 1809…); поддержка — по сроку ОС [MS Learn: Lifecycle IIS]. Сроки Windows Server — `../1c-windows/06-…`, раздел 1.
2. **Цепочка:** HTTP.sys (ядро) принимает запрос и ставит в очередь пула → WAS запускает `w3wp.exe` пула → конвейер модулей → ответ в HTTP.sys. W3SVC — адаптер HTTP.sys; WAS и W3SVC — один `svchost.exe` под LocalSystem [MS Learn].
3. **Функции — модули:** нативный модуль «устанавливается» (`<globalModules>`, только сервер) и «включается» (`<modules>`); ответ формирует **обработчик** из `<handlers>` [MS Learn]. Модуль 1С `wsisapi.dll` — ISAPI-расширение: `IsapiModule`, обработчик `*`, разрешение в `<isapiCgiRestriction>` (незарегистрированные ISAPI по умолчанию запрещены) [MS Learn; `../1c-windows/03-…`].
4. **Установка:** `Install-WindowsFeature -Name Web-Server,… -IncludeManagementTools` (без ключа консоль не ставится) [MS Learn]; для 1С обязательно `Web-ISAPI-Ext` [ИТС-адм разд. 8.2]; Windows 10/11 — `Enable-WindowsOptionalFeature`, имена `IIS-*`.
5. **Server Core:** роль `Web-Server` есть, **`Web-Mgmt-Console` нет** [MS Learn] — управление PowerShell или удалённым Диспетчером IIS через WMSVC.
6. **Конфигурация сервера — XML** `%windir%\system32\inetsrv\config\applicationHost.config`; рядом `administration.config` (Диспетчер IIS), `redirection.config` (общая конфигурация), схема `schema\IIS_schema.xml` — не править [MS Learn].
7. **Наследование:** `machine.config` → корневой `web.config` .NET → `applicationHost.config` → `web.config` по дереву URL; в файле — только отличия от схемы; изменения подхватываются автоматически [MS Learn].
8. **Большинство разделов IIS заблокированы** (`overrideModeDefault="Deny"`), в том числе аутентификация: в `web.config` их не задать — только в `applicationHost.config` через `<location path="…">` (`/commit:apphost`) или после разблокировки [MS Learn].
9. **Иерархия:** сайт (привязки) → приложение (один пул) → виртуальный каталог (физический путь); корневое приложение `/` и корневой каталог `/` обязательны [MS Learn].
10. **Привязка:** `protocol` + `IP:порт:имя_узла`; `*` — все адреса, пустое имя — любое; SNI — `sslFlags=1`; подстановка `*.corp.local` — с IIS 10.0, только слева; `http://*:80/` и `http://+:80` Microsoft предупреждает не использовать [MS Learn].
11. **Умолчания пула:** `autoStart="true"`, `managedPipelineMode="Integrated"`, `managedRuntimeVersion=""` (схема IIS 8.0+), `queueLength="1000"`, `startMode="OnDemand"`, `enable32BitAppOnWin64="false"` [MS Learn]; пул 1С — «Без управляемого кода» [ИТС-адм разд. 8.2].
12. **Удостоверение — `ApplicationPoolIdentity`:** `IIS AppPool\<пул>`, в сети — `ДОМЕН\ИМЯ$`; `IIS_IUSRS` IIS сам добавляет в маркер процесса [MS Learn].
13. **Анонимные запросы — от `IUSR`**; `userName=""` в `anonymousAuthentication` — от удостоверения пула [MS Learn]. Для файловой базы 1С права на каталог базы нужны тому, от кого идёт анонимный доступ [ИТС-адм разд. 8.3.1].
14. **`processModel`:** `idleTimeout="00:20:00"` (`00:00:00` — выкл.), `idleTimeoutAction` `Terminate`/`Suspend` (8.5+), `pingResponseTime`/`shutdownTimeLimit`/`startupTimeLimit` — `00:01:30`, `maxProcesses="1"` [MS Learn].
15. **Переработка:** `periodicRestart time="29:00:00"` — «плавающее» время суток; `requests`/`memory`/`privateMemory` = 0; `schedule` — по часам; по умолчанию с перекрытием; в IIS 10 событие пишется для всех причин [MS Learn]. Для 1С — ночью по расписанию: вызов длиннее 90 с при переработке обрывается [практика].
16. **Защита от сбоев:** 5 аварий за 5 минут → пул остановлен, HTTP.sys отвечает 503 (`HttpLevel`) или рвёт TCP (`TcpLevel`); авария `w3wp` — событие WAS 5011, ошибка приложения — 1000 [MS Learn].
17. **Веб-сад** — `maxProcesses` ≥ 2 (`0` — по узлам NUMA) [MS Learn]. Файловая база 1С — строго 1 процесс [ИТС-адм разд. 8.2, 8.10.2.2]; клиент-серверная 8.3.26+ — ~1 процесс на ~100 сеансов через IIS [ИТС-мет 6034, 2025].
18. **Средства:** Диспетчер IIS (`inetmgr`, «Редактор конфигурации» с IIS 7.5), `appcmd.exe` (`%windir%\system32\inetsrv`, не в `PATH`), модули PowerShell `IISAdministration` (IIS 10.0, `Get-IISServerManager`) и `WebAdministration` (диск `IIS:\`) [MS Learn].
19. **`appcmd <команда> <объект> [<id>] [/параметр:значение]`**; объекты `SITE`, `APP`, `VDIR`, `APPPOOL`, `CONFIG`, `BACKUP`, `WP`, `REQUEST`, `MODULE`, `TRACE`; ключи `/text:*`, `/xml`, `/config`, `/commit:…` [MS Learn].
20. **Резерв:** `appcmd add backup` / `Backup-WebConfiguration` → `%windir%\system32\inetsrv\backup`; копирует серверную конфигурацию, **не `web.config` сайтов и не содержимое**; восстановление останавливает сервер. История — `%SystemDrive%\inetpub\history`, 10 копий, проверка изменений раз в 2 минуты (копия — только если файл изменился), служба ApplicationHost Helper [MS Learn].
21. **Перенос:** пароли в конфигурации зашифрованы машинными ключами `iisConfigurationKey`/`iisWasKey` — переносить ключи (`Export-IISConfiguration`, `aspnet_regiis -px/-pi`) или задавать пароли заново [MS Learn].
22. **Общая конфигурация:** `applicationHost.config` и `administration.config` на общей папке, `redirection.config` на узлах; `Enable-IISSharedConfig`; модули на всех узлах одинаковые [MS Learn]; для 1С — одна сборка `wsisapi.dll` по одному пути [практика].
23. **Удалённый Диспетчер IIS:** `Web-Mgmt-Service` (WMSVC), `EnableRemoteManagement=1` в `HKLM\SOFTWARE\Microsoft\WebManagement\Server`, автозапуск, HTTPS-порт 8172; настраивать при остановленной службе [MS Learn].
24. **HTTP.sys:** `netsh http show servicestate` — кто занял URL; `show iplisten` — непустой список ограничивает адреса всех слушателей HTTP.sys; `show sslcert` — привязки сертификатов [MS Learn].

## 1. Версии IIS 10 и выпуски Windows

### 1.1. Что менялось внутри IIS 10.0

| Выпуск Windows | Что появилось в IIS | Источник |
|---|---|---|
| Server 2016, Windows 10 | HTTP/2 в HTTP.sys; заголовки узла с подстановкой; модуль `IISAdministration`; IIS на Nano Server и в контейнерах; оптимизация пула потоков под NUMA | [MS Learn: New Features Introduced in IIS 10.0] |
| версия 1709 (SAC) | HSTS без URL Rewrite; `Get-`/`New-`/`Remove-IISSiteBinding`; серверные переменные с параметрами TLS для журналов; `IISAdministration` в PowerShell Gallery для Server 2012+ | [MS Learn: …IIS 10.0 Version 1709] |
| Server 2019 (1809) | HTTP/2 и OCSP Stapling отключаются для отдельной привязки; интерфейс HSTS; новый API сжатия (gzip, Brotli); включает всё из 1709 и 1803 | [MS Learn: …IIS 10.0, version 1809] |
| Server 2022 | в справочнике `<binding>` есть флаги `sslFlags` 16 (QUIC), 32 (TLS 1.3 поверх TCP), 64 (Legacy TLS); справочник говорит лишь, что значения больше 4 поддерживаются с IIS 10 версии 1809, а с какого выпуска работает каждый из флагов 16/32/64, не сказано ⚠ — `02-…` | [MS Learn: Binding] |
| Server 2025 | страницы «что нового в IIS» не нашёл ⚠ | — |

`New-IISSiteBinding` появился в версии 1.1.0.0 модуля [MS Learn]. Уточнено 20.10.2026 по «New Features Introduced in IIS 10.0 Version 1709»: `Get-`/`New-`/`Remove-IISSiteBinding` пришли в версии 1709, а выпуск 1809 (Server 2019) включает всё из 1709 — значит, на Server 2016 (1607) их нет без модуля из PowerShell Gallery, на Server 2019 и новее они есть (в справке набора Server 2025 перечислены).

### 1.2. Жизненный цикл, версия, 1С

- IIS — компонент ОС и следует её жизненному циклу; на странице lifecycle указаны «IIS 10 on Windows Server 2016» (до 13.01.2027) и «…2019» (до 10.01.2029), 2022 и 2025 — по датам ОС [MS Learn: Lifecycle — Internet Information Services (IIS)]. Сводка сроков — `../1c-windows/06-…`, раздел 1.1 (там 2016 — 12.01.2027: lifecycle показывает дату в часовом поясе браузера). Вывод [практика]: IIS на Server 2016 переносить до января 2027; новый хост для 1С — Server 2022; 2025 — после подтверждения 1С (`../1c-windows/03-…`, раздел 1.3).
- 1С: IIS 10.0 — Windows 10, 11, Server 2016 и новее [ИТС-адм разд. 8.1]; модулю нужны только роль, «Расширения ISAPI» и пул без .NET [ИТС-адм разд. 8.2] — их дают все эти ОС; различия выпусков сказываются на HTTPS (`02-…`).
- Windows 10/11 — только для стенда [практика]; ограничения IIS на клиентских выпусках в прочитанной документации не описаны ⚠.

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber          # выпуск Windows
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\InetStp' | Select-Object MajorVersion, MinorVersion, VersionString  # [практика ⚠]
(Get-Item "$env:windir\system32\inetsrv\w3wp.exe").VersionInfo.FileVersion                   # растёт с обновлениями [практика]
```

Ожидаемо `MajorVersion 10`, `MinorVersion 0`; ключа `InetStp` нет — роль не установлена [практика].

## 2. Устройство: как IIS обрабатывает запрос

### 2.1. Компоненты

| Компонент | Что делает | Источник |
|---|---|---|
| **HTTP.sys** | драйвер ядра: слушает сеть, держит **очередь запросов каждого пула** (запрос ждёт, пока процесс его заберёт), кэширует ответы в ядре, фильтрует запросы; с IIS 7 в его хранилище — привязки SSL-сертификатов | [MS Learn: Introduction to IIS Architectures; Changes in Security between IIS 6.0 and IIS 7] |
| **W3SVC** (служба WWW) | адаптер прослушивателя HTTP.sys: настраивает его по конфигурации и при изменениях, сообщает WAS о запросах в очереди; счётчики производительности сайтов | [MS Learn] |
| **WAS** | читает `applicationHost.config`, передаёт конфигурацию адаптерам; **управляет пулами и рабочими процессами**: запуск, переработка, контроль здоровья, защита от сбоев; может работать без W3SVC (WCF) | [MS Learn] |
| `svchost.exe` | W3SVC и WAS — в **одном** процессе под **LocalSystem** | [MS Learn] |
| **`w3wp.exe`** | рабочий процесс пула: ядро веб-сервера, модули, при необходимости .NET и ISAPI-расширения (модуль 1С) | [MS Learn] |
| ApplicationHost Helper Service | история конфигурации и сопоставление `IIS AppPool\<пул>` ↔ SID; не зависит от WAS и W3SVC, стартует автоматически; остановлена — нет истории и сопоставления имён пулов | [MS Learn: ApplicationHost Helper Service]; короткое имя `AppHostSvc` — уточнено 20.10.2026 по статье поддержки Microsoft «Configuring IIS World Wide Web Publishing Service in a Windows Server failover cluster» (`net stop apphostsvc`) |
| **WMSVC** | урезанный веб-сервер для удалённого Диспетчера IIS: HTTPS, порт 8172 | [MS Learn: Remote Administration for IIS Manager] |

```powershell
Get-Service W3SVC, WAS, WMSVC -ErrorAction SilentlyContinue | Format-Table Name, DisplayName, Status, StartType
Get-Service W3SVC -RequiredServices        # зависимости [практика]
```

### 2.2. Путь запроса

По [MS Learn: Introduction to IIS Architectures, «HTTP Request Processing»]: HTTP.sys перехватывает запрос → обращается к WAS за конфигурацией → WAS читает `applicationHost.config` → W3SVC получает сведения о пулах и сайтах и настраивает HTTP.sys → WAS запускает рабочий процесс пула (если его нет) → `w3wp` обрабатывает запрос и возвращает ответ в HTTP.sys → ответ уходит клиенту.

```
клиент ──TCP :80/:443──► HTTP.sys (ядро: TLS, URL → очередь пула, кэш)
                            ▲ настраивает: W3SVC ◄── WAS (пулы, процессы, applicationHost.config)
                            ▼ запрос из очереди
                         w3wp.exe: аутентификация → авторизация → обработчик → журнал
                                   обработчик «*» → IsapiModule → wsisapi.dll (1С) → кластер 1С
```

Следствия:

- **503 может отдать сам HTTP.sys**, без `w3wp`: очередь пула переполнена (`queueLength`, 1000) или пул остановлен защитой от сбоев [MS Learn: `<add>`, `<failure>`] — в журнале W3C такого запроса может не быть, смотреть журнал HTTP.sys (`03-…`).
- **Рабочего процесса может не быть**, пока нет запросов (`startMode="OnDemand"`), и он завершается после простоя (`idleTimeout`) — первый запрос ждёт запуска (раздел 7.4).
- Остановка W3SVC останавливает приём HTTP всеми сайтами; переработка пула затрагивает только его приложения [практика].

### 2.3. HTTP.sys: что важно администратору

- **Список прослушиваемых адресов `iplisten`** — «IP-адреса, к которым привязывается служба HTTP» [MS Learn: netsh http]. Пустой — слушаются все адреса; непустой — только перечисленные, для всех клиентов HTTP.sys (IIS, WinRM, WMSVC…) [практика: следствие описания]. Типичная причина «сайт не отвечает на новом адресе».
- **Порт может занять не IIS**, а другое приложение, зарегистрировавшее URL в HTTP.sys; кто держит URL — `netsh http show servicestate` [MS Learn].
- Кэш ядра для динамических ответов модуля 1С, как правило, не используется [практика ⚠].

```bat
netsh http show servicestate view=requestq verbose=no   :: группы URL, очереди, процессы
netsh http show iplisten                                 :: пусто — все адреса
netsh http show sslcert                                  :: привязки сертификатов (ipport, hostnameport, ccs)
netsh http show urlacl                                   :: резервирования URL
```

Синтаксис — [MS Learn: Netsh http commands]. Параметры HTTP.sys в реестре (`HKLM\SYSTEM\CurrentControlSet\Services\HTTP\Parameters`) — `03-…`, `../1c-windows/03-…`, раздел 8.2.

### 2.4. Конвейер, модули и обработчики

**Модуль** — DLL (нативный) или тип .NET (управляемый), подписанный на события конвейера: аутентификация, авторизация, выполнение обработчика, запись журнала и т. д. [MS Learn: Introduction to IIS Architectures; IIS Modules Overview]. Нативный модуль работает после двух шагов [MS Learn: IIS Modules Overview]:

1. **Установка** — запись в `<globalModules>` (имя и путь к DLL); раздел задаётся **только на уровне сервера** и только администратором. Нативный модуль получает всё, что доступно рабочему процессу, — ставить только доверенные.
2. **Включение** — запись в `<modules>` (сервер или приложение). Управляемому модулю нужен только этот шаг.

**Обработчик** (`<handlers>`) сопоставляет путь и метод запроса с модулем, который сформирует ответ. Атрибуты `<add>` [MS Learn: Adding Handlers `<add>`]: `name`, `path`, `verb` (обязательны); `modules` (умолчание `ManagedPipelineHandler`; для ISAPI-расширения — `IsapiModule`, для CGI — `CgiModule`); `scriptProcessor` — путь к DLL/EXE; `resourceType` — `File`, `Directory`, `Either` или `Unspecified` (умолчание: не важно, есть ли файл на диске); `requireAccess` — `None`, `Read`, `Write`, `Script` (умолчание), `Execute`; `preCondition` — `bitness32`, `bitness64`, `integratedMode`, `ISAPIMode`, `runtimeVersionv1.1`, `runtimeVersionv2.0`; `responseBufferLimit` — `4194304` байт. Атрибут раздела `accessPolicy` (флаги `Read`, `Script`, `Execute`, `Write`, `Source`, `None`, `NoRemote…`; в схеме — `Read`) пропускает только обработчики, чей `requireAccess` разрешён; Microsoft подчёркивает, что это фильтр выбора, а не мера безопасности [MS Learn: Handlers `<handlers>`].

Нативные модули, которые чаще всего встречаются при разборе проблем [MS Learn: Introduction to IIS Architectures, «Native Modules»; IIS Modules Overview, «Module Reference»]:

| Модуль (файл в `inetsrv`) | Что важно |
|---|---|
| `IsapiModule` (`isapi.dll`) | ISAPI-расширения, в том числе `wsisapi.dll` 1С; связан с `isapiCgiRestriction` |
| `StaticFileModule` (`static.dll`) | статика по `staticContent/mimeMap`; без него — 404. Для 1С — тип MIME `.zip` дистрибутива тонкого клиента [ИТС-адм разд. 8.10.2.6] |
| `AnonymousAuthenticationModule` (`authanon.dll`) | если не включён ни один метод аутентификации — **401.2** |
| `WindowsAuthenticationModule` (`authsspi.dll`), `BasicAuthenticationModule` (`authbas.dll`) | проверка подлинности Windows и Basic — `02-…` |
| `RequestFilteringModule` (`modrqflt.dll`) | фильтрация запросов и лимиты — `02-…`, `03-…` |
| `CustomErrorModule` (`custerr.dll`) | страницы ошибок; «подробные сообщения» вместо безликой 500 [ИТС-адм разд. 8.10.2.3] |
| `HttpLoggingModule` (`loghttp.dll`), `FailedRequestsTracingModule` (`iisfreb.dll`) | журнал W3C и FREB — `03-…` |
| `RequestMonitorModule` (`iisreqs.dll`) | учёт выполняющихся запросов (RSCA); уточнено 20.10.2026 по IIS Modules Overview: без него «средства не смогут перечислить выполняющиеся запросы» (`appcmd list requests`, `Get-WebRequest`) |
| `HttpCacheModule` (`cachhttp.dll`), `DynamicCompressionModule` (`compdyn.dll`) | кэш и сжатие — `03-…` |
| `ManagedEngine` | связь с ASP.NET; в пуле без .NET не участвует [практика ⚠] |

**Удаление лишних модулей** уменьшает поверхность атаки и память процессов [MS Learn], но рискованно: без методов аутентификации — 401.2, без `RequestFilteringModule` не действуют правила фильтрации, без `HttpRedirectionModule` открывается защищённое перенаправлением [MS Learn: Module Reference]. Безопаснее не ставить ненужные компоненты роли (раздел 3.2). Атрибут `preCondition` есть и у модулей (`managedHandler` — управляемый модуль только для управляемых обработчиков; `runAllManagedModulesForAllRequests="true"` отменяет это) [MS Learn].

```bat
cd /d %windir%\system32\inetsrv
appcmd list modules                                        :: установленные на сервере
appcmd list modules /app.name:"Default Web Site/"          :: включённые для сайта
appcmd list config "Default Web Site/demo" /section:handlers   :: обработчики публикации 1С
appcmd module /?
```

В PowerShell (`WebAdministration`): `Get-WebGlobalModule`, `Get-WebHandler -PSPath 'IIS:\Sites\Default Web Site\demo'` [MS Learn; ⚠ состав выводимых свойств не сверялся].

### 2.5. Интегрированный и классический режим конвейера

У каждого пула свой режим (`managedPipelineMode`) [MS Learn: Introduction to IIS Architectures; `<applicationPools>`]:

- **`Integrated`** (умолчание) — конвейеры IIS и ASP.NET объединены: модули ASP.NET могут обрабатывать любой тип содержимого, аутентификация не дублируется.
- **`Classic`** — как в IIS 6.0: запросы ASP.NET сначала проходят нативные этапы IIS, потом уходят в `aspnet_isapi.dll`. Нужен только старым приложениям ASP.NET, которые не работают в интегрированном режиме.

Для пула «Без управляемого кода» (`managedRuntimeVersion=""`) CLR не загружается, и режим конвейера на ISAPI-модуль 1С не влияет; оставлять умолчание `Integrated` [практика ⚠ — в документации 1С режим конвейера не упоминается].

### 2.6. Где в этом устройстве 1С

- Модуль расширения веб-сервера 1С для IIS — `wsisapi.dll` из каталога `bin` версии платформы; публикация регистрирует модуль, создаёт виртуальное приложение и каталог с `default.vrd` [ИТС-адм разд. 8.3.1]; что именно появляется в конфигурации IIS — `../1c-windows/03-…`, раздел 4.5.
- Модуль работает **внутри `w3wp.exe`** пула. Отсюда три правила 1С, которые на самом деле правила IIS:
  - разрядность модуля = разрядность рабочего процесса; 32-разрядный модуль в 64-разрядном IIS — только в пуле с `enable32BitAppOnWin64="true"` [ИТС-адм разд. 8.3.1, 8.10.2.1];
  - в одном пуле не могут работать модули, отличающиеся третьей и четвёртой цифрами версии, — пул на версию [ИТС-адм разд. 8.10.2.2];
  - каждый рабочий процесс держит свой экземпляр расширения [ИТС-адм разд. 8.2] — отсюда ограничения веб-сада (раздел 7.7).
- Для клиент-серверной базы состояние сеанса хранится в кластере 1С, а не в `w3wp`; поэтому переработка пула не теряет сеанс 1С, но обрывает **выполняющиеся** вызовы, если они длиннее `shutdownTimeLimit` (раздел 7.5) [`../1c-windows/03-…`, раздел 1.1; практика].

## 3. Установка роли и компонентов

### 3.1. Имена компонентов

Имена `Install-WindowsFeature` (Windows Server) и DISM / `Enable-WindowsOptionalFeature` (Windows 10/11) различаются. Таблица — по [MS Learn: Installing IIS 8.5 on Windows Server 2012 R2, «Modules in IIS 8.5»]; те же имена `Web-*` есть в списке ролей Server Core текущих Windows Server [MS Learn: Roles… Server Core, ред. 12.03.2025]. Звёздочка — ставится по умолчанию с ролью (по таблице IIS 8.5; ⚠ для IIS 10.0 сверить `Get-WindowsFeature`). Отображаемые имена меняются между выпусками («ASP.NET 4.5» в 2012 R2, «ASP.NET 4.6» в списке Server Core), имена `Web-*` — нет.

| Компонент | `Install-WindowsFeature` | DISM | Для 1С и общего сервера |
|---|---|---|---|
| Веб-сервер (IIS)* / Веб-сервер* | `Web-Server` / `Web-WebServer` | `IIS-WebServerRole` / `IIS-WebServer` | обязательно |
| Документ по умолчанию*, Ошибки HTTP*, Статическое содержимое* | `Web-Default-Doc`, `Web-Http-Errors`, `Web-Static-Content` | `IIS-DefaultDocument`, `IIS-HttpErrors`, `IIS-StaticContent` | нужны |
| Просмотр каталогов* | `Web-Dir-Browsing` | `IIS-DirectoryBrowsing` | не нужен; ставится по умолчанию — держать выключенным или удалить [практика] |
| Перенаправление HTTP | `Web-Http-Redirect` | `IIS-HttpRedirect` | по желанию (HTTP → HTTPS) |
| Публикация WebDAV | `Web-DAV-Publishing` | `IIS-WebDAV` | не ставить без нужды ⚠ (`../1c-windows/03-…`, раздел 2.1) |
| Ведение журнала HTTP* | `Web-Http-Logging` | `IIS-HttpLogging` | обязательно |
| Монитор запросов, Трассировка | `Web-Request-Monitor`, `Web-Http-Tracing` | `IIS-RequestMonitor`, `IIS-HttpTracing` | рекомендуются (текущие запросы, FREB) |
| Прочие журналы (пользовательский, средства, ODBC) | `Web-Custom-Logging`, `Web-Log-Libraries`, `Web-ODBC-Logging` | `IIS-CustomLogging`, `IIS-LoggingLibraries`, `IIS-ODBCLogging` | обычно не нужны |
| Сжатие статики* / динамики | `Web-Stat-Compression` / `Web-Dyn-Compression` | `IIS-HttpCompressionStatic` / `IIS-HttpCompressionDynamic` | динамика — по решению (`03-…`) |
| Фильтрация запросов* | `Web-Filtering` | `IIS-RequestFiltering` | обязательно |
| Проверка подлинности Windows | `Web-Windows-Auth` | `IIS-WindowsAuthentication` | если вход в 1С по учётной записи Windows |
| Обычная проверка подлинности, авторизация URL, ограничения по IP | `Web-Basic-Auth`, `Web-Url-Auth`, `Web-IP-Security` | `IIS-BasicAuthentication`, `IIS-URLAuthorization`, `IIS-IPSecurity` | по решению (`02-…`); IP — закрыть `/hs/`, `/odata/` снаружи |
| Центральное хранилище сертификатов; сопоставление сертификатов; дайджест | `Web-CertProvider`; `Web-Client-Auth`, `Web-Cert-Auth`; `Web-Digest-Auth` | `IIS-CertProvider`; `IIS-ClientCertificateMappingAuthentication`, `IIS-IISCertificateMappingAuthentication`; `IIS-DigestAuthentication` | фермы и особые случаи (`02-…`) |
| **Расширения ISAPI** | `Web-ISAPI-Ext` | `IIS-ISAPIExtensions` | **обязательно для 1С** [ИТС-адм разд. 8.2] |
| Фильтры ISAPI | `Web-ISAPI-Filter` | `IIS-ISAPIFilter` | ставится по ИТС-мет 5977 |
| Расширяемость .NET, ASP.NET 3.5/4.x | `Web-Net-Ext`, `Web-Net-Ext45`, `Web-Asp-Net`, `Web-Asp-Net45` | `IIS-NetFxExtensibility(45)`, `IIS-ASPNET(45)` | для 1С не нужны [ИТС-адм разд. 8.2]; нужны сайтам ASP.NET |
| Инициализация приложений | `Web-AppInit` | `IIS-ApplicationInit` | по желанию (раздел 7.4) |
| ASP, CGI, SSI, WebSocket | `Web-ASP`, `Web-CGI`, `Web-Includes`, `Web-WebSockets` | `IIS-ASP`, `IIS-CGI`, `IIS-ServerSideIncludes`, `IIS-WebSockets` | по нуждам других приложений (CGI — для FastCGI/PHP) |
| FTP | `Web-Ftp-Server`, `Web-Ftp-Service`, `Web-Ftp-Ext` | `IIS-FTPServer`, `IIS-FTPSvc`, `IIS-FTPExtensibility` | не ставить без нужды |
| Консоль управления IIS* | `Web-Mgmt-Console` | `IIS-ManagementConsole` | Desktop Experience; **в Server Core нет** |
| Сценарии и средства управления IIS | `Web-Scripting-Tools` | `IIS-ManagementScriptingTools` | рекомендуется (⚠ какой модуль PowerShell он ставит — не сверялось) |
| Служба управления | `Web-Mgmt-Service` | `IIS-ManagementService` | удалённый Диспетчер IIS (раздел 9.4) |
| Совместимость с IIS 6 | `Web-Mgmt-Compat`, `Web-Metabase`, `Web-WMI`, `Web-Lgcy-Scripting`, `Web-Lgcy-Mgmt-Console` | `IIS-IIS6ManagementCompatibility`, `IIS-Metabase`, `IIS-WMICompatibility`, `IIS-LegacyScripts`, `IIS-LegacySnapIn` | только для старых программ (ABO, ADSI) |

Группы (`Web-Common-Http`, `Web-Health`, `Web-Performance`, `Web-Security`, `Web-App-Dev`, `Web-Mgmt-Tools`) подтягиваются вместе с компонентами. Зависимости Server Manager разрешает сам; в DISM их нужно перечислять явно, иначе установка завершится неудачей без внятной ошибки [MS Learn: «Feature Dependencies»] — на Windows 10/11 удобнее `Enable-WindowsOptionalFeature … -All` [практика; `../1c-windows/03-…`, раздел 2.2] — уточнено 20.10.2026 по справке `Enable-WindowsOptionalFeature`: `-All` включает все родительские компоненты указанного и их зависимости по умолчанию.

### 3.2. Какой набор ставить

| Назначение хоста | Набор `Install-WindowsFeature` | Примечание |
|---|---|---|
| Публикация 1С (клиент-серверные базы) | `Web-Server, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Http-Tracing, Web-Request-Monitor, Web-Scripting-Tools` + `-IncludeManagementTools`; при входе по учётной записи Windows — `Web-Windows-Auth` | состав 1С — [ИТС-адм разд. 8.2; ИТС-мет 5977, 2020]; трассировка и монитор — [практика] |
| То же на Server Core | тот же набор; консоль не ставится; плюс `Web-Mgmt-Service` для удалённого Диспетчера IIS | раздел 3.4 |
| Обратный прокси (ARR) перед сервисами | `Web-Server, Web-Http-Tracing, Web-Request-Monitor`, `Web-WebSockets` (для WebSocket — Grafana Live, сервер взаимодействия; требование подтверждено только сторонними источниками ⚠, см. `03-…`, раздел 7.6) + ARR и URL Rewrite отдельными пакетами | `03-…` |
| Сайт ASP.NET Core | `Web-Server` + Hosting Bundle .NET (вне роли) | ⚠ вне темы раздела; модуль ASP.NET Core ставится пакетом Microsoft, не ролью |
| Сайт ASP.NET (Framework 4.x) | `Web-Server, Web-Asp-Net45` (подтянет `Web-Net-Ext45`, `Web-ISAPI-*`) | уточнено 20.10.2026 по таблице «Feature Dependencies» (IIS 8.5): ASP.NET 4.5 требует .NET Framework 4.5, ISAPI Extensions, ISAPI Filters, .NET Extensibility, Request Filtering; для IIS 10.0 отдельной таблицы нет |

Принцип: **ставить только нужное**. Каждый лишний компонент — лишний модуль в каждом рабочем процессе и лишняя поверхность атаки [MS Learn: Introduction to IIS Architectures, «Modules in IIS»]. Если на одном хосте живут и 1С, и сайты ASP.NET, это нормально: .NET включается **на уровне пула**, пул 1С остаётся «Без управляемого кода» [практика].

### 3.3. Команды установки и проверки

Windows Server 2016–2025, PowerShell от имени администратора (командлету нужны повышенные права) [MS Learn: Install-WindowsFeature]:

```powershell
$f = 'Web-Server','Web-ISAPI-Ext','Web-ISAPI-Filter','Web-Http-Tracing','Web-Request-Monitor','Web-Scripting-Tools'
Install-WindowsFeature -Name $f -IncludeManagementTools -WhatIf                       # что будет установлено
Install-WindowsFeature -Name $f -IncludeManagementTools -LogPath C:\Temp\iis-install.log
# проверка
Get-WindowsFeature -Name Web-* | Where-Object Installed | Format-Table Name, DisplayName -AutoSize
Get-Service W3SVC, WAS | Format-Table Name, Status, StartType
Invoke-WebRequest -Uri http://localhost/ -UseBasicParsing | Select-Object StatusCode   # 200 — стартовая страница
```

- `-IncludeManagementTools` обязателен: в отличие от мастера Server Manager, командлет **не ставит средства управления по умолчанию**. Ещё ключи: `-WhatIf`, `-LogPath`, `-Restart`, `-ComputerName`/`-Credential` (установка на другой сервер), `-ConfigurationFilePath` (XML, сохранённый мастером, — одинаковая сборка узлов фермы) [MS Learn].
- **Нет файлов компонента** (`InstallState` = `Removed`): ключ `-Source` — сетевой путь или образ WIM; порядок поиска — локальное хранилище → `-Source` → путь групповой политики (`…\Policies\Servicing\LocalSourcePath`) → Windows Update; для UNC учётной записи компьютера (`ДОМЕН\ИМЯ$`) нужно чтение. Пример из справки: `Install-WindowsFeature -Name Web-Server -Source \\server2\winsxs` [MS Learn]; ⚠ формат указания WIM с индексом в справке не приведён. 1С тоже предупреждает, что для IIS может понадобиться дистрибутив ОС [ИТС-адм разд. 8.2].
- Windows 10/11 (стенд) — `Enable-WindowsOptionalFeature -Online -All -FeatureName IIS-WebServerRole, IIS-WebServer, IIS-ISAPIExtensions, IIS-ISAPIFilter, IIS-HttpTracing, IIS-RequestMonitor, IIS-ManagementConsole, IIS-ManagementScriptingTools` (по `../1c-windows/03-…`, раздел 2.2); образец полной установки `DISM.EXE /enable-feature /online /featureName:…` — [MS Learn: Installing IIS 8.5…].
- **Удаление:** `Uninstall-WindowsFeature -Name <имя> [-IncludeManagementTools] [-Remove] [-Restart]`; без `-IncludeManagementTools` средства управления остаются; `-Remove` удаляет и файлы из `WinSxS` (потом — только с `-Source`) [MS Learn]. **Перед удалением роли — резервная копия конфигурации** (раздел 10): ⚠ сохраняется ли `applicationHost.config` при удалении и повторной установке, не сказано — считать, что настройки пропадут.

### 3.4. Server Core

- Роль `Web-Server` и почти все компоненты (включая `Web-ISAPI-Ext`, `Web-Windows-Auth`, `Web-Scripting-Tools`, `Web-Mgmt-Service`) есть в списке Server Core; **`Web-Mgmt-Console` в нём нет** [MS Learn: Roles… Server Core]. Значит, на самом сервере только PowerShell, `appcmd`, `netsh`, а графический Диспетчер IIS подключается с другой машины.
- Установка — теми же командами `Install-WindowsFeature` (локально или с другой машины `-ComputerName`) [MS Learn].
- Удалённый Диспетчер IIS: `Install-WindowsFeature -Name Web-Mgmt-Service`, затем раздел 9.4. Старая статья Microsoft для Server Core 2008 R2 описывает тот же порядок: поставить службу управления, включить удалённое управление, запустить службу [MS Learn: Install and Configure IIS 7 on Server Core].
- Первичная настройка самой ОС на Server Core (SConfig, PowerShell remoting) — `../1c-windows/06-…`, разделы 3–4. Microsoft рекомендует Server Core; веб-сервер на Core ставить можно [`../1c-windows/06-…`, раздел 1.3].
- **Для 1С:** публикация `webinst` — консольная утилита, но установщик платформы и сам модуль на Server Core ⚠ не проверялись: в документации 1С Server Core не упоминается. Для хоста публикаций 1С практичнее Desktop Experience, если нет опыта работы с Core [практика].

### 3.5. Проверка после установки

```powershell
# сайты и пулы (IISAdministration, IIS 10.0)
Import-Module IISAdministration
Get-IISSite
Get-IISAppPool
# то же через appcmd
& "$env:windir\system32\inetsrv\appcmd.exe" list sites
& "$env:windir\system32\inetsrv\appcmd.exe" list apppools
# правила брандмауэра для 80/443 [практика: имена правил ⚠ не сверялись]
Get-NetFirewallRule -Enabled True | Where-Object DisplayName -like '*World Wide Web*' |
    Format-Table DisplayName, Direction, Action
```

Ожидается [MS Learn: Getting Started with AppCmd.exe]: сайт `Default Web Site` (id 1, привязка `http/*:80:`, состояние Started) с корневым приложением и корневым виртуальным каталогом `%SystemDrive%\inetpub\wwwroot`; пул `DefaultAppPool`, который используют все новые приложения по умолчанию. В выводе `Get-IISAppPool` в справке Microsoft у `DefaultAppPool` указаны «CLR Ver v4.0, Pipeline Mode Integrated, Start Mode OnDemand» [MS Learn: Get-IISAppPool] — то есть готовый `DefaultAppPool` использует .NET 4, хотя схема по умолчанию — `""` (раздел 7.1).

С клиента: `Test-NetConnection web1c.corp.local -Port 80` [практика].

## 4. Конфигурация: файлы, иерархия, наследование, блокировка

### 4.1. Файлы конфигурации

С IIS 7 «главное» состояние конфигурации — файлы; центральной службы конфигурации нет: библиотека работает внутри процесса, который читает или пишет настройки (WAS, `w3wp`, `appcmd`, Диспетчер IIS, PowerShell) [MS Learn: Deep Dive into IIS Configuration].

| Файл или каталог | Что в нём | Источник |
|---|---|---|
| `%windir%\system32\inetsrv\config\applicationHost.config` | **корневой файл IIS**: сайты, приложения, каталоги, пулы, умолчания `system.webServer`, регистрация разделов (`<configSections>`), блокировки; единственный файл IIS сразу после установки | [MS Learn: Introduction to ApplicationHost.config] |
| `…\config\administration.config` | конфигурация Диспетчера IIS и **пользователи IIS Manager** (логины не из Windows для делегирования) | [MS Learn: An Overview of Feature Delegation] |
| `…\config\redirection.config` | `<configurationRedirection>` — общая конфигурация | [MS Learn] |
| `…\config\schema\` (`IIS_schema.xml`, `ASPNET_schema.xml`, `FX_schema.xml`) | схема: имена, типы, умолчания; сторонние модули добавляют свои файлы. **Встроенные файлы не править** — сервер может не запуститься | [MS Learn] |
| `%windir%\Microsoft.NET\Framework\v4.0.30319\Config\machine.config` и корневой `web.config` | умолчания .NET и ASP.NET (для 64-разрядных процессов — каталог `Framework64` [практика ⚠]); пул 1С без .NET их не использует | [MS Learn: The Configuration System in IIS 7] |
| `web.config` в каталогах содержимого | настройки сайта, приложения, папки (если раздел разблокирован); «по умолчанию файлов web.config нет» | [MS Learn] |
| `%SystemDrive%\inetpub\history\`, `%windir%\system32\inetsrv\backup\` | история и резервные копии (раздел 10) | [MS Learn] |

### 4.2. Иерархия, пути конфигурации, теги `<location>`

Наследование: `machine.config` → корневой `web.config` → `applicationHost.config` → `web.config` по дереву URL; настройка действует ниже, пока её не переопределят [MS Learn]. Настройка привязана к **пути**: `"Default Web Site/demo"` (`appcmd`, атрибут `path` у `<location>`), URL `"http://localhost/app1"` (`appcmd`), `MACHINE/WEBROOT/APPHOST/<сайт>` (API, `Select-WebConfiguration`), `IIS:\Sites\<сайт>\<приложение>` (`-PSPath` в `WebAdministration`) [MS Learn].

**`<location>`** задаёт настройку для пути из файла **более высокого** уровня вместо `web.config` в папке. `path`: `"."` или `""` — текущий уровень (умолчание; в `applicationHost.config` — весь сервер), `"Сайт"`, `"Сайт/приложение"`, `"Сайт/приложение/каталог"`, физическая папка или файл. Два тега не могут ссылаться на один путь для одного раздела [MS Learn: Deep Dive…]. Когда это лучше `web.config`: владельцы сайтов могут писать в каталог содержимого, а администратор хочет держать настройку у себя; содержимое на UNC; нужна одна точка администрирования; несколько путей смотрят в одну папку; настройка для отдельного файла [MS Learn].

Для 1С [практика]: **настройки публикации живут в трёх местах** — `applicationHost.config` (приложение, пул, разрешение ISAPI, аутентификация в `<location path="Default Web Site/demo">`), `web.config` каталога публикации (обработчик) и `default.vrd` (раздел 4.8).

### 4.3. Разделы, коллекции, умолчания

- **Раздел** — единица регистрации, блокировки и поиска; разделы сгруппированы (`system.applicationHost`, `system.webServer/security/authentication` …); полное имя включает группы: `system.webServer/security/authentication/windowsAuthentication` [MS Learn].
- Внутри раздела — элементы, **коллекции** (`add`/`remove`/`clear`; у сайтов директива `site`) и атрибуты. Большинство коллекций при наследовании дописывают элементы в конец, некоторые (`mergeAppend="false"`) — в начало; `<clear/>` сбрасывает унаследованное [MS Learn].
- **В файле — только отличия от схемы**; остальное из `IIS_schema.xml` [MS Learn]. Эффективное значение — `appcmd list config … /config:*` (раздел 9.2).
- `timeSpan` пишется как `чч:мм:сс` (часы могут быть больше 24: `29:00:00`) или числом секунд/минут — формат задаёт атрибут `timeSpanFormat` в схеме [MS Learn: Introduction to ApplicationHost.config, схема `<attribute>`].
- Валидаторы имён: имя пула не может содержать `|<>&"`, имя сайта — `/\.?` [MS Learn: Introduction to ApplicationHost.config]; пул `1C-8.3.27.2074` допустим. С точкой в **имени сайта** документация расходится сама с собой: при таком описании валидатора образцы справочника `<ftpServer>` используют сайт `ftp.example.com` [MS Learn] ⚠ — проверить на стенде; надёжнее давать сайтам имена без точек [практика].

### 4.4. Блокировка и делегирование

[MS Learn: Deep Dive…; How to Use Locking in IIS 7.0 Configuration; Understanding IIS Configuration Delegation]:

| Где | Атрибут | Значения |
|---|---|---|
| `<configSections>` | `overrideModeDefault` | `Allow` (если атрибута нет) / `Deny`. **Большинство разделов IIS — `Deny`**, разделы .NET — `Allow` |
| `<configSections>` | `allowDefinition` | `MachineOnly`, `MachineToRootWeb`, `MachineToApplication`, `Everywhere` (умолчание) — где раздел вообще можно задавать |
| `<location>` | `overrideMode` | `Allow`, `Deny`, `Inherit` (умолчание — решение по цепочке до `overrideModeDefault`); устаревший аналог `allowOverride`; оба в одном теге — ошибка |
| элементы раздела | `lockAttributes`, `lockElements`, `lockAllAttributesExcept`, `lockAllElementsExcept`, `lockItem` | точечная блокировка атрибутов, элементов, директив коллекции (`lockElements="remove,clear"`), отдельных элементов |

- Разблокировать можно **только на том уровне, где заблокировали**; противоречие уровней — ошибка во время работы; блокировка раздела, уже заданного ниже, даёт приложениям ошибку нарушения блокировки [MS Learn].
- Блокировка без прав NTFS на файлы конфигурации не защищает [MS Learn: An Overview of Feature Delegation].
- По образцам Microsoft: все разделы `system.applicationHost` (`applicationPools`, `sites`, `log`, `webLimits`, `listenerAdapters`, `customMetadata`) — `MachineOnly` + `Deny`; `asp`, `security/access`, `security/applicationDependencies`, `authentication/anonymousAuthentication` — `Deny`; `windowsAuthentication` «заблокирован по умолчанию»; `defaultDocument` — `Allow`; `<modules>` разблокирован, если установлен ASP.NET [MS Learn].

```xml
<!-- applicationHost.config: разблокировать windowsAuthentication только для одного сайта [MS Learn, образец] -->
<location path="AdminSuperTrustedSite" overrideMode="Allow">
  <system.webServer><security><authentication>
    <windowsAuthentication/>
  </authentication></security></system.webServer>
</location>
```

```bat
appcmd unlock config /section:asp
appcmd lock config /section:asp
```

```powershell
Import-Module WebAdministration
Get-WebConfigurationLock -PSPath 'IIS:\' -Filter '//asp'
Add-WebConfigurationLock -Type general -Filter '//asp'
Remove-WebConfigurationLock -Filter '//asp'
```

Образцы — [MS Learn: Getting Started with AppCmd.exe; Add-/Get-WebConfigurationLock]. В Диспетчере IIS — «Делегирование функций»: «Чтение/запись» = разблокировано, «Только чтение» и «Не делегировано» = заблокировано; «Настраиваемое делегирование сайта» — для одного сайта [MS Learn].

**Рекомендация** [практика]: на хосте публикаций 1С разделы аутентификации глобально не разблокировать; настройку для публикации писать в `applicationHost.config` в `<location>` её пути (`/commit:apphost`, раздел 4.5). ⚠ Что так же поступает Диспетчер IIS для заблокированных разделов, в документации не описано.

### 4.5. Куда записывается изменение: ключ `/commit`

По умолчанию `appcmd` пишет настройку на тот уровень, для которого она задана (для `"Default Web Site/"` — в `web.config` корня сайта). Ключ `/commit` меняет место записи [MS Learn: Getting Started with AppCmd.exe]:

| `/commit:` | Куда пишется |
|---|---|
| не указан или `url` | на уровень указанного пути (обычно `web.config` в этой папке) |
| `site` | `web.config` корня сайта (с `<location>` для пути ниже) |
| `app` | `web.config` корня приложения |
| `apphost` | `applicationHost.config` (с `<location path="…">` для пути) |
| `<путь>` | указанный путь конфигурации |

```bat
:: образец Microsoft: выключить просмотр каталога для приложения, записав в web.config сайта
appcmd set config http://localhost/app1/ /section:directoryBrowse /enabled:false /commit:site
```

Для **заблокированных** разделов (`asp`, аутентификация и др.) без `/commit:apphost` команда для пути ниже сервера даст ошибку нарушения блокировки; варианты — снять блокировку или записать в `applicationHost.config` (`/commit:apphost`) [MS Learn: Getting Started with AppCmd.exe, примечание к разделу `asp`]. Все образцы справочника конфигурации Microsoft для разделов `system.applicationHost` используют `/commit:apphost` и прямо требуют его [MS Learn: `<add>` пулов — примечание к образцу AppCmd].

### 4.6. Как применяются изменения

- Изменения в `.config` подхватываются автоматически; перезапускать сервер не нужно. IIS сам перерабатывает пулы, если изменение того требует [MS Learn: Getting Started with Configuration…]. Глобальные изменения затрагивают много сайтов и приложений; изменения узкой области — только их [MS Learn: Shared Configuration, «Summary»].
- Атрибут пула `disallowRotationOnConfigChange` (умолчание `false`): `true` — не перезапускать рабочие процессы пула при изменении конфигурации [MS Learn: `<recycling>`]. ⚠ Что при этом вступает в силу сразу, а что — только после следующей переработки, в документации не расписано.
- Атрибут пула `enableConfigurationOverride` (умолчание `true`): `false` — **все** настройки из `web.config` для приложений этого пула игнорируются [MS Learn: `<add>`]. Для публикации 1С это сломало бы обработчик из `web.config` публикации — не трогать [практика: следствие].
- Атрибут виртуального каталога `allowSubDirConfig` (умолчание `true`): `false` — IIS не ищет `web.config` в папках ниже этого уровня [MS Learn: `<virtualDirectory>`]. Полезно для больших файловых деревьев (дистрибутивы, вложения) [практика].
- `configSource` позволяет вынести раздел `web.config` в отдельный файл, но только в подкаталог (по соображениям безопасности) [MS Learn: Getting Started with Configuration…].
- Новые файлы схемы подхватываются при следующем запуске процесса, работающего с конфигурацией; уже работающий процесс изменения схемы не видит [MS Learn].

### 4.7. Зашифрованные атрибуты и машинные ключи

- Пароли в конфигурации (`processModel/@password` пула с `SpecificUser`, `virtualDirectory/@password`, `configurationRedirection/@password` и др.) **шифруются автоматически**, если задавать их через `appcmd` или Диспетчер IIS. Вписывать пароль в XML вручную открытым текстом Microsoft не рекомендует [MS Learn: `<processModel>`, `<virtualDirectory>`, `<configurationRedirection>`].
- Шифрованием занимаются поставщики из раздела `<configProtectedData>`: `AesProvider` — для разделов `system.webServer`, `IISWASOnlyRsaProvider` — для `system.applicationHost`. Их ключи лежат в контейнерах **`iisConfigurationKey`** и **`iisWasKey`** и **привязаны к машине** (хранилище — `%ALLUSERSPROFILE%\Microsoft\Crypto\RSA\MachineKeys\`) [MS Learn: Shared Configuration, приложение 3].
- Следствие: скопированный на другой сервер `applicationHost.config` без ключей не расшифрует пароли — пулы с `SpecificUser` не запустятся. Перенос ключей — раздел 10.3.

### 4.8. Где лежат настройки публикации 1С (для резервирования и переноса)

| Что | Где | Чем сохранить |
|---|---|---|
| Приложение `/demo`, его физический путь и пул | `applicationHost.config`, `<sites>` | `appcmd add backup` (раздел 10.1) |
| Пул `1C-<версия>` | `applicationHost.config`, `<applicationPools>` | то же |
| Разрешение `wsisapi.dll` | `applicationHost.config`, `<isapiCgiRestriction>` (только уровень сервера) | то же |
| Аутентификация публикации (анонимная, Windows) | `applicationHost.config`, `<location path="Default Web Site/demo">` — разделы заблокированы [практика ⚠: где именно пишет `webinst -osauth`, в документации 1С не сказано] | то же |
| Обработчик `*` → `wsisapi.dll` | `web.config` в каталоге публикации [практика ⚠; `../1c-windows/03-…`, раздел 4.5] | копия каталога публикации |
| `default.vrd` | каталог публикации [ИТС-адм разд. 8.3.1] | копия каталога публикации |
| Права NTFS (каталог публикации, `bin`, файловая база, `temp`) | файловая система | `icacls … /save` (раздел 10.1) |
| Сертификат HTTPS и его привязка | хранилище сертификатов компьютера + HTTP.sys | экспорт PFX и `netsh http show sslcert` — `02-…` |
| Параметры HTTP.sys и Schannel | реестр | экспорт ветвей реестра — `02-…`, `03-…` |
| Модуль `wsisapi.dll` той же сборки | `C:\Program Files\1cv8\<версия>\bin` | дистрибутив платформы |

### 4.9. Ручная правка `applicationHost.config`

1. Перед правкой — резервная копия (`appcmd add backup <имя>`) [MS Learn: «Make a backup of the file before making any changes to it»].
2. Редактор — **от имени администратора**. 32-разрядный редактор на 64-разрядной Windows при открытии `%windir%\system32\…` попадает в перенаправленный каталог `SysWOW64` и видит другой (или пустой) каталог — правка «не применяется» [практика]. Механизм уточнён 20.10.2026 по статье Win32 «File System Redirector»: обращения 32-разрядного процесса к `%windir%\System32` перенаправляются в `%windir%\SysWOW64`; без перенаправления путь можно открыть через псевдоним `%windir%\Sysnative`. Блокнот Windows — 64-разрядный.
3. Ошибка синтаксиса в `applicationHost.config` — **все сайты отвечают «HTTP Error 503. The service is unavailable.»**; лечится копированием файла из истории `%SystemDrive%\inetpub\history` в `%windir%\system32\inetsrv\config` [MS Learn: `<configHistory>`].
4. После правки — проверить, что раздел читается: `appcmd list config /section:<раздел>`; посмотреть журнал «Система» (источник WAS) [практика].
5. Схему (`schema\*.xml`) и регистрацию встроенных разделов в `<configSections>` не трогать [MS Learn].

Вместо ручной правки удобнее «Редактор конфигурации» (Configuration Editor) Диспетчера IIS — он есть с IIS 7.5 [MS Learn: IIS Modules Overview] — или `appcmd`/PowerShell.

## 5. Сайты и привязки

### 5.1. Сайт: что в него входит

Сайт — контейнер приложений и каталогов с одной или несколькими уникальными привязками; ему же принадлежат лимиты, журнал и трассировка [MS Learn: Understanding Sites, Applications, and Virtual Directories]. `<site>` [MS Learn: Site `<site>`]: `name`; `id` (у Default Web Site — 1; Диспетчер IIS даёт «случайные многозначные» номера, `appcmd add site` без `/id` — следующий свободный [MS Learn: Getting Started with AppCmd.exe]); `serverAutoStart` (`true`); дочерние `<application>`, `<bindings>`, `<limits>`, `<logFile>`, `<traceFailedRequestsLogging>`, `<applicationDefaults>`, `<virtualDirectoryDefaults>`. Умолчания всех сайтов — `<siteDefaults>`, `<applicationDefaults>` (например, `applicationPool="DefaultAppPool"`), `<virtualDirectoryDefaults>` в `<sites>`; `<limits>` сайта важнее `<siteDefaults>` [MS Learn].

`<limits>` [MS Learn]: `connectionTimeout` (`00:02:00`), `maxBandwidth` и `maxConnections` (`4294967295`), `maxUrlSegments` (`32`, IIS 8.0+). `connectionTimeout` закрывает **неактивное** соединение — простой, не пришло тело запроса, запрос слишком долго ждал в очереди пула; длительность выполнения запроса он не ограничивает [MS Learn — перечень таймеров; вывод о долгих вызовах 1С — практика ⚠]. Лимиты времени и размеров — `03-…`, `../1c-windows/03-…`, раздел 8.

### 5.2. Привязки

`protocol` (`http`, `https`, другие протоколы WAS) + `bindingInformation` = `IP:порт:имя_узла`; пустое поле — подстановка: `*` — все адреса, пустое имя — любое имя (`*:80:`, `192.168.0.1:80:www.contoso.com`, `*:443:`) [MS Learn: Binding; New-IISSiteBinding]. `sslFlags` (IIS 8.0+, умолчание `0`; значения больше 4 — IIS 10 версии 1809+) [MS Learn: Binding]:

| `0` | `1` | `2` | `4` | `8` | `16` | `32` | `64` |
|---|---|---|---|---|---|---|---|
| IP:порт, один сертификат на пару | SNI | центральное хранилище (CCS) | без HTTP/2 | без OCSP Stapling | без QUIC | без TLS 1.3 поверх TCP | без устаревших TLS |

Флаги складываются (`-SslFlag "Sni, CentralCertStore"` — образец Microsoft). Сертификаты и протоколы — `02-…`.

- У сайта должна быть хотя бы одна привязка HTTP или HTTPS [MS Learn: `<bindings>`]; `<clear/>` отменяет унаследованные из `<siteDefaults>`.
- Комбинация протокол + IP + порт + имя уникальна среди всех сайтов: сайт-дубликат не запустится [практика ⚠]. Привязка без имени узла ловит запросы с любыми именами, для которых нет своей привязки [практика].
- Имя узла сравнивается с заголовком `Host`; нужна запись DNS [MS Learn: Wildcard Host Header Support; практика].
- **Подстановка в имени** (IIS 10.0+): `*.contoso.com` — только в самой левой части (`service.*.contoso.com` нельзя); **`http://*:80/` и `http://+:80` не использовать** — уязвимость; подстановка поддомена безопасна, если весь родительский домен ваш [MS Learn].
- Сертификаты HTTPS-привязок хранятся в HTTP.sys (`netsh http show sslcert`) [MS Learn: Changes in Security…]. `Remove-IISSiteBinding` удаляет и привязку сертификата; `-RemoveConfigOnly` — только запись в `applicationHost.config`, когда сертификат на той же паре IP:порт нужен другим привязкам [MS Learn].

### 5.3. Создание сайта

Сайт `Portal`, имя `portal.corp.local`, порт 80, свой пул, каталог `D:\Sites\portal` (формы — [MS Learn: Getting Started with AppCmd.exe; New-IISSite; New-Website; Get-IISConfigSection, пример 4]):

```bat
cd /d %windir%\system32\inetsrv
md D:\Sites\portal
appcmd add apppool /name:Portal
appcmd add site /name:Portal /bindings:"http/*:80:portal.corp.local" /physicalPath:"D:\Sites\portal"
appcmd set app "Portal/" /applicationPool:Portal
appcmd list apps /site.name:Portal
icacls "D:\Sites\portal" /grant "IIS AppPool\Portal:(OI)(CI)RX"
```

`/physicalPath` сразу создаёт корневое приложение и каталог (вывод: `SITE object "Portal" added`, `APP object "Portal/" added`, `VDIR object "Portal/" added`); новое приложение попадает в `DefaultAppPool`, поэтому `set app`; `/bindings` принимает список через запятую [MS Learn].

```powershell
# IISAdministration: командлета создания пула нет — коллекция конфигурации (образец Microsoft)
Import-Module IISAdministration
Start-IISCommitDelay
$pools = Get-IISConfigSection -SectionPath 'system.applicationHost/applicationPools' | Get-IISConfigCollection
New-IISConfigCollectionElement -ConfigCollection $pools -ConfigAttribute @{ name = 'Portal'; autoStart = $true }
$site = New-IISSite -Name 'Portal' -BindingInformation '*:80:portal.corp.local' -PhysicalPath 'D:\Sites\portal' -Passthru
$site.Applications['/'].ApplicationPoolName = 'Portal'
Stop-IISCommitDelay
# WebAdministration — то же
# New-WebAppPool -Name 'Portal'; New-Website -Name 'Portal' -Port 80 -HostHeader 'portal.corp.local' -PhysicalPath 'D:\Sites\portal' -ApplicationPool 'Portal'
```

`Start-IISCommitDelay`/`Stop-IISCommitDelay` фиксируют изменения одним коммитом [MS Learn]. Через провайдер: `New-Item IIS:\Sites\Portal -bindings @{protocol="http";bindingInformation=":80:portal.corp.local"} -physicalPath D:\Sites\portal` [MS Learn: PowerShell Snap-in…].

### 5.4. Привязки: добавить, посмотреть, удалить; запуск и остановка сайтов

```bat
appcmd set site /site.name:Contoso /+bindings.[protocol='http',bindingInformation='192.168.0.1:80:www.contoso.com']
appcmd set site /site.name:Contoso /-bindings.[protocol='http',bindingInformation='192.168.0.1:80:www.contoso.com']
appcmd list sites /state:Stopped
appcmd stop site "Portal"
appcmd start site "Portal"
```

```powershell
New-IISSiteBinding -Name 'Portal' -BindingInformation '*:8080:' -Protocol http      # IISAdministration 1.1.0.0+
Get-IISSiteBinding -Name 'Portal'
Remove-IISSiteBinding -Name 'Portal' -BindingInformation '*:8080:' -Protocol http
New-WebBinding -Name 'Portal' -IPAddress '*' -Port 8081 -HostHeader 'portal.corp.local'   # WebAdministration
Stop-IISSite -Name 'Portal' -Confirm:$false; Start-IISSite -Name 'Portal'
```

Синтаксис — [MS Learn: образцы `<binding>`, справка командлетов, Getting Started with AppCmd.exe]. Удаление `/-bindings.[…]` — общее правило коллекций `appcmd` ⚠ (для привязок в образцах не встречалось). `Set-WebConfigurationProperty … -Name Bindings -Value (…)` **заменяет все** привязки сайта [MS Learn]. Сайт с `serverAutoStart="false"` после перезапуска службы останется остановленным [MS Learn].

### 5.5. Сайты и 1С

- Публикация из конфигуратора и `webinst` всегда создаётся в **Default Web Site** и **DefaultAppPool** [ИТС-адм разд. 8.2]: не удалять Default Web Site, если публикуете `webinst` ⚠ (поведение без него не описано); отдельное имя публикации (`web1c.corp.local`) — привязкой с этим именем у Default Web Site; публикация в другой сайт — вручную (`../1c-windows/03-…`, раздел 4.6).
- Другие сайты на том же хосте — на своих именах и в своих пулах; у Default Web Site лучше убрать «пустую» привязку `*:80:`, чтобы запросы с чужими именами не попадали в публикации [практика]. HTTPS для имени публикации — `02-…`, `../1c-windows/03-…`, раздел 9.

### 5.6. Привязка «не работает»: проверка по шагам

```powershell
Get-IISSite | Format-Table Name, ID, State, Bindings -AutoSize
Resolve-DnsName portal.corp.local
Get-NetTCPConnection -LocalPort 80, 443 -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess   # 4 = HTTP.sys [практика]
netsh http show iplisten
netsh http show servicestate view=requestq
Invoke-WebRequest -Uri http://portal.corp.local/ -UseBasicParsing | Select-Object StatusCode
```

Порт слушает не процесс 4 — его занял посторонний процесс; процесс 4, но сайт не стартует — URL занят другим клиентом HTTP.sys (`servicestate`) [практика]. `iplisten` не пуст и адреса нет — `netsh http add iplisten ipaddress=<адрес>` или удалить записи `netsh http delete iplisten ipaddress=<адрес>` [MS Learn]; ⚠ нужен ли после этого перезапуск HTTP-стека, справка не говорит.

## 6. Приложения и виртуальные каталоги

### 6.1. Приложение и виртуальный каталог

- **Приложение** — группа файлов, выдающая содержимое или услуги; путь — часть URL; **принадлежит одному пулу**, у управляемых приложений — свой AppDomain; у сайта обязательно корневое приложение `/` [MS Learn: Understanding Sites…; `<application>`].
- **Виртуальный каталог** — путь, сопоставленный физическому каталогу (локальному или удалённому); у приложения обязательно корневой каталог `/`; дополнительные подключают содержимое из других мест; имя, отличное от физического, хуже выдаёт структуру диска [MS Learn].
- Следствие: **граница пула — приложение**; всё, что должно работать в своём пуле (своя сборка модуля 1С, удостоверение, переработка), — приложение, а не просто каталог [практика].

`<application>` [MS Learn]: `path` (обязателен); `applicationPool` (умолчания нет — берётся из `<applicationDefaults>`, обычно `DefaultAppPool`); `enabledProtocols` (`http` — включает HTTP и HTTPS); `preloadEnabled` (IIS 8.0+, `False`; фиктивный запрос при запуске пула, нужен `AlwaysRunning`, в журнал не пишется); `serviceAutoStartEnabled` (`false`), `serviceAutoStartProvider`.

`<virtualDirectory>` [MS Learn]: `path`; `physicalPath`; `userName`/`password` («Подключаться как», пароль шифруется при задании через `appcmd`/Диспетчер IIS); `logonMethod` — `Interactive` (0), `Batch` (1), `Network` (2), `ClearText` (3, умолчание); `allowSubDirConfig` (`true`).

### 6.2. Команды

```bat
cd /d %windir%\system32\inetsrv
appcmd add app /site.name:MySite /path:/app1 /physicalPath:C:\inetpub\mysite\app1
appcmd add vdir /app.name:"MySite/app1" /path:/vdir1 /physicalPath:C:\inetpub\mysite\app1\vdir1
appcmd set app "MySite/app1" /applicationPool:MyAppPool
appcmd list apps /site.name:"Default Web Site"
appcmd list vdirs /text:physicalPath
appcmd delete app "MySite/app1"
```

```powershell
Import-Module WebAdministration
New-WebApplication -Name 'TestApp' -Site 'Default Web Site' -PhysicalPath 'C:\Test' -ApplicationPool 'DefaultAppPool'
New-WebVirtualDirectory -Site 'Default Web Site' -Name 'ContosoVDir' -PhysicalPath 'C:\inetpub\contoso'
ConvertTo-WebApplication -PSPath 'IIS:\Sites\Default Web Site\ContosoVDir' -ApplicationPool 'Portal'   # каталог → приложение
Set-ItemProperty 'IIS:\Sites\Default Web Site\TestApp' -Name applicationPool -Value 'Portal'
```

Формы — [MS Learn: Getting Started with AppCmd.exe; справка `WebAdministration`; PowerShell Snap-in…]; `appcmd delete app` — по общему описанию команды DELETE ⚠. Вывод `list apps`: `APP "Default Web Site/" (applicationPool:DefaultAppPool)` [MS Learn].

### 6.3. Содержимое на UNC и публикации 1С

- Каталог на UNC читается учётной записью «Подключаться как», если задана, иначе удостоверением запроса [MS Learn: Changes in Security…]; слежение за `web.config` на удалённых папках дорогое [MS Learn: Deep Dive…] — для больших деревьев `allowSubDirConfig="false"` или `<location>` [практика].
- Публикация 1С — одно приложение (`/demo`) в Default Web Site с `default.vrd` и `web.config` [ИТС-адм разд. 8.3.1]; каталог — не сам `%SYSTEMDRIVE%\inetpub\wwwroot` [ИТС-адм разд. 8.2], имя — латиницей [ИТС-адм разд. 8.3.1]; держать на локальном диске хоста [практика ⚠]; не вкладывать в чужие приложения — их `web.config` наследуется [практика].
- Перенос публикации в свой пул — `appcmd set app "Default Web Site/demo" /applicationPool:"1C-<версия>"`; после перепубликации проверять `appcmd list apps` (`../1c-windows/03-…`, раздел 7.3).

## 7. Пулы приложений

### 7.1. Пул и его основные атрибуты

Пул — группа из одного или нескольких рабочих процессов с общими настройками; границы процессов изолируют приложения разных пулов друг от друга. Пулов может быть сколько угодно (но каждый — память и процессы); умолчания для всех пулов — `<applicationPoolDefaults>`, атрибуты конкретного пула их переопределяют [MS Learn: Application Pools `<applicationPools>`]. Атрибуты `<add>` [MS Learn: Adding Application Pools `<add>`; в IIS 10.0 элемент не менялся]:

| Атрибут | Смысл | Умолчание |
|---|---|---|
| `name` | уникальное имя (обязателен) | — |
| `autoStart` | запускать пул при создании и при старте IIS | `true` |
| `startMode` (IIS 7.5+) | `OnDemand` — WAS запускает процесс по первому запросу; `AlwaysRunning` — всегда | `OnDemand` |
| `managedRuntimeVersion` | `v1.1`, `v2.0`, `v4.0` или `""` (без .NET) | `""` (с IIS 8.0) |
| `managedPipelineMode` | `Integrated` или `Classic` | `Integrated` |
| `enable32BitAppOnWin64` | 32-разрядный рабочий процесс на 64-разрядной Windows | `false` |
| `queueLength` | сколько запросов HTTP.sys держит в очереди пула; сверх — 503 (или обрыв TCP при `loadBalancerCapabilities="TcpLevel"`) | `1000` |
| `enableConfigurationOverride` | учитывать ли `web.config` приложений пула | `true` |
| `passAnonymousToken` | WAS передаёт модулю анонимной аутентификации маркер `IUSR` | `true` |
| `CLRConfigFile`, `managedRuntimeLoader` (IIS 7.5+) | файл конфигурации CLR; загрузчик (`webengine4.dll`) | —; `webengine4.dll` |

Дочерние элементы: `<processModel>`, `<recycling>`, `<failure>`, `<cpu>`, `<environmentVariables>` [MS Learn].

**«Без управляемого кода»** = `managedRuntimeVersion=""`. В схеме IIS 8.0+ это умолчание [MS Learn: `<add>`, `<applicationPoolDefaults>`], но готовый `DefaultAppPool` работает с `v4.0` (вывод `Get-IISAppPool` в справке Microsoft), а пулы из Диспетчера IIS создаются с версией, выбранной в диалоге (уточнено 20.10.2026 по справочнику `<add>`, «How to create a new application pool»: в окне «Добавить пул приложений» версия .NET выбирается из списка; какая стоит в нём по умолчанию, не сказано). Для пула 1С значение обязано быть «Без управляемого кода» [ИТС-адм разд. 8.2] — **проверять явно**, а не полагаться на умолчание.

**Режим конвейера** для пула без .NET на модуль 1С не влияет — оставить `Integrated` [практика ⚠]. **32-разрядность:** 32-разрядный модуль 1С на 64-разрядной Windows — только в пуле с `enable32BitAppOnWin64="true"` (Диспетчер IIS → Пулы приложений → Дополнительные параметры → «Разрешены 32-разрядные приложения») [ИТС-адм разд. 8.10.2.1]; модули и обработчики с `preCondition="bitness64"` в таком пуле не загружаются [MS Learn: `<handlers>`/`<add>`].

### 7.2. Удостоверение пула

`processModel/@identityType` [MS Learn: `<processModel>`]:

| Значение | Как работает |
|---|---|
| `ApplicationPoolIdentity` (4) | виртуальная учётная запись `IIS AppPool\<пул>`, создаётся динамически; **умолчание с IIS 7.5** |
| `NetworkService` (2) | встроенная учётная запись; в сеть — как учётная запись компьютера; умолчание IIS 7.0 |
| `LocalService` (1) | права как у NetworkService, в сети — анонимно |
| `LocalSystem` (0) | широкие права на машине; Microsoft называет запуск пула под учётной записью с высокими правами серьёзным риском |
| `SpecificUser` (3) | своя учётная запись (`userName`, `password`); пароль задавать только через `appcmd` или Диспетчер IIS — тогда он шифруется; Microsoft упоминает управляемые учётные записи служб |

В справочнике `<processModel>` противоречие: в примечании сказано, что с IIS 7.5 умолчание — `ApplicationPoolIdentity`, а в описании значений — «the default is NetworkService». Уточнено 20.10.2026: фактическое умолчание подтверждают статья «Application Pool Identities» (каждому новому пулу на IIS 7.5+ ставится `ApplicationPoolIdentity`) и справочник `<add>` пулов («now the default process identity») [MS Learn].

Что важно знать про `ApplicationPoolIdentity` [MS Learn: Application Pool Identities; Understanding Built-In User and Group Accounts]:

- Имя пула = имя виртуальной учётной записи; права выдаются на `IIS AppPool\<пул>` (в окне выбора пользователей — расположение «этот компьютер»); в оснастке «Пользователи» её нет.
- **В сеть** процесс ходит учётной записью компьютера `ДОМЕН\ИМЯ$` — как `NetworkService`; общие папки и SQL Server разрешают доступ этой учётной записи.
- **Профиль Windows** для новых пулов не создаётся (есть только у `DefaultAppPool` и `Classic .NET AppPool`); загрузку профиля включает `loadUserProfile="true"`.
- **`IIS_IUSRS`:** при запуске процесса IIS сам добавляет SID этой группы в маркер; явно добавлять удостоверения в группу не нужно. `manualGroupMembership="true"` отключает это (тогда права выдавать удостоверению явно).
- Сопоставление имени `IIS AppPool\…` и SID выполняет служба ApplicationHost Helper [MS Learn].
- `logonType` (IIS 7.5+): `LogonBatch` (умолчание) или `LogonService` — для удостоверения `SpecificUser` [MS Learn].

Команды: `appcmd set apppool "<пул>" -processModel.identityType:ApplicationPoolIdentity` [MS Learn: Application Pool Identities]; своя учётная запись — `Set-ItemProperty IIS:\AppPools\<пул> -name processModel -value @{userName="…";password="…";identitytype=3}` [MS Learn, образец]. Доменная учётная запись для пула 1С нужна редко (ферма с общим SPN, доступ к сети от имени процесса) — `../1c-windows/03-…`, разделы 6.4 и 10.5; Kerberos и SPN — `02-…`, `../1c-windows/04-…`.

### 7.3. `processModel`: процесс, простой, контроль здоровья

| Атрибут | Смысл | Умолчание [MS Learn: `<processModel>`] |
|---|---|---|
| `idleTimeout` | через сколько простоя (нет запросов, ничего не обрабатывается) процесс просит его завершить; `00:00:00` — выключить | `00:20:00` |
| `idleTimeoutAction` (IIS 8.5+) | `Terminate` — завершить; `Suspend` — выгрузить из памяти на диск, процесс «просыпается» быстрее нового | `Terminate` |
| `maxProcesses` | число рабочих процессов: `1`; `2+` — веб-сад; `0` — по числу узлов NUMA | `1` |
| `pingingEnabled`, `pingInterval`, `pingResponseTime` | контроль «живости» процесса службой WWW; не ответил за `pingResponseTime` — процесс завершается | `true`, `00:00:30`, `00:01:30` |
| `startupTimeLimit` | сколько ждать запуска процесса; превышение — процесс завершается, счётчик защиты от сбоев растёт | `00:01:30` |
| `shutdownTimeLimit` | сколько ждать завершения процесса после начала переработки; потом процесс завершается принудительно | `00:01:30` |
| `loadUserProfile` | загружать профиль удостоверения | `false` |
| `setProfileEnvironment` (IIS 8.0+) | создавать окружение процесса по профилю | `True` |
| `logEventOnProcessModel` (IIS 8.0+) | что писать в журнал (`IdleTimeout`) | `IdleTimeout` |
| `identityType`, `userName`, `password`, `logonType`, `manualGroupMembership` | раздел 7.2 | — |

⚠ Значение `loadUserProfile` в `<applicationPoolDefaults>` готового `applicationHost.config` (а не в схеме) не сверялось; от него зависит временный каталог процесса (атрибут `temp` в `default.vrd` — `../1c-windows/03-…`, раздел 5.1).

### 7.4. Запуск заранее: `AlwaysRunning`, `preloadEnabled`, Application Initialization

- `startMode="AlwaysRunning"` — WAS всегда держит пул запущенным; приложение может подготовиться до первого запроса [MS Learn: `<add>`].
- `preloadEnabled="true"` у **приложения** — IIS отправляет приложению «фиктивный» запрос при запуске пула (нужен `AlwaysRunning`) [MS Learn: `<application>`]. Полная схема — компонент «Инициализация приложений» (`Web-AppInit`, встроен с IIS 8.0) и раздел `applicationInitialization` в `web.config`; инициализация встроена в переработку с перекрытием: трафик переключается на новый процесс, когда он прошёл инициализацию [MS Learn: IIS 8.0 Application Initialization]. Microsoft предупреждает о **несовместимости Application Initialization с ARR** — не применять на машинах с ARR [MS Learn].
- `idleTimeoutAction="Suspend"` (IIS 8.5+) — простаивающий процесс выгружается на диск и быстро возвращается; задаётся для пула или в `<applicationPoolDefaults>` [MS Learn: Idle Worker Process Page-Out].
- **Для 1С** [практика]: `AlwaysRunning` + `idleTimeout="00:00:00"` убирают ожидание запуска `w3wp` по утрам. ⚠ Загружается ли `wsisapi.dll` и устанавливает ли соединения с кластером до первого запроса к публикации (то есть даёт ли `preloadEnabled` «прогрев» модуля 1С), не проверялось: ISAPI-расширение загружается при первом обращении к его обработчику.

### 7.5. Переработка (recycling)

`<recycling>` и `<periodicRestart>` [MS Learn; в IIS 10.0 изменилось только умолчание `logEventOnRecycle`]:

| Атрибут | Смысл | Умолчание |
|---|---|---|
| `periodicRestart/@time` | перезапуск через заданное время работы | `29:00:00` |
| `periodicRestart/@requests`, `@memory`, `@privateMemory` | после N запросов; при виртуальной / частной памяти больше N КБ | `0` (выкл.) |
| `periodicRestart/schedule/add/@value` | время суток (местное, 24 ч) | — |
| `disallowOverlappingRotation` | `true` — не запускать новый процесс, пока старый не завершится | `false` |
| `disallowRotationOnConfigChange` | `true` — не перезапускать при изменении конфигурации | `false` |
| `logEventOnRecycle` | причины для записи события: `Time`, `Requests`, `Schedule`, `Memory`, `IsapiUnhealthy`, `OnDemand`, `ConfigChange`, `PrivateMemory` | IIS 10 — **все**; раньше — `Time, Memory, PrivateMemory` |

- По умолчанию переработка **с перекрытием**: новые запросы идут в новый `w3wp`, старый дорабатывает текущие до `shutdownTimeLimit` (90 с) и завершается принудительно [MS Learn: `<recycling>`, `<processModel>`; IIS 8.0 Application Initialization].
- Причины: настраиваемые (время, запросы, расписание, память) и «по ходу» — по требованию, при изменении конфигурации, по сигналу ISAPI-расширения о нездоровье [MS Learn].
- `29:00:00` не кратно суткам — переработка «уплывает» и попадает на рабочий день [практика; `../1c-windows/03-…`, раздел 7.1].

**Для 1С** [практика, если не указано иное]: сеанс клиент-серверной базы живёт в кластере и переработкой не теряется, но **вызов длиннее 90 с** в старом процессе обрывается — поэтому `time="00:00:00"` + ночное `schedule`. Переработку по `privateMemory` включать только при наблюдаемом росте памяти `w3wp`. Для **файловой** базы перекрытие даёт на короткое время два процесса, а 1С требует один [ИТС-адм разд. 8.2] — можно поставить `disallowOverlappingRotation="true"`: уточнено 20.10.2026 по справочнику `<recycling>` — Microsoft советует `true`, если рабочий процесс загружает код, не поддерживающий несколько рабочих процессов; на публикации 1С не проверялось.

```bat
cd /d %windir%\system32\inetsrv
appcmd set apppool "1C-8.3.27.2074" /recycling.periodicRestart.time:00:00:00
appcmd set config -section:system.applicationHost/applicationPools /+"[name='1C-8.3.27.2074'].recycling.periodicRestart.schedule.[value='03:00:00']" /commit:apphost
appcmd list apppool "1C-8.3.27.2074" /text:*
```

Форма коллекции `schedule` с `/commit:apphost` — образец Microsoft; вложенный атрибут через точку (`/processModel.pingingEnabled:false`) — [MS Learn: Getting Started with AppCmd.exe]. События переработки — журнал «Система», источник WAS ⚠ (коды в прочитанной документации не приведены).

### 7.6. Сбои: защита от частых сбоев, ограничение CPU

`<failure>` [MS Learn: Failure Settings]:

| Атрибут | Смысл | Умолчание |
|---|---|---|
| `rapidFailProtection` | снять с обслуживания все приложения пула, если число аварий достигло порога за интервал | `true` |
| `rapidFailProtectionInterval` | окно подсчёта аварий | `00:05:00` |
| `rapidFailProtectionMaxCrashes` | порог аварий (с IIS 7.5 — от 1 до 2147483647) | `5` |
| `loadBalancerCapabilities` | что отвечать, когда процесс запустить нельзя (очередь полна, пул в защите): `HttpLevel` — 503 (балансировщик уровня HTTP поймёт, балансировщик уровня TCP сочтёт узел живым); `TcpLevel` — закрыть TCP-соединение | `HttpLevel` |
| `autoShutdownExe`, `autoShutdownParams`, `orphanWorkerProcess`, `orphanActionExe`, `orphanActionParams` | запуск программы при остановке пула; «осиротить» упавший процесс для отладки (`%1%` — PID) | —; `false` |

- Пул, остановленный защитой, сам не поднимется: устранить причину и запустить (`appcmd start apppool`, `Start-WebAppPool`) [практика].
- Авария `w3wp` видна как предупреждение **WAS 5011** («…suffered a fatal communication error with the Windows Process Activation Service…») в журнале «Система» и ошибка **Application Error 1000** в журнале «Приложение» [MS Learn: Troubleshoot a process crash in an IIS application pool]; сбор дампов — `03-…`.
- Типичные причины у пула 1С — модуль чужой разрядности или две версии модуля в одном пуле [ИТС-адм разд. 8.10.2.1, 8.10.2.2; `../1c-windows/03-…`, раздел 14].
- За узлом балансировщика уровня TCP (L4) имеет смысл `loadBalancerCapabilities="TcpLevel"`, иначе балансировщик будет слать запросы на узел, отвечающий 503 [MS Learn: описание значения].

`<cpu>` [MS Learn: CPU Settings]: `limit` — доля CPU в **тысячных долях процента** (в Диспетчере IIS 8.5+ — в процентах; `0` — без ограничения); `action` — `NoAction` (только событие), `KillW3wp`, `Throttle`, `ThrottleUnderLoad` (два последних — IIS 8.0+); `resetInterval` — `00:05:00`; NUMA — `numaNodeAssignment` (`Most Available Memory`/`Windows Scheduling`), `numaNodeAffinityMode` (`Soft`/`Hard`); привязка к процессорам — `smpAffinitized`, `smpProcessorAffinityMask`. Для пула 1С ограничение CPU с `KillW3wp` опасно: убийство процесса обрывает вызовы всех пользователей пула [практика].

### 7.7. Веб-сад и рекомендации 1С по числу рабочих процессов

- `maxProcesses` ≥ 2 — веб-сад: пул обслуживают несколько `w3wp`, запросы распределяются между ними; `0` — столько процессов, сколько узлов NUMA [MS Learn: `<processModel>`; IIS 8.0 Multicore Scaling on NUMA Hardware]. Альтернатива веб-саду — несколько пулов (разделить нагрузку по приложениям) [MS Learn: тот же документ].
- Каждый процесс держит **своё** состояние в памяти: всё, что приложение хранит в процессе, в веб-саду не разделяется [практика].
- **Файловая база 1С** — не больше одного рабочего процесса на публикацию, при фоновых заданиях — строго 1 («Максимальное число рабочих процессов» в группе «Модель процесса») [ИТС-адм разд. 8.2, 8.10.2.2].
- **Клиент-серверная база, 8.3.26 и новее** — «1 thread pool (“рабочий процесс” IIS) на каждые ~100 сеансов» через веб-публикацию; 1000 сеансов — 10; цель — избежать кратковременных зависаний [ИТС-мет 6034, 2025].

Как выполнить рекомендацию 6034 [практика ⚠ — в статье ИТС способ не указан]:

| Способ | Как | Плюсы | Минусы |
|---|---|---|---|
| Веб-сад | `maxProcesses = ⌈сеансы / 100⌉` у пула публикации | одна публикация, один адрес | все процессы одного пула перерабатываются по одному расписанию; ⚠ равномерность распределения запросов между процессами не документирована |
| Несколько пулов | несколько публикаций одной базы (разные имена, разные пулы), пользователи разнесены по ним | изоляция групп (например, OData/обмены отдельно) | несколько адресов, списки баз у пользователей |

Каждый `w3wp` держит свой экземпляр модуля 1С и свой пул соединений с кластером [ИТС-адм разд. 8.2; `../1c-windows/03-…`, раздел 7.4] — учитывать в памяти хоста. Число подбирать нагрузочным тестом.

### 7.8. Профиль пула для публикации 1С

| Параметр | Значение | Источник |
|---|---|---|
| Пул | отдельный на каждую сборку платформы (`1C-8.3.27.2074`) | [ИТС-адм разд. 8.2, 8.10.2.2] |
| `managedRuntimeVersion` | `""` («Без управляемого кода») | [ИТС-адм разд. 8.2] |
| `enable32BitAppOnWin64` | `false` (64-разрядная 1С) | [ИТС-адм разд. 8.10.2.1] |
| `identityType` | `ApplicationPoolIdentity`, если нет причин иначе | [MS Learn; `../1c-windows/03-…`, раздел 6.4] |
| `startMode` / `idleTimeout` | `AlwaysRunning` / `00:00:00` | [практика] |
| `periodicRestart/@time` + `schedule` | `00:00:00` + ночное время | [практика] |
| `maxProcesses` | файловая — `1`; клиент-серверная 8.3.26+ — около 1 на 100 сеансов | [ИТС-адм разд. 8.10.2.2; ИТС-мет 6034] |
| `rapidFailProtection` | оставить `true`, следить за событиями WAS | [практика] |

Два равноценных способа (выполнять один); в `WebAdministration` то же делается `New-WebAppPool` и `Set-ItemProperty "IIS:\AppPools\<пул>" -Name managedRuntimeVersion -Value ''` (и `-Name processModel -Value @{ idleTimeout = '00:00:00' }`) по образцам [MS Learn], но добавить время в `schedule` из `WebAdministration` в образцах не показано ⚠:

```bat
:: 1) appcmd, cmd.exe от имени администратора
set POOL=1C-8.3.27.2074
cd /d %windir%\system32\inetsrv
appcmd add apppool /name:"%POOL%"
appcmd set apppool "%POOL%" /managedRuntimeVersion:"" /enable32BitAppOnWin64:false /startMode:AlwaysRunning
appcmd set apppool "%POOL%" /processModel.idleTimeout:00:00:00 /recycling.periodicRestart.time:00:00:00
appcmd set config -section:system.applicationHost/applicationPools /+"[name='%POOL%'].recycling.periodicRestart.schedule.[value='03:00:00']" /commit:apphost
appcmd set app "Default Web Site/demo" /applicationPool:"%POOL%"
appcmd list apppool "%POOL%" /text:*
```

Несколько атрибутов в одной команде `set` — допустимо («Specify more than one property in a single command-line») [MS Learn]. Пустое значение `""` для `managedRuntimeVersion` — [практика; `../1c-windows/03-…`, раздел 4.6].

```powershell
# 2) IISAdministration + Microsoft.Web.Administration (IIS 10.0)
Import-Module IISAdministration
$sm = Get-IISServerManager
$p  = $sm.ApplicationPools.Add('1C-8.3.27.2074')
$p.ManagedRuntimeVersion = ''
$p.Enable32BitAppOnWin64 = $false
$p.StartMode = 'AlwaysRunning'
$p.ProcessModel.IdleTimeout = [TimeSpan]::Zero
$p.Recycling.PeriodicRestart.Time = [TimeSpan]::Zero
[void]$p.Recycling.PeriodicRestart.Schedule.Add([TimeSpan]'03:00:00')
$sm.Sites['Default Web Site'].Applications['/demo'].ApplicationPoolName = $p.Name
$sm.CommitChanges()
Reset-IISServerManager -Confirm:$false; Get-IISAppPool -Name '1C-8.3.27.2074'
```

Имена свойств и методов (`ApplicationPools.Add(String)`, `ProcessModel.IdleTimeout`, `Recycling.PeriodicRestart.Time`, `Schedule.Add(TimeSpan)`, `CommitChanges`) — по справочнику API `Microsoft.Web.Administration` [MS Learn]; ⚠ сценарий целиком не выполнялся. `Reset-IISServerManager` сбрасывает кэшированное представление конфигурации у командлетов модуля [MS Learn].

### 7.9. Управление состоянием пулов и рабочих процессов

```bat
cd /d %windir%\system32\inetsrv
appcmd list apppools                               :: все пулы: версия CLR, режим, состояние
appcmd list apppools /state:started
appcmd recycle apppool "1C-8.3.27.2074"            :: переработать (с перекрытием)
appcmd stop apppool "1C-8.3.27.2074"
appcmd start apppool "1C-8.3.27.2074"
appcmd list wps                                    :: рабочие процессы: PID и пул
appcmd list wps /apppool.name:"1C-8.3.27.2074"
appcmd list requests /apppool.name:"1C-8.3.27.2074" :: выполняющиеся запросы и их длительность
```

```powershell
Get-IISAppPool                                       # IISAdministration
(Get-IISServerManager).ApplicationPools['1C-8.3.27.2074'].Recycle()
Import-Module WebAdministration
Get-WebAppPoolState -Name '1C-8.3.27.2074'
Restart-WebAppPool -Name '1C-8.3.27.2074'
Stop-WebAppPool -Name '1C-8.3.27.2074'; Start-WebAppPool -Name '1C-8.3.27.2074'
Get-ChildItem 'IIS:\AppPools\1C-8.3.27.2074\WorkerProcesses'
Get-WebRequest -AppPool '1C-8.3.27.2074'
```

Формы `list wps /apppool.name:…`, `list requests`, `recycle` — [MS Learn: Getting Started with AppCmd.exe; An End-to-End Extensibility Example for IIS 7.0 Developers: `appcmd recycle AppPool DefaultAppPool`]; `start`/`stop apppool` — уточнено 20.10.2026 по архивной справке Microsoft «Start or Stop an Application Pool (IIS 7)»: `appcmd start|stop apppool /apppool.name:<имя>` (имя можно дать и идентификатором, как у `list apppool`); остановленный пул WAS сам не запускает, его приложения получают 503. Командлеты — [MS Learn: справка `IISAdministration`, `WebAdministration`; PowerShell Snap-in: Run-time Data]. Переработка через WAS мягче, чем `iisreset`, который перезапускает все службы IIS [практика]. Для текущих запросов нужен компонент «Монитор запросов» (`Web-Request-Monitor`) [практика ⚠].

## 8. Учётные записи и права NTFS

### 8.1. Кто есть кто

| Учётная запись / группа | Что это | Источник |
|---|---|---|
| `IIS AppPool\<пул>` | виртуальная учётная запись пула (`ApplicationPoolIdentity`) | [MS Learn] |
| `IUSR` | встроенная учётная запись анонимной аутентификации IIS 7+ (заменила `IUSR_<имя_компьютера>`); пароля нет, имя не локализуется; в сети действует анонимно — для доступа к сети анонимному пользователю нужна своя учётная запись | [MS Learn: Understanding Built-In User and Group Accounts] |
| `IIS_IUSRS` | встроенная группа (заменила `IIS_WPG`) с доступом к нужным IIS ресурсам; SID одинаков на всех машинах — списки доступа переносятся `xcopy /o`; добавляется в маркер рабочих процессов автоматически | [MS Learn] |
| `NT Service\WMSVC` | учётная запись службы удалённого управления; к UNC-содержимому доступа не имеет | [MS Learn: Configuring Remote Administration and Feature Delegation] |
| пользователь запроса | при проверке подлинности Windows или Basic — сам пользователь (олицетворение) | [MS Learn: Changes in Security…, «How IIS Determines the Authenticated Identity»; ИТС-адм разд. 8.9.1] |

Порядок выбора удостоверения запроса [MS Learn: Changes in Security…]: учётные данные виртуального каталога («Подключаться как»), если заданы; иначе — удостоверение, полученное при аутентификации (анонимная учётная запись или пользователь); если пользователь не установлен (например, Forms) — удостоверение процесса; иначе — отказ в доступе.

### 8.2. Анонимное удостоверение: `IUSR` или пул

По умолчанию `anonymousAuthentication` использует `IUSR`. Если задать **пустое** имя пользователя, анонимные запросы выполняются от удостоверения пула — одной учётной записи меньше в списках доступа; пустая строка и отсутствие атрибута ведут себя по-разному [MS Learn: Application Pool Identity as Anonymous User]:

```bat
:: весь сервер (образец Microsoft)
%windir%\system32\inetsrv\appcmd set config -section:anonymousAuthentication /username:"" --password
```

```powershell
Import-Module WebAdministration
Set-WebConfigurationProperty /system.webServer/security/authentication/anonymousAuthentication -name userName -value ""
```

Раздел `anonymousAuthentication` заблокирован (`Deny`), поэтому для отдельного сайта настройка пишется в `applicationHost.config`: `appcmd set config "Portal" -section:system.webServer/security/authentication/anonymousAuthentication /userName:"" /commit:apphost` (уточнено 20.10.2026 по справочнику `<anonymousAuthentication>`: образец Microsoft для сайта `Contoso` — та же форма с `/userName:"IUSR"` и `/commit:apphost`).

**Для 1С:** при анонимной аутентификации и **файловой** базе публикация проверяет права на каталог базы у пользователя, от лица которого выполняется анонимный доступ [ИТС-адм разд. 8.3.1]; 1С формулирует права через `IIS_IUSRS` [ИТС-адм разд. 8.4.3.2.1]. ⚠ Будет ли при `userName=""` достаточно прав `IIS_IUSRS` (группа в маркере пула) — по документации так, но на публикации 1С не проверялось. Методы аутентификации и вход по учётной записи Windows — `02-…`, `../1c-windows/03-…`, раздел 10.

### 8.3. Права на содержимое

Принцип [практика]: удостоверению пула — чтение и выполнение на каталог сайта; изменение — только на те подкаталоги, куда приложение пишет; анонимному удостоверению (`IUSR`, если оно не заменено пулом) — чтение того, что отдаётся анонимно.

```bat
:: чтение и выполнение каталога сайта для удостоверения пула
icacls "D:\Sites\portal" /grant "IIS AppPool\Portal:(OI)(CI)RX"
:: запись только в каталог данных
icacls "D:\Sites\portal\data" /grant "IIS AppPool\Portal:(OI)(CI)M"
:: анонимный доступ через IUSR
icacls "D:\Sites\portal" /grant "IUSR:(OI)(CI)RX"
:: проверка
icacls "D:\Sites\portal"
```

Синтаксис выдачи прав виртуальной учётной записи — [MS Learn: `ICACLS test.txt /grant "IIS AppPool\DefaultAppPool:F"`]; наследование `(OI)(CI)`, права `RX` (чтение и выполнение) и `M` (изменение) — [MS Learn: справка `icacls`]. Если `icacls` не находит `IIS AppPool\…`: пул ещё не создан, имя с ошибкой или остановлена служба ApplicationHost Helper [MS Learn: ApplicationHost Helper Service].

**Права для 1С** (каталог `bin` версии, файловая база, каталог `temp` модуля, каталог техжурнала) — `../1c-windows/03-…`, раздел 6; в документации 1С они сформулированы для `IIS_IUSRS` [ИТС-адм разд. 8.4.3.2.1]. Для конкретного пула можно выдавать права на `IIS AppPool\1C-<версия>` [практика].

### 8.4. Права на сами файлы IIS

- Каталог `%windir%\system32\inetsrv\config` и схема — только администраторы [MS Learn: Deep Dive…; Getting Started with Configuration…].
- Делегирование владельцам сайтов — через блокировку разделов **и** права NTFS на их `web.config`: одна блокировка не защищает [MS Learn: An Overview of Feature Delegation].
- Резервные копии и экспорт ключей (раздел 10) содержат секреты — хранить с ограниченным доступом [практика].

## 9. Средства управления

### 9.1. Диспетчер IIS

`inetmgr` (`Web-Mgmt-Console`): «Модули» и «Сопоставления обработчиков» (раздел 2.4); «Редактор конфигурации» (IIS 7.5+) — любой раздел и атрибут, в том числе отсутствующие в формах (`webLimits`, `applicationPoolDefaults`); «Делегирование функций» (раздел 4.4); «Общая конфигурация» (раздел 10.4); «Служба управления» (раздел 9.4); «Пулы приложений → Дополнительные параметры» [MS Learn: IIS Modules Overview; An Overview of Feature Delegation; Shared Configuration; Dynamic Site Activation]. К удалённым серверам, сайтам и приложениям подключается через WMSVC.

### 9.2. `appcmd.exe`

`%systemroot%\system32\inetsrv\appcmd.exe`, не в `PATH`. Синтаксис `APPCMD (команда) (объект) <идентификатор> < /параметр:значение … >`; у большинства объектов — `LIST`, `ADD`, `DELETE`, `SET`, у некоторых свои (`START`/`STOP` у сайта, `RECYCLE` у пула). Объекты и идентификаторы: `SITE` (имя), `APP` (`Сайт/приложение`), `VDIR` (путь), `APPPOOL` (имя), `CONFIG` (путь конфигурации), `BACKUP` (имя копии), `WP` (PID), `REQUEST`, `MODULE`, `TRACE` [MS Learn: Getting Started with AppCmd.exe].

| Приём | Пример [MS Learn] |
|---|---|
| справка | `appcmd /?`, `appcmd site /?`, `appcmd list app /?`, `appcmd set config /section:asp /?` |
| поиск по свойствам; все свойства; одно свойство | `appcmd list sites /state:Stopped`; `appcmd list apppool "MyAppPool" /text:*`; `appcmd list vdirs /text:physicalPath` |
| XML; эффективная конфигурация с умолчаниями; список разделов | `appcmd list site "Default Web Site" /config`, `/xml`; `appcmd list config "Default Web Site/" /section:asp /config:*`; `appcmd list config /section:?` |
| вложенный атрибут; элемент коллекции (изменить / добавить / удалить) | `/processModel.pingingEnabled:false`; `/[name='X'].type:…`, `/+[name='X',type='…']`, `/-[name='X']` |
| поиск, где задано; блокировка; место записи | `appcmd search config "Default Web Site/" /section:directoryBrowse /enabled:true`; `appcmd lock`/`unlock config /section:asp`; `/commit:…` (раздел 4.5) |

Вывод `/xml` можно подать на вход другой команде `appcmd` [MS Learn — назначение; ⚠ ключ ввода и формат не описаны, подробности — в блоге автора, [сторонний: mvolo.com]]. Из PowerShell: `& "$env:windir\system32\inetsrv\appcmd.exe" …`, аргументы со скобками и кавычками — через `cmd /c` [практика].

### 9.3. PowerShell: `IISAdministration` и `WebAdministration`

**`IISAdministration`** — с IIS 10.0 рядом с `WebAdministration`: лучше масштабируется, даёт прямой доступ к `Microsoft.Web.Administration.ServerManager`, рассчитан на конвейер; новые версии — в PowerShell Gallery, в том числе для Server 2012+ [MS Learn: IISAdministration PowerShell Cmdlets]. 34 командлета (набор Server 2025) [MS Learn: IISAdministration Module]: сайты — `Get-`, `New-`, `Remove-`, `Start-`, `Stop-IISSite`; привязки — `Get-`, `New-`, `Remove-IISSiteBinding`; пулы — только `Get-IISAppPool` (создание — через `ServerManager` или коллекцию конфигурации); конфигурация — `Get-IISConfigSection`, `Get-IISConfigCollection`, `Get-IISConfigCollectionElement`, `Get-IISConfigElement`, `Get-`/`Set-IISConfigAttributeValue`, `New-`/`Remove-IISConfigCollectionElement`, `Remove-IISConfigElement`, `Remove-IISConfigAttribute`, `Clear-IISConfigCollection`; транзакции и API — `Start-`/`Stop-IISCommitDelay`, `Get-`/`Reset-IISServerManager`; общая конфигурация — `Export-IISConfiguration`, `Enable-`/`Disable-`/`Get-IISSharedConfig`; центральное хранилище сертификатов — `*-IISCentralCertProvider*` (`02-…`).

```powershell
Import-Module IISAdministration
$sites = Get-IISConfigSection -SectionPath 'system.applicationHost/sites' | Get-IISConfigCollection
$dws   = Get-IISConfigCollectionElement -ConfigCollection $sites -ConfigAttribute @{ name = 'Default Web Site' }
$lim   = Get-IISConfigElement -ConfigElement $dws -ChildElementName 'limits'
Get-IISConfigAttributeValue -ConfigElement $lim -AttributeName 'maxUrlSegments'
Set-IISConfigAttributeValue -ConfigElement $lim -AttributeName 'maxUrlSegments' -AttributeValue 64
```

Образец — [MS Learn]. `Set-IISConfigAttributeValue` меняет значение у переданного элемента, не обязательно эффективное для пути (для этого элемент берут с `-CommitPath` поглубже); имя раздела в `-SectionPath` чувствительно к регистру [MS Learn].

**`WebAdministration`** — прежний модуль (провайдер `IIS:\Sites`, `IIS:\AppPools`, `IIS:\AppPools\<пул>\WorkerProcesses`) [MS Learn: справка; PowerShell Snap-in…]: объекты — `New-Website`, `New-WebApplication`, `New-WebVirtualDirectory`, `New-WebAppPool`, `New-WebBinding`, `ConvertTo-WebApplication`, `New-Item`/`Set-ItemProperty`/`New-ItemProperty` на `IIS:\`; состояние — `Start-`/`Stop-`/`Restart-WebAppPool`, `Get-WebAppPoolState`, `Get-WebsiteState`, `Get-WebItemState`, `Restart-WebItem`, `Get-WebRequest`; конфигурация — `Get-`/`Set-`/`Add-WebConfigurationProperty`, `Get-`/`Set-`/`Add-`/`Clear-WebConfiguration` (`-PSPath`, `-Filter` с XPath, `-Location`), `*-WebConfigurationLock`; резерв — `Backup-`/`Restore-WebConfiguration`, `Get-`/`Remove-WebConfigurationBackup`.

**Что выбрать** [практика, если не указано иное]: быстрая проверка — `appcmd … /text:*`; сценарии cmd — `appcmd` (на нём образцы справочника Microsoft [MS Learn]); сценарии PowerShell на IIS 10 — `IISAdministration` + `ServerManager`; старые сценарии — `WebAdministration`; редкие атрибуты — Редактор конфигурации. ⚠ Работа обоих модулей в PowerShell 7 не проверялась — запускать в Windows PowerShell 5.1.

### 9.4. Удалённое управление

**Диспетчер IIS через WMSVC** [MS Learn: Remote Administration for IIS Manager; Configuring Remote Administration and Feature Delegation]: поставить `Web-Mgmt-Service`; включить DWORD `EnableRemoteManagement=1` в `HKLM\SOFTWARE\Microsoft\WebManagement\Server` (флажок «Разрешить удалённые подключения»); **настраивать, пока служба остановлена**; привязка по умолчанию — все неназначенные адреса, порт **8172**, самоподписанный сертификат, только HTTPS; учётные данные — Windows или ещё пользователи IIS Manager (`administration.config`); журнал — `%SystemDrive%\Inetpub\logs\WMSVC`; установка создаёт правило брандмауэра на 8172; тип запуска по умолчанию «Вручную» — поставить «Автоматически» (WMSVC зависит от HTTP.sys).

```powershell
Install-WindowsFeature -Name Web-Mgmt-Service
Stop-Service WMSVC -ErrorAction SilentlyContinue
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\WebManagement\Server' -Name EnableRemoteManagement -Value 1 -Type DWord
Set-Service -Name WMSVC -StartupType Automatic; Start-Service -Name WMSVC
Test-NetConnection web1c.corp.local -Port 8172      # с рабочего места администратора
```

Образцы Microsoft — `.reg`-файл, `net start WMSVC`, `sc.exe config WMSVC start= auto`; командлеты — эквивалент [практика]. Подключение — «Файл → Подключиться к серверу» в Диспетчере IIS; на Windows 10/11 нужен отдельный «IIS Manager for Remote Administration» ⚠ (актуальность для Windows 11 не проверялась).

**PowerShell remoting** — основной путь для Server Core [практика; WinRM — `../1c-windows/06-…`, раздел 4]: `Invoke-Command -ComputerName web1c.corp.local -ScriptBlock { Import-Module IISAdministration; Get-IISSite; Get-IISAppPool }`; `Install-WindowsFeature`/`Get-WindowsFeature` сами принимают `-ComputerName` и `-Credential` [MS Learn]. REST API Microsoft IIS Administration упомянут в «New Features Introduced in IIS 10.0» [MS Learn]; ⚠ состояние проекта на 2026 год не проверялось.

## 10. Резервирование, история, перенос и общая конфигурация

### 10.1. Резервная копия конфигурации

```bat
cd /d %windir%\system32\inetsrv
appcmd add backup "before-1C-8.3.27.2074"     :: без имени — имя по дате и времени
appcmd list backup
appcmd restore backup "before-1C-8.3.27.2074"
```

```powershell
Import-Module WebAdministration
Backup-WebConfiguration -Name 'before-1C-8.3.27.2074'
Get-WebConfigurationBackup
Restore-WebConfiguration -Name 'before-1C-8.3.27.2074'
Remove-WebConfigurationBackup -Name 'before-1C-8.3.27.2074'
```

- Копия — папка в `%windir%\System32\inetsrv\backup`; содержит `applicationHost.config` и связанное серверное состояние, включая настройки FTP и средства администрирования IIS [MS Learn: Getting Started with AppCmd.exe; Backup-WebConfiguration]. Делать перед любым изменением сервера и установкой компонентов [MS Learn].
- **Восстановление останавливает сервер** и возвращает глобальную конфигурацию на момент копии [MS Learn] — все сайты на время недоступны.
- **В копию не входят** [практика: следствие состава]: `web.config` и прочие файлы в каталогах сайтов (для 1С — `web.config` и `default.vrd` публикаций), содержимое, права NTFS, сертификаты и их привязки в HTTP.sys, параметры реестра HTTP.sys и Schannel, машинные ключи шифрования.

Полный набор для хоста публикаций 1С [практика]:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$dst   = "D:\Backup\iis-$stamp"; New-Item -ItemType Directory -Path $dst -Force | Out-Null
& "$env:windir\system32\inetsrv\appcmd.exe" add backup "auto-$stamp"
Copy-Item "$env:windir\system32\inetsrv\config\*.config" $dst                     # копия файлов вне каталога backup
robocopy C:\inetpub\wwwroot "$dst\wwwroot" /E /XF *.log                           # каталоги публикаций (default.vrd, web.config)
icacls "C:\inetpub\wwwroot\*" /save "$dst\acl-wwwroot.txt" /T                     # списки доступа; уточнено 20.10.2026 по справке icacls (образец Microsoft): вернуть — icacls C:\inetpub\wwwroot\ /restore <файл>
netsh http show sslcert > "$dst\sslcert.txt"                                      # привязки сертификатов (справочно)
reg export HKLM\SYSTEM\CurrentControlSet\Services\HTTP\Parameters "$dst\http-params.reg" /y
```

### 10.2. История конфигурации

`<configHistory>` [MS Learn]: `enabled` (`true`), `path` (`%SystemDrive%\inetpub\history`), `maxHistories` (`10`), `period` (`00:02:00` — как часто проверять изменения). Работает служба **ApplicationHost Helper**: если она остановлена или отключена, история не ведётся. Восстановление — скопировать `applicationHost.config` из нужной подпапки истории в `%windir%\system32\inetsrv\config`; это главный способ вернуть сервер после испорченной ручной правки (все сайты 503) [MS Learn: `<configHistory>`; ApplicationHost Helper Service]. Копии истории видны и в `appcmd list backup` и восстанавливаются так же [MS Learn: Getting Started with AppCmd.exe]; формат имён уточнён 20.10.2026 по «Using Configuration History with IIS 7 and IIS 8»: папки вида `CFGHISTORY_0000000016`, восстановление — `appcmd restore backup CFGHISTORY_0000000016`; при `maxHistories` самая старая копия удаляется перед созданием новой.

```bat
:: хранить 50 копий (образец Microsoft)
appcmd set config -section:system.applicationHost/configHistory /maxHistories:"50" /commit:apphost
dir %SystemDrive%\inetpub\history
```

### 10.3. Перенос на другой сервер

Порядок [практика, если не указано иное]:

1. **Хост:** та же или более новая ОС, тот же набор компонентов (`Get-WindowsFeature Web-* | Where Installed` → `Install-WindowsFeature`); для 1С — **та же сборка платформы с модулями веб-сервера по тому же пути** (путь к `wsisapi.dll` записан в `isapiCgiRestriction` и `web.config` публикаций) [ИТС-адм разд. 8.3.1; `../1c-windows/03-…`].
2. **Конфигурация** — один из вариантов:
   - `Export-IISConfiguration -PhysicalPath <папка> -KeyEncryptionPassword <SecureString>` выгружает конфигурацию и машинные ключи (ключи шифруются паролем; `-DontExportKeys` — без них; доступ к выгрузке — только администраторам) [MS Learn]. На новом сервере её можно подключить `Enable-IISSharedConfig` и затем отключить с копированием в локальные файлы `Disable-IISSharedConfig -CopyRemoteConfigToLocalFiles` [MS Learn — параметры; как способ переноса ⚠ не описан];
   - скопировать `applicationHost.config` и `administration.config` и перенести ключи: `aspnet_regiis -px "iisConfigurationKey" "D:\iisConfigurationKey.xml" -pri` на старом, `aspnet_regiis -pi "iisConfigurationKey" "D:\iisConfigurationKey.xml"` на новом, то же для `iisWasKey` [MS Learn: Shared Configuration, приложение 3]. Microsoft запускает `aspnet_regiis` из `Framework\v2.0.50727`; на современных Windows — из каталога .NET 4 ⚠. Файл с закрытым ключом после импорта удалить;
   - перенести без ключей и заново задать пароли пулов `SpecificUser` и каталогов через `appcmd`/Диспетчер IIS.
3. **Содержимое и права:** каталоги (`robocopy`), списки доступа (`icacls /restore` или заново по разделу 8.3). У `IIS_IUSRS` и `IUSR` SID одинаков на всех машинах — права переносятся `xcopy /o` [MS Learn]; права `IIS AppPool\<пул>` надёжнее выдать заново ⚠.
4. **Сертификаты и HTTPS-привязки** — экспорт/импорт PFX и привязка заново (`02-…`).
5. **Проверка:** `Get-IISSite`, `Get-IISAppPool`, `appcmd list apps`, запрос к каждому сайту; для 1С — вход в публикацию и вызов сервисов.

Web Deploy (`msdeploy`) тоже синхронизирует серверы [MS Learn: раздел Web Deploy] ⚠ — здесь не разбирался.

### 10.4. Общая конфигурация (Shared Configuration)

Однородная ферма читает один `applicationHost.config` с общей папки; изменение через любой узел видят все [MS Learn: Shared Configuration]. На папке — `applicationHost.config`, `administration.config` и выгруженные ключи; на узлах в `redirection.config` — `<configurationRedirection>`: `enabled` (`false`), `path`, `userName`, `password` (шифруется), `enableUncPolling` (IIS 7.5+, `false` — уведомления об изменениях, `true` — опрос) и `pollingPeriod` (`00:03:00`) [MS Learn: Configuration Redirection]. Учётной записи, читающей папку, нужно право «Вход в качестве пакетного задания» на веб-сервере и права на общую папку и NTFS; писать ей не нужно [MS Learn].

```powershell
Import-Module IISAdministration
$keyPwd = Read-Host -AsSecureString -Prompt 'Пароль защиты ключей'
Export-IISConfiguration -PhysicalPath '\\fs01\iisconfig$' -KeyEncryptionPassword $keyPwd `
    -UserName 'CORP\svc-iiscfg' -Password (Read-Host -AsSecureString -Prompt 'Пароль svc-iiscfg')   # на первом узле
Enable-IISSharedConfig -PhysicalPath '\\fs01\iisconfig$' -KeyEncryptionPassword $keyPwd `
    -UserName 'CORP\svc-iiscfg' -Password (Read-Host -AsSecureString -Prompt 'Пароль svc-iiscfg')   # на каждом узле
Get-IISSharedConfig          # Enabled = True, Physical Path = …
Disable-IISSharedConfig      # откат на локальную конфигурацию
```

Командлеты — [MS Learn]; `Enable-IISSharedConfig` перед включением сохраняет локальные ключи. В примерах Microsoft путь локальный (`C:\export`) ⚠ — UNC проверить на стенде. В Диспетчере IIS: «Общая конфигурация» → «Экспорт конфигурации» (один раз) → «Включить общую конфигурацию» на узлах; ключи, выгруженные вручную, интерфейс не примет [MS Learn].

**Порядок изменений** [MS Learn]: модуль или настройка, которые понимает только один узел, ломают остальные. Поэтому: выключить общую конфигурацию, привести локальный файл к общему, поставить и настроить модуль на одном узле, включить снова, разнести модуль на остальные узлы и включить на них.

**Ферма публикаций 1С** [практика]: общая конфигурация переносит только настройки IIS; на всех узлах — одна сборка платформы по одному пути, одинаковые каталоги публикаций с `default.vrd` и `web.config` (их она не синхронизирует), одинаковые права; SPN общего имени — `02-…`, `../1c-windows/03-…`, раздел 12.4.

## 11. Обновления IIS

- **IIS обновляется вместе с Windows** накопительными обновлениями; отдельного установщика нет, поддержка заканчивается вместе с ОС [MS Learn: Lifecycle — IIS]. План обновлений — `../1c-windows/06-…`, раздел 14.
- **Расширения вне ОС** (URL Rewrite, ARR, Web Deploy, IIS Manager for Remote Administration) ставятся и обновляются отдельными пакетами [практика ⚠]; ARR и URL Rewrite — `03-…`.
- **До и после обновления** [практика]: `appcmd add backup`; на ферме — вывести узел из балансировки; потом — службы, `Get-IISAppPool` (все Started), журнал «Система», ответы сайтов.
- **Обновление платформы 1С на хосте IIS** — новый пул, перепубликация, перенос приложений, удаление старого пула: `../1c-windows/03-…`, раздел 4.7; механика IIS — разделы 6.2, 7.8, 10.1.
- **Регулярно** [практика]: остановленные пулы (`appcmd list apppools /state:Stopped`), аварии за неделю, место под журналы, свежесть резервных копий и истории, лишние пулы и сайты, сроки сертификатов (`02-…`).

```powershell
# аварии рабочих процессов за 7 дней
Get-WinEvent -FilterHashtable @{ LogName = 'System'; Id = 5011; StartTime = (Get-Date).AddDays(-7) } -ErrorAction SilentlyContinue |
    Where-Object ProviderName -like '*WAS*' | Select-Object TimeCreated, Message
Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000; StartTime = (Get-Date).AddDays(-7) } -ErrorAction SilentlyContinue |
    Where-Object Message -like '*w3wp.exe*' | Select-Object TimeCreated, Message
```

Коды 5011 и 1000 — [MS Learn: Troubleshoot a process crash…]; точное имя поставщика событий WAS ⚠ не сверялось, поэтому фильтр по подстроке.

## 12. Где общие настройки IIS важны для публикации 1С

| Настройка IIS | Что важно для 1С | Подробно |
|---|---|---|
| Компоненты роли | «Расширения ISAPI» обязательны; .NET не нужен | [ИТС-адм разд. 8.2]; раздел 3 |
| `isapiCgiRestriction` | `wsisapi.dll` нужной сборки должен быть разрешён, иначе 404.2 | раздел 2.4; `../1c-windows/03-…`, разделы 4.5, 14.6 |
| Сайт | публикация всегда в Default Web Site; имя публикации — привязкой с именем узла | [ИТС-адм разд. 8.2]; раздел 5.5 |
| Приложение и пул | публикация — приложение; пул на сборку платформы; «Без управляемого кода»; разрядность пула = разрядность модуля | [ИТС-адм разд. 8.2, 8.10.2.1, 8.10.2.2]; разделы 6.3, 7.1 |
| Переработка | ночь по расписанию, иначе длинные вызовы обрываются через 90 с | раздел 7.5 |
| Веб-сад | файловая база — 1 процесс; клиент-серверная 8.3.26+ — ~1 на 100 сеансов | [ИТС-адм разд. 8.10.2.2; ИТС-мет 6034]; раздел 7.7 |
| Удостоверение и анонимный доступ | права на `bin`, файловую базу, `temp` — у того, от кого идёт запрос | [ИТС-адм разд. 8.3.1, 8.4.3.2.1]; раздел 8 |
| Блокировка разделов | аутентификация публикации хранится в `applicationHost.config` | раздел 4.4, 4.8 |
| Резерв и перенос | `default.vrd` и `web.config` публикаций в копию `appcmd` не входят | раздел 10 |
| Общая конфигурация | одна сборка платформы по одному пути на всех узлах | раздел 10.4 |
| Ошибки IIS вместо ошибок 1С | «Подробные сообщения об ошибках» | [ИТС-адм разд. 8.10.2.3]; `03-…` |

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| Все приложения пула — 503, пул «Остановлен» | защита от сбоев (5 аварий за 5 мин) или процесс не стартует: неверный пароль `SpecificUser`, модуль чужой разрядности, две версии модуля 1С в пуле | события WAS 5011 и Application Error 1000 [MS Learn]; устранить, `appcmd start apppool "<пул>"`; для 1С — пул на сборку и разрядность [ИТС-адм разд. 8.10.2.1, 8.10.2.2] |
| 503 под нагрузкой, пул работает | переполнена очередь пула (`queueLength` 1000) [MS Learn] | медленные вызовы (`appcmd list requests`), нагрузка кластера 1С; лимиты — `03-…` |
| Все сайты 503 после ручной правки `applicationHost.config` | ошибка XML или значения | файл из `%SystemDrive%\inetpub\history` или `appcmd restore backup` [MS Learn] |
| Правка `applicationHost.config` «не действует» | 32-разрядный редактор попал в `SysWOW64` (перенаправление WOW64, раздел 4.9) | 64-разрядный редактор, проверка `appcmd list config` [практика] |
| 500.19 / «раздел нельзя использовать по этому пути» | раздел заблокирован (`overrideModeDefault="Deny"`), а задан в `web.config` | `/commit:apphost` или разблокировать для пути (раздел 4.4) [MS Learn; ⚠ код и текст не сверялись] |
| Сайт не стартует: порт занят | дубль привязки у другого сайта или URL занят другим клиентом HTTP.sys | `Get-IISSiteBinding`, `netsh http show servicestate`, `Get-NetTCPConnection` (раздел 5.6) |
| Сайт не отвечает на новом IP | список `iplisten` не пуст, адреса в нём нет | `netsh http show iplisten`, добавить адрес или очистить [MS Learn] |
| По имени открывается «не тот» сайт | нет привязки с этим именем, сработала привязка без имени | привязка с именем узла, DNS [практика] |
| Первый запрос утром долгий | процесс завершён по простою или только что переработан | `idleTimeout="00:00:00"`, `AlwaysRunning`, переработка ночью (раздел 7.4) |
| Днём у 1С обрываются длинные операции | переработка по `time` (29 ч) пришлась на день; вызов дольше `shutdownTimeLimit` | `time="00:00:00"` + `schedule` ночью; события переработки в журнале «Система» [MS Learn; практика] |
| 401.2 | не включён ни один метод аутентификации | включить нужный [MS Learn]; `02-…` |
| Отказ в доступе к файлам | нет прав у удостоверения запроса (`IUSR`, пул при `userName=""`, пользователь при Windows-аутентификации) | права нужной учётной записи (раздел 8) |
| `icacls` не находит `IIS AppPool\<пул>` | пул не создан, опечатка, остановлена ApplicationHost Helper | создать пул, запустить службу [MS Learn] |
| После переноса `applicationHost.config` пулы со своей учётной записью не стартуют | пароли зашифрованы ключами старого сервера | перенести `iisConfigurationKey`/`iisWasKey` или задать пароли заново [MS Learn] |
| После установки модуля на одном узле фермы падают другие | общая конфигурация, модуля нет на всех узлах | порядок из раздела 10.4 [MS Learn] |
| `Get-IISAppPool`/`Get-IISSite` показывают старое | кэш `ServerManager` | `Reset-IISServerManager` [MS Learn] |
| Нет Диспетчера IIS на Server Core; удалённый не подключается | `Web-Mgmt-Console` в Core нет; WMSVC не запущена, `EnableRemoteManagement=0`, закрыт 8172 | раздел 9.4 [MS Learn] |
| `Install-WindowsFeature`: нет файлов | компонент удалён из `WinSxS` (`Removed`) | `-Source`, чтение для `ДОМЕН\ИМЯ$` [MS Learn] |
| Файловая база 1С: теряются фоновые задания | веб-сад или перекрывающаяся переработка | `maxProcesses=1` [ИТС-адм разд. 8.10.2.2]; `disallowOverlappingRotation="true"` (раздел 7.5; на 1С не проверялось) |
| Публикация 1С сломалась после перепубликации | приложение вернулось в `DefaultAppPool` | `appcmd list apps`, `appcmd set app … /applicationPool:…` (`../1c-windows/03-…`, раздел 7.3) |

## Быстрая шпаргалка — задача → команда

| Задача | Команда |
|---|---|
| Что установлено из IIS | `Get-WindowsFeature -Name Web-* \| Where-Object Installed` |
| Поставить IIS для 1С | `Install-WindowsFeature -Name Web-Server,Web-ISAPI-Ext,Web-ISAPI-Filter,Web-Http-Tracing,Web-Request-Monitor,Web-Scripting-Tools -IncludeManagementTools` |
| Версия ОС и IIS | `Get-CimInstance Win32_OperatingSystem`; `Get-ItemProperty HKLM:\SOFTWARE\Microsoft\InetStp` |
| Службы IIS | `Get-Service W3SVC, WAS, WMSVC` |
| Сайты, пулы | `Get-IISSite`; `Get-IISAppPool`; `appcmd list sites`; `appcmd list apppools` |
| Все свойства пула | `appcmd list apppool "<пул>" /text:*` |
| Приложения сайта и их пулы | `appcmd list apps /site.name:"Default Web Site"` |
| Создать пул | `appcmd add apppool /name:"<пул>"`; `New-WebAppPool -Name '<пул>'` |
| Пул без .NET | `appcmd set apppool "<пул>" /managedRuntimeVersion:""` |
| Перенести приложение в пул | `appcmd set app "Default Web Site/demo" /applicationPool:"<пул>"` |
| Переработка ночью | `appcmd set apppool "<пул>" /recycling.periodicRestart.time:00:00:00` + `appcmd set config -section:system.applicationHost/applicationPools /+"[name='<пул>'].recycling.periodicRestart.schedule.[value='03:00:00']" /commit:apphost` |
| Не гасить по простою, запускать сразу | `appcmd set apppool "<пул>" /processModel.idleTimeout:00:00:00 /startMode:AlwaysRunning` |
| Веб-сад | `appcmd set apppool "<пул>" /processModel.maxProcesses:4` |
| Переработать / остановить / запустить пул | `appcmd recycle apppool "<пул>"`; `Restart-WebAppPool`; `Stop-WebAppPool`; `Start-WebAppPool` |
| Рабочие процессы и текущие запросы | `appcmd list wps`; `appcmd list requests /apppool.name:"<пул>"` |
| Создать сайт | `appcmd add site /name:Portal /bindings:"http/*:80:portal.corp.local" /physicalPath:"D:\Sites\portal"`; `New-IISSite` |
| Привязки | `Get-IISSiteBinding -Name '<сайт>'`; `New-IISSiteBinding`; `appcmd set site /site.name:<сайт> /+bindings.[protocol='http',bindingInformation='*:8080:']` |
| Старт/стоп сайта | `appcmd stop site "<сайт>"`; `Start-IISSite -Name '<сайт>'` |
| Эффективная настройка раздела | `appcmd list config "<путь>" /section:<раздел> /config:*` |
| Где задана настройка | `appcmd search config "<сайт>/" /section:<раздел>` |
| Блокировка раздела | `appcmd lock config /section:<раздел>`; `appcmd unlock config /section:<раздел>` |
| Права пулу на каталог | `icacls "<каталог>" /grant "IIS AppPool\<пул>:(OI)(CI)RX"` |
| Анонимные запросы от удостоверения пула | `appcmd set config -section:anonymousAuthentication /username:"" --password` |
| Резервная копия / восстановление | `appcmd add backup "<имя>"`; `appcmd list backup`; `appcmd restore backup "<имя>"` |
| История конфигурации | `dir %SystemDrive%\inetpub\history` |
| Выгрузка конфигурации с ключами | `Export-IISConfiguration -PhysicalPath <папка> -KeyEncryptionPassword $pwd` |
| Общая конфигурация | `Enable-IISSharedConfig …`; `Get-IISSharedConfig`; `Disable-IISSharedConfig` |
| Состояние HTTP.sys | `netsh http show servicestate`; `netsh http show iplisten`; `netsh http show sslcert` |
| Удалённое управление | `Install-WindowsFeature Web-Mgmt-Service`; `EnableRemoteManagement=1`; `Set-Service WMSVC -StartupType Automatic`; `Start-Service WMSVC` |

## Источники

Документация Microsoft (прочитана 20.10.2026). IIS: исходник `https://raw.githubusercontent.com/MicrosoftDocs/iis-docs/main/iis/<путь>.md`, страница `https://learn.microsoft.com/iis/<путь>`:

- `get-started/introduction-to-iis/`: `introduction-to-iis-architecture`, `iis-modules-overview`.
- `get-started/planning-your-iis-architecture/`: `introduction-to-applicationhostconfig`, `deep-dive-into-iis-configuration-with-iis-7-and-iis-8`, `getting-started-with-configuration-in-iis-7-and-above`, `the-configuration-system-in-iis-7`, `understanding-sites-applications-and-virtual-directories-on-iis`; `get-started/planning-for-security/`: `how-to-use-locking-in-iis-configuration`, `understanding-built-in-user-and-group-accounts-in-iis`.
- `manage/managing-your-configuration-settings/`: `an-overview-of-feature-delegation-in-iis`, `understanding-iis-configuration-delegation`, `shared-configuration_264`; `manage/configuring-security/application-pool-identities`; `manage/remote-administration/`: `remote-administration-for-iis-manager`, `configuring-remote-administration-and-feature-delegation-in-iis-7`; `manage/powershell/powershell-snap-in-*` (создание сайтов, изменение настроек, данные времени выполнения).
- Справочник `configuration/`: `system.applicationHost/applicationPools/` (`index`, `add/index`, `add/processModel`, `add/recycling/…`, `add/failure`, `add/cpu`, `applicationPoolDefaults/index`), `system.applicationHost/sites/` (`index`, `site/index`, `site/bindings/index`, `site/bindings/binding`, `site/application/index`, `site/application/virtualDirectory`, `site/limits`, `siteDefaults/index`), `system.applicationHost/configHistory`, `…/webLimits`, `configurationRedirection`, `configPaths/index`, `system.webServer/handlers/index` и `add`, `…/modules/index`, `…/globalModules/index`, `…/security/isapiCgiRestriction/index`.
- Что нового: `get-started/whats-new-in-iis-10/` (`new-features-introduced-in-iis-10`, `iisadministration-powershell-cmdlets`, `wildcard-host-header-support`), `…-version-1709/new-features-introduced-in-iis-10-1709`, `…-version-1809/new-features-introduced-in-iis-10-1809`; `whats-new-in-iis-8/` (`iis-80-application-initialization`, `iis-80-server-name-indication-sni-ssl-scalability`, `iis-80-multicore-scaling-on-numa-hardware`); `whats-new-in-iis-85/` (`idle-worker-process-page-out-in-iis85`, `dynamic-site-activation-in-iis85`); `whats-new-in-iis-7/changes-in-security-between-iis-60-and-iis-7-and-above`.
- Прочее: `get-started/getting-started-with-iis/getting-started-with-appcmdexe`; `web-hosting/web-server-for-shared-hosting/` (`application-pool-identity-as-anonymous-user`, `create-a-backup-with-appcmd`); `install/installing-iis-7/` (`applicationhost-helper-service`, `install-and-configure-iis-on-server-core`); `install/installing-iis-85/installing-iis-85-on-windows-server-2012-r2` (таблица компонентов); `develop/runtime-extensibility/an-end-to-end-extensibility-example-for-iis-developers` (`appcmd recycle AppPool`).
- PowerShell: `https://learn.microsoft.com/powershell/module/iisadministration/`, `…/webadministration/` (исходники `MicrosoftDocs/windows-powershell-docs`, `docset/winserver2025-ps/`), `…/servermanager/` (`install-windowsfeature`, `get-windowsfeature`, `uninstall-windowsfeature`); API `https://learn.microsoft.com/dotnet/api/microsoft.web.administration.*` (`ApplicationPool`, `ApplicationPoolProcessModel`, `ApplicationPoolRecycling`, `ApplicationPoolPeriodicRestart`, `ScheduleCollection`, `ApplicationPoolCollection`).
- Windows: `https://learn.microsoft.com/windows-server/administration/server-core/server-core-roles-and-services` (12.03.2025); `…/windows-server/administration/windows-commands/netsh-http` (прежний адрес `…/networking/technologies/netsh/netsh-http` перенаправляет сюда); `https://learn.microsoft.com/lifecycle/products/internet-information-services-iis`; `https://learn.microsoft.com/troubleshoot/developer/webapps/iis/site-behavior-performance/process-termination-crash`.

1С (полные тексты, прочитаны 20.10.2026): «Руководство администратора» 8.3.27, гл. 8 — разд. 8.1, 8.2, 8.3.1, 8.4.3.2.1, 8.10.2.1–8.10.2.6 (`https://its.1c.ru/db/v8327doc/content/107/hdoc`; конспекты `../its-docs/adm-gl08-veb-servery-p1.md`, `-p2.md`); ИТС-мет 6034 (23.07.2025) «Особенности веб публикации на IIS платформы 1С:Предприятие 8.3.26 и выше»; ИТС-мет 5977 (31.07.2020) «Настройка веб-сервера IIS»; ИТС-мет 5944 (15.05.2018).

Сторонние: блог автора `appcmd` (`mvolo.com`) — только как ссылка из документации Microsoft о конвейерной обработке `appcmd /xml` [сторонний].

Независимая сверка 20.10.2026 (рецензент) — дополнительно прочитаны: исходники `MicrosoftDocs/iis-docs` всех страниц и образцов (`samples/*.cmd`, `*.xml`), перечисленных выше, в том числе `manage/managing-your-configuration-settings/using-configuration-history-with-iis-7-and-iis-8` (имена `CFGHISTORY_…`) и образцы справочника `system.applicationHost/sites/site/ftpServer/*` (имя сайта с точкой); справка PowerShell из `MicrosoftDocs/windows-powershell-docs` (`docset/winserver2025-ps/IISAdministration/*` — 34 командлета, `WebAdministration/*`, `ServerManager/Install-` и `Uninstall-WindowsFeature`, `Dism/Enable-WindowsOptionalFeature`); `MicrosoftDocs/SupportArticles-docs`: `support/developer/webapps/iis/www-administration-management/configure-w3svc-wsfc` (`net stop apphostsvc`), `…/site-behavior-performance/process-termination-crash`, `…/www-administration-management/use-registry-keys` (о `InetStp\MajorVersion` в ней ничего нет); архивная справка `https://learn.microsoft.com/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc732742(v=ws.10)` («Start or Stop an Application Pool (IIS 7)»); `https://learn.microsoft.com/windows/win32/winprog64/file-system-redirector`; `https://learn.microsoft.com/dotnet/api/microsoft.web.administration.schedulecollection.add`. По 1С — полный текст гл. 8 «Руководства администратора» 8.3.27 (разд. 8.1, 8.2, 8.3.1, 8.4.3.2.1, 8.10.2.1–8.10.2.6) и методички ИТС 6034, 5977, 5944.

## Что не удалось подтвердить

- Состав компонентов, устанавливаемых по умолчанию с ролью `Web-Server` в IIS 10.0 (таблица со звёздочками — от IIS 8.5).
- Какой модуль PowerShell (`WebAdministration`, `IISAdministration`) ставит компонент `Web-Scripting-Tools`; поведение модулей в PowerShell 7.
- Версия модуля `IISAdministration` в составе Windows Server 2019/2022/2025 (что командлеты `*-IISSiteBinding` есть с выпуска 1709, уточнено 20.10.2026 — раздел 1.1).
- На каком выпуске Windows работают флаги привязки 16/32/64 (QUIC, TLS 1.3 поверх TCP, Legacy TLS); новинки IIS в Windows Server 2025.
- Значения `loadUserProfile` и `managedRuntimeVersion` в `<applicationPoolDefaults>` готового `applicationHost.config` IIS 10.0 (схема: `false` и `""`; `DefaultAppPool` по справке — v4.0).
- Имя поставщика событий WAS (`Microsoft-Windows-WAS`; статья Microsoft называет только источник «Windows Process Activation Service (WAS)»); коды событий переработки пула. (Короткое имя службы `AppHostSvc` уточнено 20.10.2026.)
- Сохраняется ли `applicationHost.config` при удалении и повторной установке роли.
- Где `webinst -osauth` записывает настройки аутентификации публикации (по логике блокировки — `<location>` в `applicationHost.config`); поведение Диспетчера IIS для заблокированных разделов.
- Загружает ли `preloadEnabled`/Application Initialization модуль `wsisapi.dll` и соединения с кластером до первого пользовательского запроса.
- `disallowOverlappingRotation="true"` для публикаций файловых баз — на стенде (общая рекомендация Microsoft уточнена 20.10.2026, раздел 7.5); режим конвейера пула 1С (рекомендация `Integrated` — практика).
- Допустима ли точка в имени сайта (описание валидатора `SiteName` и образцы справочника расходятся, раздел 4.3).
- Способ выполнения рекомендации ИТС 6034 (веб-сад или несколько пулов) и равномерность распределения запросов между процессами веб-сада.
- Формы `appcmd delete app`, удаление привязки `/-bindings.[…]`, добавление в `schedule` из `WebAdministration` — собраны по общим правилам, в образцах Microsoft не встречались (`appcmd start/stop apppool` и анонимное удостоверение для одного сайта уточнены 20.10.2026).
- Работа `Export-IISConfiguration`/`Enable-IISSharedConfig` с UNC-путём; перенос через `Disable-IISSharedConfig -CopyRemoteConfigToLocalFiles`; путь к `aspnet_regiis` на современных Windows; переносимость прав `IIS AppPool\…` между машинами.
- Ограничения IIS на Windows 10/11; актуальность «IIS Manager for Remote Administration» и проекта Microsoft IIS Administration (REST API); Web Deploy.
- Ключ реестра `InetStp` для определения версии IIS (в документации Microsoft не описан).
- Установка платформы 1С и модуля веб-сервера на Server Core.
