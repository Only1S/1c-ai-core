# Сеть в Ubuntu Server: ip, netplan, DNS и имена хостов, диагностика, ufw, SSH (для стенда 1С + PostgreSQL)

> Область: настройка и диагностика сети Ubuntu Server (ВМ на Windows-хосте) под сервер «1С:Предприятие 8» и PostgreSQL: адреса, маршруты, netplan, имена и DNS, сетевые утилиты, порты стека, firewall (ufw/nftables/iptables), SSH-клиент и сервер, работа с Windows, Samba, прокси/MTU/IPv6 | Версии: Ubuntu 22.04 LTS (jammy), 24.04 LTS (noble), 26.04 LTS (resolute); платформа 1С 8.3.x / 8.5.x; PostgreSQL — любая поддерживаемая (порт 5432) | Актуальность: 2026-10-10

Условные обозначения: **[Офиц.]** — подтверждено официальной документацией (Canonical, netplan, OpenSSH, systemd, 1С, Microsoft, Docker); **[Практика]** — устойчивая практика сообщества (форумы, статьи); **⚠ не подтверждено** — утверждение записано по памяти/по вторичным источникам, первоисточник в этой сессии прочитать не удалось.

> Файл прошёл независимую проверку по первоисточникам 10.10.2026 (исходники netplan, subiquity, cloud-init и ufw; man-страницы Ubuntu; packages.ubuntu.com; release notes OpenSSH и Ubuntu; англоязычное «Руководство администратора. Клиент-серверный вариант» 1С для 8.3.22–8.3.27 и 8.5.1 и FAQ на kb.1ci.com; документация Docker, Oracle VirtualBox, Microsoft). Что именно осталось непроверенным — см. пометки «⚠» в тексте и раздел «Ограничения исследования» в конце.

В примерах используются условные значения: сервер `srv1c` (FQDN `srv1c.corp.local`) с адресом `192.168.1.50/24`, шлюз `192.168.1.1`, сеть клиентов `192.168.1.0/24`, интерфейс `enp0s3`, администратор `admin`. Подставляйте свои.

## Кратко

1. Постоянная сетевая конфигурация Ubuntu Server — только через **netplan**: YAML-файлы `/etc/netplan/*.yaml` (права `600`, владелец root), применение `sudo netplan try` (откат через 120 с, если не подтвердить) или `sudo netplan apply`. Команды `ip addr add`, `ip route add` действуют до перезагрузки.
2. Шлюз по умолчанию задаётся `routes: - to: default / via: <шлюз>`; ключи `gateway4`/`gateway6` устарели. Маршрут по умолчанию должен быть **один** (на одном интерфейсе).
3. Посмотреть состояние: `ip -br -c a` (адреса), `ip r` (маршруты), `ip neigh` (ARP), `sudo netplan status -a`, `networkctl status`, `resolvectl status` (DNS).
4. `ifconfig`, `route`, `netstat`, `arp` (пакет `net-tools`) устарели и по умолчанию не установлены; аналоги — `ip addr`, `ip route`, `ss`, `ip neigh`.
5. DNS обслуживает `systemd-resolved`: `/etc/resolv.conf` — симлинк на `/run/systemd/resolve/stub-resolv.conf` со `nameserver 127.0.0.53`. Руками файл не правят: DNS-серверы задают в netplan (`nameservers:`).
6. Имя хоста: `sudo hostnamectl set-hostname srv1c` (пишет `/etc/hostname`). После смены имени обязательно поправить `/etc/hosts`.
7. **Для 1С критично:** имя сервера должно разрешаться в его **реальный IP** и на самом сервере, и на всех клиентах. Строку `127.0.1.1 <имя>` в `/etc/hosts` сервера заменяют на `<реальный IP> <FQDN> <короткое имя>`. Проверка: `hostname -i` и `getent hosts $(hostname)` должны показать не `127.0.1.1`, а реальный адрес. Причина [Офиц.]: процессы кластера адресуются **именем рабочего сервера и номером порта**; запись в DNS/`hosts` клиента не нужна только если в свойстве рабочего сервера «Компьютер» указан IP-адрес (п. 4.5).
8. Порты 1С (TCP) [Офиц., руководство администратора 8.3.22–8.5.1]: **1540** — агент сервера (`ragent`), **1541** — менеджер кластера (`rmngr`), **1560–1591** — рабочие процессы (`rphost`) и дополнительные менеджеры кластера, **1545** — сервер администрирования (`ras`), **1550** — сервер отладки (`dbgs`). В 8.5.1 значения те же. PostgreSQL — **5432**, веб-публикация — **80/443**, SSH — **22**.
9. Проверка порта: `ss -tlnp` (кто слушает на сервере), `nc -zv srv1c 1541` (с Linux-клиента), `Test-NetConnection srv1c -Port 1541` (из PowerShell на Windows).
10. Firewall — `ufw` (по умолчанию **выключен**). Сначала `sudo ufw allow OpenSSH`, потом `sudo ufw enable`. Правила: `sudo ufw allow from 192.168.1.0/24 to any port 1540:1541 proto tcp`. Срабатывает **первое** подходящее правило.
11. `ufw` и `iptables-persistent`/`netfilter-persistent` взаимоисключающие (в 24.04+ установка одного удаляет другое). Docker публикует порты **в обход** ufw.
12. SSH-сервер: пакет `openssh-server`, служба `ssh.service` (не `sshd`; в 26.04 добавлен алиас `sshd.service`). Свои настройки — в `/etc/ssh/sshd_config.d/*.conf`, проверка `sudo sshd -t`, применение `sudo systemctl restart ssh`.
13. В Ubuntu 22.10+ (значит в 24.04 и 26.04) sshd запускается через **сокет-активацию** (`ssh.socket`). После смены `Port`/`ListenAddress` в 24.04+ нужно `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket`. В 22.04 — классический `ssh.service`.
14. Ключи: `ssh-keygen -t ed25519`, установка на сервер `ssh-copy-id admin@srv1c`; затем `PasswordAuthentication no`. Не закрывайте текущую сессию, пока не проверили вход по ключу во второй.
15. Туннель к PostgreSQL без открытия 5432 наружу: `ssh -N -L 15432:127.0.0.1:5432 admin@srv1c`, затем pgAdmin/psql на `localhost:15432`.
16. В Windows 10 (1809+)/11 клиент OpenSSH встроен: `ssh`, `scp`, `sftp`, `ssh-keygen` работают прямо в PowerShell. `ssh-copy-id` в Windows нет.
17. Перехват трафика: `sudo tcpdump -ni any 'tcp portrange 1560-1591' -w /tmp/1c.pcap`; файл открывается в Wireshark.
18. cloud-init может управлять сетью (`/etc/netplan/50-cloud-init.yaml`) и `/etc/hosts`. Отключение управления сетью: файл `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` с содержимым `network: {config: disabled}`. Имя netplan-файла после установки с ISO зависит от выпуска: 22.04 — `00-installer-config.yaml`; 24.04 (до 24.04.5 включительно) — `50-cloud-init.yaml`; 26.04 — снова `00-installer-config.yaml`. В 24.04+ установщик сам отключает cloud-init после первой загрузки (`/etc/cloud/cloud-init.disabled`) — подробности в п. 3.6.
19. Для ВМ с сервером 1С удобнее всего сетевой режим **Bridged** (мост): ВМ получает адрес в той же сети, что и клиенты. При NAT придётся пробрасывать все порты 1С (включая диапазон 1560–1591) и подменять имя сервера в `hosts` клиентов.
20. IPv6 отключать обычно не нужно; если нужно — sysctl `net.ipv6.conf.all.disable_ipv6=1` или параметр ядра `ipv6.disable=1`.

## 1. Версии и компоненты сетевого стека

| Компонент | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS | Ubuntu 26.04 LTS |
|---|---|---|---|
| Статус на 10.2026 | стандартная поддержка до 05.2027 | стандартная поддержка до 31.05.2029 (последний точечный выпуск — 24.04.5) | актуальный LTS, выпущен 23.04.2026, поддержка до 04–05.2031 (вышел 26.04.1) |
| Ядро (GA) | 5.15 | 6.8 | 7.0 |
| systemd | 249 | 255 | 259 |
| netplan | 0.104 на релизе; в `jammy-security` 0.106.1, в `jammy-updates` 0.107.1 | 1.0 на релизе; в `noble-updates` 1.1.2 | 1.2 |
| OpenSSH | 8.9p1 | 9.6p1 | 10.2p1 |
| Запуск sshd | постоянная служба `ssh.service` | сокет-активация `ssh.socket` + генератор `sshd-socket-generator` | сокет-активация; алиас `sshd.service` |
| ufw | 0.36.1 | 0.36.2-6 | 0.36.2-9build1 |
| iptables / nftables | 1.8.7 / 1.0.2 | 1.8.10 / 1.0.9 | 1.8.11 / 1.1.6 |
| fail2ban | 0.11.2-6 | 1.0.2-3 | 1.1.0-9 |
| Samba | 4.15.13 (на релизе 4.15.5) | 4.19.5 | 4.23.6 |
| Установщик пишет сеть в | `/etc/netplan/00-installer-config.yaml` | `/etc/netplan/50-cloud-init.yaml` (через cloud-init) | `/etc/netplan/00-installer-config.yaml` |
| Синхронизация времени | systemd-timesyncd | systemd-timesyncd | chrony (в новых установках) |

[Офиц.] Источники: release notes 24.04 и 26.04, ubuntu.com/about/release-cycle (сроки поддержки: 22.04 — май 2027, 24.04 — май 2029, 26.04 — май 2031; в release notes 26.04 указано «until April 2031»), таблица версий на documentation.ubuntu.com/security, packages.ubuntu.com (версии netplan.io, openssh-server, ufw, iptables, nftables, fail2ban, samba проверены 10.10.2026), исходный код установщика subiquity (теги 22.04.1, 24.04.1, 24.04.5, 25.10, 26.04.1).

Важные отличия 26.04 для этой темы [Офиц.]:

- OpenSSH 10.2p1: удалена поддержка DSA (в OpenSSH 10.0); по умолчанию включён `PerSourcePenalties` (появился в OpenSSH 9.8 и там же включён по умолчанию; временная блокировка адресов, с которых идут неудачные попытки входа); по умолчанию гибридный постквантовый обмен ключами `mlkem768x25519-sha256` (доступен с 9.9, используется по умолчанию с 10.0); появилось условие `Match invalid-user`; `sshd.service` — алиас `ssh.service`. Сервер разделён на несколько бинарников: `sshd` (слушатель), `sshd-session` (с 9.8) и `sshd-auth` (с 10.0) — поэтому часть сообщений в журнале идёт от имени `sshd-session`, а не `sshd` (важно для fail2ban и своих фильтров журнала, см. 8.9).
- netplan 1.2: собственная логика `systemd-networkd-wait-online` (ожидает link-local-адреса и один маршрутизируемый интерфейс).
- systemd 259: убрана поддержка cgroup v1 (иерархии `legacy` и `hybrid`); 26.04 — последний выпуск с совместимостью скриптов System V (init-скрипты `/etc/init.d/*` надо переводить на unit-файлы).
- Samba 4.23: NetBIOS в новом `smb.conf` по умолчанию выключен.

Бэкенд iptables [Офиц.]: начиная с Ubuntu 20.10 команды `iptables`/`ip6tables` по умолчанию работают через nftables (`iptables-nft`). Проверка: `iptables -V` выводит `(nf_tables)` или `(legacy)`; `update-alternatives --display iptables`.

## 2. Утилита ip (пакет iproute2)

`ip` — основной инструмент просмотра и **временного** изменения сетевых настроек (всё, что сделано через `ip`, пропадает после перезагрузки или `netplan apply`). Синтаксис: `ip [ОПЦИИ] ОБЪЕКТ КОМАНДА`. Объекты сокращаются: `ip a` = `ip addr` = `ip address`, `ip l` = `ip link`, `ip r` = `ip route`, `ip n` = `ip neigh`.

### 2.1. Общие опции

| Опция | Назначение |
|---|---|
| `-br`, `-brief` | краткий табличный вывод (для `addr`, `link`, `neigh`) |
| `-c`, `-color` | цветной вывод |
| `-4` / `-6` | только IPv4 / только IPv6 |
| `-s`, `-stats` | статистика (пакеты, ошибки, дропы); `-s -s` — подробнее |
| `-d`, `-details` | детали (тип устройства, параметры bond/vlan/bridge) |
| `-j`, `-json` и `-p`, `-pretty` | вывод в JSON (удобно с `jq`) |
| `-o`, `-oneline` | каждая запись в одну строку (удобно для `grep`/`awk`) |
| `-h`, `-human` | человекочитаемые единицы в статистике |
| `-ts`, `-tshort` | метки времени (для `ip monitor`) |

### 2.2. ip addr — адреса

```bash
ip -br -c addr                 # кратко: интерфейс, состояние, адреса
ip addr show dev enp0s3        # подробно по одному интерфейсу
ip -4 addr                     # только IPv4
ip -j -p addr | less           # JSON
sudo ip addr add 192.168.1.50/24 dev enp0s3    # добавить адрес (временно)
sudo ip addr del 192.168.1.50/24 dev enp0s3    # удалить адрес
sudo ip addr flush dev enp0s3                  # снять все адреса с интерфейса
```

В выводе `ip addr`: `state UP/DOWN` — состояние; `inet 192.168.1.50/24` — IPv4 с префиксом; `scope global` — обычный адрес, `scope link` — link-local, `scope host` — loopback; `dynamic` — получен по DHCP (`valid_lft` — оставшееся время аренды).

### 2.3. ip link — интерфейсы (канальный уровень)

```bash
ip -br link                          # список интерфейсов, состояние, MAC
ip -s link show dev enp0s3           # счётчики RX/TX, errors, dropped
ip -d link show dev bond0            # детали виртуального устройства
sudo ip link set dev enp0s3 up       # включить
sudo ip link set dev enp0s3 down     # выключить (ОСТОРОЖНО: оборвёт SSH)
sudo ip link set dev enp0s3 mtu 1400 # сменить MTU (временно)
sudo ip link delete dev bond0        # удалить виртуальное устройство
```

Флаги в угловых скобках: `UP` — административно включён, `LOWER_UP` — есть физический линк (несущая), `NO-CARRIER` — кабель/виртуальный адаптер не подключён.

### 2.4. ip route — маршруты

```bash
ip route                              # таблица маршрутизации (main)
ip route get 8.8.8.8                  # через какой интерфейс/шлюз и с какого адреса пойдёт пакет
ip route get 192.168.1.20 from 192.168.1.50
sudo ip route add default via 192.168.1.1                      # шлюз по умолчанию (временно)
sudo ip route add 10.10.0.0/16 via 192.168.1.254 dev enp0s3    # статический маршрут
sudo ip route replace default via 192.168.1.1 metric 100
sudo ip route del 10.10.0.0/16
ip -6 route
```

Строка `default via 192.168.1.1 dev enp0s3 proto static metric 100`: `proto static` — задан конфигурацией, `proto dhcp` — получен по DHCP, `proto kernel` — создан ядром для подключённой сети; при нескольких default выигрывает меньший `metric`.

### 2.5. ip neigh — таблица соседей (ARP/NDP)

```bash
ip neigh                         # аналог arp -n
ip neigh show dev enp0s3
sudo ip neigh flush dev enp0s3   # очистить кэш
```

Состояния: `REACHABLE` — подтверждён, `STALE` — давно не проверялся (нормально), `DELAY`/`PROBE` — проверяется, `FAILED`/`INCOMPLETE` — узел не отвечает на ARP (узел выключен, другой VLAN, неверная маска).

### 2.6. ip monitor — наблюдение за изменениями в реальном времени

```bash
ip monitor                 # все события (адреса, линки, маршруты, соседи)
ip -ts monitor link        # только изменения состояния интерфейсов, с меткой времени
ip monitor address route   # адреса и маршруты
```

Полезно при поиске «мигающего» линка или неожиданной смены адреса по DHCP. Выход — `Ctrl+C`.

### 2.7. Имена интерфейсов

Ubuntu использует «предсказуемые» имена (systemd/udev): префикс `en` — Ethernet, `wl` — Wi-Fi, `ww` — WWAN; далее способ привязки:

| Вид имени | Смысл | Где встречается |
|---|---|---|
| `eno1` | встроенный адаптер (onboard, индекс из прошивки) | физические серверы |
| `ens3`, `ens33` | слот PCI hotplug | KVM/QEMU, VMware (`ens33`, `ens160`) |
| `enp0s3`, `enp0s8` | шина PCI `p<bus>s<slot>` | VirtualBox (`enp0s3` — первый адаптер, `enp0s8` — второй) |
| `enx001122334455` | по MAC-адресу | USB-адаптеры |
| `eth0` | классическое имя | Hyper-V (драйвер `hv_netvsc`), контейнеры, облака |
| `lo` | loopback (`127.0.0.1/8`, `::1`) | всегда |

При смене типа/слота виртуального адаптера имя интерфейса меняется, и netplan-конфигурация, привязанная к старому имени, перестаёт применяться. Защита — привязка по MAC (`match: macaddress:` + `set-name:` в netplan, см. ниже).

### 2.8. Устаревшие net-tools и их современные аналоги

Пакет `net-tools` (`ifconfig`, `route`, `netstat`, `arp`) в Ubuntu Server по умолчанию не ставится; при необходимости — `sudo apt install net-tools`. В документации 1С и старых статьях встречаются именно эти команды (например, статья ИТС по установке платформы на Linux предлагает смотреть адреса через `ifconfig`).

| Устаревшая команда (net-tools) | Современный аналог |
|---|---|
| `ifconfig`, `ifconfig -a` | `ip addr`, `ip -br a` |
| `ifconfig eth0 up` / `down` | `ip link set dev eth0 up` / `down` |
| `ifconfig eth0 192.168.1.50 netmask 255.255.255.0` | `ip addr add 192.168.1.50/24 dev eth0` |
| `route -n`, `netstat -rn` | `ip route` |
| `route add default gw 192.168.1.1` | `ip route add default via 192.168.1.1` |
| `arp -n` | `ip neigh` |
| `netstat -tulpn` | `ss -tulpn` |
| `netstat -s` | `ss -s`, `nstat` |
| `netstat -i` | `ip -s link` |
| `mii-tool` | `ethtool` |
| `brctl` (bridge-utils) | `bridge`, `ip link ... type bridge` |
| `vconfig` | `ip link add link eth0 name eth0.100 type vlan id 100` |
| `iwconfig` | `iw` |

[Офиц.] Таблица соответствия — Debian Reference, гл. 5.

## 3. Netplan — постоянная конфигурация сети

Netplan — слой декларативной конфигурации: читает YAML и генерирует настройки для бэкенда («рендерера»). Сам сетью не управляет.

- `renderer: networkd` — systemd-networkd, **значение по умолчанию**, стандарт для Ubuntu Server.
- `renderer: NetworkManager` — используется в Ubuntu Desktop (в 24.04+ NetworkManager сам хранит профили через netplan в `/etc/netplan/90-NM-*.yaml`).

### 3.1. Файлы, порядок чтения, права

[Офиц.] Netplan читает `*.yaml` из трёх каталогов: `/lib/netplan/`, `/etc/netplan/`, `/run/netplan/`.

- Файлы с **разными** именами обрабатываются в лексикографическом порядке имён независимо от каталога; более поздний файл дополняет/переопределяет более ранний (скаляры перезаписываются, списки дополняются, словари сливаются).
- При **одинаковом** имени файла читается только один: приоритет `/run/netplan` > `/etc/netplan` > `/lib/netplan`.
- Свои настройки кладут в `/etc/netplan/`. Типичные имена: `50-cloud-init.yaml` (создан cloud-init; так выглядит установка 24.04 с ISO и любые облачные образы), `00-installer-config.yaml` (установщик 20.04–22.04 и снова 25.10/26.04), `70-netplan-set.yaml` (создаётся командой `netplan set` без `--origin-hint`), `90-NM-*.yaml` (профили NetworkManager), `01-netcfg.yaml`, `99-*.yaml` (свои переопределения; документация Ubuntu Server использует `99_config.yaml`).
- [Офиц.] Файлы должны принадлежать root и быть недоступны остальным: `sudo chmod 600 /etc/netplan/*.yaml`. При более широких правах netplan выдаёт предупреждение вида `Permissions for /etc/netplan/….yaml are too open. Netplan configuration should NOT be accessible by others.` (в файлах могут быть пароли Wi-Fi/VPN).
- YAML чувствителен к отступам: **только пробелы**, обычно по 2 на уровень; табуляция — ошибка разбора.

Сгенерированные файлы бэкенда лежат в `/run/systemd/network/10-netplan-<имя>.network` (для networkd) — смотреть можно, править нельзя (пересоздаются).

### 3.2. Структура YAML

```yaml
network:
  version: 2            # всегда 2
  renderer: networkd    # networkd (по умолчанию) | NetworkManager
  ethernets:            # физические интерфейсы
    enp0s3:
      dhcp4: true
  # bonds: / bridges: / vlans: / wifis: / tunnels: / vrfs: / dummy-devices: — прочие типы
```

Основные свойства интерфейса [Офиц., netplan-yaml]:

| Ключ | Назначение |
|---|---|
| `dhcp4`, `dhcp6` | `true/false`, по умолчанию `false` |
| `addresses` | список адресов в CIDR: `- 192.168.1.50/24` |
| `routes` | список маршрутов; у каждого обязателен `to`, далее `via`, `metric`, `table`, `on-link` |
| `nameservers` | `addresses: [...]` — DNS-серверы, `search: [...]` — домены поиска |
| `gateway4`, `gateway6` | **устарели**; вместо них `routes: - to: default` |
| `mtu` | MTU, по умолчанию 1500 |
| `optional: true` | не ждать интерфейс при загрузке (иначе `systemd-networkd-wait-online` может задерживать старт до 2 минут) |
| `match:` (`name`, `macaddress`, `driver`) + `set-name:` | привязка по MAC/шаблону и переименование |
| `macaddress` | задать MAC |
| `link-local: []` | отключить link-local-адреса (по умолчанию включён IPv6 link-local) |
| `accept-ra` | принимать ли IPv6 Router Advertisement |
| `dhcp4-overrides:` | `use-dns`, `use-routes`, `use-ntp`, `use-hostname`, `use-mtu`, `send-hostname` (все по умолчанию `true`), `route-metric`, `hostname` |
| `critical: true` | не снимать адрес при перезапуске networkd (только networkd) |
| `wakeonlan`, `ignore-carrier` | Wake-on-LAN; не сбрасывать конфигурацию при пропаже несущей |

### 3.3. Примеры

**DHCP (как после установки):**

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
```

**Статический адрес — типовой вариант для сервера 1С/PostgreSQL** (`/etc/netplan/01-static.yaml`):

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: false
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        search: [corp.local]
        addresses: [192.168.1.1, 1.1.1.1]
```

