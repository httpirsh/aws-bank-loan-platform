from django.urls import path
from .views import welcome_page, manager_login, home_page, LoanRequestsListView, LoanEvaluationView, LoanEvaluatedView, LoanWaitingInterviewView

urlpatterns = [
    path('', welcome_page, name='welcome_page'),  # Welcome landing page
    path('login/', manager_login, name='login'),  # Login page
    path('home/', home_page, name='home'),  # Home page after login
    path('loan-requests-list/', LoanRequestsListView.as_view(), name='loan_requests_list'),  # Loan request list
    path('loan-evaluation/<int:loan_id>/', LoanEvaluationView.as_view(), name='loan_evaluation'),  # Loan evaluation
    path('loan-evaluated/', LoanEvaluatedView.as_view(), name='loan_evaluated'),  # Evaluated loans
    path('loan-waiting-interview/', LoanWaitingInterviewView.as_view(), name='loan_waiting_interview'),  # Loans awaiting interview
]
