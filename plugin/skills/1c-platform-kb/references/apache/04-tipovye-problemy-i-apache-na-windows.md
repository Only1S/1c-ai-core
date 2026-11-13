# Apache: типовые проблемы (симптом → причина → решение), диагностика и Apache на Windows

> **Официальные тексты по теме**: документация Apache HTTP Server 2.4 — `programs/httpd.html`, `programs/apachectl.html`, `logs.html`, `bind.html`, `mod/core.html`, `mod/mpm_common.html`, `mod/mpm_winnt.html`, `mod/mod_proxy.html`, `mod/mod_proxy_http.html`, `mod/mod_ssl.html`, `platform/windows.html`, `CHANGES_2.4`; пакет Debian/Ubuntu `apache2` — `README.Debian`, `NEWS.Debian`, `apache2ctl`, `envvars`. По 1С — конспекты `../its-docs/adm-gl08-veb-servery-p1.md`, `../its-docs/adm-gl08-veb-servery-p2.md` (гл. 8 «Настройка веб-серверов»: 8.2, 8.3.1, 8.10.1 Apache, 8.10.3 Reverse Proxy), `../its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md` и методичка ИТС 5978 «Настройка веб-сервера Apache под Windows» (2020). При расхождении по вопросам 1С правы конспекты ИТС, по вопросам Apache — документация и исходный код выпуска 2.4.x.

> Статус: проверено независимой сверкой 20.10.2026: тексты и уровни около 120 сообщений журнала (около 95 кодов `AHxxxxx` и тексты без кода) — с исходным кодом ветки `2.4.x` (выпуск **2.4.69** от 01.10.2026) и метками `2.4.52`/`2.4.58`; директивы, умолчания и контексты — с исходниками документации 2.4.x (`core`, `mpm_common`, `mpm_winnt`, `mod_proxy`, `mod_proxy_http`, `mod_ssl`, `mod_reqtimeout`, `mod_log_config`, `platform/windows` и др.); `CHANGES_2.4` и страница уязвимостей; файлы пакета Debian (`debian/2.4.58-1`, `debian/2.4.66-2`), списки файлов и журналы изменений Ubuntu 22.04/24.04/26.04; README и код mod_auth_gssapi 1.6.4, MIT krb5; страница Apache Lounge; ИТС «Руководство администратора» гл. 8 и методичка 5978. Исправлено 14 ошибок (контекст сообщения `mod_auth_gssapi` для SPNEGO, уровень `AH10510`, текст `AH01916`, пароль ключа в Ubuntu через `systemd-ask-password`, лимиты заголовков при именных хостах, ограничения юнита 26.04 и др.), закрыто 8 пометок; на сервере не проверялось. Пакеты Ubuntu содержат заплатки безопасности поверх этих версий, поэтому отдельные формулировки у вас могут отличаться — ищите в журнале по коду `AHxxxxx` и по ключевым словам, а не по всей строке.

> Область: поиск и устранение неисправностей Apache HTTP Server 2.4 в Ubuntu Server 22.04 / 24.04 / 26.04 (пакет `apache2`): не запускается, не перечитывает конфигурацию, отвечает 4xx/5xx, сбои обратного прокси, TLS и Kerberos, последствия обновлений пакета и ОС; кратко — Apache 2.4 на Windows (сторонние сборки, служба, раскладка, права, брандмауэр, журнал событий). Применительно к стенду: `srv-1c-app` — Apache с модулем 1С `wsap24.so` (публикация `/demo`), `srv-itsm` — Redmine (Puma на `127.0.0.1:3000`) и NetBox (gunicorn на `127.0.0.1:8001`) за Apache или nginx, `srv-obs` — GlitchTip (`127.0.0.1:8000`) и Grafana. | Версии: Apache 2.4.69 (текущий выпуск ASF); Ubuntu 22.04 — `2.4.52-1ubuntu4.24`, 24.04 — `2.4.58-1ubuntu8.16`, 26.04 — `2.4.66-2ubuntu2.6` (packages.ubuntu.com, 20.10.2026); Windows — Apache Lounge `httpd-2.4.69-261002-Win64-VS18` (02.10.2026). | Актуальность: 2026-10-20

Пометки в тексте:

- **[Apache-док]** — документация Apache HTTP Server 2.4 (httpd.apache.org/docs/2.4 и её исходники XML в ветке `2.4.x`), журнал `CHANGES_2.4`, страница уязвимостей;
- **[Apache-код]** — исходный код ветки `2.4.x` (точные тексты сообщений, коды `AHxxxxx`, уровни журнала, коды ответа); сверено 20.10.2026;
- **[Ubuntu]** — documentation.ubuntu.com, packages.ubuntu.com, журналы изменений changelogs.ubuntu.com;
- **[Debian]** — файлы пакета `apache2` Debian (метка `debian/2.4.58-1` на salsa.debian.org): `README.Debian`, `NEWS.Debian`, `apache2ctl`, `envvars`, `apache2.conf.in`, `a2enmod`, `logrotate`;
- **[ИТС-адм разд. N]** — «Руководство администратора» 1С 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС;
- **[сторонний]** — документация и исходный код сторонних проектов (mod_auth_gssapi, MIT krb5, OpenSSL, curl, Apache Lounge, PHP);
- **[практика]** — опыт сообщества, первоисточником не подтверждён;
- **⚠** — не подтверждено, с пояснением что именно.

Связанные статьи (их тему здесь не повторяем):

- `apache/01-ustanovka-i-ustrojstvo.md` — установка, раскладка `/etc/apache2`, MPM, виртуальные хосты, `a2enmod`/`a2ensite`;
- `apache/02-https-bezopasnost-autentifikaciya.md` — TLS, certbot, заголовки безопасности, Basic/LDAP/Kerberos — **настройка**; здесь — только ошибки;
- `apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md` — настройка MPM под нагрузку, обратный прокси, форматы журналов, `mod_status`, отправка журналов в Loki;
- `../1c/05-veb-publikaciya-apache-nginx.md` — публикация 1С и её ошибки, юнит `apache2.service` в 26.04 (6.1), nginx (9), Kerberos для 1С (11.3);
- `../1c-windows/03-veb-publikaciya-iis.md`, раздел 13 — публикация 1С на Apache под Windows;
- `../linux/04-pakety-apt.md` — `unattended-upgrades`, `needrestart`, вопросы dpkg о конфигурационных файлах;
- `../linux/08-set-ssh-firewall.md` — `ss`, `curl`, `ufw`, разрешение имён;
- `../observability/03-loki-i-grafana.md` — сбор журналов в Loki.

Условные обозначения в командах: домен `example.local` — подставьте свой; публикация 1С — `/demo` в каталоге `/var/www/demo`; версия платформы — `8.3.27.XXXX`; команды выполняются администратором через `sudo`, процессы Apache в Ubuntu работают от `www-data`.

## Кратко — главные факты

