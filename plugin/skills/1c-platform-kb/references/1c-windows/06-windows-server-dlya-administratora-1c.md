# Windows Server как ОС для сервера 1С: версии, первичная настройка, службы, сеть, электропитание, антивирус, журналы, резервное копирование ОС

> **Официальные тексты по теме:** «Клиент-серверный вариант. Руководство администратора» 8.3.27, гл. 1 (требования к ОС) — https://its.1c.ru/db/v8327doc/content/123/hdoc, конспект `../its-docs/cs-gl01-trebovaniya.md`; методические статьи ИТС «Check-list по настройке рабочих серверов в продукционной зоне» (https://its.1c.ru/db/metod8dev/content/5899/hdoc, 12.05.2016) и «Инструкция по настройке рабочих серверов с Технологической Платформой 1С:Предприятие» (https://its.1c.ru/db/metod8dev/content/5908/hdoc, 25.07.2022); документация Microsoft — learn.microsoft.com (Windows Server, PowerShell, сроки поддержки).

> ⚠ Статус: написано 19.10.2026 по полным текстам документации ИТС 8.3.27, методическим статьям ИТС и Microsoft Learn (страницы прочитаны в этот день); на сервере не проверялось.

> Область: Windows Server как операционная система под сервер 1С и сопутствующие службы — что выбрать, как настроить, обслуживать и диагностировать на уровне ОС. Установка платформы, регистрация службы агента и правила брандмауэра для портов 1С — в `01-ustanovka-servera-i-sluzhba-windows.md`. MS SQL Server — в `02-ms-sql-server-dlya-1c.md`, IIS — в `03-veb-publikaciya-iis.md`. Домен, клиенты и терминальный сервер — в `04-domen-kerberos-klienty-terminalnyj-server.md`. Лицензии и диагностика 1С (техжурнал, дампы, счётчики) — в `05-licenzii-diagnostika-otlichiya-ot-linux.md`. У этого пользователя сервер 1С и PostgreSQL работают на Ubuntu; статья нужна для Windows-серверов организации и как справочник.

**Как читать статью**

- **[ИТС-КС разд. N]** — «Клиент-серверный вариант. Руководство администратора» 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС с датой редакции.
- **[MS Learn]** — документация Microsoft (learn.microsoft.com, исходники MicrosoftDocs на GitHub), прочитана 19.10.2026.
- **[практика]** — устоявшаяся практика; в первоисточнике в таком виде не описано.
- **⚠** — не подтверждено первоисточником, проверить на своей системе.
- Команды PowerShell выполнять в окне **«Windows PowerShell (Администратор)»**, если не сказано иное; `cmd` — тоже от имени администратора.

## Кратко — главные факты и команды

1. **Windows Server 2025 в перечне ОС документации 8.3.27 нет.** Для сервера 1С перечислены 2012, 2012 R2, 2016, 2019, 2022 [ИТС-КС разд. 1]. Для 8.5.x перед выбором 2025 проверить актуальные системные требования на ИТС ⚠.
2. **Сроки поддержки Microsoft** [MS Learn, lifecycle]:
   - Windows Server 2016 — расширенная поддержка до **12.01.2027** (через 3 месяца);
   - 2019 — до 09.01.2029;
   - 2022 — основная поддержка закончилась 13.10.2026, расширенная до 14.10.2031;
   - 2025 — основная до 13.11.2029, расширенная до 14.11.2034.
3. **Server Core и Desktop Experience выбираются при установке**, потом переключиться нельзя — только переустановка [MS Learn]. Microsoft рекомендует Server Core. Для 1С-сервера с консолью кластера (MMC) практичнее Desktop Experience, если нет навыка управлять удалённо [практика].
4. **Минимум для Windows Server 2025** [MS Learn]:
   - процессор x64 1,4 ГГц с SSE4.2 и POPCNT;
   - ОЗУ 2 ГБ (с Desktop Experience рекомендуется 4 ГБ);
   - системный раздел не меньше 32 ГБ, это абсолютный минимум. При ОЗУ больше 16 ГБ нужно больше места под файл подкачки и дампы.
5. Первичная настройка Server Core — **SConfig**: запускается сам, начиная с 2022; пункт 4 — удалённое управление, 5 — обновления, 15 — выход в PowerShell. Отключить автозапуск — `Set-SConfig -AutoLaunch $False` [MS Learn].
6. План электропитания — **«Высокая производительность»** [ИТС-мет 5899, 5908]; Microsoft по умолчанию ставит «Сбалансированный» и рекомендует высокую производительность для приложений, чувствительных к задержкам [MS Learn]: `powercfg /list`, `powercfg /setactive <GUID плана>`.
7. **На рабочих серверах кластера не должны одновременно работать IPv4 и IPv6** [ИТС-мет 5908, разд. 5.4]. Microsoft не рекомендует отключать IPv6 — вместо этого «предпочитать IPv4»: `DisabledComponents = 0x20` в `HKLM\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters`, затем перезагрузка [MS Learn].
8. Сетевой стек под много соединений [ИТС-мет 5908, разд. 6]:
   - диапазон динамических портов: `netsh int ipv4 set dynamicport tcp start=10000 num=55536` (и `udp`); по умолчанию с Windows Server 2008 — 49152–65535 [MS Learn]. В методичке ИТС стоит `num=64510` — это ошибка: конец диапазона вышел бы за 65535, а Windows такое не принимает [MS Learn];
   - параметры реестра `Tcpip\Parameters` и `AFD\Parameters` — подробно в разд. 6.
