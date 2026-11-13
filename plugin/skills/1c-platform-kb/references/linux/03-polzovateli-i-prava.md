# Пользователи, группы, права доступа, sudo и ACL в Ubuntu Server (для связки «1С:Предприятие 8» + PostgreSQL)

> Область: локальные учётные записи и группы, системные пользователи сервисов (`postgres`, `usr1cv8`/`grp1cv8`, `www-data`), классические права POSIX, ACL, атрибуты файлов, sudo/su, PAM-лимиты, политика паролей и блокировка, SSH-ключи, диагностика «Permission denied» | Версии: Ubuntu Server 22.04 LTS (jammy), 24.04 LTS (noble), 26.04 LTS (resolute); платформа 1С 8.3.20+ … 8.3.27 и 8.5.x; PostgreSQL 14–18 (ванильный из Ubuntu/PGDG, сборка 1С, Postgres Pro) | Актуальность: 2026-10-10

Условные пометки в тексте:

- **[офиц.]** — утверждение взято из официальной документации (Canonical, PGDG, Postgres Professional, 1С, man-страницы).
- **[практика]** — практика сообщества (Инфостарт, Хабр, блоги интеграторов), официально не закреплена.
- **⚠ не подтверждено** — первоисточником проверить не удалось; перед применением проверьте на своей системе.

> Файл прошёл независимую проверку фактов 2026-10-10 (сверка с man-страницами jammy/noble/resolute, исходниками `postgresql-common`, документацией PostgreSQL 18, README и исходниками sudo-rs, репозиторием Postgres Pro для 1С). Документация 1С на ИТС (`v8327doc`, `v85*doc`) рецензенту недоступна (тело страниц не отдаётся без подписки), поэтому всё, что касается внутреннего устройства дистрибутива 1С, подтверждено только публикациями сообщества и помечено соответствующим образом. Команды для самостоятельной проверки спорных мест собраны в разделе 16.

---

## Кратко

1. Учётные записи лежат в трёх текстовых файлах: `/etc/passwd` (644, 7 полей), `/etc/shadow` (640 `root:shadow`, хэши и сроки паролей), `/etc/group` (644, 4 поля). Читать их надёжнее через `getent passwd|group|shadow ИМЯ` — эта команда учитывает и LDAP/SSSD.
2. В Ubuntu для людей используйте `adduser` (интерактивная обёртка: домашний каталог `0750`, `/etc/skel`, запрос пароля), а `useradd` — низкоуровневая утилита для скриптов: без `-m` домашний каталог **не создаётся**, оболочка по умолчанию `/bin/sh`, пароль заблокирован.
3. Добавить пользователя в дополнительную группу: `sudo usermod -aG ГРУППА ПОЛЬЗОВАТЕЛЬ`. Без `-a` список дополнительных групп **заменяется** (можно потерять группу `sudo`). Новое членство действует только для новых сессий; работающую службу нужно перезапустить.
4. Системные учётные записи сервисов: `postgres` (дом `/var/lib/postgresql`, оболочка `/bin/bash`, пароль заблокирован), `usr1cv8` с группой `grp1cv8` (от него работают `ragent`/`rmngr`/`rphost`, данные кластера в `/home/usr1cv8/.1cv8/1C/1cv8`), `www-data` (UID/GID 33, дом `/var/www`, оболочка `/usr/sbin/nologin`).
5. Войти «под сервисом»: `sudo -u postgres psql`, `sudo -iu postgres`, `sudo -u usr1cv8 -s`; для учётки с `nologin` — `sudo -u www-data bash` или `sudo su -s /bin/bash - www-data`.
6. Права: `chmod 750 каталог`, `chmod -R u=rwX,g=rX,o= каталог`, `chown -R usr1cv8:grp1cv8 каталог`. Чтобы пройти по пути, нужен бит `x` на **каждом** каталоге цепочки.
7. Спецбиты: SUID `4000`, SGID `2000` (на каталоге — новые файлы наследуют группу каталога), sticky `1000` (как на `/tmp`, удалять может только владелец). Общий каталог для нескольких учёток: `chmod 2770` + ACL по умолчанию.
8. Каталог данных PostgreSQL: строго `0700` (или `0750`, если кластер создан с `initdb --allow-group-access`), владелец — пользователь сервера (`postgres`). При других правах сервер не стартует. **[офиц.]**
9. ACL: `setfacl -m u:usr1cv8:rwX каталог` (точечно), `setfacl -d -m u:usr1cv8:rwX каталог` (наследование для новых объектов), `getfacl каталог` (проверка). Реальные права именованных записей ограничены маской (`mask::`).
10. Атрибуты: `chattr +i файл` (неизменяемый даже для root), `chattr +a файл` (только дозапись), `lsattr файл`. «Operation not permitted» у root — первым делом `lsattr`.
11. sudo: правила — в `/etc/sudoers` и файлах `/etc/sudoers.d/*` (имя без точки и без `~` на конце, права `0440`), редактировать только через `visudo` / `visudo -f /etc/sudoers.d/ИМЯ`, проверять `visudo -c`. Члены группы `sudo` получают полный root.
12. **Ubuntu 26.04: `sudo` — это `sudo-rs`** (переписан на Rust). Нет `Defaults logfile`, нет журналирования ввода-вывода (`log_input`/`log_output`, `sudoreplay`), нет `sudo -E`, шаблоны `*` в аргументах команд разрешены только как последний отдельный аргумент, пароль по умолчанию отображается звёздочками. Классический sudo доступен как `sudo.ws`. **[офиц.]**
13. Пароль от sudo кэшируется 15 минут (`timestamp_timeout`), попыток ввода 3 (`passwd_tries`). `sudo -l` — что мне разрешено, `sudo -k` — сбросить кэш.
14. root в Ubuntu по умолчанию без пароля (вход под ним закрыт); администрирование — через пользователя из группы `sudo`. Это и есть схема «администратор без пароля root».
15. `/etc/security/limits.conf` действует только на PAM-сессии (ssh, консоль, su, sudo). На службы systemd (сервер 1С, PostgreSQL, Apache) **не действует** — для них лимиты задаются в юните: `LimitNOFILE=`, `LimitNPROC=`, `LimitCORE=`.
16. `passwd -l` / `usermod -L` блокируют только пароль (в хэш добавляется `!`); вход по SSH-ключу остаётся. Полная блокировка: `usermod -L -e 1 ИМЯ` плюс удаление/переименование `authorized_keys`.
17. Блокировка после неудачных попыток — `pam_faillock` (`/etc/security/faillock.conf`: `deny=3`, `fail_interval=900`, `unlock_time=600` по умолчанию); снять: `faillock --user ИМЯ --reset`. В Ubuntu по умолчанию **не включён**.
18. SSH-ключи: `~/.ssh` — `700`, `~/.ssh/authorized_keys` — `600`, домашний каталог не должен быть доступен на запись группе/остальным, иначе `sshd` (StrictModes) молча игнорирует ключи.
19. Диагностика «Permission denied»: `namei -l /полный/путь`, `sudo -u usr1cv8 test -r /путь && echo OK`, `getfacl`, `lsattr`, `findmnt -T /путь`, затем AppArmor: `sudo dmesg | grep 'apparmor="DENIED"'`.
20. Самая частая ловушка Ubuntu: домашние каталоги создаются с правами `0750`, поэтому `postgres`, `usr1cv8` и `www-data` **не видят** файлы в `/home/admin/...`. Дампы, выгрузки и дистрибутивы кладите в `/srv`, `/var/tmp`, `/opt` или отдельный общий каталог.
21. `adduser` различается между LTS: в 22.04 (3.118) комментарий задаётся только `--gecos`, а `adduser --system` **создаёт** `/home/ИМЯ`; в 24.04/26.04 — `--comment`, дом системной учётки `/nonexistent`. `usermod -rG` есть только в 24.04+. В переносимых скриптах указывайте `--home`/`--no-create-home` явно. **[офиц.]**
22. Файлы PostgreSQL в Ubuntu: `pg_hba.conf` и `pg_ident.conf` — `postgres:postgres 0640`, `postgresql.conf` — `0644`, журнал `/var/log/postgresql/postgresql-NN-main.log` — `postgres:adm 0640` (читают члены группы `adm`). **[офиц., исходники `pg_createcluster`]**
23. Всё, что касается внутреннего устройства дистрибутива 1С (оболочка и UID `usr1cv8`, владелец `/opt/1cv8`, расположение `conf`/`logcfg.xml` в 8.3.20+, права `/var/1C/licenses`, платформа 8.5), подтверждено только практикой сообщества — документация ИТС без подписки недоступна. Перед действиями на рабочем сервере выполните блок самопроверки из раздела 16.

---

## 1. Версии и отличия между LTS

| Что | Ubuntu 22.04 (jammy) | Ubuntu 24.04 (noble) | Ubuntu 26.04 (resolute, вышла 23.04.2026) |
|---|---|---|---|
| `sudo` | классический sudo 1.9.9 (sudo.ws) | классический sudo 1.9.15p5 | **sudo-rs** 0.2.13 (пакет `sudo-rs` 0.2.13-0ubuntu1.x), классический — `sudo.ws` |
| coreutils (`chmod`, `chown`, `id`, `ls` …) | GNU | GNU | **rust-coreutils (uutils)** 0.10.0; `cp`, `mv`, `rm` пока GNU; GNU-версии доступны с префиксом `gnu` (например `gnuls`) |
| `adduser` | 3.118ubuntu5 (только `--gecos`, `--force-badname`, `--add_extra_groups`; `--system` создаёт дом по общим правилам) | 3.137ubuntu1 (`--comment`, `--gecos` устарела; дом системной учётки — `/nonexistent`) | 3.153ubuntu1 |
| `passwd`, `useradd`, `usermod` (shadow) | 4.8.1 (нет `usermod -r`) | 4.13 | 4.17.4 |
| `su`, `namei`, `last` | util-linux 2.37.2 | util-linux 2.39.3 | util-linux 2.41.3; `last` — из пакета **wtmpdb** (0.75.0) |
| Последний вход | `lastlog` (`/var/log/lastlog`) | `lastlog` | **`lastlog2`** (`/var/lib/lastlog/lastlog2.db`) |
| OpenSSH | 8.9p1 | 9.6p1 | 10.2p1 (`sshd.service` — псевдоним `ssh.service`, DSA удалён) |
| PostgreSQL в репозитории Ubuntu | 14 | 16 | 18 |
| systemd | 249 (249.11) | 255 | 259 (cgroup v1 удалён) |
| PAM (`libpam-modules`) | 1.4.0 | 1.5.3 | 1.7.0 |
| Блокировка после неудачных входов | `pam_faillock` (pam_tally2 удалён) | `pam_faillock` | `pam_faillock` |

Источники версий: release notes Ubuntu 26.04 (дата выпуска — 23 апреля 2026 г., поддержка до апреля 2031 г.), строки «Provided by» на manpages.ubuntu.com для jammy/noble/resolute (см. раздел «Источники»). Версии в таблице сверены по этим страницам **[офиц.]**; исключения — PostgreSQL 14/16 в репозиториях 22.04/24.04 и удаление `pam_tally2` (общеизвестные сведения, отдельной страницей не сверялись; наличие `pam_faillock` в 22.04 подтверждено man-страницей jammy).

Актуальная стабильная ветка PostgreSQL на 10.10.2026 — **18** (текущий минорный выпуск 18.6); PostgreSQL 19 — в бета-тестировании (Beta 4 вышла 24.09.2026). Поддержка PostgreSQL 14 (версия из Ubuntu 22.04) сообществом заканчивается 12.11.2026 **[офиц., postgresql.org/support/versioning]**. На ИТС опубликована документация платформы 1С для версий 8.3.6 … 8.3.27, 8.5.1 и 8.5.4.

Сборка Postgres Pro для 1С (`repo.postgrespro.ru/1c/`) на 10.10.2026 доступна для веток 14, 15, 16, 17, 18 (`1c-14` … `1c-18`); для ветки 17 (17.10) заявлены Ubuntu 22.04, 24.04, 25.10 и 26.04 **[офиц., meta.json репозитория]**.

Практический вывод: скрипты и правила sudoers, написанные для 22.04/24.04, при переходе на 26.04 нужно проверить на совместимость с sudo-rs (раздел 10.8) и, реже, с uutils.

---

## 2. Базы учётных записей: /etc/passwd, /etc/shadow, /etc/group

### 2.1. /etc/passwd

Одна строка — одна учётная запись, 7 полей через двоеточие:

```
имя:x:UID:GID:комментарий(GECOS):домашний_каталог:оболочка
```

Примеры (значения UID/GID у динамических системных учёток на разных серверах различаются; комментарий, оболочка и тип UID в строке `usr1cv8` показаны условно — ⚠ не подтверждено: первоисточника с выводом `getent passwd usr1cv8` для единого установщика 8.3.20+ найти не удалось, зависят от версии установщика 1С; на своём сервере смотрите `getent passwd usr1cv8`):

```
root:x:0:0:root:/root:/bin/bash
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
postgres:x:114:120:PostgreSQL administrator,,,:/var/lib/postgresql:/bin/bash
usr1cv8:x:999:1001:1C Enterprise 8 server launcher:/home/usr1cv8:/bin/sh
admin1c:x:1000:1000:Administrator 1C,,,:/home/admin1c:/bin/bash
```

- `x` во втором поле — пароль хранится в `/etc/shadow`.
- Диапазоны UID в Ubuntu **[офиц.]**: 0–99 — статические системные (из пакета `base-passwd`), 100–999 — динамические системные (создаются пакетами), 1000–59999 — обычные пользователи, 65534 — `nobody`.
- Оболочка `/usr/sbin/nologin` (или `/bin/false`) — интерактивный вход запрещён; служба при этом работает нормально.
- Права файла: `-rw-r--r-- root root` (644). Читать может любой пользователь.

### 2.2. /etc/shadow

9 полей:

```
имя:хэш:дата_смены:мин_дней:макс_дней:предупреждение:неактивность:срок_учётки:резерв
```

- Хэш начинается с идентификатора алгоритма: `$y$` — yescrypt (по умолчанию в Ubuntu 22.04+, задаётся опцией `yescrypt` модуля `pam_unix` в `/etc/pam.d/common-password`), `$6$` — SHA-512. Подтверждено профилем `debian/pam-configs/unix` пакета pam: `Password: [success=end default=ignore] pam_unix.so obscure use_authtok try_first_pass yescrypt` **[офиц., исходники пакета]**. На странице Ubuntu Server «User management» в примере до сих пор стоит `pam_unix.so obscure sha512` — это устаревший текст документации; фактическое значение на сервере: `grep pam_unix /etc/pam.d/common-password`. Старые хэши `$6$` продолжают работать и заменяются на `$y$` при следующей смене пароля.
- `!` или `*` в поле хэша — войти по паролю нельзя. `!` перед настоящим хэшем — пароль заблокирован командой `passwd -l` / `usermod -L` (снимается `passwd -u`).
- Даты — в днях от 01.01.1970. `срок_учётки = 1` — учётная запись отключена целиком.
- Права: `-rw-r----- root shadow` (640). Обычный пользователь прочитать не может.

Просмотр в удобном виде:

```bash
sudo getent shadow postgres      # строка из shadow
sudo passwd -S postgres          # статус: L — заблокирован, P — есть пароль, NP — без пароля
sudo chage -l admin1c            # сроки действия пароля и учётной записи
```

### 2.3. /etc/group и /etc/gshadow

```
имя_группы:x:GID:список,дополнительных,членов
```

```
sudo:x:27:admin1c
grp1cv8:x:1001:
postgres:x:120:
ssl-cert:x:115:postgres
```

- В четвёртом поле перечислены только **дополнительные** члены. Основная группа пользователя задаётся полем GID в `/etc/passwd` и в этом списке не дублируется (поэтому у `grp1cv8` список пуст, хотя `usr1cv8` в ней состоит).
- `/etc/gshadow` (640 `root:shadow`) — пароли и администраторы групп; на практике почти не используется.

### 2.4. Правильное чтение и безопасная правка

```bash
getent passwd usr1cv8            # запись пользователя (в т.ч. из LDAP/SSSD)
getent group grp1cv8             # запись группы
getent passwd | cut -d: -f1      # все имена
getent passwd | awk -F: '$3>=1000 && $3<60000 {print $1}'   # только «люди»
sudo vipw                        # правка /etc/passwd с блокировкой файла
sudo vigr                        # правка /etc/group
sudo pwck -r ; sudo grpck -r     # проверка целостности (только чтение)
```

Вручную редактировать `passwd`/`shadow`/`group` обычным редактором не следует: при ошибке формата можно потерять возможность входа.

### 2.5. Файлы настроек по умолчанию

| Файл | Что задаёт |
|---|---|
| `/etc/adduser.conf` | поведение `adduser`: `DSHELL=/bin/bash`, `DHOME=/home`, `DIR_MODE=0750`, диапазоны `FIRST_UID=1000`, `LAST_UID=59999`, `FIRST_SYSTEM_UID=100`, `LAST_SYSTEM_UID=999`, `EXTRA_GROUPS`, `NAME_REGEX` |
| `/etc/default/useradd` | умолчания `useradd`: `SHELL=/bin/sh`, `HOME=/home`, `SKEL=/etc/skel`, `INACTIVE=-1`, `EXPIRE=` |
| `/etc/login.defs` | `UMASK 022`, `USERGROUPS_ENAB yes`, `HOME_MODE 0750`, `UID_MIN 1000`, `UID_MAX 60000`, `SYS_UID_MIN`/`SYS_UID_MAX`, `PASS_MAX_DAYS 99999`, `PASS_MIN_DAYS 0`, `PASS_WARN_AGE 7`, `ENCRYPT_METHOD` |
| `/etc/skel/` | шаблон содержимого нового домашнего каталога (`.bashrc`, `.profile`, `.bash_logout`) |

Уточнения по результатам проверки:

- `/etc/default/useradd`: в поставляемом файле **активна только строка `SHELL=/bin/sh`**; строки `GROUP=100`, `HOME=/home`, `INACTIVE=-1`, `EXPIRE=`, `SKEL=/etc/skel`, `CREATE_MAIL_SPOOL=no` закомментированы (это встроенные умолчания `useradd`, их показывает `useradd -D`) **[офиц., исходники пакета shadow]**.
- `/etc/adduser.conf`: man-страница `adduser.conf(5)` (noble) описывает умолчание Debian `DIR_MODE=0700` и `SYS_DIR_MODE=0755`; Ubuntu поставляет файл с `DIR_MODE=0750` — документация Ubuntu Server: домашние каталоги создаются с «private permissions (`0750`)» **[офиц.]**. Изменение введено в Ubuntu 21.04 (пакеты `adduser` и `shadow`); на существующие каталоги и на обновлённые системы оно не действует — права старых домашних каталогов остаются прежними (часто `0755`).
- `/etc/login.defs`: `HOME_MODE 0750` (действует на `useradd -m`) подтверждено журналом изменений пакета shadow в Ubuntu: 1:4.8.1-1ubuntu8 (21.04) — «Set HOME_MODE=750 in login.defs to enable private home directories», и та же правка «d/login.defs: Enable private home directories by default» перенесена в версии для 22.04 (1:4.8.1-2ubuntu1) и 24.04 (1:4.13+dfsg1-4ubuntu1) **[офиц., changelogs.ubuntu.com]**. Смысл параметра по man `useradd(8)`: «The mode for new home directories. If not specified, the UMASK is used to create the mode». `USERGROUPS_ENAB yes` — умолчание Debian, на которое ссылается man `pam_umask(8)`; сам поставляемый файл рецензент не читал (⚠ проверьте `grep` ниже). `ENCRYPT_METHOD` в `login.defs` исторически `SHA512` (с shadow 4.1.5), но на хэши, создаваемые через PAM (`passwd`), влияет не он, а опция `yescrypt` модуля `pam_unix` (раздел 2.2).
- Проверка фактических значений на сервере:

  ```bash
  grep -E '^#?(DSHELL|DHOME|DIR_MODE|SYS_DIR_MODE|FIRST_UID|LAST_UID|FIRST_SYSTEM_UID|LAST_SYSTEM_UID|EXTRA_GROUPS|USERGROUPS)=' /etc/adduser.conf
  grep -E '^(UMASK|HOME_MODE|USERGROUPS_ENAB|UID_MIN|UID_MAX|SYS_UID_MIN|SYS_UID_MAX|PASS_MAX_DAYS|PASS_MIN_DAYS|PASS_WARN_AGE|ENCRYPT_METHOD)' /etc/login.defs
  grep -v '^#' /etc/default/useradd ; useradd -D
  ```

  В новых версиях `adduser` файл `/etc/adduser.conf` может поставляться с закомментированными строками (`#DIR_MODE=…`): закомментированная строка показывает встроенное умолчание, а не действующую настройку администратора (⚠ по памяти рецензента). Самая надёжная проверка результата — создать пробную учётку и посмотреть права: `sudo adduser --disabled-password --comment test probe1 && stat -c '%a %U:%G %n' /home/probe1 && sudo deluser --remove-home probe1` (в 22.04 вместо `--comment` — `--gecos`).

---

## 3. Создание и изменение пользователей и групп

### 3.1. adduser и useradd — в чём разница

| | `adduser` (Debian/Ubuntu, Perl-обёртка) | `useradd` (пакет `passwd`, низкий уровень) |
|---|---|---|
| Режим | интерактивный: спрашивает пароль и ФИО | неинтерактивный, всё через ключи |
| Домашний каталог | создаёт (`/home/ИМЯ`, права из `DIR_MODE=0750`), копирует `/etc/skel` | создаёт **только с `-m`**; права из `HOME_MODE` |
| Оболочка | `DSHELL=/bin/bash` | `SHELL=/bin/sh` из `/etc/default/useradd` |
| Пароль | запрашивает (или `--disabled-password`) | не задаёт — учётка с заблокированным паролем, нужен `passwd ИМЯ` |
| Одноимённая группа | создаёт | создаёт, если `USERGROUPS_ENAB yes` |
| Системная учётка | `adduser --system`: оболочка `/usr/sbin/nologin`, основная группа `nogroup`, если нет `--group`/`--ingroup`. **Домашний каталог зависит от версии:** в 24.04/26.04 (adduser 3.137+) — `/nonexistent`, не создаётся; в **22.04 (adduser 3.118) — создаётся по тем же правилам, что и у обычного пользователя (`/home/ИМЯ`)**, если не указать `--home` или `--no-create-home` **[офиц., man adduser jammy/noble]** | `useradd -r`: UID из системного диапазона, без домашнего каталога (если нет `-m`), без сроков в shadow |
| Рекомендация | man useradd: «On Debian, administrators should usually use adduser(8) instead» **[офиц.]** | для скриптов и переносимых инструкций |

`adduser` — основные формы и ключи (24.04/26.04):

```bash
sudo adduser ivanov                         # обычный пользователь, диалог
sudo adduser --disabled-password --comment "Backup operator" backupop   # без пароля (вход только по ключу / sudo -u)
sudo adduser --system --group --home /srv/svc1 --shell /usr/sbin/nologin svc1   # системная учётка со своей группой
sudo adduser ivanov sudo                    # добавить существующего пользователя в существующую группу
sudo addgroup exch1c                        # создать группу
sudo addgroup --system grp1clogs            # системная группа (GID из диапазона 100–999)
```

