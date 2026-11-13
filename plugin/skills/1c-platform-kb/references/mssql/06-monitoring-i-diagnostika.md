# Мониторинг и диагностика SQL Server под 1С: ожидания, блокировки, взаимоблокировки, медленные запросы

> **Официальные тексты по теме** (полные тексты ИТС 8.3.27, адрес главы — `https://its.1c.ru/db/v8327doc/content/NNN/hdoc`): «Руководство администратора» — прил. 3, разд. 3.24 «logcfg.xml» (115: `DBMSSQL`, `DBMSSQLCONN`, `Dbpid`, `<plansql>`, `<dbmslocks>`, разд. 3.24.5 о взаимных блокировках), гл. 6, разд. 6.6.3 (105: «Время ожидания блокировки данных»); «Клиент-серверный вариант» — гл. 1, разд. 1.5.4 (123: версии SQL Server), гл. 5, разд. 5.2.11–5.2.12 (127: «Соединение с СУБД», «Заблокировано СУБД», разрыв соединения); «Руководство разработчика» — гл. 9 (54: уровни изоляции на MS SQL, индексы). Методические статьи ИТС: 6008, 5861, 5910, 5813, 5906, 5834, 5945, 5946, 5904, 5837, 5838, 5899, 2923, 2374. Конспекты: `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`, `../its-metod/sbor-dannyh-dlya-rassledovaniya-problem.md`, `../its-metod/monitoring-i-audit.md`, `../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`, `../its-docs/dev-gl09-rabota-s-dannymi.md`, `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`.

> Статус: проверено независимой сверкой 20.10.2026: с исходниками MS Learn (`MicrosoftDocs/sql-docs`, ветка `live`, — DMV, `ALTER DATABASE SET`/Query Store, XE, `sp_configure`, флаги трассировки, IFI, tempdb, блокировки и взаимоблокировки, права и роли, счётчики; статьи поддержки о блокировках, вводе-выводе, tempdb; справка `logman`), с полными текстами ИТС 8.3.27 (адм. прил. 3, разд. 3.24 и гл. 6, 7; КС гл. 1, 2, 5; разр. гл. 9), методическими статьями 6008, 5861, 5910, 5813, 5906, 5834, 5837, 5838, 5899, 5904, 5945, 5946, 2374, 2923, 2926 и репозиториями `sp_WhoIsActive`, First Responder Kit; имена колонок DMV и синтаксис всех запросов D-01…D-37 сверены со справочником; исправлено 6 ошибок, закрыто 13 пометок; на сервере не проверялось — запросы T‑SQL, сеансы расширенных событий и команды не запускались, сначала прогоните их на тестовом экземпляре.

> Область: наблюдение за SQL Server с базами «1С:Предприятия 8» (рабочие серверы 1С — на Windows) и расследование жалоб «всё тормозит», «висит проведение», «конфликт блокировок», «взаимоблокировка» — от ожиданий до строки кода конфигурации | Версии: SQL Server 2016–2025 (1С 8.3.27 и 8.5.1 поддерживают до 2022 включительно — [ИТС-КС разд. 1.5.4]; `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`), платформа 8.3.2x / 8.5.x | Актуальность: 2026-10-20

**Пометки.** **[MS Learn]** — документация Microsoft (исходники `MicrosoftDocs/sql-docs`, ветка `live`, и статьи поддержки `MicrosoftDocs/SupportArticles-docs`, прочитаны 20.10.2026); **[ИТС-КС разд. N]**, **[ИТС-адм разд. N]** / **[ИТС-адм прил. 3, разд. N]**, **[ИТС-разр гл./прил. N]** — книги ИТС 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья `https://its.1c.ru/db/metod8dev/content/NNNN/hdoc` с датой (многие писались под SQL Server 2005–2014 — применимость оговорена); **[сторонний]** — сторонний инструмент по его репозиторию; **[практика]** — практика администраторов, в первоисточниках так не описана; **⚠** — не подтверждено первоисточником.

**Ваш контекст.** У вас сервер 1С на Ubuntu и «PostgreSQL для 1С»; **рабочие процессы 1С на Linux с MS SQL Server не работают** [ИТС-КС разд. 2.3; ИТС-адм разд. 7.2] — статья справочная, для Windows-площадок организации. Сам SQL Server может стоять на Linux (1.6). Базы сервисов (Redmine, NetBox и др.) в экземпляр под 1С не кладутся. Аналог для PostgreSQL — `../postgresql/06-monitoring-i-diagnostika-zaprosov.md`.

**Смежные статьи раздела** (их тему здесь не расписываю): `01-versii-redakcii-arhitektura.md`; `02-ustanovka-i-nastrojka-ekzemplyara.md` (память, `MAXDOP`, флаги, tempdb); `03-administrirovanie-instrumenty-prava.md` (SSMS, `sqlcmd`, роли); `04-rezervnoe-kopirovanie-i-vosstanovlenie.md`; `05-obsluzhivanie-indeksy-statistika.md`; `07-otkazoustojchivost-i-obnovlenie-versij.md`; `08-tipovye-problemy-i-zaprosy-1c.md`. Обзор — `../1c-windows/02-ms-sql-server-dlya-1c.md` (раздел 11 — краткая версия этой статьи).

**Условные имена**: экземпляр `sql01`, база ИБ `buh`, логин кластера 1С `buh_1c`, логин мониторинга `mon_ro`, каталог файлов XE `E:\XE` (у учётной записи службы SQL Server должно быть право записи [практика]). `D-NN` — запросы из библиотеки (раздел 13).

## Кратко — главные факты

1. **Начинать с ожиданий, а не с Диспетчера задач**: SQL Server сам управляет памятью и потоками (SQLOS), узкое место видно по статистике ожиданий; быстрый вход — Activity Monitor (Overview → Resource Waits → Processes) [ИТС-мет 6008, 2023].
2. **`sys.dm_os_wait_stats` накопительна** с момента старта или `DBCC SQLPERF ('sys.dm_os_wait_stats', CLEAR)` и показывает завершённые ожидания; текущие — `sys.dm_exec_requests`, `sys.dm_os_waiting_tasks` [MS Learn]. «Что сейчас» — дельта за минуту (D-03).
3. **Права**: до 2019 — `VIEW SERVER STATE`; с 2022 — `VIEW SERVER PERFORMANCE STATE` (роль `##MS_ServerStateReader##`); `KILL` — `ALTER ANY CONNECTION`; DAC — только `sysadmin` [MS Learn].
4. **Ожидания 1С**: `LCK_M_*` — блокировки; `PAGEIOLATCH_*` — чтение с диска; `WRITELOG`/`LOGBUFFER` — диск журнала; `CXPACKET`/`CXCONSUMER` — параллелизм (для 1С `MAXDOP = 1`); `ASYNC_NETWORK_IO` — сервер 1С медленно забирает результат; `RESOURCE_SEMAPHORE` — память под сортировки и хеши [ИТС-мет 6008; MS Learn].
5. **`LCK_M_RS_*`, `LCK_M_RIn_*`, `LCK_M_RX_*`** — диапазонные блокировки, т. е. `SERIALIZABLE`: признак **автоматического режима** блокировок (управляемый на SQL Server 2005+ — Read Committed Snapshot) [MS Learn; ИТС-разр гл. 9, разд. 9.2.3.2].
6. **По DMV не узнать пользователя 1С** — виден логин ИБ и компьютер рабочего сервера; мост — «Соединение с СУБД» в консоли кластера (`db-proc-info` в `rac`) = `session_id` = свойство `Dbpid` события `DBMSSQL` [ИТС-КС разд. 5.2.11.1; ИТС-адм прил. 3, разд. 3.24.2.4.2].
7. **Головной блокирующий в 1С часто «спит»**: транзакция открыта, а `rphost` исполняет код между запросами — в `sys.dm_exec_requests` строки нет, в `sys.dm_exec_sessions` `open_transaction_count > 0` [MS Learn; практика]. D-07 это учитывает.
8. **Платформа сама опрашивает блокировки** (`SELECT spid, blocked FROM master.dbo.sysprocesses …`) — штатный запрос, не «оптимизировать» [ИТС-мет 6006, 2022 — конспект `vzaimoblokirovki…`, 2.4.2].
9. **Взаимоблокировки уже пишутся** сеансом `system_health` (`xml_deadlock_report` с графом); флаги 1204/1222 на нагруженном сервере не нужны [MS Learn].
10. **Ошибка 1205** — жертва взаимоблокировки (поиск циклов раз в 5 с, жертва — дешевле откатить) [MS Learn]; «thread communication buffer», «Intra-query parallelism» — потоки параллельного плана, `MAXDOP = 1` [ИТС-мет 5834, 2015].
11. **Долгие блокировки** — blocked process report: `sp_configure 'blocked process threshold', N` (5–86 400 с) + XE `blocked_process_report` [MS Learn].
12. **SQL Trace и Profiler устарели** — трассировать расширенными событиями (методика 5910 с `sp_trace_create` ещё работает) [MS Learn; ИТС-мет 5910, 2016].
13. **Кеш планов живёт до вытеснения плана**: ежедневный `DBCC FREEPROCCACHE` из регламента 1С [ИТС-мет 5837, 2022] обнуляет «топ запросов» — смотреть топ за период после очистки или Query Store; время в `sys.dm_exec_query_stats` и Query Store — **микросекунды**, в `sys.dm_exec_requests` — миллисекунды [MS Learn].
14. **Query Store** — с 2016, во всех редакциях; включён по умолчанию для **новых** баз с 2022; хранит историю запросов, планов и (с 2017) ожиданий в самой базе [MS Learn].
15. **Принудительный план для 1С — крайняя мера**: номера `#tt<N>` меняют тексты, реструктуризация — схему, неудачное принуждение SQL Server молча игнорирует [MS Learn; практика]. `FORCE_LAST_GOOD_PLAN` — только Enterprise [MS Learn].
16. **Топ запросов** — методики 5861 (CPU), 5813 (диск), 5910 («размазанная» нагрузка), 5906 (top-25 вызовов `CALL`) [ИТС-мет 5861, 2015; 5813, 2015; 5910, 2016; 5906, 2016]; `CPU_Time_Ms` в скриптах 5861 — на деле микросекунды [MS Learn].
17. **Диски**: задержки по файлам — `sys.dm_io_virtual_file_stats`; ориентир 1С — данные 10–20 мс, журнал 1–5 мс [ИТС-мет 6008; 5904]; Microsoft — устойчиво выше 10–15 мс — узкое место, ошибка 833 — ввод-вывод дольше 15 с [MS Learn].
18. **tempdb под 1С нагружена всегда**: временные таблицы платформы, сортировки, хранилище версий RCSI [ИТС-мет 2374, 2008; MS Learn]; `PAGELATCH_UP` на `2:1:1`/`2:1:3` — мало файлов tempdb [MS Learn].
19. **Техжурнал `DBMSSQL`** даёт `Sql`, `Context` (стек 1С) и `Dbpid`; **`<plansql/>`** собирает планы для всех запросов всех баз и замедляет СУБД — только на время анализа, лучше на копии [ИТС-адм прил. 3, разд. 3.24.2.10.1; `../1c/07-…`].
20. **`<dbmslocks/>`** раз в ≥ 2 с запрашивает «кто кого блокирует» и дописывает к событиям `lka`, `lkp`, `lkpid`, `lkaid`, `lksrc`, `lkpto`, `lkato` [ИТС-адм прил. 3, разд. 3.24.5].
21. **Таблицы `_Reference<n>`, `_InfoRg<n>`, `_AccumRg<n>`…** → объекты конфигурации: `ПолучитьСтруктуруХраненияБазыДанных()` [`../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`].
22. **Флаг 2330** из рекомендаций 1С [ИТС-мет 5946, 2019] отключает статистику использования индексов — `sys.dm_db_index_usage_stats` пустеет; недокументирован Microsoft (Подтверждено 20.10.2026: в справочнике флагов MS Learn его нет, 1С тоже называет его недокументированным).
23. **Аварийный вход** — DAC: `sqlcmd -S sql01 -A` / `admin:sql01`; по сети — `sp_configure 'remote admin connections', 1` [MS Learn; ИТС-мет 6008]. **SQL Server 2025** в перечне 1С нет [ИТС-КС разд. 1.5.4] — его новшества (`LCK_M_S_XACT*`, `MAX_DURATION` у XE) вне поддержки 1С [MS Learn].

## 1. С чего начинать: методика ИТС 6008 и общий порядок

### 1.1. Принцип: ожидания

По [ИТС-мет 6008, 2023]: SQL Server содержит SQLOS, поэтому средства Windows неверно показывают нагрузку на СУБД; операция выполняется квантами (около 4 мс), перед каждым проверяются ресурсы (диск, процессор, память, сеть, блокировки), при недоступности соединение ждёт и копит время по типу ожидания — эта статистика и показывает узкое место.

Microsoft делит ожидания на **ресурсные** (блокировки, латчи, сеть, диск), **очередные** (простаивающие фоновые задачи — их огромные времена нормальны) и **внешние** (расширенные процедуры, связанные серверы) [MS Learn]. `wait_time_ms` включает **сигнальную** часть `signal_wait_time_ms` — от освобождения ресурса до получения процессора; её большая доля — очередь к CPU (10.5) [MS Learn].

### 1.2. Порядок «жалоба → причина»

По [ИТС-мет 6008; 5861; 5813; 5910; 5906] и методике расследования блокировок (`../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`):

1. **Отделить СУБД от сервера 1С**: у тормозящего сеанса в консоли кластера сравнить «Время вызова (текущее)» и «Время вызова СУБД (текущее)» [ИТС-КС разд. 5.2.11.1]; Монитором ресурсов убедиться, что нагрузку создаёт SQL Server [ИТС-мет 5813; 5861]. Если время уходит не в СУБД — `../1c/10-…`, сценарий 1.22 в `../its-metod/sbor-dannyh-…`.
2. **Ожидания** — накопленные (D-02) и за минуту (D-03); в острой ситуации — Activity Monitor (3.4).
3. **Кто ждёт сейчас**: D-05, цепочки блокировок D-07, объект блокировки D-08.
4. **По типу ожидания** — в раздел: блокировки → 5; взаимоблокировки → 6; `PAGEIOLATCH`/`WRITELOG` → 10.1–10.2; `RESOURCE_SEMAPHORE` → 10.3; `PAGELATCH` на tempdb → 10.4; CPU → 9.2, 10.5.
5. **База и запросы-лидеры** — кеш (D-14…D-18) или Query Store (D-28…D-33); проверить, не «размазана» ли нагрузка [ИТС-мет 5861].
6. **Связать с кодом 1С** — «узкий» техжурнал `DBMSSQL` по таблицам запроса (12.2); сеанс — по `session_id` в консоли, затем журнал регистрации [ИТС-мет 5813; 5861].
7. **Исправить и убедиться, что нагрузка ушла** [ИТС-мет 5813; 5861].

Данные для поддержки 1С — сценарии `../its-metod/sbor-dannyh-…` (1.14 взаимоблокировки — `xml_deadlock_report`; 1.21 диск; 1.23 CPU).

### 1.3. Права для диагностики

| Что | Разрешение | Источник |
|---|---|---|
| DMV (`sys.dm_os_wait_stats`, `sys.dm_exec_requests`, `sys.dm_exec_sessions`, `sys.dm_exec_query_stats`…), чужие сеансы | до 2019 — `VIEW SERVER STATE`; 2022+ — `VIEW SERVER PERFORMANCE STATE` | [MS Learn] |
| Роли 2022+ | `##MS_ServerStateReader##` (`VIEW SERVER STATE` + `…PERFORMANCE STATE` + `…SECURITY STATE`), `##MS_ServerPerformanceStateReader##` (только performance), `##MS_ServerStateManager##` (+ `ALTER SERVER STATE`: `DBCC FREEPROCCACHE`, `DBCC SQLPERF`) | [MS Learn] |
| `KILL` | `ALTER ANY CONNECTION` (`sysadmin`, `processadmin`) | [MS Learn] |
| DAC | `sysadmin` | [MS Learn] |
| Сеансы XE | `ALTER ANY EVENT SESSION`; с 2022 для создания — также `CREATE ANY EVENT SESSION` (Подтверждено 20.10.2026 по MS Learn, CREATE EVENT SESSION) | [MS Learn] |
| Запросы в контексте базы ИБ (`USE [buh]`: D-08, D-09, D-28…D-34) | доступ к базе (пользователь для логина); Query Store читается с `VIEW DATABASE STATE` (2022+: `VIEW DATABASE PERFORMANCE STATE`) — серверные `VIEW SERVER STATE` и роли `##MS_Server…Reader##` дают его только в базах, где у логина есть пользователь; без `VIEW DEFINITION` (2022+: `VIEW PERFORMANCE DEFINITION`) имена таблиц из `sys.partitions`/`OBJECT_NAME` возвращаются `NULL` (видимость метаданных) | [MS Learn] |
| Принудить план Query Store | `ALTER` на базу | [MS Learn] |
| Разрыв соединения из консоли 1С при долгом запросе | права логина, под которым кластер подключается к СУБД (практика — `processadmin`) | [ИТС-КС разд. 5.2.12.3] |

```sql
-- от имени sysadmin
CREATE LOGIN mon_ro WITH PASSWORD = N'<сложный пароль>', CHECK_POLICY = ON;
GRANT VIEW SERVER STATE TO mon_ro;
-- 2022+, минимально: ALTER SERVER ROLE [##MS_ServerPerformanceStateReader##] ADD MEMBER mon_ro;
-- для D-08, D-09, D-28…D-34 (контекст базы ИБ) — либо выполнять их под sysadmin, либо [практика]:
-- USE [buh]; CREATE USER mon_ro FOR LOGIN mon_ro; GRANT VIEW DEFINITION TO mon_ro;   -- права на данные не даёт
EXECUTE AS LOGIN = N'mon_ro';
SELECT COUNT(*) AS sessions_visible FROM sys.dm_exec_sessions;   -- проверка: больше 1
REVERT;
```

Эти права дают чтение служебных представлений, но не данных баз [MS Learn]; тексты запросов 1С с параметрами при этом видны — учитывайте при выдаче доступа подрядчикам [практика].

### 1.4. Инструменты

| Инструмент | Что даёт | Версия / нагрузка | Источник |
|---|---|---|---|
| Activity Monitor | Overview, Processes, Resource Waits, Data File I/O, Expensive Queries | все; малая | [ИТС-мет 6008; MS Learn] |
| Performance Dashboard | CPU, ожидания, дорогие запросы | SSMS 17.2+ | [MS Learn] |
| Стандартные отчёты SSMS | «Activity – All Blocking Transactions», «Top Transactions by Locks Count» | все | [MS Learn; ИТС-мет 6006 — конспект, 2.4.4] |
| Расширенные события, `system_health` | трассировка запросов, блокировок, взаимоблокировок | `system_health` всегда включён | [MS Learn] |
| Query Store | история запросов, планов, ожиданий | 2016+ | [MS Learn] |
| ЦКК, ЦУП (КИП) | контрольные процедуры, анализ блокировок и взаимоблокировок | КИП | `../its-metod/monitoring-i-audit.md`; `…/vzaimoblokirovki-…` |
| `sp_WhoIsActive`; First Responder Kit | «кто что делает», экспресс-диагностика | [сторонний] | 4.3 |

SQL Server Profiler на рабочем сервере не использовать: нагружает сервер и теряет события [ИТС-мет 5910]; SQL Trace и Profiler объявлены устаревшими [MS Learn].

### 1.5. Сервер «не отвечает»: DAC

- Отдельные ресурсы, одно подключение на экземпляр; по умолчанию — только с самого сервера; по сети — `sp_configure 'remote admin connections', 1` + `RECONFIGURE` без перезапуска; на кластерах по умолчанию выключено [MS Learn; ИТС-мет 6008; 5904].
- Порт — 1434, если свободен, иначе динамический (в журнале ошибок); Express слушает DAC только с флагом 7806 [MS Learn].
- `sqlcmd -S sql01 -A` (или `-U sa -A`); в SSMS — `admin:sql01` (`admin:sql01\INST`) **в окне запроса**: Object Explorer/IntelliSense пытаются открыть второе соединение [MS Learn].
- В DAC — только лёгкие запросы (D-05, D-07) и `KILL` [практика].

### 1.6. SQL Server на Linux

- DMV, Query Store, XE и `system_health` — те же [MS Learn]; журнал ошибок — `/var/opt/mssql/log/errorlog` в UTF-16 (`iconv -f UTF-16LE -t UTF-8`), дампы — там же [MS Learn].
- Performance Monitor нет — счётчики SQL Server читаются через `sys.dm_os_performance_counters` (D-24, D-25) [практика]; ОС — средствами Linux (`../linux/06-…`).
- Файлы `system_health*.xel` — в каталоге журнала экземпляра ⚠ (для Windows — `\MSSQL\Log` [MS Learn], путь на Linux по аналогии).
- Техжурнал `DBMSSQL` собирается на рабочих серверах 1С (Windows) [ИТС-КС разд. 2.3].

## 2. Как работа 1С выглядит изнутри SQL Server

### 2.1. Соединения и имена

| В SQL Server | Для 1С | Источник |
|---|---|---|
| `login_name` | логин из свойств ИБ («Пользователь сервера БД»); при пустом — учётная запись службы сервера 1С | [ИТС-мет 2926, 2008]; `../1c-windows/02-…`, 4.1 |
| `host_name`, `client_net_address` | компьютер рабочего сервера 1С (`rphost`), не рабочее место | [ИТС-КС разд. 2.1]; [практика] |
| `program_name`, `client_interface_name` | на практике вида «1CV83 Server», OLE DB ⚠ — проверить `SELECT DISTINCT program_name, client_interface_name FROM sys.dm_exec_sessions WHERE is_user_process = 1;` | ⚠ |

Сводка соединений по серверам 1С и базам — D-36.

### 2.2. Тексты запросов: `sp_executesql`, `@P`, `#tt`

