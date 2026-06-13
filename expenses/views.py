from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Expense, ExpensePayer, ExpenseSplit
from .serializers import ExpenseSerializer, CreateExpenseSerializer, ExpenseSplitSerializer
from groups.models import Group, GroupMember


class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        expenses = group.expenses.filter(is_deleted=False).order_by('-created_at')
        return Response(ExpenseSerializer(expenses, many=True).data)

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        payers_data = data.pop('payers')
        splits_data = data.pop('splits')

        expense = Expense.objects.create(
            group=group,
            created_by=request.user,
            **data
        )

        # Create payers
        for payer in payers_data:
            ExpensePayer.objects.create(
                expense=expense,
                user_id=payer['user_id'],
                amount_paid=payer['amount_paid']
            )

        # Create splits based on split_type
        total = float(expense.total_amount)
        if expense.split_type == 'equal':
            count = len(splits_data)
            equal_amount = round(total / count, 2)
            for split in splits_data:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user_id=split['user_id'],
                    owed_amount=equal_amount,
                    split_value=equal_amount
                )
        elif expense.split_type == 'percentage':
            for split in splits_data:
                owed = round(total * float(split['split_value']) / 100, 2)
                ExpenseSplit.objects.create(
                    expense=expense,
                    user_id=split['user_id'],
                    owed_amount=owed,
                    split_value=split['split_value']
                )
        elif expense.split_type == 'share':
            total_shares = sum(float(s['split_value']) for s in splits_data)
            for split in splits_data:
                owed = round(total * float(split['split_value']) / total_shares, 2)
                ExpenseSplit.objects.create(
                    expense=expense,
                    user_id=split['user_id'],
                    owed_amount=owed,
                    split_value=split['split_value']
                )
        else:  # unequal
            for split in splits_data:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user_id=split['user_id'],
                    owed_amount=split['split_value'],
                    split_value=split['split_value']
                )

        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
        if not GroupMember.objects.filter(group=expense.group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        return Response(ExpenseSerializer(expense).data)

    def put(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
        if not GroupMember.objects.filter(group=expense.group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ExpenseSerializer(expense, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
        if not GroupMember.objects.filter(group=expense.group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        expense.is_deleted = True
        expense.deleted_at = timezone.now()
        expense.save()
        return Response({'message': 'Expense deleted'})


class ExpenseSplitsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
        if not GroupMember.objects.filter(group=expense.group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        splits = expense.splits.all()
        return Response(ExpenseSplitSerializer(splits, many=True).data)