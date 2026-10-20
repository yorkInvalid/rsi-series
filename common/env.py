"""
读配置：先看环境变量，再看仓库根目录的 .env（照 .env.example 填）。
作者本机还兼容 ../llm-sourcing-study/.env 的旧写法（A = DeepSeek，B = 腾讯 TokenHub），别人用不到。
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT.parent / "llm-sourcing-study" / ".env"
LEGACY_NAMES = {"DEEPSEEK_API_KEY": "A_API_KEY", "TOKENHUB_API_KEY": "B_API_KEY"}


def _parse(path):
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip("\"'")
    return values


_LOCAL = _parse(ROOT / ".env")
_LEGACY = _parse(LEGACY)


def get(name, default=None):
    value = os.environ.get(name) or _LOCAL.get(name)
    if not value and name in LEGACY_NAMES:
        value = _LEGACY.get(LEGACY_NAMES[name])
    return value or default


def require(name):
    value = get(name)
    if not value:
        raise SystemExit(f"缺少 {name}：把仓库根目录的 .env.example 复制成 .env，填上 {name}。")
    return value
