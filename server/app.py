"""SheepStealer web server.

  POST /api/compose  {"prompt": "a blue car"}  ->  scene text + what was understood
  POST /api/render   {"scene": "...", ...}     ->  PNG made by the C++ engine
"""
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

import builder
import prompt as reader

ROOT = Path(__file__).resolve().parent.parent
ENGINE = os.environ.get("SHEEPSTEALER_BIN", str(ROOT / "build" / "sheepstealer"))
SCENES = ROOT / "scenes"
MODELS = SCENES / "models"
WEB = ROOT / "web"

MAX_SCENE_BYTES = 200_000
MAX_PROMPT_CHARS = 300
MAX_SIDE = 960
MAX_PIXELS = 500_000
MAX_SPP = 32
TIMEOUT = int(os.environ.get("RENDER_TIMEOUT", "60"))

EXAMPLES = [("Teddy bear", "teddy.txt"), ("Mirror and glass", "spheres.txt"), ("Basic shapes", "shapes.txt"),
            ("Depth of field", "dof.txt"), ("Mesh model", "mesh.txt")]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 400_000
busy = threading.BoundedSemaphore(int(os.environ.get("MAX_JOBS", "2")))


def fail(message, status):
    return jsonify({"error": message}), status


def whole(data, key, default, low, high):
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number." % key)
    if value < low or value > high:
        raise ValueError("%s must be between %d and %d." % (key, low, high))
    return value


def picture_settings(data):
    width = whole(data, "width", 480, 16, MAX_SIDE)
    height = whole(data, "height", 270, 16, MAX_SIDE)
    spp = whole(data, "spp", 8, 1, MAX_SPP)
    if width * height > MAX_PIXELS:
        raise ValueError("The picture is too big (at most %d pixels)." % MAX_PIXELS)
    return width, height, spp


@app.errorhandler(413)
def too_large(_):
    return fail("That request is too large.", 413)


@app.after_request
def headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/img/<path:name>")
def images(name):
    return send_from_directory(WEB / "img", name, max_age=86400)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "engine_found": os.path.isfile(ENGINE), "objects": len(builder.OBJECTS)})


@app.get("/api/objects")
def objects():
    return jsonify({"objects": builder.object_list(), "colors": {k: list(v) for k, v in builder.COLORS.items()}})


@app.get("/api/examples")
def examples():
    found = []
    for title, name in EXAMPLES:
        file = SCENES / name
        if file.is_file():
            found.append({"name": title, "scene": file.read_text(encoding="utf-8")})
    return jsonify(found)


@app.post("/api/compose")
def compose():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("prompt"), str):
        return fail('Send JSON like {"prompt": "a blue car"}.', 400)
    text = data["prompt"].strip()
    if not text:
        return fail("Type what you want to see, for example: a blue car with pink trees.", 400)
    if len(text) > MAX_PROMPT_CHARS:
        return fail("That is too long (at most %d characters)." % MAX_PROMPT_CHARS, 400)
    try:
        width, height, spp = picture_settings(data)
    except ValueError as problem:
        return fail(str(problem), 400)

    spec = reader.parse(text)
    if not spec["items"]:
        names = ", ".join(o["title"].lower() for o in list(builder.OBJECTS.values())[:12])
        extra = (" I did not know: %s." % ", ".join(spec["ignored"][:6])) if spec["ignored"] else ""
        return fail("I could not find an object in that. Try one of: %s, ...%s" % (names, extra), 400)
    scene, _ = builder.compose(spec["items"], sky=spec["sky"], floor_color=spec["floor"], mood=spec["mood"],
                               width=width, height=height, spp=spp)
    return jsonify({"scene": scene, "understood": reader.describe(spec), "ignored": spec["ignored"][:8],
                    "notes": spec["notes"], "objects": len(spec["items"])})


@app.post("/api/render")
def render():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return fail('Send JSON like {"scene": "..."}.', 400)
    scene = data.get("scene")
    if not isinstance(scene, str) or not scene.strip():
        return fail("The scene is empty.", 400)
    if len(scene.encode("utf-8")) > MAX_SCENE_BYTES:
        return fail("The scene is too long.", 413)
    try:
        width, height, spp = picture_settings(data)
    except ValueError as problem:
        return fail(str(problem), 400)
    if not os.path.isfile(ENGINE):
        return fail("The render engine is not built on this server.", 500)
    if not busy.acquire(blocking=False):
        return fail("The server is busy with other renders. Try again in a few seconds.", 503)

    work = tempfile.mkdtemp(prefix="sheepstealer_")
    try:
        Path(work, "scene.txt").write_text(scene, encoding="utf-8")
        if MODELS.is_dir():
            shutil.copytree(MODELS, Path(work, "models"))
        command = [ENGINE, "scene.txt", "out.png", "--width", str(width), "--height", str(height), "--spp", str(spp)]
        started = time.monotonic()
        try:
            done = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return fail("The render took too long and was stopped. Try a smaller picture.", 504)
        seconds = time.monotonic() - started
        if done.returncode != 0:
            lines = done.stderr.strip().splitlines()
            message = lines[0] if lines else "The render failed."
            return fail(message.replace("error: ", "", 1), 400)
        png = Path(work, "out.png").read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)
        busy.release()
    return Response(png, mimetype="image/png", headers={"X-Render-Seconds": "%.2f" % seconds, "Cache-Control": "no-store"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
