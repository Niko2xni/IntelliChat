from django.db import models
from django.utils import timezone


class DashboardMetrics(models.Model):
    total_chats = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0.0)
    satisfaction_rate = models.FloatField(default=0.0)
    
    # Percentage changes from last week
    chats_change = models.FloatField(default=0.0)
    users_change = models.FloatField(default=0.0)
    response_time_change = models.FloatField(default=0.0)
    satisfaction_change = models.FloatField(default=0.0)
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Dashboard Metrics"

    def __str__(self):
        return f"Dashboard Metrics - {self.last_updated}"


class CommonInquiry(models.Model):
    title = models.CharField(max_length=255)
    count = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Common Inquiries"
        ordering = ['-count']

    def __str__(self):
        return self.title


class ResponseTimeData(models.Model):
    date = models.DateField()
    average_response_time = models.FloatField()
    min_response_time = models.FloatField()
    max_response_time = models.FloatField()

    class Meta:
        verbose_name_plural = "Response Time Data"
        ordering = ['-date']


class FAQ(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()
    tags = models.CharField(max_length=200, help_text="Comma-separated tags")
    category = models.CharField(max_length=100, choices=[
        ('general', 'General'),
        ('technical', 'Technical'),
        ('billing', 'Billing'),
        ('account', 'Account'),
        ('features', 'Features'),
    ], default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['-created_at']

    def __str__(self):
        return self.question

    def get_tags_list(self):
        """Return tags as a list."""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


class Document(models.Model):
    CATEGORY_CHOICES = [
        ('templates', 'Templates'),
        ('forms', 'Forms'),
        ('guidelines', 'Guidelines'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=50)  # PDF, DOCX, XLSX, etc
    file_size = models.IntegerField()  # in bytes
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    uploaded_by = models.CharField(max_length=100, default='Admin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.title

    def __str__(self):
        return f"{self.date} - Avg: {self.average_response_time}s"
