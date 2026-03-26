from django.contrib import admin
from .models import DashboardMetrics, CommonInquiry, ResponseTimeData


@admin.register(DashboardMetrics)
class DashboardMetricsAdmin(admin.ModelAdmin):
    readonly_fields = ('last_updated',)
    fields = ('total_chats', 'active_users', 'avg_response_time', 'satisfaction_rate',
              'chats_change', 'users_change', 'response_time_change', 'satisfaction_change', 'last_updated')


@admin.register(CommonInquiry)
class CommonInquiryAdmin(admin.ModelAdmin):
    list_display = ('title', 'count', 'percentage')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ResponseTimeData)
class ResponseTimeDataAdmin(admin.ModelAdmin):
    list_display = ('date', 'average_response_time', 'min_response_time', 'max_response_time')
    list_filter = ('date',)