Ключи: `--system`, `--group`, `--ingroup ГРУППА`, `--home КАТАЛОГ`, `--no-create-home`, `--shell ОБОЛОЧКА`, `--uid N`, `--gid N`, `--comment "текст"` (в 22.04 — `--gecos "текст"`; в 24.04+ `--gecos` помечена устаревшей), `--disabled-password` (не запускать `passwd`), `--disabled-login` (то же плюс оболочка `/usr/sbin/nologin`), `--add-extra-groups`, `--allow-bad-names`.

Отличия по версиям **[офиц., man adduser jammy 3.118ubuntu5 / noble 3.137ubuntu1 / resolute 3.153ubuntu1]**:

| Что | 22.04 (3.118) | 24.04 (3.137) и 26.04 (3.153) |
|---|---|---|
| Комментарий (GECOS) | только `--gecos "текст"`; опции `--comment` в man-странице **нет** — команда завершится ошибкой о неизвестной опции | `--comment "текст"`; `--gecos` — устаревший синоним («deprecated and will be removed after Debian bookworm»). В 24.04 `--gecos` заведомо работает (её использует postinst `postgresql-common` 257); ⚠ не подтверждено, что она ещё принимается в 26.04 — в новых скриптах только `--comment` |
| `--disabled-login` | только не запускает `passwd` (учётка непригодна для входа, пока не задан пароль); оболочку **не меняет** | не запускает `passwd` **и** ставит оболочку `/usr/sbin/nologin` |
| `--disabled-password` | как `--disabled-login`, но вход по SSH-ключу возможен | не запускает `passwd`; оболочка обычная, вход по ключу возможен |
| Дополнительные группы из `EXTRA_GROUPS` | `--add_extra_groups` (с подчёркиванием) | `--add-extra-groups` (старое написание устарело) |
| Ослабить проверку имени | `--force-badname` | `--allow-bad-names`; `--allow-all-names` — любые имена, допустимые для `useradd` |
| Дом системной учётки (`--system`) | `/home/ИМЯ`, создаётся | `/nonexistent`, не создаётся |
| Прочее | — | 26.04: `--firstuid`/`--lastuid`, `--stdoutmsglevel`, `--encrypt-home` |

Вывод для скриптов, которые должны работать на всех трёх LTS: системные учётки создавайте с **явными** `--home КАТАЛОГ` (или `--no-create-home`) и `--shell`, а комментарий задавайте через `useradd -c` либо проверяйте версию (`dpkg-query -W adduser`).

`useradd` — основные ключи:

| Ключ | Значение |
|---|---|
| `-m`, `--create-home` | создать домашний каталог |
| `-M` | не создавать, даже если включён `CREATE_HOME` |
| `-d КАТАЛОГ` | домашний каталог (по умолчанию `/home/ИМЯ`) |
| `-s ОБОЛОЧКА` | оболочка входа |
| `-g ГРУППА` | основная группа (должна существовать) |
| `-G гр1,гр2` | дополнительные группы (через запятую без пробелов) |
| `-r`, `--system` | системная учётка |
| `-u UID` | явный UID |
| `-c "комментарий"` | поле GECOS |
| `-e ГГГГ-ММ-ДД` | дата отключения учётной записи |
| `-U` / `-N` | создавать / не создавать одноимённую группу |
| `-k КАТАЛОГ` | шаблон вместо `/etc/skel` (только с `-m`) |
| `-D` | показать/изменить значения по умолчанию |

```bash
sudo useradd -m -s /bin/bash -c "Ivan Ivanov" -G sudo ivanov && sudo passwd ivanov
sudo useradd -r -s /usr/sbin/nologin -d /nonexistent svc_monitor
sudo useradd -D                              # текущие значения по умолчанию
```

### 3.2. usermod — изменение учётной записи

| Ключ | Что делает |
|---|---|
| `-aG гр1,гр2` | **добавить** в дополнительные группы (`-a` работает только вместе с `-G`) |
| `-G гр1,гр2` (без `-a`) | **заменить** список дополнительных групп — из остальных групп пользователь будет удалён |
| `-rG гр1` | удалить из указанных дополнительных групп (24.04+: shadow 4.13 и новее; в 22.04 с shadow 4.8.1 ключа `-r` нет — используйте `gpasswd -d ПОЛЬЗОВАТЕЛЬ ГРУППА` или `deluser ПОЛЬЗОВАТЕЛЬ ГРУППА`) **[офиц., man usermod jammy/noble/resolute]** |
| `-g ГРУППА` | сменить основную группу (файлы в домашнем каталоге перейдут к новой группе) |
| `-L` / `-U` | заблокировать / разблокировать пароль (`!` перед хэшем) |
| `-s ОБОЛОЧКА` | сменить оболочку |
| `-d КАТАЛОГ` | сменить домашний каталог; с `-m` — перенести содержимое |
| `-l НОВОЕ_ИМЯ` | переименовать логин (домашний каталог не переименовывается) |
| `-e ДАТА` | срок действия учётки (`-e 1` — отключить, `-e ""` — снять срок) |
| `-u UID` | сменить UID (файлы вне домашнего каталога придётся перечинить вручную) |
| `-c "текст"` | комментарий |

```bash
sudo usermod -aG sudo ivanov                 # дать полные права администратора
sudo usermod -aG grp1clogs usr1cv8           # сервер 1С — в группу чтения/записи техжурнала
sudo usermod -aG grp1clogs www-data
sudo usermod -s /usr/sbin/nologin oldadmin   # запретить интерактивный вход
sudo usermod -L -e 1 oldadmin                # полностью отключить учётную запись
sudo usermod -U -e "" oldadmin               # включить обратно
sudo usermod -d /srv/1c/home -m usr1cv8      # перенос домашнего каталога (службу 1С предварительно остановить)
```

Важно:

- Изменение UID, логина или домашнего каталога возможно, только когда у пользователя нет запущенных процессов **[офиц., man usermod]** — для `usr1cv8`/`postgres` сначала остановите службу.
- Новое членство в группах процесс получает **при старте сессии**. Человеку — перелогиниться (или `newgrp ГРУППА` в текущей оболочке); службе — `sudo systemctl restart ИМЯ_СЛУЖБЫ`. Проверка у работающего процесса: `grep Groups /proc/$(pgrep -o ragent)/status`.

### 3.3. Удаление: userdel, deluser, groupdel, delgroup

```bash
sudo deluser ivanov                      # удалить учётку, домашний каталог остаётся
sudo deluser --remove-home ivanov        # вместе с домашним каталогом и почтовым ящиком
sudo deluser --backup --remove-home ivanov   # перед удалением сделать архив в текущем каталоге
sudo deluser ivanov sudo                 # убрать пользователя из группы
sudo userdel -r ivanov                   # низкоуровневый аналог (-r — с домашним каталогом)
sudo delgroup exch1c ; sudo groupdel exch1c   # удалить группу
```

- Группу нельзя удалить, пока она является основной для какого-либо пользователя.
- После удаления пользователя его файлы вне домашнего каталога остаются с «голым» числовым UID. Найти: `sudo find / -xdev \( -nouser -o -nogroup \) 2>/dev/null`.

### 3.4. Группы: groupadd, groupmod, gpasswd, newgrp

```bash
sudo groupadd exch1c                     # обычная группа
sudo groupadd -r grp1clogs               # системная (-r)
sudo groupadd -g 2001 pgbackup           # с заданным GID (удобно для NFS/общих томов)
sudo groupmod -n newname oldname         # переименовать
sudo gpasswd -a usr1cv8 exch1c           # добавить пользователя в группу (аналог usermod -aG)
sudo gpasswd -d usr1cv8 exch1c           # удалить из группы
sudo gpasswd -M usr1cv8,postgres exch1c  # задать полный список членов
newgrp exch1c                            # новая оболочка с этой группой в качестве основной
sg exch1c -c "touch /srv/exchange/test"  # выполнить одну команду с группой
```

### 3.5. Пароли и сроки: passwd, chpasswd, chage

```bash
passwd                                   # сменить свой пароль
sudo passwd ivanov                       # задать пароль другому
sudo passwd -S ivanov                    # статус (L/P/NP, дата смены, min, max, warn, inactive)
sudo passwd -S -a                        # статус всех
sudo passwd -l ivanov ; sudo passwd -u ivanov   # заблокировать / разблокировать пароль
sudo passwd -e ivanov                    # потребовать смену пароля при следующем входе
sudo passwd -d ivanov                    # удалить пароль (учётка без пароля — опасно)
echo 'ivanov:N0v-Parol_2026' | sudo chpasswd    # задать пароль неинтерактивно (не оставляйте в history)

sudo chage -l ivanov                     # показать сроки
sudo chage -M 90 -m 1 -W 14 -I 30 ivanov # макс. 90 дней, мин. 1, предупреждать за 14, неактивность 30
sudo chage -d 0 ivanov                   # заставить сменить пароль при следующем входе
sudo chage -E 2026-12-31 ivanov          # учётная запись действует до даты
sudo chage -E -1 -M -1 ivanov            # снять срок учётки и срок пароля
```

Ключи `chage`: `-d` дата последней смены, `-E` срок учётной записи, `-I` дней неактивности после истечения пароля, `-m`/`-M` минимум/максимум дней между сменами, `-W` дней предупреждения, `-l` показать, `-i` даты в формате ISO.

Для сервисных учёток (`postgres`, `usr1cv8`, `www-data`) сроки паролей задавать нельзя: истёкшая учётная запись ломает `su`, cron и часть PAM-сессий. Проверка: `sudo chage -l postgres` — должно быть «never».

---

## 4. Кто есть кто и кто в системе: id, groups, getent, who, w, last, lastlog, loginctl

### 4.1. Сведения об учётной записи

```bash
id                               # свой uid, gid и все группы текущей сессии
id usr1cv8                       # uid=999(usr1cv8) gid=1001(grp1cv8) groups=1001(grp1cv8),1002(grp1clogs)
id -u postgres ; id -gn postgres ; id -nG postgres    # только UID / имя основной группы / имена всех групп
groups ivanov                    # список групп пользователя
getent group sudo                # кто входит в группу sudo
getent passwd 33                 # найти учётку по UID
whoami ; logname                 # эффективный пользователь / пользователь, вошедший в сессию
```

`id ИМЯ` читает базы заново, а `id` без аргументов показывает группы **текущего процесса**. Если только что выполнили `usermod -aG`, то `id ИМЯ` уже покажет новую группу, а `id` в старой сессии — ещё нет.

### 4.2. Кто сейчас вошёл и история входов

```bash
who                              # активные сессии: пользователь, терминал, время, откуда
who -b                           # время последней загрузки системы
w                                # то же плюс нагрузка и что запущено в каждой сессии
last -n 20                       # последние 20 входов/выходов
last -a -F -n 20 ivanov          # с полным временем, хост в последнем столбце, по пользователю
last reboot | head               # история перезагрузок
sudo lastb -n 20                 # неудачные попытки входа (22.04/24.04, читает /var/log/btmp)
lastlog                          # дата последнего входа каждого пользователя (22.04/24.04)
lastlog -u ivanov ; lastlog -b 90   # по пользователю / не входившие более 90 дней
```

Отличия Ubuntu 26.04 **[офиц., manpages resolute]**:

- `last` предоставляется пакетом **wtmpdb** (в 26.04 — версия 0.75.0; база SQLite `/var/log/wtmp.db`, а `/var/lib/wtmpdb/wtmp.db` — символьная ссылка с апстримного расположения на неё; устойчива к «проблеме 2038 года»); основные ключи (`-n`, `-a`, `-F`, `-i`, `-x`, `-s`, `-t`, `-f`) сохранены, поддерживаются также `-d` (DNS), `-p ВРЕМЯ` (кто был в системе в указанный момент), `-R` (без имени хоста), `-w` (полные имена), `--time-format` и новый `-S` (показывать PAM-сервис); полная форма — `wtmpdb last`. Другие подкоманды: `wtmpdb boot`, `wtmpdb shutdown`, `wtmpdb rotate -d ДНЕЙ` (перенос старых записей), `wtmpdb import -f /var/log/wtmp` (импорт старого файла).
- Вместо `lastlog` — **`lastlog2`** (пакет `lastlog2` из util-linux 2.41.3, база `/var/lib/lastlog/lastlog2.db`): `lastlog2`, `lastlog2 -u ivanov`, `lastlog2 -b 90`, `lastlog2 -t 7`, `lastlog2 -a` (только входившие), `lastlog2 -i /var/log/lastlog` (импорт старого файла; существующие записи перезаписываются), `lastlog2 -s` (показать PAM-сервис последнего входа), `lastlog2 -u ivanov -C` (очистить запись пользователя), `lastlog2 -u ivanov -S` (поставить текущее время), `lastlog2 -u ivanov -r НОВОЕ_ИМЯ` (переименовать запись), `lastlog2 -d ФАЙЛ` (другая база).
- `lastb` в 26.04: man-страницы `lastb` в разделе resolute на manpages.ubuntu.com **нет** (HTTP 404), а страница `last(1)` из wtmpdb о `lastb` не упоминает — исходите из того, что команды нет. В Debian 13, откуда взята эта связка, release notes прямо говорят: `util-linux` больше не содержит `last` и `lastb`, пакет `login` — `lastlog`; пакета-замены для `lastb` нет, похожие сведения даёт **`lslogins --failed`**; файлы `/var/log/lastlog*` и `/var/log/btmp*` больше ничем не читаются **[офиц., Debian 13 release notes, п. 5.1.9]**. ⚠ не подтверждено release notes Ubuntu, что в 26.04 всё точно так же; проверка: `command -v lastb`, `lslogins --failed`.
- Записи в базы `wtmpdb` и `lastlog2` вносят PAM-модули `pam_wtmpdb` (пакет `libpam-wtmpdb`; пример из man: `session required pam_wtmpdb.so`) и `pam_lastlog2` (пакет `libpam-lastlog2`; пример из man: `session optional pam_lastlog2.so silent_if=gdm,gdm-password`). В Debian 13 эти пакеты нужно ставить вручную («you will need to install the new packages after the upgrade»). ⚠ не подтверждено, включены ли они по умолчанию в серверной установке 26.04 — man-страницы и release notes этого не говорят. Проверка: `grep -rE 'pam_(lastlog2|wtmpdb)' /etc/pam.d/` и `dpkg -l wtmpdb libpam-wtmpdb lastlog2 libpam-lastlog2`. Если `last`/`lastlog2` показывают пустой список при заведомо бывших входах — модули не подключены.
- Неудачные входы на любой версии надёжнее смотреть в журнале: `journalctl -u ssh --since today | grep -i failed` или `grep 'Failed password' /var/log/auth.log`.

### 4.3. loginctl (systemd-logind)

```bash
loginctl list-sessions                   # все сессии: номер, UID, пользователь, TTY
loginctl list-users                      # вошедшие пользователи
loginctl session-status 42               # дерево процессов сессии и последние строки журнала
loginctl show-user ivanov                # свойства (State, Linger, Sessions …)
loginctl user-status ivanov              # процессы пользователя
sudo loginctl terminate-session 42       # завершить сессию
sudo loginctl terminate-user ivanov      # завершить все сессии пользователя
sudo loginctl kill-user ivanov --signal=SIGKILL
sudo loginctl enable-linger usr1cv8      # держать user-менеджер systemd без входа (для пользовательских служб)
sudo loginctl disable-linger usr1cv8
```

`enable-linger` нужен, только если какие-то процессы запускаются как пользовательские юниты (`systemctl --user`). Штатный сервер 1С и PostgreSQL — системные службы, linger им не требуется.

---

## 5. Системные пользователи сервисов: postgres, usr1cv8/grp1cv8, www-data

### 5.1. Сводная таблица

| Учётная запись | Основная группа | Кто создаёт | Домашний каталог | Оболочка | Что работает от её имени |
|---|---|---|---|---|---|
| `postgres` | `postgres` (+ `ssl-cert`) | пакет `postgresql-common` (Ubuntu/PGDG/сборка 1С), пакеты Postgres Pro | `/var/lib/postgresql` | `/bin/bash` | процессы `postgres`, утилиты `psql`, `pg_dump`, `pg_basebackup` |
| `usr1cv8` | `grp1cv8` | установщик сервера 1С | `/home/usr1cv8` | ⚠ зависит от версии установщика (проверить `getent passwd usr1cv8`) | `ragent`, `rmngr`, `rphost`, `ras`, сервер хранилища `crserver` |
| `www-data` | `www-data` | пакет `base-passwd` (статический UID/GID 33) | `/var/www` | `/usr/sbin/nologin` | Apache (`apache2`) и модуль веб-расширения 1С `wsap24.so`, nginx |

Проверка, что учётные записи на месте:

```bash
getent passwd postgres usr1cv8 www-data
id postgres ; id usr1cv8 ; id www-data
for u in postgres usr1cv8 www-data; do sudo passwd -S "$u"; done      # статус пароля каждой учётки
ps -o user:12,group:12,pid,cmd -C postgres,ragent,rmngr,rphost,apache2   # от кого реально работают процессы
systemctl show -p User -p Group 'srv1cv8-*' 'postgresql@*'               # User=/Group= загруженных юнитов
```

Ожидаемое: у всех трёх пароль заблокирован (`L` в `passwd -S`) — войти под ними по паролю нельзя, и задавать им пароль не нужно.

### 5.2. postgres

Как создаётся **[офиц., исходники postgresql-common]**:

- В пакетах для Ubuntu 22.04/24.04 (postgresql-common 238/257) — скриптом postinst:

  ```bash
  adduser --system --quiet --home /var/lib/postgresql --no-create-home \
      --shell /bin/bash --group --gecos "PostgreSQL administrator" postgres
  adduser --quiet postgres ssl-cert     # если есть группа ssl-cert
  ```

- В актуальной версии postgresql-common (ветка master, 2026) — декларативно, через systemd-sysusers и tmpfiles:

  ```
  # sysusers.d
  u postgres - "PostgreSQL administrator" /var/lib/postgresql /bin/bash
  m postgres ssl-cert
  # tmpfiles.d
  d /run/postgresql      2775 postgres postgres
  d /var/log/postgresql  2775 postgres postgres
  d /var/lib/postgresql  0755 postgres postgres
  z /etc/postgresql      0755 postgres postgres
  ```

  В старых версиях (22.04/24.04) каталог журналов создаётся как `root:postgres` с правами `1775`, сокет-каталог `/var/run/postgresql` — `postgres:postgres 2775`.

Особенности:

