"""Tạo SFX (gió rừng, chim hót) và nhạc nền nhẹ bằng tổng hợp âm thanh, khi người dùng không có file sẵn.
Nhạc dài đúng timeline.json["total"]. Bỏ qua file đã có, trừ khi --force.

python make_sfx_music.py <root> [--force]
"""
import argparse, json, pathlib, subprocess, wave
import numpy as np, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
ap = argparse.ArgumentParser()
ap.add_argument("root", type=pathlib.Path)
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
rng = np.random.default_rng(7)
total = json.loads((a.root / "_ghi_chu" / "timeline.json").read_text(encoding="utf-8"))["total"]

def save_mp3(x, path):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    tmp = path.with_suffix(".wav")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(tmp), "-b:a", "192k", str(path)], check=True)
    tmp.unlink(); print("tạo", path.name)

def lowpass(x, alpha):
    y = np.empty_like(x); acc = 0.0
    for i in range(0, len(x), 4096):
        blk = x[i:i + 4096]; out = np.empty_like(blk)
        for j, v in enumerate(blk):
            acc += alpha * (v - acc); out[j] = acc
        y[i:i + 4096] = out
    return y

def fade(x, sec):
    n = int(sec * SR); env = np.ones(len(x)); env[:n] = np.linspace(0, 1, n); env[-n:] = np.linspace(1, 0, n)
    return x * env if x.ndim == 1 else x * env[:, None]

def need(path):
    path.parent.mkdir(exist_ok=True)
    return a.force or not path.exists()

wind_p, bird_p, music_p = a.root / "sfx" / "gio_rung.mp3", a.root / "sfx" / "chim_hot.mp3", a.root / "music" / "nhac_nen.mp3"

if need(wind_p):  # noise lọc thấp, lên xuống chậm theo cơn gió
    n = int(40 * SR); noise = rng.standard_normal(n)
    wind = lowpass(noise, 0.02) * 0.6 + lowpass(noise, 0.08) * 0.15
    tt = np.arange(n) / SR
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * tt / 9.0) * np.sin(2 * np.pi * tt / 23.0 + 1)
    save_mp3(fade(np.stack([wind * gust, np.roll(wind, 900) * gust], 1), 3), wind_p)

if need(bird_p):  # tiếng chíp FM ngẫu nhiên, pan trái phải
    n = int(30 * SR); birds = np.zeros((n, 2))
    for _ in range(38):
        s = rng.uniform(0, 29); f0 = rng.uniform(2600, 4800); pan = rng.uniform(0.2, 0.8)
        for k in range(rng.integers(2, 6)):
            dur = rng.uniform(0.05, 0.14); m = int(dur * SR); ts = np.arange(m) / SR
            sweep = f0 + rng.uniform(-900, 900) * ts / dur
            tone = np.sin(2 * np.pi * np.cumsum(sweep) / SR + 0.3 * np.sin(2 * np.pi * 40 * ts))
            env = np.sin(np.pi * ts / dur) ** 2 * rng.uniform(0.3, 1)
            i = int((s + k * rng.uniform(0.12, 0.22)) * SR)
            if i + m < n:
                birds[i:i + m, 0] += tone * env * (1 - pan); birds[i:i + m, 1] += tone * env * pan
    save_mp3(fade(birds + lowpass(rng.standard_normal(n), 0.02)[:, None] * 0.05, 2), bird_p)

if need(music_p):  # pad ấm Am-F-C-G, nốt đàn nhẹ
    n = int(total * SR); ts = np.arange(n) / SR; music = np.zeros((n, 2))
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [130.81, 196.0, 261.63], [196.0, 246.94, 293.66]]
    bar = 6.0
    for c in range(int(total / bar) + 1):
        lo, hi = int(c * bar * SR), min(n, int((c + 1.6) * bar * SR))
        if lo >= n: break
        seg = ts[lo:hi] - c * bar; env = np.sin(np.pi * np.clip(seg / (bar * 1.6), 0, 1)) ** 1.5
        for f in chords[c % 4]:
            for det, ch in ((-0.7, 0), (0.7, 1)):
                music[lo:hi, ch] += (np.sin(2 * np.pi * (f + det) * seg) + 0.25 * np.sin(4 * np.pi * (f + det) * seg)) * env * 0.2
        music[lo:hi] += (np.sin(np.pi * chords[c % 4][0] * seg) * env * 0.25)[:, None]
        for h in range(4):
            st, m = int((c * bar + h * 1.5) * SR), int(1.4 * SR)
            if st + m < n:
                pp = np.arange(m) / SR
                music[st:st + m] += (np.sin(4 * np.pi * chords[c % 4][h % 3] * pp) * np.exp(-pp * 3) * 0.12)[:, None]
    music[:, 0] = lowpass(music[:, 0], 0.25); music[:, 1] = lowpass(music[:, 1], 0.25)
    save_mp3(fade(music, 4), music_p)
