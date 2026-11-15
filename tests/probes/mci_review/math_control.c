/* Standalone arithmetic controls for mci_fused/fused_finish.
 * This does not render video or benchmark the filter. See math-review.md.
 */
#include <float.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#if FLT_RADIX != 2 || FLT_MANT_DIG != 24 || FLT_MAX_EXP != 128
#error "This control requires IEEE binary32 float"
#endif

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

static NOINLINE uint32_t direct_quotient(uint32_t n, uint32_t d)
{
    return (uint32_t)((float)n / (float)d);
}

static NOINLINE float reciprocal_product(uint32_t n, uint32_t d)
{
    /* Deliberately wrong replacement: preserve the rounded reciprocal as a
     * separate operation, even when the compiler otherwise keeps division. */
    volatile float reciprocal = 1.0f / (float)d;
    return (float)n * reciprocal;
}

static uint64_t next_random(uint64_t *state)
{
    uint64_t x = *state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return *state = x;
}

int main(void)
{
    uint64_t boundary_cases = 0, factorization_cases = 0;
    uint64_t state = UINT64_C(20261115);
    uint32_t w, k;
    int delta;

    /* Overinclusive bound: 16 accepted pairs, each uint8 weight <= 255.
     * Stock's actual largest table entry is 240, giving w <= 3840.
     * Check the rational values closest to every integer boundary. */
    for (w = 1; w <= 4080; ++w) {
        for (k = 1; k <= 255; ++k) {
            for (delta = -1; delta <= 1; ++delta) {
                const uint32_t n = (uint32_t)((int64_t)w * k + delta);
                const uint32_t expected = n / w;
                const uint32_t actual = direct_quotient(n, w);
                if (actual != expected) {
                    fprintf(stderr, "direct division mismatch: n=%u w=%u got=%u expected=%u\n",
                            n, w, actual, expected);
                    return 1;
                }
                ++boundary_cases;
            }
        }
    }

    /* The two integer floors commute exactly. Check a fixed random sample of
     * the entire permitted accumulator range, including values that might not
     * be constructible from stock's particular table weights. */
    for (k = 0; k < 100000; ++k) {
        const uint32_t rw = 1 + next_random(&state) % 4080;
        const uint64_t limit = UINT64_C(255) * 1024 * rw;
        const uint32_t sum = next_random(&state) % (limit + 1);
        const uint32_t rounded = sum + (rw << 9);
        const uint32_t n = rounded >> 10;
        const uint32_t expected = (uint64_t)rounded / (1024 * rw);
        if ((n / rw) != expected || direct_quotient(n, rw) != expected) {
            fprintf(stderr, "factorization mismatch: sum=%u w=%u\n", sum, rw);
            return 1;
        }
        ++factorization_cases;
    }

    /* Actual table weight 164, one accepted pair, midpoint, samples 0 and 1:
     * S = 164 * 512; num = 164. Exact output is 1. A rounded reciprocal
     * multiplication is one float below 1, whose truncation gives 0. */
    {
        const uint32_t weight = 164, alpha = 512, sample_a = 0, sample_b = 1;
        const uint32_t sum = weight * ((1024 - alpha) * sample_a + alpha * sample_b);
        const uint32_t n = (sum + 512 * weight) >> 10;
        const uint32_t stock = (sum + 512 * weight) / (1024 * weight);
        const uint32_t direct = direct_quotient(n, weight);
        const float wrong_float = reciprocal_product(n, weight);
        const uint32_t wrong = (uint32_t)wrong_float;
        const uint32_t max_sum = weight * 1024 * 255;
        const uint32_t max_n = (max_sum + 512 * weight) >> 10;
        const float max_r = (float)max_n / (float)weight;

        if (stock != 1 || direct != 1 || wrong != 0 || max_r != 255.5f ||
            direct_quotient(max_n, weight) != 255) {
            fputs("counterfactual or upper-bound control did not behave as registered\n", stderr);
            return 1;
        }
        printf("{\"execution_status\":\"complete\",\"boundary_cases\":%" PRIu64
               ",\"factorization_cases\":%" PRIu64
               ",\"direct_division_pass\":true,\"counterfactual\":{"
               "\"weight\":%u,\"alpha\":%u,\"sample_a\":%u,\"sample_b\":%u,"
               "\"sum\":%u,\"num\":%u,\"stock\":%u,\"direct_float\":%u,"
               "\"reciprocal_product\":%.17g,\"reciprocal_integer\":%u},"
               "\"upper_bound_quotient\":%.17g}\n",
               boundary_cases, factorization_cases, weight, alpha, sample_a, sample_b,
               sum, n, stock, direct, (double)wrong_float, wrong, (double)max_r);
    }
    return 0;
}
