## Hướng dẫn cài đặt và khởi chạy

Để thuận tiện cho việc kiểm thử và đánh giá hệ thống mạng thực tế, dưới đây là
tài liệu hướng dẫn các bước chi tiết để khởi chạy toàn bộ mô hình Hybrid Chat
(Client-Server kết hợp P2P).

---

### Bước 1: Yêu cầu môi trường

- Hệ thống yêu cầu cài đặt Python 3.7 trở lên.
- Cài đặt thư viện `requests` (sử dụng cho tiến trình P2P Gateway của client).
  Mở Terminal và chạy lệnh:

pip install requests


---

### Bước 2: Khởi chạy Tracker Server (Máy chủ trung tâm)

- Mở Terminal tại thư mục gốc của dự án.
- Thực thi lệnh khởi chạy backend server ở port mặc định (8005):

python start_chatapp.py --server-port 8005


---

### Bước 3: Khởi chạy các tiến trình Peer Gateway

- Mở các tab Terminal mới (giữ nguyên Terminal của Tracker Server).
- Khởi chạy Gateway cho từng client ở các port độc lập (ví dụ: 9001 và 9002):

# Terminal cho Peer 1
python peer.py --port 9001

# Terminal cho Peer 2
python peer.py --port 9002


---

### Bước 4: Truy cập giao diện và Kiểm thử P2P Chat

- Mở trình duyệt web (khuyến nghị mở 2 cửa sổ song song hoặc dùng tab Ẩn danh
  cho tài khoản thứ hai) và truy cập vào các Gateway:
  - Giao diện Peer 1: http://127.0.0.1:9001/login
  - Giao diện Peer 2: http://127.0.0.1:9002/login

- Đăng nhập bằng các tài khoản kiểm thử đã được thiết lập sẵn trong auth.py
  (ví dụ: admin với mật khẩu 123, hoặc user1 với mật khẩu 123).

- Sau khi kết nối thành công, hệ thống sẽ báo log xanh và các peer có thể bắt
  đầu nhắn tin trực tiếp để kiểm chứng cơ chế Non-blocking và Short-polling.
