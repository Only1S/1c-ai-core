# База знаний: Linux Ubuntu, 1С на Linux и на Windows, PostgreSQL для 1С, Redmine, NetBox, наблюдаемость (GlitchTip, Loki, Grafana) — оглавление

> Снимок для скилла `1c-platform-kb`: пути — от каталога `references/`. Разделы Redmine, NetBox и стенда наблюдаемости (`guides/08`, `guides/09`) в снимок не входят — ссылки на них ведут в базу-источник.


> Обновлено 2026-10-20. Как пользоваться: найти тему в маршрутизаторе или по заголовкам ниже → открыть файл → искать Grep по ключевому слову и читать нужный раздел частями (статьи большие).

## Состояние проверки

- **Проверены независимым рецензентом по первоисточникам:** все статьи `linux/`; `1c/01`, `1c/02`, `1c/04`, `1c/05`; `postgresql/01`, `postgresql/02`, `postgresql/03`.
- **Независимым рецензентом не проверены:** `1c/03`, `1c/06`–`1c/10` (отметка стоит в начале каждой). Для них выполнены программные и точечные сверки, перечисленные ниже; построчно эти статьи никто не перечитывал.
- **`postgresql/04`–`09` проверены независимой сверкой 19.10.2026** (веер из 6 агентов с согласия пользователя, около 2,5 млн токенов). Каждая статья построчно сверена:
  - с документацией PostgreSQL 14–18 и исходным кодом нужных веток;
  - с примечаниями к выпускам;
  - с документацией «PostgreSQL для 1С» 16 и индексами пакетов;
  - с документацией сторонних инструментов.
  
  Проверено около 1330 утверждений, исправлено 79 ошибок, закрыто 28 пометок «⚠». Отметка в начале каждой статьи заменена.

  Главное для пользователя:
  - ветки 14–16 сборки «PostgreSQL для 1С» собираются только для Ubuntu 22.04 и 24.04;
  - контрольные суммы данных включает `pg-setup initdb` и в ветке 16;
  - в бесплатной сборке 16.14 нет `pg_hint_plan`, `pg_wait_sampling`, `pgpro_pwr`, `ptrack`;
  - открытый `pg_probackup` не работает с сервером, где есть `pgpro_edition()`;
  - `auto_dump` сборки Postgres Pro имеет другие параметры, чем в методичках ИТС;
  - тексты ошибок локали в 16+ другие;
  - формула ёмкости таблицы блокировок уточнена;
  - в PostgreSQL 19 (RC 1 от 15.10.2026) `standard_conforming_strings` всегда `on` — несовместимо с требованием 1С;
  - с 16.15 модули логического декодирования ограничены `output_plugin_libraries` — это касается копий БД (`dbcopies_decoding`).
  
  Замечания агентов к другим файлам внесены вручную: `postgresql/01`–`03`, `1c/06`, `1c/09`, `1c/10`, `guides/02`, `guides/07`, `its-metod/razmeshchenie-*` (в самих статьях ИТС 1798 и 1591 расходятся имена таблиц регистров бухгалтерии).
- **Разделы 20.10.2026:** `mssql/` (8 статей), `apache/` (4), `iis/` (3) — написаны и проверены независимой сверкой веерами «пишущий + проверяющий» с согласия пользователя (итоги — в начале каждого раздела ниже); замечания проверяющих к другим файлам внесены вручную (для `iis/` — в `1c-windows/03`: TLS по умолчанию в Windows Server 2025, `DisabledByDefault`, `*-IISSiteBinding` нет на Server 2016, расписание переработки пула, сжатие, HTTPERR). `kafka/` и `rabbitmq/` (по 3 статьи) написаны **без веера** по указанию пользователя экономить — независимой сверки не было, умолчания и ключи настроек точечно сверены с исходным кодом (Kafka 4.4, схема `rabbit.schema` 4.4.0).
- **Сверка имён (все статьи `1c/` и `postgresql/`):** ключи утилит 1С, имена служебных файлов, переменных `SRV1CV8_*`, событий техжурнала, элементов XML — с полными текстами документации ИТС 8.3.27 и 8.5.1; параметры PostgreSQL, имена `pg_*`, ключи утилит — с документацией PostgreSQL 18. Выдуманных имён не найдено. В `1c/07` помечено: события `TTS`, `TTSADM`, `UDBCFGLOCK`, `UDBCFGTRAN` в документации 8.3.27/8.5.1 отсутствуют (относятся к 8.5.4).
- **Смысловые сверки PostgreSQL (`postgresql/04`–`09`):** значения параметров по умолчанию — с образцом `postgresql.conf` версии 18; утверждения «появилось или удалено в версии N» — с замечаниями к выпускам 12–18; имена колонок в SQL-запросах — с документацией. Расхождений не найдено. Официальные значения ИТС в `postgresql/02` и в руководстве `guides/01` совпадают со статьёй ИТС (редакция 19.06.2025).
- **Смысловые сверки 1С:** свойства кластера и рабочих серверов в `1c/03` (умолчания, пороги памяти 80 % / 95 % / 10 %, интервал 300 с, порты), параметры `conf.cfg` в `1c/08`, единицы длительности в `1c/07` — совпадают с документацией.
- **Разбор пометок «⚠» (10–11.10.2026):** просмотрены все пометки во всех трёх разделах — `linux/`, `1c/`, `postgresql/`. Закрыто или уточнено 252 пометки: в начале такой пометки теперь стоит «Уточнено», «Подтверждено» или «сверено» с датой и источником. Источники: полные тексты документации ИТС 8.3.27 (в том числе «Руководство разработчика», конспекты — `its-docs/dev-*.md`), методические статьи ИТС, открытая документация сборки «PostgreSQL для 1С» (`repo.postgrespro.ru/doc/pg1c/`, конспект — `guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`), файлы её репозитория и содержимое пакета `postgrespro-1c-16-server` 16.14 (служба systemd, `pg-setup`, пресеты `pgpro_tune`, скрипты установки), документация и исходный код PostgreSQL 12–18, исходные тексты и файл NEWS systemd, исходный код Apache и ядра Linux, правки пакетов Debian (salsa.debian.org), журналы изменений и списки файлов пакетов Ubuntu, документация сторонних проектов (pg_auto_failover, WAL-G, pgBackRest, Barman, pgcenter).
- **Найденные и исправленные фактические ошибки:** (1) `1c/05` — сеансы веб-сервисов, HTTP-сервисов и OData клиентских лицензий не требуют (документация, разд. 10.3.4.8); (2) `linux/09` — сообщение `invalid LC_COLLATE locale name` появилось в PostgreSQL 16, а не 15; (3) `1c/07` — умолчания `ProcessSizeMax` и `ExternalSizeMax` в systemd выросли с 2G до 32G в версии 253, а не 251; (4) `linux/08` — адрес `127.0.0.54` у systemd-resolved появился в версии 250, а не 251; (5) `linux/01` — срок очистки `/tmp` «30 дней» действует в Ubuntu 24.04, но не в 22.04 (там `/tmp` очищается только при загрузке).
- **Какие пометки «⚠» остались и почему:** открытых вопросов 1663 на 20.10.2026 (`iis/` — 184, `kafka/` — 37, `rabbitmq/` — 35, `mssql/` — 386, `apache/` — 87; `linux/` — 212, `1c/` — 269, `postgresql/` — 135, `redmine/` — 55, `netbox/` — 31, `1c-windows/` — 232; до разделов `iis/`, `kafka/`, `rabbitmq/` было 1412; на 16.10.2026 без `1c-windows/` было 721; на 11.10.2026 по первым трём разделам было 638 — две пометки закрыла проверка совместимости 15.10.2026); полный список с номерами строк — в `guides/06-otkrytye-voprosy.md` (пересобран 19.10.2026; `observability/` и `guides/` в него не входят). Ниже — разбивка по первым трём разделам на 11.10.2026. Группы: (1) около 210 проверяются только на живом сервере — параметры и поля `rac`, текст поставляемых юнитов, фактические каталоги, поведение сборки PostgreSQL; для них есть сценарий `guides/05-sbor-dannyh-s-servera.md`; (2) около 45 относятся к версии 8.5.4 и новее — документация 8.5.4 по подписке недоступна; (3) около 65 касаются сторонних продуктов (Postgres Pro, Patroni, КриптоПро, HASP, гипервизоры), по которым открытого первоисточника не нашлось; (4) около 320 — практика сообщества, оценки и тексты сообщений, которых нет ни в одном первоисточнике. Ещё 107 вхождений знака — служебные: пояснения в начале статей и сводки «что осталось проверить».
- **В начале каждой статьи `1c/` и `postgresql/`** стоит блок «Официальные тексты по теме» со ссылками на конспекты ИТС: статьи писались до получения доступа к закрытой документации, при расхождении правы конспекты.
- **Руководства `guides/`** на живом сервере не прогонялись.
- **Пробелы:** покрытие тем проверено по ключевым словам; дописаны `guides/03` (СУБД на отдельном хосте, второй рабочий сервер), `guides/04` («1С:Сервер взаимодействия», по статьям ИТС 2023–2026 годов) и разделы 9.3–9.4 в `1c/10` («1С:Центр администрирования» как официальный инструмент автоматизации; Kubernetes).
- Конспекты ИТС составлены по полным текстам источников; каждый сверен с источником выборочно.
- **«Руководство разработчика» 8.3.27 (11.10.2026):** законспектированы все 39 глав и 13 приложений — 20 файлов `its-docs/dev-*.md` плюс прежняя выборка. Книга большая (около 5 млн знаков), поэтому читалась в три уровня: **полностью** — главы и разделы, значимые для администратора (главы 1, 9, 19, 20, 22, 23, 24, 26, 32, 33, 37, 38, приложения 1, 2, 5, 6, 8, 10, 13 и отмеченные разделы глав 2, 4, 5, 15, 17, 21, 25, 29, 30, 31, 34, приложения 7); **обзорно** (заголовки, вводные абзацы, все примечания, абзацы по ключевым словам) — главы по разработке (3, 6, 7, 8, 10–14, 16, 18, 27, 28, 35, 36, 39) и остальные разделы; раздел 34.1 и раздел 7.9 приложения 7 не конспектировались. Точный состав прочитанного указан в начале каждого конспекта в строке «Как читалось». По обзорно прочитанным разделам ответ на детальный вопрос нужно сверять с текстом главы на ИТС.
- **Redmine (15.10.2026):** раздел `redmine/` (6 статей) написан по официальной вики redmine.org (руководства по установке, администрированию и для пользователей, REST API, безопасность, журналы изменений 6.0–7.0 — всего около 100 страниц через JSON-интерфейс вики) и по исходному коду ветки 7.0-stable; спорные места вики (устаревшие умолчания, путь тем, вкладки настроек, адрес `rails server`) сверены с кодом Redmine 7.0 и Rails 8.1.4. Независимым рецензентом не проверялся, на живом сервере не прогонялся; непроверенное помечено «⚠» (54 открытых вопроса и 6 строк-легенд в шапках; внесены в `guides/06` 15.10.2026). Статья `redmine/06` — Redmine как задачник стенда наблюдаемости вместо OpenProject.
- **NetBox (15.10.2026):** раздел `netbox/` (6 статей) — по просьбе пользователя «внедрить NetBox»; 16.10.2026 пользователь сузил задачу до учёта оборудования и схем подключений — статья `netbox/06`. Написан по документации NetBox 4.7.3 (`docs/` репозитория `netbox-community/netbox`, метка v4.7.3), по исходному коду 4.7.3 (настройки, задания обслуживания, «перепись» и Copilot, отправка вебхуков и повторы, сериализаторы и фильтры API), по репозиторию и вики netbox-docker 5.1.1, Docker Hub и packages.ubuntu.com. Найдено важное: 4.7 требует PostgreSQL 15+ с `ltree` и Redis 6+; по умолчанию NetBox обращается в интернет («перепись» раз в сутки, Copilot, каталог плагинов) — в закрытом контуре `ISOLATED_DEPLOYMENT = True`; повторов вебхуков по умолчанию нет; неизвестный параметр фильтра API молча игнорируется; дампы 4.7.0 восстанавливались без триггеров (`--exit-on-error` обязателен); файлы `env/*.env` netbox-docker содержат общеизвестные пароли. В стенд NetBox добавлен профилем `netbox` (порт 8090, свой PostgreSQL 18 и Valkey), мост дополнен приёмом вебхуков NetBox → задача Redmine (проверено офлайн с заглушками). Независимым рецензентом не проверялся, ничего не запускалось; 31 открытая пометка «⚠» (плюс 2 строки-легенды в шапках) — внесены в `guides/06`.
- **Совместимость (15.10.2026):** `guides/09` — проверка совместимости всех инструментов (10 агентов с согласия пользователя): найдено ❌ 16, ⚠️ 56; 53 ошибки в статьях `observability/`, `guides/08`, `redmine/02`, `redmine/06`, `linux/08` и 3 по коду BSL (`1c/03`, `1c/09`) исправлены в тот же день. Уточнение пользователя: «PostgreSQL для 1С» — только для баз 1С, у сервисов (GlitchTip, Redmine) отдельный PostgreSQL.
- **Наблюдаемость (15.10.2026):** раздел `observability/` (3 статьи: WSL2 и Docker Engine; GlitchTip 6.2.6; Loki 3.7.8 и Grafana 12.4) и руководство `guides/08` — сверка документа пользователя «Тестовый стенд OpenProject + GlitchTip + Loki на ПК (WSL2)»; 15.10.2026 пользователь убрал OpenProject из проекта и поставил на его место Redmine — развёртывание Redmine в стенде, мост GlitchTip → Redmine и связь с GitLab описаны в `redmine/06`. Источники — документация Microsoft по WSL и справка `wsl.exe` из исходников, документация Docker, документация и **исходный код GlitchTip 6.2.6**, документация Loki 3.7.8 и Grafana 12.4.13, документация Sentry по протоколу. Найдено: ошибка времени в коде BSL для Loki (`ТекущаяУниверсальнаяДатаВМиллисекундах` считает от 0001 года), запрет вебхуков GlitchTip на внутренние адреса без `GLITCHTIP_ALLOW_PRIVATE_IPS=True`, необходимость фонового обработчика GlitchTip и др. На стенде не проверялось; 44 пометки «⚠».
- **1С на Windows, книги пользователя, сверка с Ubuntu (19.10.2026):** по просьбе пользователя изучить документацию «не только для Linux, но и для Windows». Сделано:
  - выгружены полные тексты четырёх книг ИТС 8.3.27: «Руководство администратора», «Клиент-серверный вариант», «Руководство пользователя», «Интерфейс „Такси“»;
  - выгружены 57 открытых методических статей ИТС про MS SQL, IIS, HASP, терминальный сервер, COM;
  - написан раздел `1c-windows/` (6 статей; 01–05 — веер из 5 агентов с согласия пользователя, около 3 млн токенов);
  - составлен конспект книг пользователя `its-docs/usr-rukovodstvo-polzovatelya-i-taksi.md`;
  - статьи `linux/` сверены с документацией Ubuntu Server (`guides/10`).

  Программная сверка имён (ключи, файлы, параметры) в статьях 01–05 с полными текстами ИТС выдуманных имён 1С не нашла. Выборочная смысловая проверка (права `processadmin`, флаг 4199, `UpdateDBCfg=v2` только по TCP/IP) подтвердилась.

  Исправлено в существующих статьях:
  - `linux/11` — kdump включается не всегда;
  - `1c/08` — аутентификация ОС администраторов возможна в консоли MMC;
  - `1c/03` — ключ `--service-principal-name` помечен как не подтверждённый ИТС;
  - `its-docs/adm-gl08-…-p2` — `DisabledByDefault` и смысл `UrlSegmentMaxLength`;
  - `its-docs/cs-gl04` — расхождение имени службы в документации;
  - `its-metod/veb-https-…` — ошибка `netsh … num=64510` (правильно `num=55536`) и `MemLimit` = 8 Тб;
  - `its-metod/licenzii-…` — порядок поиска `nhsrv.ini` по прил. 3.26.

## Маршрутизатор «задача → файл»

