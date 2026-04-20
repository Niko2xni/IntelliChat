from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json
from unittest.mock import patch

from dashboard.models import Document

from .models import ChatMessage, ChatSession, Student
from .views import DOCUMENT_ACCESS_RESTRICTION_MESSAGE, _send_transactional_email


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


class DocumentAccessControlTests(TestCase):
    def setUp(self):
        self.general_user = Student.objects.create_user(
            email='general-user@tip.edu.ph',
            username='general-user@tip.edu.ph',
            password='password123',
            first_name='General',
            last_name='User',
        )
        self.student_leader = Student.objects.create_user(
            email='student-leader@tip.edu.ph',
            username='student-leader@tip.edu.ph',
            password='password123',
            first_name='Student',
            last_name='Leader',
            account_type=Student.ACCOUNT_STUDENT_LEADER,
        )
        self.document = Document.objects.create(
            title='Student Leader Manual',
            description='Manual for student leaders',
            file=SimpleUploadedFile(
                'student-leader-manual.pdf',
                b'%PDF-1.4\nstudent leader manual\n%%EOF',
                content_type='application/pdf',
            ),
            file_type='PDF',
            file_size=len(b'%PDF-1.4\nstudent leader manual\n%%EOF'),
            category='guidelines',
            status='active',
        )

    def test_download_chat_document_denies_anonymous_and_general_users(self):
        download_url = reverse('chatbot_download_document', args=[self.document.id])

        anonymous_response = self.client.get(download_url)
        self.assertEqual(anonymous_response.status_code, 404)

        self.client.force_login(self.general_user)
        general_response = self.client.get(download_url)
        self.assertEqual(general_response.status_code, 404)

    def test_download_chat_document_allows_student_leader(self):
        self.client.force_login(self.student_leader)

        response = self.client.get(reverse('chatbot_download_document', args=[self.document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment;', response.get('Content-Disposition', ''))

    def test_ask_gemini_returns_access_message_for_non_leader_document_request(self):
        self.client.force_login(self.general_user)

        with patch('chatbot.views.genai.Client') as mock_genai:
            response = self.client.post(
                reverse('ask_gemini'),
                data=json.dumps({'message': 'Can you share the student leader manual document?'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['response'], DOCUMENT_ACCESS_RESTRICTION_MESSAGE)
        self.assertEqual(payload['documents'], [])
        mock_genai.assert_not_called()

    def test_ask_gemini_returns_documents_for_student_leader(self):
        self.client.force_login(self.student_leader)

        with patch('chatbot.views.genai.Client') as mock_genai:
            mock_genai.return_value.models.generate_content.return_value.text = 'Here is the manual.'
            response = self.client.post(
                reverse('ask_gemini'),
                data=json.dumps({'message': 'Can you share the student leader manual document?'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['response'], 'Here is the manual.')
        self.assertGreaterEqual(len(payload['documents']), 1)
        self.assertEqual(
            payload['documents'][0]['url'],
            reverse('chatbot_download_document', args=[self.document.id]),
        )

    def test_non_leader_session_render_hides_existing_document_attachments(self):
        session = ChatSession.objects.create(user=self.general_user, title='Need a file')
        ChatMessage.objects.create(session=session, role=ChatMessage.USER, content='Need a file')
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ASSISTANT,
            content='Here is a file.',
            attachments=[
                {
                    'id': self.document.id,
                    'title': self.document.title,
                    'file_type': self.document.file_type,
                    'file_size_display': '1.0 KB',
                    'url': reverse('chatbot_download_document', args=[self.document.id]),
                }
            ],
        )

        self.client.force_login(self.general_user)
        response = self.client.get(reverse('chat_session', args=[session.id]))

        self.assertEqual(response.status_code, 200)
        assistant_messages = [
            message for message in response.context['current_messages']
            if message['role'] == ChatMessage.ASSISTANT
        ]
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]['attachments'], [])
