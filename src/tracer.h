#pragma once
#include <algorithm>
#include <cmath>
#include <limits>
#include "scene.h"

const double INF = std::numeric_limits<double>::infinity();
const double T_MIN = 1e-4;            // minimum hit distance: prevents "shadow acne"

inline Vec3 sky(const Scene& sc, const Ray& r) {
    double k = 0.5 * (r.direction.normalize().y + 1.0);
    return sc.bgBottom * (1.0 - k) + sc.bgTop * k;
}

// r = d - 2 (d . n) n
inline Vec3 reflectDir(const Vec3& d, const Vec3& n) {
    return d - n * (2.0 * d.dot(n));
}

// Is the path from 'origin' along 'dir' blocked before 'dist'?
// Glass does not block light, so the shadow ray passes through it.
inline bool inShadow(const Scene& sc, Vec3 origin, const Vec3& dir, double dist) {
    double travelled = 0;
    while (true) {
        HitRecord tmp;
        if (!sc.world.hit(Ray(origin, dir), T_MIN, dist - travelled, tmp)) return false;
        if (tmp.mat.type != MatType::Glass) return true;
        origin = tmp.point;
        travelled += tmp.t;
    }
}

// Ambient + diffuse + specular, with hard shadows. Mirror and glass call this
// with withDiffuse = false and only get highlights.
inline Vec3 lighting(const Scene& sc, const Ray& r, const HitRecord& rec, bool withDiffuse) {
    Vec3 base = rec.mat.albedo(rec.point, rec.normal);
    Vec3 result = withDiffuse ? base * (sc.settings.ambient + rec.mat.glow) : Vec3(0, 0, 0);
    Vec3 toEye = (r.direction * -1.0).normalize();
    Vec3 shadowOrigin = rec.point + rec.normal * T_MIN;

    for (const Light& L : sc.lights) {
        Vec3 toLight = L.position - rec.point;
        double dist = toLight.length();
        if (dist < 1e-9) continue;
        toLight = toLight * (1.0 / dist);

        double ndl = rec.normal.dot(toLight);
        if (ndl <= 0) continue;
        if (inShadow(sc, shadowOrigin, toLight, dist)) continue;

        if (withDiffuse) result = result + base.mulv(L.color) * (0.9 * ndl);

        Vec3 halfVec = (toLight + toEye).normalize();
        double spec = rec.mat.ks * std::pow(std::max(0.0, rec.normal.dot(halfVec)), rec.mat.shininess);
        result = result + L.color * spec;
    }
    return result;
}

// 'depth' counts down; below 0 the recursion stops.
inline Vec3 rayColor(const Scene& sc, const Ray& r, int depth) {
    if (depth < 0) return sky(sc, r);

    HitRecord rec;
    if (!sc.world.hit(r, T_MIN, INF, rec)) return sky(sc, r);

    Vec3 d = r.direction.normalize();
    const Vec3& n = rec.normal;

    if (rec.mat.type == MatType::Matte) return lighting(sc, r, rec, true);

    if (rec.mat.type == MatType::Mirror) {
        Vec3 reflected = rayColor(sc, Ray(rec.point, reflectDir(d, n)), depth - 1);
        return rec.mat.color.mulv(reflected) + lighting(sc, r, rec, false);
    }

    // ---- glass
    double ior = rec.mat.ior;
    double n1 = rec.front ? 1.0 : ior;          // medium the ray is in
    double n2 = rec.front ? ior : 1.0;          // medium it enters
    double eta = n1 / n2;

    double cosi = std::min(1.0, -d.dot(n));
    double k = 1.0 - eta * eta * (1.0 - cosi * cosi);

    Vec3 reflected = rayColor(sc, Ray(rec.point, reflectDir(d, n)), depth - 1);
    Vec3 result;

    if (k < 0) {
        result = reflected;                      // total internal reflection
    } else {
        Vec3 refrDir = d * eta + n * (eta * cosi - std::sqrt(k));    // Snell's law
        Vec3 refracted = rayColor(sc, Ray(rec.point, refrDir), depth - 1);

        double r0 = std::pow((n1 - n2) / (n1 + n2), 2);              // Schlick's approximation
        double c = (n1 <= n2) ? cosi : std::sqrt(k);
        double R = r0 + (1.0 - r0) * std::pow(1.0 - c, 5);

        Vec3 tint = rec.front ? rec.mat.color : Vec3(1, 1, 1);
        result = reflected * R + refracted.mulv(tint) * (1.0 - R);
    }
    return result + lighting(sc, r, rec, false);
}
