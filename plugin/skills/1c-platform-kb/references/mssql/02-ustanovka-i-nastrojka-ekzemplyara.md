# Установка и настройка экземпляра SQL Server под 1С: подготовка Windows, установка мастером и без участия, службы и привилегии, сортировка, сеть и драйвер, sp_configure, tempdb и model, флаги трассировки, уровень совместимости, обновления, SQL Server на Linux

> **Официальные тексты по теме** (полные тексты ИТС 8.3.27, адрес главы — `https://its.1c.ru/db/v8327doc/content/NNN/hdoc`): «Клиент-серверный вариант. Руководство администратора» — гл. 1 (123: разд. 1.3.1, 1.3.2, 1.5.4), гл. 2 (124: разд. 2.3), гл. 3 (125: разд. 3.2.1, 3.2.3), гл. 5 (127: разд. 5.2.12.3, 5.5), прил. 3 (133: разд. 3.7, 3.8); «Руководство администратора» — гл. 5 (104: разд. 5.2.1.3.2), гл. 6 (105: разд. 6.8), гл. 7 (106: разд. 7.2), прил. 3 (115: разд. 3.17.23 `UpdateDBCfg`, 3.24 техжурнал, событие `DBMSSQLCONN`); «Руководство разработчика» — гл. 9 (54: разд. 9.2.3.2), прил. 8 (92: разд. 8.4). Методические статьи ИТС: 5904 (2019), 5946 (2019), 5945 (2018), 6008 (2023), 5899 (2016), 5908 (2022), 5834 (2015), 2926/2374/2377/2379 (2008). Конспекты в базе: `../its-docs/cs-gl01-trebovaniya.md`, `../its-docs/cs-gl03-ustanovka-komponentov-p2.md`, `../its-docs/cs-gl02-klient-servernyj-variant-p3.md`, `../its-docs/adm-gl05-spisok-infobaz.md`, `../its-docs/adm-gl07-avtonomnyj-server.md`, `../its-docs/dev-gl09-rabota-s-dannymi.md`, `../its-docs/dev-prilozheniya.md`, `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`. При расхождении этой статьи с первоисточником прав первоисточник.

> Статус: проверено независимой сверкой 20.10.2026: с полными текстами ИТС 8.3.27 («Клиент-серверный вариант» гл. 1, 2, 3, 5, прил. 3; «Руководство администратора» гл. 5, 6, 7, прил. 3; «Руководство разработчика» гл. 9, прил. 8), методическими статьями ИТС 5904, 5946, 5945, 6008, 5899, 5908, 5834, 2926, 2371, 2374, 2377, 2379, со страницей v8.1c.ru «Список поддерживаемых СУБД» (20.10.2026), со сроками на learn.microsoft.com/lifecycle и с исходниками документации Microsoft (`MicrosoftDocs/sql-docs`, ветка `live`; `MicrosoftDocs/SupportArticles-docs`, ветка `main`) — параметры `setup.exe` и `ConfigurationFile.ini`, `sp_configure` и их умолчания, имена столбцов DMV и свойств `SERVERPROPERTY` во всех запросах, флаги трассировки, уровни совместимости, OLE DB Driver, `mssql-conf`; исправлено 5 ошибок, закрыто 3 пометки; на сервере не проверялось. Команды T‑SQL, PowerShell, `setup.exe` и `mssql-conf` не запускались.

> Область: установка и первичная настройка **экземпляра** Microsoft SQL Server, который будет хранить базы «1С:Предприятия 8» при рабочих серверах 1С на Windows: подготовка Windows и дисков, установка мастером и без участия (`setup.exe`, `ConfigurationFile.ini`), учётные записи служб, Instant File Initialization и Lock Pages in Memory, сортировка, проверка подлинности, протоколы, порты, брандмауэр, драйвер на серверах 1С, параметры `sp_configure`, `tempdb`, `model`, флаги трассировки, уровень совместимости и оценщик кардинальности, обновления CU/GDR, кратко — SQL Server на Linux и `mssql-conf` | Версии: SQL Server 2016–2025 (1С 8.3.27 и 8.5.1 поддерживают до 2022 включительно), Windows Server 2016–2025, платформа 1С 8.3.27 / 8.5.1 | Актуальность: 2026-10-20

**Как читать статью**

- **[ИТС-КС разд. N.N]** — «Клиент-серверный вариант. Руководство администратора» 8.3.27; **[ИТС-адм разд. N.N]** — «Руководство администратора» 8.3.27 (приложения — «прил. N, разд. N.N»); **[ИТС-разр гл./прил. N]** — «Руководство разработчика» 8.3.27.
- **[ИТС-мет NNNN, ГГГГ]** — методическая статья `https://its.1c.ru/db/metod8dev/content/NNNN/hdoc` с датой публикации. Статьи 2008 года писались под SQL Server 2000/2005 — у каждого совета из них указано, актуален ли он.
- **[MS Learn]** — документация Microsoft (learn.microsoft.com; исходники на GitHub, адреса — в разделе «Источники»). **[v8.1c.ru]** — страница системных требований фирмы «1С» «Список поддерживаемых СУБД».
- **[практика]** — устоявшаяся практика администраторов, в первоисточниках в таком виде не описана. **[сторонний]** — сторонний инструмент по его официальному сайту. **⚠** — не удалось подтвердить первоисточником: перед применением проверить на стенде.
- **Ваш контекст.** Сервер 1С у вас на Ubuntu, СУБД — «PostgreSQL для 1С». **Рабочие процессы 1С на Linux с MS SQL Server не работают** [ИТС-КС разд. 2.3], поэтому раздел `kb/mssql/` — справочник для Windows-площадок организации. Сам SQL Server при этом может стоять и на Linux, если рабочие серверы 1С — на Windows [v8.1c.ru]. Базы сервисов (Redmine, NetBox, GlitchTip и др.) в экземпляр SQL Server для 1С не кладут — как и в кластер «PostgreSQL для 1С».

**Смежные статьи раздела** (их тему здесь не расписываю):

- `mssql/01-versii-redakcii-arhitektura.md` — версии, редакции, сроки поддержки, архитектура;
- `mssql/03-administrirovanie-instrumenty-prava.md` — SSMS, `sqlcmd`, dbatools, логины для 1С, роли `processadmin`/`dbcreator`, создание базы;
- `mssql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` — модели восстановления, `BACKUP`/`RESTORE`, проверка копий;
- `mssql/05-obsluzhivanie-indeksy-statistika.md` — регламент: статистика, индексы, `DBCC CHECKDB`, очистка кеша планов;
- `mssql/06-monitoring-i-diagnostika.md` — ожидания, DMV, Query Store, Extended Events, блокировки;
- `mssql/07-otkazoustojchivost-i-obnovlenie-versij.md` — Always On, FCI, доставка журналов, переход на новую версию SQL Server;
- `mssql/08-tipovye-problemy-i-zaprosy-1c.md` — типовые проблемы 1С на MS SQL и запросы.

Обзор всего MS SQL для 1С одной статьёй — `../1c-windows/02-ms-sql-server-dlya-1c.md`; Windows Server под 1С (электропитание, антивирус, сеть) — `../1c-windows/06-windows-server-dlya-administratora-1c.md`; сервер 1С на Windows, служба и `USR1CV8` — `../1c-windows/01-ustanovka-servera-i-sluzhba-windows.md`.

**Условные обозначения в примерах:** сервер СУБД `sql01`, экземпляр по умолчанию `MSSQLSERVER` (служба `MSSQLSERVER`, учётная запись `NT SERVICE\MSSQLSERVER`), тома `C:` (система и программы), `D:` (данные), `L:` (журналы), `T:` (`tempdb`), `E:` (резервные копии); доменная группа администраторов СУБД `CORP\sql-admins`; рабочие серверы 1С `10.10.0.21`, `10.10.0.22`, машина администратора `10.10.0.50`; база 1С `buh`, логин `buh_1c`. «Под sysadmin» — подключение к экземпляру учётной записью из роли `sysadmin` (SSMS или `sqlcmd -S sql01 -E`); «PowerShell (админ)» — PowerShell, запущенный от имени локального администратора сервера.

## Кратко — главные факты

1. **MS SQL — только при рабочих серверах 1С на Windows**: рабочий процесс на Linux с MS SQL не работает [ИТС-КС разд. 2.3], `ibsrv` на Linux — тоже [ИТС-адм разд. 7.2]; ARM64 и E2K не поддерживаются [ИТС-КС разд. 1.5.4]. Сам SQL Server может стоять на Linux [v8.1c.ru].
2. **Версии:** 8.3.27 и 8.5.1 — от 2000 SP1 до 2022 [ИТС-КС разд. 1.5.4; `otlichiya-8.5.1`]; v8.1c.ru (20.10.2026) для x86-64 — 2016, 2017, 2019, 2022. **2025 у 1С нет** — новая установка: 2022 с последним CU.
3. **Диски:** данные, журналы, `tempdb`, копии — на разных томах; отклик данных 10–20 мс, журнала 1–5 мс; выравнивание 1024 КБ, NTFS 64 КБ, без сжатия [ИТС-мет 5904, 2019; 6008, 2023]. Сектор больше 4 КБ не поддерживается — `ForcedPhysicalSectorSizeInBytes` [MS Learn].
4. **Антивирус:** исключить `sqlservr.exe`, `sqlagent.exe`, `sqlbrowser.exe`, `.mdf/.ndf/.ldf/.bak/.trn` и их каталоги [MS Learn]; в закрытом сегменте 1С антивирус на серверах не ставит [ИТС-мет 5908, 2022].
5. **Компоненты:** `/FEATURES=SQLEngine`; SSMS — отдельно [MS Learn]. Экземпляр по умолчанию — TCP 1433; именованный — статический порт или Browser (UDP 1434) [MS Learn].
6. **Без участия:** `setup.exe /Q /ACTION=Install /IACCEPTSQLSERVERLICENSETERMS /SUPPRESSPRIVACYSTATEMENTNOTICE /PID=…`; без `/PID` — Evaluation; `/SQLMAXDOP`, `/SQLMAXMEMORY` — с 2019; `ConfigurationFile.ini` (без паролей) — в `…\Setup Bootstrap\Log\<дата>` [MS Learn].
7. **Служба:** по умолчанию `NT SERVICE\MSSQLSERVER` (в сети — `ДОМЕН\ИМЯ$`); менять учётную запись — только в Configuration Manager (`SQLServerManager16.msc` / `…17.msc`) [MS Learn].
8. **IFI — включать** (`/SQLSVCINSTANTFILEINIT=True` или «Perform volume maintenance tasks» для SID службы) [ИТС-мет 5904; MS Learn]; проверка — `sys.dm_server_services`. С 2022 рост журнала до 64 МБ тоже мгновенный [MS Learn].
9. **LPIM — не включать при сервере 1С на той же машине** [ИТС-мет 5904, 2019]; на выделенном — при признаках вытеснения (17890) и только с `max server memory` [MS Learn].
10. **Сортировка:** ИТС требования не формулирует ⚠; `tempdb` — в сортировке экземпляра [MS Learn]; практика — сортировка экземпляра = сортировке баз 1С, для русских конфигураций `Cyrillic_General_CI_AS`, задавать явно (`/SQLCOLLATION`). Смена — пересборкой системных баз [MS Learn].
11. **Проверка подлинности:** смешанная, логин на каждую ИБ [ИТС-мет 5904; ИТС-КС прил. 3, разд. 3.7]; `sa` отключить [MS Learn].
12. **Протоколы:** TCP/IP вкл., Named Pipes выкл. [ИТС-мет 5904]. **`UpdateDBCfg=v2` с MS SQL — только по TCP/IP** [ИТС-адм прил. 3, разд. 3.17.23], а OLE DB Driver 19.1+ пробует `sm tcp np` [MS Learn] — конфликт на совмещённом сервере (7.1). Setup порты не открывает [MS Learn].
13. **Драйвер на серверах 1С:** OLE DB Driver актуальной версии или Native Client [ИТС-КС разд. 1.5.4]; Native Client с 2022+ не поставляется; **OLE DB 19 по умолчанию требует шифрования** и доверенного сертификата, 18 — нет; актуальны 18.7.6 и 19.4.3 [MS Learn]. 8.5.1 знает `MSOLEDBSQL19` [`otlichiya-8.5.1`].
14. **`max server memory`** задавать всегда (умолчание — без предела); при совмещении — минус доля 1С [ИТС-мет 5904; MS Learn].
15. **`max degree of parallelism` = 1** [ИТС-мет 5904; 6008; 5945]; на реструктуризацию — 0 и обратно [ИТС-мет 5945, 2018]; при `MAXDOP = 1` `cost threshold for parallelism` не действует [MS Learn].
16. **`remote admin connections` = 1** [ИТС-мет 5904]; DAC по умолчанию — 127.0.0.1:1434 [MS Learn]; `backup compression default` и `backup checksum default` = 1 [MS Learn; практика].
17. **`tempdb`:** 4 файла [ИТС-мет 5904] / min(8, логических CPU) [MS Learn], одинаковые размер и прирост; на 2016+ флаги 1117/1118 не нужны [MS Learn].
18. **`model`:** наследуются параметры и модель восстановления, из файловых свойств — только начальный размер данных; прирост без `FILEGROWTH` — 64 МБ [MS Learn] → прирост 512 МБ из ИТС [5904] проверять на каждой базе.
19. **Флаги:** из списка ИТС [5946, 2019] на 2016+ без действия 610, 1117, 1118, 2371, 8048 [MS Learn]; нужны **1224** (вместо 1211) и **4199** (для 2014 его требует платформа [ИТС-адм разд. 5.2.1.3.2]); только через `-T`, иначе пропадут [MS Learn].
20. **Совместимость:** 130/140/150/160/170 для 2016/2017/2019/2022/2025; восстановленная база сохраняет уровень; старый оценщик для базы — `LEGACY_CARDINALITY_ESTIMATION = ON` (2016+) [MS Learn]; у 1С рекомендаций нет ⚠.
21. **Обновления:** с 2017 только CU и GDR [MS Learn]; ставить последний CU [ИТС-мет 5904]: `<пакет>.exe /qs /IAcceptSQLServerLicenseTerms /Action=Patch /InstanceName=MSSQLSERVER` [MS Learn]; перед — копии баз [практика].
22. **2022+:** «Automatic» на деле — отложенный запуск [MS Learn] — учитывать порядок старта с сервером 1С.
23. **Linux:** `mssql-conf set …` + `systemctl restart mssql-server`; `memory.memorylimitmb` (умолч. 80 %), `traceflag`, `set-collation`; 2022 — Ubuntu 20.04/22.04, 2025 — 22.04/24.04 [MS Learn].

## 1. До установки: где ставить и что выбрать

### 1.1. Ограничения смешанной среды

| Ситуация | MS SQL для баз 1С | Источник |
|---|---|---|
| Рабочие серверы 1С на Windows x86-64 | да | [ИТС-КС разд. 1.5.4] |
| Рабочие серверы 1С на Linux (как у вас) | **нет** — рабочий процесс не взаимодействует с MS SQL | [ИТС-КС разд. 2.3] |
| Кластер 1С на ARM64 или E2K | нет | [ИТС-КС разд. 1.5.4] |
| Автономный сервер `ibsrv` на Linux | нет | [ИТС-адм разд. 7.2] |
| SQL Server на Linux при рабочих серверах 1С на Windows | да | [v8.1c.ru] |
| SQL Server на Windows при рабочих серверах 1С на Windows | да | [ИТС-КС разд. 3.2.1] — там MS SQL помечен «только для Windows»; это расходится с v8.1c.ru (версия для Linux допускается) — ИТС, видимо, отстаёт ⚠ |

Если сервер 1С площадки переедет на Linux, базы придётся перенести в PostgreSQL (`ibcmd infobase replicate`, `../1c-windows/02-…`) [практика].

### 1.2. Версия SQL Server

| Источник | Что сказано |
|---|---|
| [ИТС-КС разд. 1.5.4] (8.3.27) | 2000 SP1 (реком. SP4), 2005 SP3, 2008 SP1, 2008 R2, 2012, 2014, 2016, 2017, 2019, 2022; при режиме совместимости конфигурации выше 8.3.7 — минимум 2005 |
| `../its-docs/otlichiya-8.5.1-ot-8.3.27.md` (8.5.1) | список MS SQL не изменился: 2000 SP1 – 2022 |
| [v8.1c.ru] на 20.10.2026 | x86-64: SQL Server 2016, 2017, 2019, 2022; «версия для Linux поддерживается в случае использования рабочих серверов… на Microsoft Windows»; 2008 R2, 2012, 2014; 2008 SP1; 2005 SP3 |

- **2025 у 1С не заявлен ни в ИТС, ни на v8.1c.ru** — ставить его под 1С значит работать в неподдерживаемой конфигурации [практика]. Сроки поддержки Microsoft (2025: выход 18.11.2025, основная до 06.01.2031, расширенная до 06.01.2036 [MS Learn]) и остальные версии — `mssql/01-…`.
- **2016** на 20.10.2026 вне расширенной поддержки (с 14.07.2026, далее только платные ESU), **2017** — до 12.10.2027 (по `../1c-windows/02-…`, раздел 2.2, сверено там 19.10.2026 с learn.microsoft.com/lifecycle). Новая установка — **SQL Server 2022 с последним CU** [практика].
- Требования к ОС [MS Learn]: SQL Server 2022 — Windows Server 2016 и новее (Windows 10 1607+), .NET Framework 4.7.2; SQL Server 2025 — Windows Server 2019 и новее; минимум ОЗУ 1 ГБ, рекомендуется от 4 ГБ «и больше по мере роста баз»; только x64.
- Не ставить SQL Server на контроллер домена: службы на DC нельзя запускать под локальной служебной учётной записью, нельзя потом менять роль компьютера, на RODC не поддерживается [MS Learn].

### 1.3. Один сервер с 1С или отдельный

| Вопрос | SQL Server на одной машине с сервером 1С | SQL Server на отдельной машине |
|---|---|---|
| Когда | ИТС: на одном или на разных компьютерах — «в зависимости от предполагаемой загрузки», без порогов [ИТС-мет 2926, 2008]; на одной машине обычно малая и средняя нагрузка [практика] | крупные базы, много пользователей [практика]; сеть 1 Гбит/с и выше между кластером и СУБД [ИТС-КС разд. 1.3.1] |
| `max server memory` | уменьшить на объём, нужный серверу 1С [ИТС-мет 5904, 2019] | память ОС + запас (раздел 9.3) |
| Lock Pages in Memory | **не включать** [ИТС-мет 5904, 2019] | по ситуации [MS Learn] |
| Протокол 1С → СУБД | ИТС советует включить Shared Memory [ИТС-мет 5904], но оптимизированная реструктуризация требует TCP/IP [ИТС-адм прил. 3, разд. 3.17.23] — раздел 7.1 | TCP/IP |
| Отказоустойчивость | падение машины — простой и 1С, и СУБД [практика] | можно резервировать по отдельности (`mssql/07-…`) |

## 2. Подготовка Windows

### 2.1. Раскладка томов

ИТС: файлы данных и журналов — на разных дисковых массивах; к диску журнала требования по скорости выше, чем к диску данных: отклик 10–20 мс для данных и 1–5 мс для журнала [ИТС-мет 5904, 2019; 6008, 2023]. Microsoft: `tempdb` — на быстрый диск; разносить `tempdb` с пользовательскими базами, если между ними есть конкуренция за ввод-вывод; отдельные файлы `tempdb` по разным дискам раскладывать не обязательно [MS Learn].

