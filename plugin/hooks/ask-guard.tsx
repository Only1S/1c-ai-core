// Мод «спросить вместо запрета» (М-2): отказ барьера guard-destructive с пометкой «Если это осознанное решение — выполни вручную сам»
// мод показывает владельцу окном вариантов; только явное «Разрешить один раз» снимает этот отказ для этого вызова (ADR-0010).
// Окно — только если все отказы команды из списка и команда видна целиком (ADR-0011).
// Модуль плагина один (hooks.json): подключается из status-band.tsx.
import type { EngineInterface, On, PreToolUseResult } from 'claude-code'

import { runPython } from './run-python'

/** Начало вопроса мода: subagent-gate.py по нему не записывает ответ владельца как согласие на помощников. */
export const ASK_PREFIX = 'Барьер guard-destructive отклонил команду'
export const DENY_LABEL = 'Отказать (Рекомендую)'
export const ALLOW_LABEL = 'Разрешить один раз'

// Тексты отказа guard-destructive.py, которые мод узнаёт; contour-tests §73 сверяет их с самим барьером
export const GUARD_HEAD = 'Заблокировано до-исполнительным барьером (guard-destructive): '
export const GUARD_TAIL = 'Если это осознанное решение — выполни вручную сам; агент деструктив не запускает.'
// префикс вложенной команды — по шаблону: перечень в скобках барьер дополняет (с 30.10.2026 — «heredoc в исполнитель»)
const INNER = /^команда внутри другой \([^)]*\) — /
// приставка движка у отказа командного хука (живая проба 30.10.2026): без её снятия мод не узнавал ни одного отказа
const ENGINE_PREFIX = /^PreToolUse:\w+ hook error: /

/** Причины барьера, о которых можно спросить: локальное удаление файлов и правка истории git. Остальные — всегда отказ. */
export const ASKABLE: readonly string[] = [
  'rm с рекурсией и принуждением', 'rm с рекурсией вне временной папки', 'Remove-Item -Recurse', 'rmdir /s', 'del /s',
  'find … -delete', 'robocopy /MIR', 'git push --delete',
  'git reset --hard', 'git clean -f/--force', 'git checkout . / --', 'git checkout -f/--force', 'git switch -f/--discard-changes',
  'git stash clear/drop', 'git restore .', 'force-push', 'git branch -D', 'git filter-branch', 'git reflog expire',
  'git gc --prune=now', 'git update-ref -d', 'рекурсивное удаление в коде интерпретатора',
]

/** Никогда не спрашивать (решение владельца 30.10.2026): по тексту команды, поверх причины барьера. */
const NEVER: ReadonlyArray<readonly [string, RegExp]> = [
  ['секреты', /\.env\b|\.pem\b|\.key\b|\bid_(rsa|ed25519|ecdsa|dsa)\b|_(rsa|ed25519|ecdsa|dsa)\b|\.?pgpass|[\\/]secrets?[\\/]|[\\/]?\.ssh\b|credential|\.npmrc\b|\.pypirc\b|[\\/]\.(aws|azure|kube|gnupg)\b|token|secret|passw|парол/i],
  ['плагин, хуки, разрешения и настройки', /\.claude|settings(\.local)?\.json|managed-settings|disableAllHooks|permission|\bhooks?\b|\bplugins?\b|CLAUDE_PLUGIN|hooksPath|--no-verify|consent/i],
  ['базы 1С и СУБД', /\b(1cv8[cs]?|ibcmd|ibsrv|rac|ras|ragent|rphost|psql|pg_\w+|dropdb|createdb|sqlcmd|osql|mysql|mariadb)\b|\.1cd\b|\.v8-project|\b(srvr|file|ref)\s*=|infobase|\.(dt|cf|cfe)\b/i],
  ['сервер', /\b(ssh|scp|sftp|rsync)\b|vm-shell|tmux\s+send-keys/i],
]

const MASKS: ReadonlyArray<readonly [RegExp, string]> = [
  [/(:\/\/)[^\s/@:]+:[^\s/@]+@/g, '$1***@'],
  [/\b(gh[pousr]_|github_pat_|glpat-|xox[baprs]-|sk-|AKIA)[A-Za-z0-9_-]{6,}/g, '$1***'],
  [/(\b[\w-]*(?:token|secret|passw\w*|pwd|key)\s*[=:]\s*)\S+/gi, '$1***'],
]

