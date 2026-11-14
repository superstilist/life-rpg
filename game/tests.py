from django.test import TestCase, Client
from django.urls import reverse
from game.models import Character, Item, InventoryItem
import json


class NovelEngineControlFlowTestCase(TestCase):
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
        char = Character.objects.first()
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
