---
name: capcut-video
description: Làm video thuyết minh (địa lý, lịch sử, giới thiệu vùng đất...) kiểu ảnh hoạt hình 2D + giọng đọc + phụ đề, rồi dựng thẳng timeline vào project CapCut Pro của người dùng. Dùng khi người dùng nhờ "tạo video ... dài khoảng X phút", "làm video giống lần trước", "dựng timeline CapCut", hoặc gọi /capcut-video.
---

# Video thuyết minh → timeline CapCut

Quy trình đã chạy thành công với video "Bình Phước năm 1990" (10/2026, CapCut Pro 9.6 Windows).
Mẫu kết quả: `D:\test capcut claude\BinhPhuoc_1990` (folder tư liệu) và project CapCut `test 22`.
Người dùng nói tiếng Việt, gọi là "anh/chị". Trả lời ngắn, rõ, báo từng bước.

Script nằm trong `scripts/` của skill này (đường dẫn: `%USERPROFILE%\.claude\skills\capcut-video\scripts`).
Chạy bằng `python -P <script>` (Python 3.14; gói cần: `edge-tts numpy imageio-ffmpeg`, cài bằng
`python -m pip install --user edge-tts numpy imageio-ffmpeg` nếu thiếu). Không có ffmpeg hệ thống: dùng `imageio_ffmpeg.get_ffmpeg_exe()`.

## Cấu trúc folder tư liệu `<root>` (trong `D:\test capcut claude\<TenVideo>`)

```
anh/01.jpg ... NN.jpg          ảnh 16:9, mỗi câu một ảnh
giong_doc/01.mp3 ... NN.mp3    giọng đọc, mỗi câu một file
sfx/gio_rung.mp3, chim_hot.mp3 (hoặc file người dùng đưa)
music/nhac_nen.mp3             (hoặc file người dùng đưa)
_ghi_chu/                      KHÔNG kéo vào CapCut (CapCut chỉ nhận MP4/MOV/JPG/PNG/MP3)
  00_nguon_va_fact.md          bảng câu ↔ nguồn, và số cố ý KHÔNG nêu
  01_kich_ban.txt              mỗi câu một dòng
  03_prompt_anh_va_chuyen_dong.txt   dòng "NN | prompt tiếng Anh | ZOOM|PAN"
  04_phu_de_cum.txt            câu kịch bản có " / " đánh chỗ ngắt cụm phụ đề
  moc_tu.json, timeline.json, phu_de.srt   (script sinh ra)
```

## Các bước

1. **Tra cứu fact.** Wikipedia tiếng Việt (WebFetch `vi.wikipedia.org/wiki/<Tên>`; trang định hướng thì thêm "(tỉnh)", "(huyện)").
   Chỉ dùng fact chắc chắn; hai nguồn ghi số khác nhau thì KHÔNG nêu số. Chú ý mốc hành chính đúng năm được hỏi
   (vd 1990 chưa có tỉnh Bình Phước, vùng này thuộc tỉnh Sông Bé). Ghi `00_nguon_va_fact.md`.

2. **Kịch bản.** Giọng kể chuyện, mỗi câu một dòng, số câu theo yêu cầu. Độ dài: ~4–4,5 giây/câu khi đọc
   (≈ 12–16 chữ/câu) → 20 câu ≈ 1 phút 30. Viết `04_phu_de_cum.txt`: cùng câu, chèn " / " chia cụm 2–5 chữ theo
   nhịp đọc (ngắt ở dấu phẩy, không tách tên riêng). Năm và số viết bằng chữ số trong kịch bản để phụ đề ra chữ số.

