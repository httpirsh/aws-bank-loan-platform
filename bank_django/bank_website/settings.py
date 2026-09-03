"""
Django settings for loans_app project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Loads variables from a local .env file if present (gitignored, see .env.example).
# In the devcontainer, env vars come from remoteEnv instead, so this is a no-op there.
load_dotenv(BASE_DIR.parent / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "bank-website-env.eba-ganzz9ai.us-east-1.elasticbeanstalk.com,localhost,127.0.0.1",
).split(",")

# Application definition

INSTALLED_APPS = [
    "api",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "bank_website.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
                os.path.join(BASE_DIR, 'frontend', 'templates'),  
                os.path.join(BASE_DIR, 'frontend', 'dist'),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]



WSGI_APPLICATION = "bank_website.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'db-loan-applications'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# AWS Configuration from environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN', '')
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
AWS_COLLECTION_NAME = os.getenv('AWS_COLLECTION_NAME', 'userfaces')
AWS_DYNAMO_TABLE_NAME = os.getenv('AWS_DYNAMO_TABLE_NAME', 'Users')

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files for Vite (CSS, JavaScript, Images)
ASSETS_ROOT = os.path.join(BASE_DIR, 'frontend', 'dist', 'assets')
ASSETS_URL = '/assets/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
# STATIC_ROOT is collectstatic's output dir for deployment; it must be
# separate from STATICFILES_DIRS, which is where collectstatic (and the
# dev-mode finder) looks for source files - here, the Vite build output.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = "/assets/"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend', 'dist', 'assets'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

