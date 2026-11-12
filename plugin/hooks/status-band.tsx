// Панель ядра сбоку от чата: сбор данных и рисование (сбой фильтра, доработка и база, шаги, итог проверки, что нового); тексты — core-pane.tsx
// Единственный модуль плагина (hooks.json берёт один): подключает и остальные моды
import { atom, read, update } from 'claude-code'
import type { EngineInterface, PluginOptions, Register, Timer } from 'claude-code'

import type { CardLine, CheckMark, Facts, Step, StepSince } from './status-band.d'
import { declareSteps, loadSteps, serveSteps } from './task-steps'
import { ageOf, answerOf, declareOwner, loadOwner, serveOwner } from './owner-tasks'
import type { OwnerTask } from './owner-tasks'
import { serveCommitRules } from './commit-rules'
import { serveInboundFilter } from './inbound-filter'
import { serveAskGuard } from './ask-guard'
import { serveCheck, startCheck } from './project-check'
import { CORE_PANE, FAULT_HINT, PANE_COLUMNS, announceLongTurn, announceVersion, checkText, currentStep, declareCore, newerVersion, notesOf, paneText, paneTitle, stagesLine, stagesSvg, stepLine } from './core-pane'
import type { CoreView } from './core-pane'
import { declareWork, refreshWorkIfOpen, serveWork } from './work-pane'
import { declareTools, serveTools } from './core-tools'

const NO_FACTS: Facts = { base: null, step: null, cards: [], version: null }
const facts = atom({ plugin: 'ones-core', key: 'status-band-facts' } as const, NO_FACTS)
const suggested = atom({ plugin: 'ones-core', key: 'status-band-suggested' } as const, null as string | null)
const notesShown = atom({ plugin: 'ones-core', key: 'core-pane-notes' } as const, false)
const busy = atom({ plugin: 'ones-core', key: 'core-pane-busy' } as const, false)
const tick = atom({ plugin: 'ones-core', key: 'core-pane-tick' } as const, 0)
const latest = atom({ plugin: 'ones-core', key: 'core-pane-latest' } as const, null as string | null)
// пишут другие моды: task-steps.tsx, inbound-filter.ts и project-check.tsx; чтение подписывает панель на их записи
const steps = atom({ plugin: 'ones-core', key: 'task-steps-list' } as const, null as Step[] | null)
// дела владельца пишет owner-tasks.tsx; атом объявлен здесь: движок модов читает только атомы из констант этого файла
const ownerList = atom({ plugin: 'ones-core', key: 'owner-tasks-list' } as const, null as OwnerTask[] | null)
const fault = atom({ plugin: 'ones-core', key: 'inbound-filter-fault' } as const, null as string | null)
const lastCheck = atom({ plugin: 'ones-core', key: 'project-check-last' } as const, null as CheckMark | null)
const since = atom({ plugin: 'ones-core', key: 'task-steps-since' } as const, null as StepSince | null)

// значок текущего шага, пока идёт ход: крутится сам, панель не перерисовывается; цвет явный — рамка картинки темы окна не видит
const SPINNER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#f5c518" stroke-opacity="0.3" stroke-width="2"/>'
  + '<path d="M8 2a6 6 0 0 1 6 6" fill="none" stroke="#f5c518" stroke-width="2" stroke-linecap="round">'
  + '<animateTransform attributeName="transform" type="rotate" from="0 8 8" to="360 8 8" dur="1s" repeatCount="indefinite"/></path></svg>'

const STEP_MARK = '**Следующий шаг:**'
const STEP_MAX = 60             // подсказка в поле ввода
const JOURNAL_STEP_MAX = 240    // в панели есть место: строка журнала показывается целиком
const CARDS_SHOWN = 5
const CHANNEL = 'https://github.com/Only1S/1c-ai-core.git'
const CHANNEL_TIMEOUT_MS = 8000
const TICK_MS = 30000
const SUBJECT_MAX = 24

