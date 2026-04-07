from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_home, name='chatbot_home'),
    path('sessions/<int:session_id>/', views.chatbot_home, name='chat_session'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('request/', views.request_form_view, name='request_form'),
    path('submit-role-request/', views.submit_role_request, name='submit_role_request'),
    path('ask/', views.ask_gemini, name='ask_gemini'),
    path('send-otp/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('send-password-otp/', views.send_password_change_otp, name='send_password_otp'),
    path('verify-password-otp/', views.verify_password_change_otp, name='verify_password_otp'),
    path('update-password/', views.update_password, name='update_password'),
    path('init-delete-account/', views.init_delete_account, name='init_delete_account'),
    path('confirm-delete-account/', views.confirm_delete_account, name='confirm_delete_account'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('init-change-email/', views.init_change_email, name='init_change_email'),
    path('confirm-change-email/', views.confirm_change_email, name='confirm_change_email'),
]