- Запросы приходят через `sp_executesql` с параметрами `@P1`, `@P2`… и используют временные таблицы `#tt<число>` — нормализация методики 5910 вырезает именно `exec sp_executesql N'`, `@P<цифры>`, `#tt<цифры>`; в техжурнале текст выглядит как `{call sp_executesql(N'…', N'…')}` [ИТС-мет 5910, 2016].
- Временные таблицы и `GROUP BY`/`UNION`/`DISTINCT` нагружают tempdb [ИТС-мет 2374, 2008].
- Один запрос конфигурации из разных сеансов может иметь разный текст (номера `#tt`) и попадать в кеш и Query Store отдельными записями ⚠ [практика].
- `FETCH API_CURSOR…` в тексте — выборка серверным курсором; исходный текст — `sys.dm_exec_cursors(session_id)` (D-35) [MS Learn]; что платформа их использует, в ИТС не описано ⚠.

### 2.3. Уровни изоляции и время ожидания блокировки

| Режим блокировок | Уровень на MS SQL | Чтение вне транзакции | Признаки в DMV |
|---|---|---|---|
| Автоматический | Repeatable Read или Serializable | «грязное» | `transaction_isolation_level` 3/4; `LCK_M_S`, `LCK_M_RS_*`, `LCK_M_RIn_*` |
| Управляемый, SQL Server 2005+ | Read Committed Snapshot | согласованное | уровень 2 (RCSI — свойство базы); `LCK_M_X`/`U`/`IX`; рост хранилища версий |

Уровни — [ИТС-разр гл. 9, разд. 9.2.3.2]; коды `transaction_isolation_level` (0 не задан, 1 ReadUncommitted, 2 ReadCommitted, 3 RepeatableRead, 4 Serializable, 5 Snapshot) — [MS Learn]. RCSI базы — `SELECT name, is_read_committed_snapshot_on FROM sys.databases;`, вручную не менять; что платформа включает его сама, в ИТС прямо не сказано ⚠.

**«Время ожидания блокировки данных»** (параметры ИБ, «Прочие») — предел ожидания транзакционной блокировки сервером БД и управляемой блокировки; изменение требует прав администратора и монопольного режима; методы `ПолучитьВремяОжиданияБлокировкиДанных()`/`УстановитьВремяОжиданияБлокировкиДанных()` [ИТС-адм разд. 6.6.3]. Умолчание (на практике 20 с) и передача значения в `LOCK_TIMEOUT` сеанса (колонка `lock_timeout`, мс, в `sys.dm_exec_sessions`) в документации не описаны ⚠. Превышение на SQL Server — ошибка 1222 «Lock request time out period exceeded» (в техжурнале — от провайдера, например `Microsoft SQL Server Native Client 11.0: Lock request time out period exceeded.`) [`../its-metod/sbor-dannyh-…`, 1.15]; счётчик `Lock Timeouts/sec` [MS Learn].

### 2.4. Мост «сеанс 1С ↔ `session_id`»

| Где | Поле | Смысл | Источник |
|---|---|---|---|
| Консоль, сеансы | «Соединение с СУБД» | идентификатор процесса сервера БД (`session_id`), пока соединение захвачено: идёт вызов СУБД, открыта транзакция или держится `МенеджерВременныхТаблиц` с таблицей | [ИТС-КС разд. 5.2.11.1] |
| там же | «Заблокировано СУБД», «Захвачено СУБД», «Время вызова СУБД» | кто держит блокировку СУБД; сколько захвачено соединение; время обращений к СУБД | [ИТС-КС разд. 5.2.11.1] |
| `rac session list` | `db-proc-info`, `blocked-by-dbms`, `db-proc-took`, `duration-current-dbms` | то же; сверять с `rac help session` | `../1c/03-administrirovanie-klastera-ras-rac.md` |
| Техжурнал `DBMSSQL` | `Dbpid` | идентификатор соединения в терминах СУБД | [ИТС-адм прил. 3, разд. 3.24.2.4.2] |
| `<dbmslocks/>` | `lksrc` | номер соединения источника блокировки (у жертвы) | [ИТС-адм прил. 3, разд. 3.24.5] |

Порядок: D-07 дал головной `session_id` → в консоли сеанс с этим «Соединением с СУБД» → пользователь, компьютер, время начала → журнал регистрации и техжурнал. Если поле пусто (соединение не захвачено), сопоставлять по `Dbpid` в техжурнале [ИТС-КС разд. 5.2.11.1; практика].

### 2.5. Служебные запросы платформы

- Опрос блокировок сервисом вспомогательных функций кластера: `SELECT spid, blocked FROM master.dbo.sysprocesses WITH(NOLOCK) WHERE blocked > 0 AND lastwaittype LIKE 'LCK_%'` [ИТС-мет 6006 — конспект, 2.4.2].
- При `<dbmslocks/>` — запрос «кто кого заблокировал» не чаще раза в 2 с, одним рабочим процессом [ИТС-адм прил. 3, разд. 3.24.5]; при `<plansql/>` — получение планов для всех запросов [`../1c/07-…`].

Их не «оптимизировать» и не убивать — исключать при разборе топов [практика].

### 2.6. Таблицы → объекты конфигурации

| Таблица SQL | Объект 1С |
|---|---|
| `_Reference<n>`, `_Document<n>`, `_Enum<n>`, `_Chrc<n>`, `_Acc<n>`, `_Node<n>`, `_Task<n>`, `_BPr<n>` | справочник, документ, перечисление, ПВХ, план счетов, план обмена, задача, бизнес-процесс |
| `<префикс><n>_VT<k>` | табличная часть |
| `_InfoRg<n>`, `_InfoRgSL<n>`, `_InfoRgSF<n>` | регистр сведений, срезы последних/первых |
| `_AccumRg<n>`, `_AccumRgT<n>`, `_AccumRgTn<n>` | движения, остатки, обороты регистра накопления |
| `_AccRg<n>`, `_AccRgAT…` | регистр бухгалтерии и итоги (имена итогов в статьях ИТС расходятся) |
| `…ChngR<n>` | регистрация изменений для обмена |
| `_YearOffset` | смещение дат (только MS SQL) |

Источник — `../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md` (ИТС 1798). Номера `<n>` — только из своей базы: `ПолучитьСтруктуруХраненияБазыДанных()`, размеры с 8.3.15 — `ПолучитьРазмерДанныхБазыДанных()` [`../its-metod/sbor-dannyh-…`]. От `hobt_id`/`object_id` к таблице — D-08, D-09.

## 3. Статистика ожиданий

### 3.1. Устройство и способы снятия

- Колонки `sys.dm_os_wait_stats`: `wait_type`, `waiting_tasks_count` (растёт в начале ожидания), `wait_time_ms` (с сигнальным), `max_wait_time_ms`, `signal_wait_time_ms`; не сохраняется при перезапуске (старт — `sqlserver_start_time` в `sys.dm_os_sys_info`); сброс — `DBCC SQLPERF ('sys.dm_os_wait_stats', CLEAR);` [MS Learn; ИТС-мет 6008]. Сбрасывать без нужды не стоит — лучше дельта [практика].
- По сеансу — `sys.dm_exec_session_wait_stats` (2016+; сбрасывается при открытии сеанса и сбросе соединения пулом) [MS Learn]; по запросам во времени — Query Store (2017+) [MS Learn].

| Задача | Запрос |
|---|---|
| Картина с момента старта | D-02 (по 6008, без «безопасных») |
| Что сейчас (окно 1–5 мин) | D-03 |
| Чего ждёт сеанс 1С | D-04 |
| Какие запросы чего ждут за сутки | D-32 |
| Чего ждут выполняющиеся запросы | D-05 |

### 3.2. Типовые ожидания под 1С

| Ожидание | Смысл | Типичная причина в 1С → действие | Источник |
|---|---|---|---|
| `LCK_M_X`, `LCK_M_U`, `LCK_M_IX` | ждёт монопольную/обновления/намерения блокировку | конкурирующая запись регистров, долгие транзакции → раздел 5 | [MS Learn; ИТС-мет 6008] |
| `LCK_M_S`, `LCK_M_IS` | ждёт разделяемую | чтение в транзакции в автоматическом режиме → управляемые блокировки | [MS Learn; ИТС-разр гл. 9] |
| `LCK_M_RS_S`, `LCK_M_RS_U`, `LCK_M_RIn_NL`, `LCK_M_RX_X` | блокировки диапазонов ключей | `SERIALIZABLE` → автоматический режим, «ДЛЯ ИЗМЕНЕНИЯ» со сканированием → 6.4 | [MS Learn; ИТС-мет 4051 — конспект, 1.6] |
| `LCK_M_SCH_M`, `LCK_M_SCH_S` | блокировки схемы | реструктуризация, перестроение индексов днём → регламент ночью | [MS Learn] |
| `LCK_M_S_XACT*` | блокировка транзакции при оптимизированной блокировке | только 2025 с `OPTIMIZED_LOCKING = ON` (требует ADR) → для 1С не включать | [MS Learn] |
| `PAGEIOLATCH_SH`, `_EX` | латч буфера, читаемого/пишущего на диск | тяжёлые чтения, мало памяти, медленный диск `.mdf` → D-15, 10.1, 10.3 | [MS Learn; ИТС-мет 6008] |
| `WRITELOG` | ждёт сброса журнала (фиксация, контрольная точка) | медленный диск `.ldf`, частые мелкие транзакции → журнал 1–5 мс | [MS Learn; ИТС-мет 6008] |
| `LOGBUFFER` | нет места в буфере журнала | следствие `WRITELOG`, сервер «встаёт» на сброс | [MS Learn; ИТС-мет 6008] |
| `IO_COMPLETION` | ввод-вывод не страниц данных | сортировки на диске, создание базы, трассировки | [MS Learn; ИТС-мет 6008] |
| `ASYNC_IO_COMPLETION` | асинхронный ввод-вывод не данных | MS: доставка журналов, зеркалирование, массовые операции; 1С: частый рост журнала | [MS Learn; ИТС-мет 6008] |
| `PREEMPTIVE_OS_WRITEFILEGATHER` | долгое автоувеличение файла с обнулением | рост журнала (до 2019 IFI на журнал не действует; с 2022 — только на приросты до 64 МБ) или данных без IFI | [MS Learn — статья об IFI; ИТС-мет 6008] |
| `CXPACKET`, `CXCONSUMER`; с 2022 `CXSYNC_PORT`, `CXSYNC_CONSUMER` | синхронизация потоков параллельного плана | `MAXDOP = 0` → `1`, затем первопричина (фрагментация, диск у «отстающего» потока) | [MS Learn; ИТС-мет 6008; 5904] |
| `SOS_SCHEDULER_YIELD` | задача ждёт нового кванта CPU | сканирования, регрессия плана, нет индекса, устаревшая статистика → D-14, D-30 | [MS Learn] |
| `THREADPOOL` | нет свободного рабочего потока | очень долгие пакеты, массовые блокировки → устранить; в аварии — DAC | [MS Learn] |
| `RESOURCE_SEMAPHORE` | ждёт грант памяти | сортировки/хеши отчётов при нехватке памяти; ошибка 8645 → D-19, D-20 | [MS Learn; ИТС-мет 6008] |
| `RESOURCE_SEMAPHORE_QUERY_COMPILE` | предел одновременных компиляций | много компиляций, некешируемые планы | [MS Learn] |
| `ASYNC_NETWORK_IO` | клиент не забирает результат | `rphost` медленно выбирает большой результат или сеть → проверить канал, затем сторону 1С | [MS Learn; ИТС-мет 6008] |
| `PAGELATCH_UP`, `_EX` | латч страницы в памяти | tempdb `2:1:1` (PFS), `2:1:2` (GAM), `2:1:3` (SGAM) → равные файлы tempdb (10.4) | [MS Learn] |
| `LATCH_EX`, `LATCH_SH` | латчи внутренних структур | детализация — `sys.dm_os_latch_stats` | [MS Learn; ИТС-мет 6008] |
| `CMEMTHREAD` | конкуренция за объект памяти | частые компиляции; флаг 8048 с 2016 не нужен | [MS Learn; ИТС-мет 5946] |
| `WAIT_ON_SYNC_STATISTICS_REFRESH` | ждёт синхронное обновление статистики (2019+) | крупные таблицы; 1С советует асинхронное автообновление [ИТС-мет 5904] | [MS Learn] |
| `HADR_SYNC_COMMIT` | фиксация ждёт синхронную реплику AG | Always On → `07-…` | [MS Learn] |

Для дисковых ожиданий (`PAGEIOLATCH_*`, `WRITELOG`, `ASYNC_IO_COMPLETION`) среднее на ожидание должно быть ниже 10–15 мс [MS Learn] — колонка `avg_ms` в D-02/D-03.

### 3.3. «Безопасные» ожидания

Не означают проблему фоновые ожидания из перечня [ИТС-мет 6008] — полный список вшит в D-02: `SLEEP_*`, `LAZYWRITER_SLEEP`, `XE_TIMER_EVENT`, `XE_DISPATCHER_WAIT`, `REQUEST_FOR_DEADLOCK_SEARCH`, `CHECKPOINT_QUEUE`, `LOGMGR_QUEUE`, `DIRTY_PAGE_POLL`, `SQLTRACE_*`, `BROKER_*`, `DBMIRROR*`, `HADR_*` (часть), `QDS_*_SLEEP`, `WAITFOR` и др. Microsoft отдельно: `LAZYWRITER_SLEEP` не учитывать при поиске пользовательских задержек [MS Learn]. Незнакомое ожидание с огромным временем и описанием «Internal use only» — сначала проверить в описании `sys.dm_os_wait_stats` [практика].

### 3.4. Activity Monitor по методике 6008

1. SSMS → правой кнопкой по серверу → Activity Monitor; период обновления — в группе Overview [ИТС-мет 6008].
2. **Overview**: проблему показывают значения на графике **Waiting Tasks** [ИТС-мет 6008].
3. **Resource Waits**: сортировать по **Average Waiter Count**; `Wait Time (ms/sec)`, `Cumulative Wait Time (sec)` [ИТС-мет 6008].
4. **Processes**: фильтр `Wait Type` = `(NonBlanks)`; `Task State` — `running`, `runnable` (очередь к CPU), `suspended` (ждёт ресурс), `pending` (ждёт поток), `background`, `rollback`, `dormant`; по правой кнопке — текст запроса или завершение [ИТС-мет 6008]; **Blocked By** — кто блокирует [MS Learn].
5. **Data File I/O** — нагрузка по файлам [ИТС-мет 6008].

Категории Resource Waits укрупнены ⚠ — точный тип даёт D-03.

## 4. Текущие сеансы и запросы

### 4.1. Представления

| Представление | Строка на | Ключевые колонки | Источник |
|---|---|---|---|
| `sys.dm_exec_sessions` | сеанс (и спящий) | `status` (`Running`/`Sleeping`/`Dormant`/`Preconnect`), `open_transaction_count` (2012+), `transaction_isolation_level`, `lock_timeout`, `host_name`, `program_name`, `login_name`, `cpu_time`, `logical_reads`, `last_request_start_time`, `last_request_end_time` | [MS Learn] |
| `sys.dm_exec_requests` | выполняющийся запрос | `status` (`running`, `runnable`, `suspended`, `sleeping`, `background`, `rollback`), `command`, `blocking_session_id`, `wait_type`, `wait_time` (мс), `wait_resource`, `last_wait_type`, `open_transaction_count`, `cpu_time`, `total_elapsed_time`, `logical_reads`, `granted_query_memory` (страницы), `dop` (2016+), `percent_complete`, `sql_handle`, `plan_handle`, `statement_start_offset`/`_end_offset`, `query_hash` | [MS Learn] |
| `sys.dm_exec_connections` | соединение | `client_net_address`, `net_transport`, `encrypt_option`, `auth_scheme`, `last_read`, `last_write`, `most_recent_sql_handle` (последний запрос — для спящего блокировщика) | [MS Learn] |
| `sys.dm_os_waiting_tasks` | ждущая задача | `wait_type`, `wait_duration_ms`, `blocking_session_id` (`-2` — осиротевшая распределённая транзакция, `-3` — отложенное восстановление, `-4` — владелец латча не определён), `resource_description` | [MS Learn] |

`sp_who` (документирована, колонка `blk`) и `sp_who2` (недокументирована) Microsoft называет старыми — основой служит `sys.dm_exec_sessions` [MS Learn]. Последний оператор сеанса — `DBCC INPUTBUFFER(<spid>)` или `sys.dm_exec_input_buffer(<spid>, NULL)` (2014 SP2+) [MS Learn]. Снимок «сейчас» — D-05; сеансы с открытой транзакцией — D-06.

### 4.2. Текст, план и прогресс

| Нужно | Средство | Версия | Источник |
|---|---|---|---|
| Текст оператора | `sys.dm_exec_sql_text(sql_handle)` + вырезка по `statement_start_offset`/`_end_offset` (байты; Unicode — делить на 2) | все | [MS Learn] |
| Кешированный план | `sys.dm_exec_query_plan(plan_handle)`; по оператору — `sys.dm_exec_text_query_plan(plan_handle, start, end)` | все | [MS Learn] |
| «Живой» план | `sys.dm_exec_query_statistics_xml(session_id)` | 2016 SP1+ | [MS Learn] |
| Прогресс по операторам | `sys.dm_exec_query_profiles`; облегчённое профилирование включено по умолчанию с 2019 (на 2016 SP1–2017 — флаг 7412), отключается `LIGHTWEIGHT_QUERY_PROFILING = OFF` | 2014 SP2+ | [MS Learn] |
| Последний фактический план | `sys.dm_exec_query_plan_stats(plan_handle)` при `ALTER DATABASE SCOPED CONFIGURATION SET LAST_QUERY_PLAN_STATS = ON;` | 2019+ | [MS Learn] |
| Прогресс обслуживания | `percent_complete` (`BACKUP`, `DBCC CHECKDB`, `ALTER INDEX REORGANIZE`, откат и др.) | все | [MS Learn] |

Облегчённое профилирование Microsoft допускает держать постоянно на сервере, который не упирается в CPU [MS Learn]; `LAST_QUERY_PLAN_STATS` — на время расследования ⚠ (нагрузка для 1С не оценена).

### 4.3. `sp_WhoIsActive` и First Responder Kit [сторонний]

- **`sp_WhoIsActive`** (GitHub `amachanic/sp_whoisactive`, GPLv3; SQL Server 2005–2022 и Azure SQL DB; для 2012–2019 — скрипт из папки `2019`, для 2008 — из `2008`; версия на 20.10.2026 — `v2200.20260409`) [сторонний]. Параметры (сверены с текстом процедуры): `@find_block_leaders`, `@get_locks`, `@get_plans`, `@get_transaction_info`, `@get_additional_info`, `@get_task_info`, `@get_memory_info`, `@show_sleeping_spids` (по умолчанию `1`), `@delta_interval`, `@destination_table`, `@filter`/`@filter_type`, `@sort_order`, `@help` [сторонний].

```sql
EXEC sp_WhoIsActive @find_block_leaders = 1, @get_locks = 1, @get_transaction_info = 1,
                    @sort_order = '[blocked_session_count] DESC';   -- колонка допустима для сортировки (Подтверждено 20.10.2026 по тексту процедуры)
EXEC sp_WhoIsActive @delta_interval = 5, @get_plans = 1;            -- что грузит CPU/диск сейчас
```

- **First Responder Kit** (Brent Ozar Unlimited, MIT; все поддерживаемые Microsoft версии и SQL Server на Linux; установка — `Install-All-Scripts.sql` в `master`): `sp_BlitzFirst` (снимок DMV, пауза `@Seconds` = 5, повторный снимок, приоритетный список причин; `@ExpertMode = 1` — ожидания, счётчики, файлы, `sp_BlitzWho`), `sp_BlitzWho`, `sp_BlitzCache`, `sp_BlitzLock` (разбор взаимоблокировок из `system_health` или своего сеанса — `@EventSessionPath`) [сторонний].

Ставятся в `master` — по согласованию с политикой; в базах ИБ ничего не создавать [практика].

### 4.4. Снятие «зависшего» запроса: консоль 1С или `KILL`

1. **Сначала консоль кластера.** При долгом запросе к MS SQL сервер 1С пытается разорвать соединение; успех зависит от прав логина СУБД; пользователь увидит «Сеанс работы завершен администратором»; разрыв активно работающего пользователя может привести к потере данных; не разрывается, пока вызов стоит на строке не в СУБД (COM, HTTP) [ИТС-КС разд. 5.2.12.3].
2. **`KILL <session_id>`** — если консоль не помогла; нужен `ALTER ANY CONNECTION`; откат большой транзакции долог, прогресс — `KILL <session_id> WITH STATUSONLY` (ничего не прерывает) [MS Learn]. Осиротевшая распределённая транзакция (`-2`) — `KILL '<UOW>'` с GUID из `request_owner_guid` в `sys.dm_tran_locks` [MS Learn].

> ⚠ **Перед `KILL`** убедитесь (D-07), что это головной блокирующий, а не жертва; запишите номер и время начала сеанса 1С и последний оператор (`sys.dm_exec_input_buffer`) — иначе причину не найти [ИТС-мет 5813; 5861]. Сеанс в `rollback` убивать бесполезно [MS Learn]. Прерывание реструктуризации или загрузки `.dt` оставит базу в промежуточном состоянии — нужна свежая резервная копия (`04-…`) [практика].

## 5. Блокировки и цепочки блокировок

### 5.1. Что блокирует 1С на MS SQL

- **Управляемый режим** (рекомендован): Read Committed Snapshot — чтения не ставят разделяемых блокировок, конфликтуют записи; согласованность обеспечивают управляемые блокировки платформы, на SQL Server не видимые [ИТС-разр гл. 9, разд. 9.2.3.2]; их ожидания — в техжурнале `TLOCK`/`TTIMEOUT`/`TDEADLOCK` [ИТС-адм прил. 3, разд. 3.24.2.3].
- **Автоматический режим**: Repeatable Read/Serializable — разделяемые блокировки до конца транзакции, при Serializable — и на диапазоны ключей; при пустой таблице блокируется вся таблица [ИТС-разр гл. 9, разд. 9.2.3.2; `../its-metod/ekspluataciya-krupnoj-sistemy-blokirovki-tranzakcii.md`, п. 19].
- **Эскалация SQL Server**: инструкция с ≥ 5000 блокировок на одну ссылку на таблицу (проверка каждые 1250 новых) может укрупнить их до таблицы/секции [MS Learn]; 1С рекомендует флаг 1224 (по количеству) или 1211 (полностью) [ИТС-мет 5946, 2019]; 1211 может исчерпать память блокировок [MS Learn]. Своя эскалация платформы — свыше 100 000 управляемых блокировок на пространство [ИТС-разр гл. 9, разд. 9.2.3.6].
- **Страничные блокировки индексов 1С выключены с 8.3.22** [ИТС-мет 5837, 2022] — ожидайте в `sys.dm_tran_locks` ресурсы `KEY`/`RID`/`OBJECT`, а не `PAGE` ⚠ (вывод, не проверен).

