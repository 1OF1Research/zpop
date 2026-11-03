"""Negative-path tests for zpop receipts and claims. Each case names its
sensitivity: the tampering it must catch. Run: python3 tests/test_receipts.py"""
import sys, os, json, copy, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "zpop"))
from zpop import core
from zpop.receipts import verify_signature
from zpop.claims import verify_claim, build_claim, control_message

EX = os.path.join(os.path.dirname(__file__), "..", "examples")
fails = []
def check(name, cond, sensitivity):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [sensitivity: {sensitivity}]"))
    if not cond: fails.append(name)

win = json.load(open(f"{EX}/window-2026-11-02/receipt.json"))
pay = json.load(open(f"{EX}/payment-f7d058/receipt.json"))
claim = json.load(open(f"{EX}/claim-demo/claim.json"))

check("genuine receipts verify", verify_signature(win) and verify_signature(pay), "canonical form stability")
t = copy.deepcopy(win); t["facts"]["aggregates"]["total_subsidy_zats"] += 1
check("edited fact breaks signature", not verify_signature(t), "any single-field edit")
t = copy.deepcopy(pay); t["facts"]["value_balances_zats"]["orchard"] = 0
check("edited value balance breaks signature", not verify_signature(t), "fact substitution")
t = copy.deepcopy(pay); t["prev_receipt"] = "00" * 32
check("edited chain link breaks signature", not verify_signature(t), "chain splicing")

ok, probs = verify_claim(claim)
check("genuine claim verifies", ok, f"control proof path ({probs})")
bad = copy.deepcopy(claim)
bad["control_proofs"][0]["signature_b64"] = base64.b64encode(b"\x1f" + b"\x00" * 64).decode()
ok, _ = verify_claim(bad)
check("forged control proof rejected", not ok, "signature from a key that does not control the address")
bad = copy.deepcopy(claim)
bad["payout_addresses"].append("t1MKn34KBa8Xh4g8qU8psibBXvURafphVn7")
ok, _ = verify_claim(bad)
check("claiming a stranger's producing address rejected", not ok, "address appended without a control proof (this is the window's top producer)")
bad = copy.deepcopy(claim)
bad["window"]["end_height"] += 1
ok, _ = verify_claim(bad)
check("edited claim window rejected", not ok, "claim hash binding")

# a control proof over the top producer address signed by a key that does
# not control it must fail: the signature is well-formed, but secp256k1
# recovery yields the signer's address, not the claimed one. Both keys are
# synthetic constants generated here, so this test needs no keys/ material.
top_addr = win["facts"]["aggregates"]["top_miner_addresses"][0]["address"]
not_the_producer = 0x5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED5EED
forged = build_claim(claim["operator"]["name"], bytes(range(32)), claim["network"],
                     dict(claim["window"]), [(top_addr, not_the_producer)])
ok, probs = verify_claim(forged)
check("control proof over top producer signed by wrong key rejected",
      not ok and any("control proof" in p for p in probs),
      "secp256k1 recovery binds the proof to the controlling key only")
print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
