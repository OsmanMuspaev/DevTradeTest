from django.db import models


class User(models.Model):
    github_id = models.BigIntegerField(unique=True)
    github_username = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=120, blank=True, null=True)
    age = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

class UserScript(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scripts")
    title = models.CharField(max_length=100)
    code = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_scripts"
