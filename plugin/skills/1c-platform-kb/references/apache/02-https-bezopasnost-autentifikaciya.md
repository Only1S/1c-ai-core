# Apache: HTTPS и TLS, сертификаты, безопасность, аутентификация (Basic, LDAP/AD, Kerberos)

> **Официальные тексты по теме** (конспекты ИТС 1С 8.3.27): `../its-docs/adm-gl08-veb-servery-p1.md` и `../its-docs/adm-gl08-veb-servery-p2.md` — глава 8 «Настройка веб-серверов» (8.2 — HTTPS «настоятельно рекомендуется», MPM worker; 8.10.1.3 — заголовок `X-Frame-Options`; 8.10.3 — обратный прокси и заголовки `X-Forwarded-*`); `../its-docs/adm-gl02-ustanovka-p2.md` — разд. 2.8.1.2 «Аутентификация ОС при использовании веб-сервера Apache» (официальный рецепт на `mod_auth_kerb`); `../its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md` — методички 5979/5980 (HTTPS на Apache и nginx под Linux, 2020); `../its-metod/kerberos-openid-autentifikaciya.md`. Публикация 1С (`webinst`, `default.vrd`, модуль `wsap24`) здесь **не** описывается — она в `../1c/05-veb-publikaciya-apache-nginx.md`.

> Статус: проверено независимой сверкой 20.10.2026: директивы, умолчания, контексты и «с версии» — с исходниками документации Apache 2.4 (`docs/manual/*.xml`, ветка 2.4.x), спорное — с исходным кодом httpd 2.4.52/2.4.58/2.4.64–2.4.66/2.4.x и OpenSSL 3.0.13; версии и даты — с httpd.apache.org, `vulnerabilities_24.html`, `CHANGES_2.4`, packages.ubuntu.com, журналами пакета Ubuntu (`4.25`/`8.17`/`2ubuntu2.6`); файлы и юниты Ubuntu — с пакетом Debian `apache2` на salsa.debian.org (метки `debian/2.4.52-1`, `2.4.58-1`, `2.4.66-2`); `mod_auth_gssapi` — с README и кодом; TLS — с TLSRef 6.0; certbot, Let's Encrypt, Microsoft, Chromium/Edge/Mozilla, MIT krb5, OpenLDAP, nginx — с их официальными страницами; 1С — с полными текстами ИТС 8.3.27. Исправлено 13 ошибок и неточностей, закрыто 33 пометки (осталось 18); на сервере не проверялось.

