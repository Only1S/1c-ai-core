// Мод «правила коммита» (М-3): движок не просит модель добавлять строку Co-Authored-By в сообщение коммита и подпись
// в описание PR — распоряжение владельца, docs/process/work-journals-and-commits.md п.8. Коммит со строкой, если она
// всё же появится, отклоняет git commit-msg (tools/git/hooks/commit-msg, ставит /ones-core:setup).

import type { On } from 'claude-code'

/** Текст атрибуции коммита и PR — пустой; остальные виды (exemption, remedy) движок составляет сам.
 *  Один обработчик на событие: движок берёт один обработчик события на модуль. */
export function serveCommitRules (on: On) {
  on('attribution.text', async ($, e, next) => (e.kind === 'commit' || e.kind === 'pr' ? { text: '' } : next(e)))
}
