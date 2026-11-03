"""Chain data layer for zpop: two independent public sources.

Source A (structure): lightwalletd over gRPC/TLS (default zec.rocks:443) -
compact blocks with full coinbase outputs and shielded component counts.
Source B (cross-check): Blockchair keyless API - per-block difficulty,
chainwork, coinbase totals ('reward'), timestamps, transaction counts.

Fees note (measured 2026-11-03): Blockchair's fee_total does not reconcile
on blocks containing shielded transactions (it nets transparent inputs and
outputs across shielded bundles), so fees are derived from the coinbase
identity total = subsidy + fees, and Blockchair is used only where it is
exact: difficulty, chainwork, timestamps, counts, coinbase totals."""
import json, sys, time, urllib.request
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import grpc
import service_pb2 as sp, service_pb2_grpc as sg
from .core import script_to_address
from .subsidy import subsidy_zats, funding_streams

LWD_MAINNET = "zec.rocks:443"
LWD_TESTNET = "testnet.zec.rocks:443"
POOLS = [sp.TRANSPARENT, sp.SAPLING, sp.ORCHARD, sp.IRONWOOD]

class Lightwalletd:
    def __init__(self, endpoint=LWD_MAINNET):
        self.endpoint = endpoint
        self.stub = sg.CompactTxStreamerStub(
            grpc.secure_channel(endpoint, grpc.ssl_channel_credentials()))
    def info(self):
        i = self.stub.GetLightdInfo(sp.Empty(), timeout=30)
        return {"version": i.version, "vendor": i.vendor, "chain": i.chainName,
                "height": i.blockHeight, "branch": i.consensusBranchId}
    def tip(self):
        b = self.stub.GetLatestBlock(sp.ChainSpec(), timeout=30)
        return b.height, b.hash[::-1].hex()
    def block(self, height):
        rng = sp.BlockRange(); rng.start.height = height; rng.end.height = height
        rng.poolTypes.extend(POOLS)
        for blk in self.stub.GetBlockRange(rng, timeout=60):
            return blk
        raise RuntimeError(f"no block at {height}")
    def blocks(self, start, end, chunk=200):
        out = []
        h = start
        while h <= end:
            rng = sp.BlockRange(); rng.start.height = h; rng.end.height = min(h + chunk - 1, end)
            rng.poolTypes.extend(POOLS)
            for blk in self.stub.GetBlockRange(rng, timeout=120):
                out.append(blk)
            h += chunk
        return out
    def transaction(self, txid_hex_display):
        f = sp.TxFilter(); f.hash = bytes.fromhex(txid_hex_display)[::-1]
        return self.stub.GetTransaction(f, timeout=30)

def block_time(lwd, height):
    return lwd.block(height).time

def resolve_window(lwd, t_start, t_end):
    """First height with time >= t_start, last height with time < t_end."""
    tip, _ = lwd.tip()
    def first_ge(t, lo, hi):
        while lo < hi:
            mid = (lo + hi) // 2
            if block_time(lwd, mid) >= t: hi = mid
            else: lo = mid + 1
        return lo
    start = first_ge(t_start, 0, tip)
    end = first_ge(t_end, start, tip) - 1
    return start, end

def coinbase_facts(blk, network="mainnet"):
    cb = blk.vtx[0]
    outs = []
    for o in cb.vout:
        kind, addr = script_to_address(o.scriptPubKey, network)
        outs.append({"value": o.value, "script_hex": o.scriptPubKey.hex(),
                     "kind": kind, "address": addr})
    return outs

def block_facts(blk, network="mainnet"):
    h = blk.height
    miner_base, zcg_due, lockbox_due = funding_streams(h)
    outs = coinbase_facts(blk, network)
    cb_total = sum(o["value"] for o in outs)
    fees = cb_total - (miner_base + zcg_due)
    sap = sum(len(t.spends) + len(t.outputs) for t in blk.vtx)
    orc = sum(len(t.actions) for t in blk.vtx)
    irn = sum(len(t.ironwoodActions) for t in blk.vtx)
    cbx = blk.vtx[0]
    cb_shielded = {"sapling_spends": len(cbx.spends), "sapling_outputs": len(cbx.outputs),
                   "orchard_actions": len(cbx.actions), "ironwood_actions": len(cbx.ironwoodActions)}
    return {
        "height": h,
        "hash": blk.hash[::-1].hex(),
        "time": blk.time,
        "tx_count": len(blk.vtx),
        "coinbase_outputs": outs,
        "coinbase_total": cb_total,
        "subsidy_zats": subsidy_zats(h),
        "fees_zats": fees,
        "sapling_components": sap,
        "orchard_actions": orc,
        "ironwood_actions": irn,
        "coinbase_shielded": cb_shielded,
        "coinbase_has_shielded": any(cb_shielded.values()),
    }

# ---------------- Blockchair ----------------
BC = "https://api.blockchair.com/zcash"

def _bc_get(path, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(BC + path, headers={"User-Agent": "zpop/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            last = e; time.sleep(2 * (i + 1))
    raise RuntimeError(f"blockchair {path} failed: {last}")

def bc_block(height):
    """Exact per-block cross-check fields from Blockchair's raw node dump.
    Raises if the height is above Blockchair's indexed state (their Zcash
    indexer lags the tip; the error says by how much we know)."""
    d = _bc_get(f"/raw/block/{height}")
    data = d["data"]
    if not data:
        raise RuntimeError(f"blockchair has no block {height} yet (indexed state {d['context'].get('state')})")
    b = data[str(height)]["decoded_raw_block"]
    pools = {p["id"]: p["chainValueZat"] for p in b.get("valuePools", [])}
    return {"height": b["height"], "hash": b["hash"], "time": b["time"],
            "difficulty": b["difficulty"], "chainwork": b["chainwork"],
            "tx_count": len(b["tx"]), "bits": b["bits"],
            "value_pools": pools, "bc_state": d["context"].get("state")}

def bc_stats():
    d = _bc_get("/stats")
    return d["data"]
