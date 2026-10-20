"""
第 1 集实验：井字棋自我对弈。

一个一开始什么都不会的程序，只知道规则和输赢。它自己跟自己下，每下完一盘，
就顺着这盘棋倒着往回记：哪些局面最后通向赢、哪些通向输（时序差分学习，
Sutton & Barto《强化学习》第 1 章那个经典例子）。没有棋谱，没有人教。

每隔一段时间拉它出去考两场试，考试时不学习：
  - 对手 A：随机乱下的程序
  - 对手 B：永远不犯错的程序（把所有走法穷举一遍的 minimax）
井字棋双方都不犯错的结果是和棋，所以对 B 能做到的最好成绩就是「一盘不输」。

用法：python3 selfplay.py        # 5 个随机种子，每个下 5 万盘，大约 1 分钟
输出：results/curve.json、results/games.json、results/curve.png
"""

import json
import random
import time
from functools import lru_cache
from pathlib import Path

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
EMPTY = "." * 9
OUT = Path(__file__).resolve().parent / "results"
TOTAL_GAMES = 50_000
CHECKPOINTS = [0, 10, 30, 100, 200, 300, 500, 1000, 1500, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 30000, 40000, 50000]
SEEDS = [1, 2, 3, 4, 5]
EXAM_GAMES = 100  # 先手、后手各考 100 盘


def winner(b):
    for i, j, k in LINES:
        if b[i] != "." and b[i] == b[j] == b[k]:
            return b[i]
    return "draw" if "." not in b else None


def to_move(b):
    return "X" if b.count("X") == b.count("O") else "O"


def play(b, i, p):
    return b[:i] + p + b[i + 1:]


@lru_cache(maxsize=None)
def minimax(b):
    """站在 X 的角度：1 是 X 赢，0 是 O 赢，0.5 是和棋。"""
    w = winner(b)
    if w:
        return {"X": 1.0, "O": 0.0, "draw": 0.5}[w]
    p = to_move(b)
    vals = [minimax(play(b, i, p)) for i in range(9) if b[i] == "."]
    return max(vals) if p == "X" else min(vals)


def perfect_move(b, rng):
    p = to_move(b)
    moves = [i for i in range(9) if b[i] == "."]
    vals = {i: minimax(play(b, i, p)) for i in moves}
    best = max(vals.values()) if p == "X" else min(vals.values())
    return rng.choice([i for i in moves if vals[i] == best])


def random_move(b, rng):
    return rng.choice([i for i in range(9) if b[i] == "."])


class Learner:
    """一张表：局面 → X 最后赢的可能性。没见过的局面先当 0.5（不知道）。"""

    def __init__(self, rng, alpha=0.3):
        self.v = {}
        self.rng = rng
        self.alpha = alpha

    def value(self, b):
        w = winner(b)
        if w:
            return {"X": 1.0, "O": 0.0, "draw": 0.5}[w]
        return self.v.get(b, 0.5)

    def move(self, b, eps=0.0):
        p = to_move(b)
        moves = [i for i in range(9) if b[i] == "."]
        if self.rng.random() < eps:
            return self.rng.choice(moves), True
        vals = {i: self.value(play(b, i, p)) for i in moves}
        best = max(vals.values()) if p == "X" else min(vals.values())
        return self.rng.choice([i for i in moves if vals[i] == best]), False

    def selfplay_game(self, eps):
        """自己跟自己下一盘，下完倒着更新表。"""
        b, states, moves = EMPTY, [], []
        while not winner(b):
            i, _ = self.move(b, eps)
            b = play(b, i, to_move(b))
            states.append(b)
            moves.append(i)
        target = self.value(states[-1])
        for s in reversed(states[:-1]):
            old = self.v.get(s, 0.5)
            self.v[s] = old + self.alpha * (target - old)
            target = self.v[s]
        return moves, winner(b)


def match(learner, opponent, learner_side, rng):
    b, moves = EMPTY, []
    while not winner(b):
        if to_move(b) == learner_side:
            i, _ = learner.move(b)
        else:
            i = opponent(b, rng)
        b = play(b, i, to_move(b))
        moves.append(i)
    w = winner(b)
    result = "draw" if w == "draw" else ("win" if w == learner_side else "loss")
    return result, moves


def exam(learner, opponent, rng):
    tally = {"win": 0, "draw": 0, "loss": 0}
    for side in ("X", "O"):
        for _ in range(EXAM_GAMES):
            r, _ = match(learner, opponent, side, rng)
            tally[r] += 1
    n = 2 * EXAM_GAMES
    return {k: round(v / n, 4) for k, v in tally.items()}


