"""
World database manager and routing utilities for Life-RPG.
Each world lives in its own (world_name).sqlite3 database.
"""
import os
import re
from pathlib import Path
from typing import Optional, Tuple, List
from django.conf import settings
from django.db import connections
from django.core.management import call_command

KNOWN_WORLDS = {
    'fantasy',
    'dark_gothic',
    'cosmic_scifi',
    'steampunk_abyss',
}


def sanitize_world_id(raw_world: Optional[str]) -> str:
    """Sanitizes raw world identifier into a valid safe filename/alias."""
    if not raw_world:
        return 'fantasy'
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '', str(raw_world).strip().lower())
    return clean or 'fantasy'


def ensure_world_database(world_id: str) -> str:
    """
    Ensures that the database for world_id is registered in settings.DATABASES,
    its sqlite3 file exists at BASE_DIR / (world_id).sqlite3, and all migrations are applied.
    Returns the database alias.
    """
    alias = sanitize_world_id(world_id)
    db_filename = f"{alias}.sqlite3"
    db_path = settings.BASE_DIR / db_filename

    if alias not in settings.DATABASES:
        settings.DATABASES[alias] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path,
            'ATOMIC_REQUESTS': False,
            'AUTOCOMMIT': True,
            'CONN_HEALTH_CHECKS': False,
            'CONN_MAX_AGE': 0,
            'OPTIONS': {},
            'TIME_ZONE': None,
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
            'TEST': {'CHARSET': None, 'COLLATION': None, 'MIGRATE': True, 'MIRROR': None, 'NAME': None},
        }
        connections.databases[alias] = settings.DATABASES[alias]

    # Run migrations if database was just registered or tables missing
    try:
        call_command('migrate', database=alias, interactive=False, verbosity=0)
    except Exception as e:
        print(f"Warning: migrate failed for {alias}: {e}")

    # Seed default catalog items into world database
    try:
        from game.models import Item
        from game.event_system import DEFAULT_ITEMS
        if Item.objects.using(alias).count() == 0:
            for item_data in DEFAULT_ITEMS:
                Item.objects.using(alias).create(**item_data)
    except Exception as e:
        print(f"Warning: seeding items failed for {alias}: {e}")

    return alias


def get_character_world_db(character) -> str:
    """Returns database alias where this character resides."""
    if hasattr(character, '_state') and character._state.db:
        return character._state.db
    flags = getattr(character, 'story_flags', None)
    if isinstance(flags, dict) and flags.get('world_id'):
        return sanitize_world_id(flags['world_id'])
    return 'default'


def get_character_from_session(request) -> Tuple[Optional[object], str]:
    """
    Finds the active character from session across world databases.
    Returns (character, db_alias).
    """
    from game.models import Character

    char_id = request.session.get('character_id')
    if not char_id:
        return None, 'default'

    world_id = request.session.get('world_id')
    search_dbs = []
    if world_id:
        search_dbs.append(ensure_world_database(world_id))
    search_dbs.append('default')
    for w in KNOWN_WORLDS:
        if w not in search_dbs:
            search_dbs.append(ensure_world_database(w))

    for db in search_dbs:
        try:
            char = Character.objects.using(db).filter(id=char_id).first()
            if char:
                return char, db
        except Exception:
            continue

    return None, 'default'


def get_all_hall_of_fame(limit: int = 5) -> List[object]:
    """Retrieves top fallen characters across all databases."""
    from game.models import Character
    all_chars = []
    dbs = ['default'] + list(KNOWN_WORLDS)
    for db in dbs:
        try:
            chars = list(Character.objects.using(db).filter(is_alive=False).order_by('-score')[:limit])
            all_chars.extend(chars)
        except Exception:
            continue
    all_chars.sort(key=lambda c: c.score or 0, reverse=True)
    return all_chars[:limit]


def get_all_graveyard() -> Tuple[List[object], List[object]]:
    """Retrieves all deceased and living characters across all databases."""
    from game.models import Character
    all_deceased = []
    all_living = []
    dbs = ['default'] + list(KNOWN_WORLDS)
    for db in dbs:
        try:
            dec = list(Character.objects.using(db).filter(is_alive=False).order_by('-score'))
            liv = list(Character.objects.using(db).filter(is_alive=True).order_by('-score'))
            all_deceased.extend(dec)
            all_living.extend(liv)
        except Exception:
            continue
    all_deceased.sort(key=lambda c: c.score or 0, reverse=True)
    all_living.sort(key=lambda c: c.score or 0, reverse=True)
    return all_deceased, all_living


