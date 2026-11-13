# IIS: HTTPS и TLS, сертификаты, аутентификация (анонимная, Basic, Windows/Kerberos), авторизация и безопасность

> **Официальные тексты по теме**: справочник конфигурации IIS 10.0 (`system.webServer/security/*`, `system.applicationHost/sites/site/{bindings,hsts}`, `httpProtocol`, `httpRedirect`, `httpErrors`), статьи «IIS 10.0 Version 1709 HSTS Support», «New Features in IIS 10.0 / 1709 / 1809», «Centralized SSL Certificate Support», «SNI», «Application Pool Identities», «Understanding IIS URL Authorization»; Windows — «TLS registry settings», «Manage TLS», «Protocols in TLS/SSL (Schannel SSP)», `netsh http`, модули PowerShell `IISAdministration`, `WebAdministration`, `TLS`, `PKI`; статьи поддержки «Http.sys registry settings», «HTTP 400 … Request Header too long», «Troubleshoot Kerberos failures», «HTTP status code overview». 1С — «Руководство администратора» 8.3.27: разд. 8.9 «Безопасность при работе через Интернет», 8.10.2 «Internet Information Services», 4.3.8–4.3.9, 5.2.4, прил. 7.3.4; конспекты `../its-docs/adm-gl08-veb-servery-p1.md`, `-p2.md`; методички ИТС 5977, 5944, 5949.

> Статус: проверено независимой сверкой 20.10.2026: с исходниками справочника конфигурации IIS и статей `MicrosoftDocs/iis-docs` (атрибуты, умолчания и образцы `appcmd`/PowerShell всех разделов), со схемой `IIS_schema.xml` IIS 10 (Windows 11 26300), с `windowsserverdocs` (TLS registry settings, Manage TLS, netsh http, AD FS, certutil), `win32`/`sdk-api` (Schannel: протоколы, наборы шифров, `SecPkgContext_ConnectionInfo`, `LogonUser`, журнал HTTP Server API), `SupportArticles-docs` (Http.sys, HTTP 400 Kerberos, Kerberos failures, коды состояния), `windows-powershell-docs` (IISAdministration, WebAdministration, TLS, PKI), событием 4624, с полными текстами ИТС 8.3.27 (разд. 4.3.8.2, 4.3.9, 8.4.3.2.1, 8.9, 8.10.2, прил. 3.17, 7.3.4), конспектом гл. 17 «Руководства разработчика» и методичками 5944, 5949, 5977; исправлено 8 ошибок и неточностей, закрыто 20 пометок; на сервере не проверялось. Команды с пометкой [практика] и помеченное как неподтверждённое (сводка — в конце) с документацией не сверены.

> Область: безопасность IIS 10.0 на Windows Server 2016–2025 — сертификаты (хранилища, импорт, привязки, SNI, CCS, перепривязка), протоколы и шифры Schannel, HSTS и перенаправление, заголовки и скрытие версии, аутентификация (анонимная, Basic, Windows/Kerberos, Extended Protection, клиентские сертификаты), авторизация (URL Authorization, ограничения по IP, динамические ограничения), фильтрация запросов, учётные записи пулов, журналы безопасности; где это важно для публикации 1С | Версии: IIS 10.0 (WS 2016 = 1607, 2019 = 1809, 2022, 2025); 1С 8.3.27 / 8.5.x | Актуальность: 2026-10-20

Пометки: **[MS Learn]** — документация Microsoft; **[ИТС-адм разд. N]** — «Руководство администратора» 1С 8.3.27; **[ИТС-мет NNNN, ГГГГ]** — методическая статья ИТС; **[сторонний]** — документация стороннего продукта (MDN, OpenSSL, curl); **[практика]** — практика или вывод автора; **⚠** — не подтверждено первоисточником (сводка — в конце).

Смежные статьи: `iis/01-ustrojstvo-ustanovka-sajty-puly.md` (устройство, роли, сайты, пулы); `iis/03-proizvoditelnost-arr-zhurnaly-diagnostika.md` (ARR, журналы, FREB); `1c-windows/03-veb-publikaciya-iis.md` — **публикация 1С** (`webinst`, `default.vrd`, `wsisapi.dll`, права, лимиты для OData, HTTPS и аутентификация именно для 1С — здесь не дублируется); `1c-windows/04-…` (SPN службы 1С, делегирование в AD); `1c-windows/06-…` (**сроки поддержки Windows Server** — раздел 1, брандмауэр — 6.3, журналы — 11); `apache/02-https-bezopasnost-autentifikaciya.md` (то же для Apache, сравнение — раздел 17).

Обозначения: компьютер с IIS — `WEB01` (`CORP\WEB01$`), имя публикации — `web1c.corp.local` (A-запись на `WEB01`), домен `CORP` / `corp.local`; сайт `Default Web Site`, приложение 1С — `Default Web Site/demo`, пул — `1C-<версия>`; группа — `CORP\1C-Web-Users`; сервер интеграции — `10.10.20.15`, подсеть администраторов — `10.10.5.0/24`; кластер 1С пользователя — `srv-1c-app` (Ubuntu). Все команды — в консоли **от имени администратора**; `appcmd` лежит в `%windir%\system32\inetsrv\` (в `PATH` не входит). Перед серией изменений — `appcmd add backup <имя>` (откат — `appcmd restore backup "<имя>"`) [MS Learn].

## Кратко — главные факты

1. **IIS везде 10.0, но возможности зависят от сборки Windows**: `<hsts>` и `removeServerHeader` — с 1709, то есть с Windows Server 2019 (**не 2016**); `New-/Get-/Remove-IISSiteBinding` — с 1709; флаги привязки `DisableHTTP2`/`DisableOCSPStp` — с 1809; TLS 1.3 — с Windows Server 2022 [MS Learn].
2. **TLS делает Schannel — общий для всей ОС.** У сайта можно только выключить что-то у привязки (`sslFlags` 4–64: `DisableTLS13`, `DisableLegacyTLS` …); шифры и их порядок — на весь сервер (`Get-/Disable-/Enable-TlsCipherSuite`, политика «SSL Cipher Suite Order») [MS Learn].
3. **Сертификат** — в `Cert:\LocalMachine\My` (или `WebHosting`), с ключом и всеми именами в SAN; `Import-PfxCertificate` без `-Exportable` делает ключ неэкспортируемым [MS Learn]. Для 1С поля сертификата — только US-ASCII/Punycode [ИТС-адм разд. 8.9.2].
4. **HTTPS-привязка живёт в двух местах**: `<binding protocol="https" bindingInformation sslFlags>` в `applicationHost.config` и запись http.sys с отпечатком (`netsh http show sslcert`) [MS Learn].
5. **SNI** — `sslFlags="1"`, в http.sys `hostnameport=имя:443`; **CCS** — компонент `Web-CertProvider`, файлы `<имя>.pfx` (`_.corp.local.pfx` для подстановочного), `sslFlags="2"`, запись `ccs=443` [MS Learn].
6. **Продлённый сертификат сам не встанет**, если не включена «автоматическая перепривязка» (Certificate Rebind, IIS 8.5+) [MS Learn].
7. **Версии протоколов** — `HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\<TLS 1.x>\Server`, параметр `Enabled` (0/1); `DisabledByDefault` описан в руководстве AD FS, но не в текущем справочнике [MS Learn]. В ИТС — `DisableByDefault` [ИТС-адм разд. 8.10.2.5]: такого имени у Microsoft нет (подтверждено 20.10.2026: ни в «TLS registry settings», ни в руководстве AD FS его нет — там только `Enabled` и `DisabledByDefault`).
8. **По умолчанию**: WS 2016/2019 — TLS 1.0–1.2; WS 2022/2025 — плюс TLS 1.3; SSL 3.0 выключен с 2016 [MS Learn]. Отключение TLS 1.0/1.1 «по умолчанию» анонсировано для выпусков с 2024 года, но таблица протоколов показывает их включёнными на WS 2025 ⚠.
9. **Прежде чем выключать TLS 1.0/1.1** — журнал `CRYPT_PROTOCOL` (IIS 1709+, TLS 1.2 = `400`) или Schannel `EventLogging` [MS Learn]; выключать — у привязки (`DisableLegacyTLS`) или в реестре с перезагрузкой.
10. **HSTS** — `<hsts enabled max-age includeSubDomains preload redirectHttpToHttps>` у сайта, всё по умолчанию выключено, `max-age` = 0 [MS Learn]. `includeSubDomains` на корпоративном домене сломает внутренние HTTP-сайты [практика].
11. **HTTP → HTTPS**: `redirectHttpToHttps` (1709+); `<httpRedirect>` на отдельном HTTP-сайте (`Permanent` 301, `Found` 302, `Temporary` 307, `PermRedirect` 308 — с IIS 10.0); URL Rewrite 2.1 (ставится отдельно, 308 не умеет) [MS Learn].
12. **Для 1С не полагайтесь на перенаправление** — тонкий клиент, HTTP-сервисы, SOAP, OData сразу на `https://` [практика]; через Интернет — только HTTPS [ИТС-адм разд. 8.2; ИТС-мет 5977, 2020].
13. **Заголовки** (`customHeaders`): убрать `X-Powered-By`, добавить `nosniff`, `Referrer-Policy`, `Content-Security-Policy: frame-ancestors` [MS Learn; сторонний MDN]. ИТС для встраивания веб-клиента даёт `X-Frame-Options` с `allow-from` [ИТС-адм разд. 8.10.2.7], но браузеры такой заголовок игнорируют целиком [сторонний MDN] — нужен `frame-ancestors`.
14. **`Server`**: `removeServerHeader="true"` у `<requestFiltering>` (1709+) и `DisableServerHeader` (0/1/2) в реестре http.sys [MS Learn].
15. **Секции аутентификации заблокированы на уровне сервера** — `appcmd … /commit:apphost` пишет их в `<location>` `applicationHost.config` [MS Learn]. Анонимная включена по умолчанию от `IUSR`; `userName=""` — от удостоверения пула.
16. **Basic на IIS** проверяет учётную запись Windows, пароль идёт открыто — только поверх HTTPS [MS Learn]. Для 1С почти не нужен: при анонимном IIS 1С сама запрашивает Basic и проверяет своих пользователей [ИТС-адм разд. 8.9.1].
17. **Windows-аутентификация**: поставщики `Negotiate`, `NTLM`; `useKernelMode="true"`; без SPN Kerberos работает для `ApplicationPoolIdentity` через учётную запись компьютера; псевдоним — SPN `HTTP/<имя>`; пул под доменной учётной записью — SPN на ней и `useAppPoolCredentials="true"`; дубли SPN → `KRB_AP_ERR_MODIFIED` [MS Learn].
18. **Windows-аутентификация не работает поверх HTTP/2** — IIS сам откатывается на HTTP/1.1 [MS Learn].
19. **400 «Request header too long»** — большой билет Kerberos: `MaxFieldLength`/`MaxRequestBytes` = 4/3·T + 200 и перезапуск службы HTTP [MS Learn].
20. **Аутентификация ОС 1С через IIS**: анонимная выкл., Windows вкл., `Negotiate` первым, `iisreset`; разнесённые IIS и кластер — делегирование Kerberos [ИТС-мет 5944, 2018]; к Linux-кластеру — только Kerberos к SPN `usr1cv8/…` ⚠.
21. **Extended Protection** (`tokenChecking` `None`/`Allow`/`Require`, по умолчанию `None`): начинать с `Allow`; за SSL-разгружающим прокси — флаг `Proxy` и `<spn>` [MS Learn].
22. **Клиентские сертификаты**: `<access sslFlags="Ssl, SslNegotiateCert|SslRequireCert">` + сопоставление через AD или IIS [MS Learn]. В 1С при TLS 1.3 клиентские сертификаты — только ГОСТ [ИТС-адм разд. 8.9.2] ⚠ для RSA — выключать TLS 1.3 у привязки.
23. **URL Authorization**: сначала запреты (от родителя), потом разрешения [MS Learn]; работает, только когда IIS знает пользователя (Windows/Basic) [практика].
24. **`ipSecurity` / `dynamicIpSecurity`** (`Web-IP-Security`): белые списки для `/hs`, `/odata`; динамические пороги по умолчанию — 5 одновременных или 20 запросов за 200 мс, выключены [MS Learn]; для веб-клиента 1С начинать с `enableLoggingOnlyMode` [практика].
25. **Фильтрация**: `maxAllowedContentLength` 30 000 000, `maxUrl` 4096, `maxQueryString` 2048; `allowHighBitCharacters` не выключать (кириллица в URL OData — имена ресурсов вида `Catalog_Контрагент` [ИТС, «Руководство разработчика», 17.4]); `TRACE` запретить [MS Learn]. Пул — `ApplicationPoolIdentity`; аудит — подстатусы IIS, 4624/4625, Schannel, CAPI2.

## 1. Версии IIS 10.0 и компоненты

### 1.1. Что зависит от сборки

[MS Learn, «New Features Introduced in IIS 10.0 / 1709 / 1809», справочники `hsts`, `requestFiltering`, `binding`, «Protocols in TLS/SSL»]

| Возможность (раздел) | WS 2016 (1607) | WS 2019 (1809) | WS 2022 | WS 2025 |
|---|---|---|---|---|
| HTTP/2 поверх TLS | да | да | да | да |
| `<hsts>`, `redirectHttpToHttps` (4) | **нет** | да (+ интерфейс в диспетчере) | да | да |
| `removeServerHeader` (5.3) | **не работает** | да | да | да |
| `New-/Get-/Remove-IISSiteBinding` (2.3) | нет (`New-WebBinding`) | да | да | да |
| Переменные `CRYPT_*` для журнала (3.5) | нет | да | да | да |
| Флаги `DisableHTTP2` (4), `DisableOCSPStp` (8) | нет | да | да | да |
| Флаги `DisableQUIC` (16), `DisableTLS13` (32), `DisableLegacyTLS` (64) | нет | ⚠ | да ⚠ | да ⚠ |
| TLS 1.3 | нет | нет | **да, включён** | **да, включён** |

⚠ Справочник `<binding>`: «значения больше 4 — только с IIS 10 version 1809»; флаги TLS 1.3 и QUIC осмысленны лишь на WS 2022+, на 2019 не проверялись. На **WS 2016** (расширенная поддержка — до января 2027, `1c-windows/06`) нет встроенного HSTS, скрытия `Server` и новых командлетов — ниже даны обходные пути (более новую версию модуля `IISAdministration` Microsoft распространяет и через PowerShell Gallery для Windows Server 2012 и новее [MS Learn, «New Features 1709», «IISAdministration PowerShell Cmdlets»]). Проверка: `Get-ComputerInfo -Property WindowsProductName, OsBuildNumber`; `Get-Command New-IISSiteBinding -ErrorAction SilentlyContinue` [практика].

### 1.2. Компоненты безопасности

[MS Learn, «Installing IIS 8.5 on Windows Server 2012 R2» — таблица имён; ⚠ для IIS 10.0 сверьте `Get-WindowsFeature Web-*`]

| Компонент | `Install-WindowsFeature` | Секция | Раздел |
|---|---|---|---|
| Request Filtering (ставится по умолчанию) | `Web-Filtering` | `requestFiltering` | 14 |
| Basic Authentication | `Web-Basic-Auth` | `basicAuthentication` | 8 |
| Windows Authentication | `Web-Windows-Auth` | `windowsAuthentication` | 9 |
| Client Certificate Mapping (через AD) | `Web-Client-Auth` | `clientCertificateMappingAuthentication` | 10 |
| IIS Client Certificate Mapping | `Web-Cert-Auth` | `iisClientCertificateMappingAuthentication` | 10 |
| IP and Domain Restrictions (в IIS 8+ — и динамические) | `Web-IP-Security` | `ipSecurity`, `dynamicIpSecurity` | 12–13 |
| URL Authorization | `Web-Url-Auth` | `authorization` | 11 |
| Centralized SSL Certificate Support | `Web-CertProvider` | CCS | 2.5 |
| HTTP Redirection | `Web-Http-Redirect` | `httpRedirect` | 4.3 |
| Digest Authentication | `Web-Digest-Auth` | `digestAuthentication` | для 1С не нужен |

Анонимная аутентификация встроена [MS Learn]. Ставьте только используемое: IIS «из коробки» отдаёт лишь статику ради уменьшения поверхности атаки [MS Learn, `security`]. Пример: `Install-WindowsFeature -Name Web-Windows-Auth, Web-IP-Security, Web-Url-Auth, Web-Http-Redirect`, проверка — `Get-WindowsFeature Web-* | Where-Object Installed`.

## 2. Сертификаты

### 2.1. Требования

