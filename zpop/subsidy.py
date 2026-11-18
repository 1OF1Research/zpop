"""Zcash emission schedule (mainnet), derived from chain data.

Era boundaries and amounts were read off live coinbase transactions from
Parallax on 2026-11-03 (heights 900000, 1046399, 1046400, 2726399, 2726400,
3540899-3540901) rather than transcribed from memory:
  height < 840000        : 12.5 ZEC (after the 20,000-block Slow Start ramp)
  840000 .. 1046399      : 6.25 ZEC   (coinbase at 900000: 80/20 split of 6.25)
  1046400 .. 2726399     : 3.125 ZEC  (Canopy streams 7/5/8 visible at 1046400)
  2726400 .. 3543404     : 1.5625 ZEC (ZIP 1016 layout 80/8 + 12% deferred)
  3543405 .. 7766399     : 0.52083333 ZEC (NU7 / ZIP 218: block target spacing
                           75s -> 25s, per-block subsidy divided by 3 so daily
                           issuance is unchanged; same 80/8 + 12% layout.
                           Boundary and amounts read off live coinbases on
                           2026-11-17: height 3543404 pays the old stream
                           12,500,000 zats, height 3543405 pays stream
                           4,166,666 and miner base 41,666,668, so subsidy is
                           52,083,333 = 41,666,668 + 4,166,666 + 6,249,999.
                           Next halving at 2726400 + 5,040,000 = 7766400,
                           the 25-second-era halving interval.)
  height >= 7766400      : not encoded - subsidy_zats refuses rather than
                           guesses."""
INITIAL_SUBSIDY = 1250000000  # 12.5 ZEC in zatoshis
ERAS = [(840000, 625000000), (1046400, 312500000), (2726400, 156250000)]
NU7_ACTIVATION = 3543405       # first 25-second block (verified on chain)
NU7_SUBSIDY = 52083333         # 156250000 / 3, split 41666668/4166666/6249999
NEXT_HALVING = 7766400         # 2726400 + 5040000 (25s-era halving interval)

def subsidy_zats(height: int) -> int:
    if height < 0: raise ValueError("negative height")
    if height < 20000:
        return INITIAL_SUBSIDY * (height + 1) // 20000
    if height >= NEXT_HALVING:
        raise ValueError("height beyond encoded schedule (next halving not encoded)")
    if height >= NU7_ACTIVATION:
        return NU7_SUBSIDY
    s = INITIAL_SUBSIDY
    for start, val in ERAS:
        if height >= start: s = val
    return s

def funding_streams(height: int):
    """(miner_zats, zcg_stream_zats, lockbox_accrual_zats) per ZIP 1015/1016 as
    deployed from height 2726400: miner 80%, ZCG stream 8% paid as a coinbase
    output, coinholder lockbox 12% accrued to the deferred lockbox pool (NOT
    a coinbase output)."""
    if height < 2726400:
        raise ValueError("funding-stream layout only encoded for heights >= 2726400")
    s = subsidy_zats(height)
    zcg = s * 8 // 100
    lockbox = s * 12 // 100
    return s - zcg - lockbox, zcg, lockbox
