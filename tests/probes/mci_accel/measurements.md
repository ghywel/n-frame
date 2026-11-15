# CPU MCI exactness and timing

All-plane byte/timestamp equality; this is not an interpolation-quality claim.

| Case | Block | Mask | Threads | Exact runs |
|---|---:|---:|---:|---:|
| bars_h9 | 16 | 0 | 1 | 1 |
| bars_h9 | 16 | 1 | 1 | 1 |
| bars_h9 | 16 | 2 | 2 | 1 |
| bars_h9 | 16 | 4 | 4 | 1 |
| bars_h9 | 16 | 8 | 1 | 1 |
| bars_h9 | 16 | 15 | 4 | 1 |
| bars_v9 | 16 | 0 | 1 | 1 |
| bars_v9 | 16 | 1 | 1 | 1 |
| bars_v9 | 16 | 2 | 2 | 1 |
| bars_v9 | 16 | 4 | 4 | 1 |
| bars_v9 | 16 | 8 | 1 | 1 |
| bars_v9 | 16 | 15 | 4 | 1 |
| border420 | 4 | 1 | 2 | 1 |
| border420 | 4 | 2 | 4 | 1 |
| border420 | 4 | 4 | 2 | 1 |
| border420 | 4 | 8 | 4 | 1 |
| border420 | 4 | 15 | 1 | 1 |
| border420 | 4 | 15 | 2 | 1 |
| border420 | 4 | 15 | 4 | 1 |
| border420 | 8 | 1 | 2 | 1 |
| border420 | 8 | 2 | 4 | 1 |
| border420 | 8 | 4 | 2 | 1 |
| border420 | 8 | 8 | 4 | 1 |
| border420 | 8 | 15 | 1 | 1 |
| border420 | 8 | 15 | 2 | 1 |
| border420 | 8 | 15 | 4 | 1 |
| border420 | 16 | 0 | 1 | 1 |
| border420 | 16 | 1 | 1 | 1 |
| border420 | 16 | 1 | 2 | 1 |
| border420 | 16 | 2 | 2 | 1 |
| border420 | 16 | 2 | 4 | 1 |
| border420 | 16 | 4 | 2 | 1 |
| border420 | 16 | 4 | 4 | 1 |
| border420 | 16 | 8 | 1 | 1 |
| border420 | 16 | 8 | 4 | 1 |
| border420 | 16 | 15 | 1 | 4 |
| border420 | 16 | 15 | 2 | 4 |
| border420 | 16 | 15 | 4 | 5 |
| border444 | 4 | 1 | 2 | 1 |
| border444 | 4 | 2 | 4 | 1 |
| border444 | 4 | 4 | 2 | 1 |
| border444 | 4 | 8 | 4 | 1 |
| border444 | 4 | 15 | 1 | 1 |
| border444 | 4 | 15 | 2 | 1 |
| border444 | 4 | 15 | 4 | 1 |
| border444 | 8 | 1 | 2 | 1 |
| border444 | 8 | 2 | 4 | 1 |
| border444 | 8 | 4 | 2 | 1 |
| border444 | 8 | 8 | 4 | 1 |
| border444 | 8 | 15 | 1 | 1 |
| border444 | 8 | 15 | 2 | 1 |
| border444 | 8 | 15 | 4 | 1 |
| border444 | 16 | 0 | 1 | 1 |
| border444 | 16 | 1 | 1 | 1 |
| border444 | 16 | 1 | 2 | 1 |
| border444 | 16 | 2 | 2 | 1 |
| border444 | 16 | 2 | 4 | 1 |
| border444 | 16 | 4 | 2 | 1 |
| border444 | 16 | 4 | 4 | 1 |
| border444 | 16 | 8 | 1 | 1 |
| border444 | 16 | 8 | 4 | 1 |
| border444 | 16 | 15 | 1 | 4 |
| border444 | 16 | 15 | 2 | 4 |
| border444 | 16 | 15 | 4 | 5 |
| cut | 16 | 0 | 1 | 1 |
| cut | 16 | 1 | 1 | 1 |
| cut | 16 | 2 | 2 | 1 |
| cut | 16 | 4 | 4 | 1 |
| cut | 16 | 8 | 1 | 1 |
| cut | 16 | 15 | 4 | 1 |
| face_occluded | 16 | 0 | 1 | 1 |
| face_occluded | 16 | 1 | 1 | 1 |
| face_occluded | 16 | 2 | 2 | 1 |
| face_occluded | 16 | 4 | 4 | 1 |
| face_occluded | 16 | 8 | 1 | 1 |
| face_occluded | 16 | 15 | 4 | 1 |
| pan43 | 16 | 0 | 1 | 1 |
| pan43 | 16 | 1 | 1 | 1 |
| pan43 | 16 | 2 | 2 | 1 |
| pan43 | 16 | 4 | 4 | 1 |
| pan43 | 16 | 8 | 1 | 1 |
| pan43 | 16 | 15 | 4 | 1 |
| pan43_60 | 16 | 0 | 1 | 1 |
| pan43_60 | 16 | 1 | 1 | 1 |
| pan43_60 | 16 | 2 | 2 | 1 |
| pan43_60 | 16 | 4 | 4 | 1 |
| pan43_60 | 16 | 8 | 1 | 1 |
| pan43_60 | 16 | 15 | 1 | 3 |
| pan43_60 | 16 | 15 | 2 | 3 |
| pan43_60 | 16 | 15 | 4 | 4 |
| rigid_frozen | 16 | 0 | 1 | 1 |
| rigid_frozen | 16 | 1 | 1 | 1 |
| rigid_frozen | 16 | 2 | 2 | 1 |
| rigid_frozen | 16 | 4 | 4 | 1 |
| rigid_frozen | 16 | 8 | 1 | 1 |
| rigid_frozen | 16 | 15 | 4 | 1 |
| rigid_grain | 16 | 0 | 1 | 1 |
| rigid_grain | 16 | 1 | 1 | 1 |
| rigid_grain | 16 | 2 | 2 | 1 |
| rigid_grain | 16 | 4 | 4 | 1 |
| rigid_grain | 16 | 8 | 1 | 1 |
| rigid_grain | 16 | 15 | 4 | 1 |
| shirt | 16 | 0 | 4 | 1 |
| shirt | 16 | 15 | 1 | 1 |
| shirt | 16 | 15 | 4 | 1 |
| static | 16 | 0 | 1 | 1 |
| static | 16 | 1 | 1 | 1 |
| static | 16 | 2 | 2 | 1 |
| static | 16 | 4 | 4 | 1 |
| static | 16 | 8 | 1 | 1 |
| static | 16 | 15 | 4 | 1 |
| suit | 16 | 0 | 4 | 1 |
| suit | 16 | 15 | 1 | 1 |
| suit | 16 | 15 | 4 | 1 |

| Case | Block | Mask / threads | Baseline s | Candidate s | Speedup | Candidate ME / overlap / output ms |
|---|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 15 / 4 | 23.6656 | 10.6953 | 2.213x | 343.04 / 8534.79 / 1703.01 |
| suit | 16 | 15 / 4 | 28.3870 | 12.7264 | 2.231x | 422.67 / 10156.10 / 2020.39 |

Times are warmed interleaved process medians, with a consistent framemd5 sink. Stage wall times are not CPU time.
