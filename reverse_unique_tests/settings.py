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
    'tests',
]

SILENCED_SYSTEM_CHECKS = ['1_7.W001']
