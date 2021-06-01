from flask import Flask, request, jsonify, session, g
from collections import defaultdict
from os import environ
from hashlib import sha256
from uuid import uuid4 

Users = defaultdict(dict)
Tokens = defaultdict(list)


def signup():
    # missing inputs validation
    params = request.json
    
    if params.get("email") in Users:
        return "Conflict", 409
    
    Users[params["email"]] = {
        "email": params.get("email"), # serve as unique id
        "name": params.get("name"),
        "password": sha256(params.get("password").encode()).hexdigest(),
    }
    
    return "Created", 201

def signin():
    # missing inputs validation
    params = request.json
    user = Users.get(params.get("email"))
    
    if not user or \
    user["password"] != sha256(params.get("password").encode()).hexdigest():
        return "Unauthorized", 403
    
    token = str(uuid4()) # generate random token
    Tokens[user["email"]].append(token)
    session["user"] = user["email"]
    return token, 200
    
    

def signout():
    session.clear()
    return 200


#@authenticate
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
