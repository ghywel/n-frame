// chronophotograph.glsl -- Marey's gun in a shader (2026-10-25)
//
// Etienne-Jules Marey photographed motion as a sequence of exposures on one plate. Here the window's median is the plate
// (the still world, as ghost-town.glsl), and the moving parts of the four previous frames and the current one are laid
// on it oldest first, each where it differs from the plate, the older the fainter: every mover trails its own recent
// past as a strobe of solid ghosts. Eight frames, [-4 .. +3]; the future frames vote in the plate but are not drawn.
// WINDOW 8
// DESC [effects] chronophotograph: the still plate, with the last five frames' movers laid on it as fading exposures
vec4 hook() {
    vec3 c[NW]; float y[NW];
    for (int k = 0; k < NW; k++) { c[k] = F(k, HOOKED_pos); y[k] = L(c[k]); }
    int med = 0;
    for (int i = 0; i < NW; i++) {
        int below = 0;
        for (int j = 0; j < NW; j++) if (y[j] < y[i] || (y[j] == y[i] && j < i)) below++;
        if (below == NW / 2) med = i;
    }
    vec3 o = c[med];
    for (int d = -4; d <= 0; d++) {
        for (int k = 0; k < NW; k++) {
            if (abs(T(k) - float(d)) < 0.5) {
                float m = smoothstep(0.035, 0.10, abs(y[k] - y[med]));
                float a = d == 0 ? 1.0 : 0.30 + 0.12 * float(d + 4);
                o = mix(o, c[k], m * a);
            }
        }
    }
    return vec4(o, 1.0);
}
