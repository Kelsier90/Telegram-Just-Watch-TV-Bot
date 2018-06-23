from django.db import models
from django.db.models.signals import post_save
from django.utils import timezone
import datetime

# Create your models here.
class TelegramUser(models.Model):
    id = models.BigIntegerField(primary_key=True)
    username = models.CharField(max_length=32)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    country = models.CharField(max_length=2, default='GB')
    last_command_date = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

class TelegramBotCommand(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='commands')
    command = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']


def save_command(sender, instance, **kwargs):
    instance.user.last_command_date = datetime.datetime.now(tz=timezone.utc)
    instance.user.save()

post_save.connect(save_command, sender=TelegramBotCommand)