| Том | Что лежит | Типовой размер [практика] | Комментарий |
|---|---|---|---|
| `C:` | ОС, двоичные файлы SQL Server, системные базы `master`/`model`/`msdb` | 150+ ГБ | установщику нужно не меньше 6 ГБ свободного места [MS Learn] |
| `D:` | файлы данных баз 1С (`.mdf`) | объём баз за 2–3 года + 30 % | NTFS 64 КБ |
| `L:` | журналы транзакций (`.ldf`) | максимум журнала между `BACKUP LOG` + запас; при простой модели — пик реструктуризации | самый быстрый массив, без кэша на запись без батарейки [практика] |
| `T:` | `tempdb` (данные и журнал) | 10–25 % от объёма баз [практика] | при отдельном томе ИТС предлагает занять файлами 50 % тома (раздел 10.2) |
| `E:` | резервные копии | 2–3 полных копии + журналы | лучше отдельный массив или СХД [практика]; подробнее `mssql/04-…` |

Запрет: не указывать один и тот же путь для `INSTANCEDIR` и `SQLUSERDBDIR` — иначе SQL Server Agent и полнотекстовый поиск не стартуют из-за прав [MS Learn].

### 2.2. Форматирование: кластер 64 КБ, выравнивание, размер сектора

- **ИТС:** выровнять разделы по границе 1024 КБ и отформатировать с блоком 64 КБ, «если нет иных рекомендаций от производителя» [ИТС-мет 5904, 2019].
- **Microsoft:** для дисков с файлами данных — размер единицы размещения 64 КБ (так форматируются диски данных SQL Server на ВМ Azure из Marketplace) [MS Learn, Azure VM storage best practices].
- **Сектор:** SQL Server поддерживает диски с размером сектора 512 байт и 4 КБ; если ОС видит сектор больше 4 КБ (часть NVMe-дисков; Microsoft называет Windows 11, чьи драйверы NVMe сообщают реальный размер сектора 8–16 КБ; Windows Server 2025 в этой статье Microsoft не упомянут — на любой ОС проверяйте `fsutil`), установка падает с кодами `0x851A0019` / `0x851A001A`, в журнале ошибки 5178/5179. Проверка — `fsutil fsinfo sectorinfo`, значения `PhysicalBytesPerSectorForAtomicity` и `PhysicalBytesPerSectorForPerformance`; лечение — мультистроковый параметр `ForcedPhysicalSectorSizeInBytes` = `* 4095` в `HKLM\SYSTEM\CurrentControlSet\Services\stornvme\Parameters\Device` и перезагрузка; флаг 1800 для этого не нужен [MS Learn].

Проверка существующих томов (PowerShell (админ), только чтение):

```powershell
# смещение разделов: делится ли на 1 МБ (1048576) [практика]
Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, Offset,
  @{n='Aligned1MB';e={ $_.Offset % 1MB -eq 0 }}
# размер кластера NTFS: ожидается 65536 [практика]
fsutil fsinfo ntfsinfo D: | Select-String 'Bytes Per Cluster'
# размер сектора: не больше 4096 [MS Learn]
fsutil fsinfo sectorinfo D: | Select-String 'PhysicalBytesPerSector'
# нет ли сжатия NTFS на томе/каталоге данных [практика]
(Get-Item 'D:\MSSQL\Data').Attributes -match 'Compressed'
```

Форматирование **уничтожает все данные тома** — только для нового пустого диска, сначала убедитесь, что буква и номер диска верные (PowerShell (админ)) [практика]:

```powershell
# ВНИМАНИЕ: стирает том D:
Format-Volume -DriveLetter D -FileSystem NTFS -AllocationUnitSize 65536 -NewFileSystemLabel 'SQLData' -Confirm
```

Новые разделы, созданные средствами Windows Server 2008 и новее, по умолчанию выровнены по 1 МБ [практика] ⚠ — проверяйте запросом выше, особенно на дисках, перенесённых со старых систем.

- **Без сжатия:** проверить отсутствие сжатия файлов данных и журналов [ИТС-мет 5904, 2019]. Из SQL Server признак виден в `sys.dm_os_volume_stats` — столбцы `is_compressed`, `file_system_type` [MS Learn] (запрос — раздел 3.7).

### 2.3. Электропитание, виртуализация, файловое резервное копирование

- **Схема электропитания — «Высокая производительность»** [ИТС-мет 5904, 2019; 5899, 2016]. PowerShell (админ) [практика]:

```powershell
powercfg /getactivescheme
powercfg /setactive SCHEME_MIN      # псевдоним плана «Высокая производительность»
powercfg /getactivescheme           # проверка
```

Подробнее — `../1c-windows/06-…`.

- **Виртуальная машина:** гарантированное выделение ресурсов, суммарная память ВМ меньше памяти хоста [ИТС-мет 5899, 2016]; в ВМ задать `min server memory`, чтобы гипервизор не отбирал буферный пул [MS Learn] (раздел 9.3).
- **Файлы баз исключить из файлового резервного копирования** (агенты вида Backup Exec) — копировать базы средствами СУБД [ИТС-мет 5904, 2019]. Если на сервере работает копирование на уровне ОС через VSS, служба SQL Writer (`LOCAL SYSTEM`) участвует в нём [MS Learn]; режим копирования, не ломающий цепочку копий СУБД, — `../1c-windows/06-…` (про `-vssCopy`) и `mssql/04-…`.

### 2.4. Антивирус

Позиция 1С: если серверы стоят в зоне со строго ограниченным доступом, антивирус на них не ставят — он заметно снижает производительность почти без выигрыша в защите; защищают компьютеры пользователей [ИТС-мет 5908, 2022]. Это сказано о рабочих серверах кластера; для сервера СУБД отдельной позиции в ИТС нет — логика та же [практика].

Если антивирус обязателен, исключения по Microsoft [MS Learn, «Configure antivirus software to work with SQL Server»] (действуют для SQL Server 2016–2025):

| Что исключить | Значение |
|---|---|
| Процессы | `sqlservr.exe`, `sqlagent.exe`, `sqlbrowser.exe`, `%ProgramFiles%\Microsoft SQL Server\1<NN>\Shared\SQLDumper.exe` |
| Файлы данных и журналов | `.mdf`, `.ndf`, `.ldf` — и каталоги, где они реально лежат (`D:\MSSQL\Data`, `L:\MSSQL\Log`, `T:\TempDB`) |
| Резервные копии | `.bak`, `.trn` и каталог копий |
| Трассировки, XE, аудит | `.trc`; `.xel`, `.xem` (системные — в каталоге `LOG` экземпляра); `.sqlaudit` |
| Дампы | `.mdmp` в каталоге `LOG` экземпляра |
| `DBCC CHECKDB` | временные файлы внутреннего снимка `<файл_данных>_MSSQL_DBCC<id>` |
| Полнотекстовые каталоги | `…\MSSQL\FTDATA` (для 1С обычно не используются) |

Последствия «подметающего» сканирования по Microsoft: если сканер держит файл базы в момент открытия, база может стать `SUSPECT` [MS Learn]. Проверить, не внедрил ли антивирус свои модули в процесс SQL Server, — `SELECT name, company, description FROM sys.dm_os_loaded_modules WHERE ISNULL(company, N'') NOT LIKE N'Microsoft%';` (DMV и столбцы — [MS Learn], фильтр — [практика]).

Исключения в Microsoft Defender (PowerShell (админ); пути — свои) [практика; командлет Defender]:

```powershell
Add-MpPreference -ExclusionProcess 'sqlservr.exe','sqlagent.exe','sqlbrowser.exe'
Add-MpPreference -ExclusionExtension 'mdf','ndf','ldf','bak','trn'
Add-MpPreference -ExclusionPath 'D:\MSSQL\Data','L:\MSSQL\Log','T:\TempDB','E:\Backup'
Get-MpPreference | Select-Object ExclusionProcess, ExclusionExtension, ExclusionPath   # проверка
```

## 3. Установка: мастер и командная строка

Установку запускают **от имени локального администратора**; при установке с сетевой шары — доменной учётной записью с правами чтения и выполнения на шаре [MS Learn]. Без параметра `/PID` (ключа продукта) ставится редакция **Evaluation** [MS Learn] — на рабочем сервере это ошибка: пробная редакция ограничена по сроку ⚠ (срок в прочитанных текстах не указан; по практике — 180 дней).

### 3.1. Какие компоненты нужны 1С

| Компонент (`/FEATURES`) | Для 1С | Источник |
|---|---|---|
| `SQLEngine` — только ядро СУБД | **да** | [MS Learn] — значение параметра |
| `SQL` — ядро + репликация + полнотекстовый поиск + DQ | избыточно | [MS Learn] |
| `Replication` | нет (если нет отдельных задач репликации) | [практика] |
| `FullText` | нет: полнотекстовый поиск 1С — механизм платформы, а не SQL Server | Уточнено 20.10.2026 по ИТС-КС разд. 2.2.3.1 и ИТС-адм разд. 7.4.10: поиск и индексирование выполняет сервис кластера «Полнотекстового поиска», индекс хранится в файлах на стороне сервера 1С (у автономного сервера — каталоги `ftext-data`, `ftext2-data`); компонент SQL Server не используется |
| SQL Server Agent | ставится вместе с ядром (кроме Express) — нужен для заданий копирования и регламента | [MS Learn] (в Express служба Agent отключена) |
| SSMS | отдельный установщик | [MS Learn] |
| `Tools`, `Conn`, `BC`, `SNAC_SDK` | есть только до SQL Server 2019 включительно | [MS Learn] |
| `AZUREEXTENSION` (2022+) | не нужен изолированному серверу 1С | [MS Learn] — параметр; решение — [практика] |

### 3.2. Экземпляр по умолчанию или именованный

- **По умолчанию** (`MSSQLSERVER`) слушает TCP 1433; служба `MSSQLSERVER`, виртуальная учётная запись `NT SERVICE\MSSQLSERVER` [MS Learn]. В свойствах ИБ 1С указывают просто имя компьютера [ИТС-адм разд. 5.2.1.3.2].
- **Именованный** использует динамический порт, клиент узнаёт его у службы SQL Server Browser (UDP 1434); через брандмауэр удобнее задать статический порт [MS Learn]. В ИТС имя экземпляра записано как `Server/instance` [ИТС-адм разд. 5.2.1.3.2]; в нотации Microsoft — `server\instance`, порт — через запятую `server,port` [MS Learn, sqlcmd]. Какие формы принимает поле «Сервер баз данных» 1С, ИТС не уточняет ⚠ — проверяйте на тестовой ИБ.
- Несколько экземпляров на одном сервере — у каждого свой `max server memory`, сумма не должна превышать физическую память [MS Learn] (раздел 9.3). Для 1С обычно один экземпляр по умолчанию на сервер [практика].

### 3.3. Мастер установки: что выбирать

Названия страниц — по английскому интерфейсу SQL Server 2022 ⚠ (точные названия пунктов мастера в прочитанных текстах приведены не все).

| Страница мастера | Решение для 1С | Источник |
|---|---|---|
| Product Key | ключ своей редакции; пустой = Evaluation | [MS Learn] |
| Microsoft Update / Product Updates | искать обновления или указать папку с CU (14.2) | [MS Learn] |
| Install Rules | предупреждение о брандмауэре ожидаемо — порты setup не открывает | [MS Learn] |
| Feature Selection | Database Engine Services; Azure Extension — снять для изолированного сервера | [MS Learn]; [практика] |
| Server Configuration → Service Accounts | виртуальные по умолчанию; Agent — Automatic; Browser — Disabled для единственного экземпляра по умолчанию | [MS Learn]; [практика] |
| Server Configuration → «Grant Perform Volume Maintenance Task privilege to SQL Server Database Engine Service» | **включить** (IFI) | [MS Learn]; [ИТС-мет 5904] |
| Server Configuration → Collation | Customize → задать сортировку (раздел 5) | [MS Learn] |
| Database Engine Configuration | Mixed Mode и пароль `sa`; администраторы — доменная группа; Data Directories — `D:`/`L:`/`E:`; TempDB — min(8, CPU) файлов на `T:`; MaxDOP (2019+) — **1**; Memory (2019+) — вручную при совмещении с 1С; FILESTREAM — нет | [ИТС-мет 5904]; [MS Learn]; разделы 9, 10 |
| Ready to Install | сохранить путь к `ConfigurationFile.ini` | [MS Learn] |

### 3.4. Установка без участия: параметры `setup.exe`

Формат параметров [MS Learn]: `/ПАРАМЕТР`, `/ПАРАМЕТР=True|False`, `/ПАРАМЕТР=1|0` для логических, `/ПАРАМЕТР="значение"`; многозначные — `"A" "B"` через пробел, исключение — `/FEATURES=A,B` через запятую без пробелов. Пути к каталогам можно задавать с завершающим `\` или без.

Параметры, существенные для экземпляра под 1С [MS Learn, «Install SQL Server from the command prompt»]:

| Параметр | Значение / умолчание | Для 1С |
|---|---|---|
| `/ACTION` | `Install` (обязателен) | `Install` |
| `/Q` или `/QS` | тихий режим / только индикатор (`/QS` — только с `/ACTION=INSTALL`) | `/Q` для сценария |
| `/IACCEPTSQLSERVERLICENSETERMS` | обязателен при `/Q`, `/QS` | да |
| `/SUPPRESSPRIVACYSTATEMENTNOTICE` | обязателен при `/Q`, `/QS` | да |
| `/ENU` | английская версия на локализованной ОС | по желанию |
| `/UpdateEnabled`, `/UpdateSource` | по умолчанию setup ищет обновления (MU/WSUS); `/UpdateSource` — `"MU"`, папка, UNC | папка с последним CU |
| `/PID` | ключ продукта; без него — Evaluation | обязательно на рабочем сервере |
| `/PRODUCTCOVEREDBYSA` (2022+) | покрыта ли лицензия Software Assurance | по договору |
| `/FEATURES` | `SQLEngine` | `SQLEngine` |
| `/INSTANCENAME` | обязателен | `MSSQLSERVER` |
| `/INSTANCEDIR`, `/INSTALLSQLDATADIR` | каталог экземпляра; каталог системных баз (умолч. `%Program Files%\Microsoft SQL Server\`) | по умолчанию на `C:` |
| `/SQLSVCACCOUNT`, `/SQLSVCPASSWORD`, `/SQLSVCSTARTUPTYPE` | учётная запись ядра — по документации **обязательна**; пароль для виртуальной, MSA и встроенной не указывается; режим запуска `Automatic`/`Manual`/`Disabled` | `"NT Service\MSSQLSERVER"` (виртуальная) или gMSA; `Automatic` |
| `/AGTSVCACCOUNT`, `/AGTSVCSTARTUPTYPE` | учётная запись Agent (обязательна) и режим запуска | `"NT Service\SQLSERVERAGENT"`; `Automatic` |
| `/BROWSERSVCSTARTUPTYPE` | запуск Browser | `Disabled` для единственного экземпляра по умолчанию [практика] |
| `/SQLSYSADMINACCOUNTS` | обязателен (кроме Express) — члены `sysadmin` | `"CORP\sql-admins"` |
| `/ADDCURRENTUSERASSQLADMIN` | умолч. `True` для Express, `False` для остальных | не использовать |
| `/SECURITYMODE` | `SQL` — смешанный режим; без параметра — только Windows | `SQL` |
| `/SAPWD` | обязателен при `/SECURITYMODE=SQL` | сложный пароль, потом отключить `sa` |
| `/SQLCOLLATION` | по умолчанию — по локали ОС | явно (раздел 5) |
| `/SQLSVCINSTANTFILEINIT` | `False` по умолчанию | `True` |
| `/SQLUSERDBDIR`, `/SQLUSERDBLOGDIR` | умолч. `<InstallSQLDataDir>\<SQLInstanceID>\MSSQL\Data` | `D:\MSSQL\Data`, `L:\MSSQL\Log` |
| `/SQLBACKUPDIR` | умолч. `…\MSSQL\Backup` | `E:\Backup` |
| `/SQLTEMPDBDIR`, `/SQLTEMPDBLOGDIR` | несколько каталогов `/SQLTEMPDBDIR` — через пробел, файлы раскладываются по кругу | `T:\TempDB` |
| `/SQLTEMPDBFILECOUNT` | умолч. 8 или число ядер, что меньше (Express — 1, менять нельзя) | min(8, логических CPU) |
| `/SQLTEMPDBFILESIZE` (2016+) | умолч. 8 МБ; максимум в setup — 1024 МБ | 1024, потом увеличить (раздел 10) |
| `/SQLTEMPDBFILEGROWTH` | умолч. 64 МБ; 0 — без роста; максимум 1024 | 512 [ИТС-мет 5904] |
| `/SQLTEMPDBLOGFILESIZE`, `/SQLTEMPDBLOGFILEGROWTH` (2016+) | умолч. 8 / 64 МБ; максимум 1024 | 1024 / 512 |
| `/TCPENABLED`, `/NPENABLED` | `1`/`0` | `1`, `0` |
| `/SQLMAXDOP` (2019+) | если не задан — по рекомендациям Microsoft | `1` |
| `/USESQLRECOMMENDEDMEMORYLIMITS` (2019+) | рассчитанные Microsoft min/max; несовместим с `/SQLMINMEMORY`/`/SQLMAXMEMORY` | не использовать при совмещении с 1С |
| `/SQLMINMEMORY`, `/SQLMAXMEMORY` (2019+) | min умолч. 0; max — рассчитанная рекомендация | задать явно |
| `/FILESTREAMLEVEL` | умолч. `0` | `0` |
| `/INDICATEPROGRESS`, `/HIDECONSOLE` | подробный журнал в консоль; скрыть окно | по желанию |

Пример установки SQL Server 2022 под 1С (cmd от имени администратора, из каталога дистрибутива; значения памяти — для сервера 128 ГБ без 1С на той же машине) [MS Learn — параметры; значения — практика]:

```bat
setup.exe /Q /ACTION=Install /IACCEPTSQLSERVERLICENSETERMS /SUPPRESSPRIVACYSTATEMENTNOTICE ^
  /PID="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX" /UpdateEnabled=True /UpdateSource="E:\Distr\SQL2022_CU" ^
  /FEATURES=SQLEngine /INSTANCENAME=MSSQLSERVER /SQLSVCACCOUNT="NT Service\MSSQLSERVER" /AGTSVCACCOUNT="NT Service\SQLSERVERAGENT" ^
  /SQLSVCSTARTUPTYPE=Automatic /AGTSVCSTARTUPTYPE=Automatic /BROWSERSVCSTARTUPTYPE=Disabled ^
  /SQLSYSADMINACCOUNTS="CORP\sql-admins" /SECURITYMODE=SQL /SAPWD="<временный пароль sa>" ^
  /SQLCOLLATION=Cyrillic_General_CI_AS /SQLSVCINSTANTFILEINIT=True ^
  /SQLUSERDBDIR="D:\MSSQL\Data" /SQLUSERDBLOGDIR="L:\MSSQL\Log" /SQLBACKUPDIR="E:\Backup" ^
  /SQLTEMPDBDIR="T:\TempDB" /SQLTEMPDBLOGDIR="T:\TempDB" /SQLTEMPDBFILECOUNT=8 ^
  /SQLTEMPDBFILESIZE=1024 /SQLTEMPDBFILEGROWTH=512 /SQLTEMPDBLOGFILESIZE=1024 /SQLTEMPDBLOGFILEGROWTH=512 ^
  /TCPENABLED=1 /NPENABLED=0 /SQLMAXDOP=1 /SQLMINMEMORY=0 /SQLMAXMEMORY=110592
