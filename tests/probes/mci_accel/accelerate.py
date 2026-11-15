#!/usr/bin/env python3
"""Generate a bounded minterpolate acceleration patch without editing FFmpeg.

    python tests/probes/mci_accel/accelerate.py --source /path/to/ffmpeg --out /tmp/mci-patch

Outputs: accelerate.patch, manifest.json, sad_control.c, and patched files under
tree/. Apply the patch explicitly only after the unmodified baseline is built.
Exact anchors fail closed on unexpected source changes. Profiling additions
outside the replaced loops are retained, and every input/output file is hashed.

The filter option mci_accel is an initialization-time integer bitmask, default 0:
  1: cached pixelutils SIMD SAD, bidirectional estimation only;
  2: two independent direction jobs, bidirectional EPZS only;
  4: chroma-aligned output row jobs, bidirectional synthesis only;
  8: evaluate only the last full-resolution representative of each chroma pixel.
Bits 4 and 8 combine but also work independently. No OBMC scatter is threaded.
There is no process_command handler and no claim of per-frame option mutation.

Validation checklist (PLAN.md/GATE.md define the bounded measured matrix;
the broader items below remain deployment follow-ups unless RESULTS.md records
their execution, and must not be implied by a subset speed claim):
* Compile/run emitted sad_control.c against the patched build's libavutil. It
  compares the actual old/new cost functions, including clipping and predictor
  penalty, for all supported block sizes, offsets, unequal strides, extremes,
  and deterministic random data. Example from the patched FFmpeg build root:
      cc -O2 -I. /tmp/mci-patch/sad_control.c libavutil/libavutil.a -lm \
          -o /tmp/mci-patch/sad_control
  Add platform link libraries if required by that build configuration.
* Compare masks 0,1,2,4,8,3,12,15 to the untouched binary, including full decoded
  YUV hashes, output count/PTS, and instrumented per-frame vectors. Repeat at
  filter_threads=1,2,4; one thread must still process both directions.
* Include flat/repeating textures (tie order), cuts, large +/- translations,
  clipped boundaries, startup/tail, mb_size=4/8/16, odd dimensions, 410/411/420/
  422/440/444/gray/alpha formats, and crowded OBMC overlaps above the 32-ref cap.
* Byte-compare mask0 and inactive bilateral/dup/blend paths separately. Check
  output bytes rather than compressed-file hashes; container metadata can vary.

Hazards deliberately preserved: strict first-minimum search ties, row-major
left/top/top-right predictor dependencies, pre-clamp displacement penalty, C
signed division for negative chroma displacement, first-32 OBMC references,
and the old final-row/column OBMC clipping. Luma initializes fallback references
before chroma in each owned row range; skipped chroma visits therefore have no
remaining side effects. The old get_sad_ob and set_frame_data stay verbatim.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess


FILES = ("libavfilter/vf_minterpolate.c", "libavfilter/motion_estimation.h", "configure")
BASE_COMMIT = "3a5eb948e76dc6390e4b3cff7becf84bc492b7af"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected one anchor, found {count}: {old[:110]!r}")
    return text.replace(old, new, 1)


def function_between(text: str, start: str, following: str) -> str:
    if text.count(start) != 1 or text.count(following) != 1:
        raise ValueError(f"ambiguous function boundaries: {start!r}, {following!r}")
    a, b = text.index(start), text.index(following)
    if b <= a:
        raise ValueError("reversed function boundaries")
    return text[a:b]


SAD_LOOP = """    for (j = -me_ctx->mb_size / 2; j < me_ctx->mb_size * 3 / 2; j++)
        for (i = -me_ctx->mb_size / 2; i < me_ctx->mb_size * 3 / 2; i++)
            sad += FFABS(data_ref[x_mv + i + (y_mv + j) * linesize_ref] - data_cur[x + i + (y + j) * linesize_cur]);
"""

SAD_SIMD = """    /* Keep the original clipped windows and the pre-clip displacement penalty. */
    sad = me_ctx->mc_sad(data_cur + x - me_ctx->mb_size / 2 +
                        (y - me_ctx->mb_size / 2) * linesize_cur, linesize_cur,
                        data_ref + x_mv - me_ctx->mb_size / 2 +
                        (y_mv - me_ctx->mb_size / 2) * linesize_ref, linesize_ref);
