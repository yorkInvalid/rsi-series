"""
按 timing.json（配音时间轴）和 ../results 里的实验数据，生成第 1 集的 index.html（HyperFrames 合成）。

改了文案就先跑 make_voice.py，再跑这个；画面会自动跟着新的时间轴走。
  python3 build.py
"""

import json
import math
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
T = json.loads((HERE / "timing.json").read_text(encoding="utf-8"))
L = {l["id"]: l for l in T["lines"]}
DUR = T["duration"]
CURVE = json.loads((RES / "curve.json").read_text(encoding="utf-8"))["average"]
GAMES = json.loads((RES / "games.json").read_text(encoding="utf-8"))
META = json.loads((RES / "learn_to_learn.json").read_text(encoding="utf-8"))

s = lambda i: L[i]["start"]
e = lambda i: L[i]["end"]
ss = lambda i: L[i]["scene_start"]
se = lambda i: L[i]["scene_end"]
r = lambda x: round(x, 3)

A = []  # 时间轴上的动画，一行一句 JS


def fade_in(sel, t, dur=0.4, y=24, scale=None):
    frm = f"opacity: 0, y: {y}" + (f", scale: {scale}" if scale else "")
    to = "opacity: 1, y: 0" + (", scale: 1" if scale else "")
    A.append(f'tl.fromTo("{sel}", {{ {frm} }}, {{ {to}, duration: {dur}, ease: "power3.out" }}, {r(t)});')


def pop(sel, t):
    A.append(f'tl.fromTo("{sel}", {{ opacity: 0, scale: 1.5 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.2)" }}, {r(t)});')


def show(sel, t, dur=0.25):
    A.append(f'tl.fromTo("{sel}", {{ opacity: 0 }}, {{ opacity: 1, duration: {dur} }}, {r(t)});')


def hide(sel, t, dur=0.25):
    A.append(f'tl.to("{sel}", {{ opacity: 0, duration: {dur} }}, {r(t)});')


# ---------- 井字棋棋盘 ----------
LINES3 = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def win_line(moves):
    b = ["."] * 9
    for k, i in enumerate(moves):
        b[i] = "X" if k % 2 == 0 else "O"
    for ln in LINES3:
        if b[ln[0]] != "." and b[ln[0]] == b[ln[1]] == b[ln[2]]:
            return ln
    return None


