# Резервное копирование и восстановление баз 1С в SQL Server: модели восстановления, полные, разностные и журнальные копии, цепочка журнала, восстановление на момент времени, проверка и автоматизация

> **Официальные тексты по теме** (конспекты ИТС 8.3.27 в этой базе): `../its-docs/adm-gl06-administrirovanie-ib-p3.md` (разд. 6.7–6.10, 6.13 «Руководства администратора»: `.dt`, резервное копирование ИБ, журнал регистрации), `../its-docs/cs-gl05-administrirovanie-klastera-p1.md` (разд. 5.1.1 «Операции резервного копирования в клиент-серверном варианте»), `../its-docs/cs-gl05-administrirovanie-klastera-p3.md` (разд. 5.4 «Хранилище двоичных данных», 5.5 «Администрирование СУБД»), `../its-docs/cs-gl02-klient-servernyj-variant-p1.md` (разд. 2.2.3.2 — где кластер хранит журнал регистрации), `../its-docs/adm-gl05-spisok-infobaz.md` (разд. 5.2.1.3 — параметры ИБ на MS SQL), `../its-docs/adm-gl07-avtonomnyj-server.md` (разд. 7.2, 7.3.7, 7.4.6–7.4.7 — `ibcmd infobase dump/restore`), `../its-docs/dev-gl02-rabota-s-konfiguraciej.md` (разд. 2.14.2.1 — модель восстановления при реструктуризации). Методические статьи ИТС о копиях на MS SQL — 2922, 2378, 2373 (2008) и 5904 (2019); их актуальность — в разделе 16.4.

> Статус: проверено независимой сверкой 20.10.2026: с исходниками документации Microsoft (`MicrosoftDocs/sql-docs`: BACKUP/RESTORE и их аргументы, ALTER DATABASE, DBCC, модели восстановления, журнал и ошибка 9002, IFI, сжатие и шифрование копий, URL/S3, VSS Writer, страницы ошибок, DMV и таблицы `msdb`, процедуры агента, `sqlcmd`, редакции, известные проблемы 2025; Backup-SqlDatabase; `wbadmin`; срок поддержки 2016), с полными текстами ИТС 8.3.27 (адм. гл. 5–7, прил. 3–4; КС гл. 1, 2, 5; разр. гл. 2 и 26; метод. 2922, 2378, 2373, 2926, 4055, 5837, 5899, 5904, 5908, 6008) и с репозиториями Ola Hallengren и dbatools; исправлено 7 ошибок (пропущенные звенья журнала в примерах 9.2, 11 и 17.2, `database_backup_lsn`, шифрование копий, умолчание `sqlcmd -N`, `estimated_completion_time`), закрыто 14 пометок; на сервере не проверялось.

> Область: резервное копирование и восстановление баз «1С:Предприятия 8» в Microsoft SQL Server — модели восстановления, виды и параметры копий, сетевые папки и URL, цепочка журнала, рост журнала и ошибка 9002, восстановление (полное, на момент времени, с хвостом журнала, под другим именем и на другом сервере, страничное), проверка копий, история в `msdb`, автоматизация (агент, планы обслуживания, Ola Hallengren, PowerShell), VSS и `wbadmin`, что ещё копировать для 1С, типовые сценарии. | Версии: SQL Server 2016–2025 (поддержка 2016 закончилась 14.07.2026 [MS Learn, lifecycle]); платформа 8.3.27 (и 8.5.1) поддерживает MS SQL до 2022 включительно, 2025 в перечне нет [ИТС-КС разд. 1.5.4; `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`]. | Актуальность: 2026-10-20

Пометки: **[MS Learn]** — документация Microsoft (learn.microsoft.com, исходники `MicrosoftDocs/sql-docs`); **[ИТС-КС разд. N]** — «Клиент-серверный вариант. Руководство администратора» 8.3.27; **[ИТС-адм разд. N]** — «Руководство администратора» 8.3.27; **[ИТС-разр гл. N]** — «Руководство разработчика» 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС с датой; **[сторонний]** — сторонний инструмент по его сайту или репозиторию; **[практика]** — опыт сообщества и выводы автора; **⚠** — не подтверждено первоисточником, проверяйте на стенде.

Смежные статьи (их тему здесь не расписываю): `mssql/01-versii-redakcii-arhitektura.md` (версии, редакции, что поддерживает 1С), `mssql/02-ustanovka-i-nastrojka-ekzemplyara.md` (установка, учётные записи служб, каталоги, мгновенная инициализация файлов), `mssql/03-administrirovanie-instrumenty-prava.md` (SSMS, `sqlcmd`, логины, агент, Database Mail), `mssql/05-obsluzhivanie-indeksy-statistika.md` (регламент, `DBCC CHECKDB` по расписанию), `mssql/06-monitoring-i-diagnostika.md` (DMV, журнал ошибок, оповещения), `mssql/07-otkazoustojchivost-i-obnovlenie-versij.md` (группы доступности, доставка журналов, обновление версий), `mssql/08-tipovye-problemy-i-zaprosy-1c.md` (повреждения, типовые ошибки 1С); `../1c-windows/02-ms-sql-server-dlya-1c.md` (обзор MS SQL для 1С — здесь подробнее его разделы 8–9), `../1c-windows/06-windows-server-dlya-administratora-1c.md` (`wbadmin` для ОС), `../1c/03-administrirovanie-klastera-ras-rac.md` (`rac`).

**Обозначения.** Экземпляр по умолчанию на сервере `SQL01` (служба `MSSQLSERVER`), домен `CORP`, база 1С `buh` с логическими именами файлов `buh` и `buh_log` (**у вас могут быть другие** — смотрите `RESTORE FILELISTONLY` или `sys.database_files`), логин кластера 1С `buh_1c`. Диски: `D:` — данные, `L:` — журналы, `E:\Backup\buh\` — локальные копии, `\\backup01\sql$\SQL01\` — сетевая папка. T-SQL выполняется от имени **sysadmin**, если не сказано иначе; PowerShell — «от имени администратора». Время — время сервера SQL Server. Имена файлов с датой собираются функциями `FORMAT(SYSDATETIME(), N'yyyyMMdd_HHmmss')` (SQL Server 2012+) [практика]; запросы с `LAG … OVER` — тоже 2012+ [практика].

**Смешанная среда.** Рабочие процессы кластера 1С на Linux с MS SQL работать не могут [ИТС-КС разд. 2.3]; автономный сервер и `ibcmd` на Linux тоже [ИТС-адм разд. 7.2]. MS SQL для баз 1С — только при рабочих серверах 1С на Windows x86-64 [ИТС-КС разд. 1.5.4]; сам SQL Server может стоять на Linux (5.4). Базы сервисов (Redmine, NetBox, GlitchTip) в экземпляр СУБД 1С не кладите.

## Кратко — главные факты

1. **Копию клиент-серверной ИБ делают средствами СУБД**, не выгрузкой `.dt`: выгрузка может не загрузиться при ошибках в базе, долгая, требует монопольного доступа и много памяти [ИТС-адм разд. 6.7; ИТС-КС разд. 5.1.1]. SQL Server копирует базу без остановки работы [ИТС-мет 2922, 2008; MS Learn].
2. **Копия ИБ = база данных + журнал регистрации + хранилище двоичных данных** (КОРП). Журнал регистрации не хранится в базе (`<каталог данных сервера>\reg_<порт>\<uuid ИБ>\1Cv8Log`); его и хранилище средствами СУБД не скопировать [ИТС-адм разд. 6.9.2, 6.13.1; ИТС-КС разд. 2.2.3.2, 5.1.1].
3. **Модели**: `SIMPLE` — без копий журнала и без восстановления на момент; `FULL` — с ними; `BULK_LOGGED` — копии журнала нужны, но внутри копии с массовыми операциями момент не выбрать. Standard/Enterprise по умолчанию `FULL`, Express — `SIMPLE`; новая база берёт модель из `model` [MS Learn].
4. **Рабочие базы 1С — `FULL`, копия журнала каждые 15–30 минут** (интервал Microsoft [MS Learn]), полная ежедневно, разностные между ними; тестовые — `SIMPLE` [практика]. 1С: модель — «в зависимости от политики резервного копирования» [ИТС-мет 5904, 2019].
5. **После `SIMPLE` → `FULL` до первой полной (или разностной) копии цепочки нет**; признак — `sys.database_recovery_status.last_log_backup_lsn IS NULL` [MS Learn].
6. **Цепочку журнала рвут** переход в `SIMPLE`, потеря файла копии журнала, копия журнала «чужой» программой. **Не рвут** полные и разностные копии (копия журнала после полной покрывает и её время) [MS Learn].
7. **Базу разностных копий сдвигает** любая полная копия без `COPY_ONLY`, в том числе VSS-копия программы копирования ВМ [MS Learn]. Внеплановые копии — только `WITH COPY_ONLY`.
8. **`WITH CHECKSUM`** — по умолчанию выключено (кроме сжатых копий); для всех копий — `backup checksum default` = 1 [MS Learn].
9. **`WITH COMPRESSION`** — Enterprise и Standard (не Express/Web); восстановить сжатую копию может любая редакция; `ALGORITHM`/`LEVEL` — с 2022, `ZSTD` — с 2025 [MS Learn].
10. **По умолчанию `BACKUP` дописывает в существующий файл (`NOINIT`), а `RESTORE` берёт `FILE = 1`** — так восстанавливают «не ту» копию. Один файл — одна копия с датой в имени, `.bak`/`.trn` [MS Learn].
11. **Сетевая папка**: UNC прямо в `TO DISK`; права нужны **учётной записи службы SQL Server**; виртуальная учётная запись выходит в сеть как `CORP\SQL01$`; подключённые буквы дисков службе не видны [MS Learn]. `sp_addumpdevice` из ИТС-мет 2378 (2008) не нужен.
12. **`RESTORE VERIFYONLY` не проверяет структуру данных**; настоящая проверка — восстановление и `DBCC CHECKDB` [MS Learn; ИТС-мет 5904, 2019; ИТС-мет 5899, 2016].
13. **Журнал растёт** — смотрите `log_reuse_wait_desc`: `LOG_BACKUP` (нет копий журнала), `ACTIVE_TRANSACTION` (длинная транзакция — зависший сеанс 1С, обмен), `REPLICATION` (в том числе CDC механизма копий базы данных 1С «Версия2») [MS Learn; ИТС-разр гл. 26].
14. **`BACKUP LOG … WITH TRUNCATE_ONLY` из ИТС-мет 2373 (2008) не работает** — удалён; нужна копия журнала, затем при необходимости `DBCC SHRINKFILE` [MS Learn]. Журнал, ни разу не копировавшийся, освобождается после **двух** копий журнала [MS Learn].
15. **Восстановление: все шаги `NORECOVERY`, затем `RESTORE DATABASE … WITH RECOVERY`**; поспешный `RECOVERY` — начинать заново с полной копии [MS Learn].
16. **Перед восстановлением поверх базы в `FULL`** — копия хвоста журнала (`BACKUP LOG … WITH NORECOVERY`), иначе ошибка 3159; `REPLACE` выбрасывает несохранённый хвост [MS Learn].
17. **Во время восстановления к ИБ не должно быть подключений** [ИТС-КС разд. 5.1.1]; монопольный режим 1С **не** переводит базу в `SINGLE_USER` [ИТС-адм разд. 6.7]. `SINGLE_USER` не удастся при `AUTO_UPDATE_STATISTICS_ASYNC = ON` (1С его рекомендует) [MS Learn; ИТС-мет 5904, 2019].
18. **Права**: `BACKUP` — `sysadmin`, `db_owner`, `db_backupoperator`; `RESTORE` — `sysadmin`, `dbcreator`, владелец базы, а `db_owner` — **нет**; `dbcreator` восстанавливает и удаляет **любую** базу [MS Learn].
19. **Копию новой версии SQL Server на старой не восстановить** (3169) — копию с 2025 на 2022 не вернуть [MS Learn].
20. **На другом сервере** владелец базы — тот, кто восстанавливал; пользователи без логина с тем же SID «осиротевают» (`ALTER USER … WITH LOGIN`, `CREATE LOGIN … WITH SID`) [MS Learn].
21. **Копию рабочей базы регистрируют в кластере с блокировкой регламентных заданий**, с тем же смещением дат и только на отдельную базу данных [ИТС-адм разд. 5.2.1.3.6, 5.2.1.3.8; ИТС-мет 4055, 2010].
22. **VSS**: SQL Writer не делает копий журнала; `wbadmin start backup` с параметрами по умолчанию делает копию типа copy (`-vssCopy`), `-vssFull` вмешивается в историю других программ [MS Learn]; файлы `.mdf`/`.ldf` исключить из файлового копирования [ИТС-мет 5904, 2019].
23. **Автоматизация**: в Express нет агента — планировщик Windows и `sqlcmd -b`; ODBC-`sqlcmd` из SQL Server 2025 по умолчанию требует шифрования (`-N m`), с самоподписанным сертификатом — `-C` [MS Learn]. Ola Hallengren `DatabaseBackup` — бесплатно, SQL Server 2017–2025 [сторонний].
24. **Чужие `.bak` опасны**: вредоносная копия может захватить экземпляр и хост ещё до проверок — восстанавливайте только копии из доверенного контура [MS Learn].

## 1. Что и зачем копировать для базы 1С

### 1.1. Позиция 1С

- **Копию делают перед любой операцией, которая может повредить данные** [ИТС-КС разд. 5.1.1; ИТС-адм разд. 6.9.2].
- **Клиент-серверный вариант — средствами СУБД**: это точная копия с возвратом ровно в то состояние; выгрузка `.dt` предполагает корректные данные — при нарушениях выгрузка может пройти, а загрузка — нет [ИТС-КС разд. 5.1.1]. `.dt` как копию не рекомендуют: незагружаемость, длительность, монопольный доступ, память [ИТС-адм разд. 6.7]. То же для `ibcmd infobase dump` — не средство копирования, подключений быть не должно [ИТС-адм разд. 7.3.7].
- **Копия снимается на работающей базе**, однопользовательский режим 1С не нужен [ИТС-мет 2922, 2008]. Microsoft: во время `BACKUP` разрешены `INSERT`/`UPDATE`/`DELETE`; нельзя одновременно добавлять/удалять файлы базы и сжимать файлы — вторая операция ждёт и по тайм-ауту падает [MS Learn].
- **Копия СУБД сохраняет всё**, даже при нарушениях в базе — после восстановления базу можно исправлять [ИТС-мет 2922, 2008].
- **Первую автоматическую копию восстановить на резервном сервере и проверить** [ИТС-мет 5904, 2019]; «хотя бы один раз проведено тестовое восстановление … с замером времени» [ИТС-мет 5899, 2016].

### 1.2. Состав копии ИБ

Порядок копирования и восстановления [ИТС-адм разд. 6.9.2]: (1) база данных — средствами СУБД; (2) журнал регистрации — если нужна история после восстановления; (3) хранилище двоичных данных — встроенным языком или стандартной функцией. **Журнал регистрации восстанавливают при остановленном кластере** [ИТС-адм разд. 6.9.2]. Подробнее — раздел 16.

Что ещё копировать [практика, если не указано]:

| Объект | Где / чем | Источник |
|---|---|---|
| `master` (регулярно и после изменений; копии журнала `master` не поддерживаются), `msdb` (задания, история — после изменений), `model` (после настройки); `tempdb` не копируется | `BACKUP DATABASE` | [MS Learn] |
| Логины (SID, хеши паролей), задания, операторы, связанные серверы, `CREDENTIAL` | копии `master`/`msdb` + скрипты (10.3) | [MS Learn] |
| Сертификаты и ключи TDE и шифрования копий | `BACKUP CERTIFICATE … WITH PRIVATE KEY` (4.6) | [MS Learn] |
| Реестр кластера `1CV8Clst.lst` | `<каталог данных сервера>\reg_<порт>\` (по умолчанию `C:\Program Files\1cv8\srvinfo\reg_1541\`) | [ИТС-адм прил. 3, разд. 3.7] |
| Журналы регистрации, хранилище двоичных данных | `…\reg_<порт>\<uuid ИБ>\1Cv8Log`, `…\reg_<порт>\BinDataStrg\<uuid ИБ>` (если каталоги не переназначены) | [ИТС-КС разд. 2.2.3.2] |
| `conf.cfg`, `logcfg.xml`, публикации (`default.vrd`), программные лицензии | файлово; пути — `../1c-windows/01-…`, `03-…`, `05-…` | — |

**Не копировать**: сеансовые данные кластера (`…\reg_<порт>\snccntx…`) [ИТС-мет 5908, 2022, разд. 10.1]; файлы `.mdf`/`.ldf` работающего SQL Server файловыми системами копирования [ИТС-мет 5904, 2019] (без VSS копия несогласована, с VSS — раздел 15).

### 1.3. RPO, RTO и схема

RPO (допустимая потеря) задаёт частоту копий журнала, RTO (время возврата) — частоту полных/разностных и скорость восстановления [MS Learn]. Microsoft: копия журнала каждые 15–30 минут «может быть достаточной»; регулярные полные и разностные ограничивают число применяемых копий журнала [MS Learn]. Время восстановления = запись файлов данных (быстрее с мгновенной инициализацией) + **обнуление файла журнала** + разностная и журналы + откат (8.6) — измерьте его [ИТС-мет 5899, 2016].

Ориентиры [практика]:

| База | Модель | Полная | Разностная | Журнал |
|---|---|---|---|---|
| Рабочая до ~200 ГБ | `FULL` | ежедневно ночью | — или днём | каждые 15 мин |
| Рабочая крупная | `FULL` | раз в неделю | ежедневно | каждые 5–15 мин |
| Тестовая, песочница | `SIMPLE` | по требованию | — | — |

Хранить: 14–35 дней на основном хранилище + копия вне площадки [практика].

## 2. Модели восстановления и выбор для 1С

### 2.1. Три модели

| | `SIMPLE` | `FULL` | `BULK_LOGGED` |
|---|---|---|---|
| Копии журнала | нет | обязательны | обязательны |
| Усечение журнала | после контрольной точки | после копии журнала (не `COPY_ONLY`), если была контрольная точка | как `FULL` |
| Потери | всё после последней копии данных | обычно ничего | как `FULL`; при массовых операциях после последней копии журнала — всё после неё |
| На момент времени | нет | да | только на конец копии; внутри копии с массовыми изменениями — нет |
| Доставка журналов, группы доступности | нет | да | — |

Источник таблицы — [MS Learn]. В `BULK_LOGGED` (и в `SIMPLE`, если не идёт копирование) минимально протоколируются массовая загрузка (`bcp`, `BULK INSERT`, `INSERT … SELECT` при условиях), `SELECT INTO`, `CREATE INDEX`, `ALTER INDEX REBUILD`/`DBCC DBREINDEX`, `.WRITE`; копии журнала в `BULK_LOGGED` бывают большими; хвост журнала повреждённой базы с массовыми изменениями не скопировать [MS Learn].

### 2.2. Умолчания и проверка

Standard/Enterprise — `FULL`, Express — `SIMPLE`, новая база — из `model` [MS Learn]; 1С задаёт модель в `model` по политике копий [ИТС-мет 5904, 2019]. Смена модели требует права `ALTER` и сбрасывает кеш планов базы [MS Learn].

```sql
SELECT d.name, d.recovery_model_desc, d.log_reuse_wait_desc, d.is_auto_update_stats_async_on,
       drs.last_log_backup_lsn          -- NULL: копия журнала невозможна (SIMPLE или нет полной копии) [MS Learn]
