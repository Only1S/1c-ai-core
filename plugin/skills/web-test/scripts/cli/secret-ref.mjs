// dev_core: ссылка ${ИМЯ} или %ИМЯ% на значение из окружения: пароль в .v8-project.json хранится только так (db-list).
// Отдельным модулем — без зависимости от playwright, чтобы правило проверялось без браузера.
export function expandSecretRef(value) {
  const m = /^\s*(?:\$\{(\w+)\}|%(\w+)%)\s*$/.exec(value ?? '');
  if (!m) return value;
  const name = m[1] || m[2];
  const got = process.env[name];
  if (got === undefined) {
    throw new Error(`environment variable ${name} is not set: the value comes from the environment `
      + '(.env of the project or the env block of .claude/settings.local.json)');
  }
  return got;
}
