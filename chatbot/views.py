import json
import re
import secrets
import time
from hashlib import sha256

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from google import genai

from .models import ChatMessage, ChatSession, Student
from dashboard.models import RoleRequest, create_audit_log

SYSTEM_PROMPT = """
You are the T.I.P. Office of Student Affairs (OSA) Virtual Assistant.
Your goal is to provide accurate, helpful, and polite information to students and faculty
of the Technological Institute of the Philippines.

CONTEXT & RULES:
- Use the provided T.I.P. Information to answer queries about history, policies, and locations.
- If a student asks about a location, specify if it's in T.I.P. Manila (Casal or Arlegui) or Quezon City.
- For academic rules (absences, refunds, grades), be precise. (e.g., 20% absence rule, 90% refund in 1st week).
- If a question is NOT covered by the provided data, politely advise the student to visit the
  Office of Student Affairs (OSA) at the Founders' Hall (Manila) or the relevant office in QC.
- Maintain a professional yet welcoming tone ("T.I.P.ian" spirit).
- Use Markdown for clarity (bullet points for lists).

SCOPE OF KNOWLEDGE:
- You ONLY answer questions related to the Technological Institute of the Philippines (T.I.P.), its policies, history, locations, and student services.
- Your knowledge base is strictly limited to the information provided below.

STRICT OUT-OF-SCOPE RULES:
1. If a user asks a question that is NOT related to T.I.P. (e.g., general world news, sports, math problems unrelated to T.I.P. tutorials, or creative writing), you must politely decline.
2. Respond with: "I'm sorry, I am only programmed to assist with T.I.P. Office of Student Affairs related inquiries. Please visit the OSA office for other concerns."
3. Do not engage in casual conversation or "roleplay" outside of your professional persona.
4. Only write in Paragraphs.

T.I.P. KNOWLEDGE BASE:
I. About the Technological Institute of the Philippines (T.I.P.)
Founding: Established on February 8, 1962, as a private non-sectarian stock school in Manila.
Founders: A group of educators led by Engineer Demetrio A. Quirino, Jr. and Dr. Teresita U. Quirino.
Vision & Mission: Founded to maintain high instructional standards, bring higher education within reach of the masses, and cooperate with government economic and social programs.
Campuses:
T.I.P. Manila: Originally at the Lorenzana Building in Quiapo; now a 2.3-hectare site with four main buildings.
T.I.P. Quezon City: Established in 1983 to decongest the Manila University Belt; now a 3.3-hectare site with ten main buildings.
Autonomous Status: Both campuses hold Autonomous Status from CHED, the highest award for higher education institutions in the Philippines.
Certification: The school's Quality Management System has been ISO 9001 certified since 1999.
II. Key People Mentioned
Angelo Quirino Lahoz: President of T.I.P. 2025.
Engr. Demetrio A. Quirino, Jr.: Co-founder.
Dr. Teresita U. Quirino: Co-founder.
Prudencio "Dero" Pedero: Composer of the T.I.P. Fight Song ("We're on Top of the World").
III. Campus Geography & Crucial Locations
T.I.P. Manila Campus
Casal Campus: Founders' Hall (F Building): A central hub housing the Registrar, Student Recruitment Office, Accountancy, Cashiering, and the Office of Student Affairs (OSA) on the 1st Floor. The Library is located on the 5th Floor.
P. Casal (PC) Buildings: Includes PC-5, PC-12 (formerly SHS), and Building 2.
PE Center: Located within the Casal Campus area.
Arlegui Campus:
Arlegui Building: Features the Office of Student Affairs (OSA) and Guidance & Counseling (2nd Floor), the Career Center (3rd Floor), a second Library (5th Floor), and the Anniversary Hall (6th Floor).
T.I.P. Quezon City Campus
TechnoCoRe Building: A landmark facility housing state-of-the-art engineering and fabrication workshops for research and technopreneurship.
General Campus: Comprises ten main buildings equipped with modern IT labs and smart classrooms.

IV. Detailed Student Policies
General Directives & Norms of Conduct
Agreement to Rules: Enrollment constitutes a voluntary agreement to abide by all school regulations.
Conduct Expectations: Students must uphold school order, preserve the institution's good name, and actualize its mission.
Official Channels: Students are responsible for checking the Canvas LMS, T.I.P. website, and official social media for notices.
Identification: Official ID cards must be worn at all times while on campus.
Admission and Registration
Official Status: A student is only officially enrolled after submitting all credentials and paying fees.
Prerequisites: Courses taken without passing the required prerequisites will not be credited.
Transferees: Must complete a residency requirement of at least one school year and 42 units at T.I.P.
Tuition and Other Fees
Refund Eligibility: Only possible within the first two weeks of a regular semester or the first four days of summer.
Refund Rates: 90% refund in the 1st week; 80% refund in the 2nd week; no refund thereafter.
Attendance
Tardiness: Arriving 15 to 45 minutes late (depending on class length) counts as tardy; three tardies equal one absence.
20% Absence Rule: Students exceeding absences of 20% of school days receive no credit.
Mark of 6.00: Exceeded limit with written notification to the instructor.
Mark of 7.00: Exceeded limit without written notification.
Academic Changes (Shifting and Overload)
Program Shifting: Allowed only once and requires completion of one year or 42 units; shifting back to a former program is prohibited.
Study Overload: Reserved for graduating students with approval from the Program Chair.
Examinations and Grading
Special Exams: Must be applied for within five school days from the last scheduled exam date.
Grading System: Uses a cumulative system (1.00 Excellent to 5.00 Failed).
Incomplete (4.00): Must be removed within one year or it becomes a 5.00.
Latin Honors: Requires earning at least 75% of program courses at T.I.P. and maintaining specific GPA standards.
Conduct and Discipline
Major Offenses: Include computer hacking, drug/alcohol possession, fighting, hazing, and unauthorized fund-raising.
Fraternities: Recruitment of first-year students is strictly prohibited.
Sanctions: Can include suspension, non-readmission, exclusion, or expulsion.
Hearing Committee: Major cases are investigated by a committee including an officer from a different department, faculty, staff, and student observers.
Student Services
ARIS Portal: Web-based tool for tracking academic status, grades, and account balances.
Tutorial Services: Offers free Online Study Group Tutorials (OSGT) in Math and English via Canvas.
Medical/Dental: Clinic provides basic first aid, consultations, and Annual Oral Prophylaxis (dental cleaning).
Math Enhancement Program (MEP): A free summer tutorial for incoming freshmen to prepare for college-level math.
"""


