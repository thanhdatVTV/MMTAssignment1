#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
app.sampleapp
~~~~~~~~~~~~~~~~~

"""

import sys
import os
import importlib.util
import json

from   daemon import AsynapRous
from apps.auth import validate_user, create_session

app = AsynapRous()

@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user login via POST request.

    This route simulates a login process and prints the provided headers and body
    to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or login payload.
    """
    try:
        data = json.loads(body)
        username = data.get("username")
        password = data.get("password")

        print("[SampleApp] Logging in {} with body {}".format(headers, body))

        if not validate_user(username, password):
            data = {"error": "Invalid credentials"}
            return json.dumps(data), 401, {"Content-Type": "application/json"}

        session_id = create_session(username)

        data = {
            "message": "Login success",
            "username": username
        }

        # Return body, status, and headers (Set-Cookie)
        return json.dumps(data), 200, {
            "Content-Type": "application/json",
            "Set-Cookie": "session_id={}; Path=/; HttpOnly".format(session_id)
        }

    except Exception as e:
        print("[SampleApp] login exception {}".format(e))
        data = {"error": "Bad request"}
        return json.dumps(data), 400, {"Content-Type": "application/json"}

@app.route('/profile', methods=['GET'])
def profile(headers="guest", body="anonymous"):
    from apps.auth import get_current_user
    username = get_current_user(headers)
    
    if not username:
        data = {"error": "Unauthorized"}
        return json.dumps(data), 401, {"Content-Type": "application/json"}
    
    data = {
        "message": "User profile",
        "username": username,
        "role": "Administrator" if username == "admin" else "User"
    }
    return json.dumps(data), 200, {"Content-Type": "application/json"}


@app.route("/echo", methods=["POST"])
def echo(headers="guest", body="anonymous"):
    print("[SampleApp] received body {}".format(body))

    try:
        message = json.loads(body)
        data = {"received": message }
        # Convert to JSON string
        json_str = json.dumps(data)
        return (json_str.encode("utf-8"))
    except json.JSONDecodeError:
        data = {"error": "Invalid JSON"}
        # Convert to JSON string
        json_str = json.dumps(data)
        return (json_str.encode("utf-8"))


@app.route('/hello', methods=['PUT'])
async def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print("[SampleApp] ['PUT'] **ASYNC** Hello in {} to {}".format(headers, body))
    data =  {"id": 1, "name": "Alice", "email": "alice@example.com"}

    # Convert to JSON string
    json_str = json.dumps(data)
    return (json_str.encode("utf-8"))

def create_sampleapp(ip, port):
    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()