Серверу 1С нужен **постоянный** адрес: либо статика, как выше, либо резервирование (reservation) на DHCP-сервере по MAC. Меняющийся адрес ломает соответствие «имя → IP» у клиентов.

**Привязка по MAC с переименованием** (защита от смены имени интерфейса в ВМ):

```yaml
network:
  version: 2
  ethernets:
    lan0:
      match:
        macaddress: "08:00:27:aa:bb:cc"
      set-name: lan0
      addresses: [192.168.1.50/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1]
```

**Два интерфейса** (например, VirtualBox: NAT для выхода в интернет + Host-only для связи с Windows-хостом). Маршрут по умолчанию — только на одном:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:                 # NAT: интернет, адрес по DHCP, даёт default route и DNS
      dhcp4: true
    enp0s8:                 # Host-only: статический адрес для SSH и клиентов 1С
      dhcp4: false
      addresses: [192.168.56.10/24]
      # routes и nameservers здесь НЕ задаём
```

Если оба интерфейса на DHCP и оба выдают шлюз — отключите маршруты на втором: `dhcp4-overrides: {use-routes: false, use-dns: false}` либо задайте `route-metric`.

**Несколько адресов и дополнительный статический маршрут:**

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      addresses:
        - 192.168.1.50/24
        - 192.168.1.51/24
      routes:
        - to: default
          via: 192.168.1.1
        - to: 10.10.0.0/16
          via: 192.168.1.254
          metric: 200
```

**Bond (агрегация/резервирование двух адаптеров):**

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1: {dhcp4: false}
    eno2: {dhcp4: false}
  bonds:
    bond0:
      interfaces: [eno1, eno2]
      parameters:
        mode: active-backup        # balance-rr (по умолч.) | active-backup | balance-xor | broadcast | 802.3ad | balance-tlb | balance-alb
        primary: eno1
        mii-monitor-interval: 100  # мс; по умолчанию 0 = мониторинг выключен
      addresses: [192.168.1.50/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1]
```

Для `802.3ad` (LACP) нужна настройка на коммутаторе; доп. параметры `lacp-rate: slow|fast`, `transmit-hash-policy: layer2|layer3+4|layer2+3|encap2+3|encap3+4`.

**Bridge (мост — если на этом же сервере запускаются KVM/LXD-гости):**

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp3s0:
      dhcp4: false
  bridges:
    br0:
      interfaces: [enp3s0]
      addresses: [192.168.1.50/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1]
      parameters:
        stp: false          # по умолчанию true
        forward-delay: 0
```

**VLAN:**

```yaml
network:
  version: 2
  ethernets:
    enp3s0: {dhcp4: false}
  vlans:
    vlan100:
      id: 100               # 0–4094
      link: enp3s0
      addresses: [10.0.100.5/24]
```

### 3.4. Команды netplan

| Команда | Что делает |
|---|---|
| `sudo netplan generate` | только проверяет YAML и генерирует файлы бэкенда в `/run`; сеть не трогает. Удобно как проверка синтаксиса |
| `sudo netplan try [--timeout N]` | применяет конфигурацию и ждёт подтверждения (Enter); без подтверждения **откатывает** через 120 с (по умолчанию). Главная команда при работе по SSH |
| `sudo netplan apply` | применяет конфигурацию сразу, без отката |
| `sudo netplan --debug apply` | то же с отладочным выводом (опция `--debug` ставится **перед** подкомандой) |
| `sudo netplan get [ключ]` | показывает итоговую (слитую из всех файлов) конфигурацию или её часть |
| `sudo netplan set ключ=значение` | меняет параметр из командной строки, пишет в YAML; `ключ=null` удаляет ключ |
| `netplan status [-a] [интерфейс]` | текущее состояние: адреса, маршруты, DNS, MAC. [Офиц.] Команда появилась в netplan 0.106 (release notes: «New 'netplan status' CLI»), т. е. в 22.04 доступна после установки обновлений (0.106.1/0.107.1), в 24.04+ — сразу |
| `netplan status --diff` / `--diff-only` | различия между YAML и фактическим состоянием системы: адреса, маршруты, MAC, DNS, домены поиска, отсутствующие интерфейсы; «+» — есть только в системе, «−» — только в YAML (netplan 1.0+, т. е. 24.04+; в 22.04 опции нет) |
| `netplan info` | версия и поддерживаемые возможности |
| `netplan ip leases <интерфейс>` | сведения о DHCP-аренде |
| `netplan rebind` | перепривязка SR-IOV VF (обычному серверу не нужно) |

Примеры:

```bash
sudo netplan generate && echo OK              # проверить синтаксис
sudo netplan try --timeout 60                 # применить с откатом через 60 с
sudo netplan apply
sudo netplan get                              # вся конфигурация
sudo netplan get ethernets.enp0s3.addresses
sudo netplan set ethernets.enp0s3.dhcp4=false
sudo netplan set --origin-hint 60-static "ethernets.enp0s3.addresses=[192.168.1.50/24]"
sudo netplan set "ethernets.enp0s3={dhcp4: false, addresses: [192.168.1.50/24]}"   # сразу поддерево
sudo netplan set ethernets.enp0s3.dhcp4=null   # удалить ключ
sudo netplan status -a
sudo netplan status --diff
sudo netplan status -f json enp0s3
```

Пояснения и ограничения [Офиц.]:

- `netplan set --origin-hint ИМЯ` пишет в `/etc/netplan/ИМЯ.yaml` (суффикс `.yaml` добавляется сам; пустое значение — ошибка `Invalid/empty origin-hint`). Без `--origin-hint` netplan обновляет те YAML-файлы, из которых была прочитана конфигурация (интерфейс, уже описанный в каком-то файле, правится **в этом же файле**), а данные, не привязанные ни к одному файлу (новые интерфейсы и т. п.), пишет в `/etc/netplan/70-netplan-set.yaml` [Офиц., исходный код netplan: `FALLBACK_FILENAME = '70-netplan-set.yaml'`, описание функции `netplan_state_update_yaml_hierarchy`]. Следствие: `netplan set` может изменить и файл `50-cloud-init.yaml` — после команды посмотрите `sudo grep -r . /etc/netplan/`. Присваивание `null` удаляет ключ [Офиц., справка по аргументу `key_value` в исходном коде]. После `set` изменения нужно применить (`netplan try`/`apply`).
- `netplan try` применяет те же процедуры, что `apply`; при таймауте/отмене нужно убедиться, что конфигурация действительно откатилась. Подтвердить/отклонить можно не только клавишей, но и сигналами `SIGUSR1`/`SIGINT` процессу `netplan try`. [Офиц., исходный код `try_command.py`] Если в конфигурации есть bond или bridge с **нестандартными параметрами** (блок `parameters:`), `try` ничего не применяет и завершается с сообщением `<интерфейс>: reverting custom parameters for bridges and bonds is not supported` и подсказкой `Please carefully review the configuration and use 'netplan apply' directly.` — тогда только `apply` с консоли ВМ. Простые («тривиальные») bond/bridge без особых параметров `try` обрабатывает.
- `netplan apply` **не удаляет** виртуальные устройства (bond, bridge), убранные из YAML: удалите вручную (`sudo ip link delete dev bond0`) и повторите `apply`, либо перезагрузитесь.
- `netplan status` получает данные от `systemd-networkd` и попытается его запустить, если он не замаскирован.
- Хуки (скрипты при поднятии интерфейса) в netplan не поддерживаются; для networkd используйте `networkd-dispatcher`.
- В Ubuntu 18.04 синтаксис `to: default` не работал (там `gateway4`) — встречается в старых инструкциях.

Смежные команды бэкенда networkd:

```bash
networkctl list                    # интерфейсы и их состояние (routable / degraded / off)
networkctl status enp0s3           # адрес, шлюз, DNS, файл .network
sudo journalctl -u systemd-networkd -b   # журнал за текущую загрузку
sudo systemctl restart systemd-networkd
```

### 3.5. Безопасный порядок смены адреса по SSH

1. Сделать копию действующего файла (имя зависит от выпуска — `ls /etc/netplan/`): `sudo cp -a /etc/netplan/50-cloud-init.yaml ~/netplan.bak` (в 22.04 и 26.04 это обычно `00-installer-config.yaml`). Копию кладите **вне** `/etc/netplan/` или с расширением не `.yaml`, иначе netplan прочитает и её.
2. Отредактировать YAML (`sudoedit /etc/netplan/….yaml`), проверить права `600`.
3. `sudo netplan generate` — синтаксис.
4. `sudo netplan try`. Если меняются параметры, не затрагивающие ваш канал (DNS, второй интерфейс, маршруты), — проверьте `ip -br a`, `ip r`, `resolvectl status` из второго окна и нажмите Enter для подтверждения.
5. Если меняется **адрес интерфейса, через который вы подключены**, текущая SSH-сессия зависнет, и нажать Enter в ней не получится. Варианты: работать с **консоли ВМ** (окно гипервизора); либо запускать `netplan try` внутри `tmux`/`screen`, подключиться по новому адресу, вернуться в сессию (`tmux attach`) и подтвердить.
6. Если подтверждения не было — через 120 с конфигурация откатится, и сервер снова доступен по старому адресу.

### 3.6. cloud-init и сеть

cloud-init присутствует в образах Ubuntu Server и может управлять сетью: он генерирует `/etc/netplan/50-cloud-init.yaml`. В заголовке этого файла прямо сказано, что изменения могут не сохраниться и как отключить управление сетью.

Источники сетевой конфигурации cloud-init в порядке возрастания приоритета [Офиц.]: источник данных (datasource, напр. метаданные облака) → системная конфигурация (ключ `network:` в `/etc/cloud/cloud.cfg` и `/etc/cloud/cloud.cfg.d/*`) → командная строка ядра (`ip=` или `network-config=`).

**Отключить управление сетью со стороны cloud-init** [Офиц.]:

```bash
echo 'network: {config: disabled}' | sudo tee /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
```

Альтернатива — параметр ядра `network-config=disabled`. После этого cloud-init больше не перезаписывает netplan; дальше либо правьте `50-cloud-init.yaml`, либо (чище) переименуйте его в свой файл, например `01-static.yaml`.

Особенности установки с ISO (установщик subiquity) [Офиц., исходный код subiquity: `subiquity/models/network.py` и `subiquity/models/subiquity.py` в тегах 22.04.1, 24.04.1, 24.04.5, 25.04, 25.10, 26.04.1]:

| Выпуск (версия установщика) | Куда установщик пишет сеть | Что с cloud-init |
|---|---|---|
| 20.04–22.04 | `/etc/netplan/00-installer-config.yaml` (Wi-Fi с паролями — отдельно в `00-installer-config-wifi.yaml`) | сеть cloud-init отключена файлом `/etc/cloud/cloud.cfg.d/subiquity-disable-cloudinit-networking.cfg` (`network: {config: disabled}`); сам cloud-init остаётся включённым |
| 24.04–25.04 (включая 24.04.5) | `/etc/cloud/cloud.cfg.d/90-installer-network.cfg`, из которого cloud-init при первой загрузке генерирует `/etc/netplan/50-cloud-init.yaml` (ветка `use_cloudinit_net`; иначе — как в 22.04) | после первой загрузки cloud-init отключается целиком файлом `/etc/cloud/cloud-init.disabled` |
| 25.10, 26.04, 26.04.1 | снова `/etc/netplan/00-installer-config.yaml` | сеть cloud-init отключена файлом `/etc/cloud/cloud.cfg.d/00-subiquity-disable-cloudinit-networking.cfg`; после первой загрузки cloud-init отключается целиком (`/etc/cloud/cloud-init.disabled`) |

- В 24.04+ установщик добавляет в конфигурацию первой загрузки отложенную запись файла `/etc/cloud/cloud-init.disabled` с текстом `Disabled by Ubuntu live installer after first boot. To re-enable cloud-init on this image run: sudo cloud-init clean --machine-id`. Практическое следствие: на сервере 24.04/26.04, **установленном с ISO**, cloud-init после первой загрузки больше не запускается и не перезаписывает ни netplan, ни имя хоста, ни `/etc/hosts`; файл `50-cloud-init.yaml` в 24.04 можно править напрямую. В 22.04 cloud-init продолжает работать при каждой загрузке (но сеть не трогает).
- Таблица отражает **версию установщика**, а не только выпуск Ubuntu: если при установке было принято предложение обновить установщик («Update to the new installer»), работает более новый subiquity, и набор файлов может соответствовать следующей строке таблицы (в коде установщика есть явная проверка «выпуск не 20.04 и не 22.04» — именно потому, что новый установщик умеет ставить старые выпуски). ⚠ не подтверждено: из какого канала берётся обновление установщика и до какой версии он обновляется на конкретном ISO.
- Облачные образы, шаблоны ВМ провайдеров, образы для Multipass/LXD ведут себя иначе: там cloud-init активен, сеть лежит в `50-cloud-init.yaml` и может перегенерироваться.
- Всегда проверяйте фактическое состояние, а не выпуск: `ls -l /etc/netplan/ /etc/cloud/cloud.cfg.d/ /etc/cloud/cloud-init.disabled 2>/dev/null; cloud-init status`.
- [Офиц., docs.cloud-init.io] cloud-init применяет сетевую конфигурацию при «первой загрузке нового экземпляра» (событие `BOOT_NEW_INSTANCE`; расширить можно ключом `updates: network: when: ['boot']`). При **клонировании ВМ** или смене идентификатора экземпляра активный cloud-init может сработать заново и затереть ручные правки — ещё одна причина явно отключить его управление сетью после настройки.

Если cloud-init вообще не нужен (обычная ВМ, не облако) [Офиц., docs.cloud-init.io «How to disable cloud-init»]: `sudo touch /etc/cloud/cloud-init.disabled` отключает его целиком (проверяется при загрузке); альтернатива — параметр ядра `cloud-init=disabled`. Вернуть: удалить файл (на системах, установленных с ISO 24.04+, — `sudo cloud-init clean --machine-id`, **осторожно**: это сбрасывает состояние cloud-init и `machine-id`, при следующей загрузке он отработает как на новом экземпляре).

## 4. Имена хостов и DNS

### 4.1. Имя хоста: hostnamectl, /etc/hostname, hostname

```bash
hostnamectl                                 # текущее имя (static/transient/pretty), ОС, ядро, тип виртуализации
sudo hostnamectl set-hostname srv1c         # задать статическое имя; записывается в /etc/hostname
sudo hostnamectl hostname srv1c             # то же в современном синтаксисе (systemd 249+, т. е. 22.04 и новее)
hostnamectl hostname                        # только показать имя (systemd 249+)
cat /etc/hostname
hostname          # короткое имя
hostname -f       # FQDN (как его разрешает система: /etc/hosts или DNS)
hostname -i       # адрес(а), в которые разрешается имя хоста  <-- ключевая проверка для 1С
hostname -I       # все адреса всех интерфейсов (без разрешения имён)
```

Правила:

- В `/etc/hostname` рекомендуется держать одно короткое имя без домена (латиница, цифры, дефис; без подчёркиваний), лучше в нижнем регистре.
- FQDN формируется не в `/etc/hostname`, а разрешением имени: первой в строке `/etc/hosts` идёт FQDN, затем короткое имя.
- `hostnamectl set-hostname` **не правит** `/etc/hosts` — после смены имени исправьте его вручную, иначе `sudo` будет ругаться `sudo: unable to resolve host <имя>`.
- [Офиц., hostnamectl(1) для systemd 249] В man-странице начиная с systemd 249 документирована команда `hostnamectl hostname [ИМЯ]`; `set-hostname` оставлена как совместимый синоним и работает во всех трёх LTS.
- cloud-init может возвращать прежнее имя при загрузке (модуль Update Hostname выполняется при **каждой** загрузке; если `/etc/hostname` изменён вручную, cloud-init перестаёт его трогать). Чтобы имя гарантированно сохранялось: в `/etc/cloud/cloud.cfg` (или в файле `/etc/cloud/cloud.cfg.d/*.cfg`) установить `preserve_hostname: true` [Офиц., docs.cloud-init.io, модули Set Hostname / Update Hostname: при `true` имя не меняется; по умолчанию `false`]. На системах 24.04+/26.04, установленных с ISO, cloud-init после первой загрузки отключён (п. 3.6), и эта проблема не возникает.

### 4.2. /etc/hosts и строка 127.0.1.1

Формат строки: `IP-адрес  каноническое_имя  [псевдонимы…]`. Типичный файл сразу после установки Ubuntu/Debian:

```
127.0.0.1 localhost
127.0.1.1 srv1c

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
```

[Офиц., Debian Reference 5.1.1] Строку `127.0.1.1 <имя_хоста>` добавляет установщик Debian/Ubuntu для систем **без постоянного IP-адреса**, чтобы имя хоста всегда во что-то разрешалось (обход проблем некоторых программ). Там же сказано: для системы **с постоянным IP-адресом** вместо `127.0.1.1` следует указать этот постоянный адрес, а первым именем — FQDN.

Правильный `/etc/hosts` для сервера 1С со статическим адресом:

```
127.0.0.1       localhost
192.168.1.50    srv1c.corp.local srv1c

# строки IPv6 можно оставить как есть
::1     ip6-localhost ip6-loopback
```

Если домена нет — просто `192.168.1.50    srv1c`.

Проверка после правки:

```bash
hostname -f                  # srv1c.corp.local (или srv1c)
hostname -i                  # 192.168.1.50  (НЕ 127.0.1.1)
getent hosts srv1c           # 192.168.1.50   srv1c.corp.local srv1c
getent hosts "$(hostname)"
ping -c1 srv1c
```

cloud-init и `/etc/hosts`: если в начале файла есть комментарий о том, что система настроена с `manage_etc_hosts`, значит cloud-init пересоздаёт файл из шаблона при каждой загрузке и ручные правки пропадут. [Офиц., docs.cloud-init.io, модуль Update Etc Hosts] Значения параметра: `false` — не трогать (по умолчанию); `localhost` — файл целиком не переписывается, но при каждой загрузке гарантируется строка «FQDN и имя хоста → loopback-адрес дистрибутива» (в Debian/Ubuntu это `127.0.1.1`) — **для сервера 1С это значение так же вредно, как и `true`**; `true` — генерировать файл целиком из шаблона при каждой загрузке (`template` — устаревший с 22.3 синоним `true`). Шаблон в документации назван `/etc/cloud/templates/hosts.tmpl`; на Ubuntu фактически используется дистрибутивный вариант `/etc/cloud/templates/hosts.debian.tmpl` (точный путь написан в комментарии в начале самого `/etc/hosts`; ⚠ имя дистрибутивного шаблона по документации не подтверждено, проверьте `ls /etc/cloud/templates/`). Решение: `manage_etc_hosts: false` в `/etc/cloud/cloud.cfg` (или в `cloud.cfg.d/`), либо править шаблон. Проверка: `grep -r manage_etc_hosts /etc/cloud/ /var/lib/cloud/instance/ 2>/dev/null`.

### 4.3. Порядок разрешения имён: /etc/nsswitch.conf и getent

Порядок источников задаёт строка `hosts:` в `/etc/nsswitch.conf`:

```
hosts:          files dns
```

- `files` — `/etc/hosts` (проверяется первым и имеет приоритет над DNS);
- `dns` — резолвер из `/etc/resolv.conf` (в Ubuntu — заглушка systemd-resolved);
- на системах с `libnss-mdns` (обычно десктоп) строка выглядит как `files mdns4_minimal [NOTFOUND=return] dns mdns4` — так она приведена в документации Ubuntu Server;
- могут встречаться модули `resolve` (libnss-resolve), `myhostname` (libnss-myhostname), `mymachines`.

`getent` выполняет запрос **через NSS**, т. е. так же, как это делают обычные программы (включая процессы сервера 1С и PostgreSQL):

```bash
getent hosts srv1c            # что получит приложение
getent ahosts srv1c           # все адреса (IPv4 и IPv6), как их вернёт getaddrinfo()
getent ahostsv4 srv1c         # только IPv4
getent hosts 192.168.1.50     # обратное разрешение
```

Важно: `dig`, `nslookup`, `host` сами `/etc/hosts` и `nsswitch.conf` **не читают** — они шлют DNS-запрос серверу из `/etc/resolv.conf`. Нюанс Ubuntu: этот сервер — заглушка systemd-resolved (`127.0.0.53`), а она [Офиц., systemd-resolved(8)] при `ReadEtcHosts=yes` (по умолчанию) отвечает и записями из `/etc/hosts`. Поэтому `dig srv1c` без указания сервера может показать адрес из `/etc/hosts`, и это **не** означает, что запись есть в настоящем DNS. Чтобы спросить именно DNS-сервер — `dig @192.168.1.1 srv1c.corp.local`; чтобы узнать, что увидит приложение, — `getent hosts srv1c`. Если `dig @сервер` отвечает одно, а `getent hosts` другое — приложение увидит то, что показал `getent`.

Если для домена поиска не задан `search`, короткие (однокомпонентные) имена через DNS могут не разрешаться: [Офиц., systemd-resolved(8)] запросы A/AAAA для однокомпонентных имён по умолчанию **не отправляются** на внешние DNS-серверы («never sent out to remote DNS servers by default») — только с подстановкой доменов поиска либо через LLMNR; включить отправку можно параметром `ResolveUnicastSingleLabel=yes` в `resolved.conf`. Отсюда правило: либо задавайте `nameservers: search:` в netplan, либо используйте FQDN, либо прописывайте имена в `/etc/hosts`.

### 4.4. systemd-resolved и resolvectl

`systemd-resolved` — локальный кэширующий резолвер. [Офиц.]:

- слушает `127.0.0.53:53` (UDP и TCP) — полнофункциональная заглушка (stub), и `127.0.0.54:53` — «прокси»-режим без проверки DNSSEC и без LLMNR/mDNS (второй адрес описан в man-странице 24.04 (systemd 255); в 22.04 с systemd 249 слушается только `127.0.0.53` — уточнено 11.10.2026 по файлу NEWS systemd: второй адрес `127.0.0.54` появился в версии 250 (раздел «CHANGES WITH 250»), а не 251; ранее было: номер версии, в которой появился `127.0.0.54` (251), приведён по памяти);
- `/etc/resolv.conf` в Ubuntu — симлинк на `/run/systemd/resolve/stub-resolv.conf` (внутри `nameserver 127.0.0.53` и домены поиска);
- реальные вышестоящие DNS-серверы — в `/run/systemd/resolve/resolv.conf`;
- режимы работы с `/etc/resolv.conf` определяются автоматически по тому, на что указывает симлинк: `stub-resolv.conf` (рекомендуемый), `/usr/lib/systemd/resolv.conf` (статическая заглушка без доменов поиска), `/run/systemd/resolve/resolv.conf` (список реальных серверов, клиенты ходят мимо заглушки), либо чужой файл (resolved только читает его);
- сам синтезирует ответы для локального имени хоста (в **все настроенные локальные адреса**, а если их нет — в `127.0.0.2` и `::1`), `localhost` (и `*.localhost`), `_gateway` (текущий шлюз по умолчанию), `_outbound` (локальный адрес, с которого уходит трафик по маршруту по умолчанию);
- записи из `/etc/hosts` учитывает в обе стороны — имя → адрес и адрес → имя (отключается `ReadEtcHosts=no`).

