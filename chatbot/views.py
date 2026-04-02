import json
import re
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from google import genai
from .models import Student
from django.core.mail import send_mail
import time
import secrets

@ensure_csrf_cookie
def chatbot_home(request):
    return render(request, 'chatbot/index.html')


def login_view(request):
    errors = {}
    email_value = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
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
        if not request.session.get('otp_verified'):
            errors['general'] = "Please verify your email via OTP first."
            return render(request, 'chatbot/signup.html', {'errors': errors})

        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip().lower()
        student_number = request.POST.get('studentNumber', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirmPassword', '').strip()

        form_data = {
            'first_name': first_name, 'last_name': last_name,
            'email': email, 'student_number': student_number,
        }

        if not all([first_name, last_name, email, student_number, password]):
            errors['general'] = "All fields are required."
        
        if email != request.session.get('otp_email_target'):
            errors['email'] = "Email mismatch. Please verify the OTP for this email."

        if Student.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered.'
        
        if Student.objects.filter(student_number=student_number).exists():
            errors['studentNumber'] = 'This student number is already registered.'

        if password != confirm_password:
            errors['confirmPassword'] = 'Passwords do not match.'

        if not errors:
            try:
                user = Student.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    student_number=student_number,
                )
                login(request, user)
                
                request.session.pop('email_otp', None)
                request.session.pop('otp_email_target', None)
                request.session.pop('otp_verified', None)
                request.session.pop('otp_timestamp', None)
                request.session.modified = True
                
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

def verify_otp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_otp = data.get('otp')
            session_otp = request.session.get('email_otp')
            otp_timestamp = request.session.get('otp_timestamp', 0)
            
            if time.time() - otp_timestamp > 600:  # 10 minutes validation
                return JsonResponse({'valid': False, 'error': 'OTP has expired. Please request a new one.'})
            
            if session_otp and str(user_otp) == str(session_otp):
                request.session['otp_verified'] = True
                return JsonResponse({'valid': True})
            request.session['otp_verified'] = False
            return JsonResponse({'valid': False, 'error': 'Invalid verification code.'})
        except Exception:
            return JsonResponse({'valid': False, 'error': 'Invalid request.'}, status=400)

def send_otp(request):
    """Generates and sends an OTP to the provided email."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            student_number = data.get('studentNumber', '').strip()

            if not email.endswith('@tip.edu.ph'):
                return JsonResponse({'success': False, 'error': 'Must be a TIP email.'})
                
            if Student.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'This email is already registered.'})
                
            if student_number and Student.objects.filter(student_number=student_number).exists():
                return JsonResponse({'success': False, 'error': 'This student number is already registered.'})

            otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
            
            request.session['email_otp'] = otp
            request.session['otp_email_target'] = email
            request.session['otp_timestamp'] = time.time()
            request.session['otp_verified'] = False
            
            subject = "Your IntelliChat Verification Code"
            message = f"Hello! Your verification code is: {otp}\n\nThis code will expire in 10 minutes."
            from_email = settings.DEFAULT_FROM_EMAIL
            
            send_mail(subject, message, from_email, [email], fail_silently=False)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False}, status=400)

def send_password_change_otp(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
            
        try:
            data = json.loads(request.body)
            password = data.get('password', '').strip()
            
            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'error': 'Incorrect password.'})
                
            email = request.user.email
            if not email:
                return JsonResponse({'success': False, 'error': 'User has no email associated.'})

            otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
            
            request.session['password_change_otp'] = otp
            request.session['password_change_otp_timestamp'] = time.time()
            request.session['password_change_otp_verified'] = False
            
            subject = "Your Password Change Verification Code"
            message = f"Hello! Your verification code to change your password is: {otp}\n\nThis code will expire in 10 minutes. If you did not request a password change, please ignore this email."
            from_email = settings.DEFAULT_FROM_EMAIL
            
            send_mail(subject, message, from_email, [email], fail_silently=False)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)

def verify_password_change_otp(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'valid': False, 'error': 'Unauthorized'}, status=401)
            
        try:
            data = json.loads(request.body)
            user_otp = data.get('otp')
            session_otp = request.session.get('password_change_otp')
            otp_timestamp = request.session.get('password_change_otp_timestamp', 0)
            
            if time.time() - otp_timestamp > 600:  # 10 minutes validation
                return JsonResponse({'valid': False, 'error': 'OTP has expired. Please request a new one.'})
            
            if session_otp and str(user_otp) == str(session_otp):
                request.session['password_change_otp_verified'] = True
                return JsonResponse({'valid': True})
                
            request.session['password_change_otp_verified'] = False
            return JsonResponse({'valid': False, 'error': 'Invalid verification code.'})
        except Exception:
            return JsonResponse({'valid': False, 'error': 'Invalid request.'}, status=400)
    return JsonResponse({'valid': False, 'error': 'Invalid request.'}, status=400)

def update_password(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
            
        if not request.session.get('password_change_otp_verified', False):
            return JsonResponse({'success': False, 'error': 'Please verify your email via OTP first.'})
            
        try:
            data = json.loads(request.body)
            password = data.get('password', '').strip()
            confirm_password = data.get('confirmPassword', '').strip()
            
            if not password or len(password) < 8:
                return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long.'})
                
            if password != confirm_password:
                return JsonResponse({'success': False, 'error': 'Passwords do not match.'})
                
            # Update the user's password
            request.user.set_password(password)
            request.user.save()
            
            # Keep the user logged in
            update_session_auth_hash(request, request.user)
            
            # Clear the OTP session variables
            request.session.pop('password_change_otp', None)
            request.session.pop('password_change_otp_timestamp', None)
            request.session.pop('password_change_otp_verified', None)
            request.session.modified = True
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)

def init_delete_account(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
            
        try:
            data = json.loads(request.body)
            password = data.get('password', '').strip()
            
            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'error': 'Incorrect password.'})
                
            email = request.user.email
            if not email:
                return JsonResponse({'success': False, 'error': 'User has no email associated.'})

            otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
            
            request.session['delete_account_otp'] = otp
            request.session['delete_account_otp_timestamp'] = time.time()
            
            subject = "Account Deletion Verification Code"
            message = f"Hello! Your verification code to irrevocably delete your account is: {otp}\n\nThis code will expire in 10 minutes. If you did not request this, please change your password immediately."
            from_email = settings.DEFAULT_FROM_EMAIL
            
            send_mail(subject, message, from_email, [email], fail_silently=False)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)

def confirm_delete_account(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
            
        try:
            data = json.loads(request.body)
            user_otp = data.get('otp')
            session_otp = request.session.get('delete_account_otp')
            otp_timestamp = request.session.get('delete_account_otp_timestamp', 0)
            
            if time.time() - otp_timestamp > 600:
                return JsonResponse({'success': False, 'error': 'OTP has expired. Please start over.'})
            
            if session_otp and str(user_otp) == str(session_otp):
                user = request.user
                logout(request)
                user.delete()
                # Clear session keys manually just in case, though logout handles it
                if 'delete_account_otp' in request.session:
                    del request.session['delete_account_otp']
                if 'delete_account_otp_timestamp' in request.session:
                    del request.session['delete_account_otp_timestamp']
                return JsonResponse({'success': True})
                
            return JsonResponse({'success': False, 'error': 'Invalid verification code.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)