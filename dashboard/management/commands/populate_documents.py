from django.core.management.base import BaseCommand
from dashboard.models import Document

class Command(BaseCommand):
    help = 'Populate the database with sample documents'

    def handle(self, *args, **options):
        # Clear existing documents
        Document.objects.all().delete()

        # Sample documents data (without file references since we just need data)
        documents_data = [
            {
                'title': 'User Guide',
                'file_type': 'PDF',
                'file_size': 245000,
                'category': 'guidelines',
                'download_count': 127,
                'view_count': 342,
                'status': 'active',
            },
            {
                'title': 'API Documentation',
                'file_type': 'DOCX',
                'file_size': 189000,
                'category': 'guidelines',
                'download_count': 94,
                'view_count': 256,
                'status': 'active',
            },
            {
                'title': 'Training Materials',
                'file_type': 'PDF',
                'file_size': 1228800,
                'category': 'guidelines',
                'download_count': 78,
                'view_count': 195,
                'status': 'active',
            },
            {
                'title': 'Pencil Booking Form',
                'file_type': 'XLSX',
                'file_size': 156000,
                'category': 'forms',
                'download_count': 145,
                'view_count': 287,
                'status': 'active',
            },
            {
                'title': 'Budget Template',
                'file_type': 'XLSX',
                'file_size': 234000,
                'category': 'templates',
                'download_count': 112,
                'view_count': 298,
                'status': 'active',
            },
            {
                'title': 'Activity Proposal Guidelines',
                'file_type': 'PDF',
                'file_size': 567000,
                'category': 'guidelines',
                'download_count': 89,
                'view_count': 201,
                'status': 'active',
            },
        ]

        for doc_data in documents_data:
            # Create a minimal file reference
            Document.objects.create(
                title=doc_data['title'],
                file_type=doc_data['file_type'],
                file_size=doc_data['file_size'],
                category=doc_data['category'],
                status=doc_data['status'],
                download_count=doc_data['download_count'],
                view_count=doc_data['view_count'],
                file=''  # Empty file reference for now - just for demo
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {len(documents_data)} sample documents')
        )