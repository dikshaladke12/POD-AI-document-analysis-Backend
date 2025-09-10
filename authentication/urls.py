from django.urls import path
from .views.authviews import (
    RegisterUser, 
    LoginUser,
    SendForgotPasswordOtp,
    VerifyForgotPasswordOtp,
    ResetForgotPassword,
    GetUserDetails
    )
from .views.emailviews import *

urlpatterns = [
  
    path('register/', RegisterUser.as_view(), name='register'),
    path('login/', LoginUser.as_view(), name='login'),
    path('profile/', GetUserDetails.as_view(), name='login'),
    path('forgot-password/email/', SendForgotPasswordOtp.as_view(), name='forgot-password-email'),
    path('forgot-password/verify/', VerifyForgotPasswordOtp.as_view(), name='forgot-password-verify'),
    path('forgot-password/reset/', ResetForgotPassword.as_view(), name='forgot-password-reset'),

    # path('forgot-password/send-otp/', SendOtpView.as_view(), name='send-otp'),
    # path('forgot-password/verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    # path('forgot-password/reset/', ResetPasswordView.as_view(), name='reset-password'),
    
    # path('getroles/', RolesListView.as_view(), name='getroles'),
    # path('superuserlogin/', SuperUserLogin.as_view(), name='login'),
    # path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),
    # path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    # path('<int:id>/', UserView.as_view(), name='userview'),
    # path('forgotpassword/', ForgotPasswordView.as_view(), name='forgotpassword'),
    # path('resetpassword/', ResetPasswordView.as_view(), name='resetpassword'),
    # path('verifyemail-otp/', VerifyEmailOtpView.as_view(), name='verifyemail-otp'),
    # path('forgotpassword-otp/', ForgotPasswordOtpView.as_view(), name='forgotpasswordotp'),
    # path('email/', varification_mail, name='email'),
]
