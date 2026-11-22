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

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
