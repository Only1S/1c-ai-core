# Управление пакетами в Ubuntu Server: apt, dpkg, репозитории, фиксация версий, обновления

> Область: установка, обновление, фиксация и откат пакетов на сервере «1С:Предприятие 8» + PostgreSQL под Ubuntu Server (apt, dpkg, репозитории, unattended-upgrades, needrestart, do-release-upgrade, snap, офлайн-установка) | Версии: Ubuntu 22.04 LTS jammy (apt 2.4.x), 24.04 LTS noble (apt 2.7.14 → 2.8.3), 26.04 LTS resolute (apt 3.2.0); PostgreSQL 14–18 (Postgres Pro 1C, «PostgreSQL с патчем от 1С», PGDG); платформа 1С 8.3.x / 8.5.x | Актуальность: 2026-10-10

Условные обозначения: **[офиц.]** — официальная документация/рекомендация (Canonical, Debian/APT, PGDG, Postgres Professional, 1С); **[практика]** — устоявшаяся практика сообщества; **[код]** — проверено по исходному коду программы (apt, unattended-upgrades, needrestart), но не на стенде; **⚠ не подтверждено** — утверждение не удалось проверить по первоисточнику на дату статьи, перед применением проверить на стенде.

> Фактчек 2026-10-10 (независимая рецензия): сверены с первоисточниками man-страницы apt 2.8.3/3.2.0, NEWS и changelog apt, исходники apt (`versionmatch.cc`, `policy.cc`), unattended-upgrades и needrestart, индексы `Release`/`Packages` архива Ubuntu, PGDG и repo.postgrespro.ru, release notes 24.04/26.04, документация платформы 1С 8.3.27 (конспекты в `kb/its-docs/`). Исправлено по итогам: поведение `APT::Default-Release` в Ubuntu, ожидание блокировки, способы поставки платформы 1С, зависимость «PostgreSQL с патчем от 1С» от `postgresql-common`, ключи Postgres Pro, синтаксис needrestart. Остаток непроверенного помечен «⚠».

## Кратко

1. `dpkg` — низкий уровень (ставит/удаляет один `.deb`, зависимости не скачивает); `apt` — высокий уровень (репозитории, зависимости, обновления). `apt` — для человека в терминале, `apt-get` / `apt-cache` — для скриптов (стабильный вывод) **[офиц.]**.
2. Базовый цикл: `sudo apt update` (обновить индексы) → `apt list --upgradable` (посмотреть) → `sudo apt upgrade` (обновить, ничего не удаляя) или `sudo apt full-upgrade` (может удалять пакеты).
3. Версии apt: 22.04 — 2.4.x; 24.04 — 2.7.14 (релиз) / 2.8.3 (updates); 26.04 — 3.2.0 (новый решатель зависимостей по умолчанию, `apt why` / `apt why-not`, команды `apt history-*`, `apt-key` удалён, TLS/хеши через OpenSSL).
4. С 24.04 системные репозитории описаны в формате deb822: `/etc/apt/sources.list.d/ubuntu.sources`. Однострочный формат (`*.list`) объявлен устаревшим, но будет удалён «не раньше 2029 года».
5. Сторонний репозиторий подключается так: ключ в отдельный файл (`/etc/apt/keyrings/` — ключи администратора, `/usr/share/keyrings/` — ключи из пакетов) + `Signed-By:` в описании источника. `apt-key` устарел; в 26.04 его нет вообще.
6. Для 1С годятся только сборки PostgreSQL из списка поддерживаемых СУБД (Postgres Pro 1С, «PostgreSQL с патчем от 1С», Postgres Pro Standard/Enterprise, Tantor и др.). «Ванильного» PostgreSQL из PGDG или из архива Ubuntu в этом списке нет.
7. Репозиторий Postgres Pro для 1С: `https://repo.postgrespro.ru/1c/1c-NN/` (NN = 14…18), подключается скриптом `keys/pgpro-repo-add.sh`; пакеты `postgrespro-1c-NN*`, версии вида `18.4-1.noble`. В индексе лежит **только последняя** версия; старые — в `https://repo.postgrespro.ru/1c/archive/1c-NN.M/`.
8. Фиксация версии: `sudo apt-mark hold <пакет>` / `unhold` / `showhold`. На сервере 1С пакеты СУБД держат на hold и обновляют только вручную в окно обслуживания.
9. Тонкая настройка источников и версий — pinning: файлы `/etc/apt/preferences.d/*.pref` (`Package:` / `Pin:` / `Pin-Priority:`). Приоритет ≥ 1000 разрешает даунгрейд, < 0 запрещает установку.
10. `unattended-upgrades` на Ubuntu Server включён по умолчанию и ставит обновления безопасности ежедневно. Настройка: `/etc/apt/apt.conf.d/50unattended-upgrades` (что и как) и `20auto-upgrades` (включено/частота). Исключения — `Unattended-Upgrade::Package-Blacklist`.
11. Начиная с 24.04 `needrestart` **сам перезапускает службы**, чьи библиотеки обновились, в том числе во время unattended-upgrades. PostgreSQL и сервер 1С нужно исключить через `$nrconf{override_rc}` в `/etc/needrestart/conf.d/`.
12. Запуск автообновлений — systemd-таймеры `apt-daily.timer` (6:00 и 18:00 + случайная задержка до 12 ч) и `apt-daily-upgrade.timer` (6:00 + до 60 мин).
13. Нужна ли перезагрузка: существует файл `/var/run/reboot-required` (список пакетов — `/var/run/reboot-required.pkgs`).
14. «The following packages have been kept back» — чаще всего phased updates (постепенная раскатка), hold или обновление требует удаления пакетов. Это не ошибка.
15. `do-release-upgrade`: LTS→LTS открывается после первого точечного релиза (24.04 → 26.04.1 открыт 29.09.2026); сторонние репозитории на время обновления отключаются; меняются glibc/ICU (→ переиндексация баз PostgreSQL), имена библиотек, версия PostgreSQL в архиве. Для сервера 1С+PostgreSQL безопаснее развернуть новую ВМ и перенести базы.
16. В списке ОС для сервера 1С на v8.1c.ru (на 10.10.2026) указаны Ubuntu 20.04 / 22.04 / 24.04 LTS; Ubuntu 26.04 там нет — причина не торопиться с 26.04 в продуктиве.
17. Блокировка apt («Could not get lock /var/lib/dpkg/lock-frontend») — нельзя удалять lock-файлы при живом процессе; правильно ждать: `apt-get -o DPkg::Lock::Timeout=300 …`. Команда `apt` в терминале ждёт блокировку dpkg сама и бессрочно, без терминала — 120 с; `apt-get` по умолчанию не ждёт вовсе (NEWS apt 1.9.11).
18. Журналы: `/var/log/apt/history.log` (что и какой командой), `/var/log/apt/term.log` (вывод), `/var/log/dpkg.log` (каждое изменение состояния пакета).
19. Откат версии: `sudo apt install пакет=версия` — работает, только если старая версия где-то доступна (кеш `/var/cache/apt/archives`, архивный репозиторий, snapshot.ubuntu.com). Лучший откат на ВМ — снимок (checkpoint/snapshot) перед обновлением.
20. Локальный `.deb` ставят так: `sudo apt install ./файл.deb` (зависимости подтянутся сами). snap для СУБД и 1С на сервере не используют.
21. `APT::Default-Release "noble";` в Ubuntu **не использовать**: все «карманы» (`noble-updates`, `-security`, `-backports`, `-proposed`) имеют `Codename: noble`, поэтому все они получают приоритет 990 — пакеты из `-backports` (подключён по умолчанию) и из `-proposed` (если подключён) начинают ставиться автоматически **[код]** (раздел 7.3).
22. Платформа 1С на Linux ставится одним из двух несовместимых способов **[офиц., документация 8.3.27]**: программой установки `setup-full-<версия>-x86_64.run` (пакетный менеджер ОС не используется, apt о платформе не знает) либо deb/rpm-пакетами `1c-enterprise-<версия>-<компонента>`. «PostgreSQL с патчем от 1С» — это deb-пакеты с теми же именами, что в архиве Ubuntu (`postgresql-NN`, `postgresql-client-NN`, `libpq5`), и им нужен `postgresql-common` из архива Ubuntu.

## 1. Как устроена система пакетов

| Слой | Инструменты | Что делает |
|---|---|---|
| Пакет `.deb` | `dpkg-deb` | архив: файлы + управляющая информация (зависимости, скрипты preinst/postinst/prerm/postrm, conffiles) |
| Низкий уровень | `dpkg`, `dpkg-query`, `dpkg-reconfigure` | установка/удаление конкретного `.deb`, база установленных пакетов; зависимости проверяет, но сам ничего не скачивает |
| Высокий уровень | `apt`, `apt-get`, `apt-cache`, `apt-mark`, `apt-config`, `apt-file` | репозитории, расчёт зависимостей, загрузка, обновления, фиксация |
| Автоматика | `unattended-upgrades`, `needrestart`, таймеры `apt-daily*` | автоустановка обновлений, перезапуск служб |
| Параллельная система | `snap` (snapd) | самодостаточные пакеты с собственным автообновлением, от apt не зависят |

Ключевые пути:

| Путь | Назначение |
|---|---|
| `/etc/apt/sources.list`, `/etc/apt/sources.list.d/*.list`, `*.sources` | описания репозиториев |
| `/etc/apt/apt.conf.d/` | настройки apt (читаются в алфавитном порядке; имя файла — без расширения или `.conf`) |
| `/etc/apt/preferences`, `/etc/apt/preferences.d/` | pinning (приоритеты версий/источников) |
| `/etc/apt/keyrings/`, `/usr/share/keyrings/` | ключи репозиториев (для `Signed-By`) |
| `/etc/apt/trusted.gpg.d/` | «глобально доверенные» ключи (устаревающий механизм) |
| `/etc/apt/auth.conf.d/` | логины/пароли к закрытым репозиториям и прокси |
| `/var/lib/apt/lists/` | скачанные индексы (`Release`, `Packages`) |
| `/var/cache/apt/archives/` | скачанные `.deb` |
| `/var/lib/dpkg/status` | база установленных пакетов dpkg |
| `/var/lib/dpkg/info/` | списки файлов и скрипты пакетов |
| `/var/log/apt/`, `/var/log/dpkg.log` | журналы |

Что в каком релизе (проверено по Launchpad, release notes и индексам репозиториев):

| Ubuntu | Кодовое имя | apt | glibc | Ядро GA | PostgreSQL в архиве Ubuntu | libicu | Стандартная поддержка до |
|---|---|---|---|---|---|---|---|
| 22.04 LTS | jammy | 2.4.5 → 2.4.14 | 2.35 | 5.15 | 14 | 70 | весна 2027 |
| 24.04 LTS | noble | 2.7.14 → 2.8.3 | 2.39 | 6.8 | 16 | 74 | весна 2029 |
| 26.04 LTS | resolute | 3.2.0 | 2.43 | 7.0 | 18 | 78 | апрель 2031 |

Примечания: в release notes 26.04 apt назван «3.1», в архиве resolute опубликован 3.2.0 — на конкретной машине смотреть `apt --version`. Следующий промежуточный релиз — 26.10 «Stonking Stingray» (не LTS, для сервера 1С не применять). Узнать свой релиз: `lsb_release -a` или `. /etc/os-release; echo $VERSION_CODENAME`.

## 2. apt: команды

### 2.1. Сводная таблица

| Команда | Что делает | Замечания |
|---|---|---|
| `apt update` | скачивает свежие индексы пакетов из всех источников | ничего не устанавливает; выполнять перед любой установкой |
| `apt upgrade` | обновляет установленные пакеты, **не удаляя** ничего; может доставить новые зависимости | пакеты, для которых нужно что-то удалить, остаются «kept back» |
| `apt full-upgrade` | как upgrade, но **может удалять** пакеты ради обновления | синоним `apt-get dist-upgrade`; с apt 2.1.16 заодно убирает неиспользуемые ядра |
| `apt install П…` | установить/обновить пакеты | `П=версия`, `П/выпуск`, `./файл.deb`; суффикс `П-` — удалить в той же транзакции |
| `apt reinstall П` | переустановить ту же версию | восстановление испорченных файлов пакета (конфиги не трогает) |
| `apt remove П` | удалить пакет, **оставив** конфигурационные файлы | состояние `rc` в `dpkg -l` |
| `apt purge П` | удалить вместе с конфигами | данные (например, каталог кластера PostgreSQL) пакеты обычно не удаляют, но проверять |
| `apt autoremove` | удалить автоматически установленные зависимости, которые больше никому не нужны | `--purge` — вместе с конфигами; `apt autopurge` — то же |
| `apt search ШАБЛОН` | поиск по именам и описаниям (regex) | `apt-cache search --names-only` — только по именам |
| `apt show П` | карточка пакета: версия, зависимости, размер, источник | `apt show П=версия`, `-a` — все версии |
| `apt list` | список пакетов по критерию | `--installed`, `--upgradable` (в man — `--upgradeable`, принимаются оба), `--all-versions` / `-a`, glob-шаблоны |
| `apt policy [П]` | приоритеты источников и версия-кандидат | главный инструмент отладки pinning и «почему ставится не та версия» |
| `apt depends П` / `apt rdepends П` | прямые / обратные зависимости | `--installed`, `--recurse` |
| `apt download П` | скачать `.deb` в текущий каталог без установки | root не нужен; зависимости не скачивает |
| `apt changelog П` | показать changelog пакета | для пакетов из сторонних репозиториев часто недоступен |
| `apt clean` | удалить все `.deb` из `/var/cache/apt/archives` | |
| `apt autoclean` | удалить из кеша только те `.deb`, которых уже нет в репозиториях | |
| `apt distclean` (`apt-get dist-clean`) | как `clean`, плюс удаляет скачанные индексы из `/var/lib/apt/lists` (остаются только `Release`, `Release.gpg`, `InRelease`) | apt ≥ 2.7.8, т. е. 24.04+; в 22.04 нет. После него нужен `apt update`. Удобно перед созданием шаблона/снимка ВМ |
| `apt satisfy 'строка зависимостей'` | удовлетворить произвольную строку зависимостей | `apt satisfy 'libicu74 (>= 74.1)'` |
| `apt edit-sources` | открыть источники в редакторе с проверкой | в man помечено как work-in-progress |
| `apt showsrc`, `apt source`, `apt build-dep` | работа с исходными пакетами | нужен `deb-src` |
| `apt why П` / `apt why-not П` | объяснение решателя: почему пакет установлен / почему не может быть установлен | apt ≥ 3.1 (Ubuntu 26.04) |
| `apt history-list`, `history-info ID`, `history-undo ID`, `history-redo ID`, `history-rollback ID` | журнал транзакций apt и откат на уровне пакетов | `history-list`/`history-info` — apt ≥ 3.1.6, `undo`/`redo`/`rollback` — apt ≥ 3.1.7 (changelog apt); в 26.04 (apt 3.2.0) есть все **[офиц., release notes 26.04]**; в 22.04/24.04 нет. В man apt(8) 3.2.0 эти команды не описаны |
| `apt modernize-sources` | преобразовать `*.list` в deb822 `*.sources` (старые файлы → `.bak`) | apt 3.x (26.04); в 24.04 нет |

### 2.2. Полезные опции (общие для apt и apt-get)

| Опция | Смысл |
|---|---|
| `-y`, `--yes`, `--assume-yes` | отвечать «да» на вопросы |
| `-s`, `--simulate`, `--dry-run` | показать, что будет сделано, ничего не меняя (root не нужен) |
| `-V`, `--verbose-versions` | показывать полные версии «было → станет» |
| `-d`, `--download-only` | только скачать в кеш |
| `--no-install-recommends` | не ставить рекомендуемые пакеты (меньше лишнего на сервере) |
| `--only-upgrade` | с `install`: обновить, только если пакет уже установлен |
| `--no-upgrade` | с `install`: не обновлять уже установленные |
| `--reinstall` | переустановить |
| `-f`, `--fix-broken` | починить сломанные зависимости |
| `-t ВЫПУСК`, `--target-release` | предпочесть указанный выпуск (например, `-t noble-backports`) |
| `--allow-downgrades` | разрешить понижение версии без вопроса (нужно для отката с `-y`) |
| `--allow-change-held-packages` | разрешить менять пакеты на hold (опасно) |
| `--no-remove` | прервать, если что-то придётся удалить |
| `--with-new-pkgs` | для `apt-get upgrade`: разрешить доустановку новых зависимостей (у `apt upgrade` включено) |
| `-U`, `--update` | выполнить `update` перед командой (24.04+) |
| `-S ID`, `--snapshot ID` | работать с архивом Ubuntu на момент времени (snapshot.ubuntu.com, см. 12.3) |
| `--print-uris` | вместо скачивания вывести URL-ы пакетов |
| `-o Ключ=Значение` | разово задать любой параметр конфигурации |
| `--allow-releaseinfo-change` | для `update`: принять изменение Origin/Label/Suite репозитория |
| `--ignore-hold` | для `apt-get`: игнорировать hold (опасно; для разового осознанного обновления лучше `apt-mark unhold`) |
| `--audit` | включить вывод диагностических сообщений уровня «audit» (например, `apt update --audit`); появился в apt 2.9.2 (changelog), т. е. из LTS есть только в 26.04 — в man apt-get(8) для 24.04 (apt 2.8.3) такого ключа нет |

### 2.3. Примеры

```bash
# Обычное обновление с предварительным просмотром
sudo apt update
apt list --upgradable
sudo apt upgrade -s            # симуляция
sudo apt upgrade -V            # с показом версий

# Установка без «рекомендуемых» пакетов
sudo apt install --no-install-recommends mc htop

# Конкретная версия пакета
apt list -a postgrespro-1c-18-server            # какие версии видны
sudo apt install postgrespro-1c-18-server=18.4-1.noble

# Версия из определённого выпуска
sudo apt install -t noble-backports cockpit
sudo apt install cockpit/noble-backports

# Обновить один пакет, не трогая остальные
sudo apt install --only-upgrade openssl

# Установить один пакет и удалить другой одной транзакцией
sudo apt install chrony systemd-timesyncd-

# Удаление с конфигами и подчистка зависимостей
sudo apt purge apache2 && sudo apt autoremove --purge

# Откуда пакет, какой кандидат, какие приоритеты
apt policy libpq5
apt policy                       # все источники с приоритетами

# Кому нужен пакет (среди установленных)
apt rdepends --installed libicu74

# Установленные пакеты, которых нет ни в одном подключённом репозитории
# (сторонние, вручную поставленные .deb, остатки после обновления релиза)
apt list '?obsolete'
```

Неинтерактивная установка в скриптах (без диалогов debconf и без вопросов про конфиги — оставить старый конфиг):

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get -y \
  -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold \
  install <пакет>
