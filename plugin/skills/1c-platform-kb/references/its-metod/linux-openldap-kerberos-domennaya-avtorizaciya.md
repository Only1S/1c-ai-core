# ИТС-конспект (методические материалы): Настройка OpenLDAP и Kerberos для доменной авторизации в Linux
> Источник: статьи раздела «Методическая поддержка» портала 1С:ИТС (ссылки — в разделах). Это конспект своими словами, не дословный текст. Составлен 2026-10-10.

## Кратко: главные официальные рекомендации

1. Связка OpenLDAP + Kerberos (MIT) рассматривается как замена Active Directory в полностью Linux-окружении; настроенный сервер можно использовать для доменной аутентификации в платформе «1С:Предприятие» без AD.
2. Стенд статьи — Ubuntu 22.04 LTS. Для других дистрибутивов отличия, по словам авторов, минимальны и касаются в основном настроек самой ОС (например, сети).
3. Роли разносятся по отдельным хостам: DNS, сервер каталогов + Kerberos (KDC), сервер 1С:Предприятия, сервер PostgreSQL, клиентская машина с GUI.
4. До начала работ на каждом хосте задаётся полное доменное имя (`hostnamectl set-hostname`).
5. Нужен собственный DNS (bind9) с прямой и обратной зонами: адресация по FQDN вместо IP упрощает сопровождение. Рекурсивные запросы разрешаются только доверенным клиентам (ACL `trusted`), передача зон запрещена (`allow-transfer { none; }`), используется только IPv4 (`-4`).
6. Конфигурацию bind проверять до перезапуска: `named-checkconf` (пустой вывод = нет ошибок) и `named-checkzone` для каждой зоны. При включённом UFW — открыть профиль `Bind9`.
7. На каждом хосте сети DNS-сервер прописывается через отдельный файл Netplan и применяется через `netplan try` (автооткат по тайм-ауту, если сеть сломалась).
8. Перед заменой `sudo` на `sudo-ldap` задать пароль учётной записи root: пакеты взаимоисключающие, это страховка на случай проблем с установкой.
9. Конфигурация slapd строится с нуля в формате `cn=config`; штатные `/etc/ldap/slapd.d` и `/var/lib/ldap` при этом удаляются (примечание составителя: на сервере, где каталог уже содержит данные, это означает их потерю).
10. Управлять `cn=config` разрешено только локальному root через SASL EXTERNAL (`ldapi:///`).
11. Наборы схем подключаются в строго определённом порядке — атрибуты иерархически зависят друг от друга. Схемы Kerberos и sudo перед подключением конвертируются в LDIF.
12. Для базы `mdb` обязателен `olcDbMaxsize` (в байтах): он должен превышать ожидаемый размер базы с учётом роста, и на файловой системе должно быть столько свободного места. Каталог `olcDbDirectory` должен существовать до загрузки конфигурации.
13. Для `olcRootDN` правила ACL не нужны — у него полный доступ к базе.
14. Вместо анонимных запросов используется служебный пользователь `nssproxy` с правом чтения; остальные пользователи видят только свои записи и могут сами менять пароль. Обязательно проверить, что прочие учётные записи доступа к дереву не имеют.
15. TLS для OpenLDAP авторы называют крайне рекомендуемым: и для поддержки аутентификации LDAP с механизмом SASL EXTERNAL, и для конфиденциальности и целостности данных. Сертификат должен быть подписан доверенным УЦ; собственный УЦ допустим в тестовой среде.
16. УЦ рекомендуется держать на отдельной машине без сети, каталог УЦ — на отдельном носителе, подключаемом только на время выпуска сертификатов (носитель — в сейф). Ключ УЦ — 4096 бит, зашифрован AES-256, пароль хранить надёжно: без него новые сертификаты не выпустить.
17. Закрытые ключи клиентов УЦ в норме не должны храниться в самом УЦ (клиент присылает только CSR); хранение всех ключей в одном месте — упрощение для теста, для организаций с серьёзными требованиями ИБ может быть неприемлемо.
18. «Клиентами» каталога считаются не только рабочие места пользователей, но и хост сервера 1С:Предприятия.
19. `/etc/nslcd.conf` содержит пароль привязки — права `600`, владелец `nslcd:nslcd`. В `nss_initgroups_ignoreusers` перечисляются все системные пользователи, чтобы машина оставалась работоспособной при недоступности каталога.
20. Домашние каталоги доменных пользователей создаются автоматически через `pam_mkhomedir`; доступ по SSH ограничивается директивой `AllowGroups`.
21. Сообщения `... not indexed` в журнале slapd устраняются добавлением индексов `olcDbIndex` (для учётных записей и отдельно для `krbPrincipalName`, `ou`).
22. Kerberos хранит свою базу в OpenLDAP (контейнер `cn=kerberos,ou=services,...`), работает от имени отдельной записи `krbadmin`. Доступ к поддереву Kerberos — только `krbadmin` и администратору каталога; `nssproxy` не должен даже видеть контейнер.
23. Пароль `krbadmin` для KDC сохраняется в stash-файле в закрытом каталоге `/etc/krb5.d` (права только владельцу). Мастер-пароль базы Kerberos и пароль `krbadmin` обязательно сохранить.
24. ACL Kerberos (`kadm5.acl`) — это не ACL OpenLDAP. Правило `*/admin@REALM *` даёт права администратора области всем принципалам с суффиксом `/admin`.
25. Журналы slapd, krb5kdc и kadmind выводятся в отдельные файлы через rsyslog с ротацией logrotate (ежедневно, 7 копий, сжатие).

---

## Статья: «Настройка OpenLDAP и Kerberos для использования доменной авторизации в Linux»

- **Дата публикации:** 30.12.2022
- **Ссылка:** https://its.1c.ru/db/metod8dev/content/6010/hdoc
- **Рубрика на ИТС:** «Технологические вопросы крупных внедрений»

### Оценка применимости на октябрь 2026: частично устарело

Оценка составителя конспекта (в самой статье её нет).

- **Что остаётся верным.** Общая схема (свой DNS с прямой и обратной зонами → slapd в формате `cn=config` → TLS → клиенты через nslcd/NSS/PAM → KDC с хранением базы в LDAP), набор компонентов (bind9, slapd, nslcd, MIT Kerberos), структура LDIF-файлов, принципы разграничения доступа, требования к хранению ключей и паролей.
- **Версии.** Статья написана под Ubuntu 22.04 LTS (конец 2022 г.). К октябрю 2026 г. вышли более новые LTS-выпуски; версии OpenLDAP, MIT Kerberos, bind9, sudo в них другие, поэтому имена пакетов, набор файлов в `/etc/ldap/schema`, поведение утилит нужно сверять с фактической системой.
- **Листинги частично перенесены из более старых материалов** и не соответствуют описанному стенду: в выводе проверки ACL фигурирует чужой суффикс `dc=pacman,dc=loc`, в проверке доступа — несуществующий пользователь `pablo`, вывод запуска slapd имеет вид старого init-скрипта, в списках ключей присутствуют типы шифрования на одиночном DES.
- **Криптография.** В `kdc.conf` перечислены `des3-hmac-sha1`, `arcfour-hmac`, `des-hmac-sha1`, `des-cbc-md5`, `des-cbc-crc` — слабые и устаревшие типы шифрования; в актуальных версиях MIT Kerberos их поддержка сокращена или отключена, для новой установки разумно оставлять AES (требует проверки по документации используемой версии).
- **rsyslog.** Конструкция `& ~` — устаревший синтаксис отбрасывания сообщения (в современных версиях rsyslog применяется `& stop`); работает ли старый вариант — проверить на своей версии.
- **sudo-ldap.** Наличие пакета `sudo-ldap` в актуальном выпуске дистрибутива нужно проверить отдельно.
- **Внешние DNS.** В `forwarders` указаны публичные адреса 8.8.8.8 и 8.8.4.4 — в реальной сети подставляются свои вышестоящие серверы.
- **Неполнота и внутренние противоречия.** В статье смешаны суффиксы `da-test.loc` и `da-test.ru`, отсутствует команда выпуска корневого сертификата, не показано создание `ou=services` и CRL-файла, есть опечатки в командах (см. следующий подраздел). Выполнять её «как есть» копированием нельзя — только как план работ с проверкой каждого шага.
- **1С.** Статья заканчивается на настройке KDC и индексов. Настройка самого сервера 1С:Предприятия (служебный принципал, keytab для службы, параметры аутентификации пользователей информационной базы) в ней **не описана**.

### Сводка несогласованностей источника (важно при использовании)

