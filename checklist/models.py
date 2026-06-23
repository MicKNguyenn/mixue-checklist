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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    score = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
class AuditCategory(models.Model):
    
    title=models.CharField(
        max_length=255
    )

    weight=models.IntegerField()

    is_active=models.BooleanField(
        default=True
    )

class AuditItem(models.Model):

    category = models.ForeignKey(
        AuditCategory,
        on_delete=models.CASCADE,
        related_name="items"
    )

    title = models.CharField(max_length=255)

    score = models.IntegerField(default=10)  # điểm mỗi item

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
class AuditIssue(models.Model):

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="issues"
    )

    item = models.ForeignKey(   # ✅ BẮT BUỘC THÊM
        AuditItem,
        on_delete=models.SET_NULL,
        null=True
    )

    category = models.ForeignKey(
        AuditCategory,
        on_delete=models.SET_NULL,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("pass", "Đạt"),
            ("fail", "Không đạt"),
        ],
        default="pass"
    )

    note = models.TextField(blank=True, null=True)

    deduct_score = models.IntegerField(default=0)
    
class AuditIssueImage(models.Model):

    issue = models.ForeignKey(
        AuditIssue,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.URLField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
class AuditFixImage(models.Model):

    issue = models.ForeignKey(
        AuditIssue,
        on_delete=models.CASCADE,
        related_name="fix_images"
    )

    image = models.URLField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    

    
