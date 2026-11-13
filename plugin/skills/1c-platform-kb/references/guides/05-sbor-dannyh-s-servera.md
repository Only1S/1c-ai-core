# Сбор данных с сервера: что нужно, чтобы закрыть оставшиеся пометки «⚠»

> Область: одноразовый сценарий, который собирает с рабочего или тестового сервера 1С + PostgreSQL сведения, недоступные из документации | Актуальность: 2026-10-10
>
> **Статус:** сценарий написан по документации и статьям базы знаний, на сервере не запускался. Он только читает состояние и ничего не меняет.

## Зачем

После сверки с документацией в статьях базы знаний остались пометки «⚠», которые закрываются только фактом с живого сервера. Почти все они сводятся к нескольким вопросам:

| Что неизвестно | Чем закрывается | Какие статьи затрагивает |
|---|---|---|
| Параметры утилиты `rac` (документация их не перечисляет) | `rac help` и `rac help <режим>` | `1c/03`, `1c/04`, `1c/06`, `1c/08`, `1c/10` |
| Имена полей в выводе `rac` | `rac … list` на работающем кластере | `1c/03`, `1c/07` |
| Текст поставляемых юнитов systemd и имена переменных `SRV1CV8_*` | `systemctl cat` | `1c/02`, `1c/03`, `1c/07` |
| Какие каталоги реально используются (`conf`, журнал по умолчанию, `cacert*.pem`, лицензии) | `ls`, `find` | `1c/07`, `1c/08`, `1c/09` |
| Параметры `ibcmd`, `ras`, `webinst`, установщика | встроенная справка | `1c/02`, `1c/05`, `1c/06` |
| Как сервер 1С выглядит со стороны PostgreSQL (`application_name`, расширения, локаль, права) | запросы к `pg_stat_activity` и каталогу | `postgresql/01`, `postgresql/03`, `postgresql/06` |
| Раскладка файлов и юнит сборки PostgreSQL | `systemctl cat`, `SHOW` | `postgresql/01`, `postgresql/03` |
| Режим Transparent Huge Pages, лимиты служб | `/sys`, `/proc` | `postgresql/02`, `linux/09` |

## Сценарий

Сохраните как `collect-1c-info.sh`, задайте в начале версию платформы и имя службы PostgreSQL, запустите от `root`. Результат — один текстовый файл в `/tmp`.

