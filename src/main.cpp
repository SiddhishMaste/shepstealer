#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>

#include "image_out.h"
#include "render.h"
#include "scene.h"

static void printHelp() {
    std::cout <<
        "SheepStealer Engine 1.0 - a CPU ray tracer\n"
        "\n"
        "Usage: sheepstealer <scene.txt> <output.png|output.ppm> [options]\n"
        "       sheepstealer --scene FILE --out FILE [options]\n"
        "\n"
        "Options:\n"
        "  --scene FILE    scene file to render\n"
        "  --out FILE      output image (.png or .ppm)\n"
        "  --width N       image width in pixels   (1-" << Limits::maxDim << ")\n"
        "  --height N      image height in pixels  (1-" << Limits::maxDim << ")\n"
        "  --spp N         samples per pixel, for smooth edges (1-" << Limits::maxSpp << ")\n"
        "  --depth N       maximum reflection/refraction bounces (0-" << Limits::maxDepth << ")\n"
        "  --threads N     worker threads (default: all CPU cores)\n"
        "  --seed N        random seed (same seed = identical image)\n"
        "  --help          show this help\n"
        "\n"
        "Examples:\n"
        "  sheepstealer scenes/teddy.txt teddy.png\n"
        "  sheepstealer scenes/spheres.txt out.png --width 1280 --height 720 --spp 32\n"
        "  sheepstealer scenes/spheres.txt out.ppm --threads 2 --depth 8\n";
}

// Reads a whole-number option value, or fails with a clear message.
static int intArg(const std::string& name, const std::string& text) {
    char* end = nullptr;
    long v = std::strtol(text.c_str(), &end, 10);
    if (text.empty() || *end != '\0' || v < -2000000000L || v > 2000000000L)
        throw SceneError("option " + name + " expects a whole number, got '" + text + "'");
    return int(v);
}

int main(int argc, char** argv) {
    try {
        std::string scenePath, outPath;
        bool hasW = false, hasH = false, hasSpp = false, hasDepth = false, hasSeed = false;
        int w = 0, h = 0, spp = 0, depth = 0, seed = 0;
        int threads = int(std::thread::hardware_concurrency());
        if (threads < 1) threads = 1;

        std::vector<std::string> positional;
        for (int i = 1; i < argc; i++) {
            std::string a = argv[i];
            auto value = [&]() -> std::string {
                if (i + 1 >= argc) throw SceneError("option " + a + " needs a value (try --help)");
                return argv[++i];
            };
            if (a == "--help" || a == "-h") { printHelp(); return 0; }
            else if (a == "--scene")   scenePath = value();
            else if (a == "--out")     outPath = value();
            else if (a == "--width")   { w = intArg(a, value());     hasW = true; }
            else if (a == "--height")  { h = intArg(a, value());     hasH = true; }
            else if (a == "--spp")     { spp = intArg(a, value());   hasSpp = true; }
            else if (a == "--depth")   { depth = intArg(a, value()); hasDepth = true; }
            else if (a == "--seed")    { seed = intArg(a, value());  hasSeed = true; }
            else if (a == "--threads") threads = intArg(a, value());
            else if (!a.empty() && a[0] == '-') throw SceneError("unknown option '" + a + "' (try --help)");
            else positional.push_back(a);
        }
        if (positional.size() > 2) throw SceneError("too many arguments (try --help)");
        if (scenePath.empty() && positional.size() > 0) scenePath = positional[0];
        if (outPath.empty() && positional.size() > 1) outPath = positional[1];
        if (scenePath.empty() || outPath.empty()) {
            printHelp();
            throw SceneError("a scene file and an output file are both required");
        }
        if (threads < 1 || threads > Limits::maxThreads)
            throw SceneError("--threads must be between 1 and " + std::to_string(Limits::maxThreads));

        std::string outErr = checkOutputPath(outPath);
        if (!outErr.empty()) throw SceneError(outErr);

        Scene sc = loadScene(scenePath);

        // Command-line options override the scene file.
        if (hasW) sc.settings.width = w;
        if (hasH) sc.settings.height = h;
        if (hasSpp) sc.settings.spp = spp;
        if (hasDepth) sc.settings.maxDepth = depth;
        if (hasSeed) sc.settings.seed = unsigned(seed);
        validateSettings(sc.settings, "command line");

        std::cout << "Scene: " << scenePath << "  (" << sc.settings.width << "x" << sc.settings.height
                  << ", " << sc.settings.spp << " samples/pixel, depth " << sc.settings.maxDepth
                  << ", " << threads << " threads)\n";

        auto start = std::chrono::steady_clock::now();
        std::vector<Vec3> pixels = renderScene(sc, threads, true);
        double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

        std::string err = writeImage(outPath, pixels, sc.settings.width, sc.settings.height);
        if (!err.empty()) throw SceneError(err);

        std::cout << "Render time: " << secs << " s\n";
        std::cout << "Saved: " << outPath << "\n";
        return 0;
    } catch (const SceneError& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
