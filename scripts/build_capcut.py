"""Dựng timeline CapCut (đã kiểm chứng trên CapCut Pro 9.6 Windows) vào một draft CÓ SẴN, đã ĐÓNG.

python build_capcut.py <draft_dir> <root> [--birds 7-10,13-16] [--ref assets/ref_draft_content.json]

<root> cần: anh/NN.(jpg|png), giong_doc/NN.mp3, music/*.mp3, sfx/*.mp3,
_ghi_chu/timeline.json (make_timeline.py), _ghi_chu/03_prompt_anh_va_chuyen_dong.txt (dòng "NN | ... | ZOOM|PAN").
Ghi đè draft_content.json ở gốc draft và bản sao trong Timelines/<id>/; sao lưu trước vào _backup_<thời gian>.
"""
import argparse, json, copy, uuid, pathlib, shutil, subprocess, re, time
import imageio_ffmpeg

SKILL = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("draft", type=pathlib.Path)
ap.add_argument("root", type=pathlib.Path)
ap.add_argument("--ref", type=pathlib.Path, default=SKILL / "assets" / "ref_draft_content.json")
ap.add_argument("--birds", default="", help="khoảng câu có chim hót, vd 7-10,13-16")
ap.add_argument("--vol-music", type=float, default=0.12)
ap.add_argument("--vol-wind", type=float, default=0.22)
ap.add_argument("--vol-birds", type=float, default=0.18)
ap.add_argument("--zoom", default="1.0,1.25", help="scale đầu,cuối cho cảnh ZOOM")
ap.add_argument("--pan", default="1.3,0.26", help="scale, biên độ x cho cảnh PAN")
ap.add_argument("--sub-size", type=float, default=9.0)
ap.add_argument("--sub-y", type=float, default=-0.82)
a = ap.parse_args()

DRAFT, ASSET = a.draft, a.root
FF = imageio_ffmpeg.get_ffmpeg_exe()
US = 1_000_000

if (DRAFT / ".locked").exists():
    raise SystemExit("Project đang mở trong CapCut (.locked). Nhờ người dùng đóng project rồi chạy lại.")

def uid():
    return str(uuid.uuid4()).upper()

def p(path):
    return str(path).replace("\\", "/")

def probe(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r).groups()
    wh = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", r)
    return int((int(h) * 3600 + int(m) * 60 + float(s)) * US), (tuple(map(int, wh.groups())) if wh else None)

ref = json.load(open(a.ref, encoding="utf-8"))
draft = json.load(open(DRAFT / "draft_content.json", encoding="utf-8"))
tl_files = list((DRAFT / "Timelines").glob("*/draft_content.json"))

bk = DRAFT / f"_backup_{time.strftime('%Y%m%d_%H%M%S')}"; bk.mkdir()
shutil.copy2(DRAFT / "draft_content.json", bk / "draft_content.json")
shutil.copy2(DRAFT / "draft_meta_info.json", bk / "draft_meta_info.json")
for f in tl_files:
    shutil.copy2(f, bk / f"timeline_{f.parent.name}.json")

# --- mẫu lấy từ draft tham chiếu (1 track video, 1 text, 1 audio) ---
seg_tpl = {t["type"]: t["segments"][0] for t in ref["tracks"]}
track_tpl = {k: v for k, v in ref["tracks"][0].items() if k != "segments"}
mat = ref["materials"]
video_tpl, audio_tpl, text_tpl = mat["videos"][0], mat["audios"][0], mat["texts"][0]

M = {k: [] for k in draft["materials"]}
for k in ref["materials"]:
    M.setdefault(k, [])

def helper(kind):
    o = copy.deepcopy(mat[kind][0]); o["id"] = uid(); M[kind].append(o); return o["id"]

def kf_list(prop, pairs):
    return {"id": uid(), "material_id": "", "property_type": prop,
            "keyframe_list": [{"curveType": "Line", "graphID": "", "id": uid(),
                               "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0},
                               "time_offset": t, "values": [v]} for t, v in pairs]}

