/* Standalone capsule-v1 GPU proof. No video decode, RGB conversion, or ME.
 * Build with installed libplacebo/Vulkan headers, e.g.:
 *   cc -std=c17 -O2 replay.c $(pkg-config --cflags --libs libplacebo) -o replay
 *   ./replay --validate-only capsule.bin
 *   ./replay --shader gather.comp --repeats 5 capsule.bin > result.json
 *   ./replay --readback staging --shader gather.comp --repeats 5 capsule.bin
 * pkg-config may need the local libplacebo prefix in PKG_CONFIG_PATH.
 * No shader compile or device creation occurs with --validate-only.
 * All timed replays are offline, expanded-u32, with input re-upload and output
 * poison. They omit live decode/encode and are not playback throughput claims.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <libplacebo/gpu.h>
#include <libplacebo/log.h>
#include <libplacebo/vulkan.h>

enum { HEADER_WORDS = 64, MAX_REPEATS = 100, LOCAL_X = 8, LOCAL_Y = 8 };
enum { MAX_FILE_BYTES = 256 * 1024 * 1024 };

/* Canonical obmc tables from vf_minterpolate.c at 3a5eb948e76dc6390e4b3cff7becf84bc492b7af. */
static const uint32_t expected_8[64] = {
    4, 12, 20, 28, 28, 20, 12, 4, 12, 36, 60, 84, 84, 60, 36, 12,
    20, 60, 100, 140, 140, 100, 60, 20, 28, 84, 140, 196, 196, 140, 84, 28,
    28, 84, 140, 196, 196, 140, 84, 28, 20, 60, 100, 140, 140, 100, 60, 20,
    12, 36, 60, 84, 84, 60, 36, 12, 4, 12, 20, 28, 28, 20, 12, 4,
};

static const uint32_t expected_16[256] = {
    0, 4, 4, 8, 8, 12, 12, 16, 16, 12, 12, 8, 8, 4, 4, 0,
    4, 8, 16, 20, 28, 32, 40, 44, 44, 40, 32, 28, 20, 16, 8, 4,
    4, 16, 24, 36, 44, 56, 64, 76, 76, 64, 56, 44, 36, 24, 16, 4,
    8, 20, 36, 48, 64, 76, 92, 104, 104, 92, 76, 64, 48, 36, 20, 8,
    8, 28, 44, 64, 80, 100, 116, 136, 136, 116, 100, 80, 64, 44, 28, 8,
    12, 32, 56, 76, 100, 120, 144, 164, 164, 144, 120, 100, 76, 56, 32, 12,
    12, 40, 64, 92, 116, 144, 168, 196, 196, 168, 144, 116, 92, 64, 40, 12,
    16, 44, 76, 104, 136, 164, 196, 224, 224, 196, 164, 136, 104, 76, 44, 16,
    16, 44, 76, 104, 136, 164, 196, 224, 224, 196, 164, 136, 104, 76, 44, 16,
    12, 40, 64, 92, 116, 144, 168, 196, 196, 168, 144, 116, 92, 64, 40, 12,
    12, 32, 56, 76, 100, 120, 144, 164, 164, 144, 120, 100, 76, 56, 32, 12,
    8, 28, 44, 64, 80, 100, 116, 136, 136, 116, 100, 80, 64, 44, 28, 8,
    8, 20, 36, 48, 64, 76, 92, 104, 104, 92, 76, 64, 48, 36, 20, 8,
    4, 16, 24, 36, 44, 56, 64, 76, 76, 64, 56, 44, 36, 24, 16, 4,
    4, 8, 16, 20, 28, 32, 40, 44, 44, 40, 32, 28, 20, 16, 8, 4,
    0, 4, 4, 8, 8, 12, 12, 16, 16, 12, 12, 8, 8, 4, 4, 0,
};

