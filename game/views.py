from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import JsonResponse, HttpResponseNotAllowed
from .models import Character, InventoryItem, LogEntry
from .event_system import (
    seed_default_items,
    generate_random_fantasy_character,
    trigger_random_event,
    process_event_choice
)
from .novel_engine import (
    get_active_novel_state,
    advance_novel_phase,
    skip_novel_phases,
    resolve_novel_choice,
    perform_interlude,
)
from .novel_prose import (
    enrich_event,
    enrich_choices,
    enrich_interludes,
    prose_outcome,
    chapter_bridge,
)
import random
import json


@never_cache
def index_view(request):
    """Landing page: random fantasy birth generator & Hall of Fame."""
    seed_default_items()
    hall_of_fame = Character.objects.filter(is_alive=False).order_by('-score')[:5]

    active_character = None
    char_id = request.session.get('character_id')
    if char_id:
        active_character = Character.objects.filter(id=char_id).first()

    from .plot_generator import WORLD_PRESETS, DIFFICULTIES
    return render(request, 'game/index.html', {
        'active_character': active_character,
        'hall_of_fame': hall_of_fame,
        'world_presets': WORLD_PRESETS,
        'difficulties': DIFFICULTIES,
    })


def start_game_view(request):
    """Generates run character starting at Age 0 with custom world, seed, and vector plot."""
    if request.method == 'POST':
        import random
        from .plot_generator import WORLD_PRESETS, DIFFICULTIES

        custom_name = request.POST.get('name', '').strip()
        world_id = request.POST.get('world_id', 'fantasy').strip()
        if world_id not in WORLD_PRESETS:
            world_id = 'fantasy'
        
        difficulty = request.POST.get('difficulty', 'normal').strip()
        if difficulty not in DIFFICULTIES:
            difficulty = 'normal'

        seed_raw = request.POST.get('seed', '').strip()
        if not seed_raw:
            seed_val = random.randint(100000, 999999)
        else:
            try:
                seed_val = int(seed_raw)
            except ValueError:
                seed_val = abs(hash(seed_raw)) % 1000000

        # Generate base fantasy character
        character = generate_random_fantasy_character()

        world_info = WORLD_PRESETS[world_id]
        if custom_name:
            character.name = custom_name

        # Align location with world starting locations
        starting_locs = world_info.get("locations", ["Невідомий край"])
        world_rng = random.Random(seed_val)
        character.current_location = world_rng.choice(starting_locs)

        # Initialize vector plot story state
        initial_vector = {
            "chaos_order": 0.0,
            "light_shadow": 0.0,
            "aggression_diplomacy": 0.0,
            "mystery_reason": 0.0
        }

        # Pick race from chosen world
        world_races = world_info.get("races", [])
        if world_races:
            character.race = world_rng.choice(world_races)

        # Apply difficulty adjustments
        diff_info = DIFFICULTIES.get(difficulty, {})
        hp_mult = diff_info.get("hp_mult", 1.0)
        gold_mult = diff_info.get("gold_mult", 1.0)
        if difficulty == 'story':
            hp_mult, gold_mult = 1.3, 1.5
        elif difficulty == 'hardcore':
            hp_mult, gold_mult = 0.8, 0.7

        character.max_hp = int(character.max_hp * hp_mult)
        character.current_hp = character.max_hp
        character.gold = int(character.gold * gold_mult)

        # Story flags setup
        if not isinstance(character.story_flags, dict):
            character.story_flags = {}

        character.story_flags.update({
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
        })
        character.save()

        request.session['character_id'] = character.id
        messages.success(request, f"Ви розпочали шлях у світі {world_info['name']} як {character.name} (Зерно: {seed_val})!")
        return redirect('game:play')

    return redirect('game:index')


@never_cache
def play_view(request):
    """Main fantasy Visual Novel RPG dashboard."""
    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)

    if not character.is_alive:
        messages.warning(request, f"{character.name} відійшов у вічність.")
        return redirect('game:graveyard')

    relics = InventoryItem.objects.filter(character=character).select_related('item')
    chronicle_logs = character.logs.all().order_by('-id')
    latest_story = chronicle_logs.first()
    active_event = request.session.get('active_event')

    # Visual Novel RPG progression state
    novel_state = get_active_novel_state(character)

    # --- Шар прози: подаємо механіку як роман ---
    if active_event:
        active_event = enrich_event(active_event)
    novel_state['choices'] = enrich_choices(novel_state.get('choices', []))
    novel_state['interlude_options'] = enrich_interludes(novel_state.get('interlude_options', []))

    return render(request, 'game/play.html', {
        'character': character,
        'relics': relics,
        'chronicle_logs': chronicle_logs,
        'latest_story': latest_story,
        'active_event': active_event,
        'novel_state': novel_state,
    })


