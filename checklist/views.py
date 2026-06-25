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
from django.contrib.auth import authenticate, login
from .models import Audit, AuditIssue
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef  
from django.db.models import Count
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import *
from django.db.models import Count


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

    if not request.user.is_staff:
        return redirect("/")    
    today = timezone.now().date()

    return render(
        request,
        "checklist/admin_dashboard.html",
        {
            "today": today
        }
    )
    
def admin_day(request, date):

    if not request.user.is_staff:
        return redirect("/")
    
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

    if not request.user.is_staff:
        return redirect("/")
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

    if not request.user.is_staff:
        return redirect("/")
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
    if not request.user.is_staff:
        return redirect("/")
    
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

    # ===============================
    # THỐNG KÊ
    # ===============================

    stat_start_row = ws.max_row + 2

    blue_fill = PatternFill("solid", fgColor="5B9BD5")
    orange_fill = PatternFill("solid", fgColor="F4B183")
    white_font = Font(bold=True, color="FFFFFF")
    bold_font = Font(bold=True)

    center = Alignment(horizontal="center", vertical="center")

    # ===== ROW 1: TỶ LỆ ĐẠT =====
    ws.merge_cells(
        start_row=stat_start_row,
        start_column=1,
        end_row=stat_start_row,
        end_column=2
    )

    cell = ws.cell(row=stat_start_row, column=1)
    cell.value = "THỐNG KÊ TỶ LỆ ĐẠT"
    cell.fill = blue_fill
    cell.font = white_font
    cell.alignment = center

    # ===== ROW 2: LỖI =====
    ws.merge_cells(
        start_row=stat_start_row + 1,
        start_column=1,
        end_row=stat_start_row + 1,
        end_column=2
    )

    cell2 = ws.cell(row=stat_start_row + 1, column=1)
    cell2.value = "THỐNG KÊ LỖI / CHƯA BÁO CÁO"
    cell2.fill = orange_fill
    cell2.font = bold_font
    cell2.alignment = center

    # ===== FORMULA =====
    data_start = 2
    data_end = stat_start_row - 1

    for col in range(3, ws.max_column + 1):

        letter = ws.cell(row=1, column=col).column_letter

        # tỷ lệ đạt
        rate_formula = (
            f'=COUNTIF({letter}{data_start}:{letter}{data_end},"Đạt")'
            f'/COUNTA({letter}{data_start}:{letter}{data_end})'
        )

        c = ws.cell(row=stat_start_row, column=col)
        c.value = rate_formula
        c.number_format = "0.00%"
        c.fill = blue_fill
        c.font = white_font
        c.alignment = center

    # lỗi
        error_formula = (
            f'=COUNTA({letter}{data_start}:{letter}{data_end})'
            f'-COUNTIF({letter}{data_start}:{letter}{data_end},"Đạt")'
        )

        c2 = ws.cell(row=stat_start_row + 1, column=col)
        c2.value = error_formula
        c2.fill = orange_fill
        c2.font = bold_font
        c2.alignment = center

    wb.save(response)

    return response

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        # ======================
        # ADMIN DJANGO
        # ======================
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_staff:

            login(request, user)

            today = timezone.localdate()

            return redirect(
                f"/admin-day/{today}/"
            )

        # ======================
        # STORE
        # ======================
        store = Store.objects.filter(
            code=username,
            password=password
        ).first()

        if store:

            request.session["store_id"] = store.id

            return redirect("/dashboard/")

        return render(
            request,
            "login.html",
            {
                "error": "Sai tài khoản hoặc mật khẩu"
            }
        )

    return render(
        request,
        "login.html"
    )
    
def audit_create(request):

    # lấy danh sách store cho form
    stores = Store.objects.all()


    if request.method == "POST":

        store_id = request.POST.get("store_id")

        audit = Audit.objects.create(
            store_id=store_id,
            user=request.user,
            score=200
        )

        for category in AuditCategory.objects.filter(is_active=True):

            for item in category.items.filter(is_active=True):

                status = request.POST.get(f"status_{item.id}", "pass")

                note = request.POST.get(f"note_{item.id}", "")
                
                issue = AuditIssue.objects.create(
                    audit=audit,
                    item=item,
                    category=item.category,
                    status=status,
                    note=note,  
                    deduct_score=item.score if status == "fail" else 0
                )

                if status == "fail":

                    file = request.FILES.get(f"image_{item.id}")

                    if file:
                        upload = cloudinary.uploader.upload(file)

                        AuditIssueImage.objects.create(
                            issue=issue,
                            image=upload["secure_url"]
                        )

        update_audit_score(audit)

        return redirect(f"/audit/{audit.id}/")

    categories = AuditCategory.objects.prefetch_related("items").all()

    return render(request, "checklist/audit_create.html", {
        "categories": categories,
        "stores": stores
    })
    
