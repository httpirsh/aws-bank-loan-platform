import json

from django.test import TestCase, Client


class LoanSimulationViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_returns_active_message(self):
        response = self.client.get("/api/simulator/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("active", response.json()["message"])

    def test_post_valid_input_returns_calculated_details(self):
        response = self.client.post(
            "/api/simulator/",
            data=json.dumps({"loan_amount": 10000, "loan_duration": 36}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("interest_rate", data)
        self.assertIn("total_repayment", data)
        self.assertIn("monthly_installment", data)

    def test_post_invalid_amount_returns_400(self):
        response = self.client.post(
            "/api/simulator/",
            data=json.dumps({"loan_amount": 0, "loan_duration": 36}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