```

Вопрос dpkg при обновлении изменённого конфига: `Y/I` — поставить версию из пакета, `N/O` — оставить свою (по умолчанию), `D` — показать разницу, `Z` — открыть оболочку. Свой конфиг сохраняется, новый кладётся рядом как `*.dpkg-dist`; если принять новый — старый остаётся как `*.dpkg-old`.

### 2.4. apt, apt-get, apt-cache — в чём разница

| | `apt` | `apt-get` / `apt-cache` |
|---|---|---|
| Назначение | интерактивная работа | скрипты, автоматизация |
| Стабильность вывода/поведения | может меняться между версиями (apt предупреждает: «WARNING: apt does not have a stable CLI interface») | стабильный интерфейс |
| Индикатор прогресса, цвет, пейджер (apt 3.x) | да | нет |
| Команды только здесь | `list`, `full-upgrade`, `edit-sources`, `why`, `history-*`, `modernize-sources` | `dselect-upgrade`, `check`, `indextargets`; `apt-cache`: `madison`, `showpkg`, `stats`, `unmet`, `pkgnames`, `dotty` |
| `upgrade` | доустанавливает новые зависимости | без `--with-new-pkgs` — не доустанавливает |
| Скачанные `.deb` после установки | удаляет из кеша; отключается параметром `Binary::apt::APT::Keep-Downloaded-Packages "true";` **[офиц., NEWS apt 1.2~exp1; в man apt.conf(5) параметр не описан]** | оставляет в `/var/cache/apt/archives` |
| Ожидание блокировки dpkg | ждёт: в терминале — бессрочно, без терминала — 120 с **[офиц., NEWS apt 1.9.11]** | не ждёт, пока не задан `DPkg::Lock::Timeout` |

Соответствия: `apt full-upgrade` = `apt-get dist-upgrade`; `apt search/show/policy/depends/rdepends` = `apt-cache search/show/policy/depends/rdepends`; `apt list --installed` ≈ `dpkg -l`.

Полезное из `apt-cache`, чего нет в `apt`:

```bash
apt-cache madison postgrespro-1c-18-server    # таблица «версия | источник»
apt-cache showpkg libpq5                      # версии + обратные зависимости по версиям
apt-cache unmet                               # неудовлетворённые зависимости в кеше
apt-cache depends --recurse --no-recommends --no-suggests libpq5
```

Посмотреть действующую конфигурацию apt:

```bash
apt-config dump | less
apt-config dump | grep -i -E 'periodic|unattended|proxy'
```

### 2.5. apt-file — какой пакет содержит файл

`dpkg -S` ищет только среди **установленных** пакетов; `apt-file` — по индексам содержимого всех пакетов репозиториев.

```bash
sudo apt install apt-file
sudo apt-file update                    # скачать индексы Contents (десятки МБ)
apt-file search bin/pg_config           # в каком пакете есть такой файл
apt-file search -x '/libicuuc\.so\.[0-9]+$'   # -x — регулярное выражение
apt-file list unixodbc                  # список файлов пакета (даже не установленного)
```

## 3. dpkg, dpkg-query, dpkg-reconfigure, debconf

### 3.1. Команды dpkg

| Команда | Что делает |
|---|---|
| `dpkg -i файл.deb` (`--install`) | установить/обновить пакет из файла; зависимости **не** скачивает. `-R каталог` — все `.deb` рекурсивно |
| `dpkg --unpack файл.deb` | распаковать без настройки |
| `dpkg --configure П` / `--configure -a` (`--pending`) | настроить распакованный пакет / **все незавершённые** (первое средство после прерванной установки) |
| `dpkg -r П` (`--remove`) | удалить, оставив конфиги. Официальная документация Ubuntu Server не рекомендует — зависимые пакеты остаются сломанными; лучше `apt remove` |
| `dpkg -P П` (`--purge`) | удалить вместе с конфигами |
| `dpkg -l [шаблон]` (`--list`) | список пакетов со статусами |
| `dpkg -s П` (`--status`) | состояние и карточка установленного пакета |
| `dpkg -L П` (`--listfiles`) | какие файлы установил пакет |
| `dpkg -S путь` (`--search`) | какому установленному пакету принадлежит файл |
| `dpkg -C` (`--audit`) | проверка базы: частично установленные/ненастроенные пакеты |
| `dpkg -V [П]` (`--verify`) | сверить файлы пакета с контрольными суммами (изменённые/повреждённые) |
| `dpkg --get-selections [шаблон]` | вывести «пакет → состояние выбора» (install/hold/deinstall/purge) |
| `dpkg --set-selections` | прочитать такие пары со stdin |
| `dpkg --print-architecture` | основная архитектура (`amd64`) |
| `dpkg --add-architecture i386` / `--remove-architecture` / `--print-foreign-architectures` | мультиархитектура (после добавления — `apt update`) |
| `dpkg --compare-versions v1 OP v2` | сравнение версий (`lt le eq ne ge gt`), код возврата 0/1 |
| `dpkg -c файл.deb` / `-I файл.deb` / `-x файл.deb каталог` / `-e файл.deb каталог` | (через dpkg-deb) содержимое / метаданные / распаковать файлы / извлечь управляющие скрипты |
| `dpkg --force-…` | принудительные режимы: `confold`, `confnew`, `confdef`, `confmiss`, `depends`, `overwrite`, `all` — применять осознанно |

Колонки статуса в `dpkg -l` (первые две-три буквы):

| Позиция | Буквы | Значение |
|---|---|---|
| 1 — желаемое | `u` unknown, `i` install, `h` hold, `r` remove, `p` purge | что должно быть |
| 2 — фактическое | `n` not-installed, `c` config-files, `H` half-installed, `U` unpacked, `F` half-configured, `W` triggers-awaited, `t` triggers-pending, `i` installed | что есть |
| 3 — ошибка | `R` reinst-required | пакет надо переустановить |

Частые сочетания: `ii` — установлен; `rc` — удалён, конфиги остались; `hi` — установлен и на hold; `iU` — распакован, не настроен; `iF` — настройка упала (смотреть `/var/log/apt/term.log`); `un` — не установлен.

```bash
dpkg -l | grep -E 'postgres|1c-enterprise'      # что установлено из СУБД и 1С
dpkg -l 'postgrespro-1c-18*'                    # по шаблону
dpkg -s postgrespro-1c-18-server | grep -E '^(Status|Version|Depends)'
dpkg -L postgrespro-1c-18-server | grep -E 'bin/|\.service'
dpkg -S /usr/bin/psql                           # чей файл (для симлинков может не найти)
dpkg -S "$(readlink -f /usr/bin/psql)"          # чей файл с раскрытием симлинка
dpkg -l | awk '/^rc/ {print $2}'                # удалённые, но с остатками конфигов
dpkg -l | grep -v '^ii' | tail -n +6            # всё, что не в состоянии «ii»
sudo dpkg --audit                               # есть ли недоустановленное
sudo dpkg --configure -a                        # довести до конца прерванную установку
dpkg --compare-versions 18.4-1.noble gt 18.3-1.noble && echo newer
```

Перенос набора пакетов на другую машину того же релиза:

```bash
dpkg --get-selections > selections.txt          # на исходной
sudo dpkg --set-selections < selections.txt     # на целевой
sudo apt-get dselect-upgrade
```

### 3.2. dpkg-query — форматированные запросы

```bash
dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' 'postgres*'
dpkg-query -W -f='${Installed-Size}\t${Package}\n' | sort -n | tail -20     # самые «тяжёлые» пакеты (КиБ)
dpkg-query -W -f='${binary:Package}\n' 'postgrespro-1c-18*'                  # имена для подстановки в другие команды
dpkg-query -S '*/libicuuc.so*'                                               # поиск владельца по маске
```

`dpkg -l`, `-s`, `-L`, `-S`, `-p` — это фактически вызовы `dpkg-query`.

### 3.3. dpkg-reconfigure и debconf

Многие пакеты задают вопросы при установке через **debconf** и хранят ответы в его базе.

```bash
sudo dpkg-reconfigure tzdata                    # часовой пояс
sudo dpkg-reconfigure locales                   # сгенерировать локали (для 1С/PostgreSQL нужна ru_RU.UTF-8)
sudo dpkg-reconfigure -plow unattended-upgrades # включить/выключить автообновления (-plow — показать и «неважные» вопросы)
sudo dpkg-reconfigure -f noninteractive tzdata  # без диалога, с текущими ответами