- **Хранилища компьютера**: `Cert:\LocalMachine\My` (в `netsh` — `MY`) и `Cert:\LocalMachine\WebHosting` — работает как «Личное», но рассчитано на большое число сертификатов; `-CertStoreLocation` у `New-IISSiteBinding` принимает только эти два [MS Learn, SNI; `New-IISSiteBinding`].
- **Ключ** — обязателен; без `-Exportable` при импорте он неэкспортируемый [MS Learn] — украсть его «Экспортом» нельзя; резервная копия — исходный PFX в сейфе [практика].
- **Имена** — все в SAN (`-DnsName` у `New-SelfSignedCertificate` кладёт их туда, первое — и в Subject) [MS Learn]; для SNI имя привязки должно совпадать с CN/SAN [MS Learn, SNI].
- **Назначение** — Server Authentication (`1.3.6.1.5.5.7.3.1`); http.sys по умолчанию проверяет назначение (`usagecheck` — «Default is enabled») [MS Learn, `netsh http`].
- **1С** [ИТС-адм разд. 8.9.2]: действительные подпись, срок, имя сайта; поля — только US-ASCII/Punycode; клиент доверяет ЦС цепочки (на Linux — `/etc/ssl/certs` [ИТС-адм разд. 4.3.9.3]).
- **Цепочка**: промежуточные ЦС — в `Cert:\LocalMachine\CA` [практика ⚠]; неполная цепочка — классика «браузер доволен, тонкий клиент нет» (браузер достраивает сам) [практика].
- **Отзыв**: клиенты 1С с 8.3.12 проверяют сертификат средствами Windows, включая отзыв, — CRL/OCSP вашего ЦС должны быть доступны **с клиентов** [ИТС-мет 5949, 2018]; в 8.3.27 при невозможности проверить отзыв соединение по умолчанию всё же устанавливается (`IgnoreServerCertificatesChainRevocationSoftFail` = `true`), отозванный сертификат отвергается [ИТС-адм прил. 3.17.16]; сторона клиента — `1c-windows/03`, раздел 9.6.

### 2.2. Получение и импорт

| Вариант | Как | Когда |
|---|---|---|
| AD CS | `Get-Certificate -Template <имя шаблона> -DnsName … -CertStoreLocation Cert:\LocalMachine\My` [MS Learn]; шаблон веб-сервера обычно `WebServer` ⚠ | внутренние публикации |
| Публичный ЦС | запрос из диспетчера IIS («Сертификаты сервера → Создать запрос сертификата…») ⚠ или готовый PFX | Интернет |
| Самоподписанный | `New-SelfSignedCertificate -DnsName … -CertStoreLocation Cert:\LocalMachine\My` (срок по умолчанию — год) [MS Learn] | только стенд — для реальных систем 1С не рекомендует [ИТС-мет 5977, 2020] |

```powershell
# AD CS от имени компьютера (право «Заявка» на шаблон)
$r = Get-Certificate -Template 'WebServer' -DnsName 'web1c.corp.local','WEB01.corp.local' -SubjectName 'CN=web1c.corp.local' -CertStoreLocation 'Cert:\LocalMachine\My'
$r.Status                                          # Issued или Pending
# Импорт PFX (ключ неэкспортируемый)
$pfxPass = Read-Host -AsSecureString 'Пароль PFX'
Import-PfxCertificate -FilePath 'C:\Certs\web1c.pfx' -CertStoreLocation 'Cert:\LocalMachine\My' -Password $pfxPass
# Проверка
Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.DnsNameList -match 'web1c' } |
  Select-Object Thumbprint, Subject, NotAfter, HasPrivateKey, @{n='SAN';e={$_.DnsNameList -join ','}}
certutil -urlfetch -verify C:\Certs\web1c.cer      # цепочка, загрузка сертификатов AIA и CRL из CDP [MS Learn, certutil]
```

Параметры `Get-Certificate` и `Import-PfxCertificate` — [MS Learn]. Пароль PFX не передавайте строкой в командной строке — он останется в истории PowerShell [практика].

### 2.3. Привязка `https`

В `applicationHost.config` — `<binding protocol="https" bindingInformation="IP:порт:имя" sslFlags="…">` (`sslFlags` по умолчанию `0`); отдельно http.sys хранит «адрес/имя:порт → отпечаток, хранилище, AppID» [MS Learn, `binding`, SNI, CCS]. Диспетчер IIS и командлеты создают обе части, `appcmd` — только первую.

| `sslFlags` | `-SslFlag` | Смысл | С версии |
|---|---|---|---|
| `0` | `None` | «IP:порт», один сертификат на сочетание | всегда |
| `1` | `Sni` | выбор по имени из SNI | IIS 8.0 |
| `2` | `CentralCertStore` | сертификат из CCS | IIS 8.0 |
| `4` / `8` | `DisableHTTP2` / `DisableOCSPStp` | выключить HTTP/2 / OCSP stapling | 1809 |
| `16` / `32` / `64` | `DisableQUIC` / `DisableTLS13` / `DisableLegacyTLS` | выключить QUIC / TLS 1.3 / «устаревший TLS» (какие версии — не уточнено ⚠) | ⚠ WS 2022+ |

Флаги складываются (`65` = SNI + DisableLegacyTLS) [MS Learn].

```powershell
# WS 2019+ (IISAdministration)
New-IISSiteBinding -Name 'Default Web Site' -BindingInformation '*:443:web1c.corp.local' -Protocol https `
  -CertificateThumbPrint '<отпечаток>' -CertStoreLocation 'Cert:\LocalMachine\My' -SslFlag 'Sni, DisableLegacyTLS'
Get-IISSiteBinding -Name 'Default Web Site'
netsh http show sslcert hostnameport=web1c.corp.local:443
# WS 2016 (WebAdministration)
New-WebBinding -Name 'Default Web Site' -IPAddress '*' -Port 443 -HostHeader 'web1c.corp.local' -Protocol 'https' -SslFlags 1
(Get-WebBinding -Name 'Default Web Site' -Port 443 -Protocol 'https').AddSslCertificate('<отпечаток>', 'my')
```

```bat
:: любая версия: appcmd + netsh (две части) [синтаксис — MS Learn; связка — практика]
cd /d %windir%\system32\inetsrv
appcmd set site /site.name:"Default Web Site" /+bindings.[protocol='https',bindingInformation='*:443:web1c.corp.local',sslFlags='1']
netsh http add sslcert hostnameport=web1c.corp.local:443 certhash=<отпечаток> appid={<GUID из [guid]::NewGuid()>} certstorename=MY
```

Синтаксис командлетов, образцы `appcmd set site /+bindings.[…]` и ключи `netsh http add sslcert` (`hostnameport`, `ipport`, `ccs`, `certhash`, `appid`, `certstorename`) — [MS Learn]. Без SNI: `*:443:` и `ipport=0.0.0.0:443`. Удаление: `Remove-IISSiteBinding -Name … -BindingInformation … -Protocol https` [MS Learn] или `netsh http delete sslcert hostnameport=…` + `appcmd set site … /-bindings.[…]` [практика]. Проверка снаружи: `Test-NetConnection web1c.corp.local -Port 443`; `curl.exe -sv -o NUL https://web1c.corp.local/` (Schannel; `curl.exe` есть в Windows 10 1803+/Server 2019+ ⚠); с Ubuntu — `openssl s_client -connect web1c.corp.local:443 -servername web1c.corp.local -showcerts </dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName` [сторонний].

### 2.4. SNI

- Клиент передаёт имя при рукопожатии, IIS выбирает сертификат по имени — много HTTPS-сайтов на одном IP:443; клиент без SNI (в документации — IE на Windows XP) имени не передаст [MS Learn, SNI].
- При смешении привязок «IP:порт» и «имя:порт» диспетчер IIS изредка удаляет не ту запись SSL — сверяйтесь с `netsh http show sslcert` [MS Learn].
- Схема для сервера с несколькими сайтами: SNI-привязки у сайтов + одна `*:443:` с сертификатом-заглушкой на сайте, отвечающем 403/404, — сканеры «по IP» не увидят внутренние имена [практика].
- OCSP stapling у привязок с SNI и CCS **по умолчанию выключен**; включается `EnableOcspStaplingForSni` = 1 (DWORD) в `…\SecurityProviders\SCHANNEL` [MS Learn].

### 2.5. Централизованное хранилище (CCS)

Для фермы или десятков сайтов: сертификаты в общей папке, IIS выбирает файл по имени узла [MS Learn, «IIS 8.0 Centralized SSL Certificate Support»]. Компонент `Web-CertProvider` (по умолчанию не ставится); файлы `<имя узла>.pfx`, подстановочный — `_.corp.local.pfx`, многоимённый — отдельный файл на каждое имя, у всех PFX — один общий пароль или без пароля; учётная запись доступа к папке — только чтение; привязка `sslFlags="2"` (с SNI — `3`), в http.sys одна запись `ccs=443` без отпечатка [MS Learn].

```powershell
Install-WindowsFeature Web-CertProvider
$acct = Read-Host -AsSecureString 'Пароль svc-iis-certs'; $pk = Read-Host -AsSecureString 'Общий пароль PFX'
Enable-IISCentralCertProvider -CertStoreLocation '\\fs01\IISCerts' -UserName 'CORP\svc-iis-certs' -Password $acct -PrivateKeyPassword $pk
Get-IISCentralCertProvider
New-IISSiteBinding -Name 'Intranet' -BindingInformation '*:443:intranet.corp.local' -Protocol https -SslFlag 'Sni, CentralCertStore'
netsh http show sslcert ccs=443
```

[MS Learn, `Enable-IISCentralCertProvider`, `New-IISSiteBinding` пример 3]. Противоречие страницы `Enable-IISCentralCertProvider` подтверждено 20.10.2026: у `-PrivateKeyPassword` указано `Required: True`, но пример 1 обходится без него, а описание велит задавать параметр, только если у всех сертификатов общий пароль. На WS 2016 — `Enable-WebCentralCertProvider -CertStoreLocation … -UserName … -Password <строка> [-PrivateKeyPassword <строка>]` [MS Learn].

### 2.6. Продление и перепривязка

- **Certificate Rebind** (IIS 8.5+): «Сертификаты сервера → Включить автоматическую перепривязку обновлённого сертификата»; IIS регистрирует задачу планировщика `Microsoft\Windows\CertificateServicesClient`, которая на событие продления (1001) вызывает `appcmd` и меняет отпечаток во всех привязках; с автоматической регистрацией AD CS цикл полностью автоматический [MS Learn, «Certificate Rebind in IIS 8.5»].
- Без неё сайт отдаёт старый сертификат до истечения [MS Learn]. Ручная замена у SNI-привязки — пересоздать привязку (2.3) или `netsh http update sslcert hostnameport=… certhash=<новый> appid={…} certstorename=MY` ⚠ (сохраняет ли прочие флаги — не проверено).
- Контроль сроков [практика]:

```powershell
Get-ChildItem Cert:\LocalMachine\My, Cert:\LocalMachine\WebHosting |
  Where-Object { $_.HasPrivateKey -and $_.NotAfter -lt (Get-Date).AddDays(30) } | Select-Object PSParentPath, Thumbprint, Subject, NotAfter
netsh http show sslcert | Select-String 'IP:port|Hostname:port|Certificate Hash|Certificate Store'
```

Для 1С: одно имя (`web1c.corp.local`) — в SAN, в списке баз (`ws="https://web1c.corp.local/demo"`) и в SPN (9.3) [практика]; проверка сертификата на клиентах, `IgnoreServerCertificatesChainRevocationSoftFail`, CAPI2 — `1c-windows/03`, раздел 9.6 [ИТС-мет 5949; ИТС-адм прил. 3.17.16].

## 3. Протоколы и шифры: Schannel

### 3.1. Как устроено

- HTTPS в IIS обслуживает http.sys средствами Schannel; версии протоколов задаются в реестре **на всю систему** отдельно для роли сервера и клиента (`…\Protocols\<версия>\Server` / `\Client`) [MS Learn, «TLS registry settings»]. Клиентская роль влияет на исходящие соединения этого же сервера [практика].
- Приложение может только **сузить** системный набор версий [MS Learn]; в IIS это флаги привязки (2.3) — единственный «посайтовый» рычаг.
- Изменения действуют для новых дескрипторов учётных данных; долгоживущие службы нужно перезапускать [MS Learn] — для http.sys/LSASS на практике это перезагрузка [практика].
- Порядок шифров — через политику, MDM или модуль `TLS`; правка реестра порядка не поддерживается и может быть сброшена обновлением [MS Learn, «Manage TLS»].

### 3.2. Умолчания

[MS Learn, «Protocols in TLS/SSL (Schannel SSP)», ред. 20.03.2025]

| ОС | SSL 3.0 | TLS 1.0 | TLS 1.1 | TLS 1.2 | TLS 1.3 |
|---|---|---|---|---|---|
| WS 2016 (1607), WS 2019 (1809) | выкл. | вкл. | вкл. | вкл. | нет |
| WS 2022 | выкл. | вкл. | вкл. | вкл. | **вкл.** |
| WS 2025 | выкл. | вкл. ⚠ | вкл. ⚠ | вкл. | **вкл.** |

- Включать TLS 1.3 на более ранних Windows — «небезопасная конфигурация»; SSL 2.0 удалён с WS 2016 [MS Learn].
- ⚠ «TLS 1.0 and TLS 1.1 deprecation in Windows»: в сборках Insider 2024 года TLS 1.0/1.1 выключены, «уже выпущенных ОС это не касается»; таблица выше для WS 2025 показывает их включёнными. Проверяйте (3.6). Вернуть — `Enabled` = 1 в `TLS 1.0\Server`, `TLS 1.1\Server` (и `Client`) [MS Learn].
- Шифры WS 2022/2025 по умолчанию: первыми `TLS_AES_256_GCM_SHA384`, `TLS_AES_128_GCM_SHA256` (TLS 1.3), затем ECDHE-GCM для TLS 1.2; в WS 2022 23H2+ не включены `TLS_RSA_WITH_3DES_EDE_CBC_SHA` и `TLS_DHE_RSA_WITH_AES_*_GCM_*`; `TLS_CHACHA20_POLY1305_SHA256` поддерживается, но выключен [MS Learn, «TLS Cipher Suites in Windows Server 2022/2025»].

### 3.3. Реестр: точные имена и команды

```
HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\<SSL 3.0 | TLS 1.0 | TLS 1.1 | TLS 1.2 | TLS 1.3 | DTLS 1.2>\<Server | Client>
    Enabled            DWORD  1 — включить, 0 — выключить (переопределяет умолчание)
    DisabledByDefault  DWORD  1 — не использовать, пока приложение явно не попросит
```

- Справочник Microsoft (апрель 2025) для версий описывает **только `Enabled`** и предупреждает не создавать неописанные параметры Schannel; `DisabledByDefault` есть в руководстве AD FS (отключение SSL 3.0: `Enabled`=0, `DisabledByDefault`=1) [MS Learn]. Первичен `Enabled`; `DisabledByDefault`=1 рядом встречается в корпоративных шаблонах [практика].
- **ИТС** (разд. 8.10.2.5, рецепт времён Windows 7) для включения TLS 1.1/1.2 предлагает `DisableByDefault` = 0 [ИТС-адм разд. 8.10.2.5]; у Microsoft такого имени нет, а на WS 2016+ TLS 1.1/1.2 включены и так.
- Подраздела версии может не быть — значит, действует умолчание [MS Learn].

Выключить TLS 1.0/1.1 серверной роли (после 3.5; **сначала резервная копия** — ошибка ломает RDP и все HTTPS-службы сервера [практика]):

```powershell
reg export "HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL" "C:\Backup\schannel-$(Get-Date -Format yyyyMMdd-HHmm).reg"
$base = 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols'
foreach ($p in 'TLS 1.0','TLS 1.1') {
  $k = "$base\$p\Server"
  if (-not (Test-Path $k)) { New-Item -Path $k -Force | Out-Null }
  New-ItemProperty -Path $k -Name 'Enabled' -PropertyType DWord -Value 0 -Force | Out-Null
  New-ItemProperty -Path $k -Name 'DisabledByDefault' -PropertyType DWord -Value 1 -Force | Out-Null
}
Get-ChildItem $base -Recurse | ForEach-Object { [pscustomobject]@{ Key = ($_.Name -replace '^.*\\Protocols\\',''); Enabled = $_.GetValue('Enabled'); DisabledByDefault = $_.GetValue('DisabledByDefault') } }
# затем перезагрузка в окно обслуживания; откат — импорт .reg или удаление созданных значений [MS Learn: «To revert these changes, delete the above registry values»]
```

**Без реестра (WS 2022+)** — только у привязки публикации: `-SslFlag 'Sni, DisableLegacyTLS'` или `netsh http update sslcert … disablelegacytls=enable` [MS Learn]; другие сайты не затрагиваются ⚠ (не проверено). **TLS 1.3 у привязки** выключать лишь при реальной несовместимости (RSA-клиентские сертификаты 1С — 10.4): `DisableTLS13` / `disabletls13=enable` [MS Learn; применимость — практика].

### 3.4. Наборы шифров

```powershell
Get-TlsCipherSuite | Format-Table Name, Exchange, Cipher, CipherLength, Protocols   # упорядоченный список
Get-TlsCipherSuite -Name 'CBC'                                                       # подстрока С УЧЁТОМ регистра
Disable-TlsCipherSuite -Name 'TLS_RSA_WITH_3DES_EDE_CBC_SHA'
Enable-TlsCipherSuite -Name 'TLS_CHACHA20_POLY1305_SHA256' -Position 2                # 0 — высший приоритет
Get-TlsEccCurve                                                                      # curve25519, NistP256, NistP384
```