9. Признаки исчерпания портов — события **4227 и 4231** в журнале «Система» и масса соединений `TIME_WAIT` у одного PID в `netstat -anob`. Порт в `TIME_WAIT` по умолчанию держится 4 минуты [MS Learn].
10. **Антивирус**: на рабочих серверах кластера в закрытом сегменте 1С его не ставить — защищать клиентские компьютеры [ИТС-мет 5908, разд. 10.4]. Если политика безопасности требует антивирус — исключения через `Add-MpPreference -ExclusionPath / -ExclusionProcess` [MS Learn].
11. Каталог кластера (`srvinfo`): **не сжимать** средствами NTFS и **не включать в файловый бэкап** — там сеансовые данные [ИТС-мет 5908, разд. 10.1–10.2].
12. Пользователи, от которых работают процессы кластера (если через `swpuser.ini`), должны иметь **профиль Windows** — достаточно одного интерактивного входа. Агенту (`ragent`) нужны права администратора и политики «Настройка квот памяти для процесса» и «Замена маркера уровня процесса» [ИТС-мет 5899].
13. Для сбора загрузки оборудования из ЦКК пользователь, от которого работает `rphost`, должен входить в группу **«Пользователи системного монитора»** (Performance Monitor Users) [ИТС-мет 5899].
14. Резервное копирование ОС: компонент Windows Server Backup и `wbadmin start backup`. Если на сервере есть MS SQL со своими бэкапами, использовать **`-vssCopy`**: `-vssFull` обновляет историю резервных копий файлов и может обрезать журналы приложений [MS Learn].
15. Журналы событий из командной строки: `wevtutil qe System /c:20 /rd:true /f:text`, экспорт — `wevtutil epl System C:\Temp\system.evtx` [MS Learn]. В PowerShell — `Get-WinEvent`.
16. Время: в домене — `w32tm /config /syncfromflags:domhier /update`, вне домена — `/manualpeerlist:"…" /syncfromflags:manual /update`; проверка — `w32tm /query /status /verbose` [MS Learn]. Расхождение времени ломает Kerberos — `04-…`.
17. В Windows Server 2025 **сервер OpenSSH установлен по умолчанию**, включается в Server Manager («Remote SSH Access») [MS Learn]. В 2019–2022 его ставят отдельно.
18. Активация Windows: `slmgr /dlv` (подробно), `slmgr /xpr` (срок), `slmgr /ato` (активировать) [MS Learn].

## 1. Версии Windows Server и поддержка 1С

### 1.1. Что поддерживает платформа

| ОС | 8.3.27: сервер 1С [ИТС-КС разд. 1] | Поддержка Microsoft [MS Learn] |
|---|---|---|
| Windows Server 2012 / 2012 R2 | да | расширенная закончилась 10.10.2023, платные обновления ESU — 13.10.2026; не использовать |
| Windows Server 2016 | да | расширенная до 12.01.2027 |
| Windows Server 2019 | да | расширенная до 09.01.2029 |
| Windows Server 2022 | да | основная закончилась 13.10.2026, расширенная до 14.10.2031 |
| Windows Server 2025 | **в перечне 8.3.27 нет** ⚠ | основная до 13.11.2029, расширенная до 14.11.2034 |

- Документация 8.3.27 требует «все актуальные обновления используемой версии ОС» [ИТС-КС разд. 1].
- 32-разрядный сервер 1С на Windows Server не поддерживается: в списке для x86 Windows Server отмечен как неподдерживаемый [ИТС-КС разд. 1].
- **Вывод на октябрь 2026:**
  - новый сервер под 8.3.27 — Windows Server 2022: поддерживается 1С и получает обновления безопасности до 2031 года;
  - серверы на 2016 планировать к переносу до января 2027 года;
  - 2025 — только после подтверждения 1С для вашей версии платформы [практика].

### 1.2. Редакции

- **Standard** и **Datacenter** [MS Learn, сравнение редакций]. Для сервера 1С функциональных различий почти нет: Hyper-V, Storage Replica, IIS, Windows Server Backup есть в обеих.
- Только в Datacenter (и Datacenter: Azure Edition) — Storage Spaces Direct, Host Guardian для Hyper-V, неограниченная репликация.
- **Hotpatching** (установка обновлений без перезагрузки) в 2025 Standard и Datacenter доступна только для серверов, подключённых к Azure Arc, при активной Software Assurance или подписке [MS Learn]. Без этого — обычные обновления с перезагрузкой.
- Сколько гостевых ОС можно запустить на одной лицензии (Standard — 2 виртуальные машины на полностью лицензированный хост, Datacenter — без ограничения) — это условия лицензирования Microsoft, а не техническое ограничение. Проверять по актуальным условиям лицензирования ⚠.

### 1.3. Server Core или Desktop Experience

| | Server Core | Desktop Experience |
|---|---|---|
| Интерфейс | PowerShell, SConfig, cmd | обычный рабочий стол Windows |
| Диск | меньше (≈ на 4 ГБ) | больше |
| Роли локально | только PowerShell | Server Manager или PowerShell |
| MMC | нет (ставится через App Compatibility FOD) | есть |
| Поверхность атаки | значительно меньше | без сокращения |

Источник — [MS Learn]. Переключиться между вариантами после установки нельзя.

**Для 1С:**
- консоль администрирования кластера — оснастка MMC. На Server Core её нет, кластер администрируют через `ras`/`rac` (`kb/1c/03`) или консолью с другой машины [практика];
- конфигуратор и толстый клиент на Server Core не запускают [практика];
- методички ИТС ссылаются на графические инструменты: Control Panel, Process Explorer, RAMMap, BgInfo, Windows Performance Recorder [ИТС-мет 5899]. С ними удобнее Desktop Experience.

