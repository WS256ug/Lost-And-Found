from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import LoginForm, SignUpForm
from .models import Profile


class StaffAwareLoginView(LoginView):
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        if self.request.user.is_staff:
            return reverse("admin_dashboard")
        return reverse("item_list")


def signup_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin_dashboard")
        return redirect("item_list")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(
                user=user,
                role=form.cleaned_data["role"],
                phone_number=form.cleaned_data.get("phone_number"),
                identification_number=form.cleaned_data["identification_number"],
            )
            login(request, user)
            messages.success(request, "Your account has been created successfully.")
            return redirect("item_list")
    else:
        form = SignUpForm()

    return render(request, "accounts/signup.html", {"form": form})