def make_track(kind, segs, idx):
    t = copy.deepcopy(track_tpl); t.update(id=uid(), type=kind, segments=segs)
    for s in segs: s["track_render_index"] = idx
    return t

def base_seg(kind, material_id, start, dur, src_start=0):
    s = copy.deepcopy(seg_tpl[kind])
    s.update(id=uid(), material_id=material_id, common_keyframes=[], keyframe_refs=[],
             target_timerange={"start": start, "duration": dur})
    if kind != "text":
        s["source_timerange"] = {"start": src_start, "duration": dur}
    return s

tl = json.load(open(ASSET / "_ghi_chu" / "timeline.json", encoding="utf-8"))
motion = {}
for line in (ASSET / "_ghi_chu" / "03_prompt_anh_va_chuyen_dong.txt").read_text(encoding="utf-8").splitlines():
    m = re.match(r"(\d{2}) \|.*\| (ZOOM|PAN)\s*$", line)
    if m: motion[int(m.group(1))] = m.group(2)
clips = tl["clips"]
TOTAL = int(tl["total"] * US)
starts = [int(c["start"] * US) for c in clips]
ends = starts[1:] + [TOTAL]
z0, z1 = map(float, a.zoom.split(",")); pan_sc, pan_x = map(float, a.pan.split(","))

# --- 1. ảnh + zoom/pan ---
vsegs = []
for i in range(1, len(clips) + 1):
    img = next(ASSET.joinpath("anh").glob(f"{i:02d}.*"))
    _, (w, h) = probe(img)
    v = copy.deepcopy(video_tpl)
    v.update(id=uid(), type="photo", path=p(img), material_name=img.name, duration=10800 * US,
             width=w, height=h, has_audio=False, local_material_id=str(uuid.uuid4()), unique_id="")
    M["videos"].append(v)
    start, dur = starts[i - 1], ends[i - 1] - starts[i - 1]
    s = base_seg("video", v["id"], start, dur)
    s["extra_material_refs"] = [helper(k) for k in ("speeds", "placeholder_infos", "canvases",
                                                     "sound_channel_mappings", "material_colors", "vocal_separations")]
    s["volume"] = 0.0
    end_t = dur - 1
    if motion.get(i) == "PAN":
        x0, x1 = (pan_x, -pan_x) if i % 2 else (-pan_x, pan_x)   # đổi chiều xen kẽ
        s["clip"]["scale"] = {"x": pan_sc, "y": pan_sc}; s["clip"]["transform"]["x"] = x0
        s["common_keyframes"] = [kf_list("KFTypePositionX", [(0, x0), (end_t, x1)]),
                                 kf_list("KFTypeScaleX", [(0, pan_sc), (end_t, pan_sc)]),
                                 kf_list("KFTypeScaleY", [(0, pan_sc), (end_t, pan_sc)])]
    else:
        s["clip"]["scale"] = {"x": z0, "y": z0}
        s["common_keyframes"] = [kf_list("KFTypeScaleX", [(0, z0), (end_t, z1)]),
                                 kf_list("KFTypeScaleY", [(0, z0), (end_t, z1)])]
    vsegs.append(s)

# --- 2. phụ đề (font mặc định của CapCut, có dấu tiếng Việt) ---
def text_material(txt):
    t = copy.deepcopy(text_tpl)
    n = len(txt.encode("utf-16-le")) // 2
    style = {"fill": {"content": {"render_type": "solid", "solid": {"color": [1, 1, 1]}}},
             "strokes": [{"content": {"render_type": "solid", "solid": {"alpha": 1, "color": [0, 0, 0]}}, "width": 0.06}],
             "size": a.sub_size, "bold": True, "range": [0, n]}
    t.update(id=uid(), content=json.dumps({"text": txt, "styles": [style]}, ensure_ascii=False),
             font_path="", font_resource_id="", font_id="", fonts=[], font_size=a.sub_size, text_size=30,
             border_color="#000000", border_width=0.06, background_alpha=0.0, has_shadow=True,
             shadow_alpha=0.6, alignment=1, words={"start_time": [], "end_time": [], "text": []},
             current_words={"start_time": [], "end_time": [], "text": []})
    M["texts"].append(t); return t["id"]

