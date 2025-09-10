from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from ..serializers import (
    UserSerializer,
    ForgotPasswordOtpSerializer,
    ResetPasswordSerializer,
)
from ..models import *
from rest_framework.permissions import AllowAny, IsAuthenticated
import random
from django.core.mail import send_mail
from FAX_POD import constants, settings, utils
from django.contrib.auth.hashers import check_password
from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password

import logging
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema


logger = logging.getLogger(__name__)


class RegisterUser(APIView):
    @swagger_auto_schema(request_body=UserSerializer)
    def post(self, request):
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                data = {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                }
                return utils.success_response(
                    message="User registered successfully.",
                    data=data,
                    status_code=status.HTTP_201_CREATED,
                    api_status_code=status.HTTP_201_CREATED,
                )
            return utils.error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                api_status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return utils.error_response(
                message="Error while registering user.",
                errors=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                api_status_code=status.HTTP_400_BAD_REQUEST,
            )


from authentication.models import *
class LoginUser(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # encryptedData = request.data.get('payload')
        # decryptedData = utils.decrypt_data(encryptedData)
        # print("decryptedData : ",decryptedData)
        email = request.data.get('email')
        password = request.data.get('password')

        # Step 1: Validate presence of email and password
        if not email or not password:
            return Response({
                "message": "Email and password are required.",
                "status": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Authenticate user
        user = authenticate(request, email=email, password=password)

        # Step 3: If authenticated, return JWT tokens
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Login successful.",
                "data": {
                    "user_id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "token": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    }
                },
                "status": 200
            }, status=status.HTTP_200_OK)

        # Step 4: If credentials are invalid
        return Response({
            "message": "Invalid email or password.",
            "status": 400
        }, status=status.HTTP_400_BAD_REQUEST)


class SendForgotPasswordOtp(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return utils.error_response("Email is required")

        try:
            user = Users.objects.get(email=email, is_deleted=False)
        except Users.DoesNotExist:
            return utils.error_response("No user registered with this email.")

        otp = random.randint(100000, 999999)
        user.otp_code = str(otp)
        user.otp_created_at = timezone.now()
        user.save()

        # 📨 In production, send via email
        print("Generated OTP:", otp)

        return utils.success_response(
            message="Verification code sent successfully.",
            data={"email": user.email}
        )


class VerifyForgotPasswordOtp(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return utils.error_response("Invalid data", errors=serializer.errors)

        email = serializer.validated_data['email']
        otp = str(serializer.validated_data['otp'])

        try:
            user = Users.objects.get(email=email, is_deleted=False)
        except Users.DoesNotExist:
            return utils.error_response("User not found.")

        if not user.is_otp_valid(otp):
            return utils.error_response("OTP is incorrect or expired.")

        user.clear_otp()  # OTP can only be used once
        return utils.success_response("OTP verified successfully.")


class ResetForgotPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return utils.error_response("Invalid data", errors=serializer.errors)

        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']

        try:
            user = Users.objects.get(email=email, is_deleted=False)
        except Users.DoesNotExist:
            return utils.error_response("User not found.")

        user.password = make_password(new_password)
        user.save()

        return utils.success_response("Password updated successfully.")


class GetUserDetails(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user  # Comes from token
            # If you're using custom user model, request.user will be instance of `Users`
            serializer = UserSerializer(user)

            return utils.success_response(
                message="User details fetched successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                api_status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to fetch user details.",
                errors=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                api_status_code=status.HTTP_400_BAD_REQUEST,
            )
