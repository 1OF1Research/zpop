"""Core primitives for zpop: base58check, script->address, Ed25519,
RIPEMD-160, secp256k1 and Zcash message signatures. Pure Python, stdlib only.
Every primitive is covered by published test vectors in tests/test_units.py."""
import hashlib, struct

# ---------------- base58 / base58check ----------------
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
B58I = {c: i for i, c in enumerate(B58)}

def b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + (out or "")

def b58decode(s: str) -> bytes:
    n = 0
    for c in s:
        n = n * 58 + B58I[c]
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + raw

def b58check_encode(payload: bytes) -> str:
    ck = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return b58encode(payload + ck)

def b58check_decode(s: str) -> bytes:
    raw = b58decode(s)
    payload, ck = raw[:-4], raw[-4:]
    want = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if ck != want:
        raise ValueError("bad base58 checksum")
    return payload

# Zcash address prefixes (two-byte) per network / kind
ADDR_PREFIX = {
    ("mainnet", "p2pkh"): bytes([0x1C, 0xB8]),
    ("mainnet", "p2sh"): bytes([0x1C, 0xBD]),
    ("testnet", "p2pkh"): bytes([0x1D, 0x25]),
    ("testnet", "p2sh"): bytes([0x1C, 0xBA]),
}

def script_to_address(script: bytes, network="mainnet"):
    """Return (kind, address) for standard transparent scripts, else (None, None)."""
    if len(script) == 25 and script[:3] == b"\x76\xa9\x14" and script[23:] == b"\x88\xac":
        return "p2pkh", b58check_encode(ADDR_PREFIX[(network, "p2pkh")] + script[3:23])
    if len(script) == 23 and script[:2] == b"\xa9\x14" and script[22:] == b"\x87":
        return "p2sh", b58check_encode(ADDR_PREFIX[(network, "p2sh")] + script[2:22])
    return None, None

def address_to_hash160(addr: str):
    payload = b58check_decode(addr)
    for (net, kind), pfx in ADDR_PREFIX.items():
        if payload[:2] == pfx:
            return net, kind, payload[2:]
    raise ValueError("unrecognised address prefix")

# ---------------- RIPEMD-160 ----------------
# Verified pure-Python implementation: zpop/ripemd160.py (Pieter Wuille,
# Bitcoin Core test framework, MIT). Validated against the published
# RIPEMD-160 test vectors including the 1,000,000-byte vector.
try:
    from .ripemd160 import ripemd160
except ImportError:  # direct module import (tests put zpop/ on sys.path)
    from ripemd160 import ripemd160

def hash160(b: bytes) -> bytes:
    return ripemd160(hashlib.sha256(b).digest())

# ---------------- Ed25519 (RFC 8032) ----------------
_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)

def _xrecover(y):
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q) % _Q
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0: x = (x * _I) % _Q
    if x % 2 != 0: x = _Q - x
    return x

_BY = (4 * pow(5, _Q - 2, _Q)) % _Q
_B = (_xrecover(_BY), _BY)

def _ed_add(P, Q):
    x1, y1 = P; x2, y2 = Q
    t = _D * x1 * x2 * y1 * y2 % _Q
    x3 = (x1 * y2 + x2 * y1) * pow(1 + t, _Q - 2, _Q) % _Q
    y3 = (y1 * y2 + x1 * x2) * pow(1 - t, _Q - 2, _Q) % _Q
    return x3, y3

def _ed_mul(P, e):
    Q = (0, 1)
    while e > 0:
        if e & 1: Q = _ed_add(Q, P)
        P = _ed_add(P, P)
        e >>= 1
    return Q

def _ed_encode(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32))

def _ed_decode(s):
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    sign = (s[31] >> 7) & 1
    x = _xrecover(y)
    if (x & 1) != sign: x = _Q - x
    return x, y

def ed25519_keypair(seed32: bytes):
    h = hashlib.sha512(seed32).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8; a |= (1 << 254)
    return _ed_encode(_ed_mul(_B, a)), h, a

def ed25519_sign(seed32: bytes, msg: bytes) -> bytes:
    pub, h, a = ed25519_keypair(seed32)
    r = int.from_bytes(hashlib.sha512(h[32:] + msg).digest(), "little") % _L
    R = _ed_encode(_ed_mul(_B, r))
    k = int.from_bytes(hashlib.sha512(R + pub + msg).digest(), "little") % _L
    S = (r + k * a) % _L
    return R + S.to_bytes(32, "little")

