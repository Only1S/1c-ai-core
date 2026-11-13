# Диски, разделы, файловые системы, LVM, swap и сетевые ФС (Ubuntu Server под 1С + PostgreSQL)

> Область: блочные устройства, разметка MBR/GPT, ext4/XFS, монтирование и `/etc/fstab`, поиск занятого места, LVM, расширение диска ВМ на лету, swap, mdadm, SSD/NVMe, планировщики ввода-вывода, тесты дисков, NFS/CIFS/sshfs, tmpfs, рекомендации по разметке сервера «1С:Предприятие 8» + PostgreSQL | Версии: Ubuntu Server 22.04 / 24.04 / 26.04 LTS; PostgreSQL 14–18 (19 — на 2026-09-24 только Beta 4); платформа 1С 8.3.x / 8.5.x; Postgres Pro 1C 14–18 | Актуальность: 2026-10-10

Условные обозначения: **[офиц.]** — утверждение из официальной документации (Canonical, PGDG, Postgres Professional, 1С, Microsoft, kernel.org, man-страницы); **[практика]** — устоявшаяся практика сообщества; **⚠ не подтверждено** — в этой сессии первоисточником не проверено, перед применением проверить на месте.

Статус проверки: 2026-10-10 файл прошёл независимую вычитку по первоисточникам (man-страницы jammy/noble/resolute на manpages.ubuntu.com, исходный код lvm2, growpart, curtin, systemd и ядра, release notes Ubuntu и util-linux, документация Microsoft, Red Hat, PostgreSQL, Postgres Pro, v8.1c.ru, конспекты документации платформы 8.3.27 из `kb/its-docs`). Исправленные места помечены в тексте версиями; всё, что проверить не удалось, по-прежнему несёт знак ⚠.

Все команды, меняющие диски, выполняются от root (`sudo`). Команды, уничтожающие данные (`mkfs.*`, `wipefs -a`, `pvcreate` на занятом устройстве, `lvreduce`, `mdadm --create`, `dd of=/dev/...`), перед запуском сверяйте с выводом `lsblk -f`.

## Кратко — главные факты и команды

1. **Посмотреть всё сразу**: `lsblk -f` (дерево устройств + ФС + UUID + точки монтирования), `df -hT` (заполнение ФС), `sudo pvs; sudo vgs; sudo lvs` (LVM), `swapon --show`, `findmnt --real`.
2. **Установщик Ubuntu Server (Subiquity) по умолчанию делает LVM и НЕ отдаёт весь диск корню**: том `ubuntu-vg/ubuntu-lv` получает весь VG только при VG < 10 ГиБ; 10–20 ГиБ → 10 ГиБ; 20–200 ГиБ → половину; > 200 ГиБ → 100 ГиБ [офиц., autoinstall reference]. Остаток виден в `vgs` (столбец `VFree`). Отдать всё корню: `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv`.
3. **Расширение диска ВМ без перезагрузки** (вариант Ubuntu по умолчанию, PV на разделе `sda3`): увеличить диск в гипервизоре → `echo 1 | sudo tee /sys/class/block/sda/device/rescan` → `sudo growpart /dev/sda 3` → `sudo pvresize /dev/sda3` → `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv`.
4. `lvextend -r` (`--resizefs`) сам увеличивает ФС (ext4 → `resize2fs`, XFS → `xfs_growfs`). Вручную: ext4 — `resize2fs /dev/VG/LV` (на смонтированной можно), XFS — `xfs_growfs /точка_монтирования` (только на смонтированной).
5. **XFS нельзя уменьшить**, ext4 можно уменьшить только размонтированной. Планируйте тома «с ростом», а не «с запасом на уменьшение».
6. В `/etc/fstab` используйте `UUID=` (или `/dev/mapper/VG-LV` для LVM), а не `/dev/sdX`: имена `sdX` между перезагрузками не гарантированы.
7. После правки `fstab`: `sudo systemctl daemon-reload && sudo findmnt --verify && sudo mount -a`. Ошибка в `fstab` без `nofail` → загрузка в emergency mode.
8. Для некритичных и сетевых томов (бэкапы, шары): `nofail`, для сетевых ещё `_netdev` и лучше `x-systemd.automount`.
9. Для томов PostgreSQL и 1С: `noatime`; TRIM — еженедельным `fstrim.timer`, а не опцией `discard`. `nobarrier`/`barrier=0` и `data=writeback` не применять.
10. **ext4 или XFS для PostgreSQL** — обе годятся; официальная документация PostgreSQL не ждёт «существенных изменений производительности» от смены ФС [офиц.]. ext4 — умолчание Ubuntu и проще в сопровождении; XFS чаще выбирают под большие тома данных.
11. **Каталог данных PostgreSQL не должен быть самой точкой монтирования** — создавайте подкаталог внутри смонтированного тома [офиц., PostgreSQL docs]. Проще всего монтировать том в `/var/lib/postgresql` (тогда `…/NN/main` автоматически подкаталог).
12. **Куда делось место**: `df -hT` → `sudo du -xhd1 / | sort -h` → `sudo ncdu -x /`. Если `df` показывает больше, чем `du`: удалённые, но открытые файлы — `sudo lsof +L1`. «No space left on device» при свободном месте: кончились inode — `df -i`.
13. **Swap на сервере БД не отключать**: Ubuntu Server обычно создаёт файл `/swap.img` (до 8 ГБ), но на маленьком корневом томе установщик может не создать его вовсе (раздел 9.1). Проверка: `swapon --show`, `free -h`. Файл подкачки: `fallocate -l 8G` (или `dd`) → `chmod 600` → `mkswap` → `swapon` → строка в `fstab`.
14. **Снапшот LVM — не бэкап.** Для PostgreSQL он согласован, только если ВЕСЬ кластер (данные + `pg_wal` + все табличные пространства) лежит на одном LV; иначе — `pg_basebackup`/`pg_dump`/`pg_probackup` [офиц., PostgreSQL docs].
15. **Планировщик ввода-вывода**: `cat /sys/block/sda/queue/scheduler`. Ядро само ставит `none` для многоочередных устройств (NVMe, многоочередной virtio) и `mq-deadline` для одноочередных. В гостевой ВМ на Hyper-V Microsoft рекомендует `none` [офиц.].
16. **Тест диска под БД**: `fio` (8k random, `--direct=1`), для WAL — `fio --fdatasync=1` и `pg_test_fsync`. `dd` без `oflag=direct` или `conv=fdatasync` измеряет кэш ОЗУ, а не диск.
17. **Выгрузка бэкапов на Windows-шару**: `cifs-utils`, файл `credentials` с правами 600, опции `uid=,gid=,file_mode=,dir_mode=,vers=3.1.1,_netdev,nofail,x-systemd.automount`. В скрипте бэкапа всегда проверять `mountpoint -q /mnt/…`, иначе при недоступной шаре бэкап ляжет в корневую ФС.
18. **Ubuntu 26.04: `/tmp` — это tmpfs в ОЗУ** (изменение появилось в 24.10) [офиц.]. Сервер 1С по умолчанию пишет временные файлы в `/tmp`, значит на 26.04 они расходуют память, а не диск — см. раздел 15.
19. В ВМ SMART недоступен (диск виртуальный) — здоровье носителей контролируется на хосте; `mdadm` внутри гостя обычно не нужен.
20. Резервируйте в VG 10–20 % свободных экстентов: это и место под снапшоты, и «аварийный запас» для быстрого расширения тома.
21. **Emergency mode и заблокированный root.** В Ubuntu root по умолчанию заблокирован, а `sulogin` даёт оболочку без пароля только с ключом `--force` [офиц., sulogin(8)]. Заранее проверьте, что аварийная консоль ВМ действительно пустит вас чинить `fstab` (раздел 5.4), иначе понадобится `init=/bin/bash` или загрузка с ISO.
22. **Версии утилит различаются между LTS**: `parted --fix` есть только с parted 3.5 (нет в 22.04); `lsblk -N` — с util-linux 2.39 (нет в 22.04); `mkswap --file` — с 2.40 (только 26.04); `lvreduce` без `-r` на 26.04 сам отказывается резать занятую ФС, а на 22.04/24.04 — нет (раздел 1).

## 1. Версии и отличия релизов Ubuntu

| | 22.04 LTS (jammy) | 24.04 LTS (noble) | 26.04 LTS (resolute) |
|---|---|---|---|
| Ядро GA / HWE | 5.15 / 6.8 (22.04.5) [офиц.] | 6.8 / 7.0 (24.04.5, сентябрь 2026; в 24.04.4 было 6.17) [офиц.] | 7.0 [офиц.] |
| systemd | 249.11 [офиц.] | 255.4 [офиц.] | 259.5 [офиц.] |
| util-linux (`lsblk`, `mount`, `findmnt`, `fstrim`, `swapon`, `wipefs`) | 2.37.2 [офиц.] | 2.39.3 [офиц.] | 2.41.3 [офиц.] |
| lvm2 | 2.03.11 [офиц.] | 2.03.16 [офиц.] | 2.03.31 [офиц.] |
| e2fsprogs | 1.46.5 [офиц.] | 1.47.0 [офиц.] | 1.47.2 [офиц.] |
| xfsprogs | 5.13.0 [офиц.] | 6.6.0 [офиц.] | 6.18.0 [офиц.] |
| parted | 3.4 (без `--fix`) [офиц.] | 3.6 [офиц.] | ⚠ не проверено (ожидаемо ≥ 3.6) |
| mdadm | 4.2 [офиц.] | 4.3 [офиц.] | 4.5 [офиц.] |
| PostgreSQL в архиве Ubuntu | 14 | 16 | 18 |
| `/tmp` | каталог на корневой ФС | каталог на корневой ФС | **tmpfs** (с 24.10) [офиц.] |
| coreutils (`df`, `du`, `dd`) | GNU | GNU | rust-coreutils (uutils); `cp`, `mv`, `rm` пока GNU [офиц.] |
| initramfs | initramfs-tools | initramfs-tools | dracut по умолчанию (с 25.10) [офиц.] |
| Стандартная поддержка до | апрель 2027 | апрель 2029 | апрель 2031 [офиц.] |

Версии для 22.04 сверены по страницам manpages.ubuntu.com/manpages/jammy (строка «Provided by»): systemd 249.11-0ubuntu3.22, util-linux 2.37.2-4ubuntu3.6, lvm2 2.03.11-2.1ubuntu5, e2fsprogs 1.46.5-2ubuntu1.2, xfsprogs 5.13.0-1ubuntu2.1, parted 3.4-2build1; ядра — по ubuntu.com/kernel/lifecycle (22.04.5 → 6.8, 24.04.4 → 6.17, 24.04.5 → 7.0). Точную версию на своём сервере дают `lsblk --version`, `sudo lvm version`, `mkfs.ext4 -V`, `mkfs.xfs -V`, `parted --version`, `mdadm --version`, `uname -r`.

Важные следствия:

- **HWE-ядро 24.04 с выпуска 24.04.5 — 7.0** (образ `ubuntu-24.04.5-live-server-amd64.iso` датирован 2026-09-09; в 24.04.4 HWE-ядром было 6.17) [офиц., ubuntu.com/kernel/lifecycle, releases.ubuntu.com]. Системы с пакетом `linux-generic-hwe-24.04` получают 7.0 обычным обновлением; системы на GA-ядре (`linux-generic`) остаются на 6.8. ⚠ не подтверждено в этой сессии: какое ядро серверный установщик ставит по умолчанию с образа 24.04.5 (исторически Ubuntu Server ставил GA-ядро, а HWE выбиралось пунктом загрузочного меню «…with the HWE kernel»). Какое ядро у вас — `uname -r`; от него зависят, например, умолчания планировщика и поддержка новых форматов XFS.
- **util-linux — что в какой версии появилось** [офиц., ReleaseNotes на kernel.org]: 2.38 — `X-fstrim.notrim` в `fstab`, `mount -m/--mkdir`, `lsblk -A/--noempty`, `lsblk -y`; 2.39 — `lsblk -N/--nvme` и `-v/--virtio`, столбцы `ID-LINK`, `PARTN`, `MQ`, новый файловый API монтирования в `mount`; 2.40 — `mkswap -F/--file` (создаёт файл подкачки сам), `lsblk -Q/--filter`. Значит, в 22.04 (2.37.2) нет `lsblk -N`, `X-fstrim.notrim` и `mount --mkdir`; `mkswap --file` есть только в 26.04.
- **parted `-f/--fix`** появился в parted 3.5 (в NEWS — альфа 3.4.64 от 2022-03-30) [офиц., NEWS parted]: в 22.04 (parted 3.4) опции нет — там резервную GPT после увеличения диска чинит `sgdisk -e` или `growpart`.
- **lvm2 в 26.04** (≥ 2.03.17): у `lvextend`/`lvreduce` появилась опция `--fs` (`checksize`, `resize`, `resize_fsadm`, `ignore`) и `--fsmode`; `-r` теперь эквивалентно `--fs resize` и вызывает утилиту ФС напрямую. В 22.04/24.04 `-r` работает через `fsadm`. Для повседневного `lvextend -r` разницы нет. Если ни `--fs`, ни `-r` не указаны, действует `checksize` [офиц., исходный код lvm2 `tools/lvresize.c`: «Use checksize when no fs option is specified»]: `lvextend` просто увеличивает LV, не трогая ФС, а `lvreduce` **отказывается** уменьшать том, если отрезаемое место занято ФС. В 22.04/24.04 такой защиты нет.
- **xfsprogs**: умолчания `mkfs.xfs` различаются между релизами (раздел 4.2) — ФС, созданная на 26.04, может не смонтироваться на старом ядре.
- **mdadm 4.5 в 26.04**: из man исчезла фраза об автоматическом внутреннем bitmap для массивов от 100 ГБ (раздел 10) — задавайте `--bitmap=internal` явно.
- **26.04, rust-coreutils**: `df`, `du`, `dd` — реализация на Rust; Canonical прямо пишет, что она «not fully compatible yet». Вернуть GNU: `sudo apt install coreutils-from-gnu coreutils-from-uutils- --allow-remove-essential` [офиц., release notes]. ⚠ не подтверждено: поведение каждого флага из этой статьи на uutils в этой сессии не проверялось.
- **26.04, dmraid удалён** (пакет убран из архива ещё в 24.10) — для программного RAID только `mdadm` [офиц., release notes 26.04].
- **PostgreSQL на октябрь 2026** (перепроверено по postgresql.org 2026-10-10): поддерживаются 14–18 (текущие минорные 18.6, 17.11, 16.15, 15.19, 14.24 — выпуск 13.08.2026); 14 снимается с поддержки 12 ноября 2026; 19 — Beta 4 от 24.09.2026, финального выпуска ещё нет [офиц., postgresql.org]. 1С поддерживает Postgres Pro 1C 18.4 / 17.10 / 16.14 / 15.18 / 14.23 и «PostgreSQL с патчем 1С» 18.4-1.1C / 17.10-2.1C / 16.14-1.1C / 15.18-1.1C / 14.23-1.1C [офиц., v8.1c.ru].

## 2. Обзор блочных устройств: lsblk, blkid, имена устройств

### 2.1. Как называются диски

| Имя | Что это |
|---|---|
| `/dev/sda`, `/dev/sdb`… разделы `sda1`, `sda2` | SCSI/SATA/SAS/USB; виртуальные диски Hyper-V (SCSI-контроллер), VMware, VirtualBox (SATA/SCSI) |
| `/dev/vda`… разделы `vda1` | virtio-blk (KVM, Proxmox) |
| `/dev/nvme0n1`… разделы `nvme0n1p1` | NVMe: контроллер 0, пространство имён 1, раздел 1 |
| `/dev/xvda` | Xen |
| `/dev/mapper/VG-LV`, `/dev/VG/LV`, `/dev/dm-N` | device-mapper: LVM, LUKS, multipath. Дефис в имени VG/LV в `/dev/mapper` удваивается: `ubuntu-vg`/`ubuntu-lv` → `/dev/mapper/ubuntu--vg-ubuntu--lv` |
| `/dev/md0` | программный RAID mdadm |
| `/dev/sr0`, `/dev/loopN` | CD/DVD; loop-устройства (snap-пакеты) |

Имена `sdX` назначаются в порядке обнаружения и могут поменяться после добавления диска или перезагрузки. Стабильные ссылки создаёт udev в `/dev/disk/`:

```bash
ls -l /dev/disk/by-uuid/      # UUID файловой системы (то, что пишут в fstab)
ls -l /dev/disk/by-id/        # модель+серийный номер, wwn-…, nvme-…, dm-name-…, lvm-pv-uuid-…
ls -l /dev/disk/by-path/      # физический путь (контроллер/порт)
ls -l /dev/disk/by-label/     # метка ФС
ls -l /dev/disk/by-partuuid/  # UUID раздела GPT (PARTUUID)
```

### 2.2. lsblk

`lsblk` читает sysfs и базу udev, root не нужен (но часть столбцов без root может быть пустой).

```bash
lsblk                         # дерево: NAME MAJ:MIN RM SIZE RO TYPE MOUNTPOINTS
lsblk -f                      # ФС: NAME FSTYPE FSVER LABEL UUID FSAVAIL FSUSE% MOUNTPOINTS
lsblk -p                      # полные пути (/dev/sda1 вместо sda1)
lsblk -d                      # только сами диски, без разделов и «держателей»
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINTS
lsblk -d -o NAME,SIZE,MODEL,SERIAL,TRAN,ROTA,SCHED,RA,DISC-GRAN,DISC-MAX
lsblk -t                      # топология: выравнивание, MIN-IO, OPT-IO, PHY-SEC, LOG-SEC, ROTA, SCHED, RQ-SIZE, RA
lsblk -D                      # поддержка discard (TRIM/UNMAP): DISC-GRAN, DISC-MAX не нулевые = поддерживается
lsblk -S                      # только SCSI-устройства (HCTL, вендор, модель)
lsblk -N                      # только NVMe (util-linux >= 2.39: есть в 24.04 и 26.04, в 22.04 опции нет)
lsblk -v                      # только virtio-диски (тоже с util-linux 2.39; это НЕ «verbose»)
lsblk -m                      # владелец/группа/права узлов устройств
lsblk -s /dev/mapper/ubuntu--vg-ubuntu--lv   # обратное дерево: на чём лежит LV
lsblk -b -dn -o SIZE /dev/sda # размер в байтах без заголовка (для скриптов)
lsblk -J -o NAME,SIZE,FSTYPE,MOUNTPOINTS     # JSON
lsblk -O                      # все доступные столбцы; список столбцов: lsblk --help
```

Полезные столбцы для `-o`: `NAME, KNAME, PATH, SIZE, TYPE (disk/part/lvm/raid1/rom/loop), FSTYPE, FSVER, LABEL, UUID, PARTUUID, PARTLABEL, PTTYPE (gpt/dos), MOUNTPOINTS, FSSIZE, FSUSED, FSAVAIL, FSUSE%, MODEL, SERIAL, WWN, TRAN (sata/sas/nvme/virtio/usb), HCTL, ROTA (1 = вращающийся диск), SCHED, RQ-SIZE, RA (read-ahead в КиБ), PHY-SEC, LOG-SEC, DISC-GRAN, DISC-MAX, RO, RM`.

Пример типичной свежей установки Ubuntu Server на диск 100 ГБ (UEFI):

```text
NAME                      SIZE TYPE FSTYPE      MOUNTPOINTS
sda                       100G disk
├─sda1                      1G part vfat        /boot/efi
├─sda2                      2G part ext4        /boot
└─sda3                     97G part LVM2_member
  └─ubuntu--vg-ubuntu--lv 48.5G lvm ext4        /
```

Здесь видно главное: раздел `sda3` — 97 ГБ, а корневой том — только половина; вторая половина свободна в VG.

### 2.3. blkid

`blkid` читает сигнатуры напрямую с устройств (нужен root, иначе покажет кэш или ничего).

```bash
sudo blkid                                   # все устройства: UUID, TYPE, LABEL, PARTUUID
sudo blkid /dev/sdb1                         # одно устройство
sudo blkid -s UUID -o value /dev/vg_pg/lv_pgdata   # только UUID — удобно подставлять в fstab
sudo blkid -o export /dev/sdb1               # в виде KEY=value
sudo blkid -U 1b2c3d4e-…                     # найти устройство по UUID
sudo blkid -L pgdata                         # найти устройство по метке
sudo blkid -p /dev/sdb                       # низкоуровневая проверка, минуя кэш (видит и таблицу разделов: PTTYPE)
```

### 2.4. Размеры секторов и выравнивание

```bash
sudo blockdev --getss --getpbsz /dev/sda     # логический и физический размер сектора (512/4096)
sudo blockdev --getsize64 /dev/sda           # размер устройства в байтах
cat /sys/block/sda/queue/rotational          # 1 = HDD, 0 = SSD (в ВМ значение часто не отражает реальный носитель)
sudo parted /dev/sda align-check optimal 1   # выровнен ли раздел 1
```

Современные `fdisk`, `parted`, `sgdisk`, установщик Ubuntu по умолчанию начинают разделы с 1 МиБ (сектор 2048) — это корректное выравнивание и для 4K-дисков, и для RAID, и для VHDX.

## 3. Таблицы разделов и инструменты разметки

### 3.1. MBR и GPT

| | MBR (msdos, «dos») | GPT |
|---|---|---|
| Максимальный размер диска | 2 ТиБ (при секторе 512 байт) | практически без ограничений (ЗиБ) |
| Число разделов | 4 первичных, либо 3 первичных + расширенный с логическими | 128 по умолчанию |
| Избыточность | нет | резервная копия заголовка и таблицы в конце диска, CRC |
| Идентификатор раздела | тип — 1 байт (`83` Linux, `8e` LVM, `82` swap, `fd` RAID) | GUID типа; у каждого раздела свой PARTUUID и имя (PARTLABEL) |
| Загрузка | BIOS | UEFI — нужен раздел ESP (FAT32, `/boot/efi`); BIOS+GPT — нужен «BIOS boot» раздел 1 МиБ без ФС для GRUB |

Практика:

- Установщик Ubuntu Server размечает системный диск в GPT. ВМ Hyper-V поколения 2 — это UEFI, значит GPT + ESP.
- Диски данных проще вообще не делить на разделы, а отдавать целиком под LVM (`pvcreate /dev/sdb`): при расширении виртуального диска не нужен шаг `growpart`. Минус — другие ОС и утилиты видят такой диск «пустым»; если это риск, создайте один GPT-раздел на весь диск.
- **После увеличения диска с GPT резервная копия таблицы оказывается не в конце диска.** `growpart` и `parted` исправляют это сами; вручную — `sudo sgdisk -e /dev/sda`. Microsoft отдельно предупреждает: после изменения размера VHD/VHDX утилиты разметки предложат исправить первичный и резервный заголовки GPT, и это безопасно [офиц., Microsoft Learn].

### 3.2. fdisk (и sfdisk, cfdisk)

`fdisk` (пакет `fdisk`, часть util-linux) умеет и MBR, и GPT. Изменения пишутся на диск только командой `w`.

```bash
sudo fdisk -l                 # все диски и разделы (тип таблицы: Disklabel type: gpt/dos)
sudo fdisk -l /dev/sdb        # один диск
sudo fdisk -x /dev/sdb        # подробно (UUID разделов, имена, атрибуты)
sudo fdisk /dev/sdb           # интерактивно
```

Команды внутри `fdisk`: `m` — справка; `p` — показать таблицу; `F` — показать свободное место; `g` — создать новую пустую GPT; `o` — новую пустую MBR; `n` — новый раздел; `d` — удалить; `t` — сменить тип (в GPT можно вводить псевдонимы `linux`, `lvm`, `swap`, `uefi`, `raid`; в MBR — коды `83`, `8e`, `82`, `fd`); `w` — записать и выйти; `q` — выйти без записи.

`sfdisk` — скриптовый вариант; главное применение — резервная копия таблицы разделов:

```bash
sudo sfdisk -d /dev/sda > /root/sda.partition-table.dump   # дамп таблицы (текст)
sudo sfdisk /dev/sda < /root/sda.partition-table.dump      # восстановление (ОПАСНО: перезаписывает таблицу)
echo ", +" | sudo sfdisk -N 3 /dev/sda                     # растянуть раздел 3 до конца свободного места (то, что делает growpart)
echo ", +" | sudo sfdisk --no-reread -N 3 /dev/sda         # то же на диске со смонтированными разделами; затем sudo partx -u /dev/sda
```

На диске, разделы которого смонтированы, `sfdisk` без `--no-reread` (или `--force`) откажется работать («This disk is currently in use»); после записи таблицы ядру нужно сообщить новый размер раздела — `partx -u`. Для расширения системного диска проще и безопаснее `growpart` (раздел 8.3), он делает оба шага сам.

`cfdisk /dev/sdb` — то же в псевдографике (ncurses), удобно вручную.

### 3.3. gdisk и sgdisk (только GPT)

Пакет `gdisk` (в серверной установке обычно есть; иначе `sudo apt install gdisk`).