Следствие для сервера 1С: если строку `127.0.1.1 <имя>` из `/etc/hosts` просто **удалить** (ничего не вписав взамен), то при стандартном `hosts: files dns` собственное имя сервера всё равно разрешится — его синтезирует systemd-resolved во все локальные адреса интерфейсов. Это работает, но результат зависит от набора интерфейсов (несколько адресов, IPv6, адреса Docker-мостов), поэтому надёжнее явная строка `<реальный IP> <FQDN> <имя>` (п. 4.2).

Команды:

```bash
resolvectl status                    # глобальные и по-интерфейсные DNS-серверы, домены поиска, DNSSEC
resolvectl status enp0s3
resolvectl query srv1c               # разрешить имя через resolved (показывает источник ответа)
resolvectl query 192.168.1.50        # обратный запрос
resolvectl dns                       # DNS-серверы по интерфейсам
resolvectl domain                    # домены поиска
sudo resolvectl flush-caches         # сбросить кэш
resolvectl statistics                # статистика кэша
sudo resolvectl dns enp0s3 8.8.8.8 8.8.4.4    # временно задать DNS интерфейсу
sudo resolvectl revert enp0s3                  # вернуть настройки интерфейса
ls -l /etc/resolv.conf               # убедиться, что это симлинк на stub-resolv.conf
cat /run/systemd/resolve/resolv.conf # реальные вышестоящие DNS
```

Как правильно задавать DNS:

- **постоянно** — в netplan (`nameservers: addresses: [...]`, `search: [...]`), затем `sudo netplan apply`;
- глобально для всех интерфейсов — `/etc/systemd/resolved.conf` или drop-in `/etc/systemd/resolved.conf.d/*.conf` (параметры `DNS=`, `FallbackDNS=`, `Domains=`, `DNSStubListener=`, `LLMNR=`, `MulticastDNS=`, `DNSSEC=`, `Cache=`), затем `sudo systemctl restart systemd-resolved`;
- если адрес получен по DHCP, а DNS нужен свой: `dhcp4-overrides: {use-dns: false}` + `nameservers:` в netplan.

Не редактируйте `/etc/resolv.conf` вручную и не заменяйте симлинк обычным файлом без необходимости — правки перезапишутся или сломают split-DNS. Если порт 53 нужен другому DNS-серверу на этом же хосте (dnsmasq, bind, AdGuard) — `DNSStubListener=no` в `resolved.conf` и перенаправление симлинка на `/run/systemd/resolve/resolv.conf`.

### 4.5. Почему разрешение имён критично для кластера серверов 1С

**Механизм** [Офиц., «Руководство администратора. Клиент-серверный вариант», п. 2.2.2 «Client application and server cluster interaction», англ. версия для 8.5.1 на kb.1ci.com; то же в 8.3.22–8.3.27]. Клиент и процессы кластера общаются по TCP/IP; «каждый процесс кластера адресуется **именем рабочего сервера**, на котором он запущен, **и номером сетевого порта**» («Each cluster process is addressed using the name of a working server where it runs, and the network port number»). Клиент (тонкий/толстый клиент, конфигуратор, модуль веб-сервера, консоль администрирования) сначала обращается по адресу кластера — к **менеджеру кластера** (`rmngr`), в примере документации `1C_Serv:1541`. Менеджер назначает клиенту рабочий процесс (`rphost`) и передаёт его адрес — в примере документации `1C_Serv:1561`, т. е. то же **имя рабочего сервера** и порт из диапазона 1560:1591. Дальше клиент **сам** разрешает это имя и подключается напрямую к рабочему процессу, который и выполняет аутентификацию пользователя базы и всю дальнейшую работу.

Откуда берётся имя [Офиц., п. 5.2.6 «Operations with the list of working servers in a cluster»]: у рабочего сервера в кластере есть свойство **«Компьютер»** — «сетевой адрес рабочего сервера, на котором запущен агент сервера»; адрес кластера для клиента формируется как `<свойство «Компьютер»>:<порт главного менеджера кластера>`. Там же прямо сказано: **если в качестве сетевого адреса рабочего сервера (свойство «Компьютер») указан IP-адрес в точечной нотации, добавлять его в записи DNS (файл hosts) не требуется.** При автоматическом создании кластера в это свойство попадает имя хоста, поэтому по умолчанию разрешение имени обязательно. (⚠ не подтверждено: что именно — короткое имя или FQDN — попадает в свойство при автосоздании кластера на Linux, документация не уточняет; посмотрите в консоли или `rac server list --cluster=<id>`, поле `agent-host`.)

Из этого следуют **требования**:

1. **На сервере** собственное имя должно разрешаться в реальный (не loopback) адрес. При строке `127.0.1.1 srv1c` в `/etc/hosts` процессы кластера работают с адресом `127.0.1.1`, и удалённые клиенты не могут с ними соединиться. [Практика: требование следует из механизма адресации «имя + порт» и многократно подтверждено сообщениями пользователей; в прочитанных разделах официального руководства строка `127.0.1.1` прямо не упоминается. Общая рекомендация Debian Reference для систем с постоянным IP — заменить `127.0.1.1` на постоянный адрес — см. п. 4.2.]
2. **На каждом клиенте** (и на веб-сервере с публикацией, и на других серверах кластера) имя сервера 1С должно разрешаться в тот же реальный адрес — через DNS либо через файл `hosts`. [Офиц., ИТС, статья «Установка Платформы „1С:Предприятие“ в ОС Linux» (8.3.13) и её английская версия «Installing 1C:Enterprise 8 platform on Linux» на kb.1ci.com]: IP-адрес сервера должен корректно разрешаться в имя хоста; запись о соответствии IP-адреса и имени нужно внести в файлы `hosts` тех компьютеров, **с которых будут устанавливаться соединения с кластером серверов**, иначе при установке клиентского соединения с рабочим процессом кластера возникнет ошибка; файл в Windows — `%windir%\system32\drivers\etc\hosts`, в Linux — `/etc/hosts`; формат записи — `IP-адрес hostname.local hostname`; адрес смотрят командой `ifconfig`, имя — `hostname -f`.
3. Указать в строке подключения клиента **IP-адрес** вместо имени недостаточно: первое соединение (к 1541) пройдёт, но дальше кластер вернёт **имя** рабочего сервера, и клиент всё равно должен будет его разрешить. [Офиц., FAQ 1Ci «How to resolve "No such host is known" error»: ошибка возникает «независимо от того, указано в настройках базы имя сервера или IP»; лечится записью `IP имя_сервера` в `C:\Windows\System32\drivers\etc\hosts` клиента, имя сервера смотрят в консоли администрирования в ветке центральных серверов.] Альтернатива на стороне сервера — указать IP-адрес в свойстве «Компьютер» рабочего сервера (см. «Механизм» выше).
4. Адрес сервера должен быть **постоянным**; если он может измениться, связывать имя с адресом надо через DNS/`hosts` (так и рекомендует статья ИТС).
5. Имя хоста задают **до** первого запуска сервера 1С (до создания кластера). [Офиц., п. 2.2.1 «General concepts» руководства администратора] Сведения о кластере хранятся в двух реестрах: **реестр сервера** — файл `1cv8wsrv.lst` в каталоге данных сервера (список кластеров, в которые входит сервер, и администраторы сервера) и **реестр кластера** — файл `1cv8clst.lst` (на диске — `1CV8Clst.lst`; в Linux регистр имени важен) в каталоге данных кластера `reg_<порт менеджера>` внутри каталога данных сервера (список баз, рабочих серверов, рабочих процессов, менеджеров, сервисов, администраторов кластера); его ведёт главный менеджер кластера. Каталог данных сервера на Linux по умолчанию — `/home/usr1cv8/.1cv8/1C/1cv8` (переменная `SRV1CV8_DATA`), т. е. файлы — `/home/usr1cv8/.1cv8/1C/1cv8/1cv8wsrv.lst` и `/home/usr1cv8/.1cv8/1C/1cv8/reg_1541/1CV8Clst.lst`. После переименования хоста кластер продолжает отдавать клиентам **старое** имя (оно записано в свойстве «Компьютер» рабочего сервера в реестре кластера); лечится пересозданием кластера (остановить сервер, сделать копию и убрать каталог данных, запустить, заново зарегистрировать базы) либо исправлением записи о рабочем сервере через консоль администрирования. [Практика; ⚠ не подтверждено: сама процедура «после переименования» в документации не описана, и можно ли изменить «Компьютер» у уже существующего рабочего сервера без его удаления/добавления — проверьте на своей версии; у `rac server insert` адрес задаётся параметрами `--agent-host`/`--agent-port`. Перед любыми действиями с `*.lst` остановите сервер 1С и сделайте копию каталога данных.]
6. Имя сервера PostgreSQL, указанное в параметрах информационной базы, разрешается **на сервере 1С** (а не на клиенте): проверяйте его `getent hosts <имя_СУБД>` именно там.

**Рекомендации сообщества по `/etc/hosts` сервера 1С** [Практика, форумы Infostart, linux.org.ru]: одна строка «реальный IP – FQDN – короткое имя»; не привязывать имя сервера к `127.0.0.1`/`127.0.1.1`/`localhost.localdomain`; не держать имя сервера в IPv6-строках (`::1`); при работе в домене Active Directory имя должно быть FQDN и разрешаться через DNS (прямая и обратная зона), а не только через `hosts`.

**Типовые симптомы:**

| Симптом у клиента / администратора | Вероятная причина | Что проверить |
|---|---|---|
| «Сервер 1С:Предприятия не обнаружен. Не запущен ни один рабочий процесс. Соединение с информационной базой невозможно» | на сервере имя разрешается в `127.0.1.1`; либо `rphost` действительно не запущен | на сервере: `hostname -i`, `getent hosts $(hostname)`, `pgrep -a rphost`, `ss -tlnp \| grep -E 'ragent\|rmngr\|rphost'` |
| «Ошибка сетевого доступа к серверу… Этот хост неизвестен» (Windows Sockets 11001), в тексте `server_addr=tcp://srv1c:1560` или `:1541` | клиент не может разрешить имя сервера (нет записи в DNS/`hosts`) | на клиенте: `ping srv1c`, `Resolve-DnsName srv1c`; добавить запись в `hosts` |
| «…конечный компьютер отверг запрос на подключение» (10061), в тексте адрес `127.0.1.1:1560` или адрес клиента | сервер отдал loopback-адрес либо имя на клиенте разрешается не в тот IP | `hosts` на сервере и на клиенте |
| «Попытка установить соединение была безуспешной…» (10060, таймаут) на портах 1560–1591, при этом 1541 доступен | firewall пропускает 1540–1541, но не диапазон рабочих процессов | `sudo ufw status`, с клиента `Test-NetConnection srv1c -Port 1560` |
| Консоль администрирования подключается к агенту (1540), но не открывает кластер/процессы | закрыт 1541 или 1560–1591; имя рабочего сервера не разрешается с машины администратора | то же |
| После переименования сервера клиенты ищут старое имя | старое имя осталось в реестре кластера | список рабочих серверов в консоли/`rac server list` |

О текстах сообщений. [Офиц., FAQ 1Ci] В англоязычном интерфейсе ошибка неразрешённого имени выглядит так: `Connection error, reason: server_addr=[ИМЯ СЕРВЕРА] descr=11001(0x00002AF9): No such host is known.` и далее служебное `line=… file=src\core\src\Networking.cpp` — т. е. в `server_addr=` стоит именно **имя рабочего сервера**, которое вернул кластер. Русские формулировки («Этот хост неизвестен», «…конечный компьютер отверг запрос на подключение», «Попытка установить соединение была безуспешной…») — это стандартные системные тексты Windows для кодов Winsock 11001 (WSAHOST_NOT_FOUND), 10061 (WSAECONNREFUSED) и 10060 (WSAETIMEDOUT); обрамление («Ошибка сетевого доступа к серверу (Windows Sockets - …)», `server_addr=tcp://…`) зависит от версии платформы — ⚠ не подтверждено дословно для русского интерфейса. На Linux-клиентах вместо кодов Winsock будут тексты `errno` (например, `Connection refused`, `Name or service not known`). Фраза «Не запущен ни один рабочий процесс» подтверждена только по сообщениям пользователей (linux.org.ru).

**Диагностический минимум:**

```bash
# на сервере 1С
hostname; hostname -f; hostname -i
getent hosts "$(hostname)"
grep -v '^#' /etc/hosts
sudo ss -tlnp | grep -E ':(1540|1541|1545|15[6-9][0-9])\b'
```

```powershell
# на Windows-клиенте
ping srv1c                       # разрешение имени так, как его видит приложение (с учётом файла hosts)
Resolve-DnsName srv1c            # системный резолвер Windows: hosts + кэш + DNS (как у приложений)
Resolve-DnsName srv1c -DnsOnly -NoHostsFile   # только DNS, без файла hosts (то же покажет nslookup srv1c)
Test-NetConnection srv1c -Port 1541
Test-NetConnection srv1c -Port 1560
notepad C:\Windows\System32\drivers\etc\hosts    # от имени администратора; строка: 192.168.1.50  srv1c.corp.local srv1c
ipconfig /flushdns
```

## 5. Диагностика сети

Набор предустановленных утилит зависит от образа (в minimal-установке нет почти ничего). Проверка наличия: `command -v dig nc tcpdump mtr`. Установка всего набора:

```bash
sudo apt update
sudo apt install iputils-ping iputils-tracepath traceroute mtr-tiny bind9-dnsutils \
                 netcat-openbsd telnet curl wget nmap tcpdump ethtool iperf3 net-tools
```

| Утилита | Пакет Ubuntu |
|---|---|
| `ip`, `ss`, `bridge`, `nstat` | `iproute2` |
| `ping` | `iputils-ping` |
| `tracepath` | `iputils-tracepath` |
| `traceroute` | `traceroute` (или `inetutils-traceroute`) |
| `mtr` | `mtr-tiny` (без GUI) |
| `dig`, `nslookup`, `host` | `bind9-dnsutils` (старое имя `dnsutils`), `bind9-host` |
| `nc` | `netcat-openbsd` |
| `telnet` | `telnet` (в 24.04+ — `inetutils-telnet`) |
| `ifconfig`, `route`, `netstat`, `arp` | `net-tools` |
| `smbclient`, `mount.cifs` | `smbclient`, `cifs-utils` |

### 5.1. Логика поиска неисправности (снизу вверх)

1. Линк и адрес: `ip -br a` — интерфейс `UP`, адрес есть?
2. Шлюз: `ip r` — есть `default via …`? `ping -c3 <шлюз>`.
3. Маршрутизация наружу: `ping -c3 1.1.1.1`.
4. DNS: `resolvectl status`, `getent hosts ubuntu.com`, `dig ubuntu.com`.
5. Слушает ли служба: `sudo ss -tlnp | grep <порт>` — и на каком адресе (`0.0.0.0`/`*` — на всех, `127.0.0.1` — только локально).
6. Локальный firewall: `sudo ufw status verbose`.
7. Доступность порта извне: `nc -zv <хост> <порт>` с клиента.
8. Если порт «filtered»/таймаут — firewall по пути; если «refused» — узел доступен, но порт никто не слушает (или слушает на другом адресе).
9. Содержимое обмена: `tcpdump`.

### 5.2. ping

```bash
ping -c 4 192.168.1.1              # 4 пакета и выход
ping -c 3 -W 2 srv1c               # ждать ответ не более 2 с
ping -i 0.2 -c 50 srv1c            # интервал 0.2 с (оценка потерь)
ping -I enp0s8 192.168.56.1        # через конкретный интерфейс
ping -4 -c 3 srv1c                 # принудительно IPv4 (ping -6 — IPv6)
ping -M do -s 1472 192.168.1.1     # проверка MTU: запрет фрагментации, 1472 + 28 байт заголовков = 1500
```

Отсутствие ответа на ping не означает недоступность узла — ICMP может быть закрыт (Windows по умолчанию не отвечает на ping из «общедоступной» сети). Проверяйте конкретный TCP-порт.

### 5.3. tracepath, traceroute, mtr

```bash
tracepath -n srv1c                 # маршрут + определение Path MTU; не требует root
traceroute -n 8.8.8.8              # UDP-пробы (по умолчанию)
sudo traceroute -I -n 8.8.8.8      # ICMP-пробы
sudo traceroute -T -p 443 -n ya.ru # TCP SYN на порт 443 (проходит там, где закрыты UDP/ICMP)
mtr -n 8.8.8.8                     # интерактивно: traceroute + ping в реальном времени
mtr -rwc 50 -n 8.8.8.8             # отчёт: 50 циклов, широкий формат (для вставки в заявку провайдеру)
sudo mtr -T -P 1541 -n srv1c       # TCP-режим на порт 1541
```

Потери на промежуточном узле при нулевых потерях на конечном — это ограничение ICMP на маршрутизаторе, а не проблема.

### 5.4. dig, nslookup, host

```bash
dig srv1c.corp.local               # полный ответ: секции QUESTION/ANSWER, сервер, время
dig +short srv1c.corp.local        # только адрес
dig @192.168.1.1 srv1c.corp.local  # спросить конкретный DNS-сервер
dig -x 192.168.1.50 +short         # обратная запись (PTR)
dig corp.local MX +noall +answer   # другой тип записи, только секция ответа
dig +trace ubuntu.com              # проследить делегирование от корня
nslookup srv1c 192.168.1.1         # то же в стиле Windows
host srv1c.corp.local
```

Напоминание: эти утилиты не используют NSS (`nsswitch.conf`); без `@сервер` они спрашивают заглушку systemd-resolved, которая подмешивает записи `/etc/hosts`, с `@сервер` — конкретный DNS-сервер напрямую (см. п. 4.3). Для проверки «как видит приложение» — `getent hosts`.

### 5.5. ss — сокеты и соединения

Основные флаги: `-t` TCP, `-u` UDP, `-l` только слушающие, `-a` все, `-n` без разрешения имён и портов, `-p` процесс (для чужих процессов нужен `sudo`), `-4`/`-6`, `-s` сводка, `-o` таймеры, `-i` внутренняя информация TCP (rtt, cwnd), `-m` память, `-e` расширенно (uid, inode), `-H` без заголовка.

```bash
sudo ss -tulpn                         # кто что слушает (TCP+UDP, с процессами)
sudo ss -tlnp | grep -E 'ragent|rmngr|rphost|ras'    # порты сервера 1С
sudo ss -tlnp 'sport = :5432'          # кто слушает 5432
ss -s                                  # сводка по количеству сокетов
ss -tn state established               # установленные TCP-соединения
ss -tn state established '( dport = :5432 or sport = :5432 )'    # соединения с PostgreSQL
ss -Htn state established '( sport = :1541 )' | wc -l            # сколько клиентов на менеджере кластера
ss -tn dst 192.168.1.20                # соединения с конкретным узлом
ss -tn 'sport >= :1560 and sport <= :1591'   # соединения рабочих процессов
ss -tni dst 192.168.1.20               # с TCP-метриками (rtt, retrans)
ss -tan state time-wait | wc -l        # сокеты в TIME-WAIT
```

Колонка `Local Address:Port`: `0.0.0.0:5432` или `*:5432` — слушает на всех адресах; `127.0.0.1:5432` — только локально (типичная причина «с сервера работает, с клиента нет»: у PostgreSQL `listen_addresses = 'localhost'`); `[::]:22` — IPv6 (обычно принимает и IPv4).

### 5.6. nc (netcat), telnet и проверка порта без утилит

```bash
nc -zv srv1c 1541                  # проверить один порт (-z без передачи данных, -v подробно)
nc -zv -w 3 srv1c 1540-1541        # диапазон, таймаут 3 с
nc -zv srv1c 1560-1591 2>&1 | grep -v refused    # какие порты рабочих процессов открыты
nc -zvu srv1c 123                  # UDP (результат ненадёжен: UDP не подтверждает доставку)
nc -l 9999                         # слушатель на порту 9999 (проверить, что firewall пропускает)
nc -lk 9999                        # слушатель, не завершающийся после первого клиента
nc srv1c 9999                      # подключиться к слушателю и «поболтать»
nc -l 9999 > file.bin              # приём файла ...
nc -N srv1c 9999 < file.bin        # ... и отправка (-N закрыть соединение по EOF)
telnet srv1c 1541                  # интерактивная проверка; выход: Ctrl+] затем quit
timeout 3 bash -c '</dev/tcp/srv1c/1541' && echo open || echo closed   # вообще без утилит
```

Приём «слушатель + проверка»: остановить службу нельзя, а понять, режет ли firewall порт, нужно — поднимите `nc -l` на свободном соседнем порту из того же правила.

### 5.7. curl

| Флаг | Назначение |
|---|---|
| `-v` | подробный обмен: DNS, TCP, TLS, заголовки запроса/ответа |
| `-I` | только заголовки ответа (метод HEAD) |
| `-i` | заголовки ответа вместе с телом |
| `-k` | не проверять TLS-сертификат (самоподписанные) |
| `-o файл` / `-O` | сохранить в файл / под именем из URL |
| `-L` | следовать перенаправлениям |
| `--resolve host:port:addr` | подменить разрешение имени для этого запроса (тест виртуального хоста/сертификата без правки hosts) |
| `-x http://proxy:3128` | через прокси; `--noproxy host1,host2` — исключения |
| `-u user:pass` | Basic-аутентификация |
| `-d 'данные'` | тело запроса (POST); `-d @file.json` — из файла |
| `-H 'Имя: значение'` | заголовок |
| `-X МЕТОД` | явный метод (PUT, DELETE, PATCH) |
| `-s` / `-S` / `-f` | тихо / показывать ошибки при `-s` / код возврата ≠ 0 при HTTP ≥ 400 |
| `-w 'формат'` | вывести метрики: `%{http_code}`, `%{time_total}`, `%{remote_ip}` |
| `--connect-timeout N`, `-m N` | таймаут соединения / всего запроса |
| `-C -` | докачка |
| `--cacert файл` | свой корневой сертификат |
| `-4` / `-6` | принудительно IPv4 / IPv6 |

```bash
curl -I http://srv1c/base/                                   # жива ли веб-публикация 1С
curl -sk -o /dev/null -w '%{http_code} %{time_total}s\n' https://srv1c/base/
curl -u 'user:pass' -H 'Accept: application/json' 'http://srv1c/base/odata/standard.odata/'
curl -u 'user:pass' -X POST -H 'Content-Type: application/json' -d '{"a":1}' http://srv1c/base/hs/api/v1/ping
curl -v --resolve srv1c.corp.local:443:192.168.1.50 https://srv1c.corp.local/base/
curl -L -O https://example.com/file.tar.gz
curl -x http://proxy.corp.local:3128 -I https://ubuntu.com
curl -v telnet://srv1c:1541                                  # проверка TCP-порта, если нет nc/telnet
```

