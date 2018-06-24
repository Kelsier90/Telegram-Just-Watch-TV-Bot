from django.db import models
from django.utils import timezone
import datetime

# Create your models here.
class TelegramUser(models.Model):
    id = models.BigIntegerField(primary_key=True)
    username = models.CharField(max_length=32)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    last_command = models.CharField(max_length=500, null=True)
    country = models.CharField(max_length=2, default='ES')
    last_activity = models.DateTimeField(auto_now=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']