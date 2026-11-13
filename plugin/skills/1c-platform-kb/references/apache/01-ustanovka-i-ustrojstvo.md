# Apache HTTP Server на Ubuntu: версии, установка, устройство конфигурации, MPM, модули, виртуальные хосты

> **Официальные тексты по теме** (конспекты ИТС и статьи базы, на которые опирается раздел): `../its-docs/adm-gl08-veb-servery-p1.md`, `../its-docs/adm-gl08-veb-servery-p2.md` — глава 8 «Настройка веб-серверов» руководства администратора 8.3.27 (требования к Apache, рекомендуемый MPM `worker`, права пользователя веб-сервера, отдельный экземпляр Apache на каждую версию платформы); `../its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md`; публикация 1С — `../1c/05-veb-publikaciya-apache-nginx.md`. Документация Apache — https://httpd.apache.org/docs/2.4/; описание раскладки Debian на самом сервере — `zless /usr/share/doc/apache2/README.Debian.gz`.

> Статус: проверено независимой сверкой 20.10.2026: с исходниками документации и кодом httpd ветки `2.4.x` (`core`, `mpm_common`, `event`, `stopping`, `bind`, `sections`, `configuring`, `vhosts/details`, `mod_systemd`, `mod_macro`; `listen.c`, `vhost.c`, `util.c`, `config.c`, `mod_so.c`, `mod_alias.c`, `mod_proxy.c`, MPM, `configure.in`), `CHANGES_2.4`, страницей уязвимостей 2.4 и главной страницей httpd.apache.org, исходниками пакета Debian `apache2` (метки `debian/2.4.58-1`, `2.4.66-2`: юниты, `apache2ctl`, `envvars`, `apache2.conf.in`, `postinst`, `a2enmod`, `a2query`, `README.Debian`, `README.multiple-instances`, `setup-instance`, `rules`, `debian/changelog`) и `php-fpm` (ветка `debian/main/8.3`), журналами Ubuntu `2.4.52-1ubuntu4.25` / `2.4.58-1ubuntu8.17` / `2.4.66-2ubuntu2.6`, страницами и списками файлов packages.ubuntu.com, документацией Ubuntu Server, man-страницами systemd и dash, главой 8 «Руководства администратора» 1С 8.3.27; исправлено 11 ошибок, закрыто 6 пометок (ещё 3 подтверждены по первоисточникам с оговоркой «на сервере не проверялось»); на сервере не проверялось.

> Область: Apache HTTP Server 2.4 на Ubuntu Server 22.04 / 24.04 / 26.04 (пакет `apache2` из репозитория Ubuntu) — версии и поддержка, установка и состав пакетов, служба systemd (в том числе несколько экземпляров `apache2@`), раскладка `/etc/apache2`, утилиты `a2enmod`/`a2ensite`/`a2enconf`/`a2query`/`apache2ctl`, порядок чтения конфигурации, секции и `.htaccess`, MPM, модули, имя сервера, виртуальные хосты, права, AppArmor, перезагрузка без обрыва. Публикация 1С (`webinst`, `default.vrd`, модуль `wsap24.so`) здесь **не** расписывается — она в `../1c/05-…`; здесь — только то, где общие настройки Apache важны для 1С. | Версии: httpd **2.4.69** (01.10.2026) — текущий выпуск; Ubuntu 22.04 — `2.4.52-1ubuntu4.25`, 24.04 — `2.4.58-1ubuntu8.17`, 26.04 — `2.4.66-2ubuntu2.6` (все три — от 08.10.2026). | Актуальность: 2026-10-20

Пометки в тексте:

- **[Apache-док]** — документация Apache HTTP Server 2.4 (httpd.apache.org/docs/2.4 и её исходники XML в ветке `2.4.x` репозитория apache/httpd);
- **[Apache-код]** — исходный код httpd ветки `2.4.x` (raw.githubusercontent.com/apache/httpd/2.4.x/…);
- **[Apache-CL]** — журнал изменений `CHANGES_2.4`, главная страница проекта, страница уязвимостей 2.4;
- **[Debian]** — исходники пакета `apache2` (salsa.debian.org, apache-team/apache2), включая `README.Debian` и man-страницы утилит;
- **[Ubuntu]** — packages.ubuntu.com (версии, состав и списки файлов пакетов), changelogs.ubuntu.com, manpages.ubuntu.com, документация Ubuntu Server (documentation.ubuntu.com/server);
- **[ИТС-адм разд. N]** — «Руководство администратора» 1С:Предприятия 8.3.27, глава 8;
- **[сторонний]** — сторонние проекты по их официальным страницам;
- **[практика]** — опыт эксплуатации или вывод автора из перечисленных источников;
- **⚠** — не удалось подтвердить первоисточником или не проверялось на сервере: проверяйте на стенде.

Связанные статьи (их тему здесь не расписываем):

- `../1c/05-veb-publikaciya-apache-nginx.md` — публикация 1С: `webinst`, `default.vrd`, `wsap24.so`, права (§6), юнит Ubuntu 26.04 и модуль 1С (§3.1, §6.1), `worker` под нагрузку (§12), HTTPS, nginx;
- `02-https-bezopasnost-autentifikaciya.md` — `mod_ssl`, сертификаты, certbot, TLS, заголовки, Basic/LDAP/Kerberos (`mod_auth_gssapi`);
- `03-proizvoditelnost-proksi-zhurnaly-monitoring.md` — MPM под нагрузку, таймауты, размер тела запроса, `mod_proxy`, журналы, `mod_status`, Loki;
- `04-tipovye-problemy-i-apache-na-windows.md` — аварии подробнее, Apache под Windows; `../1c-windows/03-veb-publikaciya-iis.md`, раздел 13;
- `../linux/05-systemd-sluzhby-zhurnaly-cron.md` (systemd, drop-in), `../linux/04-pakety-apt.md` (apt, автоматические обновления, сроки поддержки), `../linux/08-set-ssh-firewall.md` (`ufw`); сервисы за Apache — `../redmine/02-ustanovka-ubuntu-postgresql.md`, `../netbox/02-ustanovka-ubuntu.md`, `../observability/03-loki-i-grafana.md`.

Условные обозначения: сервер 1С с публикацией — ВМ `srv-1c-app` (FQDN `srv-1c-app.corp.example`, имя, по которому пользователи открывают публикацию, — `1c.corp.example`); ВМ сервисов — `srv-itsm` (Redmine, NetBox) и `srv-obs` (GlitchTip, Loki, Grafana); домен `corp.example` замените своим. Команды с `sudo` выполняет администратор (root через sudo); проверки «глазами веб-сервера» — `sudo -u www-data …`. Версия платформы 1С в путях — `8.3.27.2074`, как в `../1c/05`.

## Кратко — главные факты

1. **Поддерживается одна ветка — 2.4.x.** Текущий выпуск — **2.4.69 от 01.10.2026** (закрыто 20 уязвимостей). Ветка 2.2 закрыта: последний выпуск 2.2.34 (июль 2017), исправлений больше не будет **[Apache-CL]**.
2. **Ubuntu не меняет версию Apache внутри выпуска:** 22.04 — 2.4.52, 24.04 — 2.4.58, 26.04 — 2.4.66; исправления безопасности переносятся патчами (суффикс `ubuntuN.M` растёт). Обновления от 05.10 и 08.10.2026 закрыли 12 из 20 CVE выпуска 2.4.69 во всех трёх выпусках. «2.4.58» в выводе `apache2 -v` само по себе не значит «уязвим» — смотрите журнал пакета **[Ubuntu]**.
3. **Пакеты:** `apache2` (скрипты, `/etc/apache2`, юниты systemd) тянет `apache2-bin` (`/usr/sbin/apache2` и 118 модулей `.so`), `apache2-data`, `apache2-utils` (`ab`, `htpasswd`, `rotatelogs`, `htcacheclean` и др.); рекомендует `ssl-cert` **[Ubuntu]**.
4. **Что включено сразу после установки:** MPM `event`; модули `authz_host auth_basic access_compat authn_file authz_user alias dir autoindex env mime negotiation setenvif filter deflate status reqtimeout`; фрагменты `charset localized-error-pages other-vhosts-access-log security serve-cgi-bin`; сайт `000-default` **[Debian]**.
5. **Раскладка Debian:** главный файл `/etc/apache2/apache2.conf` подключает `mods-enabled/*.load`, `mods-enabled/*.conf`, `ports.conf`, `conf-enabled/*.conf`, `sites-enabled/*.conf` — **только файлы с суффиксом `.conf`** (и `.load`). Включение и выключение — символьными ссылками через `a2enmod`/`a2dismod`, `a2ensite`/`a2dissite`, `a2enconf`/`a2disconf` **[Debian]**.
6. **`apache2` напрямую не запускают:** пользователь, каталоги и журналы заданы в `/etc/apache2/envvars`, их подхватывает только `apache2ctl`; ключи `-t`, `-S`, `-M`, `-V` давайте через `apache2ctl` **[Debian]**.
7. **Перед каждой перезагрузкой — `sudo apache2ctl configtest` → `Syntax OK`**, затем `sudo systemctl reload apache2` (это `apachectl graceful`: текущие запросы дорабатывают, новые идут в процессы с новой конфигурацией). `apache2ctl graceful/restart` сами прогоняют `-t` и при синтаксической ошибке не перезапускают сервер **[Debian, Apache-док]**.
8. **Полный перезапуск (`systemctl restart`) обрывает запросы** (для 1С — прерванные длительные операции). Он нужен при смене MPM и модулей, изменении `ServerLimit`/`ThreadLimit`, конфликтном изменении `Listen` **[Apache-док, Debian]**.
9. **Юнит `apache2.service`:** 22.04/24.04 — `Type=forking`, из ограничений только `PrivateTmp=true`; **26.04** — `Type=notify` и около 25 директив «закалки» (`MemoryDenyWriteExecute=yes`, `ProtectHome=read-only`, …), которые могут сломать модуль 1С — drop-in в `../1c/05` §6.1 **[Debian]**.
10. **Несколько экземпляров Apache на одной ВМ:** `sudo sh /usr/share/doc/apache2/examples/setup-instance <имя>` → `/etc/apache2-<имя>`, служба `apache2@<имя>`, команды `a2enmod-<имя>`, `apache2ctl-<имя>`. 1С требует **отдельный экземпляр Apache на каждую версию платформы** на одном компьютере (публикация — только вручную) **[Debian, ИТС-адм разд. 8.2]**.
11. **MPM:** по умолчанию `event`. 1С для Linux официально рекомендует **`worker`**, остальные — «не рекомендуются» **[ИТС-адм разд. 8.2, 8.10.1.1]**. `prefork` ставится сам вместе с `libapache2-mod-php*` (пакет переключает MPM) — это расходится с рекомендацией 1С; PHP на сервере с публикацией 1С — только через `php-fpm` **[Debian]**.
12. **Загружен может быть ровно один MPM:** два — `AH00534: apache2: Configuration error: More than one MPM loaded.`; ни одного — `… No MPM loaded.` Переключение: `sudo a2dismod mpm_event && sudo a2enmod mpm_worker && sudo apache2ctl configtest && sudo systemctl restart apache2` **[Apache-док, Apache-код, Debian]**.
13. **Порядок применения секций:** `<Directory>` + `.htaccess` → `<DirectoryMatch>` → `<Files>` → `<Location>` → `<If>`; секции внутри `<VirtualHost>` — после глобальных. Доступ к файлам ограничивают `<Directory>`, а не `<Location>` **[Apache-док]**.
14. **`.htaccess` в Ubuntu не читается** (`AllowOverride None` для `/` и `/var/www/`; умолчание Apache с 2.3.9) **[Debian, Apache-док]**.
15. **AH00558 «Could not reliably determine the server's fully qualified domain name»** — предупреждение, не ошибка: Apache не смог получить FQDN по обратному разрешению имени хоста. Лечится глобальным `ServerName` (`/etc/apache2/conf-available/local-servername.conf` + `a2enconf`) или записью FQDN в `/etc/hosts` **[Apache-код, Debian]**.
16. **Выбор виртуального хоста — в две фазы:** по IP:порту соединения (точный IP важнее `*`), затем по `Host`/SNI среди хостов того же уровня; имя не совпало — **первый** хост этого IP:порта. Смесь `<VirtualHost 10.x.x.x:80>` и `<VirtualHost *:80>` — частая причина «открывается не тот сайт» **[Apache-док]**.
17. **Всё, что задано вне `<VirtualHost>`, наследуют все виртуальные хосты** — в том числе `Alias` и `<Directory>` публикаций 1С, которые `webinst` дописывает в конец `apache2.conf`: публикация доступна по IP-адресу и по любому имени сервера, если хост сам не перехватывает этот путь (например, `ProxyPass /`) **[Apache-код `mod_alias.c`, `mod_proxy.c`, Apache-док]**.
18. **`StrictHostCheck On`** (2.4.49+) в основном сервере или хосте по умолчанию отвечает `400` на запросы с незнакомым именем — простой способ не отдавать публикацию по IP и чужим именам **[Apache-док]**.
19. **Процессы:** родитель — root (порты, журналы, ключи TLS), обработчики — `www-data`. Журналы — `/var/log/apache2/*.log`, `root:adm 0640`, ротация ежедневно, 14 архивов **[Debian]**.
20. **AppArmor-профиля для Apache в Ubuntu по умолчанию нет** — только с пакетом `libapache2-mod-apparmor` **[Ubuntu]**. Профили ufw: `Apache` (80), `Apache Secure` (443), `Apache Full` (80, 443) **[Ubuntu]** (доработка Ubuntu, LP 261198; в Debian вошла только в 2.4.60-1 — журнал Ubuntu `2.4.66-2ubuntu1`, раздел Dropped).
21. **Таймауты в Ubuntu:** `Timeout 300` (у Apache по умолчанию 60), `KeepAliveTimeout 5`, `MaxKeepAliveRequests 100`; подбор — `03-…` **[Debian, Apache-док]**.
22. **Размер тела запроса:** с 2.4.54 `LimitRequestBody` по умолчанию 1 ГиБ (было 0 — без ограничения): на 24.04/26.04 загрузка больше 1 ГиБ через публикацию получит `413`; на 22.04 (2.4.52) изменение, судя по журналу пакета, не переносилось ⚠ **[Apache-док, Apache-CL]**.

## 1. Версии Apache и поддержка

### 1.1. Ветка 2.4 и последние выпуски

- Стабильная ветка одна — **2.4.x**. Ветка 2.2 закрыта (последний выпуск 2.2.34, июль 2017) **[Apache-CL]**. Ветка trunk (2.5) — разработческая; директивы с пометкой «2.5.1 and later» (например, `ListenTCPDeferAccept`) в 2.4 отсутствуют, даже если документация их показывает **[Apache-док]**.
- Отдельных «долгих» подветок внутри 2.4 нет: исправления, в том числе безопасности, проект выпускает новыми номерами 2.4.x, а дистрибутивы (Ubuntu, Debian, RHEL) переносят их в свои версии сами **[Apache-CL, практика]**.
- Для TLS 1.3 с OpenSSL 1.1.1 нужен Apache 2.4.43 и новее — во всех поддерживаемых Ubuntu это выполнено **[Apache-CL]**.

Даты выпусков (по странице уязвимостей 2.4) **[Apache-CL]**:

| Выпуск | Дата | Чем примечателен для администратора |
|---|---|---|
| 2.4.69 | 01.10.2026 | 20 CVE: `mod_rewrite` (CVE-2026-56154), `mod_http2` (CVE-2026-57941), `mod_ssl` — `SSLRequire` в `.htaccess` (CVE-2026-59797), `mod_dav`/`mod_dav_fs`, `mod_auth_digest`, `mod_proxy_uwsgi`, `mod_proxy_ftp`, `mod_proxy_html`, `mod_vhost_alias`, `mod_userdir`, `mod_session`, `mod_heartmonitor`, внутренние перенаправления в CGI (CVE-2026-42356), запись за границу в `ap_directory_walk()` (CVE-2026-59685, только Windows — пути с короткими именами 8.3), `mod_charset_lite`, `mod_xml2enc`. Прочее: у `mod_md` `MDServerStatus` теперь выключен по умолчанию; `mod_auth_digest` убрал поддержку RFC 2069 |
| 2.4.68, 2.4.67 | 08.06.2026, 04.05.2026 | исправления безопасности |
| 2.4.66 | 04.12.2025 | основа пакета Ubuntu 26.04 |
| 2.4.65 | 23.07.2025 | исправление ошибки 2.4.64: любое `RewriteCond expr` считалось истинным (CVE-2025-54090) |
| 2.4.64 | 10.07.2025 | основа Ubuntu 25.10 |
| 2.4.58 | 19.10.2023 | основа пакета Ubuntu 24.04 |
| 2.4.54 | 08.06.2022 | `LimitRequestBody` по умолчанию 1 ГиБ вместо 0 |
| 2.4.52 | 20.12.2021 | основа пакета Ubuntu 22.04 |

Появление директив, полезных при чтении чужих инструкций: `StrictHostCheck` — 2.4.49; `MergeSlashes` — 2.4.39; `<IfFile>`, `<IfDirective>`, `<IfSection>` — 2.4.34; `mod_systemd` — 2.4.42; `Protocols` (для HTTP/2) — 2.4.17 **[Apache-док]**. Всё это есть во всех поддерживаемых Ubuntu.

### 1.2. Пакет apache2 в Ubuntu 22.04 / 24.04 / 26.04

| Ubuntu | Кодовое имя | Версия в выпуске | Последняя (карман `-security`, 08.10.2026) | Стандартная поддержка выпуска |
|---|---|---|---|---|
| 22.04 LTS | jammy | 2.4.52-1ubuntu4 | 2.4.52-1ubuntu4.25 | до весны (мая) 2027 |
| 24.04 LTS | noble | 2.4.58-1ubuntu8 | 2.4.58-1ubuntu8.17 | до мая 2029 |
| 26.04 LTS | resolute | 2.4.66-2ubuntu2 | 2.4.66-2ubuntu2.6 | до апреля 2031 |
| 25.10 (не LTS) | questing | 2.4.64-1ubuntu3 | 2.4.64-1ubuntu3.5 | — |

