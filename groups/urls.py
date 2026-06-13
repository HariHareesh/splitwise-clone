from django.urls import path
from . import views

urlpatterns = [
    path('groups/', views.GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group-detail'),
    path('groups/<int:pk>/members/', views.GroupMemberView.as_view(), name='group-members'),
    path('groups/<int:pk>/members/<int:user_id>/', views.RemoveMemberView.as_view(), name='remove-member'),
    path('groups/<int:pk>/invite/', views.InviteView.as_view(), name='group-invite'),
    path('groups/join/<str:token>/', views.JoinGroupView.as_view(), name='join-group'),
    path('groups/<int:pk>/balances/', views.GroupBalancesView.as_view(), name='group-balances'),
    path('groups/<int:pk>/my-balance/', views.MyBalanceView.as_view(), name='my-balance'),
]