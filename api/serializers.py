from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from rest_framework import serializers

from accounts.models import Profile
from items.models import Claim, Conversation, Item, Message, Notification


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("role", "phone_number", "identification_number")


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_staff")


class CurrentUserSerializer(UserSummarySerializer):
    profile = serializers.SerializerMethodField()

    class Meta(UserSummarySerializer.Meta):
        fields = UserSummarySerializer.Meta.fields + ("profile",)

    def get_profile(self, obj):
        try:
            profile = obj.profile
        except Profile.DoesNotExist:
            return None
        return ProfileSerializer(profile).data


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )
    identification_number = serializers.CharField(max_length=50)
    role = serializers.ChoiceField(choices=Profile.Role.choices)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        profile_data = {
            "role": validated_data.pop("role"),
            "phone_number": validated_data.pop("phone_number", ""),
            "identification_number": validated_data.pop("identification_number"),
        }
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, **profile_data)
        return user


class ItemSummarySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    report_type_display = serializers.CharField(
        source="get_report_type_display",
        read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Item
        fields = (
            "id",
            "report_type",
            "report_type_display",
            "title",
            "category",
            "location",
            "event_date",
            "status",
            "status_display",
            "image_url",
            "created_at",
        )

    def get_image_url(self, obj):
        if not obj.image and not obj.image_data:
            return None

        url = reverse("item_image", args=[obj.pk])
        request = self.context.get("request")
        if request is None:
            return url
        return request.build_absolute_uri(url)


class PublicFoundItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    report_type_display = serializers.CharField(
        source="get_report_type_display",
        read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    public_label = serializers.SerializerMethodField()
    can_view_private_details = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = (
            "id",
            "report_type",
            "report_type_display",
            "public_label",
            "image_url",
            "status",
            "status_display",
            "created_at",
            "can_view_private_details",
        )

    def get_image_url(self, obj):
        if not obj.image and not obj.image_data:
            return None

        url = reverse("item_image", args=[obj.pk])
        request = self.context.get("request")
        if request is None:
            return url
        return request.build_absolute_uri(url)

    def get_public_label(self, obj):
        if obj.report_type == Item.ReportType.FOUND:
            return "Found item"
        return "Lost report"

    def get_can_view_private_details(self, obj):
        request = self.context.get("request")
        return bool(request and obj.can_user_view_private_details(request.user))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and instance.can_user_view_private_details(request.user):
            data.update(
                {
                    "title": instance.title,
                    "category": instance.category,
                    "category_display": instance.get_category_display(),
                    "location": instance.location,
                    "event_date": instance.event_date.isoformat(),
                }
            )
        return data


class PublicFoundItemDetailSerializer(PublicFoundItemSerializer):
    verification_question = serializers.CharField(read_only=True)
    has_verification_question = serializers.SerializerMethodField()
    my_claim = serializers.SerializerMethodField()

    class Meta(PublicFoundItemSerializer.Meta):
        fields = PublicFoundItemSerializer.Meta.fields + (
            "verification_question",
            "has_verification_question",
            "my_claim",
        )

    def get_has_verification_question(self, obj):
        return obj.has_verification_question

    def get_my_claim(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        claim = obj.claims.filter(claimant=request.user).first()
        if claim is None:
            return None

        return {
            "id": claim.id,
            "status": claim.status,
            "status_display": claim.get_status_display(),
            "answer_matches": claim.answer_matches,
            "review_note": claim.review_note,
            "created_at": claim.created_at,
            "reviewed_at": claim.reviewed_at,
        }


class ItemSerializer(ItemSummarySerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    reported_by = UserSummarySerializer(read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    verification_answer = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    has_verification_question = serializers.SerializerMethodField()
    my_claim = serializers.SerializerMethodField()
    can_view_private_details = serializers.SerializerMethodField()

    class Meta(ItemSummarySerializer.Meta):
        fields = (
            "id",
            "report_type",
            "report_type_display",
            "title",
            "description",
            "category",
            "category_display",
            "location",
            "event_date",
            "image",
            "image_url",
            "verification_question",
            "verification_answer",
            "has_verification_question",
            "status",
            "status_display",
            "reported_by",
            "my_claim",
            "can_view_private_details",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "reported_by",
            "created_at",
            "updated_at",
        )

    def get_has_verification_question(self, obj):
        return obj.has_verification_question

    def get_can_view_private_details(self, obj):
        request = self.context.get("request")
        return bool(request and obj.can_user_view_private_details(request.user))

    def get_my_claim(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        claim = obj.claims.filter(claimant=request.user).first()
        if claim is None:
            return None

        return {
            "id": claim.id,
            "status": claim.status,
            "status_display": claim.get_status_display(),
            "answer_matches": claim.answer_matches,
            "review_note": claim.review_note,
            "created_at": claim.created_at,
            "reviewed_at": claim.reviewed_at,
        }

    def validate_report_type(self, value):
        if value not in (Item.ReportType.LOST, Item.ReportType.FOUND):
            raise serializers.ValidationError("Report type must be lost or found.")
        if self.instance is not None and value != self.instance.report_type:
            raise serializers.ValidationError("Report type cannot be changed.")
        return value

    def create(self, validated_data):
        image = validated_data.get("image")
        verification_answer = validated_data.pop("verification_answer", "")
        report_type = validated_data["report_type"]
        validated_data["status"] = (
            Item.Status.LOST
            if report_type == Item.ReportType.LOST
            else Item.Status.FOUND
        )
        item = super().create(validated_data)
        update_fields = []
        if image:
            item.store_image_file(image)
            update_fields.extend(["image_data", "image_content_type", "image_filename"])
        if verification_answer:
            item.set_verification_answer(verification_answer)
            update_fields.append("verification_answer_hash")
        if update_fields:
            item.save(update_fields=update_fields)
        return item

    def update(self, instance, validated_data):
        image = validated_data.get("image")
        verification_answer = validated_data.pop("verification_answer", "")
        item = super().update(instance, validated_data)
        update_fields = []
        if image:
            item.store_image_file(image)
            update_fields.extend(["image_data", "image_content_type", "image_filename"])
        if verification_answer:
            item.set_verification_answer(verification_answer)
            update_fields.append("verification_answer_hash")
        if update_fields:
            item.save(update_fields=update_fields)
        return item


class ClaimSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    claimant = UserSummarySerializer(read_only=True)
    claimant_profile = serializers.SerializerMethodField()
    reviewed_by = UserSummarySerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id",
            "item",
            "claimant",
            "claimant_profile",
            "proof_details",
            "answer_matches",
            "status",
            "status_display",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_item(self, obj):
        request = self.context.get("request")
        if request and obj.item.can_user_view_private_details(request.user):
            return ItemSummarySerializer(obj.item, context=self.context).data
        return PublicFoundItemSerializer(obj.item, context=self.context).data

    def get_claimant_profile(self, obj):
        try:
            profile = obj.claimant.profile
        except Profile.DoesNotExist:
            return None
        return ProfileSerializer(profile).data


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSummarySerializer(read_only=True)
    actor = UserSummarySerializer(read_only=True)
    item = serializers.SerializerMethodField()
    claim = serializers.SerializerMethodField()
    notification_type_display = serializers.CharField(
        source="get_notification_type_display",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "recipient",
            "actor",
            "notification_type",
            "notification_type_display",
            "title",
            "message",
            "item",
            "claim",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields

    def get_item(self, obj):
        if obj.item is None:
            return None

        request = self.context.get("request")
        if request and obj.item.can_user_view_private_details(request.user):
            return ItemSummarySerializer(obj.item, context=self.context).data
        return PublicFoundItemSerializer(obj.item, context=self.context).data

    def get_claim(self, obj):
        if obj.claim is None:
            return None
        return ClaimSerializer(obj.claim, context=self.context).data


class ClaimCreateSerializer(serializers.Serializer):
    verification_answer = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        write_only=True,
    )
    proof_details = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate(self, attrs):
        item = self.context["item"]
        request = self.context["request"]

        if item.report_type != Item.ReportType.FOUND:
            raise serializers.ValidationError("Only found items can be claimed.")

        if item.reported_by_id == request.user.id:
            raise serializers.ValidationError("You cannot claim an item you reported.")

        if item.status in (Item.Status.CLAIMED, Item.Status.RETURNED):
            raise serializers.ValidationError("This item is no longer available to claim.")

        if Claim.objects.filter(item=item, claimant=request.user).exists():
            raise serializers.ValidationError("You already submitted a claim for this item.")

        if item.has_verification_question and not attrs.get("verification_answer"):
            raise serializers.ValidationError(
                {"verification_answer": "Answer the verification question to submit a claim."}
            )

        return attrs

    def create(self, validated_data):
        item = self.context["item"]
        request = self.context["request"]
        verification_answer = validated_data.get("verification_answer", "")

        return Claim.objects.create(
            item=item,
            claimant=request.user,
            proof_details=validated_data["proof_details"],
            answer_matches=item.check_verification_answer(verification_answer),
        )


class ClaimReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(Claim.Status.APPROVED, Claim.Status.REJECTED),
    )
    review_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        trim_whitespace=True,
    )


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("id", "sender", "body", "created_at", "is_mine")

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.sender_id == request.user.id)


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, trim_whitespace=True)


class ConversationListSerializer(serializers.ModelSerializer):
    item = ItemSummarySerializer(read_only=True)
    participant = UserSummarySerializer(read_only=True)
    reporter = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "item",
            "participant",
            "reporter",
            "other_user",
            "last_message",
            "created_at",
            "updated_at",
        )

    def get_reporter(self, obj):
        return UserSummarySerializer(obj.item.reported_by).data

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        other_user = (
            obj.participant
            if obj.item.reported_by_id == request.user.id
            else obj.item.reported_by
        )
        return UserSummarySerializer(other_user).data

    def get_last_message(self, obj):
        messages = list(obj.messages.all())
        if not messages:
            return None
        return MessageSerializer(messages[-1], context=self.context).data


class ConversationDetailSerializer(ConversationListSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ("messages",)
