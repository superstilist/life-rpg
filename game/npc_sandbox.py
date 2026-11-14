"""
Процедурний соціальний пісочний рушій NPC для Life-RPG.
Генерує унікальних жителів локацій та обробляє взаємодії:
жести, романтику, вбивство. NPC живуть у базі даних світу.
"""
import random
from typing import Dict, Any, List
from .models import WorldNPC


NPC_NAME_SYLLABLES = {
    'M': {
        'prefix': ['Аль', 'Вор', 'Гар', 'Дор', 'Ель', 'Зор', 'Ка', 'Лор', 'Мир',
                   'Нор', 'Ор', 'Рен', 'Сар', 'Тар', 'Ур', 'Фен', 'Хал', 'Цир', 'Шер', 'Яр'],
        'suffix': ['дін', 'вен', 'рон', 'гар', 'мир', 'нор', 'рен', 'тан', 'фей',
                   'хор', 'цій', 'шан', 'ярд', 'бор', 'віс', 'ґрон'],
    },
    'F': {
        'prefix': ['Ае', 'Ве', 'Га', 'Ела', 'Зі', 'Іл', 'Ка', 'Лі', 'Мі', 'На',
                   'Оро', 'Сі', 'Та', 'Ул', 'Фе', 'Ха', 'Це', 'Ша', 'Юл'],
        'suffix': ['рія', 'лена', 'міра', 'на', 'ра', 'ріс', 'са', 'танія', 'фія',
                   'ша', 'бел', 'дора', 'ліна', 'мара', 'нестія'],
    },
}

NPC_ROLES = {
    'villager': ('Сільський житель', 'noble'),
    'merchant': ('Торговець', 'cunning'),
    'guard': ('Вартівник', 'noble'),
    'hermit': ('Відлюдник', 'melancholic'),
    'artisan': ('Майстер', 'noble'),
    'healer': ('Цілитель', 'romantic'),
    'mystic': ('Містик', 'melancholic'),
    'scoundrel': ('Пройдисвіт', 'cunning'),
    'noble': ('Дворянин', 'noble'),
    'wanderer': ('Мандрівник', 'noble'),
    'outcast': ('Вигнанець', 'melancholic'),
    'beast_tamer': ('Приборкувач звірів', 'hotheaded'),
    'priest': ('Жрець', 'fanatic'),
}

NPC_APPEARANCE_TRAITS = [
    "з шрамом через око", "з дерев'яним протезом", "у запльованих шатах",
    "із сяйним амулетом на шиї", "з довгою бусизною бородою", "у маскарадній масці",
    "з чорним плащем і капюшоном", "у бронзованих наплечниках",
    "з татуюванням рун на руці", "у вишиваній хустині",
    "із кільцем-печаткою", "з посохом, що світиться",
]

DIALOGUE_STYLES = ['formal', 'rustic', 'poetic', 'curt', 'flirtatious']


def generate_npc_name(rng: random.Random, gender: str) -> str:
    g = 'F' if gender == 'F' else 'M'
    syl = NPC_NAME_SYLLABLES.get(g, NPC_NAME_SYLLABLES['M'])
    return f"{rng.choice(syl['prefix'])}{rng.choice(syl['suffix'])}"


def generate_local_npc(world_id: str, location: str, seed_val: int,
                       turn: int = 0, race: str = 'Людина',
                       variant: int = 0) -> Dict[str, Any]:
    """Повертає словник з даними нового процедурного NPC."""
    rng = random.Random(seed_val + variant * 1013 + turn)
    gender = rng.choice(['M', 'F'])
    name = generate_npc_name(rng, gender)
    role_key = rng.choice(WorldNPC.ROLE_ARCHETYPES)
    role_title, base_temper = NPC_ROLES.get(role_key, ('Місцевий житель', 'noble'))
    temperament = rng.choice(WorldNPC.TEMPERAMENTS) if rng.random() < 0.6 else base_temper

    return {
        'name': name,
        'gender': gender,
        'race': race,
        'role_title': role_title,
        'temperament': temperament,
        'location': location,
        'world_id': world_id,
        'seed_val': seed_val,
        'age': rng.randint(14, 75),
        'gold': rng.randint(5, 200),
        'strength': rng.randint(2, 18),
        'affection': 0,
        'respect': rng.randint(10, 40),
        'fear': 0,
        'trust': rng.randint(5, 30),
        'relationship': 'stranger',
        'is_alive': True,
        'appearance': rng.sample(NPC_APPEARANCE_TRAITS, k=2),
        'dialogue_style': rng.choice(DIALOGUE_STYLES),
        'memory_log': [],
        'first_met_at_turn': turn,
    }