echo %ERRORLEVEL%
```

- Код возврата `0` — успех; подробности — в `Summary.txt` (раздел 3.6) [практика] ⚠ (значения кодов возврата setup в прочитанных текстах не описаны).
- Каталоги `D:\MSSQL\Data`, `L:\MSSQL\Log`, `T:\TempDB`, `E:\Backup` лучше создать заранее [практика]; права на них setup выдаёт SID службы [MS Learn — раздел о правах файловой системы] ⚠ (для нестандартных каталогов — проверить ACL после установки).
- Для SQL Server 2016–2017 убрать `/SQLMAXDOP`, `/SQLMINMEMORY`, `/SQLMAXMEMORY` (их нет до 2019) и задать то же через `sp_configure` после установки (раздел 9) [MS Learn].
- `/SQLTEMPDBFILECOUNT=8` в примере рассчитан на сервер с 8 и более ядрами: значение можно поднимать только до числа ядер [MS Learn] — на меньшем сервере укажите число ядер.
- **Пароли в командной строке** остаются в истории оболочки и могут попасть в журналы [практика]; надёжнее — `ConfigurationFile.ini` без паролей и ввод `/SAPWD` в момент запуска, а сразу после установки — смена пароля `sa` и отключение входа (раздел 6) [MS Learn: «по возможности передавайте учётные данные во время выполнения»].

### 3.5. Файл конфигурации `ConfigurationFile.ini`

- Мастер формирует файл по введённым значениям; путь показан на странице **Ready to Install**; чтобы получить файл, не устанавливая, — дойти до этой страницы и отменить установку [MS Learn]. Express сам файл не создаёт — запуск `SETUP.exe /UIMODE=Normal /ACTION=INSTALL` [MS Learn].
- В файл **не пишутся пароли** и `/IAcceptSQLServerLicenseTerms` — их передают в командной строке или добавляют в файл вручную [MS Learn].
- Порядок применения: файл перекрывает умолчания пакета, командная строка перекрывает файл [MS Learn]. Для каждой новой версии SQL Server файл генерировать заново — набор параметров меняется [MS Learn].
- Использовать файл можно только при установке из командной строки: `Setup.exe /ConfigurationFile=MyConfigurationFile.ini` [MS Learn].
- После установки копия файла остаётся в `%ProgramFiles%\Microsoft SQL Server\<nnn>\Setup Bootstrap\Log\<yyyyMMdd_HHmmss>\ConfigurationFile.ini` [MS Learn] — удобно для аудита и повторения настройки на втором сервере.

Пример файла для экземпляра 1С (SQL Server 2022). Ключи — те же имена, что у параметров командной строки, без `/` [MS Learn — структура файла: секция `[OPTIONS]`, пары «имя=значение»]; файл, сгенерированный мастером, содержит больше ключей — берите его за основу, а этот используйте как список того, что проверить:

```ini
; ConfigurationFile.ini для экземпляра SQL Server под 1С (пример, SQL Server 2022)
[OPTIONS]
ACTION="Install"
FEATURES=SQLENGINE
INSTANCENAME="MSSQLSERVER"
SQLSVCACCOUNT="NT Service\MSSQLSERVER"
AGTSVCACCOUNT="NT Service\SQLSERVERAGENT"
QUIET="True"
SUPPRESSPRIVACYSTATEMENTNOTICE="True"
UPDATEENABLED="True"
UPDATESOURCE="E:\Distr\SQL2022_CU"
SQLSVCSTARTUPTYPE="Automatic"
AGTSVCSTARTUPTYPE="Automatic"
BROWSERSVCSTARTUPTYPE="Disabled"
SQLSYSADMINACCOUNTS="CORP\sql-admins"
SECURITYMODE="SQL"
SQLCOLLATION="Cyrillic_General_CI_AS"
SQLSVCINSTANTFILEINIT="True"
SQLUSERDBDIR="D:\MSSQL\Data"
SQLUSERDBLOGDIR="L:\MSSQL\Log"
SQLBACKUPDIR="E:\Backup"
SQLTEMPDBDIR="T:\TempDB"
SQLTEMPDBLOGDIR="T:\TempDB"
SQLTEMPDBFILECOUNT="8"
SQLTEMPDBFILESIZE="1024"
SQLTEMPDBFILEGROWTH="512"
SQLTEMPDBLOGFILESIZE="1024"
SQLTEMPDBLOGFILEGROWTH="512"
TCPENABLED="1"
NPENABLED="0"
SQLMAXDOP="1"
SQLMINMEMORY="0"
SQLMAXMEMORY="110592"
```

Запуск (cmd от имени администратора; пароль `sa` и согласие с лицензией — в командной строке):

```bat
setup.exe /ConfigurationFile="E:\Distr\SQL2022_1C.ini" /IACCEPTSQLSERVERLICENSETERMS /PID="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX" /SAPWD="<временный пароль sa>"
```

Ключи `QUIET`, `UPDATEENABLED`, `UPDATESOURCE` в виде ключей файла — по аналогии с параметрами командной строки ⚠ (в сгенерированном файле проверьте их точное написание).

### 3.6. Журналы установки

[MS Learn, «View and read SQL Server Setup log files»]:

| Файл | Где |
|---|---|
| `Summary.txt` — итог последнего запуска | `%programfiles%\Microsoft SQL Server\<nnn>\Setup Bootstrap\Log` |
| `Summary_<ИмяКомпьютера>_<дата>.txt`, `Detail.txt`, `ConfigurationFile.ini`, `SystemConfigurationCheck_Report.htm`, журналы MSI | `…\Setup Bootstrap\Log\<yyyyMMdd_HHmmss>` |
| Тихий режим | `%temp%\sqlsetup*.log` |

`<nnn>` — номер версии: 130 для 2016, 140 для 2017 [MS Learn], далее 150 (2019), 160 (2022), 170 (2025) [практика]. При ошибке смотрят `Summary.txt` (раздел с неуспешными правилами и компонентами), затем `Detail.txt` — поиск по слову `error` [практика].

### 3.7. Проверка после установки

Под sysadmin (SSMS или `sqlcmd -S sql01 -E`; клиент `sqlcmd` из комплекта 2025 по умолчанию требует шифрования (`-Nm`) — для сервера с самоподписанным сертификатом добавьте `-C`, доверие к сертификату [MS Learn]):

```sql
-- 1. Версия, CU, редакция, сортировка, режим проверки подлинности [MS Learn: SERVERPROPERTY]
SELECT SERVERPROPERTY('ProductVersion')          AS version,
       SERVERPROPERTY('ProductLevel')            AS level,        -- RTM / SPn
       SERVERPROPERTY('ProductUpdateLevel')      AS cu,           -- CUn
       SERVERPROPERTY('ProductUpdateReference')  AS kb,
       SERVERPROPERTY('Edition')                 AS edition,
       SERVERPROPERTY('Collation')               AS server_collation,
       SERVERPROPERTY('IsIntegratedSecurityOnly') AS windows_only, -- 0 = смешанный режим
       SERVERPROPERTY('InstanceDefaultDataPath') AS data_path,
       SERVERPROPERTY('InstanceDefaultLogPath')  AS log_path,
       SERVERPROPERTY('InstanceDefaultBackupPath') AS backup_path; -- 2019+

-- 2. Службы, учётные записи, IFI [MS Learn: sys.dm_server_services]
SELECT servicename, startup_type_desc, status_desc, service_account,
       instant_file_initialization_enabled
FROM sys.dm_server_services;

-- 3. Процессоры, память, модель памяти (LPIM), ВМ [MS Learn: sys.dm_os_sys_info]
SELECT cpu_count, hyperthread_ratio, socket_count, cores_per_socket, numa_node_count,
       physical_memory_kb / 1024 AS physical_memory_mb, sql_memory_model_desc,
       virtual_machine_type_desc, softnuma_configuration_desc
FROM sys.dm_os_sys_info;

-- 4. Параметры экземпляра
SELECT name, value, value_in_use, is_dynamic, is_advanced
FROM sys.configurations
WHERE name IN (N'max server memory (MB)', N'min server memory (MB)', N'max degree of parallelism',
               N'cost threshold for parallelism', N'optimize for ad hoc workloads',
               N'backup compression default', N'backup checksum default',
               N'remote admin connections', N'blocked process threshold (s)');

-- 5. Файлы всех баз и тома под ними: где лежат, сколько свободно, нет ли сжатия [MS Learn]
SELECT DB_NAME(f.database_id) AS db, f.type_desc, f.name, f.physical_name,
       f.size / 128 AS size_mb, f.growth, f.is_percent_growth,
       vs.volume_mount_point, vs.file_system_type, vs.is_compressed,
       vs.available_bytes / 1048576 AS volume_free_mb
FROM sys.master_files AS f
CROSS APPLY sys.dm_os_volume_stats(f.database_id, f.file_id) AS vs
ORDER BY db, f.type_desc;

-- 6. Параметры запуска (-T, -d, -e, -l) и сетевые настройки из реестра [MS Learn]
SELECT registry_key, value_name, value_data FROM sys.dm_server_registry
WHERE registry_key LIKE N'%Parameters' OR registry_key LIKE N'%SuperSocketNetLib%';

-- 7. Журнал ошибок: IFI, LPIM, порты [MS Learn: sp_readerrorlog; тексты сообщений — см. ниже]
EXECUTE sp_readerrorlog 0, 1, N'Instant File Initialization';
EXECUTE sp_readerrorlog 0, 1, N'locked pages';
EXECUTE sp_readerrorlog 0, 1, N'listening';
```

- Сообщение `Database Instant File Initialization: enabled.` — IFI работает; `…: disabled.` — нет (2012 SP4, 2014 SP2, 2016 и новее) [MS Learn]. `Using locked pages in the memory manager` — LPIM действует [MS Learn]. Строки вида `Server is listening on [ 'any' <ipv4> 1433]` показывают адреса и порты — подтверждено 20.10.2026 (MS Learn, статья поддержки «A network-related or instance-specific error occurred while establishing a connection to SQL Server»).
- Читать журнал ошибок в 2022+ может член `securityadmin` или владелец разрешения `VIEW ANY ERROR LOG`/`VIEW SERVER STATE` [MS Learn].

PowerShell (админ) — службы и порт [практика]:

```powershell
Get-Service -Name 'MSSQLSERVER','SQLSERVERAGENT','SQLBrowser' | Select-Object Name, Status, StartType
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 1433,1434 | Select-Object LocalAddress, LocalPort, OwningProcess
Test-NetConnection sql01 -Port 1433      # с рабочего сервера 1С
```

## 4. Учётные записи служб и привилегии Windows

### 4.1. Какую учётную запись дать службе

| Вариант | Имя | Когда | Источник |
|---|---|---|---|
| Виртуальная учётная запись (умолчание с Windows Server 2008 R2) | `NT SERVICE\MSSQLSERVER`, Agent — `NT SERVICE\SQLSERVERAGENT`; именованный экземпляр — `NT SERVICE\MSSQL$<имя>`, `NT SERVICE\SQLAGENT$<имя>` | изолированный сервер; в сеть выходит как учётная запись компьютера `ДОМЕН\ИМЯКОМПЬЮТЕРА$` | [MS Learn] |
| Управляемая (MSA) | `ДОМЕН\ИМЯ$`, пароль пустой | один сервер, нужны сетевые ресурсы и самостоятельная регистрация SPN | [MS Learn] |
| Групповая управляемая (gMSA) | `ДОМЕН\ИМЯ$` | несколько серверов: FCI, группы доступности (2016+) | [MS Learn] |
| Доменная учётная запись | `ДОМЕН\svc-sql` | если MSA/gMSA недоступны; минимальные права, отдельная для каждой службы | [MS Learn] |

- Microsoft: по возможности MSA, gMSA или виртуальная; не давать учётной записи службы дополнительных прав — права выдаются SID службы или через группы [MS Learn]. На контроллере домена виртуальные учётные записи не поддерживаются [MS Learn].
- Если виртуальная учётная запись не смогла зарегистрировать SPN — зарегистрировать вручную (Kerberos для подключений к SQL Server) [MS Learn]. Для 1С с логинами SQL Server это не критично; при входе рабочих процессов 1С в SQL Server по Windows-аутентификации без SPN будет NTLM [практика] ⚠.
- **Копии на сетевую папку:** при виртуальной учётной записи права на шару выдают учётной записи компьютера `ДОМЕН\sql01$` [MS Learn; практика].

Setup выдаёт SID службы ядра права `SeServiceLogonRight`, `SeAssignPrimaryTokenPrivilege`, `SeChangeNotifyPrivilege`, `SeIncreaseQuotaPrivilege` и др. [MS Learn]; права IFI и LPIM в этот список **не входят** — их выдают отдельно (4.2, 4.3).

**Смена учётной записи или пароля службы — только в SQL Server Configuration Manager**: он заодно обновляет локальное хранилище безопасности, защищающее главный ключ службы; оснастка «Службы» меняет только имя, и потом, например, задания Agent с шагами CmdExec падают с «A required privilege isn't held by the client» [MS Learn]. Запуск оснастки: `SQLServerManager16.msc` (2022), `SQLServerManager17.msc` (2025), для других версий — свой номер [MS Learn].

С SQL Server 2022 режим запуска «Automatic», выставленный в Configuration Manager, фактически работает как «Automatic (Delayed Start)» [MS Learn]. Если на той же машине служба сервера 1С стартует раньше SQL Server, первые подключения рабочих процессов могут завершаться ошибкой до старта СУБД [практика] ⚠ — проверьте после перезагрузки журнал 1С и при необходимости задайте зависимость или отложенный запуск службы 1С (`../1c-windows/01-…`).

### 4.2. Instant File Initialization (IFI)

**Что это.** Без IFI SQL Server при создании базы, добавлении файла, росте файла (в том числе автоприросте) и восстановлении из копии сначала заполняет новое место нулями; с IFI место отдаётся сразу, старое содержимое диска перезаписывается по мере записи данных [MS Learn]. ИТС: автоприрост «крайне затратен», пока место «забивается нулями», транзакции не могут менять данные [ИТС-мет 6008, 2023].

**Когда работает.** IFI для файлов данных — если SID службы или учётной записи службы выдано право `SE_MANAGE_VOLUME_NAME` («Perform volume maintenance tasks», «Выполнение задач по обслуживанию томов») [MS Learn]. Для **журнала транзакций** — с SQL Server 2022 (все редакции) рост до 64 МБ инициализируется мгновенно и без этого права; рост больше 64 МБ — с обнулением [MS Learn]. Отсюда совет: на 2022+ прирост журнала 64 МБ ускоряет авторост, но для баз 1С с большим журналом ИТС советует размер, исключающий авторост вообще (раздел 11) — эти рекомендации не противоречат друг другу [практика]. TDE отключает IFI для файлов данных (для журнала в 2022+ — нет) [MS Learn]; шифрование на уровне СУБД 1С допускает с SQL Server 2008 [ИТС-КС разд. 5.5.2].

**Как включить:**

1. При установке — `/SQLSVCINSTANTFILEINIT=True` или флажок в мастере (SQL Server 2016+) [MS Learn].
2. После установки (Microsoft рекомендует выдавать право **SID службы** — тогда оно сохранится при смене учётной записи) [MS Learn]:
   - `secpol.msc` → Локальные политики → Назначение прав пользователя → «Выполнение задач по обслуживанию томов» (Perform volume maintenance tasks) → добавить `NT SERVICE\MSSQLSERVER`;
   - перезапустить службу SQL Server;
   - проверить журнал ошибок и `sys.dm_server_services` (раздел 3.7).

**Проверка «по ИТС».** Создать базу с файлом данных 5 ГБ и журналом 1 МБ: если создалась мгновенно — IFI работает; базу удалить [ИТС-мет 5904, 2019]. Под sysadmin, в тихое время (без IFI создание займёт заметное время и нагрузит диск):

```sql
DECLARE @t0 datetime2 = SYSDATETIME();
CREATE DATABASE ifi_test
  ON PRIMARY (NAME = N'ifi_test', FILENAME = N'D:\MSSQL\Data\ifi_test.mdf', SIZE = 5GB)
  LOG ON     (NAME = N'ifi_test_log', FILENAME = N'L:\MSSQL\Log\ifi_test_log.ldf', SIZE = 1MB);
