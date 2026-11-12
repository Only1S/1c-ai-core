// Мод «выжимка длинного вывода» (решение владельца 05.11.2026; по мотивам context-diet, MIT — docs/sources/claude-code-mods-review.md)
// Длинный вывод Bash и PowerShell модель видит выжимкой: начало, конец и строки с ошибками, предупреждениями и итогом.
// Полный текст — в logs/output-NN.txt проекта (по кругу из FILES_MAX файлов). Вызывает чистка входящих после маски ПДн.
import type { EngineInterface } from 'claude-code'

export const LIMIT = 8000          // знаков: короче — вывод идёт как есть
const HEAD = 12
const TAIL = 12
const BEFORE = 2
const AFTER = 3
const FILES_MAX = 50
const SIGNAL = /\b(error|errors|fail|failed|failure|warn|warning|exception|traceback|fatal|panic|assert\w*)\b|\[(FAIL|WARN)\]|ошибк|предупрежд|исключени|итог|не выполнен|упал|отказ/i
// печать файла целиком — модель просила именно весь текст: такой вывод не сжимается
const WHOLE = /^\s*(cat|type|Get-Content|gc|head|tail|sed\s+-n|less|more)\b/i

let counter = 0

/** Выжимка текста: null — короче порога или выжимка не короче половины исходного (резать незачем). */
export function digestText (text: string): string | null {
  if (text.length <= LIMIT) return null
  const lines = text.split(/\r?\n/)
  const keep = new Set<number>()
  for (let i = 0; i < Math.min(HEAD, lines.length); i++) keep.add(i)
  for (let i = Math.max(0, lines.length - TAIL); i < lines.length; i++) keep.add(i)
  lines.forEach((line, i) => {
    if (!SIGNAL.test(line)) return
    for (let j = Math.max(0, i - BEFORE); j <= Math.min(lines.length - 1, i + AFTER); j++) keep.add(j)
  })
  const out: string[] = []
  let prev = -1
  for (const i of [...keep].sort((a, b) => a - b)) {
    if (i > prev + 1) out.push('… (пропущено строк: ' + (i - prev - 1) + ')')
    out.push(lines[i] ?? '')
    prev = i
  }
  let body = out.join('\n')
  if (body.length > LIMIT) body = body.slice(0, LIMIT / 2) + '\n… (выжимка обрезана — смотри полный вывод)\n' + body.slice(-LIMIT / 2)
  return body.length * 2 > text.length ? null : body
}

/** Заголовок выжимки для модели: сколько срезано, что оставлено, где полный текст. */
export const headerOf = (from: number, to: number, path: string) =>
  '[ones-core, выжимка вывода: ' + from + ' → ' + to + ' знаков. Оставлены начало, конец и строки с ошибками, предупреждениями ' +
  'и итогом. Полный вывод: ' + path + ' — прочитай его, прежде чем отвечать о том, чего здесь нет.]'

/** Сжимать ли вывод этого вызова: только Bash и PowerShell, кроме печати файла целиком. */
export function digestible (tool: string, input: Record<string, unknown>): boolean {
  if (tool !== 'Bash' && tool !== 'PowerShell') return false
  return !WHOLE.test(String(input.command ?? ''))
}

/** Текст результата → выжимка с сохранением полного текста; null — оставить как есть (коротко, незачем или файл не записан). */
export async function digestOutput ($: EngineInterface, text: string): Promise<string | null> {
  const body = digestText(text)
  if (body === null) return null
  counter = counter % FILES_MAX + 1
  const rel = 'logs/output-' + String(counter).padStart(2, '0') + '.txt'
  try {
    await $.fs.write((await $.session.root()) + '/' + rel, text)
  } catch {
    return null   // полного текста нет на диске — резать нельзя: модель потеряла бы то, что не попало в выжимку
  }
  return headerOf(text.length, body.length, rel) + '\n' + body
}
