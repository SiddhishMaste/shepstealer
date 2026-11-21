#pragma once
#include "ray.h"
#include "rng.h"

// Look-at camera with perspective projection and thin-lens depth of field
// (REQ-CAM-01..08).
class Camera {
public:
    Camera(const Vec3& eye, const Vec3& lookAt, const Vec3& up, double fovDeg,
           double aspect, double aperture, double focusDist)
        : eye(eye), aperture(aperture), focusDist(focusDist) {
        w = (eye - lookAt).normalize();          // points backwards
        u = up.cross(w).normalize();             // points right
        v = w.cross(u);                          // points up
        halfH = std::tan(fovDeg * 3.14159265358979323846 / 360.0);
        halfW = halfH * aspect;
    }

    // s: 0 = left, 1 = right.   t: 0 = bottom, 1 = top.
    Ray getRay(double s, double t, Rng& rng) const {
        Vec3 dir = (u * ((2 * s - 1) * halfW) + v * ((2 * t - 1) * halfH) - w).normalize();
        if (aperture <= 0) return Ray(eye, dir);                 // pinhole: no blur

        // Every lens sample aims at the same point on the focal plane.
        double tFocus = focusDist / -dir.dot(w);
        Vec3 focal = eye + dir * tFocus;
        double x, y;
        do { x = 2 * rng.next() - 1; y = 2 * rng.next() - 1; } while (x * x + y * y > 1);
        Vec3 origin = eye + u * (x * aperture) + v * (y * aperture);
        return Ray(origin, (focal - origin).normalize());
    }

private:
    Vec3 eye, u, v, w;
    double halfH, halfW, aperture, focusDist;
};
