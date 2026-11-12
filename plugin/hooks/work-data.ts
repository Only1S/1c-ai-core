// Данные панели «Доработка» (work-pane.tsx) и инструментов ядра на чтение (core-tools.tsx): портфель доработок, шаги задачи,
// проверки хода. Только чтение: файлы — $.fs.read, программы — два своих скрипта плагина в режиме чтения (readOnlyIO);
// своих правил тут нет — «чего не хватает» считает gen-portfolio.py (как lint-project-docs), ход судит turn-checks.py (как stop-guard).
import type { EngineInterface } from 'claude-code'

import { runPython } from './run-python'
import type { Step, WorkCard, WorkChecks, WorkPortfolio, WorkTurn, WorkView } from './status-band.d'
import { listOf, parseSteps } from './task-steps'

/** Всё, чем данные доработки трогают мир: корень, сессия, чтение файла и запуск своего скрипта только на чтение. */
export type ReadOnlyIO = {
  readonly root: string
  readonly sessionId: string
  read: (path: string) => Promise<string | null>
  run: (script: Script, args: readonly string[], stdin?: string) => Promise<{ code: number, out: string, err: string }>
}
type Script = 'portfolio' | 'checks'

// единственные программы, которые запускает этот модуль: путь от корня плагина и флаг режима чтения
const SCRIPTS: Readonly<Record<Script, readonly string[]>> = {
  portfolio: ['/tools/pipeline/gen-portfolio.py', '--json'],
  checks: ['/tools/checks/turn-checks.py'],
}
const RUN_TIMEOUT_MS = 30000
const STEPS_FILE = '/.claude/task-steps.json'
const LINE_MAX = 200

export async function readOnlyIO ($: EngineInterface): Promise<ReadOnlyIO> {
  const [root, sessionId] = await Promise.all([$.session.root(), $.session.id()])
  const plugin = $.plugin.root
  return {
    root,
    sessionId,
    read: async path => {
      try {
        return (await $.fs.exists(path)) ? await $.fs.read(path) : null
      } catch {
        return null
      }
    },
    run: async (script, args, stdin) => {
      const [path, ...flags] = SCRIPTS[script]
      try {
        // -I: без PYTHON* окружения и пути скрипта в sys.path; -B: без кэша байткода — скрипт ничего не оставляет
        const r = await runPython((argv, init) => $.process.run(argv, init), ['-I', '-B', plugin + path, ...flags, ...args],
          { cwd: root, timeoutMs: RUN_TIMEOUT_MS, ...(stdin === undefined ? {} : { stdin }) })
        return { code: r.exitCode, out: r.stdout, err: r.stderr }
      } catch (e) {
        return { code: -1, out: '', err: String(e) }
      }
    },
  }
}

const lastLine = (s: string) => (s.trim().split(/\r?\n/).pop() ?? '').slice(0, LINE_MAX)
const arr = <T>(v: unknown, ok: (x: unknown) => x is T): T[] => (Array.isArray(v) ? v.filter(ok) : [])
const str = (v: unknown): v is string => typeof v === 'string'

/** Портфель из вывода gen-portfolio.py --json; разобрать нельзя — null. */
export function portfolioOf (out: string): WorkPortfolio | null {
  try {
    const d = JSON.parse(out)
    if (typeof d?.docs !== 'boolean') return null
    const cards = arr(d.cards, (c): c is Record<string, unknown> => typeof c === 'object' && c !== null && str((c as { rel?: unknown }).rel))
      .map((c): WorkCard => ({
        rel: String(c.rel), title: str(c.title) ? c.title : String(c.rel), key: str(c.key) ? c.key : '', raw: str(c.raw) ? c.raw : '',
        stage: str(c.stage) ? c.stage : null, next: str(c.next) ? c.next : null, rejected: c.rejected === true,
        missing: arr(c.missing, str),
        matrix: Object.fromEntries(Object.entries(typeof c.matrix === 'object' && c.matrix !== null ? c.matrix : {}).filter(([, n]) => typeof n === 'number')) as Record<string, number>,
        mtime: typeof c.mtime === 'number' ? c.mtime : 0,
      }))
    const state = d.portfolio === 'in-sync' || d.portfolio === 'stale' ? d.portfolio : 'absent'
    return { docs: d.docs, portfolio: state, cards }
  } catch {
    return null
  }
}

