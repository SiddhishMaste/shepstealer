#pragma once
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <initializer_list>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "hittable_list.h"
#include "plane.h"
#include "sphere.h"
#include "triangle.h"

// Hard limits so bad input cannot use unbounded memory or time (REQ-SAFE-02).
namespace Limits {
    const int    maxDim = 2048;
    const long   maxPixels = 2000000;
    const int    maxSpp = 64;
    const int    maxDepth = 16;
    const int    maxThreads = 256;
    const size_t maxLights = 16;
    const size_t maxMaterials = 256;
    const size_t maxPrimitives = 500000;
}

struct Light {
    Vec3 position;
    Vec3 color;
};

struct Settings {
    int width = 480, height = 270;
    int spp = 4;               // samples per pixel
    int maxDepth = 5;          // recursion limit
    double ambient = 0.12;
    unsigned seed = 1;
};

struct CameraSpec {
    bool present = false;
    Vec3 eye, lookAt, up = Vec3(0, 1, 0);
    double fov = 45, aperture = 0, focus = -1;   // focus < 0 means "distance to lookAt"
};

struct Scene {
    Settings settings;
    CameraSpec cam;
    Vec3 bgTop = Vec3(0.5, 0.7, 1.0), bgBottom = Vec3(1, 1, 1);
    HittableList world;
    std::vector<Light> lights;
};

class SceneError : public std::runtime_error {
public:
    explicit SceneError(const std::string& m) : std::runtime_error(m) {}
};

// Checks render settings. Used for scene files and for command-line overrides.
inline void validateSettings(const Settings& s, const std::string& where) {
    auto bad = [&](const std::string& msg) { throw SceneError(where + ": " + msg); };
    if (s.width < 1 || s.width > Limits::maxDim)
        bad("width must be between 1 and " + std::to_string(Limits::maxDim) + " (got " + std::to_string(s.width) + ")");
    if (s.height < 1 || s.height > Limits::maxDim)
        bad("height must be between 1 and " + std::to_string(Limits::maxDim) + " (got " + std::to_string(s.height) + ")");
    if (long(s.width) * s.height > Limits::maxPixels)
        bad("width x height must not exceed " + std::to_string(Limits::maxPixels) + " pixels");
    if (s.spp < 1 || s.spp > Limits::maxSpp)
        bad("spp must be between 1 and " + std::to_string(Limits::maxSpp) + " (got " + std::to_string(s.spp) + ")");
    if (s.maxDepth < 0 || s.maxDepth > Limits::maxDepth)
        bad("depth must be between 0 and " + std::to_string(Limits::maxDepth) + " (got " + std::to_string(s.maxDepth) + ")");
    if (s.ambient < 0 || s.ambient > 1)
        bad("ambient must be between 0 and 1");
}

// ---------------------------------------------------------------------------
// Scene file format: one object per line, "keyword option values ...".
// Lines may have '#' comments. See scenes/*.txt for examples.
// ---------------------------------------------------------------------------

// The options of one line, e.g. "center 0 1 0 radius 2" -> {center:[0,1,0], radius:[2]}
class Args {
public:
    std::string where;                                   // "file.txt:12", for error messages
    std::map<std::string, std::vector<std::string>> kv;

    explicit Args(const std::string& where) : where(where) {}

    [[noreturn]] void fail(const std::string& msg) const { throw SceneError(where + ": " + msg); }
    void need(bool ok, const std::string& msg) const { if (!ok) fail(msg); }
    bool has(const std::string& k) const { return kv.count(k) > 0; }

