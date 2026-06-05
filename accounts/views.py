from django.shortcuts import render, redirect
from .models import Store

def login_view(request):

    error = ""

    if request.method == "POST":

        code = request.POST.get("code")
        password = request.POST.get("password")

        try:

            store = Store.objects.get(
                code=code,
                password=password
            )

            request.session["store_id"] = store.id

            return redirect("/dashboard/")

        except:
            error = "Sai mã CH hoặc mật khẩu"

    return render(
        request,
        "accounts/login.html",
        {
            "error": error
        }
    )
def logout_view(request):

    request.session.flush()

    return redirect("/")