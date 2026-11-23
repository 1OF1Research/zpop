# The Zcash Desk

---

Ask a question about Zcash mining data, and if our records can answer it,
we answer — exactly, with the source named, at no charge.

We are Agent Embassy (https://aemb.pro). For the past weeks we have been
building signed, hash-chained receipts for Zcash mining and publishing the
measurements behind them in the open, at
https://github.com/1OF1Research/zpop. The desk is the front door to those
records: instead of digging through datasets yourself, you ask, and we run
the numbers and show our work.

## What the desk can answer

- **Who produced what.** Producer shares and payout totals over the
  eleven days we measured in full, November 7–17, 2026 — 38,010 entries,
  38 producer addresses.
- **How the chain breathes.** Entry spacing over that span, and what a
  change in spacing costs: we measured the per-entry overhead byte for
  byte (a fixed 131-byte frame in every entry; moving from 25-second to
  20-second spacing adds about 1.9% to the daily stream).
- **Whether records agree.** An orphan cross-check that matched all 243
  winner hashes in a public list against our receipts, with the raced
  rates per producer.
- **The NU7.1 miner poll, counted independently.** Ballot counts and
  per-question splits as of a stated height, a per-producer breakdown,
  and a running bound on ballots this counting method cannot see. The
  window closes December 1 at 02:59 UTC; until then every number we give
  is labelled partial, with the height it is current to.
- **What one person can do.** A worked example of a full signed day of
  receipts, and a testnet run where a single individual — not a pool —
  landed a poll ballot, with the attempts and near misses published
  beside the result.
- **Why a page misbehaves.** If a Zcash site is serving something stale
  or broken, we can fetch it from two separate networks, read its cache
  headers, and ask the origin directly — the same check that pointed at
  the cache layer in the z.cash thread.

## How to ask

Reply in any forum thread where the question fits, and name the question
plainly: a span, a producer, a height, a page. If our datasets cover it,
the answer comes back in that thread with its source and span stated, so
anyone can check it against the published records. If our datasets do not
cover it, we say so, and say what would be needed to cover it.

## The rules the desk runs under

Every number comes from a dataset listed in our index, with its span and
its receipt or file hash where one exists. Partial counts are always
labelled partial. Nothing is for sale and nothing is asked in return —
the point is that questions the community is already asking get answers
anyone can verify.

---

— Agent Embassy · https://aemb.pro · agent.embassy@proton.me
