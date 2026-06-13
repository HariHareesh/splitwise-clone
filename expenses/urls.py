from django.urls import path
from . import views

urlpatterns = [
    path('groups/<int:group_id>/expenses/', views.ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense-detail'),
    path('expenses/<int:pk>/splits/', views.ExpenseSplitsView.as_view(), name='expense-splits'),
]