FROM sys.databases AS d
JOIN sys.database_recovery_status AS drs ON drs.database_id = d.database_id
WHERE d.database_id > 4 ORDER BY d.name;
```

### 2.3. Что выбрать

- **Рабочие базы — `FULL`** с копиями журнала: только так можно вернуть базу 1С на момент перед ошибкой («до перепроведения в 14:05») [практика].
- **`SIMPLE`** — тестовые и учебные копии [практика]; в нём нет доставки журналов, групп доступности, восстановления на момент [MS Learn].
- **`BULK_LOGGED` — совет 1С на время загрузки `.dt` и реструктуризации** («Простая» или «С неполным протоколированием», на время операции или постоянно, если момент времени не нужен; **перед сменой — резервная копия**) [ИТС-адм разд. 6.8; ИТС-разр гл. 2, разд. 2.14.2.1]. Microsoft: безопасно, если пользователей нет и всё сделанное можно повторить [MS Learn]. Какие операции реструктуризации 1С протоколируются минимально — не описано ⚠.
- Журнал растёт не из-за модели, а без копий журнала или из-за длинных транзакций (раздел 7); `SIMPLE` «ради места» лишает восстановления на момент [практика].

### 2.4. Переключение модели

```sql
BACKUP LOG [buh] TO DISK = N'E:\Backup\buh\buh_LOG_before_switch.trn' WITH CHECKSUM, COMPRESSION, INIT;  -- перед уходом из FULL [MS Learn]
ALTER DATABASE [buh] SET RECOVERY BULK_LOGGED;     -- на загрузку .dt / реструктуризацию [ИТС-адм разд. 6.8]
-- … операция в 1С …
ALTER DATABASE [buh] SET RECOVERY FULL;
BACKUP LOG [buh] TO DISK = N'E:\Backup\buh\buh_LOG_after_bulk.trn' WITH CHECKSUM, COMPRESSION, INIT;    -- сразу после возврата [MS Learn]
```

| Переход | Сразу сделать [MS Learn] |
|---|---|
| `FULL` ↔ `BULK_LOGGED` | после массовых операций вернуть `FULL`, копия журнала |
| `SIMPLE` → `FULL`/`BULK_LOGGED` | полная или разностная копия — только после неё начинается цепочка; включить задания копий журнала |
| → `SIMPLE` | отключить задания копий журнала; полные копии оставить |

Проверка: `last_log_backup_lsn` не `NULL`; первая копия журнала новой цепочки — `msdb.dbo.backupset.begins_log_chain = 1` [MS Learn]. Типичная ловушка [практика]: «перевели в `FULL`, а копии журнала падают с 4214 (BACKUP LOG cannot be performed because there is no current database backup)» — не сделана полная копия (текст 4214 — [MS Learn]).

## 3. Виды резервных копий

### 3.1. Полная

- Копирует всю базу и часть журнала, нужную для согласованности; восстановленная база соответствует моменту **окончания** копии; неиспользуемое место не копируется (оценка — `sp_spaceused`); для `master` возможна только полная [MS Learn].
- Пока идёт копия данных, журнал не усекается (`ACTIVE_BACKUP_OR_RESTORE`) — закладывайте место в журнале на время полной копии [MS Learn].
- Нельзя для баз в `RESTORING` и `STANDBY`; `BACKUP` нельзя внутри транзакции [MS Learn].

```sql
-- sysadmin / db_owner / db_backupoperator
DECLARE @f nvarchar(400) = N'E:\Backup\buh\buh_FULL_' + FORMAT(SYSDATETIME(), N'yyyyMMdd_HHmmss') + N'.bak';
BACKUP DATABASE [buh] TO DISK = @f WITH CHECKSUM, COMPRESSION, INIT, STATS = 10, DESCRIPTION = N'1C buh: плановая полная';
-- Проверка: «BACKUP DATABASE successfully processed …», строка в msdb.dbo.backupset (раздел 13)
```

### 3.2. Разностная

- Содержит экстенты, изменённые с **базы разностных копий** — последней полной без `COPY_ONLY` (битовая карта изменённых экстентов); растёт со временем, поэтому полную периодически делают заново; при восстановлении нужна база и **только последняя** разностная; `DIFFERENTIAL` + `COPY_ONLY` → `COPY_ONLY` игнорируется [MS Learn].
- Текущая база разностных — `sys.master_files.differential_base_time`/`differential_base_lsn` [MS Learn]: удобно проверить, не сдвинул ли её «чужой» бэкап (раздел 15).

```sql
DECLARE @f nvarchar(400) = N'E:\Backup\buh\buh_DIFF_' + FORMAT(SYSDATETIME(), N'yyyyMMdd_HHmmss') + N'.bak';
BACKUP DATABASE [buh] TO DISK = @f WITH DIFFERENTIAL, CHECKSUM, COMPRESSION, INIT, STATS = 10;
SELECT name, differential_base_time FROM sys.master_files WHERE database_id = DB_ID(N'buh');
```

### 3.3. Копия журнала

- Только в `FULL`/`BULK_LOGGED` и после полной копии (иначе 4214); копирует журнал от предыдущей копии журнала до текущего конца; после неё неактивные VLF освобождаются (кроме `COPY_ONLY`, `NO_TRUNCATE`) [MS Learn].
- Цепочка копий журнала не зависит от копий данных; Microsoft советует класть копии журнала на отдельный том от копий базы [MS Learn].
- Каждая копия пишет строку в журнал ошибок и журнал событий Windows; при частых копиях их подавляет флаг **3226** (если мониторинг на них не опирается) [MS Learn].

```sql
DECLARE @f nvarchar(400) = N'E:\Backup\buh\buh_LOG_' + FORMAT(SYSDATETIME(), N'yyyyMMdd_HHmmss') + N'.trn';
BACKUP LOG [buh] TO DISK = @f WITH CHECKSUM, COMPRESSION, INIT;
```

### 3.4. `COPY_ONLY`

| | Обычная | `COPY_ONLY` [MS Learn] |
|---|---|---|
| Полная | новая база разностных копий | база разностных не меняется, сама базой быть не может; восстанавливается как обычная |
| Журнал | усекает журнал | не усекает, на цепочку не влияет; обычно не нужна |

Для 1С [практика]: копии перед обновлением конфигурации/платформы, групповой обработкой, для разработчиков, партнёра, переноса — `COPY_ONLY`. Обычная внеплановая полная цепочку журнала не рвёт, но **сдвигает базу разностных**: если её файл потом удалят «как лишний», разностные станут бесполезны.

```sql
BACKUP DATABASE [buh] TO DISK = N'\\backup01\sql$\SQL01\buh\buh_COPY_before_update_20261020.bak'
WITH COPY_ONLY, CHECKSUM, COMPRESSION, INIT, STATS = 10;
RESTORE VERIFYONLY FROM DISK = N'\\backup01\sql$\SQL01\buh\buh_COPY_before_update_20261020.bak' WITH CHECKSUM;
```

SSMS — флажок **Copy-only backup**; PowerShell — `Backup-SqlDatabase … -CopyOnly` [MS Learn].

### 3.5. Хвост журнала

Последняя копия плана восстановления на точку сбоя; не нужна, если точка лежит в более ранней копии журнала или базу заменяют без продвижения дальше последней копии [MS Learn].

| Ситуация | Команда | Примечание [MS Learn] |
|---|---|---|
| База в сети, дальше `RESTORE` поверх | `BACKUP LOG … WITH NORECOVERY` | база → `RESTORING`; журнал усекается; может понадобиться `SINGLE_USER` для монопольного доступа |
| База не запускается, журнал цел | `… WITH NO_TRUNCATE` | = `COPY_ONLY` + `CONTINUE_AFTER_ERROR`; в `SUSPECT` возможно, в `OFFLINE`/`EMERGENCY` — нет |
| База повреждена | `… WITH CONTINUE_AFTER_ERROR` | только при целом журнале и без массовых изменений; метаданные могут быть неполны (`has_incomplete_metadata = 1`), журнал пригоден |

### 3.6. Файловые и частичные копии

Имеют смысл для баз с несколькими файловыми группами [MS Learn]. База 1С по умолчанию в одной файловой группе; пользовательские табличные пространства — только КОРП и явная настройка [ИТС-КС разд. 5.5.5.2]; поэтапное восстановление ИБ 1С документацией 1С не описано ⚠ — используйте полные копии.

## 4. Параметры `BACKUP`

### 4.1. `CHECKSUM`

- Проверяет контрольную сумму и признак «разорванной» страницы у каждой страницы (если включены) и считает общую контрольную сумму копии; отметка — `backupset.has_backup_checksums` [MS Learn].
- Умолчание — `NO_CHECKSUM`, **кроме сжатых копий**; для всех копий — `backup checksum default` = 1 (явный `NO_CHECKSUM` сильнее; полезно для средств, не передающих `CHECKSUM`, — документация называет доставку журналов и задачу копирования планов обслуживания); на время — флаг 3023 [MS Learn].
- Ошибка контрольной суммы страницы → `BACKUP` останавливается с 3043 (`STOP_ON_ERROR`), страница — в `msdb.dbo.suspect_pages`; `CONTINUE_AFTER_ERROR` снимает копию повреждённой базы (`is_damaged = 1`) [MS Learn].
- Имеет смысл при `PAGE_VERIFY CHECKSUM`; у баз со старых версий могло остаться `TORN_PAGE_DETECTION`/`NONE` — Microsoft советует `CHECKSUM` [MS Learn]. Цена — процессор и скорость копирования [MS Learn].

```sql
EXECUTE sp_configure 'backup checksum default', 1;  RECONFIGURE;    -- ALTER SETTINGS (sysadmin, serveradmin)
SELECT name, page_verify_option_desc FROM sys.databases WHERE page_verify_option_desc <> N'CHECKSUM';
-- ALTER DATABASE [buh] SET PAGE_VERIFY CHECKSUM;   -- без остановки базы [MS Learn]; уточнено 20.10.2026 по ALTER DATABASE SET options: сумма пишется в заголовок при записи страницы на диск — у страниц, не записанных после включения, её нет
```

### 4.2. `COMPRESSION`

- Enterprise, Standard, Developer; не Express и Web; восстановить сжатую копию может любая редакция с 2008 — тестовую копию на Express восстановить можно [MS Learn].
- Умолчание — без сжатия; `backup compression default` = 1 (сразу) или `WITH COMPRESSION`/`NO_COMPRESSION` [MS Learn]. Сжатие обычно ускоряет копирование, но грузит процессор (ограничение — Resource Governor) [MS Learn]. Сжатые и несжатые копии не смешиваются в одном наборе носителей [MS Learn].
- `COMPRESSION (ALGORITHM = MS_XPRESS | QAT_DEFLATE | ZSTD, LEVEL = LOW | MEDIUM | HIGH)`: `ALGORITHM` и `LEVEL` — с 2022, `ZSTD` — с 2025, `LEVEL` по умолчанию `LOW`; `backup compression algorithm` (2022+): 1 — `MS_XPRESS`, 2 — QAT, 3 — `ZSTD` [MS Learn]. У значения 3 в 2025 есть «известная проблема» — уточнено 20.10.2026 по `sql-server-2025-known-issues`: `sp_configure 'backup compression algorithm', 3` отвергается ошибкой 15129 («'3' is not a valid value…»); обход по Microsoft — указывать `ALGORITHM = ZSTD` в самой команде `BACKUP` [MS Learn].
- Степень — `backup_size / compressed_backup_size`; база с TDE сжимается плохо при `MAXTRANSFERSIZE` ≤ 64 КБ (с 2019 CU5 поднимается автоматически); флаг 3042 отключает предварительное выделение файла [MS Learn].

```sql
EXECUTE sp_configure 'backup compression default', 1;  RECONFIGURE;
BACKUP DATABASE [buh] TO DISK = N'E:\Backup\buh\buh_FULL_zstd.bak'
WITH COMPRESSION (ALGORITHM = ZSTD, LEVEL = MEDIUM), CHECKSUM, INIT, STATS = 10;   -- SQL Server 2025
SELECT TOP (10) type, backup_finish_date,
       CAST(backup_size / NULLIF(compressed_backup_size, 0) AS decimal(9,2)) AS ratio,
       compression_algorithm                                           -- колонка с 2022 [MS Learn]
FROM msdb.dbo.backupset WHERE database_name = N'buh' ORDER BY backup_finish_date DESC;
```

### 4.3. Разбиение на файлы, буферы, зеркало

- Полоса — до 64 устройств; **для восстановления нужны все файлы**; число устройств набора неизменно (иначе `FORMAT`) [MS Learn].
- `BUFFERCOUNT * MAXTRANSFERSIZE` = память буферов; `MAXTRANSFERSIZE` кратен 64 КБ, для дисков до 4 МБ (умолчание 1 МБ); избыточный `BUFFERCOUNT` грозит нехваткой памяти [MS Learn]. Подбирать замером [практика].
- `MIRROR TO` — до трёх зеркал, только Enterprise [MS Learn]; в Standard — копирование файла после копии [практика].

```sql
BACKUP DATABASE [buh]
TO DISK = N'E:\Backup\buh\buh_FULL_20261020_1.bak', DISK = N'E:\Backup\buh\buh_FULL_20261020_2.bak',
   DISK = N'F:\Backup\buh\buh_FULL_20261020_3.bak', DISK = N'F:\Backup\buh\buh_FULL_20261020_4.bak'
WITH CHECKSUM, COMPRESSION, FORMAT, MEDIANAME = N'buh_FULL_20261020', MAXTRANSFERSIZE = 4194304, BUFFERCOUNT = 50, STATS = 5;
```

### 4.4. `INIT`, `NOINIT`, `FORMAT` и имена файлов

| Параметр | Что делает [MS Learn] |
|---|---|
| `NOINIT` (умолчание) | дописывает набор в конец файла |
| `INIT` | перезаписывает наборы, сохраняя заголовок носителя (кроме неистёкших `EXPIREDATE`/`RETAINDAYS` и несовпадения имени) |
| `SKIP` | без проверок срока и имени |
| `FORMAT` | новый заголовок носителя (подразумевает `SKIP`); форматирование одного тома полосы портит всю полосу |

**Ловушка** [MS Learn — механизм; практика — последствия]: годами `BACKUP DATABASE [buh] TO DISK = N'E:\Backup\buh.bak'` без `INIT` — файл растёт, а `RESTORE … FROM DISK = N'E:\Backup\buh.bak'` без `FILE = n` восстанавливает **самую старую** копию. Номера наборов — `RESTORE HEADERONLY`, колонка `Position`. Правило: один файл — одна копия, `INIT`, имя `buh_FULL_20261020_010000.bak`; расширения `.bak` и `.trn` (Microsoft — ради единообразия и исключений антивируса) [MS Learn]. Без пути копия уходит в каталог по умолчанию (`BackupDirectory` в реестре экземпляра) [MS Learn].

### 4.5. Ход операции

```sql
-- Все сеансы видны с VIEW SERVER STATE, в 2022+ — с VIEW SERVER PERFORMANCE STATE [MS Learn]
SELECT r.session_id, r.command, r.start_time, r.percent_complete,
       DATEADD(SECOND, r.estimated_completion_time / 1000, GETDATE()) AS eta, t.text   -- колонка по документации «Internal only»; мс до конца — практика