def npc_speak(npc, context: str = "", character_name: str = "") -> str:
    """Генерує репліку NPC у його власному стилі (приймає модель або словник)."""
    def g(key, default=None):
        return getattr(npc, key, None) if not isinstance(npc, dict) else npc.get(key, default)

    style = g('dialogue_style', 'formal') or 'formal'
    name = g('name', 'Незнайомець') or 'Незнайомець'
    rel = g('relationship', 'stranger') or 'stranger'
    cn = character_name or "мандруючий"

    openings = {
        'formal': [f"{name} вклоняється: ", f"— {name} каже урочисто: "],
        'rustic': [f"{name} спльовує й бурчить: ", f"{name} зрушно відповідає: "],
        'poetic': [f"{name}, зачарований краєм, шепоче: ", f"{name} мелодійно промовляє: "],
        'curt': [f"{name} суворо кивнув: ", f"— {name} відрізав: "],
        'flirtatious': [f"{name} з хитрим поглядом посміхається: ", f"{name} гучно сміється: "],
    }
    open_str = random.choice(openings.get(style, openings['formal']))

    body_map = {
        'stranger': f"«Хто ти такий, {cn}? Спершу покажи свій намір».",
        'acquaintance': f"«Знову ти, {cn}? Що привело тебе сюди?»",
        'friend': f"«Як я радий тебе бачити, {cn}! Розкажи, що тебе вело цієї миті».",
        'confidant': f"«Я вірю твоїм словам, {cn}. Що тебе тривожить?»",
        'lover': f"«Моє серце завжди б'ється швидше при тебе, {cn}...»",
        'spouse': f"«Мій дорогий {cn}, ти знаєш, що я завжди з тобою».",
        'rival': f"«Твоя поява завжди псує мені настрій, {cn}.»",
        'nemesis': f"«Твоя присутність тут — ганьба, {cn}. Ми зустрінемося в кінці.»",
        'deceased': "...",
    }
    return f"{open_str}{body_map.get(rel, '«Що тобі потрібно?»')}"


def process_gesture(character, npc, gesture_type: str) -> Dict[str, Any]:
    """Жест героя відносно NPC: оновлює повагу, страх, симпатію."""
    rng = random.Random(character.id * 7 + npc.id * 13 + hash(gesture_type))
    tem = npc.temperament
    charisma = getattr(character, 'charisma', 10)

    msg = ""
    d_aff, d_resp, d_fear = 0, 0, 0

    if gesture_type == 'bow':
        d_resp = rng.randint(2, 6) if tem in ('noble', 'fanatic') else rng.randint(0, 3)
        msg = f"Ви вклоняєтесь перед {npc.name}. Він/вона з легкою посмішкою кивнув."
        if d_resp > 3 and npc.relationship == 'stranger':
            npc.relationship = 'acquaintance'

    elif gesture_type == 'handshake':
        if tem in ('hotheaded', 'cunning'):
            d_fear = rng.randint(1, 4)
            d_resp = rng.randint(-2, 1)
            msg = f"{npc.name} нерішуче потискає руку, наляканий вашою силою."
        else:
            d_resp = rng.randint(3, 7)
            d_aff = rng.randint(1, 4)
            msg = f"Ваше рукостискання з {npc.name} міцне та щире. Він/вона відчуває повагу."

    elif gesture_type == 'threaten':
        d_fear = rng.randint(10, 25)
        d_resp = rng.randint(-5, -1)
        msg = f"Ви кладете руку на ефес зброї, дивлячись у очі {npc.name}. Він/вона блідіє."
        if npc.fear > 50 and npc.relationship != 'nemesis':
            npc.relationship = 'nemesis'

    elif gesture_type == 'smile':
        if tem in ('romantic', 'melancholic'):
            d_aff = rng.randint(5, 12)
            msg = f"Ваша тепла посмішка змушує {npc.name} задуматися й злегка зашаріти."
        else:
            d_aff = rng.randint(2, 5)
            msg = f"{npc.name} з опаскою, але й з цікавістю відповідає на вашу посмішку."

    elif gesture_type == 'insult':
        d_resp = rng.randint(-10, -3)
        d_fear = rng.randint(0, 8)
        msg = f"Ви зневажливо плюєте під ноги {npc.name}. Він/вона стискає кулаки."
        if rng.random() < 0.35 and npc.relationship not in ('rival', 'nemesis'):
            npc.relationship = 'rival'

    else:
        msg = "Ви робите невизначений жест."

    npc.affection = max(-100, min(100, npc.affection + d_aff))
    npc.respect = max(0, min(100, npc.respect + d_resp))
    npc.fear = max(0, min(100, npc.fear + d_fear))

    npc.memory_log.append({
        'turn': character.turns,
        'action': f"Жест: {gesture_type}",
        'delta': {'aff': d_aff, 'resp': d_resp, 'fear': d_fear},
    })
    npc.save()

    return {
        'success': True,
        'message': msg,
        'affection': npc.affection,
        'respect': npc.respect,
        'fear': npc.fear,
    }


