"""zpop command line: keygen, tkeygen, window, pay, claim, claim-receipt, verify."""
import argparse, base64, datetime, json, os, secrets, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from . import core
from .chain import Lightwalletd, resolve_window
from .txp import parse_tx
from .receipts import issue, verify_signature, canonical, sha256_hex
from .claims import build_claim, verify_claim
from .window import facts_from_compact, aggregates_from_facts, blockchair_checks, measure_addresses

def _load_seed(path):
    with open(path) as f: return bytes.fromhex(f.read().strip())

def _save(path, obj, mode=0o644):
    with open(path, "w") as f: json.dump(obj, f, indent=1)
    os.chmod(path, mode)

def cmd_keygen(a):
    seed = secrets.token_bytes(32)
    with open(a.out, "w") as f: f.write(seed.hex())
    os.chmod(a.out, 0o600)
    pub, _, _ = core.ed25519_keypair(seed)
    print(f"seed written to {a.out} (0600). public key: {pub.hex()}")

def cmd_tkeygen(a):
    priv = secrets.randbelow(core._N - 1) + 1
    addr = core.pubkey_to_address(core.secp_pubkey(priv), a.network)
    _save(a.out, {"priv_hex": format(priv, "064x"), "address": addr, "network": a.network}, 0o600)
    print(f"transparent key written to {a.out} (0600). address: {addr}")

def cmd_window(a):
    lwd = Lightwalletd(a.endpoint)
    t0 = int(datetime.datetime.fromisoformat(a.day).replace(tzinfo=datetime.timezone.utc).timestamp())
    start, end = resolve_window(lwd, t0, t0 + 86400)
    blks = lwd.blocks(start, end)
    facts = facts_from_compact(lwd, blks)
    agg = aggregates_from_facts(facts)
    bc = blockchair_checks(facts)
    info = lwd.info()
    dataset = {"meta": {"lwd_info": info, "lwd_endpoint": a.endpoint,
                        "sources": ["lightwalletd (ECC LightWalletD)", "blockchair.com keyless API"],
                        "built_by": "zpop window"},
               "aggregates": agg, "blocks": facts}
    os.makedirs(a.outdir, exist_ok=True)
    ds_path = os.path.join(a.outdir, "dataset.json")
    _save(ds_path, dataset)
    ds_hash = sha256_hex(open(ds_path, "rb").read())
    r = issue("network_window",
              {"network": a.network, "day_utc": a.day, "aggregates": agg, "blockchair": bc},
              a.issuer_name, _load_seed(a.issuer_seed), a.prev,
              evidence={"dataset_sha256": ds_hash, "dataset_blocks": len(facts),
                        "lwd_endpoint": a.endpoint, "lwd_info": info})
    _save(os.path.join(a.outdir, "receipt.json"), r)
    print(f"window {a.day}: heights {start}..{end}, {len(facts)} blocks")
    print(f"dataset {ds_path} sha256 {ds_hash}")
    print(f"receipt sha256 {r['receipt_sha256']}")

def _pay_facts(lwd, txid):
    rawtx = lwd.transaction(txid)
    raw = rawtx.data; height = rawtx.height
    p = parse_tx(raw)
    blk = lwd.block(height)
    vout = []
    for o in p["vout"]:
        kind, addr = core.script_to_address(bytes.fromhex(o["script_hex"]))
        vout.append({"value": o["value"], "kind": kind, "address": addr, "script_hex": o["script_hex"]})
    fee = None; basis = "not asserted (transparent input values require prevout lookup)"
    if len(p["vin"]) == 0:
        # conservation with no transparent inputs: fee = sum(value balances) - transparent outputs
        fee = (p["value_balance_sapling"] + p["value_balance_orchard"] + p["value_balance_ironwood"]) - sum(o["value"] for o in p["vout"])
        basis = "derived: sum of pool value balances minus transparent outputs (transaction has no transparent inputs)"
    facts = {
        "txid": txid, "network": "mainnet", "height": height,
        "block_hash": blk.hash[::-1].hex(), "block_time": blk.time,
        "version": p["version"], "consensus_branch_id": format(p.get("consensus_branch_id", 0), "08x"),
        "lock_time": p.get("lock_time"), "expiry_height": p.get("expiry_height"),
        "counts": {"transparent_inputs": len(p["vin"]), "transparent_outputs": len(p["vout"]),
                   "sapling_spends": p["sapling_spends"], "sapling_outputs": p["sapling_outputs"],
                   "orchard_actions": p["orchard_actions"], "ironwood_actions": p["ironwood_actions"]},
        "value_balances_zats": {"sapling": p["value_balance_sapling"], "orchard": p["value_balance_orchard"],
                                "ironwood": p["value_balance_ironwood"]},
        "transparent_outputs": vout,
        "fee_zats": fee, "fee_basis": basis,
        "raw_len": p["raw_len"], "raw_sha256": p["raw_sha256"],
    }
    return facts, raw

