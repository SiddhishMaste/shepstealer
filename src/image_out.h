#pragma once
#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include "vec3.h"

// Clamp to [0,1] (REQ-LGT-08), then sRGB transfer function (REQ-OUT-04).
inline unsigned char toByte(double c) {
    c = c < 0 ? 0 : (c > 1 ? 1 : c);
    c = (c <= 0.0031308) ? 12.92 * c : 1.055 * std::pow(c, 1.0 / 2.4) - 0.055;
    return (unsigned char)(c * 255.0 + 0.5);
}

// Checks the output path BEFORE the (possibly long) render starts.
// Returns "" if it looks writable, otherwise an error message.
inline std::string checkOutputPath(const std::string& path) {
    namespace fs = std::filesystem;
    std::string ext;
    size_t dot = path.find_last_of('.');
    if (dot != std::string::npos) ext = path.substr(dot + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return std::tolower(c); });
    if (ext != "png" && ext != "ppm") return "unknown output format '." + ext + "' (use .png or .ppm)";

    fs::path dir = fs::path(path).parent_path();
    if (dir.empty()) dir = ".";
    std::error_code ec;
    if (!fs::is_directory(dir, ec)) return "the folder '" + dir.string() + "' does not exist";
    if (fs::is_directory(path, ec)) return "'" + path + "' is a folder, not a file";

    bool existed = fs::exists(path, ec);
    {
        std::ofstream probe(path, std::ios::app | std::ios::binary);
        if (!probe) return "cannot write '" + path + "' (check you have permission)";
    }
    if (!existed) fs::remove(path, ec);          // do not leave an empty file behind
    return "";
}

// Writes .ppm or .png (chosen by the file extension, REQ-OUT-03).
// Returns "" on success, otherwise an error message (REQ-OUT-05).
inline std::string writeImage(const std::string& path, const std::vector<Vec3>& pixels, int W, int H) {
    std::string ext;
    size_t dot = path.find_last_of('.');
    if (dot != std::string::npos) ext = path.substr(dot + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return std::tolower(c); });

    std::vector<unsigned char> rgb(pixels.size() * 3);
    for (size_t i = 0; i < pixels.size(); i++) {
        rgb[3 * i] = toByte(pixels[i].x);
        rgb[3 * i + 1] = toByte(pixels[i].y);
        rgb[3 * i + 2] = toByte(pixels[i].z);
    }

    if (ext == "ppm") {
        std::ofstream f(path, std::ios::binary);
        if (!f) return "cannot write '" + path + "' (check the folder exists and you have permission)";
        f << "P6\n" << W << " " << H << "\n255\n";
        f.write(reinterpret_cast<const char*>(rgb.data()), std::streamsize(rgb.size()));
        f.flush();
        if (!f) return "failed while writing '" + path + "'";
        return "";
    }
    if (ext == "png") {
        if (!stbi_write_png(path.c_str(), W, H, 3, rgb.data(), W * 3))
            return "cannot write '" + path + "' (check the folder exists and you have permission)";
        return "";
    }
    return "unknown output format '." + ext + "' (use .png or .ppm)";
}