```bash
sudo gdisk -l /dev/sda                         # показать таблицу и её состояние (MBR: protective, GPT: present)
sudo sgdisk -p /dev/sda                        # то же, скриптовый вариант
sudo sgdisk -e /dev/sda                        # перенести резервные структуры GPT в конец диска (после увеличения диска)
sudo sgdisk -n 1:0:0 -t 1:8e00 -c 1:pgdata /dev/sdb   # создать раздел 1 на всё свободное место, тип Linux LVM, имя pgdata
sudo sgdisk --backup=/root/sda.gpt /dev/sda    # двоичная резервная копия GPT
sudo sgdisk --load-backup=/root/sda.gpt /dev/sda
sudo sgdisk -R /dev/sdNEW /dev/sdOLD           # скопировать таблицу с sdOLD на sdNEW (порядок аргументов: -R ЦЕЛЬ ИСТОЧНИК!)
sudo sgdisk -G /dev/sdNEW                      # после копирования — сгенерировать новые GUID диска и разделов
sudo sgdisk --zap-all /dev/sdb                 # уничтожить GPT и MBR на диске
```

Коды типов `sgdisk`: `8300` Linux filesystem, `8e00` Linux LVM, `8200` Linux swap, `fd00` Linux RAID, `ef00` EFI System, `ef02` BIOS boot.

### 3.4. parted и partprobe

`parted` применяет изменения **немедленно** (нет отдельной команды «записать»).

```bash
sudo parted -l                                   # все диски
sudo parted /dev/sdb print free                  # таблица и свободные промежутки
sudo parted /dev/sdb unit s print                # в секторах
sudo parted -s /dev/sdb mklabel gpt              # новая таблица GPT (уничтожает старую!)
sudo parted -s -a optimal /dev/sdb mkpart primary 1MiB 100%   # один раздел на весь диск
sudo parted -s /dev/sdb set 1 lvm on             # пометить раздел 1 как LVM
sudo parted -s /dev/sdb name 1 pgdata            # имя раздела (GPT)
sudo parted /dev/sda resizepart 3 100%           # растянуть раздел 3 до конца диска (спросит Fix для GPT и Yes для занятого раздела)
sudo parted -s -f /dev/sda print                 # --fix: в скриптовом режиме автоматически исправить GPT после увеличения диска (parted >= 3.5: 24.04/26.04)
```

`-f/--fix` («automatically answer "fix" to exceptions in script mode») добавлен в parted 3.5 [офиц., NEWS parted: альфа 3.4.64 от 2022-03-30]; в Ubuntu 22.04 (parted 3.4-2build1) этой опции нет — man jammy её не описывает. На 22.04 используйте `sudo sgdisk -e /dev/sda` либо интерактивный `parted` (ответ `Fix`).

Перечитать таблицу разделов в ядре без перезагрузки:

```bash
sudo partprobe                 # все диски (пакет parted)
sudo partprobe -s /dev/sdb     # один диск, с выводом итога
sudo partx -u /dev/sdb         # обновить сведения ядра о разделах (util-linux); работает и когда другие разделы диска заняты
sudo blockdev --rereadpt /dev/sdb   # старый ioctl BLKRRPART — отказывает, если какой-либо раздел диска смонтирован
```

### 3.5. wipefs — стереть сигнатуры

`wipefs` не затирает данные, а удаляет «магические» сигнатуры ФС, RAID, LVM и таблиц разделов, чтобы устройство выглядело чистым.

```bash
sudo wipefs /dev/sdb               # только показать сигнатуры и их смещения
sudo wipefs -n -a /dev/sdb         # «сухой» прогон: что было бы стёрто
sudo wipefs -a -b /dev/sdb         # стереть всё, сохранив копии в ~/wipefs-sdb-<смещение>.bak
sudo wipefs -a /dev/sdb1           # стереть сигнатуру ФС на разделе
sudo wipefs -a -t ext4 /dev/sdb1   # только сигнатуры указанного типа
```

Восстановление из копии (пример из man): `dd if=~/wipefs-sdb-0x00000438.bak of=/dev/sdb seek=$((0x00000438)) bs=1 conv=notrunc`. Для стирания таблицы разделов на используемом диске нужен `-f`.

Когда нужно: диск раньше был в mdadm/LVM/ZFS и `pvcreate`/`mkfs` ругается на старые сигнатуры; перед повторным использованием диска из старого RAID (дополнительно `mdadm --zero-superblock`).

## 4. Файловые системы: создание, настройка, проверка

### 4.1. mkfs.ext4

`mkfs.ext4` = `mke2fs -t ext4` (пакет `e2fsprogs`). Умолчания берутся из `/etc/mke2fs.conf`.

```bash
sudo mkfs.ext4 -L pgdata -m 1 /dev/vg_pg/lv_pgdata      # метка pgdata, резерв root 1 % вместо 5 %
sudo mkfs.ext4 -L backup -m 0 -T largefile /dev/vg_bak/lv_backup   # том под крупные файлы бэкапов: 1 inode на 1 МиБ
sudo mkfs.ext4 -n /dev/vg_pg/lv_pgdata                  # ничего не создавать, только показать параметры и резервные суперблоки
sudo mkfs.ext4 -E lazy_itable_init=0,lazy_journal_init=0 /dev/sdb1   # полная инициализация сразу (перед тестами производительности)
sudo mkfs.ext4 -E nodiscard /dev/sdb1                   # не делать discard всего устройства при создании (быстрее на тонких/больших томах)
sudo mkfs.ext4 -G 4096 /dev/sdb1                        # рекомендация Microsoft для динамических VHDX (см. ниже)
```

Ключевые опции:

| Опция | Смысл |
|---|---|
| `-L метка` | метка тома, до 16 байт |
| `-m N` | процент блоков, зарезервированных для root; **по умолчанию 5 %** |
| `-T тип` | профиль из `/etc/mke2fs.conf`: `largefile` (inode на 1 МиБ), `largefile4` (inode на 4 МиБ), `news`/`small` (много мелких файлов) |
| `-i байт` | байт на один inode (умолчание 16384); **после создания изменить нельзя** |
| `-N число` | задать число inode напрямую |
| `-b размер` | размер блока (умолчание 4096) |
| `-E lazy_itable_init=0/1`, `lazy_journal_init=0/1` | отложенная (фоновая, поток `ext4lazyinit`) инициализация таблиц inode и журнала; по умолчанию включена |
| `-E discard` / `nodiscard` | TRIM всего устройства при создании; по умолчанию `discard` |
| `-E stride=…,stripe_width=…` | выравнивание под RAID (в блоках ФС) |
| `-E root_owner=uid:gid` | владелец корневого каталога новой ФС |
| `-O фича,^фича` | включить/выключить возможности (`metadata_csum`, `64bit`, `has_journal`…) |
| `-F` | принудительно (например, устройство — не раздел) |

Практические замечания:

- **Резерв 5 % на томе PostgreSQL процессу `postgres` недоступен** (он не root). На томе 500 ГБ это 25 ГБ «мёртвого» места. Ставьте `-m 1`; для тома бэкапов — `-m 0`. Резерв можно менять на смонтированной ФС (`tune2fs -m`), поэтому это ещё и аварийный резерв: при переполнении тома `sudo tune2fs -m 0 /dev/…` мгновенно возвращает зарезервированное место.
- **Не используйте `-T largefile4` для тома данных PostgreSQL под 1С.** Информационная база 1С — это десятки тысяч таблиц и индексов, каждая — минимум один файл плюс `_fsm`/`_vm`; база ERP даёт сотни тысяч файлов. Умолчания (inode на 16 КиБ) хватает с огромным запасом; `largefile` допустим только для тома бэкапов.
- Microsoft для ext4 на **динамических VHDX** рекомендует `mkfs.ext4 -G 4096` и создавать VHDX с `-BlockSizeBytes 1MB`, чтобы файл VHDX не раздувался на почти пустой ФС [офиц., Microsoft Learn].

### 4.2. mkfs.xfs

Пакет `xfsprogs` (в Ubuntu Server установлен по умолчанию; иначе `sudo apt install xfsprogs`).

```bash
sudo mkfs.xfs -L pgdata /dev/vg_pg/lv_pgdata     # метка до 12 символов
sudo mkfs.xfs -f -L pgdata /dev/vg_pg/lv_pgdata  # -f: перезаписать обнаруженную старую ФС
sudo mkfs.xfs -N /dev/vg_pg/lv_pgdata            # только показать, с какими параметрами была бы создана
sudo mkfs.xfs -K /dev/sdb1                       # не делать discard при создании
sudo mkfs.xfs -d su=64k,sw=4 /dev/md0            # выравнивание под RAID: stripe unit 64 КиБ, 4 диска данных
sudo xfs_info /pgdata                            # параметры смонтированной XFS
```

Умолчания (xfsprogs 6.6 в 24.04 и 6.18 в 26.04): размер блока 4096, сектор 512, `crc=1` (контрольные суммы метаданных, формат V5), `reflink=1`, `finobt=1`, `inobtcount=1`, `bigtime=1` (даты до 2486 года), `rmapbt` включается «когда возможно», размер inode 512 байт, журнал от 64 МБ до 2 ГБ внутри ФС. Минимальный размер ФС — 300 МБ. inode выделяются динамически (лимит — `-i maxpct`, по умолчанию 25 % для ФС меньше 1 ТБ, 5 % — меньше 50 ТБ, 1 % — больше), поэтому «кончились inode» для XFS практически нетипично.

Отличия умолчаний по релизам [офиц., man mkfs.xfs для jammy/noble/resolute]:

| Возможность | 22.04 (xfsprogs 5.13) | 24.04 (6.6) | 26.04 (6.18) |
|---|---|---|---|
| `crc`, `finobt`, `reflink` | включены | включены | включены |
| `bigtime` (даты после 2038 года) | **выключен** | включён | включён |
| `inobtcount` | **выключен** | включён | включён |
| `rmapbt` | выключен | «when possible» | «when possible» |
| `nrext64` (64-битные счётчики экстентов) | — (возможность появилась позже) | выключен | включается «when possible» |
| `exchange`, `parent` | — | — | выключены |
| Минимум 300 МБ данных и 64 МБ журнала | в man не указан (минимум AG — 16 МиБ) | есть | есть |

Что реально получилось, показывают `mkfs.xfs -N /dev/…` (до создания) и `xfs_info /точка` (после). На 22.04 том, которому жить дольше 2038 года, создавайте с `-m bigtime=1,inobtcount=1`.

Совместимость: XFS, созданная новым `mkfs.xfs`, может не монтироваться на заметно более старом ядре (новые флаги формата): ядро сообщает «Superblock has unknown incompatible features … Filesystem cannot be safely mounted by this kernel». Практический пример: `nrext64=1` из 26.04 требует ядра не старше 5.19 (⚠ версия ядра — по памяти рецензента), то есть такой том не смонтируется на 22.04 с GA-ядром 5.15. Если том планируется переносить на старую систему — создавайте его там либо с профилем совместимости. Готовые профили лежат в `/usr/share/xfsprogs/mkfs/` (`ls /usr/share/xfsprogs/mkfs/`), применяются так: `mkfs.xfs -c options=/usr/share/xfsprogs/mkfs/<файл>.conf …`.

### 4.3. tune2fs, e2label, dumpe2fs (ext4)

```bash
sudo tune2fs -l /dev/vg_pg/lv_pgdata                   # суперблок: размеры, резерв, счётчики, возможности, состояние
sudo tune2fs -l /dev/vg_pg/lv_pgdata | grep -Ei 'block count|reserved block|inode count|free|state|features|mount count|last checked'
sudo tune2fs -m 1 /dev/vg_pg/lv_pgdata                 # резерв root 1 % (можно на смонтированной ФС)
sudo tune2fs -m 0 /dev/vg_bak/lv_backup                # убрать резерв полностью
sudo tune2fs -r 262144 /dev/vg_pg/lv_pgdata            # резерв в блоках (262144 × 4 КиБ = 1 ГиБ)
sudo tune2fs -L pgdata /dev/vg_pg/lv_pgdata            # метка
sudo tune2fs -U random /dev/sdb1                       # новый случайный UUID (после клонирования диска)
sudo tune2fs -c 0 -i 0 /dev/sdb1                       # отключить проверки «по числу монтирований» и «по времени»
sudo tune2fs -e remount-ro /dev/sdb1                   # поведение при ошибке ФС: continue | remount-ro | panic
sudo tune2fs -o journal_data_writeback /dev/sdb1       # умолчательные опции монтирования в суперблоке (НЕ делать для БД)
sudo e2label /dev/sdb1                                 # показать метку
sudo e2label /dev/sdb1 backup                          # задать метку (до 16 символов)
sudo dumpe2fs -h /dev/sdb1                             # то же, что tune2fs -l, плюс сведения о журнале
```

### 4.4. xfs_admin, xfs_info, xfs_growfs

```bash
sudo xfs_admin -l /dev/vg_pg/lv_pgdata           # показать метку
sudo xfs_admin -u /dev/vg_pg/lv_pgdata           # показать UUID
sudo xfs_admin -L pgdata /dev/vg_pg/lv_pgdata    # задать метку (до 12 символов); "--" очищает метку
sudo xfs_admin -U generate /dev/vg_pg/lv_clone   # новый UUID (после клонирования тома / для постоянного снапшота)
sudo xfs_info /pgdata                            # геометрия ФС
sudo xfs_growfs /pgdata                          # растянуть ФС на всё устройство (аргумент — точка монтирования)
sudo xfs_growfs -D 26214400 /pgdata              # до заданного размера в блоках ФС
```

Согласно man: «Devices that are mounted cannot be modified» — `xfs_admin` меняет метку/UUID только на размонтированной ФС [офиц., xfs_admin(8) noble]. `xfs_growfs`, наоборот, работает только на смонтированной. Метку смонтированной XFS можно посмотреть и сменить через `xfs_io` — команда `label [ -c | -s label ]`: «On filesystems that support online label manipulation, get, set, or clear the filesystem label» [офиц., xfs_io(8) noble]: `sudo xfs_io -c 'label' /pgdata` (показать), `sudo xfs_io -c 'label -s pgdata' /pgdata` (задать), `sudo xfs_io -c 'label -c' /pgdata` (очистить); `sudo xfs_io -c 'fsuuid' /pgdata` печатает UUID смонтированной ФС. UUID онлайн не меняется — только `xfs_admin -U` на размонтированной ФС.

Копия XFS (LVM-снапшот, клон диска) имеет тот же UUID, что оригинал, и рядом с ним не смонтируется («Filesystem has duplicate UUID»): монтируйте с `-o nouuid` или смените UUID через `xfs_admin -U generate`.

### 4.5. Проверка и восстановление: fsck, e2fsck, xfs_repair

**Никогда не запускайте `e2fsck`/`xfs_repair` с исправлением на смонтированной ФС.** Сначала остановите PostgreSQL и сервер 1С, размонтируйте том.

```bash
sudo fsck -N /dev/sdb1                 # ничего не делать, показать, какая программа проверки была бы вызвана
sudo e2fsck -f /dev/vg_pg/lv_pgdata    # ext4: принудительная полная проверка, вопросы задаются интерактивно
sudo e2fsck -fp /dev/vg_pg/lv_pgdata   # -p: автоматически чинить безопасное («preen»)
sudo e2fsck -fy /dev/vg_pg/lv_pgdata   # -y: отвечать «да» на всё (когда -p остановился с «UNEXPECTED INCONSISTENCY; RUN fsck MANUALLY»)
sudo e2fsck -fn /dev/vg_pg/lv_pgdata   # -n: только чтение, ничего не исправлять
sudo e2fsck -b 32768 /dev/sdb1         # использовать резервный суперблок (список — mkfs.ext4 -n или dumpe2fs)
sudo e2fsck -fD /dev/sdb1              # дополнительно оптимизировать каталоги
```

Код возврата `e2fsck` — сумма: 0 нет ошибок; 1 ошибки исправлены; 2 исправлены, нужна перезагрузка; 4 остались неисправленные ошибки; 8 операционная ошибка; 16 ошибка синтаксиса; 32 отменено пользователем; 128 ошибка библиотеки.

XFS: `fsck.xfs` ничего не проверяет (заглушка для загрузки), инструмент — `xfs_repair`:

```bash
sudo xfs_repair -n /dev/vg_pg/lv_pgdata   # только проверка, без изменений (код 1 = найдены повреждения)
sudo xfs_repair /dev/vg_pg/lv_pgdata      # проверка и исправление (ФС размонтирована)
sudo xfs_repair -v -m 2048 /dev/…         # подробно, ограничить память 2 ГБ
```

Если `xfs_repair` отказывается работать из-за «грязного» журнала (код 2): сначала смонтируйте и сразу размонтируйте ФС — журнал проиграется. `xfs_repair -L` (обнулить журнал) — крайняя мера: по man, ФС после этого «will likely appear to be corrupt», возможна потеря файлов.

Проверка корневой ФС (её нельзя размонтировать):

- параметры ядра на одну загрузку (в меню GRUB клавиша `e`, дописать в строку `linux`): `fsck.mode=force fsck.repair=yes` — их обрабатывает `systemd-fsck`;
- либо загрузиться с установочного ISO (режим восстановления/shell) и проверить том оттуда: `vgchange -ay`, затем `e2fsck -f /dev/ubuntu-vg/ubuntu-lv`.

Где искать следы проблем с диском/ФС:

```bash
sudo dmesg -T | grep -Ei 'ext4|xfs|i/o error|buffer i/o|blk_update_request|critical medium|remount'
sudo journalctl -k -p err -b            # ошибки ядра за текущую загрузку
sudo journalctl -b -u 'systemd-fsck*'   # что делал fsck при загрузке
findmnt -no OPTIONS /pgdata             # если тут появилось ro — ФС перемонтирована только для чтения после ошибки
```

**Проверка ext4 без остановки служб: e2scrub и снапшот LVM.** `e2scrub` проверяет (но не чинит) метаданные смонтированной ext4 на LVM: создаёт временный снапшот `<имя_LV>.e2scrub`, запускает на нём `e2fsck`, затем удаляет снапшот; для этого в VG должно быть не меньше 256 МиБ свободного места, иначе том пропускается [офиц., e2scrub(8)]. `e2scrub_all` обходит все LV с ext2/3/4, при найденных ошибках помечает ФС для `fsck` при следующем монтировании, при отсутствии ошибок вызывает `fstrim` [офиц., e2scrub_all(8)].

```bash
sudo e2scrub -n /dev/ubuntu-vg/ubuntu-lv      # показать, какие команды были бы выполнены
sudo e2scrub /dev/vg_pg/lv_pgdata             # проверить один том «на ходу» (код возврата — как у e2fsck)
sudo e2scrub_all -n                           # что было бы проверено на всей системе
sudo e2scrub -r /dev/vg_pg/lv_pgdata          # убрать «зависший» снапшот *.e2scrub после прерванной проверки
systemctl list-timers 'e2scrub*'              # запускается ли проверка по расписанию
```

[практика, состав пакета подтверждён 11.10.2026 списком файлов `e2fsprogs` для 24.04 на packages.ubuntu.com (`e2scrub_all.timer`, `e2scrub_all.service`, `e2scrub_reap.service`, `/etc/e2scrub.conf`, `/etc/cron.d/e2scrub_all`); периодичность и поведение — как и раньше, не подтверждено первоисточником в этой сессии] Пакет `e2fsprogs` в Debian/Ubuntu поставляет таймер `e2scrub_all.timer` (еженедельный запуск) и службу `e2scrub_reap.service`; на свежей установке Ubuntu Server с половиной VG в запасе таймер действительно будет периодически создавать короткоживущие снапшоты ext4-томов. На нагруженном томе БД снапшот в 256 МиБ может переполниться раньше, чем закончится проверка, — это безвредно (проверка прерывается, оригинал цел), но даёт всплеск ввода-вывода из-за copy-on-write (раздел 7.7). Если это мешает: `sudo systemctl disable --now e2scrub_all.timer`. Для XFS такого штатного механизма по расписанию нет: проверка — `xfs_repair -n` на размонтированном томе. Проверять `xfs_repair -n` несмонтированный снапшот работающего тома можно, но журнал снапшота не проигран, поэтому возможны ложные сообщения о несогласованности — такой результат годится только как грубая оценка.

Тот же приём вручную для ext4 — снять снапшот и проверить его только для чтения: `sudo lvcreate -s -n chk -L 2G /dev/vg_pg/lv_pgdata && sudo e2fsck -fn /dev/vg_pg/chk; sudo lvremove -y /dev/vg_pg/chk`.

### 4.6. ext4 или XFS для PostgreSQL

Что говорят первоисточники:

- **PostgreSQL [офиц.]**: «Generally, any file system with POSIX semantics can be used for PostgreSQL… all other things being equal, one should not expect major performance or behavior changes merely from switching file systems or making minor file system configuration changes» (раздел «Creating a Database Cluster → File Systems»).
- **Postgres Professional, приложение «Конфигурирование Postgres Pro для решений 1С» [офиц.]**: про выбор ФС ничего не сказано; требование к дискам — «RAID 0–1 или SSD».
- **1С (ИТС)**: в открытых материалах, доступных в этой сессии, рекомендации по выбору ФС не найдено (см. список закрытых страниц в отчёте). В документации платформы 8.3.27 (конспекты глав «Требования», «Установка», «Запуск компонентов» в `kb/its-docs`) ext4/XFS не упоминаются вовсе: требования сформулированы как «жёсткий диск или SSD», права пользователя `usr1cv8` на каталог данных кластера и на каталог временных файлов.
- **Тесты [практика]**:
  - EDB (Томаш Вондра, «Postgres vs. File Systems: A Performance Comparison», 10.10.2022; ядро 5.17, pgbench, SSD) — прочитано: на чтение все ФС близки; на запись ext4 и XFS явно быстрее — на 16-ядерном Xeon с NVMe при scale 10000 около 30 тыс. tps против примерно 4–6 тыс. у ZFS и 6,5 тыс. у Btrfs; Btrfs автор считает неподходящей для БД; ZFS медленнее, но даёт самую ровную задержку.
  - Phoronix, май 2025, ядро 6.15 — XFS быстрее всех в тестах PostgreSQL 17 на запись; Phoronix, март 2026, ядра 6.12→7.0 — ext4 заметно прибавила, на 7.0 разрыв с XFS «very close». ⚠ не подтверждено: обе страницы Phoronix при проверке отвечали HTTP 403, цифры известны только по пересказу поисковой выдачи — на них не опираться.

| Критерий | ext4 | XFS |
|---|---|---|
| Умолчание установщика Ubuntu | да | нет |
| Увеличение | на смонтированной (`resize2fs`) | только на смонтированной (`xfs_growfs`) |
| Уменьшение | да, на размонтированной | **нет** |
| inode | фиксированное число при создании | динамические |
| Резерв для root | 5 % по умолчанию (настраивается) | нет аналога |
| Параллельная запись многими процессами | хорошо | лучше масштабируется (allocation groups) |
| reflink (`cp --reflink`) | нет | да (по умолчанию) |
| Минимальный размер | единицы МБ | 300 МБ |
| Восстановление | `e2fsck` (зрелый, предсказуемый) | `xfs_repair` (на больших томах требователен к ОЗУ) |
| Метка | до 16 байт | до 12 символов |

Возможность reflink в XFS полезна для PostgreSQL: `pg_upgrade --clone`, а в PostgreSQL 18 — параметр `file_copy_method = clone` (быстрое клонирование файлов при `CREATE DATABASE … STRATEGY=FILE_COPY`) [офиц.: параметр описан в документации PostgreSQL 18].

Вывод [практика]: для системного тома, каталога сервера 1С и небольших баз берите ext4 — меньше сюрпризов и есть уменьшение. Для больших томов данных PostgreSQL (сотни ГБ и более, много одновременных сеансов) разумен XFS. Смешивать можно. Btrfs и ZFS (copy-on-write) под данные PostgreSQL для 1С без специальной настройки не используйте.

Опции монтирования для обеих ФС под БД: `defaults,noatime`. Не использовать: `barrier=0`/`nobarrier` (в XFS опция удалена из ядра; в ext4 отключает сброс кэша диска — риск порчи при сбое питания), `data=writeback`, `sync`. По документации PostgreSQL, отключать барьеры допустимо только при контроллере с исправной батареей (BBU) и осознанно.

## 5. Монтирование: mount, umount, findmnt, /etc/fstab

### 5.1. mount и umount