def _chat_sessions_for_user(user):
    if not user.is_authenticated:
        return []
    return ChatSession.objects.filter(user=user).prefetch_related('messages')


def _serialize_messages(messages):
    return [
        {
            'role': message.role,
            'content': message.content,
        }
        for message in messages
    ]


def _session_title_from_message(message):
    compact = re.sub(r'\s+', ' ', message).strip()
    if len(compact) <= 60:
        return compact
    return f"{compact[:57].rstrip()}..."


def _request_identifier(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"

    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"

    return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


def _is_rate_limited(request):
    limit = getattr(settings, 'CHAT_RATE_LIMIT', 20)
    window = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW', 60)
    cache_key = f"chat-rate-limit:{_request_identifier(request)}"

    if cache.add(cache_key, 1, timeout=window):
        return False

    current_count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, current_count, timeout=window)
    return current_count > limit


def _response_cache_key(user_message, history):
    payload = json.dumps(
        {
            'message': user_message,
            'history': history,
        },
        sort_keys=True,
    )
    return f"chat-response:{sha256(payload.encode('utf-8')).hexdigest()}"


@ensure_csrf_cookie
def chatbot_home(request, session_id=None):
    chat_sessions = _chat_sessions_for_user(request.user)
    current_session = None
    current_messages = []

    if session_id is not None and request.user.is_authenticated:
        current_session = ChatSession.objects.filter(
            id=session_id,
            user=request.user,
        ).prefetch_related('messages').first()
        if current_session is None:
            return redirect('chatbot_home')
        current_messages = _serialize_messages(current_session.messages.all())

    return render(request, 'chatbot/index.html', {
        'chat_sessions': chat_sessions,
        'current_session': current_session,
        'current_messages': current_messages,
    })