| № | Где | Что в источнике | Пометка |
|---|-----|-----------------|---------|
| 1 | Вводные данные, разделы 1–8 | Заявлен домен `da-test.ru`, но таблица хостов и зоны DNS — `da-test.loc`; `hostnamectl`, LDAP-суффикс, сертификаты, `krb5.conf` — `da-test.ru`; ответы инсталлятору Kerberos — `DA-TEST.LOC`, `da1.da-test.loc`, `da1.test.loc` | ⚠ в источнике неясно. В DNS из раздела 2 имён `*.da-test.ru` нет. На практике выбрать один суффикс и применять везде |
| 2 | Раздел 2, ACL bind | Блок начинается с `cl "trusted"`, точка с запятой стоит после комментария | исправлено по смыслу (`acl`, `;` перед комментарием) |
| 3 | Раздел 2, обратная зона | Для зоны `2.0.10.in-addr.arpa` (/24) PTR-записи заданы двумя октетами (`2.1`, `2.2`…), пример ответа `nslookup` содержит имя с «приклеенным» суффиксом зоны | ⚠ в источнике неясно; проверять `named-checkzone` и `nslookup` |
| 4 | Раздел 4, LDIF-файлы | Между записями в нескольких LDIF потеряны пустые строки-разделители | исправлено по смыслу |
| 5 | Раздел 4, вывод проверки ACL | Показаны правила с `dc=pacman,dc=loc`, `userPKCS12`, `shadowLastChange`, Kerberos — которых на этом шаге ещё нет; в списке схем нет `ppolicy` | листинг из другого материала |
| 6 | Раздел 5 | Файл назван `init-units.ldif`, а применяется `4-users+groups.ldif`; `dc: example` при DN `dc=da-test,dc=ru`; группа `cn=test.group` с `cn: tester`, в выводе — `cn=testing` | ⚠ в источнике неясно |
| 7 | Разделы 5 и 6 | Команды раздела 5 используют StartTLS (`-ZZ`), хотя TLS настраивается только в разделе 6 | ⚠ порядок шагов в источнике неясен |
| 8 | Разделы 5–7 | Часть изменений `cn=config` выполняется от имени `cn=admin,dc=da-test,dc=ru`, хотя по ACL раздела 4 управлять `cn=config` может только root через SASL EXTERNAL | ⚠ в источнике неясно; в других местах той же статьи используется `-QY EXTERNAL -H ldapi:///` |
| 9 | Раздел 6 | `sudo cd`, `sudo umask`, `sudo echo 1000 > serial` — встроенные команды оболочки и перенаправление под `sudo` в таком виде не дают нужного эффекта | ⚠ по смыслу блок выполняется в оболочке root |
| 10 | Раздел 6 | Вместо команды выпуска корневого сертификата повторён фрагмент `openssl.cnf` | ⚠ команда в источнике отсутствует |
| 11 | Раздел 6 | Во втором варианте `ldap.conf` указано `BASE dc=example,dc=com` | ⚠ в остальных местах `dc=da-test,dc=ru` |
| 12 | Раздел 7 | Используется `TLS_CRLFILE /etc/ssl/rootca.crl`, но создание CRL не описано; `systemctl restart service nscd` | ⚠ / исправлено по смыслу |
| 13 | Раздел 8 | Контейнер `cn=kerberos,ou=services,...` — создание `ou=services` нигде не показано; файл `init-kerberos.ldif` применяется как `9.1-kerberos.ldif`; `sudo namo`; обещан принципал для `tester`, создаётся для `user1` | ⚠ / исправлено по смыслу |

### Назначение и стенд

Цель статьи — развернуть OpenLDAP как службу каталогов и Kerberos как службу аутентификации для Linux-окружения, чтобы затем использовать их для доменной аутентификации в «1С:Предприятии» без Active Directory.

Используется пять машин: четыре сервера и одна клиентская с графическим интерфейсом.

- Домен (по тексту вводных данных): `da-test.ru`
- Сеть: `10.0.2.0`, маска `255.255.255.0`

| Роль | Имя хоста (как в таблице источника) | IP |
|------|--------------------------------------|----|
| Сервер имён (DNS) | ns1.da-test.loc | 10.0.2.1 |
| Сервер OpenLDAP и Kerberos | da1.da-test.loc | 10.0.2.2 |
| Сервер 1С:Предприятия | app1.da-test.loc | 10.0.2.3 |
| Сервер PostgreSQL | dbms1.da-test.loc | 10.0.2.4 |
| Клиентский компьютер с GUI | pc1.da-test.loc | 10.0.2.5 |

⚠ в источнике неясно: суффикс `.loc` в таблице и DNS против `.ru` во всех остальных разделах (см. сводку, п. 1).

### 1. Предварительная настройка

На каждой машине задаётся полное имя хоста; `<имя хоста>` — короткое имя (`ns1`, `da1` и т. д.):

```bash
sudo hostnamectl set-hostname <имя хоста>.da-test.ru
```

### 2. Настройка сервера имён (bind9)

Сервер имён ставится на отдельный хост (`ns1`). Смысл: хосты должны находить друг друга по именам, а не по IP.

**Установка и режим IPv4.**

```bash
sudo apt install bind9 bind9utils bind9-doc
sudo nano /etc/default/named
```

В `/etc/default/named` к значению `OPTIONS` добавляется `-4` (IPv6 в статье не используется — для локальной сети предприятия достаточно IPv4):

```
OPTIONS="-u bind -4"
```

```bash
sudo systemctl restart bind9
```

**Опции: `/etc/bind/named.conf.options`.** Перед блоком `options` добавляется список доверенных клиентов — тех, кому разрешены рекурсивные запросы (отдельные адреса или подсеть целиком):

```
acl "trusted" {
        10.0.2.1;      # ns1.da-test.loc
        10.0.2.0/24;
};
```

(исправлено по смыслу: в источнике блок начинается с `cl "trusted"`, а `;` в первой строке стоит после комментария)

Внутри `options`, после параметра `directory`:

```
recursion yes;                 # разрешить рекурсивные запросы
allow-recursion { trusted; };  # ...но только клиентам из acl "trusted"
listen-on { 10.0.2.1; };       # адрес самого DNS-сервера
allow-transfer { none; };      # передача зон по умолчанию запрещена

forwarders {
    8.8.8.8;
    8.8.4.4;
};
```

`forwarders` — серверы, которым переадресуются запросы по внешним именам (сокращает трафик к внешним DNS). Смысл правок в целом: обращаться к вашему DNS за внешними доменами смогут только доверенные хосты.

**Зоны: `/etc/bind/named.conf.local`.**

```
zone "da-test.loc" {
    type primary;
    file "/etc/bind/zones/db.da-test.loc"; # файл прямой (forward) зоны
};

zone "2.0.10.in-addr.arpa" {
    type primary;
    file "/etc/bind/zones/db.2.0.10";      # файл обратной (reverse) зоны подсети 10.0.2.0/24
};
```

**Прямая зона.** Каталог зон создаётся вручную, файл делается из шаблона `db.local`:

```bash
sudo mkdir /etc/bind/zones
sudo cp /etc/bind/db.local /etc/bind/zones/db.da-test.loc
sudo nano /etc/bind/zones/db.da-test.loc
```

Правки в файле:

1. Заменить SOA-запись. Префикс `admin` — имя пользователя-администратора на хосте DNS.
2. Удалить три шаблонные записи после SOA (`@ IN NS localhost.`, `@ IN A 127.0.0.1`, `@ IN AAAA ::1`).
3. Добавить NS-запись своего сервера (точка в конце имени обязательна).
4. Добавить A-записи всех хостов зоны.

Итоговый файл:

```
$TTL    604800
@       IN      SOA     ns1.da-test.loc. admin.da-test.loc. (
                  3     ; Serial
             604800     ; Refresh
              86400     ; Retry
            2419200     ; Expire
             604800 )   ; Negative Cache TTL
;
; NS-записи
    IN      NS      ns1.da-test.loc.

; Серверы имен - A-записи
ns1.da-test.loc.          IN      A      10.0.2.1

; 10.0.2.0/24 - A-записи
da1.da-test.loc.          IN      A      10.0.2.2
app1.da-test.loc.         IN      A      10.0.2.3
dbms1.da-test.loc.        IN      A      10.0.2.4
pc1.da-test.loc.          IN      A      10.0.2.5
```

**Обратная зона.** Делается из шаблона `db.127`:

```bash
sudo cp /etc/bind/db.127 /etc/bind/zones/db.2.0.10
sudo nano /etc/bind/zones/db.2.0.10
```

Правки: та же SOA-запись; удалить две шаблонные записи после SOA (`@ IN NS localhost.` и `1.0.0 IN PTR localhost.`); добавить NS-запись и PTR-записи всех хостов подсети. Итоговый файл:

```
$TTL    604800
@       IN      SOA     ns1.da-test.loc. admin.da-test.loc. (
                              3         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
; Серверы имен - NS-записи
      IN      NS      ns1.da-test.loc.

; PTR-записи
2.1   IN      PTR     ns1.da-test.loc.    ; 10.0.2.1
2.2   IN      PTR     da1.da-test.loc.    ; 10.0.2.2
2.3   IN      PTR     app1.da-test.loc.   ; 10.0.2.3
2.4   IN      PTR     dbms1.da-test.loc.  ; 10.0.2.4
2.5   IN      PTR     pc1.da-test.loc.    ; 10.0.2.5
```

⚠ в источнике неясно: по тексту статьи первый столбец — «два последних октета в обратном порядке», при этом зона объявлена для сети /24 (`2.0.10.in-addr.arpa`), а в примере ответа `nslookup 10.0.2.3` показано `3.2.0.10.in-addr.arpa   name = app1.da-test.loc.2.0.10.in-addr.arpa.` Формат первого столбца нужно проверить на своём стенде (`named-checkzone` + обратный `nslookup`).

**Проверка и запуск.**

```bash
sudo named-checkconf
sudo named-checkzone da-test.loc /etc/bind/zones/db.da-test.loc
sudo named-checkzone 2.0.10.in-addr.arpa /etc/bind/zones/db.2.0.10
sudo systemctl restart bind9
sudo ufw allow Bind9
```