sudo debconf-show unattended-upgrades           # сохранённые ответы пакета
sudo apt install debconf-utils
sudo debconf-get-selections | grep -i mscorefonts   # все ответы в формате для set-selections
```

`debconf-set-selections` — заранее задать ответы (preseed), чтобы установка прошла без вопросов. Формат строки: `пакет вопрос тип значение`.

```bash
# Принять лицензию шрифтов Microsoft (ttf-mscorefonts-installer нужен серверу 1С для печатных форм)
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ttf-mscorefonts-installer
```

Фронтенды debconf: `dialog` (по умолчанию), `readline`, `noninteractive`. Переменная `DEBIAN_FRONTEND=noninteractive` действует на один запуск; `DEBIAN_PRIORITY=critical` — показывать только критичные вопросы.

## 4. Установка локальных .deb и исправление зависимостей

```bash
# Рекомендуемый способ: apt сам подтянет зависимости из репозиториев
sudo apt install ./имя_версия_amd64.deb                  # обязателен путь: ./ или абсолютный
sudo apt install /tmp/pkgs/*.deb                         # несколько пакетов одной транзакцией

# Старый способ: dpkg, затем починка зависимостей
sudo dpkg -i *.deb
sudo apt -f install          # то же: sudo apt --fix-broken install

# gdebi — ставит .deb с зависимостями (пакет gdebi-core, universe; noble 0.9.5.7+nmu7, resolute 0.9.5.8)
sudo apt install gdebi-core
sudo gdebi файл.deb          # -n — без вопросов

# Посмотреть пакет до установки
dpkg -I файл.deb             # метаданные и зависимости
dpkg -c файл.deb             # список файлов
apt install -s ./файл.deb    # симуляция: что ещё будет установлено/удалено
```

Пояснения:

- Без `./` apt будет искать пакет с таким именем в репозиториях.
- `apt -f install` доустанавливает недостающие зависимости **или удаляет** пакет, который их не может получить, — читать план перед подтверждением.
- Сообщение `N: Download is performed unsandboxed as root as file '…' couldn't be accessed by user '_apt'` — безвредно: пользователь `_apt` не может прочитать файл в домашнем каталоге. Убирается, если положить `.deb` в `/tmp` или `/var/tmp`.
- Набор `.deb` «PostgreSQL с патчем от 1С» (с releases.1c.ru) и deb-пакеты платформы 1С ставятся именно так: все файлы набора одной командой `sudo apt install ./*.deb` (в официальном Dockerfile 1С для СУБД — `apt-get install -y --allow-downgrades /путь/*.deb`).
- Платформа 1С на Linux — два способа установки **[офиц., документация платформы 8.3.27, гл. 2.2–2.3]**, между собой **несовместимых** (чем ставили, тем и удаляют):
  - **программа установки** `setup-full-<версия>-x86_64.run` (на базе VMware InstallBuilder; только x86/x86-64; пакетный менеджер ОС не используется). На releases.1c.ru это дистрибутив «Технологическая платформа 1С:Предприятия (64-bit) для Linux» — архив `server64_*.zip` с `.run`-файлом внутри; в таком виде x86-64-дистрибутив поставляется начиная с 8.3.20 **[практика: скрипты onec-docker ветвятся по номеру релиза < 20 / ≥ 20; официальный репозиторий 1C-Company/docker_fresh ставит платформу именно так]**. Пакетный режим: `sudo ./setup-full-8.3.27.1688-x86_64.run --mode unattended --enable-components server,ws,server_admin,liberica_jre,ru`;
  - **пакетный менеджер**: файлы по шаблону из документации `1c-enterprise-<A.B.C.D>-<компонента>_<A.B.C-D>.<arch>.deb` (компоненты `common`, `server`, `ws`, `crs`, `client`, `thin-client` и их `-nls`; `arch` для DEB — `amd64`, `arm64`, `e2k-8c`), пример из документации: `1c-enterprise-8.3.22.100-common_8.3.22-100.arm64.deb`. Имя пакета в базе dpkg, как следует из шаблона имени файла, — `1c-enterprise-<A.B.C.D>-<компонента>` (искать: `dpkg -l '1c-enterprise*'`). Для ARM64 и «Эльбруса» это единственный способ (и только с лицензией КОРП). Ставить в порядке зависимостей (`common` → `server` → `ws`/`client`) либо разом через `sudo apt install ./1c-enterprise-*.deb`; `thin-client` конфликтует с `common`. ⚠ не подтверждено: публикуются ли на releases.1c.ru deb-пакеты **сервера** для x86-64 в актуальных версиях (в скрипте загрузки официального репозитория 1C-Company/docker_fresh фигурирует только «Клиент 1С:Предприятия (64-bit) для DEB-based Linux-систем»); в реальных файлах перед архитектурой может стоять не точка, а подчёркивание (`…_amd64.deb`) — смотреть `ls`.
  - До 8.3.20 x86-64-дистрибутив для Ubuntu/Debian был набором deb-пакетов `1c-enterprise83-common`, `-server`, `-ws`, … **[офиц., старая инструкция ИТС 2018 г.]** (⚠ по памяти рецензента, не проверено: в 8.3.18–8.3.19 номер версии уже входил в имя пакета).

## 5. Репозитории

### 5.1. Два формата описания источников

**Однострочный** (`/etc/apt/sources.list`, `/etc/apt/sources.list.d/*.list`) — по умолчанию до 23.10 включительно; объявлен устаревшим:

```
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu jammy main restricted universe multiverse
#тип [опции через пробел, значения через запятую]                          URI                          выпуск  компоненты…
```

**deb822** (`/etc/apt/sources.list.d/*.sources`) — по умолчанию с 24.04. Файл системных источников — `/etc/apt/sources.list.d/ubuntu.sources`:

```
Types: deb
URIs: http://archive.ubuntu.com/ubuntu/
Suites: noble noble-updates noble-backports
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://security.ubuntu.com/ubuntu/
Suites: noble-security
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
```

Блоки (stanza) разделяются пустой строкой; несколько значений в поле — через пробел.

| Поле deb822 | Опция в однострочном | Смысл |
|---|---|---|
| `Types:` | `deb` / `deb-src` | бинарные и/или исходные пакеты |
| `URIs:` | URI | адрес архива; схемы `http`, `https`, `file`, `copy`, `cdrom`, `mirror+…` |
| `Suites:` | выпуск | `noble`, `noble-updates`, `noble-pgdg`…; если заканчивается на `/` — «плоский» репозиторий, тогда `Components` не указывается |
| `Components:` | компоненты | `main universe …` |
| `Enabled: no` | закомментировать строку | отключить блок, не удаляя |
| `Architectures:` | `arch=` | ограничить архитектуры (`amd64`) |
| `Signed-By:` | `signed-by=` | путь(и) к файлу ключей, отпечаток или встроенный блок ключа. Несколько файлов: в deb822 — через пробел, в однострочном формате — через запятую. Файл должен быть читаем пользователем `_apt` (права 0644) |
| `Trusted: yes` | `trusted=yes` | считать источник доверенным без проверки подписи (только для локальных репозиториев) |
| `Snapshot:` | `snapshot=` | работа со снимками архива: `yes`/`no` (в man apt 3.x — `enable`/`disable`) либо ID снимка |
| `Include:` / `Exclude:` | `include=` / `exclude=` | ограничить набор пакетов, используемых из источника (взаимоисключающие; apt ≥ 3.1, т. е. 26.04) |
| `Check-Valid-Until: no` | `check-valid-until=no` | не проверять срок действия Release (для старых снимков/архивов) |
| `Allow-Insecure`, `Allow-Weak`, `Allow-Downgrade-To-Insecure` | то же в нижнем регистре | ослабление проверок — избегать |

Правила имён файлов в `sources.list.d`: только буквы, цифры, `_`, `-`, `.`; расширение строго `.list` или `.sources`. Файлы с другими расширениями игнорируются — этим удобно пользоваться для отключения: `.disabled`, `.bak`, `~`, `.dpkg-*` пропускаются молча (список `Dir::Ignore-Files-Silently`), для прочих apt выводит уведомление «N: Ignoring file …».

Перевод старых файлов в deb822 (apt 3.x, Ubuntu 26.04): `sudo apt modernize-sources` — создаёт `*.sources`, старые файлы переименовывает в `*.list.bak`, проставляет `Signed-By` там, где может определить ключ; опции в квадратных скобках, которые не удалось перенести, нужно дописать вручную.

### 5.2. Компоненты и «карманы» архива Ubuntu

| Компонент | Что внутри | Поддержка |
|---|---|---|
| `main` | свободное ПО, поддерживаемое Canonical | обновления безопасности 5 лет |
| `restricted` | проприетарные драйверы, поддерживаемые Canonical | да |
| `universe` | свободное ПО сообщества | обновления безопасности не гарантированы; через Ubuntu Pro (esm-apps) — да |
| `multiverse` | несвободное/с лицензионными ограничениями | нет |

`universe` и `multiverse` в Ubuntu включены по умолчанию. Пакеты `gdebi-core`, `checkinstall`, `apt-offline`, `ttf-mscorefonts-installer` (multiverse) живут именно там.

| Карман (суффикс выпуска) | Назначение |
|---|---|
| `noble` | состояние на момент релиза, не меняется |
| `noble-security` | обновления безопасности (их ставит unattended-upgrades) |
| `noble-updates` | исправления ошибок; раскатываются поэтапно (phased updates) |
| `noble-backports` | новые версии отдельных пакетов; приоритет 100 — сами не ставятся |
| `noble-proposed` | тестовые обновления; с 24.04 приоритет 100 — сами не ставятся; на продуктиве не включать |

Включить/выключить компонент или сменить зеркало:

```bash
sudo add-apt-repository universe                      # включить компонент
sudoedit /etc/apt/sources.list.d/ubuntu.sources       # 24.04+: поправить URIs / Components вручную
sudoedit /etc/apt/sources.list                        # 22.04
sudo apt update
```

Зеркала стран имеют вид `http://<код_страны>.archive.ubuntu.com/ubuntu/`; `security.ubuntu.com` лучше оставлять как есть (обновления безопасности появляются там раньше, чем на зеркалах).

### 5.3. Ключи: signed-by, /etc/apt/keyrings и почему apt-key устарел

Каждый репозиторий подписывает файл `InRelease`/`Release` своим OpenPGP-ключом; apt проверяет подпись при `apt update`.

Почему `apt-key` плох: он добавлял ключ в общее хранилище (`/etc/apt/trusted.gpg`, позже `/etc/apt/trusted.gpg.d/`), которому apt доверяет **для всех** источников. Владелец любого стороннего ключа получал возможность подписать подменённый «системный» пакет. `Signed-By` привязывает ключ к конкретному репозиторию.

Хронология (по NEWS пакета apt и release notes Ubuntu):

| Версия apt / Ubuntu | Что изменилось |
|---|---|
| apt 2.4 (22.04) | появился каталог `/etc/apt/keyrings` — рекомендованное место для ключей, не управляемых пакетами; ключи из старого `trusted.gpg` ещё работают, но с предупреждением «Key is stored in legacy trusted.gpg keyring» |
| apt 2.7/2.8 (24.04) | `apt-key` ещё есть, но помечен устаревшим (man: «will last be available in … Ubuntu 24.04»); требуются ключи RSA ≥ 2048 бит, Ed25519 или Ed448 — на RSA-1024 сначала предупреждение, затем (обновление apt 2.8.x) ошибка |
| apt 2.9.15 | apt перестал использовать apt-key для проверки подписей; имена файлов в `trusted.gpg.d` — только буквы, цифры и `_ - : .` (иначе файл молча игнорируется) |
| apt 2.9.24 | `/etc/apt/trusted.gpg` больше **не** считается доверенным; источники без `Signed-By` объявлены устаревшими (вместе с каталогом `trusted.gpg.d`) |
| apt 3.x (26.04) | `apt-key` удалён; подписи проверяются напрямую (`gpgv`/Sequoia); криптография — через OpenSSL |

Если `Signed-By` не указан, apt (включая 3.2) всё ещё берёт ключи из `/etc/apt/trusted.gpg.d/` — поэтому старые скрипты подключения, кладущие ключ туда, пока работают, но это устаревающий путь.

Форматы файлов ключей: `.gpg` — бинарный (подходит всем версиям apt), `.asc` — ASCII-armored (apt ≥ 1.4, т. е. все актуальные Ubuntu). Расширение должно соответствовать содержимому.

Типовое подключение стороннего репозитория (шаблон):

```bash
sudo install -d -m 0755 /etc/apt/keyrings

# Вариант А: сохранить ключ как есть (ASCII) — расширение .asc
sudo curl -fsSL https://repo.example.com/key.asc -o /etc/apt/keyrings/example.asc

# Вариант Б: преобразовать в бинарный — расширение .gpg
curl -fsSL https://repo.example.com/key.asc | sudo gpg --dearmor -o /etc/apt/keyrings/example.gpg

sudo chmod 0644 /etc/apt/keyrings/example.*
gpg --show-keys /etc/apt/keyrings/example.asc      # посмотреть отпечаток и сверить с сайтом поставщика

# Описание источника (deb822)
. /etc/os-release
sudo tee /etc/apt/sources.list.d/example.sources >/dev/null <<EOF
Types: deb
URIs: https://repo.example.com/ubuntu
Suites: $VERSION_CODENAME
Components: main
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/example.asc
EOF

sudo apt update
apt policy | grep -A2 repo.example.com
```

Перенос ключа из устаревшего общего хранилища (22.04/24.04, где `apt-key` ещё есть):

```bash
apt-key list                                         # найти ключ, последние 8 символов отпечатка — его ID
sudo apt-key export 1A2B3C4D | sudo gpg --dearmor -o /etc/apt/keyrings/example.gpg
sudo apt-key del 1A2B3C4D
# затем дописать signed-by=/etc/apt/keyrings/example.gpg в описание источника
```

Официальная документация Ubuntu Server о сторонних репозиториях **[офиц.]**: пакеты из них ставятся с правами root без какой-либо изоляции; конфликты со штатными пакетами — самая частая причина сбоев обновления релиза; рекомендуется настраивать pinning и вместо обновления релиза разворачивать систему заново на новом релизе.

### 5.4. add-apt-repository и PPA

`add-apt-repository` входит в пакет `software-properties-common` (в минимальных образах может отсутствовать).

```bash
sudo apt install software-properties-common
sudo add-apt-repository ppa:владелец/имя        # подключить PPA (ключ ставится автоматически) и сделать apt update
sudo add-apt-repository -y -n ppa:владелец/имя  # -y без вопроса, -n без apt update
sudo add-apt-repository -r ppa:владелец/имя     # отключить PPA (пакеты из него остаются!)
sudo add-apt-repository -L                      # показать подключённые источники
sudo add-apt-repository universe                # включить компонент
sudo add-apt-repository "deb [signed-by=/etc/apt/keyrings/x.gpg] https://repo.example.com/ubuntu noble main"

sudo apt install ppa-purge
sudo ppa-purge ppa:владелец/имя                 # отключить PPA и вернуть пакеты к версиям из архива Ubuntu
```

- PPA (Personal Package Archive, Launchpad) — репозиторий частного лица/команды; origin вида `LP-PPA-владелец-имя`. В 24.04+ PPA записывается как deb822-файл в `/etc/apt/sources.list.d/` со встроенным в `Signed-By` ключом; по наблюдаемой практике имя файла — `<владелец>-ubuntu-<имя>-<кодовое_имя>.sources`, например `deadsnakes-ubuntu-ppa-noble.sources` (в 22.04 — `…-jammy.list` и ключ в `/etc/apt/trusted.gpg.d/`). ⚠ не подтверждено по первоисточнику: в man add-apt-repository(1) и release notes схема имени не описана, исходники software-properties открыть не удалось — смотреть `ls /etc/apt/sources.list.d/`.
- `add-apt-repository` не настраивает pinning — пакеты PPA получают приоритет 500 и могут заменить системные.
- На сервере 1С+PostgreSQL PPA не нужны; ни 1С, ни Postgres Professional через PPA ничего не распространяют **[практика]**.

## 6. Рабочие примеры: репозитории PostgreSQL

Сначала главное: фирма «1С» в списке поддерживаемых СУБД (v8.1c.ru, на 10.10.2026) для x86-64 указывает, в частности: **Postgres Pro 1С** 18.4 / 17.10 / 16.14 / 15.18 / 14.23; **PostgreSQL с патчем от 1С** 18.4-1.1C / 17.10-2.1C / 16.14-1.1C / 15.18-1.1C / 14.23-1.1C (дистрибутивы на releases.1c.ru); Postgres Pro Standard / Enterprise (и CERT-варианты) 18.4.1 … 14.23.1; Tantor SE 1C. Обычного PostgreSQL сообщества (PGDG, пакет `postgresql` из архива Ubuntu) в списке нет. Соответствие версий СУБД конкретным версиям платформы на этой странице не приводится — см. статью базы знаний о PostgreSQL для 1С.

### 6.1. Репозиторий Postgres Pro для 1С (repo.postgrespro.ru)

Структура (проверено по листингу каталога на 10.10.2026): `https://repo.postgrespro.ru/1c/` → `1c-14/`, `1c-15/`, `1c-16/`, `1c-17/`, `1c-18/`, `archive/`, `installers/`. Внутри каждой ветки: `keys/`, `ubuntu/`, `debian/`, `altlinux/`, `redos/`, `rhel/`, `rosa/`, `sles/`, `win/` и файл `meta.json` (официальные команды установки и список ОС). Для Ubuntu в ветке 1c-18 есть `dists/`: `focal`, `jammy`, `noble`, `oracular`, `questing`, `resolute`; при этом в `meta.json` ветки 1c-18 поддерживаемыми названы Ubuntu 22.04, 24.04, 25.10, 26.04 (только x86_64). Тот же сервер отвечает по имени `repo.postgres.ru` (именно оно записано в официальных командах и в файле источника, который создаёт скрипт).

Официальный способ — скрипт из каталога `keys/` **[офиц., Postgres Professional, `meta.json`]**:

```bash
wget https://repo.postgres.ru/1c/1c-18/keys/pgpro-repo-add.sh
less pgpro-repo-add.sh                 # прочитать, что именно он сделает
sudo sh pgpro-repo-add.sh

# Вариант 1 (официальный): сборка для 1С — единственный PostgreSQL на машине.
# Метапакет сам создаёт кластер по умолчанию и запускает службу.
sudo apt-get install postgrespro-1c-18

# Вариант 2 (официальный): на машине уже есть другой PostgreSQL (например, при переходе
# с предыдущей мажорной версии) — без метапакета, инициализация вручную.
sudo apt-get install postgrespro-1c-18-contrib
sudo /opt/pgpro/1c-18/bin/pg-setup initdb
sudo /opt/pgpro/1c-18/bin/pg-setup service enable
sudo /opt/pgpro/1c-18/bin/pg-setup service start
```

Что делает скрипт на Ubuntu (по тексту скрипта ветки 1c-18):

- определяет дистрибутив по `/etc/os-release` (`ID`, `VERSION_CODENAME`) и архитектуру (`dpkg --print-architecture`);
- создаёт `/etc/apt/sources.list.d/postgresql-1c-18.list` со строкой вида `deb https://repo.postgres.ru/1c/1c-18/ubuntu noble main` (однострочный формат, **без** `signed-by`); если файл уже есть — завершается с кодом 2;
- кладёт ключ в `/etc/apt/trusted.gpg.d/postgrespro.gpg` (бинарный формат; `apt-key` не используется); для Ubuntu 26.04 и Debian 13 записывает два ключа (старый и новый), для остальных — один;
- при необходимости ставит `apt-transport-https` и выполняет `apt-get update`;
- если репозиторий закрыт паролем, спрашивает логин/пароль и пишет их в `/etc/apt/auth.conf.d/<хост>.conf` (права 0600).

В каталоге `keys/` лежат также сами ключи (проверено по содержимому файлов на 10.10.2026; все три — ASCII-armored):

| Файл | Что внутри |
|---|---|
| `GPG-KEY-POSTGRESPRO` | один блок — «старый» ключ (RSA 2048, создан в 2015 г.) |
| `GPG-KEY-POSTGRESPRO-2` | один блок — «новый» ключ (RSA 4096, создан в 2025 г.) |
| `GPG-KEY-POSTGRESPRO-COMBO` | два блока подряд: старый ключ (блок длиннее, чем в `GPG-KEY-POSTGRESPRO`, т. е. в обновлённой редакции) и новый ключ (совпадает с `GPG-KEY-POSTGRESPRO-2`) |

Скрипт для Ubuntu 26.04 / Debian 13 устанавливает именно пару ключей, для более старых релизов — один старый ключ.

Ручной вариант в стиле deb822 с `Signed-By` (⚠ не подтверждено на стенде: официально описан только скрипт; вариант собран по содержимому скрипта и каталога `keys/`). Ключ преобразуется в бинарный `.gpg` — так же поступает сам скрипт, и это снимает вопрос, читает ли apt `.asc`-файл с двумя блоками:

```bash
sudo install -d -m 0755 /etc/apt/keyrings
# COMBO содержит оба ключа — годится и для 22.04/24.04, и для 26.04
curl -fsSL https://repo.postgres.ru/1c/1c-18/keys/GPG-KEY-POSTGRESPRO-COMBO \
  | sudo gpg --dearmor -o /etc/apt/keyrings/postgrespro.gpg
sudo chmod 0644 /etc/apt/keyrings/postgrespro.gpg
gpg --show-keys /etc/apt/keyrings/postgrespro.gpg     # должно быть ДВА ключа; отпечатки сверить с поставщиком
. /etc/os-release
sudo tee /etc/apt/sources.list.d/postgrespro-1c-18.sources >/dev/null <<EOF
Types: deb
URIs: https://repo.postgres.ru/1c/1c-18/ubuntu
Suites: $VERSION_CODENAME
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/postgrespro.gpg
EOF
sudo apt update && apt policy postgrespro-1c-18
```

Замечания к ручному варианту:

- Нужна программа `gpg` (пакет `gpg`/`gnupg`; в минимальных образах может отсутствовать — `sudo apt install gpg`).
- Не держать одновременно файл от скрипта (`postgresql-1c-18.list`, без `signed-by`) и свой `.sources` на тот же URL — получится `E: Conflicting values set for option Signed-By…` или дубли «configured multiple times».
- Скрипт кладёт ключ в `/etc/apt/trusted.gpg.d/` — это устаревающий «общий» каталог доверия (раздел 5.3): в 26.04 (apt 3.2) он ещё работает, но источники без `Signed-By` объявлены устаревшими. Ручной вариант с `Signed-By` привязывает ключ только к этому репозиторию.
- Имя хоста в `URIs` определяет, что писать в `Pin: origin …` (раздел 7.3): `repo.postgres.ru` или `repo.postgrespro.ru` — используйте одно и то же везде.
- Если `gpg --show-keys` показал один ключ вместо двух (⚠ поведение `gpg --dearmor` на файле из двух armored-блоков на стенде не проверялось), скачайте `GPG-KEY-POSTGRESPRO` и `GPG-KEY-POSTGRESPRO-2` отдельными файлами `.asc` и перечислите оба в `Signed-By` через пробел.

Пакеты ветки 1c-18 для noble (все одной версии `18.4-1.noble` на 14.07.2026):

| Пакет | Назначение |
|---|---|
| `postgrespro-1c-18` | метапакет: зависит от `-server`, `-client`, `-contrib` той же версии |
| `postgrespro-1c-18-server` | сервер СУБД |
| `postgrespro-1c-18-client` | psql, pg_dump и др. |
| `postgrespro-1c-18-libs` | libpq и другие библиотеки |
| `postgrespro-1c-18-contrib` | расширения (в т. ч. нужные 1С) |
| `postgrespro-1c-18-dev` | заголовки, pg_config |
| `postgrespro-1c-18-jit` | JIT (LLVM) |
| `postgrespro-1c-18-plperl`, `-plpython3`, `-pltcl` | процедурные языки |
| `postgrespro-1c-18-docs`, `-docs-ru` | документация |
| `*-dbgsym` | отладочные символы |

Важные свойства этих пакетов (из индекса `Packages`):

- В версию зашито кодовое имя релиза Ubuntu: `18.4-1.noble`, `18.4-1.resolute`, `17.10-1.jammy`. Пакет собран под библиотеки конкретного релиза: на noble `postgrespro-1c-18-server` зависит от `libc6 (>= 2.38)`, `libicu74`, `libssl3t64`, `libxml2`; на resolute — от `libc6 (>= 2.43)`, `libicu78`, `libxml2-16`; ветка 17 на jammy — от `libicu70`, `libssl3`, `libldap-2.5-0`. Пакет от другого релиза Ubuntu не установится или не запустится.
- Метапакет `postgrespro-1c-18` объявляет `Conflicts: postgrespro-common, postgresql-common, postgresql-common-pro-1c` — его нельзя поставить рядом с PostgreSQL из архива Ubuntu/PGDG (они зависят от `postgresql-common`).
- В индексе репозитория лежит только текущая версия. Предыдущие — в архиве: `https://repo.postgrespro.ru/1c/archive/1c-18.3/ubuntu`, `…/1c-17.9/ubuntu` и т. д. Каталоги есть только для реально выпускавшихся сборок, а не для каждой минорной версии сообщества: на 10.10.2026 для ветки 18 — `1c-18.0`, `1c-18.1`, `1c-18.3`, `1c-18.4`; для ветки 17 — `1c-17.0`, `17.2`, `17.4`, `17.5`, `17.6`, `17.7`, `17.9`, `17.10`; самые старые — `1c-9.6.x` и `1c-10.x`. Перед обновлением убедитесь, что каталог с **вашей текущей** версией в архиве есть, — иначе откатиться можно будет только на сохранённые `.deb`.
- Серверный пакет и `-contrib` зависят друг от друга (`-server` → `-contrib`, `-contrib` → `-server (= версия)`), а `-server` жёстко требует `-client (= версия)`: обновлять, понижать и замораживать нужно **все** пакеты `postgrespro-1c-18*` одной командой.
- Файл `Release` этого репозитория содержит `Origin: Ubuntu`, `Label: Postgres Professional Repository`, `Codename: noble`, поля `Suite` нет. Поэтому в pinning этот репозиторий нужно отбирать по хосту (`Pin: origin repo.postgres.ru` — то имя, которое записано в файле источника) или по метке (`l=Postgres Professional Repository`), а **не** по `o=`: условие `o=Ubuntu` совпадёт и с ним.

Раскладка (по документации Postgres Pro для продуктов этого семейства и `meta.json` ветки): бинарные файлы — `/opt/pgpro/1c-18/bin/`, данные — `/var/lib/pgpro/1c-18/data/`, служба — `postgrespro-1c-18`. Инициализация вручную (вариант 2) — `/opt/pgpro/1c-18/bin/pg-setup initdb` **[офиц.]**: кластер создаётся от имени `postgres`, локаль берётся из переменной `LANG` (переменные `LC_*` игнорируются), после команды можно дописать параметры `initdb` (например, `--locale=ru_RU.UTF-8`). Уточнено 11.10.2026 по документации самой сборки (`https://repo.postgrespro.ru/doc/pg1c/18/ru/html/`, страницы `app-initdb`, `app-pgpro-tune`; конспект — `kb/guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`): утилита `pgpro_tune` и пресет `1c.tune` в сборке «для 1С» документированы, применить пресет можно явно — `pgpro_tune -D <каталог данных> --no-default -P /opt/pgpro/1c-NN/share/1c.tune`; сама быстрая установка его не применяет (по коду пакетов 16.14 метапакет вызывает `pg-setup initdb` без параметров, выполняется только `default.tune`); а вот это по-прежнему не подтверждено для актуальных версий: встречающаяся в старых руководствах форма `pg-setup initdb --tune=1c` — в справке `pg-setup` значения `tune` не перечислены, а про сборку «для 1С» поставщик пишет, что параметры конфигурации выставляются автоматически под характеристики машины (1c.postgres.ru). Подробности — в статье `kb/postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`.

Условия использования (со страницы 1c.postgres.ru): сборки бесплатны для любых целей, кроме предоставления СУБД как сервиса и встраивания в свои продукты; без гарантий и техподдержки; обновления могут отставать от основной ветки; только 64-бит.

### 6.2. Репозиторий PGDG (apt.postgresql.org)

Это репозиторий сообщества PostgreSQL (PostgreSQL Global Development Group). Поддерживаемые Ubuntu: jammy (22.04), noble (24.04), resolute (26.04), stonking (26.10, только amd64); архитектуры amd64, arm64, ppc64el. Версии PostgreSQL: 13–18, а также 19 beta (на 10.10.2026 PostgreSQL 19 ещё не вышел: 24.09.2026 выпущена Beta 4).

**Для сервера баз 1С PGDG не применять** — это не сборка с патчами 1С. Где он уместен: клиентские утилиты нужной версии на рабочей станции администратора, отдельные серверы не под 1С, стенды.

Автоматически **[офиц.]**:

```bash
sudo apt install -y postgresql-common ca-certificates
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
```

Вручную **[офиц.]**:

```bash
sudo apt install curl ca-certificates
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc

. /etc/os-release
sudo tee /etc/apt/sources.list.d/pgdg.sources <<EOF
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: $VERSION_CODENAME-pgdg
Architectures: $(dpkg --print-architecture)
Components: main
Signed-By: /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
EOF

sudo apt update
sudo apt install postgresql-18          # именно с номером версии
```

Особенности:

- Метапакеты `postgresql` и `postgresql-client` всегда тянут **последнюю** мажорную версию: после выхода PostgreSQL 19 обычный `apt upgrade` доустановит рядом новый сервер. Ставить нужно пакет с номером: `postgresql-18`, `postgresql-client-18`.
- `Release` репозитория (проверено 10.10.2026): `Origin: apt.postgresql.org`, `Label: PostgreSQL for Debian/Ubuntu repository`, `Suite: noble-pgdg`, `Codename: noble-pgdg`, архитектуры `amd64 arm64 ppc64el`. Все поддерживаемые версии лежат в компоненте `main` (нумерованные компоненты `13`…`20` нужны для особых случаев — бета-версий и библиотек конкретной версии). В pinning: `Pin: release o=apt.postgresql.org` или `Pin: origin apt.postgresql.org`.
- Есть выпуски `<codename>-pgdg-snapshot` (ежедневные сборки) и архив старых версий на `apt-archive.postgresql.org`: выпуск `<codename>-pgdg-archive` содержит все когда-либо публиковавшиеся версии пакетов:

```
deb https://apt-archive.postgresql.org/pub/repos/apt noble-pgdg-archive main
```

- Пакеты PGDG называются так же, как в архиве Ubuntu (`postgresql-16`, `libpq5`, `postgresql-common`), и имеют более высокие версии — после подключения PGDG `apt upgrade` заменит системные `libpq5` и `postgresql-common` на версии PGDG. Если это нежелательно — pinning (раздел 7.3).

### 6.3. «PostgreSQL с патчем от 1С» — набор .deb без репозитория

Дистрибутив скачивается с releases.1c.ru (нужна учётная запись с доступом к обновлениям) как архив с `.deb`-файлами и ставится локально:

```bash
sudo apt install bzip2 postgresql-common               # postgresql-common — из архива Ubuntu, он нужен пакетам сборки
mkdir /tmp/pg1c && tar -xf postgresql_*.tar.bz2 -C /tmp/pg1c          # имя архива зависит от версии и ОС
find /tmp/pg1c -name '*.deb' | sort                    # deb-файлы могут лежать во вложенном каталоге
for f in $(find /tmp/pg1c -name '*.deb'); do dpkg-deb -f "$f" Package Version Depends; echo; done
cd <каталог с .deb>
apt-get install -s ./*.deb | grep -E '^(Inst|Remv)'    # «всухую»: что будет установлено/удалено
sudo apt install ./*.deb                               # в скриптах: apt-get install -y --allow-downgrades ./*.deb
sudo apt-mark hold $(dpkg-query -W -f='${binary:Package} ${Version}\n' | awk '$2 ~ /1C$/ {print $1}')
apt-mark showhold
```

Что подтверждено, а что нет:

- **Имена пакетов — те же, что в архиве Ubuntu/PGDG** (`postgresql-NN`, `postgresql-client-NN`, `libpq5`), версия оканчивается на `.1C` (например, `18.4-1.1C`) **[практика: руководства сообщества для версий 10–15 — три пакета `libpq5*.deb`, `postgresql-client-NN*.deb`, `postgresql-NN*.deb`; номера версий вида `18.4-1.1C` — официальный список СУБД на v8.1c.ru]**. ⚠ не подтверждено: точный состав архива для 17–18 (возможны `-dbgsym` и дополнительные пакеты) — страницы releases.1c.ru закрыты; проверяйте `dpkg-deb -f` по каждому файлу.
- **Сборке нужен `postgresql-common` из архива Ubuntu** (раскладка как у штатных пакетов Debian/Ubuntu: `pg_createcluster`, `/etc/postgresql/NN/main`, служба `postgresql@NN-main`) **[практика]** — его **нельзя** запрещать закреплением (см. пример 1 в разделе 7.3). `apt install ./*.deb` подтянул бы его и сам; заранее его ставят, чтобы до установки сервера при необходимости отключить автосоздание кластера (`create_main_cluster = false` в `/etc/postgresql-common/createcluster.conf`). Серверный пакет при установке сам создаёт кластер `NN/main` с локалью из окружения установки — перед установкой убедитесь, что сгенерирована и выбрана `ru_RU.UTF-8` (`locale`, `sudo dpkg-reconfigure locales`), подробности — в статье `kb/postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`.
- С 2025–2026 гг. 1С публикует отдельные дистрибутивы под конкретные версии ОС (в скрипте официального репозитория 1C-Company/docker_fresh — «Дистрибутив СУБД PostgreSQL для Debian 13.0 x86 (64-bit) одним архивом»): берите архив под **свою** версию Ubuntu, иначе не сойдутся зависимости `libicuNN`/`libssl`/`libllvmNN`.
- Именно из-за совпадения имён без hold/pinning первый же `apt upgrade` может заменить пакеты сборки «обычными» с большей версией (в архиве Ubuntu 24.04 — PostgreSQL 16, в 26.04 — 18; в PGDG — все версии) — и 1С перестанет работать с базой. Hold обязателен; дополнительная страховка — пример 3 в разделе 7.3.

## 7. Фиксация версий: apt-mark hold и pinning

### 7.1. Почему это критично для сервера 1С + PostgreSQL

1. **Совместимость.** 1С работает только с конкретными сборками PostgreSQL (раздел 6). Замена сборки на «обычную» из архива Ubuntu или PGDG (у которой версия выше) ломает работу информационных баз.
2. **Обновление пакета СУБД = перезапуск СУБД.** Скрипты пакета при обновлении останавливают и запускают службу. Если это произойдёт днём (ручной `apt upgrade` «заодно» или автообновление), пользователей 1С выбросит, а длительные операции (проведение, обмены, реструктуризация) оборвутся.
3. **Откат затруднён.** В репозитории Postgres Pro 1С лежит только последняя версия; без заранее сохранённых `.deb` или архивного репозитория вернуться нельзя.
4. **Связка версий.** Минорные версии СУБД и версия платформы 1С проверяются фирмой «1С» парами; обновлять их нужно осознанно, после чтения списка поддерживаемых СУБД и замечаний к релизу платформы, сначала на копии.
5. **Системные библиотеки.** Обновление glibc / libicu меняет правила сортировки строк — индексы PostgreSQL по текстовым полям могут стать некорректными (раздел 9.2). Внутри одного LTS-релиза Ubuntu мажорные версии glibc и ICU не меняются, но это ещё один довод не обновлять всё подряд без плана.
6. **Платформа 1С, поставленная программой установки, не под контролем apt.** Установленная через `setup-full-….run` платформа живёт в `/opt/1cv8/x86_64/<версия>/` и удаляется собственной программой `uninstaller-full` из каталога версии (`sudo /opt/1cv8/x86_64/8.3.24.100/uninstaller-full`). По документации платформы 8.3.27 **[офиц.]** программа установки пакетный менеджер ОС не использует, а «установленное программой установки удалить пакетным менеджером нельзя» — то есть в базе dpkg такой установки нет (на стенде это видно по пустому выводу `dpkg -l '1c-enterprise*'`; ⚠ сам вывод команды рецензентом не проверялся). Следствия:
   - apt платформу не обновит, не удалит и не учтёт как потребителя библиотек: `apt autoremove` может удалить нужные ей библиотеки, если они числятся «автоматически установленными» и больше никому не нужны. Библиотеки-зависимости 1С стоит пометить как установленные вручную: `sudo apt-mark manual <пакет>…`;
   - программа установки перед установкой пытается сама доустановить недостающие зависимости и шрифты Microsoft Core Fonts (сначала из репозитория ОС, затем с зеркал SourceForge по HTTP), а чего поставить не смогла — показывает списком: эти пакеты ставятся вручную через apt **[офиц.]**. На сервере без интернета шрифты и зависимости готовят заранее (раздел 11.3);
   - если платформа поставлена deb-пакетами `1c-enterprise-<версия>-*`, она видна в `dpkg -l '1c-enterprise*'` и удаляется пакетным менеджером (`sudo apt purge '1c-enterprise-<версия>-*'`), а программой удаления — нельзя **[офиц.]**. Зависимости между пакетами платформы apt учитывает; системные библиотеки, по документации, должны стоять заранее (их ставит скрипт `v8-install-deps.sh` из поставки) — ⚠ насколько полно они объявлены в поле `Depends` пакетов, не проверено (`dpkg -s 1c-enterprise-<версия>-server | grep Depends`), поэтому `apt-mark manual` для библиотек уместен и здесь. Одноимённых пакетов в архиве Ubuntu нет, так что apt их сам не заменит.

Вывод **[практика]**: пакеты СУБД — на hold; автообновление для них запрещено дополнительно через `Package-Blacklist`; обновление — вручную, в окно, после резервной копии и снимка ВМ.

### 7.2. apt-mark

| Команда | Что делает |
|---|---|
| `apt-mark hold П…` | заморозить: пакет не будет автоматически установлен, обновлён или удалён |
| `apt-mark unhold П…` | снять заморозку |
| `apt-mark showhold` | показать замороженные |
| `apt-mark manual П…` / `apt-mark auto П…` | пометить как установленный вручную / автоматически (влияет на `autoremove`) |
| `apt-mark showmanual` / `showauto` | списки |
| `apt-mark minimize-manual` | пометить зависимости метапакетов как автоматические |

```bash
# Заморозить все установленные пакеты Postgres Pro 1C 18
dpkg-query -W -f='${binary:Package}\n' 'postgrespro-1c-18*' | xargs sudo apt-mark hold
apt-mark showhold

# Плановое обновление СУБД в окно обслуживания
sudo apt-mark unhold $(apt-mark showhold | grep '^postgrespro-1c-18')
sudo apt update
apt list --upgradable 2>/dev/null | grep postgrespro
sudo apt install --only-upgrade $(dpkg-query -W -f='${binary:Package}\n' 'postgrespro-1c-18*')
dpkg-query -W -f='${binary:Package}\n' 'postgrespro-1c-18*' | xargs sudo apt-mark hold

# Чтобы autoremove не снёс библиотеки, нужные платформе 1С (пример)
sudo apt-mark manual unixodbc libgsf-1-114 fontconfig
```

Как hold проявляется:

- `apt upgrade` / `full-upgrade` пропускают пакет и пишут `The following packages have been kept back`;
- явный `apt install П` для замороженного пакета apt выполнит только после подтверждения, а в режиме `-y` завершится ошибкой `E: Held packages were changed and -y was used without --allow-change-held-packages.`;
- hold хранится в базе dpkg как «selection state»: `dpkg --get-selections | grep hold`; то же самое можно сделать через `echo "пакет hold" | sudo dpkg --set-selections`;
- `dpkg -i новый.deb` hold **не** остановит — dpkg ставит то, что ему дали (по man dpkg hold удерживает только от автоматических действий, «если они не запрошены явно»);
- hold не мешает удалению пакета командой `apt remove П`, названной явно (apt покажет «The following held packages will be changed» и спросит подтверждение);
- `unattended-upgrades` пакеты на hold не трогает **[код]**: в функции `is_pkg_change_allowed` проверяется состояние `SELSTATE_HOLD`, в отладочном журнале — строка `pkg <имя> is on hold` (раздел 8.1);
- перед `do-release-upgrade` hold снимают осознанно (раздел 9.1): как обновлятор релиза обходится с замороженными пакетами, документация Ubuntu не описывает; по практике hold приводит к ошибке расчёта обновления («Could not calculate the upgrade») **[практика]**.

Чего hold не делает: не защищает от обновления **зависимостей** (libc6, libicu, libssl), не запрещает установку «конкурента» с другим именем, не действует на snap.

### 7.3. Pinning: /etc/apt/preferences.d

Файлы: `/etc/apt/preferences` и `/etc/apt/preferences.d/*` (имя — без расширения или с `.pref`; только буквы, цифры, `-`, `_`, `.`). Формат записи (записи разделяются пустой строкой):

```
Explanation: необязательный комментарий
Package: <имена через пробел | glob | /regex/ | src:имя_исходного | *>
Pin: version <шаблон> | release <ключ=значение,…> | origin <имя_хоста>
Pin-Priority: <число>
```

Ключи `Pin: release`: `a=` (Suite/архив: `noble-updates`), `n=` (Codename: `noble`), `o=` (Origin из Release: `Ubuntu`, `apt.postgresql.org`, `LP-PPA-…`), `l=` (Label), `c=` (компонент: `main`), `v=` (версия выпуска: `24.04`). `Pin: origin` — это **имя хоста** из URI источника, а не поле Origin.

Приоритеты по умолчанию и смысл диапазонов:

| Приоритет | Кому назначается / что означает |
|---|---|
| 1 | выпуски с `NotAutomatic: yes`; версии, не прошедшие поэтапную раскатку (phased) |
| 100 | уже установленная версия; выпуски `NotAutomatic` + `ButAutomaticUpgrades` (backports; с 24.04 — proposed) |
| 500 | все остальные источники |
| 990 | целевой выпуск (`-t` или `APT::Default-Release`) |
| P ≥ 1000 | ставить, **даже если это даунгрейд** |
| 990 ≤ P < 1000 | ставить, даже если не из целевого выпуска, если установленная версия не новее |
| 500 ≤ P < 990 | ставить, если нет версии из целевого выпуска и установленная не новее |
| 100 ≤ P < 500 | ставить, только если нет версии из других источников и установленная не новее |
| 0 < P < 100 | ставить, только если пакет вообще не установлен |
| P < 0 | **никогда не устанавливать** |
| P = 0 | не использовать (поведение не определено) |

Правила выбора: побеждает версия с наибольшим приоритетом; при равных — более новая; даунгрейд — только при P ≥ 1000. Из «конкретных» записей (с именем пакета) действует первая подошедшая; из «общих» (`Package: *`) — максимальная.

Примеры для сервера 1С.

**Пример 1.** Запретить установку PostgreSQL из архива Ubuntu — чтобы никто случайно не поставил `postgresql` рядом со сборкой для 1С и чтобы одноимённые пакеты «PostgreSQL с патчем от 1С» не были заменены системными. Файл `/etc/apt/preferences.d/no-distro-postgresql.pref`:

```
Explanation: на этом сервере используется сборка PostgreSQL для 1С, системный PostgreSQL запрещён
Package: postgresql postgresql-[0-9]* postgresql-client postgresql-client-[0-9]* postgresql-contrib postgresql-common
Pin: release o=Ubuntu
Pin-Priority: -1
```

Проверка: `apt policy postgresql postgresql-common` — у версий из архива Ubuntu приоритет `-1`, `Candidate: (none)` либо уже установленная версия. Замечания:

- Запись в таком виде (с `postgresql-common`) годится **только для сервера со сборкой Postgres Pro 1С**: её метапакет и так конфликтует с `postgresql-common`.
- Для сценария **«PostgreSQL с патчем от 1С» `postgresql-common` из списка нужно убрать** (как и не добавлять `postgresql-client-common`): пакеты сборки 1С зависят от `postgresql-common` из архива Ubuntu, и с приоритетом `-1` установка завершится ошибкой вида «Depends: postgresql-common … but it is not installable». Вместо него в список стоит добавить `libpq5` (он входит в набор 1С) — предварительно посмотрев, кому ещё нужен системный `libpq5`: `apt rdepends --installed libpq5`. Установленная версия `.1C` при этом остаётся кандидатом (у неё приоритет 100, у версий Ubuntu — `-1`).
- Условие `o=Ubuntu` совпадает и с репозиторием Postgres Pro 1С (у него тоже `Origin: Ubuntu`), но его пакеты называются иначе (`postgrespro-1c-*`) и под запись не попадают.
- На PGDG (`o=apt.postgresql.org`) запись не действует: если он подключён, нужен отдельный запрет или пример 4.

**Пример 2.** Закрепить конкретную версию сборки Postgres Pro 1С (альтернатива hold: версия-кандидат видна в `apt policy`, возврат на неё разрешён). Файл `/etc/apt/preferences.d/postgrespro-1c.pref`:

```
Package: postgrespro-1c-18*
Pin: version 18.4-1.noble
Pin-Priority: 1001
```

**Пример 3.** Защитить «PostgreSQL с патчем от 1С» от замены одноимёнными пакетами из любого источника, включая PGDG. Файл `/etc/apt/preferences.d/postgresql-1c-patch.pref`:

```
Package: postgresql* libpq5 libpq-dev libecpg* libpgtypes*
Pin: version *.1C
Pin-Priority: 1001
```

Как это работает **[код: apt-pkg/versionmatch.cc]**: в `Pin: version` завершающая `*` означает совпадение по префиксу (пример из man — `5.32*`), а любой другой шаблон сопоставляется через `fnmatch()` без учёта регистра — поэтому `*.1C` совпадает с любой версией, оканчивающейся на `.1C`. Версия сборки 1С получает приоритет 1001, одноимённые версии из Ubuntu/PGDG — обычные 500, и кандидатом остаётся сборка 1С, даже если в репозитории версия «новее». ⚠ на стенде не проверялось — после создания файла обязательно посмотреть `apt policy postgresql-18 libpq5` (у установленной версии должно стоять 1001, `Candidate` = `Installed`) и `sudo apt upgrade -s`. Закрепление не заменяет hold: при установке нового набора `.deb` от 1С (тоже `.1C`) оно не мешает, а от явного `apt install postgresql-18=<версия Ubuntu>` не защищает.

**Пример 4.** Понизить приоритет стороннего репозитория, чтобы он не подменял системные пакеты (рекомендация документации Ubuntu **[офиц.]**: 100 — можно ставить и получать обновления уже установленного; 1 — можно ставить явно, автоматических обновлений не будет). Файл `/etc/apt/preferences.d/pgdg.pref`:

```
Package: *
Pin: origin apt.postgresql.org
Pin-Priority: 100
```

Для общего закрепления (`Package: *`) репозитория Postgres Pro 1С использовать `Pin: origin repo.postgres.ru` (хост из файла источника) или `Pin: release l=Postgres Professional Repository`, но не `o=Ubuntu`.

Проверка и отладка:

```bash
apt policy                         # все источники и их приоритеты, список закреплений («Pinned packages»)
apt policy postgrespro-1c-18-server libpq5
apt-cache policy | grep -B1 -A2 postgres
sudo apt upgrade -s | grep -i -E 'postgres|kept back'
```

В выводе `apt policy П` строка `Candidate:` — то, что будет установлено; число перед версией в «Version table» — итоговый приоритет; `***` — установленная версия.

Предостережения:

- **`APT::Default-Release` в Ubuntu лучше не задавать вовсе** **[код: apt-pkg/policy.cc, versionmatch.cc + файлы `Release` архива Ubuntu]**. Параметр создаёт закрепление с приоритетом 990 на выпуск, который сопоставляется с полем `Suite` (архив) **или** `Codename`:
  - `APT::Default-Release "noble";` — в Ubuntu у всех «карманов» `Codename: noble` (`Suite` у них разные: `noble`, `noble-updates`, `noble-security`, `noble-backports`, `noble-proposed`), поэтому **все** они получают 990. Обновления безопасности при этом ставятся как обычно, но теряется защитный приоритет 100 у `-backports` (подключён по умолчанию) и `-proposed`: пакеты из них начинают выбираться как обычные обновления. (Ловушка «security-обновления перестали приходить» из руководств по Debian относится именно к Debian, где у security-выпуска другое кодовое имя — `bookworm-security`.)
  - `APT::Default-Release "a=noble";` (форма «ключ=значение») — совпадает только с `Suite: noble`; тогда `noble-updates`/`noble-security` остаются с 500 против 990, и для ещё не обновлявшихся пакетов кандидатом становится версия на момент релиза — исправления безопасности не выбираются.
  - Если нужно отдать предпочтение выпуску разово — `-t`/`--target-release` в конкретной команде с именем кармана (`-t noble-backports`); `-t noble` по той же причине совпадёт со всеми карманами сразу. Проверка любых экспериментов: `apt policy` (числа перед источниками) и `apt upgrade -s`.
  - ⚠ на стенде не проверялось: вывод сделан по исходному коду apt и по файлам `Release` (`noble-security`: `Suite: noble-security`, `Codename: noble`; `noble-backports`: `Suite: noble-backports`, `Codename: noble`, `NotAutomatic: yes`, `ButAutomaticUpgrades: yes`).
- Pinning с приоритетом ≥ 1000 на `Package: *` может вызвать массовый даунгрейд — всегда сначала `apt upgrade -s`.
- Pinning и hold не отменяют необходимость читать план транзакции перед «Y».

## 8. Автоматические обновления

### 8.1. unattended-upgrades

**По умолчанию на Ubuntu Server [офиц.]:** пакет `unattended-upgrades` установлен и включён; раз в сутки обновляются индексы и ставятся обновления **безопасности** (карман `-security`, а при подключённом Ubuntu Pro — ещё ESM). Обычные обновления (`-updates`) и сторонние репозитории автоматически не ставятся, пока их origin не добавлен в `Allowed-Origins`.

Файлы:

| Файл | Назначение |
|---|---|
| `/etc/apt/apt.conf.d/20auto-upgrades` | включение и периодичность |
| `/etc/apt/apt.conf.d/50unattended-upgrades` | что обновлять и как (источники, исключения, перезагрузка, почта) |
| `/var/log/unattended-upgrades/unattended-upgrades.log` | журнал решений |
| `/var/log/unattended-upgrades/unattended-upgrades-dpkg.log` | вывод dpkg при автообновлениях |
| `/usr/lib/apt/apt.systemd.daily` | скрипт, который запускают таймеры |

`20auto-upgrades` (значение — период в днях; `0` — выключено):

```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

Другие параметры группы `APT::Periodic` (описаны в заголовке `/usr/lib/apt/apt.systemd.daily`): `Download-Upgradeable-Packages` (заранее скачивать обновления), `AutocleanInterval` (периодический `autoclean`), `Enable`, `Verbose`. Текущие значения: `apt-config dump APT::Periodic`.

Основные параметры `50unattended-upgrades`:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `Unattended-Upgrade::Allowed-Origins { … };` | `"${distro_id}:${distro_codename}"`, `…-security`, `"${distro_id}ESMApps:${distro_codename}-apps-security"`, `"${distro_id}ESM:${distro_codename}-infra-security"` (в свежих версиях пакета — ещё `…-apps-legacy-security` и `…-infra-legacy-security`); строки `-updates`, `-proposed`, `-backports` закомментированы | из каких источников ставить; формат `"Origin:Suite"` (вторая часть — поле `Suite`, см. ниже) |
| `Unattended-Upgrade::Package-Blacklist { … };` | пусто | регулярные выражения (Python) имён пакетов, которые **не** обновлять; сопоставление с начала имени |
| `Unattended-Upgrade::DevRelease` | `"auto"` | поведение на разрабатываемом релизе |
| `Unattended-Upgrade::AutoFixInterruptedDpkg` | `"true"` | выполнять `dpkg --configure -a` при прерванной установке |
| `Unattended-Upgrade::MinimalSteps` | `"true"` | ставить минимальными шагами (можно прервать) |
| `Unattended-Upgrade::Mail` | не задано | адрес для отчётов (нужен настроенный MTA/почтовый клиент) |
| `Unattended-Upgrade::MailReport` | `"on-change"` | `always` / `only-on-error` / `on-change` |
| `Unattended-Upgrade::Remove-Unused-Kernel-Packages` | `"true"` | удалять старые ядра |
| `Unattended-Upgrade::Remove-New-Unused-Dependencies` | `"true"` | удалять зависимости, ставшие ненужными после этого обновления |
| `Unattended-Upgrade::Remove-Unused-Dependencies` | `"false"` | полный аналог `apt autoremove` |
| `Unattended-Upgrade::Automatic-Reboot` | `"false"` | перезагружаться, если появился `/var/run/reboot-required` |
| `Unattended-Upgrade::Automatic-Reboot-WithUsers` | `"true"` | перезагружаться даже при вошедших пользователях |
| `Unattended-Upgrade::Automatic-Reboot-Time` | `"now"` | время перезагрузки (`"02:00"` или `"+5"`) |
| `Acquire::http::Dl-Limit` | не задано | ограничение скорости загрузки, КиБ/с |
| `Unattended-Upgrade::SyslogEnable` / `SyslogFacility` | `"false"` / `"daemon"` | дублировать журнал в syslog |
| `Unattended-Upgrade::Allow-downgrade` | `"false"` | разрешить даунгрейд при pin ≥ 1000 |
| `Unattended-Upgrade::Postpone-For-Days` | (Ubuntu 25.04+, т. е. из LTS — 26.04) | на сколько дней пользователю разрешено отложить автообновление; `0` — возможность отключена. Парный параметр `Unattended-Upgrade::Postpone-Wait-Time` — сколько секунд ждать ответа. На сервере без своего D-Bus-клиента (сигнал `AboutToStart`, метод `Postpone()`) ни на что не влияет |
| `Unattended-Upgrade::InstallOnShutdown` | `"false"` | ставить обновления при выключении, а не в фоне (на сервере не включать) |
| `Unattended-Upgrade::Allow-APT-Mark-Fallback` | `"true"` | при неудаче расчёта подбирать кандидатов зависимостям по отдельности |
| `Unattended-Upgrade::Origins-Pattern { … };` | не задано в Ubuntu | альтернатива `Allowed-Origins` с ключами `origin=`, `codename=`, `label=`, `archive=`, `component=`, `site=` |

**Рекомендуемая настройка для сервера 1С + PostgreSQL [практика].** Обновления безопасности ОС оставить, СУБД/веб-сервер/ядро исключить, перезагрузку не разрешать. Изменения лучше класть в отдельный файл (он читается позже `50unattended-upgrades` и не конфликтует с обновлениями самого пакета):

```
// /etc/apt/apt.conf.d/52unattended-upgrades-local
Unattended-Upgrade::Package-Blacklist {
    "postgrespro-";        // сборка Postgres Pro для 1С
    "postgresql";          // «PostgreSQL с патчем от 1С» / системный PostgreSQL
    "libpq5$";
    "apache2";             // веб-публикация 1С
    "linux-";              // ядро — только в окно обслуживания (по желанию)
    "libc6$";
    "libc-bin$";
    "locales$";
    "libicu";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "admin@example.com";
Unattended-Upgrade::MailReport "only-on-error";
```

Замечания:

- Исключение пакета может заблокировать обновления, которые от него зависят (предупреждение документации Ubuntu). Заблокированные пакеты нужно регулярно обновлять вручную, иначе сервер останется без исправлений безопасности.
- Пакеты на hold автообновление не трогает **[код]**: в скрипте `unattended-upgrade` функция `is_pkg_change_allowed` возвращает отказ для пакетов из blacklist и для пакетов в состоянии `SELSTATE_HOLD` (в отладочном выводе — `pkg <имя> is on hold`). В документации Ubuntu про hold ничего не сказано (там описан только `Package-Blacklist`), поэтому blacklist и hold стоит использовать вместе и проверять пробным прогоном `--dry-run -d`.
- Как сопоставляется `Allowed-Origins` **[код]**: строка `"Origin:Suite"` превращается в шаблон `o=<Origin>,a=<Suite>` — вторая часть сравнивается с полем `Suite` файла `Release` (в `apt policy` это `a=`), **а не** с `Codename` (`n=`); сравнение — по правилам shell-шаблонов (`fnmatch`). Более гибкая форма — `Unattended-Upgrade::Origins-Pattern { "origin=…,codename=…,label=…"; };` (ключи `o`/`origin`, `l`/`label`, `a`/`archive`/`suite`, `c`/`component`, `n`/`codename`, `site`).
- Сторонние репозитории в `Allowed-Origins` не входят. `Release` репозитория Postgres Pro 1С содержит `Origin: Ubuntu` и `Codename: noble`, но поля `Suite` в нём **нет** (проверено по файлам `dists/noble/Release` и `dists/resolute/Release` на 10.10.2026), поэтому под штатные шаблоны `"Ubuntu:noble"` / `"Ubuntu:noble-security"` он не попадает **[код]** и автоматически обновляться не должен. ⚠ на стенде не проверялось, а поставщик может в любой момент добавить `Suite` в `Release` — поэтому blacklist/hold обязательны, а контроль такой: в `apt-cache policy` у строки репозитория Postgres Pro не должно быть `a=noble`; в выводе `sudo unattended-upgrade --dry-run -d` пакеты `postgrespro-*` не должны попадать в список к обновлению. Свои шаблоны вида `"origin=Ubuntu"` или `"o=Ubuntu,n=noble"` в `Origins-Pattern` этот репозиторий **захватят** — не использовать.
- Список `Package-Blacklist` из отдельного файла **добавляется** к списку из `50unattended-upgrades` (списочные параметры apt.conf накапливаются), а скалярные параметры (`Automatic-Reboot`, `Mail`) переопределяются последним прочитанным файлом — поэтому имя своего файла должно сортироваться после `50…`.

Проверка и ручной запуск:

```bash
sudo unattended-upgrade -v --dry-run      # что было бы установлено (ничего не меняет)
sudo unattended-upgrade -d                # выполнить сейчас с отладочным выводом
tail -n 50 /var/log/unattended-upgrades/unattended-upgrades.log
grep -B2 -A6 unattended /var/log/apt/history.log | tail -40
apt-config dump | grep -E 'Unattended-Upgrade|APT::Periodic'
```

Варианты ограничения:

```bash
# А. Только скачивать, ставить вручную
printf '%s\n' 'APT::Periodic::Update-Package-Lists "1";' \
              'APT::Periodic::Download-Upgradeable-Packages "1";' \
              'APT::Periodic::Unattended-Upgrade "0";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades

# Б. Полностью выключить автоматику apt
printf '%s\n' 'APT::Periodic::Update-Package-Lists "0";' \
              'APT::Periodic::Unattended-Upgrade "0";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer     # дополнительно — остановить таймеры

# В. То же через диалог
sudo dpkg-reconfigure -plow unattended-upgrades

# Г. Удалить пакет совсем (не рекомендуется: сервер остаётся без автоматических исправлений безопасности)
sudo apt purge unattended-upgrades
```

Когда отключать совсем — оправдано лишь там, где обновления ставятся дисциплинированно вручную по регламенту или централизованно (Landscape, Ansible). Иначе лучше вариант «безопасность ОС автоматически, СУБД и 1С — вручную».

### 8.2. Таймеры apt-daily

Содержимое штатных юнитов (пакет apt):

```ini
# apt-daily.timer — обновление индексов и загрузка
[Timer]
OnCalendar=*-*-* 6,18:00
RandomizedDelaySec=12h
Persistent=true

# apt-daily-upgrade.timer — установка (unattended-upgrade) и очистка; After=apt-daily.timer
[Timer]
OnCalendar=*-*-* 6:00
RandomizedDelaySec=60m
Persistent=true
```

То есть установка обновлений по умолчанию происходит между 6:00 и 7:00 по времени сервера — для сервера 1С это уже рабочее время в части часовых поясов. `Persistent=true` означает: если машина была выключена, задание выполнится сразу после загрузки (типично для ВМ — обновление стартует в момент включения и держит блокировку apt).

```bash
systemctl list-timers 'apt-daily*'                  # когда сработают в следующий раз
systemctl cat apt-daily.timer apt-daily-upgrade.timer
journalctl -u apt-daily-upgrade.service --since yesterday

# Перенести установку обновлений на 03:00–03:15 и не «догонять» пропущенное
sudo systemctl edit apt-daily-upgrade.timer
```

В открывшемся редакторе:

```ini
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:00
RandomizedDelaySec=15m
Persistent=false
```

(пустая строка `OnCalendar=` сбрасывает штатное расписание; после сохранения — `sudo systemctl daemon-reload` выполняется автоматически, проверить `systemctl list-timers`).

### 8.3. needrestart

`needrestart` после установки/обновления пакетов (хук apt) проверяет, какие процессы продолжают использовать старые версии библиотек, и нужно ли новое ядро.

**Важно [офиц., release notes 24.04]:** начиная с Ubuntu 24.04 needrestart **автоматически перезапускает** службы, затронутые обновлением библиотек, — в том числе при неинтерактивных запусках (unattended-upgrades). В 22.04 при ручном `apt upgrade` показывался диалог выбора служб, а под unattended-upgrades выполнялся только вывод списка.

Следствие для сервера 1С: ночное обновление `libssl3` или `libc6` может перезапустить PostgreSQL, сервер 1С и Apache без участия администратора. Нужно исключить их из автоперезапуска.

Настройка — не в основном файле `/etc/needrestart/needrestart.conf`, а в отдельном файле в `/etc/needrestart/conf.d/` **[офиц.]**:

```perl
# /etc/needrestart/conf.d/50-1c-postgres.conf
# 0 = не перезапускать автоматически (служба останется в списке «требуют перезапуска»)
$nrconf{override_rc}{qr(^postgrespro-.*\.service$)} = 0;
$nrconf{override_rc}{qr(^postgresql.*\.service$)} = 0;
$nrconf{override_rc}{qr(^srv1cv8.*\.service$)} = 0;
$nrconf{override_rc}{qr(^ras.*\.service$)} = 0;
$nrconf{override_rc}{qr(^apache2\.service$)} = 0;

# Альтернатива: вообще ничего не перезапускать, только показывать список
# $nrconf{restart} = 'l';      # 'l' — список, 'i' — спрашивать, 'a' — автоматически
```

Почему именно такая форма записи **[код: исходники needrestart — `ex/needrestart.conf` и скрипт `needrestart`]**:

- Штатный список задан в `/etc/needrestart/needrestart.conf` присваиванием целого хеша `$nrconf{override_rc} = { qr(^dbus) => 0, … };`, а файлы `/etc/needrestart/conf.d/*.conf` (расширение `.conf` обязательно, порядок — по имени) исполняются **после** него, в конце того же файла. Поэтому пример из документации Ubuntu — `$nrconf{override_rc} = { qr(^моя-служба\.service$) => 0, };` — будучи помещён в `conf.d`, **заменит весь штатный список** (dbus, сеть, getty, `systemd-logind` и т. д. снова начнут перезапускаться). Запись `$nrconf{override_rc}{qr(...)} = 0;` добавляет элемент в существующий хеш и штатный список не затирает — это обычный Perl, специальной документации на неё нет. (Структура файла проверена по upstream; в пакете Ubuntu убедиться, что блок чтения `conf.d` стоит в конце `needrestart.conf`: `tail -n 12 /etc/needrestart/needrestart.conf`.)
- Ключ — регулярное выражение, сопоставляется с именем юнита (`postgrespro-1c-18.service`, `postgresql@18-main.service`, `srv1cv8-8.3.27.1688@default.service`); значение `0` — не перезапускать автоматически, `1` — перезапускать. Ключи перебираются в отсортированном порядке, срабатывает первый совпавший.
- Ошибка синтаксиса в файле из `conf.d` роняет needrestart целиком («Error parsing …») — после правки обязательно выполнить `sudo needrestart -r l -v` и убедиться, что он отработал, а нужные службы показаны как отложенные, а не перезапущены.
- Имена юнитов сервера 1С зависят от версии и способа установки — уточнить: `systemctl list-units 'srv1cv8*' 'ras*'` (с 8.3.21 — шаблон `srv1cv8-<версия>@.service`, экземпляр обычно `@default`, и `ras-<версия>.service`; при обновлении платформы имя юнита меняется, но шаблоны `^srv1cv8` и `^ras` продолжают подходить).

В штатном списке исключений уже есть dbus, дисплейные менеджеры, getty, сеть (`network`, `NetworkManager`, `openvpn`, …), `systemd-logind`, docker/libvirt/lxc, `user@…`, `cron-*` и юниты `apt-daily*`/`unattended-upgrades`; PostgreSQL, Apache и сервера 1С там нет. ⚠ состав списка проверен по исходникам needrestart (ветка master), а не по файлу из пакета Ubuntu — на своей системе смотреть `grep -n 'qr(' /etc/needrestart/needrestart.conf`.

```bash
sudo needrestart            # проверить сейчас (режим из конфигурации)
sudo needrestart -r l       # только показать, что требует перезапуска
sudo needrestart -k         # только ядро: загружено ли самое новое установленное
sudo needrestart -b         # машинно-читаемый вывод (для мониторинга)
sudo NEEDRESTART_MODE=l apt upgrade          # на один запуск: только список
sudo NEEDRESTART_SUSPEND=1 apt upgrade       # на один запуск: не вызывать needrestart
```

После обновления библиотек вручную, в окно: остановить сервер 1С → перезапустить PostgreSQL → запустить сервер 1С (или перезагрузить ВМ целиком, если обновлялось ядро/glibc).

### 8.4. Перезагрузка после обновления ядра

Пакеты, требующие перезагрузки (ядро, glibc, systemd, микрокод), создают файл-флаг:

```bash
[ -f /var/run/reboot-required ] && { cat /var/run/reboot-required; cat /var/run/reboot-required.pkgs; }
uname -r                                         # работающее ядро
dpkg -l 'linux-image-*' | grep '^ii'             # установленные ядра
sudo needrestart -k
```

- `/var/run` — ссылка на `/run`; флаг исчезает после перезагрузки. При входе по SSH о нём сообщает MOTD: `*** System restart required ***`.
- Новое ядро начинает работать только после перезагрузки; до неё исправления безопасности ядра не действуют (исключение — Livepatch, раздел 9.5).
- Порядок для сервера 1С: предупредить пользователей → остановить сервер 1С (`systemctl stop 'srv1cv8*'`) → убедиться, что PostgreSQL завершил работу штатно (или просто `sudo reboot` — systemd остановит службы по порядку) → после загрузки проверить `systemctl --failed`, службы СУБД и 1С.
- Автоматическая перезагрузка (`Unattended-Upgrade::Automatic-Reboot "true"` + `Automatic-Reboot-Time "02:00"`) допустима только если ночью нет регламентных заданий 1С и резервного копирования.

### 8.5. Phased updates — поэтапная раскатка

Обновления из `-updates` Ubuntu раздаёт не всем сразу, а растущей доле машин (apt реализует это с 21.04; действует и на серверах). Обновления безопасности не фазируются.

- Симптом: `apt upgrade` пишет `The following packages have been kept back` (в новых версиях — «deferred due to phasing»), хотя hold нет. Это нормально: пакет придёт позже.
- Проверка: `apt policy <пакет>` — у кандидата пометка вида `(phased 20%)`.
- Доля определяется на клиенте из `/etc/machine-id`, имени и версии пакета. Чтобы группа серверов (например, тест и продуктив) получала обновления одинаково, задать общий идентификатор `APT::Machine-ID "<UUID>";`.
- Отключить фазирование (получать всё сразу — на свой риск) или наоборот никогда не брать незавершённые фазы:

```
// /etc/apt/apt.conf.d/99-phased-updates
APT::Get::Always-Include-Phased-Updates "true";
// либо: APT::Get::Never-Include-Phased-Updates "true";
```

- Ставить «задержанный» пакет явной командой `apt install` документация не советует: если задержка вызвана не фазированием, apt может предложить удаление других пакетов.

### 8.6. Сводный порядок ручного обновления сервера 1С + PostgreSQL

Сводка **[практика]** из приёмов, описанных выше (hold — 7.2, needrestart — 8.3, перезагрузка — 8.4, сохранение пакетов для отката — 12.2):

```bash
# 0. Заранее, вне окна: что придёт и не затронет ли это СУБД/библиотеки
sudo apt update
apt list --upgradable
apt-get -s upgrade | grep -E '^(Inst|Remv)' | grep -i -E 'postgres|libpq|libc6|libicu|libssl|linux-image|apache2'
apt-mark showhold                                   # пакеты СУБД должны быть в списке

# 1. В окно: резервные копии баз, затем снимок ВМ при остановленных сервере 1С и СУБД
# 2. Остановить сервер 1С и обновить ОС; СУБД на hold не изменится
sudo systemctl stop 'srv1cv8*'
sudo NEEDRESTART_MODE=l apt upgrade                 # needrestart только перечислит службы, ничего не перезапуская

# 3. (Отдельным шагом и не каждый раз) плановое обновление СУБД — раздел 7.2:
#    сначала сохранить текущие .deb (12.2), сверить новую версию со списком поддерживаемых СУБД 1С

# 4. Перезапуск в правильном порядке либо перезагрузка, если обновлялись ядро/glibc
[ -f /var/run/reboot-required ] && cat /var/run/reboot-required.pkgs
sudo systemctl restart postgrespro-1c-18            # или postgresql@18-main для сборки 1С
sudo systemctl start 'srv1cv8*'                     # если юнит не поднялся по шаблону — указать полное имя
# либо: sudo reboot

# 5. Проверки
systemctl --failed
sudo needrestart -r l
apt-mark showhold
dpkg -l | grep -E 'postgres|libpq5'                 # версии СУБД на месте (…noble / …1C)
```

Замечание к шагу 4: `systemctl start 'srv1cv8*'` с шаблоном действует только на юниты, уже загруженные в память systemd; после остановки надёжнее полное имя (`systemctl list-unit-files 'srv1cv8*'`, затем `sudo systemctl start srv1cv8-<версия>@default`).

## 9. Обновление релиза, ядра HWE, Ubuntu Pro, Livepatch

### 9.1. do-release-upgrade

Правила **[офиц.]**:

- Переход возможен только на следующий релиз: LTS → следующий LTS (22.04 → 24.04 → 26.04), перепрыгнуть нельзя. С 22.04 на 26.04 — только через 24.04.
- LTS → LTS предлагается только после первого точечного релиза нового LTS. Фактически для 26.04: 26.04.1 вышел в конце августа 2026 г., а путь 24.04 → 26.04.1 Canonical открыла 29.09.2026 (задержка из-за регрессий в rust-coreutils).
- Сторонние репозитории и PPA на время обновления **отключаются**.
- Система считается обновлённой только после перезагрузки.

Настройка — `/etc/update-manager/release-upgrades`: `Prompt=lts` (предлагать только LTS; значение по умолчанию на LTS-сервере), `Prompt=normal` (любой следующий релиз), `Prompt=never` (не предлагать). На сервере 1С разумно поставить `never`, чтобы никто не запустил обновление по подсказке в MOTD.

Опции `do-release-upgrade`:

| Опция | Смысл |
|---|---|
| `-c`, `--check-dist-upgrade-only` | только проверить, есть ли новый релиз (код возврата) |
| `-d`, `--devel-release` | обновиться до разрабатываемого релиза; также форсирует LTS→LTS до открытия пути — не для продуктива |
| `-p`, `--proposed` | взять обновлятор из `-proposed` |
| `-f FRONTEND`, `--frontend=` | интерфейс, например `DistUpgradeViewNonInteractive` |
| `--allow-third-party` | не отключать сторонние репозитории |
| `-q`, `--quiet`; `-e VAR=VAL,…` | тихий режим; переменные окружения на время обновления |

Порядок работы:

```bash
# 0. Снимок ВМ (выключенной) + резервные копии баз 1С (dt и/или pg_dump) — обязательно
# 1. Привести текущий релиз в актуальное состояние
sudo apt update
sudo apt dist-upgrade -o APT::Get::Always-Include-Phased-Updates=true
[ -f /run/reboot-required ] && sudo reboot
# 2. Проверки
df -h / /boot /var                 # нужно несколько ГБ свободного места
apt-mark showhold                  # hold-ы мешают обновлению — осознанно снять
apt list '?obsolete'               # пакеты не из репозиториев
ls /etc/apt/sources.list.d/        # какие сторонние репозитории будут отключены
do-release-upgrade -c
# 3. Запуск — в tmux/screen или с консоли гипервизора, не в «голой» SSH-сессии
sudo do-release-upgrade
# 4. После перезагрузки
lsb_release -a; uname -r; systemctl --failed
ls /etc/apt/sources.list.d/        # включить обратно сторонние репозитории с новым кодовым именем
sudo apt update && sudo apt full-upgrade && sudo apt autoremove --purge
```

При запуске по SSH обновлятор предупреждает об этом и предлагает поднять запасной sshd на порту 1022 — чтобы было куда подключиться, если основной sshd во время обновления перестанет отвечать; порт нужно самому открыть в брандмауэре (`sudo ufw allow 1022/tcp`), автоматически это не делается. ⚠ не подтверждено по первоисточнику в этой проверке: в актуальных man do-release-upgrade(8) и документации Ubuntu Server порт не упоминается, исходный код ubuntu-release-upgrader (`DistUpgradeController.py`) открыть не удалось — сведения по многолетней практике; надёжнее запускать обновление в `tmux`/`screen` или с консоли гипервизора (Hyper-V/VMware), где SSH не нужен вовсе. Журналы обновления — `/var/log/dist-upgrade/` (`main.log`, `apt.log`, `term.log`). Отключённые источники: в deb822 — `Enabled: no`, в `*.list` — закомментированные строки с пометкой «disabled on upgrade».

### 9.2. Риски обновления релиза для сервера 1С + PostgreSQL

| Риск | Что происходит | Что делать |
|---|---|---|
| Платформа 1С не поддерживает новый релиз | на 10.10.2026 в списке ОС сервера 1С (v8.1c.ru) — Ubuntu 20.04 / 22.04 / 24.04; 26.04 нет | не обновлять продуктив до появления релиза в списке и проверки на стенде |
| Пакеты СУБД собраны под старый релиз | `postgrespro-1c-18-server 18.4-1.noble` требует `libicu74`, `libxml2`; в resolute — `libicu78`, `libxml2-16`. Сторонний репозиторий отключён, пакет остаётся от старого релиза; после удаления «устаревших» библиотек сервер не стартует (`error while loading shared libraries: libicui18n.so.74…`) | до перезагрузки/первого запуска переключить репозиторий на новое кодовое имя и обновить пакеты СУБД до сборки для нового релиза (`18.4-1.resolute`); не соглашаться на «Remove obsolete packages?», не посмотрев список |
| Смена glibc → смена порядка сортировки | 22.04: glibc 2.35 → 24.04: 2.39 → 26.04: 2.43. PostgreSQL хранит отсортированные строки в B-tree-индексах; при изменении правил сортировки в локали индексы по `text`/`varchar`/`char` становятся некорректными: неверные результаты, «пропавшие» строки, дубли в уникальных индексах. `pg_upgrade` от этого не спасает | после обновления: `REINDEX` всех баз (или как минимум индексов по строковым полям), затем `ALTER DATABASE … REFRESH COLLATION VERSION`; надёжнее — перенос через `pg_dump`/`pg_restore` или выгрузку 1С (dt) на новый сервер |
| Смена версии ICU | 70 → 74 → 78; если база использует провайдер сортировки ICU, версии правил тоже меняются | то же: REINDEX + REFRESH COLLATION VERSION |
| Смена мажорной версии PostgreSQL в архиве Ubuntu | 14 → 16 → 18 (касается только системного `postgresql`; кластеры сами не мигрируют) | для 1С системный PostgreSQL не используется; иначе — `pg_upgradecluster`/`pg_upgrade` |
| Пропавшие/переименованные библиотеки | в 24.04 — переход на 64-битное time_t: `libssl3` → `libssl3t64`, `libreadline8` → `libreadline8t64` и т. п.; в 26.04 — `libxml2` → `libxml2-16`. Платформа 1С, поставленная через `.run`, в зависимостях apt не участвует — её библиотеки могут быть удалены или заменены несовместимыми | после обновления переустановить платформу 1С той версии, которая поддерживает новый релиз; проверить вывод `ldd /opt/1cv8/x86_64/<версия>/ragent` — в нём не должно быть строк `not found` |
| Изменения базовой системы 26.04 | `sudo` → sudo-rs, coreutils → rust-coreutils (uutils; `cp`, `mv`, `rm` пока GNU), cgroup v1 удалён, systemd 259, chrony вместо systemd-timesyncd (новые установки), Dracut вместо initramfs-tools, OpenSSH 10.2 без DSA, Python 3.14, apt-key удалён | проверить свои скрипты резервного копирования и обслуживания на стенде |
| Конфиги | вопросы о замене изменённых конфигов (sshd, apache2, sysctl) | по умолчанию оставлять свои (`N`), затем сравнить с `*.dpkg-dist` |

Диагностика сортировки в PostgreSQL после любого обновления glibc/ICU:

```sql
-- провайдер и версия правил сортировки баз (PostgreSQL 15+)
SELECT datname, datlocprovider, datcollate, datcollversion,
       pg_database_collation_actual_version(oid) AS actual_version
FROM pg_database;
-- при расхождении в журнале СУБД будет:
-- WARNING:  database "…" has a collation version mismatch
REINDEX DATABASE имя_базы;                      -- выполняется, будучи подключённым к этой базе
ALTER DATABASE имя_базы REFRESH COLLATION VERSION;
```

Быстрая проверка, изменилась ли сортировка libc между двумя системами (из wiki PostgreSQL): выполнить на обеих `( echo "1-1"; echo "11" ) | LC_COLLATE=en_US.UTF-8 sort` и сравнить вывод (совпадение не гарантирует отсутствия других отличий). Локали `C`/`POSIX` изменению не подвержены.

**Рекомендация [офиц. Canonical для систем со сторонними репозиториями + практика 1С]:** не обновлять релиз «на месте», а развернуть новую ВМ с нужным релизом, поставить поддерживаемые сборки СУБД и платформы, перенести базы логическим способом (выгрузка/загрузка dt, `pg_dump`/`pg_restore`), переключить клиентов. Старая ВМ остаётся готовым откатом.

### 9.3. Ядра GA и HWE

| Релиз | Ядро GA | Ядра HWE |
|---|---|---|
| 22.04 | 5.15 | до 6.8 (22.04.5) |
| 24.04 | 6.8 | 6.17 (24.04.4, поддержка до июля 2026), 7.0 (24.04.5, с июля 2026) |
| 26.04 | 7.0 | появятся с 26.04.2 |

- GA (General Availability) — ядро релиза, поддерживается весь срок LTS. HWE (Hardware Enablement) — более новые ядра из следующих релизов; каждые полгода мажорная версия меняется (кроме последнего в ряду).
- **Серверные установки по умолчанию остаются на GA** [офиц.]; настольные — на HWE. Для ВМ с 1С и PostgreSQL GA-ядра достаточно: стабильность важнее поддержки нового железа.
- Перейти на HWE: `sudo apt install --install-recommends linux-generic-hwe-24.04` (и перезагрузка). Проверить статус: `hwe-support-status --verbose`.

```bash
uname -r
dpkg -l 'linux-image-*' 'linux-generic*' 'linux-virtual*' | grep '^ii'
apt policy linux-generic linux-generic-hwe-24.04
```

Старые ядра убирает `apt autoremove --purge` (и `apt full-upgrade` с apt 2.1.16); apt всегда оставляет работающее и последние установленные ядра (параметр `APT::NeverAutoRemove::KernelCount`, по умолчанию 2).

### 9.4. Ubuntu Pro и ESM

- Ubuntu Pro — подписка Canonical: 10 лет обновлений безопасности (5 стандартных + 5 ESM) для `main` (**esm-infra**) и `universe` (**esm-apps**), Livepatch, FIPS/CIS, Landscape. С дополнением Legacy — до 15 лет. **Бесплатно для личного использования до 5 машин.**
- Клиент `pro` (пакет `ubuntu-pro-client`, раньше `ubuntu-advantage-tools`) предустановлен.

```bash
pro status                         # подключена ли машина и какие сервисы включены
sudo pro attach                    # интерактивно: выдаст ссылку и код для привязки к учётной записи
sudo pro attach <ТОКЕН>            # по токену из https://ubuntu.com/pro/dashboard
sudo pro attach --no-auto-enable <ТОКЕН>   # привязать, ничего не включая
sudo pro enable esm-infra
sudo pro enable esm-apps
sudo pro disable livepatch
pro security-status                # сколько пакетов получают обновления и из каких источников
sudo pro detach
sudo pro config set apt_news=false # убрать «новости» Pro из вывода apt
```

- После `pro attach` по умолчанию включаются `esm-apps`, `esm-infra` и `livepatch`. Появляются источники `esm.ubuntu.com` (файлы `ubuntu-esm-*.sources` в `sources.list.d`), а unattended-upgrades начинает ставить и ESM-обновления (их origin уже есть в `Allowed-Origins`).
- Строки в выводе apt вида «Get more security updates through Ubuntu Pro with 'esm-apps' enabled» — информационные, не ошибка.
- Когда это нужно серверу 1С: если остаётесь на LTS после окончания стандартной поддержки (22.04 — после весны 2027) или если критичны исправления для пакетов из `universe`.

### 9.5. Livepatch

Livepatch накладывает исправления критичных и важных уязвимостей ядра **без перезагрузки** (между окнами обслуживания). Требует Ubuntu Pro; клиент — snap `canonical-livepatch` (значит, нужен snapd).

```bash
sudo pro enable livepatch
canonical-livepatch status --verbose
sudo pro disable livepatch
```

Ограничения: закрывает только часть исправлений безопасности ядра, не обновляет само ядро и не отменяет плановые перезагрузки; работает на LTS-ядрах (GA и поддерживаемых HWE). Для ВМ с 1С, которую можно перезагрузить ночью, Livepatch — удобство, а не необходимость.

## 10. snap

snap — отдельная от apt система пакетов (демон `snapd`): приложение со всеми зависимостями в сжатом образе, смонтированном в `/snap/<имя>/<ревизия>`; данные — в `/var/snap/<имя>`; по умолчанию изоляция (confinement) и **автообновление 4 раза в сутки**.

| Команда | Что делает |
|---|---|
| `snap list` (`--all` — включая старые ревизии) | установленные snap-пакеты |
| `snap find СЛОВО` / `snap info ИМЯ` | поиск / сведения, каналы, версии |
| `sudo snap install ИМЯ` | установить; `--classic` — без изоляции (если пакет этого требует), `--channel=…`, `--revision=N` |
| `sudo snap refresh [ИМЯ]` | обновить сейчас (всё или один пакет) |
| `snap refresh --list` | что обновится при следующем refresh |
| `snap refresh --time` | расписание автообновления: last / next / hold |
| `sudo snap refresh --hold[=СРОК] [ИМЯ…]` | отложить автообновление; без срока — навсегда (`forever`) |
| `sudo snap refresh --unhold [ИМЯ…]` | снять откладывание |
| `sudo snap revert ИМЯ` | вернуться к предыдущей ревизии |
| `sudo snap remove ИМЯ` | удалить (делается снимок данных); `--purge` — без снимка |
| `snap services`, `sudo snap logs ИМЯ`, `sudo snap restart ИМЯ` | службы snap-пакета |
| `snap changes`, `snap tasks N` | журнал операций snapd |
| `sudo snap set system КЛЮЧ=ЗНАЧЕНИЕ`, `snap get system КЛЮЧ` | системные настройки snapd |

Управление автообновлением:

```bash
snap refresh --time
sudo snap refresh --hold                 # заморозить автообновление ВСЕХ snap бессрочно (snapd ≥ 2.58)
sudo snap refresh --hold=72h             # на 72 часа
sudo snap refresh --hold=forever lxd     # один пакет — бессрочно
sudo snap refresh --unhold
sudo snap set system refresh.timer=sun,02:00-04:00   # окно автообновления: воскресенье, 02–04
sudo snap set system refresh.retain=2                # сколько ревизий хранить (место на диске)
```

Нюанс из man snap: `--hold` без имён пакетов блокирует только **авто**обновления (ручной `snap refresh` работает); `--hold` с именами блокирует для этих пакетов и общий `snap refresh` (но не `snap refresh ИМЯ`).

Когда snap **не** использовать на сервере **[практика]**:

- PostgreSQL, сервер 1С, Apache для веб-публикации 1С — только deb-пакеты/официальные установщики. 1С и Postgres Professional snap-пакеты не выпускают; автообновление snap перезапускает службы в произвольное время; изоляция мешает доступу к файлам и сокетам вне `/var/snap`.
- Всё, что должно обновляться строго в окно обслуживания, — либо не snap, либо с `--hold`.
- Допустимо: вспомогательные инструменты (`canonical-livepatch`, `lxd`), где автообновление не вредит.

Если snap не нужен совсем (и не используется Livepatch):

```bash
snap list                                   # убедиться, что нет нужных пакетов
sudo snap remove --purge <каждый пакет>     # сначала приложения, затем core*, snapd
sudo apt purge snapd
```

Чтобы snapd не вернулся как зависимость другого пакета — запрещающее закрепление **[практика]**, файл `/etc/apt/preferences.d/no-snapd.pref`:

```
Package: snapd
Pin: release a=*
Pin-Priority: -10
```

## 11. Блокировки, прокси, офлайн-установка, очистка места

### 11.1. Блокировки apt/dpkg

| Lock-файл | Кто берёт |
|---|---|
| `/var/lib/dpkg/lock-frontend` | любой фронтенд (apt, apt-get, unattended-upgrade) на всё время транзакции |
| `/var/lib/dpkg/lock` | сам dpkg во время работы с базой |
| `/var/lib/apt/lists/lock` | `apt update` |
| `/var/cache/apt/archives/lock` | загрузка пакетов |

Типичные сообщения: `E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 1234 (unattended-upgr)`; `Waiting for cache lock: Could not get lock …` (apt ждёт сам).

Чаще всего блокировку держат автоматические задания (`apt-daily.service`, `apt-daily-upgrade.service`, особенно сразу после включения ВМ — `Persistent=true`), второй сеанс администратора или `packagekitd`.

```bash
# Кто держит
ps -eo pid,etime,cmd | grep -E '[a]pt|[d]pkg|[u]nattended'
sudo lsof /var/lib/dpkg/lock-frontend
systemctl status apt-daily.service apt-daily-upgrade.service unattended-upgrades.service

# Правильно подождать (секунды; -1 — ждать бесконечно)
sudo apt-get -o DPkg::Lock::Timeout=300 install -y <пакет>

# В скриптах первичной настройки ВМ: дождаться завершения автозаданий
sudo systemd-run --property="After=apt-daily.service apt-daily-upgrade.service" --wait /bin/true
cloud-init status --wait        # если ВМ развёрнута из cloud-образа
```

Правила:

- Команда `apt` ждёт блокировку dpkg сама **[офиц., NEWS apt 1.9.11]**: если запущена в терминале — бессрочно (сообщение «Waiting for cache lock…», прервать — Ctrl+C), если без терминала (скрипт, cron, конвейер) — 120 секунд. `apt-get` по умолчанию не ждёт — нужен `DPkg::Lock::Timeout` (секунды; `-1` — бесконечно). Постоянно: `echo 'DPkg::Lock::Timeout "300";' | sudo tee /etc/apt/apt.conf.d/80-lock-timeout`. В man apt.conf(5) параметр не описан (проверено для apt 3.2.0), но работает во всех актуальных LTS (apt ≥ 1.9.11).
- Таймаут относится к блокировке dpkg; для `/var/lib/apt/lists/lock` (`apt update`) ожидание не реализовано (Debian bug #1069167) — в скриптах делать повтор.
- **Не удалять lock-файлы и не убивать dpkg**, пока процесс жив: получится полуустановленная система. Удалять файл блокировки допустимо, только если процесса-владельца точно нет (после сбоя питания), и сразу затем: `sudo dpkg --configure -a && sudo apt -f install`.
- Перед разбирательством проверить место: `df -h /var /boot` — переполненный раздел часто оставляет dpkg в прерванном состоянии.

### 11.2. Прокси для apt

`sudo` по умолчанию не передаёт переменные `http_proxy`/`https_proxy`, поэтому прокси для apt задают в конфигурации:

```
// /etc/apt/apt.conf.d/95proxy
Acquire::http::Proxy  "http://proxy.example.local:3128/";
Acquire::https::Proxy "http://proxy.example.local:3128/";
// для отдельных хостов — напрямую, без прокси
Acquire::http::Proxy::repo.local "DIRECT";
```

- Поддерживаемые схемы прокси: `http`, `https`, `socks5h`. Специальное значение `DIRECT` — без прокси. Переменные окружения `http_proxy` и `no_proxy` тоже учитываются, если дошли до процесса apt.
- Логин и пароль прокси/репозитория не писать в URL, а хранить в `/etc/apt/auth.conf.d/*.conf` (формат `machine <хост> login <имя> password <пароль>`, права 0600).
- Разово: `sudo apt -o Acquire::http::Proxy="http://proxy:3128/" update`.
- Смежные параметры: `Acquire::ForceIPv4 "true";` (если IPv6 не работает), `Acquire::Retries "3";`, `Acquire::http::Timeout "30";`, `Acquire::http::Dl-Limit "500";` (КиБ/с), `Acquire::http::No-Cache "true";` (при «Hash Sum mismatch» через кеширующий прокси).
- Кеширующий прокси пакетов для нескольких серверов — `apt-cacher-ng` (слушает порт 3142): на клиентах `Acquire::http::Proxy "http://cache-host:3142";`.

### 11.3. Офлайн-установка

Сами дистрибутивы 1С (`setup-full-….run`) и «PostgreSQL с патчем от 1С» переносятся файлами; из сети нужны только их зависимости из архива Ubuntu. Машина-донор должна быть **того же релиза и архитектуры**, что и изолированный сервер.

**Способ 1. Скачать пакет со всеми зависимостями (самодостаточный набор):**

```bash
mkdir ~/debs && cd ~/debs
apt-get download $(apt-cache depends --recurse --no-recommends --no-suggests \
    --no-conflicts --no-breaks --no-replaces --no-enhances unixodbc libgsf-1-114 \
    | grep '^\w' | sort -u)
# перенести каталог на сервер, там:
sudo apt install ./*.deb          # или: sudo dpkg -i *.deb
```

(виртуальные пакеты в списке дадут ошибку «Can't select candidate version» — убрать их из списка; набор получается с запасом, зато не зависит от состояния донора).

Особый случай — шрифты `ttf-mscorefonts-installer`: сам пакет шрифтов не содержит, а скачивает их при установке с SourceForge, поэтому на изолированном сервере перенос одного `.deb` не помогает. ⚠ не подтверждено в этой проверке (по памяти рецензента): пакет умеет брать заранее скачанные файлы шрифтов из локального каталога — вопрос debconf `msttcorefonts/dldir`; проверить `sudo debconf-show ttf-mscorefonts-installer` и `sudo dpkg-reconfigure ttf-mscorefonts-installer`. Программа установки платформы 1С тоже пытается поставить эти шрифты сама (сначала из репозитория ОС, затем с зеркал SourceForge) **[офиц.]** — без доступа в интернет шаг не выполнится, шрифты нужно подготовить заранее.

**Способ 2. Скачать только недостающее — донор с таким же набором пакетов (клон ВМ):**

```bash
mkdir -p /tmp/debs/partial
sudo apt-get install --download-only -o Dir::Cache::archives=/tmp/debs <пакеты>
```

**Способ 3. Получить список URL и скачать на любой машине (хоть на Windows):**

```bash
apt-get install --print-uris -y <пакеты> | grep -oE "https?://[^']+\.deb" > urls.txt
```

**Способ 4. apt-offline** (universe: noble 1.8.5, resolute 1.8.6) — «подпись» запроса на изолированной машине, загрузка на подключённой:

```bash
# на изолированном сервере
sudo apt-offline set /tmp/req.sig --update --install-packages unixodbc libgsf-1-114
# на машине с интернетом
apt-offline get req.sig --bundle bundle.zip
# снова на сервере
sudo apt-offline install bundle.zip
sudo apt install unixodbc libgsf-1-114
```

**Способ 5. Локальный репозиторий** — когда пакетов много или серверов несколько:

```bash
sudo apt install dpkg-dev                       # даёт dpkg-scanpackages
sudo mkdir -p /srv/localrepo && sudo cp ~/debs/*.deb /srv/localrepo/
cd /srv/localrepo
sudo sh -c 'dpkg-scanpackages --multiversion . /dev/null > Packages && gzip -9kf Packages'

sudo tee /etc/apt/sources.list.d/localrepo.sources >/dev/null <<'EOF'
Types: deb
URIs: file:/srv/localrepo
Suites: ./
Trusted: yes
EOF
sudo apt update && apt policy | grep -A1 localrepo
```

- Это «плоский» репозиторий: `Suites` оканчивается на `/`, поле `Components` отсутствует. `Trusted: yes` отключает проверку подписи — допустимо только для своего локального каталога. Однострочный эквивалент: `deb [trusted=yes] file:/srv/localrepo ./`.
- После добавления пакетов — пересоздать `Packages` и выполнить `apt update`.
- Для «настоящих» подписанных репозиториев и зеркал: `reprepro`, `aptly` (свои репозитории), `apt-mirror`/`debmirror` (полное зеркало), `apt-cacher-ng` (кеш).

### 11.4. Очистка места

```bash
df -h / /var /boot
sudo du -xsh /var/cache/apt/archives /var/lib/apt/lists /var/log /var/lib/snapd 2>/dev/null

sudo apt clean                      # весь кеш .deb
sudo apt autoclean                  # только устаревшие .deb
sudo apt autoremove --purge         # ненужные зависимости и старые ядра
dpkg -l | awk '/^rc/ {print $2}' | xargs -r sudo dpkg -P     # остатки конфигов удалённых пакетов
sudo journalctl --vacuum-size=200M  # журнал systemd

# Ядра: что установлено и какое работает
dpkg -l 'linux-image-*' 'linux-modules-*' 'linux-headers-*' | grep '^ii'
uname -r
sudo apt purge linux-image-6.8.0-31-generic linux-modules-6.8.0-31-generic   # вручную — только НЕ работающее ядро

# Старые ревизии snap
snap list --all | awk '/disabled/ {print $1, $3}' | while read n r; do sudo snap remove "$n" --revision="$r"; done
```

- Переполненный `/boot` — классическая причина сбоя обновления ядра (`No space left on device` при генерации initrd). Лечение: `sudo apt autoremove --purge`; если apt уже сломан — вручную удалить самое старое неработающее ядро через `dpkg -P`, затем `sudo apt -f install`.
- Перед `autoremove` читать список: если платформа 1С поставлена через `.run`, её библиотеки могут попасть в «больше не нужные» (раздел 7.1) — сначала `apt-mark manual`.
- Кеш `.deb` бывает полезен для отката (раздел 12.3): перед обновлением СУБД не делать `apt clean`, а после успешной проверки — можно.

## 12. Журналы и откат пакета

### 12.1. Журналы

| Файл | Что в нём |
|---|---|
| `/var/log/apt/history.log` | транзакции apt: `Start-Date`, `Commandline` (точная команда), `Requested-By` (кто через sudo), списки `Install:` / `Upgrade:` (старая → новая версия) / `Remove:` / `Purge:`, `End-Date` |
| `/var/log/apt/term.log` | полный вывод dpkg и скриптов пакетов в этих транзакциях — искать здесь текст ошибок postinst |
| `/var/log/dpkg.log` | каждое действие dpkg с отметкой времени: `install`, `upgrade <пакет> <старая> <новая>`, `remove`, `purge`, `status …`, `configure` — включая то, что ставилось мимо apt (`dpkg -i`) |
| `/var/log/unattended-upgrades/` | решения и вывод автообновлений |
| `/var/log/dist-upgrade/` | журналы `do-release-upgrade` |
| `/var/log/alternatives.log` | изменения update-alternatives |

Старые журналы ротируются: `history.log.1.gz`, `dpkg.log.1`, `dpkg.log.2.gz` … — искать через `zgrep`/`zcat -f`.

```bash
# Что и когда обновлялось в последних транзакциях
grep -E '^(Start-Date|Commandline|Requested-By|Upgrade|Install|Remove)' /var/log/apt/history.log | tail -40

# Все обновления PostgreSQL за всю историю журналов
zgrep -h -E ' (install|upgrade|remove) .*postgres' /var/log/dpkg.log* | sort

# Что произошло в конкретный день
zgrep -h '^2026-10-0[5-9] ' /var/log/dpkg.log* | grep -E ' (install|upgrade|remove|purge) '

# Какой версии был пакет до последнего обновления
zgrep -h ' upgrade postgrespro-1c-18-server' /var/log/dpkg.log* | tail -1

# Что делало автообновление
zcat -f /var/log/apt/history.log* | grep -A6 'unattended-upgrade'
```

В Ubuntu 26.04 (apt 3.2.0) тот же журнал доступен командами **[офиц.: release notes 26.04; changelog apt — 3.1.6 «History Command and Parsing», 3.1.7 «Add history undo, redo, and rollback features»]**. В 22.04/24.04 этих команд нет; в man apt(8) версии 3.2.0 они не описаны, поэтому точный синтаксис аргументов сверять по выводу самой команды на своей системе:

```bash
apt history-list                 # транзакции с номерами (ID)
apt history-info 42              # какие пакеты и версии затронула транзакция 42
sudo apt history-undo 42         # отменить транзакцию: поставить удалённое, удалить установленное, вернуть версии
sudo apt history-redo 42         # повторить отменённую
sudo apt history-rollback 40     # откатить все транзакции после 40-й
```

Это откат только на уровне пакетов: конфигурационные файлы и данные не возвращаются, а старые версии должны быть доступны apt (кеш или репозиторий). ⚠ не подтверждено: комментарии к действиям каждой команды в блоке выше — по описанию в release notes («listing, inspecting, undoing, redoing, and rolling back changes»), на стенде не проверялись; для СУБД откат через `history-undo` не использовать без снимка ВМ — у Postgres Pro 1С предыдущей версии в основном репозитории уже нет.

### 12.2. Где взять предыдущую версию

| Источник пакета | Где лежат старые версии |
|---|---|
| Архив Ubuntu | в индексах — только версия релиза и последняя из `-updates`/`-security`. Старые: **snapshot.ubuntu.com** (состояние архива на любой момент с 01.03.2023) или страница пакета на Launchpad (`https://launchpad.net/ubuntu/+source/<пакет>`) — скачать `.deb` вручную |
| PGDG | `apt-archive.postgresql.org`, выпуск `<codename>-pgdg-archive` |
| Postgres Pro 1С | `https://repo.postgrespro.ru/1c/archive/1c-<версия>/ubuntu` (например, `1c-18.3`, `1c-17.9`); в каждом каталоге — только те релизы Ubuntu, под которые версия собиралась (в `1c-17.9`: focal, jammy, noble, oracular, questing) |
| «PostgreSQL с патчем от 1С», платформа 1С | releases.1c.ru — хранить скачанные дистрибутивы у себя |
| Любой | `/var/cache/apt/archives/*.deb`, если кеш не чистился и пакет ставился через `apt-get` (или включено сохранение, см. ниже) |

Сохранять скачанные `.deb` после установки командой `apt` **[офиц., NEWS apt 1.2~exp1 — там же дан именно этот пример файла]** (проверка: `apt-config dump | grep -i Keep-Downloaded`):

```
// /etc/apt/apt.conf.d/01keep-debs
Binary::apt::APT::Keep-Downloaded-Packages "true";
```

Надёжнее перед обновлением СУБД явно сохранить текущие пакеты:

```bash
mkdir -p ~/rollback/pg-$(date +%F) && cd ~/rollback/pg-$(date +%F)
apt-get download $(dpkg-query -W -f='${binary:Package}=${Version}\n' 'postgrespro-1c-18*')
```

(сработает, пока текущая версия ещё есть в индексе, то есть **до** `apt update`, который увидит новую версию, — либо из архивного репозитория).

### 12.3. Откат на предыдущую версию

```bash
# 1. Узнать, с какой версии обновились
zgrep -h ' upgrade postgrespro-1c-18' /var/log/dpkg.log* | tail

# 2. Посмотреть, какие версии доступны apt
apt policy postgrespro-1c-18-server
apt list -a postgrespro-1c-18-server
apt-cache madison postgrespro-1c-18-server

# 3а. Версия есть в репозитории — понизить ВСЕ пакеты одной сборки разом
V=18.3-1.noble
sudo apt install $(dpkg-query -W -f='${binary:Package}\n' 'postgrespro-1c-18*' | sed "s/\$/=$V/")
#    (в скриптах с -y добавить --allow-downgrades)

# 3б. Версии в репозитории нет — поставить из сохранённых файлов
sudo apt install ./postgrespro-1c-18*_18.3-1.noble_amd64.deb

# 3в. Версия только в архивном репозитории Postgres Pro — временно подключить его
echo "deb https://repo.postgrespro.ru/1c/archive/1c-18.3/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/pgpro-archive.list
sudo apt update && apt list -a postgrespro-1c-18-server
# … выполнить шаг 3а, затем удалить файл и снова apt update

# 4. Заморозить, чтобы пакет не обновился обратно
dpkg-query -W -f='${binary:Package}\n' 'postgrespro-1c-18*' | xargs sudo apt-mark hold
```

Откат пакета из архива Ubuntu через снимок архива (24.04+):

```bash
sudo apt update --snapshot 20260901T000000Z            # индексы архива на 1 сентября 2026, 00:00 UTC
apt policy openssl --snapshot 20260901T000000Z         # какая версия была в архиве на эту дату
sudo apt install openssl=<версия> --snapshot 20260901T000000Z
sudo apt update                                        # вернуть обычные индексы
```

Формат идентификатора снимка — `YYYYMMDDTHHMMSSZ` (UTC). Закрепить весь сервер на состоянии архива (воспроизводимые установки, одинаковые тест и продуктив): `echo 'APT::Snapshot "20260901T030400Z";' | sudo tee /etc/apt/apt.conf.d/50snapshot` — действует и на unattended-upgrades (то есть **обновления безопасности перестают приходить**, пока ID не сдвинут вперёд). В 22.04 (apt ≥ 2.4.11) для снимков нужно добавить `[snapshot=yes]` в строки источников.

Уточнения к снимкам:

- Сервис хранит снимки начиная с 1 марта 2023 г.; Canonical обещает хранить историю «не менее двух лет» — очень старые даты могут стать недоступны.
- Снимки есть только у архива Ubuntu (и репозиториев, у которых в `Release` есть поле `Snapshots:`); на репозитории Postgres Pro и PGDG ключ `--snapshot` не действует — для них свои архивы (раздел 12.2).
- ⚠ В 24.04 (apt 2.7/2.8) ключ `--snapshot` понимают не все подкоманды: поддержка в `apt show`/`apt list` добавлена только в apt 2.9.7 (changelog). Если `apt policy … --snapshot ID` ответит, что параметр не понят, задайте то же через конфигурацию: `apt policy openssl -o APT::Snapshot=20260901T000000Z`.

Оговорки:

- dpkg формально **не поддерживает** понижение версии: скрипты пакетов пишутся в расчёте на обновление вверх. Даунгрейд обычно проходит для минорных версий, но это не гарантировано.
- Понижать нужно все бинарные пакеты одного исходного пакета одновременно (иначе конфликт зависимостей `(= версия)`).
- PostgreSQL: минорные версии внутри одной мажорной совместимы по формату данных, но читать замечания к релизу (иногда после минорного обновления требуется REINDEX). Между мажорными версиями откат пакетом невозможен — только восстановление из резервной копии.
- Самый надёжный откат на ВМ — снимок (checkpoint/snapshot) гипервизора, сделанный **при остановленных СУБД и сервере 1С** перед обновлением, плюс резервные копии баз.

## 13. Сборка из исходников, checkinstall, update-alternatives

### 13.1. Сборка из исходников — кратко

На сервере 1С + PostgreSQL собирать что-либо из исходников почти никогда не нужно: СУБД берётся готовой поддерживаемой сборкой, платформа — установщиком 1С. Самосборный PostgreSQL фирмой «1С» не поддерживается. Если всё же требуется (утилита, драйвер, модуль):

```bash
sudo apt install build-essential            # gcc, g++, make, заголовки libc
# Зависимости сборки пакета из архива (нужен deb-src: «Types: deb deb-src» в *.sources)
sudo apt build-dep <пакет>
apt source <пакет>                          # скачать и распаковать исходный пакет в текущий каталог (без sudo)

# Классическая сборка: ставить только в /usr/local, чтобы не пересекаться с файлами пакетов
./configure --prefix=/usr/local
make -j"$(nproc)"
sudo make install                           # dpkg и apt об этих файлах не знают
```

Минусы `make install`: файлы не учтены в базе dpkg — их не видно в `dpkg -S`, нет обновлений безопасности, удаление — только `sudo make uninstall` (если автор его предусмотрел).

**checkinstall** (universe: jammy/noble/resolute — 1.6.2+git20170426) перехватывает `make install` и собирает из установленных файлов простой `.deb`, который затем ставится и удаляется штатно:

```bash
sudo apt install checkinstall
sudo checkinstall --pkgname=mytool --pkgversion=1.2.3 --pkgrelease=1 --default make install
dpkg -l mytool
sudo dpkg -r mytool            # удаление
```

Получается пакет без корректных зависимостей и скриптов — годится для одной машины, не для распространения. Пересборка пакета Ubuntu с правкой: `apt source П && cd П-*/ && dpkg-buildpackage -us -uc -b` (нужны `dpkg-dev`, `devscripts`).

### 13.2. update-alternatives

Механизм выбора «реализации по умолчанию», когда одну команду предоставляют несколько пакетов (`editor`, `java`, `python3` и т. п.): `/usr/bin/<имя>` → ссылка в `/etc/alternatives/<имя>` → реальный файл. Состояние хранится в `/var/lib/dpkg/alternatives/`, журнал — `/var/log/alternatives.log`.

| Команда | Что делает |
|---|---|
| `update-alternatives --get-selections` | все группы и текущий выбор |
| `update-alternatives --display ИМЯ` | режим (auto/manual), варианты с приоритетами, текущая ссылка |
| `update-alternatives --list ИМЯ` | только пути вариантов |
| `sudo update-alternatives --config ИМЯ` | выбрать интерактивно |
| `sudo update-alternatives --set ИМЯ ПУТЬ` | выбрать без диалога (для скриптов) |
| `sudo update-alternatives --auto ИМЯ` | вернуть автоматический режим (наибольший приоритет) |
| `sudo update-alternatives --install ССЫЛКА ИМЯ ПУТЬ ПРИОРИТЕТ [--slave ССЫЛКА ИМЯ ПУТЬ]…` | зарегистрировать вариант |
| `sudo update-alternatives --remove ИМЯ ПУТЬ` / `--remove-all ИМЯ` | убрать вариант / всю группу |

```bash
sudo update-alternatives --config editor                 # редактор по умолчанию (visudo, crontab -e, systemctl edit)
sudo update-alternatives --set editor /usr/bin/vim.basic
update-alternatives --display java
# зарегистрировать свою сборку как вариант
sudo update-alternatives --install /usr/local/bin/mytool mytool /opt/mytool-2.0/bin/mytool 20
```

Режимы: **auto** — система сама переключает ссылку на вариант с наибольшим приоритетом при установке/удалении пакетов; **manual** — выбор администратора сохраняется. `--config`/`--set` переводят группу в manual.

К PostgreSQL: пакеты архива Ubuntu/PGDG (и «PostgreSQL с патчем от 1С», использующий ту же раскладку) применяют собственный механизм `pg_wrapper` из `postgresql-common` (`/usr/bin/psql` → ссылка на `pg_wrapper`, который выбирает версию), а не alternatives. У сборок Postgres Pro программы лежат в `/opt/pgpro/<ветка>/bin/`: при установке метапакетом (`postgrespro-1c-18`) они попадают в `PATH` автоматически, при установке отдельными пакетами ссылки создаёт утилита из пакета `-client` — `sudo /opt/pgpro/1c-18/bin/pg-wrapper links update` (убрать — `pg-wrapper links remove`) **[офиц., документация Postgres Pro: справка pg-wrapper и раздел об установке из бинарных пакетов; для ветки `1c-18` путь подставлен по аналогии с `std-17`]**. В системах с `update-alternatives` (Ubuntu к ним относится) `pg-wrapper` регистрирует программы Postgres Pro именно как альтернативы с приоритетами — найти группы: `update-alternatives --get-selections | grep -i -E 'psql|pgpro|postgres'`, затем `update-alternatives --display <группа>` / `sudo update-alternatives --config <группа>` (⚠ имена групп на стенде не проверялись). Без `pg-wrapper` программы вызываются по полному пути: `/opt/pgpro/1c-18/bin/psql`.

## Типичные ошибки и подводные камни

| Симптом | Причина | Решение |
|---|---|---|
| `E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process N (unattended-upgr)` | работает автообновление или другой apt | дождаться (`-o DPkg::Lock::Timeout=300`), посмотреть владельца (`ps`, `lsof`); lock-файлы не удалять (11.1) |
| `E: dpkg was interrupted, you must manually run 'sudo dpkg --configure -a'` | установка прервана (перезагрузка, нет места, убит процесс) | `df -h`; `sudo dpkg --configure -a`; затем `sudo apt -f install` |
| `E: Sub-process /usr/bin/dpkg returned an error code (1)` | упал скрипт пакета (postinst/prerm) | читать конец `/var/log/apt/term.log`; устранить причину (нет места, занят порт, служба не стартует); `sudo dpkg --configure -a` |
| `The following packages have unmet dependencies` / `E: Unmet dependencies. Try 'apt --fix-broken install'` | `.deb` поставлен через `dpkg -i` без зависимостей; пакет собран под другой релиз | `sudo apt -f install`; проверить, что пакет для вашего релиза (`dpkg -I файл.deb`, поле Depends) |
| `The following packages have been kept back` | phased update; hold; обновление требует установки/удаления пакетов | `apt policy П` (ищем `phased`), `apt-mark showhold`; если не hold и не фаза — `sudo apt full-upgrade -s` и изучить план |
| `E: Held packages were changed and -y was used without --allow-change-held-packages` | скрипт пытается изменить пакет на hold | осознанно `apt-mark unhold` или убрать пакет из команды |
| `NO_PUBKEY XXXXXXXX` / `The following signatures couldn't be verified because the public key is not available` | ключ репозитория не установлен, лежит в устаревшем `trusted.gpg`, или поставщик сменил ключ | положить актуальный ключ в `/etc/apt/keyrings/` и указать `Signed-By` (5.3); для Postgres Pro — заново взять свежий `pgpro-repo-add.sh`/ключи из `keys/` |
| `W: Key is stored in legacy trusted.gpg keyring (/etc/apt/trusted.gpg), see the DEPRECATION section in apt-key(8)` | ключ добавлен через `apt-key add` | перенести ключ в отдельный файл и `signed-by` (5.3); в apt ≥ 2.9.24 такой ключ уже не действует |
| `apt-key: command not found` (26.04) | `apt-key` удалён | использовать `Signed-By`; старые инструкции вида «curl … и apt-key add -» заменить по шаблону из 5.3 |
| Предупреждение или ошибка `apt update` о слабом алгоритме ключа (`… uses weak algorithm (rsa1024)`; ⚠ точный текст зависит от версии apt) | с 24.04 apt принимает подписи только ключами RSA ≥ 2048, Ed25519, Ed448 **[офиц., release notes 24.04]**: сначала это было предупреждение, с обновлением apt 2.8.x — ошибка | получить у поставщика репозитория новый ключ; PPA — удалить и добавить заново (`add-apt-repository -r`, затем снова `add-apt-repository`) |
| После добавления `APT::Default-Release "noble";` `apt upgrade` предлагает версии с `~bpo`/из `noble-backports` | у всех карманов Ubuntu `Codename: noble` — все получили приоритет 990, защита backports (100) снята | удалить параметр (`grep -r Default-Release /etc/apt/`), проверить `apt policy`; раздел 7.3 |
| `postgresql-NN : Depends: postgresql-common … but it is not installable` при установке «PostgreSQL с патчем от 1С» | `postgresql-common` запрещён закреплением с отрицательным приоритетом (пример 1 из 7.3 в варианте для Postgres Pro) либо компонент/репозиторий Ubuntu недоступен | убрать `postgresql-common` из запрещающей записи; `apt policy postgresql-common` должен показывать кандидата |
| После правки needrestart начали перезапускаться dbus / сеть / `systemd-logind`, обрываются SSH-сеансы | в файле из `conf.d` написано `$nrconf{override_rc} = { … };` — штатный список исключений заменён целиком | переписать на `$nrconf{override_rc}{qr(…)} = 0;` (8.3); проверить `sudo needrestart -r l -v` |
| `E: The repository '… <codename> Release' does not have a Release file` / `404 Not Found` | у поставщика нет каталога для вашего релиза (новый или промежуточный релиз, опечатка в кодовом имени, после обновления релиза) | открыть `…/dists/` репозитория в браузере, сверить кодовое имя; для 1С/PostgreSQL использовать только LTS |
| `E: Release file for … is not valid yet (invalid for another 3h 12min)` или `… is expired` | неверные часы в ВМ (после паузы/восстановления снимка) | исправить время: `timedatectl`, синхронизация (chrony/systemd-timesyncd, служба времени гипервизора); затем `apt update` |
| `E: Repository '…' changed its 'Origin'/'Label'/'Suite' value` | поставщик изменил метаданные репозитория | убедиться, что это ожидаемо, и `sudo apt update --allow-releaseinfo-change` |
| `E: Conflicting values set for option Signed-By regarding source …` | один репозиторий описан дважды с разными ключами (например, `.list` от скрипта и `.sources` вручную) | оставить одно описание: `grep -r <хост> /etc/apt/sources.list /etc/apt/sources.list.d/` |
| `W: Target Packages (…) is configured multiple times in …` | дубли источников | удалить дубль |
| `E: Unable to locate package П` | не выполнен `apt update`; пакет в `universe`/`multiverse`, а компонент выключен; имя другое в этом релизе (t64-переименования); нет сборки для архитектуры | `sudo apt update`; `apt search`, `apt-file search`; `sudo add-apt-repository universe` |
| `Hash Sum mismatch` | испорченный кеш прокси/зеркала, обрыв связи | `sudo rm -rf /var/lib/apt/lists/* && sudo apt update`; `Acquire::http::No-Cache "true";` или другое зеркало |
| `Temporary failure resolving 'archive.ubuntu.com'` | нет DNS/сети или нужен прокси | проверить `resolvectl status`, `ping`, настроить прокси (11.2) |
| `dpkg: error processing archive … trying to overwrite '/путь', which is also in package X` | два пакета содержат один файл (смешаны сборки разных поставщиков) | удалить конфликтующий пакет; `--force-overwrite` — только понимая последствия |
| `postgrespro-1c-18 : Conflicts: postgresql-common` | попытка поставить сборку Postgres Pro 1С рядом с системным/PGDG PostgreSQL (или наоборот — `apt install postgresql-common` ради скрипта PGDG) | на сервере баз 1С держать одну сборку; системный PostgreSQL удалить (`apt purge 'postgresql*'` — сначала убедиться, что в нём нет данных) |
| После `apt upgrade` 1С не подключается к базе / ошибки СУБД, в `dpkg.log` — обновление `postgresql-NN`, `libpq5` | сборку с патчем 1С заменили пакеты из архива Ubuntu/PGDG (нет hold/pinning) | вернуть сборку 1С (12.3), поставить hold и pinning (7.2, 7.3) |
| Пользователей 1С «выбросило» около 6–7 утра; в `history.log` — `unattended-upgrade` | автообновление обновило библиотеку/СУБД, needrestart перезапустил службы | blacklist + hold (8.1), исключения needrestart (8.3), перенос таймера (8.2) |
| После обновления релиза PostgreSQL не стартует: `error while loading shared libraries: libicu…so.NN` | пакет СУБД от старого релиза, библиотека удалена | подключить репозиторий для нового кодового имени, обновить пакеты СУБД (9.2) |
| В журнале PostgreSQL: `WARNING: database "…" has a collation version mismatch` | сменилась версия glibc/ICU (обновление релиза, перенос каталога данных на другую ОС) | `REINDEX DATABASE …; ALTER DATABASE … REFRESH COLLATION VERSION;` (9.2) |
| Обновление ядра падает: `No space left on device`, `/boot` заполнен | накопились старые ядра | `sudo apt autoremove --purge`; при сломанном apt — `dpkg -P` самого старого неработающего ядра, затем `apt -f install` |
| После `apt autoremove` сервер/клиент 1С не запускается (`cannot open shared object file`) | apt удалил библиотеку, которую считал ненужной: платформа 1С из `.run` не числится её потребителем | вернуть пакет (`apt install`), пометить `apt-mark manual`; искать по `history.log`, что удалено |
| `debconf: unable to initialize frontend: Dialog` / установка «зависла» на вопросе в скрипте | нет терминала для диалога | `DEBIAN_FRONTEND=noninteractive`, при необходимости preseed через `debconf-set-selections` |
| `N: Download is performed unsandboxed as root as file … couldn't be accessed by user '_apt'` | `.deb` лежит в каталоге, недоступном пользователю `_apt` | безвредно; положить файл в `/tmp` |
| `add-apt-repository: command not found` | нет пакета | `sudo apt install software-properties-common` |
| `apt upgrade` после подключения PGDG хочет заменить `libpq5`, `postgresql-common` | у PGDG версии выше системных | если не нужно — pin `origin apt.postgresql.org` с приоритетом 100 (7.3) |
| `apt` предлагает удалить десятки пакетов при установке одного | конфликт версий/репозиториев; смешаны релизы | **не подтверждать**; `apt install -s`, `apt policy`, в apt ≥ 3.1 — `apt why-not П` |
| Автообновление не ставит пакеты из стороннего репозитория | его origin не входит в `Allowed-Origins` | так и задумано; для СУБД — хорошо. Иначе добавить `"Origin:Suite"` и проверить `--dry-run` |
| snap-служба перезапустилась сама | автообновление snap (4 раза в сутки) | `snap refresh --hold`, `refresh.timer` (раздел 10) |

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Обновить индексы | `sudo apt update` |
| Что можно обновить | `apt list --upgradable` |
| Обновить всё без удаления пакетов | `sudo apt upgrade` |
| Обновить с разрешением удалять | `sudo apt full-upgrade` |
| Только посмотреть план | `sudo apt upgrade -s` / `apt install -s П` |
| Установить пакет | `sudo apt install П` |
| Установить без рекомендуемых | `sudo apt install --no-install-recommends П` |
| Установить конкретную версию | `sudo apt install П=ВЕРСИЯ` |
| Установить локальный файл | `sudo apt install ./файл.deb` |
| Починить зависимости | `sudo apt -f install` |
| Довести прерванную установку | `sudo dpkg --configure -a` |
| Переустановить | `sudo apt reinstall П` |
| Удалить / удалить с конфигами | `sudo apt remove П` / `sudo apt purge П` |
| Убрать ненужные зависимости и старые ядра | `sudo apt autoremove --purge` |
| Найти пакет | `apt search СЛОВО`; `apt-cache search --names-only СЛОВО` |
| Сведения о пакете | `apt show П`; `dpkg -s П` |
| Доступные версии и источник | `apt policy П`; `apt list -a П`; `apt-cache madison П` |
| Установлен ли пакет, какой версии | `dpkg -l П`; `apt list --installed П` |
| Файлы пакета | `dpkg -L П` |
| Чей это файл (установленные пакеты) | `dpkg -S /путь` |
| В каком пакете есть файл (все репозитории) | `apt-file search путь` |
| Зависимости / кто зависит | `apt depends П` / `apt rdepends --installed П` |
| Скачать `.deb` | `apt download П` |
| Что внутри `.deb` | `dpkg -I файл.deb`; `dpkg -c файл.deb` |
| Заморозить / разморозить / список | `sudo apt-mark hold П` / `unhold П` / `apt-mark showhold` |
| Пометить «установлен вручную» | `sudo apt-mark manual П` |
| Все приоритеты и закрепления | `apt policy` |
| Пакеты не из репозиториев | `apt list '?obsolete'` |
| Список источников | `grep -rh -e '^deb' -e '^URIs' -e '^Suites' /etc/apt/sources.list /etc/apt/sources.list.d/` |
| Подключить PPA / убрать с откатом пакетов | `sudo add-apt-repository ppa:x/y` / `sudo ppa-purge ppa:x/y` |
| Конвертировать источники в deb822 (apt 3.x) | `sudo apt modernize-sources` |
| Посмотреть ключ | `gpg --show-keys файл.asc` |
| Преобразовать ключ в бинарный | `gpg --dearmor -o /etc/apt/keyrings/x.gpg < key.asc` |
| Проверить автообновление «всухую» | `sudo unattended-upgrade -v --dry-run` |
| Включить/выключить автообновление | `sudo dpkg-reconfigure -plow unattended-upgrades` |
| Когда сработают таймеры apt | `systemctl list-timers 'apt-daily*'` |
| Что требует перезапуска | `sudo needrestart -r l`; ядро — `sudo needrestart -k` |
| Нужна ли перезагрузка | `cat /var/run/reboot-required /var/run/reboot-required.pkgs` |
| Кто держит блокировку apt | `sudo lsof /var/lib/dpkg/lock-frontend` |
| Подождать блокировку | `sudo apt-get -o DPkg::Lock::Timeout=300 install П` |
| История установок | `less /var/log/apt/history.log`; `zgrep -h ' upgrade ' /var/log/dpkg.log*` |
| История (apt 3.x) | `apt history-list`; `apt history-info N` |
| Откатить версию | `sudo apt install П=СТАРАЯ_ВЕРСИЯ` (+ `--allow-downgrades` с `-y`) |
| Очистить кеш пакетов | `sudo apt clean` |
| Очистить кеш пакетов и индексы (24.04+) | `sudo apt distclean`, затем при необходимости `sudo apt update` |
| Сохранять `.deb` после `apt install` | `Binary::apt::APT::Keep-Downloaded-Packages "true";` в `/etc/apt/apt.conf.d/01keep-debs` |
| Не перезапускать службу автоматически (needrestart, 24.04+) | `$nrconf{override_rc}{qr(^имя\.service$)} = 0;` в `/etc/needrestart/conf.d/*.conf` |
| Установлена ли платформа 1С пакетами | `dpkg -l '1c-enterprise*'` (пусто — ставилась через `setup-full-….run`; смотреть `ls /opt/1cv8/x86_64/`) |
| Официально подключить Postgres Pro 1С | `wget https://repo.postgres.ru/1c/1c-18/keys/pgpro-repo-add.sh && sudo sh pgpro-repo-add.sh` |
| Остатки конфигов удалённых пакетов | `sudo apt purge '?config-files'` (apt ≥ 2.0; вариант через `dpkg -l` и `dpkg -P` — в разделе 11.4) |
| Самые большие пакеты | `dpkg-query -W -f='${Installed-Size}\t${Package}\n'` с сортировкой `sort -n` (полная команда — в разделе 3.2) |
| Проверить целостность файлов пакета | `sudo dpkg -V П` |
| Перенастроить пакет | `sudo dpkg-reconfigure П` |
| Заранее ответить на вопрос установки | `sudo debconf-set-selections <<< "П вопрос тип значение"` (пример с конвейером — в разделе 3.3) |
| Текущая конфигурация apt | `apt-config dump` |
| Прокси для apt | файл `/etc/apt/apt.conf.d/95proxy`: `Acquire::http::Proxy "http://host:3128/";` |
| Проверить новый релиз | `do-release-upgrade -c` |
| Запретить предложения обновить релиз | `Prompt=never` в `/etc/update-manager/release-upgrades` |
| Статус Ubuntu Pro | `pro status`; `pro security-status` |
| Перейти на ядро HWE (24.04) | `sudo apt install --install-recommends linux-generic-hwe-24.04` |
| Список snap / заморозить автообновление | `snap list` / `sudo snap refresh --hold` |
| Выбрать альтернативу | `sudo update-alternatives --config ИМЯ` |
| Почему пакет установлен / не ставится (apt ≥ 3.1) | `apt why П` / `apt why-not П` |

