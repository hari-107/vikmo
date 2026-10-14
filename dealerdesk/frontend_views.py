"""Serve the compiled React entry point while retaining Django's API routes."""
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import redirect


def frontend_page(request):
    entry = settings.BASE_DIR / "frontend" / "dist" / "index.html"
    if entry.is_file():
        return FileResponse(entry.open("rb"), content_type="text/html; charset=utf-8")
    # Development still works before the first frontend production build.
    return redirect(settings.FRONTEND_DEV_URL)
