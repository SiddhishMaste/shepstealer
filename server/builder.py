"""Builds SheepStealer scene files from object recipes.

Every object (car, tree, ice cream, ...) is a small recipe that puts simple shapes
together: sphere, box, cylinder, cone and ellipsoid. compose() places the objects
in a row, adds a floor, a background colour, lights and a camera, and returns the
scene file text that the C++ engine renders.
"""

# ---------------------------------------------------------------- colours
COLORS = {
    "red": (0.85, 0.12, 0.10), "orange": (1.0, 0.52, 0.10), "yellow": (1.0, 0.85, 0.15),
    "green": (0.18, 0.62, 0.25), "lime": (0.60, 0.85, 0.20), "mint": (0.60, 0.93, 0.74),
    "teal": (0.10, 0.58, 0.58), "cyan": (0.20, 0.80, 0.90), "turquoise": (0.25, 0.80, 0.75),
    "blue": (0.10, 0.30, 0.92), "navy": (0.08, 0.12, 0.42), "purple": (0.55, 0.20, 0.75),
    "violet": (0.60, 0.35, 0.85), "lavender": (0.75, 0.65, 0.95), "pink": (1.0, 0.45, 0.72),
    "magenta": (0.90, 0.15, 0.60), "maroon": (0.50, 0.08, 0.15), "brown": (0.45, 0.27, 0.13),
    "beige": (0.90, 0.80, 0.62), "peach": (1.0, 0.75, 0.60), "cream": (0.97, 0.93, 0.80),
    "white": (0.95, 0.95, 0.95), "grey": (0.55, 0.55, 0.58), "silver": (0.80, 0.82, 0.85),
    "black": (0.08, 0.08, 0.09), "gold": (0.95, 0.75, 0.20),
    # Halloween update
    "slime": (0.45, 0.95, 0.15), "ember": (1.0, 0.35, 0.05), "plum": (0.35, 0.12, 0.45),
    "ink": (0.06, 0.05, 0.16), "blood": (0.55, 0.02, 0.05), "bone": (0.93, 0.90, 0.80),
    "frost": (0.85, 0.95, 1.0), "rust": (0.65, 0.30, 0.12),
}
COLOR_ALIASES = {"gray": "grey", "golden": "gold", "rose": "pink", "violet": "violet",
                 "aqua": "cyan", "tan": "beige", "indigo": "navy", "scarlet": "red",
                 "crimson": "red", "dark": None, "light": None}


