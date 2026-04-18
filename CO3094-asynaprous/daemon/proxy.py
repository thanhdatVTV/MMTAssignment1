#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.proxy
~~~~~~~~~~~~~~~~~

This module implements a simple proxy server using Python's socket and threading libraries.
It routes incoming HTTP requests to backend services based on hostname mappings and returns
the corresponding responses to clients.

Requirement:
-----------------
- socket: provides socket networking interface.
- threading: enables concurrent client handling via threads.
- response: customized :class: `Response <Response>` utilities.
- httpadapter: :class: `HttpAdapter <HttpAdapter >` adapter for HTTP request processing.
- dictionary: :class: `CaseInsensitiveDict <CaseInsensitiveDict>` for managing headers and cookies.

"""
import socket
import threading
from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

#: A dictionary mapping hostnames to backend IP and port tuples.
#: Used to determine routing targets for incoming requests.
PROXY_PASS = {
    "192.168.56.103:8080": ('192.168.56.103', 9000),
    "app1.local": ('192.168.56.103', 9001),
    "app2.local": ('192.168.56.103', 9002),
}


def forward_request(host, port, request):
    """
    Forwards an HTTP request to a backend server and retrieves the response.

    :params host (str): IP address of the backend server.
    :params port (int): port number of the backend server.
    :params request (str): incoming HTTP request.

    :rtype bytes: Raw HTTP response from the backend server. If the connection
                  fails, returns a 404 Not Found response.
    """

    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        backend.connect((host, port))
        backend.sendall(request.encode())
        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk
        return response
    except socket.error as e:
      print("Socket error: {}".format(e))
      return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')


def resolve_routing_policy(hostname, routes):
    """
    Handles an routing policy to return the matching proxy_pass.
    It determines the target backend to forward the request to.

    :params host (str): IP address of the request target server.
    :params port (int): port number of the request target server.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    print(f"[Proxy] Resolving hostname: {hostname}")
    # Default fallback if hostname not in routes
    proxy_map, policy = routes.get(hostname, ('127.0.0.1:9000', 'round-robin'))
    
    print(f"[Proxy] Policy: {policy}, Map: {proxy_map}")

    proxy_host = '127.0.0.1'
    proxy_port = '9000'
    
    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            print("[Proxy] Empty resolved routing for hostname {}".format(hostname))
        elif len(proxy_map) == 1:
            # Fixed: changed 'value' to 'proxy_map'
            parts = proxy_map[0].split(":")
            proxy_host = parts[0]
            proxy_port = parts[1] if len(parts) > 1 else '80'
        else:
            # Round-robin or other policy could be implemented here
            # For now, default to the first one
            parts = proxy_map[0].split(":")
            proxy_host = parts[0]
            proxy_port = parts[1] if len(parts) > 1 else '80'
    else:
        # Singularity case (string)
        parts = proxy_map.split(":")
        proxy_host = parts[0]
        proxy_port = parts[1] if len(parts) > 1 else '80'

    return proxy_host, proxy_port

def handle_client(ip, port, conn, addr, routes):
    """
    Handles an individual client connection by parsing the request,
    determining the target backend, and forwarding the request.

    The handler extracts the Host header from the request to
    matches the hostname against known routes. In the matching
    condition,it forwards the request to the appropriate backend.

    The handler sends the backend response back to the client or
    returns 404 if the hostname is unreachable or is not recognized.

    :params ip (str): IP address of the proxy server.
    :params port (int): port number of the proxy server.
    :params conn (socket.socket): client connection socket.
    :params addr (tuple): client address (IP, port).
    :params routes (dict): dictionary mapping hostnames and location.
    """

    try:
        data = conn.recv(4096)
        if not data:
            conn.close()
            return
        
        request = data.decode("utf-8", errors="ignore")

        # Extract hostname
        hostname = ''
        for line in request.splitlines():
            if line.lower().startswith('host:'):
                hostname = line.split(':', 1)[1].strip()
                break

        print("[Proxy] {} at Host: {}".format(addr, hostname))

        # Resolve the matching destination in routes and need conver port
        # to integer value
        resolved_host, resolved_port = resolve_routing_policy(hostname, routes)
        try:
            resolved_port = int(resolved_port)
        except ValueError:
            print("Not a valid integer")

        if resolved_host:
            print("[Proxy] Host name {} is forwarded to {}:{}".format(hostname,resolved_host, resolved_port))
            response = forward_request(resolved_host, resolved_port, request)        
        else:
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')
        conn.sendall(response)
    except Exception as e:
        print("[Proxy ERROR] Error handling client {}: {}".format(addr, e))
    finally:
        conn.close()

def run_proxy(ip, port, routes):
    """
    Starts the proxy server and listens for incoming connections. 

    The process dinds the proxy server to the specified IP and port.
    In each incomping connection, it accepts the connections and
    spawns a new thread for each client using `handle_client`.
 

    :params ip (str): IP address to bind the proxy server.
    :params port (int): port number to listen on.
    :params routes (dict): dictionary mapping hostnames and location.

    """

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)
        print("[Proxy] Listening on IP {} port {}".format(ip,port))
        while True:
            conn, addr = proxy.accept()
            print(f"[Proxy] Accepted connection from {addr}")
            
            #
            #  TODO: implement the step of the client incoming connection
            #        using non-blocking communication
            #          + multi-thread
            #          + callback
            #          + coroutine
            #        provided handle_client routine
            #

            # Start a new thread for each client
            client_thread = threading.Thread(
                target=handle_client,
                args=(ip, port, conn, addr, routes),
                daemon=True
            )
            client_thread.start()
    except socket.error as e:
      print("Socket error: {}".format(e))

def create_proxy(ip, port, routes):
    """
    Entry point for launching the proxy server.

    :params ip (str): IP address to bind the proxy server.
    :params port (int): port number to listen on.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    run_proxy(ip, port, routes)
