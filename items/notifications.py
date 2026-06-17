from .models import Claim, Notification


def create_notification(
    *,
    recipient,
    actor,
    notification_type,
    title,
    message,
    item=None,
    claim=None,
):
    if actor is not None and recipient.pk == actor.pk:
        return None

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        item=item,
        claim=claim,
    )


def notify_claim_submitted(claim, actor):
    return create_notification(
        recipient=claim.item.reported_by,
        actor=actor,
        notification_type=Notification.Type.CLAIM_SUBMITTED,
        title="New claim submitted",
        message=f"{actor.username} submitted a claim for your found item.",
        item=claim.item,
        claim=claim,
    )


def notify_claim_reviewed(claim, actor, *, auto_rejected=False):
    if claim.status == Claim.Status.APPROVED:
        return create_notification(
            recipient=claim.claimant,
            actor=actor,
            notification_type=Notification.Type.CLAIM_APPROVED,
            title="Claim approved",
            message="Your claim was approved. Contact the reporter to arrange return.",
            item=claim.item,
            claim=claim,
        )

    if claim.status == Claim.Status.REJECTED:
        message = (
            "Your claim was rejected because another claim was approved."
            if auto_rejected
            else "Your claim was rejected. Check the item for reviewer notes."
        )
        return create_notification(
            recipient=claim.claimant,
            actor=actor,
            notification_type=Notification.Type.CLAIM_REJECTED,
            title="Claim rejected",
            message=message,
            item=claim.item,
            claim=claim,
        )

    return None