- `named-checkconf` при отсутствии синтаксических ошибок ничего не выводит; при ошибке — исправить и повторить.
- `named-checkzone <зона> <файл>`: оба аргумента должны соответствовать `named.conf.local`; ожидаемый ответ — `zone da-test.loc/IN: loaded serial 3` и `OK`.
- `ufw allow Bind9` нужен, только если используется брандмауэр UFW.

**Настройка клиентов DNS (на каждом хосте сети).** Сначала определяется интерфейс частной сети:

```bash
ip address
ip address show to 10.0.2.0/24
```

В примере это `enp0s3`. В Ubuntu 22.04 сеть настраивается через Netplan, поэтому создаётся отдельный файл:

```bash
sudo nano /etc/netplan/00-private-nameservers.yaml
```

```yaml
network:
    version: 2
    ethernets:
        enp0s3:                             # частный сетевой интерфейс
            nameservers:
                addresses:
                - 10.0.2.1                  # IP-адрес ns1.da-test.loc
                search: [ da-test.loc ]     # зона DNS
```

```bash
sudo netplan try
sudo resolvectl status
```

- `netplan try` применяет конфигурацию с подтверждением: если в течение тайм-аута (в примере 120 секунд) не нажать ENTER, изменения откатываются — защита от потери связи.
- В `resolvectl status` в секции нужного интерфейса должны быть `DNS Servers: 10.0.2.1` и `DNS Domain: da-test.loc`.

Проверка разрешения имён:

```bash
nslookup app1
nslookup 10.0.2.3
```

Короткое имя `app1` дополняется до `app1.da-test.loc` благодаря параметру `search`; ожидается адрес `10.0.2.3` от сервера `10.0.2.1#53`. Обратный запрос должен вернуть имя хоста.

### 3. Установка OpenLDAP и Kerberos (хост da1)

**Страховка перед заменой sudo.** Вместо `sudo` ставится `sudo-ldap` — он позволяет выполнять команды с повышенными правами, даже если пользователю локально роль sudo не назначена. Пакеты `sudo` и `sudo-ldap` взаимоисключающие, поэтому заранее задаётся пароль учётной записи root — чтобы не остаться без административного доступа, если установка пойдёт не так.

```bash
passwd
```

(в источнике команда приведена именно так, без `sudo` и имени пользователя; по тексту речь о пароле root)

**Пакеты.**

```bash
sudo apt-get install slapd ldap-utils krb5-kdc-ldap sudo-ldap
```

Ответы на вопросы установщика (как в источнике):

| Вопрос | Значение |
|--------|----------|
| Пароль учётной записи admin для конфигурации OpenLDAP | свой |
| Область Kerberos (realm) | `DA-TEST.LOC` |
| Сервер Kerberos области | `da1.da-test.loc` |
| Управляющий сервер области | `da1.test.loc` |

⚠ в источнике неясно: здесь суффикс `.loc` (и опечатка `da1.test.loc`), в разделе 8 область — `DA-TEST.RU`, сервер — `da1.da-test.ru`. Авторы отмечают, что ошибку, допущенную при установке, можно исправить позже (файл `/etc/krb5.conf` в разделе 8 всё равно создаётся заново).

Проверка, что пакеты установлены (ожидается четыре строки со статусом `install`):

```bash
dpkg --get-selections|egrep '(slapd|ldap-utils|krb5-kdc-ldap|sudo-ldap)'
```

### 4. Настройка OpenLDAP

Настройка идёт применением серии LDIF-файлов; их удобно держать в одном рабочем каталоге.

```bash
mkdir ~/ldap
cd ~/ldap
```

#### 4.1. Сброс конфигурации по умолчанию

**Предупреждение (составителя, по смыслу команд):** шаг удаляет и конфигурацию, и базу данных slapd, созданные при установке пакета. На сервере, где каталог уже содержит данные, это означает их потерю.

```bash
sudo systemctl stop slapd
sudo rm -rf /etc/ldap/slapd.d
sudo rm -rf /var/lib/ldap
mkdir /etc/ldap/slapd.d
```

(последняя команда в источнике без `sudo`)

#### 4.2. Начальная конфигурация `cn=config`

Файл `init-ldap-config.ldif`:

```ldif
dn: cn=config
objectClass: olcGlobal
cn: config
olcPidFile: /var/run/slapd/slapd.pid
olcArgsFile: /var/run/slapd/slapd.args

dn: olcDatabase={0}config,cn=config
objectClass: olcDatabaseConfig
olcDatabase: {0}config
olcAccess: to *
  by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth" manage

dn: cn=schema,cn=config
objectClass: olcSchemaConfig
cn: schema
```

(исправлено по смыслу: в источнике потеряна пустая строка между первой и второй записями)

Что здесь задаётся:

- `cn=config` — корень дерева конфигурации; `olcPidFile` и `olcArgsFile` — куда slapd пишет PID и аргументы запуска;
- `olcDatabase={0}config` — служебная база конфигурации; правило `olcAccess` разрешает управлять ею только локальному root (uid=0, gid=0) через SASL EXTERNAL;
- `cn=schema,cn=config` — контейнер для наборов схем.

Инициализация, проверка, права, запуск только по IPv4:

```bash
sudo slapadd -n 0 -F /etc/ldap/slapd.d -l init-ldap-config.ldif
sudo slaptest -uF /etc/ldap/slapd.d
sudo chown -R openldap:openldap /etc/ldap/slapd.d
sudo chmod 750 /etc/ldap/slapd.d
```

`slaptest` должен ответить `config file testing succeeded`. Так как DNS настроен только на IPv4, в `/etc/default/slapd` задаётся:

```
SLAPD_OPTIONS="-4"
```

#### 4.3. Отдельный журнал slapd

В `/etc/rsyslog.conf` после инструкции `$IncludeConfig` добавляется:

```
# Файл журнала службы каталогов /var/log/slapd.log
if $programname == 'slapd' then /var/log/slapd.log
& ~
```

```bash
sudo touch /var/log/slapd.log
sudo chmod 0640 /var/log/slapd.log
sudo chown syslog:adm /var/log/slapd.log
sudo systemctl restart rsyslog
```

Ротация — файл `/etc/logrotate.d/slapd`:

```
/var/log/slapd.log {
 daily
 missingok
 rotate 7
 compress
 delaycompress
 notifempty
}
```

Проверка ротации, запуск службы и контроль:

```bash
sudo logrotate -df /etc/logrotate.conf
sudo systemctl start slapd
sudo tail /var/log/slapd.log
sudo ss -tan | grep 389
sudo ss -xa | grep ldap
sudo ldapsearch -QLLL -Y EXTERNAL -H ldapi:/// -b 'cn=config' dn
```

Ожидается: в журнале строка `slapd starting`; слушается TCP-порт 389 (порт по умолчанию) и сокет `/var/run/slapd/ldapi`; в конфигурации четыре записи — `cn=config`, `cn=schema,cn=config`, `olcDatabase={-1}frontend,cn=config`, `olcDatabase={0}config,cn=config`.

#### 4.4. Динамические модули

Нужны два модуля: `back_mdb` (механизм хранения базы) и `back_monitor` (ветка с текущим состоянием службы). Файл `switch-dynamic-modules.ldif`:

```ldif
dn: cn=module,cn=config
objectClass: olcModuleList
cn: module
olcModulePath: /usr/lib/ldap
olcModuleLoad: back_mdb.la
olcModuleLoad: back_monitor.la
```

```bash
sudo ldapadd -QY EXTERNAL -H ldapi:/// -f switch-dynamic-modules.ldif
```

#### 4.5. Наборы схем

Набор схем — хранилище объектных классов и атрибутов одной предметной области. Схемы из пакетов `krb5-kdc-ldap` и `sudo-ldap` поставляются не в LDIF, их нужно сконвертировать.

```bash
zcat /usr/share/doc/krb5-kdc-ldap/kerberos.schema.gz > ~/ldap/kerberos.schema
cp /usr/share/doc/sudo-ldap/schema.OpenLDAP ~/ldap/sudo.schema
```

Скрипт `convert-schema-to-ldif.sh`:

```bash
#!/bin/bash
SCHEMAD=~/ldap

tmpd=`mktemp -d`
pushd ${tmpd} >>/dev/null
echo '' > convert.dat

for schema in ${SCHEMAS} ; do
    echo include ${SCHEMAD}/${schema} >> convert.dat
done

mkdir output
slaptest -f convert.dat -F ./output
if [ $? -ne 0 ] ; then
    echo "slaptest conversion failed"
    exit
fi
for schema in ${SCHEMAS} ; do
    fullpath=${SCHEMAD}/${schema}
    schema_name=`basename ${fullpath} .schema`
    schema_dir=`dirname ${fullpath}`
    ldif_file=${schema_name}.ldif

    find . -name *${schema_name}.ldif -exec mv '{}' ./${ldif_file} \;
    sed -i "/dn:/ c dn: cn=${schema_name},cn=schema,cn=config" ${ldif_file}
    sed -i "/cn:/ c cn: ${schema_name}" ${ldif_file}
    sed -i '/structuralObjectClass/ d' ${ldif_file}
    sed -i '/entryUUID/ d' ${ldif_file}
    sed -i '/creatorsName/ d' ${ldif_file}
    sed -i '/createTimestamp/ d' ${ldif_file}
    sed -i '/entryCSN/ d' ${ldif_file}
    sed -i '/modifiersName/ d' ${ldif_file}
    sed -i '/modifyTimestamp/ d' ${ldif_file}
    sed -i '/^ *$/d' ${ldif_file}

    mv ${ldif_file} ${schema_dir}
done
popd >>/dev/null
rm -rf $tmpd
```

