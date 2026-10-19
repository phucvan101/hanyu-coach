# Hanyu Coach — luyện tiếng Trung trên máy cá nhân

Ứng dụng web chạy **trên chính máy của bạn** (không đưa lên internet), dựa trên file từ vựng bạn đã học:

1. **Ôn nhanh đầu buổi**: các từ đến hạn ôn và những câu bạn nói sai ở các buổi trước.
2. **Kiểm tra từ vựng** (6 dạng câu hỏi): Hán tự → nghĩa · nghĩa → Hán tự · Hán tự → pinyin · nghe → chọn từ · nghĩa → tự gõ Hán tự · điền từ vào câu.
3. **Hội thoại có kiểm soát**: AI đóng vai theo tình huống của bài và **chỉ dùng từ bạn đã học**.
4. **Hội thoại tự do**: bạn phải tự dùng các từ mục tiêu của bài.
5. **Báo cáo cuối buổi**: điểm mạnh, điểm yếu, từng câu sai kèm câu đúng, lỗi ngữ pháp, điểm theo kỹ năng. Mọi thứ được lưu lại; biểu đồ tiến độ nằm ở trang chủ.

Trang **Hội thoại tổng hợp**: chọn một quyển và tự đặt chủ đề bất kỳ. AI nói bằng từ của quyển; nếu cần từ mới (tối đa 2 từ/lượt) thì từ đó được in đậm kèm giải thích. Câu sai được sửa ngay dưới câu bạn nói. Cuối buổi có báo cáo và **lộ trình cải thiện**: các bài bấm làm ngay (viết lại câu sai, hội thoại ngắn luyện đúng điểm ngữ pháp bị sai, ôn pinyin từ yếu, hội thoại buộc dùng các từ bạn chưa dùng).

Ngoài ra có trang **Hán tự → pinyin** (thanh bên trái): luyện riêng việc nhìn chữ Hán rồi gõ pinyin, chọn tất cả / từ yếu / đến hạn ôn / hay sai thanh hoặc theo từng quyển, bài.

Trang **Flashcard** (thanh bên trái): lật thẻ theo 3 chiều (Hán tự → nghĩa · nghĩa → Hán tự · nghe → Hán tự), tự chấm *Quên / Khó / Nhớ / Dễ* và kết quả được ghi vào lịch ôn. Chọn bộ thẻ giống trang pinyin; phím tắt `Space` lật, `1`–`4` chấm, `←` `→` xem lại thẻ trước.

Phải đạt **≥ 70%** ở mỗi bước mới mở được bước tiếp theo.

---

## Cài đặt (không cần biết lập trình)

### Bước 1 — Cài Docker Desktop (chỉ làm một lần)
- Tải tại https://www.docker.com/products/docker-desktop/ rồi cài như phần mềm bình thường.
- **Windows**: nếu trình cài đặt hỏi về WSL 2 thì đồng ý; cài xong khởi động lại máy.
- **Mac**: chọn bản đúng chip (Apple Silicon M1/M2/M3… hoặc Intel).
- Mở Docker Desktop một lần, chấp nhận điều khoản. Không cần đăng nhập.

### Bước 2 — Giải nén
Giải nén file zip vào một chỗ cố định, ví dụ `Documents/hanyu-coach`. Đừng để trong thư mục Downloads rồi xoá nhầm, vì dữ liệu học nằm ở thư mục `data` bên trong.

### Bước 3 — Mở ứng dụng
- **Windows**: bấm đúp `Start-Windows.bat`.
- **Mac**: lần đầu **chuột phải** vào `Start-Mac.command` → **Open** → **Open** (macOS chặn file tải từ internet). Từ lần sau bấm đúp là chạy.

Lần đầu mất 2–5 phút để tải và cài đặt. Xong trình duyệt sẽ tự mở trang **http://localhost:8765**. Những lần sau chỉ mất vài giây.

Muốn tắt hẳn: chạy `Stop-Windows.bat` / `Stop-Mac.command`. Nếu không tắt, ứng dụng chạy nền rất nhẹ và tự bật lại cùng Docker Desktop.

### Bước 4 — Nhập API key (miễn phí)
1. Vào https://aistudio.google.com/apikey, đăng nhập Google, bấm **Create API key**.
2. Trong app: **Cài đặt** → dán vào ô *Gemini API key* → **Lưu cài đặt** → **Kiểm tra kết nối**.

Nên thêm **AI dự phòng** để dùng khi Gemini hết hạn mức miễn phí trong ngày: **GLM-4.7-Flash** (miễn phí, tiếng Trung rất tự nhiên). Đăng ký tại https://open.bigmodel.cn hoặc https://z.ai, tạo API key, rồi trong Cài đặt bấm nút *GLM* và dán key.

### Bước 5 — Nhập từ vựng
**Thư viện** → chọn file CSV → **Nhập**. AI sẽ chuẩn hoá nghĩa và chia bài theo chủ đề (1–2 phút). Xong thì về trang **Học** và bấm **Bắt đầu**.

---

## Định dạng file từ vựng
Đúng định dạng xuất từ Hanzii, phân cách bằng dấu `;`, không cần dòng tiêu đề:
```
办公室;bàngōngshì;BIỆN CÔNG THẤT;"văn phòng; phòng hành chính";""
```
Cột: Hán tự · pinyin · Hán Việt · nghĩa (nhiều nghĩa ngăn bằng `;`) · ghi chú (có thể để trống).
Mỗi file là **một quyển bạn đã học xong**. Hanzii hay xếp nghĩa hiếm lên đầu (VD 错 = "mài"), nên AI chọn lại *nghĩa chính* theo giáo trình. Bạn có thể sửa tay trong **Thư viện → Xem & sửa bài**.