FROM sys.dm_exec_requests AS r CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) AS t
WHERE r.command LIKE N'BACKUP%' OR r.command LIKE N'RESTORE%';
```

Глубже — расширенное событие `sqlserver.backup_restore_progress_trace` (тяжёлое, ненадолго) и счётчики **Device Throughput Bytes/sec** (`SQLServer:Backup Device`), **Backup/Restore Throughput/sec** (`SQLServer:Databases`) [MS Learn].

### 4.6. Шифрование копий

`WITH ENCRYPTION (ALGORITHM = AES_256, SERVER CERTIFICATE = <имя>)` (алгоритмы `AES_128`, `AES_192`, `AES_256`, `TRIPLE_DES_3KEY`; шифратор — сертификат в `master` или асимметричный ключ, причём только из EKM-провайдера) — не в Express и Web (восстановить зашифрованную копию они могут) [MS Learn]. **Без сертификата копию не восстановить** — храните его с закрытым ключом отдельно от копий столько же, сколько копии; то же для TDE [MS Learn]. `PASSWORD`/`MEDIAPASSWORD` для новых копий удалены с 2012 (пароль носителя — слабая защита; защищайте каталог ACL) [MS Learn].

```sql
USE master;
BACKUP CERTIFICATE BackupCert TO FILE = N'\\backup01\keys$\SQL01_BackupCert.cer'
WITH PRIVATE KEY (FILE = N'\\backup01\keys$\SQL01_BackupCert.pvk', ENCRYPTION BY PASSWORD = N'<пароль ключа>');   -- синтаксис подтверждён 20.10.2026 (MS Learn, BACKUP CERTIFICATE)
BACKUP DATABASE [buh] TO DISK = N'E:\Backup\buh\buh_FULL_enc.bak'
WITH ENCRYPTION (ALGORITHM = AES_256, SERVER CERTIFICATE = BackupCert), COMPRESSION, CHECKSUM, INIT;
```

Подтверждено 20.10.2026 (MS Learn, `BACKUP CERTIFICATE`): `TO FILE` принимает локальный путь или UNC; `WITH PRIVATE KEY (FILE = …, ENCRYPTION BY PASSWORD = …)`; с 2022 есть `FORMAT = 'PFX'` (сертификат и ключ в одном файле). Ключи и сертификаты — `mssql/03-…`.

### 4.7. Права

- `BACKUP DATABASE/LOG` — `sysadmin`, `db_owner`, `db_backupoperator` (роль: `BACKUP DATABASE`, `BACKUP LOG`, `CHECKPOINT`) [MS Learn].
- **Файл пишет процесс SQL Server**: права на каталог — у учётной записи службы; права отправившего `BACKUP` на файлы роли не играют [MS Learn]. `sp_addumpdevice` права не проверяет [MS Learn].
- Учётным записям копирования — не больше прав, чем нужно [MS Learn]; заданию копий достаточно `db_backupoperator` [практика].

```sql
-- CREATE LOGIN [CORP\svc-sqlbackup] FROM WINDOWS;   -- однократно [практика]
USE [buh];
CREATE USER [CORP\svc-sqlbackup] FOR LOGIN [CORP\svc-sqlbackup];
ALTER ROLE db_backupoperator ADD MEMBER [CORP\svc-sqlbackup];
```

## 5. Куда класть копии

### 5.1. Не рядом с базой

- Копии — не на дисках данных и журнала (и не на другом томе того же диска): при отказе устройства пропадут и база, и копия [MS Learn]; 1С: копии только на локальном диске сервера СУБД «существенно снижают надёжность» [ИТС-мет 2378, 2008].
- Архив копий — вне площадки [MS Learn]; правило «3-2-1» [практика]. От шифровальщиков — копия, недоступная на изменение с сервера SQL (отдельные учётные данные, неизменяемое хранилище) [практика]; Azure — неизменяемое хранилище с 2025 (5.3) [MS Learn].

### 5.2. Сетевая папка

В 2008 году ИТС советовал `SP_ADDUMPDEVICE 'disk', '<имя>', '\\Компьютер\Каталог\Файл.bak'` и запуск SQL Server под доменной учётной записью — Enterprise Manager видел только локальные диски [ИТС-мет 2378, 2008]. Сейчас UNC пишут прямо в `TO DISK` [MS Learn]:

```sql
BACKUP DATABASE [buh] TO DISK = N'\\backup01\sql$\SQL01\buh\buh_FULL_20261020_010000.bak' WITH CHECKSUM, COMPRESSION, INIT, STATS = 10;
```

Требования [MS Learn]: доступ нужен **учётной записи службы SQL Server** (запись — копирование, чтение — восстановление); служба не видит подключённых букв дисков; виртуальная учётная запись (`NT SERVICE\MSSQLSERVER`, умолчание установки) и `NETWORK SERVICE` выходят в сеть как **учётная запись компьютера** `CORP\SQL01$`; после копирования по сети — `RESTORE VERIFYONLY` (сетевые ошибки).

```sql
SELECT servicename, service_account, instant_file_initialization_enabled FROM sys.dm_server_services;   -- кто служба [MS Learn]
```

```powershell
# На файловом сервере backup01 (администратор) [практика]
New-SmbShare -Name 'sql$' -Path 'F:\SQLBackup' -ChangeAccess 'CORP\SQL01$' -FullAccess 'CORP\Domain Admins'
icacls 'F:\SQLBackup\SQL01' /grant 'CORP\SQL01$:(OI)(CI)M'
# Проверка: на SQL01 — COPY_ONLY-копия маленькой базы в \\backup01\sql$\SQL01\ и RESTORE VERIFYONLY
```

- 3201 «Cannot open backup device … Operating system error 5 (Access is denied.)» — нет прав у службы или неверный путь [MS Learn].
- Рабочая группа: учётная запись компьютера в сети не работает; обход — служба под локальной учётной записью с тем же именем и паролем на файловом сервере ⚠ [практика]; надёжнее копировать локально и переносить файлы отдельной задачей.

### 5.3. URL (Azure, S3) — кратко

| | Azure Blob Storage | S3-совместимое |
|---|---|---|
| Версии | 2012 SP1 CU2; с 2016 — блочные блобы и полосы до 64 URL; неизменяемое хранилище (контейнер) — 2025; управляемое удостоверение — 2025 (Azure Arc) | 2022 |
| Учётные данные | `CREDENTIAL` с SAS (`IDENTITY = 'SHARED ACCESS SIGNATURE'`) — только он даёт блочные блобы | `CREATE CREDENTIAL [s3://<endpoint>:<port>/<bucket>] WITH IDENTITY = 'S3 Access Key', SECRET = '<AccessKeyID>:<SecretKeyID>'` |
| Ограничения | ~195,3 ГБ на блочный блоб → крупные — полосой | 10 000 частей; часть 5–20 МБ (`MAXTRANSFERSIZE`, умолчание 10 МБ, менять только со сжатием); TLS обязателен; Express — нет |

Источник — [MS Learn]. Очистку старых копий в URL делают политикой хранилища (Ola Hallengren её для URL не поддерживает [сторонний]) [практика].

### 5.4. SQL Server на Linux

- Копии Windows ↔ Linux совместимы (если параметры сортировки поддерживаются ОС); Microsoft рекомендует перенос копией и восстановлением [MS Learn].
- Файлы для `RESTORE` — в подкаталоге `/var/opt/mssql` (владелец `mssql:mssql`); каталог копий по умолчанию — `filelocation.defaultbackupdir` = `/var/opt/mssql/data` (`sudo /opt/mssql/bin/mssql-conf set filelocation.defaultbackupdir <каталог>`); агент выключен по умолчанию (`mssql-conf set sqlagent.enabled true`) [MS Learn].
- VSS и SQL Writer на Linux нет [MS Learn] — опирайтесь на собственные копии SQL Server.
- Базы 1С на таком сервере обслуживают только рабочие серверы 1С на Windows [ИТС-КС разд. 2.3]. Пример — 17.4.

## 6. Цепочка журнала: как устроена и что её рвёт

### 6.1. LSN и непрерывность

| `msdb.dbo.backupset` / `RESTORE HEADERONLY` | Смысл [MS Learn] |
|---|---|
| `first_lsn` / `FirstLSN` | первая запись журнала в наборе |
| `last_lsn` / `LastLSN` | **следующая** запись после набора |
| `checkpoint_lsn` / `CheckpointLSN` | с этой записи начинается повтор |
| `database_backup_lsn` / `DatabaseBackupLSN` | LSN последней полной копии — «начало контрольной точки» в момент её старта; у разностных и копий журнала на практике равен `checkpoint_lsn` полной копии, на которой они основаны (так это равенство Microsoft прямо не формулирует) |
| `begins_log_chain` / `BeginsLogChain` | 1 — первая копия журнала новой цепочки (после создания базы или перехода из `SIMPLE`) |
| `is_copy_only`, `has_backup_checksums`, `is_damaged`, `has_bulk_logged_data` | признаки набора |

Цепочка непрерывна, если `first_lsn` следующей копии журнала равен `last_lsn` предыдущей [MS Learn — определения; практика — правило]. Потеряна копия журнала — восстановиться можно только до неё [MS Learn].

Пример Microsoft: 8:00 полная, 12:00 и 16:00 журнал, 18:00 полная, 20:00 журнал (содержит записи 16:00–20:00, «перекрывая» полную 18:00). На точку 21:45: полная 18:00 + журнал 20:00 + хвост **или** полная 8:00 + все четыре журнала + хвост — страховка, если полная 18:00 испорчена [MS Learn].

### 6.2. Что рвёт цепочку

| Действие | Цепочка журнала | База разностных | Источник |
|---|---|---|---|
| Обычная полная копия | не рвётся | сдвигается | [MS Learn] |
| Полная `COPY_ONLY`, разностная, журнал `COPY_ONLY` | не рвётся | не меняется | [MS Learn] |
| Переход в `SIMPLE` и обратно | **рвётся**; новая — после полной/разностной | — | [MS Learn] |
| Потеря файла копии журнала | **рвётся** для восстановления (сервер этого не видит) | — | [MS Learn] |
| Копия журнала «чужой» программой в неизвестное место | **рвётся** для вас | — | [практика] |
| `BACKUP LOG … TO DISK = 'NUL'` | **рвётся**: NUL выбрасывает данные, а журнал считается скопированным | — | [MS Learn — NUL; практика — вывод] |
| VSS-копия программы ВМ/СРК не в режиме copy | не рвётся (VSS не копирует журнал) | **сдвигается** на копию, которой у вас нет | [MS Learn] |
| `RESTORE … WITH REPLACE` из старой копии / `RECOVERY` на момент | новая «развилка» (recovery fork); старые копии журнала после неё не применимы | — | [MS Learn — `fork_point_lsn`; практика] |
| Загрузка `.dt` в существующую базу | формально сохраняется, журнал огромный; после — полная копия | — | [практика] ⚠ |

### 6.3. Проверка по `msdb`

```sql
-- Разрывы цепочки копий журнала за 7 дней [практика; колонки — MS Learn]
WITH l AS (
    SELECT bs.database_name, bs.backup_finish_date, bs.first_lsn, bs.last_lsn, bs.begins_log_chain,
           LAG(bs.last_lsn) OVER (PARTITION BY bs.database_name ORDER BY bs.first_lsn) AS prev_last_lsn,
           bmf.physical_device_name
    FROM msdb.dbo.backupset AS bs
    JOIN msdb.dbo.backupmediafamily AS bmf
      ON bmf.media_set_id = bs.media_set_id AND bmf.family_sequence_number = 1 AND bmf.mirror = 0
    WHERE bs.type = 'L' AND bs.is_copy_only = 0 AND bs.database_name = N'buh'
      AND bs.backup_start_date > DATEADD(DAY, -7, GETDATE()))
SELECT * FROM l
WHERE (prev_last_lsn IS NOT NULL AND first_lsn <> prev_last_lsn) OR begins_log_chain = 1;   -- пусто = разрывов нет

-- «Чужие» копии: виртуальные устройства (VSS/VDI), снимки, не ваш каталог
SELECT bs.database_name, bs.type, bs.backup_finish_date, bs.is_copy_only, bs.is_snapshot, bs.user_name,
       bmf.device_type,                      -- 2 диск, 5 лента, 7 виртуальное устройство, 9 Azure [MS Learn]
       bmf.physical_device_name
FROM msdb.dbo.backupset AS bs JOIN msdb.dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id
WHERE bs.backup_finish_date > DATEADD(DAY, -30, GETDATE())
  AND (bmf.device_type = 7 OR bs.is_snapshot = 1
       OR (bmf.device_type = 2 AND bmf.physical_device_name NOT LIKE N'E:\Backup\%'
                               AND bmf.physical_device_name NOT LIKE N'\\backup01\sql$\%'))
ORDER BY bs.backup_finish_date DESC;
```

У VSS/VDI-копий имя устройства обычно — GUID (`{AA4B3232-…}`) [MS Learn — пример ошибки 18210].

## 7. Рост журнала, ошибка 9002, усечение и сжатие

### 7.1. Усечение ≠ сжатие

- **Усечение** освобождает неактивные VLF внутри файла; размер файла не меняется. Происходит: в `SIMPLE` — после контрольной точки; в `FULL`/`BULK_LOGGED` — после копии журнала (не `COPY_ONLY`), если была контрольная точка; новая база в `FULL` до первой полной копии ведёт себя как `SIMPLE` [MS Learn].
- **Сжатие** (`DBCC SHRINKFILE`) возвращает место ОС, только если в конце файла есть неактивные VLF; это **не регулярная операция** — выросший от работы файл вырастет снова, а рост журнала дорог [MS Learn; ИТС-мет 6008, 2023].

### 7.2. `log_reuse_wait_desc`

| Значение | Причина [MS Learn] | Что делать в среде 1С [практика, если не указано] |
|---|---|---|
| `NOTHING` / `CHECKPOINT` | свободные VLF есть / не было контрольной точки | ничего; при затяжке — `CHECKPOINT` [MS Learn] |
| `LOG_BACKUP` | нужна копия журнала | наладить копии журнала; если журнал ни разу не копировался — **две** копии [MS Learn] |
| `ACTIVE_BACKUP_OR_RESTORE` | идёт копия данных или восстановление | дождаться или отменить копию [MS Learn] |
| `ACTIVE_TRANSACTION` | длинная/отложенная транзакция; мешает при любой модели, в том числе `SIMPLE` | найти (7.3): зависший сеанс 1С, обмен, закрытие месяца, «забытый» конфигуратор |
| `REPLICATION` | недоставленные транзакции репликации; так же действуют CDC и отслеживание изменений | у 1С — механизм копий базы данных «Версия2» на MS SQL использует CDC [ИТС-разр гл. 26]: проверить агент и задания CDC |
| `AVAILABILITY_REPLICA` | вторичная реплика отстаёт | `mssql/07-…` |
| `DATABASE_SNAPSHOT_CREATION`, `LOG_SCAN`, `OLDEST_PAGE`, `XTP_CHECKPOINT`, `SLOG_SCAN` | кратковременные; косвенные контрольные точки; In-Memory OLTP; ADR | для 1С нетипично ⚠ |

### 7.3. Диагностика

```sql
DBCC SQLPERF (LOGSPACE);                                        -- заполненность журналов всех баз [MS Learn]
USE [buh];
SELECT total_log_size_in_bytes / 1048576.0 AS log_mb, used_log_space_in_percent,
       log_space_in_bytes_since_last_backup / 1048576.0 AS since_last_log_backup_mb   -- колонка с 2014
FROM sys.dm_db_log_space_usage;                                 -- [MS Learn]
SELECT COUNT(*) AS vlf_count, SUM(CASE WHEN vlf_active = 1 THEN 1 ELSE 0 END) AS active_vlf
FROM sys.dm_db_log_info(DB_ID(N'buh'));                         -- 2016 SP2+ [MS Learn]
DBCC OPENTRAN (N'buh');                                         -- самая старая активная транзакция [MS Learn]
SELECT dt.database_transaction_begin_time, dt.database_transaction_log_bytes_used / 1048576.0 AS log_mb,
       st.session_id, s.host_name, s.program_name, s.login_name
FROM sys.dm_tran_database_transactions AS dt
JOIN sys.dm_tran_session_transactions AS st ON st.transaction_id = dt.transaction_id
JOIN sys.dm_exec_sessions AS s ON s.session_id = st.session_id
WHERE dt.database_id = DB_ID(N'buh') ORDER BY dt.database_transaction_begin_time;
```

Колонки `sys.dm_tran_database_transactions`, `sys.dm_tran_session_transactions` (`session_id`, `transaction_id`) и `sys.dm_exec_sessions` (`host_name`, `program_name`, `login_name`) — подтверждено 20.10.2026 (MS Learn); в 2022+ эти DMV требуют `VIEW SERVER PERFORMANCE STATE`. Все подключения 1С идут с рабочего сервера под одним логином; пользователя 1С по `session_id` покажет консоль кластера («Соединение с СУБД») [ИТС-КС разд. 5.2.12.2]; подробно — `mssql/06-…`, `mssql/08-…`.

### 7.4. Ошибка 9002

Текст: «The transaction log for database '…' is full. To find out why space in the log cannot be reused, see the log_reuse_wait_desc column in sys.databases.» Если журнал заполнился при работе — база в сети, но только на чтение; если при восстановлении (recovery) — по документации база помечается `RESOURCE PENDING` [MS Learn] (в `sys.databases.state_desc` такого значения нет; видимо, `RECOVERY_PENDING` ⚠). Для 1С — массовые ошибки записи у всех [практика].

Действия [MS Learn, кроме помеченного]:

1. `SELECT name, recovery_model_desc, log_reuse_wait_desc FROM sys.databases WHERE name = N'buh';`
2. `LOG_BACKUP` → копия журнала (если не копировался — две); нет места для копии — на другой диск или в сетевую папку [практика].
3. Освободить место на томе журнала или временно **добавить файл журнала на другом диске** (`ALTER DATABASE … ADD LOG FILE`); несколько файлов журнала производительности не дают — это временная мера.
4. `MAXSIZE` или выключенный автоприрост → поднять `MAXSIZE`/включить `FILEGROWTH` (максимум файла журнала — 2 ТБ).
5. `ACTIVE_TRANSACTION` → найти транзакцию (7.3), завершить сеанс в 1С (консоль или `rac session terminate`, `../1c/03-…`); `KILL` — «с крайней осторожностью» (откат длинной транзакции сам долгий).
6. Если 9002 возникла во время восстановления базы — после устранения причины `ALTER DATABASE [buh] SET ONLINE;`.

```sql
ALTER DATABASE [buh] ADD LOG FILE (NAME = N'buh_log_tmp', FILENAME = N'E:\TempLog\buh_log_tmp.ldf', SIZE = 8192MB, FILEGROWTH = 1024MB);
-- потом, когда файл освободится: REMOVE FILE удаляет только пустой файл [MS Learn]; EMPTYFILE документация описывает для файлов данных, для журнала этот порядок — практика ⚠:
-- USE [buh]; DBCC SHRINKFILE (N'buh_log_tmp', EMPTYFILE); ALTER DATABASE [buh] REMOVE FILE [buh_log_tmp];
```

### 7.5. Почему `TRUNCATE_ONLY` удалён и как сжимать сейчас

**Старый рецепт** [ИТС-мет 2373, 2008]: при росте журнала, если `DBCC SHRINKFILE` не уменьшает файл, выполнить `BACKUP LOG <база> WITH TRUNCATE_ONLY`, затем `DBCC SHRINKFILE(<файл журнала>)`.

**Сейчас** [MS Learn]: `BACKUP LOG WITH NO_LOG` и `WITH TRUNCATE_ONLY` удалены; чтобы избавиться от цепочки копий журнала, базу переводят в `SIMPLE`. Версия удаления на прочитанных страницах не указана (по истории — SQL Server 2008 ⚠). Смысл [практика]: `TRUNCATE_ONLY` молча рвал цепочку, оставляя `FULL` с иллюзией восстановления на момент; переход в `SIMPLE` делает разрыв явным.

```sql
-- Вариант 1: цепочка сохраняется (FULL)
BACKUP LOG [buh] TO DISK = N'E:\Backup\buh\buh_LOG_before_shrink.trn' WITH CHECKSUM, COMPRESSION, INIT;
USE [buh];
SELECT name, type_desc, size / 128 AS size_mb FROM sys.database_files;    -- логическое имя журнала
DBCC SHRINKFILE (N'buh_log', 8192);       -- МБ [MS Learn]; не сжалось — активная часть в конце: ещё копия журнала и повтор
-- Вариант 2: момент времени НЕ нужен — цепочка рвётся! Перед этим — полная копия.
ALTER DATABASE [buh] SET RECOVERY SIMPLE;
USE [buh]; CHECKPOINT; DBCC SHRINKFILE (N'buh_log', 8192);
ALTER DATABASE [buh] SET RECOVERY FULL;
BACKUP DATABASE [buh] TO DISK = N'E:\Backup\buh\buh_FULL_newchain.bak' WITH CHECKSUM, COMPRESSION, INIT;   -- новая цепочка
```

**Размер журнала для 1С**:

- Журнал — такой, чтобы не расти между `BACKUP LOG`; в `model` журнал 1–2 ГБ, прирост 512 МБ [ИТС-мет 5904, 2019]. IFI к журналу не применяется — размер задавать заранее [ИТС-мет 6008, 2023]; уточнение Microsoft: с 2022 приросты журнала **до 64 МБ** используют IFI (без `SE_MANAGE_VOLUME_NAME`), крупнее — с обнулением [MS Learn].
- Microsoft: прирост в МБ, не в процентах; `FILEGROWTH` журнала ≤ 1024 МБ; умолчание с 2016 — 64 МБ; мелкий шаг — много VLF, крупный — паузы и крупные VLF; несколько файлов журнала не ускоряют; `AUTO_SHRINK` не включать; при оценке размера учитывать журнал за время полной копии, крупнейшего обслуживания индексов и крупнейшего пакета [MS Learn].
- Самые «журналоёмкие» операции 1С: перестроение индексов в `FULL` (ночной регламент ИТС-мет 5837 [ИТС-мет 5837, 2022]), реструктуризация, загрузка `.dt`, закрытие периода, перепроведение [практика]. Регламент индексов — `mssql/05-…`.

### 7.6. ADR

Ускоренное восстановление (2019+; `ALTER DATABASE [<db>] SET ACCELERATED_DATABASE_RECOVERY = ON;`) даёт мгновенный откат и **агрессивное усечение журнала при длинных транзакциях**; с репликацией и CDC агрессивное усечение отключается; при интенсивной записи журнал и его копии растут [MS Learn]. Рекомендаций 1С по ADR в источниках нет ⚠ — только после испытаний на копии.

## 8. Восстановление: схема, права, монопольный доступ

### 8.1. `RECOVERY`, `NORECOVERY`, `STANDBY`

- Восстановление: копирование страниц → повтор (redo) журнала → откат (undo) незавершённых; после отката база в сети и копии журнала больше не применить [MS Learn].
- `RECOVERY` (умолчание) — откат, база готова; `NORECOVERY` — без отката, база в `RESTORING`; `STANDBY = <файл>` — только чтение между копиями журнала, файл до следующего `RESTORE` не удалять [MS Learn].
- **Лучшая практика**: все шаги `NORECOVERY`, затем отдельно `RESTORE DATABASE <база> WITH RECOVERY`. Поспешный `RECOVERY` — последовательность заново с полной копии; отменить восстановление нельзя [MS Learn].

### 8.2. Права

- Базы нет — нужно `CREATE DATABASE`; база есть — `sysadmin`, `dbcreator`, владелец (`dbo`); **`db_owner` права `RESTORE` не имеет** (членство в роли нельзя проверить у недоступной базы) [MS Learn]. `RESTORE VERIFYONLY/HEADERONLY/FILELISTONLY` — `CREATE DATABASE` [MS Learn].
- 1С рекомендует логину кластера роль `dbcreator` [ИТС-мет 5904, 2019], ИТС-мет 2926 (2008) — снимать её после создания базы; `dbcreator` может восстановить и удалить **любую** базу экземпляра [MS Learn] — на общем экземпляре это риск; восстанавливает администратор СУБД [практика].

### 8.3. Хвост журнала, `REPLACE`, ошибка 3159

- В `FULL`/`BULK_LOGGED` без копии хвоста — ошибка **3159** («The tail of the log … has not been backed up …»), если нет `REPLACE` или `STOPAT` после конца копии данных [MS Learn].
- `REPLACE` снимает проверки [MS Learn]: восстановление поверх **другой** базы (не совпал `family_guid`); отсутствие копии хвоста (работа теряется); перезапись неопознанных файлов. «Использовать редко и обдуманно».
- `RESTORE` нельзя внутри транзакции; прерванное восстановление — `WITH RESTART` [MS Learn].

### 8.4. Монопольный доступ

**ИТС**: во время восстановления к ИБ не должно быть подключений — конфигуратора, клиентов, фоновых и регламентных заданий, средств администрирования [ИТС-КС разд. 5.1.1]; монопольный режим ИБ не переводит базу MS SQL в `SINGLE_USER` [ИТС-адм разд. 6.7].

**Шаг 1 — 1С** (`rac` из каталога `bin` платформы на сервере 1С; ключи сверить с `rac help infobase` — `../1c/03-…`):

```cmd
rac infobase update --cluster=<uuid кластера> --infobase=<uuid ИБ> --infobase-user=<админ ИБ> --infobase-pwd=<пароль> ^
    --sessions-deny=on --scheduled-jobs-deny=on --denied-message="Восстановление базы" --permission-code=RESTORE2026
rac session list --cluster=<uuid кластера> --infobase=<uuid ИБ>
rac session terminate --cluster=<uuid кластера> --session=<uuid сеанса>
```

Блокировка начала сеансов не выгоняет существующие сеансы и не мешает им открывать соединения [ИТС-КС разд. 5.2.7.2] — сеансы завершают.

**Шаг 2 — SQL Server** [MS Learn, кроме помеченного]:

- `ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;` — откат и немедленное отключение остальных; режим остаётся после отключения автора (войти может один любой). Право — `ALTER`.
- **`AUTO_UPDATE_STATISTICS_ASYNC = ON` мешает**: фоновый поток статистики занимает подключение, войти в `SINGLE_USER` нельзя. 1С это значение рекомендует [ИТС-мет 5904, 2019]. Выход [практика]: перед работой `ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC OFF;` — после `RESTORE` параметры базы вернутся к значениям из копии [MS Learn].
- `RESTRICTED_USER` пускает `db_owner`, `dbcreator`, `sysadmin` — логин 1С обычно `db_owner`/владелец, от переподключений 1С не спасает [MS Learn — определение; практика — вывод].
- Надёжно — временно `ALTER LOGIN [buh_1c] DISABLE;` (после — `ENABLE`) [MS Learn — синтаксис; практика — приём]; **осторожно**, если кластер ходит в SQL Server под общей Windows-учётной записью службы 1С (заденет все базы); Windows-группу так не отключить [MS Learn].
- SSMS: флажок **Close existing connections** включает однопользовательский режим на время восстановления.
- Документация: офлайн-`RESTORE` «через короткую задержку» сам отключает пользователей; на практике часто ошибка «Exclusive access could not be obtained because the database is in use» (текст подтверждён 20.10.2026: MS Learn, `restore-a-database-backup-using-ssms` — так SSMS падает без флажка Close existing connections; номер 3101 — ⚠, сверить: `SELECT text FROM sys.messages WHERE message_id = 3101 AND language_id = 1033;`). Отключайте явно [практика].

### 8.5. Порядок и план восстановления

Набор: последняя полная (или `COPY_ONLY`, но тогда без разностных), последняя разностная на её основе, все копии журнала после неё по порядку, при необходимости хвост; содержимое файлов — `RESTORE HEADERONLY` (`Position` для `FILE = n`, `BackupType`: 1 база, 2 журнал, 5 разностная; LSN; `HasBackupChecksums`; `IsCopyOnly`) и `RESTORE FILELISTONLY` (логические и физические имена, `Size` в байтах) [MS Learn].

```sql
-- Какие файлы нужны для восстановления buh на момент @target (по истории msdb этого сервера) [практика; колонки — MS Learn]
USE msdb;
DECLARE @db sysname = N'buh', @target datetime = '2026-10-19T10:30:00';
DECLARE @full_id int, @full_ckpt numeric(25,0), @diff_id int, @base_last numeric(25,0);
SELECT TOP (1) @full_id = backup_set_id, @full_ckpt = checkpoint_lsn, @base_last = last_lsn
FROM dbo.backupset WHERE database_name = @db AND type = 'D' AND is_copy_only = 0 AND backup_finish_date <= @target
ORDER BY backup_finish_date DESC;
SELECT TOP (1) @diff_id = backup_set_id, @base_last = last_lsn          -- нет разностной — переменные не меняются
FROM dbo.backupset WHERE database_name = @db AND type = 'I' AND database_backup_lsn = @full_ckpt AND backup_finish_date <= @target
ORDER BY backup_finish_date DESC;
SELECT 1 AS step, bs.type, bs.backup_finish_date, bmf.family_sequence_number, bmf.physical_device_name
FROM dbo.backupset AS bs JOIN dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id AND bmf.mirror = 0
WHERE bs.backup_set_id = @full_id
UNION ALL
SELECT 2, bs.type, bs.backup_finish_date, bmf.family_sequence_number, bmf.physical_device_name
FROM dbo.backupset AS bs JOIN dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id AND bmf.mirror = 0
WHERE bs.backup_set_id = @diff_id
UNION ALL
SELECT 3, bs.type, bs.backup_finish_date, bmf.family_sequence_number, bmf.physical_device_name
FROM dbo.backupset AS bs JOIN dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id AND bmf.mirror = 0
WHERE bs.database_name = @db AND bs.type = 'L' AND bs.is_copy_only = 0 AND bs.last_lsn > @base_last
  AND bs.backup_finish_date <= ISNULL((SELECT MIN(x.backup_finish_date) FROM dbo.backupset AS x
                                       WHERE x.database_name = @db AND x.type = 'L' AND x.is_copy_only = 0
                                         AND x.backup_finish_date >= @target), '99991231')
ORDER BY step, backup_finish_date, family_sequence_number;
```

Проверьте глазами: журналы без разрывов (6.3), последний заканчивается **после** `@target`. На другом сервере истории нет — выбирайте файлы вручную или загрузите историю `RESTORE VERIFYONLY … WITH LOADHISTORY` в порядке создания копий [MS Learn]. Альтернативы — шкала **Timeline** окна Restore Database в SSMS (Database Recovery Advisor) [MS Learn] и `Restore-DbaDatabase -RestoreTime … -OutputScriptOnly` [сторонний].

### 8.6. Сколько займёт

- Файлы данных обнуляются, если не включена мгновенная инициализация (IFI: право `SE_MANAGE_VOLUME_NAME` / «Perform volume maintenance tasks» у службы или её SID; проверка — `sys.dm_server_services.instant_file_initialization_enabled`); TDE мешает IFI данных [MS Learn]. Настройка — `mssql/02-…`.
- **Файл журнала** создаётся в исходном размере и обнуляется (IFI для журнала — только приросты до 64 МБ с 2022) [MS Learn — правила IFI]; раздутый журнал удлиняет восстановление [практика].
- Ход — `percent_complete` (4.5); фазы восстановления пишутся в журнал ошибок [MS Learn].

### 8.7. После восстановления

- Параметры `ALTER DATABASE` возвращаются к значениям на конец копии (модель, `READ_COMMITTED_SNAPSHOT`, `AUTO_UPDATE_STATISTICS_ASYNC`…); `WITH RESTRICTED_USER` переопределяет режим доступа; кеш планов базы сброшен [MS Learn]. Осталась в `SINGLE_USER` — `SET MULTI_USER` [практика].
- На другом сервере владелец — тот, кто восстанавливал [MS Learn] (10.3).
- Копия старой версии обновляется при `RECOVERY`; новее сервера — нельзя (3169); системные базы — только из копий той же версии и уровня обновления; при переносе на 2022 с более ранней — `sp_updatestats` [MS Learn]. Обновление версий — `mssql/07-…`.

## 9. На момент времени (`STOPAT`) и до точки сбоя

### 9.1. Условия [MS Learn, кроме помеченного]

- Только `FULL` (в `BULK_LOGGED` — не внутри копии журнала с массовыми изменениями); момент — всегда из копии журнала; сначала полная копия, **закончившаяся раньше** момента (можно и более старую, если затем применить все журналы).
- **В каждой** `RESTORE LOG` — одинаковый `STOPAT`; в `RESTORE DATABASE` он даёт ошибку, если копия данных новее момента. Точка — последняя фиксация не позже момента. Момент позже последней копии журнала — база остаётся невосстановленной с предупреждением.
- Неизвестный момент ищут с `STANDBY` (журналы по одному, между шагами — запросы только на чтение); открыть такую базу в 1С нельзя ⚠ [практика].
- Часовой пояс `STOPAT` прямо не указан ⚠ (в примерах — локальное время сервера [практика]); смещение дат 1С на `STOPAT` не влияет [практика].

### 9.2. «Как было в 10:30» — рядом с рабочей базой

```sql
USE master;   -- sysadmin / dbcreator; рабочую базу не трогаем
RESTORE DATABASE [buh_1030] FROM DISK = N'E:\Backup\buh\buh_FULL_20261019_010000.bak'
  WITH MOVE N'buh' TO N'D:\MSSQL\Data\buh_1030.mdf', MOVE N'buh_log' TO N'L:\MSSQL\Log\buh_1030_log.ldf', NORECOVERY, STATS = 10;
RESTORE DATABASE [buh_1030] FROM DISK = N'E:\Backup\buh\buh_DIFF_20261019_090000.bak' WITH NORECOVERY;
-- … сначала ВСЕ копии журнала после разностной по порядку (09:15, 09:30, 09:45, 10:00) — так же WITH NORECOVERY, STOPAT = N'2026-10-19T10:30:00';
-- с пропущенным звеном следующие копии журнала не применятся (журналы каждые 15 мин, раздел 1.3)
RESTORE LOG [buh_1030] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_101500.trn' WITH NORECOVERY, STOPAT = N'2026-10-19T10:30:00';
RESTORE LOG [buh_1030] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_103000.trn' WITH NORECOVERY, STOPAT = N'2026-10-19T10:30:00';
RESTORE LOG [buh_1030] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_104500.trn' WITH NORECOVERY, STOPAT = N'2026-10-19T10:30:00';
RESTORE DATABASE [buh_1030] WITH RECOVERY;
SELECT TOP (5) restore_date, destination_database_name, stop_at FROM msdb.dbo.restorehistory ORDER BY restore_date DESC;   -- проверка
```

Дальше — регистрация копии в кластере с блокировкой регламентных заданий (10.4) и перенос данных средствами 1С (17.1). **Вернуть отдельный документ «на месте» средствами SQL Server нельзя**: связаны документ, движения регистров, итоги, история данных — переносить механизмами 1С (выгрузка/загрузка XML, обработки переноса) [практика].

### 9.3. До точки сбоя

```sql
BACKUP LOG [buh] TO DISK = N'E:\Backup\buh\buh_TAIL_20261019_2150.trn' WITH NORECOVERY, CHECKSUM, INIT;   -- хвост [MS Learn]
-- повреждена/офлайн: WITH NO_TRUNCATE или CONTINUE_AFTER_ERROR (3.5)
-- затем полная, разностная, все журналы и хвост WITH NORECOVERY; RESTORE DATABASE [buh] WITH RECOVERY;
```

### 9.4. Метки и LSN

`STOPATMARK = 'имя' | 'lsn:<номер>'` и `STOPBEFOREMARK` — до помеченной транзакции (`BEGIN TRANSACTION <имя> WITH MARK`) или LSN; `mark_name` — только в `RESTORE LOG`; метки служат для согласованного восстановления связанных баз [MS Learn]. 1С меток не ставит ⚠.

## 10. Под другим именем и на другом сервере (`MOVE`)

### 10.1. `MOVE`

- Без `MOVE` файлы восстанавливаются по исходным путям; иной путь, занятый файл, другой диск — `MOVE '<логическое имя>' TO '<путь>'` для **каждого** файла (список — `RESTORE FILELISTONLY`); пути по умолчанию у версий разные (`MSSQL13.…`, `MSSQL16.…`) — для копий старых версий `MOVE` почти всегда нужен [MS Learn].
- 3156 «File '…' cannot be restored to '…'. Use WITH MOVE …», 5133 «Directory lookup … failed with the operating system error 2» — нет пути/доступа или забыт `.ndf` (табличные пространства 1С КОРП) [MS Learn].
- В `RESTORE LOG` `MOVE` нужен только для файлов, добавленных за период копии; `RESTORE VERIFYONLY … WITH MOVE` проверяет место и конфликты; логическое имя меняет `ALTER DATABASE [buh_test] MODIFY FILE (NAME = N'buh', NEWNAME = N'buh_test');` [MS Learn].

### 10.2. Новое имя на том же сервере

Имя в `RESTORE DATABASE` становится именем новой базы, `REPLACE` не нужен [MS Learn]; `MOVE` — всегда, иначе попытка писать в файлы рабочей базы [практика]. Новая база сохраняет `family_guid` оригинала [MS Learn]. Регистрировать копию в 1С — только как новую ИБ (10.4).

### 10.3. Другой сервер: логины, владелец, прочее

- На более новую версию — можно, на старую — нельзя; Windows → Linux — можно [MS Learn].
- **Владелец** — логин, выполнивший восстановление [MS Learn]; у баз, созданных кластером 1С, владельцем был логин 1С [ИТС-мет 2926, 2008]:

```sql
SELECT name, SUSER_SNAME(owner_sid) AS owner FROM sys.databases WHERE name = N'buh';
USE [buh];
SELECT dp.type_desc, dp.sid, dp.name AS user_name                -- «осиротевшие» пользователи [MS Learn]
FROM sys.database_principals AS dp LEFT JOIN sys.server_principals AS sp ON dp.sid = sp.sid
WHERE sp.sid IS NULL AND dp.authentication_type_desc = 'INSTANCE';
-- CREATE LOGIN [buh_1c] WITH PASSWORD = N'<пароль>', SID = 0x…;   -- логина нет: тот же SID [MS Learn]
-- ALTER USER [buh_1c] WITH LOGIN = [buh_1c];                      -- логин есть с другим SID [MS Learn]
-- ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];             -- владелец — логин 1С [MS Learn — синтаксис; практика — когда]
```

`sp_change_users_login` устарела [MS Learn]. Логины с теми же SID и хешами паролей переносят скриптом `sp_help_revlogin` (статья поддержки Microsoft, не читалась ⚠) или `Copy-DbaLogin` (dbatools; уточнено 20.10.2026 по исходнику `public/Copy-DbaLogin.ps1`: `-Source`, `-Destination`, `-Login`; переносит логины SQL и Windows с паролями и исходными SID, `-NewSid` — только для клонирования) [сторонний].
- Не переносятся с базой [MS Learn]: логины, задания, связанные серверы, учётные данные, сертификаты (TDE, шифрование копий), параметры экземпляра, флаги трассировки — рекомендованные 1С настройки экземпляра (`mssql/02-…`) задать заново [практика].
- Параметры сортировки экземпляра (`tempdb`) держите как у баз 1С; влияние расхождения на 1С в источниках не описано ⚠.
- **CDC** (копии базы данных 1С «Версия2»): при восстановлении на другом сервере настройки CDC удаляются без `KEEP_CDC` (несовместим с `NORECOVERY`), задания захвата и очистки не создаются (`sys.sp_cdc_add_job`) [MS Learn]; проще заново включить «Версия2» в 1С ⚠ [ИТС-разр гл. 26; практика]. Service Broker по умолчанию выключается при восстановлении (`ENABLE_BROKER`/`NEW_BROKER`) [MS Learn]; 1С его не использует ⚠.

### 10.4. Регистрация в кластере 1С

- Если в указанной базе данных уже есть ИБ 1С, устанавливается связь с ней [ИТС-КС разд. 5.2.7.1; ИТС-адм разд. 5.2.1.3.7]; «Создать базу данных в случае её отсутствия» не нужен.
- **«Установить блокировку регламентных заданий»** — обязательно: иначе задания запускаются сразу [ИТС-адм разд. 5.2.1.3.6] — обмены, почта, загрузка выписок от имени рабочей системы [практика].
- **Смещение дат** не меняется после создания [ИТС-мет 4055, 2010; ИТС-адм разд. 5.2.1.3.2] — указывайте как у оригинала (обычно 2000); поведение при несовпадении не описано ⚠.
- **Одну базу данных нельзя регистрировать в нескольких ИБ**: не работают блокировки ИБ и объектов, менеджер управляемых блокировок; возможна порча [ИТС-адм разд. 5.2.1.3.8].

```cmd
rac infobase create --cluster=<uuid кластера> --name=buh_1030 --dbms=MSSQLServer --db-server=SQL01 ^
    --db-name=buh_1030 --db-user=buh_1c --db-pwd=<пароль> --locale=ru_RU --date-offset=2000 ^
    --scheduled-jobs-deny=on --license-distribution=allow
```

Ключи — `../1c/03-…` (сверено там с `rac help` 8.3.1x); `--dbms=MSSQLServer` — уточнено 20.10.2026: так тип СУБД назван в описании `ibcmd` [ИТС-адм прил. 4, разд. 4.10.2; пример — разд. 7.4.17] и в таблице ключей `rac infobase` в `../1c/03-…`; для своей версии всё равно сверяйте с `rac help infobase`.

## 11. Страничное восстановление

- Для отдельных повреждённых страниц (823/824, контрольная сумма, разрыв), когда целую базу восстанавливать долго; подозрительные страницы — `msdb.dbo.suspect_pages` (до 1000 строк; `event_type` 1 — 823/824, 2 — контрольная сумма, 3 — разрыв, 4 — восстановлена, 5 — исправлена DBCC, 7 — освобождена DBCC) [MS Learn].
- Только `FULL`/`BULK_LOGGED` (в `BULK_LOGGED` «как правило, не работает» — перейти в `FULL`), только файловые группы чтения-записи; нельзя: журнал, GAM/SGAM/PFS, страница 0 файла, 1:9; онлайн — только Enterprise; много страниц — восстанавливать файл/базу; повреждённый некластерный индекс проще перестроить [MS Learn].

```sql
SELECT file_id, page_id, event_type, error_count, last_update_date FROM msdb.dbo.suspect_pages WHERE database_id = DB_ID(N'buh');
SELECT OBJECT_NAME(pi.object_id, pi.database_id) AS table_name, pi.index_id, pi.page_type_desc
FROM sys.dm_db_page_info(DB_ID(N'buh'), 1, 57, 'DETAILED') AS pi;            -- 2019+ [MS Learn]
USE master;
RESTORE DATABASE [buh] PAGE = '1:57, 1:202' FROM DISK = N'E:\Backup\buh\buh_FULL_20261019_010000.bak' WITH NORECOVERY;
RESTORE DATABASE [buh] FROM DISK = N'E:\Backup\buh\buh_DIFF_20261019_090000.bak' WITH NORECOVERY;   -- шаг «последняя разностная» [MS Learn]; нужен ли здесь тот же PAGE = … — в документации не показано ⚠, проверить на стенде
RESTORE LOG [buh] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_091500.trn' WITH NORECOVERY;   -- первая копия журнала после разностной … и все следующие по порядку
BACKUP  LOG [buh] TO DISK = N'E:\Backup\buh\buh_LOG_pagefix.trn' WITH INIT;
RESTORE LOG [buh] FROM DISK = N'E:\Backup\buh\buh_LOG_pagefix.trn' WITH RECOVERY;
-- Проверка: DBCC CHECKDB (N'buh') WITH NO_INFOMSGS, ALL_ERRORMSGS;  suspect_pages.event_type = 4  [MS Learn]
```

Таблицы 1С (`_Document123`…) сопоставляют объектам — `ПолучитьСтруктуруХраненияБазыДанных()` (`../its-metod/razmeshchenie-dannyh-tablicy-i-polya.md`). Повреждения и `REPAIR_*` — `mssql/08-…`.

## 12. Проверка копий

### 12.1. `RESTORE VERIFYONLY`

Проверяет [MS Learn]: набор полон и читается; некоторые поля заголовков страниц (номер страницы); контрольную сумму, если она есть; место на устройствах назначения (с `MOVE` — в новом месте). **Структуру данных не проверяет.**

- Без контрольной суммы копии восстановление не может надёжно проверить и суммы страниц — поэтому `BACKUP … WITH CHECKSUM` + `RESTORE VERIFYONLY … WITH CHECKSUM` (с `CHECKSUM` проверка падает, если сумм в копии нет — тоже сигнал) [MS Learn].
- У `VERIFYONLY` по умолчанию `CONTINUE_AFTER_ERROR` (у прочих `RESTORE` — `STOP_ON_ERROR`); `WITH LOADHISTORY` пишет набор в историю `msdb` (на другом сервере — в порядке создания копий, иначе мастер SSMS увидит разрыв LSN); нужно право `CREATE DATABASE` [MS Learn].

```sql
RESTORE VERIFYONLY FROM DISK = N'E:\Backup\buh\buh_FULL_20261019_010000.bak' WITH CHECKSUM;   -- «The backup set on file 1 is valid.»
```

### 12.2. Восстановление и `DBCC CHECKDB`

- Microsoft: стратегии восстановления нет, пока копии не восстановлены во всех комбинациях плана и восстановленная база не проверена `DBCC CHECKDB` [MS Learn]. 1С: восстановить первую автоматическую копию на резервном сервере и проверить [ИТС-мет 5904, 2019]; тестовое восстановление с замером времени [ИТС-мет 5899, 2016]. Для 1С — ещё и вход в копию (с блокировкой регламентных заданий, 10.4) [практика].

| Опция `DBCC CHECKDB` | Что даёт [MS Learn] |
|---|---|
| без опций | полная физическая и логическая проверка; периодически |
| `PHYSICAL_ONLY` | только физическая структура и распределение; быстро; для частых проверок продуктива; подразумевает `NO_INFOMSGS`, несовместима с `REPAIR_*` |
| `NO_INFOMSGS`, `ALL_ERRORMSGS` | без информационных сообщений; все ошибки (и так по умолчанию) |
| `DATA_PURITY` | допустимость значений; для баз со старых версий включается однократным успешным запуском |
| `EXTENDED_LOGICAL_CHECKS` | индексированные представления, XML- и пространственные индексы; дорого |
| `TABLOCK` | блокировки вместо снимка; быстрее, но меньше параллелизм и проверок |
| `MAXDOP = n` | с 2014 SP2 |

Проверка работает через внутренний снимок — разрежённые файлы `<файл>_MSSQL_DBCC<id>` рядом с данными; после аварийного выключения ОС их можно удалить, убедившись, что проверка не идёт [MS Learn]. `REPAIR_ALLOW_DATA_LOSS` — крайняя мера, Microsoft всегда предпочитает восстановление из исправной копии; ремонт удаляет строки и страницы без учёта связей таблиц [MS Learn] — для 1С затем «Тестирование и исправление» [ИТС-адм разд. 6.10; практика]. Подробно — `mssql/08-…`.

### 12.3. Автоматическая тестовая проверка (T-SQL)

```sql
-- Последнюю полную копию buh — в buh_verify, проверить, удалить (sysadmin; тестовый сервер или нерабочее время) [практика]
USE master;
DECLARE @file nvarchar(400);
SELECT TOP (1) @file = bmf.physical_device_name
FROM msdb.dbo.backupset AS bs JOIN msdb.dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id
WHERE bs.database_name = N'buh' AND bs.type = 'D' AND bmf.device_type = 2
ORDER BY bs.backup_finish_date DESC;            -- на тестовом сервере истории нет — задайте @file вручную
IF DB_ID(N'buh_verify') IS NOT NULL ALTER DATABASE [buh_verify] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
RESTORE DATABASE [buh_verify] FROM DISK = @file
  WITH MOVE N'buh' TO N'D:\MSSQL\Verify\buh_verify.mdf', MOVE N'buh_log' TO N'L:\MSSQL\Verify\buh_verify_log.ldf',
       REPLACE, CHECKSUM, STATS = 10;           -- REPLACE — только для остатка прошлого прогона: ПРОВЕРЬТЕ ИМЯ БАЗЫ
DBCC CHECKDB (N'buh_verify') WITH NO_INFOMSGS, ALL_ERRORMSGS;
DROP DATABASE [buh_verify];                     -- ⚠ удаляет только тестовую копию
```

Шаг задания агента «с ошибкой» = сигнал; длительность шагов = ваше RTO. Готовая альтернатива — `Test-DbaLastBackup` (14.4) [сторонний].

## 13. История копий в `msdb`

| Таблица `msdb.dbo.…` | Что хранит [MS Learn] |
|---|---|
| `backupset` | тип (`D` база, `I` разностная, `L` журнал, `F`/`G` файловые, `P`/`Q` частичные), времена, LSN, `backup_size`, `compressed_backup_size`, `is_copy_only`, `has_backup_checksums`, `is_damaged`, `is_snapshot`, `begins_log_chain`, `recovery_model`, `user_name`, `compression_algorithm` (2022+), `last_valid_restore_time`; для VSS `backup_size` оценочный |
| `backupmediafamily` | `physical_device_name`, `device_type` (2/5/7/9), `family_sequence_number`, `mirror` |
| `backupmediaset`, `backupfile`, `backupfilegroup` | наборы носителей, файлы и группы в копии |
| `restorehistory` | `restore_date`, `destination_database_name`, `user_name`, `restore_type` (`D`, `F`, `G`, `I`, `L`, `V`), `replace`, `recovery`, `stop_at` |

```sql
-- Свежесть копий всех баз (сигнал: полной > 1 сут., журнала > 1 ч в FULL) [практика]
SELECT d.name, d.recovery_model_desc,
       MAX(CASE WHEN b.type = 'D' AND b.is_copy_only = 0 THEN b.backup_finish_date END) AS last_full,
       MAX(CASE WHEN b.type = 'I' THEN b.backup_finish_date END) AS last_diff,
       MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END) AS last_log
FROM sys.databases AS d LEFT JOIN msdb.dbo.backupset AS b ON b.database_name = d.name
WHERE d.name <> N'tempdb' GROUP BY d.name, d.recovery_model_desc ORDER BY d.name;

-- Последние копии базы [практика; колонки — MS Learn]
SELECT TOP (30) bs.type, bs.backup_start_date, bs.backup_finish_date, bs.is_copy_only, bs.has_backup_checksums,
       bs.is_damaged, bs.is_snapshot, CAST(bs.compressed_backup_size / 1048576.0 AS decimal(18,1)) AS size_mb,
       bs.user_name, bmf.device_type, bmf.physical_device_name
FROM msdb.dbo.backupset AS bs JOIN msdb.dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id
WHERE bs.database_name = N'buh' ORDER BY bs.backup_finish_date DESC;

-- История восстановлений [MS Learn]
SELECT TOP (20) rh.restore_date, rh.destination_database_name, rh.user_name, rh.restore_type, rh.replace, rh.stop_at,
       bs.database_name AS source_db, bs.backup_finish_date
FROM msdb.dbo.restorehistory AS rh JOIN msdb.dbo.backupset AS bs ON bs.backup_set_id = rh.backup_set_id
ORDER BY rh.restore_date DESC;
```

История растёт — Microsoft рекомендует периодически `sp_delete_backuphistory` (из `msdb`; файлы копий не удаляются) [MS Learn]; у Ola Hallengren для этого отдельное задание [сторонний]. Саму `msdb` копируйте после изменений [MS Learn].

```sql
USE msdb;
DECLARE @d datetime = DATEADD(DAY, -90, GETDATE());
EXECUTE dbo.sp_delete_backuphistory @oldest_date = @d;     -- права по умолчанию — sysadmin ⚠
```

## 14. Автоматизация

### 14.1. SQL Server Agent: задания T-SQL

```sql
USE msdb;   -- sysadmin
-- Копия журнала каждые 15 минут
EXEC dbo.sp_add_job @job_name = N'1C buh - LOG', @owner_login_name = N'sa',     -- служебный sysadmin, не личный логин [практика]
     @notify_level_eventlog = 2, @notify_level_email = 2, @notify_email_operator_name = N'DBA';   -- 2 = при ошибке; оператор — mssql/03
EXEC dbo.sp_add_jobstep @job_name = N'1C buh - LOG', @step_name = N'BACKUP LOG', @subsystem = N'TSQL',
     @database_name = N'master', @on_fail_action = 2,
     @command = N'DECLARE @f nvarchar(400) = N''E:\Backup\buh\buh_LOG_'' + FORMAT(SYSDATETIME(), N''yyyyMMdd_HHmmss'') + N''.trn'';
BACKUP LOG [buh] TO DISK = @f WITH CHECKSUM, COMPRESSION, INIT;';
EXEC dbo.sp_add_jobschedule @job_name = N'1C buh - LOG', @name = N'every 15 min',
     @freq_type = 4, @freq_interval = 1, @freq_subday_type = 4, @freq_subday_interval = 15, @active_start_time = 0;
EXEC dbo.sp_add_jobserver @job_name = N'1C buh - LOG', @server_name = N'(LOCAL)';
-- Полная ежедневно в 01:00 с проверкой файла
EXEC dbo.sp_add_job @job_name = N'1C buh - FULL', @owner_login_name = N'sa', @notify_level_email = 2, @notify_email_operator_name = N'DBA';
EXEC dbo.sp_add_jobstep @job_name = N'1C buh - FULL', @step_name = N'BACKUP DATABASE', @subsystem = N'TSQL', @database_name = N'master',
     @command = N'DECLARE @f nvarchar(400) = N''E:\Backup\buh\buh_FULL_'' + FORMAT(SYSDATETIME(), N''yyyyMMdd_HHmmss'') + N''.bak'';
BACKUP DATABASE [buh] TO DISK = @f WITH CHECKSUM, COMPRESSION, INIT;
RESTORE VERIFYONLY FROM DISK = @f WITH CHECKSUM;';
EXEC dbo.sp_add_jobschedule @job_name = N'1C buh - FULL', @name = N'daily 01:00',
     @freq_type = 4, @freq_interval = 1, @freq_subday_type = 1, @active_start_time = 10000;    -- HHmmss
EXEC dbo.sp_add_jobserver @job_name = N'1C buh - FULL', @server_name = N'(LOCAL)';
-- Проверка: EXEC dbo.sp_start_job @job_name = N'1C buh - FULL'; история задания в SSMS; строка в msdb.dbo.backupset
```

Значения (`@freq_type` 4 — ежедневно; `@freq_subday_type` 1 — в указанное время, 4 — минуты, 8 — часы; `@active_start_time` — `HHmmss`; `@on_fail_action` 2 — завершить с ошибкой; `@server_name` по умолчанию `(LOCAL)`; `@notify_level_*` 2 — при ошибке) — [MS Learn]; `sp_start_job @job_name = …` — подтверждено 20.10.2026 (MS Learn; чужие задания запускают `SQLAgentOperatorRole` и `sysadmin`). 1С: Database Mail, операторы, оповещение при ошибках [ИТС-мет 5904, 2019] (`mssql/03-…`). Для многих баз — одна процедура с перебором `sys.databases` или Ola Hallengren [практика].

### 14.2. Планы обслуживания

- План — пакет SSIS, запускаемый заданием агента: копии (полные, разностные, журнал, с хранением), проверка целостности, индексы, статистика, очистка; результаты — текстовый отчёт или `msdb.dbo.sysmaintplan_log`/`sysmaintplan_logdetail`, просмотр — **Maintenance Plans → View History** [MS Learn; ИТС-мет 5837, 2022].
- **Maintenance Cleanup Task** удаляет файлы **только локально**; подкаталоги — при **Include first-level subfolders**; расширение без точки (`BAK`, `TRN`) [MS Learn].
- Документация относит задачу копирования планов к средствам, не передающим `CHECKSUM`, — для них `backup checksum default` [MS Learn] (флажок контрольной суммы в новых SSMS ⚠).
- В Express нет агента — нет и планов [MS Learn]. 1С о копиях на MS SQL отдельной статьи о планах не даёт: допустимы любые специализированные средства [ИТС-мет 2922, 2008].

### 14.3. Ola Hallengren `DatabaseBackup` [сторонний]

- Бесплатно (MIT); `MaintenanceSolution.sql` — SQL Server 2017, 2019, 2022, 2025 и Azure SQL MI; процедуры `DatabaseBackup`, `DatabaseIntegrityCheck`, `IndexOptimize`, `CommandExecute`, таблица `CommandLog` (версия `DatabaseBackup.sql` от 2026-09-12). Для 2016 — уточнено 20.10.2026 по FAQ: текущий скрипт её не поддерживает, для SQL Server 2008–2016 на сайте отдельно выложена последняя совместимая версия.
- Задания: `DatabaseBackup - SYSTEM_DATABASES - FULL`, `DatabaseBackup - USER_DATABASES - FULL`/`- DIFF`/`- LOG`, `DatabaseIntegrityCheck - …`, `IndexOptimize - USER_DATABASES`, `sp_delete_backuphistory`, `sp_purge_jobhistory`, `CommandLog Cleanup`, `Output File Cleanup` — **без расписаний**: по FAQ сначала запустить вручную, проверить, затем назначить расписания. Переменные скрипта: `@CreateJobs`, `@BackupDirectory`, `@CleanupTime`, `@OutputFileDirectory`, `@LogToTable` (умолчание `'Y'`).

| Параметр `dbo.DatabaseBackup` | Значения и смысл |
|---|---|
| `@Databases` | `USER_DATABASES`, `SYSTEM_DATABASES`, `ALL_DATABASES`, `AVAILABILITY_GROUP_DATABASES`, имена, `%шаблон%`, `-исключение` |
| `@Directory` | каталог/UNC, несколько через запятую — полоса; внутри — «сервер\экземпляр\база\тип» |
| `@BackupType` | `FULL`, `DIFF`, `LOG` |
| `@Verify` | `Y`/`N` (умолчание `N`) — `RESTORE VERIFYONLY` |
| `@Checksum`, `@Compress` | `Y`/`N`/`NULL` (`NULL` — умолчание сервера); `@CompressionAlgorithm` (`MS_XPRESS`, `QAT_DEFLATE`, `ZSTD`), `@CompressionLevel` |
| `@CopyOnly` | `COPY_ONLY` |
| `@CleanupTime`, `@CleanupMode` | удалять копии старше N часов, после (`AFTER_BACKUP`, умолчание) или до копии; удаляет только после успешной копии и проверки; копии журнала новее последней полной/разностной не удаляет; через `xp_delete_file`; для URL не работает |
| `@ChangeBackupType` | `Y` — если разностную/журнал сделать нельзя (проверка `differential_base_lsn`, `last_log_backup_lsn`), сделать полную вместо пропуска |
| `@NumberOfFiles`, `@BufferCount`, `@MaxTransferSize` | полоса и буферы |
| `@Encrypt`, `@EncryptionAlgorithm`, `@ServerCertificate`; `@URL`, `@Credential` | шифрование; копии в URL |
| `@LogToTable`, `@Execute` | журнал в `dbo.CommandLog`; `N` — только напечатать команды |

```sql
EXECUTE dbo.DatabaseBackup @Databases = 'USER_DATABASES', @Directory = N'\\backup01\sql$', @BackupType = 'FULL',
    @Verify = 'Y', @Checksum = 'Y', @Compress = 'Y', @CleanupTime = 336, @LogToTable = 'Y';      -- хранить 14 суток
EXECUTE dbo.DatabaseBackup @Databases = 'USER_DATABASES', @Directory = N'\\backup01\sql$', @BackupType = 'LOG',
    @Checksum = 'Y', @Compress = 'Y', @ChangeBackupType = 'Y', @CleanupTime = 336, @LogToTable = 'Y';
-- Проверка: SELECT TOP (20) * FROM dbo.CommandLog ORDER BY ID DESC;   (в базе, где установлено решение)
```

`xp_delete_file` — недокументированная процедура ⚠. Express: процедуры ставят тем же скриптом, а запускают `sqlcmd` из планировщика Windows (FAQ) [сторонний].

### 14.4. PowerShell: SqlServer и dbatools

```powershell
Import-Module SqlServer        # модуль Microsoft; установка: Install-Module -Name SqlServer (из PowerShell Gallery, от администратора) — подтверждено 20.10.2026 (MS Learn)
Backup-SqlDatabase -ServerInstance 'SQL01' -Database 'buh' -BackupFile 'E:\Backup\buh\buh_COPY_20261020.bak' -CopyOnly -Checksum -CompressionOption On
Backup-SqlDatabase -ServerInstance 'SQL01' -Database 'buh' -BackupAction Log -BackupFile 'E:\Backup\buh\buh_LOG_20261020.trn'
$rd = New-Object Microsoft.SqlServer.Management.Smo.RelocateFile('buh',     'D:\MSSQL\Data\buh_test.mdf')
$rl = New-Object Microsoft.SqlServer.Management.Smo.RelocateFile('buh_log', 'L:\MSSQL\Log\buh_test_log.ldf')
Restore-SqlDatabase -ServerInstance 'SQL01' -Database 'buh_test' -BackupFile 'E:\Backup\buh\buh_COPY_20261020.bak' -RelocateFile @($rd, $rl)
# журнал до момента: -RestoreAction Log -ToPointInTime "Oct 19, 2026 10:30 AM" -NoRecovery
```

`-CopyOnly`, `-Incremental` (= разностная), `-BackupAction`, `-Checksum`, `-CompressionOption`, `-RelocateFile`, `-ReplaceDatabase`, `-RestoreAction`, `-ToPointInTime`, `-NoRecovery` — [MS Learn]; значения `-CompressionOption` — уточнено 20.10.2026 (MS Learn, Backup-SqlDatabase): `Default`, `On`, `Off`. `-Encrypt` (`Mandatory`/`Optional`/`Strict`) появился в версии 22 модуля с умолчанием `Optional`; в 23+ умолчание — `Mandatory` (старые скрипты с самоподписанным сертификатом начнут падать; `-TrustServerCertificate`) [MS Learn].

```powershell
# dbatools [сторонний, по исходникам GitHub]
Backup-DbaDatabase  -SqlInstance SQL01 -Database buh -Type Full -CopyOnly -CompressBackup -Checksum -Path '\\backup01\sql$\SQL01\buh'
Restore-DbaDatabase -SqlInstance SQL01 -Path '\\backup01\sql$\SQL01\buh' -DatabaseName buh_1030 -ReplaceDbNameInFile `
    -RestoreTime '2026-10-19 10:30' -OutputScriptOnly          # только скрипт плана восстановления
Test-DbaLastBackup  -SqlInstance SQL01 -Database buh -Destination SQL-TEST -Prefix 'verify-'
```

`Test-DbaLastBackup` восстанавливает последние копии под именем `dbatools-testrestore-<база>` (или с `-Prefix`), переименовывает файлы, выполняет `DBCC CHECKDB` и удаляет базу; ключи `-VerifyOnly`, `-NoCheck`, `-NoDrop`, `-MaxSize`, `-CopyFile`, `-IgnoreLogBackup`, `-IgnoreDiffBackup` [сторонний]. Умолчания шифрования подключений dbatools 2.x не сверялись ⚠.

### 14.5. Express: планировщик Windows

В Express нет агента; база — до 10 ГБ (до 2022) или 50 ГБ (2025) [MS Learn] — для рабочих баз 1С обычно мало (`mssql/01-…`).

```powershell
# Полная копия ежедневно в 01:00 от имени SYSTEM [практика]; NT AUTHORITY\SYSTEM нужен логин с db_backupoperator ⚠ (или gMSA)
$a = New-ScheduledTaskAction -Execute 'sqlcmd.exe' -Argument '-S .\SQLEXPRESS -E -b -C -i C:\Scripts\backup_buh_full.sql -o C:\Scripts\backup_buh_full.log'
$t = New-ScheduledTaskTrigger -Daily -At 01:00
Register-ScheduledTask -TaskName '1C buh FULL backup' -Action $a -Trigger $t -User 'NT AUTHORITY\SYSTEM' -RunLevel Highest
Start-ScheduledTask -TaskName '1C buh FULL backup'
Get-Content C:\Scripts\backup_buh_full.log; (Get-ScheduledTaskInfo -TaskName '1C buh FULL backup').LastTaskResult   # 0 = успех
```

`sqlcmd`: `-b` — при ошибке с серьёзностью > 10 `ERRORLEVEL` 1; `-E` — доверенное подключение; `-C` — доверять сертификату без проверки; `-N m` (обязательное шифрование) — **умолчание** ODBC-варианта `sqlcmd` в SQL Server 2025, в 2022 и раньше было `-N o`; у `sqlcmd` (Go) без `-N` и `-C` сертификат сервера не проверяется [MS Learn]. Какой вариант установлен — `sqlcmd-installed-version` [MS Learn]. `-C` — осознанное ослабление проверки для локального подключения [практика].

### 14.6. Удаление старых копий

Удалять только копии старше **самой старой хранимой полной** — иначе пропадут копии журнала, нужные для восстановления от неё; разностные старше неё бесполезны [практика].

```powershell
$root = 'E:\Backup\buh'; $keepDays = 14     # [практика]; сначала прогон с -WhatIf
$oldestKeptFull = Get-ChildItem $root -Filter 'buh_FULL_*.bak' | Where-Object LastWriteTime -ge (Get-Date).AddDays(-$keepDays) |
    Sort-Object LastWriteTime | Select-Object -First 1
if (-not $oldestKeptFull) { throw 'В окне хранения нет полной копии — ничего не удаляю' }
Get-ChildItem $root -File | Where-Object { $_.Extension -in '.bak', '.trn' -and $_.LastWriteTime -lt $oldestKeptFull.LastWriteTime } |
    Remove-Item -WhatIf          # ⚠ убрать -WhatIf после проверки списка: удаление безвозвратно
```

Контроль [практика]: задание «свежесть копий» (запрос 13, `THROW` при просрочке) с оповещением; оповещения агента на 9002 и ошибки 17–25 — `mssql/06-…`; тестовое восстановление (12.3) раз в месяц/квартал с записью времени [ИТС-мет 5899, 2016].

## 15. VSS, `wbadmin` и копирование виртуальных машин

### 15.1. SQL Writer

- Позволяет программам копирования Windows копировать файлы баз через VSS при работающем SQL Server; без него остаются только собственные копии SQL Server [MS Learn].
- Работает под **Local System**, подключается логином `NT Service\SQLWriter` с **sysadmin** (замораживает ввод-вывод экземпляра на время снимка); отключённая служба ломает средства на основе снимков VSS или даёт несогласованные копии; если кроме T-SQL-копий ничего не нужно — службу можно отключить, логин удалить [MS Learn].
- Поддерживает полные, разностные, `COPY_ONLY`, восстановление с переносом и переименованием; **не поддерживает копии журнала**, файловые копии, страничное восстановление; на Linux его нет [MS Learn].
- Полная VSS-копия (не copy) после «Backup Complete» фиксируется **как база разностных копий** [MS Learn].
- В 2025 SQL Writer подключается по TDS 8.0 с `Encrypt=Mandatory` и `TrustServerCertificate=No` по умолчанию — уточнено 20.10.2026 (MS Learn, `sql-writer-service`): нужен действительный сертификат сервера; для самоподписанного документация допускает `TrustServerCertificate=Yes` (где это задаётся — не описано ⚠); при `Encrypt=Strict` сертификат проверяется всегда. Неудачные VDI/VSS-копии — ошибка 18210 в журнале ошибок [MS Learn].

### 15.2. `wbadmin`

- С параметрами `wbadmin start backup` делает копию **copy** (`-vssCopy` — умолчание): история файлов не обновляется, разностные копии других программ не затрагиваются [MS Learn].
- `-vssFull` обновляет историю, журналы предыдущих копий могут быть обрезаны; Microsoft предупреждает не использовать его, если приложения копирует другая программа [MS Learn] — на сервере SQL Server только `-vssCopy` [`../1c-windows/06-…`].

```cmd
wbadmin start backup -backupTarget:\\backup01\os$ -allCritical -systemState -vssCopy -quiet
wbadmin get versions
```

### 15.3. Программы копирования ВМ и СРК

- «Согласованные с приложением» копии ВМ вызывают VSS в гостевой ОС; при полной (не copy) копии в `msdb` появляется полная копия на виртуальном устройстве (`device_type = 7`), база разностных сдвигается [MS Learn — механизм; практика — проявление]; проверка — 6.3.
- Выбор [практика] ⚠ (режимы и названия у продуктов свои): (1) копии баз делает только SQL Server, в программе ВМ для SQL выключена обработка приложений или включён copy-only; (2) копии делает только программа ВМ/СРК с поддержкой копий журнала, свои задания `BACKUP` отключены; (3) не смешивать без понимания, где лежат все звенья. «Усечение журнала после копии» в программе ВМ ломает вашу цепочку ⚠.

### 15.4. Снимковые копии T-SQL (2022+)

`ALTER DATABASE … SET SUSPEND_FOR_SNAPSHOT_BACKUP = ON` → снимок СХД → `BACKUP DATABASE … TO DISK = '…bkm' WITH METADATA_ONLY` (синоним `SNAPSHOT`; `BACKUP GROUP`, `BACKUP SERVER`); при восстановлении файлы копируют из снимка, затем `RESTORE` по файлу метаданных [MS Learn]. Для 1С — только очень крупные базы на СХД со снимками [практика].

## 16. 1С: `.dt`, журнал регистрации, хранилище двоичных данных

### 16.1. `.dt` — для переноса, не для копий

- Назначение — образ ИБ независимо от способа хранения и перенос между СУБД и вариантами; в выгрузку входят данные хранилищ двоичных данных (клиент-серверный вариант); перед выгрузкой — тестирование и исправление [ИТС-адм разд. 6.7; ИТС-КС разд. 5.1.2].
- Когда нужен [практика, если не указано]: перенос MS SQL ↔ PostgreSQL (или `ibcmd infobase replicate` — только на Windows, `ibcmd` на Linux с MS SQL не работает [ИТС-адм разд. 7.2, 7.4.17]); смена смещения дат 0 → 2000 [ИТС-адм разд. 5.2.1.3.2; ИТС-мет 4055, 2010]; передача партнёру; **возврат на старую версию SQL Server**, куда копия не восстановится (3169) [MS Learn — 3169].
- Загрузка в MS SQL [ИТС-адм разд. 6.8]: ИБ полностью заменяется; место под временные файлы ≈ объёму развёрнутой ИБ — **на сервере 1С**; база может быть в разы больше `.dt`; модель «Простая»/«С неполным протоколированием» на время загрузки, **перед сменой модели — копия**. После — `FULL` и полная копия [практика].
- Версии: в 8.3 загружается `.dt` 8.1/8.2, в 8.5 — 8.1/8.2/8.3; `.dt` 8.3.1+ не загружается в версии младше 8.3.1 (кроме совместимости 8.2.16) [ИТС-адм разд. 6.8; `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`].

```cmd
:: ibcmd на Windows (MS SQL); к базе не должно быть подключений, в том числе кластера [ИТС-адм разд. 7.3.7, 7.4.6]
ibcmd infobase dump --dbms=mssqlserver --database-server=SQL01 --database-user=buh_1c --database-password=<пароль> ^
    --database-name=buh --data="D:\ss-data\buh-data" buh.dt
ibcmd infobase create --dbms=mssqlserver --database-server=SQL01 --db-user=buh_1c --database-password=<пароль> ^
    --database-name=buh_new --data="D:\ss-data\buh_new-data" --create-database --restore=buh.dt
```

Автономный сервер и `ibcmd` нельзя направлять на ИБ, работающую под кластером [ИТС-адм разд. 7.2]; `--db-user` и `--database-user` — уточнено 20.10.2026: это синонимы (`--database-user=<name> --db-user=<name>` в таблице общих параметров `ibcmd`) [ИТС-адм прил. 4, разд. 4.10.2].

### 16.2. Журнал регистрации

- В базе не хранится, при выгрузке/загрузке не сохраняется; средствами СУБД не копируется [ИТС-адм разд. 6.13.1; ИТС-КС разд. 5.1.1].
- Где: `<каталог данных сервера>\reg_<порт>\<uuid ИБ>\1Cv8Log` (каталог сервиса может быть переназначен, КОРП); каталог данных сервера на Windows при установке «как сервис» — `<каталог установки>\srvinfo` (ключ `/d` агента); файлы `1Cv8.lgf`, `*.lgp`, `*.lgx`; формат журнала хранится в ИБ [ИТС-КС разд. 2.2.3.2, 2.2.13; ИТС-адм разд. 6.13.1, 6.13.2].
- **Восстанавливать — при остановленном кластере** [ИТС-адм разд. 6.9.2]. uuid ИБ — `rac infobase summary list` (`../1c/03-…`) или `1CV8Clst.lst` [ИТС-адм прил. 3, разд. 3.7].
- Копирование «на ходу» ⚠ [практика]: `.lgp` открыты на запись — надёжнее через VSS (`wbadmin start backup -include:<каталог> -vssCopy`); `robocopy` годится для просмотра истории с риском потерять последние записи. Копия ИБ под новым именем получает новый uuid — журнал оригинала при необходимости копируют в её каталог при остановленном кластере ⚠.

### 16.3. Хранилище двоичных данных (КОРП)

- Копируется отдельно [ИТС-КС разд. 5.1.1, 5.4.5]: `СоздатьПолнуюРезервнуюКопию()` (`.sbf`), `СоздатьДифференциальнуюРезервнуюКопию()` (`.sbd`, нужна полная), `ЗагрузитьПолнуюРезервнуюКопию()`, `ЗагрузитьДифференциальнуюРезервнуюКопию()` (оба файла), `ПолучитьУниверсальнуюДатуСозданияРезервнойКопии()`; параметр `УниверсальнаяДатаДоКоторойВыполнятьОчистку` — очистка и сжатие после копии; интерактивно — «Управление хранилищем двоичных данных» [ИТС-адм разд. 6.9.2].
- При режимах `РазмещениеКопийДанныхВХранилищеПриЗаписиВБазуДанных`/`…ПриЧтенииИзБазыДанных` минимально достаточно копии ИБ, но копировать хранилище всё равно рекомендуется; при восстановлении снимаются все «пометки на удаление»; хранилище S3 — средствами провайдера [ИТС-КС разд. 5.4.5].
- Порядок восстановления: база → журнал регистрации → хранилище [ИТС-адм разд. 6.9.2].

Прочее — таблица 1.2; индексы полнотекстового поиска (`…\reg_<порт>\<uuid ИБ>\1Cv8FTxt…` [ИТС-КС разд. 2.2.3.2]) можно перестроить, а не копировать ⚠ [практика].

### 16.4. Методички ИТС: что актуально

| Статья | Суть | На 2026 |
|---|---|---|
| 2922, 28.10.2008 | `.dt` неудобна для копий; файловая база — копия `1Cv8.1CD` без подключений; клиент-серверная — средствами СУБД без однопользовательского режима; копия СУБД точнее выгрузки; можно специализированные программы | **актуальна**, совпадает с документацией 8.3.27 [ИТС-КС разд. 5.1.1; ИТС-адм разд. 6.7] |
| 2378, 11.04.2008 | `SP_ADDUMPDEVICE` с UNC и доменная учётная запись SQL Server; копии только на локальном диске снижают надёжность | **принцип актуален, механизм устарел**: UNC в `TO DISK`, права учётной записи службы (`ДОМЕН\компьютер$`) [MS Learn] |
| 2373, 11.04.2008 | `BACKUP LOG … WITH TRUNCATE_ONLY` + `DBCC SHRINKFILE` | **устарела** — раздел 7.5 [MS Learn] |
| 5904, 15.07.2019 | модель — по политике; журнал на период между `BACKUP LOG`; исключить файлы баз из файлового копирования; Database Mail и операторы; после первой копии — восстановить и проверить | **актуальна**; IFI для журнала уточнено для 2022 |
| 5899, 12.05.2016 | тестовое восстановление с замером | **актуальна** |
| 6008, 09.11.2023 | IFI не работает для журнала | с 2022 — приросты до 64 МБ с IFI [MS Learn] |

## 17. Сценарии

### 17.1. «Восстановить вчерашнюю копию рядом»

Права: sysadmin/dbcreator, администратор кластера 1С.

1. Найти копию (запросы раздела 13; для точного момента — 9.2). Проверить место: `Size` в `RESTORE FILELISTONLY` и свободное место томов:

```sql
SELECT DISTINCT vs.volume_mount_point, vs.available_bytes / 1073741824 AS free_gb
FROM sys.master_files AS mf CROSS APPLY sys.dm_os_volume_stats(mf.database_id, mf.file_id) AS vs;   -- [MS Learn]
```

2. Восстановить:

```sql
USE master;
RESTORE FILELISTONLY FROM DISK = N'E:\Backup\buh\buh_FULL_20261019_010000.bak';
RESTORE DATABASE [buh_20261019] FROM DISK = N'E:\Backup\buh\buh_FULL_20261019_010000.bak'
WITH MOVE N'buh' TO N'D:\MSSQL\Data\buh_20261019.mdf', MOVE N'buh_log' TO N'L:\MSSQL\Log\buh_20261019_log.ldf',
     CHECKSUM, STATS = 10, RECOVERY;
ALTER DATABASE [buh_20261019] SET RECOVERY SIMPLE;                  -- копии журнала копии не нужны [практика]
SELECT name, state_desc, recovery_model_desc, SUSER_SNAME(owner_sid) AS owner FROM sys.databases WHERE name = N'buh_20261019';
```

3. Зарегистрировать в кластере новой ИБ **с блокировкой регламентных заданий** и тем же смещением дат (10.4); на том же сервере логин 1С сопоставится по SID без доработок [практика].
4. Пользователь сравнивает и переносит данные средствами 1С; регламентные задания на копии не включать [практика].
5. Уборка (⚠ разрушающее, проверьте имя): `rac infobase drop …` (только регистрация, `../1c/03-…`), затем `DROP DATABASE [buh_20261019];`.

### 17.2. «Вернуть рабочую базу на момент перед ошибкой» (на месте)

⚠ **Разрушающая операция**: работа всех пользователей после момента пропадёт. Сначала рассмотрите 17.1 + перенос данных; решение — с руководителем; простой — по замеру тестового восстановления.

1. 1С: блокировка сеансов и регламентных заданий, завершение сеансов (8.4).
2. SQL Server (sysadmin), `FULL`:

```sql
USE master;
ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC OFF;            -- иначе SINGLE_USER может не получиться
ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
BACKUP LOG [buh] TO DISK = N'E:\Backup\buh\buh_TAIL_20261020_1105.trn' WITH NORECOVERY, CHECKSUM, INIT;   -- хвост; база → RESTORING
RESTORE DATABASE [buh] FROM DISK = N'E:\Backup\buh\buh_FULL_20261019_010000.bak' WITH NORECOVERY, STATS = 10;
RESTORE DATABASE [buh] FROM DISK = N'E:\Backup\buh\buh_DIFF_20261019_130000.bak' WITH NORECOVERY;
-- … копии журнала 13:15 и 13:30 — так же WITH NORECOVERY, STOPAT = N'2026-10-19T14:05:00', по порядку (все звенья после разностной, без пропусков)
RESTORE LOG [buh] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_134500.trn' WITH NORECOVERY, STOPAT = N'2026-10-19T14:05:00';
RESTORE LOG [buh] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_140000.trn' WITH NORECOVERY, STOPAT = N'2026-10-19T14:05:00';
RESTORE LOG [buh] FROM DISK = N'E:\Backup\buh\buh_LOG_20261019_141500.trn' WITH NORECOVERY, STOPAT = N'2026-10-19T14:05:00';
RESTORE DATABASE [buh] WITH RECOVERY;
ALTER DATABASE [buh] SET MULTI_USER;                                   -- если режим пришёл из копии [практика]
SELECT name, state_desc, user_access_desc, recovery_model_desc, is_auto_update_stats_async_on FROM sys.databases WHERE name = N'buh';
```

   Хвост (`buh_TAIL_…`) позволяет повторить восстановление на другой момент, вплоть до точки сбоя [MS Learn]. После `RECOVERY` на 14:05 начата новая развилка — старые копии журнала после 14:05 к ней не применить [практика].
3. Сразу **новая полная копия** [практика].
4. Журнал регистрации на момент копии — при остановленном кластере; затем хранилище двоичных данных [ИТС-адм разд. 6.9.2].
5. 1С: `--sessions-deny=off --scheduled-jobs-deny=off`, проверить вход и регламентные задания.

В `SIMPLE`: шаги 1 и 2 до `SINGLE_USER`, затем `RESTORE DATABASE [buh] FROM DISK = … WITH REPLACE, STATS = 10;` — `REPLACE` здесь осознанно перезаписывает базу [MS Learn].

### 17.3. «Перенести базу на новый сервер» с минимальным простоем

Условия: SQL Server той же или новее версии (из поддерживаемых 1С — `mssql/01-…`), рабочие серверы 1С видят новый сервер (`mssql/02-…`), база в `FULL` с непрерывной цепочкой. Права — sysadmin на обоих серверах, администратор кластера.

**Заранее**: экземпляр настроен под 1С (память, параллелизм, `tempdb`, флаги трассировки, параметры сортировки как у старого — `mssql/02-…`), логины созданы **с теми же SID** (10.3). Восстановить полную, разностную и все копии журнала **с `NORECOVERY`** и догонять новыми копиями журнала из общей сетевой папки:

```sql
-- НОВЫЙ сервер SQL02
RESTORE DATABASE [buh] FROM DISK = N'\\backup01\sql$\SQL01\buh\buh_FULL_20261019_010000.bak'
WITH MOVE N'buh' TO N'D:\MSSQL\Data\buh.mdf', MOVE N'buh_log' TO N'L:\MSSQL\Log\buh_log.ldf', NORECOVERY, STATS = 10;
RESTORE DATABASE [buh] FROM DISK = N'\\backup01\sql$\SQL01\buh\buh_DIFF_20261019_130000.bak' WITH NORECOVERY;
RESTORE LOG [buh] FROM DISK = N'\\backup01\sql$\SQL01\buh\buh_LOG_20261019_131500.trn' WITH NORECOVERY;   -- … и далее по порядку
```

**Переключение**:

1. 1С: блокировка и завершение сеансов (8.4); отключить задание копий журнала на старом сервере.
2. Старый сервер — финальный хвост, база уходит в `RESTORING` (никто туда больше не запишет):

```sql
-- СТАРЫЙ сервер SQL01
ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC OFF;
ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
BACKUP LOG [buh] TO DISK = N'\\backup01\sql$\SQL01\buh\buh_TAIL_cutover.trn' WITH NORECOVERY, CHECKSUM, INIT;
```

3. Новый сервер — оставшиеся журналы и хвост, восстановление, параметры:

```sql
-- НОВЫЙ сервер SQL02
RESTORE LOG [buh] FROM DISK = N'\\backup01\sql$\SQL01\buh\buh_TAIL_cutover.trn' WITH NORECOVERY;
RESTORE DATABASE [buh] WITH RECOVERY;
ALTER DATABASE [buh] SET MULTI_USER;
ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC ON;         -- выключали перед хвостом; 1С рекомендует ON [ИТС-мет 5904]
SELECT SUSER_SNAME(owner_sid) AS owner, compatibility_level, recovery_model_desc FROM sys.databases WHERE name = N'buh';
-- ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];             -- если владельцем должен быть логин 1С (10.3)
-- USE [buh]; EXEC sp_updatestats;                                 -- при переносе на 2022 с более ранней версии [MS Learn]
```

4. 1С: сменить сервер баз данных ИБ (консоль или `rac infobase update … --db-server=SQL02` [`../1c/03-…`]), снять блокировки, проверить вход, проведение, регламентные задания.
5. Новый сервер: задания копий (полная — сразу), проверка первой копии восстановлением [ИТС-мет 5904, 2019].
6. **Откат** до начала работы пользователей: на старом `RESTORE DATABASE [buh] WITH RECOVERY;` — база выйдет в сеть на момент хвоста [MS Learn — восстановление без данных]; вернуть прежний сервер в 1С.
7. Уровень совместимости при переносе на новую версию сохраняется — уточнено 20.10.2026 (MS Learn, `restore-a-database-backup-using-ssms`, `alter-database-transact-sql-compatibility-level`): остаётся прежним, если не ниже минимально допустимого (уровень 90 поднимается до 100); менять ли его, решается отдельно (`mssql/07-…`).

Небольшая база проще: блокировка 1С → `COPY_ONLY` на старом → `RESTORE` на новом → шаги 4–5; старую базу — `READ_ONLY` или `OFFLINE`, чтобы туда не писали [практика].

### 17.4. Тестовая копия на SQL Server под Linux

Базы 1С на таком сервере обслуживают только рабочие серверы 1С на Windows [ИТС-КС разд. 2.3].

```bash
scp buh_COPY_20261020.bak admin@sqllinux01:/tmp/                                   # с Windows (WSL/Git Bash) [MS Learn]
sudo mkdir -p /var/opt/mssql/backup && sudo mv /tmp/buh_COPY_20261020.bak /var/opt/mssql/backup/
sudo chown mssql:mssql /var/opt/mssql/backup/buh_COPY_20261020.bak                 # [практика]
sqlcmd -S localhost -U sa -C -Q "RESTORE FILELISTONLY FROM DISK = '/var/opt/mssql/backup/buh_COPY_20261020.bak'"
sqlcmd -S localhost -U sa -C -Q "RESTORE DATABASE buh_test FROM DISK = '/var/opt/mssql/backup/buh_COPY_20261020.bak' WITH MOVE 'buh' TO '/var/opt/mssql/data/buh_test.mdf', MOVE 'buh_log' TO '/var/opt/mssql/data/buh_test_log.ldf', STATS = 10"
```

Без `MOVE` для дополнительных файлов восстановление ищет пути Windows и падает с 5133 [MS Learn].

### 17.5. Повреждение базы — кратко

Хвост журнала (`NO_TRUNCATE` или `CONTINUE_AFTER_ERROR`) → `DBCC CHECKDB` → несколько страниц — раздел 11, иначе восстановление до точки сбоя (9.3); ремонт `REPAIR_ALLOW_DATA_LOSS` — только без копий и после физических копий файлов `.mdf`/`.ndf`/`.ldf` [MS Learn], затем «Тестирование и исправление» в 1С [ИТС-адм разд. 6.10]. Подробно — `mssql/08-…`.

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| 4214 «BACKUP LOG cannot be performed because there is no current database backup» | база новая или переведена из `SIMPLE` без полной копии | полная копия [MS Learn] |
| 3201 «Cannot open backup device '\\…'. Operating system error 5 (Access is denied.)» | нет прав у **учётной записи службы**; буква диска вместо UNC; неверный путь | права `CORP\SQL01$` на папку и NTFS, только UNC (5.2) [MS Learn] |
| 3159 «The tail of the log … has not been backed up» | `FULL`, хвост не сохранён | `BACKUP LOG … WITH NORECOVERY`; `REPLACE` — осознанно [MS Learn] |
| 3101 ⚠ «Exclusive access could not be obtained because the database is in use» | подключены сеансы 1С, консоли, мониторинг | блокировка и завершение сеансов в 1С, `SINGLE_USER WITH ROLLBACK IMMEDIATE` (8.4) [ИТС-КС разд. 5.1.1; MS Learn] |
| `SINGLE_USER` включён, а войти нельзя («база уже открыта одним пользователем») ⚠ | подключение занял поток асинхронной статистики или рабочий процесс 1С | `AUTO_UPDATE_STATISTICS_ASYNC OFF` до `SINGLE_USER`, `ALTER LOGIN [buh_1c] DISABLE`, команды одной пачкой [MS Learn; практика] |
| Восстановились данные месячной давности | копии дописывались в один файл (`NOINIT`), взят `FILE = 1` | `RESTORE HEADERONLY` → `FILE = n`; впредь отдельный файл и `INIT` [MS Learn] |
| 3169 «… backed up on a server running version …. That version is incompatible …» | копия с более новой версии | та же или новее версия; на старую — `.dt` (16.1) [MS Learn] |
| 3156 «… Use WITH MOVE …», 5133 «Directory lookup … operating system error 2» | нет исходного пути; забыт `.ndf` | `FILELISTONLY` → `MOVE` для каждого файла [MS Learn] |
| Разностная не применяется к полной ⚠ | база разностной — другая полная (внеплановая без `COPY_ONLY` или VSS) | найти базу по `database_backup_lsn` = `checkpoint_lsn` (8.5); впредь `COPY_ONLY`, режим copy в программе ВМ [MS Learn] |
| Копия журнала «too early/too late» ⚠ | пропущено звено или нарушен порядок | проверка цепочки (6.3), порядок по `first_lsn` [MS Learn] |
| 9002 «The transaction log for database … is full» | нет копий журнала, длинная транзакция, CDC, кончилось место/`MAXSIZE` | `log_reuse_wait_desc` → 7.4 [MS Learn] |
| `DBCC SHRINKFILE` журнала не сжимает | активная часть в конце файла, усечение задержано | ещё копия журнала, устранить причину, повторить [MS Learn] |
| Скрипт из ИТС-мет 2373 с `TRUNCATE_ONLY` падает | параметр удалён | 7.5 [MS Learn] |
| Журнал базы 1С растёт, `REPLICATION` | механизм копий базы данных 1С «Версия2» (CDC), агент или задания CDC не работают | запустить агент/задания; при отказе от механизма — выключить в 1С [ИТС-разр гл. 26; MS Learn] |
| После программы копирования ВМ «сломались» разностные, в `msdb` полные на виртуальном устройстве | VSS-копии не в режиме copy | 6.3; режим copy или без обработки SQL (15.3) [MS Learn] |
| После `wbadmin … -vssFull` сломались копии другой программы | `-vssFull` обновляет историю | `-vssCopy` [MS Learn] |
| `VERIFYONLY` проходит, а восстановленная база с ошибками `CHECKDB` | VERIFYONLY не проверяет структуру; база была повреждена (`is_damaged`) или копия без сумм | регулярное тестовое восстановление + `CHECKDB` (12) [MS Learn] |
| 3043 при `BACKUP … WITH CHECKSUM` | повреждённая страница в базе | `DBCC CHECKDB`, страничное восстановление (11) [MS Learn] |
| 3183 «RESTORE detected an error on page … as read from the backup set» | повреждена копия | другая копия; `CONTINUE_AFTER_ERROR` — крайняя мера [MS Learn] |
| Восстановление долго «стоит» в начале или на 100 % | обнуление большого журнала, нет IFI; длинный откат | журнал разумного размера, IFI; журнал ошибок и `percent_complete` (8.6) [MS Learn; практика] |
| Копия сразу отправила письма/обмены | зарегистрирована без блокировки регламентных заданий | `--scheduled-jobs-deny=on`; разобрать, что ушло [ИТС-адм разд. 5.2.1.3.6] |
| На новом сервере 1С не входит в базу | нет логина/другой SID, «осиротевший» пользователь, владелец — администратор | `CREATE LOGIN … WITH SID`, `ALTER USER … WITH LOGIN`, `ALTER AUTHORIZATION` (10.3) [MS Learn] |
| Две ИБ на одной базе данных, странные блокировки | копию зарегистрировали на исходную базу | удалить лишнюю регистрацию [ИТС-адм разд. 5.2.1.3.8] |
| Задание `sqlcmd` (Express) перестало подключаться после обновления утилит | новый `sqlcmd` требует шифрования, сертификат самоподписанный | `-C` или доверенный сертификат [MS Learn] |
| От последней хранимой полной не восстановиться | удалены копии журнала после неё | правило 14.6 [практика] |
| Загрузка `.dt` идёт часами, журнал огромный | `FULL` во время загрузки | `SIMPLE`/`BULK_LOGGED` на время, затем `FULL` и полная копия [ИТС-адм разд. 6.8] |

## Быстрая шпаргалка

| Задача | Команда (sysadmin) |
|---|---|
| Модель, ожидание журнала, возможность копии журнала | `SELECT d.name, d.recovery_model_desc, d.log_reuse_wait_desc, drs.last_log_backup_lsn FROM sys.databases d JOIN sys.database_recovery_status drs ON drs.database_id = d.database_id;` |
| `FULL` и начало цепочки | `ALTER DATABASE [buh] SET RECOVERY FULL;` + полная копия |
| Полная / разностная / журнал | `BACKUP DATABASE [buh] TO DISK = @f WITH CHECKSUM, COMPRESSION, INIT;` / `… WITH DIFFERENTIAL, …` / `BACKUP LOG [buh] TO DISK = @f WITH CHECKSUM, COMPRESSION, INIT;` |
| Внеплановая | `… WITH COPY_ONLY, CHECKSUM, COMPRESSION, INIT;` |
| Хвост | `BACKUP LOG [buh] TO DISK = … WITH NORECOVERY, CHECKSUM, INIT;` (повреждена — `NO_TRUNCATE`/`CONTINUE_AFTER_ERROR`) |
| Умолчания экземпляра | `EXEC sp_configure 'backup checksum default', 1; EXEC sp_configure 'backup compression default', 1; RECONFIGURE;` |
| Что в файле / проверить файл | `RESTORE HEADERONLY FROM DISK = N'…';` и `RESTORE FILELISTONLY …` / `RESTORE VERIFYONLY FROM DISK = N'…' WITH CHECKSUM;` |
| Восстановить рядом | `RESTORE DATABASE [buh_copy] FROM DISK = N'…' WITH MOVE N'buh' TO N'…', MOVE N'buh_log' TO N'…', STATS = 10;` |
| На момент | все шаги `NORECOVERY`, в каждом `RESTORE LOG` — `STOPAT = N'2026-10-19T10:30:00'`, затем `RESTORE DATABASE [x] WITH RECOVERY;` |
| Монопольный доступ | `ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC OFF; ALTER DATABASE [buh] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;` |
| Страницы | `RESTORE DATABASE [buh] PAGE = '1:57' FROM DISK = … WITH NORECOVERY;` → журналы → новая копия журнала → `RESTORE LOG … WITH RECOVERY` |
| Ход операции | `SELECT command, percent_complete FROM sys.dm_exec_requests WHERE command LIKE 'BACKUP%' OR command LIKE 'RESTORE%';` |
| Журнал переполнен | `SELECT log_reuse_wait_desc FROM sys.databases WHERE name = N'buh'; DBCC SQLPERF(LOGSPACE); DBCC OPENTRAN(N'buh');` |
| Сжать журнал | после копии журнала: `USE [buh]; DBCC SHRINKFILE (N'buh_log', 8192);` |
| Логины и владелец | `ALTER USER [buh_1c] WITH LOGIN = [buh_1c];` / `CREATE LOGIN … WITH PASSWORD = N'…', SID = 0x…;` / `ALTER AUTHORIZATION ON DATABASE::[buh] TO [buh_1c];` |
| Целостность | `DBCC CHECKDB (N'buh') WITH NO_INFOMSGS, ALL_ERRORMSGS;` (часто — `PHYSICAL_ONLY`) |
| История | `EXEC msdb.dbo.sp_delete_backuphistory @oldest_date = '2026-07-20';` |
| 1С перед восстановлением / копия | `rac infobase update … --sessions-deny=on --scheduled-jobs-deny=on` / `rac infobase create … --dbms=MSSQLServer --date-offset=2000 --scheduled-jobs-deny=on` |
| ОС без вреда для SQL | `wbadmin start backup -backupTarget:\\backup01\os$ -allCritical -systemState -vssCopy -quiet` |

## Источники

Microsoft (learn.microsoft.com/sql/…; исходники `https://raw.githubusercontent.com/MicrosoftDocs/sql-docs/live/docs/<путь>.md`, прочитаны 20.10.2026):

