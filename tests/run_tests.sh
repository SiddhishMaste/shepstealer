#!/bin/bash
# Black-box tests for SheepStealer. Run from the project folder:  bash tests/run_tests.sh
BIN=./build/sheepstealer
TMP=$(mktemp -d)
pass=0; fail=0

ok()   { echo "  ok   - $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL - $1"; fail=$((fail+1)); }

# expect_error NAME "text the message must contain" scene-file-contents
expect_error() {
    printf '%b' "$3" > "$TMP/s.txt"
    msg=$($BIN "$TMP/s.txt" "$TMP/o.png" --width 8 --height 8 --spp 1 2>&1 >/dev/null); code=$?
    if [ $code -ne 0 ] && echo "$msg" | grep -q "$2"; then ok "$1"; else bad "$1 (exit $code: $msg)"; fi
}

echo "Error handling"
expect_error "negative radius is named"       "radius must be greater than 0"  'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\nsphere center 0 0 0 radius -1 material m\n'
expect_error "line number is reported"        ":3:"                            'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\nsphere center 0 0 0 radius -1 material m\n'
expect_error "up parallel to view rejected"   "parallel"                       'camera eye 0 0 5 lookat 0 5 5 up 0 1 0\n'
expect_error "fov 180 rejected"               "fov must be"                    'camera eye 0 0 5 lookat 0 0 0 fov 180\n'
expect_error "unknown material"               "unknown material"               'camera eye 0 0 5 lookat 0 0 0\nsphere center 0 0 0 radius 1 material x\n'
expect_error "glass ior 0 rejected"           "ior must be greater"            'camera eye 0 0 5 lookat 0 0 0\nmaterial m glass ior 0\n'
expect_error "missing camera"                 "no 'camera'"                    'material m matte\n'
expect_error "missing number values"          "needs 3 number"                 'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\nsphere center 0 0 radius 1 material m\n'
expect_error "obj path traversal blocked"     "without '..'"                   'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\nobj file ../x.obj material m\n'
expect_error "unknown keyword"                "unknown keyword"                'camera eye 0 0 5 lookat 0 0 0\nteapot size 3\n'
expect_error "box with bad corners rejected"  "greater than the matching" 'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\nbox min 1 1 1 max 0 2 2 material m\n'
expect_error "cone radius must be positive"   "radius must be greater than 0" 'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\ncone from 0 0 0 to 0 1 0 radius 0 material m\n'
expect_error "cylinder segments limited"      "segments must be between"  'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\ncylinder from 0 0 0 to 0 1 0 radius 1 segments 2 material m\n'
expect_error "ellipsoid radius must be positive" "every radius must be greater" 'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\nellipsoid center 0 0 0 radii 1 0 1 material m\n'
expect_error "torus radius must be positive"  "radius and tube must be greater" 'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\ntorus center 0 0 0 radius 0 tube 1 material m\n'
expect_error "torus axis must not be zero"    "axis must not be"          'camera eye 0 0 5 lookat 0 0 0\nmaterial m matte\ntorus center 0 0 0 radius 1 tube 0.3 axis 0 0 0 material m\n'

echo "Limits and output"
$BIN scenes/spheres.txt "$TMP/o.png" --width 5000 >/dev/null 2>&1 && bad "width limit" || ok "width limit enforced"
$BIN scenes/spheres.txt "$TMP/o.png" --depth 99   >/dev/null 2>&1 && bad "depth limit" || ok "depth limit enforced"
$BIN scenes/spheres.txt /no/such/dir/o.png        >/dev/null 2>&1 && bad "bad output dir" || ok "unwritable output reported"
$BIN scenes/spheres.txt "$TMP/o.jpg"              >/dev/null 2>&1 && bad "bad format" || ok "unknown format rejected"
$BIN --help >/dev/null 2>&1 && ok "--help exits 0" || bad "--help"

echo "Rendering"
$BIN scenes/teddy.txt "$TMP/t.png" --width 64 --height 64 --spp 2 >/dev/null 2>&1 && [ -s "$TMP/t.png" ] && ok "PNG written" || bad "PNG written"
$BIN scenes/teddy.txt "$TMP/t.ppm" --width 64 --height 64 --spp 2 >/dev/null 2>&1 && head -c 2 "$TMP/t.ppm" | grep -q P6 && ok "PPM written (P6)" || bad "PPM written"
$BIN scenes/mesh.txt  "$TMP/m.png" --width 64 --height 36 --spp 1 >/dev/null 2>&1 && ok "mesh + obj renders" || bad "mesh + obj renders"
$BIN scenes/spheres.txt "$TMP/a.ppm" --width 96 --height 54 --spp 4 --threads 1 >/dev/null 2>&1
$BIN scenes/spheres.txt "$TMP/b.ppm" --width 96 --height 54 --spp 4 --threads 5 >/dev/null 2>&1
cmp -s "$TMP/a.ppm" "$TMP/b.ppm" && ok "same image with 1 and 5 threads" || bad "same image with 1 and 5 threads"
$BIN scenes/spheres.txt "$TMP/c.ppm" --width 96 --height 54 --spp 4 --threads 2 --seed 5 >/dev/null 2>&1
$BIN scenes/spheres.txt "$TMP/d.ppm" --width 96 --height 54 --spp 4 --threads 2 --seed 5 >/dev/null 2>&1
cmp -s "$TMP/c.ppm" "$TMP/d.ppm" && ok "same seed gives identical image" || bad "same seed gives identical image"
$BIN scenes/shapes.txt "$TMP/s.png" --width 64 --height 36 --spp 1 >/dev/null 2>&1 && [ -s "$TMP/s.png" ] && ok "box, cylinder and cone render" || bad "box, cylinder and cone render"

rm -rf "$TMP"
echo; echo "$pass passed, $fail failed"
[ $fail -eq 0 ]
