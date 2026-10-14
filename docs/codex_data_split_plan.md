# Codex 任务：按 CAMMA 合并划分重建 SurgStream-Bench 数据划分

> 把下面「任务说明」整段交给 Codex，在服务器上的项目根目录里运行。
> 参考实现在 GitHub `RP0929/SurgStreamer` 的 `claude/vibrant-clarke-2sgegp` 分支：
> `tools/splits/camma_combined_split.json`（划分文件）和 `tools/check_split.py`（检查脚本）。

---

## 任务说明（交给 Codex）

### 背景

SurgStream-Bench 由 Cholec80、CholecT50、Endoscapes2023 三个数据集构建。三个数据集来自同一家医院，部分视频是同一台手术，只是在不同数据集里编号不同。旧划分只做了「CholecT50 测试视频不进 Cholec80 训练」，导致测试集泄漏：例如 Cholec80 测试集的 67/68/70/71/72 号就是 Endoscapes 训练集的 1/2/3/4/7 号。

现在改用 CAMMA 官方重叠分析（https://github.com/CAMMA-public/camma_dataset_overlaps ）推荐的合并划分：
- CholecT50、Endoscapes2023 保持官方划分；
- Cholec80 删掉与其他两个数据集冲突的视频。

数据集已经在服务器上，**不要下载任何数据**。

### 目标划分（视频编号即各数据集自己的公开编号）

| 数据集 | train | val | test |
|---|---|---|---|
| Cholec80（删除冲突后） | 36 | 7 | 15 |
| CholecT50（官方） | 35 | 5 | 10 |
| Endoscapes2023（官方） | 120 | 41 | 40 |
| 视频条目合计 | 191 | 53 | 65 |
| 去重后的手术台数 | 171 | 53 | 61 |

```text
Cholec80 train : 1 2 3 4 5 7 8 9 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 33 34 35 36 37 38 39 40
Cholec80 val   : 41 43 44 45 46 47 48
Cholec80 test  : 51 53 54 55 58 59 61 63 64 69 73 74 76 77 80
Cholec80 不使用: 6 10 14 32 | 42 | 49 50 52 56 57 60 62 65 66 67 68 70 71 72 75 78 79

CholecT50 train: 1 2 4 5 13 15 18 22 23 25 26 27 31 35 36 40 43 47 48 49 52 56 57 60 62 65 66 68 70 75 79 92 96 103 110
CholecT50 val  : 8 12 29 50 78
CholecT50 test : 6 10 14 32 42 51 73 74 80 111

Endoscapes train: 1-120   val: 121-161   test: 162-201   （与官方 train_vids.txt / val_vids.txt / test_vids.txt 一致）
```

注意：
- CholecT50 的 92/96/103/110/111 不在 Cholec80 里，这是正常的。
- 同一台手术可能同时出现在两个数据集的**同一个划分**里，比如 Cholec80 的 51 号和 CholecT50 的 51 号都在测试集。这是允许的，因为它们提供的标签不同。
- 验证集里有 8 台手术和训练集重叠（如 Cholec80 val 的 43/47/48 也在 CholecT50 train）。按 CAMMA 方案保留，**不要自行删除**。测试集与训练集的重叠必须为 0。

### 步骤

**第 0 步：只读盘点，不改任何文件**
1. 找到三个数据集在服务器上的根目录，以及现有的数据生成代码和划分定义（搜索 `split`、`train_videos`、`test_videos`、`VID`、`video`、Cholec80 / CholecT50 / Endoscapes 等关键词）。
2. 列出每个数据集在磁盘上的视频编号和命名方式：
   - Cholec80 通常是 `videoXX.mp4`，或 `videoXX/` 帧目录；
   - CholecT50 通常是 `VIDXX/`；
   - Endoscapes 是 `{split}/{VIDEO_ID}_{FRAME}.jpg`，`FRAME` 是 25fps 下的原始帧号，除以 25 得到秒。
3. 确认 Endoscapes 的 `train_vids.txt / val_vids.txt / test_vids.txt` 和上面的编号一致。
4. 输出一份盘点报告 `reports/split_inventory.md`，内容包括：路径、每个数据集实际存在的视频编号、缺失的编号、旧划分写在哪些文件的哪些行。**先停下来把报告给我看，我确认后再继续。**

**第 1 步：落地统一的划分文件**
1. 在仓库里新增 `configs/splits/camma_combined_split.json`。内容直接用参考分支的 `tools/splits/camma_combined_split.json`，没有就按上面的编号生成，结构为：
   - `splits.{cholec80|cholect50|endoscapes}.{train|val|test}`：编号列表；
   - `procedure.{dataset}.{id}`：跨数据集统一的手术编号，用于去重和检查泄漏。
2. 新增一个读取函数，例如 `surgstream/data/splits.py` 里的 `get_split(dataset, video_id) -> "train"|"val"|"test"|None`。返回 `None` 表示该视频不使用（Cholec80 被删掉的 22 个）。
3. 把现有代码里所有写死的划分全部改成调用这个函数，旧的划分定义删除，不要留两套。

**第 2 步：重新生成数据**
1. 用新的划分重新跑 benchmark 的样本生成：17 个任务，训练、验证、测试三个划分，并把旧的输出移到 `*_old/` 目录备份。
2. 每条样本必须带上字段：`dataset`、`video_id`（整数）、`split`、`procedure_id`。
3. 不改任何任务模板、窗口定义或问题改写逻辑，只改划分。

**第 3 步：检查（全部通过才算完成）**
1. 运行 `python tools/check_split.py train=... val=... test=...`（脚本从参考分支拷贝），必须输出 `OK`，退出码为 0。
2. 新增单元测试 `tests/test_splits.py`，至少断言：
   - 各数据集各划分的视频数等于上表（36/7/15、35/5/10、120/41/40）；
   - 测试集的 `procedure_id` 和训练集的交集为空；
   - Cholec80 被删除的 22 个视频没有出现在任何生成样本里；
   - 每个生成样本的 `split` 等于 `get_split(dataset, video_id)`。
3. 把旧数据也跑一遍 `check_split.py`，并把结果写进报告，确认旧数据确实会报 FAIL，以证明检查有效。

**第 4 步：输出统计（论文要用）**

生成 `reports/split_stats.md`，按 数据集 × 划分 列出：
- 视频数、去重手术数；
- 总时长（小时，按 1 fps 帧数 / 3600 计算）；
- 样本数，再按 5 种时间模式（RT/BM/FP/PA/CM）、6 个临床场景（S1–S6）、17 个任务细分。

### 约束
- 不下载数据，不改动原始数据集目录，只读。
- 不改模型、训练代码和任务定义；只改划分相关的代码和生成的数据。
- 每一步单独 commit，commit message 写清楚改了什么。
- 遇到磁盘上的编号和上表对不上（缺视频、命名不同），**停下来报告**，不要自行猜测映射。

### 完成标准
- `check_split.py` 对新数据输出 OK；`pytest tests/test_splits.py` 全部通过。
- 代码里只剩一处划分定义（`configs/splits/camma_combined_split.json`）。
- 交付 `reports/split_inventory.md`、`reports/split_stats.md`，以及新旧数据的检查结果。
