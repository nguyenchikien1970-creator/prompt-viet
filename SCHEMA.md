# CHUẨN SCHEMA DỮ LIỆU PROMPT VIỆT

Tài liệu này quy định cấu trúc dữ liệu chính thức, ý nghĩa các trường, kiểu dữ liệu trong cơ sở dữ liệu (PostgreSQL / Supabase) và các trạng thái vòng đời của một prompt trong toàn bộ dự án **Prompt Việt**.

---

## 1. Định nghĩa chi tiết các trường (Fields Specification)

| Trường (Field) | Kiểu dữ liệu (Supabase / JSON) | Bắt buộc | Giá trị mặc định trước khi dịch | Giải thích & Quy tắc |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `TEXT` (Primary Key) | Có | *(Lấy từ gốc)* | Mã định danh duy nhất của prompt từ `prompts.chat` (giữ nguyên không đổi). |
| `slug` | `TEXT` (Unique) | Có | `null` | Đường dẫn tĩnh thân thiện SEO cho website (được AI tạo ra từ `vi_title` ở bước enrich/dịch). |
| `original_title` | `TEXT` | Có | *(Lấy từ gốc)* | Tiêu đề gốc của prompt. |
| `original_prompt` | `TEXT` | Có | *(Lấy từ gốc)* | Toàn văn câu lệnh gốc, giữ nguyên định dạng Markdown, biến số, code block. |
| `language_original` | `TEXT` | Không | `null` | Ngôn ngữ gốc của prompt (`en`, `fr`, `es`, `am`... hoặc `null` nếu không chắc chắn). |
| `language_detection` | `TEXT` | Có | `"unknown"` | Phương thức xác định ngôn ngữ: `"source"` \| `"rule_based"` \| `"ai"` \| `"unknown"`. |
| `vi_title` | `TEXT` | Không | `null` | Tiêu đề dịch tiếng Việt tự nhiên, chuẩn văn phong tiếng Việt (bổ sung khi dịch). |
| `vi_prompt` | `TEXT` | Không | `null` | Nội dung câu lệnh dịch tiếng Việt (bảo toàn biến, code, link, Markdown). |
| `translation_status` | `TEXT` | Có | `"pending"` | Trạng thái dịch: `"pending"` \| `"translated"` \| `"reviewed"` \| `"failed"`. |
| `source_category` | `TEXT` | Không | *(Lấy từ gốc)* | Phân loại gốc nguyên bản lấy từ `prompts.chat` (kể cả `null`). Không bao giờ bị ghi đè. |
| `source_tags` | `TEXT[]` (Mảng chuỗi) | Có | *(Lấy từ gốc)* | Các thẻ tags nguyên bản lấy từ `prompts.chat` (kể cả `[]`). Không bao giờ bị ghi đè. |
| `category` | `TEXT` | Không | `null` | Phân loại chuẩn hóa cho website Prompt Việt (được AI bổ sung ở bước enrich). |
| `subcategory` | `TEXT` | Không | `null` | Ngành ngách chuyên sâu cho website (được AI bổ sung ở bước enrich). |
| `tags` | `TEXT[]` (Mảng chuỗi) | Có | `[]` | Mảng 3–8 tags chuẩn hóa phục vụ bộ lọc tìm kiếm trên website Prompt Việt. |
| `search_keywords_vi` | `TEXT[]` (Mảng chuỗi) | Có | `[]` | Các từ khóa tìm kiếm tiếng Việt phổ biến, từ đồng nghĩa hỗ trợ tìm kiếm. |
| `use_case` | `TEXT` | Không | `null` | 1–2 câu giải thích: *Prompt này dùng khi nào, giải quyết bài toán gì cho người dùng*. |
| `model_type` | `TEXT[]` (Mảng chuỗi) | Có | `["text"]` | Loại hình model AI phù hợp: `["text"]`, `["image"]`, `["video"]`, `["coding"]`... |
| `difficulty` | `TEXT` | Không | `null` | Độ phức tạp: `"beginner"` \| `"intermediate"` \| `"advanced"` \| `null`. |
| `quality_status` | `TEXT` | Có | `"unreviewed"` | Trạng thái chất lượng: `"unreviewed"` \| `"ok"` \| `"needs_review"`. |
| `author` | `JSONB` hoặc `TEXT` | Có | *(Lấy từ gốc)* | Thông tin tác giả gốc `{ "name", "username", "avatar" }` để tôn trọng bản quyền cộng đồng. |
| `source` | `TEXT` | Có | `"prompts.chat"` | Nguồn gốc dữ liệu (`"prompts.chat"`). |
| `source_url` | `TEXT` | Có | Tự động tạo | Đường link đối chiếu đến bài đăng gốc trên website `prompts.chat`. |
| `created_at` | `TIMESTAMPTZ` | Có | *(Lấy từ gốc)* | Thời gian khởi tạo bản ghi gốc (chuỗi ISO 8601). |