Источники: packages.ubuntu.com, журналы изменений changelogs.ubuntu.com (версии и даты на 20.10.2026) **[Ubuntu]**; сроки поддержки — `../linux/04-pakety-apt.md`, `../linux/08-set-ssh-firewall.md`. В разрабатываемом следующем выпуске (кодовое имя `stonking`) — 2.4.68-1ubuntu4 **[Ubuntu]**.

- Пакет лежит в компоненте **main** (раздел `web`) — обновления безопасности от Canonical идут весь срок стандартной поддержки выпуска; после него — через ESM (Ubuntu Pro), см. `../linux/04-pakety-apt.md` **[Ubuntu]**.
- На packages.ubuntu.com в кармане `-updates` на 20.10.2026 показана версия на одну ступень старше, чем в `-security` (например, для noble `8.16` против `8.17`). `apt` берёт наибольшую версию из всех подключённых карманов — проверяйте фактическое состояние командой `apt policy apache2` **[Ubuntu, практика]**.
- **Деление на пакеты** (одинаково в трёх выпусках): `apache2` — скрипты, `/etc/apache2`, юниты, `a2*`; `apache2-bin` — `/usr/sbin/apache2` и модули в `/usr/lib/apache2/modules/`; `apache2-data` — общие файлы (страница по умолчанию, иконки, страницы ошибок); `apache2-utils` — утилиты; `apache2-doc` — руководство (необязательно) **[Ubuntu]**.

```bash
apt policy apache2                                  # установленная версия и из какого кармана пришла
apache2 -v                                          # Server version: Apache/2.4.58 (Ubuntu) — на 24.04
dpkg -l 'apache2*' | awk '/^ii/{print $2, $3}'      # все пакеты apache2-* и их версии
lsb_release -ds                                     # выпуск Ubuntu
```

### 1.3. Бэкпорты: как понять, закрыта ли уязвимость

Ubuntu сохраняет номер версии Apache на весь срок выпуска и вносит исправления патчами: в `apache2 -v` будет «2.4.58», даже если закрыто всё до 2.4.69. Признак исправления — запись в журнале изменений пакета **[Ubuntu]**.

Пример на 20.10.2026: выпуск 2.4.69 (01.10.2026) закрыл 20 CVE. Обновления Ubuntu от 05.10 (`4.24` / `8.16` / `2.5`) и 08.10.2026 (`4.25` / `8.17` / `2.6`) упоминают во всех трёх выпусках 12 из них: CVE-2026-93546, -79768, -73636, -73637, -63718, -63686, -63292, -63045, -59797, -58415, -57941, -56154 **[Ubuntu]**. Остальные 8 (CVE-2026-59685, -56449, -56153, -48005, -47360, -46729, -42528, -42356) в журналах не упомянуты. Уточнено 20.10.2026 по странице уязвимостей 2.4 (диапазоны «Affects»): CVE-2026-59685 касается только Windows, CVE-2026-56449 (`mod_proxy_html`) — только 2.4.68, CVE-2026-42356 (CGI) — 2.4.60–2.4.68, то есть по исходным версиям 22.04 и 24.04 не затронуты, а 26.04 (2.4.66) — затронута. ⚠ Статус остальных пяти (`mod_charset_lite` -56153, `mod_auth_digest` -48005, `mod_session` -47360, `mod_heartmonitor` -46729, `mod_dav` -42528) и -42356 для 26.04 смотрите в трекере `https://ubuntu.com/security/CVE-<номер>` (на 20.10.2026 он не ответил: 504 / обрыв соединения).

```bash
zgrep -n 'CVE-2026-56154' /usr/share/doc/apache2/changelog.Debian.gz   # есть ли исправление в установленном пакете
apt changelog apache2 | head -60                                        # журнал пакета из репозитория
```

Практика:

- Сканеры, сравнивающие «2.4.58 < 2.4.69», дают ложные срабатывания — отвечайте выдержкой из `changelog.Debian.gz`.
- Обновляйте Apache из репозитория Ubuntu; сторонние PPA и самосборка на сервере 1С не рекомендуются (⚠ сторонние репозитории здесь не проверялись).
- Обновление пакета перезапускает службу полностью (restart, а не reload): уточнено 20.10.2026 по журналу Debian — запись 2.4.4-2 «Restart the server on upgrades» (новый двоичный файл должен заново загрузить модули) **[Debian]**; ⚠ на сервере не проверялось. На Ubuntu Server по умолчанию работают автоматические обновления безопасности (`unattended-upgrades`), поэтому Apache может перезапуститься сам в рабочее время — для сервера публикации 1С назначьте окно обновлений или ставьте `apache2` вручную (`../linux/04-pakety-apt.md`).

### 1.4. Что поменялось между выпусками Ubuntu

| Что | 22.04 (2.4.52) | 24.04 (2.4.58) | 26.04 (2.4.66) |
|---|---|---|---|
| Тип юнита `apache2.service` | `Type=forking` | `Type=forking` | `Type=notify` (через `mod_systemd`) |
| Ограничения юнита | только `PrivateTmp=true` | только `PrivateTmp=true` | `PrivateTmp=true` и около 25 директив «закалки» (раздел 3.1) |
| `OOMPolicy=continue` | нет | есть (добавлено в Debian 2.4.54-5) | есть |
| `Restart=` | `on-abort` | `on-abort` | `on-abnormal` |
| Сигнал остановки | по умолчанию (`SIGTERM`) | по умолчанию | `KillSignal=SIGWINCH` (мягкая остановка) |
| `apache2ctl stop/restart/graceful`, вызванные вручную | шлют сигнал процессу сами | шлют сигнал сами | вызывают `systemctl stop/restart/reload` |
| Каталоги PID и блокировок (`envvars`) | `/var/run/apache2`, `/var/lock/apache2` | то же | `/run/apache2`, `/run/lock/apache2` |
| `LANG` в `envvars` | `C` | `C` | `C.UTF-8` |
| Псевдоним службы | — | — | `httpd.service`, `httpd@.service` |
| Профили ufw | есть | есть | есть |
| `LimitRequestBody` по умолчанию | 0 (без ограничения) ⚠ | 1 ГиБ | 1 ГиБ |
| TLS 1.0/1.1 в `ssl.conf` по умолчанию | см. `02-…` | см. `02-…` | выключены (Debian 2.4.64-2, «per RFC 8996») |

Источники: юниты и `envvars` — метки `debian/2.4.52-1`, `debian/2.4.58-1`, `debian/2.4.66-2` **[Debian]**; журнал изменений пакета (записи 2.4.54-5, 2.4.64-2, 2.4.65-3, 2.4.66-1) **[Debian]**; списки файлов пакетов **[Ubuntu]**. ⚠ Юнит самого пакета Ubuntu 26.04 не читался (исходники Launchpad с этой машины недоступны): вывод сделан по метке Debian `2.4.66-2` и по разделу «Remaining changes» журнала Ubuntu `2.4.66-2ubuntu1`, где изменений юнита нет. Перепроверено рецензентом 20.10.2026: юнит Debian `2.4.66-2` прочитан, в записях Ubuntu `2.4.66-2ubuntu1` … `2ubuntu2.6` юнит не меняется, а `apache2-bin` 26.04 (в отличие от 24.04) зависит от `libsystemd0` — это согласуется с `Type=notify`. На сервере проверьте: `systemctl cat apache2`.

Что означает таблица для 1С:

- Переход 24.04 → 26.04 меняет **не** Apache-конфигурацию публикации, а окружение процесса: ограничения systemd могут не дать модулю `wsap24.so` работать (`MemoryDenyWriteExecute=yes`), а файловой базе или keytab в `/home` — открываться (`ProtectHome=read-only`). Drop-in и разбор — `../1c/05` §6.1 **[Debian, практика]**.
- Выпуск 26.04 на 20.10.2026 отсутствует в списке ОС, поддерживаемых 1С (`../1c/05`) — рабочий сервер 1С держите на 22.04/24.04, пока 1С не объявит поддержку.

### 1.5. Apache на Windows — коротко

Проект Apache выпускает для Windows только исходный код; готовые сборки делают сторонние проекты, документация называет Apache Lounge и WampServer **[Apache-док `platform/windows`]**. На Windows работает единственный MPM — `mpm_winnt` (один процесс с потоками, `ThreadsPerChild`), конфигурация — в `conf\httpd.conf` каталога установки, служба регистрируется `httpd.exe -k install` **[Apache-док]**. Для 1С на Apache 2.2 под Windows с файловой базой руководство советует `ThreadStackSize 8388608` в `<IfModule mpm_winnt_module>` **[ИТС-адм разд. 8.10.1.1]**. Подробности — `04-…` и `../1c-windows/03-veb-publikaciya-iis.md`, раздел 13.

## 2. Установка и состав пакетов

### 2.1. Установка

```bash
sudo apt update
sudo apt install -y apache2              # тянет apache2-bin, apache2-data, apache2-utils; рекомендует ssl-cert
systemctl status apache2 --no-pager      # active (running)
apache2 -v                               # Server version: Apache/2.4.xx (Ubuntu)
sudo apache2ctl -V | grep -i 'server mpm'   # Server MPM:     event
ss -ltnp | grep -E ':(80|443)\s'         # слушает *:80 (443 — только после a2enmod ssl)
curl -sI http://localhost/ | head -3     # HTTP/1.1 200 OK, Server: Apache/2.4.xx (Ubuntu)
```

Пакеты-зависимости и рекомендации на примере 24.04 **[Ubuntu]**: `apache2` зависит от `apache2-bin`, `apache2-data`, `apache2-utils` той же версии, а также `init-system-helpers`, `media-types`, `perl`, `procps`; рекомендует `ssl-cert` (самоподписанный сертификат «snakeoil» для проверки HTTPS); предлагает `apache2-doc`, `apache2-suexec-pristine | apache2-suexec-custom`, `ufw`, `www-browser`. `apache2-bin` тянет библиотеки APR и APR-util (один из драйверов БД — первым указан SQLite3 — и LDAP), `libbrotli1`, `libcurl4t64` и др.

Где брать: только из репозитория Ubuntu. Дистрибутив 1С ставит лишь модуль `wsap24.so` и утилиту `webinst` (компонент `ws`, `../1c/05` §3.4); сам Apache 1С не поставляет **[ИТС-адм разд. 8.1]** (руководство отсылает за дистрибутивом на httpd.apache.org/download, но на Ubuntu это означает пакет `apache2`) **[практика]**.

### 2.2. Что делает установка (сценарий postinst)

При **первой** установке (не при обновлении) сценарий `apache2.postinst` **[Debian]**:

1. включает MPM `event` (`a2enmod -m -q mpm_event`);
2. копирует страницу по умолчанию в `/var/www/html/index.html`, если в `/var/www` и `/var/www/html` нет своего `index.*`;
3. включает модули `authz_host auth_basic access_compat authn_file authz_user alias dir autoindex env mime negotiation setenvif filter deflate status reqtimeout`;
4. включает фрагменты `charset localized-error-pages other-vhosts-access-log security serve-cgi-bin`;
5. включает сайт `000-default` и создаёт `/var/log/apache2/error.log`, `access.log`, `other_vhosts_access.log` с владельцем `root:adm` и правами `0640`;
6. выполняет «отложенные действия» пакетов-модулей из `/var/lib/apache2/deferred_actions` (включение модулей, смена MPM) — этот шаг выполняется при каждой настройке пакета, в том числе при обновлении.

Служба `apache-htcacheclean` (очистка дискового кэша) при установке отключается, если не включён `cache_disk` **[Debian]**.

Следствие для администратора: на чистой ВМ включены `autoindex` (листинг каталогов), `status` (страница `/server-status` для локальных запросов), `access_compat` (старые `Order/Allow/Deny`) и `negotiation` — что из этого выключать, разобрано в `02-…`. Модули `alias auth_basic authn_file authz_host authz_user autoindex deflate dir env filter mime negotiation setenvif` (а также встроенные `logio unixd version watchdog`) утилита `a2dismod` считает **существенными** и без ключа `-f` требует ввести подтверждение (раздел 5) **[Debian]**.

### 2.3. Состав файлов

- **`apache2-bin`:** `/usr/sbin/apache2` (в других дистрибутивах — `httpd`) и 118 модулей `/usr/lib/apache2/modules/mod_*.so`, в том числе три MPM (`mod_mpm_event.so`, `mod_mpm_worker.so`, `mod_mpm_prefork.so`), `mod_ssl`, `mod_http2`, `mod_md`, `mod_proxy*`, `mod_brotli`, `mod_lua`. Встроены в сам `apache2` (файлов `.so` у них нет): `core`, `mod_so`, `http_core`, `mod_log_config`, `mod_logio`, `mod_unixd`, `mod_version`, `mod_watchdog`; в 26.04 ещё `mod_systemd` (уточнено 20.10.2026: `debian/rules` 2.4.66-2 собирает его статически при наличии `libsystemd-dev`; в списке файлов `apache2-bin` 26.04 нет `mod_systemd.so`, а сам пакет зависит от `libsystemd0`, — значит, модуль встроен). Список встроенных: `apache2ctl -l` **[Ubuntu, Debian `debian/rules`]**.
- **`apache2`:** `/usr/sbin/apache2ctl` (ссылка `apachectl`), `a2enmod` (ссылки `a2dismod`, `a2ensite`, `a2dissite`, `a2enconf`, `a2disconf`), `a2query`; каталог `/etc/apache2/`; юниты `apache2.service`, `apache2@.service`, `apache-htcacheclean.service`, `apache-htcacheclean@.service` в `/usr/lib/systemd/system` (в 22.04 — `/lib/systemd/system`); сценарии `/etc/init.d/`; `/etc/logrotate.d/apache2`, `/etc/cron.daily/apache2`; профиль ufw `/etc/ufw/applications.d/apache2-utils.ufw.profile`; документация `/usr/share/doc/apache2/README.Debian.gz`, `README.multiple-instances`, `examples/setup-instance`; `/usr/share/apache2/ask-for-passphrase` (запрос пароля к ключу TLS при старте) **[Ubuntu, Debian `apache2.links`]**.
- **`apache2-utils`:** `ab`, `htpasswd`, `htdigest`, `htdbm`, `htcacheclean`, `rotatelogs`, `logresolve`, `checkgid`, `fcgistarter`, `httxt2dbm`, `split-logfile`, `check_forensic` **[Ubuntu]**.

### 2.4. Модули из других пакетов

Часть модулей поставляется отдельными пакетами `libapache2-mod-*`; при установке они сами включают свой модуль (через вспомогательный сценарий `apache2-maintscript-helper`) **[Debian, Ubuntu]**.

Примеры (версии 22.04 / 24.04 / 26.04 на 20.10.2026) **[Ubuntu]**: `libapache2-mod-auth-gssapi` 1.6.3 / 1.6.4 / 1.6.4 — Kerberos/SPNEGO, вход в публикацию 1С по доменной учётной записи (`02-…`); `libapache2-mod-auth-openidc` 2.4.11 / 2.4.15.1 / 2.4.18.1 — OpenID Connect; `libapache2-mod-security2` 2.9.5 / 2.9.7 / 2.9.12 — WAF ModSecurity; `libapache2-mod-wsgi-py3` 4.9.0 / 5.0.0 / 5.0.2; `libapache2-mod-php` (PHP 8.1 / 8.3 / 8.5) — **переключает MPM на `prefork`** (раздел 8.3); `libapache2-mod-apparmor` — профиль AppArmor (раздел 13).

Модуль 1С (`wsap24.so`) в пакеты Ubuntu не входит: его ставит дистрибутив платформы в `/opt/1cv8/x86_64/<версия>/`, а подключает строка `LoadModule`, которую пишет `webinst` (раздел 9.2, `../1c/05` §4.3).

Сервисы пользователя (Redmine, NetBox, GlitchTip, Grafana) модулей внутри Apache не требуют: Apache для них — обратный прокси (`mod_proxy`, `mod_proxy_http`, `mod_headers`, при необходимости `mod_proxy_wstunnel`), см. `03-…`, `../redmine/02-…`, `../netbox/02-…`.

### 2.5. Проверка после установки

```bash
systemctl is-enabled apache2 && systemctl is-active apache2     # enabled / active
sudo apache2ctl configtest                                       # Syntax OK
sudo apache2ctl -S                                               # виртуальные хосты и пути (раздел 6.2)
sudo apache2ctl -M | sort                                        # загруженные модули: (static) и (shared)
a2query -M                                                       # event
curl -sI http://127.0.0.1/ | head -1                             # HTTP/1.1 200 OK
sudo tail -n 20 /var/log/apache2/error.log                       # нет ли ошибок и AH00558
sudo journalctl -u apache2 -b --no-pager | tail -n 20            # сообщения запуска
```

### 2.6. Удаление и переустановка — осторожно

- `sudo apt remove apache2` оставляет `/etc/apache2`; `sudo apt purge apache2` удаляет конфигурационные файлы пакета, включая **`apache2.conf`**, куда `webinst` дописывает модуль 1С и публикации. Перед `purge` сохраните каталог: `sudo tar -C /etc -czf /root/apache2-etc-$(date +%F).tgz apache2` **[практика]**. ⚠ Что именно удаляет `purge` из файлов, изменённых вами, на сервере не проверялось.
- Каталоги экземпляров `/etc/apache2-<имя>` пакет не трогает: удаляются только файлы конфигурации по умолчанию **[Debian `README.multiple-instances`]**.
- Если удалили файл из `/etc/apache2` и хотите вернуть исходный: `sudo apt install --reinstall -o Dpkg::Options::="--force-confmiss" apache2` — ⚠ на сервере не проверялось (стандартный механизм dpkg).

## 3. Служба systemd

### 3.1. Юнит apache2.service по выпускам

Общее для всех выпусков **[Debian]**: `ExecStart=/usr/sbin/apachectl start`, `ExecStop=/usr/sbin/apachectl graceful-stop`, `ExecReload=/usr/sbin/apachectl graceful`, `KillMode=mixed`, `PrivateTmp=true` (у Apache свои `/tmp` и `/var/tmp`), `Environment=APACHE_STARTED_BY_SYSTEMD=true`, `After=network.target remote-fs.target nss-lookup.target`, `WantedBy=multi-user.target`.

