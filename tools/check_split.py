#!/usr/bin/env python3
"""Check that generated SurgStream-Bench data follows the CAMMA combined split.

Every record must name its source dataset and video. The split comes from the
file (``train=path``) or from a field in each record (``--split-key``).

Examples:
    python tools/check_split.py train=data/train.jsonl val=data/val.jsonl test=data/test.jsonl
    python tools/check_split.py data/all.jsonl --split-key split

Exit code 0 means the data matches tools/splits/camma_combined_split.json and no
test procedure appears in training; 1 means a violation was found.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SPLIT_FILE = Path(__file__).with_name("splits") / "camma_combined_split.json"
SPLITS = ("train", "val", "test")
DATASET_KEYS = ("dataset", "source", "data_source", "src")
VIDEO_KEYS = ("video_id", "video", "vid", "video_name", "video_path", "frame", "image")


def norm_dataset(name):
    s = str(name).lower().replace("-", "").replace("_", "")
    if "endoscapes" in s:
        return "endoscapes"
    if "t50" in s or "cholect" in s:
        return "cholect50"
    if "cholec80" in s or "c80" in s:
        return "cholec80"
    return None


def parse_video(value, dataset):
    s = Path(str(value)).name
    if dataset == "endoscapes":
        m = re.match(r"(\d+)_\d+", s)  # frame files are named {VIDEO_ID}_{FRAME_NUM}.jpg
        if m:
            return int(m.group(1))
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def first_key(record, keys, override):
    if override:
        return record.get(override)
    for k in keys:
        if k in record:
            return record[k]
    return None


def load_records(path):
    text = Path(path).read_text()
    if path.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), [data])
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", nargs="+", help="split=path, or path together with --split-key")
    ap.add_argument("--split-key", help="record field holding train/val/test")
    ap.add_argument("--dataset-key", help="record field holding the source dataset")
    ap.add_argument("--video-key", help="record field holding the video id or frame path")
    args = ap.parse_args()

    ref = json.loads(SPLIT_FILE.read_text())
    expected = {d: {s: set(v) for s, v in sp.items()} for d, sp in ref["splits"].items()}
    procedure = {d: {int(k): p for k, p in m.items()} for d, m in ref["procedure"].items()}

    used = defaultdict(set)  # (dataset, split) -> video ids
    unparsed = 0
    for item in args.data:
        split, path = item.split("=", 1) if "=" in item else (None, item)
        for rec in load_records(path):
            s = split or (rec.get(args.split_key) if args.split_key else None)
            d = norm_dataset(first_key(rec, DATASET_KEYS, args.dataset_key) or "")
            raw = first_key(rec, VIDEO_KEYS, args.video_key)
            if d is None and raw is not None:
                d = norm_dataset(raw)  # e.g. a path such as .../endoscapes/1_29375.jpg
            v = parse_video(raw, d) if raw is not None else None
            if s not in SPLITS or d is None or v is None:
                unparsed += 1
                continue
            used[(d, s)].add(v)

    errors = []
    for (d, s), vids in sorted(used.items()):
        wrong = sorted(vids - expected[d][s])
        print(f"{d:10s} {s:5s}: {len(vids):3d} videos used, {len(expected[d][s]):3d} expected")
        for v in wrong:
            home = next((t for t in SPLITS if v in expected[d][t]), "removed from the combined split")
            errors.append(f"{d} video {v} is in {s} but belongs to: {home}")

    train_procs = {procedure[d].get(v, f"{d}:{v}") for (d, s), vids in used.items() if s == "train" for v in vids}
    for (d, s), vids in sorted(used.items()):
        if s == "test":
            for v in sorted(vids):
                if procedure[d].get(v, f"{d}:{v}") in train_procs:
                    errors.append(f"leak: {d} test video {v} is the same procedure as a training video")

    if unparsed:
        print(f"warning: {unparsed} records skipped (no split, dataset or video id); pass --*-key options")
    if errors:
        print(f"\nFAIL: {len(errors)} problem(s); the data was likely generated with the old split")
        for e in errors:
            print("  " + e)
        return 1
    print("\nOK: data follows the CAMMA combined split and no test procedure is seen in training")
    return 0


if __name__ == "__main__":
    sys.exit(main())
