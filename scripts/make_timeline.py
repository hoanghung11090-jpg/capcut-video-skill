"""Tính mốc thời gian từng câu từ file giọng đọc, ghép phụ đề cụm 2-5 chữ theo mốc từng từ.
Ghi <root>/_ghi_chu/timeline.json và phu_de.srt.

python make_timeline.py <root> [--gap 0.4] [--tail 1.5]
Cần: giong_doc/NN.mp3, _ghi_chu/moc_tu.json (từ tts.py), _ghi_chu/04_phu_de_cum.txt
(mỗi dòng là một câu kịch bản, dùng " / " đánh chỗ ngắt cụm).
"""
import argparse, json, pathlib, re, subprocess
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ap = argparse.ArgumentParser()
ap.add_argument("root", type=pathlib.Path)
ap.add_argument("--gap", type=float, default=0.4, help="khoảng nghỉ giữa hai câu (giây)")
ap.add_argument("--tail", type=float, default=1.5, help="đuôi sau câu cuối (giây)")
a = ap.parse_args()
notes = a.root / "_ghi_chu"

def duration(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)

def align(text, words):
    """Gắn (start, end) cho từng token của câu; một mốc của TTS có thể gồm nhiều token."""
    toks, times = text.split(), []
    for w in words:
        n = len(w["text"].split()); step = (w["end"] - w["start"]) / n
        times += [(w["start"] + j * step, w["start"] + (j + 1) * step) for j in range(n)]
    if len(times) != len(toks):
        raise SystemExit(f"lệch số từ: {text!r} ({len(toks)} token / {len(times)} mốc)")
    return list(zip(toks, times))

def chunks(marked, words):
    parts = [p.split() for p in marked.split("/")]
    toks = align(" ".join(t for p in parts for t in p), words)
    out, k = [], 0
    for p in parts:
        c = toks[k:k + len(p)]; k += len(p)
        out.append({"text": " ".join(t for t, _ in c).rstrip(",.;:"), "start": c[0][1][0]})
    return out

timeline, t = [], 0.0
for v in sorted((a.root / "giong_doc").glob("[0-9][0-9].mp3")):
    d = duration(v); timeline.append({"file": v.name, "start": round(t, 3), "dur": round(d, 3)}); t += d + a.gap
total = t - a.gap + a.tail

moc = json.loads((notes / "moc_tu.json").read_text(encoding="utf-8"))
marked = [l.strip() for l in (notes / "04_phu_de_cum.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
if len(marked) != len(timeline):
    raise SystemExit(f"04_phu_de_cum.txt có {len(marked)} dòng, giọng đọc có {len(timeline)} file")
subs = []
for i, e in enumerate(timeline):
    m = moc[f"{i + 1:02d}"]
    if re.sub(r"\s*/\s*", " ", marked[i]) != m["text"]:
        raise SystemExit(f"câu {i + 1} trong 04_phu_de_cum.txt khác kịch bản")
    for c in chunks(marked[i], m["words"]):
        subs.append({"text": c["text"], "start": round(e["start"] + c["start"], 3)})
clip_ends = [e["start"] for e in timeline[1:]] + [total]
for j, s in enumerate(subs):
    nxt = subs[j + 1]["start"] if j + 1 < len(subs) else total
    s["end"] = round(min(nxt, next(ce for ce in clip_ends if ce > s["start"])), 3)
bad = [s["text"] for s in subs if not 2 <= len(s["text"].split()) <= 5]
if bad:
    print("CẢNH BÁO cụm ngoài 2-5 chữ:", bad)

def ts(x):
    ms = int(round(x * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
(notes / "phu_de.srt").write_text("\n".join(f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n"
                                            for i, s in enumerate(subs, 1)), encoding="utf-8")
(notes / "timeline.json").write_text(json.dumps({"total": round(total, 3), "gap": a.gap, "clips": timeline, "subs": subs},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(timeline)} câu, {len(subs)} cụm phụ đề, tổng {total:.1f} s")