static const uint32_t expected_32[1024] = {
    0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 4, 8, 8, 8, 8,
    8, 8, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4, 0, 0, 0, 0,
    0, 4, 4, 4, 8, 8, 8, 12, 12, 16, 16, 16, 20, 20, 20, 24,
    24, 20, 20, 20, 16, 16, 16, 12, 12, 8, 8, 8, 4, 4, 4, 0,
    0, 4, 8, 8, 12, 12, 16, 20, 20, 24, 28, 28, 32, 32, 36, 40,
    40, 36, 32, 32, 28, 28, 24, 20, 20, 16, 12, 12, 8, 8, 4, 0,
    0, 4, 8, 12, 16, 20, 24, 28, 28, 32, 36, 40, 44, 48, 52, 56,
    56, 52, 48, 44, 40, 36, 32, 28, 28, 24, 20, 16, 12, 8, 4, 0,
    4, 8, 12, 16, 20, 24, 28, 32, 40, 44, 48, 52, 56, 60, 64, 68,
    68, 64, 60, 56, 52, 48, 44, 40, 32, 28, 24, 20, 16, 12, 8, 4,
    4, 8, 12, 20, 24, 32, 36, 40, 48, 52, 56, 64, 68, 76, 80, 84,
    84, 80, 76, 68, 64, 56, 52, 48, 40, 36, 32, 24, 20, 12, 8, 4,
    4, 8, 16, 24, 28, 36, 44, 48, 56, 60, 68, 76, 80, 88, 96, 100,
    100, 96, 88, 80, 76, 68, 60, 56, 48, 44, 36, 28, 24, 16, 8, 4,
    4, 12, 20, 28, 32, 40, 48, 56, 64, 72, 80, 88, 92, 100, 108, 116,
    116, 108, 100, 92, 88, 80, 72, 64, 56, 48, 40, 32, 28, 20, 12, 4,
    4, 12, 20, 28, 40, 48, 56, 64, 72, 80, 88, 96, 108, 116, 124, 132,
    132, 124, 116, 108, 96, 88, 80, 72, 64, 56, 48, 40, 28, 20, 12, 4,
    4, 16, 24, 32, 44, 52, 60, 72, 80, 92, 100, 108, 120, 128, 136, 148,
    148, 136, 128, 120, 108, 100, 92, 80, 72, 60, 52, 44, 32, 24, 16, 4,
    4, 16, 28, 36, 48, 56, 68, 80, 88, 100, 112, 120, 132, 140, 152, 164,
    164, 152, 140, 132, 120, 112, 100, 88, 80, 68, 56, 48, 36, 28, 16, 4,
    4, 16, 28, 40, 52, 64, 76, 88, 96, 108, 120, 132, 144, 156, 168, 180,
    180, 168, 156, 144, 132, 120, 108, 96, 88, 76, 64, 52, 40, 28, 16, 4,
    8, 20, 32, 44, 56, 68, 80, 92, 108, 120, 132, 144, 156, 168, 180, 192,
    192, 180, 168, 156, 144, 132, 120, 108, 92, 80, 68, 56, 44, 32, 20, 8,
    8, 20, 32, 48, 60, 76, 88, 100, 116, 128, 140, 156, 168, 184, 196, 208,
    208, 196, 184, 168, 156, 140, 128, 116, 100, 88, 76, 60, 48, 32, 20, 8,
    8, 20, 36, 52, 64, 80, 96, 108, 124, 136, 152, 168, 180, 196, 212, 224,
    224, 212, 196, 180, 168, 152, 136, 124, 108, 96, 80, 64, 52, 36, 20, 8,
    8, 24, 40, 56, 68, 84, 100, 116, 132, 148, 164, 180, 192, 208, 224, 240,
    240, 224, 208, 192, 180, 164, 148, 132, 116, 100, 84, 68, 56, 40, 24, 8,
    8, 24, 40, 56, 68, 84, 100, 116, 132, 148, 164, 180, 192, 208, 224, 240,
    240, 224, 208, 192, 180, 164, 148, 132, 116, 100, 84, 68, 56, 40, 24, 8,
    8, 20, 36, 52, 64, 80, 96, 108, 124, 136, 152, 168, 180, 196, 212, 224,
    224, 212, 196, 180, 168, 152, 136, 124, 108, 96, 80, 64, 52, 36, 20, 8,
    8, 20, 32, 48, 60, 76, 88, 100, 116, 128, 140, 156, 168, 184, 196, 208,
    208, 196, 184, 168, 156, 140, 128, 116, 100, 88, 76, 60, 48, 32, 20, 8,
    8, 20, 32, 44, 56, 68, 80, 92, 108, 120, 132, 144, 156, 168, 180, 192,
    192, 180, 168, 156, 144, 132, 120, 108, 92, 80, 68, 56, 44, 32, 20, 8,
    4, 16, 28, 40, 52, 64, 76, 88, 96, 108, 120, 132, 144, 156, 168, 180,
    180, 168, 156, 144, 132, 120, 108, 96, 88, 76, 64, 52, 40, 28, 16, 4,
    4, 16, 28, 36, 48, 56, 68, 80, 88, 100, 112, 120, 132, 140, 152, 164,
    164, 152, 140, 132, 120, 112, 100, 88, 80, 68, 56, 48, 36, 28, 16, 4,
    4, 16, 24, 32, 44, 52, 60, 72, 80, 92, 100, 108, 120, 128, 136, 148,
    148, 136, 128, 120, 108, 100, 92, 80, 72, 60, 52, 44, 32, 24, 16, 4,
    4, 12, 20, 28, 40, 48, 56, 64, 72, 80, 88, 96, 108, 116, 124, 132,
    132, 124, 116, 108, 96, 88, 80, 72, 64, 56, 48, 40, 28, 20, 12, 4,
    4, 12, 20, 28, 32, 40, 48, 56, 64, 72, 80, 88, 92, 100, 108, 116,
    116, 108, 100, 92, 88, 80, 72, 64, 56, 48, 40, 32, 28, 20, 12, 4,
    4, 8, 16, 24, 28, 36, 44, 48, 56, 60, 68, 76, 80, 88, 96, 100,
    100, 96, 88, 80, 76, 68, 60, 56, 48, 44, 36, 28, 24, 16, 8, 4,
    4, 8, 12, 20, 24, 32, 36, 40, 48, 52, 56, 64, 68, 76, 80, 84,
    84, 80, 76, 68, 64, 56, 52, 48, 40, 36, 32, 24, 20, 12, 8, 4,
    4, 8, 12, 16, 20, 24, 28, 32, 40, 44, 48, 52, 56, 60, 64, 68,
    68, 64, 60, 56, 52, 48, 44, 40, 32, 28, 24, 20, 16, 12, 8, 4,
    0, 4, 8, 12, 16, 20, 24, 28, 28, 32, 36, 40, 44, 48, 52, 56,
    56, 52, 48, 44, 40, 36, 32, 28, 28, 24, 20, 16, 12, 8, 4, 0,
    0, 4, 8, 8, 12, 12, 16, 20, 20, 24, 28, 28, 32, 32, 36, 40,
    40, 36, 32, 32, 28, 28, 24, 20, 20, 16, 12, 12, 8, 8, 4, 0,
    0, 4, 4, 4, 8, 8, 8, 12, 12, 16, 16, 16, 20, 20, 20, 24,
    24, 20, 20, 20, 16, 16, 16, 12, 12, 8, 8, 8, 4, 4, 4, 0,
    0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 4, 8, 8, 8, 8,
    8, 8, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4, 0, 0, 0, 0,
};