1. **Первые четыре команды при любой неисправности:** `sudo apache2ctl configtest`, `systemctl status apache2 --no-pager`, `sudo journalctl -u apache2 -b --no-pager | tail -n 50`, `sudo tail -n 50 /var/log/apache2/error.log`. Ошибки разбора конфигурации выводятся на stderr **до** открытия журнала (флаг `APLOG_STARTUP`), поэтому в `error.log` их нет — только в выводе `configtest` и в journald [Apache-код].
2. **Не запускайте `/usr/sbin/apache2` напрямую.** Без `/etc/apache2/envvars` получите `AH00111: Config variable ${APACHE_RUN_DIR} is not defined` и `DefaultRuntimeDir must be a valid directory, absolute or relative to ServerRoot`; любые ключи `apache2` передавайте через `apache2ctl` [Debian `README.Debian`, Apache-код].
3. **Карта конфигурации:** `sudo apache2ctl -S` — виртуальные хосты по адресам и хост «по умолчанию»; `-M` — модули и MPM; `-t -D DUMP_INCLUDES` — дерево подключённых файлов; `-t -D DUMP_RUN_CFG` — пользователь, `PidFile`, мьютексы, `Define`; `-t -D DUMP_CERTS` — файлы сертификатов `mod_ssl` [Apache-код].
4. **`Invalid command 'X', perhaps misspelled or defined by a module not included in the server configuration`** почти всегда означает «модуль не включён»: `ProxyPass` → `a2enmod proxy proxy_http`, `SSLEngine` → `ssl`, `Header`/`RequestHeader` → `headers`, `ManagedApplicationDescriptor` → нет строки `LoadModule _1cws_module` [Apache-код].
5. **Порт занят:** `(98)Address already in use: AH00072: make_sock: could not bind to address [::]:80` → `no listening sockets available, shutting down` → `AH00015: Unable to open logs`. Кто держит порт — `sudo ss -tlnp 'sport = :80'`. На Windows то же выглядит как `(OS 10048)… AH00072` [Apache-код, Apache-док].
6. **403 + `AH01630: client denied by server configuration: <путь>`** — отказ правилами `Require`. В Debian/Ubuntu всё вне `/var/www` и `/usr/share` закрыто (`<Directory /> Require all denied`) — каталог вне них нужно явно разрешить [Debian `NEWS.Debian`, `apache2.conf`]. **403 + `AH00035 … because search permissions are missing on a component of the path`** — права файловой системы (`namei -l <путь>`) [Apache-код].
7. **Многие причины 4xx и сбои TLS пишутся на уровне `info`/`debug`** — при штатном `LogLevel warn` их не видно: 404 `AH00128 File does not exist`, 413 `AH01588`/`AH01591`, 400 `AH00561` (слишком длинный заголовок), 414 `AH00565`, 408 `AH01382`, сбой рукопожатия `AH02008`. На время разбора включайте точечно: `LogLevel warn core:info ssl:info authz_core:debug` [Apache-код].
8. **«Proxy Error» в теле ответа** — ответил сам Apache (`mod_proxy`), а не бэкенд. 503 + `AH00957 … attempt to connect to 127.0.0.1:3000 … failed` + `AH00959 … disabling worker for (127.0.0.1:3000) for 60s` — бэкенд не принял соединение; следующие 60 секунд Apache отвечает 503 сразу (`AH00940`), даже если бэкенд уже поднялся. Параметр `retry=` у `ProxyPass` (по умолчанию 60) [Apache-док, Apache-код].
9. **Таймаут ответа бэкенда в Apache — это 502, а не 504:** `(70007)The timeout specified has expired: AH01102: error reading status line from remote server …` и `AH00898: Error reading from remote server returned by /…`. Срок — `ProxyTimeout` или параметр `timeout=` у `ProxyPass`; по умолчанию равен `TimeOut` (в Ubuntu 300 с). 504 Apache отдаёт только при таймауте передачи **тела запроса** бэкенду и в туннелях; у nginx таймаут ответа — 504 [Apache-код, Debian].
10. **`AH01144: No protocol handler was valid for the URL …`** → 500: включён `proxy`, но не `proxy_http` (или не `proxy_wstunnel`/`proxy_fcgi` для своих схем) [Apache-код].
11. **Обрыв первого запроса после простоя** (`AH01102` с `(104)Connection reset by peer` или `(70014)End of file found`) — гонка keep-alive: бэкенд закрыл простаивающее соединение. Документированные средства — `SetEnv proxy-initial-not-pooled 1`, `disablereuse=On` или `ttl=` меньше таймаута простоя бэкенда [Apache-док].
12. **HTTPS не стартует:** `SSLCertificateFile: file '…' does not exist or is empty`, `AH02565: Certificate and private key … do not match`, `AH02564: Failed to configure encrypted (?) private key …` и `AH02580 … Pass phrase incorrect` — ключ с паролем: в Ubuntu его спрашивает `systemd-ask-password` (`SSLPassPhraseDialog exec:/usr/share/apache2/ask-for-passphrase`), и без оператора служба не запускается [Apache-код, Debian].
13. **Рукопожатие TLS не проходит** — включите `LogLevel ssl:info`: появятся `AH02008: SSL library error 1 in handshake (server …)` и `SSL Library Error: error:0A0000C1:SSL routines::no shared cipher` (или `…::unsupported protocol`, `…::http request`). Снаружи — `openssl s_client -connect хост:443 -servername хост -showcerts` [Apache-код, сторонний: OpenSSL 3.0].
14. **Браузер доволен сертификатом, а тонкий клиент 1С, `curl`, Java — нет:** сервер не отдаёт промежуточный сертификат (`Verify return code: 21 (unable to verify the first certificate)`). С 2.4.8 цепочка кладётся в `SSLCertificateFile` (сертификат + промежуточные), `SSLCertificateChainFile` устарела [Apache-док].
15. **`421 Misdirected Request` + `AH02032 … have no compatible SSL setup`** — имя из SNI и заголовок `Host` ведут в виртуальные хосты с разными настройками TLS. Ужесточение пришло с исправлением CVE-2025-23048 (Apache 2.4.64; в Ubuntu 22.04/24.04 — обновления 14.07.2025), ослаблено директивой `SSLVHostSNIPolicy` (Apache 2.4.66; в Ubuntu 22.04/24.04 — заплатка от 09.12.2025, LP #2117112) [Apache-док, Ubuntu].
16. **Kerberos (`mod_auth_gssapi`):** `GSS ERROR In Negotiate Auth: gss_accept_sec_context() failed: […(Request ticket server HTTP/… kvno N not found in keytab; keytab is likely out of date)]` — keytab устарел; `Clock skew too great` — время; браузер спрашивает пароль — нет билета (зона интрасети, SPN, обращение по IP) [сторонний: mod_auth_gssapi, MIT krb5].
17. **Большой билет Kerberos** (много групп в AD) даёт 400 с пояснением `Size of a request header field exceeds server limit.` и `AH00561` на уровне `info` — поднимите `LimitRequestFieldSize` (по умолчанию 8190) глобально или в первом хосте адреса:порта: при именных хостах значение берётся из хоста по умолчанию (раздел 4.4) [Apache-док, Apache-код].
18. **`systemctl restart apache2` при сломанной конфигурации остановит Apache и не запустит его.** `sudo systemctl reload apache2` (в 22.04–26.04 это `apachectl graceful`) и `sudo apache2ctl graceful`/`restart` сначала проверяют конфигурацию и при ошибке оставляют работать старые процессы. Правило: `sudo apache2ctl configtest && sudo systemctl restart apache2` [Debian `apache2ctl`, Apache-док].
19. **После обновления пакета:** `apt changelog apache2` (ищите `SECURITY REGRESSION`), сравнение `apache2ctl -M`/`-S` с сохранёнными до обновления, `curl` и `openssl s_client` по каждому сайту. Поведение меняли обновления безопасности: 403 `AH10508` (июль 2024), удаление `SSLEngine optional` (июль 2025), 421 на SNI (июль–декабрь 2025) [Ubuntu, Apache-док].
20. **Windows:** ASF двоичных сборок не выпускает — берут сторонние (Apache Lounge: 2.4.69, сборка VS18 от 02.10.2026, нужен Visual C++ Redistributable 2017–2026). Служба — `httpd.exe -k install [-n имя]` (по умолчанию `Apache2.4`, `conf\httpd.conf`), проверка — `httpd.exe -n "Apache2.4" -t`; «Error 1067» разбирают запуском `httpd.exe` в консоли и по журналу событий «Приложение», источник `Apache Service` [Apache-док, Apache-код, сторонний].
21. **На Windows нет `a2enmod` и `sites-enabled`:** модули включают раскомментированием `LoadModule` в `httpd.conf`, дополнительные файлы — `Include conf/extra/…`; в путях — прямые косые черты; один дочерний процесс с потоками (`ThreadsPerChild`, по умолчанию 64; исчерпание — `AH00326`) [Apache-док, Apache-код].
22. **Для 1С** причины на стороне Apache чаще всего такие: не перезапущен после публикации или смены версии платформы, модуль `wsap24.so` не загрузился (путь, зависимости, разрядность), каталог публикации закрыт правилами `Require`, MPM не тот (официально — `worker`, для файловой базы `ServerLimit 1`), таймауты и размер тела запроса не согласованы по цепочке прокси [ИТС-адм разд. 8.2, 8.3.1, 8.10.1].

## 1. Методика: как искать причину

### 1.1. Порядок проверки снизу вверх

| Шаг | Вопрос | Команда (на сервере) | Что ожидаем |
|---|---|---|---|
| 1 | Процесс жив? | `systemctl status apache2 --no-pager`; `pgrep -a apache2` | `active (running)`, родитель от `root`, дочерние от `www-data` |
| 2 | Слушает нужный адрес и порт? | `sudo ss -tlnp \| grep -E ':(80\|443)\s'` | `LISTEN … *:80 … users:(("apache2",…))` |
| 3 | Конфигурация разбирается? | `sudo apache2ctl -t` | `Syntax OK` |
| 4 | Запрос вообще доходит? | с сервера `curl -sv http://127.0.0.1/…`; с клиента — то же по имени; `sudo ufw status verbose` | ответ есть локально, но нет снаружи — брандмауэр, DNS, прокси перед Apache |
| 5 | В какой виртуальный хост попал запрос? | `sudo apache2ctl -S`; журнал доступа нужного хоста | имя из `Host` совпадает с `ServerName`/`ServerAlias` нужного хоста |
| 6 | Кто сформировал ответ? | `curl -sv` — заголовок `Server:` и тело | Apache, модуль 1С, бэкенд, nginx (таблица 1.3) |
| 7 | Что в журнале ошибок на нужном уровне? | `sudo tail -f /var/log/apache2/error.log` + временный `LogLevel` (раздел 2.2) | строка с `AHxxxxx`, по ней — раздел 3–7 |

Сначала воспроизведите проблему **с самого сервера** (`curl --resolve`, раздел 2.3): если локально работает, а снаружи нет — причина между клиентом и Apache [практика].

### 1.2. Где журналы

| Что | Ubuntu (пакет `apache2`) | Windows (сборка Apache Lounge и подобные) |
|---|---|---|
| Журнал ошибок сервера | `/var/log/apache2/error.log` (`ErrorLog ${APACHE_LOG_DIR}/error.log`, `LogLevel warn` в `apache2.conf`) [Debian] | `logs\error.log` в каталоге сервера (умолчание `ErrorLog logs/error.log` для Windows) [Apache-док] |
| Ошибки до открытия журнала (разбор конфигурации, загрузка модулей) | stderr: вывод `apache2ctl -t`, `journalctl -u apache2` | консоль `httpd.exe`; журнал событий Windows «Приложение», источник `Apache Service` [Apache-док, Apache-код] |
| Журнал доступа хоста по умолчанию | `/var/log/apache2/access.log` (`000-default.conf`, формат `combined`) [Debian] | `logs\access.log` (если включён `CustomLog`) |
| Доступ к хостам без своего `CustomLog` | `/var/log/apache2/other_vhosts_access.log` (`conf-available/other-vhosts-access-log.conf`, формат `vhost_combined` с `%v:%p` в начале строки) [Debian; уточнено 20.10.2026 по `debian/config-dir/conf-available/other-vhosts-access-log.conf` и `apache2.conf.in` метки `debian/2.4.58-1`: `CustomLog ${APACHE_LOG_DIR}/other_vhosts_access.log vhost_combined`] | — |
| Ротация | `/etc/logrotate.d/apache2`: ежедневно, 14 копий, сжатие, `create 640 root adm`, после ротации `reload` [Debian] | встроенной нет: `rotatelogs.exe` в конвейере `CustomLog` [практика] |

Следствия:

- Файлы журналов в Ubuntu принадлежат `root:adm` с правами `640`: читать их без `sudo` может член группы `adm` (`sudo usermod -aG adm <админ>`, перелогиниться) [Debian].
- Сообщения уровня `notice` при записи в файл **подавить нельзя** — они пишутся всегда [Apache-док, `LogLevel`]. Поэтому по `error.log` всегда видна хронология перезапусков: `AH00489` (event) / `AH00292` (worker) / `AH00163` (prefork) `… configured -- resuming normal operations`, `AH00493: SIGUSR1 received. Doing graceful restart`, `AH00494: SIGHUP received. Attempting to restart`, `AH00491: caught SIGTERM, shutting down` (event; в prefork — `AH00169`) [Apache-код; коды сообщений о сигналах у worker и prefork свои — ищите по тексту]. Ночной `reload` в 00:00 почти всегда — `logrotate`; перезапуск после обновления пакета — `needrestart` или скрипты пакета (раздел 9).
- `ErrorLog` внутри `<VirtualHost>` уводит ошибки хоста в отдельный файл.

Быстрый поиск по журналу ошибок:

```bash
# все перезапуски
sudo grep -E 'AH00(489|292|163|493|494|491|169)' /var/log/apache2/error.log | tail -n 20
# ошибки прокси и TLS
sudo grep -E 'AH0(0957|0959|0940|1102|0898|1144|1114|2032|2008)' /var/log/apache2/error.log | tail -n 30
```

Строка журнала по умолчанию: `[дата с микросекундами] [модуль:уровень] [pid N:tid M] [client адрес:порт] AHxxxxx: текст` (`ErrorLogFormat` по умолчанию для потоковых MPM) [Apache-док]; с 2.4.68 доступна метка времени с миллисекундами `%{m}t` [`CHANGES_2.4`] — в пакетах Ubuntu 22.04–26.04 (2.4.52/2.4.58/2.4.66) её нет.

### 1.3. Кто ответил: Apache, модуль 1С, бэкенд или промежуточный прокси

| Признак ответа (`curl -sv`) | Кто ответил | Куда смотреть |
|---|---|---|
| `Server: Apache/2.4.58 (Ubuntu)`, тело — стандартная HTML-страница с заголовком `403 Forbidden`, `404 Not Found`, `500 Internal Server Error` и подписью сервера внизу | сам Apache (в Ubuntu `ServerTokens OS` и `ServerSignature On` заданы в `conf-available/security.conf`) [Debian] | `error.log`: разделы 3–4 |
| Тело `… Proxy Error … The proxy server could not handle the request … Reason: …` | `mod_proxy` Apache [Apache-код] | `error.log`: раздел 5 |
| `400 Bad Request` и текст `You're speaking plain HTTP to an SSL-enabled server port.` | `mod_ssl`: на порт TLS пришёл обычный HTTP [Apache-код] | раздел 6.2 |
| `421 Misdirected Request` | `mod_ssl`, проверка SNI ↔ `Host` [Apache-код] | раздел 6.4 |
| Страница или текст ошибки 1С (о версии, кластере, лицензии), код 500 при исправном Apache | модуль 1С `wsap24.so` | `../1c/05`, раздел «Типичные ошибки» |
| `Server: nginx/…`, страница `502 Bad Gateway`/`504 Gateway Time-out` с подписью `nginx` | nginx перед Apache | журнал nginx (`/var/log/nginx/error.log`), `../1c/05` раздел 9 |
| JSON или HTML приложения (Redmine, NetBox, GlitchTip) | сам бэкенд | журнал приложения: `../redmine/05-obsluzhivanie-obnovlenie-bezopasnost.md`, `../netbox/04-obsluzhivanie-bekap-obnovlenie.md` |
### 1.4. Сценарий сбора диагностики (только чтение)

Сценарий ничего не меняет и не перезапускает; его вывод удобно приложить к задаче в Redmine. Запуск: `sudo bash apache-diag.sh > /tmp/apache-diag-$(hostname -s).txt 2>&1`.

```bash
#!/bin/bash
# apache-diag.sh — сбор сведений об Apache в Ubuntu. Только чтение.
set -u
sec() { printf '\n===== %s =====\n' "$1"; }

sec "Хост и ОС";        hostname -f; grep PRETTY_NAME /etc/os-release; date -R
sec "Пакеты";           dpkg -l 'apache2*' 'libapache2-mod-*' 2>/dev/null | awk '/^ii/{print $2, $3}'
sec "Версия и MPM";     apache2ctl -V 2>&1 | grep -E 'Server version|Server built|Server MPM|SERVER_CONFIG_FILE|HTTPD_ROOT'
sec "Служба";           systemctl status apache2 --no-pager -l 2>&1 | head -n 25
sec "Ограничения юнита"; systemctl show apache2 -p Type -p PrivateTmp -p MemoryDenyWriteExecute -p ProtectHome -p ProtectSystem -p NRestarts 2>&1
sec "Журнал службы";    journalctl -u apache2 -b --no-pager 2>&1 | tail -n 40
sec "Проверка конфигурации"; apache2ctl -t 2>&1
sec "Виртуальные хосты и параметры запуска"; apache2ctl -S 2>&1
sec "Модули";           apache2ctl -M 2>&1
sec "Подключённые файлы"; apache2ctl -t -D DUMP_INCLUDES 2>&1
sec "Сертификаты";      apache2ctl -t -D DUMP_CERTS 2>&1
sec "Порты";            ss -tlnp 2>&1 | grep -E 'apache2|nginx|:80\s|:443\s'
sec "Процессы";         ps -o pid,ppid,user,nlwp,rss,etime,cmd -C apache2 2>&1 | head -n 20
sec "Коды в error.log (последние 2000 строк)"
tail -n 2000 /var/log/apache2/error.log 2>/dev/null | grep -o 'AH[0-9]\{5\}' | sort | uniq -c | sort -rn | head -n 25
sec "Последние ошибки"; tail -n 40 /var/log/apache2/error.log 2>/dev/null
sec "Брандмауэр";       ufw status verbose 2>&1 | head -n 30
sec "Локальные ответы"; for u in http://127.0.0.1/ https://127.0.0.1/; do
    printf '%s -> ' "$u"; curl -sk -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 10 "$u"; done
```

Ключи и пароли сценарий не читает.

## 2. Инструменты диагностики

### 2.1. `apache2ctl`, `apachectl`, `apache2`

В Ubuntu `apachectl` и `apache2ctl` — один и тот же сценарий Debian (`/usr/sbin/apache2ctl`, `/usr/sbin/apachectl`), который читает `/etc/apache2/envvars` и передаёт неизвестные ему аргументы программе `/usr/sbin/apache2` [Debian, Ubuntu filelist]. Поэтому все ключи `httpd` из документации пишутся как `apache2ctl <ключ>`.

| Команда | Что показывает | Источник |
|---|---|---|
| `sudo apache2ctl -t` (= `configtest`) | проверка синтаксиса; `Syntax OK` или первая ошибка с файлом и строкой. Код выхода 0 — без ошибок | [Apache-док] |
| `sudo apache2ctl -S` | синоним `-t -D DUMP_VHOSTS -D DUMP_RUN_CFG`: блок `VirtualHost configuration:` (строки `… is a NameVirtualHost`, `default server <имя> (<файл>:<строка>)`, `port 443 namevhost <имя> (<файл>:<строка>)`, `alias …`), затем `ServerRoot`, `Main DocumentRoot`, `Main ErrorLog`, мьютексы, `PidFile`, `Define`, `User`, `Group` | [Apache-код] |
| `sudo apache2ctl -M` | синоним `-t -D DUMP_MODULES`: статические и загруженные модули, среди них MPM (`mpm_event_module (shared)`) | [Apache-код] |
| `sudo apache2ctl -t -D DUMP_INCLUDES` | дерево подключённых файлов с отступом по глубине `Include` — находит, из какого файла пришла директива | [Apache-код] |
| `sudo apache2ctl -t -D DUMP_RUN_CFG` | только параметры запуска без виртуальных хостов | [Apache-код] |
| `sudo apache2ctl -t -D DUMP_CERTS` | `Server certificates:` и пути всех файлов `SSLCertificateFile` (есть в 2.4.52 и 2.4.58) | [Apache-код] |
| `apache2ctl -V` | версия, дата сборки, `Server MPM`, пути по умолчанию (`HTTPD_ROOT`, `SERVER_CONFIG_FILE`) | [Apache-док] |
| `sudo apache2ctl -e debug -t` | поднимает `LogLevel` на время запуска (`-E файл` — сообщения запуска в файл) | [Apache-док] |
| `sudo apache2ctl -X` | отладочный режим: один рабочий процесс, без отсоединения от консоли; только при **остановленной** службе, выход — `Ctrl+C` | [Apache-док] |
| `apache2ctl status` / `fullstatus` | страница `mod_status` через текстовый браузер `www-browser -dump http://localhost:80/server-status`; в Ubuntu Server браузера обычно нет → `'www-browser -dump …' failed.` — пользуйтесь `curl -s http://127.0.0.1/server-status?auto` | [Debian `apache2ctl`] |

Код выхода `apache2ctl` полезен в сценариях: при ошибке он печатает `Action '<аргументы>' failed.` и `The Apache error log may have more information.` и возвращает ненулевой код [Debian `apache2ctl`].

Почему нельзя `sudo apache2 -t`: `apache2.conf` использует переменные `${APACHE_RUN_USER}`, `${APACHE_RUN_DIR}`, `${APACHE_LOG_DIR}` из `envvars`; без них — `AH00111`, `DefaultRuntimeDir must be a valid directory…` или `apache2: bad user name ${APACHE_RUN_USER}` (`AH00543`) [Debian `README.Debian`, «Common Problems», п. 8; Apache-код]. Если без прямого вызова не обойтись: `sudo bash -c 'source /etc/apache2/envvars && apache2 -t'`.

### 2.2. Уровни журнала и точечная детализация

Уровни `LogLevel` по убыванию важности: `emerg`, `alert`, `crit`, `error`, `warn`, `notice`, `info`, `debug`, `trace1` … `trace8`. По умолчанию `warn` [Apache-док]. Документация рекомендует держать не ниже `crit`; в Ubuntu задан `warn` [Debian].

Синтаксис [Apache-док]:

- `LogLevel info` — для всех модулей; повторный `LogLevel` без имени модуля сбрасывает уровень всех модулей;
- `LogLevel warn ssl:info proxy:debug` — общий уровень плюс уровни отдельных модулей; модуль можно назвать идентификатором без `_module` (`ssl`), с ним (`ssl_module`) или именем исходного файла (`mod_ssl.c`);
- внутри `<Directory>`/`<Location>` — уровень для запросов в этой области (только сообщения, связанные с запросом, после разбора запроса; сообщения соединения и сервера не затрагиваются).

Готовые наборы на время разбора. Кладите их в отдельный файл и выключайте после разбора: на `debug`/`trace*` в журнал попадают заголовки запросов, а `mod_dumpio` пишет тела запросов вместе с паролями и токенами.

| Задача | Строка `LogLevel` | Что появится |
|---|---|---|
| 403 непонятно от какого правила | `LogLevel warn authz_core:debug` | `authorization result of Require …: denied/granted` по каждому правилу [Apache-код] |
| 404, 413, 414, 400 «header too long», 408 | `LogLevel warn core:info http:info reqtimeout:info` (идентификатор `http` уточнён 20.10.2026 по коду: в `http_filters.c` стоит `APLOG_USE_MODULE(http)`) | `AH00128`, `AH00565`, `AH00561` (ядро), `AH01588`/`AH01591` (`http_filters.c`), `AH01382` (`mod_reqtimeout`) |
| сбои TLS у клиентов | `LogLevel warn ssl:info` | `AH02008 … in handshake` + причина OpenSSL; `AH02411`/`AH02003` для TLS к бэкенду |
| обратный прокси | `LogLevel warn proxy:debug proxy_http:debug` | выбор воркера, `AH00944`/`AH00947 connecting …`, `AH00942`/`AH00943` захват/освобождение соединения |
| `mod_rewrite` | `LogLevel alert rewrite:trace3` (`RewriteLog` в 2.4 нет) | ход сопоставления правил [Apache-док] |
| Kerberos | `LogLevel warn auth_gssapi:debug` (идентификатор уточнён 20.10.2026 по `src/mod_auth_gssapi.c`: `APLOG_USE_MODULE(auth_gssapi)`, модуль `auth_gssapi_module`) | `GSS Server Name: …`, `requester: …` [сторонний: исходный код mod_auth_gssapi] |
| весь обмен байтами | `a2enmod dump_io` + `DumpIOInput On`, `DumpIOOutput On`, `LogLevel dumpio:trace7` | тела запросов и ответов после расшифровки TLS [Apache-док]. В Debian файл модуля называется `dump_io.load`, поэтому `a2enmod dump_io`, а не `dumpio` [Ubuntu filelist] |

Порядок включения:

```bash
sudo tee /etc/apache2/conf-available/zz-debug.conf >/dev/null <<'EOF'
# ВРЕМЕННО, удалить после разбора
LogLevel warn ssl:info authz_core:debug proxy:debug proxy_http:debug
EOF
sudo a2enconf zz-debug && sudo apache2ctl -t && sudo systemctl reload apache2
# ... воспроизвести, затем
sudo a2disconf zz-debug && sudo apache2ctl -t && sudo systemctl reload apache2
```

Для `LogLevel` достаточно `reload` (`a2enmod` советует `restart`, `a2enconf`/`a2ensite` — `reload`) [Debian `a2enmod`].

Связать строку журнала доступа со строкой журнала ошибок можно идентификатором запроса: `%L` в `LogFormat` («Request log ID from the error log», `-`, если для запроса ничего не писалось в журнал ошибок) и `[R:%L]` в `ErrorLogFormat` [Apache-док]. Пример из документации: `ErrorLogFormat "[%{uc}t] [%-m:%-l] [R:%L] [C:%{C}L] %7F: %E: %M"`.

`mod_log_debug` (`sudo a2enmod log_debug`): `LogMessage "%{HTTP:X-Forwarded-Proto}"` внутри `<Location "/demo">` покажет, какие заголовки дошли до Apache от прокси [Apache-док].

### 2.3. `curl`

```bash
# код ответа и время — без тела
curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' http://127.0.0.1/demo/

# заголовки запроса и ответа, перенаправления, TLS (только для разбора: -k отключает проверку сертификата)
curl -sv -o /dev/null https://srv-1c-app.example.local/demo/

# запрос в нужный виртуальный хост в обход DNS: SNI и Host будут правильными
curl -sv --resolve redmine.example.local:443:127.0.0.1 https://redmine.example.local/ -o /dev/null

# проверка цепочки по своему корневому сертификату
curl -sv --cacert /usr/local/share/ca-certificates/corp-root.crt https://srv-1c-app.example.local/demo/ -o /dev/null

# Kerberos (SPNEGO): сначала kinit пользователем домена, затем
curl -sv --negotiate -u : https://srv-1c-app.example.local/demo/ -o /dev/null
```

Коды завершения `curl`, которые чаще всего встречаются при разборе [сторонний: libcurl-errors]: `7` — не удалось подключиться (`CURLE_COULDNT_CONNECT`: порт закрыт, служба не слушает); `28` — таймаут (`CURLE_OPERATION_TIMEDOUT`); `35` — ошибка рукопожатия TLS (`CURLE_SSL_CONNECT_ERROR`, например HTTPS на порт с обычным HTTP); `52` — сервер закрыл соединение, ничего не ответив (`CURLE_GOT_NOTHING`); `56` — ошибка приёма (`CURLE_RECV_ERROR`); `60` — сертификат не прошёл проверку (`CURLE_PEER_FAILED_VERIFICATION`). Код — `echo $?` сразу после `curl`.

### 2.4. `openssl s_client` и проверка сертификатов

```bash
# что отдаёт сервер: цепочка, протокол, шифр, результат проверки
openssl s_client -connect srv-1c-app.example.local:443 -servername srv-1c-app.example.local -showcerts </dev/null
# коротко
openssl s_client -connect srv-1c-app.example.local:443 -servername srv-1c-app.example.local -brief </dev/null
# проверка имени (результат 62 — hostname mismatch); протокол — ключами -tls1_2 / -tls1_3
openssl s_client -connect 192.0.2.10:443 -servername srv-1c-app.example.local -verify_hostname srv-1c-app.example.local </dev/null 2>&1 | grep 'Verify return code'

# содержимое сертификата
sudo openssl x509 -in /etc/ssl/certs/1c.crt -noout -subject -issuer -dates -ext subjectAltName
# совпадают ли сертификат и ключ (хеши должны быть равны)
sudo openssl x509 -in /etc/ssl/certs/1c.crt -noout -pubkey | sha256sum
sudo openssl pkey -in /etc/ssl/private/1c.key -pubout | sha256sum
# проверка цепочки локально
openssl verify -CAfile corp-root.crt -untrusted intermediate.crt server.crt
```

Строка `Verify return code` в выводе `s_client` — номер и текст ошибки проверки OpenSSL [сторонний: OpenSSL 3.0 `x509_txt.c`, `x509_vfy.h`]:

| Код | Текст | Что значит для Apache |
|---|---|---|
| 0 | `ok` | цепочка строится до доверенного корня |
| 9 / 10 | `certificate is not yet valid` / `certificate has expired` | не наступил / истёк срок (часы клиента или сервера, не продлён сертификат) |
| 18 | `self-signed certificate` | самоподписанный сертификат сервера; клиент должен доверять ему явно |
| 19 | `self-signed certificate in certificate chain` | корень цепочки (свой ЦС) не в списке доверенных у клиента |
| 20 | `unable to get local issuer certificate` | у клиента нет корня; или сервер отдал не ту цепочку |
| 21 | `unable to verify the first certificate` | сервер **не отдал промежуточный** сертификат — исправлять на сервере (раздел 6.3) |
| 62 | `hostname mismatch` | имя не входит в `subjectAltName` (только с `-verify_hostname`) |
### 2.5. Сеть, права, процессы

| Задача | Команда |
|---|---|
| Кто слушает порт | `sudo ss -tlnp 'sport = :443'`; `sudo fuser -v 443/tcp` (пакет `psmisc`) |
| Права по всей цепочке каталогов | `namei -l /var/www/demo/default.vrd` |
| Может ли `www-data` прочитать файл / пройти в каталог | `sudo -u www-data test -r /путь && echo OK`; `sudo -u www-data ls /путь/каталог` |
| Разрешение имени так, как его видит Apache | `getent hosts redmine.example.local` (учитывает `/etc/hosts`) |
| Ограничения юнита systemd | `systemctl show apache2 -p PrivateTmp -p MemoryDenyWriteExecute -p ProtectHome`; `systemctl cat apache2` |
| Профиль AppArmor | `sudo aa-status \| grep -i apache` (в Ubuntu по умолчанию профиля нет; он в пакете `libapache2-mod-apparmor`) — см. `../1c/05`, раздел 6.1 |
| Время (для Kerberos и сроков сертификатов) | `timedatectl`; `chronyc tracking` |

### 2.6. `mod_status`, `mod_info`

- **`mod_status`** в Ubuntu включён, `/server-status` — только с локального адреса (`../1c/05`, 12.1): `curl -s 'http://127.0.0.1/server-status?auto'`; показатели — `apache/03-…`.
- **`mod_info`** (`sudo a2enmod info`, `restart`) — `/server-info`: модули и реально применённые директивы. Только `Require local` и выключать после разбора — страница раскрывает конфигурацию [Apache-док].

## 3. Apache не запускается или не перечитывает конфигурацию

### 3.1. Как увидеть настоящую причину

```bash
sudo apache2ctl configtest            # ошибка разбора с файлом и строкой
systemctl status apache2 --no-pager -l
sudo journalctl -u apache2 -b --no-pager | tail -n 40
sudo tail -n 30 /var/log/apache2/error.log   # ошибки после открытия журнала: порты, модули, TLS-инициализация
```

`systemctl` сам причину не показывает — только `Job for apache2.service failed because the control process exited with error code.` и `Failed with result 'exit-code'` [практика]. В Ubuntu 22.04/24.04 юнит запускает `apachectl start` (`Type=forking`), и всё, что `apache2` вывел на stderr, оказывается в journald вместе с итоговыми строками `Action 'start' failed.` / `The Apache error log may have more information.` [Debian; состав юнита — `../1c/05`, раздел 3.1]. В Ubuntu 26.04 юнит другой (`Type=notify`, набор ограничений systemd) — там же.

Сообщения об ошибках разбора бывают двух видов [Apache-код]:

- **на этапе чтения файлов** (директивы, которые выполняются сразу при чтении: `LoadModule`, `Include`, `Define`, `<IfModule>`, ошибки вложенности секций) — одной строкой с цепочкой включений: `apache2: Syntax error on line 146 of /etc/apache2/apache2.conf: Syntax error on line 1 of /etc/apache2/mods-enabled/x.load: Cannot load …` — читайте **справа налево**: последний файл и строка — место ошибки;
- **на этапе обработки** — двумя строками: `AH00526: Syntax error on line 12 of /etc/apache2/sites-enabled/redmine.conf:` и на следующей строке сам текст ошибки.

### 3.2. Каталог ошибок запуска

| № | Сообщение (как в журнале) | Причина | Что делать |
|---|---|---|---|
| 1 | `AH00526: Syntax error on line N of <файл>:` + текст | опечатка, директива не в своём контексте, лишние или неверные аргументы | открыть файл на строке N; `sudo apache2ctl -t -D DUMP_INCLUDES` — откуда файл подключён |
| 2 | `Invalid command 'X', perhaps misspelled or defined by a module not included in the server configuration` | директива принадлежит невключённому модулю (таблица 3.3) или опечатка | `sudo a2enmod <модуль>`; проверить написание |
| 3 | `<VirtualHost> was not closed.` / `</VirtualHost> without matching <VirtualHost> section` | непарные секции (часто после ручной правки или неудачного `sed`) | выровнять секции; для поиска — `grep -n '<\/\?VirtualHost' <файл>` |
| 4 | `Either all Options must start with + or -, or no Option may.` | смешаны `Options +Indexes FollowSymLinks` (с плюсом и без) — в 2.4 это ошибка | писать все с `+`/`-` либо все без знаков [Apache-код] |
| 5 | `AH00534: apache2: Configuration error: More than one MPM loaded.` / `… No MPM loaded.` | включены два MPM или ни одного (`mods-enabled/mpm_*.load`) | `ls /etc/apache2/mods-enabled/mpm_*`; `sudo a2dismod mpm_event mpm_prefork; sudo a2enmod mpm_worker` и **restart** (`../1c/05`, раздел 3.3) |
| 6 | `AH00111: Config variable ${APACHE_…} is not defined` + `DefaultRuntimeDir must be a valid directory…` | `apache2` запущен напрямую, без `envvars` | запускать через `apache2ctl` (раздел 2.1) |
| 7 | `apache2: bad user name ${APACHE_RUN_USER}` (`AH00543`) | то же | то же [Debian `README.Debian`, п. 8] |
| 8 | `(98)Address already in use: AH00072: make_sock: could not bind to address [::]:80` → `no listening sockets available, shutting down` → `AH00015: Unable to open logs` | порт занят другой программой (nginx, второй экземпляр Apache, контейнер Docker) **или** пересекающиеся `Listen` (например, `Listen 80` и `Listen 10.0.0.5:80`); точный повтор `Listen` даёт другую ошибку — «Cannot define multiple Listeners on the same IP:port», её ловит `configtest` (уточнено 20.10.2026 по `listen.c`) | раздел 3.4 |
| 9 | `(13)Permission denied: AH00072: make_sock: could not bind to address 0.0.0.0:80` | запуск не от `root` (порты ниже 1024), ограничение системы безопасности | запускать службой: `sudo systemctl start apache2` |
| 10 | `(99)Cannot assign requested address: AH00072: make_sock: could not bind to address 192.0.2.10:443` | в `Listen` указан адрес, которого нет на сервере (сменили адрес в netplan) | исправить `Listen` в `/etc/apache2/ports.conf` или вернуть адрес; `ip -br a` [практика: текст errno] |
| 11 | `AH00073: make_sock: unable to listen for connections on address …` | системная ошибка `listen()` после успешного `bind` | смотреть код ошибки в скобках перед сообщением [Apache-код] |
| 12 | `AH00558: apache2: Could not reliably determine the server's fully qualified domain name, using 127.0.1.1. Set the 'ServerName' directive globally to suppress this message` | нет глобального `ServerName` | только предупреждение; убрать — `ServerName` в отдельном файле `conf-available` (`../1c/05`, раздел 3.2) [Debian `README.Debian`, «Common Problems», п. 1] |
| 13 | `AH02291: Cannot access directory '/var/log/apache2/1c/' for error log of vhost defined at <файл>:<строка>` (для основного журнала — `… for main error log`) | каталог журнала, указанный в `ErrorLog`, не существует | `sudo install -d -o root -g adm -m 750 /var/log/apache2/1c` (или поправить путь) [Apache-код] |
| 14 | `AH02297: Cannot access directory '…' for log file '…' defined at <файл>:<строка>` | то же для `CustomLog` | то же |
| 15 | `(13)Permission denied: AH00091: apache2: could not open error log file /…/x.log.` → `AH00015: Unable to open logs` | у `root` нет права записи в каталог журнала (права, сетевая ФС; на ФС только для чтения код будет `(30)Read-only file system`); в 26.04 юнит делает `/usr`, `/etc`, `/boot` (`ProtectSystem=full`) и `/home` (`ProtectHome=read-only`) доступными только для чтения, `/root` — недоступным | журналы держать в `/var/log/apache2` (в 26.04 он ещё и явно перечислен в `ReadWritePaths`), не в `/etc`, `/home`, `/root` [Debian `apache2.service` метки `debian/2.4.66-2`; `../1c/05`, 3.1] |
| 16 | `AH00112: Warning: DocumentRoot [/var/www/x] does not exist`; `AH00548: NameVirtualHost has no effect …` | нет каталога; остаток конфигурации 2.2 | предупреждения: создать каталог / удалить строку |
| 17 | `AH00547: Could not resolve host name <имя> -- ignoring!` | `<VirtualHost имя:443>` с неразрешаемым именем | `<VirtualHost *:443>` + `ServerName` |
| 18 | `SSLCertificateFile: file '…' does not exist or is empty`, `AH02565 … do not match`, `AH02564 … encrypted (?) private key` | сертификат или ключ | раздел 6.1 |
| 19 | `'shmcb' session cache not supported (known names: …). Maybe you need to load the appropriate socache module (mod_socache_shmcb?).` | `SSLSessionCache shmcb:…` без модуля `socache_shmcb` | `sudo a2enmod socache_shmcb` [Apache-код] |
| 20 | `SSLEngine` — `Argument must be On or Off`; `AH10510: 'SSLEngine optional' is no longer supported` | неверный аргумент (ошибка разбора); `optional` удалён в 2.4.64 (в Ubuntu 22.04/24.04 — с обновлением 14.07.2025): `AH10510` — уровень `notice`, запуск **не прерывается**, а TLS для этого хоста выключается (как `SSLEngine off`) [Apache-код, `ssl_engine_config.c`] | `SSLEngine on` в `<VirtualHost>` [Apache-док, Ubuntu] |
| 21 | `AH02569: Illegal attempt to re-initialise SSL for server (SSLEngine On should go in the VirtualHost, not in global scope.)` | `SSLEngine on` вне виртуального хоста | перенести в `<VirtualHost *:443>` [Apache-код] |
| 22 | `Cannot load <модуль>.so into server: …` и другие ошибки модулей | см. раздел 3.5 | |
| 23 | `AH01574: module _1cws_module is already loaded, skipping` | `LoadModule` записан дважды | оставить одну строку (`../1c/05`, ошибка 3) |
| 24 | `Could not open configuration file /etc/apache2/x.conf: No such file or directory` | `Include` без маски на несуществующий файл | исправить путь; для необязательных файлов — `IncludeOptional` (несуществующий путь без маски не ошибка с 2.4.30) [Apache-док] |

### 3.3. «Invalid command»: директива → модуль

| Директива из сообщения | Модуль | Как включить в Ubuntu |
|---|---|---|
| `ProxyPass`, `ProxyPassReverse`, `ProxyPreserveHost`, `ProxyTimeout`, `ProxyAddHeaders` | `mod_proxy` | `sudo a2enmod proxy`; для `http://`-бэкендов ещё `proxy_http` (иначе 500 и `AH01144`, раздел 5) |
| `BalancerMember` | `mod_proxy_balancer` | `sudo a2enmod proxy_balancer lbmethod_byrequests` |
| `SSLEngine`, `SSLCertificateFile`, `SSLProxyEngine`, `SSLVHostSNIPolicy` | `mod_ssl` | `sudo a2enmod ssl` (`SSLVHostSNIPolicy` есть только в 2.4.66+ и в пакетах Ubuntu 22.04/24.04 начиная с обновления 09.12.2025) |
| `Header`, `RequestHeader` | `mod_headers` | `sudo a2enmod headers` |
| `RewriteEngine`, `RewriteRule`, `RewriteCond` | `mod_rewrite` | `sudo a2enmod rewrite` |
| `RemoteIPHeader`, `RemoteIPInternalProxy` | `mod_remoteip` | `sudo a2enmod remoteip` |
| `AuthLDAPURL`, `AuthLDAPBindDN` | `mod_authnz_ldap` (+ `mod_ldap`) | `sudo a2enmod authnz_ldap` |
| `GssapiCredStore`, `GssapiAllowedMech`, `GssapiDelegCcacheDir` | `mod_auth_gssapi` (пакет `libapache2-mod-auth-gssapi`, universe) | `sudo apt install libapache2-mod-auth-gssapi && sudo a2enmod auth_gssapi` |
| `Krb5Keytab`, `KrbMethodNegotiate`, `KrbSaveCredentials` | `mod_auth_kerb` (пакет `libapache2-mod-auth-kerb` — только Ubuntu 22.04) | `sudo a2enmod auth_kerb` (`../1c/05`, раздел 11.3) |
| `ManagedApplicationDescriptor` (и обработчик `1c-application`) | модуль 1С `_1cws_module` (`wsap24.so`) | строка `LoadModule _1cws_module "/opt/1cv8/x86_64/<версия>/wsap24.so"` **до** блоков публикаций (`../1c/05`, ошибка 2) |
| `DumpIOInput` / `LogMessage` / `H2Direct` | `mod_dumpio` / `mod_log_debug` / `mod_http2` | `sudo a2enmod dump_io` / `log_debug` / `http2` |
| `Order`, `Allow`, `Deny` (синтаксис 2.2) | `mod_access_compat` | лучше переписать на `Require` (Debian прямо пишет, что модуль совместимости «does not work well in practice») [Debian `NEWS.Debian`] |

`a2enmod` сам подключает зависимости, перечисленные в строке `# Depends:` файла `.load`, и отказывается работать при конфликте, объявленном строкой `# Conflicts:`, с сообщением `Module <имя> is enabled - cannot proceed due to conflicts. It needs to be disabled first!` [Debian, код `a2enmod`]. Уточнено 20.10.2026 по `.load`-файлам метки `debian/2.4.58-1` (выборочно): `proxy_http` — `# Depends: proxy`; `proxy_balancer` — `# Depends: proxy alias slotmem_shm`; `ssl` — `# Depends: mime socache_shmcb` (поэтому ошибка № 19 из 3.2 бывает только при ручном `LoadModule` или отключённом `socache_shmcb`); `authnz_ldap` — `# Depends: ldap`; `mpm_event` — `# Conflicts: mpm_worker mpm_prefork`.

### 3.4. Порт занят

```bash
sudo ss -tlnp 'sport = :80'        # кто держит 80
sudo ss -tlnp 'sport = :443'
sudo apache2ctl -S 2>&1 | head     # какие адреса ждёт сам Apache
grep -rn '^\s*Listen' /etc/apache2/ # все Listen (ports.conf + сайты)
```

| Что видно | Причина | Решение |
|---|---|---|
| порт держит `nginx` | на хосте работает nginx перед Apache, а Apache всё ещё слушает 80/443 | Apache — на `127.0.0.1:8080` (в `ports.conf` и `<VirtualHost 127.0.0.1:8080>`), снаружи — nginx (`../1c/05`, раздел 9.2) |
| порт держит `docker-proxy` | контейнер опубликовал порт `80`/`443` (например, GlitchTip или NetBox без `127.0.0.1:` в `ports:`) | публиковать контейнеры на `127.0.0.1:<порт>`, наружу — через Apache (`../observability/02-glitchtip.md`, `../netbox/05-…`) |
| порт держит `apache2`, а служба считается остановленной | процесс запущен вручную (`apache2ctl -X`, `apache2 -k start` в обход systemd) или остался «сиротой» | `ps -ef \| grep [a]pache2`; аккуратно остановить: `sudo apache2ctl -k graceful-stop`, при зависании — `sudo kill <pid родителя>`; затем `sudo systemctl start apache2` |
| ни одного процесса на порту, но Apache пишет `Address already in use` | пересекающиеся `Listen` (точный повтор `Listen` даёт «Cannot define multiple Listeners on the same IP:port» при `configtest`); например, пересекающиеся `Listen 80` и `Listen 127.0.0.1:80` | оставить один `Listen` на адрес и порт — по документации повтор приводит к фатальной ошибке [Apache-док, `mod/mpm_common.html#listen`, `bind.html`] |
| после `reload` с изменённым `Listen` Apache завершился | при перезапуске Apache держит старые сокеты; конфликтующий новый набор `Listen` (например, `127.0.0.1:80` → `80`) приводит к отказу | менять `Listen` только полной остановкой и запуском: `sudo systemctl stop apache2 && sudo systemctl start apache2` [Apache-док, `bind.html`] |

### 3.5. Ошибки загрузки модулей, несовместимость с MPM, падения процессов

Тексты ошибок `LoadModule` формирует `mod_so`: `Cannot load <файл> into server: <текст ошибки динамического загрузчика>`; хвост после двоеточия — это сообщение `dlerror()` из glibc [Apache-код; тексты glibc — практика].

| Сообщение | Причина | Решение |
|---|---|---|
| `Cannot load /opt/1cv8/x86_64/8.3.27.XXXX/wsap24.so into server: /opt/1cv8/x86_64/8.3.27.XXXX/wsap24.so: cannot open shared object file: No such file or directory` | платформу обновили или удалили, а `LoadModule` указывает на старый каталог | `grep -rn 'wsap24.so' /etc/apache2/`; поправить путь; `configtest`; `restart` (`../1c/05`, раздел 13) |
| `Cannot load <модуль> into server: libXXX.so.N: cannot open shared object file: No such file or directory` | нет библиотеки, от которой зависит модуль (не установлен пакет; модуль собран под другой выпуск ОС) | `ldd <модуль> \| grep 'not found'`; поставить пакет с библиотекой (`apt-file search libXXX.so.N`); для 1С — доустановить компонент `ws` той же сборки и зависимости из `../1c/02-ustanovka-servera-ubuntu.md` |
| `Cannot load <модуль> into server: <модуль>: undefined symbol: <имя>` | модуль собран для другой версии Apache/APR/OpenSSL или другой сборки платформы (частично обновлённый каталог 1С) | поставить модуль, собранный под ваш пакет; для 1С — модуль и библиотеки одной сборки, `webinst`/`wsap24.so` строго версии кластера [ИТС-адм разд. 8.2, 8.3.1] |
| `Cannot load <модуль> into server: <модуль>: wrong ELF class: ELFCLASS32` | 32-разрядный модуль в 64-разрядный Apache | только модуль той же разрядности; на Linux сочетание «64-разрядный веб-сервер + 32-разрядная 1С» не поддерживается [ИТС-адм разд. 8.3.1; текст ошибки — практика] |
| `API module structure '<имя>' in file <файл> is garbled - expected signature 41503234 but saw <другое> - perhaps this is not an Apache module DSO, or was compiled for a different Apache version?` | модуль для другой ветки Apache (например `wsap22.so` для 2.2 вместо `wsap24.so`); `41503234` — сигнатура «AP24» | взять модуль для 2.4 (`wsap24.so`) [Apache-код, `ap_mmn.h`; уточнено 20.10.2026 по истории `ap_mmn.h`: у модулей 2.2 сигнатура «AP22», то есть `saw 41503232`] |
| ``Can't locate API module structure `<имя>' in file <файл>: …`` | неверный идентификатор в `LoadModule` (например, `1cws_module` вместо `_1cws_module`) | исправить идентификатор |
| `Apache is running a threaded MPM, but your PHP Module is not compiled to be threadsafe.  You need to recompile PHP.` + `AH00013: Pre-configuration failed` | на сервер поставили `libapache2-mod-php`, а MPM переключили на `worker`/`event` (например, ради 1С) | на сервере публикации 1С PHP-приложения в процессе Apache не держать; если нужны — PHP-FPM через `proxy_fcgi` [сторонний: исходный код PHP 8.3, `sapi_apache2.c`; Apache-код] |
| `AH10034: The mpm module (prefork.c) is not supported by mod_http2. … the HTTP/2 protocol will be inactive.` | `mod_http2` при `mpm_prefork` | только предупреждение: HTTP/2 не работает; для 1С `prefork` и так не рекомендуется [Apache-код; ИТС-адм разд. 8.10.1] |
| `AH00052: child pid 12345 exit signal Segmentation fault (11)` | падение рабочего процесса: сторонний модуль (модуль 1С, `auth_kerb`, `auth_gssapi`), несовместимые библиотеки, нехватка стека потока | раздел 3.6 |

**Совместимость модуля 1С с MPM.** Официально для Linux — `worker`, для файловой базы — `ServerLimit 1` [ИТС-адм разд. 8.2, 8.10.1.1]. Ошибок загрузки `wsap24.so` при `event`/`prefork` документация не описывает; неподходящий MPM проявляется позже — лишние экземпляры модуля и соединения с кластером, у файловой базы — ошибки блокировок и потеря результатов фоновых заданий (`../1c/05`, раздел 3.3). Смена MPM — только через `restart` [Apache-док].

### 3.6. Падения рабочих процессов (`AH00052`)

1. Найти частоту и время: `sudo grep -c 'exit signal' /var/log/apache2/error.log`; `sudo grep 'exit signal' /var/log/apache2/error.log | tail`. Совпадение времени с конкретными запросами — по журналу доступа (запросы, «оборванные» на этом времени, у которых в `%X` стоит `X`) [Apache-док, `mod_log_config`].
2. `AH00060: seg fault or similar nasty error detected in the parent process` — падает родительский процесс; это серьёзнее, обычно — модуль, выполняющий код при запуске [Apache-код].
3. Исключать модули по одному на стенде, начиная со сторонних (не из пакета `apache2-bin`).
4. Для дампа ядра: инструкция пакета `/usr/share/doc/apache2/README.backtrace` [Ubuntu filelist] и директива `CoreDumpDirectory`: по умолчанию процесс остаётся в `ServerRoot`, куда `www-data` писать не должен, поэтому для дампов задают отдельный каталог с правом записи для `www-data`; директива действует, только если ядро настроено писать дампы в рабочий каталог процесса; кроме того, на Linux дампы процессов, сменивших пользователя после запуска от `root`, Apache снова разрешает, только если `CoreDumpDirectory` задана. Документация не рекомендует держать её на рабочих серверах (другие процессы с теми же правами смогут подключаться к дочерним процессам через `ptrace`) — включайте только на время разбора [Apache-док]. В Ubuntu 26.04 учитывайте ограничения юнита (`../1c/05`, 6.1).
5. Падения с участием модуля 1С — в поддержку 1С с дампом и версией платформы, предварительно исключив неподходящий MPM и несовпадение сборок [практика].

### 3.7. `reload` или `restart`

| Команда | Проверяет конфигурацию перед действием | Если конфигурация сломана | Текущие запросы |
|---|---|---|---|
| `sudo systemctl reload apache2` (в 22.04–26.04 — `ExecReload=/usr/sbin/apachectl graceful`) | да | Apache продолжает работать со старой конфигурацией, `reload` завершается ошибкой | дорабатывают |
| `sudo apache2ctl graceful` | да (сценарий Debian сначала выполняет `apache2 -t`) | то же | дорабатывают |
| `sudo apache2ctl restart` | да | то же | обрываются (сигнал `SIGHUP`; в 22.04 и 26.04 — через `systemctl restart`, см. ниже) |
| `sudo systemctl restart apache2` | **нет** (`stop`, затем `start`) | **Apache остановлен и не запущен** | обрываются |
| `sudo systemctl stop` / `start` | нет | `start` не выполнится | — |

[Debian `apache2ctl`: для `restart|graceful` сначала `$HTTPD -t`; Apache-док `apachectl`; юнит 22.04/24.04 — `../1c/05`, 3.1]. Для 26.04 уточнено 20.10.2026 по `debian/apache2.service` метки `debian/2.4.66-2` (основа пакета 26.04; в списке изменений Ubuntu юнит не упоминается): `Type=notify`, `ExecReload=/usr/sbin/apachectl graceful` — та же проверка перед перечитыванием; на сервере сверьте `systemctl cat apache2`. Оговорка: в 26.04 `apache2ctl` (Debian 2.4.66) под systemd передаёт `restart`/`graceful` после проверки конфигурации в `systemctl restart`/`reload`, а `stop` — в `systemctl stop`; то есть `apache2ctl restart` там равен проверке и `systemctl restart`, а не сигналу `SIGHUP` [Debian `apache2ctl` метки `debian/2.4.66-2`]. В 22.04 так же поступает правка Ubuntu для `restart`/`graceful` («use systemd for graceful», LP #1832182) — по журналу изменений jammy, сам сценарий не читался.

Что требует **полного** перезапуска (`restart`), а не `reload`:

- смена MPM, `ServerLimit`, `ThreadLimit` (при перезапуске игнорируются) [Apache-док];
- изменения `Listen`, конфликтующие со старыми сокетами (раздел 3.4) [Apache-док];
- новая публикация 1С на Apache, её отключение, смена версии платформы или пути к модулю — официальное требование 1С [ИТС-адм разд. 8.3.1];
- на Windows — любые изменения: новый дочерний процесс перечитывает конфигурацию сам (раздел 10.5) [Apache-док].

Безопасная последовательность: `sudo apache2ctl configtest && sudo systemctl restart apache2 && systemctl is-active apache2`.

## 4. Ошибки доступа и ограничения запроса: 403, 404, 401, 400, 408, 413, 414

### 4.1. 403 Forbidden

| Сообщение в `error.log` | Причина | Решение |
|---|---|---|
| `AH01630: client denied by server configuration: /srv/1c/www/demo/` (если файла нет — `… configuration: uri /путь`) | отказ правилами `Require` [Apache-код] | ниже: «Как найти правило» |
| `AH01797: client denied by server configuration: …` | то же, но отказал `mod_access_compat` (`Order`/`Allow`/`Deny` из 2.2) | переписать на `Require`; смешение старых и новых директив в одной области документация прямо называет «NOT WORKING AS EXPECTED» [Apache-док, `upgrading.html`] |
| `AH00035: access to /demo/ denied (filesystem path '/var/www/demo/default.vrd') because search permissions are missing on a component of the path` | у `www-data` нет права `x` на какой-то каталог пути | `namei -l /var/www/demo/default.vrd`; дать `o+x` или группу `www-data` на каталоги пути (`../1c/05`, раздел 6) [Apache-код] |
| `AH00132: file permissions deny server access: /var/www/…` | нет права чтения самого файла | права на файл; в 26.04 — ограничения юнита (`InaccessiblePaths=/root`, `/boot` и др.; `ProtectHome=read-only` чтению не мешает) [Debian `apache2.service` метки `debian/2.4.66-2`] |
| `AH00037: Symbolic link not allowed or link target not accessible: /var/www/…` | символическая ссылка при `Options -FollowSymLinks`, при `SymLinksIfOwnerMatch` с разными владельцами ссылки и цели, либо цель недоступна | `Options +FollowSymLinks` для каталога или класть файлы без ссылок [Apache-код] |
| `AH01276: Cannot serve directory /var/www/demo/: No matching DirectoryIndex (index.html,…) found, and server-generated directory index forbidden by Options directive` | запрошен каталог, индексного файла нет, листинг запрещён. Для публикации 1С — признак, что запрос обрабатывает **не модуль 1С** (нет `SetHandler 1c-application`, модуль не загружен) | для 1С — блок публикации и `apache2ctl -M \| grep 1cws` (`../1c/05`, ошибка 8) [Apache-код] |
| `AH10508: Unsafe URL with %3f URL rewritten without UnsafeAllow3F` | `RewriteRule` подставляет обратную ссылку, в которую попал закодированный `?`; с 2.4.60 такие подстановки блокируются (в Ubuntu 22.04/24.04 — с обновления 04.07.2024; частично смягчено 03.04.2025, LP #2103723) | переписать правило; флаг `[UnsafeAllow3F]` — только если подстановка заведомо безопасна [Apache-код, `CHANGES_2.4`, Ubuntu] |
| (без отдельного кода) правило `RewriteRule` в контексте сервера, где подстановка начинается с обратной ссылки или переменной, перестало находить файл после обновления | исправление CVE-2024-38475 (2.4.60) — такие подстановки больше не отображаются на произвольный путь ФС | флаг `UnsafePrefixStat` при условии, что подстановка ограничена; лучше переписать правило [Apache-док, `CHANGES_2.4`] |
| `AH02033: No hostname was provided via SNI for a name based virtual host` (уровень info) | `SSLStrictSNIVHostCheck on`, а клиент не прислал SNI (обращение по IP, очень старый клиент) | обращаться по имени; либо выключить строгую проверку [Apache-код, Apache-док] |
| `AH02222: Cannot find peer certificate chain`, `AH02039: Certificate Verification: Error (…)` | требуется клиентский сертификат | раздел 6.5 |
| 403 с текстом приложения (NetBox «CSRF verification failed», Redmine «Invalid form authenticity token») | не Apache: бэкенд не получил исходные `Host`/схему | раздел 5.4 |

**Как найти правило, которое отказало.** Включите `LogLevel warn authz_core:debug` (раздел 2.2) и повторите запрос: по каждому контейнеру и директиве в журнале появится `authorization result of Require ip 10.0.0.0/8: denied` или `granted`, итоговая — `authorization result of <RequireAny>: denied` [Apache-код]. Затем:

```bash
sudo apache2ctl -S                     # какой виртуальный хост обслуживает запрос
sudo grep -rn -E 'Require|<Directory|<Location|<Files' /etc/apache2/apache2.conf /etc/apache2/conf-enabled/ /etc/apache2/sites-enabled/
```

Частые причины `AH01630`:

1. **Каталог вне `/var/www` и `/usr/share`.** `apache2.conf` в Debian/Ubuntu содержит `<Directory /> … Require all denied` и разрешает только `/usr/share` и `/var/www/`; каталоги в `/srv` нужно разрешать явно [Debian `apache2.conf.in`, `NEWS.Debian`]. Блок `webinst` содержит своё разрешение, поэтому проблема возникает при ручной публикации или переносе каталога (например, в `/srv/1c/www`).
2. **`Require ip` и прокси перед Apache.** Если запросы приходят через nginx или другой прокси, Apache видит адрес прокси. `Require ip` проверяет адрес клиента, установленный `mod_remoteip`, только если тот включён и прокси перечислен в `RemoteIPInternalProxy`/`RemoteIPTrustedProxy` [Apache-док, `mod_remoteip`].
3. **Порядок секций.** `<Location>` применяется после `<Directory>`, и её правила авторизации заменяют разрешение из блока публикации (`../1c/05`, раздел 11.4); более общий `<Location "/">` с `Require` в конце конфигурации закроет всё, что разрешено выше.
### 4.2. 404 Not Found

| Признак | Причина | Решение |
|---|---|---|
| `AH00128: File does not exist: /var/www/html/demo` (уровень info) — путь из **`/var/www/html`** | запрос попал в хост по умолчанию (`000-default.conf`): `Host` не совпал ни с одним `ServerName`/`ServerAlias` нужного хоста, либо нужный хост слушает другой адрес/порт | `sudo apache2ctl -S`; `curl -H 'Host: …'`; дописать `ServerAlias` (короткое имя, имя с доменом, адрес) [Apache-код; Debian `README.Debian`, «Common Problems», п. 3 — тот же признак с `/etc/apache2/htdocs`] |
| публикация 1С отвечает 404, хотя каталог есть | Apache не перезапущен после публикации; регистр (`/Demo` ≠ `/demo`); блок публикации в файле другого хоста | `sudo systemctl restart apache2`; сверить имя с `-wsdir` (`../1c/05`, ошибка 6) |
| `Alias "/demo/" …` и запрос `/demo` без косой черты | если в `Alias` после URL-пути стоит `/`, сервер требует её и в запросе | писать `Alias "/demo" "/var/www/demo/"` [Apache-док, комментарий в `httpd.conf` дистрибутива] |
| 404 с подписью приложения (Redmine, NetBox) | бэкенд ждёт другой префикс пути: `ProxyPass /redmine http://127.0.0.1:3000/`, а приложение работает от корня (или наоборот) | согласовать префикс в `ProxyPass` и в настройке приложения (у Redmine — `relative_url_root`, ⚠ см. `../redmine/02-…`) |
| сервисы 1С (`/hs`, `/ws`, `/odata`) — 404 | не опубликованы в `default.vrd` | `../1c/05`, ошибки 16–18 |

URL в Apache чувствительны к регистру — и на Linux, и на Windows (`Alias`, `Location`, `ProxyPass`) [Apache-док, `platform/windows.html`].

### 4.3. 401 Unauthorized и 500 из-за аутентификации

| Сообщение | Причина | Решение |
|---|---|---|
| `AH01618: user ivanov not found: /demo/` | пользователя нет в файле `AuthUserFile` (или указан не тот файл) | `sudo grep '^ivanov:' /etc/apache2/.htpasswd-1c`; `sudo htpasswd -B /etc/apache2/.htpasswd-1c ivanov` [Apache-код] |
| `AH01617: user ivanov: authentication failure for "/demo/": Password Mismatch` | неверный пароль | сбросить пароль `htpasswd`; проверить раскладку/кодировку у клиента [Apache-код] |
| `(13)Permission denied: AH01620: Could not open password file: /etc/apache2/.htpasswd-1c` → 500 | файл паролей читает **рабочий процесс** (`www-data`), а права только у `root` | `sudo chown root:www-data …; sudo chmod 640 …` [Apache-код] |
| `AH01796: AuthType GSSAPI configured without corresponding module` → **500** | `AuthType` задан, модуль аутентификации не загружен | `sudo a2enmod auth_gssapi` (или нужный модуль) [Apache-код] |
| `AH01627: AuthType configured with no corresponding authorization directives` → **500** | есть `AuthType`, нет ни одного `Require` | добавить `Require valid-user` [Apache-код] |
| `AH01629: authorization failure (no authenticated user): /demo/` | требуется пользователь, а аутентификация не состоялась | смотреть строки выше: чем закончилась аутентификация [Apache-код] |
| `AH01631: user ivanov: authorization failure for "/demo/":` | пользователь опознан, но не проходит `Require` (группа, `Require user`) | правила `Require` [Apache-код] |
| 401 от сервиса 1С при верном пароле | заголовок `Authorization` занят Basic-аутентификацией Apache, а 1С ждёт свои учётные данные (или наоборот) | `../1c/05`, ошибка 19 и раздел 11.4 |

Kerberos — раздел 7.

### 4.4. Лимиты запроса: 400, 408, 413, 414

| Код | Сообщение (уровень) | Директива, умолчание | Где встречается на стенде |
|---|---|---|---|
| 400 | `AH00561: Request header exceeds LimitRequestFieldSize: Authorization` (info); в теле — `Size of a request header field exceeds server limit.`; варианты `AH00560 … after merging`, `AH00562 … after folding` | `LimitRequestFieldSize 8190` [Apache-док] | Kerberos: заголовок `Authorization: Negotiate …` у пользователя со множеством групп; большие cookie |
| 400 | `AH00563: Number of request headers exceeds LimitRequestFields` (info) | `LimitRequestFields 100` | редкие клиенты и прокси с длинной цепочкой заголовков |
| 414 | `AH00565: request failed: client's request-line exceeds LimitRequestLine (longer than 8190)` (info) | `LimitRequestLine 8190` | длинные запросы OData с `$filter`/`$select` к публикации 1С (ИТС описывает ту же проблему для IIS) [Apache-код; ИТС-адм разд. 8.10.2.4] |
| 413 | `AH01588: Requested content-length of N is larger than the configured limit of M` или `AH01591: Read content length of N is larger than the configured limit of M` (info) | `LimitRequestBody 1073741824` (1 ГиБ); в 2.4.53 и раньше — `0`, без ограничения [Apache-док] | загрузка больших файлов в 1С, вложения Redmine, импорт в NetBox. Каждый уровень (nginx, Apache-прокси, Apache с 1С, бэкенд) режет по-своему |
| 413 | `AH02018: request body exceeds maximum size (131072) for SSL buffer` | `SSLRenegBufferSize 131072` | POST в каталог, где клиентский сертификат требуется на уровне `<Location>`/`<Directory>` (раздел 6.5) [Apache-код, Apache-док] |
| 408 | `AH01382: Request header read timeout` / `Request body read timeout` (info) | `RequestReadTimeout handshake=0 header=20-40,MinRate=500 body=20,MinRate=500` (`mod_reqtimeout`, в Ubuntu включён) [Apache-док] | медленные клиенты, загрузка большого файла по плохому каналу (скорость ниже 500 байт/с), сканеры портов |
| 400 | `You're speaking plain HTTP to an SSL-enabled server port.` (в теле ответа) | — | `http://хост:443/…` [Apache-код] |
| 400 | `AH02031: Hostname X provided via SNI, but no hostname provided in HTTP request` | — | нестандартные клиенты и проверки доступности [Apache-код] |
| 421 | `AH02032: …` | `SSLVHostSNIPolicy` | раздел 6.4 |

Где поднимать лимиты [Apache-док]: `LimitRequestBody` действует в нужном хосте и даже в `<Directory>`/`<Location>`; а `LimitRequestFieldSize`, `LimitRequestLine`, `LimitRequestFields` (контексты `server config`/`virtual host`) при именных виртуальных хостах берутся из хоста **по умолчанию** для пары адрес:порт (первого в `apache2ctl -S`) — заголовки читаются до выбора хоста по `Host` (в коде — `r->server` в `protocol.c`). Поэтому задавайте их глобально (файл в `conf-available`) или в первом хосте этого адреса. Документация упоминает, что заголовки SPNEGO бывают до 12392 байт; на практике для Kerberos берут `LimitRequestFieldSize 65536` ⚠ [практика; ср. IIS — `../1c-windows/03-…`, раздел 10.6]; у nginx перед Apache — согласованно `large_client_header_buffers`, `client_max_body_size` [практика].

## 5. Обратный прокси: 500, 502, 503, 504

### 5.1. Схемы стенда и порядок разбора

| Хост | Цепочка | Роль Apache |
|---|---|---|
| `srv-1c-app` | клиент → (nginx или внешний Apache — необязательно) → Apache + `wsap24.so` → кластер 1С (TCP 1541, 1560–1591) | конечный веб-сервер; «бэкенд» для прокси перед ним |
| `srv-itsm` | клиент → Apache (TLS) → Puma `127.0.0.1:3000` (Redmine), gunicorn `127.0.0.1:8001` (NetBox) | обратный прокси |
| `srv-obs` | клиент → Apache или nginx (TLS) → GlitchTip `127.0.0.1:8000` (Docker), Grafana | обратный прокси |

Порядок разбора на хосте прокси:

```bash
curl -sv -o /dev/null http://127.0.0.1:3000/        # 1. бэкенд напрямую, минуя Apache
sudo ss -tlnp 'sport = :3000'                        # 2. кто и на каком адресе слушает (127.0.0.1 или ::1?)
systemctl status redmine --no-pager                  #    или: docker ps / docker logs <контейнер>
sudo grep -E 'AH0(0957|0959|0940|1114|1102|0898|1144)' /var/log/apache2/error.log | tail   # 3. что видел Apache
curl -sv -o /dev/null --resolve redmine.example.local:443:127.0.0.1 https://redmine.example.local/   # 4. через Apache
```
Если бэкенд в `ProxyPass` указан как `localhost`, имя может разрешиться сначала в `::1`, а контейнер Docker опубликован только на `127.0.0.1`. Неудачная попытка по первому адресу при наличии следующего пишется на уровне `debug`, по последнему — `error` [Apache-код: `AH00957`]; надёжнее сразу писать `http://127.0.0.1:<порт>/`.

### 5.2. Каталог ответов прокси

Строки журнала даны для 2.4.52 и новее (в них имя схемы пишется строчными: `http:`/`https:`) [Apache-код, метки 2.4.52/2.4.58/2.4.x].

| Код клиенту | Журнал Apache | Причина | Решение |
|---|---|---|---|
| **503** | `(111)Connection refused: AH00957: http: attempt to connect to 127.0.0.1:3000 (127.0.0.1:3000) failed` → `AH00959: ap_proxy_connect_backend disabling worker for (127.0.0.1:3000) for 60s` → `AH01114: HTTP: failed to make connection to backend: 127.0.0.1` | бэкенд не слушает (остановлен, перезапускается, слушает другой адрес или порт) | поднять бэкенд; проверить адрес в `ProxyPass` и `ss -tlnp` |
| **503** сразу, без попыток соединения | `AH00940: http: disabled connection for (127.0.0.1:3000)` | воркер в состоянии ошибки на время `retry` (по умолчанию 60 с) после неудачного соединения — даже если бэкенд уже работает | подождать `retry`; для единственного бэкенда задать `retry=0` (пробовать всегда) или `retry=5` в `ProxyPass` [Apache-док, Apache-код] |
| **503** | `(113)No route to host` / `(110)Connection timed out: AH00957 …` | бэкенд на другом хосте недоступен по сети: брандмауэр, маршрут | `nc -zv <хост> <порт>`; `ufw` на бэкенде; время соединения ограничивает `connectiontimeout=` (по умолчанию равен `timeout`) [Apache-док] |
| **503** | — (сразу при нехватке соединений в пуле) | задан `acquire=` и свободных соединений к бэкенду нет: Apache отвечает «SERVER_BUSY» | увеличить `max=` (по умолчанию — `ThreadsPerChild`) или убрать `acquire` [Apache-док] |
| **502** | `(70007)The timeout specified has expired: AH01102: error reading status line from remote server 127.0.0.1:3000` → `AH00898: Error reading from remote server returned by /issues/…` | бэкенд не начал отвечать за `timeout=`/`ProxyTimeout` (по умолчанию = `TimeOut`, в Ubuntu 300 с) — долгий отчёт, зависание приложения | разобраться с долгим запросом в приложении; при необходимости — `ProxyTimeout`/`timeout=` для конкретного пути [Apache-код; `TimeOut 300` — Debian] |
| **502** | `(104)Connection reset by peer: AH01102: error reading status line …` или `(70014)End of file found: AH01102 …`, чаще на первом запросе после паузы | гонка keep-alive: бэкенд закрыл простаивающее соединение из пула | раздел 5.3 |
| **502** | `AH01110: error reading response` | бэкенд оборвал соединение посреди ответа (падение процесса приложения, OOM) | журнал приложения; `journalctl -k \| grep -i oom` |
| **502** | `AH01097: pass request body failed to 127.0.0.1:3000 (127.0.0.1) from 10.0.0.15 ()` / `AH01084: pass request body failed to …` | бэкенд закрыл соединение, пока Apache передавал тело запроса (лимит размера у бэкенда, падение); при **таймауте** передачи тела — **504** | лимиты размера у бэкенда; при 504 — `timeout=` [Apache-код] |
| **500** | `AH01144: No protocol handler was valid for the URL /… (scheme 'http'). If you are using a DSO version of mod_proxy, make sure the proxy submodules are included in the configuration using LoadModule.` | включён `proxy`, но не `proxy_http` | `sudo a2enmod proxy_http && sudo systemctl restart apache2` [Apache-код] |
| **500** | `(EAI 2)Name or service not known: AH00898: DNS lookup failure for: backend.example.local returned by /…` | имя бэкенда не разрешается (код ответа 500 — по коду `proxy_util.c` ⚠ в отдельных путях обработки может быть иным) | `getent hosts backend.example.local`; запись в `/etc/hosts` или адрес вместо имени [Apache-код] |
| **500** | `AH00961: https: failed to enable ssl support for 192.0.2.5:443 (backend.example.local)` | бэкенд `https://`, а `SSLProxyEngine` не включён | `SSLProxyEngine on` в виртуальном хосте [Apache-код, Apache-док] |
| **502** (по документации) или **500** `Error during SSL Handshake with remote server` | `AH02003: SSL Proxy connect failed` + `SSL Library Error: …`; `AH02411: SSL Proxy: Peer certificate does not match for hostname X`; `AH02004: SSL Proxy: Peer certificate is expired` — всё на уровне **info** | TLS к бэкенду не прошёл: имя в `ProxyPass` не входит в сертификат бэкенда (часто — обращение по IP), сертификат истёк, нет общего протокола | раздел 5.6 [Apache-код, Apache-док `SSLProxyCheckPeerName`] |
| **503** | `AH10085: Init: <хост> will respond with '503 Service Unavailable' for now. There are no SSL certificates configured and no other module contributed any.` (при запуске) | у TLS-хоста нет сертификата, временный подставил модуль (например, `mod_md` ещё не получил сертификат) | настроить сертификат или дождаться `mod_md` [Apache-код] |
| **504** | — от Apache только при таймауте передачи тела запроса или в туннеле (`proxy_wstunnel`, `CONNECT`) | | `timeout=`; при 504 от **nginx** (`upstream timed out … while reading response header from upstream`) — `proxy_read_timeout` nginx (`../1c/05`, ошибка 21) [Apache-код; текст nginx — практика] |

Страница ошибки прокси в Apache имеет заголовок статуса `502 Proxy Error` (или другой код) и текст `The proxy server could not handle the request` с причиной (`Reason: …`) — по ней сразу видно, что ответил именно `mod_proxy`, а не бэкенд [Apache-код].

### 5.3. Гонка keep-alive с бэкендом

Apache держит пул постоянных соединений к бэкенду. Если бэкенд закрывает простаивающее соединение по своему таймауту, а Apache в этот момент отправляет в него запрос, запрос теряется: `AH01102 … error reading status line` с `(104)Connection reset by peer` или `(70014)End of file found`. Документация `mod_proxy_http` описывает именно этот случай и средство — переменную `proxy-initial-not-pooled` [Apache-док]:

```apache
# 1) не использовать соединение из пула для первого запроса клиентского соединения
#    (по документации снижает производительность, особенно для клиентов HTTP/1.0)
SetEnv proxy-initial-not-pooled 1

# 2) закрывать неиспользуемые соединения раньше, чем это сделает бэкенд (ttl в секундах)
ProxyPass        "/" "http://127.0.0.1:3000/" ttl=20
ProxyPassReverse "/" "http://127.0.0.1:3000/"

# 3) крайний вариант: не держать пул вообще (новое соединение на каждый запрос)
#ProxyPass "/" "http://127.0.0.1:3000/" disablereuse=On
```

`ttl` — время жизни неактивного соединения в пуле; `disablereuse=On` — закрывать соединение сразу после использования, рекомендуется при межсетевом экране, «тихо» обрывающем соединения [Apache-док]. Таймаут простоя на стороне бэкенда (Puma, gunicorn, uWSGI, Docker-прокси) смотрите в его документации и ставьте `ttl` меньше ⚠ [значения у конкретных бэкендов не сверялись]. Между хостами с межсетевым экраном пригодится и `keepalive=On` (TCP keep-alive на соединениях к бэкенду) [Apache-док]. Для nginx перед 1С — `../1c/05`, раздел 9.2.

### 5.4. Перенаправления, `Host`, схема и адрес клиента

| Симптом | Причина | Решение |
|---|---|---|
| после входа браузер уходит на `http://127.0.0.1:3000/…` | ответы бэкенда с `Location` на внутренний адрес не переписываются | `ProxyPassReverse` с тем же путём и адресом, что `ProxyPass` [Apache-док] |
| бэкенд строит ссылки с внутренним именем или портом | до бэкенда дошёл `Host` из `ProxyPass` (`127.0.0.1:3000`) | `ProxyPreserveHost On` — передать исходный `Host` (документация: обычно `Off`, нужно, когда бэкенд должен видеть исходное имя — это наш случай) [Apache-док] |
| перенаправление на `http://` вместо `https://`, бесконечный цикл перенаправлений («слишком много переадресаций») | бэкенд не знает, что клиент пришёл по HTTPS; `ProxyAddHeaders On` (по умолчанию) передаёт только `X-Forwarded-For`, `X-Forwarded-Host`, `X-Forwarded-Server` | в хосте `:443`: `RequestHeader set X-Forwarded-Proto "https"` (модуль `headers`) [Apache-док; для Redmine — `../redmine/02-…`] |
| NetBox: 403 «CSRF verification failed» при отправке формы | `Host`/схема не совпадают с ожидаемыми приложением | `ProxyPreserveHost On`, `X-Forwarded-Proto`, настройки доверенных источников NetBox (`../netbox/03-nastrojka-prava-api-vebhuki.md`) ⚠ точное имя параметра смотрите там |
| в журнале бэкенда у всех запросов адрес `127.0.0.1` | бэкенд не доверяет `X-Forwarded-For` | настроить доверие в приложении; для Apache за nginx — `mod_remoteip` (`../1c/05`, ошибка 28) |
| `AH00124: Request exceeded the limit of 10 internal redirects due to probable configuration error. Use 'LimitInternalRecursion' to increase the …` | цикл внутренних перенаправлений: `RewriteRule` или `ErrorDocument`, ведущие сами на себя | исправить правило; лимит не поднимать вслепую [Apache-код] |
| публикация 1С за прокси: после входа переход на `http://` или на внутренний адрес, ошибки ссылок навигации | платформа не восстановила внешний адрес | прокси должен передавать `X-Forwarded-Port`, `X-Forwarded-Host`, `X-Forwarded-Proto` и `X-Forwarded-For` [ИТС-адм разд. 8.10.3]. Если прокси — Apache: `ProxyPreserveHost On` + `ProxyAddHeaders On` (даёт `For`/`Host`) + `RequestHeader set X-Forwarded-Proto "https"` и `RequestHeader set X-Forwarded-Port "443"`; если nginx — `../1c/05`, раздел 9 |
### 5.5. Долгие запросы и большие тела по цепочке

| Звено | Сколько ждёт ответа | Сколько принимает тела |
|---|---|---|
| nginx перед Apache | `proxy_read_timeout` (60 с по умолчанию) | `client_max_body_size` (1 МБ по умолчанию) — `../1c/05`, раздел 9 |
| Apache — обратный прокси | `ProxyTimeout` / `timeout=` (по умолчанию = `TimeOut`) | `LimitRequestBody` (1 ГиБ с 2.4.54) |
| Apache с модулем 1С (`srv-1c-app`) | `TimeOut` (Apache — 60, в `apache2.conf` Ubuntu — 300) | `LimitRequestBody` |
| Бэкенд (Puma, gunicorn, 1С) | свой таймаут обработки | свой лимит |

Правило: каждое внешнее звено ждёт **не меньше**, чем внутреннее, и пропускает тело **не меньше**, чем внутреннее; иначе пользователь получит ошибку внешнего звена, а внутреннее продолжит работу впустую (`../1c/05`, раздел 12.3). Признаки нарушения: Apache-прокси — 502 с `AH01102 … (70007)`, nginx — 504, лимит тела — 413 на том звене, где он меньше. Для долгих операций 1С (отчёты, обмены, сервисы) правильнее фоновые задания, чем рост таймаутов (`../1c/05`, ошибка 21).

`TimeOut` — ожидание очередной порции ввода-вывода, а не «время обработки запроса» [Apache-док]; чтение запроса от клиента дополнительно ограничивает `RequestReadTimeout` (раздел 4.4).

### 5.6. TLS от Apache к бэкенду (`ProxyPass … https://…`)

| Директива | Умолчание | Что проверяет |
|---|---|---|
| `SSLProxyEngine` | `off` | без `on` прокси к `https://` не работает (`AH00961`, 500) |
| `SSLProxyVerify` | `none` | проверка **цепочки** сертификата бэкенда по `SSLProxyCACertificateFile`; по умолчанию цепочка не проверяется |
| `SSLProxyCheckPeerName` | `on` | имя из URL в `ProxyPass` должно быть в `subjectAltName`/CN сертификата бэкенда; при несовпадении — 502 |
| `SSLProxyCheckPeerExpire` | `on` | срок действия сертификата бэкенда |

[Apache-док, `mod_ssl`]. По коду 2.4.x проверки имени и срока выполняются **независимо** от `SSLProxyVerify none`, сообщения `AH02411`/`AH02004` пишутся на уровне `info` [Apache-код]. Следствия:

- `ProxyPass / https://192.0.2.5/` к бэкенду с сертификатом на имя — ошибка имени: указывайте в URL имя из сертификата (и при необходимости `/etc/hosts`), а не адрес. Расширение SNI к бэкенду Apache не отправляет для IP-адресов (RFC 6066 их запрещает) [Apache-код];
- отключать `SSLProxyCheckPeerName off` можно только во внутренней доверенной сети и осознанно: это отключает защиту от подмены бэкенда;
- полноценная проверка: `SSLProxyVerify require` + `SSLProxyCACertificateFile /usr/local/share/ca-certificates/corp-root.crt`.

Имя для SNI и для проверки имени в сертификате бэкенда по коду 2.4.x выбирается так: при `ProxyPreserveHost On` — исходный `Host` запроса клиента, иначе — имя из URL в `ProxyPass` (заметка соединения `proxy-request-hostname`; при смене имени переиспользуемое соединение закрывается) [Apache-код, `proxy_util.c`, `ssl_engine_io.c`]. Следствие: с `ProxyPreserveHost On` сертификат TLS-бэкенда должен содержать **внешнее** имя сайта, а если бэкенд — тоже Apache с несколькими TLS-хостами, SNI и `Host` к нему совпадут и 421 по этой причине не будет.

## 6. TLS и HTTPS: сертификаты, рукопожатие, цепочка, SNI

### 6.1. Ошибки запуска `mod_ssl`

| Сообщение | Причина | Решение |
|---|---|---|
| `SSLCertificateFile: file '/etc/letsencrypt/live/1c.example.local/fullchain.pem' does not exist or is empty` | путь неверен; certbot выпустил сертификат под другим именем (`…-0001`); файл пуст после неудачного копирования | `sudo ls -l /etc/letsencrypt/live/`; `sudo certbot certificates`; поправить путь [Apache-код; имена каталогов — сторонний: документация certbot] |
| `AH02565: Certificate and private key <id> from <сертификат> and <ключ> do not match` | ключ от другого сертификата (перевыпуск, перепутанные файлы) | сравнить хеши открытых ключей (раздел 2.4) [Apache-код] |
| `AH02562: Failed to configure certificate <id> (with chain), check <файл>` + `SSL Library Error: error:…` | файл не в PEM (DER, PKCS#12), испорчен, либо сертификат отвергнут OpenSSL: `…:SSL routines::ee key too small` (короткий ключ), `…::ca md too weak` (слабая подпись, например SHA-1) | перевести в PEM (`openssl x509 -inform der …`), перевыпустить сертификат с RSA ≥ 2048 и SHA-256 [Apache-код; тексты причин — сторонний: OpenSSL 3.0; ⚠ какие именно длины ключей отвергаются при уровне безопасности OpenSSL по умолчанию в вашем выпуске Ubuntu — не сверялось] |
| `AH02564: Failed to configure encrypted (?) private key <id>, check <файл>` | ключ не удалось загрузить: он зашифрован паролем или файл не читается как ключ. В Ubuntu `mods-available/ssl.conf` задаёт `SSLPassPhraseDialog exec:/usr/share/apache2/ask-for-passphrase`: без терминала сценарий спрашивает пароль через `systemd-ask-password`, и запуск службы ждёт ввода (при загрузке — на консоли), пока его не оборвёт таймаут юнита; если пароль не получен или неверен, запуск прекращается уже на `AH02580 … Pass phrase incorrect`, `AH02579 … Private key not found` или `AH02578 … Unable to read pass phrase` [Debian `ask-for-passphrase`, `ssl.conf`; Apache-код `ssl_engine_pphrase.c`] | снять пароль: `sudo openssl pkey -in enc.key -out /etc/ssl/private/1c.key`, `sudo chmod 600 /etc/ssl/private/1c.key` (ключ читает процесс-родитель от `root`) [Apache-код, Apache-док; Debian `README.Debian`] |
| `AH02572: Failed to configure at least one certificate and key for <хост>` | в хосте `SSLEngine on`, но ни одна пара сертификат+ключ не настроена | `SSLCertificateFile` и `SSLCertificateKeyFile` в этом хосте [Apache-код] |
| `AH01909: <id> server certificate does NOT include an ID which matches the server name` (warning) | `ServerName` хоста не входит в сертификат (сертификат «на всякий случай», `snakeoil`, выпуск на IP) | перевыпустить с правильным `subjectAltName`; клиенты 1С на несовпадение имени отвечают ошибкой проверки (`../1c/05`, ошибка 24) [Apache-код] |
| `AH01906: <id> server certificate is a CA certificate (BasicConstraints: CA == TRUE !?)` | в `SSLCertificateFile` первым стоит сертификат ЦС, а не сервера (перепутан порядок в файле цепочки) | первым — сертификат сервера, затем промежуточные [Apache-код] |
| `AH01903: Failed to configure CA certificate chain!` | испорчен `SSLCertificateChainFile`/файл цепочки | собрать цепочку заново [Apache-код] |

Права на ключ: в Debian/Ubuntu ключ должен быть доступен только `root` — его читает родительский процесс до сброса привилегий, давать доступ `www-data` не нужно [Debian `README.Debian`]. В Ubuntu 26.04 ключи и сертификаты в `/root` Apache не увидит (`InaccessiblePaths=/root` в юните, `../1c/05`, раздел 6.1).

### 6.2. Рукопожатие не проходит

Сообщения о сбоях рукопожатия `mod_ssl` пишет на уровне **info**: `AH02008: SSL library error 1 in handshake (server srv-1c-app.example.local:443)` и следом `SSL Library Error: error:<код>:SSL routines::<причина>` [Apache-код]. При штатном `LogLevel warn` их нет — включите `LogLevel warn ssl:info`.

| Что видит клиент | Причина в журнале (`ssl:info`) | Объяснение | Решение |
|---|---|---|---|
| `curl: (35) … wrong version number`; Firefox `SSL_ERROR_RX_RECORD_TOO_LONG`; Chrome `ERR_SSL_PROTOCOL_ERROR` [клиентские тексты — практика] | при запуске: `AH01916: Init: (<хост>:443) You configured HTTP(80) on the standard HTTPS(443) port!` (числа в скобках — константы 80 и 443, уровень warning) | на 443 отвечает хост без `SSLEngine on` | `sudo apache2ctl -S` — какие хосты слушают `*:443`; в каждом — `SSLEngine on` [Apache-код] |
| страница `400 Bad Request … You're speaking plain HTTP to an SSL-enabled server port.` | `…::http request` | клиент пришёл по `http://` на TLS-порт | исправить адрес (или перенаправление с 80) [Apache-код, сторонний: OpenSSL] |
| ошибка соединения у старого клиента (старые Windows, Java, встроенные устройства, старые сборки тонкого клиента) | `…::no shared cipher` | нет общего набора шифров (жёсткий `SSLCipherSuite`; у сервера только ECDSA-сертификат) | обновить клиента; при крайней необходимости — отдельный хост с расширенным набором шифров [сторонний: OpenSSL] |
| то же | `…::unsupported protocol` | клиент умеет только TLS 1.0/1.1, а сервер — 1.2/1.3 | обновить клиента; не возвращать TLS 1.0/1.1 на общий хост (`apache/02-…`) [сторонний: OpenSSL] |
| ничего (клиент сам закрыл соединение) | `…::unexpected eof while reading`, `AH02007: SSL handshake interrupted by system [Hint: Stop button pressed in browser?!]` (debug) | проверка доступности по TCP, сканер, обрыв на стороне клиента | шум; если массово — смотреть, кто подключается |
| `curl: (60)`, `NET::ERR_CERT_AUTHORITY_INVALID`, тонкий клиент 1С «Удалённый узел не прошёл проверку» | на сервере ошибок нет | цепочка или доверие к корню — раздел 6.3; несовпадение имени — раздел 6.1 (`AH01909`) | |

Ищите в журнале по тексту причины, а не по шестнадцатеричному коду: формат строки у OpenSSL 1.1 и 3.x разный [сторонний: OpenSSL 3.0 `openssl.txt`]. Проверка снаружи — `openssl s_client … -brief` и `-tls1_2`/`-tls1_3` (раздел 2.4).

### 6.3. Цепочка сертификатов

- С Apache 2.4.8 промежуточные сертификаты кладут в тот же файл `SSLCertificateFile` после сертификата сервера; `SSLCertificateChainFile` устарела [Apache-док]. Порядок: сервер → промежуточный(е) → (корень не обязателен).
- certbot: в `SSLCertificateFile` — `fullchain.pem`, в `SSLCertificateKeyFile` — `privkey.pem` из `/etc/letsencrypt/live/<имя>/`; файлы в `live` обновляются при продлении, указывайте путь к ним, а не копии [сторонний: документация certbot, раздел «Where are my certificates?»]. Если указан `cert.pem` — промежуточного сертификата нет.
- Симптом неполной цепочки: браузеры открывают сайт (часть из них сама догружает промежуточные сертификаты), а `curl`, Java, тонкий клиент 1С и HTTP-клиент платформы — нет; `openssl s_client` показывает в `Certificate chain` один сертификат и `Verify return code: 21 (unable to verify the first certificate)` [сторонний: OpenSSL; поведение отдельных клиентов — практика].
- Свой ЦС организации: клиенты должны доверять корню (Windows — хранилище «Доверенные корневые центры сертификации», Linux — `/usr/local/share/ca-certificates` + `sudo update-ca-certificates`, тонкий клиент 1С — `../1c/05`, раздел 8.3).
- Сертификат продлён, а клиенты видят старый: Apache читает файлы только при запуске и перезапуске — нужен `reload` после продления (deploy-hook certbot, `apache/02-…`) [Apache-док].

### 6.4. SNI, несколько HTTPS-хостов на одном адресе и 421 Misdirected Request

Как Apache выбирает хост для TLS: сертификат — по имени из SNI в начале рукопожатия; затем запрос направляется по заголовку `Host`. Без SNI (обращение по IP-адресу, очень старый клиент) используется **первый** хост для этой пары адрес:порт — в выводе `apache2ctl -S` он помечен `default server` [Apache-док, Apache-код].

| Симптом | Причина | Решение |
|---|---|---|
| отдаётся сертификат «не того» хоста | клиент не прислал SNI (обращение по IP, IP-адреса в SNI запрещены) или имя не входит в `ServerName`/`ServerAlias` никакого хоста | обращаться по имени; дописать `ServerAlias`; сделать хостом по умолчанию тот, чей сертификат нужен большинству |
| `421 Misdirected Request`; `AH02032: Hostname <имя-SNI> provided via SNI and hostname <имя-Host> provided via HTTP have no compatible SSL setup for policy 'secure'` (2.4.66+; в 2.4.52/2.4.58 без `for policy …`; без SNI — `(default host as no SNI was provided)`) | один TLS-соединением запрошены два хоста с несовместимыми настройками TLS: браузер переиспользует соединение HTTP/2 для другого имени из того же сертификата (SAN или маска) [практика]; проверка доступности ходит по IP с чужим `Host`; прокси отправляет SNI одного имени и `Host` другого | см. ниже [Apache-код, Apache-док] |
| 403 + `AH02033 … No hostname was provided via SNI …` | `SSLStrictSNIVHostCheck on` и клиент без SNI | раздел 4.1 |
| 400 + `AH02031` | SNI есть, `Host` нет | нестандартный клиент |

**Политика `SSLVHostSNIPolicy`** (контекст — только `server config`, значения `strict | secure | authonly | insecure`, по умолчанию `secure`) [Apache-док]:

| Политика | Любое расхождение хостов | Различаются сертификат/ключ или ограничения протоколов и шифров | Различаются настройки проверки клиента (`SSLVerifyClient`, `SSLCACertificatePath`, `SSLOpenSSLConfCmd` и др.) |
|---|---|---|---|
| `strict` | блокируется | блокируется | блокируется |
| `secure` (умолчание) | разрешено | блокируется | блокируется |
| `authonly` | разрешено | разрешено | блокируется |
| `insecure` | разрешено | разрешено | разрешено (уязвимо к CVE-2025-23048) |

История: проверка ужесточена в 2.4.64 (CVE-2025-23048 — обход проверки клиентских сертификатов при возобновлении сессии TLS 1.3), `SSLVHostSNIPolicy` введена в 2.4.66 [Apache-док, `CHANGES_2.4`]; в Ubuntu — обновления 14.07.2025 (`4.15`/`8.7`), регрессия LP #2117112 и смягчение 09.12.2025 (`4.18`/`8.10`) — таблица 9.3 [Ubuntu]. ⚠ Умолчание в заплатке Ubuntu, по-видимому, `secure`, как в апстриме; текст заплатки не читался.

Что делать при 421:

1. Сравнить TLS-настройки хостов на одном `IP:443`: `sudo apache2ctl -S`, затем `grep -n -E 'SSLProtocol|SSLCipherSuite|SSLVerifyClient|SSLCACertificate|SSLOpenSSLConfCmd' /etc/apache2/sites-enabled/*.conf`.
2. Лучшее решение — одинаковые протоколы и шифры (вынести их в общий файл `conf-available`, а не задавать по-разному в каждом хосте); тогда `secure` пропустит разные сертификаты.
3. Если хосты действительно должны различаться сертификатами и шифрами, но **клиентские сертификаты нигде не используются** — `SSLVHostSNIPolicy authonly` в глобальной части конфигурации.
4. Хост с проверкой клиентских сертификатов — на отдельный адрес или порт.

### 6.5. Клиентские сертификаты (если используются)

| Сообщение | Причина | Решение |
|---|---|---|
| `AH02039: Certificate Verification: Error (20): unable to get local issuer certificate` | в `SSLCACertificateFile` нет ЦС, выдавшего клиентский сертификат | добавить цепочку ЦС клиентов [Apache-код] |
| `AH02222: Cannot find peer certificate chain` → 403 | клиент не предъявил сертификат | настройки клиента/браузера [Apache-код] |
| `AH02018: request body exceeds maximum size (131072) for SSL buffer` → 413 | сертификат требуется на уровне каталога, а не хоста: при TLS 1.2 нужна повторная выработка ключей, тело POST буферизуется в пределах `SSLRenegBufferSize` | `SSLVerifyClient` на уровне `<VirtualHost>` либо увеличить `SSLRenegBufferSize` [Apache-код, Apache-док] |
| `AH10158: cannot perform post-handshake authentication` | при TLS 1.3 требование сертификата на уровне каталога выполняется «аутентификацией после рукопожатия», которую клиент не поддерживает | `SSLVerifyClient` на уровне хоста [Apache-код; ⚠ поддержка клиентами не сверялась] |

## 7. Kerberos (SPNEGO): `mod_auth_gssapi`, `mod_auth_kerb`

Настройка — `apache/02-…` и `../1c/05`, раздел 11.3. Ход обмена: Apache отвечает 401 с `WWW-Authenticate: Negotiate` → браузер получает у контроллера домена билет на `HTTP/<полное имя сервера>@<ОБЛАСТЬ>` и повторяет запрос с `Authorization: Negotiate <токен>` → модуль расшифровывает билет ключом из keytab. Если Kerberos не получился, браузеры на Windows, отдающие проверку подсистеме Windows (Chrome, Edge, старый IE), по умолчанию переходят на NTLM и показывают окно ввода пароля, даже если сервер NTLM не поддерживает; Firefox NTLM по умолчанию не использует [сторонний: README mod_auth_gssapi].

### 7.1. Проверки

```bash
# на сервере Apache
sudo klist -k -t -e /etc/apache2/http.keytab          # принципалы, KVNO, типы шифрования (пакет krb5-user)
sudo -u www-data klist -k /etc/apache2/http.keytab    # читается ли keytab от имени рабочих процессов
timedatectl; chronyc tracking                         # расхождение времени с контроллером домена
getent hosts srv-1c-app.example.local              # имя → адрес; обратная запись — getent hosts <адрес>
# с клиента Linux в домене
kinit ivanov@EXAMPLE.LOCAL
kvno HTTP/srv-1c-app.example.local@EXAMPLE.LOCAL   # KVNO ключа в домене — должен совпасть с keytab
curl -sv --negotiate -u : https://srv-1c-app.example.local/demo/ -o /dev/null
```

На клиенте Windows: `klist` (есть ли билет `HTTP/…`), `klist purge`, `setspn -Q HTTP/srv-1c-app.example.local`, `setspn -X` (дубликаты SPN) [практика]. В журнале — `LogLevel warn auth_gssapi:debug`; `GssapiPublishErrors On` кладёт ошибку в переменные `MAG_ERROR`, `MAG_ERROR_TEXT`, `GSS_ERROR_MAJ`, `GSS_ERROR_MIN` (в журнал доступа — `%{MAG_ERROR_TEXT}e`) [сторонний: README mod_auth_gssapi]. Трассировка MIT — `Environment=KRB5_TRACE=/var/log/apache2/krb5/trace.log` через `sudo systemctl edit apache2` (каталог с записью для `www-data`) ⚠ [сторонний: MIT krb5; не проверялось].

### 7.2. Сообщения и причины

`mod_auth_gssapi` пишет ошибки строкой `<тип> <контекст>: [<основная причина> (<уточнение>)]`; типы — `GSS ERROR`, `INTERNAL ERROR`, `AUTH NOT ALLOWED` (уровень error) и `NO AUTH DATA` (уровень info, когда заголовка `Authorization` нет вовсе — `Client did not send any authentication headers`; error — при испорченном или неизвестном заголовке). Для SPNEGO контекст — `In Negotiate Auth: gss_accept_sec_context() failed`; короткое `gss_accept_sec_context()` бывает только у Basic-входа через GSSAPI (`GssapiBasicAuth`) [сторонний: исходный код mod_auth_gssapi, метка `v1.6.4` — версия пакета Ubuntu 24.04]. Основная причина и уточнение — тексты библиотеки MIT krb5 [сторонний: MIT krb5, `g_dsp_status.c`, `rd_req_dec.c`, `krb5_err.et`].

| Сообщение (фрагмент) | Причина | Решение |
|---|---|---|
| окно логина в браузере, 401 по кругу; при `info` — `NO AUTH DATA Client did not send any authentication headers` | браузер не прислал токен: адрес не в зоне «Местная интрасеть» (Firefox — не в `network.negotiate-auth.trusted-uris`), обращение по IP или по имени без SPN, компьютер не в домене [практика] | заходить по полному имени, на которое выдан SPN; настроить зону/политику браузера |
| `GSS ERROR In Negotiate Auth: gss_accept_sec_context() failed: [An unsupported mechanism was requested (…)]` | пришёл токен NTLM вместо Kerberos (Kerberos у клиента не получился) | искать, почему нет билета: SPN, дубликат SPN, время, зона браузера; ⚠ точный текст уточнения не сверялся |
| `… [Unspecified GSS failure.  Minor code may provide more information (Request ticket server HTTP/… kvno 5 not found in keytab; keytab is likely out of date)]` | keytab выпущен до смены пароля учётной записи или до повторного `ktpass` — KVNO в домене больше | перевыпустить keytab, сверить `kvno` и `klist -k` |
| `… (Request ticket server … kvno N not found in keytab; ticket is likely out of date)` | у клиента старый билет, keytab уже новый | `klist purge` на клиенте или дождаться истечения билета |
| `… (Request ticket server HTTP/… not found in keytab (ticket kvno N))` | в keytab нет принципала для имени, по которому обратились (другой алиас, CNAME) | keytab с принципалом для этого имени; `GssapiAcceptorName` при нескольких принципалах [сторонний: README] |
| `… (Cannot find key for HTTP/… kvno N in keytab)` | принципал есть, но нет ключа нужного KVNO или типа шифрования (билет AES256, а в keytab только RC4) | перевыпустить keytab с нужным шифрованием (`-crypto AES256-SHA1` в `ktpass`, `../1c/05`, 11.3) и включить AES у учётной записи [практика] |
| `… (Server principal … does not match request ticket server …)` | `GssapiAcceptorName` или имя в keytab не совпадает с именем в билете | согласовать имена |
| `… (Clock skew too great)` | расхождение времени клиента/сервера/контроллера домена | синхронизировать время (`chrony`, `../linux/09-…`) |
| `GSS ERROR gss_acquire_cred[_from]() failed to get server creds: […]` | Apache не может прочитать keytab: путь, права (`www-data`), keytab в `/root` при Ubuntu 26.04 | `sudo -u www-data klist -k <keytab>`; keytab в `/etc/apache2`, владелец `www-data`, права `600` |
| `failed to store delegated creds: […]` (без префикса `GSS ERROR`), `creating unique ccache file … failed` | нет каталога `GssapiDelegCcacheDir` или прав на запись (каталог в `/run` исчезает после перезагрузки) | создавать каталог через `systemd-tmpfiles` (`../1c/05`, 11.3) [сторонний: исходный код] |
| `S4U2 Proxy requested but GssapiDelegCcacheDir is not set. Constrained delegation disabled!` | `GssapiUseS4U2Proxy On` без каталога кешей | задать `GssapiDelegCcacheDir` [сторонний: исходный код] |
| 400 `Size of a request header field exceeds server limit.` (`AH00561`, info) | билет пользователя с большим числом групп не помещается в `LimitRequestFieldSize` | раздел 4.4 |
| 500 + `AH01796: AuthType GSSAPI configured without corresponding module` | модуль не включён | `sudo a2enmod auth_gssapi` |
| в журнале доступа есть имя `ivanov@EXAMPLE.LOCAL`, а 1С не пускает | Apache свою часть выполнил; не сработало сопоставление с пользователем 1С `\\DOMAIN\user` или делегирование учётных данных | `../1c/05`, раздел 11.3 (там же ⚠ о `mod_auth_gssapi` с 1С) |

Для `mod_auth_kerb` (Ubuntu 22.04, официальный рецепт 1С) тексты сообщений другие; здесь они не сверялись ⚠.

## 8. Перегрузка и зависания — признаки (настройка — `apache/03-…`)

| Сообщение | Значение |
|---|---|
| `AH00484` (event), `AH00286` (worker), `AH00161` (prefork): `server reached MaxRequestWorkers setting, consider raising the MaxRequestWorkers setting` | все рабочие потоки/процессы заняты; новые соединения ждут в очереди `ListenBackLog` (511). Пишется один раз за запуск [Apache-код, Apache-док] |
| `AH10159` (event) / `AH00287` (worker): `server is within MinSpareThreads of MaxRequestWorkers, consider raising the MaxRequestWorkers setting` | запас потоков почти исчерпан [Apache-код] |
| `AH03490: scoreboard is full, not at MaxRequestWorkers.Increase ServerLimit.` (event) | не хватает мест для процессов (в том числе завершающихся после `graceful`) [Apache-код] |
| `AH00326: Server ran out of threads to serve requests. Consider raising the ThreadsPerChild setting` | то же на Windows (`mpm_winnt`) [Apache-код] |
| `AH00156: Couldn't create pollset in child; check system or user limits` (prefork; у worker — `AH03285 … in thread; …`, у event — `AH00495: Couldn't create a Thread Safe Pollset…`) | исчерпан `fs.epoll.max_user_instances` [Debian `README.Debian`, п. 4 — там текст приведён как «check user or system limits»; точные строки — Apache-код] |
| `ulimit: open files: cannot modify limit: Operation not permitted` | контейнер или ограничение не дают `apache2ctl` поднять лимит файлов; настраивается `APACHE_ULIMIT_MAX_FILES` в `envvars` (по умолчанию `ulimit -n 8192`) [Debian] |
| `mod_rewrite: could not create rewrite_log_lock` | после `kill -9` остались семафоры SysV; Debian предлагает удалить семафоры `www-data` (`ipcs -s`, `ipcrm sem`) — только при остановленном Apache [Debian `README.Debian`, п. 2] |

Для 1С: все потоки Apache заняты, а процессор веб-сервера простаивает — узкое место дальше (кластер, СУБД, блокировки), а не Apache (`../1c/05`, ошибка 30).

## 9. Что проверять после обновления пакета `apache2` (и ОС)

### 9.1. Перед обновлением

```bash
apt list --upgradable 2>/dev/null | grep -E '^(apache2|libapache2)'
apt changelog apache2 2>/dev/null | head -n 80        # ищите «SECURITY REGRESSION» и упоминания SNI, rewrite, ssl
B=/root/apache-before-$(date +%F); sudo mkdir -p "$B"
sudo apache2ctl -M 2>&1 | sort | sudo tee "$B/modules.txt" >/dev/null
sudo apache2ctl -S 2>&1        | sudo tee "$B/vhosts.txt"  >/dev/null
dpkg -l 'apache2*' 'libapache2-mod-*' | awk '/^ii/{print $2,$3}' | sudo tee "$B/versions.txt" >/dev/null
sudo tar -czf "$B/etc-apache2.tgz" -C / etc/apache2
```

Особенности стенда (`../linux/04-pakety-apt.md`):

- с `"apache2"` в `Unattended-Upgrade::Package-Blacklist` обновления безопасности Apache ставятся **только вручную** — планируйте окно обслуживания;
- `needrestart` (24.04+) перезапускает службы после обновления библиотек; при исключении `apache2.service` Apache работает со старой библиотекой до вашего перезапуска;
- `webinst` пишет публикации в `/etc/apache2/apache2.conf` — конфигурационный файл пакета: при новом `apache2.conf` в пакете dpkg спросит, что делать — оставляйте свой (`N`) и сравните с `.dpkg-dist`; лучше держать публикации в `conf-available` (`../1c/05`, 4.4, 4.6).

### 9.2. После обновления

```bash
dpkg -l 'apache2*' | awk '/^ii/{print $2,$3}'
systemctl status apache2 --no-pager; sudo apache2ctl -t
diff <(sudo apache2ctl -M 2>&1 | sort) "$B/modules.txt"     # $B — каталог из 9.1
diff <(sudo apache2ctl -S 2>&1) "$B/vhosts.txt"
sudo journalctl -u apache2 --since "-1h" --no-pager | tail -n 30
sudo grep -E '\[(core|ssl|proxy|rewrite)[^]]*:(error|crit|alert|emerg)\]|AH02032|AH10508|AH10510' /var/log/apache2/error.log | tail -n 20
sudo find /etc/apache2 -name '*.dpkg-*'                      # .dpkg-dist / .dpkg-old после вопросов dpkg
for u in https://srv-1c-app.example.local/demo/ https://redmine.example.local/ https://netbox.example.local/; do
  printf '%s -> ' "$u"; curl -s -o /dev/null -w '%{http_code}\n' --max-time 20 "$u"; done
echo | openssl s_client -connect srv-1c-app.example.local:443 -servername srv-1c-app.example.local -brief 2>&1 | head -n 5
```

Для публикации 1С дополнительно — проверки из `../1c/05`, раздел 7.1 (модуль загружен, веб-клиент и сервисы отвечают).

### 9.3. Изменения поведения, приходившие обновлениями безопасности

| Апстрим | Что изменилось | Ubuntu 22.04 / 24.04 (пакет, дата) | Симптом | Что делать |
|---|---|---|---|---|
| 2.4.54 | умолчание `LimitRequestBody` 0 → 1 ГиБ | 24.04 и 26.04 — есть (2.4.58/2.4.66); 22.04 — ⚠ неясно (`../1c/05`, 12.3): по журналу изменений `2.4.52-1ubuntu4.1` (14.06.2022) заплатка CVE-2022-29404 правит только `mod_lua` (`lua_request.c`), смена умолчания в ядре не упомянута — вероятно, осталось `0` | 413 на файлах больше 1 ГиБ | `LimitRequestBody` явно |
| 2.4.60 (01.07.2024) | `mod_rewrite`: `UnsafeAllow3F`, `UnsafePrefixStat`; обработчики через `AddType` надо переводить на `AddHandler` | `4.10` / `8.2` (04.07.2024); смягчение — `4.14` / `8.6` (03.04.2025, LP #2103723), `4.16` / `8.8` (11.08.2025, LP #2119395) | 403 + `AH10508` | раздел 4.1 [Apache-док, Ubuntu] |
| 2.4.64 (10.07.2025) | удалён `SSLEngine optional` (CVE-2025-49812); строже проверка SNI ↔ `Host` (CVE-2025-23048) | `4.15` / `8.7` (14.07.2025) | `AH10510`; 421 + `AH02032` | раздел 6.4 |
| 2.4.66 (04.12.2025) | `SSLVHostSNIPolicy`; `ListenTCPDeferAccept` | `4.18` / `8.10` (09.12.2025) — только `SSLVHostSNIPolicy` | 421 исчезают при совместимых хостах | раздел 6.4 |
| 2.4.67–2.4.69 (05–10.2026) | ограничены файловые функции выражений `ap_expr` в `.htaccess` (`mod_rewrite`, `mod_setenvif`, `mod_proxy_fcgi`, `SSLRequire`) — CVE-2026-24072, CVE-2026-44119, CVE-2026-59797 | `4.20` / `8.12` (05.05.2026), `4.23` / `8.15` (06.07.2026), `4.24` / `8.16` (05.10.2026) | выражение `ap_expr` в `.htaccess` с файловой функцией (`file()`, `filesize()`; например, в `RewriteCond expr …`, `SetEnvIfExpr`, `SSLRequire`) не разбирается: `… not available in restricted context` — ошибка `.htaccess`, запросы к каталогу получают 500. Уточнено 20.10.2026 по `server/util_expr_eval.c` ветки 2.4.x (2.4.69: в `.htaccess` всегда ставится флаг `AP_EXPR_FLAG_RESTRICTED_FILE_FUNC`); промежуточный вариант 2.4.67 (флаг `AP_EXPR_FLAG_RESTRICTED` в `mod_rewrite`, `mod_setenvif`, `mod_proxy_fcgi`) запрещал и проверки `-f`, `-d`… ⚠ по журналам Ubuntu так было в пакетах с 05.05 по 06.07.2026 — не проверялось. Обычный `RewriteCond … -f` (без `expr`) не затронут | переносить такие правила из `.htaccess` в конфигурацию сервера [Apache-док, Apache-код, Ubuntu] |

Номера пакетов: 22.04 — `2.4.52-1ubuntu4.N`, 24.04 — `2.4.58-1ubuntu8.N` [Ubuntu, журналы изменений `apache2_2.4.52-1ubuntu4.24` и `apache2_2.4.58-1ubuntu8.16`].

**Переход 24.04 → 26.04** (`do-release-upgrade`): Apache 2.4.58 → 2.4.66; юнит `apache2.service` с ограничениями systemd (`MemoryDenyWriteExecute=yes`, `ProtectHome=read-only`, `InaccessiblePaths=/root` и др.) — для модуля 1С нужен drop-in **до** обновления (`../1c/05`, раздел 6.1); `SSLVHostSNIPolicy` есть изначально. После перехода — те же проверки 9.2.

## 10. Apache на Windows

Публикация 1С на Apache под Windows — `../1c-windows/03-veb-publikaciya-iis.md`, раздел 13, и методичка [ИТС-мет 5978, 2020]. Здесь — общие сведения и типовые сбои самого Apache.

### 10.1. Где взять сборку

- Проект Apache HTTP Server **не выпускает** двоичные сборки, только исходный код; документация называет популярные сторонние варианты — Apache Lounge и WampServer [Apache-док, `platform/windows.html`].
- Apache Lounge на 20.10.2026: `httpd-2.4.69-261002-Win64-VS18.zip` и `…-win32-vs18.zip` от 02.10.2026, собраны Visual Studio 2026 (VS18); требуется Visual C++ Redistributable 2017–2026 (14.51.36247, `vc_redist_x64`); не работают на XP, 7 SP1 и Server 2003; публикуются подписи PGP и суммы SHA — сверяйте (`Get-FileHash … -Algorithm SHA256`) [сторонний: apachelounge.com/download]. Без пакета Redistributable `httpd.exe` не запустится из-за отсутствующих библиотек времени выполнения ⚠ [практика].
- Разрядность Apache должна совпадать с разрядностью модуля 1С; 32-разрядная 1С с 64-разрядным Apache не поддерживается [ИТС-адм разд. 8.3.1].

### 10.2. Раскладка и отличия от Ubuntu

| | Ubuntu (Debian) | Windows (сборка ASF-раскладки, например Apache Lounge в `C:\Apache24`) |
|---|---|---|
| Программа | `/usr/sbin/apache2` через `apache2ctl` | `C:\Apache24\bin\httpd.exe` |
| Главный файл | `/etc/apache2/apache2.conf` | `C:\Apache24\conf\httpd.conf` |
| Модули | `a2enmod` / `a2dismod` (ссылки в `mods-enabled`) | раскомментировать `LoadModule …_module modules/mod_….so` в `httpd.conf` |
| Сайты | `sites-available` + `a2ensite` | `Include conf/extra/httpd-vhosts.conf` (в стандартном `httpd.conf` закомментирован) или свой `Include` [Apache-док, `httpd.conf` дистрибутива] |
| TLS | `a2enmod ssl` + `a2ensite default-ssl` | раскомментировать `LoadModule ssl_module`, `LoadModule socache_shmcb_module` и `Include conf/extra/httpd-ssl.conf`; в сборке из методички ИТС — файл `conf/extra/httpd-ahssl.conf` [Apache-док; ИТС-мет 5978] |
| Переменные | `envvars` (`${APACHE_LOG_DIR}`) | `Define` в `httpd.conf`; в сборке из методички пути пишутся через `${SRVROOT}` [ИТС-мет 5978] |
| MPM | `event`, `worker`, `prefork` | только `mpm_winnt`: один родитель + один дочерний процесс с потоками [Apache-док] |
| Учётная запись | `www-data` | учётная запись службы (по умолчанию LocalSystem) |
| Проверки | `apache2ctl -t`, `-S`, `-M` | `httpd.exe -t`, `-S`, `-M`; с `-n "<служба>"` — по конфигурации службы |

Правила `httpd.conf` на Windows [Apache-док]: пути — прямыми косыми чертами (`"C:/Apache24/htdocs"`), обратная косая может быть воспринята как экранирование; URL чувствительны к регистру, хотя файловая система — нет, поэтому доступ к файлам ограничивают `<Directory>`, а не `<Location>`.

### 10.3. Служба

Командная строка **от имени администратора** [Apache-док, Apache-код]:

```bat
cd /d C:\Apache24\bin
httpd.exe -t                                   :: Syntax OK
httpd.exe -k install                           :: служба "Apache2.4", конфигурация conf\httpd.conf
httpd.exe -k install -n "Apache2.4-83" -f "C:\Apache24\conf\httpd-83.conf"   :: второй экземпляр
httpd.exe -n "Apache2.4" -t                    :: проверка конфигурации, записанной в службу
httpd.exe -k start -n "Apache2.4"
httpd.exe -k restart -n "Apache2.4"            :: перечитать конфигурацию
httpd.exe -k stop -n "Apache2.4"
httpd.exe -k uninstall -n "Apache2.4"
sc.exe qc Apache2.4                            :: BINARY_PATH_NAME: "C:\Apache24\bin\httpd.exe" -k runservice
```

PowerShell: `Get-Service Apache2.4`, `Restart-Service Apache2.4`, события — `Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Apache Service'} -MaxEvents 20`.

- Если имя задано при установке (`-n`), его нужно указывать во всех командах `-k` [Apache-док]. Ключи `-f`/`-d`, переданные при установке, служба хранит в реестре: `HKLM\System\CurrentControlSet\Services\<имя>\Parameters\ConfigArgs` [Apache-код].
- Сообщения: успех — `The 'Apache2.4' service is successfully installed.`; без прав администратора — `AH00369: Failed to open the Windows service manager, perhaps you forgot to log in as Administrator?`; имя занято — `AH00370: Failed to create the 'Apache2.4' service` [Apache-код].
- **«Error 1067: The process terminated unexpectedly»** при запуске службы — общая ошибка: запустите `httpd.exe` в консоли (ключ `-w` оставляет окно открытым при ошибке), прочитайте сообщение, затем `logs\error.log` и журнал событий «Приложение» (источник `Apache Service` — туда пишутся ошибки запуска, пока `error.log` ещё не открыт) [Apache-док, Apache-код]. **Код 2186** — проверить учётную запись службы («Вход в систему»): Apache не может обратиться к сетевому ресурсу [Apache-док].
- Учётная запись: по умолчанию LocalSystem — широкие права локально и **никаких** в сети. Для сетевых ресурсов нужна отдельная доменная учётная запись с правом «Вход в качестве службы»; документация советует ещё «Работа в режиме операционной системы», но это очень сильная привилегия — не выдавайте её без необходимости ⚠ [Apache-док; оценка — практика]. Права: чтение и выполнение на весь каталог Apache, изменение — на `logs`; каждый каталог пути от корня диска должен быть доступен на чтение, просмотр и проход [Apache-док]. Для 1С — чтение каталога `bin` платформы, для файловой базы — изменение каталога базы [ИТС-адм разд. 8.4.3.5.1].

### 10.4. Порт занят, брандмауэр

```powershell
Get-NetTCPConnection -LocalPort 80,443 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
Get-Process -Id <PID>                       # PID 4 — System, то есть http.sys
netsh http show servicestate                # кто зарегистрировал адреса в http.sys (IIS и др.)
netsh interface ipv4 show excludedportrange protocol=tcp   # зарезервированные диапазоны (Hyper-V, WSL2, Docker)
New-NetFirewallRule -DisplayName "Apache HTTP/HTTPS" -Direction Inbound -Protocol TCP -LocalPort 80,443 -Action Allow -Program "C:\Apache24\bin\httpd.exe" -Profile Domain,Private
Test-NetConnection <сервер> -Port 443       # с клиента
```

[практика: команды Windows]. В журнале Apache: `(OS 10048)Only one usage of each socket address (protocol/network address/port) is normally permitted.  : AH00072: make_sock: could not bind to address [::]:80` — порт занят (частый случай — IIS или другая служба на http.sys); `(OS 10013)An attempt was made to access a socket in a way forbidden by its access permissions.  : AH00072: …` — порт в зарезервированном диапазоне или занят монопольно [формат `(OS N)` — Apache-код; тексты Windows — практика]. Документация отдельно предупреждает, что порт 80 могут занимать другие веб-серверы, межсетевые экраны и даже клиентские программы [Apache-док]. Если веб-сервер стоит отдельно от кластера 1С, ему нужен исходящий доступ к кластеру (TCP 1541 и 1560–1591; см. `../1c/05`, раздел 1.4).

### 10.5. `mpm_winnt`: потоки, перезапуски, AcceptEx

- Ёмкость — `ThreadsPerChild` (по умолчанию 64; документация по Windows рекомендует порядка 150 и больше под нагрузку), верхняя граница — `ThreadLimit` (по умолчанию 1920, жёсткий предел 15000). Исчерпание — `AH00326 Server ran out of threads …` [Apache-док, Apache-код].
- `MaxConnectionsPerChild` оставлять `0`: замена дочернего процесса появляется не мгновенно [Apache-док].
- Новый дочерний процесс **сам перечитывает конфигурацию**: если процесс перезапустился из-за сбоя или `MaxConnectionsPerChild`, а `httpd.conf` уже частично отредактирован и не разбирается, сервер остановится. Правьте конфигурацию только непосредственно перед перезапуском [Apache-док, `mpm_winnt`].
- При остановке и перезапуске у активных запросов есть `TimeOut` секунд, затем они обрываются [Apache-док].
- `Child: Encountered too many AcceptEx faults accepting client connections.` / `winnt_mpm: falling back to 'AcceptFilter none'.`, а также `AH02322: winnt_accept: failed to retrieve AcceptEx, try 'AcceptFilter none'` — мешают сторонние сетевые продукты (антивирус, межсетевой экран): `AcceptFilter http none` и `AcceptFilter https none` [Apache-док, Apache-код].
- Для 1С: ИТС рекомендует для файловой базы на Apache 2.2 под Windows `<IfModule mpm_winnt_module> ThreadStackSize 8388608 </IfModule>` и увеличение при исчерпании стека [ИТС-адм разд. 8.10.1.1]; для 2.4 — по аналогии ⚠. Требование «одна публикация файловой базы — один рабочий процесс» на Windows выполняется само: дочерний процесс один [Apache-док].

### 10.6. Сетевые ресурсы и UNC

- Подключённые буквы дисков службе недоступны — в `httpd.conf` только UNC-пути (`//fileserver/share/...`) и учётная запись с сетевыми правами (10.3) [Apache-док].
- С 2.4.60 (только Windows) обращение к пути, который разрешается в UNC, при обработке запроса **отклоняется**, если имя сервера не перечислено в `UNCList` (контекст `server config`; ставить до первых UNC-путей; повтор директивы сбрасывает список) [Apache-док]. После обновления старой сборки до 2.4.60+ содержимое с сетевых ресурсов перестаёт отдаваться, пока не добавлен `UNCList <сервер>`. Уточнено 20.10.2026 по `server/core.c` и `request.c` ветки 2.4.x: в журнале `AH10504: check_unc: UNC path //<сервер>/… not allowed by UNCList`, обход каталогов получает «нет доступа» — ответ 403 с `AH00035 … search permissions are missing …` (на Windows не проверялось).
- CVE-2025-59775 (исправлено в 2.4.66): утечка NTLM-хешей через UNC при `AllowEncodedSlashes On` и `MergeSlashes Off` — не меняйте эти умолчания и закройте исходящий SMB [Apache-док, `CHANGES_2.4`].

### 10.7. Особенности для 1С на Windows (кратко)

- Как платформа ищет Apache 2.4: параметр `HKLM\SYSTEM\CurrentControlSet\Services\Apache2.4\ImagePath` (по тексту ИТС в нём заменяется фрагмент `Apache2.exe` на `conf\httpd.conf`), затем `HKLM\Software\Apache Software Foundation\Apache\2.4` (`ServerRoot`), затем `C:\Program Files\Apache Software Foundation\Apache2.4\conf` [ИТС-адм разд. 8.10.1.2.3]. У ZIP-сборок в `C:\Apache24` путь службы — `"C:\Apache24\bin\httpd.exe" -k runservice` (фрагмента `Apache2.exe` нет), установщика с разделом реестра нет, каталог по умолчанию другой — **автоматическое обнаружение может не сработать** ⚠; указывайте `-confpath C:\Apache24\conf\httpd.conf` у `webinst` явно и проверяйте результат.
- После публикации — перезапуск службы (`httpd.exe -k restart -n "Apache2.4"`), как и на Linux [ИТС-адм разд. 8.3.1].
- Разные версии 1С — отдельные экземпляры Apache (службы с разными `-n` и своими `httpd.conf`), публикация вручную [ИТС-адм разд. 8.2].
- Аутентификация ОС через Apache на Windows не настраивается (`-osauth` — только IIS) — `../1c-windows/03-…`, раздел 13.

## Типичные ошибки (симптом → причина → решение)

Сводка самых частых случаев; подробности — в указанном разделе.

| № | Симптом | Причина | Решение | Раздел |
|---|---|---|---|---|
| 1 | после `systemctl restart` сайт лежит | сломанная конфигурация; `restart` её не проверяет | `sudo apache2ctl -t`, исправить, затем `restart`; впредь `configtest && restart` | 3.1, 3.7 |
| 2 | `Invalid command 'ProxyPass'` / `'SSLEngine'` / `'RequestHeader'` | модуль не включён | `a2enmod proxy proxy_http` / `ssl` / `headers` | 3.3 |
| 3 | `Address already in use: AH00072` | порт занят или пересекающиеся `Listen` (точный повтор — другая ошибка, её ловит `configtest`) | `ss -tlnp 'sport = :80'`; один `Listen` | 3.4 |
| 4 | `Cannot load …/wsap24.so into server` | путь к модулю старой платформы, нет зависимостей | исправить путь, `ldd`, перезапуск | 3.5 |
| 5 | 403 + `AH01630` | `Require`, каталог вне `/var/www` | `authz_core:debug`, явное разрешение каталога | 4.1 |
| 6 | 404, в журнале `/var/www/html/…` | запрос попал в хост по умолчанию | `apache2ctl -S`, `ServerAlias` | 4.2 |
| 7 | 400 у части доменных пользователей | большой билет Kerberos | `LimitRequestFieldSize` глобально или в первом хосте адреса:порта | 4.4, 7.2 |
| 8 | 413 при загрузке файла | `LimitRequestBody` на одном из звеньев | согласовать лимиты | 4.4, 5.5 |
| 9 | 503 «Proxy Error» 60 секунд после перезапуска бэкенда | воркер в состоянии ошибки (`retry=60`) | `retry=0`/`retry=5` | 5.2 |
| 10 | 502 «Error reading from remote server» на долгих операциях | таймаут ответа бэкенда (`AH01102`, 70007) | разобраться с запросом; `timeout=` для пути | 5.2, 5.5 |
| 11 | 502 на первом запросе после паузы | гонка keep-alive | `proxy-initial-not-pooled`, `ttl` | 5.3 |
| 12 | после входа — переход на `http://` или внутренний адрес | нет `ProxyPreserveHost`/`X-Forwarded-Proto` (для 1С — `X-Forwarded-*`) | раздел 5.4 | 5.4 |
| 13 | HTTPS не стартует: `AH02565` | ключ не от сертификата | сверить хеши открытых ключей | 6.1 |
| 14 | у `curl` и тонкого клиента 1С ошибка сертификата, у браузера нет | нет промежуточного сертификата (`Verify return code: 21`) | `fullchain.pem` в `SSLCertificateFile` | 6.3 |
| 15 | `ERR_SSL_PROTOCOL_ERROR`, `curl: (35) … wrong version number` | на 443 хост без `SSLEngine on` (`AH01916`) | `SSLEngine on` во всех `*:443` | 6.2 |
| 16 | 421 Misdirected Request после обновления | проверка SNI ↔ `Host` (`AH02032`) | одинаковые TLS-настройки хостов или `SSLVHostSNIPolicy authonly` | 6.4 |
| 17 | 403 + `AH10508` после обновления | `mod_rewrite`, `UnsafeAllow3F` | переписать правило | 4.1, 9.3 |
| 18 | браузер просит пароль на сайте с Kerberos | нет билета: зона, SPN, IP вместо имени | раздел 7 | 7.2 |
| 19 | `GSS ERROR … keytab is likely out of date` | старый keytab | перевыпустить keytab | 7.2 |
| 20 | ночью Apache перезапустился | `logrotate` (`reload`), `needrestart`, обновление пакета | хронология `AH00489`/`AH00493` в `error.log` | 1.2, 9.1 |
| 21 | Windows: «Error 1067» | ошибка конфигурации, порт занят (`(OS 10048)`/`(OS 10013)`), нет VC++ Redistributable | `httpd.exe` в консоли, `logs\error.log`, журнал событий (`Apache Service`) | 10.3, 10.4 |
| 22 | Windows: `webinst` не находит Apache в `C:\Apache24` | обнаружение по реестру не срабатывает для ZIP-сборки | `-confpath` явно | 10.7 |
| 23 | Windows: после правки `httpd.conf` сервер сам остановился | новый дочерний процесс прочитал недоправленную конфигурацию | править только перед перезапуском | 10.5 |
| 24 | Windows: файлы с сетевой папки перестали отдаваться после обновления сборки | `UNCList` (2.4.60+), учётная запись без сетевых прав, буква диска вместо UNC | `UNCList <сервер>`, UNC-пути, отдельная учётная запись службы | 10.3, 10.6 |
| 25 | Windows: «теряются» соединения, в журнале `AcceptEx faults` | антивирус/межсетевой экран | `AcceptFilter http none`, `AcceptFilter https none` | 10.5 |

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Проверить конфигурацию | `sudo apache2ctl configtest` |
| Виртуальные хосты, пользователь, PidFile | `sudo apache2ctl -S` |
| Модули и MPM | `sudo apache2ctl -M`; `apache2ctl -V \| grep -i mpm` |
| Дерево подключённых файлов | `sudo apache2ctl -t -D DUMP_INCLUDES` |
| Файлы сертификатов | `sudo apache2ctl -t -D DUMP_CERTS` |
| Причина отказа старта | `systemctl status apache2 -l --no-pager`; `sudo journalctl -u apache2 -b --no-pager \| tail -n 40` |
| Безопасный перезапуск | `sudo apache2ctl configtest && sudo systemctl restart apache2` |
| Кто держит порт | `sudo ss -tlnp 'sport = :443'` |
| Частые коды в журнале | `sudo grep -o 'AH[0-9]\{5\}' /var/log/apache2/error.log \| sort \| uniq -c \| sort -rn \| head` |
| Временная детализация журнала | файл `conf-available/zz-debug.conf` с `LogLevel warn ssl:info authz_core:debug proxy:debug`, `a2enconf`, `reload` |
| Какое правило дало 403 | `LogLevel warn authz_core:debug` → `authorization result of …` |
| Права по цепочке каталогов | `namei -l <путь>`; `sudo -u www-data test -r <файл> && echo OK` |
| Запрос в нужный хост без DNS | `curl -sv --resolve имя:443:127.0.0.1 https://имя/ -o /dev/null` |
| Бэкенд напрямую | `curl -sv http://127.0.0.1:3000/ -o /dev/null` |
| Ошибки прокси | `sudo grep -E 'AH0(0957\|0959\|0940\|1102\|0898\|1144)' /var/log/apache2/error.log \| tail` |
| Цепочка и протокол TLS | `openssl s_client -connect имя:443 -servername имя -showcerts </dev/null` |
| Совпадают ли сертификат и ключ | `openssl x509 -in c.crt -noout -pubkey \| sha256sum` и `openssl pkey -in k.key -pubout \| sha256sum` |
| Срок сертификата на сайте | `echo \| openssl s_client -connect имя:443 -servername имя 2>/dev/null \| openssl x509 -noout -dates` |
| Kerberos с клиента Linux | `kinit user@REALM && curl -sv --negotiate -u : https://имя/demo/ -o /dev/null` |
| keytab | `sudo klist -k -t -e /etc/apache2/http.keytab`; `sudo -u www-data klist -k /etc/apache2/http.keytab` |
| Что изменилось в пакете | `apt changelog apache2 \| head -n 80` |
| Остатки вопросов dpkg | `sudo find /etc/apache2 -name '*.dpkg-*'` |
| Windows: проверка и перезапуск | `httpd.exe -n "Apache2.4" -t`; `httpd.exe -k restart -n "Apache2.4"` |
| Windows: кто держит порт | `Get-NetTCPConnection -LocalPort 80,443 -State Listen`; `netsh http show servicestate` |
| Windows: события Apache | `Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Apache Service'} -MaxEvents 20` |

## Источники

Документация и код Apache (прочитано 20.10.2026):

- https://httpd.apache.org/ — текущий выпуск 2.4.69 (01.10.2026); https://downloads.apache.org/httpd/CHANGES_2.4; https://httpd.apache.org/security/vulnerabilities_24.html (даты выпусков 2.4.54–2.4.69).
- Исходники документации ветки 2.4.x (`https://raw.githubusercontent.com/apache/httpd/2.4.x/docs/manual/…`): `programs/httpd`, `programs/apachectl`, `logs`, `bind`, `upgrading`, `platform/windows`, `mod/core`, `mod/mpm_common`, `mod/mpm_winnt`, `mod/mod_proxy`, `mod/mod_proxy_http`, `mod/mod_ssl`, `mod/mod_authz_core`, `mod/mod_remoteip`, `mod/mod_reqtimeout`, `mod/mod_dumpio`, `mod/mod_log_debug`, `mod/mod_log_config`, `mod/mod_info`, `mod/mod_rewrite`; `docs/conf/httpd.conf.in`, `docs/conf/extra/httpd-ssl.conf.in`.
- Исходный код ветки 2.4.x (`https://raw.githubusercontent.com/apache/httpd/2.4.x/…`): `server/` (`main.c`, `config.c`, `core.c`, `listen.c`, `log.c`, `request.c`, `protocol.c`, `vhost.c`, `mpm_unix.c`, MPM `event`, `worker`, `prefork`, `winnt`), `modules/core/mod_so.c`, `modules/aaa/`, `modules/proxy/` (`mod_proxy.c`, `mod_proxy_http.c`, `proxy_util.c`), `modules/ssl/`, `modules/http/http_filters.c`, `modules/filters/mod_reqtimeout.c`, `modules/mappers/mod_rewrite.c`, `modules/http2/mod_http2.c`, `include/ap_mmn.h`; метки `2.4.52` и `2.4.58` — текст `AH02032`, `DUMP_CERTS`, имена схем прокси. APR 1.7: `misc/unix/errorcodes.c`, `include/apr_errno.h`.

Ubuntu и Debian:

- https://packages.ubuntu.com/jammy-updates/apache2, `/noble-updates/apache2`, `/resolute/apache2`; списки файлов `noble/amd64/apache2/filelist` и `apache2-bin/filelist`.
- https://changelogs.ubuntu.com/changelogs/pool/main/a/apache2/apache2_2.4.58-1ubuntu8.16/changelog, `…_2.4.52-1ubuntu4.24/changelog`, `…_2.4.66-2ubuntu2.6/changelog`.
- https://documentation.ubuntu.com/server/how-to/web-services/install-apache2/.
- salsa.debian.org, проект `apache-team/apache2`, метка `debian/2.4.58-1`: `debian/apache2.README.Debian`, `debian/apache2.NEWS`, `debian/apache2ctl`, `debian/config-dir/envvars`, `debian/config-dir/apache2.conf.in`, `debian/config-dir/ports.conf`, `debian/config-dir/conf-available/security.conf`, `debian/a2enmod`, `debian/apache2.logrotate` (файлы `apache2.service` и `a2query` при написании прочитать не удалось — сервер отвечал проверкой «I Challenge Thee»).
- Независимая сверка 20.10.2026 (API salsa.debian.org, повтор после проверки): метка `debian/2.4.58-1` — `debian/apache2.service`, `debian/apache2.README.Debian`, `debian/apache2.NEWS`, `debian/apache2ctl`, `debian/apache2.links`, `debian/apache2.postinst`, `debian/ask-for-passphrase`, `debian/config-dir/mods-available/ssl.conf`, `status.conf`, `info.conf`, `.load`-файлы (`proxy_http`, `proxy_balancer`, `ssl`, `authnz_ldap`, `mpm_event`, `dump_io`), `conf-available/other-vhosts-access-log.conf`, `apache2.conf.in`; метка `debian/2.4.66-2` — `debian/apache2.service`, `debian/apache2ctl`; packages.ubuntu.com — `noble/libapache2-mod-auth-gssapi` (1.6.4), `jammy`/`noble` `libapache2-mod-auth-kerb`; журналы изменений jammy/noble/resolute (записи 4.1–4.24, 8.2–8.16, «Remaining changes»).
- Код Apache, дополнительно прочитанный при сверке: `server/util_expr_eval.c`, `server/util.c`, `modules/ssl/ssl_engine_pphrase.c`, `modules/ssl/ssl_private.h`, `modules/generators/mod_autoindex.c`, `modules/loggers/mod_log_config.c`, `server/mpm/winnt/{child,service,nt_eventlog}.c`; метки `2.4.52`/`2.4.58` — `mod_proxy_http.c`, `ssl_engine_kernel.c`, `ssl_engine_config.c`.

1С: `../its-docs/adm-gl08-veb-servery-p1.md`, `…-p2.md` и полный текст главы 8 «Руководства администратора» 8.3.27 (разд. 8.2, 8.3.1, 8.4.3.5.1, 8.10.1.1, 8.10.1.2.3, 8.10.2.4, 8.10.3); методичка ИТС 5978 «Настройка веб-сервера Apache под Windows» (31.07.2020); статьи базы `../1c/05-veb-publikaciya-apache-nginx.md`, `../1c-windows/03-veb-publikaciya-iis.md`, `../linux/04-pakety-apt.md`.

Сторонние:

- mod_auth_gssapi: https://github.com/gssapi/mod_auth_gssapi — `README`, `src/mod_auth_gssapi.c` (ветка master и метки `v1.6.3`–`v1.6.5`).
- MIT krb5 (ветка master на GitHub): `src/lib/gssapi/mechglue/g_dsp_status.c`, `src/lib/gssapi/generic/disp_major_status.c`, `src/lib/krb5/krb/rd_req_dec.c`, `src/lib/krb5/error_tables/krb5_err.et`.
- OpenSSL 3.0: `crypto/err/openssl.txt`, `crypto/x509/x509_txt.c`, `include/openssl/x509_vfy.h.in`.
- curl: `docs/libcurl/libcurl-errors.md`.
- certbot: `certbot/docs/using.rst` («Where are my certificates?»); суффикс `-0001` у повторного имени — `unique_lineage_name()` в `certbot/util.py` (документация пишет `-001`, код — `%04d`).
- PHP 8.3: `sapi/apache2handler/sapi_apache2.c`.
- Apache Lounge: https://www.apachelounge.com/download/ (на 20.10.2026).

## Что не удалось подтвердить

- Тексты сообщений в **пакетах Ubuntu** (2.4.52/2.4.58 с заплатками) сверялись с апстримом, а не с исходниками пакета; в частности, вид `AH02032` с `for policy '…'` после заплатки 09.12.2025 и умолчание `SSLVHostSNIPolicy` в ней (по-видимому, `secure`, как в апстриме) — ⚠.
- Юнит `apache2.service` и `apache2ctl` сверены 20.10.2026 с метками Debian `debian/2.4.58-1` и `debian/2.4.66-2` (основы пакетов 24.04 и 26.04), а не с исходниками пакетов Ubuntu; для 22.04 (2.4.52 с правкой Ubuntu `apache2ctl` «use systemd for graceful») — только по журналу изменений.
- Тексты glibc/Windows (`wrong ELF class`, `(99)…`, `(OS 10048)`, `(OS 10013)`), браузеров и nginx — по практике; код ответа при `DNS lookup failure` (500 по `proxy_util.c`) в отдельных путях может отличаться.
- Отказ OpenSSL по умолчанию для коротких ключей и SHA-1 в конкретном выпуске Ubuntu; поддержка клиентами аутентификации после рукопожатия TLS 1.3.
- Kerberos: текст уточнения при NTLM-токене, `KRB5_TRACE` для службы, сообщения `mod_auth_kerb`, значение `LimitRequestFieldSize 65536`; таймауты простоя Puma, gunicorn, Docker-прокси (для `ttl`).
- Поведение ограничения файловых функций `ap_expr` в `.htaccess` сверено с кодом 2.4.69, на сервере не проверялось; промежуточное поведение пакетов Ubuntu с 05.05 по 06.07.2026 (запрет и проверок `-f`, `-d`…) — по журналам изменений.
- Windows: необходимость Visual C++ Redistributable проявляется ошибкой отсутствия библиотеки (практика); переменная `SRVROOT` и файл `httpd-ahssl.conf` — по методичке ИТС 5978 (2020), в текущей сборке Apache Lounge не проверялись; автоматическое обнаружение Apache в `C:\Apache24` утилитой `webinst`; ответ 403 при отказе по `UNCList` — по коду, на Windows не проверялся; применимость `ThreadStackSize 8388608` (ИТС пишет про 2.2) к Apache 2.4.
- На сервере ничего не проверялось: все команды и ожидаемые ответы нужно сверить при первом применении на `srv-1c-app`, `srv-itsm`, `srv-obs`.
