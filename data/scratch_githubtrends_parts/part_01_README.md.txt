README.md 
# GitHubTrends Skill

**Nhanh chóng khám phá các dự án mã nguồn mở được yêu thích nhất trên GitHub, tự động tạo bảng điều khiển trực quan!**

## Tính năng nổi bật

### Tính năng cơ bản
- ✅ Lấy danh sách các dự án thịnh hành hàng ngày/hàng tuần
- ✅ Lọc theo ngôn ngữ lập trình (TypeScript, Python, Go, Rust, v.v.)
- ✅ Tùy chỉnh số lượng dự án trả về
- ✅ Hiển thị tổng số Star và mức tăng trưởng theo chu kỳ
- ✅ Không cần mã token GitHub API

### Bảng điều khiển trực quan 🆕
- ✨ **HTML tương tác** - Tạo bảng điều khiển trang web có thể tương tác
- 📊 **Trực quan hóa dữ liệu** - Biểu đồ tròn tỷ lệ ngôn ngữ, biểu đồ cột tăng trưởng Stars
- 📰 **Tin tức công nghệ** - Tích hợp tin tức nóng hổi từ Hacker News
- 🔍 **Lọc thời gian thực** - Lọc theo ngôn ngữ, sắp xếp và tìm kiếm tức thì
- 📱 **Thiết kế thích ứng (Responsive)** - Hỗ trợ máy tính bàn, máy tính bảng và điện thoại
- 🎨 **Giao diện đẹp mắt** - Phong cách Tailwind CSS + GitHub

## Bắt đầu nhanh

### Xem các dự án thịnh hành trong tuần (mặc định)

```bash
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts weekly
```

### Xem các dự án thịnh hành hôm nay

```bash
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts daily
```

### Lọc theo ngôn ngữ

```bash
# Dự án TypeScript thịnh hành
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts weekly --language=TypeScript

# Dự án Python thịnh hành
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts weekly --language=Python

# Dự án Go thịnh hành
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts weekly -l=Go
```

### Chỉ định số lượng kết quả trả về

```bash
# Trả về 20 dự án
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts weekly --limit=20

# Kết hợp: Trả về 15 dự án TypeScript
bun ~/.claude/skills/GitHubTrends/Tools/GetTrending.ts weekly --language=TypeScript --limit=15
```

---

## Tạo bảng điều khiển trực quan 🆕

### Cách dùng cơ bản

```bash
# Tạo dashboard xu hướng tuần này (mặc định)
bun ~/.claude/skills/GitHubTrends/Tools/GenerateDashboard.ts
```

### Kèm tin tức công nghệ

```bash
# Tạo dashboard bao gồm tin tức từ Hacker News
bun ~/.claude/skills/GitHubTrends/Tools/GenerateDashboard.ts --include-news
```

### Tùy chọn nâng cao

```bash
# Tạo dashboard hàng ngày cho TypeScript, kèm 15 tin tức
bun ~/.claude/skills/GitHubTrends/Tools/GenerateDashboard.ts \
  --period daily \
  --language TypeScript \
  --limit 20 \
  --include-news \
  --news-count 15 \
  --output ~/Downloads/ts-daily-trends.html
```

### Chức năng của bảng điều khiển

Tệp HTML được tạo bao gồm:
- **Tổng quan thống kê** - Tổng số dự án, tổng số stars, các dự án top đầu
- **Biểu đồ phân bố ngôn ngữ** - Biểu đồ tròn thể hiện tỷ trọng từng ngôn ngữ
- **Biểu đồ tăng trưởng Stars** - Biểu đồ cột trực quan hóa xu hướng tăng
- **Thẻ dự án (Project Cards)** - Trình bày dự án dạng thẻ giao diện đẹp mắt
- **Tin tức công nghệ** - Cập nhật mới nhất từ Hacker News
- **Tính năng tương tác** - Lọc, sắp xếp và tìm kiếm nhanh
- **Responsive** - Tự động tương thích với mọi kích thước màn hình

---

## Mẫu đầu ra (Output Example)

