from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from .models import (
    AuditLog,
    CommonInquiry,
    DashboardMetrics,
    Document,
    FAQ,
    Notification,
    ResponseTimeData,
    RoleRequest,
    create_audit_log,
    create_notification,
)
import json

MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg'}


def is_admin(user):
    """Check if the user is an active administrator."""
    return user.is_active and user.is_staff


def _validate_document_upload(file):
    if not file:
        return 'No file provided'

    extension = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))
        return f'Unsupported file type. Allowed types: {allowed}.'

    if file.size > MAX_DOCUMENT_SIZE_BYTES:
        return 'File exceeds the 5 MB limit.'

    return None


@user_passes_test(is_admin, login_url='login')
def dashboard(request):
    """Main admin dashboard view."""
    try:
        metrics = DashboardMetrics.objects.latest('last_updated')
    except DashboardMetrics.DoesNotExist:
        metrics = DashboardMetrics.objects.create(
            total_chats=1247,
            active_users=342,
            avg_response_time=2.1,
            satisfaction_rate=94.0,
            chats_change=12.5,
            users_change=8.2,
            response_time_change=-5.3,
            satisfaction_change=3.1
        )
    
    inquiries = list(CommonInquiry.objects.all()[:5])

    # build simple arrays for javascript so we don't have to use template loops inside script tags
    # this avoids editor/linters showing red squiggles and also makes the data easier to consume.
    # no json.dumps here; json_script will handle serialization
    inquiry_labels = [inq.title for inq in inquiries]
    inquiry_counts = [inq.count for inq in inquiries]
    # fixed palette used both for chart and legend
    palette = ['#FFA500', '#FF7F50', '#FFD700', '#FF8C00', '#E69500']
    # pair each inquiry with a color for easier templating
    inquiry_items = [(inq, palette[idx % len(palette)]) for idx, inq in enumerate(inquiries)]

    inquiry_colors = palette

    context = {
        'metrics': metrics,
        'inquiries': inquiries,
        'inquiry_items': inquiry_items,
        'inquiry_labels': inquiry_labels,
        'inquiry_counts': inquiry_counts,
        'inquiry_colors': inquiry_colors,
    }
    
    return render(request, 'dashboard/index.html', context)

@user_passes_test(is_admin, login_url='login')
def admin_profile(request):
    """Admin profile page."""
    return render(request, 'dashboard/profile.html')


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET"])
def get_chart_data(request):
    """API endpoint to get chart data."""
    response_times = ResponseTimeData.objects.all().order_by('date')
    
    data = {
        'dates': [str(rt.date) for rt in response_times],
        'times': [rt.average_response_time for rt in response_times],
    }
    
    return JsonResponse(data)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET"])
def get_inquiries_data(request):
    """API endpoint to get common inquiries data."""
    inquiries = CommonInquiry.objects.all()
    
    data = {
        'labels': [inq.title for inq in inquiries],
        'data': [inq.count for inq in inquiries],
    }
    
    return JsonResponse(data)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET", "POST"])
@csrf_exempt
def update_metrics(request):
    """API endpoint to update dashboard metrics."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            metrics, created = DashboardMetrics.objects.get_or_create(pk=1)
            
            metrics.total_chats = data.get('total_chats', metrics.total_chats)
            metrics.active_users = data.get('active_users', metrics.active_users)
            metrics.avg_response_time = data.get('avg_response_time', metrics.avg_response_time)
            metrics.satisfaction_rate = data.get('satisfaction_rate', metrics.satisfaction_rate)
            metrics.chats_change = data.get('chats_change', metrics.chats_change)
            metrics.users_change = data.get('users_change', metrics.users_change)
            metrics.response_time_change = data.get('response_time_change', metrics.response_time_change)
            metrics.satisfaction_change = data.get('satisfaction_change', metrics.satisfaction_change)
            
            metrics.save()
            
            return JsonResponse({'status': 'success', 'message': 'Metrics updated'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Only POST is allowed'}, status=405)

@user_passes_test(is_admin, login_url='login')
def knowledge_base(request):
    """Knowledge Base management page."""
    faqs = FAQ.objects.filter(is_active=True).order_by('-created_at')
    categories = FAQ.objects.values_list('category', flat=True).distinct()
    all_tags = set()
    for faq in faqs:
        all_tags.update(faq.get_tags_list())
    
    context = {
        'faqs': faqs,
        'categories': categories,
        'tags': sorted(list(all_tags)),
    }
    
    return render(request, 'dashboard/knowledge_base.html', context)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET"])
def search_faqs(request):
    """API endpoint to search FAQs."""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    tag = request.GET.get('tag', '').strip()
    
    faqs = FAQ.objects.filter(is_active=True)
    
    if query:
        faqs = faqs.filter(
            models.Q(question__icontains=query) | 
            models.Q(answer__icontains=query) |
            models.Q(tags__icontains=query)
        )
    
    if category:
        faqs = faqs.filter(category=category)
    
    if tag:
        faqs = faqs.filter(tags__icontains=tag)
    
    faqs = faqs.order_by('-created_at')
    
    data = []
    for faq in faqs:
        data.append({
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'tags': faq.get_tags_list(),
            'category': faq.category,
            'created_at': faq.created_at.strftime('%Y-%m-%d %H:%M'),
            'view_count': faq.view_count,
        })
    
    return JsonResponse({'faqs': data})


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["POST"])
@csrf_exempt
def add_faq(request):
    """API endpoint to add a new FAQ."""
    try:
        data = json.loads(request.body)
        faq = FAQ.objects.create(
            question=data['question'],
            answer=data['answer'],
            tags=data['tags'],
            category=data.get('category', 'general')
        )
        return JsonResponse({
            'status': 'success',
            'message': 'FAQ added successfully',
            'faq_id': faq.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["POST"])
@csrf_exempt
def update_faq(request, faq_id):
    """API endpoint to update an existing FAQ."""
    try:
        data = json.loads(request.body)
        faq = FAQ.objects.get(id=faq_id)
        
        faq.question = data['question']
        faq.answer = data['answer']
        faq.tags = data['tags']
        faq.category = data.get('category', faq.category)
        faq.save()
        
        return JsonResponse({'status': 'success', 'message': 'FAQ updated successfully'})
    except FAQ.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'FAQ not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["DELETE"])
@csrf_exempt
def delete_faq(request, faq_id):
    """API endpoint to delete an FAQ."""
    try:
        faq = FAQ.objects.get(id=faq_id)
        faq.is_active = False  # Soft delete
        faq.save()
        return JsonResponse({'status': 'success', 'message': 'FAQ deleted successfully'})
    except FAQ.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'FAQ not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin, login_url='login')
def documents(request):
    """Document Management page."""
    docs = Document.objects.filter(status__in=['active', 'draft']).order_by('-created_at')
    categories = Document.objects.values_list('category', flat=True).distinct()
    
    # Calculate stats
    total_docs = docs.count()
    total_downloads = docs.aggregate(models.Sum('download_count'))['download_count__sum'] or 0
    active_docs = docs.filter(status='active').count()
    
    context = {
        'documents': docs,
        'categories': categories,
        'stats': {
            'total_documents': total_docs,
            'total_downloads': total_downloads,
            'active_documents': active_docs,
        }
    }
    
    return render(request, 'dashboard/documents.html', context)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET"])
def search_documents(request):
    """API endpoint to search documents."""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    
    docs = Document.objects.filter(status__in=['active', 'draft'])
    
    if query:
        docs = docs.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query)
        )
    
    if category:
        docs = docs.filter(category=category)
    
    docs = docs.order_by('-created_at')
    
    data = []
    for doc in docs:
        data.append({
            'id': doc.id,
            'title': doc.title,
            'file_type': doc.file_type,
            'file_size': doc.file_size,
            'file_size_display': format_file_size(doc.file_size),
            'category': doc.category,
            'status': doc.status,
            'download_count': doc.download_count,
            'view_count': doc.view_count,
            'created_at': doc.created_at.strftime('%b %d, %Y'),
            'description': doc.description,
        })
    
    return JsonResponse({'documents': data})


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["POST"])
@csrf_exempt
def upload_document(request):
    """API endpoint to upload a new document."""
    try:
        title = request.POST.get('title')
        category = request.POST.get('category', 'other')
        file = request.FILES.get('file')

        validation_error = _validate_document_upload(file)
        if validation_error:
            return JsonResponse({'status': 'error', 'message': validation_error}, status=400)
        
        # Get file extension
        file_name = file.name
        file_type = file_name.split('.')[-1].upper()
        
        # Create document
        doc = Document.objects.create(
            title=title or file_name,
            file=file,
            file_type=file_type,
            file_size=file.size,
            category=category,
            status='active'
        )
        create_audit_log(
            'Uploaded Document',
            request.user.email,
            f'Uploaded "{doc.title}" in {doc.category}.',
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Document uploaded successfully',
            'document_id': doc.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["DELETE"])
@csrf_exempt
def delete_document(request, doc_id):
    """API endpoint to delete a document."""
    try:
        doc = Document.objects.get(id=doc_id)
        title = doc.title
        # Delete the file from storage
        if doc.file:
            doc.file.delete()
        doc.delete()
        create_audit_log(
            'Deleted Document',
            request.user.email,
            f'Deleted "{title}" from documents.',
        )
        return JsonResponse({'status': 'success', 'message': 'Document deleted successfully'})
    except Document.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["POST"])
@csrf_exempt
def update_document(request, doc_id):
    """API endpoint to update an existing document."""
    try:
        doc = Document.objects.get(id=doc_id)
        title = request.POST.get('title')
        category = request.POST.get('category', doc.category)
        file = request.FILES.get('file')

        if title:
            doc.title = title
        doc.category = category

        if file:
            validation_error = _validate_document_upload(file)
            if validation_error:
                return JsonResponse({'status': 'error', 'message': validation_error}, status=400)

            # Delete old file safely
            if doc.file:
                doc.file.delete(save=False)
            doc.file = file
            doc.file_type = file.name.split('.')[-1].upper()
            doc.file_size = file.size

        doc.save()
        create_audit_log(
            'Updated Document',
            request.user.email,
            f'Updated "{doc.title}" in {doc.category}.',
        )
        return JsonResponse({'status': 'success', 'message': 'Document updated successfully'})
    except Document.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET"])
def download_document(request, doc_id):
    """API endpoint to download a document."""
    try:
        doc = Document.objects.get(id=doc_id)
        if not doc.file:
            raise Http404("File not found.")
        
        # Increment download counter natively
        doc.download_count += 1
        doc.save(update_fields=['download_count'])
        
        response = FileResponse(doc.file, as_attachment=True, filename=doc.file.name.split('/')[-1])
        return response
    except Document.DoesNotExist:
        raise Http404("Document not found.")


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["GET"])
def get_document_detail(request, doc_id):
    """API endpoint to fetch a single document's details."""
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Document not found'}, status=404)

    should_track_view = request.GET.get('track_view', '').lower() in ['1', 'true', 'yes']
    if should_track_view:
        Document.objects.filter(id=doc.id).update(view_count=models.F('view_count') + 1)
        doc.refresh_from_db(fields=['view_count'])

    file_name = doc.file.name.split('/')[-1] if doc.file else ''

    return JsonResponse({
        'status': 'success',
        'document': {
            'id': doc.id,
            'title': doc.title,
            'description': doc.description,
            'file_type': doc.file_type,
            'file_size': doc.file_size,
            'file_size_display': format_file_size(doc.file_size),
            'file_name': file_name,
            'category': doc.category,
            'category_label': dict(Document.CATEGORY_CHOICES).get(doc.category, doc.category),
            'status': doc.status,
            'status_label': dict(Document.STATUS_CHOICES).get(doc.status, doc.status),
            'download_count': doc.download_count,
            'view_count': doc.view_count,
            'created_at': doc.created_at.strftime('%b %d, %Y'),
            'updated_at': doc.updated_at.strftime('%b %d, %Y'),
            'download_url': f'/dashboard/api/download-document/{doc.id}/',
        },
    })


def format_file_size(bytes_size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

@user_passes_test(is_admin, login_url='login')
def logging_monitoring(request):
    """Logging and Monitoring page."""
    logs = AuditLog.objects.all()
    return render(request, 'dashboard/logging.html', {'logs': logs})


def _serialize_notification(notification):
    can_respond = bool(notification.requester_id and notification.role_request_id is None)
    return {
        'id': notification.id,
        'title': notification.title or 'Notification',
        'message': notification.message or '',
        'type': notification.type or Notification.TYPE_INFO,
        'created_at': notification.created_at.isoformat(),
        'action_url': notification.action_url or '',
        'can_respond': can_respond,
    }


def _notification_queryset_for_user(user):
    if not user.is_authenticated:
        return Notification.objects.none()
    return Notification.objects.filter(recipient=user)


@require_http_methods(["GET"])
def get_notifications(request):
    """Return current user's unread notifications for the UI dropdown."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    unread = _notification_queryset_for_user(request.user).filter(is_read=False).order_by('-created_at')
    unread_count = unread.count()
    payload = [_serialize_notification(item) for item in unread[:10]]

    return JsonResponse({'notifications': payload, 'unread_count': unread_count})


@require_http_methods(["POST"])
@csrf_exempt
def mark_notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        notification = _notification_queryset_for_user(request.user).get(id=notification_id)
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)

    if notification.is_read:
        return JsonResponse({'status': 'success', 'message': 'Notification already marked as read'})

    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return JsonResponse({'status': 'success', 'message': 'Notification marked as read'})


@require_http_methods(["POST"])
@csrf_exempt
def mark_all_notifications_read(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    updated = _notification_queryset_for_user(request.user).filter(is_read=False).update(is_read=True)

    return JsonResponse({
        'status': 'success',
        'message': f'Marked {updated} notifications as read',
    })


@require_http_methods(["GET"])
def get_notification_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0})

    unread_count = _notification_queryset_for_user(request.user).filter(is_read=False).count()

    return JsonResponse({'unread_count': unread_count})


@require_http_methods(["POST"])
@csrf_exempt
def submit_user_request(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    request_type = data.get('type', 'other')
    details = data.get('details', '').strip()

    requester_display = request.user.get_full_name() or request.user.username or request.user.email
    request_type_label = request_type.replace('_', ' ').title()
    admin_message = (
        f"{requester_display} submitted a {request_type_label.lower()} request. {details}"
    ).strip()

    admin_users = request.user.__class__.objects.filter(is_active=True, is_staff=True).exclude(id=request.user.id)
    admin_notifications = [
        Notification(
            recipient=admin,
            requester=request.user,
            title=f'{request_type_label} Request',
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
        title='Request Submitted',
        message=f'Your {request_type.replace("_", " ")} request has been submitted for admin review.',
        notif_type=Notification.TYPE_SUCCESS,
        action_url='/chatbot/profile/',
    )

    return JsonResponse({'status': 'success', 'message': 'Request submitted successfully'})


@require_http_methods(["POST"])
@csrf_exempt
def respond_to_user_request(request, notification_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Admin authentication required'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    response_type = data.get('response_type', 'info')
    details = data.get('details', '').strip()

    try:
        original = Notification.objects.select_related('requester').get(
            id=notification_id,
            recipient=request.user,
        )
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)

    requester = original.requester
    if requester is None:
        return JsonResponse({'error': 'No requester found for this notification'}, status=400)

    original.is_read = True
    original.save(update_fields=['is_read'])

    notif_type = Notification.TYPE_SUCCESS if response_type == 'approved' else Notification.TYPE_WARNING
    create_notification(
        recipient=requester,
        requester=request.user,
        title='Admin Response',
        message=f'Your request was marked as {response_type}. {details}'.strip(),
        notif_type=notif_type,
        action_url='/chatbot/profile/',
    )

    return JsonResponse({'status': 'success', 'message': 'Response sent successfully'})


@user_passes_test(is_admin, login_url='login')
def role_requests(request):
    """Account Elevation Requests management page."""
    requests_data = RoleRequest.objects.select_related('user', 'reviewed_by')

    return render(request, 'dashboard/role_requests.html', {'requests': requests_data})


@user_passes_test(is_admin, login_url='login')
@require_http_methods(["POST"])
@csrf_exempt
def manage_role_request(request, req_id):
    """API endpoint to accept or reject a role request."""
    action = request.POST.get('action', '').strip().lower()
    if action not in ['accept', 'reject']:
        return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

    try:
        role_request = RoleRequest.objects.select_related('user').get(id=req_id)
    except RoleRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Request not found'}, status=404)

    if role_request.status != RoleRequest.STATUS_PENDING:
        return JsonResponse({
            'status': 'error',
            'message': f'This request is already {role_request.status}.',
        }, status=400)

    role_request.status = RoleRequest.STATUS_ACCEPTED if action == 'accept' else RoleRequest.STATUS_REJECTED
    role_request.reviewed_at = timezone.now()
    role_request.reviewed_by = request.user
    role_request.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])

    if action == 'accept':
        # Local import avoids import cycles at module import time.
        from chatbot.models import Student

        role_request.user.account_type = Student.ACCOUNT_STUDENT_LEADER
        role_request.user.leader_organization = role_request.organization
        role_request.user.leader_position = role_request.position
        role_request.user.save(update_fields=['account_type', 'leader_organization', 'leader_position'])

    create_audit_log(
        'Approved Student Leader request' if action == 'accept' else 'Declined Student Leader request',
        request.user.email,
        f'{action.title()}ed role request for {role_request.user.email} ({role_request.organization} - {role_request.position}).',
    )

    decision_word = 'approved' if action == 'accept' else 'rejected'
    notification_type = Notification.TYPE_SUCCESS if action == 'accept' else Notification.TYPE_WARNING
    create_notification(
        recipient=role_request.user,
        requester=request.user,
        role_request=role_request,
        title=f'Role request {decision_word}',
        message=(
            f'Your Student Leader request for {role_request.organization} ({role_request.position}) '
            f'was {decision_word} by admin.'
        ),
        notif_type=notification_type,
        action_url='/chatbot/profile/',
    )

    Notification.objects.filter(
        role_request=role_request,
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    return JsonResponse({'status': 'success', 'message': f'Request {action}ed successfully.'})

