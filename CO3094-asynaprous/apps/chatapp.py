
import json
import threading
from daemon import AsynapRous
from apps.auth import validate_user, create_session, get_current_user

app = AsynapRous()


_lock   = threading.Lock()
PEERS   = {}   
CHANNELS = {}  


#  Helper
def _json_ok(data: dict, status: int = 200):
    return json.dumps(data), status, {"Content-Type": "application/json"}

def _json_err(msg: str, status: int = 400):
    return json.dumps({"error": msg}), status, {"Content-Type": "application/json"}


@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Authenticate user and return a session cookie.

    Request body (JSON):
        { "username": str, "password": str }

    Response:
        200 + Set-Cookie: session_id=<id>
        401 if credentials are wrong
    """
    try:
        data     = json.loads(body)
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not validate_user(username, password):
            return _json_err("Invalid credentials", 401)

        session_id = create_session(username)
        return (
            json.dumps({"message": "Login success", "username": username}),
            200,
            {
                "Content-Type": "application/json",
                "Set-Cookie": "session_id={}; Path=/; HttpOnly".format(session_id),
            },
        )
    except Exception as e:
        print("[ChatApp] login error: {}".format(e))
        return _json_err("Bad request", 400)


#  2. POST /submit-info  — peer registration
@app.route('/submit-info', methods=['POST'])
def submit_info(headers="guest", body=""):
    """
    Register a peer's IP and port with the tracker.

    Request body (JSON):
        { "ip": str, "port": int }

    Cookie: session_id=<id>   (must be logged in)
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    try:
        data = json.loads(body)
        ip   = data.get("ip")
        port = int(data.get("port", 0))

        if not ip or not port:
            return _json_err("ip and port required", 400)

        with _lock:
            PEERS[username] = {"ip": ip, "port": port, "online": True}

        print("[ChatApp] Peer registered: {} @ {}:{}".format(username, ip, port))
        return _json_ok({"message": "Registered", "username": username, "ip": ip, "port": port})

    except Exception as e:
        print("[ChatApp] submit-info error: {}".format(e))
        return _json_err("Bad request", 400)


#  3. GET /get-list  — peer discovery
@app.route('/get-list', methods=['GET'])
def get_list(headers="guest", body=""):
    """
    Return the list of currently registered peers.

    Cookie: session_id=<id>   (must be logged in)

    Response (JSON):
        { "peers": { username: { ip, port, online }, ... } }
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    with _lock:
        # Return all peers except caller
        peer_list = {
            u: info
            for u, info in PEERS.items()
            if u != username
        }

    return _json_ok({"peers": peer_list})


#  4. POST /add-list  — join / create channel

@app.route('/add-list', methods=['POST'])
def add_list(headers="guest", body=""):
    """
    Add the current user to a channel (create if not exists).

    Request body (JSON):
        { "channel": str }

    Cookie: session_id=<id>
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    try:
        data    = json.loads(body)
        channel = data.get("channel", "").strip()

        if not channel:
            return _json_err("channel name required", 400)

        with _lock:
            if channel not in CHANNELS:
                CHANNELS[channel] = []
            if username not in CHANNELS[channel]:
                CHANNELS[channel].append(username)

        print("[ChatApp] {} joined channel '{}'".format(username, channel))
        return _json_ok({"message": "Joined", "channel": channel, "members": CHANNELS[channel]})

    except Exception as e:
        print("[ChatApp] add-list error: {}".format(e))
        return _json_err("Bad request", 400)



#  5. GET /channel-list  — list channels

@app.route('/channel-list', methods=['GET'])
def channel_list(headers="guest", body=""):
    """
    Return all channels and their member lists.

    Cookie: session_id=<id>
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    with _lock:
        data = {ch: members[:] for ch, members in CHANNELS.items()}

    return _json_ok({"channels": data})



#  6. POST /connect-peer  — get info for a specific peer

@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers="guest", body=""):
    """
    Return IP/port of a specific peer so caller can open a direct P2P connection.

    Request body (JSON):
        { "target": str }   ← target username

    Cookie: session_id=<id>
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    try:
        data   = json.loads(body)
        target = data.get("target", "").strip()

        if not target:
            return _json_err("target required", 400)

        with _lock:
            peer = PEERS.get(target)

        if not peer:
            return _json_err("Peer '{}' not found".format(target), 404)

        return _json_ok({"target": target, "ip": peer["ip"], "port": peer["port"]})

    except Exception as e:
        print("[ChatApp] connect-peer error: {}".format(e))
        return _json_err("Bad request", 400)



#  7. POST /broadcast-peer  — broadcast via tracker


MESSAGES = {}  

@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers="guest", body=""):
    """
    Store a broadcast message in the channel (tracker relays).
    In Client-Server paradigm the server is the single relay point.

    Request body (JSON):
        { "channel": str, "message": str }

    Cookie: session_id=<id>
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    try:
        import time
        data    = json.loads(body)
        channel = data.get("channel", "").strip()
        text    = data.get("message", "").strip()

        if not channel or not text:
            return _json_err("channel and message required", 400)

        entry = {"from": username, "text": text, "ts": int(time.time())}

        with _lock:
            if channel not in MESSAGES:
                MESSAGES[channel] = []
            MESSAGES[channel].append(entry)

        print("[ChatApp] Broadcast [{}] {}: {}".format(channel, username, text))
        return _json_ok({"message": "Sent", "entry": entry})

    except Exception as e:
        print("[ChatApp] broadcast-peer error: {}".format(e))
        return _json_err("Bad request", 400)



#  8. POST /send-peer  — direct message (stored at tracker)

DM = {}  

@app.route('/send-peer', methods=['POST'])
def send_peer(headers="guest", body=""):
    """
    Send a direct message to another peer (stored at tracker for pickup).

    Request body (JSON):
        { "to": str, "message": str }

    Cookie: session_id=<id>
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    try:
        import time
        data = json.loads(body)
        to   = data.get("to", "").strip()
        text = data.get("message", "").strip()

        if not to or not text:
            return _json_err("to and message required", 400)

        key   = "{}:{}".format(username, to)
        entry = {"from": username, "to": to, "text": text, "ts": int(time.time())}

        with _lock:
            if key not in DM:
                DM[key] = []
            DM[key].append(entry)

        print("[ChatApp] DM {} → {}: {}".format(username, to, text))
        return _json_ok({"message": "Sent", "entry": entry})

    except Exception as e:
        print("[ChatApp] send-peer error: {}".format(e))
        return _json_err("Bad request", 400)



#  9. GET /messages  — poll messages in a channel

@app.route('/messages', methods=['GET'])
def get_messages(headers="guest", body=""):
    """
    Fetch all stored messages for a channel.
    Client polls this endpoint to receive new messages (short-polling).

    Query-style: pass channel in body JSON  { "channel": str }
    Cookie: session_id=<id>
    """
    username = get_current_user(headers)
    if not username:
        return _json_err("Unauthorized", 401)

    try:
        # body may be empty for GET; fall back to empty channel → return all
        channel = ""
        if body:
            try:
                channel = json.loads(body).get("channel", "")
            except Exception:
                pass

        with _lock:
            if channel:
                msgs = MESSAGES.get(channel, [])
            else:
                # flatten all channels
                msgs = [m for ml in MESSAGES.values() for m in ml]

        return _json_ok({"channel": channel, "messages": msgs})

    except Exception as e:
        print("[ChatApp] get-messages error: {}".format(e))
        return _json_err("Bad request", 400)



#  Entry point

def create_chatapp(ip, port):
    """Launch the chat tracker server."""
    app.prepare_address(ip, port)
    app.run()
