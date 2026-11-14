import random
import hashlib
from typing import Dict, Any, List, Optional

WORLD_PRESETS: Dict[str, Dict[str, Any]] = {
    'fantasy': {
        'id': 'fantasy',
        'name': 'Етерія: Прадавня Магія',
        'desc': 'Класичний високий дарк-фентезі: магічні розлами, дракони, стародавні ордени та битва за престол світла.',
        'threat': 'Владика Тіньопаду Малзаріон',
        'races': ['Людина', 'Вищий Ельф', 'Гірський Дворф', 'Дикий Звіролюд', 'Тіньовий Тіфлінг', 'Дракононароджений'],
        'pieces': [
            'campfire-under-stars', 'autumn-forest', 'castle-bridge-dawn',
            'lightning-storm', 'imperial-palace-snow', 'bat-cave-dusk',
            'volcano-eruption', 'starry-ridge'
        ]
    },
    'dark_gothic': {
        'id': 'dark_gothic',
        'name': 'Мордхейвен: Готичний Жах',
        'desc': 'Похмурий світ проклятих лісів, кривавих місяців, інквізиції, вампірських родів та древніх склепів.',
        'threat': 'Невмирущий Граф Воронячого Піку',
        'races': ['Вцілілий Смертний', 'Денний Напіввампір', 'Проклятий Вовкулака', 'Чорнокнижник Тіней', 'Занепалий Лицар', 'Привид Склепу'],
        'pieces': [
            'candle-flame', 'bat-cave-dusk', 'castle-bridge-dawn',
            'lightning-storm', 'starry-ridge', 'tunnel',
            'volcano-eruption', 'starfield-warp'
        ]
    },
    'cosmic_scifi': {
        'id': 'cosmic_scifi',
        'name': 'Квазар-9: Неонова Безодня',
        'desc': 'Науково-фантастична сага: далекі орбітальні колонії, бунтівні кіборги, рої темної матерії та гравітаційні аномалії.',
        'threat': 'Нексус Сінгулярності Тіней',
        'races': ['Кібер-Людина', 'Зоряний Синтетик', 'Мутант Пустоти', 'Клонований Пілот', 'Ефірний Іншопланетянин', 'Квантовий Мандрівник'],
        'pieces': [
            'black-hole', 'asteroid-belt', 'binary-stars',
            'matrix-rain', 'starfield-warp', 'wireframe-globe',
            'laser-scan', 'tesseract'
        ]
    },
    'steampunk_abyss': {
        'id': 'steampunk_abyss',
        'name': 'Ефірополіс: Залізний Подих',
        'desc': 'Світ парових титанів, котельних безодень, літаючих цепелінів, підступних баронів та магічного ефіру.',
        'threat': 'Залізний Архімашиніст',
        'races': ['Паровий Механік', 'Ефірний Алхімік', 'Небесний Корсар', 'Заводний Автоматон', 'Шляхетний Лорд', 'Підпільний Диверсант'],
        'pieces': [
            'pipe-flow', 'radar-sweep', 'viaduct-steam-train',
            'twin-pane-commander', 'water-caustics', 'wireframe-city',
            'volcano-eruption', 'starry-ridge'
        ]
    },
    'neon_arcana_heartfire': {
        'id': 'neon_arcana_heartfire',
        'name': 'Неоновий Арканум: Серця Залізного Вогню',
        'desc': 'Кіберпанк-мегаполіс, де код замінює кров, а руни — програмний код. Темне міське фентезі з неоновими катедралями, корпоративними вампірами та романтикою, що ламає системи.',
        'threat': 'Сплячий Архітектор Коду',
        'races': ['Неоновий Ельф', 'Кібер-Гном', 'Відьма Коду', 'Вуличний Вовк', 'Вампір Корпорації', 'Синтетик-Андроїд'],
        'pieces': [
            'neon-city-rain', 'cyberpunk-alley', 'matrix-rain',
            'data-flow', 'neon-sign-flicker', 'holo-grid-sphere',
            'computer-lab-terminals', 'wireframe-city', 'terminal-session', 'glitch-title-settle'
        ],
        'locations': ['Сховище «Колиска»']
    }
}

DIFFICULTIES: Dict[str, Dict[str, Any]] = {
    'story': {'id': 'story', 'name': 'Наративна подорож', 'desc': 'Більше здоров’я, менше смертельних ризиків, фокус на сюжеті.'},
    'normal': {'id': 'normal', 'name': 'Класична сага', 'desc': 'Збалансовані випробування, чесні кубики долі та перевірки навичок.'},
    'hardcore': {'id': 'hardcore', 'name': 'Залізна воля (Permadeath)', 'desc': 'Жорсткі наслідки кожної помилки, висока ціна вибору.'}
}

