from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from chatbot.models import Student
from dashboard.models import Document


class Command(BaseCommand):
    help = (
        'Clean broken media references in DB. It clears file fields when files are '
        'missing both in current storage and local media, or when local PDF files are invalid.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without updating records.',
        )
        parser.add_argument(
            '--skip-pdf-validation',
            action='store_true',
            help='Do not validate local PDF integrity before deciding cleanup.',
        )
        parser.add_argument(
            '--only-profiles',
            action='store_true',
            help='Only process Student.profile_picture references.',
        )
        parser.add_argument(
            '--only-documents',
            action='store_true',
            help='Only process Document.file references.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_pdf_validation = options['skip_pdf_validation']
        only_profiles = options['only_profiles']
        only_documents = options['only_documents']

        process_profiles = only_profiles or not (only_profiles or only_documents)
        process_documents = only_documents or not (only_profiles or only_documents)

        media_root = Path(settings.MEDIA_ROOT)
        stats = {
            'inspected': 0,
            'cleaned': 0,
            'would_clean': 0,
            'kept_local': 0,
            'skipped_storage_error': 0,
            'ok_storage': 0,
        }

        if process_profiles:
            queryset = Student.objects.filter(profile_picture__isnull=False).exclude(profile_picture='')
            self.stdout.write(f'Inspecting {queryset.count()} profile picture references...')
            for user in queryset.iterator():
                self._process_file_reference(
                    instance=user,
                    field_name='profile_picture',
                    label=f'Student#{user.id}',
                    local_media_root=media_root,
                    dry_run=dry_run,
                    skip_pdf_validation=skip_pdf_validation,
                    stats=stats,
                )

        if process_documents:
            queryset = Document.objects.filter(file__isnull=False).exclude(file='')
            self.stdout.write(f'Inspecting {queryset.count()} document file references...')
            for document in queryset.iterator():
                self._process_file_reference(
                    instance=document,
                    field_name='file',
                    label=f'Document#{document.id}',
                    local_media_root=media_root,
                    dry_run=dry_run,
                    skip_pdf_validation=skip_pdf_validation,
                    stats=stats,
                )

        mode = 'Dry-run summary' if dry_run else 'Cleanup summary'
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode}: inspected={stats["inspected"]}, '
                f'cleaned={stats["cleaned"]}, would_clean={stats["would_clean"]}, '
                f'kept_local={stats["kept_local"]}, ok_storage={stats["ok_storage"]}, '
                f'skipped_storage_error={stats["skipped_storage_error"]}'
            )
        )

    def _process_file_reference(
        self,
        instance,
        field_name,
        label,
        local_media_root,
        dry_run,
        skip_pdf_validation,
        stats,
    ):
        field_file = getattr(instance, field_name)
        if not field_file:
            return

        stats['inspected'] += 1
        file_name = field_file.name
        local_path = local_media_root / file_name

        storage_status, storage_error = self._storage_status(field_file)

        if storage_status == 'exists':
            stats['ok_storage'] += 1
            return

        should_validate_pdf = (
            not skip_pdf_validation
            and file_name.lower().endswith('.pdf')
        )

        if storage_status == 'error':
            if local_path.exists() and should_validate_pdf and not self._is_valid_pdf_local(local_path):
                self._clear_reference(
                    instance=instance,
                    field_name=field_name,
                    label=label,
                    file_name=file_name,
                    reason='local PDF is invalid',
                    dry_run=dry_run,
                    stats=stats,
                )
                return

            stats['skipped_storage_error'] += 1
            self.stdout.write(
                self.style.WARNING(
                    f'Skipped: {label} ({file_name}) -> unable to verify current storage: {storage_error}'
                )
            )
            return

        # storage_status == 'missing'
        if local_path.exists():
            if should_validate_pdf and not self._is_valid_pdf_local(local_path):
                self._clear_reference(
                    instance=instance,
                    field_name=field_name,
                    label=label,
                    file_name=file_name,
                    reason='local PDF is invalid',
                    dry_run=dry_run,
                    stats=stats,
                )
                return

            stats['kept_local'] += 1
            self.stdout.write(
                self.style.WARNING(
                    f'Kept: {label} ({file_name}) -> exists locally but not in current storage.'
                )
            )
            return

        self._clear_reference(
            instance=instance,
            field_name=field_name,
            label=label,
            file_name=file_name,
            reason='missing in current storage and local media',
            dry_run=dry_run,
            stats=stats,
        )

    def _clear_reference(self, instance, field_name, label, file_name, reason, dry_run, stats):
        if dry_run:
            stats['would_clean'] += 1
            self.stdout.write(
                self.style.WARNING(
                    f'Would clean: {label} ({file_name}) -> {reason}'
                )
            )
            return

        model_field = instance._meta.get_field(field_name)
        setattr(instance, field_name, None if model_field.null else '')
        instance.save(update_fields=[field_name])
        stats['cleaned'] += 1
        self.stdout.write(self.style.SUCCESS(f'Cleaned: {label} ({file_name}) -> {reason}'))

    @staticmethod
    def _storage_status(field_file):
        try:
            exists = field_file.storage.exists(field_file.name)
        except Exception as exc:
            return 'error', exc
        return ('exists', None) if exists else ('missing', None)

    @staticmethod
    def _is_valid_pdf_local(path):
        try:
            with path.open('rb') as stream:
                head = stream.read(8)
                stream.seek(0, 2)
                size = stream.tell()
                stream.seek(max(size - 2048, 0))
                tail = stream.read()
        except Exception:
            return False

        return head.startswith(b'%PDF-') and b'%%EOF' in tail
