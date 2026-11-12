// Панель ядра сбоку от чата: команда /core открывает её, старт сессии — тоже, если окну хватает ширины;
// после обновления ядра — всплывашка «что нового», после долгого хода — уведомление (исследование модов, 30.10.2026).
// Модуль плагина один (hooks.json), старт сессии общий: status-band.tsx зовёт declareCore и announceVersion и рисует панель.
import type { EngineInterface } from 'claude-code'

import type { CardLine, CheckMark, Step } from './status-band.d'
import type { OwnerTask } from './owner-tasks'
import { ageOf } from './owner-tasks'

export const CORE_PANE = 'ones-core-core'
export const PANE_COLUMNS = 54   // примерно ширина карточек Claude; просьба к окну: граница, перетащенная человеком, важнее
export const FAULT_HINT = 'Пока фильтр не работает, ответы 1С скрыты. Выполните в терминале python -V: нет версии — установите Python. Версия есть — /ones-core:report-issue.'
const SEEN_KEY = 'core-pane-seen-version'
const STAGE_LABELS = ['Заявка', 'ТЗ', 'План', 'Код', 'Приёмка', 'Готово']
const GREEN = '#3fb950'
const YELLOW = '#f5c518'
const GRAY = '#8b8f94'
const LONG_TURN_MS = 10 * 60 * 1000

/** Что показать в панели: всё уже собрано status-band.tsx и другими модами — панель ничего не считает сама. */
export type CoreView = {
  fault: string | null          // почему не работает фильтр входящих
  cards: readonly CardLine[]    // идущие доработки, свежие первыми
  base: string | null
  steps: readonly Step[]
  step: string | null           // «Следующий шаг» журнала: показывается, когда шагов задачи нет
  check: CheckMark | null
  version: string | null
  notes: string | null          // запись этой версии, когда открыт раздел «Что нового»
  busy: boolean                 // идёт ход главного агента
  latest: string | null         // более новая версия ядра в канале
  stepMinutes: number | null    // сколько минут идёт текущий шаг
  owner?: readonly OwnerTask[]  // «Ждёт вас»: дела, которые может сделать только владелец (owner-tasks.tsx)
  ownerNow?: number | null      // время для возраста дел
}

/** Стадии доработки картинкой: пройденные — зелёный кружок с галочкой, текущая — жёлтая с вращением, будущие пустые;
 *  цвета явные — рамка картинки темы окна не видит. */
export function stagesSvg (index: number): string {
  const x = (i: number) => 16 + i * 48
  const lines = STAGE_LABELS.slice(1).map((_, i) =>
    '<line x1="' + (x(i) + 7) + '" y1="9" x2="' + (x(i + 1) - 7) + '" y2="9" stroke="' + (i < index ? GREEN : GRAY) + '" stroke-width="2.5"/>')
  const dots = STAGE_LABELS.map((_, i) => {
    if (i < index) return '<circle cx="' + x(i) + '" cy="9" r="7" fill="' + GREEN + '"/><path d="M' + (x(i) - 3.5) + ' 9.2l2.4 2.5 4.6-5" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    if (i > index) return '<circle cx="' + x(i) + '" cy="9" r="6" fill="none" stroke="' + GRAY + '" stroke-width="2"/>'
    return '<circle cx="' + x(i) + '" cy="9" r="6" fill="none" stroke="' + YELLOW + '" stroke-opacity="0.3" stroke-width="2.5"/>'
      + '<path d="M' + x(i) + ' 3a6 6 0 0 1 6 6" fill="none" stroke="' + YELLOW + '" stroke-width="2.5" stroke-linecap="round">'
      + '<animateTransform attributeName="transform" type="rotate" from="0 ' + x(i) + ' 9" to="360 ' + x(i) + ' 9" dur="1.4s" repeatCount="indefinite"/></path>'
  })
  const labels = STAGE_LABELS.map((t, i) => '<text x="' + x(i) + '" y="31" font-size="10" text-anchor="middle" font-family="sans-serif" fill="' + (i === index ? YELLOW : GRAY) + '">' + t + '</text>')
  return '<svg xmlns="http://www.w3.org/2000/svg" width="276" height="38" viewBox="0 0 276 38">' + [...lines, ...dots, ...labels].join('') + '</svg>'
}

/** Стадии текстом для поверхностей без картинок: ✓ пройдена, ● текущая, ○ впереди. */
export const stagesLine = (index: number) => STAGE_LABELS.map((_, i) => (i < index ? '✓' : i === index ? '●' : '○')).join(' ')

/** Самый свежий тег канала core-vX.Y.Z из вывода git ls-remote, если он новее установленной версии; иначе null. */
export function newerVersion (lsRemote: string, version: string | null): string | null {
  if (version === null) return null
  const parts = (v: string) => v.split('.').map(Number)
  const newer = (a: string, b: string) => {
    const [x, y] = [parts(a), parts(b)]
    const i = x.findIndex((n, k) => n !== y[k])
    return i >= 0 && x[i] > y[i]
  }
  const best = [...lsRemote.matchAll(/refs\/tags\/core-v(\d+\.\d+\.\d+)$/gm)].map(m => m[1]).reduce((a, b) => (newer(b, a) ? b : a), version)
  return best === version ? null : best
}

