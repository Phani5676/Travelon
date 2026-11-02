from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = SignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to BusGo, {user.username}.")

        next_url = request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        if hasattr(user, "operator"):
            return redirect("operator_dashboard")
        return redirect("home")

    return render(request, "accounts/signup.html", {"form": form})