3. **Giọng đọc.** Mặc định edge-tts giọng nam trầm `vi-VN-NamMinhNeural`, rate +4%, pitch −12Hz:
   `python -P scripts/tts.py <root>` → giong_doc/*.mp3 + `_ghi_chu/moc_tu.json` (mốc từng từ).
   Lỗi `NoAudioReceived` là tạm thời (script tự thử lại). Nếu người dùng muốn dịch vụ khác (vivibe, giọng CapCut)
   thì hỏi; giọng CapCut phải tạo trong app, khi đó phụ đề dùng "Phụ đề tự động" của CapCut.
   Báo người dùng edge-tts là dùng không chính thức dịch vụ của Microsoft (thận trọng với quảng cáo thương mại).

4. **Timeline + phụ đề.** `python -P scripts/make_timeline.py <root>` → `timeline.json` (mốc từng câu, nghỉ 0,4 s,
   các cụm phụ đề khớp mốc từ) và `phu_de.srt`. Nếu tổng dài hơn yêu cầu >10%: rút gọn câu, chạy lại bước 3–4.
   Phụ đề PHẢI chạy theo lời đọc (người dùng đã từ chối kiểu phụ đề từ khóa tóm tắt).

5. **SFX + nhạc.** Nếu người dùng không có file: `python -P scripts/make_sfx_music.py <root>`
   (tổng hợp gió rừng, chim hót, nhạc pad nhẹ; bỏ qua file đã có). Hỏi trước nếu họ nhắc có thư mục sfx/music riêng.

6. **Ảnh bằng Google Flow** (Codex không cài trên máy). Dùng Claude in Chrome (người dùng đã đăng nhập Google):
   - Mở `https://labs.google/fx/tools/flow` → "Dự án mới" → đóng popup giới thiệu.
   - Bấm chip model ở ô nhập (góc dưới phải) → chọn **Hình ảnh**, **16:9**, **x1**, model Nano Banana (0 tín dụng).
   - Mỗi ảnh: click ô "Bạn muốn tạo những gì?", gõ prompt, Enter, chờ 2 s rồi gửi prompt kế tiếp (Flow xếp hàng được).
   - Prompt = mô tả cảnh + STYLE CHUNG: "2D flat illustration, thin clean linework, flat colors with no gradients or
     texture, limited earthy palette (...), <bối cảnh, năm>, no text, no logos, 16:9."
   - Ảnh mới nằm trên cùng; danh sách ảo hóa nên phải cuộn để gom. Dùng javascript_tool: cuộn container lớn nhất,
     gom `img` có naturalWidth>500 vào `window.__t[src] = caption` (Flow tự đặt caption tiếng Anh ngắn), rồi
     map caption → số câu.
   - Tải về: fetch src → blob → `<a download="bpXX_NN.jpg">`. Chrome có thể về chậm vài giây — kiểm tra
     `%USERPROFILE%\Downloads` trước khi kết luận bị chặn. Chuyển vào `anh/NN.jpg`, xóa file tạm của mình.
   - Ghép contact sheet bằng ffmpeg (`tile=4x5`) rồi Read để kiểm tra thứ tự/chất lượng.
   - Ảnh Flow ~1376×768 và có logo ✦ nhỏ góc dưới phải — báo người dùng.

7. **Giao folder.** Nói người dùng: tạo project mới trong CapCut, (kéo folder vào nếu muốn — không bắt buộc),
   **đóng project** (về màn hình chính là đủ), gửi tên project.

8. **Dựng timeline.** Project nằm ở `%USERPROFILE%\Downloads\CapCut Drafts\<tên project>` (CapCut đổi tên thư mục
   theo tên project khi đóng; project cũ hơn có thể ở `AppData\Local\CapCut\User Data\Projects\com.lveditor.draft`,
   tra `root_meta_info.json` ở đó nếu không thấy). Chỉ ghi khi KHÔNG có file `.locked`.
   ```
   python -P scripts/build_capcut.py "<draft_dir>" <root> --birds 7-10,13-16
   ```
   `--birds`: các khoảng câu có cảnh rừng để đặt tiếng chim. Mặc định: zoom 1.0→1.25, pan scale 1.3 lia ±0.26
   (xen kẽ chiều), phụ đề size 9 trắng viền đen ở y=−0.82, nhạc 12%, gió 22% suốt video, chim 18%.
   Người dùng đã duyệt các mức này — giữ nguyên trừ khi được yêu cầu.
   Script tự sao lưu vào `<draft>/_backup_<thời gian>/` và ghi cả `Timelines/<id>/draft_content.json`.

9. **Kiểm tra.** Nhờ người dùng mở project, bấm phát: ảnh có chuyển động, phụ đề khớp giọng, âm lượng ổn.
   Mỗi lần sửa: sửa file/tham số → nhờ đóng project → chạy lại bước 8. Xong thì gợi ý xuất 1080p, 30fps, MP4.

## Lưu ý kỹ thuật

- `assets/ref_draft_content.json` là draft mẫu (CapCut 9.6) để lấy cấu trúc segment/material; nếu CapCut nâng cấp
  lớn mà project mở lỗi, lấy một draft mới có sẵn video + text + audio làm `--ref`.
- Thư mục chứa scripts tạm của phiên trước không còn; mọi script cần dùng đều ở `scripts/`.
- Không tự gửi/đăng gì ra ngoài; tải file từ Flow chỉ vào thư mục Downloads rồi chuyển vào `<root>`.
