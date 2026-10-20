"""第 3 集候选实验：同一张考卷，它自己判的分和程序判的分差多少。"""
import json
from concurrent.futures import ThreadPoolExecutor

import ds
import puzzles as pz
import selftrain as st

tests = st.test_set()

def one(i_p):
    i, p = i_p
    text, expr = st.solve_once(p, "", 0.0, 70000 + i)
    return pz.check(expr, p), st.self_judge(p, text)

with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(one, enumerate(tests)))
real = sum(r[0] for r in rows); selfs = sum(r[1] for r in rows)
fp = sum(1 for r in rows if r[1] and not r[0]); fn = sum(1 for r in rows if r[0] and not r[1])
print(f"程序判：{real}/100；它自己判：{selfs}/100")
print(f"错的说成对：{fp} 道；对的说成错：{fn} 道")
print(f"约 {ds.cost(st.TOKENS['in'], st.TOKENS['out']):.2f} 元")
json.dump({"real": real, "self": selfs, "false_positive": fp, "false_negative": fn, "rows": rows}, open("results/self_grade.json", "w"))
