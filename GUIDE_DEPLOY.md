# Hướng dẫn Deploy với Docker

Tài liệu này hướng dẫn cách deploy **Mini Notebook RAG Bot** lên server sử dụng Docker Compose.

---

## Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Chuẩn bị trước khi deploy](#2-chuẩn-bị-trước-khi-deploy)
3. [Cấu trúc Docker](#3-cấu-trúc-docker)
4. [Deploy lần đầu](#4-deploy-lần-đầu)
5. [Quản lý sau deploy](#5-quản-lý-sau-deploy)
6. [Re-indexing](#6-re-indexing)
7. [Persistent Storage](#7-persistent-storage)
8. [Bảo mật](#8-bảo-mật)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Yêu cầu hệ thống

| Thành phần | Tối thiểu | Ghi chú |
|---|---|---|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | v2.20+ | `docker compose version` (lưu ý: không có dấu `-`) |
| RAM | 4 GB | `BAAI/bge-m3` cần ~2 GB khi load |
| Disk | 5 GB | ~1 GB model HuggingFace + ChromaDB data |
| CPU | 2 cores | Model chạy CPU-only (không cần GPU) |

---

## 2. Chuẩn bị trước khi deploy

### 2.1 Clone repo và tạo thư mục data

```bash
git clone <your-repo-url>
cd mini_notebook
mkdir -p data
```

### 2.2 Tạo file `.env`

```bash
cp .env.example .env   # nếu có file mẫu
# hoặc tạo thủ công:
touch .env
```

Điền đầy đủ các biến môi trường vào `.env`:

```env
# ── Bắt buộc ──────────────────────────────────────────────────
GOOGLE_API_KEY=your_google_ai_studio_key_here
DISCORD_TOKEN=your_discord_bot_token_here

# ── Tùy chọn ──────────────────────────────────────────────────
BOT_TYPE=discord                  # hoặc: telegram
CHROMA_COLLECTION=rag_documents   # tên collection trong ChromaDB
```

> **Lấy API key:**
> - `GOOGLE_API_KEY`: [aistudio.google.com](https://aistudio.google.com) → Get API key
> - `DISCORD_TOKEN`: [discord.com/developers/applications](https://discord.com/developers/applications) → Bot → Reset Token

### 2.3 Thêm file PDF

```bash
cp /path/to/your/document.pdf data/
```

Bot sẽ đọc **tất cả file PDF** trong thư mục `data/` khi khởi động lần đầu.

---

## 3. Cấu trúc Docker

Hệ thống gồm **2 container** chạy trong cùng một internal network `rag_net`:

```
docker-compose.yml
├── service: chroma   ← ChromaDB server
│     image: chromadb/chroma:latest
│     volume: chroma_data (named, persistent)
│     port: 8000 (nội bộ — KHÔNG expose ra ngoài)
│
└── service: bot      ← Discord/Telegram bot + embedding model
      build: .  (từ Dockerfile)
      volume: ./data (bind mount, read-only)
      volume: hf_cache (named — cache model HuggingFace)
      depends_on: chroma
```

### Tại sao ChromaDB không expose port?

ChromaDB không có cơ chế xác thực mạnh mặc định. Nếu expose port `8000` ra internet, bất kỳ ai cũng có thể đọc/xóa toàn bộ vector data. Bằng cách chỉ để trong `rag_net`, chỉ container `bot` mới kết nối được qua hostname `chroma`.

### Named Volumes

| Volume | Dùng cho | Mục đích |
|---|---|---|
| `chroma_data` | ChromaDB | Lưu toàn bộ vector index, không mất khi restart |
| `hf_cache` | Bot container | Cache model `BAAI/bge-m3` (~1 GB), tránh re-download |

---

## 4. Deploy lần đầu

```bash
# Bước 1: Build image cho bot container
docker compose build

# Bước 2: Khởi động toàn bộ stack
docker compose up -d

# Bước 3: Theo dõi quá trình khởi động
docker compose logs -f
```

### Quá trình khởi động lần đầu

Lần chạy đầu tiên sẽ mất **3–10 phút** vì:

1. Docker pull image `chromadb/chroma:latest`
2. Bot container download model `BAAI/bge-m3` (~1 GB từ HuggingFace Hub)
3. Bot đọc tất cả PDF trong `data/`, tạo embeddings, ghi vào ChromaDB

Log bình thường sẽ trông như sau:

```
chroma   | Starting ChromaDB server on port 8000...
bot      | [RAG] Bắt đầu đọc PDF và tạo Vector vào ChromaDB...
bot      | [RAG] Đã lưu embedding vào ChromaDB thành công!
bot      | [Discord] Logged in as YourBotName#1234 (ID: 123456789)
bot      | [Discord] Bot is ready and listening for messages.
```

> **Từ lần thứ 2 trở đi:** Model đã được cache trong volume `hf_cache`, ChromaDB đã có data trong `chroma_data` — startup chỉ mất **vài giây**.

---

## 5. Quản lý sau deploy

### Xem trạng thái containers

```bash
docker compose ps
```

### Xem logs theo thời gian thực

```bash
# Tất cả services
docker compose logs -f

# Chỉ xem log bot
docker compose logs -f bot

# Chỉ xem log chromadb
docker compose logs -f chroma
```

### Khởi động lại bot (không restart ChromaDB)

```bash
docker compose restart bot
```

### Dừng toàn bộ stack

```bash
docker compose down
# Data vẫn còn trong named volumes — an toàn
```

### Xóa toàn bộ (kể cả data)

```bash
# ⚠️ CẢNH BÁO: xóa cả volumes — mất toàn bộ vector index!
docker compose down -v
```

### Update code và redeploy

```bash
git pull
docker compose build bot     # chỉ rebuild bot container
docker compose up -d bot     # restart với image mới
```

---

## 6. Re-indexing

### Khi nào cần re-index?

- Thêm hoặc thay thế file PDF trong `data/`
- Muốn xóa tất cả dữ liệu cũ và build lại từ đầu

### Cách re-index

```bash
# Bước 1: Thêm/sửa file PDF
cp new_document.pdf data/

# Bước 2: Xóa collection hiện tại trong ChromaDB
docker compose exec chroma python3 -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
client.delete_collection('rag_documents')
print('Collection deleted.')
"

# Bước 3: Restart bot — sẽ tự động build index mới
docker compose restart bot

# Theo dõi quá trình build index
docker compose logs -f bot
```

> **Lưu ý:** Thay `rag_documents` bằng giá trị `CHROMA_COLLECTION` nếu bạn đã đổi tên.

---

## 7. Persistent Storage

### Data sẽ tồn tại qua các sự kiện sau:

| Sự kiện | Data an toàn? |
|---|---|
| `docker compose restart` | ✅ |
| `docker compose down` rồi `up` | ✅ |
| Reboot server | ✅ |
| `docker compose down -v` | ❌ Mất toàn bộ |
| Xóa thủ công volume `chroma_data` | ❌ Mất vector index |

### Backup vector data

```bash
# Backup
docker run --rm \
  -v mini_notebook_chroma_data:/source:ro \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/chroma_backup_$(date +%Y%m%d).tar.gz -C /source .

# Restore
docker run --rm \
  -v mini_notebook_chroma_data:/target \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/chroma_backup_YYYYMMDD.tar.gz -C /target
```

> **Prefix volume:** Docker Compose tự động thêm tên project làm prefix — mặc định là tên thư mục (`mini_notebook`). Kiểm tra bằng `docker volume ls`.

---

## 8. Bảo mật

### Những gì đã được bảo vệ

- **ChromaDB không có public port** — chỉ accessible trong `rag_net`, không thể truy cập từ internet.
- **`.env` không được commit** — đã có trong `.gitignore`.
- **`data/` mount read-only** — bot container không thể ghi vào thư mục PDF.

### Khuyến nghị thêm cho production

```bash
# Giới hạn resource cho bot container (tránh OOM)
# Thêm vào service bot trong docker-compose.yml:
#   deploy:
#     resources:
#       limits:
#         memory: 3G
```

- Đặt server sau một firewall, chỉ mở port SSH (22) và không port nào khác cho stack này.
- Rotate Discord Token và Google API Key định kỳ.
- Dùng Docker secrets hoặc vault nếu deploy trên Kubernetes/Swarm.

---

## 9. Troubleshooting

### Bot không kết nối được ChromaDB

```bash
# Kiểm tra chroma đang chạy
docker compose ps chroma

# Kiểm tra logs chromadb
docker compose logs chroma

# Test kết nối từ trong bot container
docker compose exec bot python3 -c "
import chromadb
c = chromadb.HttpClient(host='chroma', port=8000)
print('Connected. Collections:', c.list_collections())
"
```

### Model HuggingFace không download được

```bash
# Kiểm tra internet từ container
docker compose exec bot curl -I https://huggingface.co

# Nếu server không có internet, pre-download model vào volume hf_cache
# trên máy có internet trước rồi copy sang server
```

### Container bot bị OOM (Out of Memory)

```bash
# Kiểm tra memory usage
docker stats

# Xem dấu hiệu OOM trong system log
dmesg | grep -i "out of memory"
```

Giải pháp: tăng RAM server hoặc thêm giới hạn memory trong `docker-compose.yml` để tránh ảnh hưởng các service khác.

### Xem version ChromaDB đang chạy

```bash
docker compose exec chroma python3 -c "import chromadb; print(chromadb.__version__)"
```

### Reset toàn bộ và deploy lại từ đầu

```bash
docker compose down -v          # xóa containers + volumes
docker compose build --no-cache # rebuild image sạch
docker compose up -d            # deploy lại
docker compose logs -f          # theo dõi
```
