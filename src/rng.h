#pragma once
#include <cstdint>

// Small seeded random number generator (mulberry32).
// Same seed -> same sequence, so renders are reproducible.
class Rng {
    uint32_t s;
public:
    explicit Rng(uint32_t seed) : s(seed) {}

    // Random number in [0, 1)
    double next() {
        s += 0x6D2B79F5u;
        uint32_t t = s;
        t = (t ^ (t >> 15)) * (t | 1u);
        t ^= t + (t ^ (t >> 7)) * (t | 61u);
        return double(t ^ (t >> 14)) / 4294967296.0;
    }
};

// Mixes a global seed with the pixel position into a per-pixel seed.
inline uint32_t pixelSeed(uint32_t seed, int x, int y) {
    uint32_t h = seed * 747796405u + uint32_t(x) * 2891336453u + uint32_t(y) * 277803737u;
    h ^= h >> 16; h *= 0x85EBCA6Bu;
    h ^= h >> 13; h *= 0xC2B2AE35u;
    h ^= h >> 16;
    return h;
}
