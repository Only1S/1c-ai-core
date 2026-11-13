# Сводный справочник команд Ubuntu Server: по категориям и по алфавиту

> Область: командная строка Ubuntu Server (bash, coreutils, util-linux, systemd, apt, диски, сеть), утилиты PostgreSQL и «1С:Предприятие 8» на Linux — около 700 команд | Версии: Ubuntu 22.04 LTS (jammy), 24.04 LTS (noble), 26.04 LTS (resolute); PostgreSQL 14–18; платформа 1С 8.3.2x / 8.5.x | Актуальность: 2026-10-10 | Рецензия-фактчекинг: 2026-10-10 (что проверено и что осталось с пометкой «⚠ не подтверждено» — в конце раздела «Источники»)

Это **указатель**, а не учебник: для каждой команды — назначение одной строкой, пакет и 1–2 самых ходовых примера. Подробности по темам — в остальных статьях каталогов `kb/linux`, `kb/postgresql`, `kb/1c`. Полный синтаксис всегда смотрите на самом сервере: `man КОМАНДА`, `КОМАНДА --help`, `help ВСТРОЕННАЯ`.

## Кратко — 20 главных фактов и команд

1. **Актуальные версии (10.10.2026).** Ubuntu 26.04.1 LTS «Resolute Raccoon» (выпуск 23.04.2026, поддержка до апреля 2031): ядро 7.0, systemd 259, APT 3.x, OpenSSH 10.2, OpenSSL 3.5, Python 3.14, PostgreSQL 18. Ubuntu 24.04 LTS (до 31.05.2029): ядро 6.8, systemd 255, APT 2.8, OpenSSH 9.6, PostgreSQL 16. Ubuntu 22.04 LTS (до апреля 2027): ядро 5.15, systemd 249, PostgreSQL 14.
2. **PostgreSQL:** поддерживаются ветки 14–18 (минорные от 13.08.2026: 18.6, 17.11, 16.15, 15.19, 14.24); ветка 14 снимается с поддержки 12.11.2026. PostgreSQL 19 на 10.10.2026 ещё **не выпущен** (Beta 4 от 24.09.2026).
3. **В 26.04 базовые утилиты — Rust-реализация** (`rust-coreutils` 0.8.0, проект uutils): `ls`, `cat`, `sort`, `chmod`, `df`… Исключение — `cp`, `mv`, `rm` остались GNU. GNU-варианты всех утилит доступны с префиксом `gnu`: `gnuls`, `gnusort`, `gnudate`, `gnudd` (пакет `gnu-coreutils` 9.7). Скрипты с экзотическими флагами coreutils проверяйте на 26.04.
4. **В 26.04 `sudo` — это `sudo-rs`** (0.2.13). Классический sudo переименован в `sudo.ws`. В man-странице sudo-rs нет `-E` (есть только `--preserve-env=СПИСОК`) и `-H`; при вводе пароля показываются звёздочки (`Defaults !pwfeedback` в `visudo`, чтобы отключить). В sudoers у sudo-rs подстановочный знак в аргументах команды работает только как отдельный **последний** аргумент (`/sbin/service ntp *`), а шаблон внутри аргумента (`rm *.txt`, `systemctl restart srv1cv8-*`) не сработает — пишите точные имена юнитов.
5. **Время:** 22.04/24.04 — `systemd-timesyncd` (`timedatectl timesync-status`); 26.04 — `chrony` 4.8 по умолчанию с NTS (`chronyc tracking`, `chronyc sources -v`).
6. **initramfs:** 22.04/24.04 — `initramfs-tools` (`update-initramfs -u`, `lsinitramfs`); 26.04 — `dracut` (`dracut -f`, `lsinitrd`), при этом команда `update-initramfs` сохранена и поставляется пакетом `dracut`.
7. **APT:** с 24.04 источники в формате deb822 — `/etc/apt/sources.list.d/ubuntu.sources`; в 26.04 **удалён `apt-key`** (ключи кладут в `/etc/apt/keyrings/` и ссылаются через `Signed-By`), добавлены `apt why`, `apt why-not`, `apt history-list|history-info|history-undo|history-redo|history-rollback`.
8. **Сеть настраивается через netplan** (`/etc/netplan/*.yaml` → `sudo netplan try` → `sudo netplan apply`), диагностика — `ip`, `ss`, `resolvectl`, `networkctl`. `ifconfig`, `netstat`, `route`, `arp` — устаревший пакет `net-tools`, в системе по умолчанию отсутствует.
9. **Сервисы:** `systemctl status|start|stop|restart|reload|enable --now ИМЯ`, логи — `journalctl -u ИМЯ -e` (в конец) и `-f` (следить).
10. **PostgreSQL в Ubuntu — это «кластеры» postgresql-common:** `pg_lsclusters`, `pg_ctlcluster 18 main reload`, `systemctl restart postgresql@18-main`. Клиентские утилиты (`psql`, `pg_dump`…) лежат в `/usr/bin` как обёртки `pg_wrapper`; серверные (`pg_ctl`, `initdb`, `pg_controldata`, `pg_resetwal`, `pg_upgrade`) — в `/usr/lib/postgresql/NN/bin/` и в `PATH` не входят.
11. **У сборок Postgres Pro другие пути:** `/opt/pgpro/std-17/bin/`, данные `/var/lib/pgpro/std-17/data`, сервис `postgrespro-std-17`, инициализация `pg-setup initdb`; `pg_lsclusters` для них не работает. Бесплатная сборка «PostgreSQL для 1С» от Postgres Professional — пакет `postgrespro-1c-NN`, каталог `/opt/pgpro/1c-NN/` (репозиторий `repo.postgrespro.ru/1c/1c-NN/`, ветки 14–18, есть сборки для Ubuntu 22.04/24.04/26.04).
12. **Утилиты 1С не в `PATH`:** `/opt/1cv8/x86_64/<версия>/` (`ragent`, `rmngr`, `rphost`, `ras`, `rac`, `ibcmd`, `ibsrv`, `webinst`, `1cv8`, `1cv8c`). Сервис сервера — `srv1cv8-<версия>@default`, сервер администрирования — `ras-<версия>`.
13. **Порты:** SSH 22; PostgreSQL 5432; 1С: агент 1540, менеджер кластера 1541, рабочие процессы 1560–1591, RAS 1545; веб-публикация 80/443.
14. **Главные команды диагностики «что с сервером»:** `uptime`, `free -h`, `df -hT`, `df -i`, `top`/`htop`, `vmstat 1`, `iostat -xz 1`, `ss -tulpn`, `journalctl -p err -b`, `systemctl --failed`, `dmesg -T --level=err,warn`.
15. **Перед правкой конфига — копия:** `sudo cp -a файл файл.bak.$(date +%F)`; после правки — проверка синтаксиса (`sshd -t`, `visudo -c`, `netplan try`, `nginx -t`, `apache2ctl configtest`, `pg_ctlcluster 18 main reload` + чтение лога).
16. **Никогда `kill -9` для процессов `postgres`** (кроме крайнего случая): только `pg_terminate_backend(pid)` / `pg_cancel_backend(pid)` или `pg_ctlcluster … stop -m fast`.
17. **`rm -rf`, `dd`, `mkfs`, `wipefs`, `chmod -R`, `chown -R`, `> файл`** — необратимы; перед запуском проверьте `hostname`, `pwd`, `lsblk -f` и раскрытие шаблона через `echo`.
18. **Пакеты «не найдены»:** часть привычных утилит в стандартной установке отсутствует — `unzip`, `zip`, `bzip2`, `tree`, `net-tools`, `traceroute`, `smartmontools`, `nfs-common`, `acl`, `iotop`, `plocate`, `whois`, `at` (ставятся `apt install`). В 26.04 к ним добавились `last` (пакет `wtmpdb`) и `lastlog2` (пакет `lastlog2`): в манифесте серверного образа 26.04.1 этих пакетов нет, а из `util-linux` команды `last`/`lastb` убраны.
19. **Инструменты производительности** (`sysstat`: `iostat`/`mpstat`/`pidstat`/`sar`; `htop`, `strace`, `tcpdump`, `bpftrace`, `bpfcc-tools`, `trace-cmd`, `perf` из `linux-tools`) в 24.04 и 26.04 уже установлены. В 22.04 из этого набора предустановлены только `htop`, `strace`, `tcpdump`; `sysstat`, `bpftrace`, `bpfcc-tools`, `trace-cmd`, `linux-tools-*`, а также `jq` и `numactl` нужно ставить (проверено по манифесту `ubuntu-22.04.5-live-server-amd64.manifest`).
20. **Ubuntu 26.04 + PostgreSQL:** в примечаниях к выпуску описана регрессия производительности PostgreSQL на ядре Linux 7.0; системы с включёнными huge pages не затронуты — рекомендовано настроить huge pages и `huge_pages = on`.

## 0. Условные обозначения и отличия версий

**Колонка «Пакет».** Имя deb-пакета, в котором живёт команда (`dpkg -S $(command -v КОМАНДА)` покажет точно). Пометка **⊕** означает: пакета нет в стандартной установке Ubuntu Server (проверено по манифестам `ubuntu-24.04.4-live-server-amd64.manifest` и `ubuntu-26.04.1-live-server-amd64.manifest`; при рецензии дополнительно сверено с `ubuntu-22.04.5-live-server-amd64.manifest`) либо его наличие не проверялось — сначала `command -v КОМАНДА`, при отсутствии `sudo apt install ПАКЕТ`. В minimal- и cloud-образах набор ещё меньше. «bash» в колонке — встроенная команда оболочки. Оговорка о точности: манифест описывает образ установщика, а читался он автоматическим инструментом, который на длинных списках иногда пропускает строки (так, он «не нашёл» обязательный `util-linux` в манифесте 24.04), поэтому пометку ⊕ считайте подсказкой, а не гарантией.

Расхождения между выпусками, найденные при сверке манифестов: `jq`, `sysstat`, `bpftrace`, `bpfcc-tools`, `trace-cmd`, `linux-tools-*`, `numactl` — нет в 22.04, есть в 24.04/26.04; `binutils` (`strings`, `readelf`, `ar`) — есть в 22.04 и 26.04, нет в 24.04; `nvme-cli`, `mokutil` — есть только в манифесте 26.04; `byobu` — есть в 22.04/24.04, нет в 26.04; пакет диагностики называется `sosreport` в 22.04/24.04 и `sos` в 26.04; `telnet` в 22.04 — классический netkit (`telnet`), с 24.04 — `inetutils-telnet`; `irqbalance` предустановлен только в 22.04; DHCP-клиент: `isc-dhcp-client` в 22.04, `dhcpcd-base` в 24.04.

**Запись примеров.** Несколько примеров в одной ячейке разделены знаком «·»; `sudo` указан там, где нужен root; `NN` — мажорная версия PostgreSQL (14…18); `<версия>` — полный номер платформы 1С, например `8.3.27.1688`; слова ЗАГЛАВНЫМИ (`PID`, `ИМЯ`, `КАТАЛОГ`) — подставляемые значения. Примеры с конвейерами (`|`) вынесены из таблиц в блоки кода под ними. Имена сервисов и путей с номером версии (`postgresql@18-main`, `8.3.27.1688`) — примеры: подставляйте свои (`pg_lsclusters`, `ls /opt/1cv8/x86_64/`).

| Что | 22.04 jammy | 24.04 noble | 26.04 resolute |
|---|---|---|---|
| Ядро / systemd | 5.15 / 249 | 6.8 / 255 | 7.0 / 259 |
| coreutils | GNU 8.32 | GNU 9.4 | rust-coreutils 0.8.0 (+ GNU 9.7 с префиксом `gnu`; `cp`/`mv`/`rm` — GNU) |
| sudo | sudo 1.9.9 | sudo 1.9.15 | sudo-rs 0.2.13 (классический — `sudo.ws`) |
| APT | 2.4 | 2.8 | 3.1→3.2; нет `apt-key`; `apt history-*`, `apt why` |
| Источники APT | `/etc/apt/sources.list` | `/etc/apt/sources.list.d/ubuntu.sources` (deb822) | то же |
| Синхронизация времени | systemd-timesyncd | systemd-timesyncd | chrony 4.8 (NTS) |
| initramfs | initramfs-tools | initramfs-tools | dracut 110 (`update-initramfs` сохранён) |
| OpenSSH / OpenSSL | 8.9 / 3.0 | 9.6 / 3.0 | 10.2 (DSA удалён) / 3.5 |
| PostgreSQL в архиве | 14 | 16 | 18 |
| cgroup v1 | есть | есть | удалён (только v2) |
| netplan | 0.104 при выпуске → 0.106.1 в обновлениях | 1.0 при выпуске → 1.1.2 в обновлениях | 1.2 |
| Python 3 | 3.10 | 3.12 | 3.14 |
| Запуск sshd | `ssh.service` | сокет-активация `ssh.socket` (генератор `sshd-socket-generator` читает `sshd_config`) | то же: `ssh.socket` и `sshd-socket-generator` входят в `openssh-server` 10.2 |
| История входов | `last`/`lastb` (util-linux), `lastlog` (login) | то же; модуль `pam_lastlog.so` удалён | `last` — пакет ⊕ `wtmpdb`; `lastb` нет; `lastlog2` — пакет ⊕ `lastlog2` |
| Конец стандартной поддержки | апрель 2027 | 31.05.2029 | апрель 2031 |

Версии столбца 22.04 сверены с манифестом 22.04.5 (apt 2.4.13, sudo 1.9.9, coreutils 8.32, OpenSSH 8.9p1, OpenSSL 3.0.2, systemd 249.11, ядро 5.15, python3 3.10.6) и примечаниями к выпуску 22.04; столбца 24.04 — с манифестом 24.04.4 (apt 2.8.3, sudo 1.9.15p5, coreutils 9.4, OpenSSH 9.6p1, netplan 1.1.2, ядро 6.8.0-100); столбца 26.04 — с манифестом 26.04.1 (apt 3.2.0, sudo-rs 0.2.13 и классический sudo 1.9.17p2, rust-coreutils 0.8.0, gnu-coreutils 9.7, OpenSSH 10.2p1, systemd 259.5, netplan 1.2, dracut 110, ядро 7.0.0-30, python3 3.14.3).

Переключение набора coreutils в 26.04 — пакетами-провайдерами `coreutils-from-uutils` (по умолчанию) и `coreutils-from-gnu`. Проверить, что именно запускается: `ls --version`, `cp --version`, `dpkg -S "$(command -v ls)"`.

## 1. Файлы и каталоги

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `ls` | список файлов и каталогов | coreutils | `ls -lah /var/log` · `ls -ltr` (свежие внизу) · `ls -ld /opt/1cv8` |
| `pwd` | текущий каталог | bash/coreutils | `pwd -P` (без симлинков) |
| `cp` | копирование | coreutils | `cp -a /etc/postgresql /root/pg-etc.bak` · `cp -i a b` |
| `mv` | перемещение / переименование | coreutils | `mv -i old new` · `mv -n src dst` (не перезаписывать) |
| `rm` | удаление | coreutils | `rm -i file` · `rm -r -- ./old_dir` |
| `mkdir` | создать каталог | coreutils | `mkdir -p /backup/pg/daily` · `mkdir -m 700 secret` |
| `rmdir` | удалить пустой каталог | coreutils | `rmdir empty_dir` |
| `touch` | создать пустой файл / обновить время | coreutils | `touch flag` · `touch -d '2026-01-01' f` |
| `ln` | жёсткие и символические ссылки | coreutils | `ln -s /srv/data data` · `ln -sfn /opt/app-2.0 /opt/app` |
| `unlink` | удалить одно имя файла | coreutils | `unlink link_name` |
| `stat` | метаданные (права, владелец, времена, inode) | coreutils | `stat file` · `stat -c '%U:%G %a %n' file` |
| `file` | определить тип содержимого | file | `file backup.dump` |
| `tree` | дерево каталогов | ⊕ tree | `tree -L 2 -d /etc/postgresql` |
| `basename` / `dirname` | имя файла / каталог из пути | coreutils | `basename /a/b/c.dt .dt` → `c` · `dirname /a/b/c.dt` → `/a/b` |
| `realpath` / `readlink` | канонический путь / цель ссылки | coreutils | `realpath .` · `readlink -f /usr/bin/psql` |
| `mktemp` | безопасный временный файл/каталог | coreutils | `tmp=$(mktemp -d)` |
| `install` | копирование с назначением прав и владельца | coreutils | `install -d -o postgres -g postgres -m 700 /backup/pg` |
| `dd` | побайтовое копирование блоков | coreutils | `dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress` |
| `truncate` | изменить размер файла | coreutils | `truncate -s 0 app.log` (обнулить, не удаляя) |
| `fallocate` | выделить место под файл | util-linux | `fallocate -l 4G /swapfile` |
| `shred` | затереть содержимое файла | coreutils | `shred -u secret.key` |
| `sync` | сбросить буферы на диск | coreutils | `sync` |
| `rename` | массовое переименование по Perl-выражению | ⊕ rename | `rename -n 's/\.log$/.old/' *.log` (`-n` — только показать) |
| `mkfifo` | именованный канал | coreutils | `mkfifo /tmp/pipe` |
| `namei` | разобрать путь по компонентам с правами | util-linux | `namei -l /var/lib/postgresql/18/main` |
| `du` | занятое место по каталогам | coreutils | `du -sh /var/lib/postgresql` · `du -xh --max-depth=1 /var` |
| `df` | свободное место на ФС | coreutils | `df -hT` · `df -i` (inode) |
| `ncdu` | интерактивный анализ занятого места | ⊕ ncdu | `ncdu -x /` |
| `lsattr` / `chattr` | атрибуты ext4 (immutable и др.) | e2fsprogs | `chattr +i /etc/resolv.conf` · `lsattr /etc/resolv.conf` |
| `getfacl` / `setfacl` | POSIX ACL | ⊕ acl | `setfacl -m u:usr1cv8:rx /backup` · `getfacl /backup` |
| `mc` | файловый менеджер Midnight Commander | ⊕ mc | `mc` |

```bash
# Топ-10 самых «тяжёлых» каталогов на корневой ФС
sudo du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -n 10
# Резервная копия конфига перед правкой
sudo cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%F)
```

## 2. Просмотр и обработка текста

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `cat` | вывести файл(ы) | coreutils | `cat /etc/os-release` · `cat -A f` (показать `^M`, табы, концы строк) |
| `tac` | вывести строки в обратном порядке | coreutils | `tac app.log` |
| `nl` | пронумеровать строки | coreutils | `nl -ba script.sh` |
| `head` | начало файла | coreutils | `head -n 20 f` · `head -c 1M f` |
| `tail` | конец файла, слежение | coreutils | `tail -n 100 f` · `tail -F /var/log/syslog` |
| `less` | постраничный просмотр | less | `less +F app.log` (как `tail -f`) · `less -SN file` |
| `more` | простой пейджер | util-linux | `more file` |
| `wc` | счёт строк/слов/байт | coreutils | `wc -l file` |
| `sort` | сортировка | coreutils | `sort -h sizes.txt` · `sort -t: -k3,3n /etc/passwd` · `sort -u` |
| `uniq` | схлопнуть повторы (после `sort`) | coreutils | `uniq -c` |
| `cut` | вырезать поля/символы | coreutils | `cut -d: -f1,7 /etc/passwd` |
| `paste` | склеить строки/файлы | coreutils | `paste -sd, list.txt` |
| `join` | соединить два файла по ключу | coreutils | `join a.txt b.txt` |
| `tr` | замена/удаление символов | coreutils | `tr -d '\r' < win.txt > unix.txt` |
| `sed` | потоковый редактор | sed | `sed -n '10,20p' f` · `sed -i.bak 's/old/new/g' f` |
| `awk` | обработка колонок | mawk / gawk | `awk -F: '$3>=1000{print $1}' /etc/passwd` |
| `grep` | поиск строк по шаблону | grep | `grep -rn 'listen_addresses' /etc/postgresql` · `grep -c ERROR f` |
| `egrep` / `fgrep` | устаревшие формы; пишите `grep -E` / `grep -F` | grep | `grep -F 'a.b[0]' f` (буквальная строка) · `grep -E 'err(or)?s?:' f` |
| `rg` | быстрый рекурсивный поиск (ripgrep) | ⊕ ripgrep | `rg -n 'shared_buffers' /etc` |
| `column` | выровнять в таблицу | bsdextrautils | `column -t -s: /etc/passwd` |
| `fold` / `fmt` | перенос длинных строк | coreutils | `fold -w 80 f` |
| `expand` / `unexpand` | табы ↔ пробелы | coreutils | `expand -t4 f` |
| `rev` | перевернуть строки посимвольно | util-linux | `rev f` |
| `split` | разбить файл на части | coreutils | `split -b 1G -d big.dump big.dump.part_` |
| `csplit` | разбить по шаблону | coreutils | `csplit f '/^---$/' '{*}'` |
| `comm` | сравнить два отсортированных файла | coreutils | `comm -12 a b` (общие строки) |
| `diff` | различия файлов/каталогов | diffutils | `diff -u old new` · `diff -r dir1 dir2` |
| `sdiff` / `cmp` | сравнение бок о бок / побайтно | diffutils | `cmp a.bin b.bin` |
| `patch` | применить diff | patch | `patch -p1 < fix.diff` |
| `tee` | писать stdin одновременно в файл и в stdout | coreutils | `sudo tee -a /etc/hosts` (дописать; пример с конвейером — в блоке ниже) |
| `xargs` | собрать аргументы из stdin | findutils | `xargs -0 -n1 -P4 gzip` |
| `iconv` | перекодировка | libc-bin | `iconv -f cp1251 -t utf-8 in.txt -o out.txt` |
| `dos2unix` / `unix2dos` | концы строк CRLF ↔ LF | ⊕ dos2unix | `dos2unix script.sh` |
| `strings` | печатные строки из бинарника | binutils (⊕ в 24.04) | `strings -n 8 file` |
| `hexdump` / `xxd` / `od` | шестнадцатеричный дамп | bsdextrautils / xxd / coreutils | `hexdump -C -n 64 f` · `xxd -l 64 f` · `od -c f` |
| `base64` | кодирование Base64 | coreutils | `base64 -w0 f` · `base64 -d f.b64` |
| `jq` | обработка JSON | jq (⊕ в 22.04) | `jq -r '.version' f.json` · `jq '.[].name' f.json` |
| `yq` | обработка YAML | ⊕ yq | `yq '.network' /etc/netplan/50-cloud-init.yaml` |
| `envsubst` | подстановка переменных окружения в шаблон | gettext-base | `envsubst < tpl.conf > out.conf` |
| `echo` / `printf` | вывод текста | bash | `printf '%s\n' "$PATH"` |
| `seq` | последовательность чисел | coreutils | `seq -w 1 10` |
| `shuf` | случайная перестановка/выбор | coreutils | `shuf -n1 list.txt` |
| `numfmt` | человекочитаемые числа | coreutils | `numfmt --to=iec 1073741824` |
| `expr` / `bc` | арифметика | coreutils / bc | `expr 2 + 3` · `bc <<< 'scale=2; 8192/3'` |
| `yes` | бесконечно печатать строку | coreutils | `yes n` |
| `nano` | простой редактор | nano | `nano -l +120 file` (нумерация, перейти к строке 120) |
| `vim` / `vi` / `view` | редактор Vim (`view` — только чтение) | vim / vim-tiny | `vim +120 file`; выход `:wq`, без сохранения `:q!` |
| `vimdiff` | сравнение файлов в Vim | vim | `vimdiff a.conf b.conf` |
| `ed` | строчный редактор | ed | `ed file` |
| `zcat` / `zless` / `zgrep` | работа с `.gz` без распаковки | gzip | `zgrep -i error /var/log/syslog.2.gz` |
| `pv` | индикатор прогресса при чтении файла/потока | ⊕ pv | `pv big.dump > /mnt/copy/big.dump` |
| `ts` / `sponge` | метки времени к строкам stdin / запись результата «в тот же файл» | ⊕ moreutils | `ts '%F %T' < in.log` |
| `batcat` | `cat` с подсветкой | ⊕ bat | `batcat file.yaml` |

```bash
# Показать конфиг без комментариев и пустых строк
grep -Ev '^\s*(#|$)' /etc/postgresql/18/main/postgresql.conf
# Добавить строку в файл, принадлежащий root («sudo echo … >> файл» не сработает)
echo '192.168.1.10 srv1c' | sudo tee -a /etc/hosts
# Топ-10 IP по числу строк в логе
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head
# Заменить параметр в файле, сохранив копию .bak
sudo sed -i.bak 's/^#\?max_connections.*/max_connections = 500/' /etc/postgresql/18/main/postgresql.conf
# Последние 200 строк лога и слежение дальше
tail -n 200 -F /var/log/postgresql/postgresql-18-main.log
```

## 3. Поиск и справка

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `find` | поиск файлов по имени, типу, времени, размеру, владельцу | findutils | `find /var/log -type f -name '*.log' -mtime +30` · `find / -xdev -type f -size +1G` |
| `locate` / `updatedb` | мгновенный поиск по базе имён | ⊕ plocate | `sudo updatedb && locate pg_hba.conf` |
| `grep -r` | поиск по содержимому | grep | `grep -rIl 'usr1cv8' /etc` |
| `which` | путь к исполняемому файлу в `PATH` | debianutils | `which -a psql` |
| `whereis` | бинарник, man и исходники | util-linux | `whereis rsync` |
| `type` / `command -v` | чем является имя (alias, builtin, файл) | bash | `type -a ls` · `command -v rac` |
| `man` | справочные страницы | man-db | `man 5 crontab` · `man -k partition` |
| `apropos` / `whatis` | поиск по описаниям man / одна строка о команде | man-db | `apropos lvm` · `whatis ss` |
| `info` | документация GNU info | info | `info coreutils` |
| `help` | справка по встроенным командам bash | bash | `help test` · `help -s read` |
| `tldr` | краткие примеры к командам | ⊕ tealdeer (или tldr) | `tldr tar` |
| `fdfind` | удобная замена `find` (fd) | ⊕ fd-find | `fdfind -e conf . /etc` |
| `apt-file` | в каком пакете (в т. ч. неустановленном) лежит файл | ⊕ apt-file | `sudo apt-file update && apt-file search bin/pg_config` |
| `dpkg -S` / `dpkg -L` | какой установленный пакет владеет файлом / файлы пакета | dpkg | `dpkg -S /usr/bin/psql` · `dpkg -L postgresql-common` |

