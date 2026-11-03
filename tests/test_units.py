"""Offline unit tests for zpop primitives. Run: python3 tests/test_units.py
Every test names its sensitivity: the input/condition that would break it."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "zpop"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from zpop import core
from zpop.subsidy import subsidy_zats, funding_streams

fails = []
def check(name, cond, sensitivity):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [sensitivity: {sensitivity}]"))
    if not cond: fails.append(name)

# RIPEMD-160 published vectors (sensitivity: padding/length encoding for msgs >= 56 bytes)
check("ripemd160 empty", core.ripemd160(b"").hex() == "9c1185a5c5e9fc54612808977ee8f548b2258d31", "empty-input padding")
check("ripemd160 abc", core.ripemd160(b"abc").hex() == "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc", "single block")
check("ripemd160 alphabet", core.ripemd160(b"abcdefghijklmnopqrstuvwxyz").hex() == "f71c27109c692c1b56bbdceb5b9d2865b3708dbc", "26-byte input")
check("ripemd160 80 bytes", core.ripemd160(b"1234567890" * 8).hex() == "9b752e45573d4b39f4dbd3323cab82bf63326bfb", "multi-block padding boundary")

# base58check published vector (Bitcoin wiki; sensitivity: checksum bytes)
payload = bytes.fromhex("00010966776006953D5567439E5E39F86A0D273BEE")
check("b58check vector", core.b58check_encode(payload) == "16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM", "checksum or alphabet")
check("b58check roundtrip", core.b58check_decode("16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM") == payload, "leading-zero handling")

# Ed25519 RFC 8032 test vector 1 (sensitivity: clamp / cofactor handling)
seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
pub, _, _ = core.ed25519_keypair(seed)
check("ed25519 pubkey vector", pub.hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "base point or clamp")
sig = core.ed25519_sign(seed, b"")
check("ed25519 sig vector", sig.hex() == "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b", "nonce hash")
check("ed25519 verify", core.ed25519_verify(pub, b"", sig), "verify equation")
check("ed25519 verify rejects tamper", not core.ed25519_verify(pub, b"x", sig), "message binding")

# secp256k1: privkey 1 -> known hash160 (sensitivity: hash160 = ripemd160(sha256))
pub1 = core.secp_pubkey(1)
check("secp privkey1 hash160", core.hash160(pub1).hex() == "751e76e8199196d454941c45d1b3a323f1433bd6", "generator or hash160")
addr1 = core.pubkey_to_address(pub1)
check("zcash t1 shape", addr1.startswith("t1") and core.address_to_hash160(addr1)[2].hex() == "751e76e8199196d454941c45d1b3a323f1433bd6", "prefix bytes 1cb8")

# script -> address on the observed mainnet ZCG stream script (sensitivity: prefix map)
kind, addr = core.script_to_address(bytes.fromhex("a914c20cd5bdf7964ca61764db66bc2531b1792a084d87"))
check("zcg script p2sh", kind == "p2sh" and addr.startswith("t3"), "script template match")
check("zcg addr roundtrip", core.address_to_hash160(addr)[2].hex() == "c20cd5bdf7964ca61764db66bc2531b1792a084d", "hash160 extraction")

# Zcash message signatures: round trip + negatives (sensitivity: magic prefix bytes)
priv = 0xC0FFEE2540222967C54596E5CB9E26B5CF98EEC35C729D0B18B4A16BCD5B1A2B % core._N
addr = core.pubkey_to_address(core.secp_pubkey(priv))
msg = "ZPOP control proof test"
s = core.zcash_sign_message(priv, msg)
check("msgsign roundtrip", core.zcash_verify_message(addr, s, msg), "prefix or recovery")
check("msgsign rejects wrong msg", not core.zcash_verify_message(addr, s, msg + "!"), "hash binding")
check("msgsign rejects wrong addr", not core.zcash_verify_message(addr1, s, msg), "address binding")

# subsidy schedule (sensitivity: halving-height table)
check("subsidy era3", subsidy_zats(3540899) == 156250000, "halving table")
check("subsidy halving2 boundary", subsidy_zats(2726400) == 156250000 and subsidy_zats(2726399) == 312500000, "boundary off-by-one")
check("subsidy halving1 boundary", subsidy_zats(1046400) == 312500000 and subsidy_zats(1046399) == 625000000, "boundary off-by-one")
check("subsidy halving0 boundary", subsidy_zats(840000) == 625000000 and subsidy_zats(839999) == 1250000000, "boundary off-by-one")
m, z, l = funding_streams(3540899)
check("streams 80/8/12", (m, z, l) == (125000000, 12500000, 18750000), "ZIP 1016 percentages")

print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
