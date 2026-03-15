import logging

import pytz
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

SUPPORTED_LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
    ('kk', _('Kazakh')),
]


logger = logging.getLogger('users')


class CustomUserManager(BaseUserManager):
    """Custom manager for User model with email as username field."""
    
    def create_user(self, email: str, password: str, **extra_fields) -> 'User':
        """Create and save a regular user with email and password."""
        if not email:
            logger.error('User creation failed: email not provided')
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        logger.info('User created: %s', email)
        return user
    
    def create_superuser(self, email: str, password: str, **extra_fields) -> 'User':
        """Create and save a superuser with email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as the primary identifier."""
    
    email = models.EmailField(unique=True, max_length=255, verbose_name=_('email address'))
    first_name = models.CharField(max_length=50, verbose_name=_('first name'))
    last_name = models.CharField(max_length=50, verbose_name=_('last name'))
    is_active = models.BooleanField(default=True, verbose_name=_('active'))
    is_staff = models.BooleanField(default=False, verbose_name=_('staff status'))
    date_joined = models.DateTimeField(default=timezone.now, verbose_name=_('date joined'))
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name=_('avatar'))

    preferred_language = models.CharField(
        max_length=10,
        choices=SUPPORTED_LANGUAGES,
        default='en',
        blank=True,
        verbose_name=_('preferred language'),
    )
    timezone = models.CharField(
        max_length=100,
        default='UTC',
        blank=True,
        verbose_name=_('timezone'),
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self) -> str:
        return self.email
    
    def get_full_name(self) -> str:
        """Return the user's full name."""
        return f'{self.first_name} {self.last_name}'.strip()