def cmd_pay(a):
    lwd = Lightwalletd(a.endpoint)
    facts, raw = _pay_facts(lwd, a.txid)
    r = issue("shielded_payment", facts, a.issuer_name, _load_seed(a.issuer_seed), a.prev,
              evidence={"raw_tx_hex": raw.hex(), "lwd_endpoint": a.endpoint})
    _save(a.out, r)
    print(f"payment receipt for {a.txid} at height {facts['height']}: sha256 {r['receipt_sha256']}")

def cmd_claim(a):
    tkeys = json.load(open(a.tkeys))
    items = tkeys if isinstance(tkeys, list) else [tkeys]
    pairs = [(k["address"], int(k["priv_hex"], 16)) for k in items]
    claim = build_claim(a.operator_name, _load_seed(a.operator_seed), a.network,
                        {"start_height": a.start, "end_height": a.end}, pairs)
    _save(a.out, claim)
    print(f"claim {claim['claim_sha256']} for {len(pairs)} address(es)")

def cmd_claim_receipt(a):
    claim = json.load(open(a.claim))
    ok, problems = verify_claim(claim)
    if not ok:
        print("claim does not verify:", problems); sys.exit(1)
    w = claim["window"]
    if a.dataset:
        ds = json.load(open(a.dataset))
        facts = ds["blocks"]
        if facts[0]["height"] != w["start_height"] or facts[-1]["height"] != w["end_height"]:
            print("dataset window does not match claim window"); sys.exit(1)
    else:
        lwd = Lightwalletd(a.endpoint)
        facts = facts_from_compact(lwd, lwd.blocks(w["start_height"], w["end_height"]))
    measured = measure_addresses(facts, claim["payout_addresses"])
    r = issue("operator_production",
              {"claim_sha256": claim["claim_sha256"], "operator": claim["operator"],
               "network": claim["network"], "window": w,
               "payout_addresses": claim["payout_addresses"],
               "control_proofs_verified": True, "measured": measured},
              a.issuer_name, _load_seed(a.issuer_seed), a.prev,
              evidence={"claim": claim})
    _save(a.out, r)
    print(f"operator production receipt: {r['receipt_sha256']} measured {measured}")

def _cmp(path, want, got, problems):
    if want != got: problems.append(f"{path}: receipt {want!r} != recomputed {got!r}")

