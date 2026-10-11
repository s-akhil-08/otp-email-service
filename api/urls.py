from django.urls import path
from . import views

urlpatterns = [
    # Signup OTP Endpoints
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),

    # Password Reset OTP Endpoints
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-reset-otp/', views.VerifyPasswordResetOTPView.as_view(), name='verify-reset-otp'),
    path('verify-forgot-otp/', views.VerifyPasswordResetOTPView.as_view(), name='verify-forgot-otp'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),

    # Utility OTP Endpoints
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),

    # Signal & Trigger Email Endpoints
    path('send-message/', views.SendMessageView.as_view(), name='send-message'),
    path('trigger-email/', views.TriggerSignalEmailView.as_view(), name='trigger-email'),
]