const NOTE = 'Владелец разрешил ровно этот вызов один раз в окне подтверждения мода (ADR-0010); следующая такая команда — снова его решение.'
const JOURNAL = '/logs/ask-guard.jsonl'
const JOURNAL_LINES = 200
const COMMAND_MAX = 300
const BARRIER = '/hooks/guard-destructive.py'
const SWEEP_MS = 15_000

/** Причина отказа барьера, если отказ — его, целиком и с пометкой «выполни вручную сам»; иначе null. Первая строка отказа —
 *  только текст барьера (команда стоит ниже, в строке «Сегмент:»/«Команда:»), поэтому командой причину не подделать. */
export function guardReason (deny: string): string | null {
  const t = deny.trim().replace(ENGINE_PREFIX, '')
  if (!t.startsWith(GUARD_HEAD) || !t.endsWith(GUARD_TAIL) || t.split(GUARD_HEAD).length !== 2) return null
  return t.split('\n')[0].slice(GUARD_HEAD.length).replace(/\.$/, '')
}

/** О причине можно спросить владельца. */
export function isAskable (reason: string): boolean {
  const r = reason.replace(INNER, '')
  return ASKABLE.some(p => r.startsWith(p))
}

/** Категория «никогда не спрашивать» по тексту команды или null. */
export function neverAsk (command: string): string | null {
  return NEVER.find(([, re]) => re.test(command))?.[0] ?? null
}

/** Команда для окна: одной строкой, без учётных данных в адресах и токенов. */
export function masked (command: string): string {
  return MASKS.reduce((s, [re, to]) => s.replace(re, to), command.replace(/\s+/g, ' ').trim())
}

/** Одиночный & вне кавычек: барьер режет команду по ; | && || и переводу строки, и вторая команда осталась бы в тени первой.
 *  Перенаправления (2>&1, &>) и оператор вызова PowerShell в начале команды (& 'C:\x.exe') — не разделитель. */
export function hasBareAmp (command: string): boolean {
  const t = command.replace(/"[^"]*"|'[^']*'/g, '""').replace(/\d*>&\d*|&>>?|&&/g, ' ')
  return /[^\s;|&(][ \t]*&/.test(t)
}

/** Почему окно не покажет всё, что выполнится; null — покажет. Владелец разрешает только то, что видит (ADR-0011). */
export function unseen (command: string): string | null {
  if (masked(command).length > COMMAND_MAX) return 'команда длиннее окна'
  return hasBareAmp(command) ? 'одиночный & между командами' : null
}

/** Причины всех отказов барьера или null: отказа нет, вход не тот или есть отказ, о котором спросить нельзя. */
export function askableReasons (denies: unknown): string[] | null {
  if (!Array.isArray(denies) || denies.length === 0) return null
  const reasons = denies.map(d => guardReason(String(d)))
  return reasons.every((r): r is string => r !== null && isAskable(r)) ? [...new Set(reasons)] : null
}

export function questionOf (reason: string, command: string): string {
  return ASK_PREFIX + ': ' + reason + '. Команда: ' + masked(command) + '. Разрешить этот вызов один раз?'
}

/** Отпечаток команды для журнала (FNV-1a): по нему видно повтор, а сама команда в журнал не пишется. */
export function fingerprint (text: string): string {
  let h = 0x811c9dc5
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 0x01000193) >>> 0
  return h.toString(16).padStart(8, '0')
}

type Decision = 'allowed-once' | 'denied' | 'no-dialog' | 'never' | 'rule-deny'