def board(bid, moves, size=420, colors=("#7FA8FF", "#F2A65A")):
    c = size / 3
    g = [f'<svg class="board" id="{bid}" width="{size}" height="{size}" viewBox="0 0 {size} {size}">']
    for k in (1, 2):
        g.append(f'<line x1="{k * c}" y1="8" x2="{k * c}" y2="{size - 8}" class="grid"/>')
        g.append(f'<line x1="8" y1="{k * c}" x2="{size - 8}" y2="{k * c}" class="grid"/>')
    for k, i in enumerate(moves):
        cx, cy = (i % 3 + 0.5) * c, (i // 3 + 0.5) * c
        rr = c * 0.28
        col = colors[k % 2]
        if k % 2 == 0:
            g.append(f'<g id="{bid}-m{k}" class="mark"><line x1="{cx - rr}" y1="{cy - rr}" x2="{cx + rr}" y2="{cy + rr}" stroke="{col}"/>'
                     f'<line x1="{cx + rr}" y1="{cy - rr}" x2="{cx - rr}" y2="{cy + rr}" stroke="{col}"/></g>')
        else:
            g.append(f'<g id="{bid}-m{k}" class="mark"><circle cx="{cx}" cy="{cy}" r="{rr}" stroke="{col}"/></g>')
        g.append(f'<text id="{bid}-t{k}" class="tag" x="{cx + c * 0.3}" y="{cy - c * 0.22}"></text>')
    ln = win_line(moves)
    if ln:
        (x1, y1), (x2, y2) = [((i % 3 + 0.5) * c, (i // 3 + 0.5) * c) for i in (ln[0], ln[2])]
        g.append(f'<line id="{bid}-win" class="winline" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    g.append("</svg>")
    return "".join(g)


def play_moves(bid, moves, t0, step):
    for k in range(len(moves)):
        pop(f"#{bid}-m{k}", t0 + k * step)
    if win_line(moves):
        show(f"#{bid}-win", t0 + len(moves) * step, 0.3)
    return t0 + len(moves) * step


# ---------- 曲线 ----------
CW, CH = 1100, 470
LOGMAX = math.log10(50000)


def cx(g):
    return math.log10(max(g, 1)) / LOGMAX * CW


def cy(p):
    return CH - p * CH


def chart(cid, highlight_tail=False):
    pts = " ".join(f"{cx(r_['games']):.1f},{cy(r_['vs_perfect_loss']):.1f}" for r_ in CURVE)
    ticks = [(0, "0"), (10, "10"), (100, "100"), (1000, "1千"), (10000, "1万"), (50000, "5万")]
    out = [f'<div class="chart" id="{cid}"><svg class="axes" width="{CW + 140}" height="{CH + 120}" viewBox="-90 -20 {CW + 140} {CH + 120}">']
    for p in (0, 0.5, 1):
        out.append(f'<line x1="0" y1="{cy(p)}" x2="{CW}" y2="{cy(p)}" class="gl"/><text x="-18" y="{cy(p) + 10}" class="yl">{int(p * 100)}%</text>')
    for g, lab in ticks:
        out.append(f'<text x="{cx(g)}" y="{CH + 52}" class="xl">{lab}</text>')
    out.append(f'<text x="{CW / 2}" y="{CH + 88}" class="xt">自己跟自己下了多少盘</text></svg>')
    out.append(f'<div class="reveal" id="{cid}-rv"><svg width="{CW + 140}" height="{CH + 90}" viewBox="-90 -20 {CW + 140} {CH + 90}">'
               f'<polyline points="{pts}" class="loss"/></svg></div>')
    if highlight_tail:
        out.append(f'<div class="tailmark" id="{cid}-tail" style="left:{90 + cx(15000) - 40}px; top:{20 + CH - 70}px; width:{cx(50000) - cx(15000) + 80}px"></div>')
    out.append("</div>")
    return "".join(out)


def at(g):
    return min(CURVE, key=lambda r_: abs(r_["games"] - g))


# ---------- 字幕：按标点切成短句，按字数分时间 ----------
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

# ---------- 每一幕 ----------
SC = []


def scene(sid, a, b, inner):
    SC.append(f'<section id="{sid}" class="clip scene" data-start="{r(ss(a))}" data-duration="{r(se(b) - ss(a))}" data-track-index="1">{inner}</section>')


# 1 新闻钩子
scene("s-hook", "h1", "h3", """
<div class="kicker" id="hk-date">2026 年 9 月</div>
<div class="hk-title" id="hk-title">三家头部 AI 公司的老板，罕见地站到了一起</div>
<div class="quote big" id="hk-q1"><div class="who">Dario Amodei · Anthropic CEO</div>
<div class="what">《We Must Pace the Frontier》</div>
<div class="say">“从今年夏天开始，AI 进步得快多了，主要因为 AI 越来越会造下一代 AI。”</div><div class="note">原文翻译</div></div>
<div class="quotes2"><div class="quote" id="hk-q2"><div class="who">Sam Altman · OpenAI CEO</div><div class="say en">“I agree with Dario that we need to pace the frontier.”</div></div>
<div class="quote" id="hk-q3"><div class="who">Elon Musk · xAI</div><div class="say en">“Dario is right.”</div></div></div>
<div class="stamp" id="hk-slow">慢一点</div>
<div class="src">来源：darioamodei.com；Altman、Musk 的回应据 CoinDesk 报道</div>
""")
fade_in("#hk-date", ss("h1") + 0.2)
fade_in("#hk-title", s("h1") + 0.4)
hide("#hk-title", s("h2") - 0.1)
fade_in("#hk-q1", s("h2"), 0.5)
A.append(f'tl.to("#hk-q1", {{ y: -150, scale: 0.86, duration: 0.5, ease: "power2.inOut" }}, {r(s("h3"))});')
fade_in("#hk-q2", s("h3") + 0.1)
fade_in("#hk-q3", s("h3") + 1.4)
pop("#hk-slow", e("h3") - 1.2)

# 2 RSI
scene("s-rsi", "h4", "h4", """
<div class="rsi"><span id="rs-r">R</span><span id="rs-s">S</span><span id="rs-i">I</span></div>
<div class="rsi-en" id="rs-en">Recursive Self-Improvement</div>
<div class="rsi-cn" id="rs-cn">递归自我改进</div>
""")
for k, x in enumerate(("r", "s", "i")):
    pop(f"#rs-{x}", s("h4") + 0.9 + k * 0.18)
fade_in("#rs-en", s("h4") + 1.6)
fade_in("#rs-cn", s("h4") + 2.2)

# 3 拆成两半
scene("s-def", "d1", "d3", """
<div class="halves">
<div class="half" id="df-1"><div class="num">前半句</div><div class="hd">没人教，自己让自己变强</div>
<svg width="360" height="200" viewBox="0 0 360 200"><path d="M20 180 H100 V140 H180 V100 H260 V60 H340" class="stairs"/></svg></div>
<div class="half" id="df-2"><div class="num">后半句</div><div class="hd">越强，越会让自己变强</div>
<svg width="360" height="200" viewBox="0 0 360 200"><path d="M20 185 C 160 182, 250 160, 300 100 S 335 20, 345 10" class="snow"/></svg></div>
</div>
<div class="badge" id="df-b">前半句：我的电脑上 <b>3.5 秒</b></div>
""")
fade_in("#df-1", s("d1") + 0.8)
fade_in("#df-2", s("d2") + 0.2)
A.append(f'tl.to("#df-2", {{ opacity: 0.25, duration: 0.4 }}, {r(s("d3"))});')
A.append(f'tl.to("#df-1", {{ scale: 1.06, duration: 0.4 }}, {r(s("d3"))});')
pop("#df-b", s("d3") + 1.6)

# 4 第一盘：乱下，然后倒着回想
first = GAMES["first_selfplay_game"]["moves"]
scene("s-board", "a1", "a4", f"""
<div class="stage-l">{board("bd1", first, 480)}</div>
<div class="stage-r">
<div class="chip" id="bd-rule">只知道规则：先连成三个就赢</div>
<div class="chip dim" id="bd-self">自己 vs 自己 · 第 1 盘</div>
<div class="chip" id="bd-back">下完一盘，倒着回想</div>
<div class="legend" id="bd-leg"><span class="plus">+</span> 赢了，下次多走　<span class="minus">−</span> 输了，下次少走</div>
<div class="callout" id="bd-pan">摸过一次烫锅，就记住了</div>
</div>
""")
fade_in("#bd1", ss("a1") + 0.2)
fade_in("#bd-rule", s("a1") + 1.5)
fade_in("#bd-self", s("a2") + 0.1)
t_end = play_moves("bd1", first, s("a2") + 0.9, 0.42)
fade_in("#bd-back", s("a3"))
fade_in("#bd-leg", s("a3") + 1.6)
winner_first = "X" if len(first) % 2 == 1 else "O"
for j, k in enumerate(reversed(range(len(first)))):
    tag = "+" if (k % 2 == 0) == (winner_first == "X") else "−"
    A.append(f'document.getElementById("bd1-t{k}").textContent = "{tag}";')
    A.append(f'document.getElementById("bd1-t{k}").setAttribute("class", "tag {"plus" if tag == "+" else "minus"}");')
    pop(f"#bd1-t{k}", s("a3") + 2.2 + j * 0.45)
pop("#bd-pan", s("a4") + 0.1)

# 5 两个考官
scene("s-exam", "a5", "a5", """
<div class="examiners">
<div class="ex" id="ex-a"><div class="ex-k">考官 A</div><div class="ex-n">随机乱下</div>
<svg width="160" height="160" viewBox="0 0 160 160"><rect x="20" y="20" width="120" height="120" rx="22" class="die"/>
<circle cx="52" cy="52" r="10"/><circle cx="108" cy="52" r="10"/><circle cx="80" cy="80" r="10"/><circle cx="52" cy="108" r="10"/><circle cx="108" cy="108" r="10"/></svg></div>
<div class="ex" id="ex-b"><div class="ex-k">考官 B</div><div class="ex-n">永远不犯错</div>
<div class="ex-big">5478</div><div class="ex-s">井字棋全部局面，全部算透</div></div>
</div>
""")
fade_in("#ex-a", s("a5") + 1.0)
fade_in("#ex-b", s("a5") + 2.6)

# 6 曲线一路往下
c0, c1, c2, c3 = at(0), at(1000), at(5000), at(40000)
scene("s-curve", "c1", "c5", f"""
<div class="ctitle">对「永不犯错」的考官：<span class="red">输的比例</span></div>
{chart("ch1")}
<div class="readout"><div class="ro-k">输棋率</div><div class="ro-v" id="ro-loss">87%</div>
<div class="ro-k">已下</div><div class="ro-g"><span id="ro-games">0</span> 盘</div></div>
<div class="badge right" id="cv-b"><b>50,000</b> 盘 · 只用 <b>3.5</b> 秒</div>
""")
fade_in("#ch1", ss("c1") + 0.1)
fade_in(".readout", ss("c1") + 0.2)
A.append(f'tl.set("#ch1-rv", {{ width: 0 }}, 0);')
steps = [("c1", 0, c0), ("c2", 1000, c1), ("c3", 5000, c2), ("c4", 40000, c3), ("c5", 50000, at(50000))]
prev = 0
for lid, g, row in steps:
    t = s(lid) + (1.6 if lid == "c3" else 0.3)
    A.append(f'tl.to("#ch1-rv", {{ width: {r(90 + cx(g) + 12)}, duration: 0.9, ease: "power2.inOut" }}, {r(t)});')
    A.append(f'tl.fromTo(G, {{ v: {prev} }}, {{ v: {g}, duration: 0.9, ease: "power2.inOut" }}, {r(t)});')
    A.append(f'tl.set(LOSS, {{ v: {round(row["vs_perfect_loss"] * 100)} }}, {r(t + 0.6)});')
    A.append(f'tl.fromTo("#ro-loss", {{ scale: 1.25 }}, {{ scale: 1, duration: 0.35, ease: "back.out(2)" }}, {r(t + 0.6)});')
    prev = g
pop("#cv-b", s("c5") + 3.0)

# 7 同样执先手：第 0 盘 vs 第 5 万盘
g0 = GAMES["vs_perfect_at"]["0"]["X"]["moves"]
g5 = GAMES["vs_perfect_at"]["50000"]["X"]["moves"]
scene("s-replay", "r1", "r2", f"""
<div class="pair">
<div class="col"><div class="col-h">第 0 盘</div>{board("bd0", g0, 400, ("#7FA8FF", "#8A93A6"))}<div class="res lose" id="rp-lose">6 步就输了</div></div>
<div class="col"><div class="col-h">第 50,000 盘</div>{board("bd5", g5, 400, ("#7FA8FF", "#8A93A6"))}<div class="res draw" id="rp-draw">下满 9 格 · 和棋 = 满分</div></div>
</div>
<div class="pair-note">蓝色是它（先手），灰色是永不犯错的考官</div>
""")
fade_in(".pair", ss("r1") + 0.1)
show(".pair-note", ss("r1") + 0.4)
t = play_moves("bd0", g0, s("r1") + 0.4, 0.3)
pop("#rp-lose", t + 0.2)
t = play_moves("bd5", g5, s("r2") + 0.2, 0.32)
pop("#rp-draw", t + 0.1)

# 8 线平了
scene("s-flat", "f1", "f2", f"""
<div class="ctitle">前半句做到了：<span class="red">自己让自己变强</span></div>
{chart("ch2", highlight_tail=True)}
<div class="flatlabel" id="fl-l">到顶了</div>
<div class="checks" id="fl-c"><div class="ok">✓ 会把棋下好</div><div class="no">✗ 不会改进「学棋的方法」</div></div>
""")
fade_in("#ch2", ss("f1") + 0.1)
show("#ch2-tail", s("f1") + 3.2, 0.3)
pop("#fl-l", s("f1") + 3.4)
A.append(f'tl.to("#ch2", {{ opacity: 0.35, duration: 0.4 }}, {r(s("f2"))});')
fade_in("#fl-c", s("f2") + 0.2)

# 9 再加一层：改进学法
V = META["validation"]
G1 = META["history"][0]["best"]
best_g = min(V[1:], key=lambda v: v["mean"])
vmax = max(v["mean"] for v in V)
bars = []
for v in V:
    h = 380 * v["mean"] / vmax
    cls = "bar base" if v["generation"] == 0 else ("bar best" if v is best_g else "bar")
    label = "原始学法" if v["generation"] == 0 else f"第 {v['generation']} 代"
    bars.append(f'<div class="bcol"><div class="bval" id="bv{v["generation"]}">{v["mean"]:,}</div>'
                f'<div class="{cls}" id="bb{v["generation"]}" style="height:{h:.0f}px"></div><div class="blab">{label}</div></div>')
KNOBS = [  # 名字、起点、第 1 代调到哪（滑块位置 0-100）
    ("学得多快", 30, 30 * G1["alpha"] / META["base"]["alpha"]),
    ("多爱瞎试", 60, 60 * G1["eps0"] / META["base"]["eps0"]),
    ("什么时候收心", 50, 50 * G1["decay"] / META["base"]["decay"]),
    ("没见过的局面：往坏处想 ↔ 往好处想", 100 * META["base"]["init"], 100 * G1["init"]),
]
knobs = "".join(f'<div class="knob"><div class="kn">{n}</div><div class="slider"><i id="kn{k}" style="left:{a0:.0f}%"></i></div></div>' for k, (n, a0, _) in enumerate(KNOBS))
scene("s-meta", "b1", "b7", f"""
<div class="knobs" id="mk">{knobs}</div>
<div class="loop" id="ml"><span>8 种调法</span><b>→</b><span>各自从零学一遍</span><b>→</b><span>留下学得最快的</span><b>→</b><span>传给下一代接着改</span></div>
<div class="bars" id="mb">{"".join(bars)}<div class="bunit">平均要下多少盘才学会（30 次重复，连续两次考试一盘不输）</div></div>
<div class="trick" id="mt"><div class="tk">第 1 代找到的诀窍</div><div class="tv">少瞎试</div><div class="tv">对没见过的局面，先往好处想</div></div>
<div class="big2" id="mr">学棋，也学得更快了</div>
<div class="sub2" id="mr2">改进「自己变强的方法」＝ 递归</div>
<div class="flat2" id="mp">又改不动了</div>
<div class="footnote" id="mf">注：只有 4 个旋钮可拧；挑学法的是我写的外层程序，不是它自己想出来的。</div>
""")
fade_in("#mk", s("b1") + 2.0)
for k in range(len(KNOBS)):
    A.append(f'tl.fromTo("#kn{k}", {{ scale: 1 }}, {{ scale: 1.5, duration: 0.25, yoyo: true, repeat: 1 }}, {r(s("b1") + 3.6 + k * 1.6)});')
fade_in("#ml", s("b2") + 0.2)
for k, (_, a0, a1) in enumerate(KNOBS):
    dx = (min(96, max(4, a1)) - a0) / 100 * 708  # 滑轨宽 708px，用位移代替改 left
    A.append(f'tl.fromTo("#kn{k}", {{ x: 0 }}, {{ x: {dx:.1f}, duration: 0.5, ease: "power2.inOut", yoyo: true, repeat: 3 }}, {r(s("b2") + 2.0)});')
A.append(f'tl.to(["#mk", "#ml"], {{ opacity: 0, duration: 0.3 }}, {r(s("b3") - 0.2)});')
fade_in("#mb", s("b3") - 0.1)
A.append(f'tl.set(".bar", {{ scaleY: 0 }}, 0);')
def grow(g, t):
    A.append(f'tl.fromTo("#bb{g}", {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.45, ease: "power3.out" }}, {r(t)});')
    show(f"#bv{g}", t + 0.3)
grow(0, s("b3") + 0.6)
grow(1, s("b4") + 0.5)
A.append(f'tl.to("#mb", {{ opacity: 0.18, duration: 0.3 }}, {r(s("b5"))});')
fade_in("#mt", s("b5") + 0.1)
A.append(f'tl.to("#mt", {{ opacity: 0, duration: 0.3 }}, {r(s("b6") - 0.1)});')
pop("#mr", s("b6") + 0.1)
fade_in("#mr2", s("b6") + 3.6)
A.append(f'tl.to(["#mr", "#mr2"], {{ opacity: 0, duration: 0.3 }}, {r(s("b7") - 0.1)});')
A.append(f'tl.to("#mb", {{ opacity: 1, duration: 0.3 }}, {r(s("b7") - 0.1)});')
for k, v in enumerate(V[2:]):
    grow(v["generation"], s("b7") + 0.4 + k * 0.35)
pop("#mp", s("b7") + 2.4)
fade_in("#mf", s("b7") + 4.6)

# 10 AlphaGo Zero
rng = random.Random(3)
stones = []
for k in range(46):
    x, y = rng.randrange(19), rng.randrange(19)
    stones.append(f'<circle cx="{20 + x * 24}" cy="{20 + y * 24}" r="10.5" class="{"bk" if k % 2 == 0 else "wt"}" id="st{k}"/>')
grid = "".join(f'<line x1="20" y1="{20 + k * 24}" x2="452" y2="{20 + k * 24}"/><line x1="{20 + k * 24}" y1="20" x2="{20 + k * 24}" y2="452"/>' for k in range(19))
scene("s-go", "g1", "g2", f"""
<div class="gowrap"><svg class="go" width="472" height="472" viewBox="0 0 472 472"><rect width="472" height="472" rx="14" class="wood"/><g class="glines">{grid}</g>{"".join(stones)}</svg></div>
<div class="gotext">
<div class="kicker">2017 · DeepMind</div>
<div class="goname">AlphaGo Zero</div>
<div class="gofact" id="go1">看过的人类棋谱：<b>0</b> 张</div>
<div class="gofact" id="go2">自己跟自己下：<b>3 天</b> · 约 <b>490 万</b>盘</div>
<div class="score" id="go3">100 <span>:</span> 0</div>
<div class="gofact small" id="go4">对手：当年打败李世石的那一版 AlphaGo</div>
</div>
<div class="src">来源：DeepMind 2017 年 Nature 论文与官方博客；盘数据 Science News 报道</div>
""")
fade_in(".gowrap", ss("g1") + 0.1)
for k in range(46):
    show(f"#st{k}", s("g1") + 3.5 + k * 0.09, 0.1)
fade_in("#go1", s("g1") + 4.0)
fade_in("#go2", s("g1") + 6.4)
pop("#go3", s("g2") + 2.0)
fade_in("#go4", s("g2") + 3.2)

# 11 大公司
scene("s-ind", "i1", "i1", """
<div class="bignum" id="in-n">75%<sup>+</sup></div>
<div class="bigcap" id="in-c">谷歌 DeepMind 的生产代码，由 AI 编写</div>
<div class="src">据 Digital Today 2026 年 10 月报道，引自 DeepMind 安全报告</div>
""")
pop("#in-n", s("i1") + 3.8)
fade_in("#in-c", s("i1") + 4.4)

# 12 争论
scene("s-debate", "x1", "x2", """
<div class="vs">
<div class="side" id="db-a"><div class="sv">已经开始加速</div><div class="sw">— Anthropic CEO，2026 年 9 月</div></div>
<div class="q" id="db-q">?</div>
<div class="side" id="db-b"><div class="sv">没看到加速</div><div class="sw">— 谷歌 DeepMind 报告，2026 年 10 月</div></div>
</div>
<div class="sub2" id="db-s">雪球到底滚起来了没有？这个系列，一集一集用实验讲清楚</div>
""")
fade_in("#db-a", s("x1") + 0.2)
fade_in("#db-b", s("x1") + 2.8)
pop("#db-q", s("x2") + 0.3)
fade_in("#db-s", s("x2") + 2.4)

# 13 下一集
scene("s-next", "n1", "n2", """
<div class="kicker">下一集</div>
<div class="nx1" id="nx1">井字棋有输赢当裁判</div>
<div class="nx2" id="nx2">写作文、写代码，谁来当裁判？</div>
<div class="nx3" id="nx3">会自己出题、自己对答案的 AI</div>
<div class="follow" id="nx4">关注我 · 下一集见</div>
""")
fade_in("#nx1", s("n1") + 0.3)
fade_in("#nx2", s("n1") + 2.4)
pop("#nx3", s("n1") + 5.0)
pop("#nx4", s("n2") + 0.1)

for k, (a, b, txt) in enumerate(SUBS):
    A.append(f'tl.set("#sub{k}", {{ opacity: 1 }}, {r(a)}); tl.set("#sub{k}", {{ opacity: 0 }}, {r(b)});')
SUB_HTML = "".join(f'<div class="sub" id="sub{k}">{txt}</div>' for k, (_, _, txt) in enumerate(SUBS))

CSS = (HERE / "style.css").read_text(encoding="utf-8")
html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<title>RSI 第 1 集：没人教，它自己变强了</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
{CSS}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1920" data-height="1080">
  <audio id="vo" src="assets/narration.wav" data-start="0" data-duration="{DUR}" data-volume="1"></audio>
  <div id="bg" class="clip" data-start="0" data-duration="{DUR}" data-track-index="0"><div class="glow g1"></div><div class="glow g2"></div><div class="gridbg"></div></div>
  {"".join(SC)}
  <div id="chrome" class="clip" data-start="{r(ss('h4'))}" data-duration="{r(DUR - ss('h4'))}" data-track-index="2"><div class="series">RSI 递归自我改进 · 第 1 集</div></div>
  <div id="subs" class="clip" data-start="0" data-duration="{DUR}" data-track-index="3">{SUB_HTML}</div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
const counter = (sel, fmt) => {{ const el = document.querySelector(sel); return {{ _v: 0, get v() {{ return this._v; }}, set v(x) {{ this._v = x; el.textContent = fmt(x); }} }}; }};
const G = counter("#ro-games", (x) => Math.round(x).toLocaleString("en-US"));
const LOSS = counter("#ro-loss", (x) => Math.round(x) + "%");
document.querySelectorAll(".scene, #chrome").forEach((el) => {{
  const a = parseFloat(el.dataset.start), b = a + parseFloat(el.dataset.duration);
  if (a > 0.01) {{ tl.set(el, {{ autoAlpha: 0 }}, 0); tl.set(el, {{ autoAlpha: 1 }}, a); }}
  tl.set(el, {{ autoAlpha: 0 }}, b);
}});
tl.set(LOSS, {{ v: 87 }}, 0);
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
