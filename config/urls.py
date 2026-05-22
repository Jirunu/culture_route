from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('culture.urls')),
    path('api/ai/', include('ai.urls')),

    # Pages
    path('', TemplateView.as_view(template_name='index.html')),
    path('login/', TemplateView.as_view(template_name='login.html')),
    path('signup/', TemplateView.as_view(template_name='signup.html')),
    path('places/', TemplateView.as_view(template_name='places.html')),
    path('places/<int:pk>/', TemplateView.as_view(template_name='place_detail.html')),
    path('routes/', TemplateView.as_view(template_name='routes.html')),
    path('preview/', TemplateView.as_view(template_name='preview.html')),
    path('ai/', TemplateView.as_view(template_name='ai_chat.html')),
]