"""


def add_simd(vf: str, header: str, configure: str) -> tuple[str, str, str]:
    header = replace_once(header, '#include <stdint.h>\n',
                          '#include <stdint.h>\n#include "libavutil/pixelutils.h"\n')
    header = replace_once(header, "    AVMotionEstPredictor preds[2];\n",
                          "    AVMotionEstPredictor preds[2];\n"
                          "    av_pixelutils_sad_fn mc_sad; ///< optional overlapped block SAD\n")
    configure = replace_once(configure, 'minterpolate_filter_select="scene_sad"',
                             'minterpolate_filter_select="scene_sad pixelutils"')
    old = function_between(vf, "static uint64_t get_sad_ob(", "static int config_input(")
    simd = replace_once(old, "static uint64_t get_sad_ob(", "static uint64_t get_sad_ob_simd(")
    simd = replace_once(simd, "    int i, j;\n", "")
    simd = replace_once(simd, SAD_LOOP, SAD_SIMD)
    vf = replace_once(vf, old, old + simd)
    vf = replace_once(vf,
        """        if (mi_ctx->me_mode == ME_MODE_BIDIR)
            me_ctx->get_cost = &get_sad_ob;
        else if (mi_ctx->me_mode == ME_MODE_BILAT)
            me_ctx->get_cost = &get_sbad_ob;
""",
        """        if (mi_ctx->me_mode == ME_MODE_BIDIR) {
            me_ctx->get_cost = &get_sad_ob;
            if (mi_ctx->mci_accel & 1) {
                me_ctx->mc_sad = av_pixelutils_get_sad_fn(mi_ctx->log2_mb_size + 1,
                                                        mi_ctx->log2_mb_size + 1,
                                                        0, inlink->dst);
                if (!me_ctx->mc_sad)
                    return AVERROR(EINVAL);
                me_ctx->get_cost = &get_sad_ob_simd;
            }
        } else if (mi_ctx->me_mode == ME_MODE_BILAT)
            me_ctx->get_cost = &get_sbad_ob;
""")
    return vf, header, configure


DIRECTION_HELPERS = """static void search_mv(MIContext *mi_ctx, Block *blocks, int mb_x, int mb_y, int dir)
{
    search_mv_context(mi_ctx, &mi_ctx->me_ctx, blocks, mb_x, mb_y, dir);
}

typedef struct MCDirectionData {
    AVMotionEstContext me[2];
} MCDirectionData;

static int search_direction_jobs(AVFilterContext *ctx, void *arg, int jobnr, int nb_jobs)
{
    MIContext *mi_ctx = ctx->priv;
    MCDirectionData *td = arg;
    int dir, mb_x, mb_y;

    /* nb_jobs=1 still searches both directions, with separate scratch state. */
    for (dir = jobnr; dir < 2; dir += nb_jobs) {
        AVMotionEstContext *me_ctx = &td->me[dir];
        me_ctx->linesize_cur = mi_ctx->frames[2].avf->linesize[0];
        me_ctx->linesize_ref = mi_ctx->frames[dir ? 3 : 1].avf->linesize[0];
        me_ctx->data_cur = mi_ctx->frames[2].avf->data[0];
        me_ctx->data_ref = mi_ctx->frames[dir ? 3 : 1].avf->data[0];

        /* EPZS current-frame left/top/top-right predictors require this order. */
        for (mb_y = 0; mb_y < mi_ctx->b_height; mb_y++)
            for (mb_x = 0; mb_x < mi_ctx->b_width; mb_x++)
                search_mv_context(mi_ctx, me_ctx, mi_ctx->frames[2].blocks,
                                  mb_x, mb_y, dir);
    }
    return 0;
}

"""

DIRECTION_LOOP = """                for (dir = 0; dir < 2; dir++) {
                    mi_ctx->me_ctx.linesize_cur = mi_ctx->frames[2].avf->linesize[0];
                    mi_ctx->me_ctx.linesize_ref = mi_ctx->frames[dir ? 3 : 1].avf->linesize[0];
                    mi_ctx->me_ctx.data_cur = mi_ctx->frames[2].avf->data[0];
                    mi_ctx->me_ctx.data_ref = mi_ctx->frames[dir ? 3 : 1].avf->data[0];

                    for (mb_y = 0; mb_y < mi_ctx->b_height; mb_y++)
                        for (mb_x = 0; mb_x < mi_ctx->b_width; mb_x++)
                            search_mv(mi_ctx, mi_ctx->frames[2].blocks, mb_x, mb_y, dir);
                }
