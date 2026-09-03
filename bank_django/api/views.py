from .models import LoanSimulation, LoanDetails, User, LoanApplication, LoanEvaluation
from boto3.dynamodb.conditions import Attr
from django.http import JsonResponse
from django.conf import settings
from django.views import View
from rest_framework import viewsets, status
from rest_framework.response import Response
from utils import generate_jwt_token, auth_user_is, start_workflow, get_workflow_result
from .serializers import LoanApplicationSerializer, LoanEvaluationSerializer
import datetime
import base64
import boto3
import json
import os
import time
import logging
from bank_website.settings import AWS_REGION, AWS_COLLECTION_NAME

logger = logging.getLogger(__name__)

# Initialize Rekognition and DynamoDB clients
rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table('Users')

class LoanSimulationView(View):
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for loan simulation.
        """
        try:
            data = json.loads(request.body)
            loan_amount = int(data.get("loan_amount", 0))
            loan_duration = int(data.get("loan_duration", 0))
            
            # Validate inputs
            if loan_amount <= 0 or loan_duration <= 0:
                return JsonResponse({"error": "Invalid loan amount or duration"}, status=400)

            # Create a LoanSimulation object
            loan_simulation = LoanSimulation(amount=loan_amount, duration=loan_duration)

            # Calculate loan details
            loan_details = LoanDetails(loan_simulation=loan_simulation)
            loan_details.calculate_details()

            # Prepare response data
            result = {
                "interest_rate": loan_details.interest_rate,
                "total_repayment": loan_details.total_repayment,
                "monthly_installment": loan_details.monthly_payment
            }

            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    def get(self, request, *args, **kwargs):
        """
        Optionally handle GET requests to provide simulator info (e.g., default values).
        """
        return JsonResponse({"message": "Loan Simulator API is active!"}, status=200)

class LoginView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        image_data = data.get('image')

        if not image_data:
            return JsonResponse({"error": "Image file is required"}, status=400)

        try:
            # Decode the base64 image data
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            return JsonResponse({"error": "Error decoding image"}, status=400)

        try:
            # Search for the face in Rekognition's collection
            rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)
            response = rekognition_client.search_faces_by_image(
                CollectionId=AWS_COLLECTION_NAME,
                Image={'Bytes': image_bytes},
                MaxFaces=1,
                FaceMatchThreshold=70
            )

            if 'FaceMatches' in response and response['FaceMatches']:
                face_id = response['FaceMatches'][0]['Face']['FaceId']
                logger.info(f"Rekognition Face ID: {face_id}")

                user = self.get_user_by_face_id(face_id)
                if user:
                    logger.info(f"Found user: {user.username}")
                    # Generate JWT Token
                    token = generate_jwt_token(user)

                    # Set the token in an HTTP-only cookie
                    response = JsonResponse({"success": True, "message": "Login successful"})
                    response.set_cookie(
                        'jwt_token',
                        token,
                        max_age=datetime.timedelta(days=1),
                        httponly=True, # Cannot be accessed via JavaScript
                        secure=True, # Use only over HTTPS
                        samesite='Strict' # Protects against CSRF attacks
                    )
                    return response
                else:
                    return JsonResponse({"error": "Face not recognized"}, status=401)
            else:
                return JsonResponse({"error": "No matching face found"}, status=401)

        except Exception as e:
            logger.error(f"Error during Rekognition process: {e}", exc_info=True)
            return JsonResponse({"error": f"Rekognition error: {str(e)}"}, status=500)

    def get_user_by_face_id(self, face_id):
        """
        Retrieves user by face_id.
        """
        try:
            dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
            table = dynamodb.Table(settings.AWS_DYNAMO_TABLE_NAME)
            logger.debug(f"Searching for user with face_id: {face_id}")

            response = table.scan(
                FilterExpression=Attr('face_id').eq(str(face_id))
            )

            if 'Items' in response and response['Items']:
                user_data = response['Items'][0]
                # Create a User instance from the response
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    face_id=user_data['face_id']
                )
                return user
            else:
                return None

        except Exception as e:
            logger.error(f"Error retrieving user from DynamoDB: {e}", exc_info=True)
            return None
        
class LoanApplicationViewSet(viewsets.ModelViewSet):
    queryset = LoanApplication.objects.all()
    serializer_class = LoanApplicationSerializer
    http_method_names = ['get', 'post', 'delete']

    def create(self, request, *args, **kwargs):
        customer = auth_user_is(request, ["customer"])

        # Extract data from the request
        try:
            data = request.data.copy()
            monthly_income = int(data["monthly_income"])
            monthly_expenses = int(data["monthly_expenses"])
            amount = int(data["amount"])
            duration = int(data["duration"])

            input_data = {
                'monthly_income': monthly_income,
                'monthly_expenses': monthly_expenses,
                'loan_amount': amount,
                'loan_duration': duration,
            }

            workflow_result = self.workflow(input_data)

            if workflow_result["status"] == "SUCCEEDED":
                output = workflow_result["output"]
                credit_score = output["body"]["Credit_Score"]
                application_status = output["body"]["Loan_Status"]

                # Add results to the data
                data['credit_score'] = credit_score
                data['application_status'] = application_status
                data['username'] = customer['username']

                # Serialize and create the object
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
            else:
                # Log more details for debugging
                return JsonResponse({
                    "status": workflow_result["status"],
                    "message": workflow_result.get("message", "Error processing workflow."),
                    "details": workflow_result.get("details", "Additional information not available.")
                })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def list(self, request, *args, **kwargs):
        user_role = auth_user_is(request, ["officer", "customer"])

        if user_role == "customer":
            # Only include applications belonging to the authenticated customer
            self.queryset = self.queryset.filter(customer=request.user)

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        user_role = auth_user_is(request, ["officer", "customer"])

        instance = self.get_object()
        if user_role == "customer" and instance.customer != request.user:
            # Prevent access to records that don't belong to the authenticated customer
            return Response({"error": "You are not authorized to access this application."}, status=403)

        return super().retrieve(request, *args, **kwargs)
    
    def workflow(self, input_data):
        """
        Starts the workflow and retrieves the results.
        """
        execution_name = f"execution_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        state_machine_arn = os.environ["LOAN_WORKFLOW_STATE_MACHINE_ARN"]

        # Initialize the Workflow
        response = start_workflow(execution_name, input_data, state_machine_arn)

        if response:
            execution_arn = response.get("executionArn")
            time.sleep(5) 
            
            result = get_workflow_result(execution_arn)
            return result
        else:
            return {"status": "erro", "message": "Could not start the workflow"}
    
class LoanEvaluationViewSet(viewsets.ModelViewSet):
    queryset = LoanEvaluation.objects.all()
    serializer_class = LoanEvaluationSerializer