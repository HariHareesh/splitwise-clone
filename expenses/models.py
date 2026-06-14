from django.db import models
from users.models import User
from groups.models import Group


class Expense(models.Model):
    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal'),
        ('unequal', 'Unequal'),
        ('percentage', 'Percentage'),
        ('share', 'Share'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    original_currency = models.CharField(max_length=10, blank=True)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fx_rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPE_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    notes = models.TextField(blank=True)
    receipt_url = models.URLField(max_length=500, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    import_row = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'

    def __str__(self):
        return f"{self.title} - {self.total_amount}"


class ExpensePayer(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='payers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_payments')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'expense_payers'

    def __str__(self):
        return f"{self.user.email} paid {self.amount_paid}"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_splits')
    owed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    split_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'expense_splits'

    def __str__(self):
        return f"{self.user.email} owes {self.owed_amount}"