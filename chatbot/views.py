from django.shortcuts import render


def chatbot_home(request):
    return render(request, 'chatbot/index.html')


def login_view(request):
    return render(request, 'chatbot/login.html')


def signup_view(request):
    return render(request, 'chatbot/signup.html')


def profile_view(request):
    return render(request, 'chatbot/profile.html')