[MS Learn, модуль `TLS`; `-Name aes` ничего не вернёт — регистр учитывается]. ⚠ Страница `Enable-TlsCipherSuite` — «перезагрузка не требуется», «Manage TLS» — «вступает в силу при следующей загрузке»: планируйте перезагрузку. Политика «Конфигурация компьютера → Административные шаблоны → Сеть → Параметры конфигурации SSL → Порядок наборов шифров SSL» (SSL Cipher Suite Order): список через запятую не длиннее 1023 символов; набор вне списка не используется [MS Learn]. HTTP/2 падает на несовместимых наборах — ECDHE-GCM держите наверху [MS Learn]. Разумно убрать 3DES и `TLS_RSA_WITH_*` (без прямой секретности) — после проверки старых клиентов (Windows 7, старые Java-интеграции) [практика]. Клиент 1С умеет TLS 1.0–1.3 [ИТС-адм разд. 8.9.2]; его наборы шифров не перечислены ⚠.

### 3.5. Кто ходит по старым протоколам

Дополнительное поле журнала (IIS 1709+): переменные `CRYPT_PROTOCOL` (TLS 1.2 = `400`), `CRYPT_CIPHER_ALG_ID`, `CRYPT_HASH_ALG_ID`, `CRYPT_KEYEXCHANGE_ALG_ID` [MS Learn, «IIS Server Variables»]:

```bat
cd /d %windir%\system32\inetsrv
appcmd set config -section:system.applicationHost/sites /+"[name='Default Web Site'].logFile.customFields.[logFieldName='crypt-protocol',sourceName='CRYPT_PROTOCOL',sourceType='ServerVariable']" /commit:apphost
```

[синтаксис — образец MS Learn для `customFields`]. К имени файла журнала добавляется `_x` (`u_ex261020_x.log`) [MS Learn]. Прочие значения уточнены 20.10.2026: переменная — шестнадцатеричное значение `dwProtocol` структуры `SecPkgContext_ConnectionInfo` [MS Learn, «IIS Server Variables»], а в ней `SP_PROT_TLS1_0_SERVER` = `0x40`, `SP_PROT_TLS1_1_SERVER` = `0x100`, `SP_PROT_TLS1_2_SERVER` = `0x400`, `SP_PROT_TLS1_3_SERVER` = `0x1000` [MS Learn, `SecPkgContext_ConnectionInfo`] — то есть в журнале `40`, `100`, `400`, `1000`. Через неделю: `Select-String -Path C:\inetpub\logs\LogFiles\W3SVC1\u_ex*_x.log -Pattern ' 40 | 100 '` и разбор по `c-ip`/`cs(User-Agent)` [практика].

Журнал Schannel — `EventLogging` (DWORD) в `…\SecurityProviders\SCHANNEL`: 0 — нет, 1 — ошибки, 3 — ошибки и предупреждения, 7 — всё; события в журнале «Система»; **после изменения — перезагрузка** [MS Learn]. Уровень 7 включать на время [практика].

### 3.6. Проверка снаружи

```powershell
curl.exe -sI --tlsv1.1 --tls-max 1.1 https://web1c.corp.local/   # после отключения — ошибка рукопожатия
curl.exe -sI --tlsv1.2 --tls-max 1.2 https://web1c.corp.local/   # ответ
curl.exe -sI --tlsv1.3 https://web1c.corp.local/                  # WS 2022+: ответ
```

С Ubuntu: `openssl s_client -connect web1c.corp.local:443 -servername web1c.corp.local -tls1_3 </dev/null | grep -E 'Protocol|Cipher'`; для TLS 1.0/1.1 клиент OpenSSL 3 сам их не предлагает — `-tls1_1 -cipher 'DEFAULT@SECLEVEL=0'` ⚠ [сторонний]. Ключи `curl` — [сторонний]; `curl.exe` проверяет и клиентскую роль Schannel той машины, с которой запускается [практика].

### 3.7. 1С и протоколы

- 1С: TLS 1.0–1.3 и ГОСТ; при TLS 1.3 клиентские сертификаты — только ГОСТ; SSL 3.0 не поддерживается [ИТС-адм разд. 8.9.2].
- Клиентское приложение без особых указаний начинает с TLS 1.3 и понижает версию, если требует веб-сервер; ограничить — `/HttpsForceTLS1_0`, `/HttpsForceTLS1_1`, `/HttpsForceTLS1_2` (несколько сразу — нельзя) [ИТС-адм прил. 7.3.4] или `ForceTLS1_x` в `conf.cfg` [ИТС-адм прил. 3.17.13].
- Клиентский сертификат и ЦС для проверки сервера у тонкого клиента — `/HttpsCert [-windows|-linux|-macos] [-recent|-auto|-choose] [-file <path> -pwd <password>] [-none]`, `/HttpsCA [-windows] [-linux] [-macos] [-file <path>] [-pwd <password>] [-none]` [ИТС-адм прил. 7.3.4]; в свойствах базы — «Параметры настройки сертификатов» [ИТС-адм разд. 5.2.4].
- Ошибки загрузки больших объёмов по HTTPS ИТС лечит включением TLS 1.1/1.2 [ИТС-адм разд. 8.10.2.5] — на WS 2016+ они уже включены; ищите лимиты фильтрации, прокси, тайм-ауты (`1c-windows/03` раздел 8, `iis/03`).

## 4. HSTS и перенаправление HTTP → HTTPS

### 4.1. Способы

| Способ | Код | Плюсы | Минусы | Источник |
|---|---|---|---|---|
| Только привязка 443 | — | нечего перехватывать | `http://` — ошибка соединения | [практика] |
| `<hsts redirectHttpToHttps="true">` | ⚠ не указан | один сайт с 80 и 443 | 1709+; порт отбрасывается — HTTPS только на 443 | [MS Learn, `hsts`] |
| `<httpRedirect>` | 301 / 302 / 307 / 308 | встроенный `Web-Http-Redirect` | на том же сайте — петля; нужен второй сайт только на 80 | [MS Learn] |
| URL Rewrite | 301 / 302 / 303 / 307 (308 нет) | гибкие условия, `globalRules` на весь сервер | ставится отдельно (2.1, iis.net) | [MS Learn; iis.net] |

Для POST (HTTP-сервисы, SOAP), если перенаправление неизбежно, — 307/308: 307 «не даёт клиенту потерять данные POST» [MS Learn]; 301/302 клиенты исторически превращают в GET [практика].

### 4.2. Встроенный HSTS

Атрибуты `system.applicationHost/sites/site/hsts` [MS Learn]: `enabled` (`false`; заголовок добавляется в ответы на **HTTPS**-запросы), `max-age` (`0`), `includeSubDomains` (`false`; «только если все поддомены работают по TLS»), `preload` (`false`; «только если домен подан в список предзагрузки»), `redirectHttpToHttps` (`false`; схема → `https`, порт отбрасывается). Браузеры игнорируют заголовок, пришедший по HTTP, «выключить» HSTS можно лишь ответом `max-age=0` по HTTPS; для `preload` нужен `max-age` ≥ 31 536 000 и `includeSubDomains` [сторонний, MDN].

```bat
cd /d %windir%\system32\inetsrv
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].hsts.enabled:True" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].hsts.max-age:300" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].hsts.redirectHttpToHttps:True" /commit:apphost
```

```powershell
Import-Module IISAdministration
Start-IISCommitDelay
$site = Get-IISConfigSection -SectionPath 'system.applicationHost/sites' | Get-IISConfigCollection | Get-IISConfigCollectionElement -ConfigAttribute @{ 'name' = 'Default Web Site' }
$hsts = Get-IISConfigElement -ConfigElement $site -ChildElementName 'hsts'
Set-IISConfigAttributeValue -ConfigElement $hsts -AttributeName 'max-age' -AttributeValue 31536000
Stop-IISCommitDelay
```

[MS Learn, образцы `hsts`]. Рекомендации [практика]: начинать с `max-age=300`, после проверки всех приложений сайта — год; `includeSubDomains` на `corp.local` не включать (внутренние HTTP-сайты — принтеры, панели ИБП, сервисы без TLS — перестанут открываться); `preload` — только для публичных доменов. Тонкий клиент 1С — не браузер, HSTS на него вряд ли действует ⚠ — адрес в списке баз сразу `https://`.

**WS 2016** (`<hsts>` нет): заголовок через `customHeaders` на сайте, отвечающем только по HTTPS, перенаправление — отдельным HTTP-сайтом с `<httpRedirect>`, либо URL Rewrite с исходящим правилом для `RESPONSE_Strict_Transport_Security` [MS Learn, «HSTS», решения 1–2].

### 4.3. `<httpRedirect>`

Атрибуты [MS Learn]: `enabled` (`false`), `destination`, `exactDestination` (`false` — к назначению дописывается путь), `childOnly` (`false`), `httpResponseStatus` — `Found` (302, по умолчанию), `Permanent` (301), `Temporary` (307), `PermRedirect` (308, IIS 10.0); дочерние `add` (`wildcard`, `destination`). Схема Microsoft — два сайта: HTTP-сайт с `<httpRedirect enabled="true" destination="https://…" httpResponseStatus="Permanent" />` и основной только на 443 [MS Learn, «HSTS», решение 1].

```bat
cd /d %windir%\system32\inetsrv
mkdir C:\inetpub\web1c-http
appcmd add site /name:"web1c-http" /bindings:http/*:80:web1c.corp.local /physicalPath:"C:\inetpub\web1c-http"
appcmd set config "web1c-http" -section:system.webServer/httpRedirect /enabled:"True" /destination:"https://web1c.corp.local" /httpResponseStatus:"PermRedirect"
```

`set config … httpRedirect` — [MS Learn, образец]; `add site /bindings:` — формат `протокол/IP:порт:имя` и образец `APPCMD add site /name:… /bindings:"http/*:81:" /physicalPath:…` [MS Learn, «Getting Started with AppCmd.exe»; уточнено 20.10.2026]. Привязку `*:80:web1c.corp.local` с основного сайта убрать [практика]; склейку пути при `exactDestination="False"` проверьте `curl.exe -sI http://web1c.corp.local/demo/` ⚠.

### 4.4. URL Rewrite

Модуль Microsoft, ставится отдельно (URL Rewrite 2.1, «Works With: IIS 7 … IIS 10») [iis.net]. Правило из статьи Microsoft [MS Learn, «HSTS», решение 2]:

```xml
<system.webServer>
  <rewrite>
    <rules>
      <rule name="Redirect HTTP to HTTPS" stopProcessing="true">
        <match url="(.*)" />
        <conditions><add input="{HTTPS}" pattern="off" /></conditions>
        <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
      </rule>
    </rules>
  </rewrite>
</system.webServer>
```

`HTTPS` = `ON`/`OFF`, `appendQueryString` по умолчанию `true`; `<globalRules>` — только на уровне сервера и ниже не отключаются [MS Learn]. ⚠ `{HTTP_HOST}` берётся из запроса клиента — на сервере с несколькими сайтами пишите имя явно [практика]. Правило не кладите в `web.config` каталога публикации 1С — `webinst` может его перезаписать ⚠ [практика].

## 5. Заголовки ответа и скрытие версии

### 5.1. `customHeaders`

`<httpProtocol><customHeaders>` — `add` (`name`, `value`), `remove`, `clear`; заголовки идут **в каждый ответ** [MS Learn]. Конфигурация IIS по умолчанию содержит `<add name="X-Powered-By" value="ASP.NET" />` [MS Learn, образец `httpProtocol`] — убрать [практика].

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site" -section:system.webServer/httpProtocol /-"customHeaders.[name='X-Powered-By']"
appcmd set config "Default Web Site" -section:system.webServer/httpProtocol /+"customHeaders.[name='X-Content-Type-Options',value='nosniff']"
appcmd set config "Default Web Site" -section:system.webServer/httpProtocol /+"customHeaders.[name='Referrer-Policy',value='strict-origin-when-cross-origin']"
appcmd set config "Default Web Site" -section:system.webServer/httpProtocol /+"customHeaders.[name='X-Frame-Options',value='SAMEORIGIN']"
appcmd list config "Default Web Site" -section:system.webServer/httpProtocol
```

[синтаксис — образец MS Learn `customHeaders`]. Удаление унаследованного `X-Powered-By` на уровне сайта записывает `<remove>` ⚠ [практика]; проверка — `curl.exe -sI https://web1c.corp.local/`. CSP с кавычками надёжнее записать в XML вручную:

```xml
<!-- applicationHost.config, <location path="Default Web Site"> -->
<system.webServer><httpProtocol><customHeaders>
  <add name="Content-Security-Policy" value="frame-ancestors 'self'" />
</customHeaders></httpProtocol></system.webServer>
```

Значения [сторонний, MDN]: `X-Content-Type-Options: nosniff` — браузер не угадывает тип, блокирует скрипт/стиль с неподходящим MIME; `Referrer-Policy: strict-origin-when-cross-origin` (это и умолчание браузеров); `Content-Security-Policy: frame-ancestors 'self' [https://…] | 'none'` — кто может встраивать во фреймы (не наследуется от `default-src`, в `<meta>` не работает); `X-Frame-Options: SAMEORIGIN|DENY` — для старых браузеров, `ALLOW-FROM` устарел, и с ним браузер **игнорирует весь заголовок**; `Strict-Transport-Security` — через `<hsts>` (WS 2019+). Строгий CSP (`script-src`, `default-src`) веб-клиенту 1С не задавайте ⚠ [практика; так же `apache/02`].

### 5.2. Встраивание веб-клиента 1С

ИТС: у приложения веб-клиента `X-Frame-Options` — `sameorigin` (внешний сайт на том же веб-сервере), `allow-from %ВебСайт%` (на разных; протокол, домен, порт внешнего сайта), `deny` (запрет); без тонкой настройки — убедиться, что нет `deny` [ИТС-адм разд. 8.10.2.7]. Так как `ALLOW-FROM` браузеры игнорируют [сторонний MDN], для встраивания с другого сайта [практика]:

```xml
<location path="Default Web Site/demo">
  <system.webServer><httpProtocol><customHeaders>
    <remove name="X-Frame-Options" />
    <add name="Content-Security-Policy" value="frame-ancestors 'self' https://portal.corp.local" />
  </customHeaders></httpProtocol></system.webServer>
</location>
```

`<location>` в `applicationHost.config` надёжнее `web.config` публикации, который перезаписывает `webinst` ⚠. Режим встроенного рабочего места — `/MainWindowMode -EmbeddedWorkplace` [ИТС-адм прил. 7.3.3].

### 5.3. Заголовок `Server`

- **`removeServerHeader`** (`<requestFiltering>`, по умолчанию `false`): «добавлен в IIS 10.0 и не работает в версиях Windows до 1709» — то есть WS 2019+ [MS Learn].
- **`DisableServerHeader`** — DWORD в `HKLM\System\CurrentControlSet\Services\HTTP\Parameters`: `0` (умолчание) — значение приложения или `Microsoft-HTTPAPI/2.0`; `1` — не добавлять к ответам, которые формирует сам http.sys (400, 503); `2` — не добавлять никогда (заголовок приложения останется); после перезапуска службы HTTP [MS Learn].
- На WS 2016 — исходящее правило URL Rewrite, переписывающее `RESPONSE_SERVER` в пустую строку ⚠ [механизм — MS Learn, «Modifying HTTP Response Headers»].

```bat
%windir%\system32\inetsrv\appcmd set config -section:system.webServer/security/requestFiltering /removeServerHeader:"True" /commit:apphost
```

```powershell
New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\HTTP\Parameters' -Name DisableServerHeader -PropertyType DWord -Value 2 -Force
net stop http /y ; net start w3svc         # кратковременный простой всех сайтов!
curl.exe -sI https://web1c.corp.local/ | findstr /i "server x-powered"
```

`/removeServerHeader:"True"` — уточнено 20.10.2026: атрибут `removeServerHeader` (bool, `false`) есть в схеме IIS 10 (`%windir%\system32\inetsrv\config\schema\IIS_schema.xml`), а `/<атрибут>:<значение>` — общая форма `set config` [MS Learn, appcmd]. Microsoft описывает перезапуск как `net stop http`, `net start http`, `net stop iisadmin /y` и запуск остановленных служб [MS Learn]; после — `Get-Service W3SVC, WAS` [практика]. Скрытие версии — гигиена; от уязвимостей защищают обновления Windows [практика].

### 5.4. Ошибки и листинг

`<httpErrors errorMode>`: `DetailedLocalOnly` (умолчание — подробности только с самого сервера), `Custom`, `Detailed` (всем) [MS Learn]. ИТС при безликой «500» советует «Подробные сообщения об ошибках» [ИТС-адм разд. 8.10.2.3] — включайте **временно** или открывайте ошибку браузером на самом сервере: подробная страница раскрывает пути и конфигурацию [практика]. `<directoryBrowse enabled>` по умолчанию `false` [MS Learn] — не включать (403.14 — нормально). Проверка: `appcmd list config "Default Web Site/demo" -section:system.webServer/httpErrors`.

## 6. Аутентификация в IIS: общая схема

### 6.1. Методы и где они настраиваются

Все методы — дочерние элементы `system.webServer/security/authentication`; IIS поддерживает анонимную, Basic, Digest, Windows и два вида сопоставления клиентских сертификатов; включать метод нужно у сайта/приложения после установки компонента [MS Learn, `authentication`].

