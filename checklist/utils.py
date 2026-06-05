from datetime import timedelta
from django.utils import timezone
from .models import Report


def delete_old_reports():

    limit_date = (
        timezone.localdate()
        - timedelta(days=5) #Chỗ xóa data 
    )

    old_reports = Report.objects.filter(
        report_date__lt=limit_date
    )

    for report in old_reports:

        if report.image:

            report.image.delete(
                save=False
            )

        report.delete()