"""URLs for Resource Manager App"""
from django.urls import path
from . import views
from . import views_theme

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # AJAX endpoints
    path('occupy/', views.occupy_resource, name='occupy_resource'),
    path('release/', views.release_resource, name='release_resource'),
    path('join-queue/', views.join_queue, name='join_queue'),
    path('leave-queue/', views.leave_queue, name='leave_queue'),
    path('extend-time/', views.extend_time, name='extend_time'),
    path('status/', views.get_status, name='get_status'),
    path('theme/get/', views_theme.get_theme, name='get_theme'),
    path('theme/set/', views_theme.set_theme, name='set_theme'),
]