---

## 2. Vòng đời dữ liệu (Lifecycle States)

### Trạng thái dịch (`translation_status`):
* `pending`: Mới nạp từ dữ liệu gốc, chưa dịch (`vi_title` và `vi_prompt` là `null`).
* `translated`: Đã được biên dịch và làm giàu dữ liệu (enrichment) hoàn chỉnh.
* `reviewed`: Đã được con người kiểm tra chất lượng trước khi phát hành.
* `failed`: Gặp sự cố trong quá trình dịch thuật.

### Trạng thái phát hiện ngôn ngữ (`language_detection`):
* `source`: Nguồn dữ liệu gốc có sẵn metadata ngôn ngữ.
* `rule_based`: Xác định thông qua bộ quy tắc từ khóa / chữ cái (heuristic).
* `ai`: Mô hình AI xác định trong quá trình xử lý.
* `unknown`: Không chắc chắn hoặc văn bản quá ngắn/hỗn hợp (`language_original = null`).

### Trạng thái chất lượng (`quality_status`):
* `unreviewed`: Trạng thái ban đầu trước khi duyệt/dịch.
* `ok`: Prompt rõ ràng, hữu ích, đạt chuẩn cao để cộng đồng sử dụng.
* `needs_review`: Prompt kém chất lượng, cụt ngủn, mang tính spam hoặc chứa thông tin cá nhân/quảng cáo địa phương.

---

## 3. Ví dụ JSON mẫu (Giai đoạn NORMALIZE - Chưa dịch & Chưa Enrich)

```json
{
  "id": "cmutiu2p60001l404w65ruxpr",
  "slug": "steampunk-reading-nook-inside-a-living-oak",
  "original_title": "Steampunk Reading Nook Inside a Living Oak",
  "original_prompt": "Warm illustrated fantasy interior: a steampunk reading nook carved into the hollow heartwood of a giant living oak...",
  "language_original": "en",
  "language_detection": "rule_based",
  "vi_title": null,
  "vi_prompt": null,
  "translation_status": "pending",
  "source_category": "Image Generation",
  "source_tags": [],
  "category": null,
  "subcategory": null,
  "tags": [],
  "search_keywords_vi": [],
  "use_case": null,
  "model_type": ["image"],
  "difficulty": null,
  "quality_status": "unreviewed",
  "author": {
    "name": "Fatih Kadir Akın",
    "username": "f",
    "avatar": "https://avatars.githubusercontent.com/u/768052?v=4"
  },
  "source": "prompts.chat",
  "source_url": "https://prompts.chat/p/steampunk-reading-nook-inside-a-living-oak",
  "created_at": "2024-03-15T08:20:00Z"
}
```

---

## 4. Cấu hình bảng dữ liệu trong Supabase / PostgreSQL

```sql
CREATE TABLE IF NOT EXISTS public.prompts (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE,
  original_title TEXT NOT NULL,
  original_prompt TEXT NOT NULL,
  language_original TEXT,
  language_detection TEXT NOT NULL DEFAULT 'unknown',
  vi_title TEXT,
  vi_prompt TEXT,
  translation_status TEXT NOT NULL DEFAULT 'pending',
  source_category TEXT,
  source_tags TEXT[] DEFAULT '{}',
  category TEXT,
  subcategory TEXT,
  tags TEXT[] DEFAULT '{}',
  search_keywords_vi TEXT[] DEFAULT '{}',
  use_case TEXT,
  model_type TEXT[] DEFAULT '{"text"}',
  difficulty TEXT,
  quality_status TEXT NOT NULL DEFAULT 'unreviewed',
  author JSONB,
  source TEXT NOT NULL DEFAULT 'prompts.chat',
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chỉ mục
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_slug ON public.prompts(slug) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_prompts_cat_subcat ON public.prompts(category, subcategory);
CREATE INDEX IF NOT EXISTS idx_prompts_source_cat ON public.prompts(source_category);
CREATE INDEX IF NOT EXISTS idx_prompts_translation_status ON public.prompts(translation_status);
CREATE INDEX IF NOT EXISTS idx_prompts_quality_status ON public.prompts(quality_status);
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON public.prompts USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_prompts_source_tags ON public.prompts USING gin(source_tags);
CREATE INDEX IF NOT EXISTS idx_prompts_search_keywords_vi ON public.prompts USING gin(search_keywords_vi);
CREATE INDEX IF NOT EXISTS idx_prompts_model_type ON public.prompts USING gin(model_type);
```
