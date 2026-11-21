import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
ENGINE = os.environ.get("SHEEPSTEALER_BIN", str(ROOT / "build" / "sheepstealer"))
MODELS = ROOT / "scenes" / "models"
SCENES = ROOT / "scenes"
WEB = ROOT / "web"
EXAMPLES = [("Teddy bear", "teddy.txt"), ("Mirror and glass", "spheres.txt"),
            ("Depth of field", "dof.txt"), ("Mesh model", "mesh.txt")]

MAX_SCENE_BYTES = 20000
MAX_SIDE = 960
MAX_PIXELS = 500000
MAX_SPP = 32
TIMEOUT = 60

app = Flask(__name__)


def fail(message, status):
    return jsonify({"error": message}), status


def whole(data, key, default, low, high):
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number." % key)
    if value < low or value > high:
        raise ValueError("%s must be between %d and %d." % (key, low, high))
    return value


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/api/examples")
def examples():
    found = []
    for title, name in EXAMPLES:
        file = SCENES / name
        if file.is_file():
            found.append({"name": title, "scene": file.read_text(encoding="utf-8")})
    return jsonify(found)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "engine_found": os.path.isfile(ENGINE)})


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
        width = whole(data, "width", 480, 16, MAX_SIDE)
        height = whole(data, "height", 270, 16, MAX_SIDE)
        spp = whole(data, "spp", 8, 1, MAX_SPP)
    except ValueError as problem:
        return fail(str(problem), 400)
    if width * height > MAX_PIXELS:
        return fail("The picture is too big.", 400)
    if not os.path.isfile(ENGINE):
        return fail("The render engine is not built on this server.", 500)

    work = tempfile.mkdtemp(prefix="sheepstealer_")
    try:
        Path(work, "scene.txt").write_text(scene, encoding="utf-8")
        if MODELS.is_dir():
            shutil.copytree(MODELS, Path(work, "models"))
        command = [ENGINE, "scene.txt", "out.png", "--width", str(width),
                   "--height", str(height), "--spp", str(spp)]
        try:
            done = subprocess.run(command, cwd=work, capture_output=True,
                                  text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return fail("The render took too long and was stopped.", 504)
        if done.returncode != 0:
            lines = done.stderr.strip().splitlines()
            message = lines[0] if lines else "The render failed."
            return fail(message.replace("error: ", "", 1), 400)
        png = Path(work, "out.png").read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return Response(png, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