```bash
# Файлы старше 14 дней: сначала посмотреть, потом удалить
find /backup/pg -type f -name '*.dump' -mtime +14 -print
find /backup/pg -type f -name '*.dump' -mtime +14 -delete
# Что изменилось в /etc за последние сутки
sudo find /etc -type f -mtime -1 -ls
# Выполнить команду над найденным (безопасно для пробелов в именах)
find . -type f -name '*.log' -print0 | xargs -0 gzip -9
# Файлы, принадлежащие несуществующим пользователям
sudo find / -xdev \( -nouser -o -nogroup \) -print 2>/dev/null
```

## 4. Права и пользователи

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `chmod` | права доступа | coreutils | `chmod 640 f` · `chmod u+x script.sh` · `chmod -R u=rwX,g=rX,o= dir` |
| `chown` | владелец и группа | coreutils | `chown postgres:postgres /backup/pg` · `chown -R usr1cv8:grp1cv8 /srv/1c` |
| `chgrp` | группа-владелец | coreutils | `chgrp grp1cv8 file` |
| `umask` | маска прав для новых файлов | bash | `umask` · `umask 027` |
| `id` | uid, gid и группы пользователя | coreutils | `id usr1cv8` |
| `whoami` / `logname` | текущий / исходный (вошедший) пользователь | coreutils | `whoami` |
| `who` / `w` / `users` | кто сейчас в системе и что делает | coreutils / procps | `w` · `who -b` (время загрузки) |
| `groups` | группы пользователя | coreutils | `groups postgres` |
| `useradd` | создать пользователя (низкоуровнево) | passwd | `useradd -m -s /bin/bash -G sudo ivan` |
| `adduser` | создать пользователя интерактивно; добавить в группу | adduser | `adduser ivan` · `adduser ivan sudo` |
| `usermod` | изменить учётную запись | passwd | `usermod -aG docker ivan` · `usermod -L ivan` (блокировка) |
| `userdel` / `deluser` | удалить пользователя | passwd / adduser | `deluser --remove-home ivan` |
| `groupadd` / `addgroup` | создать группу | passwd / adduser | `groupadd -g 1500 backup_ops` |
| `groupmod` / `groupdel` / `delgroup` | изменить / удалить группу | passwd / adduser | `groupmod -n newname oldname` |
| `gpasswd` | членство в группе | passwd | `gpasswd -a ivan sudo` · `gpasswd -d ivan sudo` |
| `passwd` | пароль, блокировка, статус | passwd | `passwd ivan` · `passwd -l ivan` · `passwd -S ivan` |
| `chpasswd` | пакетная смена паролей (строки `логин:пароль` из stdin) | passwd | `chpasswd < users.txt` |
| `chage` | срок действия пароля | passwd | `chage -l ivan` · `chage -M 90 ivan` |
| `chsh` / `chfn` | оболочка / сведения о пользователе | passwd | `chsh -s /usr/sbin/nologin svc` |
| `pwck` / `grpck` | проверка целостности `/etc/passwd`, `/etc/group` | passwd | `sudo pwck -r` |
| `vipw` / `vigr` | безопасная правка passwd/group с блокировкой | passwd | `sudo vipw` |
| `su` | войти под другим пользователем | util-linux | `su - postgres` |
| `sudo` | выполнить команду от root/другого пользователя | sudo (26.04: sudo-rs) | `sudo -u postgres psql` · `sudo -i` · `sudo -l` · `sudo -k` |
| `sudoedit` | править файл через sudo во временной копии | sudo | `sudoedit /etc/hosts` |
| `visudo` | править sudoers с проверкой синтаксиса | sudo | `sudo visudo -f /etc/sudoers.d/admins` · `sudo visudo -c` |
| `run0` | альтернатива sudo из systemd (есть в 26.04, systemd ≥ 256) | systemd | `run0 -u postgres psql` |
| `runuser` | выполнить от пользователя (только для root, без пароля) | util-linux | `runuser -u postgres -- psql -c 'select 1'` |
| `newgrp` / `sg` | сменить активную группу / выполнить команду с группой | login | `newgrp docker` |
| `getent` | запрос к базам NSS (passwd, group, hosts…) | libc-bin | `getent passwd usr1cv8` · `getent group sudo` |
| `last` / `lastb` | история входов / неудачные попытки | util-linux (22.04/24.04); в 26.04 `last` — пакет ⊕ `wtmpdb` (`/usr/bin/last`), `lastb` отсутствует | `last -n 20` · `sudo lastb -n 20` (22.04/24.04) · в 26.04 неудачные входы: `journalctl -u ssh -g 'Failed password' --since today` |
| `lastlog` / `lastlog2` | последний вход каждого пользователя | login (22.04/24.04) / ⊕ lastlog2 (26.04) | `lastlog -u ivan`; в 26.04 — `sudo apt install lastlog2` → `lastlog2 -u ivan` (в манифесте серверного образа 26.04.1 пакета `lastlog2` нет, есть только библиотека `liblastlog2-2`) |
| `faillock` | счётчик неудачных входов (pam_faillock) | libpam-modules-bin | `faillock --user ivan` · `faillock --user ivan --reset` |
| `loginctl` | сеансы и пользователи logind | systemd | `loginctl list-sessions` · `loginctl terminate-user ivan` |
| `mkpasswd` | сгенерировать хэш пароля | ⊕ whois | `mkpasswd -m sha-512` |

```bash
# Типовые права: 644 файл, 600 секрет, 755 каталог/скрипт, 700 приватный каталог
chmod 600 ~/.ssh/authorized_keys ~/.pgpass;  chmod 700 ~/.ssh
# X (заглавная) — «исполнение только каталогам и уже исполняемым файлам»
sudo chmod -R u=rwX,g=rX,o= /srv/share
# SGID на каталоге: новые файлы наследуют группу каталога
sudo chmod g+s /srv/share
# Что разрешено пользователю через sudo
sudo -l -U ivan
# Выдать право перезапускать сервер 1С без пароля (файл в /etc/sudoers.d/, правка только через visudo)
#   ivan ALL=(root) NOPASSWD: /usr/bin/systemctl restart srv1cv8-8.3.27.1688@default
# Пишите ТОЧНОЕ имя юнита. Шаблон «srv1cv8-*» плох дважды:
#   - в классическом sudo (22.04/24.04) «*» в аргументах совпадает и с пробелами, т. е. разрешит дописать
#     к команде другие юниты (systemctl restart srv1cv8-x ssh);
#   - в sudo-rs (26.04) шаблон внутри аргумента не поддерживается вовсе — правило просто не сработает.
```

Служебные учётные записи стенда: `postgres` (владелец кластера PostgreSQL), `usr1cv8` и группа `grp1cv8` (сервер 1С), `www-data` (Apache/nginx).

## 5. Пакеты (APT, dpkg, snap)

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `apt` | менеджер пакетов для интерактивной работы | apt | `sudo apt update` · `sudo apt full-upgrade` · `apt install pkg` · `apt list --upgradable` · `apt show pkg` · `apt search regex` |
| `apt-get` | то же для скриптов (стабильный интерфейс) | apt | `apt-get -y install pkg` · `apt-get -s dist-upgrade` (симуляция) · `apt-get install -f` |
| `apt-cache` | запросы к кэшу пакетов | apt | `apt-cache policy postgresql-18` · `apt-cache madison pkg` · `apt-cache rdepends pkg` |
| `apt-mark` | заморозка версий, пометки auto/manual | apt | `sudo apt-mark hold postgresql-18` · `apt-mark showhold` · `apt-mark unhold pkg` |
| `apt-config` | показать действующую конфигурацию APT | apt | `apt-config dump` |
| `apt-key` | (устарела) ключи репозиториев; **в 26.04 удалена** | apt | замена: ключ в `/etc/apt/keyrings/имя.gpg` + поле `Signed-By:` в `.sources` |
| `add-apt-repository` | подключить PPA / компонент | software-properties-common | `sudo add-apt-repository universe` · `add-apt-repository ppa:user/name` |
| `dpkg` | низкоуровневая работа с `.deb` | dpkg | `dpkg -i pkg.deb` · `dpkg -l 'postgres*'` · `dpkg -s pkg` · `sudo dpkg --configure -a` |
| `dpkg-query` | запросы к базе установленных пакетов | dpkg | `dpkg-query -W -f='${Package} ${Version}\n' 'postgresql*'` |
| `dpkg-deb` | содержимое файла `.deb` | dpkg | `dpkg-deb -c pkg.deb` · `dpkg-deb -x pkg.deb dir/` |
| `dpkg-reconfigure` | заново настроить пакет (debconf) | debconf | `sudo dpkg-reconfigure tzdata` · `sudo dpkg-reconfigure locales` |
| `debconf-show` / `debconf-set-selections` | показать / предзадать ответы debconf | debconf | `sudo debconf-show postfix` |
| `snap` | snap-пакеты | snapd | `snap list` · `sudo snap install lxd` · `sudo snap refresh` |
| `unattended-upgrade` | автоматическая установка обновлений безопасности | unattended-upgrades | `sudo unattended-upgrade --dry-run --debug` |
| `do-release-upgrade` | переход на следующий выпуск Ubuntu | ubuntu-release-upgrader-core | `sudo do-release-upgrade -c` (только проверить наличие) |
| `pro` | Ubuntu Pro: ESM, Livepatch, статус безопасности | ubuntu-pro-client | `pro status` · `pro security-status` · `sudo pro attach ТОКЕН` |
| `update-alternatives` | выбор реализации по умолчанию (editor и т. п.) | dpkg | `sudo update-alternatives --config editor` |
| `needrestart` | какие сервисы/ядро требуют перезапуска после обновлений | needrestart | `sudo needrestart -r l` (только показать) |
| `lsb_release` | версия дистрибутива | lsb-release | `lsb_release -a` |
| `aptitude` | альтернативный менеджер с TUI | ⊕ aptitude | `aptitude search '~i postgres'` |
| `gdebi` | установить `.deb` с зависимостями | ⊕ gdebi-core | проще: `sudo apt install ./pkg.deb` |
| `debsums` | сверить файлы пакетов с контрольными суммами | ⊕ debsums | `sudo debsums -c` |

```bash
sudo apt update && apt list --upgradable        # что обновится
sudo apt full-upgrade && sudo apt autoremove --purge
sudo apt install ./postgresql-17_17.5-1.1C_amd64.deb   # локальный .deb с подтягиванием зависимостей (имя файла — пример)
sudo apt-mark hold postgresql-17 postgresql-client-17 libpq5   # не дать обновлению заменить сборку СУБД (и её libpq5)
apt-mark showhold                                      # что заморожено
apt-cache policy postgresql-17                         # откуда и какая версия будет установлена
less /var/log/apt/history.log                          # история операций APT
apt history-list                                       # то же в APT 3.1+ (26.04); есть history-info/undo/redo/rollback
#   history-* перечислены в примечаниях к выпуску 26.04; в man apt(8) версии 3.2.0 их описания нет
#   (⚠ не подтверждено: точный синтаксис аргументов history-info/undo/redo/rollback — сверить на сервере)
apt why ПАКЕТ; apt why-not ПАКЕТ                       # APT 3.x (26.04): почему пакет установлен / почему не может быть установлен
apt list --installed 'postgresql*'                     # установленные пакеты по шаблону
apt-get download ПАКЕТ; apt changelog ПАКЕТ            # скачать .deb в текущий каталог / журнал изменений пакета
dpkg --get-selections > pkgs.txt                       # список установленных пакетов (для переноса на другой сервер)
sudo dpkg -V postgresql-common                         # сверить файлы пакета с базой dpkg (изменённые конфиги помечаются)
sudo apt-get clean                                     # очистить кэш скачанных .deb (/var/cache/apt/archives)
zgrep -hE ' (install|upgrade|remove) ' /var/log/dpkg.log* | tail -n 30
[ -f /var/run/reboot-required ] && cat /var/run/reboot-required.pkgs   # нужна ли перезагрузка
```

## 6. Сервисы, systemd и планировщики

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `systemctl` | управление юнитами systemd | systemd | `systemctl status ssh` · `sudo systemctl restart apache2` · `sudo systemctl enable --now chrony` · `systemctl --failed` |
| `systemctl` (списки) | обзор юнитов и таймеров | systemd | `systemctl list-units --type=service --state=running` · `systemctl list-unit-files --state=enabled` · `systemctl list-timers` |
| `systemctl` (юнит-файлы) | просмотр и переопределение | systemd | `systemctl cat ssh` · `sudo systemctl edit ИМЯ` (drop-in) · `sudo systemctl daemon-reload` · `systemctl show -p MainPID,LimitNOFILE ИМЯ` |
| `systemctl` (прочее) | маскирование, сигналы, цели | systemd | `systemctl mask ИМЯ` · `systemctl kill -s HUP ИМЯ` · `systemctl reset-failed` · `systemctl get-default` · `systemctl link /путь/x.service` |
| `journalctl` | чтение журнала systemd | systemd | см. раздел 17 |
| `systemd-analyze` | анализ загрузки и проверка юнитов | systemd | `systemd-analyze blame` · `systemd-analyze verify x.service` · `systemd-analyze calendar 'Mon..Fri 02:30'` |
| `systemd-run` | запустить команду временным юнитом (с лимитами / по таймеру) | systemd | `sudo systemd-run --unit=bk -p MemoryMax=2G /usr/local/bin/backup.sh` |
| `systemd-cgls` / `systemd-cgtop` | дерево cgroup / нагрузка по cgroup | systemd | `systemd-cgtop -m` |
| `systemd-tmpfiles` | создать/очистить каталоги по правилам `tmpfiles.d` | systemd | `sudo systemd-tmpfiles --create` |
| `systemd-escape` | экранировать путь в имя юнита | systemd | `systemd-escape -p /mnt/data` → `mnt-data` |
| `systemd-delta` | показать переопределённые юниты и конфиги | systemd | `systemd-delta --type=extended` |
| `systemd-inhibit` | запретить выключение/сон на время команды | systemd | `systemd-inhibit --what=shutdown ./backup.sh` |
| `systemd-cat` | направить вывод команды в журнал | systemd | `systemd-cat -t backup ./backup.sh` |
| `systemd-detect-virt` | определить гипервизор или контейнер | systemd | `systemd-detect-virt` → `microsoft` (Hyper-V), `vmware`, `oracle` (VirtualBox), `kvm` |
| `hostnamectl` | имя хоста и сведения об ОС | systemd | `hostnamectl` · `sudo hostnamectl set-hostname srv1c` |
| `busctl` | диагностика D-Bus | systemd | `busctl list` |
| `coredumpctl` | список и разбор дампов памяти | ⊕ systemd-coredump | `coredumpctl list` · `coredumpctl info PID` |
| `service` | совместимость со старым синтаксисом SysV | init-system-helpers | `sudo service ssh status` |
| `update-rc.d` | (устар.) автозапуск SysV-скриптов; 26.04 — последний выпуск с их поддержкой | init-system-helpers | вместо этого `systemctl enable` |
| `crontab` | расписание cron пользователя | cron | `crontab -e` · `crontab -l` · `sudo crontab -u postgres -l` |
| `run-parts` | выполнить все скрипты каталога (так работают `/etc/cron.daily`) | debianutils | `run-parts --test /etc/cron.daily` |
| `at` / `atq` / `atrm` / `batch` | одноразовое отложенное задание | ⊕ at | `at 03:00 -f job.sh` · `atq` · `atrm 5` |
| `anacron` | периодические задания для непостоянно включённых машин | ⊕ anacron | `anacron -T` (проверить anacrontab) |

```bash
# Сервисы стенда 1С + PostgreSQL
systemctl status postgresql@18-main srv1cv8-8.3.27.1688@default apache2 --no-pager
systemctl is-active postgresql@18-main; systemctl is-enabled postgresql@18-main   # коротко: работает ли и включён ли автозапуск
systemctl list-units 'srv1cv8*' 'ras*' 'postgres*' --all                          # найти точные имена юнитов 1С и СУБД
sudo systemctl restart srv1cv8-8.3.27.1688@default
# Переопределить параметры юнита, не трогая исходный файл
sudo systemctl edit postgresql@18-main      # создаст /etc/systemd/system/postgresql@18-main.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart postgresql@18-main
# crontab: минута час день месяц день_недели команда
# 30 2 * * *  /usr/local/bin/pg_backup.sh >> /var/log/pg_backup.log 2>&1
# Таймеры systemd вместо cron: проверить выражение и увидеть ближайшие срабатывания
systemd-analyze calendar --iterations=3 '*-*-* 02:30:00'
```

## 7. Процессы

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `ps` | снимок процессов | procps | `ps aux` · `ps -ef --forest` · `ps -u usr1cv8 -o pid,rss,etime,cmd` · `ps -eo pid,user,%cpu,%mem,rss,cmd --sort=-%mem` |
| `top` | интерактивный монитор процессов | procps | `top -c`; клавиши: `1` — по ядрам, `M`/`P` — сортировка по памяти/CPU, `H` — потоки, `k` — сигнал |
| `htop` | удобный монитор с деревом и фильтрами | htop | `htop -u postgres` (F5 — дерево, F4 — фильтр, F9 — сигнал) |
| `pgrep` / `pkill` | найти / послать сигнал по имени или командной строке | procps | `pgrep -af rphost` · `pkill -TERM -f backup.sh` |
| `kill` | послать сигнал процессу | bash / procps | `kill PID` (TERM) · `kill -HUP PID` · `kill -l` |
| `killall` | сигнал всем процессам с данным именем | psmisc | `killall -TERM soffice.bin` |
| `pidof` | PID по имени программы | procps / sysvinit-utils | `pidof ragent` |
| `pstree` | дерево процессов | psmisc | `pstree -ap` · `pstree -p postgres` (процессы пользователя) |
| `nice` / `renice` | приоритет CPU при запуске / на ходу | coreutils / bsdutils | `nice -n 10 gzip big.dump` · `renice -n 5 -p PID` |
| `ionice` | приоритет ввода-вывода | util-linux | `ionice -c2 -n7 rsync -a src/ dst/` · `ionice -c3 -p PID` |
| `nohup` | запуск, устойчивый к закрытию терминала | coreutils | `nohup ./long.sh > long.log 2>&1 &` |
| `setsid` | запустить в новой сессии | util-linux | `setsid ./daemon.sh` |
| `timeout` | ограничить время выполнения | coreutils | `timeout 30s curl -sS http://localhost/` · `timeout -s KILL 5m cmd` |
| `watch` | периодически выполнять команду и показывать вывод | procps | `watch -n 2 -d 'df -h'` |
| `time` | измерить время (ключевое слово bash) и ресурсы (`/usr/bin/time`) | bash / time | `time pg_dump -Fc db -f db.dump` · `/usr/bin/time -v cmd` |
| `sleep` | пауза | coreutils | `sleep 30` |
| `uptime` | время работы и load average | procps | `uptime` |
| `pmap` | карта памяти процесса | procps | `sudo pmap -x PID` |
| `pwdx` | рабочий каталог процесса | procps | `sudo pwdx PID` |
| `lsof` | открытые файлы и сокеты | lsof | `sudo lsof -i :1541` · `sudo lsof -p PID` · `sudo lsof +L1` (удалённые, но ещё открытые файлы) |
| `fuser` | кто использует файл/ФС/порт | psmisc | `sudo fuser -vm /mnt/data` |
| `taskset` | привязка к ядрам CPU | util-linux | `taskset -cp PID` |
| `chrt` | политика планирования реального времени | util-linux | `chrt -p PID` |
| `prlimit` | лимиты ресурсов процесса | util-linux | `prlimit --pid PID` · `sudo prlimit --pid PID --nofile=65536:65536` |
| `flock` | запуск с файловой блокировкой (защита от параллельных копий) | util-linux | `flock -n /run/lock/bk.lock /usr/local/bin/backup.sh` |
| `tmux` | терминальный мультиплексор | tmux | `tmux new -s work` · `tmux attach -t work` (отсоединиться: Ctrl-b d) |
| `screen` | терминальный мультиплексор | screen | `screen -S work` · `screen -r work` (отсоединиться: Ctrl-a d) |
| `byobu` | надстройка над tmux/screen | byobu (⊕ в 26.04) | `byobu` |
| `env` / `printenv` | окружение: запустить с изменённым / показать | coreutils | `env -i PATH=/usr/bin cmd` · `printenv PATH` |
| `nproc` | число доступных ядер | coreutils | `nproc` |
| `ipcs` / `ipcrm` | разделяемая память, семафоры, очереди SysV | util-linux | `ipcs -m` |
| `lslocks` | активные файловые блокировки | util-linux | `sudo lslocks` |
| `lsns` / `nsenter` / `unshare` | пространства имён: список / войти / создать | util-linux | `sudo nsenter -t PID -n ss -tlnp` |
| `stdbuf` | управление буферизацией вывода в конвейере | coreutils | `stdbuf -oL cmd` |
| `script` | записать терминальную сессию в файл | bsdutils | `script -a session.log` |
| `numactl` | NUMA: топология и привязка | numactl (⊕ в 22.04) | `numactl --hardware` |
| `choom` | показать / изменить OOM-оценку процесса (`oom_score_adj`) | util-linux | `choom -p PID` · `sudo choom -p PID -n -500` (реже выбирать жертвой OOM-killer) |

```bash
# Топ-10 процессов по памяти (RSS) и по CPU
ps -eo pid,user,%cpu,%mem,rss,etime,cmd --sort=-rss | head -n 11
ps -eo pid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head -n 11
# Процессы сервера 1С и их память
ps -u usr1cv8 -o pid,ppid,rss,etime,cmd --sort=-rss
# Лимиты и состояние конкретного процесса
cat /proc/PID/limits;  grep -E 'VmRSS|Threads' /proc/PID/status
# Корректное завершение: сначала TERM, KILL только если не помогло
kill PID;  sleep 10;  kill -0 PID 2>/dev/null && kill -KILL PID
```

Сигналы: `TERM` (15, вежливое завершение, по умолчанию), `INT` (2, Ctrl-C), `HUP` (1, часто «перечитать конфиг»), `QUIT` (3), `KILL` (9, немедленно, без очистки), `STOP`/`CONT` (приостановить/продолжить), `USR1`/`USR2` (по смыслу программы).

## 8. Мониторинг CPU, памяти, диска и сети

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `uptime` | load average за 1/5/15 минут | procps | `uptime` (сравнивать с `nproc`) |
| `free` | память и swap | procps | `free -h` · `free -m -s 5` (колонка `available` — реально доступно) |
| `vmstat` | память, swap, блочный ввод-вывод, CPU по интервалам | procps | `vmstat 1 10` · `vmstat -w 5` |
| `top` / `htop` | процессы в реальном времени | procps / htop | см. раздел 7 |
| `mpstat` | загрузка по каждому ядру | sysstat | `mpstat -P ALL 1 5` |
| `iostat` | нагрузка на диски: await, util, очередь | sysstat | `iostat -xz 1` · `iostat -dxm 5 3` |
| `pidstat` | CPU / память / диск по процессам | sysstat | `pidstat -d 1` (ввод-вывод) · `pidstat -r -p PID 5` · `pidstat -u -C postgres 1` |
| `sar` | история и текущие счётчики (CPU, память, сеть, диск) | sysstat | `sar -u 1 5` · `sar -r` · `sar -n DEV 1 5` · `sar -d -p 1 5` · `sar -q` |
| `iotop` | ввод-вывод по процессам | ⊕ iotop (или iotop-c) | `sudo iotop -oPa` |
| `atop` | монитор с записью истории | ⊕ atop | `atop 5` · `atop -r /var/log/atop/atop_20261010` |
| `btop` / `glances` / `nmon` | наглядные «комбайны» мониторинга | ⊕ btop / glances / nmon | `btop` |
| `iftop` / `nload` / `nethogs` | трафик: по соединениям / по интерфейсу / по процессам | ⊕ iftop / nload / nethogs | `sudo iftop -i eth0 -nP` · `sudo nethogs eth0` |
| `slabtop` | кэши ядра (slab) | procps | `sudo slabtop -o` |
| `smem` | память процессов с учётом разделяемой (PSS) | ⊕ smem | `sudo smem -tk -s pss` |
| `numastat` | распределение памяти по NUMA-узлам | numactl | `numastat -p postgres` |
| `perf` | профилировщик ядра и приложений | linux-tools-common + linux-tools-$(uname -r) | `sudo perf top` · `sudo perf record -g -p PID -- sleep 30` → `sudo perf report` |
| `bpftrace` | трассировка eBPF | bpftrace | `sudo bpftrace -l 'tracepoint:syscalls:*openat*'` |
| `biolatency-bpfcc`, `execsnoop-bpfcc`, `opensnoop-bpfcc`, `tcpconnect-bpfcc` | готовые eBPF-инструменты BCC (все имеют суффикс `-bpfcc`) | bpfcc-tools | `sudo biolatency-bpfcc 5 1` · `sudo opensnoop-bpfcc -p PID` |
| `landscape-sysinfo` | сводка, которую показывает MOTD при входе | landscape-common | `landscape-sysinfo` |

