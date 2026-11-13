# Установка Ubuntu Server и работа в виртуальной машине на Windows-хосте (Hyper-V, VMware, VirtualBox)

> Область: выбор релиза Ubuntu под «1С:Предприятие 8» + PostgreSQL, установка Ubuntu Server (subiquity), чек-лист после установки, настройка гостя и ВМ на Hyper-V / VMware Workstation / VirtualBox / Proxmox-KVM, WSL2, сеть и имена для клиентов 1С, ресурсы ВМ, снапшоты/бэкапы/клонирование, привязка программной лицензии 1С к ВМ, время, USB-ключи HASP.
> Версии: Ubuntu Server 20.04 / 22.04 / 24.04 / 26.04 LTS (x86-64); хост Windows 11 Pro (Hyper-V), VMware Workstation Pro 25H2/26H1 (последняя — 26H1u1 от 03.09.2026), VirtualBox 7.x, Proxmox VE 8+; платформа 1С 8.3.x / 8.5.x; PostgreSQL 14–18 (сборки 1С и Postgres Pro).
> Актуальность: 2026-10-10 (файл прошёл независимую вычитку по первоисточникам 10.10.2026; что именно проверено и что осталось под вопросом — см. конец раздела «Источники»)

Обозначения: **[офиц.]** — утверждение из официальной документации (Canonical, Microsoft, 1С, Postgres Professional, PGDG, Oracle, Proxmox); **[практика]** — опыт сообщества; **⚠ не подтверждено** — первоисточник в этой сессии прочитать не удалось, перед применением проверить.

---

## Кратко — главные факты и команды

1. **Релизы на 10.10.2026** [офиц.]: стандартная поддержка есть у Ubuntu 22.04 LTS (до мая 2027), 24.04 LTS (до мая 2029; текущий point-релиз 24.04.5 от 10.09.2026) и 26.04 LTS «Resolute Raccoon» (вышел 23.04.2026, до мая 2031; текущий 26.04.1 от 27.08.2026). Ubuntu 20.04 с мая 2025 получает обновления только по подписке Ubuntu Pro (ESM). Промежуточные 25.04 и 25.10 сняты с поддержки; 26.10 «Stonking Stingray» запланирован на 15.10.2026.
2. **Что поддерживает 1С** [офиц., v8.1c.ru]: сервер и клиент «1С:Предприятия 8» — Ubuntu **20.04, 22.04, 24.04 LTS** (x86-64 и ARM). Ubuntu 26.04 в списке ОС платформы на 10.10.2026 **отсутствует**.
3. **Что поддерживают сборки PostgreSQL для 1С** [офиц.]: «PostgreSQL с патчем от 1С» (18.4-1.1C, 17.10-2.1C, 16.14-1.1C, 15.18-1.1C, 14.23-1.1C) — Ubuntu 20.04, 22.04, 24.04, **26.04**; Postgres Pro Standard 17/18 — Ubuntu 22.04, 24.04, 25.10, 26.04.
4. **Выбор сейчас:** для продуктивного сервера 1С + PostgreSQL — **Ubuntu Server 24.04 LTS** (есть и в списке 1С, и у всех сборок PostgreSQL, поддержка до 2029). 22.04 — допустима, но до конца стандартной поддержки меньше года. 26.04 — только стенды, пока 1С не добавит её в системные требования.
5. **Установщик subiquity по умолчанию размечает диск LVM и отдаёт корню не весь том** [офиц.]: при VG 20–200 ГиБ корневой LV = половина, при VG > 200 ГиБ — 100 ГиБ. Забрать остаток: `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv`.
6. **Hyper-V:** ВМ 2-го поколения, Secure Boot с шаблоном **«Microsoft UEFI Certificate Authority»** (`Set-VMFirmware -VMName srv1c -SecureBootTemplate MicrosoftUEFICertificateAuthority`), иначе Linux не загрузится.
7. **Память ВМ с СУБД — фиксированная**: в Hyper-V `Set-VM -Name srv1c -StaticMemory`, в Proxmox `--balloon 0`. Динамическая память/ballooning отбирает у гостя страницы, ломает расчёты `shared_buffers`/huge pages и меняет «объём ОЗУ» — ключевой параметр программной лицензии 1С.
8. **Сеть сервера 1С — мост (External/Bridged) и статический IP.** Клиент 1С получает от кластера *имя* рабочего сервера, поэтому имя сервера должно разрешаться на каждом клиенте (DNS или `C:\Windows\System32\drivers\etc\hosts`). «Default Switch» Hyper-V не годится: подсеть меняется после перезагрузки хоста.
9. **Имя хоста задать до установки 1С и до активации лицензии**: `sudo hostnamectl set-hostname srv1c`; в `/etc/hosts` имя должно указывать на реальный IP, а не на `127.0.1.1`.
10. **Пакеты гостя:** Hyper-V — `sudo apt install linux-tools-virtual linux-cloud-tools-virtual` (демоны KVP/VSS/fcopy и `lsvmbus` — из `linux-cloud-tools-common`; юниты `hv-kvp-daemon`, `hv-vss-daemon`, `hv-fcopy-daemon`); VMware — `open-vm-tools`; Proxmox/KVM — `qemu-guest-agent`; VirtualBox — Guest Additions (`VBoxLinuxAdditions.run`) либо пакет `virtualbox-guest-utils`.
11. **Контрольная точка/снапшот — не резервная копия.** PostgreSQL переживает «замороженный» снимок как аварийное отключение (восстановление по WAL) только если снимок атомарен по *всем* томам с данными и WAL [офиц., PostgreSQL docs]. Основной бэкап — средствами СУБД (`pg_dump`, `pg_basebackup` + архив WAL, pg_probackup).
12. **Автоматические контрольные точки Hyper-V** на клиентской Windows включены по умолчанию — отключить: `Set-VM -Name srv1c -AutomaticCheckpointsEnabled $false`.
13. **Клон ВМ дублирует** `/etc/machine-id` (а с ним DHCP-идентификатор), SSH host keys, имя хоста, IP и реестр кластера 1С; программная лицензия 1С в клоне недействительна.
14. **Программная лицензия 1С привязана к параметрам ВМ**: имя компьютера, материнская плата, BIOS, процессоры, объём ОЗУ, сетевые адаптеры и MAC, жёсткие диски. Удаление/замена устройства, уменьшение ОЗУ, смена MAC или имени — повторная активация по резервному пин-коду. Сначала окончательно настроить ВМ, потом активировать. (Перечень и правила сверены 10.10.2026 с полным текстом документации 8.3.27 (разд. 10.3.1.4) — см. раздел 8; ранее: Перечень и правила — по пересказам документации: официальный текст главы на ИТС прочитать не удалось, см. статус в разделе 8.)
15. **Время:** в госте обязателен NTP-клиент (`systemd-timesyncd` до 24.04, `chrony` по умолчанию с 25.10/26.04); интеграция гипервизора лишь подправляет часы после паузы/восстановления.
16. **HASP:** Hyper-V не умеет пробрасывать произвольные USB-устройства — нужен USB-over-IP (например, usbipd-win → `usbip attach`) или переход на программную лицензию; VMware Workstation, VirtualBox и Proxmox пробрасывают USB-ключ штатно.
17. **WSL2 — не серверная платформа**: экземпляр выключается при простое, IP меняется, ядро Microsoft, в системных требованиях 1С не значится. Только для экспериментов.
18. **Отключить cloud-init после установки с ISO:** `sudo touch /etc/cloud/cloud-init.disabled` (предварительно убедившись, что сеть описана в собственном файле netplan). Свежие версии установщика (2025–2026) создают этот файл сами при первой загрузке — сначала проверить `cloud-init status`.
19. **С Ubuntu 24.04 `needrestart` после обновления библиотек сам перезапускает затронутые службы, в том числе при unattended-upgrades** [офиц.] — PostgreSQL и сервер 1С нужно исключить (`/etc/needrestart/conf.d/`, `$nrconf{override_rc}`), иначе ночное обновление `libssl`/`libc` оборвёт сеансы пользователей (п. 3.10).
20. **Файл сети от установщика зависит от версии установщика**: `/etc/netplan/50-cloud-init.yaml` (24.04, генерирует cloud-init из `/etc/cloud/cloud.cfg.d/90-installer-network.cfg`) либо `/etc/netplan/00-installer-config.yaml` (22.04 и установщики с весны 2025 г.). Перед правкой — `ls -l /etc/netplan/ /etc/cloud/cloud.cfg.d/` (п. 3.3).

---

## 1. Релизы Ubuntu, сроки поддержки и выбор версии под 1С + PostgreSQL

### 1.1. Как устроен цикл релизов

- **LTS** выходит раз в два года в апреле (20.04, 22.04, 24.04, 26.04): 5 лет стандартной поддержки (обновления безопасности и исправления для `main`), затем ещё 5 лет ESM по подписке **Ubuntu Pro** (бесплатно до 5 машин для личного использования), затем платный Legacy add-on.
- **Промежуточные релизы** (xx.10 и нечётные xx.04) живут 9 месяцев. На серверы 1С их не ставят: за 9 месяцев придётся обновлять ОС, а сборки 1С и PostgreSQL под них либо не выходят, либо быстро снимаются.
- **Point-релизы** LTS (24.04.1 … 24.04.5) — обновлённые установочные образы; уже установленная система получает то же самое через `apt`. Серверные установки по умолчанию получают **GA-ядро** релиза (6.8 для 24.04), а HWE-ядро предлагается как необязательное [офиц., ubuntu.com/kernel/lifecycle: «Server installations will default to the GA kernel and provide the enablement kernel as optional»]. HWE-ядро 24.04: в 24.04.4 — **6.17**, в 24.04.5 — **7.0** (то же, что GA-ядро 26.04) [офиц., там же]. Получить HWE: пункт загрузочного меню ISO «Ubuntu Server with the HWE kernel» либо пакет `linux-generic-hwe-24.04` [практика]. Для сервера 1С + PostgreSQL в ВМ достаточно GA-ядра: HWE каждые полгода меняет мажорную версию ядра.
- Обновление LTS → LTS (`do-release-upgrade`) открывается после выхода первого point-релиза нового LTS (26.04.1 вышел 27.08.2026).

### 1.2. Состояние на 10 октября 2026 года

| Релиз | Кодовое имя | Выпуск | Конец стандартной поддержки | Конец ESM (Ubuntu Pro) | Ядро GA | Статус на 10.10.2026 |
|---|---|---|---|---|---|---|
| 20.04 LTS | Focal Fossa | 23.04.2020 | май 2025 | май 2030 (Legacy — до 2035) | 5.4 | только ESM по подписке Pro |
| 22.04 LTS | Jammy Jellyfish | 21.04.2022 | май 2027 | май 2032 | 5.15 | поддерживается, осталось < 8 мес. |
| 24.04 LTS | Noble Numbat | 25.04.2024 | май 2029 | май 2034 | 6.8 (HWE: 6.17 в 24.04.4, 7.0 в 24.04.5) | поддерживается; point-релиз 24.04.5 (10.09.2026) |
| 25.04 | Plucky Puffin | 17.04.2025 | январь 2026 | — | 6.14 | снят с поддержки |
| 25.10 | Questing Quokka | 09.10.2025 | июль 2026 | — | 6.17 | снят с поддержки |
| 26.04 LTS | Resolute Raccoon | 23.04.2026 | май 2031 | май 2036 | 7.0 | поддерживается; point-релиз 26.04.1 (27.08.2026) |
| 26.10 | Stonking Stingray | план 15.10.2026 | ~июль 2027 | — | ⚠ не подтверждено: в release notes 26.10 версия ядра ещё не указана (заглушка) | ещё не вышел (бета 24.09.2026, Kernel Freeze 01.10.2026) |

Источники дат: ubuntu.com/about/release-cycle, endoflife.date/ubuntu, releases.ubuntu.com, documentation.ubuntu.com/release-notes/26.10/schedule/. Ядра GA 20.04 (5.4), 22.04 (5.15), 24.04 (6.8), 25.10 (6.17), 26.04 (7.0) подтверждены по ubuntu.com/kernel/lifecycle [офиц.]. Ядро 25.04 (6.14) — ⚠ не подтверждено в этой вычитке: на странице kernel/lifecycle снятый с поддержки 25.04 уже не показан (значение по памяти, на выбор версии не влияет). Точные даты по endoflife.date: 22.04 — стандартная поддержка до 01.06.2027; 24.04 — до 31.05.2029; 26.04 — до 29.05.2031; 25.10 снят 01.07.2026; 25.04 — 17.01.2026. Legacy add-on по ubuntu.com/about/release-cycle: 20.04 — до мая 2035, 22.04 — до мая 2037, 24.04 — до мая 2039, 26.04 — до мая 2041.

Узнать версию установленной системы:

```bash
lsb_release -a            # Description: Ubuntu 24.04.5 LTS, Codename: noble
cat /etc/os-release       # VERSION_ID, VERSION_CODENAME
uname -r                  # версия ядра
pro status                # статус Ubuntu Pro / ESM (пакет ubuntu-pro-client)
ubuntu-distro-info --supported   # какие релизы сейчас поддерживаются (пакет distro-info)
```

### 1.3. Что официально поддерживает 1С и сборки PostgreSQL

**Платформа «1С:Предприятие 8»** [офиц., v8.1c.ru → «Системные требования» → «Операционные системы», страница без привязки к номеру версии платформы, прочитана 10.10.2026]:

| Компонент | Архитектура | Версии Ubuntu |
|---|---|---|
| Сервер 1С:Предприятия | x86-64 | 20.04 LTS, 22.04 LTS, 24.04 LTS |
| Сервер 1С:Предприятия | x86 (32-бит) | 20.04 LTS, 22.04 LTS, 24.04 LTS (как указано на странице; на практике 32-битных сборок современных Ubuntu нет) |
| Сервер 1С:Предприятия | ARM | 20.04 LTS, 22.04 LTS, 24.04 LTS |
| Тонкий и толстый клиент | x86 / x86-64, ARM | 20.04 LTS, 22.04 LTS, 24.04 LTS |

Там же перечислены Debian 10/11/12, Astra Linux SE 1.6/1.7/1.8 (только ядро generic), Альт 10, РЕД ОС 7.3/8, RHEL и Oracle Linux 8/9, Mint 20/21/22 и др. **Ubuntu 26.04, 25.x и Debian 13 в списке ОС платформы нет.**

Аппаратный минимум сервера 1С (64-бит) [офиц.]: процессор x86-64, ОЗУ **не менее 2 ГБ (рекомендуется 4 ГБ и выше)**, диск **40 ГБ и выше**. Это нижняя граница запуска, а не ориентир для расчёта (см. раздел 6).

**СУБД** [офиц., v8.1c.ru → «Список ОС для поддерживаемых СУБД»]:

| СУБД | Версии | Ubuntu |
|---|---|---|
| PostgreSQL с патчем от 1С | 18.4-1.1C, 17.10-2.1C, 16.14-1.1C, 15.18-1.1C, 14.23-1.1C | 20.04, 22.04, 24.04, 26.04 |
| Postgres Pro 1C | 18.4, 17.10, 16.14, 15.18, 14.23 | на v8.1c.ru списка ОС нет — ссылка на таблицу платформ postgrespro.ru |
| Postgres Pro Standard / Enterprise (в т. ч. Certified) | 18.4.1, 17.10.1, 16.14.1, 15.18.1, 14.23.1 | то же: ссылка на postgrespro.ru |
| Postgres Pro Standard 17 и 18 [офиц., postgrespro.ru/docs] | — | x86-64: 22.04, 24.04, 25.10, 26.04; ARM: 22.04, 24.04, 26.04 (следующий выпуск — последний с 25.10) |
| Tantor SE 1C | 18.3.1, 17.10.0, 16.14.0, 15.18.0, 14.23.0 | 22.04 |
| Jatoba | 4.8.2-1117 | 18.04, 20.04, 22.04 |

Проверено по v8.1c.ru 10.10.2026: в строке «PostgreSQL с патчем от 1С» кроме Ubuntu перечислены также Debian 9–13, Astra Linux SE 1.7/1.8, Альт 9/10, РЕД ОС 7.3/8.0, CentOS 7/9, Oracle Linux 9, Windows. То есть **СУБД для 26.04 и Debian 13 уже есть, а платформа 1С для них официально не заявлена** — ограничивающим фактором при выборе ОС является именно список ОС платформы.

Бесплатные сборки «PostgreSQL для 1С» от Postgres Professional раздаются через форму на 1c.postgres.ru (только 64-разрядные Windows и Linux; если нужной ОС в форме нет — сборка под неё не выпускается). Точный список Ubuntu для них на самой странице не опубликован — Уточнено 11.10.2026 по файлам `meta.json` репозитория (`https://repo.postgrespro.ru/1c/1c-<ветка>/meta.json`): ветки 14, 15 и 16 выпускаются для Ubuntu 22.04 и 24.04; ветки 17 и 18 — для 22.04, 24.04, 25.10 и 26.04 (то есть на 26.04 доступны только 17 и 18). Подробнее — `kb/guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`.

### 1.4. Какую версию ставить сейчас

| Вариант | Вердикт на октябрь 2026 |
|---|---|
| **Ubuntu Server 24.04 LTS** | **Рекомендуется.** Есть в требованиях 1С и у всех сборок PostgreSQL для 1С; стандартная поддержка до мая 2029; привычный стек (GNU coreutils, классический sudo, systemd-timesyncd, initramfs-tools). |
| Ubuntu Server 22.04 LTS | Допустимо для уже работающих систем. Новую установку не начинать: стандартная поддержка кончается в мае 2027. |
| Ubuntu Server 26.04 LTS | Только тестовые стенды. PostgreSQL для неё уже есть, но платформа 1С официально не заявлена → техподдержка 1С вправе отказать. Вернуться к вопросу, когда 26.04 появится на v8.1c.ru. |
| Ubuntu 20.04 LTS | Не ставить. Обновления только через Ubuntu Pro; имеет смысл лишь дожить до миграции. |
| 25.10 / 26.10 и другие промежуточные | Не ставить на серверы. |

Что изменилось в 26.04 по сравнению с 24.04 и влияет на администрирование [офиц., «Summary for LTS users»]:

- ядро **7.0** (в 24.04 — 6.8), systemd 259 вместо 255; **cgroup v1 удалён**; 26.04 — последний релиз с совместимостью со скриптами System V init (старые init.d-скрипты надо переводить в unit-файлы);
- **sudo-rs** — sudo по умолчанию (классический переименован в `sudo.ws`), `sudo-ldap` удалён;
- **rust-coreutils** по умолчанию (GNU-версии доступны с префиксом `gnu`, например `gnuls`; `cp`, `mv`, `rm` остаются GNU);
- **chrony** вместо systemd-timesyncd на новых установках, с NTS; источники — `/etc/chrony/sources.d/ubuntu-ntp-pools.sources`;
- **dracut** вместо initramfs-tools по умолчанию;
- **APT 3.1**: `apt-key` удалён (старые инструкции с `apt-key add` не работают — ключи кладут в `/etc/apt/keyrings/` и указывают через `signed-by`), появились `apt history-list` / `history-undo` / `history-rollback`;
- **OpenSSH 10.2p1** (в 24.04 — 9.6p1): DSA удалён, сервер больше не читает `~/.pam_environment`, гибридный постквантовый обмен ключами по умолчанию;
- Netplan 1.2 (в 24.04 — 1.0); в архиве PostgreSQL 18; kdump при установке включается по умолчанию (начиная с 24.10), но **только если система подходит**: не меньше 4 потоков процессора, от 6 ГБ до 2 ТБ ОЗУ, свободное место в `/var` больше пятикратного объёма ОЗУ + подкачки, архитектура amd64 (s390x, arm64 с UEFI); условия проверяет `/usr/share/kdump-tools/kdump_set_default` в момент установки (уточнено 19.10.2026 по документации Ubuntu Server «Kernel crash dump»). Сервер 1С с большим ОЗУ и обычным `/var` под условие часто не попадает — kdump тогда выключен. Проверка: `kdump-config show` (`USE_KDUMP: 1`, `current state: ready to kdump`, каталог дампов `KDUMP_COREDIR: /var/crash`).

---

## 2. Установка Ubuntu Server (установщик subiquity)

### 2.1. Образ и требования

- Образ: `ubuntu-24.04.5-live-server-amd64.iso` (~3,8 ГБ, собран 09.09.2026) с https://releases.ubuntu.com/24.04/ (для 26.04 — `ubuntu-26.04.1-live-server-amd64.iso`, ~2,7 ГБ, собран 26.08.2026) [офиц., листинг releases.ubuntu.com на 10.10.2026]. Проверка: `SHA256SUMS` из того же каталога (`Get-FileHash .\ubuntu-24.04.5-live-server-amd64.iso -Algorithm SHA256` в PowerShell).
- Минимум для установки с ISO (24.04, amd64) [офиц.]: **1,5 ГБ ОЗУ и 5 ГБ диска**; рекомендуется от 3 ГБ ОЗУ и 25 ГБ диска. Для 26.04 release notes называют от 1,5 ГБ ОЗУ и 4 ГБ диска.
- На время установки ВМ лучше дать 2–4 ГБ ОЗУ: live-система работает из памяти.

### 2.2. Экраны установщика по порядку