def run(seed):
    rng = random.Random(seed)
    exam_rng = random.Random(seed + 1000)
    L = Learner(rng)
    curve, games, played, t0 = [], {}, 0, time.time()
    first_selfplay = None
    for cp in CHECKPOINTS:
        while played < cp:
            eps = max(0.05, 0.3 * (1 - played / 20000))
            moves, w = L.selfplay_game(eps)
            if first_selfplay is None:
                first_selfplay = {"moves": moves, "winner": w}
            played += 1
        row = {
            "games": cp,
            "vs_random": exam(L, random_move, exam_rng),
            "vs_perfect": exam(L, perfect_move, exam_rng),
            "positions_known": len(L.v),
            "seconds": round(time.time() - t0, 2),
        }
        curve.append(row)
        if seed == SEEDS[0] and cp in (0, 1000, TOTAL_GAMES):
            games[str(cp)] = {side: dict(zip(("result", "moves"), match(L, perfect_move, side, random.Random(cp + 7)))) for side in ("X", "O")}
    return curve, games, first_selfplay


def main():
    OUT.mkdir(exist_ok=True)
    runs, games, first = {}, None, None
    for s in SEEDS:
        curve, g, f = run(s)
        runs[s] = curve
        if games is None:
            games, first = g, f
        last = curve[-1]
        never_lose = next((r["games"] for i, r in enumerate(curve) if all(x["vs_perfect"]["loss"] == 0 for x in curve[i:])), None)
        print(f"种子 {s}：{last['games']} 盘用时 {last['seconds']} 秒；对完美对手从第 {never_lose} 盘起一盘不输；"
              f"最后对随机对手赢 {last['vs_random']['win'] * 100:.0f}%、输 {last['vs_random']['loss'] * 100:.0f}%；记住 {last['positions_known']} 种局面")

    avg = []
    for n, cp in enumerate(CHECKPOINTS):
        rows = [runs[s][n] for s in SEEDS]
        mean = lambda f: round(sum(f(r) for r in rows) / len(rows), 4)
        avg.append({
            "games": cp,
            "vs_perfect_loss": mean(lambda r: r["vs_perfect"]["loss"]),
            "vs_perfect_draw": mean(lambda r: r["vs_perfect"]["draw"]),
            "vs_random_win": mean(lambda r: r["vs_random"]["win"]),
            "vs_random_loss": mean(lambda r: r["vs_random"]["loss"]),
            "positions_known": mean(lambda r: r["positions_known"]),
            "seconds": mean(lambda r: r["seconds"]),
        })
    (OUT / "curve.json").write_text(json.dumps({"seeds": SEEDS, "exam_games": 2 * EXAM_GAMES, "average": avg, "runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "games.json").write_text(json.dumps({"first_selfplay_game": first, "vs_perfect_at": games}, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n5 个种子平均：")
    print("  已下盘数   对完美对手输   对随机对手赢   对随机对手输   记住的局面")
    for r in avg:
        print(f"  {r['games']:>7}   {r['vs_perfect_loss'] * 100:>9.1f}%   {r['vs_random_win'] * 100:>9.1f}%   {r['vs_random_loss'] * 100:>9.1f}%   {r['positions_known']:>8.0f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Hiragino Sans GB", "Heiti TC", "Arial Unicode MS"]
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=120)
    xs = [max(r["games"], 1) for r in avg]
    for s in SEEDS:
        ax.plot(xs, [r["vs_perfect"]["loss"] * 100 for r in runs[s]], color="#E4572E", alpha=0.18, lw=1)
        ax.plot(xs, [r["vs_random"]["win"] * 100 for r in runs[s]], color="#2E86AB", alpha=0.18, lw=1)
    ax.plot(xs, [r["vs_perfect_loss"] * 100 for r in avg], color="#E4572E", lw=3, label="对「永不犯错」的对手：输的比例")
    ax.plot(xs, [r["vs_random_win"] * 100 for r in avg], color="#2E86AB", lw=3, label="对「随机乱下」的对手：赢的比例")
    ax.set_xscale("log")
    ax.set_xlabel("自己跟自己下了多少盘（对数刻度，最左边是 0 盘）")
    ax.set_ylabel("%")
    ax.set_ylim(-3, 103)
    ax.set_title("井字棋：没人教，自己跟自己下")
    ax.legend(loc="center right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "curve.png")
    print(f"\n图：{OUT / 'curve.png'}")


if __name__ == "__main__":
    main()
