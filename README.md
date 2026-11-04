# zpop — Zcash Proof-of-Production Receipts

**Signed, hash-chained, publicly verifiable receipts for what a Zcash mining
fleet produced** — blocks found, coinbase rewards received, production share
over a window, treasury inflows — re-verifiable by any stranger from public
chain data, without the operator exposing wallet internals or private
infrastructure.

Built by **Agent Embassy**. Completed on an encrypted laptop in our lab
(full-disk LUKS encryption), against live mainnet data.

## Why this exists

Zcash production has industrialized. The largest fleet — Cypherpunk
Technologies' mining operation, roughly a fifth of network hashrate — sits
inside a Nasdaq-listed company whose shareholders, hosts, and partners must
take its production numbers on trust. Public explorers show coinbase outputs
to *addresses*; they cannot bind production to an accountable operator (one
major explorer literally labels its miner field a guess). The missing half is
a signed operator claim with cryptographic proof of control over the payout
addresses. A zpop receipt is the two halves joined:

**receipt = public chain facts + a signed claim with proof-of-control +
a hash chain**, issued under the issuer's Ed25519 signature.

Either half alone is insufficient. Together they are audit-grade public
proof — and the tool proves negatives as rigorously as positives: a claim
over addresses the operator does not control fails verification, and a
claim over idle addresses verifies as a proven zero. That is what makes
its positives mean something.

## The three receipt kinds

1. **`network_window`** — a closed production window (the worked example is
   the full UTC day 2026-11-02: 1,149 blocks). Facts are rebuilt from two
   independent public sources and must agree: lightwalletd compact blocks
   (structure, coinbase outputs, pool component counts) and Blockchair
   (chainwork, difficulty, timestamps, per-block coinbase totals, value-pool
   deltas). The receipt reports the subsidy schedule asserted per block
   against consensus (ZIP-1016: miners 80% / ZCG 8% / coinholder lockbox
   12%), total fees, average hashrate by the node method (Δchainwork/Δtime),
   and production concentration by coinbase address. The ZCG stream address
   is *derived from the data* — the address receiving exactly 8% in ≥99% of
   blocks — never hardcoded. The 12% lockbox share is deferred-pool
   accounting per ZIP-1016 (it appears in no block output); the receipt's
   accrual figure is cross-checked against Blockchair's lockbox pool delta
   over the window, and the two agree.
2. **`shielded_payment`** — for any transaction (the engine's core; e.g. a
   shielded treasury inflow an operator chooses to disclose): the raw
   transaction is fetched and parsed (v4 Sapling, v5 Orchard, v6 Ironwood
   bundles), and the receipt binds its pool value balances, component
   counts, expiry, and anchoring block. Verification re-fetches and
   re-parses independently.
3. **`operator_production`** — an operator claim (documented JSON format:
   Ed25519 operator identity, window, payout transparent addresses, and a
   Zcash message signature — proof-of-control — per address) measured
   against the window: the verifier checks every control proof
   cryptographically (secp256k1 key recovery), then measures the claimed
   addresses' coinbase receipts. Production the operator did not produce
   cannot be claimed; shielded coinbase value is never attributed to
   anyone, because public data cannot attribute it — by design of the
   pools.

## Verify it yourself

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# offline: signatures + hash chain + facts against the bundled,
# hash-pinned dataset (proves internal consistency and issuer commitment)
python3 zpop.py verify examples/window-2026-11-02/receipt.json \
    examples/payment-f7d058/receipt.json examples/claim-demo/receipt.json \
    --dataset examples/window-2026-11-02/dataset.json

# online: every fact re-derived from the live public sources
# (this is the chain-truth check)
python3 zpop.py verify examples/window-2026-11-02/receipt.json \
    examples/payment-f7d058/receipt.json examples/claim-demo/receipt.json \
    --online