Логика скрипта: во временном каталоге формируется файл с директивами `include` для схем из переменной `SCHEMAS`, `slaptest` конвертирует их в формат `cn=config`, затем из полученных LDIF вычищаются служебные атрибуты и правятся `dn`/`cn`; результат кладётся рядом с исходными `.schema`.

```bash
chmod +x convert-schema-to-ldif.sh
SCHEMAS='kerberos.schema sudo.schema' convert-schema-to-ldif.sh
ls ~/ldap | egrep '(kerberos.ldif|sudo.ldif)'
```

(в источнике скрипт вызывается без `./`; ожидается сообщение `config file testing succeeded` и появление `kerberos.ldif` и `sudo.ldif`)

Перенос к остальным схемам и права:

```bash
sudo mv ~/ldap/{kerberos.ldif,sudo.ldif} /etc/ldap/schema
sudo chown root:root /etc/ldap/schema/{kerberos.ldif,sudo.ldif}
sudo chmod 0644 /etc/ldap/schema/{kerberos.ldif,sudo.ldif}
```

Файл `include-schemas.ldif`. **Порядок строк важен** — атрибуты наборов иерархически связаны и должны объявляться с соблюдением иерархии; сконвертированные `kerberos` и `sudo` идут в конце:

```ldif
include: file:///etc/ldap/schema/core.ldif
include: file:///etc/ldap/schema/cosine.ldif
include: file:///etc/ldap/schema/inetorgperson.ldif
include: file:///etc/ldap/schema/collective.ldif
include: file:///etc/ldap/schema/corba.ldif
include: file:///etc/ldap/schema/duaconf.ldif
include: file:///etc/ldap/schema/openldap.ldif
include: file:///etc/ldap/schema/dyngroup.ldif
include: file:///etc/ldap/schema/java.ldif
include: file:///etc/ldap/schema/misc.ldif
include: file:///etc/ldap/schema/nis.ldif
include: file:///etc/ldap/schema/ppolicy.ldif
include: file:///etc/ldap/schema/kerberos.ldif
include: file:///etc/ldap/schema/sudo.ldif
```

```bash
sudo ldapadd -QY EXTERNAL -H ldapi:/// -f include-schemas.ldif
```

Ожидается по одной строке `adding new entry "cn=<набор>,cn=schema,cn=config"` на каждый набор.

⚠ в источнике неясно: в списке и в выводе `ldapadd` набор `ppolicy` есть, а в более позднем листинге проверки конфигурации его нет (`kerberos` там имеет индекс `{11}`, `sudo` — `{12}`). Перед применением сверить список с фактическим содержимым `/etc/ldap/schema`.

#### 4.6. База данных каталога

Хэш пароля администратора каталога (результат вида `{SSHA}...` нужно сохранить):

```bash
slappasswd -h '{SSHA}'
```

Файл `init-db.ldif` (в `olcRootPW` подставляется полученный хэш вместе с префиксом `{SSHA}`; в источнике на этом месте стоит пример хэша):

```ldif
dn: olcDatabase=mdb,cn=config
objectClass: olcMdbConfig
olcDatabase: mdb
olcSuffix: dc=da-test,dc=ru
olcDbDirectory: /var/lib/ldap
olcDbMaxsize: 1073741824
olcRootDN: cn=admin,dc=da-test,dc=ru
olcRootPW: {SSHA}<хэш, полученный slappasswd>
olcAccess: {0}to *
  by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth" manage
  by * break
olcAccess: {1}to attrs=userPassword
  by self write
  by anonymous auth
olcAccess: {2}to *
  by self read

dn: olcDatabase=monitor,cn=config
objectClass: olcDatabaseConfig
olcDatabase: monitor
```

Пояснения к параметрам:

- `olcDbDirectory` — каталог базы; атрибут обязательный, каталог должен существовать к моменту загрузки конфигурации.
- `olcDbMaxsize` — максимальный размер базы `mdb` **в байтах** (в примере 1073741824 = 1 ГиБ). Должен быть больше ожидаемого размера с учётом прироста; на файловой системе должно хватать места под базу такого размера.
- `olcRootDN` — DN администратора базы. Отдельные правила ACL ему не нужны: доступ к данным базы у него полный.
- Правило `{0}` (вся база): управление для root через SASL EXTERNAL; `by * break` — если субъект не совпал, продолжать разбор следующих правил.
- Правило `{1}` (атрибут `userPassword`): пользователь может менять свой пароль; анонимному клиенту разрешена только аутентификация.
- Правило `{2}` (всё остальное): пользователь читает собственную запись — это нужно для аутентификации через nslcd.
- Вторая запись подключает базу `monitor` (мониторинг).

Каталог базы, загрузка конфигурации, проверки:

```bash
sudo mkdir /var/lib/ldap
sudo chown openldap:openldap /var/lib/ldap
sudo chmod 0700 /var/lib/ldap
sudo ldapadd -QY EXTERNAL -H ldapi:/// -f init-db.ldif
sudo ldapsearch -QLLL -Y EXTERNAL -H ldapi:/// -b 'cn=config' dn olcAccess
sudo ldapwhoami -WD cn=admin,dc=da-test,dc=ru
```

- `ldapadd` должен добавить `olcDatabase=mdb,cn=config` и `olcDatabase=monitor,cn=config`.
- `ldapsearch ... dn olcAccess` показывает все записи конфигурации (модули, схемы, базы `{-1}frontend`, `{0}config`, `{1}mdb`, `{2}monitor`) с их ACL — так проверяется и корректность правил, и наличие добавленного. ⚠ Листинг в источнике содержит правила с суффиксом `dc=pacman,dc=loc` и правила, которые в этой статье появляются только в разделе 8, — ориентироваться на него как на эталон нельзя.
- `ldapwhoami` после ввода пароля должен вернуть `dn:cn=admin,dc=da-test,dc=ru`.

#### 4.7. Клиентские параметры на сервере и автозапуск

`/etc/ldap/ldap.conf` (нужен, чтобы не указывать сервер и базу в каждой команде; строки TLS пока закомментированы):

```
BASE  dc=da-test,dc=ru
URI  ldap://da1.da-test.ru
# TLS_CACERT /etc/ssl/certs/rootca.crt
# TLS_REQCERT demand
TIMELIMIT 15
TIMEOUT  20
```

```bash
sudo systemctl enable slapd
```

### 5. Инициализация пользователей и групп

⚠ Порядок шагов в источнике неясен: все команды этого раздела используют StartTLS (ключ `-ZZ`), а TLS на сервере настраивается только в разделе 6. Кроме того, файл `init-nssproxy.ldif` меняет `cn=config` от имени `cn=admin,dc=da-test,dc=ru`, тогда как ACL из раздела 4 разрешает это только root через SASL EXTERNAL (в разделе 8 аналогичное изменение ACL выполняется уже через `-QY EXTERNAL -H ldapi:///`).

#### 5.1. Корневой суффикс и организационные единицы

Создаются корневая запись базы и два контейнера — для пользователей и для групп. Файл `init-units.ldif`:

```ldif
dn: dc=da-test,dc=ru
dc: example
objectClass: top
objectClass: domain

dn: ou=users,dc=da-test,dc=ru
ou: Users
objectClass: top
objectClass: organizationalUnit
description: Пользователи организации

dn: ou=groups,dc=da-test,dc=ru
ou: Groups
objectClass: top
objectClass: organizationalUnit
description: Группы организации
```

⚠ в источнике неясно: значение `dc: example` не соответствует DN `dc=da-test,dc=ru` (по смыслу ожидается `dc: da-test`).

```bash
sudo ldapmodify -a -xZZWD cn=admin,dc=da-test,dc=ru -f 4-users+groups.ldif
ldapsearch -xZZLLLWD cn=admin,dc=da-test,dc=ru
```

⚠ в источнике файл создан под именем `init-units.ldif`, а в команде указан `4-users+groups.ldif` — подставлять фактическое имя своего файла. Вторая команда должна показать три созданные записи.

#### 5.2. Группы

| Группа | gidNumber | Назначение |
|--------|-----------|------------|
| `sysadmin` | 1100 | системные администраторы |
| `nssproxy` | 801 | служебная группа для опроса сервера вместо анонимных запросов |
| `tester` | 1101 | группа для проверки настроек |

Файл `init-groups.ldif`:

```ldif
dn: cn=sysadmin,ou=groups,dc=da-test,dc=ru
cn: sysadmin
objectClass: top
objectClass: posixGroup
gidNumber: 1100
description: Системные администраторы

dn: cn=nssproxy,ou=groups,dc=da-test,dc=ru
cn: nssproxy
objectClass: top
objectClass: posixGroup
gidNumber: 801
description: Служебная группа опроса сервера

dn: cn=test.group,ou=groups,dc=da-test,dc=ru
cn: tester
objectClass: top
objectClass: posixGroup
gidNumber: 1101
description: Группа для тестирования
```

(исправлено по смыслу: добавлена потерянная пустая строка перед третьей записью)

⚠ в источнике неясно: имя третьей группы задано тремя разными способами — DN `cn=test.group`, атрибут `cn: tester`, в выводе команды `cn=testing`. Дальше по статье (SSH `AllowGroups`, `getent group tester`) используется имя `tester`.

```bash
sudo ldapmodify -a -xZZWD cn=admin,dc=da-test,dc=ru -f init-groups.ldif
```