| Метод | Секция | Компонент | Кто проверяет | Что получает расширение 1С | Раздел |
|---|---|---|---|---|---|
| Анонимная | `anonymousAuthentication` | встроен | никто; запрос от имени `IUSR` или удостоверения пула | ничего — 1С сама запросит Basic (имя/пароль 1С в UTF-8) [ИТС-адм разд. 8.9.1] | 7 |
| Basic | `basicAuthentication` | `Web-Basic-Auth` | Windows (локальные или доменные учётные записи) | те же имя и пароль — должны подходить и к Windows, и к 1С [ИТС-адм разд. 8.9.1] | 8 |
| Windows (Negotiate/NTLM) | `windowsAuthentication` | `Web-Windows-Auth` | Kerberos или NTLM через домен | пользователя ОС; если в запросе есть имя и пароль 1С — используются они [ИТС-адм разд. 8.9.1] | 9 |
| Сертификат клиента → AD | `clientCertificateMappingAuthentication` | `Web-Client-Auth` | AD по сопоставлению сертификата | пользователя ОС ⚠ (для 1С не описано) | 10 |
| Сертификат клиента → правила IIS | `iisClientCertificateMappingAuthentication` | `Web-Cert-Auth` | IIS по таблицам «один к одному» / «многие к одному» | пользователя ОС ⚠ | 10 |
| Digest | `digestAuthentication` | `Web-Digest-Auth` | домен | ⚠ не описано; для 1С не применяется | — |

Порядок, в котором расширение веб-сервера 1С ищет учётные данные после IIS [ИТС-адм разд. 4.3.8.2.3]: заголовок `Authorization: Bearer` (JWT; неудача — отказ), заголовок `Authorization: Basic`, имя и пароль из строки соединения в `default.vrd` (передаются служебными заголовками), и лишь затем — аутентификация ОС. Отсюда практическое правило: **если для пути включена Windows-аутентификация IIS, то Basic-заголовок 1С до расширения не дойдёт** — IIS потребует Negotiate раньше [практика ⚠]. HTTP-сервисам с паролями 1С нужен анонимный IIS на своём пути (9.12).

### 6.2. Блокировка секций и место хранения

- Большинство секций IIS заблокированы на уровне сервера (`overrideModeDefault="Deny"`), в том числе `<windowsAuthentication>` [MS Learn, «How to Use Locking in IIS Configuration»; appcmd: «By default, most of the IIS configuration sections are locked at the server level»]. Поэтому образцы Microsoft для аутентификации всегда пишут с `/commit:apphost` — настройка попадает в `<location path="Сайт/приложение">` в `applicationHost.config` [MS Learn, `windowsAuthentication`].
- Это **полезно для безопасности**: `web.config` в каталоге публикации (его пишет `webinst`, его может изменить тот, у кого есть запись в каталог) не может включить анонимный доступ там, где администратор его выключил. Не разблокируйте секции аутентификации без нужды [практика].
- Разблокировать (если всё же нужно) — `appcmd unlock config -section:<секция>`, заблокировать — `appcmd lock config -section:<секция>`; при блокировке уже существующие переопределения ниже дадут ошибку «нарушение блокировки» (500.19) [MS Learn, appcmd].
- Для правил авторизации можно запретить очистку унаследованных правил ниже: атрибут `lockElements="clear"` [MS Learn, «Understanding IIS URL Authorization»].

Посмотреть действующие значения для конкретного пути:

```bat
cd /d %windir%\system32\inetsrv
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/basicAuthentication
:: где в иерархии что-то задано
appcmd search config "Default Web Site" -section:system.webServer/security/authentication/anonymousAuthentication
```

`list config`, `search config` — [MS Learn, appcmd]. В PowerShell — `Get-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Location 'Default Web Site/demo' -Filter 'system.webServer/security/authentication/windowsAuthentication' -Name enabled` [MS Learn: параметры командлета].

### 6.3. Как сочетаются несколько включённых методов

- Если включена анонимная, IIS не спрашивает учётные данные: запрос обслуживается анонимно, пока ресурс доступен анонимному пользователю [MS Learn: «You must disable Anonymous authentication for any Web site, Web application, or Web service for which you want to enable other authentication methods»].
- Если анонимная выключена, IIS отвечает 401 с заголовками `WWW-Authenticate` для каждого включённого метода (Negotiate, NTLM, Basic) — клиент выбирает сам [практика]. Включённые одновременно Windows и Basic на интрасети — частый источник «в Chrome вход прозрачный, а интеграция шлёт пароль открытым текстом» [практика].
- По умолчанию, если `<providers>` не заданы (`NTAuthenticationProviders` не установлено), IIS шлёт и Negotiate, и NTLM [MS Learn, «Troubleshoot Kerberos failures»].

Для публикации 1С методичка требует **выключить анонимную** при аутентификации ОС [ИТС-мет 5944, 2018]: иначе браузер и тонкий клиент придут анонимно, и 1С покажет окно ввода пароля.

### 6.4. Режимы публикации 1С на одном IIS

| Сценарий | IIS для приложения | 1С | Канал |
|---|---|---|---|
| Пользователи с паролями 1С, OpenID, внешние партнёры | анонимная | пароль 1С / OpenID / OpenID Connect / JWT | только HTTPS [ИТС-адм разд. 8.9.1, 8.2] |
| Вход по доменной учётной записи (SSO) | Windows (Negotiate первым), анонимная — выкл. | аутентификация ОС, пользователь `\\CORP\имя` | HTTPS (Kerberos сам пароль не передаёт, но данные 1С — да) |
| Интеграции HTTP-сервисов с учётной записью 1С | анонимная на `…/demo/hs` | Basic 1С | HTTPS, ограничение по IP (раздел 12) |
| Интеграции от доменной служебной учётной записи | Windows на `…/demo/hs`, `…/demo/odata` | `ИспользоватьАутентификациюОС = Истина` у `HTTPСоединение` [ИТС-адм разд. 4.3.8.2.3] | HTTPS |

Публикация 1С целиком — `1c-windows/03` (разделы 4, 10, 11).

## 7. Анонимная аутентификация

### 7.1. Атрибуты

`<anonymousAuthentication>` [MS Learn]:

| Атрибут | Смысл | Умолчание |
|---|---|---|
| `enabled` | включена ли | `true` |
| `userName` | учётная запись анонимных запросов; **пустая строка — удостоверение пула приложений** | `IUSR` |
| `password` | пароль учётной записи (задавать только через `appcmd` или диспетчер — тогда он шифруется в конфигурации) | — |
| `logonMethod` | тип входа: `Interactive` (0), `Batch` (1), `Network` (2), `ClearText` (3) | `ClearText` |

Атрибута `defaultLogonDomain` у анонимной аутентификации нет — ни в справочнике, ни в схеме IIS 10 (он есть у `basicAuthentication` и `iisClientCertificateMappingAuthentication`) [MS Learn; `IIS_schema.xml`, сверено 20.10.2026]. (В таблице атрибутов справочника имя записано как `username`, в образцах, в `applicationHost.config` и в схеме IIS 10 — `userName` [MS Learn; `IIS_schema.xml`]; конфигурация IIS к регистру имён атрибутов чувствительна ⚠ — используйте `userName`.)

- `IUSR` — встроенная учётная запись без пароля, одинаковая на всех компьютерах (имя не локализуется); в сети действует анонимно, как `LocalService`; если анонимному пользователю нужен доступ к сетевым ресурсам — задайте отдельную учётную запись [MS Learn, «Understanding Built-In User and Group Accounts»].
- `IIS_IUSRS` — встроенная группа, её SID IIS автоматически добавляет в маркер рабочего процесса; `IUSR` в эту группу не входит [MS Learn; про `IUSR` — практика ⚠].
- Рекомендация Microsoft для изоляции контента — не полагаться на общий `IUSR` [MS Learn, «Secure Content in IIS Through File System ACLs»]. Простой способ изолировать сайты — `userName=""`: анонимные запросы идут от `IIS AppPool\<пул>`, права выдаются только ему [практика].

### 7.2. Для 1С

- Анонимный IIS + аутентификация 1С (пароль, OpenID, JWT) — самый частый режим публикации; канал — **только HTTPS**, иначе пароли 1С идут в Base64 открытым текстом [ИТС-адм разд. 8.9.1; ИТС-мет 5977, 2020].
- Права на `bin` версии 1С и каталог файловой базы в документации выдаются `IIS_IUSRS` [ИТС-адм разд. 8.4.3.2.1]; при `userName="IUSR"` анонимные запросы читают файлы от `IUSR` ⚠ (что именно выполняет `wsisapi.dll` под олицетворением, ИТС не уточняет). Если ACL сужены вручную и публикация отвечает 401.3 — сначала проверьте `userName` и права `IUSR`/пула (`1c-windows/03`, раздел 6) [практика].
- Включать анонимную вместе с Windows на одном пути для 1С бессмысленно (6.3).

### 7.3. Команды

```bat
cd /d %windir%\system32\inetsrv
:: анонимные запросы публикации — от удостоверения пула (изоляция)
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"True" /userName:"" /commit:apphost
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication
:: выключить анонимную (для аутентификации ОС)
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"False" /commit:apphost
```

Синтаксис — образцы [MS Learn, `anonymousAuthentication`] (`/enabled`, `/userName`, `/commit:apphost`); пустое значение `/userName:""` — [практика ⚠].

## 8. Basic

### 8.1. Атрибуты и поведение

`<basicAuthentication>` [MS Learn]: `enabled` (по умолчанию `false`), `defaultLogonDomain` (домен для имён без домена), `realm` (область в заголовке `WWW-Authenticate`), `logonMethod` (`Interactive`, `Batch`, `Network`, `ClearText`; по умолчанию `ClearText` — «сохраняет имя и пароль в пакете аутентификации, что позволяет серверу обращаться к другим сетевым серверам, олицетворяя клиента»).

- Basic «передаёт имена и пароли по сети в незашифрованном виде» — только вместе с SSL [MS Learn]. Требовать HTTPS у приложения — `<access sslFlags="Ssl">` (на HTTP — ответ 403.4 «SSL required») [MS Learn, `access`, коды состояния].
- Basic проверяет **учётную запись Windows**; неудачи видны в журнале «Безопасность» как события 4625, удачи — 4624; тип входа `ClearText` соответствует типу 8 «NetworkCleartext» [MS Learn, события 4624/4625] (уточнено 20.10.2026: справочник IIS отсылает к функции `LogonUser`, и описание `ClearText` в нём дословно совпадает с описанием `LOGON32_LOGON_NETWORK_CLEARTEXT` [MS Learn, `LogonUser`]).
- Риски [практика]: перебор паролей доменных учётных записей через опубликованный сайт и блокировка учётных записей по политике домена. Минимум — ограничить по IP (раздел 12) и не публиковать Basic на IIS в Интернет.

### 8.2. Для 1С

Basic на IIS и «Basic 1С» — разные вещи. При Basic на IIS имя и пароль проверяет Windows, затем расширение 1С использует их же — пользователь должен существовать и в Windows, и в 1С с тем же паролем [ИТС-адм разд. 8.9.1]. Обычный путь — анонимный IIS, тогда 1С сама запрашивает Basic и проверяет своих пользователей [ИТС-адм разд. 8.9.1]. Практически Basic на IIS нужен только для статических ресурсов без своей аутентификации [практика].

### 8.3. Команды

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/files" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"False" /commit:apphost
appcmd set config "Default Web Site/files" -section:system.webServer/security/authentication/basicAuthentication /enabled:"True" /defaultLogonDomain:"CORP" /realm:"corp.local" /commit:apphost
appcmd set config "Default Web Site/files" -section:system.webServer/security/access /sslFlags:"Ssl" /commit:apphost
appcmd list config "Default Web Site/files" -section:system.webServer/security/authentication/basicAuthentication
```

`/enabled`, `/commit:apphost`, `access /sslFlags:"Ssl"` — образцы [MS Learn]; `/defaultLogonDomain`, `/realm` — имена атрибутов [MS Learn], форма команды — [практика].

Проверка: `curl.exe -sI http://web1c.corp.local/files/` → 403 (подстатус 4 — в журнале); `curl.exe -sI https://web1c.corp.local/files/` → 401 с `WWW-Authenticate: Basic realm="corp.local"` [практика].

## 9. Проверка подлинности Windows: Negotiate, NTLM, Kerberos

### 9.1. Атрибуты и поставщики

`<windowsAuthentication>` — уровни сайта, приложения, виртуального каталога, только в `applicationHost.config` (секция заблокирована) [MS Learn]:

| Атрибут / элемент | Смысл | Умолчание |
|---|---|---|
| `enabled` | включена ли | `false` |
| `useKernelMode` | аутентификация в режиме ядра (http.sys): быстрее и снимает проблемы с пулами под своей учётной записью; «не выключайте, если используете Kerberos и своё удостоверение пула» | `true` |
| `useAppPoolCredentials` | расшифровывать билет Kerberos ключом **удостоверения пула**, сохраняя режим ядра | `false` (атрибута нет в таблице справочника, но он есть в схеме IIS 10 с умолчанием `false` — подтверждено 20.10.2026 по `IIS_schema.xml`; описан в статье поддержки) |
| `authPersistNonNTLM` | `true` — не-NTLM (Kerberos) аутентифицируется один раз на TCP-соединение; `false` — на каждый запрос | `false` |
| `authPersistSingleRequest` | `true` — аутентификация живёт один запрос, затем повторная | `false` |
| `<providers>` | список поставщиков: `Negotiate` («попытается использовать Kerberos, если доступен»), `NTLM`; список нельзя расширить | `Negotiate`, `NTLM` |
| `<extendedProtection>` | Extended Protection (IIS 7.5+) | `tokenChecking="None"` |

Источники: справочник `windowsAuthentication`, `providers` [MS Learn]; `useAppPoolCredentials` — [MS Learn, «Troubleshoot Kerberos failures»]. ⚠ Справочник (и схема IIS 10) даёт `authPersistNonNTLM` = `false` (Kerberos «по запросу»), статья поддержки — что с Windows Server 2012 R2 Kerberos по умолчанию «по сеансу»; это вопрос производительности, а не безопасности [практика].

Значение поставщика `Negotiate:Kerberos` (только Kerberos, без отката) встречается в практике, но в справочнике `<providers>` не описано ⚠ — не используйте его без проверки.

### 9.2. Как работает Kerberos для IIS

По статье поддержки Microsoft [MS Learn, «Troubleshoot Kerberos failures»]:

1. Браузер строит SPN из адреса (`HTTP/<имя узла>`); если имя — псевдоним CNAME, старые браузеры (IE) сначала разрешают его в каноническое имя и просят билет к `HTTP/<каноническое имя>`. Порт в SPN по умолчанию не включается.
2. LSASS клиента запрашивает у контроллера домена билет к этому SPN; билет зашифрован ключом **учётной записи, которой принадлежит SPN**.
3. Браузер отправляет билет в заголовке `Authorization: Negotiate …` (запрос с Kerberos больше 2000 байт, с NTLM — меньше 1400).
4. IIS расшифровывает билет: в режиме ядра — ключом учётной записи компьютера; с `useAppPoolCredentials="true"` или без режима ядра — ключом удостоверения пула. Не тот ключ → `KRB_AP_ERR_MODIFIED`.
5. Если контроллер не знает SPN, Kerberos не используется и возможен откат на NTLM; если контроллер недоступен — отката нет.

**Без явного SPN** Kerberos работает только при удостоверениях пула `NetworkService`, `ApplicationPoolIdentity` или системных — используется SPN, созданный при вводе компьютера в домен [MS Learn]. Учётная запись компьютера несёт SPN `HOST/<имя>`, которым покрывается класс `HTTP` ⚠ [практика: сопоставление классов служб в AD].

### 9.3. Какой SPN и на какой учётной записи

| Как обращаются к сайту | Удостоверение пула | Что сделать | Источник |
|---|---|---|---|
| по имени компьютера `WEB01` / `WEB01.corp.local` | `ApplicationPoolIdentity` (по умолчанию) | ничего | [MS Learn] |
| по отдельной A-записи `web1c.corp.local` → `WEB01` | `ApplicationPoolIdentity` | `setspn -S HTTP/web1c.corp.local CORP\WEB01$` (и короткое имя, если им пользуются) | [практика ⚠: SPN для псевдонима на учётной записи компьютера; `setspn -S` — MS Learn] |
| по CNAME `web1c` → `WEB01` | любое | браузер может просить `HTTP/WEB01…` — работает как первая строка; надёжнее сделать A-запись | [MS Learn: поведение IE; для других браузеров ⚠] |
| ферма из нескольких IIS под общим именем (NLB или L4-балансировщик; публикации 1С с `-osauth` через ARR не пропускать — см. `03-…`, раздел 7.5) | общая доменная учётная запись `CORP\svc-iis-1c` во всех пулах | `setspn -S HTTP/web1c.corp.local CORP\svc-iis-1c` + `useAppPoolCredentials="true"` | [MS Learn] |
| нестандартный порт (`:8443`) с разными удостоверениями | — | SPN с портом и ключ браузера `FEATURE_INCLUDE_PORT_IN_SPN_KB908209` (IE) | [MS Learn] |

Правила [MS Learn]: один SPN — одна учётная запись (дубли дают `KRB_AP_ERR_MODIFIED`); `setspn -S` проверяет дубли перед добавлением, `setspn -X` ищет их в домене. Регистрирует SPN администратор домена (или тот, кому делегировано право записи SPN) — см. `1c-windows/04`, раздел 3.2.

```cmd
:: на контроллере домена или с RSAT, от имени администратора домена
setspn -S HTTP/web1c.corp.local CORP\WEB01$
setspn -S HTTP/web1c CORP\WEB01$
setspn -L CORP\WEB01$
setspn -Q HTTP/web1c.corp.local
setspn -X
```

