from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import Profile
from items.models import Claim, Item


DEMO_PASSWORD = "DemoPass123"


class Command(BaseCommand):
    help = "Create demo users, lost/found items, generated item photos, and claims."

    def handle(self, *args, **options):
        media_dir = Path(settings.MEDIA_ROOT) / "item_images" / "demo"
        media_dir.mkdir(parents=True, exist_ok=True)

        users = self._create_users()
        images = self._create_images(media_dir)
        items = self._create_items(users, images)
        self._create_claims(users, items)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("Demo password for all users: DemoPass123")
        self.stdout.write("Users: " + ", ".join(sorted(users.keys())))
        self.stdout.write(f"Items created/updated: {len(items)}")

    def _create_users(self):
        user_rows = [
            {
                "username": "demo_staff",
                "email": "staff@example.com",
                "first_name": "Grace",
                "last_name": "Admin",
                "is_staff": True,
                "role": Profile.Role.STAFF,
                "phone_number": "0700000100",
                "identification_number": "STAFF-100",
            },
            {
                "username": "demo_amina",
                "email": "amina@example.com",
                "first_name": "Amina",
                "last_name": "Nabukeera",
                "is_staff": False,
                "role": Profile.Role.STUDENT,
                "phone_number": "0700000101",
                "identification_number": "STU-2026-101",
            },
            {
                "username": "demo_brian",
                "email": "brian@example.com",
                "first_name": "Brian",
                "last_name": "Kato",
                "is_staff": False,
                "role": Profile.Role.STUDENT,
                "phone_number": "0700000102",
                "identification_number": "STU-2026-102",
            },
            {
                "username": "demo_claire",
                "email": "claire@example.com",
                "first_name": "Claire",
                "last_name": "Mutesi",
                "is_staff": False,
                "role": Profile.Role.STUDENT,
                "phone_number": "0700000103",
                "identification_number": "STU-2026-103",
            },
            {
                "username": "demo_david",
                "email": "david@example.com",
                "first_name": "David",
                "last_name": "Okello",
                "is_staff": False,
                "role": Profile.Role.STUDENT,
                "phone_number": "0700000104",
                "identification_number": "STU-2026-104",
            },
        ]

        users = {}
        for row in user_rows:
            profile_data = {
                "role": row.pop("role"),
                "phone_number": row.pop("phone_number"),
                "identification_number": row.pop("identification_number"),
            }
            username = row["username"]
            user, created = User.objects.update_or_create(
                username=username,
                defaults=row,
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            elif not user.has_usable_password():
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])

            Profile.objects.update_or_create(
                user=user,
                defaults=profile_data,
            )
            users[username] = user

        return users

    def _create_images(self, media_dir):
        image_specs = {
            "found_phone.jpg": {
                "label": "Phone",
                "sub_label": "blue case",
                "bg": (28, 94, 122),
                "accent": (120, 210, 210),
            },
            "found_keys.jpg": {
                "label": "Keys",
                "sub_label": "green tag",
                "bg": (39, 112, 76),
                "accent": (216, 238, 116),
            },
            "found_book.jpg": {
                "label": "Book",
                "sub_label": "library copy",
                "bg": (124, 73, 38),
                "accent": (245, 214, 146),
            },
            "found_id.jpg": {
                "label": "ID Card",
                "sub_label": "campus card",
                "bg": (82, 90, 112),
                "accent": (238, 238, 245),
            },
            "lost_laptop.jpg": {
                "label": "Laptop",
                "sub_label": "silver",
                "bg": (44, 57, 74),
                "accent": (160, 189, 216),
            },
            "lost_bag.jpg": {
                "label": "Bag",
                "sub_label": "red strap",
                "bg": (122, 52, 59),
                "accent": (242, 163, 112),
            },
            "lost_wallet.jpg": {
                "label": "Wallet",
                "sub_label": "brown",
                "bg": (94, 70, 54),
                "accent": (222, 179, 122),
            },
        }

        paths = {}
        for filename, spec in image_specs.items():
            path = media_dir / filename
            self._draw_item_image(path, spec)
            paths[filename] = f"item_images/demo/{filename}"
        return paths

    def _draw_item_image(self, path, spec):
        width, height = 960, 720
        image = Image.new("RGB", (width, height), spec["bg"])
        draw = ImageDraw.Draw(image)
        font_large = self._font(92)
        font_medium = self._font(42)
        font_small = self._font(28)

        accent = spec["accent"]
        draw.rounded_rectangle((90, 80, 870, 640), radius=36, fill=(250, 252, 252))
        draw.rounded_rectangle((140, 130, 820, 430), radius=28, fill=accent)
        draw.ellipse((345, 180, 615, 450), fill=spec["bg"])
        draw.rounded_rectangle((390, 235, 570, 395), radius=22, fill=(250, 252, 252))

        label_box = draw.textbbox((0, 0), spec["label"], font=font_large)
        label_width = label_box[2] - label_box[0]
        draw.text(
            ((width - label_width) / 2, 480),
            spec["label"],
            fill=(30, 42, 50),
            font=font_large,
        )

        sub_label = spec["sub_label"]
        sub_box = draw.textbbox((0, 0), sub_label, font=font_medium)
        sub_width = sub_box[2] - sub_box[0]
        draw.text(
            ((width - sub_width) / 2, 570),
            sub_label,
            fill=(85, 102, 112),
            font=font_medium,
        )

        draw.text((26, 24), "Demo Lost & Found", fill=(245, 248, 250), font=font_small)
        image.save(path, "JPEG", quality=88)

    def _font(self, size):
        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        for font_path in font_paths:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size=size)
        return ImageFont.load_default()

    def _create_items(self, users, images):
        today = timezone.localdate()
        item_rows = [
            {
                "title": "Found blue phone",
                "report_type": Item.ReportType.FOUND,
                "description": "Found near the cafeteria. The real owner should describe the lock screen and case.",
                "category": Item.Category.ELECTRONICS,
                "location": "Cafeteria entrance",
                "event_date": today - timedelta(days=1),
                "status": Item.Status.FOUND,
                "reported_by": users["demo_staff"],
                "image": images["found_phone.jpg"],
                "verification_question": "What is on the lock screen?",
                "verification_answer": "blue mountain",
                "created_offset": 1,
            },
            {
                "title": "Found key bunch",
                "report_type": Item.ReportType.FOUND,
                "description": "A key bunch with a colored tag was handed in at security.",
                "category": Item.Category.KEYS,
                "location": "Main gate security desk",
                "event_date": today - timedelta(days=2),
                "status": Item.Status.FOUND,
                "reported_by": users["demo_staff"],
                "image": images["found_keys.jpg"],
                "verification_question": "What color is the tag?",
                "verification_answer": "green",
                "created_offset": 2,
            },
            {
                "title": "Found statistics book",
                "report_type": Item.ReportType.FOUND,
                "description": "Book found in the library reading area.",
                "category": Item.Category.BOOKS,
                "location": "Library second floor",
                "event_date": today - timedelta(days=3),
                "status": Item.Status.CLAIMED,
                "reported_by": users["demo_amina"],
                "image": images["found_book.jpg"],
                "verification_question": "What name is written inside the cover?",
                "verification_answer": "claire",
                "created_offset": 3,
            },
            {
                "title": "Found campus ID card",
                "report_type": Item.ReportType.FOUND,
                "description": "Student card found after morning lecture.",
                "category": Item.Category.ID_CARDS,
                "location": "Lecture room B12",
                "event_date": today - timedelta(days=4),
                "status": Item.Status.FOUND,
                "reported_by": users["demo_brian"],
                "image": images["found_id.jpg"],
                "verification_question": "What are the last three digits of the ID number?",
                "verification_answer": "104",
                "created_offset": 4,
            },
            {
                "title": "Lost silver laptop",
                "report_type": Item.ReportType.LOST,
                "description": "Silver laptop in a black sleeve. Has a small sticker near the touchpad.",
                "category": Item.Category.ELECTRONICS,
                "location": "Computer lab 3",
                "event_date": today - timedelta(days=1),
                "status": Item.Status.LOST,
                "reported_by": users["demo_brian"],
                "image": images["lost_laptop.jpg"],
                "created_offset": 1,
            },
            {
                "title": "Lost red-strap backpack",
                "report_type": Item.ReportType.LOST,
                "description": "Dark backpack with a red strap and notebooks inside.",
                "category": Item.Category.OTHER,
                "location": "Sports field",
                "event_date": today - timedelta(days=2),
                "status": Item.Status.LOST,
                "reported_by": users["demo_claire"],
                "image": images["lost_bag.jpg"],
                "created_offset": 2,
            },
            {
                "title": "Lost brown wallet",
                "report_type": Item.ReportType.LOST,
                "description": "Brown wallet with receipts and a student card.",
                "category": Item.Category.OTHER,
                "location": "Library cafe",
                "event_date": today - timedelta(days=5),
                "status": Item.Status.LOST,
                "reported_by": users["demo_david"],
                "image": images["lost_wallet.jpg"],
                "created_offset": 5,
            },
        ]

        items = {}
        for row in item_rows:
            verification_answer = row.pop("verification_answer", "")
            created_offset = row.pop("created_offset")
            item, _ = Item.objects.update_or_create(
                title=row["title"],
                defaults=row,
            )
            if verification_answer:
                item.set_verification_answer(verification_answer)
                item.save(update_fields=["verification_answer_hash"])
            Item.objects.filter(pk=item.pk).update(
                created_at=timezone.now() - timedelta(days=created_offset),
            )
            items[item.title] = item

        return items

    def _create_claims(self, users, items):
        claim_rows = [
            {
                "item": items["Found blue phone"],
                "claimant": users["demo_claire"],
                "proof_details": "The phone has a small crack near the top and the lock screen shows a blue mountain.",
                "verification_answer": "blue mountain",
                "status": Claim.Status.PENDING,
            },
            {
                "item": items["Found statistics book"],
                "claimant": users["demo_claire"],
                "proof_details": "My name is written inside the cover, and page 42 has my notes.",
                "verification_answer": "claire",
                "status": Claim.Status.APPROVED,
                "reviewed_by": users["demo_amina"],
                "review_note": "Verified with the name inside the cover.",
            },
            {
                "item": items["Found campus ID card"],
                "claimant": users["demo_david"],
                "proof_details": "The ID belongs to me and the last digits are 104.",
                "verification_answer": "104",
                "status": Claim.Status.PENDING,
            },
        ]

        for row in claim_rows:
            item = row["item"]
            claimant = row["claimant"]
            answer_matches = item.check_verification_answer(row["verification_answer"])
            defaults = {
                "proof_details": row["proof_details"],
                "answer_matches": answer_matches,
                "status": row["status"],
                "review_note": row.get("review_note", ""),
                "reviewed_by": row.get("reviewed_by"),
                "reviewed_at": timezone.now()
                if row["status"] != Claim.Status.PENDING
                else None,
            }
            Claim.objects.update_or_create(
                item=item,
                claimant=claimant,
                defaults=defaults,
            )
