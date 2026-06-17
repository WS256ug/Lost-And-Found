# Digital Lost and Found Management System

## Simple Django MVP Design

This MVP is based on the chapter-one problem statement: the biggest gaps are manual record keeping, poor communication, and low recovery rates. The design below keeps only the minimum features needed to make the system usable in a university environment.

As of April 29, 2026, the latest stable Django release is `6.0.4`. For a school project that prefers long-term support, `5.2.13` is also a reasonable choice.

## 1. System Architecture Overview

Use a simple 3-layer web application:

1. Presentation layer
   Basic HTML templates rendered by Django.
   Users interact through pages for signup, login, item reporting, item listing, and item detail.

2. Application layer
   Django views, forms, and authentication handle business logic.
   Search, filtering, and status updates are processed here.

3. Data layer
   SQLite stores users, profiles, and item reports.
   Uploaded images are saved in a local `media/` folder.

Simple flow:

`Browser -> Django Views/Forms -> SQLite Database`

Admin flow:

`Admin User -> Django Admin -> Item Status Update`

Why this is enough for MVP:

- Django already provides authentication and admin tools.
- SQLite is enough for development and demonstrations.
- One main `Item` model avoids unnecessary complexity.
- Local media storage is enough for optional image uploads.

## 2. Suggested Django App Structure

```text
lostfound/
|-- manage.py
|-- lostfound/
|   |-- __init__.py
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- accounts/
|   |-- __init__.py
|   |-- admin.py
|   |-- apps.py
|   |-- forms.py
|   |-- models.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|-- items/
|   |-- __init__.py
|   |-- admin.py
|   |-- apps.py
|   |-- forms.py
|   |-- models.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|-- templates/
|   |-- base.html
|   |-- registration/
|   |   `-- login.html
|   |-- accounts/
|   |   `-- signup.html
|   `-- items/
|       |-- item_list.html
|       |-- item_form.html
|       `-- item_detail.html
|-- static/
|   `-- css/
|       `-- styles.css
`-- media/
    `-- item_images/
```

### App responsibilities

- `accounts`
  Handles signup and user role storage.

- `items`
  Handles lost/found reports, search, display, and status tracking.

No separate custom admin app is needed for MVP. Use Django's built-in admin panel.

### Small setup notes

- Install `Pillow` for image upload support.
- Configure `MEDIA_URL` and `MEDIA_ROOT` in `settings.py`.
- Use Django's default authentication templates where possible to reduce work.

## 3. Database Models

### User model choice

For the simplest implementation, use Django's built-in `User` model for authentication.

Then add a small `Profile` model to store role:

- `Student`
- `Staff`

Admin users can be handled with Django's `is_staff` / `is_superuser`.

### Minimal models

#### `Profile`

```python
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("staff", "Staff"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
```

#### `Item`

Use one shared model for both lost and found reports.

```python
from django.contrib.auth.models import User
from django.db import models


class Item(models.Model):
    REPORT_TYPE_CHOICES = [
        ("lost", "Lost"),
        ("found", "Found"),
    ]

    STATUS_CHOICES = [
        ("lost", "Lost"),
        ("found", "Found"),
        ("claimed", "Claimed"),
        ("returned", "Returned"),
    ]

    CATEGORY_CHOICES = [
        ("electronics", "Electronics"),
        ("documents", "Documents"),
        ("id_cards", "ID Cards"),
        ("keys", "Keys"),
        ("books", "Books"),
        ("clothing", "Clothing"),
        ("other", "Other"),
    ]

    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=150)
    event_date = models.DateField()
    image = models.ImageField(upload_to="item_images/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
```

### Important MVP notes

- `report_type` tells us whether the report is about a lost item or a found item.
- `status` tracks the current lifecycle of the item.
- On creation:
  - a lost report starts with status `lost`
  - a found report starts with status `found`
