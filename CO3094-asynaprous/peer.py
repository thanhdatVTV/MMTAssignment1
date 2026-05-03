
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_HTML_PATH = os.path.join(BASE_DIR, 'www', 'chat.html')

STATE_LOCK = threading.Lock()
STATE = {
    'tracker': 'http://127.0.0.1:8005',
    'gateway_host': '127.0.0.1',
    'gateway_port': 9001,
    'peer_started': False,
    'username': None,
    'session': None,
}


def json_response(handler, status, payload):
    body = json.dumps(payload).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler, status, body, content_type='text/plain; charset=utf-8'):
    if isinstance(body, str):
        body = body.encode('utf-8')
    handler.send_response(status)
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Content-Type', content_type)
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def load_chat_html():
    with open(CHAT_HTML_PATH, 'rb') as f:
        return f.read()


def get_session():
    with STATE_LOCK:
        return STATE['session']


def set_login_state(username, session_obj):
    with STATE_LOCK:
        STATE['username'] = username
        STATE['session'] = session_obj
        STATE['peer_started'] = True


def clear_login_state():
    with STATE_LOCK:
        STATE['username'] = None
        STATE['session'] = None
        STATE['peer_started'] = False


def get_state_snapshot():
    with STATE_LOCK:
        return {
            'tracker': STATE['tracker'],
            'gateway_host': STATE['gateway_host'],
            'gateway_port': STATE['gateway_port'],
            'peer_started': STATE['peer_started'],
            'username': STATE['username'],
        }


def normalize_tracker_url(raw: str) -> str:
    raw = (raw or '').strip().rstrip('/')
    if not raw:
        raw = 'http://127.0.0.1:8005'
    if not raw.startswith(('http://', 'https://')):
        raw = 'http://' + raw
    return raw


def tracker_url(path: str) -> str:
    with STATE_LOCK:
        base = STATE['tracker'].rstrip('/')
    return f'{base}{path}'


def login_to_tracker(username: str, password: str):
    sess = requests.Session()
    resp = sess.post(
        tracker_url('/login'),
        json={'username': username, 'password': password},
        timeout=8,
    )
    if resp.status_code != 200:
        try:
            data = resp.json()
        except Exception:
            data = {'error': resp.text}
        return False, data.get('error', 'login failed')

    with STATE_LOCK:
        host = STATE['gateway_host']
        port = STATE['gateway_port']

    reg = sess.post(
        tracker_url('/submit-info'),
        json={'ip': host, 'port': port},
        timeout=8,
    )
    if reg.status_code != 200:
        try:
            data = reg.json()
        except Exception:
            data = {'error': reg.text}
        return False, data.get('error', 'register failed')

    set_login_state(username, sess)
    return True, None