Пул под доменной учётной записью и SPN на ней (ферма):

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /useAppPoolCredentials:"True" /commit:apphost
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication
```

Атрибут — [MS Learn, «Troubleshoot Kerberos failures»; схема `IIS_schema.xml`]; форма команды — общая форма `set config … /<атрибут>:<значение>` [MS Learn, appcmd; уточнено 20.10.2026]. Учётная запись пула задаётся как `SpecificUser` (`processModel.userName`/`password` через `appcmd` или диспетчер, чтобы пароль зашифровался) [MS Learn, `processModel`]; групповые управляемые учётные записи (gMSA) документация `processModel` упоминает как возможные («Managed service accounts can be used») [MS Learn], для публикации 1С они не описаны ⚠.

### 9.4. Включение и порядок поставщиков

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"False" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /enabled:"True" /commit:apphost
:: оставить только Negotiate (без отката на NTLM) — только если все клиенты гарантированно получают Kerberos!
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /-"providers.[value='NTLM']" /commit:apphost
:: вернуть NTLM
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /+"providers.[value='NTLM']" /commit:apphost
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication
```

Образцы включения и удаления поставщика (`/-"providers.[value='Negotiate']"`) — [MS Learn, `providers`]; удаление именно `NTLM` — по тому же образцу [практика]. После изменения поставщиков методичка 1С делает `iisreset` [ИТС-мет 5944, 2018].

Когда не оставлять одного Negotiate [MS Learn, `windowsAuthentication`; практика]: клиенты не в домене или без связи с контроллером (Kerberos «требует подключения к Active Directory, что невозможно в Интернете»), обращение по IP-адресу (SPN не найдётся), сайт на том же компьютере, что и браузер (для Kerberos нужен `DisableLoopBackCheck` [MS Learn]). Microsoft больше не развивает NTLM, NTLMv1 удалён в Windows Server 2025 — подробности в `1c-windows/04`, раздел 2.3.

### 9.5. Браузеры и зоны

- Встроенная проверка подлинности выполняется автоматически только для зон «Местная интрасеть» и «Надёжные сайты»; Kerberos-**делегирование** браузер разрешает тоже только для них (флаг `ISC_REQ_DELEGATE`) [MS Learn, «Troubleshoot Kerberos failures» — для Internet Explorer; для Edge/Chrome — политики].
- Edge — политики `AuthServerAllowlist` (кому отвечать) и `AuthNegotiateDelegateAllowlist` (кому делегировать); Firefox — `network.negotiate-auth.trusted-uris`, `network.negotiate-auth.delegation-uris`, `network.automatic-ntlm-auth.trusted-uris` [ИТС-адм разд. 9.2.2; MS Learn] — таблица в `1c-windows/03`, раздел 10.3.
- Тонкий клиент 1С через веб-сервер: `/WSA+` (по умолчанию) — сначала аутентификация ОС; адрес базы — в надёжные сайты [ИТС-адм разд. 4.3.8.2.2, 6.2.10.3].

### 9.6. Проверка: Kerberos или NTLM

```powershell
# на клиенте (обычный пользователь домена)
klist purge                                   # сбросить кеш (потом билеты получатся заново)
klist get HTTP/web1c.corp.local               # должен выдать билет; ошибка — нет SPN или он у другой учётной записи
Invoke-WebRequest -Uri 'https://web1c.corp.local/demo/' -UseDefaultCredentials -UseBasicParsing | Select-Object StatusCode
klist | Select-String 'HTTP/web1c'            # билет к HTTP/web1c.corp.local появился — значит, Kerberos
```

`klist get`, `klist purge` — [MS Learn]; `Invoke-WebRequest -UseDefaultCredentials` — [практика]. Признаки [MS Learn, «Troubleshoot Kerberos failures»; практика]:

- в инструментах разработчика браузера заголовок `Authorization: Negotiate YII…` длиной в тысячи символов — Kerberos; `Negotiate TlRMTVNT…` / `NTLM TlRMTVNT…` — NTLM (`TlRMTVNT` — Base64 от `NTLMSSP`) [практика];
- в журнале IIS: первый запрос `401 2 5` (подстатус 2 — «вход не удался из-за настройки сервера», то есть клиенту отправлен вызов), следующий — `200` с именем в `cs-username`; повторяющиеся `401 1` с `sc-win32-status` `2148074245` — неудача входа [MS Learn: такие строки приведены в статье];
- в журнале «Безопасность» сервера IIS событие 4624 содержит «Пакет проверки подлинности» (`Kerberos` или `NTLM`) ⚠ (поле есть в событии, интерпретация — практика);
- `KRB_AP_ERR_MODIFIED` в журнале «Система» — дубль SPN или не тот ключ (9.2).

### 9.7. HTTP/2 и аутентификация Windows

«Проверка подлинности Windows (NTLM/Kerberos/Negotiate) не поддерживается с HTTP/2. В этом случае IIS откатывается на HTTP/1.1» [MS Learn, «HTTP/2 on IIS»]. Выключать HTTP/2 у привязки (`DisableHTTP2`) ради Windows-аутентификации не нужно; если наблюдаются сбои именно на переключении, флаг `-SslFlag DisableHTTP2` (1809+) — диагностический шаг [практика ⚠].

### 9.8. Большие билеты → 400 «Request header too long»

У пользователя во множестве групп AD билет Kerberos растёт и не помещается в лимиты http.sys: ответ «HTTP 400 — Bad Request (Request header too long)» ещё до IIS [MS Learn, «HTTP 400 … Request Header too long»]. Решения Microsoft:

1. уменьшить число групп пользователя;
2. увеличить `MaxFieldLength` и `MaxRequestBytes` (`HKLM\System\CurrentControlSet\Services\HTTP\Parameters`, DWORD) до 4/3·T + 200 байт, где T — размер билета (Base64 увеличивает данные на треть); максимумы — 65534 (справочник http.sys: диапазон 64–65534) ⚠ или 65536 (статья о 400) и 16 777 216; изменения применяются после **перезапуска службы HTTP** и зависимых служб IIS [MS Learn].

Microsoft называет изменение этих ключей «крайне опасным» (http.sys тратит больше памяти) — ставьте рассчитанное значение, а не максимум [MS Learn]. Команды и умолчания (16 384) — `1c-windows/03`, раздел 8.2.

### 9.9. Делегирование (двойной переход) для 1С

Когда IIS и сервер 1С на разных компьютерах, модуль 1С обращается к кластеру **от имени пользователя** — нужен второй «переход» Kerberos [ИТС-мет 5944, 2018; ИТС-КС разд. 3.1.6.1.1]. Признак отсутствия делегирования — в техжурнале сервера 1С `DstUserName2: NT AUTHORITY\ANONYMOUS LOGON` и затем `EXCP` «Идентификация пользователя не выполнена» [ИТС-мет 5944].

Что нужно со стороны IIS (AD и сервер 1С — `1c-windows/04`, раздел 3.3):

1. Браузер получил **Kerberos**, а не NTLM (9.6): NTLM делегировать нельзя [ИТС-КС разд. 3.1.6.1.1].
2. Учётной записи, расшифровывающей билет, разрешено делегирование: при `ApplicationPoolIdentity` и режиме ядра — **компьютеру `WEB01`**; при пуле под доменной учётной записью — **ей** [ИТС-КС разд. 3.1.6.1.1; MS Learn: «The user account for the IIS application pool hosting your site must have the Trusted for delegation flag»]. Методичка 1С ставит «Доверять компьютеру делегирование любых служб (только Kerberos)» [ИТС-мет 5944]; безопаснее ограниченное (KCD) только к SPN службы 1С — `srv1c/…` на Windows-кластере или `usr1cv8/<FQDN>` на Linux-кластере пользователя ⚠ (KCD для 1С описан только в общем виде).
3. Браузеру разрешено делегировать (9.5).
4. Клиентский компьютер перезагружен после изменений; серверы перезагружать не нужно [ИТС-мет 5944].
5. В тонком клиенте схема работает с 8.3.10.2620 [ИТС-мет 5944].

⚠ Ограниченное делегирование «только Kerberos» не сработает, если браузер откатился на NTLM; вариант «с любым протоколом» (переход протоколов) расширяет права учётной записи IIS — обсуждайте с администратором домена [практика]. Межлесное неограниченное делегирование отключено обновлениями Windows Server марта и июля 2019 года [MS Learn, «Troubleshoot Kerberos failures»].

**Смешанная среда пользователя** (IIS на Windows, кластер `srv-1c-app` на Ubuntu): Linux-сервер 1С принимает аутентификацию ОС только по Kerberos с keytab `usr1cv8/<FQDN>` [`1c-windows/04`, раздел 4]; через IIS — только при делегировании от `WEB01$` к этому SPN; документация 1С такой сценарий не описывает ⚠. Альтернатива без двойного перехода — публикация на Apache на самом Linux-сервере (`../1c/05`, `apache/02` раздел 10).

### 9.10. Extended Protection (защита от ретрансляции)

Расширенная защита связывает аутентификацию Windows с TLS-каналом (токен привязки канала, CBT) или с ожидаемым SPN — против атак «человек посередине» и ретрансляции учётных данных [MS Learn, `extendedProtection`].

| Атрибут | Значения | Умолчание |
|---|---|---|
| `tokenChecking` | `None` (0) — не проверять CBT, как до появления функции; `Allow` (1) — проверять у тех, кто поддерживает; `Require` (2) — требовать от всех | `None` |
| `flags` | `None` (0); `Proxy` (1) — часть пути через прокси или прямое HTTP; `NoServiceNameCheck` (2) — не проверять SPN; `AllowDotlessSpn` (4) — разрешить SPN без точки (NetBIOS; небезопасно); `ProxyCohosting` (32) — весь путь по HTTP, только вместе с `Proxy` | `None` |
| `<spn name="HTTP/…">` | ожидаемые SPN (каждый с префиксом `HTTP/`), в том числе имя прокси | — |

Сценарии из документации [MS Learn]: клиент → сервер по SSL — `flags="None"` (проверяется CBT); через прокси по SSL на всём пути или **SSL-разгрузка на прокси** — `Proxy` (проверяется SPN, CBT нет); по HTTP — `Proxy, ProxyCohosting`.

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /extendedProtection.tokenChecking:"Allow" /extendedProtection.flags:"None" /commit:apphost
:: за ARR / балансировщиком с разгрузкой TLS:
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /extendedProtection.flags:"Proxy" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /+"extendedProtection.[name='HTTP/web1c.corp.local']" /commit:apphost
```

Образцы — [MS Learn, `extendedProtection`]. В диспетчере IIS: «Проверка подлинности Windows → Дополнительные параметры → Расширенная защита: Откл./Принимать/Требуется» [MS Learn]. Начинайте с `Allow`; `Require` — после проверки всех клиентов: поддержка CBT тонким клиентом 1С и HTTP-клиентами интеграций не описана ⚠. Схемы с ARR — `iis/03`.

### 9.11. Для 1С: аутентификация ОС в веб-клиенте и тонком клиенте — коротко

По [ИТС-мет 5944, 2018] и [ИТС-адм разд. 8.9.1] (подробно — `1c-windows/03`, раздел 10; AD — `1c-windows/04`, раздел 3):

1. Компонент `Web-Windows-Auth`; публикация с флажком «Использовать аутентификацию операционной системы» или `webinst … -osauth`.
2. У приложения публикации: анонимная — выкл., Windows — вкл., первым поставщиком `Negotiate`; `iisreset`.
3. SPN `HTTP/<имя публикации>` — раздел 9.3; браузеры — 9.5.
4. У пользователя ИБ — аутентификация ОС и имя вида `\\CORP\ivanov`; точное написание — по свойству `DstUserName2` события `CONN` техжурнала [ИТС-мет 5944].
5. Разнесённые IIS и кластер — делегирование (9.9).
6. Пользователи с огромным числом групп — 9.8.

### 9.12. Разная аутентификация для разных путей публикации

Настройки аутентификации задаются на уровне сайта, приложения или виртуального каталога [MS Learn]; `<location path>` в `applicationHost.config` может указывать и на путь внутри приложения [практика]. Так можно оставить веб-клиенту SSO, а HTTP-сервисам — пароли 1С:

```bat
cd /d %windir%\system32\inetsrv
:: веб-клиент и тонкий клиент — Windows
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"False" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /enabled:"True" /commit:apphost
:: HTTP-сервисы — анонимный IIS, Basic 1С (плюс ограничение по IP — раздел 12)
appcmd set config "Default Web Site/demo/hs" -section:system.webServer/security/authentication/windowsAuthentication /enabled:"False" /commit:apphost
appcmd set config "Default Web Site/demo/hs" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"True" /commit:apphost
appcmd list config "Default Web Site/demo/hs" -section:system.webServer/security/authentication/anonymousAuthentication
```

⚠ Работа `<location>` для URL-пути без физического каталога (`/demo/hs` обрабатывает `wsisapi.dll`) и поведение 1С в такой схеме не проверялись — проверьте на стенде запросом `curl.exe -sI -u user:pass https://web1c.corp.local/demo/hs/<сервис>/…`.

## 10. Клиентские сертификаты (взаимный TLS)

### 10.1. Требование сертификата: `<access sslFlags>`

`system.webServer/security/access`, атрибут `sslFlags` (по умолчанию `None`) [MS Learn]:

| Значение | Смысл |
|---|---|
| `None` | SSL не требуется |
| `Ssl` | требовать SSL (на HTTP — 403.4) |
| `SslNegotiateCert` | принимать клиентский сертификат (если клиент его предъявит) |
| `SslRequireCert` | требовать клиентский сертификат (нет — 403.7) |
| `SslMapCert` | «включить сопоставление сертификата» — есть только в справочнике; в схеме IIS 10 такого флага нет (флаги: `None` 0, `Ssl` 8, `SslNegotiateCert` 32, `SslRequireCert` 64, `Ssl128` 256 — `IIS_schema.xml`, сверено 20.10.2026), сопоставление включается секциями из 10.2 |
| `Ssl128` | требовать 128-битное шифрование (наследие; современные наборы и так сильнее) |

Значения комбинируются через запятую (`"Ssl, SslNegotiateCert"`) [MS Learn, образцы]. Ошибки клиентских сертификатов в журнале IIS [MS Learn, «HTTP status code overview»]: 403.7 — сертификат нужен, но не предъявлен; 403.12 — сопоставленному пользователю отказано в доступе; 403.13 — сертификат отозван; 403.16 — недоверенный или недействительный; 403.17 — истёк или ещё не действует.

### 10.2. Сопоставление сертификата пользователю

| Способ | Секция | Требования | Особенности |
|---|---|---|---|
| Через AD | `clientCertificateMappingAuthentication` (`enabled`) | сервер и пользователи в домене | медленнее (обращение к AD); «чтобы настройка вступила в силу, задавайте её в диспетчере IIS; иначе — перезапуск веб-сервера» |
| Средствами IIS, «один к одному» | `iisClientCertificateMappingAuthentication/oneToOneMappings/add` (`certificate` — Base64 открытой части **без переносов строк**, `userName`, `password`, `enabled`) | не нужен домен | сертификат после перевыпуска не совпадёт — сопоставление обновлять |
| Средствами IIS, «многие к одному» | `…/manyToOneMappings/add` (`name`, `permissionMode` `Allow`/`Deny`, `userName`, `password`) с `rules/add` (`certificateField`, `certificateSubField`, `matchCriteria`, `compareCaseSensitive`) | не нужен домен | например, все сертификаты с `Subject` `O=Corp` → одна учётная запись |

Атрибуты самой секции IIS-сопоставления: `enabled` (по умолчанию `false`), `oneToOneCertificateMappingsEnabled` и `manyToOneCertificateMappingsEnabled` (по умолчанию `true`), `logonMethod` (`ClearText`), `defaultLogonDomain` [MS Learn]. Пароли в сопоставлениях задавайте через `appcmd`/диспетчер — тогда они шифруются [MS Learn].

На уровне Schannel сопоставление управляется параметром `CertificateMappingMethods` (биты: Subject/Issuer 0x1, Issuer 0x2, UPN 0x4, S4U2Self 0x8, S4U2Self Explicit 0x10; по умолчанию включены только S4U2Self и S4U2Self Explicit) [MS Learn, «TLS registry settings»].

