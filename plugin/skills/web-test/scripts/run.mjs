#!/usr/bin/env node
// web-test run v1.22 — CLI entry-point
// Source: https://github.com/Nikolay-Shirokov/cc-1c-skills
/**
 * CLI runner for 1C web client automation.
 *
 * Architecture: `start` launches browser + HTTP server in one process.
 * `exec`, `shot`, `stop` send requests to the running server.
 *
 * Usage:
 *   node src/run.mjs start <url>            — launch browser, connect to 1C, serve requests
 *   node src/run.mjs run <url> <file|->     — autonomous: connect, execute script, disconnect
 *     start/run: --user=<name> [--password=<pwd>] — log in as that infobase user
 *   node src/run.mjs exec <file|->          — run script against existing session
 *   node src/run.mjs shot [file]            — take screenshot
 *   node src/run.mjs stop                   — logout + close browser
 *   node src/run.mjs status                 — check session
 *   node src/run.mjs test <dir|file>... [--url]  — run regression tests
 *
 * Внутренности живут в cli/: util, session, exec-context, server,
 * commands/{start,run,exec,shot,stop,status,test}, test-runner/*.
 */
import { createRequire } from 'module';
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import { usage, die } from './cli/util.mjs';

const [,, cmd, ...rawArgs] = process.argv;

// dev_core: без пакета playwright любая команда падала трассировкой Node (ERR_MODULE_NOT_FOUND) — теперь
// справка без команды и подсказка установки; модули с playwright грузятся только после проверки
if (!['start', 'run', 'exec', 'shot', 'stop', 'status', 'test'].includes(cmd)) usage();
try {
  createRequire(import.meta.url).resolve('playwright');
} catch {
  die(`Не установлен пакет playwright (Node). Установите: cd "${dirname(fileURLToPath(import.meta.url))}" `
    + '&& npm install && npx playwright install chromium');
}
const browser = await import('./browser.mjs');
const { cmdStart } = await import('./cli/commands/start.mjs');
const { cmdRun } = await import('./cli/commands/run.mjs');
const { cmdExec } = await import('./cli/commands/exec.mjs');
const { cmdShot } = await import('./cli/commands/shot.mjs');
const { cmdStop } = await import('./cli/commands/stop.mjs');
const { cmdStatus } = await import('./cli/commands/status.mjs');
const { cmdTest } = await import('./cli/commands/test.mjs');
// dev_core: строки списков и формы — данные базы: только база pd: none/masked (personal-data-masked-from-1c)
if (['start', 'run', 'test'].includes(cmd)) {
  const { pdRefusal } = await import('./cli/pd-gate.mjs');
  const why = pdRefusal(cmd === 'test' ? rawArgs.find(a => a.startsWith('--url='))?.slice(6) : rawArgs.find(a => !a.startsWith('--')));
  if (why) die(why);
}
const flags = {
  noRecord: rawArgs.includes('--no-record'),
  // `test` has its own per-test --timeout=ms — parse the exec bound only where it applies.
  execTimeoutMs: (cmd === 'run' || cmd === 'exec') ? parseExecTimeoutMs(rawArgs) : undefined,
};
const args = rawArgs.filter(a => !a.startsWith('--'));

// Value of a --name=value flag (first occurrence), undefined when absent. Bare words are
// positional arguments, so every valued flag uses this form.
function flagValue(name, argv = rawArgs) {
  const a = argv.find(x => x.startsWith(`--${name}=`));
  return a === undefined ? undefined : a.slice(name.length + 3);
}

// Login for start/run. An empty --user= usually means an unset shell variable — refuse rather
// than fall back to the publication's user unnoticed.
let login = {};
try {
  // dev_core: в реестре пароль лежит ссылкой ${ИМЯ} — иначе в 1С уходил её текст и вход отклонялся без объяснения
  const { expandSecretRef } = await import('./cli/secret-ref.mjs');
  login = { user: expandSecretRef(flagValue('user')), password: expandSecretRef(flagValue('password')) };
} catch (e) {
  die(e.message);
}
if (cmd === 'start' || cmd === 'run') {
  if (login.user === '') die('--user= is empty');
  if (login.password !== undefined && login.user === undefined) die('--password= requires --user=');
}

// Clipboard preservation: default ON. Disabled by --no-preserve-clipboard CLI flag
// or WEB_TEST_PRESERVE_CLIPBOARD=0 env. cmdTest may further disable via config.
const preserveClipboard = !rawArgs.includes('--no-preserve-clipboard')
  && process.env.WEB_TEST_PRESERVE_CLIPBOARD !== '0';
browser.setPreserveClipboard(preserveClipboard);

function parseExecTimeoutMs(argv) {
  const DEFAULT_MS = 30 * 60 * 1000;
  // setTimeout turns anything above 2^31-1 (Infinity included) into 1 ms — a bound that large
  // would kill the script at once instead of never.
  const MAX_MS = 2147483647;
  const check = (ms, source) => {
    if (!Number.isFinite(ms) || ms <= 0 || ms > MAX_MS) {
      die(`Invalid ${source}: expected a positive number of ms up to ${MAX_MS} `
        + `(--timeout=<ms>, --timeout-min=<min>, WEB_TEST_EXEC_TIMEOUT_MS=<ms>)`);
    }
    return Math.round(ms);
  };
  const ms = flagValue('timeout', argv);
  if (ms !== undefined) return check(Number(ms), `--timeout=${ms}`);
  const min = flagValue('timeout-min', argv);
  if (min !== undefined) return check(Number(min) * 60 * 1000, `--timeout-min=${min}`);
  const env = process.env.WEB_TEST_EXEC_TIMEOUT_MS;
  if (env) return check(Number(env), `WEB_TEST_EXEC_TIMEOUT_MS=${env}`);
  return DEFAULT_MS;
}

switch (cmd) {
  case 'start':  await cmdStart(args[0], login); break;
  case 'run':    await cmdRun(args[0], args[1], flags.execTimeoutMs, login); break;
  case 'exec':   await cmdExec(args[0], flags); break;
  case 'shot':   await cmdShot(args[0]); break;
  case 'stop':   await cmdStop(); break;
  case 'status': await cmdStatus(); break;
  case 'test':   await cmdTest(rawArgs); break;
  default:       usage();
}