### 5.2. Головной блокирующий часто «спит»

Методика Microsoft: найти головной сеанс цепочки и понять, почему он держит блокировки [MS Learn]. Сценарии статьи поддержки Microsoft применительно к 1С:

| Сценарий [MS Learn] | Признаки | В 1С [практика] | Разрешится сам |
|---|---|---|---|
| Долгий запрос держит блокировки | `running`/`runnable`/`suspended`, большой `cpu_time`/`logical_reads` | тяжёлый запрос проведения/отчёта в транзакции | да |
| Спящий сеанс с незафиксированной транзакцией | `sleeping`, `open_transaction_count > 0`, `wait_type` пуст | `rphost` исполняет код внутри транзакции (циклы, COM/HTTP, ожидание управляемой блокировки) | когда 1С завершит транзакцию |
| Клиент не дочитал результат | `runnable`, `ASYNC_NETWORK_IO` | `rphost` медленно выбирает большой результат | когда дочитает/закроет |
| Сеанс в откате | `status = rollback` | откат после ошибки или `KILL` | да — ждать (`KILL … WITH STATUSONLY`) |
| Осиротевшая транзакция | `last_request_start_time` давно, сон с открытой транзакцией | упал `rphost`/сервер 1С | со временем, иначе `KILL` |

Правила: строить поиск от `sys.dm_exec_sessions`, текст спящего — по `most_recent_sql_handle` или `sys.dm_exec_input_buffer` [MS Learn] (D-07); последний оператор спящего — не обязательно тот, что поставил блокировку, полную картину даёт трассировка XE по сеансу или техжурнал `DBMSSQL` + `SDBL` [MS Learn; ИТС-мет 6006 — конспект, 2.4.3]. Обрыв соединения без уведомления SQL Server обнаруживает средствами TCP — по [ИТС-мет 2374, 2008] до 2 часов ⚠ (для современных версий не перепроверено).

### 5.3. Что заблокировано: `wait_resource`

| Тип | `resource_description` / `wait_resource` | Как найти таблицу |
|---|---|---|
| `KEY` | хеш ключа; `KEY: <dbid>:<hobt_id> (<hash>)` | `sys.partitions.hobt_id` → `object_id`, `index_id` |
| `RID` | `<file>:<page>:<row>` | `hobt_id` (не всегда) |
| `PAGE` | `<file>:<page>`; `PAGE: <dbid>:<file>:<page>` | `hobt_id` или `sys.dm_db_page_info` (2019+) |
| `OBJECT` | — | `resource_associated_entity_id` = `object_id` |
| `XACT` | `<dbid>:<XdesId low>:<XdesId high>` | только оптимизированная блокировка (2025) |

`request_status`: `GRANTED`, `CONVERT`, `WAIT`, `LOW_PRIORITY_CONVERT`, `LOW_PRIORITY_WAIT`, `ABORT_BLOCKERS` [MS Learn]. Запросы — D-08 (в контексте базы ИБ), D-09; таблица → объект 1С — 2.6. `DBCC PAGE` из методики 1С [ИТС-мет 6006 — конспект, 2.4.7] недокументирована Microsoft (Подтверждено 20.10.2026: в каталоге DBCC справочника MS Learn страницы нет) — на 2019+ лучше `sys.dm_db_page_info` [MS Learn].

### 5.4. Длинные транзакции

- `sys.dm_tran_active_transactions` (`transaction_begin_time`, `transaction_type`, `transaction_state`), `sys.dm_tran_session_transactions` (связь с `session_id`), `sys.dm_tran_database_transactions` (по базе: `database_transaction_log_record_count`, `…_log_bytes_used`/`_reserved`) [MS Learn] — D-10; развёрнутый запрос с планом и расшифровкой `transaction_type` (1 чтение-запись, 2 только чтение, 3 системная, 4 распределённая) и `transaction_state` (0–8) — в [ИТС-мет 5813, 2015].
- `DBCC OPENTRAN ('buh')` — старейшая активная транзакция базы [MS Learn].
- Долгая транзакция держит блокировки, не даёт усекать журнал (`log_reuse_wait_desc = ACTIVE_TRANSACTION` — `04-…`) и чистить хранилище версий в tempdb (D-11) [MS Learn; ИТС-мет 2374]. Счётчик `Transactions\Longest Transaction Running Time` работает только при RCSI/snapshot — для баз 1С в управляемом режиме годится [MS Learn].

### 5.5. Blocked process report

- `blocked process threshold` — 5…86 400 с; монитор просыпается раз в 5 с (меньше 5 с не ловится); отчёт — раз в интервал для каждой заблокированной задачи, «на лучших усилиях»; не для системных задач и не детектируемых ресурсов; без перезапуска; по умолчанию отчётов нет [MS Learn].
- Для 1С — порог чуть меньше «Времени ожидания блокировки данных» ИБ, например 10 с (методика 1С использует 10) [ИТС-мет 6006 — конспект, 2.4.6; практика].

```sql
-- от имени sysadmin
EXEC sp_configure 'show advanced options', 1;  RECONFIGURE;
EXEC sp_configure 'blocked process threshold', 10;  RECONFIGURE;
SELECT name, value_in_use FROM sys.configurations WHERE name LIKE N'blocked process threshold%';
-- после расследования: EXEC sp_configure 'blocked process threshold', 0;  RECONFIGURE;   -- 0 — умолчание, отчётов нет
-- (Уточнено 20.10.2026 по MS Learn, server-configuration-options: умолчание 0; в таблице там же минимум указан 5)
```

Сеанс XE — 7.3, разбор — D-13 (структура XML `blocked-process`/`blocking-process` — по практике ⚠). Отчёты есть также в `sp_server_diagnostics` (`/queryProcessing/blockingTasks/blocked-process-report`) [MS Learn]; `system_health` пишет сеансы, ждавшие блокировку > 30 с и латчи > 15 с [MS Learn].

### 5.6. Эскалация, таймауты, `<dbmslocks/>`

- Эскалации — XE `lock_escalation` (7.5) [MS Learn]; флаги — `DBCC TRACESTATUS(-1);` [ИТС-мет 5946]; при 1224 эскалация всё равно возможна при нехватке памяти блокировок (40 % памяти Database Engine при `locks = 0`) [MS Learn]. Кто держит много блокировок: `SELECT request_session_id, resource_type, COUNT(*) FROM sys.dm_tran_locks GROUP BY request_session_id, resource_type ORDER BY 3 DESC;` — на нагруженном сервере выполнять кратко [MS Learn; практика].

| Ошибка | Где | Как распознать | Куда смотреть |
|---|---|---|---|
| 1222 «Lock request time out period exceeded» | SQL Server, `LOCK_TIMEOUT` сеанса: оператор отменяется, транзакция не откатывается | `EXCP` с текстом провайдера; `Lock Timeouts/sec` | этот раздел, D-07, 5.5 |
| превышение времени ожидания управляемой блокировки | менеджер блокировок 1С | `TTIMEOUT`, `WaitConnections` | `../its-metod/vzaimoblokirovki-…`, 2.3 |
| 1205 (жертва взаимоблокировки) | SQL Server | `EXCP` + `xml_deadlock_report` | раздел 6 |
| взаимоблокировка управляемых блокировок | менеджер 1С | `TDEADLOCK`, `DeadlockConnectionIntersections` | `../its-metod/vzaimoblokirovki-…` |

Источники таблицы: [ИТС-адм прил. 3, разд. 3.24.2.3, 3.24.2.4.2]; [MS Learn]; [`../its-metod/sbor-dannyh-…`, 1.15].

**`<dbmslocks/>`** в `logcfg.xml`: при обращениях к СУБД (не чаще раза в 2 с, одним рабочим процессом) запрашивается «кто кого заблокировал»; к очередному завершённому событию потока добавляются `lka='1'` (источник), `lkp='1'` (жертва), `lkpid` (номер запроса — у жертвы), `lkaid` (список номеров — у источника), `lksrc` (соединение источника), `lkpto`/`lkato` (секунды с обнаружения). Анализ: первое событие с `lka`/`lkp` → взять `lkaid`/`lkpid` → найти события с этими номерами во всех журналах `rphost` [ИТС-адм прил. 3, разд. 3.24.5]. Это связывает блокировку СУБД со стеком 1С без ручного сопоставления (шаблон 12.2 Г).

## 6. Взаимоблокировки

### 6.1. Механизм

- Монитор ищет циклы раз в 5 с, при найденных — до 100 мс, затем снова до 5 с [MS Learn].
- Жертва — транзакция, которую дешевле откатить, при равном `DEADLOCK_PRIORITY` (по умолчанию `NORMAL` = 0); иначе — с меньшим приоритетом; жертве — откат и ошибка 1205 «Transaction (Process ID …) was deadlocked on {lock | communication buffer | thread} resources … chosen as the deadlock victim» [MS Learn].
- «…thread communication buffer…» и «Intra-query parallelism…» — потоки одного параллельного запроса; решение — `MAXDOP = 1` или оптимизация запроса [ИТС-мет 5834, 2015].
- `Locks\Number of Deadlocks/sec` должен быть 0 [ИТС-мет 2923, 2008; MS Learn].

### 6.2. Граф из `system_health`

- `system_health` включён по умолчанию, без заметных накладных расходов; не останавливать и не менять (может перезаписаться обновлением) [MS Learn].
- Пишет: взаимоблокировки с графом (`xml_deadlock_report`); ожидания блокировок > 30 с и латчей > 15 с; ошибки severity ≥ 20 и ошибки памяти (701, 802, 8645…); 17883; результаты `sp_server_diagnostics` [MS Learn].
- Цели: кольцевой буфер и файл (файл — 5 МБ × 4, в Standard/Enterprise — 100 МБ × 10); файлы — в `…\MSSQL\Log`, читаются `sys.fn_xe_file_target_read_file('system_health*.xel', NULL, NULL, NULL)`, `timestamp_utc` — с 2017 [MS Learn]. На Express история может уйти за часы — свой сеанс 7.3 [практика].
- Методика сбора данных 1С: для MS SQL 2012+ — `xml_deadlock_report`, для 2008 и старше — Profiler «Deadlock graph» [`../its-metod/sbor-dannyh-…`, 1.14].

Разбор — D-12; из кольцевого буфера — запрос Microsoft:

```sql
SELECT xdr.value('@timestamp', 'datetime') AS deadlock_time, xdr.query('.') AS event_data
FROM (SELECT CAST(xt.target_data AS xml) AS target_data
      FROM sys.dm_xe_session_targets AS xt
      JOIN sys.dm_xe_sessions AS xs ON xs.address = xt.event_session_address
      WHERE xs.name = N'system_health' AND xt.target_name = N'ring_buffer') AS XML_Data
CROSS APPLY target_data.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS XEventData(xdr)
ORDER BY deadlock_time DESC;   -- [MS Learn]
```

Визуально: SSMS → Management → Extended Events → `system_health` → `event_file` → View Target Data → событие → вкладка графа; сохранить `.xdl` [MS Learn; практика].

### 6.3. Чтение графа для 1С

Узлы `victim-list`, `process-list`, `resource-list` [MS Learn]. Атрибуты `process` (по образцу Microsoft): `spid`, `waitresource`, `waittime`, `lockMode`, `transactionname`, `trancount`, `isolationlevel` (`read committed (2)`), `clientapp`, `hostname`, `loginname`, `currentdb`, `lockTimeout`; `executionStack` и `inputbuf`; ресурсы `keylock`/`pagelock`/`objectlock` с `objectname`, `indexname`, `mode`, `owner-list`/`waiter-list` [MS Learn].

Порядок [практика, по методике `vzaimoblokirovki…` и MS Learn]: таблицы → объекты 1С (2.6); `isolationlevel` `serializable (4)`/`repeatable read (3)` — автоматический режим, `read committed (2)` — управляемый; режимы: оба взяли `S`/`U` и хотят `X` на тот же ключ — «повышение уровня», каждый держит `X` и ждёт чужую — «разный порядок» [ИТС-мет 4051 — конспект, 1.3–1.4]; `hostname`/`spid`/время → техжурнал (`Dbpid`, `Context`) → строки кода обеих сторон.

### 6.4. Типовые причины и что делать

| Причина | Условия | Что делать | Источник |
|---|---|---|---|
| Повышение уровня блокировки | чтение (без «ДЛЯ ИЗМЕНЕНИЯ» / без управляемой исключительной блокировки), затем запись тех же данных | блокировать до чтения | [ИТС-мет 4051, 2025 — конспект, 1.3] |
| Разный порядок захвата | транзакции пишут те же регистры в разной последовательности | единый порядок, предварительные блокировки | там же, 1.4 |
| Особенность MS SQL: два запроса | автоматический режим + «ДЛЯ ИЗМЕНЕНИЯ» + сканирование | управляемый режим; без «ДЛЯ ИЗМЕНЕНИЯ»; поиск по индексу | там же, 1.6 |
| Параллелизм | «Intra-query parallelism…» | `MAXDOP = 1`, оптимизация | [ИТС-мет 5834] |
| Неоптимальный запрос | сканирование вместо поиска | индексы, статистика, текст | [ИТС-мет 4051 — конспект, 1.5] |

Общие меры Microsoft — единый порядок доступа, никаких ожиданий пользователя в транзакции, короткие транзакции, низкие уровни изоляции и версии строк [MS Learn] (для 1С — управляемый режим). Взаимоблокировки после обновления конфигурации — сравнить планы в Query Store (8.4) [практика].

`TDEADLOCK` в техжурнале — взаимоблокировка менеджера управляемых блокировок 1С; на SQL Server и в `system_health` её нет [ИТС-адм прил. 3, разд. 3.24.2.3]. Флаги 1204/1222 пишут сведения в журнал ошибок, но на нагруженных системах Microsoft советует `xml_deadlock_report` [MS Learn]. `sp_BlitzLock` [сторонний] разбирает XML взаимоблокировок в таблицу.

## 7. Extended Events: готовые сессии для 1С

### 7.1. Минимум теории

- `CREATE EVENT SESSION … ON SERVER ADD EVENT <пакет>.<событие> (ACTION(…) WHERE …) ADD TARGET package0.event_file (SET filename = N'…\name.xel', max_file_size = <МБ>, max_rollover_files = <N>) WITH (…)` [MS Learn].
- Параметры: `MAX_MEMORY` (по умолчанию 4 МБ), `EVENT_RETENTION_MODE` (`ALLOW_SINGLE_EVENT_LOSS` | `ALLOW_MULTIPLE_EVENT_LOSS` | `NO_EVENT_LOSS`), `MAX_DISPATCH_LATENCY` (по умолчанию 30 с), `MAX_EVENT_SIZE`, `TRACK_CAUSALITY`, `STARTUP_STATE` (`ON` — старт при следующем запуске службы; сейчас — `ALTER EVENT SESSION … STATE = START`); `MAX_DURATION` — только 2025 и Azure [MS Learn].
- `event_file`: к имени добавляется метка времени; **`MAX_ROLLOVER_FILES` по умолчанию `UNLIMITED`** — задавайте всегда [MS Learn].
- Предикат: `WHERE sqlserver.session_id = 59 AND duration > 0` (пример Microsoft) — фильтровать как можно строже [MS Learn; практика].
- Действия из документации Microsoft: `sqlserver.sql_text`, `session_id`, `database_id`, `database_name`, `client_app_name`, `client_pid`, `username`, `nt_username`, `query_hash_signed`, `query_plan_hash_signed`, `plan_handle`, `transaction_id`; `sqlos.task_time` [MS Learn]. `sqlserver.client_hostname` — Подтверждено 20.10.2026 (пример `CREATE EVENT SESSION` в статье MS Learn selects-and-joins-from-system-views-for-extended-events). `client_pid` — аналог колонки трассировки `ClientProcessID` [MS Learn, convert-an-existing-sql-trace-script].
- События для 1С (статья поддержки Microsoft о блокировках): `rpc_completed`, `rpc_starting`, `sql_batch_completed`, `sql_batch_starting`, `attention`, `blocked_process_report`, `error_reported`, `exchange_spill`, `execution_warning`, `hash_warning`, `missing_column_statistics`, `missing_join_predicate`, `sort_warning`, `lock_deadlock`, `login`, `logout`; `xml_deadlock_report`, `lock_escalation` — в руководствах по взаимоблокировкам и блокировкам [MS Learn].
- Проверка объектов в своей версии:

```sql
SELECT p.name AS package, o.name, o.object_type        -- event, action, target, pred_source…
FROM sys.dm_xe_objects AS o JOIN sys.dm_xe_packages AS p ON p.guid = o.package_guid
WHERE o.name IN (N'rpc_completed', N'sql_batch_completed', N'blocked_process_report', N'client_hostname', N'database_name');
SELECT name, type_name FROM sys.dm_xe_object_columns WHERE object_name = N'rpc_completed' AND column_type = N'data';
```

- Управление: `ALTER EVENT SESSION [имя] ON SERVER STATE = START | STOP;`, `DROP EVENT SESSION [имя] ON SERVER;`; работающие — `sys.dm_xe_sessions` (`create_time`, `dropped_event_count` — потерянные события, `total_bytes_generated`) [MS Learn]. В SSMS — мастер New Session, Watch Live Data, XEvent Profiler [MS Learn].

### 7.2. Сессия 1: долгие запросы базы 1С

Замена трассировки `RPC:Completed` + `SQL:BatchCompleted` из методики 5910 и «узкого» сбора 5861/5813:

```sql
-- от имени sysadmin; каталог E:\XE должен существовать
CREATE EVENT SESSION [1c_long_queries] ON SERVER
ADD EVENT sqlserver.rpc_completed (
    ACTION (sqlserver.session_id, sqlserver.database_name, sqlserver.client_app_name,
            sqlserver.client_pid, sqlserver.query_hash_signed, sqlserver.sql_text)
    WHERE (sqlserver.database_name = N'buh' AND duration >= 1000000)),     -- 1 с, мкс ⚠
ADD EVENT sqlserver.sql_batch_completed (
    ACTION (sqlserver.session_id, sqlserver.database_name, sqlserver.client_app_name,
            sqlserver.client_pid, sqlserver.query_hash_signed, sqlserver.sql_text)
    WHERE (sqlserver.database_name = N'buh' AND duration >= 1000000))
ADD TARGET package0.event_file (SET filename = N'E:\XE\1c_long_queries.xel',
                                max_file_size = 256, max_rollover_files = 8)
WITH (MAX_MEMORY = 8 MB, EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS,
      MAX_DISPATCH_LATENCY = 30 SECONDS, STARTUP_STATE = OFF);
GO
ALTER EVENT SESSION [1c_long_queries] ON SERVER STATE = START;
SELECT name, create_time FROM sys.dm_xe_sessions WHERE name = N'1c_long_queries';   -- проверка
```

- `duration` у событий завершения — микросекунды по примеру Microsoft (`sql_statement_completed`: `duration` 111021 при `cpu_time` 109000) [MS Learn] ⚠ — для `rpc_completed`/`sql_batch_completed` сверьте `sys.dm_xe_object_columns`. Загрузчик XE методики 1С считает `StartTime` как `DATEADD(millisecond, -Duration, EndTime)` [ИТС-мет 6006 — конспект, 2.4.6] — при микросекундах время начала уедет ⚠.
- `sqlserver.database_name` как источник предиката — ⚠ (проверка выше); надёжнее `sqlserver.database_id = <DB_ID('buh')>` [практика].
- Поля из загрузчика 1С: `duration`, `physical_reads`, `writes`, `cpu_time`; `logical_reads` ⚠ [ИТС-мет 6006 — конспект].
- Без порога (для 5910) — только окно 15–20 минут [ИТС-мет 5910] с ручной остановкой.

### 7.3. Сессия 2: блокировки и взаимоблокировки

Требует `blocked process threshold` (5.5).

```sql
CREATE EVENT SESSION [1c_blocking] ON SERVER
ADD EVENT sqlserver.blocked_process_report (ACTION (sqlserver.database_name)),
ADD EVENT sqlserver.xml_deadlock_report   (ACTION (sqlserver.database_name))
ADD TARGET package0.event_file (SET filename = N'E:\XE\1c_blocking.xel',
                                max_file_size = 128, max_rollover_files = 10)
WITH (MAX_MEMORY = 4 MB, EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS,
      MAX_DISPATCH_LATENCY = 15 SECONDS, STARTUP_STATE = ON);
GO
ALTER EVENT SESSION [1c_blocking] ON SERVER STATE = START;
```

`blocked_process_report` формирует системный поток монитора (в классе трассировки `IsSystem = 1`) [MS Learn] — действия вроде `sql_text` относятся к нему, полезные данные — внутри XML отчёта (D-13) [практика]. `xml_deadlock_report` здесь хранится дольше, чем в `system_health` [практика].

### 7.4. Сессия 3: ошибки и отмены

```sql
CREATE EVENT SESSION [1c_errors] ON SERVER
ADD EVENT sqlserver.error_reported (
    ACTION (sqlserver.session_id, sqlserver.database_name, sqlserver.client_app_name, sqlserver.sql_text)
    WHERE (severity >= 16 AND sqlserver.database_name = N'buh')),            -- поле severity ⚠
ADD EVENT sqlserver.attention (
    ACTION (sqlserver.session_id, sqlserver.database_name, sqlserver.client_app_name, sqlserver.sql_text)
    WHERE (sqlserver.database_name = N'buh'))
ADD TARGET package0.event_file (SET filename = N'E:\XE\1c_errors.xel', max_file_size = 64, max_rollover_files = 5)
WITH (EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS, STARTUP_STATE = OFF);
```

`attention` — отмена запроса клиентом или тайм-аут; в сценарии «спящий сеанс с открытой транзакцией» указывает на отменённый запрос, после которого транзакция осталась [MS Learn]. Основные ошибки для 1С: 1205, 1222, 8645 [MS Learn].

