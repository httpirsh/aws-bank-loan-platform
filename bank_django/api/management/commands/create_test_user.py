import bcrypt
from django.core.management.base import BaseCommand

from api.models import User

class Command(BaseCommand):
    help = 'Adds test users (customers and bank employees) to DynamoDB'

    def handle(self, *args, **kwargs):
        # Adding a customer
        add_user_to_dynamodb(
            self,
            username='iris',
            email='iris@example.com',
            phone='1234567890',
            user_type='customer'
        )

        # Adding an officer
        add_user_to_dynamodb(
            self,
            username='Íris',
            email='iris.officer@bank.com',
            phone='0987654321',
            user_type='officer',
            password='securepassword123'
        )

def add_user_to_dynamodb(command, username, email, phone, user_type, password=None, face_id=None):
    try:
        # If the user is an officer, hash the password before storing it
        if user_type == 'officer' and password:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            face_id = None  # Officers do not have a face_id
        else:
            hashed_password = None


        # Add the user to the DynamoDB table
        User.get_dynamo_table().put_item(
            Item={
                'username': username,
                'email': email,
                'phone': phone,
                'user_type': user_type,  # 'customer' or 'officer',
                'face_id': face_id,
                'password': hashed_password,
            }
        )
        command.stdout.write(command.style.SUCCESS(f"{username} added"))
    except Exception as e:
        command.stdout.write(command.style.ERROR(f"Failed to add {username}: {e}"))