def create_world_character(world_id: str, custom_name: str = "", seed_val: int = 0, difficulty: str = "normal"):
    """
    Creates a new character inside the dedicated (world_id).sqlite3 database.
    """
    import random
    from game.models import Character, Item
    from game.event_system import (
        RACES, ORIGINS, NAME_SYLLABLES, DEFAULT_ITEMS
    )
    from game.plot_generator import WORLD_PRESETS, DIFFICULTIES

    db_alias = ensure_world_database(world_id)
    world_info = WORLD_PRESETS.get(world_id, WORLD_PRESETS['fantasy'])

    world_rng = random.Random(seed_val) if seed_val else random.Random()

    # Race selection from world presets or default
    world_races = world_info.get("races")
    if world_races:
        race = world_rng.choice(world_races)
    else:
        race = world_rng.choice(RACES)

    origin_obj = world_rng.choice(ORIGINS)

    prefixes, suffixes = NAME_SYLLABLES.get(race, (['Герой'], ['']))
    gen_name = f"{world_rng.choice(prefixes)}{world_rng.choice(suffixes)}"
    name = custom_name.strip() if custom_name.strip() else gen_name

    def roll_3d6():
        return sum(world_rng.randint(1, 6) for _ in range(3))

    str_val = roll_3d6() + origin_obj['bonus'].get('strength', 0)
    agi_val = roll_3d6() + origin_obj['bonus'].get('agility', 0)
    int_val = roll_3d6() + origin_obj['bonus'].get('intelligence', 0)
    cha_val = roll_3d6() + origin_obj['bonus'].get('charisma', 0)
    luck_val = roll_3d6() + origin_obj['bonus'].get('luck', 0)

    starting_locs = world_info.get("locations", ["Селище Окгем"])
    start_location = world_rng.choice(starting_locs)

    diff_info = DIFFICULTIES.get(difficulty, {})
    hp_mult = 1.0
    gold_mult = 1.0
    if difficulty == 'story':
        hp_mult, gold_mult = 1.3, 1.5
    elif difficulty == 'hardcore':
        hp_mult, gold_mult = 0.8, 0.7

    base_hp = int((50 + str_val * 2) * hp_mult)
    base_mana = 20 + int_val * 2
    base_gold = int((10 + cha_val) * gold_mult)

    initial_vector = {
        "chaos_order": 0.0,
        "light_shadow": 0.0,
        "aggression_diplomacy": 0.0,
        "mystery_reason": 0.0
    }

    story_flags = {
        "world_id": world_id,
        "world_name": world_info["name"],
        "seed": seed_val,
        "difficulty": difficulty,
        "difficulty_name": diff_info.get("name", "Класична сага"),
        "vector_plot_enabled": True,
        "plot_vector": initial_vector,
        "current_act": 1,
        "completed_acts": [],
        "story_interlude_mode": False
    }

    origin_text = origin_obj.get('text', 'Виріс у старій хатині')
    origin_trait = origin_obj.get('trait', 'Загартований')

    # Save to the dedicated world database!
    character = Character(
        name=name,
        race=race,
        origin=origin_text,
        traits=[origin_trait],
        age=0,
        turns=0,
        current_location=start_location,
        hp=base_hp,
        max_hp=base_hp,
        mana=base_mana,
        max_mana=base_mana,
        gold=base_gold,
        strength=str_val,
        agility=agi_val,
        intelligence=int_val,
        charisma=cha_val,
        luck=luck_val,
        story_act=1,
        story_phase=0,
        story_flags=story_flags,
    )
    character.save(using=db_alias)

    # Initial log in world db
    character.logs.create(
        age=0,
        turn=0,
        title="Народження та світанок життя",
        text=f"Немовля раси {race} з'явилося на світ у краї {start_location} світу {world_info['name']}. "
             f"Передісторія: {origin_text}",
        log_type='system'
    )

    # Starter potion in world db
    starter_potion = Item.objects.using(db_alias).filter(name='Мале зілля здоров’я').first()
    if not starter_potion:
        starter_potion = Item.objects.using(db_alias).filter(item_type='POTION').first()
    if starter_potion:
        character.inventory.create(item=starter_potion, quantity=2)

    return character, db_alias
