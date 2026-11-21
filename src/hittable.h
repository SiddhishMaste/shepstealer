#pragma once
#include <algorithm>
#include "ray.h"
#include "material.h"

// Axis-aligned bounding box, used by the BVH.
struct AABB {
    Vec3 min, max;

    AABB() {}
    AABB(const Vec3& min, const Vec3& max) : min(min), max(max) {}

    static AABB surround(const AABB& a, const AABB& b) {
        return AABB(Vec3(std::min(a.min.x, b.min.x), std::min(a.min.y, b.min.y), std::min(a.min.z, b.min.z)),
                    Vec3(std::max(a.max.x, b.max.x), std::max(a.max.y, b.max.y), std::max(a.max.z, b.max.z)));
    }

    Vec3 center() const { return (min + max) * 0.5; }

    // Slab test: does the ray pass through the box between tMin and tMax?
    bool hit(const Ray& r, double tMin, double tMax) const {
        const double o[3] = {r.origin.x, r.origin.y, r.origin.z};
        const double d[3] = {r.direction.x, r.direction.y, r.direction.z};
        const double lo[3] = {min.x, min.y, min.z};
        const double hi[3] = {max.x, max.y, max.z};
        for (int a = 0; a < 3; a++) {
            double inv = 1.0 / d[a];
            double t0 = (lo[a] - o[a]) * inv;
            double t1 = (hi[a] - o[a]) * inv;
            if (inv < 0) std::swap(t0, t1);
            if (t0 > tMin) tMin = t0;
            if (t1 < tMax) tMax = t1;
            if (tMax <= tMin) return false;
        }
        return true;
    }
};

struct HitRecord {
    double t;
    Vec3 point;
    Vec3 normal;     // always faces against the incoming ray
    bool front;      // true if the ray hit the outside of the surface
    Material mat;
};

class Hittable {
public:
    virtual ~Hittable() {}
    virtual bool hit(const Ray& r, double tMin, double tMax, HitRecord& rec) const = 0;
    // Fills 'box' and returns true, or returns false for unbounded shapes (planes).
    virtual bool bounds(AABB& box) const = 0;
};
