# The REGION of every ladder case: a static crop covering the object's whole swept path over the clip, plus a 16 px
# margin, derived from the scene's motion law in scenes.sh (2026-10-21, the swarm's instruments lane, item 2).
# Sourced, not run.
#
#   region_crop <case>      ->  "crop=W:H:X:Y" (ffmpeg crop syntax), or "" for a case with no region here
#
# WHY. bench.sh scores a whole frame, and the mover is a small part of it: measured on source frames 2 and 4 of every
# case (np-scratch/swarm-20261021/instruments/share.txt), the moving band is under 3 percent of the frame on 22 of the
# 42 cases, so a defect confined to the mover is understated by 15-25 dB in the frame mean (10 log10(1 / share)); with
# the 40 dB cap that makes a 20 dB fault on L1's box read as 42.5 dB, above the cap, and count for nothing. Scoring the
# same frames over the swept path removes most of that dilution without a per-frame mask: cage.sh (probes/cage) did
# this for C1-C3 with a static crop, and this file is that choice for every case. The dilution that remains is the
# swept path's own share of the crop (an object of width w moving d px fills w / (w + d) of its path).
#
# HOW EACH CROP IS DERIVED. The clip is one second (d=1 in every scene), T is time in seconds, so t runs over [0, 1).
# For a rectangle x0(t), y0(t), w, h the swept path is [min x0, max x0 + w) x [min y0, max y0 + h) over t in [0, 1]
# (the closed interval: a bound, not a sample). Then 16 px of margin on every side, clipped to the 1280x720 frame,
# and every edge rounded OUT to an even pixel, because the frames are yuv420p and a crop on an odd offset would shift
# the chroma plane under the luma it is scored with. The tables below give, per case, the law, the swept range, and
# the crop, so a reader can check any row by hand. Format: crop=W:H:X:Y.
#
# STATED CHOICES, for the cases where "the object" needs a word:
#   L0_static       the object does not move; the region is its box plus the margin: the one place anything but a
#                   passthrough could show (hold is inf on it, as on the whole frame).
#   L6_flat_large   a flat interior: every error lives on its four edges, but the box is where the mechanism lives
#   O4_osc_flat300  (the edge is the signal), so the region is the swept box as for its textured twins L7/M1/M2/M3
#                   and O5. A tighter edge band would be a second instrument, not this one.
#   M4_belowgate    the contrast gate's own case: the box is where the gate's decision shows; same rule.
#   L9, P4          two movers: the union of both swept paths (the occlusion happens where they overlap).
#   F1/F2, R1-R3    the Fourier blob reaches R * 1.2924 = 193.9 px from its centre at the furthest lobe (scenes.sh,
#                   "Centred at 200, not L6's 150"); its boundary is band-limited to ~2 px, inside the margin.
# Scenes NOT in ALL_CASES or LADDER2_CASES whose mover fills the frame (scene_edge's W1-W3, C1-C3, B1, K1-K3,
# E1-E4): a region column is not the instrument for a frame-filling mover (its crop would be the frame, and the
# column would repeat the whole-frame one). Entries are given for them as documentation and so that bench.sh does not
# fail if one is scored through this table: W3, C1, C3 get the whole frame, stated as such; W1/W2 the static subject's
# box plus the 48 px the warp can spread (READ_GATE's reach); K1-K3 the limb's swept path; B1 the patch's; C2 the
# cage's rectangle as cage.sh had it; E1-E4 the box's swept path.
#
# The 16 px margin: the final warp's error lands within the flow's spread past a mover, which the reading tail's gate
# measured at 2 texels of 1/8 res = 16 px (add_human_reading.py, READ_GATE_R). A warp error further out than that
# is a background fault and belongs to the whole-frame column.

