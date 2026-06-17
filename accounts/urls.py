from django.urls import path
from . import views

urlpatterns = [
    path('me/',                                   views.me,             name='me'),
    path('me/badge/',                             views.select_badge,  name='select_badge'),
    path('me/nickname/',                          views.set_nickname,  name='set_nickname'),
    path('login/',                                views.login_view,     name='login_api'),
    path('logout/',                               views.logout_view,    name='logout_api'),
    path('signup/',                               views.signup,         name='signup_api'),
    path('profile/<str:username>/',               views.profile_detail, name='profile_detail'),
    path('profile/<str:username>/follow/',        views.follow_toggle,  name='follow_toggle'),
]
