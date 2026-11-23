"""Tests for the prompt reader and the object recipes. Run: python3 tests/test_prompt.py"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import builder  # noqa: E402
import prompt   # noqa: E402

BIN = os.environ.get("SHEEPSTEALER_BIN", os.path.join(ROOT, "build", "sheepstealer"))
passed = failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print("  ok   - " + name)
    else:
        failed += 1
        print("  FAIL - " + name)


def keys(text):
    return [i["key"] for i in prompt.parse(text)["items"]]


print("Prompt reader")
s = prompt.parse("a blue toy car with pink trees in the background")
check("finds the car and three trees", keys("a blue toy car with pink trees in the background") == ["car", "tree", "tree", "tree"])
check("car is blue, trees are pink", s["groups"][0]["color"] == builder.COLORS["blue"] and s["groups"][1]["color"] == builder.COLORS["pink"])
check("trees go in the back row", s["groups"][1]["row"] == "back" and s["groups"][0]["row"] == "front")
s = prompt.parse("add a ice cream with yellow background")
check("ice cream with a yellow background", keys("add a ice cream with yellow background") == ["icecream"] and s["sky"] == builder.COLORS["yellow"])
check("number words and digits", keys("two red balloons") == ["balloon"] * 2 and keys("5 penguins") == ["penguin"] * 5)
check("plural without a number gives three", keys("pink trees") == ["tree"] * 3)
check("mood: night", prompt.parse("a house at night")["mood"] == "night")
check("ground: snow", prompt.parse("a snowman on snow")["floor"] is not None)
check("unknown words are reported", "dragon" in prompt.parse("a dragon and a car")["ignored"])
check("no object gives an empty list", keys("hello there") == [])
check("group word: forest", keys("a forest").count("tree") == 7)
check("more than 24 objects are cut", len(keys("12 cars and 12 trees and 12 houses")) == builder.MAX_OBJECTS)

print("Objects and scene files")
check("at least 30 objects", len(builder.OBJECTS) >= 30)
bad = []
for key in builder.OBJECTS:
    text, _ = builder.compose([dict(key=key, color=None, row="front", hint=None)], width=64, height=36, spp=1)
    with tempfile.TemporaryDirectory() as d:
        scene = os.path.join(d, "s.txt")
        open(scene, "w").write(text)
        r = subprocess.run([BIN, scene, os.path.join(d, "o.png")], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.getsize(os.path.join(d, "o.png")):
            bad.append(key)
check("every object renders (%d objects)" % len(builder.OBJECTS), not bad)
if bad:
    print("       failed:", bad)
for c in builder.COLORS:
    text, _ = builder.compose([dict(key="car", color=builder.COLORS[c], row="front", hint=None)], width=64, height=36, spp=1)
    if "material" not in text:
        bad.append(c)
check("all %d colours work" % len(builder.COLORS), not bad)

# ---- Halloween update 1.1
check("60 objects", len(builder.OBJECTS) == 60)
check("34 colours", len(builder.COLORS) == 34)
check("witch hat phrase", keys("a witch hat") == ["witchhat"])
check("haunted house phrase", keys("a haunted house") == ["hauntedhouse"])
check("jack-o'-lantern phrase", keys("a jack-o'-lantern") == ["jackolantern"])
check("spooky mood word", prompt.parse("a ghost, spooky")["mood"] == "spooky")
check("graveyard ground", prompt.parse("a skull on a graveyard")["floor_name"] == "graveyard")
check("graveyard group", "tombstone" in keys("a graveyard"))
check("gallery groups and New tags are right", all(o["new"] == (o["key"] in builder.NEW_KEYS) for o in builder.object_list()) and all(o["group"] == "Halloween" for o in builder.object_list() if o["key"] in builder.HALLOWEEN_KEYS))

# ---- Update 1.2: block textures
check("block house phrase", keys("a block house") == ["blockhouse"])
check("grass block phrase", keys("a grass block") == ["grassblock"])
check("sheep word", keys("2 sheep") == ["blocksheep", "blocksheep"])
check("blocky word", prompt.parse("a car, blocky")["blocky"] is True)
check("plain scene is not blocky", prompt.parse("a car")["blocky"] is False)
check("only block objects turn blocky on", prompt.parse("a lava block")["blocky"] is True)
check("blocky floor uses a texture", "texture grass" in builder.compose([dict(key="car", color=None, row="front", hint=None)], blocky=True)[0])
check("blocky lava ground glows", "texture lava" in builder.compose([dict(key="car", color=None, row="front", hint=None)], blocky=True, floor_tex="lava")[0])
check("normal floor has no texture", "texture" not in builder.compose([dict(key="car", color=None, row="front", hint=None)])[0])

# ---- textured ground and platforms
_u = prompt.parse("a lava ground with a sky background and a centre cobblestone ground on lava with a house on it")
check("lava ground + stone platform (user sentence)", _u["floor_tex"] == "lava" and _u["platform"] == "stone" and keys("a house") == ["house"] and [i["key"] for i in _u["items"]] == ["house"])
_s = prompt.parse("a block house on a sand island in water")
check("sand island in water", _s["floor_tex"] == "water" and _s["platform"] == "sand")
check("ground words give textured ground without blocky", prompt.parse("a car on grass")["floor_tex"] == "grass")
check("platform box is written", "box min" in builder.compose([dict(key="house", color=None, row="front", hint=None)], floor_tex="lava", platform="stone")[0])
check("platform texture in scene", "texture stone" in builder.compose([dict(key="house", color=None, row="front", hint=None)], floor_tex="lava", platform="stone")[0])

# ---- Update 1.3: directions
def rels(q):
    return [(i["key"], i["rel"]) for i in prompt.parse(q)["items"]]
def place(q):
    return {i: p for i, p in enumerate(builder.layout(prompt.parse(q)["items"]))}
check("on top of parses", rels("a cat on top of a table")[0][1] == ("ontop", 1))
check("right of parses", rels("a house with a tree to its right")[1][1] == ("rightof", 0))
check("count above parses", all(r == ("above", 3) for _, r in rels("3 bats above a house")[:3]))
check("plain scene has no relations", all(r is None for _, r in rels("a car on grass")))
_p = place("a cat on top of a table")
check("cat sits on table surface", abs(_p[0]["y"] - 1.2) < 1e-6 and abs(_p[0]["x"] - _p[1]["x"]) < 1e-6)
_p = place("a house with a tree to its right")
check("tree is right of house", _p[1]["x"] > _p[0]["x"] + _p[0]["w"] / 2)
_p = place("a tree on the left of a house")
check("tree is left of house", _p[0]["x"] < _p[1]["x"] - _p[1]["w"] / 2)
_p = place("3 bats above a house")
check("bats float above roof", all(_p[i]["y"] > 3 for i in range(3)))
_p = place("a ball in front of the house")
check("ball is in front", _p[0]["z"] > _p[1]["z"])
_p = place("a ghost behind the tombstone")
check("ghost is behind", _p[0]["z"] < _p[1]["z"])
_p = place("a bunny under a table")
check("bunny shrinks under table", _p[0]["s"] < 0.5)
check("compose with relations works", "sphere" in builder.compose(prompt.parse("a ball on top of a table")["items"])[0])

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
