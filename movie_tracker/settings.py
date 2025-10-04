# movie_tracker/settings.py

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- UNIVERSAL, ENVIRONMENT-AWARE SETTINGS ---

# Read SECRET_KEY from the .env file
SECRET_KEY = os.environ.get('SECRET_KEY')

# Read DEBUG status from .env file. Defaults to False for safety.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Read ALLOWED_HOSTS from .env file and split it into a list
ALLOWED_HOSTS_STRING = os.environ.get('ALLOWED_HOSTS')
ALLOWED_HOSTS = ALLOWED_HOSTS_STRING.split(',') if ALLOWED_HOSTS_STRING else []

# Read CSRF_TRUSTED_ORIGINS from .env file
CSRF_TRUSTED_ORIGINS_STRING = os.environ.get('CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS_STRING.split(',') if CSRF_TRUSTED_ORIGINS_STRING else []


# --- Standard Django Settings (No changes needed here) ---

INSTALLED_APPS = [
    'jazzmin',
    'tracker',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'movie_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'movie_tracker.wsgi.application'

# --- Environment-Aware Database Configuration ---
# This will use PostgreSQL if it finds the POSTGRES_DB variable in .env,
# otherwise it will fall back to using SQLite for local development.
if 'POSTGRES_DB' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB'),
            'USER': os.environ.get('POSTGRES_USER'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- Static Files Configuration for Production ---
STATIC_URL = '/staticfiles/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'next_movie'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'next_movie'

JAZZMIN_SETTINGS = {
    "site_title": "HaveYouSeenIt Admin",
    "site_header": "HaveYouSeenIt",
    "list_filter_actions_on_top": True,
    "site_logo": None,
    "welcome_sign": "Welcome to the HaveYouSeenIt Admin Panel",
    "copyright": "HaveYouSeenIt Ltd.",
    "ui_tweaks": {
        "navbar_theme": "navbar-dark",
        "brand_theme": "navbar-dark",
        "sidebar_theme": "sidebar-dark-primary",
    }
}