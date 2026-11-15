#!/usr/bin/env python3
"""Add optional stage wall timers to pinned stock minterpolate; no arithmetic change.

profile.py FFMPEG_SOURCE
Writes only vf_minterpolate.c in an isolated checkout. Enable mci_profile=1 in
the filter to report accumulated ME / overlap / output time on destruction.
"""
import hashlib
from pathlib import Path
import sys

EXPECTED='42e776a33821d7e08a20371a554513bca17ee427aac123ec0923bc4cbefad8e7'


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('unexpected source anchor: '+old[:90])
    return text.replace(old,new)


def add(text):
    if hashlib.sha256(text.encode()).hexdigest()!=EXPECTED:
        raise ValueError('requires stock vf_minterpolate.c at FFmpeg 3a5eb94')
    text=once(text,'#include "motion_estimation.h"',
              '#include <inttypes.h>\n#include "libavutil/time.h"\n#include "motion_estimation.h"')
    text=once(text,'    int vsbmc;\n','    int vsbmc;\n    int mci_profile;\n    int64_t profile_me_us, profile_overlap_us, profile_output_us;\n    int profile_pairs, profile_draws;\n')
    text=once(text,'    { "vsbmc",',
              '    { "mci_profile", "report bidir stage wall times", OFFSET(mci_profile), AV_OPT_TYPE_BOOL, {.i64 = 0}, 0, 1, FLAGS },\n    { "vsbmc",')
    text=once(text,'        if (mi_ctx->me_mode == ME_MODE_BIDIR) {\n\n            if (mi_ctx->frames[1].avf) {',
              '        if (mi_ctx->me_mode == ME_MODE_BIDIR) {\n            int64_t profile_start = mi_ctx->mci_profile ? av_gettime_relative() : 0;\n\n            if (mi_ctx->frames[1].avf) {')
    text=once(text,'\n        } else if (mi_ctx->me_mode == ME_MODE_BILAT) {\n            Block *block;',
              '\n            if (mi_ctx->mci_profile && mi_ctx->frames[1].avf) {\n                mi_ctx->profile_me_us += av_gettime_relative() - profile_start;\n                mi_ctx->profile_pairs++;\n            }\n        } else if (mi_ctx->me_mode == ME_MODE_BILAT) {\n            Block *block;')
    text=once(text,'                bidirectional_obmc(mi_ctx, alpha);\n                set_frame_data(mi_ctx, alpha, avf_out);',
              '''                int64_t profile_start = mi_ctx->mci_profile ? av_gettime_relative() : 0;
                bidirectional_obmc(mi_ctx, alpha);
                if (mi_ctx->mci_profile) {
                    mi_ctx->profile_overlap_us += av_gettime_relative() - profile_start;
                    profile_start = av_gettime_relative();
                }
                set_frame_data(mi_ctx, alpha, avf_out);
                if (mi_ctx->mci_profile) {
                    mi_ctx->profile_output_us += av_gettime_relative() - profile_start;
                    mi_ctx->profile_draws++;
                }''')
    text=once(text,'    int i, m;\n\n    av_freep(&mi_ctx->pixel_mvs);',
              '''    int i, m;

    if (mi_ctx->mci_profile)
        av_log(ctx, AV_LOG_INFO, "MCI_PROFILE pairs=%d draws=%d me_us=%"PRId64" overlap_us=%"PRId64" output_us=%"PRId64"\\n",
               mi_ctx->profile_pairs, mi_ctx->profile_draws, mi_ctx->profile_me_us,
               mi_ctx->profile_overlap_us, mi_ctx->profile_output_us);
    av_freep(&mi_ctx->pixel_mvs);''')
    return text


if __name__=='__main__':
    p=Path(sys.argv[1])/'libavfilter/vf_minterpolate.c'
    p.write_text(add(p.read_text()))