// Карточка доработки (docs/design/customization-pipeline.md): поля шапки «Стадия:» и «Следующий шаг:»
const CARD_FIELD = (name: string) => new RegExp('^\\s*(?:[-*]\\s+)?(?:\\*\\*)?' + name + '(?:\\*\\*)?:(?:\\*\\*)?\\s*(.*)$')
const CARD_STAGE = CARD_FIELD('Стадия')
const CARD_STEP = CARD_FIELD('Следующий шаг')
const STAGES: Readonly<Record<string, string>> = {
  request: 'заявка', analysis: 'разбор и ТЗ', slicing: 'план срезов', build: 'реализация', acceptance: 'приёмка', done: 'слияние и закрытие',
}
const STAGE_ORDER = Object.values(STAGES)
const CARD_HEAD_LINES = 40     // поля — в шапке, не в теле
const CARD_BYTES_MAX = 256 * 1024 // журналы крупнее и карточками не бывают
const CARD_SCAN_MAX = 30       // сколько свежих доков читать за обновление
const CARD_DEPTH = 3

const cut = (s: string, max: number) => (s.length > max ? s.slice(0, max - 1).trimEnd() + '…' : s)

/** Ключ default реестра баз .v8-project.json. */
export function baseOf (registry: string | null): string | null {
  if (registry === null) return null
  try {
    const d = JSON.parse(registry)
    return typeof d?.default === 'string' && d.default.trim() !== '' ? d.default.trim() : null
  } catch {
    return null
  }
}

/** Строка «**Следующий шаг:** …» журнала (правило work-journals-and-commits п.12). */
export function stepOf (worklog: string | null): string | null {
  const line = worklog?.split('\n').find(l => l.startsWith(STEP_MARK))
  const s = line?.slice(STEP_MARK.length).trim() ?? ''
  return s === '' ? null : cut(s, JOURNAL_STEP_MAX)
}

