from django.urls import path
from . import views

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
]