import logging
import random
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.timezone import now, timedelta
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from supabase import Client, create_client

from .models import PasswordChangeHistory, TempUser, User
from .serializers import (
    ForgotPasswordSerializer,
    OTPVerificationSerializer,
    ResendOTPSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)

# Initialize Supabase client if keys are available
supabase: Client = None
try:
    supabase_url = getattr(settings, 'SUPABASE_URL_1', getattr(settings, 'SUPABASE_URL', None))
    supabase_key = getattr(settings, 'SUPABASE_KEY', None)
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
except Exception as e:
    logger.warning(f"Supabase client initialization skipped: {e}")


class SignupView(APIView):
    """
    POST /api/signup/
    Accepts: { email, name, mobile, password, confirmPassword }
    Generates 6-digit OTP and sends HTML verification email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"Signup attempt with data: {request.data}")
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            temp_user = serializer.save()

            plain_message = f"""
Hey {temp_user.name} 👋,

Thank you for signing up for CADverse!

Your verification code is: {temp_user.otp}

⏰ This code is valid for 10 minutes.

If you did not request this, please ignore this email.

Best regards,
The CADverse Team 🚀
            """.strip()

            html_message = render_to_string('emails/otp_verification.html', {
                'otp': temp_user.otp,
                'name': temp_user.name,
                'email': temp_user.email,
            })

            try:
                msg = EmailMultiAlternatives(
                    subject="CADverse - Verify Your Account 🔐",
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[temp_user.email]
                )
                msg.attach_alternative(html_message, "text/html")
                msg.send()

                logger.debug(f"OTP email sent to {temp_user.email}: {temp_user.otp}")
            except Exception as e:
                logger.error(f"Failed to send verification email to {temp_user.email}: {str(e)}")

            return Response({
                'message': 'Signup successful. Verification code sent to your email.'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    """
    POST /api/verify-otp/
    Accepts: { email, otp }
    Validates OTP, converts TempUser into active User, creates Auth Token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"Verifying OTP with data: {request.data}")
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            otp = serializer.validated_data['otp']
            try:
                temp_user = TempUser.objects.get(email__iexact=email, otp=otp)
                if temp_user.created_at < now() - timedelta(minutes=10):
                    temp_user.delete()
                    return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    user = User.objects.create_user(
                        email=temp_user.email,
                        name=temp_user.name,
                        mobile=temp_user.mobile,
                        password=temp_user.raw_password,
                        is_verified=True,
                        is_active=True
                    )
                    token = Token.objects.create(user=user)
                    temp_user.delete()

                    return Response({
                        'message': 'OTP verified successfully',
                        'token': token.key,
                        'user': UserSerializer(user).data
                    }, status=status.HTTP_200_OK)

            except TempUser.DoesNotExist:
                return Response({'error': 'Invalid OTP or email'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """
    POST /api/forgot-password/
    Accepts: { email }
    Generates 6-digit OTP, caches it for 5 minutes, sends HTML email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].strip().lower()

            user_exists = User.objects.filter(email__iexact=email).exists()
            if not user_exists and supabase:
                try:
                    res = supabase.table('api_user').select('email').eq('email', email).execute()
                    if res.data:
                        user_exists = True
                except Exception as ex:
                    logger.warning(f"Supabase user check error: {ex}")

            if not user_exists:
                return Response(
                    {"error": "User does not exist. Please create an account."},
                    status=status.HTTP_404_NOT_FOUND
                )

            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

            cache_key = f"forgot_otp_{email}"
            cache.set(cache_key, otp, timeout=300)
            cache.set(f"otp_{email}", otp, timeout=300)

            logger.debug(f"Password reset OTP generated for {email}: {otp}")

            plain_message = f"""
Hey 👋,

We received a request to reset your CADverse password.

Your verification code is: {otp}

⏰ This code expires in 5 minutes.

If you didn't request this, please ignore this email.

Stay safe,
The CADverse Team 🔒
            """.strip()

            html_message = render_to_string('emails/password_reset_otp.html', {
                'otp': otp,
                'email': email,
            })

            try:
                msg = EmailMultiAlternatives(
                    subject="CADverse - Password Reset Code 🔑",
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                msg.attach_alternative(html_message, "text/html")
                msg.send()

                logger.info(f"Password reset OTP email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {str(e)}")
                return Response(
                    {"error": "Failed to send OTP email. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {"message": "Password reset code sent to your email."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPasswordResetOTPView(APIView):
    """
    POST /api/verify-reset-otp/
    Accepts: { email, otp }
    Validates reset OTP from cache, returns a 5-minute valid reset_token UUID.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].strip().lower()
            otp_input = str(serializer.validated_data['otp']).strip()

            cache_key = f"forgot_otp_{email}"
            cached_otp = cache.get(cache_key) or cache.get(f"otp_{email}")

            if cached_otp is None:
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)

            if str(cached_otp) != otp_input:
                return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

            reset_token = str(uuid4())
            reset_token_key = f"reset_token_{email}"
            cache.set(reset_token_key, reset_token, timeout=300)

            return Response({
                'message': 'OTP verified successfully',
                'reset_token': reset_token
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    """
    POST /api/reset-password/
    Accepts: { email, reset_token, new_password, confirm_password }
    Validates reset_token, updates password, logs history, clears cache.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].strip().lower()
            reset_token_input = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']

            cache_key = f"reset_token_{email}"
            stored_token = cache.get(cache_key)

            if not stored_token:
                return Response(
                    {"error": "Reset token has expired or does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if stored_token != reset_token_input:
                return Response(
                    {"error": "Invalid reset token."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                user = User.objects.get(email__iexact=email)
                old_password_hashed = user.password
                user.set_password(new_password)
                user.save()

                if supabase:
                    try:
                        supabase.table('api_user').update({
                            'password': user.password
                        }).eq('email', email).execute()
                    except Exception as ex:
                        logger.warning(f"Supabase update error: {ex}")

                PasswordChangeHistory.objects.create(
                    user=user,
                    old_password_hashed=old_password_hashed,
                    new_password_hashed=user.password,
                )

                cache.delete(cache_key)
                cache.delete(f"forgot_otp_{email}")
                cache.delete(f"otp_{email}")

                return Response(
                    {"message": "Password reset successfully."},
                    status=status.HTTP_200_OK
                )

            except User.DoesNotExist:
                return Response(
                    {"error": "User does not exist."},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {"error": f"Error resetting password: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    """
    POST /api/resend-otp/
    Accepts: { email, type: 'signup' | 'forgot_password' }
    Resends fresh OTP for signup or password reset.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].strip().lower()
            otp_type = serializer.validated_data.get('type', 'signup')

            if otp_type == 'signup':
                try:
                    temp_user = TempUser.objects.get(email__iexact=email)
                    new_otp = str(random.randint(100000, 999999))
                    temp_user.otp = new_otp
                    temp_user.created_at = now()
                    temp_user.save()

                    html_message = render_to_string('emails/otp_verification.html', {
                        'otp': new_otp,
                        'name': temp_user.name,
                        'email': temp_user.email,
                    })

                    msg = EmailMultiAlternatives(
                        subject="CADverse - New Verification Code 🔐",
                        body=f"Your new verification code is: {new_otp}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[temp_user.email]
                    )
                    msg.attach_alternative(html_message, "text/html")
                    msg.send()

                    return Response({'message': 'New OTP sent successfully.'}, status=status.HTTP_200_OK)

                except TempUser.DoesNotExist:
                    return Response({'error': 'No pending signup found for this email.'}, status=status.HTTP_404_NOT_FOUND)

            elif otp_type == 'forgot_password':
                return ForgotPasswordView().post(request)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendMessageView(APIView):
    """
    POST /api/send-message/
    Accepts: { subject, message, recipient_email (optional) }
    Triggers sending email via SMTP.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        subject = request.data.get('subject')
        message = request.data.get('message')
        admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', settings.DEFAULT_FROM_EMAIL)
        recipient = request.data.get('recipient_email', admin_email)

        if not subject or not message:
            return Response({'error': 'Subject and message are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.core.mail import send_mail
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            return Response({'message': 'Message triggered and sent successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error sending message trigger: {e}")
            return Response({'error': f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TriggerSignalEmailView(APIView):
    """
    POST /api/trigger-email/
    Triggers specific notification / signal emails on-demand.
    Accepts: {
        template_type: 'welcome' | 'admin_user_creation' | 'admin_project_upload' | 'feedback_approved' | 'custom',
        email: '...',
        name: '...',
        project_name: '...',
        subject: '...',
        message: '...'
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        template_type = request.data.get('template_type')
        email = request.data.get('email')
        name = request.data.get('name', 'Client')
        project_name = request.data.get('project_name', 'CADverse Project')
        subject = request.data.get('subject')
        custom_message = request.data.get('message')

        if not template_type:
            return Response({'error': 'template_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.mail import send_mail
        from django.utils.html import strip_tags
        from .email_backends import SignalEmailBackend

        try:
            if template_type == 'welcome':
                if not email:
                    return Response({'error': 'email is required for welcome template'}, status=status.HTTP_400_BAD_REQUEST)
                subj = subject or 'Welcome to CADverse!'
                html = render_to_string('emails/welcome_email.html', {'user': {'name': name, 'email': email}, 'settings': settings})
                plain = strip_tags(html)
                recipients = [email]

            elif template_type == 'admin_user_creation':
                subj = subject or 'New User Registration Notification'
                html = render_to_string('emails/admin_user_creation.html', {'user': {'name': name, 'email': email or 'N/A'}, 'settings': settings})
                plain = strip_tags(html)
                admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', settings.DEFAULT_FROM_EMAIL)
                recipients = [admin_email]

            elif template_type == 'admin_project_upload':
                subj = subject or 'New Project File Uploaded'
                html = render_to_string('emails/admin_project_upload.html', {
                    'project': {'name': project_name},
                    'user': {'name': name, 'email': email or 'N/A'},
                    'settings': settings
                })
                plain = strip_tags(html)
                admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', settings.DEFAULT_FROM_EMAIL)
                recipients = [admin_email]

            elif template_type == 'feedback_approved':
                if not email:
                    return Response({'error': 'email is required for feedback_approved template'}, status=status.HTTP_400_BAD_REQUEST)
                subj = subject or 'Your Feedback Has Been Approved!'
                html = render_to_string('emails/feedback_approved.html', {
                    'user': {'name': name, 'email': email},
                    'project': {'name': project_name},
                    'feedback': {'feedback_text': custom_message or 'Your feedback was approved.'},
                    'settings': settings
                })
                plain = strip_tags(html)
                recipients = [email]

            elif template_type == 'custom':
                if not email or not subject or not custom_message:
                    return Response({'error': 'email, subject, and message are required for custom template'}, status=status.HTTP_400_BAD_REQUEST)
                subj = subject
                plain = custom_message
                html = f"<p>{custom_message}</p>"
                recipients = [email]

            else:
                return Response({'error': f'Invalid template_type: {template_type}'}, status=status.HTTP_400_BAD_REQUEST)

            send_mail(
                subject=subj,
                message=plain,
                from_email=settings.SIGNAL_DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                html_message=html,
                fail_silently=False,
                connection=SignalEmailBackend(),
            )

            return Response({
                'message': f'Email trigger ({template_type}) executed successfully',
                'recipient': recipients
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error executing email trigger: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

