# backbone/settings_test.py
from .settings import *
import logging

# Loop through the databases defined in your base settings
# and force them all to run lightning-fast in RAM
for db_config in DATABASES.values():
    db_config["ENGINE"] = "django.db.backends.sqlite3"
    db_config["NAME"] = ":memory:"


# Your other test overrides remain the same
DEBUG = False
TESTING = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Completely mute all db creation and migration logs in console output
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["null"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.migrations": {
            "handlers": ["null"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