- Домашний каталог `postgres` — `/var/lib/postgresql`, а **не** `/home/postgres`. Туда же кладутся `~/.pgpass` (права `0600`), `~/.psqlrc`, `~/.ssh/` (для `rsync`/`pg_basebackup` между серверами), `~/.bash_history`.
- Оболочка `/bin/bash`, поэтому `sudo -iu postgres` и `su - postgres` работают без дополнительных ключей.
- Пароль ОС-учётки `postgres` не задаётся и не нужен. Не путать с **ролью БД** `postgres`: её пароль (нужен серверу 1С для подключения по TCP) задаётся в SQL: `ALTER ROLE postgres PASSWORD '...'` или `\password postgres` в `psql`.
- Локальный вход `sudo -u postgres psql` работает благодаря методу `peer` в `pg_hba.conf` (имя пользователя ОС = имя роли).
- Сервер PostgreSQL нельзя запускать от root; `initdb` от root отказывается работать **[офиц.]**.
- Postgres Pro: сервер также работает под пользователем `postgres` **[офиц.]**; каталог данных по умолчанию `/var/lib/pgpro/std-17/data` (путь сохраняется в `/etc/default/postgrespro-std-17`), программы в `/opt/pgpro/std-17/bin`, служба `postgrespro-std-17`. Кластер создаёт `sudo /opt/pgpro/std-17/bin/pg-setup initdb` (запускается от root, операции с базой выполняет от имени `postgres`), автозапуск и старт — `pg-setup service enable` / `pg-setup service start`, добавление программ в `PATH` — `pg-wrapper links update` **[офиц., postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux]**.
- Сборка Postgres Pro для 1С: каталог программ **`/opt/pgpro/1c-NN`** и `/opt/pgpro/1c-NN/bin/pg-setup` подтверждены файлом `meta.json` репозитория `repo.postgrespro.ru/1c/1c-17/` (пакеты `postgrespro-1c-17`, `-server`, `-client`, `-libs`, `-contrib`, `-devel`, `-docs`, `-docs-ru`, `-jit`, `-plperl`, `-plpython3`, `-pltcl`) **[офиц.]**. Каталог данных `/var/lib/pgpro/1c-NN/data` и имя службы `postgrespro-1c-NN` — по аналогии с редакцией `std` (та же схема `pg-setup`); каталог данных, служба и каталог программ сборки «для 1С» подтверждены официальным описанием метапакета — см. `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, разд. 5.1; ранее: не подтверждено прямым текстом первоисточника, проверьте `cat /etc/default/postgrespro-1c-NN`, `systemctl list-units 'postgrespro*'`, `sudo -u postgres psql -Atc 'show data_directory'`.

Вход и выполнение команд:

```bash
sudo -u postgres psql                         # одна команда от имени postgres
sudo -u postgres psql -c "select version();"
sudo -iu postgres                             # интерактивная оболочка входа (HOME=/var/lib/postgresql)
sudo su - postgres                            # то же через su
sudo -u postgres pg_dump -Fc -f /srv/backup/pg/base1.dump base1
sudo -u postgres -H bash -c 'cd ~ && ls -la'  # -H выставляет HOME целевого пользователя
```

Предупреждение `could not change directory to "/home/admin1c": Permission denied` при `sudo -u postgres ...` безвредно: текущий каталог (домашний каталог администратора с правами `0750`) недоступен пользователю `postgres`. Убирается переходом в общедоступный каталог (`cd /tmp`) или использованием `sudo -iu postgres`.

### 5.3. usr1cv8 и grp1cv8

Что известно:

- Служба сервера 1С запускается от `usr1cv8:grp1cv8`: в штатном юните `srv1cv8-<версия>@.service` заданы `User=usr1cv8`, `Group=grp1cv8`, каталог данных кластера — `SRV1CV8_DATA=/home/usr1cv8/.1cv8/1C/1cv8` **[практика: содержимое юнитов в публикациях Инфостарта; путь подтверждён методической статьёй ИТС]**. Статус после проверки: путь `/home/usr1cv8/.1cv8/1C/1cv8` и переменная `SRV1CV8_DATA` есть в статье ИТС **[офиц.]**; `User=usr1cv8`/`Group=grp1cv8` рецензент видел только в юнитах RAS из публикаций сообщества (almaz-sharipov.ru, rarus.ru), а текст именно штатного `srv1cv8-<версия>@.service` найти в открытом доступе не удалось — ⚠ сверяйте `systemctl cat` на своём сервере.
- Создание учётной записи:
  - старые deb-пакеты (`1c-enterprise83-server_8.3.NN-NNNN_amd64.deb` вместе с `-common`, `-ws` и `-nls`-вариантами; каталог `/opt/1C/v8.3/x86_64`, служба `srv1cv83`, настройки (`SRV1CV8_DATA`, `SRV1CV8_DEBUG`, `SRV1CV8_KEYTAB`) в `/etc/sysconfig/srv1cv83` по статье ИТС, в Debian/Ubuntu — `/etc/default/srv1cv83` **[практика]**) создавали `usr1cv8` и `grp1cv8` в postinst — ⚠ точные параметры (`useradd`) не подтверждены. Состав пакетов и пути подтверждены методической статьёй ИТС для 8.3.13.1644 **[офиц.]**. ⚠ не подтверждено: с какой именно версии каталог установки сменился на `/opt/1cv8/x86_64/<версия>` (по памяти рецензента — с 8.3.18, когда номер версии вошёл в имя пакета; единый установщик `.run` — с 8.3.20);
  - единый дистрибутив-установщик `setup-full-<версия>-x86_64.run` (8.3.20+): по публикациям сообщества пользователь создаётся **автоматически** при установке серверного компонента (формулировка «автоматически созданному пользователю usr1cv8» — sysadminchik.ru, платформа 8.3.22.2106; «в процессе установки создается группа grp1cv8, в которую должны входить все учетные записи…» — ответ на qna.habr.com, по стилю пересказывающий документацию 1С) **[практика, 2 независимых источника]**. **Уточнено 10.10.2026** (полный текст документации 8.3.27, «Клиент-серверный вариант», глава 3): при установке создаётся пользователь ОС `usr1cv8`, от имени которого работают серверные процессы. Ранее было не подтверждено официальной документацией: тело страниц ИТС («Руководство администратора», глава 2 «Установка системы „1С:Предприятие“», `its.1c.ru/db/v8327doc/content/101/hdoc`) без подписки не отдаётся (страница возвращает только оболочку с навигацией), англоязычная база `kb.1ci.com` перенесена на `support.1ci.com` и руководство администратора там закрыто авторизацией;
  - в контейнерных сборках сообщества (репозиторий `firstBitMarksistskaya/onec-docker`) установщик запускают как `./setup-full-${ONEC_VERSION}-x86_64.run --mode unattended --enable-components server,ws,…`, а в итоговом образе учётную запись создают вручную: `groupadd -r grp1cv8 --gid=…` и `useradd -r -g grp1cv8 --uid=… --home-dir=/home/usr1cv8 --shell=/bin/bash usr1cv8` **[практика]** — то есть ручное создание такими командами (см. ниже) является общепринятым и рабочим.
- Поэтому после установки всегда проверяйте фактическое состояние:

  ```bash
  getent passwd usr1cv8 && getent group grp1cv8
  ls -ld /home/usr1cv8 /home/usr1cv8/.1cv8 2>/dev/null
  systemctl cat 'srv1cv8-*@default.service' | grep -E '^(User|Group|Environment|ExecStart)='
  ```

- Если учётной записи или домашнего каталога нет (встречается на нестандартных дистрибутивах и при ручной распаковке) — создать вручную **[практика]**:

  ```bash
  sudo groupadd -r grp1cv8
  sudo useradd -r -g grp1cv8 -d /home/usr1cv8 -m -s /bin/bash -c "1C Enterprise 8 server" usr1cv8
  # если пользователь есть, а каталога нет:
  sudo install -d -o usr1cv8 -g grp1cv8 -m 0750 /home/usr1cv8
  ```

- Пароль `usr1cv8` не нужен. Имя и группа жёстко прописаны в юните; менять их можно только drop-in-файлом (`systemctl edit ...`), но делать это без необходимости не стоит: имя `usr1cv8` фигурирует в документации, в keytab для Kerberos (`usr1cv8.keytab`, владелец `usr1cv8:grp1cv8`, права `600` **[офиц., kb.1ci.com]**) и в методиках. Уточнение по keytab: статья 1Ci написана для 8.1/8.2 и приводит команды `chown usr1cv81:grp1cv81 usr1cv81.keytab` и `chmod 600 usr1cv81.keytab` (для 8.2 — заменить на `usr1cv82`); для 8.3 те же команды с `usr1cv8:grp1cv8` приводит статья на Хабре (каталог по умолчанию там `/opt/1C/v8.3/x86_64`, переменная `SRV1CV8_KEYTAB`). Файл можно хранить в любом каталоге, указав путь в `SRV1CV8_KEYTAB`.
- В более старых поколениях платформы пользователь назывался `usr1cv82`/`grp1cv82` (8.2) и `usr1cv81`/`grp1cv81` (8.1) — встречается в старых инструкциях **[офиц., статья 1Ci]**.
- Юнит RAS (`ras cluster --port=1545` или `ras cluster --daemon -p 1545 127.0.0.1:1540`) в публикациях сообщества также запускается с `User=usr1cv8`, `Group=grp1cv8` **[практика: almaz-sharipov.ru, rarus.ru]**; сервер хранилища конфигураций `crserver` — от того же пользователя, с каталогом данных, принадлежащим `usr1cv8:grp1cv8` (в статье «1С-Рарус» — `sudo chown usr1cv8:grp1cv8 /var/opt/1C/crserver`).
- Шаблон юнита лежит в каталоге версии платформы. Подключение по публикациям сообщества (номер версии свой) **[практика: mclouds.ru для 8.3.26.1498 — через `systemctl link`; sysadminchik.ru для 8.3.22.2106 — копированием файла из `/opt/1cv8/x86_64/<версия>/` в `/lib/systemd/system/`; по almaz-sharipov.ru, начиная с 8.3.23 юнит может регистрироваться самим установщиком]**:

  ```bash
  sudo systemctl link /opt/1cv8/x86_64/8.3.26.1498/srv1cv8-8.3.26.1498@.service
  sudo systemctl enable --now srv1cv8-8.3.26.1498@default.service
  ```

- Платформа 8.5.x: уточнено 10.10.2026: в документации 8.5.1 главы об установке и запуске в этой части по сравнению с 8.3.27 не изменились; ранее было не подтверждено, что имена `usr1cv8`/`grp1cv8` и схема каталогов `/opt/1cv8/x86_64/<версия>` сохранены без изменений: документация 8.5.1 и 8.5.4 на ИТС существует, но без подписки не читается, а публикаций сообщества с выводом `systemctl cat` для 8.5 рецензент не нашёл. После установки проверьте: `ls /opt/1cv8/x86_64/`, `systemctl cat 'srv1cv8-*@default.service' | grep -E '^(User|Group|Environment|ExecStart)='`, `getent passwd usr1cv8`.

Вход и выполнение команд от `usr1cv8`:

```bash
sudo -u usr1cv8 -s                            # оболочка от имени usr1cv8 (в текущем каталоге)
sudo -iu usr1cv8                              # оболочка входа; сработает, если оболочка учётки не nologin
sudo su -s /bin/bash - usr1cv8                # то же при любой оболочке учётки
sudo -u usr1cv8 test -w /srv/1c/exchange && echo "запись есть" || echo "записи НЕТ"
sudo -u usr1cv8 ls -la /home/usr1cv8/.1cv8/1C/1cv8/
sudo -u usr1cv8 /opt/1cv8/x86_64/8.3.27.1688/rac cluster list   # пример: утилита rac от имени сервера
```

### 5.4. www-data

- Статическая учётная запись из `base-passwd`: `www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin`. Существует на любой Ubuntu ещё до установки веб-сервера.
- Apache в Ubuntu запускается от неё: `/etc/apache2/envvars` → `APACHE_RUN_USER=www-data`, `APACHE_RUN_GROUP=www-data`.
- При публикации базы 1С (`webinst`, модуль `wsap24.so`) код веб-расширения исполняется внутри процессов Apache, то есть от `www-data`. Ему нужны: чтение каталога публикации с `default.vrd` (`/var/www/<имя>/`), чтение каталога платформы `/opt/1cv8/...`, а для файловых баз — ещё и запись в каталог базы. В клиент-серверном варианте `www-data` ходит к кластеру 1С по сети и прав на каталоги кластера ему не нужно.
- Для записи отладочного/технологического журнала веб-расширения методическая статья ИТС включает `www-data` в общую группу журналов (`usermod -a -G grp1clogs www-data`) **[офиц.]** — см. раздел 7.3.
- В штатном юните `apache2.service` включён `PrivateTmp=true`: процессы Apache видят собственный изолированный `/tmp`, а не общий. Файл, положенный администратором в `/tmp`, веб-расширению не виден.

Команды от имени `www-data` (оболочка `nologin`, поэтому `-i` не подходит):

```bash
sudo -u www-data bash                         # sudo запускает указанную команду напрямую, оболочка учётки не важна
sudo -u www-data test -r /var/www/base1/default.vrd && echo OK
sudo su -s /bin/bash - www-data               # через su — с явной оболочкой
sudo -iu www-data                             # НЕ сработает: "This account is currently not available."
```

---

## 6. Права доступа: chmod, chown, chgrp, umask, спецбиты

### 6.1. Модель прав

`ls -l` показывает тип и три тройки `rwx` — для владельца (u), группы (g), остальных (o):

```
drwxr-x---  2 usr1cv8 grp1cv8 4096 окт 10 09:00 exchange
-rw-r-----  1 postgres postgres 198 окт 10 09:00 server.key
```

| Бит | Для файла | Для каталога |
|---|---|---|
| `r` (4) | читать содержимое | получить список имён (`ls`) |
| `w` (2) | изменять содержимое | создавать, удалять и переименовывать объекты **внутри** каталога |
| `x` (1) | исполнять | входить в каталог и обращаться к объектам по имени (проход) |

Правила, о которых чаще всего забывают:

- Проверяется **первая подошедшая** категория: если вы владелец — действует только тройка владельца, даже если у группы прав больше.
- Удаление файла определяется правом `w` на **каталог**, а не на файл.
- Чтобы открыть `/a/b/c/file`, нужен `x` на `/`, `/a`, `/a/b`, `/a/b/c` и `r` на сам файл.
- root (точнее, обладатель `CAP_DAC_OVERRIDE`) обходит проверки прав, но не обходит атрибут `immutable`, монтирование `ro` и ограничения AppArmor/systemd.

### 6.2. chmod

Восьмеричная запись — сумма 4+2+1 по каждой тройке; необязательная первая цифра — спецбиты (4 SUID, 2 SGID, 1 sticky):

| Режим | Значение | Где применяется |
|---|---|---|
| `600` | `rw-------` | приватные ключи, `.pgpass`, keytab, `authorized_keys` |
| `640` | `rw-r-----` | конфиги с паролями, читаемые группой службы |
| `644` | `rw-r--r--` | обычные файлы, `logcfg.xml` |
| `700` | `rwx------` | `~/.ssh`, каталог данных PostgreSQL |
| `750` | `rwxr-x---` | домашние каталоги в Ubuntu, каталоги служб |
| `755` | `rwxr-xr-x` | программы, общедоступные каталоги |
| `770` / `2770` | `rwxrwx---` / то же + SGID | общий рабочий каталог группы |
| `1777` | `rwxrwxrwt` | `/tmp`, `/var/tmp` |

Символьная запись: `[ugoa][+-=][rwxXst]`, несколько выражений через запятую.

```bash
chmod 640 file.conf
chmod u=rw,g=r,o= file.conf            # то же символьно
chmod g+w,o-rwx dir                    # добавить запись группе, убрать всё у остальных
chmod a+x script.sh                    # сделать исполняемым для всех
chmod -R u=rwX,g=rX,o= /srv/1c/exchange    # рекурсивно; X — «x только каталогам и уже исполняемым файлам»
chmod --reference=образец цель         # скопировать режим с другого объекта
chmod -c -R g+w /srv/1c/exchange       # -c печатает только реально изменённые объекты
```

Рекурсия без порчи файлов — раздельно для каталогов и файлов:

```bash
sudo find /srv/1c/exchange -type d -exec chmod 2770 {} +
sudo find /srv/1c/exchange -type f -exec chmod 660 {} +
```

Никогда не делайте `chmod -R 777` «чтобы заработало»: это снимает защиту с данных и ломает программы, которые проверяют права (sshd, PostgreSQL, sudo). Отдельно: `chmod -R` на `/`, `/etc`, `/var/lib/postgresql` приводит к неработоспособной системе.

Особенность GNU `chmod` для каталогов **[офиц., руководство coreutils]**: числовой режим из четырёх и менее цифр (`755`, `0755`) **не сбрасывает** уже установленные SUID/SGID на каталоге. Сбросить можно явно: `chmod g-s каталог`, `chmod =755 каталог` или пятизначным `chmod 00755 каталог`.

Ubuntu 26.04: `chmod`, `chown`, `chgrp`, `install`, `stat`, `id`, `mkdir` поставляются пакетом `rust-coreutils` (uutils 0.10.0). Набор ключей `chmod` по man-странице resolute тот же (`-c`, `-f`, `-v`, `-R`, `--reference`, `--preserve-root`, `-H`/`-L`/`-P`, `-h`), но описанное выше правило про SUID/SGID каталогов в man-странице uutils **не упоминается** — ⚠ не подтверждено, что поведение совпадает с GNU. Поэтому в скриптах для 26.04 не полагайтесь на «молчаливое сохранение» SGID: всегда задавайте его явно (`chmod 2770 каталог` или `chmod g+s каталог`) и проверяйте результат `stat -c '%A %a' каталог`. Если нужна гарантированно GNU-семантика — вызывайте GNU-версии с префиксом `gnu` (release notes приводят пример `gnuls`; имена `gnuchmod`, `gnuchown`, `gnuinstall` образованы по тому же правилу — ⚠ проверьте `ls /usr/bin/gnu*`) либо переключите систему целиком: `sudo apt install coreutils-from-gnu coreutils-from-uutils- --allow-remove-essential` **[офиц., release notes 26.04]**.

### 6.3. chown и chgrp

```bash
sudo chown usr1cv8 file                    # сменить владельца
sudo chown usr1cv8:grp1cv8 file            # владельца и группу
sudo chown :grp1cv8 file                   # только группу (то же: chgrp grp1cv8 file)
sudo chown -R postgres:postgres /srv/pgdata
sudo chown -h user:group symlink           # сменить владельца самой ссылки, а не цели
sudo chown --from=root:root -R usr1cv8:grp1cv8 /srv/1c   # менять только то, что сейчас принадлежит root:root
sudo chown --reference=/home/usr1cv8 /srv/1c/cluster
sudo chgrp -R exch1c /srv/1c/exchange
```

- Менять владельца может только root. Владелец файла может сменить группу файла на любую из **своих** групп.
- При `chown` обычного файла ядро сбрасывает биты SUID/SGID.
- Создать каталог сразу с нужными владельцем и правами: `sudo install -d -o usr1cv8 -g grp1cv8 -m 0750 /srv/1c/cluster`.
- Быстро посмотреть: `stat -c '%A %a %U:%G %n' /путь`.

### 6.4. umask

`umask` — маска, **вычитаемая** из прав по умолчанию (666 для файлов, 777 для каталогов) при создании объекта.

| umask | Новые файлы | Новые каталоги |
|---|---|---|
| `022` | 644 | 755 |
| `002` | 664 | 775 |
| `027` | 640 | 750 |
| `077` | 600 | 700 |

```bash
umask                    # текущая маска (например 0002)
umask -S                 # в символьном виде: u=rwx,g=rwx,o=rx
umask 027                # сменить для текущей оболочки и её потомков
sudo -u postgres sh -c 'umask 077; pg_dump -Fc -f /srv/backup/pg/b.dump base1'   # маска только на одну команду
```

Откуда берётся:

- Интерактивные сессии: `pam_umask` читает `UMASK` из `/etc/login.defs` (в Ubuntu `022`). При `USERGROUPS_ENAB yes` для обычного пользователя, у которого имя совпадает с именем основной группы, групповые биты приравниваются к битам владельца, то есть фактически получается **`002`** **[офиц., man pam_umask]**. У root — `022`.
- Постоянно для одного пользователя: строка `umask 027` в `~/.profile` (или `~/.bashrc`).
- **Службы systemd**: маска берётся не из `login.defs`, а из директивы `UMask=` юнита; по умолчанию `0022` **[офиц., systemd.exec]**. Поэтому файлы, создаваемые сервером 1С (`rphost`), имеют права `644`, каталоги — `755`, владелец `usr1cv8:grp1cv8`. Изменить:

  ```bash
  sudo systemctl edit srv1cv8-8.3.27.1688@default.service
  # в открывшемся файле:
  [Service]
  UMask=0007
  # затем
  sudo systemctl restart srv1cv8-8.3.27.1688@default.service
  ```

- PostgreSQL внутри каталога данных сам создаёт файлы с `0600` (или `0640` при групповом доступе) независимо от umask.
- Если на каталоге задан ACL по умолчанию, umask при создании объектов в нём **не применяется** (раздел 8).

### 6.5. SUID, SGID, sticky

| Бит | Число | В `ls -l` | Действие |
|---|---|---|---|
| SUID | 4000 | `s` на месте `x` владельца (`-rwsr-xr-x`) | программа исполняется с правами владельца файла (пример: `/usr/bin/passwd`, `/usr/bin/sudo`) |
| SGID на файле | 2000 | `s` на месте `x` группы | программа исполняется с правами группы файла |
| SGID на каталоге | 2000 | `drwxrws---` | новые файлы получают **группу каталога**, новые подкаталоги наследуют SGID |
| sticky на каталоге | 1000 | `t` на месте `x` остальных (`drwxrwxrwt`) | удалять и переименовывать объект может только его владелец, владелец каталога или root |

```bash
sudo chmod g+s /srv/1c/exchange        # SGID на каталог (или chmod 2770)
sudo chmod +t /srv/shared              # sticky (или chmod 1777)
sudo chmod u+s /usr/local/bin/tool     # SUID — использовать крайне осторожно
sudo find / -xdev -type f -perm -4000 -ls 2>/dev/null   # аудит всех SUID-файлов
sudo find / -xdev -type f -perm -2000 -ls 2>/dev/null   # аудит SGID-файлов
```

Заглавные `S`/`T` в выводе `ls` означают, что спецбит установлен, а соответствующего `x` нет (обычно ошибка настройки). На разделах, смонтированных с `nosuid`, SUID/SGID игнорируются. Для скриптов (bash, python) SUID в Linux не действует.

---

## 7. Типовые права для PostgreSQL и 1С

### 7.1. PostgreSQL

| Объект | Владелец:группа | Права | Комментарий |
|---|---|---|---|
| Каталог данных `/var/lib/postgresql/NN/main` (Postgres Pro: `/var/lib/pgpro/std-NN/data`) | `postgres:postgres` | `0700` | **[офиц.]** `initdb` отзывает доступ у всех, кроме владельца |
| То же при `initdb -g` / `--allow-group-access` (PostgreSQL 11+) | `postgres:postgres` | `0750`, файлы `0640` | **[офиц.]** группа получает только чтение — для бэкапа непривилегированным пользователем |
| Файлы внутри каталога данных | `postgres:postgres` | `0600` (`0640`) | создаёт сам сервер |
| `/var/lib/postgresql` (домашний каталог) | `postgres:postgres` | `0755` | tmpfiles/postinst |
| `/etc/postgresql/NN/main/` | `postgres:postgres` | `0755`; `pg_hba.conf`, `pg_ident.conf` — `0640`; `postgresql.conf` — `0644` | **[офиц., исходники `pg_createcluster`]**: `move_conffile … postgresql.conf … '644'`, `pg_hba.conf … '640'`, `pg_ident.conf … '640'`; владелец и группа — владелец кластера. Если после правки от root способом, пересоздающим файл (`sudo sed -i`, `sudo cp новый pg_hba.conf`), файл стал `root:root` — сервер не сможет его прочитать при `reload`/старте; вернуть: `sudo chown postgres:postgres` и `sudo chmod 640` |
| `/var/log/postgresql` | `root:postgres 1775` (22.04/24.04) или `postgres:postgres 2775` (новые версии postgresql-common) | | **[офиц., исходники пакета]**; `pg_createcluster` при отсутствии каталога создаёт его как `root:<группа postgres>` с режимом `01775` |
| `/var/log/postgresql/postgresql-NN-main.log` | `postgres:adm` | `0640` | **[офиц., исходники `pg_createcluster`]**: `chmod 0640`, группа `adm`, если UID владельца кластера меньше 1000 (иначе — группа владельца). Поэтому журнал читают члены группы `adm` без sudo |
| `/run/postgresql` (сокет `.s.PGSQL.5432`) | `postgres:postgres` | `2775` | **[офиц.]** |
| `~postgres/.pgpass` | `postgres:postgres` | `0600` | иначе `psql`/`pg_dump` игнорируют файл с предупреждением |
| Ключ TLS `server.key` | `postgres` | `0600` (или `root:<группа>` `0640`) | иначе сервер не стартует |

Сервер проверяет каталог данных при старте. Типовые сообщения в журнале:

```
FATAL:  data directory "/var/lib/postgresql/16/main" has invalid permissions
DETAIL:  Permissions should be u=rwx (0700) or u=rwx,g=rx (0750).