Итог: сервер СУБД или веб-сервер можно ставить на Core. Рабочий сервер 1С — на Desktop Experience, если администраторы не готовы работать только удалённо [практика].

## 2. Аппаратные требования Windows Server 2025

Источник — [MS Learn, hardware-requirements]:

- **Процессор:** x64 от 1,4 ГГц, поддержка NX/DEP, CMPXCHG16b, LAHF/SAHF, PrefetchW, SLAT (EPT/NPT). Для 2025 дополнительно SSE4.2 и POPCNT. Старые процессоры и некоторые эмулируемые ВМ этого не умеют — проверка утилитой Coreinfo из Sysinternals.
- **ОЗУ:** 2 ГБ для Server Core, 2 ГБ для Desktop Experience (рекомендуется 4 ГБ). Для физических серверов — ECC. Ставить на ВМ с минимальными 1 ядром и 1024 МБ нельзя: дайте установке не меньше 1280 МБ, потом можно уменьшить.
- **Диск:** не меньше 32 ГБ под системный раздел — абсолютный минимум (Server Core с ролью IIS). При ОЗУ больше 16 ГБ нужно больше места под файл подкачки, гибернацию и дампы.
- Это минимум для ОС. Расчёт под 1С — `kb/1c/10` и методичка «Расчёт параметров серверного оборудования» (`kb/its-metod/raschet-oborudovaniya-i-nagruzochnoe-testirovanie.md`) [ИТС-мет 5810].

## 3. Первичная настройка после установки

### 3.1. SConfig (Server Core; на Desktop Experience тоже запускается командой `SConfig`)

- Начиная с Windows Server 2022, на Server Core SConfig стартует сам, оболочка по умолчанию — PowerShell (раньше — cmd) [MS Learn].
- Основные пункты меню:

| Пункт | Что делает |
|---|---|
| 1 | домен или рабочая группа |
| 2 | имя компьютера |
| 3 | локальный администратор |
| 4 | удалённое управление (PowerShell remoting, Windows Admin Center, оснастки MMC) и ответ на ping; удалённое управление в домене и в локальной подсети включено по умолчанию, ping — выключен |
| 5 | обновления: `A` — ставить автоматически (каждый день в 3:00 по часовому поясу сервера), `D` — только скачивать (по умолчанию), `M` — вручную |
| 6 | установить обновления |
| 7 | удалённый рабочий стол |
| 8 | сеть |
| 9 | дата и время |
| 10 | диагностические данные (телеметрия) |
| 11 | активация Windows |
| 15 | выход в PowerShell |

Номера пунктов 1–3 и 6–11 взяты из порядка разделов документации; на экране своей версии сверить ⚠.

- Выключить автозапуск SConfig: `Set-SConfig -AutoLaunch $False`. «Перезагрузить» PowerShell на Server Core — `exit`: окно закроется и откроется новое [MS Learn].
- `diskpart` объявлен устаревшим, вместо него — командлеты PowerShell для дисков (`Get-Disk`, `Initialize-Disk`, `New-Partition`, `Format-Volume`) [MS Learn].

### 3.2. Те же действия в PowerShell (для Desktop Experience и сценариев)

```powershell
# от имени администратора
Rename-Computer -NewName 'srv-1c-win01' -Restart
# статический адрес (имя адаптера — из Get-NetAdapter)
New-NetIPAddress -InterfaceAlias 'Ethernet' -IPAddress 10.0.0.21 -PrefixLength 24 -DefaultGateway 10.0.0.1
Set-DnsClientServerAddress -InterfaceAlias 'Ethernet' -ServerAddresses 10.0.0.10,10.0.0.11
# ввод в домен (запросит учётные данные доменного администратора)
Add-Computer -DomainName 'corp.example' -Restart
# проверка
Get-NetIPConfiguration; (Get-CimInstance Win32_ComputerSystem).Domain
```

Командлеты — стандартные модули NetTCPIP, DnsClient, Management [практика]. Имена и адреса в примере условные.

### 3.3. Время

Источник — [MS Learn, Windows Time Service Tools and Settings]:

```cmd
:: член домена — синхронизация по иерархии домена (обычный случай)
w32tm /config /syncfromflags:domhier /update
:: вне домена — свои NTP-серверы
w32tm /config /manualpeerlist:"ntp1.example.uz ntp2.example.uz" /syncfromflags:manual /update
:: проверить источник и смещение
w32tm /query /status /verbose
w32tm /query /configuration
```

Для Kerberos расхождение часов клиента и контроллера домена должно оставаться в пределах допуска домена (по умолчанию 5 минут) — `04-…` [практика]. Сервер 1С на Linux синхронизировать с тем же источником — `kb/linux/08`.

### 3.4. Активация Windows

Источник — [MS Learn, slmgr]:
- `slmgr /dlv` — подробные сведения о лицензии;
- `slmgr /xpr` — срок активации;
- `slmgr /ipk <ключ>` — установить ключ;
- `slmgr /ato` — активировать.

KMS и AVMA (автоматическая активация ВМ на хосте Datacenter) — по документации Microsoft. Активация Windows не связана с лицензиями 1С (`05-…`), но смена оборудования ВМ влияет на обе: программная лицензия 1С привязана к параметрам ОС и оборудования.

### 3.5. Роли и компоненты

```powershell
Get-WindowsFeature | Where-Object Installed            # что установлено
Install-WindowsFeature -Name Windows-Server-Backup     # пример: компонент резервного копирования
Install-WindowsFeature -Name <Имя> -IncludeManagementTools -Restart
```

