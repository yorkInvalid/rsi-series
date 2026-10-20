"""
第 2 集实验：自己出题、自己做、程序判卷、写进笔记，一轮轮考试看正确率。

每一轮：
  1. 出题：DeepSeek 自己出 15 道它觉得有挑战的 24 点题；程序筛掉无解的、考试里出现过的、练过的
  2. 练习：每道题它最多试 3 次，每次都由裁判判对错（默认是程序；--judge self 时让它自己判，第 3 集用）
  3. 记笔记：把「判为做对」的解法交给它，让它更新一份 400 字以内的技巧笔记；再挑最多 12 道判为做对的题当例题
  4. 考试：带着笔记和例题，做同一套 100 道没练过的题，考试永远由程序判卷
第 0 轮是什么都不带的裸考。

v2（--gate，默认开）：新笔记先在「它自己出过的练习题」里抽 40 道小测，和旧笔记比，程序判卷，更好才留下；
正式考卷只记录成绩，不参与任何决定。出题时会告诉它哪些题出过了，每轮凑够至少 20 道新题。

模型不开深度思考，权重不变，变的只是笔记和例题。

用法：
  python3 selftrain.py --rounds 5
  python3 selftrain.py --rounds 5 --judge self --tag selfjudge
"""

import argparse
import json
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ds
import puzzles as pz

OUT = Path(__file__).resolve().parent / "results"
RULES = "用这 4 个数：{nums}。每个数恰好用一次，只能用加减乘除和括号，算出 24。可以先写简短的思路。最后一行只写：答案：算式"
TOKENS = {"in": 0, "out": 0}


def call(user, system="", max_tokens=600, temperature=0.0):
    r = ds.ask(user, system=system, max_tokens=max_tokens, temperature=temperature)
    TOKENS["in"] += r["in"]
    TOKENS["out"] += r["out"]
    return r["text"]


def test_set():
    rng = random.Random(0)
    groups = defaultdict(list)
    for p in pz.all_puzzles():
        d = pz.difficulty(p)
        if d:
            groups[d].append(p)
    return rng.sample(groups["中"], 30) + rng.sample(groups["难"], 60) + rng.sample(groups["分数题"], 10)


def system_prompt(notes, examples):
    if not notes and not examples:
        return ""
    s = "你在练习 24 点。下面是你自己练习后总结的笔记和例题，做题时参考。\n\n"
    if notes:
        s += "【笔记】\n" + notes + "\n\n"
    if examples:
        s += "【例题】\n" + "\n".join(f"{'、'.join(map(str, p))} → {e}" for p, e in examples)
    return s


def solve_once(p, system, temperature, seed):
    order = random.Random(seed).sample(p, 4)
    text = call(RULES.format(nums="、".join(map(str, order))), system=system, temperature=temperature)
    return text, pz.extract(text)


def self_judge(p, text):
    """第 3 集用：让模型自己判自己有没有做对。"""
    verdict = call(f"题目：用 {'、'.join(map(str, p))} 算出 24，每个数用一次。\n下面是一份解答：\n{text}\n\n这份解答对吗？只回答「对」或「错」。", max_tokens=5)
    return "对" in verdict and "错" not in verdict


def exam(tests, system):
    def one(i_p):
        i, p = i_p
        _, expr = solve_once(p, system, 0.0, 1000 + i)
        return pz.check(expr, p)

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, enumerate(tests)))
    return res


def propose(seen, tests, rnd, want=20):
    test_keys = {tuple(sorted(p)) for p in tests}
    got, unsolvable = [], 0
    for attempt in range(4):
        recent = "；".join(" ".join(map(str, k)) for k in list(seen)[-60:])
        text = call("出 15 道你觉得有挑战性、但一定有解的 24 点题。每题 4 个 1 到 13 的整数，可以重复。每行一题，只写 4 个数，用空格隔开。"
                    + (f"\n这些已经出过了，别再出：{recent}" if recent else ""), max_tokens=400, temperature=1.0)
        for line in text.splitlines():
            nums = [int(x) for x in re.findall(r"\d+", line)]
            if len(nums) != 4 or not all(1 <= x <= 13 for x in nums):
                continue
            key = tuple(sorted(nums))
            if key in test_keys or key in seen:
                continue
            seen.add(key)
            if pz.solve(nums):
                got.append(list(key))
            else:
                unsolvable += 1
        if len(got) >= want:
            break
    return got, unsolvable


