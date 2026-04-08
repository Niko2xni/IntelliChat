from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from chatbot.models import ChatMessage, ChatSession, Student

from .models import DashboardMetrics


def _create_chat_session(user, title, created_at, response_seconds):
    session = ChatSession.objects.create(user=user, title=title)
    user_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.USER,
        content=title,
    )
    assistant_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ASSISTANT,
        content='Live dashboard response',
    )

    ChatSession.objects.filter(id=session.id).update(
        created_at=created_at,
        updated_at=created_at + timedelta(seconds=response_seconds),
    )
    ChatMessage.objects.filter(id=user_message.id).update(created_at=created_at)
    ChatMessage.objects.filter(id=assistant_message.id).update(
        created_at=created_at + timedelta(seconds=response_seconds),
    )

    session.refresh_from_db()
    return session


class DashboardViewTests(TestCase):
    
    def setUp(self):
        now = timezone.now()

        self.admin_user = Student.objects.create_user(
            email='admin-test@example.com',
            username='admin-test',
            password='password123',
            first_name='Admin',
            last_name='Tester',
        )
        self.admin_user.is_staff = True
        self.admin_user.is_active = True
        self.admin_user.save(update_fields=['is_staff', 'is_active'])
        self.client.force_login(self.admin_user)

        self.student_one = Student.objects.create_user(
            email='student-one@example.com',
            username='student-one',
            password='password123',
            first_name='Student',
            last_name='One',
        )
        self.student_two = Student.objects.create_user(
            email='student-two@example.com',
            username='student-two',
            password='password123',
            first_name='Student',
            last_name='Two',
        )

        _create_chat_session(
            self.student_one,
            'Where is OSA office located',
            now - timedelta(days=1),
            42,
        )
        _create_chat_session(
            self.student_two,
            'I need a copy of the TIP student manual',
            now - timedelta(days=2),
            55,
        )
        _create_chat_session(
            self.student_one,
            'Where is OSA office located',
            now - timedelta(days=9),
            30,
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
        self.assertIn('response_time_labels', response.context)
        self.assertIn('response_time_values', response.context)
        self.assertEqual(response.context['metrics'].total_chats, 3)
        self.assertEqual(response.context['metrics'].active_users, 2)
        self.assertEqual(response.context['metrics'].chats_change, 100.0)
        self.assertEqual(response.context['metrics'].users_change, 100.0)
        self.assertEqual(response.context['inquiry_labels'][0], 'Where is OSA office located')
        self.assertEqual(response.context['inquiry_counts'][0], 2)
        self.assertEqual(response.context['response_time_values'], [30.0, 55.0, 42.0])


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

    def setUp(self):
        now = timezone.now()

        self.admin_user = Student.objects.create_user(
            email='admin-api@example.com',
            username='admin-api',
            password='password123',
            first_name='Admin',
            last_name='API',
        )
        self.admin_user.is_staff = True
        self.admin_user.is_active = True
        self.admin_user.save(update_fields=['is_staff', 'is_active'])
        self.client.force_login(self.admin_user)

        self.student_one = Student.objects.create_user(
            email='student-api-one@example.com',
            username='student-api-one',
            password='password123',
            first_name='Student',
            last_name='API One',
        )
        self.student_two = Student.objects.create_user(
            email='student-api-two@example.com',
            username='student-api-two',
            password='password123',
            first_name='Student',
            last_name='API Two',
        )

        _create_chat_session(
            self.student_one,
            'Where is OSA office located',
            now - timedelta(days=1),
            42,
        )
        _create_chat_session(
            self.student_two,
            'I need a copy of the TIP student manual',
            now - timedelta(days=2),
            55,
        )
        _create_chat_session(
            self.student_one,
            'Where is OSA office located',
            now - timedelta(days=9),
            30,
        )
    
    def test_chart_data_api(self):
        response = self.client.get(reverse('dashboard:chart_data'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('dates', response.json())
        self.assertIn('times', response.json())
        self.assertEqual(response.json()['times'], [30.0, 55.0, 42.0])
    
    def test_inquiries_data_api(self):
        response = self.client.get(reverse('dashboard:inquiries_data'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('labels', response.json())
        self.assertIn('data', response.json())
        self.assertEqual(response.json()['labels'][0], 'Where is OSA office located')
        self.assertEqual(response.json()['data'][0], 2)
