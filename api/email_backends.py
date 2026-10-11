from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.conf import settings

class SignalEmailBackend(SMTPBackend):

    def __init__(self, *args, **kwargs):
        super().__init__(
            host=settings.SIGNAL_EMAIL_HOST,
            port=settings.SIGNAL_EMAIL_PORT,
            username=settings.SIGNAL_EMAIL_HOST_USER,
            password=settings.SIGNAL_EMAIL_HOST_PASSWORD,
            use_tls=settings.SIGNAL_EMAIL_USE_TLS,
            fail_silently=kwargs.get('fail_silently', False),
            **kwargs
        )
