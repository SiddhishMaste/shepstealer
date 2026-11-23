#pragma once
#include <cmath>
#include <cstdint>
#include <string>
#include "vec3.h"

enum class MatType { Matte, Mirror, Glass };

// Block textures: every cell of a 3D grid gets one flat colour picked from a small
// palette by a hash of the cell number, so surfaces look like pixel-art blocks.
enum class Tex { None, Grass, Dirt, Stone, Sand, Planks, Water, Lava, Cloud, Snow, Leaves, Bricks };

inline bool texFromName(const std::string& s, Tex& t) {
    static const char* names[] = {"", "grass", "dirt", "stone", "sand", "planks", "water", "lava", "cloud", "snow", "leaves", "bricks"};
    for (int i = 1; i < 12; i++) if (s == names[i]) { t = Tex(i); return true; }
    return false;
}

inline uint32_t cellHash(int x, int y, int z) {
    uint32_t h = uint32_t(x) * 374761393u + uint32_t(y) * 668265263u + uint32_t(z) * 2147483647u + 1274126177u;
    h = (h ^ (h >> 13)) * 1274126177u;
    return h ^ (h >> 16);
}

inline Vec3 blockColor(Tex t, int ix, int iy, int iz) {
    uint32_t h = cellHash(ix, iy, iz);
    int k = int(h % 4);
    auto pick = [&](const Vec3* pal) { return pal[k]; };
    static const Vec3 grass[4]  = {{.33,.62,.18},{.29,.55,.16},{.39,.71,.22},{.25,.48,.14}};
    static const Vec3 dirt[4]   = {{.52,.36,.22},{.45,.30,.18},{.58,.41,.26},{.38,.26,.15}};
    static const Vec3 stone[4]  = {{.50,.50,.50},{.44,.44,.45},{.57,.57,.57},{.37,.37,.39}};
    static const Vec3 sand[4]   = {{.87,.80,.55},{.82,.75,.50},{.92,.85,.62},{.78,.70,.46}};
    static const Vec3 water[4]  = {{.14,.34,.85},{.18,.40,.90},{.11,.28,.75},{.24,.50,.95}};
    static const Vec3 lava[4]   = {{1.0,.45,.05},{1.0,.66,.10},{.90,.25,.02},{1.0,.86,.28}};
    static const Vec3 cloud[4]  = {{1,1,1},{.94,.96,1},{.86,.89,.96},{1,1,1}};
    static const Vec3 snow[4]   = {{.97,.98,1},{.91,.94,.99},{1,1,1},{.88,.92,.97}};
    static const Vec3 leaves[4] = {{.17,.42,.12},{.12,.33,.10},{.23,.52,.15},{.09,.27,.08}};
    switch (t) {
        case Tex::Grass:  return pick(grass);
        case Tex::Dirt:   return pick(dirt);
        case Tex::Stone:  return pick(stone);
        case Tex::Sand:   return pick(sand);
        case Tex::Water:  return pick(water);
        case Tex::Lava:   return pick(lava);
        case Tex::Cloud:  return pick(cloud);
        case Tex::Snow:   return pick(snow);
        case Tex::Leaves: return pick(leaves);
        case Tex::Planks: {                       // boards: a dark seam every 4th row
            Vec3 c = Vec3(.68, .50, .28) * (0.88 + 0.06 * k);
            return (((iy % 4) + 4) % 4 == 0) ? c * 0.68 : c;
        }
        case Tex::Bricks: {                       // rows of bricks, offset every other row, grey mortar
            int row = iy >> 1, col = (ix + iz + ((row & 1) ? 2 : 0)) >> 2;
            bool mortar = ((iy & 1) == 0) || (((ix + iz + ((row & 1) ? 2 : 0)) & 3) == 0);
            if (mortar) return Vec3(.72, .70, .66);
            uint32_t b = cellHash(col, row, 3) % 3;
            return Vec3(.62, .22, .16) * (0.88 + 0.08 * b);
        }
        default: return Vec3(1, 1, 1);
    }
}

struct Material {
    MatType type = MatType::Matte;
    Vec3 color = Vec3(1, 1, 1);
    double ks = 0.25;          // specular strength
    double shininess = 32;     // specular sharpness
    double ior = 1.5;          // index of refraction (glass)

    bool checker = false;      // optional checkerboard
    Vec3 color2 = Vec3(0, 0, 0);
    double scale = 1.0;        // checker square size, or block size for textures

    Tex tex = Tex::None;       // optional block texture
    double glow = 0.0;         // light the surface gives off by itself (for lava)

    // n is the surface normal: the colour is sampled a hair inside the surface so a
    // flat face that sits exactly on a cell border does not flicker.
    Vec3 albedo(const Vec3& p, const Vec3& n) const {
        if (tex != Tex::None) {
            Vec3 q = p - n * (scale * 0.02);
            return blockColor(tex, int(std::floor(q.x / scale)), int(std::floor(q.y / scale)), int(std::floor(q.z / scale))).mulv(color);
        }
        if (!checker) return color;
        int k = int(std::floor(p.x / scale)) + int(std::floor(p.z / scale));
        return (k & 1) ? color2 : color;
    }
};
