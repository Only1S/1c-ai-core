// Мод «Ждёт вас» (решение владельца 05.11.2026; по мотивам human-in-the-loop, MIT — docs/sources/claude-code-mods-review.md):
// дела, которые может сделать только владелец, — инструмент модели owner_tasks, файл .claude/owner-tasks.json проекта;
// список — в панели ядра с кнопками «Сделано / Ответить / Отказать», они вставляют ответ в поле ввода, отправляет владелец
import { atom, update } from 'claude-code'
import type { EngineInterface, On, ToolSpec } from 'claude-code'

export type OwnerTask = { id: number, title: string, why?: string, doneWhen?: string, at: number }

export const ownerList = atom({ plugin: 'ones-core', key: 'owner-tasks-list' } as const, null as OwnerTask[] | null)

const TOOL = 'mcp__ones-core__owner_tasks'
const FILE = '/.claude/owner-tasks.json'
const TEXT_MAX = 200
const TASKS_MAX = 20
const WHO = 'ждёт вас: '

const SPEC: ToolSpec = {
  name: 'owner_tasks',
  description: 'Дела, которые может сделать только владелец: секрет или пароль в окружении, отметка pd или запись в реестре баз, '
    + 'настройка Windows или задачи планировщика, вход в базу, переподключение сервера, решение. Дело видно владельцу в панели ядра '
    + '«Ждёт вас», пока не закрыто, и не теряется в чате. add — дело (title — что сделать, why — зачем, done_when — как понять, что '
    + 'готово); владелец сделал, ответил или отказал — close с номером; show — список. Пароли и ключи в дело не писать.',
  inputSchema: {
    type: 'object',
    properties: {
      action: { type: 'string', enum: ['add', 'close', 'show'], description: 'add — новое дело, close — закрыть по номерам, show — показать' },
      title: { type: 'string', description: 'для add: что сделать владельцу, глаголом' },
      why: { type: 'string', description: 'для add: зачем это нужно' },
      done_when: { type: 'string', description: 'для add: как понять, что сделано' },
      numbers: { type: 'array', items: { type: 'integer', minimum: 1 }, description: 'для close: номера дел из show' },
    },
    required: ['action'],
  },
  isDeferred: false,
}

const clip = (v: unknown): string | undefined => (typeof v === 'string' && v.trim() !== '' ? v.trim().slice(0, TEXT_MAX) : undefined)

/** Дела из файла; чужие записи пропускаются; пустой файл — пустой список; файл не разбирается — null. */
export function parseTasks (text: string | null): OwnerTask[] | null {
  const t = (text ?? '').replace(/^﻿/, '')
  if (text !== null && t.trim() === '') return []
  try {
    const d = JSON.parse(t)
    if (!Array.isArray(d?.tasks)) return null
    return (d.tasks as unknown[]).flatMap(x => {
      const o = x as Record<string, unknown> | null
      if (typeof o?.title !== 'string' || !Number.isInteger(o.id) || typeof o.at !== 'number') return []
      const task: OwnerTask = { id: o.id as number, title: o.title, at: o.at }
      if (typeof o.why === 'string') task.why = o.why
      if (typeof o.doneWhen === 'string') task.doneWhen = o.doneWhen
      return [task]
    })
  } catch {
    return null
  }
}

/** Возраст дела словами: сейчас, N мин, N ч, N дн. */
export function ageOf (at: number, now: number): string {
  const min = Math.max(0, Math.floor((now - at) / 60000))
  if (min < 1) return 'сейчас'
  if (min < 60) return min + ' мин'
  if (min < 24 * 60) return Math.floor(min / 60) + ' ч'
  return Math.floor(min / (24 * 60)) + ' дн'
}

/** Список для модели. */
export function listOf (tasks: readonly OwnerTask[]): string {
  if (tasks.length === 0) return 'Дел для владельца нет.'
  return ['Ждёт владельца (' + tasks.length + '):', ...tasks.map(t => '#' + t.id + ' ' + t.title + (t.why ? ' — ' + t.why : '') + (t.doneWhen ? ' (готово, когда: ' + t.doneWhen + ')' : ''))].join('\n')
}

/** Текст ответа владельца для поля ввода по кнопке. */
export function answerOf (t: OwnerTask, kind: 'done' | 'answer' | 'reject'): string {
  const head = 'Ждёт вас #' + t.id + ' «' + t.title + '»: '
  return kind === 'done' ? head + 'сделано.' : kind === 'reject' ? head + 'отказываюсь — ' : head
}

type Input = { action?: unknown, title?: unknown, why?: unknown, done_when?: unknown, numbers?: unknown }

/** Действие над списком: новый список или текст отказа для модели. */
export function apply (tasks: readonly OwnerTask[], input: Input, now: number): OwnerTask[] | string {
  switch (input.action) {
    case 'show':
      return [...tasks]
    case 'add': {
      const title = clip(input.title)
      if (title === undefined) return WHO + 'для add нужен title — что сделать владельцу'
      if (tasks.length >= TASKS_MAX) return WHO + 'не больше ' + TASKS_MAX + ' открытых дел; закрой сделанные через close'
      const task: OwnerTask = { id: tasks.reduce((m, t) => Math.max(m, t.id), 0) + 1, title, at: now }
      const why = clip(input.why)
      const doneWhen = clip(input.done_when)
      if (why !== undefined) task.why = why
      if (doneWhen !== undefined) task.doneWhen = doneWhen
      return [...tasks, task]
    }
    case 'close': {
      const nums = Array.isArray(input.numbers) ? input.numbers : []
      const ids = new Set(tasks.map(t => t.id))
      const bad = nums.filter(n => !Number.isInteger(n) || !ids.has(n as number))
      if (nums.length === 0 || bad.length > 0) return WHO + 'для close нужны номера открытых дел (смотри show)'
      return tasks.filter(t => !nums.includes(t.id))
    }
    default:
      return WHO + 'action — одно из: add, close, show'
  }
}

async function fileText ($: EngineInterface, path: string): Promise<string | null> {
  return (await $.fs.exists(path)) ? await $.fs.read(path) : null
}

/** Старт сессии, до next: объявить инструмент — он в списке с первого хода. */
export async function declareOwner ($: EngineInterface) {
  try {
    await $.tool.register(SPEC)
  } catch {}
}

/** Старт сессии, после next: дела из файла — в панель (они пережили перезапуск и сжатие). */
export async function loadOwner ($: EngineInterface) {
  try {
    const tasks = parseTasks(await fileText($, (await $.session.root()) + FILE)) ?? []
    await update($, ownerList, () => tasks)
  } catch {}
}

let queue: Promise<unknown> = Promise.resolve()

/** Ответ инструмента: вызовы по одному, чтобы чтение и запись файла не перекрывались. */
export function serveOwner (on: On) {
  on('tool.call', { tool: TOOL }, ($, e) => {
    const run = queue.then(async () => {
      const path = (await $.session.root()) + FILE
      const text = await fileText($, path)
      const before = text === null ? [] : parseTasks(text)
      if (before === null) return { deny: WHO + 'файл .claude/owner-tasks.json не разбирается — поправь его' }
      const now = await $.clock.now().catch(() => 0)
      const after = apply(before, e as Input, now)
      if (typeof after === 'string') return { deny: after }
      if (e.action !== 'show') await $.fs.write(path, JSON.stringify({ tasks: after }, null, 2) + '\n')
      await update($, ownerList, () => after)
      return { result: listOf(after) }
    })
    queue = run.catch(() => undefined)
    return run
  }).catch(() => ({ deny: WHO + 'файл .claude/owner-tasks.json не прочитан или не записан — список не изменён' }))
}