python3 tests/test_units.py      # 22 checks: crypto + consensus schedule
python3 tests/test_receipts.py   # 9 checks: tamper + forgery negatives
```

The worked example is all real mainnet data: the 2026-11-02 production day
(total subsidy 179,531,250,000 zats; 17 distinct miner payout addresses;
top address share 23.131%), one real shielded (Orchard, version 6)
transaction as a payment receipt, and a demonstration operator claim —
a clearly labelled lab identity whose fresh address honestly measures
**zero** production in the window.

## What it does not prove — stated plainly

- It attributes production only to transparent payout addresses an
  operator claims and proves control of. It does not guess owners of
  unclaimed addresses, and it never attributes shielded coinbase value.
- Blockchair is an independent cross-check, not a consensus source; where
  its fields are known to be inexact (its `reward` counts transparent
  coinbase outputs only, so shielded-coinbase blocks disagree by a known
  cause; its fee totals do not reconcile on shielded blocks), zpop says
  so in the receipt and derives the fact from the consensus identity
  instead (coinbase total = subsidy + fees).
- Offline verification proves the issuer committed to these bytes and the
  facts match the bundled dataset. Only online verification re-derives
  the facts from the chain.
- The demonstration operator is a lab identity, not a mining company.
  Cypherpunk Technologies is named as the motivation and the class of
  user this serves — it is not a user or customer of this tool, and no
  company data appears anywhere in it.

## Design notes

- One computation path is shared by the receipt builder and the verifier,
  so a receipt can never drift from the method that checks it.
- Cross-checks are reproducible by construction: every comparison is
  against closed-window chain data or height-pinned queries. (An early
  version of the Blockchair page check sampled by offset from the
  indexer's current tip; that tip is served inconsistently, so the check
  drifted between runs. It is now pinned to the window's last 100 block
  heights, and the indexer's tip at check time is recorded as provenance,
  not compared as a fact. Found and fixed 2026-11-03 by re-verifying the
  reference window online.)
- Pure Python 3.12 standard library for all cryptography (Ed25519,
  secp256k1, base58check, RIPEMD-160 implemented in `zpop/core.py` and
  `zpop/ripemd160.py`, tested against published vectors); the only
  third-party dependencies are grpcio/protobuf for the lightwalletd
  protocol.

### A receipt core, with claim families

The receipt machinery is deliberately vertical-neutral. A receipt is five
parts - an **anchor** (the public evidence the facts were re-derived
from), a **claim** (what the issuer asserts over a closed window), the
**evidence** (the facts themselves), an Ed25519 **signature** by the
issuer, and a **chain** link to the previous receipt's hash. Nothing in
`receipts.py` or in the claim format knows what kind of operation is
being proven; a claim family is the part that knows - it defines what
counts as ground truth, where the anchor lives, and how an operator
proves control of the thing it is claiming.

Zcash mining production is the first claim family, and it is first for
one reason: its anchor is a public ledger, so ground truth is free and
incorruptible and any stranger can re-derive every fact without the
operator's permission. The families named next, each with the public
anchor it would use:

- **AI compute delivery** - GPU-hours and jobs completed, proven against
  signed job manifests anchored to a public timestamping ledger, with
  the buyer's countersignature as the control proof.
- **Energy mix** - power drawn and its source mix hour by hour, proven
  against meter readings anchored to the grid operator's published
  settlement data and granular energy certificates.
- **SLA uptime** - availability against a contracted level, proven
  against independent third-party probe networks whose signed
  observations are the anchor.

In every family the same rule holds: the receipt is worth exactly what
its anchor is worth, and the receipt says which anchor it stands on.
Families whose anchors are operator-supplied are labelled as such -
the format never lets a weaker anchor borrow a stronger one's name.

## Layout

- `zpop/` — the package (`chain`, `window`, `claims`, `receipts`, `txp`,
  `subsidy`, `core`, `cli`)
- `examples/` — the worked example: window dataset + the three chained
  receipts + the demonstration claim
- `tests/` — unit and negative-path tests; every negative case names the
  tampering it must catch
- `keys/` — local key material (never committed; see `.gitignore`)

MIT licensed. See `CONTRIBUTING.md` to work on it.
