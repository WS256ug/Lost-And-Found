from django.contrib.auth import views as auth_views
from django.urls import path

from .views import StaffAwareLoginView, signup_view

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("login/", StaffAwareLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
