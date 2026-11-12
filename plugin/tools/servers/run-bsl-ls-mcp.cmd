@echo off
rem run-bsl-ls-mcp.cmd - запуск BSL Language Server в режиме MCP (stdio) для .mcp.json.
rem
rem Зачем лаунчер, а не прямой путь в .mcp.json:
rem   1) BLS ставится в %LOCALAPPDATA%\Programs\bsl-language-server\<версия>\ - прямой путь
rem      занёс бы в репозиторий имя пользователя (гейт утечек в health-check);
rem   2) каталог версионирован (v1.0.4, v1.0.6, ...) - прямой путь ломался бы при обновлении.
rem Лаунчер сам берёт САМУЮ СВЕЖУЮ установленную версию.
rem
rem Проверено 04.08.2026: BLS v1.0.6 поддерживает команду mcp (stdio|sse|streamable),
rem зонд tools/list вернул 10 инструментов. Док апстрима помечает режим как экспериментальный.
setlocal enabledelayedexpansion

set "BASE=%LOCALAPPDATA%\Programs\bsl-language-server"
set "EXE="

if not exist "%BASE%" (
  echo [run-bsl-ls-mcp] BSL Language Server not installed: "%BASE%" not found. 1>&2
  echo [run-bsl-ls-mcp] Install it with the 1c-syntax/claude-code-bsl-lsp plugin, which also updates it, or take a release from https://github.com/1c-syntax/bsl-language-server/releases 1>&2
  exit /b 1
)

rem Версия выбирается так (18.09.2026): сначала та, что записана в SERVER-INFO (её ведёт хук плагина
rem и ручное обновление по playbooks 5а), иначе - наибольшая по СРАВНЕНИЮ ВЕРСИЙ. Раньше бралась первая
rem по обратному порядку ИМЁН: рядом с v1.0.10 выбралась бы v1.0.9 (лексикографически "9" > "1").
if exist "%BASE%\SERVER-INFO" (
  for /f "tokens=2 delims=:, " %%v in ('findstr /c:"\"version\"" "%BASE%\SERVER-INFO"') do (
    set "VER=%%~v"
    if exist "%BASE%\!VER!\bsl-language-server\bsl-language-server.exe" (
      set "EXE=%BASE%\!VER!\bsl-language-server\bsl-language-server.exe"
    )
  )
)
if not defined EXE (
  for /f "delims=" %%d in ('powershell -NoProfile -Command "Get-ChildItem -Directory -LiteralPath $env:LOCALAPPDATA\Programs\bsl-language-server -Filter v* | Where-Object { $_.Name -match '^v\d+(\.\d+)+$' } | Sort-Object { [version]$_.Name.Substring(1) } -Descending | Select-Object -ExpandProperty Name" 2^>nul') do (
    if not defined EXE (
      if exist "%BASE%\%%d\bsl-language-server\bsl-language-server.exe" (
        set "EXE=%BASE%\%%d\bsl-language-server\bsl-language-server.exe"
      )
    )
  )
)

if not defined EXE (
  echo [run-bsl-ls-mcp] bsl-language-server.exe not found under "%BASE%". 1>&2
  exit /b 1
)

rem stdio-режим: транспорт по умолчанию, порт не нужен. Аргументы пробрасываем как есть.
"%EXE%" mcp %*
