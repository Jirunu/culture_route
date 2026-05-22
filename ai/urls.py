from django.urls import path
from . import views

urlpatterns = [
    path('chat/',     views.chat,            name='ai_chat'),
    path('guardrail/', views.guardrail,      name='ai_guardrail'),
    path('image/',    views.image_generate,  name='ai_image'),
    path('score/',    views.score,           name='ai_score'),
]