def audit_detail(request, id):

    if not request.user.is_staff:
        return redirect("/")

    audit = get_object_or_404(Audit, id=id)

    # 👉 lấy issue đầu tiên theo status
    first_issue = audit.issues.order_by("status").first()

    return render(
        request,
        "checklist/audit_detail.html",
        {
            "audit": audit,
            "first_issue": first_issue
        }
    )
    
def audit_list(request):

    if not request.user.is_staff:
        return redirect("/")

    audits = Audit.objects.all().order_by("-created_at")

    search = request.GET.get("search")

    if search:
        audits = audits.filter(store__code__icontains=search)

    # ✔ CHECK có issue pending hay không
    audits = audits.annotate(

        is_pending=Exists(
            AuditIssue.objects.filter(
                audit_id=OuterRef("id"),
                status="pending"
            )
        ),

        has_fail=Exists(
            AuditIssue.objects.filter(
                audit_id=OuterRef("id"),
                status="fail"
            )
        ),

        need_review=Exists(
            AuditIssue.objects.filter(
                audit_id=OuterRef("id"),
                status="fixed"
            )
        )
    )



    paginator = Paginator(audits, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "checklist/audit_list.html", {
        "page_obj": page_obj,
        "search": search
    })
    
def delete_audit(request, id):

    audit = get_object_or_404(Audit, id=id)

    if request.method == "POST":
        audit.delete()
        messages.success(request, "Đã xoá audit thành công")
        return redirect("audit_list")

    return redirect("audit_list")

def staff_dashboard(request):

    if "store_id" not in request.session:
        return redirect("/")

    store = Store.objects.get(id=request.session["store_id"])

    audit_id = request.GET.get("audit_id")

    if audit_id:
        audit = get_object_or_404(Audit, id=audit_id, store=store)
    else:
        audit = Audit.objects.filter(store=store).order_by("-created_at").first()

    return render(request, "checklist/staff_dashboard.html", {
        "audit": audit
    })
    
def staff_fix_issue(request,id):

    store=Store.objects.get(
        id=request.session["store_id"]
    )

    issue=get_object_or_404(
        AuditIssue,
        id=id,
        audit__store=store
    )

    fix_file=request.FILES.get(
        "fix_image"
    )

    if not fix_file:

        return JsonResponse({
            "success":False
        })

    upload=cloudinary.uploader.upload(
        fix_file
    )

    AuditFixImage.objects.create(
        issue=issue,
        image=upload["secure_url"]
    )

    issue.status="fixed"
    issue.save()

    return JsonResponse({
        "success":True
    })
        
def update_audit_score(audit):

    score = 200

    for issue in audit.issues.all():

        if issue.status == "fail":
            score -= issue.deduct_score

    audit.score = max(score, 0)
    audit.save()
    
def store_audit_history(request, store_id):

    audits = Audit.objects.filter(store_id=store_id).order_by("-created_at")

    return render(request, "checklist/store_history.html", {
        "audits": audits
    })
    
def staff_dashboard_by_audit(request, audit_id):

    if "store_id" not in request.session:
        return redirect("/")

    store = Store.objects.get(id=request.session["store_id"])

    audit = get_object_or_404(
        Audit,
        id=audit_id,
        store=store
    )

    return render(
        request,
        "checklist/staff_dashboard.html",
        {
            "audit": audit
        }
    )
    
def review_issue(request,audit_id,issue_id):

    issue=get_object_or_404(
        AuditIssue,
        id=issue_id
    )

    if request.method=="POST":

        status=request.POST.get("status")

        issue.status=status

        issue.save()

        update_audit_score(
            issue.audit
        )

    return redirect(
        f"/audit/{audit_id}/"
    )

def audit_review_issue(request, audit_id, issue_id):

    if request.method != "POST":
        return JsonResponse({"success": False})

    issue = AuditIssue.objects.get(id=issue_id, audit_id=audit_id)

    status = request.POST.get("status")
    note = request.POST.get("note")

    issue.status = status
    issue.note = note
    issue.reviewed_at = timezone.now()
    issue.save()

    return JsonResponse({"success": True})