Образец «многие к одному» из документации (имена — свои):

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/partners" -section:system.webServer/security/authentication/iisClientCertificateMappingAuthentication /enabled:"True" /manyToOneCertificateMappingsEnabled:"True" /commit:apphost
appcmd set config "Default Web Site/partners" -section:system.webServer/security/authentication/iisClientCertificateMappingAuthentication /+"manyToOneMappings.[name='Partners',enabled='True',permissionMode='Allow',userName='CORP\svc-partners',password='<пароль>']" /commit:apphost
appcmd set config "Default Web Site/partners" -section:system.webServer/security/authentication/iisClientCertificateMappingAuthentication /+"manyToOneMappings.[name='Partners'].rules.[certificateField='Subject',certificateSubField='O',matchCriteria='Partner LLC',compareCaseSensitive='True']" /commit:apphost
appcmd set config "Default Web Site/partners" -section:system.webServer/security/access /sslFlags:"Ssl, SslNegotiateCert" /commit:apphost
```

[MS Learn, образец `iisClientCertificateMappingAuthentication`]. Пароль в командной строке остаётся в истории консоли — вводите его в диспетчере IIS или очищайте историю [практика].

### 10.3. Сторона http.sys

Параметры записи `netsh http add|update sslcert` для клиентских сертификатов [MS Learn, `netsh http`]: `clientcertnegotiation=enable|disable` (по умолчанию **disabled** — сертификат запрашивается не при рукопожатии, а позже, по требованию приложения), `verifyclientcertrevocation`, `verifyrevocationwithcachedclientcertonly`, `revocationfreshnesstime`, `urlretrievaltimeout`, `sslctlidentifier` / `sslctlstorename` (список доверия CTL — какие ЦС принимаются), `dsmapperusage` (сопоставление через AD).

- ⚠ В TLS 1.3 нет повторного согласования, которым IIS запрашивает сертификат «по требованию»; на Windows Server 2022+ при `SslNegotiateCert`/`SslRequireCert` у отдельного пути возможны отказы — тогда включают `clientcertnegotiation=enable` у привязки или выключают TLS 1.3 у неё (`DisableTLS13`) [практика, документацией не подтверждено].
- `SendTrustedIssuerList` (DWORD в `…\SCHANNEL`): по умолчанию сервер **не** отправляет клиенту список доверенных ЦС (с Windows Server 2012) — тогда Edge показывает пользователю все его сертификаты, а не только подходящие; `1` — отправлять [MS Learn].
- При проверке клиентских сертификатов IIS по умолчанию не скачивает недостающие промежуточные сертификаты по AIA (`CertChainCacheOnlyUrlRetrieval` = 1 в `HKLM\System\CurrentControlSet\Services\HTTPFilter\Parameters`); `0` — разрешить [MS Learn, «Http.sys registry settings»]. Проще — положить промежуточные сертификаты ЦС клиентов в хранилище компьютера [практика].

### 10.4. Для 1С

- Тонкий клиент умеет предъявлять клиентский сертификат: из файла, из хранилища Windows/macOS, из каталога Linux (`/HttpsCert …`, окно «Параметры настройки сертификатов») [ИТС-адм прил. 7.3.4, разд. 5.2.4]; веб-клиент — сертификатом из хранилища браузера [ИТС-адм разд. 4.3.9.2].
- Схемы [ИТС-адм разд. 4.3.9.2]: если сервер требует клиентский сертификат и знает корневые ЦС, а клиент сертификата не предъявляет — соединение «не поддерживается»; проверка обеих сторон — когда у обоих есть сертификаты и списки корневых ЦС.
- **TLS 1.3**: клиентские сертификаты 1С поддерживает только ГОСТ [ИТС-адм разд. 8.9.2], а клиент без ключей `/HttpsForceTLS*` начинает с TLS 1.3 [ИТС-адм прил. 7.3.4]. На Windows Server 2022/2025 (TLS 1.3 включён) для RSA-сертификатов тонкого клиента: флаг `DisableTLS13` у привязки (2.3) или `/HttpsForceTLS1_2` на клиенте ⚠ (вывод из двух утверждений ИТС, на стенде не проверялся).
- Программно: защищённое соединение `WSОпределения`/`WSПрокси` — параметр `ЗащищенноеСоединение` с объектом `ЗащищенноеСоединениеOpenSSL` [ИТС-адм разд. 8.9.2]; клиентский сертификат в нём — см. синтакс-помощник версии ⚠.

## 11. Авторизация: правила URL Authorization

### 11.1. Как устроено

- Компонент `Web-Url-Auth`, модуль `%windir%\system32\inetsrv\urlauthz.dll`, секция `system.webServer/security/authorization`; применяется ко **всему** содержимому (в отличие от `system.web/authorization` ASP.NET, который действует только для управляемых обработчиков) [MS Learn, «Understanding IIS URL Authorization»].
- Правило `<add>`: `accessType` (`Allow`/`Deny`, обязательный), `users` (через запятую; `*` — все, `?` — анонимные), `roles` (группы), `verbs` (методы HTTP; пусто — все) [MS Learn, `authorization/add`]. Атрибут секции `bypassLoginPages` (по умолчанию `true`) — для страницы входа Forms [MS Learn].
- **Порядок вычисления** [MS Learn]: сначала все запрещающие правила начиная с родительского уровня, затем разрешающие начиная с родителя, внутри уровня — по порядку записи. Значит, запрет, заданный на сайте, нельзя «перебить» разрешением в приложении.
- Унаследованное правило «разрешить всем» в образцах Microsoft убирают элементом `<remove users="*" roles="" verbs="" />`, затем добавляют свои разрешения [MS Learn, образцы]; справочник `authorization` называет удаляемое правило «настройкой IIS по умолчанию, разрешающей доступ всем пользователям» (уточнено 20.10.2026), точный вид на своём сервере — `appcmd list config -section:system.webServer/security/authorization`.
- Учётные записи и группы — в виде `<домен или компьютер>\<имя>` (`CORP\1C-Web-Users`) [MS Learn, «Using Domain Accounts and Groups»]. Запрет очистки унаследованных правил ниже — `<authorization lockElements="clear">` [MS Learn].

### 11.2. Когда это работает

URL Authorization проверяет **пользователя IIS**. При анонимном IIS и аутентификации средствами 1С IIS видит только `IUSR`/пул — правила по группам бесполезны, права даёт сама 1С [практика]. Полезные случаи: публикация 1С с аутентификацией ОС (пустить в веб-клиент только группу), статические сайты и внутренние инструменты с Windows-аутентификацией.

### 11.3. Примеры

Только группа `CORP\1C-Web-Users` в веб-клиент (аутентификация Windows уже включена):

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authorization /-"[users='*',roles='',verbs='']"
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authorization /+"[accessType='Allow',roles='CORP\1C-Web-Users']"
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authorization /+"[accessType='Deny',users='?']"
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authorization
```

Образец разрешающего правила для роли — [MS Learn, `authorization`]; удаление унаследованного «всем» и запрет анонимных — по тому же синтаксису (уточнено 20.10.2026: ключ коллекции в схеме IIS 10 — `users` + `roles` + `verbs`, как в образце `<remove users="*" roles="" verbs="" />`). Отказ в доступе по правилу — ответ 401 с подстатусом ⚠ (в справочнике кодов для URL Authorization отдельный подстатус не приведён; в журнале смотрите `sc-substatus`).

Чтение — всем аутентифицированным, запись — только группе интеграций, на служебном сайте с Windows-аутентификацией. Из-за порядка вычисления **нельзя** писать «Deny всем на POST» и «Allow группе на POST»: запрет сработает раньше и закроет запись и группе. Правильно — обойтись одними разрешениями [порядок — MS Learn; конструкция — практика ⚠: что запрос, не подошедший ни под одно разрешение, отклоняется, документация прямо не формулирует]:

```xml
<location path="Intranet/api">
  <system.webServer>
    <security>
      <authorization>
        <remove users="*" roles="" verbs="" />
        <add accessType="Allow" users="*" verbs="GET,HEAD" />
        <add accessType="Allow" roles="CORP\Integration-Writers" />
        <add accessType="Deny" users="?" />
      </authorization>
    </security>
  </system.webServer>
</location>
```

### 11.4. NTFS тоже авторизация

Для статических файлов IIS проверяет права NTFS пользователя запроса: отказ — 401.3 «Unauthorized due to ACL on resource» [MS Learn, коды состояния]. Права публикации 1С — `1c-windows/03`, раздел 6; общие принципы — раздел 15.

## 12. Ограничения по IP-адресам и именам (IP and Domain Restrictions)

### 12.1. Атрибуты

Компонент `Web-IP-Security`, секция `system.webServer/security/ipSecurity` [MS Learn]:

| Атрибут | Смысл | Умолчание |
|---|---|---|
| `allowUnlisted` | пускать адреса, которых нет в списке; `false` — «белый список» (не забудьте `127.0.0.1`, иначе не откроете сайт с самого сервера; запрет в родителе нельзя снять `<clear>` ниже) | `true` |
| `denyAction` (IIS 8+) | что отвечать: `AbortRequest` (оборвать соединение), `Unauthorized` (401; браузер может показать окно входа), `Forbidden` (403), `NotFound` (404) | `Forbidden` |
| `enableProxyMode` (IIS 8+) | проверять также адреса из `X-Forwarded-For` | `false` |
| `enableReverseDns` | обратные DNS-запросы для правил по имени — «значительные ресурсы и время» | `false` |

Элемент `<add>`: `ipAddress`, `subnetMask` (по умолчанию `255.255.255.255` — один адрес), `domainName` (можно с `*`), `allowed` (по умолчанию `false`) [MS Learn]. ⚠ Справочник говорит только об IPv4; работа правил с IPv6-адресами (в том числе `::1`) по документации не подтверждена — на сервере с IPv6 проверьте.

Коды [MS Learn, «HTTP status code overview»]: 403.6 «IP address rejected» (классика), 403.503 / 401.503 / 404.503 — адрес в запрещённом списке при соответствующем `denyAction`, …504 — имя узла в запрещённом списке.

### 12.2. Примеры для публикации 1С

HTTP-сервисы и OData публикации — только с сервера интеграции и из подсети администраторов:

```bat
cd /d %windir%\system32\inetsrv
for %P in (hs odata) do (
  appcmd set config "Default Web Site/demo/%P" -section:system.webServer/security/ipSecurity /allowUnlisted:"False" /denyAction:"NotFound" /commit:apphost
  appcmd set config "Default Web Site/demo/%P" -section:system.webServer/security/ipSecurity /+"[ipAddress='10.10.20.15',allowed='True']" /commit:apphost
  appcmd set config "Default Web Site/demo/%P" -section:system.webServer/security/ipSecurity /+"[ipAddress='10.10.5.0',subnetMask='255.255.255.0',allowed='True']" /commit:apphost
  appcmd set config "Default Web Site/demo/%P" -section:system.webServer/security/ipSecurity /+"[ipAddress='127.0.0.1',allowed='True']" /commit:apphost
)
appcmd list config "Default Web Site/demo/odata" -section:system.webServer/security/ipSecurity
```

Синтаксис добавления правила — образец [MS Learn, `ipSecurity/add`]; `/allowUnlisted`, `/denyAction` — имена атрибутов [MS Learn], форма команды и цикл `for` в `cmd` (в `.bat` — `%%P`) — [практика]. `NotFound` скрывает сам факт существования пути [практика]. Секция `ipSecurity` по умолчанию заблокирована на уровне сервера ⚠ — поэтому `/commit:apphost`.

Проверка: с разрешённого адреса `curl.exe -sI https://web1c.corp.local/demo/odata/standard.odata/` — 401 (нужна аутентификация 1С) или 200; с любого другого — 404, в журнале `404 503` [практика; подстатус — MS Learn].

### 12.3. Замечания

- **Брандмауэр Windows — первая линия**, IIS-ограничения — вторая: порт 443 открывайте только для нужных подсетей (`New-NetFirewallRule … -RemoteAddress`, `1c-windows/06`, раздел 6.3) [практика].
- `enableProxyMode` доверяет `X-Forwarded-For` — заголовок подделывается клиентом, если тот может достучаться до IIS в обход прокси; включайте только когда IIS закрыт брандмауэром для всех, кроме прокси [практика].
- За обратным прокси (ARR, балансировщик) IIS видит адрес прокси — ограничения по адресам клиентов делайте на прокси (`iis/03`) [практика; ИТС-адм разд. 8.10.3 о том, что запросы приходят «от компьютера, на котором установлен reverse proxy»].

## 13. Динамические ограничения по IP (Dynamic IP Restrictions)

### 13.1. Атрибуты

Встроены с IIS 8.0 в «IP and Domain Restrictions» (`Web-IP-Security`), уровень сервера или сайта [MS Learn, `dynamicIpSecurity`; «IIS 8.0 Dynamic IP Address Restrictions»]:

| Элемент / атрибут | Смысл | Умолчание |
|---|---|---|
| `dynamicIpSecurity/@denyAction` | `AbortRequest`, `Unauthorized` (401), `Forbidden` (403), `NotFound` (404) | `Forbidden` |
| `dynamicIpSecurity/@enableLoggingOnlyMode` | только записывать в журнал то, что было бы отклонено | `false` |
| `dynamicIpSecurity/@enableProxyMode` | учитывать адреса из `X-Forwarded-For` | `false` |
| `denyByConcurrentRequests/@enabled`, `@maxConcurrentRequests` | порог одновременных запросов с адреса | `false`, `5` |
| `denyByRequestRate/@enabled`, `@maxRequests`, `@requestIntervalInMilliseconds` | порог числа запросов за интервал | `false`, `20`, `200` |

Коды: `…501` — одновременные запросы, `…502` — частота (основной код 401/403/404 по `denyAction`) [MS Learn, коды состояния]. ⚠ Сколько длится блокировка адреса, документация не говорит.

### 13.2. Для 1С — осторожно

- Веб-клиент 1С при открытии формы или списка шлёт пачку почти одновременных запросов ⚠, офис за NAT выглядит одним адресом — пороги по умолчанию сработают на обычной работе [практика].
- Порядок [практика]: неделя с `enableLoggingOnlyMode="true"` → разбор подстатусов `501`/`502` в журнале → пороги с запасом → выключить «только журнал». Для `/hs`, `/odata` вместо этого — белый список (раздел 12). Смысл есть на сайтах, опубликованных в Интернет.

### 13.3. Команды

[MS Learn, образец `Set-WebConfigurationProperty` для `dynamicIpSecurity`; пороги — пример]

```powershell
Import-Module WebAdministration
$p = @{ pspath = 'MACHINE/WEBROOT/APPHOST'; location = 'Default Web Site' }
$f = 'system.webServer/security/dynamicIpSecurity'
Set-WebConfigurationProperty @p -filter $f -name 'enableLoggingOnlyMode' -value 'True'
Set-WebConfigurationProperty @p -filter "$f/denyByConcurrentRequests" -name 'enabled' -value 'True'
Set-WebConfigurationProperty @p -filter "$f/denyByConcurrentRequests" -name 'maxConcurrentRequests' -value 100
Set-WebConfigurationProperty @p -filter "$f/denyByRequestRate" -name 'enabled' -value 'True'
Set-WebConfigurationProperty @p -filter "$f/denyByRequestRate" -name 'maxRequests' -value 300
Set-WebConfigurationProperty @p -filter "$f/denyByRequestRate" -name 'requestIntervalInMilliseconds' -value 1000
& "$env:windir\system32\inetsrv\appcmd.exe" list config "Default Web Site" -section:system.webServer/security/dynamicIpSecurity
```

Сплаттинг `@p` — [практика]. В образцах Microsoft `requestIntervalInMilliseconds` разный: PowerShell — `20`, `appcmd` — `210`, XML — `300` (подтверждено 20.10.2026) — значение `20` похоже на опечатку; умолчание по схеме — `200`.

## 14. Фильтрация запросов (Request Filtering)

### 14.1. Подстатусы

Встроенная функция IIS (с 7.0, замена UrlScan), секция `system.webServer/security/requestFiltering`; отказ — 404 (или 413/431) с уникальным подстатусом в журнале [MS Learn]:

| Подстатус | Причина | Где настраивается |
|---|---|---|
| 404.5 / 404.18 | запрещённая последовательность в URL / в строке запроса | `denyUrlSequences` / `denyQueryStringSequences` |
| 404.6 / 404.7 / 404.8 | метод / расширение / скрытый сегмент | `verbs` / `fileExtensions` / `hiddenSegments` |
| 404.11 / 404.12 | двойное экранирование / символы со старшим битом | `allowDoubleEscaping` / `allowHighBitCharacters` |
| 404.14 / 404.15 | длина URL / строки запроса | `requestLimits/@maxUrl` / `@maxQueryString` |
| 404.19 | своё правило | `filteringRules` |
| 413.1 | тело больше `maxAllowedContentLength` | `requestLimits` |
| 431 | заголовок длиннее предела | `requestLimits/headerLimits` |

⚠ Для превышения тела справочник `requestFiltering` даёт 413.1, общий справочник кодов — 404.13 (так же в `1c-windows/03`, раздел 8.1). Атрибуты элемента [MS Learn]: `allowDoubleEscaping` (`false`), `allowHighBitCharacters` (`true`), `unescapeQueryString` (`true` — проверять сырую и декодированную строку запроса), `removeServerHeader` (`false`, 5.3).

### 14.2. Пределы размеров

`requestLimits` [MS Learn]: `maxAllowedContentLength` — 30 000 000 байт (≈28,6 МБ), `maxUrl` — 4096, `maxQueryString` — 2048; `headerLimits/add` (`header`, `sizeLimit`) — предел отдельного заголовка. Раньше или параллельно режут [MS Learn]: http.sys — `MaxFieldLength`, `MaxRequestBytes` (по 16 384), `UrlSegmentMaxLength` (260 символов в одном сегменте), `UrlSegmentMaxCount` (255) — ответ 400 от http.sys мимо журнала IIS (16.3, HTTPERR); сайт — `limits/@maxUrlSegments` (32; ответ, по-видимому, 404.20 «Too Many URL Segments» ⚠) и `limits/@connectionTimeout` (2 минуты — ограничивает простаивающие соединения и медленную передачу тела) [MS Learn, `limits`; связь с «медленными» атаками — практика].

Значения для 1С (загрузка файлов, POST в HTTP-сервисы, длинные URL OData) и команды — `1c-windows/03`, раздел 8. Поднимайте пределы **только у приложения публикации** и до нужной величины: большой предел — и большой запрос злоумышленника [практика].

### 14.3. Методы