tsegs = []
for i, c in enumerate(tl["subs"]):
    st = int(c["start"] * US)
    s = base_seg("text", text_material(c["text"]), st, int(c["end"] * US) - st)
    s["extra_material_refs"] = []
    s["clip"]["scale"] = {"x": 1.0, "y": 1.0}
    s["clip"]["transform"] = {"x": 0.0, "y": a.sub_y}
    s["render_index"] = 14000 + i
    tsegs.append(s)

# --- 3. âm thanh ---
def audio_material(path, name):
    m = copy.deepcopy(audio_tpl)
    m.update(id=uid(), path=p(path), name=name, duration=probe(path)[0], music_id=str(uuid.uuid4()),
             type="extract_music", category_name="local_music", category_id="local")
    M["audios"].append(m); return m

def audio_seg(m, start, dur, vol, src_start=0):
    s = base_seg("audio", m["id"], start, dur, src_start)
    s["volume"] = s["last_nonzero_volume"] = vol
    s["extra_material_refs"] = [helper(k) for k in ("speeds", "placeholder_infos", "beats",
                                                     "sound_channel_mappings", "vocal_separations")]
    return s

def looped(m, start, end, vol):
    out, t = [], start
    while t < end:
        d = min(m["duration"], end - t); out.append(audio_seg(m, t, d, vol)); t += d
    return out

def pick(folder, pattern):
    files = sorted((ASSET / folder).glob("*.mp3"))
    return next((f for f in files if re.search(pattern, f.stem, re.I)), files[0] if files else None)

voice = []
for i, c in enumerate(clips, 1):
    m = audio_material(ASSET / "giong_doc" / c["file"], f"giong_{i:02d}")
    voice.append(audio_seg(m, starts[i - 1], m["duration"], 1.0))
tracks = [make_track("video", vsegs, 0), make_track("text", tsegs, 1), make_track("audio", voice, 2)]

music_f = pick("music", ".")
if music_f:
    tracks.append(make_track("audio", looped(audio_material(music_f, music_f.stem), 0, TOTAL, a.vol_music), 3))
wind_f = pick("sfx", "gio|wind")
if wind_f:
    tracks.append(make_track("audio", looped(audio_material(wind_f, wind_f.stem), 0, TOTAL, a.vol_wind), 4))
bird_f = pick("sfx", "chim|bird")
if bird_f and bird_f != wind_f and a.birds:
    bm = audio_material(bird_f, bird_f.stem); birds = []
    for rg in a.birds.split(","):
        lo, hi = map(int, rg.split("-"))
        birds += looped(bm, starts[lo - 1], ends[hi - 1], a.vol_birds)[:1]  # một lượt, không lặp
    tracks.append(make_track("audio", birds, 5))

draft["tracks"] = tracks
draft["materials"] = M
draft["duration"] = TOTAL
draft["canvas_config"] = {"ratio": "16:9", "width": 1920, "height": 1080, "background": None}
out = json.dumps(draft, ensure_ascii=False, separators=(",", ":"))
(DRAFT / "draft_content.json").write_text(out, encoding="utf-8")
for f in tl_files:
    f.write_text(out, encoding="utf-8")

meta = DRAFT / "draft_meta_info.json"
meta.write_text(re.sub(r'"tm_duration":\d+', f'"tm_duration":{TOTAL}', meta.read_text(encoding="utf-8")), encoding="utf-8")
print(f"ok: {len(vsegs)} ảnh, {len(tsegs)} phụ đề, {TOTAL / US:.1f} s; backup: {bk.name}")
