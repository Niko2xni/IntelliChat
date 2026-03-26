from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class Student(AbstractUser):
    """Custom user model for IntelliChat students."""

    student_number = models.CharField(
        max_length=7,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$',
                message='Student number must be exactly 7 digits.',
            ),
        ],
        help_text='7-digit student number',
    )

    email = models.EmailField(
        unique=True,
        help_text='Must be a TIP email (@tip.edu.ph)',
    )

    # Use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'student_number']

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_number})"
