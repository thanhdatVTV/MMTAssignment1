# peer.py

import threading
import requests
import json
import time
import uuid
import os
import sys
from urllib.parse import parse_qs
from daemon.weaprous import WeApRous

# --- Cấu hình ---
if len(sys.argv) < 2:
    print("Lỗi: Cần cung cấp cổng hoạt động.")
    print("Cách dùng: python peer.py <port>")
    sys.exit(1)

MY_IP = "127.0.0.1"
MY_PORT = int(sys.argv[1])
TRACKER_ADDRESS = "127.0.0.1:8000"
DB_DIR = 'db'
SESSION_FILE_PATH = os.path.join(DB_DIR, 'sessions.json')
USERS_FILE_PATH = os.path.join(DB_DIR, 'users.json')

# --- Trạng thái toàn cục của ứng dụng ---
SESSIONS = {}
USERS = {}
chat_messages = []
app = WeApRous()

# --- Lock để bảo vệ tài nguyên chia sẻ, ngăn chặn xung đột luồng ---
chat_lock = threading.Lock()

# ==============================================================================
# PHẦN 1: QUẢN LÝ DỮ LIỆU VÀ PHIÊN ĐĂNG NHẬP (Giữ nguyên)
# ==============================================================================

def save_sessions():
    os.makedirs(DB_DIR, exist_ok=True)
    with open(SESSION_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(SESSIONS, f, indent=4)

def load_data():
    global SESSIONS, USERS
    try:
        with open(SESSION_FILE_PATH, 'r', encoding='utf-8') as f: SESSIONS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): SESSIONS = {}
    try:
        with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f: USERS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"[Lỗi] Không tìm thấy hoặc file '{USERS_FILE_PATH}' không hợp lệ.")
        sys.exit(1)

def read_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return f.read()
    except FileNotFoundError: return "<h1>404 Not Found</h1>", 404

def get_user_from_session(headers):
    cookie_string = headers.get('cookie', '')
    # Nếu framework đổi chữ hoa/thường
    if not cookie_string:
        for k in headers:
            if k.lower() == 'cookie':
                cookie_string = headers[k]
                break

    cookies = {}
    if cookie_string:
        for p in cookie_string.split('; '):
            if '=' in p:
                k, v = p.split('=', 1)
                cookies[k.strip()] = v.strip()

    session_id = cookies.get('session_id')
    print("[DEBUG] cookie_string:", cookie_string)
    print("[DEBUG] session_id:", session_id)
    print("[DEBUG] SESSIONS:", SESSIONS)

    if session_id in SESSIONS:
        return SESSIONS[session_id]
    else:
        print("[WARN] Không tìm thấy session_id trong SESSIONS!")
        return None

# ==============================================================================
# PHẦN 2: LOGIC CLIENT P2P (Giữ nguyên)
# ==============================================================================
def register_with_tracker(username):
    url = f"http://{TRACKER_ADDRESS}/submit-info"
    my_info = {"username": username, "ip": MY_IP, "port": MY_PORT}
    try:
        requests.post(url, json=my_info, timeout=5)
    except requests.exceptions.RequestException:
        pass # Bỏ qua lỗi nếu không kết nối được tracker

def broadcast_message(sender, message):
    url = f"http://{TRACKER_ADDRESS}/get-list"
    try:
        response = requests.get(url, timeout=5)
        known_peers = response.json().get("peers", [])
    except requests.exceptions.RequestException:
        return

    payload = {"sender": sender, "message": message}
    print("payload là",payload)
    for peer in known_peers:
        if peer['port'] == MY_PORT: continue
        peer_url = f"http://{peer['ip']}:{peer['port']}/send-peer"
        print("peer url là",peer_url)
        try:
            requests.post(peer_url, json=payload, timeout=2)
        except requests.exceptions.RequestException:
            pass # Bỏ qua lỗi nếu không gửi được cho 1 peer
# --- NEW: gửi tin nhắn riêng ---
def send_direct_message(sender, target_username, message):
    """Gửi tin nhắn riêng tới 1 peer cụ thể."""
    url = f"http://{TRACKER_ADDRESS}/get-list"
    try:
        response = requests.get(url, timeout=5)
        known_peers = response.json().get("peers", [])
    except requests.exceptions.RequestException:
        print("[ERROR] Không thể truy cập tracker để gửi tin riêng.")
        return

    target_peer = None
    for peer in known_peers:
        if peer['username'] == target_username:
            target_peer = peer
            break

    if not target_peer:
        print(f"[WARN] Không tìm thấy peer '{target_username}'.")
        return

    payload = {"sender": sender, "message": message}
    peer_url = f"http://{target_peer['ip']}:{target_peer['port']}/send-peer"
    print(f"[DEBUG] Gửi tin riêng tới {target_username} qua {peer_url}")
    try:
        requests.post(peer_url, json=payload, timeout=2)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Lỗi khi gửi tin riêng tới {target_username}: {e}")

# ==============================================================================
# PHẦN 3: CÁC ROUTE CỦA MÁY CHỦ WEB (Đã được cập nhật với LOG CHI TIẾT)
# ==============================================================================
@app.route('/', methods=['GET'])
def serve_root(headers, body):
    if get_user_from_session(headers): return read_file_content('www/chat.html'), 200
    return read_file_content('www/login.html'), 200

@app.route('/login', methods=['POST'])
def handle_login(headers, body):
    data = {k: v[0] for k, v in parse_qs(body).items()}
    username, password = data.get('username'), data.get('password')
    print("username và password là:",username,password)
    print ("tên user là",USERS)
    print("password user là",USERS[username]['password'])
    if username in USERS and USERS[username]['password'] == password:
    
        print("vô rồi nè")
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = username
        save_sessions()
        threading.Thread(target=register_with_tracker, args=(username,)).start()
        headers = {'Location': '/', 'Set-Cookie': f'session_id={session_id}; Path=/; HttpOnly'}
        return "", 302, {"headers": headers}
    return "", 302, {"headers": {'Location': '/'}}