- `t-sql/statements/`: `backup-transact-sql`, `restore-statements-transact-sql`, `restore-statements-arguments-transact-sql`, `restore-statements-verifyonly-…`, `…-headeronly-…`, `…-filelistonly-…`, `alter-database-transact-sql-set-options`, `alter-database-transact-sql-file-and-filegroup-options`, `alter-authorization-…`, `alter-login-…`; `t-sql/database-console-commands/`: `dbcc-checkdb-…`, `dbcc-shrinkfile-…`, `dbcc-sqlperf-…`, `dbcc-traceon-trace-flags-…`.
- `relational-databases/backup-restore/`: `recovery-models-sql-server`, `view-or-change-the-recovery-model-of-a-database-sql-server`, `back-up-and-restore-of-sql-server-databases`, `backup-overview-sql-server`, `restore-and-recovery-overview-sql-server`, `full-database-backups-…`, `differential-backups-…`, `transaction-log-backups-…`, `copy-only-backups-…`, `tail-log-backups-…`, `apply-transaction-log-backups-…`, `restore-a-sql-server-database-to-a-point-in-time-full-recovery-model`, `restore-database-to-point-of-failure-full-recovery`, `recover-a-database-without-restoring-data-transact-sql`, `restore-pages-…`, `restore-a-database-backup-using-ssms`, `backup-compression-…`, `enable-or-disable-backup-checksums-…`, `possible-media-errors-…`, `backup-encryption`, `backup-devices-…`, `media-sets-media-families-and-backup-sets-…`, `sql-server-backup-to-url`, `sql-server-backup-to-url-s3-compatible-object-storage`, `back-up-and-restore-of-system-databases-…`, `sql-server-vss-writer-backup-guide`, `create-a-transact-sql-snapshot-backup`.
- `relational-databases/logs/`: `the-transaction-log-sql-server`, `manage-the-size-of-the-transaction-log-file`, `troubleshoot-a-full-transaction-log-sql-server-error-9002`; `relational-databases/accelerated-database-recovery-concepts`; `relational-databases/databases/`: `copy-databases-with-backup-and-restore`, `manage-metadata-when-making-a-database-available-on-another-server`, `database-instant-file-initialization`, `set-a-database-to-single-user-mode`.
- Каталоги, DMV, `msdb`: `sys-databases`, `sys-database-recovery-status`, `sys-master-files`, `sys-dm-db-log-info`, `sys-dm-db-log-space-usage`, `sys-dm-tran-database-transactions`, `sys-dm-exec-requests`, `sys-dm-server-services`, `sys-dm-db-page-info`, `backupset`, `backupmediafamily`, `restorehistory`, `suspect-pages`; процедуры `sp-delete-backuphistory`, `sp-add-job`, `sp-add-jobstep`, `sp-add-jobschedule`, `sp-add-jobserver`.
- Конфигурация и безопасность: `database-engine/configure-windows/`: `backup-checksum-default`, `view-or-configure-the-backup-compression-default-…`, `…-backup-compression-algorithm-…`, `sql-writer-service`, `configure-windows-service-accounts-and-permissions`; роли — `security/authentication-access/database-level-roles`, `server-level-roles`; `sql-server/failover-clusters/troubleshoot-orphaned-users-sql-server`; планы обслуживания — `maintenance-plans/maintenance-plans`, `maintenance-cleanup-task-maintenance-plan`.
- Linux: `linux/migrate/restore-database`, `linux/configure/mssql-conf`, `linux/sql-server-linux-overview`. Редакции: `sql-server/editions-and-components-of-sql-server-2022`, `…-2025`; `sql-server/what-s-new-in-sql-server-2025`; копии на вторичных репликах — `database-engine/availability-groups/windows/active-secondaries-backup-on-secondary-replicas-…`. `sqlcmd` — `tools/sqlcmd/sqlcmd-utility`. Ошибки 3013, 3043, 3156, 3159, 3169, 3183, 3201, 4214, 9002, 18210 — `relational-databases/errors-events/mssqlserver-NNNN-database-engine-error`.
- PowerShell: https://learn.microsoft.com/powershell/module/sqlserver/backup-sqldatabase , …/restore-sqldatabase ; `wbadmin start backup` — https://learn.microsoft.com/windows-server/administration/windows-commands/wbadmin-start-backup ; сроки поддержки — https://learn.microsoft.com/lifecycle/products/sql-server-2016 .