def cmd_verify(a):
    receipts = [json.load(open(p)) for p in a.receipts]
    problems = []
    prev = None
    for r in receipts:
        if r.get("prev_receipt") != prev:
            problems.append(f"{r['kind']}: chain link broken (prev_receipt mismatch)")
        if not verify_signature(r):
            problems.append(f"{r['kind']}: issuer signature INVALID")
        prev = r["receipt_sha256"]
    ds = json.load(open(a.dataset)) if a.dataset else None
    lwd = Lightwalletd(a.endpoint) if a.online else None
    for r in receipts:
        kind = r["kind"]; f = r["facts"]
        if kind == "network_window":
            if a.online:
                t0 = int(datetime.datetime.fromisoformat(f["day_utc"]).replace(tzinfo=datetime.timezone.utc).timestamp())
                s, e = resolve_window(lwd, t0, t0 + 86400)
                facts = facts_from_compact(lwd, lwd.blocks(s, e))
                _cmp("aggregates", f["aggregates"], aggregates_from_facts(facts), problems)
                try:
                    bc_now = blockchair_checks(facts)
                except Exception as e:
                    problems.append(f"blockchair: cross-check could not be recomputed ({e})")
                else:
                    # indexed_state_at_check is provenance (the indexer's
                    # tip when the check ran; Blockchair's reported state
                    # is not monotonic), not a chain fact - it is recorded
                    # in the receipt but excluded from equality.
                    bc_want = {k: v for k, v in f["blockchair"].items() if k != "indexed_state_at_check"}
                    bc_now = {k: v for k, v in bc_now.items() if k != "indexed_state_at_check"}
                    _cmp("blockchair", bc_want, bc_now, problems)
            elif ds:
                if sha256_hex(open(a.dataset, "rb").read()) != r["evidence"].get("dataset_sha256"):
                    problems.append("network_window: dataset hash does not match receipt evidence")
                _cmp("aggregates(from dataset)", f["aggregates"], aggregates_from_facts(ds["blocks"]), problems)
            else:
                problems.append("network_window: needs --online or --dataset for the fact layer (signature layer checked)")
        elif kind == "shielded_payment":
            if a.online:
                facts2, _ = _pay_facts(lwd, f["txid"])
                _cmp("payment facts", f, facts2, problems)
            else:
                raw = bytes.fromhex(r["evidence"]["raw_tx_hex"])
                if sha256_hex(raw) != f["raw_sha256"]:
                    problems.append("shielded_payment: evidence raw tx hash mismatch")
                p = parse_tx(raw)
                _cmp("counts.sapling", (f["counts"]["sapling_spends"], f["counts"]["sapling_outputs"]),
                     (p["sapling_spends"], p["sapling_outputs"]), problems)
                _cmp("counts.orchard", f["counts"]["orchard_actions"], p["orchard_actions"], problems)
                _cmp("counts.ironwood", f["counts"]["ironwood_actions"], p["ironwood_actions"], problems)
                _cmp("value_balances", f["value_balances_zats"],
                     {"sapling": p["value_balance_sapling"], "orchard": p["value_balance_orchard"],
                      "ironwood": p["value_balance_ironwood"]}, problems)
        elif kind == "operator_production":
            claim = r["evidence"]["claim"]
            ok, probs = verify_claim(claim)
            if not ok: problems += [f"operator_production claim: {p}" for p in probs]
            w = claim["window"]
            facts = None
            if a.online:
                facts = facts_from_compact(lwd, lwd.blocks(w["start_height"], w["end_height"]))
            elif ds:
                if ds["blocks"][0]["height"] == w["start_height"] and ds["blocks"][-1]["height"] == w["end_height"]:
                    facts = ds["blocks"]
            if facts is not None:
                _cmp("measured", f["measured"], measure_addresses(facts, claim["payout_addresses"]), problems)
            else:
                problems.append("operator_production: needs --online or matching --dataset for the fact layer (signature + claim layers checked)")
    if problems:
        print("VERIFY FAILED:")
        for p in problems: print(" -", p)
        sys.exit(1)
    print(f"VERIFY OK: {len(receipts)} receipt(s), signatures + chain + facts all verified")

def main():
    ap = argparse.ArgumentParser(prog="zpop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("keygen"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_keygen)
    p = sub.add_parser("tkeygen"); p.add_argument("--out", required=True); p.add_argument("--network", default="mainnet"); p.set_defaults(fn=cmd_tkeygen)
    p = sub.add_parser("window"); p.add_argument("--day", required=True); p.add_argument("--outdir", required=True)
    p.add_argument("--issuer-seed", required=True); p.add_argument("--issuer-name", default="Agent Embassy")
    p.add_argument("--prev"); p.add_argument("--endpoint", default="zec.rocks:443"); p.add_argument("--network", default="mainnet"); p.set_defaults(fn=cmd_window)
    p = sub.add_parser("pay"); p.add_argument("--txid", required=True); p.add_argument("--out", required=True)
    p.add_argument("--issuer-seed", required=True); p.add_argument("--issuer-name", default="Agent Embassy")
    p.add_argument("--prev"); p.add_argument("--endpoint", default="zec.rocks:443"); p.set_defaults(fn=cmd_pay)
    p = sub.add_parser("claim"); p.add_argument("--operator-name", required=True); p.add_argument("--operator-seed", required=True)
    p.add_argument("--tkeys", required=True); p.add_argument("--start", type=int, required=True); p.add_argument("--end", type=int, required=True)
    p.add_argument("--out", required=True); p.add_argument("--network", default="mainnet"); p.set_defaults(fn=cmd_claim)
    p = sub.add_parser("claim-receipt"); p.add_argument("--claim", required=True); p.add_argument("--out", required=True)
    p.add_argument("--issuer-seed", required=True); p.add_argument("--issuer-name", default="Agent Embassy")
    p.add_argument("--prev"); p.add_argument("--dataset"); p.add_argument("--endpoint", default="zec.rocks:443"); p.set_defaults(fn=cmd_claim_receipt)
    p = sub.add_parser("verify"); p.add_argument("receipts", nargs="+")
    p.add_argument("--dataset"); p.add_argument("--online", action="store_true"); p.add_argument("--endpoint", default="zec.rocks:443"); p.set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()