## Источники

Официальная документация Ubuntu / Canonical:

- https://ubuntu.com/server/docs/how-to/software/package-management/ — apt, dpkg, aptitude, расположение `ubuntu.sources`, компоненты, журнал dpkg.
- https://ubuntu.com/server/docs/how-to/software/automatic-updates/ — unattended-upgrades: файлы, Allowed-Origins, Package-Blacklist, перезагрузка, почта, таймеры, needrestart (автоперезапуск с 24.04, `override_rc`, `conf.d`), Postpone-For-Days.
- https://ubuntu.com/server/docs/explanation/software/about-apt-upgrade-and-phased-updates/ — phased updates, `Always-Include-Phased-Updates`, пометка `(phased N%)`.
- https://ubuntu.com/server/docs/explanation/software/third-party-repository-usage/ — риски сторонних репозиториев, `Signed-By`, pinning 100/1, `ppa-purge`, совет не обновлять релиз «на месте».
- https://ubuntu.com/server/docs/how-to/software/upgrade-your-release/ — `do-release-upgrade`, подготовка, LTS→LTS после первого точечного релиза, отключение сторонних репозиториев.
- https://documentation.ubuntu.com/release-notes/26.04/ и …/26.04/summary-for-lts-users/ — Ubuntu 26.04: поддержка до 04.2031, пути обновления, APT 3.x (новый решатель, OpenSSL, пейджер, удаление apt-key, history-команды), ядро 7.0, glibc 2.43, systemd 259, sudo-rs, rust-coreutils, chrony, Dracut, PostgreSQL 18.
- https://documentation.ubuntu.com/release-notes/24.04/ — Ubuntu 24.04: deb822 `ubuntu.sources`, требования к ключам (RSA ≥ 2048), приоритет 100 для `-proposed`, автоперезапуск служб needrestart, ядро 6.8, glibc 2.39, PostgreSQL 16.
- https://launchpad.net/ubuntu/+source/apt (а также +source/checkinstall, +source/gdebi, +source/apt-offline) — версии пакетов по релизам.
- https://snapshot.ubuntu.com/ — сервис снимков архива: `--snapshot`/`-S`, `--update`, `Snapshot:`, `APT::Snapshot`, формат ID.
- https://ubuntu.com/kernel/lifecycle — ядра GA/HWE по релизам, сроки, `linux-generic-hwe-24.04`, `hwe-support-status`.
- https://ubuntu.com/pro и https://ubuntu.com/pro-client/docs/ — Ubuntu Pro: ESM 10/15 лет, бесплатно до 5 машин, `pro attach`, сервисы по умолчанию.
- Сообщения о выходе 26.04.1 и открытии пути 24.04 → 26.04 (29.09.2026): https://discourse.ubuntu.com/t/ubuntu-26-04-1-lts-released/86808 , https://ubuntuhandbook.org/index.php/2026/09/ubuntu-24-04-to-ubuntu-26-04-1-upgrade/ .