`verbs`: `allowUnlisted` (`true`; `false` — белый список), `applyToWebDAV`, `add` (`verb`, `allowed`); блокировка `TRACE` — пример из документации [MS Learn]. Белый список методов для 1С рискован: OData использует `GET`, `POST`, `PATCH`, `PUT`, `DELETE` [ИТС, «Руководство разработчика», 17.4; уточнено 20.10.2026], браузерный CORS — `OPTIONS` [практика]. Минимум — запрет `TRACE`/`TRACK`:

```bat
cd /d %windir%\system32\inetsrv
appcmd set config "Default Web Site" -section:system.webServer/security/requestFiltering /+"verbs.[verb='TRACE',allowed='False']"
appcmd set config "Default Web Site" -section:system.webServer/security/requestFiltering /+"verbs.[verb='TRACK',allowed='False']"
```

[образец MS Learn `verbs`]. Проверка: `curl.exe -si -X TRACE https://web1c.corp.local/` → 404, в журнале `404 6` [практика].

### 14.4. Сегменты, расширения, последовательности

- `hiddenSegments` (404.8): IIS скрывает `web.config`, `bin`, `App_Code` и т. п. [MS Learn]; корневой URL HTTP-сервиса 1С с именем `bin` попадёт под фильтр (`1c-windows/03`, 8.1). Свой: `/+"hiddenSegments.[segment='_private']"` [MS Learn].
- `fileExtensions` (`allowUnlisted` = `true`; 404.7): белый список расширений для публикации 1С не делать — обработчик `*` принимает любые пути [практика].
- `denyUrlSequences` (404.5): в образце Microsoft — `..`, `:`, `\` [MS Learn]; `:` встречается в URL OData 1С — в литералах вида `datetime'1945-05-09T06:00:00'` [ИТС, «Руководство разработчика», 17.4; уточнено 20.10.2026], в шаблонах HTTP-сервисов — по вашей конфигурации; проверяйте на своих адресах.
- `allowDoubleEscaping="false"` (404.11 на `%25`, `+` в пути) — для некоторых HTTP-сервисов включают у приложения (`1c-windows/03`).
- `allowHighBitCharacters` (`true`) **не выключать на публикации 1С**: имена ресурсов OData строятся из имён объектов конфигурации и бывают кириллическими (`Catalog_Контрагент(guid'…')`) [ИТС, «Руководство разработчика», 17.4; уточнено 20.10.2026].
- `denyQueryStringSequences` (404.18; исключения — `alwaysAllowedQueryStrings`, `alwaysAllowedUrls`) и `filteringRules` (404.19; `scanUrl`, `scanQueryString`, `scanAllRaw`, `denyUnescapedPercent`, `appliesTo`, `denyStrings`, `scanHeaders`) [MS Learn] — это не WAF; на публикации 1С ложные срабатывания (тексты в `$filter` OData) вероятнее пользы [практика].

## 15. Учётные записи и минимальные права

### 15.1. Удостоверение пула

`processModel/@identityType` [MS Learn]:

| Значение | Что это | Оценка Microsoft |
|---|---|---|
| `ApplicationPoolIdentity` (4) | виртуальная `IIS AppPool\<пул>`; в сети — учётная запись компьютера | умолчание с IIS 7.5; права можно дать только этому пулу |
| `NetworkService` (2) | встроенная; в сети — компьютер | больше прав, чем у `ApplicationPoolIdentity` |
| `LocalService` (1) | встроенная; в сети — анонимно | «высокие права — серьёзный риск» |
| `LocalSystem` (0) | полные права на компьютере | серьёзный риск |
| `SpecificUser` (3) | своя учётная запись (`userName`/`password` — через `appcmd`/диспетчер, шифруется); допустимы управляемые учётные записи служб | фермы, доступ к сети |

Таблица справочника говорит «the default is `NetworkService`», примечания там же и статья «Application Pool Identities» — что с IIS 7.5 умолчание `ApplicationPoolIdentity`; верно второе (подтверждено 20.10.2026: в схеме IIS 10 `identityType` — `defaultValue="ApplicationPoolIdentity"`). Прочее [MS Learn]: `manualGroupMembership` (`false` — IIS сам добавляет SID `IIS_IUSRS` в маркер; `true` — удостоверение надо явно включать в ACL); `loadUserProfile` (справочник и схема — `false`; фактическое значение в `applicationPoolDefaults` своего сервера не проверено ⚠; влияет на временный каталог — для 1С см. `temp` в `1c-windows/03`, 5.1); `logonType` (`LogonBatch` / `LogonService`).

### 15.2. Принципы

1. **Свой пул на каждое приложение**, публикация 1С — отдельно от прочих сайтов; ACL — на `IIS AppPool\<пул>` [MS Learn; практика].
2. **Минимальные права NTFS**: содержимое — чтение, запись — только где нужно, «Полный доступ» избегать; доступ для `IIS_IUSRS` — это доступ для **всех** пулов сервера [MS Learn, «Secure Content in IIS Through File System ACLs»].
3. **Не `LocalSystem`/`NetworkService`** без причины [MS Learn]; анонимный пользователь — `userName=""` вместо общего `IUSR` (7.1) [практика].
4. **`isapiCgiRestriction`**: `notListedIsapisAllowed`, `notListedCgisAllowed` по умолчанию `false` [MS Learn] — разрешены только перечисленные библиотеки; держите там лишь используемые версии `wsisapi.dll` (запрещённая — 404.2) [MS Learn; про 1С — `1c-windows/03`].
5. **Блокировка секций** (6.2) — аутентификация, `ipSecurity`, `requestFiltering` в `applicationHost.config`, а не в `web.config` каталогов, куда пишут другие [практика].
6. **Пароли в конфигурации** (пулы, анонимный пользователь, сопоставления, CCS) — только через `appcmd`/диспетчер/командлеты: хранятся как `[enc:AesProvider:…:enc]` [MS Learn] (в схеме IIS сборки Windows 11 26300 умолчание уже `[enc:IISCngProvider::enc]`; с какой сборки Windows Server так — не проверено ⚠).

```bat
cd /d %windir%\system32\inetsrv
appcmd set apppool "1C-<версия>" -processModel.identityType:ApplicationPoolIdentity
icacls "D:\Sites\Intranet" /grant "IIS AppPool\Intranet:(OI)(CI)RX"
icacls "D:\Sites\Intranet\App_Data" /grant "IIS AppPool\Intranet:(OI)(CI)M"
appcmd list config -section:system.webServer/security/isapiCgiRestriction
```

Образцы `appcmd set AppPool … -processModel.identityType:ApplicationPoolIdentity` и `ICACLS … /grant "IIS AppPool\DefaultAppPool:F"` — [MS Learn]; `RX`/`M` вместо `F` — [практика].

### 15.3. Гигиена

Замените `iisstart.htm` на Default Web Site или ставьте сайт-заглушку на «чужие» имена (2.4) [практика]; не ставьте службу удалённого управления IIS (`Web-Mgmt-Service` — «управление веб-сервером удалённо из диспетчера IIS» [MS Learn]) без нужды [практика]; перед изменениями — `appcmd add backup` (восстановление останавливает сервер и возвращает глобальную конфигурацию) [MS Learn]; IIS обновляется только вместе с Windows — сроки поддержки ОС в `1c-windows/06`, раздел 1.

## 16. Журналы и аудит безопасности

### 16.1. Журнал IIS

- По умолчанию пишутся `Date`, `Time`, `ClientIP`, `UserName`, `ServerIP`, `Method`, `UriStem`, `UriQuery`, `TimeTaken`, `HttpStatus`, `Win32Status`, `ServerPort`, `UserAgent`, `HttpSubStatus`, `Referer`; `Host` и `ProtocolVersion` — нет [MS Learn, `logFile`]; для безопасности полезно добавить оба [практика].
- `cs-username` — аутентифицированный пользователь («-» у анонимных) [MS Learn]; при анонимном IIS пользователя 1С ищите в журнале регистрации 1С [практика].
- За прокси `c-ip` — адрес прокси; поле `X-Forwarded-For` (`sourceType="RequestHeader"`, `sourceName="X_FORWARDED_FOR"`) [MS Learn, `customFields`]; TLS-поля — 3.5; хранение и ротация — `iis/03`.

```bat
%windir%\system32\inetsrv\appcmd set config -section:system.applicationHost/sites /[name='Default Web Site'].logFile.logExtFileFlags:"Date, Time, ClientIP, UserName, ServerIP, Method, UriStem, UriQuery, HttpStatus, Win32Status, TimeTaken, ServerPort, UserAgent, Referer, HttpSubStatus, Host, ProtocolVersion" /commit:apphost
```

Флаги — [MS Learn]; форма команды — по образцу `/[name='Contoso'].logFile.period:"Daily"` ⚠.

### 16.2. Коды для мониторинга

[MS Learn, «HTTP status code overview»]

| Код | Что значит |
|---|---|
| 401.1 | неверное имя/пароль — много с одного адреса = перебор |
| 401.2 | вызов аутентификации (первый — норма; постоянно — нет общего метода) |
| 401.3 | отказ по ACL |
| 401/403/404 .501–.504 | динамические и статические IP-ограничения (12–13) |
| 403.4 / 403.6 | нужен SSL / IP отклонён |
| 403.7 / 403.13 / 403.16 / 403.17 | клиентский сертификат: нет / отозван / недоверенный / истёк |
| 404.2 | ISAPI/CGI не разрешён (для 1С — версия `wsisapi.dll`) |
| 404.5–404.20, 413.1, 431 | фильтрация запросов (14) |
| 500.19 | ошибка конфигурации, в том числе нарушение блокировки секции (6.2) |

Отказы по адресам за последние сутки [практика]:

```powershell
$log = Get-ChildItem 'C:\inetpub\logs\LogFiles\W3SVC1' -Filter 'u_ex*.log' | Sort-Object LastWriteTime | Select-Object -Last 1
$hdr = (Get-Content $log.FullName -TotalCount 20 | Where-Object { $_ -like '#Fields:*' } | Select-Object -Last 1) -replace '^#Fields: ',''
Get-Content $log.FullName | Where-Object { $_ -notlike '#*' } | ConvertFrom-Csv -Delimiter ' ' -Header ($hdr -split ' ') |
  Where-Object { $_.'sc-status' -in '401','403' } | Group-Object 'c-ip','sc-status','sc-substatus' |
  Sort-Object Count -Descending | Select-Object -First 20 Count, Name
```

### 16.3. Журналы Windows

- **«Безопасность»**: Basic и Windows-аутентификация IIS порождают входы Windows — 4624 (успех), 4625 (отказ); тип входа 3 «Network» и 8 «NetworkCleartext» (пароль передан пакету в нехешированном виде) [MS Learn, события 4624/4625]; «Basic с `ClearText` → тип 8» — уточнено 20.10.2026 (см. 8.1). Аудит входов включается политикой (⚠ «Аудит входа в систему»).
- **«Система»**: события Schannel по уровню `EventLogging` (3.5) ⚠ источник «Schannel»; `KRB_AP_ERR_MODIFIED` «также записывается в журналы событий» [MS Learn].
- **HTTPERR**: отказы самого http.sys (400 «header too long», 503 очереди, обрывы) — файлы `httperr<номер>.log` в каталоге по умолчанию `%SystemRoot%\System32\LogFiles\HTTPERR` (параметры `EnableErrorLogging`, `ErrorLoggingDir`, `ErrorLogFileTruncateSize` в `HKLM\System\CurrentControlSet\Services\HTTP\Parameters`) [MS Learn, «Configuring HTTP Server API Error Logging»; уточнено 20.10.2026].
- **CAPI2**: построение и проверка цепочек сертификатов (в том числе у клиентов 1С), по умолчанию выключен [ИТС-мет 5949, 2018]; `wevtutil sl Microsoft-Windows-CAPI2/Operational /e:true` [практика; `wevtutil` — `1c-windows/06`, 11].
- **FREB** (трассировка неудачных запросов) с областью аутентификации показывает, на каком модуле отказ, — `iis/03` [практика].

```powershell
Get-WinEvent -FilterHashtable @{ LogName = 'Security'; Id = 4625; StartTime = (Get-Date).AddHours(-1) } | Select-Object -First 20 TimeCreated, Message
Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Schannel'; StartTime = (Get-Date).AddDays(-1) } -ErrorAction SilentlyContinue | Select-Object -First 20 TimeCreated, Id, Message
```

## 17. IIS и Apache: где что настраивается

| Задача | IIS 10 | Apache 2.4 на Ubuntu (`apache/02`) |
|---|---|---|
| TLS | Schannel ОС, общий для всех служб Windows | OpenSSL, в каждом `VirtualHost` |
| Версии протоколов / шифры | реестр и политика на всю систему + флаги привязки | `SSLProtocol`, `SSLCipherSuite` в хосте |
| Сертификат | хранилище компьютера, ключ неэкспортируемый, привязка `netsh http` | файлы PEM, ключ `root:600` |
| HSTS / скрытие версии | `<hsts>`, `removeServerHeader` (1709+) | `Header always set …`, `ServerTokens Prod` |
| Kerberos SSO | встроено, режим ядра, учётная запись компьютера | `mod_auth_gssapi` + keytab `HTTP/…` |
| Ограничение по IP | `ipSecurity`, `dynamicIpSecurity` | `Require ip` |
| Аутентификация ОС для 1С | поддерживается | Windows-Apache — нет; Linux-Apache — через Kerberos [ИТС-адм разд. 6.2.10.3, 2.8.1.2] |

Главное: в IIS «ужесточить TLS для одного сайта» почти нельзя — меняется весь сервер (RDP, WinRM, исходящие соединения), поэтому правки Schannel — это изменения ОС с окном и откатом [практика].

## 18. Чек-лист

1. Версия ОС и сборка IIS (1.1); WS 2016 — план переезда.
2. Только нужные компоненты (1.2); нет WebDAV, CGI, Digest, ASP.NET у публикации 1С.
3. Сертификат ЦС, SAN со всеми именами, полная цепочка, CRL/OCSP доступны клиентам, ключ неэкспортируемый (2.1–2.2).
4. SNI-привязки, заглушка на `*:443:`/`*:80:`, `netsh http show sslcert` совпадает с привязками (2.3–2.4); перепривязка и контроль сроков (2.6).
5. Неделя журнала `CRYPT_PROTOCOL` → TLS 1.0/1.1 выключены у привязки или в системе; без 3DES (3).
6. HTTP → HTTPS; HSTS с постепенным `max-age`, без `includeSubDomains` во внутреннем домене (4).
7. `X-Powered-By` убран, `Server` скрыт, `nosniff`, `Referrer-Policy`, `frame-ancestors`; `DetailedLocalOnly` (5).
8. Аутентификация — в `applicationHost.config`, секции заблокированы (6.2).
9. Публикация 1С: анонимная + пароли 1С по HTTPS **или** Windows (анонимная выкл., Negotiate, SPN, делегирование) (7, 9); Basic на IIS — нет (8); Extended Protection — `Allow` (9.10).
10. `/hs`, `/odata`, админ-пути — белый список адресов, брандмауэр открывает 443 только нужным подсетям (12); динамические ограничения — для публичных сайтов, сначала «только журнал» (13).
11. `TRACE`/`TRACK` запрещены; пределы размеров подняты только у публикации 1С (14).
12. `ApplicationPoolIdentity`, пул на приложение, ACL на пул, `isapiCgiRestriction` без лишних версий (15).
13. Журналы: `Host`, `ProtocolVersion`, `X-Forwarded-For`, аудит входов, мониторинг 401/403 (16).
14. Перед каждым изменением — `appcmd add backup` и `reg export` ветки SCHANNEL.

## Типичные ошибки (симптом → причина → решение)

| Симптом | Причина | Решение |
|---|---|---|
| Сайт отдаёт старый сертификат | в http.sys старый отпечаток; продление без перепривязки | `netsh http show sslcert`, пересоздать привязку (2.3), Certificate Rebind (2.6) [MS Learn] |
| `New-IISSiteBinding` не найден | WS 2016: командлеты привязок — с 1709 | `New-WebBinding` + `AddSslCertificate()` или `appcmd` + `netsh` (2.3) [MS Learn] |
| Браузер доволен, тонкий клиент/интеграция — «сертификат не прошёл проверку» | неполная цепочка, корень не в хранилище клиента, недоступен CRL | промежуточные ЦС на сервере, корень — политикой, CAPI2 [ИТС-мет 5949; практика] |
| «Не удалось выполнить проверку отзыва сертификата» у 1С | CRL/OCSP недоступны клиенту или учётной записи процесса, а `IgnoreServerCertificatesChainRevocationSoftFail` = `false` (в 8.3.27 по умолчанию `true` [ИТС-адм прил. 3.17.16]; методичка 2018 года описывает исключение как поведение по умолчанию) | опубликовать CDP/AIA доступно; проверить параметр в `conf.cfg` клиента [ИТС-мет 5949, 2018; ИТС-адм прил. 3.17.16] |
| После отключения TLS 1.0/1.1 отвалились старые интеграции или RDP | клиенты без TLS 1.2; затронута клиентская роль | заранее журнал `CRYPT_PROTOCOL` (3.5); откат — `.reg` и перезагрузка; выключать у привязки [практика] |
| `DisableByDefault` из ИТС ничего не меняет | такого имени у Microsoft нет | на WS 2016+ TLS 1.1/1.2 включены; управление — `Enabled` (3.3) [MS Learn] |
| Правка Schannel или шифров «не действует» | нужна перезагрузка | перезагрузить в окно обслуживания [MS Learn] |
| Бесконечное перенаправление | `<httpRedirect>` на сайте, который обслуживает HTTPS | отдельный HTTP-сайт, `redirectHttpToHttps` или URL Rewrite с `{HTTPS}` = `off` (4) [MS Learn] |
| POST в 1С после перехода на HTTPS приходит пустым / 405 | клиент выполнил 301/302 как GET | `https://` у клиента; если нужно — 307/308 (4.1) [MS Learn; практика] |
| Внутренние HTTP-сайты перестали открываться | HSTS с `includeSubDomains` | убрать, ответить `max-age=0` по HTTPS, ждать истечения (4.2) [сторонний MDN] |
| Веб-клиент 1С не встраивается во фрейм портала | `X-Frame-Options: deny`/`sameorigin` или `ALLOW-FROM` | `frame-ancestors 'self' https://portal…` (5.2) [ИТС-адм разд. 8.10.2.7; MDN] |
| `removeServerHeader` не убирает `Server` | WS 2016 или ответ самого http.sys | `DisableServerHeader` = 2; на 2016 — URL Rewrite (5.3) [MS Learn] |
| 500.19 после правки `web.config` публикации | секция аутентификации заблокирована | `appcmd … /commit:apphost` (6.2) [MS Learn] |
| Вместо входа по домену 1С показывает окно пароля | анонимная не выключена / Windows не включена / не тот пользователь ОС | 9.11, `DstUserName2` в техжурнале [ИТС-мет 5944, 2018] |
| Три запроса пароля, затем 401; в журнале 401.2 / 401.1 | Kerberos не удался: нет SPN, дубль, зона браузера, обращение по IP | `klist get HTTP/…`, `setspn -Q`/`-X`, зона «Интрасеть» (9.3–9.6) [MS Learn] |
| `KRB_AP_ERR_MODIFIED` | дубль SPN или пул под доменной учётной записью без `useAppPoolCredentials` | `setspn -X`; SPN на нужной учётной записи; `useAppPoolCredentials="true"` [MS Learn] |
| Сервер 1С видит `ANONYMOUS LOGON` | нет делегирования или браузер ушёл в NTLM | делегирование для `WEB01$`/пула, Kerberos (9.9) [ИТС-мет 5944] |
| 400 «Request header too long» у части пользователей | большой билет Kerberos | `MaxFieldLength`/`MaxRequestBytes` = 4/3·T + 200 (9.8) [MS Learn] |
| Extended Protection `Require` — часть клиентов не входит | клиенты или прокси без CBT | `Allow`; за прокси — `Proxy` и `<spn>` (9.10) [MS Learn] |
| HTTP-сервисы 1С с паролем 1С получают 401 от IIS | на пути включена Windows, выключена анонимная | анонимный IIS на `/demo/hs` (9.12) + белый список (12) [практика] |
| Тонкий клиент с RSA-сертификатом не подключается к WS 2022 с `SslRequireCert` | TLS 1.3: в нём 1С поддерживает только ГОСТ-клиентские сертификаты | `DisableTLS13` у привязки или `/HttpsForceTLS1_2` (10.4) ⚠ [ИТС-адм разд. 8.9.2] |
| Правила по группам — у всех 401 | при анонимном IIS пользователь — `IUSR` | URL Authorization только с Windows/Basic (11.2) [практика] |
| После `allowUnlisted="false"` сайт не открывается с самого сервера | нет `127.0.0.1` (и ⚠ `::1`) | добавить (12.1) [MS Learn] |
| Офис массово получает 403 в веб-клиенте | `dynamicIpSecurity` с порогами по умолчанию, NAT | «только журнал», пороги по журналу (13.2) [практика] |
| TRACE отвечает 200 в отчёте сканера | метод не запрещён | `verbs` `TRACE`/`TRACK` (14.3) [MS Learn] |
| OData с кириллицей в пути — 404.12 | выключен `allowHighBitCharacters` | вернуть `true` (14.4) [MS Learn; практика] |

