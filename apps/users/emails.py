import logging

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation

logger = logging.getLogger('users')


def send_welcome_email(user) -> None:
    """
    Send a welcome email in the user's chosen language.
    Uses translation.override() so the email language is always
    the user's preference, regardless of what language the current
    request thread has activated.
    """
    lang = getattr(user, 'preferred_language', 'en') or 'en'
    with translation.override(lang):
        subject = render_to_string('emails/welcome/subject.txt', {'user': user}).strip()
        body = render_to_string('emails/welcome/body.html', {'user': user})

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[user.email],
            html_message=body,
        )
        logger.info('Welcome email sent to %s in language %s', user.email, lang)
    except Exception as exc:
        logger.error('Failed to send welcome email to %s: %s', user.email, exc)