```bash
# «60 секунд» первичной диагностики
uptime; nproc                       # нагрузка относительно числа ядер
dmesg -T --level=err,warn | tail    # ошибки ядра, OOM-killer, диски
vmstat 1 5                          # r > nproc — очередь на CPU; si/so > 0 — свопинг; wa — ожидание диска
mpstat -P ALL 1 3                   # одно ядро на 100 % — однопоточный затык
pidstat 1 3                         # кто грузит CPU
iostat -xz 1 3                      # %util ~100 и растущий await — диск не справляется
free -h                             # available мало + swap растёт — нехватка памяти
sar -n DEV 1 3                      # сетевые интерфейсы
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io   # PSI: доля времени в ожидании ресурса
journalctl -k -g 'out of memory' --since today   # не убивал ли OOM-killer rphost/postgres
```

История `sar` копится, только если включён сбор: `ENABLED="true"` в `/etc/default/sysstat` и `sudo systemctl enable --now sysstat` (в примечаниях к 24.04 прямо сказано, что sysstat установлен, но часть его сервисов по умолчанию не включена). В 22.04 пакеты `sysstat`, `bpftrace`, `bpfcc-tools`, `trace-cmd`, `linux-tools-*` и `numactl` не предустановлены — в таблице выше для 22.04 считайте их помеченными ⊕.

## 9. Диски, разделы, файловые системы, LVM, RAID

### 9.1. Обзор устройств и разделы

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `lsblk` | дерево блочных устройств | util-linux | `lsblk -f` · `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL` · `lsblk -d -o NAME,ROTA,SIZE` |
| `blkid` | UUID, метки и типы ФС | util-linux | `sudo blkid` · `sudo blkid -s UUID -o value /dev/sdb1` |
| `fdisk` | таблица разделов (MBR/GPT), интерактивно | fdisk | `sudo fdisk -l` · `sudo fdisk /dev/sdb` |
| `sfdisk` | то же для скриптов; бэкап таблицы разделов | fdisk | `sudo sfdisk -d /dev/sda > sda.parttable` |
| `cfdisk` | псевдографический редактор разделов | fdisk | `sudo cfdisk /dev/sdb` |
| `gdisk` / `sgdisk` | GPT: интерактивно / для скриптов | gdisk | `sudo sgdisk -p /dev/sda` · `sudo sgdisk --backup=sda.gpt /dev/sda` |
| `parted` | разметка, в т. ч. неинтерактивно | parted | `sudo parted -l` · `sudo parted -s /dev/sdb mklabel gpt mkpart primary 1MiB 100%` |
| `partprobe` / `partx` | сообщить ядру об изменении таблицы разделов | parted / util-linux | `sudo partprobe /dev/sdb` · `sudo partx -u /dev/sdb` |
| `growpart` | расширить раздел до конца диска | cloud-guest-utils | `sudo growpart /dev/sda 3` (диск и номер — через пробел) |
| `wipefs` | показать / стереть сигнатуры ФС и RAID | util-linux | `sudo wipefs /dev/sdb` (показать) · `sudo wipefs -a /dev/sdb` (**стереть**) |
| `blockdev` | параметры блочного устройства | util-linux | `sudo blockdev --getsize64 /dev/sda` · `sudo blockdev --getra /dev/sda` |
| `udevadm` | события и свойства устройств udev | udev | `udevadm info --query=all --name=/dev/sda` · `sudo udevadm trigger` |
| `lsscsi` | список SCSI/SATA-устройств | ⊕ lsscsi | `lsscsi -s` |
| `rescan-scsi-bus.sh` | пересканировать шину (увидеть новый диск/размер без перезагрузки) | sg3-utils | `sudo rescan-scsi-bus.sh -s` |
| `hdparm` | параметры и тест чтения SATA-диска | hdparm | `sudo hdparm -I /dev/sda` · `sudo hdparm -Tt /dev/sda` |
| `smartctl` | S.M.A.R.T.-диагностика (на физическом железе) | ⊕ smartmontools | `sudo smartctl -a /dev/sda` · `sudo smartctl -H /dev/sda` · `sudo smartctl -t short /dev/sda` |
| `nvme` | управление NVMe | nvme-cli (⊕ в 22.04/24.04) | `sudo nvme list` · `sudo nvme smart-log /dev/nvme0` |
| `losetup` | loop-устройства (образ как диск) | mount | `sudo losetup -fP --show disk.img` · `losetup -a` |
| `findfs` | найти устройство по метке или UUID | util-linux | `sudo findfs LABEL=pgbackup` · `sudo findfs UUID=…` |
| `blkdiscard` | отбросить (TRIM) **все** блоки устройства — данные уничтожаются | util-linux | `sudo blkdiscard /dev/sdX` (только на пустом диске; см. раздел 25) |
| `kpartx` | разделы внутри образа/multipath-устройства | kpartx | `sudo kpartx -av disk.img` |
| `dmsetup` | низкоуровневый device-mapper | dmsetup | `sudo dmsetup ls --tree` |

### 9.2. Файловые системы и монтирование

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `mkfs.ext4` (`mke2fs`) | создать ext4 | e2fsprogs | `sudo mkfs.ext4 -L pgdata /dev/vg_data/pgdata` |
| `mkfs.xfs` | создать XFS | xfsprogs | `sudo mkfs.xfs -L backup /dev/sdc1` |
| `mkfs.vfat` | создать FAT (EFI-раздел, флешки) | dosfstools | `sudo mkfs.vfat -F 32 /dev/sdd1` |
| `mkswap` / `swapon` / `swapoff` | создать / включить / выключить swap | util-linux / mount | `sudo mkswap /swapfile` · `swapon --show` · `sudo swapoff -a` |
| `mount` / `umount` | смонтировать / размонтировать | mount | `sudo mount /dev/sdb1 /mnt/data` · `sudo mount -a` (применить fstab) · `sudo mount -o remount,rw /` · `sudo umount /mnt/data` |
| `findmnt` | что и куда смонтировано; проверка fstab | util-linux | `findmnt -T /var/lib/postgresql` · `sudo findmnt --verify` |
| `mountpoint` | является ли каталог точкой монтирования | util-linux | `mountpoint -q /backup && echo ok` |
| `fsck` / `e2fsck` | проверка ФС (**только размонтированной**) | util-linux / e2fsprogs | `sudo e2fsck -f /dev/sdb1` |
| `tune2fs` / `dumpe2fs` / `e2label` | параметры ext4, метка | e2fsprogs | `sudo tune2fs -l /dev/sda2` · `sudo tune2fs -m 1 /dev/sdb1` (резерв root 1 %) |
| `resize2fs` | изменить размер ext4 (увеличение — онлайн) | e2fsprogs | `sudo resize2fs /dev/ubuntu-vg/ubuntu-lv` |
| `xfs_growfs` / `xfs_info` | увеличить XFS (только онлайн, уменьшить нельзя) / параметры | xfsprogs | `sudo xfs_growfs /mnt/data` · `xfs_info /mnt/data` |
| `xfs_repair` / `xfs_admin` | починка XFS (размонтированной) / метка, UUID | xfsprogs | `sudo xfs_repair /dev/sdc1` |
| `btrfs` | управление Btrfs | btrfs-progs | `sudo btrfs filesystem usage /` |
| `fstrim` | TRIM для SSD и тонких виртуальных дисков | util-linux | `sudo fstrim -av` (регулярно — `fstrim.timer`) |
| `fsfreeze` | заморозить запись в ФС на время снимка | util-linux | `sudo fsfreeze -f /mnt/data` … `sudo fsfreeze -u /mnt/data` |
| `filefrag` / `badblocks` | фрагментация файла / поиск сбойных блоков | e2fsprogs | `sudo filefrag -v file` · `sudo badblocks -sv /dev/sdb` (чтение) |
| `zramctl` | сжатый swap в памяти (zram) | util-linux | `zramctl` |
| `mount -t cifs` | подключить Windows-ресурс (SMB) | cifs-utils | `sudo mount -t cifs //winhost/share /mnt/win -o credentials=/root/.smbcred,uid=usr1cv8,gid=grp1cv8,vers=3.0` |
| `mount -t nfs` / `showmount` | подключить NFS / список экспортов | ⊕ nfs-common | `showmount -e nas` · `sudo mount -t nfs nas:/export /mnt/nas` |
| `exportfs` | управлять экспортами NFS-сервера | ⊕ nfs-kernel-server | `sudo exportfs -ra` |
| `eject` | извлечь съёмный носитель | eject | `sudo eject /dev/sr0` |

### 9.3. LVM

| Команда | Назначение | Примеры (пакет `lvm2`) |
|---|---|---|
| `pvs` / `vgs` / `lvs` | краткая сводка по PV / VG / LV | `sudo pvs` · `sudo vgs` · `sudo lvs -a -o +devices` |
| `pvdisplay` / `vgdisplay` / `lvdisplay` | подробный вывод | `sudo vgdisplay ubuntu-vg` |
| `pvcreate` / `pvremove` | создать / удалить физический том | `sudo pvcreate /dev/sdb` |
| `pvresize` | расширить PV после увеличения раздела | `sudo pvresize /dev/sda3` |
| `pvmove` | перенести данные с одного PV на другой (онлайн) | `sudo pvmove /dev/sdb /dev/sdc` |
| `vgcreate` / `vgremove` | создать / удалить группу томов | `sudo vgcreate vg_data /dev/sdb` |
| `vgextend` / `vgreduce` | добавить / убрать PV из группы | `sudo vgextend ubuntu-vg /dev/sdc` |
| `vgchange` | активация групп томов | `sudo vgchange -ay` |
| `pvscan` / `vgscan` / `lvscan` | пересканировать метаданные | `sudo vgscan` |
| `lvcreate` | создать логический том или снимок | `sudo lvcreate -L 100G -n pgdata vg_data` · `sudo lvcreate -l 100%FREE -n backup vg_data` · `sudo lvcreate -s -L 10G -n pgsnap /dev/vg_data/pgdata` |
| `lvextend` | увеличить LV (`-r` — сразу и ФС) | `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv` · `sudo lvextend -r -L +20G /dev/vg_data/pgdata` |
| `lvreduce` / `lvresize` | уменьшить / изменить размер (ext4 — только размонтировав; XFS уменьшить нельзя) | `sudo lvreduce -r -L 50G /dev/vg_data/tmp` |
| `lvremove` / `lvrename` / `lvchange` | удалить / переименовать / изменить атрибуты | `sudo lvremove /dev/vg_data/pgsnap` |
| `lvconvert` | преобразования: откат к снимку, thin, зеркало | `sudo lvconvert --merge /dev/vg_data/pgsnap` |

### 9.4. RAID, шифрование, SAN, тесты

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `mdadm` | программный RAID | mdadm | `cat /proc/mdstat` · `sudo mdadm --detail /dev/md0` · `sudo mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc` |
| `mdadm` (замена диска) | пометить сбойным, убрать, добавить новый | mdadm | `sudo mdadm /dev/md0 --fail /dev/sdb --remove /dev/sdb` · `sudo mdadm /dev/md0 --add /dev/sdd` |
| `cryptsetup` | шифрование LUKS | cryptsetup | `sudo cryptsetup luksFormat /dev/sdb1` · `sudo cryptsetup open /dev/sdb1 secure` · `sudo cryptsetup close secure` |
| `multipath` | многопутевой доступ к СХД | multipath-tools | `sudo multipath -ll` |
| `iscsiadm` | iSCSI-инициатор | open-iscsi | `sudo iscsiadm -m discovery -t sendtargets -p 10.0.0.5` · `sudo iscsiadm -m node --login` |
| `zpool` / `zfs` | ZFS | ⊕ zfsutils-linux | `zpool status` · `zfs list` |
| `fio` | нагрузочный тест диска | ⊕ fio | см. блок ниже |
| `ioping` | задержка ввода-вывода «как ping» | ⊕ ioping | `ioping -c 10 /var/lib/postgresql` |

```bash
# А. Увеличили диск ВМ в гипервизоре — расширяем корень (стандартная LVM-разметка установщика Ubuntu)
lsblk                                                    # ядро видит новый размер? если нет:
echo 1 | sudo tee /sys/class/block/sda/device/rescan
sudo growpart /dev/sda 3                                 # раздел с LVM
sudo pvresize /dev/sda3
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv   # LV и файловая система за один шаг
df -hT /

# Б. Новый диск под резервные копии
sudo parted -s /dev/sdb mklabel gpt mkpart primary 1MiB 100%
sudo mkfs.ext4 -L pgbackup /dev/sdb1
sudo mkdir -p /backup
echo 'LABEL=pgbackup /backup ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
sudo findmnt --verify && sudo systemctl daemon-reload && sudo mount -a && findmnt /backup

# В. Файл подкачки 4 ГБ (ext4/XFS; на Btrfs файл подкачки создают иначе: btrfs filesystem mkswapfile, btrfs-progs 6.1+)
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
#   если swapon ругается на «holes» — создать файл через dd: sudo dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Г. Тест случайной записи блоками 8k (размер страницы PostgreSQL) — на тестовом файле, не на устройстве!
fio --name=pg8k --filename=/var/lib/postgresql/fio.test --size=2G --rw=randwrite --bs=8k \
    --ioengine=libaio --direct=1 --iodepth=16 --runtime=60 --time_based --group_reporting
rm /var/lib/postgresql/fio.test
```

## 10. Сеть и диагностика

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `ip` | адреса, интерфейсы, маршруты, соседи | iproute2 | `ip -br a` · `ip r` · `ip route get 8.8.8.8` · `ip -s link` · `ip neigh` |
| `ip` (временные изменения до перезагрузки) | адрес / состояние интерфейса | iproute2 | `sudo ip addr add 192.168.1.50/24 dev eth0` · `sudo ip link set eth0 up` |
| `ss` | сокеты и слушающие порты | iproute2 | `sudo ss -tulpn` · `ss -tn 'sport = :5432'` · `ss -s` |
| `ping` | проверка доступности (ICMP) | iputils-ping | `ping -c 4 host` · `ping -M do -s 1472 host` (проверка MTU 1500) |
| `tracepath` | маршрут и MTU по пути | iputils-tracepath | `tracepath -n host` |
| `traceroute` | маршрут (UDP/ICMP/TCP) | ⊕ traceroute | `traceroute -n host` · `sudo traceroute -T -p 1541 host` |
| `mtr` | ping + traceroute в динамике | mtr-tiny | `mtr -rw -c 20 host` |
| `dig` | DNS-запросы | bind9-dnsutils | `dig +short srv1c.example.local` · `dig @192.168.1.1 name A` · `dig -x 192.168.1.10 +short` |
| `nslookup` / `host` | простые DNS-запросы | bind9-dnsutils / bind9-host | `host srv1c` |
| `resolvectl` | состояние systemd-resolved | systemd-resolved | `resolvectl status` · `resolvectl query name` · `sudo resolvectl flush-caches` |
| `getent hosts` | как имя разрешает сама система (с учётом `/etc/hosts`) | libc-bin | `getent hosts srv1c` |
| `hostname` | имя хоста и адреса | hostname | `hostname -f` · `hostname -I` |
| `netplan` | декларативная настройка сети | netplan.io | `sudo netplan try` (откат через 120 с без подтверждения) · `sudo netplan apply` · `sudo netplan get` · `netplan status` |
| `networkctl` | состояние systemd-networkd | systemd | `networkctl status` · `networkctl list` · `sudo networkctl renew eth0` (обновить DHCP) |
| `nmcli` | NetworkManager (на сервере обычно не используется) | ⊕ network-manager | `nmcli device status` |
| `ethtool` | параметры и статистика сетевой карты | ethtool | `sudo ethtool eth0` · `ethtool -i eth0` · `ethtool -S eth0` |
| `bridge` / `tc` | мосты / очереди и шейпинг | iproute2 | `bridge link` · `tc -s qdisc show dev eth0` |
| `nstat` | счётчики стека TCP/IP | iproute2 | `nstat -az 'Tcp*Retrans*'` |
| `ifconfig` / `route` / `netstat` / `arp` | устаревшие; замены: `ip a`, `ip r`, `ss -tulpn`, `ip neigh` | ⊕ net-tools | `netstat -tulpn` ≈ `ss -tulpn` |
| `nc` | проверка TCP/UDP-портов, простой клиент/сервер | netcat-openbsd | `nc -zv -w 3 srv 1541` · `nc -l 9000` |
| `socat` | универсальный релей соединений | ⊕ socat | `socat TCP-LISTEN:8080,fork TCP:10.0.0.5:80` |
| `telnet` | ручная проверка TCP-порта | inetutils-telnet (22.04: telnet) | `telnet srv 1540` |
| `curl` | HTTP(S)-клиент и проверка портов | curl | `curl -I https://site` · `curl -fsSL URL -o file` · `curl -v telnet://srv:1541` |
| `wget` | загрузка файлов | wget | `wget -c URL` (докачка) · `wget -qO- URL` |
| `nmap` | сканер портов | ⊕ nmap | `nmap -Pn -p 1540-1541,1560-1591,5432 srv` |
| `tcpdump` | захват пакетов | tcpdump | `sudo tcpdump -i any -nn port 5432` · `sudo tcpdump -i eth0 -nn -w /tmp/c.pcap host 10.0.0.5 and port 1541` |
| `tshark` | консольный Wireshark | ⊕ tshark | `sudo tshark -i eth0 -f 'port 1541'` |
| `iperf3` | измерение пропускной способности | ⊕ iperf3 | сервер: `iperf3 -s`; клиент: `iperf3 -c srv -t 10 -P 4` |
| `arping` | ARP-проверка, поиск конфликта адресов | ⊕ iputils-arping | `sudo arping -I eth0 -c 3 192.168.1.1` |
| `ipcalc` | расчёт подсетей | ⊕ ipcalc | `ipcalc 192.168.1.10/26` |
| `whois` | сведения о домене/адресе | ⊕ whois | `whois example.com` |
| `wg` | WireGuard | ⊕ wireguard-tools | `sudo wg show` |
| `smbclient` | клиент SMB (проверка Windows-шары) | ⊕ smbclient | `smbclient -L //winhost -U user` |
| `ftp` | FTP-клиент | ftp | `ftp host` |

```bash
ip -br a; ip r; resolvectl status | head -n 20           # адреса, маршруты, DNS
sudo ss -tulpn | grep -E ':(22|80|443|1540|1541|1545|5432)\b'   # слушают ли нужные сервисы и на каких адресах
for p in 1540 1541 1560 5432; do nc -zv -w 3 srv1c "$p"; done    # доступность портов с другого узла
getent hosts "$(hostname)"; hostname -f                  # для 1С важно, чтобы имя сервера разрешалось в его реальный IP, а не в 127.0.1.1
sudo netplan try                                         # применить YAML из /etc/netplan/ с автооткатом
```

## 11. Firewall

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `ufw` | простой интерфейс к netfilter (штатный в Ubuntu, по умолчанию выключен) | ufw | `sudo ufw status verbose` · `sudo ufw allow OpenSSH` · `sudo ufw allow 1560:1591/tcp` · `sudo ufw status numbered` · `sudo ufw delete 3` |
| `ufw` (политики и сервис) | включение, политика по умолчанию, журнал | ufw | `sudo ufw default deny incoming` · `sudo ufw enable` · `sudo ufw reload` · `sudo ufw limit 22/tcp` · `sudo ufw logging on` |
| `nft` | nftables — современный низкоуровневый интерфейс | nftables | `sudo nft list ruleset` · `sudo nft -c -f /etc/nftables.conf` (проверка) · `sudo nft -f /etc/nftables.conf` |
| `iptables` / `ip6tables` | классический синтаксис (в Ubuntu работает поверх nftables) | iptables | `sudo iptables -L -n -v --line-numbers` · `sudo iptables -S` |
| `iptables-save` / `iptables-restore` | выгрузить / загрузить набор правил | iptables | `sudo iptables-save > rules.v4` |
| `iptables-translate` | перевести правило iptables в синтаксис nft | iptables | `iptables-translate -A INPUT -p tcp --dport 22 -j ACCEPT` |
| `netfilter-persistent` | сохранять правила iptables между перезагрузками | ⊕ iptables-persistent | `sudo netfilter-persistent save` |
| `fail2ban-client` | блокировка подбора паролей | ⊕ fail2ban | `sudo fail2ban-client status sshd` · `sudo fail2ban-client set sshd unbanip 1.2.3.4` |
| `conntrack` / `ipset` | таблица соединений / наборы адресов | ⊕ conntrack / ipset | `sudo conntrack -S` |
| `firewall-cmd` | firewalld (в Ubuntu не используется по умолчанию) | ⊕ firewalld | `sudo firewall-cmd --list-all` |

```bash
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH                                            # СНАЧАЛА разрешить SSH, потом enable
sudo ufw allow 80,443/tcp                                         # веб-публикация 1С
sudo ufw allow from 192.168.1.0/24 to any port 1540:1541 proto tcp   # агент и менеджер кластера 1С
sudo ufw allow from 192.168.1.0/24 to any port 1560:1591 proto tcp   # рабочие процессы 1С
sudo ufw allow from 192.168.1.5 to any port 1545 proto tcp           # RAS — только рабочему месту администратора
sudo ufw allow from 192.168.1.20 to any port 5432 proto tcp          # PostgreSQL — только серверу 1С (если СУБД на отдельной машине)
sudo ufw enable && sudo ufw status numbered
```

## 12. SSH и передача файлов

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `ssh` | удалённая оболочка и туннели | openssh-client | `ssh -p 2222 user@host` · `ssh user@host 'uptime'` · `ssh -J bastion user@inner` · `ssh -v user@host` (отладка) |
| `ssh` (туннели) | проброс портов | openssh-client | `ssh -N -L 15432:127.0.0.1:5432 user@host` (локальный 15432 → PostgreSQL на сервере) · `ssh -N -D 1080 user@host` (SOCKS) |
| `sshd` | сервер SSH; проверка конфигурации | openssh-server | `sudo sshd -t` (синтаксис) · `sudo sshd -T` (итоговые значения) |
| `ssh-keygen` | создание и обслуживание ключей | openssh-client | `ssh-keygen -t ed25519 -C 'admin@pc'` · `ssh-keygen -R host` (убрать старый ключ хоста) · `ssh-keygen -lf key.pub` (отпечаток) · `ssh-keygen -p -f key` (сменить пароль ключа) |
| `ssh-copy-id` | установить свой публичный ключ на сервер | openssh-client | `ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host` |
| `ssh-agent` / `ssh-add` | агент ключей | openssh-client | `eval "$(ssh-agent -s)"` · `ssh-add ~/.ssh/id_ed25519` · `ssh-add -l` |
| `ssh-keyscan` | получить публичные ключи хоста | openssh-client | `ssh-keyscan -t ed25519 host >> ~/.ssh/known_hosts` |
| `ssh-import-id` | импорт ключей с GitHub/Launchpad | ssh-import-id | `ssh-import-id gh:username` |
| `scp` | копирование по SSH | openssh-client | `scp -P 2222 file user@host:/tmp/` · `scp -r user@host:/backup/dir .` |
| `sftp` | интерактивная передача файлов по SSH | openssh-client | `sftp user@host` (команды `get`, `put`, `ls`, `lcd`) |
| `rsync` | синхронизация каталогов (локально и по SSH) | rsync | `rsync -avh --progress src/ user@host:/dst/` · `rsync -aHAX --delete --numeric-ids /data/ /mnt/copy/` · `rsync -avn …` (пробный прогон) |
| `sshfs` | смонтировать удалённый каталог по SSH | ⊕ sshfs | `sshfs user@host:/dir /mnt/remote` · `umount /mnt/remote` |
| `autossh` | самовосстанавливающийся SSH-туннель | ⊕ autossh | `autossh -M 0 -N -L 15432:127.0.0.1:5432 user@host` |
| `lftp` / `rclone` | FTP/SFTP-клиент со сценариями / синхронизация с облаками и S3 | ⊕ lftp / rclone | `rclone sync /backup remote:bucket/backup` |

```bash
# Сервис называется ssh (не sshd). Проверить конфиг ДО перезапуска и не закрывать текущую сессию
sudo sshd -t && sudo systemctl restart ssh
# 24.04: sshd запускается через сокет-активацию (ssh.socket); после смены Port/ListenAddress —
# 26.04: механизм тот же — в пакете openssh-server 1:10.2p1 есть и ssh.socket, и sshd-socket-generator
# (проверено по списку файлов пакета); включён ли сокет на конкретном сервере: systemctl is-enabled ssh.socket
# 22.04: сокет-активации по умолчанию нет — достаточно sudo systemctl restart ssh
sudo systemctl daemon-reload && sudo systemctl restart ssh.socket
# scp с OpenSSH 9.0 (24.04+) по умолчанию работает по протоколу SFTP; для очень старых серверов без SFTP: scp -O …
# rsync: косая черта в конце источника = «содержимое каталога»; --delete сначала проверять с -n
rsync -avn --delete /srv/1c/files/ backup@nas:/backups/1c-files/
# С Windows-хоста (PowerShell, встроенный OpenSSH-клиент) на ВМ; имя файла — пример
#   scp C:\dist\setup-full-8.3.27.1688-x86_64.run admin@192.168.56.10:/tmp/
```

