from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from botocore.exceptions import ClientError
import boto3

class LoanSimulation(models.Model):
    amount = models.IntegerField("Amount (€)") 
    duration = models.IntegerField("Duration (months)", null=True, blank=True)
    desired_monthly_payment = models.IntegerField("Desired monthly payment (€)", null=True, blank=True)

    class Meta:
        managed = False

    def clean(self):
        super().clean()
        if self.duration and self.desired_monthly_payment:
            raise ValidationError("You can only set 'duration' or 'desired_monthly_payment', not both.")
        if not self.duration and not self.desired_monthly_payment:
            raise ValidationError("You must set either 'duration' or 'desired_monthly_payment'.")

    def get_interest_rate(self, loan_amount, loan_duration):
        """
        Calculate the interest rate based on loan amount and duration.
        """
        if loan_amount <= 10000:
            return 5.0 if loan_duration <= 12 else 5.5
        elif loan_amount <= 20000:
            return 4.5 if loan_duration <= 12 else 5.0
        else:
            return 4.0

    def calculate_loan_details(self, loan_amount, loan_duration):
        """
        Calculate total repayment and monthly installment for the loan.
        """
        interest_rate = self.get_interest_rate(loan_amount, loan_duration)
        total_repayment = loan_amount * (1 + (interest_rate / 100) * (loan_duration / 12))
        monthly_installment = total_repayment / loan_duration

        return {
            "interest_rate": interest_rate,
            "total_repayment": round(total_repayment, 2),
            "monthly_installment": round(monthly_installment, 2),
        }

class LoanDetails(models.Model):
    loan_simulation = models.ForeignKey(LoanSimulation, on_delete=models.CASCADE)
    interest_rate = models.FloatField("Interest rate (%)")
    total_repayment = models.FloatField("Total repayment (€)")
    monthly_payment = models.IntegerField("Monthly payment (€)")

    class Meta:
        managed = False

    def calculate_details(self):
        # Use the LoanSimulation instance to calculate the details
        loan_simulation = self.loan_simulation
        result = loan_simulation.calculate_loan_details(loan_simulation.amount, loan_simulation.duration)
        
        self.interest_rate = result["interest_rate"]
        self.total_repayment = result["total_repayment"]
        self.monthly_payment = result["monthly_installment"]

    def __str__(self):
        return f"LoanDetails(id={self.loan_simulation.id})"

class LoanApplication(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField("User requesting the loan application (authenticated user)")
    monthly_income = models.IntegerField("Monthly income (€)", blank=False, null=False)
    monthly_expenses = models.IntegerField("Monthly expenses (€)")
    amount = models.IntegerField("Amount (€)") 
    duration = models.IntegerField("Duration (months)", null=True, blank=True)
    desired_monthly_payment = models.IntegerField("Desired monthly payment (€)", null=True, blank=True)
    credit_score = models.IntegerField("Credit score (calculated by model)")
    application_status = models.CharField(
        max_length=9,
        choices=[
            ('accept', 'Accepted'),
            ('interview', 'Interview'),
            ('reject', 'Rejected')
        ]
    )
    created = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.duration and self.desired_monthly_payment:
            raise ValidationError("You can only set 'duration' or 'desired_monthly_payment', not both.")
        if not self.duration and not self.desired_monthly_payment:
            raise ValidationError("You must set either 'duration' or 'desired_monthly_payment'.")


    def __str__(self):
        return f"LoanApplication(id={self.id}, user={self.username}, amount={self.amount}, status={self.application_status})"    

class LoanEvaluation(models.Model):
    application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, unique=True)
    notes = models.CharField("Annotations", null=True, blank=True)
    status = models.CharField(
        max_length=11,
        choices=[
            ('unevaluated', 'Unevaluated'),
            ('accept', 'Accepted'),
            ('interview', 'Interview'),
            ('reject', 'Rejected'),
        ],
        default='unevaluated')

    officer = models.CharField("Officer evaluating the loan application", max_length=255)
    created = models.DateTimeField("When was the evaluation record created", auto_now_add=True)
    updated = models.DateTimeField("Last time the evaluation was updated", auto_now=True)
    
    # Stores the interview timeslot(s)
    timeslots = models.TextField(blank=True, null=True)  # Stores multiple timeslots as text


    def __str__(self):
        return f"LoanEvaluation(id={self.application}, officer={self.officer}, status={self.status}, timeslots={self.timeslots})"

# Initialize the DynamoDB client
dynamodb = boto3.resource(
    "dynamodb",
    region_name=settings.AWS_REGION
)

class User(models.Model):
    username = models.CharField(primary_key=True, max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    face_id = models.CharField(max_length=255)
    user_type = models.CharField(max_length=255)
    password = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'User'
        managed = False # Tell Django not to manage this table, bacause Django does not natively support DynamoDB

    def __str__(self):
        return f"User {self.name} ({self.face_id})"

    # Define the DynamoDB table name
    DYNAMODB_TABLE_NAME = "Users"

    @classmethod
    def get_dynamo_table(cls):
        """Fetch the DynamoDB table object."""
        return dynamodb.Table(cls.DYNAMODB_TABLE_NAME)

    def save(self, *args, **kwargs):
        """Override the save method to write to DynamoDB."""
        # Prepare item for DynamoDB
        item = {
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "face_id": self.face_id,
            "user_type": self.user_type,
            "password": self.password
        }

        # Write item to DynamoDB
        table = self.get_dynamo_table()
        try:
            table.put_item(Item=item)
        except ClientError as e:
            raise Exception(f"Error saving to DynamoDB: {e}")

    @classmethod
    def get(cls, username):
        """Fetch a user by ID from DynamoDB."""
        table = cls.get_dynamo_table()
        try:
            response = table.get_item(Key={"username": username})
            if "Item" in response:
                item = response["Item"]
                return cls(
                    username=item["username"],
                    email=item["email"],
                    phone=item["phone"],
                    face_id=item["face_id"],
                    user_type=item["user_type"],
                    password=item["password"]
                )
            else:
                return None
        except ClientError as e:
            raise Exception(f"Error fetching from DynamoDB: {e}")

    def delete(self, *args, **kwargs):
        """Delete a user from DynamoDB."""
        table = self.get_dynamo_table()
        try:
            table.delete_item(Key={"username": self.username})
        except ClientError as e:
            raise Exception(f"Error deleting from DynamoDB: {e}")
    