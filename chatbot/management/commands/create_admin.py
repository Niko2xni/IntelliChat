from django.core.management.base import BaseCommand
from chatbot.models import Student
import getpass


class Command(BaseCommand):
    help = 'Create an admin account with an @intellichat.com email'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email (must end with @intellichat.com)')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--student-number', type=str, help='Admin ID (7 digits, e.g. 0000001)')
        parser.add_argument('--password', type=str, help='Password (will prompt if not provided)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n=== IntelliChat Admin Account Creator ===\n'))

        # Gather info (use flags or prompt interactively)
        email = options['email'] or input('Admin email (@intellichat.com): ').strip()
        first_name = options['first_name'] or input('First name: ').strip()
        last_name = options['last_name'] or input('Last name: ').strip()
        student_number = options['student_number'] or input('Admin ID (7 digits): ').strip()
        password = options['password'] or getpass.getpass('Password (min 8 chars): ')

        # --- Validation ---
        errors = []

        if not email.endswith('@intellichat.com'):
            errors.append('Admin email must end with @intellichat.com')

        if not first_name:
            errors.append('First name is required.')

        if not last_name:
            errors.append('Last name is required.')

        import re
        if not re.match(r'^\d{7}$', student_number):
            errors.append('Admin ID must be exactly 7 digits.')

        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')

        if Student.objects.filter(email=email).exists():
            errors.append(f'An account with email "{email}" already exists.')

        if Student.objects.filter(student_number=student_number).exists():
            errors.append(f'An account with ID "{student_number}" already exists.')

        if errors:
            for err in errors:
                self.stdout.write(self.style.ERROR(f'  ✗ {err}'))
            self.stdout.write(self.style.ERROR('\nAdmin account was NOT created.\n'))
            return

        # --- Create the admin ---
        admin = Student.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            student_number=student_number,
            is_staff=True,
            is_superuser=True,
        )

        self.stdout.write(self.style.SUCCESS(f'\n  ✓ Admin account created successfully!'))
        self.stdout.write(f'    Name:   {first_name} {last_name}')
        self.stdout.write(f'    Email:  {email}')
        self.stdout.write(f'    ID:     {student_number}')
        self.stdout.write(f'    Staff:  Yes')
        self.stdout.write(f'    Super:  Yes\n')