### 7.5. Сессия 4: эскалации (пример Microsoft)

```sql
CREATE EVENT SESSION [Track_lock_escalation] ON SERVER
ADD EVENT sqlserver.lock_escalation (
    SET collect_database_name = 1, collect_statement = 1
    ACTION (sqlserver.database_id, sqlserver.database_name, sqlserver.query_hash_signed,
            sqlserver.query_plan_hash_signed, sqlserver.sql_text, sqlserver.username))
ADD TARGET package0.histogram (SET source = N'sqlserver.database_id');   -- [MS Learn]
```

Гистограмма читается из `sys.dm_xe_session_targets.target_data` [MS Learn]. При флаге 1224 эскалаций должно быть мало [практика].

### 7.6. Чтение `.xel` и замена методики 5910

- `sys.fn_xe_file_target_read_file(path, mdpath, initial_file_name, initial_offset)`: маска `*` в пути; `mdpath` с 2016 — `NULL`; пара имени файла и смещения — инкрементальное чтение; колонки `object_name`, `event_data` (XML в `nvarchar(max)`), `file_name`, `file_offset`, `timestamp_utc` (2017+); без пути — каталог `\MSSQL\Log` [MS Learn]. Разборы — D-12, D-13, D-37; большие файлы загружать в отдельную базу-«песочницу», не в базу ИБ [ИТС-мет 5910; практика].
- Методика 5910 (трассировка `sp_trace_create` событий 10/12 с фильтром по базе + техжурнал + нормализация + MD5) на 2026 год: трассировку заменяет сессия 7.2 без порога на 15–20 минут; загрузка — по образцу 1С (`../its-metod/vzaimoblokirovki-…`, 2.4.6) с поправкой на единицы; группировка — нормализацией 5910 или по `query_hash_signed` (9.4); Profiler не использовать [ИТС-мет 5910; MS Learn].
- Меры предосторожности [практика]: без фильтра `rpc_completed` на нагруженной базе 1С пишет гигабайты в час ⚠; `NO_EVENT_LOSS` на рабочем сервере не использовать ⚠; события с планами (`query_post_execution_showplan`) дороги — облегчённая альтернатива `query_post_execution_plan_profile` (2017 CU14+/2019) [MS Learn]; временные сеансы после расследования останавливать и удалять, следить за местом (D-22).

## 8. Query Store

### 8.1. Что и в каких версиях

- Тексты, планы, статистика выполнения по интервалам (`INTERVAL_LENGTH_MINUTES`, по умолчанию 60), с 2017 — ожидания по запросам; данные в самой базе, асинхронный сброс (`DATA_FLUSH_INTERVAL_SECONDS`, по умолчанию 900) [MS Learn].
- С 2016, во всех редакциях; **включён по умолчанию (`READ_WRITE`) для новых баз с 2022**; восстановленные и обновлённые «на месте» базы сохраняют прежние настройки; функции 2022 (подсказки Query Store, обратная связь DOP/CE/грантов) требуют включённого Query Store [MS Learn]. База 1С, созданная на 2022, получит его, если не изменена `model` ⚠ — проверять D-28.

### 8.2. Параметры для базы 1С

| Параметр | Умолчание [MS Learn] | Для 1С [практика] |
|---|---|---|
| `QUERY_CAPTURE_MODE` | `ALL` (2016–2017), `AUTO` (2019+) | `AUTO`: захват при ≥ 30 выполнениях, или ≥ 1 с CPU компиляции, или ≥ 100 мс CPU выполнения за сутки; `CUSTOM` — свои пороги (2019+) |
| `MAX_STORAGE_SIZE_MB` | 100 (2016–2017), 1000 (2019+) | 2000–4000 для крупной базы ⚠; Microsoft: больше 10 ГБ — пересмотреть нагрузку |
| `SIZE_BASED_CLEANUP_MODE` | `AUTO` (с 90 % до ~80 %) | `AUTO` |
| `STALE_QUERY_THRESHOLD_DAYS` | 30 | 14–30 |
| `INTERVAL_LENGTH_MINUTES` | 60 | 15–60 |
| `MAX_PLANS_PER_QUERY` | 200 | оставить |
| `WAIT_STATS_CAPTURE_MODE` | `ON` (2017+) | `ON` |

```sql
-- от имени владельца базы или sysadmin; SQL Server 2019+
ALTER DATABASE [buh] SET QUERY_STORE = ON
  (OPERATION_MODE = READ_WRITE, QUERY_CAPTURE_MODE = AUTO, MAX_STORAGE_SIZE_MB = 2048,
   SIZE_BASED_CLEANUP_MODE = AUTO, CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 30),
   INTERVAL_LENGTH_MINUTES = 30, WAIT_STATS_CAPTURE_MODE = ON);
-- проверка — D-28
```

- Query Store **молча** уходит в `READ_ONLY`, чаще всего из-за размера (`readonly_reason = 65536`): увеличить `MAX_STORAGE_SIZE_MB`, `SET QUERY_STORE CLEAR` или `OPERATION_MODE = READ_WRITE`; лимит проверяется только при сбросе на диск [MS Learn]. D-28 — в еженедельный регламент [практика].
- Состояние `ERROR`: с 2017 — `sys.sp_query_store_consistency_check` при выключенном Query Store; на 2016 — очистка [MS Learn].
- 2016–2019: Microsoft просит установить исправление масштабируемости (2016 SP2 CU15, 2017 CU23, 2019 CU9), иначе при большой нерегламентированной нагрузке Query Store потребляет много памяти [MS Learn]. Флаг 7745 — не сбрасывать данные при остановке службы; 7752 — асинхронная загрузка (с 2019 по умолчанию) [MS Learn].

### 8.3. Особенности 1С

- **Много «уникальных» текстов** — номера `#tt<N>` и динамические тексты [ИТС-мет 5910]; Microsoft для таких нагрузок советует `AUTO` и сравнение числа различных `query_hash` с числом строк `sys.query_store_query` [MS Learn]. Совпадает ли `query_hash` при разных `#tt` — ⚠.
- **`PARAMETERIZATION FORCED` для базы 1С не применять** без согласования — платформа уже параметризует запросы, а настройка меняет все планы ⚠ [практика].
- **`DBCC FREEPROCCACHE` из регламента Query Store не очищает** — «вчерашний» топ есть только в нём [MS Learn; ИТС-мет 5837].
- **Реструктуризация и обновление конфигурации** меняют таблицы, индексы и тексты — история «обрывается», принудительные планы ломаются (8.4) [MS Learn; практика].
- Накладные расходы на очень нагруженных базах 1С первоисточниками не оценены ⚠ — включать с наблюдением.

### 8.4. Анализ, принудительные планы, автоматическая настройка

- SSMS (база → Query Store): **Regressed Queries** (фильтры Duration, CPU Time, Logical/Physical Reads, DOP, Memory, Wait Time…; сравнение планов, Force/Unforce), **Query Wait Statistics** (SSMS 18+), а также Overall Resource Consumption, Top Resource Consuming Queries, Queries With Forced Plans, Queries With High Variation, Tracked Queries (Уточнено 20.10.2026 по MS Learn, best-practice-with-the-query-store) [MS Learn]. Ожидания сгруппированы в категории; Microsoft переводит: `RESOURCE_SEMAPHORE` → Memory (подсказка `MAX_GRANT_PERCENT`), `LCK_M_X` → Lock (запросы, меняющие те же сущности), `PAGEIOLATCH_SH` → Buffer IO (индекс вместо сканирования), `SOS_SCHEDULER_YIELD` → CPU (регрессия плана, индекс) [MS Learn]. Запросы — D-29…D-33.
- **Принуждение**: `EXEC sp_query_store_force_plan @query_id = …, @plan_id = …;` (нужен `ALTER` на базу), отмена — `sp_query_store_unforce_plan`; план не гарантирован — запрос перекомпилируется в тот же или похожий, в редких случаях заметно худший [MS Learn]. При изменении схемы или переименовании базы принуждение молча не применяется; причина — `last_force_failure_reason_desc` (`NO_PLAN`, `NO_INDEX`, `NO_DB`, `HINT_CONFLICT`, `SETOPT_CONFLICT`, `TIME_OUT`, `ONLINE_INDEX_BUILD`, `GENERAL_FAILURE`…) и `force_failure_count`; событие XE `query_store_plan_forcing_failed` [MS Learn].
- **Риски с 1С** [практика]: запрос с другим номером `#tt` — другой `query_id` ⚠; реструктуризация ломает принуждение или делает его вредным; принуждение маскирует настоящую причину (статистика, индекс, текст в конфигурации). Только временно, с записью в журнал изменений и проверкой D-33 после каждого обновления конфигурации.
- **Подсказки Query Store** (2022+): `EXEC sys.sp_query_store_set_hints @query_id = 39, @query_hints = N'OPTION(MAXDOP 1)';` — крайняя мера по Microsoft; `RECOMPILE` игнорируется при принудительной параметризации (предупреждение 12461) [MS Learn].
- **`FORCE_LAST_GOOD_PLAN`** (2017+, **только Enterprise**): автоматически принуждает последний хороший план при регрессии; рекомендации — `sys.dm_db_tuning_recommendations` (не сохраняются при перезапуске); `ALTER DATABASE [buh] SET AUTOMATIC_TUNING (FORCE_LAST_GOOD_PLAN = ON);` [MS Learn]. Для 1С — сначала смотреть рекомендации и применять вручную ⚠ [практика].

## 9. Кеш планов и топ-запросы: методики 5861, 5813, 5910, 5906

### 9.1. `sys.dm_exec_query_stats`: что хранит, где ловушки

- Строка на оператор кешированного плана; **живёт, пока план в кеше** [MS Learn] — теряется при перезапуске, вытеснении, перекомпиляции, `DBCC FREEPROCCACHE`. Регламент 1С очищает кеш **ежедневно** после обновления статистики [ИТС-мет 5837, 2022] (на 2016+ — `ALTER DATABASE SCOPED CONFIGURATION CLEAR PROCEDURE_CACHE` для одной базы — `05-…`); смотрите `creation_time` и `last_execution_time` [MS Learn; практика].
- `total_worker_time`, `total_elapsed_time` — **микросекунды** (точность — мс) [MS Learn]; в [ИТС-мет 5861] сумма `total_worker_time` названа `CPU_Time_Ms` — проценты верны, абсолютные значения в мкс.
- Колонки: `execution_count`, `total_logical_reads`, `total_physical_reads`, `total_logical_writes`, `total_rows`, `plan_generation_num`, `query_hash`/`query_plan_hash`; 2016+ — `last_dop`, `total_grant_kb`, `total_used_grant_kb`, `total_ideal_grant_kb`; 2016 SP2/2017 CU3+ — `total_spills` [MS Learn].
- `dbid` в `sys.dm_exec_sql_text` есть только у объектов (процедур), для прочего SQL — `NULL` [MS Learn]; поэтому методики 1С берут атрибут `dbid` плана из `sys.dm_exec_plan_attributes` [ИТС-мет 5861; 5813].
- Выборки по всему кешу с `sys.dm_exec_query_plan` («подход 2» 5861 — «около 2 минут» по самой статье) нагружают сервер; на перегруженном — сначала без планов, план точечно по `plan_handle` [ИТС-мет 5861; практика].

### 9.2. Методика 5861: высокая загрузка CPU

[ИТС-мет 5861, 2015], два подхода, пройти оба:

- **Подход 1**: запросы-лидеры по CPU и их базы; текст и стек кода (техжурнал по таблицам — 12.2 Б); если запрос выполняют сейчас несколько сеансов — найти их в консоли по `spid`, записать номер и время, завершить; если выполняют многие периодически — исправить запрос; проверить самые частые запросы и «индексы с высокими издержками» (`sys.dm_db_index_usage_stats`: `user_updates + system_updates` против `user_seeks + user_scans + user_lookups`, по всем базам через `sp_MSForEachDB`); по журналу регистрации — что делали завершённые сеансы.
- **Подход 2**: базы и запросы за последний час (`last_execution_time > CURRENT_TIMESTAMP - '01:00:00.000'`) с `percent_worker_time`/`percent_elapsed_time`; **нагрузка не должна быть «размазана»** — есть лидер → им и заниматься; размазана → методика 5910.

Замечания к скриптам (сверено с MS Learn): `CPU_Time_Ms` — микросекунды; `percent_elapsed_time` считается от `max_elapsed_time`, а не `total_elapsed_time`; в подходе 1 шаг «Убедиться, что нагрузка на диск упала» по смыслу — на процессор; `sp_MSForEachDB` недокументирована (Подтверждено 20.10.2026: в каталоге системных процедур MS Learn страницы нет). Современные версии — D-14, D-16, D-17, D-18. Признаки CPU-нагрузки — `SOS_SCHEDULER_YIELD`, доля сигнальных ожиданий, `runnable_tasks_count` (10.5) [MS Learn].

### 9.3. Методика 5813: нагрузка на диск

[ИТС-мет 5813, 2015]: убедиться Монитором ресурсов, что диск грузит СУБД; найти базы и запросы (топ по `total_physical_reads` за час с процентами), запрос в коде (техжурнал), сеансы; журнал регистрации; длинные транзакции; исправить и проверить. В статье также запросы: частые запросы, издержки ввода-вывода `(total_logical_reads + total_logical_writes) / execution_count`, кеши (`sys.dm_os_memory_clerks`), буферный пул по базам (`sys.dm_os_buffer_descriptors`), свободное место tempdb (`unallocated_extent_page_count`), транзакции хранилища версий.

Поправки на 2026 год:

- Порог «`Avg. Disk Sec/Read` > 2000 (мс)» — ошибка; ориентиры — 10.1. Счётчик измеряется в **секундах** (0,015 = 15 мс) ⚠ (по названию; страница Microsoft единицу не приводит).
- `single_pages_kb` есть только в 2008–2008 R2, с 2012 — `pages_kb` [MS Learn].
- Запрос по `sys.dm_os_buffer_descriptors` тяжёл на большом буферном пуле [практика].
- В образце `logcfg.xml` испорчено пространство имён (`xmlns=" v8.1c.ru/v8/tech-log »»"`) и путь `С:\` с кириллической «С» — набирать вручную [`../1c-windows/02-…`, 11.5].

Современные версии — D-15, D-21, D-23, D-26.

### 9.4. Методика 5910: «размазанная» нагрузка

[ИТС-мет 5910, 2016]: если лидера нет (пакетные запросы конфигурации дробятся на мелкие, тексты собираются динамически), запросы группируют по контексту вызова. Синхронно собираются серверная трассировка и техжурнал `DBMSSQL` (отбор по `p:processName`, без планов), выгружаются в отдельную базу (например, `_Traces`), тексты нормализуются функцией `fn_GetSQLHash` (убирает `#tt<цифры>`, `@P<цифры>`, `exec sp_executesql N'`, пробелы, переводы строк, знаки), считается MD5, трассировка агрегируется по хешу (средние `Duration`, `CPU`, `Reads`, `Writes`) и соединяется с контекстами (первая и последняя строки стека). Требования: каталог существует, у службы SQL Server есть право записи, файл до запуска не существует, размер (например, 2000 МБ), окно 15–20 минут; трассировку включать до техжурнала.

Упрощения на современных версиях: трассировку заменяет XE (7.2, 7.6) [MS Learn]; вместо нормализации можно группировать по **`query_hash`** — одинаков у запросов, различающихся только литералами; есть и в `sys.query_store_query` [MS Learn] (D-16). Совпадает ли он у запросов 1С с разными `#tt<N>` — ⚠; если нет — оставайтесь на нормализации 5910. Сопоставление с кодом по-прежнему требует техжурнала.

### 9.5. Методика 5906: top-25 вызовов на стороне 1С

[ИТС-мет 5906, 2016]: техжурнал `CALL` (`<property name="all"/>`), разбор `call.pl` + `awk` с суммированием по `Context`: `SumDuration`, `AvgDuration`, `Numb`; делитель 1 000 000 для 8.3 (мкс), 10 000 для 8.2; группируются только вызовы с контекстом встроенного языка. Взгляд от 1С: сначала самые долгие вызовы, затем их запросы на SQL Server (техжурнал `DBMSSQL` по `Context` или `SessionID` → D-14/Query Store) [практика]. Разбор на Linux — `../its-metod/tehzhurnal-bash-i-potreblenie-resursov.md`; на Windows — WSL или PowerShell [практика].

### 9.6. Индексы: «отсутствующие» и «бесполезные»

- `sys.dm_db_missing_index_details` (+ `_groups`, `_group_stats`) — подсказки оптимизатора; не сохраняются после перезапуска, не больше 600 строк; равенства — перед неравенствами [MS Learn]. `sys.dm_db_index_usage_stats` обнуляется при старте службы и закрытии базы [MS Learn].
- **Флаг 2330** (1С: отключить сбор статистики использования индексов на продуктивных серверах; собирать её на тестовой зоне) [ИТС-мет 5946, 2019] делает эти представления пустыми или неполными — перед выводами `DBCC TRACESTATUS(-1)`; Microsoft флаг не документирует (Подтверждено 20.10.2026 по справочнику флагов MS Learn); затрагивает ли он и `sys.dm_db_missing_index_*` — ⚠ (1С пишет только о статистике использования индексов).
- **Индексы в базе 1С не создаются в SSMS**: структура управляется платформой, нештатная работа с данными запрещена [`../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`, п. 1–2]. Индекс задают в конфигурации — индексирование реквизитов или дополнительные индексы объектов метаданных (только лицензия КОРП; создаются при реструктуризации; включаются параметром ИБ «Использовать дополнительные индексы») [ИТС-разр гл. 9, разд. 9.4]. Подсказки missing index (D-34) — материал для разработчика.

## 10. Диски, память, tempdb, процессор

### 10.1. Диски

- `sys.dm_io_virtual_file_stats(NULL, NULL)` — накопленная статистика по файлам: `num_of_reads`, `num_of_bytes_read`, `io_stall_read_ms`, `num_of_writes`, `num_of_bytes_written`, `io_stall_write_ms`, `io_stall`, `size_on_disk_bytes`; `io_stall_queued_*` — задержка от регулятора ресурсов [MS Learn]. Средняя задержка — `io_stall_read_ms / num_of_reads`; «сейчас» — дельта (D-21).
- Ориентиры: 1С — данные 10–20 мс, журнал 1–5 мс [ИТС-мет 5904; 6008]; Microsoft — `PAGEIOLATCH_*`, `WRITELOG`, `ASYNC_IO_COMPLETION` и `Avg. Disk sec/Read|Write|Transfer` устойчиво выше 10–15 мс — проблема; пик дольше минуты — уже плато [MS Learn].
- **Ошибка 833** (ввод-вывод дольше 15 с) — `EXEC sp_readerrorlog 0, 1, N'taking longer than';` (`@p1` — номер журнала, 0 — текущий; `@p2` — 1 SQL Server, 2 Агент; `@p3`/`@p4` — фильтры) [MS Learn].
- Свободное место томов — `sys.dm_os_volume_stats` (`volume_mount_point`, `total_bytes`, `available_bytes`) [MS Learn] — D-22. Activity Monitor → Data File I/O — то же интерактивно [ИТС-мет 6008].
- Данные и журналы — на разных массивах, журнал — на самом быстром [ИТС-мет 5904]; размещение — `02-…`.

### 10.2. Журнал транзакций

- `WRITELOG` — латентность диска журнала, ввод-вывод не успевает или слишком много сбросов (фиксаций/откатов) [MS Learn]; `LOGBUFFER` — следствие [ИТС-мет 6008].
- Счётчики `Databases(<база>)`: `Log Flush Wait Time`, `Log Flush Waits/sec`, `Log Flushes/sec`, `Percent Log Used`, `Log Growths` [MS Learn].
- Рост файла без IFI заполняет новое место нулями, пока транзакции ждут; по 1С IFI на журнал не действует — размер журнала задают с запасом до следующего `BACKUP LOG` [ИТС-мет 6008; 5904]. Уточнено 20.10.2026 по MS Learn (database-instant-file-initialization): с SQL Server 2022 (все редакции) приросты журнала до 64 МБ инициализируются мгновенно, более крупные — по-прежнему с обнулением; вывод 1С остаётся в силе; признак — `PREEMPTIVE_OS_WRITEFILEGATHER` у операции роста [MS Learn]. IFI включён? — `SELECT servicename, instant_file_initialization_enabled FROM sys.dm_server_services;` (2012 SP4, 2014 SP3, 2016 SP1+) [MS Learn]; проверка 1С — база 5 ГБ создаётся мгновенно [ИТС-мет 5904].
- Почему журнал не усекается — `log_reuse_wait_desc` (`04-…`).

### 10.3. Память

| Что смотреть | Где | Признак | Источник |
|---|---|---|---|
| Фактическая и целевая память | `Total`/`Target Server Memory (KB)`; `committed_kb`/`committed_target_kb` (`sys.dm_os_sys_info`) | Total устойчиво ниже Target ⚠ | [MS Learn] |
| Давление ОС | `sys.dm_os_sys_memory.system_memory_state_desc`, `available_physical_memory_kb` | сигнал низкой памяти | [MS Learn] |
| Давление на процесс | `sys.dm_os_process_memory.process_physical_memory_low`, `memory_utilization_percentage`, `locked_page_allocations_kb` | `process_physical_memory_low = 1` | [MS Learn] |
| Ожидание грантов | `RESOURCE_SEMAPHORE`, `Memory Grants Pending`, `sys.dm_exec_query_memory_grants` с `grant_time IS NULL` | > 0 устойчиво; ошибка 8645 | [MS Learn; ИТС-мет 6008] |
| Кто держит гранты | `requested_memory_kb`, `granted_memory_kb`, `used_memory_kb`, `ideal_memory_kb`, `dop`, `query_cost` | гигабайтные гранты отчётов | [MS Learn] |
| Кто вытесняет буферный пул | D-15, D-23 | одна база занимает почти весь пул | [ИТС-мет 5813] |
| `Page life expectancy` | секунды жизни страницы без обращений | провалы при отчётах; порога Microsoft не даёт («300 с» — устаревшая практика ⚠) | [MS Learn] |
| Клерки | `sys.dm_os_memory_clerks.pages_kb` | раздутый кеш планов ⚠ | [MS Learn; ИТС-мет 5813] |
| Подкачка Windows | `Memory\Pages/sec` | среднее ≈ 0, не более 20 | [ИТС-мет 2923; 5838] |

