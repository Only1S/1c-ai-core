# Администрирование SQL Server для 1С: инструменты, учётные записи и права, SQL Server Agent и Database Mail, журнал ошибок и DAC, файлы баз, безопасность

> **Официальные тексты по теме** (полные тексты ИТС 8.3.27, адрес главы — `https://its.1c.ru/db/v8327doc/content/NNN/hdoc`): «Клиент-серверный вариант» — гл. 1 (123: 1.5.4), гл. 2 (124: 2.3), гл. 3 (125: 3.2.3), гл. 5 (127: 5.2.7.3, 5.2.12.3, 5.5), прил. 3 (133: 3.4–3.11); «Руководство администратора» — гл. 5 (104: 5.2.1.3.2, 5.2.1.3.6–5.2.1.3.8), гл. 7 (106: 7.2, 7.4), прил. 3 (115: 3.7), прил. 4 (116: 4.9, 4.10), прил. 7 (119: 7.7.4); «Руководство разработчика» — прил. 8 (92: 8.4). Конспекты: `../its-docs/cs-gl03-ustanovka-komponentov-p2.md`, `../its-docs/cs-gl05-administrirovanie-klastera-p2.md`, `…-p3.md`, `../its-docs/cs-gl06-gl07-pr01-pr03-obnovlenie-licenzii-cron-bezopasnost.md`, `../its-docs/adm-gl05-spisok-infobaz.md`, `../its-docs/adm-gl07-avtonomnyj-server.md`, `../its-docs/adm-pr04-komandnye-stroki-utilit-p3.md`, `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`. Методические статьи ИТС: 1595 (2007), 2373 (2008), 2378 (2008), 2926 (2008), 5837 (2022), 5899 (2016), 5904 (2019), 6008 (2023).

> Статус: проверено независимой сверкой 20.10.2026: с полными текстами ИТС 8.3.27 («Клиент-серверный вариант» гл. 1–3, 5, прил. 3; «Руководство администратора» гл. 5, 7, прил. 3, 4, 7; «Руководство разработчика» прил. 8), методичками ИТС 1595, 2373, 2926, 5837, 5899, 5904, 6008, исходниками документации Microsoft (sql-docs, ветка `live`), страницами SSMS, PowerShell `SqlServer` и Lifecycle на learn.microsoft.com, статьями поддержки Microsoft, исходниками dbatools 2.9.1 и выпусками GitHub; синтаксис всех примеров T‑SQL сверен со справочником. Исправлено 9 ошибок, закрыто 3 пометки; на сервере не проверялось — команды T‑SQL, PowerShell, `sqlcmd` и `cmd` не запускались.

> Область: повседневное администрирование экземпляра Microsoft SQL Server, на котором лежат базы «1С:Предприятия 8» (рабочие серверы 1С — только Windows), — инструменты (SSMS, `sqlcmd`, SQL Server Configuration Manager, модуль PowerShell `SqlServer`, dbatools), логины и пользователи для 1С и их права, «осиротевшие» пользователи и владелец базы после переноса, контейнерные базы, создание и удаление ИБ на MS SQL, SQL Server Agent и Database Mail, журнал ошибок, выделенное административное подключение (DAC), файлы баз (рост, сжатие, перенос, владелец), безопасность (TLS, TDE, аудит, минимальные права, `sa`) | Версии: SQL Server 2016–2025 (поддержка 2016 закончилась 14.07.2026; 2025 — GA 18.11.2025, основная поддержка до 06.01.2031); платформа 8.3.27 (и отличия 8.5.1); SSMS 22.11; модуль `SqlServer` 22.4.5.1; dbatools 2.9.1 | Актуальность: 2026-10-20

**Как читать статью**

- **[ИТС-КС разд. N]** — «1С:Предприятие 8.3. Клиент-серверный вариант. Руководство администратора» 8.3.27; **[ИТС-адм разд. N]** — «Руководство администратора» 8.3.27 (приложения — «прил. N, разд. N»); **[ИТС-разр прил. N]** — «Руководство разработчика» 8.3.27.
- **[ИТС-мет NNNN, ГГГГ]** — методическая статья `https://its.1c.ru/db/metod8dev/content/NNNN/hdoc` с датой. Статьи 2007–2010 годов писались для SQL Server 2000/2005 — у каждой указано, что устарело.
- **[MS Learn]** — документация Microsoft (learn.microsoft.com; исходники `github.com/MicrosoftDocs/sql-docs`, ветка `live`, и страницы `learn.microsoft.com/ssms/…`, `…/powershell/…`, прочитаны 20.10.2026).
- **[сторонний]** — сторонний инструмент по его официальному репозиторию (dbatools, First Responder Kit, sp_WhoIsActive, Ola Hallengren). **[практика]** — устоявшаяся практика администраторов, в первоисточниках в таком виде не описана. **⚠** — не удалось подтвердить первоисточником; перед применением проверить на стенде.
- **Ваш контекст.** Сервер 1С у вас — Ubuntu, СУБД — «PostgreSQL для 1С». **Рабочие процессы 1С на Linux с MS SQL Server не работают** [ИТС-КС разд. 2.3], поэтому статья — справочник для Windows-серверов организации и для переноса баз с MS SQL. Сам SQL Server при этом может стоять и на Linux (раздел 2.8). Базы сервисов (Redmine, NetBox, GlitchTip и т. п.) в экземпляр СУБД баз 1С не кладутся — у них свой PostgreSQL.
- **Смежные статьи раздела** (их тему здесь не расписываю): `mssql/01-versii-redakcii-arhitektura.md` — версии, редакции, архитектура; `mssql/02-ustanovka-i-nastrojka-ekzemplyara.md` — установка, параметры экземпляра (память, MAXDOP, tempdb, флаги, протоколы); `mssql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` — копии и восстановление; `mssql/05-obsluzhivanie-indeksy-statistika.md` — регламент, индексы, статистика, `DBCC CHECKDB`; `mssql/06-monitoring-i-diagnostika.md` — DMV, ожидания, блокировки, Query Store; `mssql/07-otkazoustojchivost-i-obnovlenie-versij.md` — Always On, обновление версий; `mssql/08-tipovye-problemy-i-zaprosy-1c.md` — типовые проблемы и запросы 1С. Обзорная статья — `../1c-windows/02-ms-sql-server-dlya-1c.md`; `rac` — `../1c/03-administrirovanie-klastera-ras-rac.md`; `ibcmd` и пакетный режим — `../1c/06-infobazy-ibcmd-paketnyj-rezhim.md`; техжурнал — `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.
- **Условные имена:** экземпляр `sql01` (экземпляр по умолчанию, служба `MSSQLSERVER`; полное имя `sql01.corp.local`), именованный — `sql01\ERP`; база `buh`; логин SQL Server для ИБ `buh_1c`; кластер 1С `srv1c`, рабочие серверы 1С `app1c01`/`app1c02` (10.10.0.21, 10.10.0.22); группа администраторов СУБД в AD `CORP\SQL-Admins`; диски `D:` — данные, `L:` — журналы, `E:` — копии.

## Кратко — главные факты и команды

1. **MS SQL — только при рабочих серверах 1С на Windows x86‑64** [ИТС-КС разд. 1.5.4, 2.3]; автономный сервер `ibsrv` на Linux с MS SQL тоже не работает [ИТС-адм разд. 7.2]. Платформа 8.3.27 и 8.5.1 поддерживает SQL Server до **2022** включительно; **2025 в перечне нет** (перечень сверен 20.10.2026: [ИТС-КС разд. 1.5.4] — 2000 SP1 … 2022; `otlichiya-8.5.1` — без изменений); работа с 2025 не подтверждена ⚠.
2. **SSMS 22** ставится через Visual Studio Installer (`vs_SSMS.exe`), работает с SQL Server **2014+**, текущая — 22.11.0 от 13.10.2026; в окне подключения **шифрование по умолчанию «Mandatory»** (с SSMS 20) и сертификат проверяется [MS Learn]. Без доверенного сертификата на сервере — отметить «Trust server certificate» или поставить сертификат (раздел 12.1).
3. **`sqlcmd` бывает двух видов**: ODBC (в составе SQL Server / Command Line Utilities, на Linux — `mssql-tools18`) и Go (`winget install sqlcmd`). У ODBC-`sqlcmd` из SQL Server 2025 **по умолчанию `-Nm` (mandatory)**, у 2022 и раньше — `-No`; `-C` — доверять сертификату; `-A` — DAC (только Windows); `-b` — код возврата при ошибке [MS Learn].
4. **SQL Server Configuration Manager** — `C:\Windows\SysWOW64\SQLServerManager16.msc` (2022), `…17.msc` (2025); **учётную запись служб менять только здесь**, не в «Службах» [MS Learn]. Там же протоколы, Force Encryption, сертификат, параметры запуска (`-T`, `-m`, `-f`, `-e`).
5. **PowerShell**: `Install-Module SqlServer` (SQLPS устарел); у `Invoke-Sqlcmd` с версии 22 модуля `-Encrypt` по умолчанию `Mandatory`, есть `-TrustServerCertificate` [MS Learn]. **dbatools 2.9.1** [сторонний] — тоже «безопасные умолчания»; откат — `Set-DbatoolsInsecureConnection`.
6. **Права логина 1С по ИТС**: член `processadmin` или `sysadmin`; пользователь базы — `sa` либо **владелец базы**; при готовой базе — чтение `master` и полный доступ к `tempdb` [ИТС-адм разд. 5.2.1.3.2; ИТС-КС разд. 3.2.3]. `processadmin` нужен, чтобы «Удалить» соединение с долгим запросом в консоли кластера [ИТС-мет 1595, 2007; ИТС-КС разд. 5.2.12.3].
7. **Свой логин на каждую ИБ**, имя логина = имя ИБ [ИТС-КС прил. 3, разд. 3.7; ИТС-мет 5899, 2016]. `sysadmin` логину 1С не давать; `dbcreator` — только на время создания базы, потом снять [ИТС-мет 2926, 2008; практика].
8. **Что даёт роль на самом деле** [MS Learn]: `processadmin` → `ALTER ANY CONNECTION` (это право на `KILL` **любого** сеанса экземпляра); `dbcreator` → создать, изменить, удалить и **восстановить любую** базу. На общем экземпляре это права на чужие базы.
9. **`CREATE LOGIN`**: `CHECK_POLICY` по умолчанию `ON`, `CHECK_EXPIRATION` — `OFF` [MS Learn]. Для логина 1С — `CHECK_EXPIRATION = OFF` явно: истёкший пароль остановит все сеансы ИБ. При `CHECK_POLICY = ON` действует блокировка по неверным паролям Windows; снять — `ALTER LOGIN … WITH PASSWORD = '…' UNLOCK` [MS Learn].
10. **После восстановления базы на другом сервере владельцем становится тот, кто восстанавливал** [MS Learn]. Если логин 1С был владельцем (`dbo`, обычный случай), лечится **`ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];`**, а не `ALTER USER … WITH LOGIN` (раздел 4).
11. **«Осиротевший» пользователь** (обычный пользователь базы с SID несуществующего логина): поиск — `sys.database_principals LEFT JOIN sys.server_principals ON sid … WHERE sp.sid IS NULL AND dp.authentication_type_desc = 'INSTANCE'`; исправление — `ALTER USER [u] WITH LOGIN = [l];`; `sp_change_users_login` устарела [MS Learn]. Логины с тем же SID и паролем переносит `sp_help_revlogin` [MS Learn] или `Copy-DbaLogin` [сторонний].
12. **Контейнерные базы для 1С неприменимы**: логину 1С нужна серверная роль (`processadmin`), а пользователь контейнерной базы — принципал уровня базы; опция `contained database authentication` по умолчанию `0` — так и оставить [MS Learn; вывод — практика] ⚠.
13. **SQL Server Agent** есть в Enterprise и Standard, **нет в Express** (2022, 2025) [MS Learn]; по умолчанию служба отключена, если при установке не выбран автозапуск. Задание: `sp_add_job` → `sp_add_jobstep` → `sp_add_schedule` → `sp_attach_schedule` → `sp_add_jobserver` (всё в `msdb`); шаги T‑SQL выполняются **от имени владельца задания** [MS Learn].
14. **Оповещения**: `sp_add_operator`, `sp_add_alert` (по номеру ошибки или серьёзности), `sp_add_notification`; срабатывают только события, попавшие в журнал приложений Windows (серьёзность 19+ или `WITH LOG`) [MS Learn]. Минимум для сервера 1С: 823, 824, 825 и серьёзность 19–25 [практика].
15. **Database Mail**: `sp_configure 'Database Mail XPs', 1` → `msdb.dbo.sysmail_add_account_sp` → `sysmail_add_profile_sp` → `sysmail_add_profileaccount_sp` → тест `sp_send_dbmail`; агенту указать профиль в свойствах Agent → Alert System и перезапустить агент [MS Learn]. Журнал — `msdb.dbo.sysmail_event_log`.
16. **Журнал ошибок**: `ERRORLOG` (путь — параметр запуска `-e`), архивов по умолчанию 6, можно 6–99 (`Set-SqlErrorLog -MaxLogCount`); чтение — `EXEC sp_readerrorlog 0, 1, N'Login failed';`, ротация — `EXEC sp_cycle_errorlog;` (только `sysadmin`) [MS Learn]. Причину ошибки 18456 показывает `State` в журнале (8 — неверный пароль, 38 — нет базы, 58 — SQL-вход при режиме «только Windows») [MS Learn].
17. **DAC**: `EXEC sp_configure 'remote admin connections', 1; RECONFIGURE;` — сразу после установки; вход `admin:sql01` в SSMS («Новый запрос», IntelliSense выключить) или `sqlcmd -S sql01 -E -A -d master`; одно подключение на экземпляр (иначе 17810), только `sysadmin`, без `BACKUP`/`RESTORE` и параллелизма; Express — только с флагом 7806 [MS Learn].
18. **Рост файлов** — фиксированным шагом в МБ (1С — 512 МБ [ИТС-мет 5904, 2019]); IFI ускоряет рост данных, с 2022 — и рост журнала до 64 МБ; при TDE IFI для файлов данных не работает [MS Learn].
19. **SHRINK — не регламентная операция**: дробит индексы, файл тут же растёт снова, блокируется транзакциями с версионностью строк (а это RCSI 1С); `AUTO_SHRINK` не включать [MS Learn]. Если очень нужно — `DBCC SHRINKFILE` до целевого размера, с 2022 — `WITH WAIT_AT_LOW_PRIORITY`, затем обслуживание индексов (→ `mssql/05`). Совет 2008 года `BACKUP LOG … WITH TRUNCATE_ONLY` [ИТС-мет 2373] — опция удалена [MS Learn].
20. **Перенос базы на другой сервер** — `BACKUP … WITH COPY_ONLY, CHECKSUM` + `RESTORE … WITH MOVE`, а не detach/attach: исходная база остаётся в работе, есть контрольная сумма; на старшую версию переносится, на младшую — никак [MS Learn; практика]. Внутри экземпляра файлы переносят `ALTER DATABASE … MODIFY FILE` + `OFFLINE`/`ONLINE` [MS Learn]; 1С это допускает [ИТС-КС разд. 5.5.6, 5.5.7].
21. **TLS**: сертификат с EKU Server Authentication и `KeySpec = AT_KEYEXCHANGE`, право чтения закрытого ключа у учётной записи службы, Force Encryption = Yes, перезапуск; проверка — `encrypt_option` в `sys.dm_exec_connections` [MS Learn]. **Force Strict Encryption (TDS 8.0, с 2022) для 1С не включать**, пока не подтверждена поддержка платформой ⚠.
22. **TDE** допустимо для баз 1С [ИТС-КС разд. 5.5.2 — «шифрование на уровне СУБД», MS SQL 2008+]; редакции — Enterprise, **Standard с 2019**, не Express [MS Learn]. Шифруется и `tempdb` всего экземпляра; **без резервной копии сертификата базу не восстановить** [MS Learn].
23. **Аудит**: `CREATE SERVER AUDIT … TO FILE` + `CREATE SERVER AUDIT SPECIFICATION … ADD (FAILED_LOGIN_GROUP) …`; доступен во всех редакциях 2022/2025; читать `sys.fn_get_audit_file` [MS Learn]. Аудит изменений данных в таблицах 1С не включать [практика].
24. **`sa`**: в смешанном режиме — отключить (`ALTER LOGIN sa DISABLE;`) или переименовать (`ALTER LOGIN sa WITH NAME = …`), администраторы — через доменную группу [MS Learn; практика]. Перед этим убедиться, что ни одна ИБ не зарегистрирована под `sa`.
25. **Потерян доступ `sysadmin`**: остановить Agent, запустить экземпляр `net start MSSQLSERVER /f /mSQLCMD`, войти локальным администратором `sqlcmd -E` и выдать роль [MS Learn].

## 1. Место SQL Server в смешанной среде и кто к нему подключается

| Ситуация | Работает ли | Источник |
|---|---|---|
| Рабочие серверы 1С на Windows x86‑64 → SQL Server на Windows или Linux | да | [ИТС-КС разд. 1.5.4]; Linux-сервер СУБД — `../1c-windows/02`, п. 1.1 |
| Рабочие серверы 1С на Linux (как у вас), ARM64, E2K | **нет** | [ИТС-КС разд. 1.5.4, 2.3] |
| `ibsrv`/`ibcmd` на Linux с MS SQL | нет | [ИТС-адм разд. 7.2] |
| MS SQL как внешний источник данных для сервера 1С на Linux | да, это не база ИБ | `../1c/09-klient-linux-i-otlichiya-ot-windows.md` |

- С СУБД работают только процессы кластера 1С (`rphost`), клиенты к SQL Server не подключаются [ИТС-КС разд. 2.1]. Поэтому порт 1433 открывают только рабочим серверам 1С и машинам администраторов [ИТС-КС прил. 3, разд. 3.5 — доступ пользователей ОС к компьютеру СУБД не давать].
- В консоли кластера у сеанса видно «Соединение с СУБД» — идентификатор процесса сервера БД (на MS SQL это `session_id`) и «Заблокировано СУБД» [ИТС-КС разд. 5.2.12]: это мост от сеанса 1С к DMV (`mssql/06`).
- Отдельный экземпляр SQL Server под базы 1С и отдельный — под прочие приложения [практика]: у логина 1С роль `processadmin` действует на весь экземпляр (раздел 3.2).

## 2. Инструменты администратора

### 2.1. Что чем делается

| Инструмент | Для чего | Где ставить | Источник |
|---|---|---|---|
| SSMS 22 | обозреватель объектов, редактор запросов, мастера копий, Agent, Database Mail, журнал ошибок, аудит, DAC | машина администратора (Windows 10+ x64/Arm64) | [MS Learn] |
| `sqlcmd` (ODBC) | сценарии, задания по расписанию, DAC (`-A`), аварийный вход в однопользовательском режиме | сервер SQL (ставится с SQL Server), машина администратора, Linux (`mssql-tools18`) | [MS Learn] |
| `sqlcmd` (Go) | то же, кроссплатформенно; `sqlcmd query`, `--vertical` | любая машина (`winget install sqlcmd`) | [MS Learn] |
| SQL Server Configuration Manager | службы и их учётные записи, сетевые протоколы, порт, сертификат TLS, Force Encryption, параметры запуска | ставится вместе с SQL Server (только Windows) | [MS Learn] |
| Модуль PowerShell `SqlServer` | `Invoke-Sqlcmd`, `Get-SqlErrorLog`, `Set-SqlErrorLog`, `Backup-SqlDatabase`, `Get-SqlAgentJobHistory` и др. | машина администратора, сервер | [MS Learn] |
| dbatools | массовые операции: перенос логинов, поиск сирот, владельцы, проверка копий, файлы | машина администратора | [сторонний] |
| `mssql-conf` | настройка SQL Server на Linux (вместо Configuration Manager) | сервер Linux | [MS Learn] |

### 2.2. SQL Server Management Studio

- **Версии** [MS Learn]: SSMS 22 — общедоступная с 11.11.2025 (22.0.0), текущая 22.11.0 от 13.10.2026; основана на Visual Studio 2026, 64-разрядная, есть сборка для Arm64; полностью совместима с SQL Server 2025; **работает с SQL Server 2014 и новее** — для 2012 и старше нужна старая версия из «Release history». Поддерживается только последний выпуск канала. SSMS бесплатна.
- **Установка** [MS Learn]: загрузчик `vs_SSMS.exe` открывает Visual Studio Installer (отдельного MSI нет); нужны права локального администратора; обновление — через Visual Studio Installer; для машин без интернета — офлайн-раскладка. SSMS 22 ставится рядом с другими версиями. SSMS **не** устанавливает модули PowerShell — `SqlServer` ставится отдельно (2.5).
- **Окно подключения** [MS Learn]: «Encryption» по умолчанию **Mandatory** (так с SSMS 20), «Trust Server Certificate» по умолчанию снят — к серверу без доверенного сертификата подключение не пройдёт. Варианты: поставить на SQL Server сертификат доменного УЦ (раздел 12.1) или отметить «Trust Server Certificate» (только во внутренней сети). Strict (в SSMS 21 — «Strict (Minimum SQL Server 2022 and Azure SQL)») — для экземпляров с Force Strict Encryption.
- **Где ставить**: на машину администратора, не на сервер СУБД [практика] — меньше памяти отнимается у экземпляра и меньше лишнего ПО на сервере.
- **Полезное для 1С**: «Management → SQL Server Logs» — журнал ошибок (раздел 9); «Security → Logins» — логины и «User Mapping»; свойства базы → «Files» — размеры и рост (раздел 11); «SQL Server Agent» (раздел 7); «Database Mail» (раздел 8); «Security → Audits» (раздел 12.4). Режим SQLCMD в редакторе — «Query → SQLCMD Mode»; SSMS выполняет его через `SqlClient`, а `sqlcmd` из командной строки — через ODBC, поэтому умолчания (например, шифрования) могут различаться [MS Learn].
- **DAC из SSMS** — только через «File → New → Database Engine Query» с именем `admin:sql01`, IntelliSense выключить (раздел 10) [MS Learn].
- **Сценарий логинов** при переносе: мастер «Generate Scripts» с параметром «Script Logins = True» пароли SQL-логинов **не** переносит — создаёт их отключёнными со случайным паролем [MS Learn — статья поддержки о переносе логинов] — для них раздел 4.5.

### 2.3. sqlcmd

**Два варианта** [MS Learn]: `sqlcmd` (ODBC) — ставится с SQL Server или пакетом Microsoft Command Line Utilities, на Linux — пакет `mssql-tools18` (каталог `/opt/mssql-tools18/bin`); `sqlcmd` (Go, go-sqlcmd) — отдельная утилита (`winget install sqlcmd`, `choco install sqlcmd`, архив с GitHub `microsoft/go-sqlcmd`, последняя версия — 1.10.0 от 03.03.2026 [сторонний — релизы GitHub]). Какой стоит — `sqlcmd -?` (ODBC) или `sqlcmd --version` (Go).

Ключи, которые нужны администратору 1С [MS Learn, sqlcmd-utility]:

| Ключ | Смысл | Замечание |
|---|---|---|
| `-S [tcp:\|lpc:\|np:]сервер[\экземпляр][,порт]` | экземпляр | префикс протокола: `tcp`, `lpc` (shared memory), `np`; на Linux только `tcp` |
| `-E` | доверенное подключение (Windows) | по умолчанию, если нет `-U`/`-P`; с `-U` несовместим |
| `-U логин` / `-P пароль` | вход SQL Server | пароль лучше из переменной `SQLCMDPASSWORD`, не в командной строке [практика] |
| `-d база` | начальная база | для пользователя контейнерной базы обязателен |
| `-A` | DAC | **только Windows**; можно и `-S admin:сервер` |
| `-N[s\|m\|o]` | шифрование: strict / mandatory / optional | у `sqlcmd` (ODBC) из **SQL Server 2025 умолчание `-Nm`**, у 2022 и раньше — `-No`; у Go-версии `-N` принимает `true/false/disable/strict` |
| `-C` | доверять сертификату сервера без проверки | аналог `TrustServerCertificate=true` |
| `-F имя` | ожидаемое имя в сертификате (CN/SAN) | при подключении по DNS-псевдониму |
| `-i файл` / `-o файл` | входной сценарий / файл вывода | несколько входных — через запятую |
| `-Q "запрос"` | выполнить и выйти | `-q` — выполнить и остаться |
| `-v имя=значение` | переменные сценария `$(имя)` | на Linux/macOS `-v` не поддерживается |
| `-b` | при ошибке серьёзности > 10 выйти с `ERRORLEVEL` = 1 | обязателен в заданиях по расписанию |
| `-l сек` / `-t сек` | тайм-аут входа (умолч. 8 с) / запроса | — |
| `-W`, `-s`, `-h -1` | убрать хвостовые пробелы, разделитель, без заголовков | для разбора вывода |
| `-m-1` | показывать все сообщения, включая информационные | без пробела между `-m` и `-1` |

Примеры (`cmd` на машине администратора; вход — доменная учётная запись из `CORP\SQL-Admins`):

```bat
:: проверка входа, версии и шифрования; -C — только пока нет доверенного сертификата
sqlcmd -S sql01 -E -C -Q "SELECT @@SERVERNAME, SERVERPROPERTY('ProductVersion'), SERVERPROPERTY('Edition');"

