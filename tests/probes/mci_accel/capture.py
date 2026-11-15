#!/usr/bin/env python3
"""Generate a pinned scalar FFmpeg capture source; validate/run external capsules.

Source generation does not edit the input or build/install/run FFmpeg. See
CAPSULE.md. The run action is for the later isolated capture binary only.
"""
import argparse
from array import array
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

ORIGINAL_SHA = '42e776a33821d7e08a20371a554513bca17ee427aac123ec0923bc4cbefad8e7'
MAGIC = 0x3149434d
HEADER_WORDS = 64
MAX_BYTES = 256 * 1024 * 1024
TABLE_SHA = {
    4: '0b058376e1c422e7b431d0689b8f5004a3350aa4a0739ef0117b5e2d344db670',
    8: 'c89ee038f51390188a6f72bae96e19faf1503f069f4e83a0a1102964dcffc444',
    16: 'b7ad253622fccb1916f436b772b2905af7a6afb24d48e52faacff5b5290a39f7',
}

INCLUDES = '''
/* Optional, isolated MCI capsule exporter; disabled without both environment variables. */
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "libavutil/intreadwrite.h"
'''
FIELDS = '''
    const char *mci_capture_prefix;
    const char *mci_capture_draws;
    uint64_t mci_capture_draw_index;
    int mci_capture_error;
'''
HELPERS = r'''
/* Capsule v1: exact scalar renderer inputs/output, not a motion estimator. */
static int mci_capture_config(AVFilterLink *inlink)
{
    MIContext *c = inlink->dst->priv;
    const char *prefix = getenv("MCI_CAPTURE_PREFIX");
    const char *draws = getenv("MCI_CAPTURE_DRAWS");
    const char *p;
    uint64_t previous = 0;
    int count = 0;
    if (!prefix && !draws)
        return 0;
    if (!prefix || !*prefix || !draws || !*draws || strlen(prefix) > 4096)
        return AVERROR(EINVAL);
    if (c->mi_mode != MI_MODE_MCI || c->me_mode != ME_MODE_BIDIR ||
        c->me_method != AV_ME_METHOD_EPZS || c->search_param != 32 ||
        (c->mb_size != 4 && c->mb_size != 8 && c->mb_size != 16) ||
        (inlink->format != AV_PIX_FMT_YUV420P && inlink->format != AV_PIX_FMT_YUV444P) ||
        inlink->w > 8192 || inlink->h > 8192)
        return AVERROR(EINVAL);
    p = draws;
    while (*p) {
        char *end;
        unsigned long long value;
        if (*p < '0' || *p > '9')
            return AVERROR(EINVAL);
        errno = 0;
        value = strtoull(p, &end, 10);
        if (errno || value <= previous || ++count > 16 ||
            (*end && *end != ','))
            return AVERROR(EINVAL);
        previous = value;
        if (!*end)
            break;
        p = end + 1;
        if (!*p)
            return AVERROR(EINVAL);
    }
    c->mci_capture_prefix = prefix;
    c->mci_capture_draws = draws;
    return 0;
}

static int mci_capture_selected(const MIContext *c, uint64_t index)
{
    const char *p = c->mci_capture_draws;
    while (*p) {
        char *end;
        uint64_t value = strtoull(p, &end, 10);
        if (value == index)
            return 1;
        if (value > index || !*end)
            return 0;
        p = end + 1;
    }
    return 0;
}

typedef struct MCICapsuleWriter {
    FILE *file;
    uint8_t bytes[4096];
    size_t used;
    int error;
} MCICapsuleWriter;

static void mci_capture_flush(MCICapsuleWriter *w)
{
    if (!w->error && w->used && fwrite(w->bytes, 1, w->used, w->file) != w->used)
        w->error = AVERROR(errno ? errno : EIO);
    w->used = 0;
}

static void mci_capture_word(MCICapsuleWriter *w, uint32_t value)
{
    if (w->error)
        return;
    AV_WL32(w->bytes + w->used, value);
    w->used += 4;
    if (w->used == sizeof(w->bytes))
        mci_capture_flush(w);
}

static void mci_capture_u64(uint32_t *header, int index, uint64_t value)
{
    header[index] = value;
    header[index + 1] = value >> 32;
}

static int mci_capture_frame(AVFilterLink *inlink, AVFrame *out, int alpha)
{
    MIContext *c = inlink->dst->priv;
    AVFilterLink *outlink = inlink->dst->outputs[0];
    uint32_t header[64] = {0};
    uint64_t plane_words, payload_words;
    uint32_t counts[3];
    AVFrame *images[3] = { c->frames[1].avf, c->frames[2].avf, out };
    const uint8_t *table = obmc_tab_linear[4 - c->log2_mb_size];
    char *final = NULL, *partial = NULL;
    int ret = 0, fd = -1, plane, image, dir, i, x, y;
    MCICapsuleWriter writer = {0};
    size_t path_size;
    if (!c->mci_capture_prefix)
        return 0;
    if (c->mci_capture_draw_index == UINT64_MAX)
        return AVERROR(EOVERFLOW);
    c->mci_capture_draw_index++;
    if (!mci_capture_selected(c, c->mci_capture_draw_index))
        return 0;
    if (alpha <= 0 || alpha >= ALPHA_MAX || c->scene_changed ||
        c->frames[1].avf->pts == AV_NOPTS_VALUE || c->frames[2].avf->pts == AV_NOPTS_VALUE ||
        out->pts == AV_NOPTS_VALUE || c->frames[2].avf->pts <= c->frames[1].avf->pts)
        return AVERROR(EINVAL);
    counts[0] = (uint32_t)out->width * out->height;
    counts[1] = counts[2] = (uint32_t)AV_CEIL_RSHIFT(out->width, c->log2_chroma_w) *
                                      AV_CEIL_RSHIFT(out->height, c->log2_chroma_h);
    plane_words = (uint64_t)counts[0] + counts[1] + counts[2];
    payload_words = 3 * plane_words + 4 * (uint64_t)c->b_count + 4 * c->mb_size * c->mb_size;
    if (4 * (64 + payload_words) > 256ULL * 1024 * 1024)
        return AVERROR(EOVERFLOW);
    header[0] = 0x3149434d; header[1] = 1; header[2] = 64; header[3] = payload_words;
    header[4] = out->width; header[5] = out->height; header[6] = c->mb_size;
    header[7] = c->search_param; header[8] = alpha;
    header[9] = c->log2_chroma_w; header[10] = c->log2_chroma_h; header[11] = 3;
    header[12] = c->b_width; header[13] = c->b_height; header[14] = c->b_count; header[15] = 1;
    mci_capture_u64(header, 16, c->mci_capture_draw_index);
    mci_capture_u64(header, 18, (uint64_t)c->frames[1].avf->pts);
    mci_capture_u64(header, 20, (uint64_t)c->frames[2].avf->pts);
    mci_capture_u64(header, 22, (uint64_t)out->pts);
    header[24] = inlink->time_base.num; header[25] = inlink->time_base.den;
    header[26] = outlink->time_base.num; header[27] = outlink->time_base.den;
    header[28] = 0; header[29] = plane_words; header[30] = 2 * plane_words;
    header[31] = 3 * plane_words; header[32] = 3 * plane_words + 4 * c->b_count;
    for (plane = 0; plane < 3; plane++) header[33 + plane] = counts[plane];
    header[36] = 4 * c->b_count; header[37] = 4 * c->mb_size * c->mb_size;
    header[38] = plane_words; header[39] = ALPHA_MAX;
    header[40] = inlink->format == AV_PIX_FMT_YUV420P ? 1 : 2;
    header[41] = NB_PIXEL_MVS / 2; header[42] = 2 * c->mb_size;
    path_size = strlen(c->mci_capture_prefix) + 64;
    final = av_malloc(path_size); partial = av_malloc(path_size);
    if (!final || !partial) { ret = AVERROR(ENOMEM); goto done; }
    snprintf(final, path_size, "%s-%010"PRIu64".bin", c->mci_capture_prefix, c->mci_capture_draw_index);
    snprintf(partial, path_size, "%s.partial", final);
    if (access(final, F_OK) == 0) { ret = AVERROR(EEXIST); goto done; }
    if (errno != ENOENT) { ret = AVERROR(errno); goto done; }
    fd = open(partial, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) { ret = AVERROR(errno); goto done; }
    writer.file = fdopen(fd, "wb");
    if (!writer.file) { ret = AVERROR(errno); close(fd); goto done; }
    fd = -1;
    for (i = 0; i < 64; i++) mci_capture_word(&writer, header[i]);
    for (image = 0; image < 3; image++)
        for (plane = 0; plane < 3; plane++) {
            int pw = plane ? AV_CEIL_RSHIFT(out->width, c->log2_chroma_w) : out->width;
            int ph = plane ? AV_CEIL_RSHIFT(out->height, c->log2_chroma_h) : out->height;
            for (y = 0; y < ph; y++) {
                const uint8_t *row = images[image]->data[plane] + (ptrdiff_t)y * images[image]->linesize[plane];
                for (x = 0; x < pw; x++) mci_capture_word(&writer, row[x]);
            }
        }
    for (dir = 0; dir < 2; dir++)
        for (i = 0; i < c->b_count; i++) {
            const Block *block = &c->frames[2 - dir].blocks[i];
            mci_capture_word(&writer, (uint32_t)(int32_t)block->mvs[dir][0]);
            mci_capture_word(&writer, (uint32_t)(int32_t)block->mvs[dir][1]);
        }
    for (i = 0; i < 4 * c->mb_size * c->mb_size; i++) mci_capture_word(&writer, table[i]);
    mci_capture_flush(&writer);
    ret = writer.error;
    if (fclose(writer.file) && !ret) ret = AVERROR(errno ? errno : EIO);
    writer.file = NULL;
    if (!ret && rename(partial, final)) ret = AVERROR(errno);
    if (!ret)
        av_log(inlink->dst, AV_LOG_INFO, "MCI_CAPSULE draw=%"PRIu64" path=%s\n", c->mci_capture_draw_index, final);
done:
    if (ret < 0)
        av_log(inlink->dst, AV_LOG_ERROR, "MCI capsule capture failed at draw %"PRIu64": %d\n", c->mci_capture_draw_index, ret);
    av_free(final); av_free(partial);
    return ret;
}

'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def source_transform(text):
    require(hashlib.sha256(text.encode()).hexdigest() == ORIGINAL_SHA, 'requires pinned pristine scalar source')
    replacements = [
        ('#include "motion_estimation.h"', INCLUDES+'\n#include "motion_estimation.h"'),
        ('    int nb_planes;\n} MIContext;', '    int nb_planes;\n'+FIELDS+'} MIContext;'),
        ('static int config_input(AVFilterLink *inlink)', HELPERS+'static int config_input(AVFilterLink *inlink)'),
        ('    mi_ctx->b_count = mi_ctx->b_width * mi_ctx->b_height;\n',
         '    mi_ctx->b_count = mi_ctx->b_width * mi_ctx->b_height;\n'
         '    { int capture_ret = mci_capture_config(inlink); if (capture_ret < 0) return capture_ret; }\n'),
        ('                bidirectional_obmc(mi_ctx, alpha);\n                set_frame_data(mi_ctx, alpha, avf_out);',
         '                bidirectional_obmc(mi_ctx, alpha);\n                set_frame_data(mi_ctx, alpha, avf_out);\n'
         '                mi_ctx->mci_capture_error = mci_capture_frame(inlink, avf_out, alpha);'),
        ('        interpolate(inlink, avf_out);\n',
         '        interpolate(inlink, avf_out);\n'
         '        if (mi_ctx->mci_capture_error < 0) {\n'
         '            av_frame_free(&avf_out);\n'
         '            return mi_ctx->mci_capture_error;\n'
         '        }\n'),
    ]
    original = text
    for old, new in replacements:
        require(text.count(old) == 1, 'capture source anchor is absent or duplicated: '+old[:70])
        text = text.replace(old, new, 1)
    reversed_text = text
    for old, new in reversed(replacements):
        require(reversed_text.count(new) == 1, 'capture transform not reversible')
        reversed_text = reversed_text.replace(new, old, 1)
    require(reversed_text == original, 'capture changed unregistered source text')
    return text


def u64(h, i):
    return h[i] | h[i+1] << 32


def s64(h, i):
    n = u64(h, i)
    return n if n < 1 << 63 else n-(1 << 64)


def trunc_div(n, d):
    return (abs(n)//d)*(-1 if n < 0 else 1)


def validate_capsule(path):
    """Return verified metadata; ValueError on malformed/unsupported capsule.

    Validates the registered data contract, not historical execution provenance.
    """
    path = Path(path)
    size = path.stat().st_size
    require(256 <= size <= MAX_BYTES and size % 4 == 0, 'invalid capsule byte length')
    raw = path.read_bytes()
    h = struct.unpack('<64I', raw[:256])
    require(h[:3] == (MAGIC, 1, HEADER_WORDS), 'unsupported capsule header')
    require(size == 4*(HEADER_WORDS+h[3]), 'trailing or truncated payload')
    w, height, b, search, alpha = h[4:9]
    require(1 <= w <= 8192 and 1 <= height <= 8192 and b in TABLE_SHA and search == 32,
            'unsupported geometry/search/block size')
    require(1 <= alpha <= 1023 and h[11] == 3 and h[15] == 1 and h[39] == 1024 and
            h[41] == 16 and h[42] == 2*b and not any(h[43:]), 'unsupported flags/phase/reserved words')
    require(h[40] in (1, 2), 'unsupported pixel format')
    sub = 1 if h[40] == 1 else 0
    require(h[9] == h[10] == sub, 'format/subsampling disagreement')
    bw, bh = w//b, height//b
    require(bw >= 2 and bh >= 2 and h[12:15] == (bw, bh, bw*bh), 'block grid disagreement')
    cw, ch = (w+(1 << sub)-1) >> sub, (height+(1 << sub)-1) >> sub
    counts = (w*height, cw*ch, cw*ch); p = sum(counts); vectors = 4*bw*bh; table = 4*b*b
    require(h[33:36] == counts and h[36:39] == (vectors, table, p), 'array count disagreement')
    require(h[28:33] == (0, p, 2*p, 3*p, 3*p+vectors) and h[3] == 3*p+vectors+table,
            'noncanonical payload offsets/size')
    require(u64(h, 16) > 0 and all(0 < v <= (1 << 31)-1 for v in h[24:28]), 'invalid index/time base')
    ap, bp, op = s64(h, 18), s64(h, 20), s64(h, 22)
    require(min(ap, bp, op) > -(1 << 63) and bp > ap, 'invalid/missing source PTS')
    max64 = (1 << 63)-1
    min64 = -(1 << 63)
    mul, den = 1024*h[26]*h[25], h[27]*h[24]
    require(mul <= max64 and den <= max64, 'stock int64 rescale factor overflow')
    rescaled = (abs(op)*mul+den//2)//den * (-1 if op < 0 else 1)
    source_scaled, interval = ap*1024, bp-ap
    require(min64 < rescaled <= max64 and min64 <= source_scaled <= max64 and
            0 < interval <= max64, 'stock int64 PTS arithmetic overflow')
    numerator = rescaled-source_scaled
    require(min64 <= numerator <= max64, 'stock int64 phase numerator overflow')
    expected_alpha = max(0, min(1024, trunc_div(numerator, interval)))
    require(expected_alpha == alpha, 'PTS/alpha disagreement with stock integer rescaling')
    words = array('I'); words.frombytes(raw[256:])
    require(words.itemsize == 4, 'unsupported host unsigned-int size')
    if sys.byteorder != 'little': words.byteswap()
    require(all(v <= 255 for v in words[:3*p]), 'source/golden sample outside 8-bit range')
    for direction in range(2):
        start = 3*p+2*bw*bh*direction
        for index in range(bw*bh):
            bx, by = index % bw, index//bw
            for axis, cell, count in ((0,bx,bw),(1,by,bh)):
                n = words[start+2*index+axis]
                mv = n if n < 1 << 31 else n-(1 << 32)
                require(max(-32,-cell*b) <= mv <= min(32,(count-1-cell)*b), 'motion outside stock search/global bounds')
    table_raw = raw[256+4*h[32]:]
    require(hashlib.sha256(table_raw).hexdigest() == TABLE_SHA[b], 'overlap table does not match pinned scalar source')
    plane_hashes = {}
    for label, offset in (('a',0), ('b',p), ('golden',2*p)):
        bytes8 = bytes(v for v in words[offset:offset+p])
        plane_hashes[label] = hashlib.sha256(bytes8).hexdigest()
    return dict(schema=1, capsule_sha256=hashlib.sha256(raw).hexdigest(), bytes=size,
        width=w,height=height,mb_size=b,search_param=search,alpha=alpha,pixel_format='yuv420p' if sub else 'yuv444p',
        plane_words=list(counts),payload_words=h[3],draw_index=u64(h,16),source_a_pts=ap,source_b_pts=bp,
        output_pts=op,input_time_base=[h[24],h[25]],output_time_base=[h[26],h[27]],
        source_and_golden_packed_byte_sha256=plane_hashes,table_sha256=TABLE_SHA[b],
        scope='Verified capsule contract; execution/source provenance requires the external run manifest')


def save(path, data):
    pending = path.with_suffix(path.suffix+'.partial')
    pending.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
    pending.replace(path)


def run_capture(args):
    # Import the already registered all-plane timing/count parser, not profile parsing.
    from gate import parse_frames, probe, output_count
    root = args.out.resolve()
    require(not root.exists() or not any(root.iterdir()), 'capture requires a fresh empty output directory')
    root.mkdir(parents=True, exist_ok=True)
    manifest = root/'capture.json'
    save(manifest, dict(execution_status='incomplete'))
    draws = [int(v) for v in args.draws.split(',')]
    require(0 < len(draws) <= 16 and draws == sorted(set(draws)) and all(0 < n < 1 << 64 for n in draws),
            'draws must be 1..16 strictly increasing positive uint64 indices')
    original = args.original_source.read_text()
    generated = source_transform(original)
    require(args.capture_source.read_text() == generated, 'capture source does not equal the registered transform')
    info = probe(args.ffprobe, args.source)
    require(info['pix_fmt'] in ('yuv420p','yuv444p'), 'capture input must be 8-bit planar 420 or 444')
    rate = Fraction(info['rate']); fps = Fraction(args.fps) if args.fps else 2*rate
    require(rate > 0 and fps > 0, 'source/output rates must be positive')
    case = dict(info, output_rate=str(fps)); count = output_count(case)
    denominator = math.lcm(rate.numerator, fps.numerator)
    step = denominator*rate.denominator//rate.numerator
    vf = (f'settb=expr=1/{denominator},setpts=N*{step},tpad=stop_mode=clone:stop=2,'
          f'minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:'
          f'mb_size={args.mb_size}:search_param=32:vsbmc=1')
    command = [str(args.ffmpeg.resolve()),'-nostdin','-v','info','-nostats','-threads','1',
        '-filter_threads','1','-i',str(args.source.resolve()),'-map','0:v:0','-an','-vf',vf,
        '-frames:v',str(count),'-c:v','rawvideo','-threads','1','-pix_fmt',info['pix_fmt'],
        '-fps_mode','passthrough','-enc_time_base','filter','-f','framemd5','-']
    hashes = {label:sha(path) for label,path in [('source',args.source),('ffmpeg',args.ffmpeg),
        ('ffprobe',args.ffprobe),('original_c',args.original_source),('capture_c',args.capture_source)]}
    env = dict(os.environ, MCI_CAPTURE_PREFIX=str(root/'draw'), MCI_CAPTURE_DRAWS=','.join(map(str,draws)))
    context = dict(command=command,environment={k:env[k] for k in ('MCI_CAPTURE_PREFIX','MCI_CAPTURE_DRAWS')},
        hashes=hashes,source_path=str(args.source.resolve()),source=case,requested_draws=draws,
        capture_script_sha256=sha(__file__))
    save(manifest, dict(execution_status='incomplete', **context))
    with (root/'output.framemd5').open('wb') as out, (root/'capture.log').open('wb') as log:
        result = subprocess.run(command, env=env, stdout=out, stderr=log)
    require(result.returncode == 0, 'capture FFmpeg failed; preserve incomplete manifest and log')
    frames = parse_frames((root/'output.framemd5').read_text(),case)
    require(hashes == {label:sha(path) for label,path in [('source',args.source),('ffmpeg',args.ffmpeg),
        ('ffprobe',args.ffprobe),('original_c',args.original_source),('capture_c',args.capture_source)]}, 'input/tool/source changed during capture')
    expected = [root/f'draw-{n:010d}.bin' for n in draws]
    require(sorted(root.glob('draw-*.bin')) == sorted(expected) and not list(root.glob('draw-*.partial')),
            'missing/unexpected/partial capture files')
    capsules = []
    for path, draw in zip(expected,draws):
        cap = validate_capsule(path)
        require(cap['draw_index'] == draw and cap['width'] == case['width'] and cap['height'] == case['height'] and
                cap['pixel_format'] == case['pix_fmt'] and cap['mb_size'] == args.mb_size, 'capsule/run metadata disagreement')
        require(Fraction(*cap['input_time_base']) == Fraction(1,denominator) and
                Fraction(*cap['output_time_base']) == 1/fps, 'capsule/run timebase disagreement')
        source_indices = []
        for name in ('source_a_pts','source_b_pts'):
            source_index = cap[name]*Fraction(*cap['input_time_base'])*rate
            require(source_index.denominator == 1 and 0 <= source_index <= case['frames']+1,
                    'capsule source PTS does not identify an input or registered tail clone')
            source_indices.append(int(source_index))
        require(source_indices[1] == source_indices[0]+1, 'captured sources are not adjacent normalized inputs')
        cap['source_pair'] = [dict(normalized_input_index=i,original_frame_index=min(i,case['frames']-1),
                                   cloned_tail=i >= case['frames']) for i in source_indices]
        out_time = cap['output_pts']*Fraction(*cap['output_time_base'])
        index = out_time*fps
        require(index.denominator == 1 and 0 <= index < len(frames['frames']), 'capsule output is absent from frame records')
        cap['output_frame_index'] = int(index)
        cap['file'] = path.name
        # The rawvideo record hashes the same packed 8-bit Y,U,V golden bytes.
        raw = path.read_bytes(); header = struct.unpack('<64I',raw[:256])
        g = array('I');g.frombytes(raw[256+4*header[30]:256+4*(header[30]+header[38])])
        if sys.byteorder != 'little':g.byteswap()
        require(hashlib.md5(bytes(v for v in g)).hexdigest() == frames['frames'][int(index)]['md5'], 'golden differs from actual emitted output')
        capsules.append(cap)
    save(manifest, dict(execution_status='complete',returncode=0,**context,capsules=capsules,
        output_frames=len(frames['frames']),output_records_sha256=sha(root/'output.framemd5'),
        log_sha256=sha(root/'capture.log'),scope='Scalar stock rendering capsules; no GPU or speed result'))
    print(manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action',required=True)
    src = sub.add_parser('source');src.add_argument('original',type=Path);src.add_argument('output',type=Path)
    val = sub.add_parser('validate');val.add_argument('capsule',type=Path)
    run = sub.add_parser('run');run.add_argument('source',type=Path);run.add_argument('out',type=Path)
    run.add_argument('--ffmpeg',type=Path,required=True);run.add_argument('--ffprobe',type=Path,required=True)
    run.add_argument('--original-source',type=Path,required=True);run.add_argument('--capture-source',type=Path,required=True)
    run.add_argument('--draws',required=True);run.add_argument('--fps');run.add_argument('--mb-size',type=int,choices=(4,8,16),default=16)
    args = parser.parse_args()
    if args.action == 'source':
        require(args.original.resolve() != args.output.resolve(), 'refuse to overwrite original source')
        require(not args.output.exists(), 'source output already exists')
        args.output.write_text(source_transform(args.original.read_text()))
    elif args.action == 'validate':print(json.dumps(validate_capsule(args.capsule),indent=2))
    else:run_capture(args)


if __name__ == '__main__':main()
