from django.db import models
from django.contrib.auth.models import AbstractUser


class Student(AbstractUser):
    """Custom user model for IntelliChat students."""

    email = models.EmailField(
        unique=True,
        help_text='Must be a TIP (@tip.edu.ph) or Gmail (@gmail.com) email',
    )

    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # Use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
