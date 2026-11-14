from django.test import TestCase, Client
from django.urls import reverse
from game.models import Character, Item, InventoryItem
import json


class NovelEngineControlFlowTestCase(TestCase):
    databases = '__all__'
    def setUp(self):
        self.client = Client()
        self.character = Character.objects.create(
            name="Аела",
            race="Human",
            age=0,
            turns=0,
            hp=100,
            max_hp=100,
            mana=50,
            max_mana=50,
            gold=50,
            reputation=10,
            strength=14,
            agility=12,
            intelligence=13,
            charisma=11,
            luck=12,
            is_alive=True,
            story_act=1,
            story_phase=0,
            story_flags={},
        )

    def test_advance_narrator_phase_flow(self):
        """1. Advance phase: increments character.story_phase until max phase."""
        from game.novel_engine import advance_novel_phase, get_active_novel_state

        state = get_active_novel_state(self.character)
        self.assertEqual(self.character.story_phase, 0)
        self.assertEqual(state['current_phase_index'], 0)
        self.assertFalse(state['is_ready_for_choice'])

        # Advance to phase 1
        advance_novel_phase(self.character)
        self.character.refresh_from_db()
        self.assertEqual(self.character.story_phase, 1)

        # Advance to phase 2, 3, and max (4)
        advance_novel_phase(self.character)
        advance_novel_phase(self.character)
        state = advance_novel_phase(self.character)
        self.character.refresh_from_db()

        self.assertEqual(self.character.story_phase, 4)
        self.assertTrue(state['is_ready_for_choice'])
        self.assertEqual(len(state['choices']), 3)

        # Further advance does not exceed max phase
        advance_novel_phase(self.character)
        self.character.refresh_from_db()
        self.assertEqual(self.character.story_phase, 4)

    def test_advance_phase_view_endpoint(self):
        """Test advance_narrator_phase_view POST endpoint."""
        session = self.client.session
        session['character_id'] = self.character.id
        session.save()

        response = self.client.post(reverse('game:novel_advance'))
        self.assertRedirects(response, reverse('game:play'))
        self.character.refresh_from_db()
        self.assertEqual(self.character.story_phase, 1)

    def test_skip_narrator_phase_flow(self):
        """2. Skip phase: sets character.story_phase = max phase, immediately displaying choices."""
        from game.novel_engine import skip_novel_phases, get_active_novel_state

        self.assertEqual(self.character.story_phase, 0)
        state = skip_novel_phases(self.character)
        self.character.refresh_from_db()

        self.assertEqual(self.character.story_phase, 4)
        self.assertTrue(state['is_ready_for_choice'])
        self.assertEqual(len(state['choices']), 3)

    def test_skip_phase_view_endpoint(self):
        """Test skip_narrator_phase_view POST endpoint."""
        session = self.client.session
        session['character_id'] = self.character.id
        session.save()

        response = self.client.post(reverse('game:novel_skip'))
        self.assertRedirects(response, reverse('game:play'))
        self.character.refresh_from_db()
        self.assertEqual(self.character.story_phase, 4)

    def test_resolve_choice_advances_act_records_flags(self):
        """
        3. Resolve choice: applies consequences, logs to Chronicle, records flags,
        advances to next Act.
        """
        from game.novel_engine import resolve_novel_choice, get_active_novel_state
        from game.models import LogEntry

        # Make choice 1 (index 0) in Act 1
        res = resolve_novel_choice(self.character, act_id=1, choice_index_or_id=0)
        self.assertTrue(res['success'])
        self.character.refresh_from_db()

        # Act advanced to 2, phase reset to 0
        self.assertEqual(self.character.story_act, 2)
        self.assertEqual(self.character.story_phase, 0)
        self.assertEqual(self.character.age, 1)

        # Flag recorded
        self.assertIn('blessed_by_aether', self.character.story_flags)

        # Logged in Chronicle
        chronicle_log = LogEntry.objects.filter(character=self.character, log_type='quest').first()
        self.assertIsNotNone(chronicle_log)
        self.assertIn("Пророцтво Багряної Комети", chronicle_log.title)

        # Since Act 2 has age_min = 5 and character is age 1, state should be in Interlude!
        state = get_active_novel_state(self.character)
        self.assertTrue(state['is_interlude'])
        self.assertEqual(state['years_until_act'], 4)
        self.assertEqual(len(state['interlude_options']), 4)

    def test_resolve_choice_view_endpoint(self):
        """Test resolve_story_choice_view POST endpoint."""
        session = self.client.session
        session['character_id'] = self.character.id
        session.save()

        response = self.client.post(reverse('game:novel_choice'), {
            'act_id': '1',
            'choice_index': '1'
        })
        self.assertRedirects(response, reverse('game:play'))
        self.character.refresh_from_db()
        self.assertEqual(self.character.story_act, 2)
        self.assertIn('iron_blooded_will', self.character.story_flags)

    def test_interlude_progression_and_act_unlock(self):
        """
        4. Interlude: rich narrative life interludes that yield journal entries,
        age up by 1 year, and unlock next Act when min_age is reached.
        """
        from game.novel_engine import perform_interlude, get_active_novel_state
        from game.models import LogEntry

        self.character.story_act = 2
        self.character.age = 1
        self.character.save()

        # Perform 'training' interlude
        res = perform_interlude(self.character, 'training')
        self.assertTrue(res['success'])
        self.character.refresh_from_db()

        self.assertEqual(self.character.age, 2)
        self.assertIn("Інтерлюдія", res['title'])

        # Check Chronicle entry
        interlude_log = LogEntry.objects.filter(character=self.character, title__startswith="Інтерлюдія").first()
        self.assertIsNotNone(interlude_log)

        # Still in Interlude because Act 2 requires age 5
        state = get_active_novel_state(self.character)
        self.assertTrue(state['is_interlude'])
        self.assertEqual(state['years_until_act'], 3)

        # Fast forward through remaining 3 interludes: age 2 -> 3 -> 4 -> 5
        perform_interlude(self.character, 'arcane_study')
        perform_interlude(self.character, 'travel')
        perform_interlude(self.character, 'fellowship')
        self.character.refresh_from_db()

        self.assertEqual(self.character.age, 5)
        # Act 2 (age_min: 5) is now unlocked and ready!
        state = get_active_novel_state(self.character)
        self.assertFalse(state['is_interlude'])
        self.assertEqual(state['act_id'], 2)
        self.assertEqual(state['current_phase_index'], 0)
        self.assertFalse(state['is_ready_for_choice'])

    def test_interlude_view_endpoint(self):
        """Test interlude_action_view POST endpoint."""
        session = self.client.session
        session['character_id'] = self.character.id
        session.save()

        response = self.client.post(reverse('game:novel_interlude'), {'interlude_type': 'arcane_study'})
        self.assertRedirects(response, reverse('game:play'))
        self.character.refresh_from_db()
        self.assertEqual(self.character.age, 1)
