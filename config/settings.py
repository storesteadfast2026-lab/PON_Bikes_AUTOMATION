import os
from pathlib import Path


def _env_flag(name, default="0"):
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "pon-bike-dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [item.strip() for item in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if item.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "receiving",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "pon_bikes"),
            "USER": os.getenv("POSTGRES_USER", "pon_bikes"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "pon_bikes"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-au"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Australia/Adelaide")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "receiving:dashboard"
LOGOUT_REDIRECT_URL = "login"

# Windows default requested by the business. In Docker set this to the mounted path.
PON_CONTAINER_ROOT = os.getenv(
    "PON_CONTAINER_ROOT",
    r"S:\FORMS\CUSTOMER\PON - Pon.Bike\2026 Containers",
)
PON_PRODUCT_CATALOG_PATH = os.getenv(
    "PON_PRODUCT_CATALOG_PATH",
    r"C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls",
)
PON_PRODUCT_CATALOG_SOURCE_DISPLAY = os.getenv(
    "PON_PRODUCT_CATALOG_SOURCE_DISPLAY",
    r"C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls",
)
PON_PRODUCT_MOVES_PATH = os.getenv(
    "PON_PRODUCT_MOVES_PATH",
    r"T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV",
)
PON_UPSTOCKSERIAL_PATH = os.getenv(
    "PON_UPSTOCKSERIAL_PATH",
    r"T:\Import\UPStockSerial.csv",
)

# Operator-facing Windows paths. Docker uses /data/... internally, while the
# workflow screen shows the business/working locations that the operator knows.
PON_PRODUCT_MOVES_SOURCE_DISPLAY = os.getenv(
    "PON_PRODUCT_MOVES_SOURCE_DISPLAY",
    r"T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV",
)
PON_PRODUCT_MOVES_WORKING_DISPLAY = os.getenv(
    "PON_PRODUCT_MOVES_WORKING_DISPLAY",
    r"C:\Docker-Projects\PON_Bike_Data\translogic\PRODUCT_MOVES.CSV",
)
PON_UPSTOCK_WORKING_DISPLAY = os.getenv(
    "PON_UPSTOCK_WORKING_DISPLAY",
    r"C:\Docker-Projects\PON_Bike_Data\import\UPStockSerial.csv",
)
PON_UPSTOCK_FINAL_DISPLAY = os.getenv(
    "PON_UPSTOCK_FINAL_DISPLAY",
    r"T:\Import\UPStockSerial.csv",
)
PON_CLIENT_REPORT_DIR = os.getenv("PON_CLIENT_REPORT_DIR", str(BASE_DIR / "sample_report_data"))
PON_CLIENT_REPORT_WORKING_DISPLAY = os.getenv(
    "PON_CLIENT_REPORT_WORKING_DISPLAY",
    r"C:\Docker-Projects\PON_Bike_Data\reports",
)
PON_CLIENT_REPORT_FINAL_DISPLAY = os.getenv("PON_CLIENT_REPORT_FINAL_DISPLAY", "")
PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED = _env_flag("PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED", "0")
PON_TRANSLOGIC_IMPORT_DIRECT_PATH = os.getenv(
    "PON_TRANSLOGIC_IMPORT_DIRECT_PATH", "/data/translogic_import_direct"
)
PON_PRODUCT_MOVES_DIRECT_ENABLED = _env_flag("PON_PRODUCT_MOVES_DIRECT_ENABLED", "0")
PON_PRODUCT_MOVES_DIRECT_PATH = os.getenv(
    "PON_PRODUCT_MOVES_DIRECT_PATH", "/data/translogic_moves_direct/PRODUCT_MOVES.CSV"
)
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(25 * 1024 * 1024)))
