from django.db import models
from django.contrib.auth.models import AbstractUser


class Student(AbstractUser):
    """Custom user model for IntelliChat students."""

    ADMIN_EMAIL_DOMAIN = '@intellichat.com'
    ACCOUNT_GENERAL = 'general'
    ACCOUNT_STUDENT_LEADER = 'student_leader'
    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_GENERAL, 'General'),
        (ACCOUNT_STUDENT_LEADER, 'Student Leader'),
    ]

    email = models.EmailField(
        unique=True,
        help_text='Must be a TIP (@tip.edu.ph) email',
    )

    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    account_type = models.CharField(
        max_length=30,
        choices=ACCOUNT_TYPE_CHOICES,
        default=ACCOUNT_GENERAL,
    )
    leader_organization = models.CharField(max_length=150, blank=True)
    leader_position = models.CharField(max_length=100, blank=True)

    # Use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    @property
    def is_dashboard_admin(self):
        email = (self.email or '').strip().lower()
        return (
            self.is_active
            and self.is_staff
            and (
                self.is_superuser
                or email.endswith(self.ADMIN_EMAIL_DOMAIN)
            )
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class ChatSession(models.Model):
    user = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
    )
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.user.email})"


class ChatMessage(models.Model):
    USER = 'user'
    ASSISTANT = 'assistant'
    ROLE_CHOICES = [
        (USER, 'User'),
        (ASSISTANT, 'Assistant'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"{self.session_id}:{self.role}"
