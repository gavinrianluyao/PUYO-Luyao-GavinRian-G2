import os

os.environ.setdefault("SECRET_KEY", "django-insecure-test-key-puyo-automated-testing")

from .settings import *


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