def ed25519_verify(pub: bytes, msg: bytes, sig: bytes) -> bool:
    if len(pub) != 32 or len(sig) != 64: return False
    R = _ed_decode(sig[:32]); A = _ed_decode(pub)
    S = int.from_bytes(sig[32:], "little")
    if S >= _L: return False
    k = int.from_bytes(hashlib.sha512(sig[:32] + pub + msg).digest(), "little") % _L
    return _ed_mul(_B, S) == _ed_add(R, _ed_mul(A, k))

# ---------------- secp256k1 + Zcash message signatures ----------------
_P = 2**256 - 2**32 - 977
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
      0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def _ec_add(P, Q):
    if P is None: return Q
    if Q is None: return P
    x1, y1 = P; x2, y2 = Q
    if x1 == x2 and (y1 + y2) % _P == 0: return None
    if P == Q:
        m = (3 * x1 * x1) * pow(2 * y1, _P - 2, _P) % _P
    else:
        m = (y2 - y1) * pow(x2 - x1, _P - 2, _P) % _P
    x3 = (m * m - x1 - x2) % _P
    return x3, (m * (x1 - x3) - y1) % _P

def _ec_mul(P, e):
    Q = None
    while e > 0:
        if e & 1: Q = _ec_add(Q, P)
        P = _ec_add(P, P)
        e >>= 1
    return Q

def secp_pubkey(priv: int, compressed=True) -> bytes:
    x, y = _ec_mul(_G, priv)
    if compressed:
        return bytes([0x02 | (y & 1)]) + x.to_bytes(32, "big")
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")

def pubkey_to_address(pub: bytes, network="mainnet") -> str:
    return b58check_encode(ADDR_PREFIX[(network, "p2pkh")] + hash160(pub))

_MSG_PREFIX = b"Zcash Signed Message:\n"

def _varint(n):
    if n < 0xFD: return bytes([n])
    if n <= 0xFFFF: return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF: return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)

def zcash_message_hash(msg: str) -> bytes:
    m = msg.encode("utf-8")
    data = _varint(len(_MSG_PREFIX)) + _MSG_PREFIX + _varint(len(m)) + m
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def zcash_sign_message(priv: int, msg: str) -> bytes:
    """65-byte compact signature (not base64). Deterministic RFC 6979."""
    import hmac as _hmac
    z = zcash_message_hash(msg)
    zint = int.from_bytes(z, "big")
    bx = priv.to_bytes(32, "big") + z
    v = b"\x01" * 32; k = b"\x00" * 32
    k = _hmac.new(k, v + b"\x00" + bx, hashlib.sha256).digest()
    v = _hmac.new(k, v, hashlib.sha256).digest()
    k = _hmac.new(k, v + b"\x01" + bx, hashlib.sha256).digest()
    v = _hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = _hmac.new(k, v, hashlib.sha256).digest()
        cand = int.from_bytes(v, "big")
        if 1 <= cand < _N: break
        k = _hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = _hmac.new(k, v, hashlib.sha256).digest()
    R = _ec_mul(_G, cand)
    r = R[0] % _N
    s = (pow(cand, _N - 2, _N) * (zint + r * priv)) % _N
    recid = (R[1] & 1) | (2 if R[0] >= _N else 0)
    if s > _N // 2:
        s = _N - s; recid ^= 1
    header = 27 + recid + 4  # compressed pubkey
    return bytes([header]) + r.to_bytes(32, "big") + s.to_bytes(32, "big")

def zcash_verify_message(address: str, sig65: bytes, msg: str, network="mainnet") -> bool:
    if len(sig65) != 65: return False
    header = sig65[0]
    if header < 27 or header > 34: return False
    recid = (header - 27) & 3
    compressed = bool((header - 27) & 4)
    r = int.from_bytes(sig65[1:33], "big"); s = int.from_bytes(sig65[33:65], "big")
    if not (1 <= r < _N and 1 <= s < _N): return False
    z = int.from_bytes(zcash_message_hash(msg), "big")
    x = r + (recid // 2) * _N
    if x >= _P: return False
    alpha = (pow(x, 3, _P) + 7) % _P
    beta = pow(alpha, (_P + 1) // 4, _P)
    y = beta if (beta & 1) == (recid & 1) else _P - beta
    R = (x, y)
    if _ec_mul(R, _N) is not None: return False
    Q = _ec_mul(R, s)
    Zg = _ec_mul(_G, (-z) % _N)
    Q = _ec_add(Q, Zg)
    Q = _ec_mul(Q, pow(r, _N - 2, _N))
    if Q is None: return False
    xq, yq = Q
    if compressed:
        pub = bytes([0x02 | (yq & 1)]) + xq.to_bytes(32, "big")
    else:
        pub = b"\x04" + xq.to_bytes(32, "big") + yq.to_bytes(32, "big")
    return pubkey_to_address(pub, network) == address
