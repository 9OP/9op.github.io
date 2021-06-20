import unittest

from flask import json, session, g
from hashlib import sha256
from app import (
    Users,
    Tokens,
    authenticate,
    create_app,
)


class Test(unittest.TestCase):
    def setUp(self):
        super().setUp()
        Users.clear()
        Tokens.clear()
        self.app = create_app()
        self.client = self.app.test_client()


class TestAuthenticate(Test):
    def setUp(self):
        super().setUp()
        self.token = "token"
        self.handshake = "handshake"
        self.user = {"email": "user@mail.com", "name": "user"}

        Users[self.user["email"]] = self.user
        Tokens[self.user["email"]] = [self.token]

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "request_ctx"):
            self.request_ctx.pop()

    # Create virtual context for testing Flask session and request
    def app_context(self, bearer=True, hs=True):
        token = {"Authorization": f"Bearer {self.token}"} if bearer else {}
        handshake = {"Handshake": self.handshake} if hs else {}
        self.request_ctx = self.app.test_request_context(headers={**token, **handshake})
        self.request_ctx.push()

    def test_success(self):
        self.app_context()
        session["user"] = self.user["email"]
        session["token"] = self.token
        session["handshake"] = self.handshake

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), "ok")
        self.assertEqual(g.user["email"], self.user["email"])

    def test_missing_cookie(self):
        self.app_context()
        session["token"] = self.token
        session["handshake"] = self.handshake

        @authenticate
        def fn():
            return

        self.assertEqual(fn(), ("Authentication cookie missing", 401))
        self.assertEqual(g.get("user"), None)

    def test_invalid_token(self):
        self.token = "invalidtoken"
        self.app_context()
        session["user"] = "user@mail.com"
        session["token"] = self.token
        session["handshake"] = self.handshake

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), ("Invalid token", 401))
        self.assertEqual(g.get("user"), None)

    def test_missing_token(self):
        self.app_context(bearer=False)
        session["user"] = "user@mail.com"
        session["token"] = self.token
        session["handshake"] = self.handshake

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), ("Authentication token missing", 401))
        self.assertEqual(g.get("user"), None)

    def test_missing_handshake_header(self):
        self.app_context(hs=False)
        session["user"] = "user@mail.com"
        session["token"] = self.token
        session["handshake"] = self.handshake

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), ("Handshake failed", 401))
        self.assertEqual(g.get("user"), None)

    def test_missing_handshake_cookie(self):
        self.app_context()
        session["user"] = "user@mail.com"
        session["token"] = self.token

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), ("Handshake failed", 401))
        self.assertEqual(g.get("user"), None)


def payload(data={}, headers={}, token="", handshake=""):
    return {
        "headers": {
            **headers,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Handshake": handshake,
        },
        "data": json.dumps(data),
    }


class TestSignup(Test):
    def setUp(self):
        super().setUp()

    def test_success(self):
        user = {"email": "user@mail.com", "name": "user", "password": "password123"}

        response = self.client.post("/auth/signup", **payload(user))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, b"Created")
        self.assertEqual(len(Users), 1)

    def test_user_already_exists(self):
        user = {"email": "user@mail.com", "name": "user", "password": "password123"}
        Users[user["email"]] = user

        response = self.client.post("/auth/signup", **payload(user))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data, b"User user@mail.com already exists")
        self.assertEqual(len(Users), 1)


class TestSignin(Test):
    def setUp(self):
        super().setUp()

        self.user = {
            "email": "user@mail.com",
            "name": "user",
            "password": sha256(b"password").hexdigest(),
        }
        Users[self.user["email"]] = self.user

    def test_success(self):
        response = self.client.post(
            "/auth/signin",
            **payload({"email": "user@mail.com", "password": "password"}),
        )

        with self.client.session_transaction() as sess:
            token = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Tokens[self.user["email"]], [token])
            self.assertEqual(sess["token"], token)
            self.assertEqual(sess["user"], self.user["email"])

    def test_wrong_password(self):
        response = self.client.post(
            "/auth/signin",
            **payload({"email": "user@mail.com", "password": "wrong"}),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b"Unauthorized")

    def test_no_user(self):
        response = self.client.post(
            "/auth/signin",
            **payload({"email": "wronguser@mail.com", "password": "password"}),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b"Unauthorized")


class TestSignout(Test):
    def setUp(self):
        super().setUp()

        self.user = {
            "email": "user@mail.com",
            "name": "user",
            "password": sha256(b"password").hexdigest(),
        }
        Users[self.user["email"]] = self.user
        Tokens[self.user["email"]] = ["token"]

    def test_success(self):
        with self.client.session_transaction() as sess:
            sess["user"] = self.user["email"]
        response = self.client.get("/auth/signout")

        session_cookie = next(
            (cookie for cookie in self.client.cookie_jar if cookie.name == "session"),
            None,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"Signout")
        self.assertEqual(Tokens[self.user["email"]], [])
        self.assertIsNone(session_cookie)

    def test_success_no_session(self):
        response = self.client.get("/auth/signout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"Signout")


class TestHandshake(Test):
    def setUp(self):
        super().setUp()

    def test_success(self):
        response = self.client.post("/auth/handshake")

        with self.client.session_transaction() as sess:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(sess["handshake"], response.get_data(as_text=True))


class TestWhoami(Test):
    def setUp(self):
        super().setUp()

        self.user = {
            "email": "user@mail.com",
            "name": "user",
            "password": sha256(b"password").hexdigest(),
        }
        Users[self.user["email"]] = self.user
        Tokens[self.user["email"]] = ["token"]

    def test_success(self):
        with self.client.session_transaction() as sess:
            sess["user"] = self.user["email"]
            sess["token"] = "token"
            sess["handshake"] = "handshake"
        response = self.client.get(
            "/auth/whoami", **payload(token="token", handshake="handshake")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "email": self.user["email"],
                "name": self.user["name"],
            },
        )

    def test_missing_cookie(self):
        with self.client.session_transaction() as sess:
            sess["handshake"] = "handshake"
        response = self.client.get(
            "/auth/whoami", **payload(token="token", handshake="handshake")
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b"Authentication cookie missing")

    def test_missing_bearer(self):
        with self.client.session_transaction() as sess:
            sess["user"] = self.user["email"]
            sess["token"] = "token"
            sess["handshake"] = "handshake"
        response = self.client.get("/auth/whoami", **payload(handshake="handshake"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b"Invalid token")

    def test_invalid_bearer(self):
        with self.client.session_transaction() as sess:
            sess["user"] = self.user["email"]
            sess["token"] = "token"
            sess["handshake"] = "handshake"
        response = self.client.get(
            "/auth/whoami", **payload(token="invalidtoken", handshake="handshake")
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b"Invalid token")

    def test_handshake_failed(self):
        with self.client.session_transaction() as sess:
            sess["user"] = self.user["email"]
            sess["token"] = "token"
        response = self.client.get("/auth/whoami", **payload(token="token"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b"Handshake failed")


if __name__ == "__main__":
    unittest.main()
