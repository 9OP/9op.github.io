---
draft: true
toc: true
title: "Secure API authentication"
date: "2021-06-19"
readingTime: 15
tags: ["python", "flask", "api", "authentication", "backend"]
cover: "cover.jpg"
coverCaption: "© Christopher Burns"
---

<!--description-->

API authentication is a critical component of any web service because it impacts the security of the users' data. It is not a topic to be overlooked
and though you may find many tutorials on the web about this, most of them avoid the security question and just copy paste each other.
I am writting this post, so from now on, it can be copy pasted by other wannabe tech guru and actually spread usefull information...


This is not *another JSON web tokens authentication API tutorial*, here we are going to ask the right questions and think security first. 

<!--more-->

{{<linebreak>}}

**Sources on [GitHub](https://github.com/9OP/9op.github.io/tree/master/content/post/api_auth/src).**

{{<linebreak>}}

## Introduction

The context of this post is a backend API for a web app (Angular, React, Vue etc...).
In the context of a public API to be consummed by other web services (not web clients), the approach might be different, and we even might use JWT.

This post is about discussing the security vulnerabilities (mostly XSS and CSRF) when implementing an authentication mechanism for a web API.

{{<linebreak 2 >}}

## Authentication

Before diving into the technical questions about security and implementation, let's present a generic approach to authentication.

{{<figure src=authentication-mechanism.png caption=`Authentication mechanism flow diagram` >}}

The authentication mechanism consists in:
- A client sending his credentials to the server.
- The server verifying if the crendentials match an existing identity.
- The server generating an authentication proof send it back to the client.
- The client sending his authentication proof with futur requests etc... 

This mechanism is generic and correponds to many kind of implementations. Especially the implementation answers the following questions:
- How are the credentials send to the server? (Json, multi-form, basic auth ...)
- How the server match existing identity?
- What kind of authentication proof, the server generates?
- How the client (web browser) stores the authentication proof?

The secure implementation of this mechanism, is the purpose of this post.

{{<linebreak 2 >}}

## Vulnerabilities

Since we are going to talk about security, we need to get familiar with the two main vulnerabilities this article is about: XSS and CSRF.
These are not the only vulnerabilities found on the web, for a more detailled list go see [OWASP top ten](https://owasp.org/www-project-top-ten/).
> The OWASP Top 10 is a standard awareness document for developers and web application security. It represents a broad consensus about the most critical security risks to web applications.

OWASP top ten is a really good source/checklist to understand the good practices in building secure API.
This article cannot cover the entire top ten, however I will try as much as possible to give guidance on what you should do and what you should avoid.

{{<linebreak >}}

### XSS

XSS (cross-site-scripting), is an injection attack which allows an attacker to run JavaScript code directly whithin our user's web app.
With the rise of the web frameworks (React, Vue, Angular), it is less and less likely to occur. Usually XSS takes advantage of badly sanitized inputs, for instance a comment section.

A badly sanitized input would allow an attacker to type the following:
```html
<script>
    alert("all your data are belong to us")
</script>
```

Then when other users fetch data from our server, if the attacker's input is not sanitized by the server or web app, then the script is run in the user's app.
XSS vulnerabilities allow attackers to access the browser API of the client, and so the local storage. With XSS an attacker is able to retrieve the local storage and exfiltrate data to its own server.

**As a consequence no secrets or authentication proof should be stored in the localstorage.**

{{<linebreak >}}

### CSRF

CSRF (cross-site-request-forgery), is more common than XSS, it is a vulnerability that takes advantage of the web browser always sending cookies back to the domain they came from. Unlike XSS, in a CSRF attack, the authentication proof is not accessed by the attacker, but used indirectly on behalf of the user.

For instance if an attacker is able to trick a user to visit this malicious web page:

```html
<form action="https://bank.cash/transfert?amount=1000&to=attacker_account" method="post">
    <button type="submit">Get a cool cat picture!</button>
</form> 
```

If the user is already logged in (ie. has received a proof of authentication) from `bank.cash` and click on the button to
get a cool cat picture (because seriously, who would not like to get a cool cat picture?!), he would instead send 1000 to the `attacker_account`.
And most tragically he would not get a cool cat picture.

The attacker does not gain access to the authentication proof of the user, but was able to make a request on its behalf, because the authentication
proof (contained in the cookie) was sent to the domain `bank.cash` by the browser from the malicious page. This is CSRF.

In this example we assumed that:
- `bank.cash` web service was designed poorly (no CORS, no transfert confirmation, uses cookie only as proof of authentication).
- `POST /transfert?` makes a transfert from the authenticated user.

This is a silly example to illustrate CSRF and obviously no serious financial institutions would do that...

**As a consequence no authentication proof should be stored in cookies**

**Note:** You might have heard of CSRF/XSRF-token. These are very common in the world of MVC (model-view-controller) web framework (eg. Python Django). 
They are a countermeasure against CSRF for MVC, but they do not really make sense in the context of web API. We will discuss that latter.

{{<linebreak 2>}}

## Implementation

Now we understand XSS and CSRF vulnerabilities and their consequences on the authentication implementation:
- XSS: cannot store the authentication proof in the localstorage
- CSRF: cannot store the authentication proof in the cookies

So how should the client store the authentication proof received from the server uppon loggin? 
Where to store the authentication proof securely?
We cannot ask the users to give their credentials along with every requests because the UI would be horrible. (and we cannot store the credentials in 
the localstorage, because of XSS).

**The solution is to use both the local storage and the cookies to store a part of the authentication proof.**

Whoa, big brain time, it is like in mathematics where minus minus equals plus. 
The catch here is to not store the **entire** authentication proof in either the cookies or the local storage. But instead store a part in the local storage
and another part in an **HTTP only** cookie.

{{<linebreak>}}

### Architecture

Since this is not a tutorial on Flask, I will not expand on the code, but rather on the logic. Indeed, I decided to use Flask because of its consisennes and clarity. The ideas disclosed in this article can be implemented with your favorite stack be it Node, Go, Ruby, and even Java or PHP if you hate yourself.


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

This is the archicture we will be working with. There are 4 endpoints (signup, signin, signout and whoami). The database is mocked
with the `defaultDict` `Users` and `Tokens` (which are sugared hashmap/dictionnary). And `authenticate` is the authentication middleware responsible for 
blocking unauthorized requests.

The architecture is there, now we only need to implement the business logic. I will not focus on `signup`, so you can have a look at it directly in the 
sources, it is not really relevant since it just append a new user to the `Users` object + hash the password.

{{<linebreak >}}

### Signin

Signin logic consists in verifying the user's credentials, creating an access token and creating a "session" cookie. A "session" cookie is Flask being fancy
and encrypting the cookie with the application's `secret_key`. The "session" cookie is also HTTP-only which means it cannot be read by JavaScript on the client.
**An HTTP-only cookie is nice because it is not vulnerable to XSS**

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
    return token, 200
```

First step is to get the json body payload of the request. Then we look for a user with the input `email`. Then we compare the hashed 
password of the found user and return `401 Unauthorized` if the user was not found or the hashed password did not match the one in database.

Finnaly, we create a random unique token `str(uuid4())`, the token is stored in the database and we create an HTTP-only cookie "session" 
with the user's `email`. Uppon success this endpoint return the generated token.

Testing with curl, we got:

```txt {linenos=false}
>$ curl -i \ 
    --header "Content-Type: application/json" \
    --request POST \
    --data '{ "email":"user@mail.com", "password":"123456" }' \
    http://localhost:5000/auth/signin

HTTP/1.0 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 36
Vary: Cookie
Set-Cookie: session=eyJ1c2VyIjoidXNlckBtYWlsLmNvbSJ9.YM582A.5tjE1iE4pxWMcSKh3S86mLph0tk; HttpOnly; Path=/
Server: Werkzeug/2.0.1 Python/3.9.5
Date: Sat, 19 Jun 2021 23:25:12 GMT

9d897db6-7520-4deb-a86a-2723b19a4543
```

The authentication proof is composed of:
- token: `9d897db6-7520-4deb-a86a-2723b19a4543`
- session cookie: `eyJ1c2VyIjoidXNlckBtYWlsLmNvbSJ9.YM582A.5tjE1iE4pxWMcSKh3S86mLph0tk`


The token can be stored on the local storage because it is only a part of the authentication proof. 
The other part is contained in the HTTP-only "session" cookie (=the user's email encrypted with the app `secret-key`) which cannot be read by JavaScript. 
An XSS attack would be able to get only a part of the authentication proof: the token, not the cookie.

{{<linebreak>}}

**Note:** For the sake of conciseness multiple things are not right security-wise and production wise in the above snippet:
- In production you would need to validate the endpoint input.
- In production you would use [`bcrypt`](https://github.com/pyca/bcrypt/) instead of `sha256` as password hashing algo.

For input validation I like to use [Cerberus](https://docs.python-cerberus.org/en/stable/), it is easy to use and fits all my need (coercion, normalization, filter).
In the above snipper I would user Cerberus to validate the payload: `email` and `password`.

Concerning password, you should **never ever store the password in plain text in your database, thus hashing**. `sha` is good enough for a demo, but not for production.
I am no expert in cryptography but the reason of using `bcrypt` instead of `sha` is related to the time it takes to compute a hash. `bcrypt` is purposely slow, while `sha` is really fast. The advantage of using a slow hashing method for password, is to make the life of attackers harder by slowing down local bruteforce attacks. (eg. if your database with hashed password is breached, then attackers would take a significantly longer time to brute-force the hashing).

{{<linebreak >}}

### Signout

There are multiple approachs to signout. I have opted for a `GET` method plus clearing the "session" cookie as well as all issued tokens.
You might chose to keep the tokens and simply tag them as revoked or apply more complexe logics on which tokens you need to remove etc... 

My signout function is blind stupid, it just get the user from the "session" cookie, remove the tokens associated to that user and 
clear the "session" cookie. This way we make sure to remove both part of the authentication proof. 

```python
def signout():
    Tokens[session.get("user")].clear()
    session.clear()
    return "Signout", 200
```

{{<linebreak >}}

### Whoami

The whoami controller is decorated with the `authenticate` authentication middleware. This middleware, uppon success, will add the user to the global context `g`.
The `whoami` method simply get the user from the global context `g` and return a jsonified reponse with the user's `email` and `name`.

```python
from flask import jsonify, g

@authenticate
def whoami():
    user = g.user
    return jsonify(email=user["email"], name=user["name"]), 200
```

#curl example

{{<linebreak >}}

Now comes the main piece of this article: the authentication middleware. It is the critical part of the implementation. It should only succeed if the request
provides the entire authentication proof: token + cookie.



{{<linebreak 2>}}





{{<linebreak>}}