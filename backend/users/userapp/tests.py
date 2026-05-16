import json
import unittest
from unittest.mock import patch, MagicMock

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key",
        INSTALLED_APPS=["userapp"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=False,
    )
    django.setup()

import jwt
from userapp import views


class _NotFound(Exception):
    pass


class MockRequest:
    def __init__(self, method="GET", body=None, headers=None, params=None):
        self.method = method
        if body is None:
            self.body = b""
        elif isinstance(body, dict):
            self.body = json.dumps(body).encode()
        else:
            self.body = body
        self.headers = headers or {}
        self.GET = params or {}


def _token(user_id=1, github_id=1001, github_username="alice"):
    return jwt.encode(
        {"user_id": user_id, "github_id": github_id, "github_username": github_username},
        "dev-secret-key",
        algorithm="HS256",
    )


class TestMeView(unittest.TestCase):

    def test_no_auth_header_returns_401(self):
        resp = views.me(MockRequest())
        self.assertEqual(resp.status_code, 401)

    def test_invalid_token_returns_401(self):
        req = MockRequest(headers={"Authorization": "Bearer bad.token.here"})
        resp = views.me(req)
        self.assertEqual(resp.status_code, 401)

    @patch("userapp.views.User")
    def test_valid_token_returns_user(self, MockUser):
        mock_user = MagicMock(id=1, github_id=1001, github_username="alice",
                              email="alice@example.com", full_name="Alice", age=None)
        MockUser.objects.get.return_value = mock_user

        req = MockRequest(headers={"Authorization": f"Bearer {_token()}"})
        resp = views.me(req)

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["github_username"], "alice")
        self.assertEqual(data["github_id"], 1001)


class TestCreateScript(unittest.TestCase):

    def test_wrong_method_returns_405(self):
        resp = views.create_script(MockRequest(method="GET"))
        self.assertEqual(resp.status_code, 405)

    def test_missing_code_returns_400(self):
        req = MockRequest(method="POST", body={"user_id": 1})
        resp = views.create_script(req)
        self.assertEqual(resp.status_code, 400)

    @patch("userapp.views.User")
    def test_user_not_found_returns_404(self, MockUser):
        MockUser.DoesNotExist = _NotFound
        MockUser.objects.get.side_effect = _NotFound
        req = MockRequest(method="POST", body={"user_id": 99, "code": "x = 1"})
        resp = views.create_script(req)
        self.assertEqual(resp.status_code, 404)

    @patch("userapp.views.UserScript")
    @patch("userapp.views.User")
    def test_create_success_returns_201(self, MockUser, MockScript):
        MockUser.objects.get.return_value = MagicMock(id=1)
        MockScript.objects.filter.return_value.count.return_value = 0
        mock_s = MagicMock(id=10, title="script_1_1", code='print("hi")',
                           is_active=True, created_at=None, updated_at=None)
        MockScript.objects.create.return_value = mock_s

        req = MockRequest(method="POST", body={"user_id": 1, "code": 'print("hi")'})
        resp = views.create_script(req)

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(json.loads(resp.content)["code"], 'print("hi")')


class TestGetScripts(unittest.TestCase):

    def test_missing_user_id_returns_400(self):
        resp = views.get_scripts(MockRequest())
        self.assertEqual(resp.status_code, 400)

    @patch("userapp.views.UserScript")
    def test_returns_scripts_list(self, MockScript):
        MockScript.objects.filter.return_value.order_by.return_value = []
        req = MockRequest(params={"user_id": "1"})
        resp = views.get_scripts(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["scripts"], [])


class TestUpdateScript(unittest.TestCase):

    def test_wrong_method_returns_405(self):
        resp = views.update_script(MockRequest(method="GET"), script_id=1)
        self.assertEqual(resp.status_code, 405)

    def test_missing_fields_returns_400(self):
        req = MockRequest(method="PUT", body={"user_id": 1})
        resp = views.update_script(req, script_id=1)
        self.assertEqual(resp.status_code, 400)

    @patch("userapp.views.UserScript")
    def test_not_found_returns_404(self, MockScript):
        MockScript.DoesNotExist = _NotFound
        MockScript.objects.get.side_effect = _NotFound
        req = MockRequest(method="PUT", body={"user_id": 1, "code": "x"})
        resp = views.update_script(req, script_id=99)
        self.assertEqual(resp.status_code, 404)

    @patch("userapp.views.UserScript")
    def test_update_success(self, MockScript):
        mock_s = MagicMock(id=1, title="s1", code="new code", is_active=True, updated_at=None)
        MockScript.objects.get.return_value = mock_s
        req = MockRequest(method="PUT", body={"user_id": 1, "code": "new code"})
        resp = views.update_script(req, script_id=1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["code"], "new code")


class TestDeleteScript(unittest.TestCase):

    def test_wrong_method_returns_405(self):
        resp = views.delete_script(MockRequest(method="GET"), script_id=1)
        self.assertEqual(resp.status_code, 405)

    @patch("userapp.views.UserScript")
    def test_not_found_returns_404(self, MockScript):
        MockScript.objects.filter.return_value.delete.return_value = (0, {})
        req = MockRequest(method="DELETE", body={"user_id": 1})
        resp = views.delete_script(req, script_id=99)
        self.assertEqual(resp.status_code, 404)

    @patch("userapp.views.UserScript")
    def test_delete_success(self, MockScript):
        MockScript.objects.filter.return_value.delete.return_value = (1, {})
        req = MockRequest(method="DELETE", body={"user_id": 1})
        resp = views.delete_script(req, script_id=1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["status"], "deleted")


class TestUpdateProfile(unittest.TestCase):

    def test_wrong_method_returns_405(self):
        resp = views.update_user_profile(MockRequest(method="GET"), user_id=1)
        self.assertEqual(resp.status_code, 405)

    def test_invalid_json_returns_400(self):
        req = MockRequest(method="PUT", body=b"not json")
        resp = views.update_user_profile(req, user_id=1)
        self.assertEqual(resp.status_code, 400)

    @patch("userapp.views.User")
    def test_user_not_found_returns_404(self, MockUser):
        MockUser.DoesNotExist = _NotFound
        MockUser.objects.get.side_effect = _NotFound
        req = MockRequest(method="PUT", body={"email": "x@x.com"})
        resp = views.update_user_profile(req, user_id=99)
        self.assertEqual(resp.status_code, 404)

    @patch("userapp.views.User")
    def test_update_success(self, MockUser):
        mock_u = MagicMock(id=1, github_id=1001, github_username="alice",
                           email="alice@example.com", full_name="Alice",
                           age=25, created_at=None, updated_at=None)
        MockUser.objects.get.return_value = mock_u
        req = MockRequest(method="PUT", body={"email": "alice@example.com", "age": 25})
        resp = views.update_user_profile(req, user_id=1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["age"], 25)


if __name__ == "__main__":
    unittest.main()
