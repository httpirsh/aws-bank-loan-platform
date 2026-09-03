from django.test import TestCase, RequestFactory

from utils import generate_jwt_token, get_jwt_decoded, decode_jwt_token


class FakeUser:
    def __init__(self, username, email):
        self.username = username
        self.email = email


class JWTUtilsTestCase(TestCase):
    def setUp(self):
        self.user = FakeUser("jdoe", "jdoe@example.com")
        self.factory = RequestFactory()

    def test_generate_and_decode_round_trip(self):
        token = generate_jwt_token(self.user)
        payload = decode_jwt_token(token)
        self.assertEqual(payload["username"], "jdoe")
        self.assertEqual(payload["email"], "jdoe@example.com")

    def test_get_jwt_decoded_reads_token_from_cookie(self):
        token = generate_jwt_token(self.user)
        request = self.factory.get("/")
        request.COOKIES["jwt_token"] = token

        payload = get_jwt_decoded(request)
        self.assertEqual(payload["username"], "jdoe")

    def test_get_jwt_decoded_reads_token_from_authorization_header(self):
        token = generate_jwt_token(self.user)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = get_jwt_decoded(request)
        self.assertEqual(payload["username"], "jdoe")

    def test_get_jwt_decoded_without_token_raises(self):
        request = self.factory.get("/")
        with self.assertRaises(Exception):
            get_jwt_decoded(request)

    def test_decode_invalid_token_raises(self):
        with self.assertRaises(Exception):
            decode_jwt_token("not-a-valid-token")
