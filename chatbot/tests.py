from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
import json
from unittest.mock import patch

from .models import Student
from .views import _send_transactional_email


class LoginRedirectTests(TestCase):
    def test_chatbot_home_uses_chat_interface_for_regular_user(self):
        user = Student.objects.create_user(
            email='chat-user@example.com',
            username='chat-user@example.com',
            password='password123',
            first_name='Chat',
            last_name='User',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('chatbot_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'How can we help?')
        self.assertNotContains(response, 'Admin Dashboard')

    def test_regular_user_is_redirected_to_chatbot_home(self):
        user = Student.objects.create_user(
            email='student@example.com',
            username='student@example.com',
            password='password123',
            first_name='Regular',
            last_name='User',
        )

        response = self.client.post(
            reverse('login'),
            data={'email': user.email, 'password': 'password123'},
        )

        self.assertRedirects(response, reverse('chatbot_home'))

    def test_staff_user_without_admin_identity_is_redirected_to_chatbot_home(self):
        user = Student.objects.create_user(
            email='staff-student@example.com',
            username='staff-student@example.com',
            password='password123',
            first_name='Flagged',
            last_name='Staff',
            is_staff=True,
        )

        response = self.client.post(
            reverse('login'),
            data={'email': user.email, 'password': 'password123'},
        )

        self.assertRedirects(response, reverse('chatbot_home'))

    def test_dashboard_admin_is_redirected_to_dashboard(self):
        admin_user = Student.objects.create_user(
            email='admin@intellichat.com',
            username='admin@intellichat.com',
            password='password123',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
        )

        response = self.client.post(
            reverse('login'),
            data={'email': admin_user.email, 'password': 'password123'},
        )

        self.assertRedirects(response, reverse('dashboard:index'))


class EmailDeliveryTests(TestCase):
    @override_settings(BREVO_API_KEY='brevo-key', BREVO_SENDER_EMAIL='sender@example.com', BREVO_SENDER_NAME='IntelliChat')
    @patch('chatbot.views.urllib.request.urlopen')
    def test_send_transactional_email_uses_brevo_when_configured(self, mock_urlopen):
        response = mock_urlopen.return_value.__enter__.return_value
        response.status = 201

        _send_transactional_email('user@example.com', 'OTP Subject', 'OTP Body')

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertIn('brevo-key', str(request.header_items()))
        self.assertIn('"email": "user@example.com"', request.data.decode('utf-8'))

    @override_settings(BREVO_API_KEY='', DEFAULT_FROM_EMAIL='IntelliChat <fallback@example.com>')
    @patch('chatbot.views.send_mail')
    def test_send_transactional_email_falls_back_to_django_mail(self, mock_send_mail):
        _send_transactional_email('user@example.com', 'OTP Subject', 'OTP Body')

        mock_send_mail.assert_called_once_with(
            'OTP Subject',
            'OTP Body',
            'IntelliChat <fallback@example.com>',
            ['user@example.com'],
            fail_silently=False,
        )


class SignupValidationTests(TestCase):
    def test_send_otp_rejects_non_tip_email(self):
        response = self.client.post(
            reverse('send_otp'),
            data=json.dumps({'email': 'student@gmail.com'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'success': False, 'error': 'Must be a TIP email.'},
        )
