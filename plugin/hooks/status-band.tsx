// Единственный модуль плагина (hooks.json берёт один): подключает моды-защиты и команду /check, у каждого — свои обработчики.
// Решения владельца 20–21.11.2026 (docs/sources/claude-code-mods-review.md п.5–7): панели /core и /work, моды «шаги задачи»
// и «Ждёт вас», уведомления панели и инструменты на чтение убраны — шаги работы и дела владельца ведёт встроенный список
// задач Claude Code (CLAUDE_CODE_ENABLE_TODO_TOOLS=1 пишут старт сессии и setup).
import type { PluginOptions, Register } from 'claude-code'

import { serveAskGuard } from './ask-guard'
import { serveCommitRules } from './commit-rules'
import { serveInboundFilter } from './inbound-filter'
import { serveCheck } from './project-check'

/** Правила коммита и чистка входящих — всегда; выжимка вывода, «спросить вместо запрета» и /check — каждый своей настройкой. */
export const register: Register = (on, options: PluginOptions) => {
  serveCommitRules(on)
  serveInboundFilter(on, { outputDigest: options.outputDigest !== false })
  if (options.askInsteadOfDeny !== false) serveAskGuard(on)
  if (options.projectCheck !== false) serveCheck(on)
}
