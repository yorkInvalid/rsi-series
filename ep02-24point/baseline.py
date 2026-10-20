"""测 DeepSeek（不开深度思考）在不同难度、两种答题方式下的 24 点正确率，判卷全由程序做。"""
import json
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import ds
import puzzles as pz

RULES = "用这 4 个数：{nums}。每个数恰好用一次，只能用加减乘除和括号，算出 24。"
MODES = {
    "写过程": ("可以先写简短的思路。最后一行只写：答案：算式", 600),
    "直接答": ("不要写任何过程，直接只输出一行：答案：算式", 40),
}

rng = random.Random(0)
groups = defaultdict(list)
for p in pz.all_puzzles():
    d = pz.difficulty(p)
    if d:
        groups[d].append(p)
sample = rng.sample(groups["中"], 40) + rng.sample(groups["难"], 80) + groups["分数题"]

def run(args):
    mode, p = args
    tip, mt = MODES[mode]
    r = ds.ask(RULES.format(nums="、".join(map(str, rng.sample(p, 4)))) + tip, max_tokens=mt)
    return mode, p, pz.check(pz.extract(r["text"]), p), r["in"], r["out"]

jobs = [(m, p) for m in MODES for p in sample]
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(run, jobs))
tin = sum(r[3] for r in res); tout = sum(r[4] for r in res)
for m in MODES:
    for d in ("中", "难", "分数题"):
        rows = [r for r in res if r[0] == m and pz.difficulty(r[1]) == d]
        print(f"{m}  {d}：{sum(r[2] for r in rows)}/{len(rows)} = {sum(r[2] for r in rows) / len(rows) * 100:.0f}%")
print(f"共 {len(res)} 次调用，{tin} 输入 + {tout} 输出 token，约 {ds.cost(tin, tout):.3f} 元")
json.dump([[r[0], r[1], r[2]] for r in res], open("results/baseline.json", "w"), ensure_ascii=False)