### 5.8. wget

```bash
wget https://example.com/file.deb               # скачать в текущий каталог
wget -O /tmp/f.deb https://example.com/file.deb # под заданным именем
wget -c URL                                     # докачка
wget -P /opt/distr URL                          # в каталог
wget -q --show-progress URL                     # тихо, но с прогрессом
wget --no-check-certificate URL                 # не проверять сертификат
wget --user=u --password=p URL
wget -S --spider URL                            # только проверить доступность и заголовки
```

### 5.9. nmap (основное)

Сканируйте только свои узлы и сети.

```bash
nmap -p 22,80,443,1540,1541,1545,1560-1591,5432 srv1c   # проверить порты стека
nmap -Pn -p 1541 srv1c            # не делать ping-проверку (узел не отвечает на ICMP)
sudo nmap -sS -p- srv1c           # SYN-скан всех 65535 TCP-портов (root)
nmap -sT -p 1-1024 srv1c          # connect-скан (без root)
sudo nmap -sU -p 53,123,137 srv1c # UDP
nmap -sV -p 22,5432 srv1c         # определить версии служб
nmap -sn 192.168.1.0/24           # кто живой в сети (без сканирования портов)
nmap --open -n -T4 -oN scan.txt -p 1-10000 srv1c   # только открытые, без DNS, быстрее, отчёт в файл
```

Состояния: `open` — порт слушают; `closed` — узел ответил RST (никто не слушает, firewall не мешает); `filtered` — ответа нет (firewall отбрасывает пакеты).

### 5.10. tcpdump

Флаги [Офиц., tcpdump(8) для 24.04]: `-i ИФ` (или `any` — все интерфейсы, без promiscuous-режима), `-n` не преобразовывать адреса **и номера портов** в имена (в старых инструкциях для портов пишут `-nn` — это по-прежнему принимается, но одного `-n` достаточно), `-c N` остановиться после N пакетов, `-w файл` записать в pcap, `-r файл` прочитать, `-s N` длина захвата (по умолчанию 262144 байта, т. е. пакет целиком; `-s 0` означает то же значение по умолчанию), `-A` показать содержимое ASCII, `-X` hex+ASCII, `-e` канальные заголовки (MAC), `-v/-vv` подробнее, `-tttt` дата и время, `-C N -W K` ротация файлов по размеру (N — в **миллионах байт**, K — число файлов по кругу), `-G сек` ротация по времени (в имени файла `-w` нужен шаблон strftime, иначе файл перезаписывается; с `-W K` tcpdump завершится после K файлов), `-D` список интерфейсов.

Подводный камень: после открытия интерфейса tcpdump по умолчанию сбрасывает права до пользователя `tcpdump` (`-Z tcpdump`), поэтому запись `-w` в каталог, доступный только root (например, `/root`), завершится `Permission denied` — пишите в `/tmp` или каталог с правами для `tcpdump`, либо добавьте `-Z root`.

Фильтры (BPF): `host A`, `src A`, `dst A`, `net 192.168.1.0/24`, `port N`, `src port N`, `portrange A-B`, `tcp`, `udp`, `icmp`, `arp`, связки `and` / `or` / `not`, скобки (в кавычках).

```bash
sudo tcpdump -D                                          # список интерфейсов
sudo tcpdump -ni enp0s3 icmp                             # приходят ли ping
sudo tcpdump -ni any port 5432                           # обмен с PostgreSQL
sudo tcpdump -ni any 'tcp portrange 1540-1541 or tcp portrange 1560-1591'    # трафик кластера 1С
sudo tcpdump -ni enp0s3 host 192.168.1.20 and not port 22                   # всё от клиента, кроме SSH
sudo tcpdump -ni any 'tcp[tcpflags] & (tcp-syn|tcp-rst) != 0 and port 1541' # только установление/сброс соединений
sudo tcpdump -ni any -s 0 -w /tmp/1c.pcap 'host 192.168.1.20 and tcp portrange 1540-1591'  # запись для Wireshark
sudo tcpdump -ni any -w /tmp/cap-%H%M.pcap -G 300 -W 12 port 5432           # по файлу на 5 минут, 12 файлов
tcpdump -nn -r /tmp/1c.pcap | head                                          # прочитать запись
sudo tcpdump -ni any -A -s 0 'tcp port 80' | grep -iE '^(GET|POST|HTTP|Host:)'
```

Как читать: приходят SYN, ответа нет — пакеты доходят, но отбрасываются локальным firewall или служба не слушает на этом адресе; SYN вообще не видно — блокировка до сервера; в ответ `RST` (`Flags [R.]`) — порт закрыт. Файл `.pcap` забирается на Windows (`scp`) и открывается в Wireshark.

### 5.11. ethtool

```bash
sudo ethtool enp0s3              # скорость, дуплекс, автосогласование, «Link detected: yes/no»
ethtool -i enp0s3                # драйвер, версия, шина (e1000 / virtio_net / hv_netvsc / vmxnet3)
ethtool -S enp0s3                # счётчики драйвера (ошибки, дропы)
ethtool -k enp0s3                # offload-функции (tso, gso, gro, checksum)
sudo ethtool -K enp0s3 tso off gso off gro off   # временно отключить offload (диагностика «битых» пакетов в ВМ)
sudo ethtool -s enp0s3 speed 1000 duplex full autoneg on
sudo ethtool -p enp0s3 10        # помигать индикатором порта 10 с (физический сервер)
```

В виртуальной машине скорость/дуплекс часто показываются условно (`Unknown!` или 10000Mb/s) — это нормально.

### 5.12. iperf3 — измерение пропускной способности

```bash
iperf3 -s                         # на сервере: слушать TCP 5201 (при ufw: sudo ufw allow 5201/tcp)
iperf3 -c srv1c                   # на клиенте: 10-секундный тест TCP клиент → сервер
iperf3 -c srv1c -R                # обратное направление (сервер → клиент)
iperf3 -c srv1c -t 30 -P 4        # 30 с, 4 параллельных потока
iperf3 -c srv1c -u -b 100M        # UDP 100 Мбит/с: потери и джиттер
iperf3 -c srv1c -p 5202           # другой порт (на сервере: iperf3 -s -p 5202)
```

Для Windows есть сборки iperf3; полезно для оценки сети «клиент ↔ сервер 1С» и «сервер 1С ↔ сервер СУБД».

### 5.13. Прочее полезное

```bash
nstat -az | grep -iE 'retrans|listen|drop'   # счётчики ядра TCP (повторы, переполнение очередей)
ip -s link show dev enp0s3                   # ошибки/дропы интерфейса
sudo journalctl -k | grep -iE 'link is|enp0s3'   # сообщения ядра о линке
sudo journalctl -u systemd-networkd -u systemd-resolved -b
sudo lshw -class network -short              # сетевые адаптеры
sudo conntrack -L | head                     # таблица отслеживания соединений (пакет conntrack)
```

## 6. Порты стека 1С + PostgreSQL

| Порт (TCP) | Компонент | Чем задаётся | Кто подключается |
|---|---|---|---|
| **1540** | агент сервера `ragent` (порт рабочего сервера) | параметр `ragent -port`, на Linux переменная `SRV1CV8_PORT`; по умолчанию 1540 | консоль администрирования кластера, сервер `ras`, другие серверы кластера |
| **1541** | главный менеджер кластера `rmngr` («порт кластера») | `ragent -regport`, `SRV1CV8_REGPORT`; по умолчанию 1541 | все клиенты 1С (первое обращение), веб-сервер с публикацией, консоль |
| **1560–1591** | рабочие процессы `rphost` и дополнительные менеджеры кластера (по одному порту на процесс; порт выбирается автоматически — доступен должен быть **весь** диапазон) | `ragent -range 1560:1591` (в новых версиях документации — `/range`), `SRV1CV8_RANGE`; по умолчанию `1560:1591`; также свойство «Диапазон IP-портов» рабочего сервера (по умолчанию `1560:1591`) | все клиенты 1С, веб-сервер, консоль, другие серверы кластера |
| **1545** | сервер администрирования `ras` | `ras cluster --port=<порт>` (или `-p`); по умолчанию 1545; адрес агента по умолчанию `localhost:1540` | утилита `rac`, сторонние консоли и системы мониторинга |
| 1555 | порт мониторинга `ras` (`--monitor-port`, адрес `--monitor-address`, по умолчанию `localhost`) | параметры запуска `ras`; описан в руководстве 8.3.25 | локальный мониторинг; наружу не открывать |
| **1550** | сервер отладки `dbgs` (отладка по HTTP): запускается кластером при `ragent -debug -http` (`SRV1CV8_DEBUG="-debug -http"`) | `ragent /debugServerPort <порт>`, по умолчанию 1550; адрес — `/debugServerAddr` | конфигуратор разработчика |
| **5432** | PostgreSQL | `port` и `listen_addresses` в `postgresql.conf`, доступ — `pg_hba.conf` | сервер 1С (`rphost`, `rmngr`), администратор (psql/pgAdmin) |
| **80 / 443** | веб-сервер (Apache/nginx) с публикацией баз, HTTP-сервисов, OData | конфигурация веб-сервера | веб-клиенты, тонкие клиенты через HTTP, мобильные клиенты, интеграции |
| **22** | SSH | `Port` в `sshd_config` | администратор |
| 475 (UDP; TCP на стороне менеджера можно включить) | HASP License Manager — сетевые аппаратные ключи HASP4/HASP HL Net (если используются USB-ключи с менеджером лицензий) | клиент: `NH_PORT_NUMBER` в `nethasp.ini`; менеджер: `NHS_IP_PORTNUM` в `nhsrv.ini`; оба по умолчанию 475 | клиенты/сервер 1С → машина с ключом. [Офиц., FAQ 1Ci «Setting up HASP license manager»]: в 1С обращение к HASP License Manager **всегда идёт по UDP** (значение `NH_TCPIP_METHOD = TCP` игнорируется), только IPv4 |
| 1947 (UDP/TCP) | служба ключей защиты Sentinel/HASP LDK (общеизвестный порт Sentinel License Manager [Практика]) | — | [Офиц., FAQ 1Ci, две статьи]: в перечне портов сервера 1С назван «UDP 1947 — служба лицензионного ключа HASP»; в статье о раздаче конкурентных лицензий Linux-сервером сказано, что порт 1947 на сервере нужно открыть — он «используется для приёма запросов лицензирования». ⚠ не подтверждено: какие именно компоненты 1С и в каких сценариях используют 1947, документация не раскрывает — открывайте его только при реальной необходимости и только для своей сети |

Подтверждения и оговорки:

- [Офиц.] Значения 1540, 1541, 1560:1591 — параметры запуска `ragent` (`-port`/`/port`, `-regport`/`/regport`, `-range`/`/range`) из «Руководства администратора. Клиент-серверный вариант» (англ. версия на kb.1ci.com, проверено для 8.3.24 и 8.5.1): `/port` — порт агента, по умолчанию 1540; `/regport` — порт главного менеджера кластера, по умолчанию 1541; `/range` — диапазоны портов для динамического выбора, по умолчанию 1560:1591; кластер, который агент создаёт по умолчанию при первом запуске, получает порт 1541 и диапазон 1560:1591; свойства рабочего сервера: «IP-порт» — 1540, «Диапазон IP-портов» — 1560:1591. FAQ 1C International: «1540 — server agent port, 1541 — cluster manager port, 1560–1591 — working processes», протокол TCP.
- [Офиц., руководство администратора **8.5.1**, приложение 3 «Рекомендации по обеспечению безопасности кластера серверов», п. 3.8 «Сетевой экран»] порты по умолчанию: 1540 — агент сервера (`ragent`), 1541 — менеджер кластера (`rmngr`), 1545 — сервер администрирования (`ras`), 1550 — сервер отладки (`dbgs`), 1560–1591 — рабочие процессы (`rphost`), «конкретный порт выделяется автоматически». Рекомендации оттуда же: открывать доступ **только** к тем сетевым портам, которые нужны для работы кластера (в тексте названы оба протокола — «over TCP and UDP»; фактически обмен с кластером идёт по TCP [Практика, FAQ 1Ci]); если на компьютере несколько кластеров — ко всем их портам; если порты изменены в строках запуска — контролировать новые; **если пользователи подключаются только через веб-сервер (80/443), рекомендуется закрыть доступ ко всем перечисленным портам кластера**.
- **Порты по умолчанию в 8.5.x те же, что в 8.3.x** — подтверждено по руководству 8.5.1 (п. 2.2.2: агент 1540, менеджер 1541, диапазон 1560:1591; п. 3.8: `ras` 1545, `dbgs` 1550). Для более поздних выпусков 8.5 (8.5.2+) не проверялось.
- [Офиц., руководство администратора 8.3.25, п. 5.3.2] `ras`: порт по умолчанию 1545 (`--port`/`-p`), адрес агента по умолчанию `localhost:1540`, параметры мониторинга `--monitor-address` (по умолчанию `localhost`), `--monitor-base` (`/`), `--monitor-port` (1555). Запуск на Linux приложением: `./ras cluster --port=1545 localhost:1540`; демоном: `./ras cluster --daemon --port=1545 localhost:1540`. Аутентификация ОС в `ras` не поддерживается (только аутентификация 1С). Версии `ras` и кластера должны совпадать; `rac` должен соответствовать версии `ras`. (Страница п. 5.3.2 для 8.5.1 на kb.1ci.com пуста — для 8.5 синтаксис `ras` не проверен.)
- [Офиц., руководство 8.3.24–8.5.1, п. 4.2] отладка: `SRV1CV8_DEBUG` — пусто (отладка выключена), `-debug` или `-debug -tcp` (по TCP), `-debug -http` (по HTTP); параметр `ragent /debugServerPort` — «порт сервера отладки при отладке по HTTP», по умолчанию 1550.
- ⚠ не подтверждено (расхождение внутри самой документации): в таблице переменных systemd-юнита в п. 4.2.2 «On Linux» (проверено для 8.3.24, 8.3.27 и 8.5.1) значение `SRV1CV8_RANGE` по умолчанию записано как `1561:1590`, тогда как для параметра `/range`, для кластера по умолчанию и для свойства рабочего сервера везде указано `1560:1591`; в FAQ 1Ci про два экземпляра сервера в юните фигурирует `2560:2591`. Что реально записано в поставляемом файле `/opt/1cv8/x86_64/<версия>/srv1cv8-<версия>@.service`, на живой установке не проверялось. Проверьте у себя: `systemctl cat 'srv1cv8-*@default' | grep -i range` и `ps -eo args | grep '[r]agent'`. Для firewall открывайте 1560–1591 (это надмножество обоих вариантов) и сверяйте фактические порты: `sudo ss -tlnp | grep rphost`.
- [Офиц., руководство администратора п. 2.2.1 и 4.3.2; FAQ 1Ci «How to install and run two versions of 1C:Enterprise server on Ubuntu server»] Несколько экземпляров сервера 1С на одном хосте должны использовать разные сетевые порты **и** разные каталоги данных кластера (типовой сдвиг: 2540/2541/2560:2591; в документации — семейства портов «15xx» и «25xx»).
- [Практика, Habr] порты 1540/1541 не имеют достаточной собственной защиты от подключения к кластеру без администратора кластера — не выставляйте их в интернет, ограничивайте по адресам источников и задавайте администраторов кластера/центрального сервера.

Кому что открывать:

| Откуда → куда | Порты |
|---|---|
| Клиенты 1С (тонкий/толстый клиент, конфигуратор) → сервер 1С | 1541, 1560–1591 (на практике открывают 1540–1541 и 1560–1591). Если все пользователи работают только через веб-сервер — эти порты для клиентских сетей закрывают совсем [Офиц., п. 3.8] |
| Веб-сервер (Apache с модулем 1С) → сервер 1С | 1541, 1560–1591 (если веб-сервер на той же машине — ничего открывать не нужно) |
| Браузеры/тонкие клиенты через веб → веб-сервер | 80, 443 |
| Консоль администрирования (MMC на Windows) → сервер 1С | 1540, 1541, 1560–1591 |
| `rac` → `ras` | 1545; `ras` → `ragent`: 1540 (обычно локально) |
| Сервер 1С → PostgreSQL | 5432 (если на одной машине — не открывать, PostgreSQL слушает `localhost`) |
| Администратор → сервер | 22 |
| Конфигуратор (отладка по HTTP) → сервер 1С | 1550 |

Как узнать фактические порты на работающем сервере (не полагаясь на значения по умолчанию):

```bash
sudo ss -tlnp | grep -E 'ragent|rmngr|rphost|ras|dbgs'     # кто и на каких портах слушает
ps -eo user,pid,args | grep -E '[r]agent|[r]mngr|[r]phost'   # параметры запуска: -port, -regport, -range, -debug
systemctl list-units 'srv1cv8*' 'ras*'                       # юниты сервера 1С и ras (имена зависят от версии платформы)
```

### 6.1. Переменные запуска сервера 1С на Linux (сетевые) и управление экземпляром

[Офиц., руководство администратора, п. 4.2.2 «On Linux», англ. версия: 8.3.24, 8.3.27; для 8.5.1 — п. 4.2.2.4] Начиная с платформ с каталогом `/opt/1cv8/<arch>/<версия>/` сервер запускается шаблонным systemd-юнитом `srv1cv8-<версия>@.service` (экземпляр по умолчанию — `default`); параметры задаются переменными окружения:

| Переменная | Смысл | По умолчанию (по документации) |
|---|---|---|
| `SRV1CV8_PORT` | сетевой порт агента сервера (`ragent`) | 1540 |
| `SRV1CV8_REGPORT` | сетевой порт главного менеджера кластера (`rmngr`) | 1541 |
| `SRV1CV8_RANGE` | диапазон(ы) портов для динамического выбора | в таблице документации `1561:1590`, для `/range` — `1560:1591` (см. оговорку выше) |
| `SRV1CV8_DATA` | каталог служебных файлов кластера (списки кластеров и баз) | `/home/usr1cv8/.1cv8/1C/1cv8` |
| `SRV1CV8_DEBUG` | режим отладки: пусто / `-debug` (`-debug -tcp`) / `-debug -http` | пусто |
| `SRV1CV8_SECLEV` | уровень безопасности соединений: 0 — выключено, 1 — только при установке соединения, 2 — постоянно | 0 |
| `SRV1CV8_PINGPERIOD` / `SRV1CV8_PINGTIMEOUT` | период и таймаут проверки разрыва соединений, мс (ненулевые настройки кластера имеют приоритет) | 1000 / 5000 |
| `SRV1CV8_KEYTAB` | keytab-файл для аутентификации ОС (Kerberos) | `/opt/1cv8/x86_64/<версия>/usr1cv8.keytab` |

```bash
V=$(basename "$(ls -d /opt/1cv8/x86_64/8.* | sort -V | tail -1)")   # установленная версия платформы (A.B.C.D)
sudo systemctl link /opt/1cv8/x86_64/$V/srv1cv8-$V@.service         # зарегистрировать юнит
sudo systemctl edit srv1cv8-$V@default       # создать drop-in и переопределить параметры, например:
#   [Service]
#   Environment=SRV1CV8_PORT=2540
#   Environment=SRV1CV8_REGPORT=2541
#   Environment=SRV1CV8_RANGE=2560:2591
sudo systemctl enable srv1cv8-$V@default
sudo systemctl start  srv1cv8-$V@default
systemctl status srv1cv8-$V@default
systemctl cat srv1cv8-$V@default | grep -E 'ExecStart|SRV1CV8_'    # фактические значения переменных
```

[Офиц., п. 4.3.2 «On Linux»] «Нельзя изменить сетевые порты, используемые уже работающим экземпляром сервера»: по документации для смены портов создают **новый** экземпляр сервера с нужными портами, регистрируют в нём базы, переводят пользователей и затем останавливают и удаляют старый экземпляр (порты записаны и в реестре кластера, поэтому одной правки переменных на существующем кластере недостаточно). Несколько экземпляров на одном компьютере должны отличаться и портами, и каталогом данных (пример из FAQ 1Ci: второй экземпляр на 2540/2541/2560:2591 с собственным каталогом данных в `SRV1CV8_DATA`, в строке подключения клиента тогда указывают `сервер:2541`). В старых версиях (каталог `/opt/1C/v8.3/x86_64`, служба `srv1cv83`) те же переменные лежали в `/etc/sysconfig/srv1cv83` (RPM) или `/etc/default/srv1cv83` (DEB). Подробно установка и запуск сервера — в других файлах базы знаний (раздел 1С).

### 6.2. Что уточнить по ИТС (не удалось проверить по открытым источникам)

Большая часть сведений о портах и взаимодействии клиента с кластером проверена по англоязычной версии руководства на kb.1ci.com (8.3.22–8.3.27, 8.5.1). Осталось уточнить по русской документации на ИТС (нужна подписка):

- Фактическое значение `SRV1CV8_RANGE` в описании и в самом файле юнита (расхождение `1560:1591` / `1561:1590`).
- Описание `ras`/`rac` для 8.5.x (страница п. 5.3.2 в английской версии 8.5.1 пуста); есть ли штатный systemd-юнит для `ras` на Linux (в руководстве 8.3.25 описаны только запуск приложением и `--daemon`).
- Приложение о сервере отладки `dbgs` для 8.5.x: параметры автономного запуска.
- Русские формулировки ошибок клиента и официальная процедура переименования центрального сервера (смены свойства «Компьютер»).
- Изменились ли порты по умолчанию в выпусках 8.5 новее 8.5.1 и какая версия платформы актуальна на октябрь 2026.

## 7. Firewall

### 7.1. Как устроено

- В ядре — подсистема netfilter. Два интерфейса управления: старый **iptables** и новый **nftables** (утилита `nft`). [Офиц.] В Ubuntu с 20.10 команды `iptables` по умолчанию работают поверх nftables (`iptables-nft`).
- **ufw** (Uncomplicated Firewall) — штатная надстройка Ubuntu; установлена, но **выключена** по умолчанию. Вызывает `iptables`/`ip6tables` (правила хранит в `/etc/ufw/*.rules`, загружает через `iptables-restore`).
- [Офиц.] Используйте **один** способ управления: либо ufw, либо «чистый» nftables, либо iptables + persistent. Смешивание даёт непредсказуемый результат.
- [Офиц., release notes 24.04] ufw и пакеты `iptables-persistent`/`netfilter-persistent` несовместимы: «The ufw tool conflicts with system configuration through iptables-persistent and netfilter-persistent»; «если ufw установить на Ubuntu 24.04 LTS+, он удалит iptables-persistent и netfilter-persistent». Обратное (установка `iptables-persistent` удаляет ufw) следует из того же конфликта пакетов [Практика]. В каком именно поле пакета (`Breaks`/`Conflicts`) и с какой стороны записан конфликт — ⚠ не подтверждено (на packages.ubuntu.com у ufw 0.36.2-6 такие поля не показаны); перед установкой смотрите, что `apt` собирается удалить.

