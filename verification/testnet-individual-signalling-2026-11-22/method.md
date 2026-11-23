# Method — how an individual builds a ballot-carrying entry

Everything below ran on testnet. The same route is the
one a solo miner would use on mainnet during the poll
window (heights 3,591,200–3,629,650); only the network
and the window differ.

## 1. Your own node

Run Zebra (we used v7.1.0) on the network, fully synced,
with RPC on and a miner address of your own in the
config. Give it a reachable peer address, not a
loopback-only one: a healthy peer count (we held 40+)
is what carries a found entry to the network quickly,
and what keeps your view of the tip honest. Plan disk
room for the sync: the testnet state runs to tens of
gigabytes.

## 2. Take a template, and put the ballot in yourself

Ask the node for a block template (`getblocktemplate`).
The template's coinbase is yours to write: insert the
ballot string — `zpoll:nu7-1:` followed by the five
answers (`1` support, `2` oppose, `3` abstain, `-`
unanswered; at least one answered) and a closing `/` —
into the coinbase script, right after the height bytes,
exactly where the poll definition reads it. Our ballot:
`zpoll:nu7-1:33331/`. After editing the coinbase,
recompute the transaction identifiers and the block's
commitments from the edited bytes — the edited coinbase
changes them, and a block assembled from the template's
stale values is rejected.

## 3. Solve

Equihash 200,9 proof of work on the assembled header.
We solved with the Tromp solver (the CUDA build,
`eqcuda89`, on a rented RTX 4090 at ~245 solutions per
second; the home card managed ~15 alone, ~25 with its
CPU). One discipline matters more than raw speed:

- Short rounds. Solve in rounds of a few seconds and
  check the chain tip after every round. A winner that
  surfaces at the end of a long round races the whole
  round's length; three of our four near misses were
  lost exactly that way, by one height or by seconds.

## 4. Submit, fresh or not at all

Before submitting, check the tip once more: the
template's height must still be the next one. If the
tip has reached it, discard the candidate — a stale
submission helps no one. Submit with `submitblock`.

## 5. Count it landed only on an independent read

Your own node accepting your entry proves nothing
about the canonical chain — round 1's entry sat in our
node's best chain and was still reorganized out. The
standard we adopted: watch a public source you do not
control (we used the public lightwalletd at
testnet.zec.rocks:443) until it shows your hash
canonical at your height with at least 10
confirmations. Only then is the vote cast. If the
canonical hash at your height is a different entry,
yours was reorganized out — the honest outcome is to
say so and solve again.

## 6. Read it back

The ballot is public by design: anyone can read the
entry's coinbase and see the answers, and an
independent tally that scans coinbase script data will
count it. We read our own ballot back from the landed
entry itself (`33331`, matching what we inserted)
before calling the proof done.
