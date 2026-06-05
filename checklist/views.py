from django.shortcuts import render, redirect
from accounts.models import Store
from datetime import datetime
from django.utils import timezone
from datetime import timedelta
from .models import *
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO
from .utils import delete_old_reports
from django.utils.dateparse import parse_date
from django.http import JsonResponse
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from django.http import HttpResponse
from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side
)
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os
import uuid
import cloudinary.uploader
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST


def dashboard(request):
    
    delete_old_reports()
    
    all_slots = TimeSlot.objects.all()
    
    if "store_id" not in request.session:
        return redirect("/")

    store = Store.objects.get(
        id=request.session["store_id"]
    )

    current_slot = get_current_slot()

    items = ChecklistItem.objects.filter(
        slot=current_slot
    )

    now = timezone.localtime()

    today = now.date()

    if now.hour < 3:

        today = today - timedelta(
            days=1
        )

    completed_ids = Report.objects.filter(
        store=store,
        report_date=today
    ).values_list(
        "item_id",
        flat=True
    )

    return render(
        request,
        "checklist/dashboard.html",
        {
            "store": store,
            "items": items,
            "slot": current_slot,
            "all_slots": all_slots,
            "completed_ids": list(completed_ids)
        }
    )

def get_current_slot():

    now = datetime.now().time()

    slots = TimeSlot.objects.all()

    for slot in slots:

        if slot.start_time <= slot.end_time:

            if slot.start_time <= now <= slot.end_time:
                return slot

        else:

            if now >= slot.start_time or now <= slot.end_time:
                return slot

    return None

from PIL import Image, UnidentifiedImageError

def compress_image(image_file):
    try:
        img = Image.open(image_file)

        print("FORMAT =", img.format)

        img = img.convert("RGB")
        img.thumbnail((1280, 1280))

        output = BytesIO()

        img.save(
            output,
            format="JPEG",
            quality=75
        )

        output.seek(0)

        return ContentFile(output.read())

    except UnidentifiedImageError:
        raise Exception(
            f"Không đọc được ảnh: {image_file.name}"
        )

def upload_report(request, item_id):
    if "store_id" not in request.session:
        return redirect("/")

    store = Store.objects.get(id=request.session["store_id"])
    item = ChecklistItem.objects.get(id=item_id)

    if request.method == "POST":
        try:
            print("=== START UPLOAD ===")

            if "image" not in request.FILES:
                print("NO IMAGE")
                return redirect("/dashboard/")

            image_file = request.FILES["image"]

            print("FILE NAME:", image_file.name)
            print("CONTENT TYPE:", image_file.content_type)

            now = timezone.localtime()
            report_date = now.date()

            if now.hour < 3:
                report_date = report_date - timedelta(days=1)

            Report.objects.filter(
                store=store,
                item=item,
                report_date=report_date
            ).delete()

            random_public_id = f"mixue_{uuid.uuid4().hex[:10]}"

            print("COMPRESSING...")
            compressed_image = compress_image(image_file)

            print("UPLOADING TO CLOUDINARY...")
            upload_result = cloudinary.uploader.upload(
                compressed_image,
                folder="reports",
                public_id=random_public_id,
                overwrite=True,
                resource_type="image"
            )

            print("UPLOAD SUCCESS")

            cloudinary_url = upload_result.get("secure_url")

            print(cloudinary_url)

            Report.objects.create(
                store=store,
                item=item,
                image=cloudinary_url, # Lưu biến chứa link string vào trường image
                report_date=report_date
            )

            print("DB SAVE SUCCESS")

            return redirect("/dashboard/")

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return HttpResponse(
                f"<pre>{traceback.format_exc()}</pre>",
                status=500
            )

    return render(
        request,
        "checklist/upload.html",
        {"item": item}
    )
    
def admin_dashboard(request):

    today = timezone.now().date()

    return render(
        request,
        "checklist/admin_dashboard.html",
        {
            "today": today
        }
    )
    
