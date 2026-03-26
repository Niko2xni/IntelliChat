from django.core.management.base import BaseCommand
from dashboard.models import FAQ

class Command(BaseCommand):
    help = 'Populate the database with sample FAQs'

    def handle(self, *args, **options):
        # Clear existing FAQs
        FAQ.objects.all().delete()

        # Sample FAQs
        faqs_data = [
            {
                'question': 'How do I reset my password?',
                'answer': 'To reset your password, click on the "Forgot Password" link on the login page. Enter your email address and follow the instructions sent to your email. Make sure to check your spam folder if you don\'t see the email.',
                'tags': 'login, password, reset, account',
                'category': 'account'
            },
            {
                'question': 'What are the system requirements for IntelliChat?',
                'answer': 'IntelliChat works on most modern devices. Minimum requirements: Windows 10+, macOS 10.15+, or Linux Ubuntu 18.04+. You need a modern web browser (Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+). Internet connection is required for cloud features.',
                'tags': 'system, requirements, compatibility, browser',
                'category': 'technical'
            },
            {
                'question': 'How do I upgrade my subscription plan?',
                'answer': 'You can upgrade your subscription from your account settings. Go to Settings > Billing > Change Plan. Select your desired plan and complete the payment. The upgrade takes effect immediately, and you\'ll be prorated for the remaining billing period.',
                'tags': 'subscription, upgrade, billing, payment',
                'category': 'billing'
            },
            {
                'question': 'Can I export my chat history?',
                'answer': 'Yes, you can export your chat history in multiple formats. Go to Settings > Data Export > Chat History. Choose your preferred format (PDF, CSV, or JSON) and date range. The export will be emailed to you within a few minutes.',
                'tags': 'export, chat, history, data',
                'category': 'features'
            },
            {
                'question': 'How do I integrate IntelliChat with my existing systems?',
                'answer': 'IntelliChat offers REST APIs and webhooks for integration. Visit our Developer Portal at docs.intellichat.com for API documentation. We support integrations with Slack, Microsoft Teams, Zendesk, and many other platforms.',
                'tags': 'integration, api, webhook, developer',
                'category': 'technical'
            },
            {
                'question': 'What payment methods do you accept?',
                'answer': 'We accept all major credit cards (Visa, MasterCard, American Express), PayPal, and bank transfers for annual plans. All payments are processed securely through Stripe. You can update your payment method anytime in your billing settings.',
                'tags': 'payment, credit card, paypal, billing',
                'category': 'billing'
            },
            {
                'question': 'How do I create a new chatbot?',
                'answer': 'Click the "New Chatbot" button in your dashboard. Choose a template or start from scratch. Configure your chatbot\'s personality, knowledge base, and conversation flows. Test it thoroughly before publishing.',
                'tags': 'chatbot, create, setup, configuration',
                'category': 'features'
            },
            {
                'question': 'Is my data secure?',
                'answer': 'Yes, security is our top priority. All data is encrypted in transit and at rest. We use enterprise-grade security measures including SOC 2 compliance, regular security audits, and GDPR compliance. Your data is never shared with third parties.',
                'tags': 'security, privacy, encryption, compliance',
                'category': 'general'
            }
        ]

        for faq_data in faqs_data:
            FAQ.objects.create(**faq_data)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {len(faqs_data)} sample FAQs')
        )