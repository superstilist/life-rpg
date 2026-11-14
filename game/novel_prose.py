"""
game/novel_prose.py
Етерія: Хроніки Життя — шар прози.

Мета: відчуватися як роман, а не як гра.
- Вибір подається як думка оповідача, а не пункт меню.
- Числові «хвости» (ОЗ +20, СИЛ +2) прибираються з тексту.
- Механіка лишається незмінною — змінюється тільки те, як вона читається.
"""

import hashlib
import random
import re

# --------------------------------------------------------------------------
# 1. Числа та ігрові позначки → прибрати з прози
# --------------------------------------------------------------------------

_STAT_TOKEN_RE = re.compile(
    r"(?:"
    r"ОЗ|Мана|МАНА|mana|Золото|Репутація|Репутац|СИЛ|Сила|"
    r"СПР|Спритність|ІНТ|Інтелект|ХАР|Харизма|УДАЧ|Удача|"
    r"Реп|Зол|[+-]\s*\d+|\d+\s*[gG]"
    r")"
)

_REQUIREMENT_PATTERNS = [
    re.compile(r"\s*\(\s*Потрібно[^)]*\)", re.IGNORECASE),
    re.compile(r"\s*\(\s*\d+\s*(?:мани|mana|золотих|gold)[^)]*\)", re.IGNORECASE),
    re.compile(r"\s*\(\s*\d+\s*[gG]\s*\)"),
]


def _strip_requirements(text: str) -> str:
    """Прибирає технічні умови на кшталт «(Потрібно 20 мани)»."""
    out = text or ""
    for pat in _REQUIREMENT_PATTERNS:
        out = pat.sub("", out)
    return out.strip()


def strip_stat_tail(text: str) -> str:
    """
    Прибирає кінцеві дужки з числами/характеристиками,
    щоб результат читався як речення роману.
    """
    out = (text or "").strip()
    while True:
        m = re.search(r"\(([^()]*)\)\s*$", out)
        if not m:
            break
        inner = m.group(1)
        if _STAT_TOKEN_RE.search(inner) or re.search(r"\d", inner):
            out = out[: m.start()].rstrip(" ,.;:—-")
        else:
            break

    # технічні позначки в квадратних дужках
    out = re.sub(r"\[[^\]]*\]", "", out)
    # подвійні пробіли
    out = re.sub(r"\s{2,}", " ", out)
    # висячі розділові знаки
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    return out.strip()


def prose_outcome(text: str) -> str:
    """Текст результату вибору — без чисел."""
    return strip_stat_tail(text)


# --------------------------------------------------------------------------
# 2. Вибір → думка оповідача
# --------------------------------------------------------------------------

# Рамки, що природно поєднуються з інфінітивом («випустити спалах»).
_INF_FRAMES = [
    "Я міг би {act}.",
    "Я хотів би {act}.",
    "Може, {act}?",
    "А якщо {act}?",
    "Я наважуюся {act}.",
    "Мабуть, варто {act}.",
    "Час {act}.",
    "Я вирішую: {act}.",
    "Серце підказує: {act}.",
    "Щось у мені шепоче: {act}.",
    "Мене вабить {act}.",
]

# Рамки, що поєднуються з іменниковою фразою («шлях Заліза»).
_NOUN_FRAMES = [
    "Я обираю: {act}.",
    "Серце підказує: {act}.",
    "Може, {act}?",
    "А якщо {act}?",
    "Мене вабить {act}.",
    "Хай буде так: {act}.",
    "Ось моя стежка: {act}.",
    "Шлях один — {act}.",
]

_INFINITIVE_ENDINGS = ("тися", "ться", "ти", "ть", "йся")

_PRICE_TAIL_RE = re.compile(
    r"\s*(?:—|-|,)?\s*(?:за\s+)?\b\d+\s*"
    r"(?:золот\w*|гріш\w*|срібн\w*|монет\w*|мани|мана|g|gold)\b\.?\s*$",
    re.IGNORECASE,
)

_LEADING_LABEL_RE = re.compile(r"^\s*кінцівка\s+[IVXХІі\d]+\s*:\s*", re.IGNORECASE)

_NUM_ONES = ["", "один", "два", "три", "чотири", "п'ять", "шість", "сім", "вісім", "дев'ять"]
_NUM_TEENS = [
    "десять", "одинадцять", "дванадцять", "тринадцять", "чотирнадцять",
    "п'ятнадцять", "шістнадцять", "сімнадцять", "вісімнадцять", "дев'ятнадцять",
]
_NUM_TENS = [
    "", "", "двадцять", "тридцять", "сорок", "п'ятдесят",
    "шістдесят", "сімдесят", "вісімдесят", "дев'яносто",
]
_NUM_HUNDREDS = [
    "", "сто", "двісті", "триста", "чотириста", "п'ятсот",
    "шістсот", "сімсот", "вісімсот", "дев'ятсот",
]


def _num_uk(n: int) -> str:
    """Число словами — гроші в романі не пишуть цифрами."""
    if n <= 0:
        return "нуль"
    if n >= 1000:
        return str(n)
    parts = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        parts.append(_NUM_HUNDREDS[hundreds])
    if 10 <= rest < 20:
        parts.append(_NUM_TEENS[rest - 10])
    else:
        tens, ones = divmod(rest, 10)
        if tens:
            parts.append(_NUM_TENS[tens])
        if ones:
            parts.append(_NUM_ONES[ones])
    return " ".join(parts)


_MONEY_RE = re.compile(r"\b(\d{1,3})\s+(золотих|золота|золотими|золотий|гріш\w*|срібн\w*|монет\w*)\b")