def kpi_dashboard(request):

    if not request.user.is_staff:
        return redirect("/")

    stores = Store.objects.all().order_by("code")

    selected_stores = request.GET.getlist("stores")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    reports = Report.objects.all()

    if start_date:
        reports = reports.filter(
            report_date__gte=start_date
        )

    if end_date:
        reports = reports.filter(
            report_date__lte=end_date
        )

    if selected_stores:
        reports = reports.filter(
            store_id__in=selected_stores
        )

    total_reports = reports.count()

    pass_count = reports.filter(
        status="pass"
    ).count()

    fail_count = reports.filter(
        status="fail"
    ).count()

    pending_count = reports.filter(
        status="pending"
    ).count()

    if total_reports > 0:
        pass_percent = round(
            pass_count * 100 / total_reports,
            1
        )
    else:
        pass_percent = 0

    top_stores = (
        reports
        .values(
            "store__code"
        )
        .annotate(
            total=Count("id")
        )
        .order_by(
            "-total"
        )[:10]
    )

    top_fail_items = (
        reports.filter(
            status="fail"
        )
        .values(
            "item__title"
        )
        .annotate(
            total=Count("id")
        )
        .order_by(
            "-total"
        )[:10]
    )

    return render(
        request,
        "checklist/kpi_dashboard.html",
        {
            "stores": stores,

            "selected_stores": list(
                map(int, selected_stores)
            ) if selected_stores else [],

            "start_date": start_date,
            "end_date": end_date,

            "total_reports": total_reports,

            "pass_count": pass_count,

            "fail_count": fail_count,

            "pending_count": pending_count,

            "pass_percent": pass_percent,

            "top_stores": top_stores,

            "top_fail_items": top_fail_items
        }
    )

from openpyxl.styles import PatternFill, Font, Border, Side, Alignment

HEADER_FILL = PatternFill("solid", fgColor="E60012")

HEADER_FONT = Font(color="FFFFFF", bold=True, size=12)

CENTER = Alignment(horizontal="center", vertical="center")

THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin")
)

GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")
RED_FILL = PatternFill("solid", fgColor="FFC7CE")
YELLOW_FILL = PatternFill("solid", fgColor="FFEB9C")

def export_kpi_excel(request):

    if not request.user.is_staff:
        return redirect("/")

    start_date=request.GET.get("start_date")
    end_date=request.GET.get("end_date")

    reports=Report.objects.all()

    if start_date:
        reports=reports.filter(
            report_date__gte=start_date
        )

    if end_date:
        reports=reports.filter(
            report_date__lte=end_date
        )

    wb=Workbook()

    ws = wb.active
    ws.title = "Tong Quan"

    ws.append(["Chỉ số", "Giá trị"])

    ws.append(["Từ ngày", start_date])
    ws.append(["Đến ngày", end_date])

    total = reports.count()

    passed = reports.filter(status="pass").count()
    failed = reports.filter(status="fail").count()
    pending = reports.filter(status="pending").count()

    percent = 0

    if total > 0:
        percent = round(passed * 100 / total, 1)

    ws.append(["Tổng checklist", total])
    ws.append(["Đạt", passed])
    ws.append(["Không đạt", failed])
    ws.append(["Pending", pending])
    ws.append(["Tỷ lệ đạt (%)", percent])

    format_sheet(ws)

    
    # SHEET 2
    ws2 = wb.create_sheet("Theo CH")

    ws2.append([
        "Cửa hàng",
        "Tổng lỗi",
        "Checklist đạt TB/ngày",
        "% đạt"
    ])

    # số ngày trong khoảng admin chọn
    days_count = reports.values(
        "report_date"
    ).distinct().count()

    for store in Store.objects.all():

        rs = reports.filter(
            store=store
        )

        total_store = rs.count()

        # số checklist đạt
        pass_store = rs.filter(
            status="pass"
        ).count()

        # số lỗi
        fail_store = rs.filter(
            status="fail"
        ).count()

        # checklist đạt trung bình mỗi ngày
        avg_pass = 0

        if days_count > 0:

            avg_pass = round(
                pass_store / days_count,
                1
            )

        # % đạt của cửa hàng
        percent_store = 0

        if total_store > 0:

            percent_store = round(
                pass_store * 100 / total_store,
                1
            )

        ws2.append([
            store.code,
            fail_store,
            avg_pass,
            percent_store
        ])

    # tô màu cột % đạt
    for row in ws2.iter_rows(min_row=2):

        percent_cell = row[3]

        if percent_cell.value >= 95:

            percent_cell.fill = GREEN_FILL

        elif percent_cell.value >= 80:

            percent_cell.fill = YELLOW_FILL

        else:

            percent_cell.fill = RED_FILL

    format_sheet(ws2)
    
    #SHEET 3
    ws3 = wb.create_sheet("Top Loi")

    ws3.append([
        "CH",
        "Checklist lỗi",
        "Số lần"
    ])

    top_fail = (
        reports
        .filter(status="fail")
        .values(
            "store__code",
            "item__title"
        )
        .annotate(
            total=Count("id")
        )   
        .order_by("-total")
    )

    for row in top_fail:

        ws3.append([
            row["store__code"],
            row["item__title"],
            row["total"]
        ])

    format_sheet(ws3)
    
    #SHEET 4
    ws4 = wb.create_sheet("Theo Ngay")

    ws4.append([
        "Ngày",
        "% đạt hàng ngày",
        "CH tốt nhất",
        "Checklist lỗi nhiều nhất"
    ])

    days = (
        reports
        .values("report_date")
        .distinct()
        .order_by("report_date")
    )

    for d in days:

        date_value = d["report_date"]

        day_reports = reports.filter(
            report_date=date_value
        )

        total_day = day_reports.count()

        pass_day = day_reports.filter(
            status="pass"
        ).count()

        percent_day = 0

        if total_day > 0:

            percent_day = round(
                pass_day * 100 / total_day,
                1
            )

        # CH tốt nhất

        best_store = ""

        ranking = []

        for store in Store.objects.all():

            rs = day_reports.filter(
                store=store
            )

            total_store = rs.count()

            pass_store = rs.filter(
                status="pass"
            ).count()

            p = 0

            if total_store > 0:

                p = pass_store * 100 / total_store

            ranking.append(
                (p, store.code)
            )

        if ranking:

            best_store = max(ranking)[1]

        # lỗi nhiều nhất

        top_error = (
            day_reports
            .filter(status="fail")
            .values("item__title")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )

        error_name = ""

        if top_error:

            error_name = top_error["item__title"]

        ws4.append([
            date_value,
            percent_day,
            best_store,
            error_name
        ])

    format_sheet(ws4)
    
    response=HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response[
        "Content-Disposition"
    ]=(
        'attachment; filename="KPI_Report.xlsx"'
    )
    
    ws5 = wb.create_sheet("Leaderboard")

    red_fill=PatternFill(
        "solid",
        fgColor="E60012"
    )

    white_font=Font(
        bold=True,
        color="FFFFFF"
    )

    thin=Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    
    ws5.append([
        "Hạng",
        "Cửa hàng",
        "% đạt",
        "Tổng checklist"
    ])

    ranking=[]

    for store in Store.objects.all():

        rs=reports.filter(
            store=store
        )

        total_store=rs.count()

        pass_store=rs.filter(
            status="pass"
        ).count()

        percent_store=0

        if total_store>0:

            percent_store=round(
                pass_store * 100 / total_store,
                1
            )

        ranking.append({
            "code":store.code,
            "percent":percent_store,
            "total":total_store
        })
    
    ranking.sort(
        key=lambda x:x["percent"],
        reverse=True
    )
    
    rank = 1

    for row in ranking:

        ws5.append([
            rank,
            row["code"],
            row["percent"],
            row["total"]
        ])

        current_row = ws5.max_row

        if rank == 1:

            fill = PatternFill(
                "solid",
                fgColor="FFD700"
            )

        elif rank == 2:

            fill = PatternFill(
                "solid",
                fgColor="C0C0C0"
            )

        elif rank == 3:

            fill = PatternFill(
                "solid",
                fgColor="CD7F32"
            )

        else:

            fill = None

        if fill:

            for cell in ws5[current_row]:

                cell.fill = fill

        rank += 1

    format_sheet(ws5)  
    
    auto_fit_columns(ws)
    auto_fit_columns(ws2)
    auto_fit_columns(ws3)
    auto_fit_columns(ws4)
    auto_fit_columns(ws5)
    
    wb.save(response)
    return response