ALL_ACT_LOCATIONS = {
    'fantasy': [
        'Селище Окгем', 'Шепітливий Ліс', 'Скелі Залізокуття', 'Рубіж Могильних Курганів',
        'Столиця Сонячного Шпилю', 'Прірва Тіньопаду', 'Цитадель Чорного Сонця', 'Пантеон Долі'
    ],
    'dark_gothic': [
        'Чорний Хутір Грішників', 'Дрімучий Бор Мовчання', 'Руїни Старої Каплиці', 'Підземелля Забутого Ордену',
        'Багряний Замок Воронячого Піку', 'Безодня Кривавого Озера', 'Шпиль Опівнічного Дзвону', 'Трон Незримої Вічності'
    ],
    'cosmic_scifi': [
        'Периферійний Блок Станції-7', 'Неонові Доки Нижнього Рівня', 'Покинутий Шахтний Астероїд', 'Сектор Гіперпросторового Розлому',
        'Цитадель Корпоративного Ядра', 'Гравітаційний Колодязь Пустоти', 'Орбітальний Флагман Сингулярності', 'Край Відомого Всесвіту'
    ],
    'steampunk_abyss': [
        'Слобода Котельників та Зварювальників', 'Парові Доки Великого Каналу', 'Ефірне Роздоріжжя Шестерень', 'Лінія Барикад Проти Автоматонів',
        'Верхній Сапфіровий Палац Паробаронів', 'Пекло Головного Котла', 'Залізна Твердиня Архімашиніста', 'Шпиль Вічного Двигуна'
    ],
    'neon_arcana_heartfire': [
        'Сховище «Колиска»', 'Сміттєві Поля', 'Академія Аркана-Тех', 'Неоновий Розлом',
        'Верхнє Місто', 'Глибокий Код', 'Вежа Архітектора', 'Скрижалі Вічності'
    ]
}


