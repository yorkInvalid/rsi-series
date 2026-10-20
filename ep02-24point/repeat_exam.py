"""把裸考、第 1 轮笔记、最后的笔记各在正式考卷上重复考 3 次（题目里数字顺序每次打乱），看提升是不是运气。"""
import json
import random
from concurrent.futures import ThreadPoolExecutor

import ds
import puzzles as pz
import selftrain as st

d = json.load(open("results/selftrain-gated.json", encoding="utf-8"))
tests = d["tests"]
accepted = [r for r in d["rounds"][1:] if r.get("accepted")]
systems = {
    "裸考（没有笔记）": "",
    "第 1 轮的笔记": st.system_prompt(accepted[0]["notes"], [tuple(x) for x in accepted[0]["examples"]]),
    "最后留下的笔记": st.system_prompt(accepted[-1]["notes"], [tuple(x) for x in accepted[-1]["examples"]]),
}
out = {}
for name, sp in systems.items():
    scores = []
    for rep in range(3):
        def one(i_p):
            i, p = i_p
            _, expr = st.solve_once(p, sp, 0.0, 90000 + rep * 1000 + i)
            return pz.check(expr, p)
        with ThreadPoolExecutor(8) as ex:
            scores.append(sum(ex.map(one, enumerate(tests))))
    out[name] = scores
    print(f"{name}：{scores}，平均 {sum(scores) / 3:.1f}")
print(f"约 {ds.cost(st.TOKENS['in'], st.TOKENS['out']):.2f} 元")
json.dump(out, open("results/repeat_exam.json", "w"), ensure_ascii=False, indent=1)
