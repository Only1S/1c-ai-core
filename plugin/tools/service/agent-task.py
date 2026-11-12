r"""agent-task.py — первый срез сервиса «инженер 1С» (#1 волны 3) на GitHub Actions: задача → агент с плагином → PR.

Задача (из issue с меткой или ручного запуска) приходит текстом; драйвер собирает промпт по правилам ядра и зовёт
агента (`claude -p` с плагином ones-core), который вносит правки в рабочую копию. Коммит и PR собирает workflow —
правки проходят ревью человеком в PR до слияния (сервис не льёт в main сам). Это GitHub-центричный срез: без своего
сервера; постоянная очередь/изоляция арендатора на `vmrus` — отдельный срез позже (wave3-growth-plan Т-7).

Запуск (через workflow agent-task.yml: в мастере — .github/workflows, в проекте — шаблон рядом с этим файлом):
    python plugin/tools/service/agent-task.py --task "<текст задачи>" [--task-file <файл>] [--run] [--out <итог.md>] [--plugin-dir <папка>]
        --task / --task-file   текст задачи (или файл с ним); без текста — код 2
        --run                  позвать агента (нужен claude CLI и ключ в окружении); без него — только промпт
        --out                  куда записать итог (без него — stdout)
        --plugin-dir           папка плагина ones-core: нужна в репозитории конфигурации, где ядра нет

Код выхода: 0 — промпт собран (и агент отработал при --run); 2 — нет текста задачи. Правки агент вносит в рабочую
копию; коммит/ветку/PR делает workflow. Агент работает с разрешением на правки (`--permission-mode acceptEdits`),
но результат попадает в main только через PR с ревью.
"""
import argparse
import os
import shutil
import subprocess
import sys


def build_prompt(task):
    """Промпт агенту: выполнить задачу в этом репозитории по правилам ядра, не коммитить (PR соберёт workflow)."""
    return ('Ты — инженер 1С на ядре ones-core в CI. Выполни задачу в ЭТОМ репозитории строго по правилам ядра '
            '(`CLAUDE.md` и доки `docs/`): сперва проработка и согласование решений инструментами стека, затем правки '
            'штатными скиллами, затем проверка всем набором чекеров. Вноси изменения в рабочую копию, НО НЕ делай '
            'коммит и не трогай ветки — коммит и pull request соберёт сам workflow, правки пройдут ревью человеком '
            'до слияния. В конце кратко перечисли, что сделано и что проверено.\n\nЗАДАЧА:\n' + task.strip())


def main():
    ap = argparse.ArgumentParser(description='Сервис-агент на GitHub Actions: задача → агент → PR (#1 волны 3, первый срез).')
    ap.add_argument('--task', help='текст задачи')
    ap.add_argument('--task-file', help='файл с текстом задачи')
    ap.add_argument('--run', action='store_true', help='позвать агента (нужен claude CLI)')
    ap.add_argument('--out', help='файл итога (без него — stdout)')
    ap.add_argument('--plugin-dir', help='папка плагина ones-core')
    for s in (sys.stdout, sys.stderr):   # до разбора ключей: в справке есть символы вне кодировки консоли
        try:
            s.reconfigure(encoding='utf-8')
        except Exception:
            pass
    args = ap.parse_args()
    task = args.task or (open(args.task_file, encoding='utf-8').read() if args.task_file and os.path.isfile(args.task_file) else '') \
        or os.environ.get('TASK_TEXT', '')
    if not task.strip():
        print('нет текста задачи: задайте --task, --task-file или переменную TASK_TEXT', file=sys.stderr)
        return 2
    prompt = build_prompt(task)

    sb = ['# Сервис-агент: итог задачи', '', '## Задача', '', task.strip(), '']
    if args.run:
        claude = shutil.which('claude') or os.environ.get('CLAUDE_CLI')
        if not claude:
            sb += ['## Агент', '', '_не запущен: нет claude CLI (задайте CLAUDE_CLI или поставьте Claude Code)_', '']
        else:
            cmd = [claude, '-p', prompt, '--permission-mode', 'acceptEdits', '--output-format', 'text', '--add-dir', os.getcwd()]
            if args.plugin_dir:
                cmd += ['--plugin-dir', args.plugin_dir]
            r = subprocess.run(cmd, capture_output=True, timeout=3600)
            out = r.stdout.decode('utf-8', 'replace').strip()
            sb += ['## Агент (итог)', '', out or ('_агент не дал текста (код %s): %s_' % (r.returncode, r.stderr.decode('utf-8', 'replace')[:200])), '']
    else:
        sb += ['## Промпт агенту (черновик, без запуска)', '', '```', prompt, '```', '']

    report = '\n'.join(sb) + '\n'
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(report)
        print('итог: ' + args.out)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
