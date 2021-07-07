---
draft: false
toc: true
title: "Secure API authentication"
date: "2021-06-19"
readingTime: 15
tags: ["python", "flask", "api", "authentication", "backend"]
# cover: "cover.jpg"
---

<!--description-->

API authentication is a critical component of any web service because it impacts the integrity of users' data. It is not a topic to be overlooked
and though you may find many tutorials on the web about this, most of them avoid the security question and copy-paste each other mistakes.
I am writing this post, so from now on, it can be copy-pasted by my fellow wannabe tech guru and spread useful information...

<!--more-->

This is not *another JSON web tokens authentication API tutorial*. We are going to ask the right questions and think security first. 

{{<linebreak>}}

**Sources on [GitHub](https://github.com/9OP/9op.github.io/tree/master/content/post/api_auth/src).**

{{<linebreak>}}

## Introduction

The context of this post is a backend API for a web app (Angular, React, Vue etc...).
In the context of a public API to be consumed by other web services (not web clients), the approach might be different, and we even might use JWT.

This post is about discussing the security vulnerabilities (mostly XSS and CSRF) when implementing an authentication mechanism for a web API.

{{<linebreak 2 >}}

## Authentication

Before diving into the technical questions about security and implementation, let's present a generic approach to authentication.

{{<figure src=authentication-mechanism-light.png caption=`Authentication mechanism flow diagram` >}}

The authentication mechanism consists in:
- A client sending his credentials to the server.
- The server verifying if the credentials match an existing identity.
- The server generating an authentication proof send it back to the client.
- The client sending his authentication proof with future requests etc... 

This mechanism is generic and corresponds to many kinds of implementations. Especially the implementation answers the following questions:
- How are the credentials sent to the server? (JSON, multi-form, basic auth ...)
- How the server match the existing identity?
- What kind of authentication proof, the server generates?
- How the client (web browser) stores the authentication proof?

The secure implementation of this mechanism is the purpose of this post.

{{<linebreak 2 >}}

## Vulnerabilities

Since we are going to talk about security, we need to get familiar with the two main vulnerabilities this article is about: XSS and CSRF.
These are not the only vulnerabilities found on the web, for a more detailed list go see [OWASP top ten](https://owasp.org/www-project-top-ten/).
> The OWASP Top 10 is a standard awareness document for developers and web application security. It represents a broad consensus about the most critical security risks to web applications.

OWASP top ten is a really good source/checklist to understand the good practices in building secure API.
This article cannot cover the entire top ten, however, I will try as much as possible to give guidance on what you should do and what you should avoid.

{{<linebreak >}}

### XSS

XSS (cross-site-scripting), is a type of injection attack that allows an attacker to run JavaScript code directly within our user's web app.
With the rise of web frameworks (React, Vue, Angular), it is less and less likely to occur. 
Usually, XSS takes advantage of badly sanitized inputs, for instance, a comment section.

A badly sanitized input would allow an attacker to type the following:
```html
<script>
    alert("all your data are belong to us")
</script>
```

When other users fetch data from our server, if the attacker's input is not sanitized by the server or web app, then the script is run in the user's app.
XSS vulnerabilities allow attackers to access the browser API of the client, and so the local storage. With XSS an attacker can retrieve the local storage and exfiltrate data to its server.

**As a consequence no secrets or authentication proof should be stored in the local storage.**

{{<linebreak >}}

### CSRF

CSRF (cross-site-request-forgery), is more common than XSS, it is a vulnerability that takes advantage of the web browser always sending cookies back to the domain they came from. Unlike XSS, in a CSRF attack, the authentication proof is not accessed by the attacker but used indirectly on behalf of the user.

For instance, if an attacker can trick a user to visit this malicious web page:

```html
<form action="https://bank.cash/transfert?amount=1000&to=attacker_account" method="post">
    <button type="submit">Get a cool cat picture!</button>
</form> 
```

If the user is already logged in (ie. has received proof of authentication) from `bank.cash` and click on the button to
get a cool cat picture (because seriously, who would not like to get a cool cat picture?!), he would instead send 1000 to the `attacker_account`.
And most tragically he would not get a cool cat picture.

The attacker does not gain access to the authentication proof of the user but was able to request on its behalf, because the authentication
proof (contained in the cookie) was sent to the domain `bank.cash` by the browser from the malicious page. This is CSRF.

In this example, we assumed that:
- `bank.cash` web service was designed poorly (no CORS, no transfers confirmation, uses cookie only as proof of authentication).
- `POST /transfer?` makes a transfer from the authenticated user.

This is a silly example to illustrate CSRF and obviously, no serious financial institutions would do that...

**As a consequence no authentication proof should be stored in cookies**

**Note:** You might have heard of CSRF/XSRF-token. These are very common in the world of MVC (model-view-controller) web frameworks (eg. Python Django). 
They are a countermeasure against CSRF. The idea of the CSRF token is to compare the token sent in an HTTP-only cookie with the token sent in the request header.
If there is a value mismatch between the header and the cookie then the request is rejected. It prevents CSRF because CSRF can only use the cookies indirectly and cannot access the token sent in the header.

{{<linebreak 2>}}

## Implementation

Now we understand XSS and CSRF vulnerabilities and their consequences on the authentication implementation:
- XSS: cannot store the authentication proof in the local storage
- CSRF: cannot store the authentication proof in the cookies

So how should the client store the authentication proof received from the server upon login? 
Where to store the authentication proof securely?
We cannot ask the users to give their credentials along with every request because the UI would be horrible. 
(and we cannot store the credentials in the local storage, because of XSS).

**The solution is to use both the local storage and the cookies to store a part of the authentication proof.**

Whoa, big brain time, it is like in mathematics where two minuses equal a plus. 
The catch here is to not store the **entire** authentication proof in either the cookies or the local storage. But instead, store a part in the local storage
and another part in an **HTTP only** cookie.

{{<linebreak>}}

### Architecture

Since this is not a tutorial on Flask, I will not expand on the code itself, but rather on the logic. Indeed, I decided to use Python Flask because of its conciseness and clarity. The ideas disclosed in this article can be implemented with your favourite stack be it Node, Go, Ruby, and even Java or PHP if you hate yourself.


```python
from flask import Flask, Blueprint
from collections import defaultdict
from os import environ

# Database entities
Users = defaultdict(dict)
Tokens = defaultdict(list)

#
# Authentication middleware
def authenticate(func):
    pass

#
# Controllers
def signup():
    pass

def signin():
    pass

def signout():
    pass

@authenticate
def whoami():
    pass

#
# App Factory
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
```

This is the architecture we will be working with. There are 4 endpoints (signup, signin, signout and whoami). The database is mocked
with the `defaultDict` `Users` and `Tokens` (which are sugared hashmaps/dictionaries). And `authenticate` is the authentication middleware responsible for blocking unauthorized requests (ie. requests failing the authentication proof-verification).

We only need to implement the business logic. I will not focus on `signup`, so you can have a look at it directly in the 
sources, it is not relevant since it just appends a new user to the `Users` object and hashes the password.

{{<linebreak >}}

### Signin

Signin logic consists of verifying the user's credentials, creating an access token and creating a "session" cookie. A "session" cookie is Flask being fancy
and encrypting the cookie with the application's `secret_key` for us. The "session" cookie is also HTTP-only which means it cannot be read by JavaScript in the browser.
**An HTTP-only cookie is nice because it is not vulnerable to XSS.**

```python
from flask import request, session
from hashlib import sha256
from uuid import uuid4


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
```

The first step is to get the JSON body payload of the request. Then we look for a user in `Users` whose email is the input `email`. 
Then we compare the hashed password of the found user and return `401 Unauthorized` if the user was not 
found or the hashed password did not match the one in the database.

Finally, we create a random unique token `str(uuid4())`, the token is stored in the database and we create an HTTP-only cookie "session" 
with the user's `email` and the generated token. Upon success, this endpoint returns the token.

Testing with curl, we got:

```txt {linenos=false}
> $ curl -i \ 
    --header "Content-Type: application/json" \
    --request POST \
    --data '{ "email":"user@mail.com", "password":"123456" }' \
    http://localhost:5000/auth/signin

HTTP/1.0 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 36
Vary: Cookie
Set-Cookie: session=eyJ0b2tlbiI6IjI1MGNlNDM5LTZhZWEtNGQwOC04MjliLTUzMmViNjllYmMzNCIsInVzZXIiOiJ1c2VyQG1haWwuY29tIn0
    .YM9TtQ.WeDyTF1NNB8elnkZdIffZdQTqbY; HttpOnly; Path=/
Server: Werkzeug/2.0.1 Python/3.9.5
Date: Sat, 19 Jun 2021 23:25:12 GMT

9d897db6-7520-4deb-a86a-2723b19a4543
```

The authentication proof is composed of:
- token: `9d897db6-7520-4deb-a86a-2723b19a4543`
- cookie: `session=eyJ0b2tlbiI6IjI1MGNlNDM5LTZhZWEtN...`


The token can be **stored in the browser's local storage** because it is only a part of the authentication proof. 
The other part is contained in the HTTP-only "session" cookie which cannot be read by JavaScript. 

{{<linebreak>}}

**Note:** For the sake of conciseness multiple things are not right security-wise and production-wise in the above snippet:
- In production, you would need to validate the endpoint input.
- In production, you would use [`bcrypt`](https://github.com/pyca/bcrypt/) instead of `sha256` as the password hashing algorithm.

For input validation I like to use [Cerberus](https://docs.python-cerberus.org/en/stable/), it is easy to use and fits all my need (coercion, normalization, filter).
In the above snippet, I would use Cerberus to validate the payload: `email` and `password`.

Concerning password, you should **never store the password in plain text in your database, thus hashing**. `sha` is good enough for a demo, but not for production.
I am no expert in cryptography but the reason for using `bcrypt` instead of `sha` is related to the time it takes to compute a hash. `bcrypt` is purposely slow, while `sha` is fast. The advantage of using a slow hashing method for the password is to make the life of attackers harder by slowing down local brute-force attacks. (eg. if your database with hashed password is breached, then attackers would take a significantly longer time to brute-force the hashing).
{{<linebreak >}}

### Signout

There are multiple approaches to sign out. I have opted for a `GET` method plus clearing the "session" cookie as well as all issued tokens.
You might choose to keep the tokens and simply tag them as revoked or apply more complex logics on which tokens you need to remove etc... 

My signout function is blind stupid, it just gets the user from the "session" cookie, removes the tokens associated with that user and clear the "session" cookie. 
This way we make sure to remove both parts of the authentication proof: token and cookie. 

```python
def signout():
    Tokens[session.get("user")].clear()
    session.clear()
    return "Signout", 200
```

{{<linebreak >}}

### Whoami

The `whoami` controller is decorated with the `authenticate` authentication middleware. This middleware, upon success, will add the user to the global context `g`.
The `whoami` method simply get the user from the global context `g` and return a jsonified response with the user's `email` and `name`. It is good practice to not 
return the hashed password.

```python
from flask import jsonify, g

@authenticate
def whoami():
    user = g.user
    return jsonify(email=user["email"], name=user["name"]), 200
```

```txt {linenos=false}
> $ curl -i \
    --header "Authorization: Bearer 9d897db6-7520-4deb-a86a-2723b19a4543" \
    --cookie "session=eyJ0b2tlbiI6IjI1MGNlNDM5LTZhZWEtNGQwOC04MjliLTUzMmViNjllYm \ 
    MzNCIsInVzZXIiOiJ1c2VyQG1haWwuY29tIn0.YM9TtQ.WeDyTF1NNB8elnkZdIffZdQTqbY" \
    --request GET \
    http://localhost:5000/auth/whoami

HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 50
Vary: Cookie
Server: Werkzeug/2.0.1 Python/3.9.5
Date: Sun, 20 Jun 2021 12:19:47 GMT

{
  "email": "user@mail.com", 
  "name": "user"
}
```

{{<linebreak >}}

Now comes the main piece of this article: the authentication middleware. It is the critical part of the implementation. It should only succeed if the request
provides the entire authentication proof: token and cookie.

```python
import functools


def authenticate(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
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
```

`authenticate` is a python `decorator` (fancy word for function composition: a function that takes another function as an argument).
The function `authenticate` takes as argument a controller (e.g. `def whoami`). It is not an article on Python decorators, 
so let's dive into the logic right away.

The first step is to get the "session" cookie value: `email = session.get("user")`. If the value is `None` then the middleware returns a `401 Unauthorized`.
Then the middleware look for the token in the header `Authorization: Bearer <token>`. If the token is missing, then the middleware returns a `401 Unauthorized`.

Then if the cookie and the token were found, the middleware verifies that the token is associated with the cookie by looking into the `Tokens` database entity.
We also need to check that the token value contains in the "session" cookie match the one send in the header. Indeed, with the `app_secret` breached, an attacker could craft a session cookie with the user's email. Storing the token in the "session" cookie prevents cookie crafting/baking.
If the verification fails it means the token is invalid and the middleware returns `401 Unauthorized`.

Finally, the authentication proof was verified, the middleware attaches the `Users[email]` instance to the global context `g` and call the controller function `func`.

Testing with curl:

```txt {linenos=false}
> $ curl --header "Authorization: Bearer 9a64e921-d4a7-4923-9e61-67cdf7565201" \
    http://localhost:5000/auth/whoami

Authentication cookie missing


> $ curl --cookie "session=eyJ1c2VyIjoidXNlckBtYWlsLmNvbSJ9.YM8x3g.vWn7uuvhSbrnACXscXsyRb0ZDx8" \
    http://localhost:5000/auth/whoami

Authentication token missing


> $ curl --header "Authorization: Bearer 1234456789" \
    --cookie "session=eyJ1c2VyIjoidXNlckBtYWlsLmNvbSJ9.YM8x3g.vWn7uuvhSbrnACXscXsyRb0ZDx8" \
    http://localhost:5000/auth/whoami

Invalid token
```

{{<linebreak 2>}}

## Handshake

As the final part of this post, I would like to assess the vulnerabilities of this system.

At first sight, the authentication system is not vulnerable to XSS and CSRF because:
- XSS can only get the token not the HTTP-only "session" cookie
- CSRF can only use the cookie but not get the token

Now, what if an attacker can do both XSS and CSRF? An attacker would first get our token with an XSS attack, then use the token
in a CSRF attack (by injecting the token directly in the malicious web page).

The last piece our system needs to be safe against this XSS-CSRF kind of attack is a handshake mechanism. It should consist of the client and server agreeing
on a common secret before each request. 

A handshake prevents a CSRF attack to use a previously breached token, but it also means that for every API requests, a client should initiate a handshake with the server.

```python
# Authentication middleware
def authenticate(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        # handshake
        if session.get("handshake") != request.headers.get("handshake", ""):
            return "Handshake failed", 401

        session.pop("handshake")
        # ...
    return inner

def handshake():
    handshake = str(uuid4())
    session["handshake"] = handshake
    return handshake, 200

def create_app():
    # ...
    auth_api.route("/handshake", methods=["POST"])(handshake)

    return app
```

After the handshake is successful, it is important to remove the handshake token from the "session" cookie: `session.pop("handshake")`. 
This will force the client to handshake for future request. If the handshake token is not removed in the `authenticate` middleware, 
the system would again be vulnerable to CSRF.

{{<linebreak 2 >}}

## Conclusion

In this post, we have investigated common vulnerabilities of API authentication mechanism. In the end, there is nothing fundamentally difficult or complex about the proposed implementation. What matters is the state of mind and questions you should ask yourself when designing such systems.
Security is not an esoteric topic to be left at security specialists only, but an entire part of the system design and software architecture.

The demo application of this article proposes a way to prevent XSS and CSRF vulnerabilities, but I have to remind you that they are not the only threat to your app. There are other threats such as SQL injection, session fixation, and others listed by the OWASP top ten, that should also be
considered when building secure systems.

Web developers should be aware of the common pitfalls regarding web security to build more robust and less vulnerable systems. With this blog post
I hope I contributed to making the web a safer place, and helped fellow developers to improve their systems.
