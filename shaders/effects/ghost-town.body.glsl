// ghost-town.glsl -- what stays (2026-10-25)
//
// Every pixel takes the MEDIAN of its seven values across the window [-3 .. +3], ranked by brightness and kept whole in
// colour. Anything that moves across a pixel in under half the window -- a passer-by, a car, a bird, rain -- is outvoted
// by the background it crosses and vanishes; what stays still stays. An N:N filter: ffmpeg -i in -vf
// libplacebo=fps=source_fps:frame_mixer=custom_n:custom_shader_path=ghost-town.glsl. GHOST_MOVERS = 1 inverts it: the
// still world greyed and dimmed, only what differs from it in colour.
// WINDOW 7
// DESC [effects] ghost town: the window's median, so whatever moves within seven frames vanishes
const int GHOST_MOVERS = 0;
vec4 hook() {
    vec3 c[NW]; float y[NW];
    for (int k = 0; k < NW; k++) { c[k] = F(k, HOOKED_pos); y[k] = L(c[k]); }
    int med = 0;
    for (int i = 0; i < NW; i++) {
        int below = 0;
        for (int j = 0; j < NW; j++) if (y[j] < y[i] || (y[j] == y[i] && j < i)) below++;
        if (below == NW / 2) med = i;
    }
    if (GHOST_MOVERS == 0) return vec4(c[med], 1.0);
    vec3 now = c[NOW()];
    float m = smoothstep(0.03, 0.09, abs(L(now) - y[med]));
    return vec4(mix(vec3(0.25 * L(now)), now, m), 1.0);
}