Если сервер 1С на той же машине, `max server memory` уменьшают на долю 1С и не включают Lock Pages in Memory [ИТС-мет 5904, 2019] — при росте `rphost` SQL Server отдаст память и PLE упадёт; это ожидаемо [практика].

### 10.4. tempdb

Нагрузка от временных таблиц `#tt`, сортировок и хешей (`GROUP BY`, `UNION`, `DISTINCT`) [ИТС-мет 2374, 2008] и хранилища версий RCSI [ИТС-разр гл. 9; MS Learn]; при включённом ADR (2019+) хранилище версий базы — в ней самой [MS Learn].

| Что | Где | Источник |
|---|---|---|
| Чем занята | `sys.dm_db_file_space_usage`: `version_store_reserved_page_count`, `user_object_reserved_page_count`, `internal_object_reserved_page_count`, `unallocated_extent_page_count` — D-26 | [MS Learn; ИТС-мет 5813] |
| Кто потребляет | `sys.dm_db_session_space_usage`, `sys.dm_db_task_space_usage` — D-26 | [MS Learn] |
| Версии по базам и «держатели» | `sys.dm_tran_version_store_space_usage` (2016 SP2+), `sys.dm_tran_active_snapshot_database_transactions`, `sys.dm_tran_top_version_generators` — D-11 | [MS Learn] |
| Счётчики | `Transactions\Free Space in tempdb (KB)`, `Version Store Size (KB)`, `Version Generation rate (KB/s)`, `Version Cleanup rate (KB/s)` | [MS Learn] |
| Конкуренция за размещение | `PAGELATCH_UP`/`_EX` на `2:1:1` (PFS; PFS — каждая страница, кратная 8088), `2:1:2` (GAM), `2:1:3` (SGAM) | [MS Learn] |

- Файлы tempdb — **одинаковые**, по числу логических процессоров до 8; если не помогло — добавлять по 4 [MS Learn]; 1С — 4 файла [ИТС-мет 5904]; флаги 1117/1118 на 2016+ не нужны [ИТС-мет 5946; MS Learn].
- Конкуренция за метаданные временных объектов (2019+): `ALTER SERVER CONFIGURATION SET MEMORY_OPTIMIZED TEMPDB_METADATA = ON;` + перезапуск — только при подтверждённой конкуренции [MS Learn] ⚠ (для 1С не проверялось).
- Нет места под версии — SQL Server сжимает хранилище, самые долгие транзакции становятся «жертвами» ошибок чтения версий [MS Learn].
- Оповещение ЦКК по 1С — «SQL Tempdb Log Used Size (MB) [среднее]» > 70 ГБ [ИТС-мет 5899, 2016]. Сжатие tempdb — только в окно минимальной активности; надёжнее перезапуск службы [ИТС-мет 2374]. Причина роста почти всегда — долгая транзакция (5.4).

### 10.5. Процессор

- Признаки CPU-давления: высокая доля `signal_wait_time_ms` (D-02, «20–25 %» — практика ⚠), `SOS_SCHEDULER_YIELD`, `runnable_tasks_count > 0` на многих планировщиках (D-27) [MS Learn]; `work_queue_count > 0` и `THREADPOOL` — нет свободных потоков [MS Learn].
- Пороги 1С: `% Processor Time` > 70 % длительно, `Processor Queue Length` > 2 × ядер (2021) [ИТС-мет 5838]; в 2008 — 85 % и 2 [ИТС-мет 2923].
- Компиляции: `SQL Compilations/sec`, `SQL Re-Compilations/sec` относительно `Batch Requests/sec` [MS Learn]; перекомпиляции из-за временных таблиц возможны при неизменном тексте [ИТС-мет 6006 — конспект, 2.4].
- При `MAXDOP = 1` ожиданий `CX*` почти нет; на время реструктуризации 1С разрешает `MAXDOP = 0` и советует следить за `CXPACKET` и дисковыми ожиданиями (запрос в статье), затем вернуть `1` [ИТС-мет 5945, 2018].

## 11. Счётчики Performance Monitor

### 11.1. Windows (методики 1С)

| Счётчик | Ориентир | Источник |
|---|---|---|
| `Processor(_Total)\% Processor Time` | ≤ 70 % длительно (2021); > 85 % — узкое место (2008) | [ИТС-мет 5838; 2923] |
| `System\Processor Queue Length` | ≤ 2 × ядер (2021); > 2 (2008) | [ИТС-мет 5838; 2923] |
| `Memory\Pages/sec` | среднее ≈ 0, максимум ≤ 20 | [ИТС-мет 5838; 2923] |
| `PhysicalDisk\Avg. Disk Queue Length` | ≤ 2 × параллельных дисков | [ИТС-мет 5838] |
| `PhysicalDisk\Avg. Disk Sec/Read`, `…/Write` | данные 10–20 мс, журнал 1–5 мс; MS — до 10–15 мс | [ИТС-мет 5904; 6008; MS Learn] |
| `Network Interface\Bytes Total/sec` | ≤ 65 % пропускной способности | [ИТС-мет 5838; 2923] |
| `Memory\Available MBytes`, `LogicalDisk\% Free Space`, `System\Context Switches/sec`, `System\Threads` | в обязательном наборе 1С | [ИТС-мет 5838] |

Диски — по экземплярам томов, а не `_Total`, иначе быстрый том журнала «разбавит» медленный том данных [практика].

### 11.2. Объекты SQL Server

Префикс `SQLServer:` — экземпляр по умолчанию; для именованного — `MSSQL$<имя>:` (Подтверждено 20.10.2026 по MS Learn, use-sql-server-objects) [MS Learn].

| Объект\Счётчик | Смысл / для 1С | Источник |
|---|---|---|
| `Buffer Manager\Page life expectancy` | жизнь страницы без обращений, с; тренд и провалы | [MS Learn] |
| `Buffer Manager\Page reads/sec`, `Lazy writes/sec`, `Free list stalls/sec` | физические чтения, ленивый писатель, ожидание свободной страницы — давление на память ⚠ | [MS Learn] |
| `Memory Manager\Memory Grants Pending` | ждущие гранта — должно быть 0 | [MS Learn] |
| `General Statistics\User Connections`, `Processes blocked`, `Logins/sec` | соединения; заблокированные сейчас; новые входы без пула | [MS Learn] |
| `SQL Statistics\Batch Requests/sec`, `SQL Compilations/sec`, `SQL Re-Compilations/sec` | нагрузка и компиляции | [MS Learn] |
| `Locks(_Total)\Lock Waits/sec`, `Lock Wait Time (ms)`, `Average Wait Time (ms)` | Lock Wait Time ≤ «время отклика × активные пользователи», Average ≤ времени отклика | [MS Learn; ИТС-мет 2923] |
| `Locks(_Total)\Lock Timeouts/sec`, `Number of Deadlocks/sec` | тайм-ауты; взаимоблокировки — 0 | [MS Learn; ИТС-мет 2923] |
| `Access Methods\Full Scans/sec`, `Index Searches/sec`, `Page Splits/sec`, `Workfiles/Worktables Created/sec` | рост Full Scans после обновления конфигурации — ищите регрессию | [MS Learn] |
| `Databases(<база>)\Log Flush Wait Time`, `Log Growths`, `Percent Log Used`, `Transactions/sec` | журнал и транзакции (10.2) | [MS Learn] |
| `Transactions\Free Space in tempdb (KB)`, `Version Store Size (KB)`, `Longest Transaction Running Time` | tempdb и версии (10.4) | [MS Learn] |

### 11.3. Сбор: `logman` и DMV

1С рекомендует собирать счётчики постоянно, раз в 15 с (на нагрузочных тестах — раз в 1 с), в кольцевой двоичный `.blg`, через `logman` и автозапуск Планировщиком заданий [ИТС-мет 5838, 2021]. Пример для сервера СУБД (cmd от имени локального администратора; экземпляр по умолчанию):

```cmd
logman create counter SQL_1C -f bincirc -max 1024 -si 15 -o "E:\PerfLogs\SQL_1C" -c ^
 "\Processor(_Total)\% Processor Time" "\System\Processor Queue Length" "\Memory\Available MBytes" "\Memory\Pages/sec" ^
 "\PhysicalDisk(*)\Avg. Disk sec/Read" "\PhysicalDisk(*)\Avg. Disk sec/Write" "\PhysicalDisk(*)\Avg. Disk Queue Length" ^
 "\Network Interface(*)\Bytes Total/sec" ^
 "\SQLServer:Buffer Manager\Page life expectancy" "\SQLServer:Memory Manager\Memory Grants Pending" ^
 "\SQLServer:SQL Statistics\Batch Requests/sec" "\SQLServer:SQL Statistics\SQL Compilations/sec" ^
 "\SQLServer:Locks(_Total)\Lock Waits/sec" "\SQLServer:Locks(_Total)\Lock Wait Time (ms)" ^
 "\SQLServer:Locks(_Total)\Number of Deadlocks/sec" "\SQLServer:General Statistics\Processes blocked" ^
 "\SQLServer:Transactions\Free Space in tempdb (KB)" "\SQLServer:Transactions\Version Store Size (KB)"
logman start SQL_1C
logman query SQL_1C
```

Ключи `create counter`, `-f bincirc`, `-c`, `-si`, `-v` — из статьи 1С [ИТС-мет 5838]; `-max` (размер файла в МБ) и `-o` (путь к файлу журнала) — Подтверждено 20.10.2026 по справке `logman create counter` (MS Learn, windowsserverdocs). Анализ — `.blg` в Performance Monitor: среднее и пики [ИТС-мет 5838].

Без Performance Monitor (и на Linux) — `sys.dm_os_performance_counters`: у счётчиков «в секунду» (`cntr_type` 272696576) значение накопительное — скорость по двум снимкам (D-25); 65792 — мгновенное (D-24); 537003264 — отношение к «… base»; 1073874176 — среднее [MS Learn].

ЦКК (КИП): сбор счётчиков включается в карточке сервера (Агент КИП или PDH; пользователь — в группе Performance Monitor Users), набор синхронизируется с ролью оборудования [ИТС-мет 5838]; минимальные оповещения: место на дисках < 10 %, память < 200 МБ (кроме СУБД), CPU > 90 % за 5 минут, tempdb > 70 ГБ [ИТС-мет 5899]. Подробно — `../its-metod/monitoring-i-audit.md`.

## 12. Связка с техжурналом 1С

### 12.1. События и свойства

| Событие | Что | Ключевые свойства | Источник |
|---|---|---|---|
| `DBMSSQL` | операторы SQL на MS SQL | `Sql`, `planSQLText` (с `<plansql/>`), `Context`, `Dbpid` (= `session_id`), `Database` (`Сервер\База`), `Rows`, `RowsAffected`, `Trans` (0/1), `Usr`, `SessionID`, `t:connectID`, `p:processName`, `Duration` (1/10000 с), `Durationus` (мкс), `lk*` при `<dbmslocks/>` | [ИТС-адм прил. 3, разд. 3.24.2.3, 3.24.2.4.2, 3.24.5] |
| `DBMSSQLCONN` | первое соединение, выбор провайдера | 8.3.27: `hResultOLEDB`, `hResultNC2005`, `hResultNC2008`, `hResult2012`; 8.5.1: `hResultMSOLEDBSQL19`, `hResultMSOLEDBSQL`, `hResultNC2012`, `hResultNC2005`, `hResultOLEDB` | [ИТС-адм прил. 3]; `../its-docs/otlichiya-8.5.1-…` |
| `SDBL` с `Func` = `BeginTransaction`/`CommitTransaction`/`RollbackTransaction` | границы транзакций | `Func`, `Context` | [ИТС-мет 6006 — конспект, 2.4.3] |
| `TLOCK`, `TTIMEOUT`, `TDEADLOCK` | управляемые блокировки 1С | `Regions`, `Locks`, `WaitConnections`, `DeadlockConnectionIntersections` | [ИТС-адм прил. 3, разд. 3.24.2.4.2] |
| `EXCP`, `EXCPCNTX` | исключения, в том числе 1205, 1222 | `Descr`, `Context` | [ИТС-адм прил. 3; `../its-metod/sbor-dannyh-…`, 1.14] |
| `CALL` | серверные вызовы (5906) | `Context`, `Memory`, `MemoryPeak`, `InBytes`, `OutBytes`; `CpuTime` (в таблице свойств 8.3.27 описан только для `EVENTLOG`, для `CALL` — в официальном примере ИТС 6005) | [ИТС-мет 5906; ИТС-адм прил. 3, разд. 3.24.2.4.2; `../its-metod/sbor-dannyh-…`, сц. 18] |

`SDBL` и `DBMSSQL` резко увеличивают объём журнала [ИТС-адм прил. 3, разд. 3.24.2.3] — всегда фильтруйте по базе, длительности или тексту. Формат, ротация, разбор — `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.

### 12.2. Шаблоны `logcfg.xml`

Каталоги — на сервере 1С; букву диска набирайте вручную (в методиках 5861/5813 — кириллическая «С») [`../1c-windows/02-…`, 11.5].

**А. Долгие запросы одной ИБ** (1 с = `Duration` 10000) [ИТС-адм прил. 3; `../1c/07-…`]:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="D:\LOGS\dbmssql_long" history="24">
    <event>
      <eq property="Name" value="DBMSSQL"/>
      <eq property="p:processName" value="buh"/>
      <ge property="Duration" value="10000"/>
    </event>
    <property name="all"/>
  </log>
</config>
```

**Б. «Узкий» журнал на один запрос из топа DMV** (имена таблиц из текста SQL; стек — в конце события) [ИТС-мет 5861; 5813]; в методиках к нему добавлен `<plansql/>` — см. 12.3:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="C:\Sql_Reads" history="2">
    <event>
      <eq property="Name" value="DBMSSQL"/>
      <like property="Sql" value="%SELECT TOP%Reference5774%"/>
    </event>
    <property name="all"/>
  </log>
</config>
```

**В. Все запросы ИБ на 15–20 минут — для 5910** — как А, но без условия `Duration` (в статье — `<ns:eq property="p:processName" …>`, `history="4"`) [ИТС-мет 5910].

**Г. Блокировки СУБД с границами транзакций** [ИТС-мет 6006 — конспект, 2.4.3; ИТС-адм прил. 3, разд. 3.24.5]:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="D:\LOGS\locks" history="2">
    <event><eq property="Name" value="DBMSSQL"/><eq property="p:processName" value="buh"/></event>
    <event><eq property="Name" value="SDBL"/><eq property="Func" value="BeginTransaction"/></event>
    <event><eq property="Name" value="SDBL"/><eq property="Func" value="CommitTransaction"/></event>
    <event><eq property="Name" value="SDBL"/><eq property="Func" value="RollbackTransaction"/></event>
    <event><eq property="Name" value="EXCP"/></event>
    <property name="all"/>
  </log>
  <dbmslocks/>
</config>
```

**Д. Взаимоблокировки СУБД для поддержки** — `EXCP`, `EXCPCNTX`, `SDBL`, `DBMSSQL` со всех серверов кластера + `xml_deadlock_report` [`../its-metod/sbor-dannyh-…`, 1.14].

Проверка: через минуту в `location` появились каталоги `rphost_<pid>` с файлами `ГГММДДЧЧ.log`; объём — следить первые часы [`../1c/07-…`; `../its-metod/monitoring-i-audit.md`].

### 12.3. `<plansql/>` — только на время анализа

- План — в `planSQLText`, вместе с ним записывать `Sql`; **получение планов замедляет запросы** (для некоторых СУБД существенно), в обычном режиме не собирать [ИТС-адм прил. 3, разд. 3.24.2.10.1]. Сбор включается для **всех** баз, записываются только прошедшие фильтр [`../1c/07-…` по ИТС-мет 5809]; для PostgreSQL методика 1С запрещает его на продуктивных серверах [`../1c/07-…` по ИТС-мет 6011], для MS SQL разумно то же [практика].
- Формат MS SQL упрощён: `Rows`, `Executes`, `EstimateRows`, `EstimateIO`, `EstimateCPU`, `AvgRowSize`, `TotalSubtreeCost`, `EstimateExecutions`, `StmtText` через запятую, `StmtText` — до конца строки [ИТС-адм прил. 3, разд. 3.24.2.10.3]; расхождение `Rows` и `EstimateRows` — проблема статистики/кардинальности [практика].
- Альтернативы без нагрузки на весь сервер: план из кеша, «живой» план, `sys.dm_exec_query_plan_stats` (2019+), Query Store [MS Learn]; фактический план на копии базы — текст из `Sql` с параметрами `@P` в SSMS с «Include Actual Execution Plan» (DML реально изменит данные — только на копии) [практика].

### 12.4. Стыковка ТЖ ↔ DMV ↔ Query Store

1. Из DMV/Query Store/XE: характерные таблицы текста, `session_id`, время.
2. В техжурнале — `DBMSSQL` с `Dbpid` = `session_id` в то же время или с тем же фрагментом `Sql` [ИТС-адм прил. 3].
3. Из события — `Context`, `Usr`, `SessionID`, `t:connectID` [ИТС-адм прил. 3]; по `SessionID` — консоль и журнал регистрации [ИТС-мет 5813].
4. Таблицы → объекты (`ПолучитьСтруктуруХраненияБазыДанных()`); итог для разработчика: строка кода, текст, план, ожидания, блокировки [практика].

Обратный путь «жалоба на операцию»: шаблон А с фильтром `Usr` → `Dbpid`/`Sql` → D-05 или Query Store [практика; `../its-metod/sbor-dannyh-…`].

**ЦКК и ЦУП** (КИП): ЦКК — контрольные процедуры, счётчики, оповещения [`../its-metod/monitoring-i-audit.md`]; ЦУП — автоматический анализ ожиданий на управляемых блокировках и блокировках СУБД, схемы взаимоблокировок, «Анализ запросов» со стеками; для MS SQL он делает то, что вручную требует трассировки и техжурнала; запись показателей может снизить производительность исследуемой базы [ИТС-мет 6006, 4051 — конспект, 1.7, 2.3.5, 2.4.1]. Настройка — документация КИП (`its.1c.ru/db/kip`) [ИТС-мет 5838].

## 13. Библиотека диагностических запросов

Условия: логин с `VIEW SERVER STATE` (2022+: `VIEW SERVER PERFORMANCE STATE` или `##MS_ServerStateReader##`) — 1.3; для D-08, D-09, D-28…D-34 ещё доступ к базе ИБ и видимость метаданных (1.3); запросы только читают. Колонки и функции сверены с документацией Microsoft [MS Learn]; тексты запросов — [практика] на основе примеров Microsoft и методик ИТС, если не указано иное; на сервере не запускались.

Состав: **D-01–D-04** — паспорт экземпляра и ожидания (накопленные, за минуту, по сеансу); **D-05–D-13** — что выполняется, открытые транзакции, цепочки блокировок, объект и ресурс блокировки, длинные транзакции, хранилище версий, взаимоблокировки, blocked process report; **D-14–D-19** — кеш планов: CPU, чтения, `query_hash`, базы, частота, гранты; **D-20–D-27** — память, диски, тома, счётчики, tempdb, планировщики; **D-28–D-33** — Query Store: состояние, топ, регрессии, планы, ожидания, принуждение; **D-34–D-37** — отсутствующие индексы, курсоры, соединения 1С, разбор XE.

### D-01. Паспорт экземпляра

```sql
SELECT SERVERPROPERTY('ProductVersion')     AS product_version,
       SERVERPROPERTY('ProductLevel')       AS product_level,      -- RTM / SPn
       SERVERPROPERTY('ProductUpdateLevel') AS cu_level,           -- CUn
       SERVERPROPERTY('Edition')            AS edition,
       si.sqlserver_start_time,
       DATEDIFF(HOUR, si.sqlserver_start_time, SYSDATETIME()) AS uptime_hours,
       si.cpu_count, si.scheduler_count,
       si.physical_memory_kb / 1024  AS server_ram_mb,
       si.committed_kb / 1024        AS sql_committed_mb,
       si.committed_target_kb / 1024 AS sql_target_mb
FROM sys.dm_os_sys_info AS si;

SELECT name, value_in_use
FROM sys.configurations
WHERE name LIKE N'max degree of parallelism%' OR name LIKE N'cost threshold for parallelism%'
   OR name LIKE N'max server memory%'         OR name LIKE N'blocked process threshold%'
   OR name LIKE N'remote admin connections%'  OR name LIKE N'optimize for ad hoc%';

DBCC TRACESTATUS(-1);   -- глобальные флаги: 1224/1211, 4199, 2330 и др. [ИТС-мет 5946]
```

Все накопительные DMV считают «с момента `sqlserver_start_time`» — сначала аптайм [MS Learn].

### D-02. Накопленные ожидания (по методике 6008)