FATAL:  data directory "/var/lib/postgresql/16/main" has wrong ownership
HINT:  The server must be started by the user that owns the data directory.
```

Исправление (кластер остановлен):

```bash
sudo systemctl stop postgresql@16-main
sudo chown -R postgres:postgres /var/lib/postgresql/16/main
sudo chmod 700 /var/lib/postgresql/16/main
sudo systemctl start postgresql@16-main
```

Перевод существующего кластера на групповой доступ **[офиц.]**: остановить сервер и выставить `0750` на **все** каталоги и `0640` на **все** файлы каталога данных, затем запустить:

```bash
sudo systemctl stop postgresql@16-main
sudo find /var/lib/postgresql/16/main -type d -exec chmod 750 {} +
sudo find /var/lib/postgresql/16/main -type f -exec chmod 640 {} +
sudo systemctl start postgresql@16-main
```

Каталог данных на отдельном томе **[офиц.]**: не используйте точку монтирования как каталог данных — создайте внутри неё подкаталог, принадлежащий `postgres`:

```bash
sudo install -d -o postgres -g postgres -m 0700 /mnt/pgdata/16/main
sudo pg_createcluster 16 main -d /mnt/pgdata/16/main     # или перенос существующего кластера
```

Рекомендуется, чтобы `postgres` владел и родительским каталогом каталога данных **[офиц.]**.

### 7.2. Сервер 1С

| Объект | Владелец:группа | Права | Комментарий |
|---|---|---|---|
| `/opt/1cv8/x86_64/<версия>/` (программы платформы, юнит `srv1cv8-<версия>@.service`) | `root:root` | каталоги `755`, файлы `644`/`755` | серверу нужно только чтение и исполнение. В части руководств встречается `chown -R usr1cv8:grp1cv8 /opt/1cv8` **[практика: sysadminchik.ru для 8.3.22]** — это не обязательно и снижает защищённость (служба сможет изменить собственные исполняемые файлы). ⚠ не подтверждено первоисточником, что сразу после установки владелец именно `root:root` и что серверу не требуется запись в каталог версии (например, для `usr1cv8.keytab` или `conf`): официального описания прав нет. Проверьте `ls -ld /opt/1cv8 /opt/1cv8/x86_64/*`; если техжурнал/keytab не подхватываются при владельце `root`, выдавайте права точечно на конкретный файл, а не рекурсивно на всё дерево |
| `/opt/1cv8/x86_64/<версия>/conf/` (`logcfg.xml`, `conf.cfg` и т.п.) | `root:root` | `755`, файлы `644` | файлы должны быть **читаемы** для `usr1cv8`. Расположение для 8.3.20+ подтверждено только практикой сообщества: в `onec-docker` каталог создают вручную (`mkdir -p /opt/1cv8/current/conf`, где `current` — ссылка на каталог версии) и кладут `logcfg.xml` туда **и** в `/home/usr1cv8/.1cv8/1C/1cv8/conf` **[практика]**. Официально подтверждён только старый путь `/opt/1C/v8.3/x86_64/conf` (ИТС, 8.3.13; там же: `mkdir -p /opt/1C/v8.3/x86_64/conf` — каталог тоже создаётся вручную). **Уточнено 10.10.2026** (приложения 1 и 3 документации 8.3.27): `/opt/1cv8/conf` — официальный каталог в порядке поиска конфигурационных файлов и значение `ConfLocation` по умолчанию. Ранее было не подтверждено: встречающийся в инструкциях общий для всех версий каталог `/opt/1cv8/conf` и содержимое `conf.cfg` (параметр `ConfLocation`) — нужна страница ИТС «Приложение 3. Описание и расположение служебных файлов». Каталог привязан к версии: **после обновления платформы `logcfg.xml` нужно перенести в `conf` новой версии** |
| `/home/usr1cv8` | `usr1cv8:grp1cv8` | `750` | домашний каталог |
| `/home/usr1cv8/.1cv8/1C/1cv8/` (данные кластера: `reg_1541/`, `1cv8wsrv.lst`, журналы регистрации, сеансовые данные) | `usr1cv8:grp1cv8` | `700`–`750`, создаёт сам сервер | путь по умолчанию (методическая статья ИТС и штатный юнит); меняется переменной `SRV1CV8_DATA`. Точные режимы подкаталогов — ⚠ проверьте `ls -la` на своём сервере |
| Свой каталог данных кластера (например `/srv/1c/cluster`) | `usr1cv8:grp1cv8` | `750` | ИТС: `chown -R usr1cv8 /cluster_data` **[офиц.]** |
| `usr1cv8.keytab` (Kerberos) | `usr1cv8:grp1cv8` | `600` | **[офиц.]** статья 1Ci (для 8.1/8.2: `chown usr1cv81:grp1cv81 usr1cv81.keytab`, `chmod 600 usr1cv81.keytab`); для 8.3 — те же команды с `usr1cv8:grp1cv8` **[практика, Хабр]**. Расположение задаётся `SRV1CV8_KEYTAB` |
| Каталог технологического журнала (например `/var/log/1c`) | `usr1cv8:grp1clogs` | `g+rw` (на практике `2770`) | **[офиц., ИТС]** см. 7.3 |
| Каталог программных лицензий `/var/1C/licenses` | `root:grp1cv8` | `775` (владелец `rwx`, группа `rwx`, остальные `r-x`) | **[практика]**: ответ на qna.habr.com, пересказывающий документацию 1С: «Владелец каталога: root… Группа владельца: grp1cv8. Права: чтение и запись (rwx)… для остальных пользователей: только чтение (r-x)»; «у пользователей группы grp1cv8 есть доступ на запись». Путь `/var/1C/licenses` для серверных лицензий подтверждает almaz-sharipov.ru. Подтверждено документацией 8.3.27 (глава 10, сверено 10.10.2026): каталог `/var/1C/licenses` создаётся при установке, владелец — `root` (rwx), группа — `grp1cv8` (rwx), остальные — r-x; учётные записи, работающие с лицензиями, должны входить в `grp1cv8`. Прежняя оговорка: не подтверждено текстом ИТС. Следствие: активировать лицензию нужно от учётки, входящей в `grp1cv8`, либо после активации проверить, что файл `*.lic` читается `usr1cv8` (`sudo -u usr1cv8 ls -l /var/1C/licenses`). Файл лицензии, попавший в профиль пользователя (`~/.1cv8/1C/1cv8/conf/*.lic`), **переносят** (`mv`), а не копируют — копия блокирует лицензию **[практика]** |
| Каталог обмена/выгрузок (например `/srv/1c/exchange`) | `usr1cv8:exch1c` | `2770` + ACL по умолчанию | раздел 15.1 |
| Каталог публикации `/var/www/<база>/default.vrd` | `root:www-data` или `www-data:www-data` | `750`/`640` | должен читаться `www-data` |

Перенос каталога данных кластера 1С на отдельный диск:

```bash
sudo systemctl stop srv1cv8-8.3.27.1688@default.service
sudo install -d -o usr1cv8 -g grp1cv8 -m 0750 /srv/1c/cluster
sudo rsync -aHAX /home/usr1cv8/.1cv8/1C/1cv8/ /srv/1c/cluster/
sudo systemctl edit srv1cv8-8.3.27.1688@default.service
#   [Service]
#   Environment=SRV1CV8_DATA=/srv/1c/cluster
sudo systemctl start srv1cv8-8.3.27.1688@default.service
```

(Номер версии в имени юнита замените на установленный: `systemctl list-units 'srv1cv8*'`.)

Перед переносом убедитесь, что drop-in действительно подействует: в штатном юните должна быть строка `Environment=SRV1CV8_DATA=…`, а `ExecStart` должен ссылаться на `${SRV1CV8_DATA}` (ключ `-d` у `ragent`) — `systemctl cat 'srv1cv8-*@default.service' | grep -E 'SRV1CV8_DATA|ExecStart'`. Содержимое штатного юнита рецензент первоисточником подтвердить не смог (⚠; в публикациях сообщества в юните встречаются `Environment=SRV1CV8_DEBUG=…`, `Environment=SRV1CV8_KEYTAB=…`, а `SRV1CV8_DATA=/home/usr1cv8/.1cv8/…` — в конфигурации старой службы `/etc/default/srv1cv83-*`). После запуска проверьте фактический каталог: `ps -o cmd -C ragent | tr ' ' '\n' | grep -A1 -x -e '-d'` и наличие свежих файлов в `/srv/1c/cluster/reg_1541/`. Пакет `rsync` в минимальной установке может отсутствовать (`sudo apt install rsync`); ключи `-aHAX` сохраняют владельцев, жёсткие ссылки, ACL и расширенные атрибуты.

### 7.3. Технологический журнал 1С: общая группа

Рецепт из методической статьи ИТС «Установка Платформы 1С:Предприятие в ОС Linux» **[офиц.]** (статья написана для 8.3.13.1644 с каталогом `/opt/1C/v8.3/x86_64/conf`, который создаётся вручную: `mkdir -p /opt/1C/v8.3/x86_64/conf`; для 8.3.20+ по практике сообщества `logcfg.xml` кладут в `/opt/1cv8/x86_64/<версия>/conf/` — каталог также создаётся вручную, см. примечание в таблице 7.2; команды статьи сверены рецензентом дословно):

```bash
sudo mkdir -p /var/log/1c/logs
sudo groupadd grp1clogs
sudo usermod -a -G grp1clogs www-data
sudo usermod -a -G grp1clogs usr1cv8
sudo chown -R usr1cv8:grp1clogs /var/log/1c
sudo chmod g+rw /var/log/1c
```

Дополнение **[практика]**: чтобы новые файлы журнала наследовали группу и оставались доступными группе, поставьте SGID и ACL по умолчанию, после чего перезапустите службы (иначе новое членство в группе не подействует):

```bash
sudo chmod 2770 /var/log/1c /var/log/1c/logs
sudo setfacl -R -d -m g:grp1clogs:rwX /var/log/1c
sudo systemctl restart srv1cv8-8.3.27.1688@default.service apache2
```

---

## 8. ACL: getfacl и setfacl

ACL (POSIX Access Control Lists) позволяют дать права **конкретному** пользователю или группе сверх классической тройки владелец/группа/остальные. ext4 и XFS поддерживают ACL по умолчанию; утилиты находятся в пакете `acl` (если команд нет — `sudo apt install acl`). Признак наличия ACL — знак `+` после прав в `ls -l`: `drwxrws---+`.

### 8.1. Просмотр

```bash
getfacl /srv/1c/exchange
```

```
# file: srv/1c/exchange
# owner: usr1cv8
# group: exch1c
# flags: -s-
user::rwx
user:postgres:r-x
group::rwx
group:backupops:r-x          #effective:r--
mask::rw-
other::---
default:user::rwx
default:group::rwx
default:group:exch1c:rwx
default:mask::rwx
default:other::---
```

- `user::`, `group::`, `other::` — обычные права владельца, группы-владельца и остальных.
- `user:ИМЯ:`, `group:ИМЯ:` — именованные записи.
- `mask::` — **верхняя граница** для всех именованных записей и для группы-владельца. Реально действующее право = запись И маска; если они различаются, `getfacl` дописывает `#effective:`.
- `default:` — ACL по умолчанию (только у каталогов): шаблон, который получают новые объекты внутри.
- `# flags: -s-` — спецбиты (здесь SGID).

Полезные ключи `getfacl`: `-R` (рекурсивно), `-d` (только default), `-a` (только access), `-e` (всегда показывать effective), `-p` (не убирать ведущий `/`), `-t` (табличный вид).

### 8.2. Изменение

Формат записи: `[d:]u:ИМЯ:права`, `[d:]g:ИМЯ:права`, `[d:]m::права`, `[d:]o::права`. Права — `rwx`, `-`, цифрой или с `X` (исполнение только для каталогов и уже исполняемых файлов).

| Ключ `setfacl` | Действие |
|---|---|
| `-m записи` | добавить/изменить записи |
| `-x записи` | удалить записи (права не указываются: `-x u:ivanov`) |
| `-b` | удалить все расширенные записи (останутся обычные права) |
| `-k` | удалить ACL по умолчанию |
| `-d` | операция применяется к ACL по умолчанию (то же, что префикс `d:`) |
| `-R` | рекурсивно; `-L`/`-P` — следовать/не следовать символьным ссылкам |
| `-n` | не пересчитывать маску |
| `--set записи` | заменить ACL целиком |
| `--set-file=ФАЙЛ`, `-M ФАЙЛ` | взять записи из файла (`-` — stdin) |
| `--restore=ФАЙЛ` | восстановить из резервной копии `getfacl -R` |
| `--test` | показать результат, ничего не меняя |

```bash
sudo setfacl -m u:usr1cv8:rwx /srv/exchange                 # дать usr1cv8 полный доступ к каталогу
sudo setfacl -m u:postgres:r-x,g:backupops:r-x /srv/exchange   # несколько записей сразу
sudo setfacl -R -m u:usr1cv8:rwX /srv/exchange              # рекурсивно на всё существующее
sudo setfacl -R -d -m u:usr1cv8:rwX /srv/exchange           # и по умолчанию — на всё, что появится
sudo setfacl -x u:postgres /srv/exchange                    # убрать запись
sudo setfacl -b /srv/exchange                               # убрать все ACL
sudo setfacl -k /srv/exchange                               # убрать только default-ACL
sudo setfacl -m m::rwx /srv/exchange                        # явно задать маску
getfacl file1 | setfacl --set-file=- file2                  # скопировать ACL с файла на файл
```

Резервная копия и восстановление ACL дерева:

```bash
cd / && sudo getfacl -R srv/exchange > /root/exchange.acl
cd / && sudo setfacl --restore=/root/exchange.acl
```

### 8.3. Маска и её подводные камни

- При `setfacl -m` маска по умолчанию **пересчитывается** как объединение прав группы-владельца и всех именованных записей (отключается `-n`).
- Когда у объекта есть ACL, групповая тройка в `ls -l` показывает **маску**, а `chmod g=...` меняет именно маску. Команда `chmod 750 каталог` на каталоге с ACL урежет маску до `r-x`, и именованные записи с `rwx` перестанут давать запись (`#effective:r-x`). После массового `chmod` проверьте `getfacl` и при необходимости верните `setfacl -m m::rwx`.
- Новый файл в каталоге с default-ACL получает записи из шаблона, но маска урезается режимом, который запросила программа при создании (обычно `0666` для файла) — поэтому у файлов `x` в маске нет, и это нормально.
- Если у каталога есть default-ACL, `umask` процесса при создании объектов внутри **не применяется**.

### 8.4. Перенос и копирование

- `cp -a` и `cp --preserve=all` сохраняют ACL; обычный `cp` — нет (новый файл получит default-ACL каталога назначения).
- `mv` в пределах одной файловой системы сохраняет ACL файла и **не** применяет default-ACL нового каталога — частая причина «файл переложили, а 1С его не видит».
- `rsync -A` (или `-aHAX`), `tar --acls` — сохраняют ACL; без этих ключей — нет.
- На CIFS/SMB-, FAT/exFAT-, NTFS-ресурсах POSIX ACL, `chown` и `chmod` в обычном понимании не работают: права задаются опциями монтирования (`uid=`, `gid=`, `file_mode=`, `dir_mode=`).

---

## 9. Атрибуты файлов: lsattr и chattr

Атрибуты (флаги inode) — отдельный от прав и ACL механизм файловых систем ext4/XFS/btrfs. Утилиты из пакета `e2fsprogs` (установлен всегда).

```
chattr [-RVf] [-v версия] [-p проект] [+-=режим] файлы...
```

Операторы: `+` добавить, `-` снять, `=` оставить только перечисленные. Ключи: `-R` рекурсивно, `-V` подробно, `-f` подавлять большинство ошибок.

| Атрибут | Значение |
|---|---|
| `i` | immutable: файл нельзя изменить, удалить, переименовать, создать на него жёсткую ссылку, открыть на запись — **даже root** |
| `a` | append only: файл можно открыть на запись только в режиме дозаписи; удалить и перезаписать нельзя |
| `A` | не обновлять время доступа (atime) |
| `d` | пропускать при `dump` |
| `S` / `D` | синхронная запись файла / каталога |
| `c`, `C` | сжатие / отключить copy-on-write (актуально для btrfs) |
| `e` | файл использует экстенты (служебный, присутствует почти у всех файлов ext4, снять нельзя) |
| `j` | журналирование данных (ext3/ext4) |

Ставить и снимать `i` и `a` может только root (точнее, процесс с `CAP_LINUX_IMMUTABLE`) **[офиц., man chattr]**. Уже открытые на запись дескрипторы установка атрибута не затрагивает.

```bash
lsattr /etc/resolv.conf                 # показать атрибуты файла
lsattr -d /srv/backup                   # атрибуты самого каталога, а не содержимого
lsattr -R /srv/backup | grep -- '-i-'   # найти неизменяемые объекты
sudo chattr +i /etc/resolv.conf         # запретить любые изменения
sudo chattr -i /etc/resolv.conf         # снять запрет
sudo chattr +a /var/log/audit-1c.log    # только дозапись
sudo chattr -R +i /srv/backup/archive/2025   # «заморозить» архивный каталог
```

Когда применять и чего ждать:

- `+i` — защита от случайного изменения критичного файла (например, от перезаписи `resolv.conf`), «заморозка» старых архивов бэкапа.
- `+a` — журнал, который нельзя стереть. Учтите: `logrotate` такой файл повернуть не сможет.
- Симптом: `rm`, `mv`, `chmod`, `chown`, редактор от root выдают **«Operation not permitted»** (а не «Permission denied»). Диагностика — `lsattr`.
- `+i` на каталоге запрещает создавать и удалять объекты в нём.
- Обновление пакетов (`apt`, `dpkg`) падает с ошибкой, если нужно заменить неизменяемый файл.
- `tar`, `cp`, `rsync` атрибуты не переносят.

---

## 10. sudo и su

### 10.1. Как устроено в Ubuntu

- Учётная запись root существует, но пароль у неё не задан (в поле хэша стоит значение, не соответствующее ни одному паролю), поэтому войти под root по паролю нельзя **[офиц.]**.
- Первый пользователь, созданный установщиком, включён в группу `sudo`; члены этой группы могут выполнять любые команды от root, вводя **свой** пароль.
- Включить пароль root: `sudo passwd root`; выключить: `sudo passwd -l root` **[офиц.]**. Для сервера 1С/PostgreSQL включать его обычно незачем.
- Правила хранятся в `/etc/sudoers` (права `0440 root:root`) и в файлах каталога `/etc/sudoers.d/`.

Штатный `/etc/sudoers` в Ubuntu 22.04/24.04 (содержательные строки):

```
Defaults        env_reset
Defaults        mail_badpass
Defaults        secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
Defaults        use_pty

root    ALL=(ALL:ALL) ALL
%admin  ALL=(ALL) ALL
%sudo   ALL=(ALL:ALL) ALL

@includedir /etc/sudoers.d
```

Чем подтверждено содержимое (сам файл рецензент прочитать не смог — git Launchpad не открылся, поэтому сверка по журналу изменений пакета sudo 1.9.9-1ubuntu2 **[офиц., changelogs.ubuntu.com]**):

- `Defaults use_pty` — «add use_pty to default configuration, fixing CVE-2005-4890» (sudo 1.9.6-1~exp2, то есть есть и в 22.04, и в 24.04);
- `secure_path` задаётся в файле, а не при сборке («move secure_path from configure to default sudoers»), `/snap/bin` добавлен правкой Ubuntu («include /snap/bin in the secure_path»);
- строка `%admin` — правка Ubuntu «also grant admin group sudo access» (группа `admin` — наследие старых выпусков; в свежей установке её нет, действует `%sudo`);
- `@includedir` вместо `#includedir` — с sudo 1.9.1-2 (оба написания равнозначны; `#includedir` — **не** комментарий);
- сборка Ubuntu: «compile with --without-lecture --with-tty-tickets --enable-admin-flag» (отсюда `lecture` = never), пароль действует 15 минут, тайм-аут ввода пароля отключён («change TIMEOUT … to 15 mins, disable PASSWORD_TIMEOUT»);
- патч `keep_home_by_default` удалён в sudo 1.8.27-1ubuntu2 (Ubuntu 19.10): начиная с этой версии `sudo КОМАНДА` выставляет `HOME` целевого пользователя, как в остальных дистрибутивах. В инструкциях для Ubuntu 18.04 и старше поведение `HOME` описано иначе — не переносите их без проверки.

Точный текст на сервере: `sudo grep -vE '^\s*(#|$)' /etc/sudoers`. ⚠ не подтверждено: содержимое `/etc/sudoers` в Ubuntu 26.04 (с sudo-rs) — прочитать не удалось.

### 10.2. Команда sudo

| Команда | Что делает |
|---|---|
| `sudo КОМАНДА` | выполнить от root |
| `sudo -u ПОЛЬЗОВАТЕЛЬ КОМАНДА` | выполнить от другого пользователя |
| `sudo -g ГРУППА КОМАНДА` | выполнить с другой основной группой |
| `sudo -i` / `sudo -iu ПОЛЬЗОВАТЕЛЬ` | оболочка входа (окружение и домашний каталог целевого пользователя) |
| `sudo -s` / `sudo -u ПОЛЬЗОВАТЕЛЬ -s` | оболочка без смены каталога и с минимальной сменой окружения |
| `sudo -l` | показать, что разрешено текущему пользователю |
| `sudo -l -U ПОЛЬЗОВАТЕЛЬ` | то же для другого пользователя (нужны права root) |
| `sudo -v` | продлить кэш пароля, ничего не выполняя |
| `sudo -k` / `sudo -K` | сбросить кэш пароля для терминала / удалить все отметки времени |
| `sudo -n КОМАНДА` | неинтерактивно: если нужен пароль — сразу ошибка (для скриптов и cron) |
| `sudo -H КОМАНДА` | установить `HOME` целевого пользователя. В Ubuntu 22.04/24.04 это и так происходит из-за `env_reset` (ключ что-то меняет, только если `HOME` добавлен в `env_keep` или `env_reset` отключён); в sudo-rs `HOME` целевого пользователя выставляется всегда, ключ `-H` в man-странице sudo-rs 0.2.13 не описан, в исходниках апстрима принимается «для совместимости» и ничего не делает — ⚠ в скриптах для 26.04 лучше его не использовать |
| `sudo -E КОМАНДА` | сохранить окружение вызывающего (только sudo.ws и только если это разрешено правилом: тег `SETENV:` или опция `setenv`; для правила с командой `ALL` тег `SETENV` подразумевается; в sudo-rs не поддерживается: в исходниках апстрима флаг принимается с предупреждением «preserving the entire environment is not supported, '-E' is ignored», окружение **не** сохраняется) |
| `sudo -ll` (или `sudo -l -l`) | подробный список правил; работает и в sudo.ws, и в sudo-rs («use twice for longer format») |
| `sudo --preserve-env=VAR1,VAR2 КОМАНДА` | сохранить отдельные переменные |
| `sudoedit ФАЙЛ` / `sudo -e ФАЙЛ` | безопасно редактировать файл своим редактором |
| `sudo -b КОМАНДА` | выполнить в фоне |

```bash
sudo systemctl restart postgresql
sudo -u postgres psql -c "\l"
sudo -u usr1cv8 -s
sudo -l
echo 'vm.swappiness = 10' | sudo tee /etc/sysctl.d/90-swappiness.conf   # запись в файл root
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'                          # перенаправление внутри sudo
```

Перенаправление `>` выполняет **ваша** оболочка, а не sudo: `sudo echo x > /etc/file` завершится «Permission denied». Используйте `| sudo tee` или `sudo sh -c '...'`.

### 10.3. visudo и /etc/sudoers.d

Правила редактируются только через `visudo`: он блокирует файл и проверяет синтаксис перед сохранением (при ошибке предлагает `e` — вернуться к правке, `x` — выйти без сохранения, `Q` — сохранить с ошибкой, чего делать нельзя). Ошибка в sudoers лишает sudo всех пользователей.

```bash
sudo visudo                                   # основной файл
sudo visudo -f /etc/sudoers.d/90-admins-1c    # отдельный файл с локальными правилами (рекомендуется)
sudo visudo -c                                # проверить основной файл и все включаемые
sudo visudo -cf /etc/sudoers.d/90-admins-1c   # проверить один файл
sudo EDITOR=nano visudo                       # выбрать редактор (SUDO_EDITOR, VISUAL, EDITOR)
```

Правила каталога `/etc/sudoers.d` **[офиц., man sudoers]**:

- файлы читаются в лексикографическом порядке (`10-...` раньше `90-...`);
- файлы, имя которых **содержит точку** или оканчивается на `~`, **пропускаются** (`admins.conf`, `rules.bak` работать не будут);
- права файла — `0440`, владелец `root:root` (`visudo -f` выставляет сам);
- при конфликте действует **последнее** подошедшее правило, а не самое точное.

Если правку всё же испортили и sudo не работает: войти под root с консоли гипервизора/в recovery mode либо выполнить `pkexec visudo` (если установлен polkit).

### 10.4. Синтаксис правил

```
КТО   ГДЕ=(ОТ_КОГО[:ОТ_ГРУППЫ])   [ТЕГ:] КОМАНДЫ
```

- `КТО` — пользователь, `%группа`, `User_Alias`;
- `ГДЕ` — имя хоста или `ALL` (на одиночном сервере всегда `ALL`);
- `(ОТ_КОГО)` — от чьего имени разрешено запускать; `(ALL:ALL)` — от любого пользователя и группы;
- `ТЕГ` — `NOPASSWD:`, `PASSWD:`, `NOEXEC:`, `SETENV:`;
- `КОМАНДЫ` — **полные пути** через запятую, `ALL` или `Cmnd_Alias`.

```
# /etc/sudoers.d/90-admins-1c

# Полный администратор без запроса пароля (вход только по SSH-ключу)
admin1c ALL=(ALL:ALL) NOPASSWD: ALL

# Группа операторов 1С: управление службами без пароля, остальное запрещено.
# "systemctl status" сюда не включаем: он не требует root (выполняется без sudo),
# а под sudo открывает пейджер less, из которого можно выйти в оболочку root.
Cmnd_Alias SRV1C = /usr/bin/systemctl start srv1cv8-8.3.27.1688@default.service, \
                   /usr/bin/systemctl stop srv1cv8-8.3.27.1688@default.service, \
                   /usr/bin/systemctl restart srv1cv8-8.3.27.1688@default.service
%oper1c ALL=(root) NOPASSWD: SRV1C

# Оператору бэкапа разрешено запускать pg_dump и psql от имени postgres
backupop ALL=(postgres) NOPASSWD: /usr/bin/pg_dump, /usr/bin/pg_dumpall, /usr/bin/psql

# Разработчику — оболочка от имени usr1cv8, но не root
dev1c ALL=(usr1cv8) ALL
```

Проверка: `sudo -l -U backupop`, затем от имени пользователя `sudo -n -u postgres pg_dump --version`.

Псевдонимы: `User_Alias`, `Runas_Alias`, `Host_Alias`, `Cmnd_Alias` (имена — заглавными буквами).

### 10.5. Ограничение набора команд — правила безопасности

- Указывайте полные пути (`/usr/bin/systemctl`, а не `systemctl`) и по возможности полные аргументы.
- Шаблоны в аргументах опасны: в классическом sudo `*` совпадает и с пробелами, поэтому правило `/usr/bin/systemctl restart srv1cv8*` пропустит `systemctl restart srv1cv8-x ssh ...`. В sudo-rs (26.04) шаблон внутри аргументов — ошибка разбора; допустим только отдельный завершающий `*` («любые оставшиеся аргументы»). Самый надёжный вариант для обеих реализаций — перечислить команды полностью.

  Уточнение по источникам: man sudoers (24.04) — `*` «Matches any set of zero or more characters (including white space)»; README sudo-rs — «wildcards are only supported in argument positions for a command as the final argument»; `sudoers.5.md` sudo-rs — «Wildcards in command line arguments are not supported» **[офиц.]**. Документация sudo-rs не уточняет, отвергается ли такое правило при разборе или просто не срабатывает (⚠) — после переноса правил на 26.04 выполните `sudo visudo -c` и проверьте каждое правило командой `sudo -l -U ПОЛЬЗОВАТЕЛЬ`. С sudo 1.9.10 (22.04 — 1.9.9, поэтому только 24.04 и `sudo.ws` в 26.04) в sudo.ws можно задавать аргументы регулярным выражением (`^…$`), что безопаснее `*`; в sudo-rs регулярные выражения не документированы.
- `""` вместо аргументов — команду можно запускать только **без** аргументов: `/usr/bin/apt ""`.
- «Запретительные» правила вида `user ALL=(ALL) ALL, !/bin/su` не работают как защита: команду можно скопировать под другим именем или запустить через оболочку.
- Не давайте через sudo программы, из которых можно выйти в оболочку (редакторы `vi`/`nano`, `less`, `find`, `tar`, `awk`, `python`, `env`, а также `systemctl` без ограничения аргументов — он вызывает пейджер). Для редактирования файлов — `sudoedit`, для остального — тег `NOEXEC:` или обёртка-скрипт, принадлежащий root и недоступный на запись другим.
- Скрипт, разрешённый в sudoers, и все каталоги на пути к нему должны быть недоступны на запись тому, кому он разрешён.
- `NOPASSWD: ALL` оправдан только для учётной записи, вход в которую защищён ключом; не выдавайте его сервисным учёткам (`usr1cv8`, `www-data`, `postgres`).

### 10.6. Тайм-аут, попытки, окружение (Defaults)

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `timestamp_timeout` | `15` (минут) | сколько действует введённый пароль; `0` — спрашивать всегда; отрицательное значение (sudo.ws) — до перезагрузки |
| `timestamp_type` | `tty` | кэш привязан к терминалу; другие значения: `ppid`, `global` (только sudo.ws) |
| `passwd_tries` | `3` | число попыток ввода пароля |
| `passwd_timeout` | `0` (нет) | тайм-аут ожидания ввода пароля, минут |
| `secure_path` | задан в `/etc/sudoers` | `PATH` для запускаемых команд |
| `env_reset` | включён | команды получают минимальное окружение |
| `env_keep` | список | какие переменные сохранять: `Defaults env_keep += "http_proxy https_proxy"` |
| `use_pty` | включён | запуск команды в псевдотерминале. Встроенное умолчание: «on by default for sudo 1.9.14 and above» (24.04), в sudo 1.9.9 (22.04) — off, но там опцию включает строка `Defaults use_pty` штатного `/etc/sudoers`; в sudo-rs — on **[офиц., man sudoers jammy/noble, sudoers-rs]** |
| `editor` | `/usr/bin/editor` | редактор для `visudo`/`sudoedit` (sudo-rs: список `/usr/bin/editor:/usr/bin/nano:/usr/bin/vi`) |
| `lecture` | `never` | показывать ли «лекцию» при первом запуске. Подтверждено man sudoers для сборки Ubuntu 24.04 (1.9.15p5): «The default value is never» **[офиц.]**; в sudo-rs параметр не документирован |
| `umask` | `0022` | маска для запускаемых команд |
| `pwfeedback` | sudo.ws: выключен; sudo-rs: включён | печатать `*` при вводе пароля |
| `syslog` | `authpriv` | facility для syslog; приоритеты `syslog_goodpri` = `notice`, `syslog_badpri` = `alert` (sudo.ws) |
| `loglinelen` | `80` | перенос строк в файле журнала (`0` — не переносить; только sudo.ws с `logfile`) |

Значения `timestamp_timeout` = 15, `passwd_tries` = 3, `passwd_timeout` = 0, `timestamp_type` = `tty`, `editor`, `umask`, `iolog_dir` = `/var/log/sudo-io`, `secure_path` («not set by default» — задаётся только в `/etc/sudoers`) сверены по man sudoers сборок Ubuntu 22.04 (1.9.9) и 24.04 (1.9.15p5) и по `sudoers.5.md` sudo-rs **[офиц.]**. Обратите внимание: апстримные умолчания sudo (по памяти рецензента — `timestamp_timeout` и `passwd_timeout` по 5 минут, ⚠ не сверено) отличаются от сборки Debian/Ubuntu — не переносите цифры из руководств для других дистрибутивов без проверки `sudo -V` от root (sudo.ws печатает все действующие значения).

Для sudo-rs (26.04): области действия `Defaults:пользователь`, `Defaults@хост`, `Defaults>от_кого`, `Defaults!команда` в грамматике `sudoers.5.md` описаны; `lecture`, `mail_badpass`, `logfile` и ряд других параметров sudo.ws не документированы, что происходит со строкой с неизвестным параметром — документация не говорит (⚠). После переноса старого `sudoers` на 26.04 обязательно выполните `sudo visudo -c` и прочитайте предупреждения.

```
# /etc/sudoers.d/10-defaults
Defaults                timestamp_timeout=5
Defaults:admin1c        timestamp_timeout=30
Defaults                passwd_tries=3
Defaults:%oper1c        !lecture
```

### 10.7. Журналирование sudo

- По умолчанию sudo пишет в syslog с facility `authpriv`: это `/var/log/auth.log` (при установленном rsyslog) и журнал systemd. В журнал попадают и успешные запуски, и отказы.

  ```bash
  sudo journalctl -t sudo --since today          # все записи sudo за сегодня
  sudo journalctl -t sudo -g 'COMMAND=' -n 50    # последние 50 выполненных команд
  sudo grep -a 'sudo:' /var/log/auth.log | tail -n 30
  sudo journalctl -t sudo -g 'NOT in sudoers|incorrect password'   # отказы (классический sudo)
  sudo journalctl _COMM=su --since yesterday     # использование su
  ```

  Формат записи классического sudo: `sudo:  admin1c : TTY=pts/0 ; PWD=/home/admin1c ; USER=root ; COMMAND=/usr/bin/systemctl restart postgresql`.

  sudo-rs для **успешного** запуска пишет запись того же вида: в исходниках (`src/sudo/pipeline.rs`, функция `log_command_execution`) строка формата — `"{} : {} PWD={} ; USER={} ; COMMAND={}"`, где второй элемент — `TTY=… ;` (при отсутствии терминала опускается) **[офиц., исходники sudo-rs]**. Поэтому поиск по `COMMAND=` работает на всех трёх LTS. А вот тексты **отказов** у sudo-rs другие: пользователю выводится «Sorry, user ИМЯ is not allowed to execute 'команда' as ПОЛЬЗОВАТЕЛЬ on ХОСТ.» / «Sorry, user ИМЯ may not run команда on ХОСТ.» / «I'm sorry ИМЯ. I'm afraid I can't do that», при исчерпании попыток — «maximum N incorrect authentication attempts», для `-n` — «interactive authentication is required». Шаблон `'NOT in sudoers|incorrect password'` рассчитан на sudo.ws; для 26.04 ищите, например, `sudo journalctl -t sudo -g 'not allowed|may not run|incorrect authentication'` — ⚠ не подтверждено, что в syslog попадает ровно тот же текст, что на экран; проверьте, выполнив заведомо запрещённую команду.

- Отдельный файл журнала (только классический sudo, 22.04/24.04 или `sudo.ws`):

  ```
  Defaults logfile="/var/log/sudo.log"
  Defaults log_year, log_host, loglinelen=0
  ```

- Запись сессий целиком (только классический sudo): `Defaults log_input, log_output`, каталог `iolog_dir` по умолчанию `/var/log/sudo-io`; просмотр — `sudo sudoreplay -l` и `sudo sudoreplay ИДЕНТИФИКАТОР`.
- В sudo-rs (26.04) журналирование идёт **только в syslog**; `logfile`, `log_input`/`log_output` и `sudoreplay` не поддерживаются **[офиц.]**. Если нужна запись сессий — переключитесь на `sudo.ws` или используйте `auditd`/`tlog`.

### 10.8. sudo-rs в Ubuntu 25.10/26.04: что проверить

Официально (документация Ubuntu Server и README проекта sudo-rs):

| Тема | Поведение sudo-rs | Что делать |
|---|---|---|
| Приглашение пароля | `[sudo: authenticate] Password:` вместо `[sudo] password for ИМЯ:` | скрипты expect переписать или использовать `sudo -S`/`--prompt ""` |
| Ввод пароля | `pwfeedback` включён — печатаются звёздочки | отключить: `Defaults !pwfeedback` |
| Журнал | только syslog; нет `logfile`, нет I/O-журналов, нет `sudoreplay`, `sudo_logsrvd` | см. 10.7 |
| Почта | отправка писем не поддерживается (`mail_badpass` принимается, но не действует) | — |
| Шаблоны в аргументах команд | только завершающий отдельный `*`; `/bin/rm *.txt` не разрешит `rm README.txt` | перечислять команды явно |
| `sudo -E` | не поддерживается (окружение целиком не сохраняется; флаг либо отвергается, либо игнорируется с предупреждением — зависит от версии) | `Defaults env_keep += "..."` или `--preserve-env=СПИСОК` |
| `sudo -H` | не нужен: `HOME` целевого пользователя выставляется всегда | убрать из скриптов или проверить, что версия его принимает |
| `sudo -l -l` / `sudo -ll` | поддерживается (подробный формат) | — |
| Прочие ключи | поддерживаются `-A`, `-B`, `-b`, `-D`, `-e`, `-g`, `-i`, `-K`, `-k`, `-l`, `-n`, `-p`, `-S`, `-s`, `-U`, `-u`, `-V`, `-v`; **нет** `-P`, `-C`, `-T`, `-r`/`-t` (SELinux), `-R`/`--chroot`, `--host` | man `sudo-rs(8)` в 26.04 |
| Файл правил | читает `/etc/sudoers-rs` (предназначен для сосуществования с sudo.ws) и `/etc/sudoers` | если на сервере есть `/etc/sudoers-rs`, правьте его: `ls -l /etc/sudoers-rs /etc/sudoers`. ⚠ порядок приоритета документация не описывает |
| Области `Defaults` | `Defaults:user`, `@host`, `>runas`, `!cmnd` поддерживаются | — |
| Правило при нескольких совпадениях | как в sudo.ws: «the last match is used» | — |
| `env_reset` | всегда включён, отключить нельзя | — |
| `timestamp_type` | только `tty` и `ppid` | — |
| LDAP | нет `sudoers.ldap`, пакет `sudo-ldap` удалён | LDAP-аутентификация через PAM/SSSD |
| Лимиты и umask | всегда через PAM | настраивать `pam_limits`/`pam_umask`, а не sudoers |
| Кодировка sudoers | файл должен быть корректным UTF-8 | не оставлять комментарии в cp1251 |
| Значения по умолчанию | `timestamp_timeout=15`, `passwd_tries=3`, `use_pty` включён | совпадают с классическим sudo |
| Справка | `sudo-rs --help`, `man sudoers-rs` | список поддерживаемого зависит от версии пакета |

Переключение реализации **[офиц.]**:

```bash
sudo --version                                         # какая реализация активна
update-alternatives --display sudo
sudo update-alternatives --set sudo /usr/bin/sudo.ws            # вернуться на классический sudo
sudo update-alternatives --set sudo /usr/lib/cargo/bin/sudo     # снова sudo-rs
```

Классический sudo в 25.10/26.04 поставляется пакетом `sudo` с суффиксом `.ws` у программ (`sudo.ws`, `visudo.ws`, `sudoreplay.ws`); Canonical переключение на него не рекомендует, но поддерживает на всём сроке жизни 26.04. ⚠ не подтверждено: установлен ли пакет `sudo` по умолчанию в минимальной установке 26.04 — проверьте `dpkg -l 'sudo*'`.

### 10.9. su

`su` (пакет `util-linux`) запускает оболочку от имени другого пользователя и спрашивает пароль **целевого** пользователя (root пароль не спрашивают).

```
su [ключи] [-] [пользователь [аргументы]]
```

| Ключ | Действие |
|---|---|
| `-`, `-l`, `--login` | оболочка входа: окружение очищается, выставляются `HOME`, `SHELL`, `USER`, `LOGNAME`, `PATH`, переход в домашний каталог |
| `-c 'команда'` | выполнить одну команду |
| `-s ОБОЛОЧКА` | использовать указанную оболочку (если оболочка учётки не из `/etc/shells`, например `nologin`, ключ действует только для root) |
| `-m`, `-p` | сохранить окружение вызывающего |
| `-g`, `-G` | задать основную/дополнительную группу (только root) |
| `-P`, `--pty` | запустить в отдельном псевдотерминале |

```bash
sudo su -                               # оболочка root (в Ubuntu прямой `su -` не сработает: у root нет пароля)
sudo su - postgres                      # оболочка входа postgres
sudo su -s /bin/bash - www-data         # для учётки с nologin
sudo su - postgres -c "pg_lsclusters"   # одна команда
```

Без `-` (`su postgres`) сохраняются текущий каталог и большая часть окружения — источник странных ошибок с `PATH` и `HOME`; используйте `su -`. В скриптах и cron предпочтительнее `sudo -u` (журналируется, не требует пароля целевой учётки) или `runuser -u ИМЯ -- команда` (только от root, без PAM-аутентификации).

Конфигурация: `/etc/pam.d/su`, `/etc/pam.d/su-l`, `/etc/default/su`, `/etc/login.defs`. Неудачные попытки пишутся в `btmp`.

---

## 11. PAM и лимиты (кратко)

### 11.1. PAM

PAM (Pluggable Authentication Modules) — цепочки модулей, через которые проходят вход в систему, `su`, `sudo`, `sshd`, `passwd`, cron. Конфигурация — `/etc/pam.d/<сервис>`. В Ubuntu общие части вынесены в файлы:

| Файл | Тип | Что делает |
|---|---|---|
| `/etc/pam.d/common-auth` | auth | проверка личности (`pam_unix`, при настройке — `pam_faillock`, `pam_sss`) |
| `/etc/pam.d/common-account` | account | допустимость входа (срок учётки, блокировка) |
| `/etc/pam.d/common-password` | password | смена пароля (`pam_pwquality`, `pam_unix ... yescrypt`) |
| `/etc/pam.d/common-session`, `common-session-noninteractive` | session | подготовка сеанса (`pam_umask`, `pam_systemd`, `pam_limits` — в файлах отдельных сервисов) |

Эти файлы генерирует `pam-auth-update` из профилей `/usr/share/pam-configs/` **[офиц.]**:

```bash
sudo pam-auth-update                     # интерактивно включить/выключить профили
sudo pam-auth-update --enable ИМЯ_ПРОФИЛЯ
sudo pam-auth-update --disable ИМЯ_ПРОФИЛЯ
```

Если вручную добавить модуль внутрь управляемого блока, `pam-auth-update` сочтёт файл локально изменённым и перестанет его обновлять (пока не указать `--force`; старые версии сохраняются с суффиксом `.pam-old`). Правя PAM, **держите открытой вторую root-сессию** до проверки входа: ошибка в `common-auth` закрывает вход всем.

### 11.2. /etc/security/limits.conf и pam_limits

Формат строки **[офиц., man limits.conf]**:

```
<домен>  <тип>  <ресурс>  <значение>
```

- домен: имя пользователя, `@группа`, `*` (все), диапазон UID `1000:2000`;
- тип: `soft` (текущее значение, пользователь может поднять до hard), `hard` (потолок, задаёт root), `-` (оба сразу);
- ресурс: `nofile` (открытые файлы), `nproc` (процессы), `core` (размер core-файла, КБ), `memlock`, `stack`, `as`, `fsize`, `cpu`, `maxlogins`, `nice`, `rtprio`, `sigpending`, `msgqueue`, `locks`;
- значение: число, либо `unlimited`/`infinity`/`-1`.

```
# /etc/security/limits.d/90-1c-pg.conf
postgres   soft  nofile  65536
postgres   hard  nofile  65536
usr1cv8    -     nofile  65536
usr1cv8    -     core    unlimited
@admins    hard  nproc   4096
```

Особенности:

- Дополнительные файлы — `/etc/security/limits.d/*.conf`. Групповые записи и `*` **не действуют на root**; для root нужна явная строка `root ...`.
- Лимиты применяются модулем `pam_limits.so` в момент открытия PAM-сессии и действуют только на эту сессию и её потомков. Проверьте, что модуль подключён: `grep -r pam_limits /etc/pam.d/`.
- **На службы systemd `limits.conf` не влияет.** Сервер 1С, PostgreSQL, Apache запускаются systemd без PAM-сессии; их лимиты задаются в юните **[офиц., systemd.exec]**:

  | Директива юнита | Аналог `ulimit` |
  |---|---|
  | `LimitNOFILE=` | `ulimit -n` |
  | `LimitNPROC=` | `ulimit -u` |
  | `LimitCORE=` | `ulimit -c` |
  | `LimitMEMLOCK=` | `ulimit -l` |
  | `LimitSTACK=` | `ulimit -s` |
  | `LimitAS=` | `ulimit -v` |

  ```bash
  sudo systemctl edit postgresql@16-main.service
  #   [Service]
  #   LimitNOFILE=65536
  sudo systemctl restart postgresql@16-main.service
  systemctl show postgresql@16-main.service -p LimitNOFILE -p LimitNPROC -p LimitCORE
  ```

  Значения по умолчанию для всех служб — `DefaultLimitNOFILE=` и подобные в `/etc/systemd/system.conf`. Для ограничения числа процессов службы systemd рекомендует `TasksMax=`, для памяти — `MemoryMax=`.

### 11.3. ulimit

`ulimit` — встроенная команда оболочки: показывает и меняет лимиты текущей оболочки и её потомков.

```bash
ulimit -a                 # все мягкие лимиты
ulimit -Ha                # все жёсткие
ulimit -n                 # открытые файлы (soft)
ulimit -Hn                # открытые файлы (hard)
ulimit -n 65536           # поднять soft (не выше hard)
ulimit -c unlimited       # разрешить core-файлы
ulimit -u                 # максимум процессов пользователя
```

Лимиты **уже работающего** процесса:

```bash
cat /proc/$(pgrep -o ragent)/limits
sudo prlimit --pid $(pgrep -o -x postgres)                 # показать
sudo prlimit --pid 12345 --nofile=65536:65536              # изменить на лету (до перезапуска процесса)
```

Проверять лимиты сервера 1С командой `sudo -u usr1cv8 bash -c 'ulimit -n'` бессмысленно: она показывает лимиты PAM-сессии sudo, а не службы. Правильно — через `/proc/<pid>/limits`.

---

## 12. Политика паролей и блокировка учётных записей

### 12.1. Что есть «из коробки»

По документации Ubuntu Server **[офиц.]**: минимальная длина пароля по умолчанию — 6 символов, проверки выполняет `pam_unix` с опцией `obscure` в `/etc/pam.d/common-password`; увеличить длину можно, дописав `minlen=8` в строку `pam_unix.so`. Правила длины/сложности **не применяются**, когда пароль задаёт root (`sudo passwd ИМЯ`).

### 12.2. pam_pwquality

```bash
sudo apt install libpam-pwquality        # профиль подключается через pam-auth-update автоматически
grep pwquality /etc/pam.d/common-password
#   password  requisite  pam_pwquality.so retry=3
```

Настройки — `/etc/security/pwquality.conf` и `/etc/security/pwquality.conf.d/*.conf` **[офиц., man pwquality.conf]**:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `minlen` | `8` | минимальная длина (с учётом «кредитов») |
| `difok` | `1` | сколько символов должно отличаться от старого пароля |
| `dcredit`, `ucredit`, `lcredit`, `ocredit` | `0` | цифры / заглавные / строчные / прочие; **отрицательное** значение — минимум таких символов (`dcredit = -1` — хотя бы одна цифра) |
| `minclass` | `0` | минимум классов символов (из четырёх) |
| `maxrepeat` | `0` | максимум одинаковых символов подряд |
| `maxsequence` | `0` | максимум монотонной последовательности (`12345`, `abcde`) |
| `maxclassrepeat` | `0` | максимум подряд идущих символов одного класса |
| `dictcheck` | `1` | проверка по словарю cracklib |
| `usercheck` | `1` | пароль не должен содержать имя пользователя |
| `gecoscheck` | `0` | не должен содержать слова из поля GECOS |
| `retry` | `1` | число попыток ввода |
| `enforcing` | `1` | `0` — только предупреждать |
| `enforce_for_root` | выкл. | применять и к root |
| `local_users_only` | выкл. | не проверять нелокальных пользователей |

```
# /etc/security/pwquality.conf.d/50-site.conf
minlen = 12
minclass = 3
maxrepeat = 3
dcredit = -1
ucredit = -1
usercheck = 1
enforce_for_root
```

Проверка: `passwd` от имени обычного пользователя с заведомо слабым паролем. Сроки действия паролей задаются отдельно: `chage` для существующих учёток, `PASS_MAX_DAYS`/`PASS_MIN_DAYS`/`PASS_WARN_AGE` в `/etc/login.defs` — для вновь создаваемых.

### 12.3. Ручная блокировка

| Действие | Команда | Что реально происходит |
|---|---|---|
| Заблокировать пароль | `sudo passwd -l ИМЯ` или `sudo usermod -L ИМЯ` | в `/etc/shadow` перед хэшем ставится `!`; **вход по SSH-ключу, `sudo -u`, cron продолжают работать** |
| Разблокировать пароль | `sudo passwd -u ИМЯ` / `sudo usermod -U ИМЯ` | `!` убирается |
| Отключить учётную запись целиком | `sudo usermod -L -e 1 ИМЯ` (или `sudo chage -E 0 ИМЯ`) | срок действия учётки истёк — вход закрыт для всех методов, проходящих PAM account |
| Включить обратно | `sudo usermod -U -e "" ИМЯ` | |
| Запретить интерактивный вход, оставив учётку | `sudo usermod -s /usr/sbin/nologin ИМЯ` | |
| Выгнать из системы | `sudo loginctl terminate-user ИМЯ` или `sudo pkill -KILL -u ИМЯ` | |

Порядок при увольнении администратора **[офиц., Ubuntu Server: User management]**: заблокировать/просрочить учётку, удалить или переименовать `~ИМЯ/.ssh/authorized_keys`, завершить сессии (`w`, `loginctl`), убрать из групп `sudo` и прочих, проверить `/etc/sudoers.d/`, crontab (`sudo crontab -l -u ИМЯ`) и пароли ролей в PostgreSQL/1С, которые он знал.

### 12.4. Автоматическая блокировка: pam_faillock

`pam_faillock` считает неудачные попытки аутентификации за интервал и временно блокирует учётную запись. В Ubuntu модуль входит в `libpam-modules`, но в стек по умолчанию **не включён** (`pam_tally2` удалён начиная с 22.04).

Настройки — `/etc/security/faillock.conf` **[офиц., man faillock.conf]**:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `deny` | `3` | после скольких подряд неудач блокировать |
| `fail_interval` | `900` | окно подсчёта, секунд |
| `unlock_time` | `600` | через сколько секунд снять блокировку; `0` — только вручную |
| `dir` | `/var/run/faillock` | каталог счётчиков (на tmpfs — обнуляется при перезагрузке) |
| `even_deny_root` | выкл. | блокировать и root |
| `root_unlock_time` | = `unlock_time` | время разблокировки root |
| `audit` | выкл. | писать в журнал имя несуществующего пользователя |
| `silent` | выкл. | не сообщать пользователю о блокировке |
| `local_users_only` | выкл. | учитывать только локальных пользователей |
| `admin_group` | не задано | члены группы обрабатываются как root |

```
# /etc/security/faillock.conf
deny = 5
fail_interval = 900
unlock_time = 900
audit
silent
```

Включение в стек. Вариант из DISA STIG для Ubuntu 24.04 — добавить в `/etc/pam.d/common-auth` **сразу после** строки `pam_unix.so`:

```
auth    [success=1 default=ignore]      pam_unix.so nullok        # существующая строка
auth    [default=die]                   pam_faillock.so authfail
auth    sufficient                      pam_faillock.so authsucc
auth    requisite                       pam_deny.so               # существующая строка
auth    required                        pam_permit.so             # существующая строка
```

Дополнительно по man pam_faillock: строка `auth required pam_faillock.so preauth` **перед** `pam_unix.so` (выводит сообщение о блокировке и отказывает до запроса пароля) и `account required pam_faillock.so` в `/etc/pam.d/common-account`. ⚠ Точная раскладка зависит от того, что уже есть в `common-auth` (SSSD, другие модули, значения `success=N`): после правки пересчитайте «прыжки» `success=N` и проверьте вход во второй сессии.

Что проверено рецензентом и что нет:

- Текст STIG V-270690 (Ubuntu 24.04) сверен дословно: «add the following lines below the "auth" definition for pam_unix.so» — `auth [default=die] pam_faillock.so authfail` и `auth sufficient pam_faillock.so authsucc`. Те же две строки — первый пример в man `pam_faillock(8)` (22.04: PAM 1.4.0, 24.04: 1.5.3, 26.04: 1.7.0) **[офиц.]**. Сам STIG требует в `faillock.conf`: `audit`, `silent`, `deny = 3`, `fail_interval = 900`, `unlock_time = 0` (только ручная разблокировка) — для сервера 1С без дежурного администратора `unlock_time = 0` опасен, выбирайте конечное время.
- Логика со штатным `success=1` разобрана «на бумаге»: при успехе `pam_unix` перескакивает одну строку (`authfail`) и попадает на `authsucc` с `sufficient` — стек завершается успехом и счётчик сбрасывается; при неудаче выполняется `authfail` с `[default=die]` — стек завершается отказом. Побочный эффект: строки ниже (`pam_deny`, `pam_permit` и блок «Additional», в Ubuntu это `auth optional pam_cap.so`) при успешном входе **уже не выполняются**. Если используется `/etc/security/capability.conf` (`pam_cap`), такая раскладка его отключит. ⚠ На живой системе раскладка рецензентом не проверялась — обязателен тест во второй root-сессии.
- В man `pam_faillock` рекомендовано не задавать параметры в строке модуля, а держать их в `/etc/security/faillock.conf`.
- Готового профиля `pam-auth-update` для faillock man-страницы 22.04/24.04/26.04 не упоминают; ⚠ не подтверждено его отсутствие в `/usr/share/pam-configs/` (проверка: `ls /usr/share/pam-configs/`). При ручной правке `common-auth` утилита `pam-auth-update` будет считать файл изменённым локально (см. 11.1).
- Проверка, что модуль реально включён: `grep -n faillock /etc/pam.d/common-auth /etc/pam.d/common-account`; пустой вывод — блокировки по числу попыток нет.

**Вариант Б — через профили `pam-auth-update` (подход CIS Benchmark для Ubuntu 22.04)** **[практика: шаблоны проекта ansible-lockdown/UBUNTU22-CIS, сверены рецензентом дословно]**. Преимущества: `common-auth` и `common-account` не правятся руками, `pam-auth-update` сам пересчитывает `success=N`, блок «Additional» (`pam_cap.so`) продолжает выполняться, откат — одной командой.

Файл `/usr/share/pam-configs/faillock` (отступ в строках модулей — табуляция):

```
Name: Enable pam_faillock to deny access
Default: yes
Priority: 0
Auth-Type: Primary
Auth:
	[default=die]	pam_faillock.so authfail
```

Файл `/usr/share/pam-configs/faillock_notify`:

```
Name: Notify of failed login attempts and reset count upon success
Default: yes
Priority: 1024
Auth-Type: Primary
Auth:
	requisite	pam_faillock.so preauth
Account-Type: Primary
Account:
	required	pam_faillock.so
```

```bash
sudo pam-auth-update --enable faillock faillock_notify   # включить оба профиля
grep -n -E 'faillock|pam_unix|pam_deny|pam_permit' /etc/pam.d/common-auth /etc/pam.d/common-account
sudo pam-auth-update --disable faillock faillock_notify  # откат
```

Ожидаемый результат в `common-auth` (порядок задаётся приоритетами 1024 → 256 (`unix`) → 0): `requisite pam_faillock.so preauth`, затем `[success=2 default=ignore] pam_unix.so nullok`, затем `[default=die] pam_faillock.so authfail`, затем штатные `pam_deny.so` и `pam_permit.so`; в `common-account` — `required pam_faillock.so` перед `pam_unix.so`. Счётчик при успешном входе сбрасывает account-фаза модуля. ⚠ Ожидаемый вид файлов выведен рецензентом из правил `pam-auth-update`, на живой системе не проверялся: сравните фактический результат `grep` с описанным, и только после успешного входа во **второй** сессии закрывайте первую. Профили с именами `faillock*` в `/usr/share/pam-configs/` могут уже существовать (поставлены другим средством усиления защиты) — сначала `ls /usr/share/pam-configs/`.

Управление:

```bash
sudo faillock                          # счётчики всех пользователей
sudo faillock --user ivanov            # неудачные попытки пользователя
sudo faillock --user ivanov --reset    # снять блокировку
```

Замечания:

- Вход по SSH-ключу не проходит через `auth`-стек PAM, поэтому `pam_faillock` его не считает и не блокирует.
- Блокировка локальной учётки после перебора паролей по SSH — это отказ в обслуживании для самого администратора. Для защиты SSH от перебора эффективнее отключить парольный вход (`PasswordAuthentication no`) и/или использовать `fail2ban`.
- root по умолчанию не блокируется (нужен `even_deny_root`).

---

## 13. SSH-ключи и authorized_keys

### 13.1. Настройка входа по ключу

```bash
# на рабочей станции администратора (Windows 10/11: в PowerShell те же команды OpenSSH)
ssh-keygen -t ed25519 -C "admin1c@workstation"
ssh-copy-id admin1c@srv1c                 # в Windows ssh-copy-id нет — см. ниже
ssh admin1c@srv1c
```

Вручную (в том числе с Windows):

```bash
# на сервере, от имени владельца учётной записи
mkdir -p ~/.ssh && chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys               # вставить строку "ssh-ed25519 AAAA... комментарий"
chmod 600 ~/.ssh/authorized_keys
```

Если файлы создавались от root — вернуть владельца: `sudo chown -R admin1c:admin1c /home/admin1c/.ssh`.

### 13.2. Требуемые права

| Объект | Права | Почему |
|---|---|---|
| домашний каталог | не доступен на запись группе и остальным (`750`/`755`) | StrictModes |
| `~/.ssh` | `700` | рекомендация man sshd |
| `~/.ssh/authorized_keys` | `600` | рекомендация man sshd |
| `~/.ssh/id_ed25519` (приватный ключ) | `600` | иначе клиент `ssh` откажется его использовать |
| `~/.ssh/id_ed25519.pub`, `known_hosts`, `config` | `644` / `600` | |

При `StrictModes yes` (по умолчанию) `sshd` **не использует** `authorized_keys`, если сам файл, каталог `~/.ssh` или домашний каталог доступны на запись другим пользователям **[офиц., man sshd]**. Внешне это выглядит как «ключ не принимается, спрашивает пароль». Диагностика:

```bash
sudo journalctl -u ssh -n 50 | grep -i -E 'authentication refused|bad ownership|modes'
namei -l ~/.ssh/authorized_keys
ssh -v admin1c@srv1c                      # на клиенте: какие ключи предлагаются и что отвечает сервер
```

### 13.3. Настройки sshd

Файл `/etc/ssh/sshd_config` и фрагменты `/etc/ssh/sshd_config.d/*.conf`. В Ubuntu фрагменты включаются в начале основного файла, а для большинства директив действует **первое** встреченное значение — поэтому фрагмент переопределяет основной файл, а из двух фрагментов побеждает тот, чьё имя раньше по алфавиту **[офиц.]**.

```
# /etc/ssh/sshd_config.d/10-hardening.conf
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
AllowGroups sshusers
```

```bash
sudo addgroup sshusers && sudo adduser admin1c sshusers
sudo sshd -t                              # проверка синтаксиса
sudo sshd -T | grep -i -E 'passwordauth|permitroot|allowgroups'   # действующие значения
sudo systemctl restart ssh.service        # служба в Ubuntu называется ssh
```

- На облачных образах cloud-init создаёт `/etc/ssh/sshd_config.d/50-cloud-init.conf` с `PasswordAuthentication yes` — ваш файл должен иметь меньший номер **[практика]**.
- Не закрывайте текущую сессию, пока не проверите вход по ключу в новой.
- `passwd -l` не мешает входу по ключу; чтобы закрыть доступ, уберите ключ из `authorized_keys` или исключите пользователя из `AllowGroups`.

### 13.4. Ключи сервисных учёток и ограничения в authorized_keys

Для передачи бэкапов и WAL между серверами ключи создаются от имени `postgres` (домашний каталог — `/var/lib/postgresql`):

```bash
sudo -u postgres ssh-keygen -t ed25519 -N "" -f /var/lib/postgresql/.ssh/id_ed25519
sudo -u postgres cat /var/lib/postgresql/.ssh/id_ed25519.pub
```

На принимающей стороне ключ стоит ограничить опциями в начале строки `authorized_keys` **[офиц., man sshd]**:

```
from="10.0.0.15",restrict,command="/usr/local/bin/backup-receive.sh" ssh-ed25519 AAAA... postgres@srv1c
```

- `from="шаблон"` — разрешённые адреса клиента;
- `command="..."` — принудительная команда (исходная доступна в `SSH_ORIGINAL_COMMAND`);
- `restrict` — отключить проброс портов, агента, X11, выделение PTY и `~/.ssh/rc`; отдельные возможности возвращаются опциями `pty`, `port-forwarding` и т.д.

---

## 14. Диагностика «Permission denied»

### 14.1. Сначала различить ошибку

| Сообщение (errno) | Типичные причины |
|---|---|
| `Permission denied` (EACCES) | нет нужного бита в правах/ACL; нет `x` на одном из каталогов пути; маска ACL; AppArmor; `noexec` при запуске программы |
| `Operation not permitted` (EPERM) | атрибут `i`/`a`; попытка `chown`/`chmod` чужого файла не от root; нехватка capability; ограничения systemd/seccomp |
| `Read-only file system` (EROFS) | раздел смонтирован `ro` (в том числе аварийно после ошибок ФС); `ProtectSystem=`/`ReadOnlyPaths=` в юните |
| `No such file or directory` (ENOENT) | путь не существует **для этого процесса** (другой `/tmp` при `PrivateTmp=true`, `ProtectHome=`, несмонтированный том) |

### 14.2. Пошаговый алгоритм

**Шаг 1. От чьего имени на самом деле работает процесс и какие у него группы.**

```bash
ps -o user:12,group:12,supgrp:40,pid,cmd -C rphost,rmngr,ragent
ps -o user:12,group:12,supgrp:40,pid,cmd -C postgres | head -3
grep -E '^(Uid|Gid|Groups)' /proc/$(pgrep -o rmngr)/status
```

Если нужной группы в `Groups` нет, а в `id usr1cv8` она есть — служба запущена до изменения членства: перезапустить.

**Шаг 2. Права по всей цепочке каталогов.**

```bash
namei -l /srv/1c/exchange/in/data.xml
```

```
f: /srv/1c/exchange/in/data.xml
drwxr-xr-x root    root    /
drwxr-xr-x root    root    srv
drwxr-x--- admin1c admin1c 1c          <-- usr1cv8 сюда не пройдёт
drwxrws--- usr1cv8 exch1c  exchange
drwxrws--- usr1cv8 exch1c  in
-rw-rw---- usr1cv8 exch1c  data.xml
```

Ключи `namei`: `-l` (= `-m -o -v`: режимы, владельцы, выравнивание), `-x` (отмечать точки монтирования буквой `D`), `-n` (не следовать символьным ссылкам). Для символьной ссылки `namei` показывает и саму ссылку, и путь, на который она указывает.

**Шаг 3. Проверка от имени нужного пользователя.**

```bash
sudo -u usr1cv8 test -r /srv/1c/exchange/in/data.xml && echo "чтение OK" || echo "чтения НЕТ"
sudo -u usr1cv8 test -w /srv/1c/exchange/in          && echo "запись OK" || echo "записи НЕТ"
sudo -u usr1cv8 test -x /srv/1c                      && echo "проход OK" || echo "прохода НЕТ"
sudo -u usr1cv8 ls -la /srv/1c/exchange/in
sudo -u usr1cv8 sh -c 'touch /srv/1c/exchange/in/.probe && rm /srv/1c/exchange/in/.probe && echo "создание/удаление OK"'
sudo -u postgres head -c 16 /srv/backup/pg/base1.dump | od -c | head -1
sudo -u www-data test -r /var/www/base1/default.vrd && echo OK
```

`sudo -u` заново вычисляет группы пользователя из `/etc/group`, поэтому результат отражает то, что получит служба **после перезапуска**, а не её текущее состояние (см. шаг 1).

**Шаг 4. ACL и маска.**

```bash
getfacl -e /srv/1c/exchange/in
```

Ищите `#effective:` — запись есть, но урезана маской (раздел 8.3).

**Шаг 5. Атрибуты.**

```bash
lsattr -d /srv/1c/exchange/in ; lsattr /srv/1c/exchange/in/data.xml
```

**Шаг 6. Файловая система и опции монтирования.**

```bash
findmnt -T /srv/1c/exchange/in            # устройство, тип ФС, опции (ro, noexec, nosuid, uid=, gid=)
df -hT /srv/1c/exchange/in
sudo dmesg | tail -n 30                   # ошибки ФС, перемонтирование в read-only
```

Для CIFS/NFS/vboxsf права определяются опциями монтирования и сервером (у NFS — `root_squash`), а не `chmod` на клиенте.

**Шаг 7. Ограничения systemd у службы.**

```bash
systemctl cat apache2.service | grep -E 'PrivateTmp|Protect|ReadOnly|ReadWrite|Inaccessible|NoNewPriv|UMask|User=|Group='
systemd-analyze security apache2.service | head -n 40
```

`PrivateTmp=true` (свой `/tmp`), `ProtectHome=true` (каталоги `/home`, `/root` недоступны), `ProtectSystem=strict|full` (`/usr`, `/etc`, а при `strict` — почти вся ФС только для чтения), `ReadOnlyPaths=`, `InaccessiblePaths=` дают отказ при формально правильных правах файла. Разрешить каталог — drop-in с `ReadWritePaths=/srv/...`.

**Шаг 8. AppArmor.**

AppArmor ограничивает программу поверх обычных прав: при запрете в режиме enforce программа получает тот же `Permission denied`, а в журнале ядра появляется запись.

```bash
sudo aa-status                                              # загруженные профили и режимы (enforce/complain)
sudo aa-status | grep -i -E 'postgres|apache|1c|mysqld|cups'
sudo dmesg | grep -i 'apparmor="DENIED"' | tail
sudo journalctl -k -g 'apparmor="DENIED"' --since "30 min ago"
```

Формат записи:

```
audit: type=1400 ... apparmor="DENIED" operation="open" profile="/usr/sbin/cups-browsed" name="/путь/к/файлу" pid=1234 comm="..." requested_mask="r" denied_mask="r" fsuid=33 ouid=0
```

Поля: `profile` — чей профиль сработал, `name` — к чему обращались, `requested_mask`/`denied_mask` — какой доступ (r, w, x, k — блокировка, m — mmap), `comm` — процесс. Явные запреты (`deny` в профиле) в журнал **не пишутся** **[офиц.]**.

Исправление **[офиц., Ubuntu Server: AppArmor]**:

```bash
# 1. Добавить правило в локальное дополнение профиля (переживает обновление пакета)
echo '/srv/data/** rw,' | sudo tee -a /etc/apparmor.d/local/usr.sbin.ИМЯ_ПРОФИЛЯ
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.ИМЯ_ПРОФИЛЯ     # перечитать один профиль
sudo systemctl reload apparmor.service                            # перечитать все

# 2. Временно перевести профиль в режим «только журналировать» (нужен пакет apparmor-utils)
sudo apt install apparmor-utils
sudo aa-complain /etc/apparmor.d/usr.sbin.ИМЯ_ПРОФИЛЯ
sudo aa-enforce  /etc/apparmor.d/usr.sbin.ИМЯ_ПРОФИЛЯ            # вернуть

# 3. Сформировать правила по журналу
sudo aa-logprof
```

Профили лежат в `/etc/apparmor.d/` (имя файла — путь к программе с точками вместо `/`), локальные дополнения — в `/etc/apparmor.d/local/`, отключённые — символьные ссылки в `/etc/apparmor.d/disable/`.

Быстрая и однозначная проверка, ограничен ли **конкретный работающий процесс** профилем AppArmor (метка `unconfined` — не ограничен; имя профиля с `(enforce)` — ограничен):

```bash
ps -eo pid,user:10,label:40,comm | grep -E 'postgres|ragent|rmngr|rphost|apache2'   # столбец LABEL — метка AppArmor
sudo cat /proc/$(pgrep -o -x postgres)/attr/current                                 # то же для одного процесса
sudo cat /proc/$(pgrep -o ragent)/attr/current
ls /etc/apparmor.d/ | grep -i -E 'postgres|pgpro|1c|apache'                         # есть ли файлы профилей
```

Отключить профиль целиком (крайняя мера) **[офиц., Ubuntu Server: AppArmor]**: `sudo ln -s /etc/apparmor.d/ИМЯ_ПРОФИЛЯ /etc/apparmor.d/disable/` и `sudo apparmor_parser -R /etc/apparmor.d/ИМЯ_ПРОФИЛЯ`. Дополнительные профили ставит пакет `apparmor-profiles`. Отказы пишутся в `auditd` (`/var/log/audit/audit.log`), если он установлен, иначе в syslog/журнал ядра **[офиц., release notes 26.04]**.

Применительно к 1С и PostgreSQL: в стандартных пакетах PostgreSQL для Ubuntu и в дистрибутиве платформы 1С собственных профилей AppArmor нет (⚠ не подтверждено первоисточником: ни документация Ubuntu, ни PostgreSQL, ни 1С этого прямо не утверждают, а в 25.04–26.04 пакет `apparmor` получил «many new profiles for applications» — проверьте командами выше на своём сервере), поэтому AppArmor чаще оказывается причиной для **других** участников: программ из snap, `tcpdump`, `rsyslogd`, `chronyd`, `cups`, MySQL/MariaDB, libvirt, а также Apache при установленном `libapache2-mod-apparmor`. Начиная с 25.04 в Ubuntu добавлено много новых профилей, которые «могут ломать нестандартные сценарии использования приложений» **[офиц., release notes]** — после обновления до 26.04 проверка `DENIED` в журнале обязательна.

**Шаг 9. Если ничего не помогло — посмотреть системные вызовы.**

```bash
sudo apt install strace
sudo strace -f -e trace=%file -p $(pgrep -o rphost) 2>&1 | grep -E 'EACCES|EPERM|EROFS'
```

В выводе будет точный путь и вызов, на котором получен отказ.

### 14.3. Быстрая сводка причин

| Признак | Вероятная причина | Проверка |
|---|---|---|
| Файл лежит в `/home/<админ>/...` | домашний каталог `0750` | `namei -l` |
| Группа добавлена, доступа нет | служба/сессия не перезапущена | `/proc/<pid>/status` → `Groups` |
| ACL есть, доступа нет | маска урезана `chmod` | `getfacl -e` |
| Не удаляется даже root | `chattr +i`/`+a` | `lsattr` |
| Из консоли работает, из службы нет | `PrivateTmp`, `ProtectHome`, AppArmor, другое окружение | `systemctl cat`, `dmesg` |
| На сетевом ресурсе `chmod` не помогает | CIFS/NFS: права задаёт монтирование/сервер | `findmnt -T` |
| Внезапно «Read-only file system» | ФС перемонтирована в `ro` после ошибок диска | `dmesg`, `findmnt` |

---

## 15. Типовые сценарии

### 15.1. Дать usr1cv8 доступ на запись в каталог обмена

**Вариант А — каталог нужен только серверу 1С:**

```bash
sudo install -d -o usr1cv8 -g grp1cv8 -m 0750 /srv/1c/exchange
```

**Вариант Б — каталогом пользуются сервер 1С, администраторы и скрипты (рекомендуется):** общая группа + SGID + ACL по умолчанию.

```bash
sudo groupadd exch1c
sudo usermod -aG exch1c usr1cv8
sudo usermod -aG exch1c admin1c                     # и другие участники обмена
sudo install -d -o usr1cv8 -g exch1c -m 2770 /srv/1c/exchange
sudo setfacl -d -m u::rwx,g::rwx,o::--- /srv/1c/exchange
sudo systemctl restart srv1cv8-8.3.27.1688@default.service   # чтобы rphost получил новую группу

# проверка
getfacl /srv/1c/exchange
sudo -u usr1cv8 sh -c 'touch /srv/1c/exchange/.probe && ls -l /srv/1c/exchange/.probe && rm /srv/1c/exchange/.probe'
```

Зачем каждый элемент: SGID (`2`) — новые файлы получают группу `exch1c`, кто бы их ни создал; default-ACL `g::rwx` — файлы, созданные службой 1С с `UMask=0022`, всё равно будут доступны группе на запись (`rw-rw----`); `o::---` — посторонним доступа нет.

**Вариант В — каталог чужой, владельца менять нельзя:** точечный ACL.

```bash
sudo setfacl -R -m u:usr1cv8:rwX /data/partner/exchange
sudo setfacl -R -d -m u:usr1cv8:rwX /data/partner/exchange
sudo setfacl -m u:usr1cv8:--x /data /data/partner        # право прохода по родительским каталогам, если его нет
namei -l /data/partner/exchange
```

**Вариант Г — сетевой ресурс Windows (CIFS):** `chown`/`setfacl` не действуют, владельца задаёт монтирование (нужен пакет `cifs-utils`):

```
# /etc/fstab
//fileserver/exchange  /mnt/exchange  cifs  credentials=/etc/cifs-1c.cred,uid=usr1cv8,gid=grp1cv8,file_mode=0660,dir_mode=0770,iocharset=utf8,_netdev,nofail  0  0
```

Файл `/etc/cifs-1c.cred` (`username=...`, `password=...`, `domain=...`) — владелец `root:root`, права `600`.

**Вариант Д — общая папка гипервизора** **[практика]**: в гостевой ОС VirtualBox автоподключаемые папки (`/media/sf_ИМЯ`) принадлежат `root:vboxsf` с правами `770` — добавьте `usr1cv8` в группу `vboxsf` (`sudo usermod -aG vboxsf usr1cv8`) и перезапустите службу. В Hyper-V встроенных общих папок для Linux-гостей нет — используйте общий ресурс Windows по CIFS (вариант Г); в VMware — HGFS (`vmhgfs-fuse` с опциями `uid=`/`gid=`) или тот же CIFS.

Что ещё учесть: путь в коде 1С (`&НаСервере`) — это путь **на сервере**; файлы, загруженные администратором через WinSCP/scp, принадлежат администратору — при варианте Б они сразу попадают в группу `exch1c`, но права `rw-r--r--` у загруженного файла может понадобиться расширить (`chmod g+w`), если default-ACL не применился (например, файл перенесён командой `mv`).

### 15.2. Общий каталог для postgres и скриптов резервного копирования

Задача: `pg_dump` пишет от имени `postgres`, а копирование на внешнее хранилище и ротацию выполняет скрипт под другой учётной записью.

```bash
sudo groupadd pgbackup
sudo usermod -aG pgbackup postgres
sudo adduser --disabled-password --comment "Backup operator" backupop   # в 22.04 вместо --comment используйте --gecos
sudo usermod -aG pgbackup backupop
sudo install -d -o postgres -g pgbackup -m 2770 /srv/backup/pg
sudo setfacl -d -m u::rwx,g::rwx,o::--- /srv/backup/pg

# проверка
sudo -u postgres pg_dump -Fc -f /srv/backup/pg/base1_$(date +%F).dump base1
ls -l /srv/backup/pg
sudo -u backupop test -r /srv/backup/pg/base1_$(date +%F).dump && echo "backupop читает"
```

Варианты и замечания:

- Если скрипту достаточно **читать** дампы — права каталога `2750` и default-ACL `g::r-x`.
- Задание cron от имени `postgres` (`sudo crontab -u postgres -e`); знак `%` в crontab экранируется:

  ```
  30 1 * * * pg_dump -Fc -f /srv/backup/pg/base1_$(date +\%F).dump base1
  ```

  Процессы cron получают группы заново при каждом запуске — перезапускать PostgreSQL ради `pg_dump` не нужно. Но операции, которые выполняет **сам сервер** (`archive_command`, серверный `COPY ... TO '/путь'`), используют группы, полученные при старте: после `usermod -aG ... postgres` нужен `sudo systemctl restart postgresql@NN-main`.
- Не размещайте бэкапы внутри каталога данных и не меняйте права каталога данных ради бэкапа.
- Чтение файлов кластера непривилегированной учёткой (например, для файлового бэкапа) — только через групповой доступ: кластер, созданный с `initdb --allow-group-access` (каталог `0750`, файлы `0640`), и членство учётки в группе `postgres` **[офиц.]**.
- Журналы PostgreSQL в Ubuntu (`/var/log/postgresql/postgresql-NN-main.log`) читаются членами группы `adm`: `pg_createcluster` создаёт файл журнала с режимом `0640` и группой `adm` (если UID владельца кластера меньше 1000) **[офиц., исходники `pg_createcluster`]**; при ротации `logrotate` права сохраняет конфигурация `/etc/logrotate.d/postgresql-common` (проверьте `ls -l /var/log/postgresql`). Журнал systemd — членами групп `adm` и `systemd-journal`. Администратору-человеку достаточно `sudo usermod -aG adm,systemd-journal admin1c`. У Postgres Pro журнал по умолчанию ведётся иначе (в каталоге данных `log/` или через journald) — ⚠ проверьте `show log_destination; show logging_collector; show log_directory;`.

### 15.3. Администратор без пароля root

Цель: root остаётся без пароля (как в Ubuntu по умолчанию), все административные действия выполняются персональными учётными записями через sudo и журналируются.

```bash
# 1. Персональная учётная запись
sudo adduser admin2
sudo usermod -aG sudo admin2

# 2. Вход по ключу
sudo install -d -o admin2 -g admin2 -m 700 /home/admin2/.ssh
echo 'ssh-ed25519 AAAAC3... admin2@workstation' | sudo tee /home/admin2/.ssh/authorized_keys
sudo chown admin2:admin2 /home/admin2/.ssh/authorized_keys
sudo chmod 600 /home/admin2/.ssh/authorized_keys

# 3. Проверка (в НОВОЙ сессии, не закрывая текущую)
ssh admin2@srv1c 'sudo -l'

# 4. Убедиться, что root закрыт
sudo passwd -S root            # второе поле: L
sudo passwd -l root            # если пароль ранее задавали
sudo sshd -T | grep -i permitrootlogin
```

По желанию:

- sudo без запроса пароля (только для учётной записи с входом по ключу): файл `/etc/sudoers.d/90-admins` со строкой `admin2 ALL=(ALL:ALL) NOPASSWD: ALL`, создать через `sudo visudo -f /etc/sudoers.d/90-admins`. Компромисс: удобство против того, что компрометация сессии = компрометация root.
- Запретить вход root и парольный вход по SSH — раздел 13.3.
- Оболочка root, когда она действительно нужна: `sudo -i` (журналируется как запуск оболочки; отдельные команды внутри неё sudo уже не пишет).
- Аварийный доступ при потере sudo/SSH — консоль виртуальной машины и пункт recovery mode в меню GRUB (root-оболочка без пароля). Поэтому доступ к консоли гипервизора на Windows-хосте равен доступу root.
- Как минимум **две** учётные записи в группе `sudo`: ошибка в одной (заблокирован пароль, испорчен `authorized_keys`, вылетела из группы) не лишит доступа.

### 15.4. Оператор с ограниченными правами (перезапуск 1С, бэкап)

См. пример файла `/etc/sudoers.d/90-admins-1c` в разделе 10.4. Порядок действий:

```bash
sudo addgroup oper1c
sudo adduser operator1 && sudo adduser operator1 oper1c
sudo visudo -f /etc/sudoers.d/90-admins-1c
sudo visudo -c
sudo -l -U operator1
```

---

## 16. Самопроверка на сервере: всё, что в этом файле помечено ⚠

Часть утверждений (в основном о внутреннем устройстве дистрибутива 1С и о поставляемых Ubuntu конфигурационных файлах) не удалось подтвердить первоисточником. Ниже — команды только на чтение, которые дают фактический ответ на конкретном сервере. Вывод полезно сохранить рядом с базой знаний.

```bash
# --- Версии ---
lsb_release -ds ; uname -r
dpkg-query -W -f='${Package} ${Version}\n' adduser passwd sudo sudo-rs util-linux openssh-server libpam-modules acl \
    postgresql-common wtmpdb lastlog2 libpam-wtmpdb libpam-lastlog2 rust-coreutils coreutils 2>/dev/null
sudo --version | head -n 2 ; update-alternatives --display sudo 2>/dev/null | head -n 5

# --- Учётная запись сервера 1С: оболочка, GECOS, тип UID, домашний каталог ---
getent passwd usr1cv8 ; getent group grp1cv8 ; id usr1cv8
sudo passwd -S usr1cv8 ; sudo chage -l usr1cv8 | head -n 4
ls -ld /home/usr1cv8 /home/usr1cv8/.1cv8 /home/usr1cv8/.1cv8/1C /home/usr1cv8/.1cv8/1C/1cv8 2>&1

# --- Каталоги 1С: владельцы и режимы ---
ls -ld /opt/1cv8 /opt/1cv8/* /opt/1cv8/x86_64/* 2>&1
sudo find /opt/1cv8 -maxdepth 4 \( -name conf -o -name 'conf.cfg' -o -name 'logcfg.xml' -o -name 'nethasp.ini' \) -exec ls -ld {} + 2>/dev/null
sudo find /opt/1cv8 -maxdepth 4 -name 'conf.cfg' -exec sh -c 'echo "== $1"; cat "$1"' _ {} \; 2>/dev/null
sudo ls -la /home/usr1cv8/.1cv8/1C/1cv8/ 2>&1 | head -n 30
ls -ld /var/1C /var/1C/licenses 2>&1 ; sudo ls -l /var/1C/licenses 2>&1

# --- Юнит сервера 1С: от кого запускается, каталог данных, лимиты, umask ---
systemctl list-unit-files 'srv1cv8*' 'ras*' 2>/dev/null
systemctl cat 'srv1cv8-*@default.service' 2>/dev/null | grep -E '^(User|Group|Environment|EnvironmentFile|ExecStart|UMask|Limit|PrivateTmp|Protect)'
systemctl show 'srv1cv8-*@default.service' -p User -p Group -p UMask -p LimitNOFILE -p LimitCORE 2>/dev/null

# --- PostgreSQL: владельцы, режимы, журнал ---
getent passwd postgres ; id postgres
sudo -u postgres psql -AXtc "select name, setting from pg_settings where name in ('data_directory','hba_file','config_file','log_directory','logging_collector','log_destination','data_directory_mode','unix_socket_directories')"
sudo ls -ld /var/lib/postgresql /var/lib/postgresql/*/main /etc/postgresql/*/main /var/log/postgresql /run/postgresql 2>&1
sudo ls -l /etc/postgresql/*/main/ /var/log/postgresql/ 2>&1
ls -ld /opt/pgpro/* /var/lib/pgpro/*/data 2>/dev/null ; cat /etc/default/postgrespro-* 2>/dev/null

