from rest_framework import serializers
from .models import Expense, ExpensePayer, ExpenseSplit
from users.serializers import UserSerializer


class ExpensePayerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ExpensePayer
        fields = ['id', 'user', 'user_id', 'amount_paid']


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ExpenseSplit
        fields = ['id', 'user', 'user_id', 'owed_amount', 'split_value']


class ExpenseSerializer(serializers.ModelSerializer):
    payers = ExpensePayerSerializer(many=True, read_only=True)
    splits = ExpenseSplitSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'group', 'title', 'total_amount', 'currency', 'split_type',
                  'created_by', 'notes', 'receipt_url', 'payers', 'splits', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class CreateExpenseSerializer(serializers.ModelSerializer):
    payers = serializers.ListField(child=serializers.DictField(), write_only=True)
    splits = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Expense
        fields = ['title', 'total_amount', 'currency', 'split_type', 'notes', 'receipt_url', 'payers', 'splits']

    def validate(self, attrs):
        total = float(attrs['total_amount'])
        payers = attrs.get('payers', [])
        splits = attrs.get('splits', [])
        split_type = attrs.get('split_type')

        # Validate payers sum
        payers_sum = sum(float(p['amount_paid']) for p in payers)
        if round(payers_sum, 2) != round(total, 2):
            raise serializers.ValidationError('Payers amounts must equal total amount')

        # Validate splits
        if split_type == 'percentage':
            pct_sum = sum(float(s['split_value']) for s in splits)
            if round(pct_sum, 2) != 100.0:
                raise serializers.ValidationError('Percentages must sum to 100')

        return attrs