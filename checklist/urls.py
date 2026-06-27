from django.urls import path
from . import views
from checklist.views import *

urlpatterns = [
    
    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),
    
    path(
    'upload/<int:item_id>/',
    views.upload_report,
    name='upload_report'
    ),
    
    path(
    'admin-dashboard/',
    views.admin_dashboard,
    name='admin_dashboard'
    ),
    
    path(
    'admin-day/<str:date>/',
    views.admin_day,
    name='admin_day'
    ),
    
    path(
    'admin-store/<int:store_id>/<str:date>/',
    views.admin_store,
    name='admin_store'
    ),
    
    path(
    "manage-checklist/",
    views.manage_checklist,
    name="manage_checklist"
    ),
    
    path(
    "delete-item/<int:item_id>/",
    views.delete_item,
    name="delete_item"
    ),
    
    path(
    "admin-day/",
    views.admin_day_redirect,
    name="admin_day_redirect"
    ),   
    
    path(
    "history/",
    views.history,
    name="history"
    ),
    
    path(
    "export-excel/",
    views.export_excel,
    name="export_excel"
    ),
    
    path(
    "audit-create/",
    views.audit_create,
    name="audit_create"
    ),
    
    path("audit/<int:id>/", 
    views.audit_detail,
    name="audit_detail"
    ),
    
    path(
    "audits/",
    views.audit_list,
    name="audit_list"
    ),
    
    path(
    "audit-delete/<int:id>/",
    views.delete_audit,
    name="delete_audit"
    ),
    
    path("staff/",
    views.staff_dashboard,
    name="staff_dashboard"
    ),
    
    
    path(
    "audit/<int:audit_id>/review/<int:issue_id>/",
    views.audit_review_issue,
    name="audit_review_issue"
    ),
    
    path("staff/",
    views.staff_dashboard,
    name="staff_dashboard"
    ),
    path("staff/issue/<int:id>/fix/",
    views.staff_fix_issue,
    name="staff_fix"
    ),
    
    path(
    "kpi-dashboard/",
    views.kpi_dashboard,
    name="kpi_dashboard"
    ),
    
    path(
    "export-kpi/",
    views.export_kpi_excel,
    name="export_kpi_excel"
    ),
    
    path(
        "store/<int:store_id>/audits/", 
        views.store_audit_history, 
        name="store_audit_history"
    ),
    
    path(
        "staff/audit/<int:audit_id>/",
        views.staff_dashboard_by_audit,
        name="staff_dashboard_by_audit"
    ),
    
    path(
        "export-kpi-auditqc/",
        views.export_kpi_auditqc_excel,
        name="export_kpi_auditqc_excel"
    ),
    
    path(
        "export-audit/<int:audit_id>/",
        views.export_audit_excel,
        name="export_audit_excel"
    ),
]
    