from django.shortcuts import render, redirect
from .models import Store
from django.contrib.auth import authenticate, login
from django.utils import timezone
from .models import Store


def login_view(request):

    error = ""

    if request.method == "POST":

        code = request.POST.get("code")
        password = request.POST.get("password")

        # Ưu tiên check admin trước
        user = authenticate(
            request,
            username=code,
            password=password
        )

        if user and user.is_staff:

            login(request, user)

            today = timezone.localdate()

            return redirect(
                f"/admin-day/{today}/"
            )

        # Nếu không phải admin thì check cửa hàng
        try:

            store = Store.objects.get(
                code=code,
                password=password
            )

            request.session["store_id"] = store.id

            return redirect("/dashboard/")

        except Store.DoesNotExist:

            error = "Sai tài khoản hoặc mật khẩu"

    return render(
        request,
        "accounts/login.html",
        {"error": error}
    )
def logout_view(request):

    request.session.flush()

    return redirect("/")