## Быстрая шпаргалка

```powershell
Get-WindowsFeature Web-* | Where-Object Installed | Format-Table Name
Get-IISSiteBinding -Name 'Default Web Site'            # WS 2019+
netsh http show sslcert
Get-ChildItem Cert:\LocalMachine\My | Select-Object Thumbprint, Subject, NotAfter, HasPrivateKey
Get-TlsCipherSuite | Select-Object Name
Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols' -Recurse
Import-PfxCertificate -FilePath C:\Certs\web1c.pfx -CertStoreLocation Cert:\LocalMachine\My -Password (Read-Host -AsSecureString)
New-IISSiteBinding -Name 'Default Web Site' -BindingInformation '*:443:web1c.corp.local' -Protocol https -CertificateThumbPrint '<отпечаток>' -CertStoreLocation 'Cert:\LocalMachine\My' -SslFlag 'Sni'
Disable-TlsCipherSuite -Name 'TLS_RSA_WITH_3DES_EDE_CBC_SHA'
curl.exe -sI https://web1c.corp.local/ ; curl.exe -sI --tlsv1.1 --tls-max 1.1 https://web1c.corp.local/
klist get HTTP/web1c.corp.local
```

```bat
cd /d %windir%\system32\inetsrv
appcmd add backup before-change
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].hsts.enabled:True" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].hsts.max-age:31536000" /commit:apphost
appcmd set config -section:system.applicationHost/sites "/[name='Default Web Site'].hsts.redirectHttpToHttps:True" /commit:apphost
appcmd set config "Default Web Site" -section:system.webServer/httpProtocol /-"customHeaders.[name='X-Powered-By']"
appcmd set config -section:system.webServer/security/requestFiltering /removeServerHeader:"True" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/anonymousAuthentication /enabled:"False" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication /enabled:"True" /commit:apphost
appcmd set config "Default Web Site/demo" -section:system.webServer/security/access /sslFlags:"Ssl" /commit:apphost
appcmd set config "Default Web Site/demo/odata" -section:system.webServer/security/ipSecurity /allowUnlisted:"False" /commit:apphost
appcmd set config "Default Web Site/demo/odata" -section:system.webServer/security/ipSecurity /+"[ipAddress='10.10.20.15',allowed='True']" /commit:apphost
appcmd set config "Default Web Site" -section:system.webServer/security/requestFiltering /+"verbs.[verb='TRACE',allowed='False']"
appcmd list config "Default Web Site/demo" -section:system.webServer/security/authentication/windowsAuthentication
:: SPN (администратор домена)
setspn -S HTTP/web1c.corp.local CORP\WEB01$
setspn -X
```

## Источники

Microsoft IIS (исходники `https://raw.githubusercontent.com/MicrosoftDocs/iis-docs/main/iis/<путь>.md`, страницы `https://learn.microsoft.com/en-us/iis/<путь>`, прочитаны 20.10.2026):

- `configuration/system.applicationHost/sites/site/{bindings/binding, hsts, logFile, logFile/customFields}`, `…/siteDefaults/limits`, `…/applicationPools/add/processModel`;
- `configuration/system.webServer/security/{access, authentication, anonymousAuthentication, basicAuthentication, digestAuthentication, windowsAuthentication (+ providers, extendedProtection, spn), clientCertificateMappingAuthentication, iisClientCertificateMappingAuthentication (+ oneToOneMappings, manyToOneMappings), authorization, ipSecurity, dynamicIpSecurity (+ denyByConcurrentRequests, denyByRequestRate), isapiCgiRestriction, requestFiltering (+ requestLimits, headerLimits, verbs, hiddenSegments, fileExtensions, denyUrlSequences, denyQueryStringSequences, filteringRules)}`; `system.webServer/{httpProtocol, httpProtocol/customHeaders, httpRedirect, httpErrors, directoryBrowse}`;
- `get-started/whats-new-in-iis-10/{new-features-introduced-in-iis-10, http2-on-iis, iisadministration-powershell-cmdlets}`, `…-10-version-1709/{new-features-introduced-in-iis-10-1709, iis-10-version-1709-hsts}`, `…-10-version-1809/new-features-introduced-in-iis-10-1809`, `…-8/{iis-80-centralized-ssl-certificate-support-…, iis-80-server-name-indication-sni-ssl-scalability, iis-80-dynamic-ip-address-restrictions}`, `…-85/certificate-rebind-in-iis85`;
- `get-started/planning-for-security/{understanding-built-in-user-and-group-accounts-in-iis, secure-content-in-iis-through-file-system-acls, how-to-use-locking-in-iis-configuration}`, `get-started/getting-started-with-iis/getting-started-with-appcmdexe`; `manage/configuring-security/{application-pool-identities, understanding-iis-url-authorization, configure-request-filtering-in-iis, configuring-one-to-one-client-certificate-mappings}`; `manage/powershell/powershell-snap-in-configuring-ssl-with-the-iis-powershell-snap-in`; `web-hosting/…/configuring-step-4-configure-ssl-central-certificate-store`; `install/installing-iis-85/installing-iis-85-on-windows-server-2012-r2`; `web-dev-reference/server-variables`;
- URL Rewrite: `extensions/url-rewrite-module/{url-rewrite-module-configuration-reference, creating-rewrite-rules-for-the-url-rewrite-module, modifying-http-response-headers}`; загрузка — https://www.iis.net/downloads/microsoft/url-rewrite.

Windows и PowerShell:

- TLS registry settings — https://learn.microsoft.com/en-us/windows-server/security/tls/tls-registry-settings (ред. 18.04.2025); Manage TLS — `…/manage-tls`;
- Protocols in TLS/SSL (Schannel SSP) — https://learn.microsoft.com/en-us/windows/win32/secauthn/protocols-in-tls-ssl--schannel-ssp- ; TLS 1.0 and TLS 1.1 deprecation in Windows — `…/tls-10-11-deprecation-in-windows`; TLS Cipher Suites in Windows Server 2022 / 2025 — `…/tls-cipher-suites-in-windows-server-2022`, `…-2025`;
- Managing SSL/TLS Protocols and Cipher Suites for AD FS (`DisabledByDefault`) — `MicrosoftDocs/windowsserverdocs`, `WindowsServerDocs/identity/ad-fs/operations/Manage-SSL-Protocols-in-AD-FS.md`;
- netsh http — https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-http (ред. 19.08.2025);
- командлеты (`MicrosoftDocs/windows-powershell-docs`, `docset/winserver2025-ps`): `IISAdministration` (`New-/Get-/Remove-IISSiteBinding`, `Enable-/Get-/Set-IISCentralCertProvider`, `Set-IISCentralCertProviderCredential`, `Get-IISConfigSection`, `Get-/Set-IISConfigAttributeValue`), `WebAdministration` (`New-WebBinding`, `Get-WebBinding`, `Enable-WebCentralCertProvider`, `Get-/Set-WebConfigurationProperty`), `TLS` (`Get-/Enable-/Disable-TlsCipherSuite`, `Get-TlsEccCurve`), `PKI` (`Import-PfxCertificate`, `Get-Certificate`, `New-SelfSignedCertificate`);
- события 4624/4625 — https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624 , `…/event-4625`.
- добавлено при независимой сверке 20.10.2026: схема конфигурации IIS 10 `%windir%\system32\inetsrv\config\schema\IIS_schema.xml` (прочитана на Windows 11 сборки 26300 этой машины — умолчания и допустимые значения атрибутов); `SecPkgContext_ConnectionInfo` (`MicrosoftDocs/sdk-api`, `schannel/ns-schannel-secpkgcontext_connectioninfo.md` — константы `SP_PROT_*`); `LogonUser` (`winbase/nf-winbase-logonusera.md` — `LOGON32_LOGON_NETWORK_CLEARTEXT`); certutil — `WindowsServerDocs/administration/windows-commands/certutil.md` (`-verify`, `-urlfetch`); «Configuring HTTP Server API Error Logging» — `MicrosoftDocs/win32`, `desktop-src/Http/configuring-http-server-api-error-logging.md`; AD Schema `sPNMappings` — `desktop-src/ADSchema/a-spnmappings.md`.

Поддержка Microsoft: Http.sys registry settings for Windows — https://learn.microsoft.com/en-us/troubleshoot/developer/webapps/iis/iisadmin-service-inetinfo/httpsys-registry-windows ; HTTP 400 … Request Header too long — `…/www-authentication-authorization/http-bad-request-response-kerberos`; Troubleshoot Kerberos failures — `…/www-authentication-authorization/troubleshoot-kerberos-failures-ie`; HTTP status code overview — `…/health-diagnostic-performance/http-status-code`.

1С (ИТС 8.3.27, «Руководство администратора», полные тексты): гл. 8 — разд. 8.2, 8.9.1, 8.9.2, 8.10.2.3, 8.10.2.5, 8.10.2.7, 8.10.3 (https://its.1c.ru/db/v8327doc/content/107/hdoc; конспекты `../its-docs/adm-gl08-veb-servery-p1.md`, `-p2.md`); разд. 4.3.8.2, 4.3.9, 5.2.4, 8.4.3.2.1; прил. 3.17 (в том числе 3.17.13, 3.17.16), 7.3.3, 7.3.4. «Руководство разработчика», гл. 17.4 «Стандартный интерфейс OData» — конспект `../its-docs/dev-gl17-integraciya.md`. Методички: 5977 (2020), 5944 (2018), 5949 (2018), 6034 (2025), 6029 (2026).

Сторонние: MDN (`mdn/content`) — `Strict-Transport-Security`, `X-Frame-Options`, `Content-Security-Policy/frame-ancestors`, `X-Content-Type-Options`, `Referrer-Policy`; ключи OpenSSL `s_client` и `curl` — общеизвестные, в сессии не перечитывались.

## Что не удалось подтвердить

1. Флаги `DisableQUIC`/`DisableTLS13`/`DisableLegacyTLS`: применимость к WS 2019 и какие версии считаются «Legacy TLS».
2. TLS 1.0/1.1 по умолчанию на WS 2025: таблица протоколов — включены, статья об устаревании — выключены в выпусках с 2024 года (кроме вышедших).
3. Действие `DisabledByDefault` на современных Windows (нет в справочнике 2025 года, есть в руководстве AD FS).
4. Нужна ли перезагрузка после `Enable-/Disable-TlsCipherSuite` (две страницы Microsoft противоречат).
5. (Закрыто: значения `CRYPT_PROTOCOL` уточнены 20.10.2026, раздел 3.5.)
6. Поставщик `Negotiate:Kerberos`; умолчание `authPersistNonNTLM` (справочник и схема — `false`, статья поддержки — «по сеансу» с 2012 R2). (`useAppPoolCredentials` подтверждён схемой IIS 10.)
7. Достаточность SPN на `WEB01$` для отдельной A-записи и покрытие `HTTP` SPN-ом `HOST/<компьютер>`.
8. Extended Protection `Require` с тонким клиентом и HTTP-клиентами 1С; `SslNegotiateCert` по требованию при TLS 1.3 и роль `clientcertnegotiation`.
9. `DisableTLS13` / `/HttpsForceTLS1_2` как обход для RSA-клиентских сертификатов 1С (вывод из двух утверждений ИТС).
10. Влияние HSTS на тонкий клиент 1С.
11. Делегирование от IIS к Linux-кластеру (`usr1cv8/…`) и KCD для публикации 1С — в документации 1С не описаны.
12. Разная аутентификация для `/demo/hs` и `/demo` через `<location>` по URL-пути без каталога.
13. От чьего имени `wsisapi.dll` читает файлы при анонимной аутентификации; доступ `IUSR` к `bin` 1С.
14. `ipSecurity` и IPv6 (`::1`); заблокирована ли секция `ipSecurity` по умолчанию.
15. Длительность блокировки `dynamicIpSecurity`, вид записей в режиме «только журнал» (разнобой значений в образцах Microsoft подтверждён).
16. Подстатус отказа URL Authorization; отклонение запроса, не подошедшего ни под одно разрешение.
17. Как ведут себя `denyUrlSequences` с `:` и `allowHighBitCharacters="false"` на реальных URL 1С (методы OData, двоеточия в литералах `datetime'…'` и кириллица в именах ресурсов подтверждены по ИТС 20.10.2026).
18. Источник событий Schannel; связь `maxUrlSegments` сайта с подстатусом 404.20. (Тип входа 8 и каталог HTTPERR уточнены 20.10.2026.)
19. Команды, собранные по образцам, а не взятые из документации: `appcmd set site /+bindings.[…,sslFlags='1']`, `netsh http update sslcert` (сохранение флагов), `/userName:""`, `logExtFileFlags` с `Host`/`ProtocolVersion`. (`/removeServerHeader`, `/useAppPoolCredentials`, `add site /bindings:`, `certutil -urlfetch -verify` уточнены 20.10.2026.)
20. Имя шаблона AD CS `WebServer` для `Get-Certificate`; создание запроса сертификата из диспетчера IIS 10.0.
21. `curl.exe` на WS 2016; поведение OpenSSL 3 на Ubuntu с TLS 1.0/1.1 (`SECLEVEL=0`); промежуточные ЦС в `Cert:\LocalMachine\CA` как источник цепочки для Schannel.
22. Добавлено при сверке 20.10.2026: фактическое `loadUserProfile` в `applicationPoolDefaults`; с какой сборки Windows Server пароли в конфигурации шифруются `IISCngProvider`; чувствительность имён атрибутов к регистру.