## 13. Архивы и сжатие

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `tar` | архиватор (упаковка каталогов, сжатие внешним компрессором) | tar | `tar -czf etc.tar.gz -C / etc` · `tar -xzf a.tar.gz -C /restore` · `tar -tf a.tar.gz` · `tar --zstd -cf a.tar.zst dir` · `tar -xJf a.tar.xz` |
| `gzip` / `gunzip` / `zcat` | сжатие gzip | gzip | `gzip -k file` (оставить исходник) · `gunzip file.gz` · `gzip -t file.gz` (проверка) |
| `zstd` / `unzstd` / `zstdcat` | быстрое сжатие Zstandard, многопоточное | zstd | `zstd -T0 -10 file` · `zstd -d file.zst` · `zstd -t file.zst` |
| `xz` / `unxz` / `xzcat` | максимальное сжатие, медленно | xz-utils | `xz -T0 -6 file` · `xz -d file.xz` |
| `bzip2` / `bunzip2` / `bzcat` | сжатие bzip2 | ⊕ bzip2 | `bzip2 -k file` · `tar -xjf a.tar.bz2` |
| `pigz` | параллельный gzip | ⊕ pigz | `pigz -p 8 file` · `tar -I pigz -cf a.tar.gz dir` |
| `lz4` | сверхбыстрое сжатие | ⊕ lz4 | `lz4 file` · `lz4 -d file.lz4` |
| `zip` / `unzip` | архивы ZIP (дистрибутивы 1С приходят в zip) | ⊕ zip / unzip | `zip -r a.zip dir` · `unzip -l a.zip` · `unzip a.zip -d /tmp/out` |
| `7z` | архивы 7z и многие другие | ⊕ 7zip (в 22.04 — p7zip-full) | `7z a a.7z dir` · `7z x a.7z -o/tmp/out` · `7z l a.7z` |
| `unrar` | распаковка RAR | ⊕ unrar | `unrar x a.rar` |
| `cpio` | архивы cpio (initramfs, rpm) | cpio | `cpio -idmv < archive.cpio` |
| `ar` | архивы ar (внутренности `.deb`) | binutils | `ar x pkg.deb` |
| `zgrep` / `zless` / `zdiff` | поиск / просмотр / сравнение сжатых файлов | gzip | `zgrep -c ERROR app.log.3.gz` |
| `unsquashfs` | распаковка squashfs (snap, live-образы) | squashfs-tools | `unsquashfs -l image.squashfs` |

```bash
# Архив с сохранением прав и владельцев, исключая лишнее; распаковка в указанный каталог
sudo tar --zstd -cpf /backup/etc_$(date +%F).tar.zst --exclude='*.cache' -C / etc
sudo tar --zstd -xpf /backup/etc_2026-10-10.tar.zst -C /restore
tar -tf a.tar.zst | head                 # что внутри, до распаковки
# Многопоточное сжатие с выбором уровня
tar -I 'zstd -T0 -10' -cf files.tar.zst /srv/1c/files
# Копирование каталога «через tar по ssh» с сохранением атрибутов
tar -C /srv -cpf - data | ssh user@host 'tar -C /srv -xpf -'
```

Дампы `pg_dump -Fc` и `-Fd` уже сжаты — повторно жать их архиватором почти бесполезно.

## 14. Ядро и модули

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `uname` | версия ядра и архитектура | coreutils | `uname -r` · `uname -a` |
| `lsmod` | загруженные модули | kmod | `lsmod` |
| `modprobe` | загрузить / выгрузить модуль с зависимостями | kmod | `sudo modprobe nfs` · `sudo modprobe -r nfs` |
| `modinfo` | сведения о модуле | kmod | `modinfo e1000e` · `modinfo -F version hv_netvsc` |
| `insmod` / `rmmod` | низкоуровневая загрузка / выгрузка (обычно хватает `modprobe`) | kmod | `sudo rmmod module` |
| `depmod` | пересобрать карту зависимостей модулей | kmod | `sudo depmod -a` |
| `dmesg` | кольцевой буфер сообщений ядра | util-linux | `sudo dmesg -T` · `sudo dmesg -w` · `sudo dmesg -T --level=err,warn` |
| `sysctl` | параметры ядра на лету | procps | `sysctl -a` · `sysctl vm.swappiness` · `sudo sysctl -w vm.swappiness=10` · `sudo sysctl --system` |
| `update-initramfs` | пересобрать initramfs | initramfs-tools (26.04: dracut) | `sudo update-initramfs -u` · `sudo update-initramfs -u -k all` |
| `lsinitramfs` | содержимое initramfs | initramfs-tools-core | `lsinitramfs /boot/initrd.img-$(uname -r)` |
| `dracut` / `lsinitrd` | генератор initramfs по умолчанию в 26.04 / просмотр образа | dracut-core | `sudo dracut -f` · `sudo dracut -f --regenerate-all` · `sudo lsinitrd` |
| `dkms` | сборка внешних модулей под новые ядра | ⊕ dkms | `dkms status` |
| `getconf` | системные константы | libc-bin | `getconf PAGE_SIZE` · `getconf _NPROCESSORS_ONLN` |
| `mokutil` | Secure Boot и ключи MOK | mokutil (в манифестах 22.04/24.04 нет, в 26.04 есть; при отсутствии — ⊕) | `mokutil --sb-state` |

```bash
cat /proc/cmdline                                   # параметры загрузки текущего ядра
dpkg -l 'linux-image-*' | grep '^ii'                # установленные ядра
sysctl vm.swappiness vm.overcommit_memory vm.nr_hugepages kernel.shmmax
# Постоянная настройка: файл в /etc/sysctl.d/ + применить (значение — пример, не рекомендация)
echo 'vm.swappiness = 10' | sudo tee /etc/sysctl.d/90-local.conf && sudo sysctl --system
cat /sys/kernel/mm/transparent_hugepage/enabled;  grep -i huge /proc/meminfo   # THP и huge pages
# Автозагрузка модуля: имя в /etc/modules-load.d/*.conf; запрет: «blacklist имя» в /etc/modprobe.d/*.conf
```

## 15. Оборудование и сведения о системе

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `lshw` | полная опись оборудования | lshw | `sudo lshw -short` · `sudo lshw -C network` · `sudo lshw -C disk` |
| `lscpu` | процессор: модель, ядра, потоки, NUMA, флаги | util-linux | `lscpu` · `lscpu -e` |
| `lsmem` | блоки памяти | util-linux | `lsmem` |
| `lspci` | PCI-устройства и их драйверы | pciutils | `lspci -nnk` |
| `lsusb` | USB-устройства (аппаратные ключи защиты 1С в т. ч.) | usbutils | `lsusb` · `lsusb -t` |
| `dmidecode` | DMI/SMBIOS: модель, серийные номера, планки памяти | dmidecode | `sudo dmidecode -t system` · `sudo dmidecode -t memory` · `sudo dmidecode -s system-product-name` |
| `sensors` / `sensors-detect` | датчики температуры и вентиляторов (в ВМ обычно недоступны) | ⊕ lm-sensors | `sudo sensors-detect` → `sensors` |
| `inxi` | компактная сводка о системе | ⊕ inxi | `inxi -Fxz` |
| `hwinfo` | подробная опись оборудования | ⊕ hwinfo | `hwinfo --short` |
| `lstopo-no-graphics` | топология CPU/кэшей/NUMA | ⊕ hwloc-nox | `lstopo-no-graphics` |
| `cpupower` | частоты и режимы энергосбережения CPU | linux-tools-$(uname -r) | `cpupower frequency-info` |
| `fwupdmgr` | обновления прошивок | fwupd | `fwupdmgr get-updates` |
| `virt-what` | определить тип виртуализации | ⊕ virt-what | `sudo virt-what` (или встроенная `systemd-detect-virt`) |
| `ubuntu-drivers` | подбор проприетарных драйверов | ubuntu-drivers-common (есть в манифесте 24.04; в остальных выпусках — проверить `command -v`) | `ubuntu-drivers devices` |
| `lsvmbus` | устройства шины VMBus в госте Hyper-V | ⊕ linux-cloud-tools-common (+ `linux-cloud-tools-$(uname -r)`) | `sudo lsvmbus -vv` |
| `vmware-toolbox-cmd` | гостевые службы VMware | open-vm-tools | `vmware-toolbox-cmd -v` · `vmware-toolbox-cmd timesync status` |
| `VBoxControl` | гостевые дополнения VirtualBox | ⊕ virtualbox-guest-utils (или с ISO Guest Additions) | `VBoxControl --version` |

```bash
hostnamectl; lsb_release -a; uname -r        # что за система
lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core|Socket|NUMA'
free -h; lsblk -d -o NAME,SIZE,ROTA,MODEL    # память и диски (ROTA=1 — HDD, 0 — SSD/виртуальный)
systemd-detect-virt                          # microsoft = Hyper-V, vmware, oracle = VirtualBox, kvm, none
```

Для гостя Hyper-V драйверы (hv_vmbus, hv_netvsc, hv_storvsc, hv_balloon) уже есть в штатном ядре Ubuntu — по таблице Microsoft Learn службы интеграции для 22.04 и 24.04 «Built-in». Отдельно ставятся только пользовательские демоны: пакет `linux-cloud-tools-common` содержит `/usr/sbin/hv_kvp_daemon` (обмен данными с хостом, в т. ч. IP-адрес гостя в Hyper-V Manager), `hv_vss_daemon` (согласованные снимки/резервное копирование ВМ), `hv_fcopy_daemon`, `lsvmbus` и юниты `hv-kvp-daemon.service`, `hv-vss-daemon.service`, `hv-fcopy-daemon.service` (проверено по списку файлов пакета для 24.04); в стандартной установке 24.04/26.04 пакетов `linux-cloud-tools-*` нет.

```bash
# Демоны Hyper-V должны соответствовать работающему ядру
sudo apt install linux-cloud-tools-common "linux-cloud-tools-$(uname -r)"
# либо метапакет под «свой» вариант ядра: linux-cloud-tools-generic (ядро linux-generic) / linux-cloud-tools-virtual (ядро linux-virtual)
systemctl status hv-kvp-daemon hv-vss-daemon --no-pager
```

Microsoft для LTS-выпусков советует использовать актуальное HWE-ядро, а как «Azure-tuned» вариант называет пакет `linux-azure`; ядро `linux-virtual` — облегчённый вариант generic-ядра для ВМ (подтверждено по packages.ubuntu.com 10.10.2026: в 26.04 есть `linux-virtual`, `linux-tools-virtual`, `linux-cloud-tools-virtual` и `linux-cloud-tools-generic` (версии 7.0.0-38); ранее: не подтверждено: имена метапакетов `linux-cloud-tools-generic`/`-virtual` и наличие `linux-virtual` в 26.04 даны по практике 22.04/24.04 — проверьте `apt-cache policy linux-cloud-tools-generic linux-virtual`).

## 16. Время и локали

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `date` | показать / отформатировать дату и время | coreutils | `date '+%F %T %z'` · `date -u` · `date -d '2 days ago' +%F` · `date +%s` |
| `timedatectl` | часовой пояс, состояние синхронизации | systemd | `timedatectl` · `sudo timedatectl set-timezone Asia/Tashkent` · `timedatectl list-timezones` · `timedatectl timesync-status` (только timesyncd) |
| `chronyc` | клиент управления chrony | chrony (по умолчанию в 26.04; ⊕ в 22.04/24.04) | `chronyc tracking` · `chronyc sources -v` · `sudo chronyc makestep` (немедленно скорректировать) |
| `hwclock` | аппаратные часы (RTC) | util-linux (22.04) / util-linux-extra (24.04+; в манифесте 26.04 есть, для 24.04 наличие не подтверждено — при отсутствии ⊕) | `sudo hwclock --show` · `sudo hwclock --systohc` |
| `ntpdate` | (устарела) разовая синхронизация | ⊕ ntpsec-ntpdate | замена: `sudo chronyc makestep` или `sudo systemctl restart systemd-timesyncd` |
| `cal` / `ncal` | календарь | ⊕ ncal | `cal -3` |
| `tzselect` / `zdump` | интерактивный выбор пояса / параметры пояса | libc-bin | `zdump Asia/Tashkent` |
| `locale` | текущие и доступные локали | libc-bin | `locale` · `locale -a` |
| `locale-gen` | сгенерировать локаль | locales | `sudo locale-gen ru_RU.UTF-8` |
| `update-locale` | записать локаль по умолчанию в `/etc/default/locale` | locales | `sudo update-locale LANG=ru_RU.UTF-8` |
| `localectl` | локаль и раскладка через systemd | systemd | `localectl status` · `sudo localectl set-locale LANG=ru_RU.UTF-8` |
| `localedef` | низкоуровневая компиляция локали | libc-bin | `localedef --list-archive` |

```bash
timedatectl                                   # «System clock synchronized: yes» — время синхронизировано
sudo timedatectl set-timezone Asia/Tashkent   # пример; список: timedatectl list-timezones
sudo locale-gen ru_RU.UTF-8 en_US.UTF-8 && sudo update-locale LANG=ru_RU.UTF-8
locale -a | grep -i ru_RU                     # локаль ru_RU.utf8 должна существовать ДО инициализации кластера PostgreSQL для 1С
```

## 17. Журналы

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `journalctl` (отбор) | журнал systemd по юниту, времени, приоритету | systemd | `journalctl -u ssh -e` · `journalctl -u postgresql@18-main -f` · `journalctl -p err -b` · `journalctl -k` · `journalctl --since '1 hour ago'` |
| `journalctl` (вывод) | формат, количество, поиск | systemd | `journalctl -n 200 --no-pager` · `journalctl -o short-iso` · `journalctl -o json-pretty` · `journalctl -g 'timeout'` · `journalctl -t backup` · `journalctl _PID=1234` |
| `journalctl` (обслуживание) | загрузки, размер, очистка | systemd | `journalctl --list-boots` · `journalctl -b -1` (прошлая загрузка) · `journalctl --disk-usage` · `sudo journalctl --vacuum-size=500M` · `sudo journalctl --vacuum-time=14d` |
| `logger` | записать сообщение в системный журнал | bsdutils | `logger -t backup 'pg_dump finished'` · `logger -p user.err 'ошибка'` |
| `logrotate` | ротация текстовых логов | logrotate | `sudo logrotate -d /etc/logrotate.d/rsyslog` (пробный прогон) · `sudo logrotate -f /etc/logrotate.conf` |
| `rsyslogd` | демон syslog; проверка конфигурации | rsyslog | `sudo rsyslogd -N1` |
| `tail` / `less` / `zgrep` | чтение текстовых логов | coreutils / less / gzip | `sudo tail -F /var/log/syslog` · `sudo less +G /var/log/auth.log` |
| `dmesg` | сообщения ядра | util-linux | `sudo dmesg -T --level=err,warn` |
| `last` / `lastb` / `who` | входы в систему | см. раздел 4 | `last -n 20` |
| `ausearch` / `aureport` / `auditctl` | подсистема аудита | ⊕ auditd | `sudo ausearch -f /etc/passwd` · `sudo aureport -au` |
| `sos` | собрать диагностический архив для поддержки | sos (22.04/24.04: sosreport) | `sudo sos report` |
| `multitail` / `lnav` | просмотр нескольких логов с подсветкой | ⊕ multitail / lnav | `lnav /var/log/syslog` |

Где что лежит:

- система: `/var/log/syslog`, `/var/log/auth.log`, `/var/log/kern.log`, `/var/log/dpkg.log`, `/var/log/apt/history.log`, `/var/log/unattended-upgrades/`, `/var/log/cloud-init.log`;
- PostgreSQL (пакеты Ubuntu/PGDG/1С): `/var/log/postgresql/postgresql-NN-main.log`;
- Apache: `/var/log/apache2/access.log`, `/var/log/apache2/error.log`;
- сервер 1С: вывод сервиса — `journalctl -u srv1cv8-<версия>@default`; технологический журнал — в каталоге, заданном в `logcfg.xml`; журнал регистрации ИБ — в каталоге данных кластера (`…/reg_1541/<идентификатор ИБ>/1Cv8Log/`);
- ограничение размера журнала systemd: `SystemMaxUse=` в `/etc/systemd/journald.conf`, затем `sudo systemctl restart systemd-journald`.

## 18. Загрузка и GRUB

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `update-grub` | пересоздать `grub.cfg` после правки `/etc/default/grub` | grub2-common | `sudo update-grub` |
| `grub-mkconfig` | то же, с явным указанием файла | grub-common | `sudo grub-mkconfig -o /boot/grub/grub.cfg` |
| `grub-install` | установить загрузчик | grub2-common | BIOS: `sudo grub-install /dev/sda` · UEFI: `sudo grub-install --target=x86_64-efi --efi-directory=/boot/efi` |
| `grub-editenv` | переменные окружения GRUB (сохранённый пункт) | grub-common | `grub-editenv list` |
| `grub-set-default` / `grub-reboot` | пункт меню по умолчанию / только на следующую загрузку (нужен `GRUB_DEFAULT=saved`) | grub2-common | `sudo grub-reboot 1` |
| `efibootmgr` | загрузочные записи UEFI | efibootmgr (на UEFI-системах) | `sudo efibootmgr -v` |
| `bootctl` | состояние загрузчика / прошивки UEFI | systemd / systemd-boot | `bootctl status` |
| `systemctl` (цели) | цель загрузки, аварийные режимы | systemd | `systemctl get-default` · `sudo systemctl set-default multi-user.target` · `sudo systemctl rescue` · `sudo systemctl reboot --firmware-setup` |
| `shutdown` | плановое выключение / перезагрузка с предупреждением | systemd-sysv | `sudo shutdown -r +5 'Перезагрузка через 5 минут'` · `sudo shutdown -h 23:00` · `sudo shutdown -c` (отменить) |
| `reboot` / `poweroff` / `halt` | перезагрузка / выключение / останов | systemd-sysv | `sudo reboot` |
| `systemd-analyze` | время загрузки и «узкие места» | systemd | `systemd-analyze` · `systemd-analyze critical-chain` |
| `chroot` | сменить корень (ремонт системы из Live-образа) | coreutils | `sudo chroot /mnt /bin/bash` |
| `wall` | сообщение всем вошедшим пользователям | bsdutils | `wall 'В 22:00 перезагрузка сервера'` |
| `runlevel` / `telinit` | (устар.) уровни запуска SysV | systemd-sysv | вместо них — цели systemd |

```bash
who -b; uptime -s; last -x reboot | head -n 5     # когда загружались
[ -f /var/run/reboot-required ] && echo 'нужна перезагрузка'
df -h /boot; sudo apt autoremove --purge          # /boot переполнен старыми ядрами
# Ремонт из Live/rescue-образа: смонтировать систему и войти в неё
sudo mount /dev/ubuntu-vg/ubuntu-lv /mnt
sudo mount /dev/sda2 /mnt/boot                    # если /boot — отдельный раздел
sudo mount /dev/sda1 /mnt/boot/efi                # только на UEFI
for d in dev proc sys run; do sudo mount --rbind /$d /mnt/$d; done
sudo chroot /mnt /bin/bash
#   внутри: update-initramfs -u -k all; update-grub; grub-install …; passwd ПОЛЬЗОВАТЕЛЬ; exit
```

Меню GRUB при загрузке: удерживать Shift (BIOS) или нажимать Esc (UEFI) → «Advanced options for Ubuntu» → «recovery mode»; либо `e` на пункте и дописать к строке `linux` параметр `systemd.unit=rescue.target`.

## 19. Безопасность и криптография

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `openssl x509` | просмотр сертификата | openssl | `openssl x509 -in cert.pem -noout -subject -issuer -dates` · `openssl x509 -in cert.pem -noout -text` |
| `openssl req` | запрос на сертификат (CSR) / самоподписанный сертификат | openssl | `openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -noenc -keyout key.pem -out cert.pem -subj '/CN=srv1c.example.local' -addext 'subjectAltName=DNS:srv1c.example.local'` |
| `openssl s_client` | проверить TLS-соединение и цепочку удалённого сервера | openssl | `openssl s_client -connect host:443 -servername host` |
| `openssl verify` / `pkcs12` | проверить цепочку / распаковать PFX | openssl | `openssl verify -CAfile ca.pem cert.pem` · `openssl pkcs12 -in bundle.pfx -out bundle.pem -noenc` |
| `openssl rand` / `dgst` / `passwd` | случайные данные / хэш файла / хэш пароля | openssl | `openssl rand -base64 32` · `openssl dgst -sha256 file` · `openssl passwd -6` |
| `gpg` | шифрование и подписи OpenPGP | gnupg (gpg) | `gpg --full-generate-key` · `gpg -c file` (шифрование паролем) · `gpg -d file.gpg > file` · `gpg --verify file.sig file` · `gpg --import key.asc` |
| `sha256sum` / `sha512sum` / `b2sum` / `md5sum` / `cksum` | контрольные суммы | coreutils | `sha256sum file` · `sha256sum -c SHA256SUMS` |
| `ssh-keygen` | ключи SSH | openssh-client | см. раздел 12 |
| `aa-status` | состояние AppArmor и профилей | apparmor | `sudo aa-status` |
| `aa-complain` / `aa-enforce` / `aa-logprof` | режим профиля: только журналировать / применять; доработка профиля по журналу | ⊕ apparmor-utils | `sudo aa-complain /etc/apparmor.d/ПРОФИЛЬ` · `sudo aa-enforce /etc/apparmor.d/ПРОФИЛЬ` |
| `apparmor_parser` | перезагрузить профиль | apparmor | `sudo apparmor_parser -r /etc/apparmor.d/ПРОФИЛЬ` |
| `update-ca-certificates` | добавить свой корневой сертификат в системное хранилище | ca-certificates | положить `*.crt` в `/usr/local/share/ca-certificates/` → `sudo update-ca-certificates` |
| `certbot` | сертификаты Let's Encrypt | ⊕ certbot (deb или snap) | `sudo certbot certonly --standalone -d example.com` · `sudo certbot renew --dry-run` |
| `cryptsetup` | шифрование дисков LUKS | cryptsetup | см. раздел 9.4 |
| `getcap` / `setcap` | capabilities исполняемых файлов | libcap2-bin | `getcap /usr/bin/ping` · `sudo setcap 'cap_net_bind_service=+ep' /путь/bin` |
| `pwgen` / `uuidgen` | генератор паролей / UUID | ⊕ pwgen / uuid-runtime (предустановлен в 22.04–26.04) | `pwgen -s 24 1` · `uuidgen` |
| `kinit` / `klist` / `kdestroy` / `ktutil` | Kerberos: билет, просмотр, keytab (доменная аутентификация 1С) | ⊕ krb5-user | `kinit user@EXAMPLE.LOCAL` · `klist` · `klist -kte /путь/usr1cv8.keytab` |
| `lynis` | аудит настроек безопасности | ⊕ lynis | `sudo lynis audit system` |
| `rkhunter` / `chkrootkit` | поиск руткитов | ⊕ rkhunter / chkrootkit | `sudo rkhunter --check` |
| `clamscan` / `freshclam` | антивирус ClamAV: проверка / обновление баз | ⊕ clamav | `clamscan -r --infected /srv/share` |
| `pro fix` | проверить и закрыть конкретную CVE/USN | ubuntu-pro-client | `sudo pro fix CVE-2026-35341` |
| `fail2ban-client`, `ufw`, `auditctl`, `faillock`, `visudo`, `chattr`, `shred` | см. разделы 11, 17, 4, 1 | — | — |

```bash
# Срок действия сертификата на удалённом сервере
echo | openssl s_client -connect srv1c.example.local:443 -servername srv1c.example.local 2>/dev/null \
  | openssl x509 -noout -subject -dates
# Подходит ли закрытый ключ к сертификату (хэши открытых ключей должны совпасть)
openssl x509 -noout -pubkey -in cert.pem | openssl sha256
openssl pkey -pubout -in key.pem | openssl sha256
# Ключ стороннего репозитория без apt-key (22.04–26.04)
curl -fsSL https://example.org/repo.asc | sudo gpg --dearmor -o /etc/apt/keyrings/example.gpg
# Проверить скачанный дистрибутив по контрольной сумме
sha256sum -c SHA256SUMS --ignore-missing
```

## 20. Контейнеры и виртуализация (кратко)

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `docker` | контейнеры Docker | ⊕ docker.io | `docker ps -a` · `docker images` · `docker run -d --name web -p 8080:80 nginx` · `docker exec -it web bash` · `docker logs -f web` · `docker stop web` · `docker rm web` |
| `docker` (обслуживание) | состояние и очистка | ⊕ docker.io | `docker stats` · `docker inspect web` · `docker system df` · `docker system prune` (удаляет неиспользуемое!) |
| `docker compose` | многоконтейнерные стенды по `compose.yaml` | ⊕ docker-compose-v2 | `docker compose up -d` · `docker compose logs -f` · `docker compose down` |
| `podman` | совместимая с Docker альтернатива без демона | ⊕ podman | `podman ps -a` |
| `lxc` / `lxd` | системные контейнеры и ВМ LXD (snap; в 24.04+ ставится при первом вызове через `lxd-installer`) | snap lxd | `sudo lxd init --auto` · `lxc launch ubuntu:24.04 test` · `lxc list` · `lxc exec test -- bash` · `lxc stop test` · `lxc delete test` |
| `virsh` | управление ВМ libvirt/KVM | ⊕ libvirt-clients (сервер: libvirt-daemon-system, qemu-kvm) | `virsh list --all` · `virsh start vm1` · `virsh shutdown vm1` · `virsh destroy vm1` (жёсткое выключение) · `virsh dominfo vm1` · `virsh console vm1` · `virsh snapshot-create-as vm1 snap1` |
| `virt-install` | создать ВМ libvirt из командной строки | ⊕ virtinst | `virt-install --help` |
| `qemu-img` | образы дисков: сведения, конвертация, размер | ⊕ qemu-utils | `qemu-img info disk.qcow2` · `qemu-img convert -O vhdx disk.qcow2 disk.vhdx` · `qemu-img resize disk.qcow2 +20G` |
| `multipass` | быстрые ВМ Ubuntu | snap multipass | `multipass launch 24.04 --name t1` · `multipass shell t1` |
| `systemd-nspawn` / `machinectl` | лёгкие контейнеры systemd | ⊕ systemd-container | `machinectl list` |
| `kvm-ok` | доступна ли аппаратная виртуализация | ⊕ cpu-checker | `kvm-ok` |

В 26.04: docker.io 29, containerd 2.2, runc 1.4; cgroup v1 удалён — контейнеры и ПО, требующие cgroup v1, не запустятся.

