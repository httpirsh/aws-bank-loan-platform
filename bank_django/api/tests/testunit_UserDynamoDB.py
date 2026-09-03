import boto3
from django.conf import settings
from django.test import TestCase
from moto import mock_aws

from api import models as api_models
from api.models import User


@mock_aws
class UserDynamoDBTestCase(TestCase):
    """
    Exercises the User model's DynamoDB-backed save/get/delete methods
    against a mocked DynamoDB table (moto), so tests don't hit real AWS.

    api.models keeps a module-level `dynamodb` resource created once at
    Django startup, before any per-test mock exists, so it's swapped out
    here for one created inside the active mock (restored in tearDown).
    """

    def setUp(self):
        self._real_dynamodb_resource = api_models.dynamodb
        api_models.dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)

        client = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        client.create_table(
            TableName=User.DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

    def tearDown(self):
        api_models.dynamodb = self._real_dynamodb_resource

    def test_save_and_get_round_trip(self):
        User(
            username="jdoe",
            email="jdoe@example.com",
            phone="123456789",
            face_id="face-123",
            user_type="customer",
        ).save()

        fetched = User.get("jdoe")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.email, "jdoe@example.com")
        self.assertEqual(fetched.face_id, "face-123")
        self.assertEqual(fetched.user_type, "customer")

    def test_get_missing_user_returns_none(self):
        self.assertIsNone(User.get("does-not-exist"))

    def test_delete_removes_user(self):
        User(
            username="temp",
            email="temp@example.com",
            phone="000",
            face_id="face-000",
            user_type="customer",
        ).save()

        User(username="temp", email="", phone="", face_id="", user_type="").delete()

        self.assertIsNone(User.get("temp"))
