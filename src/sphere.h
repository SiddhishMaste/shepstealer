#pragma once
#include "hittable.h"

class Sphere : public Hittable {
public:
    Vec3 center;
    double radius;
    Material mat;

    Sphere(const Vec3& center, double radius, const Material& mat)
        : center(center), radius(radius), mat(mat) {}

    bool hit(const Ray& r, double tMin, double tMax, HitRecord& rec) const override {
        Vec3 oc = r.origin - center;
        double a = r.direction.dot(r.direction);
        double h = r.direction.dot(oc);
        double c = oc.dot(oc) - radius * radius;

        double disc = h * h - a * c;
        if (disc < 0) return false;

        double root = std::sqrt(disc);
        double t = (-h - root) / a;
        if (t < tMin || t > tMax) {
            t = (-h + root) / a;
            if (t < tMin || t > tMax) return false;
        }

        rec.t = t;
        rec.point = r.at(t);
        Vec3 outward = (rec.point - center) * (1.0 / radius);
        rec.front = outward.dot(r.direction) < 0;
        rec.normal = rec.front ? outward : outward * -1.0;
        rec.mat = mat;
        return true;
    }

    bool bounds(AABB& box) const override {
        Vec3 r(radius, radius, radius);
        box = AABB(center - r, center + r);
        return true;
    }
};