def format_sheet(sheet):

    sheet.freeze_panes = "A2"

    # style từng ô
    for row in sheet.iter_rows():

        for cell in row:

            if isinstance(cell.value, (int, float)):

                cell.alignment = Alignment(
                    horizontal="right",
                    vertical="center"
                )

            else:

                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center"
                )

            cell.border = THIN

    # header
    for cell in sheet[1]:

        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    # filter
    sheet.auto_filter.ref = sheet.dimensions

    # auto width
    for col in sheet.columns:

        max_len = max(
            len(str(c.value))
            if c.value is not None
            else 0
            for c in col
        )

        sheet.column_dimensions[
            col[0].column_letter
        ].width = max_len + 5

    # format số
    for row in sheet.iter_rows(min_row=2):

        for cell in row:

            header = str(
                sheet.cell(
                    row=1,
                    column=cell.column
                ).value or ""
            ).lower()

            # chỉ format các cột % đạt
            if header == "% đạt":

                if isinstance(cell.value, (int, float)):

                    cell.number_format = "0.0"

            # checklist TB/ngày
            elif "tb/ngày" in header:

                if isinstance(cell.value, (int, float)):

                    cell.number_format = "0.0"
                    
def auto_fit_columns(sheet):

    for col in sheet.columns:

        max_length = 0
        column = col[0].column_letter

        for cell in col:

            if cell.value is None:
                continue

            value = str(cell.value)

            # xử lý % và số dài
            length = len(value)

            if length > max_length:
                max_length = length

        adjusted_width = max_length + 4

        # giới hạn cho đẹp UI
        if adjusted_width > 40:
            adjusted_width = 40

        sheet.column_dimensions[column].width = adjusted_width
        

        