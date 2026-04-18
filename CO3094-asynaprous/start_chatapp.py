
import argparse
from apps.chatapp import create_chatapp

PORT = 8001

parser = argparse.ArgumentParser(prog='ChatApp', description='Chat Tracker Server')
parser.add_argument('--server-ip',   default='0.0.0.0')
parser.add_argument('--server-port', type=int, default=PORT)

args = parser.parse_args()
create_chatapp(args.server_ip, args.server_port)
