import json
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from google import genai


@ensure_csrf_cookie
def chatbot_home(request):
    return render(request, 'chatbot/index.html')


def login_view(request):
    return render(request, 'chatbot/login.html')


def signup_view(request):
    return render(request, 'chatbot/signup.html')


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
