from django.contrib import admin
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve
from .frontend_views import frontend_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("", frontend_page, name="frontend"),
    re_path(r"^(?:products|dealers|orders|assistant|forecasting)/?$", frontend_page),
]

# Local development can serve the Vite build on the same origin as the API.
# Production web servers should serve frontend/dist/assets and favicon.svg.
if settings.DEBUG:
    urlpatterns += [
        path("assets/<path:path>", serve, {"document_root": settings.BASE_DIR / "frontend" / "dist" / "assets"}),
        path("favicon.svg", serve, {"document_root": settings.BASE_DIR / "frontend" / "dist", "path": "favicon.svg"}),
    ]
