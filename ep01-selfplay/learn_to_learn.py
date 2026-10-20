"""
第 1 集实验 B：不光下棋变强，还改进「自己怎么学」。

实验 A 里，学棋的方法是固定的：学得多快（学习速度）、多爱尝试新走法（好奇心）、
好奇心多久收起来、没见过的局面先当成好还是坏（初始乐观程度）。这里把这四个设置交出去：
  1. 每一代拿当前最好的学法，做 7 个小变种，连同它自己一共 8 种学法
  2. 每种学法都从零开始学井字棋，看要下多少盘才「学会」（对完美对手 200 盘一盘不输，并且下一次考试也不输）
  3. 学得最快的那种留下，当下一代的起点
最后用 30 个没用过的随机种子，把第 1 代和每一代的最好学法重新比一遍，排除运气。

说明：挑选和变异是这个脚本（外层循环）做的，不是棋手自己想出来的。它是「递归自我改进」的玩具版：
被改进的对象从「棋力」升了一级，变成「提升棋力的方法」。

用法：python3 learn_to_learn.py      # 几分钟
输出：results/learn_to_learn.json、results/learn_to_learn.png
"""

import json
import math
import random
import time
from pathlib import Path

from selfplay import EMPTY, Learner, match, perfect_move, play, to_move, winner

OUT = Path(__file__).resolve().parent / "results"
CAP = 40_000  # 下到这么多盘还没学会，就按 4 万盘算
CHECK_EVERY = 250
GENERATIONS = 6
CHILDREN = 7
SEEDS_PER_EVAL = 4
VALIDATION_SEEDS = 30
BASE = {"alpha": 0.3, "eps0": 0.3, "decay": 20000, "init": 0.5}  # 实验 A 用的学法


class TunableLearner(Learner):
    def __init__(self, rng, params):
        super().__init__(rng, alpha=params["alpha"])
        self.init = params["init"]

    def value(self, b):
        w = winner(b)
        if w:
            return {"X": 1.0, "O": 0.0, "draw": 0.5}[w]
        return self.v.get(b, self.init)

    def selfplay_game(self, eps):
        b, states = EMPTY, []
        while not winner(b):
            i, _ = self.move(b, eps)
            b = play(b, i, to_move(b))
            states.append(b)
        target = self.value(states[-1])
        for s in reversed(states[:-1]):
            old = self.v.get(s, self.init)
            self.v[s] = old + self.alpha * (target - old)
            target = self.v[s]


def passes(learner, rng, games):
    for n in range(games):
        r, _ = match(learner, perfect_move, "X" if n % 2 == 0 else "O", rng)
        if r == "loss":
            return False
    return True


def games_to_learn(params, seed):
    rng, exam_rng = random.Random(seed), random.Random(seed + 99991)
    L = TunableLearner(rng, params)
    played, streak = 0, 0
    while played < CAP:
        for _ in range(CHECK_EVERY):
            eps = max(0.02, params["eps0"] * (1 - played / params["decay"]))
            L.selfplay_game(eps)
            played += 1
        if passes(L, exam_rng, 200):
            streak += 1
            if streak == 2:
                return played - CHECK_EVERY  # 第一次考过的那个时间点
        else:
            streak = 0
    return CAP


def score(params, seeds):
    return sum(games_to_learn(params, s) for s in seeds) / len(seeds)


def mutate(p, rng):
    return {
        "alpha": round(min(1.0, max(0.02, p["alpha"] * math.exp(rng.gauss(0, 0.4)))), 3),
        "eps0": round(min(0.9, max(0.0, p["eps0"] + rng.gauss(0, 0.1))), 3),
        "decay": int(min(40000, max(500, p["decay"] * math.exp(rng.gauss(0, 0.5))))),
        "init": round(min(1.0, max(0.0, p["init"] + rng.gauss(0, 0.12))), 3),
    }


def main():
    OUT.mkdir(exist_ok=True)
    rng = random.Random(2026)
    best, history, t0 = dict(BASE), [], time.time()
    for g in range(1, GENERATIONS + 1):
        seeds = [10_000 * g + k for k in range(SEEDS_PER_EVAL)]
        cands = [best] + [mutate(best, rng) for _ in range(CHILDREN)]
        scored = sorted(((score(c, seeds), c) for c in cands), key=lambda x: x[0])
        best = scored[0][1]
        history.append({"generation": g, "best": best, "best_games": scored[0][0],
                        "candidates": [{"params": c, "games": s} for s, c in scored]})
        print(f"第 {g} 代：最快的学法平均 {scored[0][0]:.0f} 盘学会  {best}  （{time.time() - t0:.0f} 秒）")

    vseeds = [777_000 + k for k in range(VALIDATION_SEEDS)]
    lineage = [dict(BASE)] + [h["best"] for h in history]
    validation = []
    for g, p in enumerate(lineage):
        runs = [games_to_learn(p, s) for s in vseeds]
        runs.sort()
        row = {"generation": g, "params": p, "mean": round(sum(runs) / len(runs)), "median": runs[len(runs) // 2],
               "failed": sum(r >= CAP for r in runs), "runs": runs}
        validation.append(row)
        print(f"验证 第 {g} 代学法（{VALIDATION_SEEDS} 个新种子）：平均 {row['mean']} 盘，中位数 {row['median']} 盘，没学会 {row['failed']} 次")

    (OUT / "learn_to_learn.json").write_text(json.dumps({"base": BASE, "cap": CAP, "history": history, "validation": validation}, ensure_ascii=False, indent=1), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Hiragino Sans GB", "Heiti TC", "Arial Unicode MS"]
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=120)
    xs = [v["generation"] for v in validation]
    ax.bar(xs, [v["mean"] for v in validation], color=["#9AA5B1"] + ["#2E86AB"] * (len(xs) - 1))
    for x, v in zip(xs, validation):
        ax.text(x, v["mean"], f"{v['mean']:,}", ha="center", va="bottom")
    ax.set_xticks(xs)
    ax.set_xticklabels(["原始学法"] + [f"第 {x} 代" for x in xs[1:]])
    ax.set_ylabel(f"平均要下多少盘才学会（{VALIDATION_SEEDS} 次重复）")
    ax.set_title("改进「自己怎么学」：学会井字棋需要的盘数")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "learn_to_learn.png")
    print(f"图：{OUT / 'learn_to_learn.png'}")


if __name__ == "__main__":
    main()