def admin_day(request, date):

    selected_date = datetime.strptime(
        date,
        "%Y-%m-%d"
    ).date()

    stores = Store.objects.all()

    total_stores = 0
    completed_stores = 0
    partial_stores = 0
    missing_stores = 0
    
    data = []

    total_items = ChecklistItem.objects.count()

    for store in stores:

        completed = Report.objects.filter(
            store=store,
            report_date=selected_date
        ).count()

        percent = 0

        if total_items > 0:
            percent = round(
                completed * 100 / total_items
            )

        data.append({
            "store": store,
            "completed": completed,
            "total": total_items,
            "percent": percent
        })
        
        if percent == 100:
            completed_stores += 1

        elif percent == 0:
            missing_stores += 1

        else:
            partial_stores += 1

        total_stores += 1

    system_percent = 0

    if total_stores > 0:

        system_percent = round(
            completed_stores * 100 / total_stores
        )
    
    return render(
        request,
        "checklist/admin_day.html",
        {
            "selected_date": selected_date,
            "data": data,
            "total_stores": total_stores,
            "completed_stores": completed_stores,
            "partial_stores": partial_stores,
            "missing_stores": missing_stores,
            "system_percent": system_percent,
        }
    )
    
def admin_store(request, store_id, date):

    selected_date = datetime.strptime(date, "%Y-%m-%d").date()

    # =========================
    # AJAX UPDATE (KHÔNG RELOAD)
    # =========================
    if request.method == 'POST':

        report_id = request.POST.get("report_id")
        status = request.POST.get("status")
        note = request.POST.get("note")

        try:
            report = Report.objects.get(id=report_id)
            report.status = status
            report.note = note
            report.save()

            return JsonResponse({
                "success": True
            })

        except Report.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Report not found"
            }, status=404)

    # =========================
    # LOAD PAGE (GIỮ NGUYÊN)
    # =========================
    store = Store.objects.get(id=store_id)
    slots = TimeSlot.objects.all()

    data = []

    for slot in slots:

        items = ChecklistItem.objects.filter(slot=slot)

        row_items = []

        for item in items:

            report = Report.objects.filter(
                store=store,
                item=item,
                report_date=selected_date
            ).first()

            row_items.append({
                "item": item,
                "report": report
            })

        data.append({
            "slot": slot,
            "items": row_items
        })

    return render(
        request,
        "checklist/admin_store.html",
        {
            "store": store,
            "selected_date": selected_date,
            "data": data
        }
    )

def manage_checklist(request):

    if request.method == "POST":

        slot_id = request.POST.get("slot_id")
        title = request.POST.get("title")

        if title:

            ChecklistItem.objects.create(
                slot_id=slot_id,
                title=title
            )

        return redirect("/manage-checklist/")

    slots = TimeSlot.objects.all()

    return render(
        request,
        "checklist/manage_checklist.html",
        {
            "slots": slots
        }
    )
    

@require_POST
def delete_item(request, item_id):
    item = get_object_or_404(ChecklistItem, id=item_id)
    item.delete()
    return redirect("/manage-checklist/")
    
def admin_day_redirect(request):

    selected_date = request.GET.get(
        "date"
    )

    return redirect(
        f"/admin-day/{selected_date}/"
    )
    
def history(request):

    if "store_id" not in request.session:
        return redirect("/")

    store = Store.objects.get(
        id=request.session["store_id"]
    )

    selected_date = request.GET.get(
        "date"
    )

    slots = TimeSlot.objects.all()

    data = []

    for slot in slots:

        reports = Report.objects.filter(
            store=store,
            item__slot=slot
        )

        if selected_date:

            selected = parse_date(
                selected_date
            )

            if selected:

                reports = reports.filter(
                    report_date=parse_date(
                        selected_date
                    )
                )

        reports = reports.select_related(
            "item"
        ).order_by(
            "-created_at"
        )

        data.append({
            "slot": slot,
            "reports": reports
        })

    dates = Report.objects.filter(
        store=store
    ).dates(
        "created_at",
        "day",
        order="DESC"
    )

    return render(
        request,
        "checklist/history.html",
        {
            "store": store,
            "data": data,
            "dates": dates,
            "selected_date": selected_date
        }
    )
    