### 7.2. ufw: включение, политики, состояние

```bash
sudo ufw status                    # Status: inactive | active + список правил
sudo ufw status verbose            # + политики по умолчанию, уровень журналирования
sudo ufw status numbered           # правила с номерами (для delete/insert)
sudo ufw show added                # правила, добавленные пользователем (видно даже при выключенном ufw)
sudo ufw show listening            # слушающие порты и какие правила на них действуют
sudo ufw show raw                  # итоговые правила iptables

sudo ufw default deny incoming     # политика: входящие запрещены (значение по умолчанию)
sudo ufw default allow outgoing    # исходящие разрешены (значение по умолчанию)
sudo ufw default deny routed       # транзитные (форвардинг)

sudo ufw allow OpenSSH             # СНАЧАЛА разрешить SSH (или: sudo ufw allow 22/tcp)
sudo ufw enable                    # включить сейчас и при загрузке (спросит подтверждение при работе по SSH)
sudo ufw --force enable            # без вопроса
sudo ufw disable                   # выключить
sudo ufw reload                    # перечитать правила
sudo ufw reset                     # выключить и удалить все правила (делает резервные копии .rules)
sudo ufw --dry-run allow 5432/tcp  # показать, что будет сделано, ничего не меняя
```

Политики: `allow` — пропустить; `deny` — молча отбросить (клиент ждёт таймаута); `reject` — отбросить с уведомлением (клиент сразу получает отказ).

### 7.3. ufw: правила

Простая форма — порт/протокол/имя службы из `/etc/services`:

```bash
sudo ufw allow 22/tcp
sudo ufw allow ssh
sudo ufw allow 80,443/tcp                 # список портов (с протоколом)
sudo ufw allow 1560:1591/tcp              # диапазон (с протоколом обязательно)
sudo ufw deny 23/tcp
sudo ufw reject 113/tcp
sudo ufw limit ssh                        # allow с ограничением частоты
```

Полная форма: `ufw [insert N | prepend] allow|deny|reject|limit [in|out] [on ИНТЕРФЕЙС] [log|log-all] [proto ПРОТОКОЛ] from АДРЕС [port ПОРТ | app ПРОФИЛЬ] to АДРЕС [port ПОРТ | app ПРОФИЛЬ] [comment 'текст']`:

```bash
sudo ufw allow from 192.168.1.0/24                                          # всё из подсети
sudo ufw allow from 192.168.1.10 to any port 22 proto tcp                   # SSH только с одного адреса
sudo ufw allow from 192.168.1.0/24 to any port 1540:1541 proto tcp comment '1C ragent/rmngr'
sudo ufw allow from 192.168.1.0/24 to any port 1560:1591 proto tcp comment '1C rphost'
sudo ufw allow from 192.168.1.0/24 to any port 1540,1541,1545,1560:1591 proto tcp   # одним правилом (не более 15 портов; диапазон считается за 2)
sudo ufw allow in on enp0s8 to any port 5432 proto tcp                      # только на конкретном интерфейсе
sudo ufw allow from 192.168.1.51 to 192.168.1.50 port 5432 proto tcp        # источник + адрес назначения
sudo ufw deny from 203.0.113.7                                              # заблокировать адрес
sudo ufw allow log from 192.168.1.0/24 to any port 22 proto tcp             # с журналированием новых соединений
sudo ufw deny out to any port 25 proto tcp                                  # исходящее правило
sudo ufw route allow in on enp0s8 out on enp0s3                             # транзит (нужен ip_forward)
```

`limit` [Офиц., ufw(8)]: соединения разрешены, но адрес блокируется, если с него было 6 и более попыток соединения за последние 30 секунд — простая защита SSH от перебора.

Ограничения синтаксиса [Офиц., ufw(8)]: в одном правиле нельзя указать более 15 портов, причём диапазон `A:B` считается за два (в примере выше — 1540, 1541, 1545 и диапазон = 5); для списка и диапазона портов обязателен протокол (`proto tcp` или суффикс `/tcp`). Комментарий задаётся `comment 'текст'` в конце правила; пустая строка `comment ''` удаляет комментарий; через `insert`/`prepend` комментарий существующего правила не обновить. Политики по умолчанию после установки: входящие — `deny`, транзит (routed) — `deny`, исходящие — `allow`.

### 7.4. ufw: порядок правил, вставка, удаление

- [Офиц.] Правила просматриваются по порядку, срабатывает **первое** совпавшее. Поэтому частные запреты должны стоять **выше** общих разрешений.
- Новое правило добавляется в конец. `ufw insert N …` — вставить на позицию N, `ufw prepend …` — в начало.
- Полный порядок обработки: `/etc/ufw/before.rules` (loopback, established/related, базовый ICMP, DHCP-клиент) → пользовательские правила (`/etc/ufw/user.rules`) → `/etc/ufw/after.rules` → политика по умолчанию. Благодаря `before.rules` ответы на исходящие соединения и ping работают без отдельных правил.

```bash
sudo ufw status numbered
sudo ufw insert 1 deny from 203.0.113.7        # запрет выше существующих allow
sudo ufw delete 3                              # удалить правило № 3 (номера после удаления сдвигаются!)
sudo ufw delete allow 80/tcp                   # удалить по тексту правила (удаляет и IPv4, и IPv6 варианты); по номеру удаляется только одно правило
sudo ufw delete allow from 192.168.1.0/24 to any port 1560:1591 proto tcp
```

При удалении нескольких правил по номерам идите от больших номеров к меньшим.

### 7.5. ufw: профили приложений

Профили — INI-файлы в `/etc/ufw/applications.d/` (их кладут пакеты: `OpenSSH`, `Apache`, `Apache Full`, `Apache Secure`, `Nginx Full`, `Samba` и др.).

```bash
sudo ufw app list
sudo ufw app info OpenSSH
sudo ufw app info Samba
sudo ufw allow Samba
sudo ufw allow from 192.168.1.0/24 to any app Samba
sudo ufw app update <имя>          # перечитать профиль после изменения файла
```

Собственный профиль для 1С — файл `/etc/ufw/applications.d/srv1cv8`. Требования к имени профиля (заголовку секции) [Офиц., исходный код ufw `applications.py`]: не `all`; не целое число (иначе путается с номером порта); первый символ — латинская буква или цифра, далее допустимы буквы, цифры, пробел, `_`, `-`, `.`, `+`; не длиннее 64 символов; имя не должно совпадать с именем службы из `/etc/services` — такие профили молча пропускаются. Файлы, начинающиеся с точки или оканчивающиеся на `~`, `.dpkg-new`, `.dpkg-old`, `.dpkg-dist`, не читаются. Поля `title`, `description`, `ports` обязательны и не должны быть пустыми.

```ini
[Srv1C]
title=1C:Enterprise server cluster
description=ragent 1540, rmngr 1541, rphost 1560-1591
ports=1540:1541/tcp|1560:1591/tcp

[Srv1C-RAS]
title=1C:Enterprise administration server
description=ras 1545
ports=1545/tcp
```

```bash
sudo ufw app list                                    # профили Srv1C и Srv1C-RAS должны появиться в списке
sudo ufw app info Srv1C
sudo ufw allow from 192.168.1.0/24 to any app Srv1C
sudo ufw allow from 192.168.1.10 to any app Srv1C-RAS
sudo ufw app update Srv1C                            # после изменения портов в файле профиля
```

Формат `ports=` [Офиц., ufw(8), раздел APPLICATION INTEGRATION; пример из man-страницы — `ports=12/udp|34|56,78:90/tcp`]: элементы через `|`, диапазон через `:`, список через запятую, протокол после `/` (для одиночного порта протокол необязателен, при списке/диапазоне — обязателен, иначе профиль отбрасывается как некорректный). Имя профиля с пробелом в командах берут в кавычки (`ufw allow 'Apache Full'`).

Особенность обновления [Офиц.]: изменение файла профиля **не меняет** уже созданные правила, пока не выполнена `sudo ufw app update <имя>` (или `all`). Команда `ufw app update --add-new <имя>` дополнительно создаёт правило для нового профиля согласно политике `ufw app default allow|deny|reject|skip` (по умолчанию `skip` — ничего не делать; `allow` man-страница называет рискованным).

### 7.6. ufw: журналирование и файлы конфигурации

```bash
sudo ufw logging on            # уровень low
sudo ufw logging medium        # off | low (по умолчанию) | medium | high | full
sudo tail -f /var/log/ufw.log  # если установлен rsyslog
sudo journalctl -k -g 'UFW' -f # то же из журнала ядра
```

Запись `[UFW BLOCK] IN=enp0s3 … SRC=192.168.1.20 DST=192.168.1.50 … PROTO=TCP SPT=51234 DPT=1560` означает: входящий пакет на порт 1560 отброшен — для него нет разрешающего правила. Уровни `high`/`full` порождают очень много записей и могут забить диск.

| Файл | Назначение |
|---|---|
| `/etc/default/ufw` | `IPV6=yes` (или `no`), политики `DEFAULT_INPUT_POLICY`, `DEFAULT_OUTPUT_POLICY`, `DEFAULT_FORWARD_POLICY` |
| `/etc/ufw/ufw.conf` | `ENABLED=yes` (или `no`), `LOGLEVEL=` |
| `/etc/ufw/before.rules`, `before6.rules` | правила до пользовательских (сюда же добавляют таблицу `*nat` для маскарадинга) |
| `/etc/ufw/user.rules`, `user6.rules` | правила, созданные командами `ufw` (вручную не править) |
| `/etc/ufw/after.rules`, `after6.rules` | правила после пользовательских |
| `/etc/ufw/sysctl.conf` | sysctl-параметры (`net/ipv4/ip_forward=1` для маршрутизации) |
| `/etc/ufw/applications.d/` | профили приложений |

### 7.7. ufw и Docker

[Офиц., docs.docker.com] «Docker and ufw use firewall rules in ways that make them incompatible with each other»: Docker направляет трафик к контейнерам в таблице `nat`, и пакеты минуют цепочки INPUT/OUTPUT, которыми управляет ufw. Итог: порт, опубликованный как `-p 5432:5432`, **доступен снаружи даже при `ufw deny 5432`**, а `ufw status` при этом выглядит «чисто».

Что делать:

- публиковать порт только на loopback: `-p 127.0.0.1:5432:5432` (в compose: `"127.0.0.1:5432:5432"`) — самый простой и надёжный способ;
- ограничивать доступ правилами в цепочке `DOCKER-USER` [Офиц., docs.docker.com/engine/network/firewall-iptables/]: это «место для пользовательских правил, которые обрабатываются раньше правил в цепочках `DOCKER-FORWARD` и `DOCKER`»; правила, добавленные в `FORWARD`, сработают уже **после** правил Docker, поэтому фильтровать нужно именно здесь. Примеры из документации (`ext_if` — внешний интерфейс):

  ```bash
  sudo iptables -I DOCKER-USER -i ext_if ! -s 192.168.1.0/24 -j DROP                      # пускать к контейнерам только свою подсеть
  sudo iptables -I DOCKER-USER -m state --state RELATED,ESTABLISHED -j ACCEPT             # ответы на уже принятые соединения — ставить ВЫШЕ правил DROP
  sudo iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdst 198.51.100.2 --ctorigdstport 80 -j ACCEPT   # отбор по ИСХОДНОМУ адресу/порту
  ```

  Пакеты попадают в `DOCKER-USER` уже **после DNAT**, поэтому обычные `-d`/`--dport` видят внутренний адрес и порт контейнера; чтобы отбирать по исходному (опубликованному) адресу и порту, нужен модуль `conntrack` (`--ctorigdst`, `--ctorigdstport`). Правила `DOCKER-USER` не сохраняются сами — их надо восстанавливать при загрузке (свой unit, `/etc/ufw/after.rules` и т. п.). [Офиц.] В новых версиях Docker кроме iptables поддерживается бэкенд nftables (параметр демона `firewall-backend`); Подтверждено 15.10.2026 (docs.docker.com, firewall-nftables.md): при бэкенде nftables цепочки `DOCKER-USER` нет — свои ограничения задают отдельными таблицами nftables. Публикация порта только на петлю (`-p 127.0.0.1:порт:порт`) надёжно не пускает к нему извне начиная с Docker Engine 28.0.0 (port-publishing.md);
- не отключать управление iptables в Docker (`"iptables": false`) без понимания последствий: по документации Docker это «не подходит большинству пользователей» и ломает сеть контейнеров;
- после настройки проверять доступность порта **снаружи** (`nmap`/`nc` с другой машины), а не по `ufw status`.

### 7.8. Типовой набор правил: сервер 1С + PostgreSQL

**Вариант А — всё на одной машине** (сервер 1С, PostgreSQL, Apache); клиенты в сети `192.168.1.0/24`:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp          comment 'SSH'
sudo ufw allow from 192.168.1.0/24 to any port 1540:1541 proto tcp   comment '1C ragent, rmngr'
sudo ufw allow from 192.168.1.0/24 to any port 1560:1591 proto tcp   comment '1C rphost'
sudo ufw allow from 192.168.1.10   to any port 1545 proto tcp        comment '1C ras: only admin PC'
sudo ufw allow 80,443/tcp                                            comment 'web publication'
# PostgreSQL на этой же машине: порт 5432 НЕ открываем (listen_addresses = 'localhost')
sudo ufw enable
sudo ufw status verbose
```

**Вариант Б — PostgreSQL на отдельном сервере.** На сервере СУБД:

```bash
sudo ufw default deny incoming
sudo ufw allow from 192.168.1.10 to any port 22 proto tcp     comment 'SSH admin'
sudo ufw allow from 192.168.1.50 to any port 5432 proto tcp   comment 'PostgreSQL from 1C server'
sudo ufw enable
```

Плюс в PostgreSQL: `listen_addresses = '192.168.1.60,localhost'` (или `'*'`) в `postgresql.conf` и строка в `pg_hba.conf` вида `host all all 192.168.1.50/32 scram-sha-256`. Firewall и `pg_hba.conf` — два независимых рубежа, нужны оба.

Проверка с клиента: `nmap -p 22,80,443,1540,1541,1545,1560-1591,5432 192.168.1.50` — 1540/1541 `open`; из диапазона 1560–1591 `open` только те порты, на которых сейчас работают процессы, остальные `closed` (а не `filtered`); 5432 в варианте А — `filtered`.

### 7.9. Основы nftables

```bash
sudo nft list ruleset                 # все таблицы, цепочки и правила (сюда же попадают правила ufw/iptables-nft/Docker)
sudo nft list tables
sudo nft -c -f /etc/nftables.conf     # проверить файл, не применяя
sudo nft -f /etc/nftables.conf        # применить
sudo systemctl enable --now nftables.service   # загружать /etc/nftables.conf при старте (по умолчанию служба выключена)
sudo systemctl reload nftables.service
```

[Офиц.] Изменения, сделанные командой `nft`, не переживают перезагрузку, пока не записаны в `/etc/nftables.conf`; файл по умолчанию — «пустышка» (таблица `inet filter` с пустыми цепочками). Загрузка файла атомарна, но правила **добавляются** к существующим, поэтому файл начинают с `flush ruleset`.

Минимальный `/etc/nftables.conf` для сервера 1С + PostgreSQL (использовать **вместо** ufw, не вместе с ним):

```
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority filter; policy drop;
        iif "lo" accept
        ct state established,related accept
        ct state invalid drop
        meta l4proto { icmp, ipv6-icmp } accept
        ip saddr 192.168.1.0/24 tcp dport 22 accept
        ip saddr 192.168.1.0/24 tcp dport { 1540, 1541, 1560-1591 } accept
        ip saddr 192.168.1.10 tcp dport 1545 accept
        tcp dport { 80, 443 } accept
        ip saddr 192.168.1.51 tcp dport 5432 accept
    }
    chain forward {
        type filter hook forward priority filter; policy drop;
    }
    chain output {
        type filter hook output priority filter; policy accept;
    }
}
```

Внимание: `flush ruleset` удаляет и правила Docker/libvirt/ufw — на хостах с Docker так делать нельзя.

### 7.10. Основы iptables

```bash
sudo iptables -L -n -v --line-numbers        # таблица filter: цепочки INPUT/FORWARD/OUTPUT, счётчики, номера
sudo iptables -S                             # правила в виде команд
sudo iptables -t nat -L -n -v                # таблица nat (проброс портов, маскарадинг, Docker)
sudo ip6tables -L -n -v                      # IPv6
iptables -V                                  # версия и бэкенд: (nf_tables) или (legacy)

sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT                          # добавить в конец
sudo iptables -I INPUT 1 -s 192.168.1.0/24 -p tcp --dport 1541 -j ACCEPT    # вставить первой
sudo iptables -A INPUT -p tcp -m multiport --dports 1540,1541,1560:1591 -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -D INPUT 3                     # удалить правило № 3
sudo iptables -P INPUT DROP                  # политика цепочки (ОСТОРОЖНО по SSH: сначала разрешающие правила)
```

Сохранение (только если **не** используется ufw):

```bash
sudo apt install iptables-persistent         # тянет netfilter-persistent; в 24.04+ удалит ufw
sudo netfilter-persistent save               # записать текущие правила в /etc/iptables/rules.v4 и rules.v6
sudo netfilter-persistent reload             # загрузить из файлов
sudo iptables-save > ~/rules.v4.bak          # ручной дамп
sudo iptables-restore < ~/rules.v4.bak       # ручное восстановление
```

Правила iptables без сохранения пропадают при перезагрузке. При включённом ufw вручную `iptables` не правят — используйте команды `ufw` или файлы `before.rules`/`after.rules`.

## 8. SSH

### 8.1. Клиент ssh

```bash
ssh admin@192.168.1.50                 # подключиться (порт 22)
ssh -p 2222 admin@srv1c                # другой порт
ssh -i ~/.ssh/id_ed25519 admin@srv1c   # конкретный ключ
ssh admin@srv1c 'uptime; df -h /'      # выполнить команду и выйти
ssh -t admin@srv1c 'sudo systemctl restart apache2'   # -t: выделить терминал (для sudo с паролем)
ssh -v admin@srv1c                     # отладка (-vv, -vvv подробнее): какой ключ предложен, почему отказ
ssh -J admin@gate.corp.local admin@192.168.1.50       # через промежуточный узел (jump host)
ssh -o StrictHostKeyChecking=accept-new admin@srv1c   # разовая опция из ssh_config
ssh -G srv1c | less                    # показать итоговую конфигурацию клиента для узла
```

Другие флаги: `-N` не запускать команду (только туннели), `-f` уйти в фон, `-C` сжатие, `-A` проброс агента (только на доверенные узлы), `-X` проброс X11, `-4`/`-6`, `-F файл` альтернативный конфиг, `-q` тихо.

Первое подключение: клиент показывает отпечаток ключа сервера и после `yes` записывает его в `~/.ssh/known_hosts`. Если сервер переустановлен и ключ сменился — ошибка `REMOTE HOST IDENTIFICATION HAS CHANGED`; после проверки причины: `ssh-keygen -R srv1c` (и `ssh-keygen -R 192.168.1.50`). Отпечатки сервера: `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`.

Управляющие последовательности в сессии (в начале строки): `~.` — оборвать зависшую сессию, `~?` — справка.

### 8.2. Туннели (проброс портов)

| Вид | Синтаксис | Смысл |
|---|---|---|
| Локальный `-L` | `ssh -L [bind:]лок_порт:узел:порт user@ssh_сервер` | порт на **вашей** машине ведёт к `узел:порт`, как его видит SSH-сервер |
| Обратный `-R` | `ssh -R [bind:]удал_порт:узел:порт user@ssh_сервер` | порт на **SSH-сервере** ведёт к `узел:порт`, как его видит ваша машина |
| Динамический `-D` | `ssh -D 1080 user@ssh_сервер` | локальный SOCKS5-прокси; трафик выходит с SSH-сервера |

```bash
# PostgreSQL, слушающий только localhost на сервере, доступен на клиенте как localhost:15432
ssh -N -L 15432:127.0.0.1:5432 admin@srv1c
psql -h 127.0.0.1 -p 15432 -U postgres

# веб-публикация 1С с сервера на http://localhost:8080/base/
ssh -N -L 8080:127.0.0.1:80 admin@srv1c

# сервер администрирования ras (1545) — для rac/консолей с рабочего места администратора
ssh -N -L 1545:127.0.0.1:1545 admin@srv1c

# узел за SSH-сервером (СУБД на другой машине внутренней сети)
ssh -N -L 15432:192.168.1.60:5432 admin@srv1c

# обратный туннель: дать серверу доступ к службе на вашем ПК (порт 3128)
ssh -N -R 3128:127.0.0.1:3128 admin@srv1c

# SOCKS-прокси и запрос через него
ssh -N -D 1080 admin@srv1c
curl --socks5-hostname 127.0.0.1:1080 http://internal.corp.local/
```

Добавьте `-f` для ухода в фон; для автоподдержания туннеля — `autossh` или unit systemd. На сервере проброс регулируют `AllowTcpForwarding` и `GatewayPorts` (чтобы `-R` слушал не только на loopback).

Ограничение для 1С [Практика]: «родное» клиент-серверное подключение 1С через SSH-туннель без ухищрений не работает — клиенту нужны сразу 1541 и весь диапазон 1560–1591, причём кластер возвращает имя сервера, а не `localhost`. Для удалённого доступа к 1С используйте VPN или веб-публикацию (80/443), а туннели — для SSH, PostgreSQL, `ras`, HTTP.

### 8.3. Ключи: ssh-keygen, ssh-copy-id, ssh-agent

```bash
ssh-keygen -t ed25519 -C "admin@workpc"            # создать пару; файлы ~/.ssh/id_ed25519 и id_ed25519.pub
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/id_srv1c -C "srv1c admin"   # отдельный файл, усиленная защита парольной фразы
ssh-keygen -t rsa -b 4096                          # RSA — только для совместимости со старыми системами
ssh-keygen -p -f ~/.ssh/id_ed25519                 # сменить/задать парольную фразу
ssh-keygen -y -f ~/.ssh/id_ed25519 > ~/.ssh/id_ed25519.pub   # восстановить публичный ключ из приватного
ssh-keygen -lf ~/.ssh/id_ed25519.pub               # отпечаток
ssh-keygen -R srv1c                                # удалить узел из known_hosts