typedef struct Capsule {
    uint32_t *words, *h, *payload;
    size_t file_bytes;
    uint32_t samples, plane_width[3], plane_height[3], plane_offset[3];
    uint32_t *a, *b, *golden, *vectors, *table;
    uint8_t *golden_bytes;
} Capsule;

typedef struct Push {
    uint32_t width, height, block_size, search_radius;
    uint32_t alpha, hsub, vsub, plane;
    uint32_t plane_width, plane_height, plane_offset, blocks_x;
    uint32_t blocks_y, block_count, max_pairs, reserved;
} Push;
_Static_assert(sizeof(Push) == 64, "push constant layout must match gather.comp");

typedef struct Timing {
    uint64_t upload_ns, dispatch_finish_ns, download_ns, pack_compare_ns, total_ns;
    uint64_t kernel_ns[3];
    unsigned timer_queries[3];
} Timing;

static uint64_t dispatches, validated_samples;
static char selected_device[VK_MAX_PHYSICAL_DEVICE_NAME_SIZE];
static bool selected_hardware;
static unsigned gpu_errors;
static const char *capsule_path;
static const char *readback_mode = "direct";

static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) {
        perror("clock_gettime");
        exit(3);
    }
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static void json_string(const char *s)
{
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        if (*p == '"' || *p == '\\')
            printf("\\%c", *p);
        else if (*p < 32)
            printf("\\u%04x", *p);
        else
            putchar(*p);
    }
    putchar('"');
}

static void status_fields(const char *status)
{
    printf("{\"status\":"); json_string(status);
    printf(",\"capsule\":"); json_string(capsule_path ? capsule_path : "");
    printf(",\"dispatches\":%" PRIu64 ",\"validated_samples\":%" PRIu64,
           dispatches, validated_samples);
    printf(",\"device\":"); json_string(selected_device);
    printf(",\"software\":%s", selected_hardware ? "false" : "null");
    printf(",\"readback_mode\":"); json_string(readback_mode);
}

static void fail(int code, const char *status, const char *reason)
{
    status_fields(status);
    printf(",\"reason\":"); json_string(reason);
    puts("}");
    exit(code);
}

static void require(bool condition, const char *reason)
{
    if (!condition)
        fail(2, "validation_error", reason);
}

static void gpu_log(void *priv, enum pl_log_level level, const char *message)
{
    (void)priv;
    if (level <= PL_LOG_ERR)
        gpu_errors++;
    pl_log_simple(stderr, level, message);
}

