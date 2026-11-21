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
