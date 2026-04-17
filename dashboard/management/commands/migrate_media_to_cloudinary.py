from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from chatbot.models import Student
from dashboard.models import Document


class Command(BaseCommand):
    help = (
        'Upload existing local media files (profile pictures and documents) '
        'to the configured default storage backend (Cloudinary when enabled).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without uploading files.',
        )
        parser.add_argument(
            '--skip-missing',
            action='store_true',
            help='Skip records whose local files are missing instead of failing.',
        )
        parser.add_argument(
            '--skip-upload-errors',
            action='store_true',
            help='Skip records whose upload to cloud storage fails instead of failing the command.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_missing = options['skip_missing']
        skip_upload_errors = options['skip_upload_errors'] or skip_missing

        if not getattr(settings, 'USE_CLOUDINARY_STORAGE', False):
            raise CommandError(
                'Cloudinary storage is not enabled in this process. '
                'Run this command outside test mode with valid Cloudinary credentials.'
            )

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            raise CommandError(f'MEDIA_ROOT does not exist: {media_root}')

        migrated = 0
        skipped = 0

        profile_users = Student.objects.filter(profile_picture__isnull=False).exclude(profile_picture='')
        documents = Document.objects.filter(file__isnull=False).exclude(file='')

        self.stdout.write(
            f'Preparing to migrate {profile_users.count()} profile pictures and {documents.count()} documents.'
        )

        for user in profile_users.iterator():
            did_migrate, did_skip = self._migrate_field_file(
                instance=user,
                field_name='profile_picture',
                local_media_root=media_root,
                dry_run=dry_run,
                skip_missing=skip_missing,
                skip_upload_errors=skip_upload_errors,
                label=f'Student#{user.id}',
            )
            migrated += int(did_migrate)
            skipped += int(did_skip)

        for document in documents.iterator():
            did_migrate, did_skip = self._migrate_field_file(
                instance=document,
                field_name='file',
                local_media_root=media_root,
                dry_run=dry_run,
                skip_missing=skip_missing,
                skip_upload_errors=skip_upload_errors,
                label=f'Document#{document.id}',
            )
            migrated += int(did_migrate)
            skipped += int(did_skip)

        mode = 'Dry-run complete' if dry_run else 'Migration complete'
        self.stdout.write(self.style.SUCCESS(f'{mode}. Migrated: {migrated}, Skipped: {skipped}.'))

    def _migrate_field_file(
        self,
        instance,
        field_name,
        local_media_root,
        dry_run,
        skip_missing,
        skip_upload_errors,
        label,
    ):
        field_file = getattr(instance, field_name)
        if not field_file:
            return False, False

        local_path = local_media_root / field_file.name
        if not local_path.exists():
            message = f'Missing local file for {label}: {local_path}'
            if skip_missing:
                self.stdout.write(self.style.WARNING(f'Skipped: {message}'))
                return False, True
            raise CommandError(message)

        if dry_run:
            self.stdout.write(f'Would migrate {label} -> {field_file.name}')
            return False, False

        try:
            with local_path.open('rb') as local_stream:
                upload_file = File(local_stream, name=field_file.name)
                getattr(instance, field_name).save(field_file.name, upload_file, save=False)
        except Exception as exc:
            message = f'Upload failed for {label} ({field_file.name}): {exc}'
            if skip_upload_errors:
                self.stdout.write(self.style.WARNING(f'Skipped: {message}'))
                return False, True
            raise CommandError(message) from exc

        instance.save(update_fields=[field_name])

        self.stdout.write(f'Migrated {label} -> {getattr(instance, field_name).name}')
        return True, False