ИТС 8.3.27 (полные тексты, выгружены 19.10.2026; `https://its.1c.ru/db/v8327doc/content/<NNN>/hdoc`): «Руководство администратора» — гл. 5 (content/104), гл. 6 (105), гл. 7 (106), прил. 3 (115); «Клиент-серверный вариант» — гл. 1 (123), гл. 2 (124), гл. 5 (127); «Руководство разработчика» — гл. 2, разд. 2.14.2.1 (47), гл. 26 (конспект `../its-docs/dev-gl26-kopii-bazy-dannyh.md`); отличия 8.5.1 — `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`. Методические статьи (`https://its.1c.ru/db/metod8dev/content/<NNNN>/hdoc`): 2922, 2378, 2373 (2008), 2926 (2008), 4055 (2010), 5837 (2022), 5899 (2016), 5904 (2019), 5908 (2022), 6008 (2023).

Сторонние: Ola Hallengren — https://ola.hallengren.com/sql-server-backup.html , https://ola.hallengren.com/frequently-asked-questions.html , https://github.com/olahallengren/sql-server-maintenance-solution ; dbatools — https://github.com/dataplat/dbatools (`public/Backup-DbaDatabase.ps1`, `Restore-DbaDatabase.ps1`, `Test-DbaLastBackup.ps1`).