/** Заголовок панели: версия ядра видна всегда; открытие той же панели его обновляет. */
export const paneTitle = (version: string | null) => 'ones-core' + (version ? ' · ядро ' + version : '')

/** Слово итога проверки: вердикт без первого замечания — замечания идут списком ниже. */
export const checkHead = (text: string) => text.split(';')[0]

const pad = (n: number) => String(n).padStart(2, '0')

/** Итог проверки строкой: идёт сейчас или «время — вердикт»; проверки ещё не было — null. */
export function checkText (c: CheckMark | null): string | null {
  if (c === null) return null
  if (c.running) return 'идёт…'
  const at = c.at === null ? null : new Date(c.at)
  return (at === null ? '' : pad(at.getHours()) + ':' + pad(at.getMinutes()) + ' — ') + checkHead(c.text)
}

/** Номер текущего шага: первый неотмеченный; все отмечены — -1. */
export const currentStep = (steps: readonly Step[]) => steps.findIndex(s => !s.done)

/** Строка шага: готовый — галочка, текущий — стрелка. */
export const stepLine = (s: Step, i: number, current: number) => (s.done ? '✓ ' : i === current ? '→ ' : '  ') + (i + 1) + '. ' + s.text

/** Панель текстом — ответ команды там, где поверхность панелей не ставит. */
export function paneText (v: CoreView): string {
  const current = currentStep(v.steps)
  const check = checkText(v.check)
  return [
    v.fault ? '**⚠ Фильтр не запускается:** ' + v.fault : null,
    v.latest ? '**Есть новая версия ' + v.latest + '**' : null,
    v.owner?.length ? '**Ждёт вас (' + v.owner.length + '):**\n' + v.owner.map(t => '- #' + t.id + ' ' + t.title + (t.why ? ' — ' + t.why : '') + (t.doneWhen ? ' (готово, когда: ' + t.doneWhen + ')' : '') + (v.ownerNow ? ' · ' + ageOf(t.at, v.ownerNow) : '')).join('\n') : null,
    v.cards.length ? '**Доработки:**\n' + v.cards.map(c => '- ' + c.name + ' · ' + c.stage).join('\n') : null,
    v.base ? '**База:** ' + v.base : null,
    v.steps.length ? '**Шаги ' + v.steps.filter(s => s.done).length + ' из ' + v.steps.length + ':**\n' + v.steps.map((s, i) => '- ' + stepLine(s, i, current)).join('\n') : null,
    !v.steps.length && v.step ? '**Следующий шаг:** ' + v.step : null,
    check ? '**Проверка:** ' + check + (v.check?.items.length ? '\n' + v.check.items.map(i => '- ' + i).join('\n') : '') : null,
    v.notes,
  ].filter(Boolean).join('\n\n')
}

/** Раздел «## core-v<версия>» из RELEASE-NOTES.md плагина (кладёт build-plugin) — без технических подробностей. */
export function notesOf(text: string | null, version: string | null): string | null {
  if (!text || !version) return null
  const m = new RegExp('(^|\\n)## core-v' + version.replace(/\./g, '\\.') + '\\b[\\s\\S]*?(?=\\n## core-v|$)').exec(text)
  if (!m) return null
  return m[0].replace(/<details>[\s\S]*?<\/details>/g, '').trim()
}

/** Старт сессии, до next: объявить команду — она в меню с первого хода. */
export async function declareCore ($: EngineInterface) {
  try {
    await $.command.register({ name: 'core', description: 'Панель ядра: сбой фильтра, доработка и база, шаги задачи, итог проверки, что нового в версии' })
  } catch {}
}

/** Старт сессии, после next: версия сменилась — всплывашка «что нового» (ключ — на проект: $.store общий для сессий). */
export async function announceVersion ($: EngineInterface, version: string | null) {
  if (!version) return
  try {
    const key = SEEN_KEY + ':' + (await $.session.root())
    const seen = await $.store.get(key)
    if (seen !== version) {
      if (seen !== undefined) $.ui.toast('Ядро обновлено до ' + version + ' — в панели /core кнопка «Что нового»', { timeoutMs: 15000 })
      await $.store.set(key, version)
    }
  } catch {}
}

/** Долгий ход главного агента закончился — уведомление, а где его некуда отправить — всплывашка. */
export async function announceLongTurn ($: EngineInterface, e: { durationMs?: number, agentId?: string, isAborted?: boolean }) {
  if (e.agentId !== undefined || e.isAborted || !e.durationMs || e.durationMs < LONG_TURN_MS) return
  const text = 'Ход закончен за ' + Math.round(e.durationMs / 60000) + ' мин — итог в чате'
  try {
    const sent = await $.ui.notify(text, { title: 'ones-core' })
    if (!sent.isSent) $.ui.toast(text, { timeoutMs: 15000 })
  } catch {
    try { $.ui.toast(text, { timeoutMs: 15000 }) } catch {}
  }
}