def mix(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def lighter(c, t=0.4):
    return mix(c, (1, 1, 1), t)


def darker(c, f=0.6):
    return tuple(v * f for v in c)


def num(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def vec(v):
    return " ".join(num(c) for c in v)


# ---------------------------------------------------------------- scene writer
class SceneWriter:
    def __init__(self):
        self.mats = {}
        self.mat_lines = []
        self.shape_lines = []

    def material(self, color, spec=0.25, shin=32, kind="matte", ior=None):
        c = tuple(round(max(0.0, min(1.5, v)), 2) for v in color)
        key = (c, round(spec, 2), round(shin), kind, ior)
        if key not in self.mats:
            name = "m%d" % len(self.mats)
            self.mats[key] = name
            extra = (" ior %s" % num(ior)) if ior else ""
            self.mat_lines.append("material %s %s color %s specular %s shininess %s%s"
                                  % (name, kind, vec(c), num(spec), num(shin), extra))
        return self.mats[key]

    def texture(self, name, tint=(1, 1, 1), scale=0.25, spec=0.03, shin=20, glow=0.0):
        key = ("tex", name, tuple(round(v, 2) for v in tint), round(scale, 3), round(spec, 2), glow)
        if key not in self.mats:
            mname = "m%d" % len(self.mats)
            self.mats[key] = mname
            self.mat_lines.append("material %s matte color %s texture %s scale %s specular %s shininess %s%s"
                                  % (mname, vec(tint), name, num(scale), num(spec), num(shin),
                                     (" glow %s" % num(glow)) if glow else ""))
        return self.mats[key]


class Pen:
    """Draws one object. Coordinates are local: the object stands on y = 0 and
    is moved to (ox, 0, oz) and scaled by s."""

    def __init__(self, sw, ox, oz, s, oy=0.0):
        self.sw, self.ox, self.oz, self.s, self.oy = sw, ox, oz, s, oy

    def P(self, p):
        return (self.ox + p[0] * self.s, self.oy + p[1] * self.s, self.oz + p[2] * self.s)

    def m(self, color, spec=0.25, shin=32, kind="matte", ior=None):
        return self.sw.material(color, spec, shin, kind, ior)

    def tex(self, name, tint=None, spec=0.03, glow=0.0, shin=20):
        """A pixel-block texture. The block size shrinks and grows with the object."""
        return self.sw.texture(name, tint or (1, 1, 1), 0.25 * self.s, spec, shin, glow)

    def sphere(self, c, r, mat):
        self.sw.shape_lines.append("sphere center %s radius %s material %s" % (vec(self.P(c)), num(r * self.s), mat))

    def box(self, lo, hi, mat):
        self.sw.shape_lines.append("box min %s max %s material %s" % (vec(self.P(lo)), vec(self.P(hi)), mat))

    def cyl(self, a, b, r, mat, seg=28):
        self.sw.shape_lines.append("cylinder from %s to %s radius %s segments %d material %s"
                                   % (vec(self.P(a)), vec(self.P(b)), num(r * self.s), seg, mat))

    def cone(self, a, b, r, mat, seg=28, turn=0):
        t = (" turn %s" % num(turn)) if turn else ""
        self.sw.shape_lines.append("cone from %s to %s radius %s segments %d%s material %s"
                                   % (vec(self.P(a)), vec(self.P(b)), num(r * self.s), seg, t, mat))

    def tri(self, a, b, c, mat):
        self.sw.shape_lines.append("triangle v0 %s v1 %s v2 %s material %s" % (vec(self.P(a)), vec(self.P(b)), vec(self.P(c)), mat))

    def torus(self, c, major, minor, mat, axis=(0, 1, 0), seg=36):
        self.sw.shape_lines.append("torus center %s radius %s tube %s axis %s segments %d material %s"
                                   % (vec(self.P(c)), num(major * self.s), num(minor * self.s), vec(axis), seg, mat))

    def ell(self, c, radii, mat, half=0, seg=36):
        h = (" half %d" % (1 if half is True or half == 1 else -1)) if half else ""
        self.sw.shape_lines.append("ellipsoid center %s radii %s segments %d%s material %s"
                                   % (vec(self.P(c)), vec(tuple(v * self.s for v in radii)), seg, h, mat))


# ---------------------------------------------------------------- object recipes
OBJECTS = {}


def obj(key, title, names, width, height, default):
    def wrap(fn):
        OBJECTS[key] = dict(key=key, title=title, names=names, width=width, height=height,
                            default=default, fn=fn)
        return fn
    return wrap


BLACK = (0.07, 0.07, 0.08)
WHITE = (0.95, 0.95, 0.95)
WOOD = (0.50, 0.32, 0.16)


@obj("car", "Toy car", ["car", "toycar", "automobile", "vehicle"], 3.6, 1.6, "blue")
def car(p, col):
    col = col or COLORS["blue"]
    body, cabin = p.m(col, .6, 90), p.m(lighter(col, .35), .5, 80)
    tire, hub, lamp = p.m(BLACK, .1), p.m((.85, .85, .9), .5, 60), p.m((1, .9, .4), .8, 100)
    p.box((-1.6, .35, -.8), (1.6, .95, .8), body)
    p.box((-.8, .95, -.68), (.7, 1.5, .68), cabin)
    for x in (-1.0, 1.0):
        for sg in (-1, 1):
            p.cyl((x, .38, sg * .7), (x, .38, sg * .98), .38, tire)
            p.cyl((x, .38, sg * .96), (x, .38, sg * 1.0), .2, hub)
    for z in (-.5, .5):
        p.sphere((1.6, .68, z), .14, lamp)


@obj("teddy", "Teddy bear", ["teddy", "bear", "teddybear", "plushie"], 2.8, 3.7, "brown")
def teddy(p, col):
    col = col or (.55, .34, .18)
    fur, belly, dark = p.m(col, .08, 16), p.m(lighter(col, .5), .08, 16), p.m(BLACK, .7, 80)
    p.sphere((0, 1.25, 0), 1.0, fur); p.sphere((0, 1.1, .45), .72, belly)
    p.sphere((0, 2.75, .1), .8, fur)
    for sx in (-1, 1):
        p.sphere((sx * .62, 3.4, 0), .28, fur); p.sphere((sx * .62, 3.4, .18), .17, belly)
        p.sphere((sx * .28, 2.95, .77), .09, dark)
        p.sphere((sx * 1.0, 1.5, .25), .38, fur)
        p.sphere((sx * .6, .42, .55), .45, fur); p.sphere((sx * .6, .45, .97), .2, belly)
    p.sphere((0, 2.55, .8), .33, belly); p.sphere((0, 2.72, 1.1), .11, dark)


@obj("icecream", "Ice cream", ["icecream", "icecreamcone", "cone", "gelato"], 1.7, 4.4, "pink")
def icecream(p, col):
    waffle = p.m((.85, .6, .3), .1, 16)
    p.cone((0, 1.9, 0), (0, 0, 0), .66, waffle)
    cols = [col, lighter(col, .45), darker(col, .75)] if col else [(1, .55, .7), (.98, .93, .8), (.42, .24, .14)]
    p.sphere((0, 2.3, 0), .74, p.m(cols[0], .5, 60))
    p.sphere((0, 3.0, 0), .66, p.m(cols[1], .5, 60))
    p.sphere((0, 3.62, 0), .58, p.m(cols[2], .5, 60))
    p.sphere((0, 4.15, 0), .17, p.m((.85, .08, .1), .9, 120))


@obj("tree", "Tree", ["tree", "bush"], 3.0, 3.7, "green")
def tree(p, col):
    col = col or COLORS["green"]
    trunk, leaf = p.m((.42, .26, .14), .05), p.m(col, .15, 24)
    leaf2 = p.m(lighter(col, .2), .15, 24)
    p.cyl((0, 0, 0), (0, 1.7, 0), .24, trunk)
    p.sphere((0, 2.4, 0), 1.1, leaf); p.sphere((-.75, 2.0, .2), .72, leaf2)
    p.sphere((.75, 2.05, .1), .72, leaf2); p.sphere((0, 3.05, 0), .72, leaf2)


@obj("house", "House", ["house", "home", "cottage", "hut"], 3.4, 3.4, "cream")
def house(p, col):
    col = col or COLORS["cream"]
    wall, roof = p.m(col, .1, 20), p.m((.62, .18, .14), .1, 20)
    door, win = p.m((.4, .24, .12), .1), p.m((.55, .78, .95), .8, 100)
    p.box((-1.4, 0, -1.4), (1.4, 1.6, 1.4), wall)
    p.cone((0, 1.6, 0), (0, 3.1, 0), 2.2, roof, seg=4, turn=45)
    p.box((-.38, 0, 1.4), (.38, 1.05, 1.46), door)
    p.box((-1.0, .75, 1.4), (-.55, 1.2, 1.46), win); p.box((.55, .75, 1.4), (1.0, 1.2, 1.46), win)
    p.box((.7, 2.2, -.6), (1.05, 3.3, -.25), p.m((.5, .3, .25), .1))


@obj("snowman", "Snowman", ["snowman", "snowmen"], 2.4, 4.4, "red")
def snowman(p, col):
    col = col or COLORS["red"]
    snow, dark = p.m(WHITE, .3, 40), p.m(BLACK, .5, 60)
    p.sphere((0, 1.0, 0), 1.0, snow); p.sphere((0, 2.3, 0), .75, snow); p.sphere((0, 3.35, 0), .55, snow)
    p.cone((0, 3.35, .45), (0, 3.28, 1.3), .12, p.m((1, .5, .1), .2))
    for sx in (-1, 1):
        p.sphere((sx * .2, 3.5, .46), .07, dark)
    for y in (2.0, 2.4, 2.8):
        p.sphere((0, y - .1, .72), .07, dark)
    p.cyl((0, 2.85, 0), (0, 3.0, 0), .66, p.m(col, .2, 30))
    p.cyl((0, 3.8, 0), (0, 4.35, 0), .36, dark); p.cyl((0, 3.8, 0), (0, 3.86, 0), .62, dark)


@obj("rocket", "Rocket", ["rocket", "spaceship", "missile", "spacecraft"], 2.8, 4.8, "white")
def rocket(p, col):
    col = col or (.92, .92, .95)
    body, red = p.m(col, .6, 80), p.m((.85, .12, .1), .5, 70)
    p.cyl((0, .8, 0), (0, 3.3, 0), .7, body); p.cone((0, 3.3, 0), (0, 4.7, 0), .7, red)
    p.cone((0, .8, 0), (0, .1, 0), .42, p.m((.3, .3, .33), .3))
    p.sphere((0, 2.5, .62), .3, p.m((.4, .7, .95), .9, 120))
    p.box((-.12, .5, .6), (.12, 1.7, 1.45), red); p.box((-.12, .5, -1.45), (.12, 1.7, -.6), red)
    p.box((.6, .5, -.12), (1.45, 1.7, .12), red); p.box((-1.45, .5, -.12), (-.6, 1.7, .12), red)


@obj("lollipop", "Lollipop", ["lollipop", "candy", "sweet"], 1.9, 3.7, "pink")
def lollipop(p, col):
    col = col or COLORS["pink"]
    p.cyl((0, 0, 0), (0, 2.0, 0), .07, p.m(WHITE, .3))
    p.cyl((0, 2.75, -.12), (0, 2.75, .12), .85, p.m(col, .6, 80))
    p.cyl((0, 2.75, .1), (0, 2.75, .14), .55, p.m(lighter(col, .7), .5, 60))
    p.cyl((0, 2.75, .13), (0, 2.75, .17), .27, p.m(col, .6, 80))


@obj("balloon", "Balloon", ["balloon"], 1.8, 3.7, "red")
def balloon(p, col):
    col = col or COLORS["red"]
    p.ell((0, 2.7, 0), (.85, 1.0, .85), p.m(col, .9, 120))
    p.cone((0, 1.68, 0), (0, 1.45, 0), .14, p.m(col, .5, 60))
    p.cyl((0, 1.5, 0), (0, 0, 0), .025, p.m(WHITE, .1), seg=6)


@obj("cupcake", "Cupcake", ["cupcake", "muffin", "cake_small"], 1.9, 2.8, "pink")
def cupcake(p, col):
    col = col or COLORS["pink"]
    p.cyl((0, 0, 0), (0, .95, 0), .75, p.m((.85, .65, .35), .1))
    for y, r in ((1.0, .9), (1.45, .68), (1.85, .45), (2.15, .24)):
        p.ell((0, y, 0), (r, .32, r), p.m(col, .5, 60))
    p.sphere((0, 2.45, 0), .17, p.m((.85, .08, .1), .9, 120))


@obj("mushroom", "Mushroom", ["mushroom", "toadstool"], 2.8, 2.7, "red")
def mushroom(p, col):
    col = col or COLORS["red"]
    p.cyl((0, 0, 0), (0, 1.4, 0), .45, p.m((.95, .9, .78), .1))
    p.ell((0, 1.25, 0), (1.45, 1.2, 1.45), p.m(col, .5, 60), half=True)
    dots = p.m(WHITE, .3)
    for x, y, z, r in ((0, 2.4, 0, .26), (.7, 2.05, .5, .2), (-.7, 2.0, .5, .2), (.2, 1.9, 1.05, .17), (-.45, 2.15, -.7, .18)):
        p.sphere((x, y, z), r, dots)


@obj("flower", "Flower", ["flower", "daisy", "rose", "tulip", "sunflower"], 2.2, 3.4, "pink")
def flower(p, col):
    import math
    col = col or COLORS["pink"]
    green = p.m((.2, .6, .2), .1)
    p.cyl((0, 0, 0), (0, 2.1, 0), .08, green)
    p.ell((.45, .9, 0), (.5, .15, .22), green); p.ell((-.45, 1.2, 0), (.5, .15, .22), green)
    pet = p.m(col, .3, 40)
    for k in range(8):
        a = k * math.pi / 4
        p.ell((.62 * math.cos(a), 2.5 + .62 * math.sin(a), .05), (.34, .34, .12), pet)
    p.sphere((0, 2.5, .12), .34, p.m((1, .8, .1), .3))


@obj("sun", "Sun", ["sun"], 4.4, 4.0, "yellow")
def sun(p, col):
    import math
    col = col or COLORS["yellow"]
    p.sphere((0, 2.6, 0), 1.0, p.m(col, .2, 20))
    ray = p.m(lighter(col, .1), .2)
    for k in range(12):
        a = k * math.pi / 6
        d = (math.cos(a), math.sin(a))
        p.cone((d[0] * 1.2, 2.6 + d[1] * 1.2, 0), (d[0] * 2.05, 2.6 + d[1] * 2.05, 0), .2, ray, seg=10)


@obj("cloud", "Cloud", ["cloud"], 4.0, 3.4, "white")
def cloud(p, col):
    col = col or WHITE
    c = p.m(col, .1, 16)
    for x, y, z, r in ((-.95, 2.4, 0, .7), (0, 2.8, 0, .95), (.95, 2.4, 0, .75), (-.2, 2.35, .6, .6), (.5, 2.5, .55, .55)):
        p.sphere((x, y, z), r, c)
    p.ell((0, 2.2, 0), (1.9, .5, .8), c)


@obj("castle", "Castle", ["castle", "fort", "palace"], 5.0, 4.4, "grey")
def castle(p, col):
    col = col or (.72, .72, .76)
    stone, roof, door = p.m(col, .1, 20), p.m((.75, .15, .15), .2, 30), p.m((.3, .18, .1), .1)
    p.box((-1.3, 0, -1.0), (1.3, 2.3, 1.0), stone)
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.cyl((sx * 1.7, 0, sz * 1.2), (sx * 1.7, 3.2, sz * 1.2), .55, stone)
            p.cone((sx * 1.7, 3.2, sz * 1.2), (sx * 1.7, 4.4, sz * 1.2), .72, roof)
    p.box((-.4, 0, 1.0), (.4, 1.3, 1.06), door)
    for x in (-1.1, -.55, 0, .55, 1.1):
        p.box((x - .15, 2.3, .8), (x + .15, 2.6, 1.0), stone)


@obj("lighthouse", "Lighthouse", ["lighthouse"], 2.4, 5.4, "red")
def lighthouse(p, col):
    col = col or COLORS["red"]
    white, red = p.m(WHITE, .2), p.m(col, .3, 40)
    p.cyl((0, 0, 0), (0, .3, 0), 1.2, p.m((.5, .5, .55), .1))
    for i, (a, b, r) in enumerate(((.3, 1.2, .95), (1.2, 2.1, .85), (2.1, 3.0, .76), (3.0, 3.9, .68))):
        p.cyl((0, a, 0), (0, b, 0), r, red if i % 2 == 0 else white)
    p.cyl((0, 3.9, 0), (0, 4.5, 0), .55, p.m((1, .95, .6), .8, 100))
    p.cone((0, 4.5, 0), (0, 5.3, 0), .7, red)


@obj("robot", "Robot", ["robot", "android", "bot"], 3.2, 4.6, "silver")
def robot(p, col):
    col = col or COLORS["silver"]
    metal, dark = p.m(col, .9, 120), p.m((.2, .22, .28), .3)
    eye, accent = p.m((.3, .9, 1), .5, 60), p.m((.9, .2, .2), .6, 60)
    p.box((-.9, 1.2, -.6), (.9, 3.0, .6), metal)
    p.box((-.6, 3.15, -.5), (.6, 4.0, .5), metal)
    p.sphere((-.25, 3.6, .5), .13, eye); p.sphere((.25, 3.6, .5), .13, eye)
    p.cyl((0, 4.0, 0), (0, 4.55, 0), .04, dark); p.sphere((0, 4.6, 0), .12, accent)
    p.cyl((-1.5, 2.9, 0), (-.9, 2.9, 0), .18, dark); p.cyl((.9, 2.9, 0), (1.5, 2.9, 0), .18, dark)
    p.sphere((-1.5, 2.9, 0), .28, accent); p.sphere((1.5, 2.9, 0), .28, accent)
    p.box((-.65, 0, -.3), (-.2, 1.2, .3), dark); p.box((.2, 0, -.3), (.65, 1.2, .3), dark)
    for x in (-.4, 0, .4):
        p.sphere((x, 2.4, .62), .09, accent)


@obj("table", "Table", ["table", "desk"], 3.4, 1.4, "brown")
def table(p, col):
    col = col or WOOD
    wood = p.m(col, .2, 30)
    p.box((-1.5, 1.0, -.95), (1.5, 1.2, .95), wood)
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.cyl((sx * 1.25, 0, sz * .7), (sx * 1.25, 1.0, sz * .7), .1, wood, seg=14)


@obj("chair", "Chair", ["chair", "seat", "stool"], 1.8, 2.5, "brown")
def chair(p, col):
    col = col or WOOD
    wood = p.m(col, .2, 30)
    p.box((-.6, .85, -.6), (.6, 1.0, .6), wood)
    p.box((-.6, 1.0, -.6), (.6, 2.4, -.5), wood)
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.cyl((sx * .5, 0, sz * .5), (sx * .5, .85, sz * .5), .07, wood, seg=12)


@obj("lamp", "Street lamp", ["lamp", "streetlamp", "streetlight", "lantern"], 1.4, 4.4, "yellow")
def lamp(p, col):
    col = col or (1, .9, .5)
    iron = p.m((.12, .13, .15), .4, 50)
    p.cyl((0, 0, 0), (0, .35, 0), .25, iron); p.cyl((0, 0, 0), (0, 3.6, 0), .09, iron)
    p.sphere((0, 3.95, 0), .4, p.m(col, .9, 120)); p.cone((0, 4.15, 0), (0, 4.65, 0), .52, iron)


@obj("windmill", "Windmill", ["windmill"], 3.6, 4.6, "red")
def windmill(p, col):
    col = col or COLORS["red"]
    tower, roof = p.m((.93, .88, .8), .1), p.m(col, .2, 30)
    blade, wood = p.m((.97, .97, .95), .1), p.m(WOOD, .1)
    p.cyl((0, 0, 0), (0, 2.7, 0), .9, tower)
    p.cone((0, 2.7, 0), (0, 3.7, 0), 1.05, roof)
    p.box((-.2, 0, .86), (.2, .9, .93), wood)
    # four arms with a sail on each, turning the same way
    p.box((-.07, 2.9, .95), (.07, 4.5, 1.05), wood); p.box((.07, 3.1, .97), (.6, 4.4, 1.03), blade)
    p.box((0, 2.83, .95), (1.6, 2.97, 1.05), wood);  p.box((.2, 2.3, .97), (1.5, 2.83, 1.03), blade)
    p.box((-.07, 1.3, .95), (.07, 2.9, 1.05), wood); p.box((-.6, 1.4, .97), (-.07, 2.7, 1.03), blade)
    p.box((-1.6, 2.83, .95), (0, 2.97, 1.05), wood); p.box((-1.5, 2.97, .97), (-.2, 3.5, 1.03), blade)
    p.sphere((0, 2.9, 1.0), .2, wood)


@obj("apple", "Apple", ["apple", "fruit", "cherry"], 1.9, 2.1, "red")
def apple(p, col):
    col = col or COLORS["red"]
    p.ell((0, .85, 0), (.95, .85, .95), p.m(col, .9, 120))
    p.cyl((0, 1.55, 0), (0, 1.95, 0), .05, p.m(WOOD, .1), seg=10)
    p.ell((.32, 1.8, 0), (.32, .1, .16), p.m((.2, .65, .2), .3))


@obj("cactus", "Cactus", ["cactus", "cacti"], 2.6, 3.2, "green")
def cactus(p, col):
    col = col or (.25, .6, .3)
    g = p.m(col, .1, 20)
    p.cyl((0, 0, 0), (0, 2.5, 0), .48, g); p.ell((0, 2.5, 0), (.48, .48, .48), g, half=True)
    for sx in (-1, 1):
        p.cyl((sx * .4, 1.3, 0), (sx * 1.05, 1.3, 0), .24, g)
        p.sphere((sx * 1.05, 1.3, 0), .24, g)
        p.cyl((sx * 1.05, 1.3, 0), (sx * 1.05, 2.1 if sx > 0 else 1.9, 0), .24, g)
        p.ell((sx * 1.05, 2.1 if sx > 0 else 1.9, 0), (.24, .24, .24), g, half=True)
    p.sphere((0, 3.0, .1), .18, p.m(COLORS["pink"], .3))


@obj("trafficcone", "Traffic cone", ["trafficcone", "pylon"], 1.8, 2.4, "orange")
def trafficcone(p, col):
    col = col or COLORS["orange"]
    p.box((-.85, 0, -.85), (.85, .2, .85), p.m((.12, .12, .14), .1))
    p.cone((0, .2, 0), (0, 2.3, 0), .7, p.m(col, .4, 50))
    white = p.m(WHITE, .3)
    p.cyl((0, 1.0, 0), (0, 1.07, 0), .418, white); p.cyl((0, 1.5, 0), (0, 1.57, 0), .292, white)


@obj("xmastree", "Christmas tree", ["christmastree", "xmastree", "pinetree", "pine", "fir"], 2.8, 4.7, "green")
def xmastree(p, col):
    col = col or (.1, .5, .2)
    g = p.m(col, .1, 20)
    p.cyl((0, 0, 0), (0, .9, 0), .25, p.m(WOOD, .1))
    p.cone((0, .8, 0), (0, 2.5, 0), 1.35, g); p.cone((0, 1.8, 0), (0, 3.4, 0), 1.05, g)
    p.cone((0, 2.7, 0), (0, 4.1, 0), .72, g)
    p.sphere((0, 4.2, 0), .2, p.m((1, .85, .2), .9, 120))
    for x, y, z, c in ((.6, 1.1, .95, (.9, .1, .1)), (-.7, 1.3, .8, (.2, .4, 1)), (.35, 2.2, .65, (1, .8, .2)),
                       (-.4, 2.3, .7, (.9, .1, .1)), (0, 3.1, .5, (.2, .4, 1))):
        p.sphere((x, y, z), .15, p.m(c, .9, 120))


@obj("cake", "Birthday cake", ["cake", "birthdaycake"], 3.4, 2.7, "pink")
def cake(p, col):
    col = col or COLORS["pink"]
    ic = p.m(WHITE, .3)
    p.cyl((0, 0, 0), (0, .12, 0), 1.75, p.m((.9, .9, .92), .5, 60))
    p.cyl((0, .12, 0), (0, 1.0, 0), 1.45, p.m(col, .3, 40)); p.cyl((0, 1.0, 0), (0, 1.1, 0), 1.5, ic)
    p.cyl((0, 1.1, 0), (0, 1.8, 0), 1.0, p.m(lighter(col, .4), .3, 40)); p.cyl((0, 1.8, 0), (0, 1.9, 0), 1.05, ic)
    for x, c in ((-.4, (.9, .2, .2)), (0, (.2, .5, 1)), (.4, (.95, .8, .2))):
        p.cyl((x, 1.9, 0), (x, 2.4, 0), .06, p.m(c, .4))
        p.cone((x, 2.4, 0), (x, 2.62, 0), .07, p.m((1, .8, .2), .8, 80), seg=8)


@obj("tent", "Tent", ["tent", "camp", "tipi"], 3.4, 2.4, "orange")
def tent(p, col):
    col = col or COLORS["orange"]
    p.cone((0, 0, 0), (0, 2.3, 0), 2.1, p.m(col, .2, 30), seg=4, turn=45)
    p.sw.shape_lines.append("triangle v0 %s v1 %s v2 %s material %s" % (
        vec(p.P((-.55, 0, 1.52))), vec(p.P((.55, 0, 1.52))), vec(p.P((0, 1.25, .72))), p.m((.15, .12, .1), .1)))


@obj("mailbox", "Mailbox", ["mailbox", "postbox"], 1.6, 2.7, "blue")
def mailbox(p, col):
    col = col or COLORS["blue"]
    p.cyl((0, 0, 0), (0, 1.8, 0), .1, p.m(WOOD, .1))
    p.box((-.5, 1.8, -.4), (.5, 2.45, .4), p.m(col, .6, 80))
    p.ell((0, 2.45, 0), (.5, .3, .4), p.m(col, .6, 80), half=True)
    p.box((.5, 2.05, -.05), (.62, 2.7, .05), p.m((.9, .15, .1), .4))


@obj("bench", "Bench", ["bench"], 3.4, 1.8, "brown")
def bench(p, col):
    col = col or WOOD
    wood, iron = p.m(col, .2, 30), p.m((.15, .15, .17), .3)
    p.box((-1.5, .75, -.4), (1.5, .9, .4), wood); p.box((-1.5, 1.0, -.52), (1.5, 1.7, -.42), wood)
    for sx in (-1, 1):
        p.box((sx * 1.3 - .06, 0, -.35), (sx * 1.3 + .06, .75, .35), iron)
        p.box((sx * 1.3 - .06, .9, -.5), (sx * 1.3 + .06, 1.7, -.4), iron)


@obj("fence", "Fence", ["fence", "gate"], 3.8, 1.8, "white")
def fence(p, col):
    col = col or WHITE
    w = p.m(col, .2, 30)
    p.box((-1.9, .35, -.03), (1.9, .5, .09), w); p.box((-1.9, 1.0, -.03), (1.9, 1.15, .09), w)
    for k in range(7):
        x = -1.65 + k * .55
        p.box((x - .17, 0, -.05), (x + .17, 1.4, .05), w)
        p.cone((x, 1.4, 0), (x, 1.68, 0), .24, w, seg=4, turn=45)


@obj("pumpkin", "Pumpkin", ["pumpkin"], 2.6, 2.0, "orange")
def pumpkin(p, col):
    col = col or COLORS["orange"]
    o = p.m(col, .3, 40)
    p.ell((0, .85, 0), (1.15, .85, 1.1), o); p.ell((-.55, .85, .2), (.7, .82, .85), o)
    p.ell((.55, .85, .2), (.7, .82, .85), o)
    p.cyl((0, 1.6, 0), (0, 2.0, 0), .12, p.m((.25, .5, .15), .1), seg=10)


@obj("duck", "Rubber duck", ["duck", "rubberduck", "duckling"], 2.2, 2.4, "yellow")
def duck(p, col):
    col = col or COLORS["yellow"]
    y, o = p.m(col, .7, 90), p.m((1, .5, .1), .4, 40)
    p.ell((0, .8, 0), (1.0, .75, .8), y); p.ell((-.95, 1.1, 0), (.4, .35, .3), y)
    p.sphere((.35, 1.85, 0), .6, y)
    p.ell((.95, 1.8, 0), (.35, .12, .26), o)
    p.sphere((.65, 2.0, .35), .08, p.m(BLACK, .7, 80)); p.sphere((.65, 2.0, -.35), .08, p.m(BLACK, .7, 80))


@obj("penguin", "Penguin", ["penguin"], 2.2, 3.2, "black")
def penguin(p, col):
    col = col or BLACK
    b, w, o = p.m(col, .3, 40), p.m(WHITE, .2), p.m((1, .55, .1), .3)
    p.ell((0, 1.3, 0), (.95, 1.3, .8), b); p.ell((0, 1.15, .3), (.7, 1.0, .6), w)
    p.sphere((0, 2.75, 0), .62, b)
    p.cone((0, 2.65, .5), (0, 2.58, 1.1), .16, o)
    for sx in (-1, 1):
        p.sphere((sx * .25, 2.9, .5), .09, w); p.sphere((sx * .25, 2.9, .57), .05, p.m(BLACK, .7, 80))
        p.ell((sx * 1.0, 1.5, 0), (.2, .8, .3), b)
        p.ell((sx * .4, .1, .5), (.35, .1, .5), o)


@obj("pizza", "Pizza", ["pizza"], 3.4, .6, "red")
def pizza(p, col):
    import math
    col = col or COLORS["red"]
    p.cyl((0, 0, 0), (0, .14, 0), 1.6, p.m((.85, .62, .32), .1))
    p.cyl((0, .14, 0), (0, .17, 0), 1.35, p.m(col, .3, 40))
    p.cyl((0, .17, 0), (0, .2, 0), 1.2, p.m((1, .85, .4), .3, 40))
    pep = p.m((.7, .15, .1), .3, 40)
    for k in range(7):
        a = k * 2 * math.pi / 7
        p.cyl((.7 * math.cos(a), .2, .7 * math.sin(a)), (.7 * math.cos(a), .26, .7 * math.sin(a)), .2, pep, seg=16)
    p.cyl((0, .2, 0), (0, .26, 0), .2, pep, seg=16)


@obj("donut", "Donut", ["donut", "doughnut"], 2.6, 1.0, "pink")
def donut(p, col):
    import math
    col = col or COLORS["pink"]
    p.torus((0, .45, 0), .95, .45, p.m((.85, .6, .3), .15, 20))
    p.torus((0, .56, 0), .95, .4, p.m(col, .6, 80))
    spr = [p.m(c, .3) for c in ((1, 1, 1), (.2, .5, 1), (1, .85, .2), (.3, .8, .4))]
    for k in range(10):
        a = k * 2 * math.pi / 10 + .3
        p.sphere((.95 * math.cos(a), .97, .95 * math.sin(a)), .06, spr[k % 4])


@obj("ball", "Ball", ["ball", "sphere", "marble", "globe"], 2.0, 2.0, "red")
def ball(p, col):
    col = col or COLORS["red"]
    p.sphere((0, 1.0, 0), 1.0, p.m(col, .9, 120))


@obj("igloo", "Igloo", ["igloo"], 3.6, 2.2, "white")
def igloo(p, col):
    col = col or WHITE
    s = p.m(col, .3, 40)
    p.ell((0, 0, 0), (1.8, 2.0, 1.8), s, half=True)
    p.box((-.6, 0, 1.2), (.6, .9, 2.1), s)
    p.ell((0, .9, 2.1), (.6, .35, .1), p.m((.1, .1, .15), .1))
    p.box((-.4, 0, 2.02), (.4, .8, 2.14), p.m((.08, .08, .12), .1))


@obj("bunny", "Bunny", ["bunny", "rabbit", "hare"], 2.2, 3.6, "white")
def bunny(p, col):
    col = col or WHITE
    f, pink = p.m(col, .15, 20), p.m((1, .65, .75), .2)
    p.ell((0, 1.0, 0), (.85, 1.0, .85), f); p.sphere((0, 2.35, .2), .6, f)
    for sx in (-1, 1):
        p.ell((sx * .25, 3.35, .05), (.17, .75, .13), f); p.ell((sx * .25, 3.35, .12), (.09, .6, .06), pink)
        p.sphere((sx * .27, 2.5, .72), .07, p.m(BLACK, .7, 80))
        p.sphere((sx * .45, .25, .55), .3, f)
    p.sphere((0, 2.3, .8), .1, pink); p.sphere((0, .85, -.8), .28, f)


@obj("cat", "Cat", ["cat", "kitten", "kitty"], 2.6, 3.0, "grey")
def cat(p, col):
    col = col or (.85, .55, .25)
    f, dk = p.m(col, .15, 20), p.m(BLACK, .7, 80)
    p.ell((0, 1.0, 0), (.85, 1.0, .75), f); p.sphere((0, 2.3, .1), .62, f)
    for sx in (-1, 1):
        p.cone((sx * .38, 2.62, .05), (sx * .45, 3.2, .05), .2, f, seg=12)
        p.sphere((sx * .22, 2.4, .6), .09, dk); p.sphere((sx * .45, .2, .5), .3, f)
    p.sphere((0, 2.25, .7), .08, p.m((1, .6, .65), .3))
    p.cyl((.2, .3, -.7), (.9, 1.7, -.8), .12, f, seg=14); p.sphere((.9, 1.7, -.8), .12, f)


# ---------------------------------------------------------------- Halloween update objects
@obj("ghost", "Ghost", ["ghost", "spook", "phantom"], 2.2, 3.2, "frost")
def ghost(p, col):
    import math
    col = col or (.96, .97, 1.0)
    w, dark = p.m(col, .2, 30), p.m(BLACK, .4, 50)
    p.cyl((0, .45, 0), (0, 1.7, 0), .85, w); p.ell((0, 1.7, 0), (.85, .95, .85), w, half=True)
    for k in range(7):
        a = k * 2 * math.pi / 7
        p.sphere((.62 * math.cos(a), .45, .62 * math.sin(a)), .32, w)
    p.ell((0, .45, 0), (.7, .2, .7), w)
    for sx in (-1, 1):
        p.ell((sx * .32, 1.95, .8), (.13, .22, .1), dark); p.ell((sx * 1.0, 1.35, .15), (.2, .4, .2), w)
    p.ell((0, 1.4, .84), (.14, .2, .08), dark)


@obj("jackolantern", "Jack-o'-lantern", ["jackolantern", "jacko"], 2.6, 2.1, "orange")
def jackolantern(p, col):
    col = col or COLORS["orange"]
    o = p.m(col, .3, 40)
    p.ell((0, .85, 0), (1.15, .85, 1.1), o); p.ell((-.55, .85, .2), (.7, .82, .85), o); p.ell((.55, .85, .2), (.7, .82, .85), o)
    p.cyl((0, 1.65, 0), (0, 2.1, 0), .13, p.m((.25, .5, .15), .1), seg=10)

    def sz(x, y):   # the pumpkin surface in front; the glowing face sits flat just on it
        return 1.1 * max(0.0, 1 - (x / 1.15) ** 2 - ((y - .85) / .85) ** 2) ** .5

    def flat(pts, z):
        return [(x, y, z) for x, y in pts]
    glow = p.m((1.0, .82, .2), .0, 1)
    for sx in (-1, 1):
        p.tri(*flat([(sx * .5 - .3, .95), (sx * .5 + .3, .95), (sx * .5, 1.5)], sz(sx * .5, 1.1) + .1), glow)
    p.tri(*flat([(-.16, .66), (.16, .66), (0, .92)], sz(0, .75) + .1), glow)
    xs = [-.6, -.4, -.2, 0, .2, .4, .6]
    for a_, b_ in zip(xs, xs[1:]):
        top = .6 - .1 * abs((a_ + b_) / 2) / .6
        bot = top - .3 + .12 * abs((a_ + b_) / 2) / .6
        v = flat([(a_, top), (b_, top), (b_, bot), (a_, bot)], 0)
        z = min(sz(x, y) for x, y, _ in v) + .06
        v = [(x, y, z) for x, y, _ in v]
        p.tri(v[0], v[1], v[2], glow); p.tri(v[0], v[2], v[3], glow)


@obj("witchhat", "Witch hat", ["witchhat", "witchshat", "wizardhat", "hat"], 3.2, 2.5, "black")
def witchhat(p, col):
    col = col or (.1, .07, .14)
    h, band, gold = p.m(col, .3, 40), p.m((.55, .2, .7), .3, 40), p.m((.95, .75, .2), .8, 90)
    p.cyl((0, 0, 0), (0, .14, 0), 1.55, h); p.cone((0, .14, 0), (0, 2.5, 0), .88, h)
    p.cyl((0, .14, 0), (0, .5, 0), .85, band)
    p.box((-.22, .17, .8), (.22, .47, .9), gold)
    p.cone((0, 2.2, 0), (.5, 2.55, 0), .14, h, seg=14)


@obj("skull", "Skull", ["skull", "skeleton"], 2.2, 2.4, "bone")
def skull(p, col):
    col = col or COLORS["bone"]
    b, dark, tooth = p.m(col, .15, 20), p.m((.05, .04, .05), .1), p.m(lighter(col, .3), .2, 30)
    p.ell((0, 1.4, 0), (1.0, .95, .95), b); p.ell((0, .6, .12), (.62, .5, .62), b)
    for sx in (-1, 1):
        p.ell((sx * .38, 1.4, .82), (.28, .34, .25), dark)
    p.ell((0, 1.0, .9), (.1, .17, .1), dark)
    for k in range(5):
        p.box((-.4 + k * .2 - .07, .22, .62), (-.4 + k * .2 + .07, .5, .72), tooth)


@obj("tombstone", "Tombstone", ["tombstone", "gravestone", "headstone", "grave"], 2.8, 2.6, "grey")
def tombstone(p, col):
    col = col or (.55, .56, .6)
    s, dark, dirt = p.m(col, .1, 16), p.m(darker(col, .45), .1), p.m((.22, .15, .1), .05)
    p.box((-.95, 0, -.3), (.95, 1.5, .3), s); p.cyl((0, 1.5, -.3), (0, 1.5, .3), .95, s)
    p.box((-.09, .6, .3), (.09, 1.75, .34), dark); p.box((-.42, 1.2, .3), (.42, 1.36, .34), dark)
    p.ell((0, 0, 1.0), (1.2, .32, .75), dirt, half=True)


@obj("bat", "Bat", ["bat"], 4.0, 3.2, "black")
def bat(p, col):
    col = col or (.1, .08, .12)
    b, red = p.m(col, .3, 40), p.m((1, .15, .1), .6, 60)
    p.ell((0, 1.5, 0), (.38, .5, .32), b); p.sphere((0, 2.05, 0), .27, b)
    for sx in (-1, 1):
        p.cone((sx * .15, 2.25, 0), (sx * .22, 2.7, 0), .1, b, seg=10); p.sphere((sx * .1, 2.1, .22), .045, red)
        pts = [(.3, 1.8), (1.9, 2.4), (1.55, 1.7), (1.1, 1.8), (.7, 1.45), (.3, 1.2)]
        for i in range(len(pts) - 1):
            p.tri((sx * pts[i][0], pts[i][1], 0), (sx * pts[i + 1][0], pts[i + 1][1], 0), (sx * .25, 1.8, 0), b)


@obj("spider", "Spider", ["spider"], 4.0, 1.9, "black")
def spider(p, col):
    col = col or BLACK
    b, red = p.m(col, .5, 70), p.m((.9, .1, .1), .6, 60)
    p.sphere((0, .95, -.1), .55, b); p.sphere((0, .95, .6), .33, b)
    for sx in (-.1, .1):
        p.sphere((sx, 1.05, .87), .07, red); p.sphere((sx * 2.4, 1.0, .86), .06, red)
    for sx in (-1, 1):
        for zo in (-.55, -.2, .15, .5):
            p.cyl((sx * .4, .95, zo * .5), (sx * 1.3, 1.6, zo * 1.3), .05, b, seg=8)
            p.cyl((sx * 1.3, 1.6, zo * 1.3), (sx * 1.9, 0.02, zo * 1.7), .05, b, seg=8)


@obj("cauldron", "Cauldron", ["cauldron"], 3.2, 2.5, "black")
def cauldron(p, col):
    col = col or (.1, .1, .12)
    iron, brew, flame = p.m(col, .5, 60), p.m((.35, .95, .2), .8, 90), p.m((1, .55, .1), .2, 20)
    p.ell((0, 1.5, 0), (1.3, 1.2, 1.3), iron, half=-1)
    p.torus((0, 1.5, 0), 1.3, .13, iron)
    p.cyl((0, 1.5, 0), (0, 1.56, 0), 1.25, brew)
    for x, y, z, r in ((.4, 1.75, .2, .22), (-.5, 1.7, -.2, .17), (.1, 1.8, -.5, .14)):
        p.sphere((x, y, z), r, brew)
    for sx in (-1, 1):
        p.torus((sx * 1.35, 1.1, 0), .2, .05, iron, axis=(1, 0, 0), seg=16)
        p.sphere((sx * .7, .1, .5), .22, iron)
    p.sphere((0, .1, -.8), .22, iron)
    for k in (-.5, 0, .5):
        p.cone((k, .01, 1.45), (k, .6, 1.45), .15, flame, seg=10)


@obj("candle", "Candle", ["candle"], 1.8, 2.4, "bone")
def candle(p, col):
    col = col or (.95, .9, .78)
    wax, gold = p.m(col, .2, 30), p.m((.95, .75, .2), .8, 90)
    p.cyl((0, 0, 0), (0, .12, 0), .85, gold); p.cyl((0, .12, 0), (0, 1.6, 0), .45, wax)
    for a, h in ((.3, .4), (-.35, .6), (.05, .3)):
        p.ell((a, 1.55, .4 if a else .44), (.1, h * .5, .08), wax)
    p.cyl((0, 1.6, 0), (0, 1.8, 0), .03, p.m(BLACK, .1))
    p.sphere((0, 1.95, 0), .15, p.m((1, .85, .3), .1, 10)); p.cone((0, 1.9, 0), (0, 2.4, 0), .15, p.m((1, .55, .1), .1, 10), seg=14)


@obj("hauntedhouse", "Haunted house", ["hauntedhouse", "mansion"], 5.4, 5.2, "plum")
def hauntedhouse(p, col):
    col = col or (.28, .2, .34)
    wall, roof, glow, door = p.m(col, .1, 20), p.m((.1, .08, .12), .2, 30), p.m((1, .8, .2), .0, 1), p.m((.1, .06, .05), .1)
    p.box((-1.5, 0, -1.2), (1.5, 2.4, 1.2), wall); p.cone((0, 2.4, 0), (0, 4.0, 0), 2.4, roof, seg=4, turn=45)
    p.cyl((-1.9, 0, .2), (-1.9, 3.5, .2), .75, wall); p.cone((-1.9, 3.5, .2), (-1.9, 5.1, .2), 1.0, roof)
    p.box((-.4, 0, 1.2), (.4, 1.3, 1.26), door)
    for x in (-1.0, .75):
        p.box((x, 1.3, 1.2), (x + .4, 2.0, 1.26), glow)
    p.box((1.0, 2.7, -.3), (1.35, 3.8, .05), wall)
    p.sphere((-1.9, 2.4, .92), .22, glow)


@obj("candycorn", "Candy corn", ["candycorn"], 2.2, 2.4, "yellow")
def candycorn(p, col):
    col = col or COLORS["yellow"]
    p.cone((0, 0, 0), (0, 2.3, 0), 1.1, p.m(col, .3, 40), seg=3, turn=90)
    p.cone((0, .85, 0), (0, 2.32, 0), .70 + .02, p.m((1, .5, .05), .3, 40), seg=3, turn=90)
    p.cone((0, 1.6, 0), (0, 2.34, 0), .33 + .03, p.m((.97, .97, .95), .3, 40), seg=3, turn=90)


@obj("broomstick", "Broomstick", ["broomstick", "broom"], 1.8, 4.0, "brown")
def broomstick(p, col):
    col = col or WOOD
    p.cyl((0, .9, 0), (0, 3.9, 0), .07, p.m(col, .2, 30), seg=10)
    p.cone((0, 0, 0), (0, 1.4, 0), .75, p.m((.8, .6, .25), .1, 16), seg=20)
    p.cyl((0, .95, 0), (0, 1.12, 0), .24, p.m((.25, .15, .1), .1))
    p.sphere((0, 3.95, 0), .1, p.m(col, .2, 30))


@obj("moon", "Moon", ["moon"], 3.4, 4.6, "cream")
def moon(p, col):
    col = col or (.98, .95, .75)
    m, crater = p.m(col, .1, 16), p.m(darker(col, .82), .1, 16)
    p.sphere((0, 3.2, 0), 1.6, m)
    for x, y, r in ((-.5, 3.6, .3), (.6, 2.8, .4), (.2, 3.9, .2), (-.8, 2.7, .25)):
        p.ell((x, y, 1.5), (r, r, r * .25), crater)


# ---------------------------------------------------------------- Update 1.2: block objects
@obj("grassblock", "Grass block", ["grassblock"], 2.4, 2.1, None)
def grassblock(p, col):
    p.box((-1, 0, -1), (1, 2, 1), p.tex("dirt", col))
    p.box((-1.02, 1.72, -1.02), (1.02, 2.0, 1.02), p.tex("grass", col))


@obj("stoneblock", "Stone block", ["stoneblock"], 2.4, 2.1, None)
def stoneblock(p, col):
    p.box((-1, 0, -1), (1, 2, 1), p.tex("stone", col))


@obj("lavablock", "Lava block", ["lavablock"], 2.4, 2.1, None)
def lavablock(p, col):
    p.box((-1, 0, -1), (1, 2, 1), p.tex("lava", col, spec=0.0, glow=0.45))


@obj("waterblock", "Water block", ["waterblock"], 2.4, 2.1, None)
def waterblock(p, col):
    p.box((-1, 0, -1), (1, 2, 1), p.tex("water", col, spec=0.5, shin=80))


@obj("blocktree", "Block tree", ["blocktree", "pixeltree"], 2.6, 4.1, None)
def blocktree(p, col):
    p.box((-.3, 0, -.3), (.3, 2.3, .3), p.tex("planks", (.75, .6, .45)))
    leaves = p.tex("leaves", col)
    p.box((-1.2, 2.0, -1.2), (1.2, 3.2, 1.2), leaves)
    p.box((-.75, 3.2, -.75), (.75, 3.9, .75), leaves)


@obj("blockcloud", "Block cloud", ["blockcloud", "pixelcloud"], 4.0, 4.2, None)
def blockcloud(p, col):
    c = p.tex("cloud", col, spec=0.0, glow=0.25)
    p.box((-1.8, 2.6, -.9), (1.8, 3.3, .9), c)
    p.box((-1.0, 3.3, -.7), (.9, 3.9, .7), c)
    p.box((.9, 3.3, -.5), (1.6, 3.7, .5), c)


@obj("blockhouse", "Block house", ["blockhouse", "pixelhouse"], 4.6, 3.8, None)
def blockhouse(p, col):
    p.box((-1.8, 0, -1.4), (1.8, 2.0, 1.4), p.tex("planks", col))
    roof = p.tex("bricks", col)
    p.box((-2.0, 2.0, -1.6), (2.0, 2.4, 1.6), roof)
    p.box((-1.5, 2.4, -1.2), (1.5, 2.8, 1.2), roof)
    p.box((-1.0, 2.8, -.8), (1.0, 3.2, .8), roof)
    p.box((-.35, 0, 1.4), (.35, 1.3, 1.46), p.m((.3, .18, .08), .02, 10))
    glass = p.m((.6, .85, 1.0), .5, 60)
    for x in (-1.4, .8):
        p.box((x, 1.0, 1.4), (x + .6, 1.6, 1.46), glass)


@obj("blocksheep", "Block sheep", ["blocksheep", "sheep", "pixelsheep"], 2.4, 2.2, None)
def blocksheep(p, col):
    wool = p.tex("cloud", col or (1.0, 1.0, 1.0), spec=0.0)
    skin = p.m((.8, .68, .58), .02, 10)
    dark = p.m((.12, .1, .1), .02, 10)
    p.box((-.6, .7, -1.0), (.6, 1.7, .9), wool)
    p.box((-.35, 1.15, .9), (.35, 1.9, 1.5), skin)
    for x in (-.2, .2):
        p.box((x - .06, 1.5, 1.5), (x + .06, 1.65, 1.53), dark)
    for x in (-.45, .2):
        for z in (-.8, .55):
            p.box((x, 0, z), (x + .25, .7, z + .25), skin)


HALLOWEEN_KEYS = ["ghost", "jackolantern", "witchhat", "skull", "tombstone", "bat", "spider", "cauldron",
            "candle", "hauntedhouse", "candycorn", "broomstick", "moon"]
NEW_KEYS = ["grassblock", "stoneblock", "lavablock", "waterblock", "blocktree", "blockcloud", "blockhouse", "blocksheep"]
BLOCK_KEYS = set(NEW_KEYS)
TEX_FLOORS = {"grass": "grass", "lawn": "grass", "field": "grass", "meadow": "grass", "swamp": "grass",
              "snow": "snow", "snowy": "snow", "winter": "snow", "sand": "sand", "beach": "sand", "desert": "sand",
              "road": "stone", "street": "stone", "stone": "stone", "water": "water", "sea": "water",
              "ocean": "water", "lake": "water", "graveyard": "dirt", "cemetery": "dirt", "mud": "dirt",
              "dirt": "dirt", "lava": "lava"}
BLOCKY_SKY = dict(top=(0.47, 0.66, 1.0), bottom=(0.78, 0.88, 1.0), floor=(0.4, 0.7, 0.3), check=(0.35, 0.62, 0.26))

UI_GROUPS = {
    "Blocks": NEW_KEYS,
    "Halloween": HALLOWEEN_KEYS,
    "Animals": ["teddy", "bunny", "cat", "duck", "penguin"],
    "Food": ["icecream", "cupcake", "cake", "pizza", "donut", "apple", "lollipop"],
    "Buildings": ["house", "castle", "lighthouse", "windmill", "igloo", "tent"],
    "Nature": ["tree", "xmastree", "flower", "mushroom", "cactus", "sun", "cloud", "pumpkin"],
    "Toys and fun": ["car", "rocket", "robot", "balloon", "ball", "snowman"],
    "Street and home": ["table", "chair", "bench", "fence", "lamp", "mailbox", "trafficcone"],
}


def object_list():
    group_of = {k: g for g, keys in UI_GROUPS.items() for k in keys}
    order = list(UI_GROUPS)
    rows = [dict(key=o["key"], title=o["title"], default=o["default"], new=o["key"] in NEW_KEYS,
                 group=group_of.get(o["key"], "Toys and fun")) for o in OBJECTS.values()]
    rows.sort(key=lambda r: order.index(r["group"]))      # Halloween first, the rest keep their order
    return rows


# ---------------------------------------------------------------- composing a scene
DAY = dict(top=(0.42, 0.64, 0.95), bottom=(0.95, 0.97, 1.0), floor=(0.84, 0.87, 0.9), check=(0.77, 0.80, 0.85))
SUNSET = dict(top=(0.30, 0.22, 0.58), bottom=(1.0, 0.62, 0.36), floor=(0.62, 0.45, 0.42), check=(0.55, 0.40, 0.38))
SPOOKY = dict(top=(0.10, 0.03, 0.22), bottom=(0.96, 0.42, 0.08), floor=(0.22, 0.15, 0.30), check=(0.16, 0.10, 0.24))
NIGHT = dict(top=(0.01, 0.02, 0.10), bottom=(0.10, 0.13, 0.32), floor=(0.13, 0.15, 0.22), check=(0.10, 0.12, 0.18))

MAX_OBJECTS = 24
GAP = 0.7


def sky_from_color(c):
    return dict(top=mix(c, (0, 0, 0), 0.08), bottom=mix(c, (1, 1, 1), 0.5),
                floor=mix(c, (1, 1, 1), 0.62), check=mix(c, (1, 1, 1), 0.48))


SURFACE = {"table": 1.2, "chair": 1.0, "bench": 0.9}     # height of the top surface when it is not the object's full height
CLEARANCE = {"table": 1.0, "bench": 0.75}                 # room underneath, so something small fits "under" it


def layout(items):
    """items: list of dict(key, color, row, hint, rel). rel = (kind, index of the anchor object).
    Returns placed objects: x, z, y (lift), s (scale), w (width)."""
    rank = {"left": 0, None: 1, "center": 1, "right": 2}
    placed = {}
    free = [i for i, it in enumerate(items) if not it.get("rel") or it["rel"][1] >= len(items)]
    for row, z in (("front", 0.0), ("back", -5.0)):
        row_idx = [i for i in free if items[i]["row"] == row]
        row_idx.sort(key=lambda i: rank.get(items[i]["hint"], 1))
        if not row_idx:
            continue
        widths = [OBJECTS[items[i]["key"]]["width"] for i in row_idx]
        total = sum(widths) + GAP * (len(widths) - 1)
        scale = min(1.0, 24.0 / total)
        total *= scale
        x = -total / 2
        for i, w in zip(row_idx, widths):
            w *= scale
            placed[i] = dict(items[i], x=x + w / 2, z=z, y=0.0, s=scale, w=w)
            x += w + GAP * scale

    todo = [i for i in range(len(items)) if i not in placed]
    for _ in range(len(items) + 1):                  # anchors first, then the objects that depend on them
        groups = {}
        for i in todo:
            kind, a = items[i]["rel"]
            if a in placed:
                groups.setdefault((a, kind), []).append(i)
        if not groups:
            break
        for (a, kind), members in groups.items():
            anc = placed[a]
            akey = anc["key"]
            s = anc["s"]
            ah = OBJECTS[akey]["height"] * s
            top = SURFACE.get(akey, OBJECTS[akey]["height"]) * s
            ws = [OBJECTS[items[m]["key"]]["width"] * s for m in members]
            gap = GAP * s
            if kind == "under" and akey not in CLEARANCE:
                kind = "infront"
            if kind in ("rightof", "leftof", "beside"):
                right = anc["x"] + anc["w"] / 2 + gap
                left = anc["x"] - anc["w"] / 2 - gap
                for n_, (m, w) in enumerate(zip(members, ws)):
                    go_right = kind == "rightof" or (kind == "beside" and n_ % 2 == 0)
                    if go_right:
                        x = right + w / 2; right += w + gap
                    else:
                        x = left - w / 2; left -= w + gap
                    placed[m] = dict(items[m], x=x, z=anc["z"], y=anc["y"], s=s, w=w)
            elif kind in ("infront", "behind"):
                total = sum(ws) + gap * (len(ws) - 1)
                x = anc["x"] - total / 2
                depth = max(ws + [anc["w"]]) * 0.45
                zoff = anc["w"] * 0.3 + depth + 0.8 * s
                z = anc["z"] + (zoff if kind == "infront" else -zoff)
                for m, w in zip(members, ws):
                    placed[m] = dict(items[m], x=x + w / 2, z=z, y=anc["y"], s=s, w=w)
                    x += w + gap
            else:                                     # above, on top of, under
                total = sum(ws) + gap * (len(ws) - 1)
                if kind == "ontop" and total > anc["w"] * 1.1 and len(ws) > 1:
                    total = max(anc["w"] * 0.9, sum(ws) * 0.6)     # let them overlap a little instead of hanging off
                x = anc["x"] - total / 2
                step = (total - ws[0]) / max(1, len(ws) - 1) if len(ws) > 1 else 0
                for n_, (m, w) in enumerate(zip(members, ws)):
                    cx = anc["x"] if len(ws) == 1 else x + ws[0] / 2 + n_ * step
                    ms = s
                    if kind == "above":
                        y = anc["y"] + ah + 0.9 * s
                    elif kind == "ontop":
                        y = anc["y"] + top
                    else:
                        y = anc["y"]
                        ms = s * min(1.0, 0.85 * CLEARANCE[akey] / OBJECTS[items[m]["key"]]["height"])
                    placed[m] = dict(items[m], x=cx, z=anc["z"], y=y, s=ms, w=w * ms / s)
            todo = [i for i in todo if i not in placed]
    for i in todo:                                    # anything left over (a loop) goes in the front row
        placed[i] = dict(items[i], x=0.0, z=0.0, y=0.0, s=1.0, w=OBJECTS[items[i]["key"]]["width"])
    return [placed[i] for i in range(len(items))]


def compose(items, sky=None, floor_color=None, mood="day", width=640, height=360, spp=16, blocky=False, floor_name=None,
            floor_tex=None, platform=None):
    """Returns (scene_text, placed_objects)."""
    items = items[:MAX_OBJECTS]
    sw = SceneWriter()
    placed = layout(items)
    PLATFORM_H = 0.6 if platform else 0.0       # a raised patch of ground under the objects
    for pl in placed:
        pen = Pen(sw, pl["x"], pl["z"], pl["s"], PLATFORM_H + pl["y"])
        OBJECTS[pl["key"]]["fn"](pen, pl["color"])

    base = {"day": DAY, "sunset": SUNSET, "night": NIGHT, "spooky": SPOOKY}.get(mood, DAY)
    look = sky_from_color(sky) if sky else (BLOCKY_SKY if (blocky or floor_tex or platform) and mood == "day" else base)
    floor_mat = None
    ymax = max([OBJECTS[p["key"]]["height"] * p["s"] + p["y"] for p in placed] or [3.0])
    xmin = min([p["x"] - p["w"] / 2 for p in placed] or [-2])
    xmax = max([p["x"] + p["w"] / 2 for p in placed] or [2])
    has_back = any(p["z"] < 0 for p in placed)
    zmin = min([p["z"] for p in placed] or [0.0])
    zmax = max([p["z"] for p in placed] or [0.0])
    cx, span = (xmin + xmax) / 2, xmax - xmin + 2.0
    dist = max(6.8, span * 0.86, ymax * 1.9)
    eye = (cx + dist * 0.12, ymax * 0.5 + 1.6, dist + max(0.0, zmax))
    look_at = (cx, ymax * 0.42 + PLATFORM_H, -1.5 if has_back else 0.0)

    night, sunset, spooky = mood == "night", mood == "sunset", mood == "spooky"
    ambient = 0.09 if night else (0.13 if spooky else (0.17 if sunset else 0.22))
    key_col = (0.55, 0.6, 1.0) if night else ((1.0, 0.62, 0.28) if spooky else ((1.0, 0.72, 0.5) if sunset else (1.0, 1.0, 1.0)))
    key_int = 0.55 if night else (0.9 if spooky else 1.0)

    lines = ["# Generated by the SheepStealer prompt reader.",
             "settings width %d height %d spp %d depth 5 ambient %s seed 7" % (width, height, spp, num(ambient)),
             "camera eye %s lookat %s up 0 1 0 fov 38" % (vec(eye), vec(look_at)),
             "background top %s bottom %s" % (vec(look["top"]), vec(look["bottom"])), ""]
    tex_floor = None
    if floor_tex:
        tex_floor = floor_tex
    elif blocky and not floor_color:
        tex_floor = "grass"
    if tex_floor:
        floor_def = "material floor matte color 0.88 0.88 0.88 texture %s scale 0.4 specular %s shininess 60%s" % (
            tex_floor, "0.4" if tex_floor == "water" else "0.02", " glow 0.4" if tex_floor == "lava" else "")
    elif floor_color:
        floor_def = "material floor matte color %s specular 0.05 shininess 20" % vec(floor_color)
    else:
        floor_def = "material floor matte color %s checker %s scale 1.4 specular 0.05 shininess 20" % (
            vec(look["floor"]), vec(look["check"]))
    if platform:
        pm = sw.texture(platform, (0.95, 0.95, 0.95), 0.25, 0.03, 30)
        lines_platform = ["box min %s max %s material %s" % (
            vec((xmin - 1.8, -0.02, zmin - 2.2)), vec((xmax + 1.8, PLATFORM_H, zmax + 2.2)), pm)]
    else:
        lines_platform = []
    lines += sw.mat_lines + [floor_def, "", "plane point 0 0 0 normal 0 1 0 material floor", ""]
    lines += lines_platform + sw.shape_lines + [""]
    lines += ["light position %s intensity %s color %s" % (vec((cx - 6, 9 + ymax, dist * 0.9)), num(key_int), vec(key_col)),
              "light position %s intensity %s color %s" % (vec((cx + 9, 5, dist * 0.6)), "0.55" if spooky else "0.4",
                                                       vec((0.55, 0.4, 1.0) if spooky else mix(key_col, (1, 1, 1), .4)))]
    return "\n".join(lines) + "\n", placed