| | 22.04 | 24.04 | 26.04 |
|---|---|---|---|
| `Type` | `forking` | `forking` | `notify` |
| `Restart` | `on-abort` | `on-abort` | `on-abnormal` |
| `OOMPolicy` | — | `continue` | `continue` |
| `KillSignal` | — | — | `SIGWINCH` |
| ограничения | — | — | `RemoveIPC`, `DevicePolicy=closed`, `KeyringMode=private`, `LockPersonality`, `MemoryDenyWriteExecute`, `PrivateDevices`, `ProtectClock`, `ProtectControlGroups`, `ProtectHome=read-only`, `ProtectHostname`, `ProtectKernelLogs/Modules/Tunables`, `ProtectSystem=full`, `RestrictNamespaces`, `RestrictRealtime`, `RestrictSUIDSGID`, `SystemCallArchitectures=native`, `ProtectProc=invisible`, `ProcSubset=pid`; `ReadWritePaths=/var/log/apache2` и `/var/cache/apache2/mod_cache_disk`; `InaccessiblePaths=/boot`, `/root`, `-/etc/sudoers`, `-/etc/sudoers.d`, `-/etc/ssh`, `-/etc/apt`, `-/etc/.git`, `-/etc/.svn` |

Что из ограничений 26.04 мешает 1С и как это снимать — `../1c/05` §6.1 (не дублируем). Для сервисов за Apache (`srv-itsm`, `srv-obs`) ограничения обычно не мешают: Apache там только проксирует **[практика]**. `ProtectSystem=full` делает доступными только для чтения `/usr`, `/boot`, `/efi` и `/etc`, поэтому запись в `/srv` и `/var` (например, журналы в `/srv/logs`) по-прежнему решают обычные права; писать в `/etc` или под `/home` служба не сможет без drop-in, а `/root` и `/boot` закрыты совсем (`InaccessiblePaths`) **[Debian, `../1c/05` §6.1]**.

На 26.04 с `Type=notify` и `mod_systemd` команда `systemctl status apache2` показывает строку состояния с числом обработанных запросов; `mod_systemd` включает `ExtendedStatus` по умолчанию **[Apache-док `mod_systemd`]**.

```bash
systemctl cat apache2                     # фактический юнит и все drop-in
systemctl show apache2 -p Type -p Restart -p KillSignal -p PrivateTmp -p MemoryDenyWriteExecute -p ProtectHome
systemd-analyze security apache2 --no-pager | tail -n 5   # оценка «закалки» юнита (systemd ≥ 240) [практика]
```

### 3.2. systemctl и apache2ctl: чем что делать

| Задача | Команда | Что происходит |
|---|---|---|
| Запустить / включить в автозапуск | `sudo systemctl enable --now apache2` | `apachectl start`; при запуске из-под systemd — `apache2 -k start` (на 26.04 — с `-DFOREGROUND`) **[Debian]** |
| Перечитать конфигурацию без обрыва | `sudo systemctl reload apache2` | `apachectl graceful`: проверка `apache2 -t`, затем `SIGUSR1` родителю (раздел 3.3) |
| Полный перезапуск | `sudo systemctl restart apache2` | остановка и запуск заново: все соединения рвутся, сбрасываются статистика и разделяемая память |
| Остановить | `sudo systemctl stop apache2` | `apachectl graceful-stop` (`SIGWINCH`), затем сигнал остановки от systemd (раздел 3.3) |
| Состояние | `systemctl status apache2 --no-pager`; `sudo journalctl -u apache2 -b` | |
| Только проверка синтаксиса | `sudo apache2ctl configtest` (то же `sudo apache2ctl -t`) | ничего не перезапускает |

Правило: **службой управляйте через `systemctl`**, `apache2ctl` используйте для проверок (`-t`, `-S`, `-M`, `-V`) **[практика]**. Почему **[Debian `apache2ctl`]**:

- в 22.04/24.04 `apache2ctl start` вне systemd сам вызывает `systemctl start apache2` (иначе systemd «не знает» о процессе), а `apache2ctl stop`, `restart`, `graceful` шлют сигнал процессу напрямую — systemd узнаёт об этом задним числом;
- в 26.04 (Debian 2.4.66-1: «Fix the restart and graceful when using systemd») `apache2ctl stop/restart/graceful`, вызванные вручную, тоже перенаправляются в `systemctl stop/restart/reload`;
- `apache2ctl status` и `fullstatus` требуют текстовый браузер (`www-browser`, например `lynx`) и включённый `mod_status`; адрес страницы задаётся `APACHE_STATUSURL` (по умолчанию `http://localhost:80/server-status`) — удобнее `curl -s 'http://localhost/server-status?auto'` (см. `03-…`).

Коды возврата `apache2ctl`: 0 — успех, иначе ошибка, при ошибке печатается `Action '…' failed.` и совет смотреть журнал ошибок **[Debian]**. Сообщения, которые Apache выдаёт до открытия своего журнала (синтаксические ошибки, AH00558), уходят в stderr — при запуске службой их видно в `journalctl -u apache2` **[практика]**.

### 3.3. Перезагрузка без обрыва: graceful, restart, graceful-stop

Сигналы родительскому процессу (PID — в `/run/apache2/apache2.pid`, в 22.04/24.04 путь записан как `/var/run/apache2/apache2.pid`) **[Apache-док `stopping`]**:

| Действие | Сигнал | Команда | Текущие запросы |
|---|---|---|---|
| Мягкий перезапуск | `USR1` | `systemctl reload` (= `apachectl graceful`) | дорабатывают в старых процессах; новые процессы работают с новой конфигурацией; статистика `mod_status` сохраняется, старые процессы помечены `G` |
| Перезапуск | `HUP` | `apachectl restart` | обрываются; родитель перечитывает конфигурацию и запускает новые процессы; статистика обнуляется |
| Мягкая остановка | `WINCH` | `apachectl graceful-stop` | дорабатывают; порты закрываются сразу; ожидание — до `GracefulShutdownTimeout` (по умолчанию 0 — без предела), затем `TERM` |
| Остановка | `TERM` | `apachectl stop` | обрываются |

Перед `graceful` и `restart` Apache проверяет синтаксис и при ошибке продолжает работать со старой конфигурацией; занятый порт или отсутствующий файл сертификата эта проверка не ловит **[Apache-док]**.

Только остановкой и запуском (`systemctl restart`) применяются **[Apache-док]**: изменения `ServerLimit` и `ThreadLimit` (при любом перезапуске игнорируются) и изменения `Listen`, конфликтующие со старыми на том же порту (пример документации: `Listen 127.0.0.1:80` → `Listen 80`; при перезапуске старые сокеты остаются открытыми, пока не откроются новые, поэтому привязка не удаётся и сервер завершится с ошибкой; обратная замена на Linux конфликтует так же — вывод по коду `listen.c` ⚠). Переход на другой порт (`Listen 80` → `Listen 8081`) не конфликтует: новый сокет открывается, старый закрывается **[Apache-док `bind`, Apache-код `listen.c`]**. Смену MPM и модулей тоже делайте `restart` — так советует `a2enmod` **[Debian]**.

Для 1С **[практика]**: `reload` пользователи веб-клиента не замечают; `restart` обрывает текущие вызовы веб-клиента и интеграций (HTTP-сервисы, OData) — только в окно обслуживания. Документация 1С после смены версии платформы, пути к модулю, новой публикации и отключения публикации требует перезапуска веб-сервера (`../1c/05` §4.6); достаточно ли в этих случаях `reload` — ⚠ не проверялось, при смене модуля (версии) делайте `restart`. Старые процессы при `graceful` живут, пока идут их длинные запросы; для файловой базы это означает два экземпляра модуля на одну базу ⚠ — меняйте её конфигурацию в окно.

Остановка через systemd **[Apache-док `mod_systemd`, Debian]**: документация `mod_systemd` требует, чтобы `ExecStop` ждал завершения сервера, а `apachectl graceful-stop` лишь посылает `WINCH` и возвращается. В 22.04/24.04 после этого systemd по `KillMode=mixed` шлёт основному процессу `SIGTERM`, а `TERM` в состоянии graceful немедленно завершает родителя и детей: `systemctl stop` там фактически не ждёт запросов (подтверждено 20.10.2026 по документации — `systemd.service(5)`: после `ExecStop` оставшиеся процессы завершаются по `KillMode`; `systemd.kill(5)`: при `mixed` основному процессу идёт `SIGTERM`; Apache `stopping`: `TERM` в состоянии graceful завершает всё сразу; ⚠ на сервере не проверялось). В 26.04 задан `KillSignal=SIGWINCH` — остановка мягкая; через `TimeoutStopSec` оставшиеся процессы получат `SIGKILL` (уточнено 20.10.2026: умолчание — `DefaultTimeoutStopSec`, при сборке systemd `default-timeout-sec = 90`, то есть 90 с; фактическое значение — `systemctl show apache2 -p TimeoutStopUSec`). Чтобы один зависший запрос не держал остановку до этого предела, задайте `GracefulShutdownTimeout` (раздел 3.4) **[практика]**.

### 3.4. Переопределение юнита (drop-in)

Юнит пакета не правят — изменения кладут в drop-in, который переживает обновления (`../linux/05-…`) **[практика]**:

```bash
sudo systemctl edit apache2          # /etc/systemd/system/apache2.service.d/override.conf
```

```ini
[Service]
# перезапускать и при обычной аварии (по умолчанию — только при аварийном завершении по сигналу)
Restart=on-failure
RestartSec=5s
# общая файловая база 1С: файлы модуля доступны группе (../1c/05 §6)
#UMask=0002
# 26.04: ограничение, мешающее модулю 1С (../1c/05 §6.1)
#MemoryDenyWriteExecute=no
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart apache2     # drop-in действует после перезапуска службы
systemctl show apache2 -p Restart -p UMask -p MemoryDenyWriteExecute
sudo systemctl revert apache2                                       # убрать все drop-in
```

**Лимит открытых файлов** **[Debian]**: `apache2ctl` при запуске от root выполняет `ulimit -n 8192` (переменная `APACHE_ULIMIT_MAX_FILES`), и это перекрывает `LimitNOFILE` юнита. Для многих соединений (обратный прокси, тысячи keep-alive) поднимайте лимит в `envvars`:

```bash
echo "APACHE_ULIMIT_MAX_FILES='ulimit -n 65536'" | sudo tee -a /etc/apache2/envvars
sudo systemctl restart apache2
grep 'open files' /proc/$(pgrep -o apache2)/limits
```

`ulimit -n` без `-H`/`-S` в `/bin/sh` Ubuntu (dash) ставит и мягкий, и жёсткий предел — уточнено 20.10.2026 по man `dash(1)` (noble): «If neither -H nor -S is specified … both limits are set». В контейнере, где лимит менять нельзя («Setting ulimit failed»), — `APACHE_ULIMIT_MAX_FILES=true` (`README.Debian`).

**Таймаут мягкой остановки** задаётся директивой Apache (`GracefulShutdownTimeout`, server config, по умолчанию 0 — ждать бесконечно) **[Apache-док `mpm_common`]**:

```bash
echo 'GracefulShutdownTimeout 30' | sudo tee /etc/apache2/conf-available/local-graceful.conf
sudo a2enconf local-graceful && sudo apache2ctl configtest && sudo systemctl reload apache2
```

### 3.5. Несколько экземпляров Apache: apache2@ и setup-instance

Когда нужно: **разные версии платформы 1С на одной ВМ** (например, 8.3.27 и 8.5.1 в переходный период) — руководство требует отдельный экземпляр веб-сервера на каждую версию и публикацию в нём только вручную **[ИТС-адм разд. 8.2]**; изоляция публикации от посторонних сайтов (свой MPM, свои ограничения); проверка новой конфигурации на другом порту **[практика]**.

Механизм **[Debian `README.multiple-instances`, `setup-instance`, `apache2@.service`]**: экземпляр — копия `/etc/apache2` в `/etc/apache2-<имя>`; служба — шаблон `apache2@<имя>` (переменная `APACHE_CONFDIR=/etc/apache2-<имя>`, запуск только при наличии каталога); `envvars` по суффиксу сам выбирает `/run/apache2-<имя>`, `/run/lock/apache2-<имя>` (в 22.04/24.04 — `/var/run/…`, `/var/lock/…`) и `/var/log/apache2-<имя>`; сценарий `setup-instance` создаёт ссылки `a2enmod-<имя>`, `a2ensite-<имя>`, `apache2ctl-<имя>` и т. д. в `/usr/local/sbin`, файл `/etc/logrotate.d/apache2-<имя>`, каталог журналов (`750`, `root:adm`) и `/etc/default/apache-htcacheclean-<имя>`.

Пример — второй экземпляр на порту 8081:

```bash
sudo sh /usr/share/doc/apache2/examples/setup-instance v851        # суффикс — латиница и цифры, без пробелов
sudo sed -i 's/^Listen 80$/Listen 8081/' /etc/apache2-v851/ports.conf
sudo sed -i 's/<VirtualHost \*:80>/<VirtualHost *:8081>/' /etc/apache2-v851/sites-available/000-default.conf
#   Listen 443 внутри <IfModule ssl_module> копии тоже смените — или выключите ssl: sudo a2dismod-v851 ssl
sudo a2dismod-v851 mpm_event && sudo a2enmod-v851 mpm_worker
sudo apache2ctl-v851 configtest                                     # Syntax OK
sudo systemctl enable --now apache2@v851
systemctl status apache2@v851 --no-pager; ss -ltnp | grep ':8081'
```

Особенности:

- `webinst` ищет конфигурацию Apache 2.4 только в `/etc/apache2/` **[ИТС-адм разд. 8.10.1.2.3]**: для экземпляра указывайте `-confpath /etc/apache2-v851/apache2.conf` (⚠ не проверялось) или публикуйте вручную; `LoadModule _1cws_module` экземпляра — на `wsap24.so` своей версии платформы (раздел 9.2).
- Изменения пакета в `/etc/apache2` в копию не попадают; `README.multiple-instances` советует ставить в копии ссылки на файлы `/etc/apache2` и держать `/etc` под контролем версий (`etckeeper`). Для `apache2ctl-v851 status` задайте `APACHE_STATUSURL` в `/etc/apache2-v851/envvars` **[Debian]**.
- В 26.04 у `apache2@.service` те же ограничения, что у основного юнита (`ReadWritePaths=/var/log/apache2-%i`); drop-in — `sudo systemctl edit apache2@v851` **[Debian]**.
- Удаление: `sudo systemctl disable --now apache2@v851`; **после копии** (`sudo tar -czf /root/apache2-v851-$(date +%F).tgz /etc/apache2-v851`) убрать `/etc/apache2-v851`, `/var/log/apache2-v851`, `/etc/logrotate.d/apache2-v851`, `/etc/default/apache-htcacheclean-v851` и ссылки `/usr/local/sbin/*-v851`.

### 3.6. Служба apache-htcacheclean

Нужна только при дисковом кэше (`mod_cache_disk`): ограничивает размер `/var/cache/apache2/mod_cache_disk`. Параметры — `/etc/default/apache-htcacheclean`; режим — демон или ежедневный запуск из `/etc/cron.daily/apache2`; при `a2enmod cache_disk` утилита сама включает службу, при `a2dismod` — выключает **[Debian `README.Debian`, `a2enmod`]**. Для публикации 1С дисковый кэш Apache не используется **[практика]**.

## 4. Раскладка конфигурации Debian/Ubuntu

### 4.1. Дерево /etc/apache2 и порядок включения

Раскладка Debian сильно отличается от исходной (`httpd.conf` в каталоге `conf/` у сборки с httpd.apache.org); её цель — чтобы модули, глобальные фрагменты и сайты включались и выключались отдельными файлами и это можно было автоматизировать **[Debian `README.Debian`]**.

```
/etc/apache2/
├── apache2.conf        главный файл: глобальные директивы и подключение остальных частей
├── envvars             переменные окружения для apache2ctl (пользователь, каталоги, LANG, ulimit)
├── magic               сигнатуры для mod_mime_magic (формат не совместим с file/libmagic)
├── ports.conf          директивы Listen
├── mods-available/     *.load (строка LoadModule) и *.conf (настройки модуля) — все установленные модули
├── mods-enabled/       ссылки на включённые *.load и *.conf
├── conf-available/     глобальные фрагменты конфигурации
├── conf-enabled/       ссылки на включённые фрагменты
├── sites-available/    виртуальные хосты (из пакета — 000-default.conf и default-ssl.conf)
└── sites-enabled/      ссылки на включённые сайты
```

Порядок чтения `apache2.conf` (метки `debian/2.4.58-1` и `debian/2.4.66-2` совпадают) **[Debian]**:

1. Глобальные директивы: `DefaultRuntimeDir`, `PidFile`, `Timeout`, `KeepAlive*`, `User`/`Group`, `HostnameLookups`, `ErrorLog`, `LogLevel`.
2. `IncludeOptional mods-enabled/*.load`, затем `IncludeOptional mods-enabled/*.conf` — сначала загружаются **все** модули, потом их настройки.
3. `Include ports.conf`.
4. Секции `<Directory />`, `<Directory /usr/share>`, `<Directory /var/www/>`, `AccessFileName`, `<FilesMatch "^\.ht">`, форматы журналов `LogFormat`.
5. `IncludeOptional conf-enabled/*.conf`.
6. `IncludeOptional sites-enabled/*.conf`.
7. Всё, что дописано в конец файла позже (так делает `webinst`: `LoadModule _1cws_module` и блоки публикаций, `../1c/05` §4.3).

Внутри каталога файлы берутся **по алфавиту** (подстановка в `Include` раскрывается в алфавитном порядке) **[Apache-док `Include`]**. Отсюда:

- `000-default.conf` идёт первым среди сайтов и становится хостом по умолчанию для своего IP:порта (раздел 11.1) **[Debian]**;
- подключаются только файлы, оканчивающиеся на `.conf` (и `.load` для модулей); `site.conf.bak`, `site.conf.dpkg-old`, `site.conf~` игнорируются — а вот `site.bak.conf` будет прочитан **[Debian, Apache-док]**;
- фрагмент из `conf-enabled/` читается после модулей, но до сайтов, и попадает в основной сервер (значит, наследуется всеми хостами, раздел 11.5).

Фактический список прочитанных файлов в порядке чтения:

```bash
sudo apache2ctl -t -D DUMP_INCLUDES      # «Included configuration files:», дерево с отступами и номерами строк Include [Apache-код config.c]
```

### 4.2. apache2.conf: что в нём и что менять