| № | Экран | Что выбрать для сервера 1С |
|---|---|---|
| 1 | Язык (Language) | **English** — язык системы и сообщений; русскую локаль добавим отдельно (п. 3.5). Сообщения об ошибках на английском проще искать. |
| 2 | Обновление установщика (Installer update) | «Update to the new installer», если есть сеть; после обновления установщик перезапустится на том же шаге. |
| 3 | Клавиатура (Keyboard) | English (US). Русская раскладка в консоли сервера не нужна. |
| 4 | Тип установки (Choose type of install) | **Ubuntu Server** (по умолчанию) или **Ubuntu Server (minimized)**; галочка «Search for third-party drivers» в ВМ не нужна. |
| 5 | Сеть (Network connections) | На время установки можно оставить DHCP; статический адрес удобнее задать сразу: интерфейс → Edit IPv4 → Manual (Subnet `192.168.1.0/24`, Address, Gateway, Name servers, Search domains). |
| 6 | Прокси (Proxy) | Пусто, если прокси нет. |
| 7 | Зеркало (Archive mirror) | По умолчанию (определяется геолокацией). |
| 8 | Разметка (Guided storage configuration) | «Use an entire disk» + «Set up this disk as an LVM group» (по умолчанию). Шифрование LUKS для ВМ с БД обычно не включают: пароль придётся вводить в консоли при каждой загрузке. См. п. 2.4. |
| 9 | Сводка разметки (Storage configuration) | Проверить размер `ubuntu-lv`; его можно увеличить прямо здесь (ubuntu-lv → Edit → Size). После подтверждения «Continue» диск будет перезаписан. |
| 10 | Профиль (Profile setup) | Your name, **Your server's name** (имя хоста, см. п. 3.2), Username, Password. Этот пользователь получает sudo. Пользователя `usr1cv8` и `postgres` здесь НЕ создавать — их создают пакеты 1С и PostgreSQL. |
| 11 | Ubuntu Pro | «Skip for now». |
| 12 | SSH (SSH Setup) | Отметить **Install OpenSSH server**. Импорт ключа из GitHub/Launchpad — по желанию; после импорта становится доступен флажок «Allow password authentication over SSH» — проверить его состояние. В autoinstall параметр `ssh.allow-pw` по умолчанию `true`, если `authorized-keys` пуст, и `false` в противном случае [офиц., справочник autoinstall]; итог после установки проверить командой `sudo sshd -T \| grep -i passwordauth`. |
| 13 | Featured server snaps | Ничего не выбирать (docker, microk8s и пр. серверу 1С не нужны). |
| 14 | Установка и перезагрузка | Дождаться «Install complete!» (при наличии сети ставятся обновления безопасности) → «Reboot Now» → на просьбу извлечь носитель нажать Enter; если ВМ снова грузится с ISO — отключить образ в настройках ВМ. |

Экраны 4, 9, 11 в официальном «screen-by-screen» описаны не полностью — их формулировки приведены по фактическому установщику 22.04–24.04 [практика].

### 2.3. «Ubuntu Server» или «Ubuntu Server (minimized)»

- **Ubuntu Server** — обычный набор: man-страницы, редакторы, `ubuntu-server`-метапакет, утилиты диагностики.
- **Minimized** — урезанный набор для автоматизированных развёртываний: нет man-страниц, части утилит и локализаций; при входе система предлагает команду `unminimize`, возвращающую полный набор.
- Для сервера 1С, который сопровождает человек, практичнее обычный вариант: разница в десятки–сотни мегабайт, а недостающие утилиты всё равно придётся доустанавливать.

### 2.4. Разметка: LVM и почему корневой том меньше диска

Что создаёт «Use an entire disk» + LVM на UEFI-машине (ВМ Hyper-V 2-го поколения) [практика, типичная картина 22.04–24.04]:

```text
sda
├─sda1   ~1 ГБ    vfat   /boot/efi      (ESP)
├─sda2   ~2 ГБ    ext4   /boot
└─sda3   остаток  LVM PV → VG ubuntu-vg
   └─ubuntu--vg-ubuntu--lv   ext4   /
```

На BIOS-машине (ВМ 1-го поколения, VirtualBox без EFI) вместо ESP создаётся раздел `bios_grub` 1 МБ. Подкачка — файл `/swap.img`, размер выбирается автоматически (`swapon --show`).

**Почему `ubuntu-lv` занимает не весь VG.** Это намеренная политика установщика `sizing-policy: scaled` [офиц., справочник autoinstall]:

| Размер VG (свободного места) | Размер корневого LV |
|---|---|
| меньше 10 ГиБ | всё место |
| 10–20 ГиБ | 10 ГиБ |
| 20–200 ГиБ | половина |
| больше 200 ГиБ | 100 ГиБ |

Смысл: оставить место для снапшотов LVM и для отдельных томов (`/var/lib/...`, `/home`), которые администратор создаст сам. В интерактивной установке это можно поправить на экране сводки разметки, в autoinstall — `sizing-policy: all`.

Проверить и расширить после установки:

```bash
lsblk                                   # дерево дисков и разделов
sudo vgs                                # VFree — свободное место в группе томов
sudo lvs                                # размеры логических томов
df -hT /                                # сколько реально в корне

# вариант 1: отдать корню всё свободное место (-r сразу расширяет файловую систему)
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv

# вариант 2: добавить корню 20 ГиБ, а остаток оставить под отдельные тома
sudo lvextend -r -L +20G /dev/ubuntu-vg/ubuntu-lv
```

Ключи `lvextend`: `-l +100%FREE` — в экстентах/процентах, `-L +20G` — в единицах размера, `-r` (`--resizefs`) — вызвать `resize2fs`/`xfs_growfs` автоматически. Расширение ext4 и XFS выполняется на смонтированной ФС, перезагрузка не нужна.

**Рекомендуемая раскладка для сервера 1С + PostgreSQL в ВМ** [практика]: системный диск 40–80 ГБ целиком под `/` (или LVM с запасом), а данные — на **отдельных виртуальных дисках** (их проще расширять, переносить и исключать из снапшотов):

| Виртуальный диск | Точка монтирования (пример) | Назначение |
|---|---|---|
| sda, 40–80 ГБ | `/` , `/boot`, `/boot/efi` | ОС, платформа 1С (`/opt/1cv8`), журналы |
| sdb | каталог данных СУБД (`/var/lib/postgresql` для сборки 1С/PGDG, `/var/lib/pgpro` для Postgres Pro) | PGDATA |
| sdc (по желанию) | каталог для `pg_wal` | WAL — имеет смысл, если это другой физический носитель |
| sdd | `/backup` | дампы и архив WAL; физически — на другом носителе, чем данные |
| (по желанию) | `/home/usr1cv8` | каталог кластера 1С: журналы регистрации, индекс полнотекстового поиска, сеансовые данные |

Подготовка отдельного диска под данные (пример для `/dev/sdb`, ext4, без LVM):

```bash
lsblk -f                                         # убедиться, что sdb пуст
sudo parted -s /dev/sdb mklabel gpt mkpart primary ext4 1MiB 100%
sudo mkfs.ext4 -L pgdata /dev/sdb1               # на динамическом VHDX Microsoft советует добавить -G 4096
sudo mkdir -p /var/lib/postgresql
sudo blkid /dev/sdb1                             # взять UUID
echo 'UUID=<uuid-из-blkid>  /var/lib/postgresql  ext4  defaults,noatime  0  2' | sudo tee -a /etc/fstab
sudo systemctl daemon-reload && sudo mount -a && df -hT /var/lib/postgresql
```

Монтировать по `UUID=` или `LABEL=`, а не по `/dev/sdb1`: порядок дисков в ВМ может поменяться после добавления контроллера или диска. Диск монтируют **до** установки PostgreSQL, чтобы каталог данных сразу создался на нём.

### 2.5. Автоматическая установка (autoinstall) — кратко

Autoinstall — YAML-ответы на вопросы установщика (Ubuntu Server 20.04+) [офиц.]. В отличие от debian-installer preseed: если конфигурация задана, неотвеченные вопросы получают значения по умолчанию, а не останавливают установку; отдельные экраны можно оставить интерактивными (`interactive-sections`).

Способы передать конфигурацию и порядок поиска (используется первый найденный):

1. параметр ядра `subiquity.autoinstallpath=путь/autoinstall.yaml` (путь внутри корня установщика);
2. `/autoinstall.yaml` в корне файловой системы установщика (требует пересборки ISO, не рекомендуется);
3. cloud-init user-data (источник NoCloud): файл начинается с `#cloud-config`, директивы — под ключом `autoinstall:`;
4. `autoinstall.yaml` в корне установочного носителя (раздел с каталогом `casper`); верхний ключ `autoinstall:` необязателен (с 24.04 допускается).

Минимальный пример `autoinstall.yaml` для сервера в ВМ:

```yaml
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  timezone: Europe/Moscow
  source:
    id: ubuntu-server            # или ubuntu-server-minimal
  identity:
    hostname: srv1c
    username: admin
    password: "$6$...хэш..."     # получить: mkpasswd -m sha-512  (пакет whois) или openssl passwd -6
  ssh:
    install-server: true
    allow-pw: true               # по умолчанию true, если authorized-keys пуст
    authorized-keys: []
  storage:
    layout:
      name: lvm                  # lvm | direct | zfs | hybrid
      sizing-policy: all         # отдать корню весь VG (по умолчанию scaled)
  packages:
    - mc
    - htop
    - sysstat
  updates: security              # или all
  shutdown: reboot               # или poweroff
```

Пояснения [офиц.]: `version` обязан быть `1`; `identity` обязателен, если нет `user-data`; `storage.layout.match` выбирает диск (без него берётся самый большой); пароль в `storage.layout.password` включает LUKS; `late-commands` выполняются перед перезагрузкой, целевая система смонтирована в `/target` (`curtin in-target -- <команда>`). Фактически использованная конфигурация сохраняется в установленной системе в `/var/log/installer/autoinstall-user-data` — удобная заготовка для повторных установок (⚠ не подтверждено в этой вычитке: путь общеизвестен, но на прочитанных страницах документации subiquity не упомянут). Полностью автоматический запуск без вопроса «Continue with autoinstall?» требует параметра ядра `autoinstall` (⚠ не подтверждено в этой вычитке: описано в разделах документации «Autoinstall quick start» / «Zero-touch deployment with autoinstall», которые прочитать не удалось; на страницах intro и «Providing autoinstall» параметр не упомянут).

Дополнительные ключи autoinstall, проверенные по справочнику [офиц.]: `storage.layout.name` — `lvm` (по умолчанию на системах с одним диском; для нескольких дисков значения по умолчанию нет), `direct`, `zfs`; `hybrid` применяется для шифрования с TPM; `kernel.package` / `kernel.flavor` взаимоисключающие (на серверном ISO по умолчанию `generic`, вариант `hwe` ставит HWE-ядро); `source.search_drivers` по умолчанию `true`; `updates` — `security` (по умолчанию) или `all`; `shutdown` — `reboot` (по умолчанию) или `poweroff`; `interactive-sections: ["*"]` — задать все обычные вопросы, используя файл лишь как набор значений по умолчанию.

---

## 3. Чек-лист после установки

Порядок важен: имя хоста, сеть, время и локаль настраивают **до** установки PostgreSQL и сервера 1С (кластер PostgreSQL создаётся с текущей локалью, кластер 1С запоминает имя хоста, лицензия привязывается к имени и MAC).

### 3.1. Обновление системы

```bash
sudo apt update                      # обновить индексы пакетов
apt list --upgradable                # что будет обновлено
sudo apt full-upgrade -y             # обновить всё, включая смену зависимостей (ядро)
sudo apt autoremove --purge -y       # убрать старые ядра и осиротевшие пакеты
cat /var/run/reboot-required 2>/dev/null && cat /var/run/reboot-required.pkgs   # нужна ли перезагрузка и из-за чего
sudo reboot
```

### 3.2. Имя хоста и /etc/hosts

Требования к имени сервера 1С [практика]: строчные латинские буквы, цифры, дефис; без подчёркиваний и кириллицы; до 15 символов (чтобы имя одинаково работало и как DNS-, и как NetBIOS-имя на клиентах Windows).

```bash
hostnamectl                               # текущее имя (Static hostname)
sudo hostnamectl set-hostname srv1c       # задать имя (пишет /etc/hostname)
hostname; hostname -f; hostname -I        # короткое имя, FQDN, все IP
getent hosts srv1c                        # во что имя разрешается локально
```

`/etc/hosts` — привести к виду (имя указывает на **реальный** адрес сервера):

```text
127.0.0.1      localhost
192.168.1.50   srv1c.corp.local srv1c

# строку установщика «127.0.1.1 srv1c» удалить или закомментировать
```

Зачем: кластер серверов 1С регистрирует рабочий сервер по имени хоста и выдаёт это имя клиентам; если имя локально разрешается в `127.0.1.1`, процессы кластера и утилиты администрирования могут получать loopback-адрес вместо сетевого. Проверка: `ping -c1 srv1c` должен показать `192.168.1.50`.

Что здесь подтверждено, а что нет:

- строку `127.0.1.1 <имя>` в `/etc/hosts` действительно пишет сам установщик Ubuntu (шаблон `127.0.0.1 localhost` / `127.0.1.1 {hostname}` в исходном коде subiquity; там же выставляется `preserve_hostname: true`, чтобы cloud-init не менял имя) [офиц., исходный код subiquity];
- инструкция 1С по установке платформы в Linux (ИТС, metod8dev, написана для 8.3.13) первым шагом предлагает проверить адрес и имя командами `ifconfig` и `hostname -f` и привести запись в `/etc/hosts` к виду `IP-адрес имя.домен имя` [офиц.; на странице читаются только команды и латиница — русский текст отдаётся в битой кодировке];
- утверждение, что именно привязка к `127.0.1.1` ломает работу кластера, — **[практика сообщества]**; в читаемой части страницы ИТС адрес `127.0.1.1` не упоминается (⚠ не подтверждено официальным текстом). Рекомендация при этом безвредна и согласуется с требованием 1С, чтобы `hostname -f` и запись hosts давали реальный адрес.

Если наверху `/etc/hosts` стоит комментарий о `manage_etc_hosts` — файл перегенерирует cloud-init; отключить cloud-init (п. 3.11) или выставить `manage_etc_hosts: false` в `/etc/cloud/cloud.cfg.d/`.

**Менять имя хоста после установки сервера 1С и активации программной лицензии нельзя без последствий**: имя прописано в реестре кластера (`1cv8wsrv.lst`) и входит в ключевые параметры лицензии (раздел 8).

### 3.3. Статический IP-адрес (netplan)

Конфигурация сети в Ubuntu Server — YAML-файлы `/etc/netplan/*.yaml`, которые netplan транслирует в настройки `systemd-networkd` (рендерер по умолчанию на сервере). Файлы читаются в лексикографическом порядке, более поздние дополняют/переопределяют ранние.

Какой файл оставил установщик — **зависит от версии установщика subiquity, а не только от релиза** [офиц., исходный код subiquity `subiquity/models/network.py`, проверено 10.10.2026]:

| Установщик | Что пишется в установленную систему |
|---|---|
| 20.04, 22.04 | `/etc/netplan/00-installer-config.yaml` + `/etc/cloud/cloud.cfg.d/subiquity-disable-cloudinit-networking.cfg` с содержимым `network: {config: disabled}` (cloud-init сеть не трогает) |
| 23.10 – 24.04 (версии установщика с июля 2023 по весну 2025; тег 24.04.1 проверен) | настройки сети кладутся в **`/etc/cloud/cloud.cfg.d/90-installer-network.cfg`**, а cloud-init при первой загрузке генерирует из них **`/etc/netplan/50-cloud-init.yaml`**. Это и есть роль файла `90-installer-network.cfg`: он — первоисточник, из которого cloud-init может заново перегенерировать `50-cloud-init.yaml` (при смене instance-id, после `cloud-init clean`) |
| установщики после коммита «network: write netplan config directly» (24.04.2025) — ветка `main` на октябрь 2026 | снова напрямую `/etc/netplan/00-installer-config.yaml` (права 0600) + `/etc/cloud/cloud.cfg.d/00-subiquity-disable-cloudinit-networking.cfg` (`network: {config: disabled}`) |

⚠ не подтверждено: какая именно версия установщика лежит на конкретном ISO (24.04.5, 26.04.1) и какой из двух вариантов получится — в release notes это не описано; к тому же установщик на шаге «Installer update» может обновить сам себя. Поэтому **не полагаться на имя файла, а смотреть по факту**: `ls -l /etc/netplan/ /etc/cloud/cloud.cfg.d/`. В шапке `50-cloud-init.yaml` написано, как отключить управление сетью через cloud-init (файл `99-disable-network-config.cfg`, см. ниже).

Имена интерфейсов в ВМ [практика]: Hyper-V — `eth0`; VMware — `ens33` (e1000), `ens160`/`ens192` (vmxnet3); VirtualBox — `enp0s3` (адаптер 1), `enp0s8` (адаптер 2); Proxmox/KVM virtio — `ens18` или `enp1s0`. Точное имя: `ip -br link`.

Надёжный порядок действий:

```bash
ip -br addr; ip route                      # текущие адреса, шлюз
ls -l /etc/netplan/ /etc/cloud/cloud.cfg.d/

# 1) запретить cloud-init управлять сетью (иначе он может перегенерировать 50-cloud-init.yaml)
echo 'network: {config: disabled}' | sudo tee /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg

# 2) убрать файл установщика (какой есть — 50-cloud-init.yaml или 00-installer-config.yaml) и написать свой
sudo mkdir -p /root/netplan.bak
sudo mv /etc/netplan/*.yaml /root/netplan.bak/          # в /etc/netplan не должно остаться двух файлов, описывающих один интерфейс
# если есть /etc/cloud/cloud.cfg.d/90-installer-network.cfg — это исходник для 50-cloud-init.yaml; после шага 1 он не применяется,
# но чтобы не путал, его можно убрать туда же:  sudo mv /etc/cloud/cloud.cfg.d/90-installer-network.cfg /root/netplan.bak/
sudo nano /etc/netplan/01-static.yaml
sudo chmod 600 /etc/netplan/01-static.yaml  # иначе netplan предупреждает, что права слишком открыты

# 3) проверить и применить
sudo netplan get                           # разобрать YAML и показать итоговую конфигурацию (ошибка синтаксиса — сообщение с номером строки)
sudo netplan try                           # применить с автооткатом через 120 с, если не подтвердить Enter (--timeout N — другой срок)
sudo netplan apply                         # применить окончательно (после подтверждённого try уже не обязателен)
#   [практика; ⚠ не подтверждено документацией] не запускать `netplan generate` непосредственно перед `netplan try`:
#   откат try восстанавливает сохранённое состояние /run/systemd/network, а generate перезаписывает его новой конфигурацией.
#   После несостоявшегося try (сработал откат) в /etc/netplan остаётся НОВЫЙ, нерабочий файл — исправить его до перезагрузки.
#   При работе по SSH безопаснее выполнять этот шаг из консоли гипервизора (vmconnect и т. п.).
netplan status                             # (24.04+) итоговое состояние интерфейсов
resolvectl status                          # какие DNS-серверы используются
```

`/etc/netplan/01-static.yaml`:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: false
      dhcp6: false
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1, 77.88.8.8]
        search: [corp.local]