```bash
sudo mount /dev/vg_pg/lv_pgdata /pgdata                 # тип ФС определяется автоматически
sudo mount -t ext4 -o noatime /dev/sdb1 /mnt/data       # явно тип и опции
sudo mount UUID=1b2c3d4e-… /pgdata                      # по UUID; также LABEL=pgdata
sudo mount /pgdata                                      # по записи в fstab (достаточно точки или устройства)
sudo mount -a                                           # смонтировать всё из fstab (кроме noauto)
sudo mount -fav                                         # -f «понарошку» + -a + -v: проверить fstab, ничего не монтируя
sudo mount -o remount,noatime /pgdata                   # сменить опции без размонтирования
sudo mount -o remount,rw /                              # вернуть корень в режим записи (emergency mode)
sudo mount -o remount,ro /mnt/data                      # только чтение
sudo mount --bind /srv/data /mnt/data-alias             # показать каталог во втором месте
sudo mount -o loop,ro ubuntu.iso /mnt/iso               # смонтировать образ
sudo mount -o ro,nouuid /dev/vg_pg/snap_pgdata /mnt/snap   # XFS-снапшот рядом с оригиналом

sudo umount /pgdata                                     # размонтировать (по точке или устройству)
sudo umount -l /mnt/share                               # lazy: отцепить сейчас, освободить, когда перестанут пользоваться
sudo umount -f /mnt/nfs                                 # принудительно (для недоступного NFS)
```

`umount: target is busy` — найдите, кто держит том:

```bash
sudo lsof +f -- /pgdata        # открытые файлы на этой ФС
sudo fuser -vm /pgdata         # процессы, использующие ФС (в т.ч. с текущим каталогом на ней)
```

Проверка «смонтировано ли» для скриптов: `mountpoint -q /backup && echo yes`.

### 5.2. findmnt

```bash
findmnt                          # дерево всех монтирований (из /proc/self/mountinfo)
findmnt --real                   # только реальные ФС, без proc/sysfs/cgroup и т.п.
findmnt /pgdata                  # одна точка: TARGET SOURCE FSTYPE OPTIONS
findmnt -T /var/lib/postgresql/18/main   # на какой ФС лежит произвольный путь
findmnt -S UUID=1b2c3d4e-…       # по источнику
findmnt -t ext4,xfs              # по типам
findmnt -D                       # в стиле df
findmnt -no OPTIONS /pgdata      # только действующие опции монтирования
findmnt -o TARGET,SOURCE,FSTYPE,SIZE,AVAIL,USE%,OPTIONS --real
findmnt --fstab                  # разобрать /etc/fstab (а не текущее состояние)
sudo findmnt --verify            # проверить fstab: синтаксис, существование устройств и точек, типы ФС
sudo findmnt --verify --verbose  # то же с перечислением всех проверок
findmnt --poll --mountpoint /mnt/share   # следить за событиями mount/umount/remount
```

### 5.3. Формат /etc/fstab

Шесть полей через пробелы/табуляцию:

```text
# <что монтировать>        <куда>     <тип>  <опции>              <dump> <pass>
UUID=1b2c3d4e-…            /pgdata    ext4   defaults,noatime     0      2
```

1. **fs_spec** — устройство: `UUID=…`, `LABEL=…`, `PARTUUID=…`, `PARTLABEL=…`, путь `/dev/mapper/vg-lv`, для сети `сервер:/путь` (NFS) или `//сервер/шара` (CIFS).
2. **fs_file** — точка монтирования; для swap — `none`. Пробел в пути кодируется как `\040`.
3. **fs_vfstype** — `ext4`, `xfs`, `vfat`, `swap`, `nfs`, `cifs`, `tmpfs`…
4. **fs_mntops** — опции через запятую.
5. **fs_freq** — для `dump`, всегда `0`.
6. **fs_passno** — порядок `fsck` при загрузке: `1` для корня, `2` для остальных ext4, `0` — не проверять (XFS, swap, сетевые, tmpfs).

Опции, не зависящие от ФС:

| Опция | Смысл |
|---|---|
| `defaults` | по `mount(8)`: `rw, suid, dev, exec, auto, nouser, async` |
| `noatime` | не обновлять время доступа к файлам (включает и `nodiratime`); экономит запись на томах БД |
| `relatime` | умолчание ядра: atime обновляется, только если он старше mtime/ctime или суток |
| `lazytime` | времена обновляются в памяти и сбрасываются на диск отложенно |
| `ro` / `rw` | только чтение / чтение-запись |
| `noexec`, `nosuid`, `nodev` | запрет исполнения, SUID-битов, файлов устройств (для `/tmp`, съёмных и сетевых томов) |
| `auto` / `noauto` | монтировать ли при загрузке и по `mount -a` |
| `nofail` | отсутствие устройства не считается ошибкой: загрузка продолжается |
| `_netdev` | ФС требует сети — монтировать после её поднятия |
| `user`, `users`, `owner` | разрешить монтирование обычным пользователям |
| `discard` | онлайн-TRIM при каждом освобождении блоков (см. раздел 11 — лучше `fstrim.timer`) |
| `errors=remount-ro` | ext4: при ошибке ФС перемонтировать только для чтения (`continue` — продолжать, `panic` — остановить систему); умолчание хранится в суперблоке, см. `tune2fs -e` |
| `X-mount.mkdir` | создать точку монтирования, если её нет |

Опции для systemd (он превращает каждую строку `fstab` в юнит `*.mount`) [офиц., systemd.mount(5)]:

| Опция | Смысл |
|---|---|
| `x-systemd.automount` | монтировать по первому обращению (создаётся юнит `.automount`); загрузка не ждёт устройство или сервер |
| `x-systemd.idle-timeout=600` | размонтировать автомонтируемую ФС после N секунд простоя |
| `x-systemd.device-timeout=30s` | сколько ждать появления устройства (по умолчанию 90 с) |
| `x-systemd.mount-timeout=30s` | сколько ждать завершения самой команды mount |
| `x-systemd.requires=юнит`, `x-systemd.after=`, `x-systemd.before=` | зависимости и порядок относительно других юнитов |
| `x-systemd.requires-mounts-for=/путь` | требовать, чтобы сначала был смонтирован другой путь |
| `x-systemd.makefs` | создать ФС, если на устройстве нет сигнатуры (осторожно!) |
| `x-systemd.growfs` | при монтировании растянуть ФС на всё устройство |
| `x-systemd.rw-only` | не откатываться на монтирование только для чтения при неудаче rw |

Имя юнита для точки монтирования: `systemd-escape -p --suffix=mount /mnt/winbackup` → `mnt-winbackup.mount`. Состояние: `systemctl status mnt-winbackup.mount`, `systemctl list-units --type=mount`.

Примеры строк:

```text
# Том данных PostgreSQL (LVM-имя стабильно, можно без UUID)
/dev/mapper/vg_pg-lv_pgdata  /var/lib/postgresql  ext4  defaults,noatime,nofail,x-systemd.device-timeout=30s  0 2
# WAL на XFS
UUID=7f6e5d4c-…              /pgwal               xfs   defaults,noatime,nofail,x-systemd.device-timeout=30s  0 0
# Локальный том бэкапов
LABEL=backup                 /backup              ext4  defaults,noatime,nofail                               0 2
# Файл подкачки (как делает установщик Ubuntu)
/swap.img                    none                 swap  sw                                                    0 0
# tmpfs
tmpfs                        /mnt/ramtmp          tmpfs rw,nosuid,nodev,size=2G,mode=1777                     0 0
```

### 5.4. Безопасный порядок правки fstab

```bash
sudo cp -a /etc/fstab /etc/fstab.$(date +%F)       # копия
sudoedit /etc/fstab                                # правка
sudo systemctl daemon-reload                       # systemd перечитывает fstab (иначе mount напомнит: «use 'systemctl daemon-reload'»)
sudo findmnt --verify --verbose                    # 0 parse errors, 0 errors — можно продолжать
sudo mount -a                                      # монтируем; ошибки видны сразу, а не при перезагрузке
findmnt /pgdata && df -hT /pgdata                  # убедиться, что смонтировано то, что нужно
```

`mount -a` не активирует `x-systemd.automount` (монтирует ФС напрямую, опции `x-systemd.*` для него — комментарии). Чтобы включить автомонтирование без перезагрузки: `sudo systemctl daemon-reload && sudo systemctl start mnt-winbackup.automount` (или `sudo systemctl restart remote-fs.target`).

**Что будет при ошибке.** Запись без `nofail` попадает в зависимости `local-fs.target` (или `remote-fs.target`). Если устройство не появилось за `device-timeout` (90 с), система уходит в **emergency mode** — без сети и SSH; чинить придётся с консоли ВМ:

```bash
# на консоли: «You are in emergency mode…», затем приглашение sulogin: «Enter root password for system maintenance
# (or press Control-D to continue):» либо, если пароль root пуст или передан --force, «Press Enter for system maintenance…»
mount -o remount,rw /        # корень может быть смонтирован только для чтения
nano /etc/fstab              # исправить или закомментировать строку
systemctl daemon-reload
mount -a
systemctl default            # продолжить обычную загрузку (или reboot)
```

**Заблокированный root — попадёте ли вы в эту оболочку.** Аварийную оболочку открывает `sulogin`. В Ubuntu учётная запись root по умолчанию заблокирована (в `/etc/shadow` вместо хеша `!` или `*`). По man: «If the root account is locked and --force is specified, no password is required»; ключ `-e/--force` — «when root account is locked by '!' or '*' … sulogin will start a root shell without asking for a password» [офиц., sulogin(8), util-linux 2.39.3]. То есть **без `--force` заблокированный root оболочку не получает**: `sulogin` выводит «Cannot open access to console, the root account is locked. See sulogin(8) man page for more details. Press Enter to continue.» и после Enter завершается с ошибкой, а systemd запускает его снова — замкнутый круг [офиц., исходный код util-linux `login-utils/sulogin.c`: `deny = !opt_e && locked_account_password(...)`, заблокированным считается пароль, начинающийся с `*` или `!`]. systemd добавляет `--force` только при `SYSTEMD_SULOGIN_FORCE=1` — в окружении служб `emergency.service`/`rescue.service` либо, в systemd 255 и новее (24.04, 26.04), в командной строке ядра [офиц., исходный код systemd v255 `src/sulogin-shell/sulogin-shell.c`]. ⚠ не подтверждено: задаёт ли Ubuntu эту переменную сама (прежняя формулировка статьи «пароль, как правило, не спрашивается» первоисточником не подтверждается). Проверьте на своём сервере **заранее**:

```bash
sudo passwd -S root                                          # «root L …» = заблокирован, «root P …» = пароль задан
systemctl show emergency.service rescue.service -p Environment   # есть ли SYSTEMD_SULOGIN_FORCE=1
systemctl cat emergency.service | grep -iE 'sulogin|Environment'
```

Подготовка (выберите одно; делается на исправной системе):

```bash
# Вариант 1: аварийная оболочка без пароля. Консоль ВМ тогда равна root-доступу — она должна быть защищена правами на хосте.
sudo mkdir -p /etc/systemd/system/emergency.service.d /etc/systemd/system/rescue.service.d
printf '[Service]\nEnvironment=SYSTEMD_SULOGIN_FORCE=1\n' | sudo tee \
  /etc/systemd/system/emergency.service.d/sulogin-force.conf \
  /etc/systemd/system/rescue.service.d/sulogin-force.conf
sudo systemctl daemon-reload

# Вариант 2: задать пароль root — sulogin будет спрашивать его (SSH-вход root по паролю при этом оставьте запрещённым)
sudo passwd root
```

Если не подготовились и оболочка недоступна: в меню GRUB нажать `e` и дописать в конец строки `linux` либо `SYSTEMD_SULOGIN_FORCE=1` (24.04/26.04), либо `init=/bin/bash` (попадёте в оболочку без systemd: `mount -o remount,rw /`, правка `/etc/fstab`, `sync`, затем `reboot -f`); либо загрузить ВМ с установочного ISO, выполнить `vgchange -ay`, смонтировать корень и исправить `fstab` оттуда. Как попасть в меню GRUB: в Ubuntu оно по умолчанию скрыто (`GRUB_TIMEOUT_STYLE=hidden`, `GRUB_TIMEOUT=0` в `/etc/default/grub`); разово меню вызывается клавишей Esc (UEFI) или Shift (BIOS) в самом начале загрузки, а чтобы оно показывалось всегда, заранее поставьте `GRUB_TIMEOUT_STYLE=menu` и `GRUB_TIMEOUT=5`, затем `sudo update-grub` [практика]. Для ВМ Hyper-V поколения 2 у Microsoft есть старый совет: таймер GRUB там мог отсчитываться слишком быстро, и «до исправления GRUB» предлагалось ставить «timeout=100000» вместо «timeout=5» [офиц., Best Practices for running Linux on Hyper-V]. **Не применяйте это значение вслепую**: если в вашей версии GRUB таймер уже идёт нормально, сервер после каждой перезагрузки простоит в меню больше суток. Сначала проверьте с `GRUB_TIMEOUT=5`, виден ли обратный отсчёт.

**`nofail` для тома данных PostgreSQL — да или нет?** [практика] Без `nofail` потеря диска данных = недоступный по SSH сервер. С `nofail` сервер загрузится, но PostgreSQL может стартовать на пустой точке монтирования. Правильная комбинация:

1. `nofail,x-systemd.device-timeout=30s` в `fstab`;
2. каталог данных — **подкаталог** внутри тома (при отсутствии тома его просто нет, и PostgreSQL корректно не стартует — именно это рекомендует документация PostgreSQL: «it also ensures clean failures if the secondary volume is taken offline»);
3. явная зависимость службы от монтирования:

```bash
sudo systemctl edit postgresql@18-main.service
# в открывшийся drop-in:
[Unit]
RequiresMountsFor=/var/lib/postgresql /pgwal
```

Аналогично для сервера 1С: `sudo systemctl edit srv1cv8-<версия>@default.service` с `RequiresMountsFor=/home/usr1cv8` (точное имя юнита — `systemctl list-units 'srv1cv8*'`).

## 6. Свободное место: df, du, ncdu и поиск «куда всё делось»

### 6.1. df

```bash
df -h                          # все ФС, размеры в «человеческих» единицах (степени 1024)
df -hT                         # плюс тип ФС
df -h /pgdata                  # ФС, на которой лежит путь
df -i                          # inode: IUsed / IFree / IUse%
df -hT -x tmpfs -x devtmpfs -x squashfs -x overlay   # без псевдо-ФС и snap-образов
df -h -t ext4 -t xfs           # только указанные типы
df --output=source,fstype,size,used,avail,pcent,ipcent,target   # свои столбцы (pcent — занято %, ipcent — inode %)
df -H                          # единицы по 1000 (как у производителей дисков)
```

На ext4 `Avail` меньше, чем `Size − Used`, на величину резерва root (по умолчанию 5 %): для обычного пользователя место «кончается» раньше, чем `Use%` дойдёт до 100.

### 6.2. du

```bash
sudo du -sh /var/lib/postgresql              # итог по каталогу
sudo du -xhd1 / | sort -h                    # первый уровень корня, не выходя за пределы ФС (-x), по возрастанию
sudo du -xh --max-depth=2 /var | sort -h | tail -20
sudo du -sh /var/log/* | sort -h             # каждый элемент каталога
sudo du -ah /var/log | sort -h | tail -20    # включая отдельные файлы
sudo du -sch /backup/*.dump                  # с общим итогом (-c)
sudo du -sh --apparent-size /swap.img        # «кажущийся» размер (для разрежённых файлов отличается от занятого)
sudo du --inodes -xd2 / | sort -n | tail -20 # где больше всего файлов (inode)
```

Ключи: `-s` — только итог; `-h` — человекочитаемо; `-x` — не переходить на другие ФС (обязательно при разборе корня, иначе в сумму попадут `/proc`, смонтированные тома и шары); `-d N` = `--max-depth=N`; `-a` — и файлы тоже; `-c` — общий итог.

### 6.3. ncdu

Интерактивный анализатор (`sudo apt install ncdu`):

```bash
sudo ncdu -x /                 # корень, не выходя на другие ФС
sudo ncdu /var/lib/postgresql
sudo ncdu -x -o /root/ncdu-root.json /    # только просканировать и сохранить результат
ncdu -f /root/ncdu-root.json              # открыть сохранённое
```

Внутри: стрелки/Enter — навигация, `d` — удалить, `g` — проценты/графики, `n`/`s`/`C` — сортировка по имени/размеру/числу элементов, `q` — выход.

### 6.4. Алгоритм «закончилось место»

```bash
df -hT                                            # 1. какая ФС заполнена
df -i                                             # 2. может, кончились inode, а не блоки
sudo du -xhd1 / 2>/dev/null | sort -h | tail      # 3. крупнейшие каталоги на этой ФС, затем углубляться
sudo find / -xdev -type f -size +1G -printf '%s\t%p\n' 2>/dev/null | sort -n | tail -20   # 4. крупнейшие файлы
sudo lsof -nP +L1                                 # 5. удалённые, но всё ещё открытые файлы
sudo journalctl --disk-usage                      # 6. журнал systemd
```

**Удалённые открытые файлы.** Если файл удалён (`rm`), но процесс держит его открытым, место не освобождается: `df` показывает занятое, `du` его не видит. `lsof +L1` выводит файлы с числом ссылок 0 (столбцы PID, FD, SIZE/OFF, NAME c пометкой `(deleted)`). Решения: перезапустить/перечитать конфигурацию процесса (`systemctl restart …`, для логов — `logrotate` с `copytruncate` или сигнал) либо обнулить файл через дескриптор, не останавливая процесс:

```bash
sudo lsof -nP +L1 | sort -k7 -n | tail      # крупнейшие — в конце
sudo sh -c ': > /proc/12345/fd/7'           # обнулить файл, открытый процессом 12345 под дескриптором 7
```

**Исчерпание inode** (только ext4; `df -i` показывает `IUse% 100%`, ошибка та же — «No space left on device»). Причина — миллионы мелких файлов: сессии PHP, почтовая очередь, кэши, неубранные временные файлы 1С, технологический журнал 1С с мелкой нарезкой. Найти каталог: `sudo du --inodes -xd3 / | sort -n | tail`; удалять пачками: `sudo find /путь -xdev -type f -mtime +7 -delete`. Увеличить число inode у существующей ext4 нельзя (только пересоздать ФС с меньшим `-i`).

**Файлы, «спрятанные» под точкой монтирования.** Если том не был смонтирован, а служба писала в каталог точки монтирования, данные лежат на корневой ФС и после монтирования не видны. Посмотреть «под» точками:

```bash
sudo mkdir -p /mnt/rootonly && sudo mount --bind / /mnt/rootonly
sudo du -sh /mnt/rootonly/pgdata /mnt/rootonly/backup /mnt/rootonly/mnt/*
sudo umount /mnt/rootonly
```

**Прочие причины расхождения `df` и `du`:** резерв root на ext4; место под LVM-снапшоты (это уровень VG, в `df` не видно); упреждающее выделение XFS для растущих файлов (освобождается после закрытия файла).

### 6.5. Типичные «пожиратели» места на сервере 1С + PostgreSQL

| Где | Что и как проверить |
|---|---|
| `…/pg_wal` | WAL не удаляется: сломан `archive_command` (`SELECT * FROM pg_stat_archiver;`), заброшенный слот репликации (`SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) FROM pg_replication_slots;`), слишком большой `max_wal_size`/`wal_keep_size`. **Файлы из `pg_wal` руками не удалять.** |
| `…/base/pgsql_tmp`, каталог `temp_tablespaces` | временные файлы сортировок и хэшей тяжёлых запросов 1С; ограничение — `temp_file_limit`; диагностика — `log_temp_files` |
| `…/base/<oid>` | раздутые таблицы/индексы (bloat) после массовых операций; копии баз |
| `/var/log/postgresql` | журналы при подробном логировании (`log_min_duration_statement`, `log_statement`) |
| `/home/usr1cv8/.1cv8/1C/1cv8/reg_1541/<uuid базы>/1Cv8Log` | журнал регистрации 1С — сокращается штатно из конфигуратора или настройкой периодичности разделения |
| каталог технологического журнала (задан в `logcfg.xml`) | технологический журнал с избыточными событиями; глубина хранения задаётся атрибутом `history` (в часах) |
| `/tmp`, каталог `TMPDIR` службы 1С | временные файлы `rphost`; на 26.04 `/tmp` в ОЗУ |
| `/var/crash`, каталог дампов | core-дампы процессов 1С/PostgreSQL |
| `/var/log/journal` | `sudo journalctl --vacuum-size=500M` или `--vacuum-time=14d`; постоянный лимит — `SystemMaxUse=` в `/etc/systemd/journald.conf` |
| `/var/cache/apt`, старые ядра в `/boot` | `sudo apt clean`; `sudo apt autoremove --purge` |
| `/var/lib/snapd` | старые ревизии snap: `snap list --all`; `sudo snap set system refresh.retain=2` |
| каталог бэкапов | не отработала ротация; бэкап писался на локальный диск вместо несмонтированной шары |

## 7. LVM

### 7.1. Понятия

- **PV (physical volume)** — диск или раздел, инициализированный под LVM (`pvcreate`).
- **VG (volume group)** — пул из одного или нескольких PV; делится на физические экстенты (**PE**, по умолчанию 4 МиБ).
- **LV (logical volume)** — «раздел» из экстентов VG; на нём создают ФС или swap. Доступен как `/dev/VG/LV` и `/dev/mapper/VG-LV` (это ссылки на `/dev/dm-N`).

Пакет — `lvm2` (в Ubuntu Server установлен). Метаданные хранятся на самих PV; текстовые копии — в `/etc/lvm/backup/` (последняя) и `/etc/lvm/archive/` (история перед каждым изменением).

### 7.2. Просмотр

```bash
sudo pvs                         # PV: VG, формат, размер, PFree
sudo pvs -o +pv_used,dev_size    # с дополнительными столбцами
sudo pvdisplay                   # подробно
sudo pvdisplay -m /dev/sda3      # какие экстенты какому LV принадлежат
sudo vgs                         # VG: число PV/LV, VSize, VFree
sudo vgdisplay ubuntu-vg         # подробно: размер PE, Total/Alloc/Free PE
sudo lvs                         # LV: атрибуты, размер, для снапшотов — Origin и Data%
sudo lvs -a -o +devices          # включая служебные тома; на каких PV лежит каждый LV
sudo lvs -o lv_name,vg_name,lv_size,lv_attr,origin,data_percent,lv_path
sudo lvdisplay /dev/ubuntu-vg/ubuntu-lv
sudo pvs -a                      # все блочные устройства, включая ещё не инициализированные под LVM
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS        # то же деревом
```

Строка атрибутов `lvs` (`-wi-ao----`): 1-й символ — тип (`-` обычный, `s` снапшот, `o` origin со снапшотом, `t` thin pool, `V` thin-том); 2-й — права (`w` запись, `r` чтение); 5-й — состояние (`a` активен); 6-й — `o` открыт (смонтирован/используется).

### 7.3. Физические тома (PV)

```bash
sudo pvcreate /dev/sdb               # весь диск под LVM (без таблицы разделов)
sudo pvcreate /dev/sdb1              # раздел (тип Linux LVM: fdisk 8e / lvm, sgdisk 8e00)
sudo pvresize /dev/sdb               # после увеличения диска/раздела: растянуть PV на новый размер
sudo pvresize --setphysicalvolumesize 40G /dev/sdb1   # уменьшить PV перед уменьшением раздела (откажется, если заняты экстенты за новой границей)
sudo pvmove /dev/sdb                 # перенести все экстенты с sdb на другие PV того же VG (онлайн)
sudo pvmove /dev/sdb /dev/sdc        # перенести именно на sdc
sudo pvmove -n lv_pgdata /dev/sdb /dev/sdc   # только экстенты одного LV
sudo pvmove -b /dev/sdb /dev/sdc     # в фоне; прогресс: lvs -a -o +devices,copy_percent
sudo pvmove                          # без аргументов — продолжить прерванный перенос (после сбоя/перезагрузки)
sudo pvmove --abort                  # отменить
sudo pvremove /dev/sdb               # снять метку LVM (PV уже не должен входить в VG)
```

Если `pvcreate` находит старую сигнатуру (ФС, RAID), он спросит подтверждение на её стирание; для скриптов — `pvcreate -y` либо заранее `wipefs -a`.

### 7.4. Группы томов (VG)

```bash
sudo vgcreate vg_pg /dev/sdb                 # создать VG из одного PV
sudo vgcreate vg_data /dev/sdb /dev/sdc      # из нескольких
sudo vgcreate -s 16M vg_big /dev/sdd         # с размером экстента 16 МиБ
sudo vgextend vg_pg /dev/sdc                 # добавить PV в VG
sudo vgreduce vg_pg /dev/sdb                 # убрать пустой PV из VG (сначала pvmove)
sudo vgreduce --removemissing vg_pg          # убрать из VG пропавшие PV (если на них нет LV; с --force — вместе с частичными LV)
sudo vgrename vg_old vg_new                  # переименовать (для системного VG потребует правки fstab, GRUB и initramfs — не делайте без нужды)
sudo vgchange -ay vg_pg                      # активировать все LV группы (после подключения диска от другой машины, в rescue-режиме)
sudo vgchange -an vg_pg                      # деактивировать
sudo vgscan; sudo pvscan                     # пересканировать устройства
sudo vgcfgbackup vg_pg                       # сохранить метаданные в /etc/lvm/backup/vg_pg
sudo vgcfgrestore --list vg_pg               # какие копии метаданных есть
sudo vgexport vg_pg; sudo vgimport vg_pg     # перенос VG между машинами
sudo vgremove vg_pg                          # удалить VG (вместе с LV — спросит подтверждение)
```

