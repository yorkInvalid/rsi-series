"""
按 timing.json（配音时间轴）和 ../results 里的实验数据，生成第 2 集的 index.html（HyperFrames 合成）。
结构沿用第 1 集的 build.py。改了文案就先跑 make_voice.py，再跑这个。
  python3 build.py
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
T = json.loads((HERE / "timing.json").read_text(encoding="utf-8"))
L = {l["id"]: l for l in T["lines"]}
DUR = T["duration"]
GATED = json.loads((RES / "selftrain-gated.json").read_text(encoding="utf-8"))
REPEAT = json.loads((RES / "repeat_exam.json").read_text(encoding="utf-8"))

s = lambda i: L[i]["start"]
e = lambda i: L[i]["end"]
ss = lambda i: L[i]["scene_start"]
se = lambda i: L[i]["scene_end"]
r = lambda x: round(x, 3)
A = []


def fade_in(sel, t, dur=0.4, y=24):
    A.append(f'tl.fromTo("{sel}", {{ opacity: 0, y: {y} }}, {{ opacity: 1, y: 0, duration: {dur}, ease: "power3.out" }}, {r(t)});')


def pop(sel, t):
    A.append(f'tl.fromTo("{sel}", {{ opacity: 0, scale: 1.5 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.2)" }}, {r(t)});')


def show(sel, t, dur=0.25):
    A.append(f'tl.fromTo("{sel}", {{ opacity: 0 }}, {{ opacity: 1, duration: {dur} }}, {r(t)});')


def dim(sel, t, to=0.0, dur=0.3):
    A.append(f'tl.to("{sel}", {{ opacity: {to}, duration: {dur} }}, {r(t)});')


SC = []


def scene(sid, a, b, inner):
    SC.append(f'<section id="{sid}" class="clip scene" data-start="{r(ss(a))}" data-duration="{r(se(b) - ss(a))}" data-track-index="1">{inner}</section>')


def cards(nums, cid, big=False):
    return f'<div class="cards{" big" if big else ""}" id="{cid}">' + "".join(f'<div class="card">{n}</div>' for n in nums) + "</div>"


# 1 上一集的问题
scene("s-hook", "h1", "h2", """
<div class="duo" id="hk-duo">
<div class="dcard" id="hk-a"><svg width="150" height="150" viewBox="0 0 150 150" class="ttt"><path d="M50 10V140M100 10V140M10 50H140M10 100H140"/><path d="M18 18L42 42M42 18L18 42M108 58L132 82M132 58L108 82" class="x"/><circle cx="75" cy="75" r="14" class="o"/><circle cx="25" cy="125" r="14" class="o"/></svg>
<div class="dt">井字棋</div><div class="dj ok">裁判：输赢</div></div>
<div class="dcard" id="hk-b"><div class="dq">∑ { }</div><div class="dt">做数学题 · 写代码</div><div class="dj">裁判：<b>？</b></div></div>
</div>
<div class="paper" id="hk-p"><div class="kicker">2025 年 1 月 · DeepSeek</div>
<div class="pt">DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning</div><div class="pn">arXiv 2501.12948</div></div>
""")
fade_in("#hk-a", ss("h1") + 0.3)
fade_in("#hk-b", s("h1") + 3.0)
dim("#hk-duo", s("h2") - 0.1)
fade_in("#hk-p", s("h2") + 0.1)

# 2 R1-Zero 怎么练
scene("s-r1", "r1", "r2", """
<div class="flow" id="r1-flow">
<div class="node" id="r1-n1">题目</div><b class="arr" id="r1-a1">→</b>
<div class="node hl" id="r1-n2">R1-Zero<small>自己做</small></div><b class="arr" id="r1-a2">→</b>
<div class="node" id="r1-n3">答案</div><b class="arr" id="r1-a3">→</b>
<div class="node judge" id="r1-n4">裁判</div><b class="arr" id="r1-a4">→</b>
<div class="node" id="r1-n5"><span class="ok">对 +1</span><span class="no">错 0</span></div>
</div>
<div class="nohuman" id="r1-x">不给看人写的解题过程</div>
<div class="judgebox" id="r1-j"><div class="jh">不是人，也不是 AI，是一段程序</div><div class="jc"><span>数学题：对答案</span><span>编程题：把代码跑一遍</span></div></div>
<div class="loopback" id="r1-loop">↺ 拿着分数接着练</div>
""")
for k in range(1, 6):
    show(f"#r1-n{k}", s("r1") + 0.5 + k * 0.45)
    if k < 5:
        show(f"#r1-a{k}", s("r1") + 0.7 + k * 0.45)
pop("#r1-x", s("r1") + 4.2)
A.append(f'tl.fromTo("#r1-n4", {{ scale: 1 }}, {{ scale: 1.15, duration: 0.3, yoyo: true, repeat: 1 }}, {r(s("r2") + 0.2)});')
fade_in("#r1-j", s("r2") + 1.6)
show("#r1-loop", s("r2") + 4.0)

# 3 AIME 15.6% → 71%
scene("s-aime", "r3", "r3", """
<div class="kicker c">AIME 2024 · 美国数学竞赛</div>
<div class="aime"><span id="ai-v">15.6</span><small>%</small></div>
<div class="track"><div class="fill" id="ai-f"></div></div>
<div class="aime-lab">R1-Zero 自己刷题过程中的正确率</div>
<div class="src">来源：DeepSeek-R1 论文（arXiv 2501.12948）</div>
""")
A.append(f'tl.fromTo(AIME, {{ v: 15.6 }}, {{ v: 71.0, duration: 2.6, ease: "power2.inOut" }}, {r(s("r3") + 3.2)});')
A.append(f'tl.fromTo("#ai-f", {{ scaleX: 0.156 }}, {{ scaleX: 0.71, duration: 2.6, ease: "power2.inOut" }}, {r(s("r3") + 3.2)});')

# 4 顿悟时刻
scene("s-aha", "r4", "r4", """
<div class="bubble" id="ah-b">……等一下。<br>我回头检查一下前面这一步。</div>
<div class="aha" id="ah-t">顿悟时刻 <span>aha moment</span></div>
<div class="footnote" id="ah-n">示意：模型自己学会了回头重新审视最初的解法（论文原文有英文示例）</div>
""")
fade_in("#ah-b", s("r4") + 1.2)
pop("#ah-t", s("r4") + 6.0)
show("#ah-n", s("r4") + 6.6)

# 5 关键是裁判
scene("s-key", "k1", "k1", """
<div class="big2 top" id="ky-t">关键：<span class="gold">自动裁判</span></div>
<div class="chips2" id="ky-c"><span>数学：有标准答案</span><span>代码：能跑起来验证</span></div>
<div class="loop2" id="ky-l"><span>自己出题</span><b>→</b><span>自己刷题</span><b>→</b><span>越练越强</span></div>
""")
pop("#ky-t", s("k1") + 0.2)
fade_in("#ky-c", s("k1") + 2.0)
fade_in("#ky-l", s("k1") + 5.6)

# 6 24 点 + 程序裁判
scene("s-24", "e1", "e2", f"""
<div class="kicker c top2">小号版本：24 点</div>
{cards([1, 2, 3, 4], "tf-c", big=True)}
<div class="rules" id="tf-r"><span>每个数用一次</span><span>加减乘除</span><span>算出 24</span></div>
<div class="prog" id="tf-p"><div class="ph">裁判程序</div>
<div class="pl ok" id="tf-p1">1 × 2 × 3 × 4 = 24　✓</div><div class="pl no" id="tf-p2">(1 + 2) × 3 + 4 = 13　✗</div></div>
""")
fade_in("#tf-c", s("e1") + 3.5)
fade_in("#tf-r", s("e1") + 6.0)
dim("#tf-r", s("e2") - 0.1)
fade_in("#tf-p", s("e2") + 0.1)
pop("#tf-p1", s("e2") + 0.8)
pop("#tf-p2", s("e2") + 1.6)

# 7 裸考
rep = REPEAT
base_scores = rep["裸考（没有笔记）"]
note_scores = rep["第 1 轮的笔记"]
scene("s-base", "e3", "c1", f"""
<div class="player" id="bs-p"><div class="pn2">选手：DeepSeek</div><div class="toggle">深度思考 <b>关</b></div><div class="pq">裸考 100 道有难度的 24 点</div></div>
<div id="bs-ex">{cards([3, 3, 8, 8], "bs-c", big=True)}
<div class="steps"><span id="bs-s1">8 ÷ 3 = 8/3</span><span id="bs-s2">3 − 8/3 = 1/3</span><span id="bs-s3">8 ÷ 1/3 = <b>24</b></span></div></div>
<div class="exams" id="bs-x">{"".join(f'<div class="ex2">第 {k + 1} 次<b>{v}</b></div>' for k, v in enumerate(base_scores))}</div>
<div class="bigscore" id="bs-s">平均 <b>{round(sum(base_scores) / 3)}</b> 分</div>
""")
fade_in("#bs-p", s("e3") + 0.2)
dim("#bs-p", s("e4") - 0.1)
fade_in("#bs-ex", s("e4") + 0.1)
for k, t in enumerate((2.6, 4.6, 6.6)):
    pop(f"#bs-s{k + 1}", s("e4") + t)
dim("#bs-ex", s("c1") - 0.1)
fade_in("#bs-x", s("c1") + 0.1)
pop("#bs-s", s("c1") + 1.2)

# 8 自己练的循环
scene("s-loop", "l1", "l1b", """
<div class="cycle" id="lp">
<div class="cn n1" id="lp1">出题<i>它</i></div><div class="cn n2" id="lp2">做题<i>它</i></div>
<div class="cn n3" id="lp3">判卷<i class="pg">程序</i></div><div class="cn n4" id="lp4">写笔记<i>它</i></div>
<svg class="ring" width="760" height="560" viewBox="0 0 760 560"><ellipse cx="380" cy="280" rx="300" ry="200"/></svg>
<div class="center" id="lp-c">带着笔记<br>再来一轮</div>
</div>
<div class="human" id="lp-h">人：<b>0</b> 次插手</div>
""")
for k in range(1, 5):
    pop(f"#lp{k}", s("l1") + 2.2 + (k - 1) * 1.2)
fade_in("#lp-c", s("l1") + 7.2)
A.append(f'tl.fromTo("#lp i", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, stagger: 0.5 }}, {r(s("l1b") + 1.0)});')
pop("#lp-h", s("l1b") + 4.0)

# 9 无解的题
rounds = GATED["rounds"][1:]
n_new = sum(len(x["practice"]) for x in rounds)
n_bad = sum(x["proposed_unsolvable"] for x in rounds)
scene("s-unsolv", "l2", "l2", f"""
<div class="tiles" id="us-t">{"".join(f'<div class="tile"><span>? ? ? ?</span><em id="us-x{k}">无解</em></div>' for k in range(n_bad))}</div>
<div class="sub3" id="us-s">它自己出的题：<b>{n_new}</b> 道有解，<b class="red">{n_bad}</b> 道根本无解</div>
""")
fade_in("#us-t", s("l2") + 0.4)
for k in range(n_bad):
    pop(f"#us-x{k}", s("l2") + 2.6 + k * 0.1)
fade_in("#us-s", s("l2") + 4.4)

# 10 笔记把关
gates = [x["gate"] for x in rounds]
tiles = "".join(
    f'<div class="gt {"keep" if g["accepted"] else "back"}" id="gt{k}"><div class="gr">第 {k + 1} 轮</div>'
    f'<div class="gs">旧 {g["old"]} → 新 {g["new"]}</div><div class="gv">{"✓ 留下" if g["accepted"] else "✗ 退回"}</div></div>'
    for k, g in enumerate(gates))
scene("s-gate", "l3", "l4", f"""
<div class="gtitle" id="gt-h">新笔记先在它自己出的题上小测（答对几道），比旧的好才留下</div>
<div class="gates">{tiles}</div>
<div class="big2 low" id="gt-b">裁判不光判题，还在判笔记</div>
""")
fade_in("#gt-h", s("l3") + 0.6)
for k in range(len(gates)):
    pop(f"#gt{k}", s("l3") + 4.0 + k * 0.5)
pop("#gt-b", s("l4") + 0.1)

# 11 笔记内容
scene("s-notes", "n1", "n1", """
<div class="notebook" id="nb"><div class="nh">它自己写的笔记（节选）</div>
<div class="nl" id="nb1">凑因数：优先想 3×8、4×6、2×12</div>
<div class="nl" id="nb2">两个相同的数，常能造出 1（如 3÷3）</div>
<div class="nl" id="nb3">用「除以分数」放大，如 6÷(1−3÷4)</div>
<div class="nl dimmed">试 3 次不对就换分组方式，不要重复同一思路</div></div>
""")
fade_in("#nb", s("n1") + 0.2)
for k, t in enumerate((2.4, 4.6, 6.6)):
    A.append(f'tl.fromTo("#nb{k + 1}", {{ backgroundColor: "rgba(242,193,78,0)" }}, {{ backgroundColor: "rgba(242,193,78,0.22)", duration: 0.3 }}, {r(s("n1") + t)});')

# 12 结果
examples = [([2, 5, 5, 11], "2×(11+5÷5)"), ([2, 3, 10, 10], "10−2×(3−10)"), ([1, 9, 11, 11], "(1+11)×(11−9)")]
scene("s-result", "c2", "c3", f"""
<div class="cmp" id="rs-cmp">
<div class="cb"><div class="cbv gray" id="rs-b0">{round(sum(base_scores) / 3)}</div><div class="cbar gray" style="height:{sum(base_scores) / 3 * 6:.0f}px" id="rs-bar0"></div><div class="cbl">裸考<small>{"、".join(map(str, base_scores))}</small></div></div>
<div class="cb"><div class="cbv gold" id="rs-b1">{round(sum(note_scores) / 3)}</div><div class="cbar gold" style="height:{sum(note_scores) / 3 * 6:.0f}px" id="rs-bar1"></div><div class="cbl">带着笔记<small>{"、".join(map(str, note_scores))}</small></div></div>
</div>
<div class="fixed" id="rs-fx">{"".join(f'<div class="fx" id="rs-f{k}"><div class="fxn">{" ".join(map(str, p))}</div><div class="fxs"><span class="no">裸考 ✗</span> → <span class="ok">带笔记 ✓</span></div><div class="fxe">解法之一：{sol}</div></div>' for k, (p, sol) in enumerate(examples))}</div>
""")
fade_in("#rs-cmp", s("c2") + 0.1)
A.append(f'tl.fromTo(["#rs-bar0", "#rs-bar1"], {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.6, stagger: 1.4, ease: "power3.out" }}, {r(s("c2") + 0.3)});')
A.append(f'tl.fromTo(["#rs-b0", "#rs-b1"], {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, stagger: 1.4 }}, {r(s("c2") + 0.8)});')
dim("#rs-cmp", s("c3") - 0.1)
for k in range(3):
    fade_in(f"#rs-f{k}", s("c3") + 0.8 + k * 0.6)

# 13 卡住了
accs = [round(x["accuracy"] * 100) for x in GATED["rounds"]]
W, H, X0, Y0 = 1100, 400, 170, 230
px = lambda k: X0 + k * W / (len(accs) - 1)
py = lambda v: Y0 + H - v / 100 * H
pts = " ".join(f"{px(k):.0f},{py(v):.0f}" for k, v in enumerate(accs))
dots = "".join(f'<circle cx="{px(k):.0f}" cy="{py(v):.0f}" r="9"/><text x="{px(k):.0f}" y="{py(v) - 22:.0f}" class="pv">{v}</text>'
               f'<text x="{px(k):.0f}" y="{Y0 + H + 46}" class="px">{"裸考" if k == 0 else f"第 {k} 轮"}</text>' for k, v in enumerate(accs))
scene("s-plateau", "p1", "p2", f"""
<svg class="plat" id="pl-c" width="1920" height="760" viewBox="0 0 1920 760">
<rect x="{px(1) - 40:.0f}" y="{py(55):.0f}" width="{px(6) - px(1) + 80:.0f}" height="{py(42) - py(55):.0f}" rx="20" class="band" id="pl-band"/>
<line x1="{X0}" y1="{Y0 + H}" x2="{X0 + W}" y2="{Y0 + H}" class="axis"/>
<polyline points="{pts}" class="pline"/>{dots}</svg>
<div class="bandlab" id="pl-l">卡在 50 分上下</div>
<div class="crib" id="pl-k">笔记 ≈ 考试带的<b>小抄</b></div>
<div class="vs2" id="pl-v"><div class="vc"><div class="vh">我的实验</div><div class="vb">大脑不变<br>只改一页笔记</div></div>
<div class="vc hl2"><div class="vh">DeepSeek R1</div><div class="vb">练习结果<br>写进了大脑（模型参数）</div></div></div>
<div class="badge" id="pl-g">后面一集：花 <b>10</b> 块钱租张显卡试试</div>
""")
fade_in("#pl-c", s("p1") + 0.1)
show("#pl-band", s("p1") + 2.2)
pop("#pl-l", s("p1") + 2.5)
dim("#pl-c", s("p3") - 0.1, 0.2)
dim("#pl-l", s("p3") - 0.1)
pop("#pl-k", s("p3") + 0.3)
dim("#pl-k", s("p2") - 0.1)
dim("#pl-c", s("p2") - 0.1, 0)
fade_in("#pl-v", s("p2") + 0.2)
pop("#pl-g", s("p2") + 7.0)

# 14 两集回顾
scene("s-recap", "s1", "s1", """
<div class="recap" id="rc">
<div class="rcard" id="rc1"><div class="rk">第 1 集</div><div class="rt">自己跟自己下棋</div><div class="rj">裁判：输赢</div></div>
<div class="rcard" id="rc2"><div class="rk">第 2 集</div><div class="rt">自己出题自己刷题</div><div class="rj">裁判：程序</div></div>
</div>
<div class="big2 low" id="rc-b">共同点：一个<span class="gold">靠谱的裁判</span></div>
""")
fade_in("#rc1", s("s1") + 1.4)
fade_in("#rc2", s("s1") + 4.0)
pop("#rc-b", s("s1") + 7.2)

# 15 论文里的细节 + 下一集
scene("s-twist", "x1", "x2", """
<div class="quote big" id="tw-q"><div class="who">DeepSeek-R1 论文</div>
<div class="say">裁判不用 AI 模型。原因之一：大规模训练中，它可能被「钻空子」（reward hacking）。</div><div class="note">大意，见论文奖励设计一节</div></div>
<div class="big2 low" id="tw-a">如果裁判就是 AI 自己？</div>
<div class="sub2 low2" id="tw-b">它会给自己放水吗？</div>
""")
fade_in("#tw-q", s("x1") + 1.0)
dim("#tw-q", s("x2") - 0.1, 0.25)
pop("#tw-a", s("x2") + 0.2)
fade_in("#tw-b", s("x2") + 2.4)

scene("s-next", "x3", "x3", """
<div class="kicker c top3">下一集</div>
<div class="nx2" id="nx2">AI 当自己的裁判</div>
<div class="follow" id="nx4">关注我 · 下一集见</div>
""")
fade_in("#nx2", s("x3") - 0.1)
pop("#nx4", s("x3") + 0.4)


# ---------- 字幕 ----------
def chunks(text):
    parts = [p for p in re.split(r"(?<=[，。：；？！])", text) if p.strip()]
    out = []
    for p in parts:
        p = p.strip().rstrip("，。：；")
        if out and len(out[-1]) + len(p) <= 16 and len(p) <= 6:
            out[-1] += "，" + p
        else:
            out.append(p)
    return out


SUBS = []
for l in T["lines"]:
    cs = chunks(l["text"])
    total = sum(len(c) for c in cs)
    t = l["start"]
    for c in cs:
        d = (l["end"] - l["start"]) * len(c) / total
        SUBS.append((t, t + d, c))
        t += d
for k, (a, b, _) in enumerate(SUBS):
    A.append(f'tl.set("#sub{k}", {{ opacity: 1 }}, {r(a)}); tl.set("#sub{k}", {{ opacity: 0 }}, {r(b)});')
SUB_HTML = "".join(f'<div class="sub" id="sub{k}">{txt}</div>' for k, (_, _, txt) in enumerate(SUBS))

CSS = (HERE / "style.css").read_text(encoding="utf-8")
html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<title>RSI 第 2 集：会自己出题、自己对答案的 AI</title>
<script src="assets/gsap.min.js"></script>
<style>
{CSS}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1920" data-height="1080">
  <audio id="vo" src="assets/narration.wav" data-start="0" data-duration="{DUR}" data-volume="1"></audio>
  <div id="bg" class="clip" data-start="0" data-duration="{DUR}" data-track-index="0"><div class="glow g1"></div><div class="glow g2"></div><div class="gridbg"></div></div>
  {"".join(SC)}
  <div id="chrome" class="clip" data-start="0" data-duration="{DUR}" data-track-index="2"><div class="series">RSI 递归自我改进 · 第 2 集</div></div>
  <div id="subs" class="clip" data-start="0" data-duration="{DUR}" data-track-index="3">{SUB_HTML}</div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
const counter = (sel, fmt) => {{ const el = document.querySelector(sel); return {{ _v: 0, get v() {{ return this._v; }}, set v(x) {{ this._v = x; el.textContent = fmt(x); }} }}; }};
const AIME = counter("#ai-v", (x) => x.toFixed(1));
{chr(10).join(A)}
tl.set({{}}, {{}}, {DUR});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
tl.seek(0);
const q = new URLSearchParams(location.search);
if (q.has("t")) tl.seek(parseFloat(q.get("t")), false);
</script>
</body>
</html>
"""
(HERE / "index.html").write_text(html, encoding="utf-8")
print(f"写出 index.html：{len(SC)} 幕，{len(SUBS)} 条字幕，时长 {DUR} 秒")