def perform_action_view(request):
    """Novel-driven actions only: story advancement, events, items."""
    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    if not character.is_alive:
        return redirect('game:graveyard')

    action = request.POST.get('action')

    if action == 'advance_novel_phase':
        advance_novel_phase(character)
        return redirect('game:play')

    elif action in ['pass_novel_phases', 'skip_novel_phases', 'skip_phase']:
        skip_novel_phases(character)
        messages.info(request, "⏭️ Ви перейшли до моменту прийняття доленосного рішення.")
        return redirect('game:play')

    elif action in ['resolve_novel_choice', 'resolve_choice']:
        act_id_val = request.POST.get('act_id') or character.story_act or 1
        try:
            act_id = int(act_id_val)
        except (ValueError, TypeError):
            act_id = character.story_act or 1
        choice_id = request.POST.get('choice_id') or request.POST.get('choice_index')
        res = resolve_novel_choice(character, act_id, choice_id)
        if res.get('success'):
            messages.success(request, prose_outcome(res.get('message', 'Рішення прийнято!')))
            # Випадкова сюжетна зустріч: шлях не буває лінійним.
            if random.random() < 0.45:
                side_event = trigger_random_event(character)
                side_event['opener'] = chapter_bridge()
                request.session['active_event'] = side_event
        else:
            messages.warning(request, res.get('message', 'Не вдалося виконати дію.'))
        return redirect('game:play')

    elif action == 'interlude':
        interlude_type = request.POST.get('interlude_type', 'training')
        res = perform_interlude(character, interlude_type)
        if res.get('success'):
            messages.success(request, f"🌿 {res.get('message')}")
        else:
            messages.warning(request, res.get('message', 'Не вдалося виконати інтерлюдію.'))
        return redirect('game:play')

    elif action == 'resolve_event':
        event_id = request.POST.get('event_id')
        choice_idx = int(request.POST.get('choice_index', 0))
        result_msg = process_event_choice(character, event_id, choice_idx)
        request.session['active_event'] = None
        messages.success(request, prose_outcome(result_msg))

    elif action == 'dismiss_event':
        request.session['active_event'] = None
        messages.info(request, "Ви вирішили оминути цю подію й зосередитися на головній сазі.")
        return redirect('game:play')

    elif action == 'use_item':
        inv_id = request.POST.get('inventory_id')
        inv_item = get_object_or_404(InventoryItem, id=inv_id, character=character)
        item = inv_item.item

        if item.item_type == 'POTION':
            character.modify_stats(hp=item.hp_bonus, mana=item.mana_bonus)
            if inv_item.quantity > 1:
                inv_item.quantity -= 1
                inv_item.save()
            else:
                inv_item.delete()

            msg = f"🧪 Випито зілля: {item.name}! (+{item.hp_bonus} ОЗ, +{item.mana_bonus} Мана)"
            messages.success(request, msg)
            LogEntry.objects.create(
                character=character,
                age=character.age,
                turn=character.turns,
                title=f"Вжито {item.name}",
                text=msg,
                log_type='event'
            )
        else:
            messages.info(request, f"{item.name} є постійним спорядженням, його бонуси вже діють!")

    return redirect('game:play')


def advance_narrator_phase_view(request):
    """
    1. Advance phase: player clicks '▶ Далі' or presses Space/Enter
    -> increments character.story_phase until max phase is reached.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    if not character.is_alive:
        return redirect('game:graveyard')

    novel_state = advance_novel_phase(character)

    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('Accept', '')
    )
    if is_json:
        return JsonResponse({
            'status': 'ok',
            'phase': character.story_phase,
            'max_phase': novel_state.get('total_phases'),
            'is_ready_for_choice': novel_state.get('is_ready_for_choice'),
            'current_phase': novel_state.get('current_phase'),
            'act_id': novel_state.get('act_id'),
        })

    return redirect('game:play')


def skip_narrator_phase_view(request):
    """
    2. Skip phase: player clicks '⏭️ До виборів' or presses Tab
    -> sets character.story_phase = max phase, immediately displaying choices.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    if not character.is_alive:
        return redirect('game:graveyard')

    novel_state = skip_novel_phases(character)
    messages.info(request, "⏭️ Ви перейшли до моменту прийняття доленосного рішення.")

    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('Accept', '')
    )
    if is_json:
        return JsonResponse({
            'status': 'ok',
            'phase': character.story_phase,
            'max_phase': novel_state.get('total_phases'),
            'is_ready_for_choice': True,
            'choices_count': len(novel_state.get('choices', [])),
            'message': 'Перейдено до виборів.'
        })

    return redirect('game:play')


