from flask import Flask, Blueprint, request, jsonify, session, g
from collections import defaultdict
from os import environ
from hashlib import sha256
from uuid import uuid4
import functools

# Database entity
Users = defaultdict(dict)
Tokens = defaultdict(list)


# Authentication middleware
def authenticate(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        # handshake
        if session.get("handshake") != request.headers.get("Handshake", ""):
            return "Handshake failed", 401
        
        email = session.get("user")
        if not email:
            return "Authentication cookie missing", 401

        token = request.headers.get("Authorization", "").strip().replace("Bearer ", "")
        if not token:
            return "Authentication token missing", 401

        if token not in Tokens.get(email, []) or token != session.get("token"):
            return "Invalid token", 401

        g.user = Users[email]
        return func(*args, **kwargs)

    return inner


#
# Controllers

def signup():
    params = request.json

    if params["email"] in Users:
        return f"User {params['email']} already exists", 409

    Users[params["email"]] = {
        "email": params["email"],
        "name": params["name"],
        "password": sha256(params["password"].encode()).hexdigest(),
    }

    return "Created", 201


def signin():
    params = request.json

    user = Users.get(params["email"])

    if not user or user["password"] != sha256(params["password"].encode()).hexdigest():
        return "Unauthorized", 401

    token = str(uuid4())  # generate random token
    Tokens[user["email"]].append(token)
    session["user"] = user["email"]
    session["token"] = token
    return token, 200


def signout():
    Tokens[session.get("user")].clear()
    session.clear()
    return "Signout", 200


def handshake():
    handshake = str(uuid4())
    session["handshake"] = handshake
    return handshake, 200


@authenticate
def whoami():
    user = g.user
    return jsonify(email=user["email"], name=user["name"]), 200



#
# App factory

def create_app():
    app = Flask(__name__)
    app.secret_key = environ.get("SECRET_KEY", "secret")

    auth_api = Blueprint("auth_api", __name__, url_prefix="/auth")
    auth_api.route("/signup", methods=["POST"])(signup)
    auth_api.route("/signin", methods=["POST"])(signin)
    auth_api.route("/signout", methods=["GET"])(signout)
    auth_api.route("/handshake", methods=["POST"])(handshake)
    auth_api.route("/whoami", methods=["GET"])(whoami)

    app.register_blueprint(auth_api)

    return app


if __name__ == "__main__":
    create_app()
