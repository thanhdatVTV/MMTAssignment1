# tracker.py (No changes needed)
import json
import threading
from daemon.weaprous import WeApRous

active_peers = []
peer_lock = threading.Lock()
app = WeApRous()

@app.route('/submit-info', methods=['POST'])
def handle_peer_registration(headers, body):
    try:
        peer_info = json.loads(body)
        with peer_lock:
            if peer_info not in active_peers:
                active_peers.append(peer_info)
                print(f"[Tracker] Registered: {peer_info['username']} at {peer_info['ip']}:{peer_info['port']}")
        return {"status": "success"}, 200
    except Exception:
        return {"status": "error"}, 400

@app.route("/add-list", methods=['POST'])
def handle_add_list(headers, body):
    try:
        data = json.loads(body)
        peers_to_add = data.get("peers", [])
        
        if type(peers_to_add) is not list:
            return {"status": "error", "message": "Dữ liệu phải là 1 list"}, 400
        added_count = 0
        with peer_lock:
            for new_peer in peers_to_add:
                if new_peer not in active_peers:
                    active_peers.append(new_peer)
                    added_count += 1
                    print(f"[Tracker] Đã thêm peer từ add-list: {new_peer.get('username')}")
                
        return {"status": "success", "message": f"Đã thêm thành công {added_count} peer mới"}, 200
    except json.JSONDecodeError:
        return {"status": "error", "message": "JSON không hợp lệ"}, 400
    except Exception as e:
        print(f"[Tracker] Lỗi trong /add-list: {e}")
        return {"status": "error", "message": "Lỗi nội bộ server"}, 500


@app.route('/get-list', methods=['GET'])
def get_active_peers(headers, body):
    """Trả về danh sách các peer đang hoạt động, kèm header CORS để cho phép fetch từ port khác."""
    with peer_lock:
        peers_data = {"peers": list(active_peers)}
        return peers_data, 200, {
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # ✅ Cho phép mọi origin (fix lỗi CORS)
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }


if __name__ == "__main__":
    TRACKER_IP = "127.0.0.1"
    TRACKER_PORT = 8000
    print(f"Tracker Server starting on http://{TRACKER_IP}:{TRACKER_PORT}")
    app.prepare_address(TRACKER_IP, TRACKER_PORT)
    app.run()