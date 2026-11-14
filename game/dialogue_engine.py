"""
Діалоговий рушій: усі взаємодії з NPC відбуваються лише в діалозі.
Дерево діалогу генерується процедурно під світ, темперамент та стан стосунків.
"""
import random
from typing import Any, Dict, List, Optional


DIALOGUE_NODES: Dict[str, Dict[str, Any]] = {
    # --- Жести / соціальні сигнали ---
    'gesture_bow': {
        'speaker': 'npc',
        'text': '{npc} дивиться на ваш уклін, оцінюючи його щирість.',
        'options': [
            {'text': 'Сказати, що прийшли з миром.', 'effects': '+Повага', 'tone': 'light',
             'delta': {'respect': 4}, 'vector': {'aggression_diplomacy': -0.05}},
            {'text': 'Тримати погляд і мовчати.', 'effects': '+Страх', 'tone': 'shadow',
             'delta': {'fear': 4}, 'vector': {'chaos_order': 0.05}},
            {'text': 'Додати сарказм до уклону.', 'effects': '−Повага', 'tone': 'chaos',
             'delta': {'respect': -6}, 'vector': {'chaos_order': 0.1}},
        ],
    },
    'gesture_handshake': {
        'speaker': 'npc',
        'text': '{npc} протягає руку, чекаючи вашої відповіді.',
        'options': [
            {'text': 'Міцно потиснути руку.', 'effects': '+Повага, +Довіра', 'tone': 'light',
             'delta': {'respect': 3, 'trust': 5}, 'vector': {'aggression_diplomacy': -0.05}},
            {'text': 'Тиснути так, що кістки хрустять.', 'effects': '+Страх', 'tone': 'shadow',
             'delta': {'fear': 8}, 'vector': {'aggression_diplomacy': 0.1}},
            {'text': 'Відвернутися від руки.', 'effects': '−Повага', 'tone': 'chaos',
             'delta': {'respect': -4}, 'vector': {'chaos_order': 0.05}},
        ],
    },
    'gesture_threaten': {
        'speaker': 'npc',
        'text': 'Ваша рука лягає на ефес. {npc} блідіє, але не відвертається.',
        'options': [
            {'text': 'Попустити зброю й посміхнутися.', 'effects': '+Довіра', 'tone': 'light',
             'delta': {'trust': 6, 'fear': -5}, 'vector': {'light_shadow': 0.05}},
            {'text': 'Шепотом назвати ціну непокору.', 'effects': '++Страх', 'tone': 'shadow',
             'delta': {'fear': 15}, 'vector': {'light_shadow': -0.15, 'aggression_diplomacy': 0.1}},
            {'text': 'Намагалися налякати, але він/вона не зламалась.', 'effects': '+Повага', 'tone': 'neutral',
             'delta': {'respect': 8}, 'vector': {'chaos_order': -0.05}},
        ],
    },
    'gesture_insult': {
        'speaker': 'npc',
        'text': 'Ваш зневажливий жест висить у повітрі. {npc} стискає кулаки.',
        'options': [
            {'text': 'Продовжити знущатися.', 'effects': '−−Повага, +Страх', 'tone': 'chaos',
             'delta': {'respect': -12, 'fear': 6}, 'vector': {'chaos_order': 0.2, 'light_shadow': -0.1}},
            {'text': 'Зупинитися й перепросити.', 'effects': '+Довіра', 'tone': 'light',
             'delta': {'trust': 4, 'respect': 2}, 'vector': {'light_shadow': 0.1}},
            {'text': 'Замовкнути й чекати реакції.', 'effects': 'Нейтрально', 'tone': 'neutral',
             'delta': {}, 'vector': {}},
        ],
    },
    # --- Романтика ---
    'romance_compliment': {
        'speaker': 'npc',
        'text': 'Ви говорите щось приємне. {npc} прислухається до вашого голосу.',
        'options': [
            {'text': 'Сказати, що його/її очі яскравіші за зорі.', 'effects': '+Симпатія', 'tone': 'light',
             'delta': {'affection': 8}, 'requires': {'min_affection': -20}},
            {'text': 'Зробити комплімент про силу, а не про зовнішність.', 'effects': '+Повага, +Симпатія', 'tone': 'light',
             'delta': {'affection': 4, 'respect': 4}},
            {'text': 'Сказати, що він/вона нікчемний/нікчемна.', 'effects': '−−Симпатія', 'tone': 'shadow',
             'delta': {'affection': -10}, 'vector': {'light_shadow': -0.1}},
        ],
    },
    'romance_dine': {
        'speaker': 'npc',
        'text': 'Ви ділите вечерю біля вогнища. {npc} розслаблюється.',
        'options': [
            {'text': 'Розпитати про його/її мрії.', 'effects': '++Симпатія, +Довіра', 'tone': 'light',
             'delta': {'affection': 10, 'trust': 6}, 'vector': {'light_shadow': 0.1}},
            {'text': 'Розповісти про минулі битви.', 'effects': '+Повага', 'tone': 'neutral',
             'delta': {'respect': 5}, 'vector': {'aggression_diplomacy': 0.05}},
            {'text': 'Налити більше вина й мовчати.', 'effects': '+Симпатія', 'tone': 'shadow',
             'delta': {'affection': 5}},
        ],
    },
    'romance_confess': {
        'speaker': 'npc',
        'text': '{npc} замирає, чекаючи ваших слів.',
        'options': [
            {'text': 'Зізнатися в коханні відкрито.', 'effects': 'Стосунки: Кохання', 'tone': 'light',
             'delta': {'affection': 20}, 'set_relationship': 'lover',
             'requires': {'min_affection': 20}},
            {'text': 'Назвати його/її лише другом.', 'effects': '−Симпатія', 'tone': 'neutral',
             'delta': {'affection': -6}},
            {'text': 'Відкинути почуття як слабкість.', 'effects': '−−Симпатія, +Страх', 'tone': 'shadow',
             'delta': {'affection': -12, 'fear': 5}, 'vector': {'light_shadow': -0.15}},
        ],
    },
    'romance_marry': {
        'speaker': 'npc',
        'text': '{npc} з упокоєм дивиться вам в очі.',
        'options': [
            {'text': 'Запропонувати шлюб перед світами цього краю.', 'effects': 'Стосунки: Дружина/Чоловік', 'tone': 'light',
             'delta': {'affection': 25}, 'set_relationship': 'spouse',
             'requires': {'relationship': 'lover', 'min_affection': 60}},
            {'text': 'Сказати, що шлюб — це лише папір.', 'effects': '−Симпатія', 'tone': 'chaos',
             'delta': {'affection': -15}, 'vector': {'chaos_order': 0.15}},
        ],
    },
    # --- Вбивство ---
    'kill_attack': {
        'speaker': 'npc',
        'text': '{npc} ще не встигає зрозуміти, що ви робите. У повітрі зависає лезо.',
        'options': [
            {'text': 'Завдати удару.', 'effects': 'Вбивство', 'tone': 'shadow', 'lethal': True,
             'delta': {}, 'vector': {'light_shadow': -0.35, 'chaos_order': 0.25, 'aggression_diplomacy': 0.2}},
            {'text': 'Зупинитися в останній момент.', 'effects': '+Довіра, +Симпатія', 'tone': 'light',
             'delta': {'trust': 8, 'affection': 6, 'fear': -10}, 'vector': {'light_shadow': 0.2}},
        ],
    },
}

