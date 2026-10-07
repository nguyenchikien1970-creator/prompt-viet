# PROMPT VIỆT – SYSTEM ARCHITECTURE

## 1. Executive Summary & Architecture Philosophy

Prompt Việt là thư viện câu lệnh AI (Prompt Library) chất lượng cao bằng tiếng Việt với quy mô **2,479 prompts** đã được chuẩn hóa, phân loại, dịch thuật và kiểm toán chất lượng.

Mục tiêu cốt lõi:
- **Cực nhanh (Near-instant UX):** Phản hồi tìm kiếm và bộ lọc dưới 10ms.
- **Static-First & Zero-Cost Infrastructure:** Không phụ thuộc database server hay serverless compute đắt đỏ. Toàn bộ website và dữ liệu tìm kiếm được phân phối tĩnh qua CDN toàn cầu (Vercel, Cloudflare Pages hoặc GitHub Pages).
- **Offline/PWA Ready:** Do toàn bộ dataset và search index tĩnh, người dùng có thể tra cứu ngay cả khi kết nối mạng chập chờn.
- **Zero-Maintenance:** Không có database server để bảo trì, không có connection pooling, không lo quota billing cạn kiệt.

---

## 2. System Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                 BUILD PIPELINE                                  |
|                                                                                 |
|  prompts_normalized.json (Source)                                               |
|           |                                                                     |
|           v                                                                     |
|  pipeline_manager.py (Translate & Audit)                                        |
|           |                                                                     |
|           v                                                                     |
|  prompts_vi.json (Master Source of Truth - 2,479 records)                       |
|           |                                                                     |
|           +---------------------------------------------+                       |
|           |                                             |                       |
|           v (build-search-index)                        v (export-csv)          |
|  search_index.json & prompts_search.json         prompts_vi.csv                 |
+---------------------------------------------------------------------------------+
                                    |
                                    v (Static Build / Distribution)
+---------------------------------------------------------------------------------+
|                           STATIC WEB APPLICATION (CDN)                          |
|                                                                                 |
|   HTML5 + TailwindCSS / Vanilla JS / MiniSearch Engine Engine                   |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                         IN-BROWSER SEARCH ENGINE                        |   |
|   |                                                                         |   |
|   |  - Client-Side Inverted Index & Tokenizer (Vietnamese Unaccent)         |   |
|   |  - Multi-Field Weighted Matching (Title: 3x, Keywords: 2x, Tags: 2x)   |   |
|   |  - Multi-Dimensional Filter State (Category, Model, Difficulty)         |   |
|   |  - 1-Click Copy Engine & Modal Detail Viewer                            |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```

---

## 3. Data Flow & Separation of Concerns

1. **Source of Truth Layer:**
   - Tệp master: `prompt-viet/data/final/prompts_vi.json` chứa đầy đủ 22 trường dữ liệu cho 2,479 bản ghi.
2. **Indexing & Optimization Layer:**
   - Script `pipeline_manager.py build-search-index` loại bỏ các trường thừa không dùng trong hiển thị ban đầu, tạo ra:
     - `prompts_search.json`: Danh sách dữ liệu nén phục vụ hiển thị card và bộ lọc (~1.2 MB).
     - `search_index.json`: Chỉ mục đảo (Inverted index) + từ điển autocomplete giúp tìm kiếm không cần index lại ở client.
3. **Client-Side Presentation Layer:**
   - Tải tệp dữ liệu tĩnh qua CDN với `Cache-Control: public, max-age=31536000, immutable`.
   - Tìm kiếm trực tiếp trên bộ nhớ trình duyệt (Web Worker hoặc Main Thread với độ trễ < 5ms).

---

## 4. Scalability & Future Evolution

- **Giai đoạn hiện tại (1 - 10,000 prompts):** Static-First hoàn toàn vượt trội về tốc độ, chi phí $0, không độ trễ mạng và trải nghiệm người dùng tối ưu.
- **Giai đoạn mở rộng tương lai (Optional Future Backend):** Khi cần tính năng cá nhân hóa (Đăng nhập, Lưu yêu thích, Lịch sử người dùng, Submit prompt từ cộng đồng), Supabase sẽ được tích hợp làm API layer bổ sung mà không ảnh hưởng tới kiến trúc Static Search hiện tại.