SELECT DATEDIFF(millisecond, @t0, SYSDATETIME()) AS create_ms;   -- единицы-десятки мс = IFI работает [практика]
DROP DATABASE ifi_test;   -- удаляет только эту тестовую базу; проверьте имя перед запуском
```

**Безопасность.** Пока файл подключён к экземпляру, доступ к нему ограничен ACL (служба, её SID, локальные администраторы); риск — во отсоединённых файлах и копиях без строгих ACL: в них может остаться «чужое» удалённое содержимое диска. Microsoft всё равно рекомендует IFI включать — выгода обычно больше риска [MS Learn].

Признаки долгого обнуления без IFI: в журнале ошибок сообщения 5144 (авторост отменён по тайм-ауту) и 5145 (авторост занял N мс), ожидание `PREEMPTIVE_OS_WRITEFILEGATHER` [MS Learn].

### 4.3. Lock Pages in Memory (LPIM)

**Что это.** Право Windows «Блокировка страниц в памяти» (`SeLockMemoryPrivilege`) позволяет SQL Server выделять память через AWE так, что ОС не вытесняет её в файл подкачки; память закреплена, пока SQL Server сам её не освободит. В Standard и выше LPIM включается автоматически, как только у учётной записи службы есть это право (флаг 845 с SQL Server 2012 не нужен); динамическое управление памятью SQL Server при этом продолжает работать [MS Learn].

**Позиция 1С:** установить право учётной записи службы SQL Server, **но если сервер 1С установлен вместе с SQL Server, эту настройку производить не нужно** [ИТС-мет 5904, 2019].

**Позиция Microsoft:** использовать LPIM, когда есть признаки вытеснения процесса `sqlservr` — сообщение 17890 «A significant part of sql server process memory has been paged out…»; при LPIM обязательно задать конкретный `max server memory`, иначе возможна нестабильность системы [MS Learn].

| Ситуация | LPIM | Почему |
|---|---|---|
| Сервер 1С и SQL Server на одной машине | **нет** | [ИТС-мет 5904, 2019]; рабочие процессы 1С расходуют память непредсказуемо, закреплённый буферный пул оставит им меньше и спровоцирует подкачку у 1С [практика] |
| Выделенный сервер SQL, есть 17890 в журнале | да, вместе с `max server memory` | [MS Learn] |
| Выделенный сервер SQL, признаков вытеснения нет | по желанию: ИТС рекомендует, Microsoft — «когда есть признаки» | [ИТС-мет 5904]; [MS Learn] |
| ВМ с динамической памятью гипервизора | осторожно; сначала `min server memory` и резервирование памяти ВМ | [MS Learn]; [практика] |

**Как включить** [MS Learn]: `gpedit.msc` → Конфигурация компьютера → Конфигурация Windows → Параметры безопасности → Локальные политики → Назначение прав пользователя → «Блокировка страниц в памяти» (Lock pages in memory) → добавить SID службы `NT SERVICE\MSSQLSERVER` (Microsoft рекомендует именно SID) → перезапуск экземпляра. В SQL Server 2019+ право можно выдать и через Configuration Manager [MS Learn] ⚠ (пункт интерфейса в прочитанных текстах не показан).

**Проверка** [MS Learn]:

```sql
SELECT sql_memory_model_desc FROM sys.dm_os_sys_info;   -- CONVENTIONAL = нет, LOCK_PAGES = есть, LARGE_PAGES = + флаг 834
SELECT osn.node_id, omn.locked_page_allocations_kb
FROM sys.dm_os_memory_nodes AS omn
JOIN sys.dm_os_nodes AS osn ON omn.memory_node_id = osn.memory_node_id
WHERE osn.node_state_desc <> N'ONLINE DAC';              -- ненулевое = память закреплена
```

Флаг 834 (крупные страницы) — только для выделенных серверов, только при запуске, может не дать службе стартовать при фрагментации памяти [MS Learn]; для 1С не нужен [практика].

### 4.4. Учётные записи для 1С (кратко)

- Пользователь, от имени которого сервер 1С обращается к SQL Server, — член `processadmin` или `sysadmin` [ИТС-КС разд. 3.2.3; ИТС-адм разд. 5.2.1.3.2]; `sa` либо владелец базы с чтением `master` и полным доступом к `tempdb` [ИТС-адм разд. 5.2.1.3.2]; для каждой ИБ — свой пользователь СУБД [ИТС-КС прил. 3, разд. 3.7]; чек-лист: логин на каждую базу, роли `public`, `dbcreator` [ИТС-мет 5904, 2019].
- Пустые имя и пароль в свойствах ИБ = подключение по Windows-аутентификации от имени пользователя рабочего процесса `rphost` [ИТС-адм разд. 5.2.1.3.2].
- Скрипты создания логинов, проверка ролей, сценарии «базу создаёт 1С» / «базу создаёт администратор» — `mssql/03-…`.

## 5. Сортировка (collation)

### 5.1. Что говорит 1С

- В прочитанных текстах ИТС 8.3.27 («Клиент-серверный вариант», «Руководство администратора», «Руководство разработчика», методические статьи по MS SQL) **требования к сортировке экземпляра SQL Server нет** ⚠. Для MS SQL есть одна оговорка: если в региональных настройках ИБ страна «Казахстан», казахский порядок сортировки в базе не используется — используется тот же, что для страны «Россия»; в тексте ИТС он записан как `Cyrillic_Generic_CI_AS` [ИТС-разр прил. 8, разд. 8.4] — у Microsoft такого имени нет, есть `Cyrillic_General_CI_AS` [MS Learn], так что в ИТС, по-видимому, опечатка ⚠.
- Явных указаний, с какой сортировкой платформа создаёт базу (`CREATE DATABASE … COLLATE …`) и от чего это зависит, в ИТС нет ⚠. Без `COLLATE` новая база получает сортировку экземпляра [MS Learn].
- Региональные установки ИБ (язык/страна) влияют на порядок сортировки строк; для PostgreSQL язык существующей ИБ можно сменить только на такой, которому соответствует та же сортировка СУБД, для Db2 смена не поддерживается; для MS SQL ограничений не названо [ИТС-адм разд. 6.5]. Из этого можно заключить, что сортировка базы СУБД связана с языком ИБ, но как именно платформа делает это на MS SQL, не описано ⚠.

### 5.2. Как сортировку выбирает установщик

Сортировка экземпляра задаётся при установке и по умолчанию берётся из **локали ОС**; для совместимости выбирается самая старая версия сортировки для этой локали, поэтому умолчание «не всегда рекомендуемое»; сортировка экземпляра становится сортировкой системных баз и всех новых пользовательских баз [MS Learn]:

| Локаль Windows | Сортировка по умолчанию [MS Learn] |
|---|---|
| Русский (Россия) | `Cyrillic_General_CI_AS` |
| Узбекский (кириллица) | `Cyrillic_General_CI_AS` |
| Узбекский (латиница) | `Uzbek_Latin_90_CI_AS` |
| Казахский | `Kazakh_90_CI_AS` |
| Белорусский, киргизский, таджикский, монгольский, татарский | `Cyrillic_General_CI_AS` |
| Английский (США) | `SQL_Latin1_General_CP1_CI_AS` |

На английской или узбекской (латиница) Windows без явного `/SQLCOLLATION` сортировка будет не кириллической [MS Learn].

### 5.3. Почему важно совпадение сортировки экземпляра и базы

- `tempdb` всегда работает в сортировке экземпляра, сменить её нельзя; временные таблицы хранятся в `tempdb`; запросы, сравнивающие строки пользовательской базы и временной таблицы, могут падать из-за конфликта сортировок, если сортировки базы и экземпляра различаются [MS Learn].
- Платформа 1С активно использует временные таблицы [ИТС-мет 2374, 2008]; указывает ли она `COLLATE` при их создании — не описано ⚠. Поэтому правило [практика]: **сортировка экземпляра = сортировке баз 1С на нём.** Для русских конфигураций — `Cyrillic_General_CI_AS`.
- **Международные конфигурации (WE).** Какую сортировку платформа даст базе с английской локалью ИБ, в ИТС не сказано ⚠. Порядок [практика]: на тестовом экземпляре создать из 1С пустую ИБ с нужной локалью, посмотреть `collation_name` в `sys.databases` и ставить рабочий экземпляр с той же сортировкой. Смешивать на одном экземпляре базы с разными сортировками не стоит.
- Версионные (`…_100_…`), `_SC`, `_UTF8`-сортировки для баз 1С без проверки не выбирать ⚠: поддержку платформой ИТС не описывает.

### 5.4. Проверка

```sql
SELECT SERVERPROPERTY('Collation') AS server_collation;                  -- [MS Learn]
SELECT name, collation_name FROM sys.databases ORDER BY name;           -- сортировка каждой базы
SELECT COLLATIONPROPERTY(N'Cyrillic_General_CI_AS', 'CodePage') AS code_page;  -- 1251 ожидается [практика] ⚠
SELECT name, description FROM sys.fn_helpcollations() WHERE name LIKE N'Cyrillic%';  -- доступные сортировки [MS Learn]
```

### 5.5. Если сортировка экземпляра выбрана неверно

Сменить сортировку экземпляра можно только **пересборкой системных баз** — `master`, `model`, `msdb`, `tempdb` удаляются и создаются заново; все логины, задания Agent, связанные серверы, настройки `sp_configure`, изменения `model` теряются; существующие пользовательские базы сортировку не меняют [MS Learn]. Сценарий Microsoft: сохранить скрипты всех объектов, выгрузить данные, удалить пользовательские базы, пересобрать `master` с новой сортировкой, создать базы и загрузить данные [MS Learn].

**Перед этим:** полные копии всех пользовательских баз и `master`, `model`, `msdb`; скрипты логинов и заданий; проверить наличие шаблонов системных баз в `…\MSSQL<xx>.MSSQLSERVER\MSSQL\Binn\Templates` [MS Learn]. На свежеустановленном экземпляре без баз проще переустановить [практика].

```bat
:: cmd от имени администратора, из каталога дистрибутива той же версии; УНИЧТОЖАЕТ системные базы
setup /QUIET /ACTION=REBUILDDATABASE /INSTANCENAME=MSSQLSERVER /SQLSYSADMINACCOUNTS="CORP\sql-admins" /SAPWD="<пароль>" /SQLCOLLATION=Cyrillic_General_CI_AS
```

Число файлов `tempdb` при пересборке не сохраняется — передайте `/SQLTEMPDBFILECOUNT` заново [MS Learn]. Для базы 1С с «чужой» сортировкой путь [практика]: выгрузить ИБ в `.dt` или перенести `ibcmd infobase replicate` в новую базу, созданную на экземпляре с правильной сортировкой (`../1c-windows/02-…`). На Linux — `mssql-conf set-collation` (раздел 15).

## 6. Режим проверки подлинности и вход `sa`

- **Смешанный режим** («SQL Server and Windows Authentication») — включить [ИТС-мет 5904, 2019]; SQL-аутентификация гибче, позволяет разные права на разные базы [ИТС-мет 2926, 2008]. Без `/SECURITYMODE=SQL` setup оставляет только Windows-аутентификацию [MS Learn].
- **Windows-аутентификация для 1С** возможна: пустые имя и пароль пользователя БД в свойствах ИБ → вход от имени учётной записи `rphost` [ИТС-адм разд. 5.2.1.3.2]; минус — одинаковые права на все базы кластера [ИТС-мет 2926, 2008].
- **`sa`:** если при установке выбран режим только Windows, `sa` отключён; при последующем переходе на смешанный режим он остаётся отключённым; не включать `sa` без необходимости — это известная цель атак [MS Learn]. Для 1С `sa` не нужен — у каждой ИБ свой логин [практика].

Сменить режим после установки: SSMS → свойства сервера → Security → Server authentication → перезапуск службы (и Agent) [MS Learn]. Скриптом (под sysadmin; меняет реестр, перезапуск обязателен) [MS Learn]:

```sql
-- смешанный режим (2) ; Windows-only — значение 1
EXECUTE xp_instance_regwrite N'HKEY_LOCAL_MACHINE', N'Software\Microsoft\MSSQLServer\MSSQLServer',
        N'LoginMode', REG_DWORD, 2;
-- отключить sa, если не нужен (после проверки, что вы входите иначе — членом CORP\sql-admins)
ALTER LOGIN sa DISABLE;
-- проверка после перезапуска
SELECT SERVERPROPERTY('IsIntegratedSecurityOnly') AS windows_only;      -- 0 = смешанный
SELECT name, is_disabled FROM sys.server_principals WHERE name = N'sa';
```

Перед `ALTER LOGIN sa DISABLE` убедитесь, что в `sysadmin` есть рабочая Windows-группа, иначе можно потерять административный доступ (восстановление — однопользовательский режим `-m`) [MS Learn — параметры запуска; практика].

## 7. Сеть: протоколы, порты, брандмауэр, шифрование

### 7.1. Протоколы и конфликт Shared Memory с оптимизированной реструктуризацией

Рекомендации ИТС [ИТС-мет 5904, 2019]: включить TCP/IP; если сервер 1С на той же машине — включить Shared Memory; Named Pipes — отключить. Старый совет «TCP/IP первой строкой, Named Pipes второй» и утилиты `svrnetcn.exe`/`cliconfg.exe` [ИТС-мет 2926, 2008] относятся к SQL Server 2000 и устарели [практика].

Но:

- **Оптимизированная реструктуризация (`UpdateDBCfg=v2` в `conf.cfg`) с MS SQL работает только при подключении сервера 1С к СУБД по TCP/IP; при Shared Memory и Named Pipes она не поддерживается.** Умолчание `UpdateDBCfg` — `v1` [ИТС-адм прил. 3, разд. 3.17.23]. Для неё же нужна Java на серверах кластера [ИТС-КС разд. 1.3.1].
- Префикс `lpc:` в имени сервера СУБД явно включает Shared Memory (`lpc:Server/instance`) [ИТС-адм разд. 5.2.1.3.2]; `lpc` — обозначение Shared Memory и у Microsoft (`sqlcmd -S lpc:…`) [MS Learn].
- Без префикса клиент выбирает протокол сам: у OLE DB Driver 19.1+ порядок по умолчанию — `sm tcp np` (сначала Shared Memory), он хранится в `HKLM\SOFTWARE\Microsoft\MSSQLServer\Client\SNI19.0\ProtocolOrder` [MS Learn]. То есть **на совмещённом сервере 1С подключится по Shared Memory даже без `lpc:`**, если протокол включён на сервере. Для драйвера 18 порядок по умолчанию в прочитанных текстах не описан ⚠.

Выход для совмещённого сервера, где нужна `v2` [практика] ⚠ (на стенде проверить `net_transport`):

1. Отключить Shared Memory на сервере SQL (Configuration Manager → SQL Server Network Configuration → Protocols for MSSQLSERVER → Shared Memory → Disabled, перезапуск службы) — локальные подключения пойдут по TCP/IP; **или**
2. указать в свойствах ИБ сервер с префиксом протокола `tcp:sql01` — принимает ли платформа префикс `tcp:`, ИТС не описывает ⚠ (`lpc:` — описан).

Если `v2` не используется, Shared Memory на совмещённом сервере оставить — рекомендация ИТС [ИТС-мет 5904].

Проверка, каким протоколом и с шифрованием ли подключены рабочие процессы 1С (под sysadmin) [MS Learn — столбцы `sys.dm_exec_connections`]:

```sql
SELECT c.session_id, c.net_transport, c.encrypt_option, c.auth_scheme, c.client_net_address,
       s.program_name, s.login_name
FROM sys.dm_exec_connections AS c
JOIN sys.dm_exec_sessions    AS s ON s.session_id = c.session_id
WHERE s.is_user_process = 1
ORDER BY s.login_name;      -- net_transport: TCP / Shared memory / Named pipe
```

Протоколы включают и выключают в SQL Server Configuration Manager; при установке — `/TCPENABLED=1 /NPENABLED=0` [MS Learn]. Изменения протоколов вступают в силу после перезапуска службы [практика]. Текущие значения из реестра — запрос к `sys.dm_server_registry` по `SuperSocketNetLib` (раздел 3.7) [MS Learn].

### 7.2. Порты

| Что | Порт | Источник |
|---|---|---|
| Экземпляр по умолчанию | TCP 1433 | [MS Learn] |
| Именованный экземпляр | динамический (выбирается при каждом старте) или заданный администратором | [MS Learn] |
| SQL Server Browser | UDP 1434 | [MS Learn] |
| DAC | TCP 1434 у экземпляра по умолчанию (если занят — динамический, см. журнал ошибок); по умолчанию слушает только 127.0.0.1 | [MS Learn] |
| Service Broker, зеркалирование/группы доступности | 4022, 5022 — по договорённости, см. `sys.tcp_endpoints` | [MS Learn] |

**Статический порт для именованного экземпляра** [MS Learn]: Configuration Manager → SQL Server Network Configuration → Protocols for `<экземпляр>` → TCP/IP → вкладка IP Addresses → раздел **IPAll**: в «TCP Dynamic Ports» удалить `0`, в «TCP Port» указать номер → перезапуск службы. При «Listen All = Yes» используются только значения IPAll; при «No» — значения отдельных IPn и их флаг «Enabled» (по умолчанию «No»). Browser сообщает новый порт сразу после изменения реестра, а ядро начнёт слушать его только после перезапуска — перезапускайте сразу [MS Learn]. Смена порта 1433 на нестандартный надёжной защитой не считается [MS Learn].

### 7.3. Брандмауэр

Setup **не открывает** порты в брандмауэре Windows; подключения с других машин заработают только после правила [MS Learn]. Пустить к 1433 только рабочие серверы 1С и машины администраторов (PowerShell (админ); `New-NetFirewallRule` — [MS Learn], ограничение `-RemoteAddress` — [практика]):

```powershell
New-NetFirewallRule -DisplayName 'SQL Server 1433 (1C, admins)' -Direction Inbound -Protocol TCP `
  -LocalPort 1433 -RemoteAddress 10.10.0.21,10.10.0.22,10.10.0.50 -Action Allow -Profile Domain
# удалённый DAC (если включён remote admin connections) — только с машины администратора
New-NetFirewallRule -DisplayName 'SQL Server DAC 1434 (admins)' -Direction Inbound -Protocol TCP `
  -LocalPort 1434 -RemoteAddress 10.10.0.50 -Action Allow -Profile Domain
