// Мод «Доработка» (волна 3, шаг 3.2): /work открывает панель рядом с чатом — карточка и её стадия, шаги задачи
// с галочками, состояние проверок и портфель доработок. Обновляется после каждого хода, пока открыта, кнопкой «Обновить»
// и сразу, когда агент отмечает шаг (инструмент task_steps). Данные — work-data.ts, только чтение.
// По типам API (2.1.309) Pane рисуется на всех поверхностях; где поверхность панелей не ставит (ui.open: isPlaced false),
// команда отвечает тем же текстом в чате. Подключается из status-band.tsx: старт сессии и конец хода у модов общие.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import type { Step, WorkView } from './status-band.d'
import { loadChecks, loadPortfolio, loadSteps, readOnlyIO, workText } from './work-data'

const WORK_PANE = 'ones-core-work'
const TITLE = 'Доработка'
// смена полей WorkView — новый тег: значение прежней версии мода переживает перезагрузку
const view = atom({ plugin: 'ones-core', key: 'work-pane-view' } as const, null as WorkView | null, { shape: 'work-view-1' })
// пишет task-steps.tsx: чтение подписывает панель — отмеченный шаг перерисовывает её сразу
const stepsList = atom({ plugin: 'ones-core', key: 'task-steps-list' } as const, null as Step[] | null)

/** Старт сессии, до next: объявить команду — она в меню с первого хода. */
export async function declareWork ($: EngineInterface) {
  try {
    await $.command.register({ name: 'work', description: 'Панель «Доработка»: карточка и стадия, шаги задачи, проверки, портфель доработок' })
  } catch {}
}

/** Перечитать портфель и проверки. answer — итоговый ответ законченного хода: тогда «последний ход» судится заново;
 *  без него (команда, кнопка) ход в журнале — сама команда, и остаётся тот, что был посчитан после хода. */
export async function refreshWork ($: EngineInterface, answer?: string) {
  const io = await readOnlyIO($)
  const [p, c, turns, before] = await Promise.all([loadPortfolio(io), loadChecks(io, { answer }), $.session.turns(), read($, view)])
  const last = answer !== undefined ? (typeof c === 'string' ? null : c.turn) : before?.checks?.turn ?? null
  const checks = typeof c === 'string' ? (before?.checks ? { ...before.checks, turn: last } : null) : { ...c, turn: last }
  await update($, view, () => ({
    portfolio: typeof p === 'string' ? before?.portfolio ?? null : p,
    checks,
    turns,
    errors: [p, c].filter((x): x is string => typeof x === 'string'),
  }))
}

/** Конец хода главного агента: панель открыта — обновить. */
export async function refreshWorkIfOpen ($: EngineInterface, answer?: string) {
  try {
    if ((await $.ui.panes()).some(p => p.id === WORK_PANE)) await refreshWork($, answer)
  } catch {}
}

/** Команда и панель. Матчеры с именем панели и команды — в этом файле, чтобы валидатор видел их значения. */
export function serveWork (on: On) {
  on('command.run', { command: 'work' }, async $ => {
    try {
      await refreshWork($)
    } catch {}
    const opened = await $.ui.open({ id: WORK_PANE, title: TITLE })
    if (opened.isPlaced) return { text: 'Панель «Доработка» открыта.' }
    const steps = await loadSteps(await readOnlyIO($))
    return { text: workText(await read($, view), steps) + '\n\n_Панель здесь не рисуется (' + opened.reason + ') — то же текстом._' }
  })
  on('ui.render', { component: 'Pane', requestId: WORK_PANE }, async ($, e) => {
    const { Box, Button, Markdown } = $.ui.resolve(e)
    const [v] = await Promise.all([read($, view), read($, stepsList)])
    const steps = await loadSteps(await readOnlyIO($))
    return (
      <Box flexDirection="column">
        <Markdown text={workText(v, steps)} />
        <Button key="ones-work-refresh" label="Обновить" onPress={() => { void refreshWork($).catch(() => undefined) }} />
      </Box>
    )
  })
}
