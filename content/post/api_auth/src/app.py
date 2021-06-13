from flask import Flask, request, jsonify, session, g
from collections import defaultdict
from os import environ
from hashlib import sha256
from uuid import uuid4
import functools


Users = defaultdict(dict)
Tokens = defaultdict(list)


def require(keys, params):
    data = dict()
    for key in keys:
        if key not in params:
            return f"Invalid parameter: {key} missing", 400
        data[key] = params[key]
    return data


def authenticate(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        email = session.get("user")
        if not email:
            return "Authentication cookie missing", 401

        bearer = request.headers.get("Authorization", "").strip().split()
        if not bearer:
            return "Authentication bearer missing", 401

        token = bearer[-1]
        if token not in Tokens.get(email):
            return "Invalid token", 401

        g.user = Users[email]

        return func(*args, **kwargs)

    return inner


def signup():
    params = require(["name", "email", "password"], request.json)

    if params["email"] in Users:
        return f"User {params['email']} already exists", 409

    Users[params["email"]] = {
        "email": params["email"],
        "name": params["name"],
        "password": sha256(params["password"].encode()).hexdigest(),
    }

    return "Created", 201


def signin():
    params = require(["email", "password"], request.json)
    user = Users.get(params["email"])

    if not user or user["password"] != sha256(params["password"].encode()).hexdigest():
        return "Unauthorized", 403

    token = str(uuid4())  # generate random token
    Tokens[user["email"]].append(token)
    session["user"] = user["email"]
    return token, 200


def signout():
    session.clear()
    return 200


@authenticate
def whoami():
    user = g.user
    return jsonify(user), 200


def create_app():
    app = Flask(__name__)
    app.secret_key = environ.get("SECRET_KEY", "secret")

    app.route("/signup", methods=["POST"])(signup)
    app.route("/signin", methods=["POST"])(signin)
    app.route("/signout", methods=["GET"])(signout)
    app.route("/whoami", methods=["GET"])(whoami)

    return app


if __name__ == "__main__":
    create_app()