"""


def add_direction_threads(vf: str) -> str:
    vf = replace_once(vf,
        """static void search_mv(MIContext *mi_ctx, Block *blocks, int mb_x, int mb_y, int dir)
{
    AVMotionEstContext *me_ctx = &mi_ctx->me_ctx;
""",
        """static void search_mv_context(MIContext *mi_ctx, AVMotionEstContext *me_ctx,
                              Block *blocks, int mb_x, int mb_y, int dir)
{
""")
    vf = replace_once(vf, "static void bilateral_me(MIContext *mi_ctx)\n",
                      DIRECTION_HELPERS + "static void bilateral_me(MIContext *mi_ctx)\n")
    threaded = """                if ((mi_ctx->mci_accel & 2) && mi_ctx->me_method == AV_ME_METHOD_EPZS) {
                    MCDirectionData td = { .me = { mi_ctx->me_ctx, mi_ctx->me_ctx } };
                    ff_filter_execute(ctx, search_direction_jobs, &td, NULL,
                                      FFMIN(2, ff_filter_get_nb_threads(ctx)));
                    /* Preserve the original post-direction-1 context as well. */
                    mi_ctx->me_ctx = td.me[1];
                } else {
""" + "".join("    " + line if line.strip() else line
                for line in DIRECTION_LOOP.splitlines(keepends=True)) + "                }\n"
    return replace_once(vf, DIRECTION_LOOP, threaded)


ROW_HELPERS = """typedef struct MCFrameData {
    AVFrame *out;
    int alpha;
    int last_chroma;
} MCFrameData;

static int set_frame_data_jobs(AVFilterContext *ctx, void *arg, int jobnr, int nb_jobs)
{
    MIContext *mi_ctx = ctx->priv;
    MCFrameData *td = arg;
    const int group = 1 << mi_ctx->log2_chroma_h;
    const int groups = AV_CEIL_RSHIFT(td->out->height, mi_ctx->log2_chroma_h);
    const int first = (groups * jobnr / nb_jobs) * group;
    const int end = FFMIN((groups * (jobnr + 1) / nb_jobs) * group, td->out->height);

    /* All planes of each complete chroma row group belong to one job. */
    set_frame_data_rows(mi_ctx, td->alpha, td->out, first, end, td->last_chroma);
    return 0;
}

static void set_frame_data_dispatch(AVFilterContext *ctx, MIContext *mi_ctx,
                                    int alpha, AVFrame *avf_out)
{
    if (mi_ctx->me_mode != ME_MODE_BIDIR || !(mi_ctx->mci_accel & 12)) {
        set_frame_data(mi_ctx, alpha, avf_out);
    } else if (mi_ctx->mci_accel & 4) {
        MCFrameData td = { .out = avf_out, .alpha = alpha,
                           .last_chroma = !!(mi_ctx->mci_accel & 8) };
        const int groups = AV_CEIL_RSHIFT(avf_out->height, mi_ctx->log2_chroma_h);
        ff_filter_execute(ctx, set_frame_data_jobs, &td, NULL,
                          FFMIN(groups, ff_filter_get_nb_threads(ctx)));
    } else {
        set_frame_data_rows(mi_ctx, alpha, avf_out, 0, avf_out->height, 1);
    }
}

"""


def add_frame_data_accel(vf: str) -> str:
    old = function_between(vf, "static void set_frame_data(", "static void var_size_bmc(")
    rows = replace_once(old,
        "static void set_frame_data(MIContext *mi_ctx, int alpha, AVFrame *avf_out)",
        "static void set_frame_data_rows(MIContext *mi_ctx, int alpha, AVFrame *avf_out,\n"
        "                                int first_row, int end_row, int last_chroma)")
    rows = replace_once(rows, "        for (y = 0; y < height; y++)\n",
                         "        for (y = first_row; y < end_row; y++)\n")
    rows = replace_once(rows,
        """                for (i = 0; i < pixel_refs->nb; i++)
                    weight_sum += pixel_weights->weights[i];
""",
        """                /* Serial chroma stores keep the last visited x and y in each
                 * subsampling cell. Preserve that representative at odd edges.
                 * Plane 0 has already initialized fallback refs for every pixel. */
                if (last_chroma && chroma &&
                    ((((x + 1) & ((1 << mi_ctx->log2_chroma_w) - 1)) && x != width - 1) ||
                     (((y + 1) & ((1 << mi_ctx->log2_chroma_h) - 1)) && y != height - 1)))
                    continue;

                for (i = 0; i < pixel_refs->nb; i++)
                    weight_sum += pixel_weights->weights[i];
""")
    # Only the pre-existing callsites are replaced; the dispatcher's original
    # path must continue calling the verbatim serial function.
    call = "                set_frame_data(mi_ctx, alpha, avf_out);"
    if vf.count(call) != 2:
        raise ValueError("expected the two original synthesis callsites")
    vf = vf.replace(call, "                set_frame_data_dispatch(ctx, mi_ctx, alpha, avf_out);")
    return replace_once(vf, old, old + rows + ROW_HELPERS)


def transform(inputs: dict[str, str]) -> dict[str, str]:
    vf, header, configure = (inputs[name] for name in FILES)
    if "mci_accel" in vf:
        raise ValueError("input already contains mci_accel; regenerate from the baseline")
    vf = replace_once(vf, "    int vsbmc;\n", "    int vsbmc;\n    int mci_accel;\n")
    vf = replace_once(vf, '    { "vsbmc", "variable-size block motion compensation", OFFSET(vsbmc), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 1, FLAGS },\n',
                      '    { "vsbmc", "variable-size block motion compensation", OFFSET(vsbmc), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 1, FLAGS },\n'
                      '    { "mci_accel", "experimental acceleration bits: 1 SIMD SAD, 2 direction jobs, 4 row jobs, 8 last chroma", OFFSET(mci_accel), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 15, FLAGS },\n')
    vf = replace_once(vf, "    .p.priv_class  = &minterpolate_class,\n",
                      "    .p.priv_class  = &minterpolate_class,\n"
                      "    .p.flags       = AVFILTER_FLAG_SLICE_THREADS,\n")
    vf, header, configure = add_simd(vf, header, configure)
    vf = add_direction_threads(vf)
    vf = add_frame_data_accel(vf)
    return dict(zip(FILES, (vf, header, configure)))


SAD_CONTROL_HEADER = r'''/* Generated actual old/new cost-function control, not a reimplementation. */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libavutil/common.h"
#include "libavfilter/motion_estimation.h"
#define COST_PRED_SCALE 64

'''

SAD_CONTROL_MAIN = r'''
static uint32_t rng = 0x51483217u;
static uint32_t next_random(void)
{
    rng ^= rng << 13;
    rng ^= rng >> 17;
    rng ^= rng << 5;
    return rng;
}

int main(void)
{
    enum { WIDTH = 103, HEIGHT = 89, STRIDE_A = 127, STRIDE_B = 139 };
    uint8_t *a = malloc(STRIDE_A * HEIGHT + 32);
    uint8_t *b = malloc(STRIDE_B * HEIGHT + 32);
    int mb, phase, test;
    unsigned long checks = 0;
    if (!a || !b)
        return 2;
    for (mb = 4; mb <= 16; mb *= 2) {
        AVMotionEstContext me = {0};
        int bits = mb == 4 ? 3 : mb == 8 ? 4 : 5;
        me.mb_size = mb;
        me.linesize_cur = STRIDE_A;
        me.linesize_ref = STRIDE_B;
        me.x_max = ((WIDTH / mb) - 1) * mb;
        me.y_max = ((HEIGHT / mb) - 1) * mb;
        me.mc_sad = av_pixelutils_get_sad_fn(bits, bits, 0, NULL);
        if (!me.mc_sad)
            return 3;
        for (phase = 0; phase < 4; phase++) {
            for (test = 0; test < STRIDE_A * HEIGHT + 32; test++)
                a[test] = phase == 0 ? 0 : phase == 1 ? 255 : phase == 2 ? (test & 1) * 255 : next_random();
            for (test = 0; test < STRIDE_B * HEIGHT + 32; test++)
                b[test] = phase == 0 ? 255 : phase == 1 ? 255 : phase == 2 ? ((test + 1) & 1) * 255 : next_random();
            for (test = 0; test < 4096; test++) {
                int x = (int)(next_random() % (WIDTH + 32)) - 16;
                int y = (int)(next_random() % (HEIGHT + 32)) - 16;
                int mx = (int)(next_random() % (WIDTH + 64)) - 32;
                int my = (int)(next_random() % (HEIGHT + 64)) - 32;
                uint64_t scalar, vector;
                me.data_cur = a + (test & 15);
                me.data_ref = b + ((test >> 4) & 15);
                me.pred_x = (int)(next_random() % 129) - 64;
                me.pred_y = (int)(next_random() % 129) - 64;
                scalar = get_sad_ob(&me, x, y, mx, my);
                vector = get_sad_ob_simd(&me, x, y, mx, my);
                if (scalar != vector) {
                    fprintf(stderr, "SAD mismatch mb=%d phase=%d test=%d: %" PRIu64 " != %" PRIu64 "\n",
                            mb, phase, test, scalar, vector);
                    return 1;
                }
                checks++;
            }
        }
    }
    free(a);
    free(b);
    printf("PASS %lu actual scalar/SIMD cost comparisons\n", checks);
    return 0;
}
'''


def sad_control(patched_vf: str) -> str:
    costs = function_between(patched_vf, "static uint64_t get_sad_ob(", "static int config_input(")
    if costs.count("static uint64_t get_sad_ob_simd(") != 1:
        raise ValueError("missing actual accelerated SAD function")
    return SAD_CONTROL_HEADER + costs + SAD_CONTROL_MAIN


def self_test(inputs: dict[str, str], outputs: dict[str, str]) -> dict[str, int]:
    """Small controls for the subtle scheduling/last-write equivalences."""
    old_vf, new_vf = inputs[FILES[0]], outputs[FILES[0]]
    for first, following in (("static uint64_t get_sad_ob(", "static int config_input("),
                             ("static void set_frame_data(", "static void var_size_bmc(")):
        original = function_between(old_vf, first, following)
        if new_vf.count(original) != 1:
            raise AssertionError(f"original body not retained verbatim: {first}")
    # A second application and a missing anchor must fail, rather than silently
    # outputting a partially accelerated source.
    for broken in (outputs, {**inputs, FILES[0]: old_vf.replace("    int vsbmc;", "    int changed;")}):
        try:
            transform(broken)
        except ValueError:
            pass
        else:
            raise AssertionError("damaged or already-patched source accepted")
    checks = 0
    for width in (1, 2, 3, 5, 16, 17, 31, 32, 33):
        for height in (1, 2, 3, 5, 16, 17, 31, 32, 33):
            for hsub, vsub in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (2, 2)):
                expected = {}
                for y in range(height):
                    for x in range(width):
                        expected[x >> hsub, y >> vsub] = (x, y)
                for threads in (1, 2, 3, 4, 16):
                    groups = (height + (1 << vsub) - 1) >> vsub
                    jobs = min(groups, threads)
                    owner, result, visited = {}, {}, []
                    for job in range(jobs):
                        first = (groups * job // jobs) << vsub
                        end = min((groups * (job + 1) // jobs) << vsub, height)
                        visited.extend(range(first, end))
                        for y in range(first, end):
                            for x in range(width):
                                key = (x >> hsub, y >> vsub)
                                if key in owner and owner[key] != job:
                                    raise AssertionError("chroma pixel has multiple owners")
                                owner[key] = job
                                skip = (((x + 1) & ((1 << hsub) - 1)) and x != width - 1 or
                                        ((y + 1) & ((1 << vsub) - 1)) and y != height - 1)
                                if not skip:
                                    if key in result:
                                        raise AssertionError("chroma representative visited twice")
                                    result[key] = (x, y)
                    if result != expected or visited != list(range(height)):
                        raise AssertionError("row partition or chroma last-write mismatch")
                    checks += 1
    for jobs in (1, 2):
        dirs = [direction for job in range(jobs) for direction in range(job, 2, jobs)]
        if sorted(dirs) != [0, 1]:
            raise AssertionError("direction lost or duplicated")
    return {"row_and_chroma_cases": checks, "direction_job_cases": 2,
            "fail_closed_cases": 2, "verbatim_original_functions": 2}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, type=Path, help="read-only FFmpeg source checkout")
    parser.add_argument("--out", required=True, type=Path, help="separate generated-artifact directory")
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    if out == source or source in out.parents:
        raise ValueError("output must be outside the FFmpeg source checkout")
    inputs = {name: (source / name).read_text() for name in FILES}
    outputs = transform(inputs)
    controls = self_test(inputs, outputs)
    patch = "".join("".join(difflib.unified_diff(inputs[name].splitlines(keepends=True),
                                                  outputs[name].splitlines(keepends=True),
                                                  fromfile="a/" + name, tofile="b/" + name))
                    for name in FILES)
    revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                              text=True, capture_output=True, check=True).stdout.strip()
    out.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        destination = out / "tree" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)
    (out / "accelerate.patch").write_text(patch)
    control = sad_control(outputs[FILES[0]])
    (out / "sad_control.c").write_text(control)
    manifest = {"status": "generated_not_compiled", "source_revision": revision,
                "audited_upstream_revision": BASE_COMMIT,
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "input_sha256": {name: sha(text) for name, text in inputs.items()},
                "output_sha256": {name: sha(text) for name, text in outputs.items()},
                "patch_sha256": sha(patch), "sad_control_sha256": sha(control),
                "cpu_generator_controls": controls,
                "mci_accel_default": 0,
                "bits": {"1": "SIMD SAD", "2": "bidir EPZS direction jobs",
                         "4": "chroma-aligned synthesis row jobs", "8": "last chroma representative"}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(out), "status": manifest["status"], "controls": controls}))


if __name__ == "__main__":
    main()
