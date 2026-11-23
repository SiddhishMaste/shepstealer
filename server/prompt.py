"""Reads a short sentence ("a blue car and 3 pink trees on a yellow background")
and turns it into a list of objects, colours, a background and a mood."""
import re

from builder import COLORS, COLOR_ALIASES, OBJECTS, MAX_OBJECTS, BLOCK_KEYS, TEX_FLOORS

# Phrases that mean one thing; they are joined into one word before reading.
PHRASES = [
    ("ice cream cone", "icecream"), ("ice-cream", "icecream"), ("ice cream", "icecream"),
    ("teddy bear", "teddy"), ("toy car", "car"), ("race car", "car"), ("sports car", "car"),
    ("christmas tree", "xmastree"), ("xmas tree", "xmastree"), ("pine tree", "xmastree"),
    ("fir tree", "xmastree"), ("street lamp", "lamp"), ("street light", "lamp"),
    ("traffic cone", "trafficcone"), ("rubber duck", "duck"), ("birthday cake", "cake"),
    ("snow man", "snowman"), ("light house", "lighthouse"), ("wind mill", "windmill"),
    ("space ship", "rocket"), ("space shuttle", "rocket"), ("post box", "mailbox"),
    ("letter box", "mailbox"), ("rose gold", "gold"), ("sky blue", "cyan"),
    ("light blue", "cyan"), ("dark blue", "navy"), ("light green", "mint"), ("dark green", "green"),
    ("hot pink", "magenta"), ("in front of", "front"), ("at the back", "behind"),
    ("grass block", "grassblock"), ("stone block", "stoneblock"), ("lava block", "lavablock"),
    ("water block", "waterblock"), ("block tree", "blocktree"), ("pixel tree", "blocktree"),
    ("block cloud", "blockcloud"), ("pixel cloud", "blockcloud"), ("block house", "blockhouse"),
    ("pixel house", "blockhouse"), ("block sheep", "blocksheep"), ("pixel sheep", "blocksheep"),
    ("witch hat", "witchhat"), ("witch's hat", "witchhat"), ("witches hat", "witchhat"),
    ("haunted house", "hauntedhouse"), ("haunted mansion", "hauntedhouse"), ("candy corn", "candycorn"),
    ("jack-o-lantern", "jackolantern"), ("jack-o'-lantern", "jackolantern"), ("jack o lantern", "jackolantern"),
    ("jack o'lantern", "jackolantern"), ("jackolantern", "jackolantern"), ("pumpkin lantern", "jackolantern"),
    ("broom stick", "broomstick"), ("full moon", "moon"), ("grave stone", "tombstone"), ("head stone", "tombstone"),
    ("in the back", "behind"), ("in back", "behind"), ("far away", "behind"),
]

NUMBERS = {"a": 1, "an": 1, "one": 1, "single": 1, "two": 2, "couple": 2, "pair": 2, "three": 3,
           "few": 3, "four": 4, "several": 4, "five": 5, "bunch": 5, "six": 6, "many": 6, "lots": 6,
           "seven": 7, "eight": 8, "nine": 9, "ten": 10, "dozen": 12}

STOP = set("""add a an the with and on in of at to some make draw create render show me picture image scene
please i want generate put place next by near beside nice beautiful cute big small little tiny large
tall short toy plus also there is are it its my for from that this these those over under up down
colored coloured color colour shiny new old pretty lovely simple just like whose has have having
background backdrop sky wall bg ground floor carpet surface behind front left right center centre middle
where who which be then where very really look looks looking can you could would should so as into
out onto upon along around""".split())

BLOCKY_WORDS = {"blocky", "pixel", "pixelated", "voxel", "minecraft", "pixelart"}
GROUND_TEX = {"lava": "lava", "water": "water", "grass": "grass", "dirt": "dirt", "stone": "stone", "cobblestone": "stone",
              "cobble": "stone", "sand": "sand", "snow": "snow", "planks": "planks", "wood": "planks",
              "bricks": "bricks", "brick": "bricks"}
