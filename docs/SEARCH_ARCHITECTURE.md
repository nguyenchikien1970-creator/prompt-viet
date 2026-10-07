# PROMPT VIỆT – SEARCH ARCHITECTURE

## 1. Yêu cầu & Mục tiêu (Requirements & Goals)

Kho dữ liệu: **2,479 prompts**.
Mục tiêu hiệu năng:
- **Độ trễ tìm kiếm (Latency):** < 5ms trong trình duyệt trên mọi thiết bị.
- **Dung lượng tải (Payload):** < 350 KB (gzipped transfer size).
- **Trải nghiệm tiếng Việt:** Tìm kiếm không dấu (accent-insensitive) khớp chính xác dữ liệu có dấu và ngược lại.
- **Đa trường (Multi-field):** Tìm đồng thời trên `vi_title`, `vi_prompt`, `category`, `subcategory`, `tags`, `search_keywords_vi`, `model_type`, `difficulty`.
- **Ranking xác định (Deterministic Scoring):** Tiêu đề và từ khóa có trọng số cao hơn nội dung prompt dài.

---

## 2. Đánh giá các giải pháp tìm kiếm (Search Engine Evaluation)

| Tiêu chí | Fuse.js | FlexSearch | MiniSearch | Pre-built Custom Index (Static) |
| :--- | :--- | :--- | :--- | :--- |
| **Kích thước thư viện (gzipped)** | ~12 KB | ~8 KB | **~6 KB** | **0 KB (Thuần JS/Tĩnh)** |
| **Thời gian khởi tạo (2,479 items)** | 60 - 120 ms | 15 - 30 ms | 20 - 40 ms | **0 ms (Instant)** |
| **Độ trễ truy vấn (Query latency)** | 40 - 90 ms | < 2 ms | < 3 ms | **< 1 ms** |
| **Hỗ trợ tiền tố (Prefix search)** | Hạn chế | Tốt | Xuất sắc | Xuất sắc |
| **Khả năng tùy biến tiếng Việt** | Trung bình | Phức tạp | Dễ dàng | **Tuyệt đối tối ưu** |
| **Bộ nhớ RAM trình duyệt** | Cao (~35 MB) | Trung bình (~18 MB)| Thấp (~8 MB) | **Rất thấp (~4 MB)** |

### Quyết định kỹ thuật:
Áp dụng mô hình **Dual-Compatible Architecture**:
1. **Pre-computed Token Map:** Build-time script tạo sẵn `prompts_search.json` (chứa các trường đã chuẩn hóa không dấu `vi_title_clean`, `keywords_clean`, `tags_clean`).
2. **Deterministic Weighted Scoring Algorithm:** Tìm kiếm trực tiếp bằng inverted lookup thuần JS hoặc MiniSearch adapter với 0 network request.

---

## 3. Vietnamese Text Normalization Pipeline

Toàn bộ văn bản đầu vào và câu truy vấn của người dùng đều đi qua pipeline chuẩn hóa:

```
[Input Text: "Trợ lý Viết Content Chuẩn SEO"]
                 |
                 v
1. Unicode NFC Normalization
                 |
                 v
2. Lowercase: "trợ lý viết content chuẩn seo"
                 |
                 v
3. Accent Removal (Tone & Diacritics Folding):
   "a, ă, â -> a", "đ -> d", "e, ê -> e", "o, ô, ơ -> o", "u, ư -> u", "y -> y"
   => "tro ly viet content chuan seo"
                 |
                 v
4. Punctuation & Special Character Stripping
                 |
                 v
5. Tokenization: ["tro", "ly", "viet", "content", "chuan", "seo"]
```

---

## 4. Công thức chấm điểm & Ranking (Scoring Model)

Mỗi tài liệu $D$ được chấm điểm với truy vấn $Q$ theo công thức trọng số:

$$\text{Score}(D, Q) = \sum_{t \in Q} \left( W_{\text{exact\_title}} \cdot \mathbb{I}_{\text{exact}} + 10 \cdot \mathbb{I}_{t \in \text{title}} + 5 \cdot \mathbb{I}_{t \in \text{keywords}} + 4 \cdot \mathbb{I}_{t \in \text{tags}} + 2 \cdot \mathbb{I}_{t \in \text{category}} + 1 \cdot \mathbb{I}_{t \in \text{prompt}} \right)$$

- **Khớp chính xác cụm từ trong Title:** Ưu tiên số 1 (Bonus 25 điểm).
- **Từ khóa / Tags:** Ưu tiên số 2 (Nhóm ý định người dùng).
- **Nội dung Prompt:** Đóng góp điểm cơ sở.
- **Tiêu chí phụ (Tie-breaker):** `quality_status == 'ok'` xếp trước, sau đó sắp xếp theo ID tăng dần để đảm bảo tính tất định (deterministic).

---

## 5. Cấu trúc tệp dữ liệu tìm kiếm (Artifacts)

1. `prompt-viet/data/search/prompts_search.json`:
   - Chứa 2,479 bản ghi thu gọn (bỏ bớt metadata không phục vụ tìm kiếm nhanh như log, source_raw, timestamp).
   - Mỗi item gồm: `id`, `slug`, `vi_title`, `vi_title_clean`, `vi_prompt`, `category`, `subcategory`, `tags`, `search_keywords_vi`, `model_type`, `difficulty`.
2. `prompt-viet/data/search/search_index.json`:
   - Inverted index ánh xạ từ token chuẩn hóa sang danh sách record ID kèm trọng số.
   - Autocomplete dictionary với 500 từ khóa tìm kiếm phổ biến nhất.