`-IncludeManagementTools` и `-Restart` — параметры `Install-WindowsFeature` [MS Learn]. Имя компонента `Windows-Server-Backup` — по практике, сверить в `Get-WindowsFeature *Backup*` ⚠. Компоненты IIS для публикации 1С — `03-…`.

## 4. Удалённое управление

- **PowerShell remoting (WinRM):** в домене включён по умолчанию (пункт 4 SConfig) [MS Learn]. Вручную — `Enable-PSRemoting -Force`. Подключение — `Enter-PSSession -ComputerName <сервер>`, массово — `Invoke-Command`.
- **Windows Admin Center** — браузерная консоль управления серверами (службы, события, производительность, роли, обновления); ставится отдельно на шлюз или на ПК администратора [MS Learn].
- **RSAT** — оснастки управления на Windows 10/11 администратора; для Server Core нужна версия, входящая в Windows 10 или новее [MS Learn].
- **RDP** — пункт 7 SConfig или «Параметры → Удалённый рабочий стол». Для администрирования — до двух одновременных сеансов без лицензий RDS. Терминальный сервер для пользователей 1С — `04-…` [практика].
- **OpenSSH:** в Windows Server 2025 серверная часть установлена по умолчанию, включается в Server Manager → «Remote SSH Access» [MS Learn]. В 2019 и 2022 ставится как компонент по требованию: `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0` [практика ⚠ имя возможности сверить: `Get-WindowsCapability -Online -Name OpenSSH*`].

## 5. Службы Windows

```powershell
Get-Service | Where-Object DisplayName -like '*1C*'          # службы 1С
Get-CimInstance Win32_Service -Filter "Name like '1C%'" |
  Select-Object Name, StartName, StartMode, State, PathName   # учётная запись и командная строка службы
Restart-Service -Name '<имя службы>'                         # перезапуск (осторожно — сеансы 1С оборвутся)
```

- Тип запуска и учётную запись меняют в `services.msc` или `sc.exe config` [MS Learn, sc config]:
  - `sc.exe config <служба> start= delayed-auto` — отложенный автозапуск, полезен, если служба 1С стартует раньше сети или СУБД;
  - `sc.exe config <служба> obj= <домен\учётная_запись> password= <пароль>`.
  - В синтаксисе `sc` после `=` обязателен пробел. В PowerShell писать `sc.exe`, а не `sc` — `sc` там псевдоним `Set-Content`.
- Действия при сбое (перезапуск службы) — вкладка «Восстановление» в `services.msc` или `sc.exe failure <служба> reset= 86400 actions= restart/60000` [практика ⚠ синтаксис сверить по `sc failure /?`].
- Регистрация и удаление службы агента 1С (`ragent -instsrvc` и др.), `ras` как служба — в `01-…`.

## 6. Сеть и TCP-стек под 1С

### 6.1. IPv4 и IPv6

- ИТС требует, чтобы на рабочих серверах кластера не использовались одновременно IPv4 и IPv6 [ИТС-мет 5908, разд. 5.4].
- Microsoft **не рекомендует отключать IPv6** или отвязывать его от адаптеров: часть компонентов Windows перестаёт работать. Рекомендуемый способ — «предпочитать IPv4» [MS Learn, configure-ipv6-in-windows]:

```powershell
# от имени администратора; потом перезагрузка
New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters' `
  -Name DisabledComponents -PropertyType DWord -Value 0x20 -Force
# проверка после перезагрузки: имя сервера должно резолвиться в IPv4
ping <имя_сервера_1С>
```

- Значение `0xFF` полностью отключает IPv6 — Microsoft так не советует [MS Learn].
- В DNS у серверов кластера не должно быть AAAA-записей, которые клиенты будут предпочитать [практика].

### 6.2. Много соединений: порты и очереди

ИТС [ИТС-мет 5908, разд. 6] рекомендует для серверов с большим числом подключений:

| Где | Параметр | Значение по ИТС |
|---|---|---|
| `HKLM\System\CurrentControlSet\Services\Tcpip\Parameters` | `MaxFreeTcbs` | 100000 |
| то же | `TcpTimedWaitDelay` | 30 |
| то же | `MaxUserPort` | 65534 |
| `HKLM\System\CurrentControlSet\Services\AFD\Parameters` | `EnableDynamicBacklog` | 1 |
| то же | `MinimumDynamicBacklog` | 20 |
| то же | `MaximumDynamicBacklog` | 20000 |
| то же | `DynamicBacklogGrowthDelta` | 10 |
| `netsh` | диапазон исходящих портов TCP и UDP | в методичке: `netsh int ipv4 set dynamicport tcp start=10000 num=64510` и то же для `udp`. **Так команда не сработает:** 10000 + 64510 − 1 = 74509 > 65535. Для диапазона 10000–65535 нужно `num=55536` |

**Комментарии по документации Microsoft:**
- С Windows Vista и Server 2008 диапазон динамических портов по умолчанию — 49152–65535 (16 384 порта), раньше был 1025–5000. Диапазон задаётся **через `netsh`**, а не через реестр; минимальный размер — 255, минимальный начальный порт — 1025 [MS Learn, KB929851]. Поэтому `MaxUserPort` в современных Windows, по всей видимости, диапазон уже не определяет — главная команда здесь `netsh` ⚠.
- Посмотреть текущий диапазон: `netsh int ipv4 show dynamicport tcp` [MS Learn].
- **Перед расширением диапазона с 10000** проверьте, что на сервере никто не слушает порты 10000–49151: именованные экземпляры SQL Server с фиксированным портом, агенты мониторинга, сам IIS. Иначе исходящее соединение может занять порт раньше службы. Порты 1С (1540, 1541, 1545, 1560–1591) ниже 10000 и не пересекаются [практика].
- `TcpTimedWaitDelay` укорачивает `TIME_WAIT` (по умолчанию 4 минуты [MS Learn, port exhaustion]). Параметры AFD (`*DynamicBacklog*`) первоисточником Microsoft в этой сессии не подтверждены ⚠ — менять только при симптомах.

**Диагностика исчерпания портов** [MS Learn]:

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; Id=4227,4231} -MaxEvents 20
netstat -anob | Select-String TIME_WAIT | Measure-Object        # сколько соединений в TIME_WAIT
Get-NetTCPConnection -State TimeWait | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 5
```

