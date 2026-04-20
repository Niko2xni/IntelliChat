import json
import re
import secrets
import time
import urllib.error
import urllib.request
from hashlib import sha256

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import models
from django.http import FileResponse, Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from google import genai

from .models import ChatMessage, ChatSession, Student
from dashboard.models import Document, FAQ, Notification, RoleRequest, create_notification

SYSTEM_PROMPT = """
You are the T.I.P. Office of Student Affairs (OSA) Virtual Assistant.
Your goal is to provide accurate, helpful, and polite information to students and faculty
of the Technological Institute of the Philippines.

CONTEXT & RULES:
- Use the provided T.I.P. Information to answer queries about history, policies, and locations.
- Use any provided admin-uploaded document list or document context as an approved knowledge source.
- If a student asks about a location, specify if it's in T.I.P. Manila (Casal Campus or Arlegui Campus)
- For academic rules (absences, refunds, grades), be precise. (e.g., 20% absence rule, 90% refund in 1st week).
- If a question is NOT covered by the provided data, politely advise the student to visit the
  Office of Student Affairs (OSA) at the Founders' Hall (Manila) or the relevant office in QC.
- Maintain a professional yet welcoming tone ("T.I.P.ian" spirit).
- Use Markdown for clarity (bullet points for lists).

SCOPE OF KNOWLEDGE:
- You ONLY answer questions related to the Technological Institute of the Philippines (T.I.P.), its policies, history, locations, and student services.
- Your knowledge base includes the information provided below and any active admin-uploaded documents explicitly provided in the current prompt.

STRICT OUT-OF-SCOPE RULES:
1. If a user asks a question that is NOT related to T.I.P. (e.g., general world news, sports, math problems unrelated to T.I.P. tutorials, or creative writing), you must politely decline.
2. Respond with: "I'm sorry, I am only programmed to assist with T.I.P. Office of Student Affairs related inquiries. Please visit the OSA office for other concerns."
3. Do not engage in casual conversation or "roleplay" outside of your professional persona.
4. Only write in Paragraphs.
5. Questions asking whether a T.I.P. document, form, guideline, or manual is available are in-scope. If matching admin documents are provided, say they are available and mention the attached document names naturally in your answer.

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

MAX_CHAT_MESSAGE_LENGTH = getattr(settings, 'CHAT_MESSAGE_MAX_LENGTH', 500)
CHAT_DOCUMENT_RESULT_LIMIT = getattr(settings, 'CHAT_DOCUMENT_RESULT_LIMIT', 3)
DOCUMENT_INTENT_PATTERN = re.compile(
    r"\b(document|documents|form|forms|template|templates|guideline|guidelines|manual|handbook|file|files|pdf|docx|jpg|jpeg|png|download|copy|copies|softcopy|attachment|attachments)\b",
    re.IGNORECASE,
)
DOCUMENT_KEYWORD_STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'need', 'send', 'show', 'give',
    'copy', 'copies', 'please', 'share', 'provide', 'download', 'file', 'files', 'document',
    'documents', 'attachment', 'attachments',
}
DOCUMENT_ACCESS_RESTRICTION_MESSAGE = (
    'Document downloads are available only for Student Leader accounts. '
    'Please submit a Student Leader role request from your profile and wait for admin approval.'
)


def _send_transactional_email(recipient_email, subject, message):
    if settings.BREVO_API_KEY:
        payload = {
            'sender': {
                'name': settings.BREVO_SENDER_NAME,
                'email': settings.BREVO_SENDER_EMAIL,
            },
            'to': [{'email': recipient_email}],
            'subject': subject,
            'textContent': message,
        }
        request = urllib.request.Request(
            'https://api.brevo.com/v3/smtp/email',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'accept': 'application/json',
                'api-key': settings.BREVO_API_KEY,
                'content-type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status >= 400:
                    raise RuntimeError('Brevo email request failed.')
            return
        except urllib.error.HTTPError as exc:
            details = exc.read().decode('utf-8', errors='ignore').strip()
            raise RuntimeError(details or f'Brevo email request failed with status {exc.code}.') from exc
        except urllib.error.URLError as exc:
            raise RuntimeError('Unable to reach Brevo email service.') from exc

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient_email], fail_silently=False)


def _chat_sessions_for_user(user):
    if not user.is_authenticated:
        return []
    return ChatSession.objects.filter(user=user).prefetch_related('messages')


def _compact_text(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def _truncate_for_history(value, max_length):
    compact = _compact_text(value)
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length - 3].rstrip()}..."


def _can_access_documents(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return getattr(user, 'account_type', '') == Student.ACCOUNT_STUDENT_LEADER


def _serialize_messages(messages, include_attachments=True):
    return [
        {
            'role': message.role,
            'content': message.content,
            'attachments': (message.attachments or []) if include_attachments else [],
            'created_at': message.created_at.isoformat(),
            'time_label': message.created_at.strftime('%I:%M %p').lstrip('0'),
        }
        for message in messages
    ]


def _session_title_from_message(message):
    compact = _compact_text(message)
    if len(compact) <= 60:
        return compact
    return f"{compact[:57].rstrip()}..."


def _chat_session_summaries_for_user(user, sessions=None):
    if not user.is_authenticated:
        return []

    session_list = sessions if sessions is not None else _chat_sessions_for_user(user)
    summaries = []

    for session in session_list:
        messages = list(session.messages.all())
        preview_source = messages[-1].content if messages else session.title
        preview = _compact_text(preview_source)
        if len(preview) > 80:
            preview = f"{preview[:77].rstrip()}..."

        summaries.append({
            'id': session.id,
            'title': session.title,
            'preview': preview or 'No messages yet',
            'updated_iso': session.updated_at.isoformat(),
            'updated_label': session.updated_at.strftime('%b %d, %I:%M %p').replace(' 0', ' '),
            'message_count': len(messages),
        })

    return summaries


def _touch_chat_session(chat_session):
    chat_session.updated_at = timezone.now()
    chat_session.save(update_fields=['updated_at'])


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


def _response_cache_key(user_message, history, document_ids=None):
    payload = json.dumps(
        {
            'message': user_message,
            'history': history,
            'documents': document_ids or [],
        },
        sort_keys=True,
    )
    return f"chat-response:{sha256(payload.encode('utf-8')).hexdigest()}"


def _serialize_chat_document(document):
    return {
        'id': document.id,
        'title': document.title,
        'file_type': document.file_type,
        'file_size_display': _format_file_size(document.file_size),
        'url': reverse('chatbot_download_document', args=[document.id]),
    }


def _build_file_download_response(file_field):
    file_name = file_field.name.split('/')[-1]

    try:
        return FileResponse(file_field, as_attachment=True, filename=file_name)
    except Exception:
        # Fallback for remote storages that cannot be streamed directly.
        return HttpResponseRedirect(file_field.url)


def _pairwise_history_summary(messages, max_chars):
    if not messages or max_chars <= 0:
        return ''

    summary_lines = []
    pending_user_message = None

    for message in messages:
        if message.role == ChatMessage.USER:
            pending_user_message = _truncate_for_history(message.content, 120)
            continue

        assistant_text = _truncate_for_history(message.content, 160)
        if pending_user_message:
            summary_lines.append(
                f"- User asked about: {pending_user_message} | Assistant replied: {assistant_text}"
            )
            pending_user_message = None
        else:
            summary_lines.append(f"- Assistant replied: {assistant_text}")

    if pending_user_message:
        summary_lines.append(f"- User asked about: {pending_user_message}")

    summary = "Earlier conversation summary:\n" + "\n".join(summary_lines)
    if len(summary) <= max_chars:
        return summary

    trimmed_lines = []
    current_length = len("Earlier conversation summary:\n")
    for line in summary_lines:
        line_length = len(line) + 1
        if current_length + line_length > max_chars:
            break
        trimmed_lines.append(line)
        current_length += line_length

    if not trimmed_lines:
        return _truncate_for_history(summary, max_chars)

    return "Earlier conversation summary:\n" + "\n".join(trimmed_lines)


def _build_history_prompt(messages):
    max_recent_messages = max(getattr(settings, 'CHAT_HISTORY_MAX_RECENT_MESSAGES', 12), 0)
    max_history_chars = max(getattr(settings, 'CHAT_HISTORY_MAX_CHARS', 6000), 0)
    summary_char_budget = max(getattr(settings, 'CHAT_HISTORY_SUMMARY_MAX_CHARS', 1600), 0)

    ordered_messages = list(messages)
    if not ordered_messages or max_history_chars == 0:
        return ''

    recent_messages = ordered_messages[-max_recent_messages:] if max_recent_messages else []
    older_messages = ordered_messages[:-max_recent_messages] if max_recent_messages else ordered_messages

    sections = []
    if older_messages and summary_char_budget:
        sections.append(_pairwise_history_summary(older_messages, summary_char_budget))

    if recent_messages:
        recent_lines = [
            f"{'User' if message.role == ChatMessage.USER else 'Assistant'}: "
            f"{_truncate_for_history(message.content, 500)}"
            for message in recent_messages
        ]
        sections.append("Recent conversation:\n" + "\n".join(recent_lines))

    history_prompt = "\n\n".join(section for section in sections if section)
    if len(history_prompt) <= max_history_chars:
        return history_prompt

    if recent_messages:
        trimmed_recent_lines = []
        recent_header_length = len("Recent conversation:\n")
        reserved_length = 0
        if older_messages and summary_char_budget:
            older_summary = _pairwise_history_summary(
                older_messages,
                min(summary_char_budget, max_history_chars // 2),
            )
            sections = [older_summary] if older_summary else []
            reserved_length = len("\n\n".join(sections)) + (2 if sections else 0)
        else:
            sections = []

        current_length = reserved_length + recent_header_length
        for line in reversed(recent_lines):
            line_length = len(line) + 1
            if current_length + line_length > max_history_chars:
                break
            trimmed_recent_lines.insert(0, line)
            current_length += line_length

        if trimmed_recent_lines:
            sections.append("Recent conversation:\n" + "\n".join(trimmed_recent_lines))
            return "\n\n".join(sections)

    return _truncate_for_history(history_prompt, max_history_chars)


def _format_file_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def _find_related_documents(user_message, limit=CHAT_DOCUMENT_RESULT_LIMIT):
    if not DOCUMENT_INTENT_PATTERN.search(user_message):
        return []

    keywords = [
        word for word in re.findall(r'[a-zA-Z0-9]{3,}', user_message.lower())
        if word not in DOCUMENT_KEYWORD_STOPWORDS
    ]

    queryset = Document.objects.filter(status='active')
    search_terms = keywords[:6]

    if not search_terms:
        return []

    if search_terms:
        query = models.Q()
        for term in search_terms:
            query |= (
                models.Q(title__icontains=term)
                | models.Q(description__icontains=term)
                | models.Q(category__icontains=term)
                | models.Q(file_type__icontains=term)
                | models.Q(file__icontains=term)
            )
        queryset = queryset.filter(query)

    return list(queryset.order_by('-download_count', '-updated_at')[:limit])


def _documents_from_recent_attachments(chat_session, limit=CHAT_DOCUMENT_RESULT_LIMIT):
    if chat_session is None:
        return []

    recent_assistant_messages = list(
        chat_session.messages.filter(role=ChatMessage.ASSISTANT).order_by('-created_at')[:8]
    )

    ordered_document_ids = []
    seen_ids = set()

    for message in recent_assistant_messages:
        for attachment in (message.attachments or []):
            doc_id = attachment.get('id')
            if not doc_id or doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            ordered_document_ids.append(doc_id)
            if len(ordered_document_ids) >= limit:
                break
        if len(ordered_document_ids) >= limit:
            break

    if not ordered_document_ids:
        return []

    document_map = {
        document.id: document
        for document in Document.objects.filter(id__in=ordered_document_ids, status='active')
    }
    return [document_map[doc_id] for doc_id in ordered_document_ids if doc_id in document_map]


def _document_context_for_prompt(documents):
    if not documents:
        return ''

    lines = [
        "Admin-uploaded documents available for this request:",
    ]
    for document in documents:
        description = _truncate_for_history(document.description, 180) if document.description else 'No description provided.'
        lines.append(
            f"- Title: {document.title} | Type: {document.file_type} | Category: {document.category} | Description: {description}"
        )

    lines.append(
        "If one or more of these documents match the user's request, answer that the document is available and mention that the relevant file is attached."
    )
    return "\n".join(lines)


def _serialize_role_request(role_request):
    if role_request is None:
        return None

    return {
        'id': role_request.id,
        'status': role_request.status,
        'status_label': role_request.get_status_display(),
        'student_number': role_request.student_number,
        'position': role_request.position,
        'organization': role_request.organization,
        'requested_at': role_request.requested_at.isoformat(),
        'requested_at_label': role_request.requested_at.strftime('%Y-%m-%d %H:%M'),
        'reviewed_at': role_request.reviewed_at.isoformat() if role_request.reviewed_at else None,
        'reviewed_at_label': role_request.reviewed_at.strftime('%Y-%m-%d %H:%M') if role_request.reviewed_at else None,
        'reviewed_by': role_request.reviewed_by.email if role_request.reviewed_by else None,
    }


def _account_type_payload(user):
    if not user.is_authenticated:
        return {
            'value': Student.ACCOUNT_GENERAL,
            'label': 'General',
            'organization': '',
            'position': '',
        }

    return {
        'value': user.account_type,
        'label': user.get_account_type_display(),
        'organization': user.leader_organization,
        'position': user.leader_position,
    }


@ensure_csrf_cookie
def chatbot_home(request, session_id=None):
    chat_sessions = _chat_sessions_for_user(request.user)
    chat_session_summaries = _chat_session_summaries_for_user(request.user, sessions=chat_sessions)
    current_session = None
    current_messages = []
    can_access_documents = _can_access_documents(request.user)

    if session_id is not None and request.user.is_authenticated:
        current_session = ChatSession.objects.filter(
            id=session_id,
            user=request.user,
        ).prefetch_related('messages').first()
        if current_session is None:
            return redirect('chatbot_home')
        current_messages = _serialize_messages(
            current_session.messages.all(),
            include_attachments=can_access_documents,
        )

    return render(request, 'chatbot/index.html', {
        'chat_sessions': chat_sessions,
        'chat_session_summaries': chat_session_summaries,
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
                if user.is_dashboard_admin:
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
    chat_sessions = _chat_sessions_for_user(request.user)
    latest_role_request = None
    if request.user.is_authenticated:
        latest_role_request = RoleRequest.objects.filter(
            user=request.user,
        ).select_related('reviewed_by').order_by('-requested_at').first()

    return render(request, 'chatbot/profile.html', {
        'chat_sessions': chat_sessions,
        'chat_session_summaries': _chat_session_summaries_for_user(
            request.user,
            sessions=chat_sessions,
        ),
        'latest_role_request': latest_role_request,
        'account_type_payload': _account_type_payload(request.user),
    })


def request_form_view(request):
    return render(request, 'chatbot/request_form.html', {
        'chat_sessions': _chat_sessions_for_user(request.user),
    })


def faqs_view(request):
    chat_sessions = _chat_sessions_for_user(request.user)
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    faqs = FAQ.objects.filter(is_active=True)
    if query:
        faqs = faqs.filter(
            models.Q(question__icontains=query)
            | models.Q(answer__icontains=query)
            | models.Q(tags__icontains=query)
        )
    if category:
        faqs = faqs.filter(category=category)

    faqs = faqs.order_by('-updated_at', '-created_at')
    categories = (
        FAQ.objects.filter(is_active=True)
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )

    return render(request, 'chatbot/faqs.html', {
        'chat_sessions': chat_sessions,
        'chat_session_summaries': _chat_session_summaries_for_user(
            request.user,
            sessions=chat_sessions,
        ),
        'faqs': faqs,
        'categories': categories,
        'query': query,
        'selected_category': category,
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

        if request.user.account_type == Student.ACCOUNT_STUDENT_LEADER:
            return JsonResponse({
                'success': False,
                'error': 'Your account is already set to Student Leader.',
            }, status=400)

        existing_pending = RoleRequest.objects.filter(
            user=request.user,
            status=RoleRequest.STATUS_PENDING,
        ).order_by('-requested_at').first()

        if existing_pending:
            return JsonResponse({
                'success': True,
                'already_pending': True,
                'message': 'You already have a pending request under review.',
                'request': _serialize_role_request(existing_pending),
                'account_type': _account_type_payload(request.user),
                'request_id': existing_pending.id,
            })

        role_request = RoleRequest.objects.create(
            user=request.user,
            student_number=student_number,
            position=position,
            organization=organization,
        )
        requester_display = request.user.get_full_name() or request.user.username or request.user.email
        admin_message = (
            f'{requester_display} submitted a Student Leader role request '
            f'for {organization} as {position}.'
        )
        admin_users = [
            admin
            for admin in Student.objects.filter(is_active=True, is_staff=True).exclude(id=request.user.id)
            if admin.is_dashboard_admin
        ]
        admin_notifications = [
            Notification(
                recipient=admin,
                requester=request.user,
                role_request=role_request,
                title='New role request submitted',
                message=admin_message,
                type=Notification.TYPE_INFO,
                action_url='/dashboard/role-requests/',
            )
            for admin in admin_users
        ]
        if admin_notifications:
            Notification.objects.bulk_create(admin_notifications)

        create_notification(
            recipient=request.user,
            requester=request.user,
            role_request=role_request,
            title='Role request submitted',
            message='Your Student Leader role request has been submitted and is now under admin review.',
            notif_type=Notification.TYPE_SUCCESS,
            action_url='/chatbot/profile/',
        )

        return JsonResponse({
            'success': True,
            'already_pending': False,
            'message': 'Request submitted successfully and sent for admin review.',
            'request': _serialize_role_request(role_request),
            'account_type': _account_type_payload(request.user),
            'request_id': role_request.id,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def my_role_request_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    latest_request = RoleRequest.objects.filter(
        user=request.user,
    ).select_related('reviewed_by').order_by('-requested_at').first()

    return JsonResponse({
        'success': True,
        'has_request': latest_request is not None,
        'request': _serialize_role_request(latest_request),
        'account_type': _account_type_payload(request.user),
    })


@require_http_methods(["DELETE"])
def delete_chat_session(request, session_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    chat_session = ChatSession.objects.filter(
        id=session_id,
        user=request.user,
    ).first()

    if chat_session is None:
        return JsonResponse({'success': False, 'error': 'Chat session not found.'}, status=404)

    chat_session.delete()

    return JsonResponse({'success': True, 'message': 'Chat session deleted successfully.'})


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
        if len(user_message) > MAX_CHAT_MESSAGE_LENGTH:
            return JsonResponse({
                'error': f'Message must be {MAX_CHAT_MESSAGE_LENGTH} characters or less.'
            }, status=400)

        chat_session = None
        history_prompt = ''
        related_documents = []
        can_access_documents = _can_access_documents(request.user)
        document_intent_detected = DOCUMENT_INTENT_PATTERN.search(user_message) is not None

        if can_access_documents:
            related_documents = _find_related_documents(user_message)

        if request.user.is_authenticated and session_id:
            chat_session = ChatSession.objects.filter(
                id=session_id,
                user=request.user,
            ).prefetch_related('messages').first()

            if chat_session is None:
                return JsonResponse({'error': 'Chat session not found.'}, status=404)

            history_prompt = _build_history_prompt(chat_session.messages.all())

            if can_access_documents and not related_documents and document_intent_detected:
                related_documents = _documents_from_recent_attachments(chat_session)

        if document_intent_detected and not can_access_documents:
            assistant_reply = DOCUMENT_ACCESS_RESTRICTION_MESSAGE
        else:
            prompt = user_message
            if history_prompt:
                prompt = f"{history_prompt}\nUser: {user_message}\nAssistant:"

            if related_documents:
                prompt = f"{_document_context_for_prompt(related_documents)}\n\n{prompt}"

            response_cache_key = _response_cache_key(
                user_message,
                history_prompt,
                document_ids=[document.id for document in related_documents],
            )
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
                attachments=[_serialize_chat_document(document) for document in related_documents],
            )
            _touch_chat_session(chat_session)

        return JsonResponse({
            'response': assistant_reply,
            'documents': [_serialize_chat_document(document) for document in related_documents],
            'session_id': chat_session.id if chat_session else None,
            'session_title': chat_session.title if chat_session else None,
            'session_url': reverse('chat_session', args=[chat_session.id]) if chat_session else None,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def download_chat_document(request, doc_id):
    if not _can_access_documents(request.user):
        raise Http404("Document not found.")

    try:
        doc = Document.objects.get(id=doc_id, status='active')
        if not doc.file:
            raise Http404("File not found.")

        doc.download_count += 1
        doc.save(update_fields=['download_count'])

        return _build_file_download_response(doc.file)
    except Document.DoesNotExist:
        raise Http404("Document not found.")


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
            if not email.endswith('@tip.edu.ph'):
                return JsonResponse({'success': False, 'error': 'Must be a TIP email.'})

            if Student.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'This email is already registered.'})

            otp = "".join(str(secrets.randbelow(10)) for _ in range(6))

            request.session['email_otp'] = otp
            request.session['otp_email_target'] = email
            request.session['otp_timestamp'] = time.time()
            request.session['otp_verified'] = False

            subject = "Your IntelliChat Verification Code"
            message = f"Hello! Your verification code is: {otp}\n\nThis code will expire in 10 minutes."
            _send_transactional_email(email, subject, message)

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
            _send_transactional_email(email, subject, message)

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
            _send_transactional_email(email, subject, message)

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

        if not (profile_picture.content_type or '').startswith('image/'):
            return JsonResponse({'success': False, 'error': 'File must be an image.'})

        try:
            if request.user.profile_picture:
                request.user.profile_picture.delete(save=False)

            request.user.profile_picture = profile_picture
            request.user.save()
            return JsonResponse({
                'success': True,
                'image_url': request.user.profile_picture.url
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
