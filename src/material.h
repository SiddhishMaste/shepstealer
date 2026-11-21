#pragma once
#include <cmath>
#include "vec3.h"

enum class MatType { Matte, Mirror, Glass };

struct Material {
    MatType type = MatType::Matte;
    Vec3 color = Vec3(1, 1, 1);
    double ks = 0.25;          // specular strength
    double shininess = 32;     // specular sharpness
    double ior = 1.5;          // index of refraction (glass)

    bool checker = false;      // optional checkerboard
    Vec3 color2 = Vec3(0, 0, 0);
    double scale = 1.0;

    Vec3 albedo(const Vec3& p) const {
        if (!checker) return color;
        int k = int(std::floor(p.x / scale)) + int(std::floor(p.z / scale));
        return (k & 1) ? color2 : color;
    }
};