static unsigned char *read_file(const char *path, size_t limit, size_t *length, bool capsule)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        fail(capsule ? 2 : 3, capsule ? "validation_error" : "setup_error", "cannot open input file");
    if (fseek(f, 0, SEEK_END))
        fail(2, "validation_error", "cannot seek input file");
    long n = ftell(f);
    if (n < 0 || (uint64_t)n > limit || fseek(f, 0, SEEK_SET))
        fail(2, "validation_error", "input file length exceeds bounded proof limits");
    unsigned char *bytes = malloc((size_t)n + 1);
    if (!bytes)
        fail(3, "setup_error", "host allocation failed");
    if (fread(bytes, 1, (size_t)n, f) != (size_t)n || fclose(f))
        fail(2, "validation_error", "input file read failed");
    bytes[n] = 0;
    *length = (size_t)n;
    return bytes;
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int64_t signed_pts(const uint32_t *h, unsigned offset)
{
    uint64_t bits = h[offset] | (uint64_t)h[offset + 1] << 32;
    int64_t value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}

static void validate_phase(const uint32_t *h)
{
    int64_t ap = signed_pts(h, 18), bp = signed_pts(h, 20), op = signed_pts(h, 22);
    require(ap != INT64_MIN && bp != INT64_MIN && op != INT64_MIN && bp > ap,
            "invalid/missing source PTS or nonincreasing source pair");
    /* Clang/GCC on the registered Mac/Linux hosts provide int128. Check every
     * original int64 intermediate; capsules invoking C overflow are refused. */
    __int128 mul = (__int128)1024 * h[26] * h[25];
    __int128 den = (__int128)h[27] * h[24];
    require(mul <= INT64_MAX && den <= INT64_MAX, "PTS rescale factors overflow stock int64");
    __int128 magnitude = op < 0 ? -(__int128)op : op;
    __int128 rescaled = (magnitude * mul + den / 2) / den;
    require(rescaled <= INT64_MAX, "rescaled PTS exceeds stock int64");
    if (op < 0) rescaled = -rescaled;
    __int128 a_scaled = (__int128)ap * 1024;
    __int128 span = (__int128)bp - ap;
    __int128 numerator = rescaled - a_scaled;
    require(a_scaled >= INT64_MIN && a_scaled <= INT64_MAX && span <= INT64_MAX &&
            numerator >= INT64_MIN && numerator <= INT64_MAX, "phase arithmetic overflows stock int64");
    __int128 alpha = numerator / span;
    if (alpha < 0) alpha = 0;
    if (alpha > 1024) alpha = 1024;
    require(alpha == h[8], "PTS/alpha disagreement with stock integer rescaling");
}

