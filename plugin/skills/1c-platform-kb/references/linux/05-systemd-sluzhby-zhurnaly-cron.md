# systemd: службы, юниты, журналы journalctl, logrotate, cron и таймеры

> Область: управление службами и автозапуском на Ubuntu Server (systemd), написание unit-файлов, юниты сервера 1С и PostgreSQL, журналы (journald, rsyslog, logrotate), планировщики (cron, anacron, at, systemd timers), загрузка/выключение, вспомогательные утилиты systemd | Версии: Ubuntu 22.04 LTS (systemd 249.11), 24.04 LTS (systemd 255.4), 26.04 LTS (systemd 259.5); платформа 1С 8.3.21–8.3.27 и 8.5.x; PostgreSQL 14/16/18 (пакеты Ubuntu/PGDG, `postgresql-common`) и Postgres Pro 1C | Актуальность: 2026-10-10

Условные обозначения: «⚠ не подтверждено» — утверждение не удалось проверить по первоисточнику в момент написания (перепроверьте на живой системе указанной командой). «Официально» — документация systemd/Canonical/1С/PGDG; «практика» — устоявшиеся приёмы сообщества.

**Статус проверки (рецензия 2026-10-10).** Часть про systemd, journald, cron, logrotate, rsyslog, PostgreSQL (`postgresql-common`) сверена с man-страницами Ubuntu 22.04/24.04/26.04, исходными текстами пакетов Debian и исходным кодом systemd 255. **Не удалось прочитать ни одного вендорского файла 1С** (`srv1cv8-<версия>@.service`, `ras-<версия>.service`) и закрытую документацию ИТС: всё, что касается точного текста этих юнитов, имён переменных `SRV1CV8_PING*`/`SRV1CV8_KEYTAB`, платформы 8.5 и поведения технологического журнала при посторонних файлах, остаётся помеченным «⚠» — перед любыми действиями на рабочем сервере смотрите `systemctl cat` своей версии. Ничего из статьи не проверялось на стенде: это сводка документации и практики, а не протокол испытаний.

---

## Кратко

1. **systemd — PID 1** во всех поддерживаемых Ubuntu. Всё, что запускается «как служба», описано unit-файлом. Версии: 22.04 → systemd 249, 24.04 → 255, 26.04 → 259 (опции отличаются: например, `systemctl edit --drop-in=` есть с 253, `--stdin` с 256, `journalctl -I` с 257).
2. **Запуск и автозапуск — разные вещи.** `start/stop` действуют сейчас, `enable/disable` — на следующую загрузку. Оба сразу: `systemctl enable --now ИМЯ`, `systemctl disable --now ИМЯ`.
3. **Где лежат юниты:** пакетные — `/usr/lib/systemd/system/` (не редактировать), свои и переопределения — `/etc/systemd/system/` (приоритет выше), временные — `/run/systemd/system/`.
4. **Не правьте вендорский unit-файл.** Делайте drop-in: `sudo systemctl edit ИМЯ` → создаётся `/etc/systemd/system/ИМЯ.service.d/override.conf`, `daemon-reload` выполняется автоматически. Посмотреть итог: `systemctl cat ИМЯ`.
5. После ручного изменения любых unit-файлов: `sudo systemctl daemon-reload` (перечитать юниты) — это НЕ то же самое, что `systemctl reload ИМЯ` (попросить саму службу перечитать её конфигурацию).
6. **Сервер 1С (8.3.21+)** поставляется с шаблонным юнитом `/opt/1cv8/x86_64/<версия>/srv1cv8-<версия>@.service`; его подключают так:
   `sudo systemctl link /opt/1cv8/x86_64/8.3.27.2325/srv1cv8-8.3.27.2325@.service && sudo systemctl enable --now srv1cv8-8.3.27.2325@default`.
   Сервер администрирования: `ras-<версия>.service` в том же каталоге (порт 1545).
7. **PostgreSQL из пакетов Ubuntu/PGDG:** реальный кластер — это `postgresql@<версия>-<кластер>.service` (например `postgresql@16-main`), а `postgresql.service` — «зонтик» (oneshot с `/bin/true`), который тянет все кластеры с `start.conf = auto`. Postgres Pro для 1С: `postgrespro-1c-<NN>.service`.
8. **Сервер 1С должен стартовать после СУБД и сети:** drop-in с `After=network-online.target postgresql.service` и `Wants=network-online.target postgresql.service`. `After=` задаёт только порядок, `Wants=/Requires=` — только «подтянуть»; почти всегда нужны оба.
9. **Журнал службы:** `journalctl -u ИМЯ -b -e` (текущая загрузка, в конец), «хвост» вживую: `journalctl -u ИМЯ -f`, только ошибки: `journalctl -p err -b`, за период: `--since "2026-10-10 08:00" --until "09:00"`.
10. **Размер журнала:** `journalctl --disk-usage`; подрезать: `sudo journalctl --vacuum-size=500M` или `--vacuum-time=14d`; постоянный лимит — `SystemMaxUse=` в `/etc/systemd/journald.conf.d/*.conf`.
11. **rsyslog** в Ubuntu по-прежнему ставится по умолчанию и пишет текстовые `/var/log/syslog`, `/var/log/auth.log`, `/var/log/kern.log`; journald пересылает ему сообщения (drop-in `/usr/lib/systemd/journald.conf.d/syslog.conf` c `ForwardToSyslog=yes`).
12. **logrotate** запускается раз в сутки таймером `logrotate.timer`; конфиги — `/etc/logrotate.conf` + `/etc/logrotate.d/*`. Проверка без изменений: `sudo logrotate -d /etc/logrotate.d/файл`; принудительно: `sudo logrotate -f /etc/logrotate.d/файл`.
13. **Технологический журнал 1С ротирует сама платформа** (атрибут `history` в `logcfg.xml`, в часах) — logrotate для него не нужен, а сжатие «на месте» внутри каталога ТЖ вредно.
14. **cron:** `crontab -e` (свой), `sudo crontab -u postgres -e` (чужой), системные задания — `/etc/crontab`, `/etc/cron.d/*` (там есть 6-е поле «пользователь»). Окружение cron минимальное (`SHELL=/bin/sh`, короткий `PATH`), символ `%` в команде надо экранировать `\%`.
15. **systemd-таймер** = пара `X.timer` + `X.service`. Включают таймер, а не службу: `systemctl enable --now X.timer`. Список: `systemctl list-timers --all`. Проверка расписания: `systemd-analyze calendar "Mon..Fri 02:30"`.
16. **Выключение/перезагрузка:** `sudo shutdown -r now`, `sudo shutdown -h +10 "сообщение"`, отмена `sudo shutdown -c`; `systemctl reboot|poweroff`. Цель по умолчанию: `systemctl get-default` / `set-default multi-user.target`.
17. **Почему долго грузится:** `systemd-analyze`, `systemd-analyze blame`, `systemd-analyze critical-chain ИМЯ.service`.
18. **Не запускается служба — порядок диагностики:** `systemctl status ИМЯ -l --no-pager` → `journalctl -u ИМЯ -b -e` → `systemctl cat ИМЯ` → `systemd-analyze verify /путь/к/unit` → после исправления `systemctl daemon-reload && systemctl reset-failed ИМЯ && systemctl start ИМЯ`.
19. **Ubuntu 26.04:** cgroup v1 удалён, `/tmp` — tmpfs по умолчанию (изменение появилось в 24.10, из LTS впервые в 26.04; важно для временных файлов сервера 1С — см. п. 14.1), служба времени по умолчанию — chrony, 26.04 — последний выпуск с совместимостью SysV-скриптов `/etc/init.d` в systemd.
20. Разовые/временные запуски с лимитами ресурсов — `systemd-run` (например `sudo systemd-run --unit=tmp-job -p MemoryMax=2G --uid=postgres КОМАНДА`).

---

## 1. Версии, компоненты и расположение файлов

### 1.1. Что какой версии

| Ubuntu | systemd | Ядро (GA) | PostgreSQL в архиве | Примечания по теме статьи |
|---|---|---|---|---|
| 22.04 LTS (jammy) | 249.11 | 5.15 | 14 | `systemctl kill --kill-who=` (старое имя опции), нет `edit --drop-in=`; man journald: по умолчанию пересылка в syslog и wall |
| 24.04 LTS (noble) | 255.4 | 6.8 | 16 | `--kill-whom=` (с 252), `edit --drop-in=` (253), `soft-reboot` (254), `Type=notify-reload` (253) |
| 26.04 LTS (resolute), вышел 23.04.2026 | 259.5 | 7.0 | 18 | `edit --stdin` (256), `run0` (256), `journalctl -I/--invocation` (257), `--kill-whom=cgroup`, cgroup v1 удалён, `/tmp` на tmpfs (изменение 24.10), chrony по умолчанию, `sudo` — это `sudo-rs`, последний LTS с поддержкой SysV-скриптов в systemd |

Узнать на месте:

```bash
systemctl --version          # первая строка: "systemd 255 (255.4-1ubuntu8.x)"
lsb_release -ds              # Ubuntu 24.04.x LTS
uname -r
```

Что из пакетов по теме стоит «из коробки» на Ubuntu Server (проверено по зависимостям метапакетов 26.04; в 22.04/24.04 состав тот же по сути):

| Компонент | Пакет | По умолчанию | Служба/таймер |
|---|---|---|---|
| systemd, journald, logind | `systemd` | да | `systemd-journald.service`, `systemd-logind.service` |
| rsyslog | `rsyslog` | да (Recommends у `ubuntu-minimal`) | `rsyslog.service` (алиас `syslog.service`) |
| cron | `cron` (Vixie cron 3.0pl1, ветка Debian) | да (`ubuntu-standard`) | `cron.service` |
| logrotate | `logrotate` | да (`ubuntu-standard`) | `logrotate.timer` → `logrotate.service` |
| anacron | `anacron` | нет | `anacron.timer` |
| at/batch | `at` | нет | `atd.service` |
| systemd-coredump / `coredumpctl` | `systemd-coredump` | нет (в Ubuntu дампы перехватывает `apport`) | `systemd-coredump.socket` |
| Синхронизация времени | 22.04/24.04: `systemd-timesyncd`; 26.04: `chrony` | да | `systemd-timesyncd.service` / `chrony.service` |

### 1.2. Каталоги unit-файлов и приоритет

Системные юниты ищутся в таком порядке (верхние перекрывают нижние с тем же именем файла):

| Приоритет | Каталог | Назначение |
|---|---|---|
| 1 | `/etc/systemd/system.control/`, `/run/systemd/system.control/` | то, что записал `systemctl set-property` |
| 2 | `/run/systemd/transient/` | временные юниты (`systemd-run`) |
| 3 | `/run/systemd/generator.early/` | генераторы (ранние) |
| 4 | **`/etc/systemd/system/`** | **юниты и переопределения администратора** |
| 5 | `/run/systemd/system/` | временные до перезагрузки (`--runtime`) |
| 6 | `/run/systemd/generator/` | генераторы (например, `postgresql-generator`, fstab) |
| 7 | `/usr/local/lib/systemd/system/` | локально собранное ПО |
| 8 | **`/usr/lib/systemd/system/`** | **юниты из пакетов** (`/lib/systemd/system` — тот же каталог, `/lib` → `/usr/lib`) |
| 9 | `/run/systemd/generator.late/` | генераторы (поздние, в т.ч. обёртки над `/etc/init.d/*`) |

Показать фактические пути: `systemd-analyze unit-paths`.

Прочие важные файлы:

| Файл/каталог | Что это |
|---|---|
| `/etc/systemd/system.conf`, `/etc/systemd/system.conf.d/*.conf` | настройки самого менеджера (значения по умолчанию для всех служб: `DefaultTimeoutStopSec`, `DefaultLimitNOFILE`, …) |
| `/etc/systemd/journald.conf`, `/etc/systemd/journald.conf.d/*.conf` | настройки журнала |
| `/etc/systemd/logind.conf` | сеансы пользователей (`RemoveIPC`, `KillUserProcesses`, …) |
| `/etc/systemd/system/*.wants/`, `*.requires/` | симлинки, которые создаёт `systemctl enable` |
| `/etc/systemd/system/ИМЯ.service.d/*.conf` | drop-in переопределения |
| `/var/log/journal/<machine-id>/` | постоянный журнал; `/run/log/journal/` — временный |
| `/var/lib/systemd/timers/stamp-*.timer` | отметки последнего срабатывания таймеров с `Persistent=true` |

### 1.3. Типы юнитов

`.service` (служба), `.socket` (сокет-активация), `.target` (группа/точка синхронизации), `.timer` (расписание), `.mount`/`.automount` (монтирование), `.path` (слежение за файлом), `.slice` (ветка cgroup для лимитов), `.scope` (группа внешне запущенных процессов), `.swap`, `.device`. Если суффикс не указан, `systemctl` подразумевает `.service`: `systemctl status cron` = `systemctl status cron.service`.

---

## 2. systemctl — управление службами

Общий синтаксис: `systemctl [ОПЦИИ] КОМАНДА [ЮНИТ...]`. Изменяющие команды требуют root (`sudo`). В именах допускаются shell-шаблоны, но они сопоставляются только с **загруженными в память** юнитами: `systemctl status 'postgresql@*'` (в кавычках, чтобы не раскрыл shell).

### 2.1. Запуск, остановка, перезапуск

| Команда | Что делает |
|---|---|
| `systemctl start ЮНИТ` | запустить (активировать) |
| `systemctl stop ЮНИТ` | остановить: `ExecStop=`, затем сигнал по `KillMode=`/`KillSignal=`, через `TimeoutStopSec=` — SIGKILL |
| `systemctl restart ЮНИТ` | остановить и запустить; если не был запущен — просто запустить |
| `systemctl try-restart ЮНИТ` | перезапустить **только если работает** (иначе ничего не делать) |
| `systemctl reload ЮНИТ` | попросить службу перечитать её собственную конфигурацию (`ExecReload=`); не у всех служб есть |
| `systemctl reload-or-restart ЮНИТ` | reload, если поддерживается, иначе restart |
| `systemctl try-reload-or-restart ЮНИТ` | то же, но только если работает |
| `systemctl kill ЮНИТ` | послать сигнал процессам юнита (см. ниже) |
| `systemctl reset-failed [ЮНИТ]` | сбросить состояние `failed`, счётчик лимита запусков и счётчик рестартов |

Примеры:

```bash
sudo systemctl restart postgresql@16-main          # перезапуск конкретного кластера PostgreSQL
sudo systemctl reload postgresql@16-main           # перечитать postgresql.conf/pg_hba.conf без разрыва сессий
sudo systemctl try-restart 'srv1cv8-*'             # перезапустить запущенные экземпляры сервера 1С, если они есть
sudo systemctl restart ssh --no-block              # поставить задание в очередь и не ждать завершения
```

Полезные опции: `--no-block` (не ждать), `--wait` (ждать завершения юнита, для `start`/`restart`), `--no-pager`, `-l`/`--full` (не обрезать строки), `-n N` (сколько строк журнала показать в `status`), `-q` (тихо), `-H user@host` (выполнить на удалённой машине по SSH), `--user` (менеджер пользователя вместо системного).

`systemctl kill`:

```bash
sudo systemctl kill -s SIGHUP rsyslog                    # сигнал всем процессам юнита (по умолчанию --kill-whom=all, сигнал SIGTERM)
sudo systemctl kill --kill-whom=main -s SIGKILL ИМЯ      # только главному процессу; в 22.04 опция называется --kill-who=
```

`--kill-whom=` принимает `main`, `control`, `all` (в systemd 259 ещё `cgroup`). В отличие от `kill PID`, не нужно искать PID и нельзя промахнуться мимо дочерних процессов.

### 2.2. Автозапуск: enable / disable / mask

| Команда | Что делает |
|---|---|
| `systemctl enable ЮНИТ` | создать симлинки по секции `[Install]` (обычно в `/etc/systemd/system/multi-user.target.wants/`); **не запускает** |
| `systemctl enable --now ЮНИТ` | включить автозапуск и сразу запустить |
| `systemctl disable ЮНИТ` | удалить симлинки; **не останавливает**. По man отменяет и `systemctl link` («removes all symlinks to the unit files backing the specified units… undoes any changes made by enable or link»). Нюанс для шаблонов: при `disable имя@экземпляр` удаляется симлинк автозапуска экземпляра, а симлинк самого шаблона, созданный `link`, судя по исходному коду systemd 255, остаётся; чтобы убрать и его — `disable имя@.service` (по имени шаблона). Подробности — п. 4.2 |
| `systemctl disable --now ЮНИТ` | отключить автозапуск и остановить |
| `systemctl reenable ЮНИТ` | disable + enable (пересоздать симлинки после правки `[Install]`) |
| `systemctl mask ЮНИТ` | «заглушить»: симлинк `/etc/systemd/system/ЮНИТ → /dev/null`; юнит нельзя запустить ни вручную, ни по зависимости. `--now` — ещё и остановить, `--runtime` — до перезагрузки |
| `systemctl unmask ЮНИТ` | снять заглушку |
| `systemctl preset ЮНИТ` | привести к политике дистрибутива (preset-файлы) |

```bash
sudo systemctl enable --now cron
sudo systemctl disable --now apport.service          # пример: отключить службу
sudo systemctl mask --now systemd-oomd.service       # гарантированно запретить запуск
systemctl is-enabled cron                            # enabled
```

Значения `systemctl is-enabled`:

| Вывод | Смысл | Код возврата |
|---|---|---|
| `enabled`, `enabled-runtime` | включён (постоянно / до перезагрузки) | 0 |
| `static` | нет секции `[Install]` — включить нельзя, запускается только по зависимости/вручную | 0 |
| `indirect` | сам не включён, но включён связанный юнит (`Also=`) или другой экземпляр шаблона, не тот что в `DefaultInstance=` | 0 |
| `alias` | имя — псевдоним другого юнита | 0 |
| `generated` | создан генератором (fstab, SysV-скрипт, `postgresql-generator`) | 0 |
| `transient` | временный (`systemd-run`) | 0 |
| `linked`, `linked-runtime` | файл подключён симлинком извне путей поиска (`systemctl link`), но не включён | >0 |
| `disabled` | выключен | >0 |
| `masked`, `masked-runtime` | заглушён | >0 |
| `bad` | файл юнита некорректен | >0 |
| `not-found` | юнита нет | 4 |

### 2.3. Состояние: status, is-active, is-failed, show, cat

```bash
systemctl status postgresql@16-main          # состояние, PID, cgroup-дерево, память/CPU, последние 10 строк журнала
systemctl status -l --no-pager -n 50 ИМЯ     # 50 строк журнала, без обрезки и пейджера
systemctl is-active ИМЯ                      # active | inactive | failed | activating | deactivating ; код 0 только если active
systemctl is-failed ИМЯ                      # код 0, если юнит в состоянии failed
systemctl is-failed                          # без аргументов: есть ли вообще сбойные юниты
systemctl is-system-running                  # running | degraded | starting | maintenance | ...
systemctl --failed                           # = systemctl list-units --state=failed
systemctl status 12345                       # аргумент-число = PID: показать юнит, которому принадлежит процесс
systemctl status "$(pgrep -o rphost)"        # к какому юниту (экземпляру сервера 1С) относится старейший rphost
```

Как читать `systemctl status`:

- строка `Loaded:` — путь к файлу юнита, состояние автозапуска (`enabled`/`disabled`/`static`/…) и `preset:`; значения `loaded`, `not-found`, `bad-setting`, `error`, `masked`;
- строка `Drop-In:` — какие каталоги `.d` и файлы `*.conf` применены (важно при отладке переопределений);
- строка `Active:` — `active (running)`, `active (exited)` (типично для oneshot с `RemainAfterExit=yes`, например `postgresql.service`), `inactive (dead)`, `failed (Result: exit-code|signal|timeout|oom-kill|start-limit-hit|…)`, `activating (auto-restart)`;
- `Main PID:`, `Tasks:`, `Memory:` (текущая память cgroup, в новых версиях ещё peak/swap), `CPU:`, `CGroup:` — дерево всех процессов службы (у сервера 1С здесь видны `ragent`, `rmngr`, все `rphost`).

Коды возврата `systemctl status` (LSB): 0 — активен, 3 — не запущен, 4 — нет такого юнита. Удобно в скриптах:

```bash
if systemctl is-active --quiet postgresql@16-main; then echo "PG работает"; fi
```

Свойства в машинном виде:

```bash
systemctl show ИМЯ                                        # все свойства Key=Value
systemctl show -p MainPID -p ActiveState -p SubState ИМЯ
systemctl show -p MainPID --value postgresql@16-main      # только значение
systemctl show -p LimitNOFILE -p LimitNOFILESoft -p MemoryMax -p TasksMax -p OOMPolicy 'srv1cv8-8.3.27.2325@default'
systemctl show -p NRestarts -p ExecMainStatus -p Result ИМЯ   # сколько раз перезапускалась и чем закончилась
```

Исходный текст юнита со всеми drop-in (каждый фрагмент с комментарием-путём):

```bash
systemctl cat postgresql@16-main
systemctl cat 'srv1cv8-8.3.27.2325@default'
```

`systemctl cat` показывает файлы **с диска**; если после правки не делали `daemon-reload`, работающая конфигурация может отличаться (systemctl предупредит: «Warning: … changed on disk. Run 'systemctl daemon-reload'»).

### 2.4. Списки: list-units, list-unit-files, list-dependencies, list-timers

```bash
systemctl list-units --type=service                        # загруженные службы (активные)
systemctl list-units --type=service --state=running        # только работающие
systemctl list-units --type=service --all                  # включая неактивные
systemctl list-units --state=failed                        # сбойные
systemctl list-unit-files --type=service                   # все УСТАНОВЛЕННЫЕ файлы юнитов и их автозапуск (включая шаблоны)
systemctl list-unit-files --type=service --state=enabled   # что включено в автозапуск
systemctl list-unit-files 'srv1cv8*' 'ras-*' 'postgresql*'
systemctl list-dependencies ИМЯ                            # что юнит тянет за собой (Requires/Wants/…)
systemctl list-dependencies --reverse ИМЯ                  # кто зависит от юнита
systemctl list-dependencies --after ИМЯ                    # после каких юнитов он стартует (порядок)
systemctl list-dependencies --before ИМЯ                   # перед какими
systemctl list-timers --all                                # таймеры: NEXT, LEFT, LAST, PASSED, UNIT, ACTIVATES
systemctl list-sockets                                     # слушающие сокеты и кого они активируют
systemctl list-jobs                                        # задания в очереди (полезно, когда «всё зависло при загрузке»)
```

Колонки `list-units`: `LOAD` (загружено ли определение: `loaded`/`not-found`/`masked`/`error`), `ACTIVE` (обобщённое состояние: `active`/`inactive`/`failed`/`activating`), `SUB` (детальное, зависит от типа: `running`, `exited`, `dead`, `waiting`, `listening`, `mounted`…). Разница: `list-units` — то, что сейчас в памяти менеджера; `list-unit-files` — то, что лежит на диске (шаблон `name@.service` без экземпляров виден только здесь).

### 2.5. Правка и перечитывание: edit, daemon-reload, revert, set-property

```bash
sudo systemctl edit ИМЯ                 # drop-in /etc/systemd/system/ИМЯ.service.d/override.conf (редактор из $SYSTEMD_EDITOR/$EDITOR/$VISUAL)
sudo systemctl edit --drop-in=limits ИМЯ   # (systemd ≥ 253) файл limits.conf вместо override.conf
sudo systemctl edit --full ИМЯ          # копия ВСЕГО юнита в /etc/systemd/system/ИМЯ.service (перекрывает пакетный целиком)
sudo systemctl edit --force --full моя.service   # создать новый юнит с нуля
sudo systemctl edit --runtime ИМЯ       # временно, в /run (до перезагрузки)
sudo systemctl revert ИМЯ               # удалить все drop-in и полную копию из /etc и /run, снять mask — вернуться к вендорскому юниту
sudo systemctl daemon-reload            # перечитать все unit-файлы и перезапустить генераторы (после ручной правки файлов)
sudo systemctl daemon-reexec            # перезапустить сам менеджер PID 1 с сохранением состояния (после обновления systemd; редко нужно)
```

`systemctl edit` сам делает эквивалент `daemon-reload`, но **не перезапускает** службу — изменения в `[Service]` применятся после `systemctl restart ИМЯ`.

Неинтерактивно (для скриптов). В 22.04/24.04 опции `--stdin` нет — пишите файл drop-in сами (`mkdir -p …service.d`, `tee`, `daemon-reload`, см. п. 4.1). В 26.04 (systemd ≥ 256) можно так:

```bash
printf '[Service]\nLimitNOFILE=65536\n' | sudo systemctl edit --stdin --drop-in=limits ИМЯ
```

Изменение лимитов ресурсов «на лету» без правки файлов:

```bash
sudo systemctl set-property postgresql@16-main.service MemoryHigh=12G     # сохраняется в /etc/systemd/system.control/…
sudo systemctl set-property --runtime ИМЯ CPUQuota=200%                   # до перезагрузки
```

### 2.6. Шаблонные юниты `name@instance`

Файл с `@` перед суффиксом (`postgresql@.service`, `srv1cv8-8.3.27.2325@.service`, `getty@.service`) — **шаблон**. Экземпляр создаётся при обращении по имени `имя@ЭКЗЕМПЛЯР.service`; строка после `@` подставляется в юнит через спецификаторы:

| Спецификатор | Значение | Пример для `postgresql@16-main.service` |
|---|---|---|
| `%i` | имя экземпляра как есть (экранированное) | `16-main` |
| `%I` | имя экземпляра, разэкранированное (`-` → `/`) | `16/main` |
| `%n` | полное имя юнита | `postgresql@16-main.service` |
| `%N` | имя без суффикса типа | `postgresql@16-main` |
| `%p` | префикс (до `@`) | `postgresql` |
| `%H` | имя хоста | `srv1c` |
| `%h` | домашний каталог пользователя службы | |
| `%t` | каталог времени выполнения (`/run` для системных) | `/run` |
| `%%` | символ `%` | |

```bash
sudo systemctl start postgresql@16-main
sudo systemctl enable --now srv1cv8-8.3.27.2325@default    # экземпляр "default" шаблона сервера 1С
systemctl list-units 'postgresql@*'
```

Особенности:

- `systemctl enable шаблон@.service` (без экземпляра) допустим только если в `[Install]` шаблона задан `DefaultInstance=` — тогда включается этот экземпляр;
- drop-in можно положить и для одного экземпляра (`/etc/systemd/system/имя@экземпляр.service.d/`), и для всех экземпляров шаблона (`/etc/systemd/system/имя@.service.d/`); сначала читается каталог экземпляра, затем шаблона;
- имена экземпляров с «неудобными» символами экранируются: `systemd-escape --template=foo@.service "мой путь"`.