| Директива в Ubuntu | Значение | Умолчание Apache | Заметки |
|---|---|---|---|
| `Mutex file:${APACHE_LOCK_DIR} default` | **закомментирована** на Linux | `Mutex default` | в Linux используются мьютексы pthread; строка нужна только на kfreebsd/hurd **[Debian `debian/rules`]** |
| `DefaultRuntimeDir` | `${APACHE_RUN_DIR}` | `logs/` относительно `ServerRoot` | разделяемая память и служебные файлы |
| `PidFile` | `${APACHE_PID_FILE}` | `logs/httpd.pid` | |
| `Timeout` | **300** | 60 | ожидание при приёме и отправке; для 1С и прокси — `03-…` |
| `KeepAlive` | `On` | `On` | |
| `MaxKeepAliveRequests` | 100 | 100 | |
| `KeepAliveTimeout` | 5 | 5 | |
| `User` / `Group` | `${APACHE_RUN_USER}` / `${APACHE_RUN_GROUP}` = `www-data` | `#-1` | модуль `mod_unixd` |
| `HostnameLookups` | `Off` | `Off` | не включать: DNS-запрос на каждый запрос |
| `ErrorLog` | `${APACHE_LOG_DIR}/error.log` | `logs/error_log` | |
| `LogLevel` | `warn` | `warn` | можно по модулям: `LogLevel warn ssl:info` |
| `<Directory />` | `Options FollowSymLinks`, `AllowOverride None`, `Require all denied` | — | вся файловая система закрыта |
| `<Directory /usr/share>` | `AllowOverride None`, `Require all granted` | — | веб-приложения из пакетов Debian |
| `<Directory /var/www/>` | `Options Indexes FollowSymLinks`, `AllowOverride None`, `Require all granted` | — | `Indexes` = листинг каталогов без `index.*` |
| `#<Directory /srv/>` | пример, закомментирован | — | раскомментировать или открыть нужный подкаталог, если сайт лежит в `/srv` |
| `AccessFileName` | `.htaccess` | `.htaccess` | |
| `<FilesMatch "^\.ht">` | `Require all denied` | — | не отдавать `.htaccess` и `.htpasswd` |
| `LogFormat` | `vhost_combined`, `combined`, `common`, `referer`, `agent` | — | вместо `%b` используется `%O` (байты с заголовками), чтобы видеть оборванные ответы; вместо `%{X-Forwarded-For}i` советуют `mod_remoteip` |

Источники: `apache2.conf.in` метки `debian/2.4.58-1` **[Debian]**; умолчания — документация `core`, `mpm_common`, `mod_unixd` **[Apache-док]**.

Как с ним обращаться:

- `README.Debian` прямо просит по возможности **не править `apache2.conf`**: в нём нет ничего, что «должно» настраиваться на месте, и он должен оставаться актуальным после обновлений. Свои глобальные настройки кладите в `conf-available/local-<что>.conf` (префикс `local-` — чтобы не совпасть по имени с файлами пакетов) и включайте `a2enconf` **[Debian]**.
- `apache2.conf` — конфигурационный файл пакета: если вы его изменили, а новая версия пакета принесёт свой, `dpkg` спросит, что оставить; автоматические обновления в такой ситуации могут пакет пропустить ⚠ поведение `unattended-upgrades` при вопросе о конфигурационном файле на сервере не проверялось **[практика]**.
- `webinst` по умолчанию пишет модуль 1С и публикации именно в конец `apache2.conf` **[ИТС-адм разд. 8.10.1.2.3, `../1c/05` §4.3]**. Это работает, но смешивает ваше с пакетным; аккуратнее держать публикации в `conf-available/1c-<имя>.conf` или внутри нужного виртуального хоста (раздел 4.9).

### 4.3. envvars

`/etc/apache2/envvars` — сценарий `sh`, который `apache2ctl` выполняет перед каждым действием; раз юнит запускает `apachectl start`, переменные и команды из него (`export`, `umask`, `ulimit`) действуют и при запуске через systemd **[Debian `apache2ctl`]**.

| Переменная | 22.04 / 24.04 | 26.04 | Назначение |
|---|---|---|---|
| `APACHE_RUN_USER`, `APACHE_RUN_GROUP` | `www-data` | `www-data` | пользователь и группа обработчиков |
| `APACHE_PID_FILE` | `/var/run/apache2$SUFFIX/apache2.pid` | `/run/apache2$SUFFIX/apache2.pid` | PID родителя |
| `APACHE_RUN_DIR` | `/var/run/apache2$SUFFIX` | `/run/apache2$SUFFIX` | `DefaultRuntimeDir`, сокеты `cgid` |
| `APACHE_LOCK_DIR` | `/var/lock/apache2$SUFFIX` | `/run/lock/apache2$SUFFIX` | блокировки |
| `APACHE_LOG_DIR` | `/var/log/apache2$SUFFIX` | то же | журналы (ротируется только `/var/log/apache2`) |
| `LANG` | `C` | `C.UTF-8` | локаль процесса; закомментированная строка `. /etc/default/locale` берёт системную |
| `APACHE_LYNX`, `APACHE_STATUSURL` | `APACHE_LYNX` закомментирована; `APACHE_STATUSURL` в файле нет (умолчание `apache2ctl` — `http://localhost:80/server-status`), при необходимости допишите `export APACHE_STATUSURL=…` | | чем и откуда `apache2ctl status` читает страницу статуса |
| `APACHE_ULIMIT_MAX_FILES` | (закомментирована; по умолчанию `ulimit -n 8192`) | | лимит открытых файлов (раздел 3.4) |
| `APACHE_ARGUMENTS` | (закомментирована) | | дополнительные ключи `apache2`, например `-D MAINTENANCE` для `<IfDefine>` |

`$SUFFIX` — пусто для `/etc/apache2` и `-<имя>` для экземпляра `/etc/apache2-<имя>` **[Debian `envvars`, `README.multiple-instances`]**.

Практика:

- **Не меняйте `APACHE_RUN_USER`** на сервере публикации 1С: права публикаций и файловых баз (`../1c/05` §6) рассчитаны на `www-data`; кроме того, `apache2ctl` откажется стартовать, если каталог блокировок уже есть с другим владельцем (`… already exists but is not a directory owned by …`) **[Debian]**.
- `umask 0002` для совместной работы с файловой базой (официальная рекомендация 1С) — строкой в `envvars` или `UMask=` в drop-in (`../1c/05` §6).
- Изменения `envvars` применяются только `systemctl restart`: при `reload` родитель живёт со старым окружением **[практика]**.
- ⚠ Нужен ли модулю 1С другой `LANG` (кириллица в путях файловой базы), документация 1С не говорит; при «знаках вопроса» вместо кириллицы в сообщениях модуля попробуйте `. /etc/default/locale` — не проверялось.

### 4.4. ports.conf

Содержимое из пакета **[Debian]**:

```apache
Listen 80

<IfModule ssl_module>
	Listen 443
</IfModule>

<IfModule mod_gnutls.c>
	Listen 443
</IfModule>
```

- `Listen [IP-адрес:]порт [протокол]` — без `Listen` сервер не запустится; несколько директив — несколько сокетов; точный повтор того же адреса и порта (`Listen 80` дважды) — ошибка конфигурации `Cannot define multiple Listeners on the same IP:port`, её ловит `configtest`; пересекающиеся адреса (`Listen 80` и `Listen 10.0.0.5:80`) или порт, занятый другим процессом, дают при запуске `(98)Address already in use: AH00072: make_sock: could not bind to address …` **[Apache-код `listen.c`]** (документация `mpm_common` для точного повтора называет «Address already in use» — в коде 2.4.x это уже ошибка разбора).
- Порт в `<VirtualHost *:80>` **не** открывает порт — он только участвует в выборе хоста; слушать порт заставляет только `Listen` **[Apache-док]**.
- Протокол указывают только для нестандартных портов HTTPS: `Listen 8443 https` (для 443 `https` подразумевается) **[Apache-док]**.
- IPv6-адрес — в квадратных скобках: `Listen [2001:db8::1]:80`. `Listen 80` в Ubuntu обслуживает IPv4 и IPv6 одним сокетом: отображение IPv4 в IPv6 (`--enable-v4-mapped`) — умолчание везде, кроме BSD **[Apache-док `bind`]**; уточнено 20.10.2026: в `debian/rules` 2.4.66-2 ключ `--enable/--disable-v4-mapped` не задан, по `configure.in` для Linux действует `yes`, и `listen.c` тогда снимает `IPV6_V6ONLY` **[Debian, Apache-код]**. Проверка — `ss -ltnp | grep apache2` (`*:80`).
- Чтобы слушать только один интерфейс (например, Apache за локальным nginx): `Listen 127.0.0.1:8080`. Переход на другой порт с прежним `Listen 80` не конфликтует (при перезапуске новый сокет открывается, старый закрывается); конфликтует смена адреса на **том же** порту (`Listen 80` ↔ `Listen 127.0.0.1:80`) — тогда нужен `systemctl restart` (stop + start), а при `reload` сервер завершится с ошибкой **[Apache-док `bind`, Apache-код `listen.c`]**. Надёжнее любые изменения `Listen` применять в окно через `restart` **[практика]**.
- После изменения портов: `sudo apache2ctl configtest && sudo systemctl restart apache2 && ss -ltnp | grep apache2`. Порты ниже 1024 открывает родительский процесс от root — отдельных прав не нужно **[практика]**.

### 4.5. conf-available и conf-enabled

Фрагменты пакета (все включены при установке) **[Debian]**:

| Файл | Что делает |
|---|---|
| `charset.conf` | только закомментированный `#AddDefaultCharset UTF-8` с предупреждением: включать, лишь если все файлы сайта в этой кодировке |
| `localized-error-pages.conf` | примеры многоязычных страниц ошибок `ErrorDocument` (закомментированы) |
| `other-vhosts-access-log.conf` | `CustomLog ${APACHE_LOG_DIR}/other_vhosts_access.log vhost_combined` — журнал доступа для хостов, у которых нет своего `CustomLog` |
| `security.conf` | `ServerTokens OS`, `ServerSignature On`, `TraceEnable Off`; закомментированные примеры `RedirectMatch 404 /\.git`, `Header set X-Content-Type-Options: "nosniff"`, `Header set Content-Security-Policy "frame-ancestors 'self';"` — ужесточение в `02-…` |
| `serve-cgi-bin.conf` | если загружены `mod_alias` и `mod_cgi`/`mod_cgid`: `ScriptAlias /cgi-bin/ /usr/lib/cgi-bin/` и `<Directory "/usr/lib/cgi-bin">` с `Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch` |

Свои фрагменты:

```bash
# пример: глобальное имя сервера (раздел 10) и таймаут мягкой остановки
sudo tee /etc/apache2/conf-available/local-servername.conf >/dev/null <<'EOF'
ServerName srv-1c-app.corp.example
EOF
sudo a2enconf local-servername
sudo apache2ctl configtest && sudo systemctl reload apache2
ls -l /etc/apache2/conf-enabled/                     # local-servername.conf -> ../conf-available/local-servername.conf
```

Фрагмент можно выключить глобально (`a2disconf`) и подключить в одном виртуальном хосте строкой `Include conf-available/<имя>.conf` — так `000-default.conf` предлагает поступать с `serve-cgi-bin.conf`; работает не для всех директив (зависит от их контекста) **[Debian]**.

### 4.6. mods-available и mods-enabled

- На каждый модуль — `<имя>.load` (одна строка `LoadModule <идентификатор> /usr/lib/apache2/modules/mod_<имя>.so`) и, если нужно, `<имя>.conf` с настройками; `a2enmod` ставит ссылки на оба **[Debian]**.
- В первой строке `.load` бывают служебные комментарии, которые читает `a2enmod` **[Debian `a2enmod`]**:
  - `# Depends: …` — включить сначала эти модули (`ssl.load`: `# Depends: mime socache_shmcb`; `proxy_http.load`: `# Depends: proxy`);
  - `# Conflicts: …` — отказаться включать, пока включены перечисленные (`mpm_event.load`: `# Conflicts: mpm_worker mpm_prefork`).
- Настройки модуля из `<имя>.conf` попадают в **основной** контекст сервера, то есть действуют на все виртуальные хосты **[Debian man `a2enmod`]**. Например, `status.conf` задаёт `<Location /server-status>` с `SetHandler server-status` и `Require local`, `ExtendedStatus On`, а при загруженном `mod_proxy` — `ProxyStatus On`; `reqtimeout.conf` — `RequestReadTimeout header=20-40,minrate=500` и `RequestReadTimeout body=10,minrate=500`; `dir.conf` — `DirectoryIndex index.html index.cgi index.pl index.php index.xhtml index.htm` **[Debian]**.
- Параметры MPM лежат в `mpm_event.conf`, `mpm_worker.conf`, `mpm_prefork.conf` (раздел 8.5). Правьте их там или переопределяйте в `conf-available/local-*.conf` — но помните, что `conf-enabled` читается **после** `mods-enabled`, и для однократных директив (`ServerLimit`, `ThreadsPerChild`) действует последнее значение — уточнено 20.10.2026 по коду MPM (`set_server_limit`, `set_threads_per_child` в `worker.c` просто перезаписывают глобальное значение при каждом вхождении) **[Apache-код]**; результат проверяйте по `server-status` или по числу процессов.

### 4.7. sites-available и sites-enabled

- Пакет даёт `000-default.conf` (`<VirtualHost *:80>`, `ServerAdmin webmaster@localhost`, `DocumentRoot /var/www/html`, свои `ErrorLog`/`CustomLog`, закомментированный `ServerName`) и `default-ssl.conf` (HTTPS-хост на сертификате «snakeoil», не включён) **[Debian]**.
- Имя файла не обязано совпадать с `ServerName`, но так удобнее: `redmine.corp.example.conf` или просто `redmine.conf` **[Debian, Ubuntu]**.
- Хост по умолчанию для IP:порта — **первый** прочитанный; поэтому сайт по умолчанию называют `000-default`, чтобы он был первым по алфавиту **[Debian `README.Debian`, man `a2ensite`]**.
- Новый сайт: скопировать шаблон, отредактировать, включить, проверить, перечитать:

```bash
sudo cp /etc/apache2/sites-available/000-default.conf /etc/apache2/sites-available/redmine.conf
sudoedit /etc/apache2/sites-available/redmine.conf
sudo a2ensite redmine                          # имя без .conf или с ним — одинаково
sudo apache2ctl configtest && sudo apache2ctl -S
sudo systemctl reload apache2
```

Документация Ubuntu после `a2ensite` предлагает `systemctl restart`; достаточно `reload` — так советует и сама `a2ensite` **[Ubuntu, Debian `a2enmod`]**.

### 4.8. Каталоги вне /etc

| Каталог | Что | Заметки |
|---|---|---|
| `/var/www/html` | корень сайта по умолчанию | владелец root; `www-data` писать сюда **не должен** **[практика]** |
| `/var/www/<публикация>` | каталоги публикаций 1С с `default.vrd` | права — `../1c/05` §6 |
| `/var/log/apache2` | `error.log`, `access.log`, `other_vhosts_access.log`, журналы хостов | файлы `root:adm 0640` ⚠ права самого каталога не сверялись |
| `/etc/logrotate.d/apache2` | `/var/log/apache2/*.log`: `daily`, `rotate 14`, `compress`, `delaycompress`, `create 640 root adm`; после ротации — `invoke-rc.d apache2 reload`; перед ротацией — сценарии из `/etc/logrotate.d/httpd-prerotate/` | журналы вне `/var/log/apache2` не ротируются **[Debian]** |
| `/var/lib/apache2/` | метки `a2enmod`/`a2ensite`/`a2enconf` (`{module,site,conf}/{enabled,disabled}_by_{admin,maint}/<имя>`), `deferred_actions` | вручную не трогать **[Debian]** |
| `/run/apache2`, `/run/lock/apache2` (в 22.04/24.04 записаны как `/var/run/…`, `/var/lock/…`) | PID, разделяемая память, `socks/`; блокировки (владелец `www-data`) | создаёт `apache2ctl` при запуске **[Debian]** |
| `/var/cache/apache2/mod_cache_disk` | дисковый кэш | в 26.04 — в `ReadWritePaths` юнита |
| `/usr/share/doc/apache2-doc/manual/` | руководство (`apache2-doc`), по `README.Debian` доступное и как `http://<сервер>/manual/` | на рабочем сервере не ставить или выключить его фрагмент |

### 4.9. Куда класть свои настройки и куда пишет 1С

| Что | Куда | Чем включать |
|---|---|---|
| Глобальные настройки (`ServerName`, `GracefulShutdownTimeout`, `StrictHostCheck`, свой формат журнала) | `/etc/apache2/conf-available/local-<что>.conf` | `a2enconf local-<что>` |
| Параметры MPM | `/etc/apache2/mods-available/mpm_<имя>.conf` | — (действуют, когда MPM включён) |
| Сайт / виртуальный хост | `/etc/apache2/sites-available/<имя>.conf` | `a2ensite <имя>` |
| Модуль 1С и публикации (`webinst` по умолчанию) | конец `/etc/apache2/apache2.conf` | `webinst` сам |
| Публикации 1С при ручной настройке | `conf-available/1c-<имя>.conf` (глобально) или внутри `<VirtualHost>` сайта 1С | `a2enconf` / `a2ensite` |
| Переопределение службы | `/etc/systemd/system/apache2.service.d/override.conf` | `systemctl edit apache2` |
| Переменные окружения, `umask`, `ulimit` | `/etc/apache2/envvars` | `systemctl restart apache2` |

Источники: `README.Debian` **[Debian]**; поведение `webinst` — **[ИТС-адм разд. 8.10.1.2.3]**, `../1c/05` §4.3–4.6.

Важное следствие расположения публикаций 1С (подробно — раздел 11.5): блок, записанный в основной контекст (`apache2.conf` или `conf-enabled`), действует **во всех** виртуальных хостах этого экземпляра Apache. Если публикация должна открываться только по имени `1c.corp.example` и только по HTTPS, переносите её `Alias` и `<Directory>` внутрь соответствующего `<VirtualHost>` (ручная публикация, `../1c/05` §4.6) или закрывайте прочие хосты (раздел 11.4) **[Apache-код, практика]**.

## 5. Утилиты a2enmod, a2dismod, a2ensite, a2dissite, a2enconf, a2disconf, a2query

