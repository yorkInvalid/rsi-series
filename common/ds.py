"""
RSI 系列所有实验共用的 DeepSeek 调用：带预算上限、闲时检查、余额检查。

用法（在实验脚本的 main 开头）：
    from common import ds
    ds.start(budget=2.0, allow_peak=args.allow_peak, label="第 2 集正式实验")
    ...  # 正常调用 ds.ask(...)
    ds.report()

规则：
  - 高峰时段（北京时间工作日 9:00-12:00、14:00-18:00，单价翻倍）不让开跑；跑到一半进入高峰也会停下。
  - 开跑前查账户余额，不够本次预算就不跑。
  - 每次调用后按实际 token 记账（缓存命中的输入单独按便宜价算），花到预算上限就停。
价格来自 DeepSeek 官方价格页（2026-10-13 查）：DeepSeek-V4.1-Flash 闲时
输入未命中 1 元/百万、命中 0.02 元/百万、输出 4 元/百万，高峰全部翻倍。
"""

import datetime as dt
import sys
import threading
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import env  # noqa: E402

BASE_URL = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic").rstrip("/")
MODEL = env.get("DEEPSEEK_MODEL", "deepseek-flash")
API_KEY = env.require("DEEPSEEK_API_KEY")
CLIENT = httpx.Client(timeout=120, trust_env=False)
PRICE = {"miss": 1.0, "hit": 0.02, "out": 4.0}  # 闲时，元 / 百万 token
PEAK_FACTOR = 2
BJ = dt.timezone(dt.timedelta(hours=8))

STATE = {"budget": None, "allow_peak": False, "spent": 0.0, "miss": 0, "hit": 0, "out": 0, "calls": 0, "peak_calls": 0}
LOCK = threading.Lock()


class Stop(RuntimeError):
    """预算花完或者进入高峰，实验应当停下。"""


def now():
    return dt.datetime.now(BJ)


def is_peak(t=None):
    t = t or now()
    return t.weekday() < 5 and (9 <= t.hour < 12 or 14 <= t.hour < 18)


def next_offpeak(t=None):
    t = (t or now()).replace(second=0, microsecond=0)
    while is_peak(t):
        t += dt.timedelta(minutes=1)
    return t


def balance():
    """账户余额（元）。查不到就返回 None。"""
    try:
        r = CLIENT.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {API_KEY}"})
        infos = r.json().get("balance_infos", [])
        cny = next((x for x in infos if x.get("currency") == "CNY"), None)
        return float(cny["total_balance"]) if cny else None
    except Exception:
        return None


def start(budget, allow_peak=False, label=""):
    if is_peak() and not allow_peak:
        sys.exit(f"现在是 DeepSeek 高峰时段（{now():%H:%M}，单价翻倍），不开跑。下一个闲时从 {next_offpeak():%m-%d %H:%M} 开始。"
                 "确实要现在跑，加 --allow-peak。")
    bal = balance()
    print(f"{label or '实验'}：预算上限 {budget:.2f} 元；账户余额 {'查不到' if bal is None else f'{bal:.2f} 元'}；"
          f"{'高峰时段（单价翻倍）' if is_peak() else '闲时'}")
    if bal is not None and bal < budget:
        sys.exit(f"余额 {bal:.2f} 元不够本次预算 {budget:.2f} 元，先充值或调低 --budget。")
    STATE.update(budget=budget, allow_peak=allow_peak)


def spent():
    return STATE["spent"]


def _check():
    if STATE["budget"] is not None and STATE["spent"] >= STATE["budget"]:
        raise Stop(f"花费 {STATE['spent']:.2f} 元已到预算上限 {STATE['budget']:.2f} 元，停下。")
    if is_peak() and not STATE["allow_peak"]:
        raise Stop(f"{now():%H:%M} 进入高峰时段，停下，免得单价翻倍。")


def ask(user, system="", thinking=False, max_tokens=800, temperature=0.0):
    _check()
    body = {"model": MODEL, "max_tokens": max_tokens, "temperature": temperature,
            "messages": [{"role": "user", "content": user}],
            "thinking": {"type": "enabled" if thinking else "disabled"}}
    if system:
        body["system"] = system
    url = BASE_URL + ("/v1/messages" if not BASE_URL.endswith("/messages") else "")
    headers = {"x-api-key": API_KEY, "Authorization": f"Bearer {API_KEY}",
               "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for attempt in range(8):
        try:
            r = CLIENT.post(url, headers=headers, json=body)
        except httpx.HTTPError:
            time.sleep(min(60, 2 ** attempt))
            continue
        if r.status_code == 402:
            raise Stop("DeepSeek 返回 402：账户余额不足。")
        if r.status_code in (429, 500, 502, 503):
            time.sleep(min(60, 2 ** attempt))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        d = r.json()
        u = d.get("usage", {})
        hit = u.get("cache_read_input_tokens", 0) or 0
        miss = u.get("input_tokens", 0) or 0
        out = u.get("output_tokens", 0) or 0
        peak = is_peak()
        c = (miss * PRICE["miss"] + hit * PRICE["hit"] + out * PRICE["out"]) / 1e6 * (PEAK_FACTOR if peak else 1)
        with LOCK:
            STATE["spent"] += c
            STATE["miss"] += miss
            STATE["hit"] += hit
            STATE["out"] += out
            STATE["calls"] += 1
            STATE["peak_calls"] += peak
        text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
        think = "".join(b.get("thinking", "") for b in d["content"] if b.get("type") == "thinking")
        return {"text": text, "thinking": think, "in": miss + hit, "out": out}
    raise RuntimeError("重试 8 次都失败")


def cost(tokens_in, tokens_out):
    """兼容旧脚本：按闲时价粗算。真实花费看 spent()。"""
    return tokens_in / 1e6 * PRICE["miss"] + tokens_out / 1e6 * PRICE["out"]


def report():
    s = STATE
    print(f"本次花费约 {s['spent']:.3f} 元（{s['calls']} 次调用，其中高峰 {s['peak_calls']} 次；"
          f"输入 {s['miss'] + s['hit']:,} token，其中缓存命中 {s['hit']:,}；输出 {s['out']:,} token）")


def add_args(ap, budget=2.0):
    ap.add_argument("--budget", type=float, default=budget, help=f"本次最多花多少元，默认 {budget}")
    ap.add_argument("--allow-peak", action="store_true", help="允许在高峰时段跑（单价翻倍）")
    ap.add_argument("--pilot", action="store_true", help="迷你试跑：少量题、两轮，预算封顶 0.5 元，并推算正式跑的花费")


def run(fn, args, label, units_full, units_pilot):
    """跑一个实验：开跑前检查，预算或高峰触发就停，结束时报账；试跑时按工作量比例推算正式跑的花费。"""
    budget = min(args.budget, 0.5) if args.pilot else args.budget
    start(budget, args.allow_peak, label + ("（迷你试跑）" if args.pilot else ""))
    try:
        fn(args)
    except Stop as e:
        print(f"⚠ {e}")
    finally:
        report()
        if args.pilot and STATE["spent"] > 0:
            est = STATE["spent"] * units_full / units_pilot
            print(f"按这次试跑推算：正式跑（闲时）约 {est / (PEAK_FACTOR if STATE['peak_calls'] else 1):.1f} 元")