/** Шапка карточки: стадия по-русски (ключ из конвейера, иной текст — как есть) и «Следующий шаг:»; без «Стадия:» — null. */
export function cardOf (text: string | null): { stage: string, step: string | null } | null {
  const head = text?.split(/\r?\n/).slice(0, CARD_HEAD_LINES) ?? []
  const field = (re: RegExp) => head.map(l => re.exec(l)?.[1]).find(v => v !== undefined)?.replace(/[`*]/g, '').trim() ?? ''
  const raw = field(CARD_STAGE)
  if (raw === '') return null
  const key = /[a-z]+/.exec(raw.toLowerCase())?.[0] ?? ''
  const step = field(CARD_STEP)
  // только свои ключи словаря: constructor и прочее из прототипа — текст как есть
  const stage = Object.prototype.hasOwnProperty.call(STAGES, key) ? STAGES[key] : cut(raw, SUBJECT_MAX)
  return { stage, step: step === '' ? null : cut(step, STEP_MAX) }
}

/** Поле version манифеста плагина. */
export function versionOf (manifest: string | null): string | null {
  if (manifest === null) return null
  try {
    const v = JSON.parse(manifest)?.version
    return typeof v === 'string' && v.trim() !== '' ? v.trim() : null
  } catch {
    return null
  }
}

async function file ($: EngineInterface, path: string): Promise<string | null> {
  try {
    return (await $.fs.exists(path)) ? await $.fs.read(path) : null
  } catch {
    return null
  }
}

type Doc = { path: string, name: string, mtimeMs: number, size: number }

async function docs ($: EngineInterface, dir: string, depth: number): Promise<Doc[]> {
  try {
    const out: Doc[] = []
    for (const en of await $.fs.list(dir)) {
      const path = dir + '/' + en.name
      if (en.kind === 'file' && en.name.endsWith('.md')) out.push({ path, name: en.name, mtimeMs: en.mtimeMs, size: en.size })
      else if (en.kind === 'dir' && depth > 0 && !en.name.startsWith('.')) out.push(...await docs($, path, depth - 1))
    }
    return out
  } catch {
    return []
  }
}

/** Карточки docs-project/**\/*.md с полем «Стадия:», свежие первыми: идущие доработки и «Следующий шаг:» самой свежей. */
async function latestCards ($: EngineInterface, root: string): Promise<{ cards: CardLine[], step: string | null }> {
  const fresh = (await docs($, root + '/docs-project', CARD_DEPTH))
    .filter(d => d.size <= CARD_BYTES_MAX).sort((a, b) => b.mtimeMs - a.mtimeMs).slice(0, CARD_SCAN_MAX)
  const cards: CardLine[] = []
  let step: string | null = null
  let first = true
  for (const d of fresh) {
    const c = cardOf(await file($, d.path))
    if (c === null) continue
    if (first) step = c.step
    first = false
    if (c.stage !== STAGES.done) cards.push({ name: d.name.slice(0, -3), stage: c.stage, index: STAGE_ORDER.indexOf(c.stage) })
  }
  return { cards: cards.slice(0, CARDS_SHOWN), step }
}

/** «Следующий шаг:» карточки — подсказкой поля ввода (Tab берёт), один раз на текст; не показалась — попробуем после хода.
 *  Не ждём: под открытым окном подсказка ждёт, пока оно закроется, а обработчик старта и хода держать нельзя. */
function suggest ($: EngineInterface, text: string | null) {
  if (text === null) return
  void read($, suggested)
    .then(last => last === text ? undefined : $.prompt.suggest({ text }).then(r => r.isShown ? update($, suggested, () => text) : undefined))
    .catch(() => undefined)
}

async function refresh ($: EngineInterface, isMain: boolean) {
  try {
    const root = await $.session.root()
    const [registry, worklog, manifest, found] = await Promise.all([
      file($, root + '/.v8-project.json'),
      file($, root + '/docs-project/worklog.md'),
      file($, $.plugin.root + '/.claude-plugin/plugin.json'),
      latestCards($, root),
    ])
    await update($, facts, () => ({ base: baseOf(registry), step: stepOf(worklog), cards: found.cards, version: versionOf(manifest) }))
    if (isMain) suggest($, found.step)
  } catch {
    await update($, facts, () => NO_FACTS)
  }
}

/** Новая версия в канале: один запрос git на старт сессии; нет сети или доступа — панель просто молчит о ней. */
async function checkLatest ($: EngineInterface, version: string | null) {
  try {
    const r = await $.process.run(['git', 'ls-remote', '--tags', CHANNEL], { timeoutMs: CHANNEL_TIMEOUT_MS })
    if (r.exitCode === 0) await update($, latest, () => newerVersion(r.stdout, version))
  } catch {}
}

/** Что показывает панель: версия и запись о ней читаются, только когда открыт раздел «Что нового». */
async function coreView ($: EngineInterface, withSteps: boolean): Promise<CoreView> {
  const [f, list, bad, check, show, working, fresh, started, , waiting] = await Promise.all([read($, facts), read($, steps), read($, fault), read($, lastCheck), read($, notesShown), read($, busy), read($, latest), read($, since), read($, tick), read($, ownerList)])
  const items = withSteps ? list ?? [] : []
  const owner = waiting ?? []
  const ownerNow = owner.length > 0 ? await $.clock.now().catch(() => null) : null
  const now = started !== null && working ? await $.clock.now().catch(() => null) : null
  const minutes = now !== null && started !== null && started.text === items.find(s => !s.done)?.text ? Math.floor((now - started.at) / 60000) : 0
  const notes = show ? notesOf(await file($, $.plugin.root + '/RELEASE-NOTES.md'), f.version) ?? '_Записи о версии ' + f.version + ' в плагине нет._' : null
  return { fault: bad, cards: f.cards ?? [], base: f.base, steps: items, step: f.step, check, version: f.version, notes, busy: working, latest: fresh, stepMinutes: minutes > 0 ? minutes : null, owner, ownerNow }
}

// таймер времени шага: идёт только пока идёт ход главного агента
let ticker: Timer | null = null

/** Панель и шаги задачи выключаются каждый своей настройкой и тогда не подключают ни одного своего обработчика;
 *  правила коммита и чистка входящих — всегда. Движок берёт один обработчик события на модуль, поэтому старт сессии — общий. */
export const register: Register = (on, options: PluginOptions) => {
  const panel = options.statusBand !== false
  const withSteps = options.taskSteps !== false
  const withOwner = panel && options.ownerTasks !== false   // «Ждёт вас» (owner-tasks.tsx): без панели делу негде показаться
  const work = options.workPane === true  // панель «Доработка» и инструменты на чтение (work-pane.tsx, core-tools.tsx)

  if (panel || withSteps || withOwner || work) {
    on('session.start', async ($, e, next) => {
      if (withSteps) await declareSteps($)
      if (withOwner) await declareOwner($)
      if (panel) await declareCore($)
      if (work) await Promise.all([declareWork($), declareTools($)])
      const r = await next(e)
      if (withSteps) await loadSteps($)
      if (withOwner) await loadOwner($)
      if (work) await refreshWorkIfOpen($)   // панель пережила перезагрузку мода
      if (!panel) return r
      await refresh($, true)
      const { version } = await read($, facts)
      await announceVersion($, version)
      void checkLatest($, version)
      void $.ui.open({ id: CORE_PANE, title: paneTitle(version), columns: PANE_COLUMNS }).catch(() => undefined)   // не хватает ширины — ждёт команды /core
      return r
    })
  }
  if (withSteps) serveSteps(on)
  if (withOwner) serveOwner(on)
  serveCommitRules(on)
  serveInboundFilter(on, { outputDigest: options.outputDigest !== false })   // выжимка длинного вывода — своей настройкой
  // «спросить вместо запрета», «кнопка проверок» — каждый своей настройкой; события, которые модуль уже
  // слушает без отбора (старт сессии, конец хода), они слушают с отбором
  if (options.askInsteadOfDeny !== false) serveAskGuard(on)
  if (options.projectCheck !== false) serveCheck(on)
  if (work) {
    serveWork(on)
    serveTools(on)
  }
  if (!panel) return   // без панели ядра панель «Доработка» обновляется командой и кнопкой: конец хода слушает только панель ядра

  // панель не встала — то же текстом в чате
  on('command.run', { command: 'core' }, async $ => {
    const opened = await $.ui.open({ id: CORE_PANE, title: paneTitle((await read($, facts)).version), columns: PANE_COLUMNS })
    return { text: opened.isPlaced ? 'Панель ядра открыта.' : paneText(await coreView($, withSteps)) + '\n\n_Панель здесь не рисуется (' + opened.reason + ') — то же текстом._' }
  })
  on('ui.render', { component: 'Pane', requestId: 'ones-core-core' }, async ($, e) => {   // литералом: так значение видит валидатор
    const { Box, Button, Markdown, Text } = $.ui.resolve(e)
    const Spinner = e.surface === 'desktop' ? $.ui.resolve(e).Svg : null   // анимация есть только в приложении, остальным — стрелка
    const v = await coreView($, withSteps)
    const current = currentStep(v.steps)
    const check = checkText(v.check)
    const level = v.check?.running ? undefined : v.check?.level
    return (
      <Box flexDirection="column" gap={1}>
        {v.fault === null ? null : (
          <Box key="ones-panel-fault" flexDirection="column">
            <Text color="error">⚠ Фильтр не запускается</Text>
            <Text color="error">{v.fault}</Text>
            <Button key="ones-panel-fix" label="Что делать" onPress={() => $.ui.toast(FAULT_HINT, { timeoutMs: 20000 })} />
          </Box>
        )}
        {v.latest === null ? null : <Box key="ones-panel-latest"><Text color="warning">Есть новая версия {v.latest}</Text></Box>}
        {(v.owner?.length ?? 0) === 0 ? null : <Box key="ones-panel-owner-count"><Text color="warning">ждёт вас: {v.owner?.length}</Text></Box>}
        {v.cards.length === 0 && v.base === null ? null : (
          <Box key="ones-panel-work" flexDirection="column">
            <Text dimColor>{'Доработки' + (v.base === null ? '' : ': база ' + v.base)}</Text>
            {v.cards.map(c => (
              <Box key={'ones-panel-card-' + c.name} flexDirection="column" marginTop={1}>
                <Text>{c.name} · {c.stage}</Text>
                {c.index < 0 ? null : Spinner !== null
                  ? <Spinner source={stagesSvg(c.index)} alt={'стадия: ' + c.stage} width={276} height={38} isInteractive />
                  : <Text dimColor>{stagesLine(c.index)}</Text>}
              </Box>
            ))}
          </Box>
        )}
        {v.steps.length === 0 ? null : (
          <Box key="ones-panel-steps" flexDirection="column">
            <Text dimColor>Шаги {v.steps.filter(s => s.done).length} из {v.steps.length}</Text>
            {v.steps.map((s, i) => (i === current && v.busy && Spinner !== null ? (
              <Box key="ones-panel-spinner" flexDirection="row" gap={1}>
                <Spinner source={SPINNER} alt="шаг выполняется" width={14} height={14} isInteractive />
                <Text bold>{stepLine(s, i, current).slice(2)}{v.stepMinutes === null ? '' : ' · ' + v.stepMinutes + ' мин'}</Text>
              </Box>
            ) : (
              <Text key={'ones-panel-step-' + i} bold={i === current} dimColor={!s.done && i !== current} color={s.done ? 'success' : undefined}>{stepLine(s, i, current)}</Text>
            )))}
          </Box>
        )}
        {v.steps.length > 0 || v.step === null ? null : (
          <Box key="ones-panel-next" flexDirection="column">
            <Text dimColor>Следующий шаг</Text>
            <Text>{v.step}</Text>
          </Box>
        )}
        {check === null ? null : (
          <Box key="ones-panel-check" flexDirection="column">
            <Text dimColor>Проверка</Text>
            <Text color={level === 'fail' ? 'error' : level === 'warn' ? 'warning' : level === 'ok' ? 'success' : undefined}>{check}</Text>
            {(v.check?.items ?? []).map((item, i) => <Text key={'ones-panel-item-' + i} color={level === 'fail' ? 'error' : 'warning'}>• {item}</Text>)}
          </Box>
        )}
        {(v.owner?.length ?? 0) === 0 ? null : (
          <Box key="ones-panel-owner" flexDirection="column">
            <Text dimColor>Ждёт вас</Text>
            {(v.owner ?? []).map(t => (
              <Box key={'ones-panel-owner-' + t.id} flexDirection="column" marginTop={1}>
                <Text bold>#{t.id} {t.title}</Text>
                {t.why ? <Text dimColor>Почему: {t.why}</Text> : null}
                {t.doneWhen ? <Text dimColor>Готово, когда: {t.doneWhen}</Text> : null}
                <Box key={'ones-panel-owner-buttons-' + t.id} flexDirection="row" flexWrap="wrap" gap={1}>
                  <Button key={'ones-panel-owner-done-' + t.id} label="Сделано" onPress={() => { void $.prompt.fill({ text: answerOf(t, 'done') }).catch(() => undefined) }} />
                  <Button key={'ones-panel-owner-answer-' + t.id} label="Ответить" onPress={() => { void $.prompt.fill({ text: answerOf(t, 'answer') }).catch(() => undefined) }} />
                  <Button key={'ones-panel-owner-reject-' + t.id} label="Отказать" onPress={() => { void $.prompt.fill({ text: answerOf(t, 'reject') }).catch(() => undefined) }} />
                  {v.ownerNow ? <Text dimColor>{ageOf(t.at, v.ownerNow)}</Text> : null}
                </Box>
              </Box>
            ))}
          </Box>
        )}
        <Box key="ones-panel-buttons" flexDirection="row" flexWrap="wrap" gap={1}>
          {options.projectCheck !== false ? <Button key="ones-panel-run-check" label="✓ Проверить" onPress={() => { startCheck($) }} /> : null}
          <Button key="ones-panel-tests" label="▶ Тесты" onPress={() => { void $.prompt.fill({ text: '/ones-core:tests ' }).catch(() => undefined) }} />
          <Button key="ones-panel-notes" label={v.notes === null ? '★ Что нового' : 'Скрыть'} onPress={() => { void update($, notesShown, s => !s).catch(() => undefined) }} />
        </Box>
        {v.notes === null ? null : <Markdown text={v.notes} />}
      </Box>
    )
  })

  on('turn.start', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId === undefined) {
      await update($, busy, () => true)
      ticker?.cancel()
      ticker = $.clock.every(TICK_MS, () => { void update($, tick, n => n + 1).catch(() => undefined) })
    }
    return r
  })

  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId === undefined) {
      ticker?.cancel()
      ticker = null
      await update($, busy, () => false)
    }
    if (e.agentId === undefined) await refresh($, true)   // ход помощника панель не меняет — файлы зря не читаем
    if (work && e.agentId === undefined) await refreshWorkIfOpen($, e.answer)
    await announceLongTurn($, e)
    return r
  })
}
