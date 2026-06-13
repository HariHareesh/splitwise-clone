from rest_framework import serializers
from .models import Settlement
from users.serializers import UserSerializer


class SettlementSerializer(serializers.ModelSerializer):
    payer = UserSerializer(read_only=True)
    payee = UserSerializer(read_only=True)
    payer_id = serializers.IntegerField(write_only=True)
    payee_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Settlement
        fields = ['id', 'payer', 'payee', 'payer_id', 'payee_id', 'amount',
                  'method', 'payment_ref', 'status', 'settled_at', 'created_at']
        read_only_fields = ['id', 'created_at']