```sql
WITH w AS (
  SELECT wait_type, waiting_tasks_count, wait_time_ms, signal_wait_time_ms, max_wait_time_ms
  FROM sys.dm_os_wait_stats
  WHERE wait_time_ms > 0
    AND wait_type NOT LIKE N'%SLEEP%'
    AND wait_type NOT IN (   -- «безопасные» ожидания [ИТС-мет 6008]
      N'BROKER_TASK_STOP', N'BROKER_TO_FLUSH', N'BROKER_TRANSMITTER', N'CHECKPOINT_QUEUE', N'CHKPT',
      N'CLR_AUTO_EVENT', N'CLR_MANUAL_EVENT', N'CLR_SEMAPHORE', N'DBMIRROR_DBM_EVENT',
      N'DBMIRROR_EVENTS_QUEUE', N'DBMIRROR_WORKER_QUEUE', N'DBMIRRORING_CMD', N'DIRTY_PAGE_POLL',
      N'DISPATCHER_QUEUE_SEMAPHORE', N'EXECSYNC', N'FSAGENT', N'FT_IFTS_SCHEDULER_IDLE_WAIT',
      N'FT_IFTSHC_MUTEX', N'HADR_CLUSAPI_CALL', N'HADR_FILESTREAM_IOMGR_IOCOMPLETION',
      N'HADR_LOGCAPTURE_WAIT', N'HADR_NOTIFICATION_DEQUEUE', N'HADR_TIMER_TASK', N'HADR_WORK_QUEUE',
      N'KSOURCE_WAKEUP', N'LOGMGR_QUEUE', N'ONDEMAND_TASK_QUEUE', N'PWAIT_ALL_COMPONENTS_INITIALIZED',
      N'REQUEST_FOR_DEADLOCK_SEARCH', N'RESOURCE_QUEUE', N'SERVER_IDLE_CHECK', N'SNI_HTTP_ACCEPT',
      N'SQLTRACE_BUFFER_FLUSH', N'SQLTRACE_WAIT_ENTRIES', N'WAIT_FOR_RESULTS', N'WAITFOR',
      N'WAITFOR_TASKSHUTDOWN', N'WAIT_XTP_HOST_WAIT', N'WAIT_XTP_OFFLINE_CKPT_NEW_LOG',
      N'WAIT_XTP_CKPT_CLOSE', N'XE_DISPATCHER_JOIN', N'XE_DISPATCHER_WAIT', N'XE_TIMER_EVENT')
)
SELECT TOP (25) wait_type, waiting_tasks_count,
       CAST(wait_time_ms / 1000.0 AS decimal(18,1))                               AS wait_s,
       CAST(100.0 * wait_time_ms / SUM(wait_time_ms) OVER () AS decimal(5,2))      AS pct,
       CAST(1.0 * wait_time_ms / NULLIF(waiting_tasks_count, 0) AS decimal(18,2))  AS avg_ms,
       CAST(100.0 * signal_wait_time_ms / NULLIF(wait_time_ms, 0) AS decimal(5,2)) AS signal_pct,
       max_wait_time_ms
FROM w
ORDER BY wait_time_ms DESC;
```

Первые 3–5 строк — профиль сервера; `avg_ms` дисковых ожиданий сравнить с 10–15 мс [MS Learn]; высокий `signal_pct` у всех — очередь к CPU (10.5). Оригинал 6008 выводит ещё строку «ВСЕ!» с общими процентами сигнальных и ресурсных ожиданий [ИТС-мет 6008].

### D-03. Ожидания за последнюю минуту (дельта)

```sql
IF OBJECT_ID(N'tempdb..#w1') IS NOT NULL DROP TABLE #w1;
SELECT wait_type, waiting_tasks_count, wait_time_ms, signal_wait_time_ms
INTO #w1 FROM sys.dm_os_wait_stats;

WAITFOR DELAY '00:01:00';            -- окно замера; во время жалобы — 1–5 минут

SELECT TOP (20) w2.wait_type,
       w2.waiting_tasks_count - w1.waiting_tasks_count AS waits,
       w2.wait_time_ms - w1.wait_time_ms               AS wait_ms,
       w2.signal_wait_time_ms - w1.signal_wait_time_ms AS signal_ms,
       CAST(1.0 * (w2.wait_time_ms - w1.wait_time_ms)
            / NULLIF(w2.waiting_tasks_count - w1.waiting_tasks_count, 0) AS decimal(18,2)) AS avg_ms
FROM sys.dm_os_wait_stats AS w2
JOIN #w1 AS w1 ON w1.wait_type = w2.wait_type
WHERE w2.wait_time_ms - w1.wait_time_ms > 0
  AND w2.wait_type NOT LIKE N'%SLEEP%'
  AND w2.wait_type NOT IN (N'XE_TIMER_EVENT', N'XE_DISPATCHER_WAIT', N'REQUEST_FOR_DEADLOCK_SEARCH',
                           N'CHECKPOINT_QUEUE', N'LOGMGR_QUEUE', N'DIRTY_PAGE_POLL', N'WAITFOR')   -- полный список — D-02
ORDER BY wait_ms DESC;
DROP TABLE #w1;
```

`wait_ms` больше 60 000 за минуту — ждали несколько задач одновременно; общая статистика не сбрасывается [практика].

### D-04. Ожидания одного сеанса (2016+)

```sql
DECLARE @spid int = 123;   -- «Соединение с СУБД» из консоли кластера 1С
SELECT wait_type, waiting_tasks_count, wait_time_ms, max_wait_time_ms, signal_wait_time_ms
FROM sys.dm_exec_session_wait_stats
WHERE session_id = @spid
ORDER BY wait_time_ms DESC;
```

Сбрасывается при открытии сеанса и сбросе соединения пулом [MS Learn] — для долгоживущих соединений `rphost` это ожидания за жизнь соединения, а не за одну операцию [практика].

### D-05. Что выполняется сейчас

```sql
SELECT r.session_id, r.status, r.command, DB_NAME(r.database_id) AS db,
       r.blocking_session_id AS blocked_by,
       r.wait_type, r.wait_time AS wait_ms, r.wait_resource, r.last_wait_type,
       r.total_elapsed_time / 1000 AS elapsed_s, r.cpu_time AS cpu_ms,
       r.logical_reads, r.reads, r.writes,
       r.granted_query_memory * 8 / 1024 AS grant_mb,      -- в страницах по 8 КБ
       r.open_transaction_count AS open_tran,
       r.transaction_isolation_level AS iso,               -- 2 = ReadCommitted, 4 = Serializable
       s.host_name, s.program_name, s.login_name,
       SUBSTRING(t.text, r.statement_start_offset / 2 + 1,
         (CASE r.statement_end_offset WHEN -1 THEN DATALENGTH(t.text)
               ELSE r.statement_end_offset END - r.statement_start_offset) / 2 + 1) AS current_statement,
       r.plan_handle
FROM sys.dm_exec_requests AS r
JOIN sys.dm_exec_sessions AS s ON s.session_id = r.session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) AS t
WHERE s.is_user_process = 1 AND r.session_id <> @@SPID
ORDER BY r.total_elapsed_time DESC;
-- план: SELECT query_plan FROM sys.dm_exec_query_plan(0x06…);
-- «живой» план (2016 SP1+): SELECT query_plan FROM sys.dm_exec_query_statistics_xml(123);
```

### D-06. Сеансы с открытой транзакцией, включая спящие

```sql
SELECT s.session_id, s.status, s.host_name, s.program_name, s.login_name,
       DB_NAME(s.database_id) AS db, s.open_transaction_count,
       s.last_request_start_time, s.last_request_end_time,
       DATEDIFF(SECOND, s.last_request_end_time, GETDATE()) AS idle_s,
       at.transaction_begin_time,
       DATEDIFF(SECOND, at.transaction_begin_time, GETDATE()) AS tran_s,
       ib.event_info AS last_statement
FROM sys.dm_exec_sessions AS s
LEFT JOIN sys.dm_tran_session_transactions AS st ON st.session_id = s.session_id
LEFT JOIN sys.dm_tran_active_transactions  AS at ON at.transaction_id = st.transaction_id
OUTER APPLY sys.dm_exec_input_buffer(s.session_id, NULL) AS ib
WHERE s.is_user_process = 1 AND s.open_transaction_count > 0
ORDER BY at.transaction_begin_time;
```

`Sleeping` с большими `tran_s` и `idle_s` — транзакция открыта без запросов: 1С исполняет код внутри транзакции или соединение «осиротело» (5.2) [MS Learn]. `open_transaction_count` в `sys.dm_exec_sessions` — с 2012, `sys.dm_exec_input_buffer` — с 2014 SP2 [MS Learn].

### D-07. Цепочки блокировок с головным блокирующим

```sql
WITH s AS (
  SELECT ses.session_id,
         ISNULL(req.blocking_session_id, 0)             AS blocked_by,
         ses.status AS session_status, req.status       AS request_status,
         req.wait_type, req.wait_time, req.wait_resource,
         ses.open_transaction_count, ses.host_name, ses.program_name, ses.login_name,
         DB_NAME(ISNULL(req.database_id, ses.database_id)) AS db,
         ses.last_request_start_time,
         COALESCE(req.sql_handle, con.most_recent_sql_handle) AS sql_handle
  FROM sys.dm_exec_sessions AS ses
  LEFT JOIN sys.dm_exec_requests    AS req ON req.session_id = ses.session_id
  LEFT JOIN sys.dm_exec_connections AS con ON con.session_id = ses.session_id
  WHERE ses.is_user_process = 1
),
chain AS (
  SELECT s.session_id AS head_session_id, s.session_id, s.blocked_by, 0 AS lvl
  FROM s
  WHERE s.blocked_by = 0
    AND EXISTS (SELECT 1 FROM s AS w WHERE w.blocked_by = s.session_id AND w.session_id <> s.session_id)
  UNION ALL
  SELECT c.head_session_id, w.session_id, w.blocked_by, c.lvl + 1
  FROM s AS w
  JOIN chain AS c ON w.blocked_by = c.session_id
  WHERE w.session_id <> w.blocked_by            -- параллельные потоки одного запроса
)
SELECT c.head_session_id, c.lvl,
       REPLICATE(N'    ', c.lvl) + CAST(c.session_id AS nvarchar(10)) AS tree,
       s.session_status, s.request_status, s.open_transaction_count AS open_tran,
       s.wait_type, s.wait_time AS wait_ms, s.wait_resource, s.db,
       s.host_name, s.program_name, s.login_name, s.last_request_start_time,
       LEFT(t.text, 500) AS sql_text,
       CASE WHEN c.lvl = 0
            THEN (SELECT ib.event_info FROM sys.dm_exec_input_buffer(c.session_id, NULL) AS ib)
       END AS head_input_buffer
FROM chain AS c
JOIN s ON s.session_id = c.session_id
OUTER APPLY sys.dm_exec_sql_text(s.sql_handle) AS t
ORDER BY c.head_session_id, c.lvl
OPTION (MAXRECURSION 100);
```

`lvl = 0` — головные; `session_status = sleeping` и `open_tran > 0` — держит транзакцию без активного запроса (5.2), дальше — консоль кластера по «Соединению с СУБД» (2.4). Отрицательные `blocking_session_id` (`-2`, `-3`, `-4`) не разворачиваются — D-08, 4.1. Основа — запросы статьи поддержки Microsoft о блокировках [MS Learn], переписанные с учётом спящих сеансов.

### D-08. Кто ждёт, на какой таблице и в каком режиме

```sql
USE [buh];   -- sys.partitions / sys.objects / sys.indexes — представления текущей базы
SELECT wt.session_id AS waiting_session, wt.blocking_session_id AS blocker,
       wt.wait_type, wt.wait_duration_ms,
       tl.resource_type, tl.request_mode, tl.request_status,
       OBJECT_SCHEMA_NAME(COALESCE(p.object_id, o.object_id)) + N'.'
         + OBJECT_NAME(COALESCE(p.object_id, o.object_id)) AS table_name,
       i.name AS index_name,
       wt.resource_description
FROM sys.dm_os_waiting_tasks AS wt
JOIN sys.dm_tran_locks AS tl ON tl.lock_owner_address = wt.resource_address
LEFT JOIN sys.partitions AS p ON p.hobt_id = tl.resource_associated_entity_id
                             AND tl.resource_type IN (N'KEY', N'PAGE', N'RID', N'HOBT')
LEFT JOIN sys.objects AS o    ON o.object_id = tl.resource_associated_entity_id
                             AND tl.resource_type = N'OBJECT'
LEFT JOIN sys.indexes AS i    ON i.object_id = p.object_id AND i.index_id = p.index_id
WHERE tl.resource_database_id = DB_ID()
ORDER BY wt.wait_duration_ms DESC;
```

Соединение `lock_owner_address = resource_address` — из статьи поддержки Microsoft [MS Learn]. `dbo._AccumRgT1234` → объект 1С (2.6). `request_mode` вида `RangeS-U` — диапазонные блокировки, т. е. Serializable. Уточнено 20.10.2026 по MS Learn (sys.dm_tran_locks): `RangeS_S` — «serializable range scan», `RangeS_U` — «serializable update scan», `RangeI_N` — проверка диапазона перед вставкой; в справке DMV режимы записаны через «_», в классе трассировки Blocked Process Report — через «-»; точное написание сверьте по выводу своей версии.

### D-09. Расшифровка `wait_resource`

```sql
-- KEY: 5:72057594214350848 (1a39e6095155)  ->  база 5, hobt_id 72057594214350848
SELECT DB_NAME(5) AS db;
USE [buh];
SELECT OBJECT_SCHEMA_NAME(p.object_id) AS sch, OBJECT_NAME(p.object_id) AS table_name,
       i.name AS index_name, p.index_id, p.partition_number, p.rows
FROM sys.partitions AS p
JOIN sys.indexes AS i ON i.object_id = p.object_id AND i.index_id = p.index_id
WHERE p.hobt_id = 72057594214350848;

-- PAGE у текущих ожиданий (2019+): page_resource -> файл/страница -> объект
SELECT r.session_id, r.wait_type, r.wait_resource,
       OBJECT_NAME(pi.object_id, pi.database_id) AS table_name, pi.index_id, pi.page_type_desc
FROM sys.dm_exec_requests AS r
CROSS APPLY sys.fn_PageResCracker(r.page_resource) AS pr
CROSS APPLY sys.dm_db_page_info(pr.db_id, pr.file_id, pr.page_id, 'DETAILED') AS pi;
```

`sys.fn_PageResCracker` и `sys.dm_db_page_info(DatabaseId, FileId, PageId, Mode)` (`'LIMITED'` по умолчанию) — с 2019 [MS Learn]; на 2016–2017 — `DBCC PAGE` по методике 1С (недокументирована — Подтверждено 20.10.2026 по каталогу DBCC MS Learn).

### D-10. Длинные транзакции и объём журнала

```sql
SELECT st.session_id,                                   -- «Соединение с СУБД» [ИТС-мет 5813]
       s.status, s.host_name, s.program_name, s.login_name,
       DB_NAME(dt.database_id) AS db,
       at.transaction_begin_time,
       DATEDIFF(SECOND, at.transaction_begin_time, GETDATE()) AS tran_s,
       at.transaction_type,      -- 1 чтение-запись, 2 только чтение, 3 системная, 4 распределённая
       at.transaction_state,     -- 2 активна, 6 зафиксирована, 7 откатывается … [ИТС-мет 5813]
       dt.database_transaction_log_record_count            AS log_records,
       dt.database_transaction_log_bytes_used / 1048576     AS log_used_mb,
       dt.database_transaction_log_bytes_reserved / 1048576 AS log_reserved_mb,
       LEFT(t.text, 500) AS last_sql
FROM sys.dm_tran_session_transactions AS st
JOIN sys.dm_tran_active_transactions  AS at ON at.transaction_id = st.transaction_id
LEFT JOIN sys.dm_tran_database_transactions AS dt ON dt.transaction_id = st.transaction_id
JOIN sys.dm_exec_sessions             AS s  ON s.session_id = st.session_id
LEFT JOIN sys.dm_exec_connections     AS c  ON c.session_id = st.session_id
OUTER APPLY sys.dm_exec_sql_text(c.most_recent_sql_handle) AS t
ORDER BY at.transaction_begin_time;
-- быстро по базе: DBCC OPENTRAN ('buh');
```

Строка на каждую затронутую базу, в том числе tempdb [MS Learn].

### D-11. Хранилище версий и его «держатели»

```sql
-- объём версий по базам (2016 SP2+; лёгкий запрос)
SELECT DB_NAME(database_id) AS db, reserved_page_count, reserved_space_kb / 1024 AS reserved_mb
FROM sys.dm_tran_version_store_space_usage
ORDER BY reserved_space_kb DESC;

-- транзакции, которые могут удерживать версии
SELECT TOP (10) a.session_id, a.transaction_id, a.elapsed_time_seconds, a.is_snapshot,
       s.host_name, s.program_name, s.login_name, s.status
FROM sys.dm_tran_active_snapshot_database_transactions AS a
LEFT JOIN sys.dm_exec_sessions AS s ON s.session_id = a.session_id
ORDER BY a.elapsed_time_seconds DESC;
```

Второй запрос — и в [ИТС-мет 5813]; «держатель» — спящий сеанс 1С → 5.2, 5.4.

### D-12. Взаимоблокировки из `system_health` (2017+)

```sql
WITH x AS (
  SELECT CAST(f.timestamp_utc AS datetime2(0)) AS utc_time,
         CAST(f.event_data AS xml)            AS ed
  FROM sys.fn_xe_file_target_read_file(N'system_health*.xel', NULL, NULL, NULL) AS f
  WHERE f.object_name = N'xml_deadlock_report'
    AND CAST(f.timestamp_utc AS datetime2(7)) > DATEADD(DAY, -7, SYSUTCDATETIME())
)
SELECT x.utc_time,
       CASE WHEN p.n.value('@id', 'nvarchar(100)')
                 = x.ed.value('(//deadlock/victim-list/victimProcess/@id)[1]', 'nvarchar(100)')
            THEN N'ЖЕРТВА' ELSE N'' END                     AS role,
       p.n.value('@spid', 'int')                             AS spid,
       p.n.value('@isolationlevel', 'nvarchar(60)')          AS isolation_level,
       p.n.value('@lockMode', 'nvarchar(20)')                AS lock_mode,
       p.n.value('@waitresource', 'nvarchar(200)')           AS wait_resource,
       p.n.value('@transactionname', 'nvarchar(60)')         AS tran_name,
       p.n.value('@hostname', 'nvarchar(128)')               AS host_name,
       p.n.value('@clientapp', 'nvarchar(256)')              AS client_app,
       p.n.value('@loginname', 'nvarchar(128)')              AS login_name,
       LEFT(p.n.value('(inputbuf)[1]', 'nvarchar(max)'), 400) AS input_buffer,
       x.ed AS full_event                                     -- щёлкнуть в SSMS — полный граф
FROM x
CROSS APPLY x.ed.nodes('//deadlock/process-list/process') AS p(n)
ORDER BY x.utc_time DESC, role DESC;

-- ресурсы: таблицы и индексы
WITH x AS (
  SELECT CAST(f.timestamp_utc AS datetime2(0)) AS utc_time, CAST(f.event_data AS xml) AS ed
  FROM sys.fn_xe_file_target_read_file(N'system_health*.xel', NULL, NULL, NULL) AS f
  WHERE f.object_name = N'xml_deadlock_report')
SELECT x.utc_time, r.n.value('local-name(.)', 'nvarchar(40)') AS lock_kind,
       r.n.value('@objectname', 'nvarchar(400)') AS object_name,
       r.n.value('@indexname', 'nvarchar(400)')  AS index_name,
       r.n.value('@mode', 'nvarchar(20)')        AS held_mode
FROM x CROSS APPLY x.ed.nodes('//deadlock/resource-list/*') AS r(n)
ORDER BY x.utc_time DESC;
```

Атрибуты — по образцу графа Microsoft [MS Learn]. На 2016 нет `timestamp_utc` — время из `x.ed.value('(event/@timestamp)[1]', 'datetime2')` [практика]. Для сеанса `1c_blocking` — маска `N'E:\XE\1c_blocking*.xel'`.

### D-13. Отчёты о заблокированных процессах из XE

```sql
WITH x AS (
  SELECT CAST(f.timestamp_utc AS datetime2(0)) AS utc_time, CAST(f.event_data AS xml) AS ed
  FROM sys.fn_xe_file_target_read_file(N'E:\XE\1c_blocking*.xel', NULL, NULL, NULL) AS f
  WHERE f.object_name = N'blocked_process_report'
)
SELECT x.utc_time,
       x.ed.value('(//data[@name="duration"]/value)[1]', 'bigint') / 1000 AS blocked_ms,   -- ⚠ мкс
       r.n.value('(blocked-process/process/@spid)[1]', 'int')               AS blocked_spid,
       r.n.value('(blocked-process/process/@waitresource)[1]', 'nvarchar(200)') AS wait_resource,
       r.n.value('(blocked-process/process/@isolationlevel)[1]', 'nvarchar(60)') AS blocked_iso,
       LEFT(r.n.value('(blocked-process/process/inputbuf)[1]', 'nvarchar(max)'), 300) AS blocked_sql,
       r.n.value('(blocking-process/process/@spid)[1]', 'int')              AS blocking_spid,
       r.n.value('(blocking-process/process/@status)[1]', 'nvarchar(30)')   AS blocking_status,
       r.n.value('(blocking-process/process/@trancount)[1]', 'int')         AS blocking_trancount,
       r.n.value('(blocking-process/process/@hostname)[1]', 'nvarchar(128)') AS blocking_host,
       LEFT(r.n.value('(blocking-process/process/inputbuf)[1]', 'nvarchar(max)'), 300) AS blocking_sql
FROM x
CROSS APPLY x.ed.nodes('//blocked-process-report') AS r(n)
ORDER BY x.utc_time DESC;
```

Структура XML — по практике ⚠ (5.5); `duration` — микросекунды: так у колонки `Duration` класса трассировки Blocked Process Report [MS Learn], для XE — по аналогии ⚠. `blocking_status = sleeping` и `blocking_trancount > 0` — спящий головной сеанс 1С.

### D-14. Топ по CPU из кеша планов

```sql
SELECT TOP (20)
       DB_NAME(CONVERT(int, pa.value)) AS db,
       qs.execution_count,
       qs.total_worker_time / 1000                         AS total_cpu_ms,   -- мкс -> мс
       qs.total_worker_time / qs.execution_count / 1000    AS avg_cpu_ms,
       qs.total_elapsed_time / qs.execution_count / 1000   AS avg_elapsed_ms,
       qs.total_logical_reads / qs.execution_count         AS avg_logical_reads,
       qs.total_rows / qs.execution_count                  AS avg_rows,
       qs.plan_generation_num, qs.creation_time, qs.last_execution_time,
       SUBSTRING(st.text, qs.statement_start_offset / 2 + 1,
         (CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
               ELSE qs.statement_end_offset END - qs.statement_start_offset) / 2 + 1) AS statement_text,
       qs.query_hash, qs.plan_handle
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
CROSS APPLY sys.dm_exec_plan_attributes(qs.plan_handle) AS pa
WHERE pa.attribute = N'dbid'
  -- AND CONVERT(int, pa.value) = DB_ID(N'buh')                    -- одна база
  -- AND qs.last_execution_time > DATEADD(HOUR, -1, GETDATE())    -- «за последний час» [ИТС-мет 5861]
ORDER BY qs.total_worker_time DESC;
```

База — из атрибута `dbid` плана, как в [ИТС-мет 5861; 5813] (9.1). Таблицы из `statement_text` → шаблон 12.2 Б.