| Задача или вопрос | Куда смотреть |
|---|---|
| Развернуть всё с нуля | `guides/01-razvertyvanie-s-nulya.md` |
| Авария, диагностика, команды на каждый день, скрипт проверки | `guides/02-runbooki-i-shpargalki.md` |
| СУБД на отдельном хосте, второй рабочий сервер 1С | `guides/03-1c-i-postgresql-na-raznyh-hostah.md` |
| Система взаимодействия, собственный сервер, видеозвонки (Janus) | `guides/04-1c-server-vzaimodejstviya.md` |
| Что собрать с сервера, чтобы закрыть оставшиеся «⚠» | `guides/05-sbor-dannyh-s-servera.md` |
| Какие утверждения в статьях остались непроверенными (Linux, 1С, PostgreSQL, Redmine, NetBox) | `guides/06-otkrytye-voprosy.md` |
| Установить «PostgreSQL для 1С» с 1c.postgres.ru по инструкции пользователя (ветка 16, локаль `en_US.UTF-8` для конфигураций WE); документация этой сборки: `pg-setup`, `pgpro_tune`, приложение K | `guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`, подробности — `postgresql/01` (раздел 5) |
| Автоматизация развёртывания: Docker, Ansible, Kubernetes, «1С:Центр администрирования» | `1c/10`, раздел 9 |
| Поддерживаемые ОС и СУБД, системные требования | `its-docs/cs-gl01-trebovaniya.md`, `its-docs/adm-gl01-trebovaniya.md`, `1c/01` |
| Что изменилось в платформе 8.5 | `its-docs/otlichiya-8.5.1-ot-8.3.27.md` |
| Установка, обновление, удаление сервера 1С | `1c/02`, `its-docs/adm-gl02-ustanovka-p1.md`, `its-docs/cs-gl03-ustanovka-komponentov-p1.md`, `its-docs/adm-gl11-gl12-pr02-pr05-…md` |
| Служба `srv1cv8`, переменные `SRV1CV8_*`, порты, второй экземпляр | `its-docs/cs-gl04-zapusk-komponentov.md`, `1c/02` |
| Командные строки `ragent`, `rmngr`, `rphost`, `ras`, `dbgs`, `crserver` | `its-docs/adm-pr04-komandnye-stroki-utilit-p1.md` |
| `rac`: сеансы, блокировка входа, свойства кластера и серверов | `1c/03`, `its-docs/cs-gl05-administrirovanie-klastera-p1…p3.md` |
| Устройство кластера, отказоустойчивость, балансировка, профили безопасности | `its-docs/cs-gl02-klient-servernyj-variant-p1…p3.md`, `1c/01`, `1c/10` |
| Лицензии, привязка к ВМ, HASP, менеджер лицензий 8.5.4 | `1c/04`, `its-docs/adm-gl10-zashchita-licenzii-p1.md`, `…-p2.md`, `its-metod/licenzii-hasp-java-api-prochee-administrirovanie.md` |
| Веб-публикация, `webinst`, `default.vrd`, HTTPS, nginx | `1c/05`, `its-docs/adm-gl08-veb-servery-p1.md`, `…-p2.md`, `its-docs/adm-pr03-sluzhebnye-fajly-p2.md`, `…-p3.md`, `its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md` |
| `ibcmd`, автономный сервер `ibsrv` | `1c/06`, `its-docs/adm-pr04-komandnye-stroki-utilit-p2.md`, `…-p3.md`, `its-docs/adm-gl07-avtonomnyj-server.md` |
| Пакетный режим `1cv8` (`DESIGNER`, `/UpdateDBCfg`, `/DumpIB` …) | `its-docs/adm-pr07-parametry-zapuska-1cv8-p1…p3.md`, `1c/06` |
| Список баз, `ibases.v8i`, `1cestart` | `its-docs/adm-gl05-spisok-infobaz.md`, `its-docs/adm-gl04-zapusk-komponentov-p1.md` |
| Пользователи базы, виды аутентификации, журнал регистрации, тестирование и исправление | `its-docs/adm-gl06-administrirovanie-ib-p1…p3.md` |
| Технологический журнал, `logcfg.xml`, события и свойства | `1c/07`, `its-docs/adm-pr03-sluzhebnye-fajly-p3.md`, `…-p4.md`, `…-p5.md`, `its-metod/tehzhurnal-bash-i-potreblenie-resursov.md` |
| `conf.cfg`, `nethasp.ini` и другие служебные файлы | `its-docs/adm-pr03-sluzhebnye-fajly-p1…p6.md`, `1c/08`, `its-docs/adm-pr01-katalog-ustanovki.md` |
| Kerberos, Active Directory, OpenID | `1c/08`, `its-metod/kerberos-openid-autentifikaciya.md`, `its-metod/linux-openldap-kerberos-domennaya-avtorizaciya.md` |
| Отличия Linux от Windows, клиент, шрифты, КриптоПро, дампы | `1c/09`, `its-docs/cs-gl02-klient-servernyj-variant-p3.md`, `its-metod/linux-ustanovka-platformy-dampy-kriptopro.md` |
| Производительность 1С, расчёт оборудования, нагрузочные тесты | `1c/10`, `its-metod/raschet-oborudovaniya-i-nagruzochnoe-testirovanie.md`, `its-metod/metodika-proizvoditelnosti-apdex.md` |
| Блокировки и взаимоблокировки 1С | `its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md`, `its-metod/ekspluataciya-krupnoj-sistemy-blokirovki-tranzakcii.md` |
| Режимы блокировок и уровни изоляции по СУБД, особенности PostgreSQL для разработчика, повторное использование сеансов HTTP-сервисов (`IBSession`), сервер хранилища `crserver`, ограничения клиента в Linux | `its-docs/dev-rukovodstvo-razrabotchika-vyborka.md` |
| «Руководство разработчика»: что в какой главе, как устроена платформа | `its-docs/dev-gl01-koncepciya.md`, `its-docs/dev-obzor-glav-razrabotki.md` |
| Транзакции, объектные и управляемые блокировки, монопольный режим, дополнительные индексы | `its-docs/dev-gl09-rabota-s-dannymi.md` |
| Свойства конфигурации, режим совместимости, обновление конфигурации базы данных (динамическое, фоновое), выгрузка в файлы XML | `its-docs/dev-gl02-rabota-s-konfiguraciej.md`, `its-docs/dev-pr07-osobennosti-rezhimov.md` |
| Роли, привилегированный и безопасный режим, защита от опасных действий, права доступа | `its-docs/dev-gl05-obekty-konfiguracii.md`, `its-docs/dev-pr07-osobennosti-rezhimov.md` (7.10), `its-docs/dev-prilozheniya.md` (приложение 6) |
| Расширения конфигурации (`.cfe`): подключение, порядок, профили безопасности, «расширение не подключается» | `its-docs/dev-gl30-rasshireniya.md` |
| Регламентные и фоновые задания, полнотекстовый поиск (версии 1 и 2), поисковые выражения | `its-docs/dev-gl19-gl20-zadaniya-polnotekstovyj-poisk.md`, `its-docs/dev-prilozheniya.md` (приложение 5) |
| Журнал регистрации глазами разработчика (файлы `.lgp`, события, ограничения) | `its-docs/dev-gl22-zhurnal-registracii.md` |
| Разделение данных (`/Z`, области), копии базы данных и Дата акселератор | `its-docs/dev-gl24-razdelenie-dannyh.md`, `its-docs/dev-gl26-kopii-bazy-dannyh.md` |
| РИБ, планы обмена, восстановление конфигурации узла (`/ResetMasterNode`) | `its-docs/dev-gl15-obmen-dannymi-rib.md` |
| Web- и HTTP-сервисы, OData, внешние источники данных (ODBC на Linux), адреса `/ws/`, `/hs/`, `/odata/` | `its-docs/dev-gl17-integraciya.md`, `its-docs/dev-prilozheniya.md` (приложение 12) |
| Отладка на сервере Linux (`SRV1CV8_DEBUG`, порты 1550 и 1560–1591, `dbgs`), сообщения об ошибках входа, отчёты об ошибках | `its-docs/dev-gl31-otladka-oshibki-testirovanie.md` |
| Хранилище конфигурации и сервер хранилища (`crserver`, порт 1542, резервная копия), поставка, поддержка, обновление типовой конфигурации | `its-docs/dev-gl37-gl38-hranilishche-postavka-podderzhka.md` |
| Система взаимодействия со стороны информационной базы: регистрация, копии базы, перенос данных, безопасность | `its-docs/dev-gl29-sistema-vzaimodejstviya.md`, `guides/04-1c-server-vzaimodejstviya.md` |
| Криптография (КриптоПро на Linux), внешние компоненты на сервере (изолированное подключение), кроссплатформенные отличия Windows и Linux | `its-docs/dev-gl23-gl32-gl33-kriptografiya-vneshnie-komponenty-linux.md` |
| Временное хранилище (где лежат данные), история данных (версионирование) | `its-docs/dev-gl21-gl25-vremennoe-hranilishche-istoriya-dannyh.md` |
| Пароли и политики паролей, восстановление пароля, активация лицензий из встроенного языка, «1С:Аналитика» | `its-docs/dev-gl34-prochie-mehanizmy.md` |
| Особенности СУБД (PostgreSQL, файловая база, MS SQL), навигационные ссылки `e1c://`, префиксы JSON | `its-docs/dev-prilozheniya.md` |
| Что меняется при смене режима совместимости; клиент под Linux и macOS; веб-клиент | `its-docs/dev-pr07-osobennosti-rezhimov.md` |
| Мониторинг, сбор данных для расследования | `its-metod/monitoring-i-audit.md`, `its-metod/sbor-dannyh-dlya-rassledovaniya-problem.md`, `its-docs/adm-pr06-internet-servisy-administrirovaniya.md` |
| Регламентные и фоновые задания, хранилище конфигурации | `its-metod/medlennye-operacii-zadaniya-vremennye-fajly-hranilishche.md` |
| Какой PostgreSQL ставить, установка сборки для 1С | `postgresql/01`, `its-docs/cs-gl03-ustanovka-komponentov-p2.md` |
| `postgresql.conf` под 1С, официальные значения | `postgresql/02`, `its-metod/pg-nastrojki-postgresql-dlya-1c.md` |
| `psql`, роли, базы, служебные утилиты, каталоги | `postgresql/03` |
| Как 1С хранит данные: таблицы, поля, индексы | `its-metod/razmeshchenie-dannyh-i-indeksy.md`, `its-metod/razmeshchenie-dannyh-tablicy-i-polya.md` |
| Резервное копирование и восстановление | `postgresql/04`, `its-metod/pg-sborka-arhivirovanie-rezervnoe-kopirovanie.md` |
| `VACUUM`, автоочистка, `REINDEX`, раздувание | `postgresql/05` |
| Медленные запросы, `pg_stat_*`, `EXPLAIN`, методика 1С | `postgresql/06`, `its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md` |
| Репликация, отказоустойчивость, копии баз данных, обновление версий PostgreSQL | `postgresql/07`, `its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md` |
| Ошибки связки 1С + PostgreSQL | `postgresql/08` |
| Устройство PostgreSQL: процессы, WAL, MVCC, блокировки | `postgresql/09` |
| Команды терминала, справочник команд | `linux/01`, `linux/12` |
| `grep`, `sed`, `awk`, разбор логов | `linux/02` |
| Пользователи, права, `sudo` | `linux/03` |
| `apt`, репозитории, фиксация версий | `linux/04` |
| `systemd`, `journalctl`, `cron`, таймеры | `linux/05` |
| Нагрузка, память, диск, OOM killer | `linux/06` |
| Диски, LVM, расширение диска ВМ, swap | `linux/07` |
| Сеть, netplan, DNS и имена, `ufw`, SSH | `linux/08` |
| `sysctl`, huge pages, локали, время, сертификаты | `linux/09` |
| Архивы, `rsync`, bash-скрипты | `linux/10` |
| Установка Ubuntu Server, Hyper-V, VMware, VirtualBox | `linux/11` |
| **1С на Windows (справочник):** установить сервер 1С на Windows Server, тихая установка (`setup.exe /S`, `msiexec`, `InstallComponents`); служба агента (`USR1CV8`, «Вход в качестве службы», `ragent /instsrvc`, `sc.exe create/config`, `srvinfo`); `ras`, `crserver`, `dbgs` службами; второй экземпляр; брандмауэр Windows; обновление и удаление | `1c-windows/01-ustanovka-servera-i-sluzhba-windows.md` |
| MS SQL Server для 1С: версии и сроки поддержки, установка экземпляра, драйвер OLE DB, права логина кластера, смещение дат 2000, MAXDOP, память, tempdb, флаги трассировки, RCSI, бэкап и журнал, регламент (индексы 8.3.22+), медленная работа (ожидания, DMV, Query Store), перенос MS SQL → PostgreSQL | `1c-windows/02-ms-sql-server-dlya-1c.md` |
| Публикация на IIS: роли, `wsisapi.dll`, `webinst -iis`, пул приложений и веб-сад (8.3.26+), лимиты запросов и длины URL для OData, HTTPS и TLS, аутентификация Windows и делегирование, ошибки 404.x/500/503, FREB; Apache под Windows | `1c-windows/03-veb-publikaciya-iis.md` |
| Аутентификация ОС на Windows (AD, Kerberos, SPN, делегирование, `DstUserName2`); клиенты Windows и сервер 1С на Ubuntu; установка и обновление клиентов (MSI, `.mst`, групповые политики, 1CEClientSetupMake); списки баз (`ibases.v8i`, `1cestart.cfg`, `1cescmn.cfg`); ключи командной строки; терминальный сервер (RDS); COM-соединение (`V83.COMConnector`, `regsvr32`) | `1c-windows/04-domen-kerberos-klienty-terminalnyj-server.md` |
| Лицензии на Windows (драйвер HASP, HASP License Manager, `nethasp.ini`, `*.lic`, 8.5.4 — `rmlic`); техжурнал и дампы на Windows (WER LocalDumps, ProcDump); журнал событий и ошибки сертификатов; счётчики Performance Monitor; сводная таблица Windows ↔ Linux | `1c-windows/05-licenzii-diagnostika-otlichiya-ot-linux.md` |
| Windows Server как ОС: какую версию брать (2025 нет в перечне 8.3.27; 2016 — до 12.01.2027), Server Core или Desktop Experience, SConfig, время, активация, удалённое управление, службы, IPv4/IPv6, динамические порты и их исчерпание, электропитание, антивирус, диски, журналы, `wbadmin`, обновления, Hyper-V | `1c-windows/06-windows-server-dlya-administratora-1c.md` |
| Что администратору нужно из «Руководства пользователя» и «Интерфейса „Такси“»: установка клиента, разрядность при запуске, низкая скорость, системные параметры, «О программе» и отчёт об ошибке, веб-клиент (браузеры, лицензия на вкладку, что требует HTTPS, Kerberos в Firefox, PWA), система взаимодействия у пользователя | `its-docs/usr-rukovodstvo-polzovatelya-i-taksi.md` |
| Сверка статей `linux/` с документацией Ubuntu Server (19.10.2026): что совпало, что уточнено (kdump) | `guides/10-sverka-linux-s-ubuntu-server.md` |
| **Запросы 1С на PostgreSQL:** почему отчёт или проведение тормозит, что в запросе 1С дорого стоит (виртуальные таблицы, «через точку», вложенные запросы, `ПОЛНОЕ СОЕДИНЕНИЕ`, `ПОДОБНО`, временные таблицы), какие стандарты ИТС нарушены, что может сделать администратор и что передать разработчику | `postgresql/10-zaprosy-1c-v-postgresql.md` |
| Расширения сборки «PostgreSQL для 1С»: `mchar`, `fulleq`, `fasttrun`, `plantuner`, `online_analyze`, `dbcopies_decoding`, `auto_dump` — параметры, умолчания, ограничения | `guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md`, разд. 8 |
| Какую версию и редакцию SQL Server брать под 1С, сроки поддержки, что поддерживают 8.3.27 и 8.5, последние CU | `mssql/01-versii-redakcii-arhitektura.md` |
| Лицензирование SQL Server: на ядро или сервер + CAL, ВМ, Software Assurance, резервные узлы, мультиплексирование через 1С | `mssql/01-versii-redakcii-arhitektura.md` |
| Как устроен SQL Server: службы, SQLOS, память, журнал и VLF, контрольные точки, tempdb и версии строк, блокировки и RCSI в 1С | `mssql/01-versii-redakcii-arhitektura.md` |
| Установить SQL Server под 1С: мастер, `setup.exe` без участия, `ConfigurationFile.ini`, журналы установки | `mssql/02-ustanovka-i-nastrojka-ekzemplyara.md` |
| Настроить экземпляр под 1С: `max server memory`, MAXDOP, DAC, IFI, Lock Pages in Memory, `tempdb`, `model`, флаги трассировки | `mssql/02-ustanovka-i-nastrojka-ekzemplyara.md` |
| Драйвер OLE DB 18/19 на серверах 1С, шифрование, Shared Memory и оптимизированная реструктуризация (`UpdateDBCfg=v2`), порты и брандмауэр | `mssql/02-ustanovka-i-nastrojka-ekzemplyara.md` |
| Логин SQL Server для ИБ 1С: какие роли (processadmin, dbcreator), создание, смена пароля, блокировка | `mssql/03-administrirovanie-instrumenty-prava.md` |
| После восстановления/переноса базы 1С не подключается: владелец, «осиротевшие» пользователи, перенос логинов с SID | `mssql/03-administrirovanie-instrumenty-prava.md` |
| SSMS, sqlcmd, Configuration Manager, PowerShell SqlServer, dbatools: установка, ключи, шифрование по умолчанию | `mssql/03-administrirovanie-instrumenty-prava.md` |
| Настроить резервное копирование базы 1С на MS SQL (модель, полные/разностные/журнал, COPY_ONLY, CHECKSUM, сжатие, сетевая папка, агент, Ola Hallengren) | `mssql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` |
| Растёт журнал транзакций / ошибка 9002 / log_reuse_wait_desc / TRUNCATE_ONLY не работает | `mssql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` |
| Восстановить базу 1С из копии SQL Server: рядом под другим именем, на момент времени (STOPAT), поверх рабочей с хвостом журнала, страничное | `mssql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md` |
| Обслуживание индексов MS SQL для 1С: REORGANIZE/REBUILD, «Reorganize Index Task» падает на 8.3.22+, ALLOW_PAGE_LOCKS | `mssql/05-obsluzhivanie-indeksy-statistika.md` |
| Статистика MS SQL для 1С: FULLSCAN, sp_updatestats, асинхронное автообновление, порог автообновления | `mssql/05-obsluzhivanie-indeksy-statistika.md` |
| DBCC CHECKDB: параметры, где и когда запускать, LastGoodCheckDbTime, что делать при ошибках | `mssql/05-obsluzhivanie-indeksy-statistika.md` |
| MS SQL под 1С тормозит: с чего начать, ожидания (sys.dm_os_wait_stats), топ запросов по CPU/чтениям | `mssql/06-monitoring-i-diagnostika.md` |
| Кто кого блокирует на SQL Server, головной блокирующий, длинные транзакции, взаимоблокировки (system_health, xml_deadlock_report) | `mssql/06-monitoring-i-diagnostika.md` |
| Готовые сеансы Extended Events и настройка Query Store для базы 1С, регрессии и принудительные планы | `mssql/06-monitoring-i-diagnostika.md` |
| Отказоустойчивость базы 1С на MS SQL: группа доступности (в т. ч. базовая в Standard), листенер, синхронный режим, автопереключение | `mssql/07-otkazoustojchivost-i-obnovlenie-versij.md` |
| Что будет с сеансами 1С при переключении SQL Server; регламент планового и аварийного переключения, логины с тем же SID | `mssql/07-otkazoustojchivost-i-obnovlenie-versij.md` |
| FCI, доставка журналов, зеркалирование, распределённые группы для баз 1С | `mssql/07-otkazoustojchivost-i-obnovlenie-versij.md` |
| Ошибка 1С с MS SQL: «Ошибка СУБД…», native=18456/1222/1205/9002/1105/701/8645 — что значит и что делать | `mssql/08-tipovye-problemy-i-zaprosy-1c.md` |
| Тайм-ауты и взаимоблокировки на MS SQL, эскалация, флаги 1211/1224, кто кого блокирует (DMV, system_health, <dbmslocks/>) | `mssql/08-tipovye-problemy-i-zaprosy-1c.md` |
| Переполнен журнал (9002) или tempdb, хранилище версий RCSI, нехватка памяти, долгая реструктуризация (MAXDOP 0) | `mssql/08-tipovye-problemy-i-zaprosy-1c.md` |
| Установить Apache на Ubuntu, разобраться в `/etc/apache2` (apache2.conf, envvars, ports.conf, *-available/*-enabled), `a2enmod`/`a2ensite`/`a2enconf`, `apache2ctl configtest`/`-S`/`-M`, перезагрузка без обрыва (reload vs restart) | `apache/01-ustanovka-i-ustrojstvo.md` |
| Версии apache2 в Ubuntu 22.04/24.04/26.04, закрыта ли CVE (бэкпорты), отличия юнита systemd 26.04, drop-in, лимит файлов | `apache/01-ustanovka-i-ustrojstvo.md` |
| Выбрать и переключить MPM (worker для 1С, mod_php переводит на prefork), `ServerLimit`/`ThreadLimit`, несколько экземпляров `apache2@` под разные версии платформы 1С | `apache/01-ustanovka-i-ustrojstvo.md` |
| Включить HTTPS в Apache, выбрать протоколы и шифры (TLSRef intermediate), HSTS, OCSP stapling, HTTP/2 | `apache/02-https-bezopasnost-autentifikaciya.md` |
| Сертификат: CSR с SAN для корпоративного УЦ, PFX → PEM, Let's Encrypt/certbot, проверка цепочки и срока | `apache/02-https-bezopasnost-autentifikaciya.md` |
| Ограничить доступ (Require ip, RequireAll), Basic/htpasswd, вход по группе AD через LDAP (ldaps, вложенные группы) | `apache/02-https-bezopasnost-autentifikaciya.md` |
| Расчёт и настройка MPM Apache (worker/event/prefork, MaxRequestWorkers, ServerLimit, ThreadsPerChild), «server reached MaxRequestWorkers», память процессов | `apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md` |
| Обратный прокси Apache перед Redmine/NetBox/GlitchTip/Grafana/Loki или перед публикацией 1С на другом сервере: X-Forwarded-*, ProxyPreserveHost, mod_remoteip, таймауты, 502/503/504, WebSocket | `apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md` |
| Балансировка нескольких веб-серверов (mod_proxy_balancer, stickysession, mod_proxy_hcheck, balancer-manager) | `apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md` |
| Apache не запускается или не перечитывает конфигурацию: `configtest` с ошибкой, `Invalid command`, порт занят (`AH00072`), не грузится модуль (в т. ч. `wsap24.so`), `reload` против `restart` | `apache/04-tipovye-problemy-i-apache-na-windows.md` |
| Apache отвечает 403/404/401/400/408/413/414: какое правило `Require` отказало (`AH01630`), права (`AH00035`), лимиты запроса, длинный заголовок Kerberos | `apache/04-tipovye-problemy-i-apache-na-windows.md` |
| Обратный прокси отвечает 500/502/503/504 («Proxy Error»), гонка keep-alive, перенаправления на http://, TLS к бэкенду, 421 Misdirected Request, ошибки рукопожатия и цепочки сертификатов | `apache/04-tipovye-problemy-i-apache-na-windows.md` |
| Установить IIS 10 на Windows Server 2016–2025 (имена компонентов `Web-*`/`IIS-*`, `Install-WindowsFeature -IncludeManagementTools`, `-Source`, Server Core), понять устройство HTTP.sys/WAS/W3SVC/w3wp | `iis/01-ustrojstvo-ustanovka-sajty-puly.md` |
| Пул приложений IIS: «Без управляемого кода», ApplicationPoolIdentity, idleTimeout, AlwaysRunning, переработка по расписанию, rapid-fail (503), веб-сад `maxProcesses` (для 1С 8.3.26+ — ~1 процесс на 100 сеансов) | `iis/01-ustrojstvo-ustanovka-sajty-puly.md` |
| Конфигурация IIS: `applicationHost.config`/`web.config`, наследование, блокировка разделов (`overrideMode`, `/commit:apphost`), `appcmd`, модули PowerShell `IISAdministration`/`WebAdministration`, удалённое управление WMSVC | `iis/01-ustrojstvo-ustanovka-sajty-puly.md` |
| Сертификат и HTTPS-привязка на IIS: импорт PFX, New-IISSiteBinding / New-WebBinding, netsh http sslcert, SNI, Central Certificate Store, автоперепривязка | `iis/02-https-autentifikaciya-bezopasnost.md` |
| Ужесточить TLS на IIS: отключить TLS 1.0/1.1 (реестр Schannel или флаги привязки), шифры Get-/Disable-TlsCipherSuite, HSTS, HTTP→HTTPS, заголовки безопасности, скрыть Server | `iis/02-https-autentifikaciya-bezopasnost.md` |
| Аутентификация на IIS: анонимная, Basic, Windows (Kerberos/NTLM, SPN HTTP/…, useAppPoolCredentials, Extended Protection, HTTP 400 из-за большого билета), делегирование для 1С | `iis/02-https-autentifikaciya-bezopasnost.md` |
| 503 под нагрузкой, очередь пула, веб-сад для 1С (8.3.26+), обрывы длинных операций при переработке, таймауты соединений, параметры http.sys в реестре | `iis/03-proizvoditelnost-arr-zhurnaly-diagnostika.md` |
| IIS как обратный прокси (URL Rewrite + ARR) перед публикацией 1С на другом сервере или перед Grafana/Redmine/NetBox/GlitchTip: X-Forwarded-*, preserveHostHeader, таймаут 502.3, WebSocket, ферма ARR | `iis/03-proizvoditelnost-arr-zhurnaly-diagnostika.md` |
| Журналы IIS (W3C, HTTPERR), трассировка неудачных запросов FREB, события WAS 5002/5010/5011/5013, счётчики и мониторинг IIS | `iis/03-proizvoditelnost-arr-zhurnaly-diagnostika.md` |
| Поставить Apache Kafka 4.x на Ubuntu (архив + свой юнит systemd, KRaft, разметка `kafka-storage format`, `advertised.listeners`) или в Docker (`apache/kafka`), выбрать версию и Java | `kafka/01-ustrojstvo-ustanovka-nastrojka.md` |
| Kafka: TLS, SASL/SCRAM, ACL, кластер из 3 контроллеров, метрики (UnderReplicated, отставание групп), сдвиг смещений, обновление `kafka-features.sh` | `kafka/02-bezopasnost-klaster-monitoring-obsluzhivanie.md` |
| Обмен 1С с Kafka: HTTP-мост Strimzi + `HTTPСоединение` (код), внешняя компонента Simple Kafka, шаблон outbox и идемпотентный приём, «1С:Шина» и Kafka | `kafka/03-obmen-1c-s-kafka.md` |
| Поставить RabbitMQ 4.x на Ubuntu из репозиториев команды RabbitMQ (не пакет Ubuntu 3.12) или в Docker; vhost, кворумные очереди, DLX, `rabbitmq.conf` | `rabbitmq/01-ustrojstvo-ustanovka-nastrojka.md` |
| RabbitMQ: пользователи и права (`configure`/`write`/`read`), TLS, кластер из 3 узлов (Khepri, cookie), Prometheus, сторожа памяти/диска, `export_definitions`, обновление с флагами | `rabbitmq/02-bezopasnost-klaster-monitoring-obsluzhivanie.md` |
| Обмен 1С с RabbitMQ: сервисы интеграции платформы (очереди в базе, фоновые задания, `SINTEG`), «1С:Шина», PinkRabbitMQ, HTTP API, прямое подключение по AMQP 1.0 (сообщество) | `rabbitmq/03-obmen-1c-s-rabbitmq.md` |

## guides/ — Сквозные руководства

### guides/01-razvertyvanie-s-nulya.md

**Развёртывание с нуля: виртуальная машина → Ubuntu Server → PostgreSQL для 1С → сервер 1С → база → веб → бэкапы** (31 КБ)

Разделы: Почему такой стек · Переменные, которые используются ниже · Этап 0. Что подготовить заранее · Этап 1. Виртуальная машина и установка Ubuntu Server · Этап 2. Базовая настройка ОС · Этап 3. Диски под данные и копии · Этап 4. PostgreSQL для 1С · Этап 5. Сервер 1С · Этап 6. Информационная база · Этап 7. Лицензии · Этап 8. Веб-публикация (по необходимости) · Этап 9. Резервное копирование · Этап 10. Журналы и минимальный контроль · Этап 11. Клиенты на Windows · Итоговый чек-лист · Что сделать в первую неделю эксплуатации · Источники

### guides/02-runbooki-i-shpargalki.md

**Шпаргалка на каждый день и аварийные инструкции: сервер 1С + PostgreSQL на Ubuntu** (30 КБ)

Разделы: Переменные · A. Шпаргалка «задача → команда» · B. Аварийные и регламентные инструкции · C. Скрипт проверки здоровья · D. Регламент · Источники

### guides/03-1c-i-postgresql-na-raznyh-hostah.md

**Сервер 1С и PostgreSQL на разных хостах: что меняется** (16 КБ)

Разделы: Кратко · Когда разносить · Переменные · Шаг 1. Подготовка хоста СУБД · Шаг 2. Проверка с хоста 1С · Шаг 3. Информационная база · Шаг 4. Что ещё меняется в эксплуатации · Второй рабочий сервер 1С · Типичные ошибки · Источники

### guides/04-1c-server-vzaimodejstviya.md

**«1С:Сервер взаимодействия»: собственный сервер системы взаимодействия на Linux** (19 КБ)

Разделы: Кратко · Компоненты и порты · Установка по шагам · Типичные ошибки и подводные камни · Что не подтверждено

### guides/05-sbor-dannyh-s-servera.md

**Сбор данных с сервера: что нужно, чтобы закрыть оставшиеся пометки «⚠»** (9 КБ)

Разделы: Зачем · Сценарий · Как пользоваться · Что сценарий не покрывает

### guides/06-otkrytye-voprosy.md

**Открытые вопросы базы знаний: все оставшиеся пометки о непроверенном** (пересобран 20.10.2026 — разделы `linux/`, `1c/`, `postgresql/`, `redmine/`, `netbox/`, `1c-windows/`, `mssql/`, `apache/`, `iis/`, `kafka/`, `rabbitmq/`, всего 1663 пометки)

Разделы: Как пользоваться · Сколько осталось · Проверяется на своём сервере · Относится к платформе 8.5.4 и новее · Касается стороннего продукта · Практика сообщества, память автора, тексты сообщений. Файл строится сценарием `tools/marks-report.ps1` (список разделов — параметр `-Dirs`; `observability/` и `guides/` в него не входят).

### guides/07-postgresql-dlya-1c-s-1c-postgres-ru.md

**Установка «PostgreSQL для 1С» с сайта 1c.postgres.ru: инструкция пользователя, сверенная с первоисточниками** (60 КБ)

Разделы: 1. Что такое 1c.postgres.ru (условия, версии и ОС, форму заполнять не обязательно) · 2. Инструкция пользователя и её сверка · 3. Порядок установки (Ubuntu 22.04 / 24.04, ветка 16): локаль, репозиторий, установка, проверка, пароль, **параметры для 1С (быстрая установка их не выставляет — шаг 7)**; если кластер создался не в той локали; типичные сбои · 4. Документация сборки: установка в Linux, пакеты, `pg-setup`, `pg-wrapper`, `pgpro_tune` и пресеты, обновление · 5. Документация сборки: приложение K «Настройка PostgreSQL для решений 1С» (локаль, оборудование, параметры сервера, модули) · 6. Что проверить на своём сервере · 7. Что показал разбор пакетов `postgrespro-1c-16-server` и `postgrespro-1c-16` (16.14-1.noble): что делает метапакет при установке (`pg-setup initdb` без параметров, `1c.tune` не применяется), служба systemd, как `pg-setup` выбирает локаль (запасной список начинается с `ru_RU.UTF-8`), файл `/etc/default/postgrespro-1c-16`, журнал в `data/log`, сокет в `/tmp`, содержимое пресетов `default.tune` и `1c.tune` (`listen_addresses = '*'`, `work_mem = 512MB`), перезапуск сервера при обновлении пакета, замечания для эксплуатации · 8. Расширения для 1С по страницам приложения F (19.10.2026): что включено само, `mchar`/`mvarchar` и риск при `pg_restore`/`pg_upgrade` (подраздел 10.2.1), `fulleq`, `fasttrun`, `plantuner`, `online_analyze` (все параметры и умолчания; с современными версиями 1С не рекомендуется), `auto_dump` в сборке Postgres Pro — другие параметры, чем у `auto_dump` 1.1 из методичек ИТС. Источники: рабочая инструкция пользователя (docx), сайт, репозиторий `repo.postgrespro.ru/1c/`, открытая документация сборки `repo.postgrespro.ru/doc/pg1c/`, сам пакет.

### guides/08-testovyj-stend-glitchtip-loki-wsl2.md

**Тестовый стенд «GlitchTip + Loki + Grafana + Redmine на ПК в WSL2» по документу пользователя: сверка с документацией** (37 КБ; OpenProject из проекта убран 15.10.2026 — его место занял Redmine, см. `redmine/06`)

Разделы: 1. Итог сверки — не заработает без исправления (время в BSL для Loki, вебхук на внутренний адрес, обработчик GlitchTip), риски потерь (вебхук без повтора и один раз на группу, разбор `attachments`, `event_id` из очереди, порядок отправки в Loki), неточности документа, безопасность · 2. Шаг за шагом: таблица «что в документе / что в документации / вывод» и уточнения таблицы неисправностей · 3. Исправленный код BSL (GlitchTip и Loki) · 4. Что проверить на стенде · 5. Что не проверено.

### guides/09-sovmestimost-instrumentov.md

**Совместимость инструментов стенда наблюдаемости 1С: версии, пары, несовместимости, закреплённый набор и перенос на рабочий сервер** (100 КБ; проверка 15.10.2026 — 9 агентов по звеньям и сводящий агент)

Разделы: Кратко (вердикт: версии совместимы, но стенд «как есть» с первого раза не заработает; 10 главных пунктов) · 1. Таблица версий (Windows 11, WSL 3.0.3, Ubuntu 24.04.5, Docker 29.9.1, Compose 5.6.0, GlitchTip 6.2.6, PostgreSQL 18.6/17.11, Valkey 9.1.2, Loki 3.7.8, Grafana 12.4.13 — не `latest`, Alloy 1.20.1, Redmine 7.0.2, NetBox 4.7.3 (дополнено 15.10.2026), Python 3.14.8, FastAPI 0.143.1, GitLab CE 19.x, gitsync 3.9.1; сроки поддержки) · 2. Матрица совместимости по звеньям (2.1–2.7) и код BSL (2.8) · 3. Несовместимости и риски по убыванию серьёзности · 4. Рекомендуемый закреплённый набор (фрагмент `docker-compose.yml`, пакеты) · 5. Перенос на рабочий сервер: отдельная ВМ для сервисов, отдельный PostgreSQL (пакеты PGDG конфликтуют с `postgrespro-1c-16`), бэкапы `pg_dump` своей версии · 6. Ошибки в статьях базы (53 — все исправлены 15.10.2026) · 7. Что не проверено.

### guides/10-sverka-linux-s-ubuntu-server.md

**Сверка статей `linux/` с официальной документацией Ubuntu Server** (19.10.2026; 23 страницы documentation.ubuntu.com/server: время и chrony, OpenSSH, ufw, автообновления, фазовые обновления, переход на новый выпуск, пользователи, sudo-rs, требования, LVM, Netplan, AppArmor, kdump, PostgreSQL, Apache, резервное копирование)

Разделы: 1. Как сверяли (обход 246 страниц, программная проверка путей, пакетов и команд, ручная сверка умолчаний) · 2. Результаты по темам (расхождений нет, кроме kdump — `linux/11` уточнён; страница Ubuntu про OpenSSH упрощает перезапуск при сокет-активации) · 3. Что есть в документации Ubuntu, но не в базе · 4. Что не сверялось

## linux/ — Linux Ubuntu — тематические статьи

### linux/01-shell-osnovy.md

**Bash и основы работы в терминале Ubuntu Server: навигация, файлы, перенаправления, окружение** (196 КБ)

Разделы: Кратко · Версии и отличия между LTS-выпусками · Подключение и первые шаги · Файловая система: стандарт FHS и что где лежит · Навигация и просмотр: pwd, cd, ls, tree, stat, file · Создание, копирование, перемещение, удаление · Поиск файлов и команд · Шаблоны, кавычки, подстановки · Перенаправления, конвейеры, tee, /dev/null · Управление заданиями и сигналы с клавиатуры · История команд, readline, алиасы · Переменные окружения и стартовые файлы · Справка: man, --help, apropos, info, tldr · tmux и screen: сессии, переживающие обрыв SSH · sudo и su: работа от имени root, postgres и usr1cv8 · Повседневные утилиты · Файловый менеджер mc (Midnight Commander) · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/02-tekst-i-logi.md

**Обработка текста и анализ логов в Ubuntu: grep, sed, awk и смежные утилиты; редакторы nano и vim** (248 КБ)

Разделы: Кратко · 1. Среда: какие реализации утилит установлены · 2. Просмотр файлов · 3. grep — поиск строк по шаблону · 4. sed — потоковый редактор · 5. awk — обработка по полям и агрегация · 6. Смежные утилиты · 7. JSON, XML, YAML · 8. Редакторы: nano, vim, sudoedit · 9. Локали, кодировки и BOM · 10. Практикум: анализ журналов · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/03-polzovateli-i-prava.md

**Пользователи, группы, права доступа, sudo и ACL в Ubuntu Server (для связки «1С:Предприятие 8» + PostgreSQL)** (212 КБ)

Разделы: Кратко · 1. Версии и отличия между LTS · 2. Базы учётных записей: /etc/passwd, /etc/shadow, /etc/group · 3. Создание и изменение пользователей и групп · 4. Кто есть кто и кто в системе: id, groups, getent, who, w, last, lastlog, loginctl · 5. Системные пользователи сервисов: postgres, usr1cv8/grp1cv8, www-data · 6. Права доступа: chmod, chown, chgrp, umask, спецбиты · 7. Типовые права для PostgreSQL и 1С · 8. ACL: getfacl и setfacl · 9. Атрибуты файлов: lsattr и chattr · 10. sudo и su · 11. PAM и лимиты (кратко) · 12. Политика паролей и блокировка учётных записей · 13. SSH-ключи и authorized_keys · 14. Диагностика «Permission denied» · 15. Типовые сценарии · 16. Самопроверка на сервере: всё, что в этом файле помечено ⚠ · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/04-pakety-apt.md

**Управление пакетами в Ubuntu Server: apt, dpkg, репозитории, фиксация версий, обновления** (199 КБ)

Разделы: Кратко · 1. Как устроена система пакетов · 2. apt: команды · 3. dpkg, dpkg-query, dpkg-reconfigure, debconf · 4. Установка локальных .deb и исправление зависимостей · 5. Репозитории · 6. Рабочие примеры: репозитории PostgreSQL · 7. Фиксация версий: apt-mark hold и pinning · 8. Автоматические обновления · 9. Обновление релиза, ядра HWE, Ubuntu Pro, Livepatch · 10. snap · 11. Блокировки, прокси, офлайн-установка, очистка места · 12. Журналы и откат пакета · 13. Сборка из исходников, checkinstall, update-alternatives · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/05-systemd-sluzhby-zhurnaly-cron.md

**systemd: службы, юниты, журналы journalctl, logrotate, cron и таймеры** (249 КБ)

Разделы: Кратко · 1. Версии, компоненты и расположение файлов · 2. systemctl — управление службами · 3. Написание unit-файлов служб · 4. Переопределения (drop-in) и подключение внешних юнитов · 5. Реальные юниты: сервер 1С, RAS, PostgreSQL · 6. Порядок запуска: сервер 1С после сети и после PostgreSQL · 7. Журнал systemd: journalctl и journald · 8. rsyslog и текстовые журналы в /var/log · 9. logrotate — ротация текстовых логов · 10. cron, anacron, at · 11. Таймеры systemd · 12. Загрузка и выключение · 13. hostnamectl, timedatectl, localectl, loginctl · 14. systemd-tmpfiles, coredumpctl, systemd-run и другие утилиты · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/06-processy-i-proizvoditelnost.md

**Процессы и диагностика производительности: CPU, память, диск, сеть** (232 КБ)

Разделы: Кратко · 0. Инструменты, пакеты, версии · 1. Кто есть кто: процессы сервера 1С и PostgreSQL · 2. Просмотр процессов: ps, pstree, pgrep/pkill, pidof · 3. Интерактивные мониторы: top, htop, atop, btop · 4. Сигналы: kill, killall, pkill — и что они значат для PostgreSQL и 1С · 5. Приоритеты и привязка: nice, renice, ionice, chrt, taskset · 6. Память · 7. CPU · 8. Диск · 9. Сеть · 10. sysstat и sar: история нагрузки · 11. /proc и /sys, lsof, fuser · 12. Трассировка: strace, ltrace, gdb/gcore · 13. cgroups v2 и ограничение ресурсов через systemd · 14. PSI и NUMA · 15. Методика: «сервер тормозит» · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/07-diski-fs-lvm.md

**Диски, разделы, файловые системы, LVM, swap и сетевые ФС (Ubuntu Server под 1С + PostgreSQL)** (228 КБ)

Разделы: Кратко — главные факты и команды · 1. Версии и отличия релизов Ubuntu · 2. Обзор блочных устройств: lsblk, blkid, имена устройств · 3. Таблицы разделов и инструменты разметки · 4. Файловые системы: создание, настройка, проверка · 5. Монтирование: mount, umount, findmnt, /etc/fstab · 6. Свободное место: df, du, ncdu и поиск «куда всё делось» · 7. LVM · 8. Расширение диска ВМ на лету · 9. Swap (подкачка) · 10. Программный RAID: mdadm (кратко) · 11. SSD и NVMe: TRIM, nvme-cli, smartctl, hdparm · 12. Планировщики ввода-вывода и read-ahead · 13. Тесты диска · 14. Сетевые файловые системы: NFS, CIFS/SMB, sshfs · 15. tmpfs и `/tmp` · 16. Рекомендации по разметке сервера 1С + PostgreSQL · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники

### linux/08-set-ssh-firewall.md

**Сеть в Ubuntu Server: ip, netplan, DNS и имена хостов, диагностика, ufw, SSH (для стенда 1С + PostgreSQL)** (217 КБ)

Разделы: Кратко · 1. Версии и компоненты сетевого стека · 2. Утилита ip (пакет iproute2) · 3. Netplan — постоянная конфигурация сети · 4. Имена хостов и DNS · 5. Диагностика сети · 6. Порты стека 1С + PostgreSQL · 7. Firewall · 8. SSH · 9. Работа с Windows-хоста · 10. Samba: обмен файлами с Windows · 11. Прокси, MTU, IPv6 — кратко · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/09-tyuning-yadra-lokali-vremya-bezopasnost.md

**Тюнинг ядра и лимитов, huge pages, локали, время, шрифты, безопасность и сертификаты (Ubuntu Server под 1С + PostgreSQL)** (244 КБ)

Разделы: Кратко · 1. Что различается между релизами Ubuntu (важно для этой темы) · 2. sysctl: чтение, запись, постоянные настройки · 3. Параметры sysctl для сервера БД и 1С · 4. Планировщик: что осталось актуальным в ядрах 6.x · 5. Лимиты ресурсов · 6. Transparent Huge Pages (THP) и обычные huge pages · 7. Энергосбережение CPU, tuned, параметры GRUB · 8. Время и его синхронизация · 9. Локали · 10. Шрифты для сервера 1С · 11. Безопасность · 12. Сертификаты и TLS · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/10-arhivy-rsync-bash-skripty.md

**Архивация, rsync и bash-скрипты для автоматизации (Ubuntu Server + 1С + PostgreSQL)** (246 КБ)

Разделы: Кратко — главные факты и команды · 1. Версии инструментов в Ubuntu LTS · 2. tar — упаковка каталогов · 3. Компрессоры · 4. Что выбирать для дампов БД · 5. rsync — синхронизация каталогов · 6. scp, sftp, rclone · 7. dd, split/cat, контрольные суммы · 8. Шифрование резервных копий · 9. Bash-скриптинг: руководство · 10. Полезные утилиты для скриптов · 11. Безопасное хранение паролей и секретов · 12. Уведомления: почта и Telegram · 13. Готовые скрипты · 14. Запуск по расписанию · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/11-ustanovka-ubuntu-server-i-vm.md

**Установка Ubuntu Server и работа в виртуальной машине на Windows-хосте (Hyper-V, VMware, VirtualBox)** (213 КБ)

Разделы: Кратко — главные факты и команды · 1. Релизы Ubuntu, сроки поддержки и выбор версии под 1С + PostgreSQL · 2. Установка Ubuntu Server (установщик subiquity) · 3. Чек-лист после установки · 4. Виртуализация на Windows 11 Pro: настройки хоста и гостя · 5. Сеть ВМ и разрешение имени сервера на клиентах 1С · 6. Ресурсы ВМ под 1С + PostgreSQL · 7. Снапшоты, резервное копирование и клонирование ВМ · 8. Программная лицензия 1С и параметры ВМ · 9. Синхронизация времени в ВМ · 10. USB-ключи HASP в виртуальной машине · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### linux/12-spravochnik-komand-a-z.md

**Сводный справочник команд Ubuntu Server: по категориям и по алфавиту** (210 КБ)

Разделы: Кратко — 20 главных фактов и команд · 0. Условные обозначения и отличия версий · 1. Файлы и каталоги · 2. Просмотр и обработка текста · 3. Поиск и справка · 4. Права и пользователи · 5. Пакеты (APT, dpkg, snap) · 6. Сервисы, systemd и планировщики · 7. Процессы · 8. Мониторинг CPU, памяти, диска и сети · 9. Диски, разделы, файловые системы, LVM, RAID · 10. Сеть и диагностика · 11. Firewall · 12. SSH и передача файлов · 13. Архивы и сжатие · 14. Ядро и модули · 15. Оборудование и сведения о системе · 16. Время и локали · 17. Журналы · 18. Загрузка и GRUB · 19. Безопасность и криптография · 20. Контейнеры и виртуализация (кратко) · 21. Разработка и отладка · 22. Встроенные команды и конструкции bash · 23. Утилиты PostgreSQL · 24. Утилиты «1С:Предприятие 8» на Linux · 25. Опасные команды и как не навредить · 26. Типичные ошибки и подводные камни · 27. Быстрая шпаргалка «задача → команда» · 28. Алфавитный указатель «команда → категория» · Источники

## 1c/ — 1С на Linux — тематические статьи

### 1c/01-arhitektura-versii-trebovaniya.md

**Архитектура «1С:Предприятие 8» на Linux: компоненты, процессы, порты, каталоги, версии и системные требования** (223 КБ)

Разделы: Кратко — 20 главных фактов и команд · 1. Варианты работы и общая архитектура · 2. Компоненты, процессы и исполняемые файлы · 3. Сетевые порты · 4. Каталоги и файлы на Linux · 5. Пользователь `usr1cv8` и группа `grp1cv8` · 6. Служба сервера: systemd-юниты (8.3.21+) · 7. Версии платформы: 8.3.18 … 8.3.27 и 8.5.x · 8. Системные требования для Linux · 9. Дистрибутивы: где брать и что внутри · 10. Лицензии — краткий обзор · 11. Сервер 1С на Windows и на Linux: отличия · 12. Расхождения между источниками и что проверять на живом сервере · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка · Источники

### 1c/02-ustanovka-servera-ubuntu.md

**Установка, обновление и удаление сервера «1С:Предприятие 8» на Ubuntu Server (пошагово)** (187 КБ)

Разделы: Кратко — главные факты и команды · 1. Версии и поддержка на октябрь 2026 · 2. Что скачать и как называется дистрибутив · 3. Подготовка ОС · 4. Установка единым дистрибутивом setup-full-<версия>-x86_64.run · 5. Что появляется после установки · 6. Регистрация и запуск службы сервера (systemd) · 7. Проверка работы сервера · 8. Сетевой экран ufw · 9. Сервер администрирования RAS и утилита rac · 10. Подключение консоли администрирования с Windows · 11. Отладка на сервере · 12. Смена портов, второй экземпляр, несколько версий · 13. Обновление платформы и откат · 14. Удаление и очистка · 15. Старый способ (до 8.3.20 включительно) — для справки · 16. Сквозной пример: Ubuntu Server 24.04 от чистой системы до работающего кластера · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — таблица «задача → команда» · Источники

### 1c/03-administrirovanie-klastera-ras-rac.md

**Администрирование кластера серверов 1С на Linux: ras и rac — полный справочник** (206 КБ) — ⚠ рецензентом не проверено

Разделы: Кратко — главные факты и команды · 1. Как устроено администрирование кластера · 2. Сервер администрирования ras · 3. Утилита rac: общий синтаксис · 4. Аутентификация администраторов · 5. Справочник режимов и команд rac · 6. Типовые задачи bash-скриптами · 7. Остановка и запуск сервера, очистка сеансовых данных · 8. Графические средства и программный доступ · 9. Что менялось в ras и rac по версиям · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Что не удалось подтвердить · Источники

### 1c/04-licenzirovanie.md

**Лицензирование «1С:Предприятия 8» на Linux: программные лицензии, HASP, серверные и клиентские лицензии, диагностика** (243 КБ)

Разделы: Кратко — главные факты и команды · 1. Версии и состояние на октябрь 2026 · 2. Виды лицензий · 3. Программные лицензии: привязка, файлы, каталоги · 4. Активация программной лицензии · 5. Как клиент и сервер находят лицензии · 6. Аппаратные ключи HASP на Linux · 7. Сервис лицензирования кластера на отдельном сервере · 8. Диагностика · 9. Практические рекомендации для сервера 1С в виртуальной машине · 10. Типичные ошибки и подводные камни · 11. Быстрая шпаргалка · 12. Источники

### 1c/05-veb-publikaciya-apache-nginx.md

**Веб-публикация «1С:Предприятие 8» на Linux: Apache 2.4, webinst, default.vrd, HTTPS, nginx, ibsrv** (261 КБ)

Разделы: Кратко — главные факты и команды · 1. Что такое веб-публикация и что через неё работает · 2. Требования и ограничения (официально) · 3. Установка Apache на Ubuntu · 4. Публикация: утилита webinst, конфигуратор, вручную · 5. Файл default.vrd · 6. Права и пользователи · 7. Проверка публикации · 8. HTTPS · 9. nginx как обратный прокси · 10. Автономный сервер ibsrv · 11. Аутентификация и ограничение доступа · 12. Производительность и стабильность · 13. Обновление платформы и публикаций · 14. Сквозной пример: Ubuntu 24.04, серверная база, HTTPS · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Что не удалось подтвердить · Источники

### 1c/06-infobazy-ibcmd-paketnyj-rezhim.md

**Информационные базы из командной строки: создание, ibcmd, пакетный режим конфигуратора, обновление, хранилище конфигураций** (214 КБ) — ⚠ рецензентом не проверено

Разделы: Кратко — 20 главных фактов и команд · 1. Инструменты и общие правила · 2. Создание информационной базы на PostgreSQL · 3. `ibcmd`: полный справочник · 4. Пакетный режим конфигуратора на Linux · 5. Клиентское приложение в пакетном режиме · 6. Расширения конфигурации (`.cfe`): сводка способов · 7. Типовой регламент обновления типовой конфигурации из скрипта · 8. Хранилище конфигураций: сервер `crserver` на Linux · 9. Инструменты автоматизации · 10. Список баз (`ibases.v8i`) и программа запуска `1cestart` · 11. Перенос и копирование базы · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники

### 1c/07-tehzhurnal-diagnostika-zhurnal-registracii.md

**Технологический журнал, дампы, журнал регистрации, отладка и диагностика сервера 1С на Linux** (242 КБ) — ⚠ рецензентом не проверено

Разделы: Кратко · 1. Технологический журнал: назначение и принцип работы · 2. Где лежит `logcfg.xml` на Linux и как он применяется · 3. Структура `logcfg.xml` · 4. Справочник событий · 5. Справочник свойств событий · 6. Формат файлов журнала · 7. Готовые файлы `logcfg.xml` · 8. Анализ технологического журнала в bash · 9. Дампы и аварийные завершения на Linux · 10. Журнал регистрации · 11. Отладка серверного кода на Linux · 12. Мониторинг сервера 1С · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка · Источники

### 1c/08-konfiguracionnye-fajly-kerberos-bezopasnost.md

**Конфигурационные файлы 1С на Linux, параметры запуска, Kerberos/AD и безопасность** (196 КБ) — ⚠ рецензентом не проверено

Разделы: Кратко — главные факты и команды · 1. Каталоги конфигурационных файлов и порядок поиска · 2. conf.cfg — полный перечень параметров · 3. Остальные конфигурационные и служебные файлы · 4. Параметры командной строки ragent, rmngr, rphost, ras · 5. Аутентификация ОС (Kerberos) для сервера 1С на Linux в домене Active Directory · 6. Аутентификация пользователей информационной базы · 7. Защита соединений · 8. Администраторы центрального сервера и кластера · 9. Профили безопасности, безопасный режим, защита от опасных действий · 10. Безопасность на уровне ОС · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### 1c/09-klient-linux-i-otlichiya-ot-windows.md

**Клиент 1С на Linux и отличия Linux от Windows для разработчика и администратора 1С** (230 КБ) — ⚠ рецензентом не проверено

Разделы: Кратко — 20 главных фактов и команд · 1. Версии и поддержка на октябрь 2026 · 2. Установка клиентских приложений на Ubuntu Desktop · 3. Шрифты и печатные формы · 4. Отличия Linux от Windows в прикладном коде · 5. Внешние источники данных и ODBC · 6. Криптография и ЭДО · 7. Интернет-функции: HTTP, FTP, почта, сертификаты, прокси · 8. Печать и оборудование · 9. Полнотекстовый поиск, изображения, PDF, офисные документы · 10. Замена типичных Windows-интеграций · 11. Разработка под Linux · 12. Чек-лист переноса сервера с Windows на Linux · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники · Что не удалось подтвердить

### 1c/10-proizvoditelnost-otkazoustojchivost-ekspluataciya.md

**Производительность, сайзинг, отказоустойчивость и регламенты эксплуатации 1С на Linux; миграция с Windows/MS SQL** (254 КБ) — ⚠ рецензентом не проверено

Разделы: Кратко — 20 главных фактов и команд · 1. Сайзинг: CPU, память, диски, сеть · 2. Настройки кластера под нагрузку · 3. Служебные файлы сервера: каталоги, временные файлы, кэши, поиск, журналы · 4. Регламентные и фоновые задания · 5. Отказоустойчивость и масштабирование кластера 1С · 6. Эксплуатационные регламенты (runbook) · 7. Миграция с Windows на Linux и с MS SQL Server на PostgreSQL · 8. Методика анализа производительности · 9. Контейнеризация и автоматизация развёртывания · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — таблица «задача → команда» · Источники

## 1c-windows/ — 1С:Предприятие на Windows (справочник; у пользователя сервер 1С и PostgreSQL на Ubuntu, рабочие места — Windows)

> Раздел написан 19.10.2026 по полным текстам «Руководства администратора» и «Клиент-серверного варианта» 8.3.27, «Руководства разработчика», 57 методическим статьям ИТС и Microsoft Learn: статьи 01–05 — веер из 5 агентов с согласия пользователя, 06 — вручную. На сервере не проверялось. Непроверенное помечено «⚠»: 237 открытых пометок, они включены в список `guides/06` (пересобран 19.10.2026). В разделах «Что не удалось подтвердить» статей собраны 76 расхождений внутри документации ИТС, между ИТС и Microsoft, а также устаревшие советы методичек 2007–2016 годов.

### 1c-windows/01-ustanovka-servera-i-sluzhba-windows.md

**Установка платформы и сервера 1С на Windows Server: служба агента, ras, crserver, dbgs, порты, несколько экземпляров, обновление и удаление** (145 КБ)

Разделы: Кратко · 1. Версии Windows, требования, сроки поддержки · 2. Дистрибутивы и программа установки (режимы, компоненты, setup.exe /S, msiexec, .mst, каталоги) · 3. Учётная запись службы и права (USR1CV8, SeServiceLogonRight, swpuser.ini) · 4. Служба агента ragent (/instsrvc, sc.exe, binPath, /d, /debug) · 5. ras как служба · 6. crserver · 7. dbgs · 8. Несколько экземпляров и версий · 9. Брандмауэр Windows · 10. Обновление платформы · 11. Удаление · 12. Рекомендации методичек · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### 1c-windows/02-ms-sql-server-dlya-1c.md

**Microsoft SQL Server для 1С: версии, установка, настройка, права, регламентное обслуживание, резервное копирование, расследование медленной работы; PostgreSQL для 1С на Windows** (146 КБ)

Разделы: Кратко · 1. Где MS SQL применим, смешанная среда · 2. Версии, редакции, сроки поддержки · 3. Установка экземпляра, драйвер OLE DB · 4. Учётные записи и права · 5. Создание ИБ, смещение дат · 6. Настройки экземпляра (память, MAXDOP, tempdb, флаги) · 7. Блокировки и версионность · 8. Модель восстановления и журнал · 9. Резервное копирование и восстановление · 10. Регламент (статистика, индексы 8.3.22+, CHECKDB) · 11. Медленная работа (ожидания, DMV, Query Store, техжурнал) · 12. Объём таблиц, перенос на PostgreSQL · 13. PostgreSQL для 1С на Windows · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### 1c-windows/03-veb-publikaciya-iis.md

**Веб-публикация 1С на IIS (и кратко Apache под Windows): роли IIS, модуль wsisapi.dll, webinst, пулы приложений, HTTPS, аутентификация Windows, сервисы и OData, нагрузка** (142 КБ)

Разделы: Кратко · 1. Архитектура и место IIS (смешанная среда IIS + кластер на Ubuntu) · 2. Установка IIS: роли и компоненты · 3. Модуль расширения веб-сервера 1С (wsisapi.dll, разрядность, версии) · 4. Публикация: конфигуратор и webinst · 5. default.vrd для IIS · 6. Права NTFS и учётные записи · 7. Пул приложений (веб-сад, ~100 сеансов на процесс в 8.3.26+) · 8. Ограничения размера и длины запросов · 9. HTTPS и TLS · 10. Аутентификация (Windows, делегирование, OpenID) · 11. Веб-сервисы, HTTP-сервисы, OData, мобильный и веб-клиент · 12. Нагрузка и стабильность · 13. Apache под Windows · 14. Диагностика (журналы, FREB, коды ответа) · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### 1c-windows/04-domen-kerberos-klienty-terminalnyj-server.md

**Домен и рабочие места Windows: аутентификация ОС (AD, Kerberos, SPN, делегирование), установка и обновление клиентов, списки баз, терминальный сервер, COM-соединение** (146 КБ)

Разделы: Кратко · 1. Карта клиентской части 1С на Windows · 2. Аутентификация операционной системы · 3. Сервер 1С на Windows в домене: учётная запись службы, SPN, делегирование · 4. Смешанная среда: клиенты Windows и сервер 1С на Ubuntu · 5. Установка клиентов на рабочие места (setup.exe /S, msiexec, .mst, групповые политики, 1CEClientSetupMake) · 6. Обновление клиентов · 7. Списки информационных баз (ibases.v8i, CommonInfoBases, 1cestart.cfg, 1cescmn.cfg) · 8. Параметры командной строки для администратора рабочих мест · 9. Терминальный сервер (RDS) · 10. COM-соединение и COM-объекты на Windows · 11. Режим низкой скорости соединения · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### 1c-windows/05-licenzii-diagnostika-otlichiya-ot-linux.md

**Лицензии, диагностика и отличия от Linux: сервер 1С:Предприятия на Windows** (145 КБ)

Разделы: Кратко · 1. Версии и сроки поддержки · 2. Ключи HASP на Windows (драйвер, HASP LM, nethasp.ini, 8.5.4 — rmlic) · 3. Программные лицензии на Windows · 4. Служебные файлы и каталоги · 5. Технологический журнал · 6. Дампы (dump, WER LocalDumps, ProcDump) · 7. Журнал событий Windows · 8. Счётчики производительности (logman, typeperf, relog, пороги) · 9. Сводная таблица Windows ↔ Linux · 10. Смешанная среда (клиенты Windows + сервер Linux) · 11. Расхождения источников · Типичные ошибки · Шпаргалка · Источники

### 1c-windows/06-windows-server-dlya-administratora-1c.md

**Windows Server как ОС для сервера 1С: версии, первичная настройка, службы, сеть, электропитание, антивирус, журналы, резервное копирование ОС** (54 КБ)

Разделы: Кратко · 1. Версии Windows Server и поддержка 1С (2025 нет в перечне 8.3.27; сроки Microsoft; редакции; Server Core или Desktop Experience) · 2. Аппаратные требования 2025 · 3. Первичная настройка (SConfig, PowerShell, время, активация, роли) · 4. Удалённое управление (WinRM, Windows Admin Center, RSAT, RDP, OpenSSH) · 5. Службы · 6. Сеть и TCP-стек (IPv4/IPv6, динамические порты — ошибка в методичке 5908, исчерпание портов, брандмауэр) · 7. Электропитание · 8. Учётные записи и профили для процессов 1С · 9. Антивирус · 10. Диски · 11. Журналы событий · 12. Производительность и инструменты · 13. Резервное копирование ОС (wbadmin, -vssCopy) · 14. Обновления · 15. Hyper-V · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

## mssql/ — Microsoft SQL Server для 1С (справочник; у пользователя СУБД 1С — PostgreSQL)

> Раздел написан 20.10.2026 ночью по просьбе пользователя («на стороне MS SQL знаний нет — подтянуть»). Веер «8 + 8» с согласия пользователя (около 9,9 млн токенов): каждую статью писал один агент, независимо сверял другой. Сверено около 1620 утверждений, исправлено 80 ошибок, закрыто 64 пометки, осталось 386 открытых «⚠» по счёту сценария (включены в `guides/06`). Источники: документация Microsoft (исходники sql-docs), полные тексты ИТС 8.3.27, методички ИТС по MS SQL, стандарты разработки. На сервере не проверялось. Обзорная статья `1c-windows/02` остаётся, вверху у неё — список найденных неточностей.

### mssql/01-versii-redakcii-arhitektura.md

**Microsoft SQL Server для администратора 1С: версии, редакции, сроки поддержки, лицензирование, архитектура** (183 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. MS SQL в схеме 1С (Linux-серверы 1С — нет) · 2. Версии 2016–2025, сроки поддержки, CU на 10.2026 · 3. Что поддерживает 1С 8.3.27/8.5 (2025 — нет) · 4. Редакции и пределы · 5. Лицензирование (на ядро, сервер + CAL, ВМ, SA, резервные узлы) · 6. Экземпляры, службы, системные базы · 7. SQLOS и потоки · 8. Память и буферный пул · 9. Кеш планов и параметризация · 10. Файлы, страницы, экстенты · 11. Журнал, VLF, контрольные точки, ADR · 12. tempdb и хранилище версий · 13. Блокировки и изоляция (RCSI в 1С, эскалация, оптимизированные блокировки) · 14. Оптимизатор, CE, уровень совместимости, IQP · 15. Query Store · 16. SQL Server на Linux · 17. Как 1С хранит данные (типы, составные поля) · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### mssql/02-ustanovka-i-nastrojka-ekzemplyara.md

**Установка и настройка экземпляра SQL Server под 1С: подготовка Windows, установка мастером и без участия, службы и привилегии, сортировка, сеть и драйвер, sp_configure, tempdb и model, флаги трассировки, уровень совместимости, обновления, SQL Server на Linux** (180 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. До установки: смешанная среда, версия, совмещение с 1С · 2. Подготовка Windows: тома, NTFS 64 КБ, сектор > 4 КБ, электропитание, антивирус · 3. Установка: компоненты, мастер, параметры setup.exe, ConfigurationFile.ini, журналы, проверка · 4. Учётные записи служб, IFI, Lock Pages in Memory · 5. Сортировка · 6. Проверка подлинности и sa · 7. Протоколы (Shared Memory vs UpdateDBCfg=v2), порты, брандмауэр, шифрование · 8. Драйвер OLE DB 18/19 и Native Client на серверах 1С · 9. sp_configure: память, MAXDOP, cost threshold, ad hoc, сжатие копий, DAC, blocked process threshold · 10. tempdb · 11. model · 12. Флаги трассировки (ИТС 5946 против MS Learn, 4199) · 13. Уровень совместимости и оценщик кардинальности · 14. Обновления CU/GDR · 15. SQL Server на Linux, mssql-conf · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### mssql/03-administrirovanie-instrumenty-prava.md

**Администрирование SQL Server для 1С: инструменты, учётные записи и права, SQL Server Agent и Database Mail, журнал ошибок и DAC, файлы баз, безопасность** (180 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Место SQL Server в смешанной среде · 2. Инструменты (SSMS, sqlcmd, Configuration Manager, PowerShell SqlServer, dbatools, SQL Server на Linux) · 3. Учётные записи и права для 1С · 4. «Осиротевшие» пользователи и владелец после переноса · 5. Контейнерные базы · 6. ИБ на MS SQL: создание, удаление, rac, ibcmd · 7. SQL Server Agent · 8. Database Mail · 9. Журнал ошибок · 10. DAC · 11. Файлы баз (рост, SHRINK, перенос, владелец) · 12. Безопасность (TLS, Kerberos, TDE, аудит, минимальные права, sa) · Типичные ошибки · Шпаргалка · Источники

### mssql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md

**Резервное копирование и восстановление баз 1С в SQL Server: модели восстановления, полные, разностные и журнальные копии, цепочка журнала, восстановление на момент времени, проверка и автоматизация** (156 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Что копировать для 1С (состав, RPO/RTO) · 2. Модели восстановления и выбор · 3. Виды копий (полная, разностная, журнал, COPY_ONLY, хвост) · 4. Параметры BACKUP (CHECKSUM, COMPRESSION/ZSTD, полоса, INIT, шифрование, права) · 5. Куда класть (сетевая папка и учётная запись службы, URL/S3, Linux) · 6. Цепочка журнала и её разрыв · 7. Рост журнала, log_reuse_wait_desc, 9002, TRUNCATE_ONLY, ADR · 8. Восстановление: NORECOVERY/RECOVERY, права, монопольный доступ, план из msdb · 9. STOPAT и точка сбоя · 10. MOVE, другой сервер, логины, регистрация в 1С · 11. Страничное восстановление · 12. VERIFYONLY и DBCC CHECKDB · 13. История в msdb · 14. Агент, планы обслуживания, Ola Hallengren, PowerShell/dbatools, Express · 15. VSS, wbadmin, копии ВМ · 16. .dt, журнал регистрации, хранилище двоичных данных, методички 2922/2378/2373 · 17. Сценарии (копия рядом, откат на месте, перенос на новый сервер, Linux) · Типичные ошибки · Шпаргалка · Источники · Что не подтверждено

### mssql/05-obsluzhivanie-indeksy-statistika.md

**Регламентное обслуживание SQL Server для 1С: индексы, статистика, целостность, кеш планов** (184 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Кто что обслуживает: СУБД и 1С (ИТС-КС 5.5, тестирование и исправление, версии и редакции, Linux) · 2. Фрагментация и плотность страниц · 3. REORGANIZE и REBUILD (онлайн, RESUMABLE, журнал, MAXDOP) · 4. ALLOW_PAGE_LOCKS = OFF в базах 8.3.22+ · 5. FILLFACTOR · 6. Статистика (пороги, ASYNC, FULLSCAN, sp_updatestats) · 7. Кеш планов (FREEPROCCACHE против CLEAR PROCEDURE_CACHE) · 8. DBCC CHECKDB · 9. Устаревшее и недокументированное · 10. Методичка 5837: что актуально · 11. Планы обслуживания и Ola Hallengren · 12. Регламент на собственном T-SQL · 13. Расписание для 1С · 14. tempdb, автоприращение, ghost cleanup · Типичные ошибки · Шпаргалка · Источники

### mssql/06-monitoring-i-diagnostika.md

**Мониторинг и диагностика SQL Server под 1С: ожидания, блокировки, взаимоблокировки, медленные запросы** (182 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. С чего начинать (методика ИТС 6008, права, инструменты, DAC, Linux) · 2. 1С изнутри SQL Server (логины, #tt, изоляция, мост session_id ↔ сеанс 1С, таблицы → объекты) · 3. Статистика ожиданий · 4. Текущие сеансы и запросы, sp_WhoIsActive, KILL · 5. Блокировки, спящий головной блокирующий, blocked process report, <dbmslocks/> · 6. Взаимоблокировки (system_health, граф) · 7. Extended Events — готовые сессии · 8. Query Store · 9. Кеш планов и топ-запросы (5861, 5813, 5910, 5906) · 10. Диски, память, tempdb, CPU · 11. Счётчики Performance Monitor · 12. Связка с техжурналом 1С (DBMSSQL, Dbpid, <plansql/>) · 13. Библиотека запросов D-01…D-37 · Типичные ошибки · Быстрая шпаргалка · Источники · Что не удалось подтвердить

### mssql/07-otkazoustojchivost-i-obnovlenie-versij.md

**Отказоустойчивость SQL Server для 1С и обновление версий: группы доступности, FCI, доставка журналов, CU/GDR, уровень совместимости, переход на PostgreSQL** (181 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Карта отказоустойчивости для 1С · 2. Группы доступности Always On (требования, базовые группы, режимы, автопереключение, настройка, логины, читаемые реплики) · 3. Подключение 1С к листенеру (MultiSubnetFailover, сертификат, SPN) · 4. Сеансы 1С при переключении (плановое и аварийное) · 5. Эксплуатация баз 1С в группе · 6. FCI · 7. Доставка журналов · 8. Зеркалирование, распределённые группы, Linux · 9. Резервирование на уровне 1С · 10. CU и GDR · 11. Переход на новую версию (уровень совместимости, CE, скользящее обновление, проверочный план) · 12. Перенос на PostgreSQL · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### mssql/08-tipovye-problemy-i-zaprosy-1c.md

**Типовые проблемы 1С + SQL Server (симптом → причина → решение) и запросы 1С в T-SQL** (181 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Как читать ошибку (native, журнал ошибок, session_id) · 2. Подключение (OLE DB, сеть, 18456, OLE DB Driver 19) · 3. Блокировки (1222, 1205, Intra-query parallelism, эскалация 1211/1224, 1204, KILL) · 4. Журнал 9002 и 1105 · 5. tempdb и хранилище версий · 6. Память (701, 8645, 8623, THREADPOOL) · 7. MAXDOP и реструктуризация · 8. Смещение дат, collation, пределы ключа · 9. CPU · 10. Диски · 11. Запросы 1С в T-SQL (sp_executesql, #tt, RCSI, ПОЛНОЕ СОЕДИНЕНИЕ, Query Store hints, стандарты, отличия от PostgreSQL) · 12. Порядок действий · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

## apache/ — Apache HTTP Server: общее администрирование (Ubuntu, кратко Windows)

> Раздел написан 20.10.2026 ночью по плану пользователя (после `mssql/`). Веер «4 + 4» с согласия пользователя (около 4,2 млн токенов): каждую статью писал один агент, независимо сверял другой. Сверено 895 утверждений, исправлено 56 ошибок, закрыто 68 пометок. Источники: документация Apache httpd 2.4 (исходники docs/manual), пакеты и журналы изменений Ubuntu/Debian, документация Ubuntu Server, README модулей. Публикация 1С на Apache по-прежнему в `1c/05`. На сервере не проверялось.

### apache/01-ustanovka-i-ustrojstvo.md

**Apache HTTP Server на Ubuntu: версии, установка, устройство конфигурации, MPM, модули, виртуальные хосты** (164 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Версии Apache и поддержка · 2. Установка и состав пакетов · 3. Служба systemd · 4. Раскладка конфигурации Debian/Ubuntu · 5. Утилиты a2enmod … a2query · 6. apache2ctl и apache2: проверка и диагностика · 7. Как Apache читает конфигурацию · 8. MPM: event, worker, prefork · 9. Модули: загрузка и проверка · 10. Имя сервера: ServerName, AH00558 · 11. Виртуальные хосты · 12. Права · 13. AppArmor и ограничения systemd · 14. Регламент изменения конфигурации без обрыва · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### apache/02-https-bezopasnost-autentifikaciya.md

**Apache: HTTPS и TLS, сертификаты, безопасность, аутентификация (Basic, LDAP/AD, Kerberos)** (170 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Версии · 2. mod_ssl в Ubuntu · 3. Сертификаты и ключи (УЦ, самоподписанные, certbot) · 4. Протоколы и шифры (TLSRef intermediate/modern) · 5. Перенаправление, HSTS, OCSP stapling, HTTP/2 · 6. ServerTokens, TRACE, заголовки, лишнее из коробки · 7. Require · 8. Basic (htpasswd) · 9. LDAP/AD · 10. Kerberos (mod_auth_gssapi) · 11. Клиентские сертификаты · 12. Связь с аутентификацией 1С · 13. mod_reqtimeout и лимиты запроса · 14. Безопасность обратного прокси · 15. Обновления безопасности · 16. Windows кратко · 17. Шаблоны · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### apache/03-proizvoditelnost-proksi-zhurnaly-monitoring.md

**Apache: производительность и настройка MPM, обратный прокси и балансировка, журналы, mod_status, мониторинг** (170 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Версии (Ubuntu 22.04/24.04/26.04, 2.4.69) · 2. MPM: prefork/worker/event, выбор по серверам · 3. Директивы MPM, умолчания Apache и Ubuntu, сообщения AH00484/AH00286/AH03490 · 4. Расчёт под память и процессор · 5. Соединения и таймауты (Timeout, KeepAlive, RequestReadTimeout, LimitRequest*) · 6. Сжатие (deflate, brotli) и кеширование (expires, cache) · 7. Обратный прокси (workers, параметры ProxyPass, X-Forwarded-*, mod_remoteip, ошибки 502/503/504) · 8. Прокси перед Redmine, NetBox, GlitchTip, Grafana, Loki · 9. Прокси перед публикацией 1С · 10. WebSocket · 11. Балансировка, hcheck, balancer-manager · 12. Журналы (форматы, %D/%^FB, logrotate, rotatelogs) · 13. mod_status и ?auto · 14. Мониторинг (Zabbix, apache_exporter, Alloy → Loki) · 15. Нагрузочная проверка (ab, wrk) · 16. Готовые наборы · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### apache/04-tipovye-problemy-i-apache-na-windows.md

**Apache: типовые проблемы (симптом → причина → решение), диагностика и Apache на Windows** (165 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Методика: как искать причину · 2. Инструменты диагностики · 3. Apache не запускается или не перечитывает конфигурацию · 4. Ошибки доступа и ограничения запроса: 403, 404, 401, 400, 408, 413, 414 · 5. Обратный прокси: 500, 502, 503, 504 · 6. TLS и HTTPS: сертификаты, рукопожатие, цепочка, SNI · 7. Kerberos (SPNEGO) · 8. Перегрузка и зависания — признаки · 9. Что проверять после обновления пакета apache2 (и ОС) · 10. Apache на Windows · Типичные ошибки · Быстрая шпаргалка · Источники · Что не удалось подтвердить

## iis/ — IIS 10: общее администрирование (справочник; у пользователя публикация 1С на Apache в Ubuntu)

> Раздел написан 20.10.2026 по плану пользователя (после `apache/`). Веер «3 + 3» с согласия пользователя (около 3,4 млн токенов): каждую статью писал один агент, независимо сверял другой. Сверено 745 утверждений, исправлено 16 ошибок, закрыто 44 пометок. Источники: документация IIS (исходники MicrosoftDocs/iis-docs), справочник конфигурации IIS, MS Learn по Windows Server и TLS, сроки поддержки Microsoft. Публикация 1С на IIS по-прежнему в `1c-windows/03`. На сервере не проверялось.

### iis/01-ustrojstvo-ustanovka-sajty-puly.md

**IIS 10: устройство, установка, сайты, приложения, пулы приложений, конфигурация и средства управления** (162 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Версии IIS 10 и выпуски Windows · 2. Устройство (HTTP.sys, WAS, W3SVC, w3wp, модули, обработчики) · 3. Установка роли и компонентов (Web-*, Server Core) · 4. Конфигурация (applicationHost.config, web.config, наследование, блокировка, /commit, ключи) · 5. Сайты и привязки · 6. Приложения и виртуальные каталоги · 7. Пулы приложений (удостоверение, переработка, простой, rapid-fail, веб-сад, профиль для 1С) · 8. Учётные записи и права NTFS · 9. Средства управления (Диспетчер IIS, appcmd, IISAdministration, WebAdministration, WMSVC) · 10. Резерв, история, перенос, общая конфигурация · 11. Обновления · 12. Где настройки IIS важны для 1С · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### iis/02-https-autentifikaciya-bezopasnost.md

**IIS: HTTPS и TLS, сертификаты, аутентификация (анонимная, Basic, Windows/Kerberos), авторизация и безопасность** (159 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Версии IIS 10.0 и компоненты · 2. Сертификаты (хранилища, импорт, привязка https, SNI, CCS, перепривязка) · 3. Протоколы и шифры Schannel (реестр Enabled/DisabledByDefault, TLS 1.3, Get-/Disable-TlsCipherSuite, CRYPT_PROTOCOL) · 4. HSTS и HTTP→HTTPS (hsts, httpRedirect, URL Rewrite) · 5. Заголовки и скрытие версии (customHeaders, frame-ancestors, removeServerHeader, DisableServerHeader) · 6. Аутентификация: общая схема и блокировка секций · 7. Анонимная · 8. Basic · 9. Windows: Negotiate/NTLM/Kerberos, SPN, useAppPoolCredentials, HTTP/2, большие билеты, делегирование для 1С, Extended Protection · 10. Клиентские сертификаты · 11. URL Authorization · 12. IP and Domain Restrictions · 13. Dynamic IP Restrictions · 14. Request Filtering · 15. Учётные записи пулов и минимальные права · 16. Журналы и аудит · 17. Сравнение с Apache · 18. Чек-лист · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

### iis/03-proizvoditelnost-arr-zhurnaly-diagnostika.md

**IIS: производительность, обратный прокси (ARR и URL Rewrite), сжатие и кеширование, журналы, FREB, мониторинг и типовые ошибки** (163 КБ) — проверено независимой сверкой 20.10.2026

Разделы: Кратко · 1. Обработка запроса и карта ограничений · 2. Пул под нагрузкой · 3. Соединения и таймауты · 4. Реестр http.sys · 5. Сжатие · 6. Кеширование · 7. URL Rewrite и ARR (обратный прокси, WebSocket, ферма) · 8. Журнал W3C · 9. HTTPERR · 10. FREB · 11. Журналы событий · 12. Мониторинг и счётчики · 13. Коды и подстатусы · 14. Порядок диагностики · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

## kafka/ — Apache Kafka: отдельный сервис и обмен с 1С

> Раздел написан 20.10.2026 по плану пользователя (после `iis/`), по его указанию — без веера агентов, экономно. Источники: документация и исходный код Apache Kafka ветки 4.4 (каталог `docs/` репозитория `apache/kafka`), страница загрузок, образ Docker `apache/kafka`; ИТС «Руководство разработчика» гл. 17.8 (сервисы интеграции) и гл. 32 (внешние компоненты), ИТС-мет о «1С:Шине» и RabbitMQ; Strimzi HTTP Bridge 1.2.0; открытые внешние компоненты. Документация «1С:Шины» (`its.1c.ru/db/esbdoc3`) под подпиской пользователя закрыта — использовано только оглавление. На сервере не проверялось.

### kafka/01-ustrojstvo-ustanovka-nastrojka.md

**Apache Kafka: устройство, версии, установка на Ubuntu и в Docker, базовая настройка** (43 КБ) — написано 20.10.2026 самостоятельно, без веера (по указанию пользователя), независимой сверки не было

Разделы: Кратко · 1. Что такое Kafka, Kafka или RabbitMQ для 1С · 2. Версии (4.4.0, 4.3.1, 4.2.2, 4.1.2), что изменилось с 4.0 и в 4.4 · 3. Подготовка Ubuntu (ресурсы, диск, дескрипторы, Java 17/21/25) · 4. Установка из архива под systemd (проверка архива, каталоги, `server.properties`, разметка хранилища, юнит, проверка, экран) · 5. Docker (`apache/kafka:4.4.0`, переменные `KAFKA_*`, compose для стенда, WSL2) · 6. Настройки тем для обмена 1С · 7. Типовые ошибки установки · 8. Что проверить

### kafka/02-bezopasnost-klaster-monitoring-obsluzhivanie.md

**Apache Kafka: безопасность, кластер, мониторинг, обслуживание и обновление** (42 КБ) — написано 20.10.2026 самостоятельно, без веера (по указанию пользователя), независимой сверки не было

Разделы: Кратко · 1. Модель безопасности · 2. TLS (EKU, PEM) · 3. SASL/SCRAM (`--add-scram`, JAAS в настройках, учётные записи систем, включение на работающем кластере, другие механизмы) · 4. ACL (`StandardAuthorizer`, `super.users`, набор для обмена 1С) · 5. Кластер (3 контроллера + брокеры, настройки, разметка `--standalone`/`--initial-controllers`, надёжность записи) · 6. Мониторинг (JMX, Prometheus JMX Exporter, kafka_exporter, журналы, проверки) · 7. Обслуживание (перезапуск, темы, сдвиг смещений, перенос разделов, резервирование) · 8. Обновление (`kafka-features.sh upgrade`, KIP-1170, с ZooKeeper) · 9. Контрольный список

### kafka/03-obmen-1c-s-kafka.md

**Обмен 1С с Apache Kafka: способы подключения, шаблон outbox, HTTP-мост, внешние компоненты** (51 КБ) — написано 20.10.2026 самостоятельно, без веера (по указанию пользователя), независимой сверки не было

Разделы: Кратко · 1. Что умеет платформа · 2. Сравнение способов (мост, компонента, посредник, «1С:Шина», CDC) · 3. Формат сообщения и JSON во встроенном языке · 4. Шаблон outbox в 1С (регистр-очередь, запись в транзакции, отправка) · 5. Идемпотентный приём · 6. Strimzi HTTP Bridge (настройки, защита, код отправки и приёма на встроенном языке, отладка) · 7. Внешние компоненты (Simple Kafka, изолированное подключение) · 8. Посредник и «1С:Шина» · 9. Мониторинг обмена · 10. Типовые ошибки

## rabbitmq/ — RabbitMQ: отдельный сервис и обмен с 1С

> Раздел написан 20.10.2026 по плану пользователя (после `kafka/`), без веера агентов. Источники: документация RabbitMQ 4.4 (`versioned_docs/version-4.4` репозитория `rabbitmq/rabbitmq-website`), сроки поддержки (`docusaurus.config.js`), схема настроек и справочник HTTP API из `rabbitmq/rabbitmq-server` (метка `v4.4.0`), примечания к выпуску 4.4.0, описание образа Docker; ИТС гл. 17.8, «Клиент-серверный вариант» гл. 2, «Руководство администратора» гл. 7.2 и прил. 3, ИТС-мет i8105995; статьи и репозитории сообщества (PinkRabbitMQ, 1CRabbitMQ, прямое подключение сервисов интеграции). На сервере не проверялось.

### rabbitmq/01-ustrojstvo-ustanovka-nastrojka.md

**RabbitMQ: устройство, версии, установка на Ubuntu и в Docker, базовая настройка** (33 КБ) — написано 20.10.2026 самостоятельно, без веера (по указанию пользователя), независимой сверки не было

Разделы: Кратко · 1. Понятия (vhost, обменники, очереди, кворумные очереди, подтверждения, DLX, политики) · 2. Версии и сроки поддержки (4.4.0, 4.3.6; что нового в 4.4.0) · 3. Установка из репозиториев команды RabbitMQ (Erlang, закрепление версии, файлы, дескрипторы, `rabbitmq.conf`, веб-интерфейс и первые пользователи, порты) · 4. Docker (`rabbitmq:4.4.0-management`, имя хоста, том) · 5. Топология и свойства для обмена 1С, адреса AMQP 1.0 · 6. Типовые ошибки установки · 7. Что проверить

### rabbitmq/02-bezopasnost-klaster-monitoring-obsluzhivanie.md

**RabbitMQ: безопасность, кластер, мониторинг, обслуживание и обновление** (29 КБ) — написано 20.10.2026 самостоятельно, без веера (по указанию пользователя), независимой сверки не было

Разделы: Кратко · 1. Пользователи, теги и права (`configure`/`write`/`read`, модель для обмена 1С, LDAP/OAuth 2/x.509) · 2. TLS (5671, `ssl_options.*`, веб-интерфейс по TLS) · 3. Защита узла · 4. Кластер (3 узла, Khepri, cookie, `classic_config`, `join_cluster`, кворумные очереди и предел доставок 20) · 5. Мониторинг (`rabbitmq_prometheus`, Grafana 10991, тревоги для обмена 1С, команды диагностики) · 6. Сторожа памяти и диска · 7. Резервирование (`export_definitions`) · 8. Обновление (пути веток, флаги, `drain`/`revive`, Docker) · 9. Контрольный список

### rabbitmq/03-obmen-1c-s-rabbitmq.md

**Обмен 1С с RabbitMQ: сервисы интеграции, «1С:Шина», внешние компоненты, HTTP API** (41 КБ) — написано 20.10.2026 самостоятельно, без веера (по указанию пользователя), независимой сверки не было

Разделы: Кратко · 1. Сравнение способов · 2. Сервисы интеграции платформы для администратора (устройство, очереди в базе, отправка и получение, «В транзакции», фоновые задания, настройки и права, техжурнал `SINTEG`) · 3. «1С:Шина» → RabbitMQ по ИТС · 4. Прямое подключение сервисов интеграции к RabbitMQ 4.x по AMQP 1.0 (приём сообщества, риски) · 5. Внешние компоненты AMQP 0-9-1 (PinkRabbitMQ, 1CRabbitMQ) · 6. HTTP API (публикация из 1С; почему не получать через `get`) · 7. Топология и права · 8. Мониторинг · 9. Типовые ошибки

## postgresql/ — PostgreSQL для 1С — тематические статьи

### postgresql/01-sborki-postgresql-dlya-1c-ustanovka.md

**Какой PostgreSQL нужен для 1С: сборки, совместимость версий, установка на Ubuntu** (207 КБ)

Разделы: Кратко — главные факты и команды · 1. Зачем 1С нужна особая сборка PostgreSQL · 2. Варианты СУБД и их статус на октябрь 2026 · 3. Версии и совместимость · 4. Подготовка ОС перед установкой · 5. Установка варианта (2): «PostgreSQL для 1С» от Postgres Professional · 6. Установка варианта (1): сборка PostgreSQL от фирмы «1С» · 7. Первичная настройка после установки · 8. Создание информационной базы 1С и проверка в `psql` · 9. Несколько версий и несколько кластеров на одном сервере · 10. Обновление и удаление · 11. Что не удалось подтвердить и что стоит дочитать · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники

### postgresql/02-postgresql-conf-tyuning-dlya-1c.md

**Настройка postgresql.conf, pg_hba.conf и ОС под нагрузку 1С** (228 КБ)

Разделы: Кратко · 1. Версии, сборки, расположение файлов · 2. Куда писать настройки и как их применять · 3. Официальные рекомендации: сводка и расхождения · 4. Параметры по группам · 5. Что изменилось в версиях 15–19 и что есть только в сборках для 1С · 6. Готовые примеры конфигурации (диски SSD) · 7. Тюнинг ОС под PostgreSQL для 1С · 8. pg_hba.conf: доступ и аутентификация · 9. Калькуляторы конфигурации и чем их результат отличается от рекомендаций для 1С · 10. Как проверять эффект настроек · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### postgresql/03-administrirovanie-psql-i-utility.md

**Администрирование PostgreSQL для 1С: psql, служебные утилиты, роли и базы, каталоги, журналы** (290 КБ)

Разделы: Кратко — главные факты и команды · 1. Версии и сборки на октябрь 2026 · 2. Раскладка каталогов и файлов · 3. psql: подключение · 4. psql: метакоманды · 5. psql: неинтерактивный запуск и выгрузка · 6. Управление сервером · 7. Служебные утилиты сервера · 8. Роли · 9. Базы данных · 10. Права, схемы, владельцы · 11. Табличные пространства · 12. Конфигурация «на лету» · 13. Сеансы · 14. Размеры и инвентаризация · 15. Журналы сервера · 16. Перенос каталога данных, смена порта, второй кластер · 17. Расширения · 18. Шпаргалка SQL администратора · 19. Особенности баз 1С · Типичные ошибки и подводные камни · Быстрая шпаргалка · Что не удалось подтвердить · Источники

### postgresql/04-rezervnoe-kopirovanie-i-vosstanovlenie.md

**Резервное копирование и восстановление PostgreSQL для баз 1С** (223 КБ) — проверено независимой сверкой 19.10.2026 (документация и исходный код PostgreSQL 14–18, документация «PostgreSQL для 1С» 16, документация сторонних инструментов)

Разделы: Кратко — 20 главных фактов и команд · 1. Карта методов, термины, пути · 2. Логические копии: pg_dump, pg_restore, pg_dumpall · 3. Физические копии: pg_basebackup · 4. Непрерывное архивирование WAL и восстановление на момент времени (PITR) · 5. pg_probackup · 6. pgBackRest, Barman, WAL-G — обзор и выбор · 7. Готовые скрипты и расписания · 8. Проверка резервных копий · 9. Специфика 1С · 10. Стратегии: RPO/RTO, правило 3-2-1, вынос копий, шифрование, сроки хранения · 11. Восстановление после аварий · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### postgresql/05-obsluzhivanie-vacuum-analyze-reindex.md

**Регламентное обслуживание PostgreSQL под 1С: VACUUM, ANALYZE, autovacuum, REINDEX, раздувание** (232 КБ) — проверено независимой сверкой 19.10.2026 (документация и исходный код PostgreSQL 14–18, документация «PostgreSQL для 1С» 16, документация сторонних инструментов)

Разделы: Кратко — 20 главных фактов и команд · 1. MVCC, «мёртвые» строки и раздувание · 2. VACUUM · 3. ANALYZE и статистика планировщика · 4. Autovacuum · 5. Что рекомендуют 1С и Postgres Professional: состав и периодичность · 6. REINDEX и reindexdb · 7. vacuumdb [PG] · 8. Возврат места: VACUUM FULL, CLUSTER, pg_repack · 9. Оценка раздувания · 10. Заморозка и переполнение счётчика транзакций (wraparound) · 11. Специфика 1С · 12. Рост WAL и места на диске; временные файлы · 13. Контрольные точки и фоновая запись: что наблюдать · 14. Целостность данных · 15. Готовые скрипты и расписание · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники

### postgresql/06-monitoring-i-diagnostika-zaprosov.md

**Мониторинг и диагностика PostgreSQL под 1С: статистика, блокировки, медленные запросы, EXPLAIN** (239 КБ) — проверено независимой сверкой 19.10.2026 (документация и исходный код PostgreSQL 14–18, документация «PostgreSQL для 1С» 16, документация сторонних инструментов)

Разделы: Кратко — 20 главных фактов и команд · 1. Подготовка: что включить заранее · 2. pg_stat_activity: кто подключён и что делает · 3. Блокировки · 4. pg_stat_statements: какие запросы съедают сервер · 5. Журнал PostgreSQL, auto_explain, pgBadger · 6. Статистические представления и ключевые метрики · 7. EXPLAIN: как получить и прочитать план · 8. Таблицы базы данных и объекты метаданных 1С · 9. Рабочий процесс «найти, почему 1С тормозит» · 10. Инструменты мониторинга · 11. Библиотека диагностических SQL-запросов · 12. Типичные ошибки и подводные камни · 13. Быстрая шпаргалка · 14. Источники

### postgresql/07-replikaciya-otkazoustojchivost-obnovlenie-versij.md

**Репликация, отказоустойчивость PostgreSQL для 1С и обновление версий** (226 КБ) — проверено независимой сверкой 19.10.2026 (документация и исходный код PostgreSQL 14–18, документация «PostgreSQL для 1С» 16, документация сторонних инструментов)

Разделы: Кратко — главные факты и команды · 1. Понятия и выбор схемы · 2. Потоковая физическая репликация: настройка пошагово · 3. Слоты репликации · 4. Асинхронная, синхронная и каскадная репликация · 5. Мониторинг репликации и отставания · 6. Переключение ролей вручную · 7. Автоматизация отказоустойчивости · 8. Как 1С подключается к СУБД и что происходит при переключении · 9. Пулеры соединений и 1С · 10. Механизм «Копии базы данных» платформы 1С и Дата акселератор · 11. Логическая репликация (публикации и подписки) и базы 1С · 12. Отказоустойчивый кластер 1С + отказоустойчивый PostgreSQL: типовые схемы · 13. Обновление минорной версии · 14. Обновление мажорной версии · 15. Обновление ОС и изменение правил сортировки (collation version mismatch) · 16. Перенос сервера БД на другой хост и переключение 1С · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники

### postgresql/08-tipovye-problemy-1c-postgresql.md

**Каталог типовых проблем связки 1С + PostgreSQL на Linux: симптом → причина → решение** (205 КБ) — проверено независимой сверкой 19.10.2026 (документация и исходный код PostgreSQL 14–18, документация «PostgreSQL для 1С» 16, документация сторонних инструментов)

Разделы: Кратко — главные факты и команды · 1. С чего начинать: как читать ошибку и где искать подробности · 2. Подключение и аутентификация · 3. Создание, удаление и загрузка информационной базы · 4. Расширения, типы данных и перенос дампов между сборками · 5. Память и лимиты ОС · 6. Производительность · 7. Блокировки · 8. Ошибки данных и обслуживания · 9. Ограничения и особенности типов данных · 10. WAL и место на диске · 11. После обновления перестало работать · 12. Отличия поведения 1С на PostgreSQL от MS SQL, которые принимают за ошибки · 13. Чек-лист «1С не подключается к базе» · 14. Чек-лист «1С тормозит на PostgreSQL» · Типичные ошибки и подводные камни (симптом → причина → решение) · Быстрая шпаргалка — «задача → команда» · Источники

### postgresql/09-arhitektura-postgresql-i-osnovy-sql-dlya-admina.md

**Архитектура PostgreSQL для администратора 1С: процессы, память, хранение, WAL, MVCC, блокировки, планировщик, безопасность** (231 КБ) — проверено независимой сверкой 19.10.2026 (документация и исходный код PostgreSQL 14–18, документация «PostgreSQL для 1С» 16, документация сторонних инструментов)

Разделы: Кратко — 20 главных фактов и команд · 1. Термины и версии · 2. Процессы · 3. Память · 4. Физическое хранение · 5. WAL и контрольные точки · 6. MVCC: версии строк, снимки, изоляция · 7. Блокировки · 8. Планировщик запросов · 9. Индексы · 10. Временные таблицы · 11. Кодировки, локали и типы mchar/mvarchar · 12. Безопасность · 13. Основы SQL для администратора · 14. Что изменилось по версиям 12 → 19 (значимое для администратора 1С) · Типичные ошибки и подводные камни · Быстрая шпаргалка · Источники

### postgresql/10-zaprosy-1c-v-postgresql.md

**Запросы 1С и PostgreSQL: как запрос языка 1С выполняется в СУБД, какие конструкции дорого стоят, как найти и исправить медленный запрос** (19.10.2026; по гл. 8 «Руководства разработчика», стандартам разработки ИТС о запросах и их оптимизации, методичкам и документации сборки)

Разделы: Кратко — 20 фактов · 1. Путь запроса: от текста 1С до PostgreSQL (что считает СУБД и что сервер 1С, что добавляется в SQL — «через точку», RLS, виртуальные таблицы; параметры сеанса платформы; типы `mvarchar`/`mchar`; блокировки и изоляция, `ДЛЯ ИЗМЕНЕНИЯ`) · 2. Конструкции языка запросов и их цена на PostgreSQL (виртуальные таблицы и итоги, соединения и число таблиц, составные типы и `ВЫРАЗИТЬ`, условия и индексы, `ПОДОБНО`, группировка и объединение, временные таблицы со стороны СУБД — `fasttrun`, `plantuner`, `temp_buffers`, `max_locks_per_transaction`) · 3. Два частых случая («то быстро, то медленно»; ошибка регулярного выражения в журнале) · 4. Как найти медленный запрос и связать его с кодом · 5. Что может администратор, а что — только разработчик · Типичные ошибки · Шпаргалка · Источники · Что не удалось подтвердить

## its-docs/ — Конспекты документации 1С:Предприятие 8.3.27 (ИТС): adm-* — «Руководство администратора», cs-* — «Клиент-серверный вариант», dev-* — «Руководство разработчика» (все 39 глав и 13 приложений; в начале каждого конспекта указано, что прочитано полностью, а что обзорно)

### its-docs/adm-gl01-trebovaniya.md

**ИТС-конспект: Руководство администратора — Глава 1. Требования к аппаратуре и программному обеспечению** (55 КБ)

Разделы: 1.1. Требования к аппаратуре · 1.2. Использование энергосберегающих режимов работы компьютера · 1.3. Поддерживаемые веб-серверы · 1.4. Прочие требования · 1.5. Ограничения · 1.6. Варианты платформы и лицензий · Что важно администратору Linux

### its-docs/adm-gl02-ustanovka-p1.md

**ИТС-конспект: Руководство администратора — Глава 2. Установка системы «1С:Предприятие» (часть 1 из 2)** (62 КБ)

Разделы: 2.1. Общая информация · 2.2. Варианты установки · 2.3. Установка в ОС Linux · 2.4. Установка в ОС macOS · 2.5. Установка в ОС Windows · 2.6. Типовые сценарии установки «1С:Предприятия» · Что важно администратору Linux

### its-docs/adm-gl02-ustanovka-p2.md

**ИТС-конспект: Руководство администратора — Глава 2. Установка системы «1С:Предприятие» (часть 2 из 2)** (35 КБ)

Разделы: 2.6.3. (окончание раздела; начало — в части 1) · 2.7. Рекомендации по развертыванию системы · 2.8. Установка и настройка дополнительного программного обеспечения · Что важно администратору Linux

### its-docs/adm-gl04-zapusk-komponentov-p1.md

**ИТС-конспект: Руководство администратора — Глава 4. Запуск компонентов системы (часть 1 из 2)** (72 КБ)

Разделы: 4.1. Общая информация · 4.2. Режимы работы системы · 4.3. Запуск клиентского приложения или конфигуратора · Что важно администратору Linux

### its-docs/adm-gl04-zapusk-komponentov-p2.md

**ИТС-конспект: Руководство администратора — Глава 4. Запуск компонентов системы (часть 2 из 2)** (39 КБ)

Разделы: 4.3.9. Использование сертификатов · 4.4. Перезапуск системы · Что важно администратору Linux

### its-docs/adm-gl05-spisok-infobaz.md

**ИТС-конспект: Руководство администратора — Глава 5. Ведение списка информационных баз** (63 КБ)

Разделы: 5.1. Общая информация · 5.2. Добавление информационной базы · 5.3. Редактирование информационной базы · 5.4. Удаление информационной базы из списка · 5.5. Порядок информационных баз в списке · 5.6. Ведение иерархического списка информационных баз · 5.7. Настройка окна запуска · 5.8. Списки общих информационных баз · Что важно администратору Linux

### its-docs/adm-gl06-administrirovanie-ib-p1.md

**ИТС-конспект: Руководство администратора — Глава 6. Администрирование информационной базы (часть 1 из 3)** (65 КБ)

Разделы: 6.1. Общая информация · 6.2. Ведение списка пользователей · Что важно администратору Linux

### its-docs/adm-gl06-administrirovanie-ib-p2.md

**ИТС-конспект: Руководство администратора — Глава 6. Администрирование информационной базы (часть 2 из 3)** (81 КБ)

Разделы: 6.2.10.6. С помощью JWT · 6.2.10.7. По QR-коду · 6.2.10.8. Через электронную почту · 6.2.10.9. Двухфакторная аутентификация · 6.2.10.10. Использование биометрии для быстрого входа в мобильном клиенте · 6.2.11. Пользователи и расширения · 6.3. Список активных пользователей · 6.4. Работа с сеансами · 6.5. Региональные установки информационной базы · 6.6. Параметры информационной базы · Что важно администратору Linux

### its-docs/adm-gl06-administrirovanie-ib-p3.md

**ИТС-конспект: Руководство администратора — Глава 6. Администрирование информационной базы (часть 3 из 3)** (78 КБ)

Разделы: 6.7. Выгрузка информационной базы в файл · 6.8. Загрузка информационной базы из файла · 6.9. Резервное копирование информационной базы · 6.10. Тестирование и исправление информационной базы · 6.11. Отмена назначения главного узла распределенной информационной базы · 6.12. Удаление данных области данных или информационной базы · 6.13. Журнал регистрации · 6.14. Технологический журнал · 6.15. Контроль ссылочной целостности · 6.16. Стандартные функции · Что важно администратору Linux

### its-docs/adm-gl07-avtonomnyj-server.md

**ИТС-конспект: Руководство администратора — Глава 7. Автономный сервер** (95 КБ)

Разделы: 7.1. Общая информация · 7.2. Особенности и ограничения · 7.3. Использование механизма · 7.4. Примеры управления и запуска автономного сервера · Сводный указатель: ключи и команды, упомянутые в главе 7 · Замеченные неясности и расхождения в источнике · Что важно администратору Linux

### its-docs/adm-gl08-veb-servery-p1.md

**ИТС-конспект: Руководство администратора — Глава 8. Настройка веб-серверов для работы с «1С:Предприятием» (часть 1 из 2)** (72 КБ)

Разделы: 8.1. Общая информация · 8.2. Общие требования · 8.3. Виды публикации · 8.4. Настройка поддержки клиентского приложения · 8.5. Настройка поддержки Web-сервисов · 8.6. Настройка поддержки стандартного интерфейса OData · 8.7. Настройка поддержки HTTP-сервисов · Сводка: параметры `webinst`, встречающиеся в этой части · Сводка: элементы и атрибуты `default.vrd`, упомянутые в этой части · Что важно администратору Linux

### its-docs/adm-gl08-veb-servery-p2.md

**ИТС-конспект: Руководство администратора — Глава 8. Настройка веб-серверов для работы с «1С:Предприятием» (часть 2 из 2)** (67 КБ)

Разделы: 8.7. Публикация HTTP-сервисов (окончание раздела) · 8.8. Настройка поддержки OpenID-аутентификации · 8.9. Безопасность при работе через Интернет · 8.10. Особенности настройки веб-серверов · Что важно администратору Linux

### its-docs/adm-gl10-zashchita-licenzii-p1.md

**ИТС-конспект: Руководство администратора — Глава 10. Защита от несанкционированного использования: особенности и настройка (лицензирование) (часть 1 из 2)** (75 КБ)

Разделы: 10.1. Общая информация · 10.2. Система защиты HASP · 10.3. Система программного лицензирования · Что важно администратору Linux

### its-docs/adm-gl10-zashchita-licenzii-p2.md

**ИТС-конспект: Руководство администратора — Глава 10. Защита от несанкционированного использования: особенности и настройка (лицензирование) (часть 2 из 2)** (59 КБ)

Разделы: 10.3 (окончание раздела; заголовок — в части 1) · 10.4. Определение возможности запуска · 10.5. Защита от неправомерного использования прикладных решений · Что важно администратору Linux

### its-docs/adm-gl11-gl12-pr02-pr05-obnovlenie-udalenie-zhurnal-oshibki.md

**ИТС-конспект: Руководство администратора — Глава 11 «Обновление системы», Глава 12 «Удаление системы», Приложение 2 «Описание элементов журнала регистрации», Приложение 5 «Обработка ошибок»** (60 КБ)

Разделы: О конспекте · Глава 11. Обновление системы · Глава 12. Удаление системы · Приложение 2. Описание элементов журнала регистрации · Приложение 5. Обработка ошибок · Что важно администратору Linux

### its-docs/adm-pr01-katalog-ustanovki.md

**ИТС-конспект: Руководство администратора — Приложение 1. Структура каталога установки и назначение каталогов и файлов** (38 КБ)

Разделы: 1.1. Структура каталогов установки · 1.2. Назначение файлов · 1.3. Конфигурационные файлы: расположение и поиск · Что важно администратору Linux

### its-docs/adm-pr03-sluzhebnye-fajly-p1.md

**ИТС-конспект: Руководство администратора — Приложение 3. Описание и расположение служебных файлов (conf.cfg, logcfg.xml, default.vrd, nethasp.ini и др.) (часть 1 из 6)** (81 КБ)

Разделы: Сводка файлов этой части · 3.1. Общая информация · 3.2. *.1ccr · 3.3. *.mft · 3.4. *.v8i · 3.5. 1cescmn.cfg · 3.6. 1cestart.cfg · 3.7. 1CV8Clst.lst · 3.8. 1cv8conn.pfl · 3.9. 1cv8wsrv.lst · 3.10. adminstall.cfg · 3.11. agentbasedir.json · 3.12. appsrvrs.lst · 3.13. cacertnx.pem и cacert.pem · 3.14. cfgrepo.conf · 3.15. ClientUpdate.cfg · 3.16. comcntrcfg.xml · 3.17. conf.cfg · Что важно администратору Linux

### its-docs/adm-pr03-sluzhebnye-fajly-p2.md

**ИТС-конспект: Руководство администратора — Приложение 3. Описание и расположение служебных файлов (conf.cfg, logcfg.xml, default.vrd, nethasp.ini и др.) (часть 2 из 6)** (82 КБ)

Разделы: 3.17. conf.cfg — параметры (продолжение, 3.17.11–3.17.23) · 3.18. ConfigDumpInfo.xml · 3.19. debugcfg.xml · 3.20. def.usr · 3.21. default.vrd · Что важно администратору Linux

### its-docs/adm-pr03-sluzhebnye-fajly-p3.md

**ИТС-конспект: Руководство администратора — Приложение 3. Описание и расположение служебных файлов (conf.cfg, logcfg.xml, default.vrd, nethasp.ini и др.) (часть 3 из 6)** (101 КБ)

Разделы: 3.21.9. (окончание раздела о настройке аутентификации OpenID Connect; заголовок и начало раздела — в предыдущей части) · 3.21.10. Элемент `<exitURL>` · 3.21.11. Элемент `<standardOData>` · 3.21.12. Элемент `<analytics>` · 3.21.13. Элемент `<progressiveWebApplication>` · 3.21.14. Элемент `<accessTokenAuthentication>` · 3.21.15. Элемент `<authentication>` · 3.21.16. Элемент `<mobileApps>` · 3.24.1. Общее описание · 3.24.2. Структура конфигурационного файла · Что важно администратору Linux

### its-docs/adm-pr03-sluzhebnye-fajly-p4.md

**ИТС-конспект: Руководство администратора — Приложение 3. Описание и расположение служебных файлов (conf.cfg, logcfg.xml, default.vrd, nethasp.ini и др.) (часть 4 из 6)** (88 КБ)

Разделы: (продолжение раздела из части 3) Примеры logcfg.xml: контекст исполнения и блокировки · 3.24.2.4.3. Описание свойства Level · 3.24.2.4.4. Значения свойства Func · 3.24.2.4.5. Описание свойства res события LIC · 3.24.2.4.6. Описание свойства Descr · 3.24.2.4.7. Описание свойства Event · 3.24.2.4.8. Описание свойства Txt · 3.24.2.5. Элемент `<dump>` · 3.24.2.6. Элемент `<leaks>` · Что важно администратору Linux

### its-docs/adm-pr03-sluzhebnye-fajly-p5.md

**ИТС-конспект: Руководство администратора — Приложение 3. Описание и расположение служебных файлов (conf.cfg, logcfg.xml, default.vrd, nethasp.ini и др.) (часть 5 из 6)** (73 КБ)

Разделы: 3.24 (продолжение). Файл настройки технологического журнала logcfg.xml · 3.25. nethasp.ini · 3.26. nhsrv.ini · 3.27. rescntsrv.lst · 3.28. ring-commands.cfg · 3.29. swpuser.ini · 3.30. testcfg.xml · 3.31. Файл списка объектов · Что важно администратору Linux

### its-docs/adm-pr03-sluzhebnye-fajly-p6.md

**ИТС-конспект: Руководство администратора — Приложение 3. Описание и расположение служебных файлов (conf.cfg, logcfg.xml, default.vrd, nethasp.ini и др.) (часть 6 из 6)** (81 КБ)

Разделы: 3.31 (окончание). Элемент `<Subsystem>` и примеры файла с перечнем объектов конфигурации · 3.32. Файл настроек объединения · 3.33. Файл различий в выгрузках конфигураций · 3.34. Конфигурационный файл автономного сервера · 3.35. Конфигурационный файл настройки пользователей сервера отладки · Что важно администратору Linux

### its-docs/adm-pr04-komandnye-stroki-utilit-p1.md

**ИТС-конспект: Руководство администратора — Приложение 4. Командные строки запуска компонентов системы и описание дополнительных утилит (ragent, rmngr, rphost, ras, rac, ibcmd, ibsrv, crserver, webinst и др.) (часть 1 из 3)** (79 КБ)

Разделы: 4.1. Утилита тестирования (chdbfl) · 4.2. Утилита контроля целостности (ci) · 4.3. Утилита преобразования (cnvdbfl) · 4.4. Утилита ring · 4.5. Утилита лицензирования (ring license) · 4.6. Утилита административной консоли (1cv8a) · Что важно администратору Linux

### its-docs/adm-pr04-komandnye-stroki-utilit-p2.md

**ИТС-конспект: Руководство администратора — Приложение 4. Командные строки запуска компонентов системы и описание дополнительных утилит (ragent, rmngr, rphost, ras, rac, ibcmd, ibsrv, crserver, webinst и др.) (часть 2 из 3)** (77 КБ)

Разделы: 4.7. Работа конфигуратора в режиме агента · 4.8. Агент клиентского приложения (1cecla) · 4.9. Автономный сервер (ibsrv) · 4.10. Утилита администрирования автономного сервера (ibcmd) · Что важно администратору Linux

### its-docs/adm-pr04-komandnye-stroki-utilit-p3.md

**ИТС-конспект: Руководство администратора — Приложение 4. Командные строки запуска компонентов системы и описание дополнительных утилит (ragent, rmngr, rphost, ras, rac, ibcmd, ibsrv, crserver, webinst и др.) (часть 3 из 3)** (85 КБ)

Разделы: 4.10.3. Режим server · 4.10.4. Режим infobase · 4.10.5. Режим config · 4.10.6. Режим extension · 4.10.7. Режим mobile-app · 4.10.8. Режим mobile-client · 4.10.9. Режим session · 4.10.10. Режим lock · 4.10.11. Режим eventlog · 4.10.12. Режим binary-data-storage · 4.11. Сервер отладки (dbgs) · 4.12. Агент кластера (ragent) · 4.13. Сервер администрирования (ras) · 4.14. Утилита публикации на веб-сервере (webinst) · Что важно администратору Linux

### its-docs/adm-pr06-internet-servisy-administrirovaniya.md

**ИТС-конспект: Руководство администратора — Приложение 6. Вспомогательные Интернет-сервисы администрирования** (93 КБ)

Разделы: Обзор приложения · 6.1. Интернет-сервис получения списка общих информационных баз · 6.2. Интернет-сервис получения дистрибутива клиентского приложения · 6.3. Web-сервис внешнего управления сеансами · 6.4. HTTP-сервис получения параметров производительности · Неясности и расхождения в самом источнике · Что важно администратору Linux

### its-docs/adm-pr07-parametry-zapuska-1cv8-p1.md

**ИТС-конспект: Руководство администратора — Приложение 7. Параметры командной строки запуска «1С:Предприятия» (часть 1 из 3)** (115 КБ)

Разделы: 7.1. Общая информация об интерфейсе командной строки системы · 7.2. Выбор режима запуска · 7.3. Общие команды запуска · 7.4. Команды пакетного режима запуска конфигуратора · Что важно администратору Linux

### its-docs/adm-pr07-parametry-zapuska-1cv8-p2.md

**ИТС-конспект: Руководство администратора — Приложение 7. Параметры командной строки запуска «1С:Предприятия» (часть 2 из 3)** (80 КБ)

Разделы: О чём эта часть · 7.4.5. Проверки конфигурации и расширений · 7.4.6. Поддержка конфигурации · 7.4.7. Команды создания файла поставки и обновления · 7.4.8. Внешние обработки (отчеты) · 7.4.9. Мобильное приложение · 7.4.10. Мобильный клиент · 7.4.11. Журнал регистрации · 7.4.12. Удаление данных · 7.4.13. Предопределенные данные · 7.4.14. Распределенная информационная база · 7.4.15. Команды работы с хранилищем конфигурации · 7.4.16. Команды работы в режиме агента · 7.4.17. Прочие параметры · 7.5. Пакетный режим запуска клиентского приложения · 7.6. Регистрация «1С:Предприятия» в качестве OLE-Automation-сервера · 7.7. Строка соединения с информационной базой · Что важно администратору Linux

### its-docs/adm-pr07-parametry-zapuska-1cv8-p3.md

**ИТС-конспект: Руководство администратора — Приложение 7. Параметры командной строки запуска «1С:Предприятия» (часть 3 из 3)** (33 КБ)

Разделы: 7.7.2. Общий набор параметров · 7.7.3. Параметры для файлового варианта информационной базы · 7.7.4. Параметры для клиент-серверного варианта информационной базы · 7.8. Командная строка веб-клиента · 7.9. Командная строка мобильной версии · Что важно администратору Linux

### its-docs/cs-gl01-trebovaniya.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 1. Требования к аппаратуре и программному обеспечению** (44 КБ)

Разделы: Содержание · Глава 1. Вводные положения · 1.1. 32-разрядный сервер · 1.2. 64-разрядный сервер · 1.3. Общие требования для клиент-серверного варианта работы · 1.4. Использование энергосберегающих режимов работы компьютера · 1.5. Поддерживаемые СУБД · Сводная таблица по СУБД (собрана из разделов 1.1, 1.2.1 и 1.5) · Что важно администратору Linux

### its-docs/cs-gl02-klient-servernyj-variant-p1.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 2. Клиент-серверный вариант работы (кластер серверов) (часть 1 из 3)** (86 КБ)

Разделы: 2.1. Общее устройство системы · 2.2. Устройство кластера серверов · 2.2.1. Общие понятия · 2.2.2. Взаимодействие клиентского приложения с кластером серверов · 2.2.3. Сервисы кластера · 2.2.3.1. Список сервисов · 2.2.3.2. Изменение положения каталогов с данными сервисов · 2.2.4. Сеансы и соединения · 2.2.4.1. Общая информация · 2.2.4.2. Виды соединений · 2.2.4.2.1. Соединения с информационной базой · 2.2.4.2.2. Служебные соединения · 2.2.4.3. Виды сеансов · 2.2.4.4. Внешнее управление сеансами · 2.2.5. Отказоустойчивый кластер · 2.2.5.1. Транзакционность сеансовых данных · 2.2.5.2. Повтор последнего вызова · 2.2.5.3. Повтор интерактивного действия · 2.2.5.4. Резервирование рабочих процессов · 2.2.5.5. Уровень отказоустойчивости · 2.2.5.6. Система отслеживания разрыва соединений · Что важно администратору Linux

### its-docs/cs-gl02-klient-servernyj-variant-p2.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 2. Клиент-серверный вариант работы (кластер серверов) (часть 2 из 3)** (86 КБ)

Разделы: 2.2.6. Масштабируемость кластера серверов · 2.2.7. Балансировка нагрузки в кластере · 2.2.8. Профили безопасности · Что важно администратору Linux

### its-docs/cs-gl02-klient-servernyj-variant-p3.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 2. Клиент-серверный вариант работы (кластер серверов) (часть 3 из 3)** (63 КБ)

Разделы: 2.2.8. Профили безопасности (окончание) · 2.2.9. Безопасность кластера серверов · 2.2.10. Механизм блокировок информационной базы · 2.2.11. Статистика загруженности рабочих процессов · 2.2.12. Система мониторинга кластера · 2.2.13. Расположение служебных файлов менеджера кластера · 2.3. Особенности работы в ОС Linux · Что важно администратору Linux

### its-docs/cs-gl03-ustanovka-komponentov-p1.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 3. Установка компонентов системы (часть 1 из 2)** (72 КБ)

Разделы: Содержание · 3.1. Установка сервера «1С:Предприятия» · 3.1.1. Общая информация · 3.1.2. Варианты установки · 3.1.3. Установка в ОС Linux · 3.1.3.1. Правила именования файлов дистрибутива · 3.1.3.2. Установка с использованием программы установки · 3.1.3.2.1. Описание программы установки · 3.1.3.2.2. Пакетная установка · 3.1.3.3. Установка с использованием пакетного менеджера · 3.1.4. Установка в ОС Windows · 3.1.4.1. Доступные программы установки · 3.1.4.2. Общие сведения о программе установки · 3.1.4.3. Общая информация · 3.1.4.3.1. Определение режима установки · 3.1.4.3.2. Приветствие · 3.1.4.3.3. Выбор компонентов · 3.1.4.3.4. Выбор языка интерфейса по умолчанию · 3.1.4.3.5. Установка сервера «1С:Предприятия» · 3.1.4.3.6. Начало установки · 3.1.4.3.7. Установка драйвера защиты · 3.1.4.3.8. Завершающие действия · 3.1.4.4. Особенности регистрации компонент · 3.1.5. Типовые сценарии установки «1С:Предприятия» · 3.1.5.1. Для ОС Linux · 3.1.5.1.1. Общая информация · 3.1.5.1.2. Установка рабочего сервера · 3.1.5.1.3. Добавление сервера в кластер серверов · 3.1.5.1.4. Работа веб-клиента · 3.1.5.2. Для ОС Windows · 3.1.5.2.1. Общая информация · 3.1.5.2.2. Установка главного сервера кластера · 3.1.5.2.3. Добавление сервера в кластер серверов · 3.1.5.3. Настройки Дата акселератора · 3.1.6. Установка и настройка дополнительного программного обеспечения · 3.1.6.1. Для ОС Windows · 3.1.6.1.1. Создание имени службы сервера для Kerberos-аутентификации · 3.1.6.2. Для ОС Linux · 3.1.6.2.1. Настройка Kerberos-аутентификации · Что важно администратору Linux

### its-docs/cs-gl03-ustanovka-komponentov-p2.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 3. Установка компонентов системы (часть 2 из 2)** (37 КБ)

Разделы: Настройка центрального сервера кластера «1С:Предприятия» (подраздел без номера; Kerberos на Linux) · 3.2. Установка серверов баз данных · 3.2.1. Общая информация · 3.2.2. Установка IBM Db2 · 3.2.3. Установка Microsoft SQL Server · 3.2.4. Установка Oracle Database · 3.2.5. Установка PostgreSQL · Что важно администратору Linux

### its-docs/cs-gl04-zapusk-komponentov.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 4. Запуск компонентов системы** (47 КБ)

Разделы: 4.1. Общая информация · 4.2. Запуск агента сервера · 4.3. Обеспечение совместной работы нескольких серверных процессов · Что важно администратору Linux

### its-docs/cs-gl05-administrirovanie-klastera-p1.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 5. Администрирование (кластер серверов, утилиты администрирования) (часть 1 из 3)** (84 КБ)

Разделы: Охват этой части · 5.1. Администрирование информационной базы · 5.2. Администрирование кластера серверов · Что важно администратору Linux

### its-docs/cs-gl05-administrirovanie-klastera-p2.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 5. Администрирование (кластер серверов, утилиты администрирования) (часть 2 из 3)** (85 КБ)

Разделы: Охват этой части · 5.2.8. Работа со списком администраторов кластера · 5.2.9. Просмотр списка менеджеров кластера · 5.2.10. Просмотр списка рабочих процессов · 5.2.11. Работа со списком сеансов · 5.2.12. Работа со списком соединений · 5.2.13. Работа со списком блокировок · 5.2.14. Работа со списком профилей безопасности · 5.2.15. Работа с механизмом управления потреблением ресурсов · Что важно администратору Linux

### its-docs/cs-gl05-administrirovanie-klastera-p3.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 5. Администрирование (кластер серверов, утилиты администрирования) (часть 3 из 3)** (97 КБ)

Разделы: 5.2.15.2.3. Удаление настройки ограничения · 5.3. Программные средства администрирования кластера серверов · 5.4. Хранилище двоичных данных · 5.5. Администрирование СУБД · Что важно администратору Linux

### its-docs/cs-gl06-gl07-pr01-pr03-obnovlenie-licenzii-cron-bezopasnost.md

**ИТС-конспект: Клиент-серверный вариант. Руководство администратора — Глава 6 «Обновление кластера серверов», Глава 7 «Удаление системы», Приложение 1 «Формат строки описания лицензии», Приложение 2 «Формат строки расписания перезапуска рабочих процессов (cron-формат)», Приложение 3 «Рекомендации по обеспечению безопасности кластера серверов»** (57 КБ)

Разделы: Состав конспекта · Глава 6. Обновление кластера серверов · Глава 7. Удаление системы · Приложение 1. Формат строки описания лицензии · Приложение 2. Формат строки расписания перезапуска рабочих процессов (cron-формат) · Приложение 3. Рекомендации по обеспечению безопасности кластера серверов · Что важно администратору Linux

### its-docs/usr-rukovodstvo-polzovatelya-i-taksi.md

**ИТС-конспект: «Руководство пользователя» и «Руководство пользователя. Интерфейс „Такси“» (8.3.27) — что нужно администратору** (19.10.2026; полностью — главы об установке, запуске, низкой скорости, системных параметрах, веб-клиенте и системе взаимодействия, остальное — обзорно)

Разделы: 1. Что это за книги · 2. Установка клиента (компоненты Windows, HASP, macOS, Linux, библиотеки, автоудаление версий) · 3. Запуск и вход (разрядность, параметры базы в списке) · 4. Режим низкой скорости соединения · 5. Системные параметры клиента («Режим технического специалиста», отладка) · 6. Что пользователь может прислать в поддержку («О программе», отчёт об ошибке с дампом) · 7. Прочее (блокировка объекта, временная блокировка, история данных, «1С:Аналитика») · 8. Веб-клиент (браузеры, лицензия на вкладку, что требует HTTPS, расширения, Kerberos в Firefox, PWA) · 9. Система взаимодействия глазами пользователя (WebSocket, «1С:Диалог», видеозвонки, «оповещения и запуск») · 10. Обзорно — остальное · Что важно администратору — коротко

### its-docs/otlichiya-8.5.1-ot-8.3.27.md

**ИТС-конспект: отличия документации 1С:Предприятие 8.5.1 от 8.3.27** (78 КБ)

Разделы: Как читать этот конспект · Кратко: главное для администратора Linux · 1. Системные требования (подробно) · 2. Установка и запуск под Linux (подробно) · 3. Лицензирование (подробно) · 4. Командная строка (подробно) · 5. Служебные файлы (подробно) · 6. Изменения по главам: «Руководство администратора» · 7. Изменения по главам: «Клиент-серверный вариант. Руководство администратора» · 8. Отфильтрованный шум · 9. Что сравнение не позволяет установить (проверить вручную)

### its-docs/dev-rukovodstvo-razrabotchika-vyborka.md

**«Руководство разработчика» 8.3.27 — выборка для администратора** (18 КБ)

Разделы: Как добраться до текста · Глава 9. Блокировки и уровни изоляции по СУБД · Приложение 8, раздел 8.6. Особенности PostgreSQL · Глава 4. Числа · Глава 17, раздел 17.7.3. Повторное использование сеансов интернет-сервисов · Глава 17. Проверка сертификата сервера при HTTPS · Глава 22. Журнал регистрации: уровни · Глава 23. Криптография в Linux · Глава 31. Отладка · Глава 32. Внешние компоненты · Глава 33. Кроссплатформенная разработка · Приложение 7, раздел 7.7. Клиентское приложение в Linux · Глава 37, раздел 37.4. Сервер хранилища конфигурации · Чего в прочитанных главах нет

### its-docs/dev-gl01-koncepciya.md

**ИТС-конспект: Руководство разработчика — Введение и Глава 1. Концепция системы** (12 КБ)

Разделы: Введение: как устроена книга · 1.1–1.2. Конфигурируемость и два этапа работы · 1.3. Основные понятия · 1.4. Варианты работы и клиентские приложения · 1.5. Средства разработки

### its-docs/dev-gl02-rabota-s-konfiguraciej.md

**ИТС-конспект: Руководство разработчика — Глава 2. Работа с конфигурацией** (19 КБ)

Разделы: 2.1–2.13. Работа в конфигураторе (по оглавлению) · 2.14. Работа с конфигурацией базы данных · 2.15. Запуск «1С:Предприятия» из конфигуратора · 2.16. Выгрузка и загрузка файлов конфигурации · 2.17. Выгрузка и загрузка конфигурации в файлы (XML) · 2.18–2.24. Прочее · 2.25. Работа с конфигурацией из встроенного языка

### its-docs/dev-gl05-obekty-konfiguracii.md

**ИТС-конспект: Руководство разработчика — Глава 5. Объекты конфигурации** (25 КБ)

Разделы: 5.1. Свойства конфигурации · 5.2–5.4. Модули приложения, внешнего соединения, сеанса · 5.5. Ветвь «Общие» · 5.6. Общие свойства объектов конфигурации (обзорно) · 5.7–5.14. Прикладные объекты (обзорно) · Что не законспектировано

### its-docs/dev-gl09-rabota-s-dannymi.md

**ИТС-конспект: Руководство разработчика — Глава 9. Работа с данными** (27 КБ)

Разделы: 9.1. Механизм транзакций · 9.2. Блокировки · 9.3. Монопольный режим · 9.4. Дополнительные индексы объектов метаданных · 9.5. Динамические выборки

### its-docs/dev-gl15-obmen-dannymi-rib.md

**ИТС-конспект: Руководство разработчика — Глава 15. Механизмы обмена данными (распределённые информационные базы)** (15 КБ)

Разделы: 15.1–15.2. Универсальные механизмы обмена данными (обзорно) · 15.3. Распределённые информационные базы · См. также

### its-docs/dev-gl17-integraciya.md

**ИТС-конспект: Руководство разработчика — Глава 17. Интеграция с внешними системами** (19 КБ)

Разделы: 17.1. Способы интеграции · 17.2. Web-сервисы (SOAP) · 17.3. HTTP-сервисы · 17.4. Стандартный интерфейс OData · 17.5. WebSocket (обзорно) · 17.6. Внешние источники данных · 17.7. Повторное использование сеансов интернет-сервисов · 17.8. Сервисы интеграции (обзорно) · 17.9. Буфер обмена (обзорно)

### its-docs/dev-gl19-gl20-zadaniya-polnotekstovyj-poisk.md

**ИТС-конспект: Руководство разработчика — Глава 19. Механизм заданий; Глава 20. Полнотекстовый поиск в данных** (23 КБ)

Разделы: Глава 19. Механизм заданий · 19.1. Общая информация · 19.2. Фоновые задания · 19.3. Регламентные задания · 19.4. Где выполняются задания · 19.5. Метаданные регламентного задания · Глава 20. Механизм полнотекстового поиска в данных · 20.1. Общие сведения · 20.2. Программный интерфейс · 20.3. Дополнительные словари (только версия 1) · 20.4. Поддержание актуальности индекса · 20.5. Мобильная платформа · См. также

### its-docs/dev-gl21-gl25-vremennoe-hranilishche-istoriya-dannyh.md

**ИТС-конспект: Руководство разработчика — Глава 21. Временное хранилище, файлы и картинки; Глава 25. История данных** (18 КБ)

Разделы: Глава 21. Временное хранилище, работа с файлами и картинками · 21.1. Временное хранилище · 21.3. Методы (обзорно) · 21.4. Картинки (обзорно) · Глава 25. История данных · 25.1. Что это · 25.2. Устройство · 25.3. Программный интерфейс (свойство глобального контекста `ИсторияДанных`)

### its-docs/dev-gl22-zhurnal-registracii.md

**ИТС-конспект: Руководство разработчика — Глава 22. Журнал регистрации** (12 КБ)

Разделы: 22.1. Общая информация · 22.2. Управление детализацией · 22.3. Запись событий · 22.4. Управление регистрацией событий · 22.5. События аудита прав доступа · 22.6. Получение записей журнала · 22.7. Дополнительные методы

### its-docs/dev-gl23-gl32-gl33-kriptografiya-vneshnie-komponenty-linux.md

**ИТС-конспект: Руководство разработчика — Глава 23. Механизм криптографии, Глава 32. Внешние компоненты, Глава 33. Кроссплатформенные прикладные решения** (20 КБ)

Разделы: Глава 23. Механизм криптографии · Общие положения · Модули криптографии (23.5) — важно для Linux · Шифрование и подпись · Сертификаты (23.4) · Глава 32. Внешние компоненты · Технологии и где что работает · Изолированное и неизолированное подключение · На сервере (32.4) · На клиенте · Глава 33. Особенности разработки кроссплатформенных прикладных решений

### its-docs/dev-gl24-razdelenie-dannyh.md

**ИТС-конспект: Руководство разработчика — Глава 24. Механизм разделения данных** (14 КБ)

Разделы: 24.1. Общая информация · 24.2. Свойства общего реквизита · 24.3. Несколько разделителей · 24.4. Установка разделителей при запуске · 24.5. Безопасный режим разделения данных · 24.6. Удаление области данных · 24.7. Особенности поведения объектов

### its-docs/dev-gl26-kopii-bazy-dannyh.md

**ИТС-конспект: Руководство разработчика — Глава 26. Механизм копий базы данных (и Дата акселератор)** (19 КБ)

Разделы: 26.1. Общая информация · 26.2. Устройство механизма · 26.3. Дата акселератор · 26.4. Особенности и ограничения · 26.5. Управление составом копии · 26.6. Защита от использования одной базы несколькими копиями · 26.7. Информация о копии · 26.8. Управление копиями

### its-docs/dev-gl29-sistema-vzaimodejstviya.md

**ИТС-конспект: Руководство разработчика — Глава 29. Система взаимодействия** (23 КБ)

Разделы: 29.1. Общая информация · 29.2. Устройство: регистрация приложения · 29.3. Интерактивная работа (обзорно) · 29.4. Программный интерфейс (свойство глобального контекста `СистемаВзаимодействия`) · 29.5. Интеграция с внешними системами (обзорно) · 29.6. Выгрузка и перенос данных · 29.7. Администрирование · 29.8. Безопасность · Что из этого важно администратору

### its-docs/dev-gl30-rasshireniya.md

**ИТС-конспект: Руководство разработчика — Глава 30. Расширение конфигурации** (33 КБ)

Разделы: 30.1. Общая информация · 30.2. Управление расширениями · 30.3. Заимствование объектов (кратко) · 30.4. Объекты расширения (выборка) · 30.5. Расширения и распределённая информационная база · 30.6. Безопасный режим и профили безопасности · 30.7. Подключение расширений и время их работы · 30.8. Работа с расширениями из встроенного языка · Что из этого важно администратору

### its-docs/dev-gl31-otladka-oshibki-testirovanie.md

**ИТС-конспект: Руководство разработчика — Глава 31. Отладка и тестирование прикладных решений** (24 КБ)

Разделы: 31.2. Отладчик · 31.3. Ошибки времени исполнения · 31.4–31.6. Производительность · 31.7. Автоматизированное тестирование (обзорно)

### its-docs/dev-gl34-prochie-mehanizmy.md

**ИТС-конспект: Руководство разработчика — Глава 34. Прочие механизмы (лицензии, пользователи и пароли, уведомления, региональные настройки)** (23 КБ)

Разделы: 34.2. Интеграция с «1С:Аналитикой» · 34.3. Региональные настройки · 34.4. Активация программных лицензий из встроенного языка · 34.5. Уведомление клиента со стороны сервера · 34.6. Пользователи и аутентификация из встроенного языка

### its-docs/dev-gl37-gl38-hranilishche-postavka-podderzhka.md

**ИТС-конспект: Руководство разработчика — Глава 37. Групповая разработка (хранилище конфигурации) и Глава 38. Поставка и поддержка конфигурации** (33 КБ)

Разделы: Глава 37. Групповая разработка конфигурации · 37.1. Принцип · 37.2. Администрирование хранилища · 37.3. Работа с хранилищем (кратко) · 37.4. Удалённая работа с хранилищем (сервер хранилища) · 37.5. Рекомендации · Глава 38. Поставка и поддержка конфигурации · 38.1. Термины · 38.2. Поставка (сторона поставщика) · 38.3. Поддержка (сторона пользователя)

### its-docs/dev-obzor-glav-razrabotki.md

**ИТС-конспект: Руководство разработчика — обзор глав по разработке (3, 4, 6, 7, 8, 10–14, 16, 18, 27, 28, 35, 36, 39)** (27 КБ)

Разделы: Глава 3. Интерфейс приложения (`/content/48/hdoc`) · Глава 4. Встроенный язык (`/content/49/hdoc`) · Глава 6. Командный интерфейс (`/content/51/hdoc`) · Глава 7. Формы (`/content/52/hdoc`) · Глава 8. Работа с запросами (`/content/53/hdoc`) · Глава 10. Система компоновки данных (`/content/55/hdoc`) · Главы 11–14. Прикладные механизмы · Глава 16. Работа с различными форматами данных (`/content/61/hdoc`) · Глава 18. Дополнительные возможности веб-клиента (`/content/63/hdoc`) · Глава 27. Глобальный поиск (`/content/72/hdoc`) · Глава 28. Разработка для мобильных устройств (`/content/73/hdoc`) · Глава 35. Инструменты разработки (`/content/80/hdoc`) · Глава 36. Механизм сравнения и объединения конфигураций (`/content/81/hdoc`) · Глава 39. Сервисные возможности (`/content/84/hdoc`)

### its-docs/dev-pr07-osobennosti-rezhimov.md

**ИТС-конспект: Руководство разработчика — Приложение 7. Особенности поведения системы в различных режимах** (24 КБ)

Разделы: 7.1. Режим низкой скорости соединения · 7.2. Режим совместимости: что меняется по версиям · 7.3. Режим совместимости расширения · 7.4–7.5. Веб-клиент (обзорно) · 7.6. Объекты системы при включённом разделении данных (обзорно) · 7.7. Клиентское приложение под Linux · 7.8. Клиентское приложение под macOS · 7.10. Механизм защиты от опасных действий

### its-docs/dev-prilozheniya.md

**ИТС-конспект: Руководство разработчика — Приложения 1–6 и 8–13** (30 КБ)

Разделы: Оглавление приложений · Приложение 1. Конвертация баз 7.7 · Приложение 2. Форматы навигационных ссылок · Приложение 5. Поисковые выражения полнотекстового поиска · Приложение 6. Права доступа · Приложение 8. Особенности работы с различными СУБД · Приложение 10. Особенности отдельных механизмов · Приложение 13. Префиксы пространств имён (JSON) · Приложения 3, 4, 9, 11, 12 (обзорно)

## its-metod/ — Конспекты методических статей ИТС

### its-metod/ekspluataciya-krupnoj-sistemy-blokirovki-tranzakcii.md

**ИТС-конспект (методические материалы): Организация эксплуатации крупной системы; избыточные блокировки; блокировки регистров; ошибки БД и транзакции; настройка клиент-серверных систем** (97 КБ)

Разделы: Кратко: главные официальные рекомендации · Состав конспекта · 1. Организация эксплуатации крупной информационной системы · 2. Типичные причины избыточных блокировок и методы оптимизации · 3. Особенности блокировок регистров при работе с 1С:Предприятием 8 в варианте клиент-сервер · 4. Ошибки базы данных и транзакции · 5. Рекомендации по настройке клиент-серверных систем на основе «1С:Предприятия» · Материалы, на которые ссылаются статьи

### its-metod/kerberos-openid-autentifikaciya.md

**ИТС-конспект (методические материалы): Kerberos-аутентификация для Linux-сервера 1С, OpenID, сохранение аутентификации** (57 КБ)

Разделы: Кратко: главные официальные рекомендации · Статьи темы и их применимость · Как читать конспект · 1. Пример настройки Kerberos-аутентификации для Linux-версии сервера 1С:Предприятия 8 · 2. Вопросы настройки OpenID-аутентификации · 3. Изменение настроек сохранения аутентификации (1С:Предприятие 8.3.26 и выше)

### its-metod/licenzii-hasp-java-api-prochee-administrirovanie.md

**ИТС-конспект (методические материалы): Лицензирование (в том числе новый механизм 8.5.4), HASP, клиентские лицензии через сервер, Java-интерфейс администрирования и прочее** (63 КБ)

Разделы: Кратко: главные официальные рекомендации · Обзор статей и их применимость · 1. Особенности лицензирования при переходе на версии платформы 1С:Предприятие 8.5.4 · 2. Получение клиентских лицензий через сервер 1С:Предприятия · 3. Использование сетевых ключей HASP на 300 и 500 пользователей · 4. Программный Java-интерфейс для административного сервера · 5. Использование утилит 1CEClientSetupMake.exe и 1CEClientSetupMake.sh · 6. Рекомендации по пересчету итогов · 7. Восстановление журнала регистрации · Пробелы источников: чего в этих статьях нет

### its-metod/linux-openldap-kerberos-domennaya-avtorizaciya.md

**ИТС-конспект (методические материалы): Настройка OpenLDAP и Kerberos для доменной авторизации в Linux** (83 КБ)

Разделы: Кратко: главные официальные рекомендации · Статья: «Настройка OpenLDAP и Kerberos для использования доменной авторизации в Linux»

### its-metod/linux-ustanovka-platformy-dampy-kriptopro.md

**ИТС-конспект (методические материалы): Платформа 1С в Linux: установка, дампы, временные файлы, анализ загруженности оборудования, КриптоПро, сертификаты** (63 КБ)

Разделы: Кратко: главные официальные рекомендации · Сводка по статьям · 1. Установка Платформы «1С:Предприятие» в ОС Linux · 2. Создание дампов аварийного завершения программы в ОС Linux · 3. Изменение каталога временных файлов сервера 1С:Предприятия · 4. Замедление работы при запуске в режиме отладки · 5. Анализ загруженности оборудования для Linux · 6. Запуск нескольких экземпляров сервера 1С:Предприятия 8 на одном компьютере · 7. Работа платформы 1С:Предприятие с КриптоПро в ОС Linux · 8. Настройка использования программы КриптоПро версии 4.0 в ОС семейства Linux · 9. Добавление сертификата DigiCert в cacert.pem · Замеченные неточности и пробелы источников

### its-metod/medlennye-operacii-zadaniya-vremennye-fajly-hranilishche.md

**ИТС-конспект (методические материалы): Расследование медленных операций; регламентные и фоновые задания; временные файлы; встроенный язык на сервере; хранилище конфигурации** (105 КБ)

Разделы: Кратко: главные официальные рекомендации · Состав конспекта · 1. Методика расследования причин медленной работы операции на примере открытия управляемой формы · 2. Особенности работы механизма заданий в клиент-серверном и файловом вариантах · 3. Создание расписаний регламентных заданий · 4. Мониторинг и управление регламентными и фоновыми заданиями · 5. Рекомендации по использованию временных файлов в конфигурациях · 6. Использование встроенного языка на сервере 1С:Предприятия · 7. Особенности работы с хранилищем конфигурации · 8. Варианты использования хранилища конфигурации

### its-metod/metodika-proizvoditelnosti-apdex.md

**ИТС-конспект (методические материалы): Методика оценки и оптимизации производительности, APDEX** (84 КБ)

Разделы: Кратко: главные официальные рекомендации · 1. Оценка интегральной производительности системы по методике APDEX · 2. Оценка производительности и оптимизация многопользовательской системы. Общий подход · 3. Анализ производительности и оптимизация работающей многопользовательской системы

### its-metod/monitoring-i-audit.md

**ИТС-конспект (методические материалы): Мониторинг на продукционных серверах и механизмы платформы для мониторинга и аудита** (103 КБ)

Разделы: Кратко: главные официальные рекомендации · Статья 1. Использование механизмов платформы «1С:Предприятие» для мониторинга и аудита · Статья 2. Мониторинг на продукционных серверах · Как две статьи соотносятся для сервера 1С на Ubuntu

### its-metod/pg-nastrojki-postgresql-dlya-1c.md

**ИТС-конспект (методические материалы): Настройки PostgreSQL для 1С (официальные рекомендации)** (62 КБ)

Разделы: Кратко: главные официальные рекомендации · Обзор статей темы · 1. Настройки PostgreSQL для работы с 1С:Предприятием · 2. Настройки PostgreSQL для работы с 1С:Предприятием. Часть 2 · 3. Оптимизация производительности PostgreSQL · 4. Настройка Write Ahead Log для PostgreSQL · 5. Особенности использования параметра FSYNC при настройке параметров Write Ahead Log PostgreSQL · 6. Отложенное создание файлов временных таблиц в PostgreSQL с патчем от 1С · Расхождения между статьями (по тексту источников)

### its-metod/pg-otkazoustojchivyj-klaster-i-kopii-bd.md

**ИТС-конспект (методические материалы): Отказоустойчивый кластер PostgreSQL и внешняя синхронизация для механизма копий баз данных** (68 КБ)

Разделы: Кратко: главные официальные рекомендации · Статья: Построение отказоустойчивого кластера PostgreSQL. Настройка внешней синхронизации на PostgreSQL для механизма копий баз данных

### its-metod/pg-rasshireniya-1c-i-metodika-rassledovaniya.md

**ИТС-конспект (методические материалы): Расширения PostgreSQL с патчами 1С (auto_dump, pg_wait_sampling) и методика расследования проблем производительности PostgreSQL** (89 КБ)

Разделы: Кратко: главные официальные рекомендации · Состав конспекта · 1. Расширение auto_dump в PostgreSQL с патчем от 1С (первая версия) · 2. Расширение pg_wait_sampling в PostgreSQL с патчем от 1С · 3. Расширение auto_dump 1.1 в PostgreSQL с патчем от 1С · 4. Методика расследования проблем производительности на уровне работы СУБД PostgreSQL · 5. Оптимизация использования виртуальной таблицы СрезПоследних при работе с PostgreSQL · 6. Использование конструкции ПОЛНОЕ ВНЕШНЕЕ СОЕДИНЕНИЕ · Памятка: какая задача — какой инструмент (по материалам разделов) · Сводка: исправления, расхождения и неясные места источников

### its-metod/pg-sborka-arhivirovanie-rezervnoe-kopirovanie.md

**ИТС-конспект (методические материалы): Сборка PostgreSQL с патчами 1С, непрерывное архивирование, резервное копирование** (61 КБ)

Разделы: Кратко: главные официальные рекомендации · Сводка по статьям · 1. Методика сборки дистрибутива СУБД PostgreSQL 9.6 c патчами для работы с 1С:Предприятие 8 · 2. Настройка непрерывного архивирования в PostgreSQL 9.6 · 3. Резервное копирование базы данных при работе с PostgreSQL · 4. Рекомендации по организации резервного копирования информационной базы

### its-metod/raschet-oborudovaniya-i-nagruzochnoe-testirovanie.md

**ИТС-конспект (методические материалы): Расчёт параметров серверного оборудования и нагрузочное тестирование** (117 КБ)

Разделы: Кратко: главные официальные рекомендации · 1. Расчет параметров серверного оборудования · 2. Проведение нагрузочного тестирования

### its-metod/razmeshchenie-dannyh-i-indeksy.md

**ИТС-конспект (методические материалы): Размещение данных 1С:Предприятия в СУБД и индексы таблиц базы данных** (112 КБ)

Разделы: Кратко: главные официальные рекомендации · 1. Размещение данных 1С:Предприятия 8 · 2. Индексы таблиц базы данных

### its-metod/razmeshchenie-dannyh-tablicy-i-polya.md

**ИТС-конспект (методические материалы): Размещение данных 1С:Предприятия: таблицы и поля** (90 КБ)

Разделы: Кратко: главные официальные рекомендации · Статья: «Размещение данных 1С:Предприятия 8. Таблицы и поля»

### its-metod/sbor-dannyh-dlya-rassledovaniya-problem.md

**ИТС-конспект (методические материалы): Рекомендации по сбору данных для расследования технологических проблем** (89 КБ)

Разделы: Кратко: главные официальные рекомендации · Обзор статей темы · 1. «Рекомендации по сбору данных, необходимых для расследования технологических проблем»

### its-metod/tehzhurnal-bash-i-potreblenie-resursov.md

**ИТС-конспект (методические материалы): Анализ технологического журнала средствами bash; загрузка CPU и потребление памяти процессами кластера** (87 КБ)

Разделы: Кратко: главные официальные рекомендации · 1. Анализ технологических журналов с помощью инструментов bash · 2. Примеры настройки технологического журнала · 3. Высокая загрузка CPU на сервере приложений · 4. Значительное потребление памяти процессами кластера на сервере приложений · 5. Анализ потребления памяти процессами платформы 1С:Предприятие · 6. Анализ причин роста сеансовых данных

### its-metod/veb-https-apache-nginx-i-nastrojka-rabochih-serverov.md

**ИТС-конспект (методические материалы): Веб-публикация по HTTPS (Apache/Nginx под Linux), отладка по HTTPS, чек-листы настройки рабочих серверов** (85 КБ)

Разделы: Кратко: главные официальные рекомендации · 1. Публикация информационных баз на веб-сервере Apache под Linux с использованием шифрования (HTTPS) · 2. Настройка публикаций на веб-сервере Nginx под Linux с использованием шифрования (HTTPS) · 3. Подключение к серверу отладки через https (в т. ч. с использованием технологии 1С:Линк) · 4. Check-list по настройке рабочих серверов в продукционной зоне · 5. Настройка рабочих серверов с развернутой Технологической Платформой 1С:Предприятие · 6. На многопроцессорных системах на одном сервере должно работать больше одного процесса rphost

### its-metod/vzaimoblokirovki-i-oshibki-blokirovok.md

**ИТС-конспект (методические материалы): Анализ и устранение взаимоблокировок; методика расследования ошибок блокировок** (109 КБ)

Разделы: Кратко: главные официальные рекомендации · Статья 1. «Анализ и устранение взаимоблокировок» · Статья 2. «Методика расследования ошибок блокировок» · Что из двух статей относится к серверу 1С на Linux с PostgreSQL (сводка по источникам)

