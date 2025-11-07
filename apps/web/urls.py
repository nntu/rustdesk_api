from django.urls import path

from apps.web import views

urlpatterns = [
    path('', views.index),
    path('login', views.login, name='web_login'),
    path('logout', views.logout, name='web_logout'),
    path('home', views.home, name='web_home'),
]
