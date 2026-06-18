from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class HttpResponsePermanentRedirectPreserveMethod(HttpResponsePermanentRedirect):
    status_code = 308


class CanonicalHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        canonical_host = getattr(settings, "CANONICAL_HOST", "").strip().lower()
        if canonical_host:
            request_host = request.get_host().split(":", 1)[0].lower()
            if request_host != canonical_host:
                scheme = getattr(settings, "CANONICAL_SCHEME", "") or request.scheme
                url = f"{scheme}://{canonical_host}{request.get_full_path()}"
                return HttpResponsePermanentRedirectPreserveMethod(url)

        return self.get_response(request)
