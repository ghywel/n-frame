// pulfrich.glsl -- 3D from a pan, with red/cyan glasses (2026-10-25)
//
// The Pulfrich effect: delay one eye's view and lateral motion becomes depth, because a moving thing is then seen in two
// places at once and the brain reads the offset as disparity. The left eye (red) sees the current frame, the right eye
// (cyan) the frame PULFRICH_DELAY earlier: in a camera pan the near world moves faster than the far, so it separates
// more and stands out of the screen. Direction matters: a pan one way gives depth, the other way inverts it (swap the
// glasses). Five frames, [-2 .. +2].
// WINDOW 5
// DESC [effects] pulfrich: red eye now, cyan eye two frames ago, so lateral motion reads as depth
const float PULFRICH_DELAY = 2.0;
vec4 hook() {
    vec3 now = F(NOW(), HOOKED_pos), late = now;
    for (int k = 0; k < NW; k++) if (abs(T(k) + PULFRICH_DELAY) < 0.5) late = F(k, HOOKED_pos);
    return vec4(now.r, late.g, late.b, 1.0);
}
