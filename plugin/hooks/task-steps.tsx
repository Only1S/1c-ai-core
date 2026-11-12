// Мод «шаги задачи»: инструмент модели — шаги с галочками в .claude/task-steps.json проекта; список — в панели ядра
// Подключается из status-band.tsx: hooks.json плагина берёт один модуль, и в модуле — один обработчик на событие
import { atom, update } from 'claude-code'
import type { EngineInterface, On, ToolSpec } from 'claude-code'

import type { Step, StepSince, StepsProgress } from './status-band.d'

const list = atom({ plugin: 'ones-core', key: 'task-steps-list' } as const, null as Step[] | null)
const since = atom({ plugin: 'ones-core', key: 'task-steps-since' } as const, null as StepSince | null)

const TOOL = 'mcp__ones-core__task_steps'
const FILE = '/.claude/task-steps.json'
const TEXT_MAX = 200
const STEPS_MAX = 50
const WHO = 'шаги задачи: '

const SPEC: ToolSpec = {
  name: 'task_steps',
  description: 'Шаги текущей задачи с галочками: хранятся в .claude/task-steps.json проекта и переживают сжатие контекста, '
    + 'список виден владельцу в панели ядра, текущий шаг — первый неотмеченный. Список всегда отражает текущую работу: взялся за другое — сразу clear и add, иначе панель показывает не то. Многошаговая задача — clear, затем add со всеми шагами '
    + '(card — слаг карточки доработки, если она есть); шаг готов — done с его номером; после сжатия контекста — show.',
  inputSchema: {
    type: 'object',
    properties: {
      action: { type: 'string', enum: ['add', 'done', 'show', 'clear'], description: 'add — шаги в конец списка, done — отметить выполненными, show — показать, clear — пустой список' },
      steps: { type: 'array', items: { type: 'string' }, description: 'для add: тексты шагов, по одному действию на шаг' },
      numbers: { type: 'array', items: { type: 'integer', minimum: 1 }, description: 'для done: номера шагов из show, с 1' },
      card: { type: 'string', description: 'для add: слаг карточки доработки docs-project/<направление>/<слаг>.md' },
    },
    required: ['action'],
  },
  isDeferred: false, // схема — сразу в списке инструментов: агент должен знать о нём без поиска
}

/** Шаги из файла; чужие записи пропускаются; пустой файл — пустой список; файл не разбирается или без списка steps — null. */
export function parseSteps (text: string | null): Step[] | null {
  const t = (text ?? '').replace(/^﻿/, '')   // BOM пишет PowerShell 5 (Set-Content -Encoding UTF8)
  if (text !== null && t.trim() === '') return []
  try {
    const d = JSON.parse(t)
    if (!Array.isArray(d?.steps)) return null
    const raw: unknown[] = d.steps
    return raw.flatMap(s => {
      const o = s as { text?: unknown, done?: unknown, card?: unknown } | null
      if (typeof o?.text !== 'string') return []
      return [typeof o.card === 'string' ? { text: o.text, done: o.done === true, card: o.card } : { text: o.text, done: o.done === true }]
    })
  } catch {
    return null
  }
}

/** Прогресс списка; пустой список — null. */
export function progressOf (steps: readonly Step[]): StepsProgress | null {
  return steps.length === 0 ? null : { done: steps.filter(s => s.done).length, total: steps.length }
}

/** Список для модели: номер, галочка, текст, карточка. */
export function listOf (steps: readonly Step[]): string {
  const p = progressOf(steps)
  if (p === null) return 'Шагов нет.'
  return ['Шаги задачи ' + p.done + '/' + p.total + ':', ...steps.map((s, i) => (i + 1) + '. [' + (s.done ? 'x' : ' ') + '] ' + s.text + (s.card ? ' (' + s.card + ')' : ''))].join('\n')
}

type Input = { action?: unknown, steps?: unknown, numbers?: unknown, card?: unknown }

