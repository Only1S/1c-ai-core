"""Проверка синтаксиса Python-файлов без запуска: python tools/lib/pycheck.py <файл>...

Печатает «имя: ошибка» для каждого файла, который не разбирается, и завершается с кодом 1, если такие есть.
Нужна проверкам ядра: хук с синтаксической ошибкой падает при запуске и молча пропускает всё (fail-open).
"""
import ast
import os
import sys


def main(paths):
    bad = []
    for p in paths:
        try:
            with open(p, encoding='utf-8-sig') as f:
                ast.parse(f.read(), filename=p)
        except (SyntaxError, ValueError, OSError) as e:
            bad.append('%s: %s' % (os.path.basename(p), e))
    for line in bad:
        print(line)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))
