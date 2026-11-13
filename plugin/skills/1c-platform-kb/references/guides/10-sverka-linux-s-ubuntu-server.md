# Сверка статей kb/linux/ с официальной документацией Ubuntu Server (19.10.2026)

> Что сделано: статьи `kb/linux/01`–`12` сверены с документацией Ubuntu Server (https://documentation.ubuntu.com/server/ — тот же текст отдаёт https://ubuntu.com/server/docs, исходники — github.com/canonical/ubuntu-server-documentation, последнее изменение репозитория 16.10.2026). Страницы прочитаны 19.10.2026 обычным HTTP-запросом. Заметки к выпускам 24.04 и 26.04 в статьях `kb/linux/` уже процитированы (rust-coreutils, sudo-rs, chrony, OpenSSH, APT 3.1), поэтому заново не сверялись.

## 1. Как сверяли

1. **Перечень страниц.** Обход разделов `how-to/`, `explanation/`, `reference/`, `tutorial/` дал 246 страниц. По темам администратора сервера 1С и PostgreSQL отобрано 24, прочитано 23 — `how-to/networking/timedatectl-and-timesyncd/` при запросе вернула 504, её тема покрыта страницами про chrony.
2. **Программная проверка покрытия.** Из каждой страницы выбраны пути (`/etc/…`, `/var/…`, `/usr/…`), имена пакетов из `apt install …` и команды из примеров (`sudo …`). Каждый элемент искали в текстах `kb/linux/*.md`. Отсутствующие разобраны вручную: почти всё — частные примеры документации (`/etc/netplan/99_config.yaml`, `vgcreate foo /dev/sda1`, PPA backports), а не пробелы.
3. **Ручная сверка умолчаний и поведения**, которые меняются от выпуска к выпуску (раздел 2).

## 2. Результаты по темам

| Тема | Где в базе | Документация Ubuntu Server | Итог |
|---|---|---|---|
| Синхронизация времени: chrony по умолчанию с 25.10 (только новые установки), NTS по пулам Ubuntu, файл `/etc/chrony/sources.d/ubuntu-ntp-pools.sources`, `ntp-bootstrap.ubuntu.com`, `chronyd -q`/`-Q`, `chronyc -N tracking` | `linux/09`, разд. 8 | `explanation/networking/about-time-synchronisation/`, `how-to/networking/chrony-client/` | совпадает (в базе подробнее: порт NTS-KE TCP 4460, `chronyc -N authdata`, возврат к обычному NTP) |
| OpenSSH: `Include /etc/ssh/sshd_config.d/*.conf` в начале `sshd_config`, проверка `sshd -t`, сокет-активация | `linux/08`, разд. 8.8; `linux/03` | `how-to/security/openssh-server/` | совпадает. **Документация Ubuntu упрощает:** после правки предлагает `systemctl restart ssh.service`. При сокет-активации (24.04, 26.04) для смены `Port`/`ListenAddress` нужно `daemon-reload` и `restart ssh.socket` — в базе это написано верно |
| Брандмауэр: `ufw` установлен, но выключен; профили в `/etc/ufw/applications.d`; `before.rules`, `DEFAULT_FORWARD_POLICY` | `linux/08`, разд. 7 | `how-to/security/firewalls/` | совпадает |
| Автообновления: `unattended-upgrades` установлен и включён, раз в сутки; файлы `20auto-upgrades`, `50unattended-upgrades`; `Allowed-Origins` с ESM; `Package-Blacklist`; `MailReport "on-change"`; таймеры `apt-daily*`, `Persistent` | `linux/04`, разд. 8 | `how-to/software/automatic-updates/` | совпадает (в базе дополнительно разбор кода `unattended-upgrade` и поведение для репозитория Postgres Pro) |
| Фазовые обновления: включены по умолчанию, обновления безопасности не фазируются | `linux/04` | `explanation/software/about-apt-upgrade-and-phased-updates/` | совпадает |
| Переход на новый выпуск: `do-release-upgrade`, только на следующий LTS, после первого точечного выпуска, `-d` не для продуктива | `linux/04`, разд. 9 | `how-to/software/upgrade-your-release/` | совпадает |
| Пользователи: root без пароля, первый пользователь в группе `sudo`, домашние каталоги `0750` (`DIR_MODE` в `/etc/adduser.conf`), `chage`, `pam_unix … minlen` | `linux/03` | `how-to/security/user-management/` | совпадает |
| sudo-rs в 26.04 | `linux/01`, `linux/02` | `reference/other-tools/sudo-rs/` | совпадает (страница уже была в источниках базы) |
| Системные требования 24.04 amd64: ОЗУ от 1,5 ГБ (ISO), рекомендуется от 3 ГБ; диск от 5 ГБ, рекомендуется от 25 ГБ | `linux/11`, разд. 2 | `reference/installation/system-requirements/` | совпадает |
| LVM: `pvcreate`, `vgcreate`, `lvcreate`, `lvextend --resizefs`, снимки, `pvmove` | `linux/07` | `how-to/storage/manage-logical-volumes/`, `explanation/storage/about-lvm/` | совпадает (в базе — те же команды с короткими ключами `-r`, `-L`) |
| Netplan: YAML в `/etc/netplan/`, рендереры, `netplan try` / `apply` / `status` | `linux/08`, разд. 3 | `explanation/networking/about-netplan/`, `configuring-networks/` | совпадает |
| AppArmor: `aa-status`, `aa-complain`, `aa-enforce`, отключение профиля через `/etc/apparmor.d/disable/` | `linux/03`, `linux/09` | `how-to/security/apparmor/` | совпадает |
| **Дамп ядра (kdump)** | `linux/11` | `how-to/software/kernel-crash-dump/` | **уточнено.** В базе было «в 26.04 kdump включён по умолчанию на серверных установках». По документации: с 24.10 включается при установке, только если система подходит — не меньше 4 потоков процессора, 6 ГБ–2 ТБ ОЗУ, свободное место в `/var` больше пятикратного объёма ОЗУ + подкачки, amd64. Условия проверяет `/usr/share/kdump-tools/kdump_set_default`. Добавлены проверка `kdump-config show` и выключение (`USE_KDUMP=0` в `/etc/default/kdump-tools` или удаление `kdump-tools`, затем перезагрузка) |
| PostgreSQL из архива Ubuntu | `postgresql/01` (у пользователя — сборка Postgres Pro, не из архива) | `how-to/databases/install-postgresql/` | расхождений нет; к сборке «PostgreSQL для 1С» страница не относится |
| Apache | `1c/05` | `how-to/web-services/install-apache2/` | расхождений нет; страница Ubuntu упоминает устаревший каталог `/etc/apache2/conf.d` (в 24.04 — `conf-available`/`conf-enabled`, как в базе) |
| Резервное копирование сценариями (`tar`, ротация) | `linux/10` | `how-to/backups/back-up-using-shell-scripts/` | совпадает по сути; пример Ubuntu архивирует `/var/spool/mail` — к серверу 1С не относится |

## 3. Что есть в документации Ubuntu, но не в базе (не добавлялось)

- SSH с аутентификацией Kerberos (GSSAPI): `how-to/security/openssh-gssapi/`, файл `/etc/ssh/sshd_config.d/gssapi.conf`. Для сервера 1С не нужно — Kerberos 1С описан в `1c/08`.
- Пример ужесточения криптографии SSH отдельным файлом `/etc/ssh/sshd_config.d/crypto-hardening.conf` (`explanation/crypto/openssh-crypto-configuration/`). Общие правила `sshd_config.d` в базе есть (`linux/08`).
- Каталог `/etc/apt/apt.conf.d/99-Phased-Updates` из примера отключения фазовых обновлений. Механизм в базе описан, имя файла произвольное.

## 4. Что не сверялось

- Страница `how-to/networking/timedatectl-and-timesyncd/` (ответ 504); её содержание — `timedatectl` и `timesyncd` — в `linux/09` подтверждено man-страницами и заметками к выпускам.
- Страницы про сервисы, которых на сервере 1С нет: почта, DNS, DHCP, Samba, OpenLDAP, виртуализация, контейнеры, высокая доступность.
- Заметки к выпускам 24.04 и 26.04 — уже в источниках статей `linux/`.