ROOT_KEYS = {
    'greet': 'greet',
    'gesture_bow': 'gesture_bow',
    'gesture_handshake': 'gesture_handshake',
    'gesture_threaten': 'gesture_threaten',
    'gesture_insult': 'gesture_insult',
    'romance_compliment': 'romance_compliment',
    'romance_dine': 'romance_dine',
    'romance_confess': 'romance_confess',
    'romance_marry': 'romance_marry',
    'kill_attack': 'kill_attack',
}


def _fmt(text: str, npc) -> str:
    return text.replace('{npc}', getattr(npc, 'name', 'Незнайомець'))


def _check_requirements(npc, opt: Dict[str, Any]) -> (bool, str):
    req = opt.get('requires') or {}
    if not req:
        return True, ''
    if 'min_affection' in req and npc.affection < req['min_affection']:
        return False, f"Потрібна симпатія {req['min_affection']}+"
    if 'relationship' in req and npc.relationship != req['relationship']:
        return False, f"Потрібні стосунки: {req['relationship']}"
    if 'min_respect' in req and npc.respect < req['min_respect']:
        return False, f"Потрібна повага {req['min_respect']}+"
    return True, ''


def open_dialogue(character, npc) -> Dict[str, Any]:
    """Відкриває діалог: привітання залежно від стосунків + доступні теми."""
    from .npc_sandbox import npc_speak
    greeting = npc_speak(npc, 'greet', character.name)

    options = [
        {'topic': 'gesture_bow', 'text': 'Шанобливо вклонятися', 'effects': 'Жест', 'tone': 'light'},
        {'topic': 'gesture_handshake', 'text': 'Потиснути руку', 'effects': 'Жест', 'tone': 'light'},
        {'topic': 'gesture_threaten', 'text': 'Покласти руку на зброю', 'effects': 'Жест', 'tone': 'shadow'},
        {'topic': 'gesture_insult', 'text': 'Зневажливо плюнути', 'effects': 'Жест', 'tone': 'chaos'},
        {'topic': 'romance_compliment', 'text': 'Зробити комплімент', 'effects': 'Романтика', 'tone': 'light'},
        {'topic': 'romance_dine', 'text': 'Запросити на вечерю', 'effects': 'Романтика', 'tone': 'light'},
        {'topic': 'romance_confess', 'text': 'Зізнатися в коханні', 'effects': 'Романтика', 'tone': 'light'},
        {'topic': 'romance_marry', 'text': 'Запропонувати шлюб', 'effects': 'Романтика', 'tone': 'light'},
        {'topic': 'kill_attack', 'text': 'Атакувати цю душу', 'effects': 'Життя під загрозою', 'tone': 'shadow'},
    ]

    transcript = [{'who': 'npc', 'speaker': npc.name, 'text': greeting}]
    return {
        'npc_id': npc.id,
        'npc_name': npc.name,
        'npc_role': npc.role_title,
        'npc_rel': npc.relationship,
        'npc_gender': npc.gender,
        'node_key': 'greet',
        'transcript': transcript,
        'options': options,
    }


