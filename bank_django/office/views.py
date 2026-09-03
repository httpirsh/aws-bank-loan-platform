import logging
import os
import boto3
import bcrypt
from django import forms
from datetime import datetime
from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, FormView
from api.models import LoanApplication, LoanEvaluation, User
from utils import auth_user_is, generate_jwt_token
logger = logging.getLogger(__name__)

def welcome_page(request):
    return render(request, 'welcomePage.html')

def manager_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        plain_pass = request.POST['password']

        # Fetch officer data from DynamoDB
        try:
            # Query DynamoDB to fetch the user
            response = User.get_dynamo_table().get_item(Key={'username': username})
            if 'Item' not in response:
                return render(request, 'login.html', {'error': 'User not found'})

            user = response['Item']

            # Check if the user is an officer
            if user.get('user_type') != 'officer':
                return render(request, 'login.html', {'error': 'Invalid user type'})

            # Check if the password matches the stored hashed password using bcrypt
            stored_password_hash = user.get('password')
            if not stored_password_hash:
                return render(request, 'login.html', {'error': 'Invalid credentials'})

            if not bcrypt.checkpw(plain_pass.encode('utf-8'), stored_password_hash.encode('utf-8')):
                return render(request, 'login.html', {'error': 'Invalid credentials'})

            # If the credentials are correct, manually create a session for the officer
            request.session['username'] = user['username']
            request.session['user_type'] = user['user_type']
            request.session['authenticated'] = True

            auth_user = User(
                    username=user['username'],
                    email=user['email'],
            )

            # Set the token in an HTTP-only cookie and return to home
            token = generate_jwt_token(auth_user)
            response = redirect('home')
            response.set_cookie(
                'jwt_token',
                token,
                max_age=timedelta(days=1),
                httponly=True, # Cannot be accessed via JavaScript
                secure=True, # Use only over HTTPS
                samesite='Strict' # Protects against CSRF attacks
            )
            return response

        except Exception as e:
            logger.error(f"Error during login: {e}")
            return render(request, 'login.html', {'error': 'Something went wrong during login.'})

    return render(request, 'login.html')

def home_page(request):
    return render(request, 'homePage.html')

class LoanRequestsListView(ListView):
    model = LoanApplication
    template_name = 'loanRequestsList.html'
    context_object_name = 'loans'

    def dispatch(self, request, *args, **kwargs):
        self.user = auth_user_is(request, ["officer"]) # Only allowed for officers

        # Call the parent dispatch method to proceed
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_date = timezone.now()

        # Filter current loans
        current_loans = LoanApplication.objects.filter(
            created__gte=current_date - timedelta(days=2),
            loanevaluation__isnull=True
        ).order_by('created')

        # Filter past loans
        past_loans = LoanApplication.objects.filter(
            created__lt=current_date - timedelta(days=2),
            loanevaluation__isnull=True
        ).order_by('created')

        # Add the current and past loan lists to the context
        context['current_loans'] = current_loans
        context['past_loans'] = past_loans

        return context

class LoanEvaluationForm(forms.Form):
    STATUS_CHOICES = [
        ('accept', 'Accepted'),
        ('reject', 'Rejected'),
        ('interview', 'Interview'),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES)
    timeslots = forms.CharField(required=False, widget=forms.HiddenInput)  # Stores the selected timeslots

class LoanEvaluationView(DetailView, FormView):
    model = LoanApplication
    template_name = 'loanEvaluation.html'
    context_object_name = 'loan'
    form_class = LoanEvaluationForm

    def get_object(self):
        return get_object_or_404(LoanApplication, id=self.kwargs['loan_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timeslots = self._get_available_timeslots()
        context['available_timeslots'] = timeslots
        return context

    def form_valid(self, form):
        loan = self.get_object()
        status = form.cleaned_data['status']
        timeslot_values = self.request.POST.getlist('timeslots')  # Get the selected timeslots

        # Create or fetch the evaluation associated with this loan
        evaluation, created = LoanEvaluation.objects.get_or_create(application=loan, officer=self.request.user.username)
        evaluation.status = status

        # If status is 'interview', attach the selected timeslots
        if status == 'interview' and timeslot_values:
            evaluation.timeslots = '/ '.join(timeslot_values)  # Store timeslots as a "/ "-separated string
        evaluation.save()


        # If status is 'interview', redirect to the loans-awaiting-interview page
        if status == 'interview':
            return redirect('loan_waiting_interview')
        else: 
            self.send_sns_notification(loan)
            return redirect('loan_evaluated')

    def send_sns_notification(self, loan):
        sns = boto3.client('sns')
        # SNS topic ARN
        topic_arn = os.environ["SNS_NOTIFICATION_TOPIC_ARN"]

        message = f"Olá {loan.username}, sua solicitação de empréstimo foi avaliada com o status: {loan.application_status}."

        sns.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject="Avaliação de Empréstimo Concluída"
        )

    def _get_available_timeslots(self):
        # Simulates available interview timeslots
        now = timezone.now()
        timeslots = [now + timedelta(hours=i) for i in range(1, 6)]
        return [{"formatted": slot.strftime('%Y-%m-%d %H:%M:%S'), "display": slot.strftime('%a, %b %d, %Y %H:%M')} for slot in timeslots]

class LoanEvaluatedView(ListView):
    model = LoanEvaluation
    template_name = 'loanEvaluated.html'
    context_object_name = 'loan_evaluated'

    def get_queryset(self):
        return  LoanEvaluation.objects.exclude(status='interview')

class LoanWaitingInterviewView(ListView):
    model = LoanEvaluation
    template_name = 'loanWaitingInterview.html'
    context_object_name = 'loan_waiting_interview'

    def get_queryset(self):
        return LoanEvaluation.objects.filter(status='interview')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        for loan in context['loan_waiting_interview']:
            if loan.timeslots:
                # Split the stored timeslots into a list of strings
                timeslot_str_list = loan.timeslots.split("/ ")

                # Parse each string into a datetime object
                loan.timeslot_list = [
                    datetime.strptime(timeslot_str, "%Y-%m-%d %H:%M:%S") 
                    for timeslot_str in timeslot_str_list
                ]
            else:
                loan.timeslot_list = []

        return context 
        
    def post(self, request, *args, **kwargs):
        # Check whether the user is allowed to change the status
        auth_user_is(request, ["officer"])

        loan_id = request.POST.get('loan_id')
        action = request.POST.get('action')

        if not loan_id or action not in ['accept', 'reject']:
            return HttpResponseBadRequest("Invalid action.")

        # Fetch the loan evaluation by ID
        loan_evaluation = get_object_or_404(LoanEvaluation, pk=loan_id)

        # Ensure the loan is currently in 'interview' status
        if loan_evaluation.status != 'interview':
            return HttpResponseBadRequest("Loan is not in interview status.")

        # Update the status based on the button pressed
        loan_evaluation.status = action
        loan_evaluation.save()
        self.send_sns_notification_eval(loan_evaluation)

        # Redirect back to the loans-awaiting-interview page
        return redirect('loan_waiting_interview')
    
    def send_sns_notification_eval(self, loan_evaluation):
        sns = boto3.client('sns')
        # SNS topic ARN
        topic_arn = os.environ["SNS_NOTIFICATION_TOPIC_ARN"]

        loan = loan_evaluation.application
        message = f"Olá {loan.username}, sua solicitação de empréstimo foi avaliada com o status: {loan_evaluation.status}."

        sns.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject="Avaliação de Empréstimo Concluída"
        )
