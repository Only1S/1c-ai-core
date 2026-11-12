// Контракт состояния модов плагина: панель ядра (status-band.tsx), «шаги задачи» (task-steps.tsx), «Доработка» (work-pane.tsx)

/** Доработка в панели ядра: слаг, стадия словами и её номер в конвейере; -1 — стадия вне словаря. */
export type CardLine = { name: string; stage: string; index: number }
/** Что панель ядра читает из проекта после старта сессии и каждого хода; null — части нет.
 *  cards — идущие доработки, свежие первыми; step — «Следующий шаг» журнала; version — версия ядра из plugin.json. */
export type Facts = { base: string | null; step: string | null; cards: CardLine[]; version: string | null }

/** Шаг задачи мода task-steps.tsx (файл .claude/task-steps.json проекта); card — слаг карточки доработки. */
export type Step = { text: string; done: boolean; card?: string }
/** Прогресс шагов: выполнено из всего. */
export type StepsProgress = { done: number; total: number }

/** Итог проверки проекта в панели (project-check.tsx): running — идёт сейчас; at — время вердикта, мс; text — вердикт; items — строки ошибок и замечаний. */
export type CheckMark = { running: boolean; at: number | null; level: 'ok' | 'warn' | 'fail' | null; text: string; items: string[] }
/** С какого времени идёт текущий шаг (пишет task-steps.tsx). */
export type StepSince = { text: string; at: number }
/** Дело владельца мода owner-tasks.tsx (файл .claude/owner-tasks.json): номер, что сделать, зачем, как понять, что готово, когда поставлено (мс). */
export type OwnerTaskState = { id: number; title: string; why?: string; doneWhen?: string; at: number }

/** Карточка доработки, как её отдаёт gen-portfolio.py --json (панель «Доработка», инструмент work_status):
 *  stage — стадия по-русски (null — ключ вне словаря), missing — чего не хватает выходу стадии, matrix — строки Т-n по статусам. */
export type WorkCard = {
  rel: string; title: string; key: string; raw: string; stage: string | null; next: string | null
  rejected: boolean; missing: string[]; matrix: Record<string, number>; mtime: number
}
/** Портфель: docs — есть ли docs-project/; portfolio — сверка docs-project/pipeline.md с карточками. */
export type WorkPortfolio = { docs: boolean; portfolio: 'absent' | 'in-sync' | 'stale'; cards: WorkCard[] }
/** Проверка хода, уже сделанная (turn-checks.py): что и прошла ли (null — не известно). */
export type WorkCheckRan = { what: string; ok: boolean | null }
/** Ход по журналу (turn-checks.py — код гейта конца хода): правки 1С, чего гейт потребует, строка следа, что уже проверено. */
export type WorkTurn = { found: boolean; calls: number; edits: string | null; missing: string[]; ran: WorkCheckRan[] }
/** Проверки (turn-checks.py): ход, гейт качества по .bsl, последний след прогона, замечания проверок конца хода в сессии;
 *  turn — null, когда хода нет (панель открыли командой до первого законченного хода). */
export type WorkChecks = {
  turn: WorkTurn | null
  gate: { mode: string; armed: string[] }
  evidence: { stamp: string; session: string; own: boolean; checked: string[]; skipped: string[]; notVerified: string[] } | null
  observations: { kind: string; count: number; sample: string }[]
}
/** Что показывает панель «Доработка» (work-pane.tsx): turns — номер хода последнего обновления; null — часть не прочитана, причина — в errors. */
export type WorkView = { portfolio: WorkPortfolio | null; checks: WorkChecks | null; turns: number | null; errors: string[] }

declare module 'claude-code' {
  interface PluginState {
    'ones-core': {
      /** Шаги задачи (пишет task-steps.tsx, показывают панели); null — ещё не прочитаны. */
      'task-steps-list': Step[] | null
      /** «Ждёт вас»: дела, которые может сделать только владелец (пишет owner-tasks.tsx, показывает панель ядра); null — ещё не прочитаны. */
      'owner-tasks-list': OwnerTaskState[] | null
      'status-band-facts': Facts
      /** «Следующий шаг:» карточки, уже показанный подсказкой поля ввода; null — ещё ни одного. */
      'status-band-suggested': string | null
      /** Открыт ли в панели ядра раздел «Что нового». */
      'core-pane-notes': boolean
      /** Идёт ли ход главного агента: у текущего шага крутится значок. */
      'core-pane-busy': boolean
      /** Счётчик таймера хода: запись перерисовывает время шага. */
      'core-pane-tick': number
      /** Более новая версия ядра в канале; null — нет или неизвестно. */
      'core-pane-latest': string | null
      /** С какого времени идёт текущий шаг; null — неизвестно. */
      'task-steps-since': StepSince | null
      /** Почему не работает фильтр входящих (пишет inbound-filter.ts); null — работает. */
      'inbound-filter-fault': string | null
      /** Итог последней проверки проекта (пишет project-check.tsx); null — проверки ещё не было. */
      'project-check-last': CheckMark | null
      /** Панель «Доработка» (work-pane.tsx): портфель и проверки последнего обновления; null — ещё не обновлялась. */
      'work-pane-view': Shaped<WorkView | null>
    }
  }
}
