# Testnet individual signalling — worked example (2026-11-22)

An individual miner can speak in the NU7.1 Miner Sentiment
Poll only by building a chain entry whose coinbase carries
a ballot — pools build entries on behalf of their hashrate,
so an individual inside a pool has no voice of their own.
This folder records a complete end-to-end proof that one
person, with a small setup, can do it alone: our own node
built the templates, we inserted our ballot into the
coinbase ourselves, a rented graphics card solved the
proof of work, and the entry is on the canonical testnet
chain where anyone can read it.

## The landed entry

- Height: **4,653,540** (Zcash testnet)
- Hash:
  `00001bb69e664f40147055fb370bd1bd65f78d3124dcf1d02af9b176bd0ca046`
- Ballot: `zpoll:nu7-1:33331/` — abstain on questions
  1–4, support on question 5
- Producer (coinbase payout) address:
  `tmPKP9KGzitowLKi77aHs2wyiaXH5wkRcTU`
- Submitted 2026-11-23T05:31:03Z; held canonical with 10
  confirmations at 2026-11-23T05:37:14Z on an independent
  read (public lightwalletd, testnet.zec.rocks:443)

Anyone can verify it: read the entry at height 4,653,540
from any testnet source, check the hash, and read the
ballot string in the coinbase's script data, after the
height. No trust in this folder is required.

## What is here

- `landed-entry.json` — the landed entry's facts, as
  written by the session at the landing.
- `attempts-and-near-misses.md` — every attempt across
  the whole experiment: the home-card session, round 1
  (two stale winners and a submitted entry that was
  reorganized out), and round 2 (one stale winner and
  the landing). The near misses are part of the result:
  at a small share of the network's work, a found entry
  is a race against the next one.
- `run-figures.json` — solving minutes, instances,
  rates, costs (each labelled by source), and solver
  benchmarks.
- `method.md` — the method, plainly enough to repeat:
  node, template, coinbase surgery, solver, submission,
  and the landing standard (an entry counts only when an
  independent read shows it canonical with at least 10
  confirmations).

## The honest limits

The first round's submitted entry was reorganized out —
a larger producer's competing entry at the same height
is the one the chain kept. The home graphics card
(a GTX 1650 Max-Q) solved for a day without landing:
at current testnet conditions, a machine of that size
cannot be relied on to vote within 24 hours. What made
the difference in round 2 was not a new idea, only the
same route run carefully: tight solver rounds, a fast
node, and patience measured in hours, not days. Total
spend across both rounds to the landing was about
$3.87 of rented compute (figures and sources in
`run-figures.json`).