```

Справка по ключам [офиц., netplan-yaml]: `addresses` — список в формате CIDR; `routes: - to: default, via: …` — маршрут по умолчанию (`gateway4` **устарел**); `nameservers.addresses` / `nameservers.search`; `dhcp4`/`dhcp6` по умолчанию выключены; `dhcp-identifier: mac` — использовать MAC как идентификатор DHCP-клиента (по умолчанию networkd формирует идентификатор из DUID, производного от `/etc/machine-id`, — важно для клонов, раздел 7.4); `match: {macaddress: …}` + `set-name:` — привязать конфигурацию к MAC и переименовать интерфейс; `optional: true` — не ждать интерфейс при загрузке.

Вариант «DHCP с резервированием на роутере» тоже рабочий: в netplan оставить `dhcp4: true` и добавить `dhcp-identifier: mac`, а на DHCP-сервере закрепить адрес за MAC-адресом ВМ (MAC в настройках ВМ сделать статическим).

### 3.4. Часовой пояс и синхронизация времени

```bash
timedatectl                                   # время, пояс, «System clock synchronized: yes/no», «NTP service: active»
timedatectl list-timezones | grep -i -E 'moscow|tashkent'
sudo timedatectl set-timezone Europe/Moscow   # пример; Asia/Tashkent, Asia/Yekaterinburg и т. п.
sudo timedatectl set-ntp true                 # включить синхронизацию штатной службой
```

Аппаратные часы ВМ держать в UTC (по умолчанию: `RTC in local TZ: no`).

Какая служба синхронизации стоит по умолчанию [офиц.]: до 25.04 включительно (в т. ч. 22.04, 24.04) — **systemd-timesyncd**; с 25.10 и в 26.04 на новых установках — **chrony** (с NTS; порт NTS-KE 4460/tcp в дополнение к 123/udp). Одновременно активна только одна: установка chrony отключает timesyncd.

systemd-timesyncd (22.04/24.04):

```bash
timedatectl timesync-status                   # сервер, смещение, интервал опроса
systemctl status systemd-timesyncd
sudo mkdir -p /etc/systemd/timesyncd.conf.d
printf '[Time]\nNTP=192.168.1.1 ntp.ubuntu.com\nFallbackNTP=pool.ntp.org\n' | sudo tee /etc/systemd/timesyncd.conf.d/local.conf
sudo systemctl restart systemd-timesyncd
```

chrony (26.04 по умолчанию; в 24.04 — `sudo apt install chrony`):

```bash
chronyc tracking                              # текущее смещение, stratum, источник
chronyc sources -v                            # список источников и их состояние
echo 'server 192.168.1.1 iburst prefer' | sudo tee /etc/chrony/sources.d/local.sources
sudo chronyc reload sources                   # перечитать каталог sources.d без перезапуска
sudo chronyc makestep                         # немедленно скачком выставить время (после восстановления из снапшота)
```

Файлы chrony: `/etc/chrony/chrony.conf`, источники по умолчанию — `/etc/chrony/sources.d/ubuntu-ntp-pools.sources`. Особенности времени в ВМ — раздел 9.

### 3.5. Локаль ru_RU.UTF-8

Локаль `ru_RU.UTF-8` должна существовать в системе **до создания кластера PostgreSQL** под базы 1С: пакеты PostgreSQL при установке создают кластер с локалью из окружения, а порядок сортировки (LC_COLLATE) кластера/базы потом не меняется без пересоздания. Язык интерфейса системы при этом может оставаться английским.

```bash
locale -a | grep -i -E 'ru_RU|en_US'          # какие локали уже сгенерированы
sudo locale-gen ru_RU.UTF-8 en_US.UTF-8       # сгенерировать (правит /etc/locale.gen и собирает локали)
sudo update-locale LANG=ru_RU.UTF-8           # системная локаль по умолчанию → /etc/default/locale
localectl status                              # проверить; действует для новых сеансов (перелогиниться)
```

Варианты: `sudo dpkg-reconfigure locales` — то же в диалоге; `sudo apt install language-pack-ru` — добавляет переводы сообщений. Если хочется английские сообщения в консоли, но русскую локаль для СУБД — оставить `LANG=en_US.UTF-8`, а локаль кластеру PostgreSQL указать явно при его создании (`--locale=ru_RU.UTF-8`); подробности — в статье про PostgreSQL для 1С.

### 3.6. Пользователи и sudo

```bash
sudo adduser ivanov                    # создать администратора (интерактивно: пароль, GECOS)
sudo usermod -aG sudo ivanov           # дать sudo (группа sudo)
id ivanov; groups ivanov               # проверить членство
sudo passwd -S root                    # статус пароля root: «L» — заблокирован (так в Ubuntu по умолчанию)
sudo visudo -f /etc/sudoers.d/90-admins   # правки sudoers только через visudo (проверяет синтаксис)
```

- Работать под личной учётной записью с `sudo`, а не под root; у root в Ubuntu нет пароля, а вход root по SSH с паролем запрещён по умолчанию (`PermitRootLogin prohibit-password`).
- Служебные пользователи `usr1cv8` (группа `grp1cv8`) и `postgres` создаются пакетами 1С и PostgreSQL — вручную их не заводят и sudo им не дают.
- 26.04: sudo по умолчанию — `sudo-rs`; базовый синтаксис sudoers совместим, классическая реализация доступна как `sudo.ws` [офиц.].

### 3.7. SSH-ключи

На рабочей станции Windows 11 (клиент OpenSSH встроен):

```powershell
ssh-keygen -t ed25519 -C "admin@workstation"          # ключи в %USERPROFILE%\.ssh\id_ed25519(.pub)
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh admin@192.168.1.50 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
ssh admin@192.168.1.50                                 # вход уже по ключу
```

(`ssh-copy-id` в Windows нет, поэтому публичный ключ дописывают в `~/.ssh/authorized_keys` конвейером.)

На сервере — запретить вход по паролю, когда ключ проверен:

```bash
sudo tee /etc/ssh/sshd_config.d/10-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
sudo sshd -t                           # проверка конфигурации
sudo systemctl restart ssh             # служба в Ubuntu называется ssh.service (не sshd); так же её называет документация Ubuntu Server
sudo sshd -T | grep -i -E 'passwordauth|permitroot'   # действующие значения
```

Тонкость: sshd берёт **первое** встретившееся значение параметра, а файлы `sshd_config.d/*.conf` подключаются в начале `sshd_config` (`Include /etc/ssh/sshd_config.d/*.conf` — первая строка штатного файла [офиц., Ubuntu Server docs]) в алфавитном порядке. Установщик/cloud-init может оставить `50-cloud-init.conf` с `PasswordAuthentication yes` — поэтому свой файл называют с меньшим номером (`10-…`). Не закрывать текущую SSH-сессию, пока вход по ключу не проверен во второй.

Ещё две особенности Ubuntu:

- **Сокет-активация.** «Since Ubuntu 22.10, openssh-server is configured to use systemd socket activation by default» [офиц., release notes 24.04]: порт 22 слушает юнит `ssh.socket`, а `ssh.service` запускается при первом подключении. Следствия [практика]: `systemctl status ssh` до первого входа может показывать «inactive» — это норма; после смены `Port`/`ListenAddress` в `sshd_config` на 24.04 нужно `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket` (параметры в юнит сокета переносит генератор systemd); проверка — `sudo ss -tlnp | grep ':22'`. ⚠ не подтверждено: сохранилась ли сокет-активация по умолчанию в 26.04 — проверить `systemctl is-enabled ssh.socket ssh.service`.
- **Имя `sshd.service`** — лишь псевдоним (`Alias=`), который существует только когда `ssh.service` включён через `systemctl enable`; при сокет-активации его может не быть, и `systemctl restart sshd` завершится ошибкой «Unit sshd.service not found» [практика; ⚠ наличие псевдонима в 26.04 не проверено]. Надёжно во всех версиях — имя `ssh`.

### 3.8. Межсетевой экран ufw

ufw после установки выключен. Сначала разрешить SSH, потом включать:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH                               # профиль приложения = 22/tcp
sudo ufw allow 1540:1541/tcp comment '1C ragent, rmngr'
sudo ufw allow 1560:1591/tcp comment '1C rphost'
sudo ufw allow from 192.168.1.0/24 to any port 1545 proto tcp comment '1C RAS (администрирование)'
sudo ufw allow 80,443/tcp comment 'веб-публикация 1С (Apache)'
# PostgreSQL наружу открывать, только если СУБД и сервер 1С на разных машинах:
sudo ufw allow from 192.168.1.51 to any port 5432 proto tcp comment 'PostgreSQL для сервера 1С'
sudo ufw enable
sudo ufw status verbose                              # действующие правила и политики
sudo ufw status numbered && sudo ufw delete 3        # удалить правило по номеру
```

Порты 1С по умолчанию: **1540/tcp** — агент сервера (ragent), **1541/tcp** — менеджер кластера (rmngr), **1560–1591/tcp** — рабочие процессы (rphost), **1545/tcp** — сервер администрирования RAS; **5432/tcp** — PostgreSQL; **1947/tcp,udp** — менеджер лицензий Sentinel HASP (если используется сетевой ключ). Клиентским приложениям нужны 1541 и весь диапазон 1560–1591; 1540 — консоли администрирования и другим серверам кластера (на практике 1540–1541 открывают вместе).

### 3.9. Полезные пакеты

```bash
sudo apt install -y mc htop sysstat tmux curl wget unzip zip net-tools dnsutils \
  iotop iftop ncdu vim bash-completion rsync lsof strace tcpdump traceroute tree jq
```

| Пакет | Зачем |
|---|---|
| `mc` | двухпанельный файловый менеджер и редактор `mcedit` |
| `htop`, `iotop`, `iftop` | процессы/память, дисковый и сетевой ввод-вывод по процессам |
| `sysstat` | `iostat`, `mpstat`, `pidstat`, `sar`; сбор истории: `sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat && sudo systemctl enable --now sysstat` |
| `tmux` | сеансы, переживающие обрыв SSH (длинные операции: дампы, обновления) |
| `curl`, `wget`, `unzip`, `zip` | загрузка и распаковка дистрибутивов 1С/PostgreSQL |
| `net-tools` | старые `ifconfig`, `netstat` (их используют многие инструкции); современные аналоги — `ip`, `ss` из `iproute2` |
| `dnsutils` | `dig`, `nslookup` — проверка разрешения имён |
| `ncdu`, `tree` | кто занял диск; дерево каталогов |
| `lsof`, `strace`, `tcpdump`, `traceroute` | диагностика файлов, системных вызовов, сети |

### 3.10. Автоматические обновления (unattended-upgrades)

В Ubuntu Server пакет `unattended-upgrades` включён по умолчанию и ежедневно ставит **обновления безопасности**. Файлы [офиц.]:

- `/etc/apt/apt.conf.d/20auto-upgrades` — включение и периодичность;
- `/etc/apt/apt.conf.d/50unattended-upgrades` — что и как обновлять;
- таймеры `apt-daily.timer` (обновление списков) и `apt-daily-upgrade.timer` (установка);
- журналы — `/var/log/unattended-upgrades/`.

Для сервера БД разумный компромисс [практика]: обновления безопасности оставить, но запретить автоматическую перезагрузку и автообновление пакетов СУБД и 1С (их обновляют вручную в окно обслуживания):

```bash
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

```text
Unattended-Upgrade::Package-Blacklist {
    "postgresql";
    "postgrespro";
    "libpq";
    "1c-enterprise";
};
Unattended-Upgrade::Automatic-Reboot "false";
```

(элементы `Package-Blacklist` — регулярные выражения Python, привязанные к началу имени пакета [офиц.]). Дополнительно можно зафиксировать версии: `sudo apt-mark hold <пакет>`; просмотр — `apt-mark showhold`.

```bash
sudo unattended-upgrade -v --dry-run        # проверить, что было бы установлено
systemctl list-timers 'apt-daily*'          # когда сработают таймеры
```

Полное отключение (если обновления ставятся только вручную):

```bash
sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";
EOF
# либо: sudo dpkg-reconfigure -plow unattended-upgrades   (ответить «No»)
# либо: sudo apt remove unattended-upgrades
```

**needrestart: автоматический перезапуск служб (Ubuntu 24.04+)** [офиц.]. Подтверждено двумя первоисточниками:

- release notes 24.04: needrestart теперь «systematically restart services if affected by a library upgrade» — это относится и к unattended-upgrade; службы исключаются через секцию `override_rc` в `/etc/needrestart/needrestart.conf`;
- Ubuntu Server docs (automatic-updates): needrestart — инструмент, который unattended-upgrades вызывает после установки обновлений; «Since Ubuntu 24.04 LTS, needrestart restarts the affected services automatically by default»; чтобы исключить критичную службу, добавить файл в `/etc/needrestart/conf.d/`, задающий для неё `$nrconf{override_rc}` в `0`.

Для сервера 1С + PostgreSQL это означает: ночное обновление `libssl3`, `libc6`, `libpam` и т. п. может **перезапустить PostgreSQL и сервер 1С посреди работы** (обрыв сеансов и транзакций), даже если сами пакеты СУБД и 1С в `Package-Blacklist`. До 24.04 (22.04) needrestart в неинтерактивном режиме только выводил список.

Исключить службы СУБД и 1С из автоперезапуска (перезапускать их вручную в окно обслуживания):

```bash
sudo tee /etc/needrestart/conf.d/90-1c-postgres.conf >/dev/null <<'EOF'
# не перезапускать автоматически СУБД и сервер 1С (0 = не перезапускать)
$nrconf{override_rc}{qr(^postgresql)} = 0;
$nrconf{override_rc}{qr(^postgrespro)} = 0;
$nrconf{override_rc}{qr(^srv1cv8)} = 0;
$nrconf{override_rc}{qr(^ras)} = 0;
$nrconf{override_rc}{qr(^apache2)} = 0;
1;
EOF
sudo needrestart -r l          # только показать, какие службы требуют перезапуска (режим list)
sudo needrestart -b            # то же в пакетном (машиночитаемом) формате
```

Пояснения: `$nrconf{override_rc}` — «hash of regex», регулярные выражения проверяются в лексическом порядке, используется первое совпавшее (комментарии штатного `needrestart.conf`); штатный файл уже содержит такие исключения для dbus, сетевых служб и т. п. (`qr(^dbus) => 0`). Каталог `/etc/needrestart/conf.d/*.conf` подключается штатным конфигом. `$nrconf{restart}` — режим: `l` (только список), `i` (интерактивно), `a` (автоматически). Синтаксис присваивания отдельного элемента хэша (`$nrconf{override_rc}{qr(...)} = 0;`) и имена юнитов (`srv1cv8-<версия>@default`, `ras…`) — [практика]: после создания файла проверить `sudo needrestart -r l` и сверить имена командой `systemctl list-units --type=service | grep -i -E 'srv1cv8|ras|postgres'`. Радикальный вариант — `sudo apt remove needrestart` (тогда о необходимости перезапуска служб после обновления библиотек придётся помнить самому).

### 3.11. Отключение cloud-init

Установщик с ISO использует cloud-init для первичной настройки (пользователь, SSH, сеть). После первой загрузки на обычной ВМ он не нужен, только замедляет загрузку и может переписать сеть/hosts. Способы отключения [офиц., docs.cloud-init.io]:

```bash
cloud-init status --long                         # текущее состояние
sudo touch /etc/cloud/cloud-init.disabled        # способ 1: файл-флаг (рекомендуемый)
# способ 2: параметр ядра cloud-init=disabled в GRUB_CMDLINE_LINUX (/etc/default/grub) + sudo update-grub
sudo reboot
cloud-init status                                # → status: disabled
```

Третий официальный способ — переменная окружения `KERNEL_CMDLINE=cloud-init=disabled` для процессов cloud-init (например, через `DefaultEnvironment` в `/etc/systemd/system.conf`) — нужен редко.

**Свежие установщики отключают cloud-init сами** [офиц., исходный код subiquity `subiquity/models/subiquity.py`, ветка main на 10.10.2026]: для всех релизов, кроме 20.04 и 22.04, установщик добавляет в задание первой загрузки запись `write_files`, создающую `/etc/cloud/cloud-init.disabled` с текстом «Disabled by Ubuntu live installer after first boot. To re-enable cloud-init on this image run: sudo cloud-init clean --machine-id». То есть на системе, поставленной новым установщиком, `cloud-init status` уже покажет `disabled`, и делать ничего не нужно. ⚠ не подтверждено: с какой именно версии установщика/ISO это действует — проверять по факту (`ls -l /etc/cloud/cloud-init.disabled; cloud-init status`). Там же установщик кладёт `/etc/cloud/cloud.cfg.d/99-installer.cfg` (источник данных `None` с пользователем и SSH-настройками, права 0600), `/etc/cloud/cloud.cfg.d/20-disable-cc-dpkg-grub.cfg`, `/etc/cloud/ds-identify.cfg` (`policy: enabled`) и сценарий `/etc/cloud/clean.d/99-installer`, который при `cloud-init clean` удаляет эти файлы (для подготовки «золотого образа»).

Перед отключением убедиться, что сеть описана в собственном файле netplan (п. 3.3) — уже сгенерированные файлы cloud-init не удаляет. Радикальный вариант — `sudo apt purge cloud-init && sudo rm -rf /etc/cloud /var/lib/cloud` [практика]. Не отключать cloud-init, если ВМ — шаблон, который будет клонироваться с настройкой через cloud-init (Proxmox, облака).

### 3.12. Прочее

- `systemctl --failed` и `journalctl -p err -b` — после настройки не должно быть упавших служб и ошибок загрузки.
- `sudo systemctl status fstrim.timer` — еженедельный TRIM включён по умолчанию; нужен, чтобы динамические виртуальные диски и SSD хоста возвращали освободившееся место.
- Подкачка: `swapon --show`, `free -h`. Для сервера СУБД swap оставляют небольшим (страховка от OOM), а `vm.swappiness` снижают — см. статью о настройке ОС под PostgreSQL.

---

## 4. Виртуализация на Windows 11 Pro: настройки хоста и гостя

Общее правило для хоста Windows [практика]: схема электропитания «Высокая производительность» (`powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`), сон и гибернация отключены (`powercfg /hibernate off`), каталоги с виртуальными дисками исключены из проверки антивирусом, для ВМ настроены автозапуск и корректное завершение при выключении хоста. 1С чувствительна к частоте одного ядра, поэтому энергосбережение процессора на хосте заметно снижает её производительность.

Если на хосте включён Hyper-V (или зависящие от него функции: WSL2, «Изоляция ядра», Windows Sandbox), VMware Workstation и VirtualBox работают поверх гипервизора Windows (Windows Hypervisor Platform) — медленнее и с ограничениями; Microsoft предупреждает, что сторонние гипервизоры при работающем Hyper-V могут не запускать ВМ или работать ненадёжно [офиц.]. Вывод: на одном хосте выбрать **один** гипервизор; на Windows 11 Pro естественный выбор для постоянно работающего сервера — Hyper-V.

### 4.1. Hyper-V

#### Включение и требования [офиц.]

Windows 10/11 **Pro или Enterprise** (в Home роли нет), 64-разрядный процессор с SLAT и расширениями виртуализации (включить в UEFI), минимум 4 ГБ ОЗУ.

```powershell
# PowerShell от имени администратора
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
# или: DISM /Online /Enable-Feature /All /FeatureName:Microsoft-Hyper-V
# после перезагрузки:
Get-VMHost | Format-List Name, VirtualMachinePath, VirtualHardDiskPath
```

#### Создание ВМ под Ubuntu Server (пример)

```powershell
# 1. Внешний коммутатор (мост в физическую сеть)
Get-NetAdapter | Format-Table Name, InterfaceDescription, Status
New-VMSwitch -Name "External" -NetAdapterName "Ethernet" -AllowManagementOS $true

# 2. ВМ 2-го поколения с системным диском
New-VM -Name "srv1c" -Generation 2 -MemoryStartupBytes 16GB `
       -NewVHDPath "D:\VM\srv1c\system.vhdx" -NewVHDSizeBytes 80GB `
       -SwitchName "External" -Path "D:\VM"

# 3. Процессоры, фиксированная память, контрольные точки, автозапуск
Set-VM -Name "srv1c" -ProcessorCount 8 -StaticMemory `
       -AutomaticCheckpointsEnabled $false -CheckpointType Production `
       -AutomaticStartAction Start -AutomaticStopAction ShutDown

# 4. Secure Boot с шаблоном для Linux
Set-VMFirmware -VMName "srv1c" -EnableSecureBoot On -SecureBootTemplate "MicrosoftUEFICertificateAuthority"

# 5. Статический MAC (важно для DHCP-резервирования и лицензии 1С)
Set-VMNetworkAdapter -VMName "srv1c" -StaticMacAddress "00155D010A01"

# 6. Отдельные диски под данные и бэкапы (фиксированного размера)
New-VHD -Path "D:\VM\srv1c\pgdata.vhdx" -SizeBytes 200GB -Fixed
Add-VMHardDiskDrive -VMName "srv1c" -ControllerType SCSI -Path "D:\VM\srv1c\pgdata.vhdx"

# 7. ISO и порядок загрузки
Add-VMDvdDrive -VMName "srv1c" -Path "D:\ISO\ubuntu-24.04.5-live-server-amd64.iso"
Set-VMFirmware -VMName "srv1c" -FirstBootDevice (Get-VMDvdDrive -VMName "srv1c")
Start-VM -Name "srv1c"; vmconnect.exe localhost "srv1c"
```

#### Поколение ВМ и Secure Boot [офиц.]

- **Поколение 2** (UEFI, загрузка с виртуального SCSI, синтетические устройства, изменение размера загрузочного VHDX на лету) рекомендуется Microsoft для большинства нагрузок; поколение ВМ после создания изменить нельзя. В таблице Microsoft для Ubuntu 14.04–24.04 отмечены оба поколения; Ubuntu 26.04 в документации Microsoft (ред. 2025–2026) ещё не перечислена.
- Secure Boot включён по умолчанию, но шаблон по умолчанию — «Microsoft Windows». Для Linux нужно выбрать шаблон **«Microsoft UEFI Certificate Authority»** (Параметры ВМ → Безопасность → Шаблон; или `Set-VMFirmware … -SecureBootTemplate MicrosoftUEFICertificateAuthority`). Иначе загрузчик shim не пройдёт проверку подписи. Крайняя мера — `Set-VMFirmware -VMName srv1c -EnableSecureBoot Off`.
- **Сертификаты Secure Boot 2011 → 2023.** Подтверждено [офиц., support.microsoft.com]: «Microsoft UEFI CA 2011» (проверка сторонних загрузчиков, в т. ч. shim Linux) истёк **27.06.2026**, замена — «Microsoft UEFI CA 2023» (плюс отдельный «Microsoft Option ROM UEFI CA 2023»); «Microsoft Corporation KEK CA 2011» истёк 24.06.2026 (замена — KEK 2K CA 2023); «Microsoft Windows Production PCA 2011» истекает 19.10.2026 (замена — «Windows UEFI CA 2023»). Устройства без новых сертификатов, по словам Microsoft, продолжают запускаться и работать, но перестают получать обновления защиты ранней загрузки (DB/DBX, загрузчик). Для виртуальных сред Microsoft пишет, что новые сертификаты в виртуальную прошивку включает создатель среды (Hyper-V, VMware и т. д.) и что это действует для **новых** виртуальных устройств; в марте 2026 г. закрыта известная проблема «Secure Boot certificate updates might fail with Event ID 1795 on Hyper-V virtual machines». Со стороны Ubuntu: в 24.04.5 вошло исправление (LP 2146560), добавляющее ключи Microsoft 2023 в набор ключей виртуальной прошивки по умолчанию и средство добавления CA 2023 в существующие ВМ (для KVM/OVMF) [офиц., release notes 24.04.5]. ⚠ не подтверждено: содержит ли шаблон Hyper-V «Microsoft UEFI Certificate Authority» сертификат 2023 года на конкретной сборке Windows 11 и чем (2011 или 2023) подписан shim на конкретном ISO — прямого описания у Microsoft и Canonical найти не удалось. Практическое правило: если свежий ISO не грузится в ВМ 2-го поколения при верном шаблоне — установить последние накопительные обновления Windows на хосте и пересоздать ВМ; как временная мера — `Set-VMFirmware -VMName srv1c -EnableSecureBoot Off` (на работу 1С и PostgreSQL Secure Boot в госте не влияет).
- В ВМ 2-го поколения нет IDE, эмулируемой («устаревшей») сетевой карты, COM-портов по умолчанию и физического DVD — только ISO.

#### Память: статическая или динамическая [офиц. + практика]

Динамическая память Hyper-V: гость стартует со «Startup RAM», затем драйвер `hv_balloon` отдаёт хосту неиспользуемые страницы (ballooning) и получает дополнительные (hot-add) в пределах Minimum…Maximum. Microsoft позиционирует механизм для простаивающих и слабо нагруженных ВМ (VDI) и оговаривает для Linux: значения Startup/Minimum/Maximum должны быть кратны 128 МБ; операции могут не срабатывать, если гостю самому не хватает памяти; приложения, склонные занимать всю память, ограничивают примерно 80 % ОЗУ.

Почему для ВМ с PostgreSQL и сервером 1С это плохо:

- PostgreSQL резервирует `shared_buffers` при старте и активно использует страничный кэш ОС; «лишнюю» с точки зрения хоста память кэша balloon отберёт — производительность БД станет непредсказуемой, под нагрузкой возможен OOM-killer;
- huge pages и параметры, рассчитанные от объёма ОЗУ, теряют смысл, когда объём плавает;
- объём ОЗУ — ключевой параметр программной лицензии 1С (раздел 8).

Поэтому: `Set-VM -Name srv1c -StaticMemory` (или `Set-VMMemory -VMName srv1c -DynamicMemoryEnabled $false -StartupBytes 16GB`). Сумма памяти всех ВМ плюс 2–4 ГБ хосту не должна превышать физическую память.

#### Виртуальные коммутаторы [офиц. + практика]

| Тип | Что даёт | Применение |
|---|---|---|
| **External** | мост на физический адаптер: ВМ — полноправный узел локальной сети со своим IP | **сервер 1С, к которому ходят клиенты из сети** |
| **Internal** | сеть «ВМ ↔ хост», без выхода наружу; с `New-NetNat` превращается в NAT | изолированный стенд; ноутбук, где нет постоянной сети |
| **Private** | только ВМ между собой | закрытые стенды |
| **Default Switch** | готовый NAT с DHCP и DNS, создаётся автоматически на клиентской Windows | только чтобы быстро выйти в интернет: подсеть и адреса могут меняться после перезагрузки хоста, постоянный адрес в такой сети не удержать |

Собственный NAT (Internal + WinNAT), когда мост невозможен [офиц.]:

```powershell
New-VMSwitch -SwitchName "NATSwitch" -SwitchType Internal
Get-NetAdapter                                            # найти ifIndex адаптера «vEthernet (NATSwitch)»
New-NetIPAddress -IPAddress 192.168.100.1 -PrefixLength 24 -InterfaceIndex <ifIndex>
New-NetNat -Name "NATNetwork" -InternalIPInterfaceAddressPrefix 192.168.100.0/24
# проброс порта с хоста в ВМ (пример: SSH на 2222)
Add-NetNatStaticMapping -NatName "NATNetwork" -Protocol TCP -ExternalIPAddress 0.0.0.0 `
    -ExternalPort 2222 -InternalIPAddress 192.168.100.10 -InternalPort 22
Get-NetNatStaticMapping
```

Ограничения: на хосте поддерживается **одна** сеть NAT; DHCP в ней нет — адрес, шлюз (192.168.100.1) и DNS в госте задаются вручную (netplan). О работе клиентов 1С через NAT — раздел 5.

Мост через Wi-Fi-адаптер возможен, но работает хуже проводного (трансляция MAC на беспроводном канале) [практика] — сервер подключать к проводной сети.

#### Пакеты интеграции в госте

Драйверы Hyper-V (LIS: `hv_vmbus`, `hv_storvsc`, `hv_netvsc`, `hv_utils`, `hv_balloon`) входят в ядро Ubuntu («Built-in»); скачиваемый пакет LIS от Microsoft на Ubuntu ставить **нельзя** [офиц.]. Доустанавливаются только пользовательские демоны:

```bash
sudo apt update
sudo apt install -y linux-tools-virtual linux-cloud-tools-virtual
sudo reboot
```

| Что | Где | Назначение |
|---|---|---|
| `hv_kvp_daemon` (юнит `hv-kvp-daemon.service`) | пакет `linux-cloud-tools-common` (тянется метапакетом `linux-cloud-tools-virtual`), `/usr/sbin/hv_kvp_daemon` | обмен «ключ-значение»: хост видит IP и версию гостя (`Get-VMNetworkAdapter -VMName srv1c \| Select IPAddresses`), может внедрять статический IP |
| `hv_vss_daemon` (юнит `hv-vss-daemon.service`) | там же | заморозка ФС гостя для «производственных» контрольных точек и резервного копирования работающей ВМ |
| `hv_fcopy_daemon` — 24.04; **`hv_fcopy_uio_daemon` — 26.04** (юнит в обоих случаях `hv-fcopy-daemon.service`) | там же | копирование файлов с хоста (`Copy-VMFile`, нужна включённая служба «Guest Service Interface») |
| `lsvmbus` | **`linux-cloud-tools-common`** (`/usr/sbin/lsvmbus`), а не `linux-tools-*` | список устройств VMBus |
| `hv_get_dhcp_info`, `hv_get_dns_info`, `hv_set_ifconfig` | там же | вспомогательные скрипты KVP (получение/внедрение сетевых настроек) |

Состав пакета проверен по спискам файлов packages.ubuntu.com для noble (24.04) и resolute (26.04) [офиц.]: юниты `/usr/lib/systemd/system/hv-kvp-daemon.service`, `hv-vss-daemon.service`, `hv-fcopy-daemon.service`, правила udev `60-hv-*-daemon.rules` (запускают демоны при появлении соответствующих устройств VMBus).

Метапакеты `-virtual` соответствуют обычному ядру `generic`. Варианты ядра: `linux-virtual` — тот же образ ядра `generic`, но без пакета `linux-modules-extra` (нет части драйверов, в т. ч. USB/IP — см. раздел 10); `linux-azure` — ядро, настроенное под Azure/Hyper-V. Дословно у Microsoft (примечание 5 к таблице Ubuntu) [офиц.]: «On long term support (LTS) releases use latest virtual Hardware Enablement (HWE) kernel for up to date Linux Integration Services», и там же команда установки Azure-ядра: `apt-get update && apt-get install linux-azure`. Для локального сервера 1С достаточно штатного ядра `generic`; HWE (`linux-virtual-hwe-24.04` / `linux-generic-hwe-24.04`) или `linux-azure` — только если нужна конкретная исправленная функция интеграции. Если используется другое ядро, ставят соответствующие пакеты инструментов (`linux-tools-azure`, `linux-cloud-tools-azure`; для HWE — `linux-tools-virtual-hwe-24.04`, `linux-cloud-tools-virtual-hwe-24.04` [практика, имена сверить через `apt-cache search linux-cloud-tools`]).

Проверка:

```bash
lsmod | grep -E '^hv_|hyperv'                       # hv_vmbus, hv_storvsc, hv_netvsc, hv_utils, hv_balloon
ps -ef | grep -E 'hv_(kvp|vss|fcopy)' | grep -v grep # запущены ли демоны
systemctl status hv-kvp-daemon hv-vss-daemon hv-fcopy-daemon   # юниты из linux-cloud-tools-common
compgen -c hv_                                       # какие утилиты hv_* установлены (способ из документации Microsoft)
cat /sys/class/ptp/ptp*/clock_name                   # «hyperv» — источник времени хоста
sudo lsvmbus                                         # устройства VMBus (утилита из linux-cloud-tools-common)
```

На хосте: `Get-VMIntegrationService -VMName srv1c` (Heartbeat, Key-Value Pair Exchange, Shutdown, Time Synchronization, VSS, Guest Service Interface); включить службу: `Enable-VMIntegrationService -VMName srv1c -Name "Guest Service Interface"`. Статическое внедрение IP не работает, если интерфейсом управляет NetworkManager [офиц.] — на сервере с networkd проблемы нет.

#### Диски: тип, расширение, планировщик

- **VHDX**, а не VHD (до 64 ТБ, защита от повреждений, изменение размера на лету).
- **Фиксированный** (`New-VHD -Fixed`) — предсказуемая производительность и нет риска внезапно исчерпать диск хоста; **динамический** (по умолчанию у `New-VM`) растёт по мере записи, удобен для системного диска и стендов. Преобразование выключенной ВМ: `Convert-VHD -Path dyn.vhdx -DestinationPath fixed.vhdx -VHDType Fixed`.
- Для динамических VHDX под Linux Microsoft рекомендует [офиц.]: создавать с блоком 1 МБ (`New-VHD -Path D:\VM\test.vhdx -SizeBytes 127GB -Dynamic -BlockSizeBytes 1MB`), использовать ext4 и форматировать `mkfs.ext4 -G 4096 /dev/sdX1` — так файл VHDX меньше раздувается.
- **Планировщик ввода-вывода** в госте — `none`: решения о порядке запросов лучше оставить гипервизору [офиц.].

```bash
cat /sys/block/sda/queue/scheduler            # текущий планировщик в квадратных скобках
echo none | sudo tee /sys/block/sda/queue/scheduler
# постоянно — правилом udev:
echo 'ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/scheduler}="none"' | sudo tee /etc/udev/rules.d/60-io-scheduler.rules
sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=block
```

**Расширение VHDX.** На хосте (ВМ может работать, если диск на SCSI-контроллере; с IDE — только выключенная) [офиц.]:

```powershell
Resize-VHD -Path "D:\VM\srv1c\system.vhdx" -SizeBytes 160GB
```

В госте (системный диск с LVM от установщика: раздел 3 — PV):

```bash
echo 1 | sudo tee /sys/class/block/sda/device/rescan   # если новый размер не виден
lsblk                                                  # sda вырос, sda3 — ещё нет
sudo growpart /dev/sda 3                               # расширить раздел (пакет cloud-guest-utils); заодно исправляет резервный заголовок GPT
sudo pvresize /dev/sda3                                # расширить физический том LVM
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv # расширить LV и файловую систему
df -hT /
```

Диск данных без LVM: `sudo growpart /dev/sdb 1 && sudo resize2fs /dev/sdb1` (ext4) или `sudo xfs_growfs <точка_монтирования>` (XFS). Уменьшение VHDX Hyper-V выполняет без учёта разделов — конец раздела может оказаться за пределами диска с потерей данных; после любого изменения размера таблицу GPT нужно поправить (`growpart`/`parted`/`sgdisk -e`) [офиц.]. Для ВМ с лицензией 1С см. предупреждение о дисках в разделе 8.

Удобно, что диски на SCSI-контроллере Hyper-V можно добавлять в работающую ВМ: `Add-VMHardDiskDrive`, затем в госте `lsblk`.

#### Enhanced Session и доступ к консоли

Enhanced Session Mode — это RDP-подключение к гостю через шину VMBus (буфер обмена, перенаправление дисков). Для Linux требует графического окружения и `xrdp` с транспортом `hv_sock` (`Set-VM -VMName srv1c -EnhancedSessionTransportType HvSocket`) [практика; ⚠ параметра `-EnhancedSessionTransportType` нет в справке `Set-VM` на learn.microsoft.com (ред. для Windows Server 2025) — он известен по инструкциям сообщества для Windows 10 1803+/11; проверить `Get-Command Set-VM -Syntax`]; серверу без GUI не нужен. Рабочие способы: консоль `vmconnect.exe` для аварийных случаев, в остальное время — SSH (буфер обмена и передача файлов через `scp`/`sftp`, WinSCP, MobaXterm).

#### Автозапуск и завершение

`Set-VM -Name srv1c -AutomaticStartAction Start -AutomaticStartDelay 30 -AutomaticStopAction ShutDown` — ВМ стартует вместе с хостом и корректно выключается (через службу интеграции Shutdown) при его завершении. Значение по умолчанию `Save` (сохранение состояния) для сервера БД хуже: после возобновления «прыгает» время и рвутся соединения.

Допустимые значения [офиц., справка `Set-VM`]: `-AutomaticStartAction` — `Nothing`, `StartIfRunning`, `Start`; `-AutomaticStopAction` — `TurnOff`, `Save`, `ShutDown`; `-AutomaticStartDelay` — секунды; `-CheckpointType` — `Disabled`, `Standard`, `Production`, `ProductionOnly`; `-StaticMemory` / `-DynamicMemory` — переключатели, объём статической памяти задаётся `-MemoryStartupBytes`; у параметра `-Name` есть псевдоним `-VMName`. Проверить результат: `Get-VM srv1c | Format-List Name, State, ProcessorCount, MemoryStartup, DynamicMemoryEnabled, AutomaticStartAction, AutomaticStopAction, CheckpointType, AutomaticCheckpointsEnabled, Generation, Version`.

#### Ещё из «Best Practices for running Linux on Hyper-V» [офиц., Microsoft]

- **Меню GRUB в ВМ 2-го поколения**: из-за отсутствия эмулируемого таймера обратный отсчёт меню проходит мгновенно; чтобы меню успевало показаться, Microsoft советует `timeout=100000` вместо `timeout=5` в конфигурации GRUB (в Ubuntu — `GRUB_TIMEOUT` в `/etc/default/grub` + `sudo update-grub`). ⚠ актуальность для GRUB 2.12 в 24.04/26.04 не проверена — менять, только если меню действительно не видно.
- **kdump**: если аварийное ядро не загружается, увеличить резерв памяти — например, `crashkernel=384M-:128M` → `crashkernel=384M-:256M`. В 26.04 (как и с 24.10) kdump включается при установке по умолчанию, если система подходит под условия (≥ 4 потоков, 6 ГБ–2 ТБ ОЗУ, место в `/var` > 5 × (ОЗУ + подкачка), см. начало статьи) [офиц., release notes 26.04; документация Ubuntu Server «Kernel crash dump», уточнено 19.10.2026] — резерв `crashkernel` уменьшает память, доступную системе (`free -m`, `cat /proc/cmdline`). Выключить: `USE_KDUMP=0` в `/etc/default/kdump-tools` или `sudo apt remove kdump-tools`, затем перезагрузка (параметр `crashkernel=` перечитывается только при загрузке); состояние — `kdump-config show`.
- **Статический MAC** обязателен для Linux-ВМ в отказоустойчивом кластере (после переезда может смениться MAC и потеряться сетевая конфигурация) — для одиночного хоста это же правило защищает DHCP-резервирование и лицензию 1С.
- **Не смешивать** устаревший (legacy) и синтетический сетевые адаптеры в одной Linux-ВМ.
- После изменения размера VHD/VHDX с GPT утилиты разметки предупредят о несоответствии основной и резервной таблиц — исправление заголовков GPT безопасно и данных не затрагивает.

### 4.2. VMware Workstation Pro

- Workstation Pro бесплатна для коммерческого, учебного и личного использования, лицензионный ключ не требуется [офиц., release notes 26H1 на techdocs.broadcom.com]; бесплатной для личного использования она стала в мае 2024 г., для всех — с ноября 2024 г. (версия 17.6.2). Загрузка — с портала Broadcom после регистрации. Версии: 25H2 (14.10.2025), 25H2u1 (26.02.2026), **26H1 (14.05.2026, сборка 25388281)**, **26H1u1 (03.09.2026)** — последняя на октябрь 2026 [даты 25H2/25H2u1/26H1u1 — по хронологии версий в Википедии; 26H1 — офиц. release notes]. В 26H1 приложение стало полностью 64-разрядным, в список гостевых (и хостовых) ОС добавлена **Ubuntu 26.04 LTS**; Ubuntu 24.04 как гость поддерживается с 17.6. В 25H2 появилось определение режима Hyper-V/WHP, в 26H1u1 — автоматическое исправление ключа платформы (PK) Secure Boot.
- **Гостевые инструменты**: VMware рекомендует пакет **open-vm-tools** из репозитория дистрибутива, а не «VMware Tools» с ISO («VMware recommends using open-vm-tools redistributed by operating system vendors»; удалять пакет, поставленный дистрибутивом, не рекомендуется; `open-vm-tools-desktop` зависит от X и нужен только при графике) [офиц., Broadcom KB 2073803]:

```bash
sudo apt install -y open-vm-tools         # для сервера без GUI; open-vm-tools-desktop нужен только с графикой
systemctl status open-vm-tools            # служба vmtoolsd
vmware-toolbox-cmd -v                     # версия инструментов
vmware-toolbox-cmd timesync status        # периодическая синхронизация времени с хостом (обычно Disabled)
vmware-toolbox-cmd stat hosttime          # время хоста
```

- **Типы сети** (Edit → Virtual Network Editor):

| Режим | Виртуальная сеть | Смысл |
|---|---|---|
| Bridged | VMnet0 | ВМ в физической сети со своим IP — вариант для сервера 1С |
| NAT | VMnet8 | ВМ за NAT хоста; встроенный DHCP; шлюз обычно `x.x.x.2`, адаптер хоста `x.x.x.1`; проброс портов: Virtual Network Editor → VMnet8 → NAT Settings → Port Forwarding |
| Host-only | VMnet1 | только «хост ↔ ВМ» |

  Для моста в Virtual Network Editor явно указать физический адаптер вместо «Automatic» — иначе мост может сесть на Wi-Fi/VPN-адаптер [практика].
- **Оборудование ВМ** [практика]: сетевой адаптер `vmxnet3` (в .vmx `ethernet0.virtualDev = "vmxnet3"`) вместо e1000; диск на контроллере SCSI/NVMe; для БД — «Allocate all disk space now» (предвыделенный диск) и «Store virtual disk as a single file»; память ВМ полностью в ОЗУ хоста (Edit → Preferences → Memory → «Fit all virtual machine memory into reserved host RAM»).
- **Ubuntu в VMware и multipath** [практика]: служба `multipathd` в госте засоряет журнал сообщениями о дисках без идентификатора; лечится параметром `disk.EnableUUID = "TRUE"` в .vmx либо отключением ненужной службы: `sudo systemctl disable --now multipathd.service multipathd.socket`.
- **Клонирование/перенос**: на вопрос при запуске скопированной ВМ ответ «I copied it» генерирует новые UUID и MAC, «I moved it» — сохраняет. Для ВМ с программной лицензией 1С при переносе на другой диск/хост выбирать «I moved it» (раздел 8).
- **USB**: штатный проброс — VM → Removable Devices → <устройство> → Connect (раздел 10).
- **Автозапуск**: в Workstation 17+ есть настройка автозапуска ВМ при старте хоста (File → Configure Auto Start VMs, служба Windows «VMware Autostart Service», которую нужно перевести в автоматический запуск) — ⚠ не подтверждено: в оглавлении официального руководства «Using VMware Workstation Pro 17» (разделы «Configuring and Managing Virtual Machines», «Using Virtual Machines») такой темы найти не удалось; название пункта меню и службы приведены по памяти и материалам сообщества — проверить в своей версии. Запасной вариант, не зависящий от версии: задача Планировщика Windows «при запуске системы» с командой `"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe" -T ws start "D:\VM\srv1c\srv1c.vmx" nogui` [практика; в 26H1 (64-разрядная) путь установки может отличаться — уточнить по факту].

### 4.3. VirtualBox

- **Guest Additions** дают синхронизацию времени, общие папки, корректное завершение; для сервера без GUI главное — время и общие папки [офиц.]. Два взаимоисключающих способа установки (не смешивать) [практика]:

```bash
# способ 1: из ISO, поставляемого с VirtualBox (Устройства → Подключить образ диска Дополнений гостевой ОС)
sudo apt install -y build-essential dkms linux-headers-$(uname -r)
sudo mount /dev/cdrom /mnt
sudo sh /mnt/VBoxLinuxAdditions.run          # сообщение об отсутствии X Window на сервере — норма
sudo reboot
sudo rcvboxadd status-kernel                 # модули ядра
sudo rcvboxadd status-user                   # служба VBoxService
lsmod | grep vbox                            # vboxguest, vboxsf