Все шесть команд — один сценарий на Perl (`a2enmod`) под разными именами; суффикс `-<имя>` в имени вызова означает экземпляр `/etc/apache2-<имя>` **[Debian `a2enmod`, `apache2.links`]**. Ключи: `-q` (тихо), `-m` (режим сценариев пакетов — не для людей), у `a2dis*` ещё `-p` (стереть метки), у `a2dismod` — `-f` **[Debian man]**.

Как они работают **[Debian `a2enmod`, man-страницы]**:

- создают или удаляют **относительные** ссылки (`../mods-available/ssl.load`) в `*-enabled`; повторное включение или выключение — не ошибка; имя принимают без суффикса (или с ним) и шаблоном (`a2dismod 'proxy_*'`); без аргументов спрашивают интерактивно;
- `a2enmod` по `# Depends:` включает зависимости, по `# Conflicts:` отказывается (`ERROR: Module mpm_event is enabled - cannot proceed due to conflicts. It needs to be disabled first!`); `a2dismod -f` выключает и зависимые модули;
- на многопоточном MPM `a2enmod cgi` заменяется на `cgid` («Your MPM seems to be threaded. Selecting cgid instead of cgi.»);
- выключение существенного модуля (`alias auth_basic authn_file authz_host authz_user autoindex deflate dir env filter logio mime negotiation setenvif unixd version watchdog`) требует ввести `Yes, do as I say!` или ключ `-f`;
- в конце печатают, что сделать: для модулей — `systemctl restart apache2`, для сайтов и фрагментов — `systemctl reload apache2` (для экземпляра — `apache2@<имя>`);
- пишут метки в `/var/lib/apache2/…/{enabled,disabled}_by_admin/`: пакет модуля при обновлении не включит снова то, что администратор выключил;
- `a2dis*` откажутся удалять обычный файл в `*-enabled` («is not a symbolic link, not deleting») — не кладите файлы прямо туда;
- коды возврата: 0 — успех, 1 — ошибка, 2 — неверный ключ.

`a2query` — справка о включённом **[Debian man `a2query`]**: `a2query -M` (текущий MPM), `-m [модуль]`, `-s [сайт]`, `-c [фрагмент]` (включено ли; код 0 — да, 32 — не найден среди включённых, 33 — выключен сценарием пакета, 1 — такого нет вовсе), `-v` (версия Apache), `-a` (версия API модулей). `a2query` читает ссылки и метки, а не работающий процесс; что реально загружено — `sudo apache2ctl -M` **[практика]**.

## 6. apache2ctl и apache2: проверка и диагностика конфигурации

### 6.1. Команды

`apache2ctl` (ссылка `apachectl`) принимает одно слово-команду (`start`, `stop`, `restart`, `graceful`, `graceful-stop`, `configtest`, `status`, `fullstatus`, `help`) или передаёт любые ключи `apache2`, подставив переменные окружения **[Debian man `apache2ctl`, сценарий]**.

| Команда | Что показывает |
|---|---|
| `sudo apache2ctl configtest` = `-t` | синтаксис: `Syntax OK` или `AH00526: Syntax error on line N of <файл>:` и текст ошибки **[Apache-код `config.c`]** |
| `sudo apache2ctl -S` = `-t -D DUMP_VHOSTS -D DUMP_RUN_CFG` | виртуальные хосты и пути запуска (раздел 6.2) **[Apache-код `main.c`]** |
| `sudo apache2ctl -t -D DUMP_INCLUDES` | прочитанные файлы в порядке чтения **[Apache-код]** |
| `sudo apache2ctl -M` = `-t -D DUMP_MODULES` | загруженные модули: `(static)` — встроенные, `(shared)` — из `.so` **[Apache-док]** |
| `apache2ctl -l` / `-L` | встроенные модули / их директивы с контекстами **[Apache-док]** |
| `apache2ctl -V`; `apache2 -v` | версия и параметры сборки (`Server MPM`); только версия **[Apache-док]** |
| `sudo apache2ctl -X` | один процесс без отсоединения от консоли — отладка; не запускать, пока работает служба **[Apache-док]** |

Полезные ключи: `-e <уровень>` (уровень журнала на время запуска), `-E <файл>` (сообщения запуска в файл), `-D <имя>` (параметр для `<IfDefine>`), `-T` (не проверять `DocumentRoot`) **[Apache-док `programs/httpd`]**. При включённом `mod_info` ключ `-D DUMP_CONFIG` выводит разобранную конфигурацию при запуске **[Apache-док `mod_info`]**.

Почему не `apache2 -t` напрямую: без `envvars` будут `AH00111: Config variable ${APACHE_RUN_DIR} is not defined` и ошибка `DefaultRuntimeDir must be a valid directory, absolute or relative to ServerRoot` или `bad user name ${APACHE_RUN_USER}` **[Apache-код `core.c`, `mpm_common.c`; Debian `README.Debian` п. 8]**.

`configtest` ловит не всё (занятый порт, нет файла сертификата или каталога журнала, модуль не загружается): окончательная проверка — `systemctl reload`/`restart` и `systemctl status` **[Apache-док `stopping`, практика]**.

### 6.2. Как читать apache2ctl -S

Формат вывода задаётся кодом `server/vhost.c` и `server/core.c` **[Apache-код]**. Пример для ВМ `srv-itsm` с хостом по умолчанию и двумя сайтами (значения иллюстративные ⚠ — сверяйте со своим выводом):

```
VirtualHost configuration:
*:80                   is a NameVirtualHost
         default server srv-itsm.corp.example (/etc/apache2/sites-enabled/000-default.conf:1)
         port 80 namevhost srv-itsm.corp.example (/etc/apache2/sites-enabled/000-default.conf:1)
         port 80 namevhost netbox.corp.example (/etc/apache2/sites-enabled/netbox.conf:1)
         port 80 namevhost redmine.corp.example (/etc/apache2/sites-enabled/redmine.conf:1)
                 alias redmine
ServerRoot: "/etc/apache2"
Main DocumentRoot: "/var/www/html"
Main ErrorLog: "/var/log/apache2/error.log"
Mutex default: dir="/var/run/apache2/" mechanism=default
PidFile: "/var/run/apache2/apache2.pid"
Define: DUMP_VHOSTS
Define: DUMP_RUN_CFG
User: name="www-data" id=33
Group: name="www-data" id=33
```

Как читать:

- `*:80 is a NameVirtualHost` — на `*:80` несколько хостов, выбор по имени; `default server` — хост, который получит запрос с незнакомым именем (первый прочитанный);
- строка вида `10.0.0.5:80  1c.corp.example (…)` без `is a NameVirtualHost` — единственный хост на этом точном IP:порту: он перехватит **все** запросы на этот адрес, имена не сравниваются (раздел 11.1);
- `alias` / `wild alias` — значения `ServerAlias` (с подстановкой `*` — `wild alias`);
- в скобках — файл и строка, где начинается `<VirtualHost>`: так находят дубликаты и забытые сайты;
- `Main DocumentRoot`/`Main ErrorLog` — значения основного сервера, которые наследуют хосты без своих.

### 6.3. Модули, версия, MPM одной командой

```bash
sudo apache2ctl -V | grep -E 'Server version|Server MPM|threaded|forked'
sudo apache2ctl -M 2>/dev/null | grep -E 'mpm|1cws|ssl|proxy|systemd'
apache2ctl -l                      # core.c mod_so.c mod_watchdog.c http_core.c mod_log_config.c mod_logio.c mod_version.c mod_unixd.c …
ls -l /etc/apache2/mods-enabled/ | grep -c '\.load'
```

## 7. Как Apache читает конфигурацию

### 7.1. Синтаксис файлов

**[Apache-док `configuring`]**: одна директива на строку; `\` последним символом (без пробелов после) переносит директиву на следующую строку; строка, начинающаяся с `#`, — комментарий, **комментарий в конце строки с директивой не допускается** (`Listen 80 # http` — ошибка); аргумент с пробелами — в двойных или одинарных кавычках, внутри распознаются только `\\` и `\"` (`\'`), две строки в кавычках подряд без пробела — **два** аргумента; имена директив нечувствительны к регистру, аргументы часто чувствительны; длина строки после подстановок — около 16 МиБ.

### 7.2. Include и IncludeOptional

**[Apache-док `core`]**: `Include` вставляет файл, каталог (все файлы и подкаталоги — не рекомендуется: подхватятся временные файлы редактора) или шаблон (`*.conf`; файлы — в алфавитном порядке); путь абсолютный или от `ServerRoot` (в Ubuntu — `/etc/apache2`). Шаблон без совпадений — ошибка у `Include` и молчаливый пропуск у `IncludeOptional` (Debian использует его для `*-enabled`). Включённый текст обрабатывается так, как если бы стоял на месте директивы (важно для порядка секций, раздел 7.6). Контексты — server config, virtual host, directory.

### 7.3. Define, ${VAR} и переменные окружения

**[Apache-док `core`, `configuring`]**:

- `Define <имя>` — то же, что ключ `-D <имя>`: включает секции `<IfDefine имя>`; `Define <имя> <значение>` — задаёт переменную, которую можно подставлять как `${имя}`.
- Переменная `Define` действует **глобально** с места определения до конца конфигурации, даже если `Define` стоит внутри `<VirtualHost>` — это частая ловушка при копировании сайтов. `UnDefine` снимает определение (только в server config).
- `${VAR}` подставляет и переменные `Define`, и переменные окружения, существовавшие **до запуска** сервера (у Debian — из `envvars`); `Define` имеет приоритет. `SetEnv` в конфигурации задаёт переменные для запросов и в подстановке `${…}` не участвует.
- Неопределённая `${VAR}` остаётся текстом как есть и даёт предупреждение `AH00111: Config variable ${VAR} is not defined` **[Apache-код `core.c`]**.
- Имя переменной не может содержать двоеточие.

Пример из пакета: `serve-cgi-bin.conf` определяет `ENABLE_USR_LIB_CGI_BIN` внутри `<IfModule mod_cgi.c>`/`<IfModule mod_cgid.c>` и включает `ScriptAlias` в `<IfDefine ENABLE_USR_LIB_CGI_BIN>` **[Debian]**.

Пример для своих сайтов — один домен в одном месте:

```apache
# /etc/apache2/conf-available/local-vars.conf  (a2enconf local-vars)
Define DOMAIN corp.example
```

```apache
# /etc/apache2/sites-available/redmine.conf
<VirtualHost *:80>
    ServerName redmine.${DOMAIN}
    ErrorLog  ${APACHE_LOG_DIR}/redmine-error.log
    CustomLog ${APACHE_LOG_DIR}/redmine-access.log combined
</VirtualHost>
```

### 7.4. Условные секции

| Секция | Условие | С какой версии | Источник |
|---|---|---|---|
| `<IfModule [!]модуль>` | модуль загружен (статически или `LoadModule`); имя — идентификатор (`ssl_module`) или файл исходника (`mod_ssl.c`) | — | **[Apache-док]** |
| `<IfDefine [!]параметр>` | задан `-D параметр` или `Define параметр` | — | **[Apache-док]** |
| `<IfFile [!]файл>` | файл существует (путь абсолютный или от `ServerRoot`) | 2.4.34 (имена с пробелами в кавычках — с 2.4.35) | **[Apache-док]** |
| `<IfDirective [!]директива>` | директива доступна (модуль загружен и её знает) | 2.4.34 | **[Apache-док]** |
| `<IfSection [!]секция>` | секция доступна | 2.4.34 | **[Apache-док]** |
| `<IfVersion [[!]оператор] версия>` | версия сервера (`mod_version`, в Ubuntu встроен) | — | **[Apache-док]**, **[Debian]** |

Применение: `<IfModule mpm_worker_module>` или `<IfModule worker.c>` — оба вида работают; руководство 1С использует второй (`<IfModule worker.c> ServerLimit 1 </IfModule>`) **[ИТС-адм разд. 8.10.1.1, Apache-док `IfModule`]**. Документация Apache советует применять `<IfModule>` только там, где один файл должен работать и с модулем, и без него, а в обычной конфигурации директивы в него не заворачивать **[Apache-док]**: если модуль защиты не загружен, лучше получить ошибку запуска, чем молча работающую без защиты конфигурацию **[практика]**.

Пример использования `<IfFile>`: подключить сертификат, только если он уже выпущен (полезно при первом запуске certbot):

```apache
<IfFile "/etc/letsencrypt/live/1c.corp.example/fullchain.pem">
    Include /etc/apache2/sites-available/1c-ssl.inc
</IfFile>
```

### 7.5. Контексты директив

У каждой директивы в документации указан контекст **[Apache-док]**: **server config** (вне секций: `apache2.conf`, `conf-enabled`, `mods-enabled`), **virtual host** (`<VirtualHost>`), **directory** (`<Directory>`, `<Location>`, `<Files>`, `<Proxy>`, `<If>` и варианты с `Match`), **.htaccess** (если разрешено `AllowOverride`). Примеры: `Listen`, `ServerLimit`, `Mutex`, `GracefulShutdownTimeout`, `User` — только server config; `ServerName`, `DocumentRoot`, `ErrorLog`, `Timeout`, `StrictHostCheck` — server config и virtual host; `Require`, `AuthMerging` — directory и `.htaccess`; `AllowOverride` — только `<Directory>` без регулярных выражений. Директива не в своём контексте даёт `<директива> cannot occur within <VirtualHost> section`, `… cannot occur within directory context` или `<директива> not allowed here` **[Apache-код `core.c`, `config.c`]**. Справка: https://httpd.apache.org/docs/2.4/mod/quickreference.html.

### 7.6. Секции Directory, Files, Location, If и порядок слияния

Секции бывают «файловые» (`<Directory>`, `<DirectoryMatch>`, `<Files>`, `<FilesMatch>`) и «по адресу» (`<Location>`, `<LocationMatch>`); `<If>` применяется по результату выражения при обработке запроса; `<Proxy>` — к проксируемым адресам **[Apache-док `sections`]**.

Порядок применения **[Apache-док `sections`]**:

1. `<Directory>` (без регулярных выражений) **вместе с** `.htaccess` (`.htaccess` переопределяет `<Directory>`) — от короткого пути к длинному независимо от порядка в файлах;
2. `<DirectoryMatch>` и `<Directory "~ …">`;
3. `<Files>` и `<FilesMatch>`;
4. `<Location>` и `<LocationMatch>`;
5. `<If>` (даже вложенные в предыдущие секции); `<Else>`/`<ElseIf>` — вместе с ней.

Дополнительно: внутри групп 2–5 секции применяются в порядке появления в конфигурации; секции внутри `<VirtualHost>` применяются **после** одноимённых секций вне его (хост может переопределить общее); при проксировании `<Proxy>` занимает место `<Directory>`; для запроса выбирается только **один** виртуальный хост — секции разных хостов не смешиваются.

Следствия для администратора **[Apache-док, практика]**:

- **Доступ к файлам ограничивайте `<Directory>`**, а не `<Location>`: на один файл ведут разные URL (регистр, `//`, ссылки, `Alias`), и `<Location>` можно обойти. Исключение — `<Location "/">`: он действует на все запросы. Публикации 1С `webinst` оформляет правильно — `Alias` + `<Directory>` (`../1c/05` §4.3).
- `<Location>` применяется **последним** (до `<If>`), поэтому `Require all granted` в `<Location "/">` отменит все запреты из `<Directory>`. И наоборот, `Require all denied` в `<Location "/">` закроет всё, включая публикации 1С, — это используют для хоста-«ловушки» (раздел 11.4). Так работает потому, что по умолчанию (`AuthMerging Off`) правила авторизации более поздней секции заменяют правила более ранней **[Apache-док `mod_authz_core`]**.
- Внутри `<Location>` не используйте `<Limit>` для ограничения отдельных методов: для неперечисленных методов секция считается «без требований», что фактически открывает доступ и перекрывает запреты `<Directory>`; используйте `<LimitExcept>` или ограничения без привязки к методам **[Apache-док `sections`]**.
- `<If>` не может сделать условными директивы, срабатывающие при разборе конфигурации (`Define`, `Include`, `Error`) — они действуют всегда **[Apache-док `If`]**.

Пример `<If>` — запрет обращения к публикации не из внутренней сети (выражение `-R` проверяет адрес клиента по подсети) **[Apache-док `expr`]**:

```apache
<Directory "/var/www/demo/">
    <If "! -R '10.0.0.0/8'">
        Require all denied
    </If>
</Directory>
```

Проще и нагляднее то же делается без `<If>`: `Require ip 10.0.0.0/8` внутри `<Directory>` (`mod_authz_host`) — подробнее о разграничении доступа в `02-…`. Если Apache стоит за обратным прокси, адрес клиента нужно сначала восстановить (`mod_remoteip`, `03-…`), иначе `-R` и `Require ip` видят адрес прокси.

### 7.7. .htaccess и AllowOverride

**[Apache-док `core`, `howto/htaccess`]**:

- `AllowOverride` (только в `<Directory>` без регулярных выражений) задаёт классы директив, разрешённые в `.htaccess`: `None`, `All` или набор `AuthConfig`, `FileInfo`, `Indexes`, `Limit`, `Options[=…]`, `Nonfatal=[Override|Unknown|All]`; `AllowOverrideList` — отдельные директивы. Умолчание — `None` (с 2.3.9; в 2.2 было `All`).
- При `None` Apache даже не ищет `.htaccess`; при разрешённом — проверяет файл в каждом каталоге пути на **каждом** запросе и перечитывает его. `Nonfatal=…` превращает ошибки `.htaccess` из `500` в предупреждение, но проигнорированная директива ограничения доступа просто перестанет действовать.
- Есть доступ к основной конфигурации — держите всё (аутентификацию, `mod_rewrite`) в ней, а не в `.htaccess`; в `<Directory "/">` шире `None` не ставьте.

В Ubuntu `.htaccess` выключен для `/` и `/var/www/`, а `<FilesMatch "^\.ht">` не даёт скачать сами файлы **[Debian]**. Блок публикации от `webinst` для Apache 2.4, по наблюдениям, содержит `AllowOverride All` (⚠ см. `../1c/05` §4.3) — в каталоге публикации кроме `default.vrd` ничего нет, ставьте там `AllowOverride None` **[практика]**.

```bash
sudo grep -rn --include='*.conf' -i 'AllowOverride' /etc/apache2/ | grep -vi 'none'    # где разрешён .htaccess
```

### 7.8. Макросы mod_macro для однотипных хостов