#### 5.3. Пользователи

| Пользователь | uidNumber / gidNumber | Оболочка | Назначение |
|--------------|-----------------------|----------|------------|
| `user1` | 1100 / 1100 | `/bin/bash` | основной рабочий пользователь |
| `nssproxy` | 801 / 801 | `/bin/false` | служебный, для опроса каталога без анонимного доступа |
| `tester` | 1101 / 1101 | `/bin/bash` | проверка применяемых настроек |

Связь пользователя с группой задаётся атрибутом `gidNumber`. Файл `init-users.ldif` (в источнике в `userPassword` у всех трёх записей стоит один и тот же пример SSHA-хэша; пароли затем всё равно задаются через `ldappasswd`):

```ldif
dn: cn=user1,ou=users,dc=da-test,dc=ru
uid: user1
gecos: User #1
objectClass: top
objectClass: account
objectClass: posixAccount
objectClass: shadowAccount
userPassword: {SSHA}<хэш>
shadowLastChange: 15140
shadowMin: 0
shadowMax: 99999
shadowWarning: 7
loginShell: /bin/bash
uidNumber: 1100
gidNumber: 1100
homeDirectory: /home/user1

dn: cn=nssproxy,ou=users,dc=da-test,dc=ru
uid: nssproxy
gecos: Network Service Switch Proxy User
objectClass: top
objectClass: account
objectClass: posixAccount
objectClass: shadowAccount
userPassword: {SSHA}<хэш>
shadowLastChange: 15140
shadowMin: 0
shadowMax: 99999
shadowWarning: 7
loginShell: /bin/false
uidNumber: 801
gidNumber: 801
homeDirectory: /home/nssproxy

dn: cn=tester,ou=users,dc=da-test,dc=ru
uid: tester
gecos: Tester
objectClass: top
objectClass: account
objectClass: posixAccount
objectClass: shadowAccount
userPassword: {SSHA}<хэш>
shadowLastChange: 15140
shadowMin: 0
shadowMax: 99999
shadowWarning: 7
loginShell: /bin/bash
uidNumber: 1101
gidNumber: 1101
homeDirectory: /home/tester
```

(исправлено по смыслу: добавлена потерянная пустая строка перед записью `tester`)

Добавление пользователей и установка паролей. `ldappasswd` сначала дважды спрашивает новый пароль изменяемой записи, затем пароль администратора каталога:

```bash
sudo ldapmodify -a -xZZWD cn=admin,dc=da-test,dc=ru -f init-users.ldif
sudo ldappasswd -xZZWD cn=admin,dc=da-test,dc=ru -S cn=user1,ou=users,dc=da-test,dc=ru
sudo ldappasswd -xZZWD cn=admin,dc=da-test,dc=ru -S cn=nssproxy,ou=users,dc=da-test,dc=ru
sudo ldappasswd -xZZWD cn=admin,dc=da-test,dc=ru -S cn=tester,ou=users,dc=da-test,dc=ru
```

Признак успеха в `/var/log/slapd.log` — пара строк вида `PASSMOD id="cn=...,ou=users,dc=da-test,dc=ru" new` и `RESULT ... err=0`.

#### 5.4. Право чтения для nssproxy

Чтобы `nssproxy` мог читать атрибуты учётных записей, в ACL базы добавляется для него право `read`. Файл `init-nssproxy.ldif`:

```ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcAccess
olcAccess: {0}to *
  by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth" manage
  by * break
-
add: olcAccess
olcAccess: {1}to attrs=userPassword
  by self write
  by anonymous auth
-
add: olcAccess
olcAccess: {2}to *
  by self read
  by dn.base="cn=nssproxy,ou=users,dc=da-test,dc=ru" read
```

(исправлено по смыслу: в источнике в DN внутри правила `{0}` лишний пробел — `cn=external ,cn=auth`)

```bash
sudo ldapmodify -xZZWD cn=admin,dc=da-test,dc=ru -f init-nssproxy.ldif
```

Проверки:

```bash
ldapsearch -xZZLLLWD cn=nssproxy,ou=users,dc=da-test,dc=ru "(objectClass=*)"
ldapsearch -xZZLLLWD cn=pablo,ou=users,dc=da-test,dc=ru "(objectClass=*)"
```

- От имени `nssproxy` запрос должен вернуть всё дерево каталога (DIT).
- От имени любой другой учётной записи доступ к дереву должен быть закрыт: ожидается `No such object (32)`. ⚠ В примере источника используется пользователь `pablo`, которого в статье никто не создавал, — для проверки подставить существующую запись (например, `tester`).

### 6. Настройка защищённого соединения (TLS)

**Зачем.** Авторы называют TLS для OpenLDAP крайне рекомендуемым: он нужен и для поддержки аутентификации LDAP с механизмом SASL EXTERNAL, и для конфиденциальности и целостности данных. Серверу требуются сертификат и закрытый ключ; сертификат должен быть подписан доверенным удостоверяющим центром (УЦ), в тестовой среде — собственным.

**Схема.** Создаётся собственная PKI: пара «закрытый ключ УЦ + самоподписанный корневой сертификат», затем ключ сервера каталогов и его сертификат, подписанный ключом УЦ. Клиентам достаточно знать только корневой сертификат: с ним они проверят любой сервер, чей сертификат подписан этим УЦ. Такие же пары можно выпускать и для других задач, например для HTTPS-публикаций на веб-сервере.

**Оговорки авторов.**

- УЦ рекомендуется размещать на отдельном компьютере без подключения к сети. В статье он для простоты размещён на сервере каталогов.
- Закрытые ключи клиентов УЦ в норме не хранятся в УЦ: клиент сам формирует пару и присылает только запрос на подпись (CSR), в котором содержится открытый ключ. В статье все ключи создаются и лежат в одном месте — это тестовый вариант, который для организации с серьёзными требованиями к безопасности может быть неприемлем.
- В боевой среде CSR обычно подписывает существующий доверенный (в том числе платный) УЦ; свой УЦ уместен, если нет корпоративного CA или это тест.
- Хорошая практика — хранить каталог УЦ на отдельном носителе, монтировать его только для выпуска сертификатов, а сам носитель держать в защищённом месте (сейф).

#### 6.1. Каталог УЦ

Создаётся каталог с правами только для владельца; `umask 066` задаёт, что новые файлы доступны на чтение и запись только создавшему их пользователю:

```bash
sudo mkdir /root/CA
sudo chmod u=rwx,g=,o= /root/CA
sudo cd /root/CA
sudo umask 066
```

⚠ Команды приведены как в источнике. `cd` и `umask` — встроенные команды оболочки, через `sudo` они не меняют состояние текущего сеанса; по смыслу весь раздел 6.1–6.4 выполняется в оболочке root, находясь в `/root/CA` (в разделе 8 авторы для похожей цели используют `sudo su -`).

В `/etc/ssl/openssl.cnf`, секция `[ CA_default ]`:

- `dir = ./demoCA` заменить на `dir = ./`;
- `default_days` — срок действия выпускаемых сертификатов, меняется по своему усмотрению.

Структура каталога УЦ; `index.txt` и `serial` служат базой данных учёта выпущенных ключей и сертификатов:

```bash
sudo mkdir certs crl newcerts private
sudo chmod 700 private
sudo touch index.txt
sudo echo 1000 > serial
```

#### 6.2. Ключ и корневой сертификат УЦ

Ключ УЦ — 4096 бит, защищён шифром AES-256. При генерации запрашивается пароль ключа — его нужно сохранить в надёжном месте: без него новые сертификаты выпустить не получится. Права `400` выставляются, чтобы ключ случайно не удалить.

```bash
sudo openssl genrsa -aes256 -out private/rootca.key 4096
sudo chmod 400 private/rootca.key
```

В `openssl.cnf` нужно убедиться, что секции `[ usr_cert ]` и `[ v3_ca ]` содержат:

```
[ usr_cert ]
# расширения, добавляемые при подписании запроса УЦ
basicConstraints=CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
nsComment = "OpenSSL Generated Certificate"
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer

[ v3_ca ]
# расширения типового УЦ
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer
basicConstraints = CA:true
keyUsage = cRLSign, keyCertSign
```

**Выпуск корневого сертификата.** ⚠ в источнике неясно: сама команда отсутствует — на её месте повторно напечатан приведённый выше фрагмент `openssl.cnf`. Из текста известны только её параметры:

- сертификат подписывается ключом `private/rootca.key`, результат — `certs/rootca.crt`;
- используется расширение `v3_ca` (это сертификат УЦ);
- алгоритм хэширования — SHA-256;
- задаётся срок действия в днях;
- через модификатор `subj` заносятся поля субъекта:

| Поле | Смысл | Значение в примере |
|------|-------|--------------------|
| C | страна | RU |
| ST | регион | Moscow |
| L | город | Moscow |
| O | организация | MyCompany |
| OU | подразделение | IT |
| CN | имя субъекта / FQDN | ca-server |
| emailAddress | адрес почты | admin@da-test.ru |

Просмотр содержимого сертификата:

```bash
sudo openssl x509 -in certs/rootca.crt -noout -text
```

#### 6.3. Ключ и сертификат сервера каталогов

Ключ сервера (в каталоге `/root/CA`):

```bash
sudo openssl genrsa -out private/da1.da-test.ru.key 4096
sudo chmod 400 private/da1.da-test.ru.key
```

Запрос на подпись. Название организации (`O=MyCompany`) должно совпадать с указанным в корневом сертификате; в `CN` — FQDN сервера каталогов:

```bash
sudo openssl req -sha256 -new -key private/da1.da-test.ru.key -out certs/da1.da-test.ru.csr -subj /C=RU/ST=Moscow/L=Moscow/O=MyCompany/OU=IT/CN=da1.da-test.ru/emailAddress=admin@da-test.ru
```

Подпись собственным УЦ (расширение `usr_cert`):

```bash
sudo openssl ca -extensions usr_cert -notext -md sha256 -keyfile private/rootca.key -cert certs/rootca.crt -in certs/da1.da-test.ru.csr -out certs/da1.da-test.ru.crt
sudo chmod 444 certs/da1.da-test.ru.crt
```

#### 6.4. Размещение ключевой информации

```bash
sudo mkdir /etc/ldap/ssl
sudo chown openldap:openldap /etc/ldap/ssl
sudo chmod 0500 /etc/ldap/ssl
sudo cp certs/da1.da-test.ru.crt private/da1.da-test.ru.key /etc/ldap/ssl
sudo chown openldap:openldap /etc/ldap/ssl/{da1.da-test.ru.crt,da1.da-test.ru.key}
sudo chmod 0400 /etc/ldap/ssl/{da1.da-test.ru.crt,da1.da-test.ru.key}
sudo cp certs/rootca.crt /etc/ssl/certs/
sudo chmod 0644 /etc/ssl/certs/rootca.crt
sudo rm -rf certs/da1.da-test.ru.csr
```

Последняя команда необязательна: запрос CSR после подписи больше не нужен.

Если УЦ вынесен на другую машину, ключи и подписанные сертификаты переносятся по сети (`scp`) или на съёмном носителе. Выпуск каждой новой пары «ключ — сертификат» состоит из трёх этапов:

1. сгенерировать секретный ключ и запрос на подпись;
2. подписать сертификат закрытым ключом УЦ (`rootca.key`);
3. перенести ключ и сертификат туда, где они будут использоваться.

#### 6.5. Включение TLS в slapd

```bash
cd ~/ldap
```

Файл `init-tls-config.ldif`:

```ldif
dn: cn=config
add: olcTLSVerifyClient
olcTLSVerifyClient: never
-
add: olcTLSCertificateFile
olcTLSCertificateFile: /etc/ldap/ssl/da1.da-test.ru.crt
-
add: olcTLSCertificateKeyFile
olcTLSCertificateKeyFile: /etc/ldap/ssl/da1.da-test.ru.key
-
add: olcTLSCACertificateFile
olcTLSCACertificateFile: /etc/ssl/certs/rootca.crt
```

Здесь задаются пути к сертификату и ключу сервера и к корневому сертификату УЦ; `olcTLSVerifyClient: never` — сертификат от клиентов не требуется.

```bash
sudo ldapmodify -QY EXTERNAL -H ldapi:/// -f init-tls-config.ldif
sudo ldapsearch -QLLLY EXTERNAL -H ldapi:/// -b cn=config -s base | grep -i tls
```

Вторая команда должна показать четыре атрибута `olcTLS*`.

`/etc/ldap/ldap.conf` с включённым TLS:

```
BASE            dc=example,dc=com
URI             ldap://da1.da-test.ru
TLS_CACERT      /etc/ssl/certs/rootca.crt
TLS_REQCERT     demand
TIMELIMIT       15
TIMEOUT         20
```

⚠ в источнике неясно: в этом варианте файла указано `BASE dc=example,dc=com`, хотя в разделах 4 и 7 — `BASE dc=da-test,dc=ru`.

Обычно изменения `cn=config` применяются без перезапуска, но чтобы подхватилась новая ключевая информация, slapd нужно перезапустить:

```bash
sudo systemctl restart slapd
sudo ldapsearch -xZZLLLWD cn=admin,dc=da-test,dc=ru -b cn=config -s base
```

Проверочный запрос с `-ZZ` должен вернуть запись `cn=config` с атрибутами `olcTLS*`. Имя сервера (`-H ldap://da1.da-test.ru`) указывать не нужно — оно берётся из `ldap.conf`. Механика проверки: при установлении соединения клиент получает подписанный сертификат сервера и проверяет его по имеющемуся у него корневому сертификату УЦ, ничего больше о сервере не зная.

### 7. Настройка подключения клиентов к OpenLDAP

Клиентскими считаются не только рабочие места пользователей, но и хост, на котором установлен сервер 1С:Предприятия, — на нём выполняются те же шаги.

#### 7.1. Пакеты и параметры клиента

```bash
sudo apt-get install ldap-utils libnss-ldapd libpam-ldapd
```

Ответы установщику (позже конфигурация всё равно правится вручную, но ответить нужно, чтобы пакеты корректно установились):

| Вопрос | Значение |
|--------|----------|
| URI сервера LDAP | `ldap://da1.da-test.ru` |
| База поиска сервера LDAP | `dc=da-test,dc=ru` |
| Имена настраиваемых служб | `group`, `netgroup`, `passwd`, `shadow` |

`/etc/ldap/ldap.conf` на клиенте:

```
BASE  dc=da-test,dc=ru
URI  ldap://da1.da-test.ru
TLS_CACERT /etc/ssl/certs/rootca.crt
TLS_REQCERT demand
TLS_CRLFILE /etc/ssl/rootca.crl
TIMELIMIT 15
TIMEOUT  20
```

Корневой сертификат УЦ (`rootca.crt`) и CRL-файл (`rootca.crl`) должны быть предварительно скопированы на клиент с сервера УЦ. ⚠ в источнике неясно: создание `rootca.crl` в статье не описано.

Проверка связи (должно вернуться дерево, начиная с `dn: dc=da-test,dc=ru`):

```bash
ldapsearch -xZZLLLWD cn=nssproxy,ou=users,dc=da-test,dc=ru
```

#### 7.2. Локальная служба имён LDAP: `/etc/nslcd.conf`

В `bindpw` указывается пароль записи `cn=nssproxy,ou=users,dc=da-test,dc=ru`, заданный в разделе 5:

```
uid nslcd
gid nslcd
uri ldap://da1.da-test.ru
base dc=da-test,dc=ru
binddn cn=nssproxy,ou=users,dc=da-test,dc=ru
bindpw <Пароль пользователя nssproxy>
rootpwmoddn cn=admin,dc=da-test,dc=ru
base group ou=groups,dc=da-test,dc=ru
base passwd ou=users,dc=da-test,dc=ru
base shadow ou=users,dc=da-test,dc=ru
bind_timelimit 5
timelimit 10
idle_timelimit 60
ssl start_tls
tls_reqcert allow
tls_cacertfile /etc/ssl/certs/rootca.crt
nss_initgroups_ignoreusers bin,daemon,games,lp,mail,nobody,nslcd,root,sshd,sync,uucp
nss_initgroups_ignoreusers sys,man,news,proxy,www-data,backup,list,irc,gnats,landscape
```

| Директива | Смысл |
|-----------|-------|
| `base`, `base group/passwd/shadow` | где в дереве каталога искать соответствующую информацию |
| `bind_timelimit 5` | не более 5 секунд на установление соединения с сервером |
| `timelimit 10` | не более 10 секунд ожидания ответа сервера |
| `idle_timelimit 60` | разрывать соединение после минуты простоя |
| `ssl start_tls` | обязательное использование TLS при подключении |
| `tls_reqcert`, `tls_cacertfile` | аналоги `TLS_REQCERT` и `TLS_CACERT` из `ldap.conf`: режим проверки сертификата сервера и путь к корневому сертификату |
| `nss_initgroups_ignoreusers` | пользователи, которых не нужно искать в каталоге; сюда вносятся все общесистемные учётные записи, чтобы с машиной можно было работать при недоступности сервера каталогов |

Файл теперь содержит данные для аутентификации, поэтому права ужесточаются:

```bash
sudo chmod 600 /etc/nslcd.conf
sudo chown nslcd:nslcd /etc/nslcd.conf
```

#### 7.3. NSS и службы

Проверить `/etc/nsswitch.conf`:

```
passwd:         compat ldap
group:          compat ldap
shadow:         compat ldap
hosts:          files dns
networks:       files
protocols:      db files
services:       db files
ethers:         db files
rpc:            db files
netgroup:       nis ldap
```

```bash
sudo systemctl enable nslcd
sudo systemctl restart nslcd
grep nssproxy /etc/passwd
sudo systemctl enable nscd
sudo systemctl restart nscd
```

(исправлено по смыслу: в источнике `sudo systemctl restart service nscd`)

- `grep nssproxy /etc/passwd` должен ничего не вывести — локальной учётной записи с таким именем на клиенте быть не должно.
- `nscd` — кэширующая служба службы имён; должна стартовать при загрузке.

Проверка получения данных из каталога:

```bash
getent passwd tester
getent group tester
getent shadow tester
```

Ожидается запись пользователя с uid/gid `1101`, домашним каталогом `/home/tester` и оболочкой `/bin/bash`; группа `tester` с gid `1101`. `getent shadow` выполняется от root (сведения о пароле доступны только ему). Успех означает, что рабочая станция находит пользователей и группы в OpenLDAP.

#### 7.4. Домашние каталоги и вход

Автосоздание домашних каталогов — в `/etc/pam.d/common-session` добавляется:

```
session required      pam_mkhomedir.so   skel=/etc/skel umask=0002
```

```bash
su - tester
```

Должно появиться приглашение командной строки пользователя `tester`.