# --- Умолчания Ubuntu: login.defs, adduser.conf, useradd, PAM ---
grep -E '^(UMASK|HOME_MODE|USERGROUPS_ENAB|ENCRYPT_METHOD|UID_MIN|UID_MAX|SYS_UID_MIN|SYS_UID_MAX)' /etc/login.defs
grep -E '^(DIR_MODE|SYS_DIR_MODE|DSHELL|EXTRA_GROUPS|ADD_EXTRA_GROUPS)=' /etc/adduser.conf
grep -v '^#' /etc/default/useradd
grep -nE 'pam_(unix|pwquality|faillock|umask|limits|lastlog2?|wtmpdb|cap)' /etc/pam.d/common-* /etc/pam.d/sshd /etc/pam.d/sudo /etc/pam.d/su /etc/pam.d/login 2>/dev/null
ls /usr/share/pam-configs/

# --- sudo: штатный файл и действующие умолчания ---
sudo grep -vE '^\s*(#|$)' /etc/sudoers ; sudo ls -l /etc/sudoers /etc/sudoers-rs /etc/sudoers.d/ 2>&1
sudo sudo -V 2>/dev/null | grep -iE 'timeout|tries|lecture|pty|editor|umask|syslog' | head -n 20   # подробный вывод — только у sudo.ws
sudo visudo -c