def resolve_story_choice_view(request):
    """
    3. Resolve choice: player makes choice [1], [2], [3]
    -> applies consequences, logs to Chronicle, records flags,
       advances to next Act or sets next story node!
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    if not character.is_alive:
        return redirect('game:graveyard')

    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('Accept', '')
    )

    act_id = None
    choice_id = None
    choice_index = None

    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body.decode('utf-8'))
            act_id = body.get('act_id')
            choice_id = body.get('choice_id')
            choice_index = body.get('choice_index')
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    else:
        act_id = request.POST.get('act_id')
        choice_id = request.POST.get('choice_id')
        choice_index = request.POST.get('choice_index')

    if choice_id:
        target_choice = choice_id
    elif choice_index is not None and str(choice_index).isdigit():
        target_choice = int(choice_index)
    else:
        target_choice = 0

    if not act_id:
        act_id = getattr(character, 'story_act', 1) or 1
    else:
        try:
            act_id = int(act_id)
        except (ValueError, TypeError):
            act_id = getattr(character, 'story_act', 1) or 1

    res = resolve_novel_choice(character, act_id, target_choice)

    if res.get('success'):
        if is_json:
            return JsonResponse({'status': 'ok', 'result': res})
        messages.success(request, prose_outcome(res.get('message', 'Рішення прийнято!')))
    else:
        if is_json:
            return JsonResponse({'status': 'error', 'message': res.get('message')}, status=400)
        messages.warning(request, res.get('message', 'Не вдалося виконати дію.'))

    return redirect('game:play')


def interlude_action_view(request):
    """
    4. Interlude: Between acts (or if waiting for next min_age), player can engage in
    rich narrative life interludes (training, arcane study, travel, fellowship) that
    yield narrative journal entries and age up by 1 year.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    if not character.is_alive:
        return redirect('game:graveyard')

    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('Accept', '')
    )

    interlude_type = 'training'
    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body.decode('utf-8'))
            interlude_type = body.get('interlude_type', 'training')
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    else:
        interlude_type = request.POST.get('interlude_type', 'training')

    res = perform_interlude(character, interlude_type)

    if res.get('success'):
        if is_json:
            return JsonResponse({'status': 'ok', 'result': res})
        messages.success(request, prose_outcome(res.get('message')))
    else:
        if is_json:
            return JsonResponse({'status': 'error', 'message': res.get('message')}, status=400)
        messages.warning(request, res.get('message', 'Не вдалося виконати інтерлюдію.'))

    return redirect('game:play')


def chronicle_view(request):
    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    logs = character.logs.all().order_by('id')
    return render(request, 'game/chronicle.html', {'character': character, 'logs': logs})


def graveyard_view(request):
    deceased = Character.objects.filter(is_alive=False).order_by('-score')
    living = Character.objects.filter(is_alive=True).order_by('-score')
    return render(request, 'game/graveyard.html', {'deceased': deceased, 'living': living})


def retire_view(request):
    char_id = request.session.get('character_id')
    if not char_id:
        return redirect('game:index')

    character = get_object_or_404(Character, id=char_id)
    if character.is_alive:
        character.is_alive = False
        character.cause_of_death = f"Вознісся до легенд у віці {character.age} років, осівши як шанований старійшина."
        character.score = character.calculate_score()
        character.save()

        LogEntry.objects.create(
            character=character,
            age=character.age,
            turn=character.turns,
            title="Легендарне вознесіння",
            text=f"{character.name} завершив свою славетну подорож із {character.score} очками легенди!",
            log_type='death'
        )
        messages.success(request, f"{character.name} вознісся до Зали Слави!")

    return redirect('game:graveyard')
