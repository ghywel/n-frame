// tremor.glsl -- the invisible made visible: Eulerian magnification in a seven-frame window (2026-10-25)
//
// Wu, Rubinstein, Shih, Guttag, Durand and Freeman (SIGGRAPH 2012) showed that amplifying each pixel's temporal change
// in a frequency band, after a spatial blur, magnifies motions and colour changes too small to see. Here the band is the
// difference of two temporal Gaussians over the window [-3 .. +3] (sigma 0.8 and 2.5 frames: about 2 to 8 Hz at 24 fps),
// taken of a 9 x 9 blur, multiplied by TREMOR_GAIN and added to the frame: a hand's tremor, a breath, a cable's hum,
// a camera's shake grows; what is still stays. Large motion is left alone (the gain falls away where the window's
// own change is already big, and the added signal is soft-limited): this is a magnifier for quiet shots. The window is short, so the slow things (a pulse, at about 1 Hz) need
// the longer history a storage ring would give (long-exposure.glsl shows the mechanism).
// WINDOW 7
// DESC [effects] tremor: a temporal band of the blurred frames, amplified and added back (Eulerian magnification)
const float TREMOR_GAIN = 14.0;
vec3 blurred(int k) {
    vec3 s = vec3(0.0);
    for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) s += F(k, HOOKED_pos + vec2(float(i), float(j)) * 2.0 * HOOKED_pt);
    return s / 25.0;
}
vec4 hook() {
    float w1[NW], w2[NW], s1 = 0.0, s2 = 0.0;
    for (int k = 0; k < NW; k++) {
        float t = T(k);
        w1[k] = exp(-0.5 * t * t / (0.8 * 0.8)); w2[k] = exp(-0.5 * t * t / (2.5 * 2.5));
        s1 += w1[k]; s2 += w2[k];
    }
    vec3 band = vec3(0.0);
    for (int k = 0; k < NW; k++) band += (w1[k] / s1 - w2[k] / s2) * blurred(k);
    // only SMALL change is magnified: where the frame's own change across the window is already large (real motion),
    // the gain falls away, and the added signal is soft-limited, so a fast scene is left as it is rather than exploded
    float big = length(blurred(0) - blurred(NW - 1));
    for (int k = 1; k < NW; k++) big = max(big, length(F(k, HOOKED_pos) - F(0, HOOKED_pos)));
    float g = TREMOR_GAIN * (1.0 - smoothstep(0.04, 0.12, big));
    vec3 add = g * band;
    add = add / (1.0 + 4.0 * abs(add));
    return vec4(clamp(F(NOW(), HOOKED_pos) + add, 0.0, 1.0), 1.0);
}
