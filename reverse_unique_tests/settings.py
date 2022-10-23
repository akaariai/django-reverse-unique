SECRET_KEY = 'not-anymore'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = [
    'reverse_unique',
    'reverse_unique_tests',
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'