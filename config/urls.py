from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.views.generic import TemplateView
from culture import views as culture_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('culture.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/survey/save/',  culture_views.survey_save,  name='survey_save'),
    path('api/survey/reset/', culture_views.survey_reset, name='survey_reset'),

    # Pages
    path('', culture_views.index_view, name='index'),
    path('survey/', culture_views.survey_view, name='survey'),
    path('app/', culture_views.app_view, name='app'),
    path('login/', TemplateView.as_view(template_name='login.html')),
    path('signup/', TemplateView.as_view(template_name='signup.html')),
    path('places/', TemplateView.as_view(template_name='places.html')),
    path('places/<int:pk>/', TemplateView.as_view(template_name='place_detail.html')),
    path('routes/', TemplateView.as_view(template_name='routes.html')),
    path('preview/', TemplateView.as_view(template_name='preview.html')),
    path('ai/', login_required(TemplateView.as_view(template_name='ai_chat.html'))),
    path('accounts/profile/<str:username>/', TemplateView.as_view(template_name='profile.html')),
    path('loading/', login_required(TemplateView.as_view(template_name='loading.html'))),
    path('settings/', TemplateView.as_view(template_name='settings.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
