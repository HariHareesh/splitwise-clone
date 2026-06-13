from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Group, GroupMember, GroupInvite
from .serializers import GroupSerializer, GroupMemberSerializer, GroupInviteSerializer
from expenses.models import ExpensePayer, ExpenseSplit
from settlements.models import Settlement
from users.models import User
from users.serializers import UserSerializer


class GroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = GroupMember.objects.filter(user=request.user, is_active=True)
        groups = [m.group for m in memberships if m.group.is_active]
        return Response(GroupSerializer(groups, many=True).data)

    def post(self, request):
        serializer = GroupSerializer(data=request.data)
        if serializer.is_valid():
            group = serializer.save(created_by=request.user)
            GroupMember.objects.create(group=group, user=request.user, role='admin')
            return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_group(self, pk, user):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        if not GroupMember.objects.filter(group=group, user=user, is_active=True).exists():
            return None, Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        return group, None

    def get(self, request, pk):
        group, err = self.get_group(pk, request.user)
        if err:
            return err
        return Response(GroupSerializer(group).data)

    def put(self, request, pk):
        group, err = self.get_group(pk, request.user)
        if err:
            return err
        member = GroupMember.objects.get(group=group, user=request.user)
        if member.role != 'admin':
            return Response({'error': 'Only admins can edit group'}, status=status.HTTP_403_FORBIDDEN)
        serializer = GroupSerializer(group, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        group, err = self.get_group(pk, request.user)
        if err:
            return err
        member = GroupMember.objects.get(group=group, user=request.user)
        if member.role != 'admin':
            return Response({'error': 'Only admins can delete group'}, status=status.HTTP_403_FORBIDDEN)
        group.is_active = False
        group.save()
        return Response({'message': 'Group deleted'})


class GroupMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        members = GroupMember.objects.filter(group=group, is_active=True)
        return Response(GroupMemberSerializer(members, many=True).data)

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        member = get_object_or_404(GroupMember, group=group, user=request.user)
        if member.role != 'admin':
            return Response({'error': 'Only admins can add members'}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        obj, created = GroupMember.objects.get_or_create(group=group, user=user, defaults={'role': 'member'})
        if not created:
            obj.is_active = True
            obj.save()
        return Response(GroupMemberSerializer(obj).data, status=status.HTTP_201_CREATED)


class RemoveMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, user_id):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        admin_member = get_object_or_404(GroupMember, group=group, user=request.user)
        if admin_member.role != 'admin':
            return Response({'error': 'Only admins can remove members'}, status=status.HTTP_403_FORBIDDEN)
        member = get_object_or_404(GroupMember, group=group, user_id=user_id)
        member.is_active = False
        member.save()
        return Response({'message': 'Member removed'})


class InviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        member = get_object_or_404(GroupMember, group=group, user=request.user)
        if member.role != 'admin':
            return Response({'error': 'Only admins can invite'}, status=status.HTTP_403_FORBIDDEN)
        email = request.data.get('email', '')
        invite = GroupInvite.objects.create(
            group=group,
            invited_by=request.user,
            email=email,
            expires_at=timezone.now() + timedelta(days=7)
        )
        return Response({
            'invite_token': str(invite.token),
            'invite_link': f"/api/groups/join/{invite.token}/",
            'email': email
        }, status=status.HTTP_201_CREATED)


class JoinGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        invite = get_object_or_404(GroupInvite, token=token, status='pending')
        if invite.expires_at < timezone.now():
            invite.status = 'expired'
            invite.save()
            return Response({'error': 'Invite expired'}, status=status.HTTP_400_BAD_REQUEST)
        obj, created = GroupMember.objects.get_or_create(
            group=invite.group, user=request.user,
            defaults={'role': 'member'}
        )
        if not created:
            obj.is_active = True
            obj.save()
        invite.status = 'accepted'
        invite.save()
        return Response({'message': f"Joined {invite.group.name}"})


class GroupBalancesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        members = GroupMember.objects.filter(group=group, is_active=True)
        balances = {}
        for m in members:
            balances[m.user.id] = {
                'user': UserSerializer(m.user).data,
                'total_paid': 0,
                'total_owed': 0,
                'net': 0
            }

        expenses = group.expenses.filter(is_deleted=False)
        for expense in expenses:
            for payer in expense.payers.all():
                if payer.user.id in balances:
                    balances[payer.user.id]['total_paid'] += float(payer.amount_paid)
            for split in expense.splits.all():
                if split.user.id in balances:
                    balances[split.user.id]['total_owed'] += float(split.owed_amount)

        for settlement in group.settlements.filter(status='completed'):
            if settlement.payer.id in balances:
                balances[settlement.payer.id]['total_paid'] += float(settlement.amount)
            if settlement.payee.id in balances:
                balances[settlement.payee.id]['total_owed'] += float(settlement.amount)

        for uid in balances:
            balances[uid]['net'] = round(balances[uid]['total_paid'] - balances[uid]['total_owed'], 2)

        # Debt simplification
        creditors = []
        debtors = []
        for uid, data in balances.items():
            if data['net'] > 0:
                creditors.append([uid, data['net']])
            elif data['net'] < 0:
                debtors.append([uid, -data['net']])

        creditors.sort(key=lambda x: -x[1])
        debtors.sort(key=lambda x: -x[1])

        transactions = []
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debt = debtors[i][1]
            credit = creditors[j][1]
            amount = min(debt, credit)
            transactions.append({
                'from': balances[debtors[i][0]]['user'],
                'to': balances[creditors[j][0]]['user'],
                'amount': round(amount, 2)
            })
            debtors[i][1] -= amount
            creditors[j][1] -= amount
            if debtors[i][1] == 0:
                i += 1
            if creditors[j][1] == 0:
                j += 1

        return Response({
            'balances': list(balances.values()),
            'suggested_settlements': transactions
        })


class MyBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        total_paid = sum(
            float(p.amount_paid)
            for e in group.expenses.filter(is_deleted=False)
            for p in e.payers.filter(user=request.user)
        )
        total_owed = sum(
            float(s.owed_amount)
            for e in group.expenses.filter(is_deleted=False)
            for s in e.splits.filter(user=request.user)
        )
        net = round(total_paid - total_owed, 2)
        return Response({'total_paid': total_paid, 'total_owed': total_owed, 'net': net})