from django.urls import path

from .views import (
    admin_dashboard,
    admin_item_edit,
    admin_item_list,
    admin_user_edit,
    admin_user_list,
    item_detail,
    item_list,
    report_found_item,
    report_lost_item,
)

urlpatterns = [
    path("", item_list, name="item_list"),
    path("dashboard/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/items/", admin_item_list, name="admin_item_list"),
    path("dashboard/items/<int:pk>/edit/", admin_item_edit, name="admin_item_edit"),
    path("dashboard/users/", admin_user_list, name="admin_user_list"),
    path("dashboard/users/<int:pk>/edit/", admin_user_edit, name="admin_user_edit"),
    path("items/<int:pk>/", item_detail, name="item_detail"),
    path("items/lost/new/", report_lost_item, name="report_lost_item"),
    path("items/found/new/", report_found_item, name="report_found_item"),
]
