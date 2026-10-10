from django.conf import settings
from django.contrib.auth.views import redirect_to_login


class LoginRequiredMiddleware:
    public_paths = ("/login", "/register", "/otp/", "/password/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        is_public = (
            any(
                path.startswith(public)
                if public.endswith("/")
                else path == public or path.startswith(public + "/")
                for public in self.public_paths
            )
            or path.startswith(settings.STATIC_URL)
        )
        if not is_public and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)