def quiz(puzzles, system, judge="program"):
    """小测：决定新笔记留不留。--judge self 时，小测也由它自己判。"""
    def one(i_p):
        i, p = i_p
        text, expr = solve_once(p, system, 0.0, 5000 + i)
        return pz.check(expr, p) if judge == "program" else self_judge(p, text)

    with ThreadPoolExecutor(8) as ex:
        return sum(ex.map(one, enumerate(puzzles)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--judge", choices=["program", "self"], default="program")
    ap.add_argument("--tag", default="program")
    ap.add_argument("--no-gate", action="store_true", help="关掉把关：新笔记直接用（第一版试跑的做法）")
    ds.add_args(ap)
    args = ap.parse_args()
    R = args.rounds
    full = (R + 1) * 100 + R * (20 * 2 + 80 + 2)
    if args.pilot:
        args.rounds, args.tag = 2, args.tag + "-pilot"
    pilot = 3 * 20 + 2 * (8 * 2 + 20 + 2)
    ds.run(_run, args, f"自己出题练 24 点（裁判：{'程序' if args.judge == 'program' else '它自己'}）", full, pilot)


def _run(args):

    tests = test_set()
    if args.pilot:
        tests = random.Random(1).sample(tests, 20)
    notes, examples, seen, log = "", [], set(), []
    bank = []  # 它自己出过、程序确认有解的题
    acc0 = exam(tests, "")
    log.append({"round": 0, "accuracy": sum(acc0) / len(acc0), "per_item": acc0, "notes": "", "examples": []})
    print(f"第 0 轮（裸考）：{sum(acc0)}/{len(acc0)}")

    for rnd in range(1, args.rounds + 1):
        practice, unsolvable = propose(seen, tests, rnd, 8 if args.pilot else 20)
        bank += practice
        system = system_prompt(notes, examples)
        judged_right, truly_right, attempts = [], 0, []

        def practice_one(i_p):
            i, p = i_p
            for k in range(3):
                text, expr = solve_once(p, system, 0.8, rnd * 100 + i * 7 + k)
                ok = pz.check(expr, p) if args.judge == "program" else self_judge(p, text)
                if ok:
                    return p, expr, text, pz.check(expr, p), k + 1
            return p, None, None, False, 3

        with ThreadPoolExecutor(8) as ex:
            results = list(ex.map(practice_one, enumerate(practice)))
        for p, expr, text, real, tries in results:
            attempts.append({"puzzle": p, "judged_right": expr is not None, "really_right": real, "tries": tries, "expr": expr})
            if expr is not None:
                judged_right.append((p, expr, text))
                truly_right += real

        solved_txt = "\n".join(f"{'、'.join(map(str, p))}：{e}" for p, e, _ in judged_right) or "（这一轮一道都没做对）"
        failed_txt = "、".join("[" + " ".join(map(str, a["puzzle"])) + "]" for a in attempts if not a["judged_right"]) or "无"
        cand_notes = call(
            f"你在自学 24 点。这是你目前的笔记：\n{notes or '（还没有笔记）'}\n\n这一轮做对的题和你的解法：\n{solved_txt}\n\n"
            f"这一轮试了 3 次都没做对的题：{failed_txt}\n\n"
            "请更新笔记：总结能帮你下次做对的技巧、常用套路和检查方法。只写笔记本身，400 字以内。",
            max_tokens=700, temperature=0.3).strip()
        pool = {tuple(p): (p, e) for p, e, _ in judged_right}
        for p, e in examples:
            pool.setdefault(tuple(p), (p, e))
        ranked = sorted(pool.values(), key=lambda x: {"分数题": 0, "难": 1, "中": 2, "易": 3}[pz.difficulty(x[0])])
        cand_examples = ranked[:12]
        gate = None
        if args.no_gate:
            notes, examples, accepted = cand_notes, cand_examples, True
        else:
            ex_keys = {tuple(p) for p, _ in cand_examples}
            qpool = [p for p in bank if tuple(p) not in ex_keys]
            qs = random.Random(rnd).sample(qpool, min(10 if args.pilot else 40, len(qpool)))
            old_score, new_score = quiz(qs, system, args.judge), quiz(qs, system_prompt(cand_notes, cand_examples), args.judge)
            accepted = new_score > old_score
            gate = {"quiz_size": len(qs), "old": old_score, "new": new_score, "accepted": accepted}
            if accepted:
                notes, examples = cand_notes, cand_examples
        acc = exam(tests, system_prompt(notes, examples))
        log.append({"round": rnd, "accuracy": sum(acc) / len(acc), "per_item": acc, "notes": notes,
                    "examples": examples, "practice": attempts, "proposed_unsolvable": unsolvable, "gate": gate,
                    "candidate_notes": cand_notes, "accepted": accepted})
        g = f"小测 {gate['old']}→{gate['new']}/{gate['quiz_size']}，{'留下新笔记' if accepted else '退回旧笔记'}；" if gate else ""
        print(f"第 {rnd} 轮：出了 {len(practice)} 道新题（另有 {unsolvable} 道无解被筛掉），练习判对 {len(judged_right)} 道"
              f"（其中真对 {truly_right} 道）；{g}考试 {sum(acc)}/{len(acc)}；累计约 {ds.cost(TOKENS['in'], TOKENS['out']):.2f} 元")

    OUT.mkdir(exist_ok=True)
    out = OUT / f"selftrain-{args.tag}.json"
    out.write_text(json.dumps({"judge": args.judge, "tests": tests, "rounds": log, "tokens": TOKENS,
                               "cost_cny": round(ds.cost(TOKENS["in"], TOKENS["out"]), 3)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写到 {out}")
    print("\n最后一轮笔记：\n" + notes)


if __name__ == "__main__":
    main()