# способ 2: пакет дистрибутива (версия может отставать от версии VirtualBox на хосте)
sudo apt install -y virtualbox-guest-utils
```

  Общая папка: `sudo mount -t vboxsf <имя_ресурса> /mnt/share`; автомонтируемые ресурсы появляются в `/media/sf_<имя>`, доступ — членам группы `vboxsf` (`sudo usermod -aG vboxsf admin`).
- **Режимы сети** [офиц.]:

| Режим | ВМ → хост | Хост → ВМ | ВМ ↔ ВМ | ВМ → сеть | Сеть → ВМ |
|---|---|---|---|---|---|
| NAT (по умолчанию) | да | проброс портов | нет | да | проброс портов |
| NAT Network | да | проброс портов | да | да | проброс портов |
| Bridged | да | да | да | да | да |
| Host-only | да | да | да | нет | нет |
| Internal | нет | нет | да | нет | нет |

  В NAT гость получает `10.0.2.15`, шлюз `10.0.2.2` (он же — доступ к loopback хоста), DNS `10.0.2.3`. Типовая схема стенда: адаптер 1 — NAT (интернет), адаптер 2 — Host-only (доступ с хоста по постоянному адресу). Для сервера, доступного из локальной сети, — Bridged.
- **Проброс портов в NAT** [офиц.]:

```powershell
VBoxManage modifyvm "srv1c" --natpf1 "ssh,tcp,,2222,,22"            # ВМ выключена: порт хоста 2222 → 22 гостя
VBoxManage controlvm "srv1c" natpf1 "ssh,tcp,,2222,,22"            # то же для работающей ВМ
VBoxManage modifyvm "srv1c" --natpf1 "ssh2,tcp,127.0.0.1,2222,,22" # слушать только на loopback хоста
VBoxManage modifyvm "srv1c" --natpf1 delete "ssh"                  # удалить правило
VBoxManage showvminfo "srv1c" | findstr /i "Rule"                  # показать правила
```

  Формат правила: `имя,протокол,IP_хоста,порт_хоста,IP_гостя,порт_гостя`. Ограничения NAT: только TCP/UDP, широковещательные рассылки ненадёжны.

  **Написание опций в VirtualBox 7.x** [офиц., справочник VBoxManage на virtualbox.org]: в актуальном руководстве опции `modifyvm` записаны через дефис и со знаком равенства — `--nat-pf1=...` (удаление: `--nat-pf1=delete=имя`), `--nic-type1=virtio`, `--bridge-adapter1=<имя>`, `--mac-address1=auto|<MAC>`; допустимые типы адаптера: `Am79C970A | Am79C973 | 82540EM | 82543GC | 82545EM | virtio | usbnet`. Слитное написание из этой статьи (`--natpf1`, `--nictype1`, `--bridgeadapter1`, `--macaddress1`) — синтаксис VirtualBox 6.x; 7.x его, как правило, тоже принимает (⚠ не подтверждено по документации — если команда отвергнута, использовать написание через дефис). Для `controlvm` (работающая ВМ) подкоманда по-прежнему пишется слитно: `natpf1 "правило"` и `natpf1 delete имя`.
- **Мост и адаптер**: `VBoxManage modifyvm "srv1c" --nic1 bridged --bridgeadapter1 "<имя адаптера хоста>" --nictype1 virtio --macaddress1 080027AABBCC`. Тип `virtio` (virtio-net) быстрее Intel PRO/1000, который быстрее PCnet [офиц.].
- **Диски**: контроллер по умолчанию — SATA (AHCI); образ фиксированного размера создаётся дольше, но не тратит время на рост [офиц.]: `VBoxManage createmedium disk --filename D:\VM\pgdata.vdi --size 204800 --variant Fixed` (размер в МБ); расширение — `VBoxManage modifymedium disk D:\VM\system.vdi --resize 163840` (размер в МБ; `--resizebyte` — в байтах), дальше в госте `growpart` и т. д., как в п. 4.1. Ограничение подтверждено руководством [офиц.]: «you can only resize dynamically allocated disk images that use the VDI and VHD formats», и только в сторону увеличения. Образ фиксированного размера (`--variant Fixed`) расширить нельзя: его сначала клонируют в динамический (`VBoxManage clonemedium disk fixed.vdi dyn.vdi --variant Standard`), расширяют и подключают вместо старого — а для ВМ с программной лицензией 1С это замена диска (раздел 8). Поэтому диск под данные в VirtualBox либо сразу делать с запасом, либо динамическим. Копировать файлы образов вручную нельзя (у образа есть UUID) — только `VBoxManage clonemedium` / `clonevm` [офиц.].
- **Критично для БД — кэш хоста и flush** [офиц.]:
  - «Use Host I/O Cache» (`VBoxManage storagectl "srv1c" --name "SATA" --hostiocache off`): с включённым кэшем хоста гость считает данные записанными раньше, чем они попали на физический диск, — при сбое хоста вероятность потери данных растёт. Для ВМ с PostgreSQL кэш хоста держать выключенным.
  - Запросы гостя на сброс кэша диска (FLUSH) VirtualBox **по умолчанию игнорирует** «ради производительности». Чтобы `fsync` PostgreSQL действительно доходил до диска: `VBoxManage setextradata "srv1c" "VBoxInternal/Devices/ahci/0/LUN#0/Config/IgnoreFlush" 0` (для каждого диска — свой номер `LUN#[x]`, 0–29; для IDE — `piix3ide` вместо `ahci`).
