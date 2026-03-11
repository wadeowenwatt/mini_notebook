# Hướng dẫn Cấu hình Zalo Official Account (Zalo OA) với Webhook Server Local

Tài liệu này hướng dẫn chi tiết các bước để kết nối ứng dụng Mini Notebook của bạn với tài khoản Zalo OA thật, cho phép RAG engine tự động trả lời tin nhắn của người dùng qua Zalo.

---

## 🚀 Bước 1: Khởi động server và tạo Public URL

Zalo yêu cầu Webhook URL phải là **HTTPS** và có thể truy cập được từ internet. Vì server của bạn đang chạy ở `localhost:8000`, ta cần dùng `ngrok` (hoặc Cloudflare Tunnels) để tạo đường hầm (tunnel).

1. Cài đặt **ngrok**: (Tham khảo: [ngrok.com/download](https://ngrok.com/download))
   - Trên macOS: `brew install ngrok/ngrok/ngrok`
2. Đăng ký tài khoản ngrok và chạy lệnh xác thực (AuthToken) mà họ cung cấp:
   ```bash
   ngrok config add-authtoken <your_auth_token>
   ```
3. Chạy lệnh expose port 8000:
   ```bash
   ngrok http 8000
   ```
4. Copy lại đường link **Forwarding** (ví dụ: `https://abcd-123.ngrok-free.app`).
   - Webhook URL hoàn chỉnh dự kiến sẽ là: `https://abcd-123.ngrok-free.app/webhook`

---

## 📦 Bước 2: Đăng ký ứng dụng trên Zalo For Developers

1. Truy cập [Zalo for Developers](https://developers.zalo.me/).
2. Đăng nhập bằng tài khoản Zalo cá nhân của bạn.
3. Ở góc phải phía trên, nhấn **Thêm mới ứng dụng** (Create App).
4. Điền các thông tin:
   - **Tên cấu hình**: (Tuỳ chọn, ví dụ: "Mini Notebook AI")
   - **Mục đích**: Chọn mục đích phù hợp (Ví dụ: "Học tập / Nghiên cứu").
5. Nhấn **Khởi tạo ID ứng dụng**. Bạn lưu lại **App ID** được tạo ra.

---

## 🔗 Bước 3: Cấp quyền (Authorize) Zalo OA cho Ứng dụng

\*Lưu ý: Bạn cần có (hoặc tạo) một Zalo Official Account (Zalo OA). Truy cập [oa.zalo.me](https://oa.zalo.me/) để tạo.\*\*

1. Trong trang quản lý Ứng dụng trên Zalo Developers (ở Bước 2), chọn mục **Sản phẩm liên kết** (Linked Products) ở menu bên trái.
2. Chọn loại sản phẩm: **Zalo Official Account**.
3. Nút **Liên kết** sẽ hiện ra, bạn nhấn vào và dán ID của Zalo OA muốn liên kết (hoặc tìm kiếm OA nếu tài khoản Zalo cá nhân của bạn đang là Quản trị viên của OA đó).
4. Bật API cho ứng dụng:
   - Nhấn vào mục **Xét duyệt tính năng** (API review) ở menu.
   - Tìm quyền **Gửi tin nhắn (Zalo Notification Service/OA)** và nhấn xin cấp quyền (nếu cần).
   - Với OA đăng ký dùng thử / dev, bạn có thể gọi API ngay lập tức mà không cần duyệt.

### Quan trọng: Xin quyền API (API Permissions)

Đi tới **Cài đặt** -> **Quản lý quyền API**. Đảm bảo các quyền này được bật:

- `Cấu hình Webhook OA`
- `Gửi tin nhắn ZNS / OA`
- `Oa.message.read` (Đọc tin nhắn gửi đến OA)
- `Oa.message.send` (Gửi tin nhắn từ OA)

---

## 🔑 Bước 4: Lấy Access Token

Để server của bạn có quyền gửi tin nhắn, nó cần `ZALO_OA_ACCESS_TOKEN`.

1. Trở lại menu chính bên trái trong Zalo Developers, chọn **Công cụ** (Tools) -> **API Explorer**.
2. Tại phần **Cấu hình app / OA** phía bên phải:
   - Chọn **Ứng dụng** (App) bạn vừa tạo ở Bước 2.
   - Chọn **Official Account** bạn đã liên kết ở Bước 3.
3. Bấm **Lấy Access Token**.
4. Zalo sẽ hiển thị một thông báo Yêu cầu cho phép ứng dụng truy cập nội dung OA $\rightarrow$ Nhấn **Đồng ý**.
5. Giao diện xuất hiện mã **Access Token** (Rất dài).
6. Copy mã Access Token này.

### Cập nhật `.env`:

Mở file `.env` trong project, dán token vào biến đã cấu hình:

```env
GOOGLE_API_KEY=AIzaSy...
ZALO_OA_ACCESS_TOKEN=cái_chuỗi_dài_ngoằng_bạn_vừa_copy_ở_đây
```

---

## 🌐 Bước 5: Cấu hình Webhook URL trên Zalo

1. Trở lại trang ứng dụng bên Zalo For Developers.
2. Tại menu bên trái, mở rộng mục **Official Account** và chọn **Webhook**.
3. Dán Webhook URL đầy đủ từ `ngrok` (có `/webhook` ở đuôi):
   ```
   https://abcd-123.ngrok-free.app/webhook
   ```
4. Ở phần **Sự kiện Webhook (Webhook Events)** bên dưới, hãy đánh dấu tick (bật) cho sự kiện:
   - **Người dùng gửi tin nhắn văn bản tới OA** (`user_send_text`)
5. Nhấn **Xác nhận / Lưu cài đặt**.

_(Optional: Nhấn nút **Kiểm tra / Test** nếu Zalo cung cấp, để đảm bảo Zalo ping về `ngrok` và trả về `HTTP 200 OK`)_

---

## 🎯 Bước 6: Kiểm tra toàn hệ thống (End-to-End Test)

1. Đảm bảo server đang chạy không có lỗi (Restart lại server sau khi thay đổi file `.env`):
   ```bash
   .venv/bin/python main.py
    # Hoặc
   .venv/bin/python -m uvicorn webhook:app --host 0.0.0.0 --port 8000
   ```
2. Đảm bảo `ngrok` vẫn đang trỏ đúng url.
3. **Mở điện thoại**, vào Zalo cá nhân.
4. Tìm trang Zalo Official Account của bạn, nhấn **Quan tâm**.
5. Nhắn một câu hỏi cho OA, ví dụ: `"Luật đất đai có phạm vi điều chỉnh là gì?"`
6. Nhìn vào cửa sổ Terminal đang chạy Server, bạn sẽ thấy log:
   ```
   [Webhook] Nhận event: user_send_text
   [Webhook] User '123456789' hỏi: 'Luật đất đai có phạm vi điều chỉnh là gì?'
   [RAG] Query: 'Luật đất đai có phạm vi điều chỉnh là gì?'
   ...
   [Zalo] Gửi tin nhắn thành công tới user 123456789.
   ```
7. Tiếng _ting_ vang lên, Zalo OA sẽ tự động nhắn lại câu trả lời được xử lý bởi LlamaIndex RAG! 🎉

---

### Lưu ý quan trọng

- **Access Token hết hạn:** Zalo OA Access Token mặc định do API Explorer tạo ra thường chỉ có thời hạn ngắn (vài tiếng đến 1 ngày). Khi đưa lên môi trường thật (Production), bạn cần viết thêm logic dùng **Refresh Token** để tự gọi API lấy `Access Token` mới.
- **ngrok URL thay đổi:** Nếu bạn tắt/bật lại ngrok bản miễn phí, URL sẽ thay đổi, bạn phải lên Zalo Developer gắn lại Webhook URL.