@app.route('/logout', methods=['POST'])
def handle_logout(headers, body):
    cookie_string = headers.get('cookie', '')
    cookies = {k.strip(): v.strip() for k, v in (p.split('=', 1) for p in cookie_string.split('; ') if '=' in p)}
    session_id = cookies.get('session_id')
    if session_id in SESSIONS: SESSIONS.pop(session_id); save_sessions()
    headers = {'Location': '/', 'Set-Cookie': 'session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT'}
    return "", 302, {"headers": headers}

# --- API P2P ---
@app.route('/send-peer', methods=['POST'])
def receive_message(headers, body):
    """Nhận tin nhắn trực tiếp từ một peer khác."""
    thread_name = threading.current_thread().name
    
    # --- BẮT ĐẦU SỬA LỖI ---
    # BƯỚC KIỂM TRA QUAN TRỌNG: Nếu body rỗng hoặc chỉ chứa khoảng trắng, bỏ qua.
    if not body or not body.strip():
        print(f"\n[{thread_name}] ⚠️  CẢNH BÁO: Đã nhận một yêu cầu /send-peer với body RỖNG. Bỏ qua.")
        return {"status": "warning", "message": "Empty body received"}, 200 # Trả về thành công để không gây lỗi phía người gửi
    # --- KẾT THÚC SỬA LỖI ---
    
    print(f"\n[{thread_name}] ➡️  Bắt đầu xử lý /send-peer.")
    try:
        data = json.loads(body)
        full_message = f"[{data.get('sender', '?')}] {data.get('message', '')}"
        
        print(f"[{thread_name}] ⏳ Chuẩn bị LẤY KHÓA để ghi tin nhắn...")
        with chat_lock:
            print(f"[{thread_name}] 🔑 ĐÃ LẤY KHÓA. Đang ghi: '{full_message}'")
            chat_messages.append(full_message)
            print(f"[{thread_name}] ✅ Ghi xong. Danh sách tin nhắn hiện tại: {len(chat_messages)} tin.")
        print(f"[{thread_name}] 🔑 ĐÃ NHẢ KHÓA. Hoàn thành /send-peer.")
        
        return {"status": "success"}, 200
    except json.JSONDecodeError as e:
        # Ghi log chi tiết hơn về lỗi JSON
        print(f"[{thread_name}] ❌ LỖI trong /send-peer: Lỗi giải mã JSON - {e}")
        print(f"    -> Dữ liệu nhận được (có thể bị lỗi): {body}")
        return {"status": "error", "message": "Invalid JSON"}, 400
    except Exception as e:
        print(f"[{thread_name}] ❌ LỖI không xác định trong /send-peer: {e}")
        return {"status": "error", "message": "Internal server error"}, 500


# --- API cho Web App ---
@app.route('/get-messages', methods=['GET'])
def get_messages_api(headers, body):
    if not get_user_from_session(headers): return "Unauthorized", 401
    
    with chat_lock:
        messages_copy = list(chat_messages)
        
    return {"messages": messages_copy}, 200

@app.route('/broadcast', methods=['POST'])
def broadcast_api(headers, body):
    thread_name = threading.current_thread().name
    print(f"\n[{thread_name}] ➡️  Bắt đầu xử lý /broadcast.")
    print(f"[DEBUG] Headers nhận được: {headers}")
    username = get_user_from_session(headers)
    print(f"[DEBUG] username = {username}")
    if not username:
        return "Unauthorized", 401
    
    message = json.loads(body).get('message', '')
    if message:
        full_message = f"[{username}]: {message}"
        
        print(f"[{thread_name}] ⏳ Chuẩn bị LẤY KHÓA để ghi tin nhắn broadcast...")
        with chat_lock:
            print(f"[{thread_name}] 🔑 ĐÃ LẤY KHÓA. Đang ghi: '{full_message}'")
            chat_messages.append(full_message)
            print(f"[{thread_name}] ✅ Ghi xong. Danh sách tin nhắn hiện tại: {len(chat_messages)} tin.")
        print(f"[{thread_name}] 🔑 ĐÃ NHẢ KHÓA. Hoàn thành /broadcast.")
        
        threading.Thread(target=broadcast_message, args=(username, message)).start()
    return {"status": "success"}, 200
# --- NEW: API gửi tin riêng ---
@app.route('/send-direct', methods=['POST'])
def send_direct_api(headers, body):
    """API để gửi tin nhắn riêng tới 1 peer cụ thể."""
    username = get_user_from_session(headers)
    if not username:
        return "Unauthorized", 401
    try:
        data = json.loads(body)
        target = data.get('to', '')
        message = data.get('message', '')
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}, 400

    if not target or not message:
        return {"status": "error", "message": "Thiếu người nhận hoặc nội dung"}, 400

    full_message = f"[PM từ {username} ➜ {target}]: {message}"
    with chat_lock:
        chat_messages.append(full_message)

    threading.Thread(target=send_direct_message, args=(username, target, message)).start()
    return {"status": "success"}, 200
# ==============================================================================
# PHẦN 4: KHỞI CHẠY ỨNG DỤNG
# ==============================================================================
if __name__ == "__main__":
    load_data()
    print(f">>> Peer đang khởi động tại http://{MY_IP}:{MY_PORT}")
    app.prepare_address(MY_IP, MY_PORT)
    app.run()