static Capsule load_capsule(const char *path)
{
    Capsule c = {0};
    unsigned char *bytes = read_file(path, MAX_FILE_BYTES, &c.file_bytes, true);
    require(c.file_bytes >= HEADER_WORDS * 4 && c.file_bytes % 4 == 0, "truncated or unaligned capsule");
    c.words = malloc(c.file_bytes);
    if (!c.words)
        fail(3, "setup_error", "capsule word allocation failed");
    for (size_t i = 0; i < c.file_bytes / 4; i++)
        c.words[i] = le32(bytes + 4 * i);
    free(bytes);
    c.h = c.words;
    c.payload = c.words + HEADER_WORDS;
    const uint32_t *h = c.h;
    require(h[0] == UINT32_C(0x3149434d) && h[1] == 1 && h[2] == HEADER_WORDS, "wrong capsule magic/version/header size");
    require((uint64_t)h[3] + HEADER_WORDS == c.file_bytes / 4, "payload length disagrees with exact file length");
    require(h[4] > 0 && h[4] <= 8192 && h[5] > 0 && h[5] <= 8192, "dimensions outside bounded proof limits");
    require(h[6] == 4 || h[6] == 8 || h[6] == 16, "unsupported block size");
    require(h[7] == 32, "v1 requires stock search radius 32");
    require(h[8] > 0 && h[8] < 1024, "v1 only captures interior MCI draws");
    require(h[11] == 3 && h[15] == 1 && h[43] == 0, "unsupported planes/capture flags/scene branch");
    require((h[40] == 1 && h[9] == 1 && h[10] == 1) ||
            (h[40] == 2 && h[9] == 0 && h[10] == 0), "pixel format/subsampling mismatch");
    require(h[12] == h[4] / h[6] && h[13] == h[5] / h[6] && h[12] >= 2 && h[13] >= 2,
            "block grid disagrees with dimensions");
    require((uint64_t)h[12] * h[13] == h[14], "block count mismatch");
    require(h[16] || h[17], "draw identity must be one-based");
    require(h[24] && h[25] && h[26] && h[27] && h[24] <= INT_MAX && h[25] <= INT_MAX &&
            h[26] <= INT_MAX && h[27] <= INT_MAX, "invalid time base");
    validate_phase(h);
    require(h[39] == 1024 && h[41] == 16 && h[42] == 2 * h[6], "wrong phase/cap/table-side constants");
    for (unsigned i = 44; i < HEADER_WORDS; i++)
        require(h[i] == 0, "nonzero reserved header word");

    uint64_t samples = 0;
    for (unsigned plane = 0; plane < 3; plane++) {
        unsigned hs = plane ? h[9] : 0, vs = plane ? h[10] : 0;
        c.plane_width[plane] = (h[4] + (1u << hs) - 1) >> hs;
        c.plane_height[plane] = (h[5] + (1u << vs) - 1) >> vs;
        c.plane_offset[plane] = (uint32_t)samples;
        uint64_t count = (uint64_t)c.plane_width[plane] * c.plane_height[plane];
        require(count == h[33 + plane], "native plane sample count mismatch");
        samples += count;
    }
    require(samples == h[38], "total sample count mismatch");
    require((uint64_t)4 * h[14] == h[36] && (uint64_t)4 * h[6] * h[6] == h[37], "vector/table length mismatch");
    require(h[28] == 0 && h[29] == samples && h[30] == 2 * samples && h[31] == 3 * samples &&
            h[32] == 3 * samples + h[36] && h[3] == 3 * samples + h[36] + h[37],
            "payload offsets are not canonical contiguous sections");
    c.samples = (uint32_t)samples;
    c.a = c.payload + h[28]; c.b = c.payload + h[29]; c.golden = c.payload + h[30];
    c.vectors = c.payload + h[31]; c.table = c.payload + h[32];
    for (uint64_t i = 0; i < 3 * samples; i++)
        require(c.payload[i] <= 255, "source or golden sample outside 8-bit range");
    for (uint32_t i = 0; i < h[36]; i++) {
        int32_t mv;
        memcpy(&mv, &c.vectors[i], sizeof(mv));
        require(mv >= -(int32_t)h[7] && mv <= (int32_t)h[7], "vector exceeds declared search bound");
        uint32_t block = (i / 2) % h[14];
        uint32_t cell = (i & 1) ? block / h[12] : block % h[12];
        uint32_t count = (i & 1) ? h[13] : h[12];
        require(mv >= -(int32_t)(cell * h[6]) && mv <= (int32_t)((count - 1 - cell) * h[6]),
                "vector exceeds stock global anchor bounds");
    }
    const uint32_t *canonical = h[6] == 4 ? expected_8 : h[6] == 8 ? expected_16 : expected_32;
    for (uint32_t i = 0; i < h[37]; i++)
        require(c.table[i] == canonical[i], "overlap table differs from pinned stock table");
    c.golden_bytes = malloc(c.samples);
    if (!c.golden_bytes)
        fail(3, "setup_error", "golden byte allocation failed");
    for (uint32_t i = 0; i < c.samples; i++)
        c.golden_bytes[i] = (uint8_t)c.golden[i];
    return c;
}

static void check_gpu(pl_gpu gpu)
{
    if (gpu_errors || pl_gpu_is_failed(gpu))
        fail(3, "setup_error", "libplacebo reported a GPU error; no equivalence conclusion");
}

static void compare_output(const Capsule *c, const uint32_t *result, uint8_t *packed)
{
    uint64_t invalid = 0, mismatches = 0;
    uint32_t first_invalid = 0, first_mismatch = 0;
    for (uint32_t i = 0; i < c->samples; i++) {
        if (result[i] > 255) {
            if (!invalid) first_invalid = i;
            invalid++;
        }
        packed[i] = (uint8_t)result[i];
        if (result[i] != c->golden[i]) {
            if (!mismatches) first_mismatch = i;
            mismatches++;
        }
    }
    validated_samples = c->samples;
    if (invalid || mismatches) {
        status_fields(invalid ? "gpu_output_invalid" : "gpu_mismatch");
        uint32_t first = invalid ? first_invalid : first_mismatch;
        printf(",\"invalid_words\":%" PRIu64 ",\"mismatched_words\":%" PRIu64
               ",\"first_index\":%u,\"actual\":%u,\"expected\":%u}\n",
               invalid, mismatches, first, result[first], c->golden[first]);
        exit(invalid ? 5 : 4);
    }
    if (memcmp(packed, c->golden_bytes, c->samples))
        fail(4, "gpu_mismatch", "packed whole-YUV byte comparison failed");
}

