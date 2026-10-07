# HƯỚNG DẪN VIỆT HÓA THƯ VIỆN PROMPTS.CHAT

Tài liệu này định nghĩa bộ quy tắc, tiêu chuẩn chất lượng và quy trình dịch thuật các prompt từ thư viện `prompts.chat` sang tiếng Việt dành cho Antigravity Agent.

---

## 1. Mục tiêu & Nguyên tắc cốt lõi
- Dịch thuật tự nhiên, chuẩn phong cách tiếng Việt hiện đại, gãy gọn, dễ hiểu.
- Không dịch máy từng chữ (word-by-word), không dùng từ ngữ tối nghĩa, gượng gạo.
- Giữ nguyên 100% mục đích, logic kỹ thuật và tính khả thi khi thực thi prompt của mô hình AI.
- **Chống Over-localization**: Không tự thêm "Việt Nam", "tiếng Việt", "người Việt" hoặc bối cảnh địa phương nếu prompt gốc không yêu cầu. Chỉ localize khi prompt gốc hoặc user yêu cầu rõ.

---

## 2. Quy tắc bảo toàn kỹ thuật (BẮT BUỘC)
Trong quá trình dịch sang `vi_prompt` và `vi_title`, **TUYỆT ĐỐI GIỮ NGUYÊN**:
1. Các biến tham số dạng: `{{variable}}`, `{variable}`, `${variable}`, `[variable]`.
2. Toàn bộ mã nguồn (code blocks), tên hàm, tên biến, câu lệnh SQL/Bash/Python...
3. Các URL, đường dẫn liên kết, địa chỉ email, username `@handle`.
4. Cấu trúc Markdown: tiêu đề (`#`, `##`), danh sách (`-`, `*`, `1.`), bảng biểu (`|`), chữ in đậm (`**`), in nghiêng (`*`).
5. Tên mô hình AI: GPT-4, Claude, Gemini, Llama, Midjourney, Stable Diffusion...
6. Các thuật ngữ API, SDK, tên công nghệ, tên sản phẩm hoặc thương hiệu: Figma, React, Docker, Kubernetes, Total Station, RTK-GPS...
7. Thuật ngữ chuyên ngành phổ biến trong cộng đồng công nghệ/marketing (ví dụ: *UI/UX, prompt, mockups, landing page, lead, conversion rate, commit, branch...*) giữ nguyên hoặc mở ngoặc chú thích nếu cần.

---

## 3. Phân loại Category
Tự động gán trường `category` vào 1 trong các nhóm tiêu chuẩn sau:
- `Business`
- `Marketing`
- `Sales`
- `Social Media`
- `Content`
- `Image`
- `Video`
- `Coding`
- `Data`
- `Education`
- `Productivity`
- `Career`
- `Finance`
- `Legal`
- `Restaurant & F&B`
- `Travel`
- `Personal Development`
- `Other`

---

## 4. Gán Tags
- Tạo từ **3 đến 8 tags** liên quan chặt chẽ đến chủ đề, kỹ năng, định dạng hoặc công cụ của prompt.
- Tag dạng chữ thường tiếng Anh hoặc tiếng Việt không dấu kết nối bằng dấu gạch ngang (ví dụ: `image-generation`, `portrait`, `midjourney`).

---

## 5. Đánh giá chất lượng (`quality_status`)
- Đặt `"quality_status": "ok"`: Đối với các prompt rõ ràng, có cấu trúc tốt, có giá trị tái sử dụng cao.
- Đặt `"quality_status": "needs_review"`: **Chỉ gán khi** lỗi thực sự ảnh hưởng đến:
  + **Ý nghĩa** (tối nghĩa, không thể hiểu được).
  + **Khả năng sử dụng** (thiếu quá nhiều ngữ cảnh cản trở sử dụng).
  + **Tính an toàn** (vi phạm nguyên tắc an toàn).
  + **Độ rõ ràng** (thông tin cá nhân cụ thể, số điện thoại, spam/quảng cáo rác cục bộ).

**LƯU Ý ĐẶC BIỆT**: Không tự động gán `needs_review` chỉ vì prompt:
- Quá ngắn.
- Có lỗi đánh máy (typo) nhẹ.
- Sử dụng ngôn ngữ gốc không phải tiếng Anh.

---

## 6. Xử lý Metadata Đặc biệt
- **language_original**: Nếu trong quá trình dịch, Agent xác định chắc chắn ngôn ngữ thực tế của bản gốc khác với `language_original` hiện có (VD: thực tế là tiếng Tây Ban Nha nhưng đang ghi 'en'):
  + Chủ động cập nhật `language_original` sang mã ngôn ngữ đúng (VD: 'es', 'fr', 'zh'...).
  + Đặt `language_detection = "ai"`.

---

## 7. Schema đầu ra cho mỗi prompt
```json
{
  "id": "cmu...",
  "original_title": "...",
  "original_prompt": "...",
  "vi_title": "...",
  "vi_prompt": "...",
  "category": "...",
  "tags": ["tag1", "tag2", "tag3"],
  "author": "...",
  "source": "prompts.chat",
  "quality_status": "ok",
  "language_original": "en",
  "language_detection": "ai"
}
```

---

## 8. Quy tắc QA – Evidence First

Mọi lỗi QA phải được xác minh trực tiếp từ file dữ liệu thật.

Trước khi báo một lỗi:
1. Tìm đúng record bằng `id`.
2. Đọc `original_prompt`.
3. Đọc `vi_prompt`.
4. Chỉ rõ đoạn sai cụ thể.
5. Nếu không có bằng chứng trong file thì không được kết luận lỗi.

**Tuyệt đối không được:**
- Tạo record giả.
- Dùng ví dụ không tồn tại trong batch.
- Suy đoán từ memory/context trước đó.
- Báo lỗi mà không dẫn được `id` record thật.
