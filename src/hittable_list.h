#pragma once
#include <memory>
#include <vector>
#include "bvh.h"

class HittableList : public Hittable {
public:
    std::vector<std::shared_ptr<Hittable>> objects;

    void add(std::shared_ptr<Hittable> obj) { objects.push_back(obj); }

    // Closest hit among all objects (REQ-GEO-11).
    bool hit(const Ray& r, double tMin, double tMax, HitRecord& rec) const override {
        HitRecord temp;
        bool anyHit = false;
        double closest = tMax;

        for (const auto& obj : objects) {
            if (obj->hit(r, tMin, closest, temp)) {
                anyHit = true;
                closest = temp.t;
                rec = temp;
            }
        }
        return anyHit;
    }

    bool bounds(AABB&) const override { return false; }

    // Puts all bounded shapes into a BVH. Planes stay outside it.
    void accelerate() {
        std::vector<std::shared_ptr<Hittable>> bounded, unbounded;
        for (const auto& o : objects) {
            AABB b;
            (o->bounds(b) ? bounded : unbounded).push_back(o);
        }
        if (bounded.size() <= 8) return;       // not worth it for tiny scenes
        objects = unbounded;
        objects.push_back(std::make_shared<BVHNode>(bounded, 0, bounded.size()));
    }
};