---

## 3. Написание unit-файлов служб

### 3.1. Синтаксис и минимальный пример

Формат — INI: секции в квадратных скобках, строки `Ключ=Значение`. Комментарии — строки, начинающиеся с `#` или `;` (комментарий в конце строки со значением **не поддерживается** — он станет частью значения). Перенос длинной строки — обратная косая черта в конце. Булевы значения: `yes/no`, `true/false`, `on/off`, `1/0`. Ключи-списки (`ExecStartPre=`, `Environment=`, `EnvironmentFile=`…) накапливаются; **пустое присваивание сбрасывает список** (`ExecStart=` на отдельной строке) — это основа переопределений в drop-in. Исключение — зависимости (`After=`, `Wants=`, `Requires=`…): они тоже накапливаются, но пустым значением не сбрасываются.

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My application server
Documentation=https://example.org/docs
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
EnvironmentFile=-/etc/default/myapp
ExecStart=/opt/myapp/bin/server --config /etc/myapp/server.conf
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemd-analyze verify /etc/systemd/system/myapp.service   # проверка синтаксиса и ссылок
sudo systemctl daemon-reload
sudo systemctl enable --now myapp.service
systemctl status myapp
```

Права на unit-файл: `root:root 0644`. Бит исполнения не нужен (systemd выдаст предупреждение «marked executable»); совет `chmod +x` из старых статей — ошибка.

### 3.2. Секция [Unit]: описание и зависимости

| Директива | Смысл |
|---|---|
| `Description=` | короткое описание (видно в `status` и журнале) |
| `Documentation=` | ссылки `man:`, `https://`, `file:` |
| `After=A B` | **порядок**: стартовать после A и B (если они вообще запускаются). При остановке порядок обратный: этот юнит останавливается раньше A и B. Не «подтягивает» A |
| `Before=A` | порядок: стартовать раньше A |
| `Wants=A` | **слабое требование**: при запуске этого юнита запустить и A; сбой A не мешает запуску |
| `Requires=A` | **жёсткое требование**: запустить A; если A не смог активироваться (при наличии `After=A`) — этот юнит не запустится; явная остановка или перезапуск A останавливает/перезапускает и этот юнит |
| `Requisite=A` | A уже должен быть активен, иначе немедленный отказ (сам A не запускается) |
| `BindsTo=A` | как `Requires=`, но юнит останавливается при любом переходе A в неактивное состояние |
| `PartOf=A` | остановка/перезапуск A распространяется на этот юнит (в одну сторону). Так `postgresql@16-main` привязан к `postgresql.service` |
| `Upholds=A` | (≥249) как `Wants=`, но A будет постоянно поднят, пока жив этот юнит |
| `Conflicts=A` | запуск одного останавливает другой |
| `OnFailure=B` | запустить B, когда этот юнит перешёл в `failed` (уведомления, откат) |
| `OnSuccess=B` | (≥249) запустить B после успешного завершения |
| `RequiresMountsFor=/путь` | добавить `Requires=`+`After=` на mount-юниты, нужные для пути (данные на отдельном диске!) |
| `ConditionPathExists=/путь` | если условие ложно — запуск **тихо пропускается** (юнит не failed) |
| `AssertPathExists=/путь` | если ложно — запуск завершается **ошибкой** |
| `StartLimitIntervalSec=`, `StartLimitBurst=` | лимит частоты запусков: не более Burst запусков за Interval (по умолчанию 5 за 10 с); при превышении — `start-limit-hit`, дальнейшие запуски блокируются до `reset-failed`. **Пишутся в `[Unit]`, а не в `[Service]`** |

Главное правило: **`After=`/`Before=` — только порядок, `Wants=`/`Requires=` — только «запусти вместе со мной»**. Они независимы. `Requires=postgresql.service` без `After=postgresql.service` запустит оба юнита **параллельно**. Типичная пара: `Wants=X` + `After=X`.

Специальные цели, которые чаще всего нужны:

| Цель | Что означает |
|---|---|
| `network.target` | сетевой стек «начал подниматься»; полезна в основном для порядка **остановки** (служба с `After=network.target` остановится до отключения сети). Не гарантирует, что адрес уже назначен |
| `network-online.target` | сеть реально настроена (есть адрес/маршрут). Активная цель: её надо и «подтянуть» (`Wants=network-online.target`), и упорядочиться после (`After=network-online.target`). Ждёт её `systemd-networkd-wait-online.service` (netplan/networkd) или `NetworkManager-wait-online.service` |
| `multi-user.target` | обычный многопользовательский режим без графики — сюда «вешают» серверные службы (`WantedBy=multi-user.target`) |
| `graphical.target` | multi-user + графика; в Ubuntu это `default.target` по умолчанию даже на сервере |
| `time-sync.target` | системные часы синхронизированы (нужен включённый `systemd-time-wait-sync.service` либо аналог от chrony) |
| `remote-fs.target`, `local-fs.target` | смонтированы сетевые / локальные ФС |
| `timers.target`, `sockets.target` | сюда включают таймеры и сокеты |
| `rescue.target`, `emergency.target` | режимы восстановления (см. раздел 12) |

### 3.3. Секция [Service]: тип службы

| `Type=` | Когда systemd считает службу запущенной | Для чего |
|---|---|---|
| `simple` (по умолчанию, если есть `ExecStart=`) | сразу после fork, ещё до exec бинарника — ошибки вида «файл не найден» проявятся уже после «успешного» start | процесс остаётся на переднем плане и не демонизируется (`ragent` без `-daemon`, `cron -f`) |
| `exec` | после успешного `execve()` — т.е. бинарник найден и запущен; `systemctl start` вернёт ошибку, если нет пользователя/файла | то же, но надёжнее; документация systemd рекомендует для долгоживущих служб |
| `forking` | когда исходный процесс завершился, оставив фоновый потомок | классические демоны, которые сами уходят в фон; нужен `PIDFile=` (так сделан `postgresql@.service`: `pg_ctlcluster … start` + `PIDFile=/run/postgresql/%i.pid`). Для новых служб не рекомендуется |
| `notify` | когда служба прислала `READY=1` через `sd_notify()` | службы с поддержкой уведомлений (`rsyslogd`, PostgreSQL, собранный с `--with-systemd`, в юнитах RHEL) |
| `notify-reload` (≥253) | как `notify`, плюс reload через сигнал (SIGHUP) с подтверждением | |
| `oneshot` (по умолчанию, если нет `ExecStart=`) | когда процесс **завершился**; последующие юниты ждут его конца | разовые действия: скрипт резервного копирования, инициализация. Допускает несколько `ExecStart=`. `Restart=always/on-success` запрещены. Тайм-аут запуска по умолчанию отключён |
| `dbus` | когда на шине появилось имя `BusName=` | |
| `idle` | как `simple`, но запуск откладывается до конца активных заданий (≤5 с) | вывод на консоль |

Сопутствующее: `RemainAfterExit=yes` — считать юнит активным после выхода процесса (для oneshot-«настроек»; так сделан зонтичный `postgresql.service`). `PIDFile=` — для `forking`. `GuessMainPID=`. `ExitType=cgroup` (≥250) — служба жива, пока жив хоть один процесс в cgroup.

### 3.4. Команды Exec*

| Директива | Когда выполняется |
|---|---|
| `ExecCondition=` | до всего; код 1–254 — тихо пропустить запуск, 255 — ошибка |
| `ExecStartPre=` | перед основной командой, последовательно; ошибка (без префикса `-`) срывает запуск |
| `ExecStart=` | основная команда. Ровно одна (кроме `Type=oneshot`) |
| `ExecStartPost=` | после того, как служба признана запущенной (по правилам `Type=`) |
| `ExecReload=` | по `systemctl reload`; доступна `$MAINPID` |
| `ExecStop=` | по `systemctl stop` (только если запуск был успешным); после неё оставшиеся процессы добиваются по `KillMode=`. Если не задана — просто посылается `KillSignal=` |
| `ExecStopPost=` | после остановки в любом случае (в т.ч. после сбоя); получает `$SERVICE_RESULT`, `$EXIT_CODE`, `$EXIT_STATUS` |

Правила командной строки (частый источник ошибок):

1. **Это не shell.** Нет `|`, `>`, `&&`, `*`, `~`, подстановки команд. Нужны — пишите `ExecStart=/bin/sh -c '…'` или вынесите в скрипт.
2. Первый аргумент — **абсолютный путь** к исполняемому файлу (или имя, которое находится в стандартном `PATH` systemd); переменная в качестве имени программы не допускается.
3. Префиксы перед путём: `-` — игнорировать ненулевой код возврата (`ExecStart=-/usr/bin/pg_ctlcluster …` в юните PostgreSQL); `+` — выполнить с полными привилегиями root, игнорируя `User=` (удобно в `ExecStartPre=+/bin/mkdir …`); `@` — подменить `argv[0]`; `:` — не подставлять переменные; `!`, `!!` — частичное повышение привилегий.
4. Переменные окружения: `${VAR}` — подставляется **одним аргументом** (даже если пусто — будет пустой аргумент `""`, даже если внутри пробелы); `$VAR` отдельным словом — **разбивается по пробелам** на ноль и более аргументов (пустая переменная исчезает бесследно). Неизвестная переменная — пустая строка. Литерал доллара — `$$`. Подстановка работает только для переменных из `Environment=`/`EnvironmentFile=` (и служебных вроде `$MAINPID`), а не «из системы».
5. Спецификаторы `%i`, `%h`, `%n` раскрываются при загрузке юнита; литерал процента — `%%` (важно в `date +%%F`).
6. Несколько команд в одной директиве можно разделить отдельно стоящим ` ; ` (для `ExecStart=` — только при `Type=oneshot`); нагляднее писать несколько строк `ExecStartPre=`/`ExecStart=`.

Пример различия п. 4 (объясняет, почему необязательные флаги вроде `-debug` передают как `$VAR`, а не `${VAR}`):

```ini
Environment=OPTS=
# так: при пустой OPTS лишнего аргумента нет
ExecStart=/usr/bin/prog --port 1540 $OPTS
# а так при пустой OPTS программа получила бы лишний пустой аргумент "":
# ExecStart=/usr/bin/prog --port 1540 ${OPTS}
```

### 3.5. Пользователь, каталог, окружение

```ini
[Service]
# от чьего имени запускать (по умолчанию root) и основная группа (по умолчанию — основная группа User=)
User=usr1cv8
Group=grp1cv8
# дополнительные группы
SupplementaryGroups=ssl-cert
# рабочий каталог (по умолчанию /); "~" — домашний каталог User=; префикс "-" — не падать, если каталога нет
WorkingDirectory=/var/lib/myapp
# маска прав создаваемых файлов (по умолчанию 0022)
UMask=0027
# несколько переменных в одной строке; значение с пробелами — в кавычки берётся ВСЁ присваивание
Environment=LANG=ru_RU.UTF-8 TZ=Europe/Moscow
Environment="JAVA_OPTS=-Xms1g -Xmx4g"
# файл вида KEY=VALUE; "-" перед путём — не ошибка, если файла нет
EnvironmentFile=-/etc/default/myapp
# пробросить переменную из окружения менеджера / убрать переменную
PassEnvironment=HTTP_PROXY
UnsetEnvironment=LD_PRELOAD
```

