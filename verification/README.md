# Verification records

The measurements behind our Zcash forum posts in the block-spacing
thread (topic 59035), kept with the receipts so anyone can re-run
them and prove them wrong.

## overhead-2026-11-18 — per-block overhead at 25s vs 20s

Measured 2026-11-18 from the public lightwalletd service at
zec.rocks:443, over the same eleven days the NU7 receipts cover
(heights 3,546,328 to 3,584,337; 38,010 blocks).

- measure_overhead.py — the measurement script.
- per-block.csv — every block: full compact size, fixed frame,
  payload, transaction count, shielded and total outputs.
- summary.json — the results: the fixed frame is exactly 131 bytes
  in every block; at 20 seconds the growth is 113,184 bytes a day
  on a daily stream of about 5.96 MB (1.9 percent).
- phantom-153-verification.json — the check of Phantom's count from
  the same thread: in his 5,000-block sample ending at height
  3,580,346, exactly 153 blocks carry more than 250 shielded
  outputs, the first at height 3,579,935 and the last at 3,580,346,
  matching his published count exactly.

## orphan-crosscheck-2026-11-19 — the orphan list, read a second way

- sovright-nu7-orphans-post.csv — the orphan list published by
  Sovright (GitHub user zmanian, gist ae49ea1b) for NU7 activation
  to 2026-11-14.
- join_gist_final.py — compares every listed winner hash against
  the canonical block hash in our receipts, using the final
  verified chain (the 2026-11-06 window plus the 2026-11-07 to
  2026-11-14 windows).
- orphan-crosscheck.json — the result: all 243 winner hashes match
  our receipts, with no mismatches. Winner-side raced rates for
  the eight largest producers run from 0.66 to 1.04 percent of
  their own blocks, roughly in proportion to production.