### 7.5. Логические тома (LV)

```bash
sudo lvcreate -n lv_pgdata -L 200G vg_pg         # том 200 ГиБ
sudo lvcreate -n lv_pgdata -l 90%VG vg_pg        # 90 % всей группы
sudo lvcreate -n lv_backup -l 100%FREE vg_bak    # всё свободное место
sudo lvcreate -n lv_swap -L 8G ubuntu-vg         # том под swap

sudo lvextend -L +50G /dev/vg_pg/lv_pgdata       # прибавить 50 ГиБ (только LV, ФС не тронута!)
sudo lvextend -r -L +50G /dev/vg_pg/lv_pgdata    # прибавить 50 ГиБ И увеличить ФС
sudo lvextend -r -L 300G /dev/vg_pg/lv_pgdata    # довести до 300 ГиБ (без «+» — абсолютный размер)
sudo lvextend -r -l +100%FREE /dev/vg_pg/lv_pgdata   # отдать всё свободное место VG
sudo lvextend -r -l +50%FREE /dev/vg_pg/lv_pgdata    # половину свободного
sudo lvextend -r -L +20G /dev/vg_pg/lv_pgdata /dev/sdc   # брать экстенты только с указанного PV

sudo lvreduce -r -L 100G /dev/vg_x/lv_x          # уменьшить до 100 ГиБ вместе с ФС (только ext4; ФС будет размонтирована и проверена)
sudo lvrename vg_pg lv_old lv_new                # переименовать (не забыть fstab)
sudo lvchange -an /dev/vg_pg/lv_x                # деактивировать том
sudo lvchange -ay /dev/vg_pg/lv_x                # активировать
sudo lvremove /dev/vg_pg/lv_x                    # удалить том (данные теряются)
```

Суффиксы для `-l`: `%VG` — от размера всей группы, `%FREE` — от свободного в группе, `%PVS` — от свободного на перечисленных PV, `%ORIGIN` — от размера исходного тома (для снапшотов). Знак `+`/`-` перед числом — относительное изменение; без знака — абсолютный размер.

`-r` (`--resizefs`): в lvm2 2.03.16 (24.04) — «Resize underlying filesystem together with the LV using fsadm(8)»; в 2.03.31 (26.04) — вызов утилиты самой ФС, эквивалент `--fs resize`. Если забыли `-r`, увеличьте ФС отдельно: `sudo resize2fs /dev/vg_pg/lv_pgdata` (ext4) или `sudo xfs_growfs /pgdata` (XFS).

**Уменьшение опасно.** Порядок без `-r`: размонтировать → `e2fsck -f` → `resize2fs /dev/… 100G` → `lvreduce -L 100G`. Ошибка в порядке или размере уничтожает ФС. Поведение `lvreduce` без `-r` зависит от версии:

- **22.04 и 24.04 (lvm2 2.03.11 / 2.03.16)**: опции `--fs` нет; `lvreduce` только предупреждает («THIS MAY DESTROY YOUR DATA») и после `y` режет том вместе с ФС.
- **26.04 (lvm2 2.03.31)**: если ни `--fs`, ни `-r` не заданы, действует `--fs checksize` — «If the reduced space is used by the fs, then do not resize the fs or LV, and return an error» [офиц.: текст опции — lvreduce(8) resolute; то, что это умолчание, — исходный код lvm2 `tools/lvresize.c`: «Use checksize when no fs option is specified… the LV is reduced only if the fs does not need to be reduced (or no fs.)»]. Защита работает, только когда lvm2 собран с поддержкой сведений о ФС из libblkid, и не действует при `--fs ignore` (man: «using ignore when reducing the LV size may destroy the file system») и при устаревшем `--fs resize_fsadm` (man: «this option does not prevent lvreduce from destroying file systems that are unmounted (or mounted if prompts are skipped)»).

Вывод одинаков для всех версий: уменьшать только командой `lvreduce -r`, после бэкапа, и никогда не добавлять `-y`/`-f`/`--fs ignore` «чтобы не спрашивал». XFS уменьшить нельзя вовсе: только новый том меньшего размера и перенос данных.

Полезно перед уменьшением ext4: `sudo resize2fs -P /dev/vg_x/lv_x` — оценка минимально возможного размера ФС (в блоках ФС).

### 7.6. Стандартная разметка установщика Ubuntu и её расширение

Что создаёт Subiquity при выборе «Use an entire disk» + «Set up this disk as an LVM group» (это умолчание; в autoinstall — `layout: {name: lvm}`):

| Раздел | Назначение |
|---|---|
| `sda1` | UEFI: ESP (FAT32, `/boot/efi`, обычно около 1 ГБ); BIOS: раздел «BIOS boot» 1 МиБ |
| `sda2` | `/boot`, ext4 (обычно около 2 ГБ) |
| `sda3` | PV LVM → VG **`ubuntu-vg`** → LV **`ubuntu-lv`**, ext4, `/` |
| файл `/swap.img` | подкачка (не раздел и не LV) |

⚠ не подтверждено: точные размеры ESP и `/boot` зависят от версии установщика и размера диска — смотрите `lsblk`. Исходный код Subiquity (`subiquity/common/filesystem/sizes.py`) при проверке открыть не удалось (GitHub и Launchpad отдали 404/ошибку); по памяти рецензента там заданы масштабируемые границы: ESP от 538 МиБ до 1075 МиБ, `/boot` от 1792 МиБ до 2048 МиБ (на маленьких дисках — ближе к минимуму). В справочнике autoinstall размеры этих разделов не описаны.

Размер `ubuntu-lv` по умолчанию (политика `sizing-policy: scaled`) [офиц., Autoinstall configuration reference]:

| Свободно в VG | Размер корневого LV |
|---|---|
| меньше 10 ГиБ | всё место |
| 10–20 ГиБ | 10 ГиБ |
| 20–200 ГиБ | половина |
| больше 200 ГиБ | 100 ГиБ |

Смысл — оставить место под снапшоты и другие тома. При автоматической установке `sizing-policy: all` отдаёт корню весь VG. В интерактивном установщике размер `ubuntu-lv` можно изменить на экране сводки по разметке до начала установки.

В `fstab`, созданном установщиком, корень записан как `/dev/disk/by-id/dm-uuid-LVM-<длинный идентификатор>`, а `/boot` и ESP — как `/dev/disk/by-uuid/…`; это стабильные ссылки, менять их не нужно.

Расширить корень на всё свободное место:

```bash
sudo vgs                                   # VFree — сколько свободно
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
df -h /
```

Лучше [практика]: не раздувать корень, а нарезать из свободного места отдельные тома — под данные PostgreSQL, каталог сервера 1С, логи:

```bash
sudo lvextend -r -L 40G /dev/ubuntu-vg/ubuntu-lv              # корню — 40 ГиБ итого
sudo lvcreate -n lv_1c -L 30G ubuntu-vg                       # под /home/usr1cv8
sudo mkfs.ext4 -L srv1c -m 1 /dev/ubuntu-vg/lv_1c
```

### 7.7. Снапшоты LVM

Классический (copy-on-write) снапшот — «замороженный» образ тома. Ему выделяется собственное место в VG, куда перед каждой первой перезаписью блока оригинала копируется старое содержимое.

```bash
sudo lvcreate -s -n snap_pgdata -L 20G /dev/vg_pg/lv_pgdata       # снапшот с 20 ГиБ под изменения
sudo lvcreate -s -n snap_pgdata -l 20%ORIGIN /dev/vg_pg/lv_pgdata # под изменения — 20 % от размера оригинала
sudo lvs                                                          # столбец Data% — заполнение снапшота
sudo mkdir -p /mnt/snap
sudo mount -o ro /dev/vg_pg/snap_pgdata /mnt/snap                 # ext4
sudo mount -o ro,nouuid /dev/vg_pg/snap_pgdata /mnt/snap          # XFS (тот же UUID, что у оригинала)
sudo umount /mnt/snap && sudo lvremove -y /dev/vg_pg/snap_pgdata  # удалить снапшот
sudo lvconvert --merge vg_pg/snap_pgdata                          # ОТКАТИТЬ оригинал к состоянию снапшота
sudo lvextend -L +10G /dev/vg_pg/snap_pgdata                      # увеличить место под изменения
```

Правила:

- **Переполнился снапшот (Data% = 100) — он становится недействительным** («If the snapshot volume uses all of the space allocated to it, then the snapshot is broken» [офиц., Ubuntu Server docs]); оригинал при этом цел. Автоувеличение: в `/etc/lvm/lvm.conf`, секция `activation`, `snapshot_autoextend_threshold = 70` и `snapshot_autoextend_percent = 20` (умолчание порога 100 = выключено); требуется работающий `lvm2-monitor.service`.
- **Пока существует классический снапшот, запись на оригинал заметно медленнее** (каждая первая запись блока = чтение + две записи). На томе БД держите снапшот минуты-часы, а не дни.
- `lvconvert --merge` для используемого тома откладывается до следующей активации; для корневого тома — до перезагрузки [офиц.].
- Чтобы снапшоты были возможны, в VG должно оставаться свободное место — ещё одна причина не отдавать весь VG одному LV.
- Thin-тома (`lvcreate -T`, thin pool) дают дешёвые снапшоты без заметного замедления, но переполнение thin pool приводит к ошибкам ввода-вывода на всех его томах. Под БД — только с мониторингом заполнения (`lvs`: `Data%`, `Meta%`).

**Пригодность снапшотов для бэкапа PostgreSQL** [офиц., PostgreSQL docs, «File System Level Backup»]:

- Снапшот тома с работающей СУБД даёт состояние «как после внезапного отключения питания»: при запуске PostgreSQL выполнит восстановление по WAL. Это штатно — но **только если в снапшот попал весь кластер: каталог данных вместе с `pg_wal` и всеми табличными пространствами**. Перед снапшотом полезно выполнить `CHECKPOINT`.
- Если данные, WAL и табличные пространства на разных томах, одновременных снапшотов получить нельзя («the snapshots *must* be simultaneous»). Тогда либо останавливать PostgreSQL на время снятия всех снапшотов, либо делать базовую копию с непрерывным архивированием (`pg_basebackup`, `pg_probackup`).
- Снапшот лежит на тех же дисках, что и оригинал: это не резервная копия, пока данные не скопированы на другой носитель (`rsync`/`tar` из `/mnt/snap`).

Где снапшоты действительно удобны [практика]: точка отката перед обновлением платформы 1С, PostgreSQL или конфигурации — остановить службы, снять снапшоты нужных томов, обновить, проверить, удалить снапшоты (или `lvconvert --merge` для отката). Для регулярных бэкапов баз 1С используйте `pg_dump`/`pg_basebackup`/`pg_probackup`.

### 7.8. Типовые сценарии

Новый диск `sdb` под данные PostgreSQL:

```bash
lsblk                                                   # убедиться, что sdb — тот самый пустой диск
sudo pvcreate /dev/sdb
sudo vgcreate vg_pg /dev/sdb
sudo lvcreate -n lv_pgdata -l 90%VG vg_pg               # 10 % оставляем в резерве
sudo mkfs.ext4 -L pgdata -m 1 /dev/vg_pg/lv_pgdata      # или: sudo mkfs.xfs -L pgdata /dev/vg_pg/lv_pgdata
sudo mkdir -p /pgdata
echo '/dev/mapper/vg_pg-lv_pgdata /pgdata ext4 defaults,noatime,nofail,x-systemd.device-timeout=30s 0 2' | sudo tee -a /etc/fstab
sudo systemctl daemon-reload && sudo findmnt --verify && sudo mount -a
df -hT /pgdata
```

Переезд VG на новый (больший или более быстрый) диск без остановки служб:

```bash
sudo pvcreate /dev/sdc
sudo vgextend vg_pg /dev/sdc
sudo pvmove -b /dev/sdb /dev/sdc         # онлайн-перенос; при сбое продолжить командой pvmove без аргументов
sudo lvs -a -o +devices,copy_percent     # наблюдать за прогрессом
sudo vgreduce vg_pg /dev/sdb
sudo pvremove /dev/sdb                   # после этого диск можно отключать от ВМ
```

Диск с LVM от другой машины (или после клонирования ВМ): `sudo vgscan && sudo vgchange -ay`, затем монтировать `/dev/VG/LV`. При совпадении имён VG (два `ubuntu-vg`) переименуйте чужой по UUID: `sudo vgs -o vg_name,vg_uuid`, затем `sudo vgrename <UUID> ubuntu-vg-old`.

### 7.9. fsfreeze и резервное копирование ВМ целиком с хоста

`fsfreeze` приостанавливает запись в ФС и сбрасывает на диск все «грязные» данные и журнал, чтобы образ на диске был согласован [офиц., fsfreeze(8)]:

```bash
sudo fsfreeze -f /backup      # заморозить: новые write() блокируются до разморозки
sudo fsfreeze -u /backup      # разморозить
```

- Для снапшотов LVM вручную вызывать `fsfreeze` не нужно: «The device-mapper (and LVM) automatically freezes a filesystem on the device when a snapshot creation is requested» [офиц.].
- **Никогда не замораживайте корневую ФС и том с данными PostgreSQL «руками» из SSH-сеанса**: любой процесс, пишущий на замороженную ФС (включая вашу оболочку и `sudo`), зависнет до разморозки, и разморозить будет некому. Заморозка — дело инструмента резервного копирования, который сам гарантированно снимет её через секунды.
- **Резервная копия ВМ средствами Hyper-V** («Live virtual machine backup») для Ubuntu 16.04–24.04 поддерживается на Windows Server 2016–2025 с оговорками Microsoft [офиц., Supported Ubuntu virtual machines on Hyper-V]: при открытых во время копирования файлах восстановленному диску может потребоваться `fsck`; копирование может молча завершиться неудачей, если к ВМ подключены iSCSI-устройства или диски прямого доступа (pass-through); для актуальных служб интеграции рекомендуется свежее ядро (HWE или `linux-azure`). ⚠ не подтверждено в этой сессии (по памяти): заморозку ФС в госте по команде хоста выполняет демон `hv_vss_daemon` из пакетов `linux-cloud-tools-…` (`linux-cloud-tools-virtual` для ядра `linux-virtual`); проверка — `systemctl status hv-vss-daemon.service`, `ps -e | grep hv_`.
- Такая копия для PostgreSQL — образ «как после отключения питания» (см. 7.7): при старте восстановленной ВМ СУБД выполнит восстановление по WAL. Это полезная дополнительная страховка для всей ВМ (ОС, настройки, кластер 1С), но **не замена** `pg_dump`/`pg_basebackup`/`pg_probackup`: копию ВМ нельзя проверить без разворачивания, из неё не достать одну базу на момент времени, и она не обнаружит логическую порчу данных.

## 8. Расширение диска ВМ на лету

### 8.1. Шаг 0 — увеличить диск в гипервизоре

- **Hyper-V** [офиц., Microsoft «Online Virtual Hard Disk Resizing Overview»; возможность появилась в Windows Server 2012 R2]: увеличивать и уменьшать диск у работающей ВМ можно только для формата **VHDX** (фиксированные, динамические и разностные диски; `.vhd` не поддерживается) и только если диск подключён к **SCSI-контроллеру** («VHDX files that are attached to an IDE controller are not supported»). У ВМ поколения 2 все диски на SCSI; у ВМ поколения 1 загрузочный диск стоит на IDE — его размер меняется только при выключенной ВМ. В таблице поддержки Ubuntu функция «VHDX resize» отмечена для 16.04–24.04 на Windows Server 2016–2025 [офиц., Supported Ubuntu virtual machines on Hyper-V; 26.04 в таблице на момент проверки ещё нет]. PowerShell на хосте: `Resize-VHD -Path D:\VM\disk.vhdx -SizeBytes 200GB`. ⚠ не подтверждено первоисточником: при наличии у ВМ контрольных точек (checkpoints) кнопка «Правка» диска в диспетчере Hyper-V недоступна и размер менять нельзя — практика, проверьте на своём хосте и удаляйте контрольные точки до расширения.
- **VMware Workstation, VirtualBox**: как правило, требуется выключить ВМ и не иметь снимков (VirtualBox: `VBoxManage modifymedium disk файл.vdi --resize <МБ>`). ⚠ не подтверждено (практика, документация этих продуктов в сессии не читалась).
- **KVM/Proxmox (virtio)**: онлайн, гость узнаёт о новом размере сам.
- Уменьшать виртуальный диск нельзя: Hyper-V позволяет «сжать» VHDX без учёта разделов внутри, что приводит к потере данных [офиц., Microsoft Learn].

### 8.2. Шаг 1 — заставить ядро увидеть новый размер

```bash
lsblk /dev/sda                                            # размер до
echo 1 | sudo tee /sys/class/block/sda/device/rescan      # SCSI/SATA/Hyper-V/VMware: перечитать размер устройства sda
for f in /sys/class/scsi_device/*/device/rescan; do echo 1 | sudo tee "$f" >/dev/null; done   # все SCSI-диски разом
sudo dmesg | tail -5                                      # «sda: detected capacity change from … to …»
lsblk /dev/sda                                            # размер после
```

- virtio-blk (`vda`): отдельный rescan не нужен.
- NVMe: `sudo nvme ns-rescan /dev/nvme0`.
- Новый (добавленный «на горячую») диск не появился: `for h in /sys/class/scsi_host/host*/scan; do echo "- - -" | sudo tee "$h" >/dev/null; done`.
- Альтернатива: `sudo rescan-scsi-bus.sh -s` (пакет `sg3-utils`; `-s` — искать изменение размеров).

### 8.3. Вариант A — LVM на разделе (умолчание Ubuntu: `sda3` → `ubuntu-vg`)

```bash
sudo growpart /dev/sda 3            # растянуть раздел 3 до конца диска (между именем диска и номером — ПРОБЕЛ)
sudo pvresize /dev/sda3             # растянуть PV на размер раздела
sudo vgs                            # появилось VFree
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv    # LV + ФС (или -L +50G, если отдать не всё)
df -h /
```

`growpart` — из пакета `cloud-guest-utils` (в Ubuntu Server обычно установлен; иначе `sudo apt install cloud-guest-utils`). Он переписывает таблицу разделов так, чтобы раздел занял всё место до конца диска или до начала следующего раздела; заодно переносит резервную GPT в конец диска. `sudo growpart -N /dev/sda 3` — пробный запуск без изменений. Для NVMe: `sudo growpart /dev/nvme0n1 3` (раздел при этом называется `nvme0n1p3`).

Ограничения: расти может только раздел, за которым есть свободное место (обычно последний). `growpart` ничего не делает, если выигрыш меньше порога `--fudge`, и отвечает `NOCHANGE` — чаще всего это значит, что не выполнен rescan (шаг 1). Величина порога расходится в источниках: man-страница growpart в 24.04 (cloud-guest-utils 0.33) называет 20480 секторов по 512 байт, то есть 10 МБ; в текущем исходном коде скрипта умолчание — `FUDGE=${GROWPART_FUDGE:-$((1024*1024))}`, то есть 1 МиБ в байтах [офиц., growpart(1) noble и `bin/growpart` в canonical/cloud-utils]. Действующее значение на своём сервере покажет `growpart --help` (строка `--fudge … (default: …)`).

Если корневая ФС заполнена на 100 %, `growpart` падает на создании временного каталога: он вызывает `mktemp -d "${TMPDIR:-/tmp}/${0##*/}.XXXXXX"`, то есть создаёт `/tmp/growpart.XXXXXX` [офиц., исходный код]. Обход — указать каталог в памяти: `sudo TMPDIR=/dev/shm growpart /dev/sda 3` (на 26.04 `/tmp` и так tmpfs).

### 8.4. Вариант B — LVM на целом диске (PV = `/dev/sdb`, без разделов)

```bash
echo 1 | sudo tee /sys/class/block/sdb/device/rescan
sudo pvresize /dev/sdb
sudo lvextend -r -l +100%FREE /dev/vg_pg/lv_pgdata
```

### 8.5. Вариант C — без LVM, ФС на разделе

```bash
echo 1 | sudo tee /sys/class/block/sdb/device/rescan
sudo growpart /dev/sdb 1
sudo resize2fs /dev/sdb1            # ext4: без указания размера — на весь раздел; можно на смонтированной ФС
sudo xfs_growfs /pgdata             # XFS: аргумент — точка монтирования; только на смонтированной ФС
```

### 8.6. Вариант D — без LVM и без разделов (ФС прямо на `/dev/sdb`)

```bash
echo 1 | sudo tee /sys/class/block/sdb/device/rescan
sudo resize2fs /dev/sdb             # ext4
sudo xfs_growfs /pgdata             # XFS
```

### 8.7. Вариант E — добавить второй диск в существующий VG

```bash
sudo pvcreate /dev/sdc
sudo vgextend ubuntu-vg /dev/sdc
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
```

Быстро, но теперь LV «размазан» по двум дискам: потеря любого из них губит том. В ВМ, где оба виртуальных диска лежат на одном хранилище хоста, это приемлемо, но усложняет переносы и восстановление; расширение существующего диска (варианты A–D) предпочтительнее.

### 8.8. Без growpart

```bash
sudo parted /dev/sda resizepart 3 100%      # спросит «Fix» (перенос резервной GPT) и «Yes» (раздел используется)
sudo partx -u /dev/sda                      # если ядро не увидело новый размер раздела
```

## 9. Swap (подкачка)

### 9.1. Посмотреть

```bash
swapon --show                  # NAME TYPE SIZE USED PRIO (пусто = подкачки нет)
free -h                        # строка Swap: total / used / free
cat /proc/swaps
grep -i -E 'swap|commit' /proc/meminfo     # SwapTotal, SwapFree, CommitLimit, Committed_AS
vmstat 1 5                     # столбцы si/so — страницы в/из подкачки в секунду; постоянно не ноль = памяти не хватает
sysctl vm.swappiness           # склонность ядра к вытеснению в swap (умолчание 60)
```

Ubuntu Server при установке создаёт **файл** `/swap.img` и строку `/swap.img none swap sw 0 0` в `fstab`. Размер выбирает curtin по эвристике (`suggested_swapsize` в `curtin/swap.py`): при ОЗУ до 1 ГБ — 2×ОЗУ, до 2 ГБ — 2 ГБ, до 4 ГБ — равен ОЗУ, до 16 ГБ — 4 ГБ, до 64 ГБ — половина ОЗУ, свыше 64 ГБ — сразу предельное значение; предел — не больше 8 ГБ и не больше 25 % свободного места ФС [офиц.: документация и исходный код curtin]. На практике это 2–8 ГБ. Два следствия из того же кода:

- если после ограничения результат оказался меньше половины ОЗУ **и** меньше 4 ГиБ, функция возвращает 0 — **файл подкачки не создаётся вовсе** (типичный случай: ВМ с 8 ГБ ОЗУ и маленьким корневым томом, где 25 % свободного места меньше 4 ГБ). Поэтому после установки всегда проверяйте `swapon --show`;
- на ext4 файл создаётся через `fallocate`, на XFS, Btrfs, ext2/ext3 — через `dd if=/dev/zero`; на ZFS файл подкачки не создаётся.

### 9.2. Файл подкачки

```bash
sudo fallocate -l 8G /swapfile                                   # ext4 — работает; на XFS — с ядра 4.18
# переносимый вариант (его man swapon называет самым надёжным):
# sudo dd if=/dev/zero of=/swapfile bs=1M count=8192 status=progress
sudo chmod 600 /swapfile                                         # иначе mkswap/swapon предупредят о небезопасных правах
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
swapon --show
```

Нельзя создавать файл подкачки через `truncate` или `cp` (разрежённый файл с «дырами» `swapon` отвергнет). На Btrfs нужен атрибут `nocow`; подкачка поверх NFS может не работать [офиц., swapon(8)].

В Ubuntu 26.04 (util-linux 2.41; опция появилась в 2.40) `mkswap` умеет создать файл сам — «Create a swap file with the appropriate file permissions and populated blocks on disk» [офиц., mkswap(8) resolute]:

```bash
sudo mkswap --file /swapfile --size 8G     # создаёт файл 8 ГиБ с правами 600 и сразу размечает его (только 26.04+)
sudo swapon /swapfile
```

В 22.04 и 24.04 опций `--file`/`--size` нет — используйте `fallocate`/`dd` + `chmod 600` + `mkswap`, как показано выше.

Изменить размер существующего `/swap.img`:

```bash
free -h                              # свободной ОЗУ должно хватить, чтобы вместить занятый swap
sudo swapoff /swap.img
sudo fallocate -l 16G /swap.img      # или rm + dd
sudo chmod 600 /swap.img
sudo mkswap /swap.img
sudo swapon /swap.img
```

### 9.3. Раздел или LV под swap

```bash
sudo lvcreate -n lv_swap -L 8G ubuntu-vg
sudo mkswap -L swap /dev/ubuntu-vg/lv_swap
sudo swapon /dev/ubuntu-vg/lv_swap
echo '/dev/mapper/ubuntu--vg-lv_swap none swap sw 0 0' | sudo tee -a /etc/fstab
```

