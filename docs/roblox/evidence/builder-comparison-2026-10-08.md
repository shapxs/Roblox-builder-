# Builder comparison: AT-003 repair task (production gate path), 2026-10-08

Same task (HUD label -> CASH, with a planted runtime-only bug in the server join code),
same gates (format, lint, typecheck, unit + policy invariants, build, roblox-studio core),
same reviewer (qwen3.8:27b, review think=False). One run each: a smoke comparison, not a
benchmark.

| | qwen3.8-flash-next:125b-mlx (current live builder) | qwen3-coder-next:q8_0 |
|---|---|---|
| Outcome | HUMAN_BLOCKED (review rejected twice; builder budget exhausted) | COMPLETE, merged |
| Total | 9.8 min | 1.9 min |
| First build | 45 s | 39 s |
| Repairs | 297 s + 155 s | 32 s |
| Reviews | 41 s + 33 s (repair, repair) | 30 s (accept) |
| Fix chosen | deleted the bonus code; then replaced it with `state.cash += 10` (behaviour change) | nil-guard keeping the intended behaviour |

For reference, the first AT-003 run (current builder, reviewer with reasoning on) took
21.0 min, 51% of it in two ~5-minute reviews.

Takeaways:
- Review with think=False: ~30-40 s per review vs ~5 min. Verdicts in both runs were
  defensible (deletion and behaviour change rejected, minimal fix accepted).
- qwen3-coder-next produced the minimal, intent-preserving fix fast. Worth a proper
  30-50 task benchmark before changing the live builder; n=1 proves nothing on its own.
- Gates (all six, including Studio) cost ~5 s per pass.
