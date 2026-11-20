# OneSTools.PS.TechLog — забандленный сторонний модуль

- **Источник:** https://github.com/akpaevj/OneSTools.PS.TechLog
- **Версия:** 1.1.11 (пакет `OneSTools.PS.TechLog` из PowerShell Gallery)
- **Автор:** Akpaev Evgeny
- **Лицензия:** **MIT** — файл `LICENSE` лежит рядом; редистрибуция требует его сохранения.
- **Патчей нет:** код не изменялся (дисциплина — [[vendor-patch-registry]]).
- **SHA-256** `OneSTools.PS.TechLog.dll` (25 088 байт, без подписи Authenticode): `4de209397def762d74f9f71a5a0afd39948be8c855149bddd329ff2ce4531f32`. По нему `pre-publish-audit` §7 считает бинарник известным и не выдаёт WARN (решение владельца 20.11.2026); другой хеш — снова WARN.
- **Назначение:** разбор и агрегация **технологического журнала (ТЖ)** 1С. Единственная ниша ТЖ в ядре; MCP-сервера под ТЖ, совместимого со средой, не существует.

## Почему забандлен, а не ставится из галереи
В этой среде `Install-Module`/`Find-Module` **не работают**: NuGet-провайдер отсутствует, а его автозагрузка с `go.microsoft.com` таймаутится (проверено). Пакет получен прямой загрузкой
`https://www.powershellgallery.com/api/v2/package/OneSTools.PS.TechLog` (это zip) и распакован. Бандл делает ядро самодостаточным.

## Состав (ВСЕ файлы обязательны)
| Файл | Роль |
|---|---|
| `OneSTools.PS.TechLog.dll` | `RootModule` (бинарный командлет `Get-TechLog`) |
| `OneSTools.PS.TechLog.psd1` | манифест |
| `Group-TechLog.ps1`, `Sort-TechLog.ps1` | **`NestedModules`** — без них `Import-Module` падает с `The given assembly name or codebase was invalid` |
| `LICENSE` | MIT (обязателен при редистрибуции) |
| `Import-TechLog.ps1` | наш самолокующийся враппер (не часть апстрима) |

## Проверенный контракт (прогон, а не README)
- `Get-TechLog -Path <glob>` → объекты `TjEvent { DateTime, Duration, EventName, Level, Properties }`
- `Sort-TechLog -Property Duration -Top N [-Descending]` → самые долгие события
- `Group-TechLog -GroupProperty EventName -AggregationProperty Duration` → `Sum/Avg/Min/Max/Count`

Разбираются в т.ч. `CALL`, `DBMSSQL`, `TLOCK`, `TDEADLOCK`, `EXCP`; свойства события доступны в `Properties` (напр. `Sql`, `DeadlockConnectionIntersections`).

## Ловушки (стоили одного упавшего прогона)
1. **Файл ТЖ обязан быть UTF-8 с BOM.** В исходнике: `reader.BaseStream.Seek(3, SeekOrigin.Current)` — безусловно пропускает 3 байта. Без BOM съедаются первые 3 символа первой строки → `DateTime.Parse` падает с `String was not recognized as a valid DateTime`.
2. **Имя файла — `yyMMddHH.log`** (год берётся как `20` + первые две цифры имени).
3. Формат строки события: `mm:ss.ffffff-duration,EventName,Level,props`.
4. **`Sort-TechLog -Top 1` падает** на втором событии (`CannotIndex`): после первого события массив из одного элемента сортировкой превращается в одиночный объект. Брать `-Top 2` и больше, первый — `@(...)[0]` (проверено прогоном 30.10.2026, `contour-tests` §83).

## Обновление
Перекачать `.nupkg` тем же способом, перепроверить контракт (`Get-Command -Module ... -Syntax`) по правилу [[probe-tool-capabilities]] и обновить этот файл, включая строку SHA-256.

Запуск: `. tools\OneSTools.PS.TechLog\Import-TechLog.ps1` (самолокуется через `$PSScriptRoot`).