    double number(const std::string& key, const std::string& s) const {
        char* end = nullptr;
        double v = std::strtod(s.c_str(), &end);
        if (s.empty() || *end != '\0' || !std::isfinite(v))
            fail("'" + key + "' expects a number, got '" + s + "'");
        return v;
    }
    double num(const std::string& k, double def) const {
        auto it = kv.find(k);
        return it == kv.end() ? def : number(k, it->second[0]);
    }
    double req(const std::string& k) const {
        if (!has(k)) fail("missing required option '" + k + "'");
        return number(k, kv.at(k)[0]);
    }
    Vec3 vec(const std::string& k, const Vec3& def) const {
        auto it = kv.find(k);
        if (it == kv.end()) return def;
        return Vec3(number(k, it->second[0]), number(k, it->second[1]), number(k, it->second[2]));
    }
    Vec3 reqVec(const std::string& k) const {
        if (!has(k)) fail("missing required option '" + k + "'");
        return vec(k, Vec3());
    }
    std::string str(const std::string& k, const std::string& def) const {
        auto it = kv.find(k);
        return it == kv.end() ? def : it->second[0];
    }
    std::string reqStr(const std::string& k) const {
        if (!has(k)) fail("missing required option '" + k + "'");
        return kv.at(k)[0];
    }
    // Rejects options that do not belong to this keyword.
    void allow(std::initializer_list<const char*> keys) const {
        for (const auto& p : kv) {
            bool ok = false;
            for (const char* k : keys) if (p.first == k) ok = true;
            if (!ok) fail("option '" + p.first + "' is not valid here");
        }
    }
};

// Number -> text without trailing zeros (so "-1" instead of "-1.000000").
inline std::string fmt(double v) {
    std::ostringstream o;
    o << v;
    return o.str();
}

inline const std::map<std::string, int>& optionSizes() {
    static const std::map<std::string, int> sizes = {
        {"width", 1}, {"height", 1}, {"spp", 1}, {"depth", 1}, {"ambient", 1}, {"seed", 1},
        {"eye", 3}, {"lookat", 3}, {"up", 3}, {"fov", 1}, {"aperture", 1}, {"focus", 1},
        {"top", 3}, {"bottom", 3}, {"color", 3}, {"checker", 3}, {"scale", 1},
        {"specular", 1}, {"shininess", 1}, {"ior", 1},
        {"center", 3}, {"radius", 1}, {"point", 3}, {"normal", 3},
        {"v0", 3}, {"v1", 3}, {"v2", 3}, {"position", 3}, {"intensity", 1},
        {"material", 1}, {"file", 1}, {"offset", 3},
        {"min", 3}, {"max", 3}, {"from", 3}, {"to", 3}, {"segments", 1}, {"turn", 1}, {"radii", 3}, {"half", 1}, {"tube", 1}, {"axis", 3},
    };
    return sizes;
}

inline Args parseArgs(const std::vector<std::string>& tok, size_t start, const std::string& where) {
    Args a(where);
    for (size_t i = start; i < tok.size();) {
        const std::string& key = tok[i];
        auto it = optionSizes().find(key);
        if (it == optionSizes().end()) a.fail("unknown option '" + key + "'");
        int n = it->second;
        if (i + n >= tok.size()) a.fail("option '" + key + "' needs " + std::to_string(n) + " value(s)");
        for (int k = 1; k <= n; k++) {              // a value that is itself an option name = values missing
            const std::string& val = tok[i + k];
            if (key != "material" && key != "file" && optionSizes().count(val))
                a.fail("option '" + key + "' needs " + std::to_string(n) + " number(s) but found '" + val + "' first");
        }
        if (a.has(key)) a.fail("option '" + key + "' is given twice");
        a.kv[key] = std::vector<std::string>(tok.begin() + i + 1, tok.begin() + i + 1 + n);
        i += 1 + n;
    }
    return a;
}

