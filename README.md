# SurgStreamer
SurgStreamer: workflow-anchored proactive streaming for real-time surgical video interaction (ISBI 2027)

## Data split check

`tools/splits/camma_combined_split.json` holds the combined Cholec80 / CholecT50 / Endoscapes2023 split derived from the [CAMMA overlap analysis](https://github.com/CAMMA-public/camma_dataset_overlaps) (CC BY-NC-SA 4.0): official CholecT50 and Endoscapes2023 splits, Cholec80 reduced to 36/7/15 videos, 171/53/61 unique procedures. To verify generated data:

```bash
python tools/check_split.py train=data/train.jsonl val=data/val.jsonl test=data/test.jsonl
# or, when each record has a split field
python tools/check_split.py data/all.jsonl --split-key split
```

Each record needs its source dataset and video id (or an Endoscapes frame name such as `1_29375.jpg`); use `--dataset-key` / `--video-key` if the fields have other names. The script exits with 1 and lists every video in the wrong split and every test procedure seen in training.
