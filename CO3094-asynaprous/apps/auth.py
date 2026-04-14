import uuid

USERS = {
    "admin": "123",
    "user1": "123"
}

SESSIONS = {}

def validate_user(username, password):
    return USERS.get(username) == password

def create_session(username):
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = username
    return session_id

def parse_cookie(cookie_str):
    cookies = {}
    if not cookie_str:
        return cookies

    for pair in cookie_str.split(";"):
        if "=" in pair:
            key, value = pair.strip().split("=", 1)
            cookies[key] = value

    return cookies

def get_current_user(headers):
    cookie_str = headers.get("cookie", "")
    cookies = parse_cookie(cookie_str)
    session_id = cookies.get("session_id")
    if not session_id:
        return None
    return SESSIONS.get(session_id)

def clear_session(session_id):
    if session_id in SESSIONS:
        del SESSIONS[session_id]