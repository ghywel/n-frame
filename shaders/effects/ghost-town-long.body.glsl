// ghost-town-long.glsl -- what stays, over three seconds (2026-10-25)
//
// ghost-town.glsl's median sees only its seven-frame window (a third of a second), so only fast movers vanish. A window
// is not the limit of what a hook can remember: this one keeps a ring of 12 past frames in one STORAGE texture (4 x 3 tiles: a pass may bind 16 textures), one written
// every 6th source frame (72 frames, three seconds at 24 fps), counted by a one-texel counter in a pass of its own (so every pixel reads the same count), and takes each
// pixel's median over the ring and the window together. Anything that crosses a pixel in under about a second and a half
// is outvoted by the background and vanishes: people walk out of a street. The first three seconds are the ring
// filling. Sized for frames up to 1920 x 1080 (the ring textures' fixed size).
// WINDOW 7
// DESC [effects] ghost town, long: the median over a 12-frame ring kept in storage textures (72 frames) and the window
// TEXTURE GHOST_COUNT 1 1 rgba32f
// BIND GHOST_N
// TEXTURE GHOST_RING 7680 3240 rgba16f
// BIND GHOST_RING
// PREPASS BEGIN
//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND GHOST_COUNT
//!SAVE GHOST_N
//!WIDTH 1
//!HEIGHT 1
//!COMPONENTS 1
//!DESC [effects] ghost town, long: the count of source frames seen, one texel, advanced once per source frame
vec4 hook() {
    float n = imageLoad(GHOST_COUNT, ivec2(0)).r;
    if (pair_changed) imageStore(GHOST_COUNT, ivec2(0), vec4(n + 1.0));
    return vec4(n);
}
// PREPASS END
const int RING = 12;
const int RING_STEP = 6;
ivec2 SLOT(int k, ivec2 px) { return px + ivec2((k % 4) * 1920, (k / 4) * 1080); }   // 4 x 3 tiles
vec3 R(int k, ivec2 px) { return imageLoad(GHOST_RING, SLOT(k, px)).rgb; }
vec4 hook() {
    ivec2 px = ivec2(HOOKED_pos * HOOKED_size);
    vec3 now = F(NOW(), HOOKED_pos);
    float n = GHOST_N_tex(vec2(0.5)).r;                              // source frames seen before this one (the pre-pass)
    int filled = int(min(floor(n / float(RING_STEP)), float(RING)));
    vec3 c[RING + NW]; float y[RING + NW]; int m = 0;
    for (int k = 0; k < NW; k++) { c[m] = F(k, HOOKED_pos); y[m] = L(c[m]); m++; }
    for (int k = 0; k < RING; k++) if (k < filled) { c[m] = R(k, px); y[m] = L(c[m]); m++; }
    int med = 0;
    for (int i = 0; i < RING + NW; i++) {
        if (i >= m) break;
        int below = 0;
        for (int j = 0; j < RING + NW; j++) if (j < m && (y[j] < y[i] || (y[j] == y[i] && j < i))) below++;
        if (below == m / 2) med = i;
    }
    if (pair_changed) {
        int fi = int(n);
        if (fi % RING_STEP == 0) {
            int slot = (fi / RING_STEP) % RING;
            imageStore(GHOST_RING, SLOT(slot, px), vec4(now, 1.0));
        }
    }
    return vec4(c[med], 1.0);
}