ssh-copy-id admin@srv1c                            # установить публичный ключ на сервер (в ~/.ssh/authorized_keys)
ssh-copy-id -i ~/.ssh/id_srv1c.pub -p 2222 admin@srv1c
```

[Офиц., Ubuntu Server; release notes OpenSSH 9.5 от 04.10.2023: «ssh-keygen(1): generate Ed25519 keys by default»] Рекомендуемый тип — `ed25519`. В OpenSSH 9.5+ (Ubuntu 24.04/26.04) `ssh-keygen` без `-t` создаёт ed25519; в 22.04 (OpenSSH 8.9) — RSA. DSA-ключи в 26.04 не поддерживаются вовсе (поддержка DSA удалена в OpenSSH 10.0): если на старых рабочих местах остались ключи `id_dsa`, после обновления сервера до 26.04 вход по ним перестанет работать — заранее замените их на ed25519.

Права, при нарушении которых sshd молча игнорирует ключ (`StrictModes yes`): домашний каталог и `~/.ssh` не должны быть доступны на запись группе/остальным; `~/.ssh` — `700`, `~/.ssh/authorized_keys` — `600`, приватный ключ — `600`:

```bash
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

Агент хранит расшифрованные ключи в памяти, чтобы не вводить парольную фразу каждый раз:

```bash
eval "$(ssh-agent -s)"        # запустить агент в текущей оболочке
ssh-add ~/.ssh/id_ed25519     # добавить ключ (спросит парольную фразу один раз)
ssh-add -l                    # список ключей в агенте
ssh-add -t 3600 ~/.ssh/id_srv1c   # добавить на час
ssh-add -D                    # удалить все
```

### 8.4. ~/.ssh/config

```
# ~/.ssh/config  (права 600)
Host *
    ServerAliveInterval 30
    ServerAliveCountMax 3
    AddKeysToAgent yes

Host srv1c
    HostName 192.168.1.50
    User admin
    Port 22
    IdentityFile ~/.ssh/id_srv1c
    IdentitiesOnly yes

Host pg
    HostName 192.168.1.60
    User admin
    ProxyJump srv1c
    LocalForward 15432 127.0.0.1:5432

Host gate
    HostName gate.corp.local
    User admin
    Port 2222
```

После этого `ssh srv1c`, `scp file srv1c:/tmp/`, `rsync … srv1c:…`, `ssh pg` (через jump host и сразу с туннелем). `ServerAliveInterval` защищает от обрыва простаивающих сессий на NAT/файрволах. Мультиплексирование (одно TCP-соединение на несколько сессий): `ControlMaster auto`, `ControlPath ~/.ssh/cm-%r@%h:%p`, `ControlPersist 10m`.

### 8.5. Копирование файлов: scp, sftp, rsync

```bash
scp file.dt admin@srv1c:/tmp/                       # файл на сервер
scp admin@srv1c:/var/log/syslog .                   # файл с сервера
scp -r ./distr admin@srv1c:/opt/                    # каталог рекурсивно
scp -P 2222 -p -C backup.tar.gz admin@srv1c:/backup/   # -P порт (заглавная!), -p сохранить времена/права, -C сжатие
scp -J gate file admin@192.168.1.50:/tmp/           # через jump host
```

[Офиц., release notes OpenSSH 9.0 от 08.04.2022] Начиная с OpenSSH 9.0 (Ubuntu 24.04/26.04) `scp` по умолчанию использует протокол SFTP; `-O` включает старый протокол scp/rcp (для очень старых серверов или серверов без подсистемы sftp). В 22.04 (OpenSSH 8.9) `scp` ещё работает по старому протоколу.

```bash
sftp admin@srv1c            # интерактивно; sftp -P 2222 ...
# команды внутри: ls / lls, cd / lcd, pwd / lpwd, get файл, put файл, get -r каталог, put -r каталог, mkdir, rm, bye
```

```bash
rsync -avz --progress ./distr/ admin@srv1c:/opt/distr/        # синхронизация поверх SSH
rsync -avP -e 'ssh -p 2222' /backup/ admin@nas:/backups/1c/   # нестандартный порт; -P = --partial --progress
rsync -av --delete /var/backups/pg/ admin@nas:/backups/pg/    # зеркало (удалять лишнее на приёмнике)
rsync -avn --delete src/ dst/                                 # -n: пробный прогон, показать что изменится
rsync -av --exclude='*.tmp' --bwlimit=20000 src/ admin@srv1c:dst/   # исключения, лимит ~20 МБ/с
```

`-a` — архивный режим (рекурсия, права, времена, владельцы, ссылки), `-v` подробно, `-z` сжатие. Слэш в конце источника важен: `src/` — копировать **содержимое**, `src` — сам каталог. rsync должен быть установлен на обеих сторонах.

### 8.6. Сервер: установка, файлы, служба

```bash
sudo apt install openssh-server
systemctl status ssh                   # служба в Ubuntu/Debian называется ssh (sshd.service — алиас только с 26.04)
sudo ss -tlnp | grep ':22'
sudo journalctl -u ssh -f              # журнал входов и ошибок
sudo sshd -t                           # проверить синтаксис конфигурации; молчание = ошибок нет
sudo sshd -T | less                    # показать ИТОГОВЫЕ действующие значения всех параметров
sudo sshd -T | grep -iE 'port|permitrootlogin|passwordauthentication|pubkeyauthentication|allowusers'
sudo systemctl restart ssh             # применить изменения (существующие сессии не обрываются)
sudo systemctl reload ssh
```

Файлы:

- `/etc/ssh/sshd_config` — основной файл сервера. [Офиц.] В Ubuntu он начинается со строки `Include /etc/ssh/sshd_config.d/*.conf`.
- `/etc/ssh/sshd_config.d/*.conf` — drop-in-файлы. Для большинства директив sshd берёт **первое** встреченное значение, поэтому значения из drop-in **перекрывают** основной файл, а среди drop-in побеждает файл, идущий **раньше по алфавиту**.
- `/etc/ssh/ssh_config`, `/etc/ssh/ssh_config.d/` — конфигурация **клиента** (не путать).
- `/etc/ssh/ssh_host_*_key(.pub)` — ключи узла.
- `~/.ssh/authorized_keys` — публичные ключи, которым разрешён вход под этим пользователем.

Подводный камень: cloud-init создаёт `/etc/ssh/sshd_config.d/50-cloud-init.conf` (права `600`) со строкой `PasswordAuthentication yes` или `no`. [Офиц., исходный код cloud-init `cloudinit/ssh_util.py` и описание модуля Set Passwords] Это происходит, когда в конфигурации cloud-init задан ключ `ssh_pwauth` (`true` — включить вход по паролю, `false` — `PasswordAuthentication no`, не задан — ничего не менять), а основной `sshd_config` содержит `Include /etc/ssh/sshd_config.d/*.conf`. Установщик Ubuntu Server задаёт `ssh_pwauth` по ответу на вопрос «Allow password authentication over SSH», поэтому на свежей системе 22.04+/24.04/26.04 этот файл обычно **есть** [Практика]. В облачных образах Ubuntu дополнительно встречается `60-cloudimg-settings.conf` с `PasswordAuthentication no` (⚠ не подтверждено первоисточником — имя файла по сообщениям пользователей). Ваш файл должен сортироваться **раньше** (например, `10-hardening.conf`), иначе настройка не подействует: побеждает первое встреченное значение. Всегда проверяйте результат через `sudo sshd -T | grep -i passwordauthentication` и смотрите, что уже лежит в каталоге: `sudo grep -r . /etc/ssh/sshd_config.d/`.

### 8.7. Основные директивы sshd_config

| Директива | По умолчанию | Комментарий |
|---|---|---|
| `Port` | 22 | можно несколько строк `Port`; при сокет-активации см. 8.8 |
| `AddressFamily` | `any` | `inet` — только IPv4, `inet6` — только IPv6 |
| `ListenAddress` | все адреса | например `ListenAddress 192.168.1.50` |
| `PermitRootLogin` | `prohibit-password` | `yes` / `prohibit-password` (только по ключу) / `forced-commands-only` / `no`. В Ubuntu у root нет пароля — ставьте `no` |
| `PubkeyAuthentication` | `yes` | вход по ключам |
| `PasswordAuthentication` | `yes` | после настройки ключей — `no` |
| `KbdInteractiveAuthentication` | в Ubuntu `no` | оставить `no`, иначе пароль через PAM останется возможен |
| `PermitEmptyPasswords` | `no` | |
| `AllowUsers` / `AllowGroups` | не заданы (разрешено всем) | белый список: `AllowUsers admin backup@192.168.1.*` |
| `DenyUsers` / `DenyGroups` | не заданы | запреты обрабатываются раньше разрешений |
| `MaxAuthTries` | 6 | попыток аутентификации на соединение |
| `LoginGraceTime` | 120 | секунд на вход |
| `ClientAliveInterval` | 0 (выкл.) | через сколько секунд тишины сервер шлёт проверку клиенту |
| `ClientAliveCountMax` | 3 | сколько проверок без ответа до разрыва; при `Interval 300` и `CountMax 2` «мёртвая» сессия закрывается через ~10 мин |
| `X11Forwarding` | в Ubuntu `yes` | на сервере без GUI — `no` |
| `AllowTcpForwarding` | `yes` | `no`/`local`/`remote` — ограничить туннели |
| `UsePAM` | в Ubuntu `yes` | не отключать |
| `AuthorizedKeysFile` | `.ssh/authorized_keys .ssh/authorized_keys2` | |
| `Subsystem sftp` | `/usr/lib/openssh/sftp-server` | |
| `Banner`, `DebianBanner` | нет / `yes` | баннер до входа; `DebianBanner no` скрывает суффикс дистрибутива в строке версии |
| `PerSourcePenalties` | включено (OpenSSH 9.8+, т. е. Ubuntu 26.04) | встроенные временные блокировки адресов-источников после неудачных попыток |
| `MaxStartups` | `10:30:100` | ограничение числа неаутентифицированных соединений (`start:rate:full`) |
| `Match User/Group/Address/Host/LocalAddress/LocalPort/RDomain/Version …`, `Match All`, `Match Invalid-User` (26.04) | — | условный блок до конца файла или следующего `Match` |

[Офиц.] Значения по умолчанию — sshd_config(5) для 26.04 (сверено 10.10.2026): upstream-умолчания `KbdInteractiveAuthentication yes`, `X11Forwarding no`, `UsePAM no`, а пакет Debian/Ubuntu в поставляемом `sshd_config` задаёт: `Include /etc/ssh/sshd_config.d/*.conf`, `KbdInteractiveAuthentication no`, `X11Forwarding yes`, `PrintMotd no`, `AcceptEnv LANG LC_* COLORTERM NO_COLOR`, `Subsystem sftp /usr/lib/openssh/sftp-server`, `UsePAM yes`. «Для каждого ключевого слова используется первое полученное значение»; `DenyUsers` проверяется раньше `AllowUsers`, `DenyGroups` — раньше `AllowGroups`. Параметры `PerSourcePenalties` по умолчанию: `authfail` 5 с, `noauth` 1 с, `crash` 90 с, `grace-exceeded` 10 с, `refuseconnection` 10 с, минимальный порог `min` 15 с, максимум `max` 10 мин; исключения — `PerSourcePenaltyExemptList` (сюда стоит внести адреса мониторинга и администраторов).

Пример усиления — `/etc/ssh/sshd_config.d/10-hardening.conf`:

```
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AllowUsers admin
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no

# пароль разрешён только из локальной сети (пример условного блока)
Match Address 192.168.1.0/24
    PasswordAuthentication yes
```

Безопасная последовательность: (1) установить ключ и проверить вход по нему; (2) создать drop-in; (3) `sudo sshd -t`; (4) `sudo systemctl restart ssh`; (5) **не закрывая** текущую сессию, открыть вторую и убедиться, что вход работает; (6) держать под рукой консоль ВМ на случай ошибки.

### 8.8. Сокет-активация ssh.socket (Ubuntu 22.10+, включая 24.04 и 26.04)

[Офиц., Ubuntu Discourse, release notes 24.04] Начиная с `openssh-server 1:9.0p1-1ubuntu1` (Ubuntu 22.10) sshd по умолчанию не висит постоянно: порт 22 слушает systemd (`ssh.socket`) и запускает `ssh.service` при первом входящем соединении. Для администратора главное следствие — меняется порядок работы с портом и адресом прослушивания.

| Версия | Поведение |
|---|---|
| 22.04 | классика: `ssh.service` запускается при загрузке и сам слушает порт; `Port` в `sshd_config` + `systemctl restart ssh` |
| 22.10–23.10 | сокет-активация; при обновлении `Port`/`ListenAddress` переносились в `/etc/systemd/system/ssh.socket.d/addresses.conf` |
| 24.04, 26.04 | сокет-активация; генератор `sshd-socket-generator` при каждом `daemon-reload` читает `Port`/`ListenAddress` из `sshd_config` и `sshd_config.d/` и формирует `ListenStream=` для `ssh.socket` |

Проверка, какой режим у вас:

```bash
systemctl is-enabled ssh.socket ssh.service
systemctl status ssh.socket          # active (listening) => сокет-активация
systemctl cat ssh.socket             # юнит и drop-in с ListenStream=
sudo ss -tlnp | grep -E ':22\b'      # при сокет-активации порт держит systemd (pid=1)
```

**Смена порта в 24.04/26.04** (например, на 2222):

```bash
echo 'Port 2222' | sudo tee /etc/ssh/sshd_config.d/05-port.conf
sudo sshd -t
sudo ufw allow 2222/tcp                 # СНАЧАЛА открыть новый порт в firewall
sudo systemctl daemon-reload            # перегенерировать настройки ssh.socket
sudo systemctl restart ssh.socket       # ssh.service отдельно перезапускать не нужно
sudo ss -tlnp | grep -E ':(22|2222)\b'  # убедиться, что слушается новый порт
# из второго окна: ssh -p 2222 admin@srv1c ; после проверки: sudo ufw delete allow OpenSSH
```

