from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from .middleware import CanonicalHostMiddleware


class CanonicalHostMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(
        CANONICAL_HOST="lost-and-found-murex-kappa.vercel.app",
        CANONICAL_SCHEME="https",
    )
    def test_redirects_alias_host_to_canonical_host(self):
        request = self.factory.get(
            "/items/lost/new/?next=report",
            HTTP_HOST="lost-and-found-ws-teams.vercel.app",
        )
        middleware = CanonicalHostMiddleware(lambda request: HttpResponse("ok"))

        response = middleware(request)

        self.assertEqual(response.status_code, 308)
        self.assertEqual(
            response["Location"],
            "https://lost-and-found-murex-kappa.vercel.app/items/lost/new/?next=report",
        )

    @override_settings(
        CANONICAL_HOST="lost-and-found-murex-kappa.vercel.app",
        CANONICAL_SCHEME="https",
    )
    def test_allows_canonical_host(self):
        request = self.factory.get(
            "/items/lost/new/",
            HTTP_HOST="lost-and-found-murex-kappa.vercel.app",
        )
        middleware = CanonicalHostMiddleware(lambda request: HttpResponse("ok"))

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