def export_excel(request):

    if request.method != "POST":

        return redirect(
            "/admin-dashboard/"
        )

    date_str = request.POST.get(
        "date"
    )

    selected_date = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    ).date()

    store_ids = request.POST.getlist(
        "stores"
    )

    stores = Store.objects.filter(
        id__in=store_ids
    )

    wb = Workbook()

    ws = wb.active

    ws.title = "QC Report"
    
    header_fill = PatternFill(
        "solid",
        fgColor="4472C4"
    )

    header_font = Font(
        bold=True,
        color="FFFFFF"
    )

    center = Alignment(
        horizontal="center",
        vertical="center"
    )

    thin = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    headers = [
        "Khung giờ",
        "Checklist"
    ]

    for store in stores:

        headers.append(
            f"CH {store.code}"
        )

    ws.append(headers)
    
    for cell in ws[1]:

        cell.fill = header_fill

        cell.font = header_font

        cell.alignment = center

        cell.border = thin

    green_fill = PatternFill(
        "solid",
        fgColor="92D050"
    )

    red_fill = PatternFill(
        "solid",
        fgColor="FF6666"
    )

    yellow_fill = PatternFill(
        "solid",
        fgColor="FFD966"
    )

    gray_fill = PatternFill(
        "solid",
        fgColor="D9D9D9"
    )

    current_row = 2

    for slot in TimeSlot.objects.all():

        items = ChecklistItem.objects.filter(
            slot=slot
        )

        slot_start_row = current_row

        first_item = True

        for item in items:

            row = []

            if first_item:

                row.append(
                    slot.name
                )

                first_item = False

            else:

                row.append("")

            row.append(
                item.title
            )

            for store in stores:

                report = Report.objects.filter(
                    store=store,
                    item=item,
                    report_date=selected_date
                ).first()

                if report:

                    if report.status == "pass":

                        value = "Đạt"

                    elif report.status == "fail":

                        value = "Không đạt"

                    else:

                        value = "Chưa đánh giá"

                else:

                    value = "Chưa báo cáo"

                row.append(value)

            ws.append(row)

            current_row += 1

        slot_end_row = current_row - 1

        if slot_end_row > slot_start_row:

            ws.merge_cells(
                start_row=slot_start_row,
                end_row=slot_end_row,
                start_column=1,
                end_column=1
            )

        slot_cell = ws.cell(
            row=slot_start_row,
            column=1
        )

        slot_cell.fill = PatternFill(
            "solid",
            fgColor="D9EAD3"
        )

        slot_cell.font = Font(
            bold=True
        )

        slot_cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

        slot_cell.border = thin

    for row in ws.iter_rows(
        min_row=2
    ):

        for cell in row:

            if cell.value == "Đạt":

                cell.fill = green_fill

            elif cell.value == "Không đạt":

                cell.fill = red_fill

            elif cell.value == "Chưa đánh giá":

                cell.fill = yellow_fill

            elif cell.value == "Chưa báo cáo":

                cell.fill = gray_fill

    response = HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="QC_{selected_date}.xlsx"'
    )
    
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 40

    for col in range(
        3,
        ws.max_column + 1
    ):

        letter = ws.cell(
            row=1,
            column=col
        ).column_letter

        ws.column_dimensions[
            letter
        ].width = 18
    
    for row in ws.iter_rows():

        ws.row_dimensions[
            row[0].row
        ].height = 30
    
    for row in ws.iter_rows():

        for cell in row:

            cell.border = thin

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )
            
    ws.auto_filter.ref = ws.dimensions
    
    wb.save(response)

    return response