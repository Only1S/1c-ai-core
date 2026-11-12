"""Гейт помощников: правило «только через инструменты» субагенту и барьер согласия на запуск помощников.

Перенос subagent-gate.ps1 на Python (ADR-0002). Событие — из поля hook_event_name:
  - SubagentStart (и пустой вход): текст tools-gate.md субагенту полем hookSpecificOutput.additionalContext
    (обычный вывод на SubagentStart до модели не доходит; лимит 10 000 символов);
  - UserPromptSubmit: запрос владельца с явным согласием на помощников записывается в logs/consent.json проекта,
    запрос без согласия снимает прежнюю запись — согласие действует на конкретный запуск (subagents-on-explicit-consent).
    Вывода нет: на этом событии stdout ушёл бы в контекст модели;
  - PostToolUse AskUserQuestion: выбранный владельцем вариант про помощников без отрицания — тоже согласие (окно мода
    «спросить вместо запрета» — вопрос о команде, а не о помощниках, — не согласие);
  - PreToolUse Agent/Task/Workflow: без согласия — отказ; если владелец назвал число помощников, вызов Agent сверх этого числа —
    отказ. Источник правды этого и двух следующих барьеров — журнал сессии (его пишет Claude Code, а logs/consent.json агент мог
    переписать сам); запись в logs/consent.json — только для события без transcript_path (старый Claude Code, самотест);
  - PreToolUse CronCreate, RemoteTrigger, mcp__scheduled-tasks__* (волна 1): задача по расписанию или фоновый запуск —
    только со своим согласием («да, запускай … по расписанию», cron, routine); согласие на помощников сюда не переносится.
    Слова 1С и GitHub («агент сервера», «агент обмена», «реквизит Агент», «контрагент», ragent, «агентский договор», «помощник
    заполнения», workflow в GitHub) согласием не считаются, вопрос — тоже; помощники — только в форме запуска (глагол запуска
    рядом, число, «веером», «через агентов», одно это слово после «да»; замер 30.10.2026); «можно», «ок», «давай» — только вместе
    с глаголом запуска (замер 29.10.2026);
  - PreToolUse других сессий приложения Claude (с 4.9.1, распоряжение владельца 18.10.2026 «исключить в обязательном
    порядке»): `start_session` по своей инициативе (own_initiative, offer, запуск предложения proposal_id) — отказ всегда;
    `start_session` user_asked и `hand_off_to_session` — отказ, если в ТЕКУЩЕМ запросе владелец сам не попросил отдельную
    сессию (предложение со словом «сессия» и глаголом действия, без отрицания и не вопрос).
Текст правила — tools-gate.md рядом с этим хуком (и в плагине, и в мастере ядра — ADR-0004).
Ошибка на SubagentStart — молча; на барьере — пропуск с пометкой DEGRADED (systemMessage).
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
I = re.IGNORECASE
EVENT = ''   # событие текущего вызова — для обработчика ошибок

# Граница слова спереди: «контрагент» — слово 1С, а не помощник (замер 30.10.2026)
AGENTS = r'\b(помощник|агент|субагент|веер|workflow|воркфлоу|многоагент|fan[- ]?out|agents?\b|subagents?\b)'
# Слова 1С и GitHub, а не помощники Claude, — вырезаются из фразы до поиска помощников.
ONEC_WORDS = (r'(агент\w*\s+(сервер\w*|кластер\w*|обмен\w*|1с|1c)\b|агентск\w*|\bragent\w*|user[- ]?agent|'
              r'помощник\w*\s+(заполнени|ввод|подбор|настройк|обновлени|подключени)\w*|'
              r'(реквизит\w*|справочник\w*|документ\w*|регистр\w*|перечислени\w*|таблиц\w*|отч[её]т\w*|форм\w*|пол[еяю]\b|колонк\w*)\s+[«"\']?агент\w*|'
              r'(workflow\w*|воркфлоу)\s+(в\s+|на\s+|из\s+)?(github|gh\b)|github\s+actions?)')
# Задача по расписанию или фоновый запуск (CronCreate, RemoteTrigger, scheduled-tasks) — своё согласие.
SCHEDULE = r'(расписани\w*|\bcron\w*|\bкрон\w*|schedul\w*|запланируй\w*|\broutines?\b|\bloop\b)'
BG_TOOL = r'^(CronCreate|RemoteTrigger|mcp__.*scheduled-tasks__.*)$'
YES = r'\b(да|запускай|запускайте|запусти|запустить|согласен|согласна|разрешаю|yes|используй|use)\b'
# «можно», «ок», «давай» — согласие только с глаголом запуска: «давай запустим», «можно запускать».
WEAK_YES = r'\b(можно|ок|ok|давай|go)\b'
LAUNCH = r'\b(запуск\w*|запуст\w*|используй\w*|задействуй\w*|run|launch|start|spawn|use)\b'
# Помощники — только в форме запуска: глагол запуска рядом со словом, число, «веером», «через агентов» или одно это слово после
# «да». Иначе «да, поправь агента обмена» — поручение про 1С, а не согласие (замер 30.10.2026).
AGENT_FORM = (LAUNCH + r'[^.!?\n]{0,40}?' + AGENTS + '|' + AGENTS + r'[^.!?\n]{0,40}?' + LAUNCH + r'|\d+\s*' + AGENTS +
              r'|\b(помощниками|агентами|субагентами|веером)\b|\bчерез\s+' + AGENTS +
              r'|^\W*(да|ок|ok|yes|давай)\W+' + AGENTS + r'\w*\W*$')
# Предложение — правило или запрет, а не согласие: «только после явного «да»», «без помощников», «не запускай».
NOT_CONSENT = r'(\bне\s|\bнет\b|\bбез\s|только после|нельзя|запрещ|\bno\b|\bnot\b|\bwithout\b|ultracode)'
NEGATIVE_ANSWER = r'^\s*(нет|no|не\b|без|solo|соло|пауза|отмена|позже|сам|вручную)|без помощник|без агент|не запуск|\bsolo\b|\bсоло\b'
# Окно мода «спросить вместо запрета» (plugin/hooks/ask-guard.tsx, ADR-0010): вопрос о команде, отклонённой барьером, — не о
# помощниках, даже если в команде слово «workflow»; его ответ согласием не считается
GUARD_ASK = 'Барьер guard-destructive отклонил команду'
# Другие сессии приложения Claude: просьба владельца — слово «сессия» и глагол действия в одном предложении, без запрета
# и не вопрос. «Плагин сам предлагает создать новые сессии — это надо исключить» — запрет, а не просьба.
SESSION_TOOL = r'^mcp__.*ccd_session__(start_session|hand_off_to_session)$'
SESSION_WORD = r'(сесси\w*|\bsessions?\b)'
SESSION_VERB = (r'\b(созда\w*|откр\w*|запуст\w*|начн\w*|начин\w*|завед\w*|перенес\w*|вынес\w*|отда\w*|сдела\w*|дела\w*|продолж\w*|'
                r'start|open|create|spawn|move|launch|hand)\b')
NOT_SESSION = NOT_CONSENT + r'|исключ|предлаг|отключ|убер|запрет'


def session_ask_in_prompt(prompt):
    """Владелец в этом запросе сам просит отдельную сессию — предложение с «сессией» и глаголом, без запрета, не вопрос."""
    for sentence in re.split(r'(?<=[.!?;\n])\s*', prompt):
        s = sentence.strip()
        if s and re.search(SESSION_WORD, s, I) and re.search(SESSION_VERB, s, I) and not re.search(NOT_SESSION, s, I) \
                and not s.endswith('?'):
            return s[:200]
    return None


def gate_path():
    return os.path.join(HERE, 'tools-gate.md')


def subagent_start():
    p = gate_path()
    if not os.path.isfile(p):
        return
    with open(p, 'rb') as f:
        text = f.read().decode('utf-8-sig', 'replace')
    if not text.strip():
        return
    plug = os.environ.get('CLAUDE_PLUGIN_ROOT') or ''
    if plug:
        # в проекте нет docs/ и .claude/skills ядра — они в плагине: помощник консилиума искал их в проекте (аудит 30.10.2026)
        text += ('\n\nГДЕ ЯДРО: этот проект подключает плагин ones-core. Правила и справочники ядра — в %s; скиллы ядра — '
                 'ones-core:<имя> (файлы в %s); знания и журналы проекта — docs-project/ проекта.'
                 % (os.path.join(plug, 'docs'), os.path.join(plug, 'skills')))
    payload = {'hookSpecificOutput': {'hookEventName': 'SubagentStart', 'additionalContext': text}}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()


def number_of_agents(text):
    mm = re.search(r'(\d+)\s*(?:помощник|агент|субагент)', text, I)
    return int(mm.group(1)) if mm else None


def consent_kinds(text, form=True):
    """На что фраза: помощники (agents, при form — только в форме запуска) и/или задача по расписанию (schedule); слова 1С
    вырезаются заранее."""
    t = re.sub(ONEC_WORDS, ' ', text, flags=I)
    return [k for k, rx in (('agents', AGENT_FORM if form else AGENTS), ('schedule', SCHEDULE)) if re.search(rx, t, I)]


def window_kinds(q, a):
    """На что ответ окна вариантов: вариант со словом про помощников — сам выбор («Веер из 4 помощников»), слово только в
    вопросе — лишь в форме запуска («Запустить помощников?» = «Да»)."""
    kinds = consent_kinds(q + ' ' + a)
    return ['agents'] + kinds if 'agents' not in kinds and 'agents' in consent_kinds(a, form=False) else kinds


def consent_in_prompt(prompt):
    """Согласие — утверждение (не вопрос) про помощников или расписание с «да/запускай…», без отрицания и условия."""
    for sentence in re.split(r'(?<=[.!?;\n])\s*', prompt):
        s = sentence.strip()
        if s and consent_kinds(s) and (re.search(YES, s, I) or (re.search(WEAK_YES, s, I) and re.search(LAUNCH, s, I))) \
                and not re.search(NOT_CONSENT, s, I) and not s.endswith('?'):
            return s
    return None


def qa_pairs(tool_input, response):
    """(вопрос, выбранный ответ) из окна вариантов; источник — для зонда формата."""
    for via, src in (('tool_input.answers', tool_input), ('tool_response.answers', response)):
        if isinstance(src, dict) and isinstance(src.get('answers'), dict) and src['answers']:
            return [(str(q), str(a)) for q, a in src['answers'].items()], via
    text = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
    pairs = re.findall(r'"([^"]+)"\s*=\s*"([^"]*)"', text)
    return pairs, ('text' if pairs else 'none')


def state_path():
    root = os.environ.get('CLAUDE_PROJECT_DIR') or ''
    return os.path.join(root, 'logs', 'consent.json') if root else ''


def load_state():
    p = state_path()
    if p and os.path.isfile(p):
        with open(p, encoding='utf-8-sig') as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    return {}


def save_state(st):
    p = state_path()
    if not p:
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


class TranscriptUnreadable(Exception):
    pass


def human_prompt(o):
    """Текст реплики владельца из строки журнала или None: уведомления задач, служебные вставки и сводки — не реплики."""
    if not isinstance(o, dict) or o.get('type') != 'user' or o.get('isMeta') or o.get('isCompactSummary') or o.get('isSidechain'):
        return None
    origin = o.get('origin')
    if isinstance(origin, dict) and origin.get('kind') not in (None, 'human'):
        return None
    c = (o.get('message') or {}).get('content')
    if isinstance(c, list):
        if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
            return None
        c = ' '.join(str(b.get('text') or '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
    if not isinstance(c, str) or c.lstrip().startswith('<task-notification>'):
        return None
    return c


def transcript_turn(path):
    """Последняя реплика владельца и что после неё: (текст, ответы окон вариантов, id вызовов Agent/Task).

    Журнал сессии пишет Claude Code, а не модель (аудит 30.10.2026: logs/consent.json агент мог переписать сам). Читается
    хвост до 8 МБ; нет файла или он не разбирается — TranscriptUnreadable, и барьер отвечает отказом, а не пропуском."""
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            f.seek(max(0, size - 8 * 1024 * 1024))
            lines = f.read().decode('utf-8', 'replace').splitlines()
    except OSError as e:
        raise TranscriptUnreadable(str(e))
    prompt, answers, calls, asks = None, [], [], set()
    for line in lines:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        text = human_prompt(o)
        if text is not None:
            prompt, answers, calls, asks = text, [], [], set()
            continue
        c = (o.get('message') or {}).get('content') if isinstance(o, dict) else None
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_use' and b.get('name') in ('Agent', 'Task'):
                calls.append(b.get('id'))
            elif b.get('type') == 'tool_use' and b.get('name') == 'AskUserQuestion':
                asks.add(b.get('id'))
            elif b.get('type') == 'tool_result' and b.get('tool_use_id') in asks:
                r = b.get('content')
                answers.append(r if isinstance(r, str) else ' '.join(str(x.get('text') or '') for x in r or [] if isinstance(x, dict)))
    if prompt is None:
        raise TranscriptUnreadable('в хвосте журнала нет реплики владельца')
    return prompt, answers, calls


def consent_from_transcript(path):
    """Согласие на помощников по журналу: {'text', 'n', 'kind'} или None; плюс число вызовов после реплики."""
    prompt, answers, calls = transcript_turn(path)
    said = consent_in_prompt(prompt)
    if said:
        return {'text': said[:200], 'n': number_of_agents(said), 'kind': consent_kinds(said)}, calls
    for a in answers:
        for q, ans in re.findall(r'"([^"]+)"\s*=\s*"([^"]*)"', a):
            if q.lstrip().startswith(GUARD_ASK):
                continue
            kinds = window_kinds(q, ans)
            if kinds and not re.search(NEGATIVE_ANSWER, ans, I):
                return {'text': ('%s = %s' % (q, ans))[:200], 'n': number_of_agents(ans) or number_of_agents(q), 'kind': kinds}, calls
    return None, calls


def turn_consent(data, sid):
    """Согласие этого хода для расписания: источник правды — журнал сессии, как у помощников (замер 30.10.2026: logs/consent.json
    агент мог переписать сам); без журнала в событии (старый Claude Code, самотест) — прежняя запись, журнал не читается — отказ."""
    tpath = str(data.get('transcript_path') or '')
    if not tpath:
        return (load_state().get(sid) or {}).get('consent') or {}
    try:
        return consent_from_transcript(tpath)[0] or {}
    except TranscriptUnreadable as e:
        deny('subagents-on-explicit-consent: не могу проверить «да» владельца по журналу сессии (%s) — без проверки запуск не '
             'проходит. Спроси владельца окном вариантов и повтори.' % e)


def turn_session_ask(data, sid):
    """Просьба владельца об отдельной сессии в текущем запросе — по журналу сессии, как turn_consent."""
    tpath = str(data.get('transcript_path') or '')
    if not tpath:
        return (load_state().get(sid) or {}).get('session_ask')
    try:
        return session_ask_in_prompt(transcript_turn(tpath)[0])
    except TranscriptUnreadable as e:
        deny('subagents-on-explicit-consent п.8: не могу проверить просьбу владельца по журналу сессии (%s) — другая сессия без '
             'проверки не запускается. Делай работу в этой сессии.' % e)


def deny(reason):
    payload = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                      'permissionDecisionReason': reason}}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()
    sys.exit(0)


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('﻿')
    data = json.loads(raw) if raw.strip() else {}
    data = data if isinstance(data, dict) else {}
    global EVENT
    event = EVENT = str(data.get('hook_event_name') or '')
    tool = str(data.get('tool_name') or '')
    sid = str(data.get('session_id') or '') or 'nosession'

    if event == 'UserPromptSubmit':
        try:
            st = load_state()
            text = str(data.get('prompt') or '')
            said = consent_in_prompt(text)
            rec = st.setdefault(sid, {})
            if said:
                rec['consent'] = {'ts': int(time.time()), 'via': 'prompt', 'text': said[:200], 'n': number_of_agents(said), 'used': 0,
                                  'kind': consent_kinds(said)}
            else:
                rec.pop('consent', None)
            asked = session_ask_in_prompt(text)   # просьба об отдельной сессии действует только на этот запрос
            if asked:
                rec['session_ask'] = {'ts': int(time.time()), 'text': asked}
            else:
                rec.pop('session_ask', None)
            save_state(st)
        except Exception:
            pass   # на UserPromptSubmit любой вывод ушёл бы модели: ошибка — молча
        return

    if event == 'PostToolUse' and tool == 'AskUserQuestion':
        st = load_state()
        pairs, via = qa_pairs(data.get('tool_input') or {}, data.get('tool_response'))
        rec = st.setdefault(sid, {})
        rec['last_ask'] = {'ts': int(time.time()), 'via': via, 'pairs': len(pairs)}
        for q, a in pairs:
            if q.lstrip().startswith(GUARD_ASK):
                continue
            kinds = window_kinds(q, a)
            if kinds and not re.search(NEGATIVE_ANSWER, a, I):
                rec['consent'] = {'ts': int(time.time()), 'via': 'ask', 'text': ('%s = %s' % (q, a))[:200],
                                  'n': number_of_agents(a) or number_of_agents(q), 'used': 0, 'kind': kinds}
        save_state(st)
        return

    if event == 'PreToolUse' and re.match(BG_TOOL, tool):
        if 'schedule' not in (turn_consent(data, sid).get('kind') or []):
            deny('subagents-on-explicit-consent: задача по расписанию или фоновый запуск (%s) — только после явного «да» владельца '
                 'на этот запуск. Спроси окном вариантов: какую задачу ставишь по расписанию (cron, routine), когда и зачем; после '
                 '«да» вызов пройдёт. Согласие на помощников сюда не переносится; ultracode и режим без подтверждений согласием не '
                 'считаются.' % tool)
        return

    if event == 'PreToolUse' and tool in ('Agent', 'Task', 'Workflow'):
        tpath = str(data.get('transcript_path') or '')
        if tpath:
            # источник правды — журнал сессии; число вызовов после реплики считается по нему же, параллельные вызовы
            # одного ответа уже в журнале — сверх названного числа не пройдёт ни один (аудит 30.10.2026)
            try:
                consent, calls = consent_from_transcript(tpath)
            except TranscriptUnreadable as e:
                deny('subagents-on-explicit-consent: не могу проверить «да» владельца по журналу сессии (%s) — без проверки '
                     'помощники не запускаются. Спроси владельца окном вариантов и повтори.' % e)
            # прежние вызовы — без текущего (записан ли он уже в журнал, зависит от версии Claude Code)
            used = len([c for c in calls if c != data.get('tool_use_id')]) if tool in ('Agent', 'Task') else 0
        else:
            st = load_state()   # без журнала (старый Claude Code, самотест) — прежняя запись согласия
            consent = (st.get(sid) or {}).get('consent')
            used = int((consent or {}).get('used') or 0)
        if not consent or 'agents' not in (consent.get('kind') or ['agents']):
            deny('subagents-on-explicit-consent: запуск помощников (%s) без явного «да» владельца на этот запуск. Спроси окном '
                 'вариантов: что запускаешь, сколько помощников и зачем (п.1, ориентир — до ~15); после «да» запуск пройдёт. '
                 'ultracode и режим без подтверждений согласием не считаются.' % tool)
        n = consent.get('n')
        if n and tool in ('Agent', 'Task'):
            if used >= n:
                deny('subagents-on-explicit-consent: владелец согласился на %d помощников («%s»), этот вызов — сверх названного '
                     'числа. Больше — только новым «да» с новым числом.' % (n, consent.get('text') or ''))
            if not tpath:
                consent['used'] = used + 1
                save_state(st)
        return

    if event == 'PreToolUse' and re.match(SESSION_TOOL, tool, I):
        ti = data.get('tool_input') if isinstance(data.get('tool_input'), dict) else {}
        own = tool.lower().endswith('start_session') and (
            str(ti.get('initiation') or '') in ('own_initiative', 'offer') or bool(ti.get('proposal_id')))
        if own or not turn_session_ask(data, sid):
            deny('subagents-on-explicit-consent п.8: владелец запретил предлагать и создавать другие сессии по своей инициативе '
                 '(распоряжение 18.10.2026 «исключить в обязательном порядке») — ни карточек-предложений, ни «New session / Do it '
                 'here», ни переноса задачи в новую сессию. Делай работу в этой сессии; отдельная сессия — только когда владелец сам '
                 'попросил её в текущем запросе (%s).' % ('это предложение по своей инициативе' if own else 'в запросе такой просьбы нет'))
        return

    if event in ('', 'SubagentStart'):
        subagent_start()


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # на SubagentStart — молча, как прежде; на барьере — отказ; на записи согласия — видимая пометка
        if EVENT == 'PreToolUse':
            sys.stdout.buffer.write(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                'permissionDecisionReason': 'subagent-gate: внутренняя ошибка проверки согласия (%s) — без проверки запуск не '
                                            'проходит (аудит 30.10.2026: раньше сбой пропускал вызов).' % e}}, ensure_ascii=False).encode('utf-8'))
            sys.stdout.flush()
        elif EVENT == 'PostToolUse':
            sys.stdout.buffer.write(json.dumps({'systemMessage': 'subagent-gate: DEGRADED — внутренняя ошибка, проверка '
                                                'согласия пропущена: %s' % e}, ensure_ascii=False).encode('utf-8'))
            sys.stdout.flush()
    sys.exit(0)