- **Запуск без окна**: `VBoxManage startvm "srv1c" --type headless`; корректное выключение — `VBoxManage controlvm "srv1c" acpipowerbutton`.
- **Extension Pack** для сервера 1С не нужен: в VirtualBox 7.x он даёт VRDP-сервер, проброс веб-камеры хоста, PXE ROM Intel, шифрование образов дисков и интеграцию с Oracle Cloud [офиц., руководство, введение]. Контроллеры USB 2.0 (EHCI) и 3.0 (xHCI) с версии 7.0.0 входят в базовый пакет («The EHCI and XHCI USB controller devices are now part of the open source base package» [офиц., Changelog 7.0]) — проброс USB-ключа HASP работает без Extension Pack.
- VirtualBox удобен для стендов; для постоянно работающего сервера БД на Windows-хосте предпочтительнее Hyper-V.

### 4.4. Proxmox VE / KVM (гость Ubuntu)

Не Windows-хост, но частый следующий шаг при переносе ВМ на выделенный сервер.

```bash
# в госте
sudo apt install -y qemu-guest-agent
sudo systemctl enable --now qemu-guest-agent
```

```bash
# на узле Proxmox
qm set <vmid> --agent 1          # включить канал агента ([практика] вступает в силу после полного выключения и включения ВМ, не после reboot из гостя)
qm agent <vmid> ping             # нет вывода об ошибке — агент отвечает
```

Агент нужен для корректного завершения гостя, получения его IP и **заморозки файловых систем (fsfreeze) при бэкапах и снапшотах** [офиц., Proxmox wiki].

Рекомендации по оборудованию ВМ [практика]: шина диска **VirtIO SCSI single** с `iothread=1` и `discard=on`, кэш диска «No cache» (`cache=none`; режимы `writeback`/`unsafe` для БД недопустимы); сеть **VirtIO**; тип процессора `host` (если нет живой миграции между разными CPU); ballooning выключить — `qm set <vmid> --balloon 0`. Драйверы virtio (`virtio_scsi`, `virtio_blk`, `virtio_net`) входят в ядро Ubuntu, отдельной установки не требуют.

Проброс USB (ключ HASP) [офиц., Proxmox wiki]: `lsusb` на узле → `qm set <vmid> -usb0 host=0529:0001` (по ID устройства) или `qm set <vmid> -usb0 host=2-1.2` (по порту — если одинаковых ключей несколько; адрес порта вики советует брать из `qm monitor <vmid>` → `info usbhost`, а не из `lsusb -t`); для USB 3.0 — `host=<…>,usb3=yes`; хабы пробросить нельзя («only "real" devices can be assigned»), но устройство за хабом можно назначить по адресу порта. `qm set <vmid> -delete usb0` меняет только конфигурацию — из работающей ВМ устройство не извлекается.

При клонировании Proxmox генерирует новые MAC и SMBIOS UUID; внутри гостя остаются прежние `machine-id` и SSH-ключи — см. п. 7.4.

### 4.5. WSL2 — можно ли использовать как сервер

WSL2 — служебная ВМ Hyper-V с ядром Linux от Microsoft, в которой дистрибутив запускается как контейнер. Свойства, существенные для сервера [офиц., learn.microsoft.com/windows/wsl]:

- **Экземпляр останавливается при простое**: `instanceIdleTimeout` (секция `[general]` файла `.wslconfig`, по умолчанию 15 000 мс; значение `-1` отключает автоостановку дистрибутива), `vmIdleTimeout` (секция `[wsl2]`, 60 000 мс, только Windows 11); Microsoft прямо пишет: «systemd services will NOT keep your WSL instance alive» [офиц., learn.microsoft.com/windows/wsl/systemd и wsl-config, ред. 2026]. При старте Windows WSL сам не запускается (нужна задача планировщика после входа пользователя) [практика].
- **Сеть**: по умолчанию NAT, адрес ВМ внутренний и меняется; доступ из локальной сети — через `netsh interface portproxy add v4tov4 listenport=<порт> listenaddress=0.0.0.0 connectport=<порт> connectaddress=<IP WSL>` на каждый порт, либо `networkingMode=mirrored` в `%UserProfile%\.wslconfig` (Windows 11 22H2+) плюс правила Hyper-V firewall.
- **Память**: по умолчанию до 50 % ОЗУ хоста (`memory` в `[wsl2]`), swap — 25 % памяти Windows; включено автоматическое возвращение кэша (`autoMemoryReclaim` в `[experimental]`, значения `disabled` / `gradual` / `dropCache`, по умолчанию `dropCache` — «cached memory will be reclaimed immediately») — страничный кэш PostgreSQL будет сбрасываться [офиц.].
- **Режимы сети** (`networkingMode` в `[wsl2]`) [офиц.]: `nat` (по умолчанию), `mirrored`, `none`, `consomme` (бывш. `virtioproxy`), `bridged` — помечен устаревшим с WSL 2.4.5; `mirrored` и `firewall` требуют Windows 11 22H2+.
- **systemd** включается в `/etc/wsl.conf` (`[boot] systemd=true`, требуется WSL 0.67.6+; для актуальной Ubuntu, которую ставит `wsl --install`, включён по умолчанию); имя хоста по умолчанию совпадает с именем Windows (`[network] hostname` в `wsl.conf`) [офиц.].
- Ядро и набор модулей — от Microsoft, а не Canonical; WSL нет в списке поддерживаемых ОС платформы 1С.
- ⚠ не подтверждено [практика]: MAC-адрес сетевого интерфейса WSL2 в режиме NAT меняется между запусками, из-за чего программная лицензия 1С, привязанная к такому «компьютеру», будет слетать. В официальной документации WSL (страницы wsl-config, networking, ред. 2026) про MAC-адрес интерфейса ничего не сказано и документированной настройки для его фиксации нет; проверить на своей системе: `ip -br link show eth0` до и после `wsl --shutdown`.

Вывод: WSL2 пригоден для учебных опытов и разработки (попробовать команды, собрать тестовую базу), но **не для сервера 1С и PostgreSQL**, к которому подключаются пользователи. Для этого — полноценная ВМ.

---

## 5. Сеть ВМ и разрешение имени сервера на клиентах 1С

### 5.1. Почему клиенту 1С нужно *имя* сервера

Клиент (тонкий, толстый, конфигуратор) подключается по строке `Srvr="srv1c";Ref="имя_базы"` к менеджеру кластера (порт 1541), а тот возвращает адрес рабочего процесса: **имя рабочего сервера, как оно зарегистрировано в кластере, и порт из диапазона 1560–1591**. Дальше клиент соединяется уже с этим именем. Отсюда три требования:

1. имя сервера (`srv1c`) должно разрешаться **на каждой клиентской машине** в адрес, по которому сервер реально доступен;
2. с клиента должны быть доступны порт 1541 и весь диапазон 1560–1591/tcp (1540 — агент сервера, нужен консоли администрирования кластера; обычно открывают вместе с 1541);
3. на самом сервере имя должно разрешаться в его сетевой IP (п. 3.2).

Типичный симптом нарушения п. 1: подключение по IP-адресу «почти работает» (порт 1541 отвечает), но клиент выдаёт ошибку сетевого доступа/«хост неизвестен» с именем сервера в тексте.

### 5.2. Варианты подключения ВМ

| Вариант | Как сделать | Плюсы / минусы |
|---|---|---|
| **Мост (рекомендуется)** | Hyper-V External; VMware Bridged (VMnet0); VirtualBox Bridged | ВМ — обычный узел сети со своим статическим IP; клиенты 1С работают без ухищрений |
| NAT + проброс портов | Hyper-V Internal + `New-NetNat` + `Add-NetNatStaticMapping`; VMware NAT Port Forwarding; VirtualBox `--natpf1` | работает, когда мост невозможен (корпоративный Wi-Fi, один разрешённый MAC); нужно пробрасывать 34 порта «один в один» и подменять имя на клиентах |
| Только хост (Host-only / Internal) | без проброса | стенд «всё на одном ПК»: клиент 1С запускается на самом хосте |

Проброс портов 1С в ВМ за NAT Hyper-V (номера портов снаружи и внутри должны совпадать, иначе клиент пойдёт на порт rphost, который не проброшен):

```powershell
$ports = @(1540, 1541) + (1560..1591)
foreach ($p in $ports) {
    Add-NetNatStaticMapping -NatName "NATNetwork" -Protocol TCP -ExternalIPAddress 0.0.0.0 `
        -ExternalPort $p -InternalIPAddress 192.168.100.10 -InternalPort $p
}
# входящее правило брандмауэра хоста [практика]; диапазон передаётся строкой, поэтому значения взяты в кавычки
New-NetFirewallRule -DisplayName "1C cluster to VM" -Direction Inbound -Protocol TCP `
    -LocalPort @('1540','1541','1560-1591') -Action Allow
Get-NetNatStaticMapping -NatName "NATNetwork" | Format-Table ExternalPort, InternalIPAddress, InternalPort   # проверить, что все 34 правила на месте
```

На клиентах при этом имя `srv1c` должно указывать на **IP хоста** Windows. Порт 5432 наружу не пробрасывают: с PostgreSQL работает только сервер 1С.

### 5.3. Имя сервера на клиентах Windows

Способ 1 — DNS (правильный для сети с доменом или роутером-DNS): A-запись `srv1c → 192.168.1.50` в зоне домена; на многих роутерах достаточно статической аренды DHCP с именем.

Способ 2 — файл hosts на каждом клиенте (годится для небольшой сети):

```powershell
# от имени администратора
notepad C:\Windows\System32\drivers\etc\hosts
#   добавить строку:   192.168.1.50   srv1c   srv1c.corp.local
ipconfig /flushdns
```

Проверка с клиента:

```powershell
Resolve-DnsName srv1c                       # или: ping srv1c
Test-NetConnection srv1c -Port 1541         # TcpTestSucceeded : True
Test-NetConnection srv1c -Port 1560
```

Проверка на сервере:

```bash
sudo ss -tlnp | grep -E ':(1540|1541|1545|15[6-9][0-9]|5432)\b'   # кто и на каких адресах слушает
sudo ufw status verbose
```

Замечания:

- Ubuntu Server не объявляет своё имя по NetBIOS/WINS; не рассчитывать, что Windows-клиенты «сами найдут» сервер по короткому имени — нужен DNS или hosts.
- Если сервер переименован или сменил IP, записи DNS/hosts и кэш клиентов (`ipconfig /flushdns`) нужно обновить; список баз у пользователей (`ibases.v8i`) хранит имя сервера.
- Веб-клиенту и мобильным клиентам имя кластера не нужно — им достаточно адреса веб-сервера (80/443).

---

## 6. Ресурсы ВМ под 1С + PostgreSQL

### 6.1. Процессор (vCPU)

- Число vCPU всех одновременно работающих ВМ не должно превышать число физических ядер хоста минус 1–2 ядра для самой Windows; переподписка CPU даёт задержки планирования, которые 1С (однопоточные серверные вызовы) переносит плохо [практика].
- Для 1С важнее частота и производительность одного ядра, чем их количество; для PostgreSQL ядра нужны под параллельные сеансы.
- **Лицензия на сервер 1С уровня ПРОФ использует не более 12 ядер**, причём в виртуальной среде считаются виртуальные ядра, заданные настройками ВМ [офиц., v8.1c.ru, «Вопросы и ответы по лицензированию», проверено 10.10.2026]. Детали оттуда же: сервер при большем числе ядер не отказывается работать, а просто «будут использоваться не более 12 ядер» (первые 12, которые перечислит ОС); на физическом сервере с Hyper-Threading «учитываться будут только физические ядра», на виртуальном (Hyper-V, VirtualBox, VMware) — «виртуальные ядра, состав которых определяется настройками виртуального сервера»; ограничение действует на каждый рабочий сервер кластера отдельно; второе ограничение ПРОФ — не более 500 одновременных сеансов. Выдавать серверу 1С ПРОФ больше 12 vCPU ради самой 1С бессмысленно (PostgreSQL на той же ВМ остальные ядра использовать может).
- Не менять число и модель vCPU после активации программной лицензии (раздел 8); в Hyper-V не переключать «режим совместимости процессора», в Proxmox не менять тип CPU.

### 6.2. Память

- **Только фиксированная**: Hyper-V — Static, VMware — вся память ВМ в ОЗУ хоста, Proxmox — `balloon 0`, VirtualBox всегда выделяет фиксированно.
- Официальный минимум 64-разрядного сервера 1С — «не менее 2 Гб (рекомендуется 4 Гб и выше)», диск «40 Гб и выше» [офиц., v8.1c.ru, проверено 10.10.2026] — это порог запуска. Таблица ниже — **⚠ не подтверждено источником: это экспертная оценка автора статьи**, а не рекомендация 1С или Postgres Professional (официальных таблиц «пользователи → vCPU/ОЗУ» для совмещённой ВМ нет); использовать как отправную точку и уточнять по фактической нагрузке (`htop`, `sar`, `pg_stat_activity`), размеру баз и типу конфигурации (ERP/КА требуют заметно больше, чем Бухгалтерия/УНФ):

| Пользователей одновременно | vCPU | ОЗУ | Комментарий |
|---|---|---|---|
| до 10 | 4 | 12–16 ГБ | небольшая бухгалтерия/УНФ |
| 10–30 | 6–8 | 24–32 ГБ | |
| 30–60 | 8–12 | 48–64 ГБ | при росте — разносить сервер 1С и СУБД по разным ВМ/хостам |

- Хосту Windows оставить не меньше 4 ГБ (с Hyper-V Manager и антивирусом — больше).
- Память под `shared_buffers`, huge pages, `work_mem` рассчитывается от объёма ОЗУ ВМ — см. статью о настройке PostgreSQL для 1С; менять объём ОЗУ ВМ значит пересчитывать конфигурацию СУБД.

### 6.3. Диски

- Главный ресурс СУБД — **время записи с подтверждением (fsync) журнала WAL**. Виртуальные диски размещать на SSD/NVMe хоста, не на HDD, сетевых папках или USB-дисках.
- **Фиксированный размер** для дисков с данными и WAL: нет накладных расходов на рост файла и фрагментации, нет риска, что на хосте кончится место и гипервизор поставит ВМ на паузу. Динамические — для системного диска и стендов.
- **Отдельные виртуальные диски** под данные, (опционально) WAL и бэкапы: независимое расширение и перенос, раздельная политика снапшотов и резервного копирования. Прирост скорости от выноса WAL есть только если это другой физический носитель. Бэкапы обязаны лежать на другом физическом устройстве, чем данные.
- **Контроллер**: Hyper-V Gen 2 — SCSI (единственный вариант); VMware — PVSCSI/NVMe; VirtualBox — SATA AHCI или NVMe; KVM — VirtIO SCSI.
- **Кэширование на хосте**: гарантии `fsync` в госте верны, только если гипервизор и хост честно сбрасывают данные на носитель. VirtualBox по умолчанию игнорирует FLUSH (п. 4.3) — исправить. В KVM — `cache=none`. На хосте не включать для диска с ВМ политику «отключить очистку буфера кэша записей Windows»; ноутбучные/настольные SSD без защиты от потери питания + отсутствие ИБП = риск повреждения БД при отключении электричества [практика].
- Файловая система в госте: ext4 (или XFS) с `noatime`; TRIM — штатным `fstrim.timer`.
- Антивирус хоста: исключить каталоги ВМ и файлы `*.vhdx`, `*.avhdx`, `*.vmdk`, `*.vdi`, процессы `vmms.exe`, `vmwp.exe` (Hyper-V) [практика, рекомендация Microsoft для хостов Hyper-V].

Быстрая проверка «честности» и скорости синхронной записи в госте [практика]:

```bash
sudo apt install -y fio
sudo fio --name=waltest --filename=/var/lib/postgresql/fio.tmp --size=1G --bs=8k --rw=write \
         --ioengine=sync --fdatasync=1 --runtime=30 --time_based
sudo rm /var/lib/postgresql/fio.tmp
# после установки PostgreSQL: pg_test_fsync -f /var/lib/postgresql/test.tmp
```

Ориентир (⚠ не подтверждено источником — практическая оценка, а не норматив): на потребительском SSD/NVMe без защиты от потери питания честный `fdatasync` даёт от сотен до нескольких тысяч операций в секунду; серверные SSD с конденсаторами (PLP) законно показывают десятки тысяч. Поэтому десятки тысяч IOPS на бытовом SSD — повод проверить, не игнорируются ли сбросы на диск (кэш хоста, IgnoreFlush в VirtualBox, `cache=unsafe/writeback` в KVM), а не доказательство само по себе. Сравнивайте результат в госте с тем же тестом на хосте: если в ВМ получается заметно быстрее, чем на «железе», сбросы где-то теряются.

### 6.4. Что ещё влияет на производительность 1С в ВМ [практика]

- схема электропитания хоста «Высокая производительность», отключённые глубокие C-состояния (VirtualBox прямо рекомендует отключать C1E/Intel C-State в BIOS при проблемах с производительностью [офиц.]);
- сервер 1С и PostgreSQL на одной ВМ обмениваются данными без сети — для небольших инсталляций это быстрее, чем две ВМ;
- отсутствие длинных цепочек снапшотов (каждая контрольная точка добавляет разностный диск);
- синтетические/паравиртуальные устройства (hv_netvsc, vmxnet3, virtio) вместо эмулируемых (e1000, IDE).

---

## 7. Снапшоты, резервное копирование и клонирование ВМ

### 7.1. Контрольные точки Hyper-V [офиц.]

| Тип | Что сохраняет | Согласованность |
|---|---|---|
| **Standard** | диски + память и состояние устройств работающей ВМ | после отката ВМ продолжает работу «с того же места» — со старым временем, старыми TCP-соединениями и состоянием СУБД в памяти; согласованность данных приложений не гарантируется |
| **Production** (по умолчанию) | только диски; в Linux-госте через «заморозку файловой системы» (fsfreeze, демон `hv_vss_daemon`) | согласованность на уровне ФС; после отката ВМ **выключена** и загружается заново — PostgreSQL выполнит восстановление по WAL |

```powershell
Set-VM -Name srv1c -CheckpointType Production          # при неудаче создаст Standard
Set-VM -Name srv1c -CheckpointType ProductionOnly      # при неудаче не создаст ничего (строже)
Set-VM -Name srv1c -AutomaticCheckpointsEnabled $false # убрать автоматические точки при каждом запуске
Checkpoint-VM -Name srv1c -SnapshotName "before-upgrade"
Get-VMCheckpoint -VMName srv1c
Restore-VMCheckpoint -VMName srv1c -Name "before-upgrade" -Confirm:$false
Remove-VMCheckpoint -VMName srv1c -Name "before-upgrade"   # слияние .avhdx с .vhdx
```

Командлеты `*-VMCheckpoint` — псевдонимы `*-VMSnapshot` (`Get-VMSnapshot`, `Restore-VMSnapshot`, `Remove-VMSnapshot`, `Export-VMSnapshot`, `Rename-VMSnapshot`): в модуле Hyper-V слова checkpoint и snapshot взаимозаменяемы [офиц.]. После применения Production-точки ВМ остаётся в выключенном состоянии, после Standard — возвращается в то же состояние вместе с содержимым памяти [офиц.].

Файлы контрольных точек (`.avhdx`) лежат рядом с `.vhdx`; удалять их вручную нельзя — только через удаление точки (Hyper-V сам выполнит слияние). Microsoft прямо указывает: контрольная точка — не полноценная резервная копия. Если в ВМ есть открытые файлы, восстановленным дискам может потребоваться `fsck`; живое резервное копирование может молча не сработать при подключённых iSCSI/pass-through дисках [офиц.].

