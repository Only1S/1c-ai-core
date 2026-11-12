---
name: run-checks-quietly-in-background
description: Проверки (health-check/contour-tests/mcp-smoke) и операции выпуска и обновления (release-core, обновление проектов) гонять в ФОНЕ и показывать только итог-вердикт, а не полный вывод — простыни логов в чат не выводить
metadata:
  type: feedback
---

# Правило: проверки и обновления — в фоне, без простыней вывода

**Прогоны проверок и операции обновления запускаю в фоне (`run_in_background`) и показываю только компактный итог — вердикт по каждому чекеру и общий, а НЕ полный вывод.** Простыни `[ OK ]`-строк health-check/contour-tests/mcp-smoke в чат не лью.

**Why:** пользователь попросил (13.07.2026) — verbose-выводы забивают чат. Экономит контекст/токены ([[token-economy-and-local-tools]]) и держит фокус на результате. НЕ отменяет [[full-checker-set-before-done]] (каждый чекер запущен и назван с результатом) — меняет только ФОРМУ подачи: итог вместо дампа.

**How to apply:**
1. Запуск проверки/выпуска/обновления проектов — `run_in_background: true` (Bash/PowerShell); полный вывод уходит в фон/лог, не в чат.
2. По завершении читаю только итог (`Select-String 'Итог|FAIL'` / summary-файл) и отчитываюсь компактно: строка на чекер (`health-check FAIL=0`, `contour-tests FAIL=0`, …) + общий вердикт.
3. **Называть каждый задействованный инструмент и его результат обязательно** ([[full-checker-set-before-done]]) — но одной строкой, без тела лога.
4. Полный лог — по явной просьбе или при FAIL (тогда показать релевантные `[FAIL]`-строки, не весь дамп).
5. Правило о подаче, не об охвате: **пропускать проверки нельзя** ([[work-through-tools]], [[full-checker-set-before-done]]) — их всё равно гонять, просто тихо.

**Границы:** при FAIL — показать причину (конкретные строки), молчать нельзя. «Проверено» без реального запуска не писать ([[full-checker-set-before-done]]).

**Принуждение (с 17.10.2026):** барьер `guard-destructive` отклоняет запуск `health-check`, `contour-tests`, `mcp-smoke`, `weekly-check`, `pre-publish-audit`, `release-core`, `recall-check`, `build-plugin --validate`, `claude plugin update/install` и `claude plugin marketplace update` без `run_in_background` (п.1; `recall-check`, `build-plugin --validate` и `marketplace update` — с 30.10.2026). С 30.10.2026 тот же запуск ловится и под запускалкой без кавычек: `cmd /c`, `cmd //c`, `uv run`, `npx`, `nohup`, `timeout N`; скрипт, чей путь лежит в переменной (`S=…; python $S`), — признанная граница. Компактность отчёта (пп.2–4) — по-прежнему дисциплина. Регресс — `contour-tests` §6e, §92 и §136.

Связано: [[full-checker-set-before-done]], [[token-economy-and-local-tools]], [[work-through-tools]], [[work-journals-and-commits]].