/** Проверки хода из вывода turn-checks.py; разобрать нельзя — null. */
export function checksOf (out: string): WorkChecks | null {
  try {
    const d = JSON.parse(out)
    const t = d?.turn
    if (typeof t?.found !== 'boolean') return null
    const ev = d.evidence
    return {
      turn: {
        found: t.found, calls: typeof t.calls === 'number' ? t.calls : 0, edits: str(t.edits) ? t.edits : null, missing: arr(t.missing, str),
        ran: arr(t.ran, (r): r is { what: string, ok?: unknown } => str((r as { what?: unknown } | null)?.what))
          .map(r => ({ what: r.what, ok: typeof r.ok === 'boolean' ? r.ok : null })),
      },
      gate: { mode: str(d.gate?.mode) ? d.gate.mode : 'block', armed: arr(d.gate?.armed, str) },
      evidence: ev && str(ev.stamp)
        ? { stamp: ev.stamp, session: str(ev.session) ? ev.session : '', own: ev.own === true, checked: arr(ev.checked, str),
            skipped: arr(ev.skipped, str), notVerified: arr(ev.notVerified, str) }
        : null,
      observations: arr(d.observations, (o): o is { kind: string, count?: unknown, sample?: unknown } => str((o as { kind?: unknown } | null)?.kind))
        .map(o => ({ kind: o.kind, count: typeof o.count === 'number' ? o.count : 1, sample: str(o.sample) ? o.sample : '' })),
    }
  } catch {
    return null
  }
}

/** Портфель проекта: значение или текст ошибки. */
export async function loadPortfolio (io: ReadOnlyIO): Promise<WorkPortfolio | string> {
  const r = await io.run('portfolio', ['--root', io.root])
  return (r.code === 0 ? portfolioOf(r.out) : null) ?? 'портфель не прочитан: ' + (lastLine(r.err) || 'код ' + r.code)
}

/** Проверки хода (основного или помощника); answer — итоговый ответ хода, когда ход уже закончен. */
export async function loadChecks (io: ReadOnlyIO, opts: { agentId?: string, answer?: string } = {}): Promise<WorkChecks | string> {
  const args = ['--root', io.root, '--session', io.sessionId, ...(opts.agentId ? ['--agent', opts.agentId] : []),
    ...(opts.answer === undefined ? [] : ['--answer-stdin'])]
  const r = await io.run('checks', args, opts.answer)
  return (r.code === 0 ? checksOf(r.out) : null) ?? 'проверки хода не прочитаны: ' + (lastLine(r.err) || 'код ' + r.code)
}

/** Шаги задачи из .claude/task-steps.json (их ведёт инструмент task_steps); файла нет или он испорчен — null. */
export async function loadSteps (io: ReadOnlyIO): Promise<Step[] | null> {
  const t = await io.read(io.root + STEPS_FILE)
  return t === null ? null : parseSteps(t)
}

/** Карточка по слагу или <направление>/<слаг>; без ссылки — последняя изменённая (как у строки над полем ввода). */
export function pickCard (p: WorkPortfolio, ref?: string): WorkCard | string | null {
  if (!ref) return [...p.cards].sort((a, b) => b.mtime - a.mtime)[0] ?? null
  const want = ref.replace(/\\/g, '/').replace(/\.md$/i, '')
  const found = p.cards.filter(c => c.rel.slice(0, -3) === want || c.rel.slice(0, -3).endsWith('/' + want))
  if (found.length === 1) return found[0]
  const names = (found.length ? found : p.cards).map(c => c.rel.slice(0, -3)).join(', ') || 'карточек нет'
  return (found.length ? 'слаг «' + ref + '» неоднозначен — укажи <направление>/<слаг>: ' : 'карточки «' + ref + '» нет; есть: ') + names
}

const stageOf = (c: WorkCard) => '`' + (c.key || c.raw) + '` — ' + (c.rejected ? 'закрыто с отказом' : c.stage ?? 'ключ вне словаря')
const matrixOf = (m: Record<string, number>) => {
  const total = Object.values(m).reduce((a, b) => a + b, 0)
  return total === 0 ? null : Object.entries(m).map(([k, n]) => k + ' ' + n).join(', ') + ' (из ' + total + ')'
}
const SYNC: Record<WorkPortfolio['portfolio'], string> = {
  'in-sync': 'docs-project/pipeline.md совпадает с карточками',
  stale: 'docs-project/pipeline.md отстал от карточек — пересоберёт /ones-core:plan',
  absent: 'docs-project/pipeline.md ещё не собран — соберёт /ones-core:plan',
}