### 7.2. Согласованность PostgreSQL при снимке диска [офиц., PostgreSQL docs, «File System Level Backup»]

- Копирование файлов работающего сервера (`tar`, `cp`, `rsync`) **не даёт пригодной копии** — сервер должен быть остановлен.
- «Замороженный снимок» тома допустим при работающем сервере: при запуске на таких данных PostgreSQL решит, что был аварийный останов, и воспроизведёт WAL. Условия: снимок **атомарный и одновременный для всех томов**, где лежат данные, табличные пространства и WAL; файлы WAL входят в снимок. Если данные и WAL на разных дисках и одновременность снимков не гарантируется — метод неприменим; нужна либо остановка сервера на время снимка, либо базовая копия с непрерывным архивированием.
- Перед снимком полезно выполнить `CHECKPOINT` — сократит время восстановления.

Практические следствия:

- Самый надёжный снапшот перед рискованной операцией (обновление платформы, ОС, СУБД) — **«холодный»**: остановить сервер 1С и PostgreSQL (или выключить ВМ), сделать точку, запустить.

```bash
systemctl list-units --type=service | grep -i -E 'srv1cv8|postgres'   # точные имена юнитов
sudo systemctl stop srv1cv8-8.3.27.1688@default   # сервер 1С; имя зависит от версии (старые сборки — srv1cv83)
sudo systemctl stop postgresql                    # или postgrespro-1c-17 / postgrespro-std-17 — по сборке
sudo sync
# … создать контрольную точку на хосте …
sudo systemctl start postgresql
sudo systemctl start srv1cv8-8.3.27.1688@default
```

(Номер версии в имени юнита — пример; шаблоны вида `'srv1cv8*'` в `systemctl start` не сработают для остановленных юнитов, поэтому имя указывают полностью.)

- Откат к точке возвращает **всю** ВМ: и базы, и журналы регистрации 1С, и системное время (до первой синхронизации). Данные, введённые после точки, теряются.
- Не держать точки неделями: растёт разностный диск, падает производительность, при удалении нужно свободное место и время на слияние.
- Точка хранится на том же носителе, что и ВМ, — от отказа диска хоста не защищает.

### 7.3. Бэкап ВМ целиком и бэкап средствами СУБД

| | Копия ВМ (Export-VM, Veeam, vzdump, копия VHDX выключенной ВМ) | Средства СУБД и 1С |
|---|---|---|
| Что восстанавливает | сервер целиком: ОС, настройки, 1С, СУБД | базы данных (и при PITR — на любой момент времени) |
| Согласованность БД | «как после сбоя питания» (горячая) или полная (холодная) | гарантированная |
| Гранулярность | вся ВМ | отдельная база / кластер; момент времени при архиве WAL |
| Объём и частота | большой, редко (еженедельно, перед изменениями) | малый, часто (ежедневно + WAL непрерывно) |
| Проверяемость | поднять копию ВМ в изолированной сети | восстановить дамп в тестовую базу |

Рекомендация [практика]: **оба уровня**. Основной — средствами СУБД: `pg_dump -Fc` по каждой базе и/или `pg_basebackup` + архив WAL (или pg_probackup); дополнительно выгрузка `.dt` для небольших баз. Вспомогательный — редкая копия ВМ целиком для быстрого подъёма сервера.

```powershell
Export-VM -Name srv1c -Path E:\Backup\VM            # экспорт (в т. ч. работающей ВМ) в каталог
Export-VMCheckpoint -VMName srv1c -Name "before-upgrade" -Path E:\Backup\VM
```

Восстановленную из копии ВМ на том же хосте с той же конфигурацией лицензия 1С, как правило, переживает; импорт с созданием нового идентификатора ВМ («Копировать виртуальную машину») и новым MAC — нет (раздел 8).

### 7.4. Клонирование ВМ: что дублируется и что ломается

| Что совпадает у клона | К чему приводит | Как исправить в клоне |
|---|---|---|
| `/etc/machine-id` | одинаковый DHCP-идентификатор (networkd строит его из DUID на основе machine-id) → DHCP выдаёт клону **тот же IP**, даже если MAC другой; совпадают идентификаторы journald/systemd | пересоздать machine-id |
| SSH host keys (`/etc/ssh/ssh_host_*`) | у двух серверов один «отпечаток»; клиенты не отличат подмену | удалить и сгенерировать заново |
| Имя хоста, `/etc/hosts` | конфликт имён в DNS, путаница в кластере 1С | `hostnamectl set-hostname`, правка hosts |
| Статический IP в netplan | конфликт адресов в сети | новый адрес до подключения к сети |
| MAC-адрес (если гипервизор не сменил) | конфликт в L2-сети | новый MAC в настройках ВМ |
| Реестр кластера 1С (`1cv8wsrv.lst`, `1CV8Clst.lst` в каталоге данных сервера) | кластер клона зарегистрирован под старым именем хоста; базы ссылаются на прежний сервер СУБД | пересоздать кластер/перерегистрировать базы на новом имени |
| Программная лицензия 1С (`*.lic`) | привязана к параметрам исходной ВМ → в клоне недействительна (и использовать одну лицензию на двух машинах нельзя) | отдельная лицензия либо HASP |
| Системный идентификатор кластера PostgreSQL, слоты, настройки архивации WAL | клон может начать писать WAL в тот же архив, что и оригинал | отключить/перенастроить `archive_command` в клоне |
| Состояние cloud-init (instance-id) | повторно не отработает или отработает неожиданно | `cloud-init clean` или отключить |

Особая опасность: если СУБД вынесена на отдельный сервер, клон сервера 1С при запуске **подключится к боевым базам**. Первый запуск клона — в изолированной сети (Private/Internal коммутатор, отключённый адаптер).

Действия в клоне (до подключения к рабочей сети):

```bash
# 1. имя
sudo hostnamectl set-hostname srv1c-test
sudo nano /etc/hosts                               # заменить старое имя и IP

# 2. machine-id
sudo rm -f /etc/machine-id /var/lib/dbus/machine-id
sudo systemd-machine-id-setup                      # создаёт новый /etc/machine-id
sudo ln -sf /etc/machine-id /var/lib/dbus/machine-id

# 3. ключи SSH-сервера
sudo rm -f /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server               # генерирует новые ключи (или: sudo ssh-keygen -A)
sudo systemctl restart ssh

# 4. сеть: новый адрес в /etc/netplan/*.yaml (и MAC в match:, если использовался)
sudo netplan apply

# 5. перезагрузка и проверка
sudo reboot
hostnamectl; cat /etc/machine-id; ip -br addr
```

На рабочей станции после смены ключей сервера: `ssh-keygen -R 192.168.1.50` (убрать старый отпечаток из `known_hosts`).

Подготовка **шаблона** (золотого образа) перед снятием копии:

```bash
sudo cloud-init clean --logs --machine-id   # если cloud-init используется: чистит состояние и сбрасывает machine-id [офиц.]
# без cloud-init:
sudo truncate -s 0 /etc/machine-id          # файл должен существовать, но быть пустым — ID сгенерируется при первой загрузке
sudo rm -f /var/lib/dbus/machine-id && sudo ln -s /etc/machine-id /var/lib/dbus/machine-id
sudo rm -f /etc/ssh/ssh_host_*              # без cloud-init ключи сами не появятся: после клонирования выполнить ssh-keygen -A
sudo shutdown -h now
```

В шаблон не включают активированную лицензию 1С, созданный кластер 1С и рабочие базы. Если клоны должны получать адреса по DHCP независимо от machine-id — в netplan добавить `dhcp-identifier: mac`.

Для Ubuntu 20.04 и старше при создании новой ВМ 2-го поколения копированием VHDX Microsoft требует заранее скопировать загрузчик: `sudo cp -r /boot/efi/EFI/ubuntu/ /boot/efi/EFI/boot` и `sudo mv /boot/efi/EFI/boot/shimx64.efi /boot/efi/EFI/boot/bootx64.efi` [офиц.]; для 22.04/24.04 это примечание в таблице Microsoft не указано.

---

## 8. Программная лицензия 1С и параметры ВМ

### 8.1. К чему привязывается лицензия

Программная лицензия (файл `*.lic`) привязывается либо к оборудованию компьютера, либо к ключу HASP; при привязке к компьютеру собираются и анализируются «ключевые параметры» его оборудования (источник — руководство администратора, глава 10 «Защита от несанкционированного использования: особенности и настройка», раздел о системе программного лицензирования; сам текст главы в этой работе не прочитан — см. статус ниже). В виртуальной машине «компьютер» — это сама ВМ: лицензия привязывается к её виртуальному оборудованию, и на каждую ВМ нужна своя лицензия.

**Статус раздела после вычитки 10.10.2026: уточнено по полному тексту документации 8.3.27 (разд. 10.3.1.4): ключевые параметры при привязке к компьютеру — наименование и версия ОС (в Linux при проверке не анализируются), сетевое имя компьютера, модель материнской платы, объём оперативной памяти, тип и версия BIOS, список процессоров и их параметры, список сетевых адаптеров и их MAC-адреса, список жёстких дисков и их параметры; при изменении хотя бы одного нужна повторная активация новым пин-кодом; параметры опрашиваются не чаще одного раза в сутки; анализируется только удаление устройств, а не добавление; память можно увеличивать, но не уменьшать ниже объёма на момент активации; внешние накопители USB и IEEE 1394 не учитываются. Прежний статус раздела: не подтверждено первоисточником.** Ни автору, ни рецензенту не удалось прочитать официальный текст: глава руководства администратора на its.1c.ru (v8327doc, глава 10 «Защита от несанкционированного использования: особенности и настройка») отдаётся инструменту в битой кодировке, англоязычная база kb.1ci.com переехала на support.1ci.com и глав руководства без входа не показывает, статьи Infostart отвечают HTTP 429, зеркало catalog.mista.ru — с просроченным сертификатом. Перечень и правила ниже совпадают с тем, как эту главу помнит рецензент и как её пересказывают форумы, но **перед любыми действиями с боевой ВМ главу нужно открыть в браузере** (ссылки — в конце раздела «Источники») и сверить формулировки для своей версии платформы (8.3.27 / 8.5.x). Что подтверждено официально (v8.1c.ru, «Вопросы и ответы по лицензированию»): на сервер «1С:Предприятия» можно установить произвольное количество файлов программных лицензий; с аппаратной защиты на программную можно перейти (платформа 8.2 и новее).

Перечень ключевых параметров — по тексту документации в пересказе Infostart и форумов:

| Параметр | Примечание |
|---|---|
| Наименование и версия ОС | **в Linux при проверке не анализируются** (для Windows — первые две цифры версии) |
| Серийный номер и дата установки ОС | только Windows |
| **Сетевое имя компьютера** | имя хоста |
| **Модель материнской платы** | в ВМ — виртуальная плата, зависит от гипервизора, поколения/версии ВМ, чипсета |
| **Объём оперативной памяти** | |
| **Тип и версия BIOS** | в ВМ — виртуальная прошивка (меняется при смене поколения/версии оборудования ВМ и гипервизора) |
| **Список процессоров и их параметры** | число и модель vCPU |
| **Список сетевых адаптеров и их MAC-адреса** | исключаются Bluetooth, адаптеры USB/IEEE 1394, программные WAN/RAS-адаптеры, адаптеры без MAC-адреса [по сообщению сотрудника 1С на форуме 1c-dn.com; ⚠ не подтверждено: официальный текст не прочитан] |
| **Список жёстких дисков и их параметры** | исключаются сетевые и внешние накопители USB/IEEE 1394 [по фрагменту англоязычной редакции руководства из поисковой выдачи; ⚠ не подтверждено: страница kb.1ci.com при вычитке не открылась] |
| Список видеоадаптеров | упоминается в старых редакциях (8.2) |

Правила сравнения [практика, по материалам Infostart и форумов; **⚠ не подтверждено: официальный текст не прочитан ни автором, ни рецензентом**]:

- при проверке анализируется **удаление** устройств, а не добавление: добавить второй сетевой адаптер или диск можно, заменить или убрать имеющийся — нельзя;
- оперативную память можно **увеличивать, но не уменьшать** относительно объёма на момент активации (подтверждено документацией 8.3.27, разд. 10.3.1.4: память можно увеличивать, но не уменьшать ниже объёма на момент активации; ранее: действует ли это для всех версий платформы и для Linux — не подтверждено; безопаснее считать объём ОЗУ неизменяемым);
- утверждение «проверка ключевых параметров выполняется не чаще одного раза в сутки» встречается в пересказах, но подтверждено документацией 8.3.27 (разд. 10.3.1.4: параметры компьютера опрашиваются не чаще одного раза в сутки); прежняя пометка: не подтверждено — не рассчитывать на то, что изменение ВМ «проявится только завтра» или что его можно успеть откатить;
- при изменении хотя бы одного ключевого параметра лицензию получают заново по **резервному пин-коду** («восстановление лицензии»); при исчерпании пин-кодов — обращение в Центр лицензирования 1С (lic@1c.ru) с описанием причины;
- при повторной активации сведения о владельце нужно ввести **в точности так же**, как при первой, — сохранить их в файл сразу после первой активации.

### 8.2. Какие действия с ВМ приводят к потере лицензии

| Действие | Затронутый параметр | Риск |
|---|---|---|
| Переименование хоста (`hostnamectl set-hostname`) | сетевое имя | **слетит** |
| Смена MAC: динамический MAC Hyper-V при переносе/импорте ВМ, пересоздание адаптера, «I copied it» в VMware, клонирование | сетевые адаптеры | **слетит** |
| Замена типа адаптера (e1000 → vmxnet3, устаревший → синтетический) | сетевые адаптеры | **слетит** (это удаление + добавление) |
| Добавление второго адаптера | — | допустимо (добавление) |
| Уменьшение ОЗУ; динамическая память/ballooning | объём ОЗУ | **слетит** / будет слетать непредсказуемо |
| Увеличение ОЗУ | объём ОЗУ | допустимо (по правилу выше) |
| Уменьшение числа vCPU; смена модели CPU (другой хост, режим совместимости процессора, тип CPU в Proxmox) | процессоры | высокий (список процессоров и их параметры входит в ключевые параметры по документации 8.3.27 (разд. 10.3.1.4); в остальном не подтверждено официальным текстом; следует из правила «удаление устройства из списка» и отчётов на форумах) |
| Увеличение числа vCPU | процессоры | **Уточнено 10.10.2026** (документация 8.3.27, разд. 10.3.1.4): процессоры входят в ключевые параметры, а общее правило — анализируется только удаление устройств, а не добавление; примеры в документации даны для сетевых адаптеров и памяти. Про добавление процессоров отдельно было не подтверждено: официального текста нет, на форумах описаны оба исхода — планировать как повторную активацию |
| Удаление/замена виртуального диска, перенос системы на новый диск, конвертация формата (VHDX↔VMDK↔VDI) | жёсткие диски | **слетит** |
| Расширение существующего диска (`Resize-VHD`, `modifymedium --resize`) | параметры диска | **Уточнено 10.10.2026** (документация 8.3.27, разд. 10.3.1.4): в ключевые параметры входит список жёстких дисков и их параметры; какие именно параметры диска сравниваются, документация не раскрывает. Ранее было не подтверждено: неизвестно, входит ли размер диска в «параметры» (официальный текст не прочитан, на форумах описаны оба исхода) — планировать как повторную активацию; надёжнее добавить новый диск, чем расширять старый |
| Добавление нового диска | — | допустимо (добавление) |
| Обновление версии/поколения ВМ (`Update-VMVersion`, «Upgrade virtual hardware»), смена чипсета, миграция между гипервизорами (V2V) | материнская плата, BIOS | высокий |
| Восстановление ВМ из резервной копии на тот же хост с той же конфигурацией и MAC | — | безопасно |
| Откат к контрольной точке | — | безопасно [практика] (конфигурация ВМ и файл лицензии возвращаются к состоянию на момент точки; если лицензия была активирована *после* точки — она исчезнет вместе с откатом, а использованный пин-код не вернётся) |
| Обновление ядра и ОС (`apt full-upgrade`, `do-release-upgrade`) | наименование и версия ОС (в пересказах документации — в Linux не анализируются) | обычное обновление пакетов и ядра на практике лицензию не затрагивает [практика]; подтверждено документацией 8.3.27 (разд. 10.3.1.4): в Linux наименование и версия ОС при проверке привязки не анализируются; прежняя оговорка: не подтверждено официальным текстом — перед `do-release-upgrade` иметь резервный пин-код и копию ВМ |

Известны и «необъяснимые» случаи (форум Infostart: лицензия слетала на VMware ESXi после перезагрузки без видимых изменений ВМ) — как правило, за ними стоит изменившийся идентификатор виртуального устройства.

### 8.3. Как не потерять лицензию

1. **Сначала окончательная конфигурация ВМ, потом активация**: имя хоста, число vCPU, объём ОЗУ (с запасом), сетевой адаптер нужного типа со **статическим MAC**, состав дисков.
2. Память — фиксированная; число и тип vCPU не менять; режим совместимости процессора не переключать.
3. Данные держать на отдельных дисках с запасом по размеру, чтобы реже менять дисковую подсистему; системный диск не заменять.
4. Перед любым изменением оборудования ВМ и перед переносом на другой хост убедиться, что есть неиспользованный резервный пин-код и сохранённые регистрационные данные.
5. Хранить копию файлов лицензий (в Linux — каталог `/var/1C/licenses`; подтверждено документацией 8.3.27 (разд. 10.3.8.3, сверено 10.10.2026); ранее было не подтверждено в этой вычитке первоисточником — путь общеизвестен по практике и совпадает с памятью рецензента о документации, но глава ИТС не прочитана; фактическое расположение проверить: `sudo find / -xdev -name '*.lic' 2>/dev/null`) — копия пригодна для восстановления только на машине с теми же ключевыми параметрами.
6. Не клонировать ВМ с активированной лицензией; тестовые стенды — с отдельной лицензией или лицензией разработчика.
7. Альтернативы привязке к «железу» ВМ [практика]: аппаратные ключи HASP (раздел 10); вынос сервиса лицензирования на отдельную маленькую ВМ, которую никогда не меняют и не переносят.

Диагностика на сервере: сообщения о ненайденной лицензии/ошибке привязки в окне клиента и технологическом журнале; состав и состояние лицензий — утилитой `ring license` из пакета «1С:Предприятие — утилита лицензирования» (⚠ команды и установка — в статье о лицензировании 1С).

**«Слепок» виртуального оборудования до и после изменений** [практика]. Раз точный алгоритм сравнения неизвестен, полезно перед активацией лицензии и перед любым изменением ВМ сохранить то, как гость видит своё «железо», и сравнить после изменения — если отличается хоть что-то из перечня ключевых параметров, готовить резервный пин-код:

```bash
{
  hostname; hostname -f
  sudo dmidecode -t bios -t system -t baseboard | grep -E 'Vendor|Version|Release Date|Manufacturer|Product Name|Serial Number|UUID'
  lscpu | grep -E 'Model name|^CPU\(s\)|Socket|Core|Thread'
  grep MemTotal /proc/meminfo; sudo dmidecode -t memory | grep -E '^\s+Size'
  ip -br link | grep -v '^lo'
  lsblk -d -o NAME,SIZE,MODEL,SERIAL,WWN,TRAN
} | sudo tee /root/hw-fingerprint-$(date +%F).txt
diff /root/hw-fingerprint-<дата1>.txt /root/hw-fingerprint-<дата2>.txt
```

Самый безопасный способ проверить рискованное изменение (расширение диска, добавление vCPU, обновление версии ВМ) — сначала сделать холодную копию ВМ (выключить, `Export-VM` или копия каталога ВМ; для изменений, не затрагивающих диски, достаточно контрольной точки), выполнить изменение, запустить 1С и убедиться, что лицензия получена; при неудаче вернуть прежнее состояние, не тратя пин-код. Для расширения диска нужна именно копия, а не контрольная точка: пока у ВМ Hyper-V есть контрольные точки, изменение размера её диска недоступно [практика].

---

## 9. Синхронизация времени в ВМ

Почему это важно для 1С и PostgreSQL: серверное время попадает в документы и журнал регистрации, по нему запускаются регламентные задания; сертификаты TLS, ЭДО и электронные подписи проверяются по времени; по меткам времени сопоставляют технологический журнал 1С с журналом PostgreSQL. Часы ВМ без синхронизации уходят быстрее, чем на физической машине, а после паузы, отката к точке или возобновления из сохранённого состояния показывают прошлое.

Общая схема: **в госте всегда работает NTP-клиент** (п. 3.4), а интеграция гипервизора используется как дополнение.

```bash
timedatectl                                   # «System clock synchronized: yes»
chronyc tracking 2>/dev/null || timedatectl timesync-status
cat /sys/devices/system/clocksource/clocksource0/current_clocksource   # hyperv_clocksource_tsc_page / kvm-clock / tsc
```

| Гипервизор | Что делает интеграция | Что настроить |
|---|---|---|
| **Hyper-V** | служба «Time Synchronization» (VMICTimeSync) через модуль `hv_utils` выставляет время при старте и **после паузы/восстановления**, а также создаёт PTP-устройство `/dev/ptp_hyperv` с временем хоста. Постоянной подстройки сама по себе не даёт [офиц., Microsoft] | NTP-клиент в госте. Вариант «брать время у хоста»: chrony + `refclock PHC /dev/ptp_hyperv …` (ниже). Хост Windows сам должен быть синхронизирован (`w32tm /query /status`, `w32tm /resync`). |
| **VMware** | периодическая синхронизация через tools по умолчанию выключена; разовая коррекция выполняется при возобновлении, откате к снапшоту, старте tools | NTP-клиент в госте; `vmware-toolbox-cmd timesync status` → оставить Disabled |
| **VirtualBox** | Guest Additions постоянно подводят время гостя к времени хоста: малые расхождения плавно, большие (после восстановления) — скачком [офиц.] | либо полагаться на GA (хост синхронизирован) и не держать второй источник, либо отключить: `VBoxManage setextradata "srv1c" "VBoxInternal/Devices/VMMDev/0/Config/GetHostTimeDisabled" 1` и оставить NTP [практика] |
| **KVM/Proxmox** | паравиртуальный источник `kvm-clock` | NTP-клиент (chrony) в госте |

