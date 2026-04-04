from django.core.management.base import BaseCommand
from dashboard.models import DashboardMetrics, CommonInquiry, ResponseTimeData, FAQ
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Seeds the Neon PostgreSQL database with initial dashboard data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding dashboard data...\n')

        # --- Dashboard Metrics ---
        if not DashboardMetrics.objects.exists():
            DashboardMetrics.objects.create(
                total_chats=1247,
                active_users=342,
                avg_response_time=2.1,
                satisfaction_rate=94.0,
                chats_change=12.5,
                users_change=8.2,
                response_time_change=-5.3,
                satisfaction_change=3.1,
            )
            self.stdout.write(self.style.SUCCESS('  ✓ Dashboard Metrics created'))
        else:
            self.stdout.write('  - Dashboard Metrics already exist, skipping')

        # --- Common Inquiries ---
        if not CommonInquiry.objects.exists():
            inquiries = [
                {'title': 'Account Help', 'count': 45, 'percentage': 28.5},
                {'title': 'Technical Support', 'count': 38, 'percentage': 24.1},
                {'title': 'General Info', 'count': 30, 'percentage': 19.0},
                {'title': 'Billing', 'count': 25, 'percentage': 15.8},
                {'title': 'Other', 'count': 20, 'percentage': 12.7},
            ]
            for inq in inquiries:
                CommonInquiry.objects.create(**inq)
            self.stdout.write(self.style.SUCCESS('  ✓ Common Inquiries created (5 entries)'))
        else:
            self.stdout.write('  - Common Inquiries already exist, skipping')

        # --- Response Time Data (last 14 days) ---
        if not ResponseTimeData.objects.exists():
            today = date.today()
            response_data = [
                (0, 2.1, 0.8, 4.5),
                (1, 1.9, 0.7, 3.8),
                (2, 2.3, 1.0, 5.2),
                (3, 2.0, 0.6, 4.1),
                (4, 1.8, 0.5, 3.5),
                (5, 2.5, 1.1, 5.8),
                (6, 2.2, 0.9, 4.9),
                (7, 2.4, 1.0, 5.0),
                (8, 1.7, 0.4, 3.2),
                (9, 2.0, 0.7, 4.3),
                (10, 1.9, 0.6, 3.9),
                (11, 2.1, 0.8, 4.6),
                (12, 2.3, 0.9, 5.1),
                (13, 2.0, 0.7, 4.0),
            ]
            for days_ago, avg, min_t, max_t in response_data:
                ResponseTimeData.objects.create(
                    date=today - timedelta(days=days_ago),
                    average_response_time=avg,
                    min_response_time=min_t,
                    max_response_time=max_t,
                )
            self.stdout.write(self.style.SUCCESS('  ✓ Response Time Data created (14 days)'))
        else:
            self.stdout.write('  - Response Time Data already exist, skipping')

        # --- FAQs ---
        if not FAQ.objects.exists():
            faqs = [
                {
                    'question': 'How do I reset my password?',
                    'answer': 'Go to Settings > Account > Change Password. Enter your current password and set a new one. Your password must be at least 8 characters long.',
                    'tags': 'password, account, security',
                    'category': 'account',
                },
                {
                    'question': 'How do I contact support?',
                    'answer': 'You can reach our support team through the chatbot, by emailing support@tip.edu.ph, or by visiting the IT helpdesk at Room 301.',
                    'tags': 'support, contact, help',
                    'category': 'general',
                },
                {
                    'question': 'What are the system requirements?',
                    'answer': 'IntelliChat works on any modern web browser (Chrome, Firefox, Edge, Safari). A stable internet connection is recommended for the best experience.',
                    'tags': 'requirements, browser, technical',
                    'category': 'technical',
                },
                {
                    'question': 'How do I update my student information?',
                    'answer': 'Your information can be updated through the Profile page. Some fields like your name are locked and can only be changed by an administrator.',
                    'tags': 'profile, student, update',
                    'category': 'account',
                },
                {
                    'question': 'Is the chatbot available 24/7?',
                    'answer': 'Yes! IntelliChat is available around the clock. However, human support agents are only available during office hours (8am - 5pm, Monday to Friday).',
                    'tags': 'availability, hours, chatbot',
                    'category': 'general',
                },
                {
                    'question': 'How do I enroll in subjects?',
                    'answer': 'Enrollment is done through the TIP Student Portal. Log in with your student credentials, navigate to Enrollment, and follow the on-screen instructions during the enrollment period.',
                    'tags': 'enrollment, subjects, registration',
                    'category': 'general',
                },
            ]
            for faq_data in faqs:
                FAQ.objects.create(**faq_data)
            self.stdout.write(self.style.SUCCESS('  ✓ FAQs created (6 entries)'))
        else:
            self.stdout.write('  - FAQs already exist, skipping')

        self.stdout.write(self.style.SUCCESS('\nDone! All seed data has been loaded.'))
