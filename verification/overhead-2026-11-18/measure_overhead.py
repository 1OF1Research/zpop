"""Per-block overhead measurement for the 25s -> 20s spacing thread.

Question (Phantom, topic 59035 post 23, 2026-11-18): daily scan work is
flat under the proposal, but per-block overhead grows - 864 more compact
headers and checkpoints a day for every light wallet. Offered to measure
it; we measure it instead.

Method: fetch the actual CompactBlocks a light wallet receives, from the
same public lightwalletd (zec.rocks) zpop's receipts are built from, for
the full receipt window Nov 7-17 2026 (heights 3546328-3584337). For each
block, three serializations of the protobuf as served:
  full     - as served, all pool types requested (what a wallet downloads)
  frame    - vtx removed: height, hash, prevHash, time, header,
             chainMetadata. The pure per-block frame.
  skeleton - frame plus the coinbase entry reduced to index + txid only.
             overhead := skeleton size (frame + the fixed coinbase entry
             every block carries even when it holds nothing for anyone).
  payload  - full - skeleton: every shielded component and transparent
             input/output of every transaction, coinbase included.
Also counted per block: shielded outputs (sapling outputs + orchard
actions + ironwood actions) and all outputs (shielded + transparent vout),
to cross-check Phantom's >250-output figures in his stated height window
3579935-3580346.
"""
import csv, json, sys, time
sys.path.insert(0, "/home/hatch/workspace/zpop-run")
sys.path.insert(0, "/home/hatch/workspace/zpop-run/zpop")
import compact_formats_pb2 as cf
from zpop.chain import Lightwalletd

START, END = 3546328, 3584337
OUT = "/home/hatch/workspace/zpop-run/overhead-2026-11-18"
PH_LO, PH_HI = 3579935, 3580346

def skeleton_of(blk):
    b = cf.CompactBlock()
    b.CopyFrom(blk)
    del b.vtx[:]
    cb = blk.vtx[0]
    sk = b.vtx.add()
    sk.index = cb.index
    sk.txid = cb.txid
    return b

def frame_of(blk):
    b = cf.CompactBlock()
    b.CopyFrom(blk)
    del b.vtx[:]
    return b

def main():
    lwd = Lightwalletd()
    rows = []
    t0 = time.time()
    h = START
    while h <= END:
        hi = min(h + 499, END)
        got = None
        for attempt in range(4):
            try:
                got = lwd.blocks(h, hi, chunk=500)
                break
            except Exception as e:
                print(f"chunk {h}-{hi} attempt {attempt} failed: {e}", flush=True)
                time.sleep(5 * (attempt + 1))
        if got is None:
            raise RuntimeError(f"chunk {h}-{hi} failed permanently")
        for blk in got:
            full = len(blk.SerializeToString())
            skel = len(skeleton_of(blk).SerializeToString())
            frame = len(frame_of(blk).SerializeToString())
            sh_out = sum(len(t.outputs) + len(t.actions) + len(t.ironwoodActions) for t in blk.vtx)
            all_out = sh_out + sum(len(t.vout) for t in blk.vtx)
            rows.append({
                "height": blk.height, "full": full, "overhead": skel,
                "frame": frame, "payload": full - skel,
                "header_len": len(blk.header), "txs": len(blk.vtx),
                "shielded_outputs": sh_out, "all_outputs": all_out,
            })
        print(f"{hi}/{END} rows={len(rows)} elapsed={time.time()-t0:.0f}s", flush=True)
        h = hi + 1

    import io, os
    def write_durable(path, text):
        tmp = path + ".tmp"
        delay = 2
        for attempt in range(12):
            try:
                with open(tmp, "w") as f:
                    f.write(text)
                    f.flush()
                    os.fsync(f.fileno())
                if os.path.getsize(tmp) != len(text.encode()):
                    raise IOError("short write")
                os.replace(tmp, path)
                return
            except OSError as e:
                print(f"write {path} attempt {attempt} refused: {e}", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise IOError(f"could not write {path}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    write_durable(f"{OUT}/per-block.csv", buf.getvalue())

    n = len(rows)
    def mean(k): return sum(r[k] for r in rows) / n
    def median(k):
        s = sorted(r[k] for r in rows)
        return s[n // 2]
    summary = {
        "blocks": n,
        "heights": [rows[0]["height"], rows[-1]["height"]],
        "source": "lightwalletd zec.rocks:443, CompactBlock as served, all pool types",
        "mean_full_bytes": mean("full"),
        "mean_overhead_bytes": mean("overhead"),
        "median_overhead_bytes": median("overhead"),
        "mean_frame_bytes": mean("frame"),
        "header_len_bytes": rows[0]["header_len"],
        "mean_payload_bytes": mean("payload"),
        "overhead_share_of_stream_pct": 100.0 * sum(r["overhead"] for r in rows) / sum(r["full"] for r in rows),
    }
    # Daily figures: payload is driven by transactions (daily totals are
    # capped the same at both spacings); overhead scales with block count.
    payload_day = summary["mean_payload_bytes"] * 3456  # per current day
    # better: payload per day from the actual 11 days
    payload_day = sum(r["payload"] for r in rows) / 11.0
    ov = summary["mean_overhead_bytes"]
    summary["daily"] = {
        "payload_bytes_per_day_measured": payload_day,
        "overhead_bytes_per_day_25s": ov * 3456,
        "overhead_bytes_per_day_20s": ov * 4320,
        "overhead_delta_bytes_per_day": ov * 864,
        "total_stream_per_day_25s": payload_day + ov * 3456,
        "total_stream_per_day_20s": payload_day + ov * 4320,
    }
    d = summary["daily"]
    d["total_delta_pct"] = 100.0 * (d["total_stream_per_day_20s"] - d["total_stream_per_day_25s"]) / d["total_stream_per_day_25s"]
    # Phantom cross-check in his stated height window
    win = [r for r in rows if PH_LO <= r["height"] <= PH_HI]
    for key in ("shielded_outputs", "all_outputs"):
        big = [r for r in win if r[key] > 250]
        tot = sum(r[key] for r in win)
        bigshare = sum(r[key] for r in big) / tot * 100 if tot else 0
        summary[f"phantom_window_{key}"] = {
            "blocks_in_window": len(win), "blocks_over_250": len(big),
            "share_of_outputs_pct": bigshare}
    write_durable(f"{OUT}/summary.json", json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
