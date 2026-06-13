from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from .models import Settlement
from .serializers import SettlementSerializer
from groups.models import Group, GroupMember
import razorpay


class SettlementListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        settlements = group.settlements.all().order_by('-created_at')
        return Response(SettlementSerializer(settlements, many=True).data)

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        serializer = SettlementSerializer(data=request.data)
        if serializer.is_valid():
            settlement = serializer.save(
                group=group,
                settled_at=timezone.now(),
                status='completed'
            )
            return Response(SettlementSerializer(settlement).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.create({
                'amount': int(float(amount) * 100),  # paise
                'currency': 'INR',
                'payment_capture': 1
            })
            return Response({
                'order_id': order['id'],
                'amount': amount,
                'currency': 'INR',
                'key': settings.RAZORPAY_KEY_ID
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)
        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')
        payee_id = request.data.get('payee_id')
        amount = request.data.get('amount')

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            settlement = Settlement.objects.create(
                group=group,
                payer=request.user,
                payee_id=payee_id,
                amount=amount,
                method='online',
                payment_ref=payment_id,
                status='completed',
                settled_at=timezone.now()
            )
            return Response(SettlementSerializer(settlement).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': 'Payment verification failed'}, status=status.HTTP_400_BAD_REQUEST)