static Timing iteration(const Capsule *c, pl_gpu gpu, pl_pass pass, pl_buf buffers[5],
                        pl_buf staging, pl_timer timers[3], uint32_t *output, uint8_t *packed)
{
    Timing t = {0};
    uint64_t start = now_ns(), stage = start;
    const uint32_t *h = c->h;
    size_t plane_bytes = (size_t)c->samples * 4;
    // Golden bytes are deliberately never bound or uploaded to any GPU object.
    pl_buf_write(gpu, buffers[0], 0, c->a, plane_bytes);
    pl_buf_write(gpu, buffers[1], 0, c->b, plane_bytes);
    pl_buf_write(gpu, buffers[2], 0, c->vectors, (size_t)h[36] * 4);
    pl_buf_write(gpu, buffers[3], 0, c->table, (size_t)h[37] * 4);
    memset(output, 0xff, plane_bytes);
    pl_buf_write(gpu, buffers[4], 0, output, plane_bytes);
    pl_gpu_finish(gpu);
    check_gpu(gpu);
    t.upload_ns = now_ns() - stage;
    stage = now_ns();
    struct pl_desc_binding bindings[5] = {0};
    for (unsigned i = 0; i < 5; i++)
        bindings[i].object = buffers[i];
    for (unsigned plane = 0; plane < 3; plane++) {
        Push p = { h[4], h[5], h[6], h[7], h[8], h[9], h[10], plane,
                   c->plane_width[plane], c->plane_height[plane], c->plane_offset[plane],
                   h[12], h[13], h[14], 16, 0 };
        pl_pass_run(gpu, pl_pass_run_params(
            .pass = pass, .desc_bindings = bindings, .push_constants = &p,
            .timer = timers[plane],
            .compute_groups = { (int)((p.plane_width + LOCAL_X - 1) / LOCAL_X),
                                (int)((p.plane_height + LOCAL_Y - 1) / LOCAL_Y), 1 }));
        dispatches++;
    }
    pl_gpu_finish(gpu);
    check_gpu(gpu);
    t.dispatch_finish_ns = now_ns() - stage;
    // Timers may be unsupported or drop queries. Missing results stay explicit.
    for (unsigned plane = 0; plane < 3; plane++) {
        uint64_t ns;
        while ((ns = pl_timer_query(gpu, timers[plane]))) {
            t.kernel_ns[plane] += ns;
            t.timer_queries[plane]++;
        }
    }
    stage = now_ns();
    pl_buf read_buffer = buffers[4];
    if (staging) {
        /* Isolate readback: original device output allocation/flags stay the
         * same. The GPU copy, synchronization, and CPU read are all download. */
        pl_buf_copy(gpu, staging, 0, buffers[4], 0, plane_bytes);
        pl_gpu_finish(gpu);
        check_gpu(gpu);
        read_buffer = staging;
    }
    if (!pl_buf_read(gpu, read_buffer, 0, output, plane_bytes))
        fail(3, "setup_error", "GPU output download failed");
    pl_gpu_finish(gpu);
    check_gpu(gpu);
    t.download_ns = now_ns() - stage;
    stage = now_ns();
    compare_output(c, output, packed);
    t.pack_compare_ns = now_ns() - stage;
    t.total_ns = now_ns() - start;
    return t;
}

static void print_timing(const Timing *t, bool warmup)
{
    printf("{\"warmup\":%s,\"upload_and_poison_wall_ns\":%" PRIu64
           ",\"dispatch_finish_wall_ns\":%" PRIu64 ",\"download_wall_ns\":%" PRIu64
           ",\"pack_compare_wall_ns\":%" PRIu64 ",\"total_replay_wall_ns\":%" PRIu64
           ",\"kernel_plane_ns\":[", warmup ? "true" : "false", t->upload_ns,
           t->dispatch_finish_ns, t->download_ns, t->pack_compare_ns, t->total_ns);
    for (unsigned plane = 0; plane < 3; plane++) {
        if (plane) putchar(',');
        if (t->timer_queries[plane] == 1)
            printf("%" PRIu64, t->kernel_ns[plane]);
        else
            printf("null");
    }
    printf("],\"timer_query_counts\":[%u,%u,%u]}",
           t->timer_queries[0], t->timer_queries[1], t->timer_queries[2]);
}

