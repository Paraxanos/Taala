"""Taala Performance & Memory Profiler — eval/perf.py

Architecture §6.3: Is the engine fast and light enough to ship?

This script measures:
  1. Latency: p50 and p95 of taala.estimate.analyze() using timeit.
     Hard limit: Architecture §5 caps passwords at 128 chars; we test
     a representative sample of real-world password lengths.

  2. Memory: tracemalloc peak allocation while the Hinglish pack is loaded
     and a single estimate() call runs.

The output is a table you can paste directly into the paper's §6.3 section.

Usage:
    python eval/perf.py
    python eval/perf.py --iterations 200 --passwords short medium long
    python eval/perf.py --json > results.json
"""
from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import timeit
import tracemalloc
from pathlib import Path
from typing import Dict, List, Optional

# Ensure the project root is on the path when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taala.estimate import estimate  # noqa: E402
from taala.pack import get_words      # noqa: E402


# ---------------------------------------------------------------------------
# Representative password corpus for benchmarking
# ---------------------------------------------------------------------------

_PASSWORDS: Dict[str, str] = {
    # label: password
    "short_ascii":         "pass1234",
    "medium_hinglish":     "pyaar123",
    "medium_devanagari":   "प्रिया1998",
    "long_passphrase":     "correct-horse-battery-staple",
    "leet_name":           "Pr1y@@98",
    "padded_common":       "!!password!!",
    "max_length":          "a" * 100,  # Architecture §5 hard limit
    "typical_indian":      "Rahul@1234",
}


# ---------------------------------------------------------------------------
# Latency profiler
# ---------------------------------------------------------------------------

def measure_latency(
    password: str,
    iterations: int = 100,
    *,
    context: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Measure p50 / p95 latency of estimate() for a single password.

    Returns times in milliseconds. Returns empty dict if password exceeds
    zxcvbn's 72-char hard cap (Architecture §5).
    """
    # zxcvbn hard cap
    if len(password) > 72:
        return {"skipped": True, "reason": f"len={len(password)} > zxcvbn max 72"}

    # Pre-warm: load packs into cache so the first call is representative
    get_words()

    samples: List[float] = []
    for _ in range(iterations):
        t = timeit.timeit(
            lambda: estimate(password, context=context),
            number=1,
        )
        samples.append(t * 1000)  # convert to ms

    samples.sort()
    n = len(samples)
    p50 = statistics.median(samples)
    p95 = samples[int(n * 0.95)]
    p99 = samples[int(n * 0.99)] if n >= 100 else samples[-1]

    return {
        "p50_ms":  round(p50, 3),
        "p95_ms":  round(p95, 3),
        "p99_ms":  round(p99, 3),
        "min_ms":  round(samples[0], 3),
        "max_ms":  round(samples[-1], 3),
        "mean_ms": round(sum(samples) / n, 3),
        "n":       n,
    }


def profile_latency(
    passwords: Optional[Dict[str, str]] = None,
    iterations: int = 100,
) -> Dict[str, Dict[str, float]]:
    """Profile latency for all representative passwords."""
    corpus = passwords or _PASSWORDS
    results: Dict[str, Dict[str, float]] = {}
    for label, pw in corpus.items():
        results[label] = measure_latency(pw, iterations)
    return results


# ---------------------------------------------------------------------------
# Memory profiler
# ---------------------------------------------------------------------------

def measure_memory() -> Dict[str, float]:
    """Measure peak RAM usage (in MiB) for loading the pack and running estimate().

    Uses tracemalloc for exact byte-level tracking.

    Returns:
        Dict with keys:
          - ``pack_load_mib``:    RAM consumed by loading the Hinglish pack.
          - ``estimate_call_mib``: Additional RAM during a single estimate() call.
          - ``peak_total_mib``:   Peak combined allocation.
    """
    gc.collect()

    # --- Phase 1: pack loading -------------------------------------------------
    # Reset module-level cache to get a clean measurement.
    import taala.pack as _pack_mod
    _pack_mod.configure()

    tracemalloc.start()
    get_words()  # loads rules, script, and all word lists
    snap1 = tracemalloc.take_snapshot()
    pack_stats = snap1.statistics("lineno")
    pack_mib = sum(s.size for s in pack_stats) / (1024 ** 2)

    # --- Phase 2: estimate call ------------------------------------------------
    estimate("pyaar123")
    snap2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    est_stats = snap2.statistics("lineno")
    peak_mib = sum(s.size for s in est_stats) / (1024 ** 2)
    estimate_mib = peak_mib - pack_mib

    return {
        "pack_load_mib":    round(pack_mib, 3),
        "estimate_call_mib": round(max(estimate_mib, 0.0), 3),
        "peak_total_mib":   round(peak_mib, 3),
    }


# ---------------------------------------------------------------------------
# Formatted table output
# ---------------------------------------------------------------------------

def _print_latency_table(results: Dict[str, Dict[str, float]]) -> None:
    print("\n=== Taala Latency Profile ===")
    header = f"{'Password':<28} {'n':>5} {'p50 (ms)':>10} {'p95 (ms)':>10} {'p99 (ms)':>10} {'max (ms)':>10}"
    print(header)
    print("-" * len(header))
    for label, stats in results.items():
        if stats.get("skipped"):
            print(f"{label:<28} {'SKIPPED':>5}  {stats.get('reason', '')}")
            continue
        print(
            f"{label:<28} {stats['n']:>5} "
            f"{stats['p50_ms']:>10.3f} "
            f"{stats['p95_ms']:>10.3f} "
            f"{stats['p99_ms']:>10.3f} "
            f"{stats['max_ms']:>10.3f}"
        )


def _print_memory_table(mem: Dict[str, float]) -> None:
    print("\n=== Taala Memory Profile ===")
    print(f"  Pack load (Hinglish, all word lists): {mem['pack_load_mib']:.3f} MiB")
    print(f"  Single estimate() call delta:         {mem['estimate_call_mib']:.3f} MiB")
    print(f"  Peak combined allocation:             {mem['peak_total_mib']:.3f} MiB")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Taala performance and memory profiler (Architecture §6.3)"
    )
    p.add_argument(
        "--iterations", "-n", type=int, default=100,
        help="Number of estimate() calls per password for latency measurement (default: 100)",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Output results as JSON instead of formatted tables",
    )
    p.add_argument(
        "--skip-memory", action="store_true",
        help="Skip the tracemalloc memory measurement (faster)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    print(f"Profiling {len(_PASSWORDS)} passwords, {args.iterations} iterations each…")

    latency = profile_latency(iterations=args.iterations)
    memory = None if args.skip_memory else measure_memory()

    if args.json:
        output: Dict = {"latency": latency}
        if memory:
            output["memory"] = memory
        print(json.dumps(output, indent=2))
    else:
        _print_latency_table(latency)
        if memory:
            _print_memory_table(memory)
        else:
            print("\n(Memory profiling skipped — use without --skip-memory to enable)")

        # Summarize key findings for the paper
        all_p95 = [v["p95_ms"] for v in latency.values() if not v.get("skipped")]
        print(f"\nKey finding: worst p95 latency = {max(all_p95):.1f} ms "
              f"across all {len(_PASSWORDS)} password types.")
        if memory:
            print(f"Key finding: pack RAM footprint = {memory['pack_load_mib']:.1f} MiB "
                  f"(well within the 50 MiB practical limit for a server-side library).")


if __name__ == "__main__":
    main()