# --- История входов в 26.04 ---
command -v last lastb lastlog lastlog2 wtmpdb lslogins

# --- AppArmor: ограничены ли процессы 1С/PostgreSQL/Apache ---
sudo aa-status 2>/dev/null | head -n 5
ps -eo pid,user:10,label:40,comm | grep -E 'postgres|ragent|rmngr|rphost|apache2' | head
ls /etc/apparmor.d/ | grep -i -E 'postgres|pgpro|1c|apache'
sudo journalctl -k -g 'apparmor="DENIED"' --since "-1day" --no-pager | tail -n 20
```

Как читать результат:

| Что увидели | Вывод |
|---|---|
| `usr1cv8` с оболочкой `/usr/sbin/nologin` или `/bin/false` | `sudo -iu usr1cv8` и `su - usr1cv8` не сработают — используйте `sudo -u usr1cv8 -s` или `sudo su -s /bin/bash - usr1cv8` |
| UID `usr1cv8` ≥ 1000 | учётка создана как обычная (без `useradd -r`): при создании к ней применились сроки из `/etc/login.defs` (`PASS_MAX_DAYS` и т.д. — у системных учёток `useradd -r` сроков нет, man: «System users will be created with no aging information»), она попадает под правила `limits.conf`, заданные диапазоном UID, и под выборки вида `awk -F: '$3>=1000'`; убедиться, что сроков нет: `sudo chage -l usr1cv8`, снять: `sudo chage -E -1 -M -1 -I -1 usr1cv8` |
| каталога `/home/usr1cv8` нет | создать: `sudo install -d -o usr1cv8 -g grp1cv8 -m 0750 /home/usr1cv8` — иначе `ragent` не сможет создать `.1cv8` |
| в `/opt/1cv8` владелец не `root` | кто-то выполнил `chown -R usr1cv8:grp1cv8 /opt/1cv8` — работает, но служба может менять собственные исполняемые файлы |
| `conf.cfg` найден и содержит `ConfLocation=…` | `logcfg.xml` платформа ищет в указанном каталоге — запишите этот путь в базу знаний |
| `data_directory_mode` = `0750` | кластер PostgreSQL создан с групповым доступом; `0700` — без него |
| `label` у `postgres`/`ragent` = `unconfined` | AppArmor эти процессы не ограничивает |
| `HOME_MODE`/`DIR_MODE` не `0750` | домашние каталоги новых пользователей создаются с другими правами — учтите в диагностике «Permission denied» |

---

## Типичные ошибки и подводные камни

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | После `usermod -G группа user` пропал sudo | `-G` без `-a` заменил список дополнительных групп, пользователь выпал из `sudo` | С другой админской учётки или из recovery mode: `usermod -aG sudo user`. Всегда писать `-aG` |
| 2 | Пользователя добавили в группу, а доступа нет | Группы назначаются процессу при старте сессии/службы | Перелогиниться (`newgrp`), для службы — `systemctl restart`; проверить `grep Groups /proc/<pid>/status` |
| 3 | `sudo -u postgres psql`: `could not change directory to "/home/admin": Permission denied` | Текущий каталог недоступен `postgres` (домашние каталоги `0750`) | Безвредно; `cd /tmp` перед командой или `sudo -iu postgres` |
| 4 | `pg_restore`/`psql -f /home/admin/x.dump`: `Permission denied` | То же: `postgres` не может войти в чужой домашний каталог | Положить файл в `/srv/...` или `/var/tmp`; либо подать через stdin: `sudo -u postgres psql base < /home/admin/x.sql` (файл открывает оболочка администратора) |
| 5 | PostgreSQL не стартует: `data directory ... has invalid permissions` | На каталог данных выставлены права шире `0700`/`0750` (часто после `chmod -R 755`) | `chmod 700 <каталог данных>` (или 750 при групповом доступе), владелец `postgres` |
| 6 | PostgreSQL не стартует: `... has wrong ownership` | Каталог данных скопирован/восстановлен от root | `chown -R postgres:postgres <каталог данных>` |
| 7 | 1С: ошибка записи/чтения файла в каталоге обмена на сервере | У `usr1cv8` нет прав на каталог или нет `x` на родительских каталогах | `namei -l`, `sudo -u usr1cv8 test -w`, сценарий 15.1 |
| 8 | Файлы, созданные сервером 1С, недоступны на запись другим участникам группы | `UMask=0022` службы → файлы `644` | Default-ACL на каталоге (`setfacl -d -m g::rwx`) или `UMask=0007` в drop-in юнита |
| 9 | ACL выдан, `getfacl` показывает `#effective:r-x` | Маску урезал `chmod g-w`/`chmod 750` | `setfacl -m m::rwx путь`; не делать `chmod` поверх ACL без проверки |
| 10 | Файл не изменяется и не удаляется даже от root: `Operation not permitted` | Атрибут `i` или `a` | `lsattr`, затем `chattr -i` / `chattr -a` |
| 11 | Правило из `/etc/sudoers.d/admins.conf` не действует | Файлы с точкой в имени или `~` на конце пропускаются | Переименовать без точки: `/etc/sudoers.d/90-admins`; права `0440` |
| 12 | После правки sudoers: `sudo: parse error ...`, sudo не работает ни у кого | Файл правили не через `visudo` | `pkexec visudo` (если есть polkit) или recovery mode; впредь только `visudo` и `visudo -c` |
| 13 | `sudo echo text > /etc/file` → `Permission denied` | Перенаправление выполняет оболочка пользователя, а не sudo | `echo text \| sudo tee /etc/file` или `sudo sh -c 'echo text > /etc/file'` |
| 14 | Лимит из `limits.conf` не применился к серверу 1С/PostgreSQL | `pam_limits` действует только на PAM-сессии, не на службы systemd | `LimitNOFILE=` и т.п. в drop-in юнита; проверка `cat /proc/<pid>/limits` |
| 15 | SSH-ключ не принимается, сервер просит пароль | Права на `~`, `~/.ssh` или `authorized_keys` допускают запись группе/остальным, либо владелец не тот | `chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys; chmod g-w,o-w ~`; `chown -R user:user ~/.ssh`; смотреть `journalctl -u ssh` |
| 16 | Учётку заблокировали `passwd -l`, а пользователь продолжает входить | Заблокирован только пароль, SSH-ключ действует | `usermod -L -e 1 user` + убрать `authorized_keys` + `loginctl terminate-user user` |
| 17 | `sudo -iu www-data` → `This account is currently not available.` | Оболочка учётки — `nologin` | `sudo -u www-data bash` или `sudo su -s /bin/bash - www-data` |
| 18 | `psql -U postgres` → `Peer authentication failed for user "postgres"` | Метод `peer`: имя пользователя ОС должно совпадать с ролью | Запускать как `sudo -u postgres psql` либо подключаться по TCP с паролем: `psql -h 127.0.0.1 -U postgres` |
| 19 | После обновления до 26.04 правило sudoers с `*` в аргументах даёт ошибку или не срабатывает | sudo-rs не поддерживает шаблоны внутри аргументов | Перечислить команды полностью или переключиться на `sudo.ws` |
| 20 | В 26.04 не пишется `/var/log/sudo.log`, нет `sudoreplay` | sudo-rs журналирует только в syslog | `journalctl -t sudo`; при необходимости `update-alternatives --set sudo /usr/bin/sudo.ws` |
| 21 | Скрипты expect/Ansible-обвязки «зависают» на sudo в 26.04 | Другой текст приглашения пароля у sudo-rs | `sudo -S`, `--prompt ""` либо правило `NOPASSWD` для автоматизации |
| 22 | В 26.04 `lastlog: command not found` | Утилита заменена на `lastlog2`, `last` — из `wtmpdb` | Использовать `lastlog2`, `last`/`wtmpdb last` |
| 23 | После `chmod -R 777` перестали работать ssh/PostgreSQL/sudo | Эти программы проверяют, что права **не шире** допустимых | Вернуть: PGDATA `700`, `~/.ssh` `700`, `authorized_keys` `600`, `/etc/sudoers` `440`, `/etc/sudoers.d/*` `440` |
| 24 | Веб-публикация 1С: Apache отдаёт 403/500, в error.log — отказ в доступе | `www-data` не может прочитать `default.vrd`, каталог публикации или файлы платформы; либо файл искали в общем `/tmp` при `PrivateTmp=true` | `sudo -u www-data test -r ...`, `namei -l`, не использовать `/tmp` для обмена с Apache |
| 25 | Технологический журнал 1С не создаётся | У `usr1cv8` нет записи в каталог журнала или `logcfg.xml` ему не читается | Раздел 7.3; `sudo -u usr1cv8 test -w /var/log/1c/logs`, `sudo -u usr1cv8 cat .../conf/logcfg.xml` |
| 26 | Файлы, загруженные администратором через WinSCP, сервер 1С не может изменить | Владелец — администратор, права `644` | Каталог с SGID и default-ACL (15.1Б) либо `chown usr1cv8:grp1cv8 файл` |
| 27 | `chown`/`chmod`/`setfacl` на подключённой сетевой папке не дают эффекта | CIFS/vboxsf: права задаются опциями монтирования | `uid=,gid=,file_mode=,dir_mode=` в fstab; `findmnt -T` |
| 28 | После удаления пользователя его файлы «достались» новому пользователю | UID освободился и был выдан повторно | Перед удалением: `find / -xdev -user ИМЯ`; после — `find / -xdev -nouser`; архивировать/перевладеть |
| 29 | Сервисная учётка перестала запускать cron/su: `Your account has expired` или требование сменить пароль | На учётку распространили политику сроков (`chage -M`, `-E`) | `chage -E -1 -M -1 -I -1 postgres` (и аналогично для `usr1cv8`) |
| 30 | `The account is locked due to N failed logins` | Сработал `pam_faillock` | `faillock --user ИМЯ --reset`; пересмотреть `deny`/`unlock_time` |
| 31 | Из консоли под `usr1cv8` файл доступен, а служба 1С получает отказ | Ограничения юнита (`ProtectHome`, `ReadOnlyPaths`), устаревшие группы процесса или AppArmor | Шаги 1, 7, 8 раздела 14.2 |
| 32 | `usermod: user usr1cv8 is currently used by process ...` | Меняете UID/логин/домашний каталог при работающей службе | Остановить службу, выполнить `usermod`, запустить |
| 33 | Каталог с SGID: после `chmod 770` бит SGID остался (или наоборот, ждали, что он появится) | Числовой режим из 3–4 цифр не трогает SUID/SGID каталога | Явно: `chmod g+s` / `chmod g-s` или `chmod 2770` / `chmod 00770` |
| 34 | `sudo -l` у пользователя показывает правило, но команда всё равно просит пароль или запрещена | Сработало более позднее правило (действует последнее совпадение), либо путь к команде отличается (`/bin/systemctl` против `/usr/bin/systemctl`) | Проверить порядок файлов в `/etc/sudoers.d` и `command -v systemctl`; `sudo -ll` показывает правила подробно |
| 35 | Скрипт с `adduser --comment …` падает на Ubuntu 22.04 (или скрипт с `--gecos` перестаёт работать на новых выпусках) | В adduser 3.118 (22.04) есть только `--gecos`; `--comment` появилась позже, а `--gecos` объявлена устаревшей («will be removed after Debian bookworm» — ⚠ не подтверждено, принимается ли она ещё в 26.04) | Для переносимости — `useradd -c` либо ветвление по версии `dpkg-query -W adduser`; так же различаются `--add_extra_groups`/`--add-extra-groups` и `--force-badname`/`--allow-bad-names` |
| 36 | На 22.04 `adduser --system svc` неожиданно создал `/home/svc`, а на 24.04 дом — `/nonexistent` | Поведение `--system` изменилось между adduser 3.118 и 3.137 | Всегда указывать `--home КАТАЛОГ` или `--no-create-home` явно |
| 37 | `usermod -rG группа user` на 22.04 завершается ошибкой о неизвестном ключе | Ключ `-r`/`--remove` появился в shadow после 4.8.1 (в man jammy его нет, в noble и resolute есть) | `sudo gpasswd -d user группа` или `sudo deluser user группа` |
| 38 | В 26.04 `sudo -E команда` не передаёт переменные (`http_proxy`, `PGPASSWORD` и т.п.) | sudo-rs не сохраняет окружение целиком; флаг игнорируется или отвергается | `sudo --preserve-env=VAR1,VAR2 команда` (нужен тег `SETENV:` или правило `ALL`) либо `Defaults env_keep += "VAR1 VAR2"` |
| 39 | После `sudo sed -i …`/`sudo cp …` по `pg_hba.conf` PostgreSQL при `reload` пишет в журнал, что не может открыть файл | Файл пересоздан и принадлежит `root:root`, а должен быть `postgres:postgres 0640` | `sudo chown postgres:postgres /etc/postgresql/NN/main/pg_hba.conf && sudo chmod 640 …`; править через `sudoedit` или `sudo -u postgres nano` |
| 40 | Сервер 1С «не видит» программную лицензию, хотя файл `*.lic` лежит в `/var/1C/licenses` | Файл создан другой учётной записью и недоступен `usr1cv8`, либо каталог не `root:grp1cv8 775` | `sudo -u usr1cv8 ls -l /var/1C/licenses`; `sudo chgrp grp1cv8 /var/1C/licenses/*.lic && sudo chmod g+rw /var/1C/licenses/*.lic` — по документации 8.3.27 (сверено 10.10.2026) каталог принадлежит `root`, группа `grp1cv8`, права `rwxrwxr-x`, членам группы нужен доступ на запись к файлам лицензий; ранее отмечалось: эталонные права не подтверждены ИТС |
| 41 | После обновления платформы 1С пропал технологический журнал | `logcfg.xml` лежал в каталоге `conf` старой версии (`/opt/1cv8/x86_64/<старая версия>/conf`) | Перенести `logcfg.xml` в `conf` новой версии (создать каталог, если его нет), права на чтение для `usr1cv8` |
| 42 | В 26.04 `last`/`lastlog2` показывают пустой список | PAM-модули `pam_wtmpdb`/`pam_lastlog2` не подключены или пакеты не установлены | `dpkg -l wtmpdb libpam-wtmpdb lastlog2 libpam-lastlog2`, `grep -rE 'pam_(wtmpdb|lastlog2)' /etc/pam.d/`; история до обновления — `wtmpdb import -f /var/log/wtmp`, `lastlog2 -i /var/log/lastlog` |
| 43 | После включения `pam_faillock` по STIG перестали применяться capabilities из `/etc/security/capability.conf` | `authsucc` с `sufficient` завершает стек до блока «Additional» (`pam_cap.so`) | Использовать раскладку через профили `pam-auth-update` (раздел 12.4, вариант Б): сброс счётчика выполняет `account required pam_faillock.so`, строка `authsucc` не нужна |

