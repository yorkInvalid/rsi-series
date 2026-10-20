"""
24 点的程序裁判：穷举解法、判卷、给题目分难度。全程不用 AI。

规则：4 个 1–13 的整数，每个恰好用一次，只能用加减乘除和括号，算出 24。不能把数字拼起来，不能用负号开头。
"""

import ast
import itertools
import re
from fractions import Fraction
from functools import lru_cache

OPS = "+-*/"


@lru_cache(maxsize=None)
def _combos(nums):
    """nums 是排好序的 Fraction 元组，返回 {值: 一个算式}。"""
    if len(nums) == 1:
        return {nums[0]: str(nums[0])}
    out = {}
    n = len(nums)
    idx = range(n)
    for k in range(1, n // 2 + 1):
        for left in itertools.combinations(idx, k):
            right = tuple(i for i in idx if i not in left)
            if k == n - k and left > right:
                continue
            a = _combos(tuple(sorted(nums[i] for i in left)))
            b = _combos(tuple(sorted(nums[i] for i in right)))
            for va, ea in a.items():
                for vb, eb in b.items():
                    cands = [(va + vb, f"({ea}+{eb})"), (va * vb, f"({ea}*{eb})"),
                             (va - vb, f"({ea}-{eb})"), (vb - va, f"({eb}-{ea})")]
                    if vb != 0:
                        cands.append((va / vb, f"({ea}/{eb})"))
                    if va != 0:
                        cands.append((vb / va, f"({eb}/{ea})"))
                    for v, ex in cands:
                        out.setdefault(v, ex)
    return out


def solve(nums):
    """有解就返回一个算式，没解返回 None。"""
    r = _combos(tuple(sorted(Fraction(x) for x in nums)))
    ex = r.get(Fraction(24))
    return ex[1:-1] if ex else None


def _all_values_no_fraction(nums):
    """只允许中间结果是整数时，能不能算出 24。用来判断一道题是不是「必须用分数」。"""
    @lru_cache(maxsize=None)
    def go(ns):
        if len(ns) == 1:
            return {ns[0]}
        vals = set()
        n = len(ns)
        for k in range(1, n):
            for left in itertools.combinations(range(n), k):
                right = tuple(i for i in range(n) if i not in left)
                for a in go(tuple(sorted(ns[i] for i in left))):
                    for b in go(tuple(sorted(ns[i] for i in right))):
                        vals |= {a + b, a * b, a - b}
                        if b != 0 and a % b == 0:
                            vals.add(a // b)
        return vals
    return 24 in go(tuple(sorted(nums)))


def count_solutions(nums):
    """数一数有多少种「本质不同」的算法：按每一步的运算结构去重，粗略但够分难度用。"""
    seen = set()

    def go(items):
        if len(items) == 1:
            v, ex = items[0]
            if v == 24:
                seen.add(ex)
            return
        for i, j in itertools.combinations(range(len(items)), 2):
            (va, ea), (vb, eb) = items[i], items[j]
            rest = [items[k] for k in range(len(items)) if k not in (i, j)]
            a, b = sorted([ea, eb])
            res = [(va + vb, f"({a}+{b})"), (va * vb, f"({a}*{b})"), (va - vb, f"({ea}-{eb})"), (vb - va, f"({eb}-{ea})")]
            if vb != 0:
                res.append((va / vb, f"({ea}/{eb})"))
            if va != 0:
                res.append((vb / va, f"({eb}/{ea})"))
            for v, ex in res:
                go(rest + [(v, ex)])

    go([(Fraction(x), str(x)) for x in nums])
    return len(seen)


def difficulty(nums):
    if not solve(nums):
        return None
    if not _all_values_no_fraction(nums):
        return "分数题"  # 中间一定要出现分数，最难
    c = count_solutions(nums)
    return "难" if c <= 2 else ("中" if c <= 6 else "易")


ALLOWED = set("0123456789+-*/() ")


def extract(text):
    """从回答里取出最后一行「答案：」后面的算式。"""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    for line in reversed(lines):
        m = re.search(r"答案\s*[:：]\s*(.+)", line)
        if m:
            return m.group(1)
    return lines[-1] if lines else ""


def normalize(expr):
    expr = expr.replace("×", "*").replace("x", "*").replace("X", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
    expr = expr.replace("（", "(").replace("）", ")").replace("`", "").replace("$", "")
    expr = expr.split("=")[0]
    return expr.strip()


def check(expr, nums):
    """程序判卷：算式只用了这 4 个数、各一次，结果正好是 24，才算对。"""
    e = normalize(expr)
    if not e or set(e) - ALLOWED:
        return False
    try:
        tree = ast.parse(e, mode="eval").body
    except SyntaxError:
        return False
    used = []

    def ev(n):
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if b == 0:
                raise ZeroDivisionError
            return a / b
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            used.append(n.value)
            return Fraction(n.value)
        raise ValueError("不允许的写法")

    try:
        v = ev(tree)
    except (ValueError, ZeroDivisionError, RecursionError):
        return False
    return v == 24 and sorted(used) == sorted(nums)


def all_puzzles():
    return [list(c) for c in itertools.combinations_with_replacement(range(1, 14), 4)]


if __name__ == "__main__":
    from collections import Counter
    tally = Counter()
    for p in all_puzzles():
        tally[difficulty(p)] += 1
    print("1–13 全部 4 数组合：", sum(tally.values()), "道")
    for k in ("易", "中", "难", "分数题", None):
        print(f"  {k or '无解'}：{tally[k]}")
    assert check("8/(3-8/3)", [3, 3, 8, 8]) and check("8÷(3−8÷3)=24", [8, 3, 8, 3])
    assert not check("8/(3-8/3)", [3, 3, 8, 9]) and not check("(13+11)", [13, 11, 1, 1])
    print("判卷自检通过")
