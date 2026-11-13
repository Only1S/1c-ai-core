# Тюнинг ядра и лимитов, huge pages, локали, время, шрифты, безопасность и сертификаты (Ubuntu Server под 1С + PostgreSQL)

> Область: подготовка и сопровождение ОС Ubuntu Server для сервера «1С:Предприятие 8» и PostgreSQL — sysctl, лимиты, THP/huge pages, энергосбережение CPU, tuned, GRUB, время (timesyncd/chrony), локали и glibc, шрифты, AppArmor/обновления/fail2ban/auditd/lynis, OpenSSL/CA/certbot.
> Версии: Ubuntu 22.04 LTS (ядро 5.15, glibc 2.35, systemd 249), 24.04 LTS (ядро 6.8, glibc 2.39, systemd 255), 26.04 LTS (ядро 7.0, glibc 2.43, systemd 259); PostgreSQL 14–18 (актуальные минорные на 10.2026 по таблице postgresql.org/support/versioning: 18.6 / 17.11 / 16.15 / 15.19 / 14.24; поддержка 14-й ветки заканчивается 12.11.2026; PostgreSQL 19 ещё не вышел: 24.09.2026 выпущена Beta 4, в её анонсе сказано лишь, что RC ожидается «в начале октября», а GA «возможно, тоже в октябре» — точных дат PGDG не называл); платформа 1С 8.3.x / 8.5.x.
> Актуальность: 2026-10-10 (файл прошёл независимую фактчек-рецензию 2026-10-10; что проверено и чем — см. раздел «Источники», что осталось непроверенным — пометки «⚠»)

Условные обозначения:

- **[1С]** — официальная рекомендация фирмы «1С» (ИТС); **[PGPro]** — документация Postgres Professional; **[PG]** — документация PostgreSQL; **[Canonical]** — документация Ubuntu; **[ядро]** — документация kernel.org; **[практика]** — практика сообщества (EDB, Percona, tuned, статьи), не официальное требование.
- **⚠ не подтверждено** — утверждение написано по памяти/по косвенным данным, первоисточником в этой сессии не проверено. Перед применением проверить на живой системе.

---

## Кратко

1. Постоянные параметры ядра кладите в **`/etc/sysctl.d/90-имя.conf`** и применяйте `sudo sysctl --system`. В `/etc/sysctl.conf` не пишите: `systemd-sysctl` при загрузке читает только каталоги `sysctl.d`. В Ubuntu 22.04/24.04 `/etc/sysctl.conf` подхватывается при загрузке лишь благодаря симлинку `/etc/sysctl.d/99-sysctl.conf` (из пакета `systemd`), а в **Ubuntu 26.04 ни файла `/etc/sysctl.conf`, ни этого симлинка в пакетах `procps`/`systemd` уже нет** (проверено по спискам файлов пакетов) — созданный вручную `/etc/sysctl.conf` там применится только при ручном `sysctl --system`/`sysctl -p`, но не при загрузке.
2. Официально [1С] и [PGPro] для сервера СУБД требуют немногого: **отключить энергосбережение** (режим максимальной производительности), **отключить Hyper-Threading**, не выгружать разделяемую память в swap, русская локаль до `initdb`. Конкретных чисел sysctl в открытых материалах 1С/PGPro нет — всё остальное ниже это [PG] и [практика].
3. Разумный минимум sysctl для ВМ с 1С + PostgreSQL: `vm.swappiness=10` (1 для выделенной СУБД), `vm.dirty_background_bytes=67108864`, `vm.dirty_bytes=536870912`, при необходимости `vm.nr_hugepages` по расчёту. Остальное — по умолчанию.
4. `kernel.shmmax`, `kernel.shmall`, `kernel.sem`, `fs.file-max`, `fs.aio-max-nr` на современных ядрах **трогать не нужно**: значения по умолчанию давно огромные, а PostgreSQL на Linux использует `mmap` и POSIX-семафоры. Старые инструкции с `kernel.shmmax=...` и `kernel.sem=250 32000 100 128` устарели и могут только ухудшить.
5. `kernel.sched_migration_cost_ns`, `kernel.sched_min_granularity_ns`, `kernel.sched_wakeup_granularity_ns`, `kernel.sched_latency_ns` **не существуют как sysctl с ядра 5.13** (Ubuntu 22.04+): перенесены в debugfs, а с 6.6 (EEVDF) частично удалены/переименованы. Из планировщика в sysctl осталось `kernel.sched_autogroup_enabled`, `kernel.numa_balancing` и RT-параметры.
6. `/etc/security/limits.conf` действует **только на PAM-сессии** (ssh, login, su, sudo, cron — там, где в `/etc/pam.d/` подключён `pam_limits.so`), а **не на службы systemd**. Для PostgreSQL и сервера 1С лимиты задаются в юните: `sudo systemctl edit <юнит>` → `LimitNOFILE=`, `LimitNPROC=`, `LimitCORE=`, `TasksMax=`. Фактические значения: `cat /proc/<pid>/limits`.
7. Значения systemd по умолчанию: `LimitNOFILE=1024:524288`, `TasksMax=15%`, `LimitMEMLOCK=8M` (systemd 255/259, т. е. Ubuntu 24.04/26.04; в man-странице systemd 249 из 22.04 значение по умолчанию не задано). **`LimitCORE` в Debian/Ubuntu — `0:infinity`** (мягкий 0, жёсткий без ограничения): апстримный systemd ставит `infinity`, но в сборке Debian/Ubuntu это переопределено (`DefaultLimitCORE=0:infinity`), поэтому core-дампы служб по умолчанию **не пишутся**, пока в юните не задан `LimitCORE=infinity`.
8. **Transparent Huge Pages** для СУБД [PG] «discouraged». Проверка: `cat /sys/kernel/mm/transparent_hugepage/enabled`. Отключение навсегда: `transparent_hugepage=never` в `GRUB_CMDLINE_LINUX_DEFAULT` + `sudo update-grub` + перезагрузка (или systemd-юнит, или tuned).
9. **Обычные huge pages** для `shared_buffers`: остановить PostgreSQL → `postgres -D ... -C shared_memory_size_in_huge_pages` → записать число в `vm.nr_hugepages` → `huge_pages = try` (по умолчанию) или `on`. Проверка: `grep -i huge /proc/meminfo`, в PG 17+ `SHOW huge_pages_status;`. **Для Ubuntu 26.04 (ядро 7.0) это не просто оптимизация**: в release notes 26.04 [Canonical] описана известная проблема — изменение в Linux 7.0 может давать заметную деградацию пропускной способности и задержек PostgreSQL, а системы с huge pages ей не подвержены; Canonical прямо рекомендует включить huge pages и поставить `huge_pages = on` (раздел 6.4).
10. В ВМ у гостя обычно нет драйвера cpufreq — `cpupower` бесполезен; режим «Высокая производительность» включается **на хосте** (схема электропитания Windows / BIOS). На «железе»: `cpupower frequency-set -g performance` или `tuned-adm profile throughput-performance`.
11. Время: `timedatectl` (статус, `set-timezone`, `set-ntp`). До Ubuntu 25.04 включительно клиент времени по умолчанию — **systemd-timesyncd**, с **25.10 и в 26.04 — chrony с NTS** (нужен исходящий **TCP 4460** помимо UDP 123; если он закрыт — время не синхронизируется). Это касается **новых установок**: при обновлении с 24.04 остаётся `systemd-timesyncd`, а chrony сам не ставится (перейти: `sudo apt-mark auto systemd-timesyncd && sudo apt install chrony`).
12. Для Kerberos расхождение часов должно быть меньше 5 минут; для лицензирования платформы **8.5.4+** [1С, ИТС № 6041] — не больше **20 минут** между компьютером Менеджера Лицензий и компьютерами клиентских/серверных приложений; для кластера 1С, журналов, регламентных заданий и TLS время на всех узлах должно совпадать.
13. Локаль **`ru_RU.UTF-8` должна существовать в ОС до `initdb`/`pg_createcluster`** и до установки сервера 1С: `sudo locale-gen ru_RU.UTF-8`, проверка `locale -a | grep ru_RU`. `LC_COLLATE`/`LC_CTYPE` базы после создания изменить нельзя.
14. Пакет `postgresql` в Ubuntu (и пакеты PGDG — общий `postgresql-common`) при установке сам создаёт кластер `main` **с системной локалью по умолчанию** — той, что записана в `/etc/default/locale` (`/etc/locale.conf`), а **не** с локалью вашего сеанса: скрипт пакета сбрасывает переменные окружения и читает системные значения, при их отсутствии берёт `C.UTF-8`. Поэтому `export LANG=ru_RU.UTF-8` перед `apt install` не помогает — нужен `sudo update-locale LANG=ru_RU.UTF-8` **до** установки либо `create_main_cluster = false` в `/etc/postgresql-common/createcluster.conf`. Если кластер уже создан в `en_US.UTF-8`/`C.UTF-8` — пересоздать: `pg_dropcluster --stop NN main && pg_createcluster --locale ru_RU.UTF-8 NN main --start`.
15. Смена мажорной версии ОС (например, 22.04 → 24.04 → 26.04) меняет glibc (2.35 → 2.39 → 2.43) и ICU, а значит потенциально порядок сортировки: индексы по текстовым полям могут стать некорректными. После такого обновления — `REINDEX` всех баз + `ALTER DATABASE ... REFRESH COLLATION VERSION`, либо перенос через dump/restore (для 1С — через `.dt` или `pg_dump`).
16. Шрифты для сервера 1С [1С]: `sudo apt-get -y install ttf-mscorefonts-installer && sudo fc-cache -fv`. Без диалога EULA: `echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | sudo debconf-set-selections`.
17. AppArmor: `sudo aa-status`; блокировки видны как `apparmor="DENIED"` в `journalctl -k` / `dmesg` (а при работающем auditd — в `/var/log/audit/audit.log`). Режимы профиля: `aa-complain` / `aa-enforce`.
18. `unattended-upgrades` в Ubuntu включён по умолчанию (только security), а с 24.04 `needrestart` **сам перезапускает службы** после обновления библиотек — для PostgreSQL и сервера 1С это надо контролировать (исключения в `/etc/needrestart/conf.d/`, `apt-mark hold`).
19. Свой корневой сертификат: скопировать **PEM с расширением `.crt`** в `/usr/local/share/ca-certificates/` → `sudo update-ca-certificates`. Удаление: удалить файл → `sudo update-ca-certificates --fresh`.
20. Самоподписанный сертификат с SAN одной командой: `openssl req -x509 -newkey rsa:2048 -noenc -keyout k.key -out c.crt -days 825 -subj "/CN=host" -addext "subjectAltName=DNS:host,IP:10.0.0.5"`. Let's Encrypt: `sudo snap install --classic certbot`, `sudo ln -s /snap/bin/certbot /usr/local/bin/certbot`, `sudo certbot --apache`; срок сертификатов сокращается: с 10.02.2027 — 64 дня, с 16.02.2028 — 45 дней (автопродление обязательно).
21. Core-дампы сервера 1С в Linux настраиваются средствами ОС, а не `logcfg.xml` [1С]. Документация 1С описывает `limits.conf` + `kernel.core_pattern` в `/etc/sysctl.conf`; для службы systemd на Ubuntu нужны `LimitCORE=infinity` в drop-in юнита и шаблон в `/etc/sysctl.d/` (раздел 5.3).
22. Корневые сертификаты для защищённых соединений платформа 1С 8.3.20+ (режим совместимости 8.3.8 и новее) берёт сначала из своего файла `cacertnx.pem`, затем из хранилища ОС; в режиме совместимости 8.3.7 и старее — только из `cacert.pem` [1С] (раздел 12.8).
23. Чтобы лимиты сервера 1С не терялись при обновлении платформы (в имени юнита — номер версии), кладите их в drop-in по префиксу: `/etc/systemd/system/srv1cv8-.service.d/limits.conf` (раздел 5.3). Профили tuned: в 22.04/24.04 — `/etc/tuned/<имя>/`, в 26.04 — `/etc/tuned/profiles/<имя>/`.
24. Строковые поля баз 1С (`mchar`/`mvarchar`) сравниваются через ICU [PGPro], и предупреждений PostgreSQL о смене версии сортировки для них ждать не стоит: после смены ОС/сборки PostgreSQL перестраивайте индексы безусловно или переносите базы логически (раздел 9.4).

---

## 1. Что различается между релизами Ubuntu (важно для этой темы)

| Что | 22.04 LTS (jammy) | 24.04 LTS (noble) | 26.04 LTS (resolute) |
|---|---|---|---|
| Ядро GA | 5.15 | 6.8 | 7.0 |
| glibc | 2.35 | 2.39 | 2.43 |
| systemd | 249 | 255 | 259 |
| Клиент времени по умолчанию | systemd-timesyncd | systemd-timesyncd | **chrony + NTS** (с 25.10; только новые установки — при обновлении остаётся timesyncd) |
| Файл системной локали (`update-locale`) | `/etc/default/locale` | `/etc/locale.conf` (по man-странице noble) | `/etc/locale.conf` |
| cgroup | v2 (v1 доступен) | v2 (v1 доступен) | **только v2** (v1 удалён) |
| sudo | sudo | sudo | **sudo-rs** (классический — `sudo.ws`) |
| coreutils | GNU | GNU | **rust-coreutils** (GNU-версии с префиксом `gnu`, кроме `cp`/`mv`/`rm`, которые остались GNU) |
| needrestart | интерактивно спрашивает; в неинтерактивном режиме (unattended-upgrades) — только список | **сам перезапускает службы** | сам перезапускает службы |
| PostgreSQL в архиве Ubuntu | 14 (14.2 на момент выпуска) | 16 (16.2) | 18 |
| OpenSSH | 8.9p1 | 9.6p1 | 10.2p1 |
| OpenSSL (пакет `openssl`) | 3.0.2 | 3.0.13 | 3.5.x (LTS-ветка: в архиве 3.5.5-1ubuntu3.x, в release notes — «обновлён до 3.5.6») |
| chrony (пакет) | 4.2 | 4.5 | 4.8 |
| initramfs | initramfs-tools | initramfs-tools | dracut (initramfs-tools поддерживается) |
| Ограничение unprivileged user namespaces через AppArmor | нет | **есть** | есть |
| `/etc/sysctl.conf` (пакет `procps`) | есть | есть | **нет** |
| Симлинк `/etc/sysctl.d/99-sysctl.conf → ../sysctl.conf` (пакет `systemd`) | есть | есть | **нет** |
| Поставляемые Ubuntu sysctl-файлы (`procps`) | `/etc/sysctl.d/10-*.conf` | `/etc/sysctl.d/10-*.conf` | `/usr/lib/sysctl.d/55-*.conf` (+ новый `55-bufferbloat.conf`) |
| `vm.max_map_count` | 65530 (умолчание ядра) | **1048576** (`/etc/sysctl.d/10-map-count.conf`) | 1048576 (`/usr/lib/sysctl.d/55-map-count.conf`) |
| `DefaultLimitMEMLOCK` systemd | не задан (наследуется) | 8M | 8M |
| Каталоги профилей tuned | `/usr/lib/tuned/<имя>/`, `/etc/tuned/<имя>/` | те же (плоская раскладка) | **`/usr/lib/tuned/profiles/<имя>/`, `/etc/tuned/profiles/<имя>/`** |
| fail2ban: `jail.d/defaults-debian.conf` | только `[sshd] enabled = true` (⚠ для 0.11.2 по памяти) | + `banaction = nftables`, для `sshd` `backend = systemd` (с пакета 1.0.2-3) | то же |
| THP по умолчанию (`/sys/kernel/mm/transparent_hugepage/enabled`) | `madvise` (с 17.10 — по рассылке kernel-team Ubuntu, см. раздел о THP; для этого ядра — по практике) | `madvise` (с 17.10 — по рассылке kernel-team Ubuntu, см. раздел о THP; для этого ядра — по практике) | ⚠ не проверено |

