from django.db import models
from accounts.models import Store


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

    image = models.ImageField(
        upload_to='reports/'
    )

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