:: сценарий с переменной и кодом возврата
sqlcmd -S sql01 -E -b -v DB=buh -i C:\Scripts\check_db.sql -o C:\Scripts\check_db.log
echo %ERRORLEVEL%

:: DAC с самого сервера (по сети — после 'remote admin connections' = 1)
sqlcmd -S sql01 -E -A -d master
```

В `check_db.sql` переменная подставляется как `$(DB)`: `SELECT name, state_desc FROM sys.databases WHERE name = N'$(DB)';` [MS Learn — `-v`]. Проверка результата — `ERRORLEVEL` = 0 и содержимое `check_db.log`.

### 2.4. SQL Server Configuration Manager

- Оснастка MMC `SQLServerManager<версия>.msc` в `C:\Windows\SysWOW64\` [MS Learn]:

| SQL Server | Файл |
|---|---|
| 2025 | `SQLServerManager17.msc` |
| 2022 | `SQLServerManager16.msc` |
| 2019 | `SQLServerManager15.msc` |
| 2017 | `SQLServerManager14.msc` |
| 2016 | `SQLServerManager13.msc` |

- **Службы**: запуск, остановка, тип запуска; **смена учётной записи служб SQL Server и Agent и их пароля — только здесь** (или SMO/WMI): утилита заодно выдаёт права в реестре и на файлы, а смена пароля так вступает в силу без перезапуска [MS Learn]. Учётная запись по умолчанию при установке — виртуальная `NT SERVICE\MSSQLSERVER` (Agent — `NT Service\SQLSERVERAGENT`; для именованного экземпляра `PAYROLL` — `NT SERVICE\MSSQL$PAYROLL` и `NT SERVICE\SQLAGENT$PAYROLL`) [MS Learn]. Подробно об учётных записях — `mssql/02`.
- **Сетевая конфигурация SQL Server → Протоколы для `<экземпляр>`**: TCP/IP вкл., Named Pipes выкл. [ИТС-мет 5904, 2019]; порт (IPAll → TCP Port); вкладка **Flags** — Force Encryption, с 2022 — Force Strict Encryption; вкладка **Certificate** — сертификат TLS (с 2019 управление сертификатами встроено, в том числе для старых версий) [MS Learn]. Изменения протоколов и шифрования — после перезапуска службы.
- **Параметры запуска** (свойства службы → Startup Parameters) [MS Learn]: `-T<флаг>` — флаг трассировки (`mssql/02`); `-e` — путь к `ERRORLOG`; `-m` / `-mSQLCMD` — однопользовательский режим; `-f` — минимальная конфигурация; `-d`/`-l` — файлы `master`.
- **Псевдонимы** клиентов: с SQL Server 2022 Configuration Manager их не создаёт — только SQL Server Client Network Utility [MS Learn]. Для 1С псевдонимы на рабочем сервере не нужны и мешают: старая методичка предупреждает, что запись на вкладке Alias меняет протокол «неожиданно» [ИТС-мет 2926, 2008].
- Удалённо — «Connect to another computer» (WMI) [MS Learn].

### 2.5. PowerShell: модуль SqlServer

- **Модули** [MS Learn]: `SqlServer` — актуальный, обновляется в PowerShell Gallery (текущая версия 22.4.5.1 от 17.06.2025 [PowerShell Gallery]), требует PowerShell 5.1+; `SQLPS` — старый, ставится с SQL Server для совместимости и больше не обновляется, им по умолчанию пользуются шаги Agent типа PowerShell. В начале сценариев — `Import-Module SqlServer`. В шаге Agent с SQL Server 2019 можно первой строкой написать `#NOSQLPS`, тогда SQLPS не загружается [MS Learn].
- **Установка** (PowerShell от имени администратора — для всех пользователей; иначе `-Scope CurrentUser`) [MS Learn]:

```powershell
Install-Module -Name SqlServer                    # с PSGallery; при конфликте имён с SQLPS — -AllowClobber
Get-Module SqlServer -ListAvailable               # проверка: версия 22.x
# без интернета: на машине с интернетом
Save-Module -Name SqlServer -Path $env:TEMP
# скопировать $env:TEMP\SqlServer\<версия> в %ProgramFiles%\WindowsPowerShell\Modules\SqlServer
```

- **`Invoke-Sqlcmd`** [MS Learn]: выполняет сценарии в синтаксисе `sqlcmd` (без `:connect`, `:out` и т. п.); `-ServerInstance` (`Компьютер\Экземпляр`), `-Database`, `-Query`/`-InputFile`, `-QueryTimeout` (без него — без ограничения), `-DedicatedAdministratorConnection`. **С версии 22 модуля `-Encrypt` по умолчанию `Mandatory`** (допустимо `Mandatory`, `Optional`, `Strict`), `-EncryptConnection` устарел, добавлены `-TrustServerCertificate` и `-HostNameInCertificate`. Ошибки T‑SQL — `-OutputSqlErrors $true` или `-AbortOnError`.
- **Умолчания шифрования у остальных командлетов модуля 22 другие** [MS Learn — `Get-SqlErrorLog`, `Set-SqlErrorLog`, `Get-SqlAgentJobHistory`; уточнено 20.10.2026]: у командлетов на SMO `-Encrypt` в версии 22 по умолчанию `Optional`, а `-TrustServerCertificate` — `$true` (совместимость с версией 21); `Mandatory` и проверку сертификата Microsoft обещает с версии 23. То есть строгие умолчания модуля 22 — только у `Invoke-Sqlcmd`.

```powershell
Import-Module SqlServer
Invoke-Sqlcmd -ServerInstance 'sql01' -Database master -TrustServerCertificate `
  -Query "SELECT name, SUSER_SNAME(owner_sid) AS owner, recovery_model_desc FROM sys.databases WHERE database_id > 4;"
```

- **Командлеты, полезные администратору 1С** [MS Learn, список модуля]: `Get-SqlErrorLog` (`-Since Midnight|Yesterday|LastWeek|LastMonth`, `-After`, `-Before`), `Set-SqlErrorLog` (`-MaxLogCount` 6–99, `-ErrorLogSizeKb`), `Get-SqlLogin`/`Add-SqlLogin`/`Remove-SqlLogin`, `Backup-SqlDatabase`/`Restore-SqlDatabase` (→ `mssql/04`), `Get-SqlAgentJob`, `Get-SqlAgentJobHistory`, `Invoke-SqlAssessment` (проверка конфигурации по правилам Microsoft). **Не использовать** `Set-SqlAuthenticationMode`, `Set-SqlNetworkConfiguration`, `Start-SqlInstance`/`Stop-SqlInstance`: им нужен SQL Server Cloud Adapter, и, по справке Microsoft, они давно не работают и **удалены в версии 22 модуля** [MS Learn — страницы этих командлетов; уточнено 20.10.2026]. Режим входа — SSMS или T‑SQL (3.3), протоколы и порт — Configuration Manager (2.4), запуск и остановка службы — Configuration Manager или `net start`/`net stop`.

```powershell
# ошибки входа за сутки
Get-SqlErrorLog -ServerInstance 'sql01' -Since Yesterday -TrustServerCertificate |
  Where-Object { $_.Text -match '18456|Login failed' } | Format-Table Date, Source, Text -AutoSize
```

### 2.6. dbatools [сторонний]

- Модуль сообщества (`github.com/dataplat/dbatools`, сайт `dbatools.io`), версия **2.9.1 от 15.10.2026**; Windows PowerShell 3+ или PowerShell 7.4+ (Linux/macOS — около 78 % команд, без WMI); SQL Server 2012+ — 100 % команд [сторонний — README]. Установка: `Install-Module dbatools -Scope CurrentUser`; с 2.5.5 модуль подписан Azure Trusted Signing — при обновлении со старой версии `Install-Module dbatools -Force -SkipPublisherCheck` [сторонний].
- **Шифрование**: dbatools 2.x требует шифрования и проверяет сертификат, как новые клиентские библиотеки Microsoft; для стенда без сертификата — `Set-DbatoolsInsecureConnection` (параметр `-SessionOnly` — только на текущий сеанс) [сторонний]. В рабочей среде лучше доверенный сертификат (раздел 12.1).
- Команды для задач этой статьи (имена и параметры — по исходникам 2.9.1) [сторонний]:

| Задача | Команда |
|---|---|
| найти/исправить сирот | `Get-DbaDbOrphanUser -SqlInstance sql01 -Database buh`; `Repair-DbaDbOrphanUser -SqlInstance sql01 -Database buh` (без `-RemoveNotExisting` — только переназначает) |
| перенести логины с SID и паролем | `Copy-DbaLogin -Source sql01 -Destination sql02 -Login buh_1c`; в файл — `Export-DbaLogin -SqlInstance sql01 -Login buh_1c -FilePath C:\Temp\buh_1c.sql` |
| проверить/сменить владельца | `Test-DbaDbOwner -SqlInstance sql01 -TargetLogin buh_1c -Database buh`; `Set-DbaDbOwner -SqlInstance sql01 -Database buh -TargetLogin buh_1c` |
| журнал ошибок | `Get-DbaErrorLog -SqlInstance sql01 -Source Logon -After (Get-Date).AddDays(-1)` |
| файлы и рост | `Get-DbaDbFile -SqlInstance sql01 -Database buh`; `Set-DbaDbFileGrowth -SqlInstance sql01 -Database buh -GrowthType MB -Growth 512` |
| файлы баз, не подключённые к экземпляру | `Find-DbaOrphanedFile -SqlInstance sql01` |
| шифрование соединений | `Get-DbaNetworkEncryption -SqlInstance sql01`; `Set-DbaNetworkCertificate -SqlInstance sql01 -Thumbprint <отпечаток> -RestartService` |
| проверить последнюю копию восстановлением | `Test-DbaLastBackup` → `mssql/04` |

> ⚠ **`Set-DbaDbOwner` без `-TargetLogin` делает владельцем `sa`** (или переименованный `sa`) [сторонний]. Для баз 1С, где владелец — логин ИБ, это **лишит 1С прав `dbo`**: запускать только с `-TargetLogin <логин ИБ>` и `-Database`.

### 2.7. Прочие сторонние средства

- **First Responder Kit** (`sp_Blitz`, `sp_BlitzFirst`, `sp_BlitzIndex`; `github.com/BrentOzarULTD/SQL-Server-First-Responder-Kit`, выпуск 20260708) и **sp_WhoIsActive** (`github.com/amachanic/sp_whoisactive`, выпуск 20260409) [сторонний] — проверка конфигурации и текущей активности; применение — `mssql/06`.
- **SQL Server Maintenance Solution** Ола Халленгрена (`github.com/olahallengren/sql-server-maintenance-solution`) [сторонний] — задания Agent для копий, `CHECKDB` и индексов; ставится и `Install-DbaMaintenanceSolution` [сторонний]. Настройка под 1С — `mssql/05`.

### 2.8. SQL Server на Linux: чем администрирование отличается

- Нет Configuration Manager — всё через `/opt/mssql/bin/mssql-conf` и `systemctl` (служба `mssql-server`), после большинства изменений — `sudo systemctl restart mssql-server` [MS Learn]. Клиентские утилиты — `mssql-tools18` (`/opt/mssql-tools18/bin/sqlcmd`); ключ `-A` (DAC) в `sqlcmd` на Linux не поддерживается [MS Learn].
- Agent есть в пакете `mssql-server` с 2017 CU4, по умолчанию выключен: `sudo /opt/mssql/bin/mssql-conf set sqlagent.enabled true` [MS Learn]; профиль Database Mail для Agent — `mssql-conf set sqlagent.databasemailprofile <профиль>` или переменная `MSSQL_AGENT_EMAIL_PROFILE` [MS Learn].
- Журнал ошибок — `/var/opt/mssql/log` (`filelocation.errorlogfile`), число архивов — `errorlog.numerrorlogs`; каталоги данных/журналов/копий по умолчанию — `/var/opt/mssql/data` (`filelocation.defaultdatadir`, `…defaultlogdir`, `…defaultbackupdir`) [MS Learn].
- TLS — `network.tlscert`, `network.tlskey`, `network.forceencryption` (для 2022 и старше ещё `network.tlsprotocols`) [MS Learn] (раздел 12.1).
- Вход Windows (Kerberos) на Linux требует ввода в AD и keytab (`adutil`, `mssql-conf setup-ad-keytab`) — `docs/linux/security/authentication/…` [MS Learn]; для 1С проще вход SQL Server [практика].
- В Linux-контейнере/ВМ SQL Server для 1С поддерживается только вместе с рабочими серверами 1С на Windows (раздел 1).

## 3. Учётные записи и права для 1С

### 3.1. Модель безопасности SQL Server в двух словах

- **Логин** (server principal, `sys.server_principals`) — вход на экземпляр: SQL Server (`type_desc = SQL_LOGIN`) или Windows (пользователь/группа). **Пользователь** (database principal, `sys.database_principals`) — представитель логина внутри базы; связь — по **SID**, а не по имени [MS Learn].
- **Владелец базы** (`sys.databases.owner_sid`) внутри базы виден как пользователь **`dbo`** и имеет все права в ней; для логина-владельца отдельного пользователя в базе нет [MS Learn — `sp_changedbowner`, `CREATE DATABASE`]. Именно так устроен типовой доступ 1С: логин ИБ — владелец базы.
- **Серверные роли** (`sysadmin`, `serveradmin`, `securityadmin`, `processadmin`, `setupadmin`, `bulkadmin`, `diskadmin`, `dbcreator`, `public`) действуют на весь экземпляр; с SQL Server 2022 добавлены 10 ролей `##MS_…##` под принцип наименьших привилегий [MS Learn].
- В `master` и `tempdb` гость (`guest`) включён и отключить его там нельзя (`REVOKE CONNECT FROM GUEST` недопустим именно в `master` и `tempdb`) [MS Learn] — поэтому любой логин может читать `master` и создавать временные объекты в `tempdb` без отдельных прав. Достаточно ли этого для требования ИТС «чтение `master` и полный доступ к `tempdb`» — ИТС не уточняет ⚠; на практике отдельных прав не выдают [практика].

### 3.2. Что требует 1С и что это значит в терминах SQL Server