def process_romance(character, npc, action: str) -> Dict[str, Any]:
    """Флірт, спільна вечеря, зізнання в коханні та весілля."""
    rng = random.Random(character.id * 11 + npc.id * 17 + hash(action))
    charisma = getattr(character, 'charisma', 10)
    msg = ""
    d_aff = 0

    if not npc.is_alive:
        return {'success': False, 'message': "Він/вона вже у царстві тіней..."}

    if action == 'compliment':
        success = rng.random() < 0.6 + charisma / 40
        if success:
            d_aff = rng.randint(5, 12)
            msg = f"Ваш комплімент змушує {npc.name} зашаріти й засміятися."
        else:
            d_aff = rng.randint(-3, 1)
            msg = f"{npc.name} з підозрою коситься на вас: «Що ти задумав?»"

    elif action == 'dine_together':
        d_aff = rng.randint(8, 15)
        msg = f"Ви ділите вечерю з {npc.name} біля вогнища. Розмова тече легко."

    elif action == 'confess_love':
        chance = 0.25 + (npc.affection / 200) + (charisma / 60)
        if npc.relationship in ('lover', 'spouse', 'confidant'):
            chance += 0.4
        if rng.random() < chance:
            d_aff = rng.randint(10, 20)
            npc.relationship = 'lover'
            msg = (f"{npc.name} з крихкою посмішкою приймає ваше зізнання: "
                   f"«Я теж це відчуваю...»")
        else:
            d_aff = rng.randint(-8, -2)
            msg = f"{npc.name} збентежено відвертається: «Це надто раптово, мандрівнику»."

    elif action == 'propose_marriage':
        if npc.relationship == 'lover' and npc.affection >= 60:
            npc.relationship = 'spouse'
            msg = (f"{npc.name} скочується перед вами на коліна! "
                   f"{npc.name} — тепер ваша дружина/ваш чоловік!")
        else:
            d_aff = rng.randint(-15, -5)
            msg = f"{npc.name} з жахом відвертається: «Ми ще не знайомі настільки близько!»"

    npc.affection = max(-100, min(100, npc.affection + d_aff))
    npc.memory_log.append({
        'turn': character.turns,
        'action': f"Романтика: {action}",
        'delta': {'aff': d_aff},
    })
    npc.save()

    return {
        'success': npc.relationship in ('lover', 'spouse'),
        'message': msg,
        'relationship': npc.relationship,
        'affection': npc.affection,
    }


def process_npc_kill(character, npc) -> Dict[str, Any]:
    """Вбивство NPC: комбат, наслідки, здобич, страх світу."""
    rng = random.Random(character.id * 3 + npc.id * 5 + character.turns)
    strength = getattr(character, 'strength', 10)
    luck = getattr(character, 'luck', 10)
    npc_str = getattr(npc, 'strength', 5)

    roll = rng.randint(1, 20) + strength // 3 + luck // 6
    target = 8 + npc_str // 2

    if roll >= target:
        npc.is_alive = False
        npc.relationship = 'deceased'
        loot = rng.randint(5, 60)
        character.modify_stats(gold=loot, reputation=-3)
        character.score += 40
        character.save()
        npc.memory_log.append({'turn': character.turns, 'action': 'вбитий героєм'})
        npc.save()
        msg = (f"Завзяті удари досягли мети — {npc.name} падає мертвим. "
               f"Ви забираєте з тіла {loot} золотих, але легенди про вашу жорстокість "
               f"швидко розносяться світом.")
        return {'success': True, 'message': msg, 'loot': loot}

    dmg = rng.randint(10, 30)
    character.modify_stats(hp=-dmg, reputation=-1)
    character.score = max(0, character.score - 10)
    character.save()
    msg = (f"{npc.name} пасткує ваш удар, відповідаючи сильними ударами! "
           f"Ви отримали {dmg} шкоди й втекли, охоплені ганьбою.")
    return {'success': False, 'message': msg}


def spawn_npcs_for_location(world_id: str, location: str, character,
                            count: int = 3) -> List[WorldNPC]:
    """Створює процедурних NPC у базі даних світу, якщо їх там ще немає."""
    from game.world_db import get_character_world_db
    db_alias = get_character_world_db(character)

    existing = list(WorldNPC.objects.using(db_alias).filter(world_id=world_id, location=location))
    alive_count = sum(1 for n in existing if n.is_alive)
    count = max(0, count - alive_count)

    if count > 0:
        for i in range(count):
            data = generate_local_npc(
                world_id=world_id,
                location=location,
                seed_val=character.story_flags.get('seed', 0),
                turn=character.turns,
                race=getattr(character, 'race', 'Людина'),
                variant=alive_count + i,
            )
            npc = WorldNPC(**data)
            npc.save(using=db_alias)

    return list(WorldNPC.objects.using(db_alias).filter(world_id=world_id, location=location))
