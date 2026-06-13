from django.urls import path
from . import views

urlpatterns = [
    path('groups/<int:group_id>/messages/', views.GroupMessagesView.as_view(), name='group-messages'),
    path('expenses/<int:expense_id>/messages/', views.ExpenseMessagesView.as_view(), name='expense-messages'),
]