База знаний (согласованность): `../1c-windows/02-ms-sql-server-dlya-1c.md`, `../1c-windows/06-windows-server-dlya-administratora-1c.md`, `../1c/03-administrirovanie-klastera-ras-rac.md`.

Независимая сверка 20.10.2026 (дополнительно к перечисленному): MS Learn — `t-sql/statements/backup-certificate-transact-sql`, `alter-database-transact-sql-compatibility-level`, `alter-user-…`, `create-login-…`; `sql-server/sql-server-2025-known-issues` (ZSTD и `sp_configure`); `relational-databases/system-catalog-views/sys-database-principals`; DMV `sys-dm-tran-session-transactions`, `sys-dm-exec-sessions`, `sys-dm-os-volume-stats` (каталог `system-dynamic-management-objects`); `sp-start-job`; `database-engine/configure-windows/view-or-configure-the-backup-compression-algorithm-server-configuration-option`; `database-engine/discontinued-database-engine-functionality-in-sql-server`; https://learn.microsoft.com/powershell/sql-server/download-sql-server-ps-module ; `wbadmin-start-backup` (исходник `MicrosoftDocs/windowsserverdocs`). ИТС — «Руководство администратора», прил. 4 (content/116, разд. 4.10.2 — общие параметры `ibcmd`), гл. 26 «Руководства разработчика» по полному тексту (content/71). Сторонние — `MaintenanceSolution.sql`, `DatabaseBackup.sql`, README и LICENSE репозитория Ola Hallengren; dbatools `public/Copy-DbaLogin.ps1`.

