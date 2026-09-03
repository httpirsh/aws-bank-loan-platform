import os

import bcrypt
import boto3
from django.conf import settings
from django.test import Client, TestCase
from django.utils import timezone
from moto import mock_aws
from rest_framework.exceptions import AuthenticationFailed

from api import models as api_models
from api.models import LoanApplication, LoanEvaluation, User

OFFICER_USERNAME = "Íris"
OFFICER_PASSWORD = "securepassword123"


@mock_aws
class OfficeViewsTestCase(TestCase):
    """
    Exercises the officer-facing Django template views (login, loan
    requests list, evaluation, interview scheduling/resolution) against a
    mocked DynamoDB + SNS (moto), so nothing touches real AWS.

    api.models keeps a module-level `dynamodb` resource created once at
    Django startup, before any per-test mock exists, so it's swapped out
    here for one created inside the active mock (restored in tearDown) -
    same approach as testunit_UserDynamoDB.py.
    """

    def setUp(self):
        self._real_dynamodb_resource = api_models.dynamodb
        api_models.dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)

        ddb_client = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        ddb_client.create_table(
            TableName=User.DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # send_sns_notification(_eval) publishes to whatever topic ARN is
        # configured; create a real moto topic with the matching name so
        # publish() succeeds instead of raising NotFound.
        topic_name = os.environ["SNS_NOTIFICATION_TOPIC_ARN"].rsplit(":", 1)[-1]
        boto3.client("sns", region_name=settings.AWS_REGION).create_topic(Name=topic_name)

        hashed_password = bcrypt.hashpw(OFFICER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        User(
            username=OFFICER_USERNAME,
            email="iris.officer@bank.com",
            phone="000000000",
            face_id="",
            user_type="officer",
            password=hashed_password,
        ).save()

        self.client = Client()

    def tearDown(self):
        api_models.dynamodb = self._real_dynamodb_resource

    def login_as_officer(self):
        response = self.client.post(
            "/office/login/",
            {"username": OFFICER_USERNAME, "password": OFFICER_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/office/home/")
        self.assertIn("jwt_token", self.client.cookies)

    def create_loan_application(self, **overrides):
        defaults = dict(
            username="iris",
            monthly_income=2200,
            monthly_expenses=900,
            amount=15000,
            duration=36,
            credit_score=720,
            application_status="interview",
        )
        defaults.update(overrides)
        return LoanApplication.objects.create(**defaults)

    # -- manager_login -----------------------------------------------

    def test_login_with_correct_credentials_sets_jwt_cookie_and_redirects(self):
        self.login_as_officer()

    def test_login_with_wrong_password_shows_error_and_sets_no_cookie(self):
        response = self.client.post(
            "/office/login/", {"username": OFFICER_USERNAME, "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials")
        self.assertNotIn("jwt_token", self.client.cookies)

    def test_login_with_unknown_username_shows_error(self):
        response = self.client.post(
            "/office/login/", {"username": "does-not-exist", "password": "whatever"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User not found")

    # -- LoanRequestsListView -----------------------------------------

    def test_loan_requests_list_requires_officer_auth(self):
        with self.assertRaises(AuthenticationFailed):
            self.client.get("/office/loan-requests-list/")

    def test_loan_requests_list_shows_unevaluated_loans(self):
        self.create_loan_application()
        self.login_as_officer()

        response = self.client.get("/office/loan-requests-list/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iris")

    def test_loan_requests_list_excludes_already_evaluated_loans(self):
        loan = self.create_loan_application()
        LoanEvaluation.objects.create(application=loan, officer=OFFICER_USERNAME, status="accept")
        self.login_as_officer()

        response = self.client.get("/office/loan-requests-list/")

        self.assertNotContains(response, "Evaluate")

    # -- LoanEvaluationView --------------------------------------------

    def test_scheduling_an_interview_creates_evaluation_and_redirects(self):
        loan = self.create_loan_application()
        self.login_as_officer()

        timeslot = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        response = self.client.post(
            f"/office/loan-evaluation/{loan.id}/",
            {"status": "interview", "timeslots": [timeslot], "notes": "Schedule a call."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/office/loan-waiting-interview/")

        evaluation = LoanEvaluation.objects.get(application=loan)
        self.assertEqual(evaluation.status, "interview")
        self.assertEqual(evaluation.timeslots, timeslot)

    def test_direct_accept_creates_evaluation_and_redirects_to_evaluated(self):
        loan = self.create_loan_application()
        self.login_as_officer()

        response = self.client.post(
            f"/office/loan-evaluation/{loan.id}/",
            {"status": "accept", "notes": "Approved."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/office/loan-evaluated/")

        evaluation = LoanEvaluation.objects.get(application=loan)
        self.assertEqual(evaluation.status, "accept")

    # -- LoanWaitingInterviewView ---------------------------------------

    def test_waiting_interview_lists_only_interview_status_evaluations(self):
        loan = self.create_loan_application()
        LoanEvaluation.objects.create(application=loan, officer=OFFICER_USERNAME, status="interview")
        self.login_as_officer()

        response = self.client.get("/office/loan-waiting-interview/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iris")

    def test_accepting_a_pending_interview_resolves_it(self):
        """
        Regression test: this POST handler used to crash with a 500 for
        every officer (it checked request.user.is_authenticated, which
        this app never sets, and its error paths `return`ed a bare
        ValueError instead of an HttpResponse).
        """
        loan = self.create_loan_application()
        evaluation = LoanEvaluation.objects.create(
            application=loan, officer=OFFICER_USERNAME, status="interview"
        )
        self.login_as_officer()

        response = self.client.post(
            "/office/loan-waiting-interview/",
            {"loan_id": evaluation.pk, "action": "accept"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/office/loan-waiting-interview/")

        evaluation.refresh_from_db()
        self.assertEqual(evaluation.status, "accept")

    def test_waiting_interview_post_without_officer_auth_is_rejected_not_crashed(self):
        loan = self.create_loan_application()
        evaluation = LoanEvaluation.objects.create(
            application=loan, officer=OFFICER_USERNAME, status="interview"
        )

        with self.assertRaises(AuthenticationFailed):
            self.client.post(
                "/office/loan-waiting-interview/",
                {"loan_id": evaluation.pk, "action": "accept"},
            )

    def test_waiting_interview_rejects_invalid_action(self):
        self.login_as_officer()

        response = self.client.post(
            "/office/loan-waiting-interview/",
            {"loan_id": "1", "action": "not-a-real-action"},
        )

        self.assertEqual(response.status_code, 400)

    # -- LoanEvaluatedView -----------------------------------------------

    def test_evaluated_loans_excludes_pending_interviews(self):
        loan = self.create_loan_application()
        LoanEvaluation.objects.create(application=loan, officer=OFFICER_USERNAME, status="interview")
        self.login_as_officer()

        response = self.client.get("/office/loan-evaluated/")

        self.assertNotContains(response, "iris")