```bash
#!/usr/bin/env bash
# Собирает справочные сведения о сервере 1С и PostgreSQL. Ничего не изменяет.
set -u
V=8.3.27.2074                      # версия платформы на сервере
PGSVC=postgrespro-1c-17            # служба PostgreSQL (для сборки 1С: postgresql@17-main)
DB=""                              # имя одной базы 1С в PostgreSQL (необязательно)

B=/opt/1cv8/x86_64/$V
OUT=/tmp/1c-info-$(hostname -s)-$(date +%F).txt
sec() { printf '\n########## %s\n' "$*"; }
run() { printf '\n$ %s\n' "$*"; "$@" 2>&1 | head -n "${LIMIT:-400}"; }
sh_() { printf '\n$ %s\n' "$1"; bash -c "$1" 2>&1 | head -n "${LIMIT:-400}"; }

{
sec "ОС"
run uname -r
sh_ 'grep -E "^(PRETTY_NAME|VERSION_ID)=" /etc/os-release'
run hostname -f
sh_ 'getent hosts "$(hostname)"'
sh_ 'locale -a | grep -i -E "ru_RU|en_US"'
sh_ 'cat /sys/kernel/mm/transparent_hugepage/enabled'
run timedatectl

sec "Каталоги платформы"
sh_ 'ls -la /opt/1cv8 /opt/1cv8/conf /opt/1cv8/common 2>&1'
sh_ "ls -la $B | head -80"
sh_ "ls -la $B/conf 2>&1"
sh_ 'find /opt/1cv8 -maxdepth 3 -name "cacert*.pem" -exec ls -l {} +'
sh_ 'find /opt/1cv8 -maxdepth 3 -name "*.service" -exec ls -l {} +'
sh_ 'ls -ld /var/1C/licenses; ls -l /var/1C/licenses | sed "s/[0-9]\{6,\}/<номер>/g"'
sh_ 'H=$(getent passwd usr1cv8 | cut -d: -f6); ls -ld "$H/.1cv8/logs" "$H/.1cv8/1C/1cv8/logs" "$H/.1cv8/1C/1cv8/conf" 2>&1; ls "$H/.1cv8/1C/1cv8" 2>&1 | head -30'

sec "Службы и процессы 1С"
sh_ "systemctl cat 'srv1cv8-$V@default' 2>&1"
sh_ "systemctl cat 'ras-$V' 2>&1"
sh_ 'ps -eo user,pid,args | grep -E "[r]agent|[r]mngr|[r]phost|[/]ras |[d]bgs|[c]rserver" | cut -c1-400'
sh_ 'ss -tlnp | grep -E "ragent|rmngr|rphost|ras|dbgs|apache|httpd|postgres"'
sh_ 'P=$(pgrep -o ragent); [ -n "$P" ] && grep -E "open files|processes|core file" /proc/$P/limits'

sec "Встроенная справка утилит"
LIMIT=120 run "$B/ras" help
LIMIT=120 run "$B/rac" help
for M in agent cluster manager server process service infobase connection session lock rule profile counter limit service-setting binary-data-storage; do
  LIMIT=260 run "$B/rac" help "$M"
done
LIMIT=120 run "$B/ibcmd" help
for M in infobase server session lock config extension; do LIMIT=200 run "$B/ibcmd" help "$M"; done
LIMIT=60 sh_ "$B/webinst 2>&1"
LIMIT=80 sh_ "ls $B/setup-* $B/uninstaller-* 2>&1"

sec "Кластер 1С (имена полей; значения стоит просмотреть перед отправкой)"
CL=$("$B/rac" cluster list 2>/dev/null | awk '/^cluster/{print $3; exit}')
printf 'cluster=%s\n' "${CL:-не получен: запущен ли ras и не заданы ли администраторы кластера?}"
if [ -n "${CL:-}" ]; then
  run "$B/rac" cluster info --cluster="$CL"
  run "$B/rac" server list --cluster="$CL"
  run "$B/rac" process list --cluster="$CL"
  run "$B/rac" service list --cluster="$CL"
  LIMIT=60 sh_ "$B/rac session list --cluster=$CL | sed -E 's/^(user-name|host|app-id|client-ip)( *: ).*/\1\2<скрыто>/' "
  LIMIT=60 sh_ "$B/rac connection list --cluster=$CL | sed -E 's/^(host)( *: ).*/\1\2<скрыто>/' "
fi

sec "PostgreSQL"
sh_ "systemctl cat '$PGSVC' 2>&1"
PSQL="sudo -u postgres psql -X -At"
sh_ "$PSQL -c 'select version()' -c 'show data_directory' -c 'show config_file' -c 'show hba_file' -c 'show unix_socket_directories' -c 'show log_directory' -c 'show logging_collector'"
sh_ "$PSQL -F ' | ' -c \"select name, setting, coalesce(unit,''), source from pg_settings where source not in ('default','override') order by 1\""
sh_ "$PSQL -F ' | ' -c \"select datname, pg_encoding_to_char(encoding), datcollate, datctype, datlocprovider from pg_database order by 1\""
sh_ "$PSQL -F ' | ' -c \"select type, database, user_name, address, auth_method from pg_hba_file_rules\""
sh_ "$PSQL -F ' | ' -c \"select application_name, count(*) from pg_stat_activity group by 1 order by 2 desc\""
sh_ "$PSQL -F ' | ' -c \"select name, default_version, installed_version from pg_available_extensions where name in ('mchar','fulleq','fasttrun','online_analyze','plantuner','pg_stat_statements','dbcopies_decoding','uuid-ossp') order by 1\""
sh_ "$PSQL -c \"select name, context from pg_settings where name in ('enable_temp_memory_catalog','enable_temp_rd_buffers','enable_sorted_merge_join','online_analyze.enable','plantuner.fix_empty_table')\""
if [ -n "$DB" ]; then
  sh_ "$PSQL -d '$DB' -F ' | ' -c \"select extname, extversion from pg_extension order by 1\""
  sh_ "$PSQL -d '$DB' -F ' | ' -c \"select count(*) filter (where relkind='r') tables, count(*) filter (where relkind='i') indexes from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'\""
  sh_ "$PSQL -d '$DB' -F ' | ' -c \"select tablename from pg_tables where schemaname='public' and tablename !~ '^_' order by 1 limit 40\""
  sh_ "$PSQL -d '$DB' -F ' | ' -c \"select locktype, mode, count(*) from pg_locks group by 1,2 order by 3 desc limit 15\""
fi
} > "$OUT" 2>&1

echo "Готово: $OUT ($(wc -l < "$OUT") строк). Просмотрите файл перед отправкой."
```

## Как пользоваться

1. Запуск: `sudo bash collect-1c-info.sh`. Если в кластере заданы администраторы, раздел «Кластер 1С» останется пустым — это не ошибка; справка утилит соберётся всё равно.
2. **Просмотрите файл перед отправкой.** Пароли сценарий не читает, имена пользователей и адреса клиентов в списках сеансов и соединений заменяются на `<скрыто>`, номера в именах файлов лицензий — на `<номер>`. Имя хоста, адреса из `pg_hba.conf` и имена баз в файле остаются — при необходимости замените их вручную.
3. Пришлите файл ассистенту: по нему закрываются пометки о параметрах `rac`, тексте юнитов, каталогах и поведении сборки PostgreSQL, а руководства `01`–`03` сверяются с фактом.

## Что сценарий не покрывает

- Содержимое документации тестовой версии 8.5.4 — нужна подписка с доступом к ней.
- Поведение под нагрузкой, сообщения об ошибках, которые появляются только при сбое.
- Сторонние продукты (Patroni, PgBouncer, pg_probackup, КриптоПро и другие): их параметры проверяются по документации производителя.