---

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Сведения об учётной записи | `id usr1cv8` ; `getent passwd usr1cv8` |
| Кто в группе | `getent group sudo` |
| Создать администратора | `sudo adduser ivanov && sudo usermod -aG sudo ivanov` |
| Создать системную учётку со своей группой | `sudo adduser --system --group --home /srv/svc svc` |
| Создать учётку и группу 1С вручную | `sudo groupadd -r grp1cv8 && sudo useradd -r -g grp1cv8 -d /home/usr1cv8 -m -s /bin/bash usr1cv8` |
| Добавить в группу / убрать из группы | `sudo usermod -aG grp user` / `sudo gpasswd -d user grp` |
| Создать / удалить группу | `sudo groupadd grp` / `sudo groupdel grp` |
| Удалить пользователя с домашним каталогом | `sudo deluser --remove-home user` |
| Сменить оболочку / запретить вход | `sudo usermod -s /bin/bash user` / `sudo usermod -s /usr/sbin/nologin user` |
| Задать пароль / статус пароля | `sudo passwd user` / `sudo passwd -S user` |
| Заблокировать пароль / учётку целиком | `sudo passwd -l user` / `sudo usermod -L -e 1 user` |
| Разблокировать | `sudo usermod -U -e "" user` |
| Сроки пароля | `sudo chage -l user` ; `sudo chage -M 90 -W 14 user` |
| Сменить пароль при следующем входе | `sudo chage -d 0 user` |
| Кто в системе / история входов | `w` ; `last -n 20` ; `lastlog` (26.04: `lastlog2`) |
| Сессии systemd / выгнать пользователя | `loginctl list-sessions` / `sudo loginctl terminate-user user` |
| Оболочка postgres | `sudo -iu postgres` |
| Команда от имени postgres / usr1cv8 / www-data | `sudo -u postgres psql` ; `sudo -u usr1cv8 -s` ; `sudo -u www-data bash` |
| Оболочка для учётки с nologin | `sudo su -s /bin/bash - www-data` |
| Права на файл / каталог | `chmod 640 f` ; `chmod 750 d` |
| Рекурсивно, не делая файлы исполняемыми | `chmod -R u=rwX,g=rX,o= d` |
| Раздельно каталоги и файлы | `find d -type d -exec chmod 750 {} +` ; `find d -type f -exec chmod 640 {} +` |
| Сменить владельца и группу | `sudo chown -R usr1cv8:grp1cv8 d` |
| Создать каталог с владельцем и правами | `sudo install -d -o usr1cv8 -g grp1cv8 -m 0750 d` |
| Общий каталог группы | `sudo chmod 2770 d && sudo setfacl -d -m u::rwx,g::rwx,o::--- d` |
| Показать режим цифрами | `stat -c '%A %a %U:%G %n' путь` |
| Текущая / новая umask | `umask` / `umask 027` |
| ACL: показать | `getfacl -e путь` |
| ACL: дать доступ пользователю | `sudo setfacl -R -m u:usr1cv8:rwX d` |
| ACL: наследование | `sudo setfacl -R -d -m u:usr1cv8:rwX d` |
| ACL: убрать запись / всё | `sudo setfacl -x u:user путь` / `sudo setfacl -b путь` |
| ACL: резервная копия / восстановление | `getfacl -R d > acl.txt` / `setfacl --restore=acl.txt` |
| Атрибуты: показать / заморозить / снять | `lsattr f` / `sudo chattr +i f` / `sudo chattr -i f` |
| Что мне разрешено в sudo | `sudo -l` (для другого: `sudo -l -U user`) |
| Править правила sudo | `sudo visudo -f /etc/sudoers.d/90-local` ; `sudo visudo -c` |
| sudo без пароля для пользователя | строка `user ALL=(ALL:ALL) NOPASSWD: ALL` в `/etc/sudoers.d/90-local` |
| Сбросить кэш пароля sudo | `sudo -k` |
| Журнал sudo | `sudo journalctl -t sudo --since today` ; `grep sudo /var/log/auth.log` |
| Какая реализация sudo (26.04) | `sudo --version` ; `update-alternatives --display sudo` |
| Запись в файл root | `echo строка \| sudo tee -a /etc/файл` |
| Лимиты сессии / процесса | `ulimit -a` / `cat /proc/<pid>/limits` |
| Лимит службы | `sudo systemctl edit ЮНИТ` → `[Service]` `LimitNOFILE=65536` |
| Сложность паролей | `sudo apt install libpam-pwquality` ; `/etc/security/pwquality.conf` |
| Счётчики faillock / сброс | `sudo faillock --user user` / `sudo faillock --user user --reset` |
| Права для SSH-ключей | `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` |
| Проверить и применить sshd | `sudo sshd -t && sudo systemctl restart ssh` |
| Права по цепочке каталогов | `namei -l /полный/путь/к/файлу` |
| Проверить доступ от имени службы | `sudo -u usr1cv8 test -w /путь && echo OK` |
| От кого работает процесс и его группы | `ps -o user,group,supgrp,cmd -C rphost` ; `grep Groups /proc/<pid>/status` |
| Опции монтирования для пути | `findmnt -T /путь` |
| Отказы AppArmor | `sudo dmesg \| grep 'apparmor="DENIED"'` ; `sudo aa-status` |
| Найти SUID-файлы | `sudo find / -xdev -type f -perm -4000` |
| Найти «бесхозные» файлы | `sudo find / -xdev \( -nouser -o -nogroup \)` |
| Починить права каталога данных PostgreSQL | `sudo chown -R postgres:postgres PGDATA && sudo chmod 700 PGDATA` |

