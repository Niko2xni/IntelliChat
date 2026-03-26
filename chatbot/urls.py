from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_home, name='chatbot_home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('ask/', views.ask_gemini, name='ask_gemini'),
]