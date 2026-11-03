"""Operator claims for ZPOP: an operator binds its identity (Ed25519) to
payout transparent addresses with a proof of control per address - a
Zcash message signature over a claim-bound statement, verifiable by
anyone with secp256k1 key recovery. The claim itself is signed by the
operator identity key. Production attributed to the claimed addresses is
then measured from chain data by the verifier; the operator cannot
inflate it, and cannot claim addresses it does not control."""
import base64, hashlib, json
from . import core
from .receipts import canonical, sha256_hex

def control_message(operator_name, address, network):
    return (f"ZPOP control proof v1\n"
            f"operator: {operator_name}\n"
            f"address: {address}\n"
            f"network: {network}\n"
            f"statement: This address is a payout address of the operator named above.")

def build_claim(operator_name, operator_seed: bytes, network, window,
                addresses_with_priv: list):
    """addresses_with_priv: [(t_address, secp_priv_int), ...]"""
    pub, _, _ = core.ed25519_keypair(operator_seed)
    proofs = []
    for addr, priv in addresses_with_priv:
        msg = control_message(operator_name, addr, network)
        sig = core.zcash_sign_message(priv, msg)
        proofs.append({"address": addr, "message": msg,
                       "signature_b64": base64.b64encode(sig).decode()})
    claim = {
        "type": "zpop.operator_claim", "version": 1,
        "operator": {"name": operator_name, "public_key": pub.hex()},
        "network": network, "window": window,
        "payout_addresses": [a for a, _ in addresses_with_priv],
        "control_proofs": proofs,
    }
    digest = sha256_hex(canonical(claim))
    claim["claim_sha256"] = digest
    claim["signature"] = core.ed25519_sign(operator_seed, bytes.fromhex(digest)).hex()
    return claim

def verify_claim(claim):
    """Returns (ok, problems). Checks the operator signature, one control
    proof per claimed address, and that each proof verifies against the
    address it claims (secp256k1 recovery -> address equality)."""
    problems = []
    body = {k: v for k, v in claim.items() if k not in ("claim_sha256", "signature")}
    digest = sha256_hex(canonical(body))
    if digest != claim.get("claim_sha256"):
        problems.append("claim hash mismatch")
    else:
        pub = bytes.fromhex(claim["operator"]["public_key"])
        if not core.ed25519_verify(pub, bytes.fromhex(digest), bytes.fromhex(claim["signature"])):
            problems.append("operator signature invalid")
    proofs = {p["address"]: p for p in claim.get("control_proofs", [])}
    for addr in claim.get("payout_addresses", []):
        p = proofs.get(addr)
        if p is None:
            problems.append(f"{addr}: missing control proof"); continue
        want_msg = control_message(claim["operator"]["name"], addr, claim["network"])
        if p["message"] != want_msg:
            problems.append(f"{addr}: control message does not match the claim-bound template"); continue
        sig = base64.b64decode(p["signature_b64"])
        if not core.zcash_verify_message(addr, sig, p["message"], claim["network"]):
            problems.append(f"{addr}: control proof signature invalid")
    return (not problems), problems
