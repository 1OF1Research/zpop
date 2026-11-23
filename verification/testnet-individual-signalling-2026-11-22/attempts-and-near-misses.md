# Every attempt and near miss

All times CST (UTC-6) unless marked Z. A "winner" is a
proof-of-work solution the solver found for one of our
templates. A winner only matters if the chain's tip has
not already passed the template's height — testnet
produces entries in bursts far faster than its 75-second
average, so a winner that surfaces late in a long solver
round is stale on arrival. Nothing stale was ever
submitted; a freshness gate checks the tip before every
submission.

## The home-card session (2026-11-21)

Setup: the house's own small card, a GTX 1650 Max-Q,
plus its CPU — about 24–25 solutions/second combined.
Ran 2026-11-21 10:43 CST to 2026-11-22 ~04:56 CST.

- 2026-11-21 13:34:49 — one GPU winner found, stale by
  two heights when it surfaced. Never submitted.
- No landing in ~18 hours. This is the measured basis
  for the finding the worked example carries: at
  current testnet conditions, a machine of this size
  cannot be relied on to vote within 24 hours.

## Round 1 — first rental (2026-11-22)

RTX 4090 (Vast.ai instance 61978101, $0.353/hr), solver
rounds of 2,600 nonces at first. Total solving
128.5 minutes.

- 08:41:28 — GPU winner, byte-128 counter 323,616.
  Tip 4,651,394 against template height 4,651,393:
  stale by one height, discarded by the gate.
- 09:35:12 — GPU winner, byte-128 counter 672,436.
  Tip 4,651,520 against template height 4,651,519:
  stale by one height, discarded by the gate.
- The solver round was then tightened from 2,600 to
  500 nonces, so a winner surfaces within seconds.
- 10:06:32 — winner four seconds after its template
  was taken; submitted for height 4,651,586, hash
  `00002bd844964887ff61d249cab209591630f9f5ac3d8cadeadfcf6c4d2febe2`.
  Our own node held it in its best chain with the
  ballot read back — and the canonical chain kept a
  competing entry at the same height instead:
  `00002d53cca53bd1a088c901ecf74671e9ed845572db040effb55092f793ec14`,
  built by a large pool (its coinbase reads "Foundry
  Zcash Pool #PrivacyMatters", ballot 33332, producer
  `t1c6b9F3igRCA3JpdtrDAcFx7EkmNwEWcHP`). Our entry was
  reorganized out. Anyone can check both hashes at
  height 4,651,586: only the second is canonical.

Round 1's lesson became round 2's landing standard: a
submission is not a landing. An entry counts only when
an independent read shows it canonical with at least
10 confirmations.

## Round 2 — rebuilt and re-run (2026-11-22)

Same ballot, same address, same route; node rebuilt
with a reachable peer address, tight solver rounds
from the start, and the new landing standard. A
second rented card joined in parallel for the final
stretch.

- 22:44:57 — GPU winner, byte-128 counter 660,641,
  for template height 4,653,411. The tip reached
  4,653,411 in the same second the winner arrived;
  discarded by the gate, never submitted. The winner
  came 11 seconds into its template — the closest
  timing of all the near misses.
- 23:31:03 — GPU winner, byte-128 counter 1,045,182.
  Submitted 23:31:04 for height 4,653,540, hash
  `00001bb69e664f40147055fb370bd1bd65f78d3124dcf1d02af9b176bd0ca046`;
  held in our node's best chain at 23:31:06 with the
  ballot read back (33331); canonical on the
  independent read with 4 confirmations at 23:34:41,
  5 at 23:35:11, 7 at 23:36:13, and 10 at 23:37:14 —
  landed. A second rented card (instance 62101676)
  had started solving in parallel at 23:31:30, 27
  seconds after this winner was found; it stood down
  the second the landing was written.
