// Stock Niko1221/Strata v0.2.22 engine/src/core/nv_defaults.cpp:1-220; read as data only.
// Source SHA-256: f96214a35c62fe5cd8eb201caf5d0734135cd8ebbf9ac92816c492d7d946fc31
// Payload SHA-256: 838fc50a9f56662055d31978e51c1bf922d0f4113fb96ef386ea44ddd013b678
// Stock payload follows.
// src/core/nv_defaults.cpp - see include/strata/core/nv_defaults.hpp.
#include "strata/core/nv_defaults.hpp"

#include "strata/core/defaults_026.hpp"
#include "strata/core/emulate.hpp"
#include "strata/core/sm120_series.hpp"
#include "strata/prefill/fused_tile_rule.hpp"

#include <cstdio>
#include <cstdlib>

namespace strata::core {

namespace {
bool off(const char* name) {
    const char* v = std::getenv(name);
    return v != nullptr && v[0] == '0';
}
}  // namespace

bool adapt_fetch_default_card(int major, int minor, uint64_t vram_bytes) {
    const int cc = strata::cc_of(major, minor);
    if (vram_bytes == 0) return false;
    if ((cc / 10) == 12) return vram_bytes <= kAdaptFetchMaxVramBytes;
    if (cc == 86 || cc == 89) return vram_bytes <= kAdaptFetchLowVramBytes;
    return false;
}

std::vector<std::pair<std::string, std::string>> nv_default_env(int major, int minor) {
    return nv_default_env(major, minor, strata::qwen_defaults_026());
}

std::vector<std::pair<std::string, std::string>> nv_default_env(int major, int minor, bool defaults026) {
    return nv_default_env(major, minor, defaults026, 0);
}

std::vector<std::pair<std::string, std::string>> nv_default_env(int major, int minor, bool defaults026, uint64_t main_vram_bytes) {
    std::vector<std::pair<std::string, std::string>> t;
    const int cc = strata::cc_of(major, minor);
    const int mj = cc / 10, mn = cc % 10;
    if (mj == 8 && mn == 6) {
        if (off("STRATA_SM86_PERF")) return t;
        t = {
            // 148-nv, RTX 3060 + RTX A4000 (IQ3_XXS, default flags, 8 pairs): the stack +9.6% / +14.6% (8/8 each), identity gate IDENTICAL.
            // Each is in because removing it from the full stack cost speed on a card (drop-one, 4 rounds) and saved none on the other.
            // Repeatable output (0.2.15, option 2 of phaseA-tests/par/RESULTS-REPEAT.md (d)): STRATA_ADAPT_NOWAIT=1 is no longer a default here.
            // With it, a verify window ran a swapped-in expert on the GPU or the CPU by its copy's timing, and two starts of the same request
            // differed (RTX A6000, fixed draft table: 7 of 24 requests identical; without it 24 of 24 in 3 of 3 starts).  Its cost there:
            // decode 0.988 [0.969, 1.002] over 3 pairs.  It was in the stack for "A4000 -6.3 points when removed (with ADAPT_LAG), 3060 -0.8";
            // ADAPT_LAG=2 stays, so the copies still get two windows to land.  STRATA_ADAPT_NOWAIT=1 brings it back.
            {"STRATA_ADAPT_LAG", "2"},
            {"STRATA_CPU_IQ_ALL_EXACT1", "1"},   // A4000 -3.3, 3060 -0.6
            {"STRATA_SIDE_MIXER", "2"},          // A4000 -1.2, 3060 -2.3
            {"STRATA_ATTN_DAILY", "1"},          // -1.2, -1.3
            {"STRATA_GR_UP75", "1"},             // -0.9, -1.8
            {"STRATA_GU_SWIGLU", "1"},           // -0.8, -1.4
            {"STRATA_QSA_ROWS", "1"},            // -0.5, -1.2
            {"STRATA_B6_MMVQ_ROWS", "1"},        // A4000 0, 3060 -1.7
            // 0.2.19 sm_86 (RTX 3090 24 GB / A4000 16 GB): bit-exact pipeline/PLE fusions + fused K-quant prompt
            // kernels. (#6583: STRATA_QFUSE=1 stays opt-in on sm_86 — it overrides STRATA_GR_UP75=1 and disables
            // 1-token self_commit, regressing sm_86 partial-VRAM decode by ~5%. STRATA_HC_Q8=1 also stays opt-in.)
            {"STRATA_DEQUANT_SIDE", "1"},
            {"STRATA_LFUSE", "1"},
            {"STRATA_PLE_COMPACT", "1"},
            {"STRATA_PLE_COPY_STREAM", "1"},
            {"STRATA_PF_FUSED_KQ", "1"},
            // 0.2.20 sm_86 consumer parity (RTX 3070 8 GB / 3060 12 GB): exact kernels matching sm_89/sm_120
            {"STRATA_HC_UPMIX", "1"},
            {"STRATA_Q80_ROWS1", "1"},
            {"STRATA_EXP_MODE", "8"},
            {"STRATA_PREFILL_CPU_SHARE_NT", "32"},
        };
        if (!defaults026 && adapt_fetch_default_card(major, minor, main_vram_bytes)) t.push_back({"STRATA_ADAPT_FETCH", "2"});
        else if (main_vram_bytes > kAdaptFetchMaxVramBytes) t.push_back({"STRATA_VERIFY_DEVICE_HITS", "1"});
    } else if (mj == 8 && mn == 9) {
        // RTX 40 / Ada Lovelace (compute capability 8.9: RTX 4090 / 4080 / 4070 / RTX 6000 Ada).
        // #6462 measured the sm_86 bit-exact set (+6%, KL 0.00000) and CPU share 32/6144 (-26% 3K follow-up TTFT) on RTX 4090.
        // #6431: STRATA_L2_PF=1 stays opt-in (regressed PCIe-streaming decode by 8-12% on partial-VRAM cards).
        // #6583: STRATA_QFUSE=1 stays opt-in alongside STRATA_GR_UP75=1 (overrides GR_UP75 and disables 1-token self_commit,
        // regressing partial-VRAM decode by ~5%).
        // STRATA_SM89_PERF=0 and STRATA_DEFAULTS=026 leave it out.
        if (off("STRATA_SM89_PERF") || defaults026) return t;
        t = {
            {"STRATA_ADAPT_LAG", "2"},
            {"STRATA_ATTN_DAILY", "1"},
            {"STRATA_GR_UP75", "1"},
            {"STRATA_GU_SWIGLU", "1"},
            {"STRATA_QSA_ROWS", "1"},
            {"STRATA_B6_MMVQ_ROWS", "1"},
            {"STRATA_HC_UPMIX", "1"},
            {"STRATA_Q80_ROWS1", "1"},
            {"STRATA_EXP_MODE", "8"},
            {"STRATA_SIDE_MIXER", "2"},
            {"STRATA_DEQUANT_SIDE", "1"},
            {"STRATA_LFUSE", "1"},
            {"STRATA_PLE_COMPACT", "1"},
            {"STRATA_PLE_COPY_STREAM", "1"},
            {"STRATA_PF_FUSED_KQ", "1"},
            {"STRATA_PREFILL_CPU_SHARE_NT", "32"},
            {"STRATA_PREFILL_CPU_SHARE_MAX", "6144"},
        };
        if (adapt_fetch_default_card(major, minor, main_vram_bytes)) t.push_back({"STRATA_ADAPT_FETCH", "2"});
        else if (main_vram_bytes > kAdaptFetchMaxVramBytes) t.push_back({"STRATA_VERIFY_DEVICE_HITS", "1"});
    } else if (mj == 12 && mn == 0) {
        // RTX 50 / PRO Blackwell (compute capability 12.0; a gfx12 HIP card reports 12.0 too, but this table is applied by the CUDA build only).  STRATA_SM120_PERF=0 and STRATA_DEFAULTS=026 leave it out.
        if (off("STRATA_SM120_PERF") || defaults026) return t;
        t = {
            // the hyper-connection read's fused up projection + mix (gr_upmix), chunks of 33+ tokens.  BW-13 (RTX 5090, UD-Q4_K_XL): BASE-05 identity 27 of 27 (9 prompts, 3 cold starts, up to
            // 31,817 tokens) against the baseline of the released engine; STRATA_HC_UPMIX_CHECK on an 8K prompt: mixed rel RMS 0, max |diff| 0 (the fused kernel is the default pair's bits).
            // STRATA_HC_UPMIX=0 is the way back.  (phaseA-tests/bw/RESULTS-BW-A.md)
            {"STRATA_HC_UPMIX", "1"},
            // #6431: STRATA_L2_PF=1 stays opt-in on sm_120 (regressed NVFP4 batch decode on 2x RTX 5090, IQ3_S on 4x RTX 5080,
            // and 1x RTX 5090 IQ3_S by 8-12% when enabled by default).
            // the one-row-per-block Q8_0 dense kernel (each row keeps its own partial sums: the two-row kernel's bits)
            {"STRATA_Q80_ROWS1", "1"},
            // the grouped native experts' mode-8 layout (the GB10 / P100 / P40 default; exact against the CUDA layout on UD-Q4_K_XL)
            {"STRATA_EXP_MODE", "8"},
            // 0.2.19 sm_120 (RTX 5090 / RTX PRO 5000 Blackwell): exact overlap/PLE/quant fusions (0.000 pts on 11,121-tok
            // force_check) + fused K-quant prompt kernels + wide CPU prefill share + native sm_120a mxf4nvf4 NVFP4 prefill.
            {"STRATA_SIDE_MIXER", "2"},
            {"STRATA_DEQUANT_SIDE", "1"},
            {"STRATA_QFUSE", "1"},
            {"STRATA_LFUSE", "1"},
            {"STRATA_PLE_COMPACT", "1"},
            {"STRATA_PLE_COPY_STREAM", "1"},
            {"STRATA_PF_FUSED_KQ", "1"},
            {"STRATA_PREFILL_CPU_SHARE_NT", "32"},
            {"STRATA_PREFILL_NVFP4", "w4a4"},
        };
        // 0.2.17 (owner yes 11-19), a card of 16 GiB or less: the PCIe share also fills the expert cache (not bit-exact: CPU and GPU round differently; the tier is not deterministic).
        // BW-9 (2x RTX 5060 Ti 16 GB, UD-Q4_K_XL, DFlash2 spec 6, tail skip OFF, product flags, 3 paired rounds; phaseA-tests/bw/RESULTS-BW-F.md): decode +4 to +43% by kind (medians 1.087 to 1.325, 3 of 3 rounds up),
        // expert cache hit rate 54.4 -> 62.0%, forced-token KL against the FP16 prompt path 0.948 [0.830, 1.063] of the default's (PASS), prompts level except json 169 at +3 to +5%.  Applies to a one-card run only
        // (the engine turns it off, with a line, for a layer split, helper cards, --batch and the other cases of the DETAILS.md row).  STRATA_ADAPT_FETCH=0 is the way back.
        if (adapt_fetch_default_card(major, minor, main_vram_bytes)) t.push_back({"STRATA_ADAPT_FETCH", "2"});
        else if (main_vram_bytes > kAdaptFetchMaxVramBytes) t.push_back({"STRATA_VERIFY_DEVICE_HITS", "1"});
    } else if (mj == 7 && mn == 0) {
        // Volta (Tesla V100 / Titan V / Quadro GV100, sm_70): 21 validated bit-exact switches measured on locked-clock
        // dual V100-SXM2-16GB (200 W / 1020 MHz and 300 W / 1530 MHz SM / 877 MHz MEM; identical sha and needle checks).
        // STRATA_SM70_PERF=0 and STRATA_DEFAULTS=026 leave the table out.
        if (off("STRATA_SM70_PERF") || defaults026) return t;
        t = {
            {"STRATA_ADAPT_OVERLAP", "1"},
            {"STRATA_SM70_TABLE", "1"},
            {"STRATA_B6_MMVQ_ROWS", "1"},
            {"STRATA_TSUM", "1"},
            {"STRATA_SMALL_UNR", "3"},
            {"STRATA_GR_NORM_FAST", "1"},
            {"STRATA_SIDE_MIXER", "2"},
            {"STRATA_ARGMAX_ROWS_SM70", "1"},
            {"STRATA_LFUSE", "1"},
            {"STRATA_GDN_SPLIT", "1"},
            {"STRATA_SH_STREAM", "1"},
            {"STRATA_Q80_ROWS1", "1"},
            {"STRATA_NO_MMVQ_ROWS2", "1"},
            {"STRATA_CPU_IQ_ALL_EXACT1", "1"},
            {"STRATA_GR_Q8_DOWN_MODE", "2"},
            {"STRATA_GR_Q8_UP_COLS", "16"},
            {"STRATA_GR_Q8_UP_MODE", "2"},
            {"STRATA_SCORES_HALVE", "1"},
            {"STRATA_SCORES_THREAD", "1"},
            {"STRATA_TOPK_SAMPLE", "1"},
            {"STRATA_SELECT_LONG", "1"},
        };
    } else if (mj == 6 && mn == 0) {
        if (off("STRATA_SM60_PERF")) return t;
        t = {
            // 148-nv, Tesla P100 (IQ3_XXS, default flags, 8 pairs): the stack +17.8% (8/8), identity gate IDENTICAL.
            {"STRATA_ADAPT_NOWAIT", "1"},        // -10 points when removed (with ADAPT_LAG)
            {"STRATA_ADAPT_LAG", "2"},
            {"STRATA_SIDE_MIXER", "2"},          // -1.8
            {"STRATA_FUSE_WAIT", "2"},           // -1.6
            {"STRATA_B6_MMVQ_ROWS", "1"},        // -1.3
            {"STRATA_FUSE_DECODE", "1"},         // -1.3
            {"STRATA_GR_UP75", "1"},             // -1.2
        };
    } else if (mj == 12 && mn == 1) {
        // GB10 (NVIDIA DGX Spark, 48 SMs, unified memory): only what was measured on that part goes in.  New in 0.2.7.1, so
        // STRATA_DEFAULTS=026 (the master switch of everything since 0.2.6) leaves the table out, like STRATA_SM121_PERF=0.
        if (off("STRATA_SM121_PERF") || defaults026) return t;
        t = {
            // the fused IQ prompt kernels.  IQ3_S, 64K context, fresh 4K/16K/32K prompts at T=0, 3 paired rounds against
            // the same tree without it: prompt 1.139 / 1.149 / 1.121, decode unchanged; 5 of 5 greedy answers byte-
            // identical with it on and off (docs/DGX_SPARK_LINUX.md; HANDOVER §6.2).  It rounds differently from MMQ,
            // so it is a default with an off switch, like the sm_86 table.
            {"STRATA_PF_FUSED", "1"},
            // the same fused prompt kernels for the K-quant experts of Unsloth's UD-Q4_K_XL files (Q4_K / Q5_K gate/up, Q5_1 / Q8_0 down) instead of llama.cpp's MMQ.
            // UD-Q4_K_XL (Flash-Next), expert cache budget 12000 (15,283 of 24,576 experts resident, so the box keeps over 16 GiB of its 121 GiB free), two starts a pair,
            // against the FP16 prompt path's text, 48 real-text prompts (24 at 2,048 and 24 at 4,096 tokens, 256 forced tokens each, 12,288 positions): forced-token
            // KL kq / MMQ 0.895 [0.808, 0.989] (0.864 [0.756, 0.976] at 2K, 0.928 [0.791, 1.088] at 4K), top-1 against the FP16 path's 96.31% / 95.74%, the same
            // text twice byte for byte on both sides (repeat floor 0); prompt speed kq / MMQ, 10 interleaved pairs, median of the per-round ratios 1.10 / 1.26 / 1.18 / 1.53 at 2K / 4K / 8K / 20K (faster in 7 / 8 / 8 / 9 of 10; the rounds scatter 0.5 to 2.0)
            // (phaseA-tests/par/RESULTS-SPARK-KQ.md).  STRATA_PF_FUSED_KQ=0 is the way back (a switch you set is kept); it is off with the rest of the table by STRATA_SM121_PERF=0.
            {"STRATA_PF_FUSED_KQ", "1"},
            // the hyper-connection read's fused up projection + mix (gr_upmix).  Measured on IQ3_S against the unfused read:
            // decode 1.054x [1.007, 1.089], prompt unchanged, and 24 of 24 greedy answers byte-identical (the parity test
            // src/prefill/gr_upmix_parity.cu covers it upstream).  The HC read is ~13% of a decode round here, which is
            // why a fusion on it moves the number at all.
            {"STRATA_HC_UPMIX", "1"},
            // Run the mixer's input-only QSA/GDN work on graph branches.  With the grouped experts' mode 8 selected,
            // fixed-work IQ3_S decode measured +6.68% paired median and +6.67% geometric mean over 8 balanced pairs
            // (AB +11.60%, BA +6.68%, identical 512-token output and verifier work).  The branch changes no arithmetic.
            {"STRATA_SIDE_MIXER", "2"},
            // the cost-aware MTP window: pick the verify window from what a draft costs against what it has been paying.
            // Measured on IQ3_S: decode 1.047x [1.019, 1.079], prompt unchanged, 24 of 24 greedy answers byte-identical.
            // It only changes which drafts are attempted, and every draft is verified, so the answers cannot drift.
            {"STRATA_SPEC_COST", "1"},
            // 0.2.19 sm_121 (DGX Spark GB10 Blackwell): bit-exact pipeline/PLE/quant fusions + native sm_121a mxf4nvf4
            // NVFP4 prefill (STRATA_SM121_PERF=0 or per-switch =0 turns off).
            {"STRATA_DEQUANT_SIDE", "1"},
            {"STRATA_QFUSE", "1"},
            {"STRATA_LFUSE", "1"},
            {"STRATA_PLE_COMPACT", "1"},
            {"STRATA_PLE_COPY_STREAM", "1"},
            {"STRATA_PREFILL_NVFP4", "w4a4"},
        };
        // a 12.1 part reports its unified memory, far above 16 GiB, so ADAPT_FETCH stays off and on-device verify hit planning turns on
        if (adapt_fetch_default_card(major, minor, main_vram_bytes)) t.push_back({"STRATA_ADAPT_FETCH", "2"});
        else if (main_vram_bytes > kAdaptFetchMaxVramBytes) t.push_back({"STRATA_VERIFY_DEVICE_HITS", "1"});
    }
    return t;
}