Увеличение LV-подкачки: `swapoff` → `lvextend -L +4G` → `mkswap` → `swapon` (после `mkswap` меняется UUID — если в `fstab` указан `UUID=`, обновите его).

Прочее: `sudo swapon -a` — включить всё из `fstab`; `sudo swapoff -a` — выключить всё; `sudo swapon -p 10 /swapfile` или опция `pri=10` в `fstab` — приоритет (больше = используется раньше); `sudo swapon --discard /dev/…` — TRIM для подкачки на SSD.

### 9.4. Какой размер нужен серверу БД и 1С

Что есть в первоисточниках:

- **PostgreSQL [офиц.]**: OOM killer срабатывает, когда исчерпаны и ОЗУ, и подкачка; наличие swap снижает риск убийства процессов. Конкретных размеров документация не даёт.
- При `vm.overcommit_memory = 2` (строгий учёт; документация PostgreSQL описывает его как способ не допустить срабатывания OOM killer) лимит выделения памяти считается как `CommitLimit = SwapTotal + (ОЗУ − огромные страницы) × vm.overcommit_ratio / 100`; текущие значения — `grep -i commit /proc/meminfo`. То есть **размер swap прямо входит в предел**: слишком маленький swap при строгом учёте даст отказы в выделении памяти задолго до исчерпания ОЗУ.
- **Postgres Professional для 1С [офиц., приложение K.2, проверено по тексту для версии 17]**: дословно — «Отключить подкачку для разделяемой памяти POSIX/System V» (рядом — «Отключить технологию гиперпоточности» и «Отключить режим энергосбережения»). Требование относится именно к разделяемой памяти, а не к подкачке вообще; способ в документе не указан. ⚠ интерпретация автора, первоисточником не подтверждена: в Linux основной сегмент разделяемой памяти PostgreSQL (`shared_buffers`) делают невыгружаемым огромные страницы (`huge_pages = on` + `vm.nr_hugepages`) — ядро их не вытесняет в подкачку. Отключать swap целиком ради этого пункта не нужно.
- **Red Hat (таблица для RHEL 9) [офиц., как ориентир от вендора Linux]**: ОЗУ < 2 ГБ → 2×ОЗУ; 2–8 ГБ → равен ОЗУ; 8–64 ГБ → не менее 4 ГБ; > 64 ГБ → по нагрузке, не менее 4 ГБ.

Рекомендация [практика]:

| ОЗУ сервера | Swap |
|---|---|
| до 8 ГБ | равен ОЗУ |
| 16–32 ГБ | 4–8 ГБ |
| 64 ГБ и более | 8–16 ГБ |

- Подкачку **не отключать**: без неё первый же всплеск потребления (тяжёлый отчёт 1С, `rphost` с утечкой, `VACUUM FULL`) закончится OOM killer, который, скорее всего, убьёт процесс PostgreSQL или `rphost`.
- Снизить склонность к вытеснению: `vm.swappiness = 1…10` в `/etc/sysctl.d/` (EDB в руководстве по настройке Debian/Ubuntu под PostgreSQL даёт `vm.swappiness = 10`) [практика]. Значение 0 не ставить.
- Swap — страховка, а не ресурс: если `vmstat` постоянно показывает ненулевые `si`/`so`, нужно добавлять ОЗУ или уменьшать `shared_buffers`/`work_mem`/лимиты памяти рабочих процессов 1С.
- Подкачку размещать на быстром диске; файл и LV по скорости равноценны.

## 10. Программный RAID: mdadm (кратко)

В гостевой ВМ программный RAID обычно не нужен — отказоустойчивость дисков обеспечивает хост. На физическом сервере без аппаратного контроллера:

```bash
sudo apt install mdadm
# RAID1 из двух разделов (тип раздела: sgdisk fd00 / fdisk raid); bitmap задаём явно — поведение по умолчанию зависит от версии mdadm
sudo mdadm --create /dev/md0 --level=1 --raid-devices=2 --bitmap=internal /dev/sdb1 /dev/sdc1
# RAID10 из четырёх
sudo mdadm --create /dev/md1 --level=10 --raid-devices=4 /dev/sd[d-g]1

cat /proc/mdstat                         # состояние и прогресс синхронизации ([UU] — оба диска в строю, [U_] — деградация)
sudo mdadm --detail /dev/md0             # подробно: State, Active/Failed/Spare Devices, роли дисков
sudo mdadm --examine /dev/sdb1           # суперблок md на компоненте
sudo mdadm --detail --scan | sudo tee -a /etc/mdadm/mdadm.conf   # закрепить массив в конфигурации
sudo update-initramfs -u                 # чтобы массив собирался при загрузке; команда есть во всех трёх LTS
```

В 22.04/24.04 `update-initramfs` — часть initramfs-tools. В 26.04 по умолчанию dracut, но команда `update-initramfs` сохранена: её man-страница в resolute «Provided by: dracut (110-11ubuntu0.1)» и прямо говорит, что скрипт адаптирован для dracut, с теми же режимами `-u`, `-c`, `-k all` [офиц., update-initramfs(8) resolute]. Родная команда dracut — `sudo dracut --regenerate-all --force` (⚠ для Ubuntu 26.04 не проверялась; предпочитайте `update-initramfs -u`).

Метаданные по умолчанию — версии 1.2 («The default is 1.2 for --create») [офиц., mdadm(8)]. Write-intent bitmap (ускоряет повторную синхронизацию после сбоя): в man mdadm 4.2 (22.04) и 4.3 (24.04) сказано: «When creating an array on devices which are 100G or larger, mdadm automatically adds an internal bitmap» (отключается `--bitmap=none`); в man mdadm 4.5 из 26.04 этой фразы уже нет (значения `--bitmap=`: `internal`, `clustered`, `none`) [офиц., mdadm(8) noble и resolute]. Поэтому при создании массива указывайте явно: `--bitmap=internal`. ⚠ не подтверждено (по памяти рецензента): новые версии mdadm при создании массива без `--bitmap` задают интерактивный вопрос о включении bitmap — в скриптах без явного ключа команда может остановиться на вопросе.

Замена отказавшего диска:

```bash
sudo mdadm /dev/md0 --fail /dev/sdb1 --remove /dev/sdb1   # пометить сбойным и вывести из массива
# заменить диск физически; новый — /dev/sdb
sudo sgdisk -R /dev/sdb /dev/sdc         # скопировать разметку с исправного sdc на новый sdb (ЦЕЛЬ первой!)
sudo sgdisk -G /dev/sdb                  # новые GUID
sudo mdadm /dev/md0 --add /dev/sdb1      # добавить — начнётся восстановление
watch -n 5 cat /proc/mdstat
```

Если системный диск был в RAID1 — на новый диск нужно поставить загрузчик (`grub-install` для BIOS либо копия ESP для UEFI).

Прочее: `sudo mdadm --stop /dev/md0` — остановить; `sudo mdadm --assemble --scan` — собрать все массивы; `sudo mdadm --zero-superblock /dev/sdb1` — стереть метаданные md с бывшего компонента; `echo check | sudo tee /sys/block/md0/md/sync_action` — проверка согласованности (результат — `/sys/block/md0/md/mismatch_cnt`); скорость перестроения — `/proc/sys/dev/raid/speed_limit_min` и `speed_limit_max`; оповещения — `MAILADDR` в `/etc/mdadm/mdadm.conf` и служба `mdmonitor`.

Уровни под БД [практика]: RAID10 — данные; RAID1 — WAL и система; RAID5/6 — только бэкапы и архивы (медленная случайная запись). Postgres Professional для 1С: «RAID 0–1 или SSD» [офиц.].

## 11. SSD и NVMe: TRIM, nvme-cli, smartctl, hdparm

### 11.1. TRIM/discard

```bash
lsblk -D                              # DISC-GRAN и DISC-MAX не нулевые — устройство принимает discard
sudo fstrim -v /pgdata                # однократный TRIM одной ФС; печатает, сколько байт отдано
sudo fstrim -av                       # все смонтированные ФС на устройствах с поддержкой discard
sudo fstrim -A -v                     # только ФС, перечисленные в fstab
sudo fstrim -n -av                    # пробный запуск
systemctl status fstrim.timer         # в Ubuntu включён, запускает fstrim.service раз в неделю
systemctl list-timers fstrim.timer    # когда был и когда будет запуск
journalctl -u fstrim.service -n 20    # что и сколько было отдано
```

- man fstrim: для большинства систем достаточно TRIM раз в неделю; частый `fstrim` или монтирование с `discard` могут сокращать срок службы некачественных SSD [офиц.]. Поэтому умолчание и рекомендация — `fstrim.timer`, а не опция `discard` в `fstab`. Исключить ФС из `fstrim -A`: опция `X-fstrim.notrim` в `fstab` — она появилась в util-linux 2.38, то есть работает в 24.04 и 26.04, а в 22.04 (2.37.2) игнорируется [офиц., ReleaseNotes util-linux 2.38; fstrim(8) noble].
- В ВМ TRIM проходит до хранилища хоста, если виртуальный диск это поддерживает (`lsblk -D` в госте). На динамических VHDX и «тонких» дисках это возвращает хосту освобождённое место [практика].
- LVM пропускает discard от ФС к диску без настройки. Параметр `issue_discards` в `lvm.conf` относится к другому — отправлять ли discard при `lvremove`/`lvreduce`.

### 11.2. nvme-cli

```bash
sudo apt install nvme-cli
sudo nvme list                           # устройства: модель, серийный номер, объём, прошивка
sudo nvme smart-log /dev/nvme0           # здоровье: critical_warning, temperature, available_spare, percentage_used, media_errors, unsafe_shutdowns
sudo nvme id-ctrl /dev/nvme0 -H          # паспорт контроллера в читаемом виде
sudo nvme error-log /dev/nvme0           # журнал ошибок
sudo nvme fw-log /dev/nvme0              # слоты и версии прошивки
sudo nvme device-self-test /dev/nvme0 -s 1   # короткий самотест (2 — расширенный)
sudo nvme self-test-log /dev/nvme0       # результаты самотестов
sudo nvme get-feature /dev/nvme0 -f 0x06 -H  # включён ли энергозависимый кэш записи (Volatile Write Cache)
sudo nvme ns-rescan /dev/nvme0           # пересканировать пространства имён
```

На что смотреть: `critical_warning` не 0 — проблема; `percentage_used` — израсходованный ресурс (100 = паспортный ресурс выработан); `available_spare` ниже `available_spare_threshold` — пора менять; рост `media_errors`. `nvme format` и `nvme sanitize` уничтожают данные.

### 11.3. smartctl (smartmontools)

```bash
sudo apt install smartmontools
sudo smartctl --scan                     # какие устройства и с каким типом (-d) видит smartctl
sudo smartctl -i /dev/sda                # модель, серийный номер, прошивка, включён ли SMART
sudo smartctl -H /dev/sda                # общий вердикт (PASSED / FAILED)
sudo smartctl -a /dev/sda                # вся информация SMART
sudo smartctl -x /dev/sda                # всё, включая расширенные журналы
sudo smartctl -A /dev/sda                # только таблица атрибутов
sudo smartctl -t short /dev/sda          # короткий самотест (обычно до 10 минут), идёт в фоне
sudo smartctl -t long /dev/sda           # расширенный (от десятков минут до часов)
sudo smartctl -l selftest /dev/sda       # результаты самотестов
sudo smartctl -l error /dev/sda          # журнал ошибок
sudo smartctl -X /dev/sda                # прервать самотест
sudo smartctl -a /dev/nvme0              # NVMe
sudo smartctl -a -d megaraid,0 /dev/sda  # диск №0 за контроллером MegaRAID (LSI/Broadcom/Dell PERC)
sudo smartctl -a -d sat /dev/sdb         # диск за USB-SATA мостом
sudo smartctl -j -a /dev/sda             # JSON для мониторинга
```

Тревожные атрибуты HDD/SATA SSD: `Reallocated_Sector_Ct` (5), `Current_Pending_Sector` (197), `Offline_Uncorrectable` (198) — рост = диск умирает; `UDMA_CRC_Error_Count` (199) — кабель или порт; у SSD — `Wear_Leveling_Count`, `Media_Wearout_Indicator`, `Percent_Lifetime_Remain` (названия зависят от производителя). Фоновый контроль — демон `smartd` (служба `smartmontools.service`, конфигурация `/etc/smartd.conf`).

**В виртуальной машине SMART недоступен**: гость видит виртуальный диск («Virtual Disk», «Msft Virtual Disk»). Здоровье носителей проверяют на хосте (в Windows — средствами производителя или `Get-PhysicalDisk | Get-StorageReliabilityCounter`).

### 11.4. hdparm и кэш записи

`hdparm` работает с ATA/SATA-дисками (для SAS/SCSI — `sdparm`, для NVMe — `nvme`).

```bash
sudo hdparm -I /dev/sda                  # паспорт диска; в «Commands/features» звёздочка у «Write cache» = кэш записи включён
sudo hdparm -W /dev/sda                  # состояние кэша записи
sudo hdparm -W0 /dev/sda                 # выключить кэш записи (медленнее, но безопасно без защиты по питанию)
sudo hdparm -tT /dev/sda                 # грубая оценка: -T чтение из кэша ОЗУ, -t последовательное чтение с диска
sudo hdparm -t --direct /dev/sda         # то же с O_DIRECT
sudo sdparm --get=WCE /dev/sda           # SCSI/SAS: бит Write Cache Enable
```

Позиция PostgreSQL [офиц., «Reliability»]: энергозависимый кэш записи диска или контроллера — риск для надёжности; потребительские SATA-диски и многие SSD имеют такой кэш и могут не выполнять сброс честно; избегайте контроллеров с кэшем без батареи; на уровне диска кэш следует выключать, если диск не гарантирует запись при потере питания. Проверка поведения — `pg_test_fsync` (раздел 13.3). Для БД под 1С берите SSD с защитой от потери питания (PLP, «enterprise»).

## 12. Планировщики ввода-вывода и read-ahead

### 12.1. Планировщик

```bash
cat /sys/block/sda/queue/scheduler            # например: [mq-deadline] none   — активный в квадратных скобках
grep . /sys/block/*/queue/scheduler           # по всем устройствам
lsblk -d -o NAME,ROTA,SCHED,RQ-SIZE,RA        # сводно
echo none | sudo tee /sys/block/sda/queue/scheduler   # сменить на лету (до перезагрузки)
ls /sys/block/sda/queue/iosched/              # настройки активного планировщика
```

Планировщики современного ядра (blk-mq) [офиц., kernel.org]:

| Имя | Суть | Где уместен |
|---|---|---|
| `none` | без переупорядочивания, запросы сразу уходят устройству | NVMe, быстрые SSD, виртуальные диски (планирует гипервизор/СХД) |
| `mq-deadline` | раздельные очереди чтения/записи со сроками, сортировка по секторам | HDD, SATA SSD, универсальное умолчание |
| `bfq` | справедливое распределение между процессами, приоритет отзывчивости | настольные системы; под БД не нужен, даёт накладные расходы |
| `kyber` | регулирует глубину очереди под целевые задержки | быстрые SSD, редко |

`bfq` и `kyber` — модули; в списке появляются после `sudo modprobe bfq` / `sudo modprobe kyber-iosched`.

Умолчание выбирает ядро: **для устройств с одной аппаратной очередью — `mq-deadline`, для многоочередных — `none`** (комментарий в `block/elevator.c`: «For single queue devices, default to using mq-deadline. If we have multiple queues or mq-deadline is not available, default to "none"»). Поэтому NVMe и многоочередные виртуальные диски обычно уже на `none`, а SATA — на `mq-deadline`. Параметр ядра `elevator=` в современных ядрах не действует: ядро лишь печатает «Kernel parameter elevator= does not have any effect anymore. Please use sysfs to set IO scheduler for individual devices.» [офиц., `block/elevator.c`]. Постоянная настройка — только правилом udev (ниже).

Рекомендации:

- **Microsoft, Linux на Hyper-V [офиц.]**: «with today's solid state disks it's recommended to use a scheduler that passes the scheduling decisions to the underlying Hyper-V hypervisor» — для blk-mq это `none` (в старых ядрах `noop`); настройку нужно закрепить самим, чтобы она пережила перезагрузку.
- **Red Hat [офиц., документация RHEL 9 «Setting the disk scheduler», таблица «Disk schedulers for different use cases»]**: «Virtual guest — Use mq-deadline. With a host bus adapter (HBA) driver that is multi-queue capable, use none»; для быстрых SSD и систем, упирающихся в процессор, — `none` (альтернатива `kyber`); для традиционных HDD — `mq-deadline` или `bfq`; для NVMe умолчание `none`, и менять его Red Hat не рекомендует. Статья базы знаний Red Hat 5427 (о планировщике в гостевых ВМ) закрыта подпиской и не читалась — цифры из неё («выигрыш около 2 %») не подтверждены ⚠.
- Обе позиции согласуются для многоочередного виртуального диска: и ядро, и Microsoft, и Red Hat приходят к `none`. Сколько аппаратных очередей у диска, видно так: `ls /sys/block/sda/mq/` (каталоги `0`, `1`, … — по одному на очередь) или столбец `MQ` в `lsblk -o NAME,MQ,SCHED` (util-linux 2.39+). ⚠ по памяти рецензента: диск Hyper-V (драйвер `storvsc`) при нескольких vCPU многоочередной, при одном vCPU очередь одна — тогда умолчанием будет `mq-deadline`, и рекомендацию Microsoft нужно применить вручную.
- **Сообщество 1С/PostgreSQL [практика]**: NVMe/SSD — `none` или `mq-deadline`; HDD — `mq-deadline`.
- Разница на SSD обычно единицы процентов. Меняйте только по результатам замеров (`fio`, реальная нагрузка).

Закрепить постоянно — правило udev, файл `/etc/udev/rules.d/60-ioscheduler.rules`:

```text
# невращающиеся диски (SSD, виртуальные на SSD) — none
ACTION=="add|change", KERNEL=="sd[a-z]*|vd[a-z]*", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="none"
# вращающиеся — mq-deadline
ACTION=="add|change", KERNEL=="sd[a-z]*", ATTR{queue/rotational}=="1", ATTR{queue/scheduler}="mq-deadline"
```

```bash
sudo udevadm control --reload
sudo udevadm trigger --type=devices --action=change --subsystem-match=block
grep . /sys/block/*/queue/scheduler
```

В ВМ признак `rotational` часто равен 1 даже для диска на SSD хоста; в таком случае пишите правило по имени устройства (`KERNEL=="sda"`) без проверки `rotational`.

### 12.2. Read-ahead (упреждающее чтение)

```bash
sudo blockdev --getra /dev/sda                 # в секторах по 512 байт; 256 = 128 КиБ (умолчание)
sudo blockdev --setra 4096 /dev/sda            # 4096 секторов = 2 МиБ (до перезагрузки)
cat /sys/block/sda/queue/read_ahead_kb         # то же в КиБ
sudo blockdev --report                         # RO, RA, SSZ, BSZ, StartSec, Size по всем устройствам
sudo blockdev --getra /dev/mapper/vg_pg-lv_pgdata   # у LV своё значение — именно оно действует для ФС на этом томе
sudo lvchange -r 4096 /dev/vg_pg/lv_pgdata     # задать read-ahead для LV (хранится в метаданных LVM; auto — умолчание)
```

Важно: упреждающее чтение применяется к тому устройству, на котором смонтирована ФС. Для ФС на LVM настраивать нужно `dm-`устройство (через `lvchange -r` или `blockdev --setra /dev/mapper/…`), а не нижележащий `sda`.

Постоянно для обычного диска — правило udev:

```text
ACTION=="add|change", KERNEL=="sdb", ATTR{queue/read_ahead_kb}="2048"
```

Что ставить [практика; официальных чисел от 1С, Postgres Pro и PGDG нет ⚠]:

- SSD/NVMe и чистый OLTP — умолчания 128 КиБ достаточно;
- HDD-массивы, СХД и нагрузка с большими последовательными чтениями (отчёты 1С с полным сканированием таблиц, `pg_dump`, `VACUUM`, восстановление) — пробовать 1–4 МиБ (`--setra 2048…8192`), в литературе по PostgreSQL встречаются значения до 16384 секторов;
- оценивать замером: время `pg_dump` большой базы и последовательный тест `fio`.

## 13. Тесты диска

Правила:

- тестируйте **файл на целевой ФС**, а не устройство (`--filename=/dev/sdX` в режиме записи уничтожит данные);
- размер тестового файла — больше ОЗУ либо `--direct=1`, иначе измеряется кэш;
- запускайте вне рабочего времени: тест создаёт пиковую нагрузку на общее хранилище;
- заранее посчитайте место: с `--directory` каждое задание fio создаёт **свой** файл размера `--size`, то есть профиль с `--size=8G --numjobs=4` займёт 32 ГиБ. На томе с работающей базой оставьте запас (`df -h` до запуска), иначе тест сам переполнит том и остановит PostgreSQL;
- после — удалить тестовые файлы.

### 13.1. fio

```bash
sudo apt install fio
sudo mkdir -p /pgdata/fio /pgwal/fio       # оба каталога: профиль 4 пишет в /pgwal/fio
sudo -i                                    # команды fio ниже выполняются от root (каталоги принадлежат root)
```

Профили под PostgreSQL (размер страницы PostgreSQL — 8 КиБ):

```bash
# 1. Смешанная случайная нагрузка 8k, 70 % чтения — «типичный OLTP»
fio --name=pg-randrw --directory=/pgdata/fio --size=8G --bs=8k --rw=randrw --rwmixread=70 \
    --ioengine=libaio --direct=1 --iodepth=32 --numjobs=4 \
    --time_based --runtime=120 --ramp_time=10 --group_reporting

# 2. Случайное чтение 8k (индексные обращения)
fio --name=pg-randread --directory=/pgdata/fio --size=8G --bs=8k --rw=randread \
    --ioengine=libaio --direct=1 --iodepth=32 --numjobs=4 --time_based --runtime=60 --group_reporting

# 3. Случайная запись 8k (checkpoint, фоновая запись)
fio --name=pg-randwrite --directory=/pgdata/fio --size=8G --bs=8k --rw=randwrite \
    --ioengine=libaio --direct=1 --iodepth=32 --numjobs=4 --time_based --runtime=60 --group_reporting

# 4. Имитация WAL: последовательная запись 8k с fdatasync после КАЖДОЙ записи, один поток
fio --name=pg-wal --directory=/pgwal/fio --size=2G --bs=8k --rw=write \
    --ioengine=psync --fdatasync=1 --numjobs=1 --time_based --runtime=60

# 5. Последовательная запись и чтение блоками 1 МиБ (бэкап/восстановление, полное сканирование)
fio --name=seq-write --directory=/pgdata/fio --size=8G --bs=1M --rw=write \
    --ioengine=libaio --direct=1 --iodepth=8 --numjobs=1 --group_reporting
fio --name=seq-read --directory=/pgdata/fio --size=8G --bs=1M --rw=read \
    --ioengine=libaio --direct=1 --iodepth=8 --numjobs=1 --group_reporting

# 6. Буферизованная запись с одним fsync в конце (поведение при checkpoint)
fio --name=buf-write --directory=/pgdata/fio --size=4G --bs=8k --rw=write --end_fsync=1

rm -rf /pgdata/fio /pgwal/fio
```

Параметры: `--rw` — `read`/`write` (последовательно), `randread`/`randwrite`, `rw`/`randrw` (смесь, доля чтения — `--rwmixread`, умолчание 50); `--bs` — размер блока (умолчание 4096); `--direct=1` — O_DIRECT, мимо страничного кэша; `--ioengine` — `psync` (умолчание, синхронные pread/pwrite), `libaio` (асинхронный, по-настоящему асинхронен только с `--direct=1`), `io_uring`; `--iodepth` — глубина очереди для асинхронных движков; `--numjobs` — число параллельных заданий; `--runtime` + `--time_based` — работать заданное время; `--ramp_time` — прогрев, не входящий в статистику; `--fsync=N` / `--fdatasync=N` — вызывать `fsync`/`fdatasync` каждые N записей; `--end_fsync=1` — один `fsync` в конце; `--group_reporting` — сводная статистика по всем заданиям; `--output-format=json` — для автоматической обработки.

Как читать: `IOPS`, `BW` (пропускная способность), `clat`/`lat` и перцентили (важны 99.00th и 99.90th, а не среднее). В профиле 4 — блок `fsync/fdatasync/sync_file_range` с задержками синхронизации: IOPS здесь ≈ предел фиксаций транзакций в секунду одним сеансом при `synchronous_commit = on`.

Ориентиры [практика]: HDD 7200 об/мин — 100–200 случайных IOPS, задержка 5–15 мс; SATA SSD — десятки тысяч IOPS, доли миллисекунды; NVMe — сотни тысяч IOPS, десятки-сотни микросекунд. В ВМ результат ограничен хранилищем и настройками кэширования хоста. Если на HDD «получилось» 10–20 тысяч `fdatasync` в секунду — сброс на диск где-то игнорируется (кэш записи хоста или контроллера): при отключении питания возможна порча базы.

