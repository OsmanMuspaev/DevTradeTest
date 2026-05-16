from django.urls import path
from .views import (
    github_login,
    github_callback, 
    me,
    create_script,
    get_scripts,
    update_script,
    delete_script,
    update_user_profile,
)

urlpatterns = [
    path("auth/github/login", github_login),
    path("auth/github/callback", github_callback),
    path("me", me),
    path("scripts", get_scripts),
    path("scripts/create", create_script),
    path("scripts/<int:script_id>", update_script),
    path("scripts/<int:script_id>/delete", delete_script),
    path("profile/<int:user_id>", update_user_profile),
]
