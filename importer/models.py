from django.db import models
from users.models import User
from groups.models import Group


class ImportSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='imports')
    imported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    anomaly_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'import_sessions'

    def __str__(self):
        return f"Import {self.filename} by {self.imported_by.username}"


class ImportAnomaly(models.Model):
    ACTION_CHOICES = [
        ('auto_fixed', 'Auto Fixed'),
        ('skipped', 'Skipped'),
        ('needs_review', 'Needs Review'),
        ('reclassified', 'Reclassified'),
    ]

    import_session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name='anomalies')
    row_number = models.IntegerField()
    anomaly_type = models.CharField(max_length=100)
    description = models.TextField()
    original_value = models.TextField(blank=True)
    resolved_value = models.TextField(blank=True)
    action_taken = models.CharField(max_length=50, choices=ACTION_CHOICES)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'import_anomalies'

    def __str__(self):
        return f"Row {self.row_number}: {self.anomaly_type}"