- No separate matching table is needed in MVP.
- No complex claim verification model is needed in MVP.
- Users contact reporters through item-based conversations.

## 4. Key Views

Function-based views are fine here because the logic is small and easy to follow.

### `accounts/views.py`

- `signup_view`
  Creates a user and profile.

- `LoginView`
  Use Django's built-in login view.

- `LogoutView`
  Use Django's built-in logout view.

### `items/views.py`

- `item_list`
  Shows all items.
  Supports:
  - keyword search with `q`
  - filter by `status`
  - filter by `category`

- `item_detail`
  Shows full item details and current status.

- `report_lost_item`
  Shows the item form and saves a new record with:
  - `report_type = "lost"`
  - `status = "lost"`

- `report_found_item`
  Shows the same form and saves a new record with:
  - `report_type = "found"`
  - `status = "found"`

Access control:

- `report_lost_item` and `report_found_item` should require login.
- Django admin should be accessible only to staff/admin users.

### Admin handling

For MVP, do not build a custom admin dashboard page.

Use Django admin for:

- viewing all items
- searching items
- filtering by status/category
- updating status to `claimed` or `returned`

Example `items/admin.py`:

```python
from django.contrib import admin
from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "report_type", "category", "status", "location", "event_date", "reported_by")
    list_filter = ("report_type", "category", "status")
    search_fields = ("title", "description", "location")
```

## 5. URL Routes

### Project `urls.py`

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("items.urls")),
    path("accounts/", include("accounts.urls")),
]
```

### `accounts/urls.py`

```python
from django.contrib.auth import views as auth_views
from django.urls import path
from .views import signup_view

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
```

### `items/urls.py`

```python
from django.urls import path
from .views import item_detail, item_list, report_found_item, report_lost_item

urlpatterns = [
    path("", item_list, name="home"),
    path("items/", item_list, name="item_list"),
    path("items/lost/new/", report_lost_item, name="report_lost_item"),
    path("items/found/new/", report_found_item, name="report_found_item"),
    path("items/<int:pk>/", item_detail, name="item_detail"),
]
```

## 6. Basic Templates / Pages Needed

Keep the interface very small.

### Core pages

- `base.html`
  Shared navigation and layout.

- `registration/login.html`
  Login form.

- `accounts/signup.html`
  Registration form with role selection.

- `items/item_list.html`
  Main page showing:
  - search bar
  - status filter
  - category filter
  - list of all reported items

- `items/item_form.html`
  Reusable form for both lost and found item reporting.

- `items/item_detail.html`
  Shows one item's full information and current status.

### Simple navigation

Add links for:

- Home
- Report Lost Item
- Report Found Item
- Login / Logout
- Signup
- Admin

## 7. Simple User Workflow

### Student or Staff

1. Register an account.
2. Log in.
3. Submit a lost or found item report.
4. Browse the item list.
5. Use search or filters to look for relevant items.
6. Open item detail pages to check full information and status.

### Admin

1. Log in through Django admin.
2. View all item reports.
3. Search or filter records.
4. Update an item's status to:
   - `claimed`
   - `returned`

### Example system flow

1. A student loses a laptop and reports it.
2. Another user later reports a found laptop.
3. Both reports appear in the public item list.
4. Admin checks the reports and, once handled physically, updates the status.
5. The owner sees the updated status on the site.

## 8. Future Improvements

These are useful later, but should stay out of the first MVP:

- automatic matching suggestions between lost and found reports
- email or SMS notifications
- ownership verification questions
- real-time messaging notifications
- audit logs and reporting dashboards
- QR code tagging for stored items
- mobile app

## Recommended MVP Summary

If you want the simplest possible implementation, build only this:

- Django authentication
- `Profile` model for role
- one `Item` model
- one reusable item form
- one item list page with search/filter
- one item detail page
- Django admin for status updates
- SQLite database

This is enough to demonstrate a working Digital Lost and Found Management System without overengineering.
