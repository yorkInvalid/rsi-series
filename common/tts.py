"""
配音：腾讯 TokenHub 上的 MiniMax-Speech-2.8-HD，按字符计费（官网价 3.5 元 / 万字符；一个汉字算 2 个字符）。
密钥读 .env 里的 TOKENHUB_API_KEY。视频用的音色是「电台男主播」：Chinese (Mandarin)_Radio_Host。

合成过的句子按（模型、音色、语速、文字）缓存，同一句不会重复花钱。
"""

import hashlib
import json
from pathlib import Path

import httpx

from common import env

MODEL = "minimax-speech-2.8-hd"
BASE_URL = env.get("TOKENHUB_BASE_URL", "https://tokenhub.tencentmaas.com").rstrip("/")
_legacy = env.ROOT.parent / "llm-sourcing-study" / "results" / "tts_cache"  # 作者本机已有的缓存，接着用，不重复花钱
CACHE = _legacy if _legacy.exists() else env.ROOT / ".tts_cache"


def synthesize(text, voice_id, speed=1.0, model=MODEL):
    """返回 (mp3 音频, 附加信息)。"""
    key = hashlib.sha1(json.dumps([model, voice_id, speed, text], ensure_ascii=False).encode("utf-8")).hexdigest()
    audio_file, info_file = CACHE / f"{key}.mp3", CACHE / f"{key}.json"
    if audio_file.exists() and info_file.exists():
        return audio_file.read_bytes(), {**json.loads(info_file.read_text(encoding="utf-8")), "cached": True}

    r = httpx.Client(timeout=120, trust_env=False).post(
        f"{BASE_URL}/v1/wand/minimax-tts/sync_tts",
        headers={"Authorization": f"Bearer {env.require('TOKENHUB_API_KEY')}"},
        json={
            "model": model,
            "text": text,
            "voice_setting": {"voice_id": voice_id, "speed": speed, "vol": 1, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
            "output_format": "hex",
        },
    )
    body = r.json() if "json" in r.headers.get("content-type", "") else {}
    status = (body.get("base_resp") or {}).get("status_code")
    if r.status_code != 200 or status != 0 or not (body.get("data") or {}).get("audio"):
        raise RuntimeError(f"语音合成失败：HTTP {r.status_code} {r.text[:300]}")
    audio = bytes.fromhex(body["data"]["audio"])
    info = {**body.get("extra_info", {}), "usage": body.get("usage"), "cached": False}
    CACHE.mkdir(parents=True, exist_ok=True)
    audio_file.write_bytes(audio)
    info_file.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    return audio, info