### 13.2. dd — как делать правильно

```bash
# последовательная запись мимо кэша ОС
dd if=/dev/zero of=/pgdata/dd.test bs=1M count=4096 oflag=direct status=progress
# запись через кэш, но время включает финальный fdatasync (данные реально на диске)
dd if=/dev/zero of=/pgdata/dd.test bs=1M count=4096 conv=fdatasync status=progress
# синхронная запись каждого блока 8k — грубая оценка скорости фиксации WAL
dd if=/dev/zero of=/pgwal/dd.test bs=8k count=10000 oflag=dsync
# последовательное чтение мимо кэша
dd if=/pgdata/dd.test of=/dev/null bs=1M iflag=direct status=progress
rm -f /pgdata/dd.test /pgwal/dd.test
```

Ошибки:

- `dd if=/dev/zero of=file bs=1M count=1000` **без** `oflag=direct` или `conv=fdatasync` — измеряется скорость записи в ОЗУ (гигабайты в секунду), диск ни при чём;
- нули из `/dev/zero` на хранилище со сжатием, дедупликацией или тонким выделением дают завышенные цифры — для таких хранилищ используйте `fio` (он по умолчанию пишет несжимаемые данные);
- перед тестом чтения без `iflag=direct` сбросьте кэш: `sync; echo 3 | sudo tee /proc/sys/vm/drop_caches`;
- `dd` — это один поток последовательного ввода-вывода; о случайной нагрузке БД он ничего не говорит.

### 13.3. pg_test_fsync

Утилита из состава PostgreSQL: измеряет, сколько синхронных записей 8 КиБ в секунду выдерживает ФС разными методами `wal_sync_method`.

