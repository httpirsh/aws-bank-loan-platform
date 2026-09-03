from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
import boto3
from datetime import datetime, timedelta, timezone
import jwt
import json
import logging

logger = logging.getLogger(__name__)

def generate_jwt_token(user):
    """Generate JWT token for the user."""
    payload = {
        'username': user.username,
        'email': user.email,
        'exp': datetime.now(timezone.utc) + timedelta(days=1)  # Use timezone-aware datetime
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    return token

def get_jwt_decoded(request):
    """Get and Decode the JWT token (from the Authorization header or cookie)."""
   
    # Check for token in cookies
    token = request.COOKIES.get('jwt_token')
    
    # If no token in cookies, try to get it from the Authorization header
    if not token:
        authorization_header = request.headers.get('Authorization')
        if authorization_header:
            # Extract token from the "Bearer <token>" format
            token = authorization_header.split(' ')[1] if authorization_header.startswith('Bearer ') else None
        if not token:
            raise Exception("Session not authenticated. JWT token not present.")
    
    # Decode the token using the secret key to get the user data
    token_decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
    return token_decoded
    
def decode_jwt_token(token):
    """
    Decodes the JWT token and returns the payload (user data).
    """
    try:
        # Decode JWT using the secret key and algorithm
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
    
def get_user_from_dynamodb(username):
    """
    Retrieves a user from DynamoDB based on username.
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
        table = dynamodb.Table(settings.AWS_DYNAMO_TABLE_NAME)

        response = table.get_item(Key={'username': username})
        if 'Item' in response:
            return response['Item']
        else:
            return None
    except Exception as e:
        print(f"Error retrieving user from DynamoDB: {e}")
        return None
    
def auth_user_is(request, user_type):
    """
    Retrieves the authenticated user from session and returns the user data if user_type matches.
    If session not authenticated or user is not of user_type, returns None.
    """
    try:
        user_data = get_jwt_decoded(request)
        username = user_data.get("username")

        # Verify if user in session is a customer in our system
        user = get_user_from_dynamodb(username)
        if (user and user['user_type'] in user_type):
            return user
    except Exception as e:
        logger.error(f"Error occurred retrieving authentication data: {e}", exc_info=True)

    raise AuthenticationFailed(detail=f"Session is not authenticated with a user profile in {user_type}.")

def start_workflow(execution_name, input_data, state_machine_arn):
    """
    Starts an execution of Step Functions.
    """
    stepfunctions_client = boto3.client('stepfunctions')

    try:
        response = stepfunctions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(input_data)
        )
        return response
    except Exception as e:
        print(f"Error starting workflow: {str(e)}")
        return None


def get_workflow_result(execution_arn):
    """
    Retrieves the result of a Step Functions execution.
    """
    stepfunctions_client = boto3.client('stepfunctions')

    try:
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        status = response.get("status")
        if status == "SUCCEEDED":
            output = json.loads(response.get("output", "{}"))
            return {"status": "SUCCEEDED", "output": output}
        else:
            return {"status": status, "message": "Execution still in progress or failed."}
    except Exception as e:
        print(f"Error retrieving workflow result: {str(e)}")
        return {"status": "error", "message": "Could not retrieve the result."}
    

