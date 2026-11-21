#pragma once
#include "hittable.h"

class Plane : public Hittable {
public:
    Vec3 point;
    Vec3 normal;
    Material mat;

    Plane(const Vec3& point, const Vec3& normal, const Material& mat)
        : point(point), normal(normal.normalize()), mat(mat) {}

    bool hit(const Ray& r, double tMin, double tMax, HitRecord& rec) const override {
        double denom = r.direction.dot(normal);
        if (std::fabs(denom) < 1e-9) return false;     // ray parallel to the plane

        double t = (point - r.origin).dot(normal) / denom;
        if (t < tMin || t > tMax) return false;

        rec.t = t;
        rec.point = r.at(t);
        rec.front = denom < 0;
        rec.normal = rec.front ? normal : normal * -1.0;
        rec.mat = mat;
        return true;
    }

    bool bounds(AABB&) const override { return false; }   // infinite
};
