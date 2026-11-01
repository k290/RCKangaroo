# Solved puzzles: evidence CSVs

There is one CSV per solved puzzle of the 2015 Bitcoin puzzle transaction
(`puzzle_001.csv` … `puzzle_135.csv`, 83 files). `index.csv` has the same rows in a single file.

Each CSV has one header row and one data row. **Every value column is followed by
`<column>_evidence`**, which holds a link you can use to confirm that value yourself.

| column | what it is | evidence link points to |
|---|---|---|
| `puzzle` | puzzle number n | the 2015-01-15 funding tx that created all puzzle outputs |
| `address` | P2PKH puzzle address | explorer address page |
| `hash160` | RIPEMD160(SHA256(pubkey)), derived here | `generate_csvs.py` |
| `key_range` | 2^(n-1) .. 2^n-1 | `generate_csvs.py` (range is checked there) |
| `public_key` | compressed pubkey as it appears on chain | the tx where it **first** appeared on chain |
| `public_key_onchain` | whether the pubkey was revealed *before* the solve (creator's 2019 dust txs for #65, #70 … #160) or by the solver's sweep | same tx |
| `private_key_hex` | the private key that was found | the claim (sweep) tx, which was signed with this key |
| `private_key_wif` | the same key in compressed WIF | `generate_csvs.py` |
| `private_key_verified` | result of the local cryptographic check | `generate_csvs.py` |
| `solved_at_utc` / `claim_txid` | first sweep of the prize | claim tx |
| `prize_btc` / `funded_btc_total` | nominal prize / sum of all funding txs | address page |
| `solver` | named solver, if one is publicly known | their announcement or profile, otherwise the address page |
| `data_source` | where the tx metadata came from | the source file on GitHub |

## How the data was built and verified

`python3 generate_csvs.py` re-checks every solved puzzle **before** it writes anything:

1. the key is in `[2^(n-1), 2^n-1]`
2. `k·G` (secp256k1, compressed) equals the recorded on-chain public key
3. `Base58Check(0x00 ‖ HASH160(pubkey))` equals the puzzle address
4. the WIF decodes back to the same key with the compressed flag set

If any check fails, the script exits non-zero and writes no CSVs. It is pure Python and needs no dependencies.

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
- If the page lists solve dates or prizes, compare them with `solved_at_utc` / `prize_btc` in `index.csv`.

**B. For each puzzle, on mempool.space (or blockstream.info, same URL paths)**
1. Open `address_evidence`. The address should exist, and its balance should now be ~0. Its
   first incoming tx should be `08389f34…cd15` (or `5d45587c…4164` / `12f34b58…13b3` for the 2017/2023 top-ups).
2. Open `claim_txid_evidence`. One input should spend from the puzzle address, and the date
   should equal `solved_at_utc`. Expand that input. The **last push of the scriptSig** is the public
   key, and it should equal `public_key`.
3. Where `public_key_onchain` says *before the solve*, open `public_key_evidence`. It is the creator's
   2019 tx (`17e4e323…b3d3`, 2019-06-01, for #65, #70 … #160). Find the input from the puzzle address. Its scriptSig
   pubkey should equal `public_key`.
4. Optionally, import `private_key_wif` into a **watch-only/offline** tool (e.g. `bx` or Electrum
   offline). It should show the same address. Never send funds to these addresses: the keys are public.

**C. Spot-check targets** (these cover each case):
- #1: trivial key, swept the same day
- #66: no pubkey before the solve, so it was revealed by the sweep
- #75: pubkey revealed in 2019
- #120 / #125 / #130 / #135: RetiredCoder's kangaroo solves. #135 is announced at
  https://bitcointalk.org/index.php?topic=5517607.msg66986617#msg66986617

If something doesn't match, fix it in `sources/puzzles.json` and rerun `python3 generate_csvs.py`.
Verification stops the run if the edit breaks the key/pubkey/address relationship.