```bash
# Ubuntu/PGDG и сборки 1С: /usr/lib/postgresql/<версия>/bin/
sudo -u postgres /usr/lib/postgresql/18/bin/pg_test_fsync -f /pgwal/18/pg_test_fsync.out -s 5
# Postgres Pro 1C: /opt/pgpro/1c-<версия>/bin/pg_test_fsync   (каталог `/opt/pgpro/1c-<версия>/bin` подтверждён в `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, разд. 5; ранее: для редакции 1C путь первоисточником не подтверждён, см. ниже)
```

Каталог из `-f` должен быть доступен на запись пользователю `postgres`: точка монтирования свежего тома принадлежит root, поэтому сначала создайте подкаталог (`sudo install -d -o postgres -g postgres -m 700 /pgwal/18`) и указывайте файл в нём — иначе `pg_test_fsync` завершится ошибкой открытия файла.

Пути Postgres Pro: документация по установке Postgres Pro Standard 17 называет каталог программ `/opt/pgpro/std-17`, каталог данных по умолчанию `/var/lib/pgpro/std-17/data`, службу `postgrespro-std-17`, скрипт инициализации `/opt/pgpro/std-17/bin/pg-setup` [офиц., postgrespro.ru «Установка двоичных пакетов в Linux»]. Для сборки «Postgres Pro 1C» по той же схеме ожидаются `/opt/pgpro/1c-17`, `/var/lib/pgpro/1c-17/data` и служба `postgrespro-1c-17` — подтверждено официальным описанием метапакета — см. `../postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md`, разд. 5.1; ранее: не подтверждено (страница с инструкцией для редакции 1C при проверке отдала 404). На сервере пути показывают `systemctl cat 'postgrespro-*'`, `ls /opt/pgpro/`, а у работающего экземпляра — `sudo -u postgres psql -c 'SHOW data_directory;'`.

- `-f` — тестовый файл; **должен лежать на той же ФС, что и `pg_wal`** (по умолчанию — `pg_test_fsync.out` в текущем каталоге);
- `-s` — секунд на каждый тест (умолчание 5; весь прогон меньше 2 минут).

Вывод — операций в секунду и микросекунд на операцию для `open_datasync`, `fdatasync`, `fsync`, `fsync_writethrough` (в Linux недоступен), `open_sync`. В Linux умолчание `wal_sync_method = fdatasync` [офиц.]; менять его по результатам теста обычно нет смысла — документация оговаривает, что различия «might not make any significant difference in real database throughput». Главная польза — оценка самого диска [практика, ориентировочные пороги]:

| Результат `fdatasync` | Что это значит |
|---|---|
| ~100–250 оп/с | честный HDD без кэша — для 1С слишком медленно, нужен SSD или контроллер с BBU |
| 1 000–5 000 оп/с | SSD потребительского класса или СХД/ВМ с накладными расходами |
| 10 000+ оп/с | серверный SSD/NVMe с защитой по питанию, RAID с BBU… либо сброс кэша игнорируется (см. 13.1) |

### 13.4. ioping

«ping для диска» — задержка единичных запросов (`sudo apt install ioping`):

```bash
ioping -c 10 /pgdata                 # 10 случайных некэшируемых чтений по 4 КиБ из временного файла в каталоге
ioping -c 10 -s 8k -D /pgdata        # блоки 8 КиБ, O_DIRECT
ioping -c 20 -W -y /pgwal            # синхронная (O_DSYNC) ЗАПИСЬ во временный файл каталога — задержка «как у WAL»
sudo ioping -R /dev/sda              # тест скорости позиционирования (только чтение, 3 секунды)
sudo ioping -RL /dev/sda             # последовательное чтение (блоки 256 КиБ)
ioping -c 100 -q /pgdata             # только итоговая статистика (min/avg/max/mdev)
```

`-W` на **каталоге** безопасен (пишет во временный файл `ioping.tmp`); на файле или устройстве `-W` уничтожает данные (man требует для этого `-WWW`).

### 13.5. Наблюдение за диском под реальной нагрузкой

```bash
sudo apt install sysstat iotop
iostat -xz 1                   # по устройствам: r/s, w/s, rkB/s, wkB/s, r_await, w_await (мс), aqu-sz, %util
sudo iotop -oPa                # какие процессы читают/пишут (накопительно)
pidstat -d 1                   # ввод-вывод по процессам
vmstat 1                       # wa — доля времени ожидания ввода-вывода; bi/bo — блоки в/из
```

Тревожные признаки: `r_await`/`w_await` стабильно выше 10–20 мс на SSD; `%util` около 100 % при малом `r/s + w/s`; высокий `wa` в `vmstat`.

## 14. Сетевые файловые системы: NFS, CIFS/SMB, sshfs

Назначение в нашем сценарии — вынос бэкапов на NAS или Windows-шару. **Каталог данных PostgreSQL и каталог кластера 1С на сетевые ФС не выносить** (для PostgreSQL на NFS документация ставит жёсткие условия, см. 14.1; CIFS для этого непригоден вовсе).

Общее правило для скриптов бэкапа:

```bash
mountpoint -q /mnt/winbackup || { echo "шара не смонтирована" >&2; exit 1; }
```

Иначе при недоступной шаре дамп будет записан в пустой каталог точки монтирования на корневой ФС и переполнит её. С `x-systemd.automount` достаточно сначала обратиться к каталогу (`ls /mnt/winbackup >/dev/null`), затем проверить `mountpoint -q`.

### 14.1. NFS

**Сервер** (Linux-NAS или второй сервер Ubuntu) [офиц., Ubuntu Server docs]:

```bash
sudo apt install nfs-kernel-server
sudo mkdir -p /srv/backup && sudo chown postgres:postgres /srv/backup
sudoedit /etc/exports
```

```text
# /etc/exports: <каталог> <клиент>(<опции>) — между клиентом и скобкой НЕ должно быть пробела
/srv/backup   192.168.10.0/24(rw,sync,no_subtree_check)
/srv/backup   192.168.10.21(rw,sync,no_subtree_check,no_root_squash)
```

```bash
sudo exportfs -ra              # перечитать /etc/exports и применить
sudo exportfs -v               # что экспортируется и с какими опциями
sudo systemctl status nfs-server    # она же nfs-kernel-server.service
sudo ufw allow from 192.168.10.0/24 to any port nfs   # 2049/tcp
```

Опции экспорта [офиц., exports(5)]:

| Опция | Смысл |
|---|---|
| `rw` / `ro` | чтение-запись / только чтение (умолчание — `ro`) |
| `sync` | отвечать клиенту только после записи на диск (умолчание); `async` быстрее, но нарушает протокол и теряет данные при сбое сервера |
| `no_subtree_check` | не проверять принадлежность файла экспортируемому поддереву (рекомендуется; указывать явно) |
| `root_squash` | root клиента превращается в анонимного пользователя (умолчание, uid/gid 65534); `no_root_squash` — root остаётся root |
| `all_squash`, `anonuid=`, `anongid=` | всех пользователей отображать в одного (удобно для «общей папки бэкапов») |
| `sec=sys\|krb5\|krb5i\|krb5p` | аутентификация: по uid (умолчание) или Kerberos |

Клиент задаётся именем хоста, IP, подсетью `адрес/маска`, шаблоном `*.example.com` или `*`. NFS с `sec=sys` доверяет числовым uid/gid: uid пользователя `postgres` на клиенте и сервере должны совпадать, либо используйте `all_squash,anonuid=…,anongid=…`. Настройки сервера с 22.04 — в `/etc/nfs.conf` и `/etc/nfs.conf.d/*.conf`. NFSv4 — один порт 2049/tcp; для NFSv3 дополнительно нужны rpcbind (111) и mountd.

**Клиент:**

```bash
sudo apt install nfs-common
showmount -e nas.example.local                       # список экспортов (работает через NFSv3/rpcbind)
sudo mkdir -p /mnt/nasbackup
sudo mount -t nfs -o vers=4.2 nas.example.local:/srv/backup /mnt/nasbackup
nfsstat -m                                           # действующие опции каждого NFS-монтирования
```

Строка `fstab`:

```text
nas.example.local:/srv/backup  /mnt/nasbackup  nfs  vers=4.2,noatime,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=30s  0 0
```

`hard` (умолчание) — при недоступности сервера операции ждут бесконечно; `soft` — возвращают ошибку по таймауту, что грозит незаметно испорченным файлом. Для бэкапов оставляйте `hard`.

PostgreSQL на NFS [офиц.]: единственное жёсткое требование — монтирование с `hard`; на сервере настоятельно рекомендуется экспорт с `sync`, иначе `fsync` клиента не гарантирует запись на носитель сервера («could cause corruption similar to running with the parameter fsync off»).

### 14.2. CIFS/SMB — шара Windows или NAS

```bash
sudo apt install cifs-utils            # mount.cifs; для диагностики ещё smbclient
sudo mkdir -p /mnt/winbackup
```

Файл с учётными данными (пароль в `fstab` писать нельзя — файл читают все):

```bash
sudo install -m 600 -o root -g root /dev/null /etc/cifs-backup.cred
sudoedit /etc/cifs-backup.cred
```

```text
username=svc_backup
password=СекретныйПароль
domain=WORKGROUP
```

Формат строгий: без пробелов вокруг `=`. Для доменной учётной записи `CORP\svc_backup` — `username=svc_backup` и `domain=CORP`.

Разовое монтирование:

```bash
sudo mount -t cifs //192.168.10.5/backup1c /mnt/winbackup \
  -o credentials=/etc/cifs-backup.cred,uid=postgres,gid=postgres,file_mode=0640,dir_mode=0750,vers=3.1.1,iocharset=utf8
```

Строка `fstab`:

```text
//192.168.10.5/backup1c  /mnt/winbackup  cifs  credentials=/etc/cifs-backup.cred,uid=postgres,gid=postgres,file_mode=0640,dir_mode=0750,vers=3.1.1,iocharset=utf8,_netdev,nofail,x-systemd.automount,x-systemd.idle-timeout=600,x-systemd.mount-timeout=30s  0 0
```

```bash
sudo systemctl daemon-reload
sudo systemctl start mnt-winbackup.automount     # включить автомонтирование без перезагрузки
ls /mnt/winbackup && findmnt /mnt/winbackup      # первое обращение монтирует шару
```

Опции [офиц., mount.cifs(8)]:

| Опция | Смысл |
|---|---|
| `credentials=файл` | файл со строками `username=`, `password=`, `domain=` |
| `uid=`, `gid=` | владелец и группа всех файлов на смонтированной шаре (умолчание — 0, то есть root) |
| `file_mode=`, `dir_mode=` | права файлов и каталогов, если сервер не поддерживает Unix-расширения (Windows не поддерживает) |
| `forceuid`, `forcegid` | игнорировать uid/gid, присланные сервером |
| `vers=` | диалект: `1.0`, `2.0`, `2.1`, `3.0`, `3.02`, `3.1.1` (`3.11`), `3`, `default`. Без указания клиент и сервер договариваются о наибольшей версии не ниже 2.1 (умолчание с ядра 4.13.5) |
| `sec=` | `ntlmssp` (умолчание), `ntlmsspi`, `krb5`, `krb5i`, `none` |
| `seal` | шифрование на уровне SMB3 |
| `domain=` | домен или рабочая группа |
| `iocharset=utf8` | кодировка имён файлов на стороне Linux (кириллица) |
| `noperm` | клиент не проверяет права локально (решает сервер) |
| `cache=strict\|none\|loose` | режим кэширования (умолчание `strict`) |
| `mfsymlinks` | эмуляция символических ссылок |
| `soft` / `hard` | при обрыве связи: вернуть ошибку (умолчание `soft`) / ждать |
| `rsize=`, `wsize=` | размер блоков чтения/записи (по умолчанию запрашивается 4 МБ) |

Особенности и ограничения:

- `uid/gid/file_mode/dir_mode` — это «маска» на всю шару: `chown` и `chmod` на CIFS-томе с Windows-сервером не работают. Программы, пытающиеся сохранить владельца и права (`cp -a`, `rsync -a`, `tar -p`), выдают предупреждения; используйте `cp`, `rsync -rt --no-perms --no-owner --no-group`.
- Запись выполняет пользователь из `uid=`: если бэкап делает `postgres`, ставьте `uid=postgres,gid=postgres`; если скрипт от root — подойдёт умолчание.
- SMB1 (`vers=1.0`) небезопасен и в современных Windows отключён. Начинайте без `vers=` или с `vers=3.1.1`.
- Пробел в имени шары в `fstab` — `\040`: `//server/My\040Backups`.
- Надёжнее сначала сделать дамп на локальный том, проверить, затем копировать на шару: обрыв сети во время прямой записи даёт испорченный файл.
- `mount error: cifs filesystem not supported by the system` — в ядре нет модуля `cifs`. Проверка: `modinfo cifs` (модуль есть на диске?) и `sudo modprobe cifs && lsmod | grep cifs`. ⚠ не подтверждено ни для одной из трёх LTS (по памяти, списки файлов пакетов не открывались): на урезанных ядрах (`linux-kvm`, облачные `linux-aws`/`linux-azure`) модуль лежит в пакете `linux-modules-extra-$(uname -r)` — `sudo apt install linux-modules-extra-$(uname -r)`; на обычном ядре `linux-generic` он установлен вместе с системой.

Диагностика:

```bash
sudo dmesg | tail -20                               # строки «CIFS: VFS: …» со статусом сервера (STATUS_LOGON_FAILURE, STATUS_ACCESS_DENIED, STATUS_BAD_NETWORK_NAME)
smbclient -L //192.168.10.5 -U svc_backup           # список шар и проверка учётной записи (пакет smbclient)
sudo mount -t cifs -v //192.168.10.5/backup1c /mnt/winbackup -o credentials=/etc/cifs-backup.cred
nc -zv 192.168.10.5 445                             # доступен ли порт SMB
```

| Ошибка | Причина |
|---|---|
| `mount error(13): Permission denied` | неверный логин/пароль/домен; пробелы вокруг `=` в credentials; у учётной записи нет прав на шару или на NTFS-каталог |
| `mount error(2): No such file or directory` | неверное имя шары |
| `mount error(112): Host is down` | несовместимая версия протокола — указать `vers=` явно |
| `mount error(115): Operation now in progress`, `(113): No route to host` | порт 445 закрыт брандмауэром Windows или сеть недоступна |

На стороне Windows-хоста: отдельная локальная учётная запись с паролем; общий доступ к папке с правом «Изменение» и NTFS-права на запись; разрешено входящее правило брандмауэра «Общий доступ к файлам и принтерам (SMB)» для сети, в которой находится ВМ. Адрес хоста на «Default Switch» Hyper-V меняется после перезагрузки — используйте внутренний или внешний коммутатор со статическим адресом ⚠ не подтверждено (практика).

### 14.3. sshfs

Монтирование каталога удалённой машины через SFTP — когда есть только SSH:

```bash
sudo apt install sshfs
sudo mkdir -p /mnt/remote
sudo sshfs backup@10.0.0.7:/srv/backup /mnt/remote \
     -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,IdentityFile=/root/.ssh/id_ed25519
sudo sshfs -p 2222 -C backup@host:/dir /mnt/remote     # другой порт, сжатие
fusermount3 -u /mnt/remote                             # размонтировать (или sudo umount /mnt/remote)
```

`-o reconnect` — переподключаться при обрыве; `-o allow_other` — дать доступ другим пользователям (при монтировании не от root требует `user_allow_other` в `/etc/fuse.conf`; сочетать с `default_permissions`); `-o idmap=user` — отобразить uid удалённого пользователя на локального.

Строка `fstab` (тип `sshfs` или `fuse.sshfs`):

```text
backup@10.0.0.7:/srv/backup  /mnt/remote  fuse.sshfs  noauto,x-systemd.automount,_netdev,reconnect,ServerAliveInterval=15,IdentityFile=/root/.ssh/id_ed25519,allow_other,default_permissions  0 0
```

sshfs работает в пространстве пользователя (FUSE) поверх шифрованного канала и заметно медленнее NFS/SMB. Для регулярной передачи бэкапов по SSH лучше `rsync -a --partial` или `scp`; sshfs — для разовых задач.

## 15. tmpfs и `/tmp`

tmpfs — ФС в оперативной памяти (страницы могут вытесняться в swap). Память занимается по мере записи файлов; предел задаётся `size=` (по умолчанию половина ОЗУ).

```bash
df -h -t tmpfs                                   # все tmpfs: /run, /dev/shm, /run/user/…, в 26.04 ещё /tmp
sudo mkdir -p /mnt/ramtmp
sudo mount -t tmpfs -o size=2G,mode=1777,nosuid,nodev tmpfs /mnt/ramtmp
sudo mount -o remount,size=4G /mnt/ramtmp        # изменить предел на лету
```

`fstab`: `tmpfs /mnt/ramtmp tmpfs rw,nosuid,nodev,size=2G,mode=1777 0 0`.

`/dev/shm` — tmpfs, через который PostgreSQL выделяет динамическую разделяемую память (`dynamic_shared_memory_type = posix`) для параллельных запросов; при слишком маленьком `/dev/shm` (контейнеры) возникают ошибки `could not resize shared memory segment`.

### 15.1. `/tmp` в Ubuntu 26.04 — в ОЗУ

Начиная с Ubuntu 24.10 используется штатный юнит systemd `tmp.mount`, и `/tmp` — это tmpfs [офиц., release notes 24.10 и 26.04]. В 22.04 и 24.04 `/tmp` — обычный каталог на корневой ФС. Проверка: `findmnt /tmp`.

Что именно делает юнит [офиц.]: в заметках к выпуску 26.04 сказано «Ubuntu now comes with the upstream `tmp.mount` unit by default» (изменение 24.10). В исходном коде systemd v259 этот юнит монтирует tmpfs с `Options=mode=1777,strictatime,nosuid,nodev,size=50%,nr_inodes=1m` — предел **50 % ОЗУ** и не больше 1 млн inode (память расходуется только под реально созданные файлы). Там же, в исходном `tmpfiles.d/tmp.conf`: `q /tmp 1777 root root 10d` и `q /var/tmp 1777 root root 30d` — файлы, которые не читали и не меняли 10 дней в `/tmp` и 30 дней в `/var/tmp`, удаляет `systemd-tmpfiles-clean.timer`. **Уточнено 11.10.2026** по журналу изменений пакета systemd 259-1ubuntu3 (changelogs.ubuntu.com): Debian с версии 256~rc3-3 убрал свою правку `tmp.conf` и вернул исходное поведение (очистка `/tmp` раз в 10 дней и `/var/tmp` раз в 30 дней, `/tmp` на tmpfs); Ubuntu сначала сохранила свой срок 30 дней для `/tmp` (256~rc3-5ubuntu1), но в 256-1ubuntu1 сняла эту правку («We want to stay aligned with Debian and upstream instead of keeping this 30d cleanup»). То есть в 26.04, судя по журналу, действуют исходные сроки — 10 дней для `/tmp` и 30 дней для `/var/tmp`; сам файл из пакета не читался. Ранее было не подтверждено только одно: не изменяет ли пакет systemd в Ubuntu эти два файла своими патчами (исходники пакета на Launchpad при проверке не открылись). Фактические значения на сервере:

```bash
findmnt /tmp                                   # tmpfs или каталог корневой ФС; действующий size=
systemctl cat tmp.mount                        # строка Options= вашего пакета
cat /usr/lib/tmpfiles.d/tmp.conf               # сроки очистки /tmp и /var/tmp («-» в последнем поле = не чистить по возрасту)
systemctl list-timers systemd-tmpfiles-clean.timer
```

Изменить предел — `sudo systemctl edit tmp.mount`:

```text
[Mount]
Options=mode=1777,strictatime,nosuid,nodev,size=2G,nr_inodes=1m
```

Если предел задаётся в процентах, знак процента в файле юнита удваивается: `size=25%%` (одиночный `%` systemd воспринимает как начало спецификатора). Применить без перезагрузки: `sudo systemctl daemon-reload && sudo mount -o remount,size=2G /tmp`.

Вернуть `/tmp` на диск: `sudo systemctl mask tmp.mount` и перезагрузка [офиц., заметки к выпуску Debian 13, откуда Ubuntu получила изменение]. Запись о `/tmp` в `/etc/fstab` имеет приоритет над `tmp.mount` (можно сделать `/tmp` отдельным LV). Правила очистки переопределяются одноимённым файлом `/etc/tmpfiles.d/tmp.conf`; исключения — строки вида `x /tmp/каталог`. Действующие правила: `systemd-tmpfiles --cat-config | grep -E '[[:space:]]/(var/)?tmp[[:space:]]'`.

**Уточнено 11.10.2026**: текст правки Debian прочитан (метка `debian/255.4-1` на salsa.debian.org; та же правка есть в 249.7-1): вместо исходных строк стоят `D /tmp 1777 root root -` (очистка `/tmp` при загрузке, без срока хранения) и закомментированная `#q /var/tmp 1777 root root 30d` (каталог `/var/tmp` автоматически не очищается). В Ubuntu 24.04 поверх этого для `/tmp` добавлен срок 30 дней (журнал изменений 255.4-1ubuntu2, LP: #2019026); в журнале пакета 22.04 такой правки нет. Сами файлы из пакетов Ubuntu не читались. Ранее было не подтверждено для 22.04 и 24.04: там `/tmp` лежит на диске, но правила очистки в `tmp.conf` отличаются от исходных systemd (исторически Debian/Ubuntu правили этот файл: очистка `/tmp` при загрузке и иной срок хранения). Не полагайтесь на память — смотрите `cat /usr/lib/tmpfiles.d/tmp.conf` на конкретном сервере. В любом случае `/tmp` — не место для файлов, которые должны пережить перезагрузку.

### 15.2. Что это значит для сервера 1С

Сервер 1С (`ragent`, `rmngr`, `rphost`) пишет временные файлы в каталог из переменной `TMPDIR`, по умолчанию — `/tmp` [офиц.: статья ИТС от 18.01.2010 и её перевод в библиотеке 1Ci «How to change temporary directory of 1C:Enterprise server»: «The default temporary file directory is /tmp»; там же предупреждение, что автоматическая очистка `/tmp` (в статье — `tmpwatch` из `/etc/cron.daily` в Fedora Core 4) может удалить нужные серверу файлы]. Статья написана для init-скриптов: переменную предлагается задать в `.bash_profile` пользователя, от имени которого работает сервер (`TMPDIR=/tmp/.usr1cv82; export TMPDIR`), а каталог исключить из `tmpwatch -x`. Для службы systemd это **не работает**: systemd не читает `.bash_profile`. Следствия для современных систем:

- на 26.04 временные файлы 1С по умолчанию расходуют **ОЗУ и swap**; крупная выгрузка, отчёт или обмен может создать файлы на гигабайты и привести к нехватке памяти либо к «No space left on device» в `/tmp`;
- периодическая очистка `/tmp` может удалить файлы долго работающего процесса.

Решение [практика] — отдельный каталог на диске и переменная окружения в юните службы:

```bash
sudo mkdir -p /srv/1c-tmp
sudo chown usr1cv8:grp1cv8 /srv/1c-tmp && sudo chmod 700 /srv/1c-tmp
sudo systemctl edit srv1cv8-<версия>@default.service
```

```text
[Service]
Environment=TMPDIR=/srv/1c-tmp
```

```bash
sudo systemctl restart srv1cv8-<версия>@default.service
sudo ls -la /srv/1c-tmp            # после запуска здесь должны появиться временные файлы
```

Что здесь подтверждено, а что нет:

- **Имя юнита и механизм drop-in — официальные.** Документация платформы 8.3.27 (клиент-серверный вариант, глава 4, п. 4.2.2.3.1 и 4.2.2.4.1; конспект — `kb/its-docs/cs-gl04-zapusk-komponentov.md`): юнит-шаблон `/opt/1cv8/<arch>/A.B.C.D/srv1cv8-A.B.C.D@.service` регистрируется командой `systemctl link`, экземпляр с параметрами по умолчанию называется `default` (служба `srv1cv8-A.B.C.D@default`), а параметры меняются именно так: `systemctl edit srv1cv8-A.B.C.D@instanceName` → секция `[Service]` → строки `Environment=ИМЯ=значение`. Точное имя на сервере: `systemctl list-units 'srv1cv8*'`.
- **`TMPDIR` в `Environment=` — практика сообщества (сама переменная `TMPDIR` подтверждена статьёй ИТС 1736; задание её через `Environment=` юнита — практика).** В официальном перечне параметров юнита (`SRV1CV8_DATA`, `SRV1CV8_DEBUG`, `SRV1CV8_KEYTAB`, `SRV1CV8_PINGPERIOD`, `SRV1CV8_PINGTIMEOUT`, `SRV1CV8_PORT`, `SRV1CV8_RANGE`, `SRV1CV8_REGPORT`, `SRV1CV8_SECLEV`) переменной для временного каталога нет; `TMPDIR` — обычная переменная окружения процесса, которую systemd передаёт `ragent` и порождённым им `rmngr`/`rphost`. Иногда задают сразу `TMPDIR`, `TEMP` и `TMP`. После перезапуска обязательно проверьте результат: `sudo cat /proc/$(pgrep -o rphost)/environ | tr '\0' '\n' | grep -i tmp` и появление файлов в новом каталоге.
- Права: глава «Требования» документации 8.3.27 называет для пользователя кластера в Linux полные права на каталог данных кластера и право чтения на каталог временных файлов [офиц., конспект `kb/its-docs/cs-gl01-trebovaniya.md`]; статья о `TMPDIR` требует, чтобы пользователь сервера имел право **записи** в новый временный каталог [офиц., 1Ci]. На практике давайте `usr1cv8:grp1cv8` полные права (`chmod 700`), как в примере выше.
- ФС каталога не должна быть смонтирована с `noexec` — известны случаи отказа внешних компонент после переноса временного каталога [практика ⚠].
- После обновления платформы имя юнита меняется (в нём номер версии), а drop-in привязан к имени: перенесите `/etc/systemd/system/srv1cv8-<старая версия>@default.service.d/` на новое имя, иначе сервер снова начнёт писать в `/tmp`.

### 15.3. tmpfs и PostgreSQL

- **`pg_stat_tmp` на tmpfs** — совет из руководства Postgres Pro для 1С (K.3). Актуален для PostgreSQL 14 и старше (`stats_temp_directory`); с PostgreSQL 15 накопительная статистика хранится в разделяемой памяти и параметр удалён.
- **Табличное пространство на tmpfs** (например, для `temp_tablespaces`) — документация PostgreSQL предупреждает: «Placing a tablespace on a temporary file system like a RAM disk risks the reliability of the entire cluster». Для временных таблиц 1С используйте отдельный быстрый дисковый том (раздел 16.3).

## 16. Рекомендации по разметке сервера 1С + PostgreSQL

### 16.1. Принципы

1. **Разные по характеру данные — на разных томах**: система; данные PostgreSQL; WAL; временные объекты PostgreSQL; каталог кластера 1С; бэкапы. Переполнение одного тома тогда не останавливает остальные: разросшийся журнал регистрации 1С не остановит СУБД, а бэкап не съест место под WAL.
2. **Бэкапы — на другом физическом носителе**, в идеале на другом устройстве (NAS, Windows-шара, второй сервер). Том бэкапов внутри того же VHDX от отказа диска не защищает.
3. **Скорость даёт только физическое разделение.** Вынос WAL или временных таблиц на отдельный виртуальный диск ускоряет работу, лишь если на хосте он лежит на другом носителе или массиве. Если все виртуальные диски — файлы на одном SSD хоста, разделение даёт управляемость (независимый рост, изоляция переполнения), но не скорость.
4. **LVM везде, кроме `/boot` и ESP**; в каждом VG оставлять 10–20 % свободных экстентов.
5. **Отдельный виртуальный диск на каждую роль** (система / PostgreSQL / бэкапы) упрощает расширение на лету, перенос и замену носителя.
6. Следить за заполнением: рабочий порог тревоги — 80 %, критический — 90 %. PostgreSQL при переполнении тома с `pg_wal` аварийно останавливается.

### 16.2. Пример разметки ВМ

| Диск | Том | Точка монтирования | ФС и опции | Размер (ориентир) |
|---|---|---|---|---|
| `sda` (система) | `sda1` | `/boot/efi` | vfat | как создал установщик |
| | `sda2` | `/boot` | ext4 | как создал установщик |
| | `ubuntu-vg/ubuntu-lv` | `/` | ext4 | 30–50 ГБ |
| | `ubuntu-vg/lv_1c` | `/home/usr1cv8` | ext4, `noatime` | от 30 ГБ; растёт с журналом регистрации |
| | `ubuntu-vg/lv_1ctmp` (по желанию) | `/srv/1c-tmp` | ext4, `noatime` | 10–50 ГБ |
| | `/swap.img` или `ubuntu-vg/lv_swap` | swap | — | раздел 9.4 |
| `sdb` (СУБД) | `vg_pg/lv_pgdata` | `/var/lib/postgresql` (Postgres Pro: `/var/lib/pgpro`) | ext4 `-m 1` или XFS, `noatime` | размер баз × 2–3 |
| | `vg_pg/lv_pgwal` (по желанию) | `/pgwal` | ext4 или XFS, `noatime` | `max_wal_size` × 3 + запас на простой архивации, обычно 20–50 ГБ |
| | `vg_pg/lv_pgtemp` (по желанию) | `/pgtemp` | ext4 или XFS, `noatime` | 20–100 ГБ |
| `sdc` (бэкапы) | `vg_bak/lv_backup` | `/backup` | ext4 `-m 0 -T largefile`, `noatime,nofail` | N копий × размер дампа |
| сеть | — | `/mnt/winbackup` | cifs или nfs, `_netdev,nofail,x-systemd.automount` | — |

Пояснения:

- **Каталог кластера сервера 1С** по умолчанию — `/home/usr1cv8/.1cv8/1C/1cv8`: это значение по умолчанию параметра `SRV1CV8_DATA` («каталог данных сервера: полный путь к каталогу служебных файлов кластера серверов») [офиц., документация 8.3.27, п. 4.2.2.4.3; конспект `kb/its-docs/cs-gl04-zapusk-komponentov.md`]; у `ragent` ему соответствует ключ `-d`. Внутри: `1cv8wsrv.lst` (список кластеров компьютера), `reg_<порт>/` (обычно `reg_1541`) с реестром кластера `1CV8Clst.lst` [офиц.: имена файлов — приложение «Служебные файлы» документации, конспект `kb/its-docs/adm-pr03-sluzhebnye-fajly-p1.md`; Linux-пути этих двух файлов в документации не приведены, только Windows-примеры `srvinfo\…`], журналами регистрации баз (`<идентификатор базы>/1Cv8Log`), индексами полнотекстового поиска и сеансовыми данными (`snccntx…` — имя каталога известно из практики сообщества). Растёт в основном за счёт журнала регистрации. Каталог `srvinfo` — это имя из Windows-установки; в Linux такого каталога нет, пока его не назвали так сами. Проще всего смонтировать отдельный том в `/home/usr1cv8` **до** установки сервера 1С либо перенести данные при остановленной службе (`rsync -aHAX`), сохранив владельца `usr1cv8:grp1cv8`; альтернатива — отдельный том в произвольном месте и `Environment=SRV1CV8_DATA=/srv/1c/cluster` в drop-in юнита (тот же механизм, что в разделе 15.2). Если агент стартует с другим (пустым) каталогом данных, он молча создаёт новый пустой кластер — «пропавшие» базы первым делом проверяйте по `systemctl show srv1cv8-…@default -p Environment`.
- Минимальные требования 1С к серверу «1С:Предприятия» (64-разрядному): от 2 ГБ ОЗУ (рекомендуется от 4 ГБ) и жёсткий диск от 40 ГБ; требования «минимальные и не учитывают прикладные решения» [офиц., v8.1c.ru, проверено 2026-10-10]. В документации платформы 8.3.27 цифры другие: ОЗУ минимум 4 ГБ, рекомендуется от 8 ГБ, на установку — от 1 ГБ диска без учёта базы данных [офиц., глава «Требования», конспект `kb/its-docs/cs-gl01-trebovaniya.md`]. Для планирования берите большее из двух и добавляйте место под журнал регистрации и временные файлы (загрузка `.dt` требует на сервере 1С свободного места под временные файлы примерно в объёме развёрнутой базы — там же, глава об администрировании ИБ).
- **Размер тома данных PostgreSQL**: кроме самих баз нужен запас на раздувание (bloat), `VACUUM FULL`/`REINDEX` (временно требуется копия таблицы или индекса), реструктуризацию при обновлении конфигурации 1С (создаются новые таблицы и копируются данные) и развёртывание копий баз.
- **Не делать каталог данных точкой монтирования** — монтировать том на уровень выше (`/var/lib/postgresql`), см. раздел 5.4.
- **`pg_wal` на отдельном томе**: при создании кластера — `initdb --waldir=/pgwal/18/main` (в Ubuntu: `pg_createcluster 18 main -- --waldir=/pgwal/18/main`); для существующего — остановить PostgreSQL, перенести каталог, создать символическую ссылку:

```bash
sudo systemctl stop postgresql@18-main
sudo mkdir -p /pgwal/18 && sudo chown postgres:postgres /pgwal/18 && sudo chmod 700 /pgwal/18
sudo -u postgres mv /var/lib/postgresql/18/main/pg_wal /pgwal/18/main
sudo -u postgres ln -s /pgwal/18/main /var/lib/postgresql/18/main/pg_wal
sudo systemctl start postgresql@18-main
```

  После этого снапшот одного LV уже не годится как копия кластера (раздел 7.7).

### 16.3. Временные объекты PostgreSQL на отдельном томе

1С интенсивно использует временные таблицы. Postgres Professional в руководстве для 1С рекомендует: `temp_tablespaces` — табличное пространство на отдельных быстрых дисках [офиц., K.3].

```bash
sudo mkdir -p /pgtemp/18 && sudo chown postgres:postgres /pgtemp/18 && sudo chmod 700 /pgtemp/18
sudo -u postgres psql -c "CREATE TABLESPACE temp_ts LOCATION '/pgtemp/18';"
sudo -u postgres psql -c "GRANT CREATE ON TABLESPACE temp_ts TO PUBLIC;"
sudo -u postgres psql -c "ALTER SYSTEM SET temp_tablespaces = 'temp_ts';"
sudo -u postgres psql -c "SELECT pg_reload_conf();"
```

`GRANT CREATE` нужен, если 1С подключается не суперпользователем: без права `CREATE` табличное пространство из `temp_tablespaces` молча игнорируется. Табличное пространство — неотъемлемая часть кластера: том `/pgtemp` должен монтироваться раньше запуска PostgreSQL (`RequiresMountsFor=`), попадать в физические бэкапы и не быть tmpfs. Если его диски по характеристикам отличаются от основных, для него задают свой `random_page_cost` (`ALTER TABLESPACE temp_ts SET (random_page_cost = 1.1);`).

### 16.4. Параметры PostgreSQL, зависящие от дисков

Из руководства Postgres Professional для 1С [офиц., K.3; значения — стартовые]: `random_page_cost` — 1.5–2.0 для RAID, 1.1–1.3 для SSD; `effective_io_concurrency` — 2 для вращающихся дисков, для SSD пробовать сотни; `checkpoint_timeout = 15min`; `min_wal_size = 512MB…4GB`, `max_wal_size = 2 × min_wal_size`; `fsync = on` (при кэше контроллера в режиме write-back — следить за батареей); `synchronous_commit = off` допустим, если важнее скорость: риск — потеря последних транзакций при сбое, но не нарушение целостности.

PostgreSQL 18 [офиц.]: новая подсистема асинхронного ввода-вывода — `io_method = worker` (умолчание; также `io_uring` и `sync`), `io_workers = 3`; умолчание `effective_io_concurrency` поднято до 16; страницы данных по умолчанию защищены контрольными суммами.

### 16.5. Контрольный список после разметки

```bash
lsblk -f                                  # все тома на месте, у каждого своя ФС и точка монтирования
sudo findmnt --verify                     # fstab без ошибок
findmnt -no OPTIONS /var/lib/postgresql   # действует noatime
df -hT && df -i                           # место и inode
sudo vgs                                  # в VG оставлен резерв
swapon --show                             # подкачка включена
systemctl status fstrim.timer             # TRIM по расписанию
grep . /sys/block/sd*/queue/scheduler     # планировщики
sudo -u postgres /usr/lib/postgresql/18/bin/pg_test_fsync -f /pgwal/18/pg_test_fsync.out   # диск под WAL честный и быстрый (каталог /pgwal/18 принадлежит postgres)
sudo reboot                               # и убедиться, что после перезагрузки всё смонтировалось само
```

## Типичные ошибки и подводные камни (симптом → причина → решение)

| № | Симптом | Причина | Решение |
|---|---|---|---|
| 1 | После установки корень 48 ГБ, хотя диск 100 ГБ | политика Subiquity: `ubuntu-lv` получает половину VG | `sudo vgs`; `sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv` или создать отдельные LV (7.6) |
| 2 | Диск ВМ увеличили, а `lsblk` показывает старый размер | ядро не перечитало размер устройства | `echo 1 \| sudo tee /sys/class/block/sda/device/rescan` (8.2) |
| 3 | `growpart`: `NOCHANGE: partition 3 is size … it cannot be grown` | не сделан rescan; за разделом нет свободного места; прирост меньше порога `--fudge` (1 МиБ в текущем коде, 10 МБ по man 24.04) | rescan; `sudo parted /dev/sda print free`; расти может только раздел, за которым есть свободное место |
| 4 | `growpart` падает с `No space left on device` | корень заполнен на 100 %, а `growpart` создаёт рабочий каталог через `mktemp -d` в `${TMPDIR:-/tmp}` | освободить немного места (`sudo apt clean`, `sudo journalctl --vacuum-size=100M`) либо `sudo TMPDIR=/dev/shm growpart /dev/sda 3` (подтверждено исходным кодом growpart) |
| 5 | `lvextend` выполнен, а `df` показывает старый размер | забыт `-r` — увеличен только LV | `sudo resize2fs /dev/VG/LV` (ext4) или `sudo xfs_growfs /точка` (XFS) |
| 6 | `xfs_growfs: … is not a mounted XFS filesystem` | XFS растёт только смонтированной; аргумент — точка монтирования | смонтировать и повторить |
| 7 | `resize2fs: Bad magic number in super-block` | на томе XFS, а не ext4 (или указан не тот узел) | `lsblk -f`; для XFS — `xfs_growfs` |
| 8 | Сервер не загружается: «You are in emergency mode» | строка в `fstab` без `nofail` указывает на отсутствующее устройство, неверный UUID или опцию | с консоли: `mount -o remount,rw /`, исправить `/etc/fstab`, `systemctl daemon-reload`, `mount -a`; впредь `findmnt --verify` и `nofail` |
| 9 | Загрузка «висит» 1,5 минуты | ожидание несуществующего устройства или сетевой шары (тайм-аут 90 с) | `nofail,x-systemd.device-timeout=10s`; для сетевых — `_netdev,x-systemd.automount` |
| 10 | `mount: (hint) your fstab has been modified, but systemd still uses the old version` | после правки `fstab` не перечитана конфигурация systemd | `sudo systemctl daemon-reload` |
| 11 | После перезагрузки том данных не смонтирован, PostgreSQL создал пустой кластер или не стартует | в `fstab` имя `/dev/sdb1`, а диски поменялись местами; либо том монтируется позже старта службы | `UUID=` или `/dev/mapper/…`; `RequiresMountsFor=` в юните; каталог данных — подкаталог тома |
| 12 | «No space left on device», а `df -h` показывает свободное место | кончились inode; либо резерв root на ext4 (процесс не root) | `df -i`; удалить мелкие файлы; `sudo tune2fs -m 1 /dev/…` |
| 13 | `df` показывает 100 %, `du` находит намного меньше | удалённые, но открытые файлы; данные под точкой монтирования | `sudo lsof +L1`; перезапуск процесса или `: > /proc/PID/fd/N`; проверка через `mount --bind / /mnt/rootonly` |
| 14 | Корень заполнился дампами баз | шара или том бэкапов не были смонтированы, скрипт писал в пустой каталог | `mountpoint -q` в скрипте; можно защитить пустую точку монтирования: `sudo chattr +i /mnt/winbackup` (на размонтированном каталоге) |
| 15 | PostgreSQL остановился: `PANIC: could not write to file "pg_wal/…": No space left on device` | переполнен том с WAL: сломано архивирование, забытый слот репликации, мало места | расширить том (`lvextend -r`) — самое быстрое; затем устранить причину (6.5). Не удалять файлы `pg_wal` вручную |
| 16 | Снапшот LVM исчез или не монтируется, в `lvs` был `Data% 100` | место под изменения переполнилось — снапшот недействителен | удалить (`lvremove`), создавать с запасом или включить автоувеличение; не держать снапшоты подолгу |
| 17 | При живом снапшоте всё стало медленно | copy-on-write: каждая первая перезапись блока удваивает ввод-вывод | удалить снапшот сразу после использования |
| 18 | XFS-снапшот не монтируется: `Filesystem has duplicate UUID` | копия имеет тот же UUID, что и смонтированный оригинал | `mount -o ro,nouuid …` |
| 19 | Нужно уменьшить том XFS | XFS не уменьшается | новый том меньшего размера → перенос данных (`rsync -aHAX`) → переключение точки монтирования |
| 20 | `lvreduce` уничтожил данные | LV уменьшен раньше ФС или сильнее неё | только `lvreduce -r` (ext4), предварительно бэкап; восстановление — `vgcfgrestore` из `/etc/lvm/archive` + `e2fsck`, если место не успели перезаписать |
| 21 | `pvcreate`/`mkfs`: `signature detected`, `Device … excluded by a filter` | на диске старые сигнатуры (ФС, RAID, таблица разделов) | `sudo wipefs /dev/sdX` — посмотреть; `sudo wipefs -a /dev/sdX` — стереть (проверив, что диск тот) |
| 22 | После увеличения диска `parted`/`gdisk` сообщают: «Not all of the space available… appears to be used» или предупреждают о резервном заголовке GPT | резервная копия GPT осталась в старом конце диска | ответить `Fix` в `parted` либо `sudo sgdisk -e /dev/sda`; `growpart` делает это сам |
| 23 | `mkfs.ext4` на большом томе занимает минуты, после — фоновая запись (`ext4lazyinit`) | discard всего устройства и отложенная инициализация таблиц inode | для ускорения — `-E nodiscard`; перед замерами производительности — `-E lazy_itable_init=0,lazy_journal_init=0` |
| 24 | `dd` показал 2 ГБ/с на HDD | запись ушла в страничный кэш | `oflag=direct` или `conv=fdatasync` (13.2) |
| 25 | `pg_test_fsync`/`fio --fdatasync=1` дают десятки тысяч операций в секунду на обычном диске | сброс кэша не доходит до носителя (кэш хоста или контроллера без батареи) | проверить политику кэширования диска ВМ на хосте и кэш записи диска; иначе при сбое питания возможна порча БД |
| 26 | Шара Windows: `mount error(13): Permission denied` | логин/пароль/домен, пробелы в credentials, права на шару или NTFS | 14.2; `smbclient -L`; `dmesg \| tail` |
| 27 | На CIFS-шаре: `chown`/`chmod: Operation not permitted`, предупреждения `rsync`/`cp -a` | сервер Windows не хранит права Unix | задать `uid=,gid=,file_mode=,dir_mode=` при монтировании; копировать без сохранения владельца и прав |
| 28 | Сервер долго выключается или «зависает» `df` | недоступен сервер NFS (режим `hard`) или CIFS | `sudo umount -f -l /mnt/…`; для сетевых ФС — `x-systemd.automount` с `x-systemd.idle-timeout` |
| 29 | Ubuntu 26.04: растёт потребление ОЗУ/swap, «No space left on device» в `/tmp` при свободном диске | `/tmp` — tmpfs; временные файлы 1С лежат в памяти | `TMPDIR` службы 1С на дисковый каталог либо `systemctl mask tmp.mount` (раздел 15) |
| 30 | У сервера 1С пропадают временные файлы, ошибки в длительных операциях | автоочистка `/tmp` удалила файлы, которыми ещё пользуются | отдельный каталог вне `/tmp` через `TMPDIR` либо исключение в `/etc/tmpfiles.d/` |
| 31 | OOM killer убил `postgres` или `rphost` | нет подкачки или она мала; память перераспределена | включить swap (9.2), пересмотреть `shared_buffers`/`work_mem`/лимиты `rphost`; `sudo dmesg -T \| grep -i 'out of memory'` |
| 32 | `swapon: … swapfile has holes` или `insecure permissions 0644` | файл создан через `truncate`/`cp`; права не 600 | пересоздать через `dd` или `fallocate`; `chmod 600` |
| 33 | `umount: target is busy` | на томе открыты файлы или чей-то текущий каталог | `sudo lsof +f -- /точка`, `sudo fuser -vm /точка`; остановить службы |
| 34 | ФС внезапно стала только для чтения, PostgreSQL падает с ошибками записи | ядро обнаружило ошибку ФС или ввода-вывода и перемонтировало ФС в `ro` | `dmesg -T`; проверить диск и хранилище хоста; остановить службы, размонтировать, `e2fsck -f`/`xfs_repair`; при повторении — менять носитель |
| 35 | `smartctl` в ВМ ничего полезного не показывает | диск виртуальный | проверять SMART на хосте |
| 36 | Новый LV или PV не виден после клонирования ВМ или переноса диска | VG не активирована; конфликт имён VG | `sudo vgscan && sudo vgchange -ay`; при конфликте — `vgrename <UUID> новое_имя` |
| 37 | Emergency mode, а на консоли «Cannot open access to console, the root account is locked» | root в Ubuntu заблокирован, `sulogin` без `--force` оболочку не даёт | в GRUB дописать к строке `linux` `SYSTEMD_SULOGIN_FORCE=1` (24.04/26.04) или `init=/bin/bash`; либо загрузка с ISO; заранее — drop-in с `Environment=SYSTEMD_SULOGIN_FORCE=1` или пароль root (раздел 5.4) |
| 38 | Ubuntu 22.04: `parted: invalid option -- 'f'` | `--fix` появился в parted 3.5, в 22.04 — parted 3.4 | `sudo sgdisk -e /dev/sda` или `growpart`; в интерактивном `parted` ответить `Fix` |
| 39 | Ubuntu 22.04: `lsblk: invalid option -- 'N'`; `X-fstrim.notrim` «не работает» | опции появились в util-linux 2.39 и 2.38, в 22.04 — 2.37.2 | `lsblk -d -o NAME,TRAN,MODEL`; исключать ФС из TRIM другим способом (свой `fstrim` по списку точек) |
| 40 | Ubuntu 26.04: `lvreduce` отказывается уменьшать том, ссылаясь на размер файловой системы | умолчание `--fs checksize`: отрезаемое место занято ФС | это защита, а не ошибка: уменьшать через `lvreduce -r` (только ext4, с бэкапом); `--fs ignore` уничтожит ФС |
| 41 | Том XFS, созданный на новой Ubuntu, не монтируется на старой: «Superblock has unknown incompatible features … cannot be safely mounted by this kernel» | новые умолчания `mkfs.xfs` (`nrext64`, `bigtime`, `inobtcount`, `rmapbt`) не поддерживаются старым ядром | монтировать на системе с новым ядром (HWE) либо пересоздать том `mkfs.xfs` на старой системе / с профилем из `/usr/share/xfsprogs/mkfs/` и перенести данные |
| 42 | В `lvs` появляется и исчезает том `<имя>.e2scrub`; раз в неделю всплеск ввода-вывода | `e2scrub_all.timer` проверяет ext4 на LVM через временный снапшот (если в VG есть ≥ 256 МиБ свободного места) | это штатно; при желании `sudo systemctl disable --now e2scrub_all.timer`; «зависший» снапшот убрать `sudo e2scrub -r /dev/VG/LV` |
| 43 | После установки Ubuntu Server нет подкачки (`swapon --show` пусто) | эвристика curtin вернула 0: допустимый размер (25 % свободного места ФС) оказался меньше половины ОЗУ и меньше 4 ГиБ | создать файл или LV подкачки вручную (раздел 9.2–9.3) |
| 44 | После обновления платформы 1С сервер снова пишет временные файлы в `/tmp`, «пропали» настройки портов/каталога | drop-in systemd привязан к имени юнита с номером версии (`srv1cv8-A.B.C.D@default.service.d`) | перенести каталог drop-in на имя нового юнита, `systemctl daemon-reload`, перезапустить службу; проверить `systemctl show … -p Environment` |
| 45 | Hyper-V: размер диска работающей ВМ не меняется (кнопка недоступна, ошибка) | диск формата `.vhd`, или подключён к IDE (ВМ поколения 1), или у ВМ есть контрольные точки | онлайн — только VHDX на SCSI; иначе выключить ВМ; контрольные точки удалить (объединить) до расширения |

Ещё несколько правил безопасности:

- Перед любой операцией с разделами и LVM на боевом сервере — свежий бэкап баз и, если возможно, контрольная точка ВМ на хосте (и не забыть её удалить: контрольные точки замедляют диск и мешают изменению размера VHDX).
- Сохраните разметку: `sudo sfdisk -d /dev/sda > /root/sda.sfdisk`, `sudo vgcfgbackup`, копии `/etc/fstab` и вывода `lsblk -f`, `blkid`.
- Увеличение — безопасная онлайн-операция; уменьшение — всегда риск и простой.
- Не используйте `--force`, `-ff`, `-y`, пока не прочитали, о чём именно предупреждает команда.

## Быстрая шпаргалка — «задача → команда»

| Задача | Команда |
|---|---|
| Диски, разделы, ФС, UUID, точки монтирования | `lsblk -f` |
| Только физические диски с моделью и типом | `lsblk -d -o NAME,SIZE,MODEL,TRAN,ROTA` |
| UUID тома для fstab | `sudo blkid -s UUID -o value /dev/VG/LV` |
| Таблица разделов диска | `sudo fdisk -l /dev/sda`; `sudo parted /dev/sda print free` |
| Новая GPT + один раздел на весь диск | `sudo parted -s /dev/sdb mklabel gpt mkpart primary 1MiB 100%` |
| Перечитать таблицу разделов | `sudo partprobe /dev/sdb`; `sudo partx -u /dev/sdb` |
| Стереть старые сигнатуры с диска | `sudo wipefs -a /dev/sdb` |
| Создать ext4 под данные БД | `sudo mkfs.ext4 -L pgdata -m 1 /dev/vg_pg/lv_pgdata` |
| Создать XFS | `sudo mkfs.xfs -L pgdata /dev/vg_pg/lv_pgdata` |
| Изменить резерв root на ext4 | `sudo tune2fs -m 1 /dev/VG/LV` |
| Метка ФС | `sudo e2label /dev/X имя`; `sudo xfs_admin -L имя /dev/X` |
| Параметры ФС | `sudo tune2fs -l /dev/X`; `sudo xfs_info /точка` |
| Проверить ext4 (размонтированную) | `sudo e2fsck -f /dev/X` |
| Проверить XFS (размонтированную) | `sudo xfs_repair -n /dev/X`, затем `sudo xfs_repair /dev/X` |
| Что и куда смонтировано | `findmnt --real`; `findmnt /точка` |
| На какой ФС лежит путь | `findmnt -T /путь`; `df -hT /путь` |
| Проверить fstab | `sudo findmnt --verify --verbose` |
| Применить fstab | `sudo systemctl daemon-reload && sudo mount -a` |
| Сменить опции без размонтирования | `sudo mount -o remount,noatime /точка` |
| Кто держит ФС | `sudo lsof +f -- /точка`; `sudo fuser -vm /точка` |
| Заполнение ФС и inode | `df -hT`; `df -i` |
| Крупнейшие каталоги | `sudo du -xhd1 /путь \| sort -h` |
| Интерактивно | `sudo ncdu -x /` |
| Файлы больше 1 ГБ | `sudo find / -xdev -type f -size +1G -printf '%s\t%p\n' \| sort -n` |
| Удалённые открытые файлы | `sudo lsof -nP +L1` |
| Размер журнала systemd / очистка | `journalctl --disk-usage`; `sudo journalctl --vacuum-size=500M` |
| Сводка LVM | `sudo pvs; sudo vgs; sudo lvs -a -o +devices` |
| Диск → PV → VG → LV | `sudo pvcreate /dev/sdb && sudo vgcreate vg_pg /dev/sdb && sudo lvcreate -n lv_pgdata -l 90%VG vg_pg` |
| Увеличить LV вместе с ФС на 50 ГиБ | `sudo lvextend -r -L +50G /dev/VG/LV` |
| Отдать LV всё свободное место VG | `sudo lvextend -r -l +100%FREE /dev/VG/LV` |
| Добавить диск в VG | `sudo pvcreate /dev/sdc && sudo vgextend VG /dev/sdc` |
| Освободить диск и убрать из VG | `sudo pvmove /dev/sdb && sudo vgreduce VG /dev/sdb && sudo pvremove /dev/sdb` |
| Снапшот / откат / удаление | `sudo lvcreate -s -n snap -L 20G /dev/VG/LV`; `sudo lvconvert --merge VG/snap`; `sudo lvremove /dev/VG/snap` |
| Пересканировать размер диска ВМ | `echo 1 \| sudo tee /sys/class/block/sda/device/rescan` |
| Найти новые диски | `for h in /sys/class/scsi_host/host*/scan; do echo "- - -" \| sudo tee $h; done` |
| Расширить раздел | `sudo growpart /dev/sda 3` |
| Расширить PV | `sudo pvresize /dev/sda3` |
| Расширить ext4 / XFS вручную | `sudo resize2fs /dev/X` / `sudo xfs_growfs /точка` |
| Подкачка: состояние | `swapon --show`; `free -h` |
| Создать файл подкачки 8 ГБ | `sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
| Состояние RAID | `cat /proc/mdstat`; `sudo mdadm --detail /dev/md0` |
| TRIM вручную / по расписанию | `sudo fstrim -av`; `systemctl status fstrim.timer` |
| Здоровье NVMe / SATA | `sudo nvme smart-log /dev/nvme0`; `sudo smartctl -a /dev/sda` |
| Планировщик ввода-вывода | `cat /sys/block/sda/queue/scheduler`; `echo none \| sudo tee /sys/block/sda/queue/scheduler` |
| Read-ahead | `sudo blockdev --getra /dev/X`; `sudo blockdev --setra 4096 /dev/X`; `sudo lvchange -r 4096 VG/LV` |
| Тест случайного ввода-вывода 8k | `fio --name=t --directory=/pgdata/fio --size=8G --bs=8k --rw=randrw --rwmixread=70 --ioengine=libaio --direct=1 --iodepth=32 --numjobs=4 --time_based --runtime=120 --group_reporting` |
| Тест fsync для WAL | `sudo -u postgres /usr/lib/postgresql/18/bin/pg_test_fsync -f /pgwal/18/t.out` (каталог должен быть доступен на запись `postgres`) |
| Задержка диска | `ioping -c 10 /pgdata` |
| Нагрузка на диски сейчас | `iostat -xz 1`; `sudo iotop -oPa` |
| Смонтировать Windows-шару | `sudo mount -t cifs //host/share /mnt/x -o credentials=/etc/cifs-backup.cred,uid=postgres,gid=postgres,vers=3.1.1` |
| Смонтировать NFS | `sudo mount -t nfs -o vers=4.2 host:/export /mnt/x` |
| Применить `/etc/exports` | `sudo exportfs -ra`; `sudo exportfs -v` |
| Проверка в скрипте бэкапа | `mountpoint -q /mnt/x \|\| exit 1` |
| tmpfs | `sudo mount -t tmpfs -o size=2G,mode=1777 tmpfs /mnt/ramtmp` |
| Где `/tmp` — на диске или в ОЗУ | `findmnt /tmp` |