## 21. Разработка и отладка

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `git` | система контроля версий | git | `git clone URL` · `git status` · `git add -A` · `git commit -m 'msg'` · `git log --oneline -n 20` · `git diff` · `git pull --rebase` · `git push` |
| `git` (ветки и откаты) | ветки, временное сохранение, отмена правок | git | `git switch -c feature` · `git stash` · `git restore file` · `git tag -a v1.0 -m 'v1.0'` |
| `make` | сборка по Makefile | ⊕ make (build-essential) | `make -j"$(nproc)"` · `sudo make install` |
| `gcc` / `g++` | компиляторы C / C++ | ⊕ build-essential | `gcc -O2 -Wall -o prog prog.c` |
| `gdb` | отладчик | ⊕ gdb | `sudo gdb -p PID` · `gdb ./prog core` · `sudo gdb -batch -ex 'thread apply all bt' -p PID` (стеки всех потоков) |
| `gcore` | снять дамп памяти работающего процесса | ⊕ gdb | `sudo gcore -o /tmp/core PID` |
| `strace` | трассировка системных вызовов | strace | `sudo strace -f -p PID -e trace=network` · `strace -c cmd` (статистика) · `strace -f -tt -T -o out.txt cmd` |
| `ltrace` | трассировка вызовов библиотек | ⊕ ltrace | `ltrace -c cmd` |
| `valgrind` | поиск ошибок работы с памятью | ⊕ valgrind | `valgrind --leak-check=full ./prog` |
| `ldd` | от каких библиотек зависит бинарник | libc-bin | `ldd /opt/1cv8/x86_64/<версия>/ragent` (ищем «not found») |
| `ldconfig` | кэш динамических библиотек | libc-bin | `sudo ldconfig` · `ldconfig -p` |
| `nm` / `objdump` / `readelf` / `addr2line` | анализ объектных и ELF-файлов | binutils (⊕ в 24.04) | `readelf -h file` · `objdump -d file` |
| `python3` | интерпретатор Python | python3 | `python3 -m http.server 8000` · `python3 -m json.tool f.json` |
| `pip3` / `python3 -m venv` | пакеты Python / виртуальное окружение | ⊕ python3-pip / python3-venv | `python3 -m venv .venv` → `. .venv/bin/activate` (с 24.04 системный `pip install` запрещён PEP 668 — используйте venv или `pipx`) |
| `cmake` / `pkg-config` | система сборки / флаги библиотек | ⊕ cmake / pkgconf | `pkg-config --libs libpq` |
| `shellcheck` | статический анализ shell-скриптов | ⊕ shellcheck | `shellcheck script.sh` |
| `bash -n` / `bash -x` | проверить синтаксис / трассировать скрипт | bash | `bash -n script.sh` · `bash -x script.sh` |
| `trace-cmd` | трассировка ftrace | trace-cmd | `sudo trace-cmd record -e sched_switch sleep 5` → `trace-cmd report` |
| `perf` / `bpftrace` | профилирование и eBPF | см. раздел 8 | `sudo perf top -p PID` |
| `coredumpctl` | дампы упавших процессов | ⊕ systemd-coredump | `coredumpctl gdb PID` |
| `xvfb-run` | запустить графическую программу без дисплея (пакетный режим конфигуратора 1С на сервере без GUI) | ⊕ xvfb | `xvfb-run -a КОМАНДА` |

## 22. Встроенные команды и конструкции bash

Справка по любой: `help ИМЯ`; список всех: `help` или `compgen -b`.

| Команда | Назначение | Пример |
|---|---|---|
| `cd`, `pwd` | сменить / показать каталог | `cd -` (в предыдущий) · `cd` (домой) |
| `pushd`, `popd`, `dirs` | стек каталогов | `pushd /etc` … `popd` |
| `echo`, `printf` | вывод | `printf '%-10s %5d\n' name 42` |
| `read` | прочитать строку в переменную | `read -rp 'Продолжить? [y/N] ' ans` · `read -rs pass` (скрытый ввод) |
| `mapfile` (`readarray`) | прочитать строки в массив | `mapfile -t lines < file` |
| `export`, `unset` | экспортировать / удалить переменную | `export PGHOST=localhost` · `unset PGPASSWORD` |
| `declare` (`typeset`), `local`, `readonly` | объявление переменных, массивов, констант | `declare -A map` · `local x=1` · `readonly CFG=/etc/app.conf` |
| `set`, `shopt` | параметры оболочки | `set -euo pipefail` · `set -x` · `shopt -s nullglob globstar` |
| `alias`, `unalias` | псевдонимы | `alias ll='ls -lah'` |
| `source` (`.`) | выполнить файл в текущей оболочке | `source ~/.bashrc` · `. /etc/os-release` |
| `exec` | заменить оболочку программой / перенаправить потоки скрипта | `exec > >(tee -a run.log) 2>&1` |
| `eval` | выполнить строку как команду (опасно с чужими данными) | `eval "$(ssh-agent -s)"` |
| `test` (`[`), `[[ … ]]` | проверки файлов, строк, чисел | `[[ -f f && -s f ]]` · `[ "$a" -gt 5 ]` · `[[ $s == *.log ]]` |
| `(( … ))`, `let` | целочисленная арифметика | `(( n++ ))` · `echo $(( 8 * 1024 ))` |
| `if`, `case`, `for`, `while`, `until`, `select`, `function` | управляющие конструкции | `for f in *.log; do gzip "$f"; done` |
| `break`, `continue`, `return`, `exit` | управление циклами, функциями, кодом возврата | `exit 1` |
| `true`, `false`, `:` | константные коды возврата, пустая команда | `while :; do …; sleep 5; done` |
| `shift`, `getopts` | разбор аргументов скрипта | `while getopts 'd:v' o; do …; done` |
| `trap` | обработчик сигналов и выхода | `trap 'rm -f "$tmp"' EXIT` |
| `type`, `command`, `builtin`, `hash`, `enable` | поиск и вызов команд, кэш путей | `command -v psql` · `hash -r` |
| `jobs`, `fg`, `bg`, `disown`, `wait`, `suspend` | управление заданиями | `cmd &` → `jobs` → `fg %1` · `disown -h %1` · `wait` |
| `kill` | послать сигнал (встроенная версия понимает `%N`) | `kill %1` |
| `history`, `fc` | история команд | `history 20` · `history -d N` (удалить строку) · `fc -l -10` |
| `ulimit` | лимиты ресурсов текущей оболочки | `ulimit -n` · `ulimit -a` · `ulimit -c unlimited` |
| `umask` | маска прав новых файлов | `umask 077` |
| `time`, `times` | время выполнения конвейера / суммарное время оболочки | `time rsync -a src/ dst/` |
| `complete`, `compgen`, `compopt`, `bind` | автодополнение и клавиши readline | `compgen -c` (все команды) · `bind -P` |
| `help`, `caller`, `logout`, `coproc` | справка, стек вызовов, выход из login-оболочки, сопроцесс | `help trap` |

```bash
# Перенаправления и соединение команд
cmd > out.txt          # stdout в файл (ПЕРЕЗАПИСЬ);   cmd >> out.txt — дозапись
cmd 2> err.txt         # stderr в файл;                cmd > all.txt 2>&1  или  cmd &> all.txt — оба потока
cmd < in.txt           # stdin из файла;               cmd <<< 'строка';   cmd <<'EOF' … EOF — here-document
a | b                  # конвейер;                     a |& b — вместе со stderr
a && b                 # b, только если a успешна;     a || b — b, только если a завершилась с ошибкой
out=$(cmd)             # подстановка вывода;           diff <(cmd1) <(cmd2) — подстановка процесса
set -o noclobber       # запретить «>» затирать существующие файлы; осознанная перезапись: cmd >| файл
# Специальные переменные: $? код возврата, $$ PID оболочки, $! PID последнего фонового, $# число аргументов, "$@" все аргументы
# Значения по умолчанию: ${VAR:-default}  ${VAR:?сообщение об ошибке}  ${#VAR} длина  ${VAR%.dump} отрезать суффикс
# История: !! — предыдущая команда (sudo !!), !$ — её последний аргумент, Ctrl-R — поиск
# Клавиши: Ctrl-C прервать, Ctrl-Z приостановить, Ctrl-D конец ввода/выход, Ctrl-L очистить, Ctrl-A/E начало/конец, Ctrl-U/K/W удалить
# Безопасный заголовок скрипта
#!/usr/bin/env bash
set -euo pipefail
```

## 23. Утилиты PostgreSQL

### 23.1. Где лежат и как вызывать

| Сборка | Бинарные файлы | Конфигурация | Данные | Сервис |
|---|---|---|---|---|
| Пакеты Ubuntu, PGDG (apt.postgresql.org) и deb-сборки PostgreSQL от «1С» (⚠ не подтверждено для сборок «1С»: страница ИТС закрыта подпиской, раскладка известна только из практики сообщества — проверьте `dpkg -L postgresql-NN`) — раскладка `postgresql-common` | `/usr/lib/postgresql/NN/bin/` | `/etc/postgresql/NN/main/` (`postgresql.conf`, `pg_hba.conf`, `conf.d/`, `start.conf`, `pg_ctl.conf`) | `/var/lib/postgresql/NN/main/` | `postgresql@NN-main` (общий `postgresql` — «зонтик») |
| Postgres Pro Standard (пример: 17) | `/opt/pgpro/std-17/bin/` | в каталоге данных | `/var/lib/pgpro/std-17/data` | `postgrespro-std-17` |
| «PostgreSQL для 1С» от Postgres Professional (пример: 17; пакет `postgrespro-1c-17`) | `/opt/pgpro/1c-17/bin/` | в каталоге данных | `/var/lib/pgpro/1c-17/data` (каталог подтверждён официальным описанием метапакета — см. `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`; ранее: не подтверждено: по аналогии со Standard и практике сообщества) | `postgrespro-1c-17` (служба подтверждена официальным описанием метапакета — см. `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`; ранее: не подтверждено: то же; проверьте `systemctl list-units 'postgrespro*'`) |

- В раскладке `postgresql-common` клиентские программы (`psql`, `pg_dump`, `createdb`…) доступны из `/usr/bin` — это ссылки на `pg_wrapper`, который сам выбирает версию и кластер. Явный выбор: `psql --cluster 18/main`, переменная `PGCLUSTER=18/main` либо порт `-p`.
- Серверные программы (`pg_ctl`, `initdb`, `pg_controldata`, `pg_resetwal`, `pg_upgrade`, `pg_checksums`, `pg_rewind`, `pg_waldump`, `pg_test_fsync`) в `PATH` не входят: вызывайте полным путём от пользователя `postgres`, например `sudo -u postgres /usr/lib/postgresql/18/bin/pg_controldata /var/lib/postgresql/18/main`.
- У Postgres Pro: инициализация `sudo /opt/pgpro/std-17/bin/pg-setup initdb`, автозапуск `pg-setup service enable`, запуск `pg-setup service start`, ссылки на утилиты в `PATH` — `sudo /opt/pgpro/std-17/bin/pg-wrapper links update`. Для сборки «PostgreSQL для 1С» (Postgres Professional) ветка в путях и пакетах называется `1c-NN` — подтверждено по репозиторию `https://repo.postgrespro.ru/1c/` (каталоги `1c-14` … `1c-18`) и его `meta.json`: пакеты `postgrespro-1c-17` (метапакет), `postgrespro-1c-17-server`, `-client`, `-libs`, `-contrib`, `-devel`, `-jit`, `-plperl`, `-plpython3`, `-pltcl`, `-docs`, `-docs-ru`; каталог установки `/opt/pgpro/1c-17`; утилита `/opt/pgpro/1c-17/bin/pg-setup` с подкомандами `initdb`, `service enable`, `service start`; поддерживаемые Ubuntu — 22.04, 24.04, 25.10, 26.04 (x86_64); версия сборки на момент проверки — 17.10 (от PGDG отстаёт: там уже 17.11). Подключение репозитория — скрипт `https://repo.postgrespro.ru/1c/1c-17/keys/pgpro-repo-add.sh` (создаёт `/etc/apt/sources.list.d/postgresql-1c-17.list` и ключ `/etc/apt/trusted.gpg.d/postgrespro.gpg`), затем `sudo apt install postgrespro-1c-17`. Условия (страница 1c.postgres.ru): бесплатно для любых целей, кроме предоставления СУБД как услуги (DBaaS) и встраивания в свои продукты; без гарантий и техподдержки.
- Подключение администратора локально: `sudo -u postgres psql` (peer-аутентификация через сокет `/var/run/postgresql`).

### 23.2. Управление кластерами (пакет `postgresql-common`)

| Команда | Назначение | Примеры |
|---|---|---|
| `pg_lsclusters` | список кластеров: версия, имя, порт, статус, владелец, каталог данных, лог | `pg_lsclusters` · `pg_lsclusters -h` (без заголовка) · `pg_lsclusters -j` (JSON) |
| `pg_ctlcluster` | `start`, `stop`, `restart`, `reload`, `status`, `promote`, `logrotate` для кластера (от root перенаправляет в systemctl); режим останова `-m smart`, `-m fast` (по умолчанию) или `-m immediate`; `-f`/`--force` — при неудаче перейти к `immediate` и затем убить процесс | `sudo pg_ctlcluster 18 main reload` · `sudo pg_ctlcluster 18 main stop -m fast` · `pg_ctlcluster 18 main status` |
| `pg_createcluster` | создать кластер (обёртка над `initdb`; параметры initdb — после `--`) | `sudo pg_createcluster 18 main --locale=ru_RU.UTF-8 --start` · `sudo pg_createcluster 18 data2 -d /data/pg/18/data2 -p 5433` |
| `pg_dropcluster` | **удалить кластер вместе с данными** | `sudo pg_dropcluster --stop 18 main` |
| `pg_renamecluster` | переименовать кластер | `sudo pg_renamecluster 18 main prod` |
| `pg_upgradecluster` | перенести кластер на новую мажорную версию (`-m dump` по умолчанию, `-m upgrade` — через pg_upgrade) | `sudo pg_upgradecluster -v 18 16 main` · `sudo pg_upgradecluster -v 18 -m upgrade --link 16 main` |
| `pg_conftool` | прочитать / изменить параметр в `postgresql.conf` | `pg_conftool 18 main show shared_buffers` · `sudo pg_conftool 18 main set max_connections 500` · `pg_conftool -s 18 main show port` |
| `pg_backupcluster` | простые копии в `/var/backups/postgresql/NN-имя/` (basebackup, dump, WAL) | `sudo pg_backupcluster 18 main createdirectory` · `sudo -u postgres pg_backupcluster 18 main basebackup` · `sudo -u postgres pg_backupcluster 18 main list` |
| `pg_restorecluster` | восстановить кластер из копии `pg_backupcluster` | `man pg_restorecluster` |
| `pg_virtualenv` | временный кластер для тестов (создаётся и удаляется автоматически) | `pg_virtualenv psql -c 'select version()'` |
| `systemctl` | штатное управление сервисом | `sudo systemctl restart postgresql@18-main` · `systemctl status postgresql@18-main` |

Автозапуск кластера задаёт `/etc/postgresql/NN/main/start.conf`: `auto` (по умолчанию), `manual`, `disabled`.

### 23.3. Клиентские утилиты

| Команда | Назначение | Примеры |
|---|---|---|
| `psql` | интерактивный терминал и исполнитель SQL-скриптов | `sudo -u postgres psql` · `psql -h srv -p 5432 -U postgres -d ib` · `psql -l` · `psql -f script.sql -v ON_ERROR_STOP=1 -1` · `psql -XAt -c 'select version()'` |
| `pg_dump` | логическая копия одной базы | `pg_dump -Fc -f /backup/ib.dump ib` · `pg_dump -Fd -j 4 -f /backup/ib.dir ib` · `pg_dump -Fc -Z zstd:3 -f ib.dump ib` (zstd — с PG 16) · `pg_dump -s ib` (только схема) |
| `pg_dumpall` | копия всего кластера или только ролей и табличных пространств | `pg_dumpall --globals-only -f globals.sql` · `pg_dumpall -f all.sql` |
| `pg_restore` | восстановление из форматов custom/directory/tar | `pg_restore -d ib_new -j 4 /backup/ib.dump` · `pg_restore -l ib.dump` (оглавление) · `pg_restore -C -d postgres ib.dump` (создать БД с исходным именем) · `pg_restore --clean --if-exists -d ib ib.dump` |
| `pg_basebackup` | физическая копия всего кластера (для реплики и PITR) | `pg_basebackup -h primary -U replicator -D /var/lib/postgresql/18/main -P -R -X stream` · `pg_basebackup -D /backup/base_2026-10-10 -Ft -z -P -X stream -c fast` |
| `pg_verifybackup` | проверить целостность базовой копии по манифесту | `pg_verifybackup /backup/base_2026-10-10` |
| `pg_combinebackup` | собрать полную копию из полной и инкрементальных (PG 17+) | `pg_combinebackup /backup/full /backup/incr1 -o /restore/data` |
| `pg_isready` | принимает ли сервер подключения (код 0 — да, 1 — отклоняет, 2 — нет ответа) | `pg_isready -h localhost -p 5432` |
| `createdb` / `dropdb` | создать / удалить базу | `createdb -T template0 -E UTF8 -l ru_RU.UTF-8 ib_test` · `dropdb --if-exists ib_test` · `dropdb -f ib_test` (PG 13+: отключить сеансы) |
| `createuser` / `dropuser` | создать / удалить роль | `createuser --pwprompt --createdb app` · `createuser --replication -P replicator` · `dropuser app` |
| `vacuumdb` | VACUUM / ANALYZE из командной строки | `vacuumdb -d ib -z -j 4` · `vacuumdb -a -Z` (только ANALYZE, все базы) · `vacuumdb -a --analyze-in-stages` (после восстановления/обновления) |
| `reindexdb` | перестроить индексы | `reindexdb -d ib -j 4` · `reindexdb -d ib -t table --concurrently` |
| `clusterdb` | физически упорядочить таблицу по индексу (CLUSTER) | `clusterdb -d ib -t table` |
| `pg_amcheck` | проверка таблиц и индексов на повреждения (PG 14+) | `pg_amcheck -d ib --install-missing --progress` |
| `pg_receivewal` | непрерывный приём WAL по протоколу репликации (архив) | `pg_receivewal -h primary -U replicator -D /backup/wal -S wal_slot` |
| `pg_recvlogical` | поток логического декодирования | `pg_recvlogical --help` |
| `pgbench` | нагрузочный тест | `pgbench -i -s 50 bench` · `pgbench -c 16 -j 4 -T 60 bench` |
| `pg_config` | параметры сборки (пакет ⊕ `libpq-dev` / `postgresql-server-dev-NN`) | `pg_config --version` · `pg_config --bindir` |

Новое в утилитах PostgreSQL 18: `pg_dump`/`pg_dumpall`/`pg_restore` получили `--statistics`, `--no-statistics`, `--statistics-only`, `--no-data`, `--no-schema` (статистика в `pg_dump` по умолчанию **не** выгружается); `vacuumdb --missing-stats-only`; `pg_upgrade` сохраняет статистику оптимизатора и получил режим `--swap`; `initdb` включает контрольные суммы данных по умолчанию (`--no-data-checksums` — отключить); `pg_verifybackup` умеет проверять копии в формате tar.

### 23.4. Серверные утилиты (`/usr/lib/postgresql/NN/bin/`, запускать от `postgres`)

| Команда | Назначение | Примеры |
|---|---|---|
| `postgres` | сам сервер СУБД | `postgres -V` |
| `initdb` | создать каталог данных (в Ubuntu — через `pg_createcluster`) | `initdb -D /путь --locale=ru_RU.UTF-8` |
| `pg_ctl` | запуск / останов / reload / promote (в Ubuntu — через `pg_ctlcluster` или `systemctl`) | `pg_ctl -D КАТАЛОГ status` · `pg_ctl -D КАТАЛОГ stop -m fast` |
| `pg_controldata` | управляющая информация кластера: состояние, последняя контрольная точка, версия, контрольные суммы | `pg_controldata /var/lib/postgresql/18/main` |
| `pg_checksums` | проверить / включить / выключить контрольные суммы (**кластер остановлен**) | `pg_checksums --check -D КАТАЛОГ` · `pg_checksums --enable -D КАТАЛОГ` |
| `pg_resetwal` | **аварийный** сброс WAL; возможна потеря данных — только после полной копии каталога | `pg_resetwal -n КАТАЛОГ` (`-n` — показать, ничего не меняя) |
| `pg_rewind` | вернуть бывший мастер в строй как реплику | `pg_rewind --target-pgdata=КАТАЛОГ --source-server='host=new_primary user=postgres dbname=postgres' -P` |
| `pg_upgrade` | обновление мажорной версии на месте (в Ubuntu — через `pg_upgradecluster`) | `pg_upgrade -b СТАРЫЙ_BIN -B НОВЫЙ_BIN -d СТАРЫЕ_ДАННЫЕ -D НОВЫЕ_ДАННЫЕ --check` |
| `pg_waldump` | расшифровка содержимого WAL-сегментов | `pg_waldump -n 20 /var/lib/postgresql/18/main/pg_wal/000000010000000000000001` |
| `pg_walsummary` | содержимое сводок WAL для инкрементальных копий (PG 17+) | `pg_walsummary ФАЙЛ.summary` |
| `pg_archivecleanup` | удалить из архива WAL-сегменты старше указанного | `pg_archivecleanup -n /backup/wal 000000010000000A00000010` (`-n` — только показать) |
| `pg_createsubscriber` | превратить физическую реплику в логическую (PG 17+) | `pg_createsubscriber --help` |
| `pg_test_fsync` / `pg_test_timing` | тест скорости fsync на диске / накладных расходов таймера | `pg_test_fsync -f /var/lib/postgresql/fsync.test` |
| `oid2name` / `vacuumlo` | соответствие OID ↔ имена объектов и файлов / очистка «осиротевших» large objects | `oid2name -d ib` |

### 23.5. Метакоманды `psql`, окружение, полезные запросы

```text
\l[+]            базы данных (с + — размеры)        \c БАЗА [РОЛЬ]   подключиться к другой базе
\dt[+] [шаблон]  таблицы                             \d[+] ТАБЛИЦА    структура таблицы, индексы
\di \dn \du \dx \db \df \dp   индексы, схемы, роли, расширения, табл. пространства, функции, права
\x [auto]        расширенный (вертикальный) вывод    \timing          показывать время выполнения
\conninfo        параметры текущего подключения      \password [РОЛЬ] сменить пароль (без записи в историю)
\i ФАЙЛ          выполнить скрипт                    \o ФАЙЛ          вывод в файл
\copy … to/from  выгрузка/загрузка CSV на стороне клиента            \watch N   повторять запрос каждые N секунд
\e               открыть запрос в редакторе          \gx              выполнить и показать вертикально
\! КОМАНДА       команда оболочки                    \pset pager off  отключить пейджер
\? и \h КОМАНДА  справка по метакомандам и по SQL    \q               выход
```

```bash
# Размеры баз
sudo -u postgres psql -c "select datname, pg_size_pretty(pg_database_size(datname)) from pg_database order by pg_database_size(datname) desc;"
# Активные запросы, самые долгие сверху
sudo -u postgres psql -c "select pid, usename, datname, state, now()-query_start as dur, left(query,60) from pg_stat_activity where state <> 'idle' order by dur desc;"
# Мягко отменить запрос / завершить сеанс (вместо kill) / перечитать конфигурацию
sudo -u postgres psql -c "select pg_cancel_backend(12345);"
sudo -u postgres psql -c "select pg_terminate_backend(12345);"
sudo -u postgres psql -c "select pg_reload_conf();"
# Копия базы 1С и восстановление в новую базу
sudo -u postgres pg_dump -Fc -f /backup/pg/ib_$(date +%F_%H%M).dump ib
sudo -u postgres pg_dumpall --globals-only -f /backup/pg/globals_$(date +%F).sql
sudo -u postgres createdb -T template0 ib_copy
sudo -u postgres pg_restore -d ib_copy -j 4 /backup/pg/ib_2026-10-10_0230.dump
sudo -u postgres vacuumdb -d ib_copy -z -j 4
```

Переменные окружения клиента: `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSFILE`; пароли — в `~/.pgpass` (строки `хост:порт:база:роль:пароль`, права `0600`), а не в `PGPASSWORD` и не в командной строке.

### 23.6. Сторонние инструменты

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `pgbackrest` | резервное копирование с PITR, инкрементами, параллелизмом | ⊕ pgbackrest | `sudo -u postgres pgbackrest --stanza=main backup` · `sudo -u postgres pgbackrest info` |
| `barman` | сервер резервных копий PostgreSQL | ⊕ barman | `barman check all` · `barman list-backup all` |
| `pg_probackup` | резервное копирование от Postgres Professional | репозиторий Postgres Pro | `pg_probackup show -B /backup` |
| `pgbouncer` | пул соединений | ⊕ pgbouncer | `systemctl status pgbouncer` |
| `pg_activity` | «top» для PostgreSQL | ⊕ pg-activity | `sudo -u postgres pg_activity` |
| `pgcli` | psql с автодополнением и подсветкой | ⊕ pgcli | `pgcli -h localhost -U postgres ib` |
| `pg_repack` | перепаковка таблиц без долгих блокировок | ⊕ postgresql-NN-repack | `pg_repack -d ib -t table` |
| `pgbadger` | отчёты по журналу PostgreSQL | ⊕ pgbadger | `pgbadger /var/log/postgresql/postgresql-18-main.log -o report.html` |
| `pg-setup` / `pg-wrapper` | инициализация и ссылки в сборках Postgres Pro | postgrespro-std-NN / postgrespro-1c-NN | `sudo /opt/pgpro/1c-17/bin/pg-setup initdb` · `sudo /opt/pgpro/1c-17/bin/pg-setup service enable` · `sudo /opt/pgpro/1c-17/bin/pg-setup service start` (см. 23.1) |

## 24. Утилиты «1С:Предприятие 8» на Linux