| Требование 1С | Где сказано | Что даёт в SQL Server [MS Learn] | Комментарий |
|---|---|---|---|
| Логин, от имени которого сервер 1С работает с MS SQL, — член `processadmin` или `sysadmin` | [ИТС-КС разд. 3.2.3; ИТС-адм разд. 5.2.1.3.2] | `processadmin` — завершать процессы экземпляра; `KILL` требует `ALTER ANY CONNECTION`, которое входит в `sysadmin` и `processadmin` | действует на **все** сеансы экземпляра, не только своей ИБ |
| Зачем `processadmin`: «Удалить» соединение, выполняющее долгий запрос, из консоли кластера | [ИТС-мет 1595, 2007; ИТС-КС разд. 5.2.12.3] | — | без роли попытка разрыва «не успешна», запрос продолжает работать; для PostgreSQL команда ничего не делает [ИТС-КС разд. 5.2.12.3]. Чем именно платформа прерывает запрос (`KILL` или отмена), ИТС не пишет ⚠ |
| Пользователь базы — `sa` или владелец базы (если она уже есть) | [ИТС-адм разд. 5.2.1.3.2] | владелец = `dbo`, все права в базе | нужно, чтобы «беспрепятственно модифицировать структуру» (реструктуризация) |
| При готовой базе — чтение `master`, полный доступ к `tempdb` | [ИТС-адм разд. 5.2.1.3.2] | даётся по умолчанию через `guest`/`public` (3.1) | ⚠ |
| Создание базы из 1С («Создать базу данных в случае ее отсутствия», `--create-database`, `CrSQLDB=Y`) | [ИТС-адм разд. 5.2.1.3.6]; [ИТС-мет 2926, 2008 — роль Database Creators] | `CREATE DATABASE` требует `CREATE DATABASE`, `CREATE ANY DATABASE` или `ALTER ANY DATABASE`; `dbcreator` — создать, изменить, удалить и **восстановить любую** базу; с 2022 — `##MS_DatabaseManager##` (создаёт базы и удаляет только свои) | создатель становится владельцем [MS Learn — `CREATE DATABASE`] |
| Пользовательские табличные пространства (КОРП) | [ИТС-КС разд. 5.5.5.2.1] | право `ALTER` на базу | у владельца есть |
| Удаление ИБ из консоли с вариантом «Удалить базу данных» | [ИТС-КС разд. 5.2.7.3] | `DROP DATABASE` требует `CONTROL` на базу, `ALTER ANY DATABASE`, `dbcreator` или `db_owner` этой базы | владельцу хватает |
| SQL Server 2014: флаг 4199 — иначе платформа включает его на каждое соединение и без прав администратора СУБД выдаёт ошибку | [ИТС-адм разд. 5.2.1.3.2] | — | `-T4199` в параметрах запуска (`mssql/02`) |
| Каждой ИБ — свой пользователь СУБД с минимально нужными правами | [ИТС-КС прил. 3, разд. 3.7] | — | имя пользователя СУБД = имя ИБ — быстрее расследовать на общем сервере [ИТС-мет 5899, 2016] |
| Чек-лист 2019: логин на каждую базу, роли `public`, `dbcreator` | [ИТС-мет 5904, 2019] | — | `processadmin` в чек-листе не упомянут, но требуется документацией (строка 1) |

**Вывод для общего экземпляра** [практика, на основе MS Learn]: логину ИБ — `processadmin` (без него не работает «Удалить соединение») + владение своей базой; `dbcreator` — только на время создания, затем снять [ИТС-мет 2926, 2008]; `sysadmin` — никогда. Учтите: член фиксированной серверной роли может добавлять в неё другие логины [MS Learn — `ALTER SERVER ROLE`, server-level roles] — логин 1С с `processadmin` способен выдать `processadmin` кому угодно, а с `dbcreator` — `dbcreator`; ещё один довод не оставлять `dbcreator` и следить за членством ролей аудитом (`SERVER_ROLE_MEMBER_CHANGE_GROUP`, 12.4). Риск `processadmin` (право завершить чужой сеанс) документацией 1С принят как неизбежный; альтернативы вроде пользовательской серверной роли с `ALTER ANY CONNECTION` ИТС не описывает ⚠ — не применять без проверки на стенде.

### 3.3. Вход SQL Server или вход Windows

| | Вход SQL Server (рекомендуется) | Вход Windows (аутентификация ОС) |
|---|---|---|
| Как задаётся в ИБ | «Пользователь базы данных» и пароль в свойствах ИБ | поля пустые — кластер подключается от имени пользователя, под которым работает конкретный `rphost` [ИТС-адм разд. 5.2.1.3.2] |
| Разные права на разные ИБ | да — свой логин на ИБ | нет — у всех ИБ кластера один пользователь ОС [ИТС-мет 2926, 2008]; разделить можно только `swpuser.ini` [ИТС-КС прил. 3, разд. 3.4] |
| Требование к экземпляру | смешанный режим (SQL Server and Windows Authentication) [ИТС-мет 5904, 2019]; переключение режима — с перезапуском службы [MS Learn] | — |
| Пароль | хранится в регистрации ИБ в кластере; меняется в двух местах (3.7) | не нужен |
| SQL Server на другом компьютере | работает | пользователь `rphost` должен быть **доменным**: локальный `USR1CV8` машины 1С на другом компьютере не аутентифицируется [практика] ⚠; Kerberos — при зарегистрированном SPN (12.2), иначе NTLM [MS Learn] |

Режим проверки подлинности: `SELECT SERVERPROPERTY('IsIntegratedSecurityOnly');` — `1` только Windows, `0` смешанный [MS Learn]. Переключение — SSMS → свойства сервера → Security → «SQL Server and Windows Authentication mode», затем перезапуск служб SQL Server и Agent [MS Learn]. T‑SQL-вариант Microsoft — запись в реестр от `sysadmin`: `EXECUTE xp_instance_regwrite N'HKEY_LOCAL_MACHINE', N'Software\Microsoft\MSSQLServer\MSSQLServer', N'LoginMode', REG_DWORD, 2;` (`2` — смешанный, `1` — только Windows) и перезапуск; права — `sysadmin` или `CONTROL SERVER` [MS Learn]; ⚠ ошибка в реестре может потребовать переустановки ОС — Microsoft прямо предупреждает. Командлет `Set-SqlAuthenticationMode` для этого не годится: он требовал SQL Server Cloud Adapter и удалён в версии 22 модуля `SqlServer` [MS Learn; уточнено 20.10.2026]. При переходе с «только Windows» на смешанный режим `sa` остаётся отключённым [MS Learn].

### 3.4. Логин для ИБ: создание и проверка

Выполнять в SSMS или `sqlcmd` от имени члена `sysadmin`. Создать логин может и `securityadmin` (с 2022 — `##MS_LoginManager##`), но добавить в фиксированную серверную роль — только `sysadmin` или член этой же роли [MS Learn — `CREATE LOGIN`, `ALTER SERVER ROLE`]:

```sql
USE master;
CREATE LOGIN [buh_1c]
    WITH PASSWORD = N'<сложный пароль>',
         DEFAULT_DATABASE = master,      -- умолчание и так master [MS Learn]
         CHECK_POLICY = ON,              -- умолчание ON: сложность и блокировка по политике Windows
         CHECK_EXPIRATION = OFF;         -- умолчание OFF; истёкший пароль остановит работу ИБ
ALTER SERVER ROLE processadmin ADD MEMBER [buh_1c];
-- только если базу будет создавать 1С (сценарий А, 3.5):
ALTER SERVER ROLE dbcreator ADD MEMBER [buh_1c];
```

- Пароль: от 8 до 128 символов, без одинарных кавычек и имени логина; при `CHECK_POLICY = ON` — сложность по политике Windows [MS Learn]. Пароль 1С кластер передаёт в строке подключения — избегайте символов `;` и `"` [практика] ⚠.
- `CHECK_POLICY = ON` включает и **блокировку учётной записи** по порогу неверных паролей из политики Windows [MS Learn]. Для логина 1С это риск: после смены пароля в SQL Server и до обновления регистрации ИБ рабочие процессы многократно пробуют старый пароль и могут заблокировать логин. Варианты: менять пароль по порядку 3.7; держать `CHECK_POLICY = ON` (сложность) и следить за блокировкой (`LOGINPROPERTY`), либо осознанно `CHECK_POLICY = OFF` для служебного логина [практика].
- Вход Windows для 1С (если выбран) — доменная учётная запись `rphost`: `CREATE LOGIN [CORP\svc-1c-rphost] FROM WINDOWS;` и те же роли [MS Learn — синтаксис; практика — выбор].

Проверка (от `sysadmin`):

```sql
SELECT p.name, p.type_desc, p.is_disabled, p.default_database_name,
       IS_SRVROLEMEMBER('processadmin', p.name) AS processadmin,
       IS_SRVROLEMEMBER('dbcreator',    p.name) AS dbcreator,
       IS_SRVROLEMEMBER('sysadmin',     p.name) AS sysadmin,
       l.is_policy_checked, l.is_expiration_checked,
       LOGINPROPERTY(p.name, 'IsLocked')            AS is_locked,
       LOGINPROPERTY(p.name, 'BadPasswordCount')    AS bad_pwd,
       LOGINPROPERTY(p.name, 'PasswordLastSetTime') AS pwd_set
FROM sys.server_principals AS p
LEFT JOIN sys.sql_logins AS l ON l.principal_id = p.principal_id
WHERE p.name = N'buh_1c';
```

Имена свойств `IsLocked`, `BadPasswordCount`, `PasswordLastSetTime`, `IsExpired`, `DaysUntilExpiration` и колонок `is_policy_checked`, `is_expiration_checked` — [MS Learn].

Эффективные права логина без входа под ним (нужно право `IMPERSONATE` или `sysadmin`) [MS Learn — `fn_my_permissions`; практика]:

```sql
USE master;
EXECUTE AS LOGIN = N'buh_1c';
SELECT permission_name FROM sys.fn_my_permissions(NULL, 'SERVER');   -- ожидается ALTER ANY CONNECTION, CONNECT SQL …
USE buh;
SELECT USER_NAME() AS user_in_db;                                      -- ожидается dbo
USE master;                                                            -- REVERT — только из базы, где был EXECUTE AS
REVERT;
```

Без возврата в исходную базу `REVERT` завершается ошибкой 15199 («переключитесь в исходную базу, где был вызван EXECUTE AS») [практика — сообщение сервера; в справочнике `REVERT` это правило не описано].

### 3.5. Сценарий А: базу создаёт 1С

1. Логин с `processadmin` и `dbcreator` (3.4).
2. Создать ИБ (консоль кластера, клиент «Добавить», `rac infobase create --create-database`, `1cv8 CREATEINFOBASE … CrSQLDB=Y`, `ibcmd infobase create --create-database` — раздел 6). Создатель базы становится её владельцем [MS Learn — `CREATE DATABASE`].
3. Снять `dbcreator`, если логин не должен создавать другие базы [ИТС-мет 2926, 2008]: `ALTER SERVER ROLE dbcreator DROP MEMBER [buh_1c];`.
4. Проверить владельца (3.8) и настроить файлы базы (раздел 11), модель восстановления (`mssql/04`).

Плюс сценария: сортировку и параметры базы выбирает платформа так, как она рассчитывает; минус — файлы создаются в каталогах по умолчанию экземпляра с размерами из `model` [ИТС-мет 5904, 2019] (настройка `model` — `mssql/02`).

### 3.6. Сценарий Б: базу заранее создаёт администратор СУБД

```sql
USE master;
CREATE DATABASE [buh]
ON PRIMARY (NAME = N'buh',     FILENAME = N'D:\MSSQL\Data\buh.mdf',    SIZE = 20GB, FILEGROWTH = 512MB)
LOG ON     (NAME = N'buh_log', FILENAME = N'L:\MSSQL\Log\buh_log.ldf', SIZE = 4GB,  FILEGROWTH = 512MB);
ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];     -- логин становится dbo
ALTER SERVER ROLE processadmin ADD MEMBER [buh_1c];
```

- Найдя пустую базу, платформа инициализирует в ней новую ИБ; найдя существующую ИБ — подключается к ней [ИТС-адм разд. 5.2.1.3.7]. Флажок «Создать базу данных в случае ее отсутствия» не нужен.
- **Сортировку** (`COLLATE`) здесь не задаю сознательно: какую сортировку платформа ожидает для данного «Языка (Страны)», ИТС не описывает ⚠. Косвенно: для страны «Казахстан» платформа использует сортировку `Cyrillic_Generic_CI_AS` (так в тексте ИТС; имя в SQL Server — `Cyrillic_General_CI_AS`) — значит, сортировку база получает по национальным настройкам ИБ [ИТС-разр прил. 8, разд. 8.4] ⚠. Без `COLLATE` база получит сортировку экземпляра [MS Learn]. Для конфигураций WE (у вас кластеры PostgreSQL — в `en_US.UTF-8`) вопрос сортировки на MS SQL открыт ⚠ — надёжнее сценарий А, а размеры файлов поменять после (11.2).
- `ALTER AUTHORIZATION` выполняет `sysadmin` или имеющий `TAKE OWNERSHIP` на базу и `IMPERSONATE` на новый логин [MS Learn]. Новый владелец не должен уже быть пользователем этой базы — иначе сначала удалить пользователя [MS Learn — `sp_changedbowner`] (раздел 11.6).

### 3.7. Смена пароля логина ИБ

Пароль хранится в регистрации ИБ в кластере (реестр кластера `1CV8Clst.lst` содержит список зарегистрированных ИБ [ИТС-адм прил. 3, разд. 3.7]; в каком виде хранится пароль — ⚠). Порядок [практика]:

1. Окно обслуживания; установить блокировку начала сеансов ИБ и завершить сеансы (`../1c/03`, режим `infobase update --sessions-deny=on`, `session terminate`).
2. В SQL Server: `ALTER LOGIN [buh_1c] WITH PASSWORD = N'<новый>';` [MS Learn].
3. В 1С: свойства ИБ в консоли кластера («Пароль пользователя») или `rac infobase update --cluster=<uuid> --infobase=<uuid> --infobase-user=<адм. ИБ> --infobase-pwd=<…> --db-user=buh_1c --db-pwd=<новый>` — ключи `--db-user`/`--db-pwd` принимаются командой `update` (`../1c/03`, 5.6); сверить с `rac help infobase` своей версии.
4. Снять блокировку, проверить вход в ИБ и отсутствие ошибок 18456 в журнале (раздел 9).
5. Если логин успел заблокироваться: `ALTER LOGIN [buh_1c] WITH PASSWORD = N'<новый>' UNLOCK;`; разблокировать без смены пароля — `CHECK_POLICY = OFF`, затем `ON` [MS Learn]. **Внимание**: при включении `CHECK_POLICY = ON` командой `ALTER LOGIN` `CHECK_EXPIRATION` тоже становится `ON`, если явно не указать `OFF` [MS Learn — «Password Policy», раздел «Policy enforcement»; в справочнике `ALTER LOGIN` этого пункта нет] — поэтому: `ALTER LOGIN [buh_1c] WITH CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;`.

### 3.8. Проверка: кто владелец и совпадает ли `dbo`

```sql
-- владелец по каталогу сервера и SID пользователя dbo внутри базы — должны совпадать
SELECT d.name, SUSER_SNAME(d.owner_sid) AS owner_login, d.owner_sid,
       dp.sid AS dbo_sid_in_db,
       CASE WHEN d.owner_sid = dp.sid THEN 'OK' ELSE 'MISMATCH' END AS check_dbo
FROM sys.databases AS d
CROSS APPLY (SELECT sid FROM sys.database_principals WHERE name = N'dbo') AS dp   -- в контексте текущей базы
WHERE d.name = DB_NAME();
```

Запускать в контексте каждой базы (`USE buh;`) [практика]; по всем базам — `Test-DbaDbOwner -SqlInstance sql01 -TargetLogin buh_1c -Database buh` [сторонний]. Колонки `owner_sid` и `sid` — [MS Learn].

### 3.9. Логины администраторов и служб

- **Администраторы СУБД** — доменная группа: `CREATE LOGIN [CORP\SQL-Admins] FROM WINDOWS; ALTER SERVER ROLE sysadmin ADD MEMBER [CORP\SQL-Admins];` [MS Learn — синтаксис]; личные SQL-логины администраторов не заводить, при увольнении достаточно убрать человека из группы [MS Learn — best practices; практика].
- **Мониторинг** (Zabbix, сборщики DMV): с 2022 — `##MS_ServerStateReader##` (DMV под `VIEW SERVER STATE`) или `##MS_ServerPerformanceStateReader##`; до 2022 — `GRANT VIEW SERVER STATE TO [login];` [MS Learn]. Логину 1С это не нужно.
- **Чтение журнала ошибок без `sysadmin`**: до 2019 — `securityadmin` или `VIEW SERVER STATE`; с 2022 — ещё право `VIEW ANY ERROR LOG` [MS Learn — `sp_readerrorlog`].
- **Копии**: `db_backupoperator` в базе или `dbcreator`/`sysadmin` — `mssql/04`.
- **Учётные записи служб** SQL Server и Agent — не администраторы Windows; Agent не запускать под учётной записью из группы Administrators [MS Learn — Agent security]; виртуальные учётные записи (по умолчанию) или gMSA — `mssql/02`.

### 3.10. Если потерян доступ `sysadmin`

Все логины `sysadmin` удалены, `sa` отключён или пароль утерян — порядок [MS Learn]:

```powershell
# PowerShell от имени локального администратора сервера SQL; экземпляр по умолчанию
net stop SQLSERVERAGENT                    # иначе Agent займёт единственное подключение
net stop MSSQLSERVER
net start MSSQLSERVER /f /mSQLCMD          # однопользовательский режим, только sqlcmd (SQLCMD — заглавными)
sqlcmd -E -S sql01 -Q "CREATE LOGIN [CORP\SQL-Admins] FROM WINDOWS; ALTER SERVER ROLE sysadmin ADD MEMBER [CORP\SQL-Admins];"
net stop MSSQLSERVER
net start MSSQLSERVER
net start SQLSERVERAGENT
```

В однопользовательском режиме любой член локальной группы Administrators входит как `sysadmin` [MS Learn]. ⚠ **На время процедуры все ИБ недоступны** — заранее заблокировать сеансы 1С. Ключ `-m<имя приложения>` защитой не является (имя приложения подделывается) [MS Learn]. Для именованного экземпляра службы — `MSSQL$<имя>` и `SQLAgent$<имя>`.

## 4. «Осиротевшие» пользователи и владелец базы после переноса

### 4.1. Почему это происходит

- Пользователь базы связан с логином по SID; если на целевом экземпляре логина с таким SID нет (база восстановлена/подключена на другом сервере, логин удалён), пользователь становится «осиротевшим» и войти под ним нельзя [MS Learn].
- **Владелец**: при восстановлении базы на другом компьютере её владельцем автоматически становится логин, который выполнял восстановление [MS Learn — «Manage metadata when making a database available on another server»]. В базе же пользователь `dbo` по-прежнему несёт SID прежнего владельца (поэтому в 3.8 возникает `MISMATCH`) [практика] ⚠.
- Логины Windows (доменные) имеют SID из AD и при переносе в пределах домена не «сиротеют»; проблема — у входов SQL Server, которые на каждом экземпляре получают новый SID, если не задан явно [MS Learn — `CREATE LOGIN … SID`].

### 4.2. Типичный случай 1С: логин ИБ — владелец базы

Логин `buh_1c` создал базу или получил её через `ALTER AUTHORIZATION` — в базе он `dbo`, отдельного пользователя `buh_1c` там нет. После `RESTORE` на другом сервере (или пересоздания логина):

- владельцем стал администратор, который восстанавливал; у `buh_1c` нет доступа к базе — в 1С ошибка открытия базы, в журнале SQL Server — `Login failed … State 38/46` («не найдена запрошенная база» — так SQL Server отвечает и при отсутствии доступа) [MS Learn — состояния 18456] ⚠;
- `ALTER USER [buh_1c] WITH LOGIN = [buh_1c]` **не поможет**: пользователя с таким именем в базе нет [практика].

Исправление (от `sysadmin`) [MS Learn]:

```sql
-- на целевом сервере: логин уже создан (4.5), лучше с тем же SID
ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];
ALTER SERVER ROLE processadmin ADD MEMBER [buh_1c];
-- проверка: запрос 3.8 в контексте buh → OK; затем вход в ИБ из 1С
```

Если `ALTER AUTHORIZATION` отвечает, что логин уже является пользователем базы, — в базе остался обычный пользователь с этим логином: удалить его (`DROP USER [buh_1c];`, если он не владеет схемами) и повторить [MS Learn — `sp_changedbowner`; практика]. ⚠ Перед `DROP USER` проверить, что он не владеет схемами (`SELECT name FROM sys.schemas WHERE principal_id = USER_ID(N'buh_1c');`).

### 4.3. Случай, когда логин 1С — обычный пользователь базы

