from django.test import TestCase
from django.urls import reverse
from .models import DashboardMetrics, CommonInquiry, ResponseTimeData


class DashboardViewTests(TestCase):
    
    def setUp(self):
        self.metrics = DashboardMetrics.objects.create(
            total_chats=1247,
            active_users=342,
            avg_response_time=2.1,
            satisfaction_rate=94.0,
            chats_change=12.5,
            users_change=8.2,
            response_time_change=-5.3,
            satisfaction_change=3.1
        )
    
    def test_dashboard_view_status(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_view_template(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertTemplateUsed(response, 'dashboard/index.html')
    
    def test_dashboard_view_context(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertIn('metrics', response.context)
        self.assertIn('inquiries', response.context)
        # new variables used for pie chart data
        self.assertIn('inquiry_labels', response.context)
        self.assertIn('inquiry_counts', response.context)
        # colors and items for legend/chart
        self.assertIn('inquiry_colors', response.context)
        self.assertIn('inquiry_items', response.context)


class DashboardMetricsTests(TestCase):
    
    def test_create_metrics(self):
        metrics = DashboardMetrics.objects.create(
            total_chats=1000,
            active_users=300,
            avg_response_time=2.0,
            satisfaction_rate=90.0
        )
        self.assertEqual(metrics.total_chats, 1000)
        self.assertEqual(metrics.active_users, 300)


class APITests(TestCase):
    
    def test_chart_data_api(self):
        response = self.client.get(reverse('dashboard:chart_data'))
        self.assertEqual(response.status_code, 200)
    
    def test_inquiries_data_api(self):
        response = self.client.get(reverse('dashboard:inquiries_data'))
        self.assertEqual(response.status_code, 200)