Man-страницы (manpages.ubuntu.com, выпуск resolute, если не указано иное):

- apt(8) — перечень команд apt 3.2.0, `why`/`why-not`, выбор версии и выпуска.
- apt-get(8) — команды и опции (`--only-upgrade`, `--allow-downgrades`, `--print-uris`, `-S/--snapshot`, `-U/--update`, `--allow-releaseinfo-change`).
- apt-cache(8) — `policy`, `madison`, `depends --recurse` и опции.
- apt-mark(8) — hold/unhold/showhold, auto/manual.
- apt_preferences(5) — pinning: приоритеты, формат записей, ключи release, фазирование, `APT::Machine-ID`.
- sources.list(5) — однострочный формат и deb822, поля, `Signed-By`, каталоги ключей, имена файлов, срок жизни однострочного формата («not before 2029»).
- apt.conf(5), apt-transport-http(1) — порядок чтения конфигурации, `Acquire::*`, прокси, `DIRECT`, `NeverAutoRemove::KernelCount`.
- apt-key(8) (выпуск noble) — формулировка об устаревании, `/etc/apt/keyrings` с apt 2.4, форматы `.gpg`/`.asc`.
- dpkg(1), update-alternatives(1), do-release-upgrade(8), unattended-upgrade(8), needrestart(1), snap(8) — опции соответствующих утилит.

