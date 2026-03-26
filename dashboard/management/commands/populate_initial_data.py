from django.core.management.base import BaseCommand
from dashboard.models import DashboardMetrics, CommonInquiry, ResponseTimeData
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Populate initial dashboard data'

    def handle(self, *args, **options):
        # Clear existing data (only if tables exist)
        try:
            DashboardMetrics.objects.all().delete()
        except:
            pass  # Tables might not exist yet
        
        try:
            CommonInquiry.objects.all().delete()
        except:
            pass  # Tables might not exist yet
            
        try:
            ResponseTimeData.objects.all().delete()
        except:
            pass  # Tables might not exist yet
        
        # Create initial metrics
        metrics = DashboardMetrics.objects.create(
            total_chats=1247,
            active_users=342,
            avg_response_time=2.1,
            satisfaction_rate=94.0,
            chats_change=12.5,
            users_change=8.2,
            response_time_change=-5.3,
            satisfaction_change=3.1
        )
        self.stdout.write(self.style.SUCCESS('✓ Dashboard metrics created'))
        
        # Create common inquiries
        inquiries = [
            {'title': 'Account Help', 'count': 45},
            {'title': 'Technical Support', 'count': 38},
            {'title': 'General Info', 'count': 30},
            {'title': 'Billing', 'count': 25},
            {'title': 'Other', 'count': 20},
        ]
        
        for inq in inquiries:
            CommonInquiry.objects.create(
                title=inq['title'],
                count=inq['count'],
                percentage=(inq['count'] / sum([i['count'] for i in inquiries])) * 100
            )
        
        self.stdout.write(self.style.SUCCESS('✓ Common inquiries created'))
        
        # Create response time data for the past 7 days
        today = datetime.now().date()
        response_times = [
            (2.4, 1.2, 3.8),
            (1.8, 0.9, 3.2),
            (2.2, 1.1, 3.5),
            (1.9, 0.8, 3.1),
            (3.2, 1.5, 4.2),
            (2.8, 1.3, 4.0),
            (2.5, 1.0, 3.8),
        ]
        
        for i, (avg, min_time, max_time) in enumerate(response_times):
            date = today - timedelta(days=6-i)
            ResponseTimeData.objects.create(
                date=date,
                average_response_time=avg,
                min_response_time=min_time,
                max_response_time=max_time
            )
        
        self.stdout.write(self.style.SUCCESS('✓ Response time data created'))
        self.stdout.write(self.style.SUCCESS('\n✓ All initial data loaded successfully!'))