int main(int argc, char **argv)
{
    const char *shader_path = "gather.comp", *output_path = NULL, *device_name = NULL;
    bool validate_only = false;
    unsigned repeats = 5;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--validate-only")) validate_only = true;
        else if (!strcmp(argv[i], "--shader") && i + 1 < argc) shader_path = argv[++i];
        else if (!strcmp(argv[i], "--device") && i + 1 < argc) device_name = argv[++i];
        else if (!strcmp(argv[i], "--readback") && i + 1 < argc) {
            readback_mode = argv[++i];
            if (strcmp(readback_mode, "direct") && strcmp(readback_mode, "staging"))
                fail(2, "validation_error", "readback must be direct or staging");
        }
        else if (!strcmp(argv[i], "--output") && i + 1 < argc) output_path = argv[++i];
        else if (!strcmp(argv[i], "--repeats") && i + 1 < argc) {
            char *end = NULL;
            errno = 0;
            unsigned long n = strtoul(argv[++i], &end, 10);
            if (errno || !*argv[i] || *end || n < 1 || n > MAX_REPEATS)
                fail(2, "validation_error", "repeats must be in 1..100");
            repeats = (unsigned)n;
        } else if (argv[i][0] == '-' || capsule_path)
            fail(2, "validation_error", "usage: replay [--validate-only] [--device exact-name] [--readback direct|staging] [--shader file] [--repeats N] [--output raw.yuv] capsule.bin");
        else capsule_path = argv[i];
    }
    if (!capsule_path)
        fail(2, "validation_error", "capsule path is required");
    uint64_t start = now_ns();
    Capsule c = load_capsule(capsule_path);
    uint64_t load_validate_ns = now_ns() - start;
    if (validate_only) {
        status_fields("validated");
        printf(",\"schema\":1,\"samples\":%u,\"width\":%u,\"height\":%u,\"alpha\":%u}\n",
               c.samples, c.h[4], c.h[5], c.h[8]);
        free(c.golden_bytes); free(c.words);
        return 0;
    }
    size_t shader_length;
    char *shader = (char *)read_file(shader_path, 1024 * 1024, &shader_length, false);
    if (!shader_length || memchr(shader, '\0', shader_length))
        fail(3, "setup_error", "shader must be nonempty text without embedded NUL");
    pl_log log = pl_log_create(PL_API_VER, pl_log_params(.log_cb = gpu_log, .log_level = PL_LOG_INFO));
    if (!log)
        fail(3, "setup_error", "libplacebo log creation failed");
    start = now_ns();
    pl_vulkan vk = pl_vulkan_create(log, pl_vulkan_params(.allow_software = false, .device_name = device_name));
    if (!vk)
        fail(3, "setup_error", "no Vulkan hardware device available");
    pl_gpu gpu = vk->gpu;
    PFN_vkGetPhysicalDeviceProperties get_properties =
        (PFN_vkGetPhysicalDeviceProperties)vk->get_proc_addr(vk->instance, "vkGetPhysicalDeviceProperties");
    if (!get_properties)
        fail(3, "setup_error", "Vulkan physical-device properties unavailable");
    VkPhysicalDeviceProperties properties;
    get_properties(vk->phys_device, &properties);
    memcpy(selected_device, properties.deviceName, sizeof(selected_device));
    selected_device[sizeof(selected_device) - 1] = 0;
    selected_hardware = properties.deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU ||
                        properties.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU;
    if (!selected_hardware)
        fail(3, "setup_error", "software/virtual/unknown device types are refused");
    if (!gpu->glsl.compute || gpu->glsl.version < 450 || gpu->limits.max_pushc_size < sizeof(Push) ||
        properties.limits.maxComputeWorkGroupInvocations < LOCAL_X * LOCAL_Y ||
        properties.limits.maxComputeWorkGroupSize[0] < LOCAL_X ||
        properties.limits.maxComputeWorkGroupSize[1] < LOCAL_Y ||
        properties.limits.maxPerStageDescriptorStorageBuffers < 5 || properties.limits.maxDescriptorSetStorageBuffers < 5)
        fail(3, "setup_error", "device lacks required compute/push/buffer limits");
    for (unsigned plane = 0; plane < 3; plane++) {
        if ((c.plane_width[plane] + LOCAL_X - 1) / LOCAL_X > gpu->limits.max_dispatch[0] ||
            (c.plane_height[plane] + LOCAL_Y - 1) / LOCAL_Y > gpu->limits.max_dispatch[1] ||
            gpu->limits.max_dispatch[2] < 1)
            fail(3, "setup_error", "plane dispatch exceeds GPU limits");
    }
    uint64_t device_init_ns = now_ns() - start;
    struct pl_desc descriptors[5] = {
        { .name = "InputA", .type = PL_DESC_BUF_STORAGE, .binding = 0, .access = PL_DESC_ACCESS_READONLY },
        { .name = "InputB", .type = PL_DESC_BUF_STORAGE, .binding = 1, .access = PL_DESC_ACCESS_READONLY },
        { .name = "Vectors", .type = PL_DESC_BUF_STORAGE, .binding = 2, .access = PL_DESC_ACCESS_READONLY },
        { .name = "Weights", .type = PL_DESC_BUF_STORAGE, .binding = 3, .access = PL_DESC_ACCESS_READONLY },
        { .name = "Output", .type = PL_DESC_BUF_STORAGE, .binding = 4, .access = PL_DESC_ACCESS_WRITEONLY },
    };
    start = now_ns();
    pl_pass pass = pl_pass_create(gpu, pl_pass_params(.type = PL_PASS_COMPUTE,
        .descriptors = descriptors, .num_descriptors = 5, .push_constants_size = sizeof(Push), .glsl_shader = shader));
    if (!pass)
        fail(3, "setup_error", "compute shader compilation/pipeline creation failed");
    uint64_t compile_ns = now_ns() - start;
    size_t sizes[5] = { (size_t)c.samples * 4, (size_t)c.samples * 4,
                        (size_t)c.h[36] * 4, (size_t)c.h[37] * 4, (size_t)c.samples * 4 };
    pl_buf buffers[5] = {0};
    pl_buf staging = NULL;
    pl_timer timers[3] = {0};
    start = now_ns();
    for (unsigned i = 0; i < 5; i++) {
        if (sizes[i] > gpu->limits.max_buf_size || sizes[i] > gpu->limits.max_ssbo_size)
            fail(3, "setup_error", "capsule section exceeds GPU storage-buffer limits");
        buffers[i] = pl_buf_create(gpu, pl_buf_params(.size = sizes[i], .storable = true,
            .host_writable = true, .host_readable = i == 4, .memory_type = PL_BUF_MEM_DEVICE));
        if (!buffers[i])
            fail(3, "setup_error", "GPU buffer allocation failed");
    }
    if (!strcmp(readback_mode, "staging")) {
        /* Host-visible, preferably host-cached transfer destination. It is not
         * a shader descriptor and contains only the GPU-produced output. */
        staging = pl_buf_create(gpu, pl_buf_params(.size = sizes[4],
            .host_readable = true, .memory_type = PL_BUF_MEM_HOST));
        if (!staging)
            fail(3, "setup_error", "host readback staging allocation failed");
    }
    for (unsigned plane = 0; plane < 3; plane++)
        timers[plane] = pl_timer_create(gpu);
    uint64_t allocation_ns = now_ns() - start;
    uint32_t *output = malloc(sizes[4]);
    uint8_t *packed = malloc(c.samples);
    if (!output || !packed)
        fail(3, "setup_error", "output host allocation failed");
    Timing timings[MAX_REPEATS + 1];
    for (unsigned i = 0; i <= repeats; i++)
        timings[i] = iteration(&c, gpu, pass, buffers, staging, timers, output, packed);
    if (output_path) {
        FILE *f = fopen(output_path, "wb");
        if (!f || fwrite(packed, 1, c.samples, f) != c.samples || fclose(f))
            fail(3, "setup_error", "packed YUV output write failed");
    }
    status_fields("success");
    printf(",\"schema\":1,\"width\":%u,\"height\":%u,\"alpha\":%u,\"samples\":%u,"
           "\"full_yuv_byte_equal\":true,\"vendor_id\":%u,\"device_id\":%u,\"driver_version\":%u,"
           "\"vulkan_api_version\":%u,\"device_uuid\":\"", c.h[4], c.h[5], c.h[8], c.samples,
           properties.vendorID, properties.deviceID, properties.driverVersion, properties.apiVersion);
    for (unsigned i = 0; i < 16; i++) printf("%02x", gpu->uuid[i]);
    printf("\",\"shader\":"); json_string(shader_path);
    printf(",\"gpu_reports_host_cached_buffers\":%s,\"staging_copy_bytes_per_iteration\":%zu",
           gpu->limits.host_cached ? "true" : "false", staging ? sizes[4] : 0);
    printf(",\"load_decode_validate_wall_ns\":%" PRIu64 ",\"device_init_wall_ns\":%" PRIu64
           ",\"compile_pipeline_wall_ns\":%" PRIu64 ",\"buffer_allocation_wall_ns\":%" PRIu64
           ",\"uploaded_bytes_per_iteration_including_poison\":%zu,\"downloaded_bytes_per_iteration\":%zu,"
           "\"warmup_iterations\":1,\"measured_iterations\":%u,\"iterations\":[",
           load_validate_ns, device_init_ns, compile_ns, allocation_ns,
           sizes[0] + sizes[1] + sizes[2] + sizes[3] + sizes[4], sizes[4], repeats);
    for (unsigned i = 0; i <= repeats; i++) {
        if (i) putchar(',');
        print_timing(&timings[i], i == 0);
    }
    puts("]}");
    for (unsigned plane = 0; plane < 3; plane++) pl_timer_destroy(gpu, &timers[plane]);
    pl_buf_destroy(gpu, &staging);
    for (unsigned i = 0; i < 5; i++) pl_buf_destroy(gpu, &buffers[i]);
    pl_pass_destroy(gpu, &pass);
    pl_vulkan_destroy(&vk);
    pl_log_destroy(&log);
    free(shader); free(output); free(packed); free(c.golden_bytes); free(c.words);
    return 0;
}