Каталог платформы: `/opt/1cv8/x86_64/<версия>/`. Единый установщик `setup-full-<версия>-x86_64.run` применяется начиная с 8.3.20 (подтверждено скриптом установки проекта onec-docker: для релизов младше 20 — `dpkg -i *.deb`, с 20-го — `setup-*.run --mode unattended`); до него платформа ставилась deb/rpm-пакетами. ⚠ не подтверждено первоисточником (документация ИТС закрыта), по памяти рецензента: каталог `/opt/1cv8/<арх>/<версия>/` появился уже в пакетах 8.3.18–8.3.19 вместе с возможностью ставить несколько версий рядом, а старый путь `/opt/1C/v8.3/x86_64/` относится к 8.3.17 и младше; systemd-юниты `srv1cv8-<версия>@.service` и `ras-<версия>.service` в каталоге версии — с 8.3.21, до этого сервер запускался init-скриптом `/etc/init.d/srv1cv83`. На вашем сервере проверяется просто: `ls /opt/1cv8/x86_64/*/ | grep -E 'service|srv1cv8'`. В `PATH` каталога нет — вызывайте полным путём или из каталога через `./`. Справка у консольных утилит встроенная: `./rac help`, `./rac help infobase`, `./ras help`, `./ibcmd help`, `./ibsrv --help` (⚠ не подтверждено: форма вызова справки у `ibsrv` — попробуйте и `--help`, и `help`). Сервер работает от пользователя `usr1cv8` (группа `grp1cv8`); данные кластера по умолчанию — `/home/usr1cv8/.1cv8/1C/1cv8/`.

О версиях платформы (на 10.10.2026): номер `8.3.27.1688` в примерах — только образец записи. По открытым источникам: на ИТС опубликована документация для 8.3.27 (`v8327doc`) и 8.5.4 (`v854doc`); в блоге разработчиков платформы «Заметки из Зазеркалья» записи июля–сентября 2026 относятся к 8.5.5, а 07.10.2026 опубликован план задач на 8.5.6. Какая сборка сейчас рекомендована к использованию, по этим источникам установить нельзя (⚠ не подтверждено: releases.1c.ru и страницы ИТС требуют входа) — подставляйте фактическую версию: `ls /opt/1cv8/x86_64/`.

| Утилита | Назначение | Пример |
|---|---|---|
| `ragent` | агент сервера — главный процесс сервера 1С (порт 1540); запускается сервисом `srv1cv8-<версия>@default` | `systemctl status srv1cv8-8.3.27.1688@default` |
| `rmngr` | менеджер кластера (порт 1541); порождается агентом | `pgrep -af rmngr` |
| `rphost` | рабочий процесс: обслуживает сеансы пользователей (порты 1560–1591) | `ps -C rphost -o pid,rss,etime,cmd` |
| `ras` | сервер администрирования кластера (порт 1545), посредник между `rac` и агентом | `./ras cluster --daemon --port=1545 localhost:1540` (или сервис `ras-<версия>`) |
| `rac` | консольный клиент администрирования кластера (работает через `ras`) | `./rac cluster list` · `./rac session --cluster=UUID list` |
| `ibcmd` | администрирование информационной базы и автономного сервера без кластера: создание ИБ, выгрузка/загрузка `.dt`, конфигурация, расширения | `./ibcmd infobase dump --dbms=PostgreSQL --db-server=localhost --db-name=ib --db-user=postgres --db-pwd=*** /backup/ib.dt` |
| `ibsrv` | автономный сервер: одна ИБ, встроенный веб-сервер, без кластера (по v8.1c.ru: работает и с файловой ИБ, до трёх клиентских сеансов без серверной лицензии) | `./ibsrv --data=КАТАЛОГ --config=ФАЙЛ.yml` (подтверждено приложением 4 документации 8.3.27 (`--data=<path>` или `-d`, `--config=<path>` или `-c`, `--daemon` — режим демона в Linux; сверено 10.10.2026); ранее: не подтверждено: имена параметров даны по памяти, документация ИТС закрыта — сверить с `./ibsrv --help`) |
| `webinst` | публикация ИБ и веб-сервисов на Apache | `sudo ./webinst -publish -apache24 -wsdir base -dir /var/www/base -connstr 'Srvr=localhost;Ref=base;' -confpath /etc/apache2/apache2.conf` |
| `1cv8` | толстый клиент и конфигуратор (в т. ч. пакетный режим `DESIGNER`) | `./1cv8 DESIGNER /S 'srv\ib' /N Админ /P *** /DumpIB /backup/ib.dt /DisableStartupDialogs /Out /tmp/dump.log` |
| `1cv8c` | тонкий клиент | `./1cv8c ENTERPRISE /S 'srv\ib'` |
| `1cv8s` | программа запуска: подбирает клиент нужной версии по параметрам базы (подтверждено приложением 1 документации 8.3.27 (интерактивная программа запуска системы конкретной версии; сверено 10.10.2026); ранее: не подтверждено: назначение дано по описанию Windows-аналога `1cv8s.exe`, приложение «Структура каталога установки» на ИТС закрыто) | `./1cv8s` |
| `1cestart` | стартер: окно списка баз (`/opt/1cv8/common/1cestart`) | `/opt/1cv8/common/1cestart` |
| `crserver` | сервер хранилища конфигураций (tcp-порт 1542) | `./crserver -port 1542 -d /srv/1c/repo` — ключи `-port` и `-d` и порт 1542 подтверждены практикой сообщества (entrypoint образа onec-docker); запуск в фоне — `-daemon` (подтверждено 11.10.2026 «Руководством разработчика» 8.3.27, разд. 37.4.5.2: `./crserver -daemon -port <порт> -d <каталог>`, порт по умолчанию 1542; ранее: не подтверждено: ключ `-daemon` дан по памяти, документация ИТС закрыта) |
| `dbgs` | сервер отладки по HTTP (порт 1550 — подтверждён как значение по умолчанию `debugServerPort` в onec-docker) | `./dbgs --addr=0.0.0.0 --port=1550` (подтверждено приложением 4 документации 8.3.27: `dbgs --version\|--help --service\|--daemon --addr=<host> --port=<port>\|--range=<range> --ownerPID=<PID> --password=<pwd> --notify=<file> --debugServerUsers=<file>` (сверено 10.10.2026); ранее: не подтверждено: ключи `--addr`/`--port` даны по памяти — сверить с `./dbgs --help`) |
| `setup-full-<версия>-x86_64.run` | установщик платформы (сервер, клиенты, веб-расширения); для одного тонкого клиента — `setup-thin-<версия>-x86_64.run` | `sudo ./setup-full-8.3.27.1688-x86_64.run --mode unattended --enable-components server,ws,server_admin,ru` — синтаксис `--mode unattended --enable-components …` и имена компонентов `server`, `ws`, `config_storage_server`, `client_full`, `ru` подтверждены скриптом onec-docker; `server_admin` (сервер администрирования `ras`) и остальные компоненты (⚠ не подтверждено первоисточником) — смотрите `./setup-full-….run --help` |
| `uninstaller-full` | удаление данной версии платформы (лежит в каталоге версии) | `sudo /opt/1cv8/x86_64/<версия>/uninstaller-full` |

```bash
cd /opt/1cv8/x86_64/8.3.27.1688
# Сервисы: юниты лежат в каталоге версии, их подключают ссылкой
sudo systemctl link "$PWD/srv1cv8-8.3.27.1688@.service" && sudo systemctl enable --now srv1cv8-8.3.27.1688@default
sudo systemctl link "$PWD/ras-8.3.27.1688.service"      && sudo systemctl enable --now ras-8.3.27.1688
systemctl cat srv1cv8-8.3.27.1688@default               # переменные SRV1CV8_DATA, SRV1CV8_PORT, SRV1CV8_REGPORT, SRV1CV8_RANGE, SRV1CV8_DEBUG…
#   полный перечень подтверждён документацией 8.3.27 (сверено 10.10.2026): SRV1CV8_DATA, SRV1CV8_DEBUG, SRV1CV8_KEYTAB, SRV1CV8_PINGPERIOD, SRV1CV8_PINGTIMEOUT, SRV1CV8_PORT, SRV1CV8_RANGE, SRV1CV8_REGPORT, SRV1CV8_SECLEV; ранее: не подтверждено первоисточником (ИТС закрыт): в поисковой выдаче автора подтверждены только SRV1CV8_DATA и шаблон
#   srv1cv8-<версия>@.service для 8.3.27; остальные имена (а также SRV1CV8_SECLEV, SRV1CV8_PINGPERIOD, SRV1CV8_PINGTIMEOUT,
#   SRV1CV8_KEYTAB) — по памяти со времён /etc/init.d/srv1cv83; для 8.5.x раскладка не проверялась. Истина — вывод systemctl cat.
# Менять параметры — не в файле из /opt/1cv8/…, а drop-in'ом: sudo systemctl edit srv1cv8-8.3.27.1688@default
#   [Service]
#   Environment=SRV1CV8_DATA=/srv/1c/cluster
# (пример: каталог данных кластера на отдельном диске, владелец usr1cv8:grp1cv8; в юнит-файлах systemd комментарий
#  в конце строки НЕ допускается — он станет частью значения)
# затем: sudo systemctl daemon-reload && sudo systemctl restart srv1cv8-8.3.27.1688@default
# Что реально получил ragent (ключи -port/-regport/-range/-d/-seclev/-debug видны в командной строке процесса):
ps -C ragent -o pid,user,etime,args
#   значения по умолчанию по практике сообщества (onec-docker): порт агента 1540, regport 1541, range 1560:1591, seclev 0,
#   pingPeriod 1000, pingTimeout 5000, порт сервера отладки 1550

# rac: сначала UUID кластера, дальше всё через --cluster=
./rac cluster list
CL=$(./rac cluster list | awk '/^cluster/{print $3}')
./rac infobase   --cluster=$CL summary list             # информационные базы
./rac session    --cluster=$CL list                     # сеансы
./rac session    --cluster=$CL terminate --session=UUID_СЕАНСА
./rac process    --cluster=$CL list                     # рабочие процессы и их память
./rac connection --cluster=$CL list;  ./rac lock --cluster=$CL list;  ./rac server --cluster=$CL list
# Создать ИБ в кластере вместе с базой в PostgreSQL
./rac infobase --cluster=$CL create --create-database --name=ib --dbms=PostgreSQL --db-server=localhost \
      --db-name=ib --locale=ru --db-user=postgres --db-pwd='***' --license-distribution=allow
# Запретить вход пользователей и регламентные задания на время обслуживания
./rac infobase --cluster=$CL update --infobase=UUID_ИБ --infobase-user=Админ --infobase-pwd='***' \
      --sessions-deny=on --denied-message='Обслуживание' --permission-code=123 --scheduled-jobs-deny=on
# Если у кластера есть администраторы: добавить --cluster-user=… --cluster-pwd=…
```

Режимы `rac` (по `./rac help`; состав зависит от версии платформы): `agent`, `cluster`, `manager`, `server`, `process`, `service`, `infobase`, `connection`, `session`, `lock`, `rule`, `profile`, `counter`, `limit`. Версии `rac` и `ras` должны соответствовать версии сервера. Режимы `ibcmd`: `infobase` (`create`, `dump`, `restore`, `config …`), `server`, `config`, `session`, `lock`, `extension`, `mobile-app`, `mobile-client`; `ibcmd` может работать напрямую с СУБД (`--dbms`, `--db-server`, `--db-name`, `--db-user`, `--db-pwd`), с работающим автономным сервером (`--pid`) или удалённо (`--remote=ssh://хост:порт`). ⚠ не подтверждено: ни автору, ни рецензенту не удалось открыть первоисточник (документация ИТС закрыта подпиской, kb.1ci.com без входа отдаёт только оглавление) — списки режимов `rac`/`ibcmd`, параметры `rac infobase create/update` и ключи `ibcmd` приведены по встроенной справке, известной из практики для 8.3.2x; в новых версиях режимов больше. Перед использованием в скриптах сверяйте: `./rac help`, `./rac help infobase`, `./ibcmd help`, `./ibcmd help infobase`. Пакетный режим конфигуратора `1cv8 DESIGNER` требует графического окружения — на сервере без GUI его запускают через `xvfb-run -a`.

Замечания по безопасности вызовов: пароли в `--db-pwd=…`, `--infobase-pwd=…`, `--cluster-pwd=…`, `/P …` видны в `ps` и остаются в `~/.bash_history` (см. раздел 25) — запускайте такие команды из скрипта с правами `0700`, читающего пароль из файла `0600`, либо начинайте команду с пробела. `ibcmd` для работы нужен каталог служебных данных (параметр `--data=КАТАЛОГ`; умолчание подтверждено приложением 4 документации 8.3.27: `~/.1cv8/standalone-server` (сверено 10.10.2026); ранее: не подтверждено: значение по умолчанию и обязательность — сверить с `./ibcmd help infobase dump`), и запускать его следует от пользователя, имеющего права на этот каталог (обычно `sudo -u usr1cv8`).

### 24.1. Веб-сервер Apache для публикации 1С

`webinst -apache24` дописывает в файл, указанный в `-confpath`, загрузку модуля платформы (`wsap24.so` из каталога версии) и псевдоним публикации, а в каталог `-dir` кладёт `default.vrd`. После публикации Apache нужно перезапустить.

| Команда | Назначение | Пакет | Примеры |
|---|---|---|---|
| `apache2ctl` (`apachectl`) | проверка конфигурации и управление Apache | apache2 (⊕) | `sudo apache2ctl configtest` (или `-t`) · `apache2ctl -M` (загруженные модули; ищите `_1cws_module`) · `apache2ctl -S` (виртуальные хосты) |
| `a2enmod` / `a2dismod` | включить / выключить модуль Apache | apache2 (⊕) | `sudo a2enmod ssl` · `sudo a2dismod status` |
| `a2ensite` / `a2dissite` | включить / выключить сайт из `/etc/apache2/sites-available/` | apache2 (⊕) | `sudo a2ensite default-ssl` · `sudo a2dissite 000-default` |
| `a2enconf` / `a2disconf` | включить / выключить фрагмент из `/etc/apache2/conf-available/` | apache2 (⊕) | `sudo a2enconf security` |
| `htpasswd` | файл паролей для Basic-аутентификации | apache2-utils (⊕) | `sudo htpasswd -c /etc/apache2/.htpasswd user` |
| `ab` | простой нагрузочный тест HTTP | apache2-utils (⊕) | `ab -n 100 -c 10 http://localhost/base/` |

```bash
sudo apt install apache2
sudo /opt/1cv8/x86_64/8.3.27.1688/webinst -publish -apache24 -wsdir base -dir /var/www/base \
     -connstr 'Srvr=localhost;Ref=base;' -confpath /etc/apache2/apache2.conf
sudo apache2ctl configtest && sudo systemctl restart apache2
grep -n '1cws\|base' /etc/apache2/apache2.conf      # что дописал webinst
ldd /opt/1cv8/x86_64/8.3.27.1688/wsap24.so | grep 'not found'   # все ли библиотеки модуля на месте
sudo tail -n 50 /var/log/apache2/error.log
```