chrony с временем хоста Hyper-V [офиц., рекомендация Microsoft для Linux-гостей]:

```bash
sudo apt install -y chrony
ls -l /dev/ptp_hyperv; cat /sys/class/ptp/ptp0/clock_name      # должно быть «hyperv»
sudo tee /etc/chrony/conf.d/hyperv.conf >/dev/null <<'EOF'
refclock PHC /dev/ptp_hyperv poll 3 dpoll -2 offset 0 stratum 2
makestep 1.0 -1
EOF
sudo systemctl restart chrony
chronyc sources -v                                              # источник PHC0 со знаком *
```

- `makestep 1.0 -1` — разрешить скачком исправлять расхождение больше 1 с **в любой момент** (по умолчанию chrony делает это только при первых обновлениях после старта, а дальше подводит часы плавно — после отката к снапшоту это может длиться часами).
- Если симлинка `/dev/ptp_hyperv` нет, Microsoft приводит правило udev: `SUBSYSTEM=="ptp", ATTR{clock_name}=="hyperv", SYMLINK += "ptp_hyperv"` (в новых версиях systemd оно уже есть).
- Если часы хоста ненадёжны (ПК не синхронизируется), источник хоста отключить: `Disable-VMIntegrationService -VMName srv1c -Name "Time Synchronization"` — и оставить в госте только сетевой NTP.
- Каталог `/etc/chrony/conf.d/` подключается штатным `chrony.conf` Ubuntu директивой `confdir`, а `/etc/chrony/sources.d/` — директивой `sourcedir` (наличие `sources.d` в 26.04 подтверждено release notes; строка `confdir` — ⚠ не подтверждено по первоисточнику, проверить: `grep -E '^(confdir|sourcedir)' /etc/chrony/chrony.conf`); если строки нет — дописать директивы прямо в `/etc/chrony/chrony.conf`.
- Строки `refclock PHC /dev/ptp_hyperv poll 3 dpoll -2 offset 0 stratum 2` и `makestep 1.0 -1` приведены у Microsoft дословно [офиц., learn.microsoft.com/azure/virtual-machines/linux/time-sync, ред. 2026]. Там же: `stratum 2` означает, что хост считается источником 2-го слоя, а гость сообщает о себе как о слое 3; устройство `/dev/ptp*` для времени хоста есть в ядрах 4.11+; сам по себе VMICTimeSync «doesn't provide ongoing time sync» между хостом и Linux-гостем, кроме коррекции после пауз; служба в Ubuntu называется `chrony` (`sudo systemctl restart chrony`).
- Не дублировать источники: в 26.04 серверы Ubuntu уже описаны в `/etc/chrony/sources.d/ubuntu-ntp-pools.sources` — повторять их в `chrony.conf` release notes прямо не советуют [офиц.].

После восстановления/возобновления ВМ: `sudo chronyc makestep` (chrony) или `sudo systemctl restart systemd-timesyncd` — и проверить `timedatectl`.

---

## 10. USB-ключи HASP в виртуальной машине

Аппаратные ключи 1С (Sentinel HASP, USB ID `0529:0001`) бывают клиентскими (локальные однопользовательские и сетевые многопользовательские) и серверными. **Серверный ключ должен быть виден локально на машине, где работает сервер 1С** — по сети он не раздаётся [практика, общеизвестное ограничение; подтверждено документацией 8.3.27 (глава 10: серверный ключ — только локальный, USB over IP для ключей не поддерживается; сверено 10.10.2026); ранее было не подтверждено первоисточником: глава ИТС о ключах защиты не прочитана, на странице вопросов и ответов v8.1c.ru этого пункта нет]. Подтверждено официально лишь то, что в отличие от аппаратного ключа на сервер можно установить неограниченное число файлов программных лицензий [офиц., v8.1c.ru]. Классический менеджер лицензий сетевых ключей (HASP License Manager, протокол NetHASP, настройки клиента в `nethasp.ini`) использует порт **475** (udp/tcp), менеджер из Sentinel LDK Run-time — порт **1947** [практика; ⚠ какой из них задействует конкретная версия платформы 1С в Linux — см. статью о лицензировании]. Сетевые клиентские ключи, наоборот, можно оставить на любой физической машине сети с менеджером лицензий HASP (порт 1947) и не пробрасывать в ВМ.

В госте Ubuntu ключу нужен драйвер: пакет `aksusbd` из Sentinel LDK Run-time Environment (на форуме Infostart подтверждена работа `aksusbd_10.11-1_amd64.deb` на Ubuntu 24.04; службы `aksusbd.service` и `hasplmd.service`, веб-интерфейс `http://localhost:1947`) либо `haspd` от Etersoft из старых инструкций 1С [практика]. В инструкции 1С на ИТС (metod8dev, эпоха 8.3.13 / Ubuntu 16.04) драйвер ставится так: `apt-get -y install libc6:i386`, затем `gdebi haspd_7.60-eter1ubuntu_amd64.deb`, `systemctl start haspd`, `systemctl status haspd` (пакеты — с ftp.etersoft.ru) [офиц., но устаревшее: для 22.04/24.04 сборки `haspd` от Etersoft может не быть — ⚠ актуальный способ см. в статье о лицензировании]. Проверка, что ключ дошёл до гостя: `lsusb | grep -i 0529`.

| Гипервизор | Проброс USB-ключа |
|---|---|
| **Hyper-V** | Штатного проброса произвольных USB-устройств в ВМ **нет**. Варианты: USB-over-IP (программный — usbipd-win, VirtualHere, USB Network Gate; аппаратный — сетевые USB-концентраторы вроде Digi AnywhereUSB), сетевой клиентский ключ на физической машине, либо переход с аппаратной защиты на программную лицензию (через партнёра 1С). |
| **VMware Workstation** | Штатно: в ВМ должен быть USB-контроллер; VM → Removable Devices → <ключ> → Connect (Disconnect from Host). Устройство остаётся за ВМ до отключения; автоподключение при старте — параметром `usb.autoConnect.device0` в .vmx (в инструкциях сообщества встречаются значения вида `"0x0529:0x0001"` или `"vid:0529 pid:0001"`) — ⚠ не подтверждено: в официальном руководстве Workstation Pro 17 (оглавление «Using VMware Workstation Pro») параметр не описан, статью базы знаний Broadcom найти не удалось; формат проверить опытным путём на своей версии. Без этого параметра Workstation обычно сам переподключает устройство к той ВМ, к которой оно было подключено при выключении [практика]. |
| **VirtualBox** | Настройки ВМ → USB → включить контроллер (xHCI) → добавить фильтр устройства. CLI: `VBoxManage list usbhost`; `VBoxManage usbfilter add 0 --target "srv1c" --name "HASP" --vendorid 0529 --productid 0001` (синтаксис по справочнику: `usbfilter add <index,0-N> --target=<uuid\|vmname\|global> --name=<строка> [--action=ignore\|hold] [--active=yes\|no] [--vendorid=XXXX] [--productid=XXXX] …`) [офиц.]. Контроллеры USB 2.0/3.0 с версии 7.0 входят в базовый пакет, Extension Pack не нужен [офиц., Changelog 7.0]. |
| **Proxmox/KVM** | `qm set <vmid> -usb0 host=0529:0001` (или по порту `host=<шина>-<порт>`); хабы не пробрасываются [офиц.]. |

**USB/IP с Windows-хоста в ВМ Hyper-V** (usbipd-win официально предназначен для передачи USB-устройств гостям Hyper-V и WSL 2) [офиц., README проекта]:

```powershell
# на хосте Windows, PowerShell от имени администратора
winget install usbipd
usbipd list                          # найти ключ и его BUSID, например 2-3
usbipd bind --busid=2-3              # «расшарить» устройство; настройка сохраняется после перезагрузки
```

```bash
# в госте Ubuntu
sudo apt install -y linux-tools-$(uname -r) linux-modules-extra-$(uname -r) hwdata
#   /usr/bin/usbip — обёртка из linux-tools-common; она ищет настоящий бинарник в /usr/lib/linux-tools/<версия ядра>/,
#   поэтому пакет linux-tools-* должен соответствовать именно работающему ядру (uname -r);
#   метапакет linux-tools-generic ставит инструменты для последнего ядра и после обновления ядра без перезагрузки может не совпасть
sudo modprobe vhci-hcd                             # клиентский модуль USB/IP (он в linux-modules-extra-<версия>-generic)
echo vhci-hcd | sudo tee /etc/modules-load.d/usbip.conf   # загружать модуль при старте системы
usbip list --remote=192.168.1.10                   # что отдаёт хост (192.168.1.10 — адрес хоста)
sudo usbip attach --remote=192.168.1.10 --busid=2-3
lsusb | grep -i 0529                               # ключ появился
```

Особенности [офиц. + практика]:

- хост слушает TCP **3240**; установщик usbipd-win сам добавляет правило брандмауэра для локальных подсетей [офиц., README];
- `usbipd bind` на хосте **сохраняется** («Sharing a device is persistent; it survives reboots»), а подключение на стороне клиента — **нет** («non-persistent»): после перезагрузки гостя или хоста, сброса или переподключения ключа команду `usbip attach` нужно повторить [офиц., README] — оформить unit systemd (пример ниже);
- модуль `vhci-hcd` поставляется в `linux-modules-extra-<версия ядра>-generic` (проверено поиском по содержимому пакетов packages.ubuntu.com для 24.04: `/lib/modules/6.8.0-31-generic/kernel/drivers/usb/usbip/vhci-hcd.ko.zst` — в `linux-modules-extra-6.8.0-31-generic`) [офиц.]. Серверный ISO ставит `linux-generic`, где этот пакет есть; при ядре, установленном через метапакет `linux-virtual` (облачные образы, minimal), `linux-modules-extra` не ставится — доустановить `sudo apt install linux-modules-extra-$(uname -r)` или перейти на `linux-generic`;
- обёртка `/usr/bin/usbip` (и `/usr/bin/usbipd`) входит в `linux-tools-common` [офиц., список файлов пакета]; если она пишет «WARNING: usbip not found for kernel …» — не установлен `linux-tools-$(uname -r)`;
- README usbipd-win для клиента Linux приводит только две команды — `usbip list --remote=<HOST>` и `sudo usbip attach --remote=<HOST> --busid=<BUSID>`; имена пакетов Ubuntu и `modprobe` выше — [практика];
- обрыв сети между гостем и хостом = «выдернутый» ключ: сеансы 1С потеряют лицензии. Для продуктива надёжнее программная лицензия или гипервизор со штатным пробросом.

Пример юнита для автоподключения ключа при загрузке гостя [практика, набросок — проверить на стенде; адрес хоста и BUSID свои]:

```ini
# /etc/systemd/system/usbip-hasp.service
[Unit]
Description=Attach HASP key from Windows host via USB/IP
Wants=network-online.target
After=network-online.target
Before=aksusbd.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/usr/sbin/modprobe vhci-hcd
ExecStart=/usr/bin/usbip attach --remote=192.168.1.10 --busid=2-3
ExecStop=/usr/bin/usbip detach --port=0
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now usbip-hasp.service
usbip port                         # какие удалённые устройства подключены и на каких портах vhci
journalctl -u usbip-hasp -b        # почему не подключилось (хост недоступен, устройство не расшарено)
```

Юнит подключает ключ только при старте; если связь с хостом пропадала, устройство нужно подключить заново (`sudo systemctl restart usbip-hasp`), после чего перезапустить драйвер ключа и проверить `lsusb`. Номер порта в `usbip detach --port=` смотреть в выводе `usbip port`.

Общие ограничения проброса USB: один ключ — одна ВМ; ВМ с проброшенным устройством нельзя мигрировать «на лету»; после перезагрузки хоста проверить, что ключ снова в ВМ (`lsusb`, страница `:1947`); два ключа одной серии на одной машине 1С не суммирует [практика].

---

## Типичные ошибки и подводные камни

| Симптом | Причина | Решение |
|---|---|---|
| После установки `df -h /` показывает половину диска (или 100 ГБ на большом диске) | политика установщика `scaled`: корневой LV меньше группы томов | `sudo vgs` → `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv` |
| ВМ Hyper-V 2-го поколения не грузится с ISO Ubuntu, ошибка проверки подписи загрузчика (Secure Boot) | выбран шаблон «Microsoft Windows» | Параметры → Безопасность → шаблон «Microsoft UEFI Certificate Authority» или `Set-VMFirmware -VMName srv1c -SecureBootTemplate MicrosoftUEFICertificateAuthority` |
| После перезагрузки хоста ВМ на «Default Switch» получила другой адрес, клиенты не подключаются | Default Switch — NAT с плавающей подсетью | External-коммутатор и статический IP; либо собственный NAT (`New-NetNat`) |
| Клиент 1С не подключается, в ошибке — имя сервера; при этом `Test-NetConnection <IP> -Port 1541` успешен | имя рабочего сервера не разрешается на клиенте | DNS-запись или строка в `C:\Windows\System32\drivers\etc\hosts`, `ipconfig /flushdns` |
| Клиент подключается к 1541, но зависает/падает при открытии базы | закрыт диапазон 1560–1591 (ufw, брандмауэр хоста, не проброшены порты NAT) | открыть/пробросить весь диапазон «порт в порт» |
| Статический IP «слетает» после перезагрузки, netplan снова с DHCP | cloud-init перегенерировал `50-cloud-init.yaml` | `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` с `network: {config: disabled}`, свой файл netplan; затем отключить cloud-init |
| `netplan apply` предупреждает «Permissions … are too open» | файл читается всеми | `sudo chmod 600 /etc/netplan/*.yaml` |
| После `netplan apply` по SSH пропала связь | ошибка в адресе/шлюзе/имени интерфейса | применять через `sudo netplan try`; чинить из консоли гипервизора |
| Клон ВМ получает по DHCP тот же IP, что и оригинал, хотя MAC другой | одинаковый `/etc/machine-id` → одинаковый DUID | пересоздать machine-id (п. 7.4) или `dhcp-identifier: mac` в netplan |
| При подключении по SSH: «REMOTE HOST IDENTIFICATION HAS CHANGED» | сервер переустановлен/клонирован/сменены host keys | убедиться, что это ожидаемо, затем `ssh-keygen -R <адрес>` на клиенте |
| У клона и оригинала одинаковый отпечаток SSH-сервера | клон не перегенерировал host keys | `sudo rm /etc/ssh/ssh_host_* && sudo dpkg-reconfigure openssh-server` |
| После изменения настроек ВМ 1С сообщает, что лицензия не обнаружена / ошибка привязки | изменился ключевой параметр (имя, MAC, ОЗУ, CPU, диск, BIOS) | вернуть параметр, если возможно; иначе повторная активация по резервному пин-коду (раздел 8) |
| Лицензия 1С периодически «отваливается» на ВМ Hyper-V | динамическая память (плавающий объём ОЗУ) или динамический MAC | `Set-VM -StaticMemory`, `Set-VMNetworkAdapter -StaticMacAddress`, затем переактивация |
| В госте памяти меньше, чем назначено; PostgreSQL падает по OOM или не может выделить huge pages | ballooning/динамическая память | фиксированная память ВМ |
| ВМ внезапно в состоянии Paused / «Приостановлено — критическое» | на диске хоста кончилось место (динамические диски, разросшиеся `.avhdx`) | освободить место, удалить (слить) контрольные точки; диски данных — фиксированные |
| Диск хоста заполняется файлами `.avhdx` | автоматические контрольные точки (включены по умолчанию на клиентской Windows) или забытые ручные | `Set-VM -AutomaticCheckpointsEnabled $false`, удалить точки через `Remove-VMCheckpoint` |
| После отката к контрольной точке время в прошлом, клиенты 1С отваливаются, база «откатилась» | Standard-точка возвращает память и все диски | использовать Production-точки или холодные снапшоты; после отката `sudo chronyc makestep`; помнить, что откатываются и базы |
| VHDX увеличен, а в госте место не прибавилось | не расширены раздел, PV, LV и ФС | `growpart` → `pvresize` → `lvextend -r` (п. 4.1) |
| Время в ВМ отстаёт/скачет, `System clock synchronized: no` | нет доступа к NTP, два конкурирующих механизма синхронизации, хост с неверным временем | настроить один источник (п. 3.4, раздел 9), синхронизировать хост |
| VMware Workstation / VirtualBox работают медленно или ВМ не стартует | на хосте включён Hyper-V / WSL2 / изоляция ядра | использовать Hyper-V, либо отключить компоненты Hyper-V на хосте |
| PostgreSQL в VirtualBox «слишком быстро» пишет, после сбоя хоста база повреждена | FLUSH игнорируется по умолчанию, включён кэш хоста | `IgnoreFlush` = 0 для каждого диска, `--hostiocache off` (п. 4.3) |
| Ключ HASP не виден в ВМ Hyper-V | Hyper-V не пробрасывает USB | USB/IP (usbipd-win), сетевой USB-концентратор, программная лицензия (раздел 10) |
| Автоматическое обновление ночью перезапустило PostgreSQL или обновило ядро | unattended-upgrades с настройками по умолчанию | `Package-Blacklist`, `apt-mark hold`, `Automatic-Reboot "false"` (п. 3.10) |
| Ночью оборвались сеансы 1С, в журнале — перезапуск `postgresql`/`srv1cv8`, хотя их пакеты не обновлялись | Ubuntu 24.04+: `needrestart` автоматически перезапускает службы, использующие обновлённую библиотеку (`libssl`, `libc`), в т. ч. после unattended-upgrades | файл в `/etc/needrestart/conf.d/` с `$nrconf{override_rc}{qr(^postgresql)} = 0;` и т. д. (п. 3.10); смотреть `/var/log/unattended-upgrades/`, `journalctl -u postgresql -u 'srv1cv8*'` |
| `systemctl restart sshd` → «Unit sshd.service not found» | в Ubuntu служба называется `ssh`; псевдонима `sshd` при сокет-активации (22.10+) может не быть | `sudo systemctl restart ssh` (п. 3.7) |
| Сменили `Port` в `sshd_config`, а sshd слушает старый порт (24.04) | порт слушает `ssh.socket`, а не сам sshd | `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket` (п. 3.7) |
| В `/etc/netplan/` нет `50-cloud-init.yaml` (или, наоборот, нет `00-installer-config.yaml`), инструкция «не сходится» | имя файла зависит от версии установщика | работать с тем файлом, что есть: `ls -l /etc/netplan/ /etc/cloud/cloud.cfg.d/` (п. 3.3) |
| `lsvmbus: command not found` после `apt install linux-tools-virtual` | `lsvmbus` лежит в `linux-cloud-tools-common` | `sudo apt install linux-cloud-tools-virtual` |
| `usbip`: «WARNING: usbip not found for kernel …» или `modprobe: FATAL: Module vhci-hcd not found` | нет `linux-tools-<версия ядра>` / `linux-modules-extra-<версия ядра>` для работающего ядра | `sudo apt install linux-tools-$(uname -r) linux-modules-extra-$(uname -r)` (раздел 10) |
| Свежий ISO Ubuntu не грузится в ВМ Hyper-V 2-го поколения при шаблоне «Microsoft UEFI Certificate Authority» | возможно, загрузчик подписан сертификатом UEFI CA 2023, которого нет в виртуальной прошивке (⚠ гипотеза, см. п. 4.1) | обновить Windows на хосте и пересоздать ВМ; временно `Set-VMFirmware -EnableSecureBoot Off` |
| `VBoxManage modifymedium --resize` завершается ошибкой на диске фиксированного размера | расширять можно только динамические VDI/VHD | клонировать в динамический образ (`clonemedium --variant Standard`) и расширить его; учесть лицензию 1С (п. 4.3, раздел 8) |
| Кластер 1С выдаёт клиентам 127.0.1.1 / сервер «не видит сам себя» по имени | в `/etc/hosts` имя хоста привязано к `127.0.1.1` | привязать имя к реальному IP (п. 3.2) |
| После переименования сервера кластер 1С не запускается/базы не открываются, лицензия слетела | имя хоста прописано в реестре кластера и входит в параметры лицензии | имя задавать до установки 1С; иначе — пересоздание кластера и повторная активация |
| Инструкция из интернета с `apt-key add` не работает на 26.04 | в APT 3.1 `apt-key` удалён | ключ в `/etc/apt/keyrings/*.gpg` + `signed-by=` в описании репозитория |
| Экземпляр WSL2 с PostgreSQL «сам выключается», из сети недоступен | особенности WSL2 (простой, NAT) | не использовать WSL2 как сервер; развернуть ВМ |
| В журнале Ubuntu под VMware поток сообщений от `multipathd` о дисках | у виртуальных дисков нет идентификатора | `disk.EnableUUID = "TRUE"` в .vmx или отключить `multipathd` |

---

## Быстрая шпаргалка

### В госте Ubuntu