Если администратор дал доступ через пользователя (например, `CREATE USER [buh_1c] FOR LOGIN [buh_1c]; ALTER ROLE db_owner ADD MEMBER [buh_1c];`), то после переноса это классическая «сирота» [MS Learn]:

```sql
USE buh;
-- найти сирот (пользователи входа SQL Server без логина)
SELECT dp.type_desc, dp.sid, dp.name AS user_name
FROM sys.database_principals AS dp
LEFT JOIN sys.server_principals AS sp ON dp.sid = sp.sid
WHERE sp.sid IS NULL AND dp.authentication_type_desc = 'INSTANCE';
-- сопоставить с существующим логином
ALTER USER [buh_1c] WITH LOGIN = [buh_1c];
```

- `sp_change_users_login` (`Report`, `Auto_Fix`, `Update_One`) устарела — вместо неё приведённый запрос и `ALTER USER … WITH LOGIN` [MS Learn].
- Пакетно: `Get-DbaDbOrphanUser` / `Repair-DbaDbOrphanUser -SqlInstance sql02 -Database buh` [сторонний] — переназначает на логины с теми же именами.
- Владение через `db_owner` вместо `dbo` для 1С ИТС не описывает (требуется «`sa` либо владелец базы» [ИТС-адм разд. 5.2.1.3.2]) — держитесь варианта «логин = владелец» [практика].

### 4.4. Пересоздать отсутствующий логин с прежним SID

Если на целевом сервере логина нет, а пользователь в базе есть, — создать логин с SID пользователя [MS Learn]:

```sql
USE buh;  SELECT name, sid FROM sys.database_principals WHERE name = N'buh_1c';   -- узнать SID
USE master;
CREATE LOGIN [buh_1c] WITH PASSWORD = N'<пароль>', SID = 0x...;                  -- SID из запроса
```

### 4.5. Перенести логины с тем же SID и паролем

- **`sp_help_revlogin`** — сценарий из статьи Microsoft «Transfer logins and passwords between instances of SQL Server»: создаёт в `master` процедуры `sp_hexadecimal` и `sp_help_revlogin`; `EXEC sp_help_revlogin` выводит `CREATE LOGIN … WITH PASSWORD = 0x… HASHED, SID = 0x…` с исходными SID и паролем [MS Learn]. Выполнить вывод на целевом сервере — сироты не появятся.
- **Вручную** [MS Learn — `CREATE LOGIN`, пример с `HASHED`]: `SELECT name, password_hash, sid FROM sys.sql_logins WHERE name = N'buh_1c';` на источнике; на цели — `CREATE LOGIN [buh_1c] WITH PASSWORD = 0x<hash> HASHED, SID = 0x<sid>, CHECK_EXPIRATION = OFF;`. Подтверждено 20.10.2026 (синтаксис `CREATE LOGIN`: `SID` — элемент списка параметров после `PASSWORD = … HASHED`; ровно такую команду формирует `sp_help_revlogin` в статье поддержки Microsoft). Хэш паролей SQL Server 2012+ переносится только на 2012+ [сторонний — dbatools `Copy-DbaLogin`]. С SQL Server 2025 хэш паролей другой — итерационный PBKDF2 (RFC 2898), версия 3, первый байт `0x03`; до 2022 включительно — SHA-512 с солью, версия 2 (`0x02`) [MS Learn — `sys.sql_logins`]. Принимает ли 2022 и младше хэш версии 3, документация не говорит ⚠ — при переносе логинов с 2025 на младшую версию задать пароль заново.
- **dbatools**: `Copy-DbaLogin -Source sql01 -Destination sql02 -Login buh_1c` — переносит логин с SID, паролем, серверными ролями и сопоставлениями; нужны права `sysadmin` на обоих экземплярах [сторонний]. В файл — `Export-DbaLogin`.
- Серверные роли (`processadmin`) и права уровня сервера переносятся отдельно: они хранятся в `master` целевого экземпляра [MS Learn].

### 4.6. Порядок переноса базы 1С на другой экземпляр (сводно)

1. Логин на целевом экземпляре — с исходным SID (4.5).
2. Копия/восстановление — `mssql/04`; перенос файлов — 11.5.
3. Владелец — `ALTER AUTHORIZATION` (4.2), проверка 3.8; сироты — 4.3.
4. `processadmin` логину; задания Agent и оповещения — перенести (`msdb` не переносится с базой [MS Learn]).
5. В 1С: изменить «Сервер баз данных» в регистрации ИБ (консоль или `rac infobase update --db-server=sql02`), смещение дат — не меняется и задаётся только при создании ИБ [ИТС-адм разд. 5.2.1.3.2]; для **копии** — регистрировать с блокировкой регламентных заданий [ИТС-адм разд. 5.2.1.3.6].
6. Проверить уровень совместимости базы и версию SQL Server (`mssql/07`).

## 5. Контейнерные (частично автономные) базы — применимость к 1С

- **Что это** [MS Learn]: база с `CONTAINMENT = PARTIAL`, у которой метаданные и пользователи (с паролем или Windows) живут в самой базе; пользователь аутентифицируется базой без логина в `master`, поэтому не может «осиротеть». В SQL Server доступна только частичная автономия (`PARTIAL`). Требует серверной опции `contained database authentication` = 1 (умолчание `0`); проверка базы — `SELECT name, containment_desc FROM sys.databases;`.
- **Ограничения** [MS Learn]: строка подключения обязана содержать имя базы; пользователь контейнерной базы — принципал уровня базы и не может быть членом серверных ролей; не поддерживаются репликация, CDC, отслеживание изменений; другая логика сортировок (`catalog collation`).
- **Риск безопасности** [MS Learn]: при включённой опции владельцы баз и пользователи с `ALTER ANY USER` (`db_owner`, `db_accessadmin`) сами выдают доступ к экземпляру — контроль уходит от `sysadmin`.
- **Вывод для 1С** [практика] ⚠: ИТС контейнерные базы не упоминает; требования 1С — логин уровня сервера в роли `processadmin` (а для создания базы — с правом `CREATE DATABASE`) — пользователем контейнерной базы не выполнить. Строку подключения с указанием базы как контейнерного пользователя платформа, по всей видимости, не формирует ⚠. **Не включать** `contained database authentication` на экземпляре 1С; перенос между серверами решать переносом логинов с SID (4.5).

## 6. Информационная база на MS SQL: создание, удаление, `rac` и `ibcmd`

### 6.1. Способы создания

| Способ | Где выполняется | Что нужно | Подробно |
|---|---|---|---|
| Консоль кластера: «Информационные базы → Создать» | Windows с консолью | права администратора кластера | [ИТС-КС разд. 5.2.7.1]; `../1c-windows/02`, 5.3 |
| Клиент: «Добавить → Создание новой информационной базы → На сервере 1С:Предприятия» | рабочее место Windows | — | [ИТС-адм разд. 5.2.1.3] |
| `rac infobase create --create-database … --dbms=MSSQLServer` | любой хост с `rac` (также Linux) → `ras` кластера на Windows | `ras` на центральном сервере | `../1c/03`, 5.6; `../1c/06`, 2.2 |
| `1cv8 CREATEINFOBASE "Srvr=…;Ref=…;DBMS=MSSQLServer;DBSrvr=…;DB=…;DBUID=…;DBPwd=…;SQLYOffs=2000;CrSQLDB=Y;SchJobDn=Y"` | Windows с клиентом | — | [ИТС-адм прил. 7, разд. 7.7.4]; `../1c-windows/02`, 5.3 |
| `ibcmd infobase create --dbms=MSSQLServer … --create-database` | **только Windows** (автономный режим) | — | [ИТС-адм разд. 7.4.4; прил. 4, разд. 4.10.4.2]; `../1c/06`, 3.5 |

Параметры, специфичные для MS SQL [ИТС-адм разд. 5.2.1.3.2]:

- **Сервер баз данных** — имя компьютера (если экземпляр один) или имя экземпляра; в ИТС пример записан `Server/instance` (в нотации Microsoft — `Server\instance`, какой разделитель принимает платформа — ⚠, обычно `\` [практика]). Префикс `lpc:` — общая память, если SQL Server на той же машине и установлен Native Client; но оптимизированная реструктуризация (`UpdateDBCfg=v2`) работает только по TCP/IP [ИТС-адм прил. 3, разд. 3.17.23] — `../1c-windows/02`, 5.1.
- **Имя базы данных** — латиница, цифры, `_`, `$`, первый символ — буква или `_`, до 63 символов, без пробелов, не зарезервированное слово [ИТС-адм разд. 5.2.1.3.2].
- **Пользователь/пароль** — раздел 3; пусто — аутентификация ОС от имени `rphost`.
- **Смещение дат** `0` или `2000`; при регистрах накопления или бухгалтерии — **2000**; после создания не меняется [ИТС-адм разд. 5.2.1.3.2]. Умолчания у инструментов разные: `SQLYOffs` — 0 [ИТС-адм прил. 7, разд. 7.7.4], `ibcmd --date-offset` — 2000 [ИТС-адм прил. 4, разд. 4.10.4.2]; указывать явно.
- **Одна база СУБД — одна ИБ**: две ИБ на одной базе ломают блокировки и могут разрушить данные [ИТС-адм разд. 5.2.1.3.8].

### 6.2. Что проверить в SQL Server после создания

```sql
SELECT name, SUSER_SNAME(owner_sid) AS owner, collation_name, recovery_model_desc,
       compatibility_level, is_read_committed_snapshot_on, containment_desc,
       is_auto_shrink_on, is_encrypted, state_desc, user_access_desc
FROM sys.databases WHERE name = N'buh';
SELECT name, type_desc, physical_name, size / 128 AS size_mb,
       CASE WHEN is_percent_growth = 1 THEN CONCAT(growth, ' %') ELSE CONCAT(growth / 128, ' MB') END AS growth,
       max_size
FROM sys.master_files WHERE database_id = DB_ID(N'buh');
```

Ожидается [практика; колонки — MS Learn]: владелец — логин ИБ; `is_auto_shrink_on = 0`; рост файлов в МБ (11.2); `containment_desc = NONE`; модель восстановления — по политике копий (`mssql/04`); `is_read_committed_snapshot_on` — `mssql/08`; `compatibility_level` — `mssql/07`. `dbcreator` снят (3.5).

### 6.3. Удаление ИБ и базы

- **Из консоли кластера** «Удалить» предлагает три варианта: «Удалить базу данных» (регистрация + база на сервере СУБД), «Очистить базу данных» (регистрация + все данные, сама база остаётся), «Оставить без изменений» (только регистрация). Если к базе есть соединения, регистрация удалится, а СУБД вернёт ошибку и базу не удалит [ИТС-КС разд. 5.2.7.3]. В `rac` — `infobase drop --drop-database | --clear-database` (`../1c/03`, 5.6).
- **Вручную в SQL Server** — ⚠ **разрушающая операция, необратима**. Сначала копия `BACKUP DATABASE … WITH COPY_ONLY, CHECKSUM` (`mssql/04`) и снятие регистрации ИБ в кластере (вариант «Оставить без изменений»), затем (от `sysadmin` или владельца):

```sql
USE master;
BACKUP DATABASE [buh] TO DISK = N'E:\Backup\buh_before_drop.bak' WITH COPY_ONLY, CHECKSUM, STATS = 10;
ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;    -- обрывает соединения
DROP DATABASE [buh];
SELECT name FROM sys.databases WHERE name = N'buh';             -- пусто
```

`DROP DATABASE` требует `CONTROL` на базу, `ALTER ANY DATABASE`, `dbcreator` или `db_owner` этой базы; снимки базы удалить заранее [MS Learn]. Если у базы `AUTO_UPDATE_STATISTICS_ASYNC = ON` (так советует для баз 1С [ИТС-мет 5904, 2019]), фоновый поток статистики может занять единственное подключение режима `SINGLE_USER` — перед ним выполнить `ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC OFF;` [MS Learn — `sp_detach_db`, «Obtain exclusive access»]. Логин ИБ после этого удалить отдельно (`DROP LOGIN [buh_1c];`), если он больше нигде не владеет базами (`SELECT name FROM sys.databases WHERE owner_sid = SUSER_SID(N'buh_1c');`) [практика].

### 6.4. `rac` для ИБ на MS SQL (кратко)

Подробный справочник — `../1c/03`, 5.6; синтаксис сверять с `rac help infobase` своей версии. Для MS SQL важны: `--dbms=MSSQLServer`, `--db-server=sql01` (или `sql01\ERP`), `--db-name`, `--db-user`/`--db-pwd` (для `create` и `update`), `--date-offset=2000` (только для MS SQL; умолчание у `rac` — ⚠), `--create-database`, `--scheduled-jobs-deny=on` для копий; удаление — `infobase drop --drop-database|--clear-database`. В 8.5.4 `rac infobase create` принимает все параметры `update` (`../1c/03`). Сам `rac` может работать с Linux-машины администратора — кластер при этом на Windows [практика].

```bash
# с машины администратора; кластер srv1c на Windows; SQL Server sql01
rac infobase create --cluster=$CL $AUTH --create-database \
    --name=buh --dbms=MSSQLServer --db-server=sql01 --db-name=buh \
    --db-user=buh_1c --db-pwd="$SQL_PWD" --date-offset=2000 --locale=ru_RU \
    --scheduled-jobs-deny=on --license-distribution=allow
rac infobase info --cluster=$CL --infobase=<uuid> --infobase-user=<адм ИБ> --infobase-pwd=<…>   # db-server, db-name, db-user
```

### 6.5. `ibcmd` и `ibsrv` с MS SQL (кратко)

Справочник — `../1c/06`, раздел 3. Для MS SQL [ИТС-адм разд. 7.2, 7.4; прил. 4, разд. 4.9, 4.10]:

- **Только Windows**: автономный сервер на Linux с MS SQL не работает [ИТС-адм разд. 7.2].
- `--dbms=MSSQLServer` (в примерах ИТС встречается `mssqlserver`), `--database-server`/`--db-server`, `--database-name`/`--db-name`, `--database-user`/`--db-user`, `--database-password`/`--db-pwd`, `--request-database-password` (`-W`, пароль из стандартного ввода), `--date-offset` (умолчание 2000). Для **`ibsrv`** имя и пароль СУБД с MS SQL можно не указывать — тогда аутентификация ОС от имени процесса `ibsrv` [ИТС-адм прил. 4, разд. 4.9]; для `ibcmd` такое поведение в таблице параметров не оговорено ⚠.
- **Нельзя** направлять `ibcmd`/`ibsrv` на базу, которая сейчас работает под кластером, — возможна порча [ИТС-адм разд. 7.2].
- Перенос MS SQL → PostgreSQL без `.dt`: `ibcmd infobase replicate --dbms=MSSQLServer … --target-dbms=PostgreSQL … --target-create-database` [ИТС-адм разд. 7.4.17] — запускать на Windows; `../1c-windows/02`, 12.2.

```bat
:: создать ИБ в новой базе MS SQL; пароль СУБД спросит из stdin
ibcmd infobase create --dbms=MSSQLServer --database-server=sql01 --database-name=buh_test ^
  --database-user=buh_1c --request-database-password --date-offset=2000 ^
  --create-database --data="D:\ss-data\buh_test" --restore="E:\dt\buh.dt"
```

Права логина те же, что в сценарии А (3.5): создание базы требует `dbcreator` на время операции.

## 7. SQL Server Agent: задания, расписания, операторы, оповещения

### 7.1. Что это и где есть

- Служба Windows, выполняющая задания по расписанию, по оповещению или вручную (`sp_start_job`); описание заданий хранится в `msdb` [MS Learn]. Служба: `SQLSERVERAGENT` (экземпляр по умолчанию) или `SQLAgent$<экземпляр>` [MS Learn]. По умолчанию при установке служба отключена, если не выбран автозапуск [MS Learn] — после установки поставить тип запуска «Автоматически» в Configuration Manager.
- **Редакции**: Enterprise и Standard — да; **Express — нет** (2022, 2025) [MS Learn]. Без Agent — Планировщик заданий Windows + `sqlcmd -b` (`../1c-windows/02`, 9.6).
- **Linux**: с 2017 CU4 входит в `mssql-server`, включается `mssql-conf set sqlagent.enabled true` [MS Learn].
- Опция `Agent XPs` по умолчанию `0`; при запуске службы Agent из SSMS она включается автоматически, иначе — `EXEC sp_configure 'show advanced options', 1; RECONFIGURE; EXEC sp_configure 'Agent XPs', 1; RECONFIGURE;` (параметр расширенный; действует без перезапуска); пока она `0`, узел Agent в SSMS пуст [MS Learn — `Agent XPs`; уточнено 20.10.2026].
- **С SQL Server 2025** Agent поддерживает TDS 8.0 и TLS 1.3 и выбирает шифрование подключения к экземпляру по его настройке: Force Strict Encryption → `strict`, Force Encryption → `mandatory`, иначе `optional`; так же подключаются локальные шаги T‑SQL. **Если в ОС оставлен только TLS 1.3, а на экземпляре не включён Force Strict Encryption (только Force Encryption или ничего), Agent не стартует** — TLS 1.3 требует strict [MS Learn — SQL Server Agent, «TDS 8.0 and strict encryption support»; уточнено 20.10.2026: какой драйвер использует Agent, документация не называет].
- На отказоустойчивом кластере (FCI) задания, выполнявшиеся в момент перехода, после него не продолжаются [MS Learn].

Задания для баз 1С — копии (`mssql/04`), статистика/индексы/`CHECKDB` (`mssql/05`). Ниже — механика и безопасность.

### 7.2. Безопасность Agent

- Доступ к Agent у не-`sysadmin` — через роли `msdb`: `SQLAgentUserRole`, `SQLAgentReaderRole`, `SQLAgentOperatorRole`; по умолчанию в них никого нет [MS Learn].
- **Шаги T‑SQL выполняются в контексте владельца задания**: смена `@owner_login_name` меняет права шагов [MS Learn]. Шаги других типов (CmdExec, PowerShell) у не-`sysadmin` выполняются через прокси (учётные данные + подсистема); шаг без прокси работает под учётной записью службы Agent — такие создаёт только `sysadmin` [MS Learn].
- Рекомендации Microsoft: служба Agent — не член группы Administrators; отдельные учётные записи для прокси с минимальными правами; Agent имеет права `sysadmin` в экземпляре [MS Learn].
- **Владелец заданий** [практика]: не личная учётная запись администратора (уволится — задание перестанет работать). Обычно владельцем ставят `sa` (даже отключённый ⚠ — поведение отключённого владельца в документации, прочитанной для статьи, не описано; проверьте на стенде) или служебный логин; смена — `EXEC msdb.dbo.sp_update_job @job_name = N'…', @owner_login_name = N'…';`, менять владельца может только `sysadmin` [MS Learn].
- Логину 1С доступ к Agent не нужен.

### 7.3. Задание через T‑SQL

От `sysadmin`, в `msdb`. Пример — ежедневная проверка целостности базы `buh` в 01:30 с оповещением оператора при ошибке (оператор — 7.5; содержание шага — `mssql/05`):

```sql
USE msdb;
EXEC dbo.sp_add_job
     @job_name = N'buh - CHECKDB',
     @enabled = 1,
     @description = N'Проверка целостности базы 1С buh',
     @owner_login_name = N'sa',                    -- см. 7.2
     @notify_level_eventlog = 2,                   -- 2 = при ошибке (умолчание)
     @notify_level_email = 2,
     @notify_email_operator_name = N'DBA';
EXEC dbo.sp_add_jobstep
     @job_name = N'buh - CHECKDB',
     @step_name = N'DBCC CHECKDB',
     @subsystem = N'TSQL',                         -- умолчание
     @database_name = N'master',
     @command = N'DBCC CHECKDB (N''buh'') WITH NO_INFOMSGS, ALL_ERRORMSGS;',
     @on_success_action = 1,                       -- выйти с успехом
     @on_fail_action = 2,                          -- выйти с ошибкой (умолчание)
     @retry_attempts = 0,
     @output_file_name = N'E:\Logs\buh_checkdb.txt';
EXEC dbo.sp_add_schedule
     @schedule_name = N'Ежедневно 01:30',
     @freq_type = 4,                               -- ежедневно
     @freq_interval = 1,                           -- каждый 1 день
     @active_start_time = 013000;                  -- HHMMSS
EXEC dbo.sp_attach_schedule @job_name = N'buh - CHECKDB', @schedule_name = N'Ежедневно 01:30';
EXEC dbo.sp_add_jobserver   @job_name = N'buh - CHECKDB', @server_name = N'(local)';
-- запуск вручную и проверка
EXEC dbo.sp_start_job @job_name = N'buh - CHECKDB';
```

- Имена параметров и значения — [MS Learn, справочники `sp_add_job`, `sp_add_jobstep`, `sp_add_schedule`, `sp_attach_schedule`, `sp_add_jobserver`]: `@notify_level_*` — `0` никогда, `1` при успехе, `2` при ошибке, `3` всегда; `@on_fail_action` — `1` выйти с успехом, `2` (умолч.) выйти с ошибкой, `3` следующий шаг, `4` перейти к `@on_fail_step_id`; `@subsystem` — `TSQL` (умолч.), `CmdExec`, `PowerShell`, `SSIS` и др.; `@freq_type` — `1` однократно, `4` ежедневно, `8` еженедельно, `16` ежемесячно, `32` ежемесячно относительно, `64` при старте Agent, `128` при простое; `@active_start_time` — `HHMMSS`, умолчание `000000`. `@server_name` по умолчанию `(LOCAL)` — локальный сервер [MS Learn].
- Расписание можно разделять между заданиями; у задания может быть несколько расписаний [MS Learn].
- ⚠ Каталог `E:\Logs` должен существовать и быть доступен на запись учётной записи службы Agent [практика].

**Проверка** [MS Learn — `dbo.sysjobhistory`, `sp_help_jobhistory`]:

```sql
USE msdb;
SELECT TOP (20) j.name, h.step_id, h.step_name, h.run_status,      -- 0 ошибка, 1 успех, 2 повтор, 3 отменено, 4 выполняется
       h.run_date, h.run_time, h.run_duration, LEFT(h.message, 300) AS message
FROM dbo.sysjobhistory AS h JOIN dbo.sysjobs AS j ON j.job_id = h.job_id
WHERE j.name = N'buh - CHECKDB'
ORDER BY h.instance_id DESC;
EXEC dbo.sp_help_jobhistory @job_name = N'buh - CHECKDB';
```

`run_date` — `yyyyMMdd`, `run_time` и `run_duration` — `HHmmss` (целые числа) [MS Learn]. В PowerShell — `Get-SqlAgentJobHistory -ServerInstance sql01 -JobName 'buh - CHECKDB' -Since Yesterday` [MS Learn] или `Get-DbaAgentJob -SqlInstance sql01 -Job 'buh - CHECKDB' -IncludeExecution` [сторонний].

### 7.4. Шаг PowerShell и шаг CmdExec

- Шаг типа PowerShell по умолчанию загружает SQLPS; с SQL Server 2019 первая строка `#NOSQLPS` отключает это, дальше `Import-Module -Name SqlServer` [MS Learn].
- Шаг CmdExec (`@subsystem = N'CmdExec'`) — например `sqlcmd -S . -E -b -i …`; без прокси выполняется под учётной записью службы Agent и создаётся только `sysadmin` [MS Learn]; `@cmdexec_success_code` — код успеха [MS Learn].

### 7.5. Операторы и уведомления о заданиях

Требуется настроенная Database Mail и профиль у Agent (раздел 8) [MS Learn]:

```sql
USE msdb;
EXEC dbo.sp_add_operator @name = N'DBA', @enabled = 1, @email_address = N'dba@example.uz';
-- уведомление об ошибке существующего задания
EXEC dbo.sp_update_job @job_name = N'buh - CHECKDB',
     @notify_level_email = 2, @notify_email_operator_name = N'DBA';
SELECT name, enabled, email_address, last_email_date, last_email_time FROM dbo.sysoperators;
```

Пейджер и `net send` устарели и будут удалены — только e‑mail [MS Learn]. Оператор может быть псевдонимом списка рассылки [MS Learn]. Чек-лист 1С: «Database Mail account», операторы, отправка оповещения из планов обслуживания при ошибках [ИТС-мет 5904, 2019].

### 7.6. Оповещения (alerts)

- Оповещение — реакция на ошибку SQL Server (по номеру или серьёзности), на условие счётчика производительности или событие WMI; действия — уведомить операторов и/или запустить задание [MS Learn].
- **Срабатывает только на события, попавшие в журнал приложений Windows**: ошибки `sys.messages` серьёзности 19 и выше, `RAISERROR … WITH LOG`, сообщения, изменённые `sp_altermessage`, `xp_logevent` [MS Learn]. Если оповещение молчит — проверить, что Agent запущен и событие есть в журнале приложений [MS Learn].
- `sp_add_alert` выполняется в `msdb`; при `@severity` номер `@message_id` должен быть `0`; `@delay_between_responses` (сек, умолч. 0) — пауза между ответами; `@include_event_description_in` (умолч. 5 = e‑mail и `net send`) [MS Learn].

Минимальный набор для сервера баз 1С [практика; номера и смысл ошибок — MS Learn]:

| Оповещение | Параметр | Почему |
|---|---|---|
| Серьёзность 19–25 | `@severity = 19 … 25` (по одному на уровень) | фатальные ошибки ресурсов и целостности |
| 823 | `@message_id = 823` | ОС вернула ошибку ввода-вывода (серьёзность 24) — диск/драйвер |
| 824 | `@message_id = 824` | логическая ошибка страницы (контрольная сумма, torn page; серьёзность 24) |
| 825 | `@message_id = 825` | чтение удалось только после повторов — предвестник отказа диска |
| 9002 | `@message_id = 9002` | журнал транзакций заполнен (`log_reuse_wait_desc`) — ⚠ попадает ли в журнал приложений, проверить |
| 1105 | `@message_id = 1105` | нет места в файловой группе — ⚠ то же |

```sql
USE msdb;
EXEC dbo.sp_add_alert @name = N'Error 823', @message_id = 823, @severity = 0,
     @enabled = 1, @delay_between_responses = 300, @include_event_description_in = 1;
EXEC dbo.sp_add_notification @alert_name = N'Error 823', @operator_name = N'DBA',
     @notification_method = 1;                     -- 1 = e-mail
EXEC dbo.sp_add_alert @name = N'Severity 024', @message_id = 0, @severity = 24,
     @enabled = 1, @delay_between_responses = 300, @include_event_description_in = 1;
EXEC dbo.sp_add_notification @alert_name = N'Severity 024', @operator_name = N'DBA', @notification_method = 1;
-- аналогично 824, 825, 9002, 1105 и серьёзности 19–25
SELECT name, message_id, severity, enabled, occurrence_count, last_occurrence_date FROM dbo.sysalerts;
-- попадёт ли ошибка в журнал приложений Windows (а значит, сработает ли оповещение по номеру)
SELECT message_id, severity, is_event_logged FROM sys.messages
WHERE message_id IN (823, 824, 825, 9002, 1105) AND language_id = 1033;
```

Как закрыть «⚠» по 9002 и 1105 на своём сервере: `is_event_logged = 1` означает, что сообщение пишется в журнал событий при возникновении [MS Learn — `sys.messages`]; если там `0` и серьёзность ниже 19, оповещение по номеру не сработает — тогда `sp_altermessage` (сообщения, изменённые им, тоже попадают в журнал приложений [MS Learn — `sp_add_alert`]). Серьёзность 823 и 824 — 24 (примеры записей в справочнике ошибок) [MS Learn].

Значения `@notification_method`: `1` e‑mail, `2` пейджер, `4` `net send` (комбинируются `OR`) [MS Learn]. Проверка без аварии: `RAISERROR (N'Проверка оповещения', 19, 1) WITH LOG;` — уровни 19–25 допускаются только с `WITH LOG` и только у `sysadmin` или с правом `ALTER TRACE`; `WITH LOG` пишет в журнал ошибок и в журнал приложений [MS Learn — `RAISERROR`], поэтому оповещение уровня 19 должно сработать [практика].

## 8. Database Mail

### 8.1. Настройка

От `sysadmin` [MS Learn — Configure Database Mail; Linux-пример с теми же процедурами]:

```sql
EXEC sp_configure 'show advanced options', 1;  RECONFIGURE;
EXEC sp_configure 'Database Mail XPs', 1;      RECONFIGURE;      -- умолчание 0; действует сразу
EXEC msdb.dbo.sysmail_add_account_sp
     @account_name    = N'SQL01 alerts',
     @email_address   = N'sql01@example.uz',
     @display_name    = N'SQL01',
     @replyto_address = N'dba@example.uz',
     @mailserver_name = N'smtp.example.uz',
     @port            = 587,                      -- умолчание 25
     @enable_ssl      = 1,                        -- умолчание 0
     @username        = N'sql01@example.uz',
     @password        = N'<пароль SMTP>';
EXEC msdb.dbo.sysmail_add_profile_sp        @profile_name = N'DBA', @description = N'Оповещения администраторов';
EXEC msdb.dbo.sysmail_add_profileaccount_sp @profile_name = N'DBA', @account_name = N'SQL01 alerts', @sequence_number = 1;
-- профиль по умолчанию для msdb: всем (public) или конкретному пользователю msdb
EXEC msdb.dbo.sysmail_add_principalprofile_sp @profile_name = N'DBA', @principal_name = N'public', @is_default = 1;
-- тест
EXEC msdb.dbo.sp_send_dbmail @profile_name = N'DBA', @recipients = N'dba@example.uz',
     @subject = N'Test Database Mail sql01', @body = N'Проверка';
```

- Отправлять почту могут члены роли `DatabaseMailUserRole` в `msdb` [MS Learn]; `public` как основной профиль — по примеру Microsoft для Linux; на общем экземпляре лучше назначить профиль конкретным пользователям `msdb` [практика].
- **Agent**: SSMS → SQL Server Agent → Properties → Alert System → Enable Mail Profile → Mail system «Database Mail» → профиль `DBA` → **перезапустить Agent** [MS Learn]. T‑SQL-аналог документацией не описан ⚠ (процедура `sp_set_sqlagent_properties` в справочнике отсутствует). На Linux — `mssql-conf set sqlagent.databasemailprofile DBA` [MS Learn].
- С SQL Server 2025 Database Mail поддерживает TDS 8.0 [MS Learn — TDS 8.0].
- Сам почтовый процесс внешний — `DatabaseMail.exe` в каталоге `\MSSQL\Binn`, запускается через активацию Service Broker, работает от учётной записи службы SQL Server, ошибки связи с экземпляром пишет в журнал приложений Windows (подтверждено 20.10.2026, MS Learn — «Database Mail external program»); при `Database Mail XPs = 0` он дорабатывает очередь до простоя (`DatabaseMailExeMinimumLifeTime`) [MS Learn].

### 8.2. Проверка и разбор

```sql
USE msdb;
SELECT TOP (20) mailitem_id, recipients, subject, sent_status, send_request_date, sent_date
FROM dbo.sysmail_allitems ORDER BY mailitem_id DESC;
SELECT TOP (20) log_date, event_type, mailitem_id, description
FROM dbo.sysmail_event_log ORDER BY log_date DESC;
-- неотправленные — с причиной
SELECT i.mailitem_id, i.subject, l.description
FROM dbo.sysmail_faileditems AS i JOIN dbo.sysmail_event_log AS l ON l.mailitem_id = i.mailitem_id;
```

Представления `sysmail_allitems`, `sysmail_faileditems`, `sysmail_event_log` — [MS Learn]. Типовые причины отказа — порт/TLS SMTP, учётные данные, блокировка relay на почтовом сервере [практика].

## 9. Журнал ошибок SQL Server и журнал Agent

### 9.1. Где лежит

- Windows: файл `ERRORLOG` в каталоге `…\MSSQL\Log` экземпляра; точный путь — параметр запуска `-e` в Configuration Manager (если не задан — из реестра) [MS Learn]. Архивы — `ERRORLOG.1`, `ERRORLOG.2`, …: при каждом старте текущий журнал переименовывается [MS Learn].
- Linux: `/var/opt/mssql/log` (`filelocation.errorlogfile`) [MS Learn].
- Журнал Agent читается той же `sp_readerrorlog` с `@p2 = 2`; ротация — `sp_cycle_agent_errorlog` [MS Learn]. Архивы журнала Agent при каждом старте переименовываются в `SQLAgent.1`, `SQLAgent.2`, … [MS Learn — `sp_cycle_agent_errorlog`]; хранится до девяти архивов (`.1` — самый новый, `.9` — самый старый) [MS Learn — «SQL Server Agent Error Log»]; имя текущего файла (`SQLAGENT.OUT`) — ⚠ (по практике).

### 9.2. Чтение

```sql
EXEC sp_readerrorlog;                                   -- текущий журнал SQL Server
EXEC sp_readerrorlog 1, 1;                              -- предыдущий (ERRORLOG.1)
EXEC sp_readerrorlog 0, 1, N'Login failed', N'buh_1c';  -- фильтр: обе строки должны встретиться
EXEC sp_readerrorlog 0, 2;                              -- текущий журнал Agent
```

- Параметры: `@p1` — номер файла (0 — текущий), `@p2` — `1` SQL Server / `2` Agent, `@p3`, `@p4` — строки фильтра (`nvarchar(4000)`) [MS Learn].
- Права: до 2019 — `securityadmin` или `VIEW SERVER STATE`; с 2022 — ещё `VIEW ANY ERROR LOG` [MS Learn]. `xp_readerrorlog` — недокументированная ⚠, в сценариях используйте `sp_readerrorlog`.
- SSMS: Object Explorer → Management → SQL Server Logs → View → SQL Server Log [MS Learn]. PowerShell: `Get-SqlErrorLog -ServerInstance sql01 -Since Midnight` [MS Learn]; dbatools — `Get-DbaErrorLog -SqlInstance sql01 -Text '*18456*'` [сторонний].

### 9.3. Ротация и число файлов

- `EXEC sp_cycle_errorlog;` — закрыть текущий журнал и начать новый без перезапуска; только `sysadmin` [MS Learn]. Ежедневная ротация заданием Agent удобна для разбора [практика].
- Архивов по умолчанию **6** (не считая текущего); число — SSMS → SQL Server Logs → Configure («Limit the number of the error log files…»), там же «Maximum size for error log file in KB» (`0` — без ограничения) [MS Learn]; PowerShell — `Set-SqlErrorLog -ServerInstance sql01 -MaxLogCount 30 -ErrorLogSizeKb 102400`, допустимо 6–99 [MS Learn]. Linux — `mssql-conf set errorlog.numerrorlogs <N>` [MS Learn].

### 9.4. Что искать в журнале на сервере баз 1С

| Строка/ошибка | Смысл | Что делать |
|---|---|---|
| `Error: 18456, Severity: 14, State: N` + `Login failed for user '…'` | неудачный вход; причина — в `State` [MS Learn] | 8 — неверный пароль (после смены пароля не обновили регистрацию ИБ, 3.7); 5/2 — нет такого логина (перенос, 4.5); 7 — логин отключён и пароль неверен; 18 — пароль нужно сменить (`MUST_CHANGE`); 38/46 — нет запрошенной базы или доступа к ней (владелец после восстановления, 4.2); 58 — вход SQL при режиме «только Windows» (3.3) или несовпадение SID; 11/12 — логин есть, доступ к серверу не дан |
| `Error: 17810` | DAC уже занят [MS Learn] | раздел 10 |
| `Error: 823/824/825` | ошибки ввода-вывода и целостности страниц [MS Learn] | оповещения 7.6, `DBCC CHECKDB` (`mssql/05`), диски |
| `Error: 9002` | журнал транзакций полон [MS Learn] | `log_reuse_wait_desc` (`mssql/04`) |
| `Error: 1105` | нет места в файловой группе [MS Learn] | рост и место на диске (11.2) |
| `A self-generated certificate was successfully loaded for encryption` | нет доверенного сертификата, используется самоподписанный [MS Learn] | раздел 12.1 |
| `Database Instant File Initialization: enabled.` / `…: disabled.` | включена ли IFI (с 2012 SP4, 2014 SP2, 2016) [MS Learn] | `mssql/02` |
| строка с портом DAC | на каком порту слушает DAC [MS Learn] | раздел 10 |
| `Server is listening on [ … <ipv4> 1433]` | адреса и порт экземпляра [практика] | сеть, брандмауэр |

Отказ входа видит и 1С: текст ошибки СУБД попадает в сообщение пользователю и в техжурнал (событие `EXCP`, `DBMSSQL`) — `../1c/07`. Запись неудачных входов в журнал ошибок управляется настройкой «Login auditing» в свойствах сервера (Security): None, Failed logins only, Successful logins only, Both failed and successful logins; изменение вступает в силу после перезапуска службы [MS Learn — SSMS, «Server Properties (Security Page)», уточнено 20.10.2026]. Умолчание «Failed logins only» ⚠ — на этой странице умолчание не указано. Для полного аудита входов используйте SQL Server Audit (12.4).

## 10. Выделенное административное подключение (DAC)

- **Назначение**: зарезервированные ресурсы для входа администратора, когда обычные подключения не проходят (зависание, исчерпание рабочих потоков) [MS Learn; ИТС-мет 6008, 2023]. Входить могут только члены `sysadmin` [MS Learn].
- **По умолчанию — только локально** с самого сервера; по сети — после `remote admin connections` = 1 (умолчание `0`), действует без перезапуска [MS Learn]. На FCI DAC по умолчанию выключен — включать заранее: если экземпляр уже не отвечает, а DAC по сети не разрешён, может понадобиться перезапуск [MS Learn]. Включить на каждом экземпляре сразу после установки [ИТС-мет 5904, 2019]:

```sql
EXEC sp_configure 'remote admin connections', 1;  RECONFIGURE;
SELECT name, value_in_use FROM sys.configurations WHERE name = N'remote admin connections';   -- 1
```

- **Порт**: TCP 1434, если свободен, иначе динамический при старте; номер — в журнале ошибок [MS Learn]. Брандмауэр: открыть 1434 (или фактический порт) только с машин администраторов [практика]. Express слушает DAC только с флагом трассировки 7806 [MS Learn].
- **Подключение** [MS Learn]:
  - `sqlcmd -S sql01 -E -A -d master` (или `-S admin:sql01`; именованный — `admin:sql01\ERP`); если DAC только локальный — `sqlcmd -S 127.0.0.1,1434`;
  - SSMS — отдельный экземпляр SSMS, выключить IntelliSense (Tools → Options → Languages → Transact-SQL → IntelliSense), File → New → Database Engine Query, сервер `admin:sql01`. Через Object Explorer DAC не открывать — он и IntelliSense занимают второе соединение, а DAC одно.
  - Проверка, что вы в DAC: `SELECT e.name, e.is_admin_endpoint FROM sys.dm_exec_sessions AS s JOIN sys.endpoints AS e ON e.endpoint_id = s.endpoint_id WHERE s.session_id = @@SPID;` — у DAC `is_admin_endpoint = 1` [колонки — MS Learn, `sys.dm_exec_sessions`, `sys.endpoints`; запрос — практика]. Проверка по группе рабочей нагрузки `DACGroup` описана Microsoft только для Azure SQL Database (уточнено 20.10.2026).
- **Ограничения** [MS Learn]: одно DAC-подключение на экземпляр (второе — ошибка 17810); нельзя параллельные запросы и команды (`BACKUP`/`RESTORE` → ошибка 3637); ресурсов мало — только диагностика: DMV (`sys.dm_exec_requests`, `sys.dm_tran_locks`, `sys.dm_os_tasks`), каталог, лёгкие `DBCC` (`FREEPROCCACHE`, `SQLPERF`), `KILL`. Тяжёлое (`DBCC CHECKDB`) не запускать; блокирующие запросы — под `READ UNCOMMITTED` и коротким `LOCK_TIMEOUT`. Если база по умолчанию у логина недоступна — ошибка 4060, поэтому `-d master`.
- **Типовое применение на сервере 1С** (запросы — `mssql/06`): найти виновника блокировки или «зависания», затем `KILL <session_id>;` и `KILL <session_id> WITH STATUSONLY;` — отчёт о ходе отката [MS Learn]. `KILL` требует `ALTER ANY CONNECTION` (`sysadmin`, `processadmin`) [MS Learn]. ⚠ Принудительное завершение сеанса 1С откатывает его транзакцию; связать `session_id` с сеансом 1С — поле «Соединение с СУБД» в консоли кластера [ИТС-КС разд. 5.2.12]. Разрыв соединения пользователя, активно работающего с ИБ, может привести к потере данных [ИТС-КС разд. 5.2.12.3] — по возможности сначала «Удалить» сеанс из консоли кластера.

## 11. Файлы баз: размер, рост, сжатие, перенос, владелец

### 11.1. Устройство и обзор

- Файлы: первичный файл данных (`.mdf`), вторичные (`.ndf`), журнал транзакций (`.ldf`); у базы минимум один файл данных и один журнал [MS Learn]. По умолчанию данные и журнал создаются на одном диске — для рабочей среды Microsoft рекомендует разные диски [MS Learn]; 1С — разные массивы, журналу нужен отклик 1–5 мс, данным — 10–20 мс [ИТС-мет 5904, 2019].
- Каталоги по умолчанию: `SERVERPROPERTY('InstanceDefaultDataPath')`, `…('InstanceDefaultLogPath')`, с 2019 — `…('InstanceDefaultBackupPath')` [MS Learn]. Задаются в свойствах сервера → Database Settings (`mssql/02`).
- 1С допускает на MS SQL менять положение файла базы и журнала, проверку целостности, реиндексацию, дефрагментацию, реорганизацию, копирование, очистку процедурного кеша, сбор статистики — это не нарушает работу прикладного решения и реструктуризацию [ИТС-КС разд. 5.5.1, 5.5.6–5.5.8]. Табличные пространства (файловые группы) для MS SQL — только через механизм КОРП [ИТС-КС разд. 5.5.5.2]; вручную переносить таблицы 1С в другие файловые группы не стоит — схемой управляет платформа [практика].

Размер и заполнение файлов текущей базы [MS Learn — `FILEPROPERTY`, «Manage the size of the transaction log file»]:

```sql
USE buh;
SELECT name, type_desc, physical_name,
       size / 128.0                                            AS size_mb,
       CAST(FILEPROPERTY(name, 'SpaceUsed') AS int) / 128.0    AS used_mb,
       size / 128.0 - CAST(FILEPROPERTY(name, 'SpaceUsed') AS int) / 128.0 AS free_mb,
       CASE WHEN is_percent_growth = 1 THEN CONCAT(growth, ' %') ELSE CONCAT(growth / 128, ' MB') END AS growth,
       max_size
FROM sys.database_files;
SELECT * FROM sys.dm_db_log_space_usage;                       -- журнал: всего/занято
```

`size` и `growth` — в страницах по 8 КБ (поэтому `/128` = МБ); `max_size`: `-1` — растёт до заполнения диска, `0` — рост запрещён, `268435456` — журнал до 2 ТБ [MS Learn]. По всем базам — `sys.master_files` [MS Learn] или `Get-DbaDbFile -SqlInstance sql01` [сторонний].

### 11.2. Рост файлов

- Автоприрост: шаг фиксированный в МБ, не в процентах [MS Learn — «Manage the size of the transaction log file»]; 1С — прирост 512 МБ, начальный размер данных — ожидаемый за длительный срок, журнал — чтобы не расти между `BACKUP LOG` [ИТС-мет 5904, 2019]. Умолчания установки (64 МБ) и `model` — `mssql/02`.
- **IFI** (Instant File Initialization) — рост файлов данных без обнуления; включается правом `SE_MANAGE_VOLUME_NAME` («Perform volume maintenance tasks») у службы (лучше у её SID) или ключом установки `/SQLSVCINSTANTFILEINIT` [MS Learn]. Журнал до 2022 всегда обнулялся; **с SQL Server 2022 (все редакции) автоприрост журнала до 64 МБ идёт мгновенно**, в том числе при TDE и без права `SE_MANAGE_VOLUME_NAME`; приросты журнала больше 64 МБ по-прежнему обнуляются [MS Learn]. Значит, при шаге журнала 512 МБ (совет 1С выше) мгновенного роста журнала нет — тем важнее заранее задать журналу размер (уточнено 20.10.2026). При TDE IFI для файлов данных не работает [MS Learn]. Проверка — `SELECT servicename, instant_file_initialization_enabled FROM sys.dm_server_services;` [MS Learn].
- `MAXSIZE` для баз 1С обычно не задают (`UNLIMITED`): упор в лимит остановит работу ИБ ошибкой 1105 [практика]; следить надо за свободным местом на дисках (`mssql/06`).

```sql
-- от sysadmin или владельца базы; логические имена — из запроса 11.1
ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh',     FILEGROWTH = 512MB);
ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh_log', FILEGROWTH = 512MB);
ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh',     SIZE = 200GB);        -- заранее увеличить (только вверх)
```

Синтаксис `MODIFY FILE (NAME, SIZE, FILEGROWTH, MAXSIZE, FILENAME)` — [MS Learn — `ALTER DATABASE` File and Filegroup options]. dbatools: `Set-DbaDbFileGrowth -SqlInstance sql01 -Database buh -GrowthType MB -Growth 512` [сторонний].

### 11.3. Сжатие (SHRINK): почему вредно и когда допустимо

**Почему вредно** [MS Learn — `DBCC SHRINKFILE`, «Shrink a database», «Manage the size of the transaction log file»]:

- сжатие **не является регламентной операцией**: файлы, растущие от обычной работы, сжимать не нужно; если после сжатия файл снова растёт — место нужно для работы, и повторное сжатие вредно (рост файла заново съедает ресурсы);
- перенос страниц из конца файла в начало **увеличивает фрагментацию индексов** — хуже большие просмотры; после сжатия нужно обслуживание индексов (`mssql/05`), которое снова займёт место;
- сжатие блокируется транзакциями под **версионными уровнями изоляции** — а 1С на MS SQL работает с RCSI (`mssql/08`), поэтому длинные транзакции 1С задерживают сжатие;
- нагружает дисковую подсистему, запускать — только в период низкой нагрузки;
- `AUTO_SHRINK` без особой причины не включать [MS Learn — `ALTER DATABASE SET`]; в планах обслуживания не использовать задачу «Shrink Database» [практика; ИТС-мет 5837, 2022 её не предусматривает].

**Когда допустимо** [MS Learn; практика]: после разового освобождения большого объёма — удаление данных (свёртка ИБ, очистка версий объектов, журнала регистрации в базе, хранилища двоичных данных в базе), удаление ИБ из общей базы-«мусорки», ошибочный рост журнала. Перед этим — полная копия (`mssql/04`).

**Как правильно** (от `sysadmin`/`db_owner`; ⚠ при `NOTRUNCATE`/`EMPTYFILE` и т. п. читать справочник):

```sql
USE buh;
-- 1) сколько реально свободно (11.1); 2) сначала только отрезать хвост без переноса страниц
DBCC SHRINKFILE (N'buh', TRUNCATEONLY);
-- 3) если мало — до целевого размера в МБ, ступенями, в тихое время
DBCC SHRINKFILE (N'buh', 180000);                                         -- target_size в МБ
-- SQL Server 2022+: не блокировать запросы 1С, при конфликте прервать сжатие
DBCC SHRINKFILE (N'buh', 180000) WITH WAIT_AT_LOW_PRIORITY (ABORT_AFTER_WAIT = SELF);
-- 4) затем обслуживание индексов (mssql/05)
```

- `target_size` — новый размер в МБ; `0` или без него — до размера при создании; `TRUNCATEONLY` возвращает ОС только свободное место в конце файла, ничего не перенося [MS Learn].
- `WAIT_AT_LOW_PRIORITY` — с SQL Server 2022; при невозможности получить блокировку — ошибка 49516; `ABORT_AFTER_WAIT = SELF | BLOCKERS` (`NONE` недопустим) [MS Learn]. `BLOCKERS` прерывает **чужие** сеансы — для 1С не использовать [практика].
- Для больших баз Microsoft предлагает сценарий ShrinkDriver (параллельно, с повторами) [MS Learn]; dbatools — `Invoke-DbaDbShrink` (есть `-StepSize`, `-WaitAtLowPriority`) [сторонний].

**Журнал транзакций**: журнал сжимается только до границы виртуального файла (VLF) и только если в конце есть неактивные VLF; частая причина «не сжимается» — нет регулярных `BACKUP LOG` в модели FULL или длинная транзакция [MS Learn]. Порядок: выяснить `log_reuse_wait_desc` → устранить причину (`BACKUP LOG`, завершить транзакцию) → `DBCC SHRINKFILE (N'buh_log', <МБ>)` → задать нормальный размер и шаг (11.2) [MS Learn; практика]. Совет ИТС 2008 года `BACKUP LOG … WITH TRUNCATE_ONLY` + `DBCC SHRINKFILE` [ИТС-мет 2373, 2008] **устарел**: опции `NO_LOG` и `TRUNCATE_ONLY` удалены из `BACKUP` [MS Learn]. Пример Microsoft с переводом базы в `SIMPLE` перед сжатием журнала **разрывает цепочку копий журнала** — после возврата в `FULL` сразу полная или разностная копия (`mssql/04`) [практика].

### 11.4. Перенос файлов в пределах экземпляра

Например, журнал — на отдельный диск `L:` [MS Learn — «Move user databases», плановый перенос]:

1. В 1С — блокировка начала сеансов и регламентных заданий, сеансы завершить (`../1c/03`, 6.5). Копия базы (`mssql/04`).
2. Учётной записи службы SQL Server (или её SID `NT SERVICE\MSSQLSERVER`) дать права на новый каталог [MS Learn].
3. Выполнить (от `sysadmin`):

```sql
USE master;
ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh_log', FILENAME = N'L:\MSSQL\Log\buh_log.ldf');
ALTER DATABASE [buh] SET OFFLINE WITH ROLLBACK IMMEDIATE;      -- ⚠ обрывает соединения
-- переместить файл средствами ОС (PowerShell от администратора):
--   Move-Item 'D:\MSSQL\Data\buh_log.ldf' 'L:\MSSQL\Log\buh_log.ldf'
ALTER DATABASE [buh] SET ONLINE;
SELECT name, physical_name, state_desc FROM sys.master_files WHERE database_id = DB_ID(N'buh');
```

4. Если база не перешла в `ONLINE` — проверить путь и права (журнал ошибок), исправить и повторить `SET ONLINE`.
5. Снять блокировку в 1С, проверить вход.

Вариант при плановой остановке экземпляра: `MODIFY FILE` → остановить службу → переместить файлы → запустить [MS Learn]. Перенос системных баз (`tempdb`, `master` и др.) — отдельная процедура (`mssql/02`) [MS Learn — «Move system databases»].

### 11.5. Перенос базы на другой экземпляр: backup/restore или detach/attach

| Критерий | Копия и восстановление | Отключение и подключение (detach/attach) |
|---|---|---|
| Исходная база во время операции | работает (копия `COPY_ONLY` не ломает цепочку копий) | **недоступна** с момента отключения |
| Целостность при переносе | `WITH CHECKSUM` при копии, `RESTORE VERIFYONLY` | контрольной суммы файлов нет; копировать нужно **все** файлы данных и журнал [MS Learn] |
| Если что-то пошло не так | исходная база не тронута | ошибки при отключении могут помешать чистому закрытию базы — подключать обратно все файлы [MS Learn] |
| Объём для передачи | копия, обычно сжатая (`COMPRESSION`, не в Express) | полный объём файлов, включая пустое место |
| На старшую версию SQL Server | да | да |
| На младшую версию | **нет** | **нет** — база новой версии не подключается к старой [MS Learn] |
| Метаданные после переноса | владелец = восстанавливавший [MS Learn]; логины, задания Agent — отдельно | при подключении сбрасываются `TRUSTWORTHY`, Service Broker, межбазовые цепочки владения [MS Learn]; логины, задания — отдельно |
| Когда разумно | **по умолчанию для баз 1С** [практика] | быстрый перенос больших файлов в пределах одного хранилища, когда простой допустим |

Копия и восстановление — `mssql/04`. Detach/attach (⚠ база недоступна; предварительно копия; сеансы 1С закрыты; от `sysadmin`) [MS Learn — `sp_detach_db`, `CREATE DATABASE … FOR ATTACH`]:

```sql
USE master;
ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
EXEC sp_detach_db @dbname = N'buh', @skipchecks = N'true';    -- 'true' = не выполнять UPDATE STATISTICS
-- скопировать buh.mdf и buh_log.ldf на новый сервер; на новом сервере:
CREATE DATABASE [buh]
    ON (FILENAME = N'D:\MSSQL\Data\buh.mdf'),
       (FILENAME = N'L:\MSSQL\Log\buh_log.ldf')
FOR ATTACH;
ALTER DATABASE [buh] SET MULTI_USER;
```

- Перед `SET SINGLE_USER` выключить `AUTO_UPDATE_STATISTICS_ASYNC` (у баз 1С он обычно включён [ИТС-мет 5904, 2019]), иначе фоновый поток статистики может занять единственное подключение [MS Learn — `sp_detach_db`]; после подключения на новом сервере вернуть `ON`.
- `sp_attach_db` устарела — вместо неё `CREATE DATABASE … FOR ATTACH`; при `FOR ATTACH` сортировку указать нельзя [MS Learn]. `FOR ATTACH_REBUILD_LOG` пересоздаёт отсутствующий журнал только после чистого закрытия и разрывает цепочку копий журнала [MS Learn] — для баз 1С крайний случай.
- Нельзя отключить базу, если у неё есть снимки, она в группе доступности или в зеркалировании; подозрительную (`SUSPECT`) — только через `EMERGENCY` [MS Learn].
- Не подключайте и не восстанавливайте базы из неизвестных источников без `DBCC CHECKDB` на нерабочем сервере [MS Learn].
- После переноса любым способом — раздел 4.6 (логины с SID, владелец, `processadmin`, регистрация в кластере). dbatools делает всё сразу: `Copy-DbaDatabase -Source sql01 -Destination sql02 -Database buh -BackupRestore -SharedPath \\fs01\sqlmove` (копии `COPY_ONLY`; вариант `-DetachAttach`) [сторонний] — владельца базы 1С после него всё равно проверить (3.8).

### 11.6. Смена владельца базы

- Владелец базы 1С — **логин ИБ** (сценарии 3.5, 3.6): так он получает права `dbo`, которых требует платформа [ИТС-адм разд. 5.2.1.3.2]. Распространённый совет «сделать владельцем всех баз `sa`» [сторонний — `Set-DbaDbOwner` по умолчанию] **к базам 1С неприменим** без перевода логина 1С в `db_owner`, а такой вариант ИТС не описывает ⚠.
- Команда (от `sysadmin` или с `TAKE OWNERSHIP` на базу и `IMPERSONATE` на логин) [MS Learn]: `ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];`. `sp_changedbowner` устарела [MS Learn].
- Новый владелец не может уже иметь доступ к базе через пользователя — сначала удалить этого пользователя [MS Learn — `sp_changedbowner`]; системным базам `master`, `model`, `tempdb` владельца не меняют [MS Learn].
- Владельцем может быть логин SQL Server или логин Windows-пользователя (не группы) [MS Learn].
- Проверка — запрос 3.8; список «чужих» владельцев — `SELECT name, SUSER_SNAME(owner_sid) FROM sys.databases WHERE database_id > 4;` [практика].

## 12. Безопасность

### 12.1. Шифрование соединений (TLS)

**Как устроено** [MS Learn]:

- Пакеты входа (учётные данные) **шифруются всегда**; если доверенного сертификата нет, SQL Server при старте создаёт самоподписанный (в журнале: «A self-generated certificate was successfully loaded for encryption»), который защищает пароль, но не от подмены сервера. Шифрование данных — по требованию клиента или принудительно сервером (Force Encryption).
- Сертификат: в хранилище компьютера (или учётной записи службы); срок действия; EKU «Server Authentication (1.3.6.1.5.5.7.3.1)»; ключ с `KeySpec = AT_KEYEXCHANGE` (устаревший CSP); в SAN — все имена, по которым подключаются (`sql01`, `sql01.corp.local`, псевдонимы); у учётной записи службы — право чтения закрытого ключа. Если сертификат выбран, но требованиям отвечает не полностью, **SQL Server не стартует**.
- Порядок выбора сертификата: заданный в Configuration Manager (реестр `…\MSSQLServer\SuperSocketNetLib\Certificate`) → сертификат с FQDN машины в хранилище, к ключу которого у службы есть доступ (даже если не выбран!) → самоподписанный. С 2022 CU22 и в 2025 регистр отпечатка в реестре не важен.

**Порядок для сервера баз 1С** [MS Learn; выбор — практика]:

1. Выпустить сертификат на доменном УЦ (корневой сертификат УЦ доверен на рабочих серверах 1С и машинах администраторов) с SAN `sql01`, `sql01.corp.local`. Для стенда — самоподписанный командлетом `New-SelfSignedCertificate` по шаблону Microsoft (`-Type SSLServerAuthentication`, `-KeySpec KeyExchange`, `-Provider "Microsoft RSA SChannel Cryptographic Provider"`, `-TextExtension "2.5.29.37={text}1.3.6.1.5.5.7.3.1"`, `-CertStoreLocation cert:\LocalMachine\My`) — тогда его нужно сделать доверенным на клиентах [MS Learn].
2. Configuration Manager (2019+, годится и для экземпляров 2008 и новее) → Protocols for `<экземпляр>` → Certificate → Import / выбрать сертификат: утилита проверяет требования, импортирует сертификат и настраивает экземпляр на него [MS Learn]. Право учётной записи службы на чтение закрытого ключа проверить отдельно («All Tasks → Manage Private Keys» в оснастке сертификатов) — без него служба может не стартовать [MS Learn]; выдаёт ли его Configuration Manager сам, документация прямо не говорит (уточнено 20.10.2026).
3. Flags → **Force Encryption = Yes**; **Force Strict Encryption — не включать** для 1С ⚠ (TDS 8.0 требует от клиента `Encrypt=Strict`; поддержку этого платформой ИТС не описывает).
4. Перезапустить службу SQL Server (и Agent).
5. Проверить:

```sql
SELECT c.session_id, c.net_transport, c.encrypt_option, c.auth_scheme, c.protocol_version,
       s.login_name, s.program_name, s.host_name
FROM sys.dm_exec_connections AS c JOIN sys.dm_exec_sessions AS s ON s.session_id = c.session_id
WHERE c.net_transport <> N'Shared memory';                      -- encrypt_option = TRUE у всех
```

Колонки `encrypt_option`, `auth_scheme`, `net_transport`, `protocol_version` — [MS Learn]; dbatools — `Get-DbaNetworkEncryption -SqlInstance sql01` [сторонний].

**Клиенты 1С и драйверы** [MS Learn — «Encryption and certificate validation in OLE DB»]:

- **OLE DB Driver 18** (устаревшие методы входа): по умолчанию `Encrypt=no` — шифруются только пакеты входа; при `Encrypt=yes` без `TrustServerCertificate` — только с проверяемым сертификатом; клиентская настройка реестра Force Protocol Encryption = 1 вместе с Trust Server Certificate = 1 — шифровать всегда, даже с самоподписанным.
- **OLE DB Driver 19**: по умолчанию `Encrypt=Mandatory` (у драйвера 19 значения `Optional`/`Mandatory`/`Strict`), сертификат проверяется: **без доверенного сертификата на SQL Server соединение не установится**, если в строке подключения не задано `TrustServerCertificate=Yes`; реестровая Force Protocol Encryption = 2 — всегда Strict. TLS 1.3 — с 19.2 только через TDS 8.0.
- Какой провайдер выбрала платформа — техжурнал `DBMSSQLCONN` (`../1c-windows/02`, 3.5); в 8.5.1 у события появились свойства `hResultMSOLEDBSQL19` и `hResultMSOLEDBSQL` [`otlichiya-8.5.1`, п. 16] — значит, 8.5.1 умеет работать через драйвер 19 ⚠ (вывод из имени свойства). **Практический вывод**: при драйвере 19 на рабочих серверах 1С — обязателен доверенный сертификат на SQL Server [практика]. Как платформа передаёт `Encrypt`/`TrustServerCertificate`, ИТС не пишет ⚠.
- При Force Encryption на сервере и SQL Server 2025: если в ОС оставлен только TLS 1.3, клиенты TDS 7.x (`Mandatory`/`Optional`) и даже Agent не подключатся — оставлять TLS 1.2 включённым, пока клиенты 1С не поддерживают Strict [MS Learn — TDS 8.0].
- **Инструменты администратора** (SSMS 20+, `sqlcmd` из 2025, `Invoke-Sqlcmd` модуля 22+, dbatools 2.x) по умолчанию требуют шифрования с проверкой сертификата — доверенный сертификат снимает необходимость ключей `-C`/`-TrustServerCertificate` [MS Learn; сторонний].

**SQL Server на Linux** [MS Learn]: `sudo /opt/mssql/bin/mssql-conf set network.tlscert /etc/ssl/certs/mssql.pem`, `… set network.tlskey /etc/ssl/private/mssql.key`, `… set network.forceencryption 1`; для 2022 и старше также `network.tlsprotocols 1.2`; затем `systemctl restart mssql-server`.

### 12.2. Kerberos для входов Windows

- Если 1С (аутентификация ОС) или администраторы входят учётными записями Windows, по сети желательно Kerberos; без SPN — откат на NTLM [MS Learn]. Проверка: `SELECT auth_scheme FROM sys.dm_exec_connections WHERE session_id = @@SPID;` → `KERBEROS` [MS Learn].
- SPN: `MSSQLSvc/<FQDN>:<порт>` для TCP (экземпляр по умолчанию — ещё `MSSQLSvc/<FQDN>`, именованный — `MSSQLSvc/<FQDN>:<экземпляр>`). Регистрируется автоматически при старте, если служба работает под встроенной учётной записью или у учётной записи есть право записи SPN; иначе вручную (доменный администратор) [MS Learn]:

```bat
setspn -S MSSQLSvc/sql01.corp.local:1433 CORP\svc-sql01
setspn -S MSSQLSvc/sql01.corp.local CORP\svc-sql01
setspn -L CORP\svc-sql01
```

`-S` — регистрация SPN (примеры Microsoft) [MS Learn]; что `-S` предварительно ищет дубликаты, а `-L` выводит SPN учётной записи, — справка `setspn` [практика]. Учётная запись `CORP\svc-sql01` — доменная учётная запись службы SQL Server (условное имя).

### 12.3. TDE (прозрачное шифрование данных) — применимость к 1С

- **Что защищает** [MS Learn]: файлы данных и журнала «на диске» и копии базы — от кражи носителей. **Не** шифрует сетевой трафик (12.1) и не скрывает данные от пользователей с доступом к базе. Размер базы не растёт.
- **1С**: шифрование на уровне СУБД для Microsoft SQL Server 2008 и новее входит в перечень допустимых административных действий [ИТС-КС разд. 5.5.2] — прикладное решение и реструктуризация работают.
- **Редакции** [MS Learn]: 2017 — только Enterprise; **2019, 2022, 2025 — Enterprise и Standard**; Express — нет.
- **Последствия** [MS Learn]: `tempdb` шифруется автоматически, если хоть одна база экземпляра под TDE, — это может замедлить и незашифрованные базы на том же экземпляре; IFI для файлов данных перестаёт работать (журнал до 64 МБ в 2022+ — работает); пока идёт сканирование шифрования, обслуживание базы недоступно; системные базы `master`, `model`, `msdb` не шифруются.
- **Главный риск** [MS Learn]: без резервной копии сертификата и закрытого ключа базу **нельзя** восстановить или подключить на другом сервере. Сертификат хранить даже после отключения TDE (часть журнала может оставаться зашифрованной). Просроченный сертификат TDE продолжает работать.

Включение (от `sysadmin`; ⚠ на рабочей базе запускает фоновое сканирование всех страниц — в окно низкой нагрузки; копии сертификата — вне сервера) [MS Learn]:

```sql
USE master;
CREATE MASTER KEY ENCRYPTION BY PASSWORD = N'<пароль DMK>';
CREATE CERTIFICATE TDE_sql01 WITH SUBJECT = N'TDE certificate sql01';
BACKUP CERTIFICATE TDE_sql01 TO FILE = N'E:\Keys\TDE_sql01.cer'
    WITH PRIVATE KEY (FILE = N'E:\Keys\TDE_sql01.pvk', ENCRYPTION BY PASSWORD = N'<пароль ключа>');
USE buh;
CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256 ENCRYPTION BY SERVER CERTIFICATE TDE_sql01;
ALTER DATABASE [buh] SET ENCRYPTION ON;
-- ход и состояние
SELECT DB_NAME(database_id) AS db, encryption_state, encryption_state_desc, percent_complete,
       encryption_scan_state_desc
FROM sys.dm_database_encryption_keys;      -- encryption_state 3 = Encrypted; *_desc — с 2019
-- 2019+: приостановить/продолжить сканирование в часы нагрузки
ALTER DATABASE [buh] SET ENCRYPTION SUSPEND;
ALTER DATABASE [buh] SET ENCRYPTION RESUME;
```

На другом сервере перед восстановлением: `CREATE MASTER KEY …; CREATE CERTIFICATE TDE_sql01 FROM FILE = N'…\TDE_sql01.cer' WITH PRIVATE KEY (FILE = N'…\TDE_sql01.pvk', DECRYPTION BY PASSWORD = N'<пароль ключа>');` [MS Learn]. Копии сертификата — в план копий (`mssql/04`).

**Оценка для 1С** [практика]: TDE оправдано, если требование защиты носителей/копий формальное (ПДн, регулятор) — тогда Standard 2019+; если цель — только защитить копии, проще шифрование копий (`BACKUP … WITH ENCRYPTION`, Enterprise/Standard; `mssql/04`). На общем экземпляре TDE одной базы замедляет `tempdb` для всех баз 1С.

### 12.4. Аудит SQL Server

- **SQL Server Audit**: объект «аудит» (куда писать: `FILE`, `APPLICATION_LOG`, `SECURITY_LOG`) + спецификации аудита сервера и баз (какие группы действий) [MS Learn]. Аудит сервера и базы есть во всех редакциях 2022 и 2025, включая Express [MS Learn — редакции].
- Параметры `CREATE SERVER AUDIT` [MS Learn]: `FILEPATH`, `MAXSIZE` (от 2 МБ), `MAX_ROLLOVER_FILES` (умолч. `UNLIMITED`) или `MAX_FILES`, `RESERVE_DISK_SPACE`; `QUEUE_DELAY` (мс, минимум и умолчание 1000, `0` — синхронно); `ON_FAILURE = CONTINUE | SHUTDOWN | FAIL_OPERATION` (умолч. `CONTINUE`). В SQL Server 2019 и раньше в имени аудита нельзя пробелы.
- Для экземпляра 1С имеет смысл аудит **безопасности**, а не данных [практика]: аудит изменений строк таблиц 1С даст огромный объём и нагрузку; аудит действий пользователей 1С — журнал регистрации и аудит прав доступа КОРП [ИТС-КС прил. 3, разд. 3.10].

```sql
USE master;
CREATE SERVER AUDIT [Audit_Security]
    TO FILE (FILEPATH = N'E:\Audit\', MAXSIZE = 256 MB, MAX_ROLLOVER_FILES = 40)
    WITH (QUEUE_DELAY = 1000, ON_FAILURE = CONTINUE);
CREATE SERVER AUDIT SPECIFICATION [AuditSpec_Security]
    FOR SERVER AUDIT [Audit_Security]
    ADD (FAILED_LOGIN_GROUP),
    ADD (SERVER_ROLE_MEMBER_CHANGE_GROUP),
    ADD (SERVER_PRINCIPAL_CHANGE_GROUP),
    ADD (LOGIN_CHANGE_PASSWORD_GROUP),
    ADD (SERVER_PERMISSION_CHANGE_GROUP),
    ADD (DATABASE_ROLE_MEMBER_CHANGE_GROUP),
    ADD (DATABASE_PRINCIPAL_CHANGE_GROUP),
    ADD (DATABASE_OWNERSHIP_CHANGE_GROUP),
    ADD (DATABASE_CHANGE_GROUP),
    ADD (BACKUP_RESTORE_GROUP),
    ADD (AUDIT_CHANGE_GROUP),
    ADD (SERVER_STATE_CHANGE_GROUP)
    WITH (STATE = ON);
ALTER SERVER AUDIT [Audit_Security] WITH (STATE = ON);
-- чтение
SELECT TOP (100) event_time, action_id, succeeded, server_principal_name, database_name,
       client_ip, application_name, LEFT(statement, 200) AS stmt          -- client_ip, application_name — с 2017
FROM sys.fn_get_audit_file(N'E:\Audit\*.sqlaudit', DEFAULT, DEFAULT)
ORDER BY event_time DESC;
```

- Имена групп действий — [MS Learn, «SQL Server Audit action groups and actions»]; `SUCCESSFUL_LOGIN_GROUP` на сервере 1С даёт очень много событий (каждое соединение `rphost`) — добавлять осознанно [практика]. Файлы аудита имеют расширение `.sqlaudit` [MS Learn — `sys.fn_get_audit_file`].
- Каталог `E:\Audit\` должен существовать, у службы — права записи [практика]. Запись в журнал безопасности Windows (`SECURITY_LOG`) требует отдельной настройки Windows [MS Learn].
- Устаревшие механизмы `c2 audit mode` и `common criteria compliance enabled` (умолчания `0`) — не включать без требования регулятора [MS Learn — значения; практика]; `default trace enabled` (умолчание `1`) оставить — по нему разбирают автоприросты файлов и изменения объектов (`mssql/06`) [MS Learn; практика].

### 12.5. Минимальные права и поверхность атаки: чек-лист

| Пункт | Как проверить | Источник |
|---|---|---|
| Свой логин SQL на каждую ИБ, имя = имени ИБ | `SELECT name, SUSER_SNAME(owner_sid) FROM sys.databases;` | [ИТС-КС прил. 3, разд. 3.7; ИТС-мет 5899] |
| У логинов ИБ нет `sysadmin`, `dbcreator` снят после создания | запрос 3.4 по всем логинам | [ИТС-мет 2926; практика] |
| Администраторы — доменная группа в `sysadmin`, личных SQL-логинов нет | `SELECT m.name, m.type_desc FROM sys.server_role_members AS r JOIN sys.server_principals AS rp ON rp.principal_id = r.role_principal_id JOIN sys.server_principals AS m ON m.principal_id = r.member_principal_id WHERE rp.name = N'sysadmin';` | [MS Learn; практика] |
| `sa` отключён или переименован (12.6) | `SELECT name, is_disabled FROM sys.server_principals WHERE sid = 0x01;` | [MS Learn; практика] |
| Службы — виртуальные учётные записи/gMSA, не администраторы | Configuration Manager; `SELECT servicename, service_account FROM sys.dm_server_services;` | [MS Learn] |
| `xp_cmdshell`, `Ole Automation Procedures`, `clr enabled`, `cross db ownership chaining`, `Ad Hoc Distributed Queries`, `contained database authentication` = 0 (умолчания) | `SELECT name, value_in_use FROM sys.configurations WHERE name IN (N'xp_cmdshell', N'Ole Automation Procedures', N'clr enabled', N'cross db ownership chaining', N'Ad Hoc Distributed Queries', N'contained database authentication');` | [MS Learn — значения по умолчанию] |
| `remote admin connections` = 1 (DAC), порт DAC закрыт брандмауэром для всех, кроме администраторов | 10 | [MS Learn; ИТС-мет 5904] |
| TCP 1433 открыт только рабочим серверам 1С и администраторам | `Get-NetFirewallRule` | [ИТС-КС прил. 3, разд. 3.5; практика] |
| TLS с доверенным сертификатом, Force Encryption (12.1) | `encrypt_option` | [MS Learn] |
| Мониторинг — отдельный логин с `##MS_ServerStateReader##` / `VIEW SERVER STATE`, не `sysadmin` | — | [MS Learn] |
| Аудит безопасности включён (12.4) | `SELECT name, is_state_enabled FROM sys.server_audits;` | [MS Learn] |
| Файлы данных и журналов баз (`.mdf`, `.ndf`, `.ldf`) исключены из файлового резервного копирования; файлы баз и копий (`.bak`, `.trn`) — из проверки антивирусом. Сами копии файловым копированием, наоборот, уносить с сервера (`mssql/04`) | — | [ИТС-мет 5904, 2019 — исключать файлы данных и журналов]; антивирус — [MS Learn — статья поддержки «Antivirus and SQL Server»], `../1c-windows/06` |
| На экземпляре только базы 1С; сервисы (Redmine, NetBox и т. п.) — в своём PostgreSQL | — | [практика; решение пользователя] |

Регулярная проверка конфигурации — `Invoke-SqlAssessment` [MS Learn] или `sp_Blitz` [сторонний] (`mssql/06`).

### 12.6. Отключение или переименование `sa`

- `sa` — общеизвестная учётная запись, частая цель атак; не включать без необходимости приложения, пароль — сложный [MS Learn]. При установке в режиме «только Windows» `sa` отключён и сохраняется отключённым после перехода в смешанный режим [MS Learn].
- **Перед отключением** — убедиться, что ни одна ИБ не работает под `sa` (ИТС допускает `sa` как пользователя базы [ИТС-адм разд. 5.2.1.3.2]) [практика]:

```sql
SELECT DISTINCT s.login_name, s.host_name, s.program_name, DB_NAME(s.database_id) AS db
FROM sys.dm_exec_sessions AS s WHERE s.login_name = N'sa';
```

и в 1С по каждой ИБ — «Пользователь базы данных» в свойствах (консоль или `rac infobase info … | grep db-user`).

```sql
ALTER LOGIN sa DISABLE;                          -- [MS Learn]
-- или переименовать (SID 0x01 и principal_id 1 сохраняются)
ALTER LOGIN sa WITH NAME = [sql01_sa_disabled];  -- [MS Learn — ALTER LOGIN … NAME]
SELECT principal_id, name, is_disabled FROM sys.server_principals WHERE sid = 0x01;
```

- Задания Agent, владельцем которых был `sa`, после отключения — проверить запуском [практика] ⚠. dbatools после переименования `sa` сам находит его по SID (параметр `-SyncSaName` у `Copy-DbaLogin`, умолчания `Set-DbaDbOwner`) [сторонний].
- Включение обратно: `ALTER LOGIN sa ENABLE; ALTER LOGIN sa WITH PASSWORD = N'<пароль>';` [MS Learn].

## Типичные ошибки (симптом → причина → решение)

| # | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | SSMS 20+/Invoke-Sqlcmd/dbatools: «The certificate chain was issued by an authority that is not trusted» | клиент по умолчанию требует шифрования и проверяет сертификат, на SQL Server самоподписанный [MS Learn] | доверенный сертификат (12.1); временно — «Trust Server Certificate», `-C`, `-TrustServerCertificate`, `Set-DbatoolsInsecureConnection -SessionOnly` |
| 2 | После установки OLE DB Driver 19 на рабочий сервер 1С соединение с MS SQL не устанавливается | у драйвера 19 `Encrypt=Mandatory` и проверка сертификата по умолчанию [MS Learn] | доверенный сертификат на SQL Server; ⚠ для 8.3.x — драйвер 18 (`../1c-windows/02`, 3.5) |
| 3 | «Удалить» соединение в консоли кластера не прерывает долгий запрос | у логина ИБ нет `processadmin` [ИТС-КС разд. 5.2.12.3; ИТС-мет 1595] | `ALTER SERVER ROLE processadmin ADD MEMBER [buh_1c];` |
| 4 | После восстановления базы на другом сервере 1С не открывает ИБ; в журнале 18456 State 38/46 | владельцем стал восстанавливавший, логин ИБ — не `dbo` [MS Learn] | `ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];` (4.2) |
| 5 | `ALTER USER [buh_1c] WITH LOGIN = [buh_1c]` — «пользователь не существует» | логин ИБ — владелец, в базе он `dbo`, отдельного пользователя нет | см. п. 4 |
| 6 | `ALTER AUTHORIZATION` — логин уже пользователь базы | новый владелец не должен иметь пользователя в базе [MS Learn — `sp_changedbowner`] | проверить схемы пользователя, `DROP USER [buh_1c];`, повторить |
| 7 | После переноса логинов «Login failed», State 8 | логин пересоздан с другим паролем; или 5/2 — логина нет [MS Learn] | `sp_help_revlogin` / `Copy-DbaLogin` (4.5) |
| 8 | После смены пароля SQL все сеансы ИБ падают, логин заблокирован | регистрация ИБ со старым паролем + `CHECK_POLICY = ON` → блокировка по политике Windows [MS Learn] | порядок 3.7; `ALTER LOGIN … WITH PASSWORD = '…' UNLOCK;` |
| 9 | Через год ИБ перестала подключаться: «password expired» / State 18 | `CHECK_EXPIRATION = ON` (в том числе включился вместе с `CHECK_POLICY = ON` через `ALTER LOGIN`) [MS Learn] | `ALTER LOGIN [buh_1c] WITH CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;` + новый пароль по 3.7 |
| 10 | Создание ИБ из 1С: нет прав на создание базы | у логина нет `dbcreator`/`CREATE ANY DATABASE` [MS Learn] | временно `dbcreator` (3.5) или сценарий Б (3.6) |
| 11 | Аутентификация ОС: ИБ на удалённом SQL Server не подключается | `rphost` работает под локальным `USR1CV8`, удалённый SQL Server его не знает [практика] ⚠ | доменная учётная запись для `rphost` (`swpuser.ini`) или вход SQL Server |
| 12 | Вход SQL Server отвергается, State 58 | экземпляр в режиме «только Windows» [MS Learn] | SSMS → свойства сервера → Security → смешанный режим, перезапуск (3.3) |
| 13 | DAC: ошибка 17810 | DAC уже занят (часто — Object Explorer/IntelliSense в SSMS) [MS Learn] | закрыть лишнее подключение; «Новый запрос», IntelliSense выкл. |
| 14 | DAC по сети не подключается | `remote admin connections` = 0 или порт 1434 закрыт [MS Learn] | включить заранее (10); брандмауэр |
| 15 | `BACKUP` через DAC — ошибка 3637 | в DAC запрещены параллельные команды [MS Learn] | копии — обычным подключением |
| 16 | Узел SQL Server Agent в SSMS пуст | `Agent XPs` = 0, служба Agent не запущена [MS Learn] | запустить Agent, тип запуска «Автоматически»; при необходимости `sp_configure 'Agent XPs', 1` (после `show advanced options`, 7.1) |
| 17 | Оповещения и уведомления не приходят | у Agent не включён профиль Database Mail или Agent не перезапущен; событие не в журнале приложений [MS Learn] | 8.1; `sysmail_event_log`; ошибки ниже 19 — `WITH LOG` |
| 18 | SQL Server 2025: Agent не стартует после ужесточения TLS | в ОС только TLS 1.3, на экземпляре не включён Force Strict Encryption (только Force Encryption или ничего) [MS Learn] | вернуть TLS 1.2 или Force Strict Encryption (⚠ проверить клиентов 1С) |
| 19 | SQL Server не стартует после выбора сертификата | сертификат отвечает требованиям не полностью или у службы нет доступа к ключу [MS Learn] | убрать сертификат в Configuration Manager/реестре, исправить, повторить |
| 20 | После `SHRINK` выросла фрагментация, файл снова вырос | сжатие — не регламентная операция [MS Learn] | убрать сжатие из регламента; `AUTO_SHRINK OFF`; индексы (`mssql/05`) |
| 21 | Журнал не сжимается | нет `BACKUP LOG` / длинная транзакция [MS Learn] | `log_reuse_wait_desc`, устранить причину (11.3) |
| 22 | `BACKUP LOG … WITH TRUNCATE_ONLY` по методичке — ошибка | опция удалена [MS Learn] | 11.3 |
| 23 | После `Set-DbaDbOwner` 1С потеряла права на базу | по умолчанию владелец — `sa` [сторонний] | `ALTER AUTHORIZATION … TO [buh_1c]`; dbatools — только с `-TargetLogin` |
| 24 | После detach/attach базы на новом сервере — сироты, нет заданий, `TRUSTWORTHY` OFF | логины (`master`) и задания (`msdb`) с базой не переносятся; `TRUSTWORTHY`, Service Broker и межбазовые цепочки владения при подключении сбрасываются [MS Learn] | 4.6 |
| 25 | Потерян доступ `sysadmin` | все администраторы удалены, `sa` отключён [MS Learn] | 3.10 (`/f /mSQLCMD`) |

## Быстрая шпаргалка — задача → команда

| Задача | Команда / где |
|---|---|
| Версия, редакция, режим входа | `SELECT SERVERPROPERTY('ProductVersion'), SERVERPROPERTY('Edition'), SERVERPROPERTY('IsIntegratedSecurityOnly');` |
| Службы, их учётные записи, IFI | `SELECT servicename, service_account, startup_type_desc, status_desc, instant_file_initialization_enabled FROM sys.dm_server_services;` |
| Открыть Configuration Manager 2022/2025 | `SQLServerManager16.msc` / `SQLServerManager17.msc` |
| Вход `sqlcmd` (доменная учётная запись) | `sqlcmd -S sql01 -E -C -Q "SELECT @@VERSION"` (`-C` — пока нет доверенного сертификата) |
| Модуль PowerShell | `Install-Module SqlServer`; `Invoke-Sqlcmd -ServerInstance sql01 -Query "…" -TrustServerCertificate` |
| Логин для ИБ | `CREATE LOGIN [buh_1c] WITH PASSWORD = N'…', CHECK_POLICY = ON, CHECK_EXPIRATION = OFF; ALTER SERVER ROLE processadmin ADD MEMBER [buh_1c];` |
| Права логина | `SELECT IS_SRVROLEMEMBER('processadmin', N'buh_1c'), IS_SRVROLEMEMBER('sysadmin', N'buh_1c');` |
| Снять `dbcreator` после создания ИБ | `ALTER SERVER ROLE dbcreator DROP MEMBER [buh_1c];` |
| Владелец базы | `SELECT name, SUSER_SNAME(owner_sid) FROM sys.databases;` |
| Сделать логин ИБ владельцем | `ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];` |
| Найти сирот | запрос 4.3 / `Get-DbaDbOrphanUser -SqlInstance sql01` |
| Сопоставить сироту | `ALTER USER [u] WITH LOGIN = [l];` |
| Перенести логины с SID и паролем | `sp_help_revlogin` / `Copy-DbaLogin -Source sql01 -Destination sql02 -Login buh_1c` |
| Разблокировать логин | `ALTER LOGIN [buh_1c] WITH PASSWORD = N'…' UNLOCK;` |
| Отключить/переименовать `sa` | `ALTER LOGIN sa DISABLE;` / `ALTER LOGIN sa WITH NAME = [новое_имя];` |
| Потерян `sysadmin` | `net start MSSQLSERVER /f /mSQLCMD` → `sqlcmd -E -S sql01 -Q "CREATE LOGIN …; ALTER SERVER ROLE sysadmin ADD MEMBER …"` |
| Задание Agent | `sp_add_job` → `sp_add_jobstep` → `sp_add_schedule` → `sp_attach_schedule` → `sp_add_jobserver`; запуск `sp_start_job` |
| История заданий | `msdb.dbo.sysjobhistory` (`run_status` 0/1) / `sp_help_jobhistory` / `Get-SqlAgentJobHistory` |
| Оператор и оповещение | `sp_add_operator`; `sp_add_alert @message_id = 823 …`; `sp_add_notification … @notification_method = 1` |
| Database Mail | `sp_configure 'Database Mail XPs', 1` → `sysmail_add_account_sp` → `sysmail_add_profile_sp` → `sysmail_add_profileaccount_sp` → `sp_send_dbmail` |
| Журнал ошибок | `EXEC sp_readerrorlog 0, 1, N'Login failed';` / `Get-SqlErrorLog -ServerInstance sql01 -Since Yesterday` |
| Ротация журнала, число архивов | `EXEC sp_cycle_errorlog;` / `Set-SqlErrorLog -ServerInstance sql01 -MaxLogCount 30` |
| DAC | `sp_configure 'remote admin connections', 1`; `sqlcmd -S sql01 -E -A -d master`; SSMS `admin:sql01` |
| Файлы базы и свободное место | запрос 11.1 / `Get-DbaDbFile -SqlInstance sql01 -Database buh` |
| Шаг роста | `ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh', FILEGROWTH = 512MB);` |
| Сжать файл (исключение!) | `DBCC SHRINKFILE (N'buh', <МБ>) WITH WAIT_AT_LOW_PRIORITY (ABORT_AFTER_WAIT = SELF);` (2022+) |
| Перенести файл в экземпляре | `MODIFY FILE (… FILENAME = …)` → `SET OFFLINE WITH ROLLBACK IMMEDIATE` → перенос → `SET ONLINE` |
| Удалить базу (⚠ после копии) | `ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [buh];` |
| Шифрование соединений | Configuration Manager → Certificate + Force Encryption; проверка `encrypt_option` в `sys.dm_exec_connections` |
| Kerberos | `SELECT auth_scheme FROM sys.dm_exec_connections WHERE session_id = @@SPID;`; `setspn -L <учётка службы>` |
| TDE: состояние | `SELECT DB_NAME(database_id), encryption_state, percent_complete FROM sys.dm_database_encryption_keys;` |
| Аудит | `CREATE SERVER AUDIT … TO FILE …`; `CREATE SERVER AUDIT SPECIFICATION … ADD (FAILED_LOGIN_GROUP) …`; `sys.fn_get_audit_file` |
| Опасные опции выключены | `SELECT name, value_in_use FROM sys.configurations WHERE name IN (N'xp_cmdshell', N'clr enabled', N'Ole Automation Procedures', N'contained database authentication');` |
| SQL Server на Linux | `mssql-conf set sqlagent.enabled true`; `… set network.forceencryption 1`; журнал `/var/opt/mssql/log` |

## Источники

**ИТС 8.3.27** (`https://its.1c.ru/db/v8327doc/content/NNN/hdoc`, полные тексты выгружены 19.10.2026): «Клиент-серверный вариант» — гл. 1 (123: 1.5.4), гл. 2 (124: 2.1, 2.3), гл. 3 (125: 3.2.3), гл. 5 (127: 5.2.7.1, 5.2.7.3, 5.2.12, 5.5.1–5.5.8), прил. 3 (133: 3.4–3.11); «Руководство администратора» — гл. 5 (104: 5.2.1.3.2, 5.2.1.3.6–5.2.1.3.8), гл. 7 (106: 7.2, 7.4.4, 7.4.6, 7.4.17), прил. 3 (115: 3.7, 3.17.23), прил. 4 (116: 4.9, 4.10.2, 4.10.4.2), прил. 7 (119: 7.7.4); «Руководство разработчика» — прил. 8 (92: 8.4). Отличия 8.5.1 — `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`.

**Методические статьи ИТС** (`https://its.1c.ru/db/metod8dev/content/NNNN/hdoc`): 1595 (17.07.2007), 2373 (11.04.2008), 2378 (11.04.2008), 2926 (30.10.2008), 5837 (18.11.2022), 5899 (12.05.2016), 5904 (15.07.2019), 6008 (2023).

**Microsoft Learn** (исходники `https://github.com/MicrosoftDocs/sql-docs`, ветка `live`, каталог `docs/`; прочитаны 20.10.2026):

- инструменты: `tools/sqlcmd/sqlcmd-utility.md`, `…/sqlcmd-download-install.md`; `tools/configuration-manager/sql-server-configuration-manager.md`; `database-engine/configure-windows/database-engine-service-startup-options.md`; `linux/configure/mssql-conf.md`, `linux/install-upgrade/setup-sql-agent.md`, `linux/install-upgrade/setup-tools.md`, `linux/sql-server-linux-db-mail-sql-agent.md`, `linux/security/encrypted-connections.md`; страницы `https://learn.microsoft.com/en-us/ssms/install/install`, `…/ssms/release-notes-22`, `…/ssms/release-history`, `…/ssms/faq`, `…/ssms/quickstarts/ssms-connect-query-sql-server`; `https://learn.microsoft.com/en-us/powershell/sql-server/download-sql-server-ps-module`, `…/sql-server-powershell`, `…/powershell/module/sqlserver/` (`invoke-sqlcmd`, `get-sqlerrorlog`, `set-sqlerrorlog`, `set-sqlauthenticationmode`, `get-sqlagentjobhistory`); `https://www.powershellgallery.com/packages/SqlServer`;
- безопасность и принципалы: `relational-databases/security/authentication-access/server-level-roles.md`, `…/principals-database-engine.md`; `t-sql/statements/create-login-transact-sql.md`, `alter-login-transact-sql.md`, `create-user-transact-sql.md`, `alter-user-transact-sql.md`, `alter-authorization-transact-sql.md`, `alter-server-role-transact-sql.md`, `drop-database-transact-sql.md`, `create-database-transact-sql.md`; `relational-databases/security/password-policy.md`; `t-sql/functions/loginproperty-transact-sql.md`; `relational-databases/system-functions/sys-fn-my-permissions-transact-sql.md`; `database-engine/configure-windows/change-server-authentication-mode.md`, `connect-to-sql-server-when-system-administrators-are-locked-out.md`, `configure-windows-service-accounts-and-permissions.md`, `register-a-service-principal-name-for-kerberos-connections.md`; `relational-databases/security/sql-server-security-best-practices.md`, `surface-area-configuration.md`; `database-engine/configure-windows/server-configuration-options-sql-server.md`;
- сироты и перенос: `sql-server/failover-clusters/troubleshoot-orphaned-users-sql-server.md`; `relational-databases/system-stored-procedures/sp-change-users-login-transact-sql.md`, `sp-changedbowner-transact-sql.md`, `sp-detach-db-transact-sql.md`, `sp-attach-db-transact-sql.md`; `relational-databases/databases/manage-metadata-when-making-a-database-available-on-another-server.md`, `database-detach-and-attach-sql-server.md`, `move-user-databases.md`, `copy-databases-with-backup-and-restore.md`; `t-sql/statements/restore-statements-transact-sql.md`; статья поддержки `https://learn.microsoft.com/en-us/troubleshoot/sql/database-engine/security/transfer-logins-passwords-between-instances`;
- контейнерные базы: `relational-databases/databases/contained-databases.md`, `security-best-practices-with-contained-databases.md`; `relational-databases/security/contained-database-users-making-your-database-portable.md`; `database-engine/configure-windows/contained-database-authentication-server-configuration-option.md`;
- Agent и почта: `https://learn.microsoft.com/en-us/ssms/agent/sql-server-agent`, `…/implement-sql-server-agent-security`; `relational-databases/system-stored-procedures/sp-add-job-…`, `sp-add-jobstep-…`, `sp-add-schedule-…`, `sp-attach-schedule-…`, `sp-add-jobserver-…`, `sp-update-job-…`, `sp-start-job-…`, `sp-help-jobhistory-…`, `sp-add-operator-…`, `sp-add-alert-…`, `sp-add-notification-…`, `sysmail-add-account-sp-…`, `sysmail-add-profile-sp-…`, `sysmail-add-profileaccount-sp-…`, `sysmail-add-principalprofile-sp-…`, `sp-send-dbmail-…`; `relational-databases/system-tables/dbo-sysjobhistory-…`, `dbo-sysoperators-…`, `dbo-sysalerts-…`; `relational-databases/system-catalog-views/sysmail-allitems-…`, `sysmail-event-log-…`; `relational-databases/database-mail/configure-database-mail.md`, `configure-sql-server-agent-mail-to-use-database-mail.md`, `check-the-status-of-e-mail-messages-sent-with-database-mail.md`; `database-engine/configure-windows/agent-xps-…`, `database-mail-xps-…`; `t-sql/language-elements/raiserror-transact-sql.md`; ошибки — `relational-databases/errors-events/mssqlserver-823-…`, `-824-`, `-825-`, `-9002-`, `-1105-`, `-18456-database-engine-error.md`;
- журнал ошибок и DAC: `relational-databases/system-stored-procedures/sp-readerrorlog-…`, `sp-cycle-errorlog-…`, `sp-cycle-agent-errorlog-…`; `database-engine/configure-windows/scm-services-configure-sql-server-error-logs.md`; `relational-databases/performance/view-the-sql-server-error-log-sql-server-management-studio.md`; `database-engine/configure-windows/diagnostic-connection-for-database-administrators.md`; `t-sql/language-elements/kill-transact-sql.md`;
- файлы: `relational-databases/databases/database-files-and-filegroups.md`, `database-instant-file-initialization.md`, `shrink-a-database.md`, `shrink-a-file.md`; `t-sql/database-console-commands/dbcc-shrinkfile-transact-sql.md`, `dbcc-shrinkdatabase-transact-sql.md`; `t-sql/statements/alter-database-transact-sql-file-and-filegroup-options.md`, `alter-database-transact-sql-set-options.md`; `relational-databases/logs/manage-the-size-of-the-transaction-log-file.md`; `relational-databases/system-catalog-views/sys-databases-…`, `sys-master-files-…`, `sys-server-principals-…`, `sys-database-principals-…`, `sys-sql-logins-…`; `relational-databases/system-dynamic-management-objects/sys-dm-exec-connections-…`, `sys-dm-exec-sessions-…`, `sys-dm-server-services-…`; `t-sql/functions/serverproperty-transact-sql.md`;
- шифрование и аудит: `database-engine/configure-windows/configure-sql-server-encryption.md`, `certificate-requirements.md`, `special-cases-for-encrypting-connections-sql-server.md`; `relational-databases/security/networking/tds-8.md`, `connect-with-strict-encryption.md`; `connect/oledb/features/encryption-and-certificate-validation.md`; `relational-databases/security/encryption/transparent-data-encryption.md`, `move-a-tde-protected-database-to-another-sql-server.md`; `relational-databases/system-dynamic-management-objects/sys-dm-database-encryption-keys-…`; `relational-databases/security/auditing/sql-server-audit-database-engine.md`, `create-a-server-audit-and-server-audit-specification.md`, `sql-server-audit-action-groups-and-actions.md`; `t-sql/statements/create-server-audit-transact-sql.md`, `create-server-audit-specification-transact-sql.md`; `relational-databases/system-functions/sys-fn-get-audit-file-transact-sql.md`;
- редакции и 2025: `sql-server/editions-and-components-of-sql-server-2017.md`, `…-2019.md`, `…-2022.md`, `…-2025.md`; `database-engine/breaking-changes-to-database-engine-features-in-sql-server-2025.md`.

**Сторонние** (прочитаны 20.10.2026): dbatools — `https://github.com/dataplat/dbatools` (README, исходники `public/*.ps1` ветки `development`, выпуск v2.9.1 от 15.10.2026), `https://dbatools.io`; First Responder Kit — `https://github.com/BrentOzarULTD/SQL-Server-First-Responder-Kit` (выпуск 20260708); sp_WhoIsActive — `https://github.com/amachanic/sp_whoisactive` (выпуск 20260409); Maintenance Solution — `https://github.com/olahallengren/sql-server-maintenance-solution`; go-sqlcmd — `https://github.com/microsoft/go-sqlcmd` (v1.10.0).

**Дополнительно при независимой сверке 20.10.2026**: `t-sql/statements/revert-transact-sql.md`, `execute-as-transact-sql.md`, `create-certificate-transact-sql.md` (срок сертификата для шифрования базы не проверяется), `backup-transact-sql.md` (`NO_LOG`/`TRUNCATE_ONLY` удалены); `relational-databases/system-catalog-views/sys-endpoints-transact-sql.md`, `messages-for-errors-catalog-views-sys-messages.md`, `sys-server-audits-transact-sql.md`, `sys-server-role-members-transact-sql.md`; `relational-databases/database-mail/database-mail-external-program.md`; `relational-databases/includes/sql-server-agent-ownership.md`; `sql-server/what-s-new-in-sql-server-2025.md`; страницы `https://learn.microsoft.com/en-us/ssms/agent/sql-server-agent-error-log`, `…/ssms/server-properties/security-page`, `…/ssms/scripting/sqlcmd-scripts-query-editor`, `…/powershell/module/sqlserver/set-sqlnetworkconfiguration`, `…/start-sqlinstance`, `https://learn.microsoft.com/en-us/lifecycle/products/sql-server-2016`, `…/sql-server-management-studio`; статьи поддержки `SupportArticles-docs` — `database-engine/security/transfer-logins-passwords-between-instances.md`, `database-engine/security/antivirus-and-sql-server.md`; dbatools — исходники `public/*.ps1` метки `v2.9.1` и `readme.md` ветки `development`; выпуски GitHub (API `releases`) dbatools, First Responder Kit, sp_WhoIsActive, go-sqlcmd. ИТС — полные тексты 104, 106, 115, 116, 119, 123–125, 127, 133, 92 и методички 1595, 2373, 2926, 5837, 5899, 5904, 6008 (`_index.txt` — даты).

**База знаний** (согласованность): `../1c-windows/02-ms-sql-server-dlya-1c.md`, `../1c-windows/01-ustanovka-servera-i-sluzhba-windows.md`, `../1c-windows/06-windows-server-dlya-administratora-1c.md`, `../1c/03-administrirovanie-klastera-ras-rac.md`, `../1c/06-infobazy-ibcmd-paketnyj-rezhim.md`, `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.

## Что не удалось подтвердить

- ⚠ **SQL Server 2025** в списках поддерживаемых СУБД платформы 8.3.27 и 8.5.1 отсутствует (на 20.10.2026; отсутствие подтверждено сверкой перечня) — работа платформы с 2025 не подтверждена.
- ⚠ Чем платформа прерывает долгий запрос при «Удалить» соединение (`KILL` или отмена запроса) и годится ли вместо `processadmin` пользовательская серверная роль с `ALTER ANY CONNECTION`.
- ⚠ Достаточно ли прав `guest`/`public` в `master` и `tempdb` для требования ИТС «чтение `master`, полный доступ к `tempdb`».
- ⚠ Какую сортировку платформа задаёт базе для разных «Языков (стран)», включая конфигурации WE, и как она поступает с заранее созданной базой другой сортировки.
- ⚠ Работает ли платформа с базой, где логин ИБ — член `db_owner`, а не владелец; применимость контейнерных баз (вывод сделан по требованиям к серверным ролям).
- ⚠ Аутентификация ОС у `ibcmd` с MS SQL (документировано только для `ibsrv`); умолчание `--date-offset` у `rac`; разделитель `Server/instance` vs `Server\instance`.
- ⚠ Поддержка платформой OLE DB Driver 19 и `Encrypt=Strict`/TDS 8.0; что передаётся в `Encrypt`/`TrustServerCertificate` (имя свойства `hResultMSOLEDBSQL19` в 8.5.1 — лишь косвенный признак).
- ⚠ Хранение пароля СУБД в реестре кластера (`1CV8Clst.lst`) и его защита.
- ⚠ Доступ локального `USR1CV8` к удалённому SQL Server при аутентификации ОС (вывод по общей логике Windows-аутентификации).
- ⚠ Попадают ли ошибки 9002 и 1105 в журнал приложений Windows (а значит, срабатывают ли на них оповещения Agent без `sp_altermessage`) — проверяется на сервере запросом к `sys.messages.is_event_logged` (7.6).
- ⚠ Работа заданий Agent, владелец которых — отключённый `sa`.
- ⚠ T‑SQL-способ задать профиль почты Agent (`sp_set_sqlagent_properties` в справочнике нет); имя текущего файла журнала Agent (`SQLAGENT.OUT`); умолчание «Login auditing» (на странице Security свойств сервера не указано).
- ⚠ Принимает ли SQL Server 2022 и младше хэш пароля версии 3 (SQL Server 2025) при `CREATE LOGIN … HASHED`.
- ⚠ Скрипты не выполнялись. Сочетание `PASSWORD … HASHED, SID = …` в одной команде — подтверждено 20.10.2026 (синтаксис `CREATE LOGIN` и статья поддержки Microsoft о `sp_help_revlogin`).