Ошибка 1С «An operation on a socket could not be performed because the system lacked sufficient buffer space or because a queue was full» — именно этот случай [ИТС-мет 5908, разд. 5.2].

### 6.3. Брандмауэр Windows

- Три профиля: «Домен», «Частный», «Общедоступный». Правило для 1С создавать в профиле «Домен» (сервер в домене) и при необходимости ограничивать `-RemoteAddress` подсетью клиентов [практика].
- Командлеты — `New-NetFirewallRule` (параметры `-DisplayName`, `-Direction`, `-Protocol`, `-LocalPort`, `-Action`, `-Profile`, `-RemoteAddress`), `Get-NetFirewallRule`, `Set-NetFirewallRule` [MS Learn]. Старая альтернатива — `netsh advfirewall firewall add rule …` [MS Learn].
- Конкретные правила для портов 1С (1540, 1541, 1545, диапазон 1560–1591, 1542, 1550) — в `01-…`. Брандмауэр не должен мешать процессам кластера общаться между собой: учитывайте порты из свойств центрального сервера, кластера и рабочих серверов и порт `ras` [ИТС-мет 5908, разд. 5.3].

## 7. Электропитание

- ИТС: план электропитания на рабочих серверах — «Высокая производительность» [ИТС-мет 5899; 5908, разд. 5.5].
- Microsoft: по умолчанию «Сбалансированный» — хорошая энергоэффективность при небольшой потере производительности. «Высокая производительность» — для приложений, чувствительных к задержкам и изменению частоты процессора [MS Learn, power performance tuning].

```cmd
powercfg /list
:: в списке найти «Высокая производительность» и активировать по её GUID, например:
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-cf8e2a3cd3e1
powercfg /getactivescheme
```

- GUID встроенного плана «Высокая производительность» — значение, которое обычно выводит `powercfg /list` [практика]. Берите GUID из своего вывода.
- Тонкая настройка через `Powercfg -setacvalueindex scheme_current sub_processor …` (параметры `PERFEPP`, `PROCTHROTTLEMIN`, `PROCTHROTTLEMAX`) описана в [MS Learn]. Для 1С обычно достаточно выбрать план.
- **На виртуальной машине** план внутри гостя почти ни на что не влияет — важен план и BIOS хоста (C-states, Turbo) [практика]. Для хоста Hyper-V — та же рекомендация.

## 8. Учётные записи и профили для процессов 1С

- По умолчанию установщик создаёт пользователя `USR1CV8` для службы агента. Варианты учётной записи службы — `01-…`.
- **Отдельные пользователи для рабочих процессов (`swpuser.ini`)** [ИТС-мет 5899, 5908 разд. 3]:
  - установщик эту схему не готовит — пользователей, права и профили создают вручную;
  - пользователю главного агента (`ragent`) нужны права администратора и политики «Настройка квот памяти для процесса» (Adjust memory quotas for a process; обычно в ней уже есть «Администраторы») и «Замена маркера уровня процесса» (Replace a process level token; «Администраторов» там обычно нет). Обе — `secpol.msc` → «Локальные политики» → «Назначение прав пользователя»;
  - у каждого такого пользователя должен быть **профиль Windows** — в нём каталог временных файлов, данные приложения и переменные окружения. Проще всего один раз войти под ним интерактивно;
  - доступ этих пользователей к каталогам, которые рабочим процессам не нужны, ограничивают правами NTFS (`icacls`).
- Для сбора загрузки оборудования из «Центра контроля качества» пользователь, от которого работает `rphost`, — в группе «Пользователи системного монитора» [ИТС-мет 5899]:

```powershell
Add-LocalGroupMember -SID 'S-1-5-32-558' -Member 'USR1CV8'    # S-1-5-32-558 — встроенная группа Performance Monitor Users
Get-LocalGroupMember -SID 'S-1-5-32-558'
```

  SID встроенной группы указан по практике; русское имя группы зависит от языка ОС, поэтому удобнее по SID ⚠.
- **Документация требует другую группу.** Пользователь, от которого работают процессы кластера (по умолчанию `USR1CV8`), должен входить в группу **«Пользователи журналов производительности»** (Performance Log Users) и иметь права «Вход в качестве службы», «Вход в качестве пакетного задания», «Список содержимого папки» на каталог временных файлов [ИТС-КС разд. 1.3.2]. Методичка 5899 для сбора данных в ЦКК называет «Пользователи системного монитора» (Performance Monitor Users). Это разные встроенные группы (S-1-5-32-559 и S-1-5-32-558 — по практике ⚠). Выполнить оба требования: `Add-LocalGroupMember -SID 'S-1-5-32-559' -Member 'USR1CV8'`. Подробно о правах службы — `01-…`, разд. 3.
- Пользователь СУБД для каждой рабочей базы — свой, с именем, совпадающим с именем информационной базы: так в трассировках СУБД сразу видно, чья нагрузка [ИТС-мет 5899]. Подробно — `02-…`.

