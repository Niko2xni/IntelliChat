import json
import re
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout
from google import genai
from .models import Student


@ensure_csrf_cookie
def chatbot_home(request):
    return render(request, 'chatbot/index.html')


def login_view(request):
    errors = {}
    email_value = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        email_value = email

        # Validate all fields are filled
        if not email:
            errors['email'] = 'Email is required.'
        if not password:
            errors['password'] = 'Password is required.'

        if not errors:
            # Authenticate against database
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                # Redirect based on role
                if user.is_staff:
                    request.session.set_expiry(0)  # Session expires when browser is closed
                    return redirect('dashboard:index')
                else:
                    return redirect('chatbot_home')
            else:
                errors['general'] = 'Invalid email or password.'

    return render(request, 'chatbot/login.html', {
        'errors': errors,
        'email_value': email_value,
    })


def signup_view(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip().lower()
        student_number = request.POST.get('studentNumber', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirmPassword', '').strip()

        # Preserve form data for re-rendering
        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'student_number': student_number,
        }

        # --- Validation ---

        # All fields required
        if not first_name:
            errors['firstName'] = 'First name is required.'
        if not last_name:
            errors['lastName'] = 'Last name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        if not student_number:
            errors['studentNumber'] = 'Student number is required.'
        if not password:
            errors['password'] = 'Password is required.'
        if not confirm_password:
            errors['confirmPassword'] = 'Please re-enter your password.'

        # Block admin email domain on signup
        if email and email.endswith('@intellichat.com'):
            errors['email'] = 'Admin accounts cannot be created here.'

        # Email must be @tip.edu.ph
        if email and 'email' not in errors and not email.endswith('@tip.edu.ph'):
            errors['email'] = 'Must be a TIP email (@tip.edu.ph).'

        # Student number must be exactly 7 digits
        if student_number and not re.match(r'^\d{7}$', student_number):
            errors['studentNumber'] = 'Student number must be exactly 7 digits.'

        # Password must be at least 8 characters
        if password and len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters.'

        # Passwords must match
        if password and confirm_password and password != confirm_password:
            errors['confirmPassword'] = 'Passwords do not match.'

        # Check if email already exists
        if email and 'email' not in errors:
            if Student.objects.filter(email=email).exists():
                errors['email'] = 'This email is already registered.'

        # Check if student number already exists
        if student_number and 'studentNumber' not in errors:
            if Student.objects.filter(student_number=student_number).exists():
                errors['studentNumber'] = 'This student number is already registered.'

        # If no errors, create the user
        if not errors:
            try:
                user = Student.objects.create_user(
                    username=email,  # Use email as username
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    student_number=student_number,
                )
                login(request, user)
                return redirect('chatbot_home')
            except Exception as e:
                errors['general'] = f'An error occurred: {str(e)}'

    return render(request, 'chatbot/signup.html', {
        'errors': errors,
        'form_data': form_data,
    })


def logout_view(request):
    logout(request)
    return redirect('home')


def profile_view(request):
    return render(request, 'chatbot/profile.html')


def ask_gemini(request):
    """Handle POST requests to send a prompt to Gemini and return the response."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

        # Initialize the client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Generate a response
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
        )

        return JsonResponse({'response': response.text})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
