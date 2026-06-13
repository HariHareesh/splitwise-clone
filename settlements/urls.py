from django.urls import path
from . import views

urlpatterns = [
    path('groups/<int:group_id>/settlements/', views.SettlementListCreateView.as_view(), name='settlement-list-create'),
    path('groups/<int:group_id>/settlements/initiate-payment/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('groups/<int:group_id>/settlements/verify-payment/', views.VerifyPaymentView.as_view(), name='verify-payment'),
]