Снять публикацию: `sudo ./webinst -delete -apache24 -wsdir base -dir /var/www/base -confpath /etc/apache2/apache2.conf` (по приложению 4 документации 8.3.27 для удаления публикации достаточно `-delete` и `-wsdir` (сверено 10.10.2026); ранее: не подтверждено: набор обязательных параметров для `-delete` — сверить с `./webinst` без параметров, он печатает справку). Известная проблема 26.04 из примечаний к выпуску: защита `MemoryDenyWriteExecute` в юните `apache2` ломает JIT у `mod-php` (LP #2144455). ⚠ не подтверждено: затрагивает ли это ограничение модуль 1С `wsap24.so` — не проверялось; если на 26.04 Apache падает или не загружает модуль после публикации, смотрите `journalctl -u apache2 -e`, `systemctl cat apache2` и пробуйте снять ограничение drop-in'ом (`sudo systemctl edit apache2` → `[Service]` / `MemoryDenyWriteExecute=no`).

### 24.2. Лицензирование (что проверить на сервере)

Сверено 10.10.2026 с документацией 8.3.27 (глава 10): каталог `/var/1C/licenses` и порядок поиска файлов лицензий подтверждены; подробности — в `../1c/04-licenzirovanie.md` и `../its-docs/adm-gl10-zashchita-licenzii-p2.md`. Ранее: не подтверждено: раздел дан по практике сообщества, документация ИТС в этой проверке недоступна. Программные лицензии сервера хранятся файлами `*.lic` (типичные каталоги: `/var/1C/licenses/`, а также `conf` в каталоге данных пользователя `usr1cv8`); привязаны к параметрам «железа» ВМ — после смены числа ядер, объёма ОЗУ, MAC-адреса, имени хоста или дисков лицензия может «слететь», поэтому перед изменением конфигурации ВМ и перед переносом на другой хост имейте резервные пин-коды. Аппаратные ключи HASP в гостевой ВМ видны как USB-устройства: `lsusb` (проброс USB в Hyper-V штатно не поддерживается — нужен сетевой ключ/USB-over-IP либо программные лицензии). Утилита лицензирования `ring` (`ring license list`, `ring license activate …`) ставится отдельным дистрибутивом и требует Java.

## 25. Опасные команды и как не навредить

Общие правила: (1) перед разрушительной командой — `hostname`, `whoami`, `pwd`; (2) шаблон сначала раскрыть «вхолостую»: `echo rm -rf ./old_*` или `ls` с тем же шаблоном; (3) перед работами на ВМ — снимок (snapshot) в гипервизоре и свежая резервная копия баз; (4) держать открытой вторую SSH-сессию и доступ к консоли ВМ; (5) в скриптах — `set -euo pipefail` и `${VAR:?}` для обязательных переменных.

| Команда | Чем опасна | Как не навредить |
|---|---|---|
| `rm -rf ПУТЬ` | необратимо; пустая переменная превращает `rm -rf "$DIR"/*` в `rm -rf /*`; лишний пробел (`rm -rf / tmp/x`) и шаблоны удаляют не то | сначала `ls` с тем же шаблоном; `rm -rI` (один вопрос) или `rm -i`; в скриптах `"${DIR:?}"`; `--one-file-system`; корзины нет — только резервные копии и снимки. Встроенная защита `--preserve-root` (включена по умолчанию) отказывает только для самого `/`, но не для `/*`, `/etc`, `/var/lib/postgresql` и т. п. |
| `find … -delete`, `find … -exec rm` | `-delete`, поставленный раньше условий (`find . -delete -name '*.tmp'`), удаляет всё | `-delete` всегда последним; сначала тот же `find` с `-print` |
| `dd if=… of=/dev/sdX` | перепутанный `of=` затирает диск без вопросов | перед запуском `lsblk -o NAME,SIZE,SERIAL,MODEL,MOUNTPOINTS`; писать `status=progress conv=fsync`; не работать «по памяти» с именами `sdX` — они меняются между загрузками |
| `mkfs.*`, `wipefs -a`, `sgdisk --zap-all`, `parted … mklabel`, `pvcreate -ff`, `mdadm --zero-superblock`, `blkdiscard`, `cryptsetup luksFormat` | уничтожают файловую систему / метаданные / всё содержимое устройства | `lsblk -f`, `blkid`, `findmnt` — убедиться, что устройство пустое и не смонтировано; в fstab и скриптах использовать `UUID=`/`LABEL=` |
| `fsck`, `e2fsck`, `xfs_repair` на смонтированной ФС | повреждение файловой системы | только на размонтированной ФС (корень — из rescue/Live-образа) |
| `lvreduce`, `resize2fs` на уменьшение, `lvremove`, `vgremove`, `pvremove` | потеря данных; XFS уменьшить нельзя вообще | увеличение (`lvextend -r`) безопасно; уменьшение — только с копией и размонтировав; перечитать `lvs` перед `lvremove` |
| `chmod -R`, `chown -R` | на `/`, `/etc`, `/usr`, `/var` ломают sudo, ssh, сервисы; `chmod -R 777` — дыра и отказ sshd/PostgreSQL | проверить путь (`namei -l`, `ls -ld`); права каталогам и файлам раздельно через `find … -type d -exec chmod 755 {} +`; каталог данных PostgreSQL — владелец `postgres`, права `0700` (иначе сервер не запустится); `~/.ssh` — `700`, `authorized_keys` — `600` |
| `kill -9` для процессов `postgres` | SIGKILL серверного процесса заставляет postmaster аварийно сбросить **все** сеансы и выполнить восстановление после сбоя; SIGKILL самого postmaster оставляет осиротевшие процессы и занятую разделяемую память | запрос — `select pg_cancel_backend(pid)`, сеанс — `select pg_terminate_backend(pid)`; сервер — `pg_ctlcluster NN main stop -m fast`; `postmaster.pid` вручную не удалять |
| `kill -9 rphost`, `systemctl restart srv1cv8-…` в рабочее время | обрыв сеансов всех пользователей, откат незавершённых транзакций | сеансы завершать через `rac session … terminate`; перезапуск — в окно обслуживания, предварительно заблокировав вход (`rac infobase … update --sessions-deny=on`) |
| `cmd > файл`, `> файл` | перенаправление обнуляет файл **до** запуска команды: `sort f > f`, `cat a b > a` дают пустой файл | дозапись `>>`; `set -o noclobber` запрещает `>` затирать существующие файлы (см. блок кода раздела 22); правка на месте — `sed -i.bak`, `sponge`; копия `cp -a` перед правкой |
| `mv`, `cp` без `-i`/`-n` | молча перезаписывают существующие файлы | `-i` (спрашивать) или `-n` (не перезаписывать); `cp -a --backup=numbered` |
| `tar -x`, `unzip -o` в «не том» каталоге | перезапись существующих файлов, в т. ч. в `/` | сначала `tar -tf` / `unzip -l`; распаковывать с `-C КАТАЛОГ` / `-d КАТАЛОГ` в пустой каталог |
| `rsync --delete` | при опечатке в источнике (пустой или несмонтированный каталог) вычищает приёмник | сначала `-n`; проверять `mountpoint -q`; помнить о роли завершающего `/`; ограничитель `--max-delete=N` |
| `reboot`, `poweroff`, `shutdown`, `systemctl isolate` не на том сервере | остановка рабочего сервера 1С/СУБД | разные имена хостов и цвета приглашения; `hostname` перед командой; пакет ⊕ `molly-guard` (спрашивает имя хоста при перезагрузке по SSH); `shutdown -r +5` оставляет время на `shutdown -c` |
| `ufw enable`, `ufw reset`, `iptables -F`, `nft flush ruleset`, `netplan apply`, `ip link set … down`, `systemctl stop ssh` по SSH | потеря удалённого доступа | сначала правило для SSH; `netplan try` вместо `apply`; `sshd -t` перед перезапуском; иметь консоль гипервизора; страховка — отложенное задание `at now + 5 minutes` с командой отката (`ufw disable`), которое снимают после успешной проверки (`atrm`) |
| `apt remove`, `apt autoremove`, `apt full-upgrade`, `apt purge`, `do-release-upgrade` | удаление нужных пакетов «за компанию»; `purge postgresql-NN` может предложить удалить каталоги данных; обновление заменит сборку PostgreSQL для 1С обычной | читать список «будут УДАЛЕНЫ» до подтверждения; `apt-get -s …` (симуляция); `apt-mark hold` на СУБД; снимок ВМ перед обновлением |
| `pg_dropcluster`, `dropdb`, `DROP DATABASE`, `pg_resetwal`, `rm` в `pg_wal/` | безвозвратная потеря баз; ручное удаление WAL делает кластер невосстановимым | сначала резервная копия; при переполнении `pg_wal` искать причину (архивирование, слот репликации), а не удалять файлы |
| `pg_ctlcluster … stop -m immediate`, `pg_ctlcluster … stop --force`, `systemctl kill postgresql@…` | режим `immediate` — это аварийный останов без контрольной точки: при следующем запуске будет восстановление по WAL; `--force` при неудаче переходит к `immediate`, а затем убивает процесс | по умолчанию и так используется `fast` (откат транзакций + контрольная точка) — его и применяйте; сначала остановите сервер 1С, потом СУБД; запуск — в обратном порядке |
| `pg_upgradecluster`, `pg_createcluster`, `pg_restore --clean`, `psql -f` «не в ту базу/кластер» | на сервере с несколькими кластерами/версиями обёртка `pg_wrapper` подключает к кластеру по умолчанию, а не к тому, о котором вы думаете | перед запуском `pg_lsclusters`; явно указывать `--cluster NN/имя` или `-p ПОРТ`; убедиться, куда подключились: `sudo -u postgres psql -c "select current_database(), current_setting('port'), current_setting('data_directory'), version()"` |
| `rm` / `chown -R` / `chmod -R` в каталоге данных кластера 1С (`/home/usr1cv8/.1cv8/1C/1cv8/reg_1541/`) | в `reg_1541` лежат реестр кластера (`1CV8Clst.lst` — список ИБ и настройки) и журналы регистрации ИБ (`<идентификатор ИБ>/1Cv8Log/`); их удаление — потеря списка баз и истории; смена владельца — сервер не стартует | перед чисткой — остановить сервер 1С и сделать копию каталога (`sudo cp -a`); по практике сообщества безопасно удалять только каталоги сеансовых данных `snccntx*` и только при остановленном сервере; владелец — `usr1cv8:grp1cv8` |
| откат ВМ к снимку (checkpoint) гипервизора | возвращает и диски с базами: все данные PostgreSQL и 1С, введённые после снимка, пропадают; снимок «на лету» без согласования с СУБД может дать несогласованное состояние, после отката «уплывает» время | снимок — страховка на время работ, а не резервная копия: перед откатом сделать `pg_dump`/копию; снимки не хранить неделями (растёт разностный диск); после отката проверить `timedatectl`, `chronyc tracking`, `pg_lsclusters` |
| `crontab -r` | удаляет весь crontab без подтверждения (клавиша рядом с `-e`) | `crontab -l > ~/crontab.bak` перед правкой; `crontab -i -r` |
| `usermod -G группа user` без `-a` | убирает пользователя из всех остальных групп, включая `sudo` | всегда `usermod -aG` |
| правка `/etc/sudoers` не через `visudo` | синтаксическая ошибка лишает всех sudo | только `visudo` / `visudo -f /etc/sudoers.d/файл`; проверка `visudo -c`; не закрывать root-сессию, пока не проверили |
| правка `/etc/fstab` | ошибка — загрузка в emergency mode | `sudo findmnt --verify` и `sudo mount -a` до перезагрузки; для некритичных ресурсов опция `nofail` |
| `sysctl -w`, запись в `/proc`, `/sys` | неверные значения (например, завышенный `vm.nr_hugepages`) оставляют систему без памяти | сначала проверить на лету, и только потом записывать в `/etc/sysctl.d/` |
| `swapoff -a` | при нехватке ОЗУ — срабатывание OOM-killer | сначала `free -h`: помещается ли занятый swap в свободную память |
| вывод `curl URL`, переданный конвейером в `sudo bash` | выполнение непросмотренного кода с правами root | скачать, прочитать, проверить контрольную сумму/подпись, затем запускать |
| `docker system prune -a --volumes` | удаляет неиспользуемые тома с данными | перед запуском `docker volume ls`; без `--volumes`, если не уверены |
| `git reset --hard`, `git clean -fdx`, `git push --force` | потеря незакоммиченной работы / чужих коммитов | `git stash` и `git status` перед; `git clean -n` (показать); `--force-with-lease` |
| пароль в командной строке (`--db-pwd=…`, `PGPASSWORD=…`) | попадает в `~/.bash_history` и виден всем в `ps` | `~/.pgpass` (0600), `read -rs`, файлы окружения с правами 0600; команда, начатая с пробела, в историю не пишется (в Ubuntu `HISTCONTROL=ignoreboth`) |
| `chattr +i` и забыли | «Operation not permitted» даже для root при правке/удалении | `lsattr файл`; снять `chattr -i` |
| `echo 3 > /proc/sys/vm/drop_caches` | данные не теряются, но кэш ОС сбрасывается и СУБД резко замедляется | не использовать как «лечение памяти»: `buff/cache` — это не утечка |

## 26. Типичные ошибки и подводные камни

| Симптом | Причина | Решение |
|---|---|---|
| `command not found` | пакет не установлен; программа не в `PATH` (утилиты 1С, серверные утилиты PostgreSQL); опечатка | `command -v ИМЯ`; `sudo apt install ПАКЕТ` (подсказку даёт `command-not-found`); полный путь: `/opt/1cv8/x86_64/<версия>/rac`, `/usr/lib/postgresql/NN/bin/pg_controldata`; после установки — `hash -r` |
| `sudo: unable to resolve host ИМЯ` | имя хоста отсутствует в `/etc/hosts` | добавить строку `127.0.1.1 ИМЯ` (или реальный IP) в `/etc/hosts` |
| `Permission denied` при `sudo echo … > /etc/файл` | перенаправление выполняет оболочка обычного пользователя, а не sudo | передать текст конвейером в `sudo tee -a /etc/файл` (пример — в блоке кода раздела 2) или выполнить всё целиком: `sudo sh -c 'echo … >> /etc/файл'` |
| `Could not get lock /var/lib/dpkg/lock-frontend` | работает другой apt/dpkg или unattended-upgrades | дождаться завершения (`ps aux`, искать `apt`, `dpkg`, `unattended`); lock-файлы не удалять; после обрыва — `sudo dpkg --configure -a` |
| `apt-key: command not found` (26.04); предупреждение «Key is stored in legacy trusted.gpg keyring» (22.04/24.04) | `apt-key` устарела и в 26.04 удалена | ключ в `/etc/apt/keyrings/имя.gpg` (`gpg --dearmor`), в описании репозитория — `Signed-By:` |
| `No space left on device`, хотя `df -h` показывает место | закончились inode; место держат удалённые, но открытые файлы; переполнен другой раздел (`/boot`, `/var`) | `df -i`; `sudo lsof +L1` и перезапуск процесса-держателя; `sudo apt autoremove --purge`; `sudo journalctl --vacuum-size=500M` |
| корень заполнен, хотя диск ВМ большой | установщик Ubuntu (Subiquity) при LVM-разметке по умолчанию применяет политику `sizing-policy: scaled` и отдаёт корневому тому лишь часть группы томов: VG меньше 10 ГиБ — всё; 10–20 ГиБ — 10 ГиБ; 20–200 ГиБ — половину; больше 200 ГиБ — 100 ГиБ (остальное оставлено под снимки и расширение; в autoinstall отключается `sizing-policy: all`) | `sudo vgs` (колонка VFree) → `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv` — либо отдать свободное место отдельному тому под базы: `sudo lvcreate -l 100%FREE -n pgdata ubuntu-vg` |
| изменили юнит-файл — поведение прежнее | не выполнен `systemctl daemon-reload`; правили файл пакета в `/usr/lib/systemd/`, который перезапишет обновление | `sudo systemctl edit ИМЯ` (drop-in) → `daemon-reload` → `restart`; проверка `systemctl cat ИМЯ` |
| `postgresql.service` — «active (exited)», а база недоступна | это «зонтичный» юнит; реальный сервер — `postgresql@NN-main` | `pg_lsclusters`; `systemctl status postgresql@18-main`; лог в `/var/log/postgresql/` |
| `psql: … socket "/var/run/postgresql/.s.PGSQL.5432" failed: No such file or directory` | кластер не запущен или слушает другой порт | `pg_lsclusters`; `sudo pg_ctlcluster 18 main start`; читать лог кластера |
| `FATAL: Peer authentication failed for user "postgres"` | локальное подключение через сокет от другого пользователя ОС | `sudo -u postgres psql` либо `psql -h localhost -U postgres` с паролем |
| `FATAL: no pg_hba.conf entry for host …` | адрес клиента не разрешён | строка в `/etc/postgresql/NN/main/pg_hba.conf` + `sudo pg_ctlcluster NN main reload`; проверить `listen_addresses` (его смена требует restart) |
| `pg_ctl: command not found`, `initdb: command not found` | серверные утилиты не в `PATH` | `pg_ctlcluster` / `pg_createcluster` либо полный путь `/usr/lib/postgresql/NN/bin/…` |
| PostgreSQL не стартует: «data directory … has invalid permissions» | после `chmod -R`/`chown -R` или копирования без `-a` | `sudo chown -R postgres:postgres КАТАЛОГ && sudo chmod 700 КАТАЛОГ` |
| `rac` не подключается к `localhost:1545` | не запущен сервер администрирования `ras`; версия `rac` не совпадает с версией сервера | `sudo systemctl start ras-<версия>` или `./ras cluster --daemon`; `sudo ss -tlnp` — слушается ли 1545 |
| клиент 1С не подключается, хотя порт 1540 открыт | закрыты 1541 и 1560–1591; имя сервера, которое возвращает кластер, не разрешается у клиента или на самом сервере указывает на `127.0.1.1` | открыть весь набор портов; прописать имя сервера в DNS/`hosts` клиентов; на сервере проверить `getent hosts "$(hostname)"` |
| сменили `Port` в `sshd_config`, а sshd слушает 22 (24.04 и 26.04: в обоих выпусках `openssh-server` содержит `ssh.socket` и `sshd-socket-generator`) | сокет-активация `ssh.socket`: порт берётся генератором при `daemon-reload` | `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket`; узнать, активен ли сокет: `systemctl is-enabled ssh.socket`; на 22.04 сокет-активации по умолчанию нет — `sudo systemctl restart ssh` |
| правило sudoers с шаблоном (`… systemctl restart srv1cv8-*`) перестало работать после перехода на 26.04 | sudo-rs поддерживает `*` в аргументах только как отдельный последний аргумент; шаблон внутри аргумента не сопоставляется | вписать точные имена юнитов (по строке на команду); проверка — `sudo -l -U ПОЛЬЗОВАТЕЛЬ`; крайний вариант — классический `sudo.ws` |
| `last: command not found`, `lastb: command not found` на 26.04 | из `util-linux` эти команды убраны; `last` теперь в пакете `wtmpdb`, которого нет в стандартной установке; `lastb` не поставляется | `sudo apt install wtmpdb` → `last`; входы и отказы — `journalctl -u ssh --since today`, `loginctl list-sessions`, `who` |
| Hyper-V Manager не показывает IP-адрес гостя, резервное копирование ВМ «на лету» идёт без согласования | не установлены демоны `hv_kvp_daemon` / `hv_vss_daemon` | `sudo apt install linux-cloud-tools-common "linux-cloud-tools-$(uname -r)"` → `systemctl status hv-kvp-daemon hv-vss-daemon` (см. раздел 15) |
| после `ufw enable` пропал SSH | не было разрешающего правила | через консоль гипервизора: `sudo ufw allow OpenSSH` |
| после `netplan apply` пропала сеть | ошибка отступов YAML (только пробелы), неверное имя интерфейса, устаревший `gateway4` | `ip -br link` — имена; `sudo netplan try`; маршрут по умолчанию — `routes: [{to: default, via: АДРЕС}]`; права файла `chmod 600 /etc/netplan/*.yaml` |
| `bad interpreter: /bin/bash^M`, `$'\r': command not found` | скрипт сохранён в Windows с CRLF | `dos2unix script.sh` или `sed -i 's/\r$//' script.sh` |
| вместо кириллицы `????` | локаль не сгенерирована или `LANG=C`; кодировка терминала не UTF-8 | `locale -a`; `sudo locale-gen ru_RU.UTF-8`; `sudo update-locale LANG=ru_RU.UTF-8`; перелогиниться |
| время «уплыло» (в т. ч. после паузы/снимка ВМ) | нет синхронизации или неверный пояс | `timedatectl`; `chronyc tracking`; `sudo chronyc makestep`; `sudo timedatectl set-timezone …` |
| `Argument list too long` | шаблон `*` раскрылся в слишком длинную строку | `find КАТАЛОГ -name '*.tmp' -delete` или `find … -print0` + `xargs -0` |
| `umount: target is busy` | в каталоге есть открытые файлы или чей-то текущий каталог | `sudo lsof +D /mnt/x`; `sudo fuser -vm /mnt/x`; выйти из каталога |
| задание cron «не работает», хотя вручную — работает | у cron минимальный `PATH` и нет окружения профиля; относительные пути; неэкранированный `%` в crontab | полные пути; `PATH=` в начале crontab; `\%` вместо `%`; вывод в лог (`>> /var/log/x.log 2>&1`); `journalctl -u cron` |
| добавили пользователя в группу — прав всё равно нет | членство применяется при новом входе | перелогиниться (или `newgrp ГРУППА`); проверить `id` |
| `Too many open files` | лимит дескрипторов процесса | `cat /proc/PID/limits`; для сервиса — `LimitNOFILE=` через `systemctl edit` |
| процесс `rphost`/`postgres` исчез сам | OOM-killer при нехватке памяти | `journalctl -k -g 'out of memory'`; пересмотреть настройки памяти СУБД и сервера 1С, добавить ОЗУ/swap |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | сервер переустановлен или ВМ пересоздана с тем же адресом | убедиться, что это ожидаемо, затем `ssh-keygen -R ХОСТ` |
| на 26.04 старый скрипт ведёт себя иначе | базовые утилиты — uutils, `sudo` — sudo-rs (нет `-E`) | `КОМАНДА --version`; вызвать GNU-вариант (`gnusort`, `gnudate`…) или поставить `coreutils-from-gnu`; `sudo --preserve-env=VAR …` либо `sudo.ws` |
| `mkdir -p` в каталоге с ACL по умолчанию создаёт каталоги без унаследованных ACL (25.10/26.04) | известная ошибка rust-coreutils (LP #2138215) | после создания проверить `getfacl`; использовать `gnumkdir -p` |
| PostgreSQL на 26.04 заметно медленнее, чем на 24.04 | регрессия, связанная с изменением в ядре Linux 7.0 (описана в примечаниях к выпуску 26.04) | настроить huge pages (`vm.nr_hugepages`) и `huge_pages = on` в `postgresql.conf` |

## 27. Быстрая шпаргалка «задача → команда»

| Задача | Команда |
|---|---|
| Версия ОС, ядра, тип виртуализации | `lsb_release -a` · `uname -r` · `systemd-detect-virt` |
| Ресурсы: ядра, память, диски | `nproc` · `free -h` · `lsblk` · `df -hT` |
| Что грузит CPU / память | `top -c` (клавиши `P` / `M`) · `ps -eo pid,user,%cpu,%mem,rss,cmd --sort=-rss` |
| Что грузит диск | `iostat -xz 1` · `pidstat -d 1` · `sudo iotop -oPa` |
| Куда делось место | `df -hT` · `df -i` · `sudo du -xh --max-depth=1 /var` · `sudo ncdu -x /` |
| Файлы больше 1 ГБ | `sudo find / -xdev -type f -size +1G` |
| Удалённые, но не освобождённые файлы | `sudo lsof +L1` |
| Какие порты слушаются и кем | `sudo ss -tulpn` |
| Доступен ли порт на другом узле | `nc -zv -w 3 ХОСТ ПОРТ` |
| Адреса, маршруты, DNS | `ip -br a` · `ip r` · `resolvectl status` |
| Применить настройки сети безопасно | `sudo netplan try` |
| Состояние / перезапуск сервиса | `systemctl status ИМЯ` · `sudo systemctl restart ИМЯ` |
| Включить автозапуск и запустить | `sudo systemctl enable --now ИМЯ` |
| Журнал сервиса: конец / слежение | `journalctl -u ИМЯ -e` · `journalctl -u ИМЯ -f` |
| Ошибки с момента загрузки; упавшие юниты | `journalctl -p err -b` · `systemctl --failed` |
| Обновить систему | `sudo apt update && sudo apt full-upgrade` |
| Какой пакет владеет файлом | `dpkg -S /путь/к/файлу` |
| Заморозить версию пакета | `sudo apt-mark hold ПАКЕТ` |
| Нужна ли перезагрузка | `cat /var/run/reboot-required` |
| Создать администратора | `sudo adduser ivan` → `sudo usermod -aG sudo ivan` |
| Сменить пароль пользователя | `sudo passwd ivan` |
| Владелец и права | `sudo chown user:group ФАЙЛ` · `chmod 640 ФАЙЛ` |
| SSH-ключ и его установка на сервер | `ssh-keygen -t ed25519` → `ssh-copy-id user@host` |
| Передать файл / каталог | `scp ФАЙЛ user@host:/tmp/` · `rsync -avh --progress КАТАЛОГ/ user@host:/путь/` |
| Упаковать / распаковать | `tar -czf a.tar.gz КАТАЛОГ` · `tar -xzf a.tar.gz -C /куда` · `unzip a.zip -d /куда` |
| Найти текст в файлах / файл по имени | `grep -rn 'текст' /etc` · `sudo find / -xdev -name 'pg_hba.conf'` |
| Следить за логом | `tail -n 100 -F ФАЙЛ` |
| Расширить корень после увеличения диска ВМ | `sudo growpart /dev/sda 3` → `sudo pvresize /dev/sda3` → `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv` |
| Подключить новый диск | `lsblk -f` → `sudo mkfs.ext4 -L метка /dev/sdb1` → строка в `/etc/fstab` → `sudo mount -a` |
| Часовой пояс и синхронизация времени | `timedatectl` · `sudo timedatectl set-timezone Asia/Tashkent` · `chronyc tracking` |
| Русская локаль | `sudo locale-gen ru_RU.UTF-8` → `sudo update-locale LANG=ru_RU.UTF-8` |
| Firewall: состояние / разрешить порт | `sudo ufw status verbose` · `sudo ufw allow 5432/tcp` |
| Плановая перезагрузка / отмена | `sudo shutdown -r +5 'сообщение'` · `sudo shutdown -c` |
| Сессия, переживающая обрыв SSH | `tmux new -s work` → `tmux attach -t work` |
| PostgreSQL: кластеры и их состояние | `pg_lsclusters` |
| PostgreSQL: консоль администратора | `sudo -u postgres psql` |
| PostgreSQL: перечитать конфигурацию / перезапустить | `sudo pg_ctlcluster 18 main reload` · `sudo systemctl restart postgresql@18-main` |
| PostgreSQL: лог | `sudo tail -F /var/log/postgresql/postgresql-18-main.log` |
| PostgreSQL: готов ли принимать подключения | `pg_isready -h localhost -p 5432` |
| PostgreSQL: копия базы / восстановление | `sudo -u postgres pg_dump -Fc -f /backup/ib.dump ib` · `sudo -u postgres pg_restore -d ib_new -j 4 /backup/ib.dump` |
| PostgreSQL: размеры баз | `sudo -u postgres psql -c '\l+'` |
| PostgreSQL: завершить зависший сеанс | `sudo -u postgres psql -c 'select pg_terminate_backend(PID)'` |
| PostgreSQL: обновить статистику | `sudo -u postgres vacuumdb -d ib -z -j 4` |
| 1С: состояние / перезапуск сервера | `systemctl status srv1cv8-<версия>@default` · `sudo systemctl restart srv1cv8-<версия>@default` |
| 1С: процессы сервера и их память | `ps -u usr1cv8 -o pid,rss,etime,cmd --sort=-rss` |
| 1С: кластер, базы, сеансы | `./rac cluster list` · `./rac infobase --cluster=UUID summary list` · `./rac session --cluster=UUID list` |
| 1С: завершить сеанс | `./rac session --cluster=UUID terminate --session=UUID` |
| 1С: опубликовать базу на Apache | `sudo ./webinst -publish -apache24 -wsdir base -dir /var/www/base -connstr 'Srvr=localhost;Ref=base;' -confpath /etc/apache2/apache2.conf` |
| 1С: слушаются ли порты сервера | `sudo ss -tlnp` (искать 1540, 1541, 1545, 1560–1591) |

## 28. Алфавитный указатель «команда → категория»

Число после стрелки — номер раздела этого файла:
**1** Файлы и каталоги · **2** Текст · **3** Поиск и справка · **4** Права и пользователи · **5** Пакеты · **6** Сервисы, systemd, планировщики · **7** Процессы · **8** Мониторинг · **9** Диски, ФС, LVM, RAID · **10** Сеть · **11** Firewall · **12** SSH и передача файлов · **13** Архивы · **14** Ядро и модули · **15** Оборудование · **16** Время и локали · **17** Журналы · **18** Загрузка и GRUB · **19** Безопасность и криптография · **20** Контейнеры и виртуализация · **21** Разработка и отладка · **22** Встроенные команды bash · **23** PostgreSQL · **24** 1С.

**0–9, символы:** `1cestart` → 24 · `1cv8` → 24 · `1cv8c` → 24 · `1cv8s` → 24 · `7z` → 13 · `.` → 22 · `:` → 22 · `[` → 22 · `[[` → 22 · `((` → 22

**A:** `a2disconf` → 24 · `a2dismod` → 24 · `a2dissite` → 24 · `a2enconf` → 24 · `a2enmod` → 24 · `a2ensite` → 24 · `aa-complain` → 19 · `aa-enforce` → 19 · `aa-logprof` → 19 · `aa-status` → 19 · `ab` → 24 · `add-apt-repository` → 5 · `addgroup` → 4 · `addr2line` → 21 · `adduser` → 4 · `alias` → 22 · `anacron` → 6 · `apache2ctl` → 24 · `apachectl` → 24 · `apparmor_parser` → 19 · `apropos` → 3 · `apt` → 5 · `apt-cache` → 5 · `apt-config` → 5 · `apt-file` → 3 · `apt-get` → 5 · `apt-key` → 5 · `apt-mark` → 5 · `aptitude` → 5 · `ar` → 13 · `arp` → 10 · `arping` → 10 · `at` → 6 · `atop` → 8 · `atq` → 6 · `atrm` → 6 · `auditctl` → 17 · `aureport` → 17 · `ausearch` → 17 · `autossh` → 12 · `awk` → 2

**B:** `b2sum` → 19 · `badblocks` → 9 · `barman` → 23 · `base64` → 2 · `basename` → 1 · `bash` → 21, 22 · `batcat` → 2 · `batch` → 6 · `bc` → 2 · `bg` → 22 · `bind` → 22 · `biolatency-bpfcc` → 8 · `blkdiscard` → 9 · `blkid` → 9 · `blockdev` → 9 · `bootctl` → 18 · `bpftrace` → 8 · `break` → 22 · `bridge` → 10 · `btop` → 8 · `btrfs` → 9 · `builtin` → 22 · `bunzip2` → 13 · `busctl` → 6 · `byobu` → 7 · `bzcat` → 13 · `bzip2` → 13

**C:** `cal` → 16 · `caller` → 22 · `case` → 22 · `cat` → 2 · `cd` → 22 · `certbot` → 19 · `cfdisk` → 9 · `chage` → 4 · `chattr` → 1 · `chfn` → 4 · `chgrp` → 4 · `chkrootkit` → 19 · `chmod` → 4 · `choom` → 7 · `chown` → 4 · `chpasswd` → 4 · `chronyc` → 16 · `chroot` → 18 · `chrt` → 7 · `chsh` → 4 · `cksum` → 19 · `clamscan` → 19 · `clusterdb` → 23 · `cmake` → 21 · `cmp` → 2 · `column` → 2 · `comm` → 2 · `command` → 3, 22 · `compgen` → 22 · `complete` → 22 · `compopt` → 22 · `conntrack` → 11 · `continue` → 22 · `coproc` → 22 · `coredumpctl` → 6, 21 · `cp` → 1 · `cpio` → 13 · `cpupower` → 15 · `createdb` → 23 · `createuser` → 23 · `crontab` → 6 · `crserver` → 24 · `cryptsetup` → 9, 19 · `csplit` → 2 · `curl` → 10 · `cut` → 2

**D:** `date` → 16 · `dbgs` → 24 · `dd` → 1 · `debconf-set-selections` → 5 · `debconf-show` → 5 · `debsums` → 5 · `declare` → 22 · `delgroup` → 4 · `deluser` → 4 · `depmod` → 14 · `df` → 1 · `diff` → 2 · `dig` → 10 · `dirname` → 1 · `dirs` → 22 · `disown` → 22 · `dkms` → 14 · `dmesg` → 14, 17 · `dmidecode` → 15 · `dmsetup` → 9 · `do-release-upgrade` → 5 · `docker` → 20 · `dos2unix` → 2 · `dpkg` → 5 · `dpkg-deb` → 5 · `dpkg-query` → 5 · `dpkg-reconfigure` → 5 · `dracut` → 14 · `dropdb` → 23 · `dropuser` → 23 · `du` → 1 · `dumpe2fs` → 9

**E:** `e2fsck` → 9 · `e2label` → 9 · `echo` → 2, 22 · `ed` → 2 · `efibootmgr` → 18 · `egrep` → 2 · `eject` → 9 · `enable` → 22 · `env` → 7 · `envsubst` → 2 · `ethtool` → 10 · `eval` → 22 · `exec` → 22 · `execsnoop-bpfcc` → 8 · `exit` → 22 · `expand` → 2 · `export` → 22 · `exportfs` → 9 · `expr` → 2

**F:** `fail2ban-client` → 11 · `faillock` → 4 · `fallocate` → 1 · `false` → 22 · `fc` → 22 · `fdfind` → 3 · `fdisk` → 9 · `fg` → 22 · `fgrep` → 2 · `file` → 1 · `filefrag` → 9 · `find` → 3 · `findfs` → 9 · `findmnt` → 9 · `fio` → 9 · `firewall-cmd` → 11 · `flock` → 7 · `fmt` → 2 · `fold` → 2 · `for` → 22 · `free` → 8 · `freshclam` → 19 · `fsck` → 9 · `fsfreeze` → 9 · `fstrim` → 9 · `ftp` → 10 · `function` → 22 · `fuser` → 7 · `fwupdmgr` → 15

**G:** `g++` → 21 · `gcc` → 21 · `gcore` → 21 · `gdb` → 21 · `gdebi` → 5 · `gdisk` → 9 · `getcap` → 19 · `getconf` → 14 · `getent` → 4, 10 · `getfacl` → 1 · `getopts` → 22 · `git` → 21 · `glances` → 8 · `gpasswd` → 4 · `gpg` → 19 · `grep` → 2, 3 · `groupadd` → 4 · `groupdel` → 4 · `groupmod` → 4 · `groups` → 4 · `growpart` → 9 · `grpck` → 4 · `grub-editenv` → 18 · `grub-install` → 18 · `grub-mkconfig` → 18 · `grub-reboot` → 18 · `grub-set-default` → 18 · `gunzip` → 13 · `gzip` → 13

**H:** `halt` → 18 · `hash` → 22 · `hdparm` → 9 · `head` → 2 · `help` → 3, 22 · `hexdump` → 2 · `history` → 22 · `host` → 10 · `hostname` → 10 · `hostnamectl` → 6 · `htop` → 7 · `htpasswd` → 24 · `hwclock` → 16 · `hwinfo` → 15

**I:** `ibcmd` → 24 · `ibsrv` → 24 · `iconv` → 2 · `id` → 4 · `if` → 22 · `ifconfig` → 10 · `iftop` → 8 · `info` → 3 · `initdb` → 23 · `insmod` → 14 · `install` → 1 · `inxi` → 15 · `ionice` → 7 · `ioping` → 9 · `iostat` → 8 · `iotop` → 8 · `ip` → 10 · `ip6tables` → 11 · `ipcalc` → 10 · `ipcrm` → 7 · `ipcs` → 7 · `iperf3` → 10 · `ipset` → 11 · `iptables` → 11 · `iptables-restore` → 11 · `iptables-save` → 11 · `iptables-translate` → 11 · `iscsiadm` → 9

**J:** `jobs` → 22 · `join` → 2 · `journalctl` → 17 · `jq` → 2

**K:** `kdestroy` → 19 · `kill` → 7, 22 · `killall` → 7 · `kinit` → 19 · `klist` → 19 · `kpartx` → 9 · `ktutil` → 19 · `kvm-ok` → 20

**L:** `landscape-sysinfo` → 8 · `last` → 4 · `lastb` → 4 · `lastlog` → 4 · `lastlog2` → 4 · `ldconfig` → 21 · `ldd` → 21 · `less` → 2 · `let` → 22 · `lftp` → 12 · `ln` → 1 · `lnav` → 17 · `local` → 22 · `locale` → 16 · `locale-gen` → 16 · `localectl` → 16 · `localedef` → 16 · `locate` → 3 · `logger` → 17 · `loginctl` → 4 · `logname` → 4 · `logout` → 22 · `logrotate` → 17 · `losetup` → 9 · `ls` → 1 · `lsattr` → 1 · `lsb_release` → 5 · `lsblk` → 9 · `lscpu` → 15 · `lshw` → 15 · `lsinitramfs` → 14 · `lsinitrd` → 14 · `lslocks` → 7 · `lsmem` → 15 · `lsmod` → 14 · `lsns` → 7 · `lsof` → 7 · `lspci` → 15 · `lsscsi` → 9 · `lstopo-no-graphics` → 15 · `lsusb` → 15 · `lsvmbus` → 15 · `ltrace` → 21 · `lvchange` → 9 · `lvconvert` → 9 · `lvcreate` → 9 · `lvdisplay` → 9 · `lvextend` → 9 · `lvreduce` → 9 · `lvremove` → 9 · `lvrename` → 9 · `lvresize` → 9 · `lvs` → 9 · `lvscan` → 9 · `lxc` → 20 · `lxd` → 20 · `lynis` → 19 · `lz4` → 13

**M:** `machinectl` → 20 · `make` → 21 · `man` → 3 · `mapfile` → 22 · `mc` → 1 · `md5sum` → 19 · `mdadm` → 9 · `mkdir` → 1 · `mke2fs` → 9 · `mkfifo` → 1 · `mkfs.ext4` → 9 · `mkfs.vfat` → 9 · `mkfs.xfs` → 9 · `mkpasswd` → 4 · `mkswap` → 9 · `mktemp` → 1 · `modinfo` → 14 · `modprobe` → 14 · `mokutil` → 14 · `more` → 2 · `mount` → 9 · `mountpoint` → 9 · `mpstat` → 8 · `mtr` → 10 · `multipass` → 20 · `multipath` → 9 · `multitail` → 17 · `mv` → 1

**N:** `namei` → 1 · `nano` → 2 · `nc` → 10 · `ncal` → 16 · `ncdu` → 1 · `needrestart` → 5 · `netfilter-persistent` → 11 · `nethogs` → 8 · `netplan` → 10 · `netstat` → 10 · `networkctl` → 10 · `newgrp` → 4 · `nft` → 11 · `nice` → 7 · `nl` → 2 · `nload` → 8 · `nm` → 21 · `nmap` → 10 · `nmcli` → 10 · `nmon` → 8 · `nohup` → 7 · `nproc` → 7 · `nsenter` → 7 · `nslookup` → 10 · `nstat` → 10 · `ntpdate` → 16 · `numactl` → 7 · `numastat` → 8 · `numfmt` → 2 · `nvme` → 9

**O:** `objdump` → 21 · `od` → 2 · `oid2name` → 23 · `opensnoop-bpfcc` → 8 · `openssl` → 19

**P:** `parted` → 9 · `partprobe` → 9 · `partx` → 9 · `passwd` → 4 · `paste` → 2 · `patch` → 2 · `perf` → 8 · `pg-setup` → 23 · `pg-wrapper` → 23 · `pg_activity` → 23 · `pg_amcheck` → 23 · `pg_archivecleanup` → 23 · `pg_backupcluster` → 23 · `pg_basebackup` → 23 · `pg_checksums` → 23 · `pg_combinebackup` → 23 · `pg_config` → 23 · `pg_conftool` → 23 · `pg_controldata` → 23 · `pg_createcluster` → 23 · `pg_createsubscriber` → 23 · `pg_ctl` → 23 · `pg_ctlcluster` → 23 · `pg_dropcluster` → 23 · `pg_dump` → 23 · `pg_dumpall` → 23 · `pg_isready` → 23 · `pg_lsclusters` → 23 · `pg_probackup` → 23 · `pg_receivewal` → 23 · `pg_recvlogical` → 23 · `pg_renamecluster` → 23 · `pg_repack` → 23 · `pg_resetwal` → 23 · `pg_restore` → 23 · `pg_restorecluster` → 23 · `pg_rewind` → 23 · `pg_test_fsync` → 23 · `pg_test_timing` → 23 · `pg_upgrade` → 23 · `pg_upgradecluster` → 23 · `pg_verifybackup` → 23 · `pg_virtualenv` → 23 · `pg_waldump` → 23 · `pg_walsummary` → 23 · `pgbackrest` → 23 · `pgbadger` → 23 · `pgbench` → 23 · `pgbouncer` → 23 · `pgcli` → 23 · `pgrep` → 7 · `pidof` → 7 · `pidstat` → 8 · `pigz` → 13 · `ping` → 10 · `pip3` → 21 · `pkg-config` → 21 · `pkill` → 7 · `pmap` → 7 · `podman` → 20 · `popd` → 22 · `postgres` → 23 · `poweroff` → 18 · `printenv` → 7 · `printf` → 2, 22 · `prlimit` → 7 · `pro` → 5, 19 · `ps` → 7 · `psql` → 23 · `pstree` → 7 · `pushd` → 22 · `pv` → 2 · `pvcreate` → 9 · `pvdisplay` → 9 · `pvmove` → 9 · `pvremove` → 9 · `pvresize` → 9 · `pvs` → 9 · `pvscan` → 9 · `pwck` → 4 · `pwd` → 1, 22 · `pwdx` → 7 · `pwgen` → 19 · `python3` → 21

**Q:** `qemu-img` → 20

**R:** `rac` → 24 · `ragent` → 24 · `ras` → 24 · `rclone` → 12 · `read` → 22 · `readarray` → 22 · `readelf` → 21 · `readlink` → 1 · `readonly` → 22 · `realpath` → 1 · `reboot` → 18 · `reindexdb` → 23 · `rename` → 1 · `renice` → 7 · `rescan-scsi-bus.sh` → 9 · `resize2fs` → 9 · `resolvectl` → 10 · `return` → 22 · `rev` → 2 · `rg` → 2 · `ring` → 24 · `rkhunter` → 19 · `rm` → 1 · `rmdir` → 1 · `rmmod` → 14 · `rmngr` → 24 · `route` → 10 · `rphost` → 24 · `rsync` → 12 · `rsyslogd` → 17 · `run-parts` → 6 · `run0` → 4 · `runlevel` → 18 · `runuser` → 4

**S:** `sar` → 8 · `scp` → 12 · `screen` → 7 · `script` → 7 · `sdiff` → 2 · `sed` → 2 · `select` → 22 · `sensors` → 15 · `sensors-detect` → 15 · `seq` → 2 · `service` → 6 · `set` → 22 · `setcap` → 19 · `setfacl` → 1 · `setsid` → 7 · `setup-full-<версия>-x86_64.run` → 24 · `sfdisk` → 9 · `sftp` → 12 · `sg` → 4 · `sgdisk` → 9 · `sha256sum` → 19 · `sha512sum` → 19 · `shellcheck` → 21 · `shift` → 22 · `shopt` → 22 · `showmount` → 9 · `shred` → 1 · `shuf` → 2 · `shutdown` → 18 · `slabtop` → 8 · `sleep` → 7 · `smartctl` → 9 · `smbclient` → 10 · `smem` → 8 · `snap` → 5 · `socat` → 10 · `sort` → 2 · `sos` → 17 · `source` → 22 · `split` → 2 · `sponge` → 2 · `ss` → 10 · `ssh` → 12 · `ssh-add` → 12 · `ssh-agent` → 12 · `ssh-copy-id` → 12 · `ssh-import-id` → 12 · `ssh-keygen` → 12 · `ssh-keyscan` → 12 · `sshd` → 12 · `sshfs` → 12 · `stat` → 1 · `stdbuf` → 7 · `strace` → 21 · `strings` → 2 · `su` → 4 · `sudo` → 4 · `sudoedit` → 4 · `suspend` → 22 · `swapoff` → 9 · `swapon` → 9 · `sync` → 1 · `sysctl` → 14 · `systemctl` → 6, 18 · `systemd-analyze` → 6, 18 · `systemd-cat` → 6 · `systemd-cgls` → 6 · `systemd-cgtop` → 6 · `systemd-delta` → 6 · `systemd-detect-virt` → 6 · `systemd-escape` → 6 · `systemd-inhibit` → 6 · `systemd-nspawn` → 20 · `systemd-run` → 6 · `systemd-tmpfiles` → 6

**T:** `tac` → 2 · `tail` → 2 · `tar` → 13 · `taskset` → 7 · `tc` → 10 · `tcpconnect-bpfcc` → 8 · `tcpdump` → 10 · `tee` → 2 · `telinit` → 18 · `telnet` → 10 · `test` → 22 · `time` → 7, 22 · `timedatectl` → 16 · `timeout` → 7 · `times` → 22 · `tldr` → 3 · `tmux` → 7 · `top` → 7 · `touch` → 1 · `tr` → 2 · `trace-cmd` → 21 · `tracepath` → 10 · `traceroute` → 10 · `trap` → 22 · `tree` → 1 · `true` → 22 · `truncate` → 1 · `ts` → 2 · `tshark` → 10 · `tune2fs` → 9 · `type` → 3, 22 · `typeset` → 22 · `tzselect` → 16

**U:** `ubuntu-drivers` → 15 · `udevadm` → 9 · `ufw` → 11 · `ulimit` → 22 · `umask` → 4, 22 · `umount` → 9 · `unalias` → 22 · `uname` → 14 · `unattended-upgrade` → 5 · `unexpand` → 2 · `uninstaller-full` → 24 · `uniq` → 2 · `unix2dos` → 2 · `unlink` → 1 · `unrar` → 13 · `unset` → 22 · `unshare` → 7 · `unsquashfs` → 13 · `until` → 22 · `unxz` → 13 · `unzip` → 13 · `unzstd` → 13 · `update-alternatives` → 5 · `update-ca-certificates` → 19 · `update-grub` → 18 · `update-initramfs` → 14 · `update-locale` → 16 · `update-rc.d` → 6 · `updatedb` → 3 · `uptime` → 7, 8 · `useradd` → 4 · `userdel` → 4 · `usermod` → 4 · `users` → 4 · `uuidgen` → 19

**V:** `vacuumdb` → 23 · `vacuumlo` → 23 · `valgrind` → 21 · `VBoxControl` → 15 · `vgchange` → 9 · `vgcreate` → 9 · `vgdisplay` → 9 · `vgextend` → 9 · `vgreduce` → 9 · `vgremove` → 9 · `vgs` → 9 · `vgscan` → 9 · `vi` → 2 · `view` → 2 · `vigr` → 4 · `vim` → 2 · `vimdiff` → 2 · `vipw` → 4 · `virsh` → 20 · `virt-install` → 20 · `virt-what` → 15 · `visudo` → 4 · `vmstat` → 8 · `vmware-toolbox-cmd` → 15

**W:** `w` → 4 · `wait` → 22 · `wall` → 18 · `watch` → 7 · `wc` → 2 · `webinst` → 24 · `wg` → 10 · `wget` → 10 · `whatis` → 3 · `whereis` → 3 · `which` → 3 · `while` → 22 · `who` → 4 · `whoami` → 4 · `whois` → 10 · `wipefs` → 9

**X:** `xargs` → 2 · `xfs_admin` → 9 · `xfs_growfs` → 9 · `xfs_info` → 9 · `xfs_repair` → 9 · `xvfb-run` → 21 · `xxd` → 2 · `xz` → 13 · `xzcat` → 13

**Y:** `yes` → 2 · `yq` → 2

**Z:** `zcat` → 2, 13 · `zdiff` → 13 · `zdump` → 16 · `zfs` → 9 · `zgrep` → 2, 13 · `zip` → 13 · `zless` → 2, 13 · `zpool` → 9 · `zramctl` → 9 · `zstd` → 13 · `zstdcat` → 13

## Источники

Проверено по первоисточникам 10.10.2026 (поисковый бюджет сессии был исчерпан раньше, чем удалось сверить каждую man-страницу; флаги «классических» утилит coreutils/util-linux/procps/iproute2/LVM/OpenSSH даны по многолетне стабильному синтаксису и на сервере сверяются через `man`/`--help`).

- https://documentation.ubuntu.com/release-notes/26.04/ — дата выпуска 26.04 LTS (23.04.2026), срок поддержки, путь обновления.
- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — ядро 7.0, systemd 259, rust-coreutils (`cp`/`mv`/`rm` остались GNU, префикс `gnu`, пакеты `coreutils-from-gnu`/`coreutils-from-uutils`), sudo-rs и `sudo.ws`, chrony вместо systemd-timesyncd, APT 3.1 (удаление `apt-key`, команды `apt history-*`), dracut, удаление cgroup v1, OpenSSH 10.2, PostgreSQL 18, последний выпуск с поддержкой SysV-скриптов.
- https://documentation.ubuntu.com/release-notes/26.04/changes-since-previous-interim/ — версии (chrony 4.8, OpenSSL 3.5, docker.io 29, containerd 2.2, QEMU 10.2, libvirt 12.0), известные проблемы: регрессия PostgreSQL на Linux 7.0 и huge pages, `mkdir -p` и ACL (LP #2138215), CVE в rust-coreutils, pwfeedback в sudo-rs.
- https://documentation.ubuntu.com/release-notes/24.04/ — 24.04: ядро 6.8, systemd 255, netplan 1.0, deb822 `ubuntu.sources`, PostgreSQL 16, сокет-активация sshd через генератор, предустановленные инструменты производительности и замечание про sysstat, удаление pam_lastlog, срок поддержки.
- https://releases.ubuntu.com/26.04/ubuntu-26.04.1-live-server-amd64.manifest и https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.manifest — какие пакеты есть в стандартном серверном образе (основа пометок ⊕), версии apt 3.2.0 / 2.8.3, sudo-rs 0.2.13, rust-coreutils 0.8.0, gnu-coreutils 9.7, dracut 110, chrony 4.8.
- https://packages.ubuntu.com/resolute/amd64/gnu-coreutils/filelist и https://packages.ubuntu.com/resolute/amd64/coreutils-from-uutils/filelist — имена `/usr/bin/gnuls`, `gnucp`, `gnusort`…; `/usr/bin/cp|mv|rm|ls` принадлежат пакету-провайдеру.
- https://manpages.ubuntu.com/manpages/resolute/en/man8/sudo-rs.8.html — опции sudo-rs 0.2.13 (нет `-E`, есть `--preserve-env=list`).
- https://manpages.ubuntu.com/manpages/resolute/en/man8/apt.8.html — подкоманды apt 3.x (`why`, `why-not`, `satisfy`, `reinstall`, `edit-sources`).
- https://manpages.ubuntu.com/manpages/resolute/en/man8/update-initramfs.8.html — `update-initramfs` в 26.04 поставляется пакетом dracut.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/chronyc.1.html — команды `chronyc`.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/last.1.html и https://manpages.ubuntu.com/manpages/resolute/en/man8/lastlog2.8.html — в 26.04 `last` из wtmpdb, `lastlog2` из util-linux.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/run0.1.html — `run0` (systemd 259).
- https://manpages.ubuntu.com/manpages/noble/en/man8/netplan.8.html — подкоманды netplan (`generate`, `apply`, `try`, `get`, `set`, `status`).
- https://manpages.ubuntu.com/manpages/resolute/en/man1/7z.1.html — пакет `7zip`, команды `7z`.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/pg_lsclusters.1.html, …/pg_ctlcluster.1.html, …/pg_createcluster.1.html, …/pg_upgradecluster.1.html, …/pg_conftool.1.html, …/pg_backupcluster.1.html, …/pg_wrapper.1.html — синтаксис и опции утилит postgresql-common 290, правила выбора кластера, `start.conf`.
- https://ubuntu.com/server/docs/how-to/security/openssh-server/ — сервис `ssh`, `sshd -t`, `ssh-keygen -t ed25519`, `ssh-copy-id`, `ssh-import-id`.
- https://ubuntu.com/server/docs/how-to/databases/install-postgresql/ — пути `/etc/postgresql/<версия>/main`, `sudo -u postgres psql`, пример `pg_basebackup … -P -v -R`.
- https://www.postgresql.org/support/versioning/ и https://www.postgresql.org/ — поддерживаемые ветки и минорные версии на 13.08.2026, статус PostgreSQL 19 (Beta 4 от 24.09.2026).
- https://www.postgresql.org/docs/18/reference-client.html и https://www.postgresql.org/docs/18/reference-server.html — полный перечень клиентских и серверных утилит PostgreSQL 18.
- https://www.postgresql.org/docs/18/app-pgdump.html — опции `pg_dump` (форматы, `-j`, `-Z метод:уровень`, `--statistics`).
- https://www.postgresql.org/docs/18/release-18.html — новое в утилитах PostgreSQL 18 (`--statistics`, `--missing-stats-only`, `--swap`, контрольные суммы по умолчанию, `pg_verifybackup` для tar).
- https://postgrespro.ru/docs/postgrespro/17/binary-installation-on-linux — пути Postgres Pro Standard 17, `pg-setup`, `pg-wrapper`, имена пакетов и сервиса.
- https://1c.postgres.ru/ — условия распространения сборок Postgres Pro для 1С (команд установки на странице нет).
- https://infostart.ru/1c/articles/2498401/ и https://infostart.ru/1c/articles/2500569/ (практика сообщества; прочитаны только в поисковой выдаче) — каталог `/opt/1cv8/x86_64/<версия>/`, `systemctl link …/srv1cv8-<версия>@.service`, `ras cluster --port=1545`, `rac cluster list`, режимы работы `ibcmd`.
- https://its.1c.ru/db/v854doc/content/70/1 и https://its.1c.ru/db/metod8dev/content/5953/hdoc — официальная документация 1С (структура каталога установки, установка на Linux); текст через автоматическую загрузку получить не удалось — см. список страниц ИТС в отчёте.

### Проверено при рецензии (фактчекинг 10.10.2026)

Поисковый инструмент в сессии рецензента был недоступен (исчерпан лимит), поэтому проверка шла прямым чтением известных адресов. Что подтверждено, исправлено или осталось под вопросом — отмечено в тексте; пометка «⚠ не подтверждено» оставлена там, где первоисточник открыть не удалось.

- https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — перечитано: ядро 6.8→7.0, systemd 255→259, APT 2.7→3.1 (удалён `apt-key`, команды `history-list/-info/-undo/-redo/-rollback`), rust-coreutils (`cp`/`mv`/`rm` — GNU, префикс `gnu`, `coreutils-from-gnu`/`coreutils-from-uutils`), sudo-rs и `sudo.ws`, chrony с NTS, dracut, удаление cgroup v1, OpenSSH 1:10.2p1 без DSA, Python 3.14, PostgreSQL 18, netplan 1.2, последний выпуск с поддержкой SysV-скриптов.
- https://documentation.ubuntu.com/release-notes/26.04/changes-since-previous-interim/ — дословно: регрессия PostgreSQL на Linux 7.0 и «systems using huge pages are not affected»; LP #2138215 (`mkdir -p` и ACL); `pwfeedback` по умолчанию и `Defaults !pwfeedback`; chrony 4.8; OpenSSL 3.5.6; docker.io 29, containerd 2.2.2, runc 1.4.0, QEMU 10.2.1, libvirt 12.0.0; Apache2 `MemoryDenyWriteExecute` и mod-php (LP #2144455).
- https://documentation.ubuntu.com/release-notes/26.04/ и …/26.04/1/ — дата выпуска 23.04.2026, поддержка до апреля 2031; 26.04.1 включает обновления по 25.08.2026.
- https://documentation.ubuntu.com/release-notes/24.04/ — «security maintained for 5 years until 31 May 2029»; ядро 6.8, systemd 255.4, netplan 1.0, Python 3.12, PostgreSQL 16.2; sysstat установлен, но сервисы не всегда включены; `sshd_config` читает systemd-генератор для `ssh.socket`; `pam_lastlog.so` удалён; deb822 `ubuntu.sources`; dhcpcd вместо isc-dhclient.
- https://documentation.ubuntu.com/release-notes/22.04/ — ядро 5.15, systemd 249.11, OpenSSL 3.0.2, Python 3.10.4, PostgreSQL 14.2, поддержка до апреля 2027.
- https://releases.ubuntu.com/22.04/ubuntu-22.04.5-live-server-amd64.manifest, …/24.04/ubuntu-24.04.4-live-server-amd64.manifest, …/26.04/ubuntu-26.04.1-live-server-amd64.manifest — версии пакетов (таблица раздела 0) и наличие пакетов в стандартном образе; в манифесте 26.04.1 нет `wtmpdb`, `lastlog2`, `byobu`, `systemd-timesyncd`, `linux-cloud-tools-*`.
- https://packages.ubuntu.com/resolute/amd64/openssh-server/filelist — в 26.04 есть `/usr/lib/systemd/system/ssh.socket` и `/usr/lib/systemd/system-generators/sshd-socket-generator`.
- https://packages.ubuntu.com/resolute/amd64/util-linux/filelist, …/resolute/amd64/wtmpdb/filelist, …/resolute/amd64/lastlog2/filelist — в 26.04 `last` находится в пакете `wtmpdb` (`/usr/bin/last`), `lastb` не поставляется, `lastlog2` — отдельный пакет; `choom`, `findfs`, `blkdiscard` — в `util-linux`.
- https://packages.ubuntu.com/noble/amd64/grub2-common/filelist — `grub-install`, `grub-reboot`, `grub-set-default`, `update-grub` принадлежат `grub2-common`.
- https://packages.ubuntu.com/noble/amd64/linux-cloud-tools-common/filelist и https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/supported-ubuntu-virtual-machines-on-hyper-v — демоны `hv_kvp_daemon`/`hv_vss_daemon`/`hv_fcopy_daemon`, `lsvmbus`, юниты `hv-*-daemon.service`; службы интеграции Hyper-V для 22.04/24.04 «Built-in», рекомендация HWE-ядра и `linux-azure`.
- https://manpages.ubuntu.com/manpages/resolute/en/man8/apt.8.html — в apt 3.2.0 описаны `why` и `why-not`; описаний `history-*` на странице нет.
- https://manpages.ubuntu.com/manpages/resolute/en/man1/pg_ctlcluster.1.html — действия `start|stop|restart|reload|status|promote|logrotate`; `-m smart|fast|immediate` (по умолчанию `fast`); `--force`; перенаправление в systemctl при запуске от root.
- https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html — `sizing-policy: scaled` (по умолчанию) и правила выделения места корневому LV.
- https://github.com/trifectatechfoundation/sudo-rs — README: `sudo -E` не поддерживается; `pwfeedback` и `use_pty` включены по умолчанию; подстановочные знаки в аргументах sudoers — только как последний аргумент.
- https://www.postgresql.org/support/versioning/ — 18.6 / 17.11 / 16.15 / 15.19 / 14.24, конец поддержки 14-й ветки 12.11.2026; PostgreSQL 19 — Beta 4 от 24.09.2026.
- https://www.postgresql.org/docs/18/app-pgdump.html — `--statistics`, `--no-statistics` («This is the default»), `--statistics-only`, `--no-data`, `--no-schema`; `-Z метод[:детали]` (`gzip`, `lz4`, `zstd`, `none`); `-j` только для формата каталога.
- https://repo.postgrespro.ru/1c/, https://repo.postgrespro.ru/1c/1c-17/meta.json, https://repo.postgrespro.ru/1c/1c-17/keys/pgpro-repo-add.sh — ветки `1c-14`…`1c-18`; пакеты `postgrespro-1c-17*`; каталог `/opt/pgpro/1c-17`; `pg-setup initdb|service enable|service start`; Ubuntu 22.04/24.04/25.10/26.04.
- https://1c.postgres.ru/ — условия использования сборки «PostgreSQL для 1С» (кроме DBaaS и встраивания; без гарантий и поддержки).
- https://github.com/firstBitMarksistskaya/onec-docker (файлы `scripts/install.sh`, `server/docker-entrypoint.sh`, `server/Dockerfile`, `crs/docker-entrypoint.sh`; практика сообщества) — `setup-full-<версия>-x86_64.run --mode unattended --enable-components server,ws,…`; релизы младше 8.3.20 ставятся deb-пакетами; значения по умолчанию ragent (1540, 1541, 1560:1591, seclev 0, pingPeriod 1000, pingTimeout 5000, порт отладки 1550); `ras cluster --daemon --port 1545`; `crserver -port 1542 -d КАТАЛОГ`; пользователь `usr1cv8`, группа `grp1cv8`.
- https://wonderland.v8.1c.ru/blog/ и https://v8.1c.ru/platforma/avtonomnyy-server/ — актуальные упоминаемые версии платформы (8.5.5, план 8.5.6); общее описание автономного сервера.
- Не открылись: https://infostart.ru/1c/articles/2498401/ и …/2500569/ (HTTP 429); https://its.1c.ru/db/metod8dev/content/5953/hdoc, https://its.1c.ru/db/v8327doc, https://its.1c.ru/db/v854doc/content/70/1 (без входа — только навигация); https://kb.1ci.com/1C_Enterprise_Platform/Guides/Administrator_Guides/ (оглавление без дочерних страниц); https://postgrespro.ru/products/1c_build (404).