**SSH.** По умолчанию sshd работает с PAM и, значит, поддерживает аутентификацию через LDAP; на всякий случай в `/etc/ssh/sshd_config` добавляется:

```
AddressFamily inet
AllowGroups sysadmin tester
SyslogFacility AUTHPRIV
PasswordAuthentication yes
AllowTcpForwarding no
ClientAliveInterval 120
ClientAliveCountMax 2
```

`AllowGroups` ограничивает перечень групп, пользователи которых могут входить по SSH. Проверка с любой другой машины (в источнике — с сервера имён):

```bash
ssh tester@da-test.ru
```

(в источнике в качестве адреса указан домен `da-test.ru`; по смыслу — имя клиентского хоста)

#### 7.5. Индексы для учётных записей

После первых входов в `/var/log/slapd.log` на сервере каталогов могут появиться строки вида `mdb_equality_candidates: (objectClass) not indexed` и `(uid) not indexed`. Убедиться, что индексов нет:

```bash
sudo ldapsearch -xZZLLLWD cn=admin,dc=da-test,dc=ru -b olcDatabase={1}mdb,cn=config olcDbIndex
```

Индексы создаются для атрибутов, упомянутых в журнале. Файл `init-account-indexes.ldif`:

```ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcDbIndex
olcDbIndex: default pres,eq
-
add: olcDbIndex
olcDbIndex: uid
-
add: olcDbIndex
olcDbIndex: cn,sn pres,eq,sub
-
add: olcDbIndex
olcDbIndex: objectClass eq
-
add: olcDbIndex
olcDbIndex: memberUid eq
-
add: olcDbIndex
olcDbIndex: uniqueMember eq
-
add: olcDbIndex
olcDbIndex: uidNumber
-
add: olcDbIndex
olcDbIndex: gidNumber eq
```

```bash
sudo ldapadd -xZZWD cn=admin,dc=da-test,dc=ru -f init-account-indexes.ldif
sudo ldapsearch -xZZLLLWD cn=admin,dc=da-test,dc=ru -b olcDatabase={1}mdb,cn=config olcDbIndex
```

Повторный запрос должен показать восемь значений `olcDbIndex`; ошибок `not indexed` по этим атрибутам в журнале после этого быть не должно. (⚠ здесь `cn=config` снова меняется от имени `cn=admin,...` — см. сводку несогласованностей, п. 8.)

### 8. Настройка Kerberos

Разворачивается центр распределения ключей (KDC) для области `DA-TEST.RU`, база которого хранится в OpenLDAP.

#### 8.1. Пакеты и проверка схемы

```bash
sudo apt-get install krb5-kdc krb5-pkinit krb5-admin-server wamerican libsasl2-modules-gssapi-mit
sudo ldapsearch -QLLLY EXTERNAL -H ldapi:/// -b cn=schema,cn=config dn | grep -i kerberos
sudo ldapsearch -QLLLY EXTERNAL -H ldapi:/// -b cn={11}kerberos,cn=schema,cn=config | grep NAME | cut -d' ' -f5 | sort
```

- Вторая команда должна найти набор схем Kerberos, установленный в разделе 4 (в примере — `cn={11}kerberos,cn=schema,cn=config`; индекс подставлять фактический).
- Третья выводит список объектов схемы. Если атрибутов Kerberos в каталоге нет, `kdb5_ldap_util` завершится ошибкой: `Kerberos Container create FAILED: No such object while creating realm 'DA-TEST.RU'`.

#### 8.2. Контейнер, группа и пользователь Kerberos в каталоге

Создаются контейнер для принципалов и учётная запись, от имени которой Kerberos работает с OpenLDAP. Файл `init-kerberos.ldif`:

```ldif
# Контейнер для Kerberos
dn: cn=kerberos,ou=services,dc=da-test,dc=ru
cn: kerberos
objectClass: top
objectClass: krbContainer

# Группа krbadmin
dn: cn=krbadmin,ou=groups,dc=da-test,dc=ru
objectClass: top
objectClass: posixGroup
cn: krbadmin
gidNumber: 800
description: Kerberos administrator's group.

# Пользователь krbadmin
dn: cn=krbadmin,ou=users,dc=da-test,dc=ru
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
objectClass: posixAccount
objectClass: top
cn: krbadmin
givenName: Kerberos Administrator
mail: kerberos.admin@da-test.ru
sn: krbadmin
uid: krbadmin
uidNumber: 800
gidNumber: 800
homeDirectory: /home/krbadmin
loginShell: /bin/false
displayname: Kerberos Administrator
```

(исправлено по смыслу: добавлена потерянная пустая строка между первой и второй записями)

⚠ в источнике неясно: родительский контейнер `ou=services,dc=da-test,dc=ru` в статье нигде не создаётся (в разделе 5 заведены только `ou=users` и `ou=groups`).

```bash
sudo ldapadd -xZZWD cn=admin,dc=da-test,dc=ru -f ~/ldap/9.1-kerberos.ldif
sudo ldappasswd -xZZWSD "cn=admin,dc=da-test,dc=ru" "cn=krbadmin,ou=users,dc=da-test,dc=ru"
```

⚠ в источнике файл назван `init-kerberos.ldif`, а в команде — `9.1-kerberos.ldif`. Пароль `krbadmin` рекомендуется сохранить в надёжном месте.

#### 8.3. `/etc/krb5.conf`

```ini
[logging]
 default = SYSLOG:INFO:LOCAL1
 kdc = SYSLOG:NOTICE:LOCAL1
 admin_server = SYSLOG:WARNING:LOCAL1

[libdefaults]
 default_realm = DA-TEST.RU
 dns_lookup_realm = false
 dns_lookup_kdc = false
 ticket_lifetime = 24h
 renew_lifetime = 7d
 forwardable = true

[realms]
 DA-TEST.RU = {
  kdc = da1.da-test.ru
  admin_server = da1.da-test.ru
  default_domain = da-test.ru
  database_module = openldap_ldapconf
 }

[domain_realm]
 .da-test.ru = DA-TEST.RU
 da-test.ru = DA-TEST.RU

[appdefaults]
 pam = {
  debug = false
  ticket_lifetime = 36000
  renew_lifetime = 36000
  forwardable = true
  krb4_convert = false
 }

[dbmodules]
 openldap_ldapconf = {
  db_library = kldap
  ldap_kerberos_container_dn = cn=kerberos,ou=services,dc=da-test,dc=ru
  ldap_kdc_dn = cn=krbadmin,ou=users,dc=da-test,dc=ru
  ldap_kadmind_dn = cn=krbadmin,ou=users,dc=da-test,dc=ru
  ldap_service_password_file = /etc/krb5.d/stash.keyfile
  ldap_servers = ldapi:///
  ldap_conns_per_server = 5
 }
```

Пояснений к параметрам в источнике нет. По содержимому файла: область ссылается (`database_module`) на секцию `[dbmodules]`, в которой указаны DN контейнера Kerberos из п. 8.2, DN записи `krbadmin` для KDC и для kadmind, файл с её паролем (`ldap_service_password_file`, создаётся в п. 8.5) и адрес сервера каталогов (`ldapi:///`).

#### 8.4. ACL и конфигурация KDC

ACL администратора Kerberos — отдельная сущность, не связанная с ACL OpenLDAP. Файл `/etc/krb5kdc/kadm5.acl`:

```
*/admin@DA-TEST.RU *
```

Файл `/etc/krb5kdc/kdc.conf`:

```ini
[kdcdefaults]
 kdc_ports = 88
 kdc_tcp_ports = 88

[realms]
 DA-TEST.RU = {
  #master_key_type = aes256-cts
  acl_file = /etc/krb5kdc/kadm5.acl
  dict_file = /usr/share/dict/words
  admin_keytab = /etc/krb5kdc/kadm5.keytab
  supported_enctypes = aes256-cts:normal aes128-cts:normal des3-hmac-sha1:normal arcfour-hmac:normal des-hmac-sha1:normal des-cbc-md5:normal des-cbc-crc:normal
 }
```

(о типах шифрования DES/3DES/RC4 — см. оценку применимости)

#### 8.5. Stash-файл и создание области

Закрытый каталог для файла с паролем (путь из `ldap_service_password_file`) и сохранение в него пароля `krbadmin`:

```bash
sudo mkdir /etc/krb5.d
sudo chmod u=rwx,g=,o= /etc/krb5.d
sudo kdb5_ldap_util -D "cn=admin,dc=da-test,dc=ru" stashsrvpw -f /etc/krb5.d/stash.keyfile cn=krbadmin,ou=users,dc=da-test,dc=ru
```

Создание записей Kerberos в каталоге (в поддереве `cn=kerberos,ou=services,dc=da-test,dc=ru`) и просмотр результата:

```bash
sudo kdb5_ldap_util -D "cn=admin,dc=da-test,dc=ru" create -subtrees "cn=kerberos,ou=services,dc=da-test,dc=ru" -r DA-TEST.RU -s
sudo ldapsearch -QLLLY EXTERNAL -H ldapi:/// -b cn=kerberos,ou=services,dc=da-test,dc=ru dn
```

**Предупреждение авторов:** в ходе этих операций запрашивается мастер-пароль базы данных Kerberos — его нужно обязательно сохранить. (В источнике фраза о мастер-пароле стоит между командами `stashsrvpw` и `create`; к какой из них она относится — ⚠ в источнике неясно.)

#### 8.6. Права доступа к поддереву Kerberos