> Область: HTTPS/TLS в Apache 2.4 на Ubuntu 22.04/24.04/26.04 — `mod_ssl`, сертификаты (корпоративный УЦ, самоподписанные, Let's Encrypt), протоколы и шифры, HSTS, OCSP stapling, HTTP/2, заголовки безопасности, `Require`, аутентификация Basic, LDAP/AD, Kerberos, медленные атаки и размеры запроса, безопасность обратного прокси, обновления; кратко — Windows. Применение: публикация 1С на `srv-1c-app`, сервисы (Redmine, NetBox, GlitchTip) на `srv-itsm`/`srv-obs`. | Версии: Apache 2.4.69 (2026-10-01); `apache2` 2.4.52 / 2.4.58 / 2.4.66 с заплатками Ubuntu. | Актуальность: 2026-10-20

Пометки: **[Apache-док]** — документация Apache 2.4, `CHANGES_2.4`, страница уязвимостей; **[Ubuntu]** — packages.ubuntu.com, журналы пакетов, документация Ubuntu Server; **[Debian]** — файлы пакета `apache2` (README.Debian, `debian/config-dir`, сценарии); **[ИТС-адм разд. N]** — «Руководство администратора» 1С 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС; **[сторонний]** — документация стороннего продукта (TLSRef/Mozilla, certbot, Let's Encrypt, `mod_auth_gssapi`, Microsoft); **[практика]** — опыт сообщества и выводы автора; **⚠** — не подтверждено первоисточником.

Смежные статьи (их тему здесь не расписываем): `apache/01-ustanovka-i-ustrojstvo.md` (установка, раскладка `/etc/apache2`, `a2en*`, MPM, хосты, слияние секций); `apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md` (таймауты долгих запросов, обратный прокси, журналы, `mod_status`); `apache/04-tipovye-problemy-i-apache-na-windows.md` (неполадки, Windows); `1c/05-veb-publikaciya-apache-nginx.md` (публикация, HTTPS — разд. 8, свой УЦ — 8.3, certbot — 8.4, аутентификация — 11); `1c/08-konfiguracionnye-fajly-kerberos-bezopasnost.md` (Kerberos сервера 1С — 5, SSO веб-клиента — 5.7, HTTPS клиента — 7.2); `linux/08-set-ssh-firewall.md` (`ufw allow 'Apache Full'`); `observability/03-loki-i-grafana.md` (журналы в Loki).

Обозначения: веб-сервер 1С — `srv-1c-app.example.local` (публичное имя `1c.example.com`); сервисы — `srv-itsm.example.local`, `srv-obs.example.local`; домен — `EXAMPLE.LOCAL` (NetBIOS `EXAMPLE`); учётки — `svc-http-1c` (Kerberos), `svc-apache-ldap` (LDAP). Команды — через `sudo` (от `root`), проверки доступа — от `www-data` (`sudo -u www-data …`).

## Кратко — главные факты

1. **Текущий выпуск — 2.4.69 (01.10.2026)**, ~20 CVE. В Ubuntu номер не растёт (22.04 — 2.4.52, 24.04 — 2.4.58, 26.04 — 2.4.66), исправления переносятся заплатками — сверяйте журнал пакета (`apt changelog apache2 | grep CVE-2026`) [Apache-док; Ubuntu].
2. **HTTPS в Ubuntu**: `sudo a2enmod ssl` (подтянет `mime`, `socache_shmcb`), свой хост `*:443` с `SSLEngine on`, `SSLCertificateFile`, `SSLCertificateKeyFile`; `Listen 443` уже в `ports.conf` [Debian].
3. **Цепочка — в файле сертификата** (свой → промежуточные), с 2.4.8; `SSLCertificateChainFile` устарел. Неполная цепочка ломает `curl`, тонкий клиент 1С и Java при «нормальном» браузере [Apache-док; практика].
4. **Ключ** читает родительский процесс от `root`: владелец `root`, права `600`, `www-data` доступ не нужен [Debian; Apache-док].
5. **Штатный `ssl.conf` Ubuntu**: 22.04 — `SSLProtocol all -SSLv3`; 24.04 — то же + `SSLSessionTickets off`; 26.04 — `all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1`; шифры `HIGH:!aNULL`. OpenSSL Ubuntu 22.04+ (`SECLEVEL=2`) и так запрещает TLS < 1.2 [Debian; Ubuntu].
6. **Профиль — «intermediate» TLSRef 6.0** (бывший Mozilla Server Side TLS; генератор переехал на `configurator.tlsref.org`): TLS 1.2/1.3, шесть наборов ECDHE (AES-GCM, ChaCha20), `SSLHonorCipherOrder off`, `SSLSessionTickets off`, HSTS 2 года. TLS 1.3 — Apache 2.4.43+ и OpenSSL 1.1.1+, наборы — `SSLCipherSuite TLSv1.3 …` [сторонний; Apache-док].
7. **Let's Encrypt**: `sudo apt install certbot python3-certbot-apache`, `sudo certbot --apache -d <имя>`; продление — `certbot.timer` (snap — `snap.certbot.renew.timer`); детали для 1С — `1c/05`, разд. 8.4 [сторонний; Ubuntu].
8. **OCSP stapling с LE бессмыслен**: адреса OCSP убраны из сертификатов 07.05.2025, сервис выключен 06.08.2025. `SSLUseStapling` — только для УЦ с OCSP (AD CS с Online Responder) [сторонний].
9. **HSTS** (`Header always set Strict-Transport-Security "max-age=63072000"`) — только в HTTPS-хосте и после отладки: у браузеров не отменить до истечения срока [сторонний; практика].
10. **HTTP/2**: `a2enmod http2` в Debian включает `Protocols h2 h2c http/1.1` глобально; с `prefork` — сильные ограничения (не «несовместимость»), с `worker` для 1С работает, но выгода мала, а CVE в `mod_http2` регулярны [Apache-док; Debian; практика].
11. **Версия сервера**: Ubuntu ставит `ServerTokens OS`, `ServerSignature On` — замените на `Prod`/`Off`; `TraceEnable Off` уже стоит. Документация: это не защита, а меньше шума от сканеров [Debian; Apache-док].
12. **Ubuntu из коробки**: листинг каталогов в `/var/www` (`Options Indexes`), включены `autoindex`, `status` (`/server-status`, `Require local`), `access_compat`; `000-default` отвечает на любое имя — отключить или сделать «заглушкой» [Debian].
13. **Доступ**: `Require ip|host|forward-dns|local|all|env|method|expr`; несколько `Require` подряд — неявный `<RequireAny>`, «и» — `<RequireAll>`. За прокси адрес клиента — адрес прокси (`mod_remoteip`); `Require local` за nginx на том же хосте пропускает всех [Apache-док; практика].
14. **Basic** — только по HTTPS, пароли `htpasswd -B`; SHA-2 (`-2`, `-5`) — лишь с 2.4.59 (только 26.04) [Apache-док].
15. **LDAP/AD**: `a2enmod authnz_ldap`; `AuthLDAPURL "ldaps://dc1 dc2/DC=…?sAMAccountName?sub?(objectClass=user)"`, `LDAPTrustedGlobalCert CA_BASE64 …`; для вложенных групп AD — `AuthLDAPSubGroupClass group`; кеш LDAP — до 600 с [Apache-док; практика].
16. **Kerberos** — `mod_auth_gssapi` (universe; 1.6.3 в 22.04, 1.6.4 в 24.04/26.04), `mod_auth_kerb` — только 22.04. Нужны SPN `HTTP/<FQDN>`, keytab с AES (чтение для `www-data`), синхронное время, вход по FQDN [сторонний; Ubuntu].
17. **Заголовок SPNEGO — до 12 392 байт** при `LimitRequestFieldSize 8190` → 400 у «многогрупповых» пользователей. Поднимать в контексте сервера: в не-первом хосте для IP:порта директива игнорируется [Apache-док].
18. **Аутентификация ОС для 1С**: официально — только `mod_auth_kerb` с `KrbSaveCredentials on` и делегированием [ИТС-адм разд. 2.8.1.2]; `mod_auth_gssapi` с `GssapiDelegCcacheDir` — практика, не проверено (`1c/05`, 11.3).
19. **Лимиты**: `LimitRequestBody` — 1 ГиБ с 2.4.54 (раньше 0), иначе 413 — для загрузок в 1С задавайте явно; `LimitRequestLine 8190` — длинные OData-URL получают 414 [Apache-док; практика].
20. **`mod_reqtimeout`** включён по умолчанию (`header=20-40,minrate=500`, `body=10,minrate=500`) — защита от slowloris; время выполнения запросов 1С не ограничивает [Debian; Apache-док].
21. **`ProxyRequests Off`** (умолчание) — для обратного прокси `On` не нужен. `X-Forwarded-Proto` Apache сам не ставит — `RequestHeader set X-Forwarded-Proto "https"` (ИТС требует его для 1С за прокси) [Apache-док; ИТС-адм разд. 8.10.3].
22. **Обновления 2025 г.**: `SSLEngine optional` (TLS Upgrade) удалён — теперь он работает как `Off` и пишет в журнал уведомление `AH10510 'SSLEngine optional' is no longer supported`, запуск не прерывается; несовпадение SNI и `Host` даёт **421**; режим — `SSLVHostSNIPolicy` (2.4.66; в Ubuntu 22.04/24.04 с декабря 2025) [Apache-док; код `modules/ssl/ssl_engine_config.c` 2.4.64–2.4.66; Ubuntu].

## 1. Версии и что от них зависит

### 1.1. Выпуски Apache и пакеты Ubuntu

| Что | Значение на 20.10.2026 | Источник |
|---|---|---|
| Текущий выпуск ветки 2.4 | **2.4.69** (01.10.2026) | [Apache-док] httpd.apache.org |
| Предыдущие | 2.4.68 (08.06.2026), 2.4.67 (04.05.2026), 2.4.66 (04.12.2025), 2.4.65 (23.07.2025), 2.4.64 (10.07.2025) | [Apache-док] страница уязвимостей 2.4 |
| Ветка 2.2 | снята с поддержки, последний выпуск 2.2.34 (июль 2017) | [Apache-док] |
| Ubuntu 22.04 (jammy) | `apache2` **2.4.52-1ubuntu4.25** (jammy-security) | [Ubuntu] |
| Ubuntu 24.04 (noble) | `apache2` **2.4.58-1ubuntu8.17** (noble-security) | [Ubuntu] |
| Ubuntu 26.04 (resolute) | `apache2` **2.4.66-2ubuntu2.6** (resolute-security) | [Ubuntu] |
| OpenSSL | 3.0.2 (22.04), 3.0.13 (24.04), 3.5.5 (26.04) | [Ubuntu] |
| certbot (apt) | 1.21.0 (22.04), 2.9.0 (24.04), 4.0.0 (26.04); актуальный выпуск certbot — 5.8.0 (01.09.2026) | [Ubuntu; сторонний] |
| `libapache2-mod-auth-gssapi` | 1.6.3 (22.04), 1.6.4 (24.04, 26.04) — раздел **universe** | [Ubuntu] |

Пакеты из universe (certbot, `mod_auth_gssapi`) Ubuntu официально не поддерживает: по документации Ubuntu Server они не получают исправлений безопасности, кроме как через Ubuntu Pro (ESM Apps; для личного использования подписка бесплатна до 5 машин) [Ubuntu, «Package management», раздел «Extra repositories»; уточнено 20.10.2026].

Как узнать, что стоит на сервере:

```bash
apache2 -v                              # версия сборки: Server version: Apache/2.4.58 (Ubuntu)
apt-cache policy apache2                # установленная и доступная версия пакета
apache2ctl -M | sort                    # загруженные модули (ssl_module, http2_module, …)
apache2ctl -S                           # виртуальные хосты: кто «первый» на *:443, какой файл
openssl version                         # версия OpenSSL
a2query -m ssl                          # включён ли модуль (a2query описан в README.Debian)
```

### 1.2. Возможности, зависящие от версии

| Возможность | С какой версии | Что в Ubuntu | Источник |
|---|---|---|---|
| TLS 1.3 | поддержка в `mod_ssl` с 2.4.36; для рабочего TLS 1.3-сервера проект требует 2.4.43+ и OpenSSL 1.1.1 | есть во всех трёх выпусках | [Apache-док] |
| Промежуточные сертификаты в `SSLCertificateFile` | 2.4.8 | есть | [Apache-док] |
| `SSLProtocol` у каждого name-based хоста (по SNI) | 2.4.42 + OpenSSL 1.1.1 | есть | [Apache-док] |
| Сертификат/ключ из PKCS#11 (`certid`/`keyid`) | 2.4.42 | есть | [Apache-док] |
| Этап `handshake=` у `RequestReadTimeout` | 2.4.39 | есть | [Apache-док] |
| `LimitRequestBody` по умолчанию 1 ГиБ (было 0) | 2.4.54 | 24.04 и 26.04 — да; 22.04 (2.4.52) — ⚠ см. 13.3 | [Apache-док] |
| `htpasswd -2/-5` (SHA-256/512 crypt) | 2.4.59 | только 26.04 | [Apache-док] |
| Удалён `SSLEngine optional` (TLS Upgrade, CVE-2025-49812) | 2.4.64 | перенесено: 22.04 — `2.4.52-1ubuntu4.15`, 24.04 — `2.4.58-1ubuntu8.7` (14.07.2025) | [Apache-док; Ubuntu] |
| Строгая проверка SNI ↔ `Host` (CVE-2025-23048) | 2.4.64 | те же обновления, что выше | [Apache-док; Ubuntu] |
| `SSLVHostSNIPolicy` | 2.4.66 | перенесено как исправление регрессии «Misdirected Request» (LP #2117112): 22.04 — `4.18`, 24.04 — `8.10` (09.12.2025); в 26.04 — из коробки | [Apache-док; Ubuntu] |
| `ProtocolsHonorOrder`, `Protocols` (HTTP/2) | 2.4.17 | есть | [Apache-док] |
| `H2StreamTimeout` | 2.4.55 | 24.04, 26.04 | [Apache-док] |

### 1.3. Чем отличается `ssl.conf` по выпускам Ubuntu

Файл `/etc/apache2/mods-available/ssl.conf` — общие (глобальные) настройки `mod_ssl`, действуют на все TLS-хосты [Debian]:

| Директива | 22.04 (`debian/2.4.52-1`) | 24.04 (`debian/2.4.58-1`) | 26.04 (`debian/2.4.66-2`) |
|---|---|---|---|
| `SSLCipherSuite` | `HIGH:!aNULL` | `HIGH:!aNULL` | `HIGH:!aNULL` |
| `SSLProtocol` | `all -SSLv3` | `all -SSLv3` | `all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1` |
| `SSLSessionTickets` | не задан (умолчание Apache — `on`) | `off` | `off` |
| `SSLSessionCache` | `shmcb:${APACHE_RUN_DIR}/ssl_scache(512000)` | то же | то же |
| `SSLSessionCacheTimeout` | `300` | `300` | `300` |
| `SSLPassPhraseDialog` | `exec:/usr/share/apache2/ask-for-passphrase` | то же | то же |
| `SSLHonorCipherOrder` | закомментирован (умолчание `off`) | то же | то же |
| Обёртка `<IfModule mod_ssl.c>` | есть | нет | нет |

Строку «Disable by default TLS 1.0 and TLS 1.1» в Debian внесли 17.07.2025 — поэтому она есть только в 26.04 [Debian]. На практике в 22.04/24.04 TLS 1.0/1.1 всё равно не согласуются: в Ubuntu начиная с 22.04 OpenSSL собран с `SECLEVEL=2`, а заплатка Ubuntu отключает на этом уровне версии ниже TLS 1.2 [Ubuntu, «OpenSSL» в документации Ubuntu Server]. Включить их обратно можно только понижением уровня безопасности — не делайте этого.

## 2. `mod_ssl` в Ubuntu: файлы, включение, проверка

### 2.1. Что поставляет пакет

| Файл | Назначение | Источник |
|---|---|---|
| `/usr/lib/apache2/modules/mod_ssl.so` | сам модуль (пакет `apache2-bin`) | [Ubuntu filelist] |
| `/etc/apache2/mods-available/ssl.load` | `LoadModule ssl_module …`; строка `# Depends: mime socache_shmcb` — `a2enmod` включит зависимости | [Debian] |
| `/etc/apache2/mods-available/ssl.conf` | глобальные настройки (см. 1.3) | [Debian] |
| `/etc/apache2/sites-available/default-ssl.conf` | пример хоста `*:443` со «змеиным маслом» (snakeoil) | [Debian] |
| `/etc/apache2/ports.conf` | `Listen 80`; `Listen 443` — внутри `<IfModule ssl_module>` и `<IfModule mod_gnutls.c>` | [Debian] |
| `/etc/apache2/conf-available/security.conf` | `ServerTokens`, `ServerSignature`, `TraceEnable`, закомментированные примеры заголовков | [Debian] |

В `default-ssl.conf` (24.04): `SSLEngine on`, `SSLCertificateFile /etc/ssl/certs/ssl-cert-snakeoil.pem`, `SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key`, закомментированы `SSLCertificateChainFile`, `SSLCACertificatePath`, `SSLVerifyClient`, `SSLOptions`; блок `SSLOptions +StdEnvVars` для `.cgi|.shtml|.phtml|.php` и `/usr/lib/cgi-bin` [Debian]. Обходного пути для MSIE (`BrowserMatch "MSIE [2-6]"`) в файле 24.04 уже нет, хотя README.Debian всё ещё пишет, что он там есть — README отстал от файла [Debian].

Сертификат snakeoil создаёт пакет `ssl-cert` (`make-ssl-cert`); перевыпуск после смены имени хоста: `sudo make-ssl-cert generate-default-snakeoil --force-overwrite` [Debian README]. Он годится только для проверки, что TLS вообще поднимается.

> Документация Ubuntu Server («How to use Apache2 modules») пишет, что `mod_ssl` «входит в пакет apache2-common». Такого пакета давно нет — модуль в `apache2-bin` [Ubuntu filelist]. Это неточность документации, на работу не влияет.

### 2.2. Порядок включения

```bash
# 1) модуль (зависимости mime и socache_shmcb включатся сами)
sudo a2enmod ssl
# 2) свой хост — НЕ правьте default-ssl.conf, сделайте копию под имя сервиса
sudo cp /etc/apache2/sites-available/default-ssl.conf /etc/apache2/sites-available/1c-ssl.conf
sudoedit /etc/apache2/sites-available/1c-ssl.conf     # ServerName, пути к сертификату и ключу
sudo a2ensite 1c-ssl
# 3) проверка синтаксиса и применение
sudo apache2ctl configtest                             # должно быть: Syntax OK
sudo systemctl reload apache2                          # reload = apachectl graceful (юнит Debian)
# 4) проверки
sudo ss -tlnp | grep -E ':(80|443)\b'                  # слушаются оба порта
sudo apache2ctl -S 2>&1 | grep -A3 ':443'              # какой хост «первый» на *:443
curl -sI https://srv-1c-app.example.local/          # заголовки ответа по HTTPS
openssl s_client -connect srv-1c-app.example.local:443 \
        -servername srv-1c-app.example.local </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

`systemctl reload apache2` в юните Debian — это `apachectl graceful` (`ExecReload=/usr/sbin/apachectl graceful`): рабочие процессы дорабатывают текущие запросы, новые получают новую конфигурацию и новые сертификаты [Debian]. Документация `mod_ssl` пишет, что файлы сертификата и ключа «перечитываются только при перезапуске сервера» — мягкий перезапуск (`graceful`) это тоже перезапуск: certbot и сценарии продления пользуются именно им [Apache-док; сторонний].

Если у хоста с `SSLEngine on` нет сертификата, Apache 2.4 не запускается с `AH02572: Failed to configure at least one certificate and key for <хост>:443` (при загруженном `mod_md` — предупреждение `AH10085` и ответ 503 на этом хосте); хост на порту 443 без `SSLEngine on` даёт при старте предупреждение `AH01916: … You configured HTTP(80) on the standard HTTPS(443) port!`, а браузер — `ERR_SSL_PROTOCOL_ERROR` [код `modules/ssl/ssl_engine_init.c` 2.4.52 и 2.4.58; уточнено 20.10.2026]. Сообщение «Server should be SSL-aware but has no certificate configured» из README.Debian («Common Problems», п. 5) относится к Apache 2.2.12 и в 2.4.52+ уже не выводится — README отстал от кода.

### 2.3. Имена, SNI и «первый» хост

- Несколько HTTPS-сайтов на одном IP:порту различаются по SNI; каждому — свой `<VirtualHost *:443>` с `ServerName`/`ServerAlias` и сертификатом [Apache-док].
- Клиент без SNI и запрос «по IP» попадают в **первый** хост `*:443` (порядок файлов `sites-enabled`) — сделайте первым «заглушку» с `Require all denied` (17.2) [практика].
- `LimitRequestFieldSize`, `LimitRequestLine`, `LimitRequestFields` читаются **только из первого хоста** для IP:порта [Apache-док] — задавайте их глобально.
- С 2.4.64 (и в обновлениях Ubuntu 2025 г.) Apache сверяет хост, выбранный по SNI, с хостом из заголовка `Host`; при несовместимых TLS-настройках — ответ **421 Misdirected Request**. Режим задаёт `SSLVHostSNIPolicy strict|secure|authonly|insecure` (умолчание `secure`; только в контексте сервера) [Apache-док]:

| Режим | Любое расхождение хостов | Разный сертификат/ключ, `SSLProtocol`, `SSLCipherSuite` | Разная проверка клиентских сертификатов |
|---|---|---|---|
| `strict` | блокируется | блокируется | блокируется |
| `secure` (умолчание) | разрешено | блокируется | блокируется |
| `authonly` | разрешено | разрешено | блокируется |
| `insecure` | разрешено | разрешено | разрешено (уязвимо к CVE-2025-23048) |

Типичный источник 421 — прокси (nginx, балансировщик) перед Apache, который ходит на `https://бэкенд` без передачи SNI (у nginx `proxy_ssl_server_name` по умолчанию `off` — подтверждено 20.10.2026 по nginx.org, `ngx_http_proxy_module` [сторонний]), или браузер, переиспользующий одно HTTP/2-соединение для двух имён с общим IP [практика]. Лечение — передавать SNI, развести имена по сертификатам или, осознанно, `SSLVHostSNIPolicy authonly`.

## 3. Сертификаты и ключи

### 3.1. Требования к сертификату сервера

- PEM: сертификат сервера, за ним промежуточные по порядку к корню (корень не нужен); к концу **первого** файла можно дописать параметры DH и кривую (с 2.4.7). Несколько пар `SSLCertificateFile`/`SSLCertificateKeyFile` — для разных алгоритмов (ECDSA и RSA) [Apache-док].
- Ключ и сертификат в одном файле документация называет «крайне нежелательным» (разные права, важен порядок директив) [Apache-док]; `make-ssl-cert` по README.Debian делает именно так — для своих сертификатов не повторяйте.
- Имя, по которому ходят клиенты, — в **subjectAltName** (SAN); на CN браузеры не смотрят [практика ⚠]. Для 1С по IP — `IP:` в SAN (`1c/05`, разд. 8.3).
- Срок: у Let's Encrypt сейчас 90 дней и сокращается (`1c/05`, 8.4); TLSRef для intermediate — рекомендуемый 90, максимум 366 дней [сторонний].

Проверки:

```bash
C=/etc/ssl/certs/srv-1c-app.fullchain.pem; K=/etc/ssl/private/srv-1c-app.key
openssl x509 -in "$C" -noout -subject -issuer -dates -ext subjectAltName
openssl x509 -in "$C" -noout -checkend $((30*86400)) && echo "ещё больше 30 дней" || echo "ИСТЕКАЕТ"
# сертификат и ключ — пара? (хеши открытых ключей должны совпасть)
openssl x509 -in "$C" -noout -pubkey | sha256sum
sudo openssl pkey -in "$K" -pubout | sha256sum
# сколько сертификатов в файле и в каком порядке
grep -c 'BEGIN CERTIFICATE' "$C"
openssl crl2pkcs7 -nocrl -certfile "$C" | openssl pkcs7 -print_certs -noout | grep -E 'subject|issuer'
# цепочка проверяется корнем организации
openssl verify -CAfile /usr/local/share/ca-certificates/corp-root-ca.crt -untrusted "$C" "$C"
# что реально отдаёт сервер (вся цепочка)
openssl s_client -connect srv-1c-app.example.local:443 -servername srv-1c-app.example.local -showcerts </dev/null
```

### 3.2. Где хранить и какие права

| Что | Где | Владелец, права | Почему |
|---|---|---|---|
| Ключ | `/etc/ssl/private/<имя>.key` | `root:root`, `600` | читает родительский процесс от `root` [Debian README; Apache-док] |
| Сертификат с цепочкой | `/etc/ssl/certs/<имя>.fullchain.pem` | `root:root`, `644` | публичные данные |
| Let's Encrypt | `/etc/letsencrypt/live/<имя>/fullchain.pem`, `privkey.pem` | ключ `600` (certbot с 0.29.0) | ссылаться на `live/`, не копировать [сторонний] |
| Корневой ЦС организации (для доверия на сервере) | `/usr/local/share/ca-certificates/corp-root-ca.crt` + `sudo update-ca-certificates` | `644` | расширение обязательно `.crt` [Ubuntu] |

```bash
sudo install -o root -g root -m 600 srv-1c-app.key /etc/ssl/private/srv-1c-app.key
sudo install -o root -g root -m 644 srv-1c-app.fullchain.pem /etc/ssl/certs/srv-1c-app.fullchain.pem
ls -l /etc/ssl/private/srv-1c-app.key              # -rw------- 1 root root
```

На Ubuntu 26.04 у юнита Apache включены ограничения systemd: в `debian/apache2.service` (метка `debian/2.4.66-2`) — `ProtectSystem=full` (`/usr`, `/boot`, `/etc` — только чтение), `ProtectHome=read-only`, `InaccessiblePaths=/root`, `PrivateDevices=yes`. Файлы в `/root` Apache не увидит, `/home` и `/etc` — только чтение; аппаратный токен PKCS#11 из `/dev` без переопределения юнита недоступен. Ключи и keytab держите в `/etc/ssl/private` и `/etc/apache2` — подробно в `1c/05`, разд. 6.1 и 11.3 [Debian; уточнено 20.10.2026; совпадение с пакетом Ubuntu на сервере проверьте: `systemctl cat apache2`]. Юнит 22.04/24.04 содержит `PrivateTmp=true` — файлы Apache в `/tmp` не видны другим службам [Debian].

**Пароль на ключе.** Если ключ зашифрован, при старте вызывается диалог `SSLPassPhraseDialog` (в Ubuntu — `exec:/usr/share/apache2/ask-for-passphrase`) [Apache-док; Debian]. Служба при перезагрузке сервера не поднимется без человека; на практике ключ хранят без пароля, но с правами `600` [Ubuntu docs; практика]. Альтернатива для строгих требований — ключ в токене PKCS#11 (`SSLCertificateKeyFile "pkcs11:…"`, с 2.4.42) [Apache-док].

### 3.3. Сертификат от корпоративного УЦ (AD CS)

Для внутренних имён (`*.example.local`) публичный УЦ сертификат не выдаст — используется УЦ организации. Порядок [практика; команды OpenSSL — сторонний]:

```bash
# 1) ключ и запрос (CSR) с SAN — на веб-сервере, ключ никуда не передаётся
sudo openssl req -new -newkey rsa:2048 -nodes \
     -keyout /etc/ssl/private/srv-1c-app.key -out ~/srv-1c-app.csr \
     -subj "/CN=srv-1c-app.example.local" \
     -addext "subjectAltName=DNS:srv-1c-app.example.local,DNS:1c.example.local"
sudo chmod 600 /etc/ssl/private/srv-1c-app.key
openssl req -in ~/srv-1c-app.csr -noout -text | grep -A1 'Subject Alternative Name'
```

```bat
rem 2) на Windows-машине с доступом к УЦ (шаблон «Веб-сервер» должен быть разрешён) — [сторонний Microsoft; ключ -attrib "Имя:значение" и атрибут CertificateTemplate=WebServer сверены 20.10.2026 по справке certreq]
certreq -submit -attrib "CertificateTemplate:WebServer" srv-1c-app.csr srv-1c-app.cer
```

```bash
# 3) если пришёл DER (.cer бинарный) — в PEM; собрать цепочку: свой → промежуточный(е)
openssl x509 -inform der -in srv-1c-app.cer -out srv-1c-app.pem   # только если файл DER
cat srv-1c-app.pem corp-issuing-ca.pem > srv-1c-app.fullchain.pem
# 4) установить (3.2) и прописать в хосте, затем configtest + reload
```

Если сертификат выдали в виде `.pfx` (PKCS#12) вместе с ключом:

```bash
openssl pkcs12 -in cert.pfx -nocerts -nodes -out key.pem          # ключ (без пароля!)
openssl pkcs12 -in cert.pfx -clcerts -nokeys -out cert.pem        # сертификат сервера
openssl pkcs12 -in cert.pfx -cacerts -nokeys -out chain.pem       # промежуточные
# старые PFX (RC2-40) в OpenSSL 3 читаются с ключом -legacy (подтверждено 20.10.2026 по openssl-pkcs12(1), OpenSSL 3.0)
```

Чтобы серверу (самому Apache при проксировании на HTTPS-бэкенд, `ldapsearch`, `curl`) доверять корпоративному УЦ — `sudo cp corp-root-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates` [Ubuntu]. Чтобы доверяли клиенты 1С — см. `1c/05`, разд. 8.3 (веб-клиент, тонкий клиент, `HttpsCA`) и `1c/08`, разд. 3.8 (`cacert.pem`/`cacertnx.pem`).

### 3.4. Самоподписанный сертификат и свой маленький УЦ

Для стенда или изолированной сети — `1c/05`, разд. 8.3 (порядок из [ИТС-адм разд. 4.3.9]: корневой сертификат, файл расширений с SAN, запрос, подпись), и [ИТС-мет 5979, 2020] (`openssl req -x509 -nodes -days 365 -newkey rsa:2048 …`). Методичка 5979 кладёт ключ в `/etc/ssl/certs` и ничего не говорит о правах — так не делайте, ключ — в `/etc/ssl/private` с `600` [ИТС-мет 5979, 2020; Debian README]. Однодневный «быстрый» вариант:

```bash
sudo openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
     -keyout /etc/ssl/private/stend.key -out /etc/ssl/certs/stend.crt \
     -subj "/CN=srv-obs.example.local" \
     -addext "subjectAltName=DNS:srv-obs.example.local,IP:10.10.20.30"
sudo chmod 600 /etc/ssl/private/stend.key
```

Свой постоянный УЦ на Ubuntu описан в документации Ubuntu Server («Obtain TLS certificates», раздел «Set up a manual Certificate Authority»: каталоги `/etc/ssl/CA`, `openssl ca`) [Ubuntu]. Для организации с AD CS предпочтителен корпоративный УЦ (3.3) — его корень уже доверен на доменных машинах [практика].

### 3.5. Let's Encrypt: certbot и альтернатива `mod_md`

Подробно (ключи certbot, профили, сокращение сроков, ARI, поведение разных версий) — в `1c/05`, разд. 8.4; здесь — только общее для любого сайта на Apache.

**Условия**: публичное DNS-имя → адрес сервера; порт 80 доступен из интернета (проверка HTTP-01 идёт только на порт 80). Проверка LE следует перенаправлениям — до 10, только на `http:`/`https:` и только на порты 80/443, сертификат при этом не проверяется [сторонний, Let's Encrypt «Challenge Types»]. Поэтому перенаправление HTTP→HTTPS проверке не мешает, если HTTPS-хост отдаёт тот же `/.well-known/acme-challenge/`; исключение для ACME в правиле перенаправления (как в TLSRef и `1c/05`) — страховка для `--webroot` [практика].

```bash
# вариант из репозитория Ubuntu (universe)
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d 1c.example.com -m admin@example.com --agree-tos -n
sudo certbot certificates                       # что выпущено, до какого числа
sudo certbot renew --dry-run                    # проверка продления
systemctl list-timers | grep -i certbot         # certbot.timer (apt); у snap — snap.certbot.renew.timer
```

- Пакет `certbot` ставит `certbot.service`, `certbot.timer` и `/etc/cron.d/certbot` [Ubuntu filelist]; задание cron при работающем systemd ничего не делает (проверка `! -d /run/systemd/system`), продлевает таймер — дважды в сутки со случайной задержкой до 12 ч [Debian, пакет certbot `debian/2.9.0-1`: `certbot.cron.d`, `certbot.timer`]. Документация Ubuntu Server советует snap (`sudo snap install --classic certbot`, таймер `snap.certbot.renew.timer`) — свежая версия 5.x вместо 1.21/2.9 [Ubuntu]. Обе сразу не ставьте — будут два таймера [практика].
- Плагин `--apache` сам создаёт хост `*-le-ssl.conf` и после продления перечитывает Apache [сторонний]. Для `certonly --webroot`/`--standalone` нужен deploy-хук:

```bash
sudo install -m 755 /dev/stdin /etc/letsencrypt/renewal-hooks/deploy/reload-apache.sh <<'EOF'
#!/bin/sh
systemctl reload apache2
EOF
sudo certbot renew --dry-run
```

- Файлы: `fullchain.pem` → `SSLCertificateFile` (Apache ≥ 2.4.8), `privkey.pem` → `SSLCertificateKeyFile`; `cert.pem`/`chain.pem` — только для Apache < 2.4.8 [сторонний, certbot].
- **OCSP**: Let's Encrypt не включает адрес OCSP в сертификаты с 07.05.2025 (с той же даты отклоняет запросы с OCSP Must-Staple) и выключил OCSP-ответчики 06.08.2025 [сторонний, Let's Encrypt]. Ключ certbot `--staple-ocsp` для LE бесполезен, `--must-staple` ломает выпуск; модуль `certbot.ocsp` объявлен устаревшим [сторонний, CHANGELOG certbot].
- **Удаление сертификата**: сначала убрать ссылки на него из конфигурации (`sudo grep -R live/<имя> /etc/apache2`), затем `certbot delete` — иначе Apache не запустится [сторонний].

**`mod_md`** — встроенный ACME-клиент (`md.load` в пакете Ubuntu), статус **Experimental**, нужен `mod_watchdog` [Apache-док]. Минимум: `MDomain 1c.example.com`, `MDCertificateAgreement accepted`, `MDContactEmail …` и хост `*:443` с `SSLEngine on` без путей к сертификату; до получения сертификата домен отвечает 503, новый подхватывается при следующем перезапуске; УЦ по умолчанию — `letsencrypt`, `MDRenewWindow 33%` [Apache-док]. Нам привычнее certbot.

### 3.6. Слежение за сроком и ротация

```bash
# проверка срока всех сертификатов, на которые ссылается Apache (запускать от root)
for f in $(sudo grep -rhoE 'SSLCertificateFile\s+\S+' /etc/apache2/sites-enabled /etc/apache2/conf-enabled | awk '{print $2}' | tr -d '"' | sort -u); do
  end=$(sudo openssl x509 -in "$f" -noout -enddate | cut -d= -f2)
  sudo openssl x509 -in "$f" -noout -checkend $((21*86400)) >/dev/null && st=OK || st=EXPIRING
  echo "$st  $end  $f"
done
```

- Порог 21 день — с запасом на сбой продления при сокращающихся сроках LE [практика].
- Эту же проверку удобно отдавать в мониторинг (Zabbix/Prometheus — `apache/03-…`); для публичных имён полезна внешняя проверка по `openssl s_client` [практика].
- После замены файлов — `sudo apache2ctl configtest && sudo systemctl reload apache2`, затем `openssl s_client … | openssl x509 -noout -dates` — убедиться, что отдаётся новый сертификат [практика]. `configtest` проверяет только синтаксис и наличие файлов: сертификаты и ключи `mod_ssl` загружает позже, на этапе инициализации (`post_config`), которого режим `-t` не выполняет [код `server/main.c`]. Поэтому перед `reload` сверьте пару ключ/сертификат (3.1): при ошибке мягкий перезапуск остановит Apache.

### 3.7. Ключ: RSA или ECDSA

- TLSRef intermediate допускает RSA (не меньше 2048 бит) и ECDSA на кривых `prime256v1`/`secp384r1`; профиль modern — только ECDSA [сторонний].
- Для 1С и внутренних клиентов разумно оставаться на **RSA 2048/3072**: старые тонкие клиенты и интеграции (Java, старые .NET) с ECDSA иногда не дружат ⚠ (практика, не проверялось).
- Можно отдавать оба сертификата одновременно: две пары `SSLCertificateFile`/`SSLCertificateKeyFile` в одном хосте — Apache выберет по возможностям клиента [Apache-док].

## 4. Протоколы, шифры, профили TLSRef (Mozilla)

### 4.1. `SSLProtocol`

- Синтаксис: `SSLProtocol [+|-]протокол …`; значения `SSLv3`, `TLSv1`, `TLSv1.1`, `TLSv1.2`, `TLSv1.3` (с OpenSSL 1.1.1), `all`. Умолчание — `all -SSLv3` (до 2.4.16 было `all`); контекст — сервер и виртуальный хост [Apache-док].
- `-all +TLSv1.2 +TLSv1.3` и `all -SSLv3 -TLSv1 -TLSv1.1` — одно и то же; генератор TLSRef с версии 5.8 пишет явный список (`-all +…`) [сторонний].
- Для name-based хостов с SNI собственный `SSLProtocol` каждого хоста учитывается с 2.4.42 при OpenSSL 1.1.1+; если в хосте не задан — берётся глобальный, а если и его нет — значение базового (первого) хоста [Apache-док].
- Ubuntu 26.04 штатно разрешает только TLS 1.2/1.3; 22.04/24.04 — формально `all -SSLv3`, фактически тоже только 1.2/1.3 из-за `SECLEVEL=2` (1.3).

### 4.2. `SSLCipherSuite`, `SSLHonorCipherOrder`

- `SSLCipherSuite [протокол] список` — список шифров OpenSSL через двоеточие. Для TLS 1.2 и ниже — без префикса (или с префиксом `SSL`); для TLS 1.3 — с префиксом `TLSv1.3` (OpenSSL 1.1.1+). Наборы TLS 1.3 нельзя задавать в контексте каталога (там нет повторного согласования) [Apache-док].
- С 2.4.7 `mod_ssl` безусловно дописывает к любому списку `!aNULL:!eNULL:!EXP` — нулевые и экспортные шифры отключены всегда [Apache-док].
- Умолчание `SSLCipherSuite` — `DEFAULT` (зависит от OpenSSL); Ubuntu ставит `HIGH:!aNULL` [Apache-док; Debian].
- `SSLCipherSuite` в `<Location>`/`<Directory>` вызывает повторное согласование TLS после чтения запроса — с TLS 1.3 это не работает; держите шифры на уровне хоста [Apache-док].
- `SSLHonorCipherOrder on|off` (умолчание `off`) — выбирать шифр по порядку сервера, а не клиента. TLSRef 6.0 для обоих профилей рекомендует `off` (`server_preferred_order: false`): все шифры в списке и так сильные, а клиент лучше знает, что у него быстрее (например, ChaCha20 без AES-NI) [Apache-док; сторонний]. Пример `SSLHonorCipherOrder on` с `RC4-SHA` в «SSL/TLS How-To» Apache — исторический, RC4 использовать нельзя [Apache-док; практика].
- Посмотреть, во что разворачивается строка: `openssl ciphers -v 'HIGH:!aNULL'` и `openssl ciphers -s -v 'DEFAULT:@SECLEVEL=2'` [Ubuntu; сторонний].

### 4.3. Профили TLSRef 6.0 (бывший Mozilla Server Side TLS)

Рекомендации Mozilla Server Side TLS переданы сообществу: страница `wiki.mozilla.org/Security/Server_Side_TLS` отсылает на `docs.tlsref.org`, а генератор `ssl-config.mozilla.org` — на `configurator.tlsref.org` [сторонний]. Машиночитаемые рекомендации версии 6.0 (`data.tlsref.org/guidelines/6.0.json`, совпадают по сути с Mozilla `guidelines/6.0.json`) содержат два профиля:

| Параметр | intermediate | modern |
|---|---|---|
| Версии TLS | 1.2, 1.3 | только 1.3 |
| Шифры TLS 1.2 (имена OpenSSL) | `ECDHE-ECDSA-AES128-GCM-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`, `ECDHE-ECDSA-AES256-GCM-SHA384`, `ECDHE-RSA-AES256-GCM-SHA384`, `ECDHE-ECDSA-CHACHA20-POLY1305`, `ECDHE-RSA-CHACHA20-POLY1305` | — |
| Наборы TLS 1.3 | `TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256` | те же |
| Группы (кривые) | `X25519MLKEM768`, `X25519`, `prime256v1`, `secp384r1` | те же |
| Сертификат | RSA ≥ 2048 или ECDSA (P-256/P-384) | только ECDSA |
| Порядок шифров сервера | нет (`SSLHonorCipherOrder off`) | нет |
| HSTS, минимум | 63 072 000 с (2 года) | то же |
| OCSP stapling | да | да |
| Срок сертификата | рекомендуемый 90 дней, максимум 366 | рекомендуемый и максимум 90 |
| Самые старые клиенты | Firefox 31.3, Android 4.4.2, Chrome 49, Edge 15 (Windows 10), IE 11 (Windows 10), Java 8u161, OpenSSL 1.0.1l, Safari 9 | Firefox 63, Android 10, Chrome 70, Edge 75, Java 11, OpenSSL 1.1.1, Safari 12.1 |

Профиля «old» в рекомендациях 6.0 нет (сам конфигуратор ещё показывает пункт «Old» — для крайних случаев) [сторонний].

Что генерирует конфигуратор TLSRef для Apache (шаблон `src/js/helpers/apache.js`, профиль intermediate, Apache 2.4.x) [сторонний], в переводе на раскладку Ubuntu:

```apache
# /etc/apache2/conf-available/tls-intermediate.conf  (глобально; затем: sudo a2enconf tls-intermediate)
SSLProtocol             -all +TLSv1.2 +TLSv1.3
SSLCipherSuite          ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305
SSLCipherSuite          TLSv1.3 TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256
SSLHonorCipherOrder     off
SSLSessionTickets       off
# Группы — только если OpenSSL их знает (см. ниже):
#SSLOpenSSLConfCmd      Curves X25519MLKEM768:X25519:prime256v1:secp384r1
```

Пояснения:

- Шаблон TLSRef добавляет `SSLOpenSSLConfCmd Curves …` (Apache ≥ 2.4.11) [сторонний]. Гибрид **`X25519MLKEM768`** есть в OpenSSL с 3.5 — в Ubuntu 26.04 (3.5.5), но не в 22.04/24.04 (3.0.x) [Ubuntu]. На 22.04/24.04 строку не задавайте или пишите `X25519:prime256v1:secp384r1`: OpenSSL 3.0 отвергает весь список, если в нём есть неизвестная группа, а `mod_ssl` при ошибке `SSLOpenSSLConfCmd` пишет `AH02407 "SSLOpenSSLConfCmd Curves …" failed` и не запускается [уточнено 20.10.2026 по коду: OpenSSL 3.0.13 `ssl/t1_lib.c` (`gid_cb`), `modules/ssl/ssl_engine_init.c` 2.4.58]. `configtest` эту ошибку не ловит — она возникает при инициализации TLS, поэтому после правки делайте `restart` и смотрите `systemctl status apache2`. `SSLOpenSSLConfCmd` — с 2.4.8 и OpenSSL 1.0.2 [Apache-док].
- `SSLCipherSuite TLSv1.3 …` повторяет умолчание OpenSSL — можно не писать; шифров DHE в профиле 6.0 нет — параметры DH не нужны [Ubuntu; сторонний].
- `conf-enabled/*.conf` загружается после `mods-enabled/*.conf` (порядок `IncludeOptional` в `apache2.conf`: `mods-enabled/*.load`, `mods-enabled/*.conf`, `ports.conf`, `conf-enabled/*.conf`, `sites-enabled/*.conf`) [Debian]; для `SSLProtocol` и `SSLCipherSuite` действует «последняя побеждает»: обработчик каждой такой директивы заново задаёт значение (у `SSLProtocol` разбор начинается с пустого набора), так что строка из `conf-enabled` заменит строку из `ssl.conf` [уточнено 20.10.2026 по коду `modules/ssl/ssl_engine_config.c`, ветка 2.4.x]. Можно и править сам `ssl.conf` — это conffile, dpkg сохранит правки [Debian].

**Какой профиль выбрать.** Для публикаций 1С и сервисов (Windows 10/11, современные браузеры, тонкие клиенты) — **intermediate**. **Modern** (только TLS 1.3) — для служебных интерфейсов с известными клиентами; до перехода проверьте старые тонкие клиенты 1С, интеграции на Java/.NET, мобильные приложения. Платформа 8.3.27 поддерживает TLS 1.0–1.3 [ИТС-адм разд. 8.9.2]; с какой версии платформы появился TLS 1.3 — ⚠ не проверялось. Со стороны клиента 1С версию TLS ограничивает `ForceTLS1_x` в `conf.cfg` (`1c/08`, разд. 7.2).

### 4.4. Сессии, повторное согласование, сжатие

| Директива | Умолчание Apache | В Ubuntu | Рекомендация | Источник |
|---|---|---|---|---|
| `SSLSessionTickets` | `on` | `off` с 24.04 | `off`: без ежедневного перезапуска билеты сессий ломают прямую секретность (PFS) | [Apache-док; Debian] |
| `SSLSessionCache` | `none` | `shmcb:${APACHE_RUN_DIR}/ssl_scache(512000)` | оставить | [Apache-док; Debian] |
| `SSLSessionCacheTimeout` | `300` | `300` | оставить; с 2.4.10 действует и для возобновления по RFC 5077 | [Apache-док] |
| `SSLCompression` | `off` | — | не включать (атака CRIME — так в документации `SSLCompression`) | [Apache-док] |
| `SSLInsecureRenegotiation` | `off` | закомментирован | не включать | [Apache-док; Debian] |
| `SSLStrictSNIVHostCheck` | `off` | закомментирован | `on`, если клиентов без SNI быть не должно | [Apache-док] |
| `SSLVHostSNIPolicy` (2.4.66) | `secure` | есть в обновлениях 22.04/24.04 | оставить `secure` | [Apache-док; Ubuntu] |
| `SSLEngine optional` | удалено в 2.4.64 | удалено и в пакетах Ubuntu (июль 2025) | убрать из старых конфигураций | [Apache-док; Ubuntu] |

### 4.5. Проверка того, что получилось

```bash
H=srv-1c-app.example.local
for v in tls1 tls1_1 tls1_2 tls1_3; do
  printf '%-7s ' $v; openssl s_client -connect $H:443 -servername $H -$v </dev/null 2>/dev/null \
    | grep -E '^ *(Protocol|Cipher) *:' | tr '\n' ' '; echo
done
# ожидание для intermediate: tls1 и tls1_1 — пусто (рукопожатие не удалось), tls1_2 и tls1_3 — протокол и шифр
openssl s_client -connect $H:443 -servername $H -tls1_2 -cipher 'AES128-SHA' </dev/null   # должно отказать
# список шифров снаружи (сторонние средства; ставить на админскую машину, не на сервер)
nmap --script ssl-enum-ciphers -p 443 $H        # [сторонний] пакет nmap
# testssl.sh — подробный аудит [сторонний]; для публичных имён — SSL Labs Server Test
```

В современных OpenSSL ключи `-tls1`/`-tls1_1` клиента сами могут быть запрещены уровнем безопасности на машине, с которой проверяете, — отказ ещё не доказывает, что сервер их не принимает; надёжнее внешний сканер [практика].

## 5. Перенаправление на HTTPS, HSTS, OCSP stapling, HTTP/2

### 5.1. Перенаправление HTTP → HTTPS

Простой вариант на `mod_alias` (модуль включён по умолчанию) [Apache-док; Debian]:

```apache
# /etc/apache2/sites-available/1c-http.conf
<VirtualHost *:80>
    ServerName srv-1c-app.example.local
    ServerAlias 1c.example.local
    Redirect permanent / https://srv-1c-app.example.local/
</VirtualHost>
```

- `Redirect` сохраняет хвост пути и строку запроса (`/demo/odata/...?$filter=…` уйдёт целиком) [Apache-док].
- **Тело POST при перенаправлении теряется** («Note that POSTs will be discarded») [Apache-док]: клиенты 301/302 повторяют запрос как GET. Поэтому интеграциям 1С (веб-сервисы, HTTP-сервисы, OData), тонким и мобильным клиентам сразу давайте `https://…` (то же в `1c/05`, разд. 8.2). Код 308 сохраняет метод и тело — `Redirect 308 / https://…/` (числовой статус 3xx допускается, если Apache его знает; подтверждено 20.10.2026 по коду 2.4.52: `mod_alias.c` принимает любой числовой 3xx, `http_protocol.c` знает «308 Permanent Redirect»; поведение браузеров — [сторонний, RFC 7538]).
- Вариант с исключением ACME (на `mod_rewrite`, нужен `sudo a2enmod rewrite`) — как в шаблоне TLSRef [сторонний]:

```apache
<VirtualHost *:80>
    ServerName 1c.example.com
    RewriteEngine On
    RewriteCond %{REQUEST_URI} !^/\.well\-known/acme\-challenge/
    RewriteRule ^.*$ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,QSA,L]
</VirtualHost>
```

- `%{HTTP_HOST}` берётся из запроса клиента: если сайт «ловит» любые имена (`ServerAlias *`), перенаправление уведёт на чужое имя; надёжнее писать своё имя явно [практика].
- В 2.4.64 была регрессия: все `RewriteCond expr …` вычислялись как «истина» (CVE-2025-54090, исправлено в 2.4.65) — `expr` в условиях лучше проверять после обновлений [Apache-док].

### 5.2. HSTS

```apache
# только в <VirtualHost *:443>; нужен mod_headers: sudo a2enmod headers
Header always set Strict-Transport-Security "max-age=63072000"
```

- `always` — чтобы заголовок шёл и в ответах-ошибках и перенаправлениях (в «табличке» `onsuccess` его не будет у ответов не-2xx) [Apache-док, `mod_headers`].
- TLSRef рекомендует минимум 63 072 000 с (2 года) и в шаблоне Apache добавляет `includeSubDomains` [сторонний]. `includeSubDomains` распространяет требование на все поддомены **этого** имени (`*.1c.example.com`), а не на родительский домен; если на поддоменах есть сайты только по HTTP — не добавляйте [практика].
- Пока HTTPS отлаживается — не включайте или ставьте `max-age=300`: браузер, получивший заголовок, до истечения срока не пустит на сайт по HTTP и не даст «принять» ошибочный сертификат [практика; то же в `1c/05`, разд. 8.2].
- Внутренние сайты с сертификатом корпоративного УЦ тоже можно защищать HSTS; для самоподписанных сертификатов HSTS сделает сайт недоступным в браузере, пока сертификат не станет доверенным [практика].
- HSTS действует только для браузеров. Тонкий клиент 1С, `curl`, интеграции его игнорируют — им нужен правильный адрес `https://` [практика].

### 5.3. OCSP stapling

Сервер сам получает у ответчика OCSP подписанный статус своего сертификата и вкладывает его в рукопожатие — клиенту не нужно ходить к УЦ [Apache-док]. Настройка (глобально, рядом с `SSLSessionCache`) [Apache-док, «SSL/TLS How-To»]:

```apache
# /etc/apache2/conf-available/ocsp-stapling.conf  — только для сертификатов с адресом OCSP!
SSLUseStapling On
SSLStaplingCache "shmcb:${APACHE_RUN_DIR}/ssl_stapling(32768)"
# рекомендации документации Apache для промышленной эксплуатации:
SSLStaplingReturnResponderErrors off
SSLStaplingResponderTimeout 4
SSLStaplingStandardCacheTimeout 172800
SSLStaplingErrorCacheTimeout 60
```

- Документация пишет путь `logs/…` относительно `ServerRoot` (в Ubuntu это `/etc/apache2`); сеансовый кеш Ubuntu лежит в `${APACHE_RUN_DIR}` — используйте его же [Apache-док; Debian]. `SSLStaplingCache` обязателен, `shmcb` требует `mod_socache_shmcb` (включается вместе с `ssl`).
- Умолчания: `SSLUseStapling off`, `SSLStaplingResponderTimeout 10`, `SSLStaplingStandardCacheTimeout 3600`, `SSLStaplingErrorCacheTimeout 600`, `SSLStaplingReturnResponderErrors on`, `SSLStaplingFakeTryLater on` [Apache-док].
- Адрес OCSP в сертификате: `openssl x509 -in cert.pem -noout -ocsp_uri`. Нет адреса — stapling бесполезен; свой ответчик — `SSLStaplingForceURL` [Apache-док]. Серверу нужен **исходящий** доступ к ответчику (HTTP).
- `AH02217: ssl_stapling_init_cert: Can't retrieve issuer certificate!` — в файле нет цепочки; `AH01929` — не удалось записать ответ в кеш (увеличьте кеш) [Apache-док].
- Проверка: `openssl s_client -connect $H:443 -servername $H -status </dev/null | grep -A5 'OCSP response'` → `successful`, `Cert Status: good` [Apache-док].
- **Let's Encrypt** — без OCSP с 2025 г. (3.5): stapling не включайте. **AD CS** — работает при опубликованном OCSP-ответчике (роль Online Responder) ⚠. Есть и реализация в `mod_md` (`MDStapling on`, с 2.4.42) [Apache-док]. CVE-2026-44185 (OCSP-запросы `mod_ssl`, 2.4.68) закрыта и в Ubuntu [Apache-док; Ubuntu].

### 5.4. HTTP/2

- Модуль `mod_http2` (`http2.load`, `http2.conf`) в пакете Ubuntu есть, но не включён. `sudo a2enmod http2` включает и `http2.conf` Debian, а там **глобально** `Protocols h2 h2c http/1.1` [Debian].
- Умолчание Apache — `Protocols http/1.1`; `h2` — HTTP/2 поверх TLS, `h2c` — открытым текстом. Порядок в списке — предпочтение сервера; `ProtocolsHonorOrder Off` отдаёт выбор клиенту [Apache-док].
- **MPM**: HTTP/2 поддерживается всеми MPM, но с `prefork` — «серьёзные ограничения»: один запрос за раз на соединение, долгий запрос блокирует остальные; обходится `H2MinWorkers` «на свой риск» [Apache-док, «HTTP/2 guide»]. Утверждение «HTTP/2 несовместим с prefork» неточно — несовместимы ожидания: выигрыша нет. Для 1С рекомендован `worker` [ИТС-адм разд. 8.2] — с ним HTTP/2 работает полноценно.
- `H2ModernTLSOnly on` (умолчание): для `h2` нужен TLS 1.2+ и шифр не из «чёрного списка» RFC 7540 — с профилем intermediate это выполняется; со старым списком шифров браузер молча откатится на HTTP/1.1 [Apache-док].
- `mod_http2` ограничивает размеры заголовков потоков теми же `LimitRequestLine`, `LimitRequestFields`, `LimitRequestFieldSize` (с 2.4.21) [Apache-док].
- **Нужно ли для 1С?** Веб-клиент работает и по HTTP/1.1, выигрыш от HTTP/2 для 1С не описан ⚠. Уязвимости в `mod_http2` идут постоянно: CVE-2026-23918 (important; по данным Apache — только 2.4.66, базовая версия Ubuntu 26.04; исправлено в `2.4.66-2ubuntu2.1` от 05.05.2026, ту же заплатку Ubuntu в тот же день выпустила и для 22.04 — `4.20`, и для 24.04 — `8.12`), CVE-2026-57941, CVE-2026-48913, CVE-2026-49975, CVE-2025-53020 [Apache-док; Ubuntu]. Включайте там, где он нужен (Redmine, NetBox, Grafana — много мелких ресурсов), `h2c` не нужен вовсе [практика].

```bash
sudo a2enmod http2 && sudo apache2ctl configtest && sudo systemctl reload apache2
curl -sI --http2 https://srv-itsm.example.local/ -o /dev/null -w '%{http_version}\n'   # 2
```

Если `h2` нужен только на одном хосте — не включайте `http2.conf` глобально: оставьте модуль, а `Protocols h2 http/1.1` пропишите в нужном `<VirtualHost *:443>` и `Protocols http/1.1` — глобально [Apache-док; практика].

## 6. Сведения о сервере, TRACE, заголовки безопасности, лишнее по умолчанию

### 6.1. `ServerTokens`, `ServerSignature`

| Директива | Умолчание Apache | Ubuntu (`security.conf`) | Рекомендация |
|---|---|---|---|
| `ServerTokens` | `Full` | `OS` | `Prod` (заголовок `Server: Apache`) |
| `ServerSignature` | `Off` | `On` | `Off` |
| `TraceEnable` | `on` | `Off` | оставить `Off` |

- `ServerTokens Major|Minor|Min[imal]|Prod[uctOnly]|OS|Full`, только в контексте сервера (не в хосте); влияет и на подпись `ServerSignature` [Apache-док].
- Документация прямо говорит: ставить ниже `Minimal` «не рекомендуется» — так сложнее отлаживать совместимость, а сокрытие заголовка `Server` «ничего не добавляет к безопасности» [Apache-док]. Тем не менее `Prod` уменьшает шум от сканеров и замечаний аудиторов [практика].
- `ServerSignature` добавляет строку с версией и именем хоста внизу страниц, сформированных сервером (ошибки, листинги, `mod_info`) [Apache-док].

```bash
sudo sed -i -E 's/^ServerTokens .*/ServerTokens Prod/; s/^ServerSignature .*/ServerSignature Off/' /etc/apache2/conf-available/security.conf
grep -E '^(ServerTokens|ServerSignature|TraceEnable)' /etc/apache2/conf-available/security.conf
sudo apache2ctl configtest && sudo systemctl reload apache2
curl -sI https://srv-1c-app.example.local/ | grep -i '^server:'         # Server: Apache
```

`security.conf` включён по умолчанию (`a2enconf security` в постустановочном сценарии) [Debian]. Это conffile — dpkg сохранит правки при обновлении [Debian; практика].

### 6.2. TRACE

`TraceEnable off` заставляет и ядро, и `mod_proxy` отвечать 405 на `TRACE`; ограничить `TRACE` через `<Limit>`/`<LimitExcept>` или `Require method` нельзя [Apache-док]. Документация подчёркивает, что включённый `TRACE` уязвимостью Apache не является — но сканеры (и аудиторы) его отмечают, а в Ubuntu он и так выключен [Apache-док; Debian]. Проверка: `curl -si -X TRACE https://$H/ | head -1` → `405`.

### 6.3. Заголовки безопасности (`mod_headers`)

`mod_headers` в Ubuntu не включён: `sudo a2enmod headers` [Debian]. `security.conf` содержит закомментированные примеры `X-Content-Type-Options: nosniff` и `Content-Security-Policy "frame-ancestors 'self';"` [Debian].

Особенности `Header` [Apache-док]:

- Синтаксис: `Header [условие] add|append|echo|edit|edit*|merge|set|setifempty|unset|note заголовок [значение] …`; `setifempty` — с 2.4.7, `expr=` — с 2.4.10.
- Условие `onsuccess` (по умолчанию) и `always` — это две разные «таблицы»: `always` попадает и в ответы-ошибки и перенаправления; заголовки бэкенда за `mod_proxy_fcgi` и CGI лежат в таблице `always`, а за `mod_proxy_http` (Redmine, NetBox, GlitchTip, Grafana) — в обычной `onsuccess` [код `mod_proxy_http.c`: заголовки ответа пишутся в `r->headers_out`]. При отдаче обе таблицы складываются — отсюда дубли, если и бэкенд, и Apache ставят одно и то же.

Набор для публикации 1С и сервисов [практика, кроме отмеченного]:

```apache
# в <VirtualHost *:443>
Header always set Strict-Transport-Security "max-age=63072000"
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
# Запрет встраивания в чужие сайты (защита от clickjacking):
Header always set Content-Security-Policy "frame-ancestors 'self'"
Header always set X-Frame-Options "SAMEORIGIN"
```

- **1С и встраивание веб-клиента** [ИТС-адм разд. 8.10.1.3]: веб-клиент и внешний сайт на одном веб-сервере — `X-Frame-Options "sameorigin"`; на разных — `"allow-from %ВебСайт%"`; встраивание запрещено — `"deny"`; без тонкой настройки — убедиться, что нет `"deny"`. `ALLOW-FROM` современные браузеры не поддерживают и заголовок с ним игнорируют целиком [сторонний, MDN «X-Frame-Options»; подтверждено 20.10.2026] — для встраивания с другого сайта: `Content-Security-Policy "frame-ancestors 'self' https://portal.example.com"`.
- **Строгий CSP (`script-src`/`default-src`) не задавайте**: веб-клиент 1С, Redmine, NetBox, GlitchTip, Grafana используют встроенные скрипты ⚠ (практика). Ограничивайтесь `frame-ancestors`.
- Если бэкенд за `mod_proxy_http` сам ставит эти заголовки, `Header always setifempty …` и `Header always unset …` его копию не видят (она в таблице `onsuccess`) — дубль останется. Шаблон из документации `mod_headers`: сначала `Header onsuccess unset <имя>`, затем `Header always set <имя> "…"`; для бэкенда за `mod_proxy_fcgi`/CGI достаточно `Header always set` [Apache-док; код `mod_proxy_http.c`]. `X-XSS-Protection` устарел и нестандартен [сторонний, MDN; подтверждено 20.10.2026].

Проверка: `curl -sI https://$H/demo/ru_RU/ | grep -iE 'strict-transport|x-content|x-frame|content-security|referrer'`.

### 6.4. Что Ubuntu включает «из коробки» и что стоит убрать

| Что | Как сделано в Ubuntu | Риск | Что сделать |
|---|---|---|---|
| Листинг каталогов | `<Directory /var/www/>` с `Options Indexes FollowSymLinks`; модуль `autoindex` включён | показ содержимого каталогов без `index.html` | `Options -Indexes` (или `Options FollowSymLinks`) в своих хостах; при ненадобности `sudo a2dismod -f autoindex` |
| Сайт `000-default` | включён; отвечает на любое имя на `*:80` | публикация доступна «по IP», лишняя поверхность | `sudo a2dissite 000-default` или заглушка `Require all denied` |
| `/server-status` | `status` включён, `Require local`, `ExtendedStatus On`, `ProxyStatus On` | за локальным прокси «local» — все (см. 7.4) | ограничить по IP/паролю; подробно — `apache/03-…` |
| `/ldap-status` | появляется при `a2enmod ldap` (`ldap.conf`: `Require local`) | то же | то же |
| `access_compat` | включён (старые `Order/Allow/Deny`) | смешение со `Require` даёт неожиданный результат | переписать на `Require`, затем `a2dismod access_compat` (если модули/сайты его не требуют) |
| `serve-cgi-bin.conf` | включён (`ScriptAlias /cgi-bin/` при наличии `mod_cgi`/`mod_cgid`) | исполнение CGI | `sudo a2disconf serve-cgi-bin`, если CGI не нужен |
| Каталоги VCS | в `security.conf` закомментировано `RedirectMatch 404 /\.git` | утечка исходников | раскомментировать, если в `DocumentRoot` бывают репозитории |

Хорошо сделано изначально: `<FilesMatch "^\.ht">` → `Require all denied`; `<Directory />` → `Require all denied`, `AllowOverride None`; `/usr/share` открыт (`Require all granted`) — не делайте туда `Alias` без нужды. `AllowCONNECT` в `mod_proxy_connect` Debian выключил по умолчанию в `2.4.59-1` (апрель 2024) — это есть только в 26.04; в 22.04/24.04 действует умолчание Apache `AllowCONNECT 443 563` [Debian/Ubuntu, журнал пакета; уточнено 20.10.2026].

Источник содержимого — `debian/config-dir/apache2.conf.in`, `security.conf`, `status.conf`, `ldap.conf`, сценарий `apache2.postinst` (список модулей по умолчанию: `authz_host auth_basic access_compat authn_file authz_user alias dir autoindex env mime negotiation setenvif filter deflate status reqtimeout`; конфигурации: `charset localized-error-pages other-vhosts-access-log security serve-cgi-bin`) [Debian].

`AllowOverride None` в своих `<Directory>` — `.htaccess` не читается, правила видны в одном месте и не надо каждый раз искать файлы по дереву [Apache-док «Security Tips»; практика]. Для публикаций 1С `webinst` сам пишет блок `<Directory>` (`AllowOverride None`, `Options None` в официальном примере) — `1c/05`.

## 7. Ограничение доступа: `Require`, `mod_authz_core`, `mod_authz_host`

### 7.1. Провайдеры `Require`

| Провайдер | Модуль | Пример | Примечание |
|---|---|---|---|
| `all granted` / `all denied` | `mod_authz_core` | `Require all denied` | замена `Allow from all` / `Deny from all` |
| `env` | `mod_authz_core` | `Require env let_me_in` | переменная от `SetEnvIf`; в подзапросах не наследуется |
| `method` | `mod_authz_core` | `Require method GET POST OPTIONS` | GET и HEAD эквивалентны; `TRACE` недоступен |
| `expr` | `mod_authz_core` | `Require expr "%{TIME_HOUR} -ge 9 && %{TIME_HOUR} -le 17"` | выражения `ap_expr`; до 2.4.16 без кавычек |
| `ip` | `mod_authz_host` | `Require ip 10.10.20.0/24 192.168.1.50` | полный адрес, начало адреса (`10.1`), сеть/маска, CIDR, IPv6; разбирается при старте |
| `host` | `mod_authz_host` | `Require host example.local` | двойной DNS-поиск (обратный + прямой) на каждый запрос |
| `forward-dns` | `mod_authz_host` | `Require forward-dns admin-pc.example.local` | только полное имя; без обратного DNS; с 2.4.19 |
| `local` | `mod_authz_host` | `Require local` | 127.0.0.0/8, ::1 или адрес клиента = адрес сервера |
| `user`, `valid-user` | `mod_authz_user` | `Require valid-user` | после аутентификации |
| `group` | `mod_authz_groupfile` | `Require group admins` | файл групп `AuthGroupFile` |
| `ldap-user`, `ldap-group`, `ldap-dn`, `ldap-attribute`, `ldap-filter`, `ldap-search` | `mod_authnz_ldap` | `Require ldap-group CN=…` | раздел 9 |
| `ssl`, `ssl-verify-client` | `mod_ssl` | `Require ssl` | только по HTTPS / только с проверенным клиентским сертификатом |

Источник — описание `Require` в `mod_authz_core` и `mod_authz_host` [Apache-док].

### 7.2. Логика: `RequireAll`, `RequireAny`, `RequireNone`

- Несколько `Require` в одной секции без контейнера — **неявный `<RequireAny>`**: первый разрешивший разрешает весь запрос, остальные не проверяются [Apache-док].
- Каждый провайдер возвращает «разрешено», «запрещено» или «нейтрально». `<RequireAny>`: разрешено, если хоть один разрешил; `<RequireAll>`: разрешено, если никто не запретил и хоть один разрешил; `<RequireNone>`: «не провалено», если никто не разрешил [Apache-док].
- `Require not …` и `<RequireNone>` сами по себе разрешить не могут — только запретить; внутри `<RequireAny>` отрицание не допускается [Apache-док].
- **Директивы авторизации из `<Location>` по умолчанию заменяют** авторизацию из `<Directory>`/`<Files>` (`AuthMerging Off`); `AuthMerging And|Or` объединяет [Apache-док]. Документация отдельно предупреждает об осторожности с `<Location>`, пересекающимися с файловым содержимым.

Примеры [Apache-док; адаптация — практика]:

```apache
# Только из сети администраторов И по паролю
<Location "/server-status">
    AuthType Basic
    AuthName "Monitoring"
    AuthBasicProvider file
    AuthUserFile /etc/apache2/htpasswd/monitoring
    <RequireAll>
        Require ip 10.10.20.0/24
        Require valid-user
    </RequireAll>
</Location>

# Из офиса — без пароля, снаружи — с паролем
<Location "/hs-portal">
    AuthType Basic
    AuthName "Portal"
    AuthBasicProvider file
    AuthUserFile /etc/apache2/htpasswd/portal
    <RequireAny>
        Require ip 10.10.0.0/16
        Require valid-user
    </RequireAny>
</Location>

# Чтение (GET, HEAD, OPTIONS) без входа, остальные методы (POST, PUT, DELETE…) — после входа
# (в примере документации в списке есть и POST — тогда POST тоже пройдёт без пароля)
<Location "/wiki-pub">
    AuthType Basic
    AuthName "Wiki"
    AuthBasicProvider file
    AuthUserFile /etc/apache2/htpasswd/wiki
    <RequireAny>
        Require method GET OPTIONS
        Require valid-user
    </RequireAny>
</Location>
```

### 7.3. Старый синтаксис (`Order/Allow/Deny`) — не смешивать

Модуль `mod_access_compat` (включён в Ubuntu) понимает директивы Apache 2.2. Смешивать их со `Require` в одной секции нельзя предсказуемо; переписывайте [Apache-док «Upgrading to 2.4»; практика]. Соответствие: `Order deny,allow` + `Deny from all` → `Require all denied`; `Order allow,deny` + `Allow from all` → `Require all granted`; `Allow from 10.10` → `Require ip 10.10`. Официальный пример 1С для Kerberos написан на синтаксисе 2.2 (`Order allow,deny`, `Allow from all`) [ИТС-адм разд. 2.8.1.2] — для 2.4 вместо них `Require valid-user`.

### 7.4. Клиентский адрес за прокси и `Require local`

- Если запрос приходит через обратный прокси, адрес клиента — это адрес прокси; `Require ip` проверяет его [Apache-док `mod_authz_host`, «Security Note»].
- Решение — `mod_remoteip` (`sudo a2enmod remoteip`): `RemoteIPHeader X-Forwarded-For` и список доверенных прокси `RemoteIPInternalProxy 10.10.20.5` (или `RemoteIPTrustedProxy`); тогда `Require ip`, журналы и `REMOTE_ADDR` видят реальный адрес. Без списка доверенных любой клиент подделает заголовок [Apache-док; практика]. Подробно — `apache/03-…`.
- `Require local` считает «локальным» и соединение, у которого адрес клиента совпадает с адресом сервера. Если перед Apache на **том же хосте** стоит nginx или другой прокси, все внешние запросы приходят с 127.0.0.1 — и `/server-status`, `/ldap-status`, `/md-status` с `Require local` станут видны всему миру [Apache-док; практика]. Либо `mod_remoteip`, либо закрыть служебные пути на самом прокси.

### 7.5. Типовые ограничения для нашей среды

```apache
# srv-1c-app: OData и HTTP-сервисы публикации demo — только с серверов интеграции
<Location "/demo/odata">
    Require ip 10.10.30.11 10.10.30.12
</Location>
<Location "/demo/hs">
    Require ip 10.10.30.0/24
</Location>

# srv-itsm: административные разделы — только из сети ИТ
<Location "/admin">
    Require ip 10.10.20.0/24
</Location>
```

Для публикаций 1С правила кладите в **отдельный файл** (`/etc/apache2/conf-available/1c-access.conf`, затем `sudo a2enconf 1c-access`), а не в блок, записанный `webinst`: при перепубликации утилита его перезапишет; более частный `<Location>` пишите ниже общего (`1c/05`, разд. 11.4) [практика].

Проверка: `curl -s -o /dev/null -w '%{http_code}\n' https://$H/demo/odata/standard.odata/` с разрешённой и запрещённой машины (ожидается 401 от 1С и 403 от Apache соответственно) [практика].

## 8. Basic-аутентификация (`htpasswd`)

### 8.1. Модули и директивы

Включены по умолчанию: `auth_basic`, `authn_file`, `authz_user`, `authz_host` (+ `authn_core`/`authz_core`) [Debian]. Директивы [Apache-док]:

| Директива | Модуль | Смысл, умолчание |
|---|---|---|
| `AuthType None\|Basic\|Digest\|Form` | `mod_authn_core` | способ аутентификации |
| `AuthName "область"` | `mod_authn_core` | область (realm), показывается в окне входа |
| `AuthBasicProvider провайдер …` | `mod_auth_basic` | откуда брать пользователей; умолчание `file` |
| `AuthUserFile путь` | `mod_authn_file` | файл паролей |
| `AuthGroupFile путь` | `mod_authz_groupfile` | файл групп (`имя: user1 user2`) |
| `AuthBasicAuthoritative On\|Off` | `mod_auth_basic` | передавать ли другим модулям при неудаче; умолчание `On` |
| `AuthBasicFake` | `mod_auth_basic` | подставить «поддельный» Basic в запрос к бэкенду (с 2.4.5) |
| `AuthzSendForbiddenOnFailure On\|Off` | `mod_authz_core` | 403 вместо 401 после неудачной авторизации; умолчание `Off` (с 2.3.11) |

Digest-аутентификацию (`mod_auth_digest`) не используйте: она слабее TLS+Basic, и в 2.4.69 в ней исправлено сразу несколько CVE (CVE-2026-73636 — повтор захваченных учётных данных при `AuthDigestNonceLifetime 0`; CVE-2026-73637, CVE-2026-48005 — отказ в обслуживании); поддержка RFC 2069 удалена [Apache-док].

### 8.2. Файл паролей

```bash
sudo install -d -o root -g www-data -m 750 /etc/apache2/htpasswd
# -c создаёт файл и ЗАТИРАЕТ существующий — только для первого пользователя!
sudo htpasswd -c -B -C 12 /etc/apache2/htpasswd/monitoring zabbix
sudo htpasswd -B -C 12 /etc/apache2/htpasswd/monitoring ivanov       # добавить/сменить пароль
printf '%s' "$PASS" | sudo htpasswd -i -B /etc/apache2/htpasswd/monitoring robot   # из сценария (stdin)
sudo htpasswd -v /etc/apache2/htpasswd/monitoring ivanov             # проверить пароль (с 2.4.5)
sudo htpasswd -D /etc/apache2/htpasswd/monitoring petrov             # удалить пользователя
sudo chown root:www-data /etc/apache2/htpasswd/monitoring && sudo chmod 640 /etc/apache2/htpasswd/monitoring
sudo -u www-data head -c0 /etc/apache2/htpasswd/monitoring && echo "www-data читает"
```

Ключи `htpasswd` [Apache-док]:

| Ключ | Что делает |
|---|---|
| `-c` | создать файл (существующий перезаписывается) |
| `-B` | bcrypt — «очень безопасный»; рекомендуемый вариант |
| `-C N` | стоимость bcrypt: умолчание 5, допустимо 4–17 (apr-util ≥ 1.6.0 ограничивает 17). Значение 10–12 — компромисс [практика] |
| `-m` | MD5 Apache (`$apr1$`) — **умолчание** с 2.2.18; работает только в Apache |
| `-2` / `-5` | SHA-256 / SHA-512 `crypt()`, `-r` — раунды (умолчание 5000); **с 2.4.59** — в Ubuntu только 26.04 |
| `-s`, `-d`, `-p` | SHA-1 без соли, `crypt()` (8 символов), открытый текст — небезопасно |
| `-b` / `-i` | пароль в командной строке (виден в `ps`) / из stdin — для сценариев только `-i` |
| `-n`, `-D`, `-v` | вывести строку на экран; удалить пользователя; проверить пароль (с 2.4.5) |

Файл паролей — **вне** `DocumentRoot` (не должен скачиваться браузером) [Apache-док]. Имя пользователя — до 255 байт, без двоеточия [Apache-док]. `htpasswd` — в пакете `apache2-utils` [Ubuntu filelist].

### 8.3. Конфигурация

```apache
<Location "/grafana-admin">
    AuthType Basic
    AuthName "Grafana admin"
    AuthBasicProvider file
    AuthUserFile /etc/apache2/htpasswd/monitoring
    Require valid-user
</Location>
```

- Basic передаёт имя и пароль в base64 — по сути открытым текстом: **только поверх HTTPS**; на HTTP-хосте делайте перенаправление, а не аутентификацию [практика; то же в `1c/05`, разд. 11.2].
- Браузер повторяет `Authorization` на каждый запрос, а `mod_authn_file` читает файл заново — для файла на сотни строк это не проблема; кеш `mod_authn_socache` для `file` бесполезен (документация советует его только для SQL — `mod_authn_dbd`) [Apache-док].
- «Выйти» из Basic нельзя — браузер помнит пароль до закрытия [практика].
- Если за Apache стоит приложение со своей аутентификацией (Redmine, NetBox, GlitchTip, Grafana), Basic Apache перехватит заголовок `Authorization`, и API-клиенты с токеном в `Authorization` перестанут работать. Закрывайте Basic только служебные пути (или ограничивайте по IP) [практика].
- **Для 1С** Basic веб-сервера — это официальный уровень аутентификации: учётные данные передаются в 1С, поэтому пользователь должен существовать и в файле Apache, и в базе с тем же паролем; для сервисов (OData, HTTP- и веб-сервисы) заголовок `Authorization` один на двоих [ИТС-адм разд. 8.9.1, по `1c/05`, разд. 11.1 и 11.4]. Чаще правильнее ограничивать сервисы по IP (7.5), а не ставить на них Basic Apache.

## 9. LDAP и Active Directory (`mod_ldap`, `mod_authnz_ldap`)

### 9.1. Как работает

- `mod_ldap` — пул соединений и кеш; `mod_authnz_ldap` — провайдер аутентификации `ldap` (для `AuthBasicProvider`) и провайдеры авторизации `ldap-user`, `ldap-group`, `ldap-dn`, `ldap-attribute`, `ldap-filter`, `ldap-search` [Apache-док].
- **Фаза аутентификации** («поиск/привязка»): из `AuthLDAPURL` и введённого имени строится фильтр `(&(фильтр)(атрибут=имя))`, выполняется поиск; если найдена **ровно одна** запись — Apache делает привязку (bind) её DN с введённым паролем [Apache-док].
- **Фаза авторизации** («сравнение»): `Require ldap-group` и др. сравнивают атрибуты; для групп по умолчанию ищется членство в атрибутах `member` и `uniqueMember` [Apache-док].
- Результаты кешируются по настройкам `mod_ldap`: изменения в каталоге (блокировка, смена пароля, исключение из группы) видны **не сразу** [Apache-док, «General caveats»].
- В Ubuntu `mod_ldap` собран с OpenLDAP (`libldap2`) и драйвером `libaprutil1-ldap` — оба в зависимостях `apache2-bin` [Ubuntu].

```bash
sudo a2enmod authnz_ldap            # # Depends: ldap — включит и mod_ldap
sudo apache2ctl -M | grep -E 'ldap' # authnz_ldap_module, ldap_module
```

### 9.2. `AuthLDAPURL`

Синтаксис: `AuthLDAPURL url [NONE|SSL|TLS|STARTTLS]`, где `url` — `ldap[s]://хост[:порт] [хост2 …]/базовый_DN?атрибут?область?фильтр` (RFC 2255) [Apache-док]:

| Часть | Значение | Для AD |
|---|---|---|
| схема | `ldap` или `ldaps` (SSL, порт по умолчанию 636) | `ldaps` |
| хосты | несколько через пробел — пробуются по очереди (не круговая балансировка); тогда весь URL в кавычках | два контроллера |
| базовый DN | откуда искать | `DC=example,DC=local` или OU |
| атрибут | по какому атрибуту искать имя; только первый из списка; умолчание `uid` | `sAMAccountName` (вход «ivanov») или `userPrincipalName` (вход «ivanov@example.local») |
| область | `one` или `sub` (умолчание `sub`; `base` не поддерживается) | `sub` |
| фильтр | умолчание `(objectClass=*)`; ~8000 символов максимум; `none` (с 2.4.10) — без фильтра | `(objectClass=user)` |
| второй параметр | `NONE`, `SSL`, `TLS`/`STARTTLS` — тип соединения поверх `LDAPTrustedMode`; для `ldap://` позволяет STARTTLS на том же порту | — |

Перечисленные в URL атрибуты попадают в переменные окружения `AUTHENTICATE_<атрибут>` (и `AUTHORIZE_…` при авторизации) — их видят CGI и другие модули [Apache-док].

**Глобальный каталог AD** (порт 3268, по SSL — 3269) позволяет искать по всем доменам леса одной операцией: `AuthLDAPURL ldap://10.0.0.1:3268/?userPrincipalName?sub` с пустым базовым DN; входить тогда нужно по UPN [Apache-док, «Using Active Directory»].

### 9.3. Защищённое соединение с контроллером (LDAPS / STARTTLS)

- Пароль пользователя при Basic+LDAP уходит на контроллер в операции bind — **обязательно** LDAPS (`ldaps://…:636`) или STARTTLS. Microsoft постепенно требует подписи/защиты LDAP ⚠ (политики AD в этой сессии не перечитывались) [практика].
- Корневой сертификат УЦ, выдавшего сертификаты контроллерам, задаётся `LDAPTrustedGlobalCert` (только контекст сервера) с типом `CA_BASE64` (PEM) или `CA_DER`; клиентские сертификаты — `LDAPTrustedClientCert` (в каталоге) [Apache-док].
- `LDAPVerifyServerCert On` — проверка сертификата LDAP-сервера, **умолчание `On`**; не выключайте [Apache-док].
- `LDAPTrustedMode NONE|SSL|TLS` — режим по умолчанию для соединений; при `ldaps://` режим принудительно SSL [Apache-док].
- Для OpenLDAP-SDK документация замечает, что STARTTLS «работает не во всех версиях»; надёжнее `ldaps://` [Apache-док].

### 9.4. Пример: вход по учётной записи домена и группе AD

```apache
# /etc/apache2/conf-available/ldap-ad.conf   (контекст сервера; sudo a2enconf ldap-ad)
LDAPTrustedGlobalCert CA_BASE64 /usr/local/share/ca-certificates/corp-root-ca.crt
LDAPVerifyServerCert On
LDAPConnectionTimeout 5
LDAPTimeout 15
LDAPCacheTTL 300
LDAPOpCacheTTL 300
```

```apache
# в нужном <VirtualHost *:443>
<Location "/ops">
    AuthType Basic
    AuthName "Учётная запись домена EXAMPLE"
    AuthBasicProvider ldap
    AuthLDAPURL "ldaps://dc1.example.local dc2.example.local/DC=example,DC=local?sAMAccountName?sub?(objectClass=user)"
    AuthLDAPBindDN "svc-apache-ldap@example.local"
    AuthLDAPBindPassword "exec:/bin/cat /etc/apache2/secrets/ldap-bind.pass"
    LDAPReferrals Off
    # вложенные группы AD: класс объекта группы в AD — group
    AuthLDAPSubGroupClass group
    AuthLDAPMaxSubGroupDepth 3
    Require ldap-group CN=GG-IT-Ops,OU=Groups,DC=example,DC=local
</Location>
```

```bash
sudo install -d -o root -g root -m 700 /etc/apache2/secrets
sudo install -o root -g root -m 600 /dev/null /etc/apache2/secrets/ldap-bind.pass
sudoedit /etc/apache2/secrets/ldap-bind.pass          # одна строка — пароль svc-apache-ldap (не в истории shell)
sudo apache2ctl configtest && sudo systemctl reload apache2
curl -s -o /dev/null -w '%{http_code}\n' -u ivanov https://srv-itsm.example.local/ops/   # 200 / 401
```

Пояснения:

- **`AuthLDAPBindDN`/`AuthLDAPBindPassword`** — учётка для поиска (без них — анонимный поиск, которого AD не разрешает [практика]). Пример в документации Apache для AD использует UPN (`apache@example.com`) [Apache-док]. `AuthLDAPBindPassword exec:программа` (с 2.4.5) берёт пароль из первой строки вывода программы — его нет в конфигурации [Apache-док]; программа запускается при чтении конфигурации (обработчик директивы `set_bind_password` в `mod_authnz_ldap.c`), то есть в главном процессе от `root` до сброса привилегий, — поэтому файл с паролем может быть `root:root 600` [уточнено 20.10.2026 по коду ветки 2.4.x]. Учётке — только чтение каталога, без интерактивного входа [практика].
- **`LDAPReferrals Off`** — при поиске от корня домена AD отдаёт ссылки на разделы `DomainDnsZones`/`ForestDnsZones`/`Configuration`, их обход даёт задержки и «Operations error» ⚠ (практика; документация Apache: умолчание `On`, значение `default` — с 2.4.7, контекст — каталог).
- **Вложенные группы**: глубина `AuthLDAPMaxSubGroupDepth` (умолчание 10), но подгруппами считаются только объекты классов `AuthLDAPSubGroupClass` — по умолчанию `groupOfNames groupOfUniqueNames` [Apache-док]; у групп AD класс `group` (LDAP-имя класса Group в схеме AD — `group` [сторонний, Microsoft «Group class»; подтверждено 20.10.2026]) — без `AuthLDAPSubGroupClass group` вложенность не работает. Для больших невложенных групп документация советует глубину 0 [Apache-док]. Альтернатива — `Require ldap-filter "memberOf:1.2.840.113556.1.4.1941:=CN=GG-IT-Ops,…"`: OID — правило LDAP_MATCHING_RULE_IN_CHAIN, проходящее цепочку вложенности [сторонний, Microsoft «Search Filter Syntax»]; внешние скобки не нужны — `mod_authnz_ldap` сам строит фильтр `(&(<фильтр>)(<атрибут>=<имя>))` [код `mod_authnz_ldap.c`; уточнено 20.10.2026].
- DN в `Require ldap-group`/`ldap-dn` пишется **без кавычек**; `AuthLDAPGroupAttributeIsDN on` (умолчание) — в группе ищется DN пользователя, для AD это правильно; `AuthLDAPRemoteUserAttribute` — атрибут для `REMOTE_USER` (должен быть в URL), `AuthLDAPRemoteUserIsDN on` — полный DN [Apache-док].
- Отключённая в AD учётка не проходит привязку, но кешированный успех держится до `LDAPCacheTTL` (600 с), сравнения — до `LDAPOpCacheTTL` (600 с). `mod_authn_socache` для LDAP не нужен — у модуля свой кеш [Apache-док].

### 9.5. Параметры `mod_ldap` (умолчания)

| Директива | Умолчание | Контекст | Комментарий |
|---|---|---|---|
| `LDAPCacheEntries` | 1024 | сервер | записей в кеше поиска/привязки |
| `LDAPCacheTTL` | 600 | сервер | секунды |
| `LDAPOpCacheEntries` | 1024 | сервер | кеш сравнений |
| `LDAPOpCacheTTL` | 600 | сервер | секунды |
| `LDAPSharedCacheSize` | 500000 | сервер | байт разделяемой памяти |
| `LDAPConnectionTimeout` | 10 с, если библиотека поддерживает | сервер | таймаут TCP-соединения |
| `LDAPTimeout` | 60 | сервер | поиск и привязка (с 2.3.5) |
| `LDAPRetries` | 3 | сервер | повторы при ошибках |
| `LDAPRetryDelay` | 0 | сервер | пауза между повторами |
| `LDAPConnectionPoolTTL` | -1 | сервер, хост | возраст соединения в пуле |
| `LDAPReferrals` | `On` | каталог | см. выше |
| `LDAPVerifyServerCert` | `On` | сервер | проверка сертификата |

Источник — синтаксис директив `mod_ldap` [Apache-док]. Документация отмечает: при «тихом» сбросе соединений брандмауэром `LDAPTimeout` вызывает повтор; лучше, чтобы брандмауэр отвечал TCP RST [Apache-док].

Статистику кеша показывает обработчик `ldap-status`; в Ubuntu `ldap.conf` вешает его на `/ldap-status` с `Require local` [Apache-док; Debian] — см. оговорку о локальном прокси (7.4).

### 9.6. Проверка и отладка

```bash
sudo apt install -y ldap-utils            # ldapsearch (OpenLDAP) [Ubuntu]
LDAPTLS_CACERT=/usr/local/share/ca-certificates/corp-root-ca.crt \
ldapsearch -H ldaps://dc1.example.local -D svc-apache-ldap@example.local -W \
           -b "DC=example,DC=local" "(sAMAccountName=ivanov)" dn memberOf
# временно подробный журнал модулей (потом вернуть!)
sudoedit /etc/apache2/conf-available/ldap-ad.conf      # LogLevel warn authnz_ldap:debug ldap:debug
sudo systemctl reload apache2; sudo tail -f /var/log/apache2/error.log
```

`LDAPTLS_CACERT` — переменная клиентской библиотеки OpenLDAP: любой параметр `ldap.conf` можно задать переменной `LDAP<параметр>`, здесь — `TLS_CACERT` [сторонний, `ldap.conf(5)` OpenLDAP; подтверждено 20.10.2026]. Отладку на уровне библиотеки включает `LDAPLibraryDebug 7` (контекст сервера) [Apache-док]. Если `ldapsearch` работает, а Apache нет — почти всегда доверие к сертификату (`LDAPTrustedGlobalCert`) или referrals [практика].

### 9.7. Безопасность LDAP-входа

- При Basic+LDAP Apache видит пароль домена каждого пользователя — компрометация веб-сервера = компрометация паролей. Для внутренних пользователей лучше Kerberos (раздел 10), для внешних — OIDC через корпоративный провайдер (у 1С — свой механизм OpenID Connect, `1c/08`, разд. 6.3) [практика].
- Выражения в `ldap-filter`/`ldap-search` экранируйте функцией `ldap` (защита от LDAP-инъекции) [Apache-док].
- В 2.4.68 исправлено использование освобождённой памяти в `mod_ldap` в контексте каталога (CVE-2026-29167; перенесено во все три выпуска Ubuntu) [Apache-док; Ubuntu].

## 10. Kerberos (SPNEGO): `mod_auth_gssapi`

### 10.1. Что выбрать

| Модуль | Пакет Ubuntu | Статус | Когда |
|---|---|---|---|
| `mod_auth_gssapi` | `libapache2-mod-auth-gssapi` (universe): 1.6.3 (22.04), 1.6.4 (24.04, 26.04) | развивается, «замена устаревшего `mod_auth_kerb`»; нужен MIT krb5 ≥ 1.11 и Apache ≥ 2.4.11 | всё новое [сторонний; Ubuntu] |
| `mod_auth_kerb` | `libapache2-mod-auth-kerb` — только 22.04 (5.4-2.5) | не развивается | только если нужен в точности официальный рецепт 1С [ИТС-адм разд. 2.8.1.2; `1c/05`, разд. 11.3] |

Пакет ставит `/etc/apache2/mods-available/auth_gssapi.load` и `/usr/lib/apache2/modules/mod_auth_gssapi.so` [Ubuntu filelist].

### 10.2. Подготовка в домене (Windows)

[сторонний Microsoft — ключи `setspn -S` (добавить с проверкой дублей), `-Q` (поиск) и `ktpass /princ /mapuser /crypto /ptype /pass /out /in` сверены 20.10.2026 по справке Windows Server «Windows commands»; команды согласованы с `1c/05`, разд. 11.3, и `1c/08`, разд. 5.3]

1. Отдельная учётная запись службы для веб-сервера, например `svc-http-1c`; пароль не истекает, интерактивный вход запрещён; включено «Эта учётная запись поддерживает 256-битное шифрование Kerberos AES». К одной учётной записи — один экземпляр службы: для `HTTP/…` своя учётка, не та, что у сервера 1С (`usr1cv8/…`) [практика; `1c/08`, разд. 5.3].
2. SPN — для **каждого** имени, по которому браузеры обращаются к сайту (полное имя в нижнем регистре; короткое имя — по желанию):

```bat
setspn -S HTTP/srv-1c-app.example.local EXAMPLE\svc-http-1c
setspn -S HTTP/1c.example.local EXAMPLE\svc-http-1c
setspn -Q HTTP/srv-1c-app.example.local
```

3. Keytab:

```bat
ktpass /princ HTTP/srv-1c-app.example.local@EXAMPLE.LOCAL /mapuser EXAMPLE\svc-http-1c ^
       /crypto AES256-SHA1 /ptype KRB5_NT_PRINCIPAL /pass * /out http-1c.keytab
```

`ktpass` задаёт учётной записи пароль из `/pass` и (по умолчанию, ключ `+setupn`) UPN, равный принципалу [сторонний, справка ktpass; подтверждено 20.10.2026]: после повторного запуска старый keytab перестаёт работать (номер версии ключа kvno растёт) [практика]. Если нужны несколько имён в одном keytab — добавляйте принципалы, указав старый файл в `/in` (по справке — keytab, который ktpass читает); что `/out` сохранит и прежние записи — ⚠ не проверено, сверяйте `klist -k`.

4. Для аутентификации ОС в 1С через веб-сервер — флажок делегирования у учётной записи `svc-http-1c` («Доверять этой учётной записи делегирование…» — полное или ограниченное на службу сервера 1С) [ИТС-адм разд. 2.8.1.2; `1c/08`, разд. 5.7].
5. **DNS**: A-запись (не CNAME) для имени сайта. Chrome и Edge по умолчанию строят SPN из канонического имени (разыменовывают CNAME; выключается политикой `DisableAuthNegotiateCnameLookup`) — CNAME приводит к запросу билета на SPN другого имени [сторонний, определение политики в исходниках Chromium; подтверждено 20.10.2026]. Обратная зона — желательна.

### 10.3. Настройка на Ubuntu

```bash
sudo apt install -y libapache2-mod-auth-gssapi krb5-user
sudo a2enmod auth_gssapi
# /etc/krb5.conf — минимум (если сервер не введён в домен через sssd/realmd):
#   [libdefaults]
#       default_realm = EXAMPLE.LOCAL
#       dns_lookup_kdc = true
timedatectl status | grep -E 'synchronized|NTP'      # время синхронно с контроллерами (chrony/timesyncd)

# keytab: root владеет, www-data читает
sudo install -o root -g www-data -m 640 http-1c.keytab /etc/apache2/http-1c.keytab
sudo klist -k -t -e /etc/apache2/http-1c.keytab      # принципалы, kvno, aes256-cts-hmac-sha1-96
sudo -u www-data test -r /etc/apache2/http-1c.keytab && echo "www-data читает keytab"
```

- README модуля: «Apache должен иметь доступ на чтение к keytab» — проверка делается в рабочем процессе, работающем от `www-data` [сторонний]. Права `root:www-data 640` (как в `1c/08`, разд. 5.7) строже, чем `www-data:www-data 600` в `1c/05`, разд. 11.3: `www-data` не сможет ни изменить, ни удалить файл [практика].
- Расхождение часов больше допуска Kerberos (по умолчанию 300 с — параметр `clockskew` в `krb5.conf` [сторонний, документация MIT krb5; подтверждено 20.10.2026]) ломает проверку билетов [практика; ИТС-мет 2799, 2015].
- Проверка ключа с доменной машины или с сервера под пользователем домена: `kinit ivanov@EXAMPLE.LOCAL && kvno HTTP/srv-1c-app.example.local@EXAMPLE.LOCAL` — номер kvno должен совпасть с номером в `klist -k` [практика ⚠]. `kinit -k -t keytab HTTP/…` сработает, только если UPN учётки совпадает с принципалом ⚠ (практика; что `ktpass` по умолчанию так и задаёт UPN — по его справке, см. выше).

### 10.4. Конфигурация Apache

```apache
# Заголовок SPNEGO бывает до 12392 байт (документация LimitRequestFieldSize) — поднимать ГЛОБАЛЬНО
# (в не-первом name-based хосте директива не действует)
LimitRequestFieldSize 32768

<VirtualHost *:443>
    ServerName srv-1c-app.example.local
    # … SSLEngine on, сертификаты …

    <Location "/intranet">
        AuthType GSSAPI
        AuthName "EXAMPLE SSO"
        GssapiCredStore keytab:/etc/apache2/http-1c.keytab
        GssapiAllowedMech krb5
        GssapiSSLonly On
        GssapiNegotiateOnce On
        GssapiLocalName On
        Require valid-user
    </Location>
</VirtualHost>
```

Директивы `mod_auth_gssapi` (по README) [сторонний]:

| Директива | Умолчание | Смысл |
|---|---|---|
| `AuthType GSSAPI` | — | включает модуль для секции |
| `GssapiCredStore keytab:путь` | — | keytab службы; также `client_keytab:путь`, `ccache:FILE:путь`; без расширения credential store — переменная `KRB5_KTNAME` в окружении Apache |
| `GssapiAllowedMech krb5\|iakerb\|ntlmssp` | все доступные | разрешённые механизмы |
| `GssapiSSLonly On` | `Off` | отказывать без TLS; в эксплуатации рекомендуется `On` |
| `GssapiNegotiateOnce On` | `Off` | не предлагать Negotiate повторно после неудачи — меньше «загадочных» окон входа |
| `GssapiBasicAuth On` | `Off` | дополнительно принимать Basic (пароль проверяется через Kerberos); `GssapiBasicTicketTimeout` — 300 с |
| `GssapiLocalName On` | `Off` | `REMOTE_USER` — локальное имя (по `auth_to_local` из `krb5.conf`), полный принципал — в `GSS_NAME` |
| `GssapiUseSessions On` | `Off` | сеанс в зашифрованной cookie (нужен `mod_session`) — без Negotiate на каждый запрос; постоянный ключ — `GssapiSessionKey` |
| `GssapiDelegCcacheDir каталог` | — | делегированные учётные данные клиента в файл; путь — в переменной запроса `KRB5CCNAME` (`GssapiDelegCcacheEnvVar`) |
| `GssapiUseS4U2Proxy On` | `Off` | ограниченное делегирование; требует `GssapiDelegCcacheDir` и `client_keytab:` |
| `GssapiAcceptorName HTTP@имя` | любое имя из keytab | принимать только для заданного имени |
| `GssapiPublishErrors On` | `Off` | ошибки в переменные `MAG_ERROR`, `MAG_ERROR_TEXT`, `GSS_ERROR_MAJ/MIN` |

Остальные (`GssapiDelegCcacheUnique`, `GssapiDelegCcachePerms`, `GssapiImpersonate`, `GssapiConnectionBound` — только для NTLMSSP, `GssapiNameAttributes`, `GssapiPublishMech`) — в README и в таблице `1c/05`, разд. 11.3.

Переменная окружения Apache `gssapi-no-negotiate` подавляет заголовки Negotiate, например `BrowserMatch Windows gssapi-no-negotiate` [сторонний].

### 10.5. Браузеры и клиенты

- **Windows (Edge/Chrome)**: Negotiate уходит только сайтам зоны «Местная интрасеть» или из списка политик `AuthServerAllowlist` (делегирование — `AuthNegotiateDelegateAllowlist`; без неё Chrome учётные данные не делегирует) [сторонний; имена политик сверены 20.10.2026 по определениям политик Chromium и справке политик Microsoft Edge]. **Firefox**: `network.negotiate-auth.trusted-uris` (и `…delegation-uris`; политика `Authentication`) [сторонний, mozilla/policy-templates; подтверждено 20.10.2026].
- **Linux**: билет через `kinit` или вход в домен (sssd); проверка — `curl --negotiate -u : -v https://srv-1c-app.example.local/intranet/` → 200 [практика].
- **Откат на NTLM** (README): Negotiate ведёт клиент — сначала Kerberos, потом NTLM; Chrome/Edge на Windows при неудаче Kerberos показывают окно ввода пароля, «похожее на Basic», даже если сервер NTLM не принимает. Для внешних клиентов README советует не предлагать Negotiate (фильтр по IP); ни Kerberos, ни NTLM не рассчитаны на интернет [сторонний].
- Вход **по IP** или по имени без SPN → билета нет → NTLM → окно входа [практика].

### 10.6. Разделение по сетям: внутри — SSO, снаружи — без Negotiate

```apache
<Location "/intranet">
    # Снаружи (не из 10.0.0.0/8) не предлагать Negotiate
    SetEnvIfExpr "! -R '10.0.0.0/8'" gssapi-no-negotiate
    AuthType GSSAPI
    AuthName "EXAMPLE SSO"
    GssapiCredStore keytab:/etc/apache2/http-1c.keytab
    GssapiSSLonly On
    GssapiBasicAuth On
    GssapiBasicAuthMech krb5
    Require valid-user
</Location>
```

Здесь внешние пользователи вводят доменные имя и пароль (Basic, проверка через Kerberos); `-R` в `ap_expr` — то же, что `%{REMOTE_ADDR} -ipmatch …` [Apache-док «Expressions»; схема — практика, на стенде не проверялась ⚠]. Если внешнего доступа быть не должно — проще `Require ip` + Kerberos.

### 10.7. Типовые проблемы Kerberos

| Симптом | Причина | Что делать |
|---|---|---|
| Окно ввода логина в Chrome/Edge вместо входа | сайт не в зоне «Интрасеть»; нет SPN; обращение по IP или CNAME; откат на NTLM | зона/политики (10.5); `setspn -Q`; входить по FQDN; A-запись |
| `400 Bad Request` «Size of a request header field exceeds server limit» у отдельных пользователей | большой билет (много групп) > `LimitRequestFieldSize` 8190 | `LimitRequestFieldSize 32768` в контексте сервера; то же на прокси перед Apache [Apache-док] |
| В журнале — ошибка проверки ключа («Key version number for principal in key table is incorrect»; тексты — по таблице ошибок MIT krb5 `krb5_err.et`) | keytab устарел (пароль учётки сменили, `ktpass` запускали повторно) | перевыпустить keytab, сравнить `klist -k` и `kvno` |
| «Clock skew too great» (MIT krb5 `krb5_err.et`) | расхождение времени | chrony/timesyncd, источник — контроллеры домена |
| 401 при правильной настройке, `curl --negotiate` работает | браузер не отдаёт билет (политики) | 10.5 |
| 403 после успешного входа | `Require` не совпадает с форматом имени (`user@REALM` против `user`) | `GssapiLocalName On`; проверить `REMOTE_USER` в журнале (`%u` в `LogFormat`) |
| Kerberos работает, но 1С не пускает | нет пользователя ОС `\\EXAMPLE\user` в базе, нет делегирования, сервер 1С без своего keytab | `1c/08`, разд. 5; `1c/05`, разд. 11.3 |

Отладка: `LogLevel auth_gssapi:debug` (модуль объявлен как `auth_gssapi_module` с `APLOG_USE_MODULE(auth_gssapi)`, а `LogLevel` принимает идентификатор без `_module` [код `src/mod_auth_gssapi.c`; Apache-док `LogLevel`; уточнено 20.10.2026]), `GssapiPublishErrors On` и вывод `%{MAG_ERROR_TEXT}e` в журнал — README называет `MAG_ERROR`/`MAG_ERROR_TEXT` переменными окружения запроса, а `%{…}e` в `LogFormat` их и выводит [сторонний; Apache-док `mod_log_config`].

## 11. Клиентские сертификаты (взаимный TLS)

Полезно для сервер-серверных интеграций (HTTP-сервисы и OData 1С, вебхуки GlitchTip/NetBox → мост → Redmine), когда IP-фильтра недостаточно [практика]:

```apache
<VirtualHost *:443>
    ServerName api-1c.example.local
    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/api-1c.fullchain.pem
    SSLCertificateKeyFile /etc/ssl/private/api-1c.key
    # кому доверяем как выпускающим клиентские сертификаты
    SSLCACertificateFile  /etc/apache2/client-ca/integration-ca.pem
    SSLVerifyClient require
    SSLVerifyDepth  2
    <Location "/demo/hs">
        Require expr "%{SSL_CLIENT_S_DN_CN} in {'erp-exchange', 'bridge-glitchtip'}"
    </Location>
</VirtualHost>
```

- `SSLVerifyClient none|optional|require|optional_no_ca` (умолчание `none`), `SSLVerifyDepth` (умолчание 1) [Apache-док; Debian `default-ssl.conf`].
- Требование клиентского сертификата в `<Location>`/`<Directory>` вызывает повторное согласование; с TLS 1.3 оно заменено «рукопожатием после установки» (post-handshake auth), которое поддерживают не все клиенты ⚠ — надёжнее отдельный хост с `SSLVerifyClient require` целиком [Apache-док; практика].
- Если на одном IP:порту есть хосты с **разными** списками доверенных УЦ для клиентов, обязательно обновление 2025 г. (CVE-2025-23048 — обход через возобновление сессии TLS 1.3) и `SSLVHostSNIPolicy` не ниже `authonly` (по умолчанию `secure`) [Apache-док].
- В 2.4.69 закрыта CVE-2026-59797: функции работы с файлами в выражениях `SSLRequire` были доступны из `.htaccess` — ещё один довод за `AllowOverride None` и `Require expr` вместо устаревшего `SSLRequire` [Apache-док].
- Тонкий клиент 1С умеет предъявлять клиентский сертификат (`/HttpsCert`, настройка в свойствах базы) — `1c/05`, разд. 8.3; `1c/08`, разд. 7.2. Но при TLS 1.3 платформа поддерживает клиентские сертификаты только на алгоритмах ГОСТ [ИТС-адм разд. 8.9.2]: для клиентских RSA/ECDSA-сертификатов 1С ограничьте такой хост версией TLS 1.2 (`SSLProtocol -all +TLSv1.2` в его `<VirtualHost>`, с SNI — 2.4.42+) — так же советует `1c/05`, разд. 8.

## 12. Сочетание с аутентификацией 1С (ссылки, без дублирования)

Публикация 1С и её аутентификация — в `1c/05` (разд. 11) и `1c/08` (разд. 5–6). Здесь — только где общие настройки Apache важны для 1С.

| Задача | Что настраивается в Apache | Что настраивается в 1С | Где подробно |
|---|---|---|---|
| Пользователи 1С (по умолчанию) | только HTTPS и, по желанию, `Require ip` | пользователи с паролем 1С | `1c/05`, 11.2 |
| Basic веб-сервера | `AuthType Basic` + `AuthUserFile`/LDAP | пользователь 1С с тем же именем и паролем | `1c/05`, 11.1, 11.4; раздел 8 здесь |
| Аутентификация ОС (Kerberos) | официально `mod_auth_kerb` (`KrbSaveCredentials on`), на 24.04+ — `mod_auth_gssapi` с `GssapiDelegCcacheDir` (практика) | у пользователя — «Аутентификация ОС» `\\EXAMPLE\user`; у сервера 1С — свой keytab `usr1cv8/…` | `1c/05`, 11.3; `1c/08`, 5.1–5.9; раздел 10 здесь |
| OpenID Connect | ничего (кроме HTTPS) | провайдер OIDC в `default.vrd`/настройках | `1c/08`, 6.3 |
| Сервисы для интеграций | ограничение по IP / клиентскому сертификату; без SSO | Basic 1С (заголовок `Authorization`) | раздел 7.5, 11 здесь; `1c/05`, 11.4 |

Важные для 1С связки:

1. **Kerberos + делегирование.** Официальный рецепт ставит у учётной записи `HTTP/…` доверие для делегирования и `KrbSaveCredentials on` — модулю 1С нужны **делегированные** учётные данные, одного `REMOTE_USER` мало [ИТС-адм разд. 2.8.1.2]. Аналог в `mod_auth_gssapi` — `GssapiDelegCcacheDir`; подхватывает ли его `wsap24` — ⚠ не подтверждено (`1c/05`, 11.3). Каталог кешей — в `/run` (через `systemd-tmpfiles`), владелец `www-data`, права `700` [практика].
2. **Интеграции** (OData, HTTP-сервисы) Negotiate не умеют — выносите их на путь без `AuthType GSSAPI`; Basic Apache и Kerberos на одном пути не сочетайте — заголовок `Authorization` один [практика].
3. **Большие билеты** — `LimitRequestFieldSize` (13.4); при nginx перед Apache — и его буферы заголовков (`apache/03-…`) [практика].
4. **На Windows** аутентификация ОС через Apache не поддерживается, `-osauth` — только IIS [ИТС-адм прил. 4.14]. **HTTPS** для Basic и SSO обязателен, для публикаций в интернет ИТС его «настоятельно рекомендует» [ИТС-адм разд. 8.2].

## 13. Медленные атаки и ограничения размеров запроса

### 13.1. `mod_reqtimeout`

Включён в Ubuntu по умолчанию [Debian]. Ограничивает время **чтения запроса**: рукопожатие TLS, заголовки, тело; не уложился — 408 и закрытие соединения, запись в журнал на уровне `info` (`LogLevel reqtimeout:info`) [Apache-док].

| Этап | Умолчание Apache | `reqtimeout.conf` Ubuntu | Смысл |
|---|---|---|---|
| `handshake` (с 2.4.39) | `0` (выключен) | не задан | время на TLS-рукопожатие |
| `header` | `20-40,MinRate=500` | `header=20-40,minrate=500` | 20 с на начало, дальше ≥ 500 байт/с, но не больше 40 с |
| `body` | `20,MinRate=500` | `body=10,minrate=500` | 10 с до первого байта тела, дальше ≥ 500 байт/с без верхней границы |

Формы: `stage=timeout`, `stage=timeout,MinRate=rate`, `stage=timeout-maxtimeout,MinRate=rate`; `handshake=0 header=0 body=0` — выключить для хоста. При `AcceptFilter` (обычно на Linux) отсчёт `handshake`/`header` начинается после первого байта. Для TLS-хостов не ставьте слишком малые значения — браузер может ждать список отзыва (CRL) [Apache-док].

- **Для 1С**: модуль не ограничивает время **выполнения** запроса (отчёт, обмен) — это `Timeout`/`ProxyTimeout` (`apache/03-…`). Мешать он может только очень медленной загрузке больших файлов (< 500 байт/с) — тогда понизьте `MinRate` для хоста публикации, а не выключайте модуль [практика].
- Защита рукопожатия: `RequestReadTimeout handshake=5-10,MinRate=500 header=20-40,MinRate=500 body=10,MinRate=500` ⚠ (значения — практика).
- «Security Tips» советуют на сайтах под DoS снижать `TimeOut` (Ubuntu ставит 300, умолчание Apache — 60) и `KeepAliveTimeout`, настраивать `MaxRequestWorkers` и `LimitRequest*` [Apache-док; Debian]. Низкий `TimeOut` противоречит долгим операциям 1С — баланс в `apache/03-…` и `1c/05`, разд. 12. От распределённых атак Apache не защищает — нужны брандмауэр и провайдер (`linux/08`).

### 13.2. Сводка лимитов ядра

| Директива | Умолчание | Контекст | Что при превышении | Источник |
|---|---|---|---|---|
| `LimitRequestBody` | 1073741824 (1 ГиБ); 0 в 2.4.53 и ранее | сервер, хост, каталог, `.htaccess` | 413 Request Entity Too Large | [Apache-док] |
| `LimitRequestFieldSize` | 8190 | сервер, хост (берётся из первого хоста для IP:порта) | 400 с текстом о размере заголовка | [Apache-док] |
| `LimitRequestLine` | 8190 | сервер, хост (то же) | 414 Request-URI Too Long, в журнале `AH00565` (уровень `info`) | [Apache-док; код `server/protocol.c`] |
| `LimitRequestFields` | 100 | сервер, хост (то же) | 400 | [Apache-док] |
| `LimitXMLRequestBody` | 1000000 | сервер, хост, каталог, `.htaccess` | 413, в журнале `AH00539 XML request body is larger than the configured limit` | [Apache-док; код `server/util_xml.c`] |

### 13.3. `LimitRequestBody` и загрузка файлов в 1С

- С 2.4.54 умолчание — 1 ГиБ (изменено в том же выпуске, что исправил CVE-2022-29404 — «нет предела по умолчанию» для `r:parsebody` в `mod_lua`; в CHANGES_2.4 — отдельной записью ядра); до этого было 0 — «без ограничения» [Apache-док].
- Ubuntu 24.04 (2.4.58) и 26.04 (2.4.66) — 1 ГиБ. **Ubuntu 22.04 (2.4.52)**: заплатка CVE-2022-29404 в журнале Ubuntu (`2.4.52-1ubuntu4.1`) описана как правка только `modules/lua/lua_request.c`, а других упоминаний `LimitRequestBody` в журнале `2.4.52-1ubuntu4.25` нет; в CHANGES_2.4 смена умолчания — отдельная запись ядра 2.4.54, с CVE не связанная. Вероятнее всего, в 22.04 действует 0 (без ограничения) — ⚠ текст заплатки не читался [Ubuntu; вывод — практика].
- Где бьёт по 1С: загрузка файлов в веб-клиенте, `ПоместитьФайл`, POST в HTTP- и веб-сервисы, обмены пакетами, мобильные клиенты [практика; ср. `1c-windows/03`, разд. 8.1 для IIS].
- Не полагайтесь на умолчание — задайте явно в секции публикации, а на остальных путях оставьте умеренный предел:

```apache
# общий предел для хоста (защита от «бесконечных» POST): 100 МиБ
LimitRequestBody 104857600
<Location "/demo">
    # 4 ГиБ для публикации 1С (подберите под реальные файлы)
    LimitRequestBody 4294967296
</Location>
```

- Комментарий в конфигурации Apache — только отдельной строкой: `#` после директивы будет принят за её аргумент [практика].
- Значение 0 — «без ограничения» [Apache-док]. Верхний предел в документации не указан; по коду (`set_limit_req_body` в `server/core.c`) принимается любое неотрицательное число типа `apr_off_t` — на 64-битной Ubuntu это 64 бита, так что 4 ГиБ допустимы [уточнено 20.10.2026].
- При nginx перед Apache действует и его `client_max_body_size` (умолчание `1m` — подтверждено 20.10.2026 по nginx.org [сторонний]) — `apache/03-…`, `1c/05`.
- Для `mod_proxy_http` специальное значение 0 соблюдается с 2.4.4 [Apache-док CHANGES].
- `LimitXMLRequestBody` проверяется только в функции разбора XML ядра `ap_xml_parse_input()` (`server/util_xml.c`), которую вызывают модули Apache, разбирающие XML сами (например, `mod_dav`) [код; уточнено 20.10.2026]; на SOAP-запросы, которые читает модуль 1С, он, по-видимому, не влияет — ⚠ поведение `wsap24` не проверялось.

### 13.4. Длинные URL (OData) и большие заголовки (Kerberos)

- **`LimitRequestLine 8190`** — длина строки запроса (метод + URI + версия). Запросы OData с длинным `$filter`/`$select` и GET-параметры HTTP-сервисов упираются в него; документация советует не менять «в нормальных условиях», но для OData поднимать приходится [Apache-док; практика].
- **`LimitRequestFieldSize 8190`** — размер одного заголовка; документация прямо пишет, что заголовки SPNEGO бывают до 12 392 байт [Apache-док].
- Обе директивы (и `LimitRequestFields`) при name-based хостинге берутся из **умолчательного (первого) хоста** для IP:порта — задавайте в контексте сервера, например в отдельном файле `conf-available` [Apache-док].
- В 2.4.69 закрыта CVE-2026-63292: переполнение стека в `mod_vhost_alias` при `Host` длиннее 8192 байт, **если `LimitRequestFieldSize` поднят выше умолчания** и `VirtualDocumentRoot` использует имя хоста — поднимая лимит, держите систему обновлённой и не используйте `mod_vhost_alias` без нужды [Apache-док].

```apache
# /etc/apache2/conf-available/request-limits.conf   (sudo a2enconf request-limits)
LimitRequestLine      16384
LimitRequestFieldSize 32768
LimitRequestFields    100
```

```bash
sudo a2enconf request-limits && sudo apache2ctl configtest && sudo systemctl reload apache2
# проверка: длинный URL
curl -s -o /dev/null -w '%{http_code}\n' "https://$H/demo/odata/standard.odata/Catalog_X?\$filter=$(head -c 12000 /dev/zero | tr '\0' 'a')"
```

## 14. Безопасность обратного прокси

Обратный прокси подробно (балансировка, таймауты, WebSocket, заголовки для приложений) — `apache/03-…`. Здесь — только то, что касается безопасности.

### 14.1. Никакого открытого прокси

- `ProxyRequests On|Off`, умолчание **`Off`**; `Off` **не мешает** `ProxyPass` — для обратного прокси `On` не нужен [Apache-док].
- Открытый прямой прокси позволяет любому ходить через ваш сервер на произвольные адреса под вашим IP — «опасно и для вашей сети, и для интернета» [Apache-док].
- В Ubuntu `mods-available/proxy.conf` содержит `ProxyRequests On` и блок `<Proxy *>` только в комментарии [Debian]. `mod_proxy_connect` (`CONNECT`-туннели) не включён; в Debian с `2.4.59-1` (апрель 2024, Closes: #1054564) `AllowCONNECT` по умолчанию выключен — из выпусков Ubuntu это только 26.04, в 22.04/24.04 при включённом модуле действует умолчание Apache `AllowCONNECT 443 563` [Debian; Apache-док].
- Проверка (с внешней машины): `curl -s -o /dev/null -w '%{http_code}\n' -x http://srv-1c-app.example.local:80 http://example.com/` — ответ не должен быть страницей example.com (ожидается 404/400/403 от вашего сервера) [практика].
- Если прямой прокси всё же нужен — только с `<Proxy "*"> Require ip …</Proxy>`; учтите, что для `CONNECT` фильтр работает только по хосту и порту, путь не виден [Apache-док].

### 14.2. Заголовки к бэкенду

- В режиме обратного прокси `mod_proxy_http` сам добавляет `X-Forwarded-For` (адрес клиента), `X-Forwarded-Host` (исходный `Host`) и `X-Forwarded-Server` (имя прокси); при цепочке прокси значения накапливаются через запятую [Apache-док]. `ProxyAddHeaders On` — умолчание (с 2.3.10) [Apache-док].
- **`X-Forwarded-Proto` и `X-Forwarded-Port` Apache сам не добавляет** [Apache-док — в списке их нет]. Для 1С за обратным прокси ИТС требует, чтобы прокси формировал `X-Forwarded-Port`, `X-Forwarded-Host`, `X-Forwarded-Proto` (восстановление исходного запроса) и `X-Forwarded-For` (адрес клиента) [ИТС-адм разд. 8.10.3]. Для Redmine/NetBox/GlitchTip `X-Forwarded-Proto` нужен, чтобы приложение строило ссылки `https://` и не уходило в цикл перенаправлений [практика].

```apache
# пример: Apache на srv-itsm принимает HTTPS и проксирует на Redmine (Puma) на 127.0.0.1:3000
<VirtualHost *:443>
    ServerName redmine.example.local
    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/redmine.fullchain.pem
    SSLCertificateKeyFile /etc/ssl/private/redmine.key

    ProxyRequests Off
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
    # не доверять заголовкам «удалённого пользователя» от клиента
    RequestHeader unset X-Remote-User
    ProxyPass        "/" "http://127.0.0.1:3000/"
    ProxyPassReverse "/" "http://127.0.0.1:3000/"
</VirtualHost>
```

- `ProxyPreserveHost On` — передавать бэкенду исходный `Host` (умолчание `Off`); `ProxyVia Off` — умолчание [Apache-док].
- `RequestHeader` в обычном («позднем») режиме срабатывает до передачи запроса бэкенду; ключ `early` документация считает отладочным [Apache-док].
- Если приложение доверяет «пользователю из заголовка прокси» (NetBox `REMOTE_AUTH_HEADER`, `netbox/03-…`), этот заголовок ставит **только** Apache, а входящий от клиента удаляется — иначе любой назовётся администратором [практика].
- Служебный заголовок бэкенда за `mod_proxy_http` убирает `Header unset X-Powered-By` (таблица `onsuccess`; вариант `always` его не видит — 6.3), за `mod_proxy_fcgi` — `Header always unset X-Powered-By`; `ProxyErrorOverride On` (коды — с 2.4.47) для API не включайте [Apache-док; практика].

### 14.3. HTTPS к бэкенду

Если бэкенд — по HTTPS (другая ВМ, недоверенный сегмент):

```apache
SSLProxyEngine on
SSLProxyVerify require
SSLProxyCheckPeerName on
SSLProxyCACertificateFile /usr/local/share/ca-certificates/corp-root-ca.crt
ProxyPass "/" "https://srv-obs.example.local:8000/"
```

- `SSLProxyEngine` (умолчание `off`), `SSLProxyVerify` (**умолчание `none`** — сертификат бэкенда не проверяется!), `SSLProxyCheckPeerName` (умолчание `on`, с 2.4.5), `SSLProxyCheckPeerExpire` (умолчание `on`), `SSLProxyProtocol` (умолчание `all -SSLv3`); с 2.4.30 эти директивы допустимы и в секции `<Proxy>` [Apache-док].
- Без `SSLProxyVerify require` шифрование к бэкенду есть, а защиты от подмены бэкенда нет [Apache-док; практика].
- Умолчание `SSLProxyCipherSuite` в документации выглядит архаично (`ALL:!ADH:RC4+RSA:+HIGH:+MEDIUM:+LOW:+EXP`), но в коде оно не применяется: если директива не задана, `mod_ssl` берёт список OpenSSL по умолчанию (`DEFAULT`) с добавкой `:!aNULL:!eNULL:!EXP`, как и для сервера, а дальше его ограничивает уровень безопасности OpenSSL Ubuntu [уточнено 20.10.2026 по коду `ssl_engine_init.c` 2.4.58, `ssl_init_ctx_cipher_suite`]; при особых требованиях задайте явно [практика].

### 14.4. Адрес клиента и доверие к `X-Forwarded-For`

Если перед Apache стоит другой прокси (nginx, балансировщик), Apache видит его адрес. `mod_remoteip` с явным списком доверенных прокси (`RemoteIPInternalProxy`/`RemoteIPTrustedProxy`) подставит адрес клиента из `X-Forwarded-For`; без списка — любой клиент подделает адрес и обойдёт `Require ip` [Apache-док; практика]. Подробно — `apache/03-…`.

### 14.5. Уязвимости прокси

Прокси-модули и подстановки URL — постоянный источник CVE: SSRF через `mod_proxy` (CVE-2021-40438), SSRF на Windows по UNC-путям с утечкой NTLM (CVE-2024-38472; CVE-2024-40898 — `mod_rewrite` в контексте сервера/хоста; CVE-2024-43394 — `mod_rewrite` и выражения), подмена ответов через `mod_proxy_uwsgi` (CVE-2026-63718), разбор ответов `mod_proxy_html`/`mod_xml2enc` (CVE-2026-56449, CVE-2026-63686), FTP-прокси (CVE-2026-63045) [Apache-док]. Не включайте прокси-модули «про запас» (`proxy_ftp`, `proxy_uwsgi`, `proxy_html`, `xml2enc`, `proxy_connect`), держите пакеты обновлёнными [практика].

## 15. Обновления безопасности

### 15.1. Где смотреть

- Страница уязвимостей ветки 2.4: `https://httpd.apache.org/security/vulnerabilities_24.html` — для каждой CVE: уровень (critical/important/moderate/low), затронутые версии, версия исправления [Apache-док].
- Журнал изменений: `https://downloads.apache.org/httpd/CHANGES_2.4` [Apache-док].
- Ubuntu: уведомления USN и журнал пакета; исправления переносятся заплатками без смены номера 2.4.x [Ubuntu].

```bash
apt changelog apache2 | head -40                                   # последние записи журнала пакета
apt changelog apache2 | grep -oE 'CVE-20[0-9]{2}-[0-9]+' | sort -u | tail -30
zgrep -c CVE /usr/share/doc/apache2/changelog.Debian.gz            # то же офлайн
apt list --upgradable 2>/dev/null | grep -E 'apache2|libapache2'
sudo unattended-upgrade --dry-run -d 2>/dev/null | grep -i apache  # попадёт ли в автообновление
```

Автоматическая установка обновлений безопасности (`unattended-upgrades`) — `linux/04-pakety-apt.md`. После обновления пакета служба перезапускается полностью (`restart`, а не `graceful`): `debian/rules` вызывает `dh_installsystemd` без `--no-restart-after-upgrade`, а при `debhelper-compat (= 13)` это поведение по умолчанию [Debian, метка `debian/2.4.58-1`; уточнено 20.10.2026] — обновляйте в окно обслуживания и затем проверьте `systemctl status apache2` и журнал ошибок [практика].

### 15.2. Что вышло за последний год (по странице уязвимостей)

- **2.4.64** (10.07.2025): удалён `SSLEngine optional` (CVE-2025-49812); обход контроля доступа при возобновлении сессии TLS 1.3 (CVE-2025-23048); разделение HTTP-ответа (CVE-2024-42516); HTTP/2 DoS (CVE-2025-53020). **2.4.65** (23.07.2025): `RewriteCond expr` всегда «истина» (CVE-2025-54090).
- **2.4.66** (04.12.2025): `SSLVHostSNIPolicy`; `mod_md` (CVE-2025-55753); утечка NTLM на Windows (CVE-2025-59775).
- **2.4.67** (04.05.2026): **important** — HTTP/2, двойное освобождение и возможное выполнение кода (CVE-2026-23918, только 2.4.66); `mod_rewrite`, `mod_md`, `mod_auth_digest`, `mod_authn_socache`, `mod_proxy_ajp`.
- **2.4.68** (08.06.2026): `mod_ldap` (CVE-2026-29167), OCSP в `mod_ssl` (CVE-2026-44185), `mod_http2` (CVE-2026-48913, -49975), `mod_proxy_html`, `mod_xml2enc`.
- **2.4.69** (01.10.2026): ~20 CVE — `SSLRequire` и файловые функции из `.htaccess` (CVE-2026-59797), `mod_http2` (CVE-2026-57941), `mod_auth_digest` (CVE-2026-73636, -73637, -48005), `mod_vhost_alias` (CVE-2026-63292), `mod_session` (CVE-2026-47360), `mod_dav_fs`, Windows-пути 8.3 (CVE-2026-59685); `MDServerStatus` теперь выключен по умолчанию.

Источник — `vulnerabilities_24.html` и `CHANGES_2.4` [Apache-док]. Перенос в Ubuntu (22.04 / 24.04 / 26.04): исправления 2.4.68 (CVE-2026-29167, -44185) — `2.4.52-1ubuntu4.23` / `2.4.58-1ubuntu8.15` / `2.4.66-2ubuntu2.4` (06.07.2026); исправления 2.4.69 (CVE-2026-57941, -59797) — `4.24` / `8.16` / `2ubuntu2.5` (05.10.2026), CVE-2026-63292 — `4.25` / `8.17` / `2ubuntu2.6` (08.10.2026); CVE-2026-23918 — во всех трёх: `4.20` / `8.12` / `2ubuntu2.1` (05.05.2026) [Ubuntu, журналы пакета; уточнено 20.10.2026]. Перед утверждением «уязвимость закрыта» на конкретном сервере проверяйте `apt changelog apache2 | grep <CVE>` [практика].

### 15.3. Что уменьшает поверхность атаки

- Включены только нужные модули (`apache2ctl -M`); не держать `mod_dav*`, `mod_lua`, `mod_userdir`, `mod_cgi`, `mod_proxy_*`, `mod_http2` «на всякий случай» — львиная доля CVE последних лет как раз в них [Apache-док; практика].
- `AllowOverride None` — `.htaccess` не читается (CVE-2026-59797 срабатывает через `.htaccess`) [Apache-док; практика].
- `Options -Indexes`, отключённый `000-default`, «заглушка» на 443 [Debian; практика].
- Рабочие процессы — от `www-data` (не `root`), `DocumentRoot` и конфигурация — без права записи для `www-data` [Ubuntu docs; Apache-док «Security Tips»].
- Регулярная проверка снаружи: `nmap --script ssl-enum-ciphers`, testssl.sh, для публичных — SSL Labs [сторонний].
- Журналы ошибок и доступа — в Loki (`observability/03-loki-i-grafana.md`) с оповещениями на всплески 401/403/408/413 [практика].

## 16. Apache на Windows — кратко

Подробно — `apache/04-tipovye-problemy-i-apache-na-windows.md` и `1c-windows/03-veb-publikaciya-iis.md`, разд. 13.

- Проект Apache двоичных сборок для Windows не выпускает (только исходный код; среди сторонних поставщиков документация называет Apache Lounge) [Apache-док `platform/windows`]; сборка Apache Lounge содержит `mod_ssl` и свежий OpenSSL [сторонний, страница загрузки Apache Lounge; подтверждено 20.10.2026; `1c-windows/03`]. Скачивать только с официального сайта сборки, сверять контрольные суммы.
- HTTPS по методичке 1С: сертификат и ключ OpenSSL, в `conf\extra\httpd-ahssl.conf` (имя файла — особенность использованной сборки) в `VirtualHost _default_:443` — `SSLCertificateFile "${SRVROOT}/certs/<сервер>.crt"` и `SSLCertificateKeyFile "${SRVROOT}/certs/<сервер>.key"` [ИТС-мет 5978, 2020]. Права на ключ — NTFS: только `SYSTEM`/администраторы и учётная запись службы [практика].
- Аутентификация ОС для 1С через Apache на Windows не работает (только IIS) [ИТС-адм прил. 4.14; `1c-windows/03`].
- Windows-специфичные CVE: SSRF по UNC-путям (CVE-2024-38472, CVE-2024-43394), утечка NTLM (CVE-2025-59775), запись за границу при путях 8.3 (CVE-2026-59685) — сборки обновлять так же регулярно, как пакеты Ubuntu [Apache-док].
- `htpasswd -p` (открытый текст) Apache принимает только на Windows — не используйте; пароли > 255 символов обрезаются [Apache-док].

## 17. Сводные шаблоны (Ubuntu 24.04)

### 17.1. Глобальные настройки безопасности

```apache
# /etc/apache2/conf-available/zz-hardening.conf   (sudo a2enconf zz-hardening)
# TLS — профиль intermediate (TLSRef 6.0)
SSLProtocol             -all +TLSv1.2 +TLSv1.3
SSLCipherSuite          ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305
SSLHonorCipherOrder     off
SSLSessionTickets       off

# Лимиты (действуют глобально; в не-первых хостах LimitRequestLine/FieldSize игнорируются)
LimitRequestLine        16384
LimitRequestFieldSize   32768

# Защита чтения запроса (дополняет reqtimeout.conf)
<IfModule reqtimeout_module>
    RequestReadTimeout handshake=5-10,MinRate=500 header=20-40,MinRate=500 body=10,MinRate=500
</IfModule>

# Листинги каталогов — нигде
<Directory /var/www/>
    Options -Indexes
</Directory>
```

`ServerTokens Prod`, `ServerSignature Off` — в `security.conf` (6.1); затем `configtest`, `reload` и проверки 4.5. Файлы `conf-enabled` загружаются по алфавиту — `zz-…` последним. `Options -Indexes` здесь отменит `Indexes` из `apache2.conf`: секции `<Directory>` с одинаковым путём применяются в порядке появления в конфигурации (включённые файлы — на месте `Include`, а `IncludeOptional conf-enabled` стоит в `apache2.conf` после `<Directory /var/www/>`), а `Options`, где все значения с `+`/`-`, сливается с действующими, `FollowSymLinks` останется [Apache-док `sections`, `core` (`Options`); Debian; уточнено 20.10.2026; слияние секций — `apache/01-…`].

### 17.2. Хост публикации 1С на `srv-1c-app`

```apache
# /etc/apache2/sites-available/000-catchall.conf — первый для *:80 и *:443: всё неизвестное — 403
<VirtualHost *:80>
    ServerName catchall.invalid
    <Location "/">
        Require all denied
    </Location>
</VirtualHost>
<VirtualHost *:443>
    ServerName catchall.invalid
    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
    SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
    <Location "/">
        Require all denied
    </Location>
</VirtualHost>
```

```apache
# /etc/apache2/sites-available/1c.conf
<VirtualHost *:80>
    ServerName srv-1c-app.example.local
    ServerAlias 1c.example.local
    Redirect permanent / https://srv-1c-app.example.local/
</VirtualHost>

<VirtualHost *:443>
    ServerName srv-1c-app.example.local
    ServerAlias 1c.example.local
    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/srv-1c-app.fullchain.pem
    SSLCertificateKeyFile /etc/ssl/private/srv-1c-app.key

    Header always set Strict-Transport-Security "max-age=63072000"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Content-Security-Policy "frame-ancestors 'self'"

    LimitRequestBody 104857600
    <Location "/demo">
        LimitRequestBody 4294967296
    </Location>
    <Location "/demo/odata">
        Require ip 10.10.30.11 10.10.30.12
    </Location>

    ErrorLog  ${APACHE_LOG_DIR}/1c-ssl-error.log
    CustomLog ${APACHE_LOG_DIR}/1c-ssl-access.log combined
    # Сам блок публикации (SetHandler 1c-application, ManagedApplicationDescriptor) webinst
    # пишет в apache2.conf — он глобальный и действует и здесь (1c/05, разд. 8.1).
</VirtualHost>
```

```bash
sudo a2enmod ssl headers
sudo a2ensite 000-catchall 1c
sudo a2dissite 000-default
sudo apache2ctl configtest && sudo systemctl reload apache2
sudo apache2ctl -S                                  # *:443 default server — catchall.invalid
curl -sI http://srv-1c-app.example.local/demo/   # 301 → https://
curl -sI https://srv-1c-app.example.local/demo/ru_RU/ | grep -iE '^(HTTP|strict|x-content|content-security)'
curl -skI https://10.10.10.5/demo/                  # по IP — 403 (заглушка)
```

Если файл называется `000-catchall.conf`, а исходный `000-default.conf` отключён, «заглушка» окажется первой по алфавиту [Debian; практика]. Блок публикации 1С `webinst` записывает в `apache2.conf` в контексте сервера — он действует во всех хостах, включая заглушку, но заглушка закрывает `/` целиком через `<Location>`: секции `<Location>` применяются после `<Directory>`, а их авторизация по умолчанию (`AuthMerging Off`) заменяет авторизацию из `<Directory>` [Apache-док `sections`, `mod_authz_core`; уточнено 20.10.2026]. Проверка на стенде: `curl -skI https://<IP>/demo/` должен дать 403.

Сервис на `srv-itsm` за Apache собирается из 14.2 (прокси и заголовки) и 9.4 (вход по группе AD на служебном пути, например `<Location "/admin/">` с `<RequireAll> Require ip …; Require ldap-group …</RequireAll>`). Basic на путях API (`/api/`) не ставьте: API NetBox/Redmine/GlitchTip несут свой токен в `Authorization` [практика].

## Типичные ошибки (симптом → причина → решение)

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | Apache не стартует: ошибка о `SSLCertificateFile` (файл не найден или пуст) | опечатка в пути; ссылка на удалённый сертификат certbot | `sudo apache2ctl configtest`; `ls -l` путей; `sudo grep -R live/ /etc/apache2` |
| 2 | Не стартует: сертификат и ключ «не совпадают» | в паре чужой ключ (перевыпуск CSR) | сравнить хеши открытых ключей (3.1) |
| 3 | Не стартует с `AH02572 Failed to configure at least one certificate and key`; или при старте `AH01916 … You configured HTTP(80) on the standard HTTPS(443) port!`, а в браузере `ERR_SSL_PROTOCOL_ERROR` | хост с `SSLEngine on` без сертификата; хост на 443 без `SSLEngine on` (на 443 отвечает HTTP) | `apache2ctl -S`; добавить пути к сертификату или `SSLEngine on` (2.2) [код `ssl_engine_init.c`; практика] |
| 4 | `NET::ERR_CERT_COMMON_NAME_INVALID` | имени нет в SAN | перевыпустить с `subjectAltName` |
| 5 | Браузер доволен, а `curl`, тонкий клиент 1С, Java — «unable to get local issuer certificate» | нет промежуточных сертификатов (браузер достраивает сам) | `SSLCertificateFile` = fullchain |
| 6 | После обновления пакета в журнале `AH10510 'SSLEngine optional' is no longer supported` | TLS Upgrade удалён (CVE-2025-49812); такой хост работает как `SSLEngine off` | убрать `optional`; для HTTPS — отдельный хост `*:443` с `SSLEngine on` |
| 7 | После обновления — `421 Misdirected Request` | SNI и `Host` ведут в хосты с несовместимыми TLS-настройками (CVE-2025-23048) | передавать SNI с прокси; общий сертификат; осознанно `SSLVHostSNIPolicy authonly` |
| 8 | Старые клиенты не подключаются (особенно после перехода на 26.04) | нет TLS 1.0/1.1 (`ssl.conf` 26.04, `SECLEVEL=2`) | обновить клиентов, уровень безопасности не понижать |
| 9 | HTTP/2 не согласуется; или после `a2enmod http2` везде появился `h2c` | `prefork`; шифр из «чёрного списка» (`H2ModernTLSOnly`); `http2.conf` задаёт `Protocols h2 h2c http/1.1` глобально | `worker`/`event`; профиль intermediate; `Protocols` явно (5.4) |
| 10 | `AH02217 … Can't retrieve issuer certificate`; stapling «не работает» с LE | нет цепочки; у LE нет OCSP с 2025 г. | fullchain; для LE `SSLUseStapling` не включать |
| 11 | certbot не продлил / браузер видит старый сертификат | закрыт порт 80, перенаправление на нестандартный порт, два certbot; certonly без хука | открыть 80; один certbot; `certbot renew --dry-run`; deploy-хук `systemctl reload apache2` |
| 12 | Сайт «навсегда» требует HTTPS | браузер помнит HSTS до истечения `max-age` | ждать/очистить в браузере; начинать с малого `max-age` |
| 13 | `400` «Size of a request header field exceeds server limit» у части пользователей | большой билет Kerberos (до 12 392 байт) или cookie | `LimitRequestFieldSize 32768` глобально (не во втором хосте!) |
| 14 | Окно ввода пароля вместо SSO | нет SPN; сайт не в «Интрасети»; вход по IP/CNAME; откат на NTLM | 10.2, 10.5 |
| 15 | Kerberos «вдруг» сломался у всех | перевыпущен keytab / сменён пароль учётки (kvno) | новый keytab; `klist -k` против `kvno` |
| 16 | `Can't contact LDAP server` при `ldaps://` | нет доверия к сертификату контроллера | `LDAPTrustedGlobalCert CA_BASE64 …`; проверить `ldapsearch` |
| 17 | Вход по LDAP есть, `Require ldap-group` не проходит | вложенные группы AD (класс `group`); кавычки вокруг DN | `AuthLDAPSubGroupClass group`; DN без кавычек; `LogLevel authnz_ldap:debug` |
| 18 | Заблокированный в AD пользователь ещё входит; вход медленный | кеш `mod_ldap` (600 с); referrals, мёртвый первый DC | меньше `LDAPCacheTTL`; `LDAPReferrals Off`; `LDAPConnectionTimeout 5` |
| 19 | 413 при загрузке файла в 1С | `LimitRequestBody` (1 ГиБ с 2.4.54) или `client_max_body_size` nginx | явный `LimitRequestBody` в `<Location "/публикация">` |
| 20 | 414 на запросах OData | `LimitRequestLine 8190` | поднять глобально (13.4) |
| 21 | 408 при медленной загрузке | `mod_reqtimeout`: тело медленнее 500 байт/с | понизить `MinRate` для хоста публикации |
| 22 | `Require ip` пропускает/блокирует не тех; `/server-status` открыт снаружи | за прокси адрес клиента = адрес прокси (`Require local` всем) | `mod_remoteip` с доверенными прокси; закрыть служебные пути |
| 23 | Приложение за Apache зацикливает перенаправление на HTTPS / строит ссылки `http://` | нет `X-Forwarded-Proto` | `RequestHeader set X-Forwarded-Proto "https"` |
| 24 | Сканер нашёл открытый прокси / листинги каталогов | `ProxyRequests On`; `Options Indexes` из `apache2.conf` | `ProxyRequests Off`; `Options -Indexes` |
| 25 | 401 у сервисов 1С при верном пароле | Basic Apache перехватил `Authorization` | убрать Basic с путей сервисов, ограничить по IP (`1c/05`, 11.4) |
| 26 | Apache ждёт пароль ключа и не поднимается после перезагрузки | ключ зашифрован | ключ без пароля с правами 600 или PKCS#11 |

## Быстрая шпаргалка

| Задача | Команда / директива |
|---|---|
| Включить TLS | `sudo a2enmod ssl && sudo a2ensite <хост> && sudo apache2ctl configtest && sudo systemctl reload apache2` |
| Проверить конфигурацию | `sudo apache2ctl configtest`; хосты — `sudo apache2ctl -S`; модули — `apache2ctl -M` |
| Что отдаёт сервер, срок, SAN | `openssl s_client -connect H:443 -servername H </dev/null \| openssl x509 -noout -dates -subject -ext subjectAltName` |
| Истекает ли за 21 день | `openssl x509 -in cert.pem -noout -checkend $((21*86400))` |
| Пара ключ/сертификат | `openssl x509 -noout -pubkey -in c.pem \| sha256sum` и `openssl pkey -pubout -in k.key \| sha256sum` |
| CSR с SAN | `openssl req -new -newkey rsa:2048 -nodes -keyout k.key -out r.csr -subj "/CN=H" -addext "subjectAltName=DNS:H"` |
| Доверить корпоративный ЦС | `sudo cp ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates` |
| Let's Encrypt | `sudo certbot --apache -d H`; `sudo certbot renew --dry-run`; `systemctl list-timers \| grep certbot` |
| Профиль intermediate | `SSLProtocol -all +TLSv1.2 +TLSv1.3`; шифры — 4.3; `SSLHonorCipherOrder off`; `SSLSessionTickets off` |
| Проверить версии TLS | `openssl s_client -connect H:443 -servername H -tls1_2 </dev/null` (и `-tls1_3`, `-tls1_1`) |
| HSTS / на HTTPS | `Header always set Strict-Transport-Security "max-age=63072000"`; `Redirect permanent / https://H/` в хосте `*:80` |
| HTTP/2 | `sudo a2enmod http2`; `curl -sI --http2 https://H/ -o /dev/null -w '%{http_version}'` |
| Скрыть версию, TRACE | `ServerTokens Prod`, `ServerSignature Off`; `curl -si -X TRACE https://H/ \| head -1` → 405 |
| Сеть И пароль | `<RequireAll> Require ip 10.10.20.0/24; Require valid-user </RequireAll>` |
| Файл паролей | `sudo htpasswd -c -B -C 12 файл user` (первый), далее без `-c`; `-v` — проверить, `-D` — удалить |
| LDAP/AD | `sudo a2enmod authnz_ldap`; `AuthBasicProvider ldap`; `AuthLDAPURL "ldaps://dc1 dc2/DC=…?sAMAccountName?sub?(objectClass=user)"`; `Require ldap-group CN=…` |
| Kerberos | `sudo apt install libapache2-mod-auth-gssapi krb5-user && sudo a2enmod auth_gssapi`; `sudo klist -k -t -e <keytab>`; `curl --negotiate -u : -v https://H/intranet/` |
| Большие билеты, длинные URL, загрузки 1С | `LimitRequestFieldSize 32768`, `LimitRequestLine 16384` — глобально; `<Location "/demo"> LimitRequestBody 4294967296 </Location>` |
| Не открытый прокси | `ProxyRequests Off`; `curl -x http://H:80 http://example.com/` не должен вернуть example.com |
| Приложение за прокси | `ProxyPreserveHost On`; `RequestHeader set X-Forwarded-Proto "https"`; к HTTPS-бэкенду — `SSLProxyVerify require` |
| Закрытые CVE в пакете | `apt changelog apache2 \| grep -oE 'CVE-20[0-9]{2}-[0-9]+' \| sort -u` |

## Источники

Apache HTTP Server (документация 2.4 — `https://httpd.apache.org/docs/2.4/<страница>.html`, исходники — `raw.githubusercontent.com/apache/httpd/2.4.x/docs/manual/<путь>.xml`):

- https://httpd.apache.org/ (выпуск 2.4.69, TLS 1.3 — с 2.4.43), https://httpd.apache.org/security/vulnerabilities_24.html (CVE и даты выпусков 2.4.64–2.4.69), https://downloads.apache.org/httpd/CHANGES_2.4 (`LimitRequestBody` в 2.4.54, TLS 1.3 в 2.4.36, `SSLVHostSNIPolicy`, SHA-2 в `htpasswd` в 2.4.59).
- `mod/mod_ssl`, `ssl/ssl_howto` (OCSP stapling, `AH02217`, `AH01929`, клиентские сертификаты), `mod/core` (`ServerTokens`, `ServerSignature`, `TraceEnable`, `LimitRequest*` — SPNEGO до 12 392 байт, `Protocols`), `mod/mod_http2`, `howto/http2` (MPM `prefork`).
- `mod/mod_authz_core`, `mod/mod_authz_host`, `mod/mod_auth_basic`, `mod/mod_authn_core`, `mod/mod_authn_file`, `mod/mod_authn_socache`, `programs/htpasswd`, `mod/mod_authnz_ldap` (в т. ч. «Using Active Directory»), `mod/mod_ldap`.
- `mod/mod_reqtimeout`, `mod/mod_headers` (`always`/`onsuccess`, `early`), `mod/mod_proxy` (`ProxyRequests`, доступ к прокси, `X-Forwarded-*`), `mod/mod_alias` (`Redirect`), `mod/mod_md`, `mod/mod_remoteip`, `mod/mod_info` (`-DDUMP_CONFIG`), `expr` (`-R`), `misc/security_tips`.

Ubuntu и Debian:

- https://packages.ubuntu.com/ — версии и списки файлов `apache2`, `apache2-bin` (зависимости `libaprutil1-ldap`, `libldap2`), `apache2-utils`, `libapache2-mod-auth-gssapi`, `certbot`, `ssl-cert`, `openssl`, `krb5-user`, `ldap-utils`.
- https://changelogs.ubuntu.com/changelogs/pool/main/a/apache2/ — `2.4.58-1ubuntu8.17`, `2.4.66-2ubuntu2.6`, jammy до `4.24`: перенос CVE-2025-23048/49812 (jammy 4.15, noble 8.7), `SSLVHostSNIPolicy` (jammy 4.18, noble 8.10), CVE 2026 г.
- https://salsa.debian.org/apache-team/apache2 (API; метки `debian/2.4.52-1`, `debian/2.4.58-1`, `debian/2.4.66-2`) — `debian/config-dir/` (`ssl.conf`, `ssl.load`, `reqtimeout.conf`, `http2.conf`, `ldap.conf`, `status.conf`, `proxy.conf`, `security.conf`, `default-ssl.conf`, `ports.conf`, `apache2.conf.in`), `apache2.README.Debian`, `apache2.postinst`, `apache2.service`, журнал коммитов `debian/config-dir`.
- Документация Ubuntu Server: «How to use Apache2 modules»; исходники `github.com/canonical/ubuntu-server-documentation` — `obtain-tls-certificates.md`, `install-a-root-ca-certificate-in-the-trust-store.md`, `explanation/crypto/openssl.md` (SECLEVEL=2).

Сторонние:

- https://github.com/gssapi/mod_auth_gssapi (README) — директивы `Gssapi*`, NTLM-откат браузеров, `gssapi-no-negotiate`.
- https://configurator.tlsref.org/, https://data.tlsref.org/guidelines/6.0.json (`github.com/tlsref/data`), шаблон `github.com/tlsref/configurator/src/js/helpers/apache.js`; https://ssl-config.mozilla.org/guidelines/latest.json (6.0) и CHANGELOG; https://wiki.mozilla.org/Security/Server_Side_TLS (сообщение о переезде на docs.tlsref.org).
- https://eff-certbot.readthedocs.io (исходник `certbot/docs/using.rst`) и `certbot/CHANGELOG.md` — плагин Apache, файлы `live/`, хуки, таймеры, устаревание `certbot.ocsp`.
- https://letsencrypt.org/2024/12/05/ending-ocsp/, https://letsencrypt.org/2025/08/06/ocsp-service-has-reached-end-of-life/ — конец OCSP; https://letsencrypt.org/docs/challenge-types/ — перенаправления при HTTP-01.

Добавлено при независимой сверке 20.10.2026:

- Исходный код httpd (`raw.githubusercontent.com/apache/httpd/<2.4.52|2.4.58|2.4.64–2.4.66|2.4.x>/…`): `server/core.c` (`set_limit_req_body`), `server/protocol.c` (414, `AH00565`), `server/util_xml.c` (`AH00539`), `server/main.c` (режим `-t` без `post_config`), `modules/mappers/mod_alias.c` и `modules/http/http_protocol.c` (308), `modules/ssl/ssl_engine_init.c` (`AH02572`, `AH01916`, `AH02407`, `ssl_init_ctx_cipher_suite`), `modules/ssl/ssl_engine_config.c` (`SSLEngine optional` → `AH10510`, разбор `SSLProtocol`), `modules/aaa/mod_authnz_ldap.c` (`exec:`, построение фильтра), `modules/proxy/mod_proxy_http.c` (таблица заголовков ответа); `docs/manual/sections.xml`; OpenSSL 3.0.13 `ssl/t1_lib.c`, `doc/man1/openssl-pkcs12.pod.in`.
- salsa.debian.org (через браузер): `debian/apache2.service` (метки `debian/2.4.52-1`, `2.4.58-1`, `2.4.66-2`), `debian/rules`, `debian/control`, `debian/apache2.postinst`, `debian/config-dir/*` (`2.4.58-1`); пакет certbot `debian/2.9.0-1` (`certbot.cron.d`, `certbot.timer`); журнал `apache2_2.4.66-2ubuntu2.6` (запись `2.4.59-1` об `AllowCONNECT`, `2.4.64-2` о TLS 1.0/1.1).
- `github.com/gssapi/mod_auth_gssapi` — `src/mod_auth_gssapi.c` (`APLOG_USE_MODULE`); MIT krb5 — `doc/admin/conf_files/krb5_conf.rst` (`clockskew`), `src/lib/krb5/error_tables/krb5_err.et`; OpenLDAP — `doc/man/man5/ldap.conf.5`.
- Microsoft: справка Windows Server `ktpass`, `setspn`, `certreq` (`MicrosoftDocs/windowsserverdocs`), схема AD «Group class», ADSI «Search Filter Syntax», политики Edge `AuthServerAllowlist`/`AuthNegotiateDelegateAllowlist`; Chromium — определения политик `HTTPAuthentication/*.yaml`; `mozilla/policy-templates` (`Authentication`); MDN `X-Frame-Options`, `X-XSS-Protection`; nginx.org (`proxy_ssl_server_name`, `client_max_body_size`); Apache Lounge (страница загрузки); документация Ubuntu Server «Package management» (universe и ESM).

1С (ИТС, по полным текстам 8.3.27): «Руководство администратора», разд. 2.8.1.2 (Kerberos в Apache), гл. 8 (8.2 — HTTPS и MPM worker; 8.9.2 — TLS 1.0–1.3, клиентские сертификаты при TLS 1.3 только ГОСТ; 8.10.1.3 — `X-Frame-Options`; 8.10.3 — обратный прокси), прил. 4.14; методички 5978 (Apache под Windows с HTTPS, 2020), 5979/5980 (HTTPS на Apache/nginx под Linux, 2020), 2799 (Kerberos для Linux-сервера 1С, 2015).

## Что не удалось подтвердить

Закрыто независимой сверкой 20.10.2026 (см. отметки «уточнено/подтверждено 20.10.2026» в тексте): поведение при неизвестной группе в `SSLOpenSSLConfCmd Curves`, `Redirect 308`, имена политик Chrome/Edge/Firefox, синтаксис `setspn`/`ktpass`/`certreq`, класс групп AD и OID цепочки, тексты ошибок Kerberos и `clockskew`, идентификатор `LogLevel auth_gssapi`, пользователь `AuthLDAPBindPassword exec:`, `LDAPTLS_CACERT`, `ALLOW-FROM`, перезапуск при обновлении пакета и cron certbot, «последняя побеждает» и слияние `<Directory /var/www/>`, перекрытие заглушкой `<Location "/">`, верхний предел `LimitRequestBody`, поддержка universe, умолчания nginx, юнит 26.04. Остаётся:

1. Умолчание `LimitRequestBody` в Ubuntu 22.04 (2.4.52): по журналу пакета заплатка CVE-2022-29404 правит только `mod_lua`; вероятно, действует 0. Проверка — загрузка > 1 ГиБ без явного лимита.
2. Сохраняет ли `ktpass … /in старый.keytab /out новый.keytab` прежние записи; влияние `LDAPReferrals On` при поиске от корня домена AD — практика.
3. `kinit -k -t keytab HTTP/…` только при UPN = принципалу; сверка `kvno` с `klist -k` — практика.
4. Подхватывает ли `wsap24` кеш `GssapiDelegCcacheDir` (`KRB5CCNAME`) и как сопоставляет `REMOTE_USER` с пользователем 1С (из `1c/05`, 11.3).
5. С какой версии платформы 1С есть TLS 1.3 (для 8.3.27 — есть, ИТС 8.9.2); ECDSA у старых тонких клиентов и интеграций; польза HTTP/2 для веб-клиента.
6. Строгий CSP ломает веб-клиент 1С и сервисы — практика.
7. Действие `LimitXMLRequestBody` на SOAP-запросы к модулю 1С (по коду Apache лимит проверяется только в `ap_xml_parse_input()`).
8. Практические значения (`RequestReadTimeout handshake=5-10,…`, `LimitRequestFieldSize 32768`, `LimitRequestLine 16384`) и схема `SetEnvIfExpr "! -R '10.0.0.0/8'" gssapi-no-negotiate` — на стенде не проверялись.
9. «На CN браузеры не смотрят» (требования CA/Browser Forum и браузеров не перечитывались); OCSP-ответчик AD CS; требования Microsoft к подписи LDAP; поддержка post-handshake auth клиентами TLS 1.3.
10. Совпадает ли `apache2.service` пакета Ubuntu 26.04 с юнитом Debian `debian/2.4.66-2` — `systemctl cat apache2` на сервере. Дамп разобранной конфигурации — `-DDUMP_CONFIG` только при загруженном `mod_info` [Apache-док].