### D-15. Топ по чтениям

```sql
SELECT TOP (20)
       DB_NAME(CONVERT(int, pa.value)) AS db,
       qs.execution_count,
       qs.total_logical_reads, qs.total_physical_reads, qs.total_logical_writes,
       qs.total_logical_reads / qs.execution_count  AS avg_logical_reads,
       qs.total_physical_reads / qs.execution_count AS avg_physical_reads,
       qs.total_elapsed_time / qs.execution_count / 1000 AS avg_elapsed_ms,
       SUBSTRING(st.text, qs.statement_start_offset / 2 + 1,
         (CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
               ELSE qs.statement_end_offset END - qs.statement_start_offset) / 2 + 1) AS statement_text,
       qs.plan_handle
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
CROSS APPLY sys.dm_exec_plan_attributes(qs.plan_handle) AS pa
WHERE pa.attribute = N'dbid'
ORDER BY qs.total_physical_reads DESC;     -- диск; память/CPU: ORDER BY qs.total_logical_reads DESC
```

Аналог запросов [ИТС-мет 5813] «нагрузка на диск» и «высокие издержки на ввод-вывод».

### D-16. Агрегация по `query_hash`

```sql
SELECT TOP (20) qs.query_hash,
       COUNT(*)                         AS statements_in_cache,
       SUM(qs.execution_count)          AS executions,
       SUM(qs.total_worker_time) / 1000 AS total_cpu_ms,
       CAST(100.0 * SUM(qs.total_worker_time) / SUM(SUM(qs.total_worker_time)) OVER ()
            AS decimal(5,2))            AS cpu_pct,
       SUM(qs.total_elapsed_time) / 1000 AS total_elapsed_ms,
       SUM(qs.total_logical_reads)      AS total_logical_reads,
       MIN(SUBSTRING(st.text, qs.statement_start_offset / 2 + 1, 400)) AS sample_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
GROUP BY qs.query_hash
ORDER BY total_cpu_ms DESC;
```

Большой `statements_in_cache` при малом `cpu_pct` верхних строк — нагрузка «размазана», путь 5910 (9.4) [ИТС-мет 5910; MS Learn].

### D-17. Нагрузка по базам

```sql
WITH db AS (
  SELECT CONVERT(int, pa.value)       AS database_id,
         SUM(qs.total_worker_time)    AS cpu_us,
         SUM(qs.total_logical_reads)  AS logical_reads,
         SUM(qs.total_physical_reads) AS physical_reads
  FROM sys.dm_exec_query_stats AS qs
  CROSS APPLY sys.dm_exec_plan_attributes(qs.plan_handle) AS pa
  WHERE pa.attribute = N'dbid'
    -- AND qs.last_execution_time > DATEADD(HOUR, -1, GETDATE())    -- за последний час [ИТС-мет 5861]
  GROUP BY CONVERT(int, pa.value))
SELECT DB_NAME(database_id) AS db,
       cpu_us / 1000 AS cpu_ms,
       CAST(100.0 * cpu_us / SUM(cpu_us) OVER () AS decimal(5,2)) AS cpu_pct,
       logical_reads, physical_reads,
       CAST(100.0 * physical_reads / NULLIF(SUM(physical_reads) OVER (), 0) AS decimal(5,2)) AS phys_reads_pct
FROM db
WHERE database_id > 4 AND database_id <> 32767       -- без системных и Resource [ИТС-мет 5861]
ORDER BY cpu_us DESC;
```

Объединяет «Нагрузку на CPU по базам» [ИТС-мет 5861; 5910] и «Базы, создающие нагрузку на диск» [ИТС-мет 5813] с правильными единицами.

### D-18. Самые частые запросы

```sql
SELECT TOP (20) qs.execution_count,
       CAST(qs.execution_count * 1.0
            / NULLIF(DATEDIFF(SECOND, qs.creation_time, qs.last_execution_time), 0) AS decimal(18,2)) AS per_sec,
       qs.total_worker_time / qs.execution_count AS avg_cpu_us,
       qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
       DB_NAME(CONVERT(int, pa.value)) AS db,
       SUBSTRING(st.text, qs.statement_start_offset / 2 + 1,
         (CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
               ELSE qs.statement_end_offset END - qs.statement_start_offset) / 2 + 1) AS statement_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
CROSS APPLY sys.dm_exec_plan_attributes(qs.plan_handle) AS pa
WHERE pa.attribute = N'dbid'
ORDER BY qs.execution_count DESC;
```

Методики 1С проверяют, не дают ли частые запросы основную нагрузку на CPU [ИТС-мет 5861]; служебный опрос блокировок платформы (2.5) тоже окажется вверху — это нормально.

### D-19. Гранты памяти и сбросы на диск (2016+)

```sql
SELECT TOP (20) qs.execution_count,
       qs.total_grant_kb / qs.execution_count / 1024       AS avg_grant_mb,
       qs.total_used_grant_kb / qs.execution_count / 1024  AS avg_used_grant_mb,
       qs.total_ideal_grant_kb / qs.execution_count / 1024 AS avg_ideal_grant_mb,
       qs.total_spills / qs.execution_count                AS avg_spill_pages,   -- 2016 SP2 / 2017 CU3+
       qs.last_dop,
       SUBSTRING(st.text, qs.statement_start_offset / 2 + 1,
         (CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
               ELSE qs.statement_end_offset END - qs.statement_start_offset) / 2 + 1) AS statement_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
ORDER BY qs.total_grant_kb DESC;
```

Использована малая доля гранта — переоценка строк; ненулевые сбросы — недооценка (сортировка/хеш ушли в tempdb) [MS Learn — колонки; интерпретация — практика].

### D-20. Кто ждёт память сейчас

```sql
SELECT mg.session_id, mg.request_time, mg.grant_time, mg.wait_time_ms,
       mg.requested_memory_kb / 1024 AS requested_mb, mg.granted_memory_kb / 1024 AS granted_mb,
       mg.used_memory_kb / 1024 AS used_mb, mg.ideal_memory_kb / 1024 AS ideal_mb,
       mg.dop, mg.query_cost, LEFT(t.text, 300) AS sql_text
FROM sys.dm_exec_query_memory_grants AS mg
OUTER APPLY sys.dm_exec_sql_text(mg.sql_handle) AS t
ORDER BY mg.grant_time, mg.requested_memory_kb DESC;    -- grant_time IS NULL — ещё ждут (вверху)
```

Строки с `grant_time IS NULL` — это `RESOURCE_SEMAPHORE` и `Memory Grants Pending` [MS Learn].

### D-21. Задержки ввода-вывода по файлам

```sql
-- накопленные с момента старта
SELECT DB_NAME(vfs.database_id) AS db, mf.type_desc, mf.physical_name,
       vfs.num_of_reads, vfs.num_of_writes,
       CAST(1.0 * vfs.io_stall_read_ms  / NULLIF(vfs.num_of_reads, 0)  AS decimal(10,1)) AS avg_read_ms,
       CAST(1.0 * vfs.io_stall_write_ms / NULLIF(vfs.num_of_writes, 0) AS decimal(10,1)) AS avg_write_ms,
       vfs.num_of_bytes_read / 1048576 AS read_mb, vfs.num_of_bytes_written / 1048576 AS written_mb,
       vfs.size_on_disk_bytes / 1048576 AS size_mb
FROM sys.dm_io_virtual_file_stats(NULL, NULL) AS vfs
JOIN sys.master_files AS mf ON mf.database_id = vfs.database_id AND mf.file_id = vfs.file_id
ORDER BY vfs.io_stall DESC;

-- дельта за 5 минут — картина «сейчас»
IF OBJECT_ID(N'tempdb..#f1') IS NOT NULL DROP TABLE #f1;
SELECT database_id, file_id, num_of_reads, io_stall_read_ms, num_of_writes, io_stall_write_ms
INTO #f1 FROM sys.dm_io_virtual_file_stats(NULL, NULL);
WAITFOR DELAY '00:05:00';
SELECT DB_NAME(v.database_id) AS db, mf.physical_name,
       v.num_of_reads - f.num_of_reads AS reads,
       CAST(1.0 * (v.io_stall_read_ms - f.io_stall_read_ms)
            / NULLIF(v.num_of_reads - f.num_of_reads, 0) AS decimal(10,1)) AS avg_read_ms,
       v.num_of_writes - f.num_of_writes AS writes,
       CAST(1.0 * (v.io_stall_write_ms - f.io_stall_write_ms)
            / NULLIF(v.num_of_writes - f.num_of_writes, 0) AS decimal(10,1)) AS avg_write_ms
FROM sys.dm_io_virtual_file_stats(NULL, NULL) AS v
JOIN #f1 AS f ON f.database_id = v.database_id AND f.file_id = v.file_id
JOIN sys.master_files AS mf ON mf.database_id = v.database_id AND mf.file_id = v.file_id
ORDER BY (v.io_stall_read_ms - f.io_stall_read_ms) + (v.io_stall_write_ms - f.io_stall_write_ms) DESC;
DROP TABLE #f1;
```

Накопленные средние «размывают» ночные пики регламента — дневные жалобы разбирать по дельте [практика]; ориентиры — 10.1.

### D-22. Свободное место томов

```sql
SELECT DISTINCT vs.volume_mount_point, vs.file_system_type,
       vs.total_bytes / 1073741824     AS total_gb,
       vs.available_bytes / 1073741824 AS free_gb,
       CAST(100.0 * vs.available_bytes / vs.total_bytes AS decimal(5,1)) AS free_pct
FROM sys.master_files AS mf
CROSS APPLY sys.dm_os_volume_stats(mf.database_id, mf.file_id) AS vs
ORDER BY free_pct;
```

Оповещение 1С — меньше 10 % [ИТС-мет 5899]; на Linux часть колонок `NULL` [MS Learn].

### D-23. Память

```sql
SELECT total_physical_memory_kb / 1024 AS os_total_mb, available_physical_memory_kb / 1024 AS os_available_mb,
       system_memory_state_desc
FROM sys.dm_os_sys_memory;

SELECT physical_memory_in_use_kb / 1024 AS sql_in_use_mb, locked_page_allocations_kb / 1024 AS locked_pages_mb,
       memory_utilization_percentage, process_physical_memory_low, process_virtual_memory_low
FROM sys.dm_os_process_memory;

SELECT TOP (15) [type], SUM(pages_kb) / 1024 AS mb          -- pages_kb с 2012 (в 5813 — single_pages_kb)
FROM sys.dm_os_memory_clerks
GROUP BY [type] ORDER BY mb DESC;

SELECT DB_NAME(database_id) AS db, COUNT_BIG(*) * 8 / 1024 AS buffer_mb   -- тяжёлый на большом пуле
FROM sys.dm_os_buffer_descriptors
GROUP BY database_id ORDER BY buffer_mb DESC;
```

Интерпретация — 10.3.

### D-24. Мгновенные счётчики через DMV

```sql
SELECT RTRIM(object_name) AS object_name, RTRIM(counter_name) AS counter_name,
       RTRIM(instance_name) AS instance_name, cntr_value
FROM sys.dm_os_performance_counters
WHERE (object_name LIKE N'%:Buffer Manager%'      AND counter_name = N'Page life expectancy')
   OR (object_name LIKE N'%:Memory Manager%'      AND counter_name IN (N'Memory Grants Pending',
        N'Memory Grants Outstanding', N'Total Server Memory (KB)', N'Target Server Memory (KB)'))
   OR (object_name LIKE N'%:General Statistics%'  AND counter_name IN (N'User Connections', N'Processes blocked'))
   OR (object_name LIKE N'%:Transactions%'        AND counter_name IN (N'Free Space in tempdb (KB)',
        N'Version Store Size (KB)', N'Longest Transaction Running Time'))
   OR (object_name LIKE N'%:Databases%'           AND counter_name IN (N'Percent Log Used', N'Log Growths')
        AND instance_name = N'buh');
```

Маска `%:Объект%` подходит и для `SQLServer:`, и для именованного экземпляра [практика]; это счётчики типа 65792 — мгновенные [MS Learn].

### D-25. Счётчики «в секунду» через DMV

```sql
DECLARE @s TABLE (object_name nchar(128), counter_name nchar(128), instance_name nchar(128), cntr_value bigint);
INSERT @s
SELECT object_name, counter_name, instance_name, cntr_value
FROM sys.dm_os_performance_counters
WHERE cntr_type = 272696576
  AND counter_name IN (N'Batch Requests/sec', N'SQL Compilations/sec', N'SQL Re-Compilations/sec',
                       N'Lock Waits/sec', N'Lock Timeouts/sec', N'Number of Deadlocks/sec',
                       N'Page reads/sec', N'Full Scans/sec', N'Index Searches/sec', N'Page Splits/sec',
                       N'Log Flushes/sec', N'Logins/sec');
WAITFOR DELAY '00:00:10';
SELECT RTRIM(p.object_name) AS object_name, RTRIM(p.counter_name) AS counter_name,
       RTRIM(p.instance_name) AS instance_name,
       CAST((p.cntr_value - s.cntr_value) / 10.0 AS decimal(18,1)) AS per_sec
FROM sys.dm_os_performance_counters AS p
JOIN @s AS s ON s.object_name = p.object_name AND s.counter_name = p.counter_name
            AND s.instance_name = p.instance_name
WHERE p.cntr_value - s.cntr_value > 0
ORDER BY object_name, counter_name, instance_name;
```

Для таких счётчиков `cntr_value` накопительный — скорость по разнице снимков [MS Learn].

### D-26. tempdb: чем занята и кем

```sql
USE tempdb;
SELECT SUM(total_page_count) * 8 / 1024                    AS total_mb,
       SUM(unallocated_extent_page_count) * 8 / 1024       AS free_mb,
       SUM(version_store_reserved_page_count) * 8 / 1024   AS version_store_mb,   -- RCSI баз 1С
       SUM(user_object_reserved_page_count) * 8 / 1024     AS user_objects_mb,    -- #tt и др.
       SUM(internal_object_reserved_page_count) * 8 / 1024 AS internal_objects_mb -- сортировки, хеши, спулы
FROM sys.dm_db_file_space_usage;

-- сеансы: выделено минус освобождено (завершённые задачи + текущие)
SELECT TOP (10) ss.session_id, s.host_name, s.program_name, s.login_name, s.status,
       (ss.user_objects_alloc_page_count - ss.user_objects_dealloc_page_count
        + ISNULL(ts.user_alloc, 0) - ISNULL(ts.user_dealloc, 0)) * 8 / 1024             AS user_mb,
       (ss.internal_objects_alloc_page_count - ss.internal_objects_dealloc_page_count
        + ISNULL(ts.int_alloc, 0) - ISNULL(ts.int_dealloc, 0)) * 8 / 1024               AS internal_mb
FROM sys.dm_db_session_space_usage AS ss
JOIN sys.dm_exec_sessions AS s ON s.session_id = ss.session_id
LEFT JOIN (SELECT session_id,
                  SUM(user_objects_alloc_page_count)       AS user_alloc,
                  SUM(user_objects_dealloc_page_count)     AS user_dealloc,
                  SUM(internal_objects_alloc_page_count)   AS int_alloc,
                  SUM(internal_objects_dealloc_page_count) AS int_dealloc
           FROM sys.dm_db_task_space_usage GROUP BY session_id) AS ts ON ts.session_id = ss.session_id
WHERE s.is_user_process = 1
ORDER BY user_mb + internal_mb DESC;
```

Идея «свободно в tempdb» — [ИТС-мет 5813]. Большой `version_store_mb` — долгая транзакция (D-11); большой `user_objects_mb` у сеанса — временные таблицы тяжёлого отчёта или незакрытый `МенеджерВременныхТаблиц` ⚠ [практика].

### D-27. Планировщики

```sql
SELECT scheduler_id, cpu_id, status, current_tasks_count, runnable_tasks_count,
       current_workers_count, active_workers_count, work_queue_count, pending_disk_io_count, load_factor
FROM sys.dm_os_schedulers
WHERE status = N'VISIBLE ONLINE'
ORDER BY runnable_tasks_count DESC;
```

`runnable_tasks_count` — очередь к CPU, `work_queue_count` — задачи без рабочего потока [MS Learn].

### D-28. Query Store: состояние

```sql
USE [buh];
SELECT actual_state_desc, desired_state_desc, readonly_reason,     -- 65536 = превышен размер
       current_storage_size_mb, max_storage_size_mb,
       query_capture_mode_desc, size_based_cleanup_mode_desc,
       stale_query_threshold_days, interval_length_minutes, flush_interval_seconds,
       wait_stats_capture_mode_desc                                 -- 2017+
FROM sys.database_query_store_options;
```

Расхождение `actual_state_desc` и `desired_state_desc` — Query Store сам сменил режим [MS Learn].

### D-29. Query Store: топ за сутки

```sql
USE [buh];
DECLARE @from datetimeoffset = DATEADD(HOUR, -24, SYSDATETIMEOFFSET());
SELECT TOP (20) q.query_id,
       SUM(rs.count_executions)                                          AS executions,
       CAST(SUM(rs.avg_cpu_time * rs.count_executions) / 1000 AS bigint) AS total_cpu_ms,      -- мкс -> мс
       CAST(SUM(rs.avg_duration * rs.count_executions) / 1000 AS bigint) AS total_duration_ms,
       CAST(SUM(rs.avg_logical_io_reads * rs.count_executions) AS bigint) AS total_logical_reads, -- страниц
       COUNT(DISTINCT p.plan_id)                                         AS plans,
       SUM(CASE WHEN rs.execution_type = 3 THEN rs.count_executions ELSE 0 END) AS aborted_by_client,
       SUM(CASE WHEN rs.execution_type = 4 THEN rs.count_executions ELSE 0 END) AS aborted_by_error,
       MAX(LEFT(qt.query_sql_text, 400))                                 AS sql_text
FROM sys.query_store_runtime_stats          AS rs
JOIN sys.query_store_runtime_stats_interval AS i  ON i.runtime_stats_interval_id = rs.runtime_stats_interval_id
JOIN sys.query_store_plan                   AS p  ON p.plan_id = rs.plan_id
JOIN sys.query_store_query                  AS q  ON q.query_id = p.query_id
JOIN sys.query_store_query_text             AS qt ON qt.query_text_id = q.query_text_id
WHERE i.start_time >= @from
GROUP BY q.query_id
ORDER BY total_cpu_ms DESC;
```

`avg_duration`, `avg_cpu_time` — мкс; `avg_logical_io_reads` — страницы по 8 КБ; `execution_type`: 0 обычное, 3 прервано клиентом, 4 исключением [MS Learn]. Много прерываний клиентом — отмены или тайм-ауты 1С (7.4) [практика].

### D-30. Query Store: регрессии (24 ч против 7 дней до них)

```sql
USE [buh];
DECLARE @now datetimeoffset = SYSDATETIMEOFFSET();
WITH r AS (
  SELECT p.query_id,
         SUM(CASE WHEN i.start_time >= DATEADD(HOUR, -24, @now) THEN rs.avg_duration * rs.count_executions END) AS dur_recent,
         SUM(CASE WHEN i.start_time >= DATEADD(HOUR, -24, @now) THEN rs.count_executions END)                  AS exec_recent,
         SUM(CASE WHEN i.start_time <  DATEADD(HOUR, -24, @now) THEN rs.avg_duration * rs.count_executions END) AS dur_hist,
         SUM(CASE WHEN i.start_time <  DATEADD(HOUR, -24, @now) THEN rs.count_executions END)                  AS exec_hist
  FROM sys.query_store_runtime_stats          AS rs
  JOIN sys.query_store_runtime_stats_interval AS i ON i.runtime_stats_interval_id = rs.runtime_stats_interval_id
  JOIN sys.query_store_plan                   AS p ON p.plan_id = rs.plan_id
  WHERE i.start_time >= DATEADD(DAY, -8, @now)
  GROUP BY p.query_id)
SELECT TOP (20) r.query_id, r.exec_recent, r.exec_hist,
       CAST(r.dur_recent / r.exec_recent / 1000 AS decimal(18,1)) AS avg_ms_recent,
       CAST(r.dur_hist   / r.exec_hist   / 1000 AS decimal(18,1)) AS avg_ms_hist,
       CAST((r.dur_recent / r.exec_recent) / NULLIF(r.dur_hist / r.exec_hist, 0) AS decimal(10,1)) AS slowdown_x,
       LEFT(qt.query_sql_text, 400) AS sql_text
FROM r
JOIN sys.query_store_query      AS q  ON q.query_id = r.query_id
JOIN sys.query_store_query_text AS qt ON qt.query_text_id = q.query_text_id
WHERE r.exec_recent >= 10 AND r.exec_hist >= 10
ORDER BY (r.dur_recent / r.exec_recent - r.dur_hist / r.exec_hist) * r.exec_recent DESC;
```

Сортировка — по «лишнему» суммарному времени за сутки, а не по кратности [практика]. После обновления конфигурации у новых текстов истории нет (8.3).

### D-31. Query Store: запросы с несколькими планами

```sql
USE [buh];
SELECT TOP (20) p.query_id,
       COUNT(DISTINCT p.plan_id)                          AS plans,
       CAST(MIN(rs.avg_duration) / 1000 AS decimal(18,1)) AS best_avg_ms,
       CAST(MAX(rs.avg_duration) / 1000 AS decimal(18,1)) AS worst_avg_ms,
       SUM(rs.count_executions)                           AS executions,
       MAX(CAST(p.is_forced_plan AS int))                 AS has_forced_plan,
       MAX(LEFT(qt.query_sql_text, 300))                  AS sql_text
FROM sys.query_store_plan          AS p
JOIN sys.query_store_runtime_stats AS rs ON rs.plan_id = p.plan_id
JOIN sys.query_store_query         AS q  ON q.query_id = p.query_id
JOIN sys.query_store_query_text    AS qt ON qt.query_text_id = q.query_text_id
GROUP BY p.query_id
HAVING COUNT(DISTINCT p.plan_id) > 1
ORDER BY MAX(rs.avg_duration) / NULLIF(MIN(rs.avg_duration), 0) DESC;
```

Признак чувствительности к параметрам или устаревшей статистики [MS Learn; практика]; сначала статистика и индексы (`05-…`), принуждение — по 8.4.

### D-32. Query Store: ожидания по запросам (2017+)

