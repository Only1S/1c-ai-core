// dev_core: web-test cli/pd-gate — строки списков и формы веб-клиента идут к модели, поэтому база должна быть без настоящих ПДн
// (personal-data-masked-from-1c): то же решение, что у guard-personal-data — pd: none или masked, нет отметки = raw, отказ.
import { existsSync, readFileSync } from 'fs';
import { dirname, join } from 'path';

const CLEAN = new Set(['none', 'masked']);
const HOW = 'Отметку ставит только владелец — это его решение о данных, сам её не ставь: в .v8-project.json у базы "pd": "none", '
  + 'если данных о людях в базе нет, или "pd": "masked", если копия обезличена.';

function registryFrom(dir) {
  for (let d = dir; ; d = dirname(d)) {
    if (existsSync(join(d, '.v8-project.json'))) return join(d, '.v8-project.json');
    if (dirname(d) === d) return null;
  }
}

// Имя публикации по умолчанию — как у web-publish: папка базы или база на сервере, без знаков, в нижнем регистре
function publication(db) {
  const name = db.type === 'server' ? String(db.ref ?? '') : String(db.path ?? '').split(/[\\/]/).filter(Boolean).pop() ?? '';
  return name.replace(/[^\p{L}\p{N}_]/gu, '').toLowerCase();
}

/** Причина не открывать адрес или null. Адрес не сопоставлен с базой реестра — чистыми должны быть все его базы. */
export function pdRefusal(url, cwd = process.cwd()) {
  const reg = registryFrom(cwd);
  if (!reg) return `personal-data-masked-from-1c: web-test не запущен — выше ${cwd} нет .v8-project.json, а неизвестная база считается базой с настоящими ПДн. Запускай из папки проекта.`;
  let dbs;
  try {
    const parsed = JSON.parse(readFileSync(reg, 'utf-8').replace(/^\uFEFF/, '')).databases ?? [];
    dbs = (Array.isArray(parsed) ? parsed : [parsed]).filter(d => d && typeof d === 'object');
  } catch (e) {
    return `personal-data-masked-from-1c: web-test не запущен — реестр ${reg} не читается (${e.message}): сбой проверки = отказ.`;
  }
  const low = String(url ?? '').toLowerCase().replace(/\/+$/, '');
  let pub = '';
  try { pub = new URL(low).pathname.split('/')[1] ?? ''; } catch { /* адрес не разобран — сверяем все базы */ }
  const byUrl = dbs.filter(d => d.webUrl && low.startsWith(String(d.webUrl).toLowerCase().replace(/\/+$/, '')));
  const byName = dbs.filter(d => pub && publication(d) === pub);
  const scope = byUrl.length ? byUrl : byName.length ? byName : dbs;
  const dirty = scope.filter(d => !CLEAN.has(String(d.pd ?? '').trim().toLowerCase())).map(d => d.id);
  if (scope.length && !dirty.length) return null;
  return `personal-data-masked-from-1c: web-test не запущен — у базы (${dirty.join(', ') || 'нет записей в реестре'}) нет отметки pd: none или masked: `
    + `значит, в ней настоящие ПДн, а строки списков и формы веб-клиента идут к модели (п.3, п.6). ${HOW}`;
}
