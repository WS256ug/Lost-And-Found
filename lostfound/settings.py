import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-26z046ai=)+)e7g)x=wp!bgn#rra(2p2*oncx#+wkeb!d#iir_",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "0" if os.environ.get("VERCEL") else "1") == "1"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "lost-and-found-murex-kappa.vercel.app,lost-and-found-ws-teams.vercel.app,.vercel.app,127.0.0.1,localhost,10.0.2.2,10.10.6.122,192.168.1.54"
    ).split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://lost-and-found-murex-kappa.vercel.app,https://lost-and-found-ws-teams.vercel.app,https://*.vercel.app",
    ).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'accounts',
    'api',
    'items',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lostfound.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'items.context_processors.nav_counts',
            ],
        },
    },
]

WSGI_APPLICATION = 'lostfound.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
def database_from_url(url):
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))

    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": parsed.port or "",
            "OPTIONS": {"sslmode": query.get("sslmode", "require")},
        }

    if parsed.scheme == "sqlite":
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": parsed.path,
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")


DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_PRISMA_URL")
)
if DATABASE_URL:
    default_database = database_from_url(DATABASE_URL)
elif os.environ.get("VERCEL"):
    default_database = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SQLITE_PATH", "/tmp/db.sqlite3"),
    }
else:
    default_database = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }

DATABASES = {
    "default": default_database
}

# if os.environ.get("VERCEL"):
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': '/tmp/db.sqlite3',
#         }
#     }
# else:
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': BASE_DIR / 'db.sqlite3',
#         }
#     }
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_REDIRECT_URL = 'item_list'
LOGOUT_REDIRECT_URL = 'item_list'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
}

CORS_ALLOWED_ORIGINS = [
    'capacitor://localhost',
    'http://localhost',
    'https://localhost',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:8100',
    'http://127.0.0.1:8100',
    'https://lost-and-found-murex-kappa.vercel.app',
    'https://lost-and-found-ws-teams.vercel.app',
]