Чтение и запись поддерева `cn=kerberos,ou=services,...` даются только `krbadmin`; кроме него и администратора каталога, доступа к этим данным не должно быть ни у кого. Файл `init-kerberos-acl.ldif`:

```ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcAccess
olcAccess: {0}to *
  by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth" manage
  by * break
olcAccess: {1}to attrs=userPassword,userPKCS12
  by self write
  by anonymous auth
olcAccess: {2}to attrs=shadowLastChange
  by self write
olcAccess: {3}to dn.subtree="cn=kerberos,ou=services,dc=da-test,dc=ru"
  by dn.exact="cn=krbadmin,ou=users,dc=da-test,dc=ru" manage
olcAccess: {4}to *
  by dn.base="cn=nssproxy,ou=users,dc=da-test,dc=ru" read
  by self read
```

```bash
sudo ldapmodify -QY EXTERNAL -H ldapi:/// -f init-kerberos-acl.ldif
```

Что нужно проверить после смены ACL:

1. `krbadmin` видит контейнер и имеет на него права чтения/записи:
   ```bash
   sudo ldapsearch -xZZLLLWD cn=krbadmin,ou=users,dc=da-test,dc=ru -b cn=kerberos,ou=services,dc=da-test,dc=ru dn
   ```
2. `nssproxy` не обнаруживает даже существования контейнера — запрос должен завершиться ошибкой `No such object (32)`:
   ```bash
   sudo ldapsearch -xZZLLLWD cn=nssproxy,ou=users,dc=da-test,dc=ru -b cn=kerberos,ou=services,dc=da-test,dc=ru dn
   ```
3. Обычные пользователи по-прежнему аутентифицируются через OpenLDAP и могут сами менять пароль — проверяется с другого хоста (например, `app1`):
   ```bash
   su - tester
   passwd
   ```
   Ожидается запрос текущего пароля LDAP, двойной ввод нового и сообщение `passwd: password updated successfully`.

#### 8.7. Журналы KDC и kadmind

На сервере каталогов в конец `/etc/rsyslog.conf` добавляется:

```
# Журнал krb5-kdc в /var/log/krb5kdc.log:
if $programname == 'krb5kdc' then /var/log/krb5kdc.log
& ~

# Журнал krb5-admin-server в /var/log/kadmind.log:
if $programname == 'kadmind' then /var/log/kadmind.log
& ~
```

```bash
sudo touch /var/log/{krb5kdc,kadmind}.log
sudo chmod 0640 /var/log/{krb5kdc,kadmind}.log
sudo chown syslog:adm /var/log/{krb5kdc,kadmind}.log
sudo nano /etc/logrotate.d/krb5kdc
sudo nano /etc/logrotate.d/kadmind
```

(исправлено по смыслу: в источнике первая команда редактора записана как `sudo namo`)

`/etc/logrotate.d/krb5kdc`:

```
/var/log/krb5kdc.log {
 daily
 missingok
 rotate 7
 compress
 delaycompress
 notifempty
}
```

`/etc/logrotate.d/kadmind`:

```
/var/log/kadmind.log {
 daily
 missingok
 rotate 7
 compress
 delaycompress
 notifempty
}
```

#### 8.8. Запуск служб

```bash
sudo systemctl restart rsyslog
sudo systemctl enable krb5-kdc
sudo systemctl enable krb5-admin-server
sudo systemctl start krb5-kdc
sudo systemctl start krb5-admin-server
ss -tan | egrep ':88|:464|:749'
```

Должны слушаться порты: `88` — krb5kdc; `464` и `749` — kadmind.

#### 8.9. Принципалы

Работа ведётся в `kadmin.local` из оболочки root:

```bash
sudo su -
kadmin.local
```

Команды внутри `kadmin.local`:

```
addprinc -randkey host/da1.da-test.ru@DA-TEST.RU
ktadd host/da1.da-test.ru@DA-TEST.RU
addprinc user1@DA-TEST.RU
addprinc user1/admin@DA-TEST.RU
get_principals
getprinc host/da1.da-test.ru@DA-TEST.RU
exit
```

| Команда | Что делает |
|---------|------------|
| `addprinc -randkey host/...` | создаёт принципал хоста текущего сервера со случайным ключом (в примере выводится предупреждение `no policy specified ... defaulting to no policy`, после чего принципал создаётся) |
| `ktadd host/...` | записывает ключи принципала в набор ключей `/etc/krb5.keytab` — по одной записи на каждый тип шифрования |
| `addprinc user1@...` | принципал пользователя; пароль запрашивается дважды |
| `addprinc user1/admin@...` | принципал с правами администратора области: по `kadm5.acl` принципалы с суффиксом `/admin` могут создавать и удалять записи пользователей и политики |
| `get_principals` | список принципалов области |
| `getprinc <принципал>` | подробные сведения: сроки действия, максимальное время жизни билета (в примере 1 день), число и типы ключей, политика |

⚠ в источнике неясно: в тексте обещано создать принципал для пользователя `tester`, фактически создаются `user1` и `user1/admin`.

Ожидаемый состав области после этих шагов: `K/M`, `krbtgt/DA-TEST.RU`, `kadmin/admin`, `kadmin/changepw`, `kadmin/history`, `kadmin/da1.da-test.ru`, `host/da1.da-test.ru`, `user1`, `user1/admin` (все — `@DA-TEST.RU`).

Проверка keytab-файла (выводит номера версий ключей и типы шифрования, доступные для `host/da1.da-test.ru`):

```bash
sudo klist -ek /etc/krb5.keytab
```

#### 8.10. Индексы для Kerberos

После запуска KDC в `/var/log/slapd.log` появляется сообщение `mdb_equality_candidates: (krbPrincipalName) not indexed`. Файл `init-kerberos-indexes.ldif`:

```ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcDbIndex
olcDbIndex: krbPrincipalName eq
-
add: olcDbIndex
olcDbIndex: ou eq
```

```bash
sudo ldapadd -QY EXTERNAL -H ldapi:/// -f init-kerberos-indexes.ldif
```

После загрузки конфигурации сообщение должно исчезнуть. На этом статья заканчивается.

### Чего в статье нет

- Настройки сервера 1С:Предприятия для Kerberos-аутентификации (принципал службы, keytab для пользователя службы, сопоставление пользователей информационной базы) — статья останавливается на готовом KDC.
- Настройки Kerberos на клиентских хостах (`app1`, `pc1`): показано только подключение клиентов к LDAP через nslcd/NSS/PAM.
- Создания `ou=services`, CRL-файла `rootca.crl`, команды выпуска корневого сертификата УЦ.
- Правил sudo в каталоге: пакет `sudo-ldap` ставится и его схема подключается, но записи sudoers в LDAP не создаются.
- Репликации/резервирования каталога и KDC, резервного копирования базы каталога.

### Справочная сводка по стенду статьи

**Порты.**

| Служба | Порт |
|--------|------|
| DNS (bind9) | 53 |
| LDAP (slapd) | 389 |
| Kerberos KDC (krb5kdc) | 88 (`kdc_ports = 88`, `kdc_tcp_ports = 88`) |
| kadmind | 464, 749 |

**Пароли и секреты, появляющиеся в ходе настройки.** Пароль root (задаётся перед установкой `sudo-ldap`); пароль администратора каталога и его SSHA-хэш; пароли `user1`, `nssproxy`, `tester`; пароль закрытого ключа УЦ; пароль `krbadmin`; мастер-пароль базы Kerberos; пароли принципалов `user1` и `user1/admin`. Авторы отдельно требуют сохранить в надёжном месте пароль ключа УЦ, пароль `krbadmin` и мастер-пароль базы Kerberos.

**Основные файлы.**

| Файл / каталог | Хост | Назначение |
|----------------|------|------------|
| `/etc/default/named`, `/etc/bind/named.conf.options`, `/etc/bind/named.conf.local`, `/etc/bind/zones/` | ns1 | DNS |
| `/etc/netplan/00-private-nameservers.yaml` | все | указание DNS-сервера и домена поиска |
| `~/ldap/*.ldif`, `~/ldap/convert-schema-to-ldif.sh` | da1 | рабочие LDIF-файлы и скрипт конвертации схем |
| `/etc/ldap/slapd.d`, `/var/lib/ldap`, `/etc/ldap/schema` | da1 | конфигурация, база и схемы slapd |
| `/etc/default/slapd` | da1 | `SLAPD_OPTIONS="-4"` |
| `/root/CA`, `/etc/ssl/openssl.cnf` | da1 (УЦ) | удостоверяющий центр |
| `/etc/ldap/ssl/`, `/etc/ssl/certs/rootca.crt` | da1 | сертификат и ключ slapd, корневой сертификат |
| `/etc/ldap/ldap.conf` | da1 и клиенты | параметры LDAP-клиента |
| `/etc/nslcd.conf`, `/etc/nsswitch.conf`, `/etc/pam.d/common-session`, `/etc/ssh/sshd_config` | клиенты (включая сервер 1С) | NSS/PAM/SSH |
| `/etc/krb5.conf`, `/etc/krb5kdc/kdc.conf`, `/etc/krb5kdc/kadm5.acl`, `/etc/krb5.d/stash.keyfile`, `/etc/krb5.keytab` | da1 | Kerberos |
| `/etc/rsyslog.conf`, `/etc/logrotate.d/{slapd,krb5kdc,kadmind}`, `/var/log/{slapd,krb5kdc,kadmind}.log` | da1 | журналы |