region_crop() {
  case "$1" in
    # ---- the frozen 42 (ALL_CASES) --------------------------------------------------------------------------
    # 100x100 boxes at y 310..410 -> y 294..426 (h 132)
    L0_static)          echo "crop=132:132:384:294" ;;   # x0 400, static: x 400..500 -> 384..516
    L1_trans_8px)       echo "crop=308:132:0:294" ;;     # x0 = 192 t: x 0..292 -> 0..308 (left edge clipped at 0)
    L2_trans_16px)      echo "crop=500:132:0:294" ;;     # x0 = 384 t: x 0..484 -> 0..500
    L3_trans_23px)      echo "crop=668:132:0:294" ;;     # x0 = 552 t: x 0..652 -> 0..668
    L4_trans_40px)      echo "crop=1076:132:0:294" ;;    # x0 = 960 t: x 0..1060 -> 0..1076
    L5_lowcontrast)     echo "crop=500:132:0:294" ;;     # L2's motion
    A1_accel_8mean)     echo "crop=308:132:0:294" ;;     # x0 = 192 t^2: same start and end as L1
    A2_accel_16mean)    echo "crop=500:132:0:294" ;;     # x0 = 384 t^2: as L2
    A3_accel_23mean)    echo "crop=668:132:0:294" ;;     # x0 = 552 t^2: as L3
    O1_osc_gentle)      echo "crop=212:132:544:294" ;;   # x0 = 600 + 40 sin: x 560..740 -> 544..756
    O2_osc_medium)      echo "crop=172:132:564:294" ;;   # x0 = 600 + 20 sin: x 580..720 -> 564..736
    O3_osc_hard)        echo "crop=156:132:572:294" ;;   # x0 = 600 + 12 sin: x 588..712 -> 572..728
    L8_diagonal)        echo "crop=500:332:0:0" ;;       # x0 = 384 t, y0 = 216 t: x 0..484, y 0..316 -> 0..500, 0..332
    L9_occlusion)       echo "crop=732:132:284:294" ;;   # A x0 = 300 + 300 t (300..700), B x0 = 900 - 300 t (600..1000): union 300..1000 -> 284..1016
    # 300x300 boxes at y 210..510 -> y 194..526 (h 332)
    L6_flat_large)      echo "crop=700:332:0:194" ;;     # x0 = 384 t: x 0..684 -> 0..700
    L7_textured_large)  echo "crop=700:332:0:194" ;;
    M1_noise_large)     echo "crop=700:332:0:194" ;;
    M2_period40)        echo "crop=700:332:0:194" ;;
    M3_period16_trap)   echo "crop=700:332:0:194" ;;
    M4_belowgate)       echo "crop=700:332:0:194" ;;
    O4_osc_flat300)     echo "crop=372:332:564:194" ;;   # x0 = 600 + 20 sin: x 580..920 -> 564..936
    O5_osc_textured)    echo "crop=372:332:564:194" ;;
    O6_osc_tex_gentle)  echo "crop=412:332:544:194" ;;   # x0 = 600 + 40 sin: x 560..940 -> 544..956
    A4_accel_tex_a033)  echo "crop=356:332:360:194" ;;   # x0 = 400 - 96 t + 96 t^2: min 376 at t = 1/2, 400 at both ends: x 376..700 -> 360..716
    A5_accel_tex_a067)  echo "crop=380:332:336:194" ;;   # x0 = 400 - 192 t + 192 t^2: min 352: x 352..700 -> 336..716
    A6_accel_tex_a133)  echo "crop=428:332:288:194" ;;   # x0 = 400 - 384 t + 384 t^2: min 304: x 304..700 -> 288..716
    A7_accel_tex_a167)  echo "crop=452:332:264:194" ;;   # x0 = 400 - 480 t + 480 t^2: min 280: x 280..700 -> 264..716
    H1_bars_sine24_h6)  echo "crop=476:332:84:194" ;;    # x0 = 100 + 144 t: x 100..544 -> 84..560
    H2_stairs_sq24_h6)  echo "crop=476:332:84:194" ;;
    V1_bars_sine24_v6)  echo "crop=332:476:474:84" ;;    # x 490..790 -> 474..806; y0 = 100 + 144 t: y 100..544 -> 84..560
    V2_stairs_sq24_v6)  echo "crop=332:476:474:84" ;;
    V3_stairs_sq24_v12) echo "crop=332:620:474:84" ;;    # y0 = 100 + 288 t: y 100..688 -> 84..704
    # the stairs along their bars: 600x300 boxes at y 210..510
    P1_stairs_along_v4)         echo "crop=728:332:84:194" ;;    # x0 = 100 + 96 t: x 100..796 -> 84..812
    P2_stairs_along_v8)         echo "crop=824:332:84:194" ;;    # x0 = 100 + 192 t: x 100..892 -> 84..908
    P5_stairs_along_v8_alias)   echo "crop=824:332:84:194" ;;
    P3_stairs_along_v12)        echo "crop=920:332:84:194" ;;    # x0 = 100 + 288 t: x 100..988 -> 84..1004
    P4_stairs_along_v8_crosser) echo "crop=992:432:84:144" ;;    # stairs 100..892 (y 210..510) + crosser x0 = 900 - 192 t, 160 wide (708..1060, y 160..560): union x 100..1060 -> 84..1076, y 160..560 -> 144..576
    # the Fourier blob, R 150, furthest lobe 193.9 px from the centre; y centre 360: y 166..554 -> 150..570 (h 420)
    F1_fourier_edge)    echo "crop=794:420:0:150" ;;     # cx = 200 + 384 t: x 6..778 -> 0..794 (left edge clipped at 0)
    F2_fourier_accel)   echo "crop=794:420:0:150" ;;     # cx = 200 + 384 t^2: same range
    R1_rot_const)       echo "crop=420:420:430:150" ;;   # cx 640 fixed: x 446..834 -> 430..850 (the blob turns in place)
    R2_rot_accel)       echo "crop=420:420:430:150" ;;
    R3_rot_tex)         echo "crop=420:420:430:150" ;;
    # ---- LADDER2 (2026-10-21) ------------------------------------------------------------------------------
    V2x_stairs_cov_v6)  echo "crop=332:476:474:84" ;;    # V2's motion
    V3x_stairs_cov_v12) echo "crop=332:620:474:84" ;;    # V3's motion
    H2x_stairs_cov_h6)  echo "crop=476:332:84:194" ;;    # H2's motion
    M1c_noise_v6)       echo "crop=460:332:0:194" ;;     # x0 = 144 t: x 0..444 -> 0..460
    M2c_period40_v6)    echo "crop=460:332:0:194" ;;
    M1c_noise_v10)      echo "crop=556:332:0:194" ;;     # x0 = 240 t: x 0..540 -> 0..556
    M2c_period40_v10)   echo "crop=556:332:0:194" ;;
    M1c_noise_v12)      echo "crop=604:332:0:194" ;;     # x0 = 288 t: x 0..588 -> 0..604
    L8t_diagonal_tex)   echo "crop=524:524:84:84" ;;     # 300x300 box, x0 = y0 = 100 + 192 t: x and y 100..592 -> 84..608
    L9b_occlusion_mid)  echo "crop=532:132:284:294" ;;   # 200x100 boxes: A x0 = 300 + 300 t (300..600, right edge to 800), B x0 = 600 - 300 t (300..600): union x 300..800 -> 284..816; y 310..410 -> 294..426
    R3i_rot_isotropic)  echo "crop=420:420:430:150" ;;   # R3's blob, cx 640 fixed: as R1-R3
    # D1 (2026-10-22): the window is STILL at x 490..790, y 210..510 (the print drifts behind it, and nothing outside the
    # window ever changes), so the swept path is the window itself: 490..790 -> 474..806, 210..510 -> 194..526 (w = h = 332).
    # The 16 px margin is black on every frame and exactly right in every mode; it dilutes the window's own error by
    # 10 log10(332^2 / 300^2) = 0.9 dB, the same for every row of the table.
    D1_print_behind_window_ramp)  echo "crop=332:332:474:194" ;;
    D1h_print_behind_window_v12)  echo "crop=332:332:474:194" ;;
    # ---- field scenes in scenes.sh but in neither list (so bench.sh can score one through the table) ----------
    O7_osc_fast_small)  echo "crop=144:132:578:294" ;;   # x0 = 600 + 6 sin: x 594..706 -> 578..722
    O8_osc_fast_tiny)   echo "crop=140:132:580:294" ;;   # x0 = 600 + 4 sin: x 596..704 -> 580..720
    O9_osc_tex_fast)    echo "crop=344:332:578:194" ;;   # x 594..906 -> 578..922
    O10_osc_tex_tiny)   echo "crop=340:332:580:194" ;;   # x 596..904 -> 580..920
    # ---- scene_edge's cases, documentation (see the header: a frame-filling mover has no region) -------------
    E1_edge_on_texture) echo "crop=700:332:0:194" ;;     # 300x300 box, x = 384 t, y 210: as L6
    E2_cartoon_edge)    echo "crop=676:292:0:214" ;;     # 260x260 box, x = 384 t, y 230: x 0..644 -> 0..676, y 230..490 -> 214..506
    E3_opposing)        echo "crop=612:432:424:144" ;;   # 200x400 boxes: left x 440..640+192 (440..832), right 640-192..840 (448..840): union 440..840 -> 424..856, y 160..560 -> 144..576
    E4_thin_lines)      echo "crop=700:332:0:194" ;;     # as E1
    W1_wall_pan_ramp)   echo "crop=396:516:442:102" ;;   # the static subject 490..790 x 150..570 plus 48 px (the warp's spread): 442..838, 102..618; the wall is the frame
    W2_wall_pan_ramp_multiscale) echo "crop=396:516:442:102" ;;
    W3_wall_pan_ramp_alone) echo "crop=1280:720:0:0" ;;  # the wall alone fills the frame: the region IS the frame (the column repeats the whole-frame one)
    K1_limb_sweep_wall) echo "crop=944:232:84:244" ;;    # 48x200 limb, x0 = 100 + 288 t + 576 t^2: x 100..1012 -> 84..1028; y 260..460 -> 244..476 (limb.sh's following box is the finer instrument)
    K2_limb_sweep_dark) echo "crop=944:232:84:244" ;;
    K3_limb_sweep_wall_bright) echo "crop=944:232:84:244" ;;
    B1_alias_over_pan)  echo "crop=232:520:474:84" ;;    # 200x200 patch at x 490 (one second): x 474..706; y0 = 100 + 288 t: y 100..588 -> 84..604
    C1_cage_drift)      echo "crop=1280:720:0:0" ;;      # the whole scene drifts: the region is the frame (cage.sh scores the cage's own rectangle, 520:360:390:145)
    C2_cage_drift_occluded) echo "crop=520:360:390:145" ;;   # cage.sh's rectangle: the cage behind the figure, as the record scored it
    C3_bars_spin_drift) echo "crop=650:630:340:60" ;;    # cage.sh's disc
    *) echo "" ;;
  esac
}