```markdown
# GitHub Trending Projects - Weekly (2026-01-19)

📊 **Total:** 10 projects | **Language:** All | **Period:** Weekly

---

## 1. vercel/next.js - ⭐ 125,342 (+1,234 this week)
**Language:** TypeScript
**Description:** The React Framework for the Web
**URL:** https://github.com/vercel/next.js

## 2. microsoft/vscode - ⭐ 160,890 (+987 this week)
**Language:** TypeScript
**Description:** Visual Studio Code
**URL:** https://github.com/microsoft/vscode

...
```

## Bảng giải thích tham số

| Tham số | Ý nghĩa | Mặc định | Giá trị khả dụng |
|---------|---------|----------|-------------------|
| `period` | Chu kỳ thời gian | `weekly` | `daily`, `weekly` |
| `--language` | Lọc ngôn ngữ lập trình | Tất cả | TypeScript, Python, Go, Rust, Java, v.v. |
| `--limit` | Số lượng dự án trả về | 10 | Số nguyên dương bất kỳ |

## Các ngôn ngữ được hỗ trợ

Mọi ngôn ngữ lập trình thông dụng đều có thể dùng làm bộ lọc:
- **TypeScript** - Dự án TypeScript
- **JavaScript** - Dự án JavaScript
- **Python** - Dự án Python
- **Go** - Dự án Go
- **Rust** - Dự án Rust
- **Java** - Dự án Java
- **C++** - Dự án C++
- **Ruby** - Dự án Ruby
- **Swift** - Dự án Swift
- **Kotlin** - Dự án Kotlin

## Từ khóa kích hoạt Skill

Kỹ năng này sẽ được kích hoạt khi bạn nói bất kỳ cụm từ nào sau:

- "show github trends" / "github trending"
- "hiển thị dự án hot" / "xem có dự án nào đang thịnh hành"
- "weekly trending" / "dự án hot tuần này"
- "daily trending" / "dự án hot hôm nay"
- "TypeScript trending" / "Python trending"
- "what's hot on github" / "github có gì hot"

## Hiện thực kỹ thuật

- **Nguồn dữ liệu**: Trang trending chính thức của GitHub (https://github.com/trending)
- **Phương thức phân tích**: Phân tích cú pháp HTML để trích xuất thông tin dự án
- **Xác thực**: Không cần mã token GitHub API
- **Tần suất cập nhật**: Cập nhật mỗi giờ một lần

## Cấu trúc thư mục

```
~/.claude/skills/GitHubTrends/
├── SKILL.md              # Tệp cấu hình chính của Skill
├── README.md             # Tài liệu hướng dẫn sử dụng (tệp này)
├── Tools/
│   └── GetTrending.ts    # Công cụ lấy dữ liệu trending
└── Workflows/
    └── GetTrending.md    # Tài liệu quy trình công việc
```

## Lưu ý quan trọng

1. **Yêu cầu mạng**: Cần có kết nối truy cập vào trang chủ GitHub
2. **Tần suất cập nhật**: Dữ liệu cập nhật theo giờ, không phải thời gian thực từng giây
3. **Độ chính xác phân tích**: Cấu trúc trang GitHub thay đổi có thể ảnh hưởng đến kết quả, hãy kiểm tra `/tmp/github-trending-debug-*.html` nếu gặp lỗi
4. **Tham số ngôn ngữ**: Không phân biệt chữ hoa/thường (`--language=typescript` và `--language=TypeScript` có tác dụng như nhau)

## Vấn đề đã biết

- Cấu trúc HTML của trang GitHub trending khá phức tạp, một số URL hoặc tên dự án có thể cần được xử lý cẩn thận
- Nếu GitHub cập nhật giao diện, công cụ có thể cần cập nhật lại logic bóc tách dữ liệu

## Định hướng phát triển

- [ ] Hỗ trợ lưu trữ dữ liệu lịch sử để phân tích xu hướng dài hạn
- [ ] Lọc theo khoảng stars (1k+, 10k+, 100k+)
- [ ] Nâng cấp bộ phân tích HTML thông minh hơn
- [ ] Tích hợp vào quy trình tự động của các kỹ năng khác