APT (Debian):

- https://raw.githubusercontent.com/Debian/apt/main/debian/NEWS — история изменений: автоудаление ядер (2.1.16), fallback на trusted.gpg (2.4.0), отказ от apt-key (2.9.15), OpenSSL/Sequoia (2.9.19), `trusted.gpg` не доверен и устаревание источников без Signed-By (2.9.24), новый решатель по умолчанию (3.1.10).
- https://raw.githubusercontent.com/Debian/apt/main/debian/apt-daily.timer и …/apt-daily-upgrade.timer — расписание таймеров.
- https://lists.debian.org/deity/2024/04/msg00040.html — Debian bug #1069167: нет ожидания блокировки списков.
- https://raw.githubusercontent.com/mvo5/unattended-upgrades/master/data/50unattended-upgrades.Ubuntu — штатный конфиг unattended-upgrades с умолчаниями.
- https://raw.githubusercontent.com/liske/needrestart/master/ex/needrestart.conf — штатный конфиг needrestart, синтаксис `override_rc`.

PostgreSQL:

- https://www.postgresql.org/download/linux/ubuntu/ и https://wiki.postgresql.org/wiki/Apt — подключение PGDG (скрипт и вручную, `pgdg.sources`), поддерживаемые релизы и версии.
- https://apt.postgresql.org/pub/repos/apt/dists/noble-pgdg/Release — Origin/Label/Suite репозитория PGDG.
- https://apt-archive.postgresql.org/ — архив старых версий PGDG (`<dist>-pgdg-archive`).
- https://wiki.postgresql.org/wiki/Locale_data_changes — изменения сортировки glibc, затронутые индексы, необходимость REINDEX, проверочная команда `sort`.

