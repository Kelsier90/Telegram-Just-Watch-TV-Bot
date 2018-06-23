from django.contrib import admin

from .models import TelegramUser

# Register your models here.
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'first_name',
        'last_name',
        'last_command',
        'country',
        'last_activity',
        'created',
    )

    search_fields = ('username',)

admin.site.register(TelegramUser, TelegramUserAdmin)
