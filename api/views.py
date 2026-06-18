from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from items.models import Claim, Conversation, Item, Message, Notification
from items.notifications import notify_claim_reviewed, notify_claim_submitted

from .serializers import (
    ClaimCreateSerializer,
    ClaimReviewSerializer,
    ClaimSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    CurrentUserSerializer,
    ItemSerializer,
    ItemSummarySerializer,
    NotificationSerializer,
    PublicFoundItemDetailSerializer,
    PublicFoundItemSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    RegisterSerializer,
)


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": CurrentUserSerializer(user, context={"request": request}).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


class IsItemOwnerOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            if obj.report_type == Item.ReportType.FOUND:
                return True
            return obj.can_user_view_private_details(request.user)
        return bool(request.user.is_staff or obj.reported_by_id == request.user.id)


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [IsItemOwnerOrStaff]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == "list":
            return PublicFoundItemSerializer
        return ItemSerializer

    def get_queryset(self):
        items = Item.objects.select_related("reported_by")
        user = self.request.user
        query = self.request.query_params.get("q", "").strip()
        status_filter = self.request.query_params.get("status", "").strip()
        category = self.request.query_params.get("category", "").strip()
        report_type = (
            self.request.query_params.get("type", "").strip()
            or self.request.query_params.get("report_type", "").strip()
        )

        if not user.is_authenticated:
            items = items.filter(report_type=Item.ReportType.FOUND)
        elif not user.is_staff:
            items = items.filter(
                Q(report_type=Item.ReportType.FOUND)
                | Q(reported_by=user)
                | Q(conversations__participant=user)
                | Q(claims__claimant=user)
            ).distinct()

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

        if status_filter:
            items = items.filter(status=status_filter)

        if category:
            items = items.filter(category=category)

        if report_type:
            items = items.filter(report_type=report_type)

        return items

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        serializer_class = (
            ItemSerializer
            if item.can_user_view_private_details(request.user)
            else PublicFoundItemDetailSerializer
        )
        serializer = serializer_class(item, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="claims",
    )
    def claims(self, request, pk=None):
        item = self.get_object()
        serializer = ClaimCreateSerializer(
            data=request.data,
            context={"item": item, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        notify_claim_submitted(claim, request.user)

        return Response(
            ClaimSerializer(claim, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="start-conversation",
    )
    def start_conversation(self, request, pk=None):
        item = self.get_object()
        if item.reported_by_id == request.user.id:
            return Response(
                {"detail": "Use your conversation list to reply about your own item."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            item.report_type == Item.ReportType.FOUND
            and not item.can_user_view_private_details(request.user)
        ):
            return Response(
                {"detail": "Submit a claim to contact the reporter about this found item."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation, created = Conversation.objects.get_or_create(
            item=item,
            participant=request.user,
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            ConversationDetailSerializer(
                conversation,
                context={"request": request},
            ).data,
            status=response_status,
        )


class IsConversationMemberOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user.is_staff
            or obj.participant_id == request.user.id
            or obj.item.reported_by_id == request.user.id
        )


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsConversationMemberOrStaff]

    def get_queryset(self):
        conversations = (
            Conversation.objects.select_related(
                "item",
                "item__reported_by",
                "participant",
            )
            .prefetch_related("messages", "messages__sender")
        )

        if self.request.user.is_staff:
            return conversations

        return conversations.filter(
            Q(participant=self.request.user) | Q(item__reported_by=self.request.user)
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ConversationListSerializer
        return ConversationDetailSerializer

    @action(detail=True, methods=["post"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=serializer.validated_data["body"],
        )
        conversation.save(update_fields=["updated_at"])

        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class IsClaimParticipantOrReviewer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user.is_staff
            or obj.claimant_id == request.user.id
            or obj.item.reported_by_id == request.user.id
        )


class ClaimViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClaimSerializer
    permission_classes = [IsClaimParticipantOrReviewer]

    def get_queryset(self):
        claims = Claim.objects.select_related(
            "item",
            "item__reported_by",
            "claimant",
            "reviewed_by",
        )

        if self.request.user.is_staff:
            return claims

        return claims.filter(
            Q(claimant=self.request.user) | Q(item__reported_by=self.request.user)
        )

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        claim = self.get_object()
        if not request.user.is_staff and claim.item.reported_by_id != request.user.id:
            return Response(
                {"detail": "Only the reporter or staff can review this claim."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ClaimReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        claim.review(
            reviewer=request.user,
            next_status=serializer.validated_data["status"],
            note=serializer.validated_data.get("review_note", ""),
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

        if claim.status == Claim.Status.APPROVED:
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
            rejection_time = timezone.now()
            Claim.objects.filter(
                item=item,
                status=Claim.Status.PENDING,
            ).exclude(pk=claim.pk).update(
                status=Claim.Status.REJECTED,
                reviewed_by=request.user,
                reviewed_at=rejection_time,
                review_note="Another claim was approved.",
            )
            for other_claim in other_pending_claims:
                other_claim.status = Claim.Status.REJECTED
                other_claim.reviewed_by = request.user
                other_claim.reviewed_at = rejection_time
                other_claim.review_note = "Another claim was approved."
                notify_claim_reviewed(other_claim, request.user, auto_rejected=True)

        return Response(ClaimSerializer(claim, context={"request": request}).data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "recipient",
            "actor",
            "item",
            "claim",
            "claim__item",
            "claim__item__reported_by",
            "claim__claimant",
            "claim__reviewed_by",
        )

    @action(detail=True, methods=["post"], url_path="read")
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(
            NotificationSerializer(notification, context={"request": request}).data
        )

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({"updated": updated})
