// spectrum.glsl -- what is oscillating, and how fast (2026-10-25)
//
// Each pixel's brightness over the eight frames [-4 .. +3] is a short signal; its discrete Fourier transform at 1, 2, 3
// and 4 cycles per window (3, 6, 9 and 12 Hz at 24 fps) says how much of the change is slow and how much is fast. The
// picture is greyed and dimmed; over it, colour shows the change's energy (brightness) and its frequency (hue: red the
// slowest, through yellow and green, to violet at the fastest a 24 fps camera can see). A swaying branch glows red, a
// flickering light or a vibrating string violet. Each pixel's straight-line trend is removed first, so a steady
// pan or slide stays dark: only what goes back and forth lights up.
// WINDOW 8
// DESC [effects] spectrum: each pixel's temporal Fourier energy over eight frames, hue the frequency
const float SPECTRUM_GAIN = 5.0;
vec3 hue(float h) { return clamp(abs(fract(h + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0); }
vec4 hook() {
    float y[NW], t[NW], mean = 0.0;
    for (int k = 0; k < NW; k++) { y[k] = L(F(k, HOOKED_pos)); t[k] = T(k); mean += y[k]; }
    mean /= float(NW);
    // remove the straight line through the samples: a steady drift (most of a pan or a slide) is a trend, not an
    // oscillation, and would otherwise light up every moving edge
    float st = 0.0, stt = 0.0, sty = 0.0;
    for (int k = 0; k < NW; k++) { st += t[k]; stt += t[k] * t[k]; sty += t[k] * (y[k] - mean); }
    float tm = st / float(NW), slope = sty / max(stt - float(NW) * tm * tm, 1e-6);
    for (int k = 0; k < NW; k++) y[k] -= slope * (t[k] - tm);
    float e = 0.0, fe = 0.0;
    for (int f = 1; f <= 4; f++) {
        float re = 0.0, im = 0.0;
        for (int k = 0; k < NW; k++) {
            float a = 6.2831853 * float(f) * t[k] / 8.0;
            re += (y[k] - mean) * cos(a); im += (y[k] - mean) * sin(a);
        }
        float p = (re * re + im * im) / float(NW * NW) * (f == 4 ? 1.0 : 2.0);
        e += p; fe += p * float(f);
    }
    float fbar = e > 0.0 ? fe / e : 1.0;                       // 1 .. 4
    float v = clamp(sqrt(e) * SPECTRUM_GAIN, 0.0, 1.0);
    vec3 base = vec3(0.30 * L(F(NOW(), HOOKED_pos)));
    return vec4(base * (1.0 - v) + hue((fbar - 1.0) / 3.0 * 0.78) * v, 1.0);
}