class PeerHandler(BaseHTTPRequestHandler):
    server_version = 'PeerGateway/1.1'

    def log_message(self, format, *args):
        print('[PeerGateway]', format % args)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', '0') or '0')
        raw = self.rfile.read(length) if length > 0 else b'{}'
        if not raw:
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ['/', '/login']:
            try:
                html = load_chat_html()
                text_response(self, 200, html, 'text/html; charset=utf-8')
            except FileNotFoundError:
                text_response(self, 404, 'chat.html not found')
            return

        if path in ['/status', '/p2p/state']:
            json_response(self, 200, get_state_snapshot())
            return

        if path in ['/get-list', '/p2p/peers']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            try:
                resp = sess.get(tracker_url('/get-list'), timeout=8)
                data = resp.json()
                json_response(self, resp.status_code, data)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        if path in ['/p2p/channels', '/channel-list']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            try:
                resp = sess.get(tracker_url('/channel-list'), timeout=8)
                data = resp.json()
                json_response(self, resp.status_code, data)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        if path in ['/signal/poll', '/p2p/signal/poll']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            try:
                resp = sess.get(tracker_url('/signal/poll'), timeout=8)
                data = resp.json()
                json_response(self, resp.status_code, data)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        text_response(self, 404, 'Not found')

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_json()
        if data is None:
            json_response(self, 400, {'error': 'invalid json'})
            return

        if path in ['/login', '/p2p/login']:
            username = str(data.get('username', '')).strip()
            password = str(data.get('password', ''))
            if not username or not password:
                json_response(self, 400, {'error': 'username and password required'})
                return
            ok, err = login_to_tracker(username, password)
            if not ok:
                json_response(self, 401, {'error': err})
                return
            snap = get_state_snapshot()
            json_response(self, 200, {
                'message': 'login success',
                'username': snap['username'],
                'tracker': snap['tracker'],
                'gateway_host': snap['gateway_host'],
                'gateway_port': snap['gateway_port'],
            })
            return

        if path in ['/logout', '/p2p/logout']:
            clear_login_state()
            json_response(self, 200, {'message': 'logged out'})
            return

        if path in ['/signal/send', '/p2p/signal/send']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            target = str(data.get('target', '')).strip()
            sig_type = str(data.get('type', '')).strip()
            payload = data.get('data')
            if not target or not sig_type:
                json_response(self, 400, {'error': 'target and type required'})
                return
            try:
                resp = sess.post(
                    tracker_url('/signal/send'),
                    json={'target': target, 'type': sig_type, 'data': payload},
                    timeout=8,
                )
                out = resp.json()
                json_response(self, resp.status_code, out)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        if path in ['/p2p/channel/join', '/add-list']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            channel = str(data.get('channel', '')).strip()
            if not channel:
                json_response(self, 400, {'error': 'channel name required'})
                return
            try:
                resp = sess.post(tracker_url('/add-list'), json={'channel': channel}, timeout=8)
                out = resp.json()
                json_response(self, resp.status_code, out)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        if path in ['/p2p/channel/send', '/broadcast-peer']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            channel = str(data.get('channel', '')).strip()
            message = str(data.get('message', '')).strip()
            if not channel or not message:
                json_response(self, 400, {'error': 'channel and message required'})
                return
            try:
                resp = sess.post(
                    tracker_url('/broadcast-peer'),
                    json={'channel': channel, 'message': message},
                    timeout=8,
                )
                out = resp.json()
                json_response(self, resp.status_code, out)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        if path in ['/p2p/channel/messages', '/messages']:
            sess = get_session()
            if not sess:
                json_response(self, 401, {'error': 'not logged in'})
                return
            channel = str(data.get('channel', '')).strip()
            try:
                resp = sess.post(tracker_url('/messages'), json={'channel': channel}, timeout=8)
                out = resp.json()
                json_response(self, resp.status_code, out)
            except Exception as e:
                json_response(self, 502, {'error': f'tracker unreachable: {e}'})
            return

        text_response(self, 404, 'Not found')


def main():
    parser = argparse.ArgumentParser(description='Peer Web Gateway for P2P chat demo')
    parser.add_argument('--host', '--gateway-host', dest='host', default='127.0.0.1',
                        help='Host/IP for this peer gateway (default: 127.0.0.1)')
    parser.add_argument('--port', '--gateway-port', dest='port', type=int, default=9001,
                        help='Port for this peer gateway (default: 9001)')
    parser.add_argument('--tracker', '--tracker-url', dest='tracker', default='http://127.0.0.1:8005',
                        help='Tracker base URL, e.g. http://127.0.0.1:8005')
    args = parser.parse_args()

    tracker = normalize_tracker_url(args.tracker)

    with STATE_LOCK:
        STATE['tracker'] = tracker
        STATE['gateway_host'] = args.host
        STATE['gateway_port'] = args.port

    server = ThreadingHTTPServer((args.host, args.port), PeerHandler)
    print(f'[PeerGateway] running at http://{args.host}:{args.port}')
    print(f'[PeerGateway] tracker = {tracker}')
    print('[PeerGateway] open /login in the browser')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[PeerGateway] stopped')


if __name__ == '__main__':
    main()