/** Действие над списком: новый список или текст отказа для модели. */
export function apply (steps: readonly Step[], input: Input): Step[] | string {
  switch (input.action) {
    case 'show':
      return [...steps]
    case 'clear':
      return []
    case 'add': {
      const texts = Array.isArray(input.steps) ? input.steps.filter((t): t is string => typeof t === 'string').map(t => t.trim().slice(0, TEXT_MAX)).filter(t => t !== '') : []
      if (texts.length === 0) return WHO + 'для add нужен непустой steps — тексты шагов'
      if (steps.length + texts.length > STEPS_MAX) return WHO + 'не больше ' + STEPS_MAX + ' шагов в списке; начните заново через clear'
      const card = typeof input.card === 'string' && input.card.trim() !== '' ? input.card.trim() : undefined
      return [...steps, ...texts.map(text => card === undefined ? { text, done: false } : { text, done: false, card })]
    }
    case 'done': {
      const nums = Array.isArray(input.numbers) ? input.numbers : []
      const bad = nums.filter(n => !Number.isInteger(n) || n < 1 || n > steps.length)
      if (nums.length === 0 || bad.length > 0) return WHO + 'для done нужны номера шагов от 1 до ' + steps.length + ' (смотри show)'
      return steps.map((s, i) => nums.includes(i + 1) ? { ...s, done: true } : s)
    }
    default:
      return WHO + 'action — одно из: add, done, show, clear'
  }
}

/** Текст файла шагов; нет файла — null. */
async function fileText ($: EngineInterface, path: string): Promise<string | null> {
  return (await $.fs.exists(path)) ? await $.fs.read(path) : null
}

/** Старт сессии, до next: объявить инструмент — тогда он в списке с первого хода. */
export async function declareSteps ($: EngineInterface) {
  try {
    await $.tool.register(SPEC)
  } catch {}
}

/** Старт сессии, после next: список из файла — в панель (он пережил перезапуск и сжатие). */
export async function loadSteps ($: EngineInterface) {
  try {
    const steps = parseSteps(await fileText($, (await $.session.root()) + FILE)) ?? []
    await update($, list, () => steps)
  } catch {}
}

// Вызовы инструмента — по одному: чтение, правка и запись файла не перекрываются (два done подряд не теряют друг друга)
let queue: Promise<unknown> = Promise.resolve()

/** Ответ инструмента. Старт сессии — у модуля плагина (один обработчик на событие): он зовёт declareSteps и loadSteps. */
export function serveSteps (on: On) {
  on('tool.call', { tool: TOOL }, ($, e) => {
    // список общий на сессию: помощник его только смотрит, иначе его clear затирает план основного агента (аудит 30.10.2026)
    if (e.agentId !== undefined && e.action !== 'show') {
      return Promise.resolve({ deny: WHO + 'список шагов ведёт основной агент; помощнику доступно только show' })
    }
    const run = queue.then(async () => {
      const path = (await $.session.root()) + FILE
      const text = await fileText($, path)
      const before = text === null ? [] : parseSteps(text)
      // испорченный файл не затираем молча: заново — только явным clear
      if (before === null && e.action !== 'clear') return { deny: WHO + 'файл .claude/task-steps.json не разбирается — поправь его или начни заново: clear' }
      const after = apply(before ?? [], e as Input)
      if (typeof after === 'string') return { deny: after }
      if (e.action !== 'show') await $.fs.write(path, JSON.stringify({ steps: after }, null, 2) + '\n')
      await update($, list, () => after)
      const current = after.find(s => !s.done)?.text ?? null
      const at = await $.clock.now().catch(() => null)
      await update($, since, s => (s?.text === current ? s : current === null || at === null ? null : { text: current, at }))
      return { result: listOf(after) }
    })
    queue = run.catch(() => undefined)
    return run
  }).catch(() => ({ deny: WHO + 'файл .claude/task-steps.json не прочитан или не записан — список не изменён' }))
}
