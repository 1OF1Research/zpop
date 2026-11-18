# NU7 windows: the activation day and the first eleven full days at 25 seconds

Receipts issued 2026-11-17 under a measurement key (not the filed example
key), after the NU7 subsidy schedule was derived from live coinbases and
added to `zpop/subsidy.py`:

- NU7 activation height: **3,543,405** (height 3,543,404 still pays the old
  stream amount; the first post-activation coinbase fixes the boundary).
- Block subsidy 52,083,333 zats, split per block: miner 41,666,668,
  Zcash Community Grants stream 4,166,666, lockbox 6,249,999.

| Day (UTC) | Heights | Blocks | Receipt sha256 |
|---|---|---|---|
| 2026-11-06 (activation) | 3543289..3546327 | 3039 | b065dc7e39d0fffc21933756818745cd52495c76337fa6ec7cf09967ff0b833b |
| 2026-11-07 | 3546328..3549770 | 3443 | b1a43b056a7254f8a1fa4febc5d0e5bfc724920f1886499448e97fe77c336956 |
| 2026-11-08 | 3549771..3553223 | 3453 | 496ca3317ac0dc333553c131e0102ba729805a1e7ed31f7ad43467e4502dafa3 |
| 2026-11-09 | 3553224..3556671 | 3448 | 9f86493df1fac9bb9c3fad86b28587104c283a24a6de3633ad8a70583af3a3b5 |
| 2026-11-10 | 3556672..3560140 | 3469 | e94d6b05ad8403853e489129451a2199379f381aa1727ab06a5d26e1b4d5cb17 |
| 2026-11-11 | 3560141..3563587 | 3447 | 20f966e1383ad1383ee940948a394837fcbfb62ce0dce68021e812515bbf24f2 |
| 2026-11-12 | 3563588..3567018 | 3431 | d3c0c3a9e96503b416ccac619108f76300d64c356b364f4d4e0eb8f6f9943248 |
| 2026-11-13 | 3567019..3570496 | 3478 | c2ab01f311ed612194b0f32f4f2a3e72afe1d6aad8cda47654b32d915df24c54 |
| 2026-11-14 | 3570497..3573971 | 3475 | 749a0ee8679e4bf24c9e397b0341bea3dd2a3439839d6d05627de178cc27e9bb |
| 2026-11-15 | 3573972..3577423 | 3452 | 2ff14965d5ddee14116025f1904746b06c8dd14627d984001e7d7ebee0e7c4c3 |
| 2026-11-16 | 3577424..3580868 | 3445 | 8f335cec3a9d8008c885229a196203b350ee526c188c0e6ca400d567f022a582 |
| 2026-11-17 | 3580869..3584337 | 3469 | eea9500ad85c6979216cc4cd7e8029e8f84cd972ec3786c079aa10a54b1343ef |

The twelve receipts form one chain, from the activation day's receipt
(prev: none) through 2026-11-17. Verify all of them against the live
network:

```
python zpop.py verify window-2026-11-06.json window-2026-11-07.json \
  window-2026-11-08.json window-2026-11-09.json window-2026-11-10.json \
  window-2026-11-11.json window-2026-11-12.json window-2026-11-13.json \
  window-2026-11-14.json window-2026-11-15.json window-2026-11-16.json \
  window-2026-11-17.json --online
```

Verified end to end on 2026-11-17: signatures, chain links, and every
window's facts re-derived from a public lightwalletd server.

Headline measurements from these windows (producer = the largest
non-stream coinbase output; an address is not a pool or a place):

- Average block interval over November 7-17: 25.00 seconds (38,010 blocks).
- A producer's block follows its own block 14.87% of the time, against
  14.81% predicted from the producers' shares alone (same-day shares,
  weighted). Every day sits within 0.7 points of its prediction.
- Ironwood actions average 7.3 per block; 151 blocks sit exactly at the
  current 330 cap, and 624 blocks (1.64%) carry more than the proposed
  264.
- 1,924 blocks (5.06%) pay a shielded coinbase and cannot be attributed
  to a producer from chain data.

Datasets for these windows are reproducible by re-running
`zpop.py window --day <day>`; they are not committed here to keep the
repository small.
