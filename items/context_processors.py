from .models import Claim, Notification


def nav_counts(request):
    if not request.user.is_authenticated:
        return {}

    pending_claims = Claim.objects.filter(status=Claim.Status.PENDING)
    if not request.user.is_staff:
        pending_claims = pending_claims.filter(item__reported_by=request.user)

    return {
        "unread_notification_count": Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count(),
        "pending_claim_count": pending_claims.count(),
    }
