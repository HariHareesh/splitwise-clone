from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Message
from .serializers import MessageSerializer
from groups.models import Group, GroupMember
from expenses.models import Expense


class GroupMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=403)
        messages = Message.objects.filter(group=group, is_deleted=False).order_by('created_at')[:100]
        return Response(MessageSerializer(messages, many=True).data)


class ExpenseMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, expense_id):
        expense = get_object_or_404(Expense, pk=expense_id, is_deleted=False)
        if not GroupMember.objects.filter(group=expense.group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=403)
        messages = Message.objects.filter(expense=expense, is_deleted=False).order_by('created_at')[:100]
        return Response(MessageSerializer(messages, many=True).data)