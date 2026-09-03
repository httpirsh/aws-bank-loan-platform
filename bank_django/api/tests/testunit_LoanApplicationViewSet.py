import boto3
from django.conf import settings
from django.test import Client, TestCase
from moto import mock_aws

from api import models as api_models
from api.models import LoanApplication, User
from utils import generate_jwt_token


@mock_aws
class LoanApplicationViewSetAccessControlTestCase(TestCase):
    """
    Regression tests for list()/retrieve(): they used to filter on a
    `customer` field that doesn't exist on LoanApplication (the real field
    is `username`) and compare against Django's own `request.user`, which
    this app never authenticates - `user_role == "customer"` was always
    False (auth_user_is returns a dict, not a role string), so every
    customer could see every other customer's loan applications.
    """

    def setUp(self):
        self._real_dynamodb_resource = api_models.dynamodb
        api_models.dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)

        boto3.client("dynamodb", region_name=settings.AWS_REGION).create_table(
            TableName=User.DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        for username in ("alice", "bob"):
            User(
                username=username,
                email=f"{username}@example.com",
                phone="000",
                face_id="",
                user_type="customer",
            ).save()

        self.alice_application = LoanApplication.objects.create(
            username="alice", monthly_income=2000, monthly_expenses=800,
            amount=10000, duration=24, credit_score=700, application_status="accept",
        )
        self.bob_application = LoanApplication.objects.create(
            username="bob", monthly_income=2500, monthly_expenses=900,
            amount=12000, duration=36, credit_score=680, application_status="accept",
        )

        self.client = Client()

    def tearDown(self):
        api_models.dynamodb = self._real_dynamodb_resource

    def login_as(self, username):
        token = generate_jwt_token(User(username=username, email=f"{username}@example.com"))
        self.client.cookies["jwt_token"] = token

    def test_customer_list_only_sees_own_applications(self):
        self.login_as("alice")

        response = self.client.get("/api/applications/")

        self.assertEqual(response.status_code, 200)
        usernames = {item["username"] for item in response.json()}
        self.assertEqual(usernames, {"alice"})

    def test_customer_cannot_retrieve_another_customers_application(self):
        self.login_as("alice")

        response = self.client.get(f"/api/applications/{self.bob_application.id}/")

        self.assertEqual(response.status_code, 403)

    def test_customer_can_retrieve_their_own_application(self):
        self.login_as("alice")

        response = self.client.get(f"/api/applications/{self.alice_application.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "alice")
