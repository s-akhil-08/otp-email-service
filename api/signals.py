import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import User
from .email_backends import SignalEmailBackend

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def send_user_creation_notification(sender, instance, created, **kwargs):
    """
    Signal to notify admin when a new user is created and send a welcome email to the user.
    """
    if created and not instance.is_superuser:
        admin_subject = 'New User Registration Notification'
        admin_context = {
            'user': instance,
            'settings': settings,
        }
        admin_html_message = render_to_string('emails/admin_user_creation.html', admin_context)
        admin_plain_message = strip_tags(admin_html_message)

        try:
            admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', settings.DEFAULT_FROM_EMAIL)
            send_mail(
                subject=admin_subject,
                message=admin_plain_message,
                from_email=settings.SIGNAL_DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                html_message=admin_html_message,
                fail_silently=False,
                connection=SignalEmailBackend(),
            )
            logger.info(f"Signal: Admin notification sent for user {instance.email}")
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")

        # Send welcome email to user
        user_subject = 'Welcome to CADverse!'
        user_context = {
            'user': instance,
            'settings': settings,
        }
        user_html_message = render_to_string('emails/welcome_email.html', user_context)
        user_plain_message = strip_tags(user_html_message)

        try:
            send_mail(
                subject=user_subject,
                message=user_plain_message,
                from_email=settings.SIGNAL_DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=user_html_message,
                fail_silently=False,
                connection=SignalEmailBackend(),
            )
            logger.info(f"Signal: Welcome email sent to {instance.email}")
        except Exception as e:
            logger.error(f"Error sending welcome email to user: {e}")