Postgres Professional:

- https://repo.postgrespro.ru/1c/ , …/1c/1c-18/ , …/1c/1c-18/keys/ , …/1c/1c-18/keys/pgpro-repo-add.sh , …/1c/1c-18/ubuntu/dists/ , …/1c/archive/ — структура репозитория, действия скрипта подключения, поддерживаемые кодовые имена, архив версий.
- https://repo.postgrespro.ru/1c/1c-18/ubuntu/dists/noble/Release и …/main/binary-amd64/Packages (а также resolute и 1c-17/jammy) — Origin/Label, имена пакетов, версии, зависимости, Conflicts.
- https://1c.postgres.ru/ — условия использования сборок для 1С.

1С:

- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/spisok-podderzhivaemykh-subd/ — список поддерживаемых СУБД и версий.
- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/operatsionnye-sistemy/ — список поддерживаемых ОС (Ubuntu 20.04/22.04/24.04).
- https://its.1c.ru/db/content/metod8dev/src/developers/scalability/instructions/i8105953.htm — старая (2018, 8.3.13) инструкция по установке платформы на Linux: deb-пакеты `1c-enterprise83-*`, установка через gdebi, зависимости. Использована только как историческая справка.
- Документация платформы «1С:Предприятие 8.3.27» на ИТС (its.1c.ru/db/v8327doc), «Руководство администратора», гл. 2 «Установка системы» (разделы 2.2–2.3: два способа установки в Linux, имена файлов `setup-full-…run` и `1c-enterprise-…deb`, пакетный режим `--mode unattended --enable-components`, доустановка зависимостей и шрифтов) и гл. 12 «Удаление» (`uninstaller-full`, несовместимость способов) — по конспектам `kb/its-docs/adm-gl02-ustanovka-p1.md` и `kb/its-docs/adm-gl11-gl12-pr02-pr05-obnovlenie-udalenie-zhurnal-oshibki.md`.
- https://github.com/1C-Company/docker_fresh (официальный репозиторий 1С: `download_releases.py`, `images/core/Dockerfile`, `images/db/Dockerfile`) — названия дистрибутивов на releases.1c.ru («Технологическая платформа 1С:Предприятия (64-bit) для Linux», «Клиент … для DEB-based Linux-систем», «Дистрибутив СУБД PostgreSQL для Debian 13.0 x86 (64-bit) одним архивом»), установка платформы из `server64_*.zip` командой `setup-full-<версия>-x86_64.run --mode unattended --enable-components …`, установка deb-пакетов СУБД через `apt-get install`.
- https://github.com/firstBitMarksistskaya/onec-docker (`scripts/install.sh`) — практика: до релиза 8.3.20 — `dpkg -i 1c-enterprise*-{common,server}*.deb`, с 8.3.20 — `setup-full-…run`.
- https://interface31.ru/post/ustanovka-postgresql-1c-10-dlya-1spredpriyatie-na-debian-ubuntu/ — практика: состав набора «PostgreSQL от 1С» (`libpq5`, `postgresql-client-10`, `postgresql-10`), предварительная установка `postgresql-common` из репозитория ОС, `apt-mark hold`.