Get-NetFirewallRule -DisplayName 'SQL Server*' | Format-Table DisplayName, Enabled, Action   # проверка
```

Аналог через `netsh advfirewall firewall add rule name = SQLPort dir = in protocol = tcp action = allow localport = 1433 remoteip = localsubnet profile = DOMAIN` [MS Learn]. Для именованного экземпляра с динамическим портом Microsoft допускает правило на программу `sqlservr.exe` (`C:\Program Files\Microsoft SQL Server\MSSQL<версия>.<экземпляр>\MSSQL\Binn\sqlservr.exe`) и UDP 1434 для Browser [MS Learn]; статический порт прозрачнее [практика].

На рабочих серверах 1С — открыть их собственные порты (1540, 1541, 1560–1591 и т. д.) [ИТС-КС прил. 3, разд. 3.8] — это `../1c-windows/01-…`.

### 7.4. Шифрование соединений и сертификат

- Сервер SQL с сертификатом, выданным доменным или коммерческим УЦ: в SQL Server 2019+ сертификат устанавливается и назначается экземпляру в Configuration Manager (работает и для более старых экземпляров); для старых — вручную через MMC «Сертификаты (локальный компьютер)» с правом чтения закрытого ключа для учётной записи службы и выбором на вкладке Certificate в свойствах протоколов [MS Learn]. Без права чтения закрытого ключа служба может не стартовать [MS Learn].
- «Force Encryption = Yes» в свойствах протоколов экземпляра требует шифрования для всех клиентов [MS Learn]. Для 1С это имеет смысл только после того, как на всех рабочих серверах стоит драйвер, проверяющий сертификат, и сертификат доверенный (раздел 8) [практика].
- Требования к сертификату (имя хоста или FQDN в субъекте/SAN и т. д.) — [MS Learn, «Certificate requirements for SQL Server»]; подробно — `mssql/03-…`.
- Клиент `sqlcmd` из комплекта SQL Server 2025 по умолчанию требует шифрования (`-Nm`), в 2022 и раньше умолчание было `-No`; `-C` — доверять сертификату сервера без проверки [MS Learn].

## 8. Драйвер на рабочих серверах 1С

### 8.1. Что требует платформа

- Для работы с MS SQL Server требуется **Microsoft OLE DB Driver for SQL Server актуальной версии** или **SQL Server Native Client** for SQL Server 2005 и новее; наличие проверяется при создании ИБ, загрузке ИБ и обновлении конфигурации базы данных; версия Native Client должна быть не младше версии SQL Server [ИТС-КС разд. 1.5.4]. В ИТС эти требования (как и минимум SQL Server 2005) сформулированы для конфигураций с режимом совместимости выше «Версия 8.3.7» [ИТС-КС разд. 1.5.4]; на практике драйвер ставят всегда [практика]. Чек-лист 2016 года упоминает только Native Client [ИТС-мет 5899, 2016] — устарело [практика].
- Драйвер нужен **на каждом рабочем сервере кластера 1С** (там работают `rphost`), а также на машине, где запускаются `ibcmd`/`ibsrv` с MS SQL [ИТС-адм разд. 7.2 — автономный сервер на Windows]. На рабочих местах пользователей драйвер не нужен — клиентские приложения не обращаются к серверу баз данных напрямую, только через кластер [ИТС-КС разд. 2.1].
- **Как платформа выбирает провайдер.** При первом соединении с MS SQL перебираются провайдеры от соответствующего самой новой версии SQL Server к старым до первого успешного; событие техжурнала `DBMSSQLCONN`, в 8.3.27 — свойства `hResultOLEDB`, `hResultNC2005`, `hResultNC2008`, `hResult2012` (коды возврата для OLE DB и Native Client 2005/2008/2012) [ИТС-адм прил. 3, разд. 3.24]. В 8.5.1 добавились `hResultMSOLEDBSQL19`, `hResultMSOLEDBSQL`, `hResultNC2012` — платформа 8.5 знает OLE DB Driver 19 [`../its-docs/otlichiya-8.5.1-ot-8.3.27.md`, п. 16]. Какой мажорной версии соответствует `hResultOLEDB` в 8.3.27 (18 или 19), в тексте не сказано ⚠.

### 8.2. OLE DB Driver 18 и 19: главное различие — шифрование

[MS Learn, «Major version differences in MSOLEDBSQL»; «Registry settings»]:

| | OLE DB Driver 18 (`MSOLEDBSQL`) | OLE DB Driver 19 (`MSOLEDBSQL19`) |
|---|---|---|
| `Encrypt` по умолчанию | `no` (без шифрования, если сервер не требует) | **`Mandatory`** (шифрование обязательно) |
| Значения `Encrypt` | `no`/`yes` | `no`/`yes`/`true`/`false`/`Optional`/`Mandatory`/`Strict` |
| Проверка сертификата | при `Encrypt=no` пропускается, даже если сервер форсирует шифрование | оценивается при любом шифровании |
| `Strict` (TDS 8.0) | нет | да, нужен SQL Server 2022+; TLS 1.3 — с 19.2.0 |
| Установка рядом | да | да (side-by-side с 18) |
| Ключ реестра | `HKLM\SOFTWARE\Microsoft\MSSQLServer\Client\SNI18.0` | `…\SNI19.0` |
| Последний выпуск на 20.10.2026 | **18.7.6** (09.10.2026) | **19.4.3** (09.10.2026) |

- Клиент 19 с настройками по умолчанию **не подключится** к серверу, который использует недоверенный (например, самоподписанный) сертификат; варианты Microsoft — доверенный сертификат на сервере (рекомендуется), `TrustServerCertificate=yes` (только для разработки) или `Encrypt=Optional` (поведение 18, менее безопасно) [MS Learn].
- В реестре драйвера: `{база}\GeneralFlags\Flag1` = «Force Protocol Encryption» (`0` Optional, `1` Mandatory, `2` Strict), `{база}\GeneralFlags\Flag2` = «Trust Server Certificate» (`0`/`1`); **драйвер всегда берёт более безопасное** из реестра и строки подключения [MS Learn]. Подтверждено 20.10.2026 (MS Learn, «Registry settings» OLE DB Driver): реестром можно ужесточить, но не ослабить то, что запросило приложение, — сертификат проверяется, если проверку включает хотя бы одна из двух настроек (реестр или строка подключения).
- Установщик 19 до версии 19.4.1 мог выставить в реестре `TrustServerCertificate` = `no` на машинах, где раньше стоял 18; исправлено в 19.4.1 [MS Learn].
- В 19.1+ в реестре же настраиваются порядок протоколов (`ProtocolOrder`, умолчание `sm tcp np`), TCP Keep-Alive (`tcp\Property2`, умолчание 30 000 мс) и интервал Keep-Alive (`tcp\Property3`, 1000 мс) [MS Learn].

**Как 1С задаёт `Encrypt` и `TrustServerCertificate` при подключении, ИТС не описывает** ⚠. Практический порядок [практика]:

1. Платформа 8.3.x — **OLE DB Driver 18 последней версии** (18.7.6): поведение без шифрования по умолчанию, как у Native Client.
2. Платформа 8.5.x — можно 19, но тогда на SQL Server нужен **доверенный сертификат** (доменный УЦ, имя сервера в сертификате); проверить, какой провайдер выбран (`DBMSSQLCONN`), и что соединения зашифрованы (`encrypt_option` в 7.1). Сверить с `1cv8upd` своей версии ⚠.
3. Ставить 18 и 19 рядом допустимо [MS Learn]; какой выберет платформа — по `DBMSSQLCONN` ⚠.

### 8.3. Native Client

- SQL Server Native Client (SNAC, `SQLNCLI`/`SQLNCLI11`) не поставляется с SQL Server 2022 и новее и с SSMS 19 и новее; последняя версия — из SQL Server 2012; для новых разработок Microsoft его не рекомендует [MS Learn]. Для SNAC, поставляемого с ядром 2012–2019, действует исключение жизненного цикла поддержки [MS Learn].
- ИТС допускает Native Client, но с условием «версия не младше версии SQL Server» [ИТС-КС разд. 1.5.4] — для SQL Server 2014+ это фактически означает **ставить OLE DB Driver** [практика].
- Префикс `lpc:` в ИТС описан с оговоркой «если установлен Native Client» [ИТС-адм разд. 5.2.1.3.2]; Shared Memory поддерживает и OLE DB Driver (`sm` в порядке протоколов) [MS Learn].

### 8.4. Установка и проверка на рабочем сервере 1С

Дистрибутив — со страницы релизов OLE DB Driver на learn.microsoft.com (x64 для 64-разрядного кластера; разрядность драйвера должна совпадать с разрядностью `rphost`) [MS Learn — ссылки на установщики; разрядность — практика]. Установка — `msiexec`, например (cmd от имени администратора). Уточнено 20.10.2026 по MS Learn («Installing OLE DB Driver for SQL Server»): при `/qn`, `/qb`, `/qr` или `/passive` обязательно свойство `IACCEPTMSOLEDBSQLLICENSETERMS=YES` (заглавными буквами); x64-пакет ставит и 64-, и 32-разрядный драйвер; начиная с 19.3 для драйвера 19 нужен Microsoft Visual C++ Redistributable — для x64-пакета обе редакции, x86 и x64; драйвер ставится рядом с прежними провайдерами OLE DB:

```bat
msiexec /i msoledbsql.msi /qn IACCEPTMSOLEDBSQLLICENSETERMS=YES /l*v C:\Temp\msoledbsql_install.log
```

Проверка (PowerShell (админ) на сервере 1С) [практика]:

```powershell
# установленные драйверы
Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Where-Object DisplayName -match 'OLE DB Driver|Native Client' | Select-Object DisplayName, DisplayVersion
# зарегистрированные OLE DB-провайдеры (64-разрядный PowerShell видит 64-разрядные)
(New-Object System.Data.OleDb.OleDbEnumerator).GetElements() |
  Where-Object SOURCES_NAME -match 'MSOLEDBSQL|SQLNCLI|SQLOLEDB' | Select-Object SOURCES_NAME, SOURCES_DESCRIPTION
# реестр драйвера 19: принудительное шифрование и доверие сертификату [MS Learn — пути]
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\MSSQLServer\Client\SNI19.0\GeneralFlags\Flag1','HKLM:\SOFTWARE\Microsoft\MSSQLServer\Client\SNI19.0\GeneralFlags\Flag2' -ErrorAction SilentlyContinue | Select-Object PSPath, Value
```

Какой провайдер выбрала платформа — `logcfg.xml` на рабочем сервере с событием `DBMSSQLCONN` и всеми свойствами (`<property name="all"/>`) [ИТС-адм прил. 3, разд. 3.24]; пример файла — `../1c-windows/02-…`, раздел 3.5; включать на время диагностики, файл потом убрать [практика].

**Устарело:** проверка `sqloledb.dll` и `ntwdblib.dll`, права `USER1CV8SERVER` на каталоги OLE DB [ИТС-мет 2926, 2008] и пункт «установить MDAC» [ИТС-мет 5908, 2022] относятся к Windows 2000/2003 и встроенному в Windows провайдеру `SQLOLEDB`; на современной Windows ошибка «Компоненты OLE DB провайдера не найдены» лечится установкой OLE DB Driver [практика].

## 9. Параметры экземпляра (`sp_configure`)

### 9.1. Как работает `sp_configure`

- Изменение применяется только после `RECONFIGURE` (в отдельных случаях — `RECONFIGURE WITH OVERRIDE`); признак применения — столбец `value_in_use` в `sys.configurations` [MS Learn].
- «Расширенные» параметры (A) видны и меняются только после `show advanced options = 1`; параметры с пометкой RR требуют перезапуска ядра; SC — самонастраивающиеся [MS Learn].
- Читать `sp_configure` может любой; менять — нужен `ALTER SETTINGS`, он есть у `sysadmin` и `serveradmin` [MS Learn].
- Все параметры раздела, кроме отмеченных, **динамические** — применяются без перезапуска [MS Learn].

### 9.2. Сводная таблица для экземпляра 1С

| Параметр | Умолчание [MS Learn] | 1С / ИТС | Microsoft | Итог для 1С |
|---|---|---|---|---|
| `max server memory (MB)` (A) | 2 147 483 647 (без предела) | при совмещении — уменьшить на долю 1С [5904, 2019] | задавать всегда; ~75 % доступной памяти; формула ниже | **задать** (9.3) |
| `min server memory (MB)` (A) | 0 | — | 0; в ВМ — задать | 0, в ВМ — часть рабочего объёма |
| `max degree of parallelism` (A) | 0 (все процессоры до 64) | **1** [5904, 2019; 6008, 2023; 5945, 2018; 2379, 2008] | ≤ 8 и по NUMA (9.4) | **1**; на реструктуризацию — 0 |
| `cost threshold for parallelism` (A) | 5 | — | 5 — «стартовая точка, не рекомендация» | при `MAXDOP = 1` не действует; при `MAXDOP > 1` — повысить (9.5) |
| `optimize for ad hoc workloads` (A) | 0 | — | включать при массе одноразовых планов | 1 после проверки (9.6) [практика] |
| `backup compression default` | 0 | — | — (CPU растёт) | 1, кроме Express (9.7) |
| `backup checksum default` | 0 | — | — | 1 [практика] |
| `remote admin connections` | 0 | **1** [5904, 2019; 6008, 2023] | DAC по сети только после включения | **1** |
| `blocked process threshold (s)` (A) | 0 (отчёты не формируются); 5–86 400 | — | — | 10–20 при расследованиях [практика] (9.9) |
| `max worker threads` (0, авто), `priority boost` (0, RR), `lightweight pooling` (0, RR), `locks` (0, RR), `fill factor (%)` (0, RR), `network packet size (B)` (4096), `xp_cmdshell` (0) | в скобках; RR — нужен перезапуск | — | `max worker threads`: рекомендованный максимум 2048 | не трогать [практика]; заполнение индексов — в регламенте (`mssql/05-…`) |
| `Agent XPs`, `Database Mail XPs` (A) | 0 | Database Mail и операторы — настроить [5904, 2019] | — | включаются при настройке Agent/почты |

### 9.3. Память

**Расчёт Microsoft для одного экземпляра** [MS Learn]: из всей памяти ОС вычесть память потоков вне `max server memory` (размер стека × рассчитанное `max worker threads`), затем ещё 25 % на прочие выделения вне буферного пула (буферы копирования, расширенные процедуры, `sp_OA`, провайдеры связанных серверов); остаток — `max server memory`. Таблица умолчаний там же: рекомендовано «75 % доступной памяти, не занятой другими процессами» [MS Learn]. С SQL Server 2019 установщик сам предлагает значение (`/USESQLRECOMMENDEDMEMORYLIMITS`) [MS Learn].

**При совмещении с сервером 1С** «верхний порог памяти необходимо уменьшить на величину, достаточную для работы сервера 1С» [ИТС-мет 5904, 2019]. Сколько это, ИТС в статье не считает ⚠. Оценка [практика]: максимум суммарной памяти процессов `ragent`/`rmngr`/`rphost` за рабочий день (счётчик «Процесс → Рабочий набор») или заданный потолок — параметры рабочего сервера «Критический объём памяти процессов» и «Временно допустимый объём памяти процессов» [ИТС-КС разд. 5.2.6] — плюс 4–8 ГБ на ОС; пересматривать при росте числа пользователей.

| Сервер | ОЗУ | Без 1С на машине | С сервером 1С на машине |
|---|---|---|---|
| Малый | 32 ГБ | 26 624 (26 ГБ) | 16 384 (16 ГБ), если 1С берёт ≤ 10 ГБ |
| Средний | 64 ГБ | 55 296 (54 ГБ) | 36 864 (36 ГБ), если 1С берёт ≤ 20 ГБ |
| Крупный | 128 ГБ | 110 592 (108 ГБ) | разносить на разные машины [ИТС-мет 2926; практика] |

Значения таблицы — ориентиры [практика]; Standard 2022 сам ограничивает буферный пул 128 ГБ (2025 — 256 ГБ) (`mssql/01-…`).

Правила Microsoft [MS Learn]:

- `max server memory` ограничивает только буферный пул; не ставить `min` и `max` равными или почти равными; слишком малое значение (минимум — 128 МБ) может не дать службе стартовать — тогда запуск с параметром `-f` (минимальная конфигурация) и исправление.
- `min server memory` SQL Server не захватывает при старте, но, набрав этот объём, ниже не отдаёт; в ВМ — задавать, чтобы гипервизор не отбирал буферный пул сверх допустимого.

Под sysadmin (без перезапуска):

```sql
EXECUTE sp_configure N'show advanced options', 1;  RECONFIGURE;
EXECUTE sp_configure N'max server memory (MB)', 36864;  RECONFIGURE;   -- пример: 64 ГБ, сервер 1С на той же машине
EXECUTE sp_configure N'min server memory (MB)', 0;      RECONFIGURE;
SELECT name, value, value_in_use FROM sys.configurations
WHERE name IN (N'max server memory (MB)', N'min server memory (MB)');   -- проверка [MS Learn]
-- сколько память SQL Server занимает сейчас и есть ли нехватка [MS Learn: sys.dm_os_process_memory]
SELECT physical_memory_in_use_kb / 1024 AS in_use_mb, locked_page_allocations_kb / 1024 AS locked_mb,
       memory_utilization_percentage, process_physical_memory_low, process_virtual_memory_low
FROM sys.dm_os_process_memory;
```

Устарело: `awe enabled`, ключи `/3GB`, `/PAE` в `boot.ini` [ИТС-мет 2371, 2008] — для 32-разрядных SQL Server 2000/2005; флаг 845 для LPIM в Standard не нужен с 2012 [MS Learn].

### 9.4. `max degree of parallelism` (MAXDOP)

**1С — `1`.** Причины [ИТС-мет 5945, 2018; 6008, 2023; 2379, 2008; 5834, 2015]: один тяжёлый запрос с неудачным планом (например, отчёт с полем составного типа «через точку» и RLS) при параллельном плане занимает процессоры у всех; время одного и того же запроса «скачет» — то параллельный план, то нет; ожидания `CXPACKET` (координатор ждёт отстающие потоки); изредка — внутризапросные взаимоблокировки «Intra-query parallelism caused your server command … to deadlock». `MAXDOP = 1` ограничивает параллелизм внутри одного запроса, разные запросы по-прежнему выполняются параллельно [ИТС-мет 2379, 2008]. Значение больше 1 полезно в системах с небольшим числом больших запросов (OLAP) [ИТС-мет 6008, 2023].

**Microsoft (2016+)** [MS Learn]: один узел NUMA и ≤ 8 логических процессоров — не больше числа процессоров; > 8 — 8; несколько узлов NUMA и ≤ 16 логических на узел — не больше их числа на узле; > 16 — половина на узел, но не больше 16. `0` (умолчание) — до 64 процессоров, «не рекомендуется в большинстве случаев». Ограничение действует на задачу (task), а не на запрос. Установщик 2019+ сам ставит значение по этим правилам, если не указать `/SQLMAXDOP` — для 1С **указать `1` явно** [MS Learn; ИТС-мет 5904].

Где ещё задаётся MAXDOP (уровни переопределения) [MS Learn]:

| Уровень | Как | Для 1С |
|---|---|---|
| Экземпляр | `sp_configure 'max degree of parallelism'` | `1` |
| База (2016+) | `ALTER DATABASE SCOPED CONFIGURATION SET MAXDOP = n` (0 — брать значение экземпляра) | если экземпляр общий с не-1С базами: экземпляр по их требованиям, а у баз 1С — `1` |
| Индекс | `WITH (MAXDOP = n)` в `CREATE/ALTER INDEX` (не сохраняется в метаданных) | в регламентных заданиях перестроения (`mssql/05-…`) |
| `DBCC CHECKDB` | подчиняется MAXDOP; с 2014 SP2 — опция `MAXDOP`; флаг 2528 отключает параллельную проверку | `mssql/05-…` |

С SQL Server 2022 есть DOP Feedback — автоматическая подстройка параллелизма повторяющихся запросов (часть Intelligent Query Processing) [MS Learn]; при `MAXDOP = 1` она неактуальна [практика].

**Реструктуризация.** Новый механизм реструктуризации (8.3.11+) выполняет массовые `INSERT`/`UPDATE`, пересоздание индексов и пересчёт итогов — это хорошо параллелится; на время обновления конфигурации ставят `0`, следят за ожиданиями и дисками, затем возвращают `1`; в замерах 1С ускорение этапов — 18–65 % [ИТС-мет 5945, 2018]. Изменение действует сразу, без перезапуска [ИТС-мет 5945; MS Learn].

```sql
-- под sysadmin: перед обновлением конфигурации БД (параметр общий для ВСЕХ баз экземпляра)
EXECUTE sp_configure N'show advanced options', 1;  RECONFIGURE;
EXECUTE sp_configure N'max degree of parallelism', 0;  RECONFIGURE;
-- ... обновление конфигурации базы данных в 1С ...
EXECUTE sp_configure N'max degree of parallelism', 1;  RECONFIGURE;   -- сразу после
-- контроль ожиданий параллелизма во время реструктуризации [ИТС-мет 5945, 2018]
SELECT wait_type, waiting_tasks_count, wait_time_ms
FROM sys.dm_os_wait_stats WHERE wait_type IN (N'CXPACKET', N'CXCONSUMER');
```

Если на экземпляре несколько баз 1С, а обновляется одна, параллелизм можно разрешить только ей: у экземпляра остаётся `1`, в базе временно `USE [buh]; ALTER DATABASE SCOPED CONFIGURATION SET MAXDOP = 8;` (например, «ядер / 2» — обычная рекомендация, по [ИТС-мет 5945, 2018]), после — `SET MAXDOP = 0` (то есть «как у экземпляра») [MS Learn — семантика; сценарий — практика] ⚠. ИТС для реструктуризации советует именно `0` на уровне экземпляра — выбор оставляется СУБД.

### 9.5. `cost threshold for parallelism`

Порог «стоимости» (оценочной, а не времени выполнения), выше которого оптимизатор рассматривает параллельные планы; 0–32 767, умолчание 5 — «стартовая точка, а не рекомендация»; повышение помогает держать мелкие OLTP-запросы последовательными; менять небольшими шагами и наблюдать полный бизнес-цикл [MS Learn]. **Не действует**, если у SQL Server один логический процессор или `max degree of parallelism = 1` [MS Learn] — то есть на типовом экземпляре 1С он не важен.

Если для экземпляра выбран `MAXDOP > 1` (общий сервер, OLAP-нагрузка), поднять порог; часто начинают с 25–50 [практика] ⚠. Признаки по Microsoft [MS Learn]: слишком низкий — много лёгких параллельных запросов, в Query Store много планов с `is_parallel_plan = 1`, в ожиданиях лидируют `CXPACKET`/`CXCONSUMER`, бывают `THREADPOOL`; слишком высокий — тяжёлые запросы не параллелятся, лидирует `SOS_SCHEDULER_YIELD`.

### 9.6. `optimize for ad hoc workloads`

При `1` для пакета, скомпилированного впервые, в кеш кладётся только заглушка плана (`Compiled Plan Stub`), полный план — при повторном вызове; уменьшает память кеша при множестве одноразовых пакетов; действует только на новые планы; минус — планы одноразовых запросов нельзя посмотреть [MS Learn]. С SQL Server 2019 то же можно включить для одной базы: `ALTER DATABASE SCOPED CONFIGURATION SET OPTIMIZE_FOR_AD_HOC_WORKLOADS = ON` [MS Learn].

ИТС этот параметр не упоминает ⚠. Для 1С он полезен, если кеш планов забит одноразовыми ad hoc-планами [практика]; проверка доли (под sysadmin) [MS Learn — столбцы DMV; запрос — практика]:

```sql
SELECT objtype, cacheobjtype,
       COUNT(*)                                        AS plans,
       SUM(CASE WHEN usecounts = 1 THEN 1 ELSE 0 END)  AS single_use_plans,
       SUM(CAST(size_in_bytes AS bigint)) / 1048576    AS size_mb,
       SUM(CASE WHEN usecounts = 1 THEN CAST(size_in_bytes AS bigint) ELSE 0 END) / 1048576 AS single_use_mb