def build_vector_plot_act(act_id: int, world_id: str, seed: int, plot_vector: Dict[str, Any], character_name: str) -> Dict[str, Any]:
    """
    Генерує унікальний сюжетний Акт на основі векторних координат долі (Plot Vector).
    """
    world = WORLD_PRESETS.get(world_id, WORLD_PRESETS['fantasy'])
    threat = world['threat']
    rng = random.Random(seed + act_id * 7919)

    c_o = plot_vector.get('chaos_order', 0.0)
    l_s = plot_vector.get('light_shadow', 0.0)
    a_d = plot_vector.get('aggression_diplomacy', 0.0)

    act_locations = ALL_ACT_LOCATIONS.get(world_id, ALL_ACT_LOCATIONS['fantasy'])
    loc_index = min(act_id - 1, len(act_locations) - 1)
    current_location = act_locations[loc_index]

    act_titles = {
        1: ("Пробудження Зірок", "Перші кроки та знак доленосного народження"),
        2: ("Поклик Незвіданого", "Перше зіткнення з таємницями світу"),
        3: ("Випробування Сили", "Клятва шляху та вибір наставника"),
        4: ("Розрив Печатки", "Світ тріщить по швах під натиском темряви"),
        5: ("Інтриги Великого Престолу", "Змова у верхах та ціна справжньої влади"),
        6: ("Спуск у Безодню", "Шлях крізь тіні до самого серця загрози"),
        7: ("Велика Битва", "Вирішальне протистояння з ворогом епохи"),
        8: ("Спадок Вічності", "Фінальний вибір та увічнення легенди")
    }

    base_title, base_sub = act_titles.get(act_id, ("Новий Рубіж", "Шлях триває"))

    tone = "похмурий" if l_s < -0.2 else ("піднесений" if l_s > 0.2 else "врівноважений")

    # --- Процедурний зустрічний NPC сцени (унікальний для акту та зерна) ---
    from .npc_sandbox import generate_local_npc
    scene_npc = generate_local_npc(
        world_id=world_id,
        location=current_location,
        seed_val=seed,
        turn=act_id,
        race=world.get('races', ['Людина'])[0],
        variant=act_id * 31 + 7,
    )
    npc_name = scene_npc['name']
    npc_role = scene_npc['role_title']
    npc_temper = scene_npc['temperament']
    npc_appearance = ", ".join(scene_npc['appearance'])
    npc_style = scene_npc['dialogue_style']

    npc_opening = {
        'formal': f"{npc_name} урочисто вклоняється: «Вітаю тебе, {character_name}.»",
        'rustic': f"{npc_name} спльовує й бурчить: «Ну і кого це вітер приніс...»",
        'poetic': f"{npc_name}, зачарований краєм, шепоче: «Давно я чекав на таку зустріч...»",
        'curt': f"{npc_name} суворо кивнув: «Кажи швидше, час не чекає.»",
        'flirtatious': f"{npc_name} з хитрим поглядом посміхається: «О, який цікавий мандрівник...»",
    }.get(npc_style, f"{npc_name} звертається до тебе:")

    temper_line = {
        'noble': "У його/її погляді читається гідність і гордість.",
        'cunning': "Оживі хитро блищать в очах, оцінюючи твою вигоду.",
        'hotheaded': "Він/вона здається готовим/ою спалахнути від першого слова.",
        'melancholic': "На обличчі відсутній спокій, ніби він/вона втратила щось дорогоцінне.",
        'romantic': "Його/її погляд теплий і трохи запальний.",
        'greedy': "Жадібні очі оглядають твоє спорядження й гаманець.",
        'fanatic': "Вогник фанатизму палає в очах назустріч твоїм словам.",
        'timid': "Він/вона трохи змішується, але намагається не відвертатися.",
    }.get(npc_temper, "")

    phases = [
        {
            "speaker": "Оповідач",
            "text": f"Світ «{world['name']}» розгортає перед вами скрижалі долі у місці «{current_location}». Загроза — {threat} — кидає свою тінь, і саме тут ваш шлях перетинається з чужим."
        },
        {
            "speaker": "Оповідач",
            "text": f"Крізь {tone} туман місцевості проступає постать: {npc_name}, {npc_role.lower()} — {npc_appearance}. {temper_line} Ваші вчинки формують тканину цієї епохи, і {character_name} відчуває, що ця зустріч вже вплинула на вектор балансу сил."
        },
        {
            "speaker": npc_name,
            "text": f"{npc_opening} «Слухай, мандрівник: {threat} стає все сильнішим. Мені потрібна твоя допомога — або твоя зброя. Але спершу покажи, що ти за людина.»"
        },
        {
            "speaker": "Оповідач",
            "text": f"Повітря напружилося. {npc_name} чекає вашого слова — або вашого вчинку. Це момент, коли доля залежить від вибору."
        }
    ]

    choices = [
        {
            "id": f"act_{act_id}_opt_a",
            "prose": f"Вчинити рішуче та прокласти свій шлях силою крізь небезпеку {current_location}.",
            "vector_delta": {"aggression_diplomacy": 0.25, "chaos_order": -0.1},
            "stat_check": "strength",
            "reward": {"score": 120, "gold": 25}
        },
        {
            "id": f"act_{act_id}_opt_b",
            "prose": f"Шукати приховані знання та давні таємниці, щоб розкрити плани ворога.",
            "vector_delta": {"mystery_reason": 0.25, "light_shadow": 0.15},
            "stat_check": "intelligence",
            "reward": {"score": 130, "mana": 15}
        },
        {
            "id": f"act_{act_id}_opt_c",
            "prose": f"Заручитися підтримкою союзників та знайти компроміс через слово й авторитет.",
            "vector_delta": {"aggression_diplomacy": -0.25, "chaos_order": 0.2},
            "stat_check": "charisma",
            "reward": {"score": 140, "reputation": 5}
        },
        {
            "id": f"act_{act_id}_opt_d",
            "prose": f"Звернутися безпосередньо до {npc_name} ({npc_role.lower()}), переконуючи його/її приєднатися до вашого плану.",
            "vector_delta": {"aggression_diplomacy": -0.1, "mystery_reason": 0.15},
            "stat_check": "charisma",
            "reward": {"score": 150, "reputation": 8},
            "npc_recruit": True
        },
        {
            "id": f"act_{act_id}_opt_e",
            "prose": f"Замість союзника зробити {npc_name} своїм заручником — силою примусити його/її відати таємницю ворога.",
            "vector_delta": {"aggression_diplomacy": 0.3, "chaos_order": 0.25, "light_shadow": -0.2},
            "stat_check": "strength",
            "reward": {"score": 160, "gold": 35},
            "npc_threaten": True
        }
    ]

    piece_list = world.get('pieces', WORLD_PRESETS['fantasy']['pieces'])
    piece = piece_list[min(act_id - 1, len(piece_list) - 1)]

    return {
        "act_id": act_id,
        "title": f"Акт {act_id} · {base_title}",
        "subtitle": base_sub,
        "location": current_location,
        "phases": phases,
        "choices": choices,
        "scene_piece": piece,
        "scene_npc": {
            "name": npc_name,
            "role_title": npc_role,
            "temperament": npc_temper,
            "appearance": npc_appearance,
        }
    }