Источники, по которым выполнена проверка (рецензия 10.10.2026), сверх перечисленных выше:

- https://raw.githubusercontent.com/Debian/apt/main/debian/NEWS — 1.2~exp1 (`Binary::apt::APT::Keep-Downloaded-Packages`), 1.9.11 (ожидание блокировки: бессрочно в терминале, 120 с без него).
- https://raw.githubusercontent.com/Debian/apt/main/debian/changelog — версии, в которых появились `distclean` (2.7.8), `-U/--update` и `--snapshot` (2.7.0), `--audit` (2.9.2), `--snapshot` для `show`/`list` (2.9.7), `modernize-sources` (2.9.26), `why`/`why-not` и `Include`/`Exclude` (3.1.0), `history-*` (3.1.6–3.1.7).
- https://raw.githubusercontent.com/Debian/apt/main/apt-pkg/versionmatch.cc и …/apt-pkg/policy.cc — сопоставление `Pin: version` (префикс и `fnmatch`), сопоставление выпуска с `Suite` или `Codename`, обработка `APT::Default-Release` (закрепление 990 поверх приоритетов NotAutomatic).
- http://archive.ubuntu.com/ubuntu/dists/noble-backports/Release — `Suite: noble-backports`, `Codename: noble`, `NotAutomatic: yes`, `ButAutomaticUpgrades: yes`.
- https://raw.githubusercontent.com/mvo5/unattended-upgrades/master/unattended-upgrade — `is_pkg_change_allowed` (blacklist и hold), `match_whitelist_string` и преобразование `Allowed-Origins` в `o=…,a=…`, `re.match` для `Package-Blacklist`.
- https://raw.githubusercontent.com/liske/needrestart/master/needrestart и …/ex/needrestart.conf — штатный `override_rc`, чтение `conf.d/*.conf`, порядок сопоставления; man needrestart(1) (noble) — `NEEDRESTART_MODE`, `NEEDRESTART_SUSPEND`.
- https://repo.postgrespro.ru/1c/1c-18/meta.json , …/keys/ (три файла ключей), …/ubuntu/dists/{noble,resolute}/Release , …/main/binary-amd64/Packages , https://repo.postgrespro.ru/1c/archive/ — официальные команды установки, содержимое ключей, отсутствие поля `Suite`, зависимости пакетов, состав архива версий.
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux и …/pg-setup — `pg-wrapper links update`, `pg-setup initdb`/`service`, каталоги `/opt/pgpro/…` и `/var/lib/pgpro/…` (на примере `std-17`).
- https://launchpad.net/ubuntu/+source/apt , …/+source/icu , …/+source/gdebi , …/+source/apt-offline , …/+source/checkinstall — версии пакетов по релизам (apt: jammy 2.4.5 → 2.4.14, noble 2.7.14build2 → 2.8.3, resolute 3.2.0, stonking 3.3.3).
- https://bugs.debian.org/1069167 — нет ожидания блокировки `/var/lib/apt/lists/lock` (на 10.2026 не исправлено).
- https://www.postgresql.org/ — на 10.10.2026: PostgreSQL 19 Beta 4 (24.09.2026); текущие минорные выпуски 18.6 / 17.11 / 16.15 / 15.19 / 14.24 (13.08.2026).

