from functools import wraps
import mimetypes

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_POST

from accounts.forms import AdminProfileForm, AdminUserForm
from accounts.models import Profile

from .forms import AdminItemForm, ClaimForm, ItemForm, MessageForm
from .models import Claim, Conversation, Item, Message, Notification
from .notifications import notify_claim_reviewed, notify_claim_submitted


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


def _missing_image_response(item):
    label = "Image unavailable"
    if item.report_type == Item.ReportType.FOUND:
        label = "Found item photo unavailable"
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="675" viewBox="0 0 900 675">
  <rect width="900" height="675" fill="#f6fafb"/>
  <rect x="120" y="105" width="660" height="465" rx="32" fill="#e4edf2"/>
  <circle cx="315" cy="255" r="54" fill="#c7d8e0"/>
  <path d="M168 506l180-176 110 108 85-84 189 152z" fill="#c7d8e0"/>
  <text x="450" y="612" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#597180">{escape(label)}</text>
</svg>
"""
    return HttpResponse(svg, content_type="image/svg+xml")


def item_image(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if (
        item.report_type == Item.ReportType.LOST
        and not item.can_user_view_private_details(request.user)
    ):
        raise Http404

    if item.image_data:
        response = HttpResponse(
            bytes(item.image_data),
            content_type=item.image_content_type or "application/octet-stream",
        )
        if item.image_filename:
            filename = item.image_filename.replace('"', "")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

    if item.image:
        content_type = (
            mimetypes.guess_type(item.image.name)[0]
            or "application/octet-stream"
        )
        try:
            return FileResponse(item.image.open("rb"), content_type=content_type)
        except (FileNotFoundError, OSError, ValueError):
            return _missing_image_response(item)

    raise Http404


def _get_or_create_profile(user):
    profile = _get_profile_or_none(user)
    if profile is not None:
        return profile

    return Profile.objects.create(
        user=user,
        role=Profile.Role.STAFF if user.is_staff else Profile.Role.STUDENT,
    )


def _visible_items_for_user(user):
    items = Item.objects.select_related("reported_by")

    if not user.is_authenticated:
        return items.filter(report_type=Item.ReportType.FOUND)

    if user.is_staff:
        return items

    return items.filter(
        Q(report_type=Item.ReportType.FOUND)
        | Q(reported_by=user)
        | Q(conversations__participant=user)
        | Q(claims__claimant=user)
    ).distinct()


def item_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    report_type = (
        request.GET.get("type", "").strip()
        or request.GET.get("report_type", "").strip()
    )
    can_filter_private_details = request.user.is_authenticated and request.user.is_staff

    items = _visible_items_for_user(request.user)

    if query:
        normalized_query = query.replace(" ", "_")
        items = items.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
            | Q(category__icontains=query)
            | Q(category__icontains=normalized_query)
            | Q(status__icontains=query)
            | Q(report_type__icontains=query)
        )

    if status:
        items = items.filter(status=status)

    if category:
        items = items.filter(category=category)

    if report_type:
        items = items.filter(report_type=report_type)

    items = items.annotate(
        pending_claim_count=Count(
            "claims",
            filter=Q(claims__status=Claim.Status.PENDING),
            distinct=True,
        )
    )
    items = list(items)
    for item in items:
        item.viewer_can_view_private_details = item.can_user_view_private_details(
            request.user
        )

    context = {
        "items": items,
        "query": query,
        "selected_status": status,
        "selected_category": category,
        "selected_report_type": report_type,
        "status_choices": Item.Status.choices,
        "category_choices": Item.Category.choices,
        "report_type_choices": Item.ReportType.choices,
        "can_filter_private_details": can_filter_private_details,
    }
    return render(request, "items/item_list.html", context)


@login_required
def notification_list(request):
    notifications = list(
        Notification.objects.filter(recipient=request.user)
        .select_related(
            "actor",
            "item",
            "item__reported_by",
            "claim",
            "claim__item",
            "claim__item__reported_by",
            "claim__claimant",
        )[:60]
    )

    for notification in notifications:
        item = notification.item or (
            notification.claim.item if notification.claim else None
        )
        notification.display_item = item
        notification.viewer_can_view_item_private_details = bool(
            item and item.can_user_view_private_details(request.user)
        )

    return render(
        request,
        "items/notification_list.html",
        {"notifications": notifications},
    )


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )
    notification.mark_read()

    if request.POST.get("open_item") == "1":
        item = notification.item or (
            notification.claim.item if notification.claim else None
        )
        if item is not None:
            return redirect("item_detail", pk=item.pk)

    return redirect("notification_list")


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )
    messages.success(request, "All alerts marked as read.")
    return redirect("notification_list")


def item_detail(request, pk):
    item = get_object_or_404(_visible_items_for_user(request.user), pk=pk)
    can_view_private_details = item.can_user_view_private_details(request.user)
    conversation = None
    reporter_conversation_count = 0
    claim = None
    claim_form = None
    claim_requests = []
    if (
        request.user.is_authenticated
        and item.reported_by != request.user
        and not request.user.is_staff
    ):
        conversation = item.conversations.filter(participant=request.user).first()
        claim = item.claims.filter(claimant=request.user).first()
        if item.report_type == Item.ReportType.FOUND and claim is None:
            claim_form = ClaimForm()
    elif request.user.is_authenticated and item.reported_by == request.user:
        reporter_conversation_count = item.conversations.count()
        claim_requests = item.claims.select_related(
            "claimant",
            "claimant__profile",
            "reviewed_by",
        )

    if request.user.is_authenticated and request.user.is_staff:
        claim_requests = item.claims.select_related(
            "claimant",
            "claimant__profile",
            "reviewed_by",
        )

    return render(
        request,
        "items/item_detail.html",
        {
            "item": item,
            "conversation": conversation,
            "reporter_conversation_count": reporter_conversation_count,
            "claim": claim,
            "claim_form": claim_form,
            "claim_requests": claim_requests,
            "can_view_private_details": can_view_private_details,
        },
    )


@login_required
@require_POST
def start_conversation(request, pk):
    item = get_object_or_404(_visible_items_for_user(request.user), pk=pk)

    if item.reported_by == request.user:
        messages.info(request, "Use Messages to reply to people about your item.")
        return redirect("conversation_list")

    if (
        item.report_type == Item.ReportType.FOUND
        and not item.can_user_view_private_details(request.user)
    ):
        messages.info(request, "Submit a claim to contact the reporter about this found item.")
        return redirect("item_detail", pk=item.pk)

    conversation, _ = Conversation.objects.get_or_create(
        item=item,
        participant=request.user,
    )
    return redirect("conversation_detail", pk=conversation.pk)


@login_required
@require_POST
def submit_claim(request, pk):
    item = get_object_or_404(_visible_items_for_user(request.user), pk=pk)

    if item.report_type != Item.ReportType.FOUND:
        messages.error(request, "Only found items can be claimed.")
        return redirect("item_detail", pk=item.pk)

    if item.reported_by == request.user:
        messages.info(request, "You cannot claim an item you reported.")
        return redirect("item_detail", pk=item.pk)

    if item.status in (Item.Status.CLAIMED, Item.Status.RETURNED):
        messages.error(request, "This item is no longer available to claim.")
        return redirect("item_detail", pk=item.pk)

    if item.claims.filter(claimant=request.user).exists():
        messages.info(request, "You already submitted a claim for this item.")
        return redirect("item_detail", pk=item.pk)

    form = ClaimForm(request.POST)
    if form.is_valid():
        verification_answer = form.cleaned_data.get("verification_answer", "")
        claim = Claim.objects.create(
            item=item,
            claimant=request.user,
            proof_details=form.cleaned_data["proof_details"],
            answer_matches=item.check_verification_answer(verification_answer),
        )
        notify_claim_submitted(claim, request.user)
        messages.success(request, "Claim submitted. The reporter or staff will review it.")
    else:
        messages.error(request, "Please add the ownership details required for your claim.")

    return redirect("item_detail", pk=item.pk)


@login_required
@require_POST
def review_claim(request, pk, decision):
    claim = get_object_or_404(
        Claim.objects.select_related("item", "item__reported_by", "claimant"),
        pk=pk,
    )

    if not request.user.is_staff and claim.item.reported_by != request.user:
        messages.error(request, "Only the reporter or staff can review this claim.")
        return redirect("item_detail", pk=claim.item.pk)

    if decision not in (Claim.Status.APPROVED, Claim.Status.REJECTED):
        messages.error(request, "Unknown claim decision.")
        return redirect("item_detail", pk=claim.item.pk)

    claim.review(
        reviewer=request.user,
        next_status=decision,
        note=request.POST.get("review_note", "").strip(),
    )
    claim.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "updated_at",
        ]
    )
    notify_claim_reviewed(claim, request.user)

    if decision == Claim.Status.APPROVED:
        item = claim.item
        item.status = Item.Status.CLAIMED
        item.save(update_fields=["status", "updated_at"])
        other_pending_claims = list(
            Claim.objects.filter(
                item=item,
                status=Claim.Status.PENDING,
            )
            .exclude(pk=claim.pk)
            .select_related("item", "item__reported_by", "claimant")
        )
        Claim.objects.filter(
            item=item,
            status=Claim.Status.PENDING,
        ).exclude(pk=claim.pk).update(
            status=Claim.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=claim.reviewed_at,
            review_note="Another claim was approved.",
        )
        for other_claim in other_pending_claims:
            other_claim.status = Claim.Status.REJECTED
            other_claim.reviewed_by = request.user
            other_claim.reviewed_at = claim.reviewed_at
            other_claim.review_note = "Another claim was approved."
            notify_claim_reviewed(other_claim, request.user, auto_rejected=True)
        messages.success(request, "Claim approved and item marked as claimed.")
    else:
        messages.success(request, "Claim rejected.")

    return redirect("item_detail", pk=claim.item.pk)


@login_required
def conversation_list(request):
    conversations = (
        Conversation.objects.filter(
            Q(participant=request.user) | Q(item__reported_by=request.user)
        )
        .select_related("item", "item__reported_by", "participant")
        .prefetch_related("messages")
    )

    return render(
        request,
        "items/conversation_list.html",
        {"conversations": conversations},
    )


def _user_can_access_conversation(user, conversation):
    return (
        user.is_staff
        or conversation.participant_id == user.id
        or conversation.item.reported_by_id == user.id
    )


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("item", "item__reported_by", "participant"),
        pk=pk,
    )
    if not _user_can_access_conversation(request.user, conversation):
        messages.error(request, "You do not have access to that conversation.")
        return redirect("conversation_list")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=form.cleaned_data["body"],
            )
            conversation.save(update_fields=["updated_at"])
            return redirect("conversation_detail", pk=conversation.pk)
    else:
        form = MessageForm()

    other_user = (
        conversation.participant
        if conversation.item.reported_by == request.user
        else conversation.item.reported_by
    )
    chat_messages = conversation.messages.select_related("sender")

    return render(
        request,
        "items/conversation_detail.html",
        {
            "conversation": conversation,
            "chat_messages": chat_messages,
            "form": form,
            "other_user": other_user,
        },
    )


@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item.objects.select_related("reported_by"), pk=pk)
    if item.reported_by != request.user:
        messages.error(request, "You can only edit items you reported.")
        return redirect("item_list")

    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect("item_detail", pk=item.pk)
    else:
        form = ItemForm(instance=item)

    return render(
        request,
        "items/item_form.html",
        {
            "form": form,
            "item": item,
            "page_title": "Edit Item",
            "submit_label": "Save Changes",
            "show_verification": item.report_type == Item.ReportType.FOUND,
        },
    )


@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item.objects.select_related("reported_by"), pk=pk)
    if item.reported_by != request.user:
        messages.error(request, "You can only delete items you reported.")
        return redirect("item_list")

    if request.method == "POST":
        item.delete()
        messages.success(request, "Item deleted successfully.")
        return redirect("item_list")

    return render(request, "items/item_confirm_delete.html", {"item": item})


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
            "show_verification": report_type == Item.ReportType.FOUND,
        },
    )


@staff_required
def admin_dashboard(request):
    recent_items = Item.objects.select_related("reported_by")[:6]
    recent_users = User.objects.order_by("-date_joined")[:6]
    recent_conversations = Conversation.objects.select_related(
        "item",
        "item__reported_by",
        "participant",
    )[:6]
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
        "total_users": User.objects.count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
        "student_profiles": Profile.objects.filter(role=Profile.Role.STUDENT).count(),
        "recent_items": recent_items,
        "recent_conversations": recent_conversations,
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
