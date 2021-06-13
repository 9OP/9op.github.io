from flask import Flask, Blueprint, request, jsonify, session, g
from collections import defaultdict
from os import environ
from hashlib import sha256
from uuid import uuid4
import functools

# Database entity
Users = defaultdict(dict)
Tokens = defaultdict(list)


# Request body validation
def require(keys, data):
    params = dict()
    for key in keys:
        value = data.get(key)
        if not value:
            return None, (f"Invalid parameter: {key} missing", 400)
        params[key] = value
    return params, None


# Authentication middleware
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
        if token not in Tokens.get(email, []):
            return "Invalid token", 401

        g.user = Users[email]
        return func(*args, **kwargs)

    return inner


#
# Controllers


def signup():
    params, err = require(["name", "email", "password"], request.json)
    if err:
        return err

    if params["email"] in Users:
        return f"User {params['email']} already exists", 409

    Users[params["email"]] = {
        "email": params["email"],
        "name": params["name"],
        "password": sha256(params["password"].encode()).hexdigest(),
    }

    return "Created", 201


def signin():
    params, err = require(["email", "password"], request.json)
    if err:
        return err
    
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
    auth_api.route("/whoami", methods=["GET"])(whoami)
    
    app.register_blueprint(auth_api)

    return app


if __name__ == "__main__":
    create_app()
