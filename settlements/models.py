from django.db import models
from users.models import User
from groups.models import Group


class Settlement(models.Model):
    METHOD_CHOICES = [('manual', 'Manual'), ('online', 'Online')]
    STATUS_CHOICES = [('pending', 'Pending'), ('completed', 'Completed')]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    payee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    payment_ref = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='completed')
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'settlements'

    def __str__(self):
        return f"{self.payer.email} -> {self.payee.email}: {self.amount}"