Одного `systemctl restart ssh` (ssh.service) в этом режиме **недостаточно** — порт принадлежит сокету. [Офиц., Launchpad #2069041 «Changing Port in sshd_config requires calling systemctl daemon-reload»]: сопровождающий пакета подтвердил, что без `daemon-reload` не обойтись; «исправление» (noble, `1:9.6p1-3ubuntu13.12`, июнь 2025) лишь добавило в поставляемый `sshd_config` комментарий с этими двумя командами. Директива `Port` накопительная: если в основном `sshd_config` есть незакомментированная строка `Port 22`, слушаться будут оба порта — закомментируйте её.

Альтернатива (работает в любой версии с сокет-активацией) — override сокета: `sudo systemctl edit ssh.socket` и в редакторе:

```ini
[Socket]
ListenStream=
ListenStream=2222
```

Пустая строка `ListenStream=` обязательна — она сбрасывает список, иначе sshd будет слушать и 22, и 2222. Затем `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket`. Не смешивайте оба способа.

**Вернуться к классической службе (24.04+)** — по README пакета openssh-server:

```bash
sudo mkdir -p /etc/systemd/system-generators/
sudo ln -s /dev/null /etc/systemd/system-generators/sshd-socket-generator   # замаскировать генератор
sudo systemctl daemon-reload
sudo systemctl disable --now ssh.socket
sudo systemctl enable --now ssh.service
```

Для 22.10–23.10 процедура другая: `systemctl disable --now ssh.socket`, удалить `/etc/systemd/system/ssh.service.d/00-socket.conf` и `/etc/systemd/system/ssh.socket.d/addresses.conf`, `systemctl daemon-reload`, `systemctl enable --now ssh.service`. Выполняйте переключение с консоли ВМ, а не из единственной SSH-сессии.

Известные особенности: при нескольких `ListenAddress` в 22.10–23.10 миграция на сокет не выполнялась (такие системы оставались на классической службе); генератор не учитывает `AddressFamily` (Launchpad #2103633, помечен дубликатом #2080216 «sshd cannot bind to IPv4 interfaces»; на 10.2026 статус исправления не проверен) — при `AddressFamily inet` сокет всё равно может слушать IPv6 (`*:порт`). Если нужен строго IPv4 — задавайте `ListenAddress <IPv4-адрес>` явно или отключайте сокет-активацию.

### 8.9. fail2ban для SSH

fail2ban читает журнал, находит неудачные попытки входа и временно блокирует адрес правилом firewall.

```bash
sudo apt install fail2ban
sudo systemctl enable --now fail2ban
sudo fail2ban-client status              # список jail'ов
sudo fail2ban-client status sshd         # статистика и заблокированные адреса
sudo fail2ban-client set sshd unbanip 192.168.1.20   # разблокировать
sudo fail2ban-client set sshd banip 203.0.113.7      # заблокировать вручную
sudo fail2ban-client reload
sudo tail -f /var/log/fail2ban.log
```

- Версии пакета: 22.04 — 0.11.2-6, 24.04 — 1.0.2-3 (в обновлениях 1.0.2-3ubuntu0.1), 26.04 — 1.1.0-9 [Офиц., packages.ubuntu.com].
- В Debian/Ubuntu jail `sshd` включён сразу после установки файлом `/etc/fail2ban/jail.d/defaults-debian.conf`. [Офиц., changelog пакета Debian] Начиная с версии пакета **1.0.2-3** (т. е. в Ubuntu 24.04) в этот файл добавлены `banaction = nftables` и `backend = systemd`; в 1.1.0-1 в нём оставлен только `[sshd] enabled = true`, а в 1.1.0-3 nftables и (для части jail'ов) systemd-бэкенд возвращены — т. е. в 26.04 (1.1.0-9) блокировка тоже идёт через nftables. В 22.04 (0.11.2-6) действуют значения из `jail.conf`: `banaction = iptables-multiport`, чтение `/var/log/auth.log`. Точное содержимое на своей системе: `cat /etc/fail2ban/jail.d/defaults-debian.conf` и `sudo fail2ban-client get sshd actions`.
- Свои настройки — только в `/etc/fail2ban/jail.local` или `/etc/fail2ban/jail.d/*.local` (файлы `.conf` перезаписываются обновлениями; `.local` читаются после `.conf`):

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1 192.168.1.0/24

[sshd]
enabled = true
port    = ssh
# если SSH на нестандартном порту:  port = 2222
# блокировать через ufw вместо nftables/iptables:  banaction = ufw
```

Замечания: не блокируйте собственную сеть (`ignoreip`); при входе только по ключам (`PasswordAuthentication no`) польза fail2ban для SSH — в основном снижение шума в журнале; более простые альтернативы — `sudo ufw limit ssh` и встроенный в OpenSSH 9.8+ `PerSourcePenalties` (Ubuntu 26.04). [Офиц., release notes OpenSSH 9.8] Начиная с OpenSSH 9.8 сервер разделён на слушатель `sshd` и посеансовый `sshd-session`, и «часть сообщений журнала помечается как исходящая от процесса `sshd-session`, а не `sshd`» — старые фильтры fail2ban перестают их находить. Исправление фильтра в основной ветке fail2ban принято 03.07.2024 (PR «Adjust sshd.conf filter for OpenSSH 9.8»), т. е. **после** выхода fail2ban 1.1.0; сам номер «1.1.0» наличия исправления не гарантирует. В пакете Debian/Ubuntu оно появилось в **1.1.0-6** («Adjust the ssh configuration to work with openssh 9.8»), так что в Ubuntu 26.04 (1.1.0-9 + OpenSSH 10.2) фильтр рабочий. В 22.04 и 24.04 OpenSSH старше 9.8, и проблемы нет. Если ставите fail2ban не из репозитория Ubuntu рядом с OpenSSH ≥ 9.8 — проверьте: `sudo fail2ban-regex systemd-journal /etc/fail2ban/filter.d/sshd.conf` (покажет, сколько строк журнала совпало с фильтром) или `sudo fail2ban-client status sshd` после заведомо неудачной попытки входа.

## 9. Работа с Windows-хоста

### 9.1. Встроенный OpenSSH в Windows

[Офиц., Microsoft Learn] Компоненты OpenSSH доступны начиная с Windows 10 (сборка 1809) и Windows Server 2019; в Windows 10/11 клиент обычно уже установлен. Проверка и установка (PowerShell от имени администратора):

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

Дальше в обычном PowerShell или cmd работают те же команды, что и в Linux:

```powershell
ssh admin@192.168.1.50
ssh -p 2222 -i $env:USERPROFILE\.ssh\id_ed25519 admin@srv1c
scp .\distr\server64.zip admin@srv1c:/tmp/      # дистрибутив сервера 1С на сервер
scp -r admin@srv1c:/var/log/apache2 .\logs\
sftp admin@srv1c
ssh -N -L 15432:127.0.0.1:5432 admin@srv1c      # туннель к PostgreSQL; pgAdmin -> localhost:15432
ssh-keygen -t ed25519 -C "admin@winpc"
```

- Ключи и настройки лежат в `C:\Users\<пользователь>\.ssh\` (`id_ed25519`, `id_ed25519.pub`, `known_hosts`, `config` — формат тот же, что в п. 8.4).
- [Офиц.] Если алгоритм не указан, `ssh-keygen` в актуальных Windows создаёт Ed25519.
- `ssh-copy-id` в Windows **нет**. Установка ключа на Linux-сервер одной командой:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | ssh admin@srv1c "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

(в cmd: `type %USERPROFILE%\.ssh\id_ed25519.pub | ssh admin@srv1c "…"`). Либо скопировать `.pub` через `scp` и дописать в `authorized_keys` на сервере.

- Агент ключей в Windows — служба, по умолчанию **отключена** [Офиц.]:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic    # от администратора
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519
ssh-add -l
```

Диагностика с Windows:

```powershell
Test-NetConnection srv1c -Port 1541          # TcpTestSucceeded : True/False (алиас tnc)
Test-NetConnection 192.168.1.50 -Port 5432
Resolve-DnsName srv1c                        # как имя разрешает Windows (hosts, кэш, DNS, при неудаче LLMNR/NetBIOS)
Resolve-DnsName srv1c -DnsOnly -NoHostsFile  # что отвечает именно DNS-сервер (без hosts)
ping srv1c ; tracert -d srv1c ; nslookup srv1c
ipconfig /all ; ipconfig /flushdns
curl.exe -I http://srv1c/base/               # именно curl.exe: в Windows PowerShell 5.1 «curl» — алиас Invoke-WebRequest
Get-NetTCPConnection -State Listen | Sort-Object LocalPort    # что слушает сама Windows
```

Файл hosts Windows: `C:\Windows\System32\drivers\etc\hosts` (редактировать от администратора), строка `192.168.1.50  srv1c.corp.local srv1c`. `nslookup` файл hosts **не учитывает** (он опрашивает DNS-сервер напрямую) — запись из hosts проверяйте через `ping srv1c` или `Resolve-DnsName srv1c`. [Офиц., Microsoft Learn, Resolve-DnsName] У `Resolve-DnsName` есть ключи `-NoHostsFile` («пропустить файл hosts»), `-DnsOnly` («только протокол DNS»), `-CacheOnly`, `-Server <адрес>` — т. е. **без** этих ключей командлет hosts-файл учитывает.

### 9.2. PuTTY, WinSCP, Windows Terminal

- **PuTTY** — SSH-клиент с GUI. В комплекте: `plink.exe` (консольный ssh), `pscp.exe`/`psftp.exe` (копирование), `puttygen.exe` (ключи), `pageant.exe` (агент). PuTTY использует свой формат ключей `.ppk`: в PuTTYgen `Conversions → Import key` загружает OpenSSH-ключ, `Save private key` сохраняет `.ppk`; `Conversions → Export OpenSSH key` — обратно. Туннели: `Connection → SSH → Tunnels` (Source port / Destination, Local/Remote/Dynamic → Add). Keepalive: `Connection → Seconds between keepalives` (например, 30). Кодировка: `Window → Translation → UTF-8`.
- **WinSCP** — файловый менеджер поверх SFTP/SCP: перенос дистрибутивов 1С, выгрузок `.dt`, бэкапов, логов. Понимает сессии и ключи PuTTY (`.ppk`), умеет конвертировать OpenSSH-ключи. Для доступа к системным файлам при входе обычным пользователем: `Advanced → Environment → SFTP → SFTP server:` `sudo /usr/lib/openssh/sftp-server` (требует `sudo` без пароля для этой команды) [Практика].
- **Windows Terminal** — удобная оболочка для встроенного `ssh`: профиль с командной строкой `ssh admin@srv1c` (Settings → Add a new profile → Command line), вкладки, UTF-8 без настроек. Вставка — `Ctrl+Shift+V` или правый клик.
- VS Code с расширением Remote-SSH использует тот же `C:\Users\<пользователь>\.ssh\config`.

### 9.3. Сетевые режимы ВМ и проброс портов

| Режим адаптера ВМ | Что получает ВМ | Пригодность для сервера 1С |
|---|---|---|
| **Bridged / мост / External switch** | адрес в той же сети, что и хост (от DHCP сети или статика) | лучший вариант: клиенты ходят напрямую, никаких пробросов; нужен постоянный IP |
| **NAT** | частный адрес за хостом; ВМ видит интернет, снаружи её не видно | только с пробросом портов; для 1С неудобно (много портов + проблема имени) |
| **Host-only / Internal** | сеть только между хостом и ВМ | годится, если клиенты 1С запускаются только на самом Windows-хосте; часто вторым адаптером вместе с NAT |

Проброс портов для NAT:

```powershell
# VirtualBox: правило NAT «имя,протокол,адрес_хоста,порт_хоста,адрес_гостя,порт_гостя»
VBoxManage modifyvm "ubuntu-1c" --natpf1 "ssh,tcp,,2222,,22"          # ВМ выключена
VBoxManage controlvm "ubuntu-1c" natpf1 "pg,tcp,127.0.0.1,15432,,5432" # ВМ запущена
VBoxManage controlvm "ubuntu-1c" natpf1 delete ssh
# затем: ssh -p 2222 admin@127.0.0.1
```

[Офиц., руководство Oracle VirtualBox 7.1, «Configuring Port Forwarding with NAT» и справка VBoxManage] Формат правила: `[имя],tcp|udp,[IP хоста],порт хоста,[IP гостя],порт гостя`; цифра после `natpf` — номер сетевого адаптера ВМ. В VirtualBox 7.x опция `modifyvm` в справке пишется как `--nat-pf1` (`VBoxManage modifyvm "VM name" --nat-pf1 "guestssh,tcp,,2222,,22"`), прежнее написание `--natpf1` по-прежнему используется в примерах самого руководства (`--natpf1 delete "guestssh"`); для работающей ВМ — `controlvm … natpf1 …` и `controlvm … natpf1 delete <имя>`. Если гость использует статический адрес не от встроенного DHCP VirtualBox, IP гостя в правиле указывать обязательно (например, `"guestssh,tcp,,2222,10.0.2.19,22"`). На Linux/macOS-хостах нельзя пробрасывать порты хоста ниже 1024 без root (на Windows-хосте ограничения нет). Каждое правило описывает один порт хоста и один порт гостя — синтаксиса диапазона в документации нет; для 1560–1591 понадобилось бы 32 правила, поэтому для 1С выбирают Bridged или Host-only. [«диапазоном нельзя» — вывод из документированного формата правила, явного запрета в руководстве нет]

```powershell
# Hyper-V: «Default Switch» — NAT с адресами, которые могут меняться после перезагрузки хоста (плохо для сервера 1С).
# Варианты: External switch (мост) либо собственная NAT-сеть со статикой:
New-VMSwitch -SwitchName "NAT1C" -SwitchType Internal
New-NetIPAddress -IPAddress 192.168.100.1 -PrefixLength 24 -InterfaceAlias "vEthernet (NAT1C)"
New-NetNat -Name "NAT1C" -InternalIPInterfaceAddressPrefix 192.168.100.0/24
# в ВМ: статический адрес 192.168.100.10/24, шлюз 192.168.100.1
Add-NetNatStaticMapping -NatName "NAT1C" -Protocol TCP -ExternalIPAddress 0.0.0.0 -ExternalPort 2222 -InternalIPAddress 192.168.100.10 -InternalPort 22
Get-NetNatStaticMapping
```

```powershell
# Универсальный проброс средствами Windows (только TCP; нужна служба «Вспомогательная служба IP», iphlpsvc):
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=1541 connectaddress=192.168.100.10 connectport=1541
netsh interface portproxy show all
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=1541
# и разрешить входящие в брандмауэре Windows:
New-NetFirewallRule -DisplayName "1C server (VM)" -Direction Inbound -Protocol TCP -LocalPort 1540-1541,1560-1591 -Action Allow
```

[Офиц., Microsoft Learn: «Set up a NAT network» (Hyper-V), справка `Add-NetNatStaticMapping`, «netsh interface portproxy»] Команды сверены с документацией: `New-VMSwitch -SwitchName … -SwitchType Internal`; `New-NetIPAddress -IPAddress … -PrefixLength … -InterfaceIndex <ifIndex>` (в документации интерфейс задают индексом из `Get-NetAdapter`; вариант с `-InterfaceAlias "vEthernet (имя)"` равнозначен); `New-NetNat -Name … -InternalIPInterfaceAddressPrefix …`; у `Add-NetNatStaticMapping` обязательны `-NatName`, `-Protocol` (TCP или UDP), `-ExternalIPAddress`, `-ExternalPort`, `-InternalIPAddress`, а `-InternalPort` по умолчанию равен внешнему. Ограничения из документации: на хосте поддерживается **только одна** NAT-сеть (один внутренний префикс WinNAT) — проверьте `Get-NetNat`, лишнюю удаляют `Get-NetNat | Remove-NetNat`; WinNAT сам адреса не раздаёт — IP, шлюз и DNS в ВМ задаются вручную (netplan). Синтаксис `netsh interface portproxy add v4tov4 listenport= connectaddress= connectport= listenaddress= protocol=tcp` подтверждён (единственное допустимое значение `protocol` — `tcp`); для `delete v4tov4` указывают `listenport` и `listenaddress`. Зависимость portproxy от службы `iphlpsvc` — [Практика].

Если клиенты 1С всё же ходят через проброс: пробрасывать нужно 1540, 1541 и **каждый** порт диапазона 1560–1591 «один в один» (кластер сообщает клиенту номер порта рабочего процесса — он должен совпадать), а имя сервера 1С на клиентах должно разрешаться в адрес, на котором слушает проброс (адрес Windows-хоста).

VMware Workstation: проброс портов для NAT настраивается в Virtual Network Editor (VMnet8 → NAT Settings → Port Forwarding).

## 10. Samba: обмен файлами с Windows

### 10.1. Клиент: smbclient и монтирование CIFS

```bash
sudo apt install smbclient cifs-utils
smbclient -L //winhost -U user                 # список общих ресурсов Windows-машины
smbclient //winhost/distr -U user              # интерактивно: ls, cd, lcd, get, put, mget, mput, prompt, recurse, exit
smbclient //winhost/distr -U 'CORP\user' -c 'get setup.run /tmp/setup.run'   # одной командой
smbclient //winhost/distr -U user%'пароль' -c 'prompt; recurse; mget *'      # пароль в командной строке виден в истории и ps
```

Монтирование общей папки Windows в файловую систему (например, для сетевого каталога обмена/бэкапов 1С):

```bash
sudo mkdir -p /mnt/winshare
sudo mount -t cifs //winhost/exchange /mnt/winshare \
     -o username=user,domain=CORP,uid=usr1cv8,gid=grp1cv8,file_mode=0660,dir_mode=0770,iocharset=utf8,vers=3.0
sudo umount /mnt/winshare
```

Постоянно — файл учётных данных `/etc/samba/creds-winhost` (права `600`, владелец root):

```
username=user
password=СЕКРЕТ
domain=CORP
```

и строка в `/etc/fstab`:

```
//winhost/exchange  /mnt/winshare  cifs  credentials=/etc/samba/creds-winhost,uid=usr1cv8,gid=grp1cv8,file_mode=0660,dir_mode=0770,iocharset=utf8,vers=3.0,_netdev,nofail,x-systemd.automount  0  0
```

`uid`/`gid` — от чьего имени файлы будут видны в Linux: серверные процессы 1С работают под `usr1cv8` (группа `grp1cv8`), иначе рабочий процесс не сможет читать/писать каталог. `_netdev,nofail` — не блокировать загрузку, если Windows-машина недоступна.

### 10.2. Сервер: простейший общий каталог на Ubuntu

[Офиц., Ubuntu Server — Samba as a file server]

```bash
sudo apt install samba
sudo mkdir -p /srv/samba/exchange
sudo chown admin:grp1cv8 /srv/samba/exchange && sudo chmod 2775 /srv/samba/exchange   # либо nobody:nogroup для гостевого доступа
sudoedit /etc/samba/smb.conf
```

В `[global]` при необходимости задать `workgroup = WORKGROUP`. В конец файла добавить ресурс с доступом по паролю:

```ini
[exchange]
   comment = Обмен файлами с Windows
   path = /srv/samba/exchange
   browseable = yes
   read only = no
   valid users = admin
   create mask = 0664
   directory mask = 0775
```

(Группа `grp1cv8` появляется после установки сервера 1С; бит setgid `2775` на каталоге заставляет новые файлы наследовать группу, чтобы их могли читать процессы 1С под `usr1cv8`.)

```bash
sudo smbpasswd -a admin                     # задать SMB-пароль существующему пользователю Linux
testparm                                    # проверить smb.conf и показать действующие параметры
sudo systemctl restart smbd                 # в 22.04/24.04 при необходимости и nmbd: smbd.service nmbd.service
sudo ufw allow from 192.168.1.0/24 to any app Samba
sudo smbstatus                              # кто подключён
```

В Windows: `\\srv1c\exchange` или `\\192.168.1.50\exchange` в Проводнике; из командной строки `net use Z: \\192.168.1.50\exchange /user:admin`.

Гостевой вариант из документации Ubuntu (полный доступ любому в сети — только для изолированного стенда): в секции ресурса `guest ok = yes`, `read only = no`, `create mask = 0755`, каталог `chown nobody:nogroup`. Современные Windows 10/11 по умолчанию блокируют небезопасный гостевой вход по SMB — поэтому вариант с пользователем и паролем надёжнее [Практика].

Порты Samba: 445/tcp (SMB), 139/tcp и 137–138/udp (NetBIOS). [Офиц.] В Ubuntu 26.04 (Samba 4.23) NetBIOS в `smb.conf` новых установок выключен — достаточно 445/tcp, обращаться по IP или DNS-имени.

## 11. Прокси, MTU, IPv6 — кратко

### 11.1. Переменные прокси

```bash
export http_proxy=http://proxy.corp.local:3128
export https_proxy=http://proxy.corp.local:3128
export no_proxy=localhost,127.0.0.1,::1,192.168.1.0/24,.corp.local,srv1c
# с аутентификацией: http://user:password@proxy.corp.local:3128  (спецсимволы в пароле — в URL-кодировке)
unset http_proxy https_proxy no_proxy     # отключить
```

- Постоянно для всех пользователей — в `/etc/environment` (формат `ИМЯ=значение`, без `export`); многие программы читают и варианты в верхнем регистре (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`) — задавайте оба. `curl` для HTTP читает только `http_proxy` в нижнем регистре.
- `sudo` по умолчанию не передаёт переменные окружения: `sudo -E apt update` либо настройка apt.
- apt: файл `/etc/apt/apt.conf.d/95proxy`:

```
Acquire::http::Proxy "http://proxy.corp.local:3128/";
Acquire::https::Proxy "http://proxy.corp.local:3128/";
```

- Службы systemd не видят переменные из профиля: `sudo systemctl edit <служба>` → `[Service]` / `Environment="https_proxy=http://proxy.corp.local:3128"`.
- Обязательно включайте в `no_proxy` имя и адрес сервера 1С и локальные сети, иначе обращения к веб-публикации/HTTP-сервисам 1С с самого сервера пойдут через прокси.

### 11.2. MTU

```bash
ip link show dev enp0s3 | grep -o 'mtu [0-9]*'     # текущее значение (стандарт Ethernet — 1500)
ping -M do -s 1472 -c 3 192.168.1.1                # проходит ли пакет 1500 байт без фрагментации
tracepath -n <узел>                                # покажет pmtu по пути
sudo ip link set dev enp0s3 mtu 1400               # временно
```

Постоянно — `mtu: 1400` у интерфейса в netplan. Признаки проблем с MTU: мелкие запросы проходят, а большие «зависают» (SSH подключается, но виснет при выводе большого текста; HTTPS-рукопожатие не завершается; 1С подвисает на крупных выборках) — типично для VPN, PPPoE, туннелей и оверлейных сетей. Jumbo frames (MTU 9000) включают только если их поддерживает **весь** путь, включая виртуальный коммутатор.

### 11.3. Отключение IPv6: нужно ли и как

Отключать IPv6 «на всякий случай» не нужно: ни Canonical, ни документация PostgreSQL этого не требуют. Причины, по которым его всё же отключают на серверах 1С [Практика]: имя сервера разрешается в IPv6-адрес (`::1` или link-local), а часть участников обмена слушает только IPv4; рекомендации с форумов убирать имя сервера из IPv6-строк `/etc/hosts`. Сначала попробуйте мягкие меры:

- убедиться, что имя сервера в `/etc/hosts` стоит только в IPv4-строке;
- предпочитать IPv4 при разрешении имён: раскомментировать в `/etc/gai.conf` строку `precedence ::ffff:0:0/96  100`.

Полное отключение — три способа:

```bash
# 1) sysctl (без перезагрузки)
sudo tee /etc/sysctl.d/60-disable-ipv6.conf >/dev/null <<'EOF'
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF
sudo sysctl --system
ip -6 addr            # должно быть пусто
```

```bash
# 2) параметр ядра (надёжнее всего; нужна перезагрузка)
# в /etc/default/grub: GRUB_CMDLINE_LINUX="ipv6.disable=1"
sudo update-grub && sudo reboot
```

```yaml
# 3) только на уровне интерфейса в netplan
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp6: false
      accept-ra: false
      link-local: []
```

После отключения проверьте службы, которые явно привязаны к IPv6: `ListenAddress ::` в sshd, `listen_addresses` в PostgreSQL (при `localhost` он попытается открыть и `::1` — будет предупреждение в журнале), `Listen [::]:80` в веб-сервере; в `/etc/default/ufw` можно поставить `IPV6=no`.

## Типичные ошибки и подводные камни

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | Клиент 1С: «Не запущен ни один рабочий процесс…» / отказ соединения с `127.0.1.1:1560`, хотя `ragent`, `rmngr`, `rphost` запущены | в `/etc/hosts` сервера имя привязано к `127.0.1.1` | заменить строку на `<реальный IP> <FQDN> <имя>`; проверить `hostname -i`; перезапустить сервер 1С |
| 2 | Клиент 1С: «Этот хост неизвестен», в тексте `tcp://srv1c:15xx` | клиент не разрешает имя сервера (кластер вернул имя, а не IP) | запись в DNS или в `hosts` клиента; подключение по IP не помогает |
| 3 | Порт 1541 доступен, а база не открывается (таймаут) | в firewall не открыт диапазон 1560–1591 | `sudo ufw allow from <сеть> to any port 1560:1591 proto tcp` |
| 4 | После `hostnamectl set-hostname`: `sudo: unable to resolve host …`; клиенты 1С ищут старое имя | не обновлён `/etc/hosts`; старое имя осталось в реестре кластера | поправить `/etc/hosts`; пересоздать кластер/исправить рабочий сервер (п. 4.5) |
| 5 | Имя хоста или `/etc/hosts` «откатываются» после перезагрузки | cloud-init: `preserve_hostname: false`, `manage_etc_hosts: true` | `preserve_hostname: true`, `manage_etc_hosts: false` в `/etc/cloud/cloud.cfg(.d)` либо правка шаблона `hosts.debian.tmpl` |
| 6 | Правки netplan пропали / не применяются | файл `50-cloud-init.yaml` перегенерирован cloud-init; или есть файл с большим номером, перекрывающий настройки | отключить сеть в cloud-init (п. 3.6); `sudo netplan get` покажет итоговую конфигурацию |
| 7 | `netplan apply`: ошибка разбора YAML (`Invalid YAML`, `expected mapping`) | табуляция, неверные отступы, пропущенное двоеточие/дефис | только пробелы; `sudo netplan generate` для проверки |
| 8 | Предупреждение `Permissions for /etc/netplan/*.yaml are too open` | права шире `600` | `sudo chmod 600 /etc/netplan/*.yaml` |
| 9 | Предупреждение о `gateway4 has been deprecated` | устаревший ключ | заменить на `routes: - to: default` / `via:` |
| 10 | После добавления второго интерфейса пропал интернет или «ходит не туда» | два маршрута по умолчанию (оба интерфейса с DHCP/шлюзом) | оставить default на одном; на втором `dhcp4-overrides: {use-routes: false}` или не задавать шлюз |
| 11 | Загрузка задерживается на ~2 минуты на `systemd-networkd-wait-online` | в netplan описан интерфейс без линка | `optional: true` для такого интерфейса или убрать его из конфигурации |
| 12 | После клонирования ВМ сеть не поднимается | изменились MAC и/или имя интерфейса; `match: macaddress` указывает на старый MAC; cloud-init сработал заново | `ip -br link`, исправить имя/MAC в netplan |
| 13 | `ping 8.8.8.8` работает, имена не разрешаются | не заданы DNS-серверы; сломан симлинк `/etc/resolv.conf`; остановлен systemd-resolved | `resolvectl status`; `nameservers:` в netplan; `sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf`; `sudo systemctl restart systemd-resolved` |
| 14 | `dig @dns-сервер srv1c` даёт один адрес, а приложение идёт на другой (или `dig srv1c` находит имя, которого нет в DNS) | приложение читает `/etc/hosts` раньше DNS (NSS: `files` перед `dns`); `dig` без `@сервер` спрашивает заглушку systemd-resolved, которая тоже отдаёт записи `/etc/hosts` | «как видит приложение» — `getent hosts srv1c`; «что в настоящем DNS» — `dig @<DNS-сервер> srv1c` |
| 15 | Короткое имя не разрешается, FQDN разрешается | не задан домен поиска | `nameservers: search: [corp.local]` в netplan |
| 16 | После `sudo ufw enable` пропал доступ по SSH | не добавлено правило для SSH до включения | с консоли ВМ: `sudo ufw allow OpenSSH`; на будущее — сначала правило, потом `enable` |
| 17 | Правило `ufw deny from X` не действует | выше стоит более общее `allow` (первое совпадение выигрывает) | `sudo ufw insert 1 deny from X` |
| 18 | `ufw status` показывает «inactive» после установки `iptables-persistent`, либо ufw удалён | пакеты несовместимы | выбрать что-то одно; при ufw — удалить `iptables-persistent`/`netfilter-persistent` |
| 19 | Порт контейнера Docker доступен снаружи, несмотря на `ufw deny` | Docker обходит цепочки ufw | публиковать на `127.0.0.1:` или правила в `DOCKER-USER` |
| 20 | С сервера `psql -h localhost` работает, с сервера 1С/клиента — «Connection refused» | PostgreSQL слушает только `localhost` | `listen_addresses` в `postgresql.conf`, запись в `pg_hba.conf`, правило firewall; проверить `ss -tlnp \| grep 5432` |
| 21 | Сменили `Port` в `sshd_config`, перезапустили `ssh` — слушается по-прежнему 22 (24.04/26.04) | порт держит `ssh.socket` | `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket` |
| 22 | `Failed to restart sshd.service: Unit sshd.service not found` (22.04/24.04) | в Ubuntu служба называется `ssh` | `sudo systemctl restart ssh` |
| 23 | `PasswordAuthentication no` в своём файле не работает | другой drop-in (например, `50-cloud-init.conf`) идёт раньше по алфавиту и задаёт `yes` | назвать свой файл с меньшим номером или исправить тот; `sudo sshd -T \| grep passwordauth` |
| 24 | Ключ установлен, но сервер всё равно спрашивает пароль | права на `~`, `~/.ssh`, `authorized_keys`; ключ не тот; CRLF/перенос строки внутри ключа | `chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys`; `ssh -v`; на сервере `sudo journalctl -u ssh -n 50` |
| 25 | `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` | сервер переустановлен / адрес занят другой машиной | убедиться, что это ожидаемо; `ssh-keygen -R <узел>` |
| 26 | SSH-сессия обрывается при простое | NAT/файрвол по пути сбрасывает неактивные соединения | клиент: `ServerAliveInterval 30`; PuTTY: keepalives |
| 27 | Собственный адрес заблокирован после нескольких неверных паролей | fail2ban, `ufw limit` или `PerSourcePenalties` (26.04) | подождать/`fail2ban-client set sshd unbanip`; добавить сеть в `ignoreip` |
| 28 | `netplan try` применил новый адрес, сессия зависла, через 2 минуты всё вернулось | так и задумано: подтверждение не получено — откат | менять адрес с консоли ВМ или подтверждать из `tmux`-сессии с нового адреса |
| 29 | В Windows `nslookup srv1c` не находит имя, хотя оно есть в `hosts` | `nslookup` (и `Resolve-DnsName -DnsOnly -NoHostsFile`) опрашивает DNS-сервер напрямую и файл hosts не читает | проверять `ping srv1c`, `Resolve-DnsName srv1c` (без ключей) или `Test-NetConnection srv1c -Port 1541` |
| 30 | Адрес ВМ меняется после перезагрузки Windows-хоста | Hyper-V Default Switch / DHCP | External switch или собственная NAT-сеть со статикой; статика/резервирование адреса |
| 31 | Обращения с сервера к собственным HTTP-сервисам 1С уходят на прокси | не задан `no_proxy` | добавить имя/адрес сервера и локальные сети в `no_proxy` |
| 32 | Мелкие запросы проходят, крупные зависают | MTU по пути меньше 1500 (VPN/туннель) | `ping -M do -s 1472`, `tracepath`; `mtu:` в netplan |
| 33 | `netplan try` ничего не применяет: `bond0: reverting custom parameters for bridges and bonds is not supported` | в конфигурации есть bond/bridge с блоком `parameters:` — откат таких настроек не поддерживается | применять `sudo netplan apply` с консоли ВМ/сервера, заранее сохранив копию YAML |
| 34 | Инструкция говорит править `50-cloud-init.yaml`, а файла нет (или наоборот — нет `00-installer-config.yaml`) | имя файла установщика зависит от выпуска: 22.04 и 26.04 — `00-installer-config.yaml`, 24.04 — `50-cloud-init.yaml` | `ls -l /etc/netplan/`; править тот файл, который есть, либо добавить свой с большим номером |
| 35 | Строка `127.0.1.1 <имя>` возвращается в `/etc/hosts` после перезагрузки, хотя файл целиком не перезаписывается | cloud-init с `manage_etc_hosts: localhost` | `manage_etc_hosts: false`; на установке с ISO 24.04+ проверить, что есть `/etc/cloud/cloud-init.disabled` |
| 36 | Клиент 1С: `server_addr=<имя> descr=11001…: No such host is known` / «Этот хост неизвестен», хотя в списке баз указан IP | кластер возвращает клиенту имя из свойства «Компьютер» рабочего сервера | запись `IP имя` в `hosts`/DNS клиента **или** IP-адрес в свойстве «Компьютер» рабочего сервера (консоль администрирования → Рабочие серверы) |
| 37 | После обновления сервера до 26.04 перестал работать вход по старому ключу | ключ типа DSA (`ssh-dss`): поддержка удалена в OpenSSH 10 | создать ключ `ssh-keygen -t ed25519` и установить его **до** обновления |
| 38 | SSH-соединения с адреса мониторинга/Ansible/проверки порта временно сбрасываются сервером 26.04 (в `journalctl -u ssh` — сообщения о `penalty`) | `PerSourcePenalties` штрафует адрес за неудачные и незавершённые аутентификации (например, «пустые» проверки порта 22) | внести адреса в `PerSourcePenaltyExemptList` в `sshd_config.d`; исправить скрипты (ключи, верный пользователь) |
| 39 | fail2ban запущен, но никого не блокирует при OpenSSH ≥ 9.8 | фильтр `sshd` не знает о процессе `sshd-session` (fail2ban без исправления от 07.2024) | пакет из репозитория 26.04 (1.1.0-9) уже исправлен; иначе обновить фильтр; проверить `fail2ban-regex` |
| 40 | Изменили файл профиля в `/etc/ufw/applications.d/`, а порты в `ufw status` прежние | правила по профилю не пересчитываются автоматически | `sudo ufw app update <имя>`; профиль с именем как в `/etc/services` или числовым не читается вовсе |

## Быстрая шпаргалка

| Задача | Команда |
|---|---|
| Адреса кратко | `ip -br -c a` |
| Маршруты / каким путём пойдёт пакет | `ip r` / `ip route get 8.8.8.8` |
| ARP-таблица | `ip neigh` |
| Статистика ошибок интерфейса | `ip -s link show dev enp0s3` |
| Следить за изменениями сети | `ip -ts monitor` |
| Временно добавить адрес | `sudo ip addr add 192.168.1.50/24 dev enp0s3` |
| Проверить YAML netplan | `sudo netplan generate` |
| Применить с автооткатом | `sudo netplan try --timeout 60` |
| Применить сразу | `sudo netplan apply` |
| Итоговая конфигурация netplan | `sudo netplan get` |
| Состояние сети и расхождения с YAML | `sudo netplan status -a` / `sudo netplan status --diff` |
| Отключить сеть cloud-init | `echo 'network: {config: disabled}' \| sudo tee /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` |
| Состояние networkd | `networkctl status enp0s3` |
| Задать имя хоста | `sudo hostnamectl set-hostname srv1c` |
| Во что разрешается имя сервера | `hostname -i` ; `getent hosts $(hostname)` |
| FQDN | `hostname -f` |
| DNS-серверы | `resolvectl status` |
| Разрешить имя как приложение / через DNS | `getent hosts имя` / `dig +short имя` |
| Сбросить DNS-кэш | `sudo resolvectl flush-caches` |
| Кто слушает порты | `sudo ss -tulpn` |
| Порты процессов 1С | `sudo ss -tlnp \| grep -E 'ragent\|rmngr\|rphost\|ras'` |
| Соединения с PostgreSQL | `ss -tn state established '( sport = :5432 )'` |
| Проверить порт с Linux | `nc -zv srv1c 1541` |
| Проверить порт с Windows | `Test-NetConnection srv1c -Port 1541` |
| Проверить порты стека | `nmap -p 22,80,443,1540,1541,1545,1560-1591,5432 srv1c` |
| Маршрут до узла | `tracepath -n узел` ; `mtr -rwc 50 -n узел` |
| Проверить веб-публикацию | `curl -I http://srv1c/base/` |
| HTTP-код и время ответа | `curl -sk -o /dev/null -w '%{http_code} %{time_total}\n' URL` |
| Записать трафик 1С | `sudo tcpdump -ni any -w /tmp/1c.pcap 'tcp portrange 1540-1591'` |
| Скорость сети | `iperf3 -s` (сервер) / `iperf3 -c srv1c -P 4` (клиент) |
| Линк, скорость, драйвер | `sudo ethtool enp0s3` ; `ethtool -i enp0s3` |
| Состояние firewall | `sudo ufw status verbose` ; `sudo ufw status numbered` |
| Разрешить SSH и включить ufw | `sudo ufw allow OpenSSH && sudo ufw enable` |
| Открыть порты 1С для подсети | `sudo ufw allow from 192.168.1.0/24 to any port 1540,1541,1560:1591 proto tcp` |
| Открыть PostgreSQL для сервера 1С | `sudo ufw allow from 192.168.1.50 to any port 5432 proto tcp` |
| Удалить правило ufw | `sudo ufw delete N` / `sudo ufw delete allow 80/tcp` |
| Вставить правило первым | `sudo ufw insert 1 deny from 203.0.113.7` |
| Журнал ufw | `sudo tail -f /var/log/ufw.log` ; `sudo journalctl -k -g UFW` |
| Все правила netfilter | `sudo nft list ruleset` ; `sudo iptables -S` |
| Бэкенд iptables | `iptables -V` |
| Создать ключ | `ssh-keygen -t ed25519 -C "комментарий"` |
| Установить ключ на сервер | `ssh-copy-id admin@srv1c` |
| Проверить конфигурацию sshd | `sudo sshd -t` ; `sudo sshd -T \| grep -i password` |
| Перезапустить SSH-сервер | `sudo systemctl restart ssh` |
| Применить смену порта SSH (24.04+) | `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket` |
| Режим запуска sshd | `systemctl status ssh.socket` |
| Туннель к PostgreSQL | `ssh -N -L 15432:127.0.0.1:5432 admin@srv1c` |
| Через промежуточный узел | `ssh -J admin@gate admin@192.168.1.50` |
| Скопировать файл / каталог | `scp f admin@srv1c:/tmp/` / `rsync -avP dir/ admin@srv1c:/dst/` |
| Заблокированные fail2ban | `sudo fail2ban-client status sshd` |
| Разблокировать адрес | `sudo fail2ban-client set sshd unbanip IP` |
| Общие папки Windows | `smbclient -L //winhost -U user` |
| Смонтировать папку Windows | `sudo mount -t cifs //winhost/share /mnt/winshare -o credentials=/etc/samba/creds-winhost,uid=usr1cv8,gid=grp1cv8,vers=3.0` |
| Проверить smb.conf | `testparm` |
| Проверить MTU | `ping -M do -s 1472 -c 3 узел` |
| Есть ли IPv6-адреса | `ip -6 addr` |

## Источники

Официальная документация (прочитано в этой сессии, октябрь 2026):

- https://ubuntu.com/server/docs/explanation/networking/configuring-networks/ — Ubuntu Server: команды `ip`, временные и постоянные настройки, примеры netplan (DHCP, статика, мост, несколько адресов, `match`/`set-name`), `/etc/hosts` с `127.0.1.1`, `/etc/nsswitch.conf`, `resolvectl`, замечание о `gateway4` и 18.04.
- https://netplan.readthedocs.io/en/stable/netplan-yaml/ — справочник YAML: типы устройств, свойства, `dhcp4-overrides`, параметры bond/bridge/vlan, устаревание `gateway4`.
- https://netplan.readthedocs.io/en/stable/netplan-try/ , …/netplan-apply/ , …/netplan-generate/ , …/netplan-set/ , …/netplan-status/ , …/cli/ — подкоманды и опции, таймаут 120 с, порядок каталогов и слияния файлов, ограничения `apply`.
- https://netplan.readthedocs.io/en/stable/security/ — права на YAML-файлы.
- https://docs.cloud-init.io/en/latest/reference/network-config.html — отключение сети cloud-init (`network: {config: disabled}`, `network-config=disabled`), приоритет источников.
- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — 26.04: netplan 1.2, systemd 259, OpenSSH 10.2p1 (DSA, PerSourcePenalties, алиас `sshd.service`), Samba 4.23, chrony, ядро 7.0.
- https://documentation.ubuntu.com/release-notes/26.04/ — дата выпуска 26.04 (23.04.2026), срок поддержки, 26.04.1.
- https://documentation.ubuntu.com/release-notes/24.04/ — 24.04: netplan 1.0 и `status --diff`, systemd 255, генератор для `ssh.socket`, несовместимость ufw и iptables-persistent.
- https://ubuntu.com/server/docs/how-to/security/openssh-server/ — пакеты, `sshd_config.d`, `sshd -t`, `systemctl restart ssh.service`, ключи ed25519, `ssh-copy-id`, `DebianBanner`, мультиплексирование.
- https://discourse.ubuntu.com/t/sshd-now-uses-socket-based-activation-ubuntu-22-10-and-later/30189 — сокет-активация sshd: версии, миграция `Port`/`ListenAddress`, возврат к классической службе.
- https://code.launchpad.net/~enr0n/ubuntu/+source/openssh/+git/openssh/+merge/460543 — `sshd-socket-generator` (24.04), порядок `daemon-reload` + `restart ssh.socket`, маскирование генератора.
- https://manpages.ubuntu.com/manpages/resolute/en/man5/sshd_config.5.html — значения директив по умолчанию, отличия пакета Debian/Ubuntu, `PerSourcePenalties`.
- https://manpages.ubuntu.com/manpages/noble/en/man8/ufw.8.html — синтаксис ufw, `limit` (6 соединений за 30 с), порядок правил, профили приложений, отчёты `show`.
- https://ubuntu.com/server/docs/how-to/security/firewalls/ — примеры ufw, профили, маскарадинг (`/etc/default/ufw`, `/etc/ufw/sysctl.conf`, `/etc/ufw/before.rules`), журналирование.
- https://documentation.ubuntu.com/security/security-features/network/firewall/ и …/firewall/nftables/ — связь ufw/iptables/nftables, бэкенд nft по умолчанию с 20.10, версии пакетов, `nft list ruleset`, `/etc/nftables.conf`, запрет смешивать подходы.
- https://manpages.ubuntu.com/manpages/noble/en/man8/systemd-resolved.service.8.html — адреса 127.0.0.53/127.0.0.54, режимы `/etc/resolv.conf`, синтезируемые записи, однокомпонентные имена.
- https://www.debian.org/doc/manuals/debian-reference/ch05.en.html — назначение строки `127.0.1.1`, рекомендация для систем с постоянным IP, таблица net-tools → iproute2.
- https://ubuntu.com/server/docs/how-to/samba/file-server/ — установка Samba, пример ресурса, перезапуск служб.
- https://docs.docker.com/engine/network/packet-filtering-firewalls/ — несовместимость Docker и ufw, предупреждение об `iptables: false`.
- https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse и …/openssh_keymanagement — OpenSSH в Windows: требования к версии, установка компонентов, служба `ssh-agent`, расположение ключей, Ed25519 по умолчанию.
- https://packages.ubuntu.com/ (поиск `ufw`, `fail2ban`) — версии пакетов по выпускам.

Дополнительно проверено рецензентом (10.10.2026):

- https://packages.ubuntu.com/ (поиск `netplan.io`, `openssh-server`, `ufw`, `iptables`, `nftables`, `fail2ban`, `samba` по всем выпускам) — версии пакетов в jammy/noble/resolute и их `-updates`/`-security`.
- https://ubuntu.com/about/release-cycle — сроки стандартной поддержки LTS (май 2027 / май 2029 / май 2031).
- https://github.com/canonical/netplan — исходный код: `netplan_cli/cli/commands/set.py` (`FALLBACK_FILENAME = '70-netplan-set.yaml'`, удаление ключа значением `null`), `try_command.py` (отказ `try` при bond/bridge с нестандартными параметрами, таймаут 120 с), `include/state.h` (описание `netplan_state_update_yaml_hierarchy`); https://github.com/canonical/netplan/releases/tag/0.106 — появление `netplan status`.
- https://netplan.readthedocs.io/en/stable/netplan-status/ , …/netplan-set/ , …/netplan-try/ , …/netplan-yaml/ — опции `--diff`, `--diff-only`, `-f json|yaml`; умолчания bond/bridge/VLAN, `dhcp4-overrides`, перечень типов устройств.
- https://github.com/canonical/subiquity — исходный код установщика Ubuntu Server (`subiquity/models/network.py`, `subiquity/models/subiquity.py`) в тегах 22.04.1, 24.04.1, 24.04.5, 25.04, 25.10, 26.04.1: куда пишется сетевая конфигурация и отключение cloud-init после первой загрузки.
- https://github.com/canonical/cloud-init — `cloudinit/ssh_util.py` (файл `/etc/ssh/sshd_config.d/50-cloud-init.conf`); https://docs.cloud-init.io/en/latest/reference/modules.html — модули Update Etc Hosts (`manage_etc_hosts`), Set/Update Hostname (`preserve_hostname`), Set Passwords (`ssh_pwauth`); https://docs.cloud-init.io/en/latest/howto/disable_cloud_init.html — `/etc/cloud/cloud-init.disabled`, `cloud-init=disabled`; https://docs.cloud-init.io/en/latest/explanation/events.html — события `BOOT_NEW_INSTANCE`/`BOOT`/`HOTPLUG`.
- https://github.com/jdstrand/ufw — `src/applications.py`: правила для имён и файлов профилей приложений; https://manpages.ubuntu.com/manpages/noble/en/man8/ufw.8.html и …/ufw-framework.8.html — формат `ports=`, лимит 15 портов, `app update --add-new`, `app default`, порядок `before`/`user`/`after`.
- https://metadata.ftp-master.debian.org/changelogs/main/f/fail2ban/unstable_changelog — changelog пакета fail2ban (1.0.2-3: `banaction = nftables`, `backend = systemd`; 1.1.0-6: совместимость с OpenSSH 9.8); https://github.com/fail2ban/fail2ban/issues/3782 — исправление фильтра `sshd` для `sshd-session` (03.07.2024).
- https://www.openssh.org/txt/release-9.0 , …/release-9.5 , …/release-9.8 , https://www.openssh.org/releasenotes.html (9.9, 10.0–10.2) — `scp` через SFTP, Ed25519 по умолчанию в `ssh-keygen`, `PerSourcePenalties`, разделение на `sshd`/`sshd-session`/`sshd-auth`, удаление DSA, `mlkem768x25519-sha256`.
- https://bugs.launchpad.net/ubuntu/+source/openssh/+bug/2069041 и …/+bug/2103633 — смена порта при сокет-активации; `AddressFamily` и `sshd-socket-generator`.
- https://manpages.ubuntu.com/manpages/jammy/en/man1/hostnamectl.1.html — команда `hostnamectl hostname` в systemd 249.
- https://manpages.ubuntu.com/manpages/noble/en/man8/ss.8.html , …/man1/nc_openbsd.1.html , …/man8/tcpdump.8.html , …/man8/mtr.8.html , …/man8/ping.8.html — опции и синтаксис фильтров `ss`, `nc`, `tcpdump`, `mtr`, `ping`.
- https://docs.docker.com/engine/network/firewall-iptables/ — цепочка `DOCKER-USER`, примеры правил, `conntrack --ctorigdst/--ctorigdstport`.
- https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/networkingdetails.html и …/vboxmanage.html — проброс портов NAT (`--nat-pf1`/`--natpf1`, `controlvm natpf1`), ограничения NAT.
- https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/user-guide/setup-nat-network , https://learn.microsoft.com/en-us/powershell/module/netnat/add-netnatstaticmapping , https://learn.microsoft.com/en-us/windows-server/networking/technologies/netsh/netsh-interface-portproxy — NAT-сеть Hyper-V, статические сопоставления портов, `netsh interface portproxy`.

1С:

- https://its.1c.ru/db/content/metod8dev/src/developers/scalability/instructions/i8105953.htm — ИТС, «Установка Платформы „1С:Предприятие“ в ОС Linux» (8.3.13, 2018): `hostname -f`, запись `IP hostname.local hostname` в `hosts` машин, с которых устанавливаются соединения с кластером (текст страницы получен с искажённой кодировкой; содержание сверено рецензентом по официальной английской версии статьи на kb.1ci.com — «Installing 1C:Enterprise 8 platform on Linux»).
- https://kb.1ci.com/1C_Enterprise_Platform/FAQ/Administration/Server/Ports_setup_for_1C_Enterprise_server/ — 1C International FAQ: порты 1540, 1541, 1560–1591 (TCP).
- kb.1ci.com, Administrator Guide «Client/Server Mode» (официальный английский перевод «Руководства администратора. Клиент-серверный вариант») — прочитано рецензентом 10.10.2026 через REST-интерфейс сайта (`https://kb.1ci.com/rest/wikis/xwiki/spaces/OnecInt/spaces/KB/spaces/1C_Enterprise_Platform/spaces/Guides/spaces/Administrator_Guides/spaces/Administrator_Guide_Client_Server_Mode/spaces/<версия>/…/pages/WebHome/translations/en`; обычные адреса страниц перенаправляют на портал поддержки):
  - 8.5.1, п. 2.2.1 «General concepts» — рабочий сервер, агент, менеджер, рабочий процесс; реестр сервера `1cv8wsrv.lst`, реестр кластера `1cv8clst.lst`, каталог `reg_<порт>`;
  - 8.5.1, п. 2.2.2 «Client application and server cluster interaction» — адресация процессов кластера «имя рабочего сервера + порт», порты 1540/1541/1560:1591;
  - 8.3.22, п. 5.2.6 «Operations with the list of working servers in a cluster» — свойства «Компьютер», «IP-порт» (1540), «Диапазон IP-портов» (1560:1591); при IP-адресе в «Компьютер» запись DNS/hosts не требуется;
  - 8.3.24 и 8.3.27, п. 4.2.2 «On Linux»; 8.5.1, п. 4.2.1 и 4.2.2.4 — юнит `srv1cv8-A.B.C.D@.service`, переменные `SRV1CV8_*`, параметры `ragent` (`/port`, `/regport`, `/range`, `/debug`, `/debugServerPort` 1550);
  - 8.3.24, п. 4.3.2 «On Linux» — несколько экземпляров сервера, запрет смены портов работающего экземпляра;
  - 8.3.25, п. 5.3.2 «Server cluster administration server» — `ras`/`rac`: порт 1545, агент `localhost:1540`, `--daemon`, `--monitor-port` 1555, совместимость версий;
  - 8.5.1, приложение 3, п. 3.8 «Network screen» — таблица портов по умолчанию (1540, 1541, 1545, 1550, 1560–1591) и рекомендации по сетевому экрану.
- kb.1ci.com, FAQ (официальные статьи 1C International): «How to resolve "No such host is known" error» (текст ошибки `server_addr=… descr=11001(0x00002AF9)`, запись в `hosts` клиента); «Installing 1C:Enterprise 8 platform on Linux» (англ. версия статьи ИТС: `hostname -f`, запись в `hosts` машин-клиентов); «How to install and run two versions of 1C:Enterprise server on Ubuntu server» (второй экземпляр на 2540/2541/2560:2591); «Setting up HASP license manager» (порт 475, `NH_PORT_NUMBER`, `NHS_IP_PORTNUM`, обмен всегда по UDP); «Configuring a Linux server to share concurrent licenses» и «How to connect to an infobase from thin client using server's external IP» (порт 1947); «How to enable debugging of 1C:Enterprise server instance» (пример строки запуска `ragent … -regport 1541 -port 1540 -range 1560:1591`).
- https://habr.com/ru/articles/861006/ — формулировки о портах 1540/1541/1560–1591 и риск отсутствия авторизации на портах кластера.
- https://www.linux.org.ru/forum/admin/10842059 — практический случай: ошибка «Не запущен ни один рабочий процесс», решение — убрать `127.0.1.1 <имя>` из `/etc/hosts`.
- forum.infostart.ru (темы 222637, 205195, 179518), infostart.ru/1c/articles/2498401 — практика: формат `/etc/hosts` «IP – FQDN – короткое имя», проверка портов telnet, смена портов сервера. Страницы прочитаны только в виде поисковых сводок (сайт вернул HTTP 429).

Ограничения исследования: лимит веб-поиска в сессии автора был исчерпан до завершения проверки части пунктов; рецензент работал без поисковой системы, только прямым чтением первоисточников по известным адресам. Всё, что не удалось сверить с первоисточником, помечено в тексте «⚠ не подтверждено». Остаются непроверенными: (1) фактическое значение `SRV1CV8_RANGE` в поставляемом юните сервера 1С (в документации расхождение `1560:1591`/`1561:1590`); (2) русские формулировки ошибок клиента 1С и процедура переименования центрального сервера; (3) синтаксис `ras` и параметры `dbgs` для 8.5.x, порты в выпусках новее 8.5.1 и актуальная на октябрь 2026 версия платформы; (4) имя дистрибутивного шаблона cloud-init для `/etc/hosts` и файл `60-cloudimg-settings.conf` в облачных образах; (5) номер версии systemd, в которой появился адрес `127.0.0.54`; (6) поведение Docker с бэкендом nftables. Опции `ss`, `nc`, `tcpdump`, `mtr`, `ping` сверены с man-страницами Ubuntu 24.04; опции остальных классических утилит (`ip`, `dig`, `curl`, `wget`, `nmap`, `ethtool`, `iperf3`, `rsync`, `scp`, `iptables`, `nft`, `smbclient`, `mount.cifs`, `traceroute`) приведены в объёме давно стабильных общеизвестных ключей и по man-страницам в этой сессии не перечитывались — при сомнении сверяйтесь с `man <утилита>` на целевой системе. Ни одна команда из файла не выполнялась на живом сервере.

