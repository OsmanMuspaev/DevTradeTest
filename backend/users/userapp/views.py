import os
import jwt
import requests
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import User, UserScript


def github_login(request):
    client_id = os.getenv("GITHUB_CLIENT_ID")

    github_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        "&scope=user:email"
        "&redirect_uri=http://localhost/auth/callback"
    )

    return JsonResponse({"url": github_url})


@csrf_exempt
def github_callback(request):
    code = request.GET.get("code")

    if not code:
        return JsonResponse({"error": "GitHub code is missing"}, status=400)

    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "code": code,
        },
        timeout=10,
    )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return JsonResponse({"error": "Could not get GitHub access token"}, status=400)

    github_user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )

    github_user = github_user_response.json()

    github_id = github_user["id"]
    github_username = github_user.get("login")
    full_name = github_user.get("name")

    user, created = User.objects.get_or_create(
        github_id=github_id,
        defaults={
            "github_username": github_username,
            "full_name": full_name,
        },
    )

    if not created:
        user.github_username = github_username
        user.full_name = full_name
        user.save()

    app_token = jwt.encode(
        {
            "user_id": user.id,
            "github_id": user.github_id,
            "github_username": user.github_username,
        },
        os.getenv("DJANGO_SECRET_KEY", "dev-secret-key"),
        algorithm="HS256",
    )

    return JsonResponse({
        "token": app_token,
        "user": {
            "id": user.id,
            "github_id": user.github_id,
            "github_username": user.github_username,
            "full_name": user.full_name,
        }
    })


def me(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return JsonResponse({"error": "Authorization header missing"}, status=401)

    try:
        token = auth_header.replace("Bearer ", "")
        payload = jwt.decode(
            token,
            os.getenv("DJANGO_SECRET_KEY", "dev-secret-key"),
            algorithms=["HS256"],
        )
    except Exception:
        return JsonResponse({"error": "Invalid token"}, status=401)

    user = User.objects.get(id=payload["user_id"])

    return JsonResponse({
        "id": user.id,
        "github_id": user.github_id,
        "github_username": user.github_username,
        "email": user.email,
        "full_name": user.full_name,
        "age": user.age,
    })


@csrf_exempt
def create_script(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data["user_id"]
        code = data["code"]
    except Exception:
        return JsonResponse({"error": "user_id and code are required"}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    next_number = UserScript.objects.filter(user=user).count() + 1

    script = UserScript.objects.create(
        user=user,
        title=f"script_{user.id}_{next_number}",
        code=code,
        is_active=True,
    )

    return JsonResponse(
        {
            "id": script.id,
            "title": script.title,
            "code": script.code,
            "is_active": script.is_active,
            "created_at": script.created_at,
            "updated_at": script.updated_at,
        },
        status=201,
    )

def get_scripts(request):
    user_id = request.GET.get("user_id")

    if not user_id:
        return JsonResponse({"error": "user_id is required"}, status=400)

    scripts = UserScript.objects.filter(user_id=user_id).order_by("-created_at")

    data = [
        {
            "id": script.id,
            "title": script.title,
            "code": script.code,
            "is_active": script.is_active,
            "created_at": script.created_at,
            "updated_at": script.updated_at,
        }
        for script in scripts
    ]

    return JsonResponse({"scripts": data})

@csrf_exempt
def update_script(request, script_id):
    if request.method != "PUT":
        return JsonResponse({"error": "Only PUT allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data["user_id"]
        code = data["code"]
    except Exception:
        return JsonResponse({"error": "user_id and code are required"}, status=400)

    try:
        script = UserScript.objects.get(id=script_id, user_id=user_id)
    except UserScript.DoesNotExist:
        return JsonResponse({"error": "Script not found"}, status=404)

    script.code = code
    script.save()

    return JsonResponse({
        "id": script.id,
        "title": script.title,
        "code": script.code,
        "is_active": script.is_active,
        "updated_at": script.updated_at,
    })

@csrf_exempt
def delete_script(request, script_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Only DELETE allowed"}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
        user_id = data.get("user_id") or request.GET.get("user_id")
    except Exception:
        user_id = request.GET.get("user_id")

    if not user_id:
        return JsonResponse({"error": "user_id is required"}, status=400)

    deleted_count, _ = UserScript.objects.filter(
        id=script_id,
        user_id=user_id,
    ).delete()

    if deleted_count == 0:
        return JsonResponse({"error": "Script not found"}, status=404)

    return JsonResponse({"status": "deleted"})


@csrf_exempt
def update_user_profile(request, user_id):
    if request.method != "PUT":
        return JsonResponse({"error": "Only PUT allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    allowed_fields = ["email", "full_name", "age"]

    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])

    user.save()

    return JsonResponse({
        "id": user.id,
        "github_id": user.github_id,
        "github_username": user.github_username,
        "email": user.email,
        "full_name": user.full_name,
        "age": user.age,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    })