#pragma once
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

#include "camera.h"
#include "tracer.h"

// Renders the scene on 'threads' worker threads and returns linear RGB pixels.
// The scene is read-only while rendering. Threads take whole rows from a shared
// counter, so no two threads ever write the same pixel (REQ-REN-01..03).
inline std::vector<Vec3> renderScene(const Scene& sc, int threads, bool showProgress) {
    const int W = sc.settings.width, H = sc.settings.height;
    const int samples = sc.settings.spp, maxDepth = sc.settings.maxDepth;
    const unsigned seed = sc.settings.seed;

    double focus = sc.cam.focus > 0 ? sc.cam.focus : (sc.cam.lookAt - sc.cam.eye).length();
    Camera cam(sc.cam.eye, sc.cam.lookAt, sc.cam.up, sc.cam.fov, double(W) / H, sc.cam.aperture, focus);

    std::vector<Vec3> pixels(size_t(W) * H);
    std::atomic<int> nextRow(0), rowsDone(0);

    auto worker = [&]() {
        for (;;) {
            int j = nextRow.fetch_add(1);
            if (j >= H) break;
            for (int i = 0; i < W; i++) {
                Rng rng(pixelSeed(seed, i, j));                  // same pixel -> same random numbers
                Vec3 sum(0, 0, 0);
                for (int s = 0; s < samples; s++) {
                    double u = (i + (samples > 1 ? rng.next() : 0.5)) / W;
                    double v = 1.0 - (j + (samples > 1 ? rng.next() : 0.5)) / H;
                    sum = sum + rayColor(sc, cam.getRay(u, v, rng), maxDepth);
                }
                pixels.at(size_t(j) * W + i) = sum * (1.0 / samples);
            }
            rowsDone.fetch_add(1);
        }
    };

    std::vector<std::thread> pool;
    for (int t = 0; t < threads; t++) pool.emplace_back(worker);

    // Progress at most twice per second (REQ-REN-06).
    auto last = std::chrono::steady_clock::now();
    while (rowsDone.load() < H) {
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        auto now = std::chrono::steady_clock::now();
        if (showProgress && now - last >= std::chrono::milliseconds(500)) {
            last = now;
            int done = rowsDone.load();
            std::cout << "\rRendering: " << (100 * done / H) << "%  (" << done << "/" << H << " rows)" << std::flush;
        }
    }
    for (auto& th : pool) th.join();
    if (showProgress) std::cout << "\rRendering: 100%  (" << H << "/" << H << " rows)\n";
    return pixels;
}