from django.test import TestCase, Client
from django.urls import reverse
from game.models import Character

class RunSetupTestCase(TestCase):
    databases = '__all__'
    def test_run_setup_with_world_and_seed(self):
        client = Client()
        post_data = {
            'name': 'Ворн',
            'world_id': 'cosmic_scifi',
            'difficulty': 'story',
            'seed': '123456'
        }
        resp = client.post(reverse('game:start_game'), post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        # The character is saved in its dedicated world database (cosmic_scifi.sqlite3)
        char = Character.objects.using('cosmic_scifi').first()
        self.assertIsNotNone(char)
        self.assertEqual(char.name, 'Ворн')
        self.assertEqual(char.story_flags.get('world_id'), 'cosmic_scifi')
        self.assertEqual(char.story_flags.get('seed'), 123456)
        self.assertTrue(char.story_flags.get('vector_plot_enabled'))
        self.assertIn('plot_vector', char.story_flags)

        # Verify play page loads vector-generated act
        play_resp = client.get(reverse('game:play'))
        self.assertEqual(play_resp.status_code, 200)
        content = play_resp.content.decode('utf-8')
        self.assertIn('Ворн', content)
from django.test import TestCase, Client
from django.urls import reverse
from game.models import Character, Item, InventoryItem, LogEntry
from game.world_db import KNOWN_WORLDS

class MultiWorldDatabasesTestCase(TestCase):
    databases = '__all__'

    def test_each_world_lives_in_its_own_sqlite_db(self):
        client = Client()
        for world_id in KNOWN_WORLDS:
            post_data = {
                'name': f'Герой_{world_id}',
                'world_id': world_id,
                'difficulty': 'normal',
                'seed': '999111'
            }
            resp = client.post(reverse('game:start_game'), post_data, follow=True)
            self.assertEqual(resp.status_code, 200)

            # Check that character exists in world database
            char = Character.objects.using(world_id).filter(name=f'Герой_{world_id}').first()
            self.assertIsNotNone(char, f"Character should exist in {world_id} database")
            self.assertEqual(char._state.db, world_id)

            # Check that default db does not have this character
            default_char = Character.objects.using('default').filter(name=f'Герой_{world_id}').first()
            self.assertIsNone(default_char, f"Character must not leak into default db")

            # Check play view loads character from its world db
            play_resp = client.get(reverse('game:play'))
            self.assertEqual(play_resp.status_code, 200)
            self.assertIn(f'Герой_{world_id}', play_resp.content.decode('utf-8'))

            # Advance novel phase in this world
            adv_resp = client.post(reverse('game:novel_advance'))
            self.assertEqual(adv_resp.status_code, 302)
            char.refresh_from_db()
            self.assertEqual(char.story_phase, 1)


class NPCSandboxTestCase(TestCase):
    """Перевірка процедурної пісочниці NPC: жести, романтика, вбивство."""
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        resp = self.client.post(reverse('game:start_game'), {
            'name': 'Пісочник',
            'world_id': 'fantasy',
            'difficulty': 'normal',
            'seed': '777',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.char = Character.objects.using('fantasy').first()
        self.assertIsNotNone(self.char)

    def test_npcs_spawn_for_location(self):
        from game.npc_sandbox import spawn_npcs_for_location, WorldNPC
        npcs = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=4)
        self.assertGreaterEqual(len(npcs), 1)
        names = [n.name for n in npcs]
        self.assertEqual(len(names), len(set(names)), "Імена NPC мають бути унікальними")
        self.assertTrue(all(n.is_alive for n in npcs))

    def test_npc_panel_renders(self):
        resp = self.client.get(reverse('game:play'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')
        self.assertIn('Жителі краю', html)
        self.assertIn('поговорити', html)
        self.assertIn('dialogue-overlay', html)

    def test_dialogue_opens_through_modal(self):
        """Діалог відкривається лише через модальне вікно, без прямих кнопок."""
        from game.npc_sandbox import spawn_npcs_for_location
        npc = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=1)[0]

        resp = self.client.get(reverse('game:play'))
        html = resp.content.decode('utf-8')
        # Картка NPC містить лише кнопку діалогу, жодних прямих дій
        self.assertNotIn('вбити', html.lower())
        self.assertNotIn('здатен', html.lower())

    def test_dialogue_node_endpoint(self):
        from game.npc_sandbox import spawn_npcs_for_location
        npc = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=1)[0]
        before = npc.respect

        resp = self.client.post(reverse('game:dialogue_node'), {
            'npc_id': npc.id,
            'node_key': 'gesture_bow',
            'option_index': 0,
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('options', data)
        npc.refresh_from_db()
        self.assertNotEqual(npc.respect, before)

    def test_dialogue_option_requires_relationship(self):
        """Опція, що потребує вірного друга, недоступна для стороннього."""
        from game.npc_sandbox import spawn_npcs_for_location
        npc = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=1)[0]
        npc.relationship = 'stranger'
        npc.save(using='fantasy')

        resp = self.client.post(reverse('game:dialogue_node'), {
            'npc_id': npc.id,
            'node_key': 'romance_confess',
            'option_index': 0,
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('options', data)
        self.assertTrue(any(o.get('locked') for o in data['options']))
        self.assertEqual(data['notice'], 'Потрібна симпатія 20+')

    def test_gesture_updates_respect(self):
        from game.npc_sandbox import spawn_npcs_for_location
        npc = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=1)[0]
        before = npc.respect
        resp = self.client.post(reverse('game:npc_action'), {
            'npc_id': npc.id,
            'action_type': 'gesture',
            'kind': 'bow',
        })
        self.assertEqual(resp.status_code, 302)
        npc.refresh_from_db()
        self.assertGreaterEqual(npc.respect, before)

    def test_kill_npc_marks_deceased(self):
        from game.npc_sandbox import spawn_npcs_for_location, WorldNPC
        npc = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=1)[0]
        # Знижуємо силу NPC та піднімаємо силу героя, щоб гарантувати вбивство
        npc.strength = 0
        npc.save(using='fantasy')
        self.char.strength = 30
        self.char.luck = 30
        self.char.save(using='fantasy')

        killed = False
        for _ in range(5):
            resp = self.client.post(reverse('game:npc_action'), {
                'npc_id': npc.id,
                'action_type': 'kill',
            })
            self.assertEqual(resp.status_code, 302)
            npc.refresh_from_db()
            if not npc.is_alive:
                killed = True
                break
        self.assertTrue(killed, "Гравець має мати можливість вбити NPC")
        self.assertEqual(npc.relationship, 'deceased')

    def test_romance_can_become_spouse(self):
        from game.npc_sandbox import spawn_npcs_for_location
        npc = spawn_npcs_for_location('fantasy', self.char.current_location, self.char, count=1)[0]
        npc.affection = 90
        npc.relationship = 'lover'
        npc.save(using='fantasy')

        resp = self.client.post(reverse('game:npc_action'), {
            'npc_id': npc.id,
            'action_type': 'romance',
            'kind': 'propose_marriage',
        })
        self.assertEqual(resp.status_code, 302)
        npc.refresh_from_db()
        self.assertEqual(npc.relationship, 'spouse')