```sql
USE [buh];
SELECT TOP (20) p.query_id, ws.wait_category_desc,
       SUM(ws.total_query_wait_time_ms)  AS wait_ms,
       MAX(LEFT(qt.query_sql_text, 300)) AS sql_text
FROM sys.query_store_wait_stats             AS ws
JOIN sys.query_store_runtime_stats_interval AS i  ON i.runtime_stats_interval_id = ws.runtime_stats_interval_id
JOIN sys.query_store_plan                   AS p  ON p.plan_id = ws.plan_id
JOIN sys.query_store_query                  AS q  ON q.query_id = p.query_id
JOIN sys.query_store_query_text             AS qt ON qt.query_text_id = q.query_text_id
WHERE i.start_time >= DATEADD(HOUR, -24, SYSDATETIMEOFFSET())
  AND ws.wait_category_desc NOT IN (N'Idle', N'User Wait')
GROUP BY p.query_id, ws.wait_category_desc
ORDER BY wait_ms DESC;
```

Категории: CPU (`SOS_SCHEDULER_YIELD`), Worker Thread (`THREADPOOL`), Lock (`LCK_M_%`), Latch, Buffer Latch (`PAGELATCH_%`), Buffer IO (`PAGEIOLATCH_%`), Compilation, Tran Log IO (`WRITELOG`, `LOGBUFFER`…), Network IO (`ASYNC_NETWORK_IO`…), Parallelism (`CXPACKET`, `CXCONSUMER`, `CXSYNC_*`), Memory (`RESOURCE_SEMAPHORE`, `CMEMTHREAD`…), Other Disk IO (`ASYNC_IO_COMPLETION`, `IO_COMPLETION`…), Idle, User Wait и др.; учитываются только ожидания выполнения, не компиляции [MS Learn].

### D-33. Query Store: принудительные планы

```sql
USE [buh];
SELECT p.plan_id, p.query_id, q.object_id AS containing_object_id,
       p.plan_forcing_type_desc, p.force_failure_count, p.last_force_failure_reason_desc,
       p.last_execution_time, LEFT(qt.query_sql_text, 300) AS sql_text
FROM sys.query_store_plan       AS p
JOIN sys.query_store_query      AS q  ON q.query_id = p.query_id
JOIN sys.query_store_query_text AS qt ON qt.query_text_id = q.query_text_id
WHERE p.is_forced_plan = 1;
-- снять: EXEC sp_query_store_unforce_plan @query_id = <q>, @plan_id = <p>;
```

Основа — запрос из рекомендаций Microsoft [MS Learn]; проверять после каждого обновления конфигурации (8.4).

### D-34. Подсказки об отсутствующих индексах

```sql
USE [buh];
SELECT TOP (20) d.statement AS table_name,
       d.equality_columns, d.inequality_columns, d.included_columns,
       s.user_seeks, s.user_scans, s.last_user_seek,
       s.avg_total_user_cost, s.avg_user_impact,
       CAST(s.avg_total_user_cost * s.avg_user_impact * (s.user_seeks + s.user_scans) AS decimal(18,0)) AS score
FROM sys.dm_db_missing_index_details     AS d
JOIN sys.dm_db_missing_index_groups      AS g ON g.index_handle = d.index_handle
JOIN sys.dm_db_missing_index_group_stats AS s ON s.group_handle = g.index_group_handle
WHERE d.database_id = DB_ID()
ORDER BY score DESC;
```

Ограничения — 9.6; индексы в базе 1С — только через конфигурацию.

### D-35. Тексты серверных курсоров

```sql
DECLARE @spid int = 123;
SELECT c.session_id, c.cursor_id, c.name, c.properties, c.creation_time, c.is_open, c.fetch_status,
       c.worker_time, c.reads, c.writes, c.dormant_duration,
       SUBSTRING(t.text, c.statement_start_offset / 2 + 1,
         (CASE c.statement_end_offset WHEN -1 THEN DATALENGTH(t.text)
               ELSE c.statement_end_offset END - c.statement_start_offset) / 2 + 1) AS cursor_statement
FROM sys.dm_exec_cursors(@spid) AS c          -- 0 — все сеансы
OUTER APPLY sys.dm_exec_sql_text(c.sql_handle) AS t;
```

Для `FETCH API_CURSOR…` в D-05 (2.2) [MS Learn; ⚠ для 1С].

### D-36. Соединения 1С по серверам и логинам

```sql
SELECT s.host_name, s.program_name, s.login_name, DB_NAME(s.database_id) AS db,
       c.client_net_address, c.net_transport, c.encrypt_option, c.auth_scheme,
       COUNT(*) AS sessions,
       SUM(CASE WHEN s.status = N'Running' THEN 1 ELSE 0 END) AS running,
       SUM(CASE WHEN s.open_transaction_count > 0 THEN 1 ELSE 0 END) AS with_open_tran,
       MIN(s.login_time) AS oldest_login
FROM sys.dm_exec_sessions AS s
LEFT JOIN sys.dm_exec_connections AS c ON c.session_id = s.session_id
WHERE s.is_user_process = 1
GROUP BY s.host_name, s.program_name, s.login_name, s.database_id,
         c.client_net_address, c.net_transport, c.encrypt_option, c.auth_scheme
ORDER BY sessions DESC;
```

Какие серверы 1С подключены, сколько соединений у баз, шифруется ли соединение (`encrypt_option`; OLE DB Driver 19 по умолчанию требует шифрования — `02-…`) [MS Learn].

### D-37. Долгие запросы из сеанса `1c_long_queries`

```sql
WITH x AS (
  SELECT f.object_name, CAST(f.timestamp_utc AS datetime2(0)) AS utc_time, CAST(f.event_data AS xml) AS ed
  FROM sys.fn_xe_file_target_read_file(N'E:\XE\1c_long_queries*.xel', NULL, NULL, NULL) AS f
)
SELECT TOP (200) x.utc_time, x.object_name,
       x.ed.value('(event/data[@name="duration"]/value)[1]', 'bigint') / 1000       AS duration_ms,  -- ⚠ мкс
       x.ed.value('(event/data[@name="cpu_time"]/value)[1]', 'bigint') / 1000       AS cpu_ms,       -- ⚠ мкс
       x.ed.value('(event/data[@name="logical_reads"]/value)[1]', 'bigint')         AS logical_reads,-- ⚠ имя поля
       x.ed.value('(event/data[@name="physical_reads"]/value)[1]', 'bigint')        AS physical_reads,
       x.ed.value('(event/data[@name="writes"]/value)[1]', 'bigint')                AS writes,
       x.ed.value('(event/action[@name="session_id"]/value)[1]', 'int')             AS session_id,
       x.ed.value('(event/action[@name="client_pid"]/value)[1]', 'int')             AS client_pid,
       LEFT(x.ed.value('(event/action[@name="sql_text"]/value)[1]', 'nvarchar(max)'), 500) AS sql_text
FROM x
ORDER BY duration_ms DESC;
```

Пути `event/data[@name=…]`, `event/action[@name=…]` — как в загрузчике методики 1С и примере Microsoft [ИТС-мет 6006 — конспект, 2.4.6; MS Learn]. `client_pid` — процесс клиента, т. е. `rphost` ⚠ (для 1С не проверялось).

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| `sqlservr.exe` «съел всю память», «сервер тормозит» | SQL Server держит память под буферный пул; Диспетчер задач не показывает картину СУБД | ожидания (D-02/D-03), PLE и гранты (D-23/D-24); `max server memory` — `02-…` [ИТС-мет 6008; MS Learn] |
| В топе ожиданий `SLEEP_TASK`, `LAZYWRITER_SLEEP`, `XE_TIMER_EVENT` | фоновые «безопасные» ожидания | исключить (D-02, 3.3) [ИТС-мет 6008] |
| Утром «топ запросов» пуст | ночной `DBCC FREEPROCCACHE` по регламенту 1С | топ за день или Query Store (D-29) [ИТС-мет 5837; MS Learn] |
| Жертвы блокировки есть, блокировщика среди активных запросов нет | головной сеанс 1С спит с открытой транзакцией | D-06/D-07 от `sys.dm_exec_sessions` + `sys.dm_exec_input_buffer` [MS Learn] |
| «Удалить соединение» в консоли 1С не срабатывает | у логина СУБД нет прав или вызов стоит не в СУБД (COM/HTTP) | права логина; иначе `KILL` после сохранения сведений [ИТС-КС разд. 5.2.12.3] |
| `LCK_M_RS_*`, частые взаимоблокировки на одной таблице | автоматический режим (Serializable), «ДЛЯ ИЗМЕНЕНИЯ» со сканированием | управляемый режим, оптимизация запроса [ИТС-разр гл. 9; ИТС-мет 4051 — конспект, 1.6] |
| «…thread communication buffer…», «Intra-query parallelism…» | взаимоблокировка потоков параллельного плана | `MAXDOP = 1` [ИТС-мет 5834] |
| Рост `CXPACKET` после реструктуризации | `MAXDOP = 0` не вернули | вернуть `1` [ИТС-мет 5945] |
| `WRITELOG` в топе, `avg_ms` 20–50 | журнал на медленном или общем томе | отдельный быстрый том `.ldf` (1–5 мс) [ИТС-мет 6008; 5904] |
| Периодические «замирания» всех пользователей | рост журнала мелким шагом (`PREEMPTIVE_OS_WRITEFILEGATHER`, `Log Growths`) | размер журнала заранее, IFI для данных [ИТС-мет 6008; MS Learn] |
| `RESOURCE_SEMAPHORE`, ошибка 8645 у отчётов | запросы ждут гранты памяти | D-19/D-20, память, оптимизация отчёта [MS Learn] |
| `PAGELATCH_UP` на `2:1:1`/`2:1:3` | мало или неравные файлы tempdb | 4–8 равных файлов [MS Learn; ИТС-мет 5904] |
| tempdb растёт до конца диска | долгая транзакция держит хранилище версий или временные объекты | D-11, D-26, D-06 [ИТС-мет 2374; MS Learn] |
| Высокий `ASYNC_NETWORK_IO`, сеть свободна | `rphost` медленно выбирает результат | разбирать сервер 1С и код, не СУБД [ИТС-мет 6008; MS Learn] |
| `blocked process threshold = 1` — отчётов нет | монитор проверяет раз в 5 с; минимум — 5 | порог ≥ 5 (для 1С ≈ 10) [MS Learn] |
| Сеанс XE заполнил диск | `max_rollover_files` по умолчанию `UNLIMITED`, нет фильтра | задать размеры и фильтры [MS Learn] |
| «Узкий» техжурнал из методики не появляется | кириллическая «С» в пути, испорчен `xmlns` | набрать вручную (12.2) [`../1c-windows/02-…`, 11.5] |
| После `<plansql/>` СУБД замедлилась | планы собираются для всех запросов всех баз | выключить; планы — из кеша/Query Store/копии [ИТС-адм прил. 3, разд. 3.24.2.10.1] |
| Query Store «перестал собирать» | ушёл в `READ_ONLY` по размеру (`readonly_reason = 65536`) | `MAX_STORAGE_SIZE_MB`, `QUERY_CAPTURE_MODE = AUTO`, `READ_WRITE` [MS Learn] |
| Принудительный план «не работает» | изменилась схема; другой `#tt` — другой запрос | D-33, снять принуждение, лечить причину [MS Learn] |
| `sys.dm_db_index_usage_stats` пуста | флаг 2330 или недавний перезапуск | `DBCC TRACESTATUS(-1)`, аптайм D-01 [ИТС-мет 5946; MS Learn] |

## Быстрая шпаргалка

| Задача | Команда / запрос |
|---|---|
| Аптайм, версия, флаги | D-01; `DBCC TRACESTATUS(-1);` |
| Чего ждёт сервер (с начала / за минуту) | D-02 / D-03 |
| Что выполняется / кто кого блокирует | D-05 / D-07; SSMS → Standard Reports → Activity – All Blocking Transactions |
| Последний оператор сеанса | `SELECT event_info FROM sys.dm_exec_input_buffer(<spid>, NULL);` |
| Долгие транзакции | D-06, D-10; `DBCC OPENTRAN ('buh');` |
| Отчёты о блокировках | `EXEC sp_configure 'blocked process threshold', 10; RECONFIGURE;` + сеанс 7.3, D-13 |
| Взаимоблокировки за неделю | D-12 |
| Топ по CPU / чтениям / частоте / базам | D-14 / D-15 / D-18 / D-17; «размазанная» — D-16 |
| Диски, ошибки 833 | D-21; `EXEC sp_readerrorlog 0, 1, N'taking longer than';` |
| Память, tempdb, CPU | D-23, D-20; D-26, D-11; D-27 |
| Счётчики без Perfmon | D-24, D-25 |
| Сеанс XE: старт/стоп/список | `ALTER EVENT SESSION [1c_long_queries] ON SERVER STATE = START;` / `= STOP;` / `SELECT name FROM sys.dm_xe_sessions;` |
| Query Store: включить / состояние / топ / регрессии | 8.2 / D-28 / D-29 / D-30 |
| Принудить / снять план | `EXEC sp_query_store_force_plan @query_id = N, @plan_id = M;` / `sp_query_store_unforce_plan` |
| Аварийный вход | `sqlcmd -S sql01 -A`; `EXEC sp_configure 'remote admin connections', 1; RECONFIGURE;` |
| Снять сеанс | консоль 1С → `KILL <spid>;` → `KILL <spid> WITH STATUSONLY;` |
| Сбор счётчиков | `logman create counter … -f bincirc -si 15 …`, `logman start SQL_1C` (11.3) |
| Техжурнал: долгие запросы / блокировки | 12.2 А / Г (`<dbmslocks/>`) |
| Таблица → объект 1С; `KEY: 5:7205…` | `ПолучитьСтруктуруХраненияБазыДанных()`; D-09 |

## Источники

**ИТС 8.3.27** (полные тексты, выгрузка 19.10.2026; `https://its.1c.ru/db/v8327doc/content/NNN/hdoc`): «Руководство администратора» — прил. 3, разд. 3.24 (115), гл. 6, разд. 6.6.3 (105); «Клиент-серверный вариант» — гл. 1, разд. 1.5.4 (123), гл. 2, разд. 2.3 (124: рабочий процесс на Linux не работает с MS SQL), гл. 5, разд. 5.2.11–5.2.12 (127); «Руководство администратора» — гл. 7, разд. 7.2 (106: автономный сервер на Linux и MS SQL); «Руководство разработчика» — гл. 9 (54), прил. 8 (92); отличия 8.5.1 — `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`.

**Методические статьи ИТС** (`https://its.1c.ru/db/metod8dev/content/NNNN/hdoc`): 6008 (09.11.2023), 5861 (11.09.2015), 5910 (28.07.2016), 5813 (18.02.2015), 5906 (13.05.2016), 5834 (18.02.2015), 5945 (15.05.2018), 5946 (29.10.2019), 5904 (15.07.2019), 5837 (18.11.2022), 5838 (03.03.2021), 5899 (12.05.2016), 2923 (28.10.2008), 2374 (11.04.2008), 2926 (30.10.2008), 1738 (18.09.2007); 6006 (16.11.2022) и 4051 (22.05.2025) — по конспекту `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`; 5809, 6011 — по `../1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md`.

**Microsoft Learn** (`https://raw.githubusercontent.com/MicrosoftDocs/sql-docs/live/docs/<путь>.md` = `https://learn.microsoft.com/en-us/sql/<путь>`, прочитаны 20.10.2026):

- DMV/DMF — страницы каталога `relational-databases/system-dynamic-management-objects/` для каждого представления, названного в тексте (`sys-dm-os-wait-stats-transact-sql`, `sys-dm-exec-requests-transact-sql`, `sys-dm-tran-locks-transact-sql`, `sys-dm-exec-query-stats-transact-sql`, `sys-dm-io-virtual-file-stats-transact-sql` и т. д.; имя файла = имя представления через дефисы + `-transact-sql`)
- Query Store: `relational-databases/performance/monitoring-performance-by-using-the-query-store`, `best-practice-with-the-query-store`, `query-store-hints`; `relational-databases/system-catalog-views/sys-query-store-*`, `sys-database-query-store-options-…`; `…/system-stored-procedures/sp-query-store-force-plan-…`, `sys-sp-query-store-set-hints-…`; `t-sql/statements/alter-database-transact-sql-set-options`; `relational-databases/automatic-tuning/automatic-tuning`
- Блокировки: `relational-databases/sql-server-deadlocks-guide`, `sql-server-transaction-locking-and-row-versioning-guide`, `performance/optimized-locking`; `database-engine/configure-windows/blocked-process-threshold-server-configuration-option`; `relational-databases/event-classes/blocked-process-report-event-class`
- Extended Events: `relational-databases/extended-events/use-the-system-health-session`, `quick-start-extended-events-in-sql-server`, `targets-for-extended-events-in-sql-server`; `t-sql/statements/create-event-session-transact-sql`; `relational-databases/system-functions/sys-fn-xe-file-target-read-file-transact-sql`; `relational-databases/sql-trace/sql-trace`; `relational-databases/performance/query-profiling-infrastructure`
- Счётчики: `relational-databases/performance-monitor/sql-server-*-object` (Buffer Manager, Memory Manager, General Statistics, SQL Statistics, Locks, Access Methods, Databases, Transactions, Wait Statistics, Latches), `use-sql-server-objects`, `activity-monitor`; `relational-databases/performance/performance-dashboard`
- Прочее: `database-engine/configure-windows/diagnostic-connection-for-database-administrators`; `t-sql/language-elements/kill-transact-sql`; `relational-databases/system-stored-procedures/sp-who-…`, `sp-readerrorlog-…`, `sp-server-diagnostics-…`; `t-sql/database-console-commands/dbcc-*` (`sqlperf`, `inputbuffer`, `opentran`, `traceon-trace-flags`); `relational-databases/databases/tempdb-database`, `database-instant-file-initialization`; `relational-databases/security/authentication-access/server-level-roles`; `sql-server/editions-and-components-of-sql-server-2022`; `linux/sql-server-linux-troubleshooting-guide`
- Статьи поддержки `https://raw.githubusercontent.com/MicrosoftDocs/SupportArticles-docs/main/support/sql/database-engine/performance/`: `understand-resolve-blocking`, `troubleshoot-high-cpu-usage-issues`, `troubleshoot-memory-grant-issues`, `troubleshoot-sql-io-performance`, `recommendations-reduce-allocation-contention`

- Дополнительно при независимой сверке 20.10.2026: `database-engine/configure-windows/server-configuration-options-sql-server` (умолчания `sp_configure`), `remote-admin-connections-server-configuration-option`; `relational-databases/security/metadata-visibility-configuration`; `relational-databases/extended-events/selects-and-joins-from-system-views-for-extended-events-in-sql-server`, `convert-an-existing-sql-trace-script-to-an-extended-events-session`; `t-sql/statements/set-lock-timeout-transact-sql`; `relational-databases/errors-events/mssqlserver-1205-…`, `-1222-…`, `-833-…`, `-8645-…`; `sql-server/editions-and-components-of-sql-server-2017`, `-2019`; справка `logman create counter` — `https://raw.githubusercontent.com/MicrosoftDocs/windowsserverdocs/main/WindowsServerDocs/administration/windows-commands/logman-create-counter.md`; перечни страниц каталогов `t-sql/database-console-commands/` и `relational-databases/system-stored-procedures/` (через API GitHub) — для проверки недокументированности.

**Сторонние**: `sp_WhoIsActive` — https://github.com/amachanic/sp_whoisactive (README и `sp_WhoIsActive.sql` v2200.20260409); First Responder Kit — https://github.com/BrentOzarULTD/SQL-Server-First-Responder-Kit (README); прочитаны 20.10.2026.

**База знаний** (согласованность): `../1c-windows/02-ms-sql-server-dlya-1c.md`, `../1c/07-…`, `../1c/03-…`, `../its-metod/vzaimoblokirovki-…`, `../its-metod/sbor-dannyh-…`, `../its-metod/monitoring-i-audit.md`, `../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`, `../postgresql/06-monitoring-i-diagnostika-zaprosov.md`.

## Что не удалось подтвердить

- `program_name`/`client_interface_name` соединений 1С; передача «Времени ожидания блокировки данных» в `LOCK_TIMEOUT` и умолчание 20 с; использование платформой серверных курсоров; включает ли платформа RCSI сама.
- Совпадает ли `query_hash` у запросов 1С с разными `#tt<N>`; поведение таких запросов в Query Store и при принуждении плана; накладные расходы Query Store и `LAST_QUERY_PLAN_STATS` на нагруженных базах 1С.
- Единица `duration` у `rpc_completed`, `sql_batch_completed`, `blocked_process_report` в XE (мкс — по примеру `sql_statement_completed` и колонке `Duration` класса трассировки Blocked Process Report); поля `logical_reads`, `severity`; источник предиката `sqlserver.database_name`; связь `client_pid` с `rphost`; ошибка единиц в загрузчике XE методики 1С.
- Структура XML `blocked_process_report` (`blocked-process`/`blocking-process`/`process`).
- Влияет ли флаг 2330 на `sys.dm_db_missing_index_*`.
- Единица `Avg. Disk sec/Read` (секунды) — по названию; страница Microsoft её не называет.
- Пороги «доля сигнальных ожиданий 20–25 %» и «PLE 300 с» — практика сообщества.
- Обнаружение обрыва соединения через 2 часа [ИТС-мет 2374, 2008] на современных версиях; отсутствие `PAGE`-блокировок для баз 8.3.22+.
- Каталог `system_health` на Linux.
- Всё о SQL Server 2025 (оптимизированная блокировка, `MAX_DURATION`) — вне поддержки 1С, не проверялось.

Закрыто при независимой сверке 20.10.2026 (MS Learn): разрешение `ALTER ANY EVENT SESSION` (с 2022 ещё `CREATE ANY EVENT SESSION`); действие `sqlserver.client_hostname`; умолчание `blocked process threshold` = 0; префикс `MSSQL$<имя>:`; ключи `logman` `-max`, `-o`; названия отчётов Query Store; написание диапазонных режимов в `sys.dm_tran_locks`; отсутствие в справочнике Microsoft флага 2330, `sp_MSForEachDB`, `sp_who2`, `DBCC PAGE`; допустимость сортировки `[blocked_session_count]` в `sp_WhoIsActive`.
