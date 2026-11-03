"""Raw Zcash transaction parser for zpop: v4 (Sapling), v5 (ZIP-225) and
v6 (ZIP-229, NU6.3 Ironwood era) transactions.

Wire layouts follow the protocol specification as implemented by Zebra
(zebra-chain serialize codecs, cross-read 2026-11-03):
- v4 Sapling is interleaved: valueBalance, then Spend descriptions
  (384 B each, per-spend anchor), then Output descriptions (948 B each).
- v5/v6 Sapling is split: spend prefixes (96 B), output prefixes (756 B),
  then valueBalance, shared anchor (iff spends > 0), spend proofs (192 B),
  spend auth sigs (64 B), output proofs (192 B), binding signature.
- Orchard-protocol bundles (v5 Orchard; v6 Orchard and Ironwood alike):
  nActions, actions (820 B each); iff nActions > 0: flags, valueBalance,
  anchor, proof (CompactSize-prefixed), spend auth sigs (64 B each),
  binding signature. An absent bundle is a single zero byte.
Correctness anchors: exact buffer consumption on every parse; sha256d
txid equality for v4; agreement with lightwalletd compact counts and
Blockchair decodes for v5/v6. ZIP-244/229 txid recomputation for v5/v6 is
NOT attempted; receipts commit to the SHA-256 fingerprint of the raw
transaction bytes plus the (height, block hash, txid) anchor reported by
two independent sources."""
import hashlib, struct

class Reader:
    def __init__(self, data): self.d = data; self.p = 0
    def take(self, n):
        if self.p + n > len(self.d): raise ValueError("overrun")
        b = self.d[self.p:self.p + n]; self.p += n; return b
    def u8(self): return self.take(1)[0]
    def u32(self): return struct.unpack("<I", self.take(4))[0]
    def i64(self): return struct.unpack("<q", self.take(8))[0]
    def varint(self):
        b = self.u8()
        if b < 0xFD: return b
        if b == 0xFD: return struct.unpack("<H", self.take(2))[0]
        if b == 0xFE: return struct.unpack("<I", self.take(4))[0]
        return struct.unpack("<Q", self.take(8))[0]
    def varbytes(self): return self.take(self.varint())
    def done(self): return self.p == len(self.d)

def _transparent(r):
    vin = []
    for _ in range(r.varint()):
        prev = r.take(32); idx = r.u32(); script = r.varbytes(); seq = r.u32()
        vin.append({"prev_txid": prev[::-1].hex(), "index": idx,
                    "script_hex": script.hex(), "sequence": seq})
    vout = []
    for _ in range(r.varint()):
        val = r.i64(); script = r.varbytes()
        vout.append({"value": val, "script_hex": script.hex()})
    return vin, vout

def _sapling_v4(r):
    vb = r.i64()
    ns = r.varint()
    for _ in range(ns): r.take(384)
    no = r.varint()
    for _ in range(no): r.take(948)
    if ns + no > 0: r.take(64)
    return vb, ns, no

def _sapling_v5(r):
    ns = r.varint()
    for _ in range(ns): r.take(96)          # cv, nullifier, rk
    no = r.varint()
    for _ in range(no): r.take(756)         # cv, cmu, epk, enc580, out80
    if ns + no == 0: return 0, 0, 0
    vb = r.i64()
    if ns > 0: r.take(32)                   # shared anchor
    for _ in range(ns): r.take(192)         # spend proofs
    for _ in range(ns): r.take(64)          # spend auth sigs
    for _ in range(no): r.take(192)         # output proofs
    r.take(64)                              # binding signature
    return vb, ns, no

def _orchard_bundle(r):
    n = r.varint()
    if n == 0: return 0, 0, None
    for _ in range(n): r.take(820)
    flags = r.u8(); vb = r.i64(); anchor = r.take(32)
    r.varbytes()                            # Halo 2 proof
    for _ in range(n): r.take(64)           # spend auth sigs
    r.take(64)                              # binding signature
    return vb, n, {"flags": flags, "anchor": anchor.hex()}

def parse_tx(data: bytes) -> dict:
    r = Reader(data)
    header = r.u32()
    version = header & 0x7FFFFFFF
    out = {"version": version, "overwintered": bool(header >> 31), "raw_len": len(data),
           "raw_sha256": hashlib.sha256(data).hexdigest()}
    if version == 4:
        out["version_group_id"] = r.u32()
        vin, vout = _transparent(r)
        out["lock_time"] = r.u32(); out["expiry_height"] = r.u32()
        vb, ns, no = _sapling_v4(r)
        njs = r.varint()
        if njs > 0:
            # JoinSplit description size depends on the Sprout proof system:
            # 1802 B with PHGR proofs (pre-Sapling), 1698 B with Groth16
            # proofs (Sapling era). Exact total consumption arbitrates.
            rest = len(data) - r.p
            for size in (1698, 1802):
                if size * njs + 96 == rest:
                    r.take(size * njs); break
            else:
                raise ValueError("joinsplit section size mismatch")
            r.take(32); r.take(64)  # joinSplitPubKey + joinSplitSig
        out.update({"vin": vin, "vout": vout, "value_balance_sapling": vb,
                    "sapling_spends": ns, "sapling_outputs": no, "joinsplits": njs,
                    "value_balance_orchard": 0, "orchard_actions": 0,
                    "value_balance_ironwood": 0, "ironwood_actions": 0})
        if not r.done(): raise ValueError(f"v4 parse left {len(data)-r.p} bytes")
        out["txid"] = hashlib.sha256(hashlib.sha256(data).digest()).digest()[::-1].hex()
        return out
    if version in (5, 6):
        out["version_group_id"] = r.u32()
        out["consensus_branch_id"] = r.u32()
        out["lock_time"] = r.u32(); out["expiry_height"] = r.u32()
        vin, vout = _transparent(r)
        vb, ns, no = _sapling_v5(r)
        vbo, nao, _ = _orchard_bundle(r)
        out.update({"vin": vin, "vout": vout, "value_balance_sapling": vb,
                    "sapling_spends": ns, "sapling_outputs": no,
                    "value_balance_orchard": vbo, "orchard_actions": nao,
                    "value_balance_ironwood": 0, "ironwood_actions": 0})
        if version == 6:
            vbi, nai, _ = _orchard_bundle(r)
            out["value_balance_ironwood"] = vbi
            out["ironwood_actions"] = nai
        if not r.done(): raise ValueError(f"v{version} parse left {len(data)-r.p} bytes")
        return out
    raise ValueError(f"unsupported tx version {version}")
