// web-test cli/session v1.0 — session-file helpers for HTTP-server mode
// Source: https://github.com/Nikolay-Shirokov/cc-1c-skills
import { existsSync, readFileSync, unlinkSync, mkdirSync } from 'fs';
import { resolve, dirname, basename } from 'path';
import { tmpdir } from 'os';
import { createHash } from 'crypto';
import { die } from './util.mjs';

// dev_core: файл сеанса и скриншот ошибки — во временной папке своего проекта, а не в папке скилла
// (в плагине она одна на все проекты). Проект — вверх от текущей папки до .v8-project.json.
function projectRoot() {
  const cwd = resolve(process.cwd());
  for (let d = cwd; ; d = dirname(d)) {
    if (existsSync(resolve(d, '.v8-project.json'))) return d;
    if (dirname(d) === d) return cwd;
  }
}
const ROOT = projectRoot();
const KEY = process.platform === 'win32' ? ROOT.toLowerCase() : ROOT;
export const STATE_DIR = resolve(tmpdir(), 'ones-core-web-test',
  basename(ROOT) + '-' + createHash('sha1').update(KEY).digest('hex').slice(0, 8));
mkdirSync(STATE_DIR, { recursive: true });
export const SESSION_FILE = resolve(STATE_DIR, '.browser-session.json');

export function loadSession() {
  if (!existsSync(SESSION_FILE)) {
    die('No active session. Run: node src/run.mjs start <url>');
  }
  return JSON.parse(readFileSync(SESSION_FILE, 'utf-8'));
}

export function cleanup() {
  try { unlinkSync(SESSION_FILE); } catch {}
}
