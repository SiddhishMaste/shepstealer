# SheepStealer Engine 1.0

A CPU ray tracer written in C++17. It reads a scene file and renders a PNG or PPM image.

## Build

    sudo apt install -y build-essential cmake git
    cmake -S . -B build
    cmake --build build

## Run

    ./build/sheepstealer scenes/teddy.txt teddy.png
    ./build/sheepstealer scenes/spheres.txt out.png --width 1280 --height 720 --spp 32
    ./build/sheepstealer --help

Options override the scene file: `--width --height --spp --depth --threads --seed`.
The same scene and seed always give the same image, whatever the thread count.

## Tests

    bash tests/run_tests.sh

## Scene file format

One object per line, `keyword option values...`. `#` starts a comment.
Vectors are three numbers (`center 0 1 0`). Colours are red green blue from 0 to 1.

| Line | Options |
|---|---|
| `settings` | `width height spp depth ambient seed` |
| `camera` | `eye lookat up fov aperture focus` (eye and lookat are required) |
| `background` | `color r g b`, or `top r g b bottom r g b` for a gradient |
| `material NAME TYPE` | TYPE is `matte`, `mirror` or `glass`. Options: `color specular shininess ior checker r g b scale s` |
| `sphere` | `center radius material` |
| `plane` | `point normal material` |
| `triangle` | `v0 v1 v2 material` |
| `obj` | `file scale offset material` (loads a Wavefront .obj next to the scene file) |
| `light` | `position color intensity` |

Materials must be defined before the shapes that use them.

## Files

| File | Job |
|---|---|
| `vec3.h`, `ray.h` | vector maths and rays |
| `material.h` | matte / mirror / glass settings |
| `hittable.h` | HitRecord, bounding boxes, shape base class |
| `sphere.h`, `plane.h`, `triangle.h` | ray-shape intersection |
| `bvh.h`, `hittable_list.h` | closest hit, speed-up tree |
| `camera.h` | look-at camera, field of view, depth of field |
| `tracer.h` | lighting, shadows, reflection, refraction |
| `render.h` | multi-threaded renderer, progress |
| `scene.h` | scene file reader and checks |
| `image_out.h` | gamma correction, PNG and PPM output |
| `main.cpp` | command line |

## Prompt to picture (web interface)

The `server/` folder is a small Flask app. It turns a sentence into a scene file, runs the C++ engine on it
and sends the picture back. The `web/` folder is the page.

```
python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt
.venv/bin/python server/app.py        # then open http://127.0.0.1:8000
```

* `server/builder.py` has 39 object recipes (car, tree, ice cream, house, snowman, rocket, castle, ...) built from
  the engine's shapes, and places them in a row with a floor, a background, lights and a camera.
* `server/prompt.py` reads a sentence: objects, colours (26), counts, left/right/background, day/sunset/night,
  and ground words such as grass, snow and sand. Words it does not know are reported back, not guessed.
* New engine shapes: `box`, `cylinder`, `cone` and `ellipsoid` (with `half 1` for a dome) in `scenes/shapes.txt`.
* Tests: `bash tests/run_tests.sh` (engine) and `python3 tests/test_prompt.py` (prompt reader and objects).

## Update 1.1: Halloween

- 13 new objects (ghost, jack-o'-lantern, witch hat, skull, tombstone, bat, spider, cauldron, candle, haunted house, candy corn, broomstick, moon): 52 in total.
- 8 new colours (slime, ember, plum, ink, blood, bone, frost, rust): 34 in total.
- New `spooky` look, ground words (graveyard, cemetery, swamp, mud, dirt, lava) and the scene words `graveyard` and `halloween`.
- Engine: new `torus` shape and half ellipsoids (`half 1` / `half -1`); the donut now uses a real torus. 27 engine tests.
- Website: Halloween theme (with a Classic look switch), patch notes in About, New tags in the gallery.

## Update 1.2: Block textures

- Engine: `texture` option for materials (grass, dirt, stone, sand, planks, water, lava, cloud, snow, leaves, bricks) with block size set by `scale`, and a `glow` option. Demo scene: `scenes/blocks.txt`. 32 engine tests.
- Textured ground words (lava, sand, water, snow, stone, cobblestone, dirt, planks, bricks) and a raised centre platform: "a centre cobblestone ground on lava with a house on it".
- 8 block objects (grass, stone, lava and water blocks, tree, cloud, house, sheep): 60 objects in total.
- The word `blocky` (or `pixel`) draws the ground and sky in blocks; a scene of only block objects does it automatically.

## Update 1.3: Directions

The prompt reader understands where objects stand relative to each other: right of, left of, beside / next to, above, on top of, under / below, in front of and behind. Examples: `a cat on top of a table`, `a house with a tree to its right and 3 bats above it`, `a bunny under a table`. `builder.layout()` places related objects after the row-based ones, and `compose()` widens the camera and platform to fit.