## 9. Антивирус

- **Позиция ИТС:** если рабочие серверы кластера стоят в зоне со строго ограниченным доступом, антивирус на них не ставят — он заметно снижает производительность почти без выигрыша в защите. Защищают пользовательские компьютеры, с которых идёт доступ к серверам и сетевым каталогам [ИТС-мет 5908, разд. 10.4].
- **Если антивирус обязателен** по политике безопасности — исключения [практика, механизм — MS Learn]:

```powershell
# Microsoft Defender: исключить каталоги и процессы 1С (пути — свои)
Add-MpPreference -ExclusionPath 'C:\Program Files\1cv8\srvinfo', 'D:\1C\LOGS', 'D:\1C\DUMPS'
Add-MpPreference -ExclusionProcess 'ragent.exe', 'rmngr.exe', 'rphost.exe'
Get-MpPreference | Select-Object ExclusionPath, ExclusionProcess     # проверка
```

  - Каталог кластера на вашем сервере может быть другим — смотрите параметр `-d` в командной строке службы (раздел 5). Каталоги данных и журналов SQL Server — по рекомендациям Microsoft для SQL (`02-…`).
  - Сторонний антивирус и Defender вместе: Defender переводят в пассивный режим [MS Learn].
  - Исключения по процессу снимают проверку файлов, которые открывает процесс, но не самого исполняемого файла [практика].

## 10. Диски и файловая система

- **Не сжимать** (NTFS-сжатие) диск или каталог кластера [ИТС-мет 5908, разд. 10.2].
- **Не включать каталоги кластера в файловый бэкап** (`exec backup` и аналоги): там сеансовые данные, копировать их не нужно, а нагрузку это создаёт [ИТС-мет 5908, разд. 10.1]. Резервировать нужно информационные базы (выгрузка `.dt` или бэкап СУБД — `02-…`, `kb/postgresql/04`) и файлы настроек.
- Сеансовые данные — на быстрых дисках; места должно хватать [ИТС-мет 5908, разд. 7.3].
- Дефрагментация: ИТС напоминает о периодической дефрагментации дисков Windows [ИТС-мет 5908, разд. 10.3]. Для SSD Windows по расписанию выполняет оптимизацию (TRIM), а не дефрагментацию. Проверить расписание — `Get-ScheduledTask -TaskName ScheduledDefrag`, вручную — `Optimize-Volume -DriveLetter D -Verbose` [практика ⚠].
- Размер кластера NTFS 64 КБ для файлов данных SQL Server — `02-…`.
- Свободное место: оповещение при остатке меньше 10 % [ИТС-мет 5899]. При ОЗУ больше 16 ГБ закладывайте место под файл подкачки и полный дамп памяти [MS Learn].

## 11. Журналы событий

```powershell
Get-WinEvent -LogName System -MaxEvents 50 | Format-Table TimeCreated, Id, ProviderName, Message -AutoSize
Get-WinEvent -FilterHashtable @{LogName='Application'; Level=1,2; StartTime=(Get-Date).AddDays(-1)}   # критические и ошибки за сутки
```

```cmd
wevtutil el                                   :: список журналов
wevtutil qe System /c:20 /rd:true /f:text     :: 20 последних событий журнала «Система», от новых к старым
wevtutil epl System C:\Temp\system.evtx       :: экспорт для передачи в поддержку
wevtutil gl Application                       :: свойства журнала (размер, хранение)
```

- Синтаксис `wevtutil` (`el`, `gl`, `sl`, `qe` с `/c:`, `/rd:`, `/f:`, `epl`) — [MS Learn].
- Что искать по 1С: падения служб (Service Control Manager, события 7031/7034), ошибки приложений (Application Error, событие 1000 с `rphost.exe`), исчерпание портов (4227, 4231) [практика; 4227/4231 — MS Learn]. События, которые пишет сама платформа, и настройка дампов — `05-…`.

## 12. Производительность и инструменты

- **Счётчики Performance Monitor** собирать постоянно, запуск — через планировщик заданий [ИТС-мет 5899]. Набор счётчиков и `logman`/`typeperf` — `05-…`.
- **Утилиты Sysinternals** держать в одном каталоге (например, `C:\Utils`): Process Explorer, RAMMap, ProcDump; BgInfo — чтобы на рабочем столе были имя сервера, место на дисках и адреса [ИТС-мет 5899].
- **Windows Performance Toolkit** (Windows Performance Recorder) на рабочих серверах. Проверка — запуск записи «Resource Analysis → CPU Usage» на несколько секунд [ИТС-мет 5899; методичка ссылается на Windows 8.1 SDK — сейчас WPT входит в Windows ADK ⚠].
- `powercfg /energy` — 60-секундный анализ проблем энергопотребления (таймеры, драйверы) [MS Learn].
- «Монитор ресурсов» (`resmon`) и `Get-Counter` — быстрый взгляд без настройки сборщика [практика].

## 13. Резервное копирование самой ОС

```powershell
Install-WindowsFeature Windows-Server-Backup         # один раз
```

```cmd
:: состояние системы и критические тома — для восстановления «на голое железо»
wbadmin start backup -backupTarget:E: -allCritical -systemState -vssCopy -quiet
:: каталог настроек 1С и скриптов на сетевую папку
wbadmin start backup -backupTarget:\\backup01\srv1c -include:C:\Scripts,"C:\Program Files\1cv8\conf" -vssCopy -quiet
wbadmin get versions
```

