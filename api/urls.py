from django.urls import path
from .views import telegram_bot, query, providers, title, test

urlpatterns = [
    path('api/<token>/', telegram_bot, name="bot"),
    path('query/', query, name="query"),
    path('providers/', providers, name="providers"),
    path('title/<id>', title, name="title"),
    path('test/', test, name="test"),
]