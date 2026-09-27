#!/usr/bin/env python3
"""Phase E prep: sanity-check a Phase A rosbag before trusting it for replay.

Pure post-processing over a recorded bag (rosbag2_py) -- no live ROS topics,
nothing to gate on hardware. Reports, per topic: message count, approximate
rate, and the largest gap between consecutive messages (a large gap is often
the first sign a sensor dropped out during recording, worth knowing before
building a replay pipeline or odometry factor on top of the bag).

Usage:
    ros2 run laksa_replay bag_stats /path/to/bag_dir
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

import rosbag2_py


def analyze(bag_path: str) -> dict:
    reader = rosbag2_py.SequentialReader()
    storage_options = rosbag2_py.StorageOptions(uri=bag_path, storage_id="sqlite3")
    converter_options = rosbag2_py.ConverterOptions("", "")
    reader.open(storage_options, converter_options)

    timestamps = defaultdict(list)
    while reader.has_next():
        topic, _data, t = reader.read_next()
        timestamps[topic].append(t)  # nanoseconds

    stats = {}
    for topic, ts in timestamps.items():
        ts.sort()
        count = len(ts)
        if count < 2:
            stats[topic] = {"count": count, "rate_hz": None, "max_gap_s": None}
            continue
        duration_s = (ts[-1] - ts[0]) / 1e9
        rate_hz = (count - 1) / duration_s if duration_s > 0 else None
        gaps = [(b - a) / 1e9 for a, b in zip(ts, ts[1:])]
        stats[topic] = {
            "count": count,
            "rate_hz": rate_hz,
            "max_gap_s": max(gaps),
        }
    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bag_path")
    args = parser.parse_args(argv)

    stats = analyze(args.bag_path)
    if not stats:
        print("No topics found in bag.", file=sys.stderr)
        return 1

    name_width = max(len(t) for t in stats)
    print(f"{'topic':<{name_width}}  {'count':>8}  {'rate_hz':>10}  {'max_gap_s':>10}")
    for topic, s in sorted(stats.items()):
        rate = f"{s['rate_hz']:.2f}" if s["rate_hz"] is not None else "n/a"
        gap = f"{s['max_gap_s']:.3f}" if s["max_gap_s"] is not None else "n/a"
        print(f"{topic:<{name_width}}  {s['count']:>8}  {rate:>10}  {gap:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