## Источники

Официальная документация и man-страницы:

- https://documentation.ubuntu.com/release-notes/26.04/ и https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/ — Ubuntu 26.04 LTS: дата выпуска и срок поддержки, ядро 7.0, systemd 259, PostgreSQL 18, `/tmp` на tmpfs (с 24.10), rust-coreutils и команда возврата к GNU, dracut, удаление dmraid.
- https://discourse.ubuntu.com/t/ubuntu-24-04-lts-noble-numbat-release-notes/39890 — Ubuntu 24.04: ядро 6.8 (HWE 6.17), systemd 255.4, PostgreSQL 16.
- https://discourse.ubuntu.com/t/oracular-oriole-release-notes/44878 — Ubuntu 24.10: появление `tmp.mount` по умолчанию.
- https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html — раскладки `lvm`/`direct`/`zfs`, `sizing-policy` (`scaled`/`all`) и пороги размера корневого LV.
- https://discourse.ubuntu.com/t/how-is-the-size-of-the-lvm-container-decided/24608 — обсуждение кода Subiquity, выбирающего размер `ubuntu-lv`.
- https://ubuntu.com/server/docs/explanation/storage/about-lvm/ и https://ubuntu.com/server/docs/how-to/storage/manage-logical-volumes/ — понятия LVM, создание/расширение/перенос томов, снапшоты и `lvconvert --merge`.
- https://ubuntu.com/server/docs/how-to/networking/install-nfs/ — NFS: пакеты `nfs-kernel-server`/`nfs-common`, `/etc/exports`, `exportfs`, `/etc/nfs.conf`.
- https://ubuntu.com/server/docs/how-to/samba/mount-cifs-shares-permanently/ — CIFS: `cifs-utils`, файл credentials, строки `fstab`, диагностика `mount error(13)`.
- https://curtin.readthedocs.io/en/latest/topics/config.html и https://raw.githubusercontent.com/canonical/curtin/master/curtin/swap.py — файл подкачки `/swap.img`, `maxsize` 8 ГБ, эвристика размера.
- https://manpages.ubuntu.com/manpages/noble/en/man8/lsblk.8.html, …/findmnt.8.html, …/mount.8.html, …/man5/fstab.5.html, …/man5/systemd.mount.5.html, …/swapon.8.html, …/fstrim.8.html, …/wipefs.8.html, …/blockdev.8.html — util-linux 2.39.3 и systemd 255: опции и формулировки.
- https://manpages.ubuntu.com/manpages/noble/en/man8/mkfs.ext4.8.html, …/tune2fs.8.html, …/e2fsck.8.html, …/resize2fs.8.html, …/man5/ext4.5.html; https://manpages.ubuntu.com/manpages/resolute/en/man8/mke2fs.8.html — e2fsprogs 1.47.0 (24.04) и 1.47.2 (26.04).
- https://manpages.ubuntu.com/manpages/noble/en/man8/mkfs.xfs.8.html, …/xfs_admin.8.html, …/xfs_repair.8.html; https://manpages.ubuntu.com/manpages/resolute/en/man8/mkfs.xfs.8.html — xfsprogs 6.6.0 (24.04) и 6.18.0 (26.04), умолчания формата.
- https://manpages.ubuntu.com/manpages/noble/en/man8/lvextend.8.html, …/lvcreate.8.html, …/pvresize.8.html, …/pvmove.8.html, …/vgreduce.8.html; https://manpages.ubuntu.com/manpages/resolute/en/man8/lvextend.8.html, …/lvreduce.8.html — lvm2 2.03.16 (24.04) и 2.03.31 (26.04): `-r`, `--fs`, `%FREE`, примеры.
- https://manpages.ubuntu.com/manpages/noble/en/man1/growpart.1.html — `growpart` (cloud-guest-utils 0.33): синтаксис, `--dry-run`, `--fudge`.
- https://manpages.ubuntu.com/manpages/noble/en/man8/mdadm.8.html, …/smartctl.8.html, …/hdparm.8.html, …/man1/nvme.1.html, …/man1/fio.1.html, …/man1/ioping.1.html, …/man1/sshfs.1.html, …/man8/mount.cifs.8.html, …/man5/exports.5.html — соответствующие утилиты (mdadm, smartmontools 7.4, nvme-cli 2.8, fio 3.36, ioping 1.3, sshfs 3.7.3, cifs-utils 7.0, nfs-utils).
- https://docs.kernel.org/block/switching-sched.html и https://raw.githubusercontent.com/torvalds/linux/master/block/elevator.c — просмотр и переключение планировщиков; выбор планировщика по умолчанию.
- https://www.debian.org/releases/trixie/release-notes/issues.en.html — `/tmp` на tmpfs: предел 50 % ОЗУ, `systemctl edit tmp.mount`, `systemctl mask tmp.mount`; очистка `/tmp` (10 дней) и `/var/tmp` (30 дней).
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/best-practices-for-running-linux-on-hyper-v — Linux на Hyper-V: `mkfs.ext4 -G 4096`, VHDX `BlockSizeBytes 1MB`, планировщик `none`, предупреждение об изменении размера VHDX и GPT.
- https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_storage_devices/getting-started-with-swap_managing-storage-devices — таблица рекомендуемого размера подкачки, операции с подкачкой на LVM и в файле.

PostgreSQL и Postgres Pro:

- https://www.postgresql.org/support/versioning/ — поддерживаемые версии и даты окончания поддержки.
- https://www.postgresql.org/docs/current/creating-cluster.html — подкаталог вместо точки монтирования; «any file system with POSIX semantics»; требования к NFS.
- https://www.postgresql.org/docs/current/backup-file.html — согласованные снапшоты ФС, требование одновременности, `CHECKPOINT`.
- https://www.postgresql.org/docs/current/wal-reliability.html — кэш записи дисков, `hdparm -I`/`-W 0`, `sdparm`, BBU, барьеры, контрольные суммы.
- https://www.postgresql.org/docs/current/pgtestfsync.html и https://www.postgresql.org/docs/current/runtime-config-wal.html — `pg_test_fsync`; `wal_sync_method` (в Linux — `fdatasync`), `fsync`, `synchronous_commit`.
- https://www.postgresql.org/docs/current/manage-ag-tablespaces.html — табличные пространства, `temp_tablespaces`, предупреждение о RAM-диске.
- https://www.postgresql.org/docs/18/runtime-config-resource.html — `io_method`, `io_workers`, `effective_io_concurrency`, `file_copy_method`, `temp_file_limit`.
- https://postgrespro.ru/docs/postgresql/17/kernel-resources — overcommit, OOM killer и подкачка, огромные страницы.
- https://postgrespro.ru/docs/postgrespro/17/config-one-c, …/one-c-basic-server-requirements, …/one-c-configuring-server — Postgres Pro для 1С: «RAID 0–1 или SSD», подкачка разделяемой памяти, `temp_tablespaces`, `random_page_cost`, `effective_io_concurrency`, `pg_stat_tmp` на tmpfs, параметры WAL и контрольных точек.

1С:

- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/apparatnye-trebovaniya/ — минимальные требования к серверу 1С (ОЗУ от 2 ГБ, диск от 40 ГБ).
- https://v8.1c.ru/tekhnologii/systemnye-trebovaniya-1s-predpriyatiya-8/subd/ — поддерживаемые версии Postgres Pro и PostgreSQL с патчем 1С.
- https://its.1c.ru/db/content/metod8dev/src/admins/linux/i8101736.htm и https://1c-dn.com/library/how_to_change_temporary_directory_of_1c_enterprise_server/ — временный каталог сервера 1С в Linux: `TMPDIR`, риск автоочистки `/tmp`.
- https://its.1c.ru/db/content/metod8dev/src/developers/scalability/administration/postgresql/i8105825.htm — «Настройки PostgreSQL для работы с 1С:Предприятием» (старая статья для 8.1/PostgreSQL 8.2; о `fsync` и надёжности дисковой подсистемы; прочитана частично из-за проблем с кодировкой).

Практика сообщества и тесты:

- https://www.enterprisedb.com/blog/tuning-debian-ubuntu-postgresql — EDB: `noatime`, `vm.swappiness = 10`, параметры `vm.dirty_*`, отключение THP, расчёт огромных страниц.
- https://www.phoronix.com/review/linux-615-filesystems/5 и https://www.phoronix.com/review/linux-612-linux-70-xfs-ext4/7 — сравнение ext4 и XFS в тестах PostgreSQL на ядрах 6.15 и 6.12–7.0 (известно по поисковой выдаче; при вычитке обе страницы ответили HTTP 403 — не подтверждено).
- https://www.enterprisedb.com/blog/postgres-vs-file-systems-performance-comparison — Томаш Вондра, 10.10.2022: ext4/XFS против ZFS/Btrfs под PostgreSQL (при вычитке прочитано: ядро 5.17.11, pgbench, ~30 тыс. tps у ext4/XFS против 4–6,5 тыс. у ZFS/Btrfs на NVMe при scale 10000).
- https://access.redhat.com/solutions/5427 — Red Hat о планировщике в виртуальных машинах (статья закрыта подпиской, не читалась; вместо неё использована открытая документация RHEL 9, см. ниже).
- https://infostart.ru/1c/articles/2742324/ и https://infostart.ru/public/2790159/ — чек-листы настройки Linux/PostgreSQL под 1С 8.5: планировщик `none`/`mq-deadline` для NVMe, отдельные диски под журналы и временные данные, `vm.swappiness` 1–10 (по поисковой выдаче; сами страницы ответили HTTP 429).
- https://forum.infostart.ru/forum71/topic344307/ — перенос временного каталога сервера 1С на Ubuntu и побочные эффекты (по поисковой выдаче).

Не удалось прочитать в этой сессии (закрыто, недоступно или исчерпан лимит поиска): страницы ИТС о настройке PostgreSQL и Linux для 1С (см. отчёт), wiki.ubuntu.com (SwapFaq, IOSchedulers), man7.org, freedesktop.org. Утверждения, опирающиеся только на память автора, помечены в тексте знаком ⚠.

Дополнительно использовано при независимой вычитке 2026-10-10 (веб-поиск был недоступен — исчерпан лимит; читались только прямые адреса первоисточников):

- https://www.postgresql.org/support/versioning/ и https://www.postgresql.org/ — текущие минорные версии 18.6 / 17.11 / 16.15 / 15.19 / 14.24 (выпуск 2026-08-13), PostgreSQL 19 Beta 4 от 2026-09-24, окончание поддержки 14 — 12.11.2026.
- https://ubuntu.com/kernel/lifecycle и https://releases.ubuntu.com/24.04/ — ядра по выпускам (22.04.5 → 6.8; 24.04.4 → 6.17; 24.04.5 → 7.0; 26.04 → 7.0), образ 24.04.5 от 2026-09-09.
- https://manpages.ubuntu.com/manpages/jammy/en/man8/lsblk.8.html, …/jammy/en/man8/lvextend.8.html, …/jammy/en/man8/mkfs.xfs.8.html, …/jammy/en/man8/mke2fs.8.html, …/jammy/en/man1/systemctl.1.html, …/jammy/en/man8/parted.8.html, …/jammy/en/man8/mdadm.8.html — версии пакетов 22.04 (util-linux 2.37.2, lvm2 2.03.11, xfsprogs 5.13.0, e2fsprogs 1.46.5, systemd 249.11, parted 3.4, mdadm 4.2); отсутствие `lsblk -N` и `parted --fix` в 22.04; умолчания `mkfs.xfs` 5.13.
- https://manpages.ubuntu.com/manpages/noble/en/man8/mkfs.xfs.8.html и …/resolute/en/man8/mkfs.xfs.8.html — умолчания `rmapbt`, `nrext64`, `bigtime`, `inobtcount`, минимум 300 МБ.
- https://manpages.ubuntu.com/manpages/noble/en/man8/xfs_admin.8.html, …/noble/en/man8/parted.8.html (parted 3.6, `-f/--fix`), …/noble/en/man8/mdadm.8.html (mdadm 4.3) и …/resolute/en/man8/mdadm.8.html (mdadm 4.5: описание `--bitmap=`), …/noble/en/man8/fstrim.8.html, …/noble/en/man8/sulogin.8.html (`--force` и заблокированный root), …/noble/en/man8/e2scrub.8.html, …/noble/en/man8/e2scrub_all.8.html, …/noble/en/man8/fsfreeze.8.html, …/noble/en/man8/mount.cifs.8.html, …/noble/en/man1/growpart.1.html (`--fudge` 20480 секторов).
- https://manpages.ubuntu.com/manpages/resolute/en/man8/lvreduce.8.html (lvm2 2.03.31: `--fs checksize|resize|resize_fsadm|ignore`), …/resolute/en/man8/mkswap.8.html (util-linux 2.41.3: `-F/--file`, `-s/--size`), …/resolute/en/man8/lsblk.8.html, …/resolute/en/man8/update-initramfs.8.html (поставляется пакетом dracut 110), …/resolute/en/man5/systemd.mount.5.html (systemd 259.5).
- https://raw.githubusercontent.com/lvmteam/lvm2/main/tools/lvresize.c — умолчание `checksize` при отсутствии `--fs` и `--resizefs`.
- https://raw.githubusercontent.com/canonical/cloud-utils/main/bin/growpart — `FUDGE` по умолчанию 1 МиБ, временный каталог через `mktemp -d "${TMPDIR:-/tmp}/…"`, перенос резервной GPT (`sgdisk --move-second-header`).
- https://raw.githubusercontent.com/canonical/curtin/master/curtin/swap.py — полный алгоритм `suggested_swapsize` (в том числе возврат 0 и значение для ОЗУ свыше 64 ГБ), `fallocate` или `dd` в зависимости от ФС.
- https://raw.githubusercontent.com/torvalds/linux/master/block/elevator.c — сообщение о недействующем параметре `elevator=`, выбор планировщика по умолчанию.
- https://raw.githubusercontent.com/systemd/systemd/v255/src/sulogin-shell/sulogin-shell.c — `SYSTEMD_SULOGIN_FORCE` (переменная окружения и параметр командной строки ядра).
- https://raw.githubusercontent.com/util-linux/util-linux/master/login-utils/sulogin.c — поведение `sulogin` при заблокированном root без `--force` и текст сообщения «Cannot open access to console, the root account is locked».
- https://manpages.ubuntu.com/manpages/noble/en/man8/xfs_io.8.html — команды `label` и `fsuuid` для смонтированной XFS.
- https://raw.githubusercontent.com/systemd/systemd/v259/units/tmp.mount и https://raw.githubusercontent.com/systemd/systemd/v259/tmpfiles.d/tmp.conf — опции tmpfs для `/tmp` (`size=50%`, `nr_inodes=1m`), сроки очистки 10 и 30 дней.
- https://www.kernel.org/pub/linux/utils/util-linux/v2.38/v2.38-ReleaseNotes, …/v2.39/v2.39-ReleaseNotes, …/v2.40/v2.40-ReleaseNotes — в каких версиях появились `X-fstrim.notrim`, `mount --mkdir`, `lsblk -N/-v`, `mkswap --file`.
- https://cgit.git.savannah.gnu.org/cgit/parted.git/plain/NEWS — `--fix` добавлен в 3.4.64 (альфа будущей 3.5).
- https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/dn282286(v=ws.11) — «Online Virtual Hard Disk Resizing Overview»: только VHDX и только SCSI-контроллер.
- https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/supported-ubuntu-virtual-machines-on-hyper-v — таблица функций для Ubuntu 16.04–24.04 (VHDX resize, TRIM, live backup и примечания к нему).
- https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/monitoring_and_managing_system_status_and_performance/setting-the-disk-scheduler_monitoring-and-managing-system-status-and-performance — таблица «Disk schedulers for different use cases» (виртуальный гость: `mq-deadline`, при многоочередном HBA — `none`).
- https://postgrespro.ru/docs/postgrespro/17/one-c-basic-server-requirements, …/one-c-configuring-server, …/binary-installation-on-linux — дословные формулировки K.2/K.3 и схема путей `/opt/pgpro/std-17`, `/var/lib/pgpro/std-17/data`.
- https://1c-dn.com/library/how_to_change_temporary_directory_of_1c_enterprise_server/ — перечитано: `/tmp` по умолчанию, `TMPDIR` в `.bash_profile`, `tmpwatch -x`.
- Конспекты документации платформы 8.3.27 в этой базе знаний: `kb/its-docs/cs-gl04-zapusk-komponentov.md` (юнит `srv1cv8-A.B.C.D@.service`, экземпляр `default`, `systemctl edit` + `Environment=`, перечень `SRV1CV8_*` и умолчание `SRV1CV8_DATA`), `kb/its-docs/cs-gl01-trebovaniya.md` (требования к серверу, права на каталоги), `kb/its-docs/adm-pr03-sluzhebnye-fajly-p1.md` (`1cv8wsrv.lst`, `1CV8Clst.lst`).

Не открылись при вычитке: исходный код Subiquity (GitHub и git.launchpad.net — 404/ошибка), исходники пакета systemd Ubuntu на Launchpad, git.kernel.org (xfsprogs, 403), phoronix.com (403), страница Postgres Pro для 1С (404), kb.1ci.com (перенаправление на support.1ci.com без содержимого руководства), страницы ИТС (кириллица в ответе искажена — читаются только латинские фрагменты).
