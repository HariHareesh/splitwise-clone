from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', views.MarkReadView.as_view(), name='notification-read'),
    path('notifications/read-all/', views.MarkAllReadView.as_view(), name='notification-read-all'),
]