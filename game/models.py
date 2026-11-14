from django.db import models
import random
import re


class Character(models.Model):
    RACE_CHOICES = [
        ('Human', 'Human (Balanced & Adaptable)'),
        ('High Elf', 'High Elf (Arcane Affinity & Longevity)'),
        ('Mountain Dwarf', 'Mountain Dwarf (Physical Might & Resilience)'),
        ('Wild Beastkin', 'Wild Beastkin (Feral Agility & Instinct)'),
        ('Shadow Tiefling', 'Shadow Tiefling (Charisma & Nether Luck)'),
        ('Dragonborn', 'Dragonborn (Draconic Power & Aura)'),
    ]

    name = models.CharField(max_length=100)
    race = models.CharField(max_length=50, default='Human')
    origin = models.CharField(max_length=255, default='Born to a humble village family')
    traits = models.JSONField(default=list)  # e.g. ["Mana Sensitive", "Eagle Eye"]

    age = models.IntegerField(default=0)
    turns = models.IntegerField(default=0)
    current_location = models.CharField(max_length=100, default='Oakham Crossroad Village')

    hp = models.IntegerField(default=100)
    max_hp = models.IntegerField(default=100)

    mana = models.IntegerField(default=50)
    max_mana = models.IntegerField(default=50)

    gold = models.IntegerField(default=50)
    reputation = models.IntegerField(default=0)  # -100 (infamous) to +100 (legendary)

    # Core Attributes (3d6 Gaussian rolls: 6 - 18)
    strength = models.IntegerField(default=10)
    agility = models.IntegerField(default=10)
    intelligence = models.IntegerField(default=10)
    charisma = models.IntegerField(default=10)
    luck = models.IntegerField(default=10)

    is_alive = models.BooleanField(default=True)
    cause_of_death = models.CharField(max_length=255, blank=True, null=True)
    score = models.IntegerField(default=0)

    # Visual Novel RPG Progression & Global Story State
    story_act = models.IntegerField(default=1)
    story_phase = models.IntegerField(default=0)  # Current narrator phase in active act
    story_flags = models.JSONField(default=dict)  # Persistent decisions, relationships, relics
    alignment = models.CharField(max_length=50, default='Світло')  # 'Світло', 'Рівновага', 'Тінь'
    companion = models.CharField(max_length=100, blank=True, default='')
    mentor = models.CharField(max_length=100, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_score(self):
        base_score = (self.age * 40) + (self.gold * 2) + (self.reputation * 10) + \
                     (self.strength * 20) + (self.agility * 20) + \
                     (self.intelligence * 20) + (self.charisma * 20) + (self.luck * 30)
        if not self.is_alive and self.age >= 80:
            base_score += 600  # Longevity hero bonus
        return max(0, base_score)

    def check_vitals(self):
        """Checks vital conditions and handles fantasy death causes."""
        if not self.is_alive:
            return True

        death_reason = None
        if self.hp <= 0:
            death_reason = "Поліг у героїчному бою від ран та грізних чудовиськ."
        elif self.mana < 0:
            death_reason = "Загинув від магічної віддачі, розсіявшись у магічному ефірі."
        elif self.age >= 105 and self.race not in ['High Elf', 'Вищий Ельф']:
            death_reason = "Відійшов у вічність від мирної глибокої старості, оспіваний у піснях бардів."
        elif self.age >= 180:
            death_reason = "Вознісся до Зоряного Царства після віків безсмертного життя."

        if death_reason:
            self.is_alive = False
            self.cause_of_death = death_reason
            self.score = self.calculate_score()
            self.save()
            return True

        return False

    def modify_stats(self, hp=0, mana=0, gold=0, reputation=0, strength=0, agility=0, intelligence=0, charisma=0, luck=0):
        """Safely updates stats within boundaries."""
        if not self.is_alive:
            return

        self.hp = min(self.max_hp, max(0, self.hp + hp))
        self.mana = min(self.max_mana, max(0, self.mana + mana))
        self.gold = max(0, self.gold + gold)
        self.reputation = min(100, max(-100, self.reputation + reputation))

        self.strength = max(1, self.strength + strength)
        self.agility = max(1, self.agility + agility)
        self.intelligence = max(1, self.intelligence + intelligence)
        self.charisma = max(1, self.charisma + charisma)
        self.luck = max(1, self.luck + luck)

        self.score = self.calculate_score()
        self.save()
        self.check_vitals()

    def hp_bar(self, width=10):
        if self.max_hp <= 0:
            return "[░" * width + "]"
        ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        filled = int(round(ratio * width))
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def mana_bar(self, width=10):
        if self.max_mana <= 0:
            return "[░" * width + "]"
        ratio = max(0.0, min(1.0, self.mana / self.max_mana))
        filled = int(round(ratio * width))
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def hp_percent(self):
        if self.max_hp <= 0:
            return 0
        return int(max(0, min(100, (self.hp / self.max_hp) * 100)))

    def mana_percent(self):
        if self.max_mana <= 0:
            return 0
        return int(max(0, min(100, (self.mana / self.max_mana) * 100)))

    def hero_title(self):
        if self.score > 3500:
            return "Напівбог Епохи"
        elif self.score > 2500:
            return "Легендарний Герой"
        elif self.score > 1800:
            return "Славетний Чемпіон"
        elif self.score > 1200:
            return "Досвідчений Шукач Пригод"
        elif self.score > 600:
            return "Перспективний Мандрівник"
        return "Юний Початківець"

    def race_ascii_portrait(self):
        portraits = {
            'Human': """  .---.
 / o o \\
|   ▲   |
 \\  =  /
  '---'""",
            'Людина': """  .---.
 / o o \\
|   ▲   |
 \\  =  /
  '---'""",
            'High Elf': """  /\\   /\\
 /  o o  \\
|    │    |
 \\   ~   /
  '-----'""",
            'Вищий Ельф': """  /\\   /\\
 /  o o  \\
|    │    |
 \\   ~   /
  '-----'""",
            'Mountain Dwarf': """  _____
 / # # \\
|  ===  |
{#######}
 {#####}""",
            'Гірський Дворф': """  _____
 / # # \\
|  ===  |
{#######}
 {#####}""",
            'Wild Beastkin': """ /\\___/\\
(  o o  )
 )  =  (
(  ---  )
 ""   "" """,
            'Дикий Звіролюд': """ /\\___/\\
(  o o  )
 )  =  (
(  ---  )
 ""   "" """,
            'Shadow Tiefling': """(\\_____/)
 \\ o o /
 (  ^  )
  \\ ~ /
   '-'""",
            'Тіньовий Тіфлінг': """(\\_____/)
 \\ o o /
 (  ^  )
  \\ ~ /
   '-'""",
            'Dragonborn': """ <^---^>
 / v v \\
(  ===  )
 \\  -  /
  '---'""",
            'Дракононароджений': """ <^---^>
 / v v \\
(  ===  )
 \\  -  /
  '---'"""
        }
        return portraits.get(self.race, " [ГЕРОЙ] ")

    def life_stage(self):
        if self.age < 5:
            return "Немовля (0-4 роки)"
        elif self.age < 12:
            return "Дитинство (5-11 років)"
        elif self.age < 17:
            return "Юність та учнівство (12-16 років)"
        elif self.age < 35:
            return "Молодість (17-34 роки)"
        elif self.age < 55:
            return "Зріла майстерність (35-54 роки)"
        elif self.age < 75:
            return "Ветеран-старійшина (55-74 роки)"
        return "Жива легенда (75+ років)"

    def action_label(self, key):
        if self.age < 5:
            labels = {
                'quest': '[Q] Повзати в саду',
                'meditate': '[M] Сон та чарівні сни',
                'train': '[T] Вчитися ходити та гратися',
                'tavern': '[R] Тепле молоко біля печі',
                'socialize': '[S] Лепетати й посміхатися',
                'dice': '[G] Дерев’яні кубики',
                'explore': '[E] Дослідити хату та подвір’я',
            }
        elif self.age < 12:
            labels = {
                'quest': '[Q] Лазити по деревах і ловити рибу',
                'meditate': '[M] Читати чарівні казки',
                'train': '[T] Бій на дерев’яних мечах',
                'tavern': '[R] Свіжа випічка з печі та узвар',
                'socialize': '[S] Ігри з друзями села',
                'dice': '[G] Грати в камінці',
                'explore': '[E] Дослідити таємний гай',
            }
        elif self.age < 17:
            labels = {
                'quest': '[Q] Патруль гільдії учнів',
                'meditate': '[M] Початкове вивчення магії',
                'train': '[T] Тренування зі справжньою зброєю',
                'tavern': '[R] Відпочинок у сільській корчмі',
                'socialize': '[S] Юнацькі розмови та залицяння',
                'dice': '[G] Гра в кості з однолітками',
                'explore': '[E] Вирушити в дикі землі',
            }
        else:
            labels = {
                'quest': '[Q] Підземелля та полювання',
                'meditate': '[M] Магічна медитація',
                'train': '[T] Військові тренування',
                'tavern': '[R] Відпочинок у таверні (15g)',
                'socialize': '[S] Спілкування в гільдії та бали',
                'dice': '[G] Гра в кості в корчмі',
                'explore': '[E] Дослідити незвідані землі',
            }
        raw = labels.get(key, key)
        # гаряча клавіша живе в шаблоні, а ціна — у механіці, не в тексті
        raw = re.sub(r"^\[[A-Za-z]\]\s*", "", raw)
        raw = re.sub(r"\s*\(\d+\s*g\)\s*$", "", raw, flags=re.IGNORECASE)
        return raw

    @property
    def quest_label(self):
        return self.action_label('quest')

    @property
    def meditate_label(self):
        return self.action_label('meditate')

    @property
    def train_label(self):
        return self.action_label('train')

    @property
    def tavern_label(self):
        return self.action_label('tavern')

    @property
    def socialize_label(self):
        return self.action_label('socialize')

    @property
    def dice_label(self):
        return self.action_label('dice')

    @property
    def explore_label(self):
        return self.action_label('explore')

    @property
    def hp_state(self):
        """Стан тіла словами — роман не показує 53/53."""
        if self.max_hp <= 0:
            return "—"
        ratio = self.hp / self.max_hp
        if ratio >= 0.95:
            return "повен сил"
        if ratio >= 0.75:
            return "подряпаний"
        if ratio >= 0.5:
            return "поранений"
        if ratio >= 0.25:
            return "тяжко поранений"
        if self.hp > 0:
            return "на межі"
        return "непритомний"

    @property
    def mana_state(self):
        """Стан ефіру словами."""
        if self.max_mana <= 0:
            return "не обдарований"
        ratio = self.mana / self.max_mana
        if ratio >= 0.95:
            return "повна"
        if ratio >= 0.6:
            return "спокійна"
        if ratio >= 0.3:
            return "тоншає"
        if self.mana > 0:
            return "на денці"
        return "порожня"

    def location_flavor(self):
        locations = {
            'Oakham Crossroad Village': 'Затишне перехресне селище з дерев’яними садибами, ярмарком та теплими вогнищами.',
            'Селище Окгем': 'Затишне перехресне селище з дерев’яними садибами, ярмарком та теплими вогнищами.',
            'Whispering Woods': 'Древній ліс велетенських дерев, де мешкають лісові духи та ельфійські слідопити.',
            'Шепітливий Ліс': 'Древній ліс велетенських дерев, де мешкають лісові духи та ельфійські слідопити.',
            'Ironforge Crags': 'Гірські підземні кузні дворфів, де дзвін молотів лунає крізь кам’яні склепіння.',
            'Скелі Залізокуття': 'Гірські підземні кузні дворфів, де дзвін молотів лунає крізь кам’яні склепіння.',
            'Sunspire High Capital': 'Величне білокам’яне місто лицарів, королівських турнірів та великої бібліотеки.',
            'Столиця Сонячного Шпилю': 'Величне білокам’яне місто лицарів, королівських турнірів та великої бібліотеки.',
            'Nether Shadowfell Chasm': 'Оповита туманом прірва тіней, лігво злодійських гільдій та забороненої магії.',
            'Прірва Тіньопаду': 'Оповита туманом прірва тіней, лігво злодійських гільдій та забороненої магії.',
            'Dragonspire Peaks': 'Хмарні вулканічні вершини, де сплять прадавні дракони й лежать їхні скарби.',
            'Піки Драконячого Шпилю': 'Хмарні вулканічні вершини, де сплять прадавні дракони й лежать їхні скарби.',
        }
        return locations.get(self.current_location, 'Таємничі землі, сповнені легенд та пригод.')

    @property
    def visible_traits(self):
        if isinstance(self.traits, list):
            return [t for t in self.traits if isinstance(t, str)]
        elif isinstance(self.traits, dict):
            return self.traits.get('perks', [])
        return []

    def get_story_state(self):
        default_state = {
            'act': self.story_act or 1,
            'phase': self.story_phase or 0,
            'completed_nodes': [],
            'completed_acts': [],
            'flags': self.story_flags if isinstance(self.story_flags, dict) else {},
            'mentor': self.mentor or None,
            'faction': None,
            'companion': self.companion or None,
            'alignment': self.alignment or 'Світло',
            'ending': None,
        }
        merged = default_state.copy()
        if isinstance(self.traits, list):
            for item in self.traits:
                if isinstance(item, dict) and '_story' in item:
                    merged.update(item['_story'])
                    break
        elif isinstance(self.traits, dict) and '_story' in self.traits:
            merged.update(self.traits['_story'])

        # Direct database columns take precedence
        if self.story_act:
            merged['act'] = self.story_act
        if self.story_phase is not None:
            merged['phase'] = self.story_phase
        if isinstance(self.story_flags, dict) and self.story_flags:
            if not isinstance(merged.get('flags'), dict):
                merged['flags'] = {}
            merged['flags'].update(self.story_flags)
        if self.mentor:
            merged['mentor'] = self.mentor
        if self.companion:
            merged['companion'] = self.companion
        if self.alignment:
            merged['alignment'] = self.alignment
        return merged

    def save_story_state(self, state_dict):
        self.story_act = state_dict.get('act', self.story_act)
        self.story_phase = state_dict.get('phase', self.story_phase)
        self.story_flags = state_dict.get('flags', self.story_flags)
        if state_dict.get('mentor'):
            self.mentor = state_dict.get('mentor')
        if state_dict.get('companion'):
            self.companion = state_dict.get('companion')
        if state_dict.get('alignment'):
            self.alignment = state_dict.get('alignment')
        perks = self.visible_traits
        self.traits = perks + [{'_story': state_dict}]
        self.save()

    @property
    def current_act(self):
        return self.get_story_state().get('act', 1)

    @property
    def act_title(self):
        act_titles = {
            1: "Акт I: Знамення Багряної Комети",
            2: "Акт II: Тіні Старого Лісу",
            3: "Акт III: Таємниця Ордену Хранителів",
            4: "Акт IV: Розлам Світової Печаті",
            5: "Акт V: Інтриги Сонячного Престолу",
            6: "Акт VI: Похід у Прірву Тіньопаду",
            7: "Акт VII: Битва під Чорним Сонцем",
            8: "Акт VIII: Спадок Вічності",
        }
        return act_titles.get(self.current_act, "Акт VIII: Спадок Вічності")

    def __str__(self):
        status = "Alive" if self.is_alive else "Fallen"
        return f"{self.name} the {self.race} (Age {self.age}) - {status}"


class Item(models.Model):
    ITEM_TYPES = [
        ('WEAPON', 'Weapon / Arms'),
        ('ARMOR', 'Armor / Shield'),
        ('POTION', 'Potion / Consumable'),
        ('ARTIFACT', 'Magic Artifact'),
        ('SCROLL', 'Spell Scroll'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='POTION')
    price = models.IntegerField(default=50)
    icon_symbol = models.CharField(max_length=10, default='[+]')

    hp_bonus = models.IntegerField(default=0)
    mana_bonus = models.IntegerField(default=0)
    strength_bonus = models.IntegerField(default=0)
    agility_bonus = models.IntegerField(default=0)
    intelligence_bonus = models.IntegerField(default=0)
    charisma_bonus = models.IntegerField(default=0)
    luck_bonus = models.IntegerField(default=0)

    def ascii_art(self):
        """ASCII art for this item, resolved from the shared catalog."""
        from .ascii_art import get_item_art
        return get_item_art(self.name, self.item_type)

    @property
    def type_color_class(self):
        type_classes = {
            'WEAPON': 'item-weapon',
            'ARMOR': 'item-armor',
            'POTION': 'item-potion',
            'ARTIFACT': 'item-artifact',
            'SCROLL': 'item-scroll',
        }
        return type_classes.get(self.item_type, 'item-default')

    @property
    def bonus_display(self):
        bonuses = []
        if self.hp_bonus: bonuses.append(f"+{self.hp_bonus} ЗДОР")
        if self.mana_bonus: bonuses.append(f"+{self.mana_bonus} МАНА")
        if self.strength_bonus: bonuses.append(f"+{self.strength_bonus} СИЛ")
        if self.agility_bonus: bonuses.append(f"+{self.agility_bonus} СПР")
        if self.intelligence_bonus: bonuses.append(f"+{self.intelligence_bonus} ІНТ")
        if self.charisma_bonus: bonuses.append(f"+{self.charisma_bonus} ХАР")
        if self.luck_bonus: bonuses.append(f"+{self.luck_bonus} УДАЧ")
        return ", ".join(bonuses) if bonuses else "Спорядження"

    def __str__(self):
        return f"{self.name} ({self.price}g)"


class InventoryItem(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.character.name} owns {self.quantity}x {self.item.name}"


class LogEntry(models.Model):
    LOG_TYPES = [
        ('quest', 'Quest / Battle'),
        ('event', 'World Encounter'),
        ('magic', 'Arcane Meditation'),
        ('system', 'Life Milestone'),
        ('death', 'Fallen Hero'),
    ]

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='logs')
    age = models.IntegerField()
    turn = models.IntegerField()
    title = models.CharField(max_length=150)
    text = models.TextField()
    log_type = models.CharField(max_length=20, choices=LOG_TYPES, default='event')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"[Year {self.age}] {self.title}"
