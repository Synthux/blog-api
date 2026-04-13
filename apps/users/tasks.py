import logging

from celery import shared_task

logger = logging.getLogger('users')


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_welcome_email_task(user_id: int) -> None:
    """
    Send a welcome email asynchronously after user registration.
    """
    from apps.users.emails import send_welcome_email
    from apps.users.models import User

    try:
        user = User.objects.get(id=user_id)
        send_welcome_email(user)
        logger.info('Welcome email task completed for user id=%d', user_id)
    except User.DoesNotExist:
        logger.error('send_welcome_email_task: User %d not found', user_id)
