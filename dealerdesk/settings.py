"""DealerDesk settings. Everything environment-specific comes from environment variables.

Required: DATABASE_URL (PostgreSQL). Also read: SUPPLIER_API_URL, SUPPLIER_API_KEY and one LLM key
(GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY or GROQ_API_KEY).
For local development you can put them in a .env file at the repo root (never commit it).
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # real environment variables always win over .env

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    # add your apps here
]

MIDDLEWARE = [
    "core.middleware.SimpleCorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dealerdesk.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "dealerdesk.wsgi.application"

# ---- Database: PostgreSQL only -------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ImproperlyConfigured("Set DATABASE_URL to a PostgreSQL URL, e.g. postgres://user:pass@localhost:5432/dealerdesk")
DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=0)}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("DealerDesk requires PostgreSQL. SQLite can't test the concurrency rules.")

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
FRONTEND_DEV_URL = os.environ.get("FRONTEND_DEV_URL", "http://127.0.0.1:5173/")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- API: no authentication in this assignment ----------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
}

# ---- Assignment settings --------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_MODEL_PREFERENCES = [
    m.strip()
    for m in os.environ.get(
        "GEMINI_MODEL_PREFERENCES",
        "gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.8-flash,gemini-3.1-flash-lite",
    ).split(",")
    if m.strip()
]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_MODEL_PREFERENCES = [
    m.strip()
    for m in os.environ.get(
        "GROQ_MODEL_PREFERENCES",
        "qwen/qwen3.8-27b,openai/gpt-oss-120b,llama-3.3-70b-versatile",
    ).split(",")
    if m.strip()
]
GROQ_ENABLED = os.environ.get("GROQ_ENABLED", "true").lower() in ("true", "1", "yes")
SUPPLIER_API_URL = os.environ.get("SUPPLIER_API_URL", "http://127.0.0.1:8099")
SUPPLIER_API_KEY = os.environ.get("SUPPLIER_API_KEY", "")

