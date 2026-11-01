#!/usr/bin/env python3
"""Build one CSV per solved Bitcoin puzzle (the 2015 "1000 BTC" puzzle transaction).

Input : sources/puzzles.json  (compiled from public GitHub datasets, see README.md)
Output: puzzle_NNN.csv for every solved puzzle, plus index.csv

Nothing is trusted blindly. Before a CSV is written, every solved puzzle is
re-verified here with pure-Python secp256k1 arithmetic:

  1. the private key lies in the puzzle's range [2^(n-1), 2^n - 1]
  2. private_key * G (compressed) == the public key seen on chain
  3. Base58Check(0x00 || HASH160(pubkey)) == the puzzle address
  4. the WIF decodes to the same private key (compressed flag set)

If any check fails the script exits non-zero and writes nothing.

Every value column is followed by an "<column>_evidence" column holding a link
that lets a reader confirm the value independently (block explorer, the
original announcement, or this script).
"""

import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_JSON = os.path.join(HERE, "sources", "puzzles.json")

# Where to point readers. mempool.space is used for on-chain evidence; swap the
# prefix if you prefer another explorer (blockstream.info uses the same paths).
TX_URL = "https://mempool.space/tx/{}"
ADDR_URL = "https://mempool.space/address/{}"
SCRIPT_URL = "https://github.com/k290/RCKangaroo/blob/claude/tender-gauss-5jro04/solved_puzzles/generate_csvs.py"
AGNTN_URL = "https://github.com/agntn/puzzles/blob/main/src/collections/bits/{}.ts"
# Public profile where a named solver lists the puzzles they solved.
SOLVER_PROFILE = {"RetiredCoder": "https://github.com/RetiredC"}
# Transaction of 2015-01-15 that created all 256 puzzle outputs (#1..#256).
FUNDING_TXID = "08389f34c98c606322740c0be6a7125d9860bb8d5cb182c02f98461e5fa6cd15"

# --------------------------------------------------------------------------- #
# secp256k1 / Bitcoin encoding (pure Python, no dependencies)
# --------------------------------------------------------------------------- #
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _jac_double(p):
    x, y, z = p
    if y == 0:
        return (0, 0, 0)
    s = (4 * x * y * y) % P
    m = (3 * x * x) % P
    nx = (m * m - 2 * s) % P
    ny = (m * (s - nx) - 8 * y ** 4) % P
    return (nx, ny, (2 * y * z) % P)


def _jac_add(p, q):
    if p[2] == 0:
        return q
    if q[2] == 0:
        return p
    z1s, z2s = p[2] * p[2] % P, q[2] * q[2] % P
    u1, u2 = p[0] * z2s % P, q[0] * z1s % P
    s1, s2 = p[1] * z2s * q[2] % P, q[1] * z1s * p[2] % P
    if u1 == u2:
        return _jac_double(p) if s1 == s2 else (0, 0, 0)
    h, r = (u2 - u1) % P, (s2 - s1) % P
    h2 = h * h % P
    h3 = h * h2 % P
    nx = (r * r - h3 - 2 * u1 * h2) % P
    ny = (r * (u1 * h2 - nx) - s1 * h3) % P
    return (nx, ny, h * p[2] * q[2] % P)


def point_mul(k):
    acc, add = (0, 0, 0), (G[0], G[1], 1)
    while k:
        if k & 1:
            acc = _jac_add(acc, add)
        add = _jac_double(add)
        k >>= 1
    zi = pow(acc[2], -1, P)
    return (acc[0] * zi * zi % P, acc[1] * zi * zi * zi % P)


def compressed_pubkey(k):
    x, y = point_mul(k)
    return ("03" if y & 1 else "02") + format(x, "064x")


def _ripemd160(data):
    try:
        return hashlib.new("ripemd160", data).digest()
    except ValueError:  # OpenSSL 3 builds without legacy provider
        return _ripemd160_py(data)


def _ripemd160_py(msg):
    # Compact reference RIPEMD-160 for systems whose hashlib lacks it.
    def rol(x, n):
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF
    f = [lambda x, y, z: x ^ y ^ z, lambda x, y, z: (x & y) | (~x & z),
         lambda x, y, z: (x | ~y) ^ z, lambda x, y, z: (x & z) | (y & ~z),
         lambda x, y, z: x ^ (y | ~z)]
    kl = [0, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
    kr = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0]
    rl = [list(range(16)), [7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8],
          [3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12],
          [1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2],
          [4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13]]
    rr = [[5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12],
          [6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2],
          [15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13],
          [8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14],
          [12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11]]
    sl = [[11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8],
          [7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12],
          [11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5],
          [11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12],
          [9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6]]
    sr = [[8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6],
          [9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11],
          [9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5],
          [15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8],
          [8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11]]
    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    ml = len(msg) * 8
    msg += b"\x80" + b"\x00" * ((55 - len(msg)) % 64) + ml.to_bytes(8, "little")
    for off in range(0, len(msg), 64):
        x = [int.from_bytes(msg[off + 4 * i:off + 4 * i + 4], "little") for i in range(16)]
        al, bl, cl, dl, el = h
        ar, br, cr, dr, er = h
        for j in range(5):
            for i in range(16):
                t = rol((al + (f[j](bl, cl, dl) & 0xFFFFFFFF) + x[rl[j][i]] + kl[j]) & 0xFFFFFFFF, sl[j][i])
                al, bl, cl, dl, el = el, (t + el) & 0xFFFFFFFF, bl, rol(cl, 10), dl
                t = rol((ar + (f[4 - j](br, cr, dr) & 0xFFFFFFFF) + x[rr[j][i]] + kr[j]) & 0xFFFFFFFF, sr[j][i])
                ar, br, cr, dr, er = er, (t + er) & 0xFFFFFFFF, br, rol(cr, 10), dr
        t = (h[1] + cl + dr) & 0xFFFFFFFF
        h = [t, (h[2] + dl + er) & 0xFFFFFFFF, (h[3] + el + ar) & 0xFFFFFFFF,
             (h[4] + al + br) & 0xFFFFFFFF, (h[0] + bl + cr) & 0xFFFFFFFF]
    return b"".join(v.to_bytes(4, "little") for v in h)