- Ключи `-backupTarget`, `-include`, `-allCritical`, `-systemState`, `-vssFull`, `-vssCopy`, `-quiet` — [MS Learn, wbadmin start backup].
- **`-vssFull` или `-vssCopy`:** `-vssFull` обновляет историю резервных копий файлов, журналы предыдущих копий могут быть обрезаны. Если SQL Server на этом сервере бэкапится своими средствами, брать **`-vssCopy`** [MS Learn]. Уточнено 20.10.2026 по руководству SQL Writer (sql-server-vss-writer-backup-guide): VSS-копия журнал SQL Server не копирует и цепочку журнала не рвёт. Но полная (не copy) VSS-копия становится новой базой для разностных копий SQL Server, и ваши разностные копии начнут считаться от неё — подробно в `../mssql/04-…`.
- Каталог кластера (`srvinfo`) в `-include` не добавлять [ИТС-мет 5908, разд. 10.1].
- Не реже раза в год проводить пробное восстановление с замером времени [ИТС-мет 5899].

## 14. Обновления Windows

- Режим — пункт 5 SConfig или групповые политики / WSUS [MS Learn]. На сервере 1С **не включать автоматическую установку с перезагрузкой**: режим «D» (только скачивать) или управление через WSUS с окном обслуживания [практика].
- Порядок на сервере 1С [практика]:
  1. заблокировать начало сеансов или дождаться окна;
  2. остановить службу агента 1С (`kb/1c/03` — блокировка, `01-…` — служба);
  3. установить обновления, перезагрузить;
  4. проверить, что служба 1С запустилась, и войти в базу.
- В кластере с несколькими рабочими серверами — по одному серверу.
- Hotpatch (Windows Server 2025) уменьшает число перезагрузок, но только через Azure Arc [MS Learn].

## 15. Hyper-V: сервер 1С и Linux-ВМ на Windows-хосте

- Установка Ubuntu Server в ВМ Hyper-V, поколение ВМ, Secure Boot для Linux, интеграционные службы — `kb/linux/11-ustanovka-ubuntu-server-i-vm.md`.
- Рекомендации Microsoft для Linux-гостей [MS Learn, Best Practices for running Linux on Hyper-V]:
  - на ВМ поколения 2 меню GRUB проскакивает слишком быстро (нет эмулируемого таймера);
  - в отказоустойчивом кластере у каждого сетевого адаптера ВМ — статический MAC;
  - планировщик ввода-вывода `none` (`noop`) для дисков ВМ.
- Список поддерживаемых версий Ubuntu — страница «Supported Ubuntu virtual machines on Hyper-V» [MS Learn].
- Для сервера 1С на ВМ: фиксированная память без Dynamic Memory, резерв vCPU, диски фиксированного размера на быстром хранилище [практика]. Учтите, что смена параметров ВМ может сбросить программную лицензию 1С (`05-…`, `kb/1c/04`).

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| Установщик Windows Server 2025 не стартует на старом сервере или ВМ | процессор без SSE4.2/POPCNT; ВМ с 1 ядром и 1024 МБ | проверить Coreinfo; дать установке ≥ 1280 МБ (разд. 2) |
| На Server Core нет консоли кластера 1С | MMC не установлена | администрировать через `ras`/`rac` или консолью с другой машины; либо ставить Desktop Experience (раздел 1.3) |
| Нужен графический интерфейс на установленном Server Core | переключение не поддерживается | только переустановка (раздел 1.3) |
| Клиенты 1С периодически не подключаются, в журнале 4227/4231 | исчерпаны динамические порты, много `TIME_WAIT` | разд. 6.2: `netsh … dynamicport`, найти процесс-источник |
| Сервер 1С «плавает» по скорости, частота CPU низкая | план «Сбалансированный» | «Высокая производительность» (разд. 7); на ВМ — настройки хоста |
| После отключения IPv6 перестали работать компоненты Windows | IPv6 отключён полностью (`0xFF`) или отвязан от адаптера | `DisabledComponents = 0x20` («предпочитать IPv4») (разд. 6.1) |
| Резкие задержки при работе пользователей, высокая нагрузка на диск | антивирус проверяет каталог кластера и журналы | исключения или отказ от антивируса в закрытом сегменте (разд. 9) |
| Рабочие процессы под пользователем из `swpuser.ini` не стартуют | нет профиля пользователя или прав у агента | один интерактивный вход; политики квот памяти и замены маркера (разд. 8) |
| После файлового бэкапа ОС «сломалась» цепочка бэкапов SQL | `wbadmin … -vssFull` | `-vssCopy` (разд. 13) |
| Kerberos-вход в 1С не работает после переноса ВМ | время ВМ разошлось с доменом | `w32tm` (разд. 3.3), синхронизация от домена, а не от хоста |
| Служба 1С падает после обновления ОС и не поднимается | перезагрузка во время работы, нет действий при сбое | плановые окна обновлений; «Восстановление» службы (разд. 5, 14) |

## Быстрая шпаргалка — задача → команда