## Что не удалось подтвердить

- Номера ошибок 3101, 3136, 3154, 4305, 4326 и их тексты (кроме текста «Exclusive access could not be obtained…», подтверждённого 20.10.2026 по `restore-a-database-backup-using-ssms`), сообщения о занятой однопользовательской базе — страниц в документации нет; сверять `SELECT message_id, text FROM sys.messages WHERE message_id IN (3101, 3136, 3154, 4305, 4326) AND language_id = 1033;`.
- Часовой пояс `STOPAT`; версия удаления `TRUNCATE_ONLY`/`NO_LOG` (по истории — 2008; в `discontinued-database-engine-functionality-in-sql-server` её нет); соответствие «`RESOURCE PENDING`» состоянию `RECOVERY_PENDING`.
- Какие операции реструктуризации и загрузки `.dt` 1С выигрывают от `BULK_LOGGED`; рекомендации 1С по ADR; влияние параметров сортировки экземпляра/`tempdb` на 1С; поведение 1С при несовпадении смещения дат; использование 1С Service Broker и меток транзакций.
- Прочие ключи `rac` — сверять с `rac help` своей версии (значение `--dbms=MSSQLServer` и синонимы `--db-user`/`--database-user` у `ibcmd` уточнены 20.10.2026 по ИТС-адм прил. 4, разд. 4.10.2).
- Права по умолчанию на `sp_delete_backuphistory` (документация говорит лишь, что выданное `EXECUTE` может перезаписаться при обновлении); установка dbatools; умолчания шифрования dbatools 2.x; скрипт `sp_help_revlogin`. (`BACKUP CERTIFICATE`, `sp_start_job`, `-CompressionOption`, `Install-Module SqlServer`, `Copy-DbaLogin` — сверены 20.10.2026.)
- Где задаётся `TrustServerCertificate` для SQL Writer 2025 (сама настройка и умолчания — сверены 20.10.2026; «известная проблема» с `backup compression algorithm = 3` — тоже).
- Удаление временного второго файла журнала через `EMPTYFILE` (для журнала не описано); нужен ли `PAGE = …` при восстановлении разностной копии в последовательности страничного восстановления.
- Режимы программ копирования ВМ (обработка приложений, copy-only, усечение журнала).
- Копирование `1Cv8Log` «на ходу» и перенос журнала регистрации на новый uuid ИБ.
- Задание планировщика от `NT AUTHORITY\SYSTEM` или gMSA в Express; работа заданий агента с владельцем `sa` при отключённом логине `sa`.
- Все команды статьи на сервере не выполнялись.
