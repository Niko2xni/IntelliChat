from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from .models import DashboardMetrics, CommonInquiry, ResponseTimeData, FAQ, Document
import json


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


@require_http_methods(["GET"])
def get_chart_data(request):
    """API endpoint to get chart data."""
    response_times = ResponseTimeData.objects.all().order_by('date')
    
    data = {
        'dates': [str(rt.date) for rt in response_times],
        'times': [rt.average_response_time for rt in response_times],
    }
    
    return JsonResponse(data)


@require_http_methods(["GET"])
def get_inquiries_data(request):
    """API endpoint to get common inquiries data."""
    inquiries = CommonInquiry.objects.all()
    
    data = {
        'labels': [inq.title for inq in inquiries],
        'data': [inq.count for inq in inquiries],
    }
    
    return JsonResponse(data)


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


@require_http_methods(["POST"])
@csrf_exempt
def upload_document(request):
    """API endpoint to upload a new document."""
    try:
        title = request.POST.get('title')
        category = request.POST.get('category', 'other')
        file = request.FILES.get('file')
        
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
        
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
        
        return JsonResponse({
            'status': 'success',
            'message': 'Document uploaded successfully',
            'document_id': doc.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_document(request, doc_id):
    """API endpoint to delete a document."""
    try:
        doc = Document.objects.get(id=doc_id)
        # Delete the file from storage
        if doc.file:
            doc.file.delete()
        doc.delete()
        return JsonResponse({'status': 'success', 'message': 'Document deleted successfully'})
    except Document.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def format_file_size(bytes_size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"