/** Строка журнала мода: решение, причина барьера, программа, длина и отпечаток команды — без самой команды. */
async function journal ($: EngineInterface, decision: Decision, reason: string, command: string, extra?: string) {
  try {
    const path = (await $.session.root()) + JOURNAL
    const old = (await $.fs.exists(path)) ? (await $.fs.read(path)).split('\n').filter(l => l.trim() !== '') : []
    const line = JSON.stringify({
      ts: new Date(await $.clock.now()).toISOString(), decision, reason, program: command.trim().split(/\s+/)[0] ?? '',
      length: command.length, hash: fingerprint(command), ...(extra ? { note: extra } : {}),
    })
    await $.fs.write(path, [...old.slice(-(JOURNAL_LINES - 1)), line].join('\n') + '\n')
  } catch {}
}

/** Все отказы барьера по команде целиком (guard-destructive.py --all-reasons): причины для окна или null — как у askableReasons,
 *  а ещё при сбое запуска. */
async function sweep ($: EngineInterface, tool: string, input: unknown): Promise<string[] | null> {
  try {
    const out = await runPython((argv, init) => $.process.run(argv, init), [$.plugin.root + BARRIER, '--all-reasons'], {
      stdin: JSON.stringify({ tool_name: tool, tool_input: input }), timeoutMs: SWEEP_MS,
      env: { CLAUDE_PROJECT_DIR: await $.session.root(), PYTHONIOENCODING: 'utf-8' },
    })
    return out.exitCode === 0 ? askableReasons(JSON.parse(out.stdout)) : null
  } catch {
    return null
  }
}

// Вызовы Bash/PowerShell основного агента: окно — только им; помощник получает отказ, как раньше
const MAIN = new Set<string>()

export function serveAskGuard (on: On) {
  on('tool.call', { tool: /^(Bash|PowerShell)$/ }, async ($, e, next) => {
    const id = e.tool_use_id
    if (e.agentId !== undefined || !id) return next(e)
    MAIN.add(id)
    try {
      return await next(e)
    } finally {
      MAIN.delete(id)
    }
  }).catch(($, e, next) => next(e))

  // Ниже модуля — командные хуки плагина и настроек: next(e) отдаёт их свёрнутое решение, в том числе отказ guard-destructive
  on('classic.PreToolUse', { tool: /^(Bash|PowerShell)$/ }, async ($, e, next) => {
    const r: PreToolUseResult = await next(e)
    if (r.deny === undefined) return r
    const reason = guardReason(r.deny)
    if (reason === null || !isAskable(reason)) return r
    const command = typeof (e as { command?: unknown }).command === 'string' ? (e as { command: string }).command : ''
    const never = neverAsk(command)
    if (command === '' || never !== null || r.updatedInput !== undefined || !MAIN.has(e.tool_use_id)) {
      await journal($, 'never', reason, command, never ?? (MAIN.has(e.tool_use_id) ? 'вход переписан' : 'не основной агент'))
      return r
    }
    const hidden = unseen(command)
    if (hidden !== null) {
      await journal($, 'never', reason, command, hidden)
      return r
    }
    const { tool, tool_use_id: _id, ...input } = e
    // запрет permissions.deny окно не снимет — не спрашиваем впустую
    try {
      if ((await $.tool.check({ tool, input })).decision === 'deny') {
        await journal($, 'rule-deny', reason, command)
        return r
      }
    } catch {}
    // барьер выходит на первом совпадении: снять отказ можно, только если все отказы этой команды — из списка (ADR-0011)
    const reasons = await sweep($, tool, input)
    if (reasons === null) {
      await journal($, 'never', reason, command, 'в команде есть отказ, о котором спросить нельзя, или сверка не удалась')
      return r
    }
    let answer: string
    try {
      answer = await $.ui.ask(questionOf(reasons.join('; '), command), { options: [DENY_LABEL, ALLOW_LABEL], header: 'Барьер' })
    } catch {
      await journal($, 'no-dialog', reason, command)   // окно закрыто, ошибка, запуск без интерфейса (-p)
      return r
    }
    if (answer !== ALLOW_LABEL) {
      await journal($, 'denied', reason, command)
      return { ...r, deny: r.deny + '\nВладелец ответил в окне подтверждения: отказать.' }
    }
    await journal($, 'allowed-once', reason, command)
    $.ui.log('ones-core: владелец разрешил один раз — ' + reason)
    return { additionalContext: [...(r.additionalContext ?? []), NOTE] }
  }).catch(($, e, next) => next(e))
}