def login_view(request):
    errors = {}
    email_value = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        email_value = email

        if not email:
            errors['email'] = 'Email is required.'
        if not password:
            errors['password'] = 'Password is required.'

        if not errors:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                if user.is_staff:
                    request.session.set_expiry(0)
                    return redirect('dashboard:index')
                return redirect('chatbot_home')
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
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirmPassword', '').strip()

        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
        }

        if not all([first_name, last_name, email, password]):
            errors['general'] = "All fields are required."

        if email != request.session.get('otp_email_target'):
            errors['email'] = "Email mismatch. Please verify the OTP for this email."

        if Student.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered.'

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
    return render(request, 'chatbot/profile.html', {
        'chat_sessions': _chat_sessions_for_user(request.user),
    })


def request_form_view(request):
    return render(request, 'chatbot/request_form.html', {
        'chat_sessions': _chat_sessions_for_user(request.user),
    })


def submit_role_request(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST requests are allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
        student_number = data.get('student_number', '').strip()
        position = data.get('position', '').strip()
        organization = data.get('organization', '').strip()

        if not all([student_number, position, organization]):
            return JsonResponse({'success': False, 'error': 'All fields are required.'}, status=400)

        role_request = RoleRequest.objects.create(
            user=request.user,
            student_number=student_number,
            position=position,
            organization=organization,
        )
        create_audit_log(
            'Submitted Student Leader request',
            request.user.email,
            f'Submitted role request for {organization} as {position}.',
        )

        return JsonResponse({'success': True, 'request_id': role_request.id})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def ask_gemini(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    if _is_rate_limited(request):
        return JsonResponse(
            {'error': 'Too many chat requests. Please wait a minute and try again.'},
            status=429,
        )

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')

        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

        chat_session = None
        history = []

        if request.user.is_authenticated and session_id:
            chat_session = ChatSession.objects.filter(
                id=session_id,
                user=request.user,
            ).prefetch_related('messages').first()

            if chat_session is None:
                return JsonResponse({'error': 'Chat session not found.'}, status=404)

            history = [
                f"{'User' if message.role == ChatMessage.USER else 'Assistant'}: {message.content}"
                for message in chat_session.messages.all()
            ]

        prompt = user_message
        if history:
            prompt = "Conversation so far:\n" + "\n".join(history) + f"\nUser: {user_message}\nAssistant:"

        response_cache_key = _response_cache_key(user_message, history)
        assistant_reply = cache.get(response_cache_key)

        if assistant_reply is None:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config={'system_instruction': SYSTEM_PROMPT}
            )
            assistant_reply = response.text
            cache.set(
                response_cache_key,
                assistant_reply,
                timeout=getattr(settings, 'CHAT_RESPONSE_CACHE_TTL', 300),
            )

        if request.user.is_authenticated:
            if chat_session is None:
                chat_session = ChatSession.objects.create(
                    user=request.user,
                    title=_session_title_from_message(user_message),
                )

            ChatMessage.objects.create(
                session=chat_session,
                role=ChatMessage.USER,
                content=user_message,
            )
            ChatMessage.objects.create(
                session=chat_session,
                role=ChatMessage.ASSISTANT,
                content=assistant_reply,
            )

        return JsonResponse({
            'response': assistant_reply,
            'session_id': chat_session.id if chat_session else None,
            'session_title': chat_session.title if chat_session else None,
            'session_url': reverse('chat_session', args=[chat_session.id]) if chat_session else None,
        })

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

            if time.time() - otp_timestamp > 600:
                return JsonResponse({'valid': False, 'error': 'OTP has expired. Please request a new one.'})

            if session_otp and str(user_otp) == str(session_otp):
                request.session['otp_verified'] = True
                return JsonResponse({'valid': True})
            request.session['otp_verified'] = False
            return JsonResponse({'valid': False, 'error': 'Invalid verification code.'})
        except Exception:
            return JsonResponse({'valid': False, 'error': 'Invalid request.'}, status=400)


def send_otp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            if not (email.endswith('@tip.edu.ph') or email.endswith('@gmail.com')):
                return JsonResponse({'success': False, 'error': 'Must be a TIP or Gmail email.'})

            if Student.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'This email is already registered.'})

            otp = "".join(str(secrets.randbelow(10)) for _ in range(6))

            request.session['email_otp'] = otp
            request.session['otp_email_target'] = email
            request.session['otp_timestamp'] = time.time()
            request.session['otp_verified'] = False

            subject = "Your IntelliChat Verification Code"
            message = f"Hello! Your verification code is: {otp}\n\nThis code will expire in 10 minutes."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

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
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

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

            if time.time() - otp_timestamp > 600:
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

            request.user.set_password(password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            create_audit_log(
                'Changed Password',
                request.user.email,
                'User changed their password through profile settings.',
            )

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
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

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
                email = user.email
                logout(request)
                user.delete()
                create_audit_log(
                    'Deleted Account',
                    email,
                    'User deleted their account through profile settings.',
                )
                request.session.pop('delete_account_otp', None)
                request.session.pop('delete_account_otp_timestamp', None)
                return JsonResponse({'success': True})

            return JsonResponse({'success': False, 'error': 'Invalid verification code.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)


def upload_profile_picture(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        profile_picture = request.FILES.get('profile_picture')
        if not profile_picture:
            return JsonResponse({'success': False, 'error': 'No image file provided.'})

        if profile_picture.size > 4 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'File size exceeds 4MB limit.'})

        if not profile_picture.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'File must be an image.'})

        try:
            if request.user.profile_picture:
                request.user.profile_picture.delete(save=False)

            request.user.profile_picture = profile_picture
            request.user.save()
            create_audit_log(
                'Updated Profile Picture',
                request.user.email,
                'User uploaded a new profile picture.',
            )

            return JsonResponse({
                'success': True,
                'image_url': request.user.profile_picture.url
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)


def init_change_email(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        try:
            data = json.loads(request.body)
            password = data.get('password', '').strip()
            new_email = data.get('new_email', '').strip()

            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'error': 'Incorrect password.'})

            if not (new_email.endswith('@tip.edu.ph') or new_email.endswith('@gmail.com')):
                return JsonResponse({'success': False, 'error': 'Must be a TIP or Gmail email.'})

            if Student.objects.filter(email=new_email).exists():
                return JsonResponse({'success': False, 'error': 'This email is already in use.'})

            otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
            request.session['email_change_otp'] = otp
            request.session['email_change_otp_timestamp'] = time.time()
            request.session['email_change_new'] = new_email

            subject = "Your Email Change Verification Code"
            message = f"Your verification code to change your email is: {otp}\n\nThis code will expire in 10 minutes."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_email], fail_silently=False)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)


def confirm_change_email(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        try:
            data = json.loads(request.body)
            otp_entered = data.get('otp', '').strip()

            stored_otp = request.session.get('email_change_otp')
            timestamp = request.session.get('email_change_otp_timestamp')
            new_email = request.session.get('email_change_new')

            if not stored_otp or not timestamp or not new_email:
                return JsonResponse({'success': False, 'error': 'No active verification session.'})

            if time.time() - timestamp > 600:
                return JsonResponse({'success': False, 'error': 'Verification code expired.'})

            if stored_otp == otp_entered:
                old_email = request.user.email
                request.user.email = new_email
                request.user.save()
                create_audit_log(
                    'Changed Email',
                    old_email,
                    f'User changed email from {old_email} to {new_email}.',
                )

                del request.session['email_change_otp']
                del request.session['email_change_otp_timestamp']
                del request.session['email_change_new']

                return JsonResponse({'success': True})

            return JsonResponse({'success': False, 'error': 'Invalid verification code.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