/** Карточка: стадия, следующий шаг, выход стадии, матрица. */
export function cardText (c: WorkCard): string {
  const mx = matrixOf(c.matrix)
  return [
    '**Доработка:** ' + c.title + ' — `docs-project/' + c.rel + '`',
    '**Стадия:** ' + stageOf(c),
    c.next ? '**Следующий шаг:** ' + c.next : null,
    c.rejected ? null : '**Выход стадии:** ' + (c.missing.length ? 'не хватает — ' + c.missing.join('; ') : 'готов'),
    mx ? '**Матрица готовности:** ' + mx : null,
  ].filter(Boolean).join('\n')
}

/** Портфель списком (узкая панель переносит строки списка лучше, чем таблицу). */
export function portfolioText (p: WorkPortfolio, current?: WorkCard | null): string {
  if (!p.docs) return 'В проекте нет `docs-project/` — карточек доработок нет (папку заводит `/ones-core:setup`).'
  if (p.cards.length === 0) return 'Доработок нет — карточку заводит `/ones-core:plan new <направление> <слаг> <название>`.'
  return ['**Портфель — ' + p.cards.length + ':** ' + SYNC[p.portfolio], ...p.cards.map(c =>
    '- ' + (c === current ? '▸ ' : '') + c.title + ' · ' + stageOf(c) + (c.next ? ' · шаг: ' + c.next : '')
    + (c.missing.length && !c.rejected ? ' · не хватает: ' + c.missing.join('; ') : ''))].join('\n')
}

/** Шаги задачи; null — файла шагов нет. */
export function stepsText (steps: readonly Step[] | null): string {
  return steps === null || steps.length === 0 ? '_Шагов задачи нет._' : listOf(steps)
}

/** Ход: правки 1С и чего гейт конца хода потребует (live — ход идёт) или требовал (done — последний законченный). */
function turnLines (t: WorkTurn, mode: string, phase: 'live' | 'done'): string[] {
  const head = phase === 'live' ? 'Ход' : 'Последний ход'
  if (!t.found) return [head + ': журнал хода не найден — проверки хода не видны']
  const verdict = t.edits === null ? head + ': правок 1С нет — гейт конца хода молчит'
    : head + ': правки 1С (' + t.edits + '); гейт конца хода (режим ' + mode + ') '
      + (t.missing.length ? (phase === 'live' ? 'потребует' : 'требовал') + ': ' + t.missing.map((m, i) => (i + 1) + ') ' + m).join('; ')
        : 'доволен — всё нужное в ходе есть')
  return [
    verdict,
    t.ran.length ? 'уже проверено: ' + t.ran.map(r => r.what + (r.ok === false ? ' (ошибка)' : '')).join('; ') : null,
  ].filter((x): x is string => x !== null)
}

/** Проверки: ход (если он есть), гейт качества по .bsl, последний след прогона, замечания проверок конца хода в сессии. */
export function checksText (c: WorkChecks, phase: 'live' | 'done'): string {
  const ev = c.evidence
  return ['**Проверки**', ...[
    ...(c.turn ? turnLines(c.turn, c.gate.mode, phase) : []),
    c.gate.armed.length
      ? 'гейт качества взведён по ' + c.gate.armed.length + ' правкам .bsl (' + c.gate.armed.slice(0, 3).join(', ') + (c.gate.armed.length > 3 ? ', …' : '')
        + ') — после полного набора проверок запиши след: `gate-evidence.py --checked … --not-verified …`'
      : 'гейт качества по правкам .bsl не взведён',
    ev ? 'последний след прогона: ' + ev.stamp + (ev.own ? '' : ' (другая сессия)') + ' — проверено ' + ev.checked.length + ' · пропущено '
      + ev.skipped.length + ' · НЕ проверено ' + ev.notVerified.length : 'следа прогона проверок нет (logs/gate-evidence.md)',
    c.observations.length ? 'замечания проверок конца хода в сессии: ' + c.observations.map(o => o.kind + ' ×' + o.count).join(', ') : null,
  ].filter((x): x is string => x !== null).map(x => '- ' + x)].join('\n')
}

/** Тело панели «Доработка» — markdown; null — панель ещё не обновлялась. */
export function workText (v: WorkView | null, steps: readonly Step[] | null): string {
  if (v === null) return '_Панель ещё не обновлялась — «Обновить» или `/ones-core:work`._'
  const p = v.portfolio
  const cur = p ? pickCard(p) : null
  return [
    p && typeof cur === 'object' && cur !== null ? cardText(cur) : null,
    stepsText(steps),
    v.checks ? checksText(v.checks, 'done') : null,
    p ? portfolioText(p, typeof cur === 'object' ? cur : null) : null,
    v.errors.length ? '_' + v.errors.join('; ') + '_' : null,
    v.turns === null ? null : '_Обновлено на ходе ' + v.turns + '._',
  ].filter(Boolean).join('\n\n')
}
