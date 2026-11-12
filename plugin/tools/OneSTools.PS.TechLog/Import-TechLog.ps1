<#
  Import-TechLog.ps1 — самолокующийся импорт забандленного модуля OneSTools.PS.TechLog.

  Зачем враппер: Install-Module/Find-Module в этой среде НЕ работают
  (NuGet-провайдер отсутствует, его автозагрузка с go.microsoft.com таймаутится),
  поэтому модуль лежит рядом и грузится по $PSScriptRoot — без хардкода корня ядра.

  Использование:
    . tools\OneSTools.PS.TechLog\Import-TechLog.ps1
    $ev = Get-TechLog -Path 'D:\techlog\*\*.log'
    $ev | Sort-TechLog  -Property Duration -Top 20 -Descending
    $ev | Group-TechLog -GroupProperty EventName -AggregationProperty Duration

  ВАЖНО (проверено прогоном, в README этого нет):
    * файлы ТЖ должны быть в UTF-8 С BOM — командлет безусловно пропускает 3 байта;
    * имя файла ТЖ — yyMMddHH.log (год = 20 + первые две цифры);
    * строка события — mm:ss.ffffff-duration,EventName,Level,props.
#>
$manifest = Join-Path $PSScriptRoot 'OneSTools.PS.TechLog.psd1'
if(-not (Test-Path $manifest)){ throw "Не найден манифест модуля: $manifest" }
Import-Module $manifest -Force -WarningAction SilentlyContinue
Write-Host "OneSTools.PS.TechLog импортирован. Команды: Get-TechLog / Sort-TechLog / Group-TechLog"