GROUND_NOUNS = {"ground", "floor", "platform", "island", "base", "pad", "patch"}
PLATFORM_NOUNS = {"platform", "island", "pad", "patch", "base"}
BG_WORDS = {"background", "backdrop", "sky", "wall", "bg"}
FLOOR_WORDS = {"ground", "floor", "carpet", "surface"}
POS_LEFT, POS_RIGHT, POS_CENTER = {"left"}, {"right"}, {"center", "centre", "middle"}
POS_BACK = {"behind", "back", "rear"}
MOODS = {"sunset": "sunset", "sunrise": "sunset", "dusk": "sunset", "evening": "sunset",
         "night": "night", "midnight": "night", "nighttime": "night", "moonlit": "night",
         "day": "day", "daytime": "day", "sunny": "day",
         "spooky": "spooky", "halloween": "spooky", "creepy": "spooky", "scary": "spooky", "haunted": "spooky",
         "eerie": "spooky"}
FLOORS = {"grass": (0.36, 0.68, 0.28), "lawn": (0.36, 0.68, 0.28), "field": (0.40, 0.70, 0.30),
          "meadow": (0.42, 0.72, 0.32), "garden": None, "snow": (0.96, 0.97, 1.0), "snowy": (0.96, 0.97, 1.0),
          "winter": (0.96, 0.97, 1.0), "sand": (0.93, 0.82, 0.55), "beach": (0.93, 0.82, 0.55),
          "desert": (0.93, 0.78, 0.5), "road": (0.28, 0.28, 0.31), "street": (0.28, 0.28, 0.31),
          "water": (0.15, 0.45, 0.78), "sea": (0.15, 0.45, 0.78), "ocean": (0.15, 0.45, 0.78),
          "lake": (0.15, 0.45, 0.78),
          "graveyard": (0.20, 0.24, 0.17), "cemetery": (0.20, 0.24, 0.17), "swamp": (0.20, 0.38, 0.15),
          "mud": (0.30, 0.20, 0.12), "stone": (0.5, 0.5, 0.52), "dirt": (0.36, 0.25, 0.15), "lava": (0.95, 0.30, 0.05)}

# Words that stand for a whole group of objects.
GROUPS = {
    "forest": [("tree", 7, "back")], "woods": [("tree", 6, "back")], "orchard": [("tree", 5, "back"), ("apple", 3, "front")],
    "village": [("house", 3, "front"), ("tree", 2, "back")], "town": [("house", 3, "front"), ("lamp", 2, "back")],
    "garden": [("flower", 4, "front"), ("tree", 1, "back")], "party": [("cake", 1, "front"), ("balloon", 3, "back")],
    "christmas": [("xmastree", 1, "front"), ("snowman", 1, "front")], "camping": [("tent", 1, "front"), ("tree", 3, "back")],
    "playground": [("ball", 2, "front"), ("bench", 1, "front")], "farm": [("windmill", 1, "back"), ("fence", 2, "front")],
    "winterland": [("snowman", 2, "front"), ("igloo", 1, "back")], "kitchen": [("table", 1, "front"), ("chair", 2, "front")],
    "graveyard": [("tombstone", 3, "front"), ("ghost", 1, "back"), ("bat", 2, "back")],
    "cemetery": [("tombstone", 3, "front"), ("ghost", 1, "back"), ("bat", 2, "back")],
    "halloween": [("jackolantern", 2, "front"), ("ghost", 1, "back"), ("bat", 2, "back")],
}

OBJECT_WORDS = {}
for _key, _o in OBJECTS.items():
    for _name in set(_o["names"] + [_key]):
        OBJECT_WORDS[_name] = _key
OBJECT_WORDS.update({"cone": "trafficcone", "cones": "trafficcone", "roses": "flower", "cacti": "cactus",
                     "men": "snowman", "snowmen": "snowman", "mice": None})


def singular(word):
    """Returns the base form of a word that may be plural."""
    if word in OBJECT_WORDS or word in COLORS:
        return word
    for cand in (word[:-1] if word.endswith("s") else None,
                 word[:-2] if word.endswith("es") else None,
                 word[:-3] + "y" if word.endswith("ies") else None):
        if cand and (cand in OBJECT_WORDS or cand in GROUPS):
            return cand
    return word


def colour_of(word):
    word = COLOR_ALIASES.get(word, word)
    return word if word in COLORS else None


