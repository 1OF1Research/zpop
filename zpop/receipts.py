"""ZPOP receipts: canonical JSON, Ed25519-signed, hash-chained.

A receipt binds (a) a set of facts, (b) the evidence they were derived
from, and (c) the previous receipt's hash, under an issuer signature.
Verification has two independent layers: the signature layer (anyone,
offline, proves the issuer committed to exactly these bytes and the
chain is intact) and the fact layer (recompute the facts from the chain,
online, or from the hash-pinned dataset, offline)."""
import hashlib, json, datetime
from . import core

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def issue(kind, facts, issuer_name, issuer_seed: bytes, prev_hash, evidence=None, issued_at=None):
    pub, _, _ = core.ed25519_keypair(issuer_seed)
    body = {
        "type": "zpop.receipt", "version": 1, "kind": kind,
        "issuer": {"name": issuer_name, "public_key": pub.hex()},
        "issued_at": issued_at or now_iso(),
        "facts": facts, "evidence": evidence or {},
        "prev_receipt": prev_hash,
    }
    digest = sha256_hex(canonical(body))
    sig = core.ed25519_sign(issuer_seed, bytes.fromhex(digest))
    body["receipt_sha256"] = digest
    body["signature"] = sig.hex()
    return body

def verify_signature(receipt) -> bool:
    body = {k: v for k, v in receipt.items() if k not in ("receipt_sha256", "signature")}
    digest = sha256_hex(canonical(body))
    if digest != receipt.get("receipt_sha256"): return False
    try:
        pub = bytes.fromhex(receipt["issuer"]["public_key"])
        sig = bytes.fromhex(receipt["signature"])
    except Exception:
        return False
    return core.ed25519_verify(pub, bytes.fromhex(digest), sig)

def check_chain(receipts):
    """receipts in issuance order; returns list of per-receipt problems."""
    problems = []
    prev = None
    for r in receipts:
        if r.get("prev_receipt") != prev:
            problems.append(f"{r.get('kind')}: prev_receipt mismatch")
        if not verify_signature(r):
            problems.append(f"{r.get('kind')}: signature invalid")
        prev = r.get("receipt_sha256")
    return problems
