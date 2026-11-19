"""Orphan cross-check, final chain edition (2026-11-19).

Re-runs the Sovright gist comparison against the final verified zpop
chain (runs-fixed 2026-11-06 + runs3 2026-11-07..14) instead of the
superseded draft datasets the first pass used. Every gist row whose
height our receipts cover gets its winner_hash compared against the
canonical block hash in our receipts.
"""
import json, csv, collections, datetime

END = int(datetime.datetime(2026, 11, 14, 16, 2, 23, tzinfo=datetime.timezone.utc).timestamp())
ACT = 3543405
sources = [("runs-fixed", ["2026-11-06"])] + [
    ("runs3", [f"2026-11-{d:02d}" for d in range(7, 15)])]

canon = {}
per_addr_blocks = collections.Counter()
for base, days in sources:
    for d in days:
        ds = json.load(open(f"{base}/window-{d}/dataset.json"))
        r = json.load(open(f"{base}/window-{d}/receipt.json"))
        script = r["facts"]["aggregates"]["stream_script_hex"]
        for f in ds["blocks"]:
            h = f["height"]
            if h < ACT or f["time"] > END:
                continue
            best = None
            for o in f["coinbase_outputs"]:
                if o["script_hex"] == script:
                    continue
                if best is None or o["value"] > best[1]:
                    best = (o["address"], o["value"])
            canon[h] = (f["hash"], best[0] if best else None, f["time"])
            if best:
                per_addr_blocks[best[0]] += 1

rows = list(csv.DictReader(open("verification-2026-11-19/sovright-nu7-orphans-post.csv")))
in_cov = [r for r in rows if int(r["height"]) in canon]
match = mismatch = 0
bad = []
raced = collections.Counter()
for r in in_cov:
    h = int(r["height"])
    chash, producer, _ = canon[h]
    if chash == r["winner_hash"]:
        match += 1
    else:
        mismatch += 1
        bad.append(h)
    if producer:
        raced[producer] += 1

out = {
    "gist": "https://gist.github.com/zmanian/ae49ea1bcc3e3793456180606ae80f86",
    "gist_rows": len(rows),
    "canonical_blocks_in_window": len(canon),
    "rows_inside_our_coverage": len(in_cov),
    "winner_hash_matches": match,
    "winner_hash_mismatches": mismatch,
    "mismatch_heights": bad[:10],
    "raced_heights_with_transparent_winner": sum(raced.values()),
    "rows_whose_winner_was_shielded_coinbase": len(in_cov) - sum(raced.values()),
    "raced_rates_top8": [
        {"producer": a, "raced": c, "blocks": per_addr_blocks[a],
         "raced_pct_of_own_blocks": round(100 * c / per_addr_blocks[a], 2)}
        for a, c in raced.most_common(8)],
    "chain_used": "runs-fixed/window-2026-11-06 + runs3/window-2026-11-07..14 (final verified chain)",
}
json.dump(out, open("verification-2026-11-19/orphan-crosscheck.json", "w"), indent=1)
print(json.dumps(out, indent=1))