| Задача | Команда (PowerShell или cmd от имени администратора) |
|---|---|
| Версия и сборка ОС | `Get-ComputerInfo -Property OsName,OsVersion,OsBuildNumber` или `winver` |
| Срок и состояние активации | `slmgr /dlv`, `slmgr /xpr` |
| Меню первичной настройки | `SConfig` |
| Установленные роли | `Get-WindowsFeature \| Where-Object Installed` |
| Службы 1С и их учётные записи | `Get-CimInstance Win32_Service -Filter "Name like '1C%'" \| Select Name,StartName,State,PathName` |
| Отложенный автозапуск службы | `sc.exe config <служба> start= delayed-auto` |
| Диапазон динамических портов | `netsh int ipv4 show dynamicport tcp` |
| Расширить диапазон (10000–65535) | `netsh int ipv4 set dynamicport tcp start=10000 num=55536`, то же для `udp` |
| Соединения в TIME_WAIT по процессам | `Get-NetTCPConnection -State TimeWait \| Group OwningProcess` |
| Предпочитать IPv4 | `DisabledComponents = 0x20` в `HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters`, перезагрузка |
| План электропитания | `powercfg /list`, `powercfg /setactive <GUID>`, `powercfg /getactivescheme` |
| Время | `w32tm /query /status /verbose`; `w32tm /config /syncfromflags:domhier /update` |
| Исключения Defender | `Add-MpPreference -ExclusionPath …`, `Get-MpPreference` |
| Последние ошибки «Система» | `wevtutil qe System /c:20 /rd:true /f:text` |
| Экспорт журнала | `wevtutil epl System C:\Temp\system.evtx` |
| Бэкап состояния системы | `wbadmin start backup -backupTarget:E: -allCritical -systemState -vssCopy -quiet` |
| Удалённая сессия | `Enter-PSSession -ComputerName <сервер>` |

## Источники

- ИТС: «Клиент-серверный вариант. Руководство администратора» 8.3.27, гл. 1 «Требования к аппаратуре и программному обеспечению» — https://its.1c.ru/db/v8327doc/content/123/hdoc (конспект `kb/its-docs/cs-gl01-trebovaniya.md`); «Руководство администратора», гл. 1 — https://its.1c.ru/db/v8327doc/content/100/hdoc.
- ИТС, методические статьи: «Check-list по настройке рабочих серверов в продукционной зоне» (12.05.2016) — https://its.1c.ru/db/metod8dev/content/5899/hdoc; «Инструкция по настройке рабочих серверов с Технологической Платформой 1С:Предприятие» (25.07.2022) — https://its.1c.ru/db/metod8dev/content/5908/hdoc; «Расчёт параметров серверного оборудования» — https://its.1c.ru/db/metod8dev/content/5810/hdoc.
- Microsoft Learn (прочитано 19.10.2026):
  - сроки поддержки — https://learn.microsoft.com/lifecycle/products/windows-server-2025 (а также `-2022`, `-2019`, `-2016`);
  - Server Core и Desktop Experience — `WindowsServerDocs/get-started/install-options-server-core-desktop-experience.md`;
  - аппаратные требования — `get-started/hardware-requirements.md`;
  - сравнение редакций — `get-started/editions-comparison.md`;
  - новое в 2025 (OpenSSH) — `get-started/whats-new-windows-server-2025.md`;
  - hotpatch — `get-started/hotpatch.md`;
  - SConfig — `administration/server-core/server-core-sconfig.md`;
  - электропитание — `administration/performance-tuning/hardware/power/power-performance-tuning.md`;
  - служба времени — `networking/windows-time-service/Windows-Time-Service-Tools-and-Settings.md`;
  - команды `wbadmin start backup`, `wevtutil`, `sc config`, `netsh advfirewall`, `vssadmin` — `administration/windows-commands/…`;
  - удалённое управление — `administration/server-manager/configure-remote-management-in-server-manager.md`;
  - Windows Admin Center — `manage/windows-admin-center/overview.md`;
  - `slmgr` — `get-started/activation-slmgr-vbs-options.md`;
  - Linux на Hyper-V — `virtualization/hyper-v/Best-Practices-for-running-Linux-on-Hyper-V.md`, `Supported-Ubuntu-virtual-machines-on-Hyper-V.md` (все — репозиторий github.com/MicrosoftDocs/windowsserverdocs, ветка `main`);
  - диапазон динамических портов (KB929851) — https://learn.microsoft.com/troubleshoot/windows-server/networking/default-dynamic-port-range-tcpip-chang;
  - исчерпание портов — https://learn.microsoft.com/troubleshoot/windows-client/networking/tcp-ip-port-exhaustion-troubleshooting;
  - IPv6 — https://learn.microsoft.com/troubleshoot/windows-server/networking/configure-ipv6-in-windows;
  - Defender на Windows Server — https://learn.microsoft.com/defender-endpoint/microsoft-defender-antivirus-on-windows-server;
  - командлеты `Add-MpPreference`, `Install-WindowsFeature`, `New-NetFirewallRule`, `Get-NetFirewallRule` — https://learn.microsoft.com/powershell/module/…; `Enable-PSRemoting` — MicrosoftDocs/PowerShell-Docs.

## Что не удалось подтвердить

- Поддержку **Windows Server 2025** платформой 8.5.x: в документации 8.3.27 её нет, страница системных требований на v8.1c.ru отдаётся без содержимого (формируется скриптом).
- Номера пунктов SConfig, кроме 4, 5 и 15 (подтверждены документацией).
- Действует ли `MaxUserPort` в современных Windows. Документация Microsoft описывает управление диапазоном только через `netsh`; параметры AFD `*DynamicBacklog*` в документации Microsoft не найдены.
- Имена компонентов `Windows-Server-Backup` и `OpenSSH.Server~~~~0.0.1.0`, синтаксис `sc failure` — проверять на сервере (`Get-WindowsFeature`, `Get-WindowsCapability`, `sc failure /?`).
- GUID плана «Высокая производительность» и SID группы «Пользователи системного монитора» (`S-1-5-32-558`) — по практике; сверить с выводом `powercfg /list` и `Get-LocalGroup`.
- Где сейчас распространяется Windows Performance Toolkit (методичка 2016 года ссылается на Windows 8.1 SDK).
- Условия лицензирования гостевых ОС для Standard и Datacenter — смотреть в актуальных условиях Microsoft.
