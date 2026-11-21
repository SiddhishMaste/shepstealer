#pragma once
#include <memory>
#include <vector>
#include "hittable.h"

// Bounding Volume Hierarchy (REQ-PERF-04): a tree of boxes. A ray that
// misses a box skips everything inside it, so big meshes stay fast.
class BVHNode : public Hittable {
public:
    std::shared_ptr<Hittable> left, right;
    AABB box;

    BVHNode(std::vector<std::shared_ptr<Hittable>>& objs, size_t start, size_t end) {
        size_t n = end - start;

        AABB total;
        for (size_t i = start; i < end; i++) {
            AABB b;
            objs[i]->bounds(b);
            total = (i == start) ? b : AABB::surround(total, b);
        }
        box = total;

        if (n == 1) { left = right = objs[start]; return; }

        // Split along the longest axis, at the median object.
        Vec3 ext = total.max - total.min;
        int axis = (ext.x >= ext.y && ext.x >= ext.z) ? 0 : (ext.y >= ext.z ? 1 : 2);
        auto key = [axis](const std::shared_ptr<Hittable>& o) {
            AABB b;
            o->bounds(b);
            Vec3 c = b.center();
            return axis == 0 ? c.x : (axis == 1 ? c.y : c.z);
        };
        std::sort(objs.begin() + start, objs.begin() + end,
                  [&](const std::shared_ptr<Hittable>& a, const std::shared_ptr<Hittable>& b) {
                      return key(a) < key(b);
                  });

        size_t mid = start + n / 2;
        left = (mid - start == 1) ? objs[start] : std::make_shared<BVHNode>(objs, start, mid);
        right = (end - mid == 1) ? objs[mid] : std::make_shared<BVHNode>(objs, mid, end);
    }

    bool hit(const Ray& r, double tMin, double tMax, HitRecord& rec) const override {
        if (!box.hit(r, tMin, tMax)) return false;
        bool hitLeft = left->hit(r, tMin, tMax, rec);
        bool hitRight = (right != left) && right->hit(r, tMin, hitLeft ? rec.t : tMax, rec);
        return hitLeft || hitRight;
    }

    bool bounds(AABB& b) const override { b = box; return true; }
};
