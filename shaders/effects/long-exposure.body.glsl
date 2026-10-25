// long-exposure.glsl -- an exposure as long as you like (2026-10-25)
//
// The window holds eight frames, but a STORAGE texture persists between calls, so a shader can keep any history it
// can fold into a texture. Here it keeps a running exposure, updated once per source frame (pair_changed): LIGHT_PAINT
// keeps each pixel's brightest recent colour, decaying by EXPOSURE_DECAY a frame, so lights draw comet trails and a
// sparkler writes; otherwise a shutter drag, each frame mixed in at 1 - EXPOSURE_DECAY, so movement smears like a slow
// photograph while the still world stays sharp. One frame is enough for the mechanism; the cache is sized for 4K.
// WINDOW 2
// DESC [effects] long exposure: a running exposure kept in a storage texture across frames (light painting or shutter drag)
// TEXTURE EXPOSURE 3840 2160 rgba16f
// BIND EXPOSURE
const int LIGHT_PAINT = 1;
const float EXPOSURE_DECAY = 0.94;
vec4 hook() {
    ivec2 px = ivec2(HOOKED_pos * HOOKED_size);
    vec3 now = F(NOW(), HOOKED_pos);
    vec3 acc = imageLoad(EXPOSURE, px).rgb;
    if (!pair_changed) return vec4(acc, 1.0);
    vec3 o = LIGHT_PAINT == 1 ? max(acc * EXPOSURE_DECAY, now) : mix(now, acc, EXPOSURE_DECAY);
    if (acc == vec3(0.0)) o = now;
    imageStore(EXPOSURE, px, vec4(o, 1.0));
    return vec4(o, 1.0);
}