`mod_macro` (с 2.4.5; в Ubuntu не включён: `sudo a2enmod macro`) разворачивает шаблоны при запуске: `<Macro имя $параметр …> … </Macro>`, `Use имя значения…`, `UndefMacro имя`. Параметры начинайте с `$`, `%` или `@` (иначе предупреждение); подставляется ровно то имя, что объявлено в `<Macro>`. Если значение нужно встроить в строку без разделителя, объявите параметр в скобках — `<Macro имя $(param)>` — и пишите `$(param)` в теле; форма `${param}` конфликтует с переменными `Define` **[Apache-док `mod_macro`]**. Пример для ВМ сервисов (⚠ на сервере не запускался; нужны `a2enmod proxy proxy_http`, полные настройки прокси — `03-…`):

```apache
<Macro ProxySite $name $port>
    <VirtualHost *:80>
        ServerName $name.corp.example
        ErrorLog  ${APACHE_LOG_DIR}/$name-error.log
        CustomLog ${APACHE_LOG_DIR}/$name-access.log combined
        ProxyPreserveHost On
        ProxyPass        / http://127.0.0.1:$port/
        ProxyPassReverse / http://127.0.0.1:$port/
    </VirtualHost>
</Macro>
Use ProxySite redmine 3000
UndefMacro ProxySite
```

## 8. MPM: event, worker, prefork

### 8.1. Чем отличаются

MPM (Multi-Processing Module) принимает соединения и раздаёт их обработчикам; в сервере загружен ровно один MPM, в Ubuntu все три собраны модулями (`--enable-mpms-shared=all`) и переключаются `a2enmod` **[Apache-док `mpm`, Debian `debian/rules`]**.

| | `prefork` | `worker` | `event` |
|---|---|---|---|
| Модель | процессы без потоков; один процесс — одно соединение | процессы × потоки; поток занят соединением всё время, **включая простой keep-alive** | как `worker`, но простаивающие keep-alive-соединения, дописывание ответа медленному клиенту и закрытие соединений обслуживает поток-слушатель; рабочий поток занят только обработкой запроса |
| Когда выбирать | нужны непотокобезопасные библиотеки (`mod_php`); максимальная изоляция запросов | рекомендация 1С для публикации на Linux | по умолчанию; лучше всего держит много простаивающих соединений (обратный прокси для сервисов) |
| Главные директивы | `StartServers`, `MinSpareServers`, `MaxSpareServers`, `MaxRequestWorkers`, `MaxConnectionsPerChild`, `ServerLimit` | `StartServers`, `MinSpareThreads`, `MaxSpareThreads`, `ThreadLimit`, `ThreadsPerChild`, `MaxRequestWorkers`, `MaxConnectionsPerChild`, `ServerLimit` | те же, что у `worker`, плюс `AsyncRequestWorkerFactor` (по умолчанию 2) |
| Значения в файле Ubuntu (`mods-available/mpm_*.conf`) | `StartServers 5`, `MinSpareServers 5`, `MaxSpareServers 10`, `MaxRequestWorkers 150`, `MaxConnectionsPerChild 0` | `StartServers 2`, `MinSpareThreads 25`, `MaxSpareThreads 75`, `ThreadLimit 64`, `ThreadsPerChild 25`, `MaxRequestWorkers 150`, `MaxConnectionsPerChild 0` | как у `worker` |
| Умолчания Apache (если директивы нет) | `StartServers 5`, `MinSpareServers 5`, `MaxSpareServers 10`, `MaxRequestWorkers 256`, `ServerLimit 256` | `StartServers 3`, `MinSpareThreads 75`, `MaxSpareThreads 250`, `ThreadLimit 64`, `ThreadsPerChild 25`, `ServerLimit 16`, `MaxRequestWorkers` = 16 × 25 = 400 | как у `worker` |

Источники: `mpm_common`, `event`, `worker`, `prefork` **[Apache-док]**; файлы `mpm_*.conf` метки `debian/2.4.58-1` **[Debian]**.

Ограничения `event` по документации **[Apache-док `event`]**: все модули из поставки Apache с ним совместимы; если фильтр соединения объявил себя несовместимым, `event` ведёт себя как `worker` (поток на соединение); для ответов от CGI/FastCGI и проксируемых серверов (в отличие от статических файлов) поток держится до конца формирования ответа — выигрыш `event` там в основном в обслуживании простаивающих keep-alive-соединений. ⚠ Что так же ведут себя ответы модуля 1С, — вывод по аналогии, не проверялся.

### 8.2. MPM и модуль 1С (wsap24.so)

Официально **[ИТС-адм разд. 8.2, 8.10.1.1]**:

- на Linux с Apache 2.2 и новее рекомендуется MPM **`worker`**, остальные «использовать не рекомендуется»;
- каждый рабочий процесс веб-сервера несёт свой экземпляр расширения веб-сервера (модуля 1С);
- для **файловой** базы запросы к одной базе выполняются модулем последовательно; разрешать нескольким рабочим процессам обслуживать публикацию файловой базы не рекомендуется, а при фоновых заданиях процесс должен быть ровно один: `ServerLimit 1` в секции настроек `worker` (`<IfModule worker.c>`); для другого MPM аналог искать в его документации.

Что из этого следует для Apache **[Apache-док, практика]**:

- При `ServerLimit 1` и `worker` одновременных запросов не больше `ThreadsPerChild` (а он не больше `ThreadLimit`, по умолчанию 64); `MaxRequestWorkers` должен быть равен `ThreadsPerChild` (`1 × ThreadsPerChild`). Пример и расчёт для нагрузки — `../1c/05` §12.
- `ServerLimit` действует на весь экземпляр Apache: если на нём же нагруженная серверная база или сервисы, один процесс станет узким местом — держите файловые публикации в отдельном экземпляре (раздел 3.5).
- ⚠ Вывод из описания `ServerLimit` и мягкого перезапуска, не проверялся: при `ServerLimit 1` во время `graceful` старый процесс занимает единственное место в таблице процессов, пока не доработает текущие запросы, и новые запросы к публикации могут ждать его завершения. Для файловой базы меняйте конфигурацию в окно обслуживания.
- `event` с модулем 1С на практике работает (на нём по умолчанию публикуется большинство инструкций, `../1c/05` §3.3), но это не официальная рекомендация: при обращении в поддержку 1С ожидайте вопроса о MPM **[практика]**.
- `prefork` для 1С плох: процесс на соединение означает столько экземпляров модуля и пулов соединений с кластером, сколько процессов, — лишняя память и соединения, для файловой базы — ошибки блокировок (`../1c/05` §3.3) **[практика]**.
- На ВМ сервисов (`srv-itsm`, `srv-obs`), где Apache только проксирует, оставляйте `event` **[практика]**.

### 8.3. MPM и PHP: почему mod_php несовместим с рекомендацией 1С

Сценарий установки `libapache2-mod-php<версия>` (Debian/Ubuntu) **[Debian, пакет php]**:

- если уже включён `prefork` (или `itk`) — просто включает модуль PHP;
- иначе вызывает `apache2_switch_mpm prefork` — **переключает весь Apache на `prefork`**; если переключить не удалось — не включает PHP и пишет `Could not switch to prefork MPM, not enabling PHP <версия>`;
- если уже включён PHP другой версии — не включает новый (`… module already enabled, not enabling PHP …`).

Следствие: установка на `srv-1c-app` любого веб-приложения на PHP с зависимостью от `libapache2-mod-php` молча переводит публикацию 1С на `prefork` (вступит в силу при ближайшем перезапуске). После установки пакетов проверяйте `a2query -M` **[практика]**. Если PHP всё-таки нужен на том же Apache — используйте `php<версия>-fpm` (PHP работает отдельной службой, Apache обращается к ней через `mod_proxy_fcgi`, MPM не меняется): пакет `php-fpm` кладёт фрагмент `conf-available/php<версия>-fpm.conf` **[Debian, пакет php]**; включение — `sudo a2enmod proxy_fcgi setenvif && sudo a2enconf php8.3-fpm` (24.04; уточнено 20.10.2026 по `debian/php-fpm.postinst.extra` ветки `debian/main/8.3`: именно эти две команды пакет печатает при установке, сам он PHP-FPM в Apache не включает). Сервисам пользователя (Redmine, NetBox, GlitchTip) PHP не нужен.

### 8.4. Как узнать и переключить MPM

```bash
# 1) что сейчас
a2query -M                                          # event
sudo apache2ctl -V | grep -i 'server mpm'           # Server MPM:     event
sudo apache2ctl -M | grep mpm                       # mpm_event_module (shared)

# 2) переключить на worker (сначала выключить текущий — иначе a2enmod откажет из-за «# Conflicts:»)
sudo a2dismod mpm_event
sudo a2enmod mpm_worker
sudo apache2ctl configtest                          # Syntax OK; если «No MPM loaded» — не включили новый MPM

# 3) применить — только полным перезапуском (обрыв текущих запросов: делайте в окно)
sudo systemctl restart apache2

# 4) проверить
a2query -M                                          # worker
sudo apache2ctl -V | grep -i 'server mpm'           # Server MPM:     worker
ps -o pid,nlwp,cmd -C apache2                       # у дочерних процессов nlwp = ThreadsPerChild + служебные потоки
```

Ошибки:

- `ERROR: Module mpm_event is enabled - cannot proceed due to conflicts. It needs to be disabled first!` — не выключили старый MPM **[Debian `a2enmod`]**;
- `AH00534: apache2: Configuration error: More than one MPM loaded.` — две ссылки `mpm_*.load` в `mods-enabled` (например, после ручного копирования) **[Apache-док `mpm`]**;
- `AH00534: apache2: Configuration error: No MPM loaded.` — выключили, но не включили **[Apache-код `mpm_common.c`]**.

```bash
ls -l /etc/apache2/mods-enabled/mpm_*            # должна быть ровно одна пара mpm_<имя>.load/.conf
```

### 8.5. Параметры MPM: где лежат и что меняется только полным перезапуском

- Файл — `/etc/apache2/mods-available/mpm_<имя>.conf` (ссылка на него появляется в `mods-enabled` вместе с `.load`). Директивы MPM — контекста server config: внутри `<VirtualHost>` Apache не запустится с ошибкой `… cannot occur within <VirtualHost> section` **[Debian, Apache-док, Apache-код `worker.c` — `GLOBAL_ONLY`]**.
- `MaxRequestWorkers` для `worker`/`event` — общее число потоков-обработчиков; должно быть не меньше `ThreadsPerChild` и кратно ему (иначе Apache округлит вниз и напишет предупреждение); чтобы поднять выше `ServerLimit × ThreadsPerChild`, нужно поднять `ServerLimit`. Для `event` `ServerLimit` должен вмещать ещё и старые процессы, дорабатывающие после `graceful` **[Apache-док]**.
- `ThreadsPerChild` ≤ `ThreadLimit`; `MaxSpareThreads` ≥ `MinSpareThreads` + `ThreadsPerChild` (иначе Apache сам поправит) **[Apache-док]**.
- `ServerLimit` и `ThreadLimit` задают размер разделяемой таблицы процессов: их изменение при любом перезапуске (`graceful`, `restart`) игнорируется — нужен `systemctl restart` (stop + start). Слишком большие значения тратят разделяемую память; жёсткие пределы при сборке — `ServerLimit 20000` (у `prefork` 200000), `ThreadLimit 20000` (у `event` 100000) **[Apache-док]**.
- `MaxConnectionsPerChild 0` — процессы не пересоздаются; ненулевое значение ограничивает утечки памяти, но для 1С каждое пересоздание процесса — новый экземпляр модуля и новый пул соединений с кластером **[Apache-док, практика]**.
- Переполнение: запросы сверх `MaxRequestWorkers` ждут в очереди ядра (`ListenBackLog`, по умолчанию 511), а в журнале один раз за запуск появляется `server reached MaxRequestWorkers setting, consider raising the MaxRequestWorkers setting` (`AH00484` у `event`, `AH00286` у `worker`, `AH00161` у `prefork`) **[Apache-док, Apache-код]**. Подбор чисел, `mod_status`, `AsyncRequestWorkerFactor` — `03-…` и `../1c/05` §12.

## 9. Модули: загрузка и проверка

### 9.1. LoadModule, встроенные и загружаемые модули

- `LoadModule <идентификатор> <файл>` (модуль `mod_so`, контекст server config и virtual host) загружает модуль; `LoadFile <файл>` — просто библиотеку **[Apache-док `mod_so`]**.
- В Ubuntu строки `LoadModule` лежат в `mods-available/<имя>.load` с абсолютным путём `/usr/lib/apache2/modules/mod_<имя>.so`; все `.load` читаются раньше любых настроек **[Debian]**.
- Встроенные модули (`core`, `mod_so`, `http_core`, `mod_log_config`, `mod_logio`, `mod_unixd`, `mod_version`, `mod_watchdog`, в 26.04 ещё `mod_systemd`) загружать нельзя и не нужно: строка `LoadModule unixd_module …`, скопированная из инструкции для RHEL, даст ошибку `module unixd_module is built-in and can't be loaded` **[Debian, Apache-код `mod_so.c`]**.
- `sudo apache2ctl -M` помечает модули `(static)` и `(shared)`; `apache2ctl -l` — только встроенные **[Apache-док]**.
- Идентификатор модуля (`ssl_module`) и имя файла исходника (`mod_ssl.c`) — две формы, которые принимает `<IfModule>` **[Apache-док]**.
- Модули сторонних пакетов (`libapache2-mod-*`) кладут свои `.load` и включаются сценариями пакета; модуль 1С — исключение, его подключает `webinst` строкой в `apache2.conf` **[Debian, `../1c/05`]**.

Включение и проверка модуля:

```bash
sudo a2enmod headers proxy proxy_http                # зависимости .load (# Depends:) включатся сами
sudo apache2ctl configtest && sudo systemctl restart apache2
sudo apache2ctl -M | grep -E 'headers|proxy'          # headers_module (shared), proxy_module (shared), proxy_http_module (shared)
```

### 9.2. Модуль 1С в Apache

- Строку загрузки пишет `webinst` (или вы при ручной публикации): `LoadModule _1cws_module "/opt/1cv8/x86_64/8.3.27.2074/wsap24.so"` (`../1c/05` §4.3); блоки публикаций обрабатывает обработчик `1c-application` (`SetHandler 1c-application`) **[`../1c/05`]**.
- В одном экземпляре Apache модуль загружается **один раз**; вторая строка `LoadModule _1cws_module …` в другом файле даст `AH01574: module _1cws_module is already loaded, skipping`, и работать будет тот, что встретился первым (порядок — раздел 4.1) **[Apache-код `mod_so.c`, `../1c/05` §4.4]**. Разные версии платформы — разные экземпляры Apache (раздел 3.5) **[ИТС-адм разд. 8.2]**.
- Путь содержит номер версии платформы. После обновления платформы и удаления старого каталога Apache не запустится: `Cannot load /opt/1cv8/x86_64/<старая версия>/wsap24.so into server: … cannot open shared object file: No such file or directory` — исправьте путь во всех местах (`grep -rn _1cws_module /etc/apache2*/`), проверьте `configtest`, перезапустите (`restart`, не `reload`, — меняется загруженный модуль) **[Apache-код `mod_so.c`, практика]**.
- Модуль для другой версии API Apache (например, `wsap22.so` от Apache 2.2) не загрузится: `API module structure '…' in file … is garbled - expected signature … - perhaps this is not an Apache module DSO, or was compiled for a different Apache version?` На Ubuntu нужен только `wsap24.so` **[Apache-код `mod_so.c`, `../1c/05` §3.4]**.
- Если не хватает системных библиотек платформы — та же ошибка `Cannot load …` с именем недостающей библиотеки: `ldd /opt/1cv8/x86_64/8.3.27.2074/wsap24.so | grep 'not found'` **[практика]**.
- Права: пользователю, от имени которого работает Apache (`www-data`), нужны чтение и выполнение на каталог исполняемых файлов версии платформы; для файловой базы — изменение каталога базы **[ИТС-адм разд. 8.4.2.1]**. Проверка: `sudo -u www-data test -r /opt/1cv8/x86_64/8.3.27.2074/wsap24.so && echo ok`; цепочка прав — `namei -l /opt/1cv8/x86_64/8.3.27.2074/wsap24.so` (подробно — `../1c/05` §6).
- Результат: `sudo apache2ctl -M | grep 1cws` → `_1cws_module (shared)`.
- На 26.04 модуль может не работать из-за ограничений юнита (`MemoryDenyWriteExecute=yes`) — `../1c/05` §6.1.

### 9.3. Типовые сообщения при загрузке модулей

Сообщения `mod_so` и что они значат **[Apache-код `mod_so.c`, `config.c`]**: `Invalid command '<директива>', perhaps misspelled or defined by a module not included in the server configuration` — модуль директивы не включён; `Cannot load <файл> into server: <ошибка загрузчика>` — нет файла, прав или библиотек; `Can't locate API module structure '<имя>' in file …` — неверный идентификатор в `LoadModule`; `API module structure … is garbled …` — модуль от другой версии Apache; `module <имя> is already loaded, skipping` (AH01574) — дубль; `module <имя> is built-in and can't be loaded` — модуль встроен. Действия — в таблице «Типичные ошибки» (строки 3, 5, 12, 13).

## 10. Имя сервера: ServerName, AH00558, UseCanonicalName

`ServerName [схема://]имя|IP-адрес[:порт]` (server config, virtual host) **[Apache-док `core`]**:

- в хостах по имени — то, что должно стоять в `Host`, чтобы запрос попал в хост (вместе с `ServerAlias`); если в `<VirtualHost *:порт>` его нет — наследуется имя основного сервера, а у хоста на точном IP — имя, полученное обратным разрешением этого адреса **[Apache-код `vhost.c`]**;
- основа самоссылающихся адресов при `UseCanonicalName On`; при `Off` (по умолчанию) Apache берёт имя и порт из запроса клиента (`DNS` — обратное разрешение, для старых клиентов без `Host`);
- за устройством, снимающим TLS (обратный прокси, балансировщик), указывайте схему и порт клиентов: `ServerName https://1c.corp.example:443` — иначе перенаправления уйдут на `http://`;
- IPv6-адрес в `ServerName` не поддерживается (ошибка запуска даже в скобках).

