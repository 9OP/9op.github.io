import unittest

from flask import json, session, g
from app import (
    create_app,
    Users,
    Tokens,
    require,
    authenticate,
)


class Test(unittest.TestCase):
    def setUp(self):
        super().setUp()
        Users.clear()
        Tokens.clear()


class TestRequire(Test):
    def test_success(self):
        data = {
            "email": "user@mail.com",
            "name": "user",
            "other": "123",
        }
        keys = ["email", "name"]

        self.assertEqual(
            require(keys, data), ({"email": data["email"], "name": data["name"]}, None)
        )

    def test_missing_params(self):
        data = {"email": "user@mail.com"}
        keys = ["email", "name"]

        self.assertEqual(
            require(keys, data), (None, (f"Invalid parameter: name missing", 400))
        )


class TestAuthenticate(Test):
    def setUp(self):
        super().setUp()
        self.app = create_app()
        self.token = "token"
        self.user = {"email": "user@mail.com", "name": "user"}

        Users[self.user["email"]] = self.user
        Tokens[self.user["email"]] = [self.token]

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "request_ctx"):
            self.request_ctx.pop()

    # Create virtual context for testing Flask session and request
    def app_context(self, bearer=True):
        headers = {"Authorization": f"Bearer {self.token}"} if bearer else {}
        self.request_ctx = self.app.test_request_context(headers=headers)
        self.request_ctx.push()

    def test_success(self):
        self.app_context()
        session["user"] = self.user["email"]

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), "ok")
        self.assertEqual(g.user["email"], self.user["email"])

    def test_missing_cookie(self):
        self.app_context()

        @authenticate
        def fn():
            return

        self.assertEqual(fn(), ("Authentication cookie missing", 401))
        self.assertEqual(g.get("user"), None)

    def test_invalid_token(self):
        self.token = "invalidtoken"
        self.app_context()
        session["user"] = "user@mail.com"

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), ("Invalid token", 401))
        self.assertEqual(g.get("user"), None)

    def test_missing_token(self):
        self.app_context(bearer=False)
        session["user"] = "user@mail.com"

        @authenticate
        def fn():
            return "ok"

        self.assertEqual(fn(), ("Authentication bearer missing", 401))
        self.assertEqual(g.get("user"), None)


def payload(data={}, headers={}, token=""):
    return {
        "headers": {
            **headers,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        "data": json.dumps(data),
    }


class TestSignup(Test):
    def setUp(self):
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

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

    # unittest is standard but it doesnt not support parametrized tests...
    def test_missing_parameter(self):
        def _test_missing_parameter(user, key):
            response = self.client.post("/auth/signup", **payload(user))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.data, f"Invalid parameter: {key} missing".encode()
            )

        _test_missing_parameter({"name": "user", "password": "123"}, "email")
        _test_missing_parameter({"email": "user@mail.com", "password": "123"}, "name")
        _test_missing_parameter({"email": "user@mail.com", "name": "user"}, "password")


class TestSignin(unittest.TestCase):
    pass


class TestSignout(unittest.TestCase):
    pass


class TestWhoami(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