**Tài liệu ngữ pháp / bài khoá** (.txt, .md, .pdf có chữ, .docx): thêm vào từng quyển trong Thư viện. AI rút ra các mẫu câu, và phần hội thoại sẽ bám theo các mẫu đó.

## Gõ tiếng Trung
- **Bộ gõ có sẵn trong app** (nút <b>拼</b> màu xanh): gõ pinyin không dấu, ví dụ `mifan`, rồi bấm **Space** hoặc phím số để chọn chữ. Những từ bạn đã học hiện lên trước.
- **Tắt nút 拼** để gửi thẳng pinyin trong hội thoại; AI sẽ hiểu và tự chuyển sang chữ Hán.
- Dùng bộ gõ của máy: *Windows*: Cài đặt → Thời gian & ngôn ngữ → Ngôn ngữ → Thêm *Tiếng Trung (Giản thể)* → Microsoft Pinyin. *Mac*: Cài đặt hệ thống → Bàn phím → Nguồn đầu vào → thêm *Pinyin – Giản thể*.
- **Nói**: bấm nút micro, nói, bấm lần nữa để dừng. Trình duyệt sẽ hỏi quyền dùng micro ở lần đầu. Phần nhận dạng giọng nói dùng Gemini.

## Cách chấm
- **Pinyin**: chỉ cần đúng âm là tính đúng. Sai hoặc thiếu thanh điệu chỉ bị cảnh báo (dấu triện vàng 调) và bị trừ vào kỹ năng *Thanh điệu*. Có thể gõ `ni3hao3`, `nǐhǎo` hoặc `nihao`.
- **Câu sai trong hội thoại** được đưa vào *Sổ lỗi* và quay lại ở phần ôn đầu buổi. Viết lại đúng **2 lần** thì câu đó được coi là đã sửa xong.
- **Từ vựng** được lên lịch ôn theo phương pháp lặp lại ngắt quãng: từ nào sai sẽ quay lại ngay buổi sau, từ đúng liên tục thì giãn dần (1 → 3 → 7+ ngày).

## Dữ liệu & quyền riêng tư
- Toàn bộ lịch sử học nằm trong thư mục `data` (file `hanyu.sqlite`). Muốn sao lưu thì copy thư mục này, hoặc vào **Cài đặt → Tải bản sao lưu**.
- Ứng dụng chỉ mở cho chính máy này (`127.0.0.1`), người khác trong cùng mạng không vào được.
- Chỉ nội dung câu hỏi và hội thoại được gửi tới AI (Gemini/GLM). Ở gói miễn phí, Google có thể dùng nội dung này để cải thiện model, nên đừng đưa thông tin cá nhân vào hội thoại.
- Giọng đọc mặc định là giọng Microsoft online (miễn phí, không cần key). Có thể chuyển sang *giọng có sẵn trên máy* trong Cài đặt.

## Cập nhật phiên bản mới
Tắt app, thay mọi file và thư mục **trừ `data`**, rồi chạy lại file Start. App sẽ tự cài đặt lại.

## Xử lý sự cố
| Hiện tượng | Cách xử lý |
|---|---|
| Cửa sổ báo không khởi động được Docker | Mở Docker Desktop bằng tay, đợi đến khi hiện "Engine running", rồi chạy lại file Start. |
| Trình duyệt báo "không truy cập được" | Đợi thêm 1 phút rồi tải lại trang (lần đầu cài đặt khá lâu). |
| "Chưa cấu hình API key" / "HTTP 429" | Nhập key trong Cài đặt. Lỗi 429 là hết hạn mức miễn phí trong ngày: thêm AI dự phòng GLM. |
| Không nghe được âm thanh | Cài đặt → Giọng đọc → chọn "giọng có sẵn trên máy" → Nghe thử. |
| Mac báo "không thể mở vì nhà phát triển không xác định" | Chuột phải → Open. Nếu vẫn bị chặn: mở Terminal, gõ `chmod +x ` rồi kéo file Start-Mac.command vào, nhấn Enter. |
| Cổng 8765 đã bị dùng | Sửa `127.0.0.1:8765:8765` thành `127.0.0.1:8766:8765` trong `docker-compose.yml`, rồi mở http://localhost:8766 |

---

## Dành cho lập trình viên
```
backend/   FastAPI + SQLite (app/), jieba + pypinyin, LLM: Gemini (API gốc) + OpenAI-compatible
  app/learning.py    luồng học, chấm điểm, báo cáo
  app/quiz.py        sinh câu hỏi & chấm
  app/pinyin_utils.py chuẩn hoá/chấm pinyin, thanh điệu
  app/text_utils.py  tách từ, kiểm tra câu AI chỉ dùng từ đã học
  app/ime.py         bộ gõ pinyin (chỉ mục app/data/ime.sqlite, tạo bằng scripts/build_ime.py)
  app/prompts.py     toàn bộ prompt
frontend/  Vue 3 + Vite (dist/ đã build sẵn để Docker không cần Node)
```
Chạy dev:
```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8765
cd frontend && npm install && npm run dev        # http://localhost:5173
HANYU_FAKE_LLM=1 python -m pytest -q            # test luồng đầy đủ với LLM giả lập
```
Sửa giao diện xong thì chạy `npm run build` để cập nhật `frontend/dist`.
# hanyu-coach
