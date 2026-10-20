"""
第 2 集配音：用 common/tts.py（腾讯 TokenHub 上的 MiniMax-Speech，电台男主播）逐句合成，排成时间轴。
每句可以单独设停顿（gap）。
合成过的句子有缓存，只改了一句就只花这一句的钱。

运行：
  python3 make_voice.py      # 需要 .env 里的 TOKENHUB_API_KEY
输出 assets/narration.wav 和 timing.json，然后跑 build.py。
"""

import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from common.tts import synthesize  # noqa: E402

LEAD_IN = 0.6
GAP = 0.35


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> None:
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    voice_dir = HERE / "voice"
    voice_dir.mkdir(exist_ok=True)

    lines, t, chars = [], LEAD_IN, 0
    for line in script["lines"]:
        mp3, info = synthesize(line["text"], script["voice"], speed=script["speed"])
        chars += 0 if info.get("cached") else len(line["text"])
        src, wav = voice_dir / f"{line['id']}.mp3", voice_dir / f"{line['id']}.wav"
        src.write_bytes(mp3)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "48000", "-ac", "2", str(wav)], check=True)
        d = duration(wav)
        lines.append({**line, "start": round(t, 3), "end": round(t + d, 3), "file": wav.name})
        t += d + line.get("gap", GAP)

    total = math.ceil((lines[-1]["end"] + script["tail"]) * 10) / 10
    for i, line in enumerate(lines):
        line["scene_start"] = 0.0 if i == 0 else line["start"]
        line["scene_end"] = lines[i + 1]["start"] if i + 1 < len(lines) else total

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for line in lines:
        cmd += ["-i", str(voice_dir / line["file"])]
    delays = "".join(f"[{i}:a]adelay={int(l['start'] * 1000)}:all=1[a{i}];" for i, l in enumerate(lines))
    mix = "".join(f"[a{i}]" for i in range(len(lines)))
    (HERE / "assets").mkdir(exist_ok=True)
    cmd += [
        "-filter_complex", f"{delays}{mix}amix=inputs={len(lines)}:normalize=0,apad,atrim=0:{total}[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(HERE / "assets" / "narration.wav"),
    ]
    subprocess.run(cmd, check=True)

    (HERE / "timing.json").write_text(json.dumps({"duration": total, "lines": lines}, ensure_ascii=False, indent=2), encoding="utf-8")
    for l in lines:
        print(f"{l['start']:7.2f} → {l['end']:7.2f}  {l['id']:4} {l['text']}")
    print(f"总时长 {total} 秒；这次新合成 {chars} 字（约 {chars * 2 * 3.5 / 10000:.2f} 元）")


if __name__ == "__main__":
    main()