def tokenize(text):
    text = text.lower()
    for a, b in PHRASES:
        text = re.sub(r"\b" + re.escape(a) + r"(s?)\b", lambda m, b=b: b + m.group(1), text)
    text = re.sub(r"[,;.]", " , ", text)
    text = re.sub(r"[^a-z0-9, ]", " ", text)
    return text.split()


def parse(text):
    tokens = tokenize(text)
    n = len(tokens)
    used = [False] * n            # tokens already understood
    sky = floor = None
    sky_name = floor_name = None
    mood = "day"
    mood_given = False
    blocky = False
    for i, w in enumerate(tokens):
        if w in BLOCKY_WORDS:
            blocky = True; used[i] = True
    ignored = []
    notes = []

    kinds = []
    for i, w in enumerate(tokens):
        base = singular(w)
        if base in OBJECT_WORDS and OBJECT_WORDS[base]:
            kinds.append("obj")
        elif colour_of(w):
            kinds.append("col")
        else:
            kinds.append("other")

    def nearest_colour(i, step, skip):
        """Finds a colour next to position i, skipping filler words."""
        j = i + step
        while 0 <= j < n and tokens[j] in skip:
            j += step
        if 0 <= j < n and kinds[j] == "col" and not used[j]:
            return j
        return None

    # 0. textured ground: "lava ground", "a centre cobblestone ground", "a stone island"
    floor_tex = platform = None
    specs = []
    for i, w in enumerate(tokens):
        if w in GROUND_TEX and i + 1 < n and tokens[i + 1] in GROUND_NOUNS:
            near = range(max(0, i - 3), i)
            is_plat = tokens[i + 1] in PLATFORM_NOUNS or any(tokens[k] in POS_CENTER for k in near)
            for k in near:
                if tokens[k] in POS_CENTER:
                    used[k] = True
            used[i] = used[i + 1] = True
            specs.append((GROUND_TEX[w], is_plat))
    for tex_name, is_plat in specs:
        if is_plat and platform is None:
            platform = tex_name
        elif not is_plat and floor_tex is None:
            floor_tex = tex_name
        else:
            notes.append("Only one ground and one platform are drawn.")
    if floor_tex:
        floor_name = floor_tex
        floor = FLOORS.get(floor_tex) or (0.5, 0.5, 0.5)

    # 1. background and floor colours ("yellow background", "on green grass")
    for i, w in enumerate(tokens):
        if w in BG_WORDS or w in FLOOR_WORDS:
            j = nearest_colour(i, -1, {"colored", "coloured", "color", "colour"})
            if j is None:
                j = nearest_colour(i, 1, {"of", "is", "in", "as", "color", "colour", "colored", "coloured"})
            if j is not None:
                if w in BG_WORDS:
                    sky, sky_name = COLORS[colour_of(tokens[j])], colour_of(tokens[j])
                else:
                    floor, floor_name = COLORS[colour_of(tokens[j])], colour_of(tokens[j])
                used[j] = used[i] = True
    # 2. mood and ground words ("sunset", "snow", "grass")
    for i, w in enumerate(tokens):
        if w in MOODS:
            mood, mood_given, used[i] = MOODS[w], True, True
        elif w in FLOORS and not used[i] and not (singular(w) in OBJECT_WORDS):
            if FLOORS[w] is not None and floor is None:
                floor, floor_name = FLOORS[w], w
                if TEX_FLOORS.get(w):
                    floor_tex = TEX_FLOORS[w]
            used[i] = True

    # 3. objects with colour, count and position
    items = []
    obj_positions = [i for i in range(n) if kinds[i] == "obj"]
    for idx, i in enumerate(obj_positions):
        base = singular(tokens[i])
        key = OBJECT_WORDS[base]
        plural = tokens[i] != base
        used[i] = True

        # colour: the closest colour before the object, over filler words only
        color = None
        j = i - 1
        while j >= 0 and kinds[j] != "obj" and tokens[j] not in (",", "and", "with", "on"):
            if kinds[j] == "col" and not used[j]:
                color = COLORS[colour_of(tokens[j])]
                used[j] = True
                break
            j -= 1
        # count: a number just before the object (or before its colour)
        count = 1
        j = i - 1
        steps = 0
        while j >= 0 and steps < 4 and kinds[j] != "obj" and tokens[j] != ",":
            w = tokens[j]
            if w.isdigit():
                count, used[j] = max(1, min(int(w), 12)), True
                break
            if w in NUMBERS and not (w in ("a", "an") and plural):
                count, used[j] = NUMBERS[w], True
                break
            j -= 1
            steps += 1
        else:
            pass
        if count == 1 and plural:
            count = 3
        # position words after the object, up to the next object / comma / "and"
        end = obj_positions[idx + 1] if idx + 1 < len(obj_positions) else n
        row, hint = "front", None
        k = i + 1
        while k < end and tokens[k] not in (",", "and"):
            w = tokens[k]
            if w in POS_BACK or (w in BG_WORDS and not used[k]):
                row = "back"; used[k] = True
            elif w == "front":
                row = "front"; used[k] = True
            elif w in POS_LEFT:
                hint = "left"; used[k] = True
            elif w in POS_RIGHT:
                hint = "right"; used[k] = True
            elif w in POS_CENTER:
                hint = "center"; used[k] = True
            k += 1
        # "background trees": the word just before the object
        if i > 0 and tokens[i - 1] in ("background", "behind", "back"):
            row = "back"
        items.append(dict(key=key, color=color, count=count, row=row, hint=hint))

    # group words (forest, village, party ...) when no plain objects were named
    for i, w in enumerate(tokens):
        if w in GROUPS or singular(w) in GROUPS:
            if kinds[i] == "obj":
                continue
            g = GROUPS.get(w) or GROUPS[singular(w)]
            used[i] = True
            color = None
            j = nearest_colour(i, -1, set())
            if j is not None:
                color = COLORS[colour_of(tokens[j])]; used[j] = True
            for key, cnt, row in g:
                if not any(it["key"] == key and it["row"] == row for it in items):
                    items.append(dict(key=key, color=color if key in ("tree", "house", "flower") else None,
                                      count=cnt, row=row, hint=None))
    # 4. words we did not understand
    for i, w in enumerate(tokens):
        if used[i] or w in STOP or w in NUMBERS or w.isdigit() or w == ",":
            continue
        if kinds[i] == "col":
            continue
        ignored.append(w)

    if items and all(it["key"] in BLOCK_KEYS for it in items):
        blocky = True          # only block objects: draw the whole world in blocks
    flat = []
    for it in items:
        for _ in range(it["count"]):
            flat.append(dict(key=it["key"], color=it["color"], row=it["row"], hint=it["hint"]))
    if len(flat) > MAX_OBJECTS:
        notes.append("Only the first %d objects are drawn." % MAX_OBJECTS)
        flat = flat[:MAX_OBJECTS]
    return dict(items=flat, groups=items, sky=sky, sky_name=sky_name, floor=floor, floor_name=floor_name, mood=mood, blocky=blocky, floor_tex=floor_tex, platform=platform, ignored=ignored, notes=notes)


def color_name(c):
    if c is None:
        return None
    for name, v in COLORS.items():
        if v == c:
            return name
    return "custom"


def describe(spec):
    """A short sentence of what was understood, for the page."""
    parts = []
    for it in spec["groups"]:
        title = OBJECTS[it["key"]]["title"].lower()
        c = color_name(it["color"])
        name = ((c + " ") if c else "") + title
        bit = ("%d x %s" % (it["count"], name)) if it["count"] > 1 else name
        if it["row"] == "back":
            bit += " (background)"
        if it["hint"]:
            bit += " (%s)" % it["hint"]
        parts.append(bit)
    out = ", ".join(parts)
    extra = []
    if spec["sky"]:
        extra.append("%s background" % spec["sky_name"])
    if spec["floor"]:
        extra.append("%s ground" % spec["floor_name"])
    if spec.get("platform"):
        extra.append("%s platform in the centre" % spec["platform"])
    if spec["mood"] != "day":
        extra.append(spec["mood"])
    if spec.get("blocky"):
        extra.append("blocky look")
    return out + ((" | " + ", ".join(extra)) if extra else "")
