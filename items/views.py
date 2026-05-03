from functools import wraps

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.forms import AdminProfileForm, AdminUserForm
from accounts.models import Profile

from .forms import AdminItemForm, ItemForm
from .models import Item


def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Admin access is restricted to staff users.")
            return redirect("item_list")
        return view_func(request, *args, **kwargs)

    return wrapped_view


def _get_profile_or_none(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def _get_or_create_profile(user):
    profile = _get_profile_or_none(user)
    if profile is not None:
        return profile

    return Profile.objects.create(
        user=user,
        role=Profile.Role.STAFF if user.is_staff else Profile.Role.STUDENT,
    )


def item_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()

    items = Item.objects.select_related("reported_by")

    if query:
        items = items.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
        )

    if status:
        items = items.filter(status=status)

    if category:
        items = items.filter(category=category)

    context = {
        "items": items,
        "query": query,
        "selected_status": status,
        "selected_category": category,
        "status_choices": Item.Status.choices,
        "category_choices": Item.Category.choices,
    }
    return render(request, "items/item_list.html", context)


def item_detail(request, pk):
    item = get_object_or_404(Item.objects.select_related("reported_by"), pk=pk)
    return render(request, "items/item_detail.html", {"item": item})


@login_required
def report_lost_item(request):
    return _save_item_report(request, Item.ReportType.LOST, Item.Status.LOST)


@login_required
def report_found_item(request):
    return _save_item_report(request, Item.ReportType.FOUND, Item.Status.FOUND)


def _save_item_report(request, report_type, status):
    label = "Lost" if report_type == Item.ReportType.LOST else "Found"

    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.report_type = report_type
            item.status = status
            item.reported_by = request.user
            item.save()
            messages.success(request, f"{label} item report submitted successfully.")
            return redirect("item_detail", pk=item.pk)
    else:
        form = ItemForm()

    return render(
        request,
        "items/item_form.html",
        {
            "form": form,
            "page_title": f"Report {label} Item",
            "submit_label": f"Save {label} Report",
        },
    )


@staff_required
def admin_dashboard(request):
    recent_items = Item.objects.select_related("reported_by")[:6]
    recent_users = User.objects.order_by("-date_joined")[:6]
    recent_user_rows = [
        {
            "user": user,
            "profile": _get_profile_or_none(user),
        }
        for user in recent_users
    ]

    context = {
        "dashboard_section": "overview",
        "total_items": Item.objects.count(),
        "lost_items": Item.objects.filter(report_type=Item.ReportType.LOST).count(),
        "found_items": Item.objects.filter(report_type=Item.ReportType.FOUND).count(),
        "claimed_items": Item.objects.filter(status=Item.Status.CLAIMED).count(),
        "returned_items": Item.objects.filter(status=Item.Status.RETURNED).count(),
        "total_users": User.objects.count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
        "student_profiles": Profile.objects.filter(role=Profile.Role.STUDENT).count(),
        "recent_items": recent_items,
        "recent_user_rows": recent_user_rows,
    }
    return render(request, "dashboard/overview.html", context)


@staff_required
def admin_item_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    report_type = request.GET.get("type", "").strip()

    items = Item.objects.select_related("reported_by")

    if query:
        items = items.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
            | Q(reported_by__username__icontains=query)
        )

    if status:
        items = items.filter(status=status)

    if category:
        items = items.filter(category=category)

    if report_type:
        items = items.filter(report_type=report_type)

    context = {
        "dashboard_section": "items",
        "items": items,
        "query": query,
        "selected_status": status,
        "selected_category": category,
        "selected_type": report_type,
        "status_choices": Item.Status.choices,
        "category_choices": Item.Category.choices,
        "report_type_choices": Item.ReportType.choices,
    }
    return render(request, "dashboard/items.html", context)


@staff_required
def admin_item_edit(request, pk):
    item = get_object_or_404(Item.objects.select_related("reported_by"), pk=pk)

    if request.method == "POST":
        form = AdminItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect("admin_item_list")
    else:
        form = AdminItemForm(instance=item)

    return render(
        request,
        "dashboard/item_form.html",
        {
            "dashboard_section": "items",
            "form": form,
            "item": item,
        },
    )


@staff_required
def admin_user_list(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    access = request.GET.get("access", "").strip()

    users = User.objects.order_by("-date_joined")

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(profile__phone_number__icontains=query)
            | Q(profile__identification_number__icontains=query)
        )

    if role:
        users = users.filter(profile__role=role)

    if access == "staff":
        users = users.filter(is_staff=True)
    elif access == "inactive":
        users = users.filter(is_active=False)

    user_rows = [
        {
            "user": user,
            "profile": _get_profile_or_none(user),
        }
        for user in users
    ]

    return render(
        request,
        "dashboard/users.html",
        {
            "dashboard_section": "users",
            "user_rows": user_rows,
            "query": query,
            "selected_role": role,
            "selected_access": access,
            "role_choices": Profile.Role.choices,
        },
    )


@staff_required
def admin_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = _get_or_create_profile(user)

    if request.method == "POST":
        user_form = AdminUserForm(request.POST, instance=user)
        profile_form = AdminProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "User updated successfully.")
            return redirect("admin_user_list")
    else:
        user_form = AdminUserForm(instance=user)
        profile_form = AdminProfileForm(instance=profile)

    return render(
        request,
        "dashboard/user_form.html",
        {
            "dashboard_section": "users",
            "managed_user": user,
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )
