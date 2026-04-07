from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('profile/', views.admin_profile, name='profile'),
    path('api/chart-data/', views.get_chart_data, name='chart_data'),
    path('api/inquiries-data/', views.get_inquiries_data, name='inquiries_data'),
    path('api/update-metrics/', views.update_metrics, name='update_metrics'),
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('api/search-faqs/', views.search_faqs, name='search_faqs'),
    path('api/add-faq/', views.add_faq, name='add_faq'),
    path('api/update-faq/<int:faq_id>/', views.update_faq, name='update_faq'),
    path('api/delete-faq/<int:faq_id>/', views.delete_faq, name='delete_faq'),
    path('documents/', views.documents, name='documents'),
    path('api/search-documents/', views.search_documents, name='search_documents'),
    path('api/upload-document/', views.upload_document, name='upload_document'),
    path('api/update-document/<int:doc_id>/', views.update_document, name='update_document'),
    path('api/delete-document/<int:doc_id>/', views.delete_document, name='delete_document'),
    path('api/download-document/<int:doc_id>/', views.download_document, name='download_document'),
    path('logging/', views.logging_monitoring, name='logging'),
    path('role-requests/', views.role_requests, name='role_requests'),
    path('api/manage-role-request/<int:req_id>/', views.manage_role_request, name='manage_role_request'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/count/', views.get_notification_count, name='get_notification_count'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/submit-request/', views.submit_user_request, name='submit_user_request'),
    path('api/notifications/<int:notification_id>/respond/', views.respond_to_user_request, name='respond_to_user_request'),
]