---

## Источники

Официальная документация и man-страницы:

- https://ubuntu.com/server/docs/how-to/security/user-management/ — Ubuntu Server «User management»: root без пароля, группа `sudo`, диапазоны UID, `adduser`/`deluser`, права домашних каталогов `0750` и `DIR_MODE`, политика паролей по умолчанию, `chage`, замечание о SSH-ключах при блокировке пароля, переключение `sudo-rs`/`sudo.ws`.
- https://ubuntu.com/server/docs/_sources/reference/other-tools/sudo-rs.md.txt — Ubuntu Server, справка по sudo-rs: отличие приглашения пароля, отсутствие I/O-журналов и `sudoreplay`, отсутствие `sudoers.ldap`, `man sudoers-rs`.
- https://documentation.ubuntu.com/release-notes/26.04/ и https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — дата выпуска 26.04, sudo-rs по умолчанию, rust-coreutils, OpenSSH 10.2p1, PostgreSQL 18, ядро 7.0, systemd 259, новые профили AppArmor.
- https://cdn.jsdelivr.net/gh/trifectatechfoundation/sudo-rs@main/README.md и https://raw.githubusercontent.com/trifectatechfoundation/sudo-rs/main/docs/man/sudoers.5.md — sudo-rs: отличия от классического sudo (pwfeedback, logfile, шаблоны в аргументах, `sudo -E`, почта, UTF-8), значения Defaults по умолчанию, версия в Ubuntu 26.04 (0.2.13).
- https://manpages.ubuntu.com/manpages/noble/en/man5/sudoers.5.html и .../man8/visudo.8.html — синтаксис sudoers, теги, псевдонимы, правила `@includedir`, значения `timestamp_timeout` (15), `passwd_tries` (3), syslog `authpriv`, `iolog_dir`, порядок «последнее совпадение», поведение `visudo`.
- https://manpages.ubuntu.com/manpages/noble/en/man8/adduser.8.html и https://manpages.ubuntu.com/manpages/resolute/en/man8/adduser.8.html — формы вызова и ключи `adduser`, поведение `--system` (nologin, `/nonexistent`, `nogroup`), версии 3.137ubuntu1 / 3.153ubuntu1.
- https://manpages.ubuntu.com/manpages/noble/en/man8/useradd.8.html , .../man8/usermod.8.html , .../man1/passwd.1.html , .../man1/chage.1.html , .../man5/login.defs.5.html — ключи `useradd`/`usermod`/`passwd`/`chage`, рекомендации по полной блокировке (`--expiredate 1`), параметры `login.defs`.
- https://manpages.ubuntu.com/manpages/resolute/en/man8/lastlog2.8.html и https://manpages.ubuntu.com/manpages/resolute/en/man1/last.1.html — `lastlog2` (util-linux 2.41.3) и `last` из wtmpdb в Ubuntu 26.04.
- https://manpages.ubuntu.com/manpages/noble/en/man1/loginctl.1.html — команды `loginctl`, `enable-linger`.
- https://manpages.ubuntu.com/manpages/noble/en/man1/su.1.html — ключи `su`, поведение `-`/`-s`, файлы конфигурации.
- https://manpages.ubuntu.com/manpages/noble/en/man1/setfacl.1.html — ключи `setfacl`, формат записей, пересчёт маски, `--restore`.
- https://manpages.ubuntu.com/manpages/noble/en/man1/chattr.1.html — атрибуты, `CAP_LINUX_IMMUTABLE`.
- https://manpages.ubuntu.com/manpages/noble/en/man1/namei.1.html — ключи `namei`.
- https://www.gnu.org/software/coreutils/manual/html_node/Directory-Setuid-and-Setgid.html — поведение `chmod` в отношении SUID/SGID каталогов.
- https://manpages.ubuntu.com/manpages/noble/en/man8/pam_umask.8.html — откуда берётся umask, опция `usergroups`.
- https://manpages.ubuntu.com/manpages/noble/en/man5/limits.conf.5.html — формат `limits.conf`.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.exec.5.html — `LimitNOFILE=` и другие лимиты служб, `UMask=` (0022 по умолчанию), `User=`/`Group=`.
- https://manpages.ubuntu.com/manpages/noble/en/man5/pwquality.conf.5.html и .../man8/pam_pwquality.8.html — параметры и значения по умолчанию `pam_pwquality`.
- https://manpages.ubuntu.com/manpages/noble/en/man5/faillock.conf.5.html , .../man8/pam_faillock.8.html , .../man8/faillock.8.html — параметры `pam_faillock`, каталог счётчиков, утилита `faillock`.
- https://manpages.ubuntu.com/manpages/noble/en/man8/pam-auth-update.8.html — профили PAM, `--enable/--disable/--force`.
- https://www.stigviewer.com/stigs/canonical_ubuntu_2404_lts/2026-05-14/finding/V-270690 — DISA STIG для Ubuntu 24.04: строки `pam_faillock` в `common-auth`.
- https://manpages.ubuntu.com/manpages/noble/en/man8/sshd.8.html и https://ubuntu.com/server/docs/how-to/security/openssh-server/ — права на `~/.ssh` и `authorized_keys`, StrictModes, опции `authorized_keys`, `sshd_config.d`, `sshd -t`.
- https://ubuntu.com/server/docs/how-to/security/apparmor/ — команды AppArmor, каталоги профилей, формат записи `DENIED`, локальные дополнения.
- https://www.postgresql.org/docs/current/creating-cluster.html и https://www.postgresql.org/docs/current/app-initdb.html — права каталога данных (0700/0750, файлы 0600/0640), `--allow-group-access`, запрет запуска от root, рекомендации по точке монтирования; текущая версия документации — PostgreSQL 18.
- https://salsa.debian.org/postgresql/postgresql-common/ (файлы `debian/postgresql-common.postinst` тегов `debian/238`, `debian/257`; `debian/postgresql-common.sysusers`, `debian/postgresql-common.tmpfiles` ветки master) — как создаётся пользователь `postgres`, права `/var/log/postgresql`, `/run/postgresql`, `/var/lib/postgresql`, `/etc/postgresql`.
- https://manpages.ubuntu.com/manpages/noble/en/man1/pg_createcluster.1.html — владелец кластера, каталоги по умолчанию, группа `ssl-cert`.
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux — Postgres Pro: пользователь `postgres`, `/var/lib/pgpro/std-17/data`, `/opt/pgpro/std-17`, `pg-setup`.
- https://its.1c.ru/db/metod8dev/content/5953/hdoc (текст: https://its.1c.ru/db/content/metod8dev/src/developers/scalability/instructions/i8105953.htm ) — ИТС «Установка Платформы 1С:Предприятие в ОС Linux» (для 8.3.13): `chown -R usr1cv8 /cluster_data`, группа `grp1clogs` для техжурнала, путь `/home/usr1cv8/.1cv8/1C/1cv8`, переменная `SRV1CV8_DATA`. Страница прочитана частично (кириллица в выдаче искажена, команды читаемы).
- https://kb.1ci.com/1C_Enterprise_Platform/FAQ/Administration/Server/Specifics_of_1C_Enteprise_server_administration_on_Linux — особенности администрирования сервера 1С в Linux: keytab (`chown`, `chmod 600`), домашний каталог пользователя сервера, старые имена `usr1cv81`/`usr1cv82`.

Дополнительно использовано при проверке фактов 2026-10-10 (рецензент):

- https://manpages.ubuntu.com/manpages/jammy/en/man8/adduser.8.html — adduser 3.118ubuntu5 (22.04): только `--gecos`, `--force-badname`, `--add_extra_groups`; системной учётке дом создаётся «by the same rules as for normal users».
- https://manpages.ubuntu.com/manpages/noble/en/man5/adduser.conf.5.html — умолчания `adduser.conf` (Debian: `DIR_MODE` 0700, `SYS_DIR_MODE` 0755, `USERGROUPS` yes, `EXTRA_GROUPS` users, `NAME_REGEX`).
- https://manpages.ubuntu.com/manpages/jammy/en/man8/usermod.8.html , .../noble/... , .../resolute/... — версии shadow 4.8.1 / 4.13 / 4.17.4; ключ `-r/--remove` отсутствует в jammy.
- https://manpages.ubuntu.com/manpages/jammy/en/man8/sshd.8.html (OpenSSH 8.9p1), https://manpages.ubuntu.com/manpages/jammy/en/man1/loginctl.1.html (systemd 249.11), https://manpages.ubuntu.com/manpages/jammy/en/man1/su.1.html (util-linux 2.37.2), https://manpages.ubuntu.com/manpages/jammy/en/man8/pam_faillock.8.html (PAM 1.4.0), https://manpages.ubuntu.com/manpages/resolute/en/man8/pam_faillock.8.html (PAM 1.7.0) — версии компонентов по строке «Provided by».
- https://manpages.ubuntu.com/manpages/jammy/en/man5/sudoers.5.html — sudo 1.9.9: `passwd_timeout` 0, `timestamp_timeout` 15, `passwd_tries` 3, `use_pty` off по умолчанию; noble (1.9.15p5): `lecture` never, `use_pty` on с 1.9.14, `*` в аргументах «including white space», `""` — запрет аргументов.
- https://manpages.ubuntu.com/manpages/resolute/en/man8/sudo-rs.8.html — sudo-rs 0.2.13-0ubuntu1.2 в 26.04: перечень поддерживаемых ключей (нет `-E`, `-H` в документации).
- https://raw.githubusercontent.com/trifectatechfoundation/sudo-rs/main/src/sudo/pipeline.rs , .../src/sudo/cli/mod.rs , .../src/common/error.rs , .../docs/man/sudo.8.md — исходники sudo-rs: формат записи журнала о выполненной команде, обработка `-E`/`-H`/`-l -l`, тексты отказов. Ветка `main` может отличаться от 0.2.13 в мелочах.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/chmod.1.html — `chmod` из `rust-coreutils` 0.10.0 в 26.04.
- https://manpages.ubuntu.com/manpages/resolute/en/man8/pam_lastlog2.8.html и .../man8/pam_wtmpdb.8.html — пакеты `libpam-lastlog2`, `libpam-wtmpdb` (0.75.0), примеры строк PAM; https://www.debian.org/releases/trixie/release-notes/issues.en.html (п. 5.1.9) — замена `last`/`lastb`/`lastlog`, `lslogins --failed`.
- https://changelogs.ubuntu.com/changelogs/pool/main/s/shadow/shadow_4.13+dfsg1-4ubuntu3/changelog — «Set HOME_MODE=750 in login.defs to enable private home directories» (1:4.8.1-1ubuntu8, 21.04) и перенос правки в 22.04/24.04.
- https://changelogs.ubuntu.com/changelogs/pool/main/s/sudo/sudo_1.9.9-1ubuntu2/changelog — `use_pty` в штатном sudoers (1.9.6-1~exp2), `/snap/bin` в `secure_path`, группа `admin`, сборка `--without-lecture`, тайм-аут 15 минут, удаление `keep_home_by_default` (1.8.27-1ubuntu2).
- https://salsa.debian.org/vorlon/pam/-/raw/master/debian/pam-configs/unix — профиль `pam_unix`: `obscure … yescrypt` (умолчание хэширования).
- https://salsa.debian.org/debian/shadow/-/raw/master/debian/default/useradd — в `/etc/default/useradd` активна только `SHELL=/bin/sh`.
- https://salsa.debian.org/postgresql/postgresql-common/-/raw/master/pg_createcluster — режимы `postgresql.conf` (644), `pg_hba.conf`/`pg_ident.conf` (640), журнал `0640` с группой `adm`, каталог журналов `01775 root:postgres`.
- https://salsa.debian.org/postgresql/postgresql-common/-/raw/debian/257/debian/postgresql-common.postinst — создание `postgres` (`adduser --system … --gecos "PostgreSQL administrator"`), `ssl-cert`, права каталогов (сверено дословно).
- https://www.postgresql.org/support/versioning/ — PostgreSQL 18.6 текущая, 19 Beta 4 (24.09.2026), окончание поддержки 14 — 12.11.2026.
- https://repo.postgrespro.ru/1c/ и https://repo.postgrespro.ru/1c/1c-17/meta.json — сборка Postgres Pro для 1С: ветки 14–18, пакеты `postgrespro-1c-17*`, каталог `/opt/pgpro/1c-17`, поддерживаемые Ubuntu 22.04/24.04/25.10/26.04.
- https://discourse.ubuntu.com/t/private-home-directories-for-ubuntu-21-04-onwards/19533 — обсуждение перехода на домашние каталоги `0750` (не затрагивает существующие установки).
- Недоступно рецензенту (нужна подписка ИТС или авторизация): https://its.1c.ru/db/v8327doc/content/101/hdoc («Глава 2. Установка системы „1С:Предприятие“»), https://its.1c.ru/db/v8327doc/content/115/hdoc («Приложение 3. Описание и расположение служебных файлов»), документация 8.5.1/8.5.4, руководство администратора на support.1ci.com.

Практика сообщества:

- https://sysadminchik.ru/str/liversi_result.php?search_id=42 — установка сервера 1С 8.3.22 на Ubuntu из `setup-full-*.run`: «автоматически созданному пользователю usr1cv8», `chown -R usr1cv8:grp1cv8 /opt/1cv8`.
- https://almaz-sharipov.ru/article/linux-1c/1c-server — сервер 1С 8.3.22–8.3.25: ручное создание `/home/usr1cv8` при его отсутствии, юнит RAS с `User=usr1cv8`, `Group=grp1cv8`.
- https://mclouds.ru/2025/02/razvertyvanie-servera-1s-na-linuks-polnyj-gajd-na-primere-astra-linux/ — установка 8.3.26 без ручного создания пользователя, `systemctl link` юнита из `/opt/1cv8/x86_64/<версия>/`.
- https://rarus.ru/publications/20210927-ot-ekspertov-ustanovka-1c-linux-496320/ — несколько экземпляров сервера 1С: `SRV1CV8_DATA=/home/usr1cv8/.1cv8/...`, юниты с `User=usr1cv8`/`Group=grp1cv8`, права на ключи TLS.
- https://habr.com/ru/companies/first/articles/588028/ — доменная авторизация сервера 1С на Linux: `usr1cv8` как локальный пользователь сервера, права keytab.
- https://qna.habr.com/q/961553 — группа `grp1cv8` и права каталога лицензий (страница прочитана рецензентом: владелец `root` — rwx, группа `grp1cv8` — rwx, остальные — r-x; путь каталога в ответе не назван, команды не приведены).
- https://www.ssdnodes.com/learn/sudo-rs-on-ubuntu-what-changes — практические отличия sudo-rs (шаблоны в аргументах, `sudo -E`, `sudo.ws`).
- https://raw.githubusercontent.com/firstBitMarksistskaya/onec-docker/feature/first-bit/server/Dockerfile и .../scripts/install.sh — контейнерная сборка сервера 1С: `groupadd -r grp1cv8`, `useradd -r -g grp1cv8 --home-dir=/home/usr1cv8 --shell=/bin/bash usr1cv8`, `logcfg.xml` в `/opt/1cv8/current/conf` и `/home/usr1cv8/.1cv8/1C/1cv8/conf`, запуск установщика `--mode unattended --enable-components server,ws,…`.
- https://raw.githubusercontent.com/ansible-lockdown/UBUNTU22-CIS/devel/templates/usr/share/pam-configs/faillock.j2 и .../faillock_notify.j2 — профили `pam-auth-update` для `pam_faillock` по CIS Benchmark (раздел 12.4, вариант Б).

Замечания рецензента к источникам сообщества: статья sysadminchik.ru советует `chmod 777` на файл установщика и `chown -R usr1cv8:grp1cv8 /opt/1cv8` — оба приёма избыточны (достаточно `chmod +x`; владелец каталога платформы может оставаться `root`). В статье mclouds.ru каталог конфигурации назван `/opt/1C/v8.3/x86_64/conf/` при установке в `/opt/1cv8/…` — это путь старой раскладки, для 8.3.26 его нужно перепроверять. Статья rarus.ru (2021) помечена автором как устаревшая.

