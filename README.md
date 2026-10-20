# RSI 递归自我改进 · 用小实验讲清楚

抖音科普系列「RSI 递归自我改进」的配套代码。每集一个小实验，在自己电脑上就能复现；视频里说的「我写的程序」都在这里。

**RSI**（Recursive Self-Improvement，递归自我改进）拆开是两半：

1. 没人教，AI 自己让自己变强；
2. 变强以后，它更会让自己变强，像滚雪球。

这个系列从最简单的游戏讲起，一集一集往上走，最后讲到各家 AI 公司现在在做的事。

## 每集一览

| 集 | 主题 | 实验 | 结果 | 代码 |
|---|---|---|---|---|
| 1 | 没人教，它自己变强了 | 井字棋自我对弈；再让它改进「自己怎么学」 | 3.5 秒下 5 万盘，对「永不犯错」的对手输棋率 87% → 0%。改学法后，学会所需盘数 13,175 → 4,500，之后到顶 | [ep01-selfplay](ep01-selfplay/) |
| 2 | 会自己出题、自己对答案的 AI | DeepSeek（关深度思考）自己出 24 点题、自己做，程序判卷，做对的写成笔记 | 裸考平均 36 分 → 带笔记平均 50 分（各考 3 次），第一轮之后卡住 | [ep02-24point](ep02-24point/) |

## 视频里说的「我写的程序」

| 视频里的说法 | 文件 |
|---|---|
| 第 1 集：「我写了一个下井字棋的程序」「永远不犯错的考官」 | [ep01-selfplay/selfplay.py](ep01-selfplay/selfplay.py) |
| 第 1 集：「让它改进自己学棋的方法」 | [ep01-selfplay/learn_to_learn.py](ep01-selfplay/learn_to_learn.py) |
| 第 2 集：「我写了一段程序当裁判」 | [ep02-24point/puzzles.py](ep02-24point/puzzles.py) |
| 第 2 集：「自己出题、自己做、程序判卷、写笔记、小测把关」 | [ep02-24point/selftrain.py](ep02-24point/selftrain.py) |
| 第 2 集：「裸考三次，平均 36 分」 | [ep02-24point/repeat_exam.py](ep02-24point/repeat_exam.py) |

## 快速开始

```bash
git clone https://github.com/yorkInvalid/rsi-series.git
cd rsi-series
pip install -r requirements.txt
cp .env.example .env      # 第 2 集要填 DeepSeek 的 key；做视频配音要填腾讯 TokenHub 的 key
```

第 1 集不要任何 key，几十秒跑完：

```bash
cd ep01-selfplay
python3 selfplay.py
python3 learn_to_learn.py
```

第 2 集调 DeepSeek，要花钱，先迷你试跑：

```bash
cd ep02-24point
python3 selftrain.py --pilot        # 20 道题、两轮，封顶 0.5 元，并推算正式跑要多少钱
python3 selftrain.py --budget 3     # 确认值得再正式跑
```

## 花钱的实验怎么跑

所有调 DeepSeek 的实验都走 [common/ds.py](common/ds.py)，自带三道关：

- **闲时才跑**：北京时间工作日 9:00–12:00、14:00–18:00 是 DeepSeek 高峰，单价翻倍。这个时段脚本拒绝启动；跑到一半进入高峰会自动停下。确实要跑加 `--allow-peak`。
- **余额检查**：开跑前查账户余额，不够本次预算就不跑。
- **预算上限**：`--budget 2` 表示这次最多花 2 元，花到就停（按实际 token 和缓存命中计费）。
- **迷你试跑**：`--pilot` 只用少量题、跑两轮，封顶 0.5 元，按实际花费推算正式跑要多少钱。

注意：腾讯云的 Token Plan、Coding Plan 不能用来跑这些实验，它们的条款禁止用于自动化脚本和批量调用。

## 目录

```
common/            所有实验共用：读配置（env.py）、调 DeepSeek（ds.py）、配音（tts.py）
ep01-selfplay/     第 1 集：井字棋自我对弈 + 改进学法
ep02-24point/      第 2 集：自己出题练 24 点；还有第 3 集的候选实验
  */results/       每次实验的原始结果（JSON、图）
  */video/         视频工程：口播稿、配音时间轴、画面生成脚本
```

## 视频怎么做出来的

每集的 `video/` 里：

1. `script.json`：口播稿，一句一行。
2. `python3 make_voice.py`：用腾讯 TokenHub 上的 MiniMax 语音（电台男主播）逐句配音，排出时间轴 `timing.json`。
3. `python3 build.py`：按时间轴和实验数据生成画面 `index.html`，每个画面跟着对应那句话出现。
4. `npx --yes hyperframes@0.8.163 render -o renders/epXX.mp4`：用 [HyperFrames](https://github.com/heygen-com/hyperframes) 渲染成视频（要 Node 22）。

配音音频和渲染出的视频文件比较大，没放进仓库。

## 资料来源

- Dario Amodei，[We Must Pace the Frontier](https://darioamodei.com/post/we-must-pace-the-frontier)，2026 年 9 月
- [CoinDesk：Altman、Musk 的回应](https://www.coindesk.com/tech/2026/09/12/anthropic-ceo-calls-for-ai-race-to-slow-down-musk-and-openai-s-altman-agrees)
- [Digital Today：DeepMind 报告称未见 AI 研发加速](https://www.digitaltoday.co.kr/en/view/115695/google-deepmind-says-no-evidence-ai-self-improvement-acceleration-gap-with-industry-warnings)，2026 年 10 月
- DeepSeek-AI，[DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](https://arxiv.org/abs/2501.12948)，2025 年 1 月
- DeepMind，[AlphaGo Zero: Starting from scratch](https://deepmind.google/discover/blog/alphago-zero-starting-from-scratch/)，2017；盘数据 [Science News](https://www.sciencenews.org/article/newest-alphago-mastered-game-no-human-input)
