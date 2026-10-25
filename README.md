# capcut-video — Claude Code skill

Skill cho Claude Code: làm video thuyết minh ảnh hoạt hình 2D (giọng đọc + phụ đề khớp từng chữ + SFX + nhạc nền)
và dựng thẳng timeline vào project **CapCut Pro** (đã kiểm chứng trên CapCut 9.6 Windows) bằng cách ghi file `draft_content.json`.

## Cài đặt

Chép thư mục này vào `~/.claude/skills/capcut-video/`, rồi trong Claude Code gõ `/capcut-video` hoặc nhờ
"làm video về ... dài 1 phút 30, dựng vào CapCut".

Cần Python 3 và:

```bash
python -m pip install --user edge-tts numpy imageio-ffmpeg
```

## Nội dung

| File | Việc |
|---|---|
| `SKILL.md` | Quy trình từng bước cho Claude |
| `scripts/tts.py` | Giọng đọc edge-tts, mỗi câu một file, kèm mốc thời gian từng từ |
| `scripts/make_timeline.py` | Mốc từng câu + phụ đề cụm 2–5 chữ khớp lời đọc, xuất `.srt` |
| `scripts/make_sfx_music.py` | Tổng hợp tiếng gió rừng, chim hót, nhạc nền nhẹ |
| `scripts/build_capcut.py` | Ghi timeline (ảnh zoom/pan, phụ đề, giọng, nhạc, SFX) vào project CapCut đã đóng |
| `assets/ref_draft_content.json` | Draft mẫu đã làm sạch, dùng làm khuôn cấu trúc |

## Lưu ý

- Chỉ ghi khi project đã đóng trong CapCut (không có file `.locked`); script tự sao lưu trước khi ghi.
- Định dạng draft của CapCut không công khai và có thể đổi theo phiên bản.
- edge-tts dùng không chính thức dịch vụ đọc của Microsoft; cân nhắc khi dùng cho mục đích thương mại.