B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58check_encode(payload):
    raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out


def b58check_decode(s):
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(s) - len(s.lstrip("1"))) + raw
    payload, chk = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != chk:
        raise ValueError("bad Base58Check checksum")
    return payload


def p2pkh_address(pubkey_hex):
    h160 = _ripemd160(hashlib.sha256(bytes.fromhex(pubkey_hex)).digest())
    return b58check_encode(b"\x00" + h160), h160.hex()


# --------------------------------------------------------------------------- #
# Verification and CSV output
# --------------------------------------------------------------------------- #
def verify(r):
    n, k = r["puzzle"], int(r["private_key_hex"], 16)
    lo, hi = (1 << (n - 1)), (1 << n) - 1
    if not lo <= k <= hi:
        raise AssertionError(f"#{n}: key {k:x} outside [2^{n-1}, 2^{n}-1]")
    pub = compressed_pubkey(k)
    if pub != r["public_key"]:
        raise AssertionError(f"#{n}: k*G = {pub} but on-chain pubkey is {r['public_key']}")
    addr, h160 = p2pkh_address(pub)
    if addr != r["address"]:
        raise AssertionError(f"#{n}: pubkey hashes to {addr}, puzzle address is {r['address']}")
    wif = b58check_decode(r["private_key_wif"])
    if wif[0] != 0x80 or wif[33:] != b"\x01" or int.from_bytes(wif[1:33], "big") != k:
        raise AssertionError(f"#{n}: WIF does not encode the private key (compressed)")
    return h160


def first(txs, kind):
    hits = sorted((t for t in txs if t["type"] == kind), key=lambda t: t["date"])
    return hits[0] if hits else None


def build_row(r, h160):
    n = r["puzzle"]
    claim = first(r["transactions"], "claim")
    reveal = first(r["transactions"], "pubkeyReveal")
    if reveal and reveal["date"] < claim["date"]:
        pk_tx, pk_how = reveal, "revealed on chain before the solve"
    else:
        pk_tx, pk_how = claim, "revealed on chain by the solver's sweep (first spend)"
    announce = next((f["url"] for f in r["facts"] if f["text"].startswith("Announced")), None)
    solver_link = announce or SOLVER_PROFILE.get(r["solver"]) or ADDR_URL.format(r["address"])
    funding_btc = sum(float(t["amount_btc"]) for t in r["transactions"] if t["type"] in ("funding", "increase"))
    tx = TX_URL.format
    row = [
        ("puzzle", n, tx(FUNDING_TXID)),
        ("address", r["address"], ADDR_URL.format(r["address"])),
        ("hash160", h160, SCRIPT_URL),
        ("key_range", f"2^{n-1} .. 2^{n}-1", SCRIPT_URL),
        ("public_key", r["public_key"], tx(pk_tx["txid"])),
        ("public_key_onchain", f"{pk_how} ({pk_tx['date']} UTC)", tx(pk_tx["txid"])),
        ("private_key_hex", r["private_key_hex"], tx(claim["txid"])),
        ("private_key_wif", r["private_key_wif"], SCRIPT_URL),
        ("private_key_verified", "yes: in range, k*G == public_key, HASH160 -> address, WIF round-trips", SCRIPT_URL),
        ("solved_at_utc", claim["date"], tx(claim["txid"])),
        ("claim_txid", claim["txid"], tx(claim["txid"])),
        ("prize_btc", r["prize_btc"], ADDR_URL.format(r["address"])),
        ("funded_btc_total", f"{funding_btc:.8f}".rstrip("0").rstrip("."), ADDR_URL.format(r["address"])),
        ("solver", r["solver"] or "unknown", solver_link),
        ("data_source", "agntn/puzzles bits/%d.ts (cross-checked, see README)" % n, AGNTN_URL.format(n)),
    ]
    header = []
    values = []
    for name, value, link in row:
        header += [name, name + "_evidence"]
        values += [value, link]
    return header, values


def main():
    rows = [r for r in json.load(open(SOURCE_JSON)) if r["solved"]]
    built = []
    for r in rows:
        h160 = verify(r)  # raises on any mismatch -> nothing gets written
        built.append((r, build_row(r, h160)))
    for r, (header, values) in built:
        with open(os.path.join(HERE, "puzzle_%03d.csv" % r["puzzle"]), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerow(values)
    with open(os.path.join(HERE, "index.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(built[0][1][0])
        for _, (_, values) in built:
            w.writerow(values)
    print(f"verified and wrote {len(built)} puzzle CSVs + index.csv")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        sys.exit("VERIFICATION FAILED: %s" % e)
