from django.contrib import admin
from .models import *
from django.utils.html import format_html


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    list_display = (
        "store",
        "item",
        "created_at",
        "preview"
    )

    def preview(self, obj):

        if obj.image:
            return format_html(
                '<img src="{}" width="120"/>',
                obj.image.url
            )

        return "-"


admin.site.register(TimeSlot)
admin.site.register(ChecklistItem)