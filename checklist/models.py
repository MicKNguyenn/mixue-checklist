from django.db import models
from accounts.models import Store
from django.contrib.auth.models import User

class TimeSlot(models.Model):

    name = models.CharField(max_length=100)

    start_time = models.TimeField()

    end_time = models.TimeField()

    def __str__(self):
        return self.name


class ChecklistItem(models.Model):

    slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=255
    )


class Report(models.Model):

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE
    )

    item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.CASCADE
    )

    image = models.URLField(max_length=1000, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Chờ đánh giá'),
            ('pass', 'Đạt'),
            ('fail', 'Không đạt')
        ],
        default='pending'
    )

    note = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    latitude = models.FloatField(
        null=True,
        blank=True
    )

    longitude = models.FloatField(
        null=True,
        blank=True
    )
    
    report_date = models.DateField(
    null=True,
    blank=True
    )

class Audit(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    score = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class AuditIssue(models.Model):

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="issues"
    )

    image = models.URLField(max_length=1000, blank=True, null=True) # ảnh lỗi

    title = models.CharField(max_length=255, blank=True, null=True)

    note = models.TextField(blank=True, null=True)

    # 👉 ảnh khắc phục của nhân viên
    fix_image = models.URLField(max_length=1000, blank=True, null=True)

    # 👉 trạng thái QC đánh giá lại
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Chờ xử lý"),
            ("fixed", "Đã khắc phục"),
            ("pass", "Đạt"),
            ("fail", "Không đạt"),
        ],
        default="pending"
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)