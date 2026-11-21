#pragma once
#include "hittable.h"

// Moller-Trumbore ray-triangle intersection (REQ-GEO-06/07).
class Triangle : public Hittable {
public:
    Vec3 v0, e1, e2, normal;
    Material mat;

    Triangle(const Vec3& a, const Vec3& b, const Vec3& c, const Material& mat)
        : v0(a), e1(b - a), e2(c - a), mat(mat) {
        normal = e1.cross(e2).normalize();
    }

    bool hit(const Ray& r, double tMin, double tMax, HitRecord& rec) const override {
        Vec3 p = r.direction.cross(e2);
        double det = e1.dot(p);
        if (std::fabs(det) < 1e-12) return false;          // ray parallel to triangle
        double inv = 1.0 / det;

        Vec3 tv = r.origin - v0;
        double u = tv.dot(p) * inv;                        // barycentric u
        if (u < 0 || u > 1) return false;

        Vec3 q = tv.cross(e1);
        double v = r.direction.dot(q) * inv;               // barycentric v
        if (v < 0 || u + v > 1) return false;

        double t = e2.dot(q) * inv;
        if (t < tMin || t > tMax) return false;

        rec.t = t;
        rec.point = r.at(t);
        rec.front = r.direction.dot(normal) < 0;
        rec.normal = rec.front ? normal : normal * -1.0;
        rec.mat = mat;
        return true;
    }

    bool bounds(AABB& box) const override {
        Vec3 a = v0, b = v0 + e1, c = v0 + e2;
        const double pad = 1e-6;
        box = AABB(Vec3(std::min({a.x, b.x, c.x}) - pad, std::min({a.y, b.y, c.y}) - pad, std::min({a.z, b.z, c.z}) - pad),
                   Vec3(std::max({a.x, b.x, c.x}) + pad, std::max({a.y, b.y, c.y}) + pad, std::max({a.z, b.z, c.z}) + pad));
        return true;
    }
};
