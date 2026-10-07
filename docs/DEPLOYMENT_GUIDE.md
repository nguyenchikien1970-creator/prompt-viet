# Hướng Dẫn Deploy Nền Tảng Web Prompt Việt (Static-First)

Tài liệu này hướng dẫn chi tiết quy trình kiểm thử và deploy website **Prompt Việt** lên các hạ tầng CDN tĩnh (Zero Cost, High Availability, Global Edge).

---

## 1. Kiến Trúc Triển Khai (Overview)

Website **Prompt Việt** tuân thủ hoàn toàn kiến trúc **Static-First**:
- **Source root**: `prompt-viet/web/`
- **Entry point**: `prompt-viet/web/index.html`
- **Data assets**: `prompt-viet/web/data/` (`prompts_cards.json`, `prompts_search.json`, `search_index.json`)
- **Backend / Database**: **None** (Hoàn toàn chạy client-side in-memory index trên trình duyệt, không yêu cầu database, không phát sinh chi phí vận hành server).

---

## 2. Kiểm Thử Cục Bộ (Local Preview)

Để chạy preview trên máy cục bộ trước khi deploy:

### Cách 1: Sử dụng Python HTTP Server
```bash
cd prompt-viet/web
python3 -m http.server 8080
```
Truy cập trình duyệt: `http://localhost:8080`

### Cách 2: Sử dụng Node.js `npx serve`
```bash
npx serve prompt-viet/web -l 8080
```

---

## 3. Triển Khai Lên Vercel (Khuyến Nghị)

Vercel cung cấp Global Edge Network với hỗ trợ HTTP/2, Brotli compression và SSL tự động.

### Deploy qua Vercel CLI:
```bash
# Cài đặt Vercel CLI (nếu chưa có)
npm i -g vercel

# Điều hướng vào thư mục web và deploy
cd prompt-viet/web
vercel --prod
```
*Ghi chú:* File `vercel.json` đã được cấu hình sẵn với security headers và cache-control tối ưu cho thư viện JSON.

### Deploy qua GitHub Git Integration:
1. Push repository lên GitHub.
2. Tại dashboard [vercel.com](https://vercel.com): **Add New Project** -> Chọn repo.
3. Thiết lập:
   - **Root Directory**: `prompt-viet/web`
   - **Build Command**: Để trống (Static HTML)
   - **Output Directory**: `.`
4. Bấm **Deploy**.

---

## 4. Triển Khai Lên Cloudflare Pages

Cloudflare Pages miễn phí băng thông không giới hạn và tốc độ truy cập tại Việt Nam cực nhanh thông qua PoP Viettel/VNPT/FPT.

### Deploy qua Cloudflare Wrangler CLI:
```bash
# Cài đặt wrangler
npm i -g wrangler

# Deploy trực tiếp thư mục web
wrangler pages deploy prompt-viet/web --project-name=prompt-viet
```
*Ghi chú:* File `_headers` đã được cấu hình sẵn cho Cloudflare Pages.

### Deploy qua Git:
1. Kết nối kho Git với Cloudflare Dashboard > Workers & Pages.
2. Build settings:
   - **Framework preset**: None
   - **Build output directory**: `prompt-viet/web`
3. Nhấn **Save and Deploy**.

---

## 5. Triển Khai Lên GitHub Pages

1. Vào **Settings** của GitHub Repository > **Pages**.
2. Chọn **Source**: Deploy from a branch hoặc cấu hình GitHub Action workflow:
```yaml
name: Deploy Prompt Viet to GitHub Pages
on:
  push:
    branches: [main]
    paths:
      - 'prompt-viet/web/**'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./prompt-viet/web
```

---

## 6. Checklist Kiểm Thử Sau Khi Deploy (Production Smoke Test)

1. **Asset Loading:** Mở Network tab, xác nhận `index.html`, `style.css`, `app.js`, `prompts_cards.json`, `search_index.json` trả về mã HTTP `200`.
2. **Instant Search:**
   - Gõ "content seo" -> kết quả xuất hiện trong < 50ms.
   - Gõ tiếng Việt có dấu: "lập trình viên" -> kết quả chính xác.
   - Gõ không dấu: "lap trinh vien" -> cùng tập kết quả.
3. **Bộ lọc Facet:**
   - Chọn Category -> Subcategory tự động filter tương ứng.
   - Chọn Difficulty / Model -> Thẻ bài viết cập nhật tức thì.
4. **Copy Button:**
   - Bấm nút "Sao chép Prompt" -> Toast thông báo hiển thị "Đã sao chép vào bộ nhớ tạm!".
   - Paste vào clipboard -> Nội dung prompt đầy đủ.
5. **Detail Modal:**
   - Bấm vào thẻ bất kỳ -> Modal popup chi tiết hiển thị toàn bộ nội dung prompt tiếng Việt, prompt gốc tiếng Anh, giải thích, tags, model type.
