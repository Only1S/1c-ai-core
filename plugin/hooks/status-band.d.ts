// Контракт состояния модов плагина: чистка входящих (inbound-filter.ts) и команда проверки проекта (project-check.tsx)

/** Итог проверки проекта (project-check.tsx): running — идёт сейчас; at — время вердикта, мс; text — вердикт; items — строки ошибок и замечаний. */
export type CheckMark = { running: boolean; at: number | null; level: 'ok' | 'warn' | 'fail' | null; text: string; items: string[] }

declare module 'claude-code' {
  interface PluginState {
    'ones-core': {
      /** Почему не работает фильтр входящих (пишет inbound-filter.ts); null — работает. */
      'inbound-filter-fault': string | null
      /** Итог последней проверки проекта (пишет project-check.tsx); null — проверки ещё не было. */
      'project-check-last': CheckMark | null
    }
  }
}