FROM sys.dm_exec_cached_plans
GROUP BY objtype, cacheobjtype
ORDER BY size_mb DESC;
-- если single_use_mb у Adhoc — значимая доля памяти кеша:
EXECUTE sp_configure N'show advanced options', 1;  RECONFIGURE;
EXECUTE sp_configure N'optimize for ad hoc workloads', 1;  RECONFIGURE;
```

Флаг 8032 (увеличенные лимиты кешей, как в SQL Server 2005 RTM) — только если `optimize for ad hoc workloads` не помог и это подтверждено; может отнять память у буферного пула [MS Learn].

### 9.7. Сжатие и контрольные суммы резервных копий

- `backup compression default`: `0` — без сжатия (умолчание), `1` — сжимать; доступно не во всех редакциях (в Express нет — `mssql/01-…`); сжатие заметно нагружает CPU [MS Learn]. Можно переопределить в каждой команде `BACKUP` [MS Learn].
- `backup compression algorithm` (2022+): `1` — MS_XPRESS (умолчание), `2` — Intel QAT, `3` — ZSTD (2025+; у ZSTD есть известная проблема при установке значения — см. known issues 2025) [MS Learn].
- `backup checksum default`: `1` — проверять контрольные суммы страниц во всех операциях копирования и восстановления, в том числе из планов обслуживания, где опции `CHECKSUM` нет; при ошибке копирование останавливается с ошибкой 3043 [MS Learn]. Включать [практика]; стратегия копий — `mssql/04-…`.

```sql
EXECUTE sp_configure N'backup compression default', 1;  RECONFIGURE;   -- не в Express
EXECUTE sp_configure N'backup checksum default', 1;     RECONFIGURE;
```

### 9.8. Выделенное административное подключение (DAC)

DAC — отдельные зарезервированные ресурсы для диагностики, когда сервер перегружен и обычные подключения не проходят [MS Learn; ИТС-мет 6008, 2023]. По умолчанию доступно только с самого сервера и слушает 127.0.0.1, TCP 1434 (если порт занят — динамический, см. журнал ошибок) [MS Learn]. Включить сетевой DAC — в чек-листе 1С [ИТС-мет 5904, 2019]:

```sql
EXECUTE sp_configure N'remote admin connections', 1;  RECONFIGURE;    -- [MS Learn; ИТС-мет 5904]
```

Подключение: SSMS, «Имя сервера» `admin:sql01` (через «Новый запрос», а не Обозреватель объектов) [ИТС-мет 6008, 2023; MS Learn]; `sqlcmd -S sql01 -E -A` [ИТС-мет 6008, 2023; MS Learn]. Одновременно возможно одно DAC-подключение [MS Learn, по `../1c-windows/02-…`]. Порт 1434 — в брандмауэр только для машины администратора (раздел 7.3).

### 9.9. `blocked process threshold (s)`

Порог в секундах, после которого формируется отчёт о заблокированном процессе (событие `blocked_process_report`); 5–86 400, по умолчанию отчёты не формируются; монитор блокировок просыпается раз в 5 секунд, так что значение меньше 5 не работает; применяется без перезапуска; отчёт — «по возможности», без гарантии реального времени [MS Learn]. Для 1С имеет смысл включать на время расследования ожиданий на блокировках СУБД вместе с сеансом Extended Events [практика]; сам сеанс и разбор — `mssql/06-…`, методика 1С по блокировкам — `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`.

```sql
EXECUTE sp_configure N'show advanced options', 1;  RECONFIGURE;
EXECUTE sp_configure N'blocked process threshold (s)', 20;  RECONFIGURE;   -- отключить: 0
```

### 9.10. Скрипт первичной настройки экземпляра

Под sysadmin, после установки и обновления до последнего CU; значения памяти подставить свои. Скрипт не трогает базы и безопасен для повторного запуска [практика]:

```sql
EXECUTE sp_configure N'show advanced options', 1;               RECONFIGURE;
EXECUTE sp_configure N'max server memory (MB)', 55296;           RECONFIGURE;  -- 64 ГБ, выделенный сервер
EXECUTE sp_configure N'min server memory (MB)', 0;               RECONFIGURE;
EXECUTE sp_configure N'max degree of parallelism', 1;            RECONFIGURE;  -- [ИТС-мет 5904]
EXECUTE sp_configure N'cost threshold for parallelism', 50;      RECONFIGURE;  -- на случай MAXDOP > 1 [практика]
EXECUTE sp_configure N'remote admin connections', 1;             RECONFIGURE;  -- [ИТС-мет 5904]
EXECUTE sp_configure N'backup compression default', 1;           RECONFIGURE;  -- не в Express
EXECUTE sp_configure N'backup checksum default', 1;              RECONFIGURE;
-- EXECUTE sp_configure N'optimize for ad hoc workloads', 1;     RECONFIGURE;  -- после проверки 9.6
SELECT name, value, value_in_use FROM sys.configurations
WHERE name IN (N'max server memory (MB)', N'min server memory (MB)', N'max degree of parallelism',
               N'cost threshold for parallelism', N'remote admin connections',
               N'backup compression default', N'backup checksum default',
               N'optimize for ad hoc workloads')
ORDER BY name;
```

## 10. `tempdb`

### 10.1. Почему `tempdb` под 1С нагружена

- Временные таблицы платформы, сортировки и группировки (`GROUP BY`, `UNION`, `DISTINCT`) [ИТС-мет 2374, 2008]; рабочие таблицы спулов, курсоров, сортировок, хэш-соединений [MS Learn].
- Хранилище версий строк: в управляемом режиме блокировок на SQL Server 2005+ платформа работает на уровне Read Committed Snapshot [ИТС-разр гл. 9, разд. 9.2.3.2], а версии строк для `READ COMMITTED` на основе версий хранятся в `tempdb` [MS Learn]. Длинная транзакция не даёт очищать версии — `tempdb` растёт [ИТС-мет 2374, 2008; MS Learn].
- `tempdb` пересоздаётся при каждом запуске, её нельзя копировать и восстанавливать; в ней всегда действует отложенная фиксация; сортировка — как у экземпляра; модель восстановления — простая [MS Learn].

### 10.2. Число и размер файлов

| Вопрос | 1С | Microsoft |
|---|---|---|
| Число файлов данных | 4 [ИТС-мет 5904, 2019] | = числу логических процессоров, если их ≤ 8; иначе 8; при сохраняющейся конкуренции добавлять по 4 [MS Learn] |
| Размер | на отдельном массиве — 50 % объёма / число файлов; вместе с базами — 1–10 ГБ на файл [ИТС-мет 5904, 2019] | заранее выделить место под типовую нагрузку, чтобы не расти после каждого перезапуска [MS Learn] |
| Прирост | 512 МБ [ИТС-мет 5904, 2019] | разумный, например 64 МБ; одинаковый у всех файлов; автоприрост оставить включённым [MS Learn] |
| Одинаковость | — | все файлы данных — одного размера и прироста (пропорциональное заполнение) [MS Learn] |
| Ограничение размера | убедиться, что ограничение размера `tempdb` снято; оповещение, если журнал `tempdb` > 70 ГБ [ИТС-мет 5899, 2016] | `max_size` у файлов — см. запрос ниже |

Совместить [практика]: число файлов — по правилу Microsoft (на сервере с 4 логическими CPU — 4, как и у 1С; с 16 — 8), размер — по правилу ИТС, прирост одинаковый у всех, 512 МБ при IFI или 64 МБ, если IFI нет. Начиная с 2017, установщик предупреждает, если начальный размер файла больше 1 ГБ, а IFI не включён [MS Learn].

Умолчания после установки (2016+) [MS Learn]: файлы `tempdev` (`tempdb.mdf`), `temp#` (`tempdb_mssql_#.ndf`), `templog` (`templog.ldf`) по 8 МБ с приростом 64 МБ; файлы с именами `tempdb_mssql_*.ndf` удаляются при удалении экземпляра — не называть так пользовательские файлы.

### 10.3. Команды

Под sysadmin. Размер через `MODIFY FILE` можно только **увеличить**; уменьшение — `DBCC SHRINKFILE` [MS Learn].

```sql
-- текущие файлы tempdb, размеры, прирост, ограничение [MS Learn]
SELECT name, type_desc, physical_name, size * 8 / 1024 AS size_mb,
       CASE WHEN is_percent_growth = 1 THEN CONCAT(growth, ' %') ELSE CONCAT(growth * 8 / 1024, ' MB') END AS growth,
       CASE max_size WHEN -1 THEN 'unlimited' ELSE CONCAT(CAST(max_size AS bigint) * 8 / 1024, ' MB') END AS max_size
FROM tempdb.sys.database_files;

-- выровнять размеры и прирост (пример для 8 файлов по 8 ГБ) — имена взять из запроса выше
ALTER DATABASE tempdb MODIFY FILE (NAME = N'tempdev', SIZE = 8GB, FILEGROWTH = 512MB);
ALTER DATABASE tempdb MODIFY FILE (NAME = N'temp2',   SIZE = 8GB, FILEGROWTH = 512MB);
-- ... temp3 ... temp8 ...
ALTER DATABASE tempdb MODIFY FILE (NAME = N'templog', SIZE = 8GB, FILEGROWTH = 512MB);

-- добавить файл (того же размера и прироста)
ALTER DATABASE tempdb ADD FILE (NAME = N'temp9', FILENAME = N'T:\TempDB\temp9.ndf', SIZE = 8GB, FILEGROWTH = 512MB);
```

Удаление лишнего файла: файл должен быть пуст — `USE tempdb; DBCC SHRINKFILE (N'temp9', EMPTYFILE); ALTER DATABASE tempdb REMOVE FILE temp9;` [MS Learn — `REMOVE FILE` только для пустого файла; последовательность — практика] ⚠ (в нагруженной `tempdb` очистка может не пройти — делать в тихое время или после перезапуска).

**Перенос `tempdb` на другой том** [MS Learn; ИТС-мет 2377, 2008]: узнать логические имена (`SELECT name, physical_name FROM sys.master_files WHERE database_id = DB_ID('tempdb');`), для **каждого** файла выполнить `ALTER DATABASE tempdb MODIFY FILE (NAME = …, FILENAME = N'T:\TempDB\…');`, перезапустить службу, проверить пути тем же запросом, удалить старые файлы. До перезапуска `tempdb` работает на старом месте. Каталог назначения должен существовать и быть доступен SID службы [практика]. Перезапуск службы SQL Server разрывает все сеансы 1С — в окно обслуживания.

### 10.4. Что изменилось по версиям

| Версия | Изменение | Источник |
|---|---|---|
| 2016 | несколько файлов при установке; файлы растут одновременно (`AUTOGROW_ALL_FILES` всегда включён) — 1117 не нужен; только однородные экстенты — 1118 не нужен | [MS Learn] |
| 2017 | предупреждение установщика о больших файлах без IFI; DMV `sys.dm_tran_version_store_space_usage` — объём хранилища версий по базам (страница DMV указывает и 2016 SP2) | [MS Learn] |
| 2019 | одновременное обновление PFS; **Memory-optimized TempDB metadata** (по умолчанию выключено) | [MS Learn] |
| 2022 | одновременное обновление GAM и SGAM — меньше конкуренции за защёлки страниц выделения | [MS Learn] |
| 2025 | ADR в `tempdb` (включение — перезапуск), управление ресурсами пространства `tempdb` | [MS Learn] |

**Memory-optimized TempDB metadata** (2019+) убирает конкуренцию за метаданные временных объектов. Microsoft советует включать **только** при подтверждённой конкуренции (ожидания `PAGELATCH_*` на системных таблицах `tempdb`, диагностический запрос — в документации `tempdb`); ограничения: перезапуск для включения и выключения, возможен рост памяти `MEMORYCLERK_XTP`, нельзя columnstore на временных таблицах [MS Learn]. Под sysadmin, с перезапуском:

```sql
ALTER SERVER CONFIGURATION SET MEMORY_OPTIMIZED TEMPDB_METADATA = ON;   -- затем перезапуск службы
SELECT SERVERPROPERTY('IsTempdbMetadataMemoryOptimized') AS mo_tempdb_meta;  -- 1 после перезапуска
```

Если после включения служба не стартует — запуск с `-f`, выключить функцию, убрать `-f` [MS Learn]. Совместимость с платформой 1С в ИТС не описана ⚠ — сначала на тестовом стенде.

### 10.5. Контроль заполнения

```sql
-- свободно в tempdb и кто занимает: версии, внутренние, пользовательские объекты (МБ) [MS Learn: sys.dm_db_file_space_usage]
SELECT SUM(unallocated_extent_page_count) / 128         AS free_mb,
       SUM(version_store_reserved_page_count) / 128     AS version_store_mb,
       SUM(internal_object_reserved_page_count) / 128   AS internal_mb,
       SUM(user_object_reserved_page_count) / 128       AS user_objects_mb
FROM tempdb.sys.dm_db_file_space_usage;
-- хранилище версий по базам (2016 SP2+, 2017+) [MS Learn]
SELECT DB_NAME(database_id) AS db, reserved_space_kb / 1024 AS version_store_mb
FROM sys.dm_tran_version_store_space_usage ORDER BY reserved_space_kb DESC;
```

Рост `tempdb` из-за «зависших» транзакций — причина и разбор в `mssql/08-…` и [ИТС-мет 2374, 2008]; уменьшить — перезапуском службы или `DBCC SHRINKFILE` в тихое время [ИТС-мет 2374, 2008]. Умолчание прироста «10 %» из той статьи устарело — с 2016 прирост 64 МБ [MS Learn].

## 11. База `model` и параметры новых баз

### 11.1. Что наследуется от `model`, а что нет

- Новая база создаётся копированием `model`: наследуются объекты, параметры базы (`ALTER DATABASE … SET …`) и модель восстановления [MS Learn].
- **Файловые свойства `model` не наследуются, кроме начального размера файла данных** [MS Learn, «model database»]. Если `CREATE DATABASE` не указывает `FILEGROWTH`, прирост по умолчанию с SQL Server 2016 — 64 МБ для данных и журнала (2005–2014: данные 1 МБ, журнал 10 %) [MS Learn, `CREATE DATABASE`]. Начальный размер журнала без явного указания — больший из 512 КБ и 25 % от файла данных [MS Learn].
- Сортировку `model` сменить нельзя — она равна сортировке экземпляра [MS Learn].

Отсюда **расхождение с ИТС**: чек-лист 1С предлагает в `model` задать начальный размер данных 1–10 ГБ, журнала 1–2 ГБ и прирост 512 МБ [ИТС-мет 5904, 2019]. По документации Microsoft из этого сработает только размер файла данных; прирост и размер журнала базы, созданной платформой, будут умолчаниями `CREATE DATABASE`, если платформа не задаёт их сама ⚠ (какой `CREATE DATABASE` выполняет платформа, ИТС не описывает). Порядок [практика]: настроить `model` как советует ИТС **и** после создания каждой ИБ проверить файлы базы и при необходимости задать размеры и прирост явно (11.3).

### 11.2. Рекомендации 1С и умолчания Microsoft

| Параметр | ИТС [5904, 2019] | Умолчание `model` [MS Learn] |
|---|---|---|
| Начальный размер данных | `model` — 1–10 ГБ; рабочая база — ожидаемый размер за длительный период | 8 МБ (2016+) |
| Журнал | `model` — 1–2 ГБ; рабочая база — такой, чтобы не расти между `BACKUP LOG` | 8 МБ |
| Прирост | 512 МБ | 64 МБ (данные и журнал) |
| Модель восстановления | по политике резервного копирования | зависит от редакции |
| `AUTO_UPDATE_STATISTICS_ASYNC` | **ON** | OFF |
| `PAGE_VERIFY` | — | CHECKSUM |
| `READ_COMMITTED_SNAPSHOT` | — (уровень изоляции задаёт платформа) | OFF |
| `AUTO_SHRINK`, `AUTO_CLOSE` | — | OFF |

Для загрузки `.dt` ИТС советует модель «Простая» или «С неполным протоколированием», смену модели — с предварительной резервной копией [ИТС-адм разд. 6.8]; подробнее — `mssql/04-…`. Сжатие данных на уровне СУБД в перечне допустимых для MS SQL административных действий ИТС нет (указано только для Oracle) [ИТС-КС разд. 5.5.4] — `ROW`/`PAGE`-сжатие таблиц 1С не включать без отдельной проверки [практика] ⚠.

### 11.3. Команды

Под sysadmin. После изменения `model` Microsoft рекомендует сделать её резервную копию [MS Learn].

```sql
-- model: модель восстановления и асинхронное обновление статистики [MS Learn: ALTER DATABASE SET; значения — ИТС-мет 5904]
ALTER DATABASE [model] SET RECOVERY FULL;                 -- или SIMPLE — по политике копий
ALTER DATABASE [model] SET AUTO_UPDATE_STATISTICS_ASYNC ON;
ALTER DATABASE [model] MODIFY FILE (NAME = N'modeldev', SIZE = 1GB, FILEGROWTH = 512MB);
ALTER DATABASE [model] MODIFY FILE (NAME = N'modellog', SIZE = 1GB, FILEGROWTH = 512MB);
BACKUP DATABASE [model] TO DISK = N'E:\Backup\model.bak' WITH CHECKSUM, INIT;
SELECT name, recovery_model_desc, is_auto_update_stats_async_on, page_verify_option_desc,
       is_read_committed_snapshot_on, compatibility_level, collation_name
FROM sys.databases WHERE name = N'model';
```

Логические имена файлов `model` — `modeldev`, `modellog` [MS Learn].

После того как платформа создала базу `buh` (или после восстановления копии), проверить и при необходимости выровнять (под sysadmin):

```sql
SELECT name, type_desc, physical_name, size / 128 AS size_mb, growth, is_percent_growth
FROM [buh].sys.database_files;                              -- growth в страницах по 8 КБ, если is_percent_growth = 0
ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh',     FILEGROWTH = 512MB);   -- логические имена — из запроса выше
ALTER DATABASE [buh] MODIFY FILE (NAME = N'buh_log', FILEGROWTH = 512MB);
ALTER DATABASE [buh] SET AUTO_UPDATE_STATISTICS_ASYNC ON;   -- если не унаследовалось
SELECT name, compatibility_level, is_read_committed_snapshot_on, snapshot_isolation_state_desc,
       recovery_model_desc, is_auto_update_stats_async_on, page_verify_option_desc
FROM sys.databases WHERE name = N'buh';
```

`READ_COMMITTED_SNAPSHOT` у базы 1С вручную не менять — изоляцию определяет платформа [ИТС-разр гл. 9, разд. 9.2.3.2]; включает ли платформа этот параметр базы сама, в прочитанных текстах ИТС прямо не сказано ⚠ (`../1c-windows/02-…`, раздел 7.1).

## 12. Флаги трассировки

### 12.1. Как включать и проверять