Источники строк: release notes 22.04, 24.04 и 26.04 (ядро, glibc, systemd, needrestart, chrony, sudo-rs, PostgreSQL, OpenSSH, OpenSSL), packages.ubuntu.com (версии `openssl`, списки файлов пакетов `procps`, `systemd`, `tuned` для jammy/noble/resolute), changelog пакетов `procps` (2:4.0.4-4ubuntu2: `vm.max_map_count=1048576`, LP: #2057792) и `fail2ban`, man-страницы `update-locale` и `systemd-system.conf` для jammy/noble/resolute. Значения для 22.04 (ядро 5.15, glibc 2.35, systemd 249.11, OpenSSL 3.0.2, PostgreSQL 14.2, chrony 4.2) подтверждены release notes 22.04; OpenSSH 8.9p1 — по версии пакета (в тексте release notes номер не назван).

Следствия:

- Параметры планировщика `kernel.sched_*_ns` отсутствуют как sysctl **во всех трёх** релизах (перенос в debugfs случился в 5.13).
- При переходе 24.04 → 26.04 проверьте синхронизацию времени: chrony становится клиентом по умолчанию только **для новых установок**; на обновлённой системе остаётся `systemd-timesyncd`, и release notes 26.04 предлагают перейти вручную: `sudo apt-mark auto systemd-timesyncd && sudo apt install chrony` [Canonical]. В свежей установке 26.04 работает chrony с NTS.
- Скрипты, рассчитанные на GNU coreutils и классический sudo, на 26.04 нужно перепроверить. GNU-версии утилит вызываются с префиксом `gnu` (пример из release notes — `gnuls`; соответственно `gnusort`), классический sudo — `sudo.ws`.
- **PostgreSQL на ядре 7.0 (26.04)**: в release notes 26.04 («Changes since 25.10», известные проблемы) сказано, что изменение в Linux 7.0 может вызывать существенную деградацию пропускной способности и задержек PostgreSQL; системы с huge pages не затронуты, рекомендация Canonical — включить huge pages и `huge_pages = on` (раздел 6.4).
- Унаследованные конфиги с правками в `/etc/sysctl.conf`: после чистой установки 26.04 такого файла нет, а перенесённый вручную файл при загрузке не применится — переносите строки в `/etc/sysctl.d/90-*.conf`.
- Поддерживает ли конкретная сборка платформы 1С Ubuntu 26.04 — см. статью базы знаний про установку 1С (в этой статье не проверялось).

---

## 2. sysctl: чтение, запись, постоянные настройки

### 2.1. Чтение и временная запись

```bash
sysctl -a                         # все параметры (ключ = значение)
sysctl vm.swappiness              # один параметр
sysctl -n vm.swappiness           # только значение (удобно в скриптах)
sysctl -a -r '^vm\.dirty'         # по регулярному выражению (-r / --pattern)
cat /proc/sys/vm/swappiness       # то же через procfs: точки в имени = слэши в пути

sudo sysctl -w vm.swappiness=10   # записать до перезагрузки
echo 10 | sudo tee /proc/sys/vm/swappiness   # эквивалент
```

Ключевые опции `sysctl` (procps 4.0.4 в 24.04/26.04): `-a/--all`, `-n/--values`, `-N/--names`, `-w/--write`, `-p[ФАЙЛ]/--load` (по умолчанию `/etc/sysctl.conf`), `--system` (все системные файлы), `-e/--ignore` (не ругаться на неизвестные ключи), `-q/--quiet`, `-r/--pattern`.

### 2.2. Постоянные настройки

Каталоги, которые читает `sysctl --system`, в порядке приоритета [man sysctl(8)]:

1. `/etc/sysctl.d/*.conf`
2. `/run/sysctl.d/*.conf`
3. `/usr/local/lib/sysctl.d/*.conf`
4. `/usr/lib/sysctl.d/*.conf`
5. `/lib/sysctl.d/*.conf`
6. `/etc/sysctl.conf`

Правила:

- Файлы сортируются **по имени лексикографически независимо от каталога**; если файл с тем же именем есть в каталоге выше по списку, одноимённый файл ниже игнорируется (так «маскируют» поставляемые файлы).
- Один и тот же ключ в нескольких файлах — побеждает **последнее присваивание** (файл с «бо́льшим» именем). При ручном `sysctl --system` файл `/etc/sysctl.conf` обрабатывается **последним** и перекрывает `sysctl.d` — забытая в нём строка даёт разное поведение «после загрузки» и «после `sysctl --system`». Держите `/etc/sysctl.conf` пустым (только комментарии).
- Рекомендация systemd [man sysctl.d(5)]: в `/usr/lib` — префиксы 10–40, в `/etc` и `/run` — префиксы **60–90**.
- Чтобы отключить файл, поставляемый в `/usr/lib/sysctl.d/` (в Ubuntu 26.04 это `55-*.conf` пакета `procps`, `50-pid-max.conf` пакета `systemd`): `sudo ln -s /dev/null /etc/sysctl.d/55-имя.conf` (имя должно совпадать). В Ubuntu 22.04/24.04 файлы Ubuntu лежат прямо в `/etc/sysctl.d/10-*.conf` (это conffile-ы пакета `procps`) — их не маскируют, а переопределяют своим файлом с бо́льшим номером.
- Что именно Ubuntu задаёт «из коробки» (имена файлов — по спискам файлов пакета `procps`; префикс `10-` в 22.04/24.04 и `55-` в 26.04): `console-messages` (`kernel.printk`), `ipv6-privacy`, `kernel-hardening` (`kernel.kptr_restrict` и др.), `magic-sysrq` (`kernel.sysrq`), `network-security` (`rp_filter`), `ptrace` (`kernel.yama.ptrace_scope` — из-за него `gdb -p`/`strace -p` к чужому процессу, например `rphost`, работает только от root), `zeropage` (`vm.mmap_min_addr`), `map-count` (`vm.max_map_count`, с 24.04), `bufferbloat` (только 26.04; содержимое — ⚠ не проверено). Точные значения: `systemd-analyze cat-config sysctl.d`.
- Формат строки: `ключ = значение`; комментарии `#` и `;`; разделитель в имени — `.` или `/`. Ведущий `-` перед присваиванием (`-kernel.foo = 1`) — не считать ошибкой, если ключ не удалось установить.
- При загрузке параметры применяет `systemd-sysctl.service`; он читает **только каталоги `sysctl.d`**. В Ubuntu 22.04 и 24.04 `/etc/sysctl.conf` (файл пакета `procps`) подхватывается через симлинк `/etc/sysctl.d/99-sysctl.conf` (файл пакета `systemd`) — подтверждено списками файлов пакетов jammy/noble; так как имя начинается с `99-`, строки из `sysctl.conf` при загрузке применяются **после** ваших `90-*.conf` и перекрывают их. В **Ubuntu 26.04** пакет `procps` (2:4.0.4-9ubuntu1) больше не содержит `/etc/sysctl.conf`, а пакет `systemd` — симлинка `99-sysctl.conf` (подтверждено списками файлов пакетов resolute); при этом `sysctl --system` и `sysctl -p` по-прежнему читают `/etc/sysctl.conf`, если его создать [man sysctl(8), resolute]. На системе, обновлённой с 24.04, старые файл и симлинк могут остаться — проверьте `ls -l /etc/sysctl.conf /etc/sysctl.d/`. **Вывод: всегда используйте свой файл в `/etc/sysctl.d/`.**
- Следствие для инструкций 1С: в документации платформы (приложение 3, раздел о дампах в Linux) шаблон дампов предлагается писать в `/etc/sysctl.conf` и применять `sysctl -p` — документация написана в расчёте на Fedora Core 4. На Ubuntu кладите эту строку в `/etc/sysctl.d/` (раздел 5.3).
- Параметры модулей, загружаемых позже (`net.bridge.*`, `net.netfilter.*`), при загрузке не применятся — нужен `modules-load.d` или udev-правило [man sysctl.d(5)].

```bash
# создать файл и применить
sudo nano /etc/sysctl.d/90-1c-postgres.conf
sudo sysctl --system                               # применить всё, печатает "* Applying <файл> ..."
sudo sysctl -p /etc/sysctl.d/90-1c-postgres.conf   # применить только один файл

# проверка
sysctl vm.swappiness vm.dirty_bytes vm.dirty_background_bytes
systemd-analyze cat-config sysctl.d                # итоговая «склейка» всех файлов sysctl.d
sudo systemctl restart systemd-sysctl              # то же, что делает загрузка
```

---

## 3. Параметры sysctl для сервера БД и 1С

### 3.1. Сводная таблица

| Параметр | По умолчанию (ядро / Ubuntu) | Что рекомендовать | Кто рекомендует |
|---|---|---|---|
| `vm.swappiness` | 60 (диапазон 0–200) | 1–10 | [практика]: EDB 10, tuned `throughput-performance` 10 и tuned `postgresql` 3 (оба значения сверены с репозиторием tuned), tuned `virtual-guest` 30, Percona 1; Tantor для 1С 1 (⚠ по выдаче поиска — страница документации Tantor с настройками ОС при рецензии не открылась) |
| `vm.overcommit_memory` | 0 | 2 — только на **выделенном** сервере PostgreSQL; на общем с 1С — оставить 0 | [PG] (2 + подбор ratio); [практика] |
| `vm.overcommit_ratio` | 50 | подбирать, когда `overcommit_memory=2` (обычно 80–95) | [PG] «при необходимости» |
| `vm.dirty_background_ratio` / `vm.dirty_ratio` | 10 / 20 (в docs.kernel.org числа не приведены; это общеизвестные значения из исходников ядра `mm/page-writeback.c`, их же называет комментарий профиля tuned «system default is 20%» — сверяйте `sysctl vm.dirty_ratio vm.dirty_background_ratio`) | заменить на `*_bytes` | [практика] |
| `vm.dirty_background_bytes` / `vm.dirty_bytes` | 0 / 0 (не используются) | 64 МБ / 512 МБ (`67108864` / `536870912`) | [практика]: профиль tuned `postgresql` |
| `vm.dirty_expire_centisecs` / `vm.dirty_writeback_centisecs` | 3000 / 500 (из исходников ядра; в docs.kernel.org числа не приведены — сверяйте `sysctl`) | обычно не трогать (EDB: 500 / 250) | [практика] |
| `vm.nr_hugepages` | 0 | по расчёту от `shared_buffers` (раздел 6) | [PG]; для Ubuntu 26.04 — [Canonical] |
| `vm.max_map_count` | 65530 (ядро [ядро]); в Ubuntu 24.04+ **1048576** (файл пакета `procps`, changelog 2:4.0.4-4ubuntu2) | не трогать | — |
| `kernel.shmmax`, `kernel.shmall` | практически без ограничений: с ядра 3.16 оба равны `ULONG_MAX − 2^24` = 18446744073692774399 [man shmget(2)]; до 3.16 `shmmax` был всего 32 МиБ — отсюда старые инструкции | **не задавать** | [PG]: значения по умолчанию достаточны |
| `kernel.sem` (`SEMMSL SEMMNS SEMOPM SEMMNI`) | `32000 1024000000 500 32000` с ядра 3.19 [man semget(2), semop(2)]: SEMMSL 32000 (было 250), SEMOPM 500 (было 32), SEMMNI 32000 (было 128); SEMMNS = SEMMSL × SEMMNI | **не задавать** | [PG]: «System V semaphores are not used on this platform» |
| `fs.file-max` | очень большое (systemd поднимает при загрузке до максимума; в сборке Debian/Ubuntu отключён только подъём `fs.nr_open`) | не задавать | [PG] упоминает как возможность |
| `fs.aio-max-nr` | 65536 (из исходников ядра `fs/aio.c`; подтверждено 11.10.2026: в `fs/aio.c` стоит `aio_max_nr = 0x10000`, то есть 65536; ранее: первоисточник в сессии не открывался — сверяйте `sysctl fs.aio-max-nr`) | не задавать (PostgreSQL не использует libaio) | — |
| `net.core.somaxconn` | 4096 (до ядра 5.4 было 128) | не задавать | [PG] упоминает |
| `net.ipv4.tcp_keepalive_time/intvl/probes` | 7200 / 75 / 9 | 600 / 60 / 5 (или настраивать в PostgreSQL) | [практика] |
| `net.ipv4.ip_local_port_range` | `32768 60999` | не трогать | — |
| `kernel.sched_autogroup_enabled` | 1 | 0 | [практика]: профиль tuned `postgresql` |
| `kernel.numa_balancing`, `vm.zone_reclaim_mode` | 1 (на NUMA) / 0 | 0 / 0 на многосокетном «железе» | [практика] |

### 3.2. Память: swap

**`vm.swappiness`** [ядро]: диапазон 0–200, по умолчанию 60. Определяет относительную «цену» вытеснения анонимной памяти в swap по сравнению со сбросом файлового кеша. При 0 ядро не начинает свопить, пока сумма свободных и файловых страниц не упадёт ниже high watermark зоны.

- Для СУБД большие значения вредны: в swap уходят страницы backend-процессов и `shared_buffers`, появляются непредсказуемые задержки. [PGPro] (приложение «Настройка Postgres Pro для решений 1С») формулирует требование без чисел: отключить подкачку для разделяемой памяти.
- [практика] 10 — умеренно; 1 — «почти не свопить, но не доводить до OOM». Значение 0 на современных ядрах не рекомендуют (выше риск OOM killer).
- Полностью убирать swap не обязательно: небольшой swap (2–8 ГБ) при `swappiness=1..10` служит «подушкой».

```bash
free -h; swapon --show              # есть ли swap и сколько занято
sudo sysctl -w vm.swappiness=10
# кто сидит в swap:
for f in /proc/[0-9]*/status; do awk '/^(Name|VmSwap)/{printf "%s ", $2} END{print ""}' "$f"; done 2>/dev/null | sort -k2 -n | tail
```

### 3.3. Память: overcommit и OOM killer

**`vm.overcommit_memory`** [ядро]:

- `0` (по умолчанию) — эвристика: явно невозможные запросы отклоняются, остальное разрешается;
- `1` — всегда разрешать;
- `2` — строгий учёт: суммарная выделенная виртуальная память не может превысить `CommitLimit`. В режиме 2 `malloc` возвращает ошибку вместо того, чтобы позже пришёл OOM killer.

Формула [ядро, `/proc/meminfo`]:

```text
CommitLimit = (RAM − память под huge pages) × overcommit_ratio / 100 + swap
```

Смотреть: `grep -E 'CommitLimit|Committed_AS' /proc/meminfo`.

[PG] рекомендует `vm.overcommit_memory=2` и подбор `vm.overcommit_ratio`, чтобы OOM killer не убил postmaster. Нюансы:

- **Выделенный сервер PostgreSQL** — можно ставить 2. Пример: 64 ГБ RAM, swap 4 ГБ, huge pages 17 ГБ, `overcommit_ratio=90` → CommitLimit = (64−17)×0,9+4 ≈ 46 ГБ. При `ratio=50` (по умолчанию) было бы всего ≈ 27,5 ГБ — сервер начнёт получать «out of memory» при свободной памяти. Обратите внимание: память под huge pages из расчёта **исключается**.
- **Общий сервер 1С + PostgreSQL** — [практика] оставлять 0: процессы `rphost` резервируют много виртуальной памяти, и строгий режим приводит к отказам выделения в 1С. Защита postmaster достигается через `OOMScoreAdjust`.
- Альтернатива [PG]: понизить `oom_score_adj` postmaster до `-1000` и вернуть дочерним процессам 0 через переменные `PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj`, `PG_OOM_ADJUST_VALUE=0` (без `PG_OOM_ADJUST_FILE` дочерние процессы унаследуют защиту postmaster, что [PG] называет неразумным).
- В Debian/Ubuntu это **уже сделано пакетом `postgresql-common`** (проверено по исходникам версии 278): в юните `postgresql@.service` задан `OOMScoreAdjust=-900`, а `pg_ctlcluster` перед запуском сам записывает `-900` в `/proc/self/oom_score_adj` и выставляет `PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj` (значение `PG_OOM_ADJUST_VALUE` по умолчанию 0) — то есть postmaster защищён, а backend-процессы остаются обычными кандидатами для OOM killer. Проверка: `systemctl show postgresql@17-main -p OOMScoreAdjust`; `cat /proc/$(pgrep -o postgres)/oom_score_adj` (ожидается `-900`), у любого backend — `0`. Для сборок Postgres Pro (свой юнит `postgrespro-*.service`) такая защита тоже есть — Подтверждено 11.10.2026 чтением пакета `postgrespro-1c-16-server` 16.14-1.noble: в `/lib/systemd/system/postgrespro-1c-16.service` заданы `OOMScoreAdjust=-1000`, `Environment=PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj` и `Environment=PG_OOM_ADJUST_VALUE=0` (значение можно переопределить в `/etc/default/postgrespro-1c-16`, который юнит читает как `EnvironmentFile`). Для других редакций и версий смотрите `systemctl cat`.

```bash
# кого убивал OOM killer
sudo journalctl -k | grep -iE 'out of memory|oom-kill|killed process'
# текущая «оценка» процесса
cat /proc/$(pgrep -o postgres)/oom_score_adj
```

### 3.4. Память: сброс «грязных» страниц

[ядро]:

- `vm.dirty_background_ratio` / `vm.dirty_background_bytes` — порог, с которого фоновые flusher-потоки начинают писать на диск;
- `vm.dirty_ratio` / `vm.dirty_bytes` — порог, с которого **сам пишущий процесс** блокируется и пишет синхронно;
- `ratio` считается в процентах от **доступной** памяти (свободная + reclaimable), а не от всей RAM;
- пары `*_ratio` и `*_bytes` взаимоисключающие: запись в одну обнуляет другую (читается как 0);
- минимум для `dirty_bytes` — две страницы.

Зачем менять: при 64–256 ГБ RAM значения 10 % / 20 % — это гигабайты «грязных» данных; при `fsync`/checkpoint PostgreSQL они выливаются на диск разом и дают «полку» на вводе-выводе. Абсолютные значения делают поведение независимым от объёма RAM.

- [практика] профиль tuned `postgresql`: `dirty_background_bytes = 67108864` (64 МБ), `dirty_bytes = 536870912` (512 МБ), с комментарием держать их близкими к размеру write-back кеша RAID-контроллера.
- [практика] EDB (Debian/Ubuntu, 2021): `vm.dirty_ratio=10`, `vm.dirty_background_ratio=3`, `vm.dirty_expire_centisecs=500`, `vm.dirty_writeback_centisecs=250`.
- [практика] Percona: `vm.dirty_background_ratio=5` для нагрузки с интенсивной записью; `dirty_ratio` выше фонового.
- Для быстрых NVMe допустимо больше (256 МБ / 1–2 ГБ). Слишком маленькие значения замедляют массовые загрузки (загрузка `.dt`, реструктуризация).

```bash
grep -E '^(Dirty|Writeback):' /proc/meminfo     # сколько сейчас «грязных» данных
sysctl vm.dirty_background_ratio vm.dirty_ratio vm.dirty_background_bytes vm.dirty_bytes
```

### 3.5. `vm.max_map_count`

[ядро]: максимум областей отображения памяти (mmap) на процесс, по умолчанию 65530. В Ubuntu 24.04 значение поднято до **1048576**: changelog пакета `procps` 2:4.0.4-4ubuntu2 — «d/sysctl.d/10-map-count.conf: Set vm.max_map_count=1048576 (LP: #2057792)»; файл `/etc/sysctl.d/10-map-count.conf` в 24.04, `/usr/lib/sysctl.d/55-map-count.conf` в 26.04; в 22.04 такого файла нет (остаётся 65530). Проверка: `sysctl vm.max_map_count`. PostgreSQL и сервер 1С в него обычно не упираются; повышают для Elasticsearch/JVM. Симптом нехватки — `mmap failed: Cannot allocate memory` при наличии свободной памяти.

### 3.6. `kernel.shmmax`, `kernel.shmall`, `kernel.sem` — актуальны ли

- **`kernel.shmmax` / `kernel.shmall`** — лимиты System V shared memory. [PG]: на Linux настройки по умолчанию достаточны, если только не выбран `shared_memory_type = sysv` (не используется по умолчанию ни на одной платформе; по умолчанию `mmap`). С PostgreSQL 9.3 основной сегмент выделяется анонимным `mmap`, System V используется только для крошечного сегмента-маркера. В ядрах ≥ 3.16 значения по умолчанию практически не ограничены: `shmmax` = `shmall` = `ULONG_MAX − 2^24` = `18446744073692774399` [man shmget(2)]. **Не задавайте их**; строки `kernel.shmmax = <половина RAM>` из старых инструкций удаляйте.
- **`kernel.sem`** — четыре числа `SEMMSL SEMMNS SEMOPM SEMMNI`. [PG 18]: на Linux «System V semaphores are not used on this platform» (используются POSIX-семафоры). Не задавайте: типичная строка из старых руководств `kernel.sem = 250 32000 100 128` **уменьшает** современные значения по умолчанию. Потребность, если очень нужно: `postgres -D $PGDATA -C num_os_semaphores`.
- **`RemoveIPC`** [PG]: параметр `logind.conf` управляет удалением IPC-объектов пользователя при его полном выходе из системы; **системные пользователи исключены**. Если пользователь `postgres` — не системный, то при завершении его последней сессии удаляются объекты разделяемой памяти, в том числе используемые параллельными запросами; типичный симптом по [PG] — «в случайные моменты» ошибки и предупреждения вида `WARNING: could not remove shared memory segment "/PostgreSQL.1450751626": No such file or directory` (сервер при этом не обязательно падает целиком). [PG]: в «чистом» systemd умолчание `RemoveIPC=yes`, но некоторые дистрибутивы ставят `no` (для Ubuntu фактическое значение — ⚠ не проверено: `systemd-analyze cat-config systemd/logind.conf | grep -i removeipc`). Пакеты создают `postgres` системным пользователем (проблемы нет); при ручной установке — создавать пользователя через `adduser --system` / `useradd -r` либо, если учётку изменить нельзя, `RemoveIPC=no` в `/etc/systemd/logind.conf`. То же относится к пользователю сервера 1С, если он создан вручную как обычный, а не установщиком.

### 3.7. Файлы: `fs.file-max`, `fs.nr_open`, `fs.aio-max-nr`

- **`fs.file-max`** — общесистемный лимит открытых файлов. systemd при загрузке поднимает его до максимума (опция сборки `bump-proc-sys-fs-file-max`, включена по умолчанию; в `debian/rules` пакета systemd отключена только соседняя `-Dbump-proc-sys-fs-nr-open=false`, поэтому в Debian/Ubuntu `fs.file-max` огромный, а `fs.nr_open` остаётся 1048576). Проверка: `sysctl fs.file-max fs.nr_open`. Исчерпание видно в `dmesg` как `VFS: file-max limit <N> reached` [ядро], вызовы получают `ENFILE`.
- **`fs.file-nr`** — три числа: выделено / свободно (всегда 0) / максимум. `cat /proc/sys/fs/file-nr`.
- **`fs.nr_open`** — потолок для `RLIMIT_NOFILE` одного процесса, по умолчанию 1024×1024 = 1048576 [ядро]: выше этого `LimitNOFILE` не поднять (`LimitNOFILE=infinity` в Ubuntu означает 1048576).
- **`fs.aio-max-nr`** — лимит событий ядерного AIO (`io_setup`); при исчерпании `EAGAIN` [man io_setup(2)]. PostgreSQL до 17 включительно ядерный AIO не использует; в PostgreSQL 18 `io_method = worker` (по умолчанию, `io_workers = 3`) [PG] тоже его не использует, а `io_method = io_uring` — это отдельный механизм, `aio-max-nr` на него не влияет. Строка `fs.aio-max-nr = 1048576` в инструкциях «для 1С» — калька с требований Oracle; не нужна.
- Для `io_method = io_uring` в PostgreSQL 18 сборка должна быть с liburing (`--with-liburing` / `-Dliburing`) [PG], а sysctl `kernel.io_uring_disabled` — равен 0 (это значение по умолчанию: «все процессы могут создавать экземпляры io_uring»; 1 — только привилегированным/группе, 2 — запрещено всем) [ядро]. Собраны ли с liburing пакеты PostgreSQL 18 из архива Ubuntu/PGDG и сборки для 1С — ⚠ не проверено (`pg_config --configure | tr ' ' '\n' | grep -i uring`); рекомендаций 1С/PGPro переходить на `io_uring` нет — оставляйте `worker`.

На практике в лимит упираются не здесь, а в **лимит процесса** (`LimitNOFILE` службы) — см. раздел 5.

### 3.8. Сеть

- **`net.core.somaxconn`** [ядро]: предел очереди `listen()`; по умолчанию 4096 (до 5.4 — 128). [PG] упоминает его как параметр, который может понадобиться увеличить при большом числе одновременных запросов на соединение; после изменения нужен перезапуск PostgreSQL. На Ubuntu 22.04+ менять не требуется.
- **`net.ipv4.tcp_keepalive_time` / `_intvl` / `_probes`** [ядро]: 7200 с / 75 с / 9. То есть «мёртвое» соединение обнаружится через 2 часа + 11 минут. Действуют только на сокеты с включённым `SO_KEEPALIVE`.
  - [практика] 600 / 60 / 5: зависший клиент или разрыв через межсетевой экран обнаруживается за ~15 минут, а NAT/файрвол не «забывает» простаивающие соединения 1С ↔ PostgreSQL и клиент ↔ сервер 1С.
  - Точечная альтернатива — параметры PostgreSQL `tcp_keepalives_idle`, `tcp_keepalives_interval`, `tcp_keepalives_count` (0 = системные значения).
- **`net.ipv4.ip_local_port_range`** [ядро]: `32768 60999` — диапазон исходящих (эфемерных) портов. Порты сервера 1С по умолчанию (1540, 1541, 1545, 1560–1591) и PostgreSQL (5432) в него не попадают. Расширять (`10000 65535`) имеет смысл только при десятках тысяч исходящих соединений на один адрес:порт; тогда слушающие порты защищают через `net.ipv4.ip_local_reserved_ports`.
- Остальное (`tcp_tw_reuse` = 2, `tcp_fin_timeout` = 60, `tcp_retries2` = 15, `tcp_timestamps` = 1, `tcp_syncookies` = 1) — оставлять по умолчанию. EDB в своём наборе ставит `net.ipv4.tcp_timestamps=0` — спорно, не повторять без причины.

```bash
ss -ltn                                  # слушающие сокеты и размер backlog (Send-Q)
nstat -az TcpExtListenOverflows TcpExtListenDrops   # переполнения очереди listen
sysctl net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes
```

### 3.9. NUMA

На многосокетных физических серверах [практика]: `vm.zone_reclaim_mode = 0` (это и так значение по умолчанию [ядро]) и `kernel.numa_balancing = 0`. Проверка топологии: `lscpu | grep -i numa`, `numactl --hardware`. В ВМ с одним виртуальным NUMA-узлом неактуально.

### 3.10. Пример файла

```ini
# /etc/sysctl.d/90-1c-postgres.conf
# ВМ: сервер 1С + PostgreSQL на одном хосте. Значения — практика сообщества, не требование 1С.

# Память
vm.swappiness = 10
vm.dirty_background_bytes = 67108864
vm.dirty_bytes = 536870912

# Только для ВЫДЕЛЕННОГО сервера PostgreSQL (без сервера 1С):
#vm.overcommit_memory = 2
#vm.overcommit_ratio = 90

# Huge pages: число из `postgres -C shared_memory_size_in_huge_pages` (раздел 6)
#vm.nr_hugepages = 4300

# Планировщик: группировка по сессиям серверу не нужна
kernel.sched_autogroup_enabled = 0

# TCP keepalive: быстрее находить «мёртвые» соединения
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5
```

```bash
sudo sysctl --system
sysctl vm.swappiness vm.dirty_bytes kernel.sched_autogroup_enabled
```

Меняйте параметры по одному и сравнивайте поведение под нагрузкой (тест Гилёва, реальные операции, `pg_stat_bgwriter`/`pg_stat_checkpointer`, `iostat -x 5`, `vmstat 5`).

---

## 4. Планировщик: что осталось актуальным в ядрах 6.x

История:

- До ядра 5.12 включительно в sysctl были `kernel.sched_migration_cost_ns` (500000), `kernel.sched_min_granularity_ns`, `kernel.sched_wakeup_granularity_ns`, `kernel.sched_latency_ns`. Классическая рекомендация для PostgreSQL — `kernel.sched_migration_cost_ns = 5000000` и `kernel.sched_autogroup_enabled = 0` (рассылка pgsql-performance, тема «Two Necessary Kernel Tweaks for Linux Systems»; профиль tuned `postgresql` для RHEL 6).
- В **5.13** отладочные параметры планировщика перенесены из sysctl в **debugfs**: `/sys/kernel/debug/sched/` (`migration_cost_ns`, `min_granularity_ns`, `latency_ns`, `wakeup_granularity_ns`, `nr_migrate`, `tunable_scaling`).
- В **6.6** планировщик CFS заменён на **EEVDF**: `min_granularity_ns` переименован в `base_slice_ns`; `latency_ns`, `wakeup_granularity_ns` и `idle_min_granularity_ns` **удалены** — подтверждено коммитом ядра 5e963f2bd465 «sched/fair: Commit to EEVDF» (в `kernel/sched/debug.c` убраны соответствующие `debugfs_create_u32(...)`; сообщение коммита: у EEVDF «меньше эвристик/настроек»). `migration_cost_ns`, `nr_migrate`, `tunable_scaling` в debugfs остались.

Что это значит для Ubuntu 22.04 / 24.04 / 26.04:

```bash
sysctl kernel.sched_migration_cost_ns
# sysctl: cannot stat /proc/sys/kernel/sched_migration_cost_ns: No such file or directory
```

- Строки `kernel.sched_migration_cost_ns`, `kernel.sched_min_granularity_ns`, `kernel.sched_wakeup_granularity_ns`, `kernel.sched_latency_ns` в `sysctl.d` **не работают** и дают ошибку при `sysctl --system`. Удаляйте их из унаследованных конфигов.
- Посмотреть/изменить через debugfs (не сохраняется после перезагрузки; официально никем для 1С/PostgreSQL не рекомендуется):

```bash
sudo ls /sys/kernel/debug/sched/
sudo cat /sys/kernel/debug/sched/migration_cost_ns      # 500000
sudo cat /sys/kernel/debug/sched/base_slice_ns          # ядра >= 6.6
echo 5000000 | sudo tee /sys/kernel/debug/sched/migration_cost_ns
```

Что осталось в sysctl и имеет смысл:

| Параметр | Назначение | Рекомендация |
|---|---|---|
| `kernel.sched_autogroup_enabled` | автогруппировка задач по сессиям (для десктопа) | 0 на сервере [практика] |
| `kernel.numa_balancing` | автоматическая миграция страниц между NUMA-узлами (0/1/2) | 0 на NUMA-сервере СУБД [практика] |
| `kernel.sched_rt_runtime_us`, `kernel.sched_rt_period_us`, `kernel.sched_rr_timeslice_ms` | real-time классы | не трогать |
| `kernel.sched_cfs_bandwidth_slice_us` | квант CPU-квот cgroup | не трогать |
| `kernel.sched_schedstats`, `kernel.sched_energy_aware`, `kernel.sched_util_clamp_*` | статистика/энергоэффективность | не трогать |

Вывод: на ядрах 6.x/7.x тюнинг планировщика для 1С/PostgreSQL сводится к `kernel.sched_autogroup_enabled=0` и (на NUMA) `kernel.numa_balancing=0`. Больший эффект дают отключение энергосбережения, THP и правильные huge pages.

---

## 5. Лимиты ресурсов

Три независимых уровня:

| Уровень | Где задаётся | На кого действует |
|---|---|---|
| Процесс (rlimit) | `ulimit` в оболочке; `prlimit` | текущая оболочка и её потомки / конкретный PID |
| PAM-сессия | `/etc/security/limits.conf`, `/etc/security/limits.d/*.conf` (модуль `pam_limits`) | входы через ssh, консоль, cron и т. п. — **не службы systemd** |
| Служба systemd | `Limit*=`, `TasksMax=` в юните / drop-in; значения по умолчанию в `/etc/systemd/system.conf` | процессы службы (PostgreSQL, сервер 1С, Apache) |

### 5.1. ulimit и prlimit

```bash
ulimit -a            # все мягкие лимиты текущей оболочки
ulimit -Ha           # жёсткие
ulimit -n            # открытые файлы (nofile)
ulimit -u            # процессы/потоки пользователя (nproc)
ulimit -c            # размер core-файла (0 = не писать)
ulimit -l            # заблокированная память (memlock), КБ
ulimit -n 65536      # поднять мягкий лимит (не выше жёсткого) для этой оболочки
ulimit -c unlimited

# лимиты работающего процесса
cat /proc/$(pgrep -o postgres)/limits
sudo prlimit --pid 1234                        # то же в табличном виде
sudo prlimit --pid 1234 --nofile=65536:65536   # изменить «на лету» (до перезапуска процесса)
```

Пример вывода `/proc/<pid>/limits` (важные строки):

```text
Limit                     Soft Limit           Hard Limit           Units
Max processes             127329               127329               processes
Max open files            1024                 524288               files
Max locked memory         8388608              8388608              bytes
Max core file size        0                    unlimited            bytes
```

### 5.2. /etc/security/limits.conf и limits.d

Формат строки [man limits.conf(5)]: `<domain> <type> <item> <value>`

- `domain`: имя пользователя, `@группа`, `*` (все), диапазон UID `1000:2000`. **Групповые и `*`-правила на root не действуют** — для root нужна строка с буквальным `root`.
- `type`: `soft`, `hard`, `-` (оба сразу).
- `item`: `nofile`, `nproc`, `core` (КБ), `memlock` (КБ), `stack` (КБ), `as` (КБ), `fsize`, `cpu` (минуты), `maxlogins`, `nice`, `rtprio`, `sigpending`, `msgqueue`, `locks`.
- `value`: число; `unlimited` / `infinity` / `-1` — без ограничений. Для `nofile` «unlimited» означает значение из `/proc/sys/fs/nr_open`.
- Индивидуальные правила пользователя приоритетнее групповых. Лимиты действуют **на сессию** и появляются после нового входа.

```ini
# /etc/security/limits.d/90-1c-postgres.conf
postgres   soft  nofile  65536
postgres   hard  nofile  65536
usr1cv8    soft  nofile  65536
usr1cv8    hard  nofile  65536
usr1cv8    soft  core    unlimited
usr1cv8    hard  core    unlimited
```

Зачем это нужно, если службы запускает systemd: только для интерактивной работы под этими пользователями (ручной запуск `pg_ctl`, `ragent`, утилит, скриптов из cron). Проверка: `sudo -u postgres bash -c 'ulimit -n'` и `su - postgres -c 'ulimit -n'`.

Через какие входы `limits.conf` применяется, определяет наличие строки `session required pam_limits.so` в соответствующем файле `/etc/pam.d/`:

- `su`: в Ubuntu 22.04/24.04/26.04 файл `/etc/pam.d/su` поставляется пакетом `util-linux`, и строка `session required pam_limits.so` в нём **активна** (проверено по исходникам Debian util-linux для bullseye и unstable). Утверждение «в `su` pam_limits закомментирован» относится к старым выпускам, где `su` поставлялся пакетом `login` (Ubuntu 18.04 и раньше — ⚠ граница по памяти) — **исправлено рецензией**;
- `sudo`, `sshd`, `login`, `cron`: строка обычно тоже есть (⚠ для 26.04 с `sudo-rs` не проверено).

Фактическое состояние на своей системе: `grep -H pam_limits /etc/pam.d/*`.

Важное следствие для документации 1С: в приложении 3 руководства администратора (раздел о дампах в Linux) включение дампов описано через `/etc/security/limits.conf` (`<username> soft core unlimited` / `hard core unlimited`). Для сервера 1С, запущенного **как служба systemd** (`srv1cv8-...@...service`), этого недостаточно: PAM в запуске службы не участвует, нужен `LimitCORE=infinity` в drop-in юнита (раздел 5.3). Строки в `limits.conf` сработают только для процессов 1С, запущенных из интерактивного сеанса/cron (тонкий клиент, `ibcmd`, ручной запуск `ragent`).

### 5.3. Лимиты служб systemd

Директивы [man systemd.exec(5)] и соответствие `ulimit`:

| Директива | ulimit | Единицы | Примечание |
|---|---|---|---|
| `LimitNOFILE=` | `-n` | дескрипторы | по умолчанию `1024:524288`; поднимать мягкий лимит выше 1024 безопасно только для программ, не использующих `select()` |
| `LimitNPROC=` | `-u` | процессы | считается **на UID**, а не на службу; для root не действует; лучше `TasksMax=` |
| `LimitCORE=` | `-c` | байты | апстрим: PID 1 ставит `infinity`; **в Debian/Ubuntu умолчание `0:infinity`** (мягкий 0) — см. ниже |
| `LimitMEMLOCK=` | `-l` | байты | по умолчанию 8M (systemd 255+/Ubuntu 24.04+; в 22.04 не задан) |
| `LimitSTACK=`, `LimitAS=`, `LimitDATA=`, `LimitFSIZE=`, `LimitCPU=` | `-s -v -d -f -t` | байты / секунды | для ограничения памяти лучше `MemoryMax=` |
| `TasksMax=` | — | задачи (процессы **и потоки**) cgroup | [man systemd.resource-control(5)]; по умолчанию `DefaultTasksMax=15%` от min(`kernel.pid_max`, `kernel.threads-max`, `pids.max` корня) |

Синтаксис: одно число (мягкий = жёсткий) или `мягкий:жёсткий`, например `LimitNOFILE=65536:524288`; `infinity` — без ограничения.

Значения по умолчанию [man systemd-system.conf(5)]: `DefaultLimitNOFILE=1024:524288`, `DefaultTasksMax=15%`, `DefaultTimeoutStopSec=90s` (одинаково в 22.04 и 24.04); `DefaultLimitMEMLOCK=8M` — в man-странице noble (systemd 255) указано явно, в man-странице jammy (systemd 249) умолчание не названо («большинство этих настроек не заданы» — лимит наследуется). Общие настройки менеджера — `/etc/systemd/system.conf` и `/etc/systemd/system.conf.d/*.conf` (после изменения: `sudo systemctl daemon-reexec` или перезагрузка).

**`LimitCORE` в Debian/Ubuntu.** Man-страница говорит, что `RLIMIT_CORE` ставится PID 1 в `infinity`, но сборка Debian/Ubuntu это переопределяет: в исходниках пакета systemd есть `debian/extra/system.conf.d/10-coredump-debian.conf` с содержимым `[Manager]` / `DefaultLimitCORE=0:infinity`; в Ubuntu 26.04 он установлен как `/usr/lib/systemd/system.conf.d/10-coredump-debian.conf` (вместе с `/usr/lib/sysctl.d/10-coredump-debian.conf`), в более старых выпусках тот же результат даёт патч Debian (наличие правки подтверждено 11.10.2026: в каталоге `debian/patches/debian` пакета Debian версий 249.7-1 и 255.4-1 есть `Revert-core-set-RLIMIT_CORE-to-unlimited-by-default.patch`; ранее: механизм для 22.04/24.04 — по памяти, результат виден в `/proc/<pid>/limits`). Итог: у служб «Max core file size» = `0` (мягкий) / `unlimited` (жёсткий), как в примере вывода в разделе 5.1, и дампы не создаются, пока мягкий лимит не поднят (`LimitCORE=infinity` в юните или `ulimit -c unlimited` в оболочке). Проверка: `systemctl show -p DefaultLimitCORE -p DefaultLimitCORESoft`.

Посмотреть:

```bash
systemctl show postgresql@17-main.service -p LimitNOFILE -p LimitNOFILESoft -p LimitNPROC -p LimitCORE -p LimitMEMLOCK -p TasksMax -p OOMScoreAdjust
systemctl status postgresql@17-main.service | grep -i tasks     # Tasks: 37 (limit: 9443)
systemctl cat postgresql@17-main.service                        # юнит + все drop-in
cat /proc/$(systemctl show -p MainPID --value postgresql@17-main.service)/limits
systemctl list-units --type=service | grep -iE 'srv1cv8|postgres'   # точные имена юнитов
```

Изменить (drop-in, переживает обновление пакета):

```bash
sudo systemctl edit postgresql@17-main.service
```

```ini
# /etc/systemd/system/postgresql@17-main.service.d/override.conf
[Service]
LimitNOFILE=65536
TasksMax=infinity
# рекомендация ИТС на случай заметной фрагментации памяти процессов PostgreSQL (см. ниже); без симптомов не обязательна:
#Environment=MALLOC_MMAP_THRESHOLD_=8192
```

```bash
sudo systemctl daemon-reload            # `systemctl edit` делает это сам
sudo systemctl restart postgresql@17-main.service
```

Для сервера 1С имя юнита зависит от версии платформы. [1С] (руководство «Клиент-серверный вариант», гл. 4, документация 8.3.27 — конспект в `kb/its-docs/cs-gl04-zapusk-komponentov.md`): на x86-64 и ARM64 сервер управляется через systemd шаблонным юнитом **`srv1cv8-A.B.C.D@.service`**, лежащим в каталоге версии `/opt/1cv8/<арх>/A.B.C.D/`; его подключают `systemctl link`, экземпляр называют после `@` (обычно `default`), параметры меняют командой `systemctl edit srv1cv8-A.B.C.D@<экземпляр>` строками `Environment=SRV1CV8_...=...` в секции `[Service]`. Пример полного имени: `srv1cv8-8.3.27.1688@default.service`. SysV-скрипт `srv1cv83` (`/etc/init.d`, конфиг в `/etc/default` или `/etc/sysconfig`) в документации 8.3.27 оставлен только для архитектуры E2K; на старых версиях платформы (в статье ИТС для 8.3.13 — `systemctl start srv1cv83`) служба называлась `srv1cv83`. Граница «шаблонный юнит с 8.3.21» в документации 8.3.27 не названа — она взята из статьи базы знаний `kb/1c/01-arhitektura-versii-trebovaniya.md` (⚠ здесь не перепроверялась). Содержимое штатного юнита (есть ли в нём `LimitNOFILE=`, `LimitCORE=`, `OOMScoreAdjust=`, `TasksMax=`) документацией не описано и **не проверено** (⚠) — смотрите `systemctl cat srv1cv8-<версия>@default` и `systemctl show ... -p LimitNOFILE -p LimitCORE -p TasksMax -p OOMScoreAdjust`. Точные имена юнитов на своей системе: `systemctl list-units --type=service | grep srv1cv8`.

```bash
sudo systemctl edit srv1cv8-8.3.27.NNNN@default.service
```

```ini
[Service]
LimitNOFILE=65536
LimitCORE=infinity
TasksMax=infinity
```

Особенности для 1С и PostgreSQL:

- **Drop-in привязан к имени юнита.** После обновления платформы 1С имя юнита меняется (в нём номер версии) — drop-in остаётся у старого имени. Варианты:
  1. переносить drop-in при каждом обновлении платформы (так предписывает и схема обновления из документации: «с теми же `SRV1CV8_*`»);
  2. **drop-in по префиксу имени** [man systemd.unit(5)]: для юнитов, в имени которых есть дефисы, systemd дополнительно читает каталоги, полученные усечением имени после каждого дефиса (пример из man: для `foo-bar-baz.service` — ещё `foo-bar-.service.d/` и `foo-.service.d/`). Для `srv1cv8-8.3.27.1688@default.service` это каталог `/etc/systemd/system/srv1cv8-.service.d/` — положенный туда `limits.conf` применится к юнитам сервера 1С **любой версии** (механизм есть в systemd 239+, т. е. во всех трёх выпусках Ubuntu; ⚠ на юните 1С не проверялось — убедитесь, что `systemctl cat srv1cv8-<версия>@default` показывает ваш файл):

     ```bash
     sudo mkdir -p /etc/systemd/system/srv1cv8-.service.d
     printf '[Service]\nLimitNOFILE=65536\nLimitCORE=infinity\nTasksMax=infinity\n' | sudo tee /etc/systemd/system/srv1cv8-.service.d/limits.conf
     sudo systemctl daemon-reload && sudo systemctl restart 'srv1cv8-*@default.service'
     systemctl cat 'srv1cv8-*@default.service' | grep -A4 limits.conf
     ```

  3. задать значения по умолчанию для всех служб в `/etc/systemd/system.conf.d/90-limits.conf` (`[Manager]`, `DefaultLimitNOFILE=65536:524288`, `DefaultTasksMax=infinity`) — самый грубый способ: мягкий лимит выше 1024 получат **все** службы, а [man systemd.exec(5)] предупреждает, что это небезопасно для программ, использующих `select()`; применять, только если первые два не подходят.
- **`max_files_per_process`** в PostgreSQL по умолчанию 1000 [PG]; [1С] (ИТС, «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2») рекомендует `max_files_per_process = 8000`, [PGPro] `pgpro_tune` ставит 10000, контроль — утилитой `lsof`. Чтобы такое значение реально работало, мягкий `LimitNOFILE` службы должен быть не меньше него (при 1024 backend сам ограничит себя доступным числом дескрипторов) — [практика], следует из механики PostgreSQL.
- **`MALLOC_MMAP_THRESHOLD_=8192`** [1С]: в той же статье ИТС (сверено с локальным конспектом `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md`) это рекомендация **на случай заметной фрагментации памяти процессов PostgreSQL в Linux**, а не безусловная настройка: переменную окружения задают в unit-файле systemd PostgreSQL (в статье пример для `/etc/systemd/system/postgresql-10.service`). В тексте статьи строка встречается и с пробелами (`Environment = MALLOC_MMAP_THRESHOLD_= 8192`) — для systemd правильна запись без пробелов вокруг значения: `Environment=MALLOC_MMAP_THRESHOLD_=8192`. В Ubuntu задавайте её в drop-in (`systemctl edit postgresql@17-main`), а не правкой юнита пакета; альтернатива для `postgresql-common` — файл `/etc/postgresql/17/main/environment` (его читает `pg_ctlcluster`), строка `MALLOC_MMAP_THRESHOLD_ = 8192`. Проверка, что переменная дошла до процесса: `sudo cat /proc/$(pgrep -o postgres)/environ | tr '\0' '\n' | grep MALLOC`.
- **`TasksMax`**: у сервера 1С каждый сеанс/соединение — потоки `rphost`; у PostgreSQL каждый клиент — процесс. На больших инсталляциях 15 % может не хватить; симптомы — `fork: retry: Resource temporarily unavailable`, `pthread_create failed`, в журнале `kernel: cgroup: fork rejected by pids controller in /system.slice/...`.
- **Core-дампы** сервера 1С. [1С] (руководство администратора, приложение 3, «Настройка генерации дампов… для ОС Linux» — конспект в `kb/its-docs/adm-pr03-sluzhebnye-fajly-p4.md`):
  - в Linux и macOS дампы настраиваются **средствами ОС**, элемент `<dump>` в `logcfg.xml` игнорируется; по умолчанию создание дампов отключено; поставщики дистрибутивов не рекомендуют держать его включённым на продуктиве;
  - включение по документации: в `/etc/security/limits.conf` строки `<username> soft core unlimited` и `<username> hard core unlimited` (`<username>` — пользователь, от имени которого работает 1С);
  - имя и место дампов — `kernel.core_pattern`, пример из документации: `sysctl -w kernel.core_pattern=/tmp/core.%e.%p` (временно) либо та же строка в `/etc/sysctl.conf` + `sysctl -p` (постоянно); настройка общесистемная, каталог должен быть доступен на запись пользователю сервера;
  - оговорка самой документации: рекомендации «в полной мере применимы к Fedora Core 4», в других дистрибутивах синтаксис может отличаться.

  Адаптация к Ubuntu с systemd [практика, следует из раздела 5 и 2.2]: (1) для службы вместо `limits.conf` — `LimitCORE=infinity` в drop-in юнита (умолчание Debian/Ubuntu — мягкий лимит 0); (2) шаблон — в `/etc/sysctl.d/90-coredump.conf`, а не в `/etc/sysctl.conf`; (3) в Ubuntu `kernel.core_pattern` по умолчанию перехватывает `apport` (`sysctl kernel.core_pattern` покажет `|/usr/share/apport/apport ...`), и при перезапуске службы `apport` шаблон будет возвращён — либо отключайте `apport` (`sudo systemctl disable --now apport.service`, `enabled=0` в `/etc/default/apport`), либо используйте `systemd-coredump` (`sudo apt install systemd-coredump`, дампы в `/var/lib/systemd/coredump/`, просмотр `coredumpctl list`) — ⚠ взаимодействие пакетов `apport` и `systemd-coredump` в Ubuntu (оба претендуют на `kernel.core_pattern`) и пригодность таких дампов для поддержки 1С при рецензии не проверялись — после настройки убедитесь на тестовом процессе (`sleep 600 & kill -SEGV $!` под пользователем сервера с `ulimit -c unlimited`), что файл дампа появляется там, где вы ожидаете; (4) каталог для дампов должен вмещать дамп размером с память `rphost` (десятки гигабайт) — не `/tmp` на корневом разделе.

  ```ini
  # sudo systemctl edit srv1cv8-8.3.27.1688@default
  [Service]
  LimitCORE=infinity
  ```

  ```bash
  sudo install -d -o usr1cv8 -g "$(id -gn usr1cv8)" -m 0750 /var/1c-dumps    # каталог на разделе с запасом места
  echo 'kernel.core_pattern=/var/1c-dumps/core.%e.%p' | sudo tee /etc/sysctl.d/90-coredump.conf
  sudo sysctl --system && sysctl kernel.core_pattern
  sudo systemctl restart srv1cv8-8.3.27.1688@default
  grep -i core /proc/$(pgrep -o ragent)/limits      # Max core file size  unlimited  unlimited
  ```

Проверка расхода дескрипторов:

```bash
sudo ls /proc/$(pgrep -o postgres)/fd | wc -l            # открыто у postmaster
for p in $(pgrep rphost); do echo "$p $(sudo ls /proc/$p/fd | wc -l)"; done
sudo lsof -u postgres | wc -l                              # суммарно у пользователя
cat /proc/sys/fs/file-nr                                   # по системе
```

---

## 6. Transparent Huge Pages (THP) и обычные huge pages

Это **два разных механизма**:

| | Transparent Huge Pages (THP) | Обычные huge pages (HugeTLB) |
|---|---|---|
| Кто выделяет | ядро автоматически, «прозрачно», фоновый `khugepaged` | администратор резервирует заранее (`vm.nr_hugepages`) |
| Кому достаются | любой анонимной памяти (режим `always`) или только по `madvise` | только тем, кто явно просит (`MAP_HUGETLB`): PostgreSQL при `huge_pages=try/on` |
| Для СУБД | **не рекомендуется** [PG] | **рекомендуется** при большом `shared_buffers` [PG] |
| Управление | `/sys/kernel/mm/transparent_hugepage/*`, параметр ядра `transparent_hugepage=` | `vm.nr_hugepages`, параметры ядра `hugepages=`, `hugepagesz=` |

Отключение THP **не мешает** обычным huge pages.

### 6.1. THP: проверить

```bash
cat /sys/kernel/mm/transparent_hugepage/enabled     # always [madvise] never — текущее в скобках
cat /sys/kernel/mm/transparent_hugepage/defrag      # always defer defer+madvise [madvise] never
grep -E 'AnonHugePages|ShmemHugePages' /proc/meminfo   # сколько памяти сейчас под THP
grep thp /proc/vmstat | head
```

Значения `enabled` [ядро]: `always` — для всей анонимной памяти; `madvise` — только для областей, где приложение вызвало `madvise(MADV_HUGEPAGE)`; `never` — выключено. В Ubuntu 22.04/24.04 по умолчанию обычно `madvise` (так собрано ядро Ubuntu; по рассылке kernel-team Ubuntu умолчание переключено с `always` на `madvise` правкой «UBUNTU: SAUCE: use CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y as default», принятой в июле 2017 года для 17.10 (lists.ubuntu.com/archives/kernel-team/2017-July/085576.html; найдено 11.10.2026); для нынешних ядер это же первоисточником — конфигурацией ядра — в ходе рецензии подтвердить не удалось, для 26.04 не проверено вовсе; всегда смотрите фактическое значение командой выше). PostgreSQL сам `madvise(MADV_HUGEPAGE)` не вызывает (⚠ по памяти), поэтому при `madvise` THP его практически не касается; значение `never` — самый однозначный вариант для сервера СУБД. Процессы сервера 1С (`rphost`) при `madvise` THP тоже получают только там, где их явно запрашивает аллокатор/библиотека.

### 6.2. THP: почему отключают для БД

- [PG], описание параметра `huge_pages`: использование THP «has been known to cause performance degradation with PostgreSQL for some users on some Linux versions, so its use is currently discouraged (unlike explicit use of huge_pages)».
- Механика: `khugepaged` и синхронная компакция памяти (defrag) при выделении вызывают непредсказуемые паузы и рост system CPU; память процессов «раздувается» (страница 2 МБ вместо нужных 4 КБ); для нагрузки с множеством короткоживущих backend-процессов и разреженным доступом к памяти выигрыша нет.
- Официального требования 1С про THP **нет**: в методических статьях ИТС о настройке PostgreSQL для 1С и в документации платформы 8.3.27 (по локальным конспектам `kb/its-metod/`, `kb/its-docs/`) нет ни слова о `transparent_hugepage`, `vm.nr_hugepages`/huge pages или `vm.swappiness`; единственное близкое требование ИТС — «запретить своппинг разделяемой памяти SYSV/posix» (пример дан только для FreeBSD: `kern.ipc.shm_use_phys=1`; как это сделать в Linux, статья не говорит — на Linux этому требованию отвечают именно huge pages, которые не выгружаются в swap). Отключение THP — общепринятая [практика]: профиль tuned `postgresql` (`transparent_hugepages=never`), EDB; упоминание в документации Tantor для 1С — по выдаче поиска, страница в ходе рецензии не открылась (⚠).

### 6.3. THP: отключить

**До перезагрузки (сразу):**

```bash
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag
```

Уже выделенные THP при этом не разбиваются — полный эффект после перезапуска служб.

**Способ 1 — параметр ядра в GRUB (самый надёжный, действует с самого начала загрузки):**

```bash
sudoedit /etc/default/grub
# GRUB_CMDLINE_LINUX_DEFAULT="quiet splash transparent_hugepage=never"
sudo update-grub
sudo reboot
cat /proc/cmdline                                   # убедиться, что параметр на месте
cat /sys/kernel/mm/transparent_hugepage/enabled     # always madvise [never]
```

Допустимые значения параметра [ядро]: `transparent_hugepage=always|madvise|never`.

**Способ 2 — systemd-юнит (без правки загрузчика):**

```ini
# /etc/systemd/system/disable-thp.service
[Unit]
Description=Disable Transparent Huge Pages (THP)
DefaultDependencies=no
After=sysinit.target local-fs.target
Before=basic.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled; echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=basic.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now disable-thp.service
```

Юнит срабатывает до `basic.target`, то есть раньше PostgreSQL и сервера 1С.

**Способ 3 — профиль tuned** с секцией `[vm]` и `transparent_hugepages=never` (раздел 7.3).

Используйте один способ. Если в ВМ применяется cloud-образ, проверьте, не переопределяет ли `GRUB_CMDLINE_LINUX_DEFAULT` файл в `/etc/default/grub.d/` (раздел 7.4).

### 6.4. Обычные huge pages для PostgreSQL

Зачем: при `shared_buffers` в десятки гигабайт и сотнях соединений (а 1С открывает много соединений) таблицы страниц каждого backend-процесса для 4-КБ страниц занимают сотни мегабайт, растут промахи TLB. Huge pages (2 МБ) уменьшают таблицы страниц в 512 раз, память под них не свопится. Заметный эффект — обычно от `shared_buffers` ≥ 8 ГБ [практика].

**Шаг 1. Рассчитать число страниц** [PG] (параметр `shared_memory_size_in_huge_pages` есть в PostgreSQL 15+; он учитывает `shared_buffers`, `max_connections`, `max_locks_per_transaction` и т. д.). Для расчёта через `postgres -C` сервер **должен быть остановлен** [PG]:

```bash
grep ^Hugepagesize /proc/meminfo            # Hugepagesize: 2048 kB
ls /sys/kernel/mm/hugepages                 # hugepages-1048576kB  hugepages-2048kB

# Ubuntu, пакеты PGDG/архива (конфиг в /etc/postgresql):
sudo systemctl stop postgresql@17-main
sudo -u postgres /usr/lib/postgresql/17/bin/postgres \
     -D /var/lib/postgresql/17/main \
     -c config_file=/etc/postgresql/17/main/postgresql.conf \
     -C shared_memory_size_in_huge_pages
# 4257

# Postgres Pro (пути зависят от редакции; пример для сборки «для 1С» — ⚠ сверить по своей установке):
# sudo -u postgres /opt/pgpro/1c-17/bin/postgres -D /var/lib/pgpro/1c-17/data -C shared_memory_size_in_huge_pages
```

На работающем сервере то же число: `sudo -u postgres psql -c "SHOW shared_memory_size_in_huge_pages;"` (значение `-1` — huge pages не поддерживаются).

Для версий до 15 — оценка по `VmPeak` процесса postmaster [практика, EDB/Percona]:

```bash
pid=$(sudo head -1 /var/lib/postgresql/14/main/postmaster.pid)
grep ^VmPeak /proc/$pid/status          # VmPeak: 8823028 kB  →  8823028 / 2048 ≈ 4309 страниц
```

**Шаг 2. Зарезервировать** (берите расчётное число с запасом 1–3 %):

```bash
sudo sysctl -w vm.nr_hugepages=4300
grep -i huge /proc/meminfo
#   HugePages_Total:    4300   ← если меньше запрошенного — память фрагментирована, нужна перезагрузка
#   HugePages_Free:     4300
#   HugePages_Rsvd:        0
#   HugePages_Surp:        0
#   Hugepagesize:       2048 kB
#   Hugetlb:         8806400 kB

echo 'vm.nr_hugepages = 4300' | sudo tee /etc/sysctl.d/91-hugepages.conf
```

Самый надёжный способ резервирования [ядро] — при загрузке: параметры ядра `hugepagesz=2M hugepages=4300` в GRUB (память ещё не фрагментирована). Для страниц нестандартного размера — запись в `/sys/kernel/mm/hugepages/hugepages-<размер>kB/nr_hugepages`.

**Шаг 3. Включить в PostgreSQL** (`postgresql.conf`):

```ini
huge_pages = try        # по умолчанию: пробовать, при неудаче молча использовать обычные страницы
#huge_pages = on        # требовать: при нехватке страниц сервер НЕ запустится
#huge_page_size = 0     # 0 = размер по умолчанию в системе; можно 2MB или 1GB (только Linux)
```

```bash
sudo systemctl start postgresql@17-main
sudo -u postgres psql -c "SHOW huge_pages;" -c "SHOW huge_pages_status;"   # huge_pages_status: on/off — параметр появился в PostgreSQL 17 (release notes 17: «полезно, когда huge_pages = try»)
grep -E 'HugePages_(Total|Free|Rsvd)' /proc/meminfo     # Free уменьшился / Rsvd > 0 → страницы используются
```

Замечания:

- `huge_pages = try` скрывает ошибку: если страниц не хватило, сервер стартует на обычных, а зарезервированная память **простаивает** (она недоступна другим процессам). На продуктиве после отладки ставьте `on` либо контролируйте `huge_pages_status`.
- Huge pages работают только при `shared_memory_type = mmap` (по умолчанию) [PG].
- После изменения `shared_buffers`, `max_connections`, `max_locks_per_transaction`, `max_prepared_transactions` — пересчитать `vm.nr_hugepages`.
- Зарезервированные страницы **вычитаются из памяти, доступной остальным** (серверу 1С, файловому кешу) и из `CommitLimit`. На общем сервере 1С + PostgreSQL считайте баланс: RAM = huge pages (shared_buffers) + память backend-ов (`work_mem`, `temp_buffers` × соединения) + `rphost`/`rmngr` + файловый кеш.
- `vm.hugetlb_shm_group` и `ulimit -l` [PG]: документация говорит лишь, что «может также понадобиться» дать пользователю СУБД право на huge pages через `vm.hugetlb_shm_group` и/или право блокировать память через `ulimit -l`. [ядро]: `hugetlb_shm_group` — идентификатор группы, которой разрешено создавать **SysV**-сегменты разделяемой памяти на huge pages, то есть параметр относится к `shared_memory_type = sysv`; при `mmap` (по умолчанию) на практике не требуется (⚠ для `mmap` — вывод из описания параметра, прямо в [PG] не сказано).
- **Ubuntu 26.04 / ядро 7.0** [Canonical, release notes 26.04, «Changes since 25.10», известные проблемы]: изменение, появившееся в Linux 7.0, может вызывать существенную деградацию пропускной способности и рост задержек PostgreSQL; по обсуждению в списке рассылки ядра системы **с huge pages не затронуты**. Рекомендация Canonical — убедиться, что huge pages настроены и `huge_pages = on`. Для сервера СУБД 1С на 26.04 это переводит huge pages из «желательно при больших `shared_buffers`» в «обязательно проверить»: настройте резерв по шагам 1–3 даже при небольшом `shared_buffers` и контролируйте `SHOW huge_pages_status;`. Ссылки на обсуждение: lore.kernel.org/lkml/20260403191942.21410-1-dipiets@amazon.it/ (сами письма в ходе рецензии не читались; исправлено ли это в обновлениях ядра 26.04.1 — ⚠ не проверено).
- Страницы 1 ГБ (`huge_page_size = 1GB`): резервируются параметрами ядра `hugepagesz=1G hugepages=N`, нужен флаг CPU `pdpe1gb` (в ВМ часто недоступен). Для типичных серверов 1С выигрыш над 2 МБ невелик.
- ВМ с динамической памятью/balloon (Hyper-V Dynamic Memory и т. п.) плохо сочетается с huge pages: гостю нужна **статически выделенная** память [практика].

Ошибка запуска при `huge_pages = on` и нехватке страниц:

```text
FATAL:  could not map anonymous shared memory: Cannot allocate memory
HINT:  This error usually means that PostgreSQL's request for a shared memory segment exceeded
       available memory, swap space, or huge pages. ...
```

---

## 7. Энергосбережение CPU, tuned, параметры GRUB

### 7.1. Что требуют 1С и Postgres Pro

- [1С] (ИТС, «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2», публикация 19.06.2025): для сервера СУБД — 8–512 ГБ RAM, 4–256 ядер, RAID 0-1 или SSD; **отключить HyperThreading; отключить Energy Saving** (режим максимальной производительности).
- [PGPro] (приложение «Настройка Postgres Pro для решений 1С», раздел «Основные требования и конфигурация сервера»): отключить гиперпоточность; отключить режим энергосбережения — иначе задержки отклика БД «могут непредсказуемо вырастать»; отключить подкачку для разделяемой памяти.

В ВМ это задачи **хоста**: настройки BIOS/UEFI (профиль питания «Maximum Performance», C-states), схема электропитания Windows на хосте («Высокая производительность»: `powercfg /setactive SCHEME_MIN`, проверка `powercfg /getactivescheme`), отсутствие переподписки vCPU. Гостевая Ubuntu частотой процессора обычно не управляет.

### 7.2. cpupower и governor (физический сервер)

Установка [практика]: утилита входит в `linux-tools`:

```bash
sudo apt install linux-tools-common linux-tools-$(uname -r)    # или linux-tools-generic
```

```bash
cpupower frequency-info                   # драйвер (intel_pstate, amd-pstate-epp, acpi-cpufreq), governor, диапазон частот
cpupower -c all frequency-info | grep -E 'driver|governor'
sudo cpupower frequency-set -g performance      # governor performance на всех ядрах
sudo cpupower -c 0-7 frequency-set -g performance
cpupower idle-info                        # C-состояния
sudo cpupower monitor                     # фактические частоты и C-состояния
sudo cpupower monitor -i 60 -m Mperf      # усреднение за 60 с

# без cpupower — через sysfs:
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

- Governor-ы: `performance` (максимальная частота), `powersave`, а у драйвера `acpi-cpufreq` также `ondemand`, `conservative`, `schedutil`, `userspace`. У `intel_pstate`/`amd-pstate-epp` в активном режиме доступны только `performance` и `powersave`.
- `cpupower frequency-set` **не сохраняется после перезагрузки**. Закрепить: профиль tuned (7.3) или собственный oneshot-юнит:

```ini
# /etc/systemd/system/cpu-performance.service
[Unit]
Description=Set CPU governor to performance

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$f"; done'

[Install]
WantedBy=multi-user.target
```

- В ВМ типичный ответ `cpupower frequency-info`: `no or unknown cpufreq driver is active on this CPU` — это нормально, управлять нечем.

### 7.3. tuned

TuneD — демон, применяющий профиль (набор sysctl, governor, THP, readahead и т. д.) и откатывающий изменения при смене профиля. В Ubuntu пакет `tuned` находится в репозитории **universe** [Canonical]; при установке сразу применяется профиль по умолчанию: `virtual-guest` в ВМ, `throughput-performance` на вычислительных узлах, иначе `balanced`.

```bash
sudo apt install tuned
systemctl status tuned
tuned-adm list profiles                 # доступные профили
tuned-adm active                        # текущий
tuned-adm recommend                     # рекомендуемый для этой машины
sudo tuned-adm profile throughput-performance
sudo tuned-adm profile virtual-guest
sudo tuned-adm verify                   # проверить, что настройки профиля действуют
sudo tuned-adm off                      # отключить тюнинг
```

Полезные профили (содержимое по репозиторию tuned):

| Профиль | Что делает |
|---|---|
| `throughput-performance` | `[cpu]` governor `performance`, `energy_perf_bias=performance`, `min_perf_pct=100`, `energy_performance_preference=performance`, `boost=1`; порог «грязных» страниц 40 % / фоновый 10 %; `vm.swappiness=10`; `[disk] readahead=>4096`; `net.core.somaxconn=>2048` (знак `>` — «не меньше») |
| `latency-performance` | governor `performance` + запрет глубоких C-состояний |
| `virtual-guest` | наследует `throughput-performance`; порог «грязных» страниц 30 % (`vm.dirty_ratio=30` в старых версиях, `[vm] dirty_bytes = 30%` в актуальной), `vm.swappiness = 30` — подтверждено по репозиторию tuned |
| `postgresql` | наследует `throughput-performance`; `[cpu] force_latency=1`; `[vm] transparent_hugepages=never`; `dirty_background_bytes=67108864`, `dirty_bytes=536870912`; `vm.swappiness=3`; `kernel.sched_autogroup_enabled=0`; `[scheduler] sched_min_granularity_ns=10000000`, `sched_migration_cost_ns=50000000` |
| `balanced`, `powersave` | не для сервера СУБД |

Каталоги профилей (**исправлено рецензией** по спискам файлов пакета `tuned`): в **Ubuntu 22.04 и 24.04** раскладка плоская — `/usr/lib/tuned/<имя>/tuned.conf` и свои профили в `/etc/tuned/<имя>/`; в **Ubuntu 26.04** (новая версия tuned) — `/usr/lib/tuned/profiles/<имя>/tuned.conf` и свои в `/etc/tuned/profiles/<имя>/`; при обновлении пакета пользовательские профили переносятся в новое место [Canonical]. Профиль в `/etc` с тем же именем перекрывает системный. Профиль `postgresql` входит в пакет `tuned` Ubuntu 24.04 и 26.04 (для 22.04 список файлов не проверялся; вместе с `oracle`, `mssql`, `virtual-guest`, `virtual-host`, `throughput-performance`, `latency-performance` и др.). Проверка раскладки: `ls -d /usr/lib/tuned/profiles 2>/dev/null || ls /usr/lib/tuned`.

Замечание о синтаксисе: в актуальной ветке tuned пороги «грязных» страниц в профилях записаны через плагин `[vm]` (`dirty_bytes = 40%`, `dirty_background_bytes = 10%` в `throughput-performance`; `dirty_bytes = 30%` в `virtual-guest`), в старых версиях (22.04/24.04) — через `[sysctl]` (`vm.dirty_ratio = 40` / `30`, `vm.dirty_background_ratio = 10`). Смысл тот же: 40 %/10 % и 30 % соответственно. В своём профиле абсолютные значения в байтах надёжнее задавать через `[sysctl]`, как в примере ниже (работает во всех версиях).

Свой профиль для ВМ с 1С + PostgreSQL:

```bash
# Ubuntu 26.04:
sudo mkdir -p /etc/tuned/profiles/1c-postgres
sudoedit /etc/tuned/profiles/1c-postgres/tuned.conf
# Ubuntu 22.04 и 24.04:
sudo mkdir -p /etc/tuned/1c-postgres
sudoedit /etc/tuned/1c-postgres/tuned.conf
```

```ini
[main]
summary=1C:Enterprise server + PostgreSQL (VM)
include=virtual-guest

[vm]
transparent_hugepages=never

[sysctl]
vm.swappiness=10
vm.dirty_background_bytes=67108864
vm.dirty_bytes=536870912
kernel.sched_autogroup_enabled=0
```

```bash
sudo tuned-adm profile 1c-postgres
tuned-adm active && sudo tuned-adm verify
```

Важно: не дублируйте одни и те же параметры в tuned и в `/etc/sysctl.d/`. По умолчанию tuned после применения своих sysctl повторно применяет системные: в `/etc/tuned/tuned-main.conf` опция **`reapply_sysctl = 1`** (подтверждено по файлу в репозитории tuned: повторно применяются `/run/sysctl.d/`, `/etc/sysctl.d/` и `/etc/sysctl.conf`, чтобы tuned не перекрывал настройки администратора), то есть `sysctl.d` «побеждает». Отсюда две ловушки: (1) значение из профиля «не применяется», потому что тот же ключ есть в `/etc/sysctl.d/` (в Ubuntu ≤ 24.04 — в том числе в поставляемых `10-*.conf`); (2) `vm.swappiness=30` профиля `virtual-guest` молча действует в ВМ, если вы поставили tuned «просто посмотреть» и нигде не задали свой `vm.swappiness`. Выберите один механизм: либо tuned-профиль, либо `sysctl.d` + юнит для THP. Прочие умолчания `tuned-main.conf` в актуальной ветке репозитория: `daemon = 1`, `dynamic_tuning = 0` (только статическая настройка); в версиях из 22.04/24.04 значение `dynamic_tuning` могло быть иным — проверьте `grep -E '^(dynamic_tuning|reapply_sysctl)' /etc/tuned/tuned-main.conf`.

### 7.4. Параметры ядра в GRUB

- Файл: `/etc/default/grub`; дополнительные фрагменты — `/etc/default/grub.d/*.cfg` (читаются после основного файла и могут переопределять переменные; в cloud-образах это `50-cloudimg-settings.cfg`).
- `GRUB_CMDLINE_LINUX_DEFAULT` — параметры только для обычной загрузки; `GRUB_CMDLINE_LINUX` — для всех пунктов меню, включая recovery.
- После правки обязательно `sudo update-grub` (обёртка над `grub-mkconfig -o /boot/grub/grub.cfg`) и перезагрузка.

```bash
cat /proc/cmdline                         # с чем загружено ядро сейчас
grep -r CMDLINE /etc/default/grub /etc/default/grub.d/ 2>/dev/null
sudoedit /etc/default/grub
sudo update-grub && sudo reboot
```

Параметры, относящиеся к теме:

| Параметр | Назначение |
|---|---|
| `transparent_hugepage=never` | отключить THP с момента загрузки |
| `hugepagesz=2M hugepages=4300` | зарезервировать huge pages при загрузке (самый надёжный способ) |
| `default_hugepagesz=1G hugepagesz=1G hugepages=16` | страницы 1 ГБ |
| `intel_idle.max_cstate=1 processor.max_cstate=1` | запрет глубоких C-состояний (физический сервер, минимальные задержки) [практика] |
| `numa_balancing=disable` | отключить автобалансировку NUMA |
| `mitigations=off` | отключает защиты от уязвимостей CPU — **не рекомендуется**, только осознанно в изолированном контуре |

Пример строки:

```ini
GRUB_CMDLINE_LINUX_DEFAULT="transparent_hugepage=never"
```

---

## 8. Время и его синхронизация

### 8.1. Зачем это серверу 1С и PostgreSQL

- **Kerberos** (доменная аутентификация пользователей 1С, SSO в веб-клиенте): билеты содержат метки времени; при расхождении часов сервера и контроллера домена больше допустимого (в Active Directory по умолчанию 5 минут) аутентификация не работает. [1С] — это единственное место, где документация платформы прямо требует синхронизации времени: в руководстве «Клиент-серверный вариант» (гл. 3, настройка Kerberos для Linux-сервера, «Шаг 2. Синхронизация времени») и в методической статье ИТС сказано, что системные часы компьютеров, участвующих в аутентификации, не должны заметно расходиться, так как тикеты действуют ограниченное время; пример из документации — разовая команда `ntpdate main` (`main` — контроллер домена). `ntpdate` в современных Ubuntu заменяют постоянной службой: chrony с контроллером домена в качестве источника (раздел 8.4), разовая коррекция — `sudo chronyc makestep`.
- **Лицензии 1С (платформа 8.5.4 и новее)** — официальное требование [1С]: в методической статье ИТС № 6041 «Особенности лицензирования при переходе на версии платформы 1С:Предприятие 8.5.4» (30.04.2026; конспект — `kb/its-metod/licenzii-hasp-java-api-prochee-administrirovanie.md`) прямо сказано: **системное время на компьютерах Менеджера Лицензий (`rmlic`) и на компьютерах клиентских и серверных приложений платформы не должно отличаться больше чем на 20 минут**. Это условие работы нового механизма проверки лицензий, появившегося в 8.5.4: при большем расхождении приложение может не получить лицензию (диагностика — «Журнал поиска лицензии»). Для 8.3.x и 8.5.1 (HASP License Manager, программные лицензии старого механизма) такого требования в документации по защите и лицензированию (гл. 10 руководства администратора, конспекты `kb/its-docs/adm-gl10…`) не найдено — зависимость старых программных лицензий от системного времени официально не описана (⚠ отсутствие упоминания не доказывает отсутствие зависимости).
- **Кластер 1С из нескольких рабочих серверов**, журнал регистрации, технологический журнал, регламентные задания, блокировки сеансов по расписанию — всё опирается на системные часы; при разных часах на узлах разбор инцидентов по журналам становится невозможным [практика]. Отдельного количественного требования к расхождению времени именно между рабочими серверами кластера в конспектах документации 8.3.27 (`kb/its-docs/cs-gl*`) не найдено; фактические официальные пороги — 20 минут для лицензирования 8.5.4+ (выше) и допуск Kerberos (обычно 5 минут). Ориентируйтесь на самый жёсткий — а на практике держите расхождение в пределах секунды (chrony).
- Независимо от версии, резкие переводы часов назад на рабочем сервере недопустимы: ломается хронология журналов, расписания регламентных заданий, сроки действия токенов, сертификатов и тикетов.
- **TLS/сертификаты, OpenID Connect/JWT-токены, NTS**: проверка срока действия зависит от часов; при сильно неверном времени не устанавливаются HTTPS-соединения (включая сам NTS).
- **PostgreSQL**: журналы, `recovery_target_time` при восстановлении на момент времени, мониторинг задержки репликации.

### 8.2. timedatectl

```bash
timedatectl                              # = timedatectl status
#   Local time: ...   Universal time: ...   RTC time: ...
#   Time zone: Europe/Moscow (MSK, +0300)
#   System clock synchronized: yes
#   NTP service: active
#   RTC in local TZ: no
timedatectl show                         # то же в виде ключ=значение
timedatectl list-timezones | grep -iE 'moscow|tashkent'
sudo timedatectl set-timezone Europe/Moscow      # меняет симлинк /etc/localtime
sudo timedatectl set-timezone Asia/Tashkent
sudo timedatectl set-ntp true            # включить и запустить службу синхронизации
sudo timedatectl set-ntp false           # выключить (нужно перед ручной установкой времени)
sudo timedatectl set-time "2026-10-10 12:00:00"
sudo timedatectl set-local-rtc 0         # аппаратные часы в UTC (так и должно быть)
timedatectl timesync-status              # состояние systemd-timesyncd (сервер, смещение, интервал опроса)
timedatectl show-timesync --all
```

- Часовой пояс сервера должен соответствовать ожиданиям прикладного решения: сервер 1С берёт текущую дату/время сервера из ОС; PostgreSQL имеет свой параметр `timezone`.
- RTC держите в UTC: режим «RTC in local TZ» официально «не полностью поддерживается» [man timedatectl].
- Если установлен chrony, `timedatectl` по-прежнему управляет часовым поясом, а строка «NTP service: active» отражает работу chrony.

### 8.3. systemd-timesyncd (по умолчанию до Ubuntu 25.04 включительно)

Простой SNTP-клиент (только клиент, один источник за раз).

```bash
systemctl status systemd-timesyncd
# Status: "Synchronized to time server 185.125.190.56:123 (ntp.ubuntu.com)."
timedatectl timesync-status
```

Настройка — `/etc/systemd/timesyncd.conf` или drop-in в `/etc/systemd/timesyncd.conf.d/*.conf`:

```ini
# /etc/systemd/timesyncd.conf.d/10-local.conf
[Time]
NTP=dc01.corp.example.com dc02.corp.example.com
FallbackNTP=ntp.ubuntu.com
```

```bash
sudo systemctl restart systemd-timesyncd
```

Для сервера 1С/СУБД, а тем более в домене и в ВМ, предпочтительнее chrony: он точнее, умеет несколько источников, аппаратные часы гипервизора (PTP) и корректно ведёт себя после пауз ВМ.

### 8.4. chrony

**Ubuntu 22.04 / 24.04:**

```bash
sudo apt install chrony        # systemd-timesyncd при этом отключается/удаляется (конфликт пакетов time-daemon)
systemctl status chrony        # юнит называется chrony.service, демон — chronyd
```

**Ubuntu 25.10 / 26.04:** chrony установлен по умолчанию и работает как клиент **с NTS** (Network Time Security) [Canonical]:

- главный файл `/etc/chrony/chrony.conf`; источники — `/etc/chrony/sources.d/*.sources`; доп. конфигурация — `/etc/chrony/conf.d/*.conf`;
- источники по умолчанию — `/etc/chrony/sources.d/ubuntu-ntp-pools.sources`:

```text
pool 1.ntp.ubuntu.com iburst maxsources 1 nts prefer
pool 2.ntp.ubuntu.com iburst maxsources 1 nts prefer
pool 3.ntp.ubuntu.com iburst maxsources 1 nts prefer
pool 4.ntp.ubuntu.com iburst maxsources 1 nts prefer
pool ntp-bootstrap.ubuntu.com iburst maxsources 1 nts certset 1
```

- обмен ключами NTS (NTS-KE) идёт по **TCP 4460**, само время — по UDP 123. Если сеть блокирует NTS-серверы Ubuntu или нужные порты, chrony в конфигурации по умолчанию **не сможет** выставить время [Canonical];
- сопутствующие файлы [Canonical]: `/etc/chrony/conf.d/ubuntu-nts.conf` (настройки NTS), `/etc/chrony/nts-bootstrap-ubuntu.crt` (сертификат для начальной синхронизации с `ntp-bootstrap.ubuntu.com`; по смыслу директив chrony опция `certset 1` в последней строке источников выбирает отдельный набор доверенных сертификатов, заданный в `ubuntu-nts.conf` — ⚠ содержимое `ubuntu-nts.conf` в ходе рецензии не открывалось);
- вернуться к обычному NTP: в `/etc/chrony/sources.d/ubuntu-ntp-pools.sources` заменить NTS-источники обычными NTP-серверами (без опции `nts`) и выполнить `sudo chronyc reload sources` [Canonical];
- источники, полученные по DHCP (опция 42), подключаются директивой `sourcedir /run/chrony-dhcp` в `chrony.conf`; чтобы их игнорировать — закомментируйте её [Canonical];
- chrony по умолчанию ставится только на **новые** установки 25.10/26.04. При обновлении с 24.04 (и других выпусков с timesyncd) остаётся `systemd-timesyncd`; release notes 26.04 предлагают перейти вручную: `sudo apt-mark auto systemd-timesyncd && sudo apt install chrony` [Canonical]. Обратный переход: `sudo apt-mark auto chrony && sudo apt install systemd-timesyncd`.

Свои источники (внутренний NTP, контроллер домена) — отдельным файлом; файл по умолчанию закомментировать, если внешние серверы недоступны:

```bash
sudoedit /etc/chrony/sources.d/corp.sources
```

```text
server dc01.corp.example.com iburst prefer
server dc02.corp.example.com iburst
```

```bash
sudo sed -i 's/^pool /#pool /' /etc/chrony/sources.d/ubuntu-ntp-pools.sources   # отключить источники Ubuntu (26.04)
sudo chronyc reload sources          # перечитать *.sources без перезапуска
sudo systemctl restart chrony        # после правки chrony.conf / conf.d
```

В 22.04/24.04 каталоги `sources.d`/`conf.d` тоже подключены в `chrony.conf` директивами `confdir /etc/chrony/conf.d`, `sourcedir /run/chrony-dhcp`, `sourcedir /etc/chrony/sources.d` — так устроен `chrony.conf` пакета Debian (проверено по исходникам chrony для bookworm: там же `driftfile /var/lib/chrony/chrony.drift`, `ntsdumpdir /var/lib/chrony`, `logdir /var/log/chrony`, `maxupdateskew 100.0`, `rtcsync`, `makestep 1 3`, `leapsectz right/UTC`); пакет Ubuntu наследует эту раскладку, но с пулами Ubuntu (⚠ сам файл Ubuntu 22.04/24.04 в ходе рецензии не открывался: `grep -E '^(sourcedir|confdir|pool|server)' /etc/chrony/chrony.conf`). Источники по умолчанию в 22.04/24.04 записаны прямо в `/etc/chrony/chrony.conf` строками `pool ...`.

Диагностика:

```bash
chronyc sources -v        # источники; первый столбец: ^* выбран, ^+ годен/комбинируется, ^- отброшен, ^? недоступен, ^x «лжец»
chronyc sourcestats       # статистика по источникам (смещение, дрейф)
chronyc tracking          # итог: Reference ID, Stratum, System time (смещение), Last offset, Leap status
chronyc activity          # сколько источников онлайн
sudo chronyc -N authdata  # NTS: Mode должен быть NTS, ненулевые KeyID/KLen
sudo chronyc makestep     # немедленно «прыжком» исправить часы (после больших расхождений)
chronyd -Q                # разово опросить источники и показать смещение, НЕ меняя часы (-q — то же, но выставить часы и выйти)
```

Про `chronyd -Q` [документация chrony]: режим «как `-q`, но только печатает смещение без коррекции часов» и отключает серверные порты, поэтому может запускаться без root, если в конфигурации нет директив, требующих привилегий (`refclock`, `hwtimestamp`, `rtcfile`). При уже работающей службе `chrony` второй экземпляр может отказаться стартовать из-за занятого pid-файла (⚠ не проверено) — на рабочем сервере достаточно `chronyc tracking` и `chronyc sources -v`.

Как читать `chronyc sources`: столбец `Reach` — восьмеричная маска последних 8 опросов (`377` = все успешны, `0` = источник недоступен); `Last sample` — смещение. В `chronyc tracking` важны `Leap status : Normal` и малое значение `System time`.

Полезные директивы `chrony.conf`:

| Директива | Смысл |
|---|---|
| `makestep 1 3` | если расхождение > 1 с, исправить скачком, но только в первые 3 обновления после старта |
| `makestep 1.0 -1` | исправлять скачком всегда (рекомендация Microsoft для ВМ на Hyper-V) |
| `rtcsync` | периодически копировать системное время в аппаратные часы |
| `driftfile /var/lib/chrony/chrony.drift` | файл дрейфа |
| `allow 10.0.0.0/8` | разрешить клиентам сети получать время (режим сервера) |
| `refclock PHC /dev/ptp_hyperv ...` | аппаратные часы гипервизора как источник |

### 8.5. Время в виртуальной машине

Часы гостя «плывут» сильнее, чем на железе, и скачут после паузы, снимка, живой миграции, восстановления ВМ.

**Hyper-V (в том числе на Windows-хосте)** [Microsoft]:

- служба интеграции «Синхронизация времени» работает через модуль ядра `hv_utils` (в стандартном ядре Ubuntu). Сама по себе она корректирует время гостя после пауз, но не ведёт постоянной синхронизации;
- тот же механизм создаёт PTP-устройство; udev создаёт симлинк `/dev/ptp_hyperv`. Рекомендуемая конфигурация — chrony с этим источником:

```bash
lsmod | grep hv_utils
ls /sys/class/ptp && cat /sys/class/ptp/ptp0/clock_name     # должно быть: hyperv
ls -l /dev/ptp_hyperv
```

```text
# /etc/chrony/conf.d/hyperv.conf
refclock PHC /dev/ptp_hyperv poll 3 dpoll -2 offset 0 stratum 2
makestep 1.0 -1
```

```bash
sudo systemctl restart chrony && chronyc sources -v     # появится источник PHC0 с меткой #*
```

- сам Windows-хост должен быть синхронизирован (`w32tm /query /status`), иначе гость будет точно следовать неверному времени хоста. В домене хост и гость должны в итоге сходиться к одному источнику — эмулятору PDC.
- Если сервер 1С введён в домен и важна согласованность именно с контроллером домена, используйте **один** основной источник (DC по NTP) и не смешивайте его с расходящимся временем хоста.

**VMware** [Broadcom/VMware KB 1006427 «Timekeeping best practices for Linux guests»]: «VMware recommends using NTP instead of VMware Tools periodic time synchronization»; периодическая синхронизация через Tools **по умолчанию выключена** и при работающем NTP в госте должна такой и оставаться (часы должен вести один механизм); разовая коррекция времени Tools после событий вроде возобновления/снимка включена по умолчанию и рекомендована. Для `ntpd` KB советует `tinker panic 0` и не использовать локальные часы как источник; про chrony отдельных настроек в KB нет ([практика]: `makestep 1 -1`, чтобы большие скачки после паузы ВМ исправлялись всегда). Пакет гостя — `open-vm-tools`; управление периодической синхронизацией — `vmware-toolbox-cmd timesync status|enable|disable` (⚠ команда приведена по памяти, в прочитанной статье KB её нет — она в соседней статье «Disabling Time Synchronization»).

**VirtualBox** [руководство VirtualBox, «Tuning the Guest Additions Time Synchronization Parameters»]: служба `VBoxService` из Guest Additions синхронизирует время гостя с хостом; параметры (задаются `VBoxManage guestproperty set "<ВМ>" "/VirtualBox/GuestAdd/VBoxService/--timesync-..." <значение>` или ключами `VBoxService`): `--timesync-interval` (по умолчанию 10 с), `--timesync-min-adjust` (100 мс), `--timesync-latency-factor` (8), `--timesync-max-latency` (250 мс), `--timesync-set-threshold` (20 минут — при большем расхождении время выставляется скачком, а не подводится плавно), `--timesync-set-start`, `--timesync-set-on-restore` (по умолчанию 1). Полностью отключить чтение времени хоста гостем: `VBoxManage setextradata "<ВМ>" "VBoxInternal/Devices/VMMDev/0/Config/GetHostTimeDisabled" 1`. Правило «один механизм» остаётся: либо Guest Additions, либо chrony (для сервера в домене — chrony с DC, а синхронизацию Guest Additions отключить; последнее — [практика]).

**KVM**: при загруженном модуле `ptp_kvm` udev создаёт симлинк `/dev/ptp_kvm` (правило systemd `50-udev-default.rules`: `SUBSYSTEM=="ptp", ATTR{clock_name}=="KVM virtual PTP", SYMLINK+="ptp_kvm"`; там же правило для `hyperv` → `ptp_hyperv`). Источник для chrony: `refclock PHC /dev/ptp_kvm poll 2` (⚠ конкретные опции строки — по памяти из документации RHEL; сам симлинк подтверждён) либо обычный NTP. Проверка: `lsmod | grep ptp_kvm; ls -l /dev/ptp*; cat /sys/class/ptp/ptp0/clock_name`.

Общее правило: ровно **один** механизм, двигающий часы (chrony *или* timesyncd *или* агент гипервизора).

---

## 9. Локали

### 9.1. Команды

```bash
locale                      # текущие LANG, LC_* (для этой сессии)
locale -a                   # все сгенерированные (доступные) локали
locale -a | grep -i ru_RU   # ru_RU.utf8 — так выводится ru_RU.UTF-8
localectl status            # системная локаль и раскладка

sudo locale-gen ru_RU.UTF-8                 # сгенерировать локаль
sudo locale-gen ru_RU.UTF-8 en_US.UTF-8     # несколько сразу
sudo update-locale LANG=ru_RU.UTF-8         # сделать системной по умолчанию (вступит в силу при новом входе)
sudo update-locale LANG=en_US.UTF-8 LC_MESSAGES=en_US.UTF-8   # пример: система на английском
sudo update-locale LC_ALL                   # имя без значения — удалить переменную из файла
sudo dpkg-reconfigure locales               # интерактивно: выбрать генерируемые локали и локаль по умолчанию
sudo localectl set-locale LANG=ru_RU.UTF-8  # эквивалент через systemd
sudo apt install language-pack-ru           # переводы сообщений программ + генерация ru_RU.UTF-8
```

Файлы:

| Файл | Назначение |
|---|---|
| `/etc/locale.gen` | список локалей для генерации (`ru_RU.UTF-8 UTF-8`) |
| `/var/lib/locales/supported.d/` | фрагменты от пакетов `language-pack-*` (вручную не править) |
| `/usr/share/i18n/SUPPORTED` | все локали, которые умеет glibc |
| `/usr/lib/locale/locale-archive` | скомпилированные локали |
| `/etc/default/locale` | системные переменные локали в 22.04 [man update-locale, jammy] |
| `/etc/locale.conf` | то же в 24.04 и 26.04 [man update-locale, noble/resolute]. Переход сделан в glibc Debian 2.37-6 («Switch from /etc/default/locale to /etc/locale.conf»); `postinst` пакета `locales` переносит старый `/etc/default/locale` в `/etc/locale.conf` и создаёт симлинк `/etc/default/locale → locale.conf` (проверено по исходникам пакета glibc Debian; Ubuntu 24.04+ наследует — на своей системе: `ls -l /etc/default/locale /etc/locale.conf`). Поэтому `pam_env ... envfile=/etc/default/locale` в `/etc/pam.d/*` и скрипты `postgresql-common` продолжают работать |

`sudo locale-gen --keep-existing` — не пересобирать уже существующие локали (единственная опция, описанная в man-странице `locale-gen` для noble/resolute).

**Про `locale-gen <имя локали>`.** Форма с аргументом (`sudo locale-gen ru_RU.UTF-8`) — исторически особенность сценария **Ubuntu**; в Debian `locale-gen` аргументы-локали не принимает (читает только `/etc/locale.gen` — проверено по исходникам Debian), и man-страницы Ubuntu 22.04/24.04/26.04 описывают только чтение `/etc/locale.gen`. На Ubuntu 22.04/24.04 форма с аргументом на практике работает (её же использует методическая статья ИТС о сборке PostgreSQL: `locale-gen en_US.UTF-8 ru_RU.UTF-8`); для 26.04 — ⚠ не проверено. Универсальный способ, работающий везде:

```bash
sudo sed -i 's/^# *\(ru_RU.UTF-8 UTF-8\)/\1/; s/^# *\(en_US.UTF-8 UTF-8\)/\1/' /etc/locale.gen
grep -E '^(ru_RU|en_US)' /etc/locale.gen      # обе строки должны быть раскомментированы
sudo locale-gen
locale -a | grep -Ei 'ru_RU|en_US'            # ru_RU.utf8, en_US.utf8
```

После любого способа обязательно проверяйте результат `locale -a | grep -i ru_RU` — это единственный надёжный признак, что локаль доступна `initdb` и серверу 1С.

### 9.2. Переменные

| Переменная | Что определяет |
|---|---|
| `LANG` | значение по умолчанию для всех категорий |
| `LC_COLLATE` | порядок сортировки строк |
| `LC_CTYPE` | классификация символов, регистр |
| `LC_MESSAGES` | язык сообщений |
| `LC_NUMERIC`, `LC_MONETARY`, `LC_TIME` | форматы чисел, денег, дат |
| `LC_ALL` | **переопределяет всё**, включая `LANG` и отдельные `LC_*`; для постоянной настройки не использовать |
| `LANGUAGE` | список языков для переводов сообщений (gettext) |

Приоритет: `LC_ALL` → конкретная `LC_*` → `LANG` → `C`. В минимальных образах и контейнерах есть только `C`, `C.utf8`, `POSIX`.

### 9.3. Почему `ru_RU.UTF-8` нужна до initdb и до установки 1С

1. [PG]: `initdb` берёт локаль из окружения (`LC_ALL` → `LC_COLLATE`/… → `LANG`, иначе `C`) либо из `--locale`; локаль должна существовать в ОС (`locale -a`). **`LC_COLLATE` и `LC_CTYPE` фиксируются при создании базы** — от них зависит порядок в индексах, изменить их потом нельзя (только создать новую базу/кластер).
2. [PGPro], «Настройка Postgres Pro для решений 1С», раздел «Настройка локали»: перед созданием кластера убедиться, что русская локаль установлена и является активной у пользователя, создающего кластер:

```bash
sudo dpkg-reconfigure locales
export LANG="ru_RU.UTF-8"
/opt/pgpro/ent-17/bin/pg-setup initdb      # путь из документации для Postgres Pro Enterprise 17
```

3. Пакет `postgresql` в Ubuntu (как и пакеты PGDG — общий `postgresql-common`) при установке **автоматически создаёт кластер `main`**. Локаль для него берётся не из окружения администратора, а из **системных настроек** (проверено по исходникам `postgresql-common` 278, `debian/maintscripts-functions`): функция `set_system_locale` сначала сбрасывает все `LANG`/`LC_*` (комментарий в коде: ssh и sudo могут протащить локаль удалённого пользователя), ставит запасное `LANG=C.UTF-8`, затем читает значения через `pam_getenv -l` и из `/etc/default/locale`, после чего вызывается `pg_createcluster -u postgres <версия> main`. Следствия:
   - если `update-locale LANG=ru_RU.UTF-8` не выполнен **до** `apt install postgresql…`, кластер получится в текущей системной локали (обычно `en_US.UTF-8` или `C.UTF-8`), даже если в вашем терминале `LANG=ru_RU.UTF-8`;
   - если системная локаль русская, но не сгенерирована (`locale -a` её не показывает), создание кластера завершится ошибкой;
   - при ручном `pg_createcluster` без `--locale` используется уже окружение вызывающего (скрипт проверяет его `setlocale(LC_ALL, "")`) — поэтому всегда указывайте `--locale ru_RU.UTF-8` явно;
   - автосоздание отключается параметром `create_main_cluster = false` в `/etc/postgresql-common/createcluster.conf` (скрипт проверяет именно его).
4. [1С] официальное условие (руководство «Клиент-серверный вариант», 3.2.5.1, документация 8.3.27; в 8.5.1 формулировка сохранена): работа возможна с кластером PostgreSQL «при совпадении национальных установок (locale) кластера и создаваемой информационной базы»; в примере документации кластер инициализируется с `LANG=ru_RU.utf-8`, кодировка — `UTF-8`. Локаль создаваемой базы определяется параметром «Язык (Страна)» информационной базы (у `ibcmd infobase create` — `--locale`, по умолчанию код локализации текущего сеанса ОС). [практика] Если кластер инициализирован в другой локали, создание базы из 1С завершается ошибкой PostgreSQL вида `ERROR: new collation (ru_RU.UTF-8) is incompatible with the collation of the template database (en_US.UTF-8)` с подсказкой `HINT: Use the same collation as in the template database, or use template0 as template.` (текст сообщения — из исходного кода PostgreSQL; что 1С получает именно его — по сообщениям форумов, ⚠ первоисточником 1С не подтверждено), а при отсутствии локали в ОС — `invalid locale name: "ru_RU.UTF-8"` (PostgreSQL ≤ 15) или `invalid LC_COLLATE locale name: "ru_RU.UTF-8"` (16+; формулировки и граница версий уточнены 11.10.2026 по исходному коду `dbcommands.c` веток 14–18: до 15-й включительно — `invalid locale name`, с 16-й — `invalid LC_COLLATE locale name` и `invalid LC_CTYPE locale name`; ранее: точные формулировки по памяти).
5. Серверу 1С локаль UTF-8 нужна для корректной работы с кириллицей в именах файлов, сообщениях, сортировке; генерируйте её до установки пакетов платформы и до первого запуска службы. Явного требования «сгенерировать ru_RU.UTF-8 до установки сервера» в прочитанных главах документации 8.3.27 (установка, запуск компонентов) нет — это [практика]; официально зафиксированы только совпадение locale кластера СУБД и базы (п. 4) и требование Postgres Pro (п. 2). Служба systemd получает локаль не из вашего сеанса: если серверу 1С нужна конкретная локаль процесса, её задают в drop-in юнита (`Environment=LANG=ru_RU.UTF-8`) — ⚠ какую локаль выставляет штатный юнит 1С, не проверено (`systemctl show srv1cv8-<версия>@default -p Environment`).

Правильная последовательность на чистом сервере:

```bash
sudo locale-gen ru_RU.UTF-8 en_US.UTF-8          # или универсальный способ через /etc/locale.gen (раздел 9.1)
sudo update-locale LANG=ru_RU.UTF-8
locale -a | grep -Ei 'ru_RU|en_US'               # ru_RU.utf8 обязана быть в списке
cat /etc/default/locale                          # LANG=ru_RU.UTF-8 — именно это прочитает пакет PostgreSQL при создании кластера main
# выйти и войти заново (или перезагрузиться), проверить: locale
# только после этого: установка PostgreSQL и платформы 1С
# сразу после установки PostgreSQL убедиться:
pg_lsclusters
sudo -u postgres psql -Atc "SELECT datname, datcollate, datctype FROM pg_database;"   # везде ru_RU.UTF-8
```

Если системную локаль хочется оставить английской (сообщения утилит на английском удобнее искать), действуйте иначе: сгенерируйте `ru_RU.UTF-8`, **не** меняя `LANG`; до установки PostgreSQL отключите автосоздание кластера (`create_main_cluster = false`), а кластер создайте вручную с `--locale ru_RU.UTF-8`:

```bash
sudo locale-gen ru_RU.UTF-8
sudo apt install postgresql-common        # только общий пакет: появляется createcluster.conf, кластер ещё не создаётся
sudo sed -i 's/^#\?create_main_cluster.*/create_main_cluster = false/' /etc/postgresql-common/createcluster.conf
grep create_main_cluster /etc/postgresql-common/createcluster.conf     # create_main_cluster = false
sudo apt install postgresql-17            # пример имени пакета; для сборок 1С/Postgres Pro — свои пакеты
sudo pg_createcluster --locale ru_RU.UTF-8 17 main --start
pg_lsclusters
```

(Порядок «сначала `postgresql-common`, потом правка `createcluster.conf`, потом сервер» выбран намеренно: заранее созданный вручную `createcluster.conf` может вызвать вопрос о замене конфигурационного файла при установке пакета. Скрипт пакета считает автосоздание выключенным при значении `false`/`off`. Для Postgres Pro этот механизм не применяется — там кластер создаёт `pg-setup initdb` с локалью из окружения, см. п. 2.)

Если кластер уже создан не с той локалью (данных ещё нет):

```bash
pg_lsclusters
sudo -u postgres psql -c "SELECT datname, datcollate, datctype FROM pg_database;"
sudo pg_dropcluster --stop 17 main
sudo pg_createcluster --locale ru_RU.UTF-8 17 main --start
```

Чтобы пакет не создавал кластер автоматически: в `/etc/postgresql-common/createcluster.conf` задать `create_main_cluster = false` до установки, затем создать кластер вручную с нужной локалью.

Системную `LANG` при этом не обязательно делать русской: достаточно, чтобы локаль была **сгенерирована**, а кластер создан с явным `--locale ru_RU.UTF-8`. Английские сообщения PostgreSQL удобнее для поиска — `lc_messages = 'en_US.UTF-8'` в `postgresql.conf` (эту категорию можно менять в любой момент [PG]).

### 9.4. Смена версии glibc и порядок сортировки

Суть [PG wiki, «Locale data changes»]: PostgreSQL для локалей провайдера `libc` использует сортировку из glibc. В **glibc 2.28** (2018) данные локалей были масштабно обновлены, и порядок сортировки изменился практически для всех локалей. Индексы B-tree по текстовым столбцам, построенные на старом порядке, после перехода на новую glibc становятся логически повреждёнными: запросы не находят существующие строки, уникальные индексы пропускают дубликаты; секционирование по диапазону текстового ключа раскладывает строки не в те секции.

- Граница для Ubuntu: до 18.04 включительно — старые данные, с 18.10 — новые; Debian: 8–9 старые, 10 новые.
- Более новые выпуски glibc (2.35 → 2.39 → 2.43 в 22.04 → 24.04 → 26.04) также могут менять отдельные правила; PostgreSQL использует **номер версии glibc как «версию правила сортировки»** [PG] и при несовпадении выдаёт предупреждение.

Кто под ударом [PG wiki]:

| Сценарий | Риск |
|---|---|
| Обновление ОС «на месте» (`do-release-upgrade`) с сохранением каталога данных | **да** |
| Перенос диска/каталога данных, восстановление файловой копии (`pg_basebackup`, снимок ВМ, копия `PGDATA`) на более новую ОС | **да** |
| Физическая (потоковая) репликация между серверами с разными версиями ОС | **да** |
| `pg_upgrade` на новой ОС | **да** |
| `pg_dump` / `pg_restore`, выгрузка/загрузка `.dt` из 1С, логическая репликация | нет |

Проверка, изменился ли порядок (выполнить на старой и новой ОС, сравнить):

```bash
( echo "1-1"; echo "11" ) | LC_COLLATE=en_US.UTF-8 sort
( echo "1-1"; echo "11" ) | LC_COLLATE=ru_RU.UTF-8 sort
ldd --version | head -1          # версия glibc
```

(В Ubuntu 26.04 `sort` — из rust-coreutils; он может сортировать не средствами glibc, поэтому для чистоты сравнения используйте GNU-вариант. По release notes 26.04 GNU-утилиты вызываются с префиксом `gnu` — пример оттуда `gnuls`; для sort это `gnusort` (⚠ имя выведено по правилу из release notes, на живой системе не проверено: `command -v gnusort`). Надёжнее спросить сам PostgreSQL: `SELECT pg_collation_actual_version(oid), collversion FROM pg_collation WHERE collname = 'ru_RU.utf8' OR collname = 'ru-RU-x-icu';` и `SELECT datname, datcollversion, pg_database_collation_actual_version(oid) FROM pg_database;` (второй запрос — PostgreSQL 15+) — расхождение столбцов означает смену версии библиотеки сортировки.)

Что покажет PostgreSQL (15+ — для базы; пример сообщения по документации `ALTER COLLATION`):

```text
WARNING:  collation "xx-x-icu" has version mismatch
DETAIL:  The collation in the database was created using version 1.2.3.4, but the operating system provides version 2.3.4.5.
HINT:  Rebuild all objects affected by this collation and run ALTER COLLATION pg_catalog."xx-x-icu" REFRESH VERSION, or build PostgreSQL with the right library version.
```

Для правила сортировки базы по умолчанию аналогичное предупреждение выдаётся при подключении к базе (PostgreSQL 15+), исправляется командой `ALTER DATABASE ... REFRESH COLLATION VERSION`. Вид сообщения (по исходному коду PostgreSQL; сверено дословно 11.10.2026 с `postinit.c` ветки 18; ранее: дословно в ходе рецензии не сверялось — ищите по словам `collation version mismatch`):

```text
WARNING:  database "ut" has a collation version mismatch
DETAIL:  The database was created using collation version 2.35, but the operating system provides version 2.39.
HINT:  Rebuild all objects in this database that use the default collation and run ALTER DATABASE ut REFRESH COLLATION VERSION, or build PostgreSQL with the right library version.
```

Здесь «2.35» и «2.39» — версии glibc Ubuntu 22.04 и 24.04: для провайдера `libc` PostgreSQL записывает как версию правила сортировки именно номер версии glibc. Клиент 1С это предупреждение пользователю не показывает — его видно в журнале PostgreSQL и при подключении через `psql`.

Лечение после смены ОС/glibc:

```bash
# 1) перестроить индексы во всех базах (на время перестроения — нагрузка и блокировки)
sudo -u postgres reindexdb --all --jobs=4
#    или по одной базе без длительных блокировок:
sudo -u postgres reindexdb --concurrently -d имя_базы

# 2) обновить записанную версию правила сортировки в каждой базе (включая postgres и template1)
sudo -u postgres psql -d имя_базы -c 'ALTER DATABASE "имя_базы" REFRESH COLLATION VERSION;'
```

Запрос из документации для поиска объектов, зависящих от устаревших правил сортировки:

```sql
SELECT pg_describe_object(refclassid, refobjid, refobjsubid) AS "Collation",
       pg_describe_object(classid, objid, objsubid) AS "Object"
  FROM pg_depend d JOIN pg_collation c
       ON refclassid = 'pg_collation'::regclass AND refobjid = c.oid
  WHERE c.collversion <> pg_collation_actual_version(c.oid)
  ORDER BY 1, 2;
```

Важно: `REFRESH COLLATION VERSION` лишь убирает предупреждение — **он не проверяет**, что индексы перестроены [PG]. Сначала `REINDEX`, потом `REFRESH`.

Особенность 1С: строки в базах 1С хранятся в типах `mchar`/`mvarchar` (расширение `mchar`). [PGPro] (документация Postgres Pro, модуль `mchar`): «Эти типы используют библиотеку ICU для сравнения строк и преобразования регистра» — то есть порядок в B-tree-индексах по таким столбцам определяет **ICU, а не glibc** (операторы `<`, `<=`, `=`, `>=`, `>` — без учёта регистра, `&<`, `&=` и т. д. — с учётом; есть поддержка B-деревьев и хеш-индексов). Что из этого следует:

- механизм версий правил сортировки PostgreSQL (`collversion`, предупреждения выше) отслеживает объекты `pg_collation` и правило сортировки базы; о типах `mchar`/`mvarchar` документация модуля в этом контексте ничего не говорит, предупреждений о смене версии ICU для них не описано — считайте, что **их нет** (⚠ это вывод из устройства расширения и молчания документации, прямого подтверждения нет);
- при смене мажорной версии ОС меняется версия системной `libicu` (у каждого выпуска Ubuntu свой soname); сборки Postgres Pro и сборки PostgreSQL от 1С могут быть слинкованы как с системной ICU, так и с собственной — ⚠ не проверено, смотрите `ldd $(pg_config --pkglibdir)/mchar.so | grep -i icu` на старой и новой системе;
- [PG wiki] отдельно отмечает, что столбцы с правилами сортировки провайдера ICU не затронуты изменением данных glibc — у них собственная «ось» изменений (версия ICU).

Поэтому после любого мажорного обновления ОС под сервером СУБД 1С (а также после замены пакета сборки PostgreSQL на собранный с другой ICU) **перестраивайте все индексы безусловно** либо переносите базы логически — отсутствие предупреждения о `collation version mismatch` для баз 1С ничего не гарантирует.

Практическая рекомендация: мажорное обновление ОС сервера СУБД делать не `do-release-upgrade`, а развёртыванием новой ВМ и переносом баз через `pg_dump`/`pg_restore` (или `.dt`); реплики и резервные серверы держать на той же версии ОС, что и основной.

---

## 10. Шрифты для сервера 1С

### 10.1. Зачем

Сервер 1С формирует табличные документы и печатные формы на своей стороне (фоновые и регламентные задания, веб-клиент, сохранение в PDF, расчёт автовысоты строк и ширины колонок). Для этого ему нужны те же шрифты, под которые свёрстаны макеты (Arial, Times New Roman, Courier New и др.). Без них fontconfig подставляет другие шрифты — «плывёт» вёрстка, обрезается текст, меняется разбиение на страницы. [1С] (ИТС, «Установка программы 1С:Предприятие 8 на Linux») прямо включает в процедуру установки шаг:

```bash
apt-get -y install ttf-mscorefonts-installer
fc-cache -fv
```

и дополнительные библиотеки (в статье — для 8.3.13.1644 и Ubuntu Server 16.04): `apt-get install libfreetype6 libgsf-1-common unixodbc glib2.0`. Актуальный перечень зависимостей для вашей версии платформы смотрите в документации администратора соответствующей версии.

Что говорит документация платформы 8.3.27 [1С] (руководство администратора, 2.8.1.1 «Установка шрифтов» и описание программы установки; конспекты `kb/its-docs/adm-gl02-ustanovka-p1.md`, `adm-gl02-ustanovka-p2.md`):

- «для корректной работы "1С:Предприятия" в Linux должны быть установлены шрифты из набора **Microsoft Core Fonts**»;
- варианты: пакет из состава дистрибутива ОС (в Ubuntu это `ttf-mscorefonts-installer`; имя пакета документация не называет); вручную — скачать файлы шрифтов с `https://sourceforge.net/projects/corefonts/files/the%20fonts/final/`, распаковать и положить в каталог **`~/.fonts` пользователя, от имени которого запускается «1С:Предприятие»** (для сервера — домашний каталог `usr1cv8`, т. е. `/home/usr1cv8/.fonts`);
- программа установки платформы (`.run`, в том числе в пакетном режиме) **сама пытается поставить** Microsoft Core Fonts for Web: ищет уже установленный пакет, затем официальный репозиторий ОС, затем зеркала SourceForge по HTTP — на сервере без доступа в интернет этот шаг не сработает, шрифты надо ставить заранее/вручную;
- после установки некоторых шрифтов может понадобиться перезагрузка компьютера, на котором шрифт используется (серверного — если шрифт использует сервер).

### 10.2. Установка ttf-mscorefonts-installer

Пакет находится в компоненте **multiverse** и при установке **скачивает шрифты из интернета** (SourceForge), показывая диалог принятия лицензии (EULA).

```bash
# компонент multiverse должен быть включён (на Ubuntu Server обычно включён; если нет):
sudo add-apt-repository -y multiverse && sudo apt update

# интерактивно (Tab → OK, затем Yes):
sudo apt install ttf-mscorefonts-installer

# без диалога (скрипты, Ansible, cloud-init):
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ttf-mscorefonts-installer

sudo fc-cache -fv
fc-list | grep -iE 'arial|times new roman|courier new|verdana' | head
ls /usr/share/fonts/truetype/msttcorefonts/
```

- Принятие EULA через `debconf-set-selections` — это юридически значимое согласие с лицензией Microsoft; делайте его осознанно.
- Вопрос `msttcorefonts/accepted-mscorefonts-eula` — особенность пакета **Ubuntu** (multiverse): в шаблонах debconf пакета Debian (проверено по исходникам `msttcorefonts` в unstable) есть только `msttcorefonts/dldir`, `baddldir`, `savedir`, `dlurl`, `http_proxy`, диалога EULA там нет. Сам ключ для Ubuntu в ходе рецензии по исходникам пакета Ubuntu не открывался (⚠), но это общеупотребительная форма; проверить, что ответ записан: `sudo debconf-show ttf-mscorefonts-installer`.
- Полезные вопросы того же пакета для закрытого контура: `msttcorefonts/dldir` — каталог, где уже лежат заранее скачанные архивы шрифтов (тогда загрузка из интернета не нужна), `msttcorefonts/http_proxy` — прокси для загрузки. Пример: `echo "ttf-mscorefonts-installer msttcorefonts/dldir string /opt/distr/corefonts" | sudo debconf-set-selections` (⚠ работа `dldir` на конкретном выпуске не проверялась).
- Состав Core Fonts: Andale Mono, Arial, Arial Black, Comic Sans MS, Courier New, Georgia, Impact, Times New Roman, Trebuchet MS, Verdana, Webdings. **Tahoma, Calibri, Cambria, Segoe UI в набор не входят** — если макеты используют их, шрифты копируют вручную с лицензионной Windows.
- Если при установке не было доступа в интернет, пакет числится установленным, а шрифтов нет. Повторить загрузку: `sudo apt install --reinstall ttf-mscorefonts-installer` или `sudo dpkg-reconfigure ttf-mscorefonts-installer`.

Ручная установка шрифтов (в том числе в закрытом контуре):

```bash
sudo mkdir -p /usr/local/share/fonts/windows
sudo cp /путь/к/*.ttf /usr/local/share/fonts/windows/
sudo chmod 644 /usr/local/share/fonts/windows/*
sudo fc-cache -fv
```

### 10.3. fontconfig

```bash
sudo apt install fontconfig
fc-list                              # все шрифты: файл: семейство:стиль
fc-list : family | sort -u           # только названия семейств
fc-list :lang=ru family | sort -u    # шрифты с кириллицей
fc-match Arial                       # какой файл реально подставится по запросу "Arial"
fc-match "Times New Roman"
fc-cache -fv                         # пересобрать кеш (-f принудительно, -v подробно)
```

Каталоги шрифтов: `/usr/share/fonts/` (пакеты), `/usr/local/share/fonts/` (ручная установка для всех), `~/.local/share/fonts/` и устаревший `~/.fonts/` (для пользователя; для сервера 1С это домашний каталог `usr1cv8`). Конфигурация — `/etc/fonts/fonts.conf`, `/etc/fonts/conf.d/`.

Проверка: если `fc-match Arial` отвечает `LiberationSans-Regular.ttf` или `DejaVuSans.ttf` — настоящего Arial нет, идёт подстановка.

После установки шрифтов **перезапустите сервер 1С** (рабочие процессы читают список шрифтов при старте) [практика].

Свободные метрически совместимые замены [практика]: `fonts-liberation` (Arial, Times New Roman, Courier New), `fonts-crosextra-carlito` (Calibri), `fonts-crosextra-caladea` (Cambria) — совпадают по ширине символов, но не по начертанию.

---

## 11. Безопасность

### 11.1. AppArmor

AppArmor — система мандатного контроля доступа, в Ubuntu установлена и включена по умолчанию [Canonical]. Профиль привязан к пути исполняемого файла и перечисляет, что программе разрешено.

Режимы профиля:

- **enforce** — нарушения блокируются и журналируются;
- **complain** — нарушения разрешаются, но журналируются (режим обучения/отладки);
- процесс без профиля — **unconfined**.

```bash
sudo aa-status                     # = sudo apparmor_status: загруженные профили, режимы, процессы
sudo apt install apparmor-utils    # aa-complain, aa-enforce, aa-genprof, aa-logprof
sudo apt install apparmor-profiles # дополнительные профили (многие — в режиме complain)

sudo aa-complain /usr/sbin/chronyd            # перевести профиль в complain (можно указать путь к файлу профиля)
sudo aa-enforce  /usr/sbin/chronyd            # вернуть enforce
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.chronyd    # перечитать один профиль после правки
sudo systemctl reload apparmor.service        # перечитать все профили

# отключить профиль:
sudo ln -s /etc/apparmor.d/usr.sbin.chronyd /etc/apparmor.d/disable/
sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.chronyd
# включить обратно:
sudo rm /etc/apparmor.d/disable/usr.sbin.chronyd
sudo apparmor_parser -a /etc/apparmor.d/usr.sbin.chronyd

sudo aa-genprof /путь/к/программе    # создать профиль в интерактивном режиме
sudo aa-logprof                      # предложить правки профилей по записям журнала
```

Каталоги: `/etc/apparmor.d/` — профили (имя = путь с точками вместо слэшей, например `usr.sbin.chronyd`); `/etc/apparmor.d/local/` — **локальные дополнения, не затираемые обновлениями пакетов**; `/etc/apparmor.d/disable/` — симлинки отключённых профилей; `/etc/apparmor.d/tunables/` — переменные; `/etc/apparmor.d/abstractions/` — общие блоки правил.

**Как понять, что блокирует именно AppArmor.** Отказ пишет ядро в виде audit-сообщения (пример условный, формат — `audit: type=1400 ... apparmor="DENIED" ...`):

```text
audit: type=1400 audit(1760090000.123:45): apparmor="DENIED" operation="open" class="file"
  profile="/usr/sbin/chronyd" name="/data/chrony/chrony.log" pid=812 comm="chronyd"
  requested_mask="w" denied_mask="w" fsuid=118 ouid=0
```

```bash
sudo dmesg | grep -i 'apparmor="DENIED"'
sudo journalctl -k --since "1 hour ago" | grep -i apparmor
sudo grep -i 'apparmor="DENIED"' /var/log/syslog /var/log/kern.log 2>/dev/null
sudo grep -i apparmor /var/log/audit/audit.log      # если установлен auditd — сообщения уходят сюда
```

Читать так: `profile` — какой профиль сработал, `name` — к чему обращались, `requested_mask`/`denied_mask` — какой доступ запрошен (`r`, `w`, `x`, `k` — блокировка, `m` — mmap exec), `comm` — процесс. Явные запрещающие правила (`deny ...`) в журнал **не пишут** [Canonical].

Типовая починка — добавить разрешение в локальный файл и перечитать профиль:

```bash
echo '/data/chrony/** rw,' | sudo tee -a /etc/apparmor.d/local/usr.sbin.chronyd
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.chronyd
```

Применительно к 1С и PostgreSQL:

- Пакеты PostgreSQL и платформы 1С своих профилей AppArmor обычно не несут — процессы `postgres`, `ragent`, `rmngr`, `rphost` работают unconfined (⚠ не подтверждено; проверьте `sudo aa-status` и `ps -eZ | grep -E 'postgres|rphost|ragent'`). Поэтому переносы каталогов данных PostgreSQL/1С AppArmor, как правило, не ломает — в отличие от служб с профилями (chronyd, rsyslogd, tcpdump, cups, snap-приложения, MySQL и др.).
- **Ubuntu 24.04+**: ядро ограничивает непривилегированные пользовательские пространства имён через AppArmor [Canonical]. Это может ломать песочницы приложений, для которых нет профиля (браузерные движки, в том числе встроенный в клиент 1С — ⚠ не подтверждено для 1С). Глобальный откат (ослабляет защиту, применять осознанно): файл `/etc/sysctl.d/60-apparmor-namespace.conf` со строкой `kernel.apparmor_restrict_unprivileged_userns=0`.
- Не отключайте AppArmor целиком «на всякий случай»: сначала найдите `DENIED` в журнале, затем правьте конкретный профиль или переводите его в complain.

### 11.2. Обновления безопасности

```bash
sudo apt update
apt list --upgradable
sudo apt upgrade                 # обычное обновление (не удаляет пакеты)
sudo apt full-upgrade            # с разрешением удаления/замены зависимостей (новые ядра и т. п.)
sudo apt autoremove --purge      # убрать старые ядра и ненужные зависимости
[ -f /var/run/reboot-required ] && cat /var/run/reboot-required /var/run/reboot-required.pkgs
```

**unattended-upgrades** [Canonical] — установлен и включён по умолчанию, ставит обновления безопасности автоматически.

| Файл | Назначение |
|---|---|
| `/etc/apt/apt.conf.d/20auto-upgrades` | включено ли и как часто: `APT::Periodic::Update-Package-Lists "1";` `APT::Periodic::Unattended-Upgrade "1";` (число — дни, `0` — выключить) |
| `/etc/apt/apt.conf.d/50unattended-upgrades` | что и как обновлять: `Allowed-Origins`, `Package-Blacklist`, перезагрузки, почта |
| `/var/log/unattended-upgrades/` | журналы (в т. ч. `unattended-upgrades-dpkg.log`) |
| таймеры `apt-daily.timer`, `apt-daily-upgrade.timer` | расписание запуска |

Ключевые параметры `50unattended-upgrades`:

```text
Unattended-Upgrade::Allowed-Origins {
        "${distro_id}:${distro_codename}";
        "${distro_id}:${distro_codename}-security";
        "${distro_id}ESMApps:${distro_codename}-apps-security";
        "${distro_id}ESM:${distro_codename}-infra-security";
//      "${distro_id}:${distro_codename}-updates";        // раскомментировать — ставить и обычные обновления
};
Unattended-Upgrade::Package-Blacklist {
        "postgresql-";           // регулярные выражения Python, привязаны к началу имени
        "postgrespro-";
        "1c-enterprise";
};
Unattended-Upgrade::Automatic-Reboot "false";          // по умолчанию: не перезагружать
Unattended-Upgrade::Automatic-Reboot-Time "03:30";     // now | hh:mm | +m — если включили перезагрузку
Unattended-Upgrade::Mail "admin@example.com";
Unattended-Upgrade::MailReport "only-on-error";        // always | only-on-error | on-change
```

(Состав `Allowed-Origins` по умолчанию подтверждён документацией Ubuntu Server: четыре активные строки — `${distro_codename}`, `-security`, `ESMApps…-apps-security`, `ESM…-infra-security`; закомментированы `-updates`, `-proposed`, `-backports`. Там же: выражения в `Package-Blacklist` — регулярные выражения Python, ведущие себя так, будто в начале стоит `^`; примеры из документации — `"linux-";`, `"libc6$";`, `"libc(6|-bin)$";`. Дополнительно есть `Unattended-Upgrade::Automatic-Reboot-WithUsers "true";` (перезагружать даже при вошедших пользователях). Сторонние репозитории — PGDG, Postgres Pro, 1С — в `Allowed-Origins` не входят и автоматически не обновляются, пока вы сами их туда не добавите.)

```bash
sudo unattended-upgrade -v --dry-run          # что было бы установлено
systemctl list-timers 'apt-daily*'
sudo dpkg-reconfigure -plow unattended-upgrades   # включить/выключить диалогом
```

**needrestart** — с Ubuntu 24.04 автоматически **перезапускает службы**, затронутые обновлением библиотек, в том числе при запуске из unattended-upgrades [Canonical]. Для сервера 1С и PostgreSQL неожиданный перезапуск в рабочее время — это обрыв сеансов. Исключения — в `/etc/needrestart/conf.d/`:

```perl
# /etc/needrestart/conf.d/50-1c-postgres.conf
# 0 = не перезапускать автоматически (только сообщать)
$nrconf{override_rc}{qr(^postgresql)} = 0;
$nrconf{override_rc}{qr(^postgrespro)} = 0;
$nrconf{override_rc}{qr(^srv1cv8)} = 0;
$nrconf{override_rc}{qr(^apache2)} = 0;
# либо глобально: только перечислять службы, ничего не перезапускать
#$nrconf{restart} = 'l';
```

Что подтверждено и что нет:

- [Canonical] «Starting with Ubuntu 24.04 LTS, needrestart restarts the affected services automatically by default»; основной файл — `/etc/needrestart/needrestart.conf`, локальные переопределения — `/etc/needrestart/conf.d/`; `$nrconf{restart}`: `'a'` — перезапускать автоматически, `'l'` — только перечислять (в апстримном файле есть и `'i'` — интерактивно; в неинтерактивном запуске, например из unattended-upgrades, режим `'i'` сам превращается в «только список» — так было в 22.04).
- Пример из документации Ubuntu:

  ```perl
  $nrconf{override_rc} = {
      qr(^whatever-critical-service\.service$) => 0,
  };
  ```

  Значение `0` исключает службу из автоматического перезапуска. **Осторожно:** в таком виде присваивание заменяет весь хеш `override_rc` целиком, включая встроенные исключения из `needrestart.conf` (там уже со значением 0 перечислены `^dbus`, дисплейные менеджеры, `^network`, `^NetworkManager`, `^systemd-logind`, `^getty@.+\.service`, `^user@\d+\.service`, `^docker`, `^libvirt`, `^apt-daily…`, `^unattended-upgrades\.service$` и др.; PostgreSQL и сервера 1С среди встроенных исключений **нет** — проверено по апстримному `needrestart.conf`). Поэтому в примере выше использована форма с добавлением отдельных ключей `$nrconf{override_rc}{qr(...)} = 0;`, которая встроенный список сохраняет. Это обычный синтаксис Perl (ключ хеша — выражение `qr(...)`), и он широко встречается в руководствах, но в официальной документации именно в таком виде не приведён — ⚠ после правки обязательно проверьте: `sudo needrestart -r l` (должен отработать без ошибок Perl) и убедитесь, что служба не попадает в список автоматически перезапускаемых.
- Регулярные выражения проверяются «в лексическом порядке, используется первое совпавшее» (комментарий в апстримном файле). Шаблон сопоставляется с именем юнита: для сервера 1С подойдёт `qr(^srv1cv8)`, для кластера PostgreSQL из `postgresql-common` — `qr(^postgresql@)` или `qr(^postgresql)`, для Postgres Pro — `qr(^postgrespro)`.
- Есть и `$nrconf{blacklist_rc}` — службы из него needrestart игнорирует полностью; сам апстримный файл советует пользоваться `override_rc`.

Заморозить версии критичных пакетов (обновлять вручную в окно обслуживания):

```bash
sudo apt-mark hold postgresql-17 postgresql-client-17
apt-mark showhold
sudo apt-mark unhold postgresql-17 postgresql-client-17
```

Ubuntu Pro (расширенные обновления ESM, Livepatch — исправления ядра без перезагрузки): `pro status`, `sudo pro attach <токен>`, `sudo pro enable livepatch`.

### 11.3. fail2ban

Блокирует IP-адреса, с которых идёт перебор паролей (по записям журналов).

```bash
sudo apt install fail2ban
sudo systemctl enable --now fail2ban
sudo fail2ban-client status              # список «тюрем» (jails)
sudo fail2ban-client status sshd         # статистика и забаненные адреса
sudo fail2ban-client set sshd unbanip 203.0.113.7
sudo fail2ban-client set sshd banip 203.0.113.7
sudo fail2ban-client reload
fail2ban-client --str2sec 1d12h          # проверить запись интервала
sudo tail -f /var/log/fail2ban.log
```

Порядок чтения конфигурации [man jail.conf(5)]: `jail.conf` → `jail.d/*.conf` → `jail.local` → `jail.d/*.local`; **файлы `.conf` не править** — свои настройки в `.local`.

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/8 192.168.0.0/16
bantime  = 1h
findtime = 10m
maxretry = 5
# backend = systemd      # читать журнал systemd вместо файлов (если нет /var/log/auth.log)
# banaction = nftables   # умолчание апстрима — iptables-multiport; в Ubuntu 24.04+ пакет уже ставит nftables (см. ниже); при UFW — banaction = ufw

[sshd]
enabled = true
```

В Debian/Ubuntu «тюрьма» `sshd` включена сразу после установки пакета через `/etc/fail2ban/jail.d/defaults-debian.conf` — подтверждено по исходникам пакета Debian. Содержимое этого файла в актуальных пакетах (Debian unstable; изменения внесены в 1.0.2-3 от 19.09.2023 — эта версия лежит в основе пакета Ubuntu 24.04 `1.0.2-3ubuntu0.1`):

```ini
[DEFAULT]
banaction = nftables
banaction_allports = nftables[type=allports]

[sshd]
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service + _COMM=sshd
enabled = true
```

То есть в Ubuntu 24.04/26.04 бан выполняется через **nftables**, а `sshd` читается из журнала systemd (файл `/var/log/auth.log` не нужен). В Ubuntu 22.04 (fail2ban 0.11.2) в этом файле, по памяти, только `[sshd]` / `enabled = true`, действие по умолчанию — `iptables-multiport` (⚠ не проверено). Порядок чтения означает, что ваш `jail.local` перекрывает `defaults-debian.conf`: если вы зададите в `jail.local` свой `banaction` или `backend` в `[DEFAULT]`, проверьте итог командой `sudo fail2ban-client -d | grep -E "sshd.*(banaction|backend|action)" | head` или `sudo fail2ban-client get sshd actions`. Юнит SSH в Ubuntu называется `ssh.service` (не `sshd.service`) — это учтено в `journalmatch`. Интервалы можно писать как `600`, `10m`, `1d12h30m`. Обязательно внесите свои адреса администрирования в `ignoreip`, чтобы не заблокировать себя.

Для сервера 1С fail2ban защищает в первую очередь SSH. Порты кластера 1С (1540, 1541, 1560–1591) и PostgreSQL (5432) в интернет открывать не следует вовсе — это задача межсетевого экрана (UFW/nftables), а не fail2ban.

### 11.4. auditd (кратко)

Подсистема аудита ядра: кто и когда менял файлы, выполнял команды, входил в систему.

```bash
sudo apt install auditd audispd-plugins
sudo systemctl enable --now auditd
sudo auditctl -s                 # состояние
sudo auditctl -l                 # загруженные правила
```

Постоянные правила — файлы `/etc/audit/rules.d/*.rules`, загрузка `sudo augenrules --load`:

```text
# /etc/audit/rules.d/50-1c-postgres.rules
-w /etc/postgresql/ -p wa -k pg_config
-w /etc/sudoers -p wa -k sudoers
-w /etc/sudoers.d/ -p wa -k sudoers
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /opt/1cv8/ -p wa -k onec_bin
-w /etc/systemd/system/ -p wa -k systemd_units
```

`-w` — наблюдаемый путь, `-p` — права (`r` чтение, `w` запись, `x` выполнение, `a` изменение атрибутов), `-k` — метка для поиска.

```bash
sudo ausearch -k pg_config -ts today -i     # события по метке за сегодня, с расшифровкой
sudo ausearch -m USER_LOGIN -ts recent -i
sudo aureport --summary
sudo aureport -au                            # отчёт по аутентификации
```

Журнал — `/var/log/audit/audit.log`. При работающем auditd сообщения AppArmor (`apparmor="DENIED"`) попадают туда же.

### 11.5. Минимизация сервисов и открытых портов

```bash
systemctl list-unit-files --type=service --state=enabled    # что включено в автозапуск
systemctl list-units --type=service --state=running         # что работает сейчас
systemctl list-unit-files --state=enabled                   # включённые юниты всех типов (сокеты, таймеры)
systemctl --failed
sudo ss -tulpn             # слушающие TCP/UDP-порты: -t TCP, -u UDP, -l listening, -p процесс, -n без имён
sudo ss -tlnp | grep -E ':(1540|1541|1545|15[6-9][0-9]|5432|80|443)\b'

sudo systemctl disable --now имя.service    # выключить и остановить
sudo systemctl mask имя.service             # запретить запуск совсем (unmask — вернуть)
systemd-analyze security имя.service        # оценка изоляции юнита
```

Что должно слушать на типичном сервере 1С + PostgreSQL:

| Порт | Кто | Комментарий |
|---|---|---|
| 22/tcp | sshd | только из сети администрирования |
| 1540/tcp | ragent | агент сервера 1С |
| 1541/tcp | rmngr | менеджер кластера |
| 1560–1591/tcp | rphost | рабочие процессы (диапазон по умолчанию) |
| 1545/tcp | ras | сервер администрирования (если запущен) |
| 5432/tcp | postgres | лучше только `127.0.0.1`, если СУБД и 1С на одном хосте (`listen_addresses`) |
| 80, 443/tcp | apache2/nginx | веб-публикация |
| 123/udp | chronyd | только если сервер раздаёт время (`allow`); клиенту входящий порт не нужен |

Кандидаты на отключение на сервере (каждый — только если точно не нужен): `ModemManager`, `multipathd` (нет multipath-хранилища), `open-iscsi`, `udisks2`, `cups`, `avahi-daemon`, `snapd` (если не используются snap-пакеты; certbot из snap его требует), cloud-init на не-облачной ВМ (`sudo touch /etc/cloud/cloud-init.disabled`).

### 11.6. lynis

Аудитор безопасности: проверяет сотни настроек и выдаёт предупреждения, рекомендации и «hardening index».

```bash
sudo apt install lynis
sudo lynis audit system                 # полный аудит
sudo lynis audit system --quick         # без пауз между разделами (-Q)
sudo lynis audit system --cronjob       # для запуска по расписанию (тихий режим)
lynis show commands
lynis show profiles
sudo lynis show details SSH-7408        # подробности по идентификатору теста из отчёта
```

Результаты: журнал `/var/log/lynis.log` (перезаписывается при каждом запуске), отчёт `/var/log/lynis-report.dat`. Версия в репозитории Ubuntu отстаёт от актуальной; свежая — из репозитория CISOfy или `git clone https://github.com/CISOfy/lynis`. Рекомендации Lynis — подсказки, а не обязательные требования: не применяйте их вслепую на сервере 1С (например, жёсткие sysctl или монтирование `/tmp` с `noexec` могут мешать работе приложений).

---

## 12. Сертификаты и TLS

Версии OpenSSL (по packages.ubuntu.com на 10.2026): Ubuntu 22.04 — **3.0.2** (пакет 3.0.2-0ubuntu1.x), 24.04 — **3.0.13** (3.0.13-0ubuntu3.x), 26.04 — **3.5.x** (LTS-ветка апстрима: в архиве 3.5.5-1ubuntu3.x, release notes говорят об обновлении до 3.5.6; поддержка QUIC и постквантовых алгоритмов ML-KEM, ML-DSA, SLH-DSA). Точная версия на своей системе: `openssl version -a`. Опции ниже — для OpenSSL 3.x (проверены по документации 3.5: `-noenc`, `-addext`, `-copy_extensions`, `-checkend`, `-ext`, умолчание `-days` = 30).

Для каких задач на сервере 1С:

- HTTPS для веб-публикации (Apache/nginx): пара «сертификат + закрытый ключ»;
- доверие к внутреннему УЦ при исходящих HTTPS-запросах из 1С и системных утилит;
- TLS между 1С и PostgreSQL — обычно **не используется**: [1С] в рекомендациях по настройке PostgreSQL указывает `ssl = off` (шифрование расходует CPU). Учтите, что пакеты PostgreSQL в Debian/Ubuntu по умолчанию создают кластер с `ssl = on` и самоподписанным «snakeoil»-сертификатом — подтверждено по исходникам `pg_createcluster` (postgresql-common 278): `ssl` берётся из `createcluster.conf` и по умолчанию `on`; если кластер создаётся заново, существует `/etc/ssl/certs/ssl-cert-snakeoil.pem`, а ключ `/etc/ssl/private/ssl-cert-snakeoil.key` читается владельцем кластера (пользователь `postgres` состоит в группе `ssl-cert`), то в `postgresql.conf` прописываются `ssl = on`, `ssl_cert_file`, `ssl_key_file`. Чтобы привести к рекомендации 1С: `ssl = off` в `postgresql.conf` (или в `conf.d/`) и перезапуск; чтобы новые кластеры создавались сразу без SSL — `ssl = off` в `/etc/postgresql-common/createcluster.conf`. Проверка: `sudo -u postgres psql -c "SHOW ssl;"`. У сборок Postgres Pro (свой `initdb`/`pg-setup`) этого поведения нет (Подтверждено 11.10.2026 чтением пакета `postgrespro-1c-16-server` 16.14-1.noble: в `postgresql.conf.sample` стоит `#ssl = off`, а скрипт `pg-setup` и пресеты `default.tune` и `1c.tune` параметр `ssl` не трогают; при этом пакет зависит от `ssl-cert`, так что «snakeoil»-сертификат в системе появится, но использоваться не будет).

### 12.1. Ключи

```bash
# RSA 2048 (классическая команда)
openssl genrsa -out server.key 2048
# то же современной командой, с выбором размера
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out server.key
# EC P-256
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out server.key
# ключ, зашифрованный паролем
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -aes256 -out server.key

chmod 600 server.key
openssl pkey -in server.key -noout -text | head     # посмотреть ключ
openssl pkey -in enc.key -out plain.key             # снять пароль с ключа
```

### 12.2. Запрос на сертификат (CSR)

```bash
openssl req -new -key server.key -out server.csr \
  -subj "/C=RU/O=Company/CN=1c.example.com" \
  -addext "subjectAltName=DNS:1c.example.com,DNS:srv1c,IP:192.168.1.10"

# ключ и CSR одной командой
openssl req -new -newkey rsa:2048 -noenc -keyout server.key -out server.csr \
  -subj "/CN=1c.example.com" -addext "subjectAltName=DNS:1c.example.com"

openssl req -in server.csr -noout -text -verify     # просмотр и проверка подписи CSR
```

- `-noenc` — не шифровать ключ паролем; прежнее имя `-nodes` в OpenSSL 3.0 объявлено устаревшим, но работает.
- `-addext` можно повторять; значение — как строка в конфигурационном файле.
- Современные клиенты проверяют имя **только по subjectAltName**; одного `CN` недостаточно.

### 12.3. Самоподписанный сертификат с SAN

```bash
openssl req -x509 -newkey rsa:2048 -noenc -sha256 -days 825 \
  -keyout server.key -out server.crt \
  -subj "/CN=1c.example.com" \
  -addext "subjectAltName=DNS:1c.example.com,DNS:srv1c,IP:192.168.1.10" \
  -addext "keyUsage=digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth"
```

`-x509` — выпустить сертификат вместо CSR; `-days` — срок (по умолчанию всего 30 дней).

### 12.4. Свой корневой УЦ и подпись серверного сертификата

```bash
# 1) корневой сертификат УЦ
openssl req -x509 -new -newkey rsa:4096 -noenc -sha256 -days 3650 \
  -keyout ca.key -out ca.crt -subj "/O=Company/CN=Company Root CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"

# 2) подписать CSR сервера, перенеся расширения (SAN) из запроса
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -copy_extensions copyall

# 3) проверить цепочку
openssl verify -CAfile ca.crt server.crt       # server.crt: OK
```

`-copy_extensions copy|copyall` есть в OpenSSL 3.x; **без неё расширения из CSR (включая SAN) в сертификат не попадают**. В OpenSSL 1.1.1 вместо неё использовали `-extfile san.cnf -extensions v3_req`.

### 12.5. Просмотр и проверка

```bash
openssl x509 -in server.crt -noout -text                     # всё содержимое
openssl x509 -in server.crt -noout -subject -issuer -dates -serial
openssl x509 -in server.crt -noout -ext subjectAltName
openssl x509 -in server.crt -noout -fingerprint -sha256
openssl x509 -in server.crt -noout -enddate
openssl x509 -in server.crt -noout -checkend 2592000         # код возврата 1, если истекает в течение 30 дней

# соответствует ли ключ сертификату (хеши открытых ключей должны совпасть)
openssl x509 -in server.crt -noout -pubkey | openssl sha256
openssl pkey -in server.key -pubout | openssl sha256

openssl verify server.crt                                     # по системному хранилищу
openssl verify -CAfile ca.crt -untrusted intermediate.crt server.crt
```

### 12.6. s_client: проверка удалённого сервера

```bash
openssl s_client -connect 1c.example.com:443 -servername 1c.example.com </dev/null
# в выводе важно: цепочка "Certificate chain", "Verify return code: 0 (ok)", версия протокола и шифр

# только срок действия и субъект
echo | openssl s_client -connect 1c.example.com:443 -servername 1c.example.com 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

openssl s_client -connect host:443 -servername host -showcerts </dev/null    # вся цепочка в PEM
openssl s_client -connect host:443 -CAfile ca.crt </dev/null                 # проверить относительно своего УЦ
openssl s_client -connect host:443 -tls1_2 </dev/null                        # принудительно TLS 1.2 (или -tls1_3)
openssl s_client -connect db.example.com:5432 -starttls postgres </dev/null  # TLS у PostgreSQL
openssl s_client -connect mail.example.com:25 -starttls smtp </dev/null
openssl s_client -connect 1.ntp.ubuntu.com:4460 -servername 1.ntp.ubuntu.com </dev/null   # доступность NTS
```

`-servername` задаёт SNI — без него сервер с несколькими сайтами может отдать не тот сертификат. Типичные коды: `20 (unable to get local issuer certificate)` / `21 (unable to verify the first certificate)` — сервер не отдаёт промежуточные сертификаты или УЦ не в доверенных; `18 (self-signed certificate)`; `10 (certificate has expired)`.

### 12.7. Конвертация форматов

| Формат | Что это |
|---|---|
| PEM (`.pem`, `.crt`, `.cer`, `.key`) | Base64-текст с `-----BEGIN ...-----`; основной формат в Linux |
| DER (`.der`, `.cer`) | двоичный вариант того же |
| PKCS#12 (`.pfx`, `.p12`) | контейнер: сертификат + ключ + цепочка, под паролем; основной формат Windows |
| PKCS#7 (`.p7b`) | цепочка сертификатов без ключа |

```bash
# DER -> PEM и обратно
openssl x509 -inform der -in cert.der -outform pem -out cert.crt
openssl x509 -in cert.crt -outform der -out cert.der

# PFX -> PEM
openssl pkcs12 -in cert.pfx -out all.pem -noenc                 # всё в один файл
openssl pkcs12 -in cert.pfx -clcerts -nokeys -out server.crt    # только сертификат сервера
openssl pkcs12 -in cert.pfx -cacerts -nokeys -out chain.crt     # только цепочка УЦ
openssl pkcs12 -in cert.pfx -nocerts -noenc -out server.key     # только ключ (без пароля)

# PEM -> PFX
openssl pkcs12 -export -inkey server.key -in server.crt -certfile chain.crt \
  -name "1c-web" -out server.pfx

# P7B -> PEM
openssl pkcs7 -print_certs -in chain.p7b -out chain.pem          # для двоичного p7b добавить -inform der

# fullchain для веб-сервера: сначала сертификат сервера, затем промежуточные
cat server.crt intermediate.crt > fullchain.pem
```

Про `-legacy`: OpenSSL 3.x по умолчанию создаёт PFX с AES-256-CBC и PBKDF2; старые Windows/Java такой файл не открывают — экспортируйте с `-legacy`. И наоборот: старый PFX (RC2-40/3DES) в OpenSSL 3.x читается только с `-legacy`, иначе ошибка `digital envelope routines::unsupported`.

### 12.8. Системное хранилище доверенных корневых сертификатов

[Canonical]: пакет `ca-certificates`.

```bash
sudo apt-get install -y ca-certificates
sudo cp company-root-ca.crt /usr/local/share/ca-certificates/     # ОБЯЗАТЕЛЬНО формат PEM и расширение .crt
sudo update-ca-certificates
#   Updating certificates in /etc/ssl/certs...  1 added, 0 removed; done.
ls /etc/ssl/certs/ | grep company-root-ca          # появится company-root-ca.pem (симлинк)

# удаление
sudo rm /usr/local/share/ca-certificates/company-root-ca.crt
sudo update-ca-certificates --fresh                # без --fresh сертификат останется в хранилище
```

- Итоговый единый файл: `/etc/ssl/certs/ca-certificates.crt`; каталог в формате OpenSSL (хеш-симлинки): `/etc/ssl/certs/`.
- Файл без расширения `.crt` **не обрабатывается**. DER сначала конвертируйте в PEM. В один файл кладите один сертификат.
- Включение/исключение поставляемых корневых сертификатов: `sudo dpkg-reconfigure ca-certificates` (список в `/etc/ca-certificates.conf`).
- Хранилище используют программы на системном OpenSSL/GnuTLS (`curl`, `wget`, `apt`, `git`, `psql`). **Не используют** или используют частично: snap-приложения [Canonical], браузеры (собственное NSS-хранилище), Java (`/etc/ssl/certs/java/cacerts`, обновляется пакетом `ca-certificates-java`), Python-библиотеки с `certifi`.
- **Платформа 1С** [1С] (руководство администратора 8.3.27, приложение 3, раздел 3.13 «cacertnx.pem и cacert.pem»; конспект `kb/its-docs/adm-pr03-sluzhebnye-fajly-p1.md`): какие корневые сертификаты платформа использует для проверки сертификатов при установке защищённого соединения, зависит от версии платформы и **режима совместимости конфигурации**:

  | Версия платформы | Режим совместимости | Что используется |
  |---|---|---|
  | до 8.3.8 | «Версия 8.3.7» и предыдущие | только файл `cacert.pem` |
  | с 8.3.8 до 8.3.19 | «Версия 8.3.8» | только механизм получения сертификатов УЦ операционной системы |
  | начиная с 8.3.20 | «Версия 8.3.8» и последующие | сначала файл **`cacertnx.pem`**, затем механизм операционной системы |
  | начиная с 8.3.20 | «Версия 8.3.7» и предшествующие | только `cacert.pem` |

  Следствия для Ubuntu: на актуальных платформах (8.3.20+/8.5) свой корневой сертификат достаточно добавить в **системное хранилище** (`update-ca-certificates`) — платформа обратится к нему после `cacertnx.pem`; файл `cacert.pem` нужно дополнять только для старых конфигураций в режиме совместимости 8.3.7 и ниже. Оба файла лежат в каталоге платформы (в методической статье ИТС для Windows — каталог `bin`; для Linux путь в документации не назван — ⚠ найти: `find /opt/1cv8 -name 'cacert*.pem'`). В клиент-серверном варианте `cacert.pem` обновляют и на сервере, и на клиентах; перезапуск сервера после этого не требуется [1С, методическая статья о добавлении сертификата DigiCert]. Какое именно «хранилище ОС» платформа читает на Linux (единый файл `/etc/ssl/certs/ca-certificates.crt` или каталог `/etc/ssl/certs`) — в документации не уточняется (⚠). В прикладном коде набор сертификатов УЦ задаётся ещё и явно — объектами `СертификатыУдостоверяющихЦентровОС` / `СертификатыУдостоверяющихЦентровФайл` в конструкторе `ЗащищенноеСоединениеOpenSSL` (подтверждено главой 17 «Руководства разработчика» 8.3.27: второй параметр конструктора `ЗащищенноеСоединениеOpenSSL` принимает `СертификатыУдостоверяющихЦентровОС`, `СертификатыУдостоверяющихЦентровФайл` или `Неопределено` (тогда сертификат сервера не проверяется), документация рекомендует вариант с хранилищем ОС; сверено 11.10.2026; ранее: по памяти, описание в синтакс-помощнике не сверялось). Типичный симптом недоверия — ошибка «Удаленный узел не прошел проверку».

Проверка, что УЦ действительно доверенный:

```bash
openssl verify server.crt
curl -sSI https://1c.example.com/ | head -1
```

### 12.9. certbot (Let's Encrypt)

Бесплатные сертификаты с автоматическим продлением. Условия: публичное доменное имя; для проверки HTTP-01 — доступность **порта 80** из интернета. Для внутренних серверов без доступа извне — проверка DNS-01 либо собственный УЦ (12.4).

Установка, рекомендованная разработчиками certbot, — snap. Команды ниже сверены с инструкцией certbot.eff.org для связки «Apache + snapd» (`sudo snap install --classic certbot`, `sudo ln -s /snap/bin/certbot /usr/local/bin/certbot`, `sudo certbot --apache`, `sudo certbot certonly --apache`, `sudo certbot renew --dry-run`). Документация certbot перечисляет и альтернативы — Docker, pip (в виртуальном окружении, «best effort») и пакеты дистрибутивов (сопровождаются не командой certbot и на LTS-выпусках часто устаревшие):

```bash
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/local/bin/certbot

# альтернатива — пакеты Ubuntu (версия отстаёт):
sudo apt install certbot python3-certbot-apache
```

```bash
sudo certbot --apache -d 1c.example.com                      # получить и прописать в Apache
sudo certbot --nginx  -d 1c.example.com
sudo certbot certonly --standalone -d 1c.example.com         # встроенный веб-сервер на 80 порту (Apache должен быть остановлен)
sudo certbot certonly --webroot -w /var/www/html -d 1c.example.com   # через каталог работающего сайта
sudo certbot certonly --manual --preferred-challenges dns -d 1c.example.com   # DNS-01 вручную (TXT-запись)

sudo certbot certificates                                    # что выпущено и когда истекает
sudo certbot renew --dry-run                                 # проверка автопродления
sudo certbot renew --deploy-hook "systemctl reload apache2"
systemctl list-timers | grep -i certbot                      # таймер автопродления (snap.certbot.renew.timer или certbot.timer)
```

Файлы: `/etc/letsencrypt/live/<имя>/fullchain.pem` (сертификат + цепочка), `privkey.pem` (ключ), `cert.pem`, `chain.pem` — это симлинки на актуальные версии в `/etc/letsencrypt/archive/`. Хуки после продления — исполняемые файлы в `/etc/letsencrypt/renewal-hooks/deploy/`.

В Apache (mod_ssl):

```apache
SSLEngine on
SSLCertificateFile      /etc/letsencrypt/live/1c.example.com/fullchain.pem
SSLCertificateKeyFile   /etc/letsencrypt/live/1c.example.com/privkey.pem
```

Срок действия сертификатов Let's Encrypt на октябрь 2026 — 90 дней (профиль по умолчанию `classic`), но объявлено поэтапное сокращение [Let's Encrypt, «Decreasing Certificate Lifetimes to 45 Days», 02.12.2025]:

| Дата | Что меняется |
|---|---|
| 13.05.2026 | профиль `tlsserver` (по желанию, для ранних испытаний) — сертификаты на 45 дней |
| 10.02.2027 | профиль по умолчанию `classic` — **64 дня**; срок повторного использования авторизации домена сокращается с 30 до 10 дней |
| 16.02.2028 | профиль `classic` — **45 дней**; повторное использование авторизации — 7 часов |

(Есть также профиль `shortlived` — сертификаты на 6 дней.) Рекомендации Let's Encrypt: использовать клиент с поддержкой ARI (ACME Renewal Information), не полагаться на фиксированный интервал продления в 60 дней (при 45-дневных сертификатах его недостаточно; приемлемо продлевать примерно на двух третях срока), не продлевать вручную и настроить мониторинг срока действия. Практический вывод для сервера с веб-публикацией 1С: автопродление должно работать без участия человека — проверяйте `sudo certbot renew --dry-run`, таймер (`systemctl list-timers | grep -i certbot`) и то, что после продления веб-сервер перечитывает сертификат (`--deploy-hook "systemctl reload apache2"` или скрипт в `/etc/letsencrypt/renewal-hooks/deploy/`); контроль срока — `openssl x509 -in /etc/letsencrypt/live/<имя>/cert.pem -noout -checkend 1209600` (код возврата 1, если до истечения меньше 14 дней). Сокращение срока авторизации означает, что проверка домена (HTTP-01 через порт 80 или DNS-01) будет выполняться практически при каждом продлении — порт 80 должен оставаться доступным постоянно.

---

## Типичные ошибки и подводные камни

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | После перезагрузки параметр sysctl вернулся к старому значению | Задан через `sysctl -w` (временно) или записан в `/etc/sysctl.conf`, который при загрузке не читается, если нет симлинка `/etc/sysctl.d/99-sysctl.conf` (в Ubuntu 26.04 его нет по умолчанию); либо перекрыт файлом с «бо́льшим» именем (в 22.04/24.04 — в том числе самим `99-sysctl.conf` → `/etc/sysctl.conf`) или профилем tuned | Свой файл `/etc/sysctl.d/90-*.conf`; `sudo sysctl --system`; искать дубликаты: `grep -r имя /etc/sysctl.d /usr/lib/sysctl.d /run/sysctl.d /etc/sysctl.conf`; `systemd-analyze cat-config sysctl.d` |
| 2 | `sysctl: cannot stat /proc/sys/kernel/sched_migration_cost_ns: No such file or directory` | Параметры планировщика перенесены в debugfs (ядро ≥ 5.13) | Удалить строки `kernel.sched_*_ns` из конфигов |
| 3 | Подняли `nofile` в `/etc/security/limits.conf`, а у PostgreSQL/`rphost` по-прежнему 1024 | `limits.conf` не действует на службы systemd | `sudo systemctl edit <юнит>` → `LimitNOFILE=65536`, перезапуск; проверка `cat /proc/<pid>/limits` |
| 4 | `Too many open files` в журнале PostgreSQL или 1С | Мягкий `LimitNOFILE=1024` при большом `max_files_per_process`/множестве соединений | `LimitNOFILE` в drop-in юнита; для PostgreSQL согласовать с `max_files_per_process` |
| 5 | После обновления платформы 1С лимиты «слетели» | Имя юнита содержит версию платформы — drop-in остался у старого юнита | Перенести drop-in на новый юнит; надёжнее — drop-in по префиксу `/etc/systemd/system/srv1cv8-.service.d/limits.conf` (раздел 5.3); в крайнем случае `DefaultLimitNOFILE`/`DefaultTasksMax` в `/etc/systemd/system.conf.d/` |
| 6 | `fork: retry: Resource temporarily unavailable`, `pthread_create failed`, в `journalctl -k`: `fork rejected by pids controller` | Исчерпан `TasksMax` службы (15 % по умолчанию) или `nproc` пользователя | `TasksMax=infinity` в drop-in; проверить `systemctl status <юнит>` (строка Tasks) |
| 7 | PostgreSQL не стартует: `could not map anonymous shared memory: Cannot allocate memory` | `huge_pages = on`, а страниц меньше нужного (изменили `shared_buffers`/`max_connections`, либо ядро не смогло выделить из-за фрагментации) | Пересчитать `shared_memory_size_in_huge_pages`, увеличить `vm.nr_hugepages`, перезагрузиться или резервировать через GRUB `hugepages=` |
| 8 | Huge pages зарезервированы, но `HugePages_Free == HugePages_Total` при работающем PostgreSQL; памяти «не хватает» | `huge_pages = try`, и PostgreSQL молча ушёл на обычные страницы (страниц чуть не хватило); резерв простаивает | Увеличить `vm.nr_hugepages` до расчётного + запас; проверить `SHOW huge_pages_status;`; после отладки `huge_pages = on` |
| 9 | После `sysctl -w vm.nr_hugepages=N` значение `HugePages_Total` меньше N | Память фрагментирована, ядро не нашло непрерывных участков | Резервировать при загрузке (sysctl.d отрабатывает рано, надёжнее — параметр ядра `hugepages=N`) |
| 10 | При `vm.overcommit_memory=2` процессы 1С/PostgreSQL получают `Cannot allocate memory` при свободной RAM | `CommitLimit` мал: `overcommit_ratio=50` по умолчанию и память huge pages исключается из расчёта | Поднять `vm.overcommit_ratio` (80–95) или вернуть `vm.overcommit_memory=0` на общем сервере |
| 11 | Периодические «замирания» СУБД на секунды, высокий `%sys`, в `top` активен `khugepaged`/`kcompactd` | THP в режиме `always` | Отключить THP (GRUB/юнит/tuned), перезапустить службы |
| 12 | `transparent_hugepage=never` добавлен в `/etc/default/grub`, но после перезагрузки THP включён | Не выполнен `update-grub`, либо переменную переопределяет файл из `/etc/default/grub.d/` (cloud-образ) | `sudo update-grub`; `cat /proc/cmdline`; править нужный файл в `grub.d` |
| 13 | `cpupower frequency-info`: `no or unknown cpufreq driver is active on this CPU` | Виртуальная машина: частотой управляет гипервизор | Настраивать электропитание на хосте (BIOS, схема Windows «Высокая производительность») |
| 14 | Governor `performance` сбрасывается после перезагрузки | `cpupower frequency-set` не постоянна | tuned-профиль или oneshot-юнит |
| 15 | Ubuntu 26.04 (или 25.10): `System clock synchronized: no`, в `chronyc sources` все источники `^?` | Наружу закрыт TCP 4460 (NTS) и/или UDP 123 | Открыть порты либо указать внутренние NTP-серверы без `nts` в `/etc/chrony/sources.d/`, `chronyc reload sources` |
| 16 | После обновления 24.04 → 26.04 нет `chronyc`, время ведёт по-прежнему `systemd-timesyncd` (или после ручных правок служб времени две/ни одной) | chrony ставится по умолчанию только на новые установки; при обновлении остаётся timesyncd [Canonical] | Проверить `systemctl status chrony systemd-timesyncd`, `timedatectl`; перейти на chrony: `sudo apt-mark auto systemd-timesyncd && sudo apt install chrony`; оставить ровно одну службу; `sudo timedatectl set-ntp true` |
| 17 | Kerberos-аутентификация в 1С перестала работать, `kinit`: `Clock skew too great` | Расхождение времени с контроллером домена > 5 минут | Синхронизировать с DC (chrony → DC), `sudo chronyc makestep` |
| 18 | Время в ВМ «прыгает» или отстаёт после паузы/снимка | Нет источника времени гипервизора либо два механизма конфликтуют | chrony с `refclock PHC /dev/ptp_hyperv` (Hyper-V) и `makestep 1.0 -1`; один механизм синхронизации |
| 19 | Создание базы из 1С: `new collation (ru_RU.UTF-8) is incompatible with the collation of the template database (...)` | Кластер PostgreSQL инициализирован не в `ru_RU.UTF-8`: пакет создал `main` в **системной** локали из `/etc/default/locale` (локаль сеанса администратора при установке пакета не учитывается); [1С] требует совпадения locale кластера и создаваемой базы | `locale-gen ru_RU.UTF-8`; пересоздать кластер (пока в нём нет данных): `pg_dropcluster --stop NN main; pg_createcluster --locale ru_RU.UTF-8 NN main --start`; на будущее — `update-locale LANG=ru_RU.UTF-8` до установки PostgreSQL или `create_main_cluster = false` |
| 20 | `initdb: error: invalid locale name "ru_RU.UTF-8"` / `locale: Cannot set LC_ALL to default locale: No such file or directory` | Локаль не сгенерирована | `sudo locale-gen ru_RU.UTF-8`; проверить `locale -a` |
| 21 | Сообщения `perl: warning: Setting locale failed` при каждом `apt`/входе по SSH | Клиент SSH передаёт `LANG`/`LC_*` (директива `SendEnv`/`AcceptEnv`), а такой локали на сервере нет | Сгенерировать эту локаль на сервере или убрать передачу переменных |
| 22 | После обновления ОС: `WARNING: database "..." has a collation version mismatch`; запросы не находят существующие строки, дубликаты в уникальных индексах | Сменилась версия glibc/ICU — изменился порядок сортировки | `reindexdb --all`, затем `ALTER DATABASE ... REFRESH COLLATION VERSION` в каждой базе; в будущем — перенос через dump/restore |
| 23 | Печатные формы 1С «поплыли»: обрезан текст, другая ширина колонок, лишние страницы | На сервере нет шрифтов макета — идёт подстановка | `ttf-mscorefonts-installer`, при необходимости вручную Tahoma/Calibri; `fc-cache -fv`; `fc-match Arial`; перезапуск сервера 1С |
| 24 | Пакет `ttf-mscorefonts-installer` установлен, но `fc-list` шрифтов не показывает | При установке не было интернета/не принята EULA — загрузка не выполнена | `sudo apt install --reinstall ttf-mscorefonts-installer` или ручное копирование `.ttf` |
| 25 | Установка из скрипта «висит» на `ttf-mscorefonts-installer` | Диалог EULA debconf ждёт ввода | `debconf-set-selections` + `DEBIAN_FRONTEND=noninteractive` |
| 26 | Служба с профилем AppArmor не может открыть файл в нестандартном каталоге (`Permission denied` при верных правах) | Путь не разрешён профилем | Найти `apparmor="DENIED"` в `journalctl -k`; добавить правило в `/etc/apparmor.d/local/<профиль>`; `apparmor_parser -r` |
| 27 | После установки auditd в `dmesg`/`kern.log` пропали сообщения AppArmor | Audit-сообщения ядра теперь забирает auditd | Смотреть `/var/log/audit/audit.log`, `ausearch -m AVC -ts recent` |
| 28 | PostgreSQL или сервер 1С перезапустились ночью «сами» | `unattended-upgrades` обновил библиотеку, а `needrestart` (24.04+) перезапустил зависимые службы | Исключения в `/etc/needrestart/conf.d/`; `Package-Blacklist`; `apt-mark hold`; обновления в окно обслуживания |
| 29 | Добавили корневой сертификат, а `curl`/`openssl verify` всё равно не доверяют | Файл не `.crt`, не PEM, либо не выполнен `update-ca-certificates` | Конвертировать в PEM, переименовать в `.crt`, положить в `/usr/local/share/ca-certificates/`, `sudo update-ca-certificates` |
| 30 | Удалили файл УЦ, а сертификат остался доверенным | Нужен `--fresh` | `sudo update-ca-certificates --fresh` |
| 31 | Браузер/клиент ругается на самоподписанный сертификат: имя не совпадает, хотя `CN` верный | В сертификате нет `subjectAltName` | Перевыпустить с `-addext "subjectAltName=DNS:...,IP:..."`; при подписи CSR — `-copy_extensions copyall` |
| 32 | `openssl pkcs12`: `digital envelope routines::unsupported` | Старый PFX (RC2-40) в OpenSSL 3.x | Добавить `-legacy` |
| 33 | Windows не принимает PFX, созданный в Ubuntu («неверный пароль») | Новые алгоритмы PFX (AES-256/PBKDF2) не понимают старые Windows/Java | Экспорт с `-legacy` |
| 34 | `openssl s_client`: `Verify return code: 21 (unable to verify the first certificate)` | Веб-сервер отдаёт только свой сертификат без промежуточных | В `SSLCertificateFile` указывать fullchain (сертификат + промежуточные) |
| 35 | certbot: `Timeout during connect (likely firewall problem)` | Порт 80 недоступен из интернета | Открыть 80/tcp, либо DNS-01, либо внутренний УЦ |
| 36 | В старой инструкции для 1С: `kernel.shmmax=...`, `kernel.sem=250 32000 100 128`, `fs.aio-max-nr=1048576` | Наследие ядер 2.6/Oracle | Не применять; современные значения по умолчанию выше, PostgreSQL использует mmap и POSIX-семафоры |
| 37 | fail2ban заблокировал администратора | Свой адрес не в `ignoreip` | Через консоль ВМ: `sudo fail2ban-client set sshd unbanip <IP>`; добавить сеть в `ignoreip` |
| 38 | Ubuntu 26.04: после чистой установки/переноса конфигов строки из `/etc/sysctl.conf` не действуют после перезагрузки | В 26.04 нет ни `/etc/sysctl.conf`, ни симлинка `99-sysctl.conf`; `systemd-sysctl` читает только `sysctl.d` | Перенести строки в `/etc/sysctl.d/90-*.conf`; `sudo sysctl --system`; проверить `systemd-analyze cat-config sysctl.d` |
| 39 | Ubuntu 26.04 (ядро 7.0): PostgreSQL заметно медленнее, чем на 24.04, при той же конфигурации | Известная проблема из release notes 26.04: изменение в Linux 7.0 даёт деградацию PostgreSQL на системах без huge pages | Настроить huge pages и `huge_pages = on` (раздел 6.4); `SHOW huge_pages_status;` должно быть `on` |
| 40 | Свой профиль tuned «не находится» (`tuned-adm profile …`: profile not found) | Профиль положен в `/etc/tuned/profiles/<имя>/` на Ubuntu 22.04/24.04 (там плоская раскладка `/etc/tuned/<имя>/`) либо наоборот — в `/etc/tuned/<имя>/` на 26.04 | Переложить каталог профиля; `tuned-adm list profiles` |
| 41 | Сервер 1С падает, а дампа нет, хотя в `limits.conf` для `usr1cv8` задано `core unlimited` (как в документации 1С) | Сервер запущен службой systemd: `limits.conf` на неё не действует, а умолчание Debian/Ubuntu — `LimitCORE=0:infinity`; кроме того, `core_pattern` перехватывает `apport` | `LimitCORE=infinity` в drop-in юнита; свой `kernel.core_pattern` в `/etc/sysctl.d/` и отключённый `apport` либо `systemd-coredump`; проверка `grep -i core /proc/<pid rphost>/limits` |
| 42 | Платформа 8.5.4+: «лицензия не найдена», хотя Менеджер Лицензий запущен и порты 475/1544 открыты | Системное время на компьютере Менеджера Лицензий и на компьютере приложения расходится больше чем на 20 минут [1С, ИТС № 6041] | Синхронизировать время на всех узлах (chrony), `chronyc tracking`; смотреть «Журнал поиска лицензии» |
| 43 | После добавления исключений needrestart начал предлагать/выполнять перезапуск `dbus`, `NetworkManager`, `systemd-logind` и т. п. | В `conf.d` использовано присваивание `$nrconf{override_rc} = { ... };`, которое заменило встроенный список исключений целиком | Использовать добавление ключей `$nrconf{override_rc}{qr(^имя)} = 0;` либо повторить в своём хеше нужные встроенные исключения; проверить `sudo needrestart -r l` |
| 44 | `apt install postgresql` выполнен в сеансе с `LANG=ru_RU.UTF-8`, а кластер `main` всё равно `en_US.UTF-8`/`C.UTF-8` | Скрипт пакета сбрасывает окружение и берёт системную локаль (`/etc/default/locale`), при её отсутствии — `C.UTF-8` | `sudo update-locale LANG=ru_RU.UTF-8` до установки либо пересоздать кластер с `--locale ru_RU.UTF-8` |
| 45 | После переноса каталога данных/обновления ОС `psql` не показывает предупреждений о версии сортировки, но в базе 1С запросы «теряют» строки, появляются дубли в уникальных индексах | Строковые поля 1С — `mchar`/`mvarchar`, сравнение через ICU; версия ICU сменилась, а механизм `collation version mismatch` PostgreSQL эти типы не отслеживает | Безусловный `reindexdb` всех баз после смены ОС/сборки PostgreSQL; надёжнее — логический перенос (`pg_dump`/`.dt`) |

Примечание: точные тексты сообщений в строках 6, 13, 17, 20, 21, 32, 35, 40 приведены по памяти (⚠ не подтверждено дословно) — ищите по ключевым словам, а не по полному совпадению. Текст в строке 19 и предупреждение в строке 22 соответствуют формулировкам из исходного кода PostgreSQL (подстановки имён — условные).

---

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Показать параметр ядра | `sysctl vm.swappiness` |
| Изменить до перезагрузки | `sudo sysctl -w vm.swappiness=10` |
| Постоянно | файл `/etc/sysctl.d/90-1c-postgres.conf` → `sudo sysctl --system` |
| Итоговая конфигурация sysctl.d | `systemd-analyze cat-config sysctl.d` |
| Память и swap | `free -h`; `swapon --show`; `grep -E 'Commit|Dirty|Huge' /proc/meminfo` |
| Кого убил OOM killer | `sudo journalctl -k \| grep -iE 'oom\|killed process'` |
| Лимиты текущей оболочки | `ulimit -a` |
| Лимиты процесса | `cat /proc/<pid>/limits`; `sudo prlimit --pid <pid>` |
| Лимиты службы | `systemctl show <юнит> -p LimitNOFILE -p TasksMax` |
| Изменить лимиты службы | `sudo systemctl edit <юнит>` → `[Service]` `LimitNOFILE=65536` → restart |
| Имена юнитов 1С и PostgreSQL | `systemctl list-units --type=service \| grep -iE 'srv1cv8\|postgres'` |
| Сколько файлов открыто у процесса | `sudo ls /proc/<pid>/fd \| wc -l` |
| Состояние THP | `cat /sys/kernel/mm/transparent_hugepage/enabled` |
| Отключить THP сейчас | `echo never \| sudo tee /sys/kernel/mm/transparent_hugepage/enabled` |
| Отключить THP навсегда | `transparent_hugepage=never` в `/etc/default/grub` → `sudo update-grub` → reboot |
| Сколько huge pages нужно PostgreSQL | (сервер остановлен) `sudo -u postgres /usr/lib/postgresql/17/bin/postgres -D /var/lib/postgresql/17/main -c config_file=/etc/postgresql/17/main/postgresql.conf -C shared_memory_size_in_huge_pages` |
| Зарезервировать huge pages | `sudo sysctl -w vm.nr_hugepages=N` + файл в `/etc/sysctl.d/` |
| Проверить huge pages | `grep -i huge /proc/meminfo`; `psql -c "SHOW huge_pages_status;"` |
| Параметры загрузки ядра | `cat /proc/cmdline`; правка `/etc/default/grub` → `sudo update-grub` |
| Governor CPU | `cpupower frequency-info`; `sudo cpupower frequency-set -g performance` |
| Профиль tuned | `tuned-adm active`; `sudo tuned-adm profile <имя>`; `tuned-adm list profiles` |
| Время и пояс | `timedatectl`; `sudo timedatectl set-timezone Europe/Moscow` |
| Включить синхронизацию | `sudo timedatectl set-ntp true` |
| Статус timesyncd | `timedatectl timesync-status` |
| Статус chrony | `chronyc tracking`; `chronyc sources -v`; `chronyc sourcestats` |
| Исправить время скачком | `sudo chronyc makestep` |
| Перечитать источники chrony | `sudo chronyc reload sources` |
| Источник времени Hyper-V | `ls -l /dev/ptp_hyperv`; `refclock PHC /dev/ptp_hyperv poll 3 dpoll -2 offset 0 stratum 2` |
| Текущая локаль | `locale`; `localectl status` |
| Доступные локали | `locale -a` |
| Сгенерировать русскую локаль | `sudo locale-gen ru_RU.UTF-8` |
| Системная локаль по умолчанию | `sudo update-locale LANG=ru_RU.UTF-8` |
| Интерактивная настройка локалей | `sudo dpkg-reconfigure locales` |
| Локаль баз PostgreSQL | `psql -c "SELECT datname, datcollate, datctype FROM pg_database;"` |
| Пересоздать кластер в ru_RU | `sudo pg_dropcluster --stop 17 main && sudo pg_createcluster --locale ru_RU.UTF-8 17 main --start` |
| Версия glibc | `ldd --version \| head -1` |
| Перестроить индексы после смены ОС | `sudo -u postgres reindexdb --all` → `ALTER DATABASE ... REFRESH COLLATION VERSION` |
| Шрифты MS без диалога | `echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" \| sudo debconf-set-selections && sudo apt-get install -y ttf-mscorefonts-installer` |
| Обновить кеш шрифтов | `sudo fc-cache -fv` |
| Какой шрифт подставится | `fc-match Arial`; `fc-list \| grep -i arial` |
| Состояние AppArmor | `sudo aa-status` |
| Отказы AppArmor | `sudo journalctl -k \| grep 'apparmor="DENIED"'` |
| Профиль в complain / enforce | `sudo aa-complain <путь>` / `sudo aa-enforce <путь>` |
| Перечитать профиль | `sudo apparmor_parser -r /etc/apparmor.d/<профиль>` |
| Обновить систему | `sudo apt update && sudo apt full-upgrade` |
| Нужна ли перезагрузка | `cat /var/run/reboot-required` |
| Проверить автообновления | `sudo unattended-upgrade -v --dry-run` |
| Заморозить пакет | `sudo apt-mark hold <пакет>`; `apt-mark showhold` |
| Статус fail2ban | `sudo fail2ban-client status sshd` |
| Разбанить адрес | `sudo fail2ban-client set sshd unbanip <IP>` |
| Правила аудита | `sudo auditctl -l`; `sudo augenrules --load` |
| Поиск событий аудита | `sudo ausearch -k <метка> -ts today -i` |
| Включённые службы | `systemctl list-unit-files --state=enabled` |
| Слушающие порты | `sudo ss -tulpn` |
| Аудит безопасности | `sudo lynis audit system` |
| Сгенерировать ключ | `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out server.key` |
| CSR с SAN | `openssl req -new -key server.key -out server.csr -subj "/CN=host" -addext "subjectAltName=DNS:host"` |
| Самоподписанный с SAN | `openssl req -x509 -newkey rsa:2048 -noenc -keyout k.key -out c.crt -days 825 -subj "/CN=host" -addext "subjectAltName=DNS:host,IP:10.0.0.5"` |
| Подписать CSR своим УЦ | `openssl x509 -req -in s.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out s.crt -days 825 -copy_extensions copyall` |
| Посмотреть сертификат | `openssl x509 -in c.crt -noout -text` |
| Срок действия | `openssl x509 -in c.crt -noout -dates` |
| Проверить цепочку | `openssl verify -CAfile ca.crt c.crt` |
| Проверить удалённый сервер | `openssl s_client -connect host:443 -servername host </dev/null` |
| PFX → PEM | `openssl pkcs12 -in c.pfx -out all.pem -noenc` |
| PEM → PFX | `openssl pkcs12 -export -inkey k.key -in c.crt -certfile chain.crt -out c.pfx` |
| DER → PEM | `openssl x509 -inform der -in c.der -out c.crt` |
| Добавить корневой УЦ в систему | `sudo cp ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates` |
| Удалить корневой УЦ | удалить файл → `sudo update-ca-certificates --fresh` |
| Сертификат Let's Encrypt | `sudo certbot --apache -d host`; `sudo certbot renew --dry-run` |
| Где задан параметр sysctl | `grep -rs <имя> /etc/sysctl.d /usr/lib/sysctl.d /run/sysctl.d /etc/sysctl.conf` |
| Есть ли `/etc/sysctl.conf` и симлинк на него | `ls -l /etc/sysctl.conf /etc/sysctl.d/99-sysctl.conf` |
| Умолчания лимитов systemd | `systemctl show -p DefaultLimitNOFILE -p DefaultLimitCORE -p DefaultLimitCORESoft -p DefaultLimitMEMLOCK -p DefaultTasksMax` |
| Лимиты для юнитов 1С любой версии | файл `/etc/systemd/system/srv1cv8-.service.d/limits.conf` → `sudo systemctl daemon-reload` → restart |
| OOM-защита postmaster | `cat /proc/$(pgrep -o postgres)/oom_score_adj` (ожидается `-900` у пакетов Debian/Ubuntu) |
| Core-дампы службы разрешены? | `grep -i core /proc/<pid>/limits`; `sysctl kernel.core_pattern` |
| Системная локаль (её берёт пакет PostgreSQL для кластера `main`) | `cat /etc/default/locale`; `localectl status` |
| Сгенерировать локаль универсально | раскомментировать `ru_RU.UTF-8 UTF-8` в `/etc/locale.gen` → `sudo locale-gen` |
| Версии правил сортировки баз (PG 15+) | `psql -c "SELECT datname, datcollversion, pg_database_collation_actual_version(oid) FROM pg_database;"` |
| С какой ICU слинкован `mchar` | `ldd $(pg_config --pkglibdir)/mchar.so \| grep -i icu` |
| Перейти на chrony после обновления до 26.04 | `sudo apt-mark auto systemd-timesyncd && sudo apt install chrony` |
| Работает ли NTS | `sudo chronyc -N authdata` (Mode: NTS, ненулевые KeyID/KLen) |
| Что перезапустил бы needrestart | `sudo needrestart -r l` |
| Раскладка профилей tuned | `ls -d /usr/lib/tuned/profiles 2>/dev/null \|\| ls /usr/lib/tuned` |
| Итоговая конфигурация «тюрьмы» fail2ban | `sudo fail2ban-client get sshd actions`; `sudo fail2ban-client -d \| grep sshd \| head` |
| Версия OpenSSL | `openssl version -a` |
| Файлы корневых сертификатов платформы 1С | `find /opt/1cv8 -name 'cacert*.pem'` |

---

## Источники

Официальная документация PostgreSQL:

- https://www.postgresql.org/docs/current/kernel-resources.html — (PostgreSQL 18) разделяемая память и семафоры на Linux, `RemoveIPC`, `fs.file-max`, `net.core.somaxconn`, `vm.overcommit_memory=2`, `oom_score_adj`/`PG_OOM_ADJUST_*`, расчёт и резервирование huge pages.
- https://www.postgresql.org/docs/current/runtime-config-resource.html — `huge_pages` (try/on/off, оговорка про THP), `huge_page_size`, `shared_memory_type`, `max_files_per_process` (1000), `io_method`/`io_workers`.
- https://www.postgresql.org/docs/current/runtime-config-preset.html — `shared_memory_size_in_huge_pages`, `huge_pages_status`, `num_os_semaphores`.
- https://www.postgresql.org/docs/current/app-postgres.html — опция `-C`; требование остановить сервер для вычисляемых параметров.
- https://www.postgresql.org/docs/current/locale.html — выбор локали в `initdb`, фиксация `LC_COLLATE`/`LC_CTYPE`, провайдеры локали.
- https://www.postgresql.org/docs/current/sql-altercollation.html и https://www.postgresql.org/docs/current/sql-alterdatabase.html — предупреждение о несовпадении версии правила сортировки, `REFRESH COLLATION VERSION`, запрос для поиска объектов.
- https://wiki.postgresql.org/wiki/Locale_data_changes — изменение данных локалей в glibc 2.28, затронутые дистрибутивы и сценарии, тест через `sort`.
- Список рассылки pgsql-announce / главная страница postgresql.org — актуальные версии (18.6, 17.11, 16.15 от 13.08.2026) и график выпуска PostgreSQL 19.

Postgres Professional:

- https://postgrespro.ru/docs/enterprise/17/config-one-c — приложение «Настройка Postgres Pro для решений 1С» (структура разделов).
- https://postgrespro.ru/docs/enterprise/17/one-c-configuring-locale — русская локаль до создания кластера (`dpkg-reconfigure locales`, `export LANG`, `pg-setup initdb`).
- https://postgrespro.ru/docs/enterprise/17/one-c-basic-server-requirements — требования к серверу: отключить гиперпоточность и энергосбережение, не выгружать разделяемую память.
- https://postgrespro.ru/docs/enterprise/17/one-c-configuring-server — `pgpro_tune`, пресет `1c.tune`, `max_files_per_process = 10000`.
- https://postgrespro.ru/docs/postgresql/17/kernel-resources — русский перевод главы об управлении ресурсами ядра.

1С (ИТС):

- https://its.1c.ru/db/metod8dev/content/5866/hdoc (то же: https://its.1c.ru/db/content/metod8dev/src/developers/scalability/administration/postgresql/i8105866.htm) — «Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2»: требования к оборудованию, HyperThreading/Energy Saving, `MALLOC_MMAP_THRESHOLD_=8192`, `max_files_per_process = 8000`, `ssl = off`. Страница открылась с искажённой кодировкой — цифры и идентификаторы взяты как есть, русские формулировки переданы по смыслу.
- https://its.1c.ru/db/content/metod8dev/src/developers/scalability/instructions/i8105953.htm — «Установка программы 1С:Предприятие 8 на Linux» (2018, 8.3.13, Ubuntu 16.04): `ttf-mscorefonts-installer`, `fc-cache -fv`, дополнительные библиотеки.
- https://its.1c.ru/db/content/metod8dev/src/developers/scalability/administration/linux/i8102799.htm — Kerberos-аутентификация для Linux-сервера 1С: шаг синхронизации времени с контроллером домена.

Ubuntu / Canonical:

- https://documentation.ubuntu.com/release-notes/26.04/ и https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — Ubuntu 26.04: ядро 7.0, glibc 2.43, systemd 259, chrony с NTS по умолчанию, sudo-rs, rust-coreutils, удаление cgroup v1, PostgreSQL 18, OpenSSH 10.2p1.
- https://documentation.ubuntu.com/release-notes/24.04/ — Ubuntu 24.04: ядро 6.8, glibc 2.39, systemd 255, поведение needrestart, ограничение unprivileged user namespaces.
- https://ubuntu.com/server/docs/how-to/networking/timedatectl-and-timesyncd/ , https://ubuntu.com/server/docs/how-to/networking/chrony-client/ , https://ubuntu.com/server/docs/how-to/networking/serve-ntp-with-chrony/ , https://ubuntu.com/server/docs/explanation/networking/about-time-synchronisation/ — timesyncd и chrony, NTS, файлы конфигурации, команды.
- https://ubuntu.com/server/docs/how-to/security/apparmor/ — AppArmor: пакеты, команды, каталоги, формат сообщений DENIED.
- https://ubuntu.com/server/docs/how-to/security/install-a-root-ca-certificate-in-the-trust-store/ — системное хранилище корневых сертификатов.
- https://ubuntu.com/server/docs/how-to/software/automatic-updates/ — unattended-upgrades, needrestart.
- https://ubuntu.com/server/docs/explanation/performance/perf-tune-cpupower/ и https://ubuntu.com/server/docs/explanation/performance/perf-tune-tuned/ — cpupower и TuneD в Ubuntu.
- https://manpages.ubuntu.com/manpages/noble/man8/sysctl.8.html , https://manpages.ubuntu.com/manpages/resolute/man8/sysctl.8.html , https://manpages.ubuntu.com/manpages/resolute/man5/sysctl.d.5.html — опции `sysctl`, порядок каталогов, формат файлов.
- https://manpages.ubuntu.com/manpages/noble/man5/limits.conf.5.html — формат `limits.conf`.
- https://manpages.ubuntu.com/manpages/noble/man5/systemd.exec.5.html , https://manpages.ubuntu.com/manpages/noble/man5/systemd-system.conf.5.html , https://manpages.ubuntu.com/manpages/noble/man5/systemd.resource-control.5.html — `Limit*=`, значения по умолчанию, `TasksMax=`.
- https://manpages.ubuntu.com/manpages/noble/man1/timedatectl.1.html — команды `timedatectl`.
- https://manpages.ubuntu.com/manpages/noble/man8/locale-gen.8.html , https://manpages.ubuntu.com/manpages/jammy/man8/update-locale.8.html , https://manpages.ubuntu.com/manpages/resolute/man8/update-locale.8.html — генерация локалей, файл системной локали по релизам.
- https://manpages.ubuntu.com/manpages/noble/man5/jail.conf.5.html — fail2ban: порядок файлов, параметры.

Ядро Linux:

- https://docs.kernel.org/admin-guide/sysctl/vm.html — `swappiness`, `overcommit_*`, `dirty_*`, `nr_hugepages`, `max_map_count`, `zone_reclaim_mode`.
- https://docs.kernel.org/admin-guide/sysctl/kernel.html — параметры `kernel.*` (в том числе какие `sched_*` остались).
- https://docs.kernel.org/networking/ip-sysctl.html — `tcp_keepalive_*`, `ip_local_port_range`, `somaxconn` и др.
- https://docs.kernel.org/admin-guide/mm/transhuge.html — THP: sysfs, значения, параметр ядра.
- https://docs.kernel.org/admin-guide/mm/hugetlbpage.html — HugeTLB: поля `/proc/meminfo`, `hugepages=`, sysfs.
- https://docs.kernel.org/filesystems/proc.html и https://www.kernel.org/doc/html/latest/mm/overcommit-accounting.html — формула `CommitLimit`, режимы overcommit, `oom_score_adj`.
- https://lkml.iu.edu/hypermail/linux/kernel/2104.3/03557.html — перенос параметров планировщика из sysctl в debugfs; https://lkml.iu.edu/hypermail/linux/kernel/2402.0/06333.html — `base_slice_ns` в EEVDF.

Прочее:

- https://learn.microsoft.com/en-us/azure/virtual-machines/linux/time-sync — синхронизация времени Linux-гостей Hyper-V/Azure: `hv_utils`, `/dev/ptp_hyperv`, строка `refclock PHC`, `makestep 1.0 -1`.
- https://docs.openssl.org/3.0/man1/openssl-req/ и https://docs.openssl.org/3.0/man1/openssl-pkcs12/ — опции `req` (`-addext`, `-copy_extensions`, `-noenc`), `pkcs12` (`-legacy`, алгоритмы по умолчанию).
- https://eff-certbot.readthedocs.io/en/stable/install.html — установка certbot (snap рекомендован), требование порта 80.
- https://cisofy.com/documentation/lynis/get-started/ — команды и файлы Lynis.
- https://github.com/redhat-performance/tuned (профили `postgresql`, `throughput-performance`) — значения параметров профилей.
- https://www.enterprisedb.com/blog/tuning-debian-ubuntu-postgresql — практика EDB (2021): sysctl, THP через GRUB, расчёт huge pages по VmPeak.
- https://habr.com/ru/post/458860/ — перевод статьи Percona (И. Ахмед, 2018) о параметрах ядра для PostgreSQL.
- https://www.postgrespro.ru/list/thread-id/2066122 — обсуждение «Two Necessary Kernel Tweaks for Linux Systems» (историческая рекомендация по `sched_migration_cost`).

Ограничения исследования (автор): лимит веб-поиска в сессии был исчерпан на середине работы, поэтому часть утверждений (помечены «⚠») написана по памяти и не сверена с первоисточником; статьи infostart.ru (HTTP 429) и wiki.astralinux.ru (HTTP 403) прочитать не удалось — сведения о них взяты из выдачи поиска.

### Дополнительно проверено при рецензии (2026-10-10)

Рецензия выполнялась без веб-поиска (лимит поиска на сессию был исчерпан) — только прямым чтением страниц первоисточников и локальных конспектов ИТС из этой базы знаний.

Пакеты и исходники Debian/Ubuntu:

- https://packages.ubuntu.com/jammy/amd64/procps/filelist , https://packages.ubuntu.com/noble/amd64/procps/filelist , https://packages.ubuntu.com/resolute/amd64/procps/filelist — наличие `/etc/sysctl.conf`, состав `/etc/sysctl.d/10-*.conf` (22.04/24.04) и `/usr/lib/sysctl.d/55-*.conf` (26.04), `10-map-count.conf`/`55-map-count.conf`.
- https://packages.ubuntu.com/noble/amd64/systemd/filelist , https://packages.ubuntu.com/resolute/amd64/systemd/filelist — симлинк `/etc/sysctl.d/99-sysctl.conf` есть в noble и отсутствует в resolute; `/usr/lib/systemd/system.conf.d/10-coredump-debian.conf` и `/usr/lib/sysctl.d/10-coredump-debian.conf` в resolute.
- https://changelogs.ubuntu.com/changelogs/pool/main/p/procps/procps_4.0.4-4ubuntu3/changelog — `vm.max_map_count=1048576` (2:4.0.4-4ubuntu2, LP: #2057792).
- https://packages.ubuntu.com/noble/all/tuned/filelist , https://packages.ubuntu.com/resolute/all/tuned/filelist — раскладка каталогов профилей tuned, наличие профиля `postgresql`.
- https://packages.ubuntu.com/search?keywords=openssl&searchon=names&exact=1&suite=all&section=all — версии OpenSSL по выпускам.
- https://sources.debian.org/src/systemd/unstable/debian/extra/system.conf.d/10-coredump-debian.conf/ — `DefaultLimitCORE=0:infinity`; https://sources.debian.org/src/systemd/bookworm/debian/rules/ — `-Dbump-proc-sys-fs-nr-open=false`.
- https://sources.debian.org/src/util-linux/unstable/debian/util-linux.su.pam/ (и то же для bullseye) — `pam_limits.so` в `/etc/pam.d/su` активен.
- https://sources.debian.org/data/main/p/postgresql-common/278/systemd/system/postgresql@.service — `OOMScoreAdjust=-900`; `.../278/pg_ctlcluster` — `PG_OOM_ADJUST_FILE`, запись `-900`; `.../278/pg_createcluster` — условия включения `ssl = on` со snakeoil-сертификатом; `.../278/debian/maintscripts-functions` — `set_system_locale`, `create_main_cluster`.
- https://sources.debian.org/src/glibc/unstable/debian/debhelper.in/locales.postinst/ и https://sources.debian.org/src/glibc/unstable/debian/local/usr_sbin/locale-gen/ — `/etc/locale.conf` + симлинк `/etc/default/locale`; `locale-gen` Debian без аргументов-локалей; https://changelogs.ubuntu.com/changelogs/pool/main/g/glibc/glibc_2.39-0ubuntu8/changelog — «Switch from /etc/default/locale to /etc/locale.conf» (2.37-6).
- https://sources.debian.org/src/fail2ban/unstable/debian/debian-files/jail.d_defaults-debian.conf/ и https://changelogs.ubuntu.com/changelogs/pool/universe/f/fail2ban/fail2ban_1.0.2-3ubuntu0.1/changelog — содержимое `defaults-debian.conf`, `banaction = nftables` и `backend = systemd` с 1.0.2-3.
- https://sources.debian.org/src/chrony/bookworm/debian/chrony.conf/ — `confdir`, `sourcedir`, `makestep 1 3`, `rtcsync` в `chrony.conf` пакета.
- https://sources.debian.org/src/msttcorefonts/unstable/debian/templates/ — шаблоны debconf пакета Debian (без EULA).

Документация и release notes:

- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ и https://documentation.ubuntu.com/release-notes/26.04/changes-since-previous-interim/ — chrony только для новых установок и команда перехода; `gnuls`/`sudo.ws`; OpenSSL 3.5.6, chrony 4.8; известная проблема PostgreSQL на Linux 7.0 и рекомендация huge pages.
- https://documentation.ubuntu.com/release-notes/22.04/ и https://documentation.ubuntu.com/release-notes/24.04/ — версии компонентов 22.04; needrestart; ограничение user namespaces и файл `60-apparmor-namespace.conf`.
- https://manpages.ubuntu.com/manpages/jammy/man5/systemd-system.conf.5.html , https://manpages.ubuntu.com/manpages/noble/man5/systemd-system.conf.5.html — умолчания `DefaultLimit*` в systemd 249 и 255; https://manpages.ubuntu.com/manpages/jammy/man5/systemd.unit.5.html — drop-in по префиксу имени с дефисами и `тип.d/`.
- https://manpages.ubuntu.com/manpages/noble/man2/shmget.2.html , https://manpages.ubuntu.com/manpages/noble/man2/semget.2.html , https://manpages.ubuntu.com/manpages/noble/man2/semop.2.html , https://manpages.ubuntu.com/manpages/noble/man2/io_setup.2.html — умолчания SHMMAX/SHMALL, SEMMSL/SEMMNI/SEMOPM, `aio-max-nr`.
- https://manpages.ubuntu.com/manpages/noble/man8/update-locale.8.html , https://manpages.ubuntu.com/manpages/jammy/man8/locale-gen.8.html , https://manpages.ubuntu.com/manpages/noble/man8/locale-gen.8.html , https://manpages.ubuntu.com/manpages/resolute/man8/locale-gen.8.html — файл системной локали, опции `locale-gen`.
- https://docs.kernel.org/admin-guide/sysctl/fs.html , https://docs.kernel.org/admin-guide/sysctl/kernel.html — `nr_open`, `file-max`, `io_uring_disabled`, `core_pattern`, перечень оставшихся `sched_*`.
- https://github.com/torvalds/linux/commit/5e963f2bd4654a202a8a05aa3a86cb0300b10e6c — «sched/fair: Commit to EEVDF»: удаление `latency_ns`, `wakeup_granularity_ns`, `idle_min_granularity_ns`.
- https://raw.githubusercontent.com/redhat-performance/tuned/master/tuned-main.conf и профили `postgresql`, `virtual-guest`, `throughput-performance` в том же репозитории — `reapply_sysctl = 1`, значения профилей.
- https://raw.githubusercontent.com/liske/needrestart/master/ex/needrestart.conf — встроенный список `override_rc`, режимы `restart`.
- https://www.postgresql.org/support/versioning/ , https://www.postgresql.org/about/news/postgresql-19-beta-4-released-3386/ — актуальные минорные версии, статус PostgreSQL 19.
- https://www.postgresql.org/docs/17/release-17.html — появление `huge_pages_status` в PostgreSQL 17.
- https://postgrespro.ru/docs/postgrespro/17/mchar — `mchar`/`mvarchar` используют ICU для сравнения строк.
- https://chrony-project.org/doc/4.5/chronyd.html — опции `-q`/`-Q`.
- https://knowledge.broadcom.com/external/article?legacyId=1006427 — VMware: рекомендация NTP вместо периодической синхронизации Tools.
- https://www.virtualbox.org/manual/topics/AdvancedTopics.html — параметры `--timesync-*`, `GetHostTimeDisabled`.
- https://raw.githubusercontent.com/systemd/systemd/main/rules.d/50-udev-default.rules.in — симлинки `/dev/ptp_kvm`, `/dev/ptp_hyperv`.
- https://docs.openssl.org/3.5/man1/openssl-req/ , https://docs.openssl.org/3.5/man1/openssl-x509/ — опции `req`/`x509` в OpenSSL 3.5.
- https://certbot.eff.org/instructions?ws=apache&os=snap — команды установки certbot (симлинк в `/usr/local/bin`).
- https://letsencrypt.org/2025/12/02/from-90-to-45 — график сокращения срока сертификатов Let's Encrypt.

Локальные конспекты ИТС (первоисточник — документация платформы 8.3.27/8.5.1 и методические статьи its.1c.ru, открытые пользователем и законспектированные в этой базе знаний):

- `kb/its-docs/cs-gl04-zapusk-komponentov.md` — юнит `srv1cv8-A.B.C.D@.service`, `systemctl edit`, параметры `SRV1CV8_*`, init-скрипт `srv1cv83` только для E2K.
- `kb/its-docs/adm-pr03-sluzhebnye-fajly-p4.md` — дампы в Linux (`limits.conf`, `kernel.core_pattern`); `kb/its-docs/adm-pr03-sluzhebnye-fajly-p1.md` — `cacertnx.pem`/`cacert.pem`.
- `kb/its-docs/cs-gl03-ustanovka-komponentov-p2.md` — совпадение locale кластера PostgreSQL и информационной базы, `LANG=ru_RU.utf-8`, шаг синхронизации времени для Kerberos (`ntpdate main`).
- `kb/its-docs/adm-gl02-ustanovka-p1.md`, `adm-gl02-ustanovka-p2.md`, `adm-gl01-trebovaniya.md` — шрифты Microsoft Core Fonts, `~/.fonts`, поведение программы установки.
- `kb/its-docs/adm-pr04-komandnye-stroki-utilit-p3.md` — `ibcmd infobase create --locale`.
- `kb/its-metod/pg-nastrojki-postgresql-dlya-1c.md` — HyperThreading/Energy Saving, `ssl = off`, `max_files_per_process = 8000`, `MALLOC_MMAP_THRESHOLD_=8192`, запрет своппинга разделяемой памяти.
- `kb/its-metod/licenzii-hasp-java-api-prochee-administrirovanie.md` — статья ИТС № 6041: допуск 20 минут по системному времени для лицензирования 8.5.4+.

Что рецензии подтвердить не удалось (остались пометки «⚠»): конфигурация ядра Ubuntu для THP (`madvise`); содержимое штатного юнита сервера 1С (лимиты, окружение); граница версии «юнит-шаблон с 8.3.21»; приём аргументов-локалей `locale-gen` в 26.04; рекомендации Tantor и статья Infostart «SRE-Suite…» (значения остались «по выдаче поиска»); поведение `chronyd -Q` при работающей службе; текст ошибок 1С при несовпадении локали; отсутствие предупреждений PostgreSQL о смене версии ICU для `mchar`; расположение `cacert*.pem` в каталоге платформы на Linux.

