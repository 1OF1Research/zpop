"""Window production facts: one computation path shared by the receipt
builder and the verifier, so a receipt can never drift from the method
that checks it."""
import collections
from .chain import block_facts, bc_block, _bc_get
from .subsidy import funding_streams
from .txp import parse_tx

def facts_from_compact(lwd, blks):
    facts = []
    for blk in blks:
        f = block_facts(blk)
        if f["coinbase_has_shielded"]:
            raw = lwd.transaction(blk.vtx[0].txid[::-1].hex()).data
            p = parse_tx(raw)
            shielded_received = -(p["value_balance_sapling"] + p["value_balance_orchard"]
                                  + p["value_balance_ironwood"])
            f["coinbase_shielded_received_zats"] = shielded_received
            f["coinbase_total"] += shielded_received
            miner_due, zcg_due, _ = funding_streams(f["height"])
            f["fees_zats"] = f["coinbase_total"] - (miner_due + zcg_due)
        else:
            f["coinbase_shielded_received_zats"] = 0
        facts.append(f)
    return facts

def aggregates_from_facts(facts):
    n = len(facts)
    start = facts[0]["height"]
    miner_due, zcg_due, lock_due = funding_streams(start)
    stream_votes = collections.Counter()
    for f in facts:
        for o in f["coinbase_outputs"]:
            if o["value"] == zcg_due:
                stream_votes[(o["script_hex"], o["address"])] += 1
    (script, saddr), scov = stream_votes.most_common(1)[0]
    per_addr = collections.Counter(); blocks_by_addr = collections.Counter()
    for f in facts:
        seen = set()
        for o in f["coinbase_outputs"]:
            if o["script_hex"] == script: continue
            per_addr[o["address"]] += o["value"]
            if o["address"] not in seen:
                blocks_by_addr[o["address"]] += 1; seen.add(o["address"])
    tot_subsidy = sum(f["subsidy_zats"] for f in facts)
    top = [{"address": a, "zats": v, "blocks": blocks_by_addr[a],
            "share_pct": round(100 * v / tot_subsidy, 3)} for a, v in per_addr.most_common(10)]
    return {
        "start_height": start, "end_height": facts[-1]["height"], "blocks": n,
        "first_time": facts[0]["time"], "last_time": facts[-1]["time"],
        "duration_s": facts[-1]["time"] - facts[0]["time"],
        "total_subsidy_zats": tot_subsidy,
        "total_fees_zats": sum(f["fees_zats"] for f in facts),
        "total_coinbase_zats": sum(f["coinbase_total"] for f in facts),
        "miner_base_total_zats": miner_due * n,
        "zcg_stream_total_zats": zcg_due * n,
        "lockbox_accrual_zats": lock_due * n,
        "negative_fee_blocks": [f["height"] for f in facts if f["fees_zats"] < 0],
        "shielded_coinbase_blocks": sum(1 for f in facts if f["coinbase_has_shielded"]),
        "shielded_coinbase_value_zats": sum(f["coinbase_shielded_received_zats"] for f in facts),
        "stream_address": saddr, "stream_script_hex": script,
        "stream_coverage_blocks": scov,
        "distinct_miner_addresses": len(per_addr),
        "top_miner_addresses": top,
        "total_txs": sum(f["tx_count"] for f in facts),
        "sapling_components": sum(f["sapling_components"] for f in facts),
        "orchard_actions": sum(f["orchard_actions"] for f in facts),
        "ironwood_actions": sum(f["ironwood_actions"] for f in facts),
    }

def blockchair_checks(facts):
    """Independent-source agreement for a closed window. Returns the check
    record embedded in receipts; the verifier recomputes and compares."""
    start, end = facts[0]["height"], facts[-1]["height"]
    before = bc_block(start - 1); after = bc_block(end)
    samples = {h: bc_block(h) for h in [start, (start + end) // 2, end]}
    cw = int(after["chainwork"], 16) - int(before["chainwork"], 16)
    dt = after["time"] - before["time"]
    lock_delta = after["value_pools"]["lockbox"] - before["value_pools"]["lockbox"]
    agree = {}
    by_h = {f["height"]: f for f in facts}
    for h, s in samples.items():
        f = by_h[h]
        agree[str(h)] = {"hash": s["hash"] == f["hash"], "time": s["time"] == f["time"],
                         "tx_count": s["tx_count"] == f["tx_count"]}
    # Height-pinned page: the window's last 100 blocks, selected by an
    # explicit id range so the check is reproducible forever. (The first
    # version paged by offset from Blockchair's indexed tip; that tip is
    # served inconsistently - its reported state lagged its own list by
    # 135 blocks on 2026-11-03 - so the sampled page drifted between runs
    # and a re-verification sampled zero in-window blocks. Found by the
    # 2026-11-03 online re-verification of the reference window.)
    page = _bc_get(f"/blocks?limit=100&q=id({end - 99}..{end})")
    checked = agreed = 0; disagreements = []
    for b in page["data"]:
        h = b["id"]
        if h in by_h:
            checked += 1
            if b["reward"] == by_h[h]["coinbase_total"]: agreed += 1
            else: disagreements.append(h)
    return {
        "source": "blockchair.com keyless API",
        "indexed_state_at_check": after["bc_state"],
        "hash_time_txcount_agreement": agree,
        "chainwork_delta": cw, "chainwork_span_s": dt, "avg_solps": cw / dt,
        "difficulty_samples": {str(h): samples[h]["difficulty"] for h in samples},
        "lockbox_pool_before_zats": before["value_pools"]["lockbox"],
        "lockbox_pool_after_zats": after["value_pools"]["lockbox"],
        "lockbox_pool_delta_zats": lock_delta,
        "coinbase_total_page_check": {"checked": checked, "agree": agreed,
                                      "disagreeing_heights": disagreements,
                                      "known_cause": "Blockchair's reward field counts transparent coinbase outputs only; every disagreeing height in the reference window is a shielded-coinbase block, where the consensus identity (subsidy + fees) confirms the zpop total."},
    }

def measure_addresses(facts, addresses):
    """Production attributable to a set of transparent payout addresses:
    coinbase value received and blocks in which the address was paid.
    Shielded coinbase value is not attributable from public data (by
    design of the pools) and is never assigned to anyone."""
    want = set(addresses)
    got = {a: {"zats": 0, "blocks": 0} for a in addresses}
    for f in facts:
        seen = set()
        for o in f["coinbase_outputs"]:
            if o["address"] in want:
                got[o["address"]]["zats"] += o["value"]
                if o["address"] not in seen:
                    got[o["address"]]["blocks"] += 1; seen.add(o["address"])
    tot_sub = sum(f["subsidy_zats"] for f in facts)
    total_zats = sum(v["zats"] for v in got.values())
    total_blocks = sum(v["blocks"] for v in got.values())
    return {"per_address": got, "total_zats": total_zats, "total_blocks": total_blocks,
            "share_pct": round(100 * total_zats / tot_sub, 4) if tot_sub else 0.0}