(Комментарии в unit-файлах пишутся только отдельными строками: `Ключ=значение  # комментарий` сделает «# комментарий» частью значения.)

Важно знать:

- **Служба не видит окружение вашего shell.** Ни `~/.bashrc`, ни `/etc/profile`, ни `/etc/environment` не читаются. По умолчанию заданы только `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`, `LANG` (из `/etc/default/locale` / `locale.conf`), `USER`, а при заданном `User=` — ещё `LOGNAME`, `HOME`, `SHELL`; плюс служебные `INVOCATION_ID`, `JOURNAL_STREAM`, `SYSTEMD_EXEC_PID`.
- `Environment=` **не раскрывает** `$ПЕРЕМЕННЫЕ` внутри значения (`Environment=PATH=$PATH:/opt/bin` не сработает как в shell), но раскрывает `%`-спецификаторы.
- Формат `EnvironmentFile`: строки `KEY=VALUE`, комментарии `#`/`;`, **без `export`**, без подстановок; значения можно брать в одинарные/двойные кавычки. Значения из файла перекрывают `Environment=`. Файл читается непосредственно перед запуском, `daemon-reload` для него не нужен (нужен `restart`).
- `Environment=` виден всем через `systemctl show` — не храните там пароли; для секретов есть `LoadCredential=` или файл с правами 0600, читаемый самой службой.
- Посмотреть реальное окружение работающего процесса: `sudo cat /proc/$(systemctl show -p MainPID --value ИМЯ)/environ | tr '\0' '\n'`.

### 3.6. Перезапуск при сбоях

```ini
[Service]
Restart=on-failure
RestartSec=5
```

| Причина завершения | `no` | `always` | `on-success` | `on-failure` | `on-abnormal` | `on-abort` | `on-watchdog` |
|---|---|---|---|---|---|---|---|
| Чистый выход (код 0, либо SIGHUP/SIGINT/SIGTERM/SIGPIPE) | – | да | да | – | – | – | – |
| Ненулевой код возврата | – | да | – | да | – | – | – |
| Убит «нечистым» сигналом (SIGKILL, SIGSEGV…) | – | да | – | да | да | да | – |
| Тайм-аут запуска/остановки | – | да | – | да | да | – | – |
| Сторожевой таймер (`WatchdogSec=`) | – | да | – | да | да | – | да |

- `RestartSec=` — пауза перед перезапуском; по умолчанию **100 мс** (поэтому падающая служба мгновенно упирается в лимит 5 запусков за 10 с → `start-limit-hit`). Для серверных служб ставьте 3–10 с.
- `systemctl stop` никогда не вызывает авто-рестарт. `RestartPreventExitStatus=` — коды, при которых не перезапускать; `SuccessExitStatus=` — коды, считающиеся успехом.
- Экспоненциальная задержка (≥254): `RestartSteps=5` + `RestartMaxDelaySec=5min`.
- Чтобы служба перезапускалась «вечно», отключите лимит в `[Unit]`: `StartLimitIntervalSec=0`.
- Счётчик рестартов: `systemctl show -p NRestarts ИМЯ`.

### 3.7. Тайм-ауты и завершение процессов

| Директива | По умолчанию | Смысл |
|---|---|---|
| `TimeoutStartSec=` | 90 с (`DefaultTimeoutStartSec`); для `oneshot` — без лимита | сколько ждать «готовности» при запуске; `infinity` или `0` — не ограничивать |
| `TimeoutStopSec=` | 90 с | сколько ждать завершения после `ExecStop=`/сигнала, потом SIGKILL |
| `TimeoutSec=` | – | задаёт оба сразу |
| `RuntimeMaxSec=` | infinity | принудительно остановить службу, проработавшую дольше |
| `KillMode=` | `control-group` | кому посылать сигнал при остановке: `control-group` — всем процессам cgroup службы; `mixed` — SIGTERM главному, затем SIGKILL остальным; `process` — только главному (не рекомендуется; так сделан `cron.service`, чтобы перезапуск cron не убивал задания); `none` — никому (крайне не рекомендуется) |
| `KillSignal=` | `SIGTERM` | первый сигнал при остановке |
| `SendSIGKILL=` | `yes` | добивать ли SIGKILL после тайм-аута |
| `FinalKillSignal=` | `SIGKILL` | чем добивать |
| `SendSIGHUP=` | `no` | дополнительно послать SIGHUP |

Последовательность остановки: `ExecStop=` → `KillSignal=` (+SIGCONT) процессам по `KillMode=` → ожидание до `TimeoutStopSec=` → `SIGKILL` оставшимся → `ExecStopPost=`.

Для СУБД короткий тайм-аут остановки опасен: в `postgresql@.service` задано `TimeoutStopSec=1h` (в старых версиях пакета — иначе), а остановка идёт командой `pg_ctlcluster -m fast … stop`. Серверу 1С на остановку рабочих процессов с большим числом сеансов тоже может не хватить 90 с — тогда `rphost` будут убиты SIGKILL (практика: увеличить `TimeoutStopSec=` до 120–300 с в drop-in).

### 3.8. Лимиты ресурсов процесса (rlimit) — LimitNOFILE и другие

Лимиты из `/etc/security/limits.conf` и `ulimit` **на службы systemd не действуют** (они применяются PAM-сеансами: вход по SSH, `su`, cron). Для служб лимиты задаются в юните:

| Директива | Аналог `ulimit` | Что ограничивает |
|---|---|---|
| `LimitNOFILE=` | `-n` | число открытых файлов/сокетов. По умолчанию для служб **1024 (soft) : 524288 (hard)** |
| `LimitNPROC=` | `-u` | число процессов/потоков пользователя (считается на UID; чаще лучше `TasksMax=`) |
| `LimitCORE=` | `-c` | размер core-дампа (`infinity` — разрешить полные дампы) |
| `LimitMEMLOCK=` | `-l` | объём блокируемой памяти (по умолчанию 8M); нужен для huge pages/`mlock` |
| `LimitSTACK=` | `-s` | размер стека |
| `LimitFSIZE=` | `-f` | максимальный размер файла |
| `LimitAS=`, `LimitDATA=`, `LimitRSS=` | `-v`, `-d`, `-m` | адресное пространство — **не используйте** для ограничения памяти (берите `MemoryMax=`); `LimitRSS` в Linux не работает |
| `LimitNICE=`, `LimitRTPRIO=`, `LimitSIGPENDING=`, `LimitMSGQUEUE=`, `LimitLOCKS=`, `LimitCPU=`, `LimitRTTIME=` | `-e`, `-r`, `-i`, `-q`, `-x`, `-t`, `-R` | прочее |

Синтаксис: одно число — и soft, и hard; `soft:hard` — раздельно; `infinity` — без ограничения; для байтовых — суффиксы `K M G T` (степени 1024).

```ini
[Service]
LimitNOFILE=65536
LimitCORE=infinity
```

Проверка фактических лимитов работающей службы:

```bash
systemctl show -p LimitNOFILE -p LimitNOFILESoft -p LimitCORE ИМЯ
cat /proc/$(systemctl show -p MainPID --value ИМЯ)/limits
```

Значения по умолчанию для **всех** служб меняются в `/etc/systemd/system.conf.d/*.conf` (`[Manager]`, `DefaultLimitNOFILE=…`, затем `systemctl daemon-reexec`), но правильнее задавать лимит конкретной службе.

Другие настройки процесса: `Nice=-5` (приоритет CPU, −20…19), `IOSchedulingClass=best-effort|idle|realtime` и `IOSchedulingPriority=0..7`, `CPUAffinity=0-3`, `CPUSchedulingPolicy=`, `OOMScoreAdjust=`.

`OOMScoreAdjust=` (−1000…1000) — поправка к «оценке» процесса для OOM-killer ядра: −1000 — никогда не убивать, положительные — убивать в первую очередь. В `postgresql@.service` задано `OOMScoreAdjust=-900` для postmaster (дочерние процессы сами возвращают себе 0). `OOMPolicy=` (`continue|stop|kill`) — что делать со **всем юнитом**, если ядро (или `systemd-oomd`) убило по OOM один из его процессов. Подтверждено: в man `systemd.service(5)` — `continue`: событие журналируется, юнит продолжает работать; `stop`: событие журналируется и юнит «is terminated cleanly by the service manager»; `kill`: ядро убивает и все остальные процессы юнита. Значение по умолчанию берётся из `DefaultOOMPolicy=`, которое в исходном `system.conf` systemd равно `stop` (для юнитов с `Delegate=yes` — `continue`). То есть по умолчанию systemd остановит **всю** службу (результат `oom-kill`); будет ли она затем запущена снова, зависит от её `Restart=`: `Result: oom-kill` считается сбоем, поэтому служба с `Restart=always/on-failure` перезапустится целиком (все сеансы 1С оборвутся), а служба без авто-рестарта (`postgresql@.service`) останется лежать. Для служб, которые сами умеют пережить гибель рабочего процесса (кластер 1С перезапускает `rphost`, postmaster — backend), поведение `stop` часто нежелательно — см. раздел 5. Официальных рекомендаций 1С или PGDG по `OOMPolicy=` нет; это вывод из документации systemd и практика сообщества, на стенде в рамках статьи не проверялось.

### 3.9. Контроль ресурсов через cgroup v2: MemoryMax, CPUQuota и др.

Действуют на **все процессы службы суммарно** (у сервера 1С — `ragent` + `rmngr` + все `rphost`).

| Директива | Смысл |
|---|---|
| `MemoryMax=8G` | жёсткий предел памяти cgroup; при превышении внутри cgroup срабатывает OOM-killer. Значение в байтах с `K/M/G/T`, в `%` от ОЗУ или `infinity` |
| `MemoryHigh=6G` | «мягкий» порог: выше него процессы тормозятся и память агрессивно высвобождается (без убийства) |
| `MemorySwapMax=0` | предел использования swap |
| `MemoryMin=`, `MemoryLow=` | защита памяти от вытеснения |
| `CPUQuota=200%` | не более двух полных ядер CPU (100% = одно ядро) |
| `CPUWeight=100` | относительный вес при конкуренции за CPU (1…10000, по умолчанию 100) |
| `AllowedCPUs=0-7` | на каких ядрах можно работать (cpuset) |
| `TasksMax=` | предел числа процессов+потоков (не только процессов!) в cgroup службы; по умолчанию `DefaultTasksMax=15%` от минимума из `kernel.pid_max`, `kernel.threads-max` и `pids.max` корневой cgroup. Пример из man — 4915 при `pid_max=32768`; на реальной 64-битной Ubuntu `pid_max` обычно 4194304, поэтому предел определяется `kernel.threads-max` (зависит от объёма ОЗУ) и на небольшой ВМ составляет порядка нескольких тысяч–десятков тысяч. Смотрите фактическое значение: `systemctl show -p TasksMax -p TasksCurrent ИМЯ` или строку `Tasks: N (limit: M)` в `systemctl status`. `infinity` — снять |
| `IOWeight=`, `IOReadBandwidthMax=/dev/sda 50M`, `IOWriteIOPSMax=` | ограничения ввода-вывода |
| `Slice=` | в какую ветку cgroup поместить службу (по умолчанию `system.slice`) |

```bash
systemd-cgtop                     # «top» по cgroup: CPU, память, задачи по службам
systemd-cgls                      # дерево cgroup с процессами
systemctl status ИМЯ              # строки Memory:/CPU:/Tasks:
systemctl show -p MemoryCurrent -p MemoryPeak -p TasksCurrent -p CPUUsageNSec ИМЯ
```

Устаревшие директивы cgroup v1 (`MemoryLimit=`, `CPUShares=`, `BlockIO*=`) объявлены deprecated с systemd 252; в Ubuntu 26.04 cgroup v1 удалён совсем — используйте `MemoryMax=`, `CPUWeight=`, `IO*=`.

Официальных рекомендаций 1С ограничивать сервер через `MemoryMax=` нет: память рабочих процессов регулируется настройками кластера («временно допустимый объём памяти процессов», «критический объём памяти процессов» и т.п.). `MemoryMax=`/`MemoryHigh=` — страховка уровня ОС (практика сообщества), применять осознанно.

### 3.10. Вывод, журналирование и изоляция

| Директива | Смысл |
|---|---|
| `StandardOutput=journal` | куда направить stdout; по умолчанию `journal`. Варианты: `null`, `file:/путь`, `append:/путь`, `truncate:/путь`, `journal+console`, `inherit`, `tty` |
| `StandardError=inherit` | stderr; по умолчанию наследует `StandardOutput` |
| `SyslogIdentifier=myapp` | тег сообщений в журнале (по умолчанию имя процесса) |
| `LogRateLimitIntervalSec=0` | отключить лимит частоты сообщений для этой службы |
| `PrivateTmp=yes` | отдельные `/tmp` и `/var/tmp` только для этой службы |
| `ProtectSystem=full` | `/usr`, `/boot`, `/efi`, `/etc` только для чтения (`strict` — вся ФС, кроме явно разрешённого) |
| `ProtectHome=yes` | `/home`, `/root`, `/run/user` недоступны |
| `ReadWritePaths=/var/lib/myapp` | исключения из `ProtectSystem=` |
| `NoNewPrivileges=yes` | запрет повышения привилегий через setuid |
| `RuntimeDirectory=myapp` | создать `/run/myapp` (владелец `User=`), удалить при остановке |
| `StateDirectory=myapp`, `LogsDirectory=myapp` | создать `/var/lib/myapp`, `/var/log/myapp` с нужным владельцем |

`PrivateTmp=yes` важно понимать при отладке: файлы, которые служба пишет в `/tmp`, вы в «общем» `/tmp` не увидите (они в `/tmp/systemd-private-…-ИМЯ.service-…/tmp`). Оценка «защищённости» юнита: `systemd-analyze security ИМЯ`.

Частые коды `status=` в `systemctl status` при сбое запуска: `200/CHDIR` — нет `WorkingDirectory`; `203/EXEC` — не найден/не исполняем файл из `ExecStart` (неверный путь, нет бита `x`, CRLF в shebang скрипта, `noexec` на ФС); `209/STDOUT` — не открыть файл вывода; `216/GROUP`, `217/USER` — нет такой группы/пользователя; `226/NAMESPACE` — не удалось настроить изоляцию (нет каталога из `ReadWritePaths=` и т.п.). Полная таблица: `systemd-analyze exit-status`.

### 3.11. Секция [Install]

| Директива | Смысл |
|---|---|
| `WantedBy=multi-user.target` | при `enable` создать симлинк в `multi-user.target.wants/` — служба стартует при обычной загрузке |
| `RequiredBy=` | то же, но жёсткая зависимость |
| `Alias=имя.service` | дополнительное имя (так `rsyslog.service` получает алиас `syslog.service`) |
| `Also=другой.socket` | включать/выключать вместе |
| `DefaultInstance=default` | для шаблонов: какой экземпляр включать при `enable шаблон@.service` |

Юнит без `[Install]` — `static`: его нельзя `enable`, он запускается только как зависимость, таймером, сокетом или вручную (типично для `X.service`, который запускает `X.timer`).

---

## 4. Переопределения (drop-in) и подключение внешних юнитов

### 4.1. Drop-in: `/etc/systemd/system/ИМЯ.service.d/*.conf`

Вместо правки вендорского файла (который перезапишется при обновлении пакета/платформы) создаётся каталог `ИМЯ.service.d/` с файлами `*.conf`, которые читаются **после** основного файла в алфавитном порядке и дополняют/переопределяют его.

```bash
sudo systemctl edit postgresql@16-main        # откроет редактор; сохранит /etc/systemd/system/postgresql@16-main.service.d/override.conf
```

или вручную:

```bash
sudo mkdir -p /etc/systemd/system/postgresql@16-main.service.d
sudo tee /etc/systemd/system/postgresql@16-main.service.d/limits.conf >/dev/null <<'EOF'
[Service]
LimitNOFILE=65536
OOMPolicy=continue
EOF
sudo systemctl daemon-reload
sudo systemctl restart postgresql@16-main
systemctl cat postgresql@16-main              # убедиться, что drop-in подхватился
systemctl status postgresql@16-main           # строка "Drop-In:"
```

Правила:

1. В drop-in обязательно указывать секцию (`[Unit]`, `[Service]`, `[Install]`).
2. Скалярные ключи (`Type=`, `User=`, `Restart=`, `LimitNOFILE=`) просто заменяются последним значением.
3. Списочные ключи **добавляются**. Чтобы заменить `ExecStart=`, сначала сбросьте его пустой строкой, иначе получите ошибку «Service has more than one ExecStart= setting»:

   ```ini
   [Service]
   ExecStart=
   ExecStart=/новый/путь/к/программе --опции
   ```

   То же для `Environment=` целиком, `ExecStartPre=`, `EnvironmentFile=`. Но одну переменную переопределять сбросом не нужно: более поздний `Environment=VAR=значение` перекрывает прежнее значение той же переменной.
4. Зависимости (`After=`, `Requires=`, `Wants=`) в drop-in можно только **добавлять**; убрать вендорскую зависимость можно лишь полной копией юнита (`systemctl edit --full`).
5. Приоритет каталогов тот же: `/etc` > `/run` > `/usr/lib`. Drop-in работает и поверх юнита, подключённого через `systemctl link`.
6. Для юнитов с дефисами в имени systemd дополнительно ищет «усечённые» каталоги: для `foo-bar-baz.service` — `foo-bar-.service.d/` и `foo-.service.d/` (официально, man `systemd.unit(5)`; более «длинный» префикс перекрывает более «короткий»). Есть и каталоги уровня типа: `/etc/systemd/system/service.d/*.conf` применяются ко **всем** службам (самый низкий приоритет среди drop-in).

   Как это работает для юнитов 1С. По исходному коду systemd 255 (`src/shared/dropin.c`, функция `unit_file_find_dirs`) усечение выполняется над **префиксом** имени (часть до `@` или до суффикса типа) по **последнему дефису**; точки в номере версии роли не играют. Для `srv1cv8-8.3.27.2325@default.service` префикс — `srv1cv8-8.3.27.2325`, усечённый — `srv1cv8-`, и каталоги просматриваются в таком порядке:

   | Каталог в `/etc/systemd/system/` | На что действует |
   |---|---|
   | `srv1cv8-8.3.27.2325@default.service.d/` | одна версия, один экземпляр |
   | `srv1cv8-8.3.27.2325@.service.d/` | одна версия, все экземпляры |
   | `srv1cv8-.service.d/` | любые юниты с префиксом `srv1cv8-` |
   | `srv1cv8-@default.service.d/` | **все версии**, экземпляр `default` |
   | `srv1cv8-@.service.d/` | **все версии, все экземпляры** |
   | `service.d/` | все службы системы |

   Для `ras-8.3.27.2325.service` аналогично: `ras-8.3.27.2325.service.d/`, затем `ras-.service.d/`. Практический смысл: настройки, которые не должны теряться при обновлении платформы (`After=`/`Wants=`, `LimitNOFILE=`, `TimeoutStopSec=`, `OOMPolicy=`), можно один раз положить в `/etc/systemd/system/srv1cv8-@.service.d/override.conf`, а не переносить каталог drop-in под каждое новое имя юнита. ⚠ Это вывод из чтения исходного кода версии 255 (Ubuntu 24.04; код версий 249 и 259 не сверялся), а не из документации (man описывает только пример без `@`), на стенде не проверялось и в руководствах 1С не встречается — после создания обязательно убедитесь, что каталог виден в строке `Drop-In:` вывода `systemctl status srv1cv8-<версия>@default` и в `systemctl cat`. Не кладите туда то, что зависит от версии или экземпляра (порты, `SRV1CV8_DATA`, пути с номером версии).
7. Найти все отличия от вендорской конфигурации в системе: `systemd-delta --type=extended,overridden,masked`.

### 4.2. `systemctl link` — подключить unit-файл, лежащий вне стандартных путей

```bash
sudo systemctl link /opt/1cv8/x86_64/8.3.27.2325/srv1cv8-8.3.27.2325@.service
# Created symlink /etc/systemd/system/srv1cv8-8.3.27.2325@.service → /opt/1cv8/x86_64/8.3.27.2325/srv1cv8-8.3.27.2325@.service
```

- Создаёт в `/etc/systemd/system/` симлинк на файл по **абсолютному** пути; после этого юнит доступен всем командам `systemctl` (сам по себе `link` не включает и не запускает).
- Официальное ограничение: файловая система с подключённым файлом должна быть доступна в момент старта systemd (в man прямо сказано: пути под `/home` и `/var` не годятся, если это отдельные ФС). Для 1С это значит: `/opt` должен находиться на корневой ФС (или юнит надо скопировать в `/etc/systemd/system/`).
- `systemctl enable /абсолютный/путь/к/юниту.service` делает link + enable за один шаг.
- `systemctl disable ЮНИТ` **удаляет и симлинк, созданный `link`** — так в man (22.04, 24.04 и 26.04): «removes all symlinks to the unit files backing the specified units from the unit configuration directory, and hence undoes any changes made by enable or link», причём удаляются и симлинки, созданные вручную. Для обычного (не шаблонного) юнита, например `ras-<версия>.service`, это значит: после `disable` юнит снова «not found», перед следующим `start` нужно повторить `link`.
- **Шаблонный юнит 1С — особый случай.** По исходному коду systemd 255 (`src/shared/install.c`: в набор «к удалению» попадает только то имя, которое передано команде, а симлинк удаляется, если его имя, имя его шаблона или имя файла-цели есть в этом наборе) команда `systemctl disable srv1cv8-<версия>@default` удалит только `multi-user.target.wants/srv1cv8-<версия>@default.service`, а симлинк шаблона `/etc/systemd/system/srv1cv8-<версия>@.service` **останется**. Команда по имени шаблона — `systemctl disable srv1cv8-<версия>@.service` (или сокращённо `srv1cv8-<версия>@`) — удаляет и симлинк шаблона, и симлинки автозапуска всех его экземпляров; именно так поступает скрипт обновления interface31.ru (`systemctl disable srv1cv8-$oldver@`). ⚠ На стенде не проверялось: man и код формально расходятся, поэтому после `disable` всегда смотрите результат — `ls -l /etc/systemd/system/ | grep -E '1cv8|ras-'` и `systemctl list-unit-files 'srv1cv8*' 'ras-*'`. «Висячий» симлинк на удалённый каталог платформы убирается вручную: `sudo rm /etc/systemd/system/srv1cv8-<версия>@.service && sudo systemctl daemon-reload`.
- Ошибка `Failed to link unit: File /etc/systemd/system/X.service already exists` означает, что там уже лежит обычный файл или другой симлинк с тем же именем (например, юнит ранее скопировали вручную) — удалите его и повторите.

---

## 5. Реальные юниты: сервер 1С, RAS, PostgreSQL

### 5.1. Сервер 1С:Предприятия — `srv1cv8-<версия>@.service`

**Что подтверждено** (фрагменты англоязычной документации платформы 8.3.22/8.3.23 «Administrator Guide. Client/Server Mode», п. 4.2 «Running the server agent → On Linux», доступные через поисковую выдачу, и согласованные между собой практические руководства для 8.3.22–8.3.27; сам русскоязычный текст «Руководства администратора» на ИТС закрыт подпиской и напрямую не читался):

- Единый дистрибутив (`setup-full-<версия>-x86_64.run`, платформа устанавливается в `/opt/1cv8/x86_64/<версия>/`) появился в 8.3.20, но в 8.3.20 сервер ещё запускался init-скриптом: в каталоге платформы лежали `srv1cv83` и `srv1cv83.conf`, которые подключали симлинками в `/etc/init.d/srv1cv83` и `/etc/default/srv1cv83` (практика; так делает скрипт обновления interface31.ru). **С 8.3.21** вместо этого в каталоге платформы поставляется **шаблонный** юнит `srv1cv8-<версия>@.service` (подтверждено несколькими независимыми руководствами для 8.3.21–8.3.27). Установщик его **не регистрирует** — это делает администратор командой `systemctl link`.
- Имя экземпляра (после `@`) произвольное; стандартный экземпляр называется `default`. Разные экземпляры = разные агенты кластера на одном хосте (с разными портами и каталогами данных).
- Сервер работает от пользователя `usr1cv8`, группа `grp1cv8`. Каталог данных кластера по умолчанию — `/home/usr1cv8/.1cv8/1C/1cv8` (там `1cv8wsrv.lst`, каталоги `reg_<порт>` с информацией о базах, журналами регистрации и т.п.).
- Порты по умолчанию: агент `ragent` — 1540, менеджер кластера `rmngr` — 1541, диапазон рабочих процессов `rphost` — 1560:1591.
- Параметры запуска задаются **переменными окружения в юните** (`Environment=SRV1CV8_…`), менять их надо через drop-in, а не правкой файла в `/opt`.
- Для платформы 8.5.x схема, предположительно, та же (`/opt/1cv8/x86_64/8.5.x.y/srv1cv8-8.5.x.y@.service`) — по сравнению документации 8.5.1 и 8.3.27 (10.10.2026) схема имён и расположение юнитов не менялись; на сервере не подтверждено, проверьте `ls /opt/1cv8/x86_64/*/*.service`.

Регистрация и запуск (на примере 8.3.27.2325; подставьте свою версию):

```bash
ls /opt/1cv8/x86_64/                                   # какие версии установлены
sudo systemctl link /opt/1cv8/x86_64/8.3.27.2325/srv1cv8-8.3.27.2325@.service
sudo systemctl enable srv1cv8-8.3.27.2325@default.service    # автозапуск экземпляра default
sudo systemctl start  srv1cv8-8.3.27.2325@default.service
systemctl status srv1cv8-8.3.27.2325@default.service --no-pager
sudo ss -ltnp | grep -E 'ragent|rmngr|rphost'          # слушают ли 1540, 1541, 1560+ (имена процессов видны только под root)
```

В руководствах встречается и `systemctl enable srv1cv8-8.3.27.2325@` (без экземпляра; так в статье interface31.ru для 8.3.27.2325 и в их скрипте обновления) — команда без экземпляра допустима только при наличии `DefaultInstance=` в секции `[Install]` шаблона, так что её работоспособность косвенно подтверждает, что в вендорском юните задан экземпляр по умолчанию `default`. Надёжнее всегда писать экземпляр явно: `…@default`. Осторожно с опечаткой из ряда статей (serveradmin.ru, wiki.kint.ru): `systemctl start srv1cv8-…@.default` (с точкой) запустит **другой** экземпляр с именем `.default`, не тот, что включён в автозапуск; если затем стартует ещё и `default`, оба экземпляра претендуют на одни и те же порты и каталог кластера. Проверка, что именно запущено: `systemctl list-units 'srv1cv8*'`.

**Точный текст вендорского юнита из открытых источников получить не удалось** (документация платформы на ИТС закрыта подпиской; при рецензии 2026-10-10 повторная попытка тоже не удалась: страница главы на its.1c.ru отдаёт без подписки только оглавление, kb.1ci.com без входа показывает пустые разделы, Infostart отвечает 429) — ⚠ не подтверждено дословно. Всегда смотрите фактический файл своей версии:

```bash
systemctl cat srv1cv8-8.3.27.2325@default.service
# или прямо файл:
cat /opt/1cv8/x86_64/8.3.27.2325/srv1cv8-8.3.27.2325@.service
```

Для понимания устройства ниже — **шаблон сообщества** `srv1cv83@.service` (GitHub `slothfk/1c_systemd`, статья Infostart №1341653), который появился раньше вендорского и использует те же основные переменные `SRV1CV8_*` (для вендорского юнита подтверждены `SRV1CV8_DATA`, `SRV1CV8_PORT`, `SRV1CV8_REGPORT`, `SRV1CV8_RANGE`). В шаблоне сообщества экземпляром служит номер версии платформы, а не имя `default`. Директивы приведены дословно, комментарии переведены:

```ini
[Unit]
Description=1C:Enterprise Server 8.3 (%i)
Requires=network.target

[Service]
Type=simple
User=usr1cv8
Group=grp1cv8
# каталог данных кластера
Environment=SRV1CV8_DATA=/home/usr1cv8/.1cv8/1C/1cv8/
# порт агента сервера (ragent)
Environment=SRV1CV8_PORT=1540
# порт менеджера кластера, создаваемого при первом запуске
Environment=SRV1CV8_REGPORT=1541
# диапазон портов рабочих процессов
Environment=SRV1CV8_RANGE=1560:1591
# уровень безопасности соединений: 0, 1, 2
Environment=SRV1CV8_SECLEV=0
# режим отладки: пусто — выключен, "-debug" — включён
Environment=SRV1CV8_DEBUG=
# период и тайм-аут проверки разрыва соединений, мс
Environment=SRV1CV8_PING_PERIOD=1000
Environment=SRV1CV8_PING_TIMEOUT=5000
# keytab для Kerberos-аутентификации
Environment=KRB5_KTNAME=/opt/1cv8/x86_64/%i/usr1cv8.keytab
ExecStart=/bin/sh -c "/opt/1cv8/x86_64/%i/ragent -d ${SRV1CV8_DATA} -port ${SRV1CV8_PORT} -regport ${SRV1CV8_REGPORT} \
 -range ${SRV1CV8_RANGE} -seclev ${SRV1CV8_SECLEV} -pingPeriod ${SRV1CV8_PING_PERIOD} -pingTimeout ${SRV1CV8_PING_TIMEOUT} ${SRV1CV8_DEBUG}"
Restart=always
RestartSec=5

[Install]
DefaultInstance=default
WantedBy=multi-user.target
```

Разбор (что здесь важно понимать и что проверять в вендорском файле):

| Элемент | Пояснение |
|---|---|
| `Type=simple` + `ragent` **без** `-daemon` | агент остаётся на переднем плане; systemd сам следит за ним и за всем деревом `ragent → rmngr, rphost` в одной cgroup. Ключ `-daemon` нужен только при ручном запуске из shell |
| `Requires=network.target` | жёсткая зависимость **без** `After=` — порядок не задаёт; и `network.target` не означает «сеть поднята». Если СУБД на другом хосте или имена разрешаются по DNS — добавьте `After=`/`Wants=network-online.target` (раздел 6) |
| `User=usr1cv8`, `Group=grp1cv8` | все файлы кластера, лицензий (`/var/1C/licenses`), техжурнала должны быть доступны этому пользователю |
| `Environment=SRV1CV8_*` + `${VAR}` в `ExecStart` | параметры `ragent`: `-d` каталог кластера, `-port`, `-regport`, `-range`, `-seclev`, `-pingPeriod`, `-pingTimeout`, `-debug` |
| `/bin/sh -c "…"` | в шаблоне сообщества команда запускается через shell, чтобы пустая `${SRV1CV8_DEBUG}` не превращалась в пустой аргумент (см. п. 3.4) |
| `Restart=always`, `RestartSec=5` | агент перезапускается через 5 с после любого завершения, кроме `systemctl stop` |
| нет `LimitNOFILE=` | действует общий предел 1024 (soft) / 524288 (hard) открытых файлов |
| нет `KillMode=`, `TimeoutStopSec=` | при остановке SIGTERM получают все процессы cgroup; через 90 с — SIGKILL |

Переменные запуска агента сервера (имена по документации 1С и шаблонам; значения по умолчанию — из тех же источников):

| Переменная | Параметр `ragent` | По умолчанию | Смысл |
|---|---|---|---|
| `SRV1CV8_DATA` | `-d` | `/home/usr1cv8/.1cv8/1C/1cv8` | каталог служебных файлов кластера |
| `SRV1CV8_PORT` | `-port` | 1540 | порт агента сервера |
| `SRV1CV8_REGPORT` | `-regport` | 1541 | порт менеджера кластера, создаваемого по умолчанию |
| `SRV1CV8_RANGE` | `-range` | 1560:1591 | диапазоны портов рабочих процессов (`45:49` или `45:67,70:72`) |
| `SRV1CV8_SECLEV` | `-seclev` | 0 | уровень защищённости соединений: 0 — незащищённые, 1 — защита только на время аутентификации, 2 — постоянно защищённые |
| `SRV1CV8_DEBUG` | `-debug` | пусто (выключено) | отладка на сервере. Значение — **сами ключи командной строки**, а не `0/1`: `-debug` (или `-debug -tcp`) — отладка по TCP, `-debug -http` — по HTTP. Для вендорского юнита 8.3.21+ это подтверждено практикой: скрипт обновления interface31.ru включает отладку drop-in'ом `Environment=SRV1CV8_DEBUG="-debug -http"` / `"-debug -tcp"`; так же устроен шаблон сообщества. В старом init-скрипте (`/etc/default/srv1cv83`, до 8.3.21) переменная принимала `0/1` — не переносите старые значения. Дословно вендорский `ExecStart` не прочитан — сверяйте в `systemctl cat` |
| `SRV1CV8_KEYTAB` (в шаблоне сообщества — напрямую `KRB5_KTNAME`) | – | `usr1cv8.keytab` в каталоге платформы | keytab для Kerberos-аутентификации. `SRV1CV8_KEYTAB` — имя, встреченное автором во фрагменте англоязычной документации 8.3.23 (и, по памяти, в старом init-скрипте); в документации 8.3.27 переменная называется `SRV1CV8_KEYTAB` (сверено 10.10.2026); не подтверждено, какое из двух имён использует вендорский юнит вашей версии (в трёх просмотренных шаблонах сообщества — только `KRB5_KTNAME`). `KRB5_KTNAME` — стандартная переменная библиотеки Kerberos, её и нужно задавать, если в `systemctl cat` нет `SRV1CV8_KEYTAB` |
| проверка разрыва соединений: в шаблоне сообщества `SRV1CV8_PING_PERIOD` / `SRV1CV8_PING_TIMEOUT`; в англоязычной документации 8.3.23 фигурируют `SRV1CV8_PINGPERIOD` / `SRV1CV8_PINGTIMEOUT` — ⚠ не подтверждено, какое написание в вашей версии | `-pingPeriod`, `-pingTimeout` | 1000 / 5000 мс | период и тайм-аут проверки |

Переменная с неверным именем молча игнорируется — имена берите только из `systemctl cat` своей версии.

**Типовые переопределения** (drop-in для экземпляра; имя каталога содержит версию!):

```bash
sudo systemctl edit srv1cv8-8.3.27.2325@default.service
```

```ini
[Unit]
# стартовать после сети и локального PostgreSQL (см. раздел 6)
After=network-online.target postgresql.service
Wants=network-online.target postgresql.service

[Service]
# больше открытых файлов/сокетов при большом числе сеансов (практика)
LimitNOFILE=65536
# дать рабочим процессам время корректно завершиться (практика)
TimeoutStopSec=180
# не останавливать весь кластер, если ядро убило по OOM один rphost (практика)
OOMPolicy=continue
# полные дампы памяти при аварийном завершении (если настроен сбор дампов)
LimitCORE=infinity
```

```bash
sudo systemctl restart srv1cv8-8.3.27.2325@default.service
systemctl show -p LimitNOFILESoft -p TimeoutStopUSec -p OOMPolicy srv1cv8-8.3.27.2325@default.service
```

Оговорки к этому набору. (1) Всё, кроме `After=`/`Wants=`, — практика сообщества, официальных рекомендаций 1С по `LimitNOFILE=`, `TimeoutStopSec=`, `OOMPolicy=` для юнита сервера не найдено; прежде чем что-то добавлять, посмотрите, что уже задано в вендорском файле (`systemctl cat …`) и что действует фактически (`systemctl show -p LimitNOFILE -p LimitNOFILESoft -p TasksMax -p OOMPolicy -p Restart -p TimeoutStopUSec …`). (2) `OOMPolicy=continue` меняет только реакцию systemd: убитый ядром `rphost` кластер 1С перезапустит сам, остальные сеансы уцелеют; без этой строки (при `stop`) systemd остановит весь юнит, а при `Restart=always` в юните тут же поднимет его заново — то есть оборвутся все сеансы. Первопричину (нехватку памяти) это не устраняет: смотрите `journalctl -k -g 'out of memory|oom-kill'` и настройки памяти рабочих процессов в кластере. (3) Число потоков сервера 1С ограничено ещё и `TasksMax=` (п. 3.9): при большом числе сеансов сверяйте `Tasks: N (limit: M)` в `systemctl status`; при приближении к пределу — `TasksMax=infinity` или явное число в том же drop-in.

Включение отладки на сервере (значение переменной — ключи `ragent`; подтверждено практикой для вендорского юнита 8.3.21+, см. таблицу выше; дословный `ExecStart` своей версии всё же проверьте через `systemctl cat`):

```ini
# /etc/systemd/system/srv1cv8-<версия>@default.service.d/override.conf
[Service]
# отладка по TCP (то же, что просто -debug)
Environment=SRV1CV8_DEBUG="-debug -tcp"
# либо отладка по HTTP (вместо строки выше):
# Environment=SRV1CV8_DEBUG="-debug -http"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart srv1cv8-8.3.27.2325@default
# проверка: ключ должен появиться в командной строке ragent
ps -o pid,args -C ragent | cat
systemctl show -p Environment srv1cv8-8.3.27.2325@default     # итоговый набор переменных с учётом drop-in
```

Кавычки в `Environment=ИМЯ="значение с пробелом"` обязательны: без них systemd воспримет `-http` как отдельное (некорректное) присваивание и в переменную попадёт только `-debug`. Выключение отладки — удалить строку (или весь drop-in), `daemon-reload`, `restart`. Перезапуск сервера 1С обрывает все сеансы — выполняйте в технологическое окно.

Второй экземпляр сервера на том же хосте (подтверждено статьёй interface31.ru для 8.3.22.2283):

```bash
sudo systemctl edit srv1cv8-8.3.22.2283@2x.service
```

```ini
[Service]
Environment=SRV1CV8_DATA=/home/usr1cv8/.1cv8/1C/1cv8_2x
Environment=SRV1CV8_PORT=2540
Environment=SRV1CV8_REGPORT=2541
Environment=SRV1CV8_RANGE=2560:2591
```

```bash
sudo mkdir -p /home/usr1cv8/.1cv8/1C/1cv8_2x && sudo chown -R usr1cv8:grp1cv8 /home/usr1cv8/
sudo systemctl enable --now srv1cv8-8.3.22.2283@2x
```

**Обновление платформы** (имя юнита содержит версию, поэтому каждый релиз — это новый юнит и новые drop-in):

```bash
OLD=8.3.27.2074; NEW=8.3.27.2325
# 0. что сейчас запущено и подключено (экземпляров может быть несколько!)
systemctl list-units 'srv1cv8*' 'ras-*'; systemctl list-unit-files 'srv1cv8*' 'ras-*'
# 1. остановить старую версию (обрывает все сеансы 1С)
sudo systemctl stop ras-$OLD                           # если используется RAS
sudo systemctl stop srv1cv8-$OLD@default               # и остальные экземпляры этой версии, если они есть
# 2. убрать из автозапуска и отключить link. Для шаблона — disable ПО ИМЕНИ ШАБЛОНА (с "@." без экземпляра):
#    это снимает и автозапуск экземпляров, и симлинк шаблона (см. п. 4.2); для обычного юнита RAS достаточно имени
sudo systemctl disable srv1cv8-$OLD@.service
sudo systemctl disable ras-$OLD.service                # если используется RAS
ls -l /etc/systemd/system/ | grep -E '1cv8|ras-'      # симлинков на $OLD остаться не должно (каталоги *.service.d останутся)
systemctl list-units --all 'srv1cv8*' 'ras-*'          # старые юниты не должны быть active
# 3. (необязательно) удалить старую платформу: sudo /opt/1cv8/x86_64/$OLD/uninstaller-full --mode unattended
# 4. установка новой версии: sudo ./setup-full-$NEW-x86_64.run --mode unattended --enable-components server,ws
sudo systemctl link /opt/1cv8/x86_64/$NEW/srv1cv8-$NEW@.service
sudo systemctl link /opt/1cv8/x86_64/$NEW/ras-$NEW.service            # если используется RAS
# 5. перенести свои переопределения на новое имя юнита (если не используется общий каталог srv1cv8-@.service.d, п. 4.1):
sudo cp -a /etc/systemd/system/srv1cv8-$OLD@default.service.d /etc/systemd/system/srv1cv8-$NEW@default.service.d
grep -rn "$OLD" /etc/systemd/system/srv1cv8-$NEW@default.service.d/   # не осталось ли путей/имён со старой версией
sudo systemctl daemon-reload
# 6. сверить переменные нового вендорского юнита со своими drop-in (имена могли измениться между версиями)
systemctl cat srv1cv8-$NEW@default | grep -E '^(Environment|ExecStart|# /)'
sudo systemctl enable --now srv1cv8-$NEW@default
sudo systemctl enable --now ras-$NEW                                   # если используется RAS
systemctl status srv1cv8-$NEW@default --no-pager
systemctl list-unit-files 'srv1cv8*' 'ras-*'
```

Если drop-in не перенести, новая версия молча стартует с параметрами по умолчанию (другие порты/каталог кластера, без `After=postgresql`, без отладки). Старый каталог `srv1cv8-$OLD@default.service.d` после проверки удалите, чтобы не путаться. Если RAS используется со своим drop-in (`ras-$OLD.service.d`), его переносят так же. Альтернативы (практика): (1) общий для всех версий drop-in `/etc/systemd/system/srv1cv8-@.service.d/` (п. 4.1, с проверкой по строке `Drop-In:`); (2) собственный юнит без версии в имени, например `/etc/systemd/system/srv1cv8.service`, работающий через симлинк `/opt/1cv8/x86_64/current → <версия>`.

Журнал службы: `journalctl -u srv1cv8-8.3.27.2325@default -b -e`. Сам сервер 1С в stdout пишет мало; основная диагностика — технологический журнал (`logcfg.xml`) и журнал регистрации.

### 5.2. Сервер администрирования кластера — `ras-<версия>.service`

В каталоге платформы лежит и юнит RAS (обычный, не шаблон): `/opt/1cv8/x86_64/<версия>/ras-<версия>.service` (так в руководстве 1smonitor.ru для 8.3.27.2074 — сверено при рецензии; по данным автора статьи, так же и в руководстве interface31.ru). RAS слушает порт **1545** и подключается к агенту `localhost:1540`; с ним работают утилита `rac` и внешние панели управления. Расхождение источников: руководство k1c.proapdex.ru для 8.3.22.1750 называет файл `ras-8.3.22.1750@.service` (с `@`, т.е. шаблон) — ⚠ не подтверждено, опечатка это или отличие ранних версий; перед `link` посмотрите, что лежит у вас: `ls -l /opt/1cv8/x86_64/<версия>/*.service`. Если файл окажется шаблоном, команды ниже пишутся с экземпляром (`ras-<версия>@default`), как для сервера.

```bash
sudo systemctl link /opt/1cv8/x86_64/8.3.27.2325/ras-8.3.27.2325.service
sudo systemctl enable --now ras-8.3.27.2325.service
systemctl status ras-8.3.27.2325 --no-pager
ss -ltnp | grep 1545
/opt/1cv8/x86_64/8.3.27.2325/rac cluster list          # проверка: rac по умолчанию обращается к localhost:1545
sudo systemctl disable --now ras-8.3.27.2325           # остановить и убрать из автозапуска
```

Текст вендорского `ras-<версия>.service` в открытом доступе также не найден (⚠ не подтверждено дословно). Ближайшее, что есть, — юнит из руководства k1c.proapdex.ru для 8.3.22.1750, который автор руководства получил **копированием вендорского файла** и правкой под свой сервер (какие строки изменены, там не сказано; текст на странице «склеен» в одну строку, ниже — реконструкция):

```ini
[Unit]
Description=1C:RAS 15XX (8.3.22.1750)
Requires=network.target

[Service]
Type=simple
User=usr_1c_15
Group=grp1cv8
Environment=RAS_PORT=1545
Environment=RAS_CLUSTER_ADDRESS=localhost:1540
ExecStart=/opt/1cv8/x86_64/8.3.22.1750/ras cluster --port=${RAS_PORT} $RAS_CLUSTER_ADDRESS
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
```

Из этого следует (⚠ с той же оговоркой — проверяйте `systemctl cat ras-<версия>`): в вендорском юните порт RAS и адрес агента, вероятно, вынесены в переменные `RAS_PORT` и `RAS_CLUSTER_ADDRESS`, и менять их нужно drop-in'ом, не трогая `ExecStart`:

```ini
# sudo systemctl edit ras-8.3.27.2325.service   — перенаправить штатный RAS на агент с портом 2540
[Service]
Environment=RAS_PORT=2545
Environment=RAS_CLUSTER_ADDRESS=localhost:2540
```

Один юнит `ras-<версия>.service` — это один процесс RAS и один агент. Если RAS нужен каждому из двух экземпляров сервера, второй оформляют отдельным юнитом (копия вендорского файла в `/etc/systemd/system/ras-2x.service` со своим портом и адресом агента — так и сделано в упомянутом руководстве).

Шаблон сообщества `ras1cv83@.service` (репозиторий slothfk/1c_systemd; текст сверен при рецензии) использует другие имена переменных и хорошо показывает нужные элементы:

```ini
[Unit]
Description=1C:Enterprise Remote Administration Service (%i)
After=network.target

[Service]
Type=simple
Environment=SRV1CV8_HOST=localhost
Environment=SRV1CV8_PORT=1540
Environment=RAS1CV8_PORT=1542
ExecStart=/bin/sh -c "/opt/1cv8/x86_64/%i/ras cluster --port ${RAS1CV8_PORT} ${SRV1CV8_HOST}:${SRV1CV8_PORT}"
KillSignal=SIGINT
PrivateTmp=true
Restart=on-failure
RestartSec=5
User=usr1cv8
Group=grp1cv8

[Install]
DefaultInstance=default
WantedBy=multi-user.target
```

Замечания: `ras cluster` запускается **без** `--daemon` (`Type=simple`); порт 1542 в этом шаблоне — выбор его автора, стандартный порт RAS — 1545; `KillSignal=SIGINT` — корректная остановка `ras`. Если агент кластера слушает нестандартный порт (второй экземпляр), RAS нужно явно указать адрес агента (`ras cluster --port=1545 localhost:2540`) через drop-in с переопределением `ExecStart=` или соответствующих переменных. Логично добавить RAS зависимость `After=srv1cv8-<версия>@default.service`.

### 5.3. PostgreSQL из пакетов Ubuntu/PGDG — `postgresql@.service` и `postgresql.service`

Пакет `postgresql-common` (общий для версий 14/16/18 и репозитория PGDG) устанавливает `/usr/lib/systemd/system/postgresql@.service`, `/usr/lib/systemd/system/postgresql.service`, генератор `/usr/lib/systemd/system-generators/postgresql-generator`, а также шаблоны `pg_dump@.service/.timer`, `pg_basebackup@.service/.timer`, `pg_receivewal@.service`.

Текст `postgresql@.service` (postgresql-common 293, Debian unstable; в более старых версиях пакета отличаются детали тайм-аутов — сверяйте `systemctl cat postgresql@16-main`):

```ini
# systemd service template for PostgreSQL clusters. The actual instances will
# be called "postgresql@version-cluster", e.g. "postgresql@9.3-main". The
# variable %i expands to "version-cluster", %I expands to "version/cluster".
# (%I breaks for cluster names containing dashes.)

[Unit]
Description=PostgreSQL Cluster %i
AssertPathExists=/etc/postgresql/%I/postgresql.conf
RequiresMountsFor=/etc/postgresql/%I /var/lib/postgresql/%I
PartOf=postgresql.service
ReloadPropagatedFrom=postgresql.service
Before=postgresql.service
# stop server before networking goes down on shutdown
After=network.target

[Service]
Type=forking
# -: ignore startup failure (recovery might take arbitrarily long)
# the actual pg_ctl timeout is configured in pg_ctl.conf
ExecStart=-/usr/bin/pg_ctlcluster --skip-systemctl-redirect %i start
TimeoutStartSec=infinity
ExecStop=/usr/bin/pg_ctlcluster --skip-systemctl-redirect -m fast %i stop
TimeoutStopSec=1h
ExecReload=/usr/bin/pg_ctlcluster --skip-systemctl-redirect %i reload
PIDFile=/run/postgresql/%i.pid
SyslogIdentifier=postgresql@%i
# prevent OOM killer from choosing the postmaster (individual backends will
# reset the score to 0)
OOMScoreAdjust=-900
# restarting automatically will prevent "pg_ctlcluster ... stop" from working,
# so we disable it here. Also, the postmaster will restart by itself on most
# problems anyway, so it is questionable if one wants to enable external
# automatic restarts.
#Restart=on-failure
# (This should make pg_ctlcluster stop work, but doesn't:)
#RestartPreventExitStatus=SIGINT SIGTERM

[Install]
WantedBy=multi-user.target
```

Зонтичный `postgresql.service`:

```ini
# postgresql.service is the meta unit for managing all PostgreSQL clusters on
# the system at once. Conceptually, this unit is more like a systemd target,
# but we are using a service since targets cannot be reloaded.

[Unit]
Description=PostgreSQL RDBMS

[Service]
Type=oneshot
ExecStart=/bin/true
ExecReload=/bin/true
RemainAfterExit=on

[Install]
WantedBy=multi-user.target
```

Разбор:

| Элемент | Что означает на практике |
|---|---|
| Имя экземпляра `16-main` | `%i` = `16-main`, `%I` = `16/main` → конфигурация `/etc/postgresql/16/main/`, данные `/var/lib/postgresql/16/main/` |
| `AssertPathExists=…/postgresql.conf` | нет конфигурации кластера — запуск завершится ошибкой, а не «тихим» пропуском |
| `RequiresMountsFor=` | если данные на отдельном томе — он будет смонтирован до старта |
| `PartOf=postgresql.service` + `ReloadPropagatedFrom=` + `Before=postgresql.service` | `systemctl stop/restart/reload postgresql` распространяется на все кластеры; сам `postgresql.service` считается запущенным только после того, как отработал старт кластеров. Поэтому `After=postgresql.service` в чужом юните = «после запуска всех автозапускаемых кластеров» |
| `postgresql.service` всегда `active (exited)` | это нормально: он ничего не запускает сам. **Состояние СУБД смотрите у `postgresql@16-main`**, а не у `postgresql` |
| Генератор + `start.conf` | `postgresql-generator` при загрузке и при `daemon-reload` создаёт `/run/systemd/generator/postgresql.service.wants/postgresql@X-Y.service` для кластеров, у которых в `/etc/postgresql/X/Y/start.conf` стоит `auto`. `manual` — кластер запускается только явно; `disabled` — запуск запрещён. Поэтому `systemctl enable postgresql@16-main` обычно не нужен |
| `Type=forking` + `PIDFile=` | `pg_ctlcluster start` запускает postmaster в фоне и выходит; systemd находит главный процесс по `/run/postgresql/16-main.pid` |
| `ExecStart=-…` и `TimeoutStartSec=infinity` | ненулевой код возврата `pg_ctlcluster` игнорируется, а запуск не ограничен по времени: если `pg_ctl` не дождался готовности (долгое восстановление после сбоя), но postmaster жив — юнит считается запущенным. Если postmaster не стартовал вовсе, юнит кластера уходит в `failed`, но зонтичный `postgresql.service` всё равно остаётся `active`. Вывод: проверяйте `pg_lsclusters`, `systemctl status postgresql@16-main` и лог, а не `postgresql.service` |
| `ExecStop=… -m fast … stop`, `TimeoutStopSec=1h` | быстрая остановка (активные транзакции откатываются, сессии рвутся), systemd ждёт до часа и только потом SIGKILL |
| `ExecReload=… reload` | `systemctl reload postgresql@16-main` = `pg_reload_conf()` |
| `OOMScoreAdjust=-900` | postmaster почти никогда не будет выбран OOM-killer'ом; backend-процессы возвращают себе 0 |
| `#Restart=on-failure` (закомментировано) | авто-рестарта **нет** намеренно. Если кластер остановился (в т.ч. из-за `OOMPolicy=stop` после убийства backend'а ядром) — он останется лежать до ручного запуска |
| `--skip-systemctl-redirect` | под root `pg_ctlcluster 16 main restart` сам перенаправляется в `systemctl`, а этот ключ в юните предотвращает зацикливание |
| Журнал | сам PostgreSQL пишет в `/var/log/postgresql/postgresql-16-main.log` (а не в journald); в `journalctl -u postgresql@16-main` — только сообщения `pg_ctlcluster`/systemd |

Команды:

```bash
pg_lsclusters                                       # версии, кластеры, порты, статус, каталоги, лог-файлы
sudo systemctl status 'postgresql@*' --no-pager
sudo systemctl restart postgresql@16-main           # один кластер
sudo systemctl reload  postgresql@16-main
sudo systemctl stop postgresql                      # все кластеры
sudo pg_ctlcluster 16 main status
sudo tail -n 50 /var/log/postgresql/postgresql-16-main.log
```

Типовой drop-in для кластера под 1С (практика сообщества, не официальная рекомендация):

```ini
# sudo systemctl edit postgresql@16-main
[Service]
# не гасить весь кластер, если ядро убило по OOM один backend (postmaster сам перезапустит дочерние процессы)
OOMPolicy=continue
LimitNOFILE=65536
```

**Postgres Pro для 1С** (сборки `postgrespro-1c-NN` из репозитория Postgres Professional; на 2026-10 в `https://repo.postgrespro.ru/1c/` лежат каталоги `1c-14` … `1c-18`) не использует `postgresql-common`: нет ни `pg_lsclusters`/`pg_ctlcluster`, ни `postgresql@.service`, ни `/etc/postgresql/`. Служба называется `postgrespro-1c-<NN>.service` (например `sudo systemctl restart postgrespro-1c-15`; подтверждено практическим руководством wiki.kint.ru).

Схема размещения официально описана в документации Postgres Pro Standard («Установка двоичных пакетов в Linux») для идентификатора продукта `std-NN`; для сборки 1С тот же шаблон с идентификатором `1c-NN` (для сборки «для 1С» каталог, служба и файл подтверждены в `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, разд. 5.1; ранее: именно для `1c` по первоисточнику не сверено — документация описывает `std`; проверьте `systemctl cat postgrespro-1c-<NN>` и `cat /etc/default/postgrespro-1c-<NN>`):

| Что | Postgres Pro Standard (официально) | Сборка для 1С (по аналогии) |
|---|---|---|
| Программы | `/opt/pgpro/std-17/bin` | `/opt/pgpro/1c-<NN>/bin` |
| Каталог данных по умолчанию | `/var/lib/pgpro/std-17/data` | `/var/lib/pgpro/1c-<NN>/data` (там же `postgresql.conf`, `pg_hba.conf`) |
| Файл настроек службы (путь к каталогу данных, `PG_OOM_ADJUST_VALUE` для дочерних процессов postmaster) | `/etc/default/postgrespro-std-17` | `/etc/default/postgrespro-1c-<NN>` |
| Unit-файл | `/lib/systemd/system/postgrespro-std-17.service` | `/lib/systemd/system/postgrespro-1c-<NN>.service` |
| Инициализация и служба | `/opt/pgpro/std-17/bin/pg-setup initdb`, `pg-setup service enable`, `pg-setup service start` | то же с `1c-<NN>` |
| Программы в `PATH` | `/opt/pgpro/std-17/bin/pg-wrapper links update` | то же с `1c-<NN>` |

Сервер работает от пользователя `postgres`. В зависимостях сервера 1С (`After=`/`Wants=`) тогда указывается именно `postgrespro-1c-<NN>.service`. Drop-in для него создаётся так же (`sudo systemctl edit postgrespro-1c-<NN>`); прежде чем добавлять `OOMPolicy=`/`LimitNOFILE=`, посмотрите в `systemctl cat`, что уже задано вендором.

---

## 6. Порядок запуска: сервер 1С после сети и после PostgreSQL

Задача: при загрузке ВМ сервер 1С не должен стартовать раньше, чем поднята сеть (имена/адреса) и запущена СУБД — иначе первые подключения к базам завершаются ошибками, а рабочие процессы могут стартовать с неверно определённым сетевым окружением.

**Шаг 1. Убедиться, что `network-online.target` действительно чего-то ждёт:**

```bash
systemctl is-enabled systemd-networkd-wait-online.service    # Ubuntu Server (netplan → systemd-networkd): enabled
systemctl list-dependencies network-online.target
networkctl status                                            # состояние интерфейсов (routable?)
systemctl cat systemd-networkd-wait-online.service           # с какими параметрами ждёт (в 26.04 netplan 1.2 подставляет свою логику ожидания)
```

Если вместо networkd используется NetworkManager (десктопная установка), ту же роль играет `NetworkManager-wait-online.service`. Если ни одна «wait-online»-служба не включена, `network-online.target` достигается мгновенно и `After=network-online.target` ничего не даёт.

**Шаг 2. Drop-in для юнита сервера 1С:**

```bash
sudo systemctl edit srv1cv8-8.3.27.2325@default.service
```

```ini
[Unit]
After=network-online.target postgresql.service
Wants=network-online.target postgresql.service
```

Варианты второй зависимости:

| СУБД | Что писать в `After=` и `Wants=` |
|---|---|
| PostgreSQL из пакетов Ubuntu/PGDG, все кластеры | `postgresql.service` |
| то же, конкретный кластер | `postgresql@16-main.service` |
| Postgres Pro 1C | `postgrespro-1c-16.service` |
| СУБД на другом сервере | только `network-online.target` (локальной зависимости нет) |

**Шаг 3. Проверка:**

```bash
systemctl show -p After -p Wants -p Requires srv1cv8-8.3.27.2325@default.service
systemctl list-dependencies --after srv1cv8-8.3.27.2325@default.service | head -n 30
systemd-analyze critical-chain srv1cv8-8.3.27.2325@default.service     # после перезагрузки: реальная цепочка и времена
```

Нюансы:

- `Wants=` (а не `Requires=`) выбран намеренно: с `Requires=postgresql.service` любой `systemctl restart postgresql` автоматически перезапустит и сервер 1С (жёсткая зависимость распространяет stop/restart), а сбой старта СУБД не даст подняться 1С вовсе. Если нужно именно такое поведение — используйте `Requires=` + `After=` или `BindsTo=`.
- Порядок действует и при выключении, в обратную сторону: сервер 1С с `After=postgresql.service` будет остановлен **раньше** PostgreSQL — что и требуется.
- `After=postgresql.service` гарантирует лишь, что `pg_ctlcluster start` отработал. `pg_ctl` по умолчанию ждёт готовности сервера принимать соединения, но не дольше тайм-аута из `/etc/postgresql/16/main/pg_ctl.conf`; при долгом восстановлении после сбоя юнит кластера будет считаться запущенным раньше, чем СУБД начнёт принимать подключения. Сервер 1С в таком случае просто получит ошибки соединения с СУБД до окончания восстановления.
- Жёсткое ожидание порта (практика): `ExecStartPre=/bin/sh -c 'until pg_isready -q -h 127.0.0.1 -p 5432; do sleep 2; done'` вместе с `TimeoutStartSec=300` в drop-in сервера 1С.
- Если сервер 1С обращается к СУБД и клиентам по имени хоста — оно должно разрешаться уже на этапе загрузки (запись в `/etc/hosts`), иначе `network-online.target` не поможет.

---

## 7. Журнал systemd: journalctl и journald

`systemd-journald` собирает в единый бинарный журнал: stdout/stderr всех служб, сообщения syslog (`/dev/log`), сообщения ядра (kmsg), аудит. Каждая запись — набор полей (`MESSAGE`, `PRIORITY`, `_PID`, `_SYSTEMD_UNIT`, `_COMM`, `_BOOT_ID`…). Читать полный журнал могут root и члены групп `adm` и `systemd-journal` (первый пользователь Ubuntu входит в `adm`); остальные видят только свои записи: `sudo usermod -aG systemd-journal имя`.

### 7.1. Основные опции journalctl

| Опция | Что делает |
|---|---|
| `-u ЮНИТ` / `--unit=` | записи службы (можно несколько `-u`, можно шаблон: `-u 'postgresql@*'`) |
| `-f` / `--follow` | «хвост» в реальном времени (как `tail -f`) |
| `-e` / `--pager-end` | открыть пейджер сразу в конце; подразумевает `-n1000`. В systemd 259 (Ubuntu 26.04) по man подразумевает ещё и `--boot=0` — показываются записи только текущей загрузки; чтобы увидеть и предыдущие, укажите загрузку явно (`-b -1`) или `-b all` |
| `-n N` / `--lines=N` | последние N записей (по умолчанию 10); `-n all`; `-n +N` — первые N |
| `-r` / `--reverse` | сначала новые |
| `-b` / `--boot` | только текущая загрузка; `-b -1` — предыдущая, `-b -2` — позапрошлая; `--list-boots` — список загрузок |
| `-k` / `--dmesg` | только сообщения ядра (как `dmesg`), подразумевает `-b` |
| `-p УРОВЕНЬ` | фильтр по приоритету: `emerg`(0) `alert`(1) `crit`(2) `err`(3) `warning`(4) `notice`(5) `info`(6) `debug`(7). `-p err` — этот уровень **и важнее**; диапазон: `-p warning..err` |
| `-S` / `--since`, `-U` / `--until` | интервал времени: `"2026-10-10 08:00:00"`, `"08:00"`, `today`, `yesterday`, `now`, `-2h`, `"10 min ago"` |
| `-g ШАБЛОН` / `--grep=` | поиск по тексту сообщения (регулярное выражение PCRE2); шаблон целиком в нижнем регистре — без учёта регистра, иначе с учётом; явно: `--case-sensitive=yes` или `--case-sensitive=no` |
| `-t ТЕГ` / `--identifier=` | по syslog-идентификатору (`-t CRON`, `-t sudo`, `-t postgres`) |
| `--facility=` | по syslog-facility (`cron`, `auth`, `daemon`…) |
| `-o ФОРМАТ` | вид вывода: `short` (по умолчанию), `short-iso` (время ISO 8601), `short-precise` (микросекунды), `short-full`, `short-unix`, `short-monotonic`, `verbose` (все поля), `json`, `json-pretty`, `cat` (только текст сообщения), `with-unit`, `export` |
| `-x` / `--catalog` | добавить пояснения из каталога сообщений |
| `-a` / `--all`, `-l` / `--full` | показывать поля целиком |
| `--no-pager` | не использовать пейджер (для скриптов и перенаправления) |
| `--no-hostname`, `--utc` | без имени хоста; время в UTC |
| `-q` | без служебных предупреждений |
| `-D КАТАЛОГ`, `--file=`, `--root=` | читать журнал из другого каталога/файла (например, с примонтированного диска другой ВМ: `journalctl -D /mnt/var/log/journal`) |
| `-N`, `-F ПОЛЕ` | список имён полей; все значения поля (`journalctl -F _SYSTEMD_UNIT`) |
| `-I`, `--invocation=`, `--list-invocations` | (≥257, Ubuntu 26.04) записи только последнего/заданного запуска службы: `journalctl -u ИМЯ -I` |
| `-T ТЕГ` / `--exclude-identifier=` | (≥256) исключить идентификатор |

Фильтры по полям пишутся как `ПОЛЕ=значение`: разные поля объединяются по «И», одно и то же поле — по «ИЛИ», знак `+` между группами — «ИЛИ». Путь к исполняемому файлу вместо поля равносилен `_EXE=`.

```bash
journalctl -u srv1cv8-8.3.27.2325@default -b -e            # служба 1С, текущая загрузка, в конец
journalctl -u postgresql@16-main -f                        # следить за службой
journalctl -u ssh -u cron --since today                    # две службы за сегодня
journalctl -p err -b                                       # все ошибки с момента загрузки
journalctl -p warning..err --since "-1h" --no-pager        # предупреждения и ошибки за час
journalctl -k -b -1 -p err                                 # ошибки ядра в предыдущей загрузке
journalctl -k -g 'out of memory|oom-kill|killed process'   # следы OOM-killer
journalctl --since "2026-10-09 22:00" --until "2026-10-10 06:00" -u cron
journalctl _PID=1234                                       # по PID
journalctl _UID=$(id -u usr1cv8) -b                        # всё, что писали процессы пользователя usr1cv8
journalctl _COMM=rphost --since yesterday                  # по имени процесса
journalctl /usr/sbin/cron                                  # по пути к бинарнику
journalctl _SYSTEMD_UNIT=ssh.service + _COMM=sudo          # «или»
journalctl -u ИМЯ -o short-iso --no-pager > /tmp/unit.log   # выгрузить в файл с ISO-временем
journalctl -u ИМЯ -o json-pretty -n 1                      # одна запись со всеми полями
journalctl -u ИМЯ -o cat -n 50                             # только текст
journalctl -t CRON --since today                           # запуски заданий cron
journalctl --list-boots                                    # когда сервер перезагружался
journalctl -b -1 -e                                        # чем закончилась предыдущая загрузка (поиск причин зависания/сбоя)
```

Пейджер — `less`: `/` поиск, `G` в конец, `g` в начало, `q` выход; длинные строки обрезаны — стрелки влево/вправо или запуск с `--no-pager`. Переменные: `SYSTEMD_PAGER=cat` (без пейджера), `SYSTEMD_LESS`.

Записать своё сообщение в журнал из скрипта:

```bash
logger -t backup-1c -p user.err "pg_dump завершился с ошибкой"     # через syslog-сокет
echo "текст" | systemd-cat -t backup-1c -p info                   # stdout команды → журнал
systemd-cat -t backup-1c /usr/local/bin/backup.sh                 # обернуть команду
journalctl -t backup-1c --since today
```

### 7.2. Размер журнала и очистка

```bash
journalctl --disk-usage                       # сколько занято
sudo journalctl --rotate                      # закрыть текущие файлы и начать новые (чтобы vacuum мог удалить «активное»)
sudo journalctl --vacuum-size=500M            # удалять архивные файлы, пока суммарно не останется ≤ 500M
sudo journalctl --vacuum-time=14d             # удалить записи старше 14 дней (2weeks, 1month, 36h…)
sudo journalctl --vacuum-files=5              # оставить не более 5 архивных файлов
sudo journalctl --rotate --vacuum-time=1s     # практически полностью очистить журнал
sudo journalctl --verify                      # проверить целостность файлов
sudo journalctl --flush                       # перенести журнал из /run/log/journal в /var/log/journal
sudo journalctl --sync                        # сбросить несохранённое на диск
```

`--vacuum-*` удаляет только **архивные** (ротированные) файлы, поэтому сразу после включения лимита эффект может быть неполным — сначала `--rotate`.

### 7.3. Настройка journald: `/etc/systemd/journald.conf`

Основной файл — `/etc/systemd/journald.conf` (секция `[Journal]`, все строки закомментированы = значения по умолчанию); правильнее не править его, а класть свои файлы в `/etc/systemd/journald.conf.d/*.conf`. В Ubuntu пакет `systemd` уже содержит drop-in `/usr/lib/systemd/journald.conf.d/syslog.conf`, включающий `ForwardToSyslog=yes`.

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `Storage=` | 24.04: `auto`; 26.04: `persistent` | `persistent` — на диск в `/var/log/journal` (каталог создаётся); `auto` — на диск, только если `/var/log/journal` существует (в Ubuntu существует), иначе в память; `volatile` — только `/run/log/journal` (теряется при перезагрузке); `none` — не хранить (пересылка продолжает работать) |
| `Compress=` | `yes` | сжимать объекты крупнее 512 байт |
| `SystemMaxUse=` | 10% ФС, но не более 4G | максимум места под журнал в `/var/log/journal` |
| `SystemKeepFree=` | 15% ФС, но не более 4G | сколько оставлять свободным на ФС |
| `SystemMaxFileSize=` | 1/8 от `SystemMaxUse` (не более 128M) | размер одного файла до ротации |
| `SystemMaxFiles=` | 100 | максимум архивных файлов |
| `RuntimeMaxUse=`, `RuntimeKeepFree=`, … | аналогично | то же для `/run/log/journal` |
| `MaxRetentionSec=` | 0 (выкл.) | удалять записи старше срока (`1month`, `2week`) |
| `MaxFileSec=` | `1month` | принудительная ротация файла по времени |
| `SyncIntervalSec=` | `5m` | период сброса на диск (сообщения crit и важнее — сразу) |
| `RateLimitIntervalSec=`, `RateLimitBurst=` | `30s`, `10000` | лимит на службу: не более 10000 сообщений за 30 с, лишнее отбрасывается с записью «Suppressed N messages from …»; `0` — отключить |
| `ForwardToSyslog=` | upstream `no`; **в Ubuntu `yes`** (drop-in `syslog.conf`) | пересылать сообщения в сокет `/run/systemd/journal/syslog`, который читает rsyslog |
| `ForwardToKMsg=`, `ForwardToConsole=`, `ForwardToWall=` | `no`, `no`, `yes` | пересылка в буфер ядра / на консоль (`TTYPath=`) / всем терминалам (только emerg) |
| `MaxLevelStore=`, `MaxLevelSyslog=`, `MaxLevelKMsg=`, `MaxLevelConsole=`, `MaxLevelWall=` | `debug`, `debug`, `notice`, `info`, `emerg` | максимальный уровень детализации, попадающий в хранилище / пересылку |
| `SplitMode=` | `uid` | отдельные файлы журнала на каждого обычного пользователя |
| `Seal=` | `yes` | криптографическая «печать» (если созданы ключи `journalctl --setup-keys`) |
| `LineMax=` | `48K` | максимальная длина строки из stdout службы |
| `Audit=` | `yes` | включать ли аудит ядра |

Пример: ограничить журнал 1 ГБ и 30 днями:

```bash
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/10-size.conf >/dev/null <<'EOF'
[Journal]
SystemMaxUse=1G
SystemMaxFileSize=100M
MaxRetentionSec=1month
EOF
sudo systemctl restart systemd-journald
systemd-analyze cat-config systemd/journald.conf      # итоговая конфигурация со всеми drop-in
journalctl --disk-usage
```

Если rsyslog не нужен и хочется избавиться от дублирования записей (journal + `/var/log/syslog`), можно либо удалить `rsyslog`, либо задать `ForwardToSyslog=no` в своём drop-in с именем, сортирующимся после `syslog.conf` (в `/etc/systemd/journald.conf.d/` файлы из `/etc` и `/usr/lib` сортируются вместе по имени; одноимённый файл в `/etc` перекрывает вендорский).

---

## 8. rsyslog и текстовые журналы в /var/log

### 8.1. Как это устроено в Ubuntu

`journald` получает все сообщения и (благодаря `ForwardToSyslog=yes`) дублирует их в сокет `/run/systemd/journal/syslog`; `rsyslog.service` (запускается через `syslog.socket`, модуль `imuxsock`; сообщения ядра — модуль `imklog`) раскладывает их по текстовым файлам согласно правилам. Конфигурация: `/etc/rsyslog.conf` (глобальные параметры, `$IncludeConfig /etc/rsyslog.d/*.conf`) и `/etc/rsyslog.d/50-default.conf` (правила Ubuntu). Файлы принадлежат `syslog:adm`, права `0640` — читать могут члены группы `adm`.

Правило имеет вид `facility.priority  действие`: facility — `auth, authpriv, cron, daemon, kern, mail, user, local0…local7, *`; priority — `debug, info, notice, warning, err, crit, alert, emerg, *, none`; «`-`» перед путём — без синхронной записи на диск.

Правила Ubuntu в `/etc/rsyslog.d/50-default.conf` (состав сверен при рецензии по файлу `50-default.conf` из репозитория upstream-сборок rsyslog для Ubuntu noble, который повторяет дистрибутивный; сам файл из архива Ubuntu прочитать не удалось — git.launchpad.net недоступен, поэтому в своей версии всё же сверяйте: `grep -v '^\s*#' /etc/rsyslog.d/50-default.conf`):

```
auth,authpriv.*                 /var/log/auth.log
*.*;auth,authpriv.none          -/var/log/syslog
#cron.*                         /var/log/cron.log
#daemon.*                       -/var/log/daemon.log
kern.*                          -/var/log/kern.log
#lpr.*                          -/var/log/lpr.log
mail.*                          -/var/log/mail.log
#user.*                         -/var/log/user.log
mail.err                        /var/log/mail.err
*.emerg                         :omusrmsg:*
```

Особенности конфигурации Ubuntu (по changelog пакета rsyslog 8.2312.0-3ubuntu9.x для 24.04): демон работает от непривилегированного пользователя `syslog` (поэтому файлы принадлежат `syslog:adm`), включён профиль AppArmor, а в `/etc/rsyslog.conf` включён `$RepeatedMsgReduction on` — подряд идущие одинаковые сообщения сворачиваются в одну строку вида `message repeated N times: [ … ]` (учитывайте при подсчёте событий `grep`-ом; в журнале journald свёртки нет).

После правки: `sudo rsyslogd -N1` (проверка синтаксиса) и `sudo systemctl restart rsyslog` (SIGHUP конфигурацию **не** перечитывает — только переоткрывает файлы).

### 8.2. Что где лежит

| Файл / каталог | Содержимое | Кто пишет |
|---|---|---|
| `/var/log/syslog` | всё, кроме auth (общий системный журнал; сюда же попадают запуски cron) | rsyslog |
| `/var/log/auth.log` | входы, `sudo`, `su`, `sshd`, PAM | rsyslog |
| `/var/log/kern.log` | сообщения ядра (OOM-killer, диски, сеть) | rsyslog |
| `/var/log/dmesg` | сообщения ядра при загрузке | `dmesg.service` (из пакета rsyslog) |
| `/var/log/dpkg.log` | установка/удаление/настройка пакетов dpkg | dpkg |
| `/var/log/apt/history.log`, `/var/log/apt/term.log` | история команд apt и их вывод | apt |
| `/var/log/unattended-upgrades/` | автоматические обновления | unattended-upgrades |
| `/var/log/cloud-init.log`, `/var/log/cloud-init-output.log` | первичная настройка образа | cloud-init |
| `/var/log/journal/` | бинарный журнал systemd (читать `journalctl`) | journald |
| `/var/log/postgresql/postgresql-<версия>-<кластер>.log` | лог PostgreSQL (пакеты Ubuntu/PGDG) | postgres |
| `/var/log/apache2/access.log`, `error.log` | веб-сервер (публикация баз 1С) | apache2 |
| `/var/log/wtmp`, `/var/log/btmp`, `/var/log/lastlog` | бинарные журналы входов — читать `last`, `sudo lastb`, `lastlog` | login/sshd |
| `/var/log/installer/` | журнал установки ОС | subiquity |

```bash
sudo tail -f /var/log/syslog
sudo grep -i 'failed password' /var/log/auth.log | tail
sudo grep CRON /var/log/syslog | tail -n 20
zgrep -h 'install ' /var/log/dpkg.log* | tail          # zgrep/zcat/zless читают и .gz-архивы после ротации
less +G /var/log/apt/history.log
```

В Ubuntu 24.04+ метки времени в `/var/log/syslog` и `auth.log` имеют вид RFC 3339/ISO 8601 с микросекундами и часовым поясом (`2026-10-10T08:15:02.123456+05:00`), в 22.04 — традиционный вид `Oct 10 08:15:02`. Подтверждено changelog пакета: изменение пришло из Debian в версии rsyslog 8.2210.0-3 («Enable high precision timestamps with timezone information», в Debian — по умолчанию с 12 bookworm) и присутствует в истории пакета Ubuntu 24.04 (8.2312.0); 22.04 поставляет более старую версию. Учитывайте при написании парсеров и при `grep` по дате: в 24.04+ ищите `grep '^2026-10-10T08:' /var/log/syslog`, в 22.04 — `grep '^Oct 10 08:'`. Вернуть старый формат можно строкой `$ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat` в `/etc/rsyslog.conf` (⚠ на 24.04/26.04 не проверялось; без необходимости не меняйте — новый формат однозначен и сортируется).

Отдельный файл для cron: раскомментировать строку `cron.*` в `50-default.conf` и перезапустить rsyslog. Отдельный файл для своей программы — по тегу:

```
# /etc/rsyslog.d/30-backup-1c.conf
:programname, isequal, "backup-1c"    /var/log/backup-1c.log
& stop
```

---

## 9. logrotate — ротация текстовых логов

### 9.1. Как запускается

- Конфигурация: `/etc/logrotate.conf` (глобальные значения + `include /etc/logrotate.d`) и по файлу на приложение в `/etc/logrotate.d/`.
- Запуск: раз в сутки таймером `logrotate.timer` → `logrotate.service` (`ExecStart=/usr/sbin/logrotate /etc/logrotate.conf`). Файл `/etc/cron.daily/logrotate` оставлен для систем без systemd и при работающем systemd ничего не делает.
- Состояние (когда какой файл ротировался): `/var/lib/logrotate/status`.
- Версии (подтверждено packages.ubuntu.com): 3.19.0 (22.04), 3.21.0 (24.04), 3.22.0 (26.04).

```bash
systemctl list-timers logrotate.timer          # когда был и когда будет следующий запуск
systemctl cat logrotate.timer logrotate.service
journalctl -u logrotate --since "-3d"          # ошибки ротации
sudo cat /var/lib/logrotate/status | head
```

Таймер. В logrotate 3.18–3.21 (исходники Debian 11/12; та же upstream-версия 3.21.0 в Ubuntu 24.04, и, по-видимому, 3.19 в 22.04) секция выглядит так:

```ini
[Timer]
OnCalendar=daily
AccuracySec=1h
Persistent=true
```

В logrotate 3.22 (Debian unstable; та же upstream-версия в Ubuntu 26.04) вместо `AccuracySec=1h` стоит `RandomizedDelaySec=1h`:

```ini
[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true
```

В обоих случаях ротация происходит раз в сутки в интервале примерно 00:00–01:00 местного времени (точный момент не гарантирован); `Persistent=true` — если сервер в полночь был выключен, logrotate выполнится после включения. Фактический текст в своей системе: `systemctl cat logrotate.timer`.

Важно: `logrotate.service` работает в «песочнице» (`ProtectSystem=full`, `PrivateTmp=true`, `PrivateDevices=true` и др.): каталоги `/usr`, `/boot`, `/efi`, `/etc` для него только на чтение. Логи под `/var`, `/opt`, `/home` ротируются нормально; скрипты `postrotate` выполняются в том же окружении (например, не видят общий `/tmp`).

Глобальный `/etc/logrotate.conf` в Ubuntu (суть): `weekly`, `su root adm`, `rotate 4`, `create`, закомментированные `dateext` и `compress`, `include /etc/logrotate.d`.

### 9.2. Структура конфигурации и директивы

```
/путь/к/логу1.log /путь/к/каталогу/*.log {
    директива
    директива значение
    postrotate
        команды shell
    endscript
}
```

| Директива | Смысл |
|---|---|
| `daily` / `weekly` / `monthly` / `yearly` | период ротации. `hourly` работает, только если сам logrotate запускается каждый час (см. ниже) |
| `rotate N` | хранить N старых файлов (0 — удалять сразу; по умолчанию 0) |
| `size 100M` | ротировать, когда файл больше размера, **игнорируя** период |
| `minsize 10M` | по периоду, но только если файл не меньше размера |
| `maxsize 500M` | по периоду **или** раньше, если превышен размер (проверка происходит при запуске logrotate, т.е. обычно раз в сутки) |
| `maxage N` | удалять ротированные файлы старше N дней |
| `minage N` | не ротировать файлы моложе N дней |
| `compress` / `nocompress` | сжимать старые файлы (gzip; `compresscmd`, `compressext`, `compressoptions` — другой архиватор, напр. `compresscmd /usr/bin/zstd`, `compressext .zst`) |
| `delaycompress` | сжимать не только что ротированный файл, а со следующего цикла (программа может ещё дописывать в `.1`) |
| `create 0640 user group` | после переименования создать новый пустой файл с правами/владельцем |
| `nocreate` | не создавать (программа создаст сама) |
| `copytruncate` | **скопировать** лог и обрезать оригинал до нуля — для программ, которые держат файл открытым и не умеют его переоткрывать. Между копированием и обрезкой возможна потеря нескольких строк |
| `copy` | только копия, оригинал не трогать |
| `missingok` | не считать ошибкой отсутствие файла |
| `notifempty` / `ifempty` | не ротировать / ротировать пустой файл |
| `dateext`, `dateformat -%Y%m%d`, `dateyesterday` | суффикс-дата вместо номера (`app.log-20261010.gz`) |
| `olddir /путь` | складывать старые файлы в другой каталог (на той же ФС, если не `copy`/`copytruncate`) |
| `su user group` | выполнять ротацию от имени пользователя/группы (обязательно, если каталог логов доступен на запись не только root — иначе ошибка «parent directory has insecure permissions») |
| `sharedscripts` | выполнить `prerotate`/`postrotate` один раз на весь блок, а не для каждого файла |
| `prerotate` / `postrotate` / `firstaction` / `lastaction` / `preremove` … `endscript` | скрипты (`/bin/sh`): до ротации, после, до всех, после всех, перед удалением старого файла |
| `shred` | затирать при удалении |
| `include /путь` | подключить файл/каталог; файлы с расширениями из `tabooext` (`.dpkg-old`, `.bak`, `~` и др.) пропускаются |

Два способа «отпустить» файл: (1) `create` + `postrotate` с сигналом программе переоткрыть лог (правильный: без потерь); (2) `copytruncate` (когда сигнала нет).

### 9.3. Проверка и принудительный запуск

```bash
sudo logrotate -d /etc/logrotate.d/postgresql-common    # -d (debug): только показать, что БЫЛО БЫ сделано; ничего не меняет и status не обновляет
sudo logrotate -d /etc/logrotate.conf 2>&1 | less       # проверить всю конфигурацию
sudo logrotate -v /etc/logrotate.conf                   # выполнить с подробным выводом
sudo logrotate -f /etc/logrotate.d/myapp                # -f (force): ротировать принудительно, даже если «ещё не пора»
sudo logrotate -vf -s /tmp/lr.status /etc/logrotate.d/myapp   # с отдельным файлом состояния (для экспериментов)
sudo systemctl start logrotate.service                  # запустить штатный прогон сейчас (в той же «песочнице», что и по таймеру)
```

Требования к файлам в `/etc/logrotate.d/`: владелец root, права `0644` (файл с правом записи для группы/всех игнорируется с ошибкой), без расширений из taboo-списка.

Чтобы работали `hourly`/частая проверка `size`, запускайте logrotate чаще:

```bash
sudo systemctl edit logrotate.timer
```

```ini
[Timer]
OnCalendar=
OnCalendar=hourly
```

### 9.4. Примеры

Свой сервис, умеющий переоткрывать лог по сигналу:

```
/var/log/myapp/*.log {
    daily
    rotate 14
    maxsize 200M
    compress
    delaycompress
    missingok
    notifempty
    create 0640 myapp adm
    su myapp adm
    sharedscripts
    postrotate
        systemctl kill -s HUP myapp.service 2>/dev/null || true
    endscript
}
```

Системные журналы rsyslog (`/etc/logrotate.d/rsyslog`, суть): `rotate 4`, `weekly`, `missingok`, `notifempty`, `compress`, `delaycompress`, `sharedscripts`, `postrotate /usr/lib/rsyslog/rsyslog-rotate endscript`.

**PostgreSQL (пакеты Ubuntu/PGDG)** — штатный `/etc/logrotate.d/postgresql-common`:

```
/var/log/postgresql/*.log {
       weekly
       rotate 10
       copytruncate
       delaycompress
       compress
       notifempty
       missingok
       su root root
}
```

Здесь `copytruncate`, потому что лог пишется через перенаправление stderr, открытое `pg_ctlcluster` при старте (`logging_collector = off` по умолчанию в пакетах Debian/Ubuntu), и «переоткрыть» его PostgreSQL не может. На сервере 1С с подробным журналированием (`log_min_duration_statement`, `log_lock_waits`, `auto_explain`) недельной ротации мало. Положить рядом второй файл с тем же шаблоном нельзя: один и тот же лог не может описываться двумя блоками (ошибка «duplicate log entry»; в man logrotate 3.21 (24.04+) есть директива `ignoreduplicates` — «Ignore any following matches of a log file», но строить на ней переопределение пакетного файла ненадёжно: всё зависит от порядка чтения файлов). Поэтому правят сам `/etc/logrotate.d/postgresql-common` (это conffile: при обновлении пакета dpkg спросит, оставить ли вашу версию), например так:

```
/var/log/postgresql/*.log {
       daily
       rotate 14
       maxsize 1G
       copytruncate
       compress
       delaycompress
       notifempty
       missingok
       su root root
}
```

Альтернатива без logrotate — встроенный сборщик PostgreSQL (`logging_collector = on`, `log_directory`, `log_filename = 'postgresql-%a.log'`, `log_rotation_age = 1d`, `log_truncate_on_rotation = on` дают «кольцо» из 7 файлов по дням недели). Тогда PostgreSQL ротирует сам, а logrotate этим файлам не нужен. В сборках Postgres Pro логи по умолчанию лежат не в `/var/log/postgresql` (⚠ не подтверждено: обычно каталог `log` внутри каталога данных) — проверьте `SHOW log_directory; SHOW logging_collector;`.

**Технологический журнал 1С.** Платформа ротирует его сама: файлы создаются по одному на час (`ГГММДДЧЧ.log`) в подкаталогах `<процесс>_<PID>` и удаляются по истечении числа часов из атрибута `history` элемента `<log location="…" history="…">` в `logcfg.xml`. Отсюда правила:

1. Глубину хранения задавайте `history`, а не logrotate.
2. Не сжимайте и не складывайте ничего постороннего **внутри** каталога ТЖ: по документации 1С каталог ТЖ не предназначен для посторонних файлов, и при их обнаружении платформа может перестать вести журнал в этом каталоге (⚠ формулировка по памяти из закрытой документации ИТС — перечитайте раздел о технологическом журнале в «Руководстве администратора»).
3. Не используйте для ТЖ `copytruncate`, `create`, `olddir` внутри того же дерева — платформа сама открывает/закрывает часовые файлы.

Если всё же нужна «страховочная» чистка (например, ТЖ отключили, а старые файлы остались: по практическим наблюдениям платформа чистит каталог, только пока журнал включён), делайте **только удаление** старых файлов. Вариант на logrotate (файлы старше 3 суток удаляются; `rotate 0` означает «не хранить ротированные копии»):

```
/var/log/1c/tj/*/*.log {
    daily
    minage 3
    rotate 0
    missingok
    nocreate
    su usr1cv8 grp1cv8
}
```

⚠ Вариант с logrotate приведён как иллюстрация директив и на стенде не проверялся. У него есть побочные эффекты: каждый часовой файл ТЖ попадает в файл состояния `/var/lib/logrotate/status` (тысячи записей); файл, увиденный logrotate впервые, при периодической ротации (`daily`) в этот же прогон, как правило, не обрабатывается (сначала он лишь заносится в файл состояния); `minage` считается по времени изменения файла. Перед применением обязательно прогоните `sudo logrotate -d /etc/logrotate.d/1c-tj` и убедитесь, что текущий (ещё записываемый) часовой файл не затрагивается. **Рекомендуемый способ** — одна команда `find` в cron/таймере или правило tmpfiles (раздел 14):

```bash
# сначала посмотреть, что будет удалено (без -delete), и только потом выполнять
find /var/log/1c/tj -type f -name '*.log' -mtime +3 -print | head
find /var/log/1c/tj -type f -name '*.log' -mtime +3 -delete
# пустые каталоги процессов — только «старые»: каталог только что запущенного процесса может быть ещё пуст
find /var/log/1c/tj -mindepth 1 -type d -empty -mtime +3 -delete
```

(`-mtime +3` — файл не изменялся более трёх полных суток, т.е. фактически старше 4 суток. Путь `/var/log/1c/tj` — пример: подставьте каталог из атрибута `location` своего `logcfg.xml` и **никогда не запускайте `find … -delete` с переменной, которая может оказаться пустой**.)

Архивирование ТЖ для разбора — копированием **в другой каталог** (`tar -czf /backup/tj-$(date +%F).tar.gz -C /var/log/1c tj`), не трогая оригиналы.

Прочие логи вокруг 1С, которым logrotate действительно нужен: логи Apache (`/etc/logrotate.d/apache2` ставится пакетом), логи собственных скриптов резервного копирования/обслуживания, файлы, в которые вы перенаправляете вывод `rac`/`ibcmd` из cron.

---

## 10. cron, anacron, at

### 10.1. cron в Ubuntu

Пакет `cron` — классический Vixie cron 3.0pl1 с патчами Debian (подтверждено packages.ubuntu.com — 22.04: 3.0pl1-137ubuntu3, 24.04: 3.0pl1-184ubuntu2, 26.04: 3.0pl1-200ubuntu1). Служба — **`cron.service`** (не `crond`): `ExecStart=/usr/sbin/cron -f $EXTRA_OPTS`, параметры из `/etc/default/cron` (`EnvironmentFile=-/etc/default/cron`), `KillMode=process` (перезапуск cron не убивает уже запущенные задания), `Restart=on-failure`, `After=remote-fs.target nss-user-lookup.target`.

Осторожно с документацией: в архиве Ubuntu есть и другой планировщик — пакет `cronie` (по умолчанию **не** установлен). Страница `crontab(5)` на manpages.ubuntu.com для noble отдаётся именно из пакета cronie (в шапке «Provided by: cronie»), а его синтаксис и возможности отличаются (в man cronie прямо разрешены диапазоны и списки имён — `mon,wed,fri`, `jan-mar`; у cronie есть и свои переменные, например `CRON_TZ`, которых в cron Debian/Ubuntu нет: по man `cron(8)` он работает только в одном часовом поясе — системном). Справка по установленному у вас cron — локальная: `man 5 crontab`, `man 8 cron`, `dpkg -S /usr/sbin/cron`; в сети — manpages.debian.org (пакет `cron`).

```bash
systemctl status cron
sudo systemctl restart cron          # обычно не требуется: cron сам замечает изменения crontab-файлов раз в минуту
```

Где лежат задания:

| Место | Формат | Назначение |
|---|---|---|
| `/var/spool/cron/crontabs/<пользователь>` | 5 полей времени + команда | личные crontab; **редактировать только через `crontab`** |
| `/etc/crontab` | 5 полей + **пользователь** + команда | системный crontab; `crontab`-командой не устанавливается, правится редактором |
| `/etc/cron.d/*` | как `/etc/crontab` | задания пакетов и администратора; каждый файл независим (своё окружение) |
| `/etc/cron.hourly/`, `cron.daily/`, `cron.weekly/`, `cron.monthly/` | исполняемые скрипты | запускаются через `run-parts` из `/etc/crontab` |

Штатный `/etc/crontab` (актуальные версии пакета; в старых вместо `{ …; }` стоят круглые скобки `( … )`):

```
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

17 *    * * *   root    cd / && run-parts --report /etc/cron.hourly
25 6    * * *   root    test -x /usr/sbin/anacron || { cd / && run-parts --report /etc/cron.daily; }
47 6    * * 7   root    test -x /usr/sbin/anacron || { cd / && run-parts --report /etc/cron.weekly; }
52 6    1 * *   root    test -x /usr/sbin/anacron || { cd / && run-parts --report /etc/cron.monthly; }
```

То есть: hourly — в 17 минут каждого часа, daily — 06:25, weekly — 06:47 по воскресеньям, monthly — 06:52 первого числа; если установлен anacron, три последних выполняет он.

Правила именования (частая причина «задание не запускается»):

- файлы в `/etc/cron.d/` и скрипты в `/etc/cron.{hourly,daily,weekly,monthly}/` должны состоять **только из букв, цифр, `_` и `-`**. Файл с точкой в имени (`backup.sh`, `job.cron`, `*.dpkg-old`) молча игнорируется;
- файлы `/etc/crontab` и `/etc/cron.d/*` — владелец root, без права записи для группы и остальных (`0644`); бит исполнения не нужен;
- скрипты в `cron.daily` и т.п. — исполняемые (`chmod 755`) и с корректным shebang.

Проверка, что `run-parts` «видит» скрипты: `run-parts --test /etc/cron.daily`.

### 10.2. Команда crontab

| Команда | Действие |
|---|---|
| `crontab -e` | редактировать свой crontab (редактор — `sensible-editor`: `$VISUAL`, `$EDITOR`, выбор через `select-editor`); при сохранении проверяется синтаксис |
| `crontab -l` | показать |
| `crontab -r` | **удалить весь** crontab без подтверждения (клавиши `e` и `r` рядом!) |
| `crontab -i -r` | удалить с подтверждением |
| `crontab файл` | установить crontab из файла (заменяет существующий целиком); `crontab -` — из stdin |
| `crontab -n файл` | «dry run»: только проверить синтаксис файла, ничего не устанавливая (подтверждено man `crontab(1)` пакета cron 3.0pl1-197, Debian 13; в 26.04 есть, в 22.04/24.04 ⚠ наличие опции не сверялось — проверьте `man crontab`) |
| `sudo crontab -u postgres -e` / `-l` / `-r` | crontab другого пользователя (только root) |

```bash
crontab -l > ~/crontab.bak                    # резервная копия перед правкой
sudo crontab -u postgres -l
(crontab -l 2>/dev/null; echo '30 2 * * * /usr/local/bin/job.sh') | crontab -    # добавить строку из скрипта
sudo ls -l /var/spool/cron/crontabs/          # у кого вообще есть crontab
```

Доступ: если есть `/etc/cron.allow` — пользоваться `crontab` могут только перечисленные в нём; иначе, если есть `/etc/cron.deny` — все, кроме перечисленных; если нет ни одного файла — в Debian/Ubuntu разрешено всем. root — всегда.

### 10.3. Формат строки

```
# ┌──────── минута (0-59)
# │ ┌────── час (0-23)
# │ │ ┌──── день месяца (1-31)
# │ │ │ ┌── месяц (1-12 или jan..dec)
# │ │ │ │ ┌ день недели (0-7; 0 и 7 — воскресенье; или sun..sat)
# │ │ │ │ │
  * * * * *  команда                (личный crontab)
  * * * * *  пользователь команда   (/etc/crontab и /etc/cron.d/*)
```

| Запись | Смысл |
|---|---|
| `*` | любое значение |
| `5,35` | список |
| `8-18` | диапазон |
| `*/10`, `0-23/2` | шаг (каждые 10 минут; каждые 2 часа) |
| `@reboot` | один раз при старте cron (после загрузки) |
| `@hourly`, `@daily` (`@midnight`), `@weekly`, `@monthly`, `@yearly` (`@annually`) | `0 * * * *`, `0 0 * * *`, `0 0 * * 0`, `0 0 1 * *`, `0 0 1 1 *` |

Примеры:

```
# каждый день в 02:30 — логический дамп базы от имени postgres (строка для /etc/cron.d/pg-backup)
# (лог — в /var/log/postgresql/: туда пользователь postgres может писать, и штатный logrotate подхватит *.log)
30 2 * * *   postgres  /usr/local/bin/pg-backup-1c.sh buh >>/var/log/postgresql/pg-backup-1c.log 2>&1
# каждые 15 минут в рабочее время по будням
*/15 8-18 * * 1-5  /usr/local/bin/check.sh
# 1-го числа в 03:00
0 3 1 * *  /usr/local/bin/monthly.sh
# по воскресеньям в 04:00 — VACUUM ANALYZE (строка для crontab пользователя postgres)
0 4 * * 0  vacuumdb --all --analyze --quiet
# файл с датой в имени: знак % экранируется!
0 1 * * *  tar czf /backup/etc-$(date +\%F).tar.gz /etc
```

Особенности формата:

- **День месяца и день недели объединяются по «ИЛИ»**, если оба заданы не `*`: `30 4 1,15 * 5` = 04:30 1-го и 15-го числа **и** каждую пятницу.
- **`%` в команде — спецсимвол**: неэкранированный `%` превращается в перевод строки, а всё после первого `%` подаётся команде на stdin. В командах с `date +%F` пишите `\%`, либо вынесите команду в скрипт.
- Секунд нет; минимальный шаг — минута. Шаг считается внутри поля: `*/35` в минутах — это 0-я и 35-я минуты каждого часа, а не «каждые 35 минут».
- Каждая запись, включая последнюю, должна заканчиваться переводом строки — иначе cron считает crontab повреждённым.
- Комментарий — только отдельной строкой с `#` в начале; после команды `#` станет частью команды для shell.
- Файл с окончаниями строк Windows (CRLF) cron не понимает (`bad minute` / команда с `\r` на конце) — при переносе с Windows-хоста: `sed -i 's/\r$//' файл`.
- Диапазоны и списки из **названий** (`mon-fri`, `mon,wed`) в cron Debian/Ubuntu формально не поддерживаются: в man `crontab(5)` пакета cron (22.04: 3.0pl1-137; Debian 13: 3.0pl1-197) сказано «Ranges or lists of names are not allowed» — используйте числа `1-5`. Одиночное имя (`sun`, `jan`) допустимо.
- Перевод часов (cron(8)): при сдвиге времени менее чем на 3 часа задания из «пропущенного» интервала выполняются вскоре после перевода, а задания из «повторившегося» интервала повторно не запускаются; сдвиг более 3 часов считается коррекцией часов, новое время применяется сразу. cron работает только в одном часовом поясе — системном (`/etc/localtime`).

### 10.4. Окружение cron — главная причина «в консоли работает, в cron — нет»

Задание запускается через `/bin/sh -c 'команда'` (в Ubuntu `/bin/sh` — это **dash**, не bash) с минимальным окружением:

| Переменная | Значение по умолчанию |
|---|---|
| `SHELL` | `/bin/sh` |
| `PATH` | в личных crontab и в файлах `/etc/cron.d/*` без собственной строки `PATH=` — **`/usr/bin:/bin`**. Подтверждено исходным кодом пакета cron: демон при старте делает `setenv("PATH", _PATH_DEFPATH, 1)`, где `_PATH_DEFPATH` = `"/usr/bin:/bin"` (`cron.c`, `pathnames.h`), а задания, по man 22.04, получают PATH «inherited from the environment» демона. Актуальные man-страницы значение не называют. `PATH` из `/etc/environment` на задания **не** действует (man: настройки PAM не перекрывают эти значения). В `/etc/crontab` полный PATH задан явно, но на `/etc/cron.d/*` он не распространяется (каждый файл самостоятелен) |
| `HOME`, `LOGNAME` | из `/etc/passwd` владельца crontab |
| `MAILTO` | не задана — вывод задания отправляется почтой владельцу; `MAILTO=""` — не отправлять; `MAILTO=admin@example.org` — на адрес |

Не читаются `~/.bashrc`, `~/.profile`, `/etc/profile`; нет терминала; рабочий каталог — домашний каталог пользователя. Переменные задаются строками в начале crontab (действуют на записи ниже):

```
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""
PGHOST=/var/run/postgresql

30 2 * * *  /usr/local/bin/pg-backup-1c.sh
```

В строках окружения **нет подстановок**: `PATH=$HOME/bin:$PATH` не сработает (значение берётся буквально). Отладка окружения:

```
* * * * *  env > /tmp/cron-env.txt 2>&1
```

Почта: если MTA (postfix и т.п.) не установлен, вывод заданий отбрасывается, а в журнале появляется `(CRON) info (No MTA installed, discarding output)`. Поэтому **всегда перенаправляйте вывод сами**: `>>/var/log/имя.log 2>&1` (и настройте этому файлу logrotate) или `2>&1 | logger -t имя`.

Лимиты `/etc/security/limits.conf` на задания cron действуют (cron открывает PAM-сеанс, `/etc/pam.d/cron`), в отличие от служб systemd.

### 10.5. Журналирование и диагностика cron

```bash
journalctl -u cron --since today                 # запуски: "(postgres) CMD (/usr/local/bin/pg-backup-1c.sh)"
journalctl -t CRON --since "-2h"
grep CRON /var/log/syslog | tail -n 30           # то же в текстовом виде (отдельный /var/log/cron.log по умолчанию выключен)
```

По умолчанию cron записывает только факт **запуска** задания. Уровень задаётся в `/etc/default/cron`: `EXTRA_OPTS="-L 5"` — сумма флагов: 1 — запуск, 2 — завершение, 4 — задания с ненулевым кодом возврата, 8 — PID; `-L 15` — всё. После правки `sudo systemctl restart cron`.

Типовые ошибки cron:

| Симптом | Причина | Решение |
|---|---|---|
| В журнале есть `CMD (…)`, но результата нет | команда не найдена из-за короткого `PATH=/usr/bin:/bin`: всё из `/usr/sbin`, `/sbin`, `/usr/local/bin`, а также `rac`, `ibcmd` (`/opt/1cv8/x86_64/<версия>/`) и утилиты Postgres Pro (`/opt/pgpro/1c-<NN>/bin/pg_dump`). `pg_dump`/`psql` из пакетов Ubuntu/PGDG лежат в `/usr/bin` и находятся | полные пути к программам или `PATH=` в начале crontab |
| Скрипт работает вручную, из cron — нет | рассчитывает на `~/.bashrc`, переменные (`PGPASSWORD`, `LANG`), текущий каталог, терминал | задать всё в самом скрипте: `cd`, `export`, `set -euo pipefail`; пароли — в `~/.pgpass` (0600) |
| Команда с `date +%F` обрывается | неэкранированный `%` | `\%` или вынести в скрипт |
| `bad minute`, `errors in crontab file, can't install` | синтаксис, CRLF, нет перевода строки в конце | исправить; `sed -i 's/\r$//'` |
| Файл в `/etc/cron.d` игнорируется | точка в имени, права шире 0644, владелец не root, нет поля пользователя | переименовать, `chown root:root`, `chmod 644`, добавить пользователя |
| Скрипт в `/etc/cron.daily` не выполняется | имя с точкой (`.sh`), нет бита `x`, установлен anacron и ждёт своего времени | `run-parts --test /etc/cron.daily` |
| `[[: not found`, `Syntax error: "(" unexpected` | bash-синтаксис в `/bin/sh` (dash) | `SHELL=/bin/bash` в crontab или запуск `bash /путь/скрипт` / shebang `#!/bin/bash` |
| Задание запускается дважды / накладывается само на себя | прошлый запуск не успел завершиться | `flock -n /run/lock/имя.lock команда` |
| Нет никаких следов запуска | служба cron остановлена; системное время/часовой пояс не те; ошибка в файле | `systemctl status cron`, `timedatectl`, `journalctl -u cron` |
| После смены часового пояса задания идут по старому времени | cron прочитал пояс при старте | `sudo systemctl restart cron` |
| Задание `@reboot` стартует до сети/СУБД | cron запускается рано | `sleep 60 && …` или лучше — юнит/таймер systemd с `After=` |

### 10.6. anacron

Нужен на машинах, которые работают не круглосуточно: выполняет «ежедневные/еженедельные/ежемесячные» задания, если они были пропущены. На постоянно включённом сервере не нужен и по умолчанию **не установлен** (`sudo apt install anacron`).

- Конфигурация `/etc/anacrontab`: `период_в_днях  задержка_мин  идентификатор  команда`. Штатно:

  ```
  1         5   cron.daily     run-parts --report /etc/cron.daily
  7         10  cron.weekly    run-parts --report /etc/cron.weekly
  @monthly  15  cron.monthly   run-parts --report /etc/cron.monthly
  ```

- Отметки о выполнении — `/var/spool/anacron/<идентификатор>` (дата последнего запуска).
- Запускается таймером `anacron.timer` (ежечасно с 07:30 до 23:30) и при загрузке; по умолчанию не работает от батареи.
- При установленном anacron строки daily/weekly/monthly в `/etc/crontab` ничего не делают (см. `test -x /usr/sbin/anacron`), поэтому время выполнения `/etc/cron.daily` сдвигается с 06:25 на «после 07:30 + задержка».
- Опции: `anacron -T` (проверить синтаксис), `-f` (выполнить всё, игнорируя отметки), `-n` (без задержек), `-d` (не уходить в фон), `-u` (только обновить отметки).

Современная замена «догоняющих» заданий — systemd-таймер с `Persistent=true`.

### 10.7. at и batch — разовые отложенные задания

Пакет `at` (служба `atd.service`) по умолчанию не установлен: `sudo apt install at`.

```bash
echo "systemctl restart apache2" | sudo at 03:00                 # сегодня (или завтра) в 03:00
echo "/usr/local/bin/job.sh" | at now + 30 minutes
at -f /usr/local/bin/job.sh 23:30 tomorrow                       # команды из файла
at 10am Jul 31                                                   # интерактивный ввод, завершение Ctrl+D
at -t 202610102330                                               # формат [[CC]YY]MMDDhhmm[.ss]
atq                                                              # очередь (root видит все задания)
at -c 5                                                          # показать содержимое задания №5
atrm 5                                                           # удалить
echo "vacuumdb -a -z" | batch                                    # выполнить, когда нагрузка (load average) упадёт ниже 1.5
```

Форматы времени: `HH:MM`, `midnight`, `noon`, `teatime` (16:00), `now + N minutes|hours|days|weeks`, `tomorrow`, даты `MMDDYY`, `DD.MM.YY`, `YYYY-MM-DD`. В отличие от cron, `at` **сохраняет окружение, umask и текущий каталог**, в которых задание было поставлено. Вывод отправляется почтой (нужен MTA). Доступ: `/etc/at.allow`, `/etc/at.deny`. Очередь хранится в `/var/spool/cron/atjobs`. Альтернатива без установки пакета: `sudo systemd-run --on-active=30m /usr/local/bin/job.sh` или `--on-calendar="2026-10-11 03:00"`.

---

## 11. Таймеры systemd

### 11.1. Устройство

Таймер — это пара юнитов с одинаковым именем: `X.timer` (когда) и `X.service` (что; обычно `Type=oneshot`, без секции `[Install]`). Включают и запускают **таймер**:

```bash
sudo systemctl enable --now X.timer      # расписание активно сейчас и после перезагрузки
sudo systemctl start X.service           # выполнить задание немедленно, вне расписания (удобно для проверки)
systemctl list-timers --all              # NEXT / LEFT / LAST / PASSED / UNIT / ACTIVATES
systemctl status X.timer X.service
journalctl -u X.service -e               # вывод задания
```

Директивы секции `[Timer]`:

| Директива | Смысл |
|---|---|
| `OnCalendar=` | календарное расписание (настенные часы); можно несколько строк |
| `OnBootSec=10min` | через 10 минут после загрузки системы |
| `OnStartupSec=` | после старта менеджера systemd (для пользовательских) |
| `OnActiveSec=` | после активации самого таймера |
| `OnUnitActiveSec=1h` | через час после предыдущего **запуска** службы (периодический интервал) |
| `OnUnitInactiveSec=30min` | через 30 минут после **завершения** предыдущего запуска (не накладывается сам на себя) |
| `Persistent=true` | (только для `OnCalendar`) запоминать время последнего срабатывания на диске (`/var/lib/systemd/timers/stamp-X.timer`) и, если момент был пропущен, пока сервер был выключен, выполнить сразу после запуска таймера |
| `RandomizedDelaySec=15min` | случайная задержка 0…15 мин к каждому срабатыванию (чтобы задания/ВМ не стартовали разом) |
| `FixedRandomDelay=true` | задержка случайна, но постоянна для данного хоста и таймера |
| `AccuracySec=` | точность, по умолчанию **1 минута** (срабатывания «округляются» для экономии пробуждений); для точного времени `AccuracySec=1s` |
| `Unit=` | какой юнит запускать, если имя отличается от имени таймера |
| `WakeSystem=true` | будить систему из сна |
| `RemainAfterElapse=` | по умолчанию `yes` |

Если служба ещё работает в момент срабатывания, новый экземпляр **не запускается** (наложений нет). Таймеры с `OnCalendar=` автоматически стартуют после `time-set.target`/`time-sync.target`. В `[Install]` таймера пишут `WantedBy=timers.target`.

### 11.2. Формат OnCalendar и проверка

Общий вид: `ДеньНедели Год-Месяц-День Час:Минута:Секунда [Часовой_пояс]`; `*` — любое, `,` — список, `..` — диапазон, `/` — шаг, `~` — отсчёт от конца месяца. Пропущенная дата = `*-*-*`, пропущенное время = `00:00:00`.

| Выражение | Смысл |
|---|---|
| `hourly` / `daily` / `weekly` / `monthly` / `yearly` | `*-*-* *:00:00` / `*-*-* 00:00:00` / `Mon *-*-* 00:00:00` / `*-*-01 00:00:00` / `*-01-01 00:00:00` |
| `minutely`, `quarterly`, `semiannually` | каждую минуту; раз в квартал; раз в полгода |
| `*-*-* 02:30:00` или просто `02:30` | каждый день в 02:30 |
| `Mon..Fri 08..18:00/15` | по будням с 08 до 18 каждые 15 минут |
| `*:0/10` | каждые 10 минут |
| `Sun 04:00` | по воскресеньям в 04:00 |
| `*-*-01 03:00` | 1-го числа в 03:00 |
| `*-*~01 23:00` | в последний день месяца в 23:00 |
| `Mon *-*-01..07 02:00` | первый понедельник месяца |
| `2026-12-31 23:59:00` | один раз |
| `*-*-* 02:30:00 Europe/Moscow` | с указанием часового пояса |

```bash
systemd-analyze calendar "Mon..Fri 02:30"                 # нормализованная форма и ближайшее срабатывание
systemd-analyze calendar --iterations=5 "*-*-01 03:00"    # пять ближайших
systemd-analyze timespan "1h 30min"                       # проверить интервал
systemd-analyze timestamp "+2d"                           # как systemd понимает метку времени (для --since/--until)
```

Единицы интервалов: `us`, `ms`, `s`, `min`, `h`, `d`, `w`, `M` (месяц = 30,44 суток), `y`; можно комбинировать (`1h 30min`); число без единицы — секунды.

### 11.3. Готовый пример: ночной дамп базы 1С в PostgreSQL

Скрипт `/usr/local/bin/pg-backup-1c.sh` (`chmod 750`, владелец `root:postgres`):

```bash
#!/bin/bash
set -euo pipefail
DB="${1:?укажите имя базы}"
DIR=/var/backups/pg-1c
KEEP_DAYS=14
STAMP=$(date +%F_%H%M)
# каталог должен существовать и принадлежать postgres (в юните ниже его создаёт ExecStartPre)
[ -d "$DIR" ] || { echo "нет каталога $DIR" >&2; exit 1; }
# -Fc: сжатый «custom»-формат, восстанавливается pg_restore
pg_dump -Fc -d "$DB" -f "$DIR/${DB}_${STAMP}.dump.tmp"
mv "$DIR/${DB}_${STAMP}.dump.tmp" "$DIR/${DB}_${STAMP}.dump"
find "$DIR" -name "${DB}_*.dump" -mtime +"$KEEP_DAYS" -delete
echo "OK: $DIR/${DB}_${STAMP}.dump ($(du -h "$DIR/${DB}_${STAMP}.dump" | cut -f1))"
```

Служба-шаблон `/etc/systemd/system/pg-backup-1c@.service` (имя базы — экземпляр):

```ini
[Unit]
Description=pg_dump backup of 1C database %i
After=postgresql.service
Wants=postgresql.service
# при сбое запустить юнит-уведомление (необязательно, юнит notify-failure@.service нужно создать самому)
# OnFailure=notify-failure@%n.service

[Service]
Type=oneshot
User=postgres
Group=postgres
ExecStartPre=+/usr/bin/install -d -o postgres -g postgres -m 0750 /var/backups/pg-1c
ExecStart=/usr/local/bin/pg-backup-1c.sh %i
# не мешать рабочей нагрузке
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
# дамп большой базы может идти долго
TimeoutStartSec=6h
```

Таймер `/etc/systemd/system/pg-backup-1c@.timer`:

```ini
[Unit]
Description=Nightly pg_dump of 1C database %i

[Timer]
OnCalendar=*-*-* 02:30:00
RandomizedDelaySec=5min
Persistent=true
AccuracySec=1s

[Install]
WantedBy=timers.target
```

Включение и проверка:

```bash
sudo systemd-analyze verify /etc/systemd/system/pg-backup-1c@.service /etc/systemd/system/pg-backup-1c@.timer
sudo systemctl daemon-reload
sudo systemctl enable --now pg-backup-1c@buh.timer        # база "buh"
systemctl list-timers 'pg-backup-1c@*'
sudo systemctl start pg-backup-1c@buh.service             # пробный запуск сейчас
systemctl status pg-backup-1c@buh.service --no-pager      # Result: success / exit-code
journalctl -u pg-backup-1c@buh.service -e --no-pager
ls -lh /var/backups/pg-1c/
```

Пояснения: служба `oneshot` без `[Install]` — её не «включают»; `User=postgres` даёт peer-аутентификацию через unix-сокет без пароля; `pg_dump` находится по стандартному `PATH` служб (`/usr/bin/pg_dump` из пакетов Ubuntu/PGDG; для Postgres Pro укажите полный путь к бинарнику из `/opt/pgpro/…/bin`); `ExecStartPre=+…` выполняется от root (префикс `+`) и создаёт каталог; `Persistent=true` выполнит пропущенный ночной дамп после включения ВМ; код возврата скрипта ≠ 0 переводит юнит в `failed` — это видно в `systemctl --failed` и мониторинге. Это пример механики таймера, а не стратегия резервного копирования (её см. в разделе базы знаний о PostgreSQL).

Готовые таймеры из `postgresql-common` (есть в 24.04 и 26.04 — подтверждено списком файлов пакета; тексты сверены по postgresql-common 293): `pg_dump@<версия>-<кластер>.timer` (еженедельный дамп в `/var/backups/postgresql/…`, хранит 3 копии — `Environment="KEEP=3"`, выполняется утилитой `pg_backupcluster … dump` от пользователя `postgres`), `pg_basebackup@….timer` + `pg_receivewal@….service` (базовые копии и архив WAL), `pg_compresswal@….timer`: `sudo systemctl enable --now pg_dump@16-main.timer`. Особенности штатного `pg_dump@.timer`: `OnCalendar=weekly` (понедельник 00:00) + `RandomizedDelaySec=1h` с `FixedRandomDelay=true`; `Persistent=` **не задан** — пропущенный из-за выключенной ВМ запуск не «догоняется»; в `[Install]` стоит `WantedBy=postgresql@%i.service`, т.е. включённый таймер стартует вместе со своим кластером. Для базы 1С еженедельного дампа всего кластера обычно недостаточно — меняйте расписание drop-in'ом (`sudo systemctl edit pg_dump@16-main.timer` → `[Timer]`, `OnCalendar=`, `OnCalendar=*-*-* 02:30`, `Persistent=true`) или используйте свой таймер из примера выше.

### 11.4. cron или таймер?

| Критерий | cron | systemd timer |
|---|---|---|
| Простота | одна строка | два файла + `daemon-reload` + `enable` |
| Журнал вывода | почта/ручное перенаправление | автоматически в journald (`journalctl -u X`) |
| Статус последнего запуска, код возврата | нет | `systemctl status X.service`, `list-timers`, `--failed` |
| Пропущенные запуски (сервер был выключен) | нет (нужен anacron) | `Persistent=true` |
| Наложение запусков | возможно (нужен `flock`) | невозможно |
| Зависимости (`After=postgresql.service`), порядок | нет | есть |
| Лимиты ресурсов, изоляция, пользователь | вручную (`nice`, `ionice`) | `MemoryMax=`, `CPUQuota=`, `Nice=`, `ProtectSystem=`… |
| Окружение | минимальное, свои правила (`%`, `PATH`) | как у любой службы (`Environment=`) |
| Секунды, случайная задержка, «после загрузки», «через N после завершения» | нет (только минуты, `@reboot`) | `OnCalendar` с секундами, `RandomizedDelaySec`, `OnBootSec`, `OnUnitInactiveSec` |
| Ручной запуск «как по расписанию» | копировать команду | `systemctl start X.service` |
| Переносимость | любой Unix | только systemd |

Практика: разовые простые задания пользователя — cron; всё, что важно для сервера (резервные копии, обслуживание СУБД, перезапуски) — таймеры.

---

## 12. Загрузка и выключение

### 12.1. shutdown, reboot, poweroff

В Ubuntu `shutdown`, `reboot`, `poweroff`, `halt` — это ссылки на `systemctl` (пакет `systemd-sysv`).

```bash
sudo shutdown -r now                      # перезагрузка немедленно
sudo shutdown -h now                      # выключение немедленно (-h = -P = --poweroff)
sudo shutdown -r +10 "Перезагрузка сервера 1С через 10 минут"    # через 10 минут, с сообщением всем терминалам (wall)
sudo shutdown -h 23:30                    # выключение в 23:30
sudo shutdown -c                          # отменить запланированное
shutdown --show                           # показать запланированное (systemd ≥ 250)
sudo shutdown -k +5 "Проверка оповещения" # только разослать сообщение, ничего не выключая
sudo reboot                               # = systemctl reboot
sudo poweroff                             # = systemctl poweroff
sudo systemctl reboot --when="+2h"        # (≥254) отложенная перезагрузка; формат времени — как в systemd.time(7)
sudo systemctl soft-reboot                # (≥254) перезапуск только пользовательского пространства, без перезагрузки ядра
```

Правила `shutdown`: `ВРЕМЯ` — `now`, `+минуты` или `чч:мм`; **без указания времени действие произойдёт через 1 минуту**; действие по умолчанию — выключение питания; `-H` — halt (остановить ОС без отключения питания); `-r` — перезагрузка; `--no-wall` — без оповещения. За 5 минут до отложенного выключения создаётся `/run/nologin` (новые входы запрещены).

Что происходит при штатном выключении: systemd останавливает юниты в порядке, обратном запуску (сервер 1С с `After=postgresql.service` — раньше PostgreSQL), каждому даётся его `TimeoutStopSec=` (у `postgresql@` — до часа, у прочих по умолчанию 90 с), затем оставшимся процессам — SIGTERM/SIGKILL, размонтирование ФС. Сообщение «A stop job is running for … (1min 30s)» — это ожидание такого тайм-аута; виновника ищите после загрузки: `journalctl -b -1 -e`.

Принудительные варианты (без корректной остановки служб — риск для баз данных, только в крайнем случае): `systemctl reboot --force` (убить процессы, размонтировать, перезагрузить), `systemctl reboot --force --force` (немедленно, даже без sync), `reboot -f`.

Для ВМ на Windows-хосте: «мягкое» выключение из гипервизора (Hyper-V «Завершение работы» через службы интеграции, VMware Tools/`open-vm-tools`, ACPI-кнопка питания в VirtualBox) приводит к обычному `poweroff` в гостевой ОС. Убедитесь, что гипервизор не «гасит» ВМ принудительно раньше, чем успеют остановиться сервер 1С и PostgreSQL (тайм-аут автоматической остановки ВМ на хосте должен быть больше суммарного времени остановки служб).

### 12.2. Цели (targets) и режим по умолчанию

| Цель | Аналог runlevel | Назначение |
|---|---|---|
| `poweroff.target` | 0 | выключение |
| `rescue.target` | 1, S | однопользовательский режим: базовая система, локальные ФС, root-shell, без сетевых служб |
| `multi-user.target` | 2, 3, 4 | полноценный режим без графики |
| `graphical.target` | 5 | multi-user + графический вход |
| `reboot.target` | 6 | перезагрузка |
| `emergency.target` | – | аварийный shell: минимум юнитов, корень может быть смонтирован только на чтение |

```bash
systemctl get-default                          # в Ubuntu обычно graphical.target (на сервере без графики это эквивалентно multi-user)
sudo systemctl set-default multi-user.target   # цель по умолчанию при загрузке (симлинк /etc/systemd/system/default.target)
sudo systemctl isolate multi-user.target       # перейти в цель сейчас, остановив всё лишнее
sudo systemctl rescue                          # перейти в rescue (остановит службы, в т.ч. 1С и СУБД!)
sudo systemctl emergency
sudo systemctl default                         # вернуться к цели по умолчанию
```

Вход в режим восстановления при загрузке: в меню GRUB нажать `e`, в строку `linux …` дописать `systemd.unit=rescue.target` (или `emergency.target`), `Ctrl+X`. В emergency корневая ФС может быть «ro»: `mount -o remount,rw /`. Короткие синонимы параметра ядра: `1`/`single`/`rescue` — `rescue.target` (man `systemd.special(7)`), `emergency` — `emergency.target` (man `systemd(1)`).

**Заблокированный root и оболочка восстановления.** В Ubuntu учётная запись root по умолчанию заблокирована (пароль `!`/`*`). Оболочку в rescue/emergency запускает `sulogin`. Что подтверждено документацией: по man `sulogin(8)` root-оболочка **без пароля** при заблокированном root выдаётся только с ключом `-e/--force`; systemd передаёт этот ключ, только если для `rescue.service`/`emergency.service` задана переменная `SYSTEMD_SULOGIN_FORCE=1` (systemd.io/ENVIRONMENT: «skips asking for the root password if the root password is not available (such as when the root account is locked)»). Без неё вместо оболочки появится сообщение вида «Cannot open access to console, the root account is locked» и загрузка пойдёт дальше/по кругу. ⚠ Не подтверждено, задана ли эта переменная «из коробки» в каждом выпуске Ubuntu (на практике в Ubuntu обычно видно приглашение «Press Enter for maintenance (or press Control-D to continue)», т.е. пароль не спрашивается). Поэтому на сервере, к консоли которого есть доступ только у администраторов (ВМ), стоит заранее проверить и при необходимости задать её самому:

```bash
systemctl show -p Environment rescue.service emergency.service     # есть ли SYSTEMD_SULOGIN_FORCE=1
sudo mkdir -p /etc/systemd/system/rescue.service.d /etc/systemd/system/emergency.service.d
printf '[Service]\nEnvironment=SYSTEMD_SULOGIN_FORCE=1\n' | sudo tee /etc/systemd/system/rescue.service.d/sulogin.conf \
     /etc/systemd/system/emergency.service.d/sulogin.conf >/dev/null
sudo systemctl daemon-reload
```

Это осознанное ослабление защиты (любой, у кого есть консоль ВМ, получает root без пароля) — man `sulogin` прямо предупреждает использовать `--force` только при физически защищённой консоли. Альтернативы, если оболочка недоступна: пункт GRUB «Advanced options for Ubuntu → … (recovery mode)» (меню пакета `friendly-recovery`, он входит в рекомендуемые пакеты `ubuntu-standard`; пункт «root — Drop to root shell prompt»), параметр ядра `init=/bin/bash` либо загрузка с установочного ISO и `chroot`.

Система сама сваливается в emergency-режим чаще всего из-за ошибки в `/etc/fstab` (несуществующий UUID, недоступный диск без опции `nofail`): смотрите `journalctl -xb`, исправляйте fstab, затем `systemctl daemon-reload` и `systemctl default` либо `reboot`.

### 12.3. Анализ загрузки: systemd-analyze

```bash
systemd-analyze                                   # время: firmware + loader + kernel + initrd + userspace
systemd-analyze blame | head -n 20                # юниты по убыванию времени запуска
systemd-analyze critical-chain                    # «критическая цепочка» до цели по умолчанию
systemd-analyze critical-chain srv1cv8-8.3.27.2325@default.service
systemd-analyze plot > /tmp/boot.svg              # диаграмма загрузки (открыть в браузере)
systemd-analyze verify /etc/systemd/system/*.service   # проверка unit-файлов
systemd-analyze cat-config systemd/journald.conf  # итоговый конфиг с drop-in
systemd-analyze unit-paths                        # пути поиска юнитов
systemd-analyze security ИМЯ                      # оценка изоляции службы
systemd-analyze exit-status                       # таблица кодов завершения
```

Как читать: в `critical-chain` значение после `@` — момент, когда юнит стал активен, после `+` — сколько он запускался. `blame` обманчив: юнит может быть «долгим» лишь потому, что ждал другой; службы `Type=simple` считаются запущенными мгновенно и в список не попадают; часто «виновник» — `systemd-networkd-wait-online.service` (ожидание сети, по умолчанию до 2 минут, если описанный в netplan интерфейс не поднимается — пометьте его `optional: true`).

---

## 13. hostnamectl, timedatectl, localectl, loginctl

### 13.1. hostnamectl — имя хоста

```bash
hostnamectl                                   # имя, machine-id, виртуализация (Virtualization: microsoft/vmware/oracle/kvm), ОС, ядро
sudo hostnamectl set-hostname srv1c           # задать статическое имя (/etc/hostname); работает во всех версиях
sudo hostnamectl hostname srv1c               # новый синтаксис (systemd ≥ 249)
hostnamectl hostname                          # показать
```

После смены имени поправьте `/etc/hosts` (строка `127.0.1.1 старое_имя`), иначе `sudo` будет жаловаться «unable to resolve host». В облачных образах имя может возвращать cloud-init (`preserve_hostname: true` в `/etc/cloud/cloud.cfg`). Для сервера 1С имя хоста — часть конфигурации кластера (реестр кластера, строки подключения клиентов, привязка программных лицензий): задавайте его **до** установки 1С и не меняйте на работающем сервере без плана перенастройки кластера (практика).

### 13.2. timedatectl — время и часовой пояс

```bash
timedatectl                                   # Local time, Universal time, RTC time, Time zone, System clock synchronized, NTP service
timedatectl list-timezones | grep -i -E 'moscow|tashkent'
sudo timedatectl set-timezone Asia/Tashkent   # меняет симлинк /etc/localtime
sudo timedatectl set-ntp true                 # включить службу синхронизации времени
sudo timedatectl set-time "2026-10-10 12:00:00"   # вручную (только при выключенной синхронизации)
timedatectl timesync-status                   # состояние systemd-timesyncd (22.04/24.04)
chronyc tracking; chronyc sources -v          # состояние chrony (по умолчанию в 26.04)
timedatectl show -p Timezone --value
```

Аппаратные часы держите в UTC (`RTC in local TZ: no`); `set-local-rtc 1` не рекомендуется документацией. После смены часового пояса перезапустите службы, которые прочитали его при старте: `cron`, `rsyslog`, сервер 1С, при необходимости PostgreSQL (у него свой параметр `timezone`/`log_timezone` в `postgresql.conf`). В Ubuntu 26.04 новая установка использует **chrony** вместо `systemd-timesyncd`; при обновлении с 24.04 миграция выполняется вручную: `sudo apt-mark auto systemd-timesyncd && sudo apt install chrony`.

### 13.3. localectl — локаль и раскладка

```bash
localectl                                     # System Locale, VC Keymap, X11 Layout
localectl list-locales                        # какие локали сгенерированы
sudo locale-gen ru_RU.UTF-8 en_US.UTF-8       # сгенерировать (Ubuntu/Debian)
sudo localectl set-locale LANG=ru_RU.UTF-8    # системная локаль (пишет /etc/default/locale); то же: sudo update-locale LANG=ru_RU.UTF-8
sudo localectl set-locale LANG=en_US.UTF-8 LC_TIME=ru_RU.UTF-8 LC_COLLATE=ru_RU.UTF-8
localectl list-keymaps | grep -i ru
```

Локаль применяется к новым сеансам и к службам после их перезапуска (systemd передаёт службам `LANG` из системной локали). Где хранится системная локаль: в 22.04/24.04 — `/etc/default/locale` (особенность Debian/Ubuntu); upstream systemd использует `/etc/locale.conf`, и в новых выпусках Debian/Ubuntu файл мог быть перенесён туда с симлинком совместимости (⚠ для 26.04 не сверялось — посмотрите `ls -l /etc/default/locale /etc/locale.conf`). В скриптах не правьте файл напрямую — пользуйтесь `localectl set-locale`/`update-locale`, они знают правильное место. Для 1С + PostgreSQL локаль `ru_RU.UTF-8` должна быть **сгенерирована до** создания кластера PostgreSQL (`initdb`/`pg_createcluster --locale ru_RU.UTF-8`) — подробности в статьях базы знаний о локалях и PostgreSQL.

### 13.4. loginctl — сеансы пользователей (systemd-logind)

```bash
loginctl                                      # = list-sessions: кто вошёл, с какого терминала/по SSH
loginctl list-users
loginctl session-status 42                    # процессы сеанса
loginctl show-session 42 -p Remote -p RemoteHost -p Type
loginctl user-status usr1cv8
sudo loginctl terminate-session 42            # завершить сеанс (выкинуть пользователя)
sudo loginctl terminate-user ivanov           # завершить все сеансы пользователя
sudo loginctl kill-user ivanov --signal=SIGKILL
sudo loginctl enable-linger ivanov            # разрешить пользовательским службам (systemctl --user) работать без активного входа
```

Настройки — `/etc/systemd/logind.conf` (drop-in `/etc/systemd/logind.conf.d/`): `KillUserProcesses=` (по умолчанию `no` — процессы, оставленные в `tmux`/`nohup`, переживают выход), `HandlePowerKey=poweroff` (реакция на ACPI-кнопку питания — именно так гипервизор «мягко» выключает ВМ), `RemoveIPC=`. Про `RemoveIPC` (документация PostgreSQL, раздел «systemd RemoveIPC»): при `RemoveIPC=yes` logind удаляет объекты IPC (разделяемую память, семафоры) пользователя при его полном выходе из системы; **системные** пользователи исключены. Пакетный `postgres` и `usr1cv8` — системные учётные записи, поэтому обычно проблема не возникает; если же СУБД запущена под обычным пользователем, возможны ошибки вида `could not remove shared memory segment` — тогда задайте `RemoveIPC=no`.

---

## 14. systemd-tmpfiles, coredumpctl, systemd-run и другие утилиты

### 14.1. systemd-tmpfiles — создание и очистка временных файлов/каталогов

Декларативные правила в `*.conf`: `/usr/lib/tmpfiles.d/` (пакеты), `/run/tmpfiles.d/`, `/etc/tmpfiles.d/` (администратор; файл с тем же именем перекрывает пакетный). Применяются при загрузке (`systemd-tmpfiles-setup.service`) и периодически для очистки (`systemd-tmpfiles-clean.timer`: через 15 минут после загрузки и далее раз в сутки).

Формат строки: `Тип  Путь  Режим  Владелец  Группа  Возраст  Аргумент` (`-` — по умолчанию).

| Тип | Действие |
|---|---|
| `d` | создать каталог, если нет; при заданном «возрасте» чистить содержимое старше него |
| `D` | то же, но содержимое удаляется при `--remove` |
| `e` | не создавать, а только чистить содержимое существующего каталога по возрасту (можно шаблон) |
| `f` / `f+` | создать файл (опционально записать аргумент) / создать или обнулить |
| `w` / `w+` | записать / дописать аргумент в существующий файл (например, в `/sys/…`) |
| `L` / `L+` | создать симлинк / заменить существующее |
| `r` / `R` | удалить файл / рекурсивно каталог |
| `x` / `X` | исключить путь из очистки (с содержимым / только сам путь) |
| `z` / `Z` | поправить права/владельца (одного пути / рекурсивно) |
| `C` | рекурсивно скопировать |

Возраст: `10d`, `12h`, `2w`, `30min`, `0` — удалять всё; файл удаляется, если и atime, и mtime, и ctime старше указанного.

Пример `/etc/tmpfiles.d/1c.conf`:

```
# каталоги для логов и дампов сервера 1С с нужным владельцем (создаются при каждой загрузке, если отсутствуют)
d /var/log/1c        0750 usr1cv8 grp1cv8 -
d /var/log/1c/dumps  0750 usr1cv8 grp1cv8 14d
# страховочная чистка технологического журнала: содержимое каталога (рекурсивно) старше 7 дней; сам каталог не создаётся
e /var/log/1c/tj     -    -       -       7d
```

Учтите: возраст считается по самому «свежему» из времён файла, включая atime — если старые файлы регулярно читает резервное копирование или антивирус, они не устареют.

```bash
sudo systemd-tmpfiles --create /etc/tmpfiles.d/1c.conf      # применить правила создания сейчас
sudo systemd-tmpfiles --clean  /etc/tmpfiles.d/1c.conf      # выполнить очистку по возрасту сейчас
sudo systemd-tmpfiles --cat-config | less                   # вся действующая конфигурация
systemctl list-timers systemd-tmpfiles-clean.timer
```

`/tmp` и `/var/tmp`: правила в `/usr/lib/tmpfiles.d/tmp.conf` (посмотрите фактические: `cat /usr/lib/tmpfiles.d/tmp.conf`). В Ubuntu ≤ 24.04 `/tmp` лежит на корневой ФС. **В Ubuntu 26.04 `/tmp` — tmpfs**: официально, release notes 26.04 — «Ubuntu now comes with the upstream `tmp.mount` unit by default. As a result, the `/tmp` directory is now a `tmpfs` file system by default» (изменение появилось в 24.10). Содержимое tmpfs живёт в ОЗУ/свопе и теряется при перезагрузке.

Что известно о деталях (release notes Ubuntu их не приводят; ниже — документация Debian 13 «trixie», где включён тот же upstream-юнит `tmp.mount`, и исходный `tmp.conf` systemd; по журналу изменений пакета systemd в Ubuntu (сверено 11.10.2026) собственная правка Ubuntu со сроком 30 дней для `/tmp` снята в версии 256-1ubuntu1 («We want to stay aligned with Debian and upstream instead of keeping this 30d cleanup»), то есть в 24.10 и новее действуют исходные сроки systemd; сам файл для Ubuntu 26.04 сверить на своей системе командами из блока ниже):

- размер tmpfs по умолчанию — **до 50% ОЗУ** (это верхняя граница; память расходуется по мере появления файлов);
- изменить размер: `sudo systemctl edit tmp.mount` → `[Mount]` / `Options=mode=1777,nosuid,nodev,size=4G`;
- вернуть `/tmp` на диск: `sudo systemctl mask tmp.mount` и перезагрузка;
- запись для `/tmp` в `/etc/fstab` (отдельный раздел или свой tmpfs) имеет приоритет над `tmp.mount`;
- upstream `tmp.conf`: `q /tmp 1777 root root 10d` и `q /var/tmp 1777 root root 30d` — файлы в `/tmp`, не использовавшиеся 10 дней, и в `/var/tmp` — 30 дней, удаляются ежедневной очисткой `systemd-tmpfiles-clean.timer`. В Debian до 13 и в Ubuntu 22.04/24.04 `tmp.conf` был изменён дистрибутивом, сроки там другие (уточнено 11.10.2026: правка Debian (версии 249–255) ставит `D /tmp 1777 root root -` и комментирует строку про `/var/tmp`; Ubuntu с 255.4-1ubuntu2 (24.04) добавляет для `/tmp` срок 30 дней; в Debian 256~rc3-3 правка убрана, и Ubuntu в 256-1ubuntu1 тоже сняла свою добавку «30 дней», так что в 24.10–26.04 действуют исходные сроки (10 и 30 дней) — по тексту правки на salsa.debian.org и журналам изменений пакета на changelogs.ubuntu.com; сами файлы из пакетов Ubuntu не читались, поэтому по-прежнему: точное содержимое для 22.04/24.04/26.04 не сверено — git.launchpad.net недоступен; смотрите файл). Свои исключения: `/etc/tmpfiles.d/local-tmp.conf` со строками `x /tmp/каталог`; полная замена правил — свой `/etc/tmpfiles.d/tmp.conf`.

```bash
findmnt /tmp                                   # tmpfs или каталог корневой ФС? какой size=
systemctl status tmp.mount --no-pager          # active (mounted) / masked
cat /usr/lib/tmpfiles.d/tmp.conf               # действующие сроки очистки /tmp и /var/tmp
df -h /tmp; sudo du -xsh /tmp/* 2>/dev/null | sort -h | tail     # кто занимает место
```

**Почему это важно для 1С.** По практике сообщества (многочисленные обращения вида «`/tmp` переполнен файлами `v8_*.tmp`»; документацией 1С в рамках статьи не подтверждено — подтверждено статьёй ИТС 1736, сверено 10.10.2026:) процессы сервера 1С на Linux создают временные файлы в `/tmp`, и при тяжёлых отчётах, обменах, выгрузках и реструктуризации их объём доходит до гигабайтов. На 26.04 это означает: (1) временные файлы 1С расходуют **оперативную память** ВМ, конкурируя с `rphost` и `shared_buffers` PostgreSQL, вплоть до OOM; (2) при заполнении лимита tmpfs (50% ОЗУ) операции 1С падают с «No space left on device», хотя диск свободен. Для сервера 1С на 26.04 обычно разумно вернуть `/tmp` на диск (`mask tmp.mount`) либо вынести его на отдельный раздел через `/etc/fstab` (это практическое суждение, а не официальная рекомендация 1С или Canonical); решение принимайте до ввода сервера в работу и после проверки на тестовой ВМ. Проверить, куда реально пишет ваш сервер: `sudo ls -la /tmp | grep usr1cv8` и `sudo lsof -a -u usr1cv8 +D /tmp 2>/dev/null | head` во время тяжёлой операции (`-a` — объединить условия по «И»). Возможность перенаправить временные файлы сервера 1С переменной окружения (`TMPDIR`/`TEMP` в drop-in юнита) для `TMPDIR` подтверждена статьёй ИТС «Изменение каталога временных файлов сервера 1С:Предприятия» (переменная задаётся пользователю сервера и действует после перезапуска); для `TEMP` и для задания именно в drop-in не подтверждена — нужен раздел документации 1С о временных файлах сервера.

### 14.2. coredumpctl — дампы аварийно завершившихся процессов

`coredumpctl` входит в пакет `systemd-coredump`, который в Ubuntu **не установлен**: по умолчанию `kernel.core_pattern` указывает на `apport` (отчёты в `/var/crash/`). Проверка: `cat /proc/sys/kernel/core_pattern`.

```bash
sudo apt install systemd-coredump        # переключает core_pattern на systemd-coredump
coredumpctl list                         # TIME PID UID GID SIG COREFILE EXE
coredumpctl list rphost --since yesterday
coredumpctl info 12345                   # подробности по PID (сигнал, командная строка, стек, если есть символы)
coredumpctl -1 info                      # последний дамп
coredumpctl dump 12345 -o /tmp/core.12345   # выгрузить core-файл
coredumpctl debug 12345                  # открыть в gdb
```

Файлы — в `/var/lib/systemd/coredump/` (сжатые), метаданные — в журнале; настройки — `/etc/systemd/coredump.conf` (`Storage=external|journal|none`, `Compress=`, `ProcessSizeMax=`, `ExternalSizeMax=`, `MaxUse=`, `KeepFree=`); старые дампы удаляются автоматически. Чтобы служба вообще могла оставить дамп, у неё должен быть ненулевой `LimitCORE=` (см. drop-in сервера 1С в разделе 5.1). Методика сбора дампов рабочих процессов 1С в Linux описана на ИТС (см. «Источники» — закрытая страница); она может требовать собственного `core_pattern`, конфликтующего с apport/systemd-coredump.

### 14.3. systemd-run — разовый запуск как временный юнит

Запускает команду в виде transient-службы (`run-XXXX.service`) или scope: с журналом, лимитами cgroup, от нужного пользователя, по таймеру — без создания файлов.

```bash
# тяжёлая разовая операция с ограничением ресурсов, от имени postgres, с ожиданием результата
sudo systemd-run --unit=reindex-buh --uid=postgres -p MemoryMax=4G -p CPUQuota=200% -p Nice=10 \
     --wait --collect reindexdb --dbname=buh
journalctl -u reindex-buh -e

sudo systemd-run --on-active=30m systemctl restart apache2             # отложенный запуск через 30 минут
sudo systemd-run --on-calendar="2026-10-11 03:00" --unit=night-job /usr/local/bin/job.sh
systemctl list-timers 'run-*' night-job.timer                          # проверить; отменить: systemctl stop night-job.timer

sudo systemd-run -t --uid=usr1cv8 --gid=grp1cv8 env                    # посмотреть, какое окружение получит служба под этим пользователем
sudo systemd-run --scope -p MemoryMax=2G -p IOWeight=10 ./тяжёлый_скрипт.sh   # выполнить в текущем терминале, но с лимитами
sudo systemd-run -S --uid=postgres                                     # интерактивная оболочка как отдельная служба
```

Опции: `--unit=ИМЯ`, `--description=`, `-p Свойство=значение` (любые директивы `[Service]`), `--uid=`, `--gid=`, `--nice=`, `-E VAR=значение`, `--working-directory=`, `-t` (подключить терминал), `-P` (каналы stdin/stdout), `--wait` (ждать и вернуть код возврата), `-G`/`--collect` (убрать юнит после завершения, даже неудачного), `-r` (оставить «активным» после выхода), `--scope`, `--slice=`, `--on-active=`, `--on-boot=`, `--on-calendar=`, `--on-unit-active=`, `--timer-property=`, `--user`. В Ubuntu 26.04 есть также `run0` — замена `sudo` на базе `systemd-run` (`run0 --user=postgres psql`).

### 14.4. Ещё полезное

| Команда | Назначение |
|---|---|
| `systemd-cgls`, `systemd-cgtop` | дерево cgroup с процессами; «top» по службам |
| `systemd-delta` | чем конфигурация в `/etc` отличается от вендорской (переопределения, маски, drop-in) |
| `systemd-escape --path /var/lib/pg` | получить имя юнита для пути (`var-lib-pg`) — для `.mount`-юнитов и экземпляров |
| `systemd-detect-virt` | в какой виртуализации работает ВМ (`microsoft`, `vmware`, `oracle`, `kvm`, `none`) |
| `systemd-cat` | вывод команды → в журнал |
| `systemd-inhibit --what=shutdown --why="идёт резервное копирование" команда` | блокировать выключение/перезагрузку на время выполнения команды |
| `busctl`, `networkctl`, `resolvectl` | шина D-Bus, сеть networkd, DNS-резолвер |

---

## Типичные ошибки и подводные камни

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | `Failed to start X.service: Unit X.service not found` | опечатка в имени; юнит 1С не подключён (`link`); после `systemctl disable` (обычного юнита вроде `ras-…` или шаблона по имени `…@.service`) симлинк `link` удалён; для шаблона не указан экземпляр; симлинк остался, но указывает на удалённый каталог старой платформы | `systemctl list-unit-files 'srv1cv8*'`; повторить `systemctl link …`; имя вида `srv1cv8-<версия>@default` |
| 2 | `Failed to link unit: File /etc/systemd/system/X already exists` | там лежит старая копия/симлинк — типично после `disable …@default` (по имени экземпляра симлинк шаблона не снимается, п. 4.2) и переустановки той же версии | `ls -l /etc/systemd/system/X`; если симлинк уже указывает на нужный файл — `link` не нужен; иначе удалить файл в `/etc/systemd/system/`, `daemon-reload`, повторить |
| 3 | Правка юнита «не действует»; `Warning: The unit file … changed on disk` | не сделан `daemon-reload` и/или `restart` | `sudo systemctl daemon-reload && sudo systemctl restart X`; проверить `systemctl cat X` |
| 4 | Параметры в юните приняли странное значение (`User=usr1cv8 # комментарий`) | комментарий в одной строке со значением | комментарии только отдельными строками |
| 5 | `Main process exited, code=exited, status=203/EXEC` | неверный путь в `ExecStart`, нет бита `x`, скрипт с CRLF или без shebang, ФС смонтирована `noexec` | проверить путь и права; `sed -i 's/\r$//' скрипт`; `head -1 скрипт` |
| 6 | `status=217/USER`, `216/GROUP` | нет пользователя/группы из `User=`/`Group=` | `id usr1cv8`; создать пользователя или исправить юнит |
| 7 | `status=200/CHDIR` | нет каталога `WorkingDirectory=` | создать каталог или `WorkingDirectory=-/путь` |
| 8 | `Start request repeated too quickly`, `Result: start-limit-hit` | служба падает сразу после старта и исчерпала 5 запусков за 10 с | устранить причину (журнал!), затем `systemctl reset-failed X && systemctl start X`; увеличить `RestartSec=` |
| 9 | `Service has more than one ExecStart= setting, which is only allowed for Type=oneshot` | в drop-in добавлен второй `ExecStart=` без сброса | перед новым значением пустая строка `ExecStart=` |
| 10 | Служба сразу `inactive (dead)` или `Deactivated successfully`, хотя демон должен работать | программа сама уходит в фон при `Type=simple` (например, `ragent -daemon`, `ras --daemon`) — systemd считает, что главный процесс завершился, и убивает остальных | убрать ключ демонизации либо `Type=forking` + `PIDFile=` |
| 11 | Служба «не видит» переменные, `PATH`, локаль | окружение shell службам не передаётся | `Environment=`/`EnvironmentFile=` в drop-in; проверить `/proc/PID/environ` |
| 12 | `Too many open files` при том, что `ulimit -n` в консоли большой | `limits.conf` на службы не действует; по умолчанию soft-лимит 1024 | `LimitNOFILE=65536` в drop-in, `restart`; проверить `/proc/PID/limits` |
| 13 | Сервер 1С после перезагрузки стартует раньше СУБД/сети, первые подключения с ошибками | нет `After=`/`Wants=` | drop-in из раздела 6; проверить `systemd-analyze critical-chain` |
| 14 | `After=network-online.target` не помогает | цель никто не «тянет» (`Wants=` забыт) или служба ожидания сети выключена | добавить `Wants=network-online.target`; `systemctl is-enabled systemd-networkd-wait-online` |
| 15 | Сервер 1С запускается вручную, но не при загрузке | не выполнен `enable`; юнит подключён с ФС, не доступной на раннем этапе (`/opt` на отдельном томе) | `systemctl is-enabled …`; `enable`; скопировать юнит в `/etc/systemd/system/` вместо `link` |
| 16 | После обновления платформы 1С «порт 1540 занят», работает старая версия | старый юнит не отключён, запущены оба | `systemctl list-units 'srv1cv8*' 'ras-*'`; `disable --now` старого |
| 17 | После обновления платформы пропали свои настройки (порты, отладка, порядок запуска) | drop-in привязан к имени юнита со старой версией | скопировать каталог `…@default.service.d` под новое имя, `daemon-reload` |
| 18 | `systemctl start srv1cv8-…@.default` — служба есть, но «не та» | опечатка: экземпляр назван `.default` | остановить, использовать `@default` |
| 19 | `postgresql.service` — `active (exited)`, а база недоступна | это зонтичный юнит, он активен всегда; сам кластер не поднялся либо ещё восстанавливается | `pg_lsclusters`; `systemctl status postgresql@16-main`; `/var/log/postgresql/*.log` |
| 20 | PostgreSQL остановлен целиком либо сервер 1С неожиданно перезапустился со сбросом всех сеансов; в статусе/журнале `Result: oom-kill` | ядро убило по OOM один процесс юнита, а `OOMPolicy=stop` (по умолчанию) остановил весь юнит; у `postgresql@` авто-рестарта нет, у юнита с `Restart=always` служба поднимается заново целиком | разобраться с памятью (`journalctl -k -g oom`, `journalctl -k -g "killed process"`); `OOMPolicy=continue` в drop-in (практика, не официальная рекомендация); запустить службу |
| 21 | `MemoryLimit=`/`CPUShares=` не действуют (особенно в 26.04) | директивы cgroup v1 устарели/удалены | `MemoryMax=`, `CPUWeight=`, `CPUQuota=` |
| 22 | Журнал занял гигабайты в `/var/log/journal` | лимит по умолчанию — 10% ФС (до 4G) | `journalctl --vacuum-size=…`; `SystemMaxUse=` в `journald.conf.d` |
| 23 | `journalctl` показывает мало/пусто, подсказка «not seeing messages from other users and the system» | нет прав | `sudo` или добавить пользователя в `adm`/`systemd-journal` (перелогиниться) |
| 24 | В журнале «Suppressed N messages from …» | сработал лимит 10000 сообщений за 30 с | `LogRateLimitIntervalSec=0` в юните либо `RateLimit*` в journald.conf |
| 25 | logrotate: `error: skipping … because parent directory has insecure permissions` | каталог логов доступен на запись группе/всем | директива `su пользователь группа` в блоке |
| 26 | logrotate игнорирует файл из `/etc/logrotate.d` | права шире 0644, владелец не root, расширение из taboo, один лог в двух блоках (`duplicate log entry`) | `sudo logrotate -d /etc/logrotate.conf` покажет причину |
| 27 | После ротации программа пишет в старый файл (`.1`) или в «удалённый» | программа держит дескриптор, а `postrotate` с переоткрытием нет | сигнал переоткрытия в `postrotate` или `copytruncate` |
| 28 | Лог вырос до десятков ГБ, хотя стоит `size 100M` | logrotate запускается раз в сутки | `maxsize` + учащение `logrotate.timer` (п. 9.3) |
| 29 | ТЖ 1С перестал вестись после «оптимизации» логов | в каталог ТЖ попали посторонние файлы (архивы, `.gz`) или изменены права | убрать постороннее, вернуть владельца `usr1cv8:grp1cv8`; ротацию оставить платформе (`history`) |
| 30 | Таймер создан, но не срабатывает | включили `.service` вместо `.timer`; `enable` без `--now`; ошибка в `OnCalendar` | `systemctl enable --now X.timer`; `systemctl list-timers --all`; `systemd-analyze calendar "…"` |
| 31 | Таймер срабатывает «не секунда в секунду» | `AccuracySec=1min` по умолчанию, `RandomizedDelaySec` | `AccuracySec=1s` |
| 32 | Задание cron не выполняется | см. таблицу в п. 10.5 (PATH, `%`, имя файла с точкой, CRLF, dash вместо bash) | там же |
| 33 | При выключении «A stop job is running… (1min 30s)» | служба не завершается по SIGTERM | найти юнит в `journalctl -b -1 -e`; настроить ему `ExecStop=`/`TimeoutStopSec=`/`KillSignal=` |
| 34 | Загрузка останавливается в emergency mode | ошибка в `/etc/fstab`, недоступный диск | `journalctl -xb`; исправить fstab (`nofail`, верный UUID); `systemctl daemon-reload` |
| 35 | `The unit files have no installation config (WantedBy=, …)` при `enable` | у юнита нет секции `[Install]` (static) | добавить `[Install]` или запускать через таймер/зависимость |
| 36 | `Failed to start X.service: Unit X.service is masked` | юнит заглушён | `systemctl unmask X` |
| 37 | В 26.04 сервер 1С «съедает» память при больших временных файлах либо операции падают с «No space left on device» при свободном диске | `/tmp` теперь tmpfs (по умолчанию до 50% ОЗУ), временные файлы лежат в памяти | `findmnt /tmp`; см. п. 14.1 (`systemctl mask tmp.mount` + перезагрузка либо ограничить/увеличить размер через `Options=…size=`) |
| 38 | Старый `/etc/init.d/srv1cv83` после обновления ОС не работает/конфликтует | init-скрипты — устаревший механизм (26.04 — последний LTS с их поддержкой в systemd) | перейти на вендорский юнит `srv1cv8-<версия>@.service`, удалить init-скрипт |
| 39 | Файлы юнитов/скриптов, созданные на Windows-хосте, «не работают» | окончания строк CRLF, BOM | `sed -i 's/\r$//' файл`; редактировать в nano/vim на сервере или с LF |
| 40 | В `systemctl status` сервера 1С `Tasks: N (limit: M)` близко к пределу; процессы получают `Resource temporarily unavailable` при создании потоков, в журнале ядра — `fork rejected by pids controller in /system.slice/…` (`journalctl -k -g "pids controller"`) | предел `TasksMax=` юнита (по умолчанию 15% от системного максимума потоков; на ВМ с малым ОЗУ — несколько тысяч) | `TasksMax=infinity` или явное число в drop-in, `daemon-reload`, `restart`; проверить `systemctl show -p TasksMax -p TasksCurrent` |
| 41 | В rescue/emergency вместо оболочки «Cannot open access to console, the root account is locked» | root заблокирован, а `sulogin` запущен без `--force` | заранее: drop-in с `Environment=SYSTEMD_SULOGIN_FORCE=1` для `rescue.service` и `emergency.service` (п. 12.2); сейчас: recovery mode в GRUB, `init=/bin/bash` или загрузка с ISO |
| 42 | Отладка 1С на сервере не включается после переноса настроек со старого сервера | в `SRV1CV8_DEBUG` записано `1` (формат старого init-скрипта) или значение с пробелом без кавычек | `Environment=SRV1CV8_DEBUG="-debug -http"` (или `"-debug -tcp"`), `daemon-reload`, `restart`; проверить `ps -o args -C ragent` |
| 43 | В `/etc/cron.d/файл` команда «не найдена», хотя в `/etc/crontab` PATH полный | каждый файл `/etc/cron.d/*` самостоятелен и переменные из `/etc/crontab` не наследует; без своей строки `PATH=` действует `/usr/bin:/bin` | добавить `PATH=…` первой строкой файла или писать полные пути |
| 44 | Пример из интернет-справки `crontab(5)` (`mon-fri`, `CRON_TZ=…`) не работает | справка относится к cronie, а в Ubuntu по умолчанию стоит cron (Vixie/Debian) | `man 5 crontab` на самом сервере; числа вместо имён; пояс — только системный |
---

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Состояние службы | `systemctl status ИМЯ -l --no-pager` |
| Запустить / остановить / перезапустить | `sudo systemctl start` / `stop` / `restart ИМЯ` |
| Перечитать конфигурацию службы без остановки | `sudo systemctl reload ИМЯ` |
| Включить автозапуск и запустить | `sudo systemctl enable --now ИМЯ` |
| Отключить автозапуск и остановить | `sudo systemctl disable --now ИМЯ` |
| Запретить запуск совсем / вернуть | `sudo systemctl mask ИМЯ` / `unmask ИМЯ` |
| Активна ли / включена ли | `systemctl is-active ИМЯ`; `systemctl is-enabled ИМЯ` |
| Что упало | `systemctl --failed` |
| Сбросить состояние failed | `sudo systemctl reset-failed ИМЯ` |
| Работающие службы | `systemctl list-units --type=service --state=running` |
| Что в автозапуске | `systemctl list-unit-files --type=service --state=enabled` |
| Показать юнит со всеми drop-in | `systemctl cat ИМЯ` |
| Свойство юнита | `systemctl show -p LimitNOFILE --value ИМЯ` |
| Переопределить параметры (drop-in) | `sudo systemctl edit ИМЯ` → `sudo systemctl restart ИМЯ` |
| Откатить все переопределения | `sudo systemctl revert ИМЯ` |
| Перечитать unit-файлы после ручной правки | `sudo systemctl daemon-reload` |
| Проверить unit-файл | `systemd-analyze verify /etc/systemd/system/X.service` |
| Зависимости / кто зависит | `systemctl list-dependencies ИМЯ` / `--reverse ИМЯ` |
| Послать сигнал службе | `sudo systemctl kill -s HUP ИМЯ` |
| Подключить и запустить сервер 1С | `sudo systemctl link /opt/1cv8/x86_64/ВЕР/srv1cv8-ВЕР@.service && sudo systemctl enable --now srv1cv8-ВЕР@default` |
| Подключить и запустить RAS | `sudo systemctl link /opt/1cv8/x86_64/ВЕР/ras-ВЕР.service && sudo systemctl enable --now ras-ВЕР` |
| Отключить старую версию сервера 1С (снять автозапуск и link) | `sudo systemctl stop srv1cv8-ВЕР@default && sudo systemctl disable srv1cv8-ВЕР@.service`; проверить `ls -ld /etc/systemd/system/srv1cv8-*` (симлинков на эту версию остаться не должно) |
| Включить отладку на сервере 1С | drop-in: `[Service]` + `Environment=SRV1CV8_DEBUG="-debug -http"` → `daemon-reload` → `restart` |
| Что реально задано в юните 1С | `systemctl cat srv1cv8-ВЕР@default`; `systemctl show -p Environment -p LimitNOFILE -p TasksMax -p OOMPolicy srv1cv8-ВЕР@default` |
| Юниты 1С в системе | `systemctl list-unit-files 'srv1cv8*' 'ras-*'` |
| Кластеры PostgreSQL | `pg_lsclusters`; `systemctl status 'postgresql@*'` |
| Перезапуск кластера PostgreSQL | `sudo systemctl restart postgresql@16-main` |
| Перечитать конфигурацию PostgreSQL | `sudo systemctl reload postgresql@16-main` |
| 1С после сети и PostgreSQL | drop-in: `[Unit]` `After=network-online.target postgresql.service` + `Wants=…` |
| Журнал службы (конец) | `journalctl -u ИМЯ -b -e` |
| Следить за журналом | `journalctl -u ИМЯ -f` |
| Ошибки с момента загрузки | `journalctl -p err -b` |
| Журнал за период | `journalctl --since "2026-10-10 08:00" --until "09:00"` |
| Сообщения ядра / OOM | `journalctl -k -b`; `journalctl -k -g oom` |
| Журнал предыдущей загрузки | `journalctl -b -1 -e` |
| По PID / по пользователю | `journalctl _PID=1234`; `journalctl _UID=$(id -u usr1cv8)` |
| Выгрузить журнал в файл | `journalctl -u ИМЯ -o short-iso --no-pager > файл` |
| Размер журнала / подрезать | `journalctl --disk-usage`; `sudo journalctl --vacuum-size=500M` / `--vacuum-time=14d` |
| Системные текстовые логи | `/var/log/syslog`, `/var/log/auth.log`, `/var/log/kern.log`, `/var/log/dpkg.log` |
| Проверить конфиг logrotate | `sudo logrotate -d /etc/logrotate.d/ИМЯ` |
| Принудительная ротация | `sudo logrotate -f /etc/logrotate.d/ИМЯ` |
| Когда сработает logrotate | `systemctl list-timers logrotate.timer` |
| Свой crontab: правка / просмотр | `crontab -e`; `crontab -l` |
| Crontab другого пользователя | `sudo crontab -u postgres -e` |
| Журнал запусков cron | `journalctl -u cron --since today`; `grep CRON /var/log/syslog` |
| Список таймеров | `systemctl list-timers --all` |
| Проверить расписание | `systemd-analyze calendar "Mon..Fri 02:30" --iterations=3` |
| Включить таймер / выполнить задание сейчас | `sudo systemctl enable --now X.timer`; `sudo systemctl start X.service` |
| Разовый отложенный запуск | `sudo systemd-run --on-active=30m КОМАНДА`; либо `at -f /путь/скрипт.sh 03:00` (пакет `at`) |
| Разовый запуск с лимитами | `sudo systemd-run -p MemoryMax=2G --uid=postgres --wait КОМАНДА` |
| Перезагрузка / выключение | `sudo shutdown -r now`; `sudo shutdown -h +10 "текст"`; отмена `sudo shutdown -c` |
| Цель по умолчанию | `systemctl get-default`; `sudo systemctl set-default multi-user.target` |
| Почему долго грузится | `systemd-analyze blame`; `systemd-analyze critical-chain` |
| Имя хоста | `hostnamectl`; `sudo hostnamectl set-hostname ИМЯ` |
| Время и пояс | `timedatectl`; `sudo timedatectl set-timezone Asia/Tashkent` |
| Локаль | `localectl`; `sudo locale-gen ru_RU.UTF-8`; `sudo localectl set-locale LANG=ru_RU.UTF-8` |
| Сеансы пользователей | `loginctl`; `sudo loginctl terminate-session N` |
| Ресурсы по службам | `systemd-cgtop`; `systemd-cgls` |
| Создать/почистить каталоги по правилам | `sudo systemd-tmpfiles --create`; `--clean` |
| Дампы процессов | `coredumpctl list` (пакет `systemd-coredump`) |

---

## Источники

Официальная документация systemd в редакции Ubuntu (manpages.ubuntu.com; noble = systemd 255.4, resolute = systemd 259.5, jammy = systemd 249.11):

- https://manpages.ubuntu.com/manpages/noble/en/man1/systemctl.1.html и https://manpages.ubuntu.com/manpages/resolute/en/man1/systemctl.1.html — команды и опции systemctl, семантика `link`/`disable`/`enable`/`mask`/`edit`/`revert`/`kill`, значения `is-enabled`, версии появления опций.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.unit.5.html — пути поиска юнитов, drop-in, секции `[Unit]`/`[Install]`, зависимости, спецификаторы, шаблоны.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.service.5.html — `Type=`, `Exec*=`, правила командной строки и подстановки переменных, `Restart=` (таблица), тайм-ауты, `OOMPolicy=`.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.exec.5.html — `User=`, `WorkingDirectory=`, `Environment=`/`EnvironmentFile=`, `Limit*=`, `OOMScoreAdjust=`, вывод/журналирование, изоляция, коды завершения 200–245, окружение по умолчанию.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.resource-control.5.html — `MemoryMax=`, `MemoryHigh=`, `CPUQuota=`, `CPUWeight=`, `TasksMax=`, `IO*=`, устаревшие директивы cgroup v1.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.kill.5.html — `KillMode=`, `KillSignal=`, последовательность остановки.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd-system.conf.5.html — значения по умолчанию (`DefaultTimeoutStartSec=90s`, `DefaultRestartSec=100ms`, `DefaultStartLimitIntervalSec=10s`, `DefaultStartLimitBurst=5`, `DefaultLimitNOFILE=1024:524288`, `DefaultTasksMax=15%`).
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.timer.5.html и https://manpages.ubuntu.com/manpages/noble/en/man7/systemd.time.7.html — директивы таймеров, формат календарных выражений и интервалов.
- https://manpages.ubuntu.com/manpages/noble/en/man1/journalctl.1.html и https://manpages.ubuntu.com/manpages/resolute/en/man1/journalctl.1.html — опции journalctl, фильтры, форматы вывода, новые опции 256–258.
- https://manpages.ubuntu.com/manpages/jammy/en/man5/journald.conf.5.html, https://manpages.ubuntu.com/manpages/noble/en/man5/journald.conf.5.html, https://manpages.ubuntu.com/manpages/resolute/en/man5/journald.conf.5.html — параметры journald и их значения по умолчанию в разных версиях.
- https://manpages.ubuntu.com/manpages/noble/en/man1/systemd-analyze.1.html, https://manpages.ubuntu.com/manpages/noble/en/man1/systemd-run.1.html, https://manpages.ubuntu.com/manpages/noble/en/man5/tmpfiles.d.5.html, https://manpages.ubuntu.com/manpages/noble/en/man1/coredumpctl.1.html, https://manpages.ubuntu.com/manpages/noble/en/man1/timedatectl.1.html, https://manpages.ubuntu.com/manpages/noble/en/man8/shutdown.8.html — соответствующие утилиты.

Ubuntu:

- https://documentation.ubuntu.com/release-notes/26.04/ и https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — дата выпуска 26.04, systemd 255 → 259, ядро 7.0, удаление cgroup v1, `/tmp` на tmpfs, chrony по умолчанию и команды миграции, последний выпуск с совместимостью SysV-скриптов, PostgreSQL 18.
- https://packages.ubuntu.com/ (страницы `ubuntu-minimal`, `ubuntu-standard`, `ubuntu-server`, `ubuntu-server-minimal` для resolute; списки файлов пакетов `systemd`, `rsyslog`, `postgresql-common` для noble/resolute; версии пакета `cron`) — состав системы по умолчанию, наличие `/usr/lib/systemd/journald.conf.d/syslog.conf`, `tmp.mount`, `run0`, юнитов `pg_dump@`/`pg_basebackup@`.

Исходные тексты пакетов Debian/Ubuntu (sources.debian.org):

- https://sources.debian.org/src/postgresql-common/unstable/systemd/ — тексты `postgresql@.service`, `postgresql.service`, `pg_dump@.service`/`.timer`, `README.systemd`; `debian/postgresql-common.logrotate`.
- https://sources.debian.org/src/cron/unstable/debian/ — `/etc/crontab` (`crontab.main`), `cron.service`, `/etc/default/cron`.
- https://sources.debian.org/src/logrotate/unstable/ — `examples/logrotate.timer`, `examples/logrotate.service`, `debian/ubuntu-logrotate.conf`.
- https://sources.debian.org/src/rsyslog/unstable/debian/ — `rsyslog.conf`, `rsyslog.service`, `rsyslog.logrotate`, NEWS.
- https://manpages.debian.org/bookworm/cron/cron.8.en.html, https://manpages.debian.org/trixie/cron/crontab.5.en.html, https://manpages.debian.org/trixie/cron/crontab.1.en.html — cron (опции `-L`, правила имён в `/etc/cron.d`, формат crontab, `%`, строки `@reboot` и т.п., cron.allow/deny).
- https://manpages.ubuntu.com/manpages/noble/en/man8/logrotate.8.html, https://manpages.ubuntu.com/manpages/noble/en/man8/anacron.8.html, https://manpages.ubuntu.com/manpages/noble/en/man1/at.1.html — logrotate 3.21, anacron, at.

PostgreSQL:

- https://www.postgresql.org/docs/current/kernel-resources.html — systemd `RemoveIPC`, OOM-killer и `oom_score_adj` (PostgreSQL 18 — текущая версия на дату статьи).

1С (официальное — закрыто подпиской ИТС, использованы сведения из поисковой выдачи; практические материалы):

- https://its.1c.ru/db/v8327doc — «Клиент-серверный вариант. Руководство администратора», гл. 4 «Запуск компонентов системы»: первоисточник описания вендорского юнита и таблицы переменных `SRV1CV8_*`. Требует подписки и при подготовке статьи **не был прочитан** — соответствующие места помечены ⚠.
- kb.1ci.com, «1C:Enterprise 8.3.22/8.3.23 Administrator Guide. Client/Server Mode», п. 4.2 «Running the server agent → On Linux» — регистрация юнита `systemctl link`, экземпляр `default`, переменные `SRV1CV8_*` (на дату статьи сайт перенаправляет на support.1ci.com; сведения взяты из фрагментов поисковой выдачи).
- https://interface31.ru/post/ustanovka-servera-1cpredpriyatiya-postgresql-apache2-redos-8/ — команды `link`/`enable`/`start` для 8.3.27.2325.
- https://interface31.ru/post/ustanovka-i-zapusk-neskolkih-ekzemplyarov-servera-1spredpriyatie-na-odnom-kompyutere-platforma-linux/ — несколько экземпляров, drop-in с `SRV1CV8_DATA/PORT/REGPORT/RANGE`, порты по умолчанию.
- https://interface31.ru/post/ustanavlivaem-i-nastraivaem-pusk---panel-upravleniya-servisami-i-komponentami-dlya-1spredpriyatie/ и https://1smonitor.ru/ras_1c — юнит `ras-<версия>.service`, порт 1545.
- https://serveradmin.ru/obnovlenie-servera-1s-pod-linux/, https://forum.mista.ru/topic/893638, https://wiki.kint.ru/1С8:Установка_Linux — порядок обновления, типовые ошибки (`Unit not found`, `File already exists`), имя службы `postgrespro-1c-15`.
- https://github.com/slothfk/1c_systemd (`srv1cv83@.service`, `ras1cv83@.service`), https://teletype.in/@ewgenik/c3NH5iXitxT, https://latl.ru/sysadm/1c/few_1c_srv_on_single_host/ — шаблоны юнитов сообщества и примеры drop-in (отладка, порты, ping).
- https://k1c.proapdex.ru/tools/ras_1c/ — производный юнит RAS с `RAS_PORT`/`RAS_CLUSTER_ADDRESS` для 8.3.22.1750.

Дополнительно проверено при рецензии 2026-10-10 (веб-поиск был недоступен — только прямое чтение известных страниц):

- https://manpages.ubuntu.com/manpages/resolute/en/man1/systemctl.1.html (systemd 259.5-0ubuntu3.4) — `--kill-whom=main|control|cgroup|all`, `edit --stdin` (256), `soft-reboot`/`--when=` (254), формулировки `link`/`disable`/`enable` с абсолютным путём.
- https://manpages.ubuntu.com/manpages/resolute/en/man5/systemd.unit.5.html, https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.unit.5.html — усечённые по дефису каталоги drop-in, порядок «экземпляр → шаблон», каталоги уровня типа, таблица путей поиска.
- https://raw.githubusercontent.com/systemd/systemd/v255/src/shared/dropin.c — как строятся усечённые имена для шаблонных юнитов (`foo-@inst.service.d`, `foo-@.service.d`, `foo-.service.d`).
- https://raw.githubusercontent.com/systemd/systemd/v255/src/shared/install.c — какие симлинки удаляет `disable` (совпадение по имени, по имени шаблона, по цели).
- https://sources.debian.org/src/systemd/unstable/src/core/system.conf.in/ — `DefaultOOMPolicy=stop`, `DefaultTasksMax=15%`, `DefaultLimitNOFILE=1024:…`, `DefaultRestartSec=100ms`; https://sources.debian.org/src/systemd/unstable/tmpfiles.d/tmp.conf/ — `q /tmp … 10d`, `q /var/tmp … 30d`.
- https://manpages.ubuntu.com/manpages/noble/en/man5/systemd.service.5.html, …/systemd.exec.5.html, …/systemd.kill.5.html, …/systemd.resource-control.5.html, …/systemd-system.conf.5.html, …/systemd.timer.5.html, …/systemd.special.7.html, …/tmpfiles.d.5.html — `OOMPolicy=`, подстановка `$VAR`/`${VAR}`, префиксы `Exec*=`, окружение служб по умолчанию, `KillMode=`, cgroup-директивы, значения по умолчанию менеджера, таймеры, цели, правило «возраста» tmpfiles.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/journalctl.1.html, https://manpages.ubuntu.com/manpages/resolute/en/man5/journald.conf.5.html, https://manpages.ubuntu.com/manpages/noble/en/man5/journald.conf.5.html — `-e` ⇒ `--lines=1000 --boot=0`, `-I` (257), `-T` (256), `Storage=` (`auto` в 255, `persistent` в 259), значения по умолчанию journald.
- https://systemd.io/ENVIRONMENT/ и https://manpages.ubuntu.com/manpages/noble/en/man8/sulogin.8.html — `SYSTEMD_SULOGIN_FORCE=1`, `sulogin --force` при заблокированном root.
- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — `tmp.mount`/tmpfs (изменение 24.10), systemd 255→259, ядро 6.8→7.0, chrony, удаление cgroup v1, SysV-совместимость, netplan 1.2 и `systemd-networkd-wait-online`, `sudo-rs`, PostgreSQL 18.
- https://www.debian.org/releases/trixie/release-notes/issues.html — `/tmp` на tmpfs: до 50% ОЗУ, `systemctl mask tmp.mount`, `Options=mode=1777,nosuid,nodev,size=…`, приоритет `/etc/fstab`, сроки очистки 10/30 дней, исключения `x …`.
- https://packages.ubuntu.com/ — версии `logrotate` (3.19.0 / 3.21.0 / 3.22.0) и `cron` (3.0pl1-137ubuntu3 / -184ubuntu2 / -200ubuntu1) для jammy/noble/resolute; зависимости `ubuntu-minimal` (chrony; Recommends: rsyslog), `ubuntu-standard` (cron, logrotate; Recommends: friendly-recovery), `ubuntu-server` (apport) для resolute.
- https://sources.debian.org/src/logrotate/bookworm/examples/logrotate.timer/ (3.21.0) и …/bullseye/… (3.18.0) — `AccuracySec=1h`.
- https://sources.debian.org/src/cron/unstable/cron.c/ и …/pathnames.h/ — `setenv("PATH", _PATH_DEFPATH, 1)`, `_PATH_DEFPATH "/usr/bin:/bin"`; …/debian/cron.service/, …/debian/crontab.main/ — тексты юнита и `/etc/crontab`.
- https://manpages.ubuntu.com/manpages/jammy/en/man5/crontab.5.html (cron 3.0pl1-137ubuntu3), https://manpages.debian.org/trixie/cron/crontab.5.en.html, …/crontab.1.en.html, …/cron.8.en.html (cron 3.0pl1-197) — PATH, запрет диапазонов имён, `crontab -n`, `-L`, правила имён в `/etc/cron.d`, перевод часов. Внимание: https://manpages.ubuntu.com/manpages/noble/en/man5/crontab.5.html — это страница пакета **cronie**, а не cron.
- https://sources.debian.org/src/anacron/unstable/debian/anacron.timer/, https://manpages.ubuntu.com/manpages/noble/en/man8/anacron.8.html, …/man1/at.1.html, …/man8/shutdown.8.html, …/man8/logrotate.8.html, …/man1/systemd-run.1.html, …/man1/systemd-analyze.1.html — соответствующие утилиты.
- https://changelogs.ubuntu.com/changelogs/pool/main/r/rsyslog/rsyslog_8.2312.0-3ubuntu9.4/changelog — высокоточные метки времени (8.2210.0-3), `50-default.conf`, `dmesg.service`, пользователь `syslog`, `$RepeatedMsgReduction`; https://raw.githubusercontent.com/rsyslog/rsyslog-pkg-ubuntu/master/rsyslog/noble/v8-stable/debian/50-default.conf — состав правил (upstream-сборка для noble, повторяет дистрибутивный файл).
- https://sources.debian.org/src/postgresql-common/293/systemd/system/ (`postgresql@.service`, `pg_dump@.service`), …/293/debian/postgresql-common.logrotate/ — тексты сверены повторно.
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux — `/opt/pgpro/std-17`, `/var/lib/pgpro/std-17/data`, `/etc/default/postgrespro-std-17`, `pg-setup`, `pg-wrapper`; https://repo.postgrespro.ru/1c/ — каталоги `1c-14` … `1c-18`.
- https://interface31.ru/post/pomoshhnik-ustanovki-i-obnovleniya-servera-1spredpriyatie-dlya-linux/ и сам скрипт https://cdn.interface31.ru/files/1c/1C_full_upgrade.sh — практика для вендорского юнита 8.3.21+: `disable srv1cv8-$oldver@`, `link`, `enable srv1cv8-$newver@`, `start …@default`, отладка через `Environment=SRV1CV8_DEBUG="-debug -tcp"` либо `Environment=SRV1CV8_DEBUG="-debug -http"` в `…@default.service.d/override.conf`, init-скрипт `srv1cv83` в 8.3.20.

Не удалось прочитать (нужен доступ пользователя): https://its.1c.ru/db/v8327doc/content/103/hdoc (гл. 4 «Запуск компонентов системы» руководства администратора — отдаётся только оглавление), приложение руководства администратора с описанием `logcfg.xml`/технологического журнала, kb.1ci.com (разделы пусты без входа), https://infostart.ru/1c/articles/1341653/ (HTTP 429), git.launchpad.net (файлы пакетов Ubuntu `rsyslog` и `systemd` — недоступен).