Откуда **AH00558**. Без глобального `ServerName` Apache при запуске вычисляет имя сам **[Apache-код `server/util.c`, `ap_get_local_host`]**: берёт имя хоста (`gethostname`), разрешает его в адрес и обратно; если обратное имя содержит точку — использует его молча. Иначе берёт имя хоста с точкой, IP-адрес или `127.0.0.1` и пишет на уровне `alert`: `AH00558: apache2: Could not reliably determine the server's fully qualified domain name, using <имя>. Set the 'ServerName' directive globally to suppress this message`. Для ВМ с коротким именем `srv-1c-app` без домена в `/etc/hosts` сообщение будет при каждом запуске; сервер при этом работает **[Debian `README.Debian`, п. 1 «Common Problems»]**.

```bash
# способ 1 (рекомендуется): глобальное имя
echo 'ServerName srv-1c-app.corp.example' | sudo tee /etc/apache2/conf-available/local-servername.conf
sudo a2enconf local-servername && sudo apache2ctl configtest      # Syntax OK — без AH00558
# способ 2: полное имя системы (обратное разрешение вернёт FQDN)
hostname -f; getent hosts "$(hostname)"
#   строка в /etc/hosts:  127.0.1.1  srv-1c-app.corp.example srv-1c-app
```

`README.Debian` предлагает простейший вариант `ServerName 127.0.0.1`; полное имя полезнее — его видно в перенаправлениях и в `apache2ctl -S` **[Debian, практика]**. Имя, по которому пользователи открывают публикацию 1С, задаётся в её виртуальном хосте и сертификате (`02-…`), а не в глобальном `ServerName` **[практика]**.

## 11. Виртуальные хосты

### 11.1. Как Apache выбирает хост

**[Apache-док `vhosts/details`]**:

**Фаза 1 — по адресу и порту соединения** (один раз на TCP-соединение). Приоритет, первое совпадение побеждает, более низкие уровни уже не рассматриваются — **даже если там есть хост с подходящим `ServerName`**:

| Приоритет | Вид | Пример |
|---|---|---|
| 1 | точный IP, точный порт | `<VirtualHost 10.0.0.5:80>` |
| 2 | точный IP, любой порт | `<VirtualHost 10.0.0.5:*>` |
| 3 | любой адрес, точный порт | `<VirtualHost *:80>` |
| 4 | любой адрес, любой порт | `<VirtualHost *:*>` |
| 5 | основной сервер (ни один хост не подошёл) | — |

**Фаза 2 — по имени** (на каждый запрос, даже внутри одного keep-alive-соединения): только если на фазе 1 совпало несколько хостов одного уровня. Имя из `Host` (для HTTPS — из SNI) сравнивается с `ServerName` и `ServerAlias` хостов **в порядке их появления в конфигурации**, первое совпадение выигрывает (у шаблонов `*` нет приоритета перед точными именами). Ничего не совпало — используется **первый** из этих хостов: он и есть хост по умолчанию для данного IP:порта. Порт в заголовке `Host` игнорируется; запрос без `Host` (HTTP/1.0) получает первый хост.

Для HTTPS: если клиент не прислал SNI, все соединения на этот IP:порт получают сертификат **первого** хоста **[Apache-док]**.

Прочее: имена хостов в самой строке `<VirtualHost имя:80>` разрешаются при запуске, при неудаче хост отбрасывается — пишите IP или `*` **[Apache-док]**; `_default_` — синоним `*` **[Apache-док]**; директива `NameVirtualHost` из 2.2 в 2.4 ничего не делает и выдаёт `AH00548: NameVirtualHost has no effect and will be removed in the next release` — удалите её из старых конфигураций **[Apache-код `vhost.c`]**.

### 11.2. Хосты по имени — основной способ

Несколько сайтов на одном адресе и порту, различаются только именем — так устроены все примеры статей базы (`../redmine/02-…`, `../netbox/02-…`) **[Apache-док `vhosts/name-based`, Ubuntu]**:

```apache
# /etc/apache2/sites-available/redmine.conf
<VirtualHost *:80>
    ServerName  redmine.corp.example
    ServerAlias redmine
    ErrorLog  ${APACHE_LOG_DIR}/redmine-error.log
    CustomLog ${APACHE_LOG_DIR}/redmine-access.log combined
    # прокси к Puma 127.0.0.1:3000 — ../redmine/02-…, 03-…
</VirtualHost>
```

- У каждого хоста — свой `ServerName`; в DNS (или `hosts` клиентов) все имена указывают на один IP **[Apache-док]**.
- Если хост не задаёт `Timeout`, `KeepAlive`, `KeepAliveTimeout`, `MaxKeepAliveRequests`, `ServerAdmin`, `ReceiveBufferSize`, `SendBufferSize` — берётся итоговое значение основного сервера **[Apache-док `vhosts/details`]**.
- Отдельные журналы на хост упрощают разбор и отправку в Loki (`03-…`, `../observability/03-…`); хост без своего `CustomLog` пишет в `other_vhosts_access.log` (раздел 4.5).

### 11.3. Хосты по IP и смешанные конфигурации

- Хост на точном IP (`<VirtualHost 10.0.0.5:80>`) нужен, когда у сервера несколько адресов и сайт должен быть доступен только на одном, или когда на разных адресах разные наборы сайтов **[Apache-док `vhosts/ip-based`]**.
- `<VirtualHost>` **не** заставляет слушать адрес — нужен соответствующий `Listen` (раздел 4.4) **[Apache-док]**.
- **Ловушка смешивания** **[Apache-док `vhosts/details`]**: если есть `<VirtualHost 10.0.0.5:80>` и `<VirtualHost *:80>` с разными именами, все запросы на 10.0.0.5:80 уйдут в первый (приоритет 1), имена хостов из `*:80` для этого адреса не сработают. Типичный сценарий: в одном файле для публикации 1С написали `<VirtualHost 10.0.0.5:80>`, а сайты сервисов — `*:80` → «по имени redmine открывается 1С». Держите все хосты одного порта в одном виде (обычно `*:80`/`*:443`).
- Проверка: в `sudo apache2ctl -S` у точного адреса не будет строки `is a NameVirtualHost` (раздел 6.2).

### 11.4. Хост по умолчанию, «ловушка» для чужих имён, StrictHostCheck

Запросы по IP-адресу, по старым и случайным именам (сканеры, ошибочные DNS-записи) попадают в хост по умолчанию — первый для IP:порта. В Ubuntu это `000-default.conf` с `DocumentRoot /var/www/html` **[Debian]**. На серверах публикации и сервисов разумно сделать его «ловушкой», которая ничего не отдаёт **[практика]**:

```apache
# /etc/apache2/sites-available/000-default.conf (на srv-1c-app)
<VirtualHost *:80>
    ServerName srv-1c-app.corp.example
    ErrorLog  ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined
    # закрыть всё, включая публикации 1С, если они объявлены глобально (раздел 11.5):
    # <Location "/"> применяется после <Directory>, а при AuthMerging Off его Require заменяет более ранние
    <Location "/">
        Require all denied
    </Location>
</VirtualHost>
```

Проверка: `curl -sI http://<IP-сервера>/demo/` → `403`, а `curl -sI -H 'Host: 1c.corp.example' http://<IP-сервера>/demo/` → ответ публикации.

Альтернатива или дополнение — `StrictHostCheck On` (2.4.49+, server config или хост по умолчанию; в остальных хостах не действует): Apache ответит `400`, если имени нет ни в `ServerName`, ни в `ServerAlias`, ни в строке `<VirtualHost>` хостов, подходящих по адресу **[Apache-док `core`]**:

```bash
echo 'StrictHostCheck ON' | sudo tee /etc/apache2/conf-available/local-stricthost.conf
sudo a2enconf local-stricthost && sudo apache2ctl configtest && sudo systemctl reload apache2
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: unknown.example' http://127.0.0.1/     # 400
```

При `StrictHostCheck` запросы к самому серверу по `localhost`/`127.0.0.1` (проверки, `apache2ctl status`, `server-status`) тоже получат `400`, если этих имён нет в `ServerAlias` хоста по умолчанию — добавьте их. Подтверждено 20.10.2026 по коду `server/vhost.c` (`update_server_from_aliases`: исключений для `localhost` нет) **[Apache-код]**; ⚠ на стенде не проверялось.

### 11.5. Что хосты наследуют из основного сервера — публикации 1С на всех именах

Основной сервер (всё вне `<VirtualHost>`) служит базой для каждого хоста, причём независимо от того, где в файлах он описан: настройки основного сервера сливаются в хост после полного разбора конфигурации, «каталожные» настройки (`<Directory>` и т. п.) — тоже **[Apache-док `vhosts/details`]**. Для псевдонимов это видно в коде: при слиянии настроек сервера `mod_alias` объединяет списки `Alias` и `Redirect` хоста и основного сервера (`apr_array_append(…, overrides->aliases, base->aliases)`) **[Apache-код `mod_alias.c`]**.

Следствия **[практика]**:

- Блок публикации 1С, который `webinst` дописал в конец `apache2.conf` (`Alias "/demo" "/var/www/demo/"` + `<Directory>`), работает **во всех** виртуальных хостах этого Apache, которые сами не перехватывают путь `/demo`: по IP-адресу, по старому имени сервера, на любом сайте со своим `DocumentRoot`. Хост, где стоит `ProxyPass /` (сайт сервиса за прокси), публикацию не покажет: `mod_proxy` сопоставляет адрес раньше `mod_alias` (порядок обработчиков `translate_name`: у `mod_proxy` — `APR_HOOK_FIRST`, у `mod_alias` — `APR_HOOK_MIDDLE`) **[Apache-код `mod_proxy.c`, `mod_alias.c`]**.
- Чтобы публикация была только на своём имени: перенесите `Alias` и `<Directory>` внутрь `<VirtualHost>` сайта 1С (ручная публикация, `../1c/05` §4.6) или закройте остальные хосты (`<Location "/"> Require all denied` в «ловушке», как в 11.4).
- Строку `LoadModule _1cws_module` оставляйте глобальной: модули загружаются на весь сервер.
- То же касается всего, что включено через `conf-enabled/` и `mods-enabled/*.conf` (например, `/server-status` из `status.conf` есть на каждом хосте, но разрешён только локально).

### 11.6. Схемы для серверов пользователя

**`srv-1c-app` — публикация 1С** (MPM `worker`, сервисов нет) **[практика]**:

```
sites-enabled/000-default.conf   *:80   «ловушка»: Require all denied (11.4)
sites-enabled/1c.conf            *:80   ServerName 1c.corp.example → перенаправление на HTTPS (02-…)
sites-enabled/1c-ssl.conf        *:443  ServerName 1c.corp.example, сертификат, публикации 1С (Alias + Directory внутри хоста)
apache2.conf (конец)             LoadModule _1cws_module "/opt/1cv8/x86_64/<версия>/wsap24.so"
```

```apache
# /etc/apache2/sites-available/1c.conf — HTTP-часть; HTTPS-хост и сертификат — 02-…
<VirtualHost *:80>
    ServerName 1c.corp.example
    ErrorLog  ${APACHE_LOG_DIR}/1c-error.log
    CustomLog ${APACHE_LOG_DIR}/1c-access.log combined
    Redirect permanent / https://1c.corp.example/
</VirtualHost>
```

Если публикации остаются глобальными (как их записал `webinst`), «ловушка» в `000-default.conf` закроет их для прочих имён и IP, а `1c.conf`/`1c-ssl.conf` — откроют по своему имени (у них нет `<Location "/">` с запретом).

**`srv-itsm` / `srv-obs` — обратный прокси для сервисов** (MPM `event`):

```
sites-enabled/000-default.conf   *:80/*:443  «ловушка» (или StrictHostCheck On)
sites-enabled/redmine.conf       redmine.corp.example   → 127.0.0.1:3000 (Puma, ../redmine/02-…)
sites-enabled/netbox.conf        netbox.corp.example    → 127.0.0.1:8001 (gunicorn, ../netbox/02-…) или порт стенда 8090 (../netbox/05-…)
sites-enabled/glitchtip.conf     glitchtip.corp.example → 127.0.0.1:8000 (../observability/02-…)
```

Директивы прокси, заголовки `X-Forwarded-*`, таймауты и WebSocket — `03-…`; TLS — `02-…`. Второй обратный прокси в Docker на тех же 80/443 не ставьте: порты займёт тот, кто стартует первым (`../guides/09-…`) **[практика]**.

Проверка любой схемы:

```bash
sudo apache2ctl configtest && sudo apache2ctl -S
for h in 1c.corp.example redmine.corp.example unknown.example; do
  printf '%-24s ' "$h"; curl -s -o /dev/null -w '%{http_code}\n' -H "Host: $h" http://127.0.0.1/
done
```

## 12. Права: www-data, каталоги, журналы

- **root (родитель)** открывает порты ниже 1024 и журналы, читает закрытые ключи TLS (ключ — только root, `0600`; сертификат можно читать всем), загружает модули; **`www-data` (обработчики)** читает файлы сайтов и публикаций и выполняет модули, в том числе 1С; **группа `adm`** читает журналы (`root:adm 0640`) **[Debian `README.Debian`, `postinst`]**.
- `www-data` **не должен** писать в корень сайта: уязвимость приложения позволит подменить содержимое; несколько редакторов сайта — общая группа (`chgrp -R webmasters`, `chmod -R g=rwX`), а не `www-data` **[практика]**. `User root` не ставить: документация Ubuntu прямо предупреждает, что это создаёт большие дыры в безопасности **[Ubuntu `configure-apache2-settings`]**.
- Каталогу публикации 1С запись не нужна; запись нужна каталогу **файловой** базы — держите его вне `/var/www` (`/srv/1c/bases/…`), права — `../1c/05` §6.
- Не держите файлы для Apache в домашних каталогах: в Ubuntu 22.04+ они `750`, а в 26.04 `/home` для службы ещё и только для чтения, `/root` недоступен **[Debian, `../1c/05` §6]**.
- Читать журналы без `sudo`: `sudo usermod -aG adm <пользователь>`. Изменение групп `www-data` (например, `usermod -aG grp1cv8 www-data`) действует после `systemctl restart apache2` **[практика]**.

```bash
sudo -u www-data test -r /var/www/demo/default.vrd && echo 'vrd читается'
sudo -u www-data test -w /srv/1c/bases/buh && echo 'файловая база доступна на запись'
namei -l /var/www/demo/default.vrd                 # права по всей цепочке каталогов
ps -eo user,pid,ppid,cmd | grep [a]pache2          # родитель — root, остальные — www-data
```

## 13. AppArmor и ограничения systemd

- **AppArmor-профиля для Apache в Ubuntu по умолчанию нет**: в пакете `apache2` файлов в `/etc/apparmor.d/` нет. Профиль `/etc/apparmor.d/usr.sbin.apache2` вместе с модулем `mod_apparmor` (`mods-available/apparmor.load`, `/usr/lib/apache2/modules/mod_apparmor.so`) ставит отдельный пакет `libapache2-mod-apparmor`; пакет `apparmor-profiles` (24.04) содержит лишь подпрофиль `/etc/apparmor.d/apache2.d/phpsysinfo` и неактивный образец `/usr/share/apparmor/extra-profiles/usr.sbin.httpd2-prefork` (путь SUSE, сам не загружается) **[Ubuntu, списки файлов пакетов noble]**. ⚠ В каком режиме (enforce/complain) профиль `libapache2-mod-apparmor` загружается после установки, не проверялось.
- Проверка: `sudo aa-status | grep -i apache` — пусто, если профиля нет. Если профиль есть и мешает модулю 1С (нужны чтение и отображение в память `/opt/1cv8/**`, доступ к каталогам публикации и файловой базы): `sudo aa-complain /usr/sbin/apache2` (пакет `apparmor-utils`), повторить действие, смотреть `sudo journalctl -k | grep -i apparmor` **[Ubuntu `how-to/security/apparmor`, `../1c/05` §6.1]**.
- **Ограничения systemd в 26.04** (раздел 3.1) выполняют похожую роль «песочницы» и для 1С важнее AppArmor: разбор и drop-in — `../1c/05` §6.1. Оценка: `systemd-analyze security apache2`.
- SELinux в Ubuntu не используется; инструкции для РЕД ОС/RHEL с `semanage`/`setsebool` к Ubuntu не применимы (`../1c/05` §6.1) **[практика]**.

## 14. Регламент изменения конфигурации без обрыва

Порядок для любого изменения на рабочем сервере **[Apache-док `stopping`, Debian, практика]**:

```bash
# 0) копия текущей конфигурации (и экземпляров, если есть)
sudo tar -C /etc -czf /root/apache2-etc-$(date +%F-%H%M).tgz apache2 $(cd /etc && ls -d apache2-* 2>/dev/null)

# 1) правка — в sites-available / conf-available / mods-available, не в *-enabled
sudoedit /etc/apache2/sites-available/1c-ssl.conf

# 2) синтаксис и разбор
sudo apache2ctl configtest                         # Syntax OK
sudo apache2ctl -S 2>&1 | head -30                 # хосты на месте, нет AH00558 и неожиданных default server

# 3) применить мягко (если не менялись MPM, ServerLimit/ThreadLimit, конфликтные Listen, модули)
sudo systemctl reload apache2
#    иначе — в окно обслуживания:
# sudo systemctl restart apache2

# 4) проверить, что служба жива и отвечает
systemctl is-active apache2
sudo journalctl -u apache2 --since '-5 min' --no-pager
sudo tail -n 30 /var/log/apache2/error.log
curl -sI -H 'Host: 1c.corp.example' http://127.0.0.1/ | head -3

# 5) откат при проблеме
# sudo a2dissite <сайт>  или  sudo tar -C /etc -xzf /root/apache2-etc-<дата>.tgz
# sudo apache2ctl configtest && sudo systemctl reload apache2
```

Заметки:

- Если `reload` «ничего не изменил» — проверьте, что правили файл, который действительно подключён (`apache2ctl -t -D DUMP_INCLUDES`), и что изменение не из списка «только полным перезапуском» (раздел 3.3).
- Если после `reload` служба упала (синтаксис верен, но ресурс недоступен — порт, файл сертификата): `systemctl status apache2`, `journalctl -u apache2`, исправить и `systemctl start apache2`.
- Изменения `default.vrd` публикации 1С применяются после перезагрузки Apache (`reload` или `restart`); когда именно модуль перечитывает дескриптор, документация 1С не говорит, поэтому `../1c/05` (§4.6) советует надёжный `restart` ⚠.
- Для отслеживания изменений `/etc` пригодится `etckeeper` (советует `README.multiple-instances`) **[Debian]**.

