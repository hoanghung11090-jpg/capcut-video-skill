"""Đọc kịch bản bằng edge-tts (mỗi dòng một file), cắt khoảng lặng hai đầu theo mốc từ,
lưu mốc thời gian từng từ vào <root>/_ghi_chu/moc_tu.json.

python tts.py <root> [--voice vi-VN-NamMinhNeural] [--rate +4%] [--pitch -12Hz]
"""
import argparse, asyncio, pathlib, subprocess, json, edge_tts, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
LEAD, TAIL = 0.05, 0.15  # giây giữ lại trước từ đầu / sau từ cuối

ap = argparse.ArgumentParser()
ap.add_argument("root", type=pathlib.Path)
ap.add_argument("--voice", default="vi-VN-NamMinhNeural")
ap.add_argument("--rate", default="+4%")
ap.add_argument("--pitch", default="-12Hz")
a = ap.parse_args()

notes, out = a.root / "_ghi_chu", a.root / "giong_doc"
out.mkdir(parents=True, exist_ok=True)
lines = [l.strip() for l in (notes / "01_kich_ban.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

async def main():
    words_all = {}
    for i, text in enumerate(lines, 1):
        raw = out / f"_{i:02d}.mp3"
        for attempt in range(5):
            try:
                c = edge_tts.Communicate(text, a.voice, rate=a.rate, pitch=a.pitch, boundary="WordBoundary")
                words = []
                with open(raw, "wb") as f:
                    async for ch in c.stream():
                        if ch["type"] == "audio":
                            f.write(ch["data"])
                        elif ch["type"] == "WordBoundary":
                            words.append({"text": ch["text"], "start": ch["offset"] / 1e7,
                                          "end": (ch["offset"] + ch["duration"]) / 1e7})
                break
            except edge_tts.exceptions.NoAudioReceived:
                await asyncio.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"câu {i}: dịch vụ không trả âm thanh")
        cut = max(0.0, words[0]["start"] - LEAD)
        length = words[-1]["end"] + TAIL - cut
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{cut:.3f}", "-t", f"{length:.3f}", "-i", str(raw),
                        "-b:a", "192k", str(out / f"{i:02d}.mp3")], check=True)
        raw.unlink()
        for w in words:
            w["start"] = round(w["start"] - cut, 3); w["end"] = round(w["end"] - cut, 3)
        words_all[f"{i:02d}"] = {"text": text, "words": words}
        print(i, len(words), "words")
    (notes / "moc_tu.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=1), encoding="utf-8")

asyncio.run(main())