- Флаги действуют на трёх уровнях: запрос (`QUERYTRACEON`), сеанс, глобально. Глобальный флаг нужно включать глобально, иначе он не действует [MS Learn].
- **Постоянно** — параметр запуска `-T<номер>` (ИТС называет это рекомендуемым способом [ИТС-мет 5946, 2019]): SQL Server Configuration Manager → SQL Server Services → свойства `SQL Server (MSSQLSERVER)` → вкладка **Startup Parameters** → в поле «Specify a startup parameter» ввести `-T1224` → Add → OK → перезапуск службы; каждый флаг — отдельным параметром [MS Learn]. Configuration Manager пишет параметры в реестр, они вступают в силу при следующем запуске [MS Learn]. На Linux — `mssql-conf traceflag` (раздел 15).
- **Сразу, до перезапуска** — `DBCC TRACEON (1224, -1);` (`-1` — глобально); эффект теряется при перезапуске; выключить — `DBCC TRACEOFF (1224, -1);` [MS Learn; ИТС-мет 5946, 2019].
- **Проверка** — `DBCC TRACESTATUS (-1);` (глобальные флаги) [MS Learn]; параметры запуска из реестра — `sys.dm_server_registry` по ключу `…\Parameters` (раздел 3.7) [MS Learn].
- Документированные флаги Microsoft поддерживает в продуктиве «при использовании по назначению»; любой флаг сначала проверять не на продуктиве [MS Learn].

```sql
-- под sysadmin: включить сразу (и обязательно добавить -T в параметры запуска, иначе пропадёт после перезапуска)
DBCC TRACEON (1224, -1);
DBCC TRACEON (4199, -1);
DBCC TRACESTATUS (-1);
SELECT value_name, value_data FROM sys.dm_server_registry WHERE registry_key LIKE N'%Parameters';   -- SQLArg0..N: -d, -e, -l, -T…
```

### 12.2. Список ИТС 5946 против документации Microsoft

ИТС рекомендует «всегда включать на глобальном уровне» флаги 610, 1117, 1118, 1211, 1224, 2330, 2371, 4199, 8048 [ИТС-мет 5946, 2019]. Статья 2019 года; что с ними на 2016–2025:

| Флаг | Что делает | ИТС [5946, 2019] | Microsoft [MS Learn] | Итог для SQL Server 2016–2022 |
|---|---|---|---|---|
| 610 | минимальное протоколирование вставок в индексированные таблицы | включать; «в 2016 поведение стандартное» | с 2016 не нужен: минимальное протоколирование включено по умолчанию (нужен `ALLOW_PAGE_LOCKS = ON` у индексов) | не нужен |
| 1117 | рост всех файлов файловой группы одновременно (для 1С — `tempdb`) | включать; с 2016 — параметры `AUTOGROW_*` | с 2016 управляется `AUTOGROW_SINGLE_FILE`/`AUTOGROW_ALL_FILES`, флаг без действия | не нужен |
| 1118 | только однородные экстенты | включать; с 2016 — `MIXED_PAGE_ALLOCATION` | с 2016 управляется `MIXED_PAGE_ALLOCATION`, флаг без действия | не нужен |
| 1211 | запрет эскалации блокировок всегда, даже при нехватке памяти | включать | возможна ошибка 1204 (нет ресурса блокировок); при обоих флагах главнее 1211; советуют **1224 вместо 1211** | не включать |
| 1224 | запрет эскалации по числу блокировок; по памяти (40 % памяти ядра при `locks = 0`) эскалация остаётся | включать | рекомендуется вместо 1211 | **включить** |
| 2330 | отключает сбор статистики использования индексов (`sys.dm_db_index_usage_stats`) | включать в продуктиве (недокументированный) | в справочнике флагов отсутствует | ⚠ по ситуации: без него DMV использования и отсутствующих индексов работают, с ним — нет |
| 2371 | порог автообновления статистики уменьшается с ростом таблицы | включать (2008 R2 SP1+); с 2016 — поведение движка | с 2016 при уровне совместимости ≥ 130 без действия | не нужен при уровне ≥ 130 |
| 4199 | исправления оптимизатора из CU/SP | включать; для 2016 — зависит от уровня совместимости | см. 12.3 | **включить** (или `QUERY_OPTIMIZER_HOTFIXES`) после теста |
| 8048 | секционирование объектов памяти (ожидания `CMEMTHREAD`) | включать (2008+); с 2014 SP2 и 2016 — стандартно | с 2014 SP2 и 2016 поведение динамическое | не нужен |

Почему 1С запрещает эскалацию: укрупнение блокировок обычно до таблицы резко снижает параллельную работу; цена — больше памяти на блокировки [ИТС-мет 5946, 2019]. Альтернатива флагу для одной таблицы — `LOCK_ESCALATION` в `ALTER TABLE` [MS Learn]; для таблиц 1С не применять — схемой управляет платформа, настройка пропадёт при реструктуризации [практика] ⚠. На SQL Server 2025 есть «оптимизированная блокировка» (optimized locking), которая уменьшает блокировки и избегает эскалации [MS Learn], — но 2025 платформой не поддерживается (раздел 1.2).

### 12.3. Флаг 4199 подробно

- Включает исправления оптимизатора, вышедшие в CU и SP. Изменения оптимизатора прошлых версий включены по умолчанию на **последнем** уровне совместимости данной версии без флага; изменения, выпущенные **после RTM** данной версии, — только с флагом 4199 (или аналогами). Без флага изменения оптимизатора для уровней ниже 130 выключены [MS Learn].
- Исправления оптимизатора, устраняющие **неверные результаты** и нарушения доступа, флагом не управляются — включаются сразу после установки обновления [MS Learn].
- С SQL Server 2016 то же для одной базы — `ALTER DATABASE SCOPED CONFIGURATION SET QUERY_OPTIMIZER_HOTFIXES = ON` (умолчание `OFF`, эквивалент флага 4199); с 2016 SP1 — подсказка `USE HINT('ENABLE_QUERY_OPTIMIZER_HOTFIXES')` [MS Learn].
- **SQL Server 2014 и 1С:** платформа требует флаг 4199 для используемой базы; если он не установлен на всю базу, платформа пытается включать его для каждого соединения от имени пользователя БД, и при нехватке прав — ошибка; решение — пользователь БД с правами `sa` или флаг 4199, установленный заранее [ИТС-адм разд. 5.2.1.3.2]; то же — «для 2014 необходимо включить» [ИТС-мет 5904, 2019].

Вариант без глобального флага (под sysadmin, в контексте базы 1С; 2016+):

```sql
USE [buh];
ALTER DATABASE SCOPED CONFIGURATION SET QUERY_OPTIMIZER_HOTFIXES = ON;
SELECT name, value FROM sys.database_scoped_configurations
WHERE name IN (N'QUERY_OPTIMIZER_HOTFIXES', N'LEGACY_CARDINALITY_ESTIMATION', N'MAXDOP', N'PARAMETER_SNIFFING');
```

### 12.4. Другие флаги, о которых спрашивают

| Флаг | Назначение [MS Learn] | Для 1С |
|---|---|---|
| 3226 | не писать в журналы сообщения об успешных копированиях и восстановлениях (глобальный) | полезен при частых `BACKUP LOG` [практика] |
| 7471 | параллельный `UPDATE STATISTICS` разных статистик одной таблицы (2014 SP1+) | по ситуации [практика] ⚠ |
| 460 | подробное сообщение об усечении строки (2628 вместо 8152); с уровня 150 — по умолчанию | для отладки обменов [практика] |
| 1204, 1222 | взаимоблокировки в журнал ошибок; не включать на нагруженных системах | вместо них — `system_health` и XE (`mssql/06-…`) |
| 834 / 845 | крупные страницы (только с LPIM, может не дать стартовать) / LPIM для Standard (с 2012 не нужен) | не включать |
| 9481, 2312 | старый / новый оценщик кардинальности независимо от уровня совместимости | лучше `LEGACY_CARDINALITY_ESTIMATION` на уровне базы (раздел 13) |
| 3608 | запуск только `master` — для переноса системных баз | только при переносе |

### 12.5. Рекомендуемый набор по версиям

| Версия SQL Server | Флаги запуска | Источник |
|---|---|---|
| 2014 (вне поддержки) | `-T4199` (требование платформы), `-T1224`; 1117/1118 — для `tempdb` по ИТС | [ИТС-адм разд. 5.2.1.3.2; ИТС-мет 5946] |
| 2016, 2017, 2019, 2022 | `-T1224`; `-T4199` или `QUERY_OPTIMIZER_HOTFIXES = ON` в базах 1С — после теста; `-T3226` — по желанию | [ИТС-мет 5946; MS Learn]; 3226 — [практика] |
| 2025 | платформой не поддерживается | [v8.1c.ru] |

## 13. Уровень совместимости и оценщик кардинальности

### 13.1. Уровни по версиям

[MS Learn, «ALTER DATABASE compatibility level»]:

| SQL Server | Версия ядра | Уровень по умолчанию | Допустимые уровни |
|---|---|---|---|
| 2014 | 12 | 120 | 120, 110, 100 |
| 2016 | 13 | 130 | 130, 120, 110, 100 |
| 2017 | 14 | 140 | 140 … 100 |
| 2019 | 15 | 150 | 150 … 100 |
| 2022 | 16 | 160 | 160 … 100 |
| 2025 | 17 | 170 | 170 … 100 |

- Новая база получает уровень по умолчанию для версии ядра, **если у `model` уровень не ниже**; база, подключённая или восстановленная со старой версии, **сохраняет** свой уровень (если он не ниже минимально допустимого); при обновлении экземпляра «на месте» пользовательские базы сохраняют уровень, `tempdb`, `model`, `msdb` получают уровень по умолчанию, `master` — сохраняет [MS Learn].
- Уровень меняется `ALTER DATABASE … SET COMPATIBILITY_LEVEL = …`, вступает в силу при следующем `USE` / новом входе; хранимые процедуры перекомпилируются [MS Learn].
- С уровня 130 все новые исправления и возможности, влияющие на планы, добавляются только на новейший уровень — это сделано, чтобы обновление ядра не меняло планы само по себе; рекомендация Microsoft — со временем переходить на новейший уровень контролируемо (Query Store, Query Tuning Assistant) [MS Learn].
- Удалённая функциональность и изменённые системные объекты уровнем совместимости не защищаются [MS Learn].

### 13.2. Что говорит 1С

В прочитанных текстах ИТС рекомендаций по уровню совместимости базы MS SQL нет ⚠; упоминание есть только в описании флага 4199: на SQL Server 2016 исправления оптимизатора могут применяться без флага в зависимости от уровня совместимости базы [ИТС-мет 5946, 2019]. Устанавливает ли платформа уровень совместимости при создании базы, не описано ⚠ — проверяйте `compatibility_level` в `sys.databases` после создания ИБ.

Практика администраторов 1С [практика] ⚠: новую базу оставлять на уровне по умолчанию версии; базу, перенесённую со старого сервера, переводить на новый уровень только после сравнения производительности ключевых операций (проведение, закрытие месяца, тяжёлые отчёты) — вплоть до отката на прежний уровень или включения старого оценщика.

### 13.3. Оценщик кардинальности (CE)

- Модель CE 70 (SQL Server 7.0 – 2012) исходит из независимости столбцов, равномерности, простого вложения; начиная с SQL Server 2014 (уровень 120 и выше) модель обновлена: корреляция вместо независимости, «базовое вложение»; большинству систем новый оценщик полезен, но отдельные важные запросы могут получить более медленный план [MS Learn].
- Старый оценщик для всей базы при сохранении уровня совместимости (2016+): `ALTER DATABASE SCOPED CONFIGURATION SET LEGACY_CARDINALITY_ESTIMATION = ON` — эквивалент флага 9481; умолчание `OFF` — модель по уровню совместимости [MS Learn]. Для запроса — `USE HINT('FORCE_LEGACY_CARDINALITY_ESTIMATION')` (2016 SP1+) — для запросов 1С неприменимо, их формирует платформа [MS Learn; практика].
- На 2022 (уровень 160) по умолчанию включена оптимизация планов, чувствительных к параметрам (`PARAMETER_SENSITIVE_PLAN_OPTIMIZATION = ON`) [MS Learn]; на 2025 — обратная связь CE для выражений [MS Learn]. Как они влияют на запросы 1С, в ИТС не описано ⚠.

Порядок смены уровня для базы 1С (под sysadmin; в окно обслуживания; перед — полная копия базы) [MS Learn — инструменты; порядок — практика]:

```sql
-- 0. текущее состояние
SELECT name, compatibility_level, is_query_store_on FROM sys.databases WHERE name = N'buh';
-- 1. Query Store для сравнения «до/после» (в 2022+ включён у новых баз по умолчанию)
ALTER DATABASE [buh] SET QUERY_STORE = ON;
-- 2. неделю собрать базовую линию на старом уровне, затем:
ALTER DATABASE [buh] SET COMPATIBILITY_LEVEL = 160;
-- 3а. если ключевые операции стали медленнее из-за оценок кардинальности — старый оценщик для базы
USE [buh];
ALTER DATABASE SCOPED CONFIGURATION SET LEGACY_CARDINALITY_ESTIMATION = ON;
-- 3б. или полный откат уровня
ALTER DATABASE [buh] SET COMPATIBILITY_LEVEL = 130;
```

Работа с Query Store, поиск регрессий и принудительные планы — `mssql/06-…`; переход на новую версию SQL Server целиком — `mssql/07-…`.

## 14. Обновления SQL Server: CU, GDR, политика

### 14.1. Модель обслуживания

[MS Learn, «Install SQL Server servicing updates»; «Servicing models for SQL Server»; «Updates to the Microsoft Update detection logic»]:

- **CU (накопительное обновление)** — все исправления и улучшения с выхода версии. Для 2017 и новее: ежемесячно в первый год, затем раз в два месяца до конца пятилетней основной поддержки. CU31 — последний CU для SQL Server 2017; для 2016 и старше CU больше не выпускаются — только исправления по запросу и обновления безопасности (после конца расширенной поддержки — по подписке ESU).
- **GDR** — исправления безопасности и критические; выпускаются для исходной сборки (RTM) или для конкретного CU (`CUnn-GDR`); для каждой такой базовой сборки последний GDR накопительный.
- **SP** — с SQL Server 2017 не выпускаются.
- **Две ветки:** GDR-ветка (только безопасность) и CU-ветка (безопасность + всё остальное). После установки любого CU экземпляр переходит в CU-ветку; вернуться в GDR-ветку можно, лишь удалив все CU. Microsoft всегда рекомендует последний CU своей версии.
- Обновления приходят через Microsoft Update (нужно включить получение обновлений других продуктов Microsoft), WSUS и Центр загрузки; через MU обновляются все компоненты в тихом режиме.

**Позиция 1С:** установить последний пакет обновлений и последний CU [ИТС-мет 5904, 2019]. Вывод [практика]: на серверах 1С — **CU-ветка, последний CU**, ставить не в день выхода, а после 1–2 недель наблюдения и на тестовом стенде с копией рабочей базы.

### 14.2. Установка обновления

Во время установки экземпляра — `/UpdateEnabled=True /UpdateSource="<папка с CU>"`: установщик встроит CU в установку [MS Learn]. После установки (cmd от имени администратора) [MS Learn, «Installing updates from the command line»]:

```bat
:: одно обновление для экземпляра по умолчанию и общих компонентов
SQLServer2022-KBxxxxxxx-x64.exe /qs /IAcceptSQLServerLicenseTerms /Action=Patch /InstanceName=MSSQLSERVER
:: все экземпляры на компьютере
SQLServer2022-KBxxxxxxx-x64.exe /qs /IAcceptSQLServerLicenseTerms /Action=Patch /AllInstances
:: удаление обновления (откат) с экземпляра
SQLServer2022-KBxxxxxxx-x64.exe /qs /Action=RemovePatch /InstanceName=MSSQLSERVER
```

`/quiet` — полностью без интерфейса, `/qs` — только индикатор; `/IAcceptSQLServerLicenseTerms` обязателен в тихих режимах; общие компоненты установщик всегда поднимает не ниже самого нового экземпляра [MS Learn]. Удаление CU возможно и через «Программы и компоненты» [MS Learn — статья об удалении CU] ⚠ (подробности не читались).

**Порядок для сервера с базами 1С** [практика]:

1. Прочитать описание CU (известные проблемы).
2. Полные копии баз 1С и системных баз `master`, `msdb` (`mssql/04-…`).
3. Остановить работу пользователей и регламентные задания 1С (или выбрать окно), при совмещённом сервере — остановить службу сервера 1С.
4. Установить CU, перезагрузить сервер, если требует установщик.
5. Проверить: `SELECT SERVERPROPERTY('ProductVersion'), SERVERPROPERTY('ProductUpdateLevel'), SERVERPROPERTY('ProductUpdateReference');`, журнал ошибок, старт служб, вход 1С в базу, тестовое проведение документа.
6. Отдельно, своим графиком — обновлять OLE DB Driver на рабочих серверах 1С (раздел 8).

### 14.3. Сводка политики

| Что | Когда | Кто проверяет |
|---|---|---|
| CU SQL Server | раз в 1–2 месяца после выхода и теста | администратор СУБД |
| GDR / безопасность на CU-ветке | по выходу, в ближайшее окно | администратор СУБД |
| OLE DB Driver на серверах 1С | при выходе новой версии и при смене платформы 1С | администратор 1С |
| Новая мажорная версия SQL Server | только после появления в списке 1С (v8.1c.ru, `1cv8upd`) | `mssql/07-…` |

## 15. SQL Server на Linux (кратко)

- **Когда это допустимо для 1С:** только если рабочие серверы 1С — на Windows [v8.1c.ru]. На сервере 1С под Linux (как у вас) рабочие процессы с MS SQL не работают [ИТС-КС разд. 2.3]. Ставить SQL Server на машину с «PostgreSQL для 1С» незачем: это разные СУБД для разных сценариев [практика].
- **Платформы** [MS Learn]: SQL Server 2022 — Ubuntu 20.04, 22.04 (а также RHEL 8/9, SLES 15); SQL Server 2025 — Ubuntu 22.04, 24.04, RHEL 9/10 (SLES больше не поддерживается); файловые системы XFS или ext4; на WSL — только для разработки.
- **Установка** — пакет `mssql-server` из репозитория `packages.microsoft.com` по инструкции Microsoft для своей версии Ubuntu, затем `sudo /opt/mssql/bin/mssql-conf setup`; без участия — переменные `MSSQL_SA_PASSWORD`, `MSSQL_PID` и `sudo /opt/mssql/bin/mssql-conf -n setup accept-eula` (`SA_PASSWORD` устарела) [MS Learn]. Для 2025 ключ репозитория кладётся в `/usr/share/keyrings/microsoft-prod.gpg` [MS Learn].
- **Настройка — утилита `mssql-conf`** (от `root` через `sudo`), значения пишутся в `/var/opt/mssql/mssql.conf`; большинство изменений требуют `sudo systemctl restart mssql-server` [MS Learn].

| Задача | Команда (root) [MS Learn] |
|---|---|
| Ограничить физическую память процесса (умолч. 80 % ОЗУ) | `sudo /opt/mssql/bin/mssql-conf set memory.memorylimitmb 49152` |
| TCP-порт (умолч. 1433) | `sudo /opt/mssql/bin/mssql-conf set network.tcpport 1433` |
| Каталоги по умолчанию для данных, журналов, копий (умолч. `/var/opt/mssql/data`) | `… set filelocation.defaultdatadir /mssql/data`, `… set filelocation.defaultlogdir /mssql/log`, `… set filelocation.defaultbackupdir /mssql/backup` |
| Флаги трассировки при запуске | `sudo /opt/mssql/bin/mssql-conf traceflag 1224 4199 on` (выключить — `… off`) |
| SQL Server Agent (по умолчанию выключен) | `sudo /opt/mssql/bin/mssql-conf set sqlagent.enabled true` |
| Шифрование | `… set network.tlscert /etc/ssl/certs/mssql.pem`, `… set network.tlskey /etc/ssl/private/mssql.key`, `… set network.forceencryption 1`, `… set network.tlsprotocols 1.2` |
| Сортировка экземпляра | копии баз → `sp_detach_db` пользовательских баз → `sudo /opt/mssql/bin/mssql-conf set-collation` → восстановить базы |
| Сбросить параметр | `sudo /opt/mssql/bin/mssql-conf unset network.tcpport` |
| Посмотреть заданное | `sudo cat /var/opt/mssql/mssql.conf` |
| Применить | `sudo systemctl restart mssql-server` |

