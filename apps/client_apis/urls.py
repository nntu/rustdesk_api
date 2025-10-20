from django.urls import path

from apps.client_apis import views

urlpatterns = [
    path('heartbeat', views.heartbeat),
    path('sysinfo', views.sysinfo),
    path('login', views.login),
    path('logout', views.logout),
    path('ab', views.ab),
    path('currentUser', views.current_user),
    path('users', views.users),
    path('peers', views.peers),
    path('ab/personal', views.ab_personal),
    path('device-group/accessible', views.device_group_accessible),
    path('audit/conn', views.audit_conn),
    path('audit/file', views.audit_file),
    path('time', views.time_test),
]
