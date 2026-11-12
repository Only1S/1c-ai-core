// Мод «кнопка проверок»: команда /check запускает в фоне проверку проекта (tools/checks/project-check.py плагина:
// изменённые модули .bsl, проектные доки, секреты к коммиту, запреты проекта, программы ядра), вердикт — уведомлением.
// Модуль плагина один (hooks.json): подключается из status-band.tsx.
import { atom, update } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { runPython } from './run-python'
import type { CheckMark } from './status-band.d'

const last = atom({ plugin: 'ones-core', key: 'project-check-last' } as const, null as CheckMark | null)

const SCRIPT = '/tools/checks/project-check.py'
const REPORT = 'logs/project-check.txt'
const RUN_MS = 10 * 60 * 1000
const TOAST_MS = 20000
const CLEAN_SHOW_MS = 60000
const ITEMS_MAX = 8
const ITEM_MAX = 160

export type CheckVerdict = { level: 'ok' | 'warn' | 'fail', text: string }

const LEVEL_WORD = { ok: 'чисто', warn: 'есть замечания', fail: 'есть ошибки' } as const

/** Вердикт из вывода project-check.py: последняя строка JSON; нет её — ошибка запуска с хвостом вывода. */
export function verdictOf (stdout: string, exitCode: number): CheckVerdict {
  const line = stdout.split(/\r?\n/).reverse().find(l => l.trim().startsWith('{'))
  try {
    const d = JSON.parse(line ?? '') as { verdict?: unknown, headline?: unknown }
    const level = d.verdict === 'ok' || d.verdict === 'warn' || d.verdict === 'fail' ? d.verdict : null
    if (level !== null && typeof d.headline === 'string') return { level, text: LEVEL_WORD[level] + ' — ' + d.headline }
  } catch {}
  const tail = stdout.trim().split(/\r?\n/).slice(-1)[0] ?? ''
  return { level: 'fail', text: 'проверка не дала вердикта (код ' + exitCode + ')' + (tail ? ': ' + tail.slice(0, 160) : '') }
}

/** Строки ошибок и замечаний из вывода project-check.py — в панель, каждая своей строкой. */
export function itemsOf (stdout: string): string[] {
  return stdout.split(/\r?\n/).flatMap(l => /^\[(FAIL|WARN)\]\s+(.+)$/.exec(l)?.[2] ?? []).slice(0, ITEMS_MAX).map(s => s.slice(0, ITEM_MAX))
}

/** Старт сессии: объявить команду — она в меню с первого хода. */
export async function declareCheck ($: EngineInterface) {
  try {
    await $.command.register({
      name: 'check',   // имя — литералом: так валидатор видит, что команда своя
      description: 'Проверить проект в фоне: изменённые модули .bsl, проектные доки, секреты к коммиту, запреты и программы ядра',
      immediate: true,
    })
  } catch {}
}

/** Вердикт — уведомлением; где его некуда отправить — всплывашкой. В чат не пишется: итог остаётся в панели ядра. */
async function announce ($: EngineInterface, text: string) {
  try {
    const sent = await $.ui.notify(text, { title: 'ones-core' })
    if (!sent.isSent) $.ui.toast(text, { timeoutMs: TOAST_MS })
  } catch {
    try { $.ui.toast(text, { timeoutMs: TOAST_MS }) } catch {}
  }
}

async function runCheck ($: EngineInterface) {
  let v: CheckVerdict
  let items: string[] = []
  try {
    const root = await $.session.root()
    const r = await runPython((argv, init) => $.process.run(argv, init), [$.plugin.root + SCRIPT, '--project', root, '--json', '--report', root + '/' + REPORT], { cwd: root, timeoutMs: RUN_MS })
    v = verdictOf(r.stdout, r.exitCode)
    items = itemsOf(r.stdout)
  } catch (err) {
    v = { level: 'fail', text: 'проверка не запустилась: ' + String(err instanceof Error ? err.message : err).slice(0, 160) }
  }
  const at = await $.clock.now().catch(() => null)
  await update($, last, () => ({ running: false, at, level: v.level, text: v.text, items }))
  // чистый итог уходит из панели сам; новая проверка за это время его заменит, и таймер её не тронет
  if (v.level === 'ok') $.clock.after(CLEAN_SHOW_MS, () => { void update($, last, c => (c?.running === false && c.at === at ? null : c)).catch(() => undefined) })
  await announce($, 'Проверка проекта: ' + v.text)
}

// Прогон один за раз: повторная команда во время прогона его не дублирует
let running: Promise<void> | null = null

/** Запуск в фоне для команды и кнопки панели; уже идёт — false. */
export function startCheck ($: EngineInterface): boolean {
  if (running !== null) return false
  running = update($, last, c => ({ running: true, at: c?.at ?? null, level: c?.level ?? null, text: c?.text ?? '', items: c?.items ?? [] }))
    .then(() => runCheck($), () => runCheck($))
    .finally(() => { running = null })
  return true
}

/** Команда отвечает сразу, прогон идёт в фоне. В модуле один старт сессии без отбора (его держит status-band.tsx): свой — с отбором. */
export function serveCheck (on: On) {
  on('session.start', { cwd: /^/ }, async ($, e, next) => {
    await declareCheck($)
    return next(e)
  })
  on('command.run', { command: 'check' }, async $ => {
    if (!startCheck($)) return { text: 'Проверка проекта уже идёт — вердикт придёт уведомлением.' }
    return { text: 'Проверка проекта запущена в фоне: модули .bsl и доки из изменений, секреты к коммиту, запреты и программы ядра. '
      + 'Вердикт придёт уведомлением, подробности — ' + REPORT + '.' }
  })
}