| Задача | Команда |
|---|---|
| Версия ОС и ядра | `lsb_release -a`; `uname -r` |
| Обновить систему | `sudo apt update && sudo apt full-upgrade -y` |
| Нужна ли перезагрузка | `cat /var/run/reboot-required` |
| Задать имя хоста | `sudo hostnamectl set-hostname srv1c` |
| Проверить разрешение имени | `getent hosts srv1c`; `hostname -f`; `hostname -I` |
| Адреса и маршруты | `ip -br addr`; `ip route` |
| Применить netplan безопасно | `sudo netplan try` → `sudo netplan apply` |
| Запретить cloud-init трогать сеть | `echo 'network: {config: disabled}' \| sudo tee /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` |
| Отключить cloud-init | `sudo touch /etc/cloud/cloud-init.disabled` |
| Часовой пояс | `sudo timedatectl set-timezone Europe/Moscow` |
| Состояние синхронизации времени | `timedatectl`; `timedatectl timesync-status`; `chronyc tracking` |
| Сгенерировать русскую локаль | `sudo locale-gen ru_RU.UTF-8 && sudo update-locale LANG=ru_RU.UTF-8` |
| Дать пользователю sudo | `sudo usermod -aG sudo <user>` |
| Проверить конфигурацию sshd | `sudo sshd -t`; `sudo sshd -T \| grep -i passwordauth` |
| Открыть порты кластера 1С | `sudo ufw allow 1540:1541/tcp && sudo ufw allow 1560:1591/tcp` |
| Состояние ufw | `sudo ufw status verbose` |
| Кто слушает порты | `sudo ss -tlnp` |
| Диски, тома, место | `lsblk -f`; `sudo vgs`; `sudo lvs`; `df -hT` |
| Расширить корневой LV на весь VG | `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv` |
| Расширить раздел после увеличения диска | `sudo growpart /dev/sda 3 && sudo pvresize /dev/sda3` |
| Планировщик ввода-вывода | `cat /sys/block/sda/queue/scheduler` |
| Тест синхронной записи | `fio --name=t --filename=<файл> --size=1G --bs=8k --rw=write --ioengine=sync --fdatasync=1 --runtime=30 --time_based` |
| Пакеты для Hyper-V | `sudo apt install linux-tools-virtual linux-cloud-tools-virtual` |
| Пакет для VMware | `sudo apt install open-vm-tools` |
| Пакет для Proxmox/KVM | `sudo apt install qemu-guest-agent` |
| Модули и демоны Hyper-V | `lsmod \| grep hv_`; `ps -ef \| grep hv_` |
| В какой среде виртуализации гость | `systemd-detect-virt` (microsoft / vmware / oracle / kvm / wsl) |
| Виртуальное «железо» глазами гостя | `sudo dmidecode -t system -t bios -t baseboard`; `ip -br link`; `lscpu`; `free -m` |
| Новый machine-id | `sudo rm /etc/machine-id && sudo systemd-machine-id-setup` |
| Новые ключи SSH-сервера | `sudo rm /etc/ssh/ssh_host_* && sudo dpkg-reconfigure openssh-server` |
| Проверка автообновлений | `sudo unattended-upgrade -v --dry-run`; `systemctl list-timers 'apt-daily*'` |
| Какие службы needrestart хочет перезапустить | `sudo needrestart -r l` |
| Запретить needrestart трогать СУБД и 1С | файл `/etc/needrestart/conf.d/90-1c-postgres.conf` со строками `$nrconf{override_rc}{qr(^postgresql)} = 0;` … (п. 3.10) |
| Состояние cloud-init | `cloud-init status --long`; `ls -l /etc/cloud/cloud-init.disabled` |
| Какие файлы сети оставил установщик | `ls -l /etc/netplan/ /etc/cloud/cloud.cfg.d/` |
| Слушает ли SSH (сокет-активация) | `systemctl is-enabled ssh.socket ssh.service`; `sudo ss -tlnp \| grep ':22'` |
| «Слепок» оборудования ВМ для лицензии 1С | `sudo dmidecode -t bios -t system -t baseboard`; `lscpu`; `grep MemTotal /proc/meminfo`; `ip -br link`; `lsblk -d -o NAME,SIZE,MODEL,SERIAL` |
| Юниты демонов Hyper-V | `systemctl status hv-kvp-daemon hv-vss-daemon hv-fcopy-daemon` |
| Инструменты USB/IP под работающее ядро | `sudo apt install linux-tools-$(uname -r) linux-modules-extra-$(uname -r) hwdata` |
| Подключённые по USB/IP устройства | `usbip port` |
| Виден ли ключ HASP | `lsusb \| grep -i 0529` |
| Подключить USB по сети | `sudo modprobe vhci-hcd && sudo usbip attach --remote=<хост> --busid=<busid>` |

### На хосте Windows (PowerShell от администратора)

| Задача | Команда |
|---|---|
| Включить Hyper-V | `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All` |
| Внешний коммутатор | `New-VMSwitch -Name External -NetAdapterName "Ethernet" -AllowManagementOS $true` |
| Шаблон Secure Boot для Linux | `Set-VMFirmware -VMName srv1c -SecureBootTemplate MicrosoftUEFICertificateAuthority` |
| Фиксированная память | `Set-VM -Name srv1c -StaticMemory` |
| Число vCPU | `Set-VM -Name srv1c -ProcessorCount 8` |
| Статический MAC | `Set-VMNetworkAdapter -VMName srv1c -StaticMacAddress 00155D010A01` |
| Отключить автоточки | `Set-VM -Name srv1c -AutomaticCheckpointsEnabled $false` |
| Автозапуск и корректное выключение | `Set-VM -Name srv1c -AutomaticStartAction Start -AutomaticStopAction ShutDown` |
| Создать / откатить / удалить точку | `Checkpoint-VM -Name srv1c -SnapshotName x`; `Restore-VMCheckpoint -VMName srv1c -Name x`; `Remove-VMCheckpoint -VMName srv1c -Name x` |
| Новый фиксированный диск | `New-VHD -Path D:\VM\d.vhdx -SizeBytes 200GB -Fixed`; `Add-VMHardDiskDrive -VMName srv1c -ControllerType SCSI -Path D:\VM\d.vhdx` |
| Увеличить диск | `Resize-VHD -Path D:\VM\srv1c\system.vhdx -SizeBytes 160GB` |
| Службы интеграции | `Get-VMIntegrationService -VMName srv1c` |
| IP гостя с хоста | `(Get-VMNetworkAdapter -VMName srv1c).IPAddresses` |
| Экспорт ВМ | `Export-VM -Name srv1c -Path E:\Backup\VM` |
| NAT-сеть | `New-VMSwitch -SwitchName NATSwitch -SwitchType Internal`; `New-NetIPAddress …`; `New-NetNat -Name NATNetwork -InternalIPInterfaceAddressPrefix 192.168.100.0/24` |
| Проброс порта в NAT | `Add-NetNatStaticMapping -NatName NATNetwork -Protocol TCP -ExternalIPAddress 0.0.0.0 -ExternalPort 2222 -InternalIPAddress 192.168.100.10 -InternalPort 22` |
| Имя сервера на клиенте | строка `192.168.1.50 srv1c` в `C:\Windows\System32\drivers\etc\hosts`; `ipconfig /flushdns` |
| Проверка порта с клиента | `Test-NetConnection srv1c -Port 1541` |
| Схема питания «Высокая производительность» | `powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` |
| VirtualBox: проброс порта | `VBoxManage modifyvm "srv1c" --natpf1 "ssh,tcp,,2222,,22"` |
| VirtualBox: честный flush | `VBoxManage setextradata "srv1c" "VBoxInternal/Devices/ahci/0/LUN#0/Config/IgnoreFlush" 0` |
| USB-ключ в сеть (USB/IP) | `usbipd list`; `usbipd bind --busid=<busid>` |

---

## Источники

Официальные:

- https://ubuntu.com/about/release-cycle — сроки стандартной поддержки, ESM и Legacy add-on для 20.04–26.04.
- https://endoflife.date/ubuntu — точные даты выпуска и окончания поддержки, включая 25.04/25.10, даты point-релизов 24.04.5 и 26.04.1.
- https://releases.ubuntu.com/26.04/ — имена ISO-образов 26.04 / 26.04.1.
- https://documentation.ubuntu.com/release-notes/26.04/ и …/26.04/summary-for-lts-users/ — дата выпуска 26.04, путь обновления, изменения относительно 24.04 (ядро 7.0, sudo-rs, chrony, dracut, APT 3.1, OpenSSH 10.2, systemd 259).
- https://ubuntu.com/server/docs/reference/installation/system-requirements/ — минимальные требования Ubuntu Server 24.04.
- https://ubuntu.com/server/docs/tutorial/basic-installation/ — базовый сценарий установки.
- https://canonical-subiquity.readthedocs-hosted.com/en/latest/tutorial/screen-by-screen.html — экраны установщика subiquity.
- https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html — справочник autoinstall: `sizing-policy` (правила scaled), `identity`, `ssh`, `storage`, `source`, `updates`, `shutdown`.
- https://canonical-subiquity.readthedocs-hosted.com/en/latest/tutorial/providing-autoinstall.html — способы передачи autoinstall и порядок их поиска.
- https://netplan.readthedocs.io/en/stable/netplan-yaml/ — ключи netplan (`routes`, `dhcp-identifier`, `nameservers`, устаревание `gateway4`).
- https://docs.cloud-init.io/en/latest/howto/disable_cloud_init.html и …/reference/cli.html — отключение cloud-init, `cloud-init clean --machine-id`.
- https://ubuntu.com/server/docs/how-to/software/automatic-updates/ — unattended-upgrades: файлы, параметры, таймеры.
- https://ubuntu.com/server/docs/how-to/networking/timedatectl-and-timesyncd/ — timesyncd и замена его на chrony с 25.10.
- https://packages.ubuntu.com/noble/linux-cloud-tools-virtual и https://manpages.ubuntu.com/manpages/noble/man8/hv_kvp_daemon.8.html — пакеты с демонами Hyper-V.
- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/ (подразделы «Операционные системы», «Аппаратные требования», «Список поддерживаемых СУБД», «Список ОС для поддерживаемых СУБД») — версии Ubuntu для сервера и клиента 1С, версии PostgreSQL с патчем 1С и ОС для них, минимальные требования сервера.
- https://v8.1c.ru/predpriyatie/questions_licence.htm — ограничение лицензии ПРОФ 12 ядрами и учёт виртуальных ядер.
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux и …/18/… — поддерживаемые версии Ubuntu для Postgres Pro Standard 17/18, имена пакетов и каталогов.
- https://1c.postgres.ru/ — порядок получения сборок PostgreSQL для 1С от Postgres Professional.
- https://www.postgresql.org/docs/current/backup-file.html — требования к файловым копиям и «замороженным» снимкам (PostgreSQL 18).
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/supported-ubuntu-virtual-machines-on-hyper-v — возможности Ubuntu в Hyper-V, примечания о динамической памяти, `linux-azure`, копировании VHDX.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/best-practices-for-running-linux-on-hyper-v — блок 1 МБ и `mkfs.ext4 -G 4096` для динамических VHDX, планировщик `none`, изменение размера VHDX и GPT.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/plan/should-i-create-a-generation-1-or-2-virtual-machine-in-hyper-v — поколения ВМ, Secure Boot и шаблон UEFI CA.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/dynamic-memory — механизм динамической памяти.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/checkpoints — типы контрольных точек и команды.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/setup-nat-network — NAT-сеть на Internal-коммутаторе.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/install-hyper-v — требования и включение Hyper-V.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/manage/manage-hyper-v-integration-services — службы интеграции и демоны в Linux.
- https://learn.microsoft.com/en-us/powershell/module/hyper-v/resize-vhd — изменение размера VHD/VHDX.
- https://learn.microsoft.com/en-us/azure/virtual-machines/linux/time-sync — VMICTimeSync, `/dev/ptp_hyperv`, настройка chrony.
- https://support.microsoft.com/en-us/topic/windows-secure-boot-certificate-expiration-and-ca-updates-7ff40d33-95dc-4c3c-8725-a9b95457578e — истечение сертификатов Secure Boot 2011 года в 2026 году.
- https://learn.microsoft.com/en-us/windows/wsl/wsl-config , …/wsl/networking , …/wsl/systemd — параметры WSL2, сеть, systemd.
- https://knowledge.broadcom.com/external/article?legacyId=2073803 — рекомендация VMware использовать open-vm-tools из дистрибутива.
- https://www.virtualbox.org/manual/topics/networkingdetails.html , …/guestadditions.html , …/storage.html , https://www.virtualbox.org/manual/ch12.html — режимы сети и проброс портов, Guest Additions, кэш ввода-вывода хоста, игнорирование FLUSH.
- https://pve.proxmox.com/wiki/Qemu-guest-agent , https://pve.proxmox.com/wiki/USB_Devices_in_Virtual_Machines — агент QEMU и проброс USB.
- https://github.com/dorssel/usbipd-win — USB/IP-сервер для Windows.

Добавлено при независимой вычитке 10.10.2026 (всё прочитано напрямую):

- https://ubuntu.com/kernel/lifecycle — ядра GA/HWE по релизам (5.4 / 5.15 / 6.8; HWE 24.04.4 — 6.17, 24.04.5 — 7.0; 25.10 — 6.17; 26.04 — 7.0), «Server installations will default to the GA kernel».
- https://releases.ubuntu.com/24.04/ , https://releases.ubuntu.com/26.04/ — имена, размеры и даты сборки ISO 24.04.5 и 26.04.1.
- https://documentation.ubuntu.com/release-notes/24.04/ и …/24.04/5/ — needrestart «systematically restart services», сокет-активация OpenSSH с 22.10, Netplan 1.0, cloud-init 24.1.3; исправление с ключами Microsoft 2023 в 24.04.5.
- https://documentation.ubuntu.com/release-notes/26.04/ , …/26.04/1/ , https://documentation.ubuntu.com/release-notes/26.10/ и …/26.10/schedule/ — требования 26.04 (1,5 ГБ ОЗУ / 4 ГБ диска), состав 26.04.1, кодовое имя и график 26.10 (бета 24.09.2026, релиз 15.10.2026).
- https://ubuntu.com/server/docs/how-to/security/openssh-server/ — `Include /etc/ssh/sshd_config.d/*.conf`, имя службы `ssh.service`, `sshd -t`.
- https://canonical-subiquity.readthedocs-hosted.com/en/latest/intro-to-autoinstall.html — отличия autoinstall от preseed.
- https://github.com/canonical/subiquity — исходный код установщика: `subiquity/models/network.py` (ветка main и тег 24.04.1: куда пишется сетевая конфигурация — `90-installer-network.cfg` → `50-cloud-init.yaml` либо `00-installer-config.yaml`), `subiquity/models/subiquity.py` (шаблон `/etc/hosts` с `127.0.1.1`, `preserve_hostname`, автоматическое создание `/etc/cloud/cloud-init.disabled`, `99-installer.cfg`).
- https://github.com/liske/needrestart (файл `ex/needrestart.conf`) — параметры `$nrconf{restart}`, `$nrconf{override_rc}`, каталог `conf.d`.
- https://packages.ubuntu.com/noble/amd64/linux-cloud-tools-common/filelist , https://packages.ubuntu.com/resolute/amd64/linux-cloud-tools-common/filelist , https://packages.ubuntu.com/noble/amd64/linux-tools-common/filelist и поиск по содержимому пакетов (`vhci-hcd.ko`) — юниты и бинарники демонов Hyper-V, `lsvmbus`, обёртка `usbip`, пакет с модулем `vhci-hcd`.
- https://learn.microsoft.com/en-us/powershell/module/hyper-v/set-vm — параметры и допустимые значения `Set-VM`.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/supported-ubuntu-virtual-machines-on-hyper-v (ред. от 16.02.2026) — перечитана: в таблице 16.04–24.04, Ubuntu 26.04 нет; примечания 1–12.
- https://support.microsoft.com/en-us/topic/secure-boot-certificate-updates-guidance-for-it-professionals-and-organizations-e2b43f9f-b424-42df-bc6a-8476db65ab2f — раздел о виртуальных средах, закрытая проблема Event ID 1795 на ВМ Hyper-V.
- https://techdocs.broadcom.com/us/en/vmware-cis/desktop-hypervisors/workstation-pro/26H1/release-notes.html (и …/vmware-workstation-pro-26h1-release-notes.html) — 26H1 от 14.05.2026, сборка 25388281, бесплатность, Ubuntu 26.04 как гость; наличие 26H1u1.
- https://www.virtualbox.org/manual/topics/vboxmanage.html , …/topics/Introduction.html , https://www.virtualbox.org/wiki/Changelog-7.0 — синтаксис опций 7.x, ограничение `--resize`, состав Extension Pack, USB EHCI/xHCI в базовом пакете.
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux — перечитана: Ubuntu 22.04/24.04/25.10/26.04 (x86-64), каталог `/var/lib/pgpro/std-17/data`, служба `postgrespro-std-17`, `/opt/pgpro/std-17/bin`.
- https://www.postgresql.org/docs/current/backup-file.html — перечитана (текущая версия документации — PostgreSQL 18).
- https://en.wikipedia.org/wiki/VMware_Workstation — вторичный источник: хронология версий 17.5 – 26H1u1.

Сообщество и практика:

- https://infostart.ru/1c/articles/71927/ , https://infostart.ru/1c/articles/99580/ — ключевые параметры программной лицензии и правила их сравнения (пересказ документации; прочитаны через поисковую выдачу).
- https://forum.infostart.ru/forum86/topic252925/ , https://forum.infostart.ru/forum86/topic334315/ , https://forum.infostart.ru/forum86/topic324281/ — случаи потери программной лицензии в ВМ.
- https://forum.infostart.ru/forum86/topic320362/ — драйвер HASP `aksusbd` 10.11 на Ubuntu 24.04.
- https://forum.infostart.ru/forum86/topic213688/ , https://habr.com/ru/articles/168189/ — HASP и Hyper-V, USB-over-IP.
- https://nickvsnetworking.com/ubuntu-cloned-vms-getting-duplicate-ips-and-the-mas-the-same/ — одинаковые адреса DHCP у клонов из-за machine-id.
- https://discourse.ubuntu.com/t/netplan-configuration-to-disable-dhcp-is-overwritten/73196 — перезапись netplan cloud-init в 24.04.
- https://www.omgubuntu.co.uk/2025/06/ubuntu-chrony-nts-default-25-10 , https://linuxiac.com/ubuntu-26-10-stonking-stingray-officially-announced-for-october-15-release/ — chrony по умолчанию; график 26.10.

Не удалось прочитать ни автору, ни рецензенту (страницы ИТС отдаются инструменту в нечитаемой кодировке либо требуют входа; **открыть в браузере и сверить отмеченные ⚠ места** — в первую очередь раздел 8):

- https://its.1c.ru/db/v8327doc/bookmark/adm/TI000000309 (текст главы — https://its.1c.ru/db/v8327doc/content/109/hdoc ; та же закладка в `v85doc`) — руководство администратора, глава 10 «Защита от несанкционированного использования: особенности и настройка»: точный перечень ключевых параметров программной лицензии, правила их сравнения (удаление/добавление устройств, ОЗУ, периодичность проверки), особенности Linux и виртуальных сред, каталоги файлов `*.lic` в Linux, ключи HASP (серверные/сетевые, порты менеджера лицензий).
- https://its.1c.ru/db/v8327doc/content/117/hdoc — глава «Требования к аппаратуре и программному обеспечению» для 8.3.27 (и аналог для 8.5): список дистрибутивов Linux по версии платформы, есть ли Ubuntu 26.04.
- https://its.1c.ru/db/content/metod8dev/src/developers/scalability/instructions/i8105953.htm — «Установка Платформы „1С:Предприятие“ в ОС Linux»: подготовка имени хоста и `/etc/hosts`, драйвер HASP. При вычитке со страницы удалось прочитать только команды и латиницу (`hostname -f`, формат строки hosts, `haspd`, `srv1cv83`, 8.3.13) — русский текст пояснений нечитаем; инструкция написана для старых версий (юнит `srv1cv83`, каталог `/opt/1C/v8.3/x86_64`), актуальную для 8.3.27/8.5 нужно искать в браузере.
- https://infostart.ru/1c/articles/71927/ и https://infostart.ru/1c/articles/99580/ — при вычитке отвечали HTTP 429; пересказ перечня ключевых параметров остаётся непроверенным.
- Руководство VMware Workstation Pro: тема об автозапуске ВМ («Configure Auto Start VMs») и статья базы знаний о параметре `usb.autoConnect.device0` — точные адреса не найдены.

Ограничения (автор): лимит поисковых запросов был исчерпан на середине работы, поэтому часть сведений проверена только прямым чтением известных страниц или оставлена с пометкой ⚠.

Итог независимой вычитки 10.10.2026 (рецензент; веб-поиск был недоступен — исчерпан общий лимит, проверка велась прямым чтением первоисточников по известным адресам):

- **Подтверждено и снята пометка ⚠**: ядра GA/HWE и то, что сервер по умолчанию ставит GA-ядро; даты и образы 24.04.5 / 26.04.1; версии и бесплатность VMware Workstation Pro; имена юнитов и состав пакета демонов Hyper-V; расположение модуля `vhci-hcd` и обёртки `usbip`; автоперезапуск служб `needrestart` в 24.04+; ограничение `VBoxManage modifymedium --resize`; USB 2/3 в базовом пакете VirtualBox 7; параметры WSL; строки chrony для Hyper-V; список ОС платформы 1С и СУБД на v8.1c.ru; 12 ядер ПРОФ; правила `sizing-policy`; порядок поиска autoinstall.
- **Исправлено**: `lsvmbus` находится в `linux-cloud-tools-common`, а не в `linux-tools-*`; в 26.04 демон копирования файлов называется `hv_fcopy_uio_daemon`; файл сети от установщика — не всегда `50-cloud-init.yaml` (зависит от версии установщика); бета 26.10 — 24.09.2026, а не 01.10; HWE-ядро 24.04.5 — 7.0; имя службы SSH и псевдоним `sshd`; команды USB/IP привязаны к `uname -r`; правило брандмауэра PowerShell с диапазоном портов.
- **Осталось под вопросом (⚠ в тексте)**: всё содержимое раздела 8 о ключевых параметрах лицензии 1С и правилах их сравнения; локальность серверного ключа HASP и путь `/var/1C/licenses` (общеизвестная практика без прочитанного первоисточника); влияние смены сертификатов Secure Boot на шаблон Hyper-V; пункт меню автозапуска и `usb.autoConnect` в VMware; какой вариант сетевых файлов даёт конкретный ISO; сохранение сокет-активации SSH в 26.04; MAC-адрес WSL2; ядро 26.10; таблица ресурсов ВМ и пороги fio (оценки автора без источника).

