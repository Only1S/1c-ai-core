// Свои инструменты ядра только на чтение (волна 3, шаг 3.8): «состояние доработки» (work_status) и «проверки хода» (turn_checks).
// «Только чтение» держится устройством: обработчики получают не $, а ReadOnlyIO (work-data.ts) — чтение файла и два своих
// скрипта в режиме чтения; тест work-pane.test.tsx ловит любую запись и чужой процесс, contour-tests §79 — вызовы $ в этом файле.
// Подключается из status-band.tsx: модуль плагина один, и старт сессии у модов общий (там зовётся declareTools).
import type { EngineInterface, On, ToolSpec } from 'claude-code'

import { cardText, checksText, loadChecks, loadPortfolio, loadSteps, pickCard, portfolioText, readOnlyIO, stepsText } from './work-data'
import type { ReadOnlyIO } from './work-data'

const STATUS = 'mcp__ones-core__work_status'
const CHECKS = 'mcp__ones-core__turn_checks'

const SPECS: readonly ToolSpec[] = [{
  name: 'work_status',
  description: 'Только чтение. Состояние доработки 1С по конвейеру ядра: карточка docs-project/ (стадия, следующий шаг, чего не хватает '
    + 'выходу стадии, строки матрицы готовности по статусам), шаги задачи и портфель всех доработок. Без card — последняя изменённая '
    + 'карточка. Звать в начале работы над доработкой и после сжатия контекста; стадию переводит /ones-core:plan, не этот инструмент.',
  inputSchema: {
    type: 'object',
    properties: { card: { type: 'string', description: 'слаг карточки или <направление>/<слаг>' } },
  },
  isDeferred: false,
}, {
  name: 'turn_checks',
  description: 'Только чтение. Проверки текущего хода тем же кодом, что гейт конца хода: какие проверки уже были (validate_module, '
    + 'стандарты, парные валидаторы, тесты), чего гейт ещё потребует, взведён ли гейт качества по правкам .bsl, последний след '
    + 'прогона и замечания проверок в сессии. Звать перед завершением хода с правками кода или метаданных 1С.',
  inputSchema: { type: 'object', properties: {} },
  isDeferred: false,
}]

/** Состояние доработки: карточка (по ссылке или последняя изменённая), шаги задачи, портфель. */
export async function workStatus (io: ReadOnlyIO, ref?: string): Promise<string> {
  const [p, steps] = await Promise.all([loadPortfolio(io), loadSteps(io)])
  if (typeof p === 'string') return p + '\n\n' + stepsText(steps)
  const cur = p.docs ? pickCard(p, ref) : null
  return [typeof cur === 'string' ? cur : cur ? cardText(cur) : null, stepsText(steps), portfolioText(p, typeof cur === 'object' ? cur : null)]
    .filter(Boolean).join('\n\n')
}

/** Проверки хода основного агента или помощника (по журналу его хода). */
export async function turnChecks (io: ReadOnlyIO, agentId?: string): Promise<string> {
  const c = await loadChecks(io, { agentId })
  return typeof c === 'string' ? c : checksText(c, 'live')
}

/** Старт сессии, до next: объявить инструменты — они в списке с первого хода. */
export async function declareTools ($: EngineInterface) {
  for (const spec of SPECS) {
    try {
      await $.tool.register(spec)
    } catch {}
  }
}

/** Ответы инструментов: сбой — отказ с причиной, а не тишина. */
export function serveTools (on: On) {
  on('tool.call', { tool: STATUS }, async ($, e) => {
    const card = (e as { card?: unknown }).card
    return { result: await workStatus(await readOnlyIO($), typeof card === 'string' && card.trim() !== '' ? card.trim() : undefined) }
  }).catch(() => ({ deny: 'work_status: состояние доработки не прочитано' }))
  on('tool.call', { tool: CHECKS }, async ($, e) => ({ result: await turnChecks(await readOnlyIO($), e.agentId) }))
    .catch(() => ({ deny: 'turn_checks: проверки хода не прочитаны' }))
}