def _money_to_words(act: str) -> str:
    def repl(m):
        words = _num_uk(int(m.group(1)))
        unit = m.group(2)
        if unit == "золотими":  # «відкупитися 35 золотими» → «… за тридцять п'ять золотих»
            return f"за {words} золотих"
        return f"{words} {unit}"

    return _MONEY_RE.sub(repl, act)


def _decapitalize(act: str) -> str:
    """«З апетитом…» → «з апетитом…», але «ОЗ» не чіпаємо."""
    if not act:
        return act
    head = act.split(" ", 1)[0]
    if act[0].isupper() and not (len(head) > 1 and head.isupper()):
        return act[0].lower() + act[1:]
    return act


def _normalize_act(act: str) -> str:
    act = _LEADING_LABEL_RE.sub("", act)
    act = _blurb_to_clause(act)
    act = _PRICE_TAIL_RE.sub("", act).rstrip(" ,.;:—-")
    act = _money_to_words(act)
    # внутрішня двокрапка читається краще як тире
    if ":" in act:
        head, _, tail = act.partition(":")
        act = f"{head.rstrip()} — {tail.strip()}"
    return _decapitalize(act).strip()


def _looks_infinitive(act: str) -> bool:
    """«випустити спалах», «затамувати подих» — так, «шлях Заліза» — ні."""
    head = re.split(r"[:,—]", act, maxsplit=1)[0]
    for word in head.split()[:4]:
        token = re.sub(r"[^а-яіїєґ'’]", "", word.lower())
        if len(token) > 4 and token.endswith(_INFINITIVE_ENDINGS):
            return True
    return False


def _blurb_to_clause(act: str) -> str:
    """«Шлях Заліза: стати учнем (Важка броня та меч)» → «… — важка броня та меч»."""
    m = re.search(r"\(([^()]+)\)\s*$", act)
    if not m:
        return act
    inner = m.group(1).strip().rstrip(" .;,")
    if not inner:
        return act[: m.start()].rstrip(" ,;:—-")
    if inner[0].isupper() and len(inner) > 1 and inner[1].islower():
        inner = inner[0].lower() + inner[1:]
    head = act[: m.start()].rstrip(" ,;:—-")
    return f"{head} — {inner}"


def prose_choice(text: str) -> str:
    """
    Перетворює пункт вибору на речення від першої особи.
    Стабільний для того самого тексту (без мерехтіння при перезавантаженні).
    """
    act = _strip_requirements(text or "").strip().rstrip(" .!?…")
    if not act:
        return ""
    act = _normalize_act(act)
    if not act:
        return ""

    frames = _INF_FRAMES if _looks_infinitive(act) else _NOUN_FRAMES
    idx = int(hashlib.md5(act.encode("utf-8")).hexdigest(), 16) % len(frames)
    return frames[idx].format(act=act)


# --------------------------------------------------------------------------
# 3. Збагачення структур перед рендером
# --------------------------------------------------------------------------


def enrich_choice(choice: dict) -> dict:
    c = dict(choice)
    c["prose"] = prose_choice(c.get("text", ""))
    return c


def enrich_choices(choices) -> list:
    return [enrich_choice(c) for c in (choices or [])]


def enrich_event(event):
    if not event:
        return event
    e = dict(event)
    e["choices"] = enrich_choices(e.get("choices"))
    e["description"] = strip_stat_tail(e.get("description", ""))
    return e


def enrich_interludes(options) -> list:
    enriched = []
    for opt in options or []:
        o = dict(opt)
        o["prose"] = _interlude_prose(o)
        enriched.append(o)
    return enriched


def _interlude_prose(opt: dict) -> str:
    """Рік життя як рядок роману, а не як кнопка."""
    by_type = {
        "training": "Рік у спарингах, мозолях і втомі — тіло міцнішає.",
        "arcane_study": "Рік над сувоями, у напівсні й шепоті ефіру.",
        "travel": "Рік у дорозі — чужий вітер, чужі зорі, нові стежки.",
        "fellowship": "Рік між людьми — вогнища, клятви, теплі слова.",
    }
    return by_type.get(opt.get("type", ""), opt.get("description", ""))


# --------------------------------------------------------------------------
# 4. Прозаїчні зачини сцен — «випадкова стежка»
# --------------------------------------------------------------------------

_SCENE_OPENERS = {
    "infancy": [
        "Світ був великий і теплий, і кожен звук приходив здалеку.",
        "Десь за стіною дихала ніч, а в кімнаті пахло молоком і димом.",
        "Дні пливли повільно, мов мед із ложки.",
    ],
    "childhood": [
        "Дорога кликала за тин, і я йшов, не питаючи дозволу.",
        "Дорослі казали не ходити туди. Я йшов.",
        "Той день почався як усі — і не закінчився як усі.",
    ],
    "adult": [
        "Дорога не питала, чи я готовий.",
        "Я думав, що вже бачив усе. Етерія посміхалася.",
        "Попереду лежала стежка, якої не було на жодній мапі.",
        "Вітер ніс запах диму й чогось давно забутого.",
    ],
}


def scene_opener(age: int) -> str:
    band = "infancy" if age < 5 else "childhood" if age < 12 else "adult"
    return random.choice(_SCENE_OPENERS[band])


# --------------------------------------------------------------------------
# 5. Постійні зв'язки між главами (щоб шлях читався як книга)
# --------------------------------------------------------------------------

_CHAPTER_BRIDGES = [
    "Минав час. Попіл осідав, а життя йшло далі.",
    "Роки не питали дозволу. Вони просто минали.",
    "І знову дорога. І знову вибір.",
    "Десь у глибині щось пам'ятало кожен мій крок.",
    "Світ не ставав добрішим. Я теж.",
]


def chapter_bridge() -> str:
    return random.choice(_CHAPTER_BRIDGES)