def get_dialogue_node(character, npc, node_key: str) -> Dict[str, Any]:
    """Повертає вузол діалогу з варіантами, позначеними доступністю."""
    node = DIALOGUE_NODES.get(node_key)
    if not node:
        return open_dialogue(character, npc)

    options = []
    for opt in node.get('options', []):
        allowed, reason = _check_requirements(npc, opt)
        item = {
            'text': _fmt(opt['text'], npc),
            'effects': opt.get('effects', ''),
            'tone': opt.get('tone', 'neutral'),
            'locked': not allowed,
            'lock_reason': reason if not allowed else '',
        }
        options.append(item)

    transcript = [{'who': 'npc', 'speaker': npc.name, 'text': _fmt(node['text'], npc)}]
    return {
        'npc_id': npc.id,
        'npc_name': npc.name,
        'npc_role': npc.role_title,
        'npc_rel': npc.relationship,
        'npc_gender': npc.gender,
        'node_key': node_key,
        'transcript': transcript,
        'options': options,
    }


def resolve_dialogue_option(character, npc, node_key: str, option_index: int) -> Dict[str, Any]:
    """Застосовує вибір у діалозі: метрики, вектор, стосунки, смерть."""
    node = DIALOGUE_NODES.get(node_key)
    if not node or option_index < 0 or option_index >= len(node.get('options', [])):
        return open_dialogue(character, npc)

    opt = node['options'][option_index]
    allowed, reason = _check_requirements(npc, opt)
    if not allowed:
        result = get_dialogue_node(character, npc, node_key)
        result['notice'] = reason
        return result

    # Смерть
    if opt.get('lethal'):
        from .npc_sandbox import process_npc_kill
        kill_res = process_npc_kill(character, npc)
        npc.refresh_from_db()
        transcript = [
            {'who': 'npc', 'speaker': npc.name, 'text': _fmt(node['text'], npc)},
            {'who': 'hero', 'speaker': character.name, 'text': _fmt(opt['text'], npc)},
            {'who': 'system', 'speaker': 'Літопис', 'text': kill_res.get('message', '')},
        ]
        return {
            'npc_id': npc.id, 'npc_name': npc.name, 'npc_role': npc.role_title,
            'npc_rel': npc.relationship, 'npc_gender': npc.gender,
            'node_key': 'greet', 'transcript': transcript, 'options': [],
            'finished': True, 'kill_message': kill_res.get('message', ''),
        }

    # Метрики
    delta = opt.get('delta') or {}
    npc.affection = max(-100, min(100, npc.affection + delta.get('affection', 0)))
    npc.respect = max(0, min(100, npc.respect + delta.get('respect', 0)))
    npc.fear = max(0, min(100, npc.fear + delta.get('fear', 0)))
    npc.trust = max(0, min(100, npc.trust + delta.get('trust', 0)))

    new_rel = opt.get('set_relationship')
    if new_rel:
        npc.relationship = new_rel
    elif npc.fear > 55 and npc.relationship not in ('nemesis', 'deceased'):
        npc.relationship = 'nemesis'
    elif npc.respect >= 55 and npc.affection >= 25 and npc.relationship == 'stranger':
        npc.relationship = 'acquaintance'
    elif npc.affection >= 45 and npc.relationship in ('stranger', 'acquaintance'):
        npc.relationship = 'confidant'

    npc.memory_log.append({
        'turn': character.turns,
        'action': f"Діалог: {node_key} / {option_index}",
        'delta': delta,
        'relationship': npc.relationship,
    })
    npc.save()

    # Вектор сюжету
    vec = opt.get('vector') or {}
    if vec:
        story_state = character.get_story_state()
        cur_vector = story_state.setdefault('plot_vector', {
            'chaos_order': 0.0, 'light_shadow': 0.0,
            'aggression_diplomacy': 0.0, 'mystery_reason': 0.0,
        })
        for axis, d_val in vec.items():
            cur_vector[axis] = round(cur_vector.get(axis, 0.0) + float(d_val), 3)
        character.story_flags['plot_vector'] = cur_vector
        character.save()

    character.logs.create(
        age=character.age,
        turn=character.turns,
        title=f"Діалог з {npc.name}",
        text=_fmt(opt['text'], npc),
        log_type='event',
    )

    transcript = [
        {'who': 'npc', 'speaker': npc.name, 'text': _fmt(node['text'], npc)},
        {'who': 'hero', 'speaker': character.name, 'text': _fmt(opt['text'], npc)},
    ]
    result = open_dialogue(character, npc)
    result['transcript'] = transcript + result['transcript']
    result['notice'] = 'Ваш вчинок залишив слід у цій душі.'
    return result
