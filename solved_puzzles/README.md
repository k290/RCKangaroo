# Solved puzzles: evidence CSV

`solved_puzzles.csv` has one row for each of the 83 solved puzzles of the 2015 Bitcoin puzzle
transaction (#1–#70 and #75, #80 … #135). **Every value column is followed by
`<column>_evidence`**, which holds a link you can use to confirm that value yourself.

| column | what it is | evidence link points to |
|---|---|---|
| `puzzle` | puzzle number n | the 2015-01-15 tx that created all puzzle outputs |
| `address` | P2PKH puzzle address | explorer address page |
| `hash160` | RIPEMD160(SHA256(pubkey)), derived here | `generate_csvs.py` |
| `key_range` | 2^(n-1) .. 2^n-1 | `generate_csvs.py` (range is checked there) |
| `public_key` / `public_key_first_seen_utc` | compressed pubkey, and when it **first** appeared on chain | that tx |
| `public_key_revealed_before_solve` / `_utc` | the pubkey if it was on chain before the solve, else empty: the creator's 2019-06-01 tx for #65, #70 … #135, an unrelated 2014 spend for #2, a 2013 spend for #1 | that tx (address page if empty) |
| `public_key_revealed_after_solve` / `_utc` | the pubkey as revealed by the solver's sweep (filled for every puzzle) | the sweep tx |
| `public_key_later_spend_txids` | any later spends from the address that reveal the pubkey again (e.g. #135's dust sweep) | the first such tx (address page if none) |
| `private_key_hex` | the private key that was found | the sweep tx, which was signed with this key |
| `private_key_wif` | the same key in compressed WIF | `generate_csvs.py` |
| `private_key_verified` | result of the local cryptographic check | `generate_csvs.py` |
| `solved_at_utc` / `claim_txid` | first spend after the 2015 puzzle tx | sweep tx |
| `prize_btc` / `funded_btc_total` | nominal prize / sum of puzzle funding txs (2015 onward) | address page |
| `solver` | who found the key: a name if one is public, otherwise the address the prize went to | the attribution source (see below) |
| `solver_notes` | context: other credited parties, front-running, solver totals | its source |
| `method` | how the key was found | the source for the method, or the on-chain fact it is inferred from |
| `method_basis` | **stated** (the solver or tool author says so), **reported** (third party), or **inferred** (follows from what was on chain) | same as `method` |
| `data_source` | where the tx metadata came from | the source file on GitHub |

A P2PKH spend must put a pubkey whose HASH160 equals the address into its scriptSig. So
`public_key_revealed_after_solve` is fixed by the math: it can only be the verified key below.
Only the txid and date of the sweep come from the source data.

## Solver attribution and method

These come from `sources/attribution.json`, which is hand-curated. Every claim cites one source.

| puzzles | solver | method | basis |
|---|---|---|---|
| #1–#39, #47–#50 | unnamed; the prize address prefix is given | brute force (tiny ranges, swept 2015) | inferred |
| #40–#46 | unknown (no source lists one) | brute force | inferred |
| #51–#54 | Large Bitcoin Collider pool | distributed brute force | reported (LBC trophies page) |
| #55–#58, #62, #64 | unnamed | brute force | inferred (#64 also in Matthew Green's records) |
| #59, #60, #61, #63 | zielar | BitCrack on GPUs, ~248 Gkeys/s, up to ~100 Tesla GPUs | reported (albert0bsd, bitcointalk 2021) |
| #65, #95, #100 | unnamed | ECDLP on the 2019-exposed pubkey (kangaroo/BSGS) | inferred |
| #66, #69 | unnamed finder addresses; both claims were front-run by bots | brute force | inferred |
| #67, #68 | Kowala | brute force; claims mined privately | inferred |
| #70–#90 | pikachunakapika | ECDLP on the 2019-exposed pubkey | inferred |
| #105 | 57fe | ECDLP, probably kangaroo (57fe publishes a GPU kangaroo) | inferred |
| #110, #115 | zielar with Jean-Luc Pons | JeanLucPons/Kangaroo on 256 Tesla V100 (2.1 d / 13 d) | stated (Kangaroo README) |
| #120, #125, #130 | RetiredCoder | Pollard kangaroo, own GPU code | reported |
| #135 | RetiredCoder | RCKangaroo with ASM kernels, ~200 GPUs for ~5 months | stated (bitcointalk) |

"Brute force, inferred" rests on cryptography, not on anyone's word. If no public key was on chain
before the solve, ECDLP methods (kangaroo, BSGS) had nothing to work on. The only option was to
hash candidate keys and compare each with the address.

**Attribution sources:**
- **Named solvers:** privatekeys.pw. I read it from a GitHub mirror of the page
  ([Cryptographytube/privatekeys.pw-source-code](https://github.com/Cryptographytube/privatekeys.pw-source-code)), which already includes #135. Its Top Solvers table
  matches the per-puzzle list when prizes are taken at the time of each solve. For example, RetiredCoder's 40.2 BTC = #120 1.2 + 12.5 + 13 + 13.5.
- **Per-puzzle solver list:** [Bradbuythedip/puzzle_data](https://github.com/Bradbuythedip/puzzle_data), a Feb-2025 export in privatekeys.pw's format. It
  doesn't include #40–#46, #67–#69 or #135.
- **Methods and hardware:** JeanLucPons/Kangaroo README, RetiredCoder's announcement, and Matthew Green's
  [bits-of-work-repo](https://github.com/matthewdgreen/bits-of-work-repo) ECDLP records.

The LBC trophies page and the albert0bsd thread were found by web search, but I couldn't open them
from the sandbox. Check those two links yourself.

## How the data was built and verified

`python3 generate_csvs.py` re-checks every solved puzzle **before** it writes anything:

1. the key is in `[2^(n-1), 2^n-1]`
2. `k·G` (secp256k1, compressed) equals the recorded on-chain public key
3. `Base58Check(0x00 ‖ HASH160(pubkey))` equals the puzzle address
4. the WIF decodes back to the same key with the compressed flag set

If any check fails, the script exits non-zero and writes nothing. It is pure Python and needs no dependencies.

Checks 2 and 3 make the private keys self-proving. A wrong key cannot produce the
puzzle address. For #65, #70, #75 … #135 the key also matches a public key that was published on chain years
before the solve.

`sources/puzzles.json` was compiled from public GitHub datasets. Four sources were compared:

| source | used for | agreement |
|---|---|---|
| [agntn/puzzles](https://github.com/agntn/puzzles/tree/main/src/collections/bits) `bits/N.ts` | addresses, pubkeys, keys, **all txids and dates** | primary |
| [HomelessPhD/BTC32](https://github.com/HomelessPhD/BTC32) `bits_address_privatekey.csv` | address + key | 83/83 match |
| [StableExo/TheWarden](https://github.com/StableExo/TheWarden) `bitcoin-puzzle-all-20251203.csv` | address + key + pubkey | 82/82 match (predates #135) |
| [hevnsnt/collider](https://github.com/hevnsnt/collider) `puzzle_config.hpp` (from privatekeys.pw) | address + key + pubkey | 82/82 match (predates #135) |

The per-source match flags are stored in `sources/puzzles.json` under `crosscheck`.

### Not yet checked against the chain

The build ran in a sandbox that could not reach block explorers or
bitboinc.athena.org.tr. So the **txids, dates and BTC amounts** come from agntn/puzzles
and have not been confirmed on chain. Addresses, pubkeys and keys don't depend on this,
because they are verified cryptographically. Use the checklist below to confirm the rest.

## Ground-truth checklist (manual)

**A. bitboinc stats page** (https://bitboinc.athena.org.tr/puzzle_stats.php)
- Check that its solved list matches these 83: #1–#70 and #75, #80, #85 … #135. Look in particular for
  anything solved after #135 (2026-07-28) and for whether #71 is still open.
- If the page lists solve dates or prizes, compare them with `solved_at_utc` / `prize_btc` in `solved_puzzles.csv`.

**B. For each puzzle, on mempool.space (or blockstream.info, same URL paths)**
1. Open `address_evidence`. The address should exist, and its balance should now be ~0. Its
   first puzzle deposit should be `08389f34…cd15` (#1 and #2 also show older, unrelated activity) (or `5d45587c…4164` / `12f34b58…13b3` for the 2017/2023 top-ups).
2. Open `claim_txid_evidence`. One input should spend from the puzzle address, and the date
   should equal `solved_at_utc`. Expand that input. The **last push of the scriptSig** is the public
   key, and it should equal `public_key_revealed_after_solve`.
3. Where `public_key_revealed_before_solve` is filled, open its evidence link. For #65, #70 … #135 it is
   the creator's 2019 tx (`17e4e323…b3d3`, 2019-06-01). Find the input from the puzzle address. Its scriptSig
   pubkey should equal `public_key`. Do the same for any `public_key_later_spend_txids`.
4. Optionally, import `private_key_wif` into a **watch-only/offline** tool (e.g. `bx` or Electrum
   offline). It should show the same address. Never send funds to these addresses: the keys are public.

**C. Spot-check targets** (these cover each case):
- #1: trivial key, swept the same day
- #66: no pubkey before the solve, so it was revealed by the sweep
- #75: pubkey revealed in 2019
- #120 / #125 / #130 / #135: RetiredCoder's kangaroo solves. #135 is announced at
  https://bitcointalk.org/index.php?topic=5517607.msg66986617#msg66986617

**D. Attribution**
- On privatekeys.pw, the Solved tab names a solver per puzzle. Compare it with `solver`, and fill in
  #40–#46 if the site names anyone.
- Open https://lbc.cryptoguru.org/trophies and check that it lists #51–#54.
- Open https://bitcointalk.org/index.php?topic=5365099.0 and check the BitCrack / 248 Gkeys/s figures for #59–#63.
- On bitboinc, check whether the stats page credits solvers or pools.

If something doesn't match, fix it in `sources/puzzles.json` and rerun `python3 generate_csvs.py`.
Verification stops the run if the edit breaks the key/pubkey/address relationship.