- `memory.memorylimitmb` ограничивает физическую память процесса целиком, а `max server memory (MB)` внутри неё — буферный пул; задавать оба [MS Learn]. Остальные `sp_configure` (MAXDOP, DAC и т. д.) — как на Windows (раздел 9) [MS Learn — `sp_configure` общий].
- Файлы сертификата и ключа должны быть доступны учётной записи `mssql`; Microsoft советует `chown mssql:mssql <файл>; chmod 400 <файл>`; по умолчанию разрешены TLS 1.2, 1.1, 1.0 — оставить только 1.2, если клиенты умеют [MS Learn].
- На Linux клиент `sqlcmd` (ODBC) требует `-S` и поддерживает только протокол `tcp` [MS Learn] — Shared Memory между 1С и SQL Server на Linux не возникает (сервер 1С всё равно на другой машине).
- Брандмауэр и диски Ubuntu — `../linux/08-set-ssh-firewall.md`, `../linux/07-diski-fs-lvm.md`.

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| Установка падает: `0x851A0019` «Could not find the Database Engine startup handle» / `0x851A001A`; в журнале ошибки 5178, 5179 | ОС видит сектор диска больше 4 КБ (NVMe; у Microsoft — Windows 11) | `fsutil fsinfo sectorinfo`; `ForcedPhysicalSectorSizeInBytes` = `* 4095`, перезагрузка (2.2) [MS Learn] |
| Сервер 1С не подключается к СУБД с другой машины, локально всё работает | порт не открыт (setup его не открывает), TCP/IP выключен, именованный экземпляр без Browser/статического порта | правило брандмауэра на 1433 только с серверов 1С; `/TCPENABLED=1`; статический порт (7.2–7.3) [MS Learn] |
| «Компоненты OLE DB провайдера не найдены» при создании или загрузке ИБ | на рабочем сервере 1С нет OLE DB Driver/Native Client | поставить OLE DB Driver 18 (8.3) и проверить `DBMSSQLCONN` (8) [ИТС-КС разд. 1.5.4] |
| После установки OLE DB Driver 19 — ошибки SSL «certificate chain was issued by an authority that is not trusted» | у 19 по умолчанию `Encrypt=Mandatory` и проверка сертификата, а у SQL Server самоподписанный сертификат | доверенный сертификат на SQL Server; для 8.3.x — драйвер 18 [MS Learn; практика] ⚠ |
| Оптимизированная реструктуризация на совмещённом сервере не работает | подключение 1С идёт по Shared Memory (`lpc:` или порядок протоколов драйвера `sm tcp np`) | отключить Shared Memory на экземпляре или имя сервера с `tcp:` ⚠; проверить `net_transport` (7.1) [ИТС-адм прил. 3, разд. 3.17.23] |
| Сервер уходит в подкачку, 1С тормозит, SQL Server «съел всю память» | `max server memory` по умолчанию без предела | задать по расчёту 9.3 [ИТС-мет 5904; MS Learn] |
| На совмещённом сервере рабочие процессы 1С падают по памяти после включения LPIM | закреплённый буферный пул не отдаёт память | убрать право «Блокировка страниц в памяти», перезапуск SQL Server [ИТС-мет 5904, 2019] |
| SQL Server не стартует после изменения памяти | `max server memory` слишком мало | запуск с `-f`, вернуть значение, убрать `-f` [MS Learn] |
| Один отчёт грузит все ядра, ожидания `CXPACKET`, время запросов «скачет» | `max degree of parallelism = 0` (умолчание) | `MAXDOP = 1` (9.4) [ИТС-мет 6008, 2023; 5945] |
| Ошибки «Cannot resolve the collation conflict…» при работе 1С | сортировка базы отличается от сортировки экземпляра (`tempdb`) | выровнять: база на экземпляр с той же сортировкой (5.3, 5.5) [MS Learn] ⚠ (точный текст ошибки) |
| Флаги трассировки «пропали» после перезагрузки | включены только `DBCC TRACEON` | добавить `-T<флаг>` в параметры запуска (12.1) [MS Learn] |
| SQL Server 2014: ошибка подключения 1С, связанная с флагом 4199 | платформа включает 4199 на каждое соединение, у пользователя БД нет прав | `-T4199` глобально или пользователь с правами `sa` [ИТС-адм разд. 5.2.1.3.2] |
| Медленные создание базы, восстановление, автоприрост; в журнале 5144/5145, ожидание `PREEMPTIVE_OS_WRITEFILEGATHER` | IFI выключен, большой прирост | право «Perform volume maintenance tasks» SID службы; прирост разумного размера (4.2) [MS Learn] |
| `tempdb` растёт до заполнения тома | длинные транзакции, хранилище версий, «зависшие» соединения | 10.5; разбор — `mssql/08-…` [ИТС-мет 2374, 2008] |
| После переноса базы на новый SQL Server часть операций стала медленнее | база сохранила старый уровень / сменили уровень и оценщик | 13: Query Store, `LEGACY_CARDINALITY_ESTIMATION`, откат уровня [MS Learn] |
| После перезагрузки совмещённого сервера кластер 1С пишет ошибки соединения с СУБД | SQL Server 2022+ стартует с отложенным запуском | проверить порядок запуска служб (4.1) [MS Learn; практика] ⚠ |

## Быстрая шпаргалка

```bat
:: установка (полный пример — 3.4), конфигурационный файл, CU, журнал установки
setup.exe /Q /ACTION=Install /IACCEPTSQLSERVERLICENSETERMS /SUPPRESSPRIVACYSTATEMENTNOTICE /PID="…" /FEATURES=SQLEngine /INSTANCENAME=MSSQLSERVER /SQLSVCACCOUNT="NT Service\MSSQLSERVER" /AGTSVCACCOUNT="NT Service\SQLSERVERAGENT" /SQLSYSADMINACCOUNTS="CORP\sql-admins" /SECURITYMODE=SQL /SAPWD="…" /SQLCOLLATION=Cyrillic_General_CI_AS /SQLSVCINSTANTFILEINIT=True /TCPENABLED=1 /NPENABLED=0 /SQLMAXDOP=1 /SQLMAXMEMORY=<МБ>
setup.exe /ConfigurationFile="E:\Distr\SQL2022_1C.ini" /IACCEPTSQLSERVERLICENSETERMS /SAPWD="…"
SQLServer2022-KBxxxxxxx-x64.exe /qs /IAcceptSQLServerLicenseTerms /Action=Patch /InstanceName=MSSQLSERVER
type "%ProgramFiles%\Microsoft SQL Server\160\Setup Bootstrap\Log\Summary.txt"
```

```powershell
fsutil fsinfo ntfsinfo D: | Select-String 'Bytes Per Cluster'          # 65536
fsutil fsinfo sectorinfo D: | Select-String 'PhysicalBytesPerSector'   # ≤ 4096
New-NetFirewallRule -DisplayName 'SQL 1433 (1C)' -Direction Inbound -Protocol TCP -LocalPort 1433 -RemoteAddress 10.10.0.21,10.10.0.22 -Action Allow
Test-NetConnection sql01 -Port 1433
```

```sql
SELECT SERVERPROPERTY('ProductVersion'), SERVERPROPERTY('ProductUpdateLevel'), SERVERPROPERTY('Collation');
SELECT servicename, service_account, instant_file_initialization_enabled FROM sys.dm_server_services;
SELECT sql_memory_model_desc FROM sys.dm_os_sys_info;
EXECUTE sp_configure N'show advanced options', 1; RECONFIGURE;
EXECUTE sp_configure N'max server memory (MB)', <МБ>; RECONFIGURE;
EXECUTE sp_configure N'max degree of parallelism', 1; RECONFIGURE;
EXECUTE sp_configure N'remote admin connections', 1; RECONFIGURE;
DBCC TRACEON (1224, -1); DBCC TRACESTATUS (-1);            -- и -T1224 в параметрах запуска
SELECT net_transport, encrypt_option, COUNT(*) FROM sys.dm_exec_connections GROUP BY net_transport, encrypt_option;
SELECT name, compatibility_level, collation_name FROM sys.databases;
```

```bash
sudo /opt/mssql/bin/mssql-conf set memory.memorylimitmb 49152 && sudo /opt/mssql/bin/mssql-conf traceflag 1224 on
sudo systemctl restart mssql-server && sudo cat /var/opt/mssql/mssql.conf
```

## Источники

ИТС (доступ по подписке; полные тексты 8.3.27 прочитаны 19–20.10.2026):

- «Клиент-серверный вариант. Руководство администратора»: гл. 1 — https://its.1c.ru/db/v8327doc/content/123/hdoc; гл. 2 — …/124/hdoc; гл. 3 — …/125/hdoc; гл. 5 — …/127/hdoc; прил. 3 — …/133/hdoc.
- «Руководство администратора»: гл. 5 — …/104/hdoc; гл. 6 — …/105/hdoc; гл. 7 — …/106/hdoc; прил. 3 — …/115/hdoc.
- «Руководство разработчика»: гл. 9 — …/54/hdoc; прил. 8 — …/92/hdoc.
- Методические статьи: https://its.1c.ru/db/metod8dev/content/5904/hdoc (15.07.2019), …/5946/hdoc (29.10.2019), …/5945/hdoc (15.05.2018), …/6008/hdoc (09.11.2023), …/5899/hdoc (12.05.2016), …/5908/hdoc (25.07.2022), …/5834/hdoc (18.02.2015), …/5813/hdoc (18.02.2015), …/2926/hdoc (30.10.2008), …/2371/hdoc, …/2374/hdoc, …/2377/hdoc, …/2379/hdoc (11.04.2008).
- Список поддерживаемых СУБД: https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/spisok-podderzhivaemykh-subd/ (20.10.2026).

Microsoft Learn (исходники `https://raw.githubusercontent.com/MicrosoftDocs/sql-docs/live/docs/<путь>.md`, страница — `https://learn.microsoft.com/en-us/sql/<путь>`; прочитаны 20.10.2026):

- Установка: `database-engine/install-windows/install-sql-server-from-the-command-prompt`, `…/install-sql-server-using-a-configuration-file`, `…/view-and-read-sql-server-setup-log-files`, `…/install-sql-server-servicing-updates`, `…/installing-updates-from-the-command-prompt`; `sql-server/install/hardware-and-software-requirements-for-installing-sql-server-2022` и `…-2025`, `sql-server/install/configure-the-windows-firewall-to-allow-sql-server-access`, `sql-server/what-s-new-in-sql-server-2025`, `database-engine/breaking-changes-to-database-engine-features-in-sql-server-2025`.
- Службы и права: `database-engine/configure-windows/configure-windows-service-accounts-and-permissions`, `…/scm-services-configure-server-startup-options`, `…/database-engine-service-startup-options`, `…/change-server-authentication-mode`, `relational-databases/databases/database-instant-file-initialization`, `database-engine/configure-windows/enable-the-lock-pages-in-memory-option-windows`.
- Параметры: `database-engine/configure-windows/` + `server-configuration-options-sql-server`, `server-memory-server-configuration-options`, `configure-the-max-degree-of-parallelism-server-configuration-option`, `configure-the-cost-threshold-for-parallelism-server-configuration-option`, `optimize-for-ad-hoc-workloads-server-configuration-option`, `view-or-configure-the-backup-compression-default-server-configuration-option`, `…-backup-compression-algorithm-…`, `backup-checksum-default`, `remote-admin-connections-server-configuration-option`, `blocked-process-threshold-server-configuration-option`.
- Сеть и шифрование: `database-engine/configure-windows/configure-a-server-to-listen-on-a-specific-tcp-port`, `…/configure-sql-server-encryption`, `…/certificate-requirements`, `tools/sqlcmd/sqlcmd-utility`; драйверы — `connect/oledb/oledb-driver-for-sql-server`, `connect/oledb/major-version-differences`, `connect/oledb/features/registry-settings`, `connect/oledb/release-notes-for-oledb-driver-for-sql-server`, `relational-databases/native-client/sql-server-native-client`.
- Базы и сортировки: `relational-databases/databases/tempdb-database`, `…/model-database`, `…/rebuild-system-databases`, `t-sql/statements/create-database-transact-sql`, `t-sql/statements/alter-database-transact-sql-file-and-filegroup-options`, `relational-databases/collations/collation-and-unicode-support`, `…/set-or-change-the-server-collation`.
- Флаги, совместимость, оценщик: `t-sql/database-console-commands/dbcc-traceon-trace-flags-transact-sql`, `t-sql/statements/alter-database-transact-sql-compatibility-level` (+ `includes/compatibility-levels`), `t-sql/statements/alter-database-scoped-configuration-transact-sql`, `relational-databases/performance/cardinality-estimation-sql-server`.
- DMV и функции: `t-sql/functions/serverproperty-transact-sql`, `relational-databases/system-dynamic-management-objects/…` — страницы `sys-dm-server-services`, `sys-dm-server-registry`, `sys-dm-os-sys-info`, `sys-dm-os-volume-stats`, `sys-dm-exec-cached-plans`, `sys-dm-exec-connections`, `sys-dm-os-loaded-modules` (с суффиксом `-transact-sql`), `sys-dm-tran-version-store-space-usage`; `relational-databases/system-stored-procedures/sp-readerrorlog-transact-sql`.
- Linux: `linux/configure/mssql-conf`, `linux/install-upgrade/quickstart-install-ubuntu`, `linux/install-upgrade/unattended-install-ubuntu`, `linux/sql-server-linux-release-notes` (+ `linux/includes/linux-supported-platforms-2022`, `…-2025`).
- Azure VM (64 КБ): `https://raw.githubusercontent.com/MicrosoftDocs/sql-docs/live/azure-sql/virtual-machines/windows/performance-guidelines-best-practices-storage.md`.
- Статьи поддержки (`https://raw.githubusercontent.com/MicrosoftDocs/SupportArticles-docs/main/support/sql/<путь>.md`, страница — `https://learn.microsoft.com/en-us/troubleshoot/sql/<путь>`): `database-engine/security/antivirus-and-sql-server`, `database-engine/performance/recommendations-reduce-allocation-contention`, `database-engine/database-file-operations/troubleshoot-os-4kb-disk-sector-size`, `releases/servicing-models-sql-server`, `releases/new-mu-servicing-model`, `database-engine/connect/network-related-or-instance-specific-error-occurred-while-establishing-connection` (строка `Server is listening on`).

Добавлено при независимой сверке 20.10.2026:

- MS Learn: `connect/oledb/applications/installing-oledb-driver-for-sql-server` (тихая установка, `IACCEPTMSOLEDBSQLLICENSETERMS`, Visual C++ Redistributable), `connect/oledb/features/registry-settings` (правило «более безопасного» для `Flag1`/`Flag2`), `database-engine/configure-windows/diagnostic-connection-for-database-administrators`, `includes/compatibility-levels`, `includes/snac-removed-oledb-and-odbc`, `relational-databases/system-catalog-views/` (`sys-configurations`, `sys-databases`, `sys-database-files`, `sys-master-files`, `sys-database-scoped-configurations`) и DMV `sys-dm-os-process-memory`, `sys-dm-os-memory-nodes`, `sys-dm-os-nodes`, `sys-dm-db-file-space-usage`, `sys-dm-exec-sessions`, `sys-dm-os-wait-stats` — имена столбцов во всех запросах статьи.
- Сроки поддержки: `https://learn.microsoft.com/en-us/lifecycle/products/sql-server-2016`, `…-2017`, `…-2025` (20.10.2026).
- ИТС: «Клиент-серверный вариант» гл. 2, разд. 2.1 (клиенты не обращаются к СУБД напрямую) и 2.3; разд. 1.5.4 — условие «режим совместимости выше 8.3.7» для требований к драйверу.

Смежные статьи базы: `../1c-windows/02-ms-sql-server-dlya-1c.md`, `../1c-windows/06-windows-server-dlya-administratora-1c.md`, `../its-docs/otlichiya-8.5.1-ot-8.3.27.md`, `../its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`.

## Что не удалось подтвердить

1. Требование 1С к сортировке экземпляра и то, с какой сортировкой платформа создаёт базу MS SQL (по языку ИБ?) и указывает ли `COLLATE` для временных таблиц, — в ИТС не описано; правило «сортировка экземпляра = сортировке баз» — практика. Имя `Cyrillic_Generic_CI_AS` в прил. 8 ИТС, вероятно, опечатка.
2. Какой `CREATE DATABASE` выполняет платформа (задаёт ли размеры и прирост файлов) — от этого зависит, сработает ли совет ИТС настроить прирост в `model`.
3. Включает ли платформа `READ_COMMITTED_SNAPSHOT` у базы и задаёт ли уровень совместимости базы.
4. Как платформа 8.3.27 / 8.5 передаёт OLE DB Driver параметры `Encrypt` и `TrustServerCertificate`; какой мажорной версии драйвера соответствует `hResultOLEDB` в 8.3.27; поддерживает ли 8.3.27 драйвер 19.
5. Принимает ли поле «Сервер баз данных» 1С префикс `tcp:` и формы `server\instance`, `server,port`; порядок протоколов по умолчанию у OLE DB Driver 18.
6. Ключи `QUIET`, `UPDATEENABLED`, `UPDATESOURCE` в `ConfigurationFile.ini` — по аналогии с параметрами командной строки; коды возврата `setup.exe`; точные названия страниц мастера установки 2022.
7. ~~Имя свойства согласия с лицензией в MSI OLE DB Driver~~ — уточнено 20.10.2026 по MS Learn: `IACCEPTMSOLEDBSQLLICENSETERMS=YES` (раздел 8.4).
8. Срок пробной редакции Evaluation (по практике 180 дней).
9. Пункт Configuration Manager 2019+ для выдачи права LPIM, упомянутый Microsoft.
10. Влияние отложенного автозапуска SQL Server 2022+ на старт кластера 1С на той же машине.
11. Сценарий «MAXDOP только для одной базы на время реструктуризации» и значения `cost threshold for parallelism` 25–50 — практика, не ИТС.
12. Совместимость с 1С функции Memory-optimized TempDB metadata, флагов 7471, 3226, параметра `optimize for ad hoc workloads`; влияние PSP-оптимизации (2022) на запросы 1С.
13. Флаг 2330 недокументирован Microsoft (отсутствие в справочнике флагов сверено 20.10.2026) — его эффект известен только по ИТС.
14. Выравнивание разделов по 1 МБ по умолчанию в современных Windows — практика.
15. ~~Строки журнала ошибок `Server is listening on …`~~ — подтверждено 20.10.2026 статьёй поддержки Microsoft (раздел 3.7); тексты для IFI и LPIM подтверждены раньше.
16. Можно ли опустить `/SQLSVCACCOUNT` и `/AGTSVCACCOUNT` в тихой установке (документация называет их обязательными); выдаёт ли setup права SID службы на нестандартные каталоги данных.
17. Пометка «только для Windows» у MS SQL в [ИТС-КС разд. 3.2.1] против допуска версии для Linux на v8.1c.ru — какой источник актуальнее для 8.3.27.