## Типичные ошибки (симптом → причина → решение)

| # | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | `AH00558: apache2: Could not reliably determine the server's fully qualified domain name, using …` | нет глобального `ServerName`, обратное разрешение не даёт FQDN | `conf-available/local-servername.conf` + `a2enconf` или FQDN в `/etc/hosts`; сервер работает (раздел 10) **[Apache-код, Debian]** |
| 2 | Не стартует: `(98)Address already in use: AH00072: make_sock: could not bind to address [::]:80`, `no listening sockets available, shutting down` | порт занят (nginx, второй экземпляр, контейнер) или пересекающиеся `Listen` (`80` и `10.0.0.5:80`; точный повтор даёт другую ошибку — `Cannot define multiple Listeners on the same IP:port`, 4.4) | `sudo ss -ltnp 'sport = :80'`; `grep -rn '^\s*Listen' /etc/apache2/`; у `apache2@` — свой порт (3.5) **[Apache-док, Apache-код]** |
| 3 | `AH00534: apache2: Configuration error: More than one MPM loaded.` / `No MPM loaded.` | две ссылки `mpm_*.load` или ни одной | `ls -l /etc/apache2/mods-enabled/mpm_*`; оставить один MPM (8.4) **[Apache-док, Apache-код]** |
| 4 | `ERROR: Module mpm_event is enabled - cannot proceed due to conflicts.` | включение второго MPM (`# Conflicts:`) | сначала `a2dismod mpm_event` **[Debian]** |
| 5 | `Invalid command 'ProxyPass', perhaps misspelled or defined by a module not included in the server configuration` (`ManagedApplicationDescriptor`, `SSLEngine`, `Header`…) | модуль не включён (`proxy`, модуль 1С, `ssl`, `headers`) | `a2enmod <модуль>`; для 1С — строка `LoadModule _1cws_module` (9.2) **[Apache-код]** |
| 6 | `bad user name ${APACHE_RUN_USER}`, `AH00111: Config variable ${APACHE_RUN_DIR} is not defined` | `/usr/sbin/apache2` запущен напрямую, без `envvars` | только `apache2ctl` / `systemctl` (6.1) **[Debian, Apache-код]** |
| 7 | `AH00526: Syntax error on line N of <файл>:` | опечатка, директива не в своём контексте, комментарий в конце строки, незакрытая секция | исправить строку N; `apache2ctl configtest` (7.1, 7.5) **[Apache-код]** |
| 8 | По имени открывается другой сайт или страница по умолчанию | имя не совпало (ушёл в первый хост); хост на точном IP перехватывает адрес; сайт не включён | `sudo apache2ctl -S`; `curl -sI -H 'Host: <имя>' http://127.0.0.1/`; все хосты порта — вида `*:80` (11.1–11.3) **[Apache-док]** |
| 9 | Публикация 1С открывается по IP и чужим именам | публикация в основном контексте наследуется хостами | перенести в хост 1С или «ловушка» и `StrictHostCheck On` (11.4–11.5) **[Apache-код, практика]** |
| 10 | `ERROR: Site mysite does not exist!` или после правки «ничего не изменилось» | файл без `.conf`; не было `reload`; правился неподключённый файл; нужен полный перезапуск (`ServerLimit`, `ThreadLimit`, `Listen`, MPM, `envvars`) | `sudo apache2ctl -t -D DUMP_INCLUDES`; `reload`/`restart` по 3.3 **[Debian, Apache-док]** |
| 11 | После установки пакета публикация 1С ест память, ошибки блокировок файловой базы | `libapache2-mod-php*` переключил MPM на `prefork` | `a2query -M`; `php-fpm` вместо `mod_php`, вернуть `worker` (8.3) **[Debian]** |
| 12 | После обновления платформы 1С: `Cannot load /opt/1cv8/x86_64/<версия>/wsap24.so into server: … cannot open shared object file` | путь к удалённой версии или нет библиотек | `grep -rn _1cws_module /etc/apache2*/`, `ldd …/wsap24.so`, `configtest`, `restart` (9.2) **[Apache-код, практика]** |
| 13 | `AH01574: module _1cws_module is already loaded, skipping` | `LoadModule` модуля 1С дважды | оставить одну строку (9.2) **[Apache-код]** |
| 14 | После перехода на 26.04 веб-клиент 1С не открывается | «закалка» юнита (`MemoryDenyWriteExecute=yes` и др.) | drop-in из `../1c/05` §6.1 **[Debian]** |
| 15 | `403`, в журнале `AH01630: client denied by server configuration` | доступ закрыт `Require` (каталог без своего `<Directory>`, «ловушка», `Require ip`) | `sudo grep -rn 'Require' /etc/apache2/`; `<Directory "/путь"> Require all granted </Directory>` (7.6) **[Apache-код, Debian]** |
| 16 | `403`, в журнале `AH00035: access to … denied … because search permissions are missing on a component of the path` | у `www-data` нет `x` на каталог пути (часто `/home/<user>`) | `namei -l <путь>`; файлы — не в `/home` (12) **[Apache-код]** |
| 17 | `.htaccess` не действует / `500` и `<директива> not allowed here` | `AllowOverride None` / класс директивы не разрешён | разрешить класс или перенести правила в конфигурацию (7.7) **[Apache-док, Apache-код]** |
| 18 | `AH00156: Couldn't create pollset in child; check system or user limits (prefork; у worker — AH03285 …in thread…, у event — AH00495 Couldn't create a Thread Safe Pollset…; уточнено 20.10.2026 по коду 2.4.x)` | мало `fs.epoll.max_user_instances` | поднять (`README.Debian` приводит `1024`), `../linux/09-…` **[Debian]** |
| 19 | `/var/lock/apache2 already exists but is not a directory owned by www-data` | сменили `APACHE_RUN_USER` или владельца каталога | вернуть `www-data` или `chown` (4.3) **[Debian]** |
| 20 | `systemctl stop`/`restart` идёт до полутора минут (26.04) | мягкая остановка (`KillSignal=SIGWINCH`) ждёт длинных запросов 1С до `TimeoutStopSec` | `GracefulShutdownTimeout 30` (3.3–3.4) **[Apache-док, Debian, практика]** |
| 21 | Apache перезапустился сам днём | автоматическое обновление `apache2` | `grep apache2 /var/log/apt/history.log`; окно обновлений (1.3) **[практика]** |
| 22 | `AH00548: NameVirtualHost has no effect and will be removed in the next release` | директива из 2.2 | удалить **[Apache-код]** |

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Версия Apache и пакета | `apache2 -v`; `apt policy apache2` |
| Закрыта ли уязвимость | `zgrep -n 'CVE-2026-XXXXX' /usr/share/doc/apache2/changelog.Debian.gz` |
| Установить | `sudo apt install -y apache2` |
| Проверить синтаксис | `sudo apache2ctl configtest` |
| Хосты и пути | `sudo apache2ctl -S` |
| Какие файлы подключены | `sudo apache2ctl -t -D DUMP_INCLUDES` |
| Загруженные модули | `sudo apache2ctl -M` (встроенные — `apache2ctl -l`) |
| Текущий MPM | `a2query -M`; `sudo apache2ctl -V \| grep -i mpm` |
| Сменить MPM на worker | `sudo a2dismod mpm_event && sudo a2enmod mpm_worker && sudo apache2ctl configtest && sudo systemctl restart apache2` |
| Включить модуль | `sudo a2enmod <модуль> && sudo apache2ctl configtest && sudo systemctl restart apache2` |
| Включить сайт | `sudo a2ensite <сайт> && sudo apache2ctl configtest && sudo systemctl reload apache2` |
| Включить свой фрагмент | `sudo a2enconf local-<имя> && sudo apache2ctl configtest && sudo systemctl reload apache2` |
| Перечитать без обрыва | `sudo systemctl reload apache2` |
| Полный перезапуск | `sudo systemctl restart apache2` |
| Состояние и журнал службы | `systemctl status apache2 --no-pager`; `sudo journalctl -u apache2 -b` |
| Журнал ошибок | `sudo tail -f /var/log/apache2/error.log` |
| Юнит и drop-in | `systemctl cat apache2`; `sudo systemctl edit apache2`; `sudo systemctl revert apache2` |
| Убрать AH00558 | `echo 'ServerName <FQDN>' \| sudo tee /etc/apache2/conf-available/local-servername.conf && sudo a2enconf local-servername` |
| Проверить хост по имени | `curl -sI -H 'Host: 1c.corp.example' http://127.0.0.1/` |
| Порты | `ss -ltnp \| grep apache2` |
| Профили ufw | `sudo ufw app list`; `sudo ufw allow 'Apache Full'` |
| Новый экземпляр | `sudo sh /usr/share/doc/apache2/examples/setup-instance <имя>`; порт в `/etc/apache2-<имя>/ports.conf`; `sudo systemctl enable --now apache2@<имя>` |
| Права «глазами» Apache | `sudo -u www-data test -r <файл> && echo ok`; `namei -l <путь>` |
| Модуль 1С | `sudo apache2ctl -M \| grep 1cws`; `grep -rn _1cws_module /etc/apache2*/` |
| AppArmor | `sudo aa-status \| grep -i apache` |
| Копия конфигурации | `sudo tar -C /etc -czf /root/apache2-etc-$(date +%F).tgz apache2` |

## Источники

Apache HTTP Server **[Apache-док, Apache-код, Apache-CL]**:

- https://httpd.apache.org/ (текущий выпуск, конец 2.2, TLS 1.3), https://downloads.apache.org/httpd/CHANGES_2.4, https://httpd.apache.org/security/vulnerabilities_24.html (уязвимости и даты выпусков);
- исходники документации ветки 2.4.x — https://raw.githubusercontent.com/apache/httpd/2.4.x/docs/manual/: `mod/core.xml`, `mod/mpm_common.xml`, `mod/event.xml`, `mod/worker.xml`, `mod/prefork.xml`, `mod/mod_so.xml`, `mod/mod_unixd.xml`, `mod/mod_version.xml`, `mod/mod_macro.xml`, `mod/mod_systemd.xml`, `mod/mod_info.xml`, `mod/mod_authz_core.xml`, `configuring.xml`, `sections.xml`, `howto/htaccess.xml`, `vhosts/{name-based,ip-based,details}.xml`, `mpm.xml`, `stopping.xml`, `bind.xml`, `upgrading.xml`, `expr.xml`, `programs/httpd.xml`, `platform/windows.xml`;
- исходный код 2.4.x — https://raw.githubusercontent.com/apache/httpd/2.4.x/: `server/{util,vhost,core,main,config,mpm_common,listen,request}.c`, `modules/core/mod_so.c`, `modules/mappers/mod_alias.c`, `modules/proxy/mod_proxy.c`, `modules/aaa/mod_authz_core.c`, MPM `event.c`, `worker.c`, `prefork.c` (тексты и коды сообщений `AH…`, приведённые в статье).

Пакет Debian/Ubuntu **[Debian, Ubuntu]**:

- salsa.debian.org, `apache-team/apache2`, метки `debian/2.4.52-1`, `debian/2.4.58-1`, `debian/2.4.66-2`: `apache2.README.Debian`, `README.multiple-instances`, `apache2ctl`, `a2enmod`, `apache2.postinst`, `setup-instance`, `apache2.service`, `apache2@.service`, `apache2.logrotate`, `apache2.links`, `apache2.dirs`, `rules`, `apache2-utils.ufw.profile`, `config-dir/` (`apache2.conf.in`, `envvars`, `ports.conf`, `conf-available/`, `mods-available/`, `sites-available/000-default.conf`); `php-team/php`, ветка `debian/main/8.3`: `libapache2-mod-php.postinst.extra`, `php-fpm.apache2`;
- https://packages.ubuntu.com/ — версии и списки файлов (`apache2`, `apache2-bin`, `apache2-utils`, `apache2-doc`, `libapache2-mod-*`, `apparmor-profiles`, `ssl-cert`, `php8.3-fpm`) для jammy/noble/resolute/questing; https://changelogs.ubuntu.com/changelogs/pool/main/a/apache2/ — журналы `2.4.52-1ubuntu4.25`, `2.4.58-1ubuntu8.17`, `2.4.66-2ubuntu2.6`; https://manpages.ubuntu.com/manpages/noble/ — `a2enmod(8)`, `a2ensite(8)`, `a2enconf(8)`, `apache2ctl(8)`, `a2query(1)`, `apache2(8)`;
- документация Ubuntu Server: https://documentation.ubuntu.com/server/how-to/web-services/install-apache2/, `…/configure-apache2-settings/`, `…/use-apache2-modules/`, `…/how-to/security/apparmor/`.

1С **[ИТС-адм]**: «Руководство администратора» 8.3.27, глава 8 — разделы 8.1, 8.2, 8.4.2.1, 8.10.1.1, 8.10.1.2.3; конспекты `../its-docs/adm-gl08-veb-servery-p1.md`, `…-p2.md`.

Статьи базы: `../1c/05-…`, `../linux/04-…`, `../linux/08-…`, `../redmine/02-…`, `../netbox/02-…`, `../netbox/05-…`, `../observability/02-…`, `../guides/09-…`.

Дополнительно при независимой сверке 20.10.2026:

- httpd 2.4.x: `configure.in` (умолчание `--enable-v4-mapped`), `server/listen.c` (`alloc_listener`, `match_address`, `open_listeners`, `IPV6_V6ONLY`), `server/vhost.c` (`update_server_from_aliases`, имя хоста без `ServerName`), `server/mpm/worker/worker.c` (`set_server_limit`, `set_threads_per_child`), `modules/arch/unix/mod_systemd.c`; раздел 2.3.9 в `CHANGES_2.4` (умолчание `AllowOverride None`);
- Debian `apache2`: `debian/changelog` метки `debian/2.4.66-2` (записи 2.4.4-2, 2.4.54-5, 2.4.64-2, 2.4.65-3, 2.4.66-1), `debian/a2query.in`, `config-dir/mods-available/mpm_*.conf` метки `debian/2.4.58-1`; `php-team/php` ветка `debian/main/8.3` — `debian/php-fpm.postinst.extra`; журналы Ubuntu `2.4.64-1ubuntu3.5` (questing) и записи `2.4.52-1ubuntu1` (jammy: отброшенные правки `apache2ctl`), `2.4.66-2ubuntu1` (resolute: профиль ufw перешёл в Debian 2.4.60-1); https://packages.ubuntu.com/ — `apache2-bin` (зависимость от `libsystemd0` в resolute), `stonking/apache2`, поиск по всем выпускам;
- systemd: `man/systemd.service.xml` (`ExecStop`), `man/systemd.kill.xml` (`KillMode=mixed`), `man/systemd-system.conf.xml` и `meson_options.txt` (`default-timeout-sec = 90`) — raw.githubusercontent.com/systemd/systemd/main; man `dash(1)` (manpages.ubuntu.com, noble) — `ulimit`;
- ИТС: полный текст главы 8 «Руководства администратора» 8.3.27 (разделы 8.1, 8.2, 8.4.2.1, 8.10.1.1, 8.10.1.2.2–8.10.1.2.3).

## Что не удалось подтвердить

- ⚠ **Юнит пакета Ubuntu 26.04** напрямую не читался (Launchpad недоступен): «закалка», `Type=notify`, `KillSignal=SIGWINCH`, `Restart=on-abnormal` — по метке Debian `debian/2.4.66-2` и журналу Ubuntu (рецензент 20.10.2026 подтвердил косвенно: изменений юнита в записях Ubuntu нет, `apache2-bin` зависит от `libsystemd0`). Проверка: `systemctl cat apache2`. Встроенность `mod_systemd` уточнена (раздел 2.3); на сервере — `apache2ctl -l | grep systemd`.
- ⚠ **`LimitRequestBody` на 22.04** — вероятно, 0: изменение 2.4.54 в журнале jammy не упомянуто, а патч CVE-2022-29404 там затрагивает только `mod_lua` (`lua_request.c`), не умолчание в `core`. Проверка: загрузить файл больше 1 ГиБ.
- ⚠ **5 из 20 CVE выпуска 2.4.69** (`mod_charset_lite`, `mod_auth_digest` -48005, `mod_session`, `mod_heartmonitor`, `mod_dav` -42528), а также CVE-2026-42356 для 26.04 — в журналах Ubuntu на 20.10.2026 не упомянуты, трекер не ответил; ещё три к пакетам Ubuntu неприменимы по версии или платформе (раздел 1.3).
- ⚠ **Поведение `unattended-upgrades`** при изменённом `apache2.conf`; режим перезапуска при обновлении (restart) уточнён по журналу Debian, на сервере не проверялся.
- ⚠ **Немягкая остановка на 22.04/24.04** через `systemctl stop` — подтверждена по документации systemd и Apache, на сервере не проверялась.
- ⚠ **`ServerLimit 1` и `graceful`** — возможное ожидание новых запросов; **модуль 1С и `event`** — только практика; обратная замена `Listen 80` → `Listen 127.0.0.1:80` при `reload` — вывод по коду `listen.c`.
- ⚠ **Блок публикации от `webinst`** (`AllowOverride All`) — по `../1c/05` §4.3; `webinst -confpath` в экземпляр `apache2@`; перечитывание `default.vrd` при `reload`; влияние `LANG` на модуль 1С.
- ⚠ **Режим профиля `libapache2-mod-apparmor`**, пример `mod_macro` и вывод `apache2ctl -S`, права каталога `/var/log/apache2` (у экземпляров `setup-instance` ставит `750 root:adm`, у основного каталога права в прочитанных файлах пакета не заданы), последствия `apt purge` и `--force-confmiss`, поведение `StrictHostCheck` для `localhost` (по коду подтверждено) — на сервере не проверялись. Содержимое профиля ufw (`Apache`, `Apache Secure`, `Apache Full`) рецензент не прочитал: файл в salsa закрыт проверкой браузера.
- Закрыто рецензентом 20.10.2026: встроенность `mod_systemd` в 26.04, `ulimit -n` (оба предела, man `dash`), «последнее значение побеждает» для директив MPM (код MPM), умолчание `TimeoutStopSec` 90 с, команды включения `php-fpm`, один сокет на IPv4/IPv6 для `Listen 80`, режим перезапуска при обновлении пакета, `StrictHostCheck` и `localhost` (по коду).
