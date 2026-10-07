# Dự án Việt hóa Thư viện Prompts.chat

Dự án tự động hóa quá trình chuẩn hóa, phân loại và Việt hóa toàn bộ kho thư viện mẫu câu lệnh AI chính thức từ [prompts.chat](https://prompts.chat) phục vụ cộng đồng người dùng Việt Nam.

---

## 1. Cấu trúc thư mục

```
prompt-viet/
  data/
    original/          # Dữ liệu JSON gốc tải trực tiếp từ prompts.chat (prompts_original.json)
    batches/           # Các file batch dữ liệu đầu vào (batch_001_input.json,...)
    translated/        # Kết quả dịch từng batch sau khi agent thực hiện
    final/             # Kết quả hoàn chỉnh hợp nhất (prompts_vi.csv, prompts_vi.json)
  scripts/             # Các script tiện ích xử lý dữ liệu bằng Python (tạo batch, validate, merge)
  logs/                # Nhật ký quá trình xử lý và lỗi
  checkpoints/         # Điểm kiểm soát tiến độ xử lý
  TRANSLATION_INSTRUCTIONS.md # Hướng dẫn và quy chuẩn dịch thuật
  README.md            # Tài liệu tổng quan dự án
```

---

## 2. Kiến trúc xử lý

- **Python Scripts**: Đảm nhiệm các tác vụ kỹ thuật dữ liệu độc lập:
  - Tải và bảo toàn dữ liệu gốc.
  - Phân chia batch (50 prompt/batch) để kiểm soát ngữ cảnh tối ưu.
  - Kiểm tra hợp lệ (validation) schema và đối chiếu ID.
  - Quản lý checkpoint và ghép nối (merge) thành phẩm sang CSV và JSON.
- **Antigravity AI Agent**: Trực tiếp nhận từng batch dữ liệu đầu vào, thực hiện dịch thuật chuyên sâu, gắn taxonomy (Category, Tags) và đánh giá chất lượng (`quality_status`) theo đúng quy chuẩn tại `TRANSLATION_INSTRUCTIONS.md`.

---

## 3. Nguồn dữ liệu chính thức
- **Nguồn:** `https://prompts.chat/prompts.json?full_content=true`
- **Tổng số lượng prompt:** 2.479
- **Giấy phép bản quyền nội dung:** Creative Commons CC0 1.0 Universal (Public Domain)