// Reads a Wavefront .obj model (v and f lines only). Faces with more than 3
// corners are split into triangles. Every index is bounds-checked (REQ-SEC-03).
inline void loadObj(const std::string& file, const std::string& dir, double scale, const Vec3& offset,
                    const Material& mat, HittableList& world, size_t& prims, const Args& a) {
    // REQ-SEC-01: only relative paths below the scene file's folder.
    if (file.empty() || file[0] == '/' || file[0] == '\\' || file.find("..") != std::string::npos ||
        (file.size() > 1 && file[1] == ':'))
        a.fail("model path '" + file + "' must be a relative path without '..'");

    std::ifstream in(dir + file);
    if (!in) a.fail("cannot open model file '" + file + "'");

    std::vector<Vec3> verts;
    std::string line;
    int ln = 0;
    auto bad = [&](const std::string& msg) { throw SceneError(a.where + " (" + file + ":" + std::to_string(ln) + "): " + msg); };

    while (std::getline(in, line)) {
        ln++;
        std::istringstream ss(line);
        std::string tag;
        ss >> tag;
        if (tag == "v") {
            double x, y, z;
            if (!(ss >> x >> y >> z)) bad("bad vertex");
            verts.push_back(Vec3(x, y, z) * scale + offset);
        } else if (tag == "f") {
            std::vector<int> idx;
            std::string t;
            while (ss >> t) {
                int i = 0;
                try { i = std::stoi(t.substr(0, t.find('/'))); } catch (...) { bad("bad face index '" + t + "'"); }
                if (i < 0) i = int(verts.size()) + i + 1;          // negative = counted from the end
                if (i < 1 || i > int(verts.size())) bad("face index " + t + " is out of range");
                idx.push_back(i - 1);
            }
            if (idx.size() < 3) bad("a face needs at least 3 vertices");
            for (size_t k = 1; k + 1 < idx.size(); k++) {
                if (++prims > Limits::maxPrimitives) bad("too many triangles (max " + std::to_string(Limits::maxPrimitives) + ")");
                world.add(std::make_shared<Triangle>(verts[idx[0]], verts[idx[k]], verts[idx[k + 1]], mat));
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Solid shapes made of triangles: box, cylinder and cone (REQ-GEO-08).
// Each builder hands its triangles to "emit", which adds them to the scene.
// ---------------------------------------------------------------------------
template <class Emit>
void buildBox(const Vec3& lo, const Vec3& hi, Emit emit) {
    Vec3 c[8] = {
        Vec3(lo.x, lo.y, lo.z), Vec3(hi.x, lo.y, lo.z), Vec3(hi.x, hi.y, lo.z), Vec3(lo.x, hi.y, lo.z),
        Vec3(lo.x, lo.y, hi.z), Vec3(hi.x, lo.y, hi.z), Vec3(hi.x, hi.y, hi.z), Vec3(lo.x, hi.y, hi.z)};
    const int f[6][4] = {{0, 1, 2, 3}, {4, 5, 6, 7}, {0, 1, 5, 4}, {3, 2, 6, 7}, {0, 3, 7, 4}, {1, 2, 6, 5}};
    for (const auto& q : f) {
        emit(c[q[0]], c[q[1]], c[q[2]]);
        emit(c[q[0]], c[q[2]], c[q[3]]);
    }
}

// A circle of "n" points around the axis from "a" to "b", with the given radius.
inline std::vector<Vec3> ringPoints(const Vec3& center, const Vec3& axis, double radius, int n, double turnDeg) {
    Vec3 w = axis.normalize();
    Vec3 helper = std::fabs(w.y) < 0.9 ? Vec3(0, 1, 0) : Vec3(1, 0, 0);
    Vec3 u = w.cross(helper).normalize();
    Vec3 v = w.cross(u);
    std::vector<Vec3> pts;
    for (int k = 0; k < n; k++) {
        double ang = turnDeg * 3.14159265358979323846 / 180.0 + 2.0 * 3.14159265358979323846 * k / n;
        pts.push_back(center + u * (radius * std::cos(ang)) + v * (radius * std::sin(ang)));
    }
    return pts;
}

template <class Emit>
void buildCylinder(const Vec3& from, const Vec3& to, double radius, int n, double turn, Emit emit) {
    Vec3 axis = to - from;
    std::vector<Vec3> a = ringPoints(from, axis, radius, n, turn);
    std::vector<Vec3> b = ringPoints(to, axis, radius, n, turn);
    for (int k = 0; k < n; k++) {
        int m = (k + 1) % n;
        emit(a[k], a[m], b[m]);          // side
        emit(a[k], b[m], b[k]);
        emit(from, a[m], a[k]);          // bottom cap
        emit(to, b[k], b[m]);            // top cap
    }
}

template <class Emit>
void buildCone(const Vec3& from, const Vec3& apex, double radius, int n, double turn, Emit emit) {
    std::vector<Vec3> a = ringPoints(from, apex - from, radius, n, turn);
    for (int k = 0; k < n; k++) {
        int m = (k + 1) % n;
        emit(a[k], a[m], apex);          // side
        emit(from, a[m], a[k]);          // base cap
    }
}

// An ellipsoid (a sphere stretched by "radii"). half = +1 builds only the upper half (a dome),
// half = -1 only the lower half (a bowl). Either one gets a flat disc across the cut.
template <class Emit>
void buildEllipsoid(const Vec3& c, const Vec3& r, int n, int half, Emit emit) {
    const double PI = 3.14159265358979323846;
    int bands = std::max(4, n / 2);
    if (half != 0) bands = std::max(2, bands / 2);
    double th0 = half < 0 ? PI / 2 : 0.0;
    double th1 = half > 0 ? PI / 2 : PI;
    auto point = [&](int band, int k) {
        double th = th0 + (th1 - th0) * band / bands;
        double ph = 2.0 * PI * k / n;
        return Vec3(c.x + r.x * std::sin(th) * std::cos(ph), c.y + r.y * std::cos(th), c.z + r.z * std::sin(th) * std::sin(ph));
    };
    for (int b = 0; b < bands; b++) {
        for (int k = 0; k < n; k++) {
            int m = (k + 1) % n;
            Vec3 a0 = point(b, k), a1 = point(b, m), b0 = point(b + 1, k), b1 = point(b + 1, m);
            bool topPole = (b == 0 && th0 == 0.0), bottomPole = (b == bands - 1 && th1 == PI);
            if (!topPole) emit(a0, b1, a1);          // skip the empty triangle at a pole
            if (!bottomPole) emit(a0, b0, b1);
        }
    }
    if (half != 0) {
        int cut = half > 0 ? bands : 0;
        for (int k = 0; k < n; k++) emit(c, point(cut, (k + 1) % n), point(cut, k));   // flat disc
    }
}

// A torus (a ring or donut). "radius" is the distance from the centre to the middle of the tube,
// "tube" is the radius of the tube, and "axis" is the direction the hole points in.
template <class Emit>
void buildTorus(const Vec3& c, const Vec3& axis, double major, double minor, int n, Emit emit) {
    const double PI = 3.14159265358979323846;
    int m = std::max(6, n / 3);
    Vec3 w = axis.normalize();
    Vec3 helper = std::fabs(w.y) < 0.9 ? Vec3(0, 1, 0) : Vec3(1, 0, 0);
    Vec3 u = w.cross(helper).normalize();
    Vec3 v = w.cross(u);
    auto point = [&](int i, int j) {
        double th = 2.0 * PI * (i % n) / n, ph = 2.0 * PI * (j % m) / m;
        Vec3 dir = u * std::cos(th) + v * std::sin(th);
        return c + dir * (major + minor * std::cos(ph)) + w * (minor * std::sin(ph));
    };
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            Vec3 p00 = point(i, j), p10 = point(i + 1, j), p01 = point(i, j + 1), p11 = point(i + 1, j + 1);
            emit(p00, p10, p11);
            emit(p00, p11, p01);
        }
    }
}

inline Scene loadScene(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw SceneError("cannot open scene file '" + path + "'");

    size_t slash = path.find_last_of("/\\");
    std::string dir = (slash == std::string::npos) ? "" : path.substr(0, slash + 1);

    Scene sc;
    std::map<std::string, Material> mats;
    size_t prims = 0;
    std::string raw;
    int lineNo = 0;

    while (std::getline(in, raw)) {
        lineNo++;
        size_t hash = raw.find('#');
        if (hash != std::string::npos) raw.erase(hash);

        std::istringstream ss(raw);
        std::vector<std::string> tok;
        std::string t;
        while (ss >> t) tok.push_back(t);
        if (tok.empty()) continue;

        const std::string where = path + ":" + std::to_string(lineNo);
        const std::string& cmd = tok[0];

        auto findMat = [&](const Args& a) -> const Material& {
            std::string name = a.reqStr("material");
            auto it = mats.find(name);
            if (it == mats.end()) a.fail("unknown material '" + name + "' (define it with a 'material' line first)");
            return it->second;
        };
        auto addPrim = [&](const Args& a, std::shared_ptr<Hittable> h) {
            if (++prims > Limits::maxPrimitives) a.fail("too many shapes (max " + std::to_string(Limits::maxPrimitives) + ")");
            sc.world.add(h);
        };

        if (cmd == "settings") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"width", "height", "spp", "depth", "ambient", "seed"});
            Settings& s = sc.settings;
            s.width = int(a.num("width", s.width));
            s.height = int(a.num("height", s.height));
            s.spp = int(a.num("spp", s.spp));
            s.maxDepth = int(a.num("depth", s.maxDepth));
            s.ambient = a.num("ambient", s.ambient);
            s.seed = unsigned(a.num("seed", s.seed));
            validateSettings(s, where);

        } else if (cmd == "camera") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"eye", "lookat", "up", "fov", "aperture", "focus"});
            CameraSpec& c = sc.cam;
            c.present = true;
            c.eye = a.reqVec("eye");
            c.lookAt = a.reqVec("lookat");
            c.up = a.vec("up", Vec3(0, 1, 0));
            c.fov = a.num("fov", 45);
            c.aperture = a.num("aperture", 0);
            c.focus = a.num("focus", -1);
            a.need(c.fov > 0 && c.fov < 180, "fov must be greater than 0 and less than 180 degrees (got " + fmt(c.fov) + ")");
            a.need(c.aperture >= 0, "aperture must not be negative");
            a.need(!a.has("focus") || c.focus > 0, "focus must be greater than 0");
            Vec3 view = c.lookAt - c.eye;
            a.need(view.length() > 1e-9, "lookat must differ from eye");
            a.need(c.up.length() > 1e-9, "up must not be the zero vector");
            a.need(view.normalize().cross(c.up.normalize()).length() > 1e-6,
                   "up must not be parallel to the view direction (eye -> lookat)");

        } else if (cmd == "background") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"top", "bottom", "color"});
            if (a.has("color")) {
                sc.bgTop = sc.bgBottom = a.reqVec("color");
            } else {
                sc.bgTop = a.vec("top", sc.bgTop);
                sc.bgBottom = a.vec("bottom", sc.bgBottom);
            }
            for (const Vec3& c : {sc.bgTop, sc.bgBottom})
                a.need(c.x >= 0 && c.y >= 0 && c.z >= 0, "background colours must not be negative");

        } else if (cmd == "material") {
            if (tok.size() < 3) throw SceneError(where + ": usage: material NAME matte|mirror|glass [options]");
            Args a = parseArgs(tok, 3, where);
            a.allow({"color", "specular", "shininess", "ior", "checker", "scale"});
            const std::string& name = tok[1];
            const std::string& type = tok[2];
            if (mats.count(name)) a.fail("material '" + name + "' is already defined");
            if (mats.size() >= Limits::maxMaterials) a.fail("too many materials");

            Material m;
            if (type == "matte")       { m.type = MatType::Matte;  m.ks = 0.25; m.shininess = 32; }
            else if (type == "mirror") { m.type = MatType::Mirror; m.ks = 0.6;  m.shininess = 128; }
            else if (type == "glass")  { m.type = MatType::Glass;  m.ks = 0.9;  m.shininess = 200; }
            else a.fail("material type must be matte, mirror or glass (got '" + type + "')");

            m.color = a.vec("color", Vec3(1, 1, 1));
            m.ks = a.num("specular", m.ks);
            m.shininess = a.num("shininess", m.shininess);
            m.ior = a.num("ior", 1.5);
            a.need(m.color.x >= 0 && m.color.y >= 0 && m.color.z >= 0, "color values must not be negative");
            a.need(m.ks >= 0, "specular must not be negative");
            a.need(m.shininess > 0, "shininess must be greater than 0");
            a.need(m.ior > 0, "ior must be greater than 0");
            if (a.has("checker")) {
                m.checker = true;
                m.color2 = a.reqVec("checker");
                m.scale = a.num("scale", 1.0);
                a.need(m.scale > 0, "scale must be greater than 0");
            }
            mats[name] = m;

        } else if (cmd == "sphere") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"center", "radius", "material"});
            double r = a.req("radius");
            a.need(r > 0, "radius must be greater than 0 (got " + fmt(r) + ")");
            addPrim(a, std::make_shared<Sphere>(a.reqVec("center"), r, findMat(a)));

        } else if (cmd == "plane") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"point", "normal", "material"});
            Vec3 n = a.reqVec("normal");
            a.need(n.length() > 1e-9, "normal must not be the zero vector");
            addPrim(a, std::make_shared<Plane>(a.reqVec("point"), n, findMat(a)));

        } else if (cmd == "triangle") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"v0", "v1", "v2", "material"});
            addPrim(a, std::make_shared<Triangle>(a.reqVec("v0"), a.reqVec("v1"), a.reqVec("v2"), findMat(a)));

        } else if (cmd == "box") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"min", "max", "material"});
            Vec3 lo = a.reqVec("min"), hi = a.reqVec("max");
            a.need(hi.x > lo.x && hi.y > lo.y && hi.z > lo.z, "box: every 'max' value must be greater than the matching 'min' value");
            const Material& bm = findMat(a);
            buildBox(lo, hi, [&](const Vec3& p, const Vec3& q, const Vec3& r) {
                addPrim(a, std::make_shared<Triangle>(p, q, r, bm));
            });

        } else if (cmd == "cylinder" || cmd == "cone") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"from", "to", "radius", "segments", "turn", "material"});
            Vec3 p0 = a.reqVec("from"), p1 = a.reqVec("to");
            double r = a.req("radius");
            int n = int(a.num("segments", 32));
            double turn = a.num("turn", 0);
            a.need(r > 0, cmd + ": radius must be greater than 0 (got " + fmt(r) + ")");
            a.need((p1 - p0).length() > 1e-9, cmd + ": 'from' and 'to' must be different points");
            a.need(n >= 3 && n <= 64, cmd + ": segments must be between 3 and 64 (got " + std::to_string(n) + ")");
            const Material& sm = findMat(a);
            auto emit = [&](const Vec3& p, const Vec3& q, const Vec3& s) {
                addPrim(a, std::make_shared<Triangle>(p, q, s, sm));
            };
            if (cmd == "cylinder") buildCylinder(p0, p1, r, n, turn, emit);
            else                   buildCone(p0, p1, r, n, turn, emit);

        } else if (cmd == "ellipsoid") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"center", "radii", "segments", "half", "material"});
            Vec3 rr = a.reqVec("radii");
            int n = int(a.num("segments", 36));
            int half = int(a.num("half", 0));
            a.need(rr.x > 0 && rr.y > 0 && rr.z > 0, "ellipsoid: every radius must be greater than 0");
            a.need(n >= 6 && n <= 64, "ellipsoid: segments must be between 6 and 64 (got " + std::to_string(n) + ")");
            const Material& em = findMat(a);
            buildEllipsoid(a.reqVec("center"), rr, n, half, [&](const Vec3& p, const Vec3& q, const Vec3& s) {
                addPrim(a, std::make_shared<Triangle>(p, q, s, em));
            });

        } else if (cmd == "torus") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"center", "radius", "tube", "axis", "segments", "material"});
            Vec3 ctr = a.reqVec("center");
            double major = a.req("radius"), minor = a.req("tube");
            Vec3 axis = a.has("axis") ? a.reqVec("axis") : Vec3(0, 1, 0);
            int n = int(a.num("segments", 36));
            a.need(major > 0 && minor > 0, "torus: radius and tube must be greater than 0");
            a.need(axis.length() > 1e-9, "torus: axis must not be (0 0 0)");
            a.need(n >= 6 && n <= 64, "torus: segments must be between 6 and 64 (got " + std::to_string(n) + ")");
            const Material& tm = findMat(a);
            buildTorus(ctr, axis, major, minor, n, [&](const Vec3& p, const Vec3& q, const Vec3& s) {
                addPrim(a, std::make_shared<Triangle>(p, q, s, tm));
            });

        } else if (cmd == "obj") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"file", "scale", "offset", "material"});
            double sc2 = a.num("scale", 1.0);
            a.need(sc2 > 0, "scale must be greater than 0");
            loadObj(a.reqStr("file"), dir, sc2, a.vec("offset", Vec3()), findMat(a), sc.world, prims, a);

        } else if (cmd == "light") {
            Args a = parseArgs(tok, 1, where);
            a.allow({"position", "color", "intensity"});
            if (sc.lights.size() >= Limits::maxLights) a.fail("too many lights (max " + std::to_string(Limits::maxLights) + ")");
            Vec3 c = a.vec("color", Vec3(1, 1, 1));
            double k = a.num("intensity", 1.0);
            a.need(c.x >= 0 && c.y >= 0 && c.z >= 0 && k >= 0, "light colour and intensity must not be negative");
            sc.lights.push_back({a.reqVec("position"), c * k});

        } else {
            throw SceneError(where + ": unknown keyword '" + cmd + "'");
        }
    }

    if (!sc.cam.present) throw SceneError(path + ": the scene has no 'camera' line");
    sc.world.accelerate();
    return sc;
}
