from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_home, name='chatbot_home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('ask/', views.ask_gemini, name='ask_gemini'),
    path('send-otp/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('send-password-otp/', views.send_password_change_otp, name='send_password_otp'),
    path('verify-password-otp/', views.verify_password_change_otp, name='verify_password_otp'),
    path('update-password/', views.update_password, name='update_password'),
]