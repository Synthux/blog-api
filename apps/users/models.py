import